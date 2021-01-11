# -*- coding: utf-8 -*-
#
####################################################
#
# PRISM - Pipeline for animation and VFX projects
#
# www.prism-pipeline.com
#
# contact: contact@prism-pipeline.com
#
####################################################
#
#
# Copyright (C) 2016-2020 Richard Frangenberg
#
# Licensed under GNU GPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


import os
import time
import errno
import logging


logger = logging.getLogger(__name__)


class LockfileException(Exception):
    pass


class Lockfile(object):
    def __init__(self, core, fileName, timeout=10, delay=0.05):
        self.core = core
        self._fileLocked = False
        self.lockPath = fileName + ".lock"
        self.fileName = fileName
        self.timeout = timeout
        self.delay = delay

    def acquire(self):
        startTime = time.time()
        while True:
            try:
                self.lockFile = os.open(self.lockPath, os.O_CREAT|os.O_EXCL|os.O_RDWR)
                self._fileLocked = True
                break
            except OSError as e:
                if e.errno == errno.EACCES:
                    msg = "Permission denied to create file:\n\n%s" % self.lockPath
                    self.core.popup(msg)
                    raise LockfileException(msg)
                elif e.errno != errno.EEXIST:
                    raise
                elif time.time() - startTime >= self.timeout:
                    msg = "This config seems to be in use by another process:\n\n%s\n\nForcing to write to this file while another process is writing to it could result in data loss.\n\nDo you want to force writing to this file?" % self.fileName
                    result = self.core.popupQuestion(msg)
                    if result == "Yes":
                        if os.path.exists(self.lockPath):
                            os.remove(self.lockPath)
                    else:
                        raise LockfileException("Timeout occurred while writing to file: %s" % self.fileName)

                time.sleep(self.delay)

    def release(self):
        if self._fileLocked:
            os.close(self.lockFile)
            startTime = time.time()
            while True:
                try:
                    if os.path.exists(self.lockPath):
                        os.remove(self.lockPath)
                    break
                except:
                    if time.time() - startTime >= self.timeout:
                        self.core.popup("Couldn't remove lockfile:\n\n%s\n\nIt might be used by another process. Prism won't be able to write to this file as long as it's lockfile exists." % self.lockPath)
                        break

                time.sleep(self.delay)

            self._fileLocked = False

    def waitUntilReady(self, timeout=None):
        startTime = time.time()
        timeout = timeout or self.timeout
        while True:
            if not os.path.exists(self.lockPath):
                break

            logger.debug("waiting for config to unlock before reading")

            if time.time() - startTime >= timeout:
                msg = "This config seems to be in use by another process:\n\n%s\n\nReading from this file while another process is writing to it could result in data loss.\n\nDo you want to read from this file?" % self.fileName
                result = self.core.popupQuestion(msg)
                if result == "Yes":
                    if os.path.exists(self.lockPath):
                        os.remove(self.lockPath)
                else:
                    raise LockfileException("Timeout occurred while reading from file: %s" % self.fileName)

            time.sleep(self.delay)

    def isLocked(self):
        return os.path.exists(self.lockPath)

    def __enter__(self):
        if not self._fileLocked:
            self.acquire()
        return self

    def __exit__(self, type, value, traceback):
        if self._fileLocked:
            self.release()

    def __del__(self):
        self.release()
