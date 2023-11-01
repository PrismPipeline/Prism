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


import os
import sys
import logging
import traceback
import glob

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

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
        self.registeredCallbacks[callbackName] = sorted(
            self.registeredCallbacks[callbackName],
            key=lambda x: int(x["priority"]),
            reverse=True,
        )
        # logger.debug("registered callback: %s" % str(cbDict))
        return cbDict

    @err_catcher(name=__name__)
    def unregisterPluginCallbacks(self, plugin):
        cbIds = []
        for callback in self.registeredCallbacks:
            for callbackItem in self.registeredCallbacks[callback]:
                if callbackItem["plugin"] == plugin:
                    cbIds.append(callbackItem["id"])

        for cbId in cbIds:
            self.unregisterCallback(cbId)

    @err_catcher(name=__name__)
    def unregisterCallback(self, callbackId):
        for cbName in self.registeredCallbacks:
            for cb in self.registeredCallbacks[cbName]:
                if cb["id"] == callbackId:
                    self.registeredCallbacks[cbName].remove(cb)
                    try:
                        logger.debug("unregistered callback: %s" % str(cb))
                    except:
                        pass

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
        # logger.debug("registered hook: %s" % str(hkDict))
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

        hookPath = os.path.join(self.core.projects.getHookFolder(), "*.py")

        hookPaths = glob.glob(hookPath)
        hooks = []
        for path in hookPaths:
            name = os.path.splitext(os.path.basename(path))[0]
            hookData = {"name": name, "path": path}
            hooks.append(hookData)

        return hooks

    @err_catcher(name=__name__)
    def callback(self, name="", *args, **kwargs):
        if "args" in kwargs:
            args = list(args)
            args += kwargs["args"]
            del kwargs["args"]

        result = []
        self.core.catchTypeErrors = True
        self.currentCallback["function"] = name

        if name in self.registeredCallbacks:
            for cb in list(self.registeredCallbacks[name]):
                self.currentCallback["plugin"] = getattr(cb["plugin"], "pluginName", "")
                res = cb["function"](*args, **kwargs)
                result.append(res)

        if name in self.registeredHooks:
            for cb in self.registeredHooks[name]:
                result.append(self.callHook(name, *args, **kwargs))

        self.core.catchTypeErrors = False

        return result

    @err_catcher(name=__name__)
    def callHook(self, hookName, *args, **kwargs):
        if not getattr(self.core, "projectPath", None):
            return

        result = None
        hookPath = os.path.join(self.core.projects.getHookFolder(), hookName + ".py")
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
                result = getattr(hook, "main", lambda *args, **kwargs: None)(*args, **kwargs)
            except:
                msg = "An Error occuredwhile calling the %s hook:\n\n%s" % (
                    hookName,
                    traceback.format_exc(),
                )
                self.core.popup(msg)

            if hookName in sys.modules:
                del sys.modules[hookName]

            if os.path.exists(hookPath + "c"):
                try:
                    os.remove(hookPath + "c")
                except:
                    pass

        return result
