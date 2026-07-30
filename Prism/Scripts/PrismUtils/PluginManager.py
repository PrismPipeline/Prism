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
import threading
import traceback
from typing import Any, Optional, List, Dict, Tuple, Union, Callable

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher

logger = logging.getLogger(__name__)


class DelayedPluginLoader(QThread):
    """Background thread that imports delayed plugins without blocking the main thread."""

    allImportsDone = Signal()

    def __init__(self, pluginManager, pluginPaths):
        super(DelayedPluginLoader, self).__init__()
        self.pluginManager = pluginManager
        self.pluginPaths = pluginPaths

    def run(self):
        logger.debug("loading %d delayed plugin(s)..." % len(self.pluginPaths))
        for pluginPath in self.pluginPaths:
            self.pluginManager.loadPlugin(pluginPath, force=False)
        self.allImportsDone.emit()


class PluginManager(object):
    """Manages Prism plugins and their lifecycle."""
    
    def __init__(self, core: Any) -> None:
        """Initialize the PluginManager.
        
        Args:
            core: Reference to the Prism core instance.
        """
        super(PluginManager, self).__init__()
        self.core = core
        self.monkeyPatchedFunctions = {}
        self.ignoreAutoLoadPlugins = [name.strip() for name in os.getenv("PRISM_IGNORE_AUTOLOAD_PLUGINS", "").split(",")]
        self._delayedPluginPaths = []
        self._delayedLoader = None
        self._delayedExcludePlugins = set()

    @err_catcher(name=__name__)
    def initializePlugins(self, appPlugin: str) -> None:
        """Initialize and load all plugins for a Prism session.
        
        Searches for and loads the specified app plugin first, then loads all other
        plugins from configured paths. Triggers startup callbacks after loading.
        
        Args:
            appPlugin: Name of the app plugin to load (e.g., 'Standalone', 'Maya', 'Houdini').
        """
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

        _envDelayed = os.getenv("PRISM_DELAYED_LOAD_PLUGINS")
        if _envDelayed is not None:
            _rawDelayedStr = _envDelayed
        else:
            _rawDelayedStr = self.core.getConfig("globals", "deferred_plugins", config="user", dft="")

        delayedLoad, _excludes = self.getDelayedLoadPlugins()
        self._delayedExcludePlugins = _excludes if delayedLoad else set()
        self.loadPlugins(
            pluginPaths=pluginDirs["pluginPaths"],
            directories=pluginDirs["searchPaths"],
            force=False,
            ignore=[appPlugs[0]["name"]],
            delayedPlugins=delayedLoad,
        )
        if not self._delayedPluginPaths:
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

        if self._delayedPluginPaths:
            self._startDelayedLoader()

    @err_catcher(name=__name__)
    def getDelayedLoadPlugins(self) -> Tuple[Optional[Union[List[str], str]], set]:
        """Get the list of plugins that are set to be loaded in a delayed manner.
        
        Returns:
            Tuple containing the list of delayed load plugins and the set of excluded plugins.
        """
        _envDelayed = os.getenv("PRISM_DELAYED_LOAD_PLUGINS")
        if _envDelayed is not None:
            _rawDelayedStr = _envDelayed
        else:
            _rawDelayedStr = self.core.getConfig("globals", "deferred_plugins", config="user", dft="")

        _rawDelayed = [n.strip() for n in _rawDelayedStr.split(",") if n.strip()]
        _excludes = {n[1:] for n in _rawDelayed if n.startswith("^")}
        _includes = [n for n in _rawDelayed if not n.startswith("^")]
        delayedLoad = "*" if "*" in _includes else _includes
        return delayedLoad, _excludes

    @err_catcher(name=__name__)
    def _startDelayedLoader(self) -> None:
        """Start the background thread to load delayed plugins."""
        paths = list(self._delayedPluginPaths)
        self._delayedPluginPaths = []
        logger.debug("starting delayed load of %d plugin(s)..." % len(paths))
        self._delayedLoader = DelayedPluginLoader(self, paths)
        self._delayedLoader.allImportsDone.connect(self._onAllDelayedPluginsLoaded)
        self._delayedLoader.start()

    @err_catcher(name=__name__)
    def _onAllDelayedPluginsLoaded(self) -> None:
        """Callback when all delayed plugins have been loaded."""
        logger.debug("all delayed plugins loaded")
        if self.core.pb:
            self.core.pb.sceneBrowser.refreshAppFilters()
        self.core.callback("onPluginsLoaded")
        if self.core.splashScreen:
            self.core.splashScreen.setStatus("plugins loaded...")
        self._delayedLoader = None
        if self.core.status == "waitingForDelayedPlugins":
            self.core.status = "postInitializing"
            self.core.callback(name="postInitialize")
            self.core.status = "loaded"

    @err_catcher(name=__name__)
    def getPluginDirs(self, includeDefaults: bool = True, includeEnv: bool = True, includeConfig: bool = True, enabledOnly: bool = True) ->  Dict[str, List[str]]:
        """Get plugin directories from various sources.
        
        Args:
            includeDefaults: Include default plugin directories
            includeEnv: Include PRISM_PLUGIN_PATHS and PRISM_PLUGIN_SEARCH_PATHS env vars
            includeConfig: Include user config plugin paths
            enabledOnly: Only include enabled plugins from config
            
        Returns:
            Dict with 'pluginPaths' and 'searchPaths' lists
        """
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

        if includeConfig and os.getenv("PRISM_USE_PLUGIN_CONFIG", "1") == "1":
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
    def setPluginPathEnabled(self, path: str, enabled: bool) -> bool:
        """Enable or disable a plugin path in user config.
        
        Args:
            path: Plugin path to modify.
            enabled: Whether to enable or disable the path.
            
        Returns:
            bool: True if successful, False otherwise.
        """
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
    def setPluginSearchPathEnabled(self, path: str, enabled: bool) -> bool:
        """Enable or disable a plugin search path in user config.
        
        Args:
            path: Search path to modify.
            enabled: Whether to enable or disable the path.
            
        Returns:
            bool: True if successful, False otherwise.
        """
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
    def getPluginPath(self, location: str = "root", pluginType: str = "", path: str = "", pluginName: str = "") -> str:
        """Get the file system path for a plugin.
        
        Args:
            location: Location type ('root', 'computer', 'user', 'project', 'custom').
            pluginType: Optional plugin type ('App', 'Custom', 'Single File').
            path: Custom path if location is 'custom'.
            pluginName: Optional specific plugin name.
            
        Returns:
            str: Plugin path.
        """
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

        if location not in ["computer", "custom", "user", "project"] and pluginType:
            if pluginType == "App":
                dirName = "Apps"
            elif pluginType == "Custom":
                dirName = "Custom"
            else:
                dirName = ""

            if dirName:
                pluginPath = os.path.join(pluginPath, dirName)

        if pluginName:
            pluginPath = os.path.join(pluginPath, pluginName)
            if pluginType == "Single File":
                pluginPath += ".py"

        return pluginPath.replace("\\", "/")

    @err_catcher(name=__name__)
    def getUserPluginPath(self) -> str:
        """Get the user-specific plugin directory path.
        
        Returns:
            str: User plugin directory path.
        """
        pluginPath = os.path.join(os.path.dirname(self.core.userini), "plugins")
        return pluginPath

    @err_catcher(name=__name__)
    def getComputerPluginPath(self) -> str:
        """Get the computer-specific plugin directory path.
        
        Returns:
            str: Computer plugin directory path.
        """
        pluginPath = os.path.join(self.core.getPrismDataDir(), "plugins")
        return pluginPath

    @err_catcher(name=__name__)
    def getDefaultPluginPath(self) -> str:
        """Get the default plugin installation directory.
        
        Checks environment variable and user config, falls back to computer path.
        
        Returns:
            str: Default plugin directory path.
        """
        path = os.getenv("PRISM_DEFAULT_PLUGIN_PATH")
        if not path:
            path = self.core.getConfig("globals", "defaultPluginPath", config="user")
            if not path:
                if platform.system() == "Windows":
                    path = self.getComputerPluginPath()
                else:
                    path = self.getPluginPath(location="root", pluginType="Custom")

        return path

    @err_catcher(name=__name__)
    def getFallbackPluginPath(self) -> str:
        """Get the fallback plugin directory for failed installations.
        
        Checks environment variable and user config, falls back to user path.
        
        Returns:
            str: Fallback plugin directory path.
        """
        path = os.getenv("PRISM_FALLBACK_PLUGIN_PATH")
        if not path:
            path = self.core.getConfig("globals", "fallbackPluginPath", config="user")
            if not path:
                path = self.getUserPluginPath()

        return path

    @err_catcher(name=__name__)
    def loadAppPlugin(self, pluginName: str, pluginPath: Optional[str] = None, startup: bool = False) -> Optional[Any]:
        """Load the application plugin for the current DCC.
        
        Args:
            pluginName: Name of the app plugin (e.g., 'Maya', 'Houdini').
            pluginPath: Optional path to plugin directory.
            startup: Whether this is being called during Prism startup.
            
        Returns:
            Optional[Any]: Loaded plugin instance, or None if loading failed.
        """
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
        ):
            isHp311 = self.core.appPlugin.pluginName == "Houdini" and sys.version_info.minor == 11
            if isHp311 or QApplication.instance() is not None:
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

        self.core.callback("pluginLoaded", args=[self.core.appPlugin])
        logger.debug("loaded app plugin %s" % pluginName)
        return self.core.appPlugin

    @err_catcher(name=__name__)
    def loadPlugins(
        self,
        pluginPaths: Optional[List[str]] = None,
        directory: Optional[str] = None,
        directories: Optional[List[str]] = None,
        recursive: bool = False,
        force: bool = True,
        ignore: Optional[List[str]] = None,
        singleFilePlugins: bool = False,
        delayedPlugins: Optional[Union[List[str], str]] = None,
    ) -> List[Any]:
        """Load plugins from specified paths or directories.
        
        Args:
            pluginPaths: Specific plugin paths to load
            directory: Single directory to search for plugins
            directories: Multiple directories to search
            recursive: Search subdirectories recursively
            force: Force reload even if already loaded
            ignore: List of plugin names to skip
            singleFilePlugins: Load single-file .py plugins
            delayedPlugins: Plugin names to defer to background thread ('*' for all)
            
        Returns:
            List of loaded plugin instances
        """
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
                expPath = os.path.expandvars(pPath)
                foundPluginPaths.append(expPath)

        directories = directories or []
        if directory:
            directories.append(directory)

        if directories:
            for dr in directories:
                expDr = os.path.expandvars(dr)
                if not os.path.exists(expDr):
                    continue

                if recursive:
                    for root, dirs, files in os.walk(expDr):
                        for f in files:
                            if f.endswith("_init.py"):
                                path = os.path.dirname(root)
                                foundPluginPaths.append(path)
                                break
                else:
                    for root, dirs, files in os.walk(expDr):
                        for pDir in dirs:
                            if pDir == "PluginEmpty":
                                continue

                            if pDir == self.core.appPlugin.pluginName:
                                continue

                            if pDir.startswith(".") or pDir.startswith("_"):
                                continue

                            path = os.path.join(expDr, pDir)
                            foundPluginPaths.append(path)

                        if singleFilePlugins:
                            for file in files:
                                if file.startswith(".") or file.startswith("_"):
                                    continue

                                if not file.endswith(".py"):
                                    continue

                                path = os.path.join(expDr, file)
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

                if delayedPlugins is not None:
                    if delayedPlugins == "*" or pluginName in delayedPlugins:
                        if pluginName not in self._delayedExcludePlugins:
                            self._delayedPluginPaths.append(pluginPath)
                            continue

            result.append(self.loadPlugin(pluginPath, force=force))

        return result

    @err_catcher(name=__name__)
    def searchPlugins(
        self,
        pluginPaths: Optional[List[str]] = None,
        directory: Optional[str] = None,
        directories: Optional[List[str]] = None,
        recursive: bool = True,
        pluginNames: Optional[List[str]] = None,
    ) -> List[Dict[str, str]]:
        """Search for plugins in specified paths.
        
        Args:
            pluginPaths: Optional list of direct plugin folder paths.
            directory: Optional single directory to search.
            directories: Optional list of directories to search.
            recursive: Whether to search recursively. Defaults to True.
            pluginNames: Optional list of specific plugin names to find.
            
        Returns:
            List[Dict[str, str]]: List of dicts with 'name' and 'path' keys.
        """
        result = []

        if pluginPaths:
            for pPath in pluginPaths:
                pluginName = os.path.basename(pPath)
                if pluginNames and pluginName not in pluginNames:
                    continue

                expPath = os.path.expandvars(pPath)
                if not os.path.exists(expPath):
                    continue

                pData = {"name": pluginName, "path": expPath}
                result.append(pData)

        directories = directories or []
        if directory:
            directories.append(directory)

        for dr in directories:
            expDr = os.path.expandvars(dr)
            if not os.path.exists(expDr):
                continue

            for root, dirs, files in os.walk(expDr):
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
    def activatePlugin(self, path: str) -> Optional[Any]:
        """Activate and load a previously deactivated plugin.
        
        Args:
            path: Path to plugin directory.
            
        Returns:
            Optional[Any]: Loaded plugin instance, or None if loading failed.
        """
        if os.path.basename(path) == "Scripts":
            path = os.path.dirname(path)

        pluginName = os.path.basename(path)
        if pluginName in self.core.unloadedPlugins:
            self.core.unloadedPlugins.pop(pluginName)

        logger.debug("activating plugin %s" % pluginName)
        return self.loadPlugin(path)

    @err_catcher(name=__name__)
    def loadPlugin(self, path: Optional[str] = None, name: Optional[str] = None, force: bool = True, activate: Optional[bool] = None, showWarnings: bool = False) -> Optional[Any]:
        """Load a single plugin from path or name.
        
        Args:
            path: Optional path to plugin directory or .py file.
            name: Optional plugin name to search for and load.
            force: Whether to reload if already loaded. Defaults to True.
            activate: Whether to activate if plugin was inactive. Defaults to None.
            showWarnings: Whether to show warning popups. Defaults to False.
            
        Returns:
            Optional[Any]: Loaded plugin instance, or None if loading failed.
        """
        # logger.debug("about to load plugin: %s - %s" % (path, name))
        if not path:
            if name:
                pluginPaths = self.searchPluginPaths(name)
                if not pluginPaths:
                    msg = "couldn't find plugin: %s" % name
                    if showWarnings:
                        self.core.popup(msg)
                    else:
                        logger.debug(msg)

                    return

                for pluginPath in pluginPaths:
                    result = self.loadPlugin(path=pluginPath, name=name, force=force, activate=activate)
                    if result:
                        return result

                return

            if not path:
                msg = "invalid pluginpath: \"%s\"" % path
                if showWarnings:
                    self.core.popup(msg)
                else:
                    logger.debug(msg)

                return

        if os.path.normpath(path).startswith(os.path.normpath(self.core.prismRoot)):
            location = "prismRoot"
        elif path.startswith(getattr(self.core, "projectPath", ())):
            location = "prismProject"
        else:
            location = "custom"

        _qapp = QApplication.instance()
        isGuiThread = bool(_qapp and _qapp.thread() == QThread.currentThread())
        notAutoLoadedPlugins = self.getNotAutoLoadPlugins()

        if path.endswith(".py"):
            dirpath = os.path.dirname(path)
            if dirpath not in sys.path:
                sys.path.append(dirpath)

            pluginName = os.path.basename(os.path.splitext(path)[0]).replace("Prism_Plugin_", "")
            if self.core.splashScreen and isGuiThread:
                self.core.splashScreen.setStatus("loading plugin %s..." % pluginName)

            initPath = path
            pluginPath = path
        else:
            if os.path.basename(path) == "Scripts":
                path = os.path.dirname(path)

            pluginName = os.path.basename(path)
            if pluginName == "PluginEmpty":
                return

            if self.core.splashScreen and isGuiThread:
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
                    msg = "plugin is already loaded: \"%s\"" % pluginName
                    if showWarnings:
                        self.core.popup(msg)
                    else:
                        logger.warning(msg)

                    return

            # logger.debug(pluginName)
            initmodule = "Prism_%s_init" % pluginName
            pluginPath = os.path.join(path, "Scripts")
            initPath = os.path.join(pluginPath, initmodule + ".py")

            if pluginName in notAutoLoadedPlugins and not force:
                if not os.path.exists(path):
                    msg = "pluginpath doesn't exist: %s" % path
                    if showWarnings:
                        self.core.popup(msg)
                    else:
                        logger.debug(msg)

                    return

                if activate:
                    return self.activatePlugin(path)

                self.core.unloadedPlugins[pluginName] = UnloadedPlugin(self.core, pluginName, path=pluginPath, location=location)
                msg = "skipped loading plugin %s - autoload of this plugin is disabled in the preferences" % pluginName
                if showWarnings:
                    self.core.popup(msg)
                else:
                    logger.debug(msg)

                return

            if self.core.appPlugin and (pluginName == self.core.appPlugin.pluginName):
                return

            if not (
                os.path.exists(initPath)
                or os.path.exists(initPath.replace("_init", "_init_unloaded"))
            ):
                # self.core.unloadedPlugins[pluginName] = UnloadedPlugin(self.core, pluginName, path=pluginPath, location=location)
                msg = "skipped loading plugin %s - folder doesn't contain a valid plugin (no init script) - check your plugin configuration. %s " % (pluginName, path)
                if showWarnings:
                    self.core.popup(msg)
                else:
                    logger.debug(msg)

                return

        if os.path.dirname(initPath) not in sys.path:
            sys.path.append(os.path.dirname(initPath))

        try:
            if path.endswith(".py"):
                if not os.path.exists(path):
                    msg = "pluginpath doesn't exist: %s" % path
                    if showWarnings:
                        self.core.popup(msg)
                    else:
                        logger.debug(msg)

                    return

                plugModule = __import__(pluginName)
                if hasattr(plugModule, "name"):
                    pluginName = plugModule.name

                if pluginName in notAutoLoadedPlugins and not force:
                    if activate:
                        return self.activatePlugin(path)

                    self.core.unloadedPlugins[pluginName] = UnloadedPlugin(self.core, pluginName, path=pluginPath, location=location)
                    msg = "skipped loading plugin %s - autoload of this plugin is disabled in the preferences" % pluginName
                    if showWarnings:
                        self.core.popup(msg)
                    else:
                        logger.debug(msg)

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
                default="Close",
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
            msg = "skipped loading plugin %s - plugin doesn't support this OS" % pPlug.pluginName
            if showWarnings:
                self.core.popup(msg)
            else:
                logger.debug(msg)

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
                msg = "plugin \"%s\" is inactive" % pPlug.pluginName
                if showWarnings:
                    self.core.popup(msg)
                else:
                    logger.debug(msg)

                return

            if not hasattr(pPlug, "pluginType") or pPlug.pluginType in ["Custom"]:
                self.core.customPlugins[pPlug.pluginName] = pPlug

        if self.core.pb and isGuiThread:
            self.core.pb.sceneBrowser.refreshAppFilters()

        self.core.callback("pluginLoaded", args=[pPlug])
        logger.debug("loaded plugin %s" % pPlug.pluginName)
        return pPlug

    @err_catcher(name=__name__)
    def loadPluginMetaData(self, path: Optional[str] = None) -> Optional[Any]:
        """Load plugin metadata without loading the full plugin.
        
        Args:
            path: Path to plugin directory.
            
        Returns:
            Optional[Any]: Plugin metadata instance, or None if loading failed.
        """
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
                default="Close",
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
    def reloadPlugins(self, plugins: Optional[List[str]] = None) -> None:
        """Reload multiple plugins.
        
        Args:
            plugins: Optional list of plugin names to reload. Reloads all if None.
        """
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
    def reloadPlugin(self, pluginName: str) -> Optional[Any]:
        """Reload a single plugin.
        
        Args:
            pluginName: Name of plugin to reload.
            
        Returns:
            Optional[Any]: Reloaded plugin instance.
        """
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
    def reloadCustomPlugins(self) -> None:
        """Reload all custom plugins.
        
        Unloads and reloads all modules for custom plugins.
        """
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
    def unloadProjectPlugins(self) -> None:
        """Unload all plugins located in the project directory."""
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
    def deactivatePlugin(self, pluginName: str) -> None:
        """Deactivate a loaded plugin without uninstalling it.
        
        Args:
            pluginName: Name of plugin to deactivate.
        """
        plugin = self.getPlugin(pluginName)
        if not plugin:
            logger.warning("can't find plugin: %s" % pluginName)
            return

        pluginPath = getattr(plugin, "pluginPath", "")
        self.core.unloadedPlugins[pluginName] = UnloadedPlugin(self.core, pluginName, path=pluginPath, location=plugin.location)
        logger.debug("deactivating plugin %s" % pluginName)
        self.unloadPlugin(pluginName)

    @err_catcher(name=__name__)
    def getNotAutoLoadPlugins(self, configOnly: bool = False) -> List[str]:
        """Get list of plugins that should not auto-load.
        
        Args:
            configOnly: If True, only returns config-based inactive plugins.
            
        Returns:
            List[str]: List of plugin names configured not to auto-load.
        """
        plugins = list(self.core.getConfig("plugins", "inactive", dft=[]))
        if not configOnly:
            plugins += self.ignoreAutoLoadPlugins

        plugins = list(set(plugins))
        return plugins

    @err_catcher(name=__name__)
    def getAutoLoadPlugin(self, pluginName: str) -> bool:
        """Check if a plugin is configured to auto-load.
        
        Args:
            pluginName: Name of plugin to check.
            
        Returns:
            bool: True if plugin should auto-load, False otherwise.
        """
        inactives = self.getNotAutoLoadPlugins(configOnly=True)
        autoload = pluginName not in inactives
        return autoload

    @err_catcher(name=__name__)
    def setAutoLoadPlugin(self, pluginName: str, autoload: bool) -> None:
        """Set whether a plugin should auto-load on startup.
        
        Args:
            pluginName: Name of plugin to configure.
            autoload: Whether plugin should auto-load.
        """
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
    def unloadPlugin(self, pluginName: Optional[str] = None, plugin: Optional[Any] = None) -> str:
        """Unload a plugin and clean up its resources.
        
        Args:
            pluginName: Optional name of plugin to unload.
            plugin: Optional plugin instance to unload.
            
        Returns:
            str: Path of unloaded plugin.
        """
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
    def unloadAppPlugin(self) -> None:
        """Unload the current application plugin and close related windows."""
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
    def getPluginMetaData(self) -> Dict[str, Any]:
        """Get metadata for all plugins.
        
        Returns:
            Dict mapping plugin names to their metadata
        """
        return self.core.pluginMetaData

    @err_catcher(name=__name__)
    def getPluginNames(self) -> List[str]:
        """Get names of all available plugins.
        
        Returns:
            Sorted list of plugin names (loaded and unloaded)
        """
        pluginNames = list(self.core.unloadedAppPlugins.keys())
        pluginNames.append(self.core.appPlugin.pluginName)

        return sorted(pluginNames)

    @err_catcher(name=__name__)
    def getPluginNameFromPath(self, path: str) -> str:
        """Extract plugin name from file/directory path.
        
        Args:
            path: Path to plugin file or directory
            
        Returns:
            Plugin name string
        """
        base = os.path.basename(path)
        if base == "Scripts":
            base = os.path.basename(os.path.dirname(path))
        elif base.endswith(".py"):
            base = os.path.splitext(base)[0]

        return base

    @err_catcher(name=__name__)
    def getPluginSceneFormats(self) -> List[str]:
        """Get all scene formats supported by plugins.
        
        Returns:
            List of file extensions (e.g., ['.ma', '.mb', '.blend'])
        """
        pluginFormats = list(self.core.appPlugin.sceneFormats)

        for i in self.core.unloadedAppPlugins.values():
            pluginFormats += i.sceneFormats

        return pluginFormats

    @err_catcher(name=__name__)
    def getPluginData(self, pluginName: str, data: str) -> Any:
        """Get attribute data from a plugin.
        
        Args:
            pluginName: Name of the plugin
            data: Attribute name to retrieve
            
        Returns:
            Attribute value or None if not found
        """
        if pluginName == self.core.appPlugin.pluginName:
            return getattr(self.core.appPlugin, data, None)
        else:
            for i in self.core.unloadedAppPlugins:
                if i == pluginName:
                    return getattr(self.core.unloadedAppPlugins[i], data, None)

        return None

    @err_catcher(name=__name__)
    def getPlugin(self, pluginName: str, allowUnloaded: bool = False) -> Optional[Any]:
        """Get plugin instance by name.
        
        Args:
            pluginName: Name of the plugin to retrieve
            allowUnloaded: If True, include inactive plugins
            
        Returns:
            Plugin instance or None if not found
        """
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
    def isPluginLoaded(self, pluginName: str) -> bool:
        """Check if a plugin is currently loaded.
        
        Args:
            pluginName: Name of the plugin
            
        Returns:
            True if plugin is loaded
        """
        loaded = bool(self.getPlugin(pluginName))
        return loaded

    @err_catcher(name=__name__)
    def getUnloadedPlugins(self) -> Dict[str, Any]:
        """Get all inactive/unloaded plugins.
        
        Returns:
            Dict mapping plugin names to unloaded plugin instances
        """
        return self.core.unloadedPlugins

    @err_catcher(name=__name__)
    def getUnloadedPlugin(self, pluginName: str) -> Optional[Any]:
        """Get a specific unloaded plugin by name.
        
        Args:
            pluginName: Name of the unloaded plugin
            
        Returns:
            Unloaded plugin instance or None
        """
        for unloadedName in self.core.unloadedPlugins:
            if unloadedName == pluginName:
                return self.core.unloadedPlugins[unloadedName]

    @err_catcher(name=__name__)
    def removeUnloadedPlugin(self, pluginName: str) -> None:
        """Remove a plugin from the unloaded plugins list.
        
        Args:
            pluginName: Name of the plugin to remove
        """
        if pluginName in self.core.unloadedPlugins:
            del self.core.unloadedPlugins[pluginName]

        self.setAutoLoadPlugin(pluginName, True)

    @err_catcher(name=__name__)
    def getLoadedPlugins(self) -> Dict[str, Dict[str, Any]]:
        """Get all currently loaded plugins.
        
        Returns:
            Dict with 'App' and 'Custom' keys containing plugin dicts
        """
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
    def getPlugins(self) -> Dict[str, Any]:
        """Get all plugins (loaded and unloaded).
        
        Returns:
            Dict with 'App', 'Custom', and 'inactive' plugin dicts
        """
        plugins = self.getLoadedPlugins()
        plugins["inactive"] = self.getUnloadedPlugins()
        return plugins

    @err_catcher(name=__name__)
    def registerRenderfarmPlugin(self, plugin: Any) -> bool:
        """Register a renderfarm submission plugin.
        
        Args:
            plugin: Renderfarm plugin instance
            
        Returns:
            True if registered successfully
        """
        if not plugin or plugin in self.renderfarmPlugins:
            return False

        self.renderfarmPlugins.append(plugin)
        return True

    @err_catcher(name=__name__)
    def unregisterRenderfarmPlugin(self, plugin: Any) -> bool:
        """Unregister a renderfarm submission plugin.
        
        Args:
            plugin: Renderfarm plugin instance
            
        Returns:
            True if unregistered successfully
        """
        if not plugin or plugin not in self.renderfarmPlugins:
            return False

        self.renderfarmPlugins.remove(plugin)
        return True

    @err_catcher(name=__name__)
    def getRenderfarmPlugins(self) -> List[Any]:
        """Get all registered renderfarm plugins.
        
        Returns:
            List of renderfarm plugin instances
        """
        return self.renderfarmPlugins

    @err_catcher(name=__name__)
    def getRenderfarmPlugin(self, name: str) -> Optional[Any]:
        """Get a specific renderfarm plugin by name.
        
        Args:
            name: Plugin name to find
            
        Returns:
            Renderfarm plugin instance or None
        """
        plugins = [p for p in self.renderfarmPlugins if p.pluginName == name]
        if not plugins:
            return

        return plugins[0]

    @err_catcher(name=__name__)
    def createPlugin(self, pluginName: str, pluginType: str, location: str = "root", path: str = "") -> Optional[str]:
        """Create a new plugin from template.
        
        Args:
            pluginName: Name for the new plugin
            pluginType: Plugin type ('App', 'Custom', 'Single File')
            location: Install location ('root' or custom)
            path: Custom path for plugin
            
        Returns:
            Path to created plugin or None if failed
        """
        targetPath = self.getPluginPath(location, pluginType, path, pluginName)
        if os.path.exists(targetPath):
            msg = "Canceled plugin creation: Plugin already exists:\n\n%s" % targetPath
            self.core.popup(msg)
            return

        if pluginType == "Single File":
            script = """name = "PLUGINNAME"
classname = "PLUGINNAME"


import os
from qtpy.QtWidgets import *


class PLUGINNAME:
    def __init__(self, core):
        self.core = core
        self.version = "v1.0.0"

        self.core.registerCallback("postInitialize", self.postInitialize, plugin=self)

    def postInitialize(self):
        # do stuff after Prism launched
        pass
"""
            script = script.replace("PLUGINNAME", pluginName)
            if not os.path.exists(os.path.dirname(targetPath)):
                os.makedirs(os.path.dirname(targetPath))

            with open(targetPath, "w") as f:
                f.write(script)

            self.core.openFolder(targetPath)
        else:
            presetPath = self.getPluginPath("root", pluginType)
            presetPath = os.path.join(presetPath, "PluginEmpty")
            if not os.path.exists(presetPath):
                msg = (
                    "Canceled plugin creation: Empty preset doesn't exist:\n\n%s"
                    % self.core.fixPath(presetPath)
                )
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
    def addToPluginConfig(self, pluginPath: Optional[str] = None, searchPath: Optional[str] = None, idx: int = 0) -> None:
        """Add plugin or search path to user config.
        
        Args:
            pluginPath: Specific plugin path to add
            searchPath: Search directory path to add
            idx: Insert position (0=first, -1=last)
        """
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
    def removeFromPluginConfig(self, pluginPaths: Optional[List[str]] = None, searchPaths: Optional[List[str]] = None) -> bool:
        """Remove plugin or search paths from user config.
        
        Args:
            pluginPaths: List of plugin paths to remove
            searchPaths: List of search paths to remove
            
        Returns:
            True if config was modified
        """
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
    def canPluginBeFound(self, pluginPath: str) -> bool:
        """Check if plugin path is in search paths or config.
        
        Args:
            pluginPath: Path to check
            
        Returns:
            True if plugin can be found
        """
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
    def searchPluginPath(self, pluginName: str) -> Union[str, bool]:
        """Search for first plugin path by name.
        
        Args:
            pluginName: Name of plugin to find
            
        Returns:
            Plugin path or False if not found
        """
        paths = self.searchPluginPaths(pluginName)
        if paths:
            return paths[0]
        else:
            return False

    @err_catcher(name=__name__)
    def searchPluginPaths(self, pluginName: str) -> Union[List[str], bool]:
        """Search for all plugin paths matching name.
        
        Args:
            pluginName: Name of plugin to find
            
        Returns:
            List of plugin paths or False if none found
        """
        paths = []
        userPluginConfig = self.core.getConfig(config="PluginPaths") or {}
        if "plugins" in userPluginConfig:
            for path in userPluginConfig["plugins"]:
                if not path.get("enabled", True):
                    continue

                if pluginName == os.path.basename(path["path"]):
                    paths.append(path["path"])

        if "searchPaths" in userPluginConfig:
            for path in userPluginConfig["searchPaths"]:
                if not path.get("enabled", True):
                    continue

                pluginNames = os.listdir(path["path"])
                if pluginName in pluginNames:
                    path = os.path.join(path["path"], pluginName)
                    paths.append(path)

        pluginDirs = self.getPluginDirs()
        dirs = [folder for folder in pluginDirs["searchPaths"] if folder not in userPluginConfig.get("searchPaths", [])]
        plugins = self.searchPlugins(
            directories=dirs,
            pluginNames=[pluginName],
        )

        if plugins:
            for plugin in plugins:
                paths.append(plugin["path"])

        if paths:
            npaths = []
            for path in paths:
                if path not in npaths:
                    npaths.append(path)

            paths = npaths
            return paths

        return False

    @err_catcher(name=__name__)
    def getFunctionInfo(self, function: Callable) -> Dict[str, Any]:
        """Get metadata about a function for monkey patching.
        
        Args:
            function: Function to get info for
            
        Returns:
            Dict with 'id' and 'class' keys
        """
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
    def monkeyPatch(self, orig: Callable, new: Callable, plugin: Any, quiet: bool = False, force: bool = False) -> None:
        """Replace a function with a plugin override (monkey patch).
        
        Args:
            orig: Original function to replace
            new: New function to use instead
            plugin: Plugin performing the patch
            quiet: If True, don't show errors
            force: If True, replace existing patches
        """
        functionInfo = self.getFunctionInfo(orig)
        functionId = functionInfo["id"]
        origClass = functionInfo["class"]

        if self.isFunctionMonkeyPatched(orig):
            if force:
                patch = self.getFunctionPatch(orig)
                orig = patch["orig"]
                functionInfo = self.getFunctionInfo(orig)
                functionId = functionInfo["id"]
                origClass = functionInfo["class"]
                self.core.plugins.unmonkeyPatchFunction(patch)
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
    def unmonkeyPatchFunction(self, functionData: Dict[str, Any]) -> None:
        """Remove a monkey patch and restore original function.
        
        Args:
            functionData: Dict with patch info (orig, new, id, plugin)
        """
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
    def unmonkeyPatchPluginFunctions(self, plugin: Any) -> None:
        """Remove all monkey patches applied by a specific plugin.
        
        Args:
            plugin: Plugin instance whose patches to remove
        """
        funcs = []
        for func in self.monkeyPatchedFunctions:
            if self.monkeyPatchedFunctions[func]["plugin"] == plugin:
                funcs.append(self.monkeyPatchedFunctions[func])

        for func in funcs:
            self.unmonkeyPatchFunction(func)

    @err_catcher(name=__name__)
    def isFunctionMonkeyPatched(self, function: Callable, plugin: Optional[Any] = None) -> bool:
        """Check if a function is currently monkey patched.
        
        Args:
            function: Function to check
            plugin: Optionally check if patched by specific plugin
            
        Returns:
            True if function is patched (and by plugin if specified)
        """
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
    def getFunctionPatch(self, function: Callable, preferredPatchers: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Get monkey patch info for a function.
        
        Args:
            function: Function to get patch for
            preferredPatchers: List of preferred plugin names
            
        Returns:
            Patch dict or None if not patched
        """
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

        return patches[0] if patches else None

    @err_catcher(name=__name__)
    def callUnpatchedFunction(self, function: Callable, *args: Any, **kwargs: Any) -> Any:
        """Call the original unpatched version of a function.
        
        Args:
            function: Patched function whose original version to call
            *args: Function arguments
            **kwargs: Function keyword arguments (supports preferredPatchers key)
            
        Returns:
            Return value from original function or False if not found
        """
        patch = self.getFunctionPatch(function, preferredPatchers=kwargs.get("preferredPatchers"))
        if patch:
            if "preferredPatchers" in kwargs:
                del kwargs["preferredPatchers"]

            return patch["orig"](*args, **kwargs)
        else:
            mid = self.getFunctionInfo(function)["id"]
            logger.debug("failed to call unpatched function for: %s" % mid)

        return False

    @err_catcher(name=__name__)
    def installHub(self) -> None:
        """Install Hub and PrismInternals plugins.
        
        Downloads and installs required Hub infrastructure plugins.
        """
        updates = []
        self.installHubMsg = self.core.waitPopup(
            self.core, "Installing Hub - please wait..\n\n\n"
        )
        with self.installHubMsg:
            setPermissions = False
            dataDir = self.core.getPrismDataDir()
            if not os.path.exists(dataDir):
                setPermissions = True

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

            if setPermissions:
                self.core.grantRwToAllUsers(dataDir)

    @err_catcher(name=__name__)
    def downloadPlugin(self, plugin: str) -> Optional[str]:
        """Download a plugin from the Prism service.
        
        Args:
            plugin: Plugin name ('Hub', 'PrismInternals', etc.)
            
        Returns:
            Path to downloaded zip file or None if failed
        """
        path = self.getDefaultPluginPath()
        data = {
            "key": plugin,
            "origin": "prismOss",
            "prism_version": self.core.version,
            "opsystem": platform.system(),
        }
        serverUrl = "https://service.prism-pipeline.com"
        if plugin == "Hub":
            url = serverUrl + "/api/service/links/plugins/hub"
        elif plugin == "PrismInternals":
            url = serverUrl + "/api/service/links/plugins/prisminternals"

        import requests
        response = requests.get(url, data)
        if not isinstance(response, requests.Response):
            self.core.popup("Failed to connect to server.")

        if response.status_code != 200:
            self.core.popup("Failed to connect to server. Code %s" % response.status_code)

        try:
            result = response.json()
        except:
            self.core.popup(str(response.content))

        if result.get("error"):
            self.core.popup("Error in response: %s" % result.get("error"))

        file = result["files"][0]
        cachePath = os.path.join(path, ".cache")
        zippath = os.path.join(cachePath, os.path.basename(file["url"]))
        try:
            response = requests.get(file["url"], headers=file["headers"])
        except Exception as e:
            self.core.popup("Error in request: %s" % str(e))
            return

        data = response.content
        if not data:
            self.core.popup("Empty response.")
            return

        if not os.path.exists(os.path.dirname(zippath)):
            try:
                os.makedirs(os.path.dirname(zippath))
            except Exception:
                self.core.popup("Failed to create folder: %s\n\n%s" % (os.path.dirname(zippath), str(e)))
                return

        try:
            with open(zippath, "wb") as f:
                f.write(data)
        except Exception as e:
            self.core.popup("Failed to write to file:\n\n%s" % str(e))
        else:
            return zippath

    def updatePlugins(self, pluginUpdates: List[Dict[str, str]]) -> None:
        """Extract and install plugin updates from zip/tar files.
        
        Args:
            pluginUpdates: List of dicts with 'target' and 'zip' keys
        """
        import importlib
        pluginNames = []
        basePath = ""
        zipfile = importlib.import_module("zipfile")
        tarfile = importlib.import_module("tarfile")
        for pluginUpdate in pluginUpdates:
            if os.path.exists(pluginUpdate.get("target")):
                self.removePlugin(pluginUpdate.get("target"))

            try:
                target = os.path.dirname(pluginUpdate.get("target"))
                zippath = pluginUpdate.get("zip")
                if zippath.lower().endswith(".zip"):
                    with zipfile.ZipFile(zippath, "r") as zip_ref:
                        zip_ref.extractall(target)
                elif zippath.lower().endswith(".tar.gz"):
                    with tarfile.open(zippath, 'r') as tar:
                        tar.extractall(target)
            except:
                pass
            else:
                pluginNames.append(os.path.basename(pluginUpdate.get("target")))
                basePath = os.path.dirname(pluginUpdate.get("target"))

        if pluginNames and basePath:
            self.postInstallPlugins(pluginNames, basePath)

    @err_catcher(name=__name__)
    def removePlugin(self, pluginPath: str) -> bool:
        """Remove a plugin directory.
        
        Backs up plugin before removal.
        
        Args:
            pluginPath: Path to plugin directory to remove
            
        Returns:
            True if successful
        """
        if not pluginPath or not os.path.exists(pluginPath):
            return True

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
    def getNonExistentPath(self, path: str) -> str:
        """Get non-existent path by appending incremental number.
        
        Args:
            path: Base path
            
        Returns:
            Path with _N suffix that doesn't exist
        """
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
    def backupPlugin(self, pluginPath: str) -> str:
        """Create backup of plugin before update/install.
        
        Args:
            pluginPath: Path to plugin directory
            
        Returns:
            Path to backup directory
        """
        bkpPath = os.path.join(os.path.dirname(pluginPath), ".backup", os.path.basename(pluginPath))
        bkpPath = self.getNonExistentPath(bkpPath)
        bkpPathSub = os.path.join(bkpPath, os.path.basename(pluginPath))
        logger.debug("backing up plugin: %s - %s" % (pluginPath, bkpPath))
        while True:
            try:
                shutil.copytree(pluginPath, bkpPathSub)
            except Exception as e:
                result = self.core.popupQuestion(f"Failed to backup folder: {e}", buttons=["Retry", "Skip"], default="Skip", escapeButton="Skip", icon=QMessageBox.Warning)
                if result != "Retry":
                    break
            else:
                break

        return bkpPath

    @err_catcher(name=__name__)
    def clearPluginBackup(self, backupPath: str) -> None:
        """Delete plugin backup directory.
        
        Args:
            backupPath: Path to backup directory
        """
        try:
            shutil.rmtree(backupPath)
        except Exception as e:
            logger.warning("failed to delete backup: %s - %s" % (backupPath, e))

    @err_catcher(name=__name__)
    def restorePluginFromBackup(self, backupPath: str) -> None:
        """Restore plugin from backup directory after failed install.
        
        Args:
            backupPath: Path to backup directory
        """
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
    def postInstallPlugins(self, plugins: List[str], basepath: str, load: bool = True, parent: Any = None) -> bool:
        """Post-installation tasks for plugins - add to config, load, setup integrations.
        
        Args:
            plugins: List of plugin directory names
            basepath: Base directory containing plugins
            load: Whether to load plugins. Defaults to True.
            parent: Parent widget for dialogs. Defaults to None.
            
        Returns:
            True on success
        """
        for pluginName in plugins:
            pluginPath = os.path.join(basepath, pluginName)
            if not self.core.plugins.canPluginBeFound(pluginPath):
                self.core.plugins.addToPluginConfig(pluginPath=pluginPath)

            if load:
                plug = self.core.plugins.loadPlugin(pluginPath)
                appType = getattr(plug, "appType", None)
                if appType != "standalone" and getattr(plug, "pluginType", None) == "App" and getattr(plug, "hasIntegration", None) is not False:
                    msg = "To use the plugin <b>%s</b> you need to setup the Prism integration.<br><br>Would you like to setup the integration now?" % pluginName
                    result = self.core.popupQuestion(msg, parent=parent)
                    if result == "Yes":
                        self.setupIntegrations(pluginName, parent=parent)

                if hasattr(plug, "postInstall"):
                    plug.postInstall()

            logger.debug("installed plugin %s to %s" % (pluginName, basepath))

        if load and plugins and getattr(self.core, "ps", None) and self.core.ps.isVisible():
            self.core.ps.w_user.reload()

        if self.core.ps:
            self.core.ps.w_user.refreshPlugins()

        return True

    @err_catcher(name=__name__)
    def setupIntegrations(self, plugin: str, parent: Any = None) -> None:
        """Open installer dialog to setup DCC integrations for a plugin.
        
        Args:
            plugin: Plugin name
            parent: Parent widget for dialog. Defaults to None.
        """
        installer = self.core.getInstaller([plugin], parent=parent)
        installer.installShortcuts = False
        dccItem = installer.tw_components.topLevelItem(0).child(0)
        dccItem.setCheckState(0, Qt.Checked)
        if dccItem.childCount() == 1:
            dccItem.child(0).setCheckState(0, Qt.Checked)

        installer.CompItemClicked(dccItem, 0)
        installer.resize(680, 300)
        installer.exec_()


class UnloadedPlugin(object):
    """Placeholder for plugin that failed to load.
    
    Attributes:
        core: PrismCore instance
        version: Plugin version
        pluginName: Plugin name
        pluginPath: Path to plugin
        pluginType: Plugin type
        appShortName: Application short name
        location: Plugin location
    """
    
    def __init__(self, core: Any, pluginName: str, path: str = "", location: str = "") -> None:
        """Initialize UnloadedPlugin placeholder.
        
        Args:
            core: PrismCore instance
            pluginName: Plugin name
            path: Path to plugin. Defaults to "".
            location: Plugin location. Defaults to "".
        """
        self.core = core
        self.version = ""
        self.pluginName = pluginName
        self.pluginPath = path
        self.pluginType = ""
        self.appShortName = ""
        self.location = location
