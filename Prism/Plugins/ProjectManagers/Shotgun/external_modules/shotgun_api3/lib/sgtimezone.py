#! /opt/local/bin/python

# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

# ----------------------------------------------------------------------------
#  SG_TIMEZONE module
#  this is rolled into the this shotgun api file to avoid having to require
#  current users of api2 to install new modules and modify PYTHONPATH info.
# ----------------------------------------------------------------------------

from datetime import tzinfo, timedelta
import time as _time


class SgTimezone(object):
    '''
    Shotgun's server infrastructure is configured for Coordinated Universal
    Time (UTC). In order to provide relevant local timestamps to users, we wrap
    the datetime module's tzinfo to provide convenient conversion methods.
    '''

    ZERO = timedelta(0)
    STDOFFSET = timedelta(seconds=-_time.timezone)
    if _time.daylight:
        DSTOFFSET = timedelta(seconds=-_time.altzone)
    else:
        DSTOFFSET = STDOFFSET
    DSTDIFF = DSTOFFSET - STDOFFSET

    def __init__(self):
        self.utc = UTC()
        self.local = LocalTimezone()

    @classmethod
    def UTC(cls):
        '''
        For backwards compatibility, from when UTC was a nested class,
        we allow instantiation via SgTimezone
        '''
        return UTC()

    @classmethod
    def LocalTimezone(cls):
        '''
        For backwards compatibility, from when LocalTimezone was a nested
        class, we allow instantiation via SgTimezone
        '''
        return LocalTimezone()


class UTC(tzinfo):
    '''
    Implementation of datetime's tzinfo to provide consistent calculated
    offsets against Coordinated Universal Time (UTC)
    '''

    def utcoffset(self, dt):
        return SgTimezone.ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return SgTimezone.ZERO


class LocalTimezone(tzinfo):
    '''
    Implementation of datetime's tzinfo to provide convenient conversion
    between Shotgun server time and local user time
    '''

    def utcoffset(self, dt):
        '''
        Difference between the user's local timezone and UTC timezone in seconds
        '''
        if self._isdst(dt):
            return SgTimezone.DSTOFFSET
        else:
            return SgTimezone.STDOFFSET

    def dst(self, dt):
        '''
        Daylight savings time (dst) offset in seconds
        '''
        if self._isdst(dt):
            return SgTimezone.DSTDIFF
        else:
            return SgTimezone.ZERO

    def tzname(self, dt):
        '''
        Name of the user's local timezone, including a reference
        to daylight savings time (dst) if applicable
        '''
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        '''
        Calculate whether the timestamp in question was in daylight savings
        '''
        tt = (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.weekday(), 0, -1)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0
