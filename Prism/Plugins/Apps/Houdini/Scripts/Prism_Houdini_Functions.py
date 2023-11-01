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
import platform
import glob
import logging
import tempfile
import time
import re

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

import hou

if eval(os.getenv("PRISM_DEBUG", "False")):
    try:
        del sys.modules["Prism_Houdini_Node_ImportFile"]
    except:
        pass

    try:
        del sys.modules["Prism_Houdini_Node_Filecache"]
    except:
        pass

import Prism_Houdini_Node_Filecache
import Prism_Houdini_Node_ImportFile

from PrismUtils.Decorators import err_catcher as err_catcher


logger = logging.getLogger(__name__)


class Prism_Houdini_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        self.eventLoopIterations = 0
        self.eventLoopCallbackAdded = False
        self.guiReady = False
        self.savingScenePath = None
        self.skipPreDeletePopup = False
        self.assetFormats = [
            ".hda",
            ".hdanc",
            ".hdalc",
            ".otl",
            ".otlnc",
            ".otllc",
        ]
        self.whiteListedExternalFiles = [
            {
                "nodeType": "topnet",
                "parmName": "taskgraphfile",
            },
        ]
        self.importHandlerTypes = {}
        for assetFormat in self.assetFormats:
            self.importHandlerTypes[assetFormat] = "Install HDA"

        self.ropLocation = "/out"
        self.filecache = Prism_Houdini_Node_Filecache.Prism_Houdini_Filecache(
            self.plugin
        )
        self.importFile = Prism_Houdini_Node_ImportFile.Prism_Houdini_ImportFile(
            self.plugin
        )
        self.nodeTypeAPIs = [self.filecache, self.importFile]
        self.opmenuActions = [
            {
                "label": "Publish...",
                "validator": lambda x: True,
                "callback": self.onNodePublishTriggered,
            },
            {
                "label": "Capture Thmbnail",
                "validator": lambda x: True,
                "callback": self.onCaptureThumbnailTriggered,
            },
            {
                "label": "Edit Thumbnails",
                "validator": lambda x: True,
                "callback": self.onEditThumbnailsTriggered,
                "checkable": True,
                "checked": lambda kwargs: self.getNetworkPane(node=kwargs["node"].parent()).getPref("backgroundimageediting") == "1"
            }
        ]
        self.registerCallbacks()

    @err_catcher(name=__name__)
    def registerCallbacks(self):
        self.core.registerCallback(
            "sceneSaved", self.updateEnvironment, plugin=self.plugin
        )
        self.core.registerCallback(
            "preSaveScene", self.onPreSaveScene, plugin=self.plugin
        )
        self.core.registerCallback(
            "postSaveScene", self.onPostSaveScene, plugin=self.plugin
        )
        self.core.registerCallback(
            "onProjectSettingsOpen", self.onProjectSettingsOpen, plugin=self.plugin
        )
        self.core.registerCallback(
            "onUserSettingsOpen", self.onUserSettingsOpen, plugin=self.plugin
        )
        self.core.registerCallback(
            "onProjectBrowserStartup", self.onProjectBrowserStartup, plugin=self.plugin
        )
        self.core.registerCallback(
            "preLoadPresetScene", self.preLoadPresetScene, plugin=self.plugin
        )
        self.core.registerCallback(
            "postLoadPresetScene", self.postLoadPresetScene, plugin=self.plugin
        )
        self.core.registerCallback(
            "onStateManagerOpen", self.onStateManagerOpen, plugin=self.plugin
        )
        self.core.registerCallback(
            "onProjectChanged", self.onProjectChanged, plugin=self.plugin
        )
        self.core.registerCallback(
            "expandEnvVar", self.expandEnvVar, plugin=self.plugin
        )
        self.core.registerCallback(
            "updatedEnvironmentVars", self.updatedEnvironmentVars, plugin=self.plugin
        )

    @err_catcher(name=__name__)
    def onEventLoopCallback(self):
        self.eventLoopIterations += 1
        if self.eventLoopIterations == 5:
            self.guiReady = True
            hou.ui.removeEventLoopCallback(self.onEventLoopCallback)

    @err_catcher(name=__name__)
    def startup(self, origin):
        if self.core.uiAvailable:
            if not hou.isUIAvailable():
                return False

            if not hou.qt.mainWindow():
                return False

            if not self.eventLoopCallbackAdded:
                self.eventLoopCallbackAdded = True
                hou.ui.addEventLoopCallback(self.onEventLoopCallback)

            if not self.guiReady:
                return False

            if platform.system() == "Darwin":
                origin.messageParent = QWidget()
                origin.messageParent.setParent(hou.qt.mainWindow(), Qt.Window)
                if self.core.useOnTop:
                    origin.messageParent.setWindowFlags(
                        origin.messageParent.windowFlags() ^ Qt.WindowStaysOnTopHint
                    )
            else:
                origin.messageParent = hou.qt.mainWindow()

            origin.timer.stop()
            origin.startAutosaveTimer()
        else:
            QApplication.addLibraryPath(
                os.path.join(hou.text.expandString("$HFS"), "bin", "Qt_plugins")
            )
            qApp = QApplication.instance()
            if qApp is None:
                qApp = QApplication(sys.argv)
            origin.messageParent = QWidget()

        hou.hipFile.addEventCallback(self.sceneEventCallback)

    @err_catcher(name=__name__)
    def sceneEventCallback(self, eventType):
        if eventType == hou.hipFileEventType.AfterClear:
            self.core.sceneUnload()
        elif eventType == hou.hipFileEventType.AfterLoad:
            if self.core.status != "starting":
                self.core.sceneOpen()
        elif eventType == hou.hipFileEventType.AfterSave:
            self.core.scenefileSaved()

    @err_catcher(name=__name__)
    def autosaveEnabled(self, origin):
        return hou.hscript("autosave")[0] == "autosave on\n"

    @err_catcher(name=__name__)
    def onProjectChanged(self, origin):
        self.loadPrjHDAs(origin)
        self.updateProjectEnvironment()

    @err_catcher(name=__name__)
    def sceneOpen(self, origin):
        self.updateEnvironment()

    @err_catcher(name=__name__)
    def onPreSaveScene(self, origin, filepath, versionUp, comment, publish, details):
        self.savingScenePath = filepath

    @err_catcher(name=__name__)
    def onPostSaveScene(self, origin, filepath, versionUp, comment, publish, details):
        self.savingScenePath = None
        self.updateEnvironment()

    @err_catcher(name=__name__)
    def updateEnvironment(self):
        fn = self.core.getCurrentFileName()
        if self.savingScenePath and os.path.normpath(fn) == os.path.normpath(self.savingScenePath):
            return

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
            envvars[envvar] = hou.hscript("echo $%s" % envvar)

        newenv = {}
        data = self.core.getScenefileData(fn)

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

        if data.get("type") in ["asset", "shot"]:
            newenv["PRISM_DEPARTMENT"] = data.get("department", "")
            newenv["PRISM_TASK"] = data.get("task", "")
            newenv["PRISM_USER"] = getattr(self.core, "user", "")
            version = data.get("version", "")
            try:
                intVersion = int(version[-self.core.versionPadding:])
            except:
                intVersion = version

            newenv["PRISM_FILE_VERSION"] = intVersion
        else:
            newenv["PRISM_DEPARTMENT"] = ""
            newenv["PRISM_TASK"] = ""
            newenv["PRISM_USER"] = ""
            newenv["PRISM_FILE_VERSION"] = ""

        for var in newenv:
            if newenv[var] != envvars[var]:
                hou.hscript("setenv %s=%s" % (var, newenv[var]))
                hou.hscript("varchange %s" % var)

        self.updateProjectEnvironment()

    @err_catcher(name=__name__)
    def updateProjectEnvironment(self):
        job = getattr(self.core, "projectPath", "").replace("\\", "/")
        if job.endswith("/"):
            job = job[:-1]
        hou.hscript("setenv PRISMJOB=" + job)
        hou.hscript("varchange PRISMJOB")

        if self.core.useLocalFiles:
            ljob = self.core.localProjectPath.replace("\\", "/")
            if ljob.endswith("/"):
                ljob = ljob[:-1]
        else:
            ljob = ""

        hou.hscript("setenv PRISMJOBLOCAL=" + ljob)
        hou.hscript("varchange PRISMJOBLOCAL")

    @err_catcher(name=__name__)
    def expandEnvVar(self, var):
        dbslash = False
        if var.startswith("\\\\"):
            dbslash = True
            var = var[2:]

        var = hou.text.expandString(var)
        if dbslash:
            var = "\\\\" + var

        return var

    @err_catcher(name=__name__)
    def updatedEnvironmentVars(self, reason, envVars, beforeRefresh=False):
        doReload = False

        if reason == "refreshProject" and getattr(self, "unloadedOCIO", False):
            doReload = True
        else:
            for envVar in envVars:
                if envVar["key"] == "OCIO" and envVar["value"] != envVar["orig"]:
                    if reason == "unloadProject" and beforeRefresh:
                        self.unloadedOCIO = True
                        continue

                    doReload = True

        if doReload:
            self.unloadedOCIO = False
            hou.Color.reloadOCIO()

    @err_catcher(name=__name__)
    def loadPrjHDAs(self, origin):
        if not hasattr(origin, "projectPath") or not os.path.exists(origin.projectPath):
            return

        self.core.users.ensureUser()
        self.uninstallHDAs(origin.prjHDAs)

        hdaFolders = []

        prjHDAs = self.getProjectHDAFolder()
        if prjHDAs and hasattr(self.core, "user"):
            hdaUFolder = os.path.join(prjHDAs, origin.user)
            hdaFolders += [prjHDAs, hdaUFolder]

        origin.prjHDAs = self.findHDAs(hdaFolders)

        oplib = os.path.join(
            self.core.projects.getPipelineFolder(), "ProjectHDAs.oplib"
        )
        self.installHDAs(origin.prjHDAs, oplib)

    @err_catcher(name=__name__)
    def uninstallHDAs(self, hdaPaths):
        for path in hdaPaths:
            if not os.path.exists(path):
                continue

            defs = hou.hda.definitionsInFile(path)
            if len(defs) > 0 and defs[0].isInstalled():
                hou.hda.uninstallFile(path)

    @err_catcher(name=__name__)
    def installHDAs(self, hdaPaths, oplibPath):
        oplibPath = oplibPath.replace("\\", "/")
        for path in hdaPaths:
            hou.hda.installFile(path, oplibPath)

    @err_catcher(name=__name__)
    def findHDAs(self, paths):
        if self.core.isStr(paths):
            paths = [paths]

        hdas = []

        for path in paths:
            if not os.path.exists(path):
                continue

            for root, folders, files in os.walk(path):
                if os.path.basename(root) == "backup":
                    continue

                for file in files:
                    if os.path.splitext(file)[1] in self.assetFormats:
                        hdaPath = os.path.join(root, file).replace("\\", "/")
                        hdas.append(hdaPath)

        return hdas

    @err_catcher(name=__name__)
    def getProjectHDAFolder(self, filename=None):
        folder = self.core.projects.getResolvedProjectStructurePath("houdini_HDAs")
        if not folder:
            logger.debug("project has no HDA folder")
            return

        if filename:
            filename = filename.replace(":", "_")
            if not os.path.splitext(filename)[1]:
                filename += ".hda"

            folder = os.path.join(folder, filename)

        return folder

    @err_catcher(name=__name__)
    def createHDA(
        self,
        node,
        outputPath="",
        typeName="prism_hda",
        label=None,
        saveToExistingHDA=False,
        version=1,
        blackBox=False,
        allowExternalReferences=False,
        projectHDA=False,
        setDefinitionCurrent=True,
        convertNode=False,
    ):
        namespace = self.core.getConfig(
            "houdini", "assetNamespace", dft="prism", configPath=self.core.prismIni
        )
        if namespace:
            typeName = namespace + "::" + typeName

        if node.canCreateDigitalAsset():
            if projectHDA and not outputPath:
                filename = typeName.split("::", 1)[1]
                outputPath = self.getProjectHDAFolder(filename)
                if os.path.exists(outputPath):
                    msg = (
                        "The HDA file already exists:\n\n%s\n\nDo you want to save a new definition into this file and possibly overwrite an existing definition?"
                        % outputPath
                    )
                    result = self.core.popupQuestion(msg, buttons=["Save", "Cancel"])
                    if result == "Cancel":
                        return False

            if version is not None:
                if version == "increment":
                    version = 1
                typeName += "::" + str(version)

            inputNum = len(node.inputs())

            try:
                hda = node.createDigitalAsset(
                    typeName,
                    hda_file_name=outputPath,
                    description=label,
                    min_num_inputs=inputNum,
                    max_num_inputs=inputNum,
                    ignore_external_references=allowExternalReferences,
                    change_node_type=convertNode,
                )
            except hou.OperationFailed as e:
                msg = e.instanceMessage()
                if msg.startswith("The selected subnet has references to nodes"):
                    msg = (
                        "Canceled HDA creation.\n\n"
                        + msg
                        + '\n\nYou can enable "Allow external references" in the state settings to ignore this warning.'
                    )
                self.core.popup(msg)
                return False

            if blackBox:
                hou.hda.installFile(outputPath, force_use_assets=True)
                defs = hou.hda.definitionsInFile(outputPath)
                definition = [df for df in defs if df.nodeTypeName() == typeName][0]
                self.convertDefinitionToBlackBox(definition)
            else:
                return hda
        else:
            if saveToExistingHDA:
                libFile = node.type().definition().libraryFilePath()
                if version is not None:
                    if version == "increment":
                        highestVersion = self.getHighestHDAVersion(libFile, typeName)
                        version = highestVersion + 1
                    typeName += "::" + str(version)

                self.saveNodeDefinitionToFile(
                    node, libFile, typeName=typeName, label=label, blackBox=blackBox
                )
                if convertNode:
                    node = node.changeNodeType(typeName)

                return node
            else:
                if projectHDA and not outputPath:
                    filename = typeName.split("::", 1)[1]
                    outputPath = self.getProjectHDAFolder(filename)
                    libFile = node.type().definition().libraryFilePath()
                    if version == "increment":
                        highestVersion = self.getHighestHDAVersion(libFile, typeName)
                        version = highestVersion + 1
                else:
                    if version == "increment":
                        version = 1

                if version is not None:
                    typeName += "::" + str(version)

                self.saveNodeDefinitionToFile(
                    node, outputPath, typeName=typeName, label=label, blackBox=blackBox
                )

                if projectHDA:
                    oplib = os.path.join(
                        os.path.dirname(outputPath), "ProjectHDAs.oplib"
                    ).replace("\\", "/")
                    hou.hda.installFile(
                        outputPath, oplib, force_use_assets=setDefinitionCurrent
                    )
                else:
                    hou.hda.installFile(
                        outputPath, force_use_assets=setDefinitionCurrent
                    )

                if convertNode:
                    node.changeNodeType(typeName)

        return True

    @err_catcher(name=__name__)
    def getHighestHDAVersion(self, libraryFilePath, typeName):
        definitions = hou.hda.definitionsInFile(libraryFilePath)
        highestVersion = 0
        for definition in definitions:
            name = definition.nodeTypeName()
            basename = name.rsplit("::", 1)[0]
            basename
            if basename != typeName:
                continue

            v = name.split("::")[-1]
            if sys.version[0] == "2":
                v = unicode(v)

            if not v.isnumeric():
                continue

            if int(v) > highestVersion:
                highestVersion = int(v)

        return highestVersion

    @err_catcher(name=__name__)
    def saveNodeDefinitionToFile(
        self, node, filepath, typeName=None, label=None, blackBox=False
    ):
        tmpPath = filepath + "tmp"
        kwargs = {
            "file_name": tmpPath,
            "template_node": node,
            "create_backup": False,
            "compile_contents": blackBox,
            "black_box": blackBox,
        }

        major, minor, patch = hou.applicationVersion()
        noBackup = major <= 16 and minor <= 5 and patch <= 185
        blackBoxChanged = major > 19 or (major == 19 and minor > 0)

        if noBackup:
            kwargs.pop("create_backup")

        if blackBoxChanged:
            kwargs.pop("compile_contents")
            kwargs["black_box"] = blackBox

        node.type().definition().save(**kwargs)

        defs = hou.hda.definitionsInFile(tmpPath)
        defs[0].copyToHDAFile(filepath, new_name=typeName, new_menu_name=label)
        os.remove(tmpPath)

    @err_catcher(name=__name__)
    def convertDefinitionToBlackBox(self, definition):
        filepath = definition.libraryFilePath()
        kwargs = {
            "file_name": filepath,
            "create_backup": False,
            "compile_contents": True,
            "black_box": True,
        }

        major, minor, patch = hou.applicationVersion()
        noBackup = major <= 16 and minor <= 5 and patch <= 185
        blackBoxChanged = major > 19 or (major == 19 and minor > 0)

        if noBackup:
            kwargs.pop("create_backup")

        if blackBoxChanged:
            kwargs.pop("compile_contents")
            kwargs["black_box"] = True

        definition.save(**kwargs)

    @err_catcher(name=__name__)
    def getHDAOutputpath(
        self,
        node=None,
        task="",
        comment="",
        user=None,
        version="next",
        location="global",
        saveToExistingHDA=False,
        projectHDA=False,
    ):
        fileName = self.core.getCurrentFileName()
        fnameData = self.core.getScenefileData(fileName)

        if node and node.type().definition() and saveToExistingHDA:
            outputPath = node.type().definition().libraryFilePath()
            outputFolder = os.path.dirname(outputPath)
        elif node and projectHDA:
            outputPath = self.getProjectHDAFolder(task)
            if not outputPath:
                msg = "The current project has no HDA folder set up in the Project Settings"
                self.core.popup(msg)
                return

            outputFolder = os.path.dirname(outputPath)
            version = None
        else:
            version = version if version != "next" else None

            if "type" not in fnameData:
                return

            if not task:
                return

            extension = ".hda"
            outputPathData = self.core.products.generateProductPath(
                entity=fnameData,
                task=task,
                extension=extension,
                framePadding="",
                comment=fnameData["comment"],
                version=version,
                location=location,
                returnDetails=True,
            )

            outputPath = outputPathData["path"].replace("\\", "/")
            outputFolder = os.path.dirname(outputPath)
            version = outputPathData["version"]

        result = {
            "outputPath": outputPath.replace("\\", "/"),
            "outputFolder": outputFolder.replace("\\", "/"),
            "version": version,
        }

        return result

    @err_catcher(name=__name__)
    def getCurrentFileName(self, origin, path=True):
        if path:
            path = hou.hipFile.path()
            if os.path.splitext(os.path.basename(path))[0] == "untitled":
                return ""
        else:
            path = hou.hipFile.basename()

        return path

    @err_catcher(name=__name__)
    def getCurrentSceneFiles(self, origin):
        return [self.core.getCurrentFileName()]

    @err_catcher(name=__name__)
    def getSceneExtension(self, origin):
        if str(hou.licenseCategory()) == "licenseCategoryType.Commercial":
            return ".hip"
        elif str(hou.licenseCategory()) == "licenseCategoryType.Indie":
            return ".hiplc"
        else:
            return ".hipnc"

    @err_catcher(name=__name__)
    def saveScene(self, origin, filepath, details=None):
        filepath = filepath.replace("\\", "/")
        return hou.hipFile.save(file_name=filepath, save_to_recent_files=True)

    @err_catcher(name=__name__)
    def getImportPaths(self, origin):
        val = hou.node("/obj").userData("PrismImports")

        if val is None:
            return False

        return val

    @err_catcher(name=__name__)
    def getFrameRange(self, origin):
        startframe = hou.playbar.playbackRange()[0]
        endframe = hou.playbar.playbackRange()[1]

        return [startframe, endframe]

    @err_catcher(name=__name__)
    def getCurrentFrame(self):
        currentFrame = hou.frame()
        return currentFrame

    @err_catcher(name=__name__)
    def setFrameRange(self, origin, startFrame, endFrame, currentFrame=None):
        setGobalFrangeExpr = "tset `(%d-1)/$FPS` `%d/$FPS`" % (int(startFrame), int(endFrame))
        hou.hscript(setGobalFrangeExpr)
        hou.playbar.setPlaybackRange(int(startFrame), int(endFrame))
        currentFrame = currentFrame or int(startFrame)
        hou.setFrame(currentFrame)

    @err_catcher(name=__name__)
    def getFPS(self, origin):
        return hou.fps()

    @err_catcher(name=__name__)
    def setFPS(self, origin, fps):
        frange = self.getFrameRange(origin)
        hou.setFps(fps)
        self.setFrameRange(origin, frange[0], frange[1])

    @err_catcher(name=__name__)
    def getAppVersion(self, origin):
        return hou.applicationVersion()[1:-1]

    @err_catcher(name=__name__)
    def onProjectBrowserStartup(self, origin):
        if platform.system() == "Darwin":
            origin.menubar.setNativeMenuBar(False)
        origin.checkColor = "rgb(185, 134, 32)"
        origin.sceneBrowser.lo_entityDetails.setContentsMargins(9, 18, 9, 9)
        origin.sceneBrowser.setStyleSheet(origin.sceneBrowser.styleSheet() + " QToolButton{ border-width: 0px; background-color: transparent} QToolButton::checked{background-color: rgba(200, 200, 200, 100)}")

        ssheet = hou.qt.styleSheet()
        ssheet = ssheet.replace("QScrollArea", "Qdisabled")
        ssheet = ssheet.replace("QAbstractItemView", "QWidget#sceneItems")
        ssheet = ssheet.replace("QListView", "QWidget#sceneItems")

        origin.sceneBrowser.w_scenefileItems.setObjectName("sceneItems")
        origin.sceneBrowser.w_scenefileItems.setStyleSheet(ssheet)

    @err_catcher(name=__name__)
    def preLoadPresetScene(self, origin, filepath):
        self.curDesktop = hou.ui.curDesktop()

    @err_catcher(name=__name__)
    def postLoadPresetScene(self, origin, filepath):
        if hasattr(self, "curDesktop"):
            self.curDesktop.setAsCurrent()

    @err_catcher(name=__name__)
    def openScene(self, origin, filepath, force=False):
        if (
            not filepath.endswith(".hip")
            and not filepath.endswith(".hipnc")
            and not filepath.endswith(".hiplc")
        ):
            return False

        mods = QApplication.keyboardModifiers()
        if self.core.getConfig("houdini", "openInManual") or mods == Qt.AltModifier:
            hou.setUpdateMode(hou.updateMode.Manual)

        hou.hipFile.load(file_name=filepath)
        return True

    @err_catcher(name=__name__)
    def correctExt(self, origin, lfilepath):
        if str(hou.licenseCategory()) == "licenseCategoryType.Commercial":
            return os.path.splitext(lfilepath)[0] + ".hip"
        elif str(hou.licenseCategory()) == "licenseCategoryType.Indie":
            return os.path.splitext(lfilepath)[0] + ".hiplc"
        else:
            return os.path.splitext(lfilepath)[0] + ".hipnc"

    @err_catcher(name=__name__)
    def onUserSettingsOpen(self, origin):
        if self.core.uiAvailable:
            origin.scrollArea.setStyleSheet(
                hou.qt.styleSheet().replace("QLabel", "QScrollArea")
            )

    @err_catcher(name=__name__)
    def onProjectSettingsOpen(self, origin):
        if self.core.uiAvailable:
            origin.sp_curPfps.setStyleSheet(
                hou.qt.styleSheet().replace("QSpinBox", "QDoubleSpinBox")
            )

    @err_catcher(name=__name__)
    def createProject_startup(self, origin):
        if self.core.uiAvailable:
            origin.scrollArea.setStyleSheet(
                hou.qt.styleSheet().replace("QLabel", "QScrollArea")
            )

    @err_catcher(name=__name__)
    def shotgunPublish_startup(self, origin):
        if self.core.uiAvailable:
            origin.te_description.setStyleSheet(
                hou.qt.styleSheet().replace("QTextEdit", "QPlainTextEdit")
            )

    @err_catcher(name=__name__)
    def fixImportPath(self, path):
        if not path:
            return path

        base, ext = self.splitExtension(path)
        pad = self.core.framePadding
        if len(base) > pad and base[-(pad + 1)] != "v":
            try:
                int(base[-pad:])
                return base[:-pad] + "$F" + str(pad) + ext
            except:
                return path

        return path

    @err_catcher(name=__name__)
    def getUseRelativePath(self):
        return self.core.getConfig(
            "houdini", "useRelativePaths", dft=False, config="project"
        )

    @err_catcher(name=__name__)
    def getPathRelativeToProject(self, path):
        try:
            if path.startswith("$"):
                path = path.replace("\\", "/")
                pathdata = path.split("/", 1)
                path = "$PRISM_JOB/" + os.path.relpath(hou.text.expandString(pathdata[0]) + "/" + pathdata[1], self.core.projectPath)
            else:
                path = "$PRISM_JOB/" + os.path.relpath(path, self.core.projectPath)
        except ValueError as e:
            logger.warning(str(e) + " - path: %s - start: %s" % (path, self.core.projectPath))
        
        return path

    @err_catcher(name=__name__)
    def splitExtension(self, path):
        if path.endswith(".bgeo.sc"):
            return [path[: -len(".bgeo.sc")], ".bgeo.sc"]
        else:
            return os.path.splitext(path)

    @err_catcher(name=__name__)
    def setNodeParm(self, node, parm, val=None, clear=False, severity="warning"):
        try:
            if clear:
                if node.parm(parm).isLocked():
                    node.parm(parm).lock(False)

                node.parm(parm).deleteAllKeyframes()

            if val is not None:
                node.parm(parm).set(val)
        except Exception as e:
            logger.debug(str(e))
            if not node.parm(parm):
                msg = 'parm doesn\'t exist: "%s" on node "%s"' % (parm, node.path())
                if severity == "warning":
                    logger.warning(msg)
                else:
                    logger.debug(msg)

                return False

            curTake = hou.takes.currentTake()
            if (
                curTake.hasParmTuple(node.parm(parm).tuple())
                or curTake.parent() is None
            ):
                msgString = (
                    "Cannot set this parameter. Probably because it is locked:\n\n%s"
                    % node.parm(parm).path()
                )
                msg = QMessageBox(
                    QMessageBox.Warning,
                    "Cannot set Parameter",
                    msgString,
                    QMessageBox.Cancel,
                )
                msg.addButton("Ignore", QMessageBox.YesRole)
                self.core.parentWindow(msg)
                action = msg.exec_()

                if action == 0:
                    return True
                else:
                    return False
            else:
                msgString = (
                    "The parameter is not included in the current take.\nTo continue the parameter should be added to the current take.\n\n%s"
                    % node.parm(parm).path()
                )
                msg = QMessageBox(
                    QMessageBox.Warning,
                    "Locked Parameter",
                    msgString,
                    QMessageBox.Cancel,
                )
                msg.addButton("Add to current take", QMessageBox.YesRole)
                msg.addButton("Ignore", QMessageBox.YesRole)
                self.core.parentWindow(msg)
                action = msg.exec_()

                if action == 0:
                    curTake.addParmTuple(node.parm(parm).tuple())
                    self.setNodeParm(node, parm, val, clear)
                elif action == 1:
                    return True
                else:
                    return False

        return True

    @err_catcher(name=__name__)
    def sm_preDelete(self, origin, item, silent=False):
        if not hasattr(item.ui, "node") or silent:
            return

        try:
            item.ui.node.name()
            nodeExists = True
        except:
            nodeExists = False

        if nodeExists:
            if self.skipPreDeletePopup:
                result = "Yes"
            else:
                msg = "Do you also want to delete the connected node?\n\n%s" % (
                    item.ui.node.path()
                )
                result = self.core.popupQuestion(msg, buttons=["Yes", "Yes to all", "No"], title="Delete State", default="No")

            if result in ["Yes", "Yes to all"]:
                try:
                    if item.ui.className == "ImportFile":
                        nwBox = hou.node("/obj").findNetworkBox("Import")
                        if nwBox is not None:
                            if (
                                len(nwBox.nodes()) == 1
                                and nwBox.nodes()[0] == item.ui.node
                            ):
                                nwBox.destroy()
                    item.ui.node.destroy()
                    if hasattr(item.ui, "node2"):
                        item.ui.node2.destroy()
                except:
                    pass

                if result == "Yes to all":
                    self.skipPreDeletePopup = True
                    origin.stateManager.finishedDeletionCallbacks.append(lambda: setattr(self, "skipPreDeletePopup", False))

        if (
            item.ui.className == "Install HDA"
            and os.path.splitext(item.ui.importPath)[1] == ".hda"
        ):
            fpath = item.ui.importPath.replace("\\", "/")
            defs = hou.hda.definitionsInFile(fpath)
            if len(defs) > 0 and defs[0].isInstalled():
                hou.hda.uninstallFile(fpath)

    @err_catcher(name=__name__)
    def sm_preSaveToScene(self, origin):
        if origin.scenename == self.core.getCurrentFileName():
            return

        origin.saveEnabled = False

        msg = QMessageBox(
            QMessageBox.NoIcon,
            "State Manager",
            "A problem happened with the scene load callbacks.",
        )
        msg.addButton("Save current states to scene", QMessageBox.YesRole)
        msg.addButton("Reload states from scene", QMessageBox.NoRole)
        msg.addButton("Close", QMessageBox.NoRole)

        msg.setParent(self.core.messageParent, Qt.Window)

        action = msg.exec_()

        origin.scenename = self.core.getCurrentFileName()

        if action == 1:
            self.core.closeSM(restart=True)
            return False
        elif action == 2:
            self.core.closeSM()
            return False

        origin.saveEnabled = True

    def fixStyleSheet(self, widget):
        root = os.path.dirname(self.pluginPath).replace("\\", "/")
        ssheet = ""
        ssheet += (
            "QGroupBox::indicator::checked\n{\n    image: url(%s/UserInterfaces/checkbox_on.svg);\n}"
            % root
        )
        ssheet += (
            "QGroupBox::indicator::unchecked\n{\n    image: url(%s/UserInterfaces/checkbox_off.svg);\n}"
            % root
        )
        ssheet += "QGroupBox::indicator { width: 16px; height: 16px;}"
        widget.setStyleSheet(ssheet)

    @err_catcher(name=__name__)
    def getFrameStyleSheet(self, origin):
        if self.core.uiAvailable:
            return hou.qt.styleSheet().replace("QWidget", "QFrame")
        else:
            return ""

    @err_catcher(name=__name__)
    def onOpmenuActionsTriggered(self, kwargs):
        menu = QMenu(self.core.messageParent)
        pos = QCursor.pos()

        for action in self.opmenuActions:
            if not action["validator"](kwargs):
                continue

            mAct = QAction(action["label"], self.core.messageParent)
            if action.get("checkable", False):
                mAct.setCheckable(True)
                mAct.setChecked(action["checked"](kwargs))
                mAct.toggled.connect(lambda x=None, act=action: act["callback"](kwargs))
            else:
                mAct.triggered.connect(lambda x=None, act=action: act["callback"](kwargs))

            menu.addAction(mAct)

        if not menu.isEmpty():
            menu.exec_(pos)

    @err_catcher(name=__name__)
    def removeImage(self, **kwargs):
        import nodegraphutils as utils
        nwPane = self.getNetworkPane(node=kwargs["node"].parent())
        curImgs = nwPane.backgroundImages()
        newImgs = ()
        for img in curImgs:
            if img.relativeToPath() != kwargs["node"].path():
                newImgs = newImgs + (img,)
            else:
                try:
                    os.remove(img.path())
                except:
                    pass

        nwPane.setBackgroundImages(newImgs)
        utils.saveBackgroundImages(nwPane.pwd(), newImgs)
        
    @err_catcher(name=__name__)
    def changeBrightness(self, **kwargs):
        import nodegraphutils as utils
        brightness = 0.3 if kwargs["node"].isBypassed() else 1.0
        nwPane = self.getNetworkPane(node=kwargs["node"].parent())
        curImgs = nwPane.backgroundImages()
        for img in curImgs:
            if img.relativeToPath() == kwargs["node"].path():
                img.setBrightness(brightness)
                
        nwPane.setBackgroundImages(curImgs)
        utils.saveBackgroundImages(nwPane.pwd(), curImgs)

    @err_catcher(name=__name__)
    def onCaptureThumbnailTriggered(self, kwargs):
        from PrismUtils import ScreenShot
        import hou
        import nodegraphutils as utils

        node = kwargs.get("node", None)
        if not node:
            return

        previewImg = ScreenShot.grabScreenArea(self.core)

        if previewImg:
            hip = os.path.dirname(hou.hipFile.path())
            prvPath = hip + '/network_previews/%s_%s.jpg' % (node.name(), int(time.time()))
            relPath = prvPath.replace(hip, "$HIP")
            if not os.path.exists(os.path.dirname(prvPath)):
                os.makedirs(os.path.dirname(prvPath))
                
            previewImg.save(prvPath, "JPG")

            ratio = previewImg.size().width() / float(previewImg.size().height())

            width = 4.0
            height = width/ratio

            if height > width:
                maxBound = width
                width = width/(height/width)
                height = maxBound

            startX = 1.07
            startY = -0.4

            rect = hou.BoundingRect(startX, startY, startX+width, startY-height)
            img = hou.NetworkImage(relPath, rect)
            img.setRelativeToPath(node.path())
            nwPane = getNetworkPane(node=kwargs["node"].parent())
            curImgs = nwPane.backgroundImages()
            newImgs = curImgs + (img,)
            nwPane.setBackgroundImages(newImgs)
            utils.saveBackgroundImages(nwPane.pwd(), newImgs)
            
            node.addEventCallback((hou.nodeEventType.BeingDeleted,), self.removeImage)
            node.addEventCallback((hou.nodeEventType.FlagChanged,), self.changeBrightness)

    @err_catcher(name=__name__)
    def onNodePublishTriggered(self, kwargs):
        sm = self.core.getStateManager()
        if not sm:
            return

        validTypes = []
        for stateType in sm.stateTypes:
            if not hasattr(sm.stateTypes[stateType], "isConnectableNode"):
                continue

            valid = sm.stateTypes[stateType].isConnectableNode(kwargs["node"])
            if valid:
                validTypes.append(stateType)
        
        if not validTypes:
            msg = "This node type cannot be published by any of the available state types."
            self.core.popup(msg)
            return

        if len(validTypes) > 1:
            msg = "Which statetype do you want to use to publish this node?"
            result = self.core.popupQuestion(msg, buttons=validTypes + ["Cancel"])
            if result in validTypes:
                stateType = result
            else:
                return
        else:
            stateType = validTypes[0]

        state = self.getStateFromNode(kwargs, create=False)
        if not state or state.ui.className != stateType:
            state = sm.createState(stateType, node=kwargs["node"])

        dlg = PublishDialog(self, state)
        dlg.show()

    @err_catcher(name=__name__)
    def onEditThumbnailsTriggered(self, kwargs):
        nwPane = self.getNetworkPane(node=kwargs["node"].parent())
        isEditing = nwPane.getPref("backgroundimageediting") == "1"
        if isEditing:
            nwPane.setPref("backgroundimageediting", "0")
        else:
            nwPane.setPref("backgroundimageediting", "1")

    @err_catcher(name=__name__)
    def onStateManagerOpen(self, origin):
        if platform.system() == "Darwin":
            origin.menubar.setNativeMenuBar(False)

        if self.core.uiAvailable:
            origin.enabledCol = QBrush(QColor(204, 204, 204))

        if self.core.uiAvailable:
            origin.scrollArea.setStyleSheet(
                hou.qt.styleSheet().replace("QLabel", "QScrollArea")
            )

        origin.f_import.setStyleSheet("QFrame { border: 0px; }")
        origin.f_export.setStyleSheet("QFrame { border: 0px; }")
        origin.sa_stateSettings.setStyleSheet("QScrollArea { border: 0px; }")

        root = os.path.dirname(self.pluginPath).replace("\\", "/")
        ssheet = ""
        ssheet += (
            "QTreeWidget::indicator::checked\n{\n    image: url(%s/UserInterfaces/checkbox_on.svg);\n}"
            % root
        )
        ssheet += (
            "QTreeWidget::indicator::unchecked\n{\n    image: url(%s/UserInterfaces/checkbox_off.svg);\n}"
            % root
        )
        ssheet += "QTreeWidget::indicator { width: 16px; height: 16px;}"

        origin.tw_export.setStyleSheet(ssheet)

        origin.layout().setContentsMargins(0, 0, 0, 0)

        origin.b_createExport.setStyleSheet("padding-left: 1px;padding-right: 1px;")
        origin.b_createRender.setStyleSheet("padding-left: 1px;padding-right: 1px;")
        origin.b_createPlayblast.setStyleSheet("padding-left: 1px;padding-right: 1px;")
        origin.b_showImportStates.setStyleSheet("padding-left: 1px;padding-right: 1px;")
        origin.b_showExportStates.setStyleSheet("padding-left: 1px;padding-right: 1px;")

        origin.b_createImport.setMinimumWidth(70 * self.core.uiScaleFactor)
        origin.b_createImport.setMaximumWidth(70 * self.core.uiScaleFactor)
        origin.b_createExport.setMinimumWidth(70 * self.core.uiScaleFactor)
        origin.b_createExport.setMaximumWidth(70 * self.core.uiScaleFactor)
        origin.b_createRender.setMinimumWidth(70 * self.core.uiScaleFactor)
        origin.b_createRender.setMaximumWidth(70 * self.core.uiScaleFactor)
        origin.b_createPlayblast.setMinimumWidth(70 * self.core.uiScaleFactor)
        origin.b_createPlayblast.setMaximumWidth(70 * self.core.uiScaleFactor)
        origin.b_showImportStates.setMinimumWidth(30 * self.core.uiScaleFactor)
        origin.b_showImportStates.setMaximumWidth(30 * self.core.uiScaleFactor)
        origin.b_showExportStates.setMinimumWidth(30 * self.core.uiScaleFactor)
        origin.b_showExportStates.setMaximumWidth(30 * self.core.uiScaleFactor)

        usdType = hou.nodeType(hou.sopNodeTypeCategory(), "pixar::usdrop")
        if usdType is not None and ".usd" not in self.plugin.outputFormats:
            self.plugin.outputFormats.insert(-2, ".usd")
        elif usdType is None and ".usd" in self.plugin.outputFormats:
            self.plugin.outputFormats.pop(self.plugin.outputFormats.index(".usd"))

        rsType = hou.nodeType(hou.sopNodeTypeCategory(), "Redshift_Proxy_Output")
        if rsType is not None and ".rs" not in self.plugin.outputFormats:
            self.plugin.outputFormats.insert(-2, ".rs")
        elif rsType is None and ".rs" in self.plugin.outputFormats:
            self.plugin.outputFormats.pop(self.plugin.outputFormats.index(".rs"))

    @err_catcher(name=__name__)
    def sm_saveStates(self, origin, buf):
        hou.node("/obj").setUserData("PrismStates", buf)

    @err_catcher(name=__name__)
    def sm_saveImports(self, origin, importPaths):
        hou.node("/obj").setUserData("PrismImports", importPaths)

    @err_catcher(name=__name__)
    def sm_readStates(self, origin):
        stateData = hou.node("/obj").userData("PrismStates")
        if stateData is not None:
            return stateData

    @err_catcher(name=__name__)
    def sm_deleteStates(self, origin):
        if hou.node("/obj").userData("PrismStates") is not None:
            hou.node("/obj").destroyUserData("PrismStates")

    @err_catcher(name=__name__)
    def sm_getImportHandlerType(self, extension):
        return self.importHandlerTypes.get(extension, "ImportFile")

    @err_catcher(name=__name__)
    def sm_getExternalFiles(self, origin):
        # 	hou.setFrame(hou.playbar.playbackRange()[0])
        if not os.getenv("PRISM_USE_HOUDINI_FILEREFERENCES"):
            return [[], []]

        whitelist = [
            "$HIP/$OS-bounce.rat",
            "$HIP/$OS-fill.rat",
            "$HIP/$OS-key.rat",
            "$HIP/$OS-rim.rat",
        ]
        expNodes = [
            x.ui.node
            for x in self.core.getStateManager().states
            if x.ui.className in ["Export", "ImageRender"]
            and x.ui.node is not None
            and self.isNodeValid(origin, x.ui.node)
        ]
        houdeps = hou.fileReferences()
        extFiles = []
        extFilesSource = []
        for x in houdeps:
            if "/Redshift/Plugins/Houdini/" in x[1]:
                continue

            if x[0] is None:
                continue

            if x[0].node() in expNodes:
                continue

            if x[0].node().parent() in expNodes and x[0].node().type().name() == "file":
                continue

            if x[1] in whitelist:
                continue

            if not os.path.isabs(hou.text.expandString(x[1])):
                continue

            if os.path.splitext(hou.text.expandString(x[1]))[1] == "":
                continue

            if x[0] is not None and x[0].name() in [
                "RS_outputFileNamePrefix",
                "vm_picture",
            ]:
                continue

            doContinue = False
            for whiteListed in self.whiteListedExternalFiles:
                if (
                    x[0]
                    and x[0].name() == whiteListed["parmName"]
                    and x[0].node().type().name() == whiteListed["nodeType"]
                ):
                    doContinue = True
                    break

            if doContinue:
                continue

            if (
                x[0] is not None
                and x[0].name() in ["filename", "dopoutput", "copoutput", "sopoutput"]
                and x[0].node().type().name()
                in ["rop_alembic", "rop_dop", "rop_comp", "rop_geometry"]
            ):
                continue

            if (
                x[0] is not None
                and x[0].name() in ["filename", "sopoutput"]
                and x[0].node().type().category().name() == "Driver"
                and x[0].node().type().name() in ["geometry", "alembic"]
            ):
                continue

            if (
                x[0] is not None
                and x[0].name()
                in ["default_image_filename", "default_export_nsi_filename"]
                and x[0].node().type().name() in ["3Delight"]
            ):
                continue

            extFiles.append(hou.text.expandString(x[1]).replace("\\", "/"))
            extFilesSource.append(x[0])

        return [extFiles, extFilesSource]

    @err_catcher(name=__name__)
    def captureViewportThumbnail(self):
        if not hou.isUIAvailable():
            return False

        file = tempfile.NamedTemporaryFile(suffix=".jpg")
        path = file.name
        file.close()
        frame = hou.frame()
        cur_desktop = hou.ui.curDesktop()
        scene = cur_desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if not scene:
            return

        if not scene.isCurrentTab():
            scene.setIsCurrentTab()

        flip_options = scene.flipbookSettings().stash()
        flip_options.outputToMPlay(False)
        flip_options.frameRange((frame, frame))
        flip_options.output(path)
        scene.flipbook(scene.curViewport(), flip_options)
        pm = self.core.media.getPixmapFromPath(path)
        try:
            os.remove(path)
        except:
            pass

        return pm

    @err_catcher(name=__name__)
    def getPreferredStateType(self, category):
        if category == "Export":
            if self.core.getStateManager().stateTypes["Save HDA"].canConnectNode():
                msg = 'The selected node can be connected to a "Save HDA" state.\nDo you want to create a "Save HDA" state?'
                result = self.core.popupQuestion(msg, parent=self.core.sm)
                self.core.getStateManager().activateWindow()
                if result == "Yes":
                    return "Save HDA"

            return "Export"
        else:
            return category

    @err_catcher(name=__name__)
    def isNodeValid(self, origin, node):
        try:
            node.name()
            return True
        except:
            return False

    @err_catcher(name=__name__)
    def isNodeValidFromState(self, state):
        try:
            return self.isNodeValid(None, state.node)
        except:
            return False

    @err_catcher(name=__name__)
    def goToNode(self, node):
        if not self.isNodeValid(self, node):
            return False

        node.setCurrent(True, clear_all_selected=True)
        paneTab = self.getNetworkPane(node=node.parent())
        if paneTab is not None:
            paneTab.setCurrentNode(node)
            paneTab.homeToSelection()

    @err_catcher(name=__name__)
    def getNetworkPane(self, cursor=True, node=None, multiple=False):
        ptype = hou.paneTabType.NetworkEditor
        underCursor = hou.ui.paneTabUnderCursor()
        if underCursor and underCursor.type() == ptype and not multiple:
            if not node or node == underCursor.pwd():
                return underCursor

        if node:
            validTabs = []
            for tab in hou.ui.paneTabs():
                if tab.type() == ptype and tab.pwd() == node:
                    validTabs.append(tab)

            if validTabs:
                if multiple:
                    return validTabs
                else:
                    return validTabs[0]

        if underCursor and underCursor.type() == ptype:
            return underCursor

        paneTab = hou.ui.paneTabOfType(ptype)
        if paneTab and multiple:
            return [paneTab]
        else:
            return paneTab

    @err_catcher(name=__name__)
    def getCamNodes(self, origin, cur=False):
        sceneCams = []
        for node in hou.node("/").allSubChildren():
            if (
                node.type().name() == "cam" and node.name() != "ipr_camera"
            ) or node.type().name() == "vrcam":
                sceneCams.append(node)

        if cur:
            sceneCams = ["Current View"] + sceneCams

        self.core.callback("houdini_getCameraNodes", sceneCams)
        return sceneCams

    @err_catcher(name=__name__)
    def getCamName(self, origin, handle):
        if handle == "Current View":
            return handle

        if self.core.isStr(handle):
            name = [x.name() for x in self.getCamNodes(origin) if x.name() == handle]
            if not name:
                return "invalid"
            else:
                name = name[0]
        else:
            name = handle.name()

        return name

    @err_catcher(name=__name__)
    def getValidNodeName(self, name):
        # valid node name characters: https://www.sidefx.com/docs/houdini/hom/hou/Node.html#methods-from-hou-networkmovableitem
        pattern = r"[^a-zA-Z0-9._-]"
        validName = re.sub(pattern, '_', name)
        return validName

    @err_catcher(name=__name__)
    def sm_createStatePressed(self, origin, stateType):
        stateCategories = []
        if stateType == "Render":
            renderers = self.getRendererPlugins()
            if len(hou.selectedNodes()) > 0:
                for i in renderers:
                    if hou.selectedNodes()[0].type().name() in i.ropNames:
                        stateData = {"label": "Render", "stateType": "ImageRender"}
                        return stateData

            for renderer in renderers:
                stateCategories.append({"label": "Render (%s)" % renderer.label, "stateType": "ImageRender", "kwargs": {"renderer": renderer.label}})

        return stateCategories

    @err_catcher(name=__name__)
    def getRendererPlugins(self):
        gpath = os.path.dirname(os.path.abspath(__file__)) + "/Prism_Houdini_Renderer_*"
        files = glob.glob(gpath)

        rplugs = []
        for f in files:
            if f.endswith(".pyc"):
                continue

            rname = os.path.splitext(os.path.basename(f))[0]

            if eval(os.getenv("PRISM_DEBUG", "False")):
                try:
                    del sys.modules[rname]
                except:
                    pass

            rplug = __import__(rname)
            if hasattr(rplug, "isActive") and rplug.isActive():
                rplugs.append(rplug)

        return rplugs

    @err_catcher(name=__name__)
    def sm_existExternalAsset(self, origin, asset):
        if asset.startswith("op:") and hou.node(asset.replace("\\", "/")) is not None:
            return True

        return False

    @err_catcher(name=__name__)
    def sm_fixWarning(self, origin, asset, extFiles, extFilesSource):
        parm = extFilesSource[extFiles.index(asset.replace("\\", "/"))]
        if parm is None:
            parmStr = ""
        else:
            parmStr = "In parameter: %s" % parm.path()

        return parmStr

    @err_catcher(name=__name__)
    def getRenderRopTypes(self):
        types = []
        renderers = self.getRendererPlugins()
        for renderer in renderers:
            types += renderer.ropNames

        return types

    @err_catcher(name=__name__)
    def sm_openStateFromNode(self, origin, menu, stateType=None, callback=None):
        nodeMenu = QMenu("From node", origin)

        if not stateType or stateType == "Render":
            renderMenu = QMenu("ImageRender", origin)
            ropTypes = self.getRenderRopTypes()

            renderNodes = []
            for node in hou.node("/").allSubChildren():
                if node.type().name() in ropTypes:
                    renderNodes.append(node)

            for i in origin.states:
                if (
                    i.ui.className == "ImageRender"
                    and self.isNodeValid(None, i.ui.node)
                    and i.ui.node in renderNodes
                ):
                    renderNodes.remove(i.ui.node)

            callback = callback or (lambda node: origin.createState(
                "ImageRender", node=node, setActive=True
            ))

            for node in renderNodes:
                actRender = QAction(node.path(), origin)
                actRender.triggered.connect(
                    lambda y=None, n=node: callback(node=n)
                )
                renderMenu.addAction(actRender)

            if not renderMenu.isEmpty():
                nodeMenu.addMenu(renderMenu)

        if not stateType or stateType == "Export":
            ropMenu = QMenu("Export", origin)
            ropNodes = []
            for node in hou.node("/").allSubChildren():
                if node.type().name() in [
                    "rop_dop",
                    "rop_comp",
                    "rop_geometry",
                    "rop_alembic",
                    "filecache",
                    "pixar::usdrop",
                    "Redshift_Proxy_Output",
                ]:
                    ropNodes.append(node)

                if node.type().category().name() == "Driver" and node.type().name() in [
                    "geometry",
                    "alembic",
                ]:
                    ropNodes.append(node)

            for i in origin.states:
                if (
                    i.ui.className == "Export"
                    and self.isNodeValidFromState(i.ui)
                    and i.ui.node in ropNodes
                ):
                    ropNodes.remove(i.ui.node)

            callback = callback or (lambda node: origin.createState(
                "Export", node=node, setActive=True
            ))

            for node in ropNodes:
                actExport = QAction(node.path(), origin)
                actExport.triggered.connect(
                    lambda y=None, n=node: callback(node=n)
                )
                ropMenu.addAction(actExport)

            if not ropMenu.isEmpty():
                nodeMenu.addMenu(ropMenu)

        if not nodeMenu.isEmpty():
            menu.addMenu(nodeMenu)

    @err_catcher(name=__name__)
    def sm_render_getDeadlineParams(self, origin, dlParams, homeDir):
        dlParams["pluginInfoFile"] = os.path.join(
            homeDir, "temp", "houdini_plugin_info.job"
        )
        dlParams["jobInfoFile"] = os.path.join(
            homeDir, "temp", "houdini_submit_info.job"
        )

        dlParams["jobInfos"]["Plugin"] = "Houdini"
        dlParams["jobInfos"]["Comment"] = (
            "Prism-Submission-Houdini_%s" % origin.className
        )

        if hasattr(origin, "getRenderNode"):
            driver = origin.getRenderNode()
            if driver.isInsideLockedHDA():
                if "OutputDirectory0" in dlParams["jobInfos"]:
                    del dlParams["jobInfos"]["OutputDirectory0"]

                if "OutputFilename0" in dlParams["jobInfos"]:
                    del dlParams["jobInfos"]["OutputFilename0"]
        else:
            driver = origin.node

        dlParams["pluginInfos"]["OutputDriver"] = driver.path()
        dlParams["pluginInfos"]["IgnoreInputs"] = "False"
        dlParams["pluginInfos"]["Version"] = self.getDeadlineHoudiniVersion()

        if hasattr(origin, "chb_resOverride") and origin.chb_resOverride.isChecked():
            dlParams["pluginInfos"]["Width"] = origin.sp_resWidth.value()
            dlParams["pluginInfos"]["Height"] = origin.sp_resHeight.value()

    @err_catcher(name=__name__)
    def getDeadlineHoudiniVersion(self):
        envKey = "PRISM_DEADLINE_HOUDINI_VERSION"
        if envKey in os.environ:
            version = os.environ[envKey]
        elif (
            int(
                self.core.plugins.getRenderfarmPlugin("Deadline")
                .CallDeadlineCommand(["-version"])
                .split(".")[0][1:]
            )
            > 9
        ):
            version = "%s.%s" % (
                hou.applicationVersion()[0],
                hou.applicationVersion()[1],
            )
        else:
            version = hou.applicationVersion()[0]

        return version

    @err_catcher(name=__name__)
    def sm_renderSettings_getCurrentSettings(self, origin, node=None, asString=True):
        settings = []
        if not node:
            node = hou.node(origin.e_node.text())

        if not node:
            return ""

        for parm in sorted(node.parms(), key=lambda x: x.name().lower()):
            setting = {}
            if len(parm.keyframes()) == 1:
                setting[parm.name()] = parm.expression() + " [expression]"
            elif parm.parmTemplate().dataType() == hou.parmData.String:
                setting[parm.name()] = parm.unexpandedString()
            else:
                setting[parm.name()] = parm.eval()
            settings.append(setting)

        if not asString:
            return settings

        settingsStr = self.core.writeYaml(data=settings)
        return settingsStr

    @err_catcher(name=__name__)
    def sm_renderSettings_setCurrentSettings(
        self, origin, preset, state=None, node=None
    ):
        if not node:
            if state:
                node = hou.node(state.e_node.text())
        if not node:
            return

        for setting in preset:
            parm = node.parm(list(setting.keys())[0])
            if not parm:
                continue

            value = setting.values()[0]
            if sys.version[0] == "2":
                isStr = isinstance(value, basestring)
            else:
                isStr = isinstance(value, str)

            if isStr and value.endswith(" [expression]"):
                value = value[: -len(" [expression")]
                parm.setExpression(value)
            else:
                parm.deleteAllKeyframes()
                try:
                    parm.set(value)
                except:
                    pass

    @err_catcher(name=__name__)
    def sm_renderSettings_applyDefaultSettings(self, origin):
        node = hou.node(origin.e_node.text())
        if not node:
            return

        for parm in node.parms():
            parm.revertToDefaults()

    @err_catcher(name=__name__)
    def sm_renderSettings_startup(self, origin):
        origin.w_node = QWidget()
        origin.lo_node = QHBoxLayout()
        origin.w_node.setLayout(origin.lo_node)
        origin.l_node = QLabel("Node:")
        origin.e_node = QLineEdit()
        origin.e_node.setContextMenuPolicy(Qt.CustomContextMenu)
        origin.e_node.customContextMenuRequested.connect(
            lambda x: self.showNodeContext(origin)
        )
        origin.e_node.editingFinished.connect(origin.stateManager.saveStatesToScene)
        origin.e_node.textChanged.connect(lambda x: origin.updateUi())

        origin.lo_node.addWidget(origin.l_node)
        origin.lo_node.addWidget(origin.e_node)
        if self.core.uiAvailable:
            origin.b_node = hou.qt.NodeChooserButton()
            origin.b_node.nodeSelected.connect(
                lambda x: origin.e_node.setText(x.path())
            )
            origin.b_node.nodeSelected.connect(origin.stateManager.saveStatesToScene)
            origin.lo_node.addWidget(origin.b_node)

        origin.gb_general.layout().insertWidget(0, origin.w_node)

    @err_catcher(name=__name__)
    def sm_renderSettings_loadData(self, origin, data):
        if "node" in data:
            origin.e_node.setText(data["node"])

    @err_catcher(name=__name__)
    def sm_renderSettings_getStateProps(self, origin):
        stateProps = {"node": origin.e_node.text()}

        return stateProps

    @err_catcher(name=__name__)
    def sm_renderSettings_addSelected(self, origin):
        if len(hou.selectedNodes()) == 0:
            return False

        origin.e_node.setText(hou.selectedNodes()[0].path())

    @err_catcher(name=__name__)
    def sm_renderSettings_preExecute(self, origin):
        warnings = []

        if not hou.node(origin.e_node.text()):
            warnings.append(["Invalid node specified.", "", 2])

        return warnings

    @err_catcher(name=__name__)
    def showNodeContext(self, origin):
        rcMenu = QMenu(origin.stateManager)
        mAct = QAction("Add selected", origin)
        mAct.triggered.connect(lambda: self.sm_renderSettings_addSelected(origin))
        rcMenu.addAction(mAct)

        rcMenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def createRop(self, nodeType):
        node = hou.node(self.ropLocation).createNode(nodeType)
        return node

    @err_catcher(name=__name__)
    def getStateFromNode(self, kwargs, create=True):
        sm = self.core.getStateManager()
        if not sm:
            return

        knode = kwargs["node"]

        for state in sm.states:
            node = getattr(state.ui, "node", None)
            if not self.isNodeValid(None, node):
                node = None

            if node and node.path() == knode.path():
                return state

        if getattr(sm, "stateInCreation", None):
            return sm.stateInCreation

        if not create:
            return

        state = self.createStateForNode(kwargs)
        return state

    @err_catcher(name=__name__)
    def showInStateManagerFromNode(self, kwargs):
        sm = self.core.getStateManager()
        if not sm:
            return

        if not sm.isVisible():
            sm.show()
            QCoreApplication.processEvents()

        sm.activateWindow()
        sm.raise_()
        if sm.isMinimized():
            sm.showNormal()

        state = self.getStateFromNode(kwargs)
        parent = state.parent()
        while parent:
            parent.setExpanded(True)
            parent = parent.parent()

        sm.selectState(state)

    @err_catcher(name=__name__)
    def findNode(self, path):
        for node in hou.node("/").allSubChildren():
            if (
                node.userData("PrismPath") is not None
                and node.userData("PrismPath") == path
            ):
                node.setUserData("PrismPath", node.path())
                return node

        return None

    @err_catcher(name=__name__)
    def openInExplorerFromNode(self, kwargs):
        path = kwargs["node"].parm("filepath").eval()
        self.core.openFolder(path)

    @err_catcher(name=__name__)
    def onNodeCreated(self, kwargs):
        pass

    @err_catcher(name=__name__)
    def getApiFromNode(self, node):
        for api in self.nodeTypeAPIs:
            validApi = self.isValidNodeApi(node, api)

            if validApi:
                return api

    @err_catcher(name=__name__)
    def onNodeDeleted(self, kwargs):
        if hou.hipFile.isLoadingHipFile() or hou.hipFile.isShuttingDown():
            return

        state = self.getStateFromNode(kwargs, create=False)
        if not state:
            return

        parent = None
        api = self.getApiFromNode(kwargs["node"])
        if api:
            parent = api.getParentFolder(create=False, node=kwargs["node"])

        sm = self.core.getStateManager()
        if not sm:
            return

        sm.deleteState(state, silent=True)
        while parent:
            if parent and parent.childCount() == 0:
                newParent = parent.parent()
                sm.deleteState(parent)
                parent = newParent
            else:
                break

    @err_catcher(name=__name__)
    def isValidNodeApi(self, node, api):
        validApi = False
        typeName = api.getTypeName()
        if isinstance(typeName, list):
            typeNames = typeName
        else:
            typeNames = [typeName]

        for name in typeNames:
            validApi = node.type().name().startswith(name)
            if validApi:
                break

        return validApi

    @err_catcher(name=__name__)
    def createStateForNode(self, kwargs):
        sm = self.core.getStateManager()

        parent = None
        api = self.getApiFromNode(kwargs["node"])
        if not api:
            return

        parent = api.getParentFolder(create=True, node=kwargs["node"])
        if parent:
            parentExpanded = parent.isExpanded()

        stateType = getattr(api, "getStateTypeForNode", lambda x: api.stateType)(kwargs["node"])
        openBrowser = False if api.listType == "Import" else None
        state = sm.createState(
            stateType,
            node=kwargs["node"],
            setActive=True,
            openProductsBrowser=openBrowser,
            parent=parent,
        )

        if parent:
            parent.setExpanded(parentExpanded)
            for state in sm.getSelectedStates():
                sm.ensureVisibility(state)

        return state

    @err_catcher(name=__name__)
    def detectCacheSequence(self, path):
        folder = os.path.dirname(path)
        fname = os.path.basename(path)
        base, ext = self.splitExtension(fname)
        convertedParts = []
        for part in base.split("."):
            if len(part) == self.core.framePadding:
                part = part.strip("-")
                if sys.version[0] == "2":
                    part = unicode(part)

                if part.isnumeric():
                    part = "$F" + str(self.core.framePadding)

            convertedParts.append(part)

        convertedFilename = ".".join(convertedParts) + ext
        convertedPath = os.path.join(folder, convertedFilename).replace("\\", "/")
        return convertedPath

    @err_catcher(name=__name__)
    def handleNetworkDrop(self, fileList):
        return False


class PublishDialog(QDialog):
    def __init__(self, plugin, state):
        super(PublishDialog, self).__init__()
        self.plugin = plugin
        self.state = state
        self.core = self.plugin.core
        self.core.parentWindow(self)
        self.showSm = False
        if self.core.sm.isVisible():
            self.core.sm.setHidden(True)
            self.showSm = True

        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self):
        self.setWindowTitle("Publish Node - %s" % self.state.ui.node.path())
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.addWidget(self.state.ui)
        if hasattr(self.state.ui, "gb_previous"):
            self.state.ui.gb_previous.setHidden(True)

        self.b_publish = QPushButton("Publish")
        self.lo_main.addWidget(self.b_publish)
        self.b_publish.clicked.connect(self.publish)

    @err_catcher(name=__name__)
    def closeEvent(self, event):
        if self.state == self.core.sm.getCurrentItem(self.core.sm.activeList):
            self.core.sm.showState()

        if self.showSm:
            self.core.sm.setHidden(False)

        event.accept()

    @err_catcher(name=__name__)
    def publish(self):
        self.hide()
        sm = self.core.getStateManager()
        sm.publish(
            executeState=True,
            states=[self.state],
        )
        self.close()
