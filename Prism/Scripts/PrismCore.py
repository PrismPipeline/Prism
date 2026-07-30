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

from __future__ import annotations

import os
import sys
import shutil
import time
import socket
import traceback
import platform
import errno
import stat
import re
import subprocess
import logging
import tempfile
import glob
import importlib
import atexit
import code
import io
from datetime import datetime
from multiprocessing.connection import Listener, Client
from typing import Any, Optional, Union, List, Dict, Tuple

startEnv = os.environ.copy()

if sys.version_info.minor == 13:
    pyLibs = "Python313"
elif sys.version_info.minor == 11:
    pyLibs = "Python311"
elif sys.version_info.minor == 10:
    pyLibs = "Python310"
elif sys.version_info.minor == 9:
    pyLibs = "Python39"
elif sys.version_info.minor == 7:
    pyLibs = "Python37"
else:
    pyLibs = None

prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
prismLibs = os.getenv("PRISM_LIBS")

if not prismLibs:
    prismLibs = prismRoot

if not os.path.exists(os.path.join(prismLibs, "PythonLibs")) and os.getenv("PRISM_NO_LIBS") != "1":
    raise Exception('Prism: Couldn\'t find libraries. Set "PRISM_LIBS" to fix this.')

scriptPath = os.path.join(prismRoot, "Scripts")
if scriptPath not in sys.path:
    sys.path.append(scriptPath)

cpLibs = os.path.join(prismLibs, "PythonLibs", "CrossPlatform")

if cpLibs not in sys.path:
    sys.path.append(cpLibs)

if pyLibs:
    pyLibPath = os.path.join(prismLibs, "PythonLibs", pyLibs)
    if pyLibPath not in sys.path:
        sys.path.append(pyLibPath)

py3LibPath = os.path.join(prismLibs, "PythonLibs", "Python3")
if py3LibPath not in sys.path:
    sys.path.append(py3LibPath)

if platform.system() == "Windows" and pyLibs:
    sys.path.insert(0, os.path.join(pyLibPath, "win32"))
    sys.path.insert(0, os.path.join(pyLibPath, "win32", "lib"))
    pywinpath = os.path.join(pyLibPath, "pywin32_system32")
    sys.path.insert(0, pywinpath)
    os.environ["PATH"] = pywinpath + os.pathsep + os.environ["PATH"]
    if hasattr(os, "add_dll_directory") and os.path.exists(pywinpath):
        os.add_dll_directory(pywinpath)

try:
    from qtpy.QtCore import *
    from qtpy.QtGui import *
    from qtpy.QtWidgets import *
    from qtpy import API_NAME
    if API_NAME == "PySide6":
        try:
            import shiboken6
        except:
            pass
    else:
        try:
            import shiboken2
        except:
            pass
except:
    sys.path.insert(0, os.path.join(prismLibs, "PythonLibs", "Python3", "PySide"))
    from qtpy.QtCore import *
    from qtpy.QtGui import *
    from qtpy.QtWidgets import *
    from qtpy import API_NAME
    if API_NAME == "PySide6":
        try:
            import shiboken6
        except:
            pass
    else:
        try:
            import shiboken2
        except:
            pass

from PrismUtils.Decorators import err_catcher
from PrismUtils import (
    Callbacks,
    ConfigManager,
    Integration,
    MediaManager,
    MediaProducts,
    PathManager,
    PluginManager,
    PrismWidgets,
    Products,
    ProjectEntities,
    Projects,
    SanityChecks,
    Users,
)


logging.basicConfig()
logger = logging.getLogger(__name__)
if API_NAME == "PyQt5":
    logging.getLogger("PyQt5.uic.uiparser").setLevel(logging.WARNING)
    logging.getLogger("PyQt5.uic.properties").setLevel(logging.WARNING)


# Prism core class, which holds various functions
class PrismCore:
    """Core class for the Prism Pipeline Framework.
    
    This class serves as the central hub for all Prism functionality,
    managing plugins, projects, configurations, and user interfaces.
    
    Attributes:
        version (str): Current Prism version
        core (PrismCore): Self-reference to core instance
        prismRoot (str): Root directory of Prism installation
        prismLibs (str): Directory containing Python libraries
        userini (str): Path to user configuration file
        prismIni (str): Path to project configuration file
        projectPath (str): Current project path (when loaded)
        projectName (str): Current project name (when loaded)
        appPlugin (Any): Active application plugin instance
        plugins (PluginManager): Plugin manager instance
        projects (Projects): Project manager instance
        entities (ProjectEntities): Entity manager instance
        media (MediaManager): Media manager instance
        configs (ConfigManager): Configuration manager instance
        users (Users): User manager instance
        paths (PathManager): Path manager instance
        callbacks (Callbacks): Callback manager instance
        pb (Any): Project Browser instance (when open)
        sm (Any): State Manager instance (when open)
        
    Example:
        ```python
        from PrismCore import PrismCore
        core = PrismCore(app="Standalone")
        core.projectBrowser()
        ```
    """
    
    def __init__(
        self, 
        app: str = "Standalone", 
        prismArgs: Optional[List[str]] = None, 
        splashScreen: Optional[Any] = None
    ) -> None:
        """Initialize the Prism Core.
        
        Args:
            app (str, optional): Application name to load plugin for. 
                Defaults to "Standalone".
            prismArgs (List[str], optional): Command line arguments.
                Defaults to None.
            splashScreen (Any, optional): Splash screen widget for 
                displaying startup progress. Defaults to None.
                
        Raises:
            Exception: If initialization fails, error is logged and
                written to error log.
        """
        if prismArgs is None:
            prismArgs = []
            
        self.prismIni = ""

        try:
            # set some general variables
            self.version = "v2.1.3"
            self.requiredLibraries = "v2.0.0"
            self.core = self
            self.preferredExtension = os.getenv("PRISM_CONFIG_EXTENSION", ".json")

            startTime = datetime.now()

            self.prismRoot = prismRoot.replace("\\", "/")
            self.prismLibs = prismLibs.replace("\\", "/")
            self.pythonVersion = "Python" + os.getenv("PRISM_PYTHON_VERSION", "3.13").replace(".", "")

            self.userini = self.getUserPrefConfigPath()
            prjScriptPath = os.path.abspath(
                os.path.join(__file__, os.pardir, "ProjectScripts")
            )
            sys.path.append(prjScriptPath)

            self.prismArgs = prismArgs
            self.requestedApp = app
            if "silent" in sys.argv:
                self.prismArgs.append("silent")

            self.splashScreen = splashScreen
            if self.splashScreen:
                self.splashScreen.setVersion(self.version)
                self.splashScreen.setStatus("loading core...")

            self.startEnv = startEnv
            self.uiAvailable = False if "noUI" in self.prismArgs else True
            sys.modules[__name__]._active_instance = self
            self.stateData = []
            self.prjHDAs = []
            self.uiScaleFactor = 1
            self.protocolHandlers = {}

            self.smCallbacksRegistered = False
            self.sceneOpenChecksEnabled = True
            self.parentWindows = True
            self.separateOutputVersionStack = True
            self.forceFramerange = False
            self.catchTypeErrors = False
            self.lowestVersion = 1
            self.versionPadding = 4
            self.framePadding = 4
            self.versionFormatVan = "v#"
            self.versionFormat = self.versionFormatVan.replace(
                "#", "%0{}d".format(self.versionPadding)
            )
            self.debugMode = False
            self.useLocalFiles = False
            self.pb = None
            self.sm = None
            self.dv = None
            self.ps = None
            self.status = "starting"
            self.missingModules = []
            self.restartRequired = False
            self.iconCache = {}
            self.reportHandler = lambda *args, **kwargs: None
            self.autosaveSessionMute = False
            self.prism1Compatibility = False
            self.scenePreviewWidth = 500
            self.scenePreviewHeight = 281
            self.worker = Worker
            self.worker.core = self
            self.registeredStyleSheets = []
            self.activeStyleSheet = None
            self.useTranslation = False
            self.pythonHighlighter = PythonHighlighter

            if API_NAME == "PySide6":
                import PySide6
                if self.compareVersions(PySide6.__version__, "6.8") == "lower":
                    os.environ["PRISM_SLIDER_FIX"] = "1"
            else:
                os.environ["PRISM_SLIDER_FIX"] = "1"

            # if no user ini exists, it will be created with default values
            self.configs = ConfigManager.ConfigManager(self)
            self.users = Users.Users(self)
            if not os.path.exists(self.userini):
                self.configs.createUserPrefs()

            debug = os.getenv("PRISM_DEBUG")
            if debug is None:
                debug = self.getConfig("globals", "debug_mode") or False
            else:
                debug = debug.lower() in ["true", "1"]
            self.setDebugMode(debug)
            logger.debug("Initializing Prism %s - args: %s  - python: %s" % (self.version, self.prismArgs, sys.version.split(" (")[0]))

            self.useOnTop = self.getConfig("globals", "use_always_on_top")
            if self.useOnTop is None:
                self.useOnTop = True

            if sys.argv and sys.argv[-1] in ["setupStartMenu", "refreshIntegrations"]:
                self.prismArgs.pop(self.prismArgs.index("loadProject"))

            os.environ["PRISM_VERSION"] = self.version
            self.callbacks = Callbacks.Callbacks(self)
            self.users.refreshEnvironment()
            self.projects = Projects.Projects(self)
            self.plugins = PluginManager.PluginManager(self)
            self.paths = PathManager.PathManager(self)
            self.integration = Integration.Ingegration(self)
            self.entities = ProjectEntities.ProjectEntities(self)
            self.mediaProducts = MediaProducts.MediaProducts(self)
            self.products = Products.Products(self)
            self.media = MediaManager.MediaManager(self)
            self.sanities = SanityChecks.SanityChecks(self)

            dftSheet = os.path.join(self.prismRoot, "Scripts", "UserInterfacesPrism", "stylesheets", "blue_moon")
            self.registerStyleSheet(dftSheet, default=True)

            oldSheet = os.path.join(self.prismRoot, "Scripts", "UserInterfacesPrism", "stylesheets", "qdarkstyle")
            self.registerStyleSheet(oldSheet)
            self.initializeLanguage()

            self.pluginPathApp = os.path.abspath(
                os.path.join(__file__, os.pardir, os.pardir, "Plugins", "Apps")
            )
            self.pluginPathCustom = os.path.abspath(
                os.path.join(__file__, os.pardir, os.pardir, "Plugins", "Custom")
            )
            self.pluginDirs = [
                self.pluginPathApp,
                self.pluginPathCustom,
            ]
            if os.getenv("PRISM_LOAD_PLUGINS_FROM_DFT_PATH", "1") == "1":
                self.pluginDirs.append(self.plugins.getDefaultPluginPath())

            for path in self.pluginDirs:
                sys.path.append(path)

            self.users.ensureUser()
            self.getUIscale()
            self.initializePlugins(app)
            atexit.register(self.onExit)
            qapp = QApplication.instance()
            if qapp:
                qapp.aboutToQuit.connect(self.onExit)

            if sys.argv and sys.argv[-1] == "setupStartMenu":
                if self.splashScreen:
                    self.splashScreen.close()

                self.setupStartMenu()
                sys.exit()
            elif sys.argv and sys.argv[-1] == "refreshIntegrations":
                self.integration.refreshAllIntegrations()
                sys.exit()

            endTime = datetime.now()
            logger.debug("startup duration: %s" % (endTime - startTime))
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            erStr = "%s ERROR - PrismCore init %s:\n%s\n\n%s" % (
                time.strftime("%d/%m/%y %X"),
                self.version,
                "".join(traceback.format_stack()),
                traceback.format_exc(),
            )
            self.writeErrorLog(erStr)

    @err_catcher(name=__name__)
    def getUserPrefDir(self) -> str:
        """Get the user preferences directory path.
        
        Returns a platform-specific directory for storing user preferences.
        Can be overridden with PRISM_USER_PREFS environment variable.
        
        Returns:
            str: Path to user preferences directory.
        """
        if os.getenv("PRISM_USER_PREFS"):
            return os.getenv("PRISM_USER_PREFS")

        if platform.system() == "Windows":
            path = self.getWindowsDocumentsPath() or (self.getPrismDataDir() + "/userprefs")
        elif platform.system() == "Linux":
            path = os.path.join(os.environ["HOME"])
        elif platform.system() == "Darwin":
            path = os.path.join(os.environ["HOME"], "Library", "Preferences")

        path = os.path.join(path, "Prism2")
        return path

    @err_catcher(name=__name__)
    def getWindowsDocumentsPath(self) -> str:
        """Get the Windows Documents folder path.
        
        Uses Windows Shell API to get the current user's Documents folder.
        
        Returns:
            str: Path to Windows Documents folder.
        """
        import ctypes.wintypes
        CSIDL_PERSONAL = 5       # My Documents
        SHGFP_TYPE_CURRENT = 0   # Get current, not default value

        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)

        path = buf.value
        return path

    @err_catcher(name=__name__)
    def getUserPrefConfigPath(self) -> str:
        """Get the path to user preferences configuration file.
        
        Returns:
            str: Full path to user configuration file (Prism.json or Prism.yml).
        """
        dirPath = self.getUserPrefDir()
        configPath = os.path.join(dirPath, "Prism" + self.preferredExtension)
        return configPath

    @err_catcher(name=__name__)
    def getPrismDataDir(self) -> str:
        """Get the Prism data directory path.
        
        Returns a platform-specific directory for storing shared Prism data.
        Can be overridden with PRISM_DATA_DIR environment variable.
        
        Returns:
            str: Path to Prism data directory.
        """
        if os.getenv("PRISM_DATA_DIR"):
            return os.getenv("PRISM_DATA_DIR")

        if platform.system() == "Windows":
            path = os.path.join(os.environ["PROGRAMDATA"], "Prism2")
        elif platform.system() == "Linux":
            path = os.path.join(os.environ["HOME"], "Prism2")
        elif platform.system() == "Darwin":
            path = os.path.join(os.environ["HOME"], "Documents", "Prism2")

        return path

    @err_catcher(name=__name__)
    def grantRwToAllUsers(self, path: str) -> None:
        """Grant read/write permissions to all users for a path (Windows only).
        
        Args:
            path (str): Directory or file path to modify permissions for.
        """
        try:
            subprocess.run(
                ["icacls", path, "/grant", "Users:(OI)(CI)M", "/T"],
                check=True,
                shell=True
            )
        except subprocess.CalledProcessError as e:
            logger.debug("Failed to update permissions: %s" % (str(e)))

    @err_catcher(name=__name__)
    def initializeLanguage(self) -> None:
        """Initialize language translation system.
        
        Loads Chinese translation if PRISM_LANGUAGE environment 
        variable is set to "CN".
        """
        if os.getenv("PRISM_LANGUAGE") == "CN":
            qapp = QApplication.instance()
            translator = QTranslator(qapp)
            path = os.path.join(os.path.dirname(__file__), "UserInterfacesPrism/translations/cn.qm")
            translator.load(path)
            qapp.installTranslator(translator)
            self.useTranslation = True

    @err_catcher(name=__name__)
    def initializePlugins(self, appPlugin: str) -> Any:
        """Initialize all Prism plugins.
        
        Args:
            appPlugin (str): Name of the application plugin to load.
            
        Returns:
            Any: Result from plugin manager initialization.
        """
        return self.plugins.initializePlugins(appPlugin=appPlugin)

    @err_catcher(name=__name__)
    def reloadPlugins(self, plugins: Optional[List[str]] = None) -> Any:
        """Reload specified plugins or all plugins.
        
        Args:
            plugins (List[str], optional): List of plugin names to reload.
                If None, reloads all plugins. Defaults to None.
                
        Returns:
            Any: Result from plugin manager reload.
        """
        return self.plugins.reloadPlugins(plugins=plugins)

    @err_catcher(name=__name__)
    def reloadCustomPlugins(self) -> Any:
        """Reload all custom plugins.
        
        Returns:
            Any: Result from plugin manager reload.
        """
        return self.plugins.reloadCustomPlugins()

    @err_catcher(name=__name__)
    def unloadProjectPlugins(self) -> Any:
        """Unload all project-specific plugins.
        
        Returns:
            Any: Result from plugin manager unload.
        """
        return self.plugins.unloadProjectPlugins()

    @err_catcher(name=__name__)
    def unloadPlugin(self, pluginName: str) -> Any:
        """Unload a specific plugin.
        
        Args:
            pluginName (str): Name of the plugin to unload.
            
        Returns:
            Any: Result from plugin manager unload.
        """
        return self.plugins.unloadPlugin(pluginName=pluginName)

    @err_catcher(name=__name__)
    def getPluginNames(self) -> List[str]:
        """Get names of all loaded plugins.
        
        Returns:
            List[str]: List of plugin names.
        """
        return self.plugins.getPluginNames()

    @err_catcher(name=__name__)
    def getPluginSceneFormats(self) -> List[str]:
        """Get supported scene file formats from all plugins.
        
        Returns:
            List[str]: List of file extensions (e.g., ['.ma', '.mb', '.blend']).
        """
        return self.plugins.getPluginSceneFormats()

    @err_catcher(name=__name__)
    def getPluginData(self, pluginName: str, data: str) -> Any:
        """Get specific data attribute from a plugin.
        
        Args:
            pluginName (str): Name of the plugin.
            data (str): Name of data attribute to retrieve.
            
        Returns:
            Any: The requested plugin data attribute value.
        """
        return self.plugins.getPluginData(pluginName=pluginName, data=data)

    @err_catcher(name=__name__)
    def getPlugin(self, pluginName: str, allowUnloaded: bool = False) -> Any:
        """Get a plugin instance by name.
        
        Args:
            pluginName (str): Name of the plugin to retrieve.
            allowUnloaded (bool, optional): If True, returns plugin info
                even if not loaded. Defaults to False.
                
        Returns:
            Any: Plugin instance or None if not found.
        """
        return self.plugins.getPlugin(pluginName=pluginName, allowUnloaded=allowUnloaded)

    @err_catcher(name=__name__)
    def getLoadedPlugins(self) -> Dict[str, Any]:
        """Get all loaded plugin instances.
        
        Returns:
            Dict[str, Any]: Dictionary mapping plugin names to plugin instances.
        """
        return self.plugins.getLoadedPlugins()

    @err_catcher(name=__name__)
    def createPlugin(self, *args: Any, **kwargs: Any) -> Any:
        """Create a new plugin.
        
        Args:
            *args: Variable length argument list passed to plugin manager.
            **kwargs: Arbitrary keyword arguments passed to plugin manager.
            
        Returns:
            Any: Result from plugin creation.
        """
        return self.plugins.createPlugin(*args, **kwargs)

    @err_catcher(name=__name__)
    def callback(self, *args: Any, **kwargs: Any) -> Any:
        """Execute registered callbacks.
        
        Args:
            *args: Variable length argument list passed to callback manager.
            **kwargs: Arbitrary keyword arguments passed to callback manager.
            
        Returns:
            Any: Result from callback execution.
        """
        return self.callbacks.callback(*args, **kwargs)

    @err_catcher(name=__name__)
    def registerCallback(self, *args: Any, **kwargs: Any) -> Any:
        """Register a new callback function.
        
        Args:
            *args: Variable length argument list passed to callback manager.
            **kwargs: Arbitrary keyword arguments passed to callback manager.
            
        Returns:
            Any: Result from callback registration.
        """
        return self.callbacks.registerCallback(*args, **kwargs)

    @err_catcher(name=__name__)
    def unregisterCallback(self, *args: Any, **kwargs: Any) -> Any:
        """Unregister a callback function.
        
        Args:
            *args: Variable length argument list passed to callback manager.
            **kwargs: Arbitrary keyword arguments passed to callback manager.
            
        Returns:
            Any: Result from callback unregistration.
        """
        return self.callbacks.unregisterCallback(*args, **kwargs)

    @err_catcher(name=__name__)
    def callHook(self, *args: Any, **kwargs: Any) -> Any:
        """Call a registered hook function.
        
        Args:
            *args: Variable length argument list passed to callback manager.
            **kwargs: Arbitrary keyword arguments passed to callback manager.
            
        Returns:
            Any: Result from hook execution.
        """
        return self.callbacks.callHook(*args, **kwargs)

    @err_catcher(name=__name__)
    def startup(self) -> Optional[Any]:
        """Execute startup procedures after initialization.
        
        Loads the current project if one is set and optionally opens
        the Project Browser based on preferences.
        
        Returns:
            Optional[Any]: Result from app plugin startup or None.
        """
        if not self.appPlugin:
            return

        # if self.appPlugin.hasQtParent:
        #     self.elapsed += 1
        #     if self.elapsed > self.maxwait and hasattr(self, "timer"):
        #         self.timer.stop()

        result = self.appPlugin.startup(self)
        if result is not None:
            return result

        if "prism_project" in os.environ and os.path.exists(
            os.environ["prism_project"]
        ):
            curPrj = os.environ["prism_project"]
        else:
            curPrj = self.getConfig("globals", "current project")
            if not curPrj and os.getenv("PRISM_PROJECT_FALLBACK") and os.path.exists(os.getenv("PRISM_PROJECT_FALLBACK")):
                curPrj = os.getenv("PRISM_PROJECT_FALLBACK")

        failedToSetProject = False
        if curPrj:
            if self.splashScreen:
                self.splashScreen.setStatus("loading project...")

            result = self.changeProject(curPrj)
            if result is None:
                failedToSetProject = True

        if (
            "silent" not in self.prismArgs
            and "noProjectBrowser" not in self.prismArgs
            and (self.getConfig("globals", "showonstartup") is not False or self.appPlugin.pluginName == "Standalone")
            and self.uiAvailable
            and os.getenv("PRISM_NO_PROJECT_BROWSER") != "1"
            and not failedToSetProject
        ):
            if self.splashScreen:
                self.splashScreen.setStatus("opening Project Browser...")

            self.projectBrowser()

        if self.getCurrentFileName() != "":
            self.sceneOpen()

        if not self.plugins._delayedPluginPaths and not self.plugins._delayedLoader:
            self.status = "postInitializing"
            self.callback(name="postInitialize")
            self.status = "loaded"
        else:
            self.status = "waitingForDelayedPlugins"

    @err_catcher(name=__name__)
    def shouldAutosaveTimerRun(self) -> bool:
        """Check if autosave timer should be running.
        
        Determines based on session state, preferences, and current 
        application state whether the autosave timer should be active.
        
        Returns:
            bool: True if autosave timer should run, False otherwise.
        """
        if self.autosaveSessionMute:
            return False

        autoSave = self.getConfig("globals", "autosave")
        if not autoSave:
            return False

        qapp = QApplication.instance()
        isGuiThread = qapp and qapp.thread() == QThread.currentThread()
        if "silent" in self.prismArgs or not self.uiAvailable or not isGuiThread:
            return

        return True

    @err_catcher(name=__name__)
    def isAutosaveTimerActive(self) -> bool:
        """Check if autosave timer is currently active.
        
        Returns:
            bool: True if timer exists and is active, False otherwise.
        """
        active = hasattr(self, "autosaveTimer") and self.autosaveTimer.isActive()
        return active

    @err_catcher(name=__name__)
    def startAutosaveTimer(self, quit: bool = False) -> None:
        """Start or stop the autosave timer.
        
        Args:
            quit (bool, optional): If True, stops the timer instead of
                starting it. Defaults to False.
        """
        if self.isAutosaveTimerActive():
            self.autosaveTimer.stop()
            if hasattr(self, "autosave_msg"):
                try:
                    isvis = self.autosave_msg.isVisible()
                except:
                    isvis = False

                if isvis:
                    self.autosave_msg.blockSignals(True)
                    self.autosave_msg.done(2)
                    self.autosave_msg.blockSignals(False)

        if quit:
            return

        if not self.shouldAutosaveTimerRun():
            return

        autosaveMins = 15
        minutes = os.getenv("PRISM_AUTOSAVE_INTERVAL")
        if minutes:
            try:
                minutes = float(minutes)
            except:
                logger.warning("invalid autosave interval: %s" % minutes)
            else:
                autosaveMins = minutes

        self.autosaveTimer = QTimer()
        self.autosaveTimer.timeout.connect(self.checkAutoSave)
        self.autosaveTimer.setSingleShot(True)
        self.autosaveTimer.start(autosaveMins * 60 * 1000)

        logger.debug("started autosave timer: %smin" % autosaveMins)

    @err_catcher(name=__name__)
    def checkAutoSave(self) -> None:
        """Check and potentially trigger autosave.
        
        Displays a dialog asking the user if they want to save the current
        scene when autosave interval has elapsed.
        """
        if not hasattr(self.appPlugin, "autosaveEnabled") or self.appPlugin.autosaveEnabled(self):
            return

        self.autosave_msg = QMessageBox()
        self.autosave_msg.setWindowTitle("Prism Autosave")
        self.autosave_msg.setText("Autosave is disabled. Would you like to save now?")
        self.autosave_msg.addButton("Save", QMessageBox.YesRole)
        button = self.autosave_msg.addButton("Save new version", QMessageBox.YesRole)
        button.setToolTip("Hold CTRL to open the \"Save Extended\" dialog.")
        b_no = self.autosave_msg.addButton("No", QMessageBox.YesRole)
        self.autosave_msg.addButton(
            "No, don't ask again in this session", QMessageBox.YesRole
        )
        self.autosave_msg.setDefaultButton(b_no)
        self.autosave_msg.setEscapeButton(b_no)

        self.parentWindow(self.autosave_msg)
        self.autosave_msg.finished.connect(self.autoSaveDone)
        self.autosave_msg.setModal(False)
        self.autosave_msg.show()

    @err_catcher(name=__name__)
    def autoSaveDone(self, action: int = 2) -> None:
        """Handle autosave dialog completion.
        
        Args:
            action (int, optional): Action ID from dialog. Defaults to 2.
        """
        button = self.autosave_msg.clickedButton()

        if button:
            saved = False
            if button.text() == "Save":
                saved = self.saveScene(prismReq=False)
            elif button.text() == "Save new version":
                mods = QApplication.keyboardModifiers()
                if mods == Qt.ControlModifier:
                    saved = self.saveWithComment()
                else:
                    saved = self.saveScene()
            elif button.text() == "No, don't ask again in this session":
                self.autosaveSessionMute = True
                self.startAutosaveTimer(quit=True)
                return

            if saved:
                return

        self.startAutosaveTimer()

    @err_catcher(name=__name__)
    def getWorker(self, function: Optional[Any] = None) -> Any:
        """Create and configure a worker thread.
        
        Args:
            function (Any, optional): Function to run in worker thread.
                Defaults to None.
                
        Returns:
            Any: Configured Worker instance.
        """
        worker = Worker()
        if function:
            worker.function = function

        worker.errored.connect(self.threadErrored)
        return worker

    def threadErrored(self, msg: str) -> None:
        """Handle errors from worker threads.
        
        Args:
            msg (str): Error message to log.
        """
        self.core.writeErrorLog(msg)

    @err_catcher(name=__name__)
    def setDebugMode(self, enabled: bool) -> None:
        """Enable or disable debug mode.
        
        Args:
            enabled (bool): True to enable debug mode, False to disable.
        """
        self.debugMode = enabled
        os.environ["PRISM_DEBUG"] = str(enabled)
        logLevel = "DEBUG" if enabled else "WARNING"
        self.core.updateLogging(level=logLevel)
        if getattr(self, "pb", None):
            self.pb.act_console.setVisible(self.debugMode)

    @err_catcher(name=__name__)
    def updateLogging(self, level: Optional[str] = None) -> None:
        """Update logging level for Prism.
        
        Args:
            level (str, optional): Logging level (DEBUG, INFO, WARNING, ERROR).
                If None, uses debug mode setting. Defaults to None.
        """
        if not level:
            level = "DEBUG" if self.debugMode else "WARNING"

        logging.root.setLevel(level)

    @err_catcher(name=__name__)
    def compareVersions(self, version1: str, version2: str) -> str:
        """Compare two version strings.
        
        Compares version numbers like "v2.0.1" with "v2.1.0".
        
        Args:
            version1 (str): First version string.
            version2 (str): Second version string.
            
        Returns:
            str: "lower" if version1 < version2, "higher" if version1 > version2,
                "equal" if they are the same.
        """
        if not version1:
            if version2:
                return "lower"
            else:
                return "equal"

        if not version2:
            return "higher"

        if version1[0] == "v":
            version1 = version1[1:]

        if version2[0] == "v":
            version2 = version2[1:]

        if version1 == version2:
            return "equal"

        version1Data = str(version1).split(".")
        version2Data = str(version2).split(".")

        v1Data = []
        for data in version1Data:
            items = re.split(r'(\d+)', data)
            v1Data += [x for x in items if x]

        v2Data = []
        for data in version2Data:
            items = re.split(r'(\d+)', data)
            v2Data += [x for x in items if x]

        if len(v1Data) != len(v2Data):
            while len(v1Data) > len(v2Data):
                v2Data.append("0")

            while len(v1Data) < len(v2Data):
                v1Data.append("0")

        for idx in range(len(v1Data)):
            if v1Data[idx].isnumeric() and not v2Data[idx].isnumeric():
                return "higher"
            elif not v1Data[idx].isnumeric() and v2Data[idx].isnumeric():
                return "lower"
            elif v1Data[idx].isnumeric() and v2Data[idx].isnumeric():
                v1Data[idx] = int(v1Data[idx])
                v2Data[idx] = int(v2Data[idx])

            if v1Data[idx] < v2Data[idx]:
                return "lower"
            elif v1Data[idx] > v2Data[idx]:
                return "higher"

        return "equal"

    @err_catcher(name=__name__)
    def checkCommands(self) -> None:
        """Check for and execute pending commands.
        
        Scans the Commands directory for command files created by other
        machines and executes them.
        """
        if not os.path.exists(self.prismIni):
            return

        if not self.users.ensureUser():
            return

        cmdDir = os.path.join(
            os.path.dirname(self.prismIni), "Commands", socket.gethostname()
        )
        if not os.path.exists(cmdDir):
            try:
                os.makedirs(cmdDir)
            except:
                return

        filesToRemove = []
        for filename in sorted(os.listdir(cmdDir)):
            if not filename.startswith("prismCmd_"):
                continue

            filePath = os.path.join(cmdDir, filename)
            if os.path.isfile(filePath) and os.path.splitext(filePath)[1] == ".txt":
                with open(filePath, "r") as comFile:
                    cmdText = comFile.read()

            command = None
            try:
                command = eval(cmdText)
            except:
                msg = (
                    "Could evaluate command: %s\n - %s"
                    % (cmdText, traceback.format_exc())
                )
                self.popup(msg)

            self.handleCmd(command)
            filesToRemove.append(filePath)

        for filePath in filesToRemove:
            os.remove(filePath)

    @err_catcher(name=__name__)
    def handleCmd(self, command: Optional[List[Any]]) -> None:
        """Execute a command received from the command system.
        
        Args:
            command (List[Any], optional): Command list with action and parameters.
        """
        if not command or not isinstance(command, list):
            return

        if command[0] == "deleteShot":
            shotName = command[1]
            self.entities.deleteShot(shotName)

        elif command[0] == "renameShot":
            curName = command[1]
            newName = command[2]
            self.entities.renameShot(curName, newName)

        elif command[0] == "renameLocalShot":
            curName = command[1]
            newName = command[2]
            msg = (
                'A shot in your project was renamed from "%s" to "%s". Do you want to check if there are local files with the old shotname and rename them to the new shotname?'
                % (curName, newName)
            )
            result = self.popupQuestion(msg)
            if result == "Yes":
                self.entities.renameShot(curName, newName, locations=["local"])

        elif command[0] == "renameLocalSequence":
            curName = command[1]
            newName = command[2]
            msg = (
                'A sequence in your project was renamed from "%s" to "%s". Do you want to check if there are local files with the old sequencename and rename them to the new sequencename?'
                % (curName, newName)
            )
            result = self.popupQuestion(msg)
            if result == "Yes":
                self.entities.renameSequence(curName, newName, locations=["local"])

        else:
            self.popup("Unknown command: %s" % (command))

    @err_catcher(name=__name__)
    def createCmd(self, cmd: List[Any], includeCurrent: bool = False) -> None:
        """Create a command file for other machines to execute.
        
        Args:
            cmd (List[Any]): Command list with action and parameters.
            includeCurrent (bool, optional): If True, also executes on current
                machine. Defaults to False.
        """
        if not self.projects.getCommandsEnabled():
            self.handleCmd(cmd)
            return

        if not os.path.exists(self.prismIni):
            return

        cmdDir = os.path.join(os.path.dirname(self.prismIni), "Commands")
        if not os.path.exists(cmdDir):
            try:
                os.makedirs(cmdDir)
            except:
                return

        for i in os.listdir(cmdDir):
            if not includeCurrent and i == socket.gethostname():
                continue

            if i == socket.gethostname():
                self.handleCmd(cmd)
                continue

            dirPath = os.path.join(cmdDir, i)
            if not os.path.isdir(dirPath):
                continue

            cmdFile = os.path.join(dirPath, "prismCmd_0001.txt")
            curNum = 1

            while os.path.exists(cmdFile):
                curNum += 1
                cmdFile = cmdFile[:-8] + format(curNum, "04") + ".txt"

            open(cmdFile, "a").close()
            with open(cmdFile, "w") as cFile:
                cFile.write(str(cmd))

    @err_catcher(name=__name__)
    def getLocalPath(self) -> bool:
        """Prompt user to set or confirm local project path.
        
        Shows a dialog for user to enter the local path for the current project.
        
        Returns:
            bool: True if path was set successfully, False otherwise.
        """
        defaultLocalPath = self.projects.getDefaultLocalPath()
        if self.uiAvailable:
            self.pathWin = PrismWidgets.SetPath(core=self)
            self.pathWin.setModal(True)
            self.parentWindow(self.pathWin)
            self.pathWin.e_path.setText(defaultLocalPath)
            result = self.pathWin.exec_()
            self.localProjectPath = ""
            if result == 1:
                setPathResult = self.setLocalPath(self.pathWin.e_path.text())
            else:
                return False

            if not setPathResult and result == 1:
                self.popup("Please enter a valid path to continue.")
                self.getLocalPath()
        else:
            logger.info("setting local project path to: %s" % defaultLocalPath)
            self.setLocalPath(defaultLocalPath)

        return True

    @err_catcher(name=__name__)
    def setLocalPath(self, path: str, projectName: Optional[str] = None) -> bool:
        """Set the local project path.
        
        Args:
            path (str): Local path to set for the project.
            projectName (str, optional): Project name. Uses current project 
                if None. Defaults to None.
                
        Returns:
            bool: True if path was set successfully, False otherwise.
        """
        if projectName is None:
            projectName = self.projectName

        self.localProjectPath = path

        try:
            os.makedirs(self.localProjectPath)
        except:
            pass

        if os.path.exists(self.localProjectPath):
            self.setConfig("localfiles", projectName, self.localProjectPath)
            return True
        else:
            return False

    @err_catcher(name=__name__)
    def getQScreenGeo(self) -> Optional[Any]:
        """Get the screen geometry.
        
        Returns:
            Optional[Any]: QRect of screen geometry or None.
        """
        screen = None
        if hasattr(QApplication, "primaryScreen"):
            screen = QApplication.primaryScreen()
            screen = screen.geometry()
        else:
            desktop = QApplication.desktop()
            if desktop:
                screen = desktop.screenGeometry()

        return screen

    @err_catcher(name=__name__)
    def getUIscale(self) -> float:
        """Get the UI scale factor.
        
        Returns:
            float: UI scale factor.
        """
        sFactor = 1
        self.uiScaleFactor = sFactor
        return self.uiScaleFactor

    @err_catcher(name=__name__)
    def scaleUI(self, win: Optional[Any] = None, sFactor: float = 0) -> None:
        """Scale UI elements by a factor.
        
        Args:
            win (Any, optional): Window widget to scale. Defaults to None.
            sFactor (float, optional): Scale factor. If 0, uses default.
                Defaults to 0.
        """
        if sFactor == 0:
            sFactor = self.uiScaleFactor

        if sFactor != 1:
            members = [
                attr
                for attr in dir(win)
                if not callable(getattr(win, attr)) and not attr.startswith("__")
            ]
            for i in members:
                if hasattr(getattr(win, i), "maximumWidth"):
                    maxW = getattr(win, i).maximumWidth()
                    if maxW < 100000:
                        getattr(win, i).setMaximumWidth(maxW * sFactor)
                if hasattr(getattr(win, i), "minimumWidth"):
                    getattr(win, i).setMinimumWidth(
                        getattr(win, i).minimumWidth() * sFactor
                    )

                if hasattr(getattr(win, i), "maximumHeight"):
                    maxH = getattr(win, i).maximumHeight()
                    if maxH < 100000:
                        getattr(win, i).setMaximumHeight(maxH * sFactor)
                if hasattr(getattr(win, i), "minimumHeight"):
                    getattr(win, i).setMinimumHeight(
                        getattr(win, i).minimumHeight() * sFactor
                    )

            if hasattr(win, "width"):
                curWidth = win.width()
                curHeight = win.height()
                win.resize(curWidth * sFactor, curHeight * sFactor)

    @err_catcher(name=__name__)
    def parentWindow(self, win: Any, parent: Optional[Any] = None) -> None:
        """Set window parent and configure window flags.
        
        Args:
            win (Any): Window widget to parent.
            parent (Any, optional): Parent widget. Defaults to None.
        """
        self.scaleUI(win)
        if not getattr(self, "appPlugin", None) or not self.appPlugin.hasQtParent:
            if not getattr(self, "appPlugin", None) or (
                self.appPlugin.pluginName != "Standalone" and self.useOnTop
            ):
                win.setWindowFlags(win.windowFlags() | Qt.WindowStaysOnTopHint)

        if (not parent and not self.parentWindows) or not self.uiAvailable:
            return

        parent = parent or getattr(self, "messageParent", None)
        if platform.system() == "Linux":
            win.setParent(parent, Qt.Window | Qt.Tool)
        else:
            win.setParent(parent, Qt.Window)

        if platform.system() == "Darwin" and self.useOnTop:
            win.setWindowFlags(win.windowFlags() | Qt.WindowStaysOnTopHint)

    @err_catcher(name=__name__)
    def tr(self, text: str) -> str:
        """Translate text if translation is enabled.
        
        Args:
            text (str): Text to translate.
            
        Returns:
            str: Translated text or original text.
        """
        if self.useTranslation:
            return QApplication.translate("", text)
        else:
            return text

    @err_catcher(name=__name__)
    def changeProject(self, *args: Any, **kwargs: Any) -> Any:
        """Change the active project.
        
        Args:
            *args: Variable length argument list passed to project manager.
            **kwargs: Arbitrary keyword arguments passed to project manager.
            
        Returns:
            Any: Result from project change.
        """
        return self.projects.changeProject(*args, **kwargs)

    @err_catcher(name=__name__)
    def getAboutString(self) -> str:
        """Get HTML string for About dialog.
        
        Returns:
            str: HTML formatted about information.
        """
        prVersion = ""
        if os.path.exists(self.prismIni):
            prjVersion = self.getConfig(
                "globals", "prism_version", configPath=self.prismIni
            )
            if prjVersion is not None:
                prVersion = (
                    "Project:&nbsp;&nbsp;&nbsp;&nbsp;%s&nbsp;&nbsp;&nbsp;(%s)"
                    % (prjVersion, self.projectName)
                )

        astr = """Prism:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;%s<br>
%s<br>
<br>
Copyright (C) 2023-2026 Prism Software GmbH<br>
License: GNU LGPL-3.0-or-later<br>
<br>
<a href='mailto:contact@prism-pipeline.com' style="color: rgb(150,200,250)">contact@prism-pipeline.com</a><br>
<br>
<a href='https://prism-pipeline.com/' style="color: rgb(150,200,250)">www.prism-pipeline.com</a>""" % (
            self.version,
            prVersion,
        )

        return astr

    @err_catcher(name=__name__)
    def showAbout(self) -> None:
        """Display the About dialog."""
        astr = self.getAboutString()
        self.popup(astr, title="About", severity="info")

    @err_catcher(name=__name__)
    def sendFeedbackDlg(self, state: Optional[Any] = None, startText: Optional[str] = None, parent: Optional[Any] = None) -> Any:
        """Display dialog for sending feedback.
        
        Args:
            state (Any, optional): Initial state. Defaults to None.
            startText (str, optional): Initial text for message. Defaults to None.
            parent (Any, optional): Parent widget. Defaults to None.
            
        Returns:
            Any: Dialog result.
        """
        fbDlg = PrismWidgets.EnterText()
        fbDlg.setModal(True)
        self.parentWindow(fbDlg, parent=parent)
        fbDlg.setWindowTitle("Send Message")
        fbDlg.l_info.setText("Message:\n")
        fbDlg.te_text.setMinimumHeight(200 * self.uiScaleFactor)
        if startText:
            fbDlg.te_text.setPlainText(startText)

        fbDlg.l_description = QLabel(
            "Please provide also contact information (e.g. e-mail) for further discussions and to receive answers to your questions."
        )
        fbDlg.layout().insertWidget(fbDlg.layout().count() - 1, fbDlg.l_description)
        fbDlg.buttonBox.buttons()[0].setText("Send")

        fbDlg.l_screenGrab = QLabel()
        fbDlg.lo_screenGrab = QHBoxLayout()
        fbDlg.lo_screenGrab.setContentsMargins(0, 0, 0, 0)
        fbDlg.b_addScreenGrab = QPushButton("Attach Screengrab")
        fbDlg.b_removeScreenGrab = QPushButton("Remove Screengrab")
        fbDlg.lo_screenGrab.addWidget(fbDlg.b_addScreenGrab)
        fbDlg.lo_screenGrab.addWidget(fbDlg.b_removeScreenGrab)
        fbDlg.lo_screenGrab.addStretch()
        fbDlg.sp_main = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Fixed)

        fbDlg.layout().insertWidget(fbDlg.layout().count() - 1, fbDlg.l_screenGrab)
        fbDlg.layout().insertLayout(fbDlg.layout().count() - 1, fbDlg.lo_screenGrab)
        fbDlg.layout().insertItem(fbDlg.layout().count() - 1, fbDlg.sp_main)

        size = QSize(fbDlg.size().width(), int(fbDlg.size().height() * 0.7))
        fbDlg.b_addScreenGrab.clicked.connect(lambda: self.attachScreenGrab(fbDlg, size=size))
        fbDlg.b_removeScreenGrab.clicked.connect(lambda: self.removeScreenGrab(fbDlg))
        fbDlg.b_removeScreenGrab.setVisible(False)
        fbDlg.resize(900 * self.core.uiScaleFactor, 500 * self.core.uiScaleFactor)
        fbDlg.origSize = fbDlg.size()

        result = fbDlg.exec_()

        if result == 1:
            pm = getattr(fbDlg, "screenGrab", None)
            if pm:
                attachment = tempfile.NamedTemporaryFile(suffix=".jpg").name
                self.media.savePixmap(pm, attachment)
            else:
                attachment = None

            self.sendFeedback(
                fbDlg.te_text.toPlainText(),
                subject="Prism feedback",
                attachment=attachment,
            )

    @err_catcher(name=__name__)
    def sendFeedback(self, msg: str, subject: str = "Prism feedback", attachment: Optional[str] = None) -> None:
        """Send feedback message to report handler.
        
        Args:
            msg (str): Feedback message text.
            subject (str, optional): Email subject. Defaults to "Prism feedback".
            attachment (str, optional): Path to attachment file. Defaults to None.
        """
        self.reportHandler(msg, attachment=attachment, reportType="feedback")

    @err_catcher(name=__name__)
    def attachScreenGrab(self, dlg: Any, size: Optional[Any] = None) -> None:
        """Capture and attach a screenshot to feedback dialog.
        
        Args:
            dlg (Any): Dialog widget to attach screenshot to.
            size (Any, optional): Size for screenshot preview. Defaults to None.
        """
        dlg.setWindowOpacity(0)
        from PrismUtils import ScreenShot

        previewImg = ScreenShot.grabScreenArea(self)
        dlg.setWindowOpacity(1)

        if previewImg:
            size = size or dlg.size()
            pmscaled = previewImg.scaled(
                size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            dlg.l_screenGrab.setPixmap(pmscaled)
            dlg.screenGrab = previewImg
            dlg.b_addScreenGrab.setVisible(False)
            dlg.b_removeScreenGrab.setVisible(True)
            newPos = dlg.pos() - QPoint(0, pmscaled.height() * 0.5)
            newPos.setY(max(0, newPos.y()))
            dlg.move(newPos)

    @err_catcher(name=__name__)
    def removeScreenGrab(self, dlg: Any) -> None:
        """Remove screenshot attachment from feedback dialog.
        
        Args:
            dlg (Any): Dialog widget to remove screenshot from.
        """
        dlg.screenGrab = None
        dlg.l_screenGrab.clear()
        dlg.b_addScreenGrab.setVisible(True)
        dlg.b_removeScreenGrab.setVisible(False)
        dlg.resize(dlg.origSize)

    def openWebsite(self, location: str) -> None:
        """Open a Prism-related website in the default browser.
        
        Args:
            location (str): Location identifier (home, tutorials, documentation,
                downloads, discord) or direct URL.
        """
        if location == "home":
            url = "https://prism-pipeline.com/"
        elif location == "tutorials":
            url = "https://prism-pipeline.com/tutorials/"
        elif location == "documentation":
            url = "https://prism-pipeline.com/docs/latest"
        elif location == "downloads":
            url = "https://prism-pipeline.com/downloads/"
        elif location == "discord":
            url = "https://prism-pipeline.com/discord/"
        else:
            url = location

        import webbrowser

        webbrowser.open(url)

    @err_catcher(name=__name__)
    def getCheckStateValue(self, checkState: Any) -> int:
        """Get integer value from Qt check state.
        
        Args:
            checkState (Any): Qt check state enum or integer.
            
        Returns:
            int: Integer value of check state.
        """
        if hasattr(checkState, "value"):
            return checkState.value
        else:
            return int(checkState)

    @err_catcher(name=__name__)
    def isObjectValid(self, obj: Any) -> bool:
        """Check if a Qt object is valid.
        
        Args:
            obj (Any): Qt object to validate.
            
        Returns:
            bool: True if object exists and is valid, False otherwise.
        """
        if "shiboken6" in globals():
            if not obj or not shiboken6.isValid(obj):
                return False
            else:
                return True

        elif "shiboken2" in globals():
            if not obj or not shiboken2.isValid(obj):
                return False
            else:
                return True

    @err_catcher(name=__name__)
    def getStateManager(self, create: bool = True) -> Optional[Any]:
        """Get the State Manager instance.
        
        Args:
            create (bool, optional): If True, creates State Manager if it
                doesn't exist. Defaults to True.
                
        Returns:
            Optional[Any]: State Manager instance or None.
        """
        sm = getattr(self, "sm", None)
        if not sm:
            sm = getattr(self, "stateManagerInCreation", None)

        if "shiboken6" in globals():
            if sm and not shiboken6.isValid(sm):
                sm = None
        elif "shiboken2" in globals():
            if sm and not shiboken2.isValid(sm):
                sm = None

        if not sm and create:
            sm = self.stateManager(openUi=False)

        return sm

    @err_catcher(name=__name__)
    def stateManagerEnabled(self) -> bool:
        """Check if State Manager is enabled for current application.
        
        Returns:
            bool: True if State Manager is enabled.
        """
        return True  # self.appPlugin.appType == "3d"

    @err_catcher(name=__name__)
    def stateManager(
        self, 
        stateDataPath: Optional[str] = None, 
        restart: bool = False, 
        openUi: bool = True, 
        reload_module: bool = False, 
        new_instance: bool = False, 
        standalone: bool = False
    ) -> Any:
        """Open or create the State Manager.
        
        Args:
            stateDataPath (str, optional): Path to state data file. Defaults to None.
            restart (bool, optional): Restart State Manager. Defaults to False.
            openUi (bool, optional): Show UI after opening. Defaults to True.
            reload_module (bool, optional): Reload module before opening. 
                Defaults to False.
            new_instance (bool, optional): Create new SM instance. Defaults to False.
            standalone (bool, optional): Run in standalone mode. Defaults to False.
            
        Returns:
            Any: State Manager instance or False if failed.
        """
        if not self.stateManagerEnabled():
            return False

        if not self.projects.ensureProject(openUi="stateManager"):
            return False

        if not self.users.ensureUser():
            return False

        if not self.sanities.runChecks("onOpenStateManager")["passed"]:
            return False

        mods = QApplication.keyboardModifiers()
        if not getattr(self, "sm", None) or self.debugMode or reload_module or new_instance or mods == Qt.ControlModifier:
            if not new_instance:
                self.closeSM()

            if self.uiAvailable and (eval(os.getenv("PRISM_DEBUG", "False")) or reload_module):
                try:
                    del sys.modules["StateManager"]
                except:
                    pass

            try:
                import StateManager
            except Exception as e:
                msgString = "Could not load the StateManager:\n\n%s" % str(e)
                self.popup(msgString)
                return

            sm = StateManager.StateManager(core=self, stateDataPath=stateDataPath, standalone=standalone, saveEnabled=False)
            self.stateManagerInCreation = None
            if not new_instance:
                self.sm = sm
        else:
            sm = self.sm

        if self.uiAvailable and openUi:
            sm.show()
            sm.collapseFolders()
            sm.activateWindow()
            sm.raise_()
            if sm.isMinimized():
                sm.showNormal()

        sm.saveEnabled = True
        sm.saveStatesToScene()
        return sm

    @err_catcher(name=__name__)
    def closeSM(self, restart: bool = False) -> Optional[Any]:
        """Close the State Manager.
        
        Args:
            restart (bool, optional): Restart State Manager after closing.
                Defaults to False.
                
        Returns:
            Optional[Any]: New State Manager instance if restarted, None otherwise.
        """
        if getattr(self, "sm", None):
            self.sm.saveEnabled = False
            wasOpen = self.isStateManagerOpen()
            if wasOpen:
                self.sm.close()

            if restart:
                return self.stateManager(openUi=wasOpen, reload_module=True)

    @err_catcher(name=__name__)
    def isStateManagerOpen(self) -> bool:
        """Check if State Manager is currently open.
        
        Returns:
            bool: True if State Manager is visible, False otherwise.
        """
        if not getattr(self, "sm", None):
            return False

        return self.sm.isVisible()

    @err_catcher(name=__name__)
    def projectBrowser(self, openUi: bool = True) -> Any:
        """Open or refresh the Project Browser.
        
        Args:
            openUi (bool, optional): Show UI after opening. Defaults to True.
            
        Returns:
            Any: Project Browser instance or False if failed.
        """
        if not self.projects.ensureProject(openUi="projectBrowser"):
            return False

        if getattr(self, "pb", None) and self.pb.isVisible():
            self.pb.close()

        if not self.users.ensureUser():
            return False

        if not self.sanities.runChecks("onOpenProjectBrowser")["passed"]:
            return False

        mods = QApplication.keyboardModifiers()
        if not getattr(self, "pb", None) or self.debugMode or mods == Qt.ControlModifier:
            if self.uiAvailable and eval(os.getenv("PRISM_DEBUG", "False")):
                try:
                    del sys.modules["ProjectBrowser"]
                except:
                    pass

            try:
                import ProjectBrowser
            except Exception as e:
                if self.debugMode:
                    traceback.print_exc()

                msgString = "Could not load the ProjectBrowser:\n\n%s" % str(e)
                self.popup(msgString)
                return False

            self.pb = ProjectBrowser.ProjectBrowser(core=self)
        else:
            self.pb.refreshUI()

        if openUi:
            self.pb.show()
            self.pb.activateWindow()
            self.pb.raise_()
            self.pb.checkVisibleTabs()
            if self.pb.isMinimized():
                self.pb.showNormal()

        return self.pb

    @err_catcher(name=__name__)
    def dependencyViewer(self, depRoot: str = "", modal: bool = False) -> Any:
        """Open the Dependency Viewer.
        
        Args:
            depRoot (str, optional): Root dependency to display. Defaults to "".
            modal (bool, optional): Show as modal dialog. Defaults to False.
            
        Returns:
            Any: Dependency Viewer instance or False if failed.
        """
        if getattr(self, "dv", None) and self.dv.isVisible():
            self.dv.close()

        if not getattr(self, "dv", None) or self.debugMode:
            if eval(os.getenv("PRISM_DEBUG", "False")):
                try:
                    del sys.modules["DependencyViewer"]
                except:
                    pass

            try:
                import DependencyViewer
            except Exception as e:
                msgString = "Could not load the DependencyViewer:\n\n%s" % str(e)
                self.popup(msgString)
                return False

            self.dv = DependencyViewer.DependencyViewer(core=self, depRoot=depRoot)
        else:
            self.dv.setRoot(depRoot)

        if modal:
            self.dv.exec_()
        else:
            self.dv.show()

        return True

    @err_catcher(name=__name__)
    def prismSettings(self, tab: Union[int, str] = 0, restart: bool = False, reload_module: Optional[bool] = None, settingsType: Optional[str] = None) -> Any:
        """Open Prism Settings dialog.
        
        Args:
            tab (Union[int, str], optional): Tab index or name to open. Defaults to 0.
            restart (bool, optional): Force restart of settings. Defaults to False.
            reload_module (bool, optional): Reload module before opening. 
                Defaults to None.
            settingsType (str, optional): Type of settings to display. Defaults to None.
            
        Returns:
            Any: Settings dialog instance.
        """
        if getattr(self, "ps", None) and self.ps.isVisible():
            self.ps.close()

        if not self.appPlugin:
            return

        mods = QApplication.keyboardModifiers()
        if not getattr(self, "ps", None) or self.debugMode or restart or reload_module or mods == Qt.ControlModifier:
            if (not getattr(self, "ps", None) or self.debugMode or reload_module) and reload_module is not False:
                try:
                    del sys.modules["PrismSettings"]
                except:
                    pass

                try:
                    del sys.modules["ProjectSettings"]
                except:
                    pass

            import PrismSettings
            self.ps = PrismSettings.PrismSettings(core=self)

        self.ps.show()
        self.ps.navigate({"tab": tab, "settingsType": settingsType})
        self.ps.activateWindow()
        self.ps.raise_()
        if self.ps.isMinimized():
            self.ps.showNormal()

        return self.ps

    @err_catcher(name=__name__)
    def getInstaller(self, plugins: Optional[List[str]] = None, parent: Optional[Any] = None) -> Any:
        """Get the Prism Installer instance.
        
        Args:
            plugins (List[str], optional): List of plugins to install. Defaults to None.
            parent (Any, optional): Parent widget. Defaults to None.
            
        Returns:
            Any: Installer instance.
        """
        if getattr(self, "pinst", None) and self.pinst.isVisible():
            self.pinst.close()

        if eval(os.getenv("PRISM_DEBUG", "False")):
            try:
                del sys.modules["PrismInstaller"]
            except:
                pass

        try:
            import PrismInstaller
        except:
            if self.core.appPlugin.pluginName != "Standalone":
                msg = "Unable to load PrismInstaller module in current environment.\n\nPlease try again in Prism standalone."
                self.core.popup(msg)
                return
            else:
                raise

        self.pinst = PrismInstaller.PrismInstaller(core=self, plugins=plugins, parent=parent)
        return self.pinst

    @err_catcher(name=__name__)
    def openInstaller(self) -> None:
        """Open the Prism Installer dialog."""
        pinst = self.getInstaller()
        pinst.show()

    @err_catcher(name=__name__)
    def openSetup(self, silent: bool = False) -> Any:
        """Open the Prism Setup dialog.
        
        Args:
            silent (bool, optional): Don't show dialog. Defaults to False.
            
        Returns:
            Any: Setup dialog instance.
        """
        if getattr(self, "psetup", None) and self.psetup.isVisible():
            self.psetup.close()

        if eval(os.getenv("PRISM_DEBUG", "False")):
            try:
                del sys.modules["PrismInstaller"]
            except:
                pass

        import PrismInstaller

        self.psetup = PrismInstaller.PrismSetup(core=self)
        if not silent:
            self.psetup.show()

        return self.psetup

    @err_catcher(name=__name__)
    def openConsole(self, parent: Optional[Any] = None) -> None:
        """Open a Python console.
        
        Opens console in new process if Ctrl is held, otherwise in-process.
        
        Args:
            parent (Any, optional): Parent widget. Defaults to None.
        """
        mods = QApplication.keyboardModifiers()
        if mods == Qt.ControlModifier:
            executable = self.getPythonPath(executable="python")
            code = "\"import sys;sys.path.append(\\\"%s/Scripts\\\");import PrismCore;pcore=PrismCore.create(prismArgs=[\\\"noUI\\\", \\\"loadProject\\\"])" % (self.prismRoot.replace("\\", "/"))
            cmd = "start \"\" \"%s\" -i -c %s" % (executable, code)
            logger.debug("opening console: %s" % cmd)
            subprocess.Popen(cmd, shell=True, env=self.startEnv)
        else:
            self.openConsoleInProcess(parent)

    @err_catcher(name=__name__)
    def openConsoleInProcess(self, parent: Optional[Any] = None) -> None:
        """Open Python console within current process.
        
        Args:
            parent (Any, optional): Parent widget. Defaults to None.
        """
        if getattr(self, "dlg_console", None) and self.dlg_console.isVisible():
            self.dlg_console.close()

        local_ns = {
            "pcore": self,
            "print": print  # allow print to be explicitly available
        }
        self.dlg_console = PythonConsole(self, local_ns, parent=parent)
        self.dlg_console.show()

    @err_catcher(name=__name__)
    def startTray(self) -> Any:
        """Start the Prism system tray application.
        
        Returns:
            Any: PrismTray instance if created, None otherwise.
        """
        if (
            getattr(self, "PrismTray", None)
            or self.appPlugin.pluginName != "Standalone"
        ):
            return

        import PrismTray
        self.PrismTray = PrismTray.PrismTray(core=self)
        return self.PrismTray

    @err_catcher(name=__name__)
    def setupStartMenu(self, quiet: bool = False) -> None:
        """Create Windows Start Menu entries for Prism.
        
        Args:
            quiet (bool, optional): Suppress popup notifications. Defaults to False.
        """
        if self.appPlugin.pluginName == "Standalone":
            result = self.appPlugin.createWinStartMenu(self)
            if "silent" not in self.prismArgs and not quiet:
                if result:
                    msg = "Successfully added start menu entries."
                    self.popup(msg, severity="info")
                else:
                    msg = "Creating start menu entries failed"
                    self.popup(msg, severity="warning")

    @err_catcher(name=__name__)
    def setupUninstaller(self, quiet: bool = False) -> None:
        """Register Prism uninstaller in Windows registry.
        
        Args:
            quiet (bool, optional): Suppress popup notifications. Defaults to False.
        """
        if self.appPlugin.pluginName == "Standalone":
            cmd = "import sys;sys.path.append('%s');import PrismCore;core = PrismCore.create(prismArgs=['noUI']);core.appPlugin.addUninstallerToWindowsRegistry()" % os.path.dirname(__file__).replace("\\", "/")
            self.winRunAsAdmin(cmd)
            result = self.core.appPlugin.validateUninstallerInWindowsRegistry()
            if "silent" not in self.prismArgs and not quiet:
                if result:
                    msg = "Successfully added uninstaller."
                    self.popup(msg, severity="info")
                else:
                    msg = "Adding uninstaller failed"
                    self.popup(msg, severity="warning")

    @err_catcher(name=__name__)
    def getConfig(
        self,
        cat: Optional[str] = None,
        param: Optional[str] = None,
        configPath: Optional[str] = None,
        config: Optional[Any] = None,
        dft: Optional[Any] = None,
        location: Optional[str] = None,
        allowCache: bool = True,
    ) -> Any:
        """Get configuration value from Prism config files.
        
        Args:
            cat (str, optional): Configuration category. Defaults to None.
            param (str, optional): Parameter name within category. Defaults to None.
            configPath (str, optional): Path to config file. Defaults to None.
            config (Any, optional): Existing config dict. Defaults to None.
            dft (Any, optional): Default value if not found. Defaults to None.
            location (str, optional): Config location scope. Defaults to None.
            allowCache (bool, optional): Use cached config data. Defaults to True.
            
        Returns:
            Any: Configuration value or default.
        """
        return self.configs.getConfig(
            cat=cat,
            param=param,
            configPath=configPath,
            config=config,
            dft=dft,
            location=location,
            allowCache=allowCache,
        )

    @err_catcher(name=__name__)
    def setConfig(
        self,
        cat: Optional[str] = None,
        param: Optional[str] = None,
        val: Optional[Any] = None,
        data: Optional[Any] = None,
        configPath: Optional[str] = None,
        delete: bool = False,
        config: Optional[Any] = None,
        location: Optional[str] = None,
        updateNestedData: bool = True,
    ) -> Any:
        """Set configuration value in Prism config files.
        
        Args:
            cat (str, optional): Configuration category. Defaults to None.
            param (str, optional): Parameter name within category. Defaults to None.
            val (Any, optional): Value to set. Defaults to None.
            data (Any, optional): Complete data dict to set. Defaults to None.
            configPath (str, optional): Path to config file. Defaults to None.
            delete (bool, optional): Delete the parameter. Defaults to False.
            config (Any, optional): Existing config dict. Defaults to None.
            location (str, optional): Config location scope. Defaults to None.
            updateNestedData (bool, optional): Update nested dicts. Defaults to True.
            
        Returns:
            Any: Configuration write result.
        """
        return self.configs.setConfig(
            cat=cat,
            param=param,
            val=val,
            data=data,
            configPath=configPath,
            delete=delete,
            config=config,
            location=location,
            updateNestedData=updateNestedData,
        )

    @err_catcher(name=__name__)
    def readYaml(self, path: Optional[str] = None, data: Optional[Any] = None, stream: Optional[Any] = None) -> Any:
        """Read YAML file and return parsed data.
        
        Args:
            path (str, optional): File path to read. Defaults to None.
            data (Any, optional): Data string to parse. Defaults to None.
            stream (Any, optional): Stream object to read from. Defaults to None.
            
        Returns:
            Any: Parsed YAML data.
        """
        return self.configs.readYaml(
            path=path,
            data=data,
            stream=stream,
        )

    @err_catcher(name=__name__)
    def writeYaml(self, path: Optional[str] = None, data: Optional[Any] = None, stream: Optional[Any] = None) -> Any:
        """Write data to YAML file.
        
        Args:
            path (str, optional): File path to write. Defaults to None.
            data (Any, optional): Data to serialize. Defaults to None.
            stream (Any, optional): Stream object to write to. Defaults to None.
            
        Returns:
            Any: Write result.
        """
        return self.configs.writeYaml(path=path, data=data, stream=stream)

    @err_catcher(name=__name__)
    def missingModule(self, moduleName: str) -> None:
        """Display warning popup for missing Python module.
        
        Args:
            moduleName (str): Name of missing module.
        """
        if moduleName not in self.missingModules:
            self.missingModules.append(moduleName)
            msg = 'Module "%s" couldn\'t be loaded.\nMake sure you have the latest Prism version installed.' % moduleName
            if os.getenv("PRISM_MISSING_MODULES_WARNING", "1").lower() == "1":
                self.popup(msg, title="Couldn't load module")
            else:
                logger.debug(msg)

    @err_catcher(name=__name__)
    def resolveFrameExpression(self, expression: str) -> List[int]:
        """Parse frame range expression into list of frame numbers.
        
        Supports ranges (1-10), steps (1-10x2), exclusions (^5), and combinations.
        
        Args:
            expression (str): Frame expression (e.g., "1-10,15,20-30x2,^25").
            
        Returns:
            List[int]: List of resolved frame numbers.
        """
        eChunks = expression.split(",")
        rframes = []
        for chunk in eChunks:
            cData = chunk.split("x")
            if len(cData) > 2:
                continue
            elif len(cData) == 2:
                try:
                    step = int(cData[1])
                except:
                    continue

                if step == 0:
                    continue
            else:
                step = 1

            if cData[0].strip().startswith("^"):
                mode = "substract"
                cData[0] = cData[0].strip().strip("^")
            else:
                mode = "add"

            se = [x for x in cData[0].split("-") if x]
            if len(se) == 2:
                try:
                    start = int(se[0])
                    end = int(se[1])
                except:
                    continue

            elif len(se) == 1:
                try:
                    frame = int(se[0])
                except:
                    continue
                if frame not in rframes and mode == "add":
                    rframes.append(frame)
                    if len(rframes) > 10000:
                        return rframes

                elif frame in rframes and mode == "substract":
                    rframes.remove(frame)

                continue
            else:
                continue

            if end < start:
                step *= -1
                end -= 1
            else:
                end += 1

            for frame in range(start, end, step):
                if frame not in rframes and mode == "add":
                    rframes.append(frame)
                    if len(rframes) > 10000:
                        return rframes
                elif frame in rframes and mode == "substract":
                    rframes.remove(frame)

        return rframes

    @err_catcher(name=__name__)
    def validateLineEdit(self, widget: Any, allowChars: Optional[List[str]] = None, denyChars: Optional[List[str]] = None) -> str:
        """Validate and clean text in QLineEdit widget.
        
        Args:
            widget (Any): QLineEdit widget to validate.
            allowChars (List[str], optional): Explicitly allowed characters. Defaults to None.
            denyChars (List[str], optional): Explicitly denied characters. Defaults to None.
            
        Returns:
            str: Validated text after removing invalid characters.
        """
        if not hasattr(widget, "text"):
            return

        origText = widget.text()
        validText = self.validateStr(
            origText, allowChars=allowChars, denyChars=denyChars
        )

        cpos = widget.cursorPosition()
        widget.setText(validText)
        if len(validText) != len(origText):
            cpos -= 1

        widget.setCursorPosition(cpos)
        return validText

    @err_catcher(name=__name__)
    def validateStr(self, text: str, allowChars: Optional[List[str]] = None, denyChars: Optional[List[str]] = None) -> str:
        """Remove invalid filename characters from string.
        
        Args:
            text (str): Text to validate.
            allowChars (List[str], optional): Explicitly allowed characters. Defaults to None.
            denyChars (List[str], optional): Explicitly denied characters. Defaults to None.
            
        Returns:
            str: Validated string with invalid characters replaced.
        """
        invalidChars = [
            "\\",
            "/",
            ":",
            "*",
            "?",
            '"',
            "<",
            ">",
            "|",
        ]
        if allowChars:
            for i in allowChars:
                if i in invalidChars:
                    invalidChars.remove(i)

        if denyChars:
            for i in denyChars:
                if i not in invalidChars:
                    invalidChars.append(i)

        if "_" not in invalidChars:
            fallbackChar = "_"
        elif "-" not in invalidChars:
            fallbackChar = "-"
        elif "." not in invalidChars:
            fallbackChar = "."
        else:
            fallbackChar = ""

        validText = "".join(
            ch if ch not in invalidChars else fallbackChar
            for ch in str(text.encode("utf8", errors="ignore").decode())
        )
        return validText

    @err_catcher(name=__name__)
    def isStr(self, data: Any) -> bool:
        """Check if data is a string type.
        
        Args:
            data (Any): Data to check.
            
        Returns:
            bool: True if data is string, False otherwise.
        """
        return isinstance(data, str)

    @err_catcher(name=__name__)
    def getIconForFileType(self, extension: str) -> Any:
        """Get QIcon for file type based on extension.
        
        Args:
            extension (str): File extension.
            
        Returns:
            Any: QIcon object for the file type.
        """
        if extension in self.iconCache:
            return self.iconCache[extension]

        paths = self.callback("getIconPathForFileType", args=[extension])
        paths = [p for p in paths if p]
        if paths:
            path = paths[0]
        else:
            path = None

        if extension in self.core.appPlugin.sceneFormats:
            path = getattr(self.core.appPlugin, "appIcon", path)
        else:
            for k in self.core.unloadedAppPlugins.values():
                if extension in k.sceneFormats:
                    path = getattr(k, "appIcon", path)

        if path:
            icon = QIcon(path)
            self.iconCache[extension] = icon
            return icon

    @err_catcher(name=__name__)
    def getCurrentFileName(self, path: bool = True) -> str:
        """Get current scene filename from active DCC application.
        
        Args:
            path (bool, optional): Return full path. Defaults to True.
            
        Returns:
            str: Current filename or empty string.
        """
        currentFileName = self.appPlugin.getCurrentFileName(self, path) or ""
        currentFileName = self.fixPath(currentFileName)
        return currentFileName

    @err_catcher(name=__name__)
    def fileInPipeline(self, filepath: Optional[str] = None, validateFilename: bool = True) -> bool:
        """Check if file is within current Prism project structure.
        
        Args:
            filepath (str, optional): File path to check. Uses current file if None. Defaults to None.
            validateFilename (bool, optional): Validate Prism naming convention. Defaults to True.
            
        Returns:
            bool: True if file is in project pipeline, False otherwise.
        """
        if filepath is None:
            filepath = self.getCurrentFileName()
            if not filepath:
                return False

        filepath = self.fixPath(filepath)
        validName = False
        if validateFilename:
            fileNameData = self.getScenefileData(filepath)
            validName = fileNameData.get("type") in ["asset", "shot"]

        filepath = filepath.lower()
        useEpisodes = self.core.getConfig(
            "globals",
            "useEpisodes",
            config="project",
        ) or False
        if useEpisodes:
            key = "episodes"
        else:
            key = "sequences"

        shotPath = os.path.dirname(
            self.projects.getResolvedProjectStructurePath(key)
        )

        if (
            (
                self.fixPath(self.assetPath).lower() in filepath
                or self.fixPath(shotPath).lower() in filepath
            )
            or (
                self.useLocalFiles
                and (
                    self.fixPath(self.core.getAssetPath(location="local")).lower() in filepath
                    or self.fixPath(self.core.convertPath(shotPath, "local")).lower() in filepath
                )
            )
        ) and (validName or not validateFilename):
            return True
        else:
            return False

    @err_catcher(name=__name__)
    def detectFileSequence(self, path: str) -> List[str]:
        """Detect image sequence files matching pattern.
        
        Args:
            path (str): Path pattern with frame number (supports $F4).
            
        Returns:
            List[str]: List of matching sequence files.
        """
        pathDir = os.path.dirname(path)
        regName = ""
        seqFiles = []
        siblings = []

        path = path.replace("$F4", "1001")
        for root, folders, files in os.walk(pathDir):
            siblings = [os.path.join(root, f) for f in files]
            break

        for ch in re.escape(os.path.basename(path)):
            if ch.isnumeric():
                regName += "."
            else:
                regName += ch

        r = re.compile(regName)
        for sibling in siblings:
            if r.match(os.path.basename(sibling)):
                seqFiles.append(sibling)

        if not seqFiles:
            logger.debug("No sequence files detected for pattern: %s - %s - %d siblings" % (path, regName, len(siblings)))

        return seqFiles

    @err_catcher(name=__name__)
    def getFilesFromFolder(self, path: str, recursive: bool = True) -> List[str]:
        """Get all files from folder.
        
        Args:
            path (str): Folder path to search.
            recursive (bool, optional): Include subfolders. Defaults to True.
            
        Returns:
            List[str]: List of file paths.
        """
        foundFiles = []
        for root, folders, files in os.walk(path):
            for file in files:
                path = os.path.join(root, file)
                foundFiles.append(path)

            if not recursive:
                break

        return foundFiles

    @err_catcher(name=__name__)
    def getEntityPath(self, *args: Any, **kwargs: Any) -> Any:
        """Get file system path for entity.
        
        Args:
            *args: Variable positional arguments for paths manager.
            **kwargs: Variable keyword arguments for paths manager.
            
        Returns:
            Any: Entity path.
        """
        return self.paths.getEntityPath(*args, **kwargs)

    @err_catcher(name=__name__)
    def generateScenePath(self, *args: Any, **kwargs: Any) -> Any:
        """Generate valid scene file path following Prism naming convention.
        
        Args:
            *args: Variable positional arguments for paths manager.
            **kwargs: Variable keyword arguments for paths manager.
            
        Returns:
            Any: Generated scene file path.
        """
        return self.paths.generateScenePath(*args, **kwargs)

    @err_catcher(name=__name__)
    def getScenefileData(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Extract metadata from scene filename.
        
        Args:
            *args: Variable positional arguments for entities manager.
            **kwargs: Variable keyword arguments for entities manager.
            
        Returns:
            Dict[str, Any]: Scene file metadata (entity, task, version, etc.).
        """
        return self.entities.getScenefileData(*args, **kwargs)

    @err_catcher(name=__name__)
    def getCurrentScenefileData(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Extract metadata from current scene file.
        
        Args:
            *args: Variable positional arguments for entities manager.
            **kwargs: Variable keyword arguments for entities manager.
            
        Returns:
            Dict[str, Any]: Current scene file metadata.
        """
        return self.entities.getCurrentScenefileData(*args, **kwargs)

    @err_catcher(name=__name__)
    def getHighestVersion(self, *args: Any, **kwargs: Any) -> Any:
        """Get highest version number for entity/task combination.
        
        Args:
            *args: Variable positional arguments for entities manager.
            **kwargs: Variable keyword arguments for entities manager.
            
        Returns:
            Any: Highest version data.
        """
        return self.entities.getHighestVersion(*args, **kwargs)

    @err_catcher(name=__name__)
    def getTaskNames(self, *args: Any, **kwargs: Any) -> Any:
        """Get available task names for entity.
        
        Args:
            *args: Variable positional arguments for entities manager.
            **kwargs: Variable keyword arguments for entities manager.
            
        Returns:
            Any: Task names list.
        """
        return self.entities.getTaskNames(*args, **kwargs)

    @err_catcher(name=__name__)
    def getAssetPath(self, location: str = "global") -> str:
        """Get root path for assets.
        
        Args:
            location (str, optional): Storage location (global/local). Defaults to "global".
            
        Returns:
            str: Asset root path.
        """
        path = os.path.dirname(self.projects.getResolvedProjectStructurePath("assets"))
        path = os.path.normpath(path)

        if location != "global":
            if location == "local":
                prjPath = self.localProjectPath
            else:
                prjPath = self.paths.getExportProductBasePaths().get(location, "")
                if not prjPath:
                    prjPath = self.paths.getRenderProductBasePaths().get(location, "")

            if prjPath:
                prjPath = os.path.normpath(prjPath)
            
            path = path.replace(os.path.normpath(self.projectPath), prjPath)

        return path

    @property
    def assetPath(self) -> str:
        """Get cached asset root path.
        
        Returns:
            str: Asset root path.
        """
        if not getattr(self, "_assetPath", None):
            self._assetPath = self.getAssetPath()

        return self._assetPath

    @err_catcher(name=__name__)
    def getShotPath(self, location: str = "global") -> str:
        """Get root path for shots.
        
        Args:
            location (str, optional): Storage location (global/local). Defaults to "global".
            
        Returns:
            str: Shot root path.
        """
        path = os.path.dirname(self.projects.getResolvedProjectStructurePath("shots"))
        path = os.path.normpath(path)

        if location != "global":
            if location == "local":
                prjPath = self.localProjectPath
            else:
                prjPath = self.paths.getExportProductBasePaths().get(location, "")
                if not prjPath:
                    prjPath = self.paths.getRenderProductBasePaths().get(location, "")

            if prjPath:
                prjPath = os.path.normpath(prjPath)

            path = path.replace(os.path.normpath(self.projectPath), prjPath)

        return path

    @property
    def shotPath(self) -> str:
        """Get cached shot root path.
        
        Returns:
            str: Shot root path.
        """
        if not getattr(self, "_shotPath", None):
            self._shotPath = self.getShotPath()

        return self._shotPath

    @err_catcher(name=__name__)
    def getSequencePath(self, location: str = "global") -> str:
        """Get root path for sequences.
        
        Args:
            location (str, optional): Storage location (global/local). Defaults to "global".
            
        Returns:
            str: Sequence root path.
        """
        path = os.path.dirname(
            self.projects.getResolvedProjectStructurePath("sequences")
        )
        path = os.path.normpath(path)

        if location != "global":
            if location == "local":
                prjPath = self.localProjectPath
            else:
                prjPath = self.paths.getExportProductBasePaths().get(location, "")
                if not prjPath:
                    prjPath = self.paths.getRenderProductBasePaths().get(location, "")

            if prjPath:
                prjPath = os.path.normpath(prjPath)

            path = path.replace(os.path.normpath(self.projectPath), prjPath)

        return path

    @property
    def sequencePath(self) -> str:
        """Get cached sequence root path.
        
        Returns:
            str: Sequence root path.
        """
        if not getattr(self, "_sequencePath", None):
            self._sequencePath = self.getSequencePath()

        return self._sequencePath

    @err_catcher(name=__name__)
    def getEpisodePath(self, location: str = "global") -> str:
        """Get root path for episodes.
        
        Args:
            location (str, optional): Storage location (global/local). Defaults to "global".
            
        Returns:
            str: Episode root path.
        """
        path = os.path.dirname(
            self.projects.getResolvedProjectStructurePath("episodes") or ""
        )
        path = os.path.normpath(path)

        if location != "global":
            if location == "local":
                prjPath = self.localProjectPath
            else:
                prjPath = self.paths.getExportProductBasePaths().get(location, "")
                if not prjPath:
                    prjPath = self.paths.getRenderProductBasePaths().get(location, "")

            if prjPath:
                prjPath = os.path.normpath(prjPath)

            path = path.replace(os.path.normpath(self.projectPath), prjPath)

        return path

    @property
    def episodePath(self) -> str:
        """Get cached episode root path.
        
        Returns:
            str: Episode root path.
        """
        if not getattr(self, "_episodePath", None):
            self._episodePath = self.getEpisodePath()

        return self._episodePath

    @err_catcher(name=__name__)
    def convertPath(self, path: str, target: str = "global") -> str:
        """Convert path between storage locations (global/local).
        
        Args:
            path (str): Path to convert.
            target (str, optional): Target location. Defaults to "global".
            
        Returns:
            str: Converted path for target location.
        """
        if target == "local" and not self.useLocalFiles:
            return path

        path = os.path.normpath(path)
        source = self.paths.getLocationFromPath(path)
        if source and source != target:
            sourcePath = os.path.normpath(self.paths.getLocationPath(source))
            targetLoc = self.paths.getLocationPath(target)
            if not targetLoc:
                msg = "Location doesn't exist: \"%s\"" % target
                self.core.popup(msg)
                return

            targetPath = os.path.normpath(targetLoc)
            path = os.path.normpath(path.replace(sourcePath, targetPath))

        return path

    @err_catcher(name=__name__)
    def getTexturePath(self, location: str = "global") -> str:
        """Get texture library path.
        
        Args:
            location (str, optional): Storage location. Defaults to "global".
            
        Returns:
            str: Texture path.
        """
        path = self.projects.getResolvedProjectStructurePath("textures")
        path = os.path.normpath(path)
        return path

    @property
    def texturePath(self) -> str:
        """Get cached texture library path.
        
        Returns:
            str: Texture path.
        """
        if not getattr(self, "_texturePath", None):
            self._texturePath = self.getTexturePath()

        return self._texturePath

    @err_catcher(name=__name__)
    def showFileNotInProjectWarning(self, title: Optional[str] = None, msg: Optional[str] = None, currentFilepath: Optional[str] = None) -> None:
        """Display warning when file is outside project structure.
        
        Args:
            title (str, optional): Dialog title. Defaults to None.
            msg (str, optional): Warning message. Defaults to None.
            currentFilepath (str, optional): Current file path. Defaults to None.
        """
        logger.debug("currentfilepath: %s, projectpath: %s" % (currentFilepath, getattr(self, "projectPath", None)))
        title = title or "Could not save the file"
        msg = msg or "The current scenefile is not saved in the current Prism project.\nUse the Project Browser to save your scene in the project."
        buttons = ["Open Project Browser", "Close"]
        result = self.popupQuestion(msg, buttons=buttons, title=title, icon=QMessageBox.Warning)
        if result == "Open Project Browser":
            if self.pb and self.pb.isVisible():
                self.pb.activateWindow()
                self.pb.raise_()
                self.pb.checkVisibleTabs()
                if self.pb.isMinimized():
                    self.pb.showNormal()
            else:
                self.projectBrowser()

            if self.pb:
                self.pb.showTab("Scenefiles")

        mods = QApplication.keyboardModifiers()
        if mods == Qt.ControlModifier:
            curFile = self.getCurrentFileName()
            localProjectPath = self.localProjectPath if self.useLocalFiles else ""
            msg = "Project Path: %s\nScenefile Path: %s\nLocal Project Enabled: %s\nLocal Project Path: %s\nFile in Project: %s\nPrism Version: %s" % (getattr(self.core, "projectPath", None), curFile, self.useLocalFiles, localProjectPath, self.fileInPipeline(curFile), self.version)
            self.core.popup(msg)

    @err_catcher(name=__name__)
    def saveScene(
        self,
        comment: str = "",
        publish: bool = False,
        versionUp: bool = True,
        prismReq: bool = True,
        filepath: str = "",
        details: Optional[Dict[str, Any]] = None,
        preview: Optional[Any] = None,
        location: str = "local",
    ) -> Any:
        """Save current scene file with Prism metadata.
        
        Args:
            comment (str, optional): Version comment. Defaults to "".
            publish (bool, optional): Save as published version. Defaults to False.
            versionUp (bool, optional): Increment version number. Defaults to True.
            prismReq (bool, optional): Enforce Prism requirements. Defaults to True.
            filepath (str, optional): Target filepath. Defaults to "".
            details (Dict[str, Any], optional): Additional metadata. Defaults to None.
            preview (Any, optional): Preview image pixmap. Defaults to None.
            location (str, optional): Storage location. Defaults to "local".
            
        Returns:
            Any: Saved filepath or False on failure.
        """
        details = details or {}
        if filepath == "":
            curfile = self.getCurrentFileName()
            filepath = curfile.replace("\\", "/")
            if not filepath:
                self.showFileNotInProjectWarning(currentFilepath=filepath)
                return False
        else:
            if not os.path.exists(os.path.dirname(filepath)):
                try:
                    os.makedirs(os.path.dirname(filepath))
                except Exception as e:
                    title = "Could not save the file"
                    msg = "Could not create this folder:\n\n%s\n\n%s" % (
                        os.path.dirname(filepath),
                        str(e),
                    )
                    self.popup(msg, title=title)
                    return False

            versionUp = False
            curfile = None

        if prismReq:
            if not self.projects.ensureProject():
                return False

            if not self.users.ensureUser():
                return False

            if not self.fileInPipeline(filepath, validateFilename=False):
                self.showFileNotInProjectWarning(currentFilepath=filepath)
                return False

            if self.useLocalFiles:
                if location == "local":
                    filepath = self.fixPath(filepath).replace(
                        self.projectPath, self.localProjectPath
                    )
                elif location == "global":
                    filepath = self.fixPath(filepath).replace(
                        self.localProjectPath, self.projectPath
                    )

                if not os.path.exists(os.path.dirname(filepath)):
                    try:
                        os.makedirs(os.path.dirname(filepath))
                    except Exception as e:
                        title = "Could not save the file"
                        msg = "Could not create this folder:\n\n%s\n\n%s" % (
                            os.path.dirname(filepath),
                            str(e),
                        )
                        self.popup(msg, title=title)
                        return False

            if versionUp:
                fnameData = self.getScenefileData(curfile, getEntityFromPath=True)
                if "department" not in fnameData:
                    title = "Could not save the file"
                    msg = "Couldn't get the required data from the current scenefile. Did you save it using Prism?\nUse the Project Browser to save your current scenefile with the correct name."
                    self.popup(msg, title=title)
                    return False

                if "project_path" in fnameData:
                    del fnameData["project_path"]

                fVersion = self.getHighestVersion(fnameData, fnameData.get("department"), fnameData.get("task"))
                filepath = self.generateScenePath(
                    entity=fnameData,
                    department=fnameData["department"],
                    task=fnameData["task"],
                    comment=comment,
                    extension=self.appPlugin.getSceneExtension(self),
                    location=location,
                )

        filepath = filepath.replace("\\", "/")
        outLength = len(filepath)
        if platform.system() == "Windows" and os.getenv("PRISM_IGNORE_PATH_LENGTH") != "1" and outLength > 255:
            msg = (
                "The filepath is longer than 255 characters (%s), which is not supported on Windows."
                % outLength
            )
            self.popup(msg)
            return False

        result = self.callback(
            name="preSaveScene",
            args=[self, filepath, versionUp, comment, publish, details],
        )
        for res in result:
            if isinstance(res, dict) and res.get("cancel", False):
                return

            if isinstance(res, dict) and res.get("comment", False):
                comment = res["comment"]

        result = self.appPlugin.saveScene(self, filepath, details)
        if result is False:
            logger.debug("failed to save scene")
            return False

        if curfile:
            detailData = self.getScenefileData(curfile)
            if detailData.get("type") == "asset":
                key = "assetScenefiles"
                if "sequence" in detailData:
                    del detailData["sequence"]

                if "shot" in detailData:
                    del detailData["shot"]

            elif detailData.get("type") == "shot":
                key = "shotScenefiles"
                if "asset" in detailData:
                    del detailData["asset"]

                if "asset_path" in detailData:
                    del detailData["asset_path"]

            else:
                if "project_name" in detailData:
                    del detailData["project_name"]

                key = None

            if key:
                template = self.core.projects.getTemplatePath(key)
                pathdata = self.core.projects.extractKeysFromPath(filepath, template, context=detailData)
                if pathdata.get("asset_path"):
                    pathdata["asset"] = os.path.basename(pathdata["asset_path"])

                if pathdata.get("project_name"):
                    del pathdata["project_name"]

                detailData.update(pathdata)

            detailData["comment"] = comment

            if "user" in detailData:
                del detailData["user"]
            if "username" in detailData:
                del detailData["username"]
            if "description" in detailData:
                del detailData["description"]
            if "locations" in detailData:
                del detailData["locations"]
        else:
            detailData = {
                "comment": comment
            }

        detailData.update(details)
        if prismReq:
            if versionUp:
                detailData["version"] = fVersion

            if not preview and self.core.getConfig("globals", "capture_viewport", config="user", dft=True):
                appPreview = getattr(self.appPlugin, "captureViewportThumbnail", lambda: None)()
                if appPreview:
                    preview = self.media.scalePixmap(appPreview, self.scenePreviewWidth, self.scenePreviewHeight, fitIntoBounds=False, crop=True)

            self.saveSceneInfo(filepath, detailData, preview=preview)
        
        details = detailData
        self.callback(
            name="postSaveScene",
            args=[self, filepath, versionUp, comment, publish, details],
        )

        if not prismReq:
            return filepath

        if (
            not os.path.exists(filepath)
            and os.path.splitext(self.fixPath(self.getCurrentFileName()))[0]
            != os.path.splitext(self.fixPath(filepath))[0]
        ):
            logger.debug("expected file doesn't exist")
            return False

        self.addToRecent(filepath)

        if publish:
            pubFile = filepath
            if self.useLocalFiles and location != "global":
                pubFile = self.fixPath(filepath).replace(
                    self.localProjectPath, self.projectPath
                )
                self.copySceneFile(filepath, pubFile)

            infoData = {
                "filename": os.path.basename(pubFile),
                "fps": self.getFPS(),
            }
            if versionUp:
                infoData["version"] = fVersion

            self.saveVersionInfo(filepath=pubFile, details=infoData)

        if getattr(self, "sm", None):
            self.sm.scenename = self.getCurrentFileName()

        try:
            self.pb.sceneBrowser.refreshScenefilesThreaded()
        except:
            pass

        return filepath

    @err_catcher(name=__name__)
    def getVersioninfoPath(self, scenepath: str) -> str:
        """Get versioninfo file path for scene file.
        
        Args:
            scenepath (str): Scene file path.
            
        Returns:
            str: Version info file path.
        """
        prefExt = self.configs.getProjectExtension()
        base, ext = os.path.splitext(scenepath)
        if ext:
            filepath = base + "versioninfo" + prefExt
        else:
            filepath = os.path.join(base, "versioninfo" + prefExt)
        return filepath

    @err_catcher(name=__name__)
    def saveSceneInfo(self, filepath: str, details: Optional[Dict[str, Any]] = None, preview: Optional[Any] = None, clean: bool = True, replace: bool = False) -> None:
        """Save scene metadata to versioninfo file.
        
        Args:
            filepath (str): Scene file path.
            details (Dict[str, Any], optional): Metadata dict. Defaults to None.
            preview (Any, optional): Preview pixmap. Defaults to None.
            clean (bool, optional): Remove internal keys. Defaults to True.
            replace (bool, optional): Replace all data. Defaults to False.
        """
        details = details or {}
        if "username" not in details:
            details["username"] = self.username

        if "user" not in details:
            details["user"] = self.user

        doDeps = self.getConfig("globals", "track_dependencies", config="project")
        if doDeps == "always":
            deps = self.entities.getCurrentDependencies()
            details["dependencies"] = deps["dependencies"]
            details["externalFiles"] = deps["externalFiles"]

        if replace:
            sData = details
        else:
            sData = self.getScenefileData(filepath)
            if "project_name" in sData and self.fileInPipeline(filepath, validateFilename=False):
                del sData["project_name"]

            sData.update(details)

        if clean:
            keys = ["filename", "extension", "path", "paths", "task_path"]
            for key in keys:
                if key in sData:
                    del sData[key]

        infoPath = self.getVersioninfoPath(filepath)
        self.setConfig(configPath=infoPath, data=sData, updateNestedData=not replace)

        if preview:
            self.core.entities.setScenePreview(filepath, preview)

    @err_catcher(name=__name__)
    def saveVersionInfo(self, filepath: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Save version info for published scene file.
        
        Args:
            filepath (str): Scene file path.
            details (Dict[str, Any], optional): Version metadata. Defaults to None.
        """
        details = details or {}
        if "username" not in details:
            details["username"] = self.username

        if "user" not in details:
            details["user"] = self.user

        if "date" not in details:
            details["date"] = time.strftime("%d.%m.%y %X")

        depsEnabled = self.getConfig("globals", "track_dependencies", config="project")
        if depsEnabled == "publish":
            deps = self.entities.getCurrentDependencies()
            details["dependencies"] = deps["dependencies"]
            details["externalFiles"] = deps["externalFiles"]

        infoFilePath = self.getVersioninfoPath(filepath)
        self.setConfig(data=details, configPath=infoFilePath)

    @err_catcher(name=__name__)
    def saveWithComment(self) -> bool:
        """Open save dialog with comment field.
        
        Returns:
            bool: True if dialog shown, False on validation failure.
        """
        if not self.projects.ensureProject():
            return False

        if not self.users.ensureUser():
            return False

        filepath = self.getCurrentFileName()
        if not self.fileInPipeline(filepath):
            self.showFileNotInProjectWarning(currentFilepath=filepath)
            return False

        self.savec = PrismWidgets.SaveComment(core=self)
        self.savec.accepted.connect(lambda: self.saveWithCommentAccepted(self.savec))
        self.savec.show()
        self.savec.activateWindow()
        return True

    @err_catcher(name=__name__)
    def saveWithCommentAccepted(self, dlg: Any) -> None:
        """Handle save with comment dialog acceptance.
        
        Args:
            dlg (Any): SaveComment dialog instance.
        """
        if dlg.previewDefined:
            prvPMap = dlg.l_preview.pixmap()
        else:
            prvPMap = None

        details = dlg.getDetails() or {}
        self.saveScene(comment=dlg.e_comment.text(), details=details, preview=prvPMap)

    @err_catcher(name=__name__)
    def getScenefilePaths(self, scenePath: str) -> List[str]:
        """Get all related files for scene (versioninfo, preview, etc.).
        
        Args:
            scenePath (str): Scene file path.
            
        Returns:
            List[str]: List of related file paths.
        """
        paths = [scenePath]
        infoPath = (
            os.path.splitext(scenePath)[0]
            + "versioninfo"
            + self.configs.getProjectExtension()
        )
        prvPath = os.path.splitext(scenePath)[0] + "preview.jpg"

        if os.path.exists(infoPath):
            paths.append(infoPath)
        if os.path.exists(prvPath):
            paths.append(prvPath)

        self.callback("getScenefilePaths")

        ext = os.path.splitext(scenePath)[1]
        if ext in self.appPlugin.sceneFormats:
            paths += getattr(self.appPlugin, "getScenefilePaths", lambda x: [])(
                scenePath
            )
        else:
            for i in self.unloadedAppPlugins.values():
                if ext in i.sceneFormats:
                    paths += getattr(i, "getScenefilePaths", lambda x: [])(scenePath)

        return paths

    @err_catcher(name=__name__)
    def copySceneFile(self, origFile: str, targetFile: str, mode: str = "copy") -> None:
        """Copy or move scene file with metadata.
        
        Args:
            origFile (str): Source file path.
            targetFile (str): Destination file path.
            mode (str, optional): "copy" or "move". Defaults to "copy".
        """
        origFile = self.fixPath(origFile)
        targetFile = self.fixPath(targetFile)
        if origFile == targetFile:
            return

        if not os.path.exists(os.path.dirname(targetFile)):
            while not os.path.exists(os.path.dirname(targetFile)):
                try:
                    os.makedirs(os.path.dirname(targetFile))
                except Exception as e:
                    msg = "Failed to create folder:\n\n%s\n\nError: %s" % (os.path.dirname(targetFile), str(e))
                    result = self.core.popupQuestion(msg, buttons=["Retry", "Cancel"], escapeButton="Cancel", icon=QMessageBox.Warning)
                    if result == "Retry":
                        continue
                    else:
                        return

        if mode == "copy":
            shutil.copy2(origFile, targetFile)
        elif mode == "move":
            shutil.move(origFile, targetFile)

        infoPath = (
            os.path.splitext(origFile)[0]
            + "versioninfo"
            + self.configs.getProjectExtension()
        )
        prvPath = os.path.splitext(origFile)[0] + "preview.jpg"
        infoPatht = (
            os.path.splitext(targetFile)[0]
            + "versioninfo"
            + self.configs.getProjectExtension()
        )
        prvPatht = os.path.splitext(targetFile)[0] + "preview.jpg"

        if os.path.exists(infoPath) and not os.path.exists(infoPatht):
            if mode == "copy":
                shutil.copy2(infoPath, infoPatht)
            elif mode == "move":
                shutil.move(infoPath, infoPatht)

        if os.path.exists(prvPath) and not os.path.exists(prvPatht):
            if mode == "copy":
                shutil.copy2(prvPath, prvPatht)
            elif mode == "move":
                shutil.move(prvPath, prvPatht)

        ext = os.path.splitext(origFile)[1]
        if ext in self.appPlugin.sceneFormats:
            getattr(self.appPlugin, "copySceneFile", lambda x1, x2, x3, mode: None)(
                self, origFile, targetFile, mode=mode
            )
        else:
            for i in self.unloadedAppPlugins.values():
                if ext in i.sceneFormats:
                    getattr(i, "copySceneFile", lambda x1, x2, x3, mode: None)(
                        self, origFile, targetFile, mode=mode
                    )

    @err_catcher(name=__name__)
    def getRecentScenefiles(self, project: Optional[str] = None) -> List[str]:
        """Get list of recently opened scene files.
        
        Args:
            project (str, optional): Project name. Defaults to current project.
            
        Returns:
            List[str]: List of recent scene file paths.
        """
        project = project or self.core.projectName
        rSection = "recent_files_" + project
        recentfiles = self.core.getConfig(cat=rSection, config="user") or []

        files = []
        for recentfile in recentfiles:
            if not self.core.isStr(recentfile):
                continue

            files.append(recentfile)

        return files

    @err_catcher(name=__name__)
    def addToRecent(self, filepath: str) -> None:
        """Add scene file to recent files list.
        
        Args:
            filepath (str): Scene file path to add.
        """
        if not self.isStr(filepath):
            return

        rSection = "recent_files_" + self.projectName
        recentfiles = list(self.getConfig(rSection, dft=[]))
        if filepath in recentfiles:
            recentfiles.remove(filepath)
        recentfiles = [filepath] + recentfiles
        if len(recentfiles) > 10:
            recentfiles = recentfiles[:10]

        self.setConfig(rSection, val=recentfiles)
        if self.pb:
            self.pb.refreshRecentMenu()

    @err_catcher(name=__name__)
    def fixPath(self, path: Optional[str]) -> Optional[str]:
        """Normalize path separators for current platform.
        
        Args:
            path (str, optional): File path to normalize.
            
        Returns:
            Optional[str]: Normalized path or None.
        """
        if path is None:
            return

        if platform.system() == "Windows":
            path = path.replace("/", "\\")
        else:
            path = path.replace("\\", "/")

        return path

    @err_catcher(name=__name__)
    def countFilesInFolder(self, path: str, maximum: Optional[int] = None) -> Optional[int]:
        """Count files in folder recursively.
        
        Args:
            path (str): Folder path.
            maximum (int, optional): Stop counting at this number. Defaults to None.
            
        Returns:
            Optional[int]: File count or None if path doesn't exist.
        """
        if not os.path.exists(path):
            return

        curLength = 0
        for root, folders, files in os.walk(path):
            curLength += len(files)
            if maximum and curLength >= maximum:
                return curLength

        return curLength 

    @err_catcher(name=__name__)
    def getFileModificationDate(self, path: str, validate: bool = False, ignoreError: bool = True, asString: bool = True, asDatetime: bool = False) -> Any:
        """Get file modification date.
        
        Args:
            path (str): File path.
            validate (bool, optional): Check if file exists. Defaults to False.
            ignoreError (bool, optional): Return empty string on error. Defaults to True.
            asString (bool, optional): Return formatted string. Defaults to True.
            asDatetime (bool, optional): Return datetime object. Defaults to False.
            
        Returns:
            Any: Date as string, datetime, or timestamp.
        """
        if validate:
            if not os.path.exists(path):
                return ""

        try:
            date = os.path.getmtime(path)
        except Exception as e:
            logger.debug("failed to get modification date: %s - %s" % (path, e))
            if ignoreError:
                return ""

            raise

        if asString:
            cdate = self.getFormattedDate(date)
        elif asDatetime:
            cdate = datetime.fromtimestamp(date)
        else:
            cdate = date

        return cdate

    @err_catcher(name=__name__)
    def getFormattedDate(self, stamp: Optional[Any] = None, datetimeInst: Optional[Any] = None, dateFormat: Optional[str] = None) -> str:
        """Format timestamp or datetime as string.
        
        Args:
            stamp (Any, optional): Unix timestamp. Defaults to None.
            datetimeInst (Any, optional): Datetime instance. Defaults to None.
            dateFormat (str, optional): Format string. Defaults to None.
            
        Returns:
            str: Formatted date string.
        """
        if self.isStr(stamp):
            return ""

        if datetimeInst:
            cdate = datetimeInst
        else:
            cdate = datetime.fromtimestamp(stamp)

        cdate = cdate.replace(microsecond=0)
        fmt = dateFormat or "%d.%m.%y,  %H:%M:%S"
        if os.getenv("PRISM_DATE_FORMAT"):
            fmt = os.getenv("PRISM_DATE_FORMAT")

        cdate = cdate.strftime(fmt)
        return cdate

    @err_catcher(name=__name__)
    def getDatetimeFromFormattedDate(self, dateStr: str, dateFormat: Optional[str] = None) -> datetime:
        """Convert formatted date string to datetime object.
        
        Args:
            dateStr (str): Formatted date string.
            dateFormat (str, optional): Format string. Defaults to None.
            
        Returns:
            datetime: Datetime object.
        """
        fmt = dateFormat or "%d.%m.%y,  %H:%M:%S"
        if os.getenv("PRISM_DATE_FORMAT"):
            fmt = os.getenv("PRISM_DATE_FORMAT")

        return datetime.strptime(dateStr, fmt)

    @err_catcher(name=__name__)
    def openFolder(self, path: str) -> None:
        """Open folder in system file explorer.
        
        Args:
            path (str): Folder or file path to open.
        """
        path = self.fixPath(path)

        if platform.system() == "Windows":
            cmd = os.getenv("PRISM_FILE_EXPLORER", "explorer")
            if os.path.isfile(path):
                cmd = [cmd, "/select,", path]
            else:
                if path != "" and not os.path.exists(path):
                    path = os.path.dirname(path)

                cmd = [cmd, path]
        elif platform.system() == "Linux":
            if os.path.isfile(path):
                path = os.path.dirname(path)

            cmd = ["xdg-open", "%s" % path]
        elif platform.system() == "Darwin":
            if os.path.isfile(path):
                path = os.path.dirname(path)

            cmd = ["open", "%s" % path]

        if os.path.exists(path):
            subprocess.call(cmd)
        else:
            logger.warning("Cannot open folder. Folder doesn't exist: %s" % path)

    @err_catcher(name=__name__)
    def createFolder(self, path: str, showMessage: bool = False) -> None:
        """Create folder with optional success message.
        
        Args:
            path (str): Folder path to create.
            showMessage (bool, optional): Show popup message. Defaults to False.
        """
        path = self.fixPath(path)

        if os.path.exists(path):
            if showMessage:
                msg = "Directory already exists:\n\n%s" % path
                self.popup(msg)
            return

        if os.path.isabs(path):
            try:
                os.makedirs(path)
            except:
                pass

        if os.path.exists(path) and showMessage:
            msg = "Directory created successfully:\n\n%s" % path
            self.popup(msg, severity="info")

    @err_catcher(name=__name__)
    def replaceFolderContent(self, path: str, fromStr: str, toStr: str) -> None:
        """Replace string in all folder/filenames and file contents recursively.
        
        Args:
            path (str): Root folder path.
            fromStr (str): String to find.
            toStr (str): Replacement string.
        """
        for i in os.walk(path):
            for folder in i[1]:
                if fromStr in folder:
                    folderPath = os.path.join(i[0], folder)
                    newFolderPath = folderPath.replace(fromStr, toStr)
                    os.rename(folderPath, newFolderPath)

            for file in i[2]:
                filePath = os.path.join(i[0], file)
                with open(filePath, "r") as f:
                    content = f.read()

                with open(filePath, "w") as f:
                    f.write(content.replace(fromStr, toStr))

                if fromStr in filePath:
                    newFilePath = filePath.replace(fromStr, toStr)
                    os.rename(filePath, newFilePath)

    @err_catcher(name=__name__)
    def getCopyAction(self, path: str, parent: Optional[Any] = None, allowFile: bool = True) -> Any:
        """Create QAction for copying path or file to clipboard.
        
        Args:
            path (str): Path to copy.
            parent (Any, optional): Parent widget. Defaults to None.
            allowFile (bool, optional): Allow file content copy. Defaults to True.
            
        Returns:
            Any: QAction instance.
        """
        parent = parent or self.messageParent
        if os.getenv("PRISM_COPY_FILE_CONTENT", "0") == "1" and allowFile:
            copAct = QAction(self.tr("Copy"), parent)
            copAct.triggered.connect(lambda: self.copyToClipboard(path, file=True))
        else:
            copAct = QAction(self.tr("Copy Path"), parent)
            copAct.triggered.connect(lambda: self.copyToClipboard(path, file=False))

        iconPath = os.path.join(
            self.prismRoot, "Scripts", "UserInterfacesPrism", "copy.png"
        )
        icon = self.media.getColoredIcon(iconPath)
        copAct.setIcon(icon)
        return copAct

    @err_catcher(name=__name__)
    def copyToClipboard(self, text: Any, fixSlashes: bool = True, file: bool = False) -> None:
        """Copy text or file paths to clipboard.
        
        Args:
            text (Any): Text or path(s) to copy.
            fixSlashes (bool, optional): Normalize path separators. Defaults to True.
            file (bool, optional): Copy as file object. Defaults to False.
        """
        if fixSlashes:
            if isinstance(text, list):
                text = [self.fixPath(t) for t in text]
            else:
                text = self.fixPath(text)

        if file:
            data = QMimeData()
            urls = []
            if isinstance(text, list):
                for path in text:
                    url = QUrl.fromLocalFile(path)
                    urls.append(url)

                text = " ".join(text)

            else:
                urls = [QUrl.fromLocalFile(text)]

            data.setUrls(urls)
            data.setText(text)
            cb = QApplication.clipboard()
            cb.setMimeData(data)
        else:
            cb = QApplication.clipboard()
            cb.setText(str(text))

    @err_catcher(name=__name__)
    def getClipboard(self) -> Any:
        """Get text from system clipboard.
        
        Returns:
            Any: Clipboard text or None.
        """
        cb = QApplication.clipboard()
        try:
            rawText = cb.text("plain")[0]
        except:
            return

        return rawText

    @err_catcher(name=__name__)
    def getFolderFilecount(self, folderpath: str) -> int:
        """Count total files in folder recursively.
        
        Args:
            folderpath (str): Folder path.
            
        Returns:
            int: Total file count.
        """
        filecount = 0
        try:
            for root, folders, files in os.walk(folderpath):
                filecount += len(files)
        except (OSError, IOError):
            pass

        return filecount

    @err_catcher(name=__name__)
    def getFolderSize(self, folderpath: str) -> Dict[str, int]:
        """Calculate total size and file count in folder.
        
        Args:
            folderpath (str): Path to folder.
            
        Returns:
            Dict[str, int]: Dict with "size" (bytes) and "filecount" keys.
        """
        totalSize = 0
        filecount = 0
        for root, folders, files in os.walk(folderpath):
            for file in files:
                filePath = os.path.join(root, file)
                if not os.path.islink(filePath):
                    totalSize += os.path.getsize(filePath)
                    filecount += 1

        return {"size": totalSize, "filecount": filecount}

    @err_catcher(name=__name__)
    def copyfolder_robocopy(self, src: str, dst: str, thread: Optional[Any] = None) -> bool:
        """Copy folder using Windows robocopy for better network performance.
        
        Args:
            src (str): Source folder path.
            dst (str): Destination folder path.
            thread (Optional[Any]): Worker thread for progress updates.
            
        Returns:
            bool: True if successful.
        """
        if thread:
            thread.updated.emit({"message": "\nStarting robocopy..."})
        
        src = src.rstrip('\\')
        dst = dst.rstrip('\\')
        
        # Robocopy arguments for better network performance
        cmd = [
            'robocopy', src, dst,
            '/E',  # Copy subdirectories including empty ones
            '/COPY:DAT',  # Copy Data, Attributes, and Timestamps only
            '/R:3',  # Retry 3 times on failed copies
            '/W:5',  # Wait 5 seconds between retries
            '/MT:8',  # Multi-threaded (8 threads)
            '/V',   # Verbose output for progress tracking
        ]
        
        logger.debug("Executing robocopy command: %s" % " ".join(cmd))
        logger.debug(f"Robocopy: Copying from {src} to {dst}")
        
        try:
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,  # Combine stderr with stdout
                text=True,
                encoding='utf-8',
                errors='replace',  # Handle invalid characters gracefully
                bufsize=1,  # Line buffered
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            
            # Process output in real-time
            output_lines = []
            current_file = ""
            files_copied = 0
            total_files = self.getFolderFilecount(src) or 1
            prevPrc = -1

            while True:
                if thread and thread.canceled:
                    process.terminate()
                    return
                
                # Read output line by line
                line = process.stdout.readline()
                
                if line == '' and process.poll() is not None:
                    break
                    
                if line:
                    line = line.strip()
                    output_lines.append(line)
                    
                    # Print progress to console
                    if line:
                        logger.debug(f"Robocopy: {line}")
                    
                    # Track file copying progress
                    if line and not line.startswith('ROBOCOPY') and not line.startswith('Started') and not line.startswith('Source') and not line.startswith('Dest') and not line.startswith('Files') and not line.startswith('Options') and not line.startswith('---'):
                        # Check if this looks like a file being copied
                        if '\\' in line or '/' in line:
                            current_file = line
                            files_copied += 1
                            if thread:
                                prc = int((files_copied / total_files) * 100)
                                if prc != prevPrc:
                                    prevPrc = prc
                                    data = {"percent": prc}
                                    data["filecount"] = total_files
                                    data["idx"] = files_copied + 1
                                    thread.updated.emit(data)
            
            # Wait for process to complete
            process.wait()
            
            if process.returncode in [0, 1, 2, 3]:  # Robocopy success codes
                msg = f"Robocopy completed successfully. Return code: {process.returncode}"
                logger.debug(msg)
                logger.debug(msg)
                return dst
            else:
                output = '\n'.join(output_lines)
                msg = f"Robocopy failed with return code {process.returncode}: {output}"
                logger.warning(f"ERROR: {msg}")
                logger.warning(msg)
                raise Exception(msg)
                
        except Exception as e:
            error_msg = f"Robocopy failed: {str(e)}"
            logger.warning(f"ERROR: {error_msg}")
            if thread:
                thread.warningSent.emit(f"Robocopy failed, falling back to shutil: {str(e)}")

            return self.copyfolder(src, dst, thread, robocopy=False)

    @err_catcher(name=__name__)
    def copyfolder(self, src: str, dst: str, thread: Optional[Any] = None, robocopy: Optional[bool] = None) -> str:
        """Copy folder with optional robocopy for network transfers.
        
        Args:
            src (str): Source folder path.
            dst (str): Destination folder path.
            thread (Optional[Any]): Worker thread for progress updates.
            robocopy (Optional[bool]): Use robocopy if True. Auto-detect if None.
            
        Returns:
            str: Destination path.
        """
        if robocopy is None:
            robocopy = os.getenv("PRISM_USE_ROBOCOPY", "1") == "1"

        if platform.system() == "Windows" and robocopy is not False:
            return self.copyfolder_robocopy(src, dst, thread=thread)

        if thread:
            thread.updated.emit({"message": "\nCalculating size..."})

        folderinfo = self.getFolderSize(src)
        self.copiedFileCount = 0
        self.copiedFileBytes = 0
        shutil.copytree(src, dst, copy_function=lambda s, d: self.copyfile(s, d, thread=thread, size=folderinfo["size"], filecount=folderinfo["filecount"], robocopy=False), dirs_exist_ok=True)
        if thread and thread.canceled:
            try:
                shutil.rmtree(dst)
            except:
                pass

            return

        return dst

    def copyfile_robocopy(self, src: str, dst: str, thread: Optional[Any] = None) -> bool:
        """Copy single file using Windows robocopy.
        
        Args:
            src (str): Source file path.
            dst (str): Destination file path.
            thread (Optional[Any]): Worker thread for progress updates.
            
        Returns:
            bool: True if successful.
        """
        if thread:
            thread.updated.emit({"message": "\nStarting robocopy for file..."})

        src_dir = os.path.dirname(src)
        dst_dir = os.path.dirname(dst)
        filename = os.path.basename(src)
        dst_filename = os.path.basename(dst)
        
        # Robocopy arguments for better network performance
        cmd = [
            'robocopy', src_dir, dst_dir, filename,
            '/COPY:DAT',  # Copy Data, Attributes, and Timestamps only
            '/R:3',  # Retry 3 times on failed copies
            '/W:5',  # Wait 5 seconds between retries
            '/MT:8',  # Multi-threaded (8 threads)
            '/V',   # Verbose output for progress tracking
        ]
        
        logger.debug("Executing robocopy command for file: %s" % " ".join(cmd))
        logger.debug(f"Robocopy: Copying file from {src} to {dst}")
        
        try:
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,  # Combine stderr with stdout
                text=True,
                encoding='utf-8',
                errors='replace',  # Handle invalid characters gracefully
                bufsize=1,  # Line buffered
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            
            # Process output in real-time
            output_lines = []
            prevPrc = -1
            copy_started = False

            # Initial progress
            if thread:
                data = {"percent": 0}
                thread.updated.emit(data)

            import re
            while True:
                if thread and thread.canceled:
                    process.terminate()
                    return
                
                # Read output line by line
                line = process.stdout.readline()
                
                if line == '' and process.poll() is not None:
                    break
                    
                if line:
                    line = line.strip()
                    output_lines.append(line)
                    
                    # Print progress to console
                    if line:
                        logger.debug(f"Robocopy: {line}")
                    
                    # Parse robocopy progress from output
                    if thread:
                        prc = prevPrc
                        
                        # Look for percentage in robocopy output (e.g., "5.2%" or "100%")
                        percent_match = re.search(r'(\d+(?:\.\d+)?)%', line)
                        if percent_match:
                            try:
                                prc = int(float(percent_match.group(1)))
                                prc = min(100, max(0, prc))  # Clamp between 0-100
                            except (ValueError, IndexError):
                                pass
                        
                        # Starting copy process
                        elif not copy_started and ('Started :' in line or 'Source :' in line):
                            copy_started = True
                            if prc == prevPrc:  # Only set if no percentage found
                                prc = 5
                        
                        # File being copied
                        elif copy_started and filename in line and not line.startswith('Files :'):
                            if prc == prevPrc:  # Only set if no percentage found
                                prc = 50
                        
                        # Copy operation completing
                        elif 'Files :' in line and 'Copied :' in line:
                            if prc == prevPrc:  # Only set if no percentage found
                                prc = 95
                        
                        # Process finishing
                        elif 'Ended :' in line or process.poll() is not None:
                            prc = 100
                        
                        # Update progress if changed
                        if prc != prevPrc and prc >= 0:
                            prevPrc = prc
                            data = {"percent": prc}
                            thread.updated.emit(data)
            
            # Wait for process to complete
            process.wait()
            if process.returncode in [0, 1, 2, 3, 8, 9, 10, 11]:  # Robocopy success/partial codes (dir failures are non-critical for file copies)
                msg = f"Robocopy file copy completed successfully. Return code: {process.returncode}"
                logger.debug(msg)
                if filename != dst_filename:
                    curpath = os.path.join(dst_dir, filename)
                    newpath = os.path.join(dst_dir, dst_filename)
                    logger.debug("renaming file: %s to %s" % (curpath, newpath))
                    while True:
                        try:
                            os.rename(curpath, newpath)
                        except Exception as e:
                            result = self.popupQuestion(f"Failed to rename file: {e}", buttons=["Retry", "Skip"], escapeButton="Skip", default="Skip", icon=QMessageBox.Warning)
                            if result == "Retry":
                                continue

                        break

                return dst
            else:
                output = '\n'.join(output_lines)
                msg = f"Robocopy file copy failed with return code {process.returncode}: {output}"
                logger.warning(f"ERROR: {msg}")
                logger.warning(msg)
                raise Exception(msg)
                
        except Exception as e:
            error_msg = f"Robocopy file copy failed: {str(e)}"
            logger.warning(f"ERROR: {error_msg}")
            if thread:
                thread.warningSent.emit(f"Robocopy failed, falling back to shutil:\n\n{str(e)}")

            # Re-raise the exception to trigger fallback to shutil method
            raise

    @err_catcher(name=__name__)
    def copyfile(self, src: str, dst: str, thread: Optional[Any] = None, follow_symlinks: bool = True, size: Optional[int] = None, filecount: Optional[int] = None, robocopy: Optional[bool] = None) -> str:
        """Copy data from src to dst with progress tracking.

        If follow_symlinks is not set and src is a symbolic link, a new
        symlink will be created instead of copying the file it points to.
        
        Args:
            src (str): Source file path.
            dst (str): Destination file path.
            thread (Optional[Any]): Worker thread for progress updates.
            follow_symlinks (bool): Follow symbolic links.
            size (Optional[int]): Total size for progress calculation.
            filecount (Optional[int]): File count for progress calculation.
            robocopy (Optional[bool]): Use robocopy if True. Auto-detect if None.
            
        Returns:
            str: Destination path.
        """
        if shutil._samefile(src, dst):
            msg = "{!r} and {!r} are the same file".format(src, dst)
            if thread:
                thread.warningSent.emit(msg)
            else:
                self.core.popup(msg, severity="warning")
                
            return
        
        if not os.path.exists(src):
            msg = f"Source file does not exist: {src}"
            if thread:
                thread.warningSent.emit(msg)
            else:
                self.core.popup(msg, severity="warning")

            return

        for fn in [src, dst]:
            try:
                st = os.stat(fn)
            except OSError:
                # File most likely does not exist
                pass
            else:
                # XXX What about other special files? (sockets, devices...)
                if shutil.stat.S_ISFIFO(st.st_mode):
                    raise shutil.SpecialFileError("`%s` is a named pipe" % fn)

        if not follow_symlinks and os.path.islink(src):
            os.symlink(os.readlink(src), dst)
        else:
            with self.timeMeasure:
                if robocopy is None:
                    robocopy = os.getenv("PRISM_USE_ROBOCOPY", "1") == "1"

                if platform.system() == "Windows" and robocopy is not False:
                    try:
                        result = self.copyfile_robocopy(src, dst, thread=thread)
                        if result:
                            return result
                    except Exception as e:
                        logger.warning("Robocopy file copy failed, falling back to shutil: %s" % e)

                size = size or os.stat(src).st_size
                # thread.updated.emit("Getting source hash")
                # vSourceHash = hashlib.md5(open(src, "rb").read()).hexdigest()
                # vDestinationHash = ""
                # while vSourceHash != vDestinationHash:
                with open(src, "rb") as fsrc:
                    try:
                        with open(dst, "wb") as fdst:
                            result = self.copyfileobj(fsrc, fdst, total=size, thread=thread, path=dst, filecount=filecount)
                    except PermissionError as e:
                        msg = f"Permission denied writing to destination: {dst}\n\nPlease check that:\n- You have write permissions for this location\n- The file is not locked by another application\n- The folder is not read-only\n\nError: {str(e)}"
                        logger.error(msg)
                        if thread:
                            thread.warningSent.emit(msg)
                        else:
                            self.core.popup(msg, severity="warning")
                        raise

                if filecount is not None:
                    self.copiedFileCount += 1

                if not result:
                    return

                if thread and thread.canceled:
                    try:
                        os.remove(dst)
                    except:
                        pass

                    return

                    # thread.updated.emit("Validating copied file")
                    # vDestinationHash = hashlib.md5(open(dst, "rb").read()).hexdigest()

            while True:
                try:
                    shutil.copymode(src, dst)
                except Exception as e:
                    result = self.popupQuestion(f"Failed to copy file permissions for:\n{dst}\n\nError: {str(e)}", buttons=["Retry", "Skip"], escapeButton="Skip", icon=QMessageBox.Warning, default="Skip")
                    if result != "Retry":
                        return

                break

        return dst

    @err_catcher(name=__name__)
    def copyfileobj(self, fsrc: Any, fdst: Any, total: int, thread: Optional[Any] = None, length: int = 16 * 1024, path: str = "", filecount: Optional[int] = None) -> bool:
        """Copy file object with progress tracking.
        
        Args:
            fsrc (Any): Source file object.
            fdst (Any): Destination file object.
            total (int): Total size in bytes.
            thread (Optional[Any]): Worker thread for progress updates.
            length (int): Buffer size for chunk operations.
            path (str): File path for progress display.
            filecount (Optional[int]): File count for progress tracking.
            
        Returns:
            bool: True if successful, False if canceled.
        """
        if filecount is None:
            self.copiedFileBytes = 0

        prevPrc = -1
        while True:
            if thread and thread.canceled:
                break

            buf = fsrc.read(length)
            if not buf:
                break

            try:
                fdst.write(buf)
            except Exception as e:
                if thread:
                    msg = "Failed to copy file to:\n%s\n\nError message:%s" % (path, str(e))
                    thread.warningSent.emit(msg)

                return

            self.copiedFileBytes += len(buf)
            if thread:
                prc = int((self.copiedFileBytes / total) * 100)
                if prc != prevPrc:
                    prevPrc = prc
                    data = {"percent": prc}
                    if filecount is not None:
                        data["filecount"] = filecount
                        data["idx"] = self.copiedFileCount + 1
                        data["filename"] = os.path.basename(path)

                    thread.updated.emit(data)

        return True

    @err_catcher(name=__name__)
    def copyWithProgress(self, src: str, dst: str, follow_symlinks: bool = True, popup: bool = True, start: bool = True, finishCallback: Optional[Any] = None) -> Any:
        """Copy file or folder with progress dialog.
        
        Args:
            src (str): Source path.
            dst (str): Destination path.
            follow_symlinks (bool, optional): Follow symbolic links. Defaults to True.
            popup (bool, optional): Show progress popup. Defaults to True.
            start (bool, optional): Start copy thread immediately. Defaults to True.
            finishCallback (Any, optional): Callback on completion. Defaults to None.
            
        Returns:
            Any: Worker thread instance.
        """
        if os.path.isdir(dst):
            dst = os.path.join(dst, os.path.basename(src))

        self.copyThread = Worker(self.core)
        isdir = os.path.isdir(src)
        if isdir:
            self.copyThread.function = lambda: self.copyfolder(
                src, dst, self.copyThread
            )
        else:
            self.copyThread.function = lambda: self.copyfile(
                src, dst, self.copyThread, follow_symlinks=follow_symlinks
            )

        self.copyThread.errored.connect(self.writeErrorLog)
        self.copyThread.warningSent.connect(self.core.popup)

        if finishCallback:
            self.copyThread.finished.connect(finishCallback)

        if popup:
            baseTxt = "Copying file - please wait...    "
            self.copyThread.updated.connect(lambda x: self.updateProgressPopup(x, files=isdir))
            self.copyMsg = self.core.waitPopup(
                self.core, baseTxt
            )
            self.copyMsg.baseTxt = baseTxt

            self.copyThread.finished.connect(self.copyMsg.close)
            self.copyMsg.show()
            if self.copyMsg.msg:
                b_cnl = self.copyMsg.msg.buttons()[0]
                b_cnl.setVisible(True)
                b_cnl.clicked.connect(self.copyThread.cancel)

        if start:
            self.copyThread.start()

        return self.copyThread

    @err_catcher(name=__name__)
    def updateProgressPopup(self, progress: Dict[str, Any], popup: Optional[Any] = None, files: bool = False) -> None:
        """Update progress popup dialog with current status.
        
        Args:
            progress (Dict[str, Any]): Progress data (percent, message, filename, etc.).
            popup (Any, optional): Popup dialog widget. Defaults to None.
            files (bool, optional): Show file count progress. Defaults to False.
        """
        if not popup:
            popup = self.copyMsg

        text = getattr(popup, "baseTxt", "")
        if "percent" in progress:
            updatedText = text + str(progress["percent"]) + "%\n"
            if files:
                if "filename" in progress:
                    updatedText += "File: %s/%s %s\n" % (progress["idx"], progress["filecount"], progress["filename"])
                else:
                    updatedText += "File: %s/%s\n" % (progress["idx"], progress["filecount"])
        else:
            updatedText = text + progress["message"]

        popup.msg.setText(updatedText)

    @err_catcher(name=__name__)
    def getDefaultAppByExtension(self, ext: str) -> Optional[str]:
        """Get default application for file extension.
        
        Args:
            ext (str): File extension.
            
        Returns:
            Optional[str]: Application path or None.
        """
        if platform.system() == "Windows":
            return self.getDefaultWindowsAppByExtension(ext)

    @err_catcher(name=__name__)
    def getDefaultWindowsAppByExtension(self, ext: str) -> Optional[str]:
        """Get default Windows application for file extension.
        
        Args:
            ext (str): File extension.
            
        Returns:
            Optional[str]: Application executable path or None.
        """
        try:
            import winreg as _winreg
        except Exception as e:
            logger.warning("failed to load winreg: %s" % e)
            return

        try:
            with _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{}\UserChoice'.format(ext)) as key:
                progid = _winreg.QueryValueEx(key, 'ProgId')[0]
            with _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, r'SOFTWARE\Classes\{}\shell\open\command'.format(progid)) as key:
                path = _winreg.QueryValueEx(key, '')[0]
        except:
            try:
                class_root = _winreg.QueryValue(_winreg.HKEY_CLASSES_ROOT, ext)
                if not class_root:
                    class_root = ext
                with _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, r'{}\shell\open\command'.format(class_root)) as key:
                    path = _winreg.QueryValueEx(key, '')[0]
            except:
                path = None

        if path:
            path = os.path.expandvars(path)
            data = [d.strip() for d in path.split("\"") if d]
            path = data[0] if data else path

        return path

    @err_catcher(name=__name__)
    def getExecutableOverride(self, pluginName: str) -> Optional[str]:
        """Get overridden executable path for DCC application.
        
        Args:
            pluginName (str): Plugin/DCC name.
            
        Returns:
            Optional[str]: Executable path or None.
        """
        appPath = None
        orApp = self.core.getConfig(
            "dccoverrides", "%s_override" % pluginName
        )
        if orApp:
            appPath = self.core.getConfig(
                "dccoverrides", "%s_path" % pluginName
            )

        return appPath

    @err_catcher(name=__name__)
    def openFile(self, filepath: str) -> None:
        """Open file with appropriate application.
        
        Uses DCC plugins for scene files, default system apps for others.
        
        Args:
            filepath (str): File path to open.
        """
        filepath = filepath.replace("\\", "/")
        logger.debug("Opening file " + filepath)
        fileStarted = False
        ext = os.path.splitext(filepath)[1]
        appPath = ""

        if ext in self.appPlugin.sceneFormats:
            return self.appPlugin.openScene(self, filepath)

        appPluginName = None
        for plugin in self.core.unloadedAppPlugins.values():
            if ext in plugin.sceneFormats:
                exoverride = self.getExecutableOverride(plugin.pluginName)
                if exoverride:
                    appPath = exoverride

                fileStarted = getattr(
                    plugin, "customizeExecutable", lambda x1, x2, x3: False
                )(self, appPath, filepath)
                appPluginName = plugin.pluginName

        if not appPath and not fileStarted:
            appPath = self.getDefaultAppByExtension(ext)

        if appPath and not fileStarted:
            args = []
            if isinstance(appPath, list):
                args += appPath
            else:
                args.append(appPath)

            args[0] = os.path.expandvars(args[0])
            args.append(self.core.fixPath(filepath))
            logger.debug("starting DCC with args: %s" % args)
            dccEnv = self.startEnv.copy()
            usrEnv = self.users.getUserEnvironment(appPluginName=appPluginName)
            for envVar in usrEnv:
                dccEnv[envVar["key"]] = envVar["value"]

            prjEnv = self.projects.getProjectEnvironment(appPluginName=appPluginName)
            for envVar in prjEnv:
                dccEnv[envVar["key"]] = envVar["value"]

            self.core.callback(name="preLaunchApp", args=[args, dccEnv])
            logger.debug("launching app: args: %s - env: %s" % (args, dccEnv))
            try:
                subprocess.Popen(args, env=dccEnv)
            except:
                mods = QApplication.keyboardModifiers()
                if mods == Qt.ControlModifier:
                    if os.path.isfile(args[0]):
                        msg = "Could not execute file:\n\n%s\n\nUsed arguments: %s" % (traceback.format_exc(), args)
                    else:
                        msg = "Executable doesn't exist:\n\n%s\n\nCheck your executable override in the Prism User Settings." % args[0]
                    self.core.popup(msg)
                else:
                    subprocess.Popen(" ".join(args), env=dccEnv, shell=True)

            fileStarted = True

        if not fileStarted:
            try:
                if platform.system() == "Windows":
                    os.startfile(self.core.fixPath(filepath))
                elif platform.system() == "Linux":
                    subprocess.Popen(["xdg-open", filepath])
                elif platform.system() == "Darwin":
                    subprocess.Popen(["open", filepath])
            except:
                ext = os.path.splitext(filepath)[1]
                warnStr = (
                    'Could not open the file.\n\nPossibly there is no application connected to "%s" files on your computer.\nUse the overrides in the "DCC apps" tab of the Prism User Settings to specify an application for this filetype.'
                    % ext
                )
                self.core.popup(warnStr)

    @err_catcher(name=__name__)
    def createShortcutDeprecated(
        self, vPath: str, vTarget: str = "", args: str = "", vWorkingDir: str = "", vIcon: str = ""
    ) -> None:
        """Create Windows shortcut using win32com (deprecated).
        
        Args:
            vPath (str): Shortcut path.
            vTarget (str, optional): Target executable. Defaults to "".
            args (str, optional): Arguments. Defaults to "".
            vWorkingDir (str, optional): Working directory. Defaults to "".
            vIcon (str, optional): Icon path. Defaults to "".
        """
        try:
            import win32com.client
        except:
            self.popup("Failed to create shortcut.")
            return

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(vPath)
        vTarget = vTarget.replace("/", "\\")
        shortcut.Targetpath = vTarget
        shortcut.Arguments = args
        shortcut.WorkingDirectory = vWorkingDir
        if vIcon == "":
            pass
        else:
            shortcut.IconLocation = vIcon

        try:
            shortcut.save()
        except:
            msg = (
                "Could not create shortcut:\n\n%s\n\nProbably you don't have permissions to write to this folder. To fix this install Prism to a different location or change the permissions of this folder."
                % self.fixPath(vPath)
            )
            self.popup(msg)

    @err_catcher(name=__name__)
    def createShortcut(self, link: str, target: str, args: str = "", ignoreError: bool = False) -> bool:
        """Create Windows shortcut (.lnk file)
        
        Args:
            link (str): Shortcut file path.
            target (str): Target executable path.
            args (str, optional): Command line arguments. Defaults to "".
            ignoreError (bool, optional): Suppress error logging. Defaults to False.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        link = link.replace("/", "\\")
        target = target.replace("/", "\\")

        logger.debug(
            "creating shortcut: %s - target: %s - args: %s" % (link, target, args)
        )
        result = ""

        if platform.system() == "Windows":
            c = (
                'Set oWS = WScript.CreateObject("WScript.Shell")\n'
                'sLinkFile = "%s"\n'
                "Set oLink = oWS.CreateShortcut(sLinkFile)\n"
                'oLink.TargetPath = "%s"\n'
                'oLink.Arguments = "%s"\n'
                "oLink.Save"
            ) % (link, target, args)

            tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".vbs")
            try:
                tmp.write(c)
                tmp.close()
                cmd = "cscript /nologo %s" % tmp.name
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
                )
                result = proc.communicate()
            except Exception as e:
                result = str(e)
            finally:
                tmp.close()
                os.remove(tmp.name)

        else:
            if not ignoreError:
                logger.warning("not implemented")

        if os.path.exists(link):
            return True
        else:
            if not ignoreError:
                logger.warning("failed to create shortcut: %s %s" % (link, result))
            return False

    @err_catcher(name=__name__)
    def createSymlink(self, link: str, target: str) -> None:
        """Create hard link on Windows.
        
        Args:
            link (str): Link path.
            target (str): Target file path.
        """
        link = link.replace("/", "\\")
        target = target.replace("/", "\\")

        if os.path.exists(link):
            os.remove(link)

        if platform.system() == "Windows":
            logger.debug("creating hardlink from: %s to %s" % (target, link))
            subprocess.call(["mklink", "/H", link, target], shell=True)
        else:
            logger.warning("not implemented")

    @err_catcher(name=__name__)
    def setTrayStartupWindows(self, enabled: bool, allUsers: bool = False) -> Any:
        """Configure Prism Tray to run on Windows startup.
        
        Args:
            enabled (bool): Enable or disable startup.
            allUsers (bool, optional): Install for all users. Defaults to False.
            
        Returns:
            Any: Path to startup shortcut if enabled, False on error, None if disabled.
        """
        if allUsers:
            startMenuPath = os.path.join(
                os.environ["PROGRAMDATA"], "Microsoft", "Windows", "Start Menu", "Programs"
            )
        else:
            startMenuPath = os.path.join(
                os.environ["AppData"], "Microsoft", "Windows", "Start Menu", "Programs"
            )

        trayStartup = os.path.join(startMenuPath, "Startup", "Prism.lnk")
        if os.path.exists(trayStartup):
            try:
                os.remove(trayStartup)
                logger.debug("removed %s" % trayStartup)
            except:
                logger.debug("couldn't remove %s" % trayStartup)
                return False

        if not enabled:
            return

        if not os.path.exists(os.path.dirname(trayStartup)):
            os.makedirs(os.path.dirname(trayStartup))

        target = "%s\\%s\\Prism.exe" % (self.core.prismLibs, self.pythonVersion)
        args = '""%s\\Scripts\\PrismTray.py"" standalone' % (
            self.core.prismRoot.replace("/", "\\")
        )
        self.core.createShortcut(trayStartup, target, args=args)
        return trayStartup

    @err_catcher(name=__name__)
    def getTempFilepath(self, filename: Optional[str] = None, ext: str = ".jpg", filenamebase: Optional[str] = None) -> str:
        """Get temporary file path in Prism temp folder.
        
        Args:
            filename (str, optional): Specific filename. Defaults to None.
            ext (str, optional): File extension. Defaults to ".jpg".
            filenamebase (str, optional): Filename prefix. Defaults to None.
            
        Returns:
            str: Temporary file path.
        """
        if platform.system() == "Windows":
            base = os.environ["temp"]
        else:
            base = "/tmp"

        path = os.path.join(base, "Prism")
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

        if filename:
            if filenamebase:
                filename = filenamebase + filename

            filepath = os.path.join(path, filename)
        else:
            path += "\\"
            if filenamebase:
                path += filenamebase + "_"

            file = tempfile.NamedTemporaryFile(prefix=path, suffix=ext)
            filepath = file.name
            file.close()

        return filepath

    @property
    @err_catcher(name=__name__)
    def timeMeasure(self) -> TimeMeasure:
        """Get TimeMeasure context manager for measuring execution time.
        
        Usage:
            with self.core.timeMeasure:
                # code to measure
                
        Returns:
            TimeMeasure: Time measurement context manager.
        """
        if not hasattr(self, "_timeMeasure"):
            self._timeMeasure = TimeMeasure()

        return self._timeMeasure

    @err_catcher(name=__name__)
    def checkIllegalCharacters(self, strings: List[str]) -> List[str]:
        """Check for non-ASCII characters in strings.
        
        Args:
            strings (List[str]): List of strings to check.
            
        Returns:
            List[str]: Strings containing illegal (non-ASCII) characters.
        """
        illegalStrs = []
        for i in strings:
            if not all(ord(c) < 128 for c in i):
                illegalStrs.append(i)

        return illegalStrs

    @err_catcher(name=__name__)
    def atoi(self, text: str) -> Any:
        """Convert string to int if numeric, otherwise return string.
        
        Args:
            text (str): Text to convert.
            
        Returns:
            Any: Integer or original string.
        """
        return int(text) if text.isdigit() else text

    @err_catcher(name=__name__)
    def naturalKeys(self, text: str) -> List[Any]:
        """Generate natural sort key by splitting numeric parts.
        
        Args:
            text (str): Text to create key from.
            
        Returns:
            List[Any]: List of strings and integers for natural sorting.
        """
        return [self.atoi(c) for c in re.split(r"(\d+)", text)]

    @err_catcher(name=__name__)
    def sortNatural(self, alist: List[Any]) -> List[Any]:
        """Sort list using natural (human-friendly) ordering.
        
        Args:
            alist (List[Any]): List to sort.
            
        Returns:
            List[Any]: Naturally sorted list.
        """
        sortedList = sorted(alist, key=self.naturalKeys)
        return sortedList

    @err_catcher(name=__name__)
    def scenefileSaved(self, arg: Any = None) -> None:
        """Callback when scene file is saved.
        
        Args:
            arg (Any, optional): Callback argument. Defaults to None.
        """
        if getattr(self, "sm", None):
            self.sm.scenename = self.getCurrentFileName()
            self.sm.saveStatesToScene()

        if self.shouldAutosaveTimerRun():
            self.startAutosaveTimer()

        self.updateEnvironment()
        if self.getLockScenefilesEnabled():
            self.startSceneLockTimer()

        self.callback(name="sceneSaved")

    @err_catcher(name=__name__)
    def sceneUnload(self, arg: Any = None) -> None:
        """Callback when scene is unloaded/closed.
        
        Args:
            arg (Any, optional): Callback argument. Defaults to None.
        """
        if getattr(self, "sm", None):
            self.openSm = self.sm.isVisible()
            self.sm.close()
            del self.sm

        if self.getLockScenefilesEnabled():
            self.unlockScenefile()

        if self.shouldAutosaveTimerRun():
            self.startAutosaveTimer()

    @err_catcher(name=__name__)
    def sceneOpen(self, arg: Any = None) -> None:
        """Callback when scene file is opened.
        
        Args:
            arg (Any, optional): Callback argument. Defaults to None.
        """
        if not self.sceneOpenChecksEnabled:
            return

        openSm = getattr(self, "openSm", None) or (getattr(self, "sm", None) and self.sm.isVisible())
        getattr(self.appPlugin, "sceneOpen", lambda x: None)(self)

        filepath = self.getCurrentFileName()
        if self.getLockScenefilesEnabled():
            self.lockScenefile(filepath)

        # trigger auto imports
        if os.path.exists(self.prismIni):
            sm = self.stateManager(openUi=openSm, reload_module=True)
            if sm and not sm.states:
                sm.loadDefaultStates(quiet=True)

        self.openSm = False
        self.sanities.runChecks("onSceneOpen")
        self.updateEnvironment()
        self.core.callback(name="onSceneOpen", args=[filepath])

    @err_catcher(name=__name__)
    def onExit(self) -> None:
        """Cleanup when application exits."""
        self.unlockScenefile()

    @err_catcher(name=__name__)
    def unlockScenefile(self) -> None:
        """Release lock on current scene file."""
        if getattr(self, "sceneLockfile", None) and self.sceneLockfile.isLocked():
            self.sceneLockfile.release()

    @err_catcher(name=__name__)
    def lockScenefile(self, filepath: Optional[str] = None) -> None:
        """Lock scene file to prevent concurrent edits.
        
        Args:
            filepath (str, optional): File to lock. Uses current file if None. Defaults to None.
        """
        self.unlockScenefile()
        if not filepath:
            filepath = self.getCurrentFileName()

        if os.path.isfile(filepath):
            from PrismUtils import Lockfile
            import json
            self.sceneLockfile = Lockfile.Lockfile(self.core, filepath)
            try:
                self.sceneLockfile.acquire(content=json.dumps({"username": self.username}), force=True)
            except Exception as e:
                logger.warning("failed to acquire lockfile (%s): %s" % (filepath, e))

        self.startSceneLockTimer()

    @err_catcher(name=__name__)
    def shouldScenelockTimerRun(self) -> bool:
        """Check if scene lock timer should be running.
        
        Returns:
            bool: True if timer should run.
        """
        if not self.getLockScenefilesEnabled():
            return False

        qapp = QApplication.instance()
        isGuiThread = qapp and qapp.thread() == QThread.currentThread()
        if "silent" in self.prismArgs or not self.uiAvailable or not isGuiThread:
            return

        return True

    @err_catcher(name=__name__)
    def isScenelockTimerActive(self) -> bool:
        """Check if scene lock refresh timer is running.
        
        Returns:
            bool: True if timer active, False otherwise.
        """
        active = hasattr(self, "scenelockTimer") and self.scenelockTimer.isActive()
        return active

    @err_catcher(name=__name__)
    def startSceneLockTimer(self, quit: bool = False) -> None:
        """Start timer to periodically refresh scene file lock.
        
        Args:
            quit (bool, optional): Stop timer instead of starting. Defaults to False.
        """
        if self.isScenelockTimerActive():
            self.scenelockTimer.stop()

        if quit:
            return

        if not self.shouldScenelockTimerRun():
            return

        lockMins = 5
        self.scenelockTimer = QTimer()
        self.scenelockTimer.timeout.connect(self.lockScenefile)
        self.scenelockTimer.setSingleShot(True)
        self.scenelockTimer.start(lockMins * 60 * 1000)

        logger.debug("started scenelock timer: %smin" % lockMins)

    @err_catcher(name=__name__)
    def getLockScenefilesEnabled(self) -> Any:
        """Check if scene file locking is enabled in project.
        
        Returns:
            Any: Locking configuration value.
        """
        return self.getConfig("globals", "scenefileLocking", config="project")

    @err_catcher(name=__name__)
    def updateEnvironment(self) -> None:
        """Update Prism environment variables based on current scene.
        
        Sets PRISM_SEQUENCE, PRISM_SHOT, PRISM_ASSET, etc. from scene metadata.
        """
        envvars = {
            "PRISM_SEQUENCE": "",
            "PRISM_SHOT": "",
            "PRISM_ASSET": "",
            "PRISM_ASSETPATH": "",
            "PRISM_DEPARTMENT": "",
            "PRISM_TASK": "",
            "PRISM_USER": "",
            "PRISM_FILE_VERSION": "",
        }
        useEpisodes = self.core.getConfig(
            "globals",
            "useEpisodes",
            config="project",
        ) or False
        if useEpisodes:
            envvars["PRISM_EPISODE"] = ""
        elif "PRISM_EPISODE" in os.environ:
            del os.environ["PRISM_EPISODE"]

        for envvar in envvars:
            envvars[envvar] = os.getenv(envvar)

        newenv = {}

        fn = self.getCurrentFileName()
        data = self.getScenefileData(fn)
        if data.get("type") == "asset":
            if useEpisodes:
                newenv["PRISM_EPISODE"] = ""

            newenv["PRISM_SEQUENCE"] = ""
            newenv["PRISM_SHOT"] = ""
            newenv["PRISM_ASSET"] = os.path.basename(data.get("asset_path", ""))
            newenv["PRISM_ASSETPATH"] = data.get("asset_path", "").replace("\\", "/")
        elif data.get("type") == "shot":
            newenv["PRISM_ASSET"] = ""
            newenv["PRISM_ASSETPATH"] = ""
            if useEpisodes:
                newenv["PRISM_EPISODE"] = data.get("episode", "")

            newenv["PRISM_SEQUENCE"] = data.get("sequence", "")
            newenv["PRISM_SHOT"] = data.get("shot", "")
        else:
            if useEpisodes:
                newenv["PRISM_EPISODE"] = ""

            newenv["PRISM_SEQUENCE"] = ""
            newenv["PRISM_SHOT"] = ""
            newenv["PRISM_ASSET"] = ""
            newenv["PRISM_ASSETPATH"] = ""

        if data.get("type"):
            newenv["PRISM_DEPARTMENT"] = data.get("department", "")
            newenv["PRISM_TASK"] = data.get("task", "")
            newenv["PRISM_USER"] = getattr(self, "user", "")
            newenv["PRISM_FILE_VERSION"] = data.get("version", "")
        else:
            newenv["PRISM_DEPARTMENT"] = ""
            newenv["PRISM_TASK"] = ""
            newenv["PRISM_USER"] = ""
            newenv["PRISM_FILE_VERSION"] = ""

        for var in newenv:
            if newenv[var] != envvars[var]:
                os.environ[var] = str(newenv[var])

        self.updateProjectEnvironment()

    @err_catcher(name=__name__)
    def updateProjectEnvironment(self) -> None:
        """Update PRISM_JOB and PRISM_JOB_LOCAL environment variables."""
        job = getattr(self, "projectPath", "").replace("\\", "/")
        if job.endswith("/"):
            job = job[:-1]
        os.environ["PRISM_JOB"] = job

        if self.useLocalFiles:
            ljob = self.localProjectPath.replace("\\", "/")
            if ljob.endswith("/"):
                ljob = ljob[:-1]
        else:
            ljob = ""

        os.environ["PRISM_JOB_LOCAL"] = ljob

    @err_catcher(name=__name__)
    def setTrayStartup(self, enabled: bool) -> bool:
        """Enable/disable Prism Tray autostart (cross-platform).
        
        Args:
            enabled (bool): Enable or disable autostart.
            
        Returns:
            bool: True on success, False on failure.
        """
        if platform.system() == "Windows":
            self.setTrayStartupWindows(enabled)

        elif platform.system() == "Linux":
            trayStartup = "/etc/xdg/autostart/PrismTray.desktop"
            trayLnk = self.core.fixPath(
                os.path.join(self.core.prismLibs, "Tools", "PrismTray.desktop")
            )

            if os.path.exists(trayStartup):
                try:
                    os.remove(trayStartup)
                except:
                    msg = "Failed to remove autostart file: %s" % trayStartup
                    self.popup(msg)
                    return False

            if enabled:
                if os.path.exists(trayLnk):
                    try:
                        shutil.copy2(trayLnk, trayStartup)
                        os.chmod(trayStartup, 0o777)
                    except Exception as e:
                        self.core.popup("Failed to copy autostart file: %s" % e)
                        return False
                else:
                    msg = (
                        "Cannot add Prism to the autostart because this file doesn't exist:\n\n%s"
                        % (trayLnk)
                    )
                    self.popup(msg)
                    return False

        elif platform.system() == "Darwin":
            userName = (
                os.environ["SUDO_USER"]
                if "SUDO_USER" in os.environ
                else os.environ["USER"]
            )
            trayStartup = (
                "/Users/%s/Library/LaunchAgents/com.user.PrismTray.plist" % userName
            )
            trayLnk = self.core.fixPath(
                os.path.join(self.core.prismLibs, "Tools", "com.user.PrismTray.plist")
            )

            if os.path.exists(trayStartup):
                os.remove(trayStartup)

            if enabled:
                if os.path.exists(trayLnk):
                    shutil.copy2(trayLnk, trayStartup)
                    os.chmod(trayStartup, 0o644)
                    import pwd

                    uid = pwd.getpwnam(userName).pw_uid
                    os.chown(os.path.dirname(trayStartup), uid, -1)
                    os.chown(trayStartup, uid, -1)
                    os.system(
                        "launchctl load /Users/%s/Library/LaunchAgents/com.user.PrismTray.plist"
                        % userName
                    )
                else:
                    msg = (
                        "Cannot add Prism to the autostart because this file doesn't exist:\n\n%s"
                        % (trayLnk)
                    )
                    self.popup(msg)
                    return False

        return True

    @err_catcher(name=__name__)
    def getFrameRange(self) -> Tuple[int, int]:
        """Get current scene frame range.
        
        Returns:
            Tuple[int, int]: Start and end frame numbers.
        """
        return self.appPlugin.getFrameRange(self)

    @err_catcher(name=__name__)
    def setFrameRange(self, startFrame: int, endFrame: int) -> None:
        """Set scene frame range.
        
        Args:
            startFrame (int): Start frame number.
            endFrame (int): End frame number.
        """
        self.appPlugin.setFrameRange(self, startFrame, endFrame)

    @err_catcher(name=__name__)
    def getFPS(self) -> Optional[float]:
        """Get scene frames per second (FPS).
        
        Returns:
            Optional[float]: FPS value or None.
        """
        fps = getattr(self.appPlugin, "getFPS", lambda x: None)(self)
        if fps is not None:
            fps = float(fps)

        return fps

    @err_catcher(name=__name__)
    def getResolution(self) -> Optional[Tuple[int, int]]:
        """Get current scene resolution.
        
        Returns:
            Optional[Tuple[int, int]]: Width and height in pixels, or None.
        """
        if hasattr(self.appPlugin, "getResolution"):
            return self.appPlugin.getResolution()

    @err_catcher(name=__name__)
    def getCompositingOut(self, *args: Any, **kwargs: Any) -> Any:
        """Get compositing output path.
        
        Args:
            *args: Variable positional arguments.
            **kwargs: Variable keyword arguments.
            
        Returns:
            Any: Compositing output path.
        """
        return self.paths.getCompositingOut(*args, **kwargs)

    @err_catcher(name=__name__)
    def registerStyleSheet(self, path: str, default: bool = False) -> Optional[Dict[str, Any]]:
        """Register custom UI stylesheet.
        
        Args:
            path (str): Path to stylesheet directory or JSON file.
            default (bool, optional): Set as default stylesheet. Defaults to False.
            
        Returns:
            Optional[Dict[str, Any]]: Stylesheet data dict or None on error.
        """
        if os.path.basename(path) != "stylesheet.json":
            path = os.path.join(path, "stylesheet.json")

        if not os.path.exists(path):
            self.core.popup("Invalid stylesheet path: %s" % path)
            return

        data = self.getConfig(configPath=path)
        data["path"] = os.path.dirname(path)
        data["default"] = default
        self.registeredStyleSheets = [ssheet for ssheet in self.registeredStyleSheets if ssheet["name"] != data["name"]]
        self.registeredStyleSheets.append(data)
        return data

    @err_catcher(name=__name__)
    def getRegisteredStyleSheets(self) -> List[Dict[str, Any]]:
        """Get list of registered stylesheets.
        
        Returns:
            List[Dict[str, Any]]: List of stylesheet data dicts.
        """
        return self.registeredStyleSheets

    @err_catcher(name=__name__)
    def getActiveStyleSheet(self) -> Optional[Dict[str, Any]]:
        """Get currently active stylesheet.
        
        Returns:
            Optional[Dict[str, Any]]: Active stylesheet data or None.
        """
        return self.activeStyleSheet

    @err_catcher(name=__name__)
    def setActiveStyleSheet(self, name: str) -> Optional[Dict[str, Any]]:
        """Set active stylesheet by name.
        
        Args:
            name (str): Stylesheet name.
            
        Returns:
            Optional[Dict[str, Any]]: Stylesheet data or None on error.
        """
        sheet = self.getStyleSheet(name)
        if not sheet:
            return

        self.activeStyleSheet = sheet
        qapp = QApplication.instance()
        if not qapp:
            logger.debug("Invalid qapp. Cannot set stylesheet.")
            return

        qapp.setStyleSheet(sheet["css"])
        return sheet

    @err_catcher(name=__name__)
    def getStyleSheet(self, name: str) -> Optional[Dict[str, Any]]:
        """Load stylesheet by name.
        
        Args:
            name (str): Stylesheet name.
            
        Returns:
            Optional[Dict[str, Any]]: Stylesheet data with CSS, or None.
        """
        sheets = self.getRegisteredStyleSheets()
        for sheet in sheets:
            if sheet.get("name") == name:
                modPath = os.path.dirname(sheet["path"])
                if modPath not in sys.path:
                    sys.path.append(modPath)

                mod = importlib.import_module(sheet.get("module_name", ""))
                if self.debugMode:
                    importlib.reload(mod)

                sheetData = mod.load_stylesheet()
                sheet["css"] = sheetData
                return sheet

    @err_catcher(name=__name__)
    def getPythonPath(self, executable: Optional[str] = None, root: Optional[str] = None) -> str:
        """Get path to Python executable.
        
        Args:
            executable (str, optional): Specific executable name (e.g., "python", "pythonw"). Defaults to None.
            root (str, optional): Root directory to search. Defaults to None.
            
        Returns:
            str: Path to Python executable.
        """
        if platform.system() == "Windows":
            root = root or self.prismLibs
            if executable:
                pythonPath = os.path.join(
                    root, self.pythonVersion, "%s.exe" % executable
                )
                if os.path.exists(pythonPath):
                    return pythonPath
                else:
                    pythonPath = os.path.join(root, "*", "%s.exe" % executable)
                    paths = glob.glob(pythonPath)
                    if paths:
                        return paths[0]

            pythonPath = os.path.join(root, self.pythonVersion, "pythonw.exe")
            if not os.path.exists(pythonPath):
                pythonPath = os.path.join(root, "Python313", "pythonw.exe")
                if not os.path.exists(pythonPath):
                    pythonPath = os.path.join(root, "*", "pythonw.exe")
                    paths = glob.glob(pythonPath)
                    if paths:
                        return paths[0]

                    pythonPath = os.path.join(
                        os.path.dirname(sys.executable), "pythonw.exe"
                    )
                    if not os.path.exists(pythonPath):
                        pythonPath = sys.executable
                        if "ython" not in os.path.basename(pythonPath):
                            pythonPath = "python"

        elif platform.system() == "Linux":
            pythonPath = os.path.dirname(os.path.dirname(__file__)) + "/Python313/bin/python"
        else:
            pythonPath = os.path.dirname(os.path.dirname(__file__)) + "/Python313/bin/python"

        if pythonPath.startswith("//"):
            pythonPath = "\\\\" + pythonPath[2:]

        return pythonPath

    @err_catcher(name=__name__)
    def handleRemoveReadonly(self, func: Any, path: str, exc: Tuple[Any, ...]) -> None:
        """Error handler for removing read-only files.
        
        Args:
            func (Any): Function that raised the error.
            path (str): File path.
            exc (Tuple[Any, ...]): Exception info tuple.
            
        Raises:
            Exception: If error is not permission-related.
        """
        excvalue = exc[1]
        if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
            os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
            func(path)
        else:
            raise

    @err_catcher(name=__name__)
    def ffmpegError(self, title: str, text: str, result: Any) -> None:
        """Display ffmpeg error dialog with optional output.
        
        Args:
            title (str): Dialog title.
            text (str): Error message.
            result (Any): FFMPEG output tuple.
        """
        buttons = ["Ok"]
        if result:
            buttons.append("Show ffmpeg output")
        action = self.popupQuestion(
            text, title=title, buttons=buttons, icon=QMessageBox.Warning
        )

        if result and action == "Show ffmpeg output":
            warnDlg = QDialog()

            warnDlg.setWindowTitle("FFMPEG output")
            warnString = "%s\n%s" % (result[0], result[1])
            l_warnings = QLabel(warnString)
            l_warnings.setAlignment(Qt.AlignTop)

            sa_warns = QScrollArea()
            lay_warns = QHBoxLayout()
            lay_warns.addWidget(l_warnings)
            lay_warns.setContentsMargins(10, 10, 10, 10)
            lay_warns.addStretch()
            w_warns = QWidget()
            w_warns.setLayout(lay_warns)
            sa_warns.setWidget(w_warns)
            sa_warns.setWidgetResizable(True)

            bb_warn = QDialogButtonBox()
            bb_warn.addButton("OK", QDialogButtonBox.AcceptRole)
            bb_warn.accepted.connect(warnDlg.accept)

            bLayout = QVBoxLayout()
            bLayout.addWidget(sa_warns)
            bLayout.addWidget(bb_warn)
            warnDlg.setLayout(bLayout)
            warnDlg.setParent(self.messageParent, Qt.Window)
            warnDlg.resize(1000 * self.uiScaleFactor, 500 * self.uiScaleFactor)

            warnDlg.exec_()

    @err_catcher(name=__name__)
    def isPopupTooLong(self, text: str) -> bool:
        """Check if popup message exceeds line limit.
        
        Args:
            text (str): Message text.
            
        Returns:
            bool: True if more than 50 lines.
        """
        rows = text.split("\n")
        tooLong = len(rows) > 50
        return tooLong

    @err_catcher(name=__name__)
    def shortenPopupMsg(self, text: str) -> str:
        """Truncate popup message to 50 lines.
        
        Args:
            text (str): Message text.
            
        Returns:
            str: Shortened message with ellipsis.
        """
        rows = text.split("\n")
        rows = rows[:50]
        shortText = "\n".join(rows)
        shortText += "\n..."
        return shortText

    @err_catcher(name=__name__)
    def popup(
        self,
        text: str,
        title: Optional[str] = None,
        severity: str = "warning",
        notShowAgain: bool = False,
        parent: Optional[Any] = None,
        modal: bool = True,
        widget: Optional[Any] = None,
        show: bool = True,
    ) -> Any:
        """Display popup message dialog.
        
        Args:
            text (str): Message text.
            title (str, optional): Dialog title. Defaults to None.
            severity (str, optional): "warning", "info", or "error". Defaults to "warning".
            notShowAgain (bool, optional): Show "don't show again" checkbox. Defaults to False.
            parent (Any, optional): Parent widget. Defaults to None.
            modal (bool, optional): Modal dialog. Defaults to True.
            widget (Any, optional): Additional widget to embed. Defaults to None.
            show (bool, optional): Show dialog immediately. Defaults to True.
            
        Returns:
            Any: QMessageBox or dict with notShowAgain status.
        """
        if title is None:
            if severity == "warning":
                title = "Prism - Warning"
            elif severity == "info":
                title = "Prism - Information"
            elif severity == "error":
                title = "Prism - Error"

        if not isinstance(text, str):
            text = str(text)
        if not isinstance(title, str):
            title = str(title)

        qapp = QApplication.instance()
        isGuiThread = qapp and qapp.thread() == QThread.currentThread()

        if "silent" not in self.prismArgs and self.uiAvailable and isGuiThread:
            parent = parent or getattr(self, "messageParent", None)
            msg = QMessageBox(parent)
            if "<a href=" in text or "<br>" in text:
                msg.setTextFormat(Qt.RichText)
            else:
                text = text.replace("\n", "  \n")
                if API_NAME not in ["PySide2", "PyQt5"]:
                    msg.setTextFormat(Qt.TextFormat.MarkdownText)

            if self.isPopupTooLong(text):
                text = self.shortenPopupMsg(text)
            msg.setText(text)
            msg.setWindowTitle(title)
            msg.setModal(modal)

            if severity == "warning":
                msg.setIcon(QMessageBox.Icon.Warning)
            elif severity == "info":
                msg.setIcon(QMessageBox.Icon.Information)
            else:
                msg.setIcon(QMessageBox.Icon.Critical)
            msg.addButton(QMessageBox.Ok)
            if notShowAgain:
                msg.chb = QCheckBox("Don't show again")
                msg.setCheckBox(msg.chb)
                msg.setText(text + "\n")

            if widget:
                msg.layout().addWidget(widget, 1, 2)

            if show:
                msg.setAttribute(Qt.WA_ShowWithoutActivating)
                if modal:
                    msg.exec_()
                else:
                    msg.show()

            if notShowAgain:
                return {"notShowAgain": msg.chb.isChecked()}

            return msg
        else:
            msg = "%s - %s" % (title, text)
            if severity == "warning":
                logger.warning(msg)
            elif severity == "info":
                logger.info(msg)
            else:
                logger.error(msg)

    @err_catcher(name=__name__)
    def popupQuestion(
        self,
        text: str,
        title: Optional[str] = None,
        buttons: Optional[List[str]] = None,
        default: Optional[str] = None,
        icon: Optional[Any] = None,
        widget: Optional[Any] = None,
        parent: Optional[Any] = None,
        escapeButton: Optional[str] = None,
        doExec: bool = True,
    ) -> Any:
        """Display question dialog with custom buttons.
        
        Args:
            text (str): Question text.
            title (str, optional): Dialog title. Defaults to None.
            buttons (List[str], optional): Button labels. Defaults to None.
            default (str, optional): Default button. Defaults to None.
            icon (Any, optional): QMessageBox icon. Defaults to None.
            widget (Any, optional): Additional widget. Defaults to None.
            parent (Any, optional): Parent widget. Defaults to None.
            escapeButton (str, optional): Escape button label. Defaults to None.
            doExec (bool, optional): Execute modally. Defaults to True.
            
        Returns:
            Any: Clicked button text or QMessageBox if not executed.
        """
        text = str(text)
        title = str(title or "Prism")
        buttons = buttons or ["Yes", "No"]
        icon = QMessageBox.Question if icon is None else icon
        parent = parent or getattr(self, "messageParent", None)
        isGuiThread = QApplication.instance() and QApplication.instance().thread() == QThread.currentThread()

        if "silent" in self.prismArgs or not self.uiAvailable or not isGuiThread:
            logger.info("%s - %s - %s" % (title, text, default))
            return default

        msg = QMessageBox(
            icon,
            title,
            text,
            parent=parent,
        )
        for button in buttons:
            if button in ["Close", "Cancel", "Ignore"]:
                role = QMessageBox.RejectRole
            else:
                role = QMessageBox.YesRole
            b = msg.addButton(button, role)
            if default == button:
                msg.setDefaultButton(b)

            if escapeButton == button:
                msg.setEscapeButton(b)

        self.parentWindow(msg, parent=parent)
        if widget:
            msg.layout().addWidget(widget, 1, 2)

        if doExec:
            msg.exec_()
            button = msg.clickedButton()
            if button:
                result = button.text()
            else:
                result = None

            return result
        else:
            msg.setModal(False)
            return msg

    @err_catcher(name=__name__)
    def popupNoButton(
        self,
        text: str,
        title: Optional[str] = None,
        buttons: Optional[List[str]] = None,
        default: Optional[str] = None,
        icon: Optional[Any] = None,
        parent: Optional[Any] = None,
        show: bool = True,
    ) -> Any:
        """Display non-modal message with hidden buttons.
        
        Args:
            text (str): Message text.
            title (str, optional): Dialog title. Defaults to None.
            buttons (List[str], optional): Unused. Defaults to None.
            default (str, optional): Default value. Defaults to None.
            icon (Any, optional): Unused. Defaults to None.
            parent (Any, optional): Parent widget. Defaults to None.
            show (bool, optional): Show dialog immediately. Defaults to True.
            
        Returns:
            Any: QMessageBox instance.
        """
        text = str(text)
        title = str(title or "Prism")

        if "silent" in self.prismArgs or not self.uiAvailable:
            logger.info("%s - %s" % (title, text))
            return default

        msg = QMessageBox(
            QMessageBox.NoIcon,
            title,
            text,
            QMessageBox.Cancel,
        )

        if parent:
            msg.setParent(parent, Qt.Window)
        else:
            self.core.parentWindow(msg)

        for i in msg.buttons():
            i.setVisible(False)

        msg.setModal(False)
        if show:
            msg.show()
            QCoreApplication.processEvents()

        return msg

    class waitPopup(QObject):
        """Context manager for displaying wait/progress popup dialogs.
        
        Usage:
            with self.core.waitPopup(self.core, "Processing..."):
                # long running operation
        """

        canceled = Signal()

        def __init__(
            self,
            core: Any,
            text: str,
            title: Optional[str] = None,
            buttons: Optional[List[str]] = None,
            default: Optional[str] = None,
            icon: Optional[Any] = None,
            hidden: bool = False,
            parent: Optional[Any] = None,
            allowCancel: bool = False,
            activate: bool = True,
        ) -> None:
            """Initialize wait popup.
            
            Args:
                core (Any): PrismCore instance.
                text (str): Message text to display.
                title (Optional[str]): Dialog title.
                buttons (Optional[List[str]]): List of button labels.
                default (Optional[str]): Default button.
                icon (Optional[Any]): Icon to display.
                hidden (bool): If True, don't show popup.
                parent (Optional[Any]): Parent widget.
                allowCancel (bool): Allow user to cancel operation.
                activate (bool): Whether to activate window when shown.
            """
            self.core = core
            super(self.core.waitPopup, self).__init__()
            self.parent = parent
            self.text = text
            self.title = title
            self.buttons = buttons
            self.default = default
            self.icon = icon
            self.hidden = hidden
            self.allowCancel = allowCancel
            self.activate = activate
            self.msg = None
            self.isCanceled = False

        def __enter__(self) -> 'waitPopup':
            """Enter context manager and show popup.
            
            Returns:
                waitPopup: Self.
            """
            if not self.hidden:
                self.show()

            return self

        def __exit__(self, type: Any, value: Any, traceback: Any) -> None:
            """Exit context manager and close popup.
            
            Args:
                type (Any): Exception type.
                value (Any): Exception value.
                traceback (Any): Traceback object.
            """
            self.close()

        def createPopup(self) -> None:
            """Create the popup dialog widget."""
            self.msg = self.core.popupNoButton(
                self.text,
                title=self.title,
                buttons=self.buttons,
                default=self.default,
                icon=self.icon,
                parent=self.parent,
                show=False,
            )
            if not self.msg:
                return

            if not self.activate:
                self.msg.setAttribute(Qt.WA_ShowWithoutActivating)

            if self.allowCancel:
                self.msg.rejected.connect(self.cancel)

        def show(self) -> None:
            """Show the popup dialog."""
            if not self.msg:
                self.createPopup()

            qapp = QApplication.instance()
            isGuiThread = qapp and qapp.thread() == QThread.currentThread()
            if self.core.uiAvailable and isGuiThread:
                for button in self.msg.buttons():
                    button.setVisible(self.allowCancel)

                self.msg.show()
                QCoreApplication.processEvents()
                QCoreApplication.processEvents()

        def exec_(self) -> None:
            """Execute popup dialog modally."""
            if not self.msg:
                self.createPopup()
                if not self.msg:
                    return

            for button in self.msg.buttons():
                button.setVisible(self.allowCancel)

            result = self.msg.exec_()
            if result:
                self.cancel()

        def isVisible(self) -> bool:
            """Check if popup is visible.
            
            Returns:
                bool: True if visible.
            """
            if not self.msg:
                return False

            return self.msg.isVisible()

        def close(self) -> None:
            """Close the popup dialog."""
            if self.msg and self.msg.isVisible():
                self.msg.close()

        def cancel(self) -> None:
            """Cancel the operation and emit canceled signal."""
            self.isCanceled = True
            self.canceled.emit()

    def writeErrorLog(self, text: str, data: Optional[Any] = None) -> None:
        """Write error to log files and display error popup.
        
        Args:
            text (str): Error message text.
            data (Any, optional): Additional error data. Defaults to None.
            
        Raises:
            RuntimeError: If error occurs in non-UI mode.
        """
        try:
            logger.debug(text)
            raiseError = False
            text += "\n\n"

            if hasattr(self, "messageParent") and self.uiAvailable:
                self.showErrorPopup(text=text, data=data)
            else:
                logger.warning(text)
                raiseError = True

            if getattr(self, "prismIni", None) and getattr(self, "user", None):
                prjErDir = os.getenv("PRISM_PROJECT_ERROR_LOGS") or os.path.dirname(self.prismIni)
                if prjErDir != "0":
                    prjErPath = os.path.join(prjErDir, "ErrorLog_%s.txt" % self.user)
                    try:
                        open(prjErPath, "a").close()
                    except:
                        pass

                    if os.path.exists(prjErPath):
                        with open(prjErPath, "a") as erLog:
                            erLog.write(text)

            if getattr(self, "userini", None):
                userErDir = os.getenv("PRISM_USER_ERROR_LOGS") or os.path.dirname(self.userini)
                if userErDir != "0":
                    userErPath = os.path.join(userErDir, "ErrorLog_%s.txt" % socket.gethostname())

                    try:
                        open(userErPath, "a").close()
                    except:
                        pass

                    if platform.system() in ["Linux", "Darwin"]:
                        if os.path.exists(userErPath):
                            try:
                                os.chmod(userErPath, 0o777)
                            except:
                                pass

                    if os.path.exists(userErPath):
                        with open(userErPath, "a") as erLog:
                            erLog.write(text)

                self.lastErrorTime = time.time()

            for arg in self.core.prismArgs:
                if isinstance(arg, dict) and "errorCallback" in arg:
                    arg["errorCallback"](text)
                    break

        except:
            msg = "ERROR - writeErrorLog - %s\n\n%s" % (traceback.format_exc(), text)
            logger.warning(msg)

        if raiseError:
            raise RuntimeError(text)

    def showErrorPopup(self, text: str, data: Optional[Any] = None) -> None:
        """Display error popup with details option.
        
        Args:
            text (str): Error message.
            data (Any, optional): Additional error data. Defaults to None.
        """
        try:
            ptext = """An unknown Prism error occured."""

            if self.catchTypeErrors:
                lastLine = [x for x in text.split("\n") if x and x != "\n"][-1]
                if lastLine.startswith("TypeError"):
                    ptext = """An unknown Prism error occured in this plugin:

%s

This error happened while calling this function:

%s

If this plugin was created by yourself, please make sure you update your plugin to support the currently installed Prism version.
If this plugin is an official Prism plugin, please submit this error to the support.
""" % (
                        self.callbacks.currentCallback["plugin"],
                        self.callbacks.currentCallback["function"],
                    )

            result = self.core.popupQuestion(
                ptext, buttons=["Details", "Close"], icon=QMessageBox.Warning
            )
            if result == "Details":
                self.showErrorDetailPopup(text, data=data)
            elif result == "Close":
                if self.getConfig("globals", "send_error_reports", dft=True):
                    self.sendAutomaticErrorReport(text, data=data)

            if "UnicodeDecodeError" in text or "UnicodeEncodeError" in text:
                msg = "The previous error might be caused by the use of special characters (like ö or é). Prism doesn't support this at the moment. Make sure you remove these characters from your filepaths.".decode(
                    "utf8"
                )
                self.popup(msg)
        except:
            msg = "ERROR - writeErrorLog - %s\n\n%s" % (traceback.format_exc(), text)
            logger.warning(msg)

    def showErrorDetailPopup(self, text: str, sendReport: bool = True, data: Optional[Any] = None) -> None:
        """Display detailed error dialog.
        
        Args:
            text (str): Error message.
            sendReport (bool, optional): Allow sending error report. Defaults to True.
            data (Any, optional): Additional error data. Defaults to None.
        """
        qapp = QApplication.instance()
        isGuiThread = qapp and qapp.thread() == QThread.currentThread()
        if "silent" in self.prismArgs or not self.uiAvailable or not isGuiThread:
            return

        dlg_error = ErrorDetailsDialog(self, text)
        dlg_error.exec_()
        button = dlg_error.clickedButton
        if button:
            result = button.text()
        else:
            result = None

        if result == "Report with note":
            self.sendError(text)
        elif sendReport and self.getConfig("globals", "send_error_reports", dft=True):
            self.sendAutomaticErrorReport(text, data=data)

    def sendAutomaticErrorReport(self, text: str, data: Optional[Any] = None) -> None:
        """Send automatic error report if not already reported.
        
        Args:
            text (str): Error text.
            data (Optional[Any]): Additional error data.
        """
        if getattr(self, "userini", None):
            userErPath = os.path.join(
                os.path.dirname(self.userini),
                "ErrorLog_%s.txt" % socket.gethostname(),
            )

            if os.path.exists(userErPath):
                with open(userErPath, "r", errors="ignore") as erLog:
                    content = erLog.read()

                errStr = "\n".join(text.split("\n")[1:])
                try:
                    if errStr in content:
                        logger.debug("error already reported")
                        return
                except Exception as e:
                    logger.warnung("failed to check if error happened before: %s" % str(e))

        logger.debug("sending automatic error report")
        self.reportHandler("automatic error report.\n\n" + text, quiet=True, data=data, reportType="error - automatic")

    def sendError(self, errorText: str) -> None:
        """Display dialog for sending error report with user notes.
        
        Args:
            errorText (str): Technical error message.
        """
        msg = QDialog()

        dtext = "The technical error description will be sent anonymously, but you can add additional information to this message if you like.\nFor example how to reproduce the problem or your e-mail for further discussions and to get notified when the problem is fixed.\n"
        ptext = "Additional information (optional):"

        msg.setWindowTitle("Send Error")
        l_description = QLabel(dtext)
        l_info = QLabel(ptext)
        msg.te_info = QPlainTextEdit(
            """Your email:\n\n\nWhat happened:\n\n\nHow to reproduce:\n\n\nOther notes:\n\n"""
        )
        msg.te_info.setMinimumHeight(300 * self.uiScaleFactor)

        b_send = QPushButton("Report anonymously")
        b_ok = QPushButton("Close")

        w_versions = QWidget()
        lay_versions = QHBoxLayout()
        lay_versions.addStretch()
        lay_versions.addWidget(b_send)
        lay_versions.addWidget(b_ok)
        lay_versions.setContentsMargins(0, 10, 10, 10)
        w_versions.setLayout(lay_versions)

        bLayout = QVBoxLayout()
        bLayout.addWidget(l_description)
        bLayout.addWidget(l_info)
        bLayout.addWidget(msg.te_info)
        bLayout.addWidget(w_versions)
        msg.setLayout(bLayout)
        msg.setParent(self.messageParent, Qt.Window)
        msg.setFocus()
        msg.resize(800, 470)

        b_send.clicked.connect(lambda: self.sendErrorReport(msg, errorText))
        b_send.clicked.connect(msg.accept)
        b_ok.clicked.connect(msg.accept)

        msg.l_screenGrab = QLabel()
        msg.lo_screenGrab = QHBoxLayout()
        msg.lo_screenGrab.setContentsMargins(0, 0, 0, 0)
        msg.b_addScreenGrab = QPushButton("Attach Screengrab")
        msg.b_removeScreenGrab = QPushButton("Remove Screengrab")
        msg.lo_screenGrab.addWidget(msg.b_addScreenGrab)
        msg.lo_screenGrab.addWidget(msg.b_removeScreenGrab)
        msg.lo_screenGrab.addStretch()
        msg.sp_main = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Fixed)

        msg.layout().insertWidget(msg.layout().count() - 1, msg.l_screenGrab)
        msg.layout().insertLayout(msg.layout().count() - 1, msg.lo_screenGrab)
        msg.layout().insertItem(msg.layout().count() - 1, msg.sp_main)

        size = QSize(msg.size().width(), msg.size().height() * 0.5)
        msg.b_addScreenGrab.clicked.connect(lambda: self.attachScreenGrab(msg, size))
        msg.b_removeScreenGrab.clicked.connect(lambda: self.removeScreenGrab(msg))
        msg.b_removeScreenGrab.setVisible(False)
        msg.origSize = msg.size()

        msg.exec_()

    def sendErrorReport(self, dlg: Any, errorMessage: str) -> None:
        """Send error report with user notes and optional screenshot.
        
        Args:
            dlg (Any): Error dialog widget.
            errorMessage (str): Error message text.
        """
        message = "%s\n\n\n%s" % (dlg.te_info.toPlainText(), errorMessage)
        pm = getattr(dlg, "screenGrab", None)
        if pm:
            attachment = tempfile.NamedTemporaryFile(suffix=".jpg").name
            self.media.savePixmap(pm, attachment)
        else:
            attachment = None

        self.reportHandler(message, attachment=attachment, reportType="error")
        try:
            os.remove(attachment)
        except Exception:
            pass

    @err_catcher(name=__name__)
    def copyFolder(self, source: str, destination: str, adminFallback: bool = True) -> bool:
        """Copy folder recursively with admin fallback.
        
        Args:
            source (str): Source folder path.
            destination (str): Destination folder path.
            adminFallback (bool, optional): Try admin if fails. Defaults to True.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            if sys.version_info.minor >= 8:
                shutil.copytree(source, destination, dirs_exist_ok=True)
            else:
                shutil.copytree(source, destination)

            return True
        except Exception:
            if adminFallback and platform.system() == "Windows":
                return self.copyFolderAsAdmin(source, destination)

        return False

    @err_catcher(name=__name__)
    def copyFile(self, source: str, destination: str, adminFallback: bool = True) -> bool:
        """Copy file with admin fallback.
        
        Args:
            source (str): Source file path.
            destination (str): Destination file path.
            adminFallback (bool, optional): Try admin if fails. Defaults to True.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            shutil.copy2(source, destination)
            return True
        except Exception:
            if adminFallback and platform.system() == "Windows":
                return self.copyFileAsAdmin(source, destination)

        return False

    @err_catcher(name=__name__)
    def removeFolder(self, path: str, adminFallback: bool = True) -> bool:
        """Remove folder recursively with admin fallback.
        
        Args:
            path (str): Folder path to remove.
            adminFallback (bool, optional): Try admin if fails. Defaults to True.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            shutil.rmtree(path)
            return True
        except Exception:
            if adminFallback and platform.system() == "Windows":
                return self.removeFolderAsAdmin(path)

        return False

    @err_catcher(name=__name__)
    def removeFile(self, path: str, adminFallback: bool = True) -> bool:
        """Remove file with admin fallback.
        
        Args:
            path (str): File path to remove.
            adminFallback (bool, optional): Try admin if fails. Defaults to True.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            os.remove(path)
            return True
        except Exception:
            if adminFallback and platform.system() == "Windows":
                return self.removeFileAsAdmin(path)

        return False

    @err_catcher(name=__name__)
    def writeToFile(self, path: str, text: str, adminFallback: bool = True) -> bool:
        """Write text to file with admin fallback.
        
        Args:
            path (str): File path.
            text (str): Text content to write.
            adminFallback (bool, optional): Try admin if fails. Defaults to True.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            with open(path, "w") as f:
                f.write(text)
            return True
        except Exception:
            if adminFallback and platform.system() == "Windows":
                return self.writeToFileAsAdmin(path, text)

        return False

    @err_catcher(name=__name__)
    def createDirectory(self, path: str, adminFallback: bool = True) -> bool:
        """Create directory with admin fallback.
        
        Args:
            path (str): Directory path to create.
            adminFallback (bool, optional): Try admin if fails. Defaults to True.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            os.makedirs(path)
            return True
        except Exception:
            if adminFallback and platform.system() == "Windows":
                return self.createFolderAsAdmin(path)

        return False

    @err_catcher(name=__name__)
    def getCopyFolderCmd(self, source: str, destination: str) -> str:
        """Generate Python command to copy folder.
        
        Args:
            source (str): Source folder path.
            destination (str): Destination folder path.
            
        Returns:
            str: Python command string.
        """
        source = source.replace("\\", "/")
        destination = destination.replace("\\", "/")
        cmd = "import shutil;shutil.copytree('%s', '%s')" % (source, destination)
        return cmd

    @err_catcher(name=__name__)
    def getCopyFileCmd(self, source: str, destination: str) -> str:
        """Generate Python command to copy file.
        
        Args:
            source (str): Source file path.
            destination (str): Destination file path.
            
        Returns:
            str: Python command string.
        """
        source = source.replace("\\", "/")
        destination = destination.replace("\\", "/")
        cmd = "import shutil;shutil.copy2('%s', '%s')" % (source, destination)
        return cmd

    @err_catcher(name=__name__)
    def copyFolderAsAdmin(self, source: str, destination: str) -> bool:
        """Copy folder with admin privileges on Windows.
        
        Args:
            source (str): Source folder path.
            destination (str): Destination folder path.
            
        Returns:
            bool: True if successful.
        """
        cmd = self.getCopyFolderCmd(source, destination)
        self.winRunAsAdmin(cmd)
        result = self.validateCopyFolder(source, destination)
        return result

    @err_catcher(name=__name__)
    def copyFileAsAdmin(self, source: str, destination: str) -> bool:
        """Copy file with admin privileges on Windows.
        
        Args:
            source (str): Source file path.
            destination (str): Destination file path.
            
        Returns:
            bool: True if successful.
        """
        cmd = self.getCopyFileCmd(source, destination)
        self.winRunAsAdmin(cmd)
        result = self.validateCopyFile(source, destination)
        return result

    @err_catcher(name=__name__)
    def validateCopyFolder(self, source: str, destination: str) -> bool:
        """Validate folder copy operation.
        
        Args:
            source (str): Source folder path.
            destination (str): Destination folder path.
            
        Returns:
            bool: True if destination exists.
        """
        result = os.path.exists(destination)
        return result

    @err_catcher(name=__name__)
    def validateCopyFile(self, source: str, destination: str) -> bool:
        """Validate file copy operation.
        
        Args:
            source (str): Source file path.
            destination (str): Destination file path.
            
        Returns:
            bool: True if destination exists.
        """
        result = os.path.exists(destination)
        return result

    @err_catcher(name=__name__)
    def getRemoveFolderCmd(self, path: str) -> str:
        """Generate Python command to remove folder.
        
        Args:
            path (str): Folder path to remove.
            
        Returns:
            str: Python command string.
        """
        cmd = "import shutil;shutil.rmtree('%s')" % path.replace("\\", "/")
        return cmd

    @err_catcher(name=__name__)
    def getRemoveFileCmd(self, path: str) -> str:
        """Generate Python command to remove file.
        
        Args:
            path (str): File path to remove.
            
        Returns:
            str: Python command string.
        """
        cmd = "import os;os.remove('%s')" % path.replace("\\", "/")
        return cmd

    @err_catcher(name=__name__)
    def removeFolderAsAdmin(self, path: str) -> bool:
        """Remove folder with admin privileges on Windows.
        
        Args:
            path (str): Folder path to remove.
            
        Returns:
            bool: True if successful.
        """
        cmd = self.getRemoveFolderCmd(path)
        self.winRunAsAdmin(cmd)
        result = self.validateRemoveFolder(path)
        return result

    @err_catcher(name=__name__)
    def removeFileAsAdmin(self, path: str) -> bool:
        """Remove file with admin privileges on Windows.
        
        Args:
            path (str): File path to remove.
            
        Returns:
            bool: True if successful.
        """
        cmd = self.getRemoveFileCmd(path)
        self.winRunAsAdmin(cmd)
        result = self.validateRemoveFile(path)
        return result

    @err_catcher(name=__name__)
    def validateRemoveFolder(self, path: str) -> bool:
        """Validate folder removal.
        
        Args:
            path (str): Folder path.
            
        Returns:
            bool: True if folder no longer exists.
        """
        result = not os.path.exists(path)
        return result

    @err_catcher(name=__name__)
    def validateRemoveFile(self, path: str) -> bool:
        """Validate file removal.
        
        Args:
            path (str): File path.
            
        Returns:
            bool: True if file no longer exists.
        """
        result = not os.path.exists(path)
        return result

    @err_catcher(name=__name__)
    def getWriteToFileCmd(self, path: str, text: str) -> str:
        """Generate command to write text to file via temp file.
        
        Args:
            path (str): Target file path.
            text (str): Text content.
            
        Returns:
            str: Python command string.
        """
        tempPath = tempfile.NamedTemporaryFile().name
        self.writeToFile(tempPath, text, adminFallback=False)
        cmd = self.getCopyFileCmd(tempPath, path)
        return cmd

    @err_catcher(name=__name__)
    def writeToFileAsAdmin(self, path: str, text: str) -> bool:
        """Write to file with admin privileges on Windows.
        
        Args:
            path (str): File path.
            text (str): Text content to write.
            
        Returns:
            bool: True if successful.
        """
        tempPath = tempfile.NamedTemporaryFile().name
        self.writeToFile(tempPath, text, adminFallback=False)
        result = self.copyFileAsAdmin(tempPath, path)
        os.remove(tempPath)
        return result

    @err_catcher(name=__name__)
    def validateWriteToFile(self, path: str, text: str) -> bool:
        """Validate file write operation.
        
        Args:
            path (str): File path.
            text (str): Expected text content.
            
        Returns:
            bool: True if file content matches expected text.
        """
        with open(path, "r") as f:
            data = f.read()

        result = data == text
        return result

    @err_catcher(name=__name__)
    def getCreateFolderCmd(self, path: str) -> str:
        """Generate Python command to create folder.
        
        Args:
            path (str): Folder path to create.
            
        Returns:
            str: Python command string.
        """
        cmd = "import os;os.makedirs('%s')" % path.replace("\\", "/")
        return cmd

    @err_catcher(name=__name__)
    def createFolderAsAdmin(self, path: str) -> bool:
        """Create folder with admin privileges on Windows.
        
        Args:
            path (str): Folder path to create.
            
        Returns:
            bool: True if successful.
        """
        cmd = self.getCreateFolderCmd(path)
        self.winRunAsAdmin(cmd)
        result = self.validateCreateFolder(path)
        return result

    @err_catcher(name=__name__)
    def validateCreateFolder(self, path: str) -> bool:
        """Validate folder creation.
        
        Args:
            path (str): Folder path.
            
        Returns:
            bool: True if folder exists.
        """
        result = os.path.exists(path)
        return result

    @err_catcher(name=__name__)
    def winRunAsAdmin(self, script: str) -> Any:
        """Execute Python script with admin privileges on Windows.
        
        Args:
            script (str): Python script to execute.
            
        Returns:
            Any: True on success, "canceled" if user cancels UAC prompt.
        """
        if platform.system() != "Windows":
            return

        # cmd = 'Start-Process "%s" -ArgumentList @("-c", "`"%s`"") -Verb RunAs -Wait' % (sys.executable, script)
        # logger.debug("powershell command: %s" % cmd)
        # prog = subprocess.Popen(['Powershell', "-ExecutionPolicy", "Bypass", '-command', cmd])
        # prog.communicate()

        from win32comext.shell import shellcon
        import win32comext.shell.shell as shell
        import win32con
        import win32event

        executable = self.getPythonPath()
        params = '-c "%s"' % script
        logger.debug("run as admin: %s" % params)
        try:
            procInfo = shell.ShellExecuteEx(
                nShow=win32con.SW_SHOWNORMAL,
                fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                lpVerb="runas",
                lpFile=executable,
                lpParameters=params,
            )
        except Exception as e:
            if "The operation was canceled by the user." in str(e):
                return "canceled"

            raise
        else:
            procHandle = procInfo["hProcess"]
            win32event.WaitForSingleObject(procHandle, win32event.INFINITE)
            return True

    @err_catcher(name=__name__)
    def runFileCommands(self, commands: List[Dict[str, Any]]) -> Any:
        """Execute multiple file commands with admin fallback.
        
        Args:
            commands (List[Dict[str, Any]]): List of command dicts with "type" and "args".
            
        Returns:
            Any: True on success, error message or False on failure.
        """
        for command in commands:
            result = self.runFileCommand(command)
            if result is not True:
                break
        else:
            return True

        cmd = ""
        for command in commands:
            cmd += self.getFileCommandStr(command) + ";"

        result = self.core.winRunAsAdmin(cmd)
        if result == "canceled":
            return False

        for command in commands:
            if not command.get("validate", True):
                continue

            result = self.validateFileCommand(command)
            if not result:
                msg = "failed to run command: %s, args: %s" % (
                    command["type"],
                    command["args"],
                )
                return msg
        else:
            return True

    @err_catcher(name=__name__)
    def runFileCommand(self, command: Dict[str, Any]) -> bool:
        """Execute single file command.
        
        Args:
            command (Dict[str, Any]): Command dict with "type" and "args" keys.
            
        Returns:
            bool: True if successful.
        """
        logger.debug("run file command: %s" % command)
        if command["type"] == "copyFolder":
            result = self.core.copyFolder(*command["args"], adminFallback=False)
        elif command["type"] == "copyFile":
            result = self.core.copyFile(*command["args"], adminFallback=False)
        elif command["type"] == "removeFolder":
            result = self.core.removeFolder(*command["args"], adminFallback=False)
        elif command["type"] == "removeFile":
            result = self.core.removeFile(*command["args"], adminFallback=False)
        elif command["type"] == "writeToFile":
            result = self.core.writeToFile(*command["args"], adminFallback=False)
        elif command["type"] == "createFolder":
            result = self.core.createDirectory(*command["args"], adminFallback=False)

        return result

    @err_catcher(name=__name__)
    def getFileCommandStr(self, command: Dict[str, Any]) -> str:
        """Convert file command to Python command string.
        
        Args:
            command (Dict[str, Any]): Command dict with "type" and "args" keys.
            
        Returns:
            str: Python command string.
        """
        if command["type"] == "copyFolder":
            result = self.core.getCopyFolderCmd(*command["args"])
        elif command["type"] == "copyFile":
            result = self.core.getCopyFileCmd(*command["args"])
        elif command["type"] == "removeFolder":
            result = self.core.getRemoveFolderCmd(*command["args"])
        elif command["type"] == "removeFile":
            result = self.core.getRemoveFileCmd(*command["args"])
        elif command["type"] == "writeToFile":
            result = self.core.getWriteToFileCmd(*command["args"])
        elif command["type"] == "createFolder":
            result = self.core.getCreateFolderCmd(*command["args"])

        return result

    @err_catcher(name=__name__)
    def validateFileCommand(self, command: Dict[str, Any]) -> bool:
        """Validate file command execution.
        
        Args:
            command (Dict[str, Any]): Command dict with "type" and "args" keys.
            
        Returns:
            bool: True if command succeeded.
        """
        if command["type"] == "copyFolder":
            result = self.core.validateCopyFolder(*command["args"])
        elif command["type"] == "copyFile":
            result = self.core.validateCopyFile(*command["args"])
        elif command["type"] == "removeFolder":
            result = self.core.validateRemoveFolder(*command["args"])
        elif command["type"] == "removeFile":
            result = self.core.validateRemoveFile(*command["args"])
        elif command["type"] == "writeToFile":
            result = self.core.validateWriteToFile(*command["args"])
        elif command["type"] == "createFolder":
            result = self.core.validateCreateFolder(*command["args"])

        return result

    @err_catcher(name=__name__)
    def startCommunication(self, port: int, key: bytes, callback: Optional[Any] = None) -> None:
        """Start inter-process communication server and client.
        
        Args:
            port (int): Port number for the server.
            key (bytes): Authentication key for connection.
            callback (Optional[Any]): Optional callback function for handling received data.
        """
        listener = self.startServer(port, key)
        if listener:
            conn = self.startClient(port+1, key)
            if conn:
                self.runServer(listener, conn, callback=callback)
            else:
                listener.close()

    @err_catcher(name=__name__)
    def startServer(self, port: int, key: bytes) -> Any:
        """Start server listener for inter-process communication.
        
        Args:
            port (int): Port number to listen on.
            key (bytes): Authentication key for connection.
            
        Returns:
            Any: Listener object or None on failure.
        """
        logger.debug("starting server (%s)" % port)
        address = ("localhost", port)

        try:
            listener = Listener(address, authkey=key)
        except OSError as e:
            logger.warning("failed to start server on port %s: %s" % (port, e))
            return None

        return listener

    @err_catcher(name=__name__)
    def startClient(self, port: int, key: bytes) -> Any:
        """Start client connection for inter-process communication.
        
        Args:
            port (int): Port number to connect to.
            key (bytes): Authentication key for connection.
            
        Returns:
            Any: Connection object or None on failure.
        """
        logger.debug("starting client (%s)" % port)
        address = ("localhost", port)
        retries = 3
        delay = 0.2
        for attempt in range(retries):
            try:
                conn = Client(address, authkey=key)
                return conn
            except (ConnectionRefusedError, OSError) as e:
                # The peer can still be starting up, so retry briefly before giving up.
                if attempt == retries - 1:
                    logger.warning("failed to start client (%s): %s" % (port, e))
                    return

                time.sleep(delay)

    @err_catcher(name=__name__)
    def runServer(self, listener: Any, conn: Any, callback: Optional[Any] = None) -> None:
        """Run server to handle incoming commands.
        
        Accepts connections and processes commands like getUserPrefDir, getDefaultPluginPath,
        sendFeedback, removeAllIntegrations, and isAlive.
        
        Args:
            listener (Any): Server listener object.
            conn (Any): Client connection object.
            callback (Optional[Any]): Optional callback function for handling received data.
        """
        logger.debug("server and client running")
        sconn = listener.accept()
        logger.debug("connection accepted from " + str(listener.last_accepted))

        while True:
            try:
                data = sconn.recv()
            except Exception:
                logger.debug("connecting to Prism failed")
                break

            logger.debug("command received: " + str(data))

            if callback:
                callback(data=data, conn=conn, sconn=sconn)
            else:
                if not isinstance(data, dict):
                    data = "unknown command: %s" % data
                    answer = {"success": False, "error": data}
                    self.sendData(answer, conn)
                    continue

                name = data.get("name", "")

                if name == "close":
                    sconn.close()
                    break

                elif name == "getUserPrefDir":
                    returnData = {"success": True, "data": self.getUserPrefDir()}
                    self.sendData(returnData, conn)

                elif name == "getDefaultPluginPath":
                    returnData = {"success": True, "data": self.plugins.getDefaultPluginPath()}
                    self.sendData(returnData, conn)

                elif name == "sendFeedback":
                    result = self.sendFeedback(data["data"])
                    returnData = {"success": True, "data": result}
                    self.sendData(returnData, conn)

                elif name == "removeAllIntegrations":
                    result = self.integration.removeAllIntegrations()
                    returnData = {"success": True, "data": result}
                    self.sendData(returnData, conn)

                elif name == "isAlive":
                    answer = {"success": True, "data": True}
                    self.sendData(answer, conn)

                else:
                    data = "unknown command: %s" % data
                    answer = {"success": False, "error": data}
                    self.sendData(answer, conn)

        listener.close()

    @err_catcher(name=__name__)
    def sendData(self, data: Any, conn: Any) -> None:
        """Send data to client connection.
        
        Args:
            data (Any): Data to send.
            conn (Any): Connection object.
        """
        logger.debug("sending data: %s" % data)

        if data is None:
            data = ""

        conn.send(data)

    @err_catcher(name=__name__)
    def registerProtocolHandler(self, name: str, func: Any) -> None:
        """Register a protocol handler function.
        
        Args:
            name (str): Protocol name.
            func (Any): Handler function to call for this protocol.
        """
        self.protocolHandlers[name] = func

    @err_catcher(name=__name__)
    def registerPrismProtocolHandler(self) -> bool:
        """Register Prism protocol handler in Windows registry.
        
        Registers prism:// URL protocol handler to enable launching Prism from URLs.
        
        Returns:
            bool: True if successful.
        """
        try:
            import winreg
        except Exception as e:
            logger.warning("failed to load winreg: %s" % e)
            return

        key_path = "Software\\Classes\\prism"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as k:
            winreg.SetValueEx(k, None, 0, winreg.REG_SZ, "URL:Prism Protocol")
            winreg.SetValueEx(k, "URL Protocol", 0, winreg.REG_SZ, "")

            iconPath = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "UserInterfacesPrism",
                "p_tray.png",
            )
            with winreg.CreateKey(k, "DefaultIcon") as ik:
                winreg.SetValueEx(ik, None, 0, winreg.REG_SZ, iconPath)

            pythonExe = os.path.normpath(self.getPythonPath())
            scriptPath = os.path.abspath(__file__)
            cmd = '"%s" "%s" "%%1"' % (pythonExe.replace("\\", "\\\\"), scriptPath.replace("\\", "\\\\"))
            with winreg.CreateKey(k, "shell\\open\\command") as ck:
                winreg.SetValueEx(ck, None, 0, winreg.REG_SZ, cmd)

        return True

    @err_catcher(name=__name__)
    def protocolHandler(self, url: Optional[str] = None) -> None:
        """Handle prism:// protocol URLs.
        
        Parses and routes prism:// URLs to registered protocol handlers.
        
        Args:
            url (Optional[str]): URL to handle. Defaults to sys.argv[1] if not provided.
        """
        try:
            import urllib.parse
            raw = url or sys.argv[1]
            url = raw.strip('"\'')
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)

            if parsed.netloc in self.protocolHandlers:
                logger.debug("handling url: %s" % raw)
                path = parsed.path
                qs = urllib.parse.parse_qs(parsed.query)
                self.protocolHandlers[parsed.netloc](path=path, qs=qs)

            else:
                logger.warning("No handler available for:", parsed.netloc)
        except Exception as e:
            print(e)


class TimeMeasure(object):
    """Context manager for measuring execution time.
    
    Usage:
        with TimeMeasure():
            # code to measure
    """
    
    def __enter__(self) -> 'TimeMeasure':
        """Start time measurement.
        
        Returns:
            TimeMeasure: Self.
        """
        self.startTime = datetime.now()
        logger.info("starttime: %s" % self.startTime.strftime("%Y-%m-%d %H:%M:%S"))
        return self

    def __exit__(self, type: Any, value: Any, traceback: Any) -> None:
        """End time measurement and log duration.
        
        Args:
            type (Any): Exception type.
            value (Any): Exception value.
            traceback (Any): Traceback object.
        """
        endTime = datetime.now()
        logger.info("endtime: %s" % endTime.strftime("%Y-%m-%d %H:%M:%S"))
        logger.info("duration: %s" % (endTime - self.startTime))


class PythonConsole(QDialog):
    """Interactive Python console dialog.
    
    Provides a GUI interface for executing Python commands with syntax highlighting
    and command history.
    """
    
    def __init__(self, core: Any, local_ns: Optional[Dict[str, Any]], parent: Optional[Any] = None) -> None:
        """Initialize Python console.
        
        Args:
            core (Any): PrismCore instance.
            local_ns (Optional[Dict[str, Any]]): Local namespace for console execution.
            parent (Optional[Any]): Parent widget.
        """
        super(PythonConsole, self).__init__()
        self.setWindowTitle("Python Console")
        layout = QVBoxLayout(self)
        self.core = core
        self.core.parentWindow(self, parent=parent)
 
        self.output = QPlainTextEdit(self)
        self.output.setReadOnly(True)
        self.output.setStyleSheet("background: #111; color: rgb(255, 255, 255); font-family: monospace;")
        layout.addWidget(self.output)

        self.input = QLineEdit(self)
        self.input.returnPressed.connect(self.execute_input)
        self.input.installEventFilter(self)
        layout.addWidget(self.input)

        self.console = code.InteractiveConsole(locals=local_ns or {})
        self.command_buffer = []
        self.history = []
        self.history_index = -1
        self.write("Welcome to the Prism Python Console.\nAccess the PrismCore instance using the \"pcore\" variable.")

    def sizeHint(self) -> QSize:
        """Return preferred size for console window.
        
        Returns:
            QSize: Preferred size of 600x300 pixels.
        """
        return QSize(600, 300)

    def write(self, text: str) -> None:
        """Write text to console output.
        
        Args:
            text (str): Text to display.
        """
        self.output.appendPlainText(text)

    def execute_input(self) -> None:
        """Execute command from input field.
        
        Captures stdout/stderr, executes command in interactive console,
        and displays output.
        """
        command = self.input.text()
        self.output.appendPlainText(f">>> {command}")
        self.command_buffer.append(command)
        self.history.append(command)
        self.history_index = len(self.history)

        self.input.clear()

        # Redirect stdout/stderr
        stdout_backup = sys.stdout
        stderr_backup = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        try:
            more = self.console.push(command)
            stdout_output = sys.stdout.getvalue()
            stderr_output = sys.stderr.getvalue()

            if stdout_output:
                self.output.appendPlainText(stdout_output.rstrip())
            if stderr_output:
                self.output.appendPlainText(stderr_output.rstrip())

            if more:
                self.output.appendPlainText("...")  # Multiline placeholder
        except Exception:
            self.output.appendPlainText(traceback.format_exc())
        finally:
            sys.stdout = stdout_backup
            sys.stderr = stderr_backup

        self.output.verticalScrollBar().setValue(
            self.output.verticalScrollBar().maximum()
        )

    def eventFilter(self, obj: Any, event: Any) -> bool:
        """Filter keyboard events for command history navigation.
        
        Args:
            obj (Any): Object that generated the event.
            event (Any): Event object.
            
        Returns:
            bool: True if event was handled.
        """
        if obj is self.input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Up:
                if self.history and self.history_index > 0:
                    self.history_index -= 1
                    self.input.setText(self.history[self.history_index])
                return True
            elif event.key() == Qt.Key_Down:
                if self.history and self.history_index < len(self.history) - 1:
                    self.history_index += 1
                    self.input.setText(self.history[self.history_index])
                else:
                    self.history_index = len(self.history)
                    self.input.clear()
                return True
        return super().eventFilter(obj, event)


class Worker(QThread):
    """Worker thread for executing functions in background.
    
    Signals:
        warningSent: Emitted when warning occurs.
        errored: Emitted when error occurs.
        updated: Emitted on progress update.
        dataSent: Emitted when data is sent.
    """
    
    warningSent = Signal(object)
    errored = Signal(object)
    updated = Signal(object)
    dataSent = Signal(object)

    def __init__(self, core: Optional[Any] = None, function: Optional[Any] = None) -> None:
        """Initialize worker thread.
        
        Args:
            core (Optional[Any]): PrismCore instance.
            function (Optional[Any]): Function to execute in thread.
        """
        super(Worker, self).__init__()
        if core:
            self.core = core

        self.function = function
        self.canceled = False

    def run(self) -> None:
        """Execute the worker function.
        
        Emits errored signal if exception occurs.
        """
        try:
            self.function()
        except Exception as e:
            self.errored.emit(str(e))

    def cancel(self) -> None:
        """Cancel the worker execution."""
        self.canceled = True


class ErrorDetailsDialog(QDialog):
    """Dialog for displaying detailed error information.
    
    Provides copy-to-clipboard and error reporting functionality.
    """
    
    def __init__(self, core: Any, text: str) -> None:
        """Initialize error details dialog.
        
        Args:
            core (Any): PrismCore instance.
            text (str): Error details text to display.
        """
        super(ErrorDetailsDialog, self).__init__()
        self.core = core
        self.core.parentWindow(self)
        self.text = text
        self.clickedButton = None
        self.setupUi()

    def sizeHint(self) -> QSize:
        """Return preferred size for error dialog.
        
        Returns:
            QSize: Preferred size of 1000x500 pixels.
        """
        return QSize(1000, 500)

    def showEvent(self, event: Any) -> None:
        """Handle dialog show event.
        
        Scrolls to bottom of error message.
        
        Args:
            event (Any): Show event.
        """
        super(ErrorDetailsDialog, self).showEvent(event)
        self.l_message.verticalScrollBar().setValue(self.l_message.verticalScrollBar().maximum())

    def setupUi(self) -> None:
        """Set up the user interface for error details dialog."""
        self.setWindowTitle("Error Details")
        self.lo_main = QVBoxLayout(self)
        self.l_header = QLabel("Error details:")
        self.l_message = QTextEdit()
        self.l_message.setReadOnly(True)
        self.l_message.setWordWrapMode(QTextOption.NoWrap)
        self.l_message.setPlainText(self.text)

        self.w_copy = QWidget()
        self.lo_copy = QHBoxLayout(self.w_copy)
        self.lo_copy.setContentsMargins(0, 0, 0, 0)
        self.b_copy = QToolButton()
        self.lo_copy.addStretch()
        self.lo_copy.addWidget(self.b_copy)
        self.b_copy.setToolTip("Copy details to clipboard")
        self.b_copy.setFocusPolicy(Qt.NoFocus)
        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "copy.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_copy.setIcon(icon)
        self.b_copy.clicked.connect(lambda: self.core.copyToClipboard(self.text, fixSlashes=False))

        self.bb_main = QDialogButtonBox()
        b_report = self.bb_main.addButton("Report with note", QDialogButtonBox.AcceptRole)
        b_close = self.bb_main.addButton("Close", QDialogButtonBox.RejectRole)
        b_report.clicked.connect(lambda: setattr(self, "clickedButton", b_report))
        b_close.clicked.connect(lambda: setattr(self, "clickedButton", b_close))
        self.bb_main.accepted.connect(self.accept)
        self.bb_main.rejected.connect(self.reject)

        self.lo_main.addWidget(self.l_header)
        self.lo_main.addWidget(self.l_message)
        self.lo_main.addWidget(self.w_copy)
        self.lo_main.addWidget(self.bb_main)


class PythonHighlighter (QSyntaxHighlighter):
    """Syntax highlighter for the Python language.
    """
    # Python keywords
    keywords = [
        'and', 'assert', 'break', 'class', 'continue', 'def',
        'del', 'elif', 'else', 'except', 'exec', 'finally',
        'for', 'from', 'global', 'if', 'import', 'in',
        'is', 'lambda', 'not', 'or', 'pass', 'print',
        'raise', 'return', 'try', 'while', 'yield',
        'None', 'True', 'False',
    ]

    # Python operators
    operators = [
        '=',
        # Comparison
        '==', '!=', '<', '<=', '>', '>=',
        # Arithmetic
        r'\+', '-', r'\*', '/', '//', r'\%', r'\*\*',
        # In-place
        r'\+=', '-=', r'\*=', '/=', r'\%=',
        # Bitwise
        r'\^', r'\|', r'\&', r'\~', '>>', '<<',
    ]

    # Python braces
    braces = [
        r'\{', r'\}', r'\(', r'\)', r'\[', r'\]',
    ]

    def __init__(self, parent: QTextDocument) -> None:
        """Initialize Python syntax highlighter.
        
        Args:
            parent: QTextDocument to apply syntax highlighting to
        """
        super().__init__(parent)
        self.setup()

    @err_catcher(name=__name__)
    def setup(self) -> None:
        """Initialize syntax highlighting rules and styles."""
        # Syntax styles that can be shared by all languages
        self.STYLES = {
            'keyword': (self.formatColor('#66d9ef')),
            'operator': (self.formatColor('#ff4689')),
            'brace': (self.formatColor('darkGray')),
            'defclass': (self.formatColor('#a6e22e', 'bold')),
            'string': (self.formatColor('#e6db74')),
            'string2': (self.formatColor('#e6db74')),
            'comment': (self.formatColor('#959077', 'italic')),
            'self': (self.formatColor('#66d9ef', 'italic')),
            'numbers': (self.formatColor('#ae81ff')),
        }

        # Multi-line strings (expression, flag, style)
        self.tri_single = (QRegularExpression("'''"), 1, self.STYLES['string2'])
        self.tri_double = (QRegularExpression('"""'), 2, self.STYLES['string2'])

        rules = []

        # Keyword, operator, and brace rules
        rules += [(r'\b%s\b' % w, 0, self.STYLES['keyword'])
            for w in PythonHighlighter.keywords]
        rules += [(r'%s' % o, 0, self.STYLES['operator'])
            for o in PythonHighlighter.operators]
        rules += [(r'%s' % b, 0, self.STYLES['brace'])
            for b in PythonHighlighter.braces]

        # All other rules
        rules += [
            # 'self'
            (r'\bself\b', 0, self.STYLES['self']),

            # 'def' followed by an identifier
            (r'\bdef\b\s*(\w+)', 1, self.STYLES['defclass']),
            # 'class' followed by an identifier
            (r'\bclass\b\s*(\w+)', 1, self.STYLES['defclass']),

            # Numeric literals
            (r'\b[+-]?[0-9]+[lL]?\b', 0, self.STYLES['numbers']),
            (r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b', 0, self.STYLES['numbers']),
            (r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b', 0, self.STYLES['numbers']),

            # Double-quoted string, possibly containing escape sequences
            (r'"[^"\\]*(\\.[^"\\]*)*"', 0, self.STYLES['string']),
            # Single-quoted string, possibly containing escape sequences
            (r"'[^'\\]*(\\.[^'\\]*)*'", 0, self.STYLES['string']),

            # From '#' until a newline
            (r'#[^\n]*', 0, self.STYLES['comment']),
        ]

        # Build a QRegExp for each pattern
        self.rules = [(QRegularExpression(pat), index, fmt)
            for (pat, index, fmt) in rules]

    def highlightBlock(self, text: str) -> None:
        """Apply syntax highlighting to the given block of text.
        
        Args:
            text (str): Text block to highlight.
        """
        self.tripleQuoutesWithinStrings = []
        # Do other syntax formatting
        for expression, nth, _format in self.rules:
            match_iter = index = expression.globalMatch(text)
            while match_iter.hasNext():
                match = match_iter.next()
                index = match.capturedStart(nth)
                length = match.capturedLength(nth)

                # if there is a string we check
                # if there are some triple quotes within the string
                # they will be ignored if they are matched again
                if expression.pattern() in [r'"[^"\\]*(\\.[^"\\]*)*"', r"'[^'\\]*(\\.[^'\\]*)*'"]:
                    innerIndex = self.tri_single[0].match(text, index + 1).capturedStart()
                    if innerIndex == -1:
                        innerIndex = self.tri_double[0].match(text, index + 1).capturedStart()

                    if innerIndex != -1:
                        tripleQuoteIndexes = range(innerIndex, innerIndex + 3)
                        self.tripleQuoutesWithinStrings.extend(tripleQuoteIndexes)

                # skipping triple quotes within strings
                if index in self.tripleQuoutesWithinStrings:
                    continue

                self.setFormat(index, length, _format)

        self.setCurrentBlockState(0)

        # Do multi-line strings
        in_multiline = self.match_multiline(text, *self.tri_single)
        if not in_multiline:
            in_multiline = self.match_multiline(text, *self.tri_double)

    def formatColor(self, color: str, style: str = '') -> QTextCharFormat:
        """Return a QTextCharFormat with the given color and style.
        
        Args:
            color (str): Color name or hex code.
            style (str): Style string containing 'bold' or 'italic'.
            
        Returns:
            QTextCharFormat: Formatted text format.
        """
        if API_NAME == "PySide2":
            _color = QColor()
            _color.setNamedColor(color)
        else:
            if not hasattr(QColor, "fromString"):
                return

            _color = QColor.fromString(color)

        _format = QTextCharFormat()
        _format.setForeground(_color)
        if 'bold' in style:
            _format.setFontWeight(QFont.Bold)
        if 'italic' in style:
            _format.setFontItalic(True)

        return _format

    def match_multiline(self, text: str, delimiter: Any, in_state: int, style: QTextCharFormat) -> bool:
        """Highlight multi-line strings.
        
        Args:
            text (str): Text to process.
            delimiter (Any): QRegularExpression for triple quotes.
            in_state (int): Unique integer representing state inside multi-line string.
            style (QTextCharFormat): Text format to apply.
            
        Returns:
            bool: True if still inside multi-line string.
        """
        # If inside triple-single quotes, start at 0
        if self.previousBlockState() == in_state:
            start = 0
            add = 0
        # Otherwise, look for the delimiter on this line
        else:
            start = delimiter.match(text).capturedStart()
            # skipping triple quotes within strings
            if start in self.tripleQuoutesWithinStrings:
                return False
            # Move past this match
            add = delimiter.match(text).capturedLength()

        # As long as there's a delimiter match on this line...
        while start >= 0:
            # Look for the ending delimiter
            end = delimiter.match(text, start + add).capturedStart()
            # Ending delimiter on this line?
            if end >= add:
                length = end - start + add + delimiter.match(text).capturedLength()
                self.setCurrentBlockState(0)
            # No; multi-line string
            else:
                self.setCurrentBlockState(in_state)
                length = len(text) - start + add
            # Apply formatting
            self.setFormat(start, length, style)
            # Look for the next match
            start = delimiter.match(text, start + length).capturedStart()

        # Return True if still inside a multi-line string, False otherwise
        if self.currentBlockState() == in_state:
            return True
        else:
            return False


def create(app: str = "Standalone", prismArgs: Optional[List[str]] = None) -> 'PrismCore':
    """Create and initialize a PrismCore instance.
    
    Args:
        app (str): Application name. Defaults to "Standalone".
        prismArgs (Optional[List[str]]): Command line arguments for Prism.
        
    Returns:
        PrismCore: Initialized PrismCore instance.
    """
    prismArgs = prismArgs or []
    global qapp  # required for PyQt
    qapp = QApplication.instance()
    if not qapp:
        QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
        qapp = QApplication(sys.argv)

    iconPath = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "UserInterfacesPrism",
        "p_tray.png",
    )
    appIcon = QIcon(iconPath)
    qapp.setWindowIcon(appIcon)
    qapp.setApplicationName("PrismPipeline")
    qapp.setDesktopFileName("PrismPipeline")
    if (app == "Standalone" or "splash" in prismArgs) and "noSplash" not in prismArgs and "noUI" not in prismArgs:
        splash = SplashScreen()
        splash.show()
    else:
        splash = None

    pc = PrismCore(app=app, prismArgs=prismArgs, splashScreen=splash)
    if splash:
        splash.close()
        pc.splashScreen = None

    return pc


def show(app: str = "Standalone", prismArgs: Optional[List[str]] = None) -> None:
    """Create PrismCore instance and start Qt event loop.
    
    Args:
        app (str): Application name. Defaults to "Standalone".
        prismArgs (Optional[List[str]]): Command line arguments for Prism.
    """
    create(app, prismArgs)
    qapp = QApplication.instance()
    qapp.exec_()


class SplashScreen(QWidget):
    """Splash screen widget displayed during Prism initialization."""
    
    def __init__(self) -> None:
        """Initialize splash screen widget."""
        super(SplashScreen, self).__init__()
        self.setupUi()
        self.setStatus("initializing...")

    def setupUi(self) -> None:
        """Set up the splash screen user interface."""
        self.setWindowFlags(
            Qt.FramelessWindowHint
        )
        self.lo_main = QHBoxLayout()
        self.lo_main.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.lo_main)
        self.l_header = QLabel()
        self.lo_main.addWidget(self.l_header)
        headerPath = os.path.join(
            prismRoot, "Scripts", "UserInterfacesPrism", "prism_title.png"
        )
        pmap = QPixmap(headerPath)
        mode = Qt.KeepAspectRatio
        pmap = pmap.scaled(
            800, 500, mode, Qt.SmoothTransformation
        )

        self.l_header.setPixmap(pmap)
        self.l_header.setAlignment(Qt.AlignHCenter)
        self.adjustSize()  # make sure the splashscreen open centered on the screen

        self.l_status = QLabel()
        ssheet = "font-size: 11pt; color: rgb(200, 220, 235)"
        self.l_status.setStyleSheet(ssheet)
        self.l_status.setAlignment(Qt.AlignHCenter)
        self.w_labels = QWidget(self)
        self.lo_labels = QVBoxLayout()
        self.w_labels.setLayout(self.lo_labels)
        self.lo_labels.addStretch()
        self.lo_labels.addWidget(self.l_status)
        self.w_labels.setGeometry(
            0, 0, self.width(), self.height()
        )
        self.l_version = QLabel()
        ssheet = "color: rgb(200, 220, 235)"
        self.l_version.setStyleSheet(ssheet)
        self.l_version.setAlignment(Qt.AlignRight)
        self.lo_labels.addWidget(self.l_version)

    def resizeEvent(self, event: Any) -> None:
        """Handle window resize event.
        
        Args:
            event (Any): Resize event.
        """
        self.w_labels.setGeometry(
            0, 0, self.width(), self.height()
        )

    def setStatus(self, status: str) -> None:
        """Set status message text.
        
        Args:
            status (str): Status message.
        """
        self.l_status.setText(status)
        QApplication.processEvents()

    def setVersion(self, version: str) -> None:
        """Set version label text.
        
        Args:
            version (str): Version string.
        """
        self.l_version.setText(version)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("prism://"):
        import PrismTray
        if PrismTray.isAlreadyRunning():
            qApp = QApplication.instance()
            if not qApp:
                qApp = QApplication(sys.argv)

            result = PrismTray.sendCommandToPrismProcess("protocolHandler:" + sys.argv[1])

            if result:
                sys.exit()
            else:
                pcore = create("Standalone", prismArgs=["loadProject"])
                pcore.protocolHandler()

        else:
            pcore = create("Standalone", prismArgs=["loadProject"])
            pcore.protocolHandler()

    else:
        show(prismArgs=["loadProject"])
