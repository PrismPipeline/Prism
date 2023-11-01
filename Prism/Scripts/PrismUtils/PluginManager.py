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
import shutil
import platform
import logging
import traceback

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher

logger = logging.getLogger(__name__)


class PluginManager(object):
    def __init__(self, core):
        super(PluginManager, self).__init__()
        self.core = core
        self.monkeyPatchedFunctions = {}
        self.ignoreAutoLoadPlugins = [name.strip() for name in os.getenv("PRISM_IGNORE_AUTOLOAD_PLUGINS", "").split(",")]

    @err_catcher(name=__name__)
    def initializePlugins(self, appPlugin):
        self.core.unloadedAppPlugins = {}
        self.core.customPlugins = {}
        self.core.unloadedPlugins = {}
        self.core.pluginMetaData = {}
        self.renderfarmPlugins = []

        pluginDirs = self.getPluginDirs()
        appPlugs = self.searchPlugins(
            pluginPaths=pluginDirs["pluginPaths"],
            directories=pluginDirs["searchPaths"],
            pluginNames=[appPlugin],
        )
        if not appPlugs:
            msg = "App plugin %s couldn't be found." % appPlugin
            self.core.popup(msg)
            return

        appPlug = self.loadAppPlugin(
            appPlugs[0]["name"], pluginPath=appPlugs[0]["path"], startup=True
        )
        if not appPlug:
            msg = "App plugin %s couldn't be loaded." % appPlugs[0]["name"]
            self.core.popup(msg)
            return

        self.loadPlugins(
            pluginPaths=pluginDirs["pluginPaths"],
            directories=pluginDirs["searchPaths"],
            force=False,
            ignore=[appPlugs[0]["name"]],
        )
        self.core.callback("onPluginsLoaded")
        if self.core.splashScreen:
            self.core.splashScreen.setStatus("plugins loaded...")

        if self.core.appPlugin and self.core.appPlugin.pluginName != "Standalone":
            # self.core.maxwait = 120
            # self.core.elapsed = 0
            self.core.timer = QTimer()
            result = self.core.startup()
            if result is False:
                self.core.timer.timeout.connect(self.core.startup)
                self.core.timer.start(1000)
        else:
            self.core.startup()

    @err_catcher(name=__name__)
    def getPluginDirs(self, includeDefaults=True, includeEnv=True, includeConfig=True, enabledOnly=True):
        result = {"pluginPaths": [], "searchPaths": []}
        if includeDefaults:
            result["searchPaths"] = self.core.pluginDirs[:]

        if includeEnv:
            envPluginDirs = os.getenv("PRISM_PLUGIN_PATHS", "").split(os.pathsep)
            if envPluginDirs[0]:
                result["pluginPaths"] += envPluginDirs

            envPluginSearchDirs = os.getenv("PRISM_PLUGIN_SEARCH_PATHS", "").split(os.pathsep)
            if envPluginSearchDirs[0]:
                result["searchPaths"] += envPluginSearchDirs

        if includeConfig:
            userPluginDirs = self.core.getConfig(config="PluginPaths") or {}
            if userPluginDirs.get("plugins"):
                if enabledOnly:
                    result["pluginPaths"] += [p["path"] for p in userPluginDirs["plugins"] if p.get("enabled", True)]
                else:
                    result["pluginPaths"] += userPluginDirs["plugins"]

            if userPluginDirs.get("searchPaths"):
                if enabledOnly:
                    result["searchPaths"] += [p["path"] for p in userPluginDirs["searchPaths"] if p.get("enabled", True)]
                else:
                    result["searchPaths"] += userPluginDirs["searchPaths"]

        return result

    @err_catcher(name=__name__)
    def setPluginPathEnabled(self, path, enabled):
        userPluginDirs = self.core.getConfig(config="PluginPaths") or {}
        if not userPluginDirs.get("plugins"):
            return False

        for plugin in userPluginDirs["plugins"]:
            if plugin["path"] != path:
                continue

            plugin["enabled"] = enabled
            self.core.setConfig(data=userPluginDirs, config="PluginPaths")
            return True

        return False

    @err_catcher(name=__name__)
    def setPluginSearchPathEnabled(self, path, enabled):
        userPluginDirs = self.core.getConfig(config="PluginPaths") or {}
        if not userPluginDirs.get("plugins"):
            return False

        for plugin in userPluginDirs["searchPaths"]:
            if plugin["path"] != path:
                continue

            plugin["enabled"] = enabled
            self.core.setConfig(data=userPluginDirs, config="PluginPaths")
            return True

        return False

    @err_catcher(name=__name__)
    def getPluginPath(self, location="root", pluginType="", path="", pluginName=""):
        if location == "root":
            pluginPath = os.path.abspath(
                os.path.join(__file__, os.pardir, os.pardir, os.pardir, "Plugins")
            )
        elif location == "computer":
            pluginPath = self.getComputerPluginPath()
        elif location == "user":
            pluginPath = self.getUserPluginPath()
        elif location == "project":
            pluginPath = self.core.projects.getPluginFolder()
        elif location == "custom":
            pluginPath = path

        if location not in ["custom", "user"] and pluginType:
            if pluginType == "App":
                dirName = "Apps"
            elif pluginType == "Custom":
                dirName = "Custom"

            pluginPath = os.path.join(pluginPath, dirName)

        if pluginName:
            pluginPath = os.path.join(pluginPath, pluginName)

        return pluginPath.replace("\\", "/")

    @err_catcher(name=__name__)
    def getUserPluginPath(self):
        pluginPath = os.path.join(os.path.dirname(self.core.userini), "plugins")
        return pluginPath

    @err_catcher(name=__name__)
    def getComputerPluginPath(self):
        pluginPath = os.path.join(self.core.getPrismDataDir(), "plugins")
        return pluginPath

    @err_catcher(name=__name__)
    def getDefaultPluginPath(self):
        path = os.getenv("PRISM_DEFAULT_PLUGIN_PATH")
        if not path:
            path = self.core.getConfig("globals", "defaultPluginPath", config="user")
            if not path:
                path = self.getComputerPluginPath()

        return path

    @err_catcher(name=__name__)
    def getFallbackPluginPath(self):
        path = os.getenv("PRISM_FALLBACK_PLUGIN_PATH")
        if not path:
            path = self.core.getConfig("globals", "fallbackPluginPath", config="user")
            if not path:
                path = self.getUserPluginPath()

        return path

    @err_catcher(name=__name__)
    def loadAppPlugin(self, pluginName, pluginPath=None, startup=False):
        if self.core.splashScreen:
            self.core.splashScreen.setStatus("loading appPlugin %s..." % pluginName)

        if not pluginPath:
            pluginPath = os.path.join(self.core.pluginPathApp, pluginName, "Scripts")
        else:
            if os.path.basename(pluginPath) != "Scripts":
                pluginPath = os.path.join(pluginPath, "Scripts")

        sys.path.append(pluginPath)
        self.core.appPlugin = None
        try:
            appPlug = getattr(
                __import__("Prism_%s_init" % pluginName), "Prism_Plugin_%s" % pluginName
            )(self.core)
        except Exception as e:
            logger.warning(traceback.format_exc())
            msg = "Failed to load app plugin.\nPlease contact the support.\n\n%s" % e
            self.core.popup(msg)
            return

        if not getattr(appPlug, "isActive", lambda: True)():
            logger.debug("no appPlugin loaded")
            return

        self.core.appPlugin = appPlug

        if not self.core.appPlugin:
            msg = "Prism could not initialize correctly and may not work correctly in this session."
            self.core.popup(msg, severity="error")
            return

        if not getattr(self.core.appPlugin, "enabled", True):
            logger.debug("appplugin disabled")
            return

        self.core.appPlugin.location = "prismRoot"
        self.core.appPlugin.pluginPath = pluginPath

        if (
            not getattr(self.core, "messageParent", None)
            and QApplication.instance() is not None
        ):
            for arg in self.core.prismArgs:
                if isinstance(arg, dict) and "messageParent" in arg:
                    self.core.messageParent = arg["messageParent"]
                    break
            else:
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
    def loadPlugins(
        self,
        pluginPaths=None,
        directory=None,
        directories=None,
        recursive=False,
        force=True,
        ignore=None
    ):
        ignore = ignore or []
        result = []
        foundPluginPaths = []

        loadPlugins = None
        for arg in self.core.prismArgs:
            if isinstance(arg, dict) and "loadPlugins" in arg:
                loadPlugins = arg["loadPlugins"]
                force = True
                break

        if pluginPaths:
            for pPath in pluginPaths:
                foundPluginPaths.append(pPath)

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
                                foundPluginPaths.append(path)
                                break
                else:
                    for root, dirs, files in os.walk(dr):
                        for pDir in dirs:
                            if pDir == "PluginEmpty":
                                continue

                            if pDir == self.core.appPlugin.pluginName:
                                continue

                            path = os.path.join(dr, pDir)
                            foundPluginPaths.append(path)
                        break

        for pluginPath in foundPluginPaths:
            if pluginPath.endswith(".py"):
                if loadPlugins:
                    continue
            else:
                pluginName = self.getPluginNameFromPath(pluginPath)
                if pluginName in ignore:
                    continue

                if loadPlugins and pluginName not in loadPlugins:
                    if "loadPluginMetaData" in self.core.prismArgs:
                        self.loadPluginMetaData(pluginPath)
                    continue

                if self.isPluginLoaded(pluginName):
                    continue

            result.append(self.loadPlugin(pluginPath, force=force))

        return result

    @err_catcher(name=__name__)
    def searchPlugins(
        self,
        pluginPaths=None,
        directory=None,
        directories=None,
        recursive=True,
        pluginNames=None,
    ):
        result = []

        if pluginPaths:
            for pPath in pluginPaths:
                pluginName = os.path.basename(pPath)
                if pluginNames and pluginName not in pluginNames:
                    continue

                if not os.path.exists(pPath):
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
                if "Scripts" in dirs:
                    dirs[:] = ["Scripts"]
                    continue

                dirs[:] = [d for d in dirs if d[0] not in [".", "_"]]
                for f in files:
                    if not f.endswith("_init.py"):
                        continue

                    dirs[:] = []
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
        if pluginName in self.core.unloadedPlugins:
            self.core.unloadedPlugins.pop(pluginName)

        logger.debug("activating plugin %s" % pluginName)
        return self.loadPlugin(path)

    @err_catcher(name=__name__)
    def loadPlugin(self, path=None, name=None, force=True, activate=None):
        if not path:
            if name:
                path = self.searchPluginPath(name)
                if not path:
                    logger.debug("couldn't find plugin: %s" % name)
                    return

            if not path:
                logger.debug('invalid pluginpath: "%s"' % path)
                return

        if os.path.normpath(path).startswith(os.path.normpath(self.core.prismRoot)):
            location = "prismRoot"
        elif path.startswith(getattr(self.core, "projectPath", ())):
            location = "prismProject"
        else:
            location = "custom"

        notAutoLoadedPlugins = self.getNotAutoLoadPlugins()

        if path.endswith(".py"):
            dirpath = os.path.dirname(path)
            if dirpath not in sys.path:
                sys.path.append(dirpath)

            pluginName = os.path.basename(os.path.splitext(path)[0]).replace("Prism_Plugin_", "")
            if self.core.splashScreen:
                self.core.splashScreen.setStatus("loading plugin %s..." % pluginName)

            initPath = path
            pluginPath = path
        else:
            if os.path.basename(path) == "Scripts":
                path = os.path.dirname(path)

            pluginName = os.path.basename(path)
            if pluginName == "PluginEmpty":
                return

            if self.core.splashScreen:
                self.core.splashScreen.setStatus("loading plugin %s..." % pluginName)

            if pluginName == "LoadExternalPlugins":
                result = self.core.getConfig("plugins", "load_deprExternalPlugins")
                if result is None:
                    qstr = 'Deprecated plugin found: "LoadExternalPlugins"\nLoading this plugin can cause errors if you haven\'t modified it to work with this Prism version.\n\nAre you sure you want to load this plugin? (if unsure click "No")'
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
                    logger.warning('plugin is already loaded: "%s"' % pluginName)
                    return

            # logger.debug(pluginName)
            initmodule = "Prism_%s_init" % pluginName
            pluginPath = os.path.join(path, "Scripts")
            initPath = os.path.join(pluginPath, initmodule + ".py")

            if pluginName in notAutoLoadedPlugins and not force:
                if not os.path.exists(path):
                    logger.debug("pluginpath doesn't exist: %s" % path)
                    return

                if activate:
                    return self.activatePlugin(path)

                self.core.unloadedPlugins[pluginName] = UnloadedPlugin(self.core, pluginName, path=pluginPath, location=location)
                logger.debug(
                    "skipped loading plugin %s - autoload of this plugin is disabled in the preferences"
                    % pluginName
                )
                return

            if self.core.appPlugin and (pluginName == self.core.appPlugin.pluginName):
                return

            if not (
                os.path.exists(initPath)
                or os.path.exists(initPath.replace("_init", "_init_unloaded"))
            ):
                # self.core.unloadedPlugins[pluginName] = UnloadedPlugin(self.core, pluginName, path=pluginPath, location=location)
                logger.warning(
                    "skipped loading plugin %s - folder doesn't contain a valid plugin (no init script) - check your plugin configuration. %s " % (pluginName, path)
                )
                return

        if os.path.dirname(initPath) not in sys.path:
            sys.path.append(os.path.dirname(initPath))

        try:
            if path.endswith(".py"):
                plugModule = __import__(pluginName)
                if hasattr(plugModule, "name"):
                    pluginName = plugModule.name

                if pluginName in notAutoLoadedPlugins and not force:
                    if not os.path.exists(path):
                        logger.debug("pluginpath doesn't exist: %s" % path)
                        return

                    if activate:
                        return self.activatePlugin(path)

                    self.core.unloadedPlugins[pluginName] = UnloadedPlugin(self.core, pluginName, path=pluginPath, location=location)
                    logger.debug(
                        "skipped loading plugin %s - autoload of this plugin is disabled in the preferences"
                        % pluginName
                    )
                    return

                if hasattr(plugModule, "classname"):
                    classname = plugModule.classname
                else:
                    classname = "Prism_%s" % pluginName

                pPlug = getattr(plugModule, classname)(self.core)
                pPlug.pluginName = pluginName
            elif os.path.exists(initPath.replace("_init", "_init_unloaded")):
                pPlug = getattr(
                    __import__("Prism_%s_init_unloaded" % (pluginName)),
                    "Prism_%s_unloaded" % pluginName,
                )(self.core)
            else:
                pPlug = getattr(
                    __import__("Prism_%s_init" % (pluginName)), "Prism_%s" % pluginName
                )(self.core)
        except:
            msg = "Failed to load plugin: %s" % pluginName
            detailMsg = msg + "\n\n" + traceback.format_exc()
            logger.debug(detailMsg)
            result = self.core.popupQuestion(
                msg,
                buttons=["Details", "Close"],
                icon=QMessageBox.Warning,
                default="Details",
            )

            if result == "Details":
                self.core.showErrorDetailPopup(detailMsg)

            for arg in self.core.prismArgs:
                if isinstance(arg, dict) and "errorCallback" in arg:
                    arg["errorCallback"](detailMsg)
                    break

            self.core.unloadedPlugins[pluginName] = UnloadedPlugin(self.core, pluginName, path=pluginPath, location=location)
            return

        if hasattr(pPlug, "platforms") and platform.system() not in pPlug.platforms:
            logger.debug(
                "skipped loading plugin %s - plugin doesn't support this OS"
                % pPlug.pluginName
            )
            return

        if pluginName in self.core.unloadedPlugins:
            self.core.unloadedPlugins.pop(pluginName)

        pPlug.location = location
        pPlug.pluginPath = pluginPath

        if hasattr(pPlug, "pluginType") and pPlug.pluginType in ["App"]:
            self.core.unloadedAppPlugins[pPlug.pluginName] = pPlug
        else:
            if not getattr(pPlug, "isActive", lambda: True)():
                self.core.unloadedPlugins[pPlug.pluginName] = pPlug
                logger.debug('plugin "%s" is inactive' % pPlug.pluginName)
                return

            if not hasattr(pPlug, "pluginType") or pPlug.pluginType in ["Custom"]:
                self.core.customPlugins[pPlug.pluginName] = pPlug

        if self.core.pb:
            self.core.pb.sceneBrowser.refreshAppFilters()

        self.core.callback("pluginLoaded", args=[pPlug])
        logger.debug("loaded plugin %s" % pPlug.pluginName)
        return pPlug

    @err_catcher(name=__name__)
    def loadPluginMetaData(self, path=None):
        if os.path.basename(path) == "Scripts":
            path = os.path.dirname(path)

        pluginName = os.path.basename(path)
        if pluginName == "PluginEmpty":
            return

        varmodule = "Prism_%s_Variables" % pluginName
        pluginPath = os.path.join(path, "Scripts")
        initPath = os.path.join(pluginPath, varmodule + ".py")

        if not (
            os.path.exists(initPath)
        ):
            logger.debug(
                "skipped loading plugin %s - plugin has no variable script" % initPath
            )
            logger.warning(
                "skipped loading plugin %s - plugin has no variable script" % pluginName
            )
            return

        sys.path.append(os.path.dirname(initPath))
        try:
            pPlug = getattr(
                __import__("Prism_%s_Variables" % (pluginName)), "Prism_%s_Variables" % pluginName
            )(self.core, None)
        except:
            msg = "Failed to load plugin metadata: %s" % pluginName
            result = self.core.popupQuestion(
                msg,
                buttons=["Details", "Close"],
                icon=QMessageBox.Warning,
                default="Details",
            )
            if result == "Details":
                detailMsg = msg + "\n\n" + traceback.format_exc()
                self.core.showErrorDetailPopup(detailMsg)
            return

        if os.path.normpath(path).startswith(os.path.normpath(self.core.prismRoot)):
            pPlug.location = "prismRoot"
        elif path.startswith(getattr(self.core, "projectPath", ())):
            pPlug.location = "prismProject"
        else:
            pPlug.location = "custom"

        pPlug.pluginPath = pluginPath

        self.core.pluginMetaData[pPlug.pluginName] = pPlug

        logger.debug("loaded plugin metadata %s" % pPlug.pluginName)
        return pPlug

    @err_catcher(name=__name__)
    def reloadPlugins(self, plugins=None):
        appPlug = self.core.appPlugin.pluginName

        pluginDicts = [
            self.core.unloadedAppPlugins,
            self.core.customPlugins,
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
        if pluginName in self.core.unloadedPlugins:
            pluginPath = self.core.unloadedPlugins[pluginName].pluginPath
            self.core.unloadedPlugins.pop(pluginName)
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
        self.core.unloadedPlugins[pluginName] = UnloadedPlugin(self.core, pluginName, path=pluginPath, location=plugin.location)
        logger.debug("deactivating plugin %s" % pluginName)
        self.unloadPlugin(pluginName)

    @err_catcher(name=__name__)
    def getNotAutoLoadPlugins(self, configOnly=False):
        plugins = list(self.core.getConfig("plugins", "inactive", dft=[]))
        if not configOnly:
            plugins += self.ignoreAutoLoadPlugins

        plugins = list(set(plugins))
        return plugins

    @err_catcher(name=__name__)
    def getAutoLoadPlugin(self, pluginName):
        inactives = self.getNotAutoLoadPlugins(configOnly=True)
        autoload = pluginName not in inactives
        return autoload

    @err_catcher(name=__name__)
    def setAutoLoadPlugin(self, pluginName, autoload):
        inactives = self.getNotAutoLoadPlugins(configOnly=True)
        if autoload:
            if pluginName in inactives:
                inactives.remove(pluginName)
            else:
                return
        else:
            if pluginName not in inactives:
                inactives.append(pluginName)
            else:
                return

        self.core.setConfig("plugins", "inactive", inactives)

    @err_catcher(name=__name__)
    def unloadPlugin(self, pluginName=None, plugin=None):
        if not plugin:
            plugin = self.getPlugin(pluginName)
        elif not pluginName:
            pluginName = plugin.pluginName

        pluginPath = getattr(plugin, "pluginPath", "")
        self.core.callbacks.unregisterPluginCallbacks(plugin)
        getattr(plugin, "unregister", lambda: None)()

        mods = [
            "Prism_%s_init" % pluginName,
            "Prism_%s_init_unloaded" % pluginName,
            "Prism_%s_Functions" % pluginName,
            "Prism_%s_Integration" % pluginName,
            "Prism_%s_externalAccess_Functions" % pluginName,
            "Prism_%s_Variables" % pluginName,
        ]
        if pluginPath.endswith(".py"):
            mods.append(os.path.splitext(os.path.basename(pluginPath))[0])

        for k in mods:
            try:
                del sys.modules[k]
            except:
                pass

        if pluginPath in sys.path:
            sys.path.remove(pluginPath)

        if pluginName in self.core.unloadedAppPlugins:
            pluginCategory = self.core.unloadedAppPlugins
        elif pluginName in self.core.customPlugins:
            pluginCategory = self.core.customPlugins
        else:
            pluginCategory = None

        if pluginCategory is not None:
            del pluginCategory[pluginName]

        if self.core.appPlugin and pluginName == self.core.appPlugin.pluginName:
            self.unloadAppPlugin()

        if plugin:
            logger.debug("unloaded plugin %s" % plugin.pluginName)
            self.unmonkeyPatchPluginFunctions(plugin)

        return pluginPath

    @err_catcher(name=__name__)
    def unloadAppPlugin(self):
        self.core.appPlugin = None

        try:
            if getattr(self.core, "pb", None) and self.core.pb.isVisible():
                self.core.pb.close()
        except:
            pass

        if getattr(self.core, "sm", None):
            self.core.closeSM()

        try:
            if hasattr(self.core.projects, "dlg_setProject") and self.core.projects.dlg_setProject.isVisible():
                self.core.projects.dlg_setProject.close()
        except:
            pass

        try:
            if getattr(self.core, "ps", None) and self.core.ps.isVisible():
                self.core.ps.close()
        except:
            pass

        self.core.pb = None
        self.core.sm = None
        self.core.ps = None
        self.core.projects.dlg_setProject = None

    @err_catcher(name=__name__)
    def getPluginMetaData(self):
        return self.core.pluginMetaData

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
        elif base.endswith(".py"):
            base = os.path.splitext(base)[0]

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
    def getPlugin(self, pluginName, allowUnloaded=False):
        if self.core.appPlugin and pluginName == self.core.appPlugin.pluginName:
            return self.core.appPlugin
        else:
            for i in self.core.unloadedAppPlugins:
                if i == pluginName:
                    return self.core.unloadedAppPlugins[i]

            if pluginName in self.core.customPlugins:
                return self.core.customPlugins[pluginName]

            if allowUnloaded:
                return self.getUnloadedPlugin(pluginName)

        return None

    @err_catcher(name=__name__)
    def isPluginLoaded(self, pluginName):
        loaded = bool(self.getPlugin(pluginName))
        return loaded

    @err_catcher(name=__name__)
    def getUnloadedPlugins(self):
        return self.core.unloadedPlugins

    @err_catcher(name=__name__)
    def getUnloadedPlugin(self, pluginName):
        for unloadedName in self.core.unloadedPlugins:
            if unloadedName == pluginName:
                return self.core.unloadedPlugins[unloadedName]

    @err_catcher(name=__name__)
    def removeUnloadedPlugin(self, pluginName):
        if pluginName in self.core.unloadedPlugins:
            del self.core.unloadedPlugins[pluginName]

        self.setAutoLoadPlugin(pluginName, True)

    @err_catcher(name=__name__)
    def getLoadedPlugins(self):
        appPlugs = {}
        if self.core.appPlugin:
            appPlugs[self.core.appPlugin.pluginName] = self.core.appPlugin

        appPlugs.update(self.core.unloadedAppPlugins)
        plugs = {
            "App": appPlugs,
            "Custom": self.core.customPlugins,
        }
        return plugs

    @err_catcher(name=__name__)
    def getPlugins(self):
        plugins = self.getLoadedPlugins()
        plugins["inactive"] = self.getUnloadedPlugins()
        return plugins

    @err_catcher(name=__name__)
    def registerRenderfarmPlugin(self, plugin):
        if not plugin or plugin in self.renderfarmPlugins:
            return False

        self.renderfarmPlugins.append(plugin)
        return True

    @err_catcher(name=__name__)
    def unregisterRenderfarmPlugin(self, plugin):
        if not plugin or plugin not in self.renderfarmPlugins:
            return False

        self.renderfarmPlugins.remove(plugin)
        return True

    @err_catcher(name=__name__)
    def getRenderfarmPlugins(self):
        return self.renderfarmPlugins

    @err_catcher(name=__name__)
    def getRenderfarmPlugin(self, name):
        plugins = [p for p in self.renderfarmPlugins if p.pluginName == name]
        if not plugins:
            return

        return plugins[0]

    @err_catcher(name=__name__)
    def createPlugin(self, pluginName, pluginType, location="root", path=""):
        presetPath = self.getPluginPath("root", pluginType)
        presetPath = os.path.join(presetPath, "PluginEmpty")

        if not os.path.exists(presetPath):
            msg = (
                "Canceled plugin creation: Empty preset doesn't exist:\n\n%s"
                % self.core.fixPath(presetPath)
            )
            self.core.popup(msg)
            return

        targetPath = self.getPluginPath(location, pluginType, path, pluginName)

        if os.path.exists(targetPath):
            msg = "Canceled plugin creation: Plugin already exists:\n\n%s" % targetPath
            self.core.popup(msg)
            return

        try:
            shutil.copytree(presetPath, targetPath)
        except PermissionError:
            msg = "Failed to copy files to: \"%s\"\n\nMake sure you have the required permissions and try again." % targetPath
            self.core.popup(msg)
            return

        self.core.replaceFolderContent(targetPath, "PluginEmpty", pluginName)

        scriptPath = os.path.join(targetPath, "Scripts")
        if not os.path.exists(scriptPath):
            scriptPath = targetPath

        self.core.openFolder(scriptPath)
        return targetPath

    @err_catcher(name=__name__)
    def addToPluginConfig(self, pluginPath=None, searchPath=None, idx=0):
        if pluginPath:
            pluginPath = os.path.normpath(pluginPath)

        if searchPath:
            searchPath = os.path.normpath(searchPath)

        userPluginConfig = self.core.getConfig(config="PluginPaths") or {}
        if "plugins" not in userPluginConfig:
            userPluginConfig["plugins"] = []

        if "searchPaths" not in userPluginConfig:
            userPluginConfig["searchPaths"] = []

        if pluginPath:
            userPluginConfig["plugins"] = [path for path in userPluginConfig["plugins"] if path["path"] != pluginPath]
            pluginData = {"path": pluginPath}
            if idx == -1:
                userPluginConfig["plugins"].append(pluginData)
            else:
                userPluginConfig["plugins"].insert(idx, pluginData)

        if searchPath:
            userPluginConfig["searchPaths"] = [path for path in userPluginConfig["searchPaths"] if path["path"] != pluginPath]
            pathData = {"path": searchPath}
            if idx == -1:
                userPluginConfig["searchPaths"].append(pathData)
            else:
                userPluginConfig["searchPaths"].insert(idx, pathData)

        self.core.setConfig(data=userPluginConfig, config="PluginPaths")

    @err_catcher(name=__name__)
    def removeFromPluginConfig(self, pluginPaths=None, searchPaths=None):
        if pluginPaths:
            pluginPaths = [os.path.normpath(pluginPath) for pluginPath in pluginPaths]

        if searchPaths:
            searchPaths = [os.path.normpath(searchPath) for searchPath in searchPaths]

        userPluginConfig = self.core.getConfig(config="PluginPaths") or {}
        if "plugins" not in userPluginConfig:
            userPluginConfig["plugins"] = []

        if "searchPaths" not in userPluginConfig:
            userPluginConfig["searchPaths"] = []

        if pluginPaths:
            newPluginPaths = []
            for path in userPluginConfig["plugins"]:
                if path["path"] not in pluginPaths:
                    newPluginPaths.append(path)
        else:
            newPluginPaths = userPluginConfig["plugins"]

        if searchPaths:
            newSearchPaths = []
            for path in userPluginConfig["searchPaths"]:
                if path["path"] not in searchPaths:
                    newSearchPaths.append(path)
                    break
        else:
            newSearchPaths = userPluginConfig["searchPaths"]

        if len(userPluginConfig["plugins"]) == len(newPluginPaths) and len(userPluginConfig["searchPaths"]) == newSearchPaths:
            return False

        userPluginConfig["plugins"] = newPluginPaths
        userPluginConfig["searchPaths"] = newSearchPaths
        self.core.setConfig(data=userPluginConfig, config="PluginPaths")
        return True

    @err_catcher(name=__name__)
    def canPluginBeFound(self, pluginPath):
        pluginPath = os.path.normpath(pluginPath)
        userPluginConfig = self.core.getConfig(config="PluginPaths") or {}
        if "plugins" in userPluginConfig:
            for path in userPluginConfig["plugins"]:
                if pluginPath == path["path"] and path.get("enabled", True):
                    return True

        if "searchPaths" in userPluginConfig:
            parent = os.path.dirname(pluginPath)
            for path in userPluginConfig["searchPaths"]:
                if parent == path["path"] and path.get("enabled", True):
                    return True

        return False

    @err_catcher(name=__name__)
    def searchPluginPath(self, pluginName):
        userPluginConfig = self.core.getConfig(config="PluginPaths") or {}
        if "plugins" in userPluginConfig:
            for path in userPluginConfig["plugins"]:
                if not path.get("enabled", True):
                    continue

                if pluginName == os.path.basename(path["path"]):
                    return path["path"]

        if "searchPaths" in userPluginConfig:
            for path in userPluginConfig["searchPaths"]:
                if not path.get("enabled", True):
                    continue

                pluginNames = os.listdir(path["path"])
                if pluginName in pluginNames:
                    path = os.path.join(path["path"], pluginName)
                    return path

        pluginDirs = self.getPluginDirs()
        dirs = [folder for folder in pluginDirs["searchPaths"] if folder not in userPluginConfig.get("searchPaths", [])]
        plugins = self.searchPlugins(
            directories=dirs,
            pluginNames=[pluginName],
        )

        if plugins:
            return plugins[0]["path"]

        return False

    @err_catcher(name=__name__)
    def getFunctionInfo(self, function):
        functionId = "%s.%s" % (function.__module__, function.__name__)
        if sys.version[0] == "3":
            if hasattr(function, "__self__"):
                origClass = function.__self__
                functionId += "." + str(id(origClass))
            else:
                origClass = sys.modules[function.__module__]            
        else:
            if hasattr(function, "im_self"):
                origClass = function.im_self
                functionId += "." + str(id(origClass))
            else:
                origClass = sys.modules[function.__module__]

        info = {
            "id": functionId,
            "class": origClass
        }
        return info

    @err_catcher(name=__name__)
    def monkeyPatch(self, orig, new, plugin, quiet=False, force=False):
        functionInfo = self.getFunctionInfo(orig)
        functionId = functionInfo["id"]
        origClass = functionInfo["class"]

        if functionId in self.monkeyPatchedFunctions:
            if force:
                self.core.plugins.unmonkeyPatchFunction(self.monkeyPatchedFunctions[functionId])
                logger.debug("replacing existing monkeypatch for %s" % functionId)
            else:
                if not quiet:
                    self.core.popup(
                        "Function %s is already monkeypatched and cannot get monkeypatched again by plugin %s."
                        % (functionId, plugin.pluginName)
                    )
                return

        setattr(origClass, orig.__name__, new)
        self.monkeyPatchedFunctions[functionId] = {
            "id": functionId,
            "orig": orig,
            "new": new,
            "plugin": plugin,
        }

    @err_catcher(name=__name__)
    def unmonkeyPatchFunction(self, functionData):
        if sys.version[0] == "3":
            if hasattr(functionData["orig"], "__self__"):
                origClass = functionData["orig"].__self__
            else:
                origClass = sys.modules[functionData["orig"].__module__]  
        else:
            if hasattr(functionData["orig"], "im_self"):
                origClass = functionData["orig"].im_self
            else:
                origClass = sys.modules[functionData["orig"].__module__]

        setattr(origClass, functionData["orig"].__name__, functionData["orig"])
        self.monkeyPatchedFunctions.pop(functionData["id"])

    @err_catcher(name=__name__)
    def unmonkeyPatchPluginFunctions(self, plugin):
        funcs = []
        for func in self.monkeyPatchedFunctions:
            if self.monkeyPatchedFunctions[func]["plugin"] == plugin:
                funcs.append(self.monkeyPatchedFunctions[func])

        for func in funcs:
            self.unmonkeyPatchFunction(func)

    @err_catcher(name=__name__)
    def isFunctionMonkeyPatched(self, function, plugin=None):
        patch = self.getFunctionPatch(function)
        if not patch:
            return False

        if not plugin:
            return True

        if patch["plugin"] == plugin:
            return True
        else:
            return False

    @err_catcher(name=__name__)
    def getFunctionPatch(self, function, preferredPatchers=None):
        patches = []
        for f in self.monkeyPatchedFunctions.values():
            if f["new"] == function:
                patches.append(f)

                if preferredPatchers:
                    for f2 in self.monkeyPatchedFunctions.values():
                        if f2["orig"] == f["new"]:
                            patches.append(f2)

        if preferredPatchers:
            for pref in preferredPatchers:
                for patch in patches:
                    if patch["plugin"].pluginName == pref:
                        return patch["new"]

        return patches[0]["orig"] if patches else None

    @err_catcher(name=__name__)
    def callUnpatchedFunction(self, function, *args, **kwargs):
        patch = self.getFunctionPatch(function, preferredPatchers=kwargs.get("preferredPatchers"))
        if patch:
            if "preferredPatchers" in kwargs:
                del kwargs["preferredPatchers"]

            return patch(*args, **kwargs)
        else:
            mid = self.getFunctionInfo(function)["id"]
            logger.debug("failed to call unpatched function for: %s" % mid)

        return False

    @err_catcher(name=__name__)
    def installHub(self):
        updates = []
        self.installHubMsg = self.core.waitPopup(
            self.core, "Installing Hub - please wait..\n\n\n"
        )
        with self.installHubMsg:
            if not self.core.getPlugin("PrismInternals"):
                self.installHubMsg.msg.setText("Installing Hub - please wait..\n\nDownloading PrismInternals...")
                QApplication.processEvents()
                zipPath = self.downloadPlugin("PrismInternals")
                if zipPath:
                    target = os.path.join(self.getDefaultPluginPath(), "PrismInternals")
                    updates.append({"target": target, "zip": zipPath})

            if not self.core.getPlugin("Hub"):
                self.installHubMsg.msg.setText("Installing Hub - please wait..\n\nDownloading Hub...")
                QApplication.processEvents()
                zipPath = self.downloadPlugin("Hub")
                if zipPath:
                    target = os.path.join(self.getDefaultPluginPath(), "Hub")
                    updates.append({"target": target, "zip": zipPath})

            if updates:
                self.installHubMsg.msg.setText("Installing Hub - please wait..\n\nInstalling plugins...")
                QApplication.processEvents()
                self.updatePlugins(updates)

    @err_catcher(name=__name__)
    def downloadPlugin(self, plugin):
        path = self.getDefaultPluginPath()
        data = {
            "key": plugin,
            "origin": "prismOss",
            "prism_version": self.core.version
        }
        serverUrl = "https://service.prism-pipeline.com"
        if plugin == "Hub":
            url = serverUrl + "/api/service/links/plugins/hub"
        elif plugin == "PrismInternals":
            url = serverUrl + "/api/service/links/plugins/prisminternals"

        import requests
        response = requests.get(url, data)
        if not isinstance(response, requests.Response):
            raise Exception("Failed to connect to server.")

        if response.status_code != 200:
            raise Exception("Failed to connect to server. Code %s" % response.status_code)

        try:
            result = response.json()
        except:
            raise Exception(str(response.content))

        if result.get("error"):
            raise Exception("Error in response: %s" % result.get("error"))

        file = result["files"][0]
        cachePath = os.path.join(path, ".cache")
        zippath = os.path.join(cachePath, os.path.basename(file["url"]))
        try:
            response = requests.get(file["url"], headers=file["headers"])
        except Exception:
            return

        data = response.content
        if not data:
            return

        if not os.path.exists(os.path.dirname(zippath)):
            try:
                os.makedirs(os.path.dirname(zippath))
            except Exception:
                return

        try:
            with open(zippath, "wb") as f:
                f.write(data)
        except Exception:
            pass
        else:
            return zippath

    def updatePlugins(self, pluginUpdates):
        import importlib
        pluginNames = []
        basePath = ""
        zipfile = importlib.import_module("zipfile")
        for pluginUpdate in pluginUpdates:
            if os.path.exists(pluginUpdate.get("target")):
                self.removePlugin(pluginUpdate.get("target"))

            try:
                with zipfile.ZipFile(pluginUpdate.get("zip"), "r") as zip_ref:
                    zip_ref.extractall(os.path.dirname(pluginUpdate.get("target")))
            except:
                pass
            else:
                pluginNames.append(os.path.basename(pluginUpdate.get("target")))
                basePath = os.path.dirname(pluginUpdate.get("target"))

        if pluginNames and basePath:
            self.postInstallPlugins(pluginNames, basePath)

    @err_catcher(name=__name__)
    def removePlugin(self, pluginPath):
        bkpPath = self.backupPlugin(pluginPath)
        while os.path.exists(pluginPath):
            try:
                shutil.rmtree(pluginPath, ignore_errors=True)
                if os.path.exists(pluginPath):
                    delBasePath = os.path.join(os.path.dirname(pluginPath), ".delete")
                    if not os.path.exists(delBasePath):
                        try:
                            os.makedirs(delBasePath)
                        except Exception:
                            self.restorePluginFromBackup(bkpPath)
                            msg = "Could not uninstall the plugin.\n\nFailed to create folder:\n%s" % delBasePath
                            self.core.popup(msg)
                            return

                    delPath = os.path.join(delBasePath, os.path.basename(pluginPath))
                    while os.path.exists(delPath):
                        num = delPath.rsplit("_", 1)[-1]
                        try:
                            intnum = int(num)
                            base = delPath.rsplit("_", 1)[0]
                        except:
                            intnum = 0
                            base = delPath

                        delPath = base + "_" + str(intnum + 1)

                    logger.debug("moving from %s to %s" % (pluginPath, delPath))
                    idx = 1
                    while True:
                        try:
                            os.rename(pluginPath, delPath)
                            break
                        except Exception as e:
                            logger.debug(e)
                            idx += 1

                        if idx > 3:
                            msg = "Could not uninstall the plugin.\n\nFailed to remove folder:\n%s" % pluginPath
                            result = self.core.popupQuestion(msg, buttons=["Retry", "Cancel"], escapeButton="Cancel", icon=QMessageBox.Warning)
                            if result != "Retry":
                                self.restorePluginFromBackup(bkpPath)
                                return

                            break

                    folders = self.core.getConfig("foldersToDelete", config="user") or []
                    folders.append(delPath)
                    self.core.setConfig("foldersToDelete", val=folders, config="user")
            except Exception as e:
                logger.debug(e)
                msg = "Could not uninstall the plugin.\n\nFailed to remove folder:\n%s" % pluginPath
                result = self.core.popupQuestion(msg, buttons=["Retry", "Cancel"], escapeButton="Cancel", icon=QMessageBox.Warning)
                if result != "Retry":
                    self.restorePluginFromBackup(bkpPath)
                    return

        self.clearPluginBackup(bkpPath)
        return True

    @err_catcher(name=__name__)
    def getNonExistentPath(self, path):
        newPath = path
        while os.path.exists(newPath):
            num = newPath.rsplit("_", 1)[-1]
            try:
                intnum = int(num)
                base = newPath.rsplit("_", 1)[0]
            except:
                intnum = 0
                base = newPath

            newPath = base + "_" + str(intnum + 1)

        return newPath

    @err_catcher(name=__name__)
    def backupPlugin(self, pluginPath):
        bkpPath = os.path.join(os.path.dirname(pluginPath), ".backup", os.path.basename(pluginPath))
        bkpPath = self.getNonExistentPath(bkpPath)
        bkpPathSub = os.path.join(bkpPath, os.path.basename(pluginPath))
        logger.debug("backing up plugin: %s - %s" % (pluginPath, bkpPath))
        shutil.copytree(pluginPath, bkpPathSub)
        return bkpPath

    @err_catcher(name=__name__)
    def clearPluginBackup(self, backupPath):
        try:
            shutil.rmtree(backupPath)
        except Exception as e:
            logger.warning("failed to delete backup: %s - %s" % (backupPath, e))

    @err_catcher(name=__name__)
    def restorePluginFromBackup(self, backupPath):
        if not backupPath or not os.path.exists(backupPath):
            return

        logger.debug("restoring plugin from backup: %s" % backupPath)
        target = os.path.dirname(os.path.dirname(backupPath))
        for root, folders, files in os.walk(backupPath):
            for folder in folders:
                targetFolder = root.replace(backupPath, target) + "/" + folder
                if not os.path.exists(targetFolder):
                    try:
                        os.makedirs(targetFolder)
                    except Exception as e:
                        logger.warning("failed to create folder from backup: %s" % str(e))

            for file in files:
                targetFile = root.replace(backupPath, target) + "/" + file
                if not os.path.exists(targetFile):
                    bkpFile = os.path.join(root, file)
                    try:
                        shutil.copy2(bkpFile, targetFile)
                    except Exception as e:
                        logger.warning("failed to create file from backup: %s" % str(e))

        self.clearPluginBackup(backupPath)

    @err_catcher(name=__name__)
    def postInstallPlugins(self, plugins, basepath, load=True):
        for pluginName in plugins:
            pluginPath = os.path.join(basepath, pluginName)
            if not self.core.plugins.canPluginBeFound(pluginPath):
                self.core.plugins.addToPluginConfig(pluginPath=pluginPath)

            if load:
                plug = self.core.plugins.loadPlugin(pluginPath)
                appType = getattr(plug, "appType", None)
                if appType != "standalone" and getattr(plug, "pluginType", None) == "App" and getattr(plug, "hasIntegration", None) is not False:
                    msg = "To use the plugin <b>%s</b> you need to setup the Prism integration.<br><br>Would you like to setup the integration now?" % pluginName
                    result = self.core.popupQuestion(msg)
                    if result == "Yes":
                        self.setupIntegrations(pluginName)

            logger.debug("installed plugin %s to %s" % (pluginName, basepath))

        if load and plugins and getattr(self.core, "ps", None) and self.core.ps.isVisible():
            self.core.ps.w_user.reload()

        if self.core.ps:
            self.core.ps.w_user.refreshPlugins()

        if self.core.pb:
            self.core.pb.close()
            self.core.pb = None
            self.core.projectBrowser()

        return True

    @err_catcher(name=__name__)
    def setupIntegrations(self, plugin):
        installer = self.core.getInstaller([plugin])
        installer.installShortcuts = False
        installer.exec_()


class UnloadedPlugin(object):
    def __init__(self, core, pluginName, path="", location=""):
        self.core = core
        self.version = ""
        self.pluginName = pluginName
        self.pluginPath = path
        self.pluginType = ""
        self.appShortName = ""
        self.location = location
