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
import sys
import logging
import traceback
import glob

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class Callbacks(object):
    def __init__(self, core):
        self.core = core
        self.currentCallback = {"plugin": "", "function": ""}
        self.registeredCallbacks = {}
        self.registeredHooks = {}
        self.callbackNum = 0
        self.hookNum = 0

    @err_catcher(name=__name__)
    def registerCallback(self, callbackName, function, priority=50, plugin=None):
        if callbackName not in self.registeredCallbacks:
            self.registeredCallbacks[callbackName] = []

        self.callbackNum += 1
        cbDict = {
            "function": function,
            "callbackName": callbackName,
            "priority": priority,
            "id": self.callbackNum,
            "plugin": plugin,
        }
        self.registeredCallbacks[callbackName].append(cbDict)
        self.registeredCallbacks[callbackName] = sorted(self.registeredCallbacks[callbackName], key=lambda x: int(x["priority"]), reverse=True)
        logger.debug("registered callback: %s" % str(cbDict))
        return cbDict

    @err_catcher(name=__name__)
    def unregisterCallback(self, callbackId):
        for cbName in self.registeredCallbacks:
            for cb in self.registeredCallbacks[cbName]:
                if cb["id"] == callbackId:
                    self.registeredCallbacks[cbName].remove(cb)
                    logger.debug("unregistered callback: %s" % str(cb))
                    return True

        logger.debug("couldn't unregister callback with id %s" % callbackId)
        return False

    @err_catcher(name=__name__)
    def registerHook(self, hookName, filepath):
        if hookName not in self.registeredHooks:
            self.registeredHooks[hookName] = []

        self.hookNum += 1
        hkDict = {
            "hookName": hookName,
            "filepath": filepath,
            "id": self.hookNum,
        }
        self.registeredHooks[hookName].append(hkDict)
        logger.debug("registered hook: %s" % str(hkDict))
        return hkDict

    @err_catcher(name=__name__)
    def registerProjectHooks(self):
        self.registeredHooks = {}
        hooks = self.getProjectHooks()
        for hook in hooks:
            self.registerHook(hook["name"], hook["path"])

    @err_catcher(name=__name__)
    def getProjectHooks(self):
        if not getattr(self.core, "projectPath", None):
            return

        hookPath = os.path.join(
            self.core.projectPath, "00_Pipeline", "Hooks", "*.py"
        )

        hookPaths = glob.glob(hookPath)
        hooks = []
        for path in hookPaths:
            name = os.path.splitext(os.path.basename(path))[0]
            hookData = {"name": name, "path": path}
            hooks.append(hookData)

        return hooks

    @err_catcher(name=__name__)
    def callback(self, name="", types=["custom"], *args, **kwargs):
        if "args" in kwargs:
            args = list(args)
            args += kwargs["args"]
            del kwargs["args"]

        result = []
        self.core.catchTypeErrors = True
        self.currentCallback["function"] = name

        if "curApp" in types:
            self.currentCallback["plugin"] = self.core.appPlugin.pluginName
            res = getattr(self.core.appPlugin, name, lambda *args, **kwargs: None)(*args, **kwargs)
            result.append(res)

        if "unloadedApps" in types:
            for i in self.core.unloadedAppPlugins.values():
                self.currentCallback["plugin"] = i.pluginName
                res = getattr(i, name, lambda *args, **kwargs: None)(*args, **kwargs)
                result.append(res)

        if "custom" in types:
            for i in self.core.customPlugins.values():
                try:
                    self.currentCallback["plugin"] = i.pluginName
                    res = getattr(i, name, lambda *args, **kwargs: None)(*args, **kwargs)
                    result.append(res)
                except:
                    logger.warning("error: %s" % traceback.format_exc())

        if "prjManagers" in types:
            for i in self.core.prjManagers.values():
                self.currentCallback["plugin"] = i.pluginName
                res = getattr(i, name, lambda *args, **kwargs: None)(*args, **kwargs)
                result.append(res)

        if "rfManagers" in types:
            for i in self.core.rfManagers.values():
                self.currentCallback["plugin"] = i.pluginName
                res = getattr(i, name, lambda *args, **kwargs: None)(*args, **kwargs)
                result.append(res)

        if name in self.registeredCallbacks:
            for cb in self.registeredCallbacks[name]:
                self.currentCallback["plugin"] = getattr(cb["plugin"], "pluginName", "")
                res = cb["function"](*args, **kwargs)
                result.append(res)

        if name in self.registeredHooks:
            for cb in self.registeredHooks[name]:
                self.callHook(name, *args, **kwargs)

        self.core.catchTypeErrors = False

        return result

    @err_catcher(name=__name__)
    def callHook(self, hookName, *args, **kwargs):
        if not getattr(self.core, "projectPath", None):
            return

        hookPath = os.path.join(
            self.core.projectPath, "00_Pipeline", "Hooks", hookName + ".py"
        )
        if os.path.exists(os.path.dirname(hookPath)) and os.path.basename(
            hookPath
        ) in os.listdir(os.path.dirname(hookPath)):
            hookDir = os.path.dirname(hookPath)
            if hookDir not in sys.path:
                sys.path.append(os.path.dirname(hookPath))

            if kwargs:
                kwargs["core"] = self.core

            try:
                hook = __import__(hookName)
                getattr(hook, "main", lambda *args, **kwargs: None)(*args, **kwargs)
            except:
                msg = "An Error occuredwhile calling the %s hook:\n\n%s" % (hookName, traceback.format_exc())
                self.core.popup(msg)

            if hookName in sys.modules:
                del sys.modules[hookName]

            if os.path.exists(hookPath + "c"):
                try:
                    os.remove(hookPath + "c")
                except:
                    pass
