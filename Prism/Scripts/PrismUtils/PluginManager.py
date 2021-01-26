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
import shutil
import platform
import logging
import traceback

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

from PrismUtils.Decorators import err_catcher

logger = logging.getLogger(__name__)


class PluginManager(object):
    def __init__(self, core):
        super(PluginManager, self).__init__()
        self.core = core
        self.monkeyPatchedFunctions = {}

    @err_catcher(name=__name__)
    def initializePlugins(self, appPlugin):
        self.core.unloadedAppPlugins = {}
        self.core.customPlugins = {}
        self.core.rfManagers = {}
        self.core.prjManagers = {}
        self.core.inactivePlugins = {}

        pluginDirs = self.getPluginDirs()
        appPlugs = self.searchPlugins(pluginPaths=pluginDirs["pluginPaths"], directories=pluginDirs["searchPaths"], pluginNames=[appPlugin])
        if not appPlugs:
            return

        appPlug = self.loadAppPlugin(appPlugs[0]["name"], pluginPath=appPlugs[0]["path"], startup=True)
        if not appPlug:
            return

        self.loadPlugins(pluginPaths=pluginDirs["pluginPaths"], directories=pluginDirs["searchPaths"], force=False)

        if self.core.appPlugin.pluginName != "Standalone":
            self.core.maxwait = 20
            self.core.elapsed = 0
            if self.core.uiAvailable:
                self.core.timer = QTimer()
            result = self.core.startup()
            if result is False:
                self.core.timer.timeout.connect(self.core.startup)
                self.core.timer.start(1000)
        else:
            self.core.startup()

    @err_catcher(name=__name__)
    def getPluginDirs(self):
        result = {"pluginPaths": [], "searchPaths": []}
        result["searchPaths"] = self.core.pluginDirs
        envPluginDirs = os.getenv("PRISM_PLUGIN_PATHS", "").split(os.pathsep)
        if envPluginDirs[0]:
            result["searchPaths"] += envPluginDirs
        userPluginDirs = self.core.getConfig(config="PluginPaths") or {}
        if userPluginDirs.get("plugins"):
            result["pluginPaths"] += [p["path"] for p in userPluginDirs["plugins"]]

        if userPluginDirs.get("searchPaths"):
            result["searchPaths"] += [p["path"] for p in userPluginDirs["searchPaths"]]

        return result

    @err_catcher(name=__name__)
    def getPluginPath(self, location="root", pluginType="", path="", pluginName=""):
        if location == "root":
            pluginPath = os.path.abspath(
                os.path.join(__file__, os.pardir, os.pardir, os.pardir, "Plugins")
            )
        elif location == "project":
            if not getattr(self.core, "projectPath", None):
                pluginPath = ""
            else:
                pluginPath = os.path.join(self.core.projectPath, "00_Pipeline", "Plugins")
        elif location == "custom":
            pluginPath = path

        if location != "custom" and pluginType:
            if pluginType == "App":
                dirName = "Apps"
            elif pluginType == "Custom":
                dirName = "Custom"
            elif pluginType == "Projectmanager":
                dirName = "ProjectManagers"
            elif pluginType == "Renderfarm":
                dirName = "RenderfarmManagers"

            pluginPath = os.path.join(pluginPath, dirName)

        if pluginName:
            pluginPath = os.path.join(pluginPath, pluginName)

        return pluginPath.replace("\\", "/")

    @err_catcher(name=__name__)
    def loadAppPlugin(self, pluginName, pluginPath=None, startup=False):
        if not pluginPath:
            pluginPath = os.path.join(self.core.pluginPathApp, pluginName, "Scripts")
        else:
            if os.path.basename(pluginPath) != "Scripts":
                pluginPath = os.path.join(pluginPath, "Scripts")

        sys.path.append(pluginPath)
        self.core.appPlugin = getattr(
            __import__("Prism_%s_init" % pluginName), "Prism_Plugin_%s" % pluginName
        )(self.core)

        if not self.core.appPlugin:
            msg = "Prism could not initialize correctly and may not work correctly in this session."
            self.core.popup(msg, severity="error")
            return

        if not getattr(self.core.appPlugin, "enabled", True):
            logger.debug("appplugin disabled")
            return

        self.core.appPlugin.location = "prismRoot"
        self.core.appPlugin.pluginPath = pluginPath

        if not getattr(self.core, "messageParent", None) and QApplication.instance() is not None:
            self.core.messageParent = QWidget()

        if not self.core.appPlugin.hasQtParent:
            self.core.parentWindows = False
            if self.core.appPlugin.pluginName != "Standalone" and self.core.useOnTop:
                self.core.messageParent.setWindowFlags(
                    self.core.messageParent.windowFlags() ^ Qt.WindowStaysOnTopHint
                )

        getattr(self.core.appPlugin, "instantStartup", lambda x: None)(self.core)

        if not startup:
            self.core.appPlugin.startup(self.core)

        logger.debug("loaded app plugin %s" % pluginName)
        return self.core.appPlugin

    @err_catcher(name=__name__)
    def loadPlugins(self, pluginPaths=None, directory=None, directories=None, recursive=False, force=True):
        result = []
        if pluginPaths:
            for pPath in pluginPaths:
                result.append(self.loadPlugin(pPath, force=force))

        directories = directories or []
        if directory:
            directories.append(directory)

        if directories:
            for dr in directories:
                if not os.path.exists(dr):
                    continue

                if recursive:
                    for root, dirs, files in os.walk(dr):
                        for f in files:
                            if f.endswith("_init.py"):
                                path = os.path.dirname(root)
                                result.append(self.loadPlugin(path, force=force))
                                break
                else:
                    for root, dirs, files in os.walk(dr):
                        for pDir in dirs:
                            if pDir == "PluginEmpty":
                                continue

                            if pDir == self.core.appPlugin.pluginName:
                                continue

                            path = os.path.join(dr, pDir)
                            result.append(self.loadPlugin(path, force=force))
                        break

        return result

    @err_catcher(name=__name__)
    def searchPlugins(self, pluginPaths=None, directory=None, directories=None, recursive=True, pluginNames=None):
        result = []

        if pluginPaths:
            for pPath in pluginPaths:
                pluginName = os.path.basename(pPath)
                if pluginNames and pluginName not in pluginNames:
                    continue

                pData = {"name": pluginName, "path": pPath}
                result.append(pData)

        directories = directories or []
        if directory:
            directories.append(directory)

        for dr in directories:
            if not os.path.exists(dr):
                continue

            for root, dirs, files in os.walk(dr):
                for f in files:
                    if not f.endswith("_init.py"):
                        continue

                    path = os.path.dirname(root)
                    pluginName = os.path.basename(path)
                    if pluginNames and pluginName not in pluginNames:
                        continue

                    pData = {"name": pluginName, "path": path}
                    result.append(pData)
                    break

                if not recursive:
                    break

        return result

    @err_catcher(name=__name__)
    def activatePlugin(self, path):
        if os.path.basename(path) == "Scripts":
            path = os.path.dirname(path)
        pluginName = os.path.basename(path)
        inactivePluginNames = self.core.getConfig("plugins", "inactive", dft=[])
        if pluginName in inactivePluginNames:
            inactives = self.core.getConfig("plugins", "inactive", dft=[])
            if pluginName in inactives:
                inactives.remove(pluginName)
            self.core.setConfig("plugins", "inactive", inactives)

        if pluginName in self.core.inactivePlugins:
            self.core.inactivePlugins.pop(pluginName)

        logger.debug("activating plugin %s" % pluginName)
        return self.loadPlugin(path)

    @err_catcher(name=__name__)
    def loadPlugin(self, path, force=True, activate=None):
        if not path:
            logger.debug("invalid pluginpath: \"%s\"" % path)
            return

        if os.path.basename(path) == "Scripts":
            path = os.path.dirname(path)

        pluginName = os.path.basename(path)
        if pluginName == "PluginEmpty":
            return

        if pluginName == "LoadExternalPlugins":
            result = self.core.getConfig("plugins", "load_deprExternalPlugins")
            if result is None:
                qstr = "Deprecated plugin found: \"LoadExternalPlugins\"\nLoading this plugin can cause errors if you haven't modified it to work with this Prism version.\n\nAre you sure you want to load this plugin? (if unsure click \"No\")"
                answer = self.core.popupQuestion(qstr, buttons=["Yes", "No"])
                if answer == "No":
                    self.core.setConfig("plugins", "load_deprExternalPlugins", False)
                    return
                else:
                    self.core.setConfig("plugins", "load_deprExternalPlugins", True)
            elif not result:
                return

        if self.core.getPlugin(pluginName):
            if force:
                self.unloadPlugin(pluginName)
            else:
                logger.warning("plugin is already loaded: \"%s\"" % pluginName)
                return

        initmodule = "Prism_%s_init" % pluginName
        pluginPath = os.path.join(path, "Scripts")
        initPath = os.path.join(pluginPath, initmodule + ".py")

        inactivePluginNames = self.core.getConfig("plugins", "inactive", dft=[])
        if pluginName in inactivePluginNames:
            if not os.path.exists(path):
                logger.debug("pluginpath doesn't exist: %s" % path)
                return

            if activate:
                return self.activatePlugin(path)

            self.core.inactivePlugins[pluginName] = pluginPath
            logger.debug("skipped loading plugin %s - plugin is set as inactive in the preferences" % pluginName)
            return

        if pluginName == self.core.appPlugin.pluginName:
            return

        if not (
            os.path.exists(initPath)
            or os.path.exists(initPath.replace("_init", "_init_unloaded"))
        ):
            logger.warning("skipped loading plugin %s - plugin has no init script" % pluginName)
            return

        sys.path.append(os.path.dirname(initPath))
        try:
            if os.path.exists(initPath.replace("_init", "_init_unloaded")):
                pPlug = getattr(
                    __import__("Prism_%s_init_unloaded" % (pluginName)),
                    "Prism_%s_unloaded" % pluginName,
                )(self.core)
            else:
                pPlug = getattr(__import__("Prism_%s_init" % (pluginName)), "Prism_%s" % pluginName)(
                    self.core
                )
        except:
            msg = "Failed to load plugin: %s" % pluginName
            result = self.core.popupQuestion(msg, buttons=["Details", "Close"], icon=QMessageBox.Warning, default="Details")
            if result == "Details":
                detailMsg = msg + "\n\n" + traceback.format_exc()
                self.core.showErrorDetailPopup(detailMsg)
            self.core.inactivePlugins[pluginName] = pluginPath
            return

        if platform.system() not in pPlug.platforms:
            logger.debug("skipped loading plugin %s - plugin doesn't support this OS" % pPlug.pluginName)
            return

        if os.path.normpath(path).startswith(os.path.normpath(self.core.prismRoot)):
            pPlug.location = "prismRoot"
        elif path.startswith(getattr(self.core, "projectPath", ())):
            pPlug.location = "prismProject"
        else:
            pPlug.location = "custom"

        pPlug.pluginPath = pluginPath

        if pPlug.pluginType in ["App"]:
            self.core.unloadedAppPlugins[pPlug.pluginName] = pPlug
        else:
            if not pPlug.isActive():
                logger.debug("plugin \"%s\" is inactive" % pPlug.pluginName)
                return

            if pPlug.pluginType in ["Custom"]:
                self.core.customPlugins[pPlug.pluginName] = pPlug
            elif pPlug.pluginType in ["RenderfarmManager"]:
                self.core.rfManagers[pPlug.pluginName] = pPlug
            elif pPlug.pluginType in ["ProjectManager"]:
                self.core.prjManagers[pPlug.pluginName] = pPlug

        logger.debug("loaded plugin %s" % pPlug.pluginName)
        return pPlug

    @err_catcher(name=__name__)
    def reloadPlugins(self, plugins=None):
        appPlug = self.core.appPlugin.pluginName

        pluginDicts = [
            self.core.unloadedAppPlugins,
            self.core.customPlugins,
            self.core.rfManagers,
            self.core.prjManagers,
        ]
        curPlugins = []
        if not plugins or appPlug in plugins:
            curPlugins.append(appPlug)

        for pDict in pluginDicts:
            for plug in pDict:
                if plugins and plug not in plugins:
                    continue

                curPlugins.append(plug)

        for plug in self.core.inactivePlugins:
            if plugins and plug not in plugins:
                continue

            curPlugins.append(plug)

        for plug in curPlugins:
            self.reloadPlugin(plug)

    @err_catcher(name=__name__)
    def reloadPlugin(self, pluginName):
        appPlug = pluginName == self.core.appPlugin.pluginName
        if pluginName in self.core.inactivePlugins:
            pluginPath = self.core.inactivePlugins[pluginName]
            self.core.inactivePlugins.pop(pluginName)
        else:
            pluginPath = self.unloadPlugin(pluginName)

        if appPlug:
            pluginName = self.getPluginNameFromPath(pluginPath)
            plugin = self.loadAppPlugin(pluginName, pluginPath=pluginPath)
        else:
            plugin = self.loadPlugin(pluginPath)
        return plugin

    @err_catcher(name=__name__)
    def reloadCustomPlugins(self):
        for i in self.core.customPlugins:
            mods = [
                "Prism_%s_init" % i,
                "Prism_%s_Functions" % i,
                "Prism_%s_Variables" % i,
            ]
            for k in mods:
                try:
                    del sys.modules[k]
                except:
                    pass

            cPlug = getattr(__import__("Prism_%s_init" % i), "Prism_%s" % i)(self.core)
            self.core.customPlugins[cPlug.pluginName] = cPlug

    @err_catcher(name=__name__)
    def unloadProjectPlugins(self):
        pluginDicts = [
            self.core.unloadedAppPlugins,
            self.core.customPlugins,
            self.core.rfManagers,
            self.core.prjManagers,
        ]
        prjPlugins = []
        for pDict in pluginDicts:
            for plug in pDict:
                if pDict[plug].location == "prismProject":
                    prjPlugins.append(plug)

        for plug in prjPlugins:
            self.core.unloadPlugin(plug)

    @err_catcher(name=__name__)
    def deactivatePlugin(self, pluginName):
        plugin = self.getPlugin(pluginName)
        pluginPath = getattr(plugin, "pluginPath", "")
        inactives = self.core.getConfig("plugins", "inactive", dft=[])
        if pluginName not in inactives:
            inactives.append(pluginName)
        self.core.setConfig("plugins", "inactive", inactives)
        self.core.inactivePlugins[pluginName] = pluginPath
        logger.debug("deactivating plugin %s" % pluginName)
        self.unloadPlugin(pluginName)

    @err_catcher(name=__name__)
    def unloadPlugin(self, pluginName):
        plugin = self.getPlugin(pluginName)
        pluginPath = getattr(plugin, "pluginPath", "")
        getattr(plugin, "unregister", lambda: None)()

        mods = [
            "Prism_%s_init" % pluginName,
            "Prism_%s_init_unloaded" % pluginName,
            "Prism_%s_Functions" % pluginName,
            "Prism_%s_Integration" % pluginName,
            "Prism_%s_externalAccess_Functions" % pluginName,
            "Prism_%s_Variables" % pluginName,
        ]
        for k in mods:
            try:
                del sys.modules[k]
            except:
                pass

        if pluginPath in sys.path:
            sys.path.remove(pluginPath)

        if pluginName in self.core.unloadedAppPlugins:
            pluginCategory = self.core.unloadedAppPlugins
        elif pluginName in self.core.rfManagers:
            pluginCategory = self.core.rfManagers
        elif pluginName in self.core.prjManagers:
            pluginCategory = self.core.prjManagers
        elif pluginName in self.core.customPlugins:
            pluginCategory = self.core.customPlugins
        else:
            pluginCategory = None

        if pluginCategory is not None:
            del pluginCategory[pluginName]

        if pluginName == self.core.appPlugin.pluginName:
            self.core.appPlugin = None

        if plugin:
            logger.debug("unloaded plugin %s" % plugin.pluginName)
            self.unmonkeyPatch(plugins=[plugin])

        return pluginPath

    @err_catcher(name=__name__)
    def getPluginNames(self):
        pluginNames = list(self.core.unloadedAppPlugins.keys())
        pluginNames.append(self.core.appPlugin.pluginName)

        return sorted(pluginNames)

    @err_catcher(name=__name__)
    def getPluginNameFromPath(self, path):
        base = os.path.basename(path)
        if base == "Scripts":
            base = os.path.basename(os.path.dirname(path))

        return base

    @err_catcher(name=__name__)
    def getPluginSceneFormats(self):
        pluginFormats = list(self.core.appPlugin.sceneFormats)

        for i in self.core.unloadedAppPlugins.values():
            pluginFormats += i.sceneFormats

        return pluginFormats

    @err_catcher(name=__name__)
    def getPluginData(self, pluginName, data):
        if pluginName == self.core.appPlugin.pluginName:
            return getattr(self.core.appPlugin, data, None)
        else:
            for i in self.core.unloadedAppPlugins:
                if i == pluginName:
                    return getattr(self.core.unloadedAppPlugins[i], data, None)

        return None

    @err_catcher(name=__name__)
    def getPlugin(self, pluginName):
        if pluginName == self.core.appPlugin.pluginName:
            return self.core.appPlugin
        else:
            for i in self.core.unloadedAppPlugins:
                if i == pluginName:
                    return self.core.unloadedAppPlugins[i]

            if pluginName in self.core.rfManagers:
                return self.core.rfManagers[pluginName]

            if pluginName in self.core.prjManagers:
                return self.core.prjManagers[pluginName]

            if pluginName in self.core.customPlugins:
                return self.core.customPlugins[pluginName]

        return None

    @err_catcher(name=__name__)
    def getLoadedPlugins(self):
        appPlugs = {self.core.appPlugin.pluginName: self.core.appPlugin}
        appPlugs.update(self.core.unloadedAppPlugins)
        plugs = {
            "App": appPlugs,
            "Renderfarm": self.core.rfManagers,
            "Projectmanager": self.core.prjManagers,
            "Custom": self.core.customPlugins,
        }
        return plugs

    @err_catcher(name=__name__)
    def createPlugin(self, pluginName, pluginType, location="root", path=""):
        presetPath = self.getPluginPath("root", pluginType)
        presetPath = os.path.join(presetPath, "PluginEmpty")

        if not os.path.exists(presetPath):
            msg = "Canceled plugin creation: Empty preset doesn't exist:\n\n%s" % self.core.fixPath(presetPath)
            self.core.popup(msg)
            return

        targetPath = self.getPluginPath(location, pluginType, path, pluginName)

        if os.path.exists(targetPath):
            msg = "Canceled plugin creation: Plugin already exists:\n\n%s" % targetPath
            self.core.popup(msg)
            return

        shutil.copytree(presetPath, targetPath)
        self.core.replaceFolderContent(targetPath, "PluginEmpty", pluginName)

        scriptPath = os.path.join(targetPath, "Scripts")
        if not os.path.exists(scriptPath):
            scriptPath = targetPath

        self.core.openFolder(scriptPath)
        return targetPath

    @err_catcher(name=__name__)
    def addToPluginConfig(self, pluginPath=None, searchPath=None):
        userPluginConfig = self.core.getConfig(config="PluginPaths") or {}
        if "plugins" not in userPluginConfig:
            userPluginConfig["plugins"] = []

        if "searchPaths" not in userPluginConfig:
            userPluginConfig["searchPaths"] = []

        if pluginPath:
            pluginData = {"path": pluginPath}
            userPluginConfig["plugins"].append(pluginData)

        if searchPath:
            pathData = {"path": searchPath}
            userPluginConfig["searchPaths"].append(pathData)

        self.core.setConfig(data=userPluginConfig, config="PluginPaths")

    @err_catcher(name=__name__)
    def monkeyPatch(self, orig, new, plugin):
        functionId = "%s.%s" % (orig.__module__, orig.__name__)
        if functionId in self.monkeyPatchedFunctions:
            self.core.popup("Function %s is already monkeypatched and cannot get monkeypatched again by plugin %s." % (functionId, plugin.pluginName))
            return

        self.monkeyPatchedFunctions[functionId] = {"orig": orig, "new": new, "plugin": plugin}
        if sys.version[0] == "3":
            origClass = orig.__self__
        else:
            origClass = orig.im_self

        setattr(origClass, orig.__name__, new)

    @err_catcher(name=__name__)
    def unmonkeyPatch(self, plugins=None):
        unpatched = []
        for mid in self.monkeyPatchedFunctions:
            patch = self.monkeyPatchedFunctions[mid]
            patchPlugin = patch["plugin"]
            if plugins is not None and patchPlugin not in plugins:
                continue

            if sys.version[0] == "3":
                origClass = patch["orig"].__self__
            else:
                origClass = patch["orig"].im_self

            setattr(origClass, patch["new"].__name__, patch["orig"])
            unpatched.append(mid)

        for mid in unpatched:
            self.monkeyPatchedFunctions.pop(mid)
