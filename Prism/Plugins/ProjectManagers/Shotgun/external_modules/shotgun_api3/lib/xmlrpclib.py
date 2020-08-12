#! /opt/local/bin/python
 
# XML-RPC CLIENT LIBRARY
# $Id: xmlrpclib.py 41594 2005-12-04 19:11:17Z andrew.kuchling $
#
# an XML-RPC client interface for Python.
#
# the marshalling and response parser code can also be used to
# implement XML-RPC servers.
#
# Notes:
# this version is designed to work with Python 2.1 or newer.
#
# History:
# 1999-01-14 fl  Created
# 1999-01-15 fl  Changed dateTime to use localtime
# 1999-01-16 fl  Added Binary/base64 element, default to RPC2 service
# 1999-01-19 fl  Fixed array data element (from Skip Montanaro)
# 1999-01-21 fl  Fixed dateTime constructor, etc.
# 1999-02-02 fl  Added fault handling, handle empty sequences, etc.
# 1999-02-10 fl  Fixed problem with empty responses (from Skip Montanaro)
# 1999-06-20 fl  Speed improvements, pluggable parsers/transports (0.9.8)
# 2000-11-28 fl  Changed boolean to check the truth value of its argument
# 2001-02-24 fl  Added encoding/Unicode/SafeTransport patches
# 2001-02-26 fl  Added compare support to wrappers (0.9.9/1.0b1)
# 2001-03-28 fl  Make sure response tuple is a singleton
# 2001-03-29 fl  Don't require empty params element (from Nicholas Riley)
# 2001-06-10 fl  Folded in _xmlrpclib accelerator support (1.0b2)
# 2001-08-20 fl  Base xmlrpclib.Error on built-in Exception (from Paul Prescod)
# 2001-09-03 fl  Allow Transport subclass to override getparser
# 2001-09-10 fl  Lazy import of urllib, cgi, xmllib (20x import speedup)
# 2001-10-01 fl  Remove containers from memo cache when done with them
# 2001-10-01 fl  Use faster escape method (80% dumps speedup)
# 2001-10-02 fl  More dumps microtuning
# 2001-10-04 fl  Make sure import expat gets a parser (from Guido van Rossum)
# 2001-10-10 sm  Allow long ints to be passed as ints if they don't overflow
# 2001-10-17 sm  Test for int and long overflow (allows use on 64-bit systems)
# 2001-11-12 fl  Use repr() to marshal doubles (from Paul Felix)
# 2002-03-17 fl  Avoid buffered read when possible (from James Rucker)
# 2002-04-07 fl  Added pythondoc comments
# 2002-04-16 fl  Added __str__ methods to datetime/binary wrappers
# 2002-05-15 fl  Added error constants (from Andrew Kuchling)
# 2002-06-27 fl  Merged with Python CVS version
# 2002-10-22 fl  Added basic authentication (based on code from Phillip Eby)
# 2003-01-22 sm  Add support for the bool type
# 2003-02-27 gvr Remove apply calls
# 2003-04-24 sm  Use cStringIO if available
# 2003-04-25 ak  Add support for nil
# 2003-06-15 gn  Add support for time.struct_time
# 2003-07-12 gp  Correct marshalling of Faults
# 2003-10-31 mvl Add multicall support
# 2004-08-20 mvl Bump minimum supported Python version to 2.1
#
# Copyright (c) 1999-2002 by Secret Labs AB.
# Copyright (c) 1999-2002 by Fredrik Lundh.
#
# info@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The XML-RPC client interface is
#
# Copyright (c) 1999-2002 by Secret Labs AB
# Copyright (c) 1999-2002 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

#
# things to look into some day:

# TODO: sort out True/False/boolean issues for Python 2.3

"""
An XML-RPC client interface for Python.

The marshalling and response parser code can also be used to
implement XML-RPC servers.

Exported exceptions:
  
  Error          Base class for client errors
  ProtocolError  Indicates an HTTP protocol error
  ResponseError  Indicates a broken response package
  Fault          Indicates an XML-RPC fault package

Exported classes:
  
  ServerProxy    Represents a logical connection to an XML-RPC server
  
  MultiCall      Executor of boxcared xmlrpc requests
  Boolean        boolean wrapper to generate a "boolean" XML-RPC value
  DateTime       dateTime wrapper for an ISO 8601 string or time tuple or
                 localtime integer value to generate a "dateTime.iso8601"
                 XML-RPC value
  Binary         binary data wrapper
  
  SlowParser     Slow but safe standard parser (based on xmllib)
  Marshaller     Generate an XML-RPC params chunk from a Python data structure
  Unmarshaller   Unmarshal an XML-RPC response from incoming XML event message
  Transport      Handles an HTTP transaction to an XML-RPC server
  SafeTransport  Handles an HTTPS transaction to an XML-RPC server

Exported constants:
  
  True
  False

Exported functions:
  
  boolean        Convert any Python value to an XML-RPC boolean
  getparser      Create instance of the fastest available parser & attach
                 to an unmarshalling object
  dumps          Convert an argument tuple or a Fault instance to an XML-RPC
                 request (or response, if the methodresponse option is used).
  loads          Convert an XML-RPC packet to unmarshalled data plus a method
                 name (None if not present).
"""

import re, string, time, operator

from types import *
import socket
import errno
import httplib

# --------------------------------------------------------------------
# Internal stuff

try:
    unicode
except NameError:
    unicode = None # unicode support not available

try:
    import datetime
    #import sg_timezone
except ImportError:
    datetime = None

try:
    _bool_is_builtin = False.__class__.__name__ == "bool"
except NameError:
    _bool_is_builtin = 0

def _decode(data, encoding, is8bit=re.compile("[\x80-\xff]").search):
    # decode non-ascii string (if possible)
    if unicode and encoding and is8bit(data):
        data = unicode(data, encoding)
    return data

def escape(s, replace=string.replace):
    s = replace(s, "&", "&amp;")
    s = replace(s, "<", "&lt;")
    return replace(s, ">", "&gt;",)

if unicode:
    def _stringify(string):
        # convert to 7-bit ascii if possible
        try:
            return string.encode("ascii")
        except UnicodeError:
            return string
else:
    def _stringify(string):
        return string

#__version__ = "1.0.1"

# xmlrpc integer limits
MAXINT =  2L**31-1
MININT = -2L**31

# --------------------------------------------------------------------
# Error constants (from Dan Libby's specification at
# http://xmlrpc-epi.sourceforge.net/specs/rfc.fault_codes.php)

# Ranges of errors
PARSE_ERROR       = -32700
SERVER_ERROR      = -32600
APPLICATION_ERROR = -32500
SYSTEM_ERROR      = -32400
TRANSPORT_ERROR   = -32300

# Specific errors
NOT_WELLFORMED_ERROR  = -32700
UNSUPPORTED_ENCODING  = -32701
INVALID_ENCODING_CHAR = -32702
INVALID_XMLRPC        = -32600
METHOD_NOT_FOUND      = -32601
INVALID_METHOD_PARAMS = -32602
INTERNAL_ERROR        = -32603

# --------------------------------------------------------------------
# Exceptions

##
# Base class for all kinds of client-side errors.

class Error(Exception):
    """Base class for client errors."""
    def __str__(self):
        return repr(self)

##
# Indicates an HTTP-level protocol error.  This is raised by the HTTP
# transport layer, if the server returns an error code other than 200
# (OK).
#
# @param url The target URL.
# @param errcode The HTTP error code.
# @param errmsg The HTTP error message.
# @param headers The HTTP header dictionary.

class ProtocolError(Error):
    """Indicates an HTTP protocol error."""
    def __init__(self, url, errcode, errmsg, headers):
        Error.__init__(self)
        self.url = url
        self.errcode = errcode
        self.errmsg = errmsg
        self.headers = headers
    def __repr__(self):
        return (
            "<ProtocolError for %s: %s %s>" %
            (self.url, self.errcode, self.errmsg)
            )

##
# Indicates a broken XML-RPC response package.  This exception is
# raised by the unmarshalling layer, if the XML-RPC response is
# malformed.

class ResponseError(Error):
    """Indicates a broken response package."""
    pass

##
# Indicates an XML-RPC fault response package.  This exception is
# raised by the unmarshalling layer, if the XML-RPC response contains
# a fault string.  This exception can also used as a class, to
# generate a fault XML-RPC message.
#
# @param faultCode The XML-RPC fault code.
# @param faultString The XML-RPC fault string.

class Fault(Error):
    """Indicates an XML-RPC fault package."""
    def __init__(self, faultCode, faultString, **extra):
        Error.__init__(self)
        self.faultCode = faultCode
        self.faultString = faultString
    def __repr__(self):
        return (
            "<Fault %s: %s>" %
            (self.faultCode, repr(self.faultString))
            )

# --------------------------------------------------------------------
# Special values

##
# Wrapper for XML-RPC boolean values.  Use the xmlrpclib.True and
# xmlrpclib.False constants, or the xmlrpclib.boolean() function, to
# generate boolean XML-RPC values.
#
# @param value A boolean value.  Any true value is interpreted as True,
#              all other values are interpreted as False.

if _bool_is_builtin:
    boolean = Boolean = bool
    # to avoid breaking code which references xmlrpclib.{True,False}
    True, False = True, False
else:
    class Boolean:
        """Boolean-value wrapper.
        
        Use True or False to generate a "boolean" XML-RPC value.
        """
        
        def __init__(self, value = 0):
            self.value = operator.truth(value)
        
        def encode(self, out):
            out.write("<value><boolean>%d</boolean></value>\n" % self.value)
        
        def __cmp__(self, other):
            if isinstance(other, Boolean):
                other = other.value
            return cmp(self.value, other)
        
        def __repr__(self):
            if self.value:
                return "<Boolean True at %x>" % id(self)
            else:
                return "<Boolean False at %x>" % id(self)
        
        def __int__(self):
            return self.value
        
        def __nonzero__(self):
            return self.value
    
    True, False = Boolean(1), Boolean(0)
    
    ##
    # Map true or false value to XML-RPC boolean values.
    #
    # @def boolean(value)
    # @param value A boolean value.  Any true value is mapped to True,
    #              all other values are mapped to False.
    # @return xmlrpclib.True or xmlrpclib.False.
    # @see Boolean
    # @see True
    # @see False
    
    def boolean(value, _truefalse=(False, True)):
        """Convert any Python value to XML-RPC 'boolean'."""
        return _truefalse[operator.truth(value)]


