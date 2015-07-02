#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
"""OpenROAD app server read-only vosa (nee vasa) experiment
either under Windows or cross platform with Java.

Based on code in OpenROAD 4.1 vasa_apps.asp

Windows/DCOM requires CPython Win32 Extensions to access DCOM, available
from http://sourceforge.net/projects/pywin32/

For Windows later than Windows XP also see
http://technet.microsoft.com/en-us/library/cc738214%28v=ws.10%29.aspx
short summary add remote windows users to "Distributed COM Users"

Java requires Jython.

Running
=======

Either have an app server configured locally that can be used
or setup OpenROAD client and setup Operating System evironment
variable to point to server, e.g.:

Windows

    set TEST_ORSERVER=app_server_hostname

Unix

    TEST_ORSERVER=app_server_hostname
    export TEST_ORSERVER

If TEST_ORSERVER is not set and no command line argument is given, localhost is assumed.
"""

import os
import sys

from pprint import pprint 

import orserver


APPSERVER_HOSTNAME = os.environ.get('TEST_ORSERVER') or 'localhost'

def doit(appserver_hostname=APPSERVER_HOSTNAME):
    w4gl_image = 'ASA_ns'
    connection_mode = None
    connection_mode = ''
    #connection_mode = 'unauthenticated'
    #connection_mode = 'compressed'
    #connection_mode = 'unauthenticated-compressed'

    # declare OpenROAD RemoteServer and Helper objects
    rso = orserver.or_connect(w4gl_image, appserver_hostname, connection_mode=connection_mode)

    aso = orserver.get_aso_and_attach_rso(rso)

    func_sig = 'b_arr_UCAkaDetail=UCARRAY; b_arr_UCAkaDetail.i_aka_detail_id=INTEGER; b_arr_UCAkaDetail.i_asolib=INTEGER; b_arr_UCAkaDetail.i_servertype=INTEGER; b_arr_UCAkaDetail.v_aka_name=STRING; b_arr_UCAkaDetail.v_cmdflags=STRING; b_arr_UCAkaDetail.v_imagefile=STRING; b_arr_UCAkaDetail.v_serverlocation=STRING;  b_UCSPOConfig=USERCLASS; b_UCSPOConfig.i_MaxDispatchers=INTEGER; b_UCSPOConfig.i_MaxTotalSlaves=INTEGER; b_UCSPOConfig.i_PrfMonInterval=INTEGER; b_UCSPOConfig.i_PrfMonLevel=INTEGER; b_UCSPOConfig.i_PurgeInterval=INTEGER; b_UCSPOConfig.i_TraceFileAppend=INTEGER; b_UCSPOConfig.i_TraceInterval=INTEGER; b_UCSPOConfig.i_TraceLevel=INTEGER; b_UCSPOConfig.v_TraceFileName=STRING'
    result = orserver.callproc(aso, 'GetAllNameServerData', func_sig=func_sig)
    print result
    print ''
    pprint(result)

    rso.disconnect()


def main(argv=None):
    if argv is None:
        argv = sys.argv

    try:
        hostname = argv[1]
        doit(hostname)
    except IndexError:
        doit()

    return 0


if __name__ == "__main__":
    sys.exit(main())
