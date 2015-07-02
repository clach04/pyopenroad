#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
"""OpenROAD AppServer from Python demo

To run either have an app server configured locally that can be
used (localhost is the default test server) or setup OpenROAD
client and setup Operating System evironment variable to point
to an alternative server, e.g.:

Windows

    set TEST_ORSERVER=app_server_hostname

Unix

    TEST_ORSERVER=app_server_hostname
    export TEST_ORSERVER

To run test issue:

    python test_orserver.py

or

    jython test_orserver.py
"""

import os
from pprint import pprint
import sys

from orserver import ApplicationNotFound
from orserver import Binary
from orserver import callproc
from orserver import or_connect
from orserver import func_sig2meta
from orserver import meta2func_sig
from orserver import MethodNotFound
from orserver import SimpleDispatcher


# Default server details
default_appserver_hostname = 'localhost'
default_connection_mode = None


APPSERVER_HOSTNAME = os.environ.get('TEST_ORSERVER') or default_appserver_hostname
CONNECTION_MODE = os.environ.get('TEST_ORSERVER_MODE') or default_connection_mode


def demo_app_does_not_exist(appserver_hostname, connection_mode, w4gl_image):
    print '=' * 65

    try:
        rso = or_connect(w4gl_image, appserver_hostname, connection_mode=connection_mode)
    except ApplicationNotFound as info:
        print 'oh dear'
        print info

def demo_simple_dispatcher(appserver_hostname, connection_mode, w4gl_image):
    print '=' * 65
    rso = or_connect(w4gl_image, appserver_hostname, connection_mode=connection_mode)
    comtest = SimpleDispatcher(rso)
    print 'comtest.__app_metadata', type(comtest)
    print 'comtest.__app_metadata', repr(comtest.__class__.__name__)
    #print 'comtest.__app_metadata', dir(comtest)
    print 'comtest.__app_metadata'
    # Same tests as earlier but no explict signature passing
    print 'call 1- with signature'
    result = comtest.helloworld(hellostring='COMTEST', counter=99)
    print result

    print ''
    print 'call 2 - withOUT signature and all params provided'
    result = comtest.helloworld(hellostring='COMTEST', counter=99)
    print result

    print ''
    print 'call 3 - withOUT signature and missing param'
    result = comtest.helloworld(hellostring='COMTEST')
    print result

    print ''
    print 'call 4 - withOUT signature and all params provided'
    result = comtest.helloworld(hellostring='COMTEST', counter=99)
    print result

    print ''
    print 'call 5 - with signature and missing param'
    result = comtest.helloworld(hellostring='COMTEST')
    print result

    print ''
    print 'call 6 - method that does not exist'
    try:
        result = comtest.method_does_not_exist(hellostring='COMTEST')
    except MethodNotFound as info:
        print 'oh dear'
        print info

    rso.disconnect()


def demo_manual_calls(appserver_hostname, connection_mode, w4gl_image):
    func_sig = 'hellostring=STRING; counter=INTEGER'

    # declare OpenROAD RemoteServer and Helper objects
    rso = or_connect(w4gl_image, appserver_hostname, connection_mode=connection_mode)

    print 'call 1- with signature'
    result = callproc(rso, 'helloworld', func_sig=func_sig, hellostring='COMTEST', counter=99)
    print result

    print ''
    print 'call 2 - withOUT signature and all params provided'
    result = callproc(rso, 'helloworld', func_sig=None, hellostring='COMTEST', counter=99)
    print result

    print ''
    print 'call 3 - withOUT signature and missing param'
    result = callproc(rso, 'helloworld', func_sig=None, hellostring='COMTEST')
    print result

    print ''
    print 'call 4 - withOUT signature and all params provided'
    result = callproc(rso, 'helloworld', func_sig=None, hellostring='COMTEST', counter=99)
    print result

    print ''
    print 'call 5 - with signature and missing param'
    result = callproc(rso, 'helloworld', func_sig=func_sig, hellostring='COMTEST')
    print result

    print ''
    print 'call 6 - method that does not exist'
    try:
        result = callproc(rso, 'method_does_not_exist', hellostring='COMTEST')
    except MethodNotFound as info:
        print 'oh dear'
        print info

    # TODO method does not exist
    rso.disconnect()


def demo_manual_calls_simple_userclass(appserver_hostname, connection_mode, w4gl_image):
    print ''
    print '=' * 65
    print 'demo_manual_calls_simple_userclass'

    func_sig = 'p1=USERCLASS; p1.attr_int=INTEGER; p1.attr_str=STRING; p1.vc_int=STRING; p1.vc_str=STRING'

    # declare OpenROAD RemoteServer and Helper objects
    rso = or_connect(w4gl_image, appserver_hostname, connection_mode=connection_mode)

    test_value_int = 1
    test_value_str = 'test'
    p1 = {
        u'attr_int': test_value_int,
        u'attr_str': test_value_str,
        u'vc_int': None,
        u'vc_str': None,
    }
    print 'call 1 - with signature'
    print 'p1'
    pprint(p1)
    result = callproc(rso, 'echo_ucsimple', func_sig=func_sig, p1=p1)
    print 'result'
    pprint(result)

    rso.disconnect()


def demo(appserver_hostname, connection_mode=None):
    w4gl_image = 'comtest'

    func_sig = 'hellostring=STRING; counter=INTEGER'
    param_meta = func_sig2meta(func_sig)
    print func_sig
    pprint(param_meta)
    print ''

    func_sig = 'p1=USERCLASS; p1.attr_int=INTEGER; p1.attr_str=STRING; p1.vc_int=STRING; p1.vc_str=STRING'
    param_meta = func_sig2meta(func_sig)
    print func_sig
    pprint(param_meta)
    print ''

    func_sig = meta2func_sig(param_meta)
    pprint(param_meta)
    print func_sig
    print ''

    """
    demo_manual_calls(appserver_hostname, connection_mode, w4gl_image)

    demo_app_does_not_exist(appserver_hostname, connection_mode, 'does_not_exist')

    demo_simple_dispatcher(appserver_hostname, connection_mode, w4gl_image)

    w4gl_image = 'mycomtest'
    demo_manual_calls_simple_userclass(appserver_hostname, connection_mode, w4gl_image)
    """


def main(argv=None):
    if argv is None:
        argv = sys.argv

    """Example Usage:

        orserver.py app_server_hostname
    """
    try:
        appserver_hostname = argv[1]
    except IndexError:
        # default it....
        appserver_hostname = 'localhost'

    try:
        connection_mode = argv[2]
    except IndexError:
        # default it....
        connection_mode = None
        #connection_mode = ''
        #connection_mode = 'compressed'

    demo(appserver_hostname, connection_mode)

    return 0


if __name__ == "__main__":
    sys.exit(main())
