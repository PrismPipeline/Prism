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
import threading
import shutil
import time
import socket
import traceback
import imp
import platform
import errno
import stat
import re
import subprocess
import logging
import tempfile
import hashlib
from collections import OrderedDict
from datetime import datetime

# check if python 2 or python 3 is used
if sys.version[0] == "3":
    pVersion = 3
    pyLibs = "Python37"
else:
    pVersion = 2
    pyLibs = "Python27"

prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
prismLibs = os.getenv("PRISM_LIBS")

if not prismLibs:
    prismLibs = prismRoot

if not os.path.exists(os.path.join(prismLibs, "PythonLibs")):
    raise Exception("Prism: Couldn't find libraries. Set \"PRISM_LIBS\" to fix this.")

scriptPath = os.path.join(prismRoot, "Scripts")
if scriptPath not in sys.path:
    sys.path.append(scriptPath)

pyLibPath = os.path.join(prismLibs, "PythonLibs", pyLibs)
cpLibs = os.path.join(prismLibs, "PythonLibs", "CrossPlatform")

if cpLibs not in sys.path:
    sys.path.append(cpLibs)

if pyLibPath not in sys.path:
    sys.path.append(pyLibPath)

if platform.system() == "Windows":
    sys.path.insert(0, os.path.join(pyLibPath, "win32"))
    sys.path.insert(0, os.path.join(pyLibPath, "win32", "lib"))
    os.environ['PATH'] = os.path.join(pyLibPath, "pywin32_system32") + os.pathsep + os.environ['PATH']

guiPath = os.path.join(prismRoot, "Scripts", "UserInterfacesPrism")
if guiPath not in sys.path:
    sys.path.append(guiPath)

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    try:
        if "standalone" in sys.argv:
            raise

        from PySide.QtCore import *
        from PySide.QtGui import *
    except:
        sys.path.insert(0, os.path.join(prismLibs, "PythonLibs", pyLibs, "PySide"))
        try:
            from PySide2.QtCore import *
            from PySide2.QtGui import *
            from PySide2.QtWidgets import *
        except:
            from PySide.QtCore import *
            from PySide.QtGui import *

try:
    import EnterText
except:
    modPath = imp.find_module("EnterText")[1]
    if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
        os.remove(modPath)
    import EnterText

from PrismUtils.Decorators import err_catcher
import PrismUtils
from PrismUtils import (
    Callbacks,
    ConfigManager,
    Integration,
    MediaManager,
    MediaProducts,
    PathManager,
    PluginManager,
    Products,
    ProjectEntities,
    Projects,
    SanityChecks,
    Users,
)


logger = logging.getLogger(__name__)


# Timer, which controls the autosave popup, when the autosave in the DCC is diabled
class asTimer(QObject):
    finished = Signal()

    def __init__(self, thread):
        QObject.__init__(self)
        self.thread = thread
        self.active = True

    def run(self):
        try:
            # The time interval after which the popup shows up (in minutes)
            autosaveMins = 15

            t = threading.Timer(autosaveMins * 60, self.stopThread)
            t.start()

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            erStr = "ERROR - asTimer run:\n%s" % traceback.format_exc()
            logger.warning(erStr)

    def stopThread(self):
        if self.active:
            self.finished.emit()


class TimeMeasure(object):
    def __enter__(self):
        self.startTime = datetime.now()
        logger.info("starttime: %s" % self.startTime.strftime('%Y-%m-%d %H:%M:%S'))

    def __exit__(self, type, value, traceback):
        endTime = datetime.now()
        logger.info("endtime: %s" % endTime.strftime('%Y-%m-%d %H:%M:%S'))
        logger.info("duration: %s" % (endTime-self.startTime))


# Prism core class, which holds various functions
class PrismCore:
    def __init__(self, app="Standalone", prismArgs=[]):
        self.prismIni = ""

        try:
            # set some general variables
            self.version = "v1.3.0.64"
            self.requiredLibraries = "v1.3.0.0"
            self.core = self

            startTime = datetime.now()

            self.prismRoot = prismRoot.replace("\\", "/")
            self.prismLibs = prismLibs.replace("\\", "/")

            if platform.system() == "Windows":
                self.userini = os.path.join(
                    os.environ["userprofile"], "Documents", "Prism", "Prism.yml"
                )
            elif platform.system() == "Linux":
                self.userini = os.path.join(os.environ["HOME"], "Prism", "Prism.yml")
            elif platform.system() == "Darwin":
                self.userini = os.path.join(
                    os.environ["HOME"], "Library", "Preferences", "Prism", "Prism.yml"
                )

            self.pluginPathApp = os.path.abspath(
                os.path.join(__file__, os.pardir, os.pardir, "Plugins", "Apps")
            )
            self.pluginPathCustom = os.path.abspath(
                os.path.join(__file__, os.pardir, os.pardir, "Plugins", "Custom")
            )
            self.pluginPathPrjMng = os.path.abspath(
                os.path.join(
                    __file__, os.pardir, os.pardir, "Plugins", "ProjectManagers"
                )
            )
            self.pluginPathRFMng = os.path.abspath(
                os.path.join(
                    __file__, os.pardir, os.pardir, "Plugins", "RenderfarmManagers"
                )
            )
            self.pluginDirs = [
                self.pluginPathApp,
                self.pluginPathCustom,
                self.pluginPathPrjMng,
                self.pluginPathRFMng,
            ]
            prjScriptPath = os.path.abspath(
                os.path.join(__file__, os.pardir, "ProjectScripts")
            )
            for i in self.pluginDirs:
                sys.path.append(i)
            sys.path.append(prjScriptPath)

            self.prismArgs = prismArgs
            if "silent" in sys.argv:
                self.prismArgs.append("silent")

            self.uiAvailable = False if "noUI" in self.prismArgs else True

            self.stateData = []
            self.prjHDAs = []
            self.uiScaleFactor = 1

            self.smCallbacksRegistered = False
            self.sceneOpenChecksEnabled = True
            self.parentWindows = True
            self.filenameSeparator = "_"
            self.sequenceSeparator = "-"
            self.separateOutputVersionStack = True
            self.forceFramerange = False
            self.catchTypeErrors = False
            self.versionPadding = 4
            self.framePadding = 4
            self.versionFormatVan = "v#"
            self.debugMode = False
            self.useLocalFiles = False
            self.pb = None
            self.sm = None
            self.dv = None
            self.ps = None
            self.status = "starting"
            self.missingModules = []
            self.restartRequired = False

            # delete old paths from the path variable
            for val in sys.path:
                if "00_Pipeline" in val:
                    sys.path.remove(val)

            # if no user ini exists, it will be created with default values
            self.configs = ConfigManager.ConfigManager(self)
            self.users = Users.Users(self)
            if not os.path.exists(self.userini):
                self.configs.createUserPrefs()

            logging.basicConfig()
            self.debugMode = self.getConfig("globals", "debug_mode")
            self.updateLogging()
            logger.debug("Initializing Prism " + self.version)

            self.useOnTop = self.getConfig("globals", "use_always_on_top")
            if self.useOnTop is None:
                self.useOnTop = True

            if sys.argv and sys.argv[-1] in ["setupStartMenu", "refreshIntegrations"]:
                self.prismArgs.pop(self.prismArgs.index("loadProject"))

            self.callbacks = Callbacks.Callbacks(self)
            self.projects = Projects.Projects(self)
            self.plugins = PluginManager.PluginManager(self)
            self.paths = PathManager.PathManager(self)
            self.integration = Integration.Ingegration(self)
            self.entities = ProjectEntities.ProjectEntities(self)
            self.mediaProducts = MediaProducts.MediaProducts(self)
            self.products = Products.Products(self)
            self.media = MediaManager.MediaManager(self)
            self.sanities = SanityChecks.SanityChecks(self)

            self.getUIscale()
            self.initializePlugins(app)

            if sys.argv and sys.argv[-1] == "setupStartMenu":
                self.setupStartMenu()
                sys.exit()
            elif sys.argv and sys.argv[-1] == "refreshIntegrations":
                self.integration.refreshAllIntegrations()
                sys.exit()

            endTime = datetime.now()
            logger.debug("startup duration: %s" % (endTime-startTime))

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
    def getPlugin(self, pluginName):
        return self.plugins.getPlugin(pluginName=pluginName)

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
        if self.appPlugin.hasQtParent:
            self.elapsed += 1
            if self.elapsed > self.maxwait and hasattr(self, "timer"):
                self.timer.stop()

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
            and self.getConfig("globals", "showonstartup") is not False
            and self.uiAvailable
        ):
            self.projectBrowser()

        if self.getCurrentFileName() != "":
            self.sceneOpen()

        if self.uiAvailable:
            self.updater.startup()

        self.callback(name="postInitialize")
        self.status = "loaded"

    @err_catcher(name=__name__)
    def startasThread(self, quit=False):
        if hasattr(self, "asThread") and self.asThread.isRunning():
            self.asObject.active = False
            self.asThread.quit()
            if hasattr(self, "autosave_msg") and self.autosave_msg.isVisible():
                self.autosave_msg.blockSignals(True)
                self.autosave_msg.done(2)
                self.autosave_msg.blockSignals(False)

        if quit:
            return

        autoSave = self.getConfig("globals", "autosave")
        if autoSave is None or not autoSave:
            return

        self.asThread = QThread()
        self.asObject = asTimer(self.asThread)
        self.asObject.moveToThread(self.asThread)
        self.asThread.started.connect(self.asObject.run)
        self.asObject.finished.connect(self.checkAutoSave)
        self.asThread.start()

        logger.debug("started autosave thread")

    @err_catcher(name=__name__)
    def checkAutoSave(self):
        if self.appPlugin.autosaveEnabled(self):
            return

        self.autosave_msg = QMessageBox()
        self.autosave_msg.setWindowTitle("Autosave")
        self.autosave_msg.setText("Autosave is disabled. Would you like to save now?")
        self.autosave_msg.addButton("Save", QMessageBox.YesRole)
        self.autosave_msg.addButton("Save new version", QMessageBox.YesRole)
        b_no = self.autosave_msg.addButton("No", QMessageBox.YesRole)
        self.autosave_msg.addButton(
            "No, don't ask again in this session", QMessageBox.YesRole
        )
        self.autosave_msg.setDefaultButton(b_no)

        self.parentWindow(self.autosave_msg)
        self.autosave_msg.finished.connect(self.autoSaveDone)
        self.autosave_msg.setModal(False)
        self.autosave_msg.show()

    @err_catcher(name=__name__)
    def autoSaveDone(self, action=2):
        saved = False
        if action == 0:
            saved = self.saveScene(prismReq=False)
        elif action == 1:
            saved = self.saveScene()
        elif action == 3:
            self.startasThread(quit=True)
            return

        if saved:
            return

        self.startasThread()

    @err_catcher(name=__name__)
    def setDebugMode(self, enabled):
        self.debugMode = enabled
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

        version1 = str(version1).split(".")
        version1 = [int(str(x)) for x in version1]

        version2 = str(version2).split(".")
        version2 = [int(str(x)) for x in version2]

        if (
            version1[0] < version2[0]
            or (version1[0] == version2[0] and version1[1] < version2[1])
            or (
                version1[0] == version2[0]
                and version1[1] == version2[1]
                and version1[2] < version2[2]
            )
            or (
                version1[0] == version2[0]
                and version1[1] == version2[1]
                and version1[2] == version2[2]
                and version1[3] < version2[3]
            )
        ):
            return "lower"
        else:
            return "higher"

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
                msg = "Could evaluate command: %s\n - %s" % (cmdText, traceback.format_exc()),
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
        else:
            self.popup("Unknown command: %s" % (command))

    @err_catcher(name=__name__)
    def createCmd(self, cmd):
        if not os.path.exists(self.prismIni):
            return

        cmdDir = os.path.join(os.path.dirname(self.prismIni), "Commands")
        if not os.path.exists(cmdDir):
            try:
                os.makedirs(cmdDir)
            except:
                return

        for i in os.listdir(cmdDir):
            if i == self.username:
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
        try:
            import SetPath
        except:
            modPath = imp.find_module("SetPath")[1]
            if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
                os.remove(modPath)
            import SetPath

        self.pathWin = SetPath.SetPath(core=self)
        self.pathWin.setModal(True)
        self.parentWindow(self.pathWin)
        result = self.pathWin.exec_()
        self.localProjectPath = ""
        if result == 1:
            setPathResult = self.setLocalPath(self.pathWin.e_path.text())
        else:
            return False

        if not setPathResult and result == 1:
            self.popup("Please enter a valid path to continue.")
            self.getLocalPath()

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
    def getUIscale(self):
        sFactor = 1
        highdpi = self.getConfig("globals", "highdpi")
        if highdpi:
            if "PySide2.QtCore" in sys.modules:
                qtVers = sys.modules["PySide2.QtCore"].__version_info__
            elif "PySide.QtCore" in sys.modules:
                qtVers = sys.modules["PySide.QtCore"].__version_info__

            if qtVers[0] >= 5 and qtVers[1] >= 6:
                screen_resolution = QApplication.desktop().screenGeometry()
                screenWidth, screenHeight = (
                    screen_resolution.width(),
                    screen_resolution.height(),
                )
                wFactor = screenWidth / 960.0
                hFactor = screenHeight / 540.0
                if abs(wFactor - 1) < abs(hFactor - 1):
                    sFactor = wFactor
                else:
                    sFactor = hFactor

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

        if not self.appPlugin.hasQtParent:
            if self.appPlugin.pluginName != "Standalone" and self.useOnTop:
                win.setWindowFlags(win.windowFlags() ^ Qt.WindowStaysOnTopHint)

        if not self.parentWindows or not self.uiAvailable:
            return

        parent = parent or self.messageParent
        win.setParent(parent, Qt.Window)

        if platform.system() == "Darwin" and self.useOnTop:
            win.setWindowFlags(win.windowFlags() ^ Qt.WindowStaysOnTopHint)

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
                prVersion = "Project:&nbsp;&nbsp;&nbsp;&nbsp;%s&nbsp;&nbsp;&nbsp;(%s)" % (prjVersion, self.projectName)

        astr = """Prism:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;%s<br>
%s<br>
<br>
Copyright (C) 2016-2020 Richard Frangenberg<br>
License: GNU GPL-3.0-or-later<br>
<br>
<a href='mailto:contact@prism-pipeline.com' style="color: rgb(150,200,250)">contact@prism-pipeline.com</a><br>
<br>
<a href='https://prism-pipeline.com/' style="color: rgb(150,200,250)">www.prism-pipeline.com</a>""" % (self.version, prVersion)

        return astr

    @err_catcher(name=__name__)
    def showAbout(self):
        astr = self.getAboutString()
        self.popup(astr, title="About", severity="info")

    @err_catcher(name=__name__)
    def sendFeedback(self):
        fbDlg = EnterText.EnterText()
        fbDlg.setModal(True)
        self.parentWindow(fbDlg)
        fbDlg.setWindowTitle("Send Message")
        fbDlg.l_info.setText(
            "Message for the developer:\n"
        )
        fbDlg.te_text.setMinimumHeight(200*self.uiScaleFactor)
        fbDlg.l_description = QLabel("Please provide also contact information (e.g. e-mail) for further discussions and to receive answers to your questions.")
        fbDlg.layout().insertWidget(fbDlg.layout().count()-1, fbDlg.l_description)
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

        fbDlg.layout().insertWidget(fbDlg.layout().count()-1, fbDlg.l_screenGrab)
        fbDlg.layout().insertLayout(fbDlg.layout().count()-1, fbDlg.lo_screenGrab)
        fbDlg.layout().insertItem(fbDlg.layout().count()-1, fbDlg.sp_main)

        fbDlg.b_addScreenGrab.clicked.connect(lambda: self.attachScreenGrab(fbDlg))
        fbDlg.b_removeScreenGrab.clicked.connect(lambda: self.removeScreenGrab(fbDlg))
        fbDlg.b_removeScreenGrab.setVisible(False)
        fbDlg.origSize = fbDlg.size()

        result = fbDlg.exec_()

        if result == 1:
            pm = getattr(fbDlg, "screenGrab", None)
            if pm:
                attachment = tempfile.NamedTemporaryFile(suffix=".jpg").name
                self.media.savePixmap(pm, attachment)
            else:
                attachment = None

            self.sendEmail(fbDlg.te_text.toPlainText(), subject="Prism feedback", attachment=attachment)
            try:
                os.remove(attachment)
            except Exception:
                pass

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
            newPos = dlg.pos()-QPoint(0, pmscaled.height()*0.5)
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
            url = "https://prism-pipeline.readthedocs.io/en/latest/"
        elif location == "downloads":
            url = "https://prism-pipeline.com/downloads/"
        else:
            url = location

        import webbrowser

        webbrowser.open(url)

    @err_catcher(name=__name__)
    def getStateManager(self):
        sm = getattr(self, "sm", None)
        if not sm:
            sm = self.stateManager(openUi=False)

        return sm

    @err_catcher(name=__name__)
    def stateManager(self, stateDataPath=None, restart=False, openUi=True, reload_module=False):
        if self.appPlugin.appType != "3d":
            return False

        if not self.projects.ensureProject(openUi="stateManager"):
            return False

        if not self.users.ensureUser():
            return False

        if not self.sanities.runChecks("onOpenStateManager")["passed"]:
            return False

        if not getattr(self, "sm", None) or self.debugMode or reload_module:
            self.closeSM()

            if self.uiAvailable:
                try:
                    del sys.modules["StateManager"]
                except:
                    pass

            try:
                import StateManager
            except:
                try:
                    modPath = imp.find_module("StateManager")[1]
                    if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
                        os.remove(modPath)

                    import StateManager
                except Exception as e:
                    msgString = "Could not load the StateManager:\n\n%s" % str(e)
                    self.popup(msgString)
                    return

            self.sm = StateManager.StateManager(
                core=self, stateDataPath=stateDataPath
            )

        if self.uiAvailable and openUi:
            self.sm.show()
            self.sm.collapseFolders()
            self.sm.activateWindow()
            self.sm.raise_()

        self.sm.saveStatesToScene()
        return self.sm

    @err_catcher(name=__name__)
    def closeSM(self, restart=False):
        if getattr(self, "sm", None):
            self.sm.saveEnabled = False
            wasOpen = self.isStateManagerOpen()
            if wasOpen:
                self.sm.close()

            if restart:
                self.stateManager(openUi=wasOpen, reload_module=True)

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
            if self.uiAvailable:
                try:
                    del sys.modules["ProjectBrowser"]
                except:
                    pass

            try:
                import ProjectBrowser
            except:
                try:
                    modPath = imp.find_module("ProjectBrowser")[1]
                    if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
                        os.remove(modPath)

                    import ProjectBrowser
                except Exception as e:
                    msgString = "Could not load the ProjectBrowser:\n\n%s" % str(e)
                    self.popup(msgString)
                    return False

            self.pb = ProjectBrowser.ProjectBrowser(core=self)
        else:
            self.pb.refreshUI()

        if openUi:
            self.pb.show()
            self.pb.checkVisibleTabs()

        return self.pb

    @err_catcher(name=__name__)
    def dependencyViewer(self, depRoot="", modal=False):
        if getattr(self, "dv", None) and self.dv.isVisible():
            self.dv.close()

        if not getattr(self, "dv", None) or self.debugMode:
            try:
                del sys.modules["DependencyViewer"]
            except:
                pass

            try:
                import DependencyViewer
            except:
                try:
                    modPath = imp.find_module("DependencyViewer")[1]
                    if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
                        os.remove(modPath)

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
    def prismSettings(self, tab=0):
        if getattr(self, "ps", None) and self.ps.isVisible():
            self.ps.close()

        if not getattr(self, "ps", None) or self.debugMode:
            try:
                del sys.modules["PrismSettings"]
            except:
                pass

            try:
                import PrismSettings
            except:
                modPath = imp.find_module("PrismSettings")[1]
                if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
                    os.remove(modPath)
                import PrismSettings

            self.ps = PrismSettings.PrismSettings(core=self)

        self.ps.show()
        self.ps.tw_settings.setCurrentIndex(tab)

        return self.ps

    @property
    def updater(self):
        if not getattr(self, "_updater", None):
            from PrismUtils import Updater
            self._updater = Updater.Updater(self)

        return self._updater

    @err_catcher(name=__name__)
    def openInstaller(self, uninstall=False):
        if getattr(self, "pinst", None) and self.pinst.isVisible():
            self.pinst.close()

        try:
            del sys.modules["PrismInstaller"]
        except:
            pass

        try:
            import PrismInstaller
        except:
            modPath = imp.find_module("PrismInstaller")[1]
            if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
                os.remove(modPath)
            import PrismInstaller

        self.pinst = PrismInstaller.PrismInstaller(core=self, uninstall=uninstall)
        if uninstall:
            sys.exit()
        else:
            self.pinst.show()

    @err_catcher(name=__name__)
    def startTray(self):
        if getattr(self, "PrismTray", None) or self.appPlugin.pluginName != "Standalone":
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
    def getConfig(self, cat=None, param=None, configPath=None, config=None, dft=None, location=None):
        return self.configs.getConfig(cat=cat, param=param, configPath=configPath, config=config, dft=dft, location=location)

    @err_catcher(name=__name__)
    def setConfig(
        self, cat=None, param=None, val=None, data=None, configPath=None, delete=False, config=None, location=None
    ):
        return self.configs.setConfig(cat=cat, param=param, val=val, data=data, configPath=configPath, delete=delete, config=config, location=location)

    @err_catcher(name=__name__)
    def readYaml(self, path=None, data=None, stream=None):
        return self.configs.readYaml(path=path, data=data, stream=stream,)

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

        return rframes

    @err_catcher(name=__name__)
    def validateLineEdit(self, widget, allowChars=None, denyChars=None):
        if not hasattr(widget, "text"):
            return

        origText = widget.text()
        validText = self.validateStr(origText, allowChars=allowChars, denyChars=denyChars)

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
            self.filenameSeparator,
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

        if len(self.filenameSeparator) > 1:
            validText = validText.replace(self.filenameSeparator, fallbackChar)

        return validText

    @err_catcher(name=__name__)
    def isStr(self, data):
        if pVersion == 3:
            return isinstance(data, str)
        else:
            return isinstance(data, basestring)

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

        validName = False
        if validateFilename:
            fileNameData = self.getScenefileData(filepath)
            validName = fileNameData["entity"] != "invalid"

        if (
            self.fixPath(self.scenePath) in filepath
            or (
                self.useLocalFiles
                and self.fixPath(self.core.getScenePath(location="local"))
                in filepath
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

        for root, folders, files in os.walk(pathDir):
            siblings = [os.path.join(root, f) for f in files]

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
    def getEntityBasePath(self, *args, **kwargs):
        return self.paths.getEntityBasePath(*args, **kwargs)

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
    def getHighestTaskVersion(self, *args, **kwargs):
        return self.entities.getHighestTaskVersion(*args, **kwargs)

    @err_catcher(name=__name__)
    def getLatestCompositingVersion(self, *args, **kwargs):
        return self.entities.getLatestCompositingVersion(*args, **kwargs)

    @err_catcher(name=__name__)
    def getTaskNames(self, *args, **kwargs):
        return self.entities.getTaskNames(*args, **kwargs)

    @err_catcher(name=__name__)
    def resolve(self, uri, uriType="exportProduct"):
        from PrismUtils import Resolver

        if pVersion == 2:
            reload(Resolver)
        else:
            import importlib

            importlib.reload(Resolver)

        resolver = Resolver.Resolver(self)
        return resolver.resolvePath(uri, uriType)

    @err_catcher(name=__name__)
    def getScenePath(self, location="global"):
        if not getattr(self, "projectPath", None):
            return ""

        sceneName = None

        if not sceneName:
            sceneName = self.getConfig("paths", "scenes", configPath=self.prismIni)
            if not sceneName:
                self.core.popup("Required setting \"paths - scenes\" is missing in the project config.\n\nSet this setting to the scenefoldername in this config to solve this issue:\n\n%s" % self.prismIni)
                return ""

        if location == "global":
            prjPath = self.projectPath
        elif location == "local":
            prjPath = self.localProjectPath
        else:
            prjPath = self.paths.getExportProductBasePaths().get(location, "")
        scenePath = os.path.normpath(os.path.join(prjPath, sceneName))

        return scenePath

    @property
    def scenePath(self):
        if not getattr(self, "_scenePath", None):
            self._scenePath = self.getScenePath()

        return self._scenePath

    @err_catcher(name=__name__)
    def getAssetPath(self, location="global"):
        path = ""
        sceneFolder = self.getScenePath(location=location)
        if sceneFolder:
            path = os.path.join(sceneFolder, "Assets")
            path = os.path.normpath(path)

        return path

    @property
    def assetPath(self):
        if not getattr(self, "_assetPath", None):
            self._assetPath = self.getAssetPath()

        return self._assetPath

    @err_catcher(name=__name__)
    def getShotPath(self, location="global"):
        path = ""
        sceneFolder = self.getScenePath(location=location)
        if sceneFolder:
            path = os.path.join(sceneFolder, "Shots")
            path = os.path.normpath(path)

        return path

    @property
    def shotPath(self):
        if not getattr(self, "_shotPath", None):
            self._shotPath = self.getShotPath()

        return self._shotPath

    @err_catcher(name=__name__)
    def convertPath(self, path, target="global"):
        path = os.path.normpath(path)
        if self.useLocalFiles:
            if target == "global":
                scenePath = self.getScenePath("local")
                if path.startswith(scenePath):
                    path = path.replace(
                        self.core.localProjectPath, self.core.projectPath
                    )
            elif target == "local":
                scenePath = self.getScenePath("global")
                if path.startswith(scenePath):
                    path = path.replace(
                        self.core.projectPath, self.core.localProjectPath
                    )

        return path

    @err_catcher(name=__name__)
    def getTexturePath(self, location="global"):
        path = ""
        assetFolder = self.getScenePath(location=location)
        if assetFolder:
            path = os.path.join(assetFolder, "Textures")
            path = os.path.normpath(path)

        return path

    @property
    def texturePath(self):
        if not getattr(self, "_texturePath", None):
            self._texturePath = self.getTexturePath()

        return self._texturePath

    @err_catcher(name=__name__)
    def saveScene(
        self,
        comment="",
        publish=False,
        versionUp=True,
        prismReq=True,
        filepath="",
        details={},
        preview=None,
        location="local",
    ):
        if filepath == "":
            curfile = self.getCurrentFileName()
            filepath = curfile.replace("\\", "/")
        else:
            versionUp = False

        if prismReq:
            if not self.projects.ensureProject():
                return False

            if not self.users.ensureUser():
                return False

            if not self.fileInPipeline(filepath, validateFilename=False):
                title = "Could not save the file"
                msg = "The current scenefile is not inside the pipeline.\nUse the Project Browser to create a file in the pipeline."
                self.popup(msg, title=title)
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
                dstname = os.path.dirname(filepath)

                if fnameData["entity"] == "asset":
                    fVersion = self.getHighestVersion(dstname, "asset")
                    filepath = self.generateScenePath(
                        entity="asset",
                        entityName=fnameData["entityName"],
                        step=fnameData["step"],
                        category=fnameData["category"],
                        comment=comment,
                        # version=fVersion,
                        basePath=dstname,
                        extension=self.appPlugin.getSceneExtension(self),
                    )

                elif fnameData["entity"] == "shot":
                    fVersion = self.getHighestVersion(dstname, "shot")
                    filepath = self.generateScenePath(
                        entity="shot",
                        entityName=fnameData["entityName"],
                        step=fnameData["step"],
                        category=fnameData["category"],
                        comment=comment,
                        # version=fVersion,
                        basePath=dstname,
                        extension=self.appPlugin.getSceneExtension(self),
                    )

        filepath = filepath.replace("\\", "/")
        outLength = len(filepath)
        if platform.system() == "Windows" and outLength > 255:
            msg = "The filepath is longer than 255 characters (%s), which is not supported on Windows." % outLength
            self.popup(msg)
            return False

        self.callback(
            name="preSaveScene",
            types=["custom"],
            args=[self, filepath, versionUp, comment, publish, details],
        )

        result = self.appPlugin.saveScene(self, filepath, details)
        if result is False:
            return False

        if prismReq:
            self.saveSceneInfo(filepath, details, preview=preview)

        self.callback(
            name="postSaveScene",
            types=["curApp", "custom"],
            args=[self, filepath, versionUp, comment, publish, details],
        )

        if not prismReq:
            return filepath

        if (
            not os.path.exists(filepath)
            and os.path.splitext(self.fixPath(self.getCurrentFileName()))[0]
            != os.path.splitext(self.fixPath(filepath))[0]
        ):
            return False

        self.addToRecent(filepath)

        if publish:
            pubFile = filepath
            if self.useLocalFiles and location != "global":
                pubFile = self.fixPath(filepath).replace(
                    self.localProjectPath, self.projectPath
                )
                self.copySceneFile(filepath, pubFile)

            fBase = os.path.splitext(os.path.basename(pubFile))[0]

            infoData = {"filename": os.path.basename(pubFile)}
            self.saveVersionInfo(
                location=os.path.dirname(pubFile),
                version=fVersion,
                fps=True,
                filenameBase=fBase,
                data=infoData,
            )

        if getattr(self, "sm", None):
            self.sm.scenename = self.getCurrentFileName()

        try:
            self.pb.refreshCurrent()
        except:
            pass

        return filepath

    @err_catcher(name=__name__)
    def getVersioninfoPath(self, scenepath):
        ext = self.configs.preferredExtension
        return os.path.splitext(scenepath)[0] + "versioninfo" + ext

    @err_catcher(name=__name__)
    def getScenePreviewPath(self, scenepath):
        return os.path.splitext(scenepath)[0] + "preview.jpg"

    @err_catcher(name=__name__)
    def saveSceneInfo(self, filepath, details=None, preview=None):
        details = details or {}
        if "username" not in details:
            details["username"] = self.username

        doDeps = self.getConfig("globals", "track_dependencies", config="project")
        if doDeps == "always":
            deps = self.entities.getCurrentDependencies()
            details["information"] = {}
            details["information"]["Dependencies"] = deps["dependencies"]
            details["information"]["External files"] = deps["externalFiles"]

        sData = self.getScenefileData(filepath)
        sData.update(details)

        infoPath = self.getVersioninfoPath(filepath)
        self.setConfig(configPath=infoPath, data=sData)

        if preview:
            prvPath = self.getScenePreviewPath(filepath)
            self.media.savePixmap(preview, prvPath)

    @err_catcher(name=__name__)
    def saveWithComment(self):
        if not self.projects.ensureProject():
            return False

        if not self.users.ensureUser():
            return False

        if not self.fileInPipeline():
            msg = "The current file is not inside the Pipeline.\nUse the Project Browser to create a file in the Pipeline."
            self.popup(msg)
            return False

        try:
            del sys.modules["SaveComment"]
        except:
            pass

        try:
            import SaveComment
        except:
            modPath = imp.find_module("SaveComment")[1]
            if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
                os.remove(modPath)
            import SaveComment

        savec = SaveComment.SaveComment(core=self)
        savec.accepted.connect(lambda: self.saveWithCommentAccepted(savec))
        savec.show()

    @err_catcher(name=__name__)
    def saveWithCommentAccepted(self, dlg):
        if dlg.previewDefined:
            prvPMap = dlg.l_preview.pixmap()
        else:
            prvPMap = None

        details = dlg.getDetails() or {}
        self.saveScene(
            comment=dlg.e_comment.text(), details=details, preview=prvPMap
        )

    @err_catcher(name=__name__)
    def getScenefilePaths(self, scenePath):
        paths = [scenePath]
        infoPath = os.path.splitext(scenePath)[0] + "versioninfo.yml"
        prvPath = os.path.splitext(scenePath)[0] + "preview.jpg"

        if os.path.exists(infoPath):
            paths.append(infoPath)
        if os.path.exists(prvPath):
            paths.append(prvPath)

        self.callback("getScenefilePaths")

        ext = os.path.splitext(scenePath)[1]
        if ext in self.appPlugin.sceneFormats:
            paths += getattr(self.appPlugin, "getScenefilePaths", lambda x: [])(scenePath)
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

        infoPath = os.path.splitext(origFile)[0] + "versioninfo.yml"
        prvPath = os.path.splitext(origFile)[0] + "preview.jpg"
        infoPatht = os.path.splitext(targetFile)[0] + "versioninfo.yml"
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
    def getFileModificationDate(self, path):
        cdate = datetime.fromtimestamp(os.path.getmtime(path))
        cdate = cdate.replace(microsecond=0)
        cdate = cdate.strftime("%d.%m.%y,  %H:%M:%S")
        return cdate

    @err_catcher(name=__name__)
    def openFolder(self, path):
        path = self.fixPath(path)

        if platform.system() == "Windows":
            if os.path.isfile(path):
                cmd = ["explorer", "/select,", path]
            else:
                if path != "" and not os.path.exists(path):
                    path = os.path.dirname(path)

                cmd = ["explorer", path]
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
    def copyToClipboard(self, text, fixSlashes=True):
        if fixSlashes:
            text = self.fixPath(text)

        cb = QApplication.clipboard()
        cb.setText(text)

    @err_catcher(name=__name__)
    def copyfile(self, src, dst, thread=None, follow_symlinks=True):
        """Copy data from src to dst.

        If follow_symlinks is not set and src is a symbolic link, a new
        symlink will be created instead of copying the file it points to.

        """
        if shutil._samefile(src, dst):
            raise shutil.SameFileError("{!r} and {!r} are the same file".format(src, dst))

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
            thread.updated.emit("Getting source hash")
            vSourceHash = hashlib.md5(open(src, 'rb').read()).hexdigest()
            vDestinationHash = ""
            while vSourceHash != vDestinationHash:
                with open(src, 'rb') as fsrc:
                    with open(dst, 'wb') as fdst:
                        self.copyfileobj(fsrc, fdst, total=size, thread=thread)

                if thread and thread.canceled:
                    try:
                        os.remove(dst)
                    except:
                        pass
                    return

                thread.updated.emit("Validating copied file")
                vDestinationHash = hashlib.md5(open(dst, 'rb').read()).hexdigest()

        shutil.copymode(src, dst)
        return dst

    @err_catcher(name=__name__)
    def copyfileobj(self, fsrc, fdst, total, thread=None, length=16*1024):
        copied = 0
        prevPrc = -1
        while True:
            if thread and thread.canceled:
                break

            buf = fsrc.read(length)
            if not buf:
                break
            fdst.write(buf)
            copied += len(buf)
            if thread:
                prc = int((copied / total) * 100)
                if prc != prevPrc:
                    prevPrc = prc
                    thread.updated.emit("Progress: %s%%" % prc)

    @err_catcher(name=__name__)
    def copyWithProgress(self, src, dst, follow_symlinks=True):
        if os.path.isdir(dst):
            dst = os.path.join(dst, os.path.basename(src))

        self.copyThread = Worker(self.core)
        self.copyThread.function = lambda: self.copyfile(src, dst, self.copyThread, follow_symlinks=follow_symlinks)

        self.copyMsg = self.core.waitPopup(self.core, "Copying file - please wait..\n\n\n")

        self.copyThread.errored.connect(self.writeErrorLog)
        self.copyThread.updated.connect(self.updateProgressPopup)
        self.copyThread.finished.connect(self.copyMsg.close)

        self.copyMsg.show()
        b_cnl = self.copyMsg.msg.buttons()[0]
        b_cnl.setVisible(True)
        b_cnl.clicked.connect(self.copyThread.cancel)
        self.copyThread.start()

        return dst

    @err_catcher(name=__name__)
    def updateProgressPopup(self, progress):
        text = self.copyMsg.msg.text()
        updatedText = text.rsplit("\n", 2)[0] + "\n" + progress + "\n"
        self.copyMsg.msg.setText(updatedText)

    @err_catcher(name=__name__)
    def createShortcutDeprecated(self, vPath, vTarget="", args="", vWorkingDir="", vIcon=""):
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
            msg = "Could not create shortcut:\n\n%s\n\nProbably you don't have permissions to write to this folder. To fix this install Prism to a different location or change the permissions of this folder." % self.fixPath(vPath)
            self.popup(msg)

    @err_catcher(name=__name__)
    def createShortcut(self, link, target, args=""):
        link = link.replace("/", "\\")
        target = target.replace("/", "\\")

        logger.debug("creating shortcut: %s - target: %s - args: %s" % (link, target, args))
        result = ""

        if platform.system() == "Windows":
            c = (
                "Set oWS = WScript.CreateObject(\"WScript.Shell\")\n"
                "sLinkFile = \"%s\"\n"
                "Set oLink = oWS.CreateShortcut(sLinkFile)\n"
                "oLink.TargetPath = \"%s\"\n"
                "oLink.Arguments = \"%s\"\n"
                "oLink.Save"
            ) % (link, target, args)

            tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".vbs")
            try:
                tmp.write(c)
                tmp.close()
                cmd = "cscript /nologo %s" % tmp.name
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                result = proc.communicate()[0]
            finally:
                tmp.close()
                os.remove(tmp.name)

        else:
            logger.warning("not implemented")

        if os.path.exists(link):
            return True
        else:
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
            subprocess.call(['mklink', "/H", link, target], shell=True)
        else:
            logger.warning("not implemented")

    @property
    @err_catcher(name=__name__)
    def timeMeasure(self):
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

        if hasattr(self, "asThread") and self.asThread.isRunning():
            self.startasThread()

        self.callback(name="sceneSaved")

    @err_catcher(name=__name__)
    def sceneUnload(self, arg=None):  # callback function
        if getattr(self, "sm", None):
            self.sm.close()
            del self.sm

        if hasattr(self, "asThread") and self.asThread.isRunning():
            self.startasThread()

    @err_catcher(name=__name__)
    def sceneOpen(self, arg=None):  # callback function
        if not self.sceneOpenChecksEnabled:
            return

        openSm = getattr(self, "sm", None) and self.sm.isVisible()
        getattr(self.appPlugin, "sceneOpen", lambda x: None)(self)

        # trigger auto imports
        if os.path.exists(self.prismIni):
            self.stateManager(openUi=openSm, reload_module=True)

        self.sanities.checkImportVersions()
        self.sanities.checkFramerange()
        self.sanities.checkFPS()
        self.sanities.checkResolution()

    @err_catcher(name=__name__)
    def getFrameRange(self):
        return self.appPlugin.getFrameRange(self)

    @err_catcher(name=__name__)
    def setFrameRange(self, startFrame, endFrame):
        self.appPlugin.setFrameRange(self, startFrame, endFrame)

    @err_catcher(name=__name__)
    def getFPS(self):
        return float(self.appPlugin.getFPS(self))

    @err_catcher(name=__name__)
    def getResolution(self):
        if hasattr(self.appPlugin, "getResolution"):
            return self.appPlugin.getResolution()

    @err_catcher(name=__name__)
    def getCompositingOut(self, *args, **kwargs):
        return self.paths.getCompositingOut(*args, **kwargs)

    @err_catcher(name=__name__)
    def saveVersionInfo(
        self, location, version, origin=None, fps=None, filenameBase="", data=None
    ):
        data = data or {}
        infoFilePath = os.path.join(location, filenameBase + "versioninfo.yml")
        cData = {
            "information": {
                "Version": version,
                "Created by": self.getConfig("globals", "username"),
                "Creation date": time.strftime("%d.%m.%y %X")
            }
        }

        if origin:
            cData["information"]["Source scene"] = origin

        if fps:
            cData["information"]["FPS"] = self.getFPS()

        depsEnabled = self.getConfig("globals", "track_dependencies", config="project")
        if depsEnabled == "publish":
            deps = self.entities.getCurrentDependencies()
            data["Dependencies"] = deps["dependencies"]
            data["External files"] = deps["externalFiles"]

        for i in data:
            cData["information"][i] = data[i]

        self.setConfig(data=cData, configPath=infoFilePath)

    @err_catcher(name=__name__)
    def getPythonPath(self, executable=None):
        if platform.system() == "Windows":
            if executable:
                pythonPath = os.path.join(self.prismLibs, "Python37", "%s.exe" % executable)
                if os.path.exists(pythonPath):
                    return pythonPath

            pythonPath = os.path.join(self.prismLibs, "Python37", "pythonw.exe")
            if not os.path.exists(pythonPath):
                pythonPath = os.path.join(self.prismLibs, "Python27", "pythonw.exe")
                if not os.path.exists(pythonPath):
                    pythonPath = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
                    if not os.path.exists(pythonPath):
                        pythonPath = sys.executable
                        if "ython" not in os.path.basename(pythonPath):
                            pythonPath = "python"

        else:
            pythonPath = "python"

        return pythonPath

    @err_catcher(name=__name__)
    def sendEmail(self, text, subject="Prism Error", quiet=False, attachment=None):
        if not quiet:
            waitmsg = QMessageBox(
                QMessageBox.NoIcon,
                "Sending message",
                "Sending - please wait..",
                QMessageBox.Cancel,
            )
            self.parentWindow(waitmsg)
            for i in waitmsg.buttons():
                i.setVisible(False)
            waitmsg.show()
            QCoreApplication.processEvents()

        try:
            pythonPath = self.getPythonPath()
            attachment = attachment or ""

            scriptPath = os.path.join(os.path.dirname(PrismUtils.__file__), "SendEmail.py")
            args = [pythonPath, scriptPath]
            args.append(self.prismLibs)
            args.append(pyLibs)
            args.append(subject)
            args.append(text)
            args.append(attachment)

            result = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if not quiet:
                stdOutData, stderrdata = result.communicate()

                if "success" not in str(stdOutData):
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    if pVersion == 2:
                        stdOutData = unicode(stdOutData, errors="ignore")
                    messageStr = "%s\n\n%s" % (stdOutData, text)
                    raise RuntimeError(messageStr)

                self.popup("Sent message successfully", severity="info")

        except Exception as e:
            if quiet:
                logger.debug("Sending message failed: %s" % traceback.format_exc())
            else:
                mailDlg = QDialog()

                mailDlg.setWindowTitle("Sending message failed.")
                l_info = QLabel(
                    "The message couldn't be sent. Maybe there is a problem with the internet connection or the connection was blocked by a firewall.\n\nPlease send an e-mail with the following text to contact@prism-pipeline.com"
                )

                exc_type, exc_obj, exc_tb = sys.exc_info()

                messageStr = "%s\n\n%s" % (
                    traceback.format_exc(),
                    text,
                )
                messageStr = "<pre>%s</pre>" % messageStr.replace("\n", "<br />").replace(
                    "\t", "    "
                )
                l_warnings = QTextEdit(messageStr)
                l_warnings.setReadOnly(True)
                l_warnings.setAlignment(Qt.AlignTop)

                sa_warns = QScrollArea()
                sa_warns.setWidget(l_warnings)
                sa_warns.setWidgetResizable(True)

                bb_warn = QDialogButtonBox()

                bb_warn.addButton("Retry", QDialogButtonBox.AcceptRole)
                bb_warn.addButton("Ok", QDialogButtonBox.RejectRole)

                bb_warn.accepted.connect(mailDlg.accept)
                bb_warn.rejected.connect(mailDlg.reject)

                bLayout = QVBoxLayout()
                bLayout.addWidget(l_info)
                bLayout.addWidget(sa_warns)
                bLayout.addWidget(bb_warn)
                mailDlg.setLayout(bLayout)
                mailDlg.resize(750 * self.uiScaleFactor, 500 * self.uiScaleFactor)

                self.parentWindow(mailDlg)

                action = mailDlg.exec_()

                if action == 1:
                    self.sendEmail(text, subject, quiet, attachment)

        if not quiet and "waitmsg" in locals() and waitmsg.isVisible():
            waitmsg.close()

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
        action = self.popupQuestion(text, title=title, buttons=buttons, icon=QMessageBox.Warning)

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
    def popup(self, text, title=None, severity="warning", notShowAgain=False, parent=None, modal=True):
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

        isGuiThread = QApplication.instance().thread() == QThread.currentThread()

        if "silent" not in self.prismArgs and self.uiAvailable and isGuiThread:
            parent = parent or getattr(self, "messageParent", None)
            msg = QMessageBox(parent)
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

            if modal:
                msg.exec_()
            else:
                msg.show()
            if notShowAgain:
                return {"notShowAgain": msg.chb.isChecked()}
        else:
            msg = "%s - %s" % (title, text)
            if severity == "warning":
                logger.warning(msg)
            elif severity == "info":
                logger.info(msg)
            else:
                logger.error(msg)

    @err_catcher(name=__name__)
    def popupQuestion(self, text, title=None, buttons=None, default=None, icon=None, widget=None, parent=None, escapeButton=None):
        text = str(text)
        title = str(title or "Prism")
        buttons = buttons or ["Yes", "No"]
        icon = QMessageBox.Question if icon is None else icon
        parent or getattr(self, "messageParent", None)

        if "silent" in self.prismArgs or not self.uiAvailable:
            logger.info("%s - %s - %s" % (title, text, default))
            return default

        msg = QMessageBox(
            icon,
            title, text,
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

        msg.exec_()
        result = msg.clickedButton().text()

        return result

    @err_catcher(name=__name__)
    def popupNoButton(self, text, title=None, buttons=None, default=None, icon=None, parent=None):
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
        msg.show()
        QCoreApplication.processEvents()

        return msg

    class waitPopup(object):
        def __init__(self, core, text, title=None, buttons=None, default=None, icon=None, hidden=False, parent=None):
            self.core = core
            self.parent = parent
            self.text = text
            self.title = title
            self.buttons = buttons
            self.default = default
            self.icon = icon
            self.hidden = hidden
            self.msg = None

        def __enter__(self):
            if not self.hidden:
                self.show()

        def __exit__(self, type, value, traceback):
            self.close()

        def show(self):
            self.msg = self.core.popupNoButton(self.text, title=self.title, buttons=self.buttons, default=self.default, icon=self.icon, parent=self.parent)

        def close(self):
            if self.msg and self.msg.isVisible():
                self.msg.close()

    def writeErrorLog(self, text):
        try:
            logger.debug(text)
            raiseError = False
            text += "\n\n"

            if hasattr(self, "messageParent") and self.uiAvailable:
                self.showErrorPopup(text=text)
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

        except:
            msg = "ERROR - writeErrorLog - %s\n\n%s" % (traceback.format_exc(), text)
            logger.warning(msg)

        if raiseError:
            raise RuntimeError(text)

    def showErrorPopup(self, text):
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
If this plugin is an official Prism plugin, please submit this error to the developer.
""" % (self.callbacks.currentCallback["plugin"], self.callbacks.currentCallback["function"])

            result = self.core.popupQuestion(ptext, buttons=["Details", "Close"], icon=QMessageBox.Warning)
            if result == "Details":
                self.showErrorDetailPopup(text)
            elif result == "Close":
                if self.getConfig("globals", "send_error_reports", dft=True):
                    self.sendAutomaticErrorReport(text)

            if "UnicodeDecodeError" in text or "UnicodeEncodeError" in text:
                msg = "The previous error might be caused by the use of special characters (like ö or é). Prism doesn't support this at the moment. Make sure you remove these characters from your filepaths.".decode("utf8")
                self.popup(msg)
        except:
            msg = "ERROR - writeErrorLog - %s\n\n%s" % (traceback.format_exc(), text)
            logger.warning(msg)

    def showErrorDetailPopup(self, text, sendReport=True):
        result = self.popupQuestion(text, buttons=["Report with note", "Close"], icon=QMessageBox.Warning)
        if result == "Report with note":
            self.sendError(text)
        elif sendReport and self.getConfig("globals", "send_error_reports", dft=True):
            self.sendAutomaticErrorReport(text)

    def sendAutomaticErrorReport(self, text):
        if getattr(self, "userini", None):
            userErPath = os.path.join(
                os.path.dirname(self.userini),
                "ErrorLog_%s.txt" % socket.gethostname(),
            )

            if os.path.exists(userErPath):
                with open(userErPath, "r") as erLog:
                    content = erLog.read()

                errStr = "\n".join(text.split("\n")[1:])
                if errStr in content:
                    logger.debug("error already reported")
                    return

        logger.debug("sending automatic error report")
        self.sendEmail("automatic error report.\n\n" + text, quiet=True)

    def sendError(self, errorText):
        msg = QDialog()

        dtext = "The technical error description will be sent anonymously, but you can add additional information to this message if you like.\nFor example how to reproduce the problem or your e-mail for further discussions and to get notified when the problem is fixed.\n"
        ptext = "Additional information (optional):"

        msg.setWindowTitle("Send Error")
        l_description = QLabel(dtext)
        l_info = QLabel(ptext)
        msg.te_info = QPlainTextEdit("""Your email:\n\n\nWhat happened:\n\n\nHow to reproduce:\n\n\nOther notes:\n\n""")
        msg.te_info.setMinimumHeight(300*self.uiScaleFactor)

        b_send = QPushButton("Report anonymously")
        b_ok = QPushButton("Close")

        w_versions = QWidget()
        lay_versions = QHBoxLayout()
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
        msg.resize(800, 450)

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

        msg.layout().insertWidget(msg.layout().count()-1, msg.l_screenGrab)
        msg.layout().insertLayout(msg.layout().count()-1, msg.lo_screenGrab)
        msg.layout().insertItem(msg.layout().count()-1, msg.sp_main)

        size = QSize(msg.size().width(), msg.size().height()*0.5)
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

        self.sendEmail(message, attachment=attachment)
        try:
            os.remove(attachment)
        except Exception:
            pass


class Worker(QThread):
    errored = Signal(object)
    updated = Signal(object)

    def __init__(self, core, function=None):
        super(Worker, self).__init__()
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


def create(prismArgs=None):
    prismArgs = prismArgs or []

    qapp = QApplication.instance()
    if not qapp:
        qapp = QApplication(sys.argv)

    from UserInterfacesPrism import qdarkstyle
    qapp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))
    iconPath = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "UserInterfacesPrism",
        "p_tray.png",
    )
    appIcon = QIcon(iconPath)
    qapp.setWindowIcon(appIcon)
    pc = PrismCore(prismArgs=prismArgs)
    return pc


def show(prismArgs=None):
    create(prismArgs)
    qapp = QApplication.instance()
    qapp.exec_()


if __name__ == "__main__":
    show(prismArgs=["loadProject"])
