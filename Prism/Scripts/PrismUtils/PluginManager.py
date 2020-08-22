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

    @err_catcher(name=__name__)
    def initializePlugins(self, appPlugin):
        self.core.unloadedAppPlugins = {}
        self.core.customPlugins = {}
        self.core.rfManagers = {}
        self.core.prjManagers = {}
        self.core.inactivePlugins = {}

        appPlug = self.loadAppPlugin(appPlugin, startup=True)
        if not appPlug:
            return

        pluginDirs = self.getPluginDirs()
        self.loadPlugins(directories=pluginDirs)

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

    def getPluginDirs(self):
        pluginDirs = self.core.pluginDirs
        envPluginDirs = os.getenv("PRISM_PLUGIN_PATHS", "").split(os.pathsep)
        if envPluginDirs[0]:
            pluginDirs += envPluginDirs
        userPluginDirs = self.core.getConfig(config="PluginPaths", location="user")
        if userPluginDirs:
            pluginDirs += userPluginDirs
        return pluginDirs

    @err_catcher(name=__name__)
    def loadAppPlugin(self, pluginName, startup=False):
        pluginPath = os.path.join(self.core.pluginPathApp, pluginName, "Scripts")
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

        if QApplication.instance() is not None:
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
    def loadPlugins(self, pluginPaths=None, directory=None, directories=None):
        result = []
        if pluginPaths:
            for pPath in pluginPaths:
                result.append(self.loadPlugin(pPath))

        directories = directories or []
        if directory:
            directories.append(directory)

        if directories:
            for dr in directories:
                if not os.path.exists(dr):
                    continue

                for root, dirs, files in os.walk(dr):
                    for pDir in dirs:
                        if pDir == "PluginEmpty":
                            continue

                        if pDir == self.core.appPlugin.pluginName:
                            continue

                        path = os.path.join(dr, pDir)
                        result.append(self.loadPlugin(path))
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
            self.core.inactivePlugins.pop(pluginName)
            logger.debug("activating plugin %s" % pluginName)
            self.loadPlugin(path)

    @err_catcher(name=__name__)
    def loadPlugin(self, path):
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

        initmodule = "Prism_%s_init" % pluginName
        pluginPath = os.path.join(path, "Scripts")
        initPath = os.path.join(pluginPath, initmodule + ".py")

        inactivePluginNames = self.core.getConfig("plugins", "inactive", dft=[])
        if pluginName in inactivePluginNames:
            self.core.inactivePlugins[pluginName] = pluginPath
            logger.debug("skipped loading plugin %s - plugin is set as inactive in the preferences" % pluginName)
            return

        if os.path.basename(os.path.dirname(path)) == "Apps":
            if pluginName == self.core.appPlugin.pluginName:
                return

            if not (
                os.path.exists(initPath)
                or os.path.exists(initPath.replace("_init", "_init_unloaded"))
            ):
                logger.debug("skipped loading plugin %s - plugin has no init script" % pluginName)
                return

            sys.path.append(os.path.dirname(initPath))
            pPlug = getattr(
                __import__("Prism_%s_init_unloaded" % (pluginName)),
                "Prism_%s_unloaded" % pluginName,
            )(self.core)
        else:
            if not os.path.exists(initPath):
                logger.debug("skipped loading plugin %s - plugin has no init script" % pluginName)
                return

            sys.path.append(os.path.dirname(initPath))
            pPlug = getattr(__import__("Prism_%s_init" % (pluginName)), "Prism_%s" % pluginName)(
                self.core
            )

        if platform.system() not in pPlug.platforms:
            logger.debug("skipped loading plugin %s - plugin doesn't support this OS" % pPlug.pluginName)
            return

        if path.startswith(self.core.prismRoot):
            pPlug.location = "prismRoot"
        elif path.startswith(getattr(self.core, "projectPath", ())):
            pPlug.location = "prismProject"
        else:
            pPlug.location = "custom"

        pPlug.pluginPath = pluginPath

        if pPlug.pluginType in ["App"]:
            self.core.unloadedAppPlugins[pPlug.pluginName] = pPlug
        elif pPlug.pluginType in ["Custom"]:
            if pPlug.isActive():
                self.core.customPlugins[pPlug.pluginName] = pPlug
        elif pPlug.pluginType in ["RenderfarmManager"]:
            if pPlug.isActive():
                self.core.rfManagers[pPlug.pluginName] = pPlug
        elif pPlug.pluginType in ["ProjectManager"]:
            if pPlug.isActive():
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

        for plug in curPlugins:
            self.reloadPlugin(plug)

    @err_catcher(name=__name__)
    def reloadPlugin(self, pluginName):
        appPlug = pluginName == self.core.appPlugin.pluginName
        pluginPath = self.unloadPlugin(pluginName)
        if appPlug:
            pluginName = self.getPluginNameFromPath(pluginPath)
            plugin = self.loadAppPlugin(pluginName)
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
    def createPlugin(self, pluginName, pluginType):
        if pluginType == "App":
            presetPath = os.path.join(self.core.prismRoot, "Plugins", "Apps", "PluginEmpty")
        elif pluginType == "Custom":
            presetPath = os.path.join(
                self.core.prismRoot, "Plugins", "Custom", "PluginEmpty"
            )
        elif pluginType == "Projectmanager":
            presetPath = os.path.join(
                self.core.prismRoot, "Plugins", "ProjectManagers", "PluginEmpty"
            )
        elif pluginType == "Renderfarm":
            presetPath = os.path.join(
                self.core.prismRoot, "Plugins", "RenderfarmManagers", "PluginEmpty"
            )

        if not os.path.exists(presetPath):
            QMessageBox.warning(
                self.core.messageParent,
                "Prism",
                "Canceled plugin creation: Empty preset doesn't exist:\n\n%s"
                % self.core.fixPath(presetPath),
            )
            return

        targetPath = os.path.join(os.path.dirname(presetPath), pluginName)

        if os.path.exists(targetPath):
            QMessageBox.warning(
                self.core.messageParent,
                "Prism",
                "Canceled plugin creation: Plugin already exists:\n\n%s" % targetPath,
            )
            return

        shutil.copytree(presetPath, targetPath)

        for i in os.walk(targetPath):
            for folder in i[1]:
                if "PluginEmpty" in folder:
                    folderPath = os.path.join(i[0], folder)
                    newFolderPath = folderPath.replace("PluginEmpty", pluginName)
                    os.rename(folderPath, newFolderPath)

            for file in i[2]:
                filePath = os.path.join(i[0], file)
                with open(filePath, "r") as f:
                    content = f.read()

                with open(filePath, "w") as f:
                    f.write(content.replace("PluginEmpty", pluginName))

                if "PluginEmpty" in filePath:
                    newFilePath = filePath.replace("PluginEmpty", pluginName)
                    os.rename(filePath, newFilePath)

        scriptPath = os.path.join(targetPath, "Scripts")
        if not os.path.exists(scriptPath):
            scriptPath = targetPath

        self.core.openFolder(scriptPath)
        return targetPath
