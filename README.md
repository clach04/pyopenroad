# pyopenroad

Python access to the Actian Ingres OpenROAD AppServer. For CPython and Jython.

Requirements:

  * OpenROAD
  * Under Windows
      * CPython along with the Python extensions for Windows (pywin32)
  * Under Linux/Unix
      * Jython/Java along with either II_SYSTEM set or openroad.jar in classpath


To run tests against a default install of the OpenROAD install issue:

    test_orserver.py TestOpenROADServerSimpleCallProcComtestNoMetaDataLookup TestOpenROADServerSimpleProxyComtestWithMetaData

If `test_orserver.py` is ran without parameters all tests will be ran.
