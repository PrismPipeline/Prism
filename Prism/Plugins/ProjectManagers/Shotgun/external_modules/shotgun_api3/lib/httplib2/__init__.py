from .. import six

# Define all here to keep linters happy.  It should be overwritten by the code
# below, but if in the future __all__ is not defined in httplib2 this will keep
# things from breaking.
__all__ = []

# Import the proper implementation into the module namespace depending on the
# current python version.  httplib2 supports python 2/3 by forking the code rather
# than with a single cross-compatible module. Rather than modify third party code,
# we'll just import the appropriate branch here.
if six.PY3:
    # Generate ssl_error_classes
    import ssl as __ssl
    ssl_error_classes = (__ssl.SSLError, __ssl.CertificateError)
    del __ssl

    # get the python3 fork of httplib2
    from . import python3 as __httplib2_compat


else:
    # Generate ssl_error_classes
    from .python2 import SSLHandshakeError as __SSLHandshakeError  # TODO: shouldn't rely on this. not public
    ssl_error_classes = (__SSLHandshakeError,)
    del __SSLHandshakeError

    # get the python2 fork of httplib2
    from . import python2 as __httplib2_compat

# Import all of the httplib2 module.  Note that we can't use a star import because
# we need to import *everything*, not just what exists in __all__.
for __name in dir(__httplib2_compat):
    globals()[__name] = getattr(__httplib2_compat, __name)
del __httplib2_compat
del __name

# Add ssl_error_classes to __all__
__all__.append("ssl_error_classes")
