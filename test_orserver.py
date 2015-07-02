#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
"""OpenROAD AppServer from Python test suite

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

TODO more data type tests, use

Add additions demos/tests to comtest:
  * simple user class/struct (just int and varchar, versus nested demo in echostructnullable
  * parameters of:
      * array of integer (object)
      * array of string(object)
      * simple user class/struct
  *  Deeply nested UserClasses (and arrays ofUserClasses)
  *  OpenROAD client tests for above, using orunit
"""

import datetime
from decimal import Decimal
import os
import sys
from unittest import main, TestCase

from orserver import Binary
from orserver import guessmeta_from_values
from orserver import or_connect
from orserver import SimpleDispatcher


# Default server details
default_appserver_hostname = 'localhost'
default_connection_mode = None


APPSERVER_HOSTNAME = os.environ.get('TEST_ORSERVER') or default_appserver_hostname
CONNECTION_MODE = os.environ.get('TEST_ORSERVER_MODE') or default_connection_mode


class TestMetaGuess(TestCase):
    def test_helloworld_api(self):
        value = {'hellostring': 'hello', 'counter': 1}
        canon = {u'counter': 'INTEGER', u'hellostring': 'STRING'}
        result = guessmeta_from_values(value)
        self.assertEqual(canon, result)

    def test_echo_ucsimple_api(self):
        value = {
            u'p1': {
                u'attr_int': 1,
                u'attr_str': u'test',
                u'vc_int': None,
                u'vc_str': None,
            },
        }
        # func_sig = 'p1=USERCLASS; p1.attr_int=INTEGER; p1.attr_str=STRING; p1.vc_int=STRING; p1.vc_str=STRING'
        canon = {u'p1': 'USERCLASS', u'p1.attr_int': 'INTEGER', u'p1.attr_str': 'STRING', u'p1.vc_int': 'STRING', u'p1.vc_str': 'STRING'}
        result = guessmeta_from_values(value)
        self.assertEqual(canon, result)


class BaseOpenROADServerComtestWithMetaData(TestCase):
    w4gl_image = 'comtest'
    appserver_hostname = APPSERVER_HOSTNAME
    connection_mode = CONNECTION_MODE
    lookup_meta = True

    def setUp(self):
        # NOTE using Python unittest, setUp() is called before EACH and every
        # test. There is no single setup routine hook (other than hacking init,
        # module main, etc.)
        self.rso = or_connect(self.w4gl_image, self.appserver_hostname, connection_mode=self.connection_mode)
        self.server = SimpleDispatcher(self.rso, lookup_meta=self.lookup_meta)

    def tearDown(self):
        # NOTE like setUp(), tearDown() is called before EACH and every test.
        self.rso.disconnect()


class TestOpenROADServerSimpleCallProcComtestNoMetaDataLookup(BaseOpenROADServerComtestWithMetaData):
    """Does not do lookup of meta data BUT meta data can be
    provided in the test"""

    lookup_meta = False
    helloworld_func_sig = 'hellostring=STRING; counter=INTEGER'

    def test_comtest_helloworld_nometa_001(self):
        canon = {u'counter': 100, u'hellostring': u'Well "COMTEST" to you too.'}
        result = self.server._raw_callproc('helloworld', hellostring='COMTEST', counter=99)
        self.assertEqual(canon, result)

    def test_comtest_helloworld_nometa_002(self):
        canon = {u'hellostring': u'Well "COMTEST" to you too.'}
        result = self.server._raw_callproc('helloworld', hellostring='COMTEST')
        self.assertEqual(canon, result)

    def test_comtest_helloworld_nometa_003(self):
        canon = {}
        result = self.server._raw_callproc('helloworld')
        self.assertEqual(canon, result)

    def test_comtest_helloworld_001(self):
        canon = {u'counter': 100, u'hellostring': u'Well "COMTEST" to you too.'}
        result = self.server._raw_callproc('helloworld', self.helloworld_func_sig, hellostring='COMTEST', counter=99)
        self.assertEqual(canon, result)

    def test_comtest_helloworld_002(self):
        canon = {u'counter': 1, u'hellostring': u'Well "COMTEST" to you too.'}
        result = self.server._raw_callproc('helloworld', self.helloworld_func_sig, hellostring='COMTEST')
        self.assertEqual(canon, result)

    def test_comtest_helloworld_003(self):
        canon = {u'counter': 1, u'hellostring': u'Well NULL to you too!'}
        result = self.server._raw_callproc('helloworld', self.helloworld_func_sig)
        self.assertEqual(canon, result)


class TestOpenROADServerSimpleProxyComtestWithMetaData(BaseOpenROADServerComtestWithMetaData):
    """Tests helloworld procedure in sample comtest application
    Piccolo path: ingres!w4er!generic!w4gl!apped!comtest helloworld.exp"""

    def test_comtest_helloworld_001(self):
        canon = {u'counter': 100, u'hellostring': u'Well "COMTEST" to you too.'}
        result = self.server.helloworld(hellostring='COMTEST', counter=99)
        self.assertEqual(canon, result)

    def test_comtest_helloworld_002(self):
        canon = {u'counter': 1, u'hellostring': u'Well "COMTEST" to you too.'}
        result = self.server.helloworld(hellostring='COMTEST')
        self.assertEqual(canon, result)

    def test_comtest_helloworld_003(self):
        canon = {u'counter': 1, u'hellostring': u'Well NULL to you too!'}
        # no params, NOTE without metadata this will will probably fail
        result = self.server.helloworld()
        self.assertEqual(canon, result)


class TestOpenROADServerSimpleProxyComtestNoMeta(TestOpenROADServerSimpleProxyComtestWithMetaData):
    lookup_meta = False

    def test_comtest_helloworld_002(self):
        canon = {u'hellostring': u'Well "COMTEST" to you too.'}  # counter is not passed in, so not expected unless metadata present
        result = self.server.helloworld(hellostring='COMTEST')
        self.assertEqual(canon, result)

    def test_comtest_helloworld_003(self):
        canon = {}  # nothing expected back when nothing passed in
        result = self.server.helloworld()
        self.assertEqual(canon, result)


MYLONGBYTEOBJVCHAR_LEN = 1234  # EchoTypesNullable() declared myLongbyteobjVchar = varchar(1234)


class TestOpenROADServerSimpleProxyComtestEchoNullableWithMeta(BaseOpenROADServerComtestWithMetaData):
    """Tests echotypesnullable procedure in sample comtest application
    Piccolo path: ingres!w4er!generic!w4gl!apped!comtest echotypesnullable.exp
    """
    lookup_meta = True

    def test_comtest_echotypesnullable_no_params(self):
        """Test call procedure with no parameters."""
        self.maxDiff = None  # DEBUG show all diffs
        canon = {
            u'FIXME!': u'''This is expected to fail due to;
                            missing features in Python<->OpenROAD library
                            and more importantly the expected behavior for
                            the 4gl proc needs to be defined in the canon
                            below (for example, the Vchar versions of
                            parameters do not return NULL values, they
                            return strings of the word NULL).
                            Note special care will need to be taken for the DateNow params''',
            u'hellostring': u'Well NULL to you too!',
            u'counter': None,
            u'myVarchar': None,
            u'myVarcharVchar': u'<NULL>',
            u'myStringobj': None,
            u'myStringobjVchar': u'<NULL>',
            u'myInteger': None,
            u'myIntegerVchar': u'<NULL>',
            u'mySmallint': None,
            u'mySmallintVchar': u'<NULL>',
            u'myFloat': None,
            u'myFloatVchar': u'<NULL>',
            u'myMoney': None,
            u'myMoneyVchar': u'<NULL>',
            u'myDecimal': None,
            u'myDecimalVchar': u'<NULL>',
            u'myDecimal3131': None,
            u'myDecimal3131Vchar': u'<NULL>',
            u'myDecimal3116': None,
            u'myDecimal3116Vchar': u'<NULL>',
            u'myDecimal3100': None,
            u'myDecimal3100Vchar': u'<NULL>',
            u'myDate1': None,
            u'myDate1Vchar': u'<NULL>',
            u'myDate2': None,
            u'myDate2Vchar': u'<NULL>',
            u'myDateNow': None,
            u'myDateNowVchar': None,  # TBD - Server side now is (possible but) awkward to test
            u'myDateToday': None,
            u'myDateTodayVchar': None,  # TBD - Server side today is (possible but) awkward to test
            u'myLongbyteobj': None,
            u'myLongbyteobjVchar': u'<NULL>',
            u'tempStringobj': None,  # TODO this looks like a "bug" or deficiency in the comtest demo (this should be a local variable and not a parameter)
        }
        result = self.server.echotypesnullable()  # no params
        #self.maxDiff = None  # DEBUG show all diffs
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_money_with_float_input(self):
        # based on test_comtest_echotypesnullable_017
        # NOTE assumes II_MONEY_FORMAT=L:$
        test_value = 9.0
        canon = {u'myMoney': Decimal('9.0'), u'myMoneyVchar': u'               $9.00'}
        result = self.server.echotypesnullable(myMoney=test_value, myMoneyVchar=None)
        result = {
            u'myMoney': result[u'myMoney'],
            u'myMoneyVchar': result[u'myMoneyVchar'],
        }  # Ignore other fields
        # normalize decimal values
        canon['myMoney'] = Decimal(canon['myMoney'])
        result['myMoney'] = Decimal(result['myMoney'])
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_longbyte_with_bytes_empty(self):
        # based on test_comtest_echotypesnullable_037
        test_value = ''  # Python bytes/str with LongByteObject as target
        test_value_hex = u''.join(['%02x' % ord(x) for x in test_value]).upper()[:MYLONGBYTEOBJVCHAR_LEN]
        canon = {'myLongbyteobj': test_value, 'myLongbyteobjVchar': test_value_hex}
        result = self.server.echotypesnullable(myLongbyteobj=test_value, myLongbyteobjVchar=None)
        result = {
            u'myLongbyteobj': result[u'myLongbyteobj'],
            u'myLongbyteobjVchar': result[u'myLongbyteobjVchar'],
        }  # Ignore other fields
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_longbyte_with_bytes_simple(self):
        # based on test_comtest_echotypesnullable_031 and test_comtest_echotypesnullable_038
        test_value = 'test'  # Python bytes/str with LongByteObject as target
        test_value_hex = u''.join(['%02x' % ord(x) for x in test_value]).upper()[:MYLONGBYTEOBJVCHAR_LEN]
        canon = {'myLongbyteobj': test_value, 'myLongbyteobjVchar': test_value_hex}
        result = self.server.echotypesnullable(myLongbyteobj=test_value, myLongbyteobjVchar=None)
        result = {
            u'myLongbyteobj': result[u'myLongbyteobj'],
            u'myLongbyteobjVchar': result[u'myLongbyteobjVchar'],
        }  # Ignore other fields
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_longbyte_with_bytes_all_256(self):
        # based on test_comtest_echotypesnullable_longbyte_with_bytes_simple and test_comtest_echotypesnullable_039
        test_value = ''.join(map(chr, range(256)))  # full 8-bit range
        test_value_hex = u''.join(['%02x' % ord(x) for x in test_value]).upper()[:MYLONGBYTEOBJVCHAR_LEN]
        canon = {'myLongbyteobj': test_value, 'myLongbyteobjVchar': test_value_hex}
        result = self.server.echotypesnullable(myLongbyteobj=test_value, myLongbyteobjVchar=None)
        result = {
            u'myLongbyteobj': result[u'myLongbyteobj'],
            u'myLongbyteobjVchar': result[u'myLongbyteobjVchar'],
        }  # Ignore other fields
        self.assertEqual(canon, result)


class TestOpenROADServerSimpleProxyComtestEchoNullableNoMeta(BaseOpenROADServerComtestWithMetaData):
    """Tests echotypesnullable procedure in sample comtest application
    Piccolo path: ingres!w4er!generic!w4gl!apped!comtest echotypesnullable.exp

    Does not test tempStringobj parameter which appears to
    not be needed and maybe should have been declared as a
    local variable in the test procedure as it appears to be
    a side effect of the myLongbyteobj testing.

    TODO
      * go through complete parameter list
      * use NULL and not-null values
      * use edge case values, e.g.
          * min/max
          * for dates - use empty dates ""
          * for dates - times around DST change over periods)
          * varchar and stringobject should test non-ascii characters, using both Unicode and Byte (str) types
          * coercion (e.g. string containg valid numbers with numeric [int|float|decimal|money] as target, etc.)
          * bad values (e.g. string containing "x" for a numeric target, invalid dates, etc.)
    """
    lookup_meta = False

    def test_comtest_echotypesnullable_no_params(self):
        canon = {}  # nothing passed in, nothing expected back
        result = self.server.echotypesnullable()  # no params
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_001(self):
        canon = {u'hellostring': u'Well "python test" to you too.'}
        result = self.server.echotypesnullable(hellostring='python test')
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_002(self):
        canon = {u'counter': 10}
        result = self.server.echotypesnullable(counter=9)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_003(self):
        canon = {u'hellostring': u'Well NULL to you too!'}
        result = self.server.echotypesnullable(hellostring=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_004(self):
        canon = {u'counter': None}
        result = self.server.echotypesnullable(counter=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_005(self):
        canon = {}
        result = self.server.echotypesnullable()
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_006(self):
        canon = {u'myVarchar': None, u'myVarcharVchar': u'<NULL>'}
        result = self.server.echotypesnullable(myVarchar=None, myVarcharVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_007(self):
        test_value = u'Hello'
        canon = {u'myVarchar': test_value, u'myVarcharVchar': test_value}
        result = self.server.echotypesnullable(myVarchar=test_value, myVarcharVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_008(self):
        canon = {u'myStringobj': None, u'myStringobjVchar': u'<NULL>'}
        result = self.server.echotypesnullable(myStringobj=None, myStringobjVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_009(self):
        test_value = u'Hello'
        canon = {u'myStringobj': test_value, u'myStringobjVchar': test_value}
        result = self.server.echotypesnullable(myStringobj=test_value, myStringobjVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_010(self):
        canon = {u'myInteger': None, u'myIntegerVchar': u'<NULL>'}
        result = self.server.echotypesnullable(myInteger=None, myIntegerVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_011(self):
        test_value = 9
        canon = {u'myInteger': test_value, u'myIntegerVchar': str(test_value)}
        result = self.server.echotypesnullable(myInteger=test_value, myIntegerVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_012(self):
        canon = {u'mySmallint': None, u'mySmallintVchar': u'<NULL>'}
        result = self.server.echotypesnullable(mySmallint=None, mySmallintVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_013(self):
        test_value = 9
        canon = {u'mySmallint': test_value, u'mySmallintVchar': str(test_value)}
        result = self.server.echotypesnullable(mySmallint=test_value, mySmallintVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_014(self):
        canon = {u'myFloat': None, u'myFloatVchar': u'<NULL>'}
        result = self.server.echotypesnullable(myFloat=None, myFloatVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_015(self):
        test_value = 9.0
        canon = {u'myFloat': test_value, u'myFloatVchar': str(test_value)}
        result = self.server.echotypesnullable(myFloat=test_value, myFloatVchar=None)
        # normalize from string for comparison
        canon['myFloatVchar'] = float(canon['myFloatVchar'])
        result['myFloatVchar'] = float(result['myFloatVchar'])
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_016(self):
        canon = {u'myMoney': None, u'myMoneyVchar': u'<NULL>'}
        result = self.server.echotypesnullable(myMoney=None, myMoneyVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_017(self):
        test_value = 9.0  # test passing in float (server is expecting Money)
        canon = {u'myMoney': test_value, u'myMoneyVchar': str(test_value)}
        result = self.server.echotypesnullable(myMoney=test_value, myMoneyVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_018(self):
        canon = {u'myDecimal': None, u'myDecimalVchar': u'<NULL>'}
        result = self.server.echotypesnullable(myDecimal=None, myDecimalVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_019(self):
        test_value = Decimal('1.23')
        canon = {u'myDecimal': test_value, u'myDecimalVchar': str(test_value)}
        result = self.server.echotypesnullable(myDecimal=test_value, myDecimalVchar=None)
        canon['myDecimalVchar'] = Decimal(canon['myDecimalVchar'])
        result['myDecimalVchar'] = Decimal(result['myDecimalVchar'])
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_020(self):
        canon = {u'myDecimal3131': None, u'myDecimal3131Vchar': u'<NULL>'}
        result = self.server.echotypesnullable(myDecimal3131=None, myDecimal3131Vchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_021(self):
        test_value = Decimal('0.123')
        canon = {u'myDecimal3131': test_value, u'myDecimal3131Vchar': str(test_value)}
        result = self.server.echotypesnullable(myDecimal3131=test_value, myDecimal3131Vchar=None)
        canon['myDecimal3131Vchar'] = Decimal(canon['myDecimal3131Vchar'])
        result['myDecimal3131Vchar'] = Decimal(result['myDecimal3131Vchar'])
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_022(self):
        canon = {u'myDecimal3116': None, u'myDecimal3116Vchar': u'<NULL>'}
        result = self.server.echotypesnullable(myDecimal3116=None, myDecimal3116Vchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_023(self):
        test_value = Decimal('1.23')
        canon = {u'myDecimal3116': test_value, u'myDecimal3116Vchar': str(test_value)}
        result = self.server.echotypesnullable(myDecimal3116=test_value, myDecimal3116Vchar=None)
        canon['myDecimal3116Vchar'] = Decimal(canon['myDecimal3116Vchar'])
        result['myDecimal3116Vchar'] = Decimal(result['myDecimal3116Vchar'])
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_024(self):
        canon = {u'myDecimal3100': None, u'myDecimal3100Vchar': u'<NULL>'}
        result = self.server.echotypesnullable(myDecimal3100=None, myDecimal3100Vchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_025(self):
        test_value = Decimal('123')
        canon = {u'myDecimal3100': test_value, u'myDecimal3100Vchar': str(test_value)}
        result = self.server.echotypesnullable(myDecimal3100=test_value, myDecimal3100Vchar=None)
        canon['myDecimal3100Vchar'] = Decimal(canon['myDecimal3100Vchar'])
        result['myDecimal3100Vchar'] = Decimal(result['myDecimal3100Vchar'])
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_026(self):
        canon = {'myDate1': None, 'myDate1Vchar': u'<NULL>'}
        result = self.server.echotypesnullable(myDate1=None, myDate1Vchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_027(self):
        # Date only test, no time component
        test_value = datetime.date(2014, 12, 25)
        # NOTE date string format for echo tests is based on
        # server side II_DATE_FORMAT.
        # (Recommend deploying tests using FINLAND format.)
        # Canon below is using (default format) US date format
        canon = {'myDate1': datetime.datetime(test_value.year, test_value.month, test_value.day, ), 'myDate1Vchar': u'25-dec-2014'}  # expect datetime result from date input
        result = self.server.echotypesnullable(myDate1=test_value, myDate1Vchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_028(self):
        # similar as myDate1 test test_comtest_echotypesnullable_026
        canon = {'myDate2': None, 'myDate2Vchar': u'<NULL>'}
        result = self.server.echotypesnullable(myDate2=None, myDate2Vchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_029(self):
        # similar as myDate1 test test_comtest_echotypesnullable_027 but using DateTime instead of Date only
        test_value = datetime.datetime(2014, 12, 25, 13, 50, 55)
        # NOTE date string format for echo tests is based on
        # server side II_DATE_FORMAT.
        # (Recommend deploying tests using FINLAND format.)
        # Canon below is using (default format) US date format
        canon = {'myDate2': test_value, 'myDate2Vchar': u'25-dec-2014 13:50:55'}
        result = self.server.echotypesnullable(myDate2=test_value, myDate2Vchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_030(self):
        canon = {'myLongbyteobj': None, 'myLongbyteobjVchar': u'<NULL>'}
        result = self.server.echotypesnullable(myLongbyteobj=None, myLongbyteobjVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_031(self):
        test_value = 'TODO'  # TODO determine Python datatype(s) to use/support. str (byte) is appropriate along with array
        canon = {'myLongbyteobj': test_value, 'myLongbyteobjVchar': u''}
        result = self.server.echotypesnullable(myLongbyteobj=test_value, myLongbyteobjVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_032(self):
        # non-ASCII unicode support for both varchar and StringObject
        # NOTE this requires the OpenROAD server to be utf8 enabled
        # as this is required in OpenROAD to support the full bmp
        test_values_list = [
            u'Hello',  # English - 7-bit US-ASCII
            u'\u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435!',   # Russian
            u'Ol\xe1',  # Portuguese
            u'\u0417\u0434\u0440\u0430\u0432\u043e',  # Serbian
            u'Hal\xf2',  # Scottish Gaelic
            u'\xa1Hola!',  # Spanish
            u'\u4eca\u65e5\u306f',  # Japanese (konnichiwa)
            u'\u4f60\u597d',  # Chinese (Mandarin - ni hao)
        ]
        self.maxDiff = None  # DEBUG show all diffs
        for test_value in test_values_list:
            canon = {u'myVarchar': test_value, u'myVarcharVchar': test_value}
            result = self.server.echotypesnullable(myVarchar=test_value, myVarcharVchar=None)
            self.assertEqual(canon, result)

            canon = {u'myStringobj': test_value, u'myStringobjVchar': test_value}
            result = self.server.echotypesnullable(myStringobj=test_value, myStringobjVchar=None)
            self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_033(self):
        # test Python str (byte) datatype with varchar using 7-bit clear us-ascii
        test_value = 'Hello'
        canon = {u'myVarchar': test_value, u'myVarcharVchar': test_value}
        result = self.server.echotypesnullable(myVarchar=test_value, myVarcharVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_034(self):
        # test Python str (byte) datatype with varchar using characters out side of 7-bit us-ascii range
        # NOTE both this test and test_comtest_echotypesnullable_033() may end up mapping str into LongByte
        test_value = ''.join(map(chr, range(256)))  # full 8-bit range
        canon = {u'myVarchar': test_value, u'myVarcharVchar': test_value}
        result = self.server.echotypesnullable(myVarchar=test_value, myVarcharVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_035(self):
        # test Python Unicode datatype with varchar using characters out side of 7-bit us-ascii range
        # Based on test_comtest_echotypesnullable_034
        test_value = u''.join(map(unichr, range(256)))
        canon = {u'myVarchar': test_value, u'myVarcharVchar': test_value}
        result = self.server.echotypesnullable(myVarchar=test_value, myVarcharVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_036(self):
        # test OpenROAD LongByte and Python str(bytes) type with full 0-255 range
        # TODO determine Python datatype(s) to use/support. str (byte) is appropriate along with array
        test_value = ''.join(map(chr, range(256)))  # full 8-bit range
        canon = {u'myLongbyteobj': test_value, u'myLongbyteobjVchar': test_value}
        result = self.server.echotypesnullable(myLongbyteobj=test_value, myLongbyteobjVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_037(self):
        # Using explict Binary class wrapper
        # Empty value
        test_value = Binary('')
        test_value_hex = u''.join(['%02x' % ord(x) for x in test_value.data]).upper()[:MYLONGBYTEOBJVCHAR_LEN]
        canon = {u'myLongbyteobj': test_value.data, u'myLongbyteobjVchar': test_value_hex}
        result = self.server.echotypesnullable(myLongbyteobj=test_value, myLongbyteobjVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_038(self):
        # Using explict Binary class wrapper
        test_value = Binary('test')
        test_value_hex = u''.join(['%02x' % ord(x) for x in test_value.data]).upper()[:MYLONGBYTEOBJVCHAR_LEN]
        canon = {u'myLongbyteobj': test_value.data, u'myLongbyteobjVchar': test_value_hex}
        result = self.server.echotypesnullable(myLongbyteobj=test_value, myLongbyteobjVchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echotypesnullable_039(self):
        # test OpenROAD LongByte and Python str(bytes) type with full 0-255 range
        # Using explict Binary class wrapper
        test_value = Binary(''.join(map(chr, range(256))))  # full 8-bit range
        test_value_hex = u''.join(['%02x' % ord(x) for x in test_value.data]).upper()[:MYLONGBYTEOBJVCHAR_LEN]
        canon = {u'myLongbyteobj': test_value.data, u'myLongbyteobjVchar': test_value_hex}
        result = self.server.echotypesnullable(myLongbyteobj=test_value, myLongbyteobjVchar=None)
        self.assertEqual(canon, result)


#class TestOpenROADServerSimpleProxyComtestEchoIntArrayNullableNoMeta(BaseOpenROADServerComtestWithMetaData):
class TestOpenROADServerSimpleProxyComtestEchoIntArrayNullableNoMeta():  # FIXME / TODO this test is DISABLED
    """There was a thought in RWC that there was undocumented support for
    arrays of integer (objects) as parameters (without the need for a
    userclass).From this test, and the generated SCP this does not appear
    to be the case.
    From discussion with SeanT, arrays of StringObject and LongByte might
    be supported.

    Expects 4gl procedure:
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<OPENROAD xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<COMPONENT name="echoarrayint" xsi:type="proc4glsource">
		<versshortremarks>
			<![CDATA[Simple echo of arrays of integer (objects)]]>
		</versshortremarks>
		<script>
			<![CDATA[procedure echoarrayint
(
    intarray = array of IntegerObject,
    intarrayVchar = varchar(1234) /* WARNING truncation an issue for long test input arrays! */
) =
declare
    i = integer not null,
    seperator_str = varchar(10),
    trace = integer not null default 0
enddeclare
{
    //trace = 1;
    if trace = 1 then
        curprocedure.trace('echoarrayint started');
        curprocedure.trace('echoarrayint trace=' + varchar(trace ));
    endif;

    /* Loop through array and concat with comma seperator into intarrayVchar */
    if intarray is not null then
        if trace = 1 then
            curprocedure.trace('echoarrayint intarray is not null');
            curprocedure.trace('echoarrayint intarray.LastRow=' + varchar(intarray.LastRow));
        endif;

        intarrayVchar = '';
        seperator_str =  '';
        for i = 1 to intarray.LastRow do
            if trace = 1 then
                curprocedure.trace('echoarrayint i=' + varchar(i));
                curprocedure.trace('echoarrayint intarray[i].value=' + varchar(intarray[i].value));
            endif;
            intarrayVchar = intarrayVchar + seperator_str + varchar(intarray[i].value);
            if i = 1 then
                seperator_str =  ', ';
            endif;
        endfor;
    else /* intarray is null */
        if trace = 1 then
            curprocedure.trace('echoarrayint intarray is null');
        endif;
        intarrayVchar = '<NULL>';
    endif;

    if trace = 1 then
        curprocedure.trace('echoarrayint ended');
    endif;
}

/*
** Demo frame that calls this procedure

initialize()=
declare
    intarray = array of IntegerObject,
    intarrayVchar = varchar(1234),
    i = integer not null,
    num_elements = integer not null
enddeclare
{
    curframe.trace('test_echoarrayint started');

    num_elements = 0;
    curframe.trace('test_echoarrayint test with ' + varchar(num_elements) + ' elements');
    callproc echoarrayint(intarray=:intarray, intarrayVchar=byref(:intarrayVchar));
    curframe.trace('test_echoarrayint intarrayVchar="' + intarrayVchar + '"');

    num_elements = 10;
    curframe.trace('test_echoarrayint test with ' + varchar(num_elements) + ' elements');
    i = 1;
    while i <= :num_elements do
    curframe.trace('test_echoarrayint i=' + varchar(i));
        intarray[i].value = i;
        //intarray[i].value = i * 11;
    curframe.trace('test_echoarrayint intarray[i].value=' + varchar(intarray[i].value));
        i = i +1;
    endwhile;

    callproc echoarrayint(intarray=:intarray, intarrayVchar=byref(:intarrayVchar));
    curframe.trace('test_echoarrayint intarrayVchar="' + intarrayVchar + '"');

    curframe.trace('test_echoarrayint test with NULL array');
    callproc echoarrayint(intarray=NULL, intarrayVchar=byref(:intarrayVchar));
    curframe.trace('test_echoarrayint intarrayVchar="' + intarrayVchar + '"');

    curframe.trace('test_echoarrayint ended');
    return;
}


*/
]]>
		</script>
		<isarray>0</isarray>
		<isnullable>0</isnullable>
		<genscp>1</genscp>
		<scpname>SCP_echoarrayint</scpname>
		<defaultvalue>1</defaultvalue>
	</COMPONENT>
</OPENROAD>

    """

    w4gl_image = 'mycomtest'
    lookup_meta = False

    def test_comtest_echoarrayint_001(self):
        # test NULL Array of Integer
        test_value = None
        canon = {u'intarray': test_value, u'intarrayVchar': u'<NULL>'}
        result = self.server.echoarrayint(intarray=test_value, intarrayvchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echoarrayint_002(self):
        # test empty Array of Integer
        test_value = []
        canon = {u'intarray': test_value, u'intarrayVchar': u', '.join(test_value)}
        result = self.server.echoarrayint(intarray=test_value, intarrayvchar=None)
        self.assertEqual(canon, result)

    def test_comtest_echoarrayint_003(self):
        # test Array of Integer - 1 through 10
        test_value = list(range(1, 10 + 1))  # [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        canon = {u'intarray': test_value, u'intarrayVchar': u', '.join(test_value)}
        result = self.server.echoarrayint(intarray=test_value, intarrayvchar=None)
        self.assertEqual(canon, result)


class TestOpenROADServerSimpleProxyComtestEchoIntArrayNullableWithMeta(TestOpenROADServerSimpleProxyComtestEchoIntArrayNullableNoMeta):
    lookup_meta = True

    def test_comtest_echoarrayint_no_params(self):
        canon = {u'intarray': None, u'intarrayVchar': '<NULL>'}
        result = self.server.echoarrayint()
        self.assertEqual(canon, result)


class TestOpenROADServerSimpleCallProcSimpleUserClassComtestNoMetaDataLookup(BaseOpenROADServerComtestWithMetaData):
    """Does not do lookup of meta data BUT meta data can be
    provided in the test

        Expects 4gl procedure:
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<OPENROAD xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<COMPONENT name="echo_ucsimple" xsi:type="proc4glsource">
		<script>
			<![CDATA[procedure echo_ucsimple
(
    p1 = ucsimpleintstr;
) =
declare

enddeclare
{
    if p1.attr_int is NULL then
        p1.vc_int = '<NULL>';
    else
        p1.vc_int = varchar(p1.attr_int);
    endif;

    if p1.attr_str is NULL then
        p1.vc_str = '<NULL>';
    else
        p1.vc_str = varchar(p1.attr_str);
    endif;
}
]]>
		</script>
		<isarray>0</isarray>
		<isnullable>0</isnullable>
		<genscp>1</genscp>
		<scpname>SCP_echo_ucsimple</scpname>
		<defaultvalue>1</defaultvalue>
	</COMPONENT>
</OPENROAD>


    Expects 4gl Userclass:

<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<OPENROAD xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<COMPONENT name="ucsimpleintstr" xsi:type="classsource">
		<versshortremarks>
			<![CDATA[Simple user class with only integer and string]]>
		</versshortremarks>
		<superclass>userobject</superclass>
		<attributes>
			<row>
				<displayname>attr_str</displayname>
				<datatype>varchar(32)</datatype>
				<isarray>0</isarray>
				<isnullable>1</isnullable>
				<isprivate>0</isprivate>
				<defaultvalue>1</defaultvalue>
			</row>
			<row>
				<displayname>attr_int</displayname>
				<datatype>integer</datatype>
				<isarray>0</isarray>
				<isnullable>1</isnullable>
				<isprivate>0</isprivate>
				<defaultvalue>1</defaultvalue>
			</row>
			<row>
				<displayname>vc_int</displayname>
				<datatype>varchar(32)</datatype>
				<isarray>0</isarray>
				<isnullable>1</isnullable>
				<isprivate>0</isprivate>
				<defaultvalue>1</defaultvalue>
			</row>
			<row>
				<displayname>vc_str</displayname>
				<datatype>varchar(32)</datatype>
				<isarray>0</isarray>
				<isnullable>1</isnullable>
				<isprivate>0</isprivate>
				<defaultvalue>1</defaultvalue>
			</row>
		</attributes>
	</COMPONENT>
</OPENROAD>
"""

    w4gl_image = 'mycomtest'
    lookup_meta = False
    echo_ucsimple_func_sig = 'p1=USERCLASS; p1.attr_int=INTEGER; p1.attr_str=STRING; p1.vc_int=STRING; p1.vc_str=STRING'

    def test_comtest_echo_simple_int_str_userclass_no_params(self):
        canon = {
            u'p1': {
                u'attr_int': None,
                u'attr_str': None,
                u'vc_int': u'<NULL>',
                u'vc_str': u'<NULL>',
            },
        }
        result = self.server._raw_callproc('echo_ucsimple', self.echo_ucsimple_func_sig)
        self.assertEqual(canon, result)

    def test_comtest_echo_simple_uc_003(self):
        test_value_int = 1
        test_value_str = 'test'  # not an explict Unicode string type (in Py 2.x)
        p1 = {
                u'attr_int': test_value_int,
                u'attr_str': test_value_str,
                u'vc_int': None,
                u'vc_str': None,
            }
        canon = {
            u'p1': {
                u'attr_int': test_value_int,
                u'attr_str': test_value_str,
                u'vc_int': str(test_value_int),
                u'vc_str': str(test_value_str),
            },
        }
        result = self.server._raw_callproc('echo_ucsimple', self.echo_ucsimple_func_sig, p1=p1)
        self.assertEqual(canon, result)

    def test_comtest_echo_simple_uc_003_unicode(self):
        # same as test_comtest_echo_simple_uc_003, bar `test_value_str` value
        test_value_int = 1
        test_value_str = u'test'
        p1 = {
                u'attr_int': test_value_int,
                u'attr_str': test_value_str,
                u'vc_int': None,
                u'vc_str': None,
            }
        canon = {
            u'p1': {
                u'attr_int': test_value_int,
                u'attr_str': test_value_str,
                u'vc_int': str(test_value_int),
                u'vc_str': str(test_value_str),
            },
        }
        result = self.server._raw_callproc('echo_ucsimple', self.echo_ucsimple_func_sig, p1=p1)
        self.assertEqual(canon, result)


class TestOpenROADServerSimpleProxyComtestEchoSimpleUserClassNullableBase(BaseOpenROADServerComtestWithMetaData):
    """Test simple Userclass that has only integer and string (varchar) parameters
    Server implementation uses 2 as input and 2 as varchar output, similar to simple nullable echo test

    See TestOpenROADServerSimpleCallProcSimpleUserClassComtestNoMetaDataLookup for required 4gl"""
    w4gl_image = 'mycomtest'
    lookup_meta = False


class TestOpenROADServerSimpleProxyComtestEchoSimpleUserClassNullableNoMeta(TestOpenROADServerSimpleProxyComtestEchoSimpleUserClassNullableBase):
    lookup_meta = False

    def test_comtest_echo_simple_uc_001(self):
        # Integer
        test_value_int = 1
        p1 = {
                u'attr_int': test_value_int,
                u'vc_int': None,
            }
        canon = {
            u'p1': {
                u'attr_int': test_value_int,
                u'vc_int': str(test_value_int),
            },
        }
        result = self.server.echo_ucsimple(p1=p1)
        self.assertEqual(canon, result)

    def test_comtest_echo_simple_uc_002(self):
        # String
        test_value_str = 'test'
        p1 = {
                u'attr_str': test_value_str,
                u'vc_str': None,
            }
        canon = {
            u'p1': {
                u'attr_str': test_value_str,
                u'vc_str': str(test_value_str),
            },
        }
        result = self.server.echo_ucsimple(p1=p1)
        self.assertEqual(canon, result)

    def test_comtest_echo_simple_uc_003(self):
        # Integer and String
        test_value_int = 1
        test_value_str = 'test'
        p1 = {
                u'attr_int': test_value_int,
                u'attr_str': test_value_str,
                u'vc_int': None,
                u'vc_str': None,
            }
        canon = {
            u'p1': {
                u'attr_int': test_value_int,
                u'attr_str': test_value_str,
                u'vc_int': str(test_value_int),
                u'vc_str': str(test_value_str),
            },
        }
        result = self.server.echo_ucsimple(p1=p1)
        self.assertEqual(canon, result)


class TestOpenROADServerSimpleProxyComtestEchoSimpleUserClassNullableWithMeta(TestOpenROADServerSimpleProxyComtestEchoSimpleUserClassNullableBase):
    lookup_meta = True

    def test_comtest_echo_simple_int_str_userclass_no_params(self):
        canon = {
            u'p1': {
                u'attr_int': None,
                u'attr_str': None,
                u'vc_int': u'<NULL>',
                u'vc_str': u'<NULL>',
            },
        }
        result = self.server.echo_ucsimple()
        self.assertEqual(canon, result)

    def test_comtest_echo_simple_uc_003(self):
        # copy/paste of TestOpenROADServerSimpleProxyComtestEchoSimpleUserClassNullableNoMeta.test_comtest_echo_simple_uc_003()
        test_value_int = 1
        test_value_str = 'test'
        p1 = {
                u'attr_int': test_value_int,
                u'attr_str': test_value_str,
                u'vc_int': None,
                u'vc_str': None,
            }
        canon = {
            u'p1': {
                u'attr_int': test_value_int,
                u'attr_str': test_value_str,
                u'vc_int': str(test_value_int),
                u'vc_str': str(test_value_str),
            },
        }
        result = self.server.echo_ucsimple(p1=p1)
        self.assertEqual(canon, result)


if __name__ == "__main__":
    main()  # NOTE execution never returns
