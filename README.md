# pyopenroad

Python access to the Actian Ingres OpenROAD AppServer. For CPython and Jython.

Requirements:

  * OpenROAD
  * Under Windows
      * CPython 2.7 along with the Python extensions for Windows (pywin32)
  * Under Linux/Unix
      * Jython 2.7 (and Java) along with either II_SYSTEM set or openroad.jar in classpath


To run tests against a default install of the OpenROAD install issue:

    test_orserver.py TestOpenROADServerSimpleCallProcComtestNoMetaDataLookup TestOpenROADServerSimpleProxyComtestWithMetaData

If `test_orserver.py` is ran without parameters all tests will be ran.
