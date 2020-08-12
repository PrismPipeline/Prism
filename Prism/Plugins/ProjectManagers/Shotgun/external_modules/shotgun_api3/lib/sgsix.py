"""
 -----------------------------------------------------------------------------
 Copyright (c) 2009-2019, Shotgun Software Inc.

 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions are met:

  - Redistributions of source code must retain the above copyright notice, this
    list of conditions and the following disclaimer.

  - Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions and the following disclaimer in the documentation
    and/or other materials provided with the distribution.

  - Neither the name of the Shotgun Software Inc nor the names of its
    contributors may be used to endorse or promote products derived from this
    software without specific prior written permission.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

# This module contains addtional functions and variables to supplement the six
# module for python 2/3 compatibility.

from . import six
import io
import sys

# For python 3, the `file` type no longer exists, and open() returns an
# io.IOBase instance. We add file_types to allow comparison across python
# versions.  See https://stackoverflow.com/questions/36321030#36321030
#
# This means that to test if a variable contains a file in both Python 2 and 3
# you can use an isinstance test like:
#     isinstance(value, sgsix.file_types)
if six.PY3:
    file_types = (io.IOBase, )
else:
    file_types = (file, io.IOBase)  # noqa warning for undefined `file` in python 3

# For python-api calls that result in an SSL error, the exception raised is
# different on Python 2 and 3. Store the approriate exception class in a
# variable to allow easier exception handling across Python 2/3.
if six.PY3:
    import ssl
    ShotgunSSLError = ssl.SSLError
else:
    from .httplib2 import SSLHandshakeError
    ShotgunSSLError = SSLHandshakeError


def normalize_platform(platform, python2=True):
    """
    Normalize the return of sys.platform between Python 2 and 3.

    On Python 2 on linux hosts, sys.platform was 'linux' appended with the
    current kernel version that Python was built on.  In Python3, this was
    changed and sys.platform now returns 'linux' regardless of the kernel version.
    See https://bugs.python.org/issue12326
    This function will normalize platform strings to always conform to Python2 or
    Python3 behavior.

    :param str platform: The platform string to normalize
    :param bool python2: The python version behavior to target.  If True, a
        Python2-style platform string will be returned (i.e. 'linux2'), otherwise
        the modern 'linux' platform string will be returned.

    :returns: The normalized platform string.
    :rtype: str
    """
    if python2:
        return "linux2" if platform.startswith("linux") else platform
    return "linux" if platform.startswith("linux") else platform


# sgsix.platform will mimick the python2 sys.platform behavior to ensure
# compatibility with existing comparisons and dict keys.
platform = normalize_platform(sys.platform)
