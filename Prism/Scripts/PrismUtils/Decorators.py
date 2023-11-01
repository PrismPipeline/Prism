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
# Copyright (C) 2016-2023 Richard Frangenberg
# Copyright (C) 2023 Prism Software GmbH
#
# Licensed under GNU LGPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


import sys
import traceback
import time
import logging
from datetime import datetime
from functools import wraps

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


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

            data = {}
            versionStr = ""
            if core:
                versionStr += "\nCore: %s" % core.version
                data["version"] = core.version

            if core and getattr(args[0].core, "appPlugin", None):
                data["appPlugin"] = args[0].core.appPlugin.pluginName
                data["appPluginVersion"] = args[0].core.appPlugin.version
                versionStr += "\nApp plugin: %s %s" % (
                    data["appPlugin"],
                    data["appPluginVersion"],
                )
            if hasattr(args[0], "plugin"):
                data["plugin"] = args[0].plugin.pluginName
                data["pluginVersion"] = args[0].plugin.version
                versionStr += "\nPlugin: %s %s" % (
                    data["plugin"],
                    data["pluginVersion"],
                )

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
                isGuiThread = (
                    QApplication.instance()
                    and QApplication.instance().thread() == QThread.currentThread()
                )
                if isGuiThread:
                    args[0].core.writeErrorLog(erStr, data=data)
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
            logger.info("starttime: %s" % startTime.strftime("%Y-%m-%d %H:%M:%S"))
            func(*args, **kwargs)
            endTime = datetime.now()
            logger.info("endtime: %s" % endTime.strftime("%Y-%m-%d %H:%M:%S"))
            logger.info("duration: %s" % (endTime - startTime))

        return func_wrapper

    return timer_decorator
