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


import sys
import traceback
import time
import logging
from datetime import datetime
from functools import wraps

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *


logger = logging.getLogger(__name__)


def err_handler(func, name="", plugin=False):
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            if hasattr(args[0], "core"):
                core = args[0].core
            else:
                core = None
                logger.warning("class has no core")

            versionStr = ""
            if core:
                versionStr += "\nCore: %s" % core.version
            if core and getattr(args[0].core, "appPlugin", None):
                versionStr += "\nApp plugin: %s %s" % (args[0].core.appPlugin.pluginName, args[0].core.appPlugin.version)
            if plugin:
                versionStr += "\nPlugin: %s %s" % (args[0].plugin.pluginName, args[0].plugin.version)

            erStr = "%s ERROR - %s\n%s\n\n%s\n\n%s" % (
                time.strftime("%d/%m/%y %X"),
                name,
                versionStr,
                "".join(traceback.format_stack()),
                traceback.format_exc(),
            )

            if not core:
                raise Exception(erStr)

            ltime = getattr(args[0].core, "lastErrorTime", 0)
            if (time.time() - ltime) > 1:
                isGuiThread = QApplication.instance().thread() == QThread.currentThread()
                if isGuiThread:
                    args[0].core.writeErrorLog(erStr)
                else:
                    raise Exception(erStr)

    return func_wrapper


def err_catcher(name):
    return lambda x, y=name, z=False: err_handler(x, name=y, plugin=z)


def err_catcher_plugin(name):
    return lambda x, y=name, z=True: err_handler(x, name=y, plugin=z)


def err_catcher_standalone(name):
    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "%s ERROR - %s %s:\n\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    name,
                    "".join(traceback.format_stack()),
                    traceback.format_exc(),
                )
                print(erStr)
                QMessageBox.warning(None, "Prism", erStr)

        return func_wrapper
    return err_decorator


def timmer(name):
    def timer_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            startTime = datetime.now()
            logger.info("starttime: %s" % startTime.strftime('%Y-%m-%d %H:%M:%S'))
            func(*args, **kwargs)
            endTime = datetime.now()
            logger.info("endtime: %s" % endTime.strftime('%Y-%m-%d %H:%M:%S'))
            logger.info("duration: %s" % (endTime-startTime))

        return func_wrapper
    return timer_decorator
