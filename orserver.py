#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
"""Python wrapper around OpenROAD app server calls
Works either under Windows or cross platform with Java.

Windows/DCOM requires CPython Win32 Extensions to access DCOM, available
from http://sourceforge.net/projects/pywin32/

For Windows later than Windows XP also see
http://technet.microsoft.com/en-us/library/cc738214%28v=ws.10%29.aspx
short summary add remote windows users to "Distributed COM Users"

Java requires Jython.
"""

import array
import datetime
import decimal
import calendar
import os
from pprint import pprint
import sys

try:
    import xml.etree.cElementTree as ET
except ImportError:
    try:
        import cElementTree as ET
    except ImportError:
        import elementtree.ElementTree as ET

# win32 specific
try:
    import pythoncom
    import win32com.client
    win32com_client_Dispatch = win32com.client.Dispatch
    import pywintypes
except ImportError:
    win32com_client_Dispatch = None

if win32com_client_Dispatch is None:
    # Assume Jython
    import java.sql  # for Date datatypes

    import jarray

    class classPathHacker(object):
        """Original Author: SG Langer Jan 2007, conversion from Java to Jython
        Updated version (supports Jython 2.5.2) from
        http://glasblog.1durch0.de/?p=846

        Purpose: Allow runtime additions of new Class/jars either from
        local files or URL
        """
        import java.lang.reflect.Method
        import java.io.File
        import java.net.URL
        import java.net.URLClassLoader

        def addFile(self, s):
            """Purpose: If adding a file/jar call this first
            with s = path_to_jar"""
            # make a URL out of 's'
            f = self.java.io.File(s)
            u = f.toURL()
            a = self.addURL(u)
            return a

        def addURL(self, u):
            """Purpose: Call this with u= URL for
            the new Class/jar to be loaded"""
            sysloader = self.java.lang.ClassLoader.getSystemClassLoader()
            sysclass = self.java.net.URLClassLoader
            method = sysclass.getDeclaredMethod("addURL", [self.java.net.URL])
            a = method.setAccessible(1)
            jar_a = jarray.array([u], self.java.lang.Object)
            b = method.invoke(sysloader, [u])
            return u

    # Sanity check.
    # Try and add OpenROAD jar file to CLASSPATH automatically in case classpath
    # was not setup
    II_SYSTEM = os.environ.get('II_SYSTEM')
    if II_SYSTEM is not None:
        openroad_jar_path = os.path.join(II_SYSTEM, 'ingres', 'orjava', 'openroad.jar')
    else:
        # assume/hope jdbc driver is in the current directory
        openroad_jar_path = os.path.join('openroad.jar')

    print openroad_jar_path
    jarLoad = classPathHacker()
    a = jarLoad.addFile(openroad_jar_path)

    # NOTE these require openroad.jar to be in the path
    # and for the OpenROAD environment/path to be set
    from com.ca.openroad import RemoteServer
    from com.ca.openroad import ParameterData
    from com.ca.openroad import ASOSession
    from com.ca.openroad import COMException


class AppServerError(Exception):
    """Base OpenROAD AppServer Exception"""


class MethodNotFound(AppServerError):
    """No such method"""


class ApplicationNotFound(AppServerError):
    """No such application"""


class Binary:
    """Simple class for caller to indicate data is binary
    Currently both str (bytes) and unicode Python types are treated as string,
    this may change but for now this offers a way to preserve that behavior
    and allow binary (LongByteObject / BitmapObject) to be sent/received.
    NOTE this is ONLY used to send binary to OpenROAD. str (bytes) are
    always returned in Python for binary OpenROAD binary types.
    """
    def __init__(self, data):
        self.data = data

if win32com_client_Dispatch:
    def ParameterData(func_sig):
        """Emulate Java interface to generate pdo parameter defs"""
        pdo = win32com_client_Dispatch('OpenROAD.ParameterData')
        param_list = func_sig.split(';')
        #print 'DEBUG', param_list
        for param_info in param_list:
            if param_info:
                param_name, param_type = param_info.split('=')
                param_name = param_name.strip()
                param_type = param_type.strip()
                #print 'DEBUG', (param_name, param_type)
                pdo.DeclareAttribute(param_name, param_type)
        return pdo


def func_sig2meta(func_sig):
    """func_sig is a string in the same format as accepted by ParameterData()
    From a function signature string, create a dictionary of parameter meta data.

    Example:
        func_sig2meta('hellostring=STRING; counter=INTEGER')
        returns {u'counter': 'INTEGER', u'hellostring': 'STRING'}
    """
    param_meta = {}
    param_list = func_sig.split(';')
    for param_info in param_list:
        param_name, param_type = param_info.split('=')
        param_name = param_name.strip()
        if not isinstance(param_name, unicode):
            param_name = param_name.decode('us-ascii')  # 7 bit US-ASCII conversion down
        param_type = param_type.strip()
        param_meta[param_name] = param_type
    return param_meta


def meta2func_sig(param_meta):
    """Reverse of func_sig2meta()

    From a dictionary of parameter meta data create a function
    signature string suitable for use with ParameterData()"""
    function_interface = []
    param_meta_keys = list(param_meta.keys())
    param_meta_keys.sort()  # OpenROAD lib needs UserClass to be set before attributes in class
    for param_name in param_meta_keys:
        type_name = param_meta[param_name]
        function_interface.append('%s=%s' % (param_name, type_name))
    func_sig = '; '.join(function_interface)
    return func_sig


def guessmeta_from_values(values):
    """Given a dictionary `values`, generate metadata dict that matches.
    Returns dictionary of parameter metadata that matches `values`.
    Result can be fed into meta2func_sig().

    Example:
        guessmeta_from_values({'hellostring': 'hello', 'counter': 1})
        returns {u'counter': 'INTEGER', u'hellostring': 'STRING'}
    """
    param_meta = {}
    for param_name in values:
        if not isinstance(param_name, unicode):
            param_name = param_name.decode('us-ascii')  # 7 bit US-ASCII conversion down
        param_value = values[param_name]
        if param_value is None:
            # we have NO idea what OpenROAD type this should be without (SCP) metadata
            type_name = 'STRING'  # NULL string is usually coercible is most situations, there is an Ingres type that works in all situations but string is easier to document
        elif isinstance(param_value, dict):
            # nested data...
            type_name = 'USERCLASS'
            # now all attributes in class
            # FIXME this (probably) only works for un-nested UserClasses
            tmp_param_meta = guessmeta_from_values(param_value)
            for sub_param_name in param_value:
                fully_qualified_sub_param_name = param_name + '.' + sub_param_name
                param_meta[fully_qualified_sub_param_name] = tmp_param_meta[sub_param_name]
        elif isinstance(param_value, Binary):
            type_name = 'BINARY'
        elif isinstance(param_value, basestring):
            type_name = 'STRING'
        elif isinstance(param_value, int):
            type_name = 'INTEGER'
        elif isinstance(param_value, decimal.Decimal):
            type_name = 'DECIMAL'
        elif isinstance(param_value, float):
            type_name = 'FLOAT'  # or DOUBLE/
        elif isinstance(param_value, datetime.date):
            type_name = 'DATE'
            """
        elif isinstance(param_value, list) or isinstance(param_value, tuple):  # simple isinstance(param_value, collections.Iterable) check
            # OpenROAD Array or some kind, really need to know the target
            # type (/class). In all likely hood this is going to be a
            # userclass

            # for simple types, sniff the first item
            first_item = None
            for first_item in param_value:
                break
            type_name = 'ARRAY of....'
            """
        else:
            pytype_info = '%r(%r)' % (param_value.__class__.__name__, type(param_value))
            raise NotImplementedError('unsupported type %r for param %r during set type' % (pytype_info, param_name))
        param_meta[param_name] = type_name

    return param_meta


VALID_OPENROAD_SIGNATURE_TYPES = [
    'BINARY',
    'DATE',
    'DECIMAL',
    'INTEGER',
    'FLOAT',
    'MONEY',
    'SMALLINT',
    'STRING',
]

def scp_clean_type_name(type_name):
    if type_name == 'INT':
        type_name = 'INTEGER'
    elif type_name == 'BYTEARRAY':
        type_name = 'BINARY'
    elif type_name == 'DATETIME':
        type_name = 'DATE'
    elif type_name == 'SHORT':
        # TODO consider just making this an INTEGER instead?
        type_name = 'SMALLINT'
    elif type_name == 'DOUBLE':
        type_name = 'FLOAT'
    return type_name


def scp_class_metadata_to_meta(app_metadata, class_name):
    class_meta = {}
    userclasses_metadata = app_metadata['*classes*']
    #print 'userclasses_metadata'
    #pprint(userclasses_metadata )
    
    userclass_metadata = userclasses_metadata.get(class_name)
    #print 'userclass_metadata', userclass_metadata
    #pprint (userclass_metadata)
    #pprint (userclass_metadata['params'])
    for attr_name in userclass_metadata['params']:
        #print 'attr_name ', attr_name 
        type_name = userclass_metadata['params'][attr_name]['type']
        type_name = type_name.upper()
        type_name = scp_clean_type_name(type_name)
        if type_name not in VALID_OPENROAD_SIGNATURE_TYPES:
            # this could be another userclass name!
            raise NotImplementedError('unsupported type %r for class %r during scp_class_metadata_to_meta' % (type_name, class_name))
        class_meta[attr_name] = type_name
    return class_meta 

def scp_metadata_to_meta(app_metadata, method_name):
    """Given SCP data and function/method name, return dictionary
    of parameter metadata suitable for use with meta2func_sig()

    `app_metadata` is output from get_meta_data(). SCP (obtained metadata)
    is provided in XML format by OpenROAD appserver, get_meta_data()
    obtains SCP data and converts into nested dicts.
    """
    param_meta = {}
    scp_function_metadata = app_metadata.get(method_name) or app_metadata.get('SCP_' + method_name)
    #print 'scp_function_metadata', scp_function_metadata
    if scp_function_metadata:
        scp_param_data = scp_function_metadata['params']
        #pprint(scp_param_data)  # DEBUG
        for param_name in scp_param_data:
            type_name = scp_param_data[param_name]['type']
            type_name = type_name.upper()
            type_name = scp_clean_type_name(type_name)
            if type_name not in VALID_OPENROAD_SIGNATURE_TYPES:
                # This is almost certainly a UserClass, which we should be able to lookup in the metadata
                class_meta = scp_class_metadata_to_meta(app_metadata, type_name.lower())
                if class_meta:
                    for sub_param_name in class_meta:
                        fully_qualified_sub_param_name = param_name + '.' + sub_param_name
                        #print fully_qualified_sub_param_name
                        sub_type_name = class_meta[sub_param_name]
                        param_meta[fully_qualified_sub_param_name] = sub_type_name

                    type_name = 'USERCLASS'
                else:
                    raise NotImplementedError('unsupported type %r for param %r during scp_metadata_to_meta' % (type_name, param_name))
            param_meta[param_name] = type_name
    return param_meta


ARRAY_INDICATOR = '*array*'


def meta2metatree(param_meta):
    """From a dictionary of parameter meta data create nested dictionary
    """
    new_param_meta = {}
    for param_name in param_meta:
        param_type = param_meta[param_name]
        if '.' not in param_name:
            if param_type in ('USERCLASS', 'UCARRAY'):
                new_param_meta[param_name] = new_param_meta.get(param_name, {})
                # handle 'UCARRAY' some how...
                if param_type == 'UCARRAY':
                    new_param_meta[param_name][ARRAY_INDICATOR] = True
            else:
                new_param_meta[param_name] = param_type
        else:
            tmp_name_list = param_name.split('.')
            last_name = tmp_name_list.pop(-1)
            tmp_dict = new_param_meta
            for tmp_name in tmp_name_list:
                tmp_dict[tmp_name] = tmp_dict.get(tmp_name, {})
                tmp_dict = tmp_dict[tmp_name]
            tmp_dict[last_name] = param_type
    return new_param_meta


def pdo_set_value(pdo, param_meta, param_name, param_value):
    #import pdb ; pdb.set_trace()
    type_name = param_meta[param_name]

    if type_name == 'USERCLASS':
        # There is no SetAttribute() for UserClasses
        # set each attribute for the userclass seperately
        for sub_param_name in param_value:
            fully_qualified_sub_param_name = param_name + '.' + sub_param_name
            sub_param_value = param_value.get(sub_param_name)
            pdo_set_value(pdo, param_meta, fully_qualified_sub_param_name, sub_param_value)
        return

    if win32com_client_Dispatch:
        if type_name == 'BINARY':
            if isinstance(param_value, Binary):
                param_value = param_value.data
            # end up with UTF16-LE values in target (and results) if just use bytes/str and built in COM translation
            #param_value = array.array('B', param_value)  # fails, arrays of 'B' are supposed to be supported :-(
            # Passing in bytes/str into VARIANT does not work either
            param_value = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_UI1, array.array('B', param_value))
            pdo.SetAttribute(param_name, param_value)  # now treat like a regular attribute
        elif type_name == 'DATE':
            # Python has a Date and a DateTime type, it makes sense to support both (as input)
            # No attempt is made to deal with timezone information (partly as OpenROAD DCOM library appears to be doing something

            """
            # NOTE this tz code makes no impact on tests
            if isinstance(param_value, datetime.datetime):
                if param_value.utcoffset() is None:
                    # no tzinfo specified, OpenROAD will likely apply some tz foo
                    import win32timezone
                    utc_tzinfo = win32timezone.TimeZoneInfo('UTC', True)
                    param_value.replace(tzinfo = utc_tzinfo)
            """

            # check datetime first as datetime is also an instance of date
            if isinstance(param_value, datetime.datetime):
                pdo.SetAttribute(param_name, param_value)  # treat like a regular attribute
            elif isinstance(param_value, datetime.date):
                # date only
                pdo.SetDateWithoutTime(param_name, param_value)
            else:
                pytype_info = '%r(%r)' % (param_value.__class__.__name__, type(param_value))
                raise NotImplementedError('unsupported type %r for param %r during set data' % (pytype_info, param_name))
        else:
            pdo.SetAttribute(param_name, param_value)
    else:
        if type_name == 'BINARY':
            if isinstance(param_value, Binary):
                param_value = param_value.data
            pdo.setByteArray(param_name, param_value)
        elif type_name == 'STRING':
            pdo.setString(param_name, param_value)
        elif type_name == 'INTEGER':
            pdo.setInt(param_name, param_value)
        elif type_name == 'DATE':
            # No attempt is made to deal with timezone information (partly as OpenROAD DCOM library appears to be doing something
            # TODO currently using a mix of util and sql Date classes

            # Python has a Date and a DateTime type, it makes sense to support both (as input)
            # check datetime first as datetime is also an instance of date
            if isinstance(param_value, datetime.datetime):
                param_value = java.sql.Timestamp.valueOf(param_value.strftime('%Y-%m-%d %H:%M:%S') + ('.%d' % param_value.microsecond))
                pdo.setDate(param_name, param_value)
            elif isinstance(param_value, datetime.date):
                #param_value = java.sql.Date.valueOf(param_value.isoformat())  # date only using sql class
                param_value = java.util.Date(param_value.year - 1900, param_value.month - 1, param_value.day, 0, 0, 0)  # NOTE using Deprecated methods, as of JDK version 1.1
                #print 'param_value.getTimezoneOffset()', param_value.getTimezoneOffset()
                pdo.setDateWithoutTime(param_name, param_value)
            else:
                pytype_info = '%r(%r)' % (param_value.__class__.__name__, type(param_value))
                raise NotImplementedError('unsupported type %r for param %r during set data' % (pytype_info, param_name))
        elif type_name == 'DECIMAL':
            pdo.setBigDecimal(param_name, param_value)
        elif type_name == 'FLOAT':
            pdo.setDouble(param_name, param_value)
        else:
            pytype_info = '%r(%r)' % (param_value.__class__.__name__, type(param_value))
            raise NotImplementedError('unsupported type %r for param %r during set data' % (pytype_info, param_name))

def pdo_get_value(pdo, param_meta, param_name, force_type_name=None):
    #import pdb ; pdb.set_trace()
    type_name = force_type_name or param_meta[param_name]
    if win32com_client_Dispatch:
        result = pdo.GetAttribute(param_name)
        # COM interface returns reasonable type for
        #   STRING, INTEGER, and FLOAT
        # COM returns STRING for Decimal values
        if result is not None:
            if type_name == 'BINARY':
                # We end up with a buffer (py3 memoryview)
                # Whilst buffers are memory efficient, they are not
                # directly convertable to simple types without manual
                # intervention
                result = result[:]
            elif type_name == 'DATE':
                # OpenROAD always returns a DateTime, never Date only
                # No attempt is made to deal with timezone information (partly as OpenROAD DCOM library appears to be doing something
                """Python COM type is PyTime as described at
                http://timgolden.me.uk/pywin32-docs/PyTime.html
                Properties
                    int year
                    int month
                    int weekday
                    int day
                    int hour
                    int minute
                    int second
                    int msec

                Also it is likely UTC based which means pytz will be needed
                """
                """
                # assume date only for now....
                pytime_value = result
                result = datetime.date(
                    year=pytime_value.year,
                    month=pytime_value.month,
                    day=pytime_value.day
                )
                """
                pytime_value = result
                # ignore timezone
                result = datetime.datetime(
                    year=pytime_value.year,
                    month=pytime_value.month,
                    day=pytime_value.day,
                    hour=pytime_value.hour,
                    minute=pytime_value.minute,
                    second=pytime_value.second
                )
            elif type_name == 'DECIMAL':
                result = decimal.Decimal(result)
    else:
        if pdo.isNull(param_name):
            result = None
        elif type_name == 'STRING':
            result = pdo.getString(param_name)
        elif type_name == 'INTEGER':
            result = pdo.getInt(param_name)
        elif type_name == 'SMALLINT':
            result = pdo.getInt(param_name)
        elif type_name == 'BINARY':
            result = pdo.getByteArray(param_name)
            # this is now a Python array type
            if result.typecode == 'b':
                result = result.tostring()  # Convert to a bytes (str) i.e. not Unicode
            else:
                pytype_info = '%r(%r)' % (result.__class__.__name__, type(result))
                raise NotImplementedError('unsupported type %r for BINARY  typecode %r during get data' % (pytype_info, result.typecode))
        elif type_name == 'DATE':
            # OpenROAD always returns a DateTime, never Date only
            # specifically a java.util.Date
            # No attempt is made to deal with timezone information (partly as OpenROAD DCOM library appears to be doing something

            # ignore timezone
            d = pdo.getDate(param_name)
            result = datetime.datetime(1900 + d.getYear(), 1 + d.getMonth(), d.getDate(), d.getHours(), d.getMinutes(), d.getSeconds())  # NOTE using Deprecated methods, as of JDK version 1.1
            """
            # NOTE this code causes test_comtest_echotypesnullable_027 to pass but test_comtest_echotypesnullable_029 to fail
            # attempt to deal with timezone/tz NOTE really need tzinfo to handle this correctly
            tz_offset = d.getTimezoneOffset()
            if tz_offset:
                result = result + datetime.timedelta(minutes=tz_offset)
            """
        elif type_name == 'MONEY':
            result = pdo.getBigDecimal(param_name)
        elif type_name == 'DECIMAL':
            result = pdo.getBigDecimal(param_name)
            # COM returns FLOAT? for Decimal values
            if result:
                if type_name == 'DECIMAL':
                    result = decimal.Decimal(str(result))  # FIXME use more use formatting options?
        elif type_name == 'FLOAT':
            result = pdo.getDouble(param_name)
        else:
                pytype_info = '%r(%r)' % (param_value.__class__.__name__, type(param_value))
                raise NotImplementedError('unsupported type %r for param %r during get data' % (pytype_info, param_name))
    # TODO consider converting BINARY into Python 2.x str type?

    return result

def pdo2flatdict(pdo, param_meta):
    """Optional add a "flat=True" parameter. If flat is true, user class attribute names are left as class.attribute, instead of creating a sub dictionary for the attributes
    """
    result = {}
    for tmp_name in param_meta:
        type_name = param_meta[tmp_name]
        if type_name in ('USERCLASS', 'UCARRAY'):
            pass
            # see pdo2treedict()
        else:
            result[tmp_name] = pdo_get_value(pdo, param_meta, tmp_name)
    return result

def pdo2treedict(pdo, param_meta, prefix=''):
    """convert PDO into a (potentially) nested tree dictionary
    NOTE param_meta is expected to be nested, i.e. output from meta2metatree()
    """
    result = {}
    for tmp_name in param_meta:
        type_info = param_meta[tmp_name]
        if not isinstance(type_info, dict):
            type_name = type_info
            if tmp_name == ARRAY_INDICATOR:
                pass  # skip, not a real attribute
            else:
                new_tmp_name = tmp_name
                if prefix:
                    new_tmp_name = prefix + '.' + tmp_name
                result[tmp_name] = pdo_get_value(pdo, param_meta, new_tmp_name, force_type_name=type_name)
        else:
            new_tmp_name = tmp_name
            if prefix:
                new_tmp_name = prefix + '.' + tmp_name
            result[new_tmp_name] = result.get(new_tmp_name, [])
            is_array = type_info.get(ARRAY_INDICATOR)
            if is_array:
                #import pdb ; pdb.set_trace()
                if win32com_client_Dispatch:
                    num_items = pdo.LastRow(new_tmp_name)
                else:
                    num_items = pdo.lastRow(new_tmp_name)
                # NOTE named tuple would be more space efficient but plain list of dict is easier to visualize as json
                for i in range(1, num_items + 1):  # NOTE index starts from 1 in dcom?
                    # now need to get each element name in the array if a class.....
                    array_tmp_name = '%s[%d]' % (new_tmp_name, i)
                    tmp_row = pdo2treedict(pdo, type_info, prefix=array_tmp_name)
                    result[new_tmp_name].append(tmp_row)
            else:
                # userclass
                result[tmp_name] = pdo2treedict(pdo, type_info, prefix=new_tmp_name)
    return result

def pdo2dict(pdo, param_meta):
    tree_param_meta = meta2metatree(param_meta)
    result = pdo2treedict(pdo, tree_param_meta)
    return result

def get_rso():
    if win32com_client_Dispatch:
        rso = win32com_client_Dispatch('OpenROAD.RemoteServer')
    else:
        rso = RemoteServer()
    return rso

def get_aso():
    if win32com_client_Dispatch:
        aso = win32com_client_Dispatch('OpenROAD.ASOSession')
    else:
        aso = ASOSession()
    return aso

def get_aso_and_attach_rso(rso):
    aso = get_aso()
    if win32com_client_Dispatch:
        aso.AttachRSO(rso)
    else:
        aso.attachRSO(rso)
    return aso


"""
if win32com_client_Dispatch:
    rso_initiate = rso.Initiate
    rso_callproc = rso.CallProc
else:
    rso_initiate = rso.initiate
    rso_callproc = rso.callProc
"""

# TODO Should callproc check i_error_no?
if win32com_client_Dispatch:
    def rso_initiate(rso, *args, **kwargs):
        return rso.Initiate(*args, **kwargs)
    def rso_callproc(rso, procedure_name, pdo_by_value, pdo_by_byref):
        try:
            return rso.CallProc(procedure_name, pdo_by_value, pdo_by_byref)
        except pywintypes.com_error as info:
            if info.excepinfo[2] == u'The specified procedure name was not found in the initiated application.':
                raise MethodNotFound('method %r not found' % procedure_name)
            else:
                raise
else:
    def rso_initiate(rso, *args, **kwargs):
        return rso.initiate(*args, **kwargs)
    def rso_callproc(rso, procedure_name, pdo_by_value, pdo_by_byref):
        try:
            return rso.callProc(procedure_name, pdo_by_value, pdo_by_byref)
        except COMException as info:
            #except com.ca.openroad.COMException
            if info.message == u'HRESULT=0x80041200; The specified procedure name was not found in the initiated application.':
                raise MethodNotFound('method %r not found' % procedure_name)
            else:
                raise


# TODO Make Python Class wrappers for rso and pdo (following pep8?)

def or_connect(w4gl_image, appserver_hostname, connection_mode=None):
    """Sample connection_mode settings:
        connection_mode = None
        connection_mode = ''
        connection_mode = 'unauthenticated'
        connection_mode = 'compressed'
        connection_mode = 'unauthenticated-compressed'
    """

    rso = get_rso()
    if connection_mode is None:
        # Connect directly to OpenROAD Server without using Name Server
        # NOTE for me this works every other call! :-( clach04
        if win32com_client_Dispatch:
            try:
                rso.connect(w4gl_image, appserver_hostname, '')
            except pywintypes.com_error as info:
                error_text = info.excepinfo[2]
                if isinstance(error_text, basestring) and error_text.startswith("Name Server error.\ni_error_no = -329, v_msg_txt = 'uc_name_server.GetInitiateParams: An Application Known As [") and error_text.endswith("] is not registered with the name server, or is suspended or disabled'"):
                    raise ApplicationNotFound('Application %r not found on server %r' % (w4gl_image, appserver_hostname))
                else:
                    raise
        else:
            try:
                rso.connect(w4gl_image, appserver_hostname, '')
            except COMException as info:
                #except com.ca.openroad.COMException
                error_text = info.message
                if isinstance(error_text, basestring) and error_text.startswith("HRESULT=0x8004b100; Name Server error.\ni_error_no = -329, v_msg_txt = 'uc_name_server.GetInitiateParams: An Application Known As [") and error_text.endswith("] is not registered with the name server, or is suspended or disabled'"):
                    raise ApplicationNotFound('Application %r not found on server %r' % (w4gl_image, appserver_hostname))
                else:
                    raise
    else:
        # Connect to OpenROAD Server using Name Server
        connection_mode_num = 0
        w4gl_image_filename = w4gl_image
        if connection_mode != 'http' and not w4gl_image_filename.lower().endswith('.img'):
            # if using http use AKA name (i.e. name) not the filename.
            w4gl_image_filename = w4gl_image_filename + '.img'
        rso_initiate(rso, w4gl_image_filename, '-Tyes -L%s.log' % w4gl_image, appserver_hostname, connection_mode, connection_mode_num)
    return rso

def callproc(rso, procedure_name, func_sig=None, **kwargs):
    """params:
    @rso - already connected rso
    procedure_name - string containing name of procedure
    func_sig - optional parameter with procedure parameter signature, see OR AppServer Java manuual, example for comtest.helloworld() is 'hellostring=STRING; counter=INTEGER'
    """

    if func_sig:
        param_meta = func_sig2meta(func_sig)
    else:
        param_meta = guessmeta_from_values(kwargs)
        func_sig = meta2func_sig(param_meta)
    #print 'func_sig', func_sig

    # use PDO to declare attribute names (parameters) that will be passed
    pdo = ParameterData(func_sig)

    # use PDO to set values
    for param_name in kwargs:
        param_value = kwargs[param_name]
        pdo_set_value(pdo, param_meta, param_name, param_value)

    # Call the procedure in the Application Server
    rso_callproc(rso, procedure_name, None, pdo)

    # Call is complete, retrieve data from pdo byref variables
    result = pdo2dict(pdo, param_meta)

    return result


def get_meta_data(rso):
    """Get metadata from server"""
    func_sig = 'b_osca=USERCLASS; b_osca.i_context_id=INTEGER; b_osca.i_error_type=INTEGER; b_osca.i_error_no=INTEGER; b_so_interface=STRING'
    # Call the procedure in the Application Server
    result = callproc(rso, 'GetMetaDataInterface', func_sig=func_sig)
    xml_metadata = result['b_so_interface']

    # Process meta data
    app_metadata = {}
    gscp_special_names = ('b_osca', 'b_so_xml', 'p_arr_UCXML_Include', 'p_so_xmlin')
    t = ET.fromstring(xml_metadata)

    '''
    # Debug
    def prettify(elem):
        """Return a pretty-printed XML string for the Element."""
        from xml.dom import minidom
        rough_string = ET.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="\t")
    print prettify(t)
    '''
    for scps in t.findall('scps'):
        for scp in scps.findall('scp'):
            #print scp.attrib['name']
            app_metadata[scp.attrib['name']] = {}
            app_metadata[scp.attrib['name']]['info'] = scp.attrib
            app_metadata[scp.attrib['name']]['params'] = {}
            for param in scp.getchildren():
                if param.attrib['name'] not in gscp_special_names:
                    app_metadata[scp.attrib['name']]['params'][param.attrib['name']] = param.attrib

    app_metadata['*classes*'] = app_metadata.get('*classes*', {})
    for _classes in t.findall('classes'):
        for _class in _classes.findall('class'):
            #print _class.attrib['name']
            class_name = _class.attrib['name']
            app_metadata['*classes*'][class_name] = {}
            app_metadata['*classes*'][class_name]['info'] = _class.attrib
            app_metadata['*classes*'][class_name]['params'] = {}
            for param in _class.getchildren():
                app_metadata['*classes*'][class_name]['params'][param.attrib['name']] = param.attrib

    return app_metadata

class SimpleDispatcher:
    def __init__(self, rso, lookup_meta=True):
        """rso should already be connected
        if lookup_meta is False then no attempt to lookup meta data is made"""
        self.__rso = rso
        self.__app_metadata = None
        if lookup_meta:
            self.__app_metadata = get_meta_data(rso)
            #pprint(self.__app_metadata)

    def _raw_callproc(self, method_name, func_sig=None, *args, **kwargs):
        return callproc(self.__rso, method_name, func_sig=func_sig, *args, **kwargs)

    def __getattr__(self, key):
        if self.__dict__.has_key(key):
            return self.__dict__[key]
        else:
            # Assume this is a method lookup

            def gen_function(method_name):
                # Curried function, on method name
                def proxy_function(*args, **kwargs):
                    #print (method_name, args, kwargs)  # DEBUG
                    # FIXME inefficient (although unclear on overhead/impact cost), always lookup and convert metadata
                    func_sig = None
                    if self.__app_metadata:
                        param_meta = scp_metadata_to_meta(self.__app_metadata, method_name)
                        func_sig = meta2func_sig(param_meta)
                    #print 'func_sig=', func_sig
                    return callproc(self.__rso, method_name, func_sig=func_sig, *args, **kwargs)
                return proxy_function

            return gen_function(key)
