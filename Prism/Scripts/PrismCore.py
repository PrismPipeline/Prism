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
from datetime import datetime
from multiprocessing.connection import Listener, Client

startEnv = os.environ.copy()

# check if python 2 or python 3 is used
if sys.version[0] == "3":
    pVersion = 3
    if sys.version[2] == "7":
        pyLibs = "Python37"
    elif sys.version[2] == "9":
        pyLibs = "Python39"
    else:
        pyLibs = "Python310"
else:
    pVersion = 2
    pyLibs = "Python27"

prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
prismLibs = os.getenv("PRISM_LIBS")

if not prismLibs:
    prismLibs = prismRoot

if not os.path.exists(os.path.join(prismLibs, "PythonLibs")):
    raise Exception('Prism: Couldn\'t find libraries. Set "PRISM_LIBS" to fix this.')

scriptPath = os.path.join(prismRoot, "Scripts")
if scriptPath not in sys.path:
    sys.path.append(scriptPath)

pyLibPath = os.path.join(prismLibs, "PythonLibs", pyLibs)
cpLibs = os.path.join(prismLibs, "PythonLibs", "CrossPlatform")

if cpLibs not in sys.path:
    sys.path.append(cpLibs)

if pyLibPath not in sys.path:
    sys.path.append(pyLibPath)

if sys.version[0] == "3":
    py3LibPath = os.path.join(prismLibs, "PythonLibs", "Python3")
    if py3LibPath not in sys.path:
        sys.path.append(py3LibPath)

    if platform.system() == "Windows":
        sys.path.insert(0, os.path.join(py3LibPath, "win32"))
        sys.path.insert(0, os.path.join(py3LibPath, "win32", "lib"))
        pywinpath = os.path.join(prismLibs, "PythonLibs", pyLibs, "pywin32_system32")
        sys.path.insert(0, pywinpath)
        os.environ["PATH"] = pywinpath + os.pathsep + os.environ["PATH"]
        if hasattr(os, "add_dll_directory") and os.path.exists(pywinpath):
            os.add_dll_directory(pywinpath)

try:
    from qtpy.QtCore import *
    from qtpy.QtGui import *
    from qtpy.QtWidgets import *
    from qtpy import API_NAME
    try:
        import shiboken2
    except:
        pass
except:
    if pVersion == 3:
        psLibs = "Python3"
    else:
        psLibs = "Python27"
    sys.path.insert(0, os.path.join(prismLibs, "PythonLibs", psLibs, "PySide"))
    from qtpy.QtCore import *
    from qtpy.QtGui import *
    from qtpy.QtWidgets import *
    from qtpy import API_NAME
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


logger = logging.getLogger(__name__)
if API_NAME == "PyQt5":
    logging.getLogger("PyQt5.uic.uiparser").setLevel(logging.WARNING)
    logging.getLogger("PyQt5.uic.properties").setLevel(logging.WARNING)


class TimeMeasure(object):
    def __enter__(self):
        self.startTime = datetime.now()
        logger.info("starttime: %s" % self.startTime.strftime("%Y-%m-%d %H:%M:%S"))

    def __exit__(self, type, value, traceback):
        endTime = datetime.now()
        logger.info("endtime: %s" % endTime.strftime("%Y-%m-%d %H:%M:%S"))
        logger.info("duration: %s" % (endTime - self.startTime))


# Prism core class, which holds various functions
class PrismCore:
    def __init__(self, app="Standalone", prismArgs=[], splashScreen=None):
        self.prismIni = ""

        try:
            # set some general variables
            self.version = "v2.0.0"
            self.requiredLibraries = "v2.0.0"
            self.core = self
            self.preferredExtension = os.getenv("PRISM_CONFIG_EXTENSION", ".json")

            startTime = datetime.now()

            self.prismRoot = prismRoot.replace("\\", "/")
            self.prismLibs = prismLibs.replace("\\", "/")
            self.pythonVersion = "Python39"

            self.userini = self.getUserPrefConfigPath()

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
            for path in self.pluginDirs:
                sys.path.append(path)

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

            self.stateData = []
            self.prjHDAs = []
            self.uiScaleFactor = 1

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

            # if no user ini exists, it will be created with default values
            self.configs = ConfigManager.ConfigManager(self)
            self.users = Users.Users(self)
            if not os.path.exists(self.userini):
                self.configs.createUserPrefs()

            logging.basicConfig()
            debug = os.getenv("PRISM_DEBUG")
            if debug is None:
                debug = self.getConfig("globals", "debug_mode")
            else:
                debug = debug.lower() in ["true", "1"]
            self.setDebugMode(debug)
            logger.debug("Initializing Prism %s - args: %s  - python: %s" % (self.version, self.prismArgs, sys.version.split(" (")[0]))

            self.useOnTop = self.getConfig("globals", "use_always_on_top")
            if self.useOnTop is None:
                self.useOnTop = True

            if sys.argv and sys.argv[-1] in ["setupStartMenu", "refreshIntegrations"]:
                self.prismArgs.pop(self.prismArgs.index("loadProject"))

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
            self.users.ensureUser()
            self.getUIscale()
            self.initializePlugins(app)
            atexit.register(self.onExit)
            QApplication.instance().aboutToQuit.connect(self.onExit)

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
    def getUserPrefDir(self):
        if os.getenv("PRISM_USER_PREFS"):
            return os.getenv("PRISM_USER_PREFS")

        if platform.system() == "Windows":
            path = self.getWindowsDocumentsPath()
        elif platform.system() == "Linux":
            path = os.path.join(os.environ["HOME"])
        elif platform.system() == "Darwin":
            path = os.path.join(os.environ["HOME"], "Library", "Preferences")

        path = os.path.join(path, "Prism2")
        return path

    @err_catcher(name=__name__)
    def getWindowsDocumentsPath(self):
        import ctypes.wintypes
        CSIDL_PERSONAL = 5       # My Documents
        SHGFP_TYPE_CURRENT = 0   # Get current, not default value

        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)

        path = buf.value
        return path

    @err_catcher(name=__name__)
    def getUserPrefConfigPath(self):
        dirPath = self.getUserPrefDir()
        configPath = os.path.join(dirPath, "Prism" + self.preferredExtension)
        return configPath

    @err_catcher(name=__name__)
    def getPrismDataDir(self):
        if os.getenv("PRISM_DATA_DIR"):
            return os.getenv("PRISM_DATA_DIR")

        path = os.path.join(os.environ["PROGRAMDATA"], "Prism2")
        return path

    @err_catcher(name=__name__)
    def initializePlugins(self, appPlugin):
        return self.plugins.initializePlugins(appPlugin=appPlugin)

    @err_catcher(name=__name__)
    def reloadPlugins(self, plugins=None):
        return self.plugins.reloadPlugins(plugins=plugins)

    @err_catcher(name=__name__)
    def reloadCustomPlugins(self):
        return self.plugins.reloadCustomPlugins()

    @err_catcher(name=__name__)
    def unloadProjectPlugins(self):
        return self.plugins.unloadProjectPlugins()

    @err_catcher(name=__name__)
    def unloadPlugin(self, pluginName):
        return self.plugins.unloadPlugin(pluginName=pluginName)

    @err_catcher(name=__name__)
    def getPluginNames(self):
        return self.plugins.getPluginNames()

    @err_catcher(name=__name__)
    def getPluginSceneFormats(self):
        return self.plugins.getPluginSceneFormats()

    @err_catcher(name=__name__)
    def getPluginData(self, pluginName, data):
        return self.plugins.getPluginData(pluginName=pluginName, data=data)

    @err_catcher(name=__name__)
    def getPlugin(self, pluginName, allowUnloaded=False):
        return self.plugins.getPlugin(pluginName=pluginName, allowUnloaded=allowUnloaded)

    @err_catcher(name=__name__)
    def getLoadedPlugins(self):
        return self.plugins.getLoadedPlugins()

    @err_catcher(name=__name__)
    def createPlugin(self, *args, **kwargs):
        return self.plugins.createPlugin(*args, **kwargs)

    @err_catcher(name=__name__)
    def callback(self, *args, **kwargs):
        return self.callbacks.callback(*args, **kwargs)

    @err_catcher(name=__name__)
    def registerCallback(self, *args, **kwargs):
        return self.callbacks.registerCallback(*args, **kwargs)

    @err_catcher(name=__name__)
    def unregisterCallback(self, *args, **kwargs):
        return self.callbacks.unregisterCallback(*args, **kwargs)

    @err_catcher(name=__name__)
    def callHook(self, *args, **kwargs):
        return self.callbacks.callHook(*args, **kwargs)

    @err_catcher(name=__name__)
    def startup(self):
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

        if curPrj:
            self.changeProject(curPrj)

        if (
            "silent" not in self.prismArgs
            and "noProjectBrowser" not in self.prismArgs
            and (self.getConfig("globals", "showonstartup") is not False or self.appPlugin.pluginName == "Standalone")
            and self.uiAvailable
        ):
            if self.splashScreen:
                self.splashScreen.setStatus("opening Project Browser...")

            self.projectBrowser()

        if self.getCurrentFileName() != "":
            self.sceneOpen()

        self.callback(name="postInitialize")
        self.status = "loaded"

    @err_catcher(name=__name__)
    def shouldAutosaveTimerRun(self):
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
    def isAutosaveTimerActive(self):
        active = hasattr(self, "autosaveTimer") and self.autosaveTimer.isActive()
        return active

    @err_catcher(name=__name__)
    def startAutosaveTimer(self, quit=False):
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
    def checkAutoSave(self):
        if not hasattr(self.appPlugin, "autosaveEnabled") or self.appPlugin.autosaveEnabled(self):
            return

        self.autosave_msg = QMessageBox()
        self.autosave_msg.setWindowTitle("Autosave")
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
    def autoSaveDone(self, action=2):
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
    def setDebugMode(self, enabled):
        self.debugMode = enabled
        os.environ["PRISM_DEBUG"] = str(enabled)
        logLevel = "DEBUG" if enabled else "WARNING"
        self.core.updateLogging(level=logLevel)

    @err_catcher(name=__name__)
    def updateLogging(self, level=None):
        if not level:
            level = "DEBUG" if self.debugMode else "WARNING"

        logging.root.setLevel(level)

    @err_catcher(name=__name__)
    def compareVersions(self, version1, version2):
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
            if sys.version[0] == "2":
                v1Data[idx] = unicode(v1Data[idx])
                v2Data[idx] = unicode(v2Data[idx])

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
    def checkCommands(self):
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

        for i in sorted(os.listdir(cmdDir)):
            if not i.startswith("prismCmd_"):
                continue

            filePath = os.path.join(cmdDir, i)
            if os.path.isfile(filePath) and os.path.splitext(filePath)[1] == ".txt":
                with open(filePath, "r") as comFile:
                    cmdText = comFile.read()

            command = None
            try:
                command = eval(cmdText)
            except:
                msg = (
                    "Could evaluate command: %s\n - %s"
                    % (cmdText, traceback.format_exc()),
                )
                self.popup(msg)

            self.handleCmd(command)
            os.remove(filePath)

    @err_catcher(name=__name__)
    def handleCmd(self, command):
        if command is None or type(command) != list:
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
    def createCmd(self, cmd, includeCurrent=False):
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
    def getLocalPath(self):
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
    def setLocalPath(self, path, projectName=None):
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
    def getQScreenGeo(self):
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
    def getUIscale(self):
        sFactor = 1
        highdpi = self.getConfig("globals", "highdpi")
        if highdpi:
            from qtpy import QtCore
            qtVers = [int(n) for n in QtCore.__version__.split(".")]

            if qtVers[0] >= 5 and qtVers[1] >= 6:
                screen = self.getQScreenGeo()
                if screen:
                    screenWidth, screenHeight = (
                        screen.width(),
                        screen.height(),
                    )
                    wFactor = screenWidth / 960.0
                    hFactor = screenHeight / 540.0
                    if abs(wFactor - 1) < abs(hFactor - 1):
                        sFactor = wFactor
                    else:
                        sFactor = hFactor

        # sFactor = QApplication.screens()[0].logicalDotsPerInch() / 96
        self.uiScaleFactor = sFactor
        return self.uiScaleFactor

    @err_catcher(name=__name__)
    def scaleUI(self, win=None, sFactor=0):
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
    def parentWindow(self, win, parent=None):
        self.scaleUI(win)
        if not self.appPlugin or not self.appPlugin.hasQtParent:
            if not self.appPlugin or (
                self.appPlugin.pluginName != "Standalone" and self.useOnTop
            ):
                win.setWindowFlags(win.windowFlags() | Qt.WindowStaysOnTopHint)

        if (not parent and not self.parentWindows) or not self.uiAvailable:
            return

        parent = parent or self.messageParent
        win.setParent(parent, Qt.Window)

        if platform.system() == "Darwin" and self.useOnTop:
            win.setWindowFlags(win.windowFlags() | Qt.WindowStaysOnTopHint)

    @err_catcher(name=__name__)
    def changeProject(self, *args, **kwargs):
        return self.projects.changeProject(*args, **kwargs)

    @err_catcher(name=__name__)
    def getAboutString(self):
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
Copyright (C) 2023 Prism Software GmbH<br>
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
    def showAbout(self):
        astr = self.getAboutString()
        self.popup(astr, title="About", severity="info")

    @err_catcher(name=__name__)
    def sendFeedbackDlg(self):
        fbDlg = PrismWidgets.EnterText()
        fbDlg.setModal(True)
        self.parentWindow(fbDlg)
        fbDlg.setWindowTitle("Send Message")
        fbDlg.l_info.setText("Message:\n")
        fbDlg.te_text.setMinimumHeight(200 * self.uiScaleFactor)
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

        size = QSize(fbDlg.size().width(), fbDlg.size().height() * 0.7)
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
    def sendFeedback(self, msg, subject="Prism feedback", attachment=None):
        self.reportHandler(msg, attachment=attachment, reportType="feedback")

    @err_catcher(name=__name__)
    def attachScreenGrab(self, dlg, size=None):
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
    def removeScreenGrab(self, dlg):
        dlg.screenGrab = None
        dlg.l_screenGrab.setPixmap(None)
        dlg.b_addScreenGrab.setVisible(True)
        dlg.b_removeScreenGrab.setVisible(False)
        dlg.resize(dlg.origSize)

    def openWebsite(self, location):
        if location == "home":
            url = "https://prism-pipeline.com/"
        elif location == "tutorials":
            url = "https://prism-pipeline.com/tutorials/"
        elif location == "documentation":
            url = "https://prism-pipeline.com/docs/latest"
        elif location == "downloads":
            url = "https://prism-pipeline.com/downloads/"
        else:
            url = location

        import webbrowser

        webbrowser.open(url)

    @err_catcher(name=__name__)
    def isObjectValid(self, obj):
        if "shiboken2" in globals():
            if not obj or not shiboken2.isValid(obj):
                return False
            else:
                return True

    @err_catcher(name=__name__)
    def getStateManager(self, create=True):
        sm = getattr(self, "sm", None)
        if not sm:
            sm = getattr(self, "stateManagerInCreation", None)

        if "shiboken2" in globals():
            if sm and not shiboken2.isValid(sm):
                sm = None

        if not sm and create:
            sm = self.stateManager(openUi=False)

        return sm

    @err_catcher(name=__name__)
    def stateManagerEnabled(self):
        return True  # self.appPlugin.appType == "3d"

    @err_catcher(name=__name__)
    def stateManager(
        self, stateDataPath=None, restart=False, openUi=True, reload_module=False, new_instance=False, standalone=False
    ):
        if not self.stateManagerEnabled():
            return False

        if not self.projects.ensureProject(openUi="stateManager"):
            return False

        if not self.users.ensureUser():
            return False

        if not self.sanities.runChecks("onOpenStateManager")["passed"]:
            return False

        if not getattr(self, "sm", None) or self.debugMode or reload_module or new_instance:
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

            sm = StateManager.StateManager(core=self, stateDataPath=stateDataPath, standalone=standalone)
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

        sm.saveStatesToScene()
        return sm

    @err_catcher(name=__name__)
    def closeSM(self, restart=False):
        if getattr(self, "sm", None):
            self.sm.saveEnabled = False
            wasOpen = self.isStateManagerOpen()
            if wasOpen:
                self.sm.close()

            if restart:
                return self.stateManager(openUi=wasOpen, reload_module=True)

    @err_catcher(name=__name__)
    def isStateManagerOpen(self):
        if not getattr(self, "sm", None):
            return False

        return self.sm.isVisible()

    @err_catcher(name=__name__)
    def projectBrowser(self, openUi=True):
        if not self.projects.ensureProject(openUi="projectBrowser"):
            return False

        if getattr(self, "pb", None) and self.pb.isVisible():
            self.pb.close()

        if not self.users.ensureUser():
            return False

        if not self.sanities.runChecks("onOpenProjectBrowser")["passed"]:
            return False

        if not getattr(self, "pb", None) or self.debugMode:
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
    def dependencyViewer(self, depRoot="", modal=False):
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

        if modal:
            self.dv.exec_()
        else:
            self.dv.show()

        return True

    @err_catcher(name=__name__)
    def prismSettings(self, tab=0, restart=False, reload_module=None, settingsType=None):
        if getattr(self, "ps", None) and self.ps.isVisible():
            self.ps.close()

        if not self.appPlugin:
            return

        if not getattr(self, "ps", None) or self.debugMode or restart or reload_module:
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
        return self.ps

    @err_catcher(name=__name__)
    def getInstaller(self, plugins=None):
        if getattr(self, "pinst", None) and self.pinst.isVisible():
            self.pinst.close()

        if eval(os.getenv("PRISM_DEBUG", "False")):
            try:
                del sys.modules["PrismInstaller"]
            except:
                pass

        import PrismInstaller

        self.pinst = PrismInstaller.PrismInstaller(core=self, plugins=plugins)
        return self.pinst

    @err_catcher(name=__name__)
    def openInstaller(self):
        pinst = self.getInstaller()
        pinst.show()

    @err_catcher(name=__name__)
    def openSetup(self):
        if getattr(self, "psetup", None) and self.psetup.isVisible():
            self.psetup.close()

        if eval(os.getenv("PRISM_DEBUG", "False")):
            try:
                del sys.modules["PrismInstaller"]
            except:
                pass

        import PrismInstaller

        self.psetup = PrismInstaller.PrismSetup(core=self)
        self.psetup.show()

    @err_catcher(name=__name__)
    def openConsole(self):
        executable = self.getPythonPath(executable="python")
        code = "\"import sys;sys.path.append(\\\"%s/Scripts\\\");import PrismCore;pcore=PrismCore.create(prismArgs=[\\\"noUI\\\", \\\"loadProject\\\"])" % (self.prismRoot.replace("\\", "/"))
        cmd = "start \"\" \"%s\" -i -c %s" % (executable, code)
        print(cmd)
        subprocess.Popen(cmd, shell=True)

    @err_catcher(name=__name__)
    def startTray(self):
        if (
            getattr(self, "PrismTray", None)
            or self.appPlugin.pluginName != "Standalone"
        ):
            return

        import PrismTray

        self.PrismTray = PrismTray.PrismTray(core=self)

    @err_catcher(name=__name__)
    def setupStartMenu(self, quiet=False):
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
    def setupUninstaller(self, quiet=False):
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
        cat=None,
        param=None,
        configPath=None,
        config=None,
        dft=None,
        location=None,
    ):
        return self.configs.getConfig(
            cat=cat,
            param=param,
            configPath=configPath,
            config=config,
            dft=dft,
            location=location,
        )

    @err_catcher(name=__name__)
    def setConfig(
        self,
        cat=None,
        param=None,
        val=None,
        data=None,
        configPath=None,
        delete=False,
        config=None,
        location=None,
        updateNestedData=True,
    ):
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
    def readYaml(self, path=None, data=None, stream=None):
        return self.configs.readYaml(
            path=path,
            data=data,
            stream=stream,
        )

    @err_catcher(name=__name__)
    def writeYaml(self, path=None, data=None, stream=None):
        return self.configs.writeYaml(path=path, data=data, stream=stream)

    @err_catcher(name=__name__)
    def missingModule(self, moduleName):
        if moduleName not in self.missingModules:
            self.missingModules.append(moduleName)
            self.popup(
                'Module "%s" couldn\'t be loaded.\nMake sure you have the latest Prism version installed.'
                % moduleName,
                title="Couldn't load module",
            )

    @err_catcher(name=__name__)
    def resolveFrameExpression(self, expression):
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
                if frame not in rframes:
                    rframes.append(frame)
                    if len(rframes) > 10000:
                        return rframes

                continue
            else:
                continue

            if end < start:
                step *= -1
                end -= 1
            else:
                end += 1

            for frame in range(start, end, step):
                if frame not in rframes:
                    rframes.append(frame)
                    if len(rframes) > 10000:
                        return rframes

        return rframes

    @err_catcher(name=__name__)
    def validateLineEdit(self, widget, allowChars=None, denyChars=None):
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
    def validateStr(self, text, allowChars=None, denyChars=None):
        invalidChars = [
            " ",
            "\\",
            "/",
            ":",
            "*",
            "?",
            '"',
            "<",
            ">",
            "|",
            "ä",
            "ö",
            "ü",
            "ß",
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

        if pVersion == 2:
            validText = "".join(
                ch if ch not in invalidChars else fallbackChar
                for ch in str(text.encode("ascii", errors="ignore"))
            )
        else:
            validText = "".join(
                ch if ch not in invalidChars else fallbackChar
                for ch in str(text.encode("ascii", errors="ignore").decode())
            )

        return validText

    @err_catcher(name=__name__)
    def isStr(self, data):
        if pVersion == 3:
            return isinstance(data, str)
        else:
            return isinstance(data, basestring)

    @err_catcher(name=__name__)
    def getIconForFileType(self, extension):
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
    def getCurrentFileName(self, path=True):
        currentFileName = self.appPlugin.getCurrentFileName(self, path)
        currentFileName = self.fixPath(currentFileName)

        return currentFileName

    @err_catcher(name=__name__)
    def fileInPipeline(self, filepath=None, validateFilename=True):
        if filepath is None:
            filepath = self.getCurrentFileName()

        filepath = self.fixPath(filepath)
        if filepath and filepath[0].islower():
            filepath = filepath[0].upper() + filepath[1:]

        validName = False
        if validateFilename:
            fileNameData = self.getScenefileData(filepath)
            validName = fileNameData.get("type") in ["asset", "shot"]

        seqPath = os.path.dirname(
            self.projects.getResolvedProjectStructurePath("sequences")
        )

        if (
            (
                self.fixPath(self.assetPath) in filepath
                or self.fixPath(seqPath) in filepath
            )
            or (
                self.useLocalFiles
                and (
                    self.fixPath(self.core.getAssetPath(location="local")) in filepath
                    or self.fixPath(self.core.getSequencePath(location="local")) in filepath
                )
            )
        ) and (validName or not validateFilename):
            return True
        else:
            return False

    @err_catcher(name=__name__)
    def detectFileSequence(self, path):
        pathDir = os.path.dirname(path)
        regName = ""
        seqFiles = []

        path = path.replace("$F4", "1001")
        for root, folders, files in os.walk(pathDir):
            siblings = [os.path.join(root, f) for f in files]
            break

        for ch in re.escape(os.path.basename(path)):
            if sys.version[0] == "2":
                ch = unicode(ch)

            if ch.isnumeric():
                regName += "."
            else:
                regName += ch

        r = re.compile(regName)
        for sibling in siblings:
            if r.match(os.path.basename(sibling)):
                seqFiles.append(sibling)

        return seqFiles

    @err_catcher(name=__name__)
    def getFilesFromFolder(self, path, recursive=True):
        foundFiles = []
        for root, folders, files in os.walk(path):
            for file in files:
                path = os.path.join(root, file)
                foundFiles.append(path)

            if not recursive:
                break

        return foundFiles

    @err_catcher(name=__name__)
    def getEntityPath(self, *args, **kwargs):
        return self.paths.getEntityPath(*args, **kwargs)

    @err_catcher(name=__name__)
    def generateScenePath(self, *args, **kwargs):
        return self.paths.generateScenePath(*args, **kwargs)

    @err_catcher(name=__name__)
    def getScenefileData(self, *args, **kwargs):
        return self.entities.getScenefileData(*args, **kwargs)

    @err_catcher(name=__name__)
    def getHighestVersion(self, *args, **kwargs):
        return self.entities.getHighestVersion(*args, **kwargs)

    @err_catcher(name=__name__)
    def getTaskNames(self, *args, **kwargs):
        return self.entities.getTaskNames(*args, **kwargs)

    @err_catcher(name=__name__)
    def getAssetPath(self, location="global"):
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
    def assetPath(self):
        if not getattr(self, "_assetPath", None):
            self._assetPath = self.getAssetPath()

        return self._assetPath

    @err_catcher(name=__name__)
    def getShotPath(self, location="global"):
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
    def shotPath(self):
        if not getattr(self, "_shotPath", None):
            self._shotPath = self.getShotPath()

        return self._shotPath

    @err_catcher(name=__name__)
    def getSequencePath(self, location="global"):
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
    def sequencePath(self):
        if not getattr(self, "_sequencePath", None):
            self._sequencePath = self.getSequencePath()

        return self._sequencePath

    @err_catcher(name=__name__)
    def convertPath(self, path, target="global"):
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
    def getTexturePath(self, location="global"):
        path = self.projects.getResolvedProjectStructurePath("textures")
        path = os.path.normpath(path)
        return path

    @property
    def texturePath(self):
        if not getattr(self, "_texturePath", None):
            self._texturePath = self.getTexturePath()

        return self._texturePath

    @err_catcher(name=__name__)
    def showFileNotInProjectWarning(self, title=None, msg=None):
        title = title or "Could not save the file"
        msg = msg or "The current scenefile is not saved in the current Prism project.\nUse the Project Browser to save your scene in the project."
        result = self.popupQuestion(msg, buttons=["Open Project Browser", "Close"], title=title, icon=QMessageBox.Warning)
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

    @err_catcher(name=__name__)
    def saveScene(
        self,
        comment="",
        publish=False,
        versionUp=True,
        prismReq=True,
        filepath="",
        details=None,
        preview=None,
        location="local",
    ):
        details = details or {}
        if filepath == "":
            curfile = self.getCurrentFileName()
            filepath = curfile.replace("\\", "/")
            if not filepath:
                self.showFileNotInProjectWarning()
                return False
        else:
            versionUp = False
            curfile = None

        if prismReq:
            if not self.projects.ensureProject():
                return False

            if not self.users.ensureUser():
                return False

            if not self.fileInPipeline(filepath, validateFilename=False):
                self.showFileNotInProjectWarning()
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
                fnameData = self.getScenefileData(curfile)
                if "department" not in fnameData:
                    title = "Could not save the file"
                    msg = "Couldn't get the required data from the current scenefile. Did you save it using Prism?\nUse the Project Browser to save your current scenefile with the correct name."
                    self.popup(msg, title=title)
                    return False

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

        result = self.appPlugin.saveScene(self, filepath, details)
        if result is False:
            logger.debug("failed to save scene")
            return False

        if curfile:
            detailData = self.getScenefileData(curfile)
            if detailData.get("type") == "asset":
                key = "assetScenefiles"
            elif detailData.get("type") == "shot":
                key = "shotScenefiles"
            else:
                key = None

            if key:
                template = self.core.projects.getTemplatePath(key)
                pathdata = self.core.projects.extractKeysFromPath(filepath, template, context=detailData)
                if pathdata.get("asset_path"):
                    pathdata["asset"] = os.path.basename(pathdata["asset_path"])

                detailData.update(pathdata)

            detailData["comment"] = comment
            if "user" in detailData:
                del detailData["user"]
            if "username" in detailData:
                del detailData["username"]
        else:
            detailData = {}

        detailData.update(details)
        if prismReq:
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
            self.pb.sceneBrowser.refreshScenefiles()
        except:
            pass

        return filepath

    @err_catcher(name=__name__)
    def getVersioninfoPath(self, scenepath):
        prefExt = self.configs.getProjectExtension()
        base, ext = os.path.splitext(scenepath)
        if ext:
            filepath = base + "versioninfo" + prefExt
        else:
            filepath = os.path.join(base, "versioninfo" + prefExt)
        return filepath

    @err_catcher(name=__name__)
    def saveSceneInfo(self, filepath, details=None, preview=None, clean=True):
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

        sData = self.getScenefileData(filepath)
        sData.update(details)

        if clean:
            keys = ["filename", "extension", "path", "paths", "task_path"]
            for key in keys:
                if key in sData:
                    del sData[key]

        infoPath = self.getVersioninfoPath(filepath)
        self.setConfig(configPath=infoPath, data=sData)

        if preview:
            self.core.entities.setScenePreview(filepath, preview)

    @err_catcher(name=__name__)
    def saveVersionInfo(self, filepath, details=None):
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
    def saveWithComment(self):
        if not self.projects.ensureProject():
            return False

        if not self.users.ensureUser():
            return False

        if not self.fileInPipeline():
            self.showFileNotInProjectWarning()
            return False

        self.savec = PrismWidgets.SaveComment(core=self)
        self.savec.accepted.connect(lambda: self.saveWithCommentAccepted(self.savec))
        self.savec.show()
        self.savec.activateWindow()
        return True

    @err_catcher(name=__name__)
    def saveWithCommentAccepted(self, dlg):
        if dlg.previewDefined:
            prvPMap = dlg.l_preview.pixmap()
        else:
            prvPMap = None

        details = dlg.getDetails() or {}
        self.saveScene(comment=dlg.e_comment.text(), details=details, preview=prvPMap)

    @err_catcher(name=__name__)
    def getScenefilePaths(self, scenePath):
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
    def copySceneFile(self, origFile, targetFile, mode="copy"):
        origFile = self.fixPath(origFile)
        targetFile = self.fixPath(targetFile)
        if origFile == targetFile:
            return

        if not os.path.exists(os.path.dirname(targetFile)):
            os.makedirs(os.path.dirname(targetFile))

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
    def getRecentScenefiles(self, project=None):
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
    def addToRecent(self, filepath):
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
    def fixPath(self, path):
        if path is None:
            return

        if platform.system() == "Windows":
            path = path.replace("/", "\\")
        else:
            path = path.replace("\\", "/")

        return path

    @err_catcher(name=__name__)
    def getFileModificationDate(self, path, validate=False, ignoreError=True, asString=True, asDatetime=False):
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
    def getFormattedDate(self, stamp):
        if self.isStr(stamp):
            return ""

        cdate = datetime.fromtimestamp(stamp)
        cdate = cdate.replace(microsecond=0)
        fmt = "%d.%m.%y,  %H:%M:%S"
        if os.getenv("PRISM_DATE_FORMAT"):
            fmt = os.getenv("PRISM_DATE_FORMAT")

        cdate = cdate.strftime(fmt)
        return cdate

    @err_catcher(name=__name__)
    def openFolder(self, path):
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
    def createFolder(self, path, showMessage=False):
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
    def replaceFolderContent(self, path, fromStr, toStr):
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
    def copyToClipboard(self, text, fixSlashes=True, file=False):
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
            cb.setText(text)

    @err_catcher(name=__name__)
    def getClipboard(self):
        cb = QClipboard()
        try:
            rawText = cb.text("plain")[0]
        except:
            return

        return rawText

    @err_catcher(name=__name__)
    def copyfolder(self, src, dst, thread=None):
        shutil.copytree(src, dst)
        if thread and thread.canceled:
            try:
                shutil.rmtree(dst)
            except:
                pass

            return

        return dst

    @err_catcher(name=__name__)
    def copyfile(self, src, dst, thread=None, follow_symlinks=True):
        """Copy data from src to dst.

        If follow_symlinks is not set and src is a symbolic link, a new
        symlink will be created instead of copying the file it points to.

        """
        if shutil._samefile(src, dst):
            raise shutil.SameFileError(
                "{!r} and {!r} are the same file".format(src, dst)
            )

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
            size = os.stat(src).st_size
            # thread.updated.emit("Getting source hash")
            # vSourceHash = hashlib.md5(open(src, "rb").read()).hexdigest()
            # vDestinationHash = ""
            # while vSourceHash != vDestinationHash:
            with open(src, "rb") as fsrc:
                with open(dst, "wb") as fdst:
                    result = self.copyfileobj(fsrc, fdst, total=size, thread=thread, path=dst)

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

        shutil.copymode(src, dst)
        return dst

    @err_catcher(name=__name__)
    def copyfileobj(self, fsrc, fdst, total, thread=None, length=16 * 1024, path=""):
        copied = 0
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

            copied += len(buf)
            if thread:
                prc = int((copied / total) * 100)
                if prc != prevPrc:
                    prevPrc = prc
                    thread.updated.emit("Progress: %s%%" % prc)

        return True

    @err_catcher(name=__name__)
    def copyWithProgress(self, src, dst, follow_symlinks=True, popup=True, start=True, finishCallback=None):
        if os.path.isdir(dst):
            dst = os.path.join(dst, os.path.basename(src))

        self.copyThread = Worker(self.core)
        if os.path.isdir(src):
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
            self.copyThread.updated.connect(self.updateProgressPopup)
            self.copyMsg = self.core.waitPopup(
                self.core, "Copying file - please wait..\n\n\n"
            )

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
    def updateProgressPopup(self, progress, popup=None):
        if not popup:
            popup = self.copyMsg

        text = popup.msg.text()
        updatedText = text.rsplit("\n", 2)[0] + "\n" + progress + "\n"
        popup.msg.setText(updatedText)

    @err_catcher(name=__name__)
    def getDefaultWindowsAppByExtension(self, ext):
        try:
            if sys.version[0] == "3":
                import winreg as _winreg
            else:
                import _winreg
        except Exception as e:
            logger.warning("failed to load winreg: %s" % e)
            return

        import shlex
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
            path = shlex.split(path, posix=False)[0]
            path = path.strip('"')

        return path

    @err_catcher(name=__name__)
    def getExecutableOverride(self, pluginName):
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
    def openFile(self, filepath):
        filepath = filepath.replace("\\", "/")
        logger.debug("Opening file " + filepath)
        fileStarted = False
        ext = os.path.splitext(filepath)[1]
        appPath = ""

        if ext in self.appPlugin.sceneFormats:
            return self.appPlugin.openScene(self, filepath)

        for plugin in self.core.unloadedAppPlugins.values():
            if ext in plugin.sceneFormats:
                override = self.getExecutableOverride(plugin.pluginName)
                if override:
                    appPath = override

                fileStarted = getattr(
                    plugin, "customizeExecutable", lambda x1, x2, x3: False
                )(self, appPath, filepath)

        if not appPath and not fileStarted:
            appPath = self.getDefaultWindowsAppByExtension(ext)

        if appPath and not fileStarted:
            args = []
            if isinstance(appPath, list):
                args += appPath
            else:
                args.append(appPath)

            args.append(self.core.fixPath(filepath))
            logger.debug("starting DCC with args: %s" % args)
            try:
                subprocess.Popen(args, env=self.startEnv)
            except:
                if os.path.isfile(args[0]):
                    msg = "Could not execute file:\n\n%s\n\nUsed arguments: %s" % (traceback.format_exc(), args)
                else:
                    msg = "Executable doesn't exist:\n\n%s\n\nCheck your executable override in the Prism User Settings." % args[0]
                self.core.popup(msg)

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
        self, vPath, vTarget="", args="", vWorkingDir="", vIcon=""
    ):
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
    def createShortcut(self, link, target, args="", ignoreError=False):
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
                result = proc.communicate()[0]
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
    def createSymlink(self, link, target):
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
    def setTrayStartupWindows(self, enabled):
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
    def getTempFilepath(self, filename=None, ext=".jpg", filenamebase=None):
        filenamebase = filenamebase or "prism"
        path = os.path.join(os.environ["temp"], "Prism", filenamebase + "_")

        if filename:
            filepath = os.path.join(path, filename)
        else:
            file = tempfile.NamedTemporaryFile(prefix=path, suffix=ext)
            filepath = file.name
            file.close()

        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))

        return filepath

    @property
    @err_catcher(name=__name__)
    def timeMeasure(self):
        """
        with self.core.timeMeasure:
        """
        if not hasattr(self, "_timeMeasure"):
            self._timeMeasure = TimeMeasure()

        return self._timeMeasure

    @err_catcher(name=__name__)
    def checkIllegalCharacters(self, strings):
        illegalStrs = []
        for i in strings:
            if not all(ord(c) < 128 for c in i):
                illegalStrs.append(i)

        return illegalStrs

    @err_catcher(name=__name__)
    def atoi(self, text):
        return int(text) if text.isdigit() else text

    @err_catcher(name=__name__)
    def naturalKeys(self, text):
        return [self.atoi(c) for c in re.split(r"(\d+)", text)]

    @err_catcher(name=__name__)
    def sortNatural(self, alist):
        sortedList = sorted(alist, key=self.naturalKeys)
        return sortedList

    @err_catcher(name=__name__)
    def scenefileSaved(self, arg=None):  # callback function
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
    def sceneUnload(self, arg=None):  # callback function
        if getattr(self, "sm", None):
            self.openSm = self.sm.isVisible()
            self.sm.close()
            del self.sm

        if self.getLockScenefilesEnabled():
            self.unlockScenefile()

        if self.shouldAutosaveTimerRun():
            self.startAutosaveTimer()

    @err_catcher(name=__name__)
    def sceneOpen(self, arg=None):  # callback function
        if not self.sceneOpenChecksEnabled:
            return

        openSm = getattr(self, "openSm", None) or (getattr(self, "sm", None) and self.sm.isVisible())
        getattr(self.appPlugin, "sceneOpen", lambda x: None)(self)

        filepath = self.getCurrentFileName()
        if self.getLockScenefilesEnabled():
            self.lockScenefile(filepath)

        # trigger auto imports
        if os.path.exists(self.prismIni):
            self.stateManager(openUi=openSm, reload_module=True)

        self.openSm = False
        self.sanities.checkImportVersions()
        self.sanities.checkFramerange()
        self.sanities.checkFPS()
        self.sanities.checkResolution()
        self.updateEnvironment()
        self.core.callback(name="onSceneOpen", args=[filepath])

    @err_catcher(name=__name__)
    def onExit(self):
        self.unlockScenefile()

    @err_catcher(name=__name__)
    def unlockScenefile(self):
        if getattr(self, "sceneLockfile", None) and self.sceneLockfile.isLocked():
            self.sceneLockfile.release()

    @err_catcher(name=__name__)
    def lockScenefile(self, filepath=None):
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
    def shouldScenelockTimerRun(self):
        if not self.getLockScenefilesEnabled():
            return False

        qapp = QApplication.instance()
        isGuiThread = qapp and qapp.thread() == QThread.currentThread()
        if "silent" in self.prismArgs or not self.uiAvailable or not isGuiThread:
            return

        return True

    @err_catcher(name=__name__)
    def isScenelockTimerActive(self):
        active = hasattr(self, "scenelockTimer") and self.scenelockTimer.isActive()
        return active

    @err_catcher(name=__name__)
    def startSceneLockTimer(self, quit=False):
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
    def getLockScenefilesEnabled(self):
        return self.getConfig("globals", "scenefileLocking", config="project")

    @err_catcher(name=__name__)
    def updateEnvironment(self):
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

        for envvar in envvars:
            envvars[envvar] = os.getenv(envvar)

        newenv = {}

        fn = self.getCurrentFileName()
        data = self.getScenefileData(fn)
        if data.get("type") == "asset":
            newenv["PRISM_SEQUENCE"] = ""
            newenv["PRISM_SHOT"] = ""
            newenv["PRISM_ASSET"] = os.path.basename(data.get("asset_path", ""))
            newenv["PRISM_ASSETPATH"] = data.get("asset_path", "").replace("\\", "/")
        elif data.get("type") == "shot":
            newenv["PRISM_ASSET"] = ""
            newenv["PRISM_ASSETPATH"] = ""
            newenv["PRISM_SEQUENCE"] = data.get("sequence", "")
            newenv["PRISM_SHOT"] = data.get("shot", "")
        else:
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
    def updateProjectEnvironment(self):
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
    def setTrayStartup(self, enabled):
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
    def getFrameRange(self):
        return self.appPlugin.getFrameRange(self)

    @err_catcher(name=__name__)
    def setFrameRange(self, startFrame, endFrame):
        self.appPlugin.setFrameRange(self, startFrame, endFrame)

    @err_catcher(name=__name__)
    def getFPS(self):
        fps = getattr(self.appPlugin, "getFPS", lambda x: None)(self)
        if fps is not None:
            fps = float(fps)

        return fps

    @err_catcher(name=__name__)
    def getResolution(self):
        if hasattr(self.appPlugin, "getResolution"):
            return self.appPlugin.getResolution()

    @err_catcher(name=__name__)
    def getCompositingOut(self, *args, **kwargs):
        return self.paths.getCompositingOut(*args, **kwargs)

    @err_catcher(name=__name__)
    def registerStyleSheet(self, path, default=False):
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
    def getRegisteredStyleSheets(self):
        return self.registeredStyleSheets

    @err_catcher(name=__name__)
    def getActiveStyleSheet(self):
        return self.activeStyleSheet

    @err_catcher(name=__name__)
    def setActiveStyleSheet(self, name):
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
    def getStyleSheet(self, name):
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
    def getPythonPath(self, executable=None, root=None):
        if platform.system() == "Windows":
            root = root or self.prismLibs
            if executable:
                pythonPath = os.path.join(root, self.pythonVersion, "%s.exe" % executable)
                if os.path.exists(pythonPath):
                    return pythonPath
                else:
                    pythonPath = os.path.join(root, "*", "%s.exe" % executable)
                    paths = glob.glob(pythonPath)
                    if paths:
                        return paths[0]

            pythonPath = os.path.join(root, self.pythonVersion, "pythonw.exe")
            if not os.path.exists(pythonPath):
                pythonPath = os.path.join(root, "Python27", "pythonw.exe")
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

        else:
            pythonPath = "python"

        return pythonPath

    @err_catcher(name=__name__)
    def handleRemoveReadonly(self, func, path, exc):
        excvalue = exc[1]
        if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
            os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
            func(path)
        else:
            raise

    @err_catcher(name=__name__)
    def ffmpegError(self, title, text, result):
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
    def isPopupTooLong(self, text):
        rows = text.split("\n")
        tooLong = len(rows) > 50
        return tooLong

    @err_catcher(name=__name__)
    def shortenPopupMsg(self, text):
        rows = text.split("\n")
        rows = rows[:50]
        shortText = "\n".join(rows)
        shortText += "\n..."
        return shortText

    @err_catcher(name=__name__)
    def popup(
        self,
        text,
        title=None,
        severity="warning",
        notShowAgain=False,
        parent=None,
        modal=True,
        widget=None,
        show=True,
    ):
        if title is None:
            if severity == "warning":
                title = "Prism - Warning"
            elif severity == "info":
                title = "Prism - Information"
            elif severity == "error":
                title = "Prism - Error"

        if pVersion == 3:
            if not isinstance(text, str):
                text = str(text)
            if not isinstance(title, str):
                title = str(title)
        else:
            if not isinstance(text, basestring):
                text = unicode(text)
            if not isinstance(title, basestring):
                title = unicode(title)

        qapp = QApplication.instance()
        isGuiThread = qapp and qapp.thread() == QThread.currentThread()

        if "silent" not in self.prismArgs and self.uiAvailable and isGuiThread:
            parent = parent or getattr(self, "messageParent", None)
            msg = QMessageBox(parent)
            if self.isPopupTooLong(text):
                text = self.shortenPopupMsg(text)
            msg.setText(text)
            msg.setWindowTitle(title)
            msg.setModal(modal)

            if "<a href=" in text:
                msg.setTextFormat(Qt.RichText);

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
        text,
        title=None,
        buttons=None,
        default=None,
        icon=None,
        widget=None,
        parent=None,
        escapeButton=None,
        doExec=True,
    ):
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

        self.parentWindow(msg)
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
        text,
        title=None,
        buttons=None,
        default=None,
        icon=None,
        parent=None,
        show=True,
    ):
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
        """
        with self.core.waitPopup(self.core, text):

        """

        canceled = Signal()

        def __init__(
            self,
            core,
            text,
            title=None,
            buttons=None,
            default=None,
            icon=None,
            hidden=False,
            parent=None,
            allowCancel=False,
            activate=True,
        ):
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

        def __enter__(self):
            if not self.hidden:
                self.show()

            return self

        def __exit__(self, type, value, traceback):
            self.close()

        def createPopup(self):
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

        def show(self):
            if not self.msg:
                self.createPopup()

            if self.core.uiAvailable:
                for button in self.msg.buttons():
                    button.setVisible(self.allowCancel)

                self.msg.show()
                QCoreApplication.processEvents()

        def exec_(self):
            if not self.msg:
                self.createPopup()

            for button in self.msg.buttons():
                button.setVisible(self.allowCancel)

            result = self.msg.exec_()
            if result:
                self.cancel()

        def isVisible(self):
            if not self.msg:
                return False

            return self.msg.isVisible()

        def close(self):
            if self.msg and self.msg.isVisible():
                self.msg.close()

        def cancel(self):
            self.isCanceled = True
            self.canceled.emit()

    def writeErrorLog(self, text, data=None):
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
                prjErPath = os.path.join(
                    os.path.dirname(self.prismIni), "ErrorLog_%s.txt" % self.user
                )
                try:
                    open(prjErPath, "a").close()
                except:
                    pass

                if os.path.exists(prjErPath):
                    with open(prjErPath, "a") as erLog:
                        erLog.write(text)

            if getattr(self, "userini", None):
                userErPath = os.path.join(
                    os.path.dirname(self.userini),
                    "ErrorLog_%s.txt" % socket.gethostname(),
                )

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

    def showErrorPopup(self, text, data=None):
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

    def showErrorDetailPopup(self, text, sendReport=True, data=None):
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

    def sendAutomaticErrorReport(self, text, data=None):
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

    def sendError(self, errorText):
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

    def sendErrorReport(self, dlg, errorMessage):
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
    def copyFile(self, source, destination, adminFallback=True):
        try:
            shutil.copy2(source, destination)
            return True
        except Exception:
            if adminFallback and platform.system() == "Windows":
                return self.copyFileAsAdmin(source, destination)

        return False

    @err_catcher(name=__name__)
    def removeFile(self, path, adminFallback=True):
        try:
            os.remove(path)
            return True
        except Exception:
            if adminFallback and platform.system() == "Windows":
                return self.removeFileAsAdmin(path)

        return False

    @err_catcher(name=__name__)
    def writeToFile(self, path, text, adminFallback=True):
        try:
            with open(path, "w") as f:
                f.write(text)
            return True
        except Exception:
            if adminFallback and platform.system() == "Windows":
                return self.writeToFileAsAdmin(path, text)

        return False

    @err_catcher(name=__name__)
    def createDirectory(self, path, adminFallback=True):
        try:
            os.makedirs(path)
            return True
        except Exception:
            if adminFallback and platform.system() == "Windows":
                return self.createFolderAsAdmin(path)

        return False

    @err_catcher(name=__name__)
    def getCopyFileCmd(self, source, destination):
        source = source.replace("\\", "/")
        destination = destination.replace("\\", "/")
        cmd = "import shutil;shutil.copy2('%s', '%s')" % (source, destination)
        return cmd

    @err_catcher(name=__name__)
    def copyFileAsAdmin(self, source, destination):
        cmd = self.getCopyFileCmd(source, destination)
        self.winRunAsAdmin(cmd)
        result = self.validateCopyFile(source, destination)
        return result

    @err_catcher(name=__name__)
    def validateCopyFile(self, source, destination):
        result = os.path.exists(destination)
        return result

    @err_catcher(name=__name__)
    def getRemoveFileCmd(self, path):
        cmd = "import os;os.remove('%s')" % path.replace("\\", "/")
        return cmd

    @err_catcher(name=__name__)
    def removeFileAsAdmin(self, path):
        cmd = self.getRemoveFileCmd(path)
        self.winRunAsAdmin(cmd)
        result = self.validateRemoveFile(path)
        return result

    @err_catcher(name=__name__)
    def validateRemoveFile(self, path):
        result = not os.path.exists(path)
        return result

    @err_catcher(name=__name__)
    def getWriteToFileCmd(self, path, text):
        tempPath = tempfile.NamedTemporaryFile().name
        self.writeToFile(tempPath, text, adminFallback=False)
        cmd = self.getCopyFileCmd(tempPath, path)
        return cmd

    @err_catcher(name=__name__)
    def writeToFileAsAdmin(self, path, text):
        tempPath = tempfile.NamedTemporaryFile().name
        self.writeToFile(tempPath, text, adminFallback=False)
        result = self.copyFileAsAdmin(tempPath, path)
        os.remove(tempPath)
        return result

    @err_catcher(name=__name__)
    def validateWriteToFile(self, path, text):
        with open(path, "r") as f:
            data = f.read()

        result = data == text
        return result

    @err_catcher(name=__name__)
    def getCreateFolderCmd(self, path):
        cmd = "import os;os.makedirs('%s')" % path.replace("\\", "/")
        return cmd

    @err_catcher(name=__name__)
    def createFolderAsAdmin(self, path):
        cmd = self.getCreateFolderCmd(path)
        self.winRunAsAdmin(cmd)
        result = self.validateCreateFolder(path)
        return result

    @err_catcher(name=__name__)
    def validateCreateFolder(self, path):
        result = os.path.exists(path)
        return result

    @err_catcher(name=__name__)
    def winRunAsAdmin(self, script):
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
    def runFileCommands(self, commands):
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
    def runFileCommand(self, command):
        if command["type"] == "copyFile":
            result = self.core.copyFile(*command["args"], adminFallback=False)
        elif command["type"] == "removeFile":
            result = self.core.removeFile(*command["args"], adminFallback=False)
        elif command["type"] == "writeToFile":
            result = self.core.writeToFile(*command["args"], adminFallback=False)
        elif command["type"] == "createFolder":
            result = self.core.createDirectory(*command["args"], adminFallback=False)

        return result

    @err_catcher(name=__name__)
    def getFileCommandStr(self, command):
        if command["type"] == "copyFile":
            result = self.core.getCopyFileCmd(*command["args"])
        elif command["type"] == "removeFile":
            result = self.core.getRemoveFileCmd(*command["args"])
        elif command["type"] == "writeToFile":
            result = self.core.getWriteToFileCmd(*command["args"])
        elif command["type"] == "createFolder":
            result = self.core.getCreateFolderCmd(*command["args"])

        return result

    @err_catcher(name=__name__)
    def validateFileCommand(self, command):
        if command["type"] == "copyFile":
            result = self.core.validateCopyFile(*command["args"])
        elif command["type"] == "removeFile":
            result = self.core.validateRemoveFile(*command["args"])
        elif command["type"] == "writeToFile":
            result = self.core.validateWriteToFile(*command["args"])
        elif command["type"] == "createFolder":
            result = self.core.validateCreateFolder(*command["args"])

        return result

    @err_catcher(name=__name__)
    def startCommunication(self, port, key, callback=None):
        listener = self.startServer(port, key)
        if listener:
            conn = self.startClient(port+1, key)
            if conn:
                self.runServer(listener, conn, callback=callback)
            else:
                listener.close()

    @err_catcher(name=__name__)
    def startServer(self, port, key):
        logger.debug("starting server (%s)" % port)
        address = ("localhost", port)

        listener = Listener(address, authkey=key)
        return listener

    @err_catcher(name=__name__)
    def startClient(self, port, key):
        logger.debug("starting client (%s)" % port)
        address = ("localhost", port)

        conn = Client(address, authkey=key)
        return conn

    @err_catcher(name=__name__)
    def runServer(self, listener, conn, callback=None):
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
    def sendData(self, data, conn):
        logger.debug("sending data: %s" % data)

        if data is None:
            data = ""

        conn.send(data)


class Worker(QThread):
    warningSent = Signal(object)
    errored = Signal(object)
    updated = Signal(object)
    dataSent = Signal(object)

    def __init__(self, core=None, function=None):
        super(Worker, self).__init__()
        if core:
            self.core = core

        self.function = function
        self.canceled = False

    def run(self):
        try:
            self.function()
        except Exception as e:
            self.errored.emit(str(e))

    def cancel(self):
        self.canceled = True


class ErrorDetailsDialog(QDialog):
    def __init__(self, core, text):
        super(ErrorDetailsDialog, self).__init__()
        self.core = core
        self.core.parentWindow(self)
        self.text = text
        self.clickedButton = None
        self.setupUi()

    def sizeHint(self):
        return QSize(1000, 500)

    def showEvent(self, event):
        super(ErrorDetailsDialog, self).showEvent(event)
        self.l_message.verticalScrollBar().setValue(self.l_message.verticalScrollBar().maximum())

    def setupUi(self):
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


def create(app="Standalone", prismArgs=None):
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


def show(app="Standalone", prismArgs=None):
    create(app, prismArgs)
    qapp = QApplication.instance()
    qapp.exec_()


class SplashScreen(QWidget):
    def __init__(self):
        super(SplashScreen, self).__init__()
        self.setupUi()
        self.setStatus("initializing...")

    def setupUi(self):
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

    def resizeEvent(self, event):
        self.w_labels.setGeometry(
            0, 0, self.width(), self.height()
        )

    def setStatus(self, status):
        self.l_status.setText(status)
        QApplication.processEvents()

    def setVersion(self, version):
        self.l_version.setText(version)


if __name__ == "__main__":
    show(prismArgs=["loadProject"])
