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
import platform
import glob
import logging

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

import hou

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
        self.assetFormats = [
            ".hda",
            ".hdanc",
            ".hdalc",
            ".otl",
            ".otlnc",
            ".otllc",
        ]
        self.ropLocation = "/out"
        self.filecache = Prism_Houdini_Node_Filecache.Prism_Houdini_Filecache(self.plugin)
        self.importFile = Prism_Houdini_Node_ImportFile.Prism_Houdini_ImportFile(self.plugin)
        self.callbacks = []
        self.registerCallbacks()

    @err_catcher(name=__name__)
    def registerCallbacks(self):
        self.callbacks.append(self.core.registerCallback("sceneSaved", self.updateEnvironment))

    @err_catcher(name=__name__)
    def unregister(self):
        self.unregisterCallbacks()

    @err_catcher(name=__name__)
    def unregisterCallbacks(self):
        for cb in self.callbacks:
            self.core.unregisterCallback(cb["id"])

    @err_catcher(name=__name__)
    def onEventLoopCallback(self):
        self.eventLoopIterations += 1
        if self.eventLoopIterations == 2:
            self.guiReady = True
            hou.ui.removeEventLoopCallback(self.onEventLoopCallback)

    @err_catcher(name=__name__)
    def startup(self, origin):
        if self.core.uiAvailable:
            if not hou.isUIAvailable():
                return False

            if not hou.ui.mainQtWindow():
                return False

            if not self.eventLoopCallbackAdded:
                self.eventLoopCallbackAdded = True
                hou.ui.addEventLoopCallback(self.onEventLoopCallback)

            if not self.guiReady:
                return False

            if platform.system() == "Darwin":
                origin.messageParent = QWidget()
                origin.messageParent.setParent(hou.ui.mainQtWindow(), Qt.Window)
                if self.core.useOnTop:
                    origin.messageParent.setWindowFlags(
                        origin.messageParent.windowFlags() ^ Qt.WindowStaysOnTopHint
                    )
            else:
                origin.messageParent = hou.ui.mainQtWindow()

            origin.timer.stop()
        else:
            QApplication.addLibraryPath(
                os.path.join(hou.expandString("$HFS"), "bin", "Qt_plugins")
            )
            qApp = QApplication.instance()
            if qApp is None:
                qApp = QApplication(sys.argv)
            origin.messageParent = QWidget()

    @err_catcher(name=__name__)
    def autosaveEnabled(self, origin):
        return hou.hscript("autosave")[0] == "autosave on\n"

    @err_catcher(name=__name__)
    def onProjectChanged(self, origin):
        self.loadPrjHDAs(origin)
        self.updateProjectEnvironment()

    @err_catcher(name=__name__)
    def sceneOpen(self, origin):
        origin.sceneUnload()
        self.updateEnvironment()

    @err_catcher(name=__name__)
    def updateEnvironment(self):
        envvars = {
            "PRISM_SEQUENCE": "",
            "PRISM_SHOT": "",
            "PRISM_ASSET": "",
            "PRISM_ASSETPATH": "",
            "PRISM_STEP": "",
            "PRISM_CATEGORY": "",
            "PRISM_USER": "",
            "PRISM_FILE_VERSION": "",
        }

        for envvar in envvars:
            envvars[envvar] = hou.hscript("echo $%s" % envvar)

        newenv = {}

        fn = self.core.getCurrentFileName()
        data = self.core.getScenefileData(fn)
        if data["entity"] == "asset":
            newenv["PRISM_SEQUENCE"] = ""
            newenv["PRISM_SHOT"] = ""
            newenv["PRISM_ASSET"] = data["entityName"]
            entityPath = self.core.paths.getEntityBasePath(data["filename"])
            assetPath = self.core.entities.getAssetRelPathFromPath(entityPath)
            newenv["PRISM_ASSETPATH"] = assetPath.replace("\\", "/")
        elif data["entity"] == "shot":
            newenv["PRISM_ASSET"] = ""
            newenv["PRISM_ASSETPATH"] = ""

            sData = self.core.entities.splitShotname(data["entityName"])
            newenv["PRISM_SEQUENCE"] = sData[1]
            newenv["PRISM_SHOT"] = sData[0]
        else:
            newenv["PRISM_SEQUENCE"] = ""
            newenv["PRISM_SHOT"] = ""
            newenv["PRISM_ASSET"] = ""
            newenv["PRISM_ASSETPATH"] = ""

        if data["entity"] != "invalid":
            newenv["PRISM_STEP"] = data["step"]
            newenv["PRISM_CATEGORY"] = data["category"]
            newenv["PRISM_USER"] = getattr(self.core, "user", "")
            newenv["PRISM_FILE_VERSION"] = data["version"]
        else:
            newenv["PRISM_STEP"] = ""
            newenv["PRISM_CATEGORY"] = ""
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
    def loadPrjHDAs(self, origin):
        if not hasattr(origin, "projectPath") or not os.path.exists(origin.projectPath):
            return

        self.core.users.ensureUser()
        self.uninstallHDAs(origin.prjHDAs)

        hdaFolders = [os.path.join(origin.projectPath, "00_Pipeline", "HDAs")]

        prjHDAs = self.getProjectHDAFolder()
        if hasattr(self.core, "user"):
            hdaUFolder = os.path.join(prjHDAs, origin.user)
            hdaFolders += [prjHDAs, hdaUFolder]

        origin.prjHDAs = self.findHDAs(hdaFolders)

        oplib = os.path.join(prjHDAs, "ProjectHDAs.oplib")
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
        resourceDir = self.core.getConfig("paths", "assets", configPath=self.core.prismIni)
        folder = os.path.join(self.core.projectPath, resourceDir, "HDAs")

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
        convertNode=False
    ):
        namespace = self.core.getConfig("houdini", "assetNamespace", dft="prism", configPath=self.core.prismIni)
        if namespace:
            typeName = namespace + "::" + typeName

        if node.canCreateDigitalAsset():
            if projectHDA and not outputPath:
                filename = typeName.split("::", 1)[1]
                outputPath = self.getProjectHDAFolder(filename)
                if os.path.exists(outputPath):
                    msg = "The HDA file already exists:\n\n%s\n\nDo you want to save a new definition into this file and possibly overwrite an existing definition?" % outputPath
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
                    msg = "Canceled HDA creation.\n\n" + msg + "\n\nYou can enable \"Allow external references\" in the state settings to ignore this warning."
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

                self.saveNodeDefinitionToFile(node, libFile, typeName=typeName, label=label, blackBox=blackBox)
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

                self.saveNodeDefinitionToFile(node, outputPath, typeName=typeName, label=label, blackBox=blackBox)

                if projectHDA:
                    oplib = os.path.join(os.path.dirname(outputPath), "ProjectHDAs.oplib").replace("\\", "/")
                    hou.hda.installFile(outputPath, oplib, force_use_assets=setDefinitionCurrent)
                else:
                    hou.hda.installFile(outputPath, force_use_assets=setDefinitionCurrent)

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
    def saveNodeDefinitionToFile(self, node, filepath, typeName=None, label=None, blackBox=False):
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

        if noBackup:
            kwargs.pop("create_backup")

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

        if noBackup:
            kwargs.pop("create_backup")

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
        projectHDA=False
    ):
        fileName = self.core.getCurrentFileName()
        fnameData = self.core.getScenefileData(fileName)
        prefUnit = "meter"

        if node and node.type().definition() and saveToExistingHDA:
            outputPath = node.type().definition().libraryFilePath()
            outputFolder = os.path.dirname(outputPath)
        elif node and projectHDA:
            outputPath = self.core.appPlugin.getProjectHDAFolder(task)
            outputFolder = os.path.dirname(outputPath)
            version = None
        else:
            if not task:
                return

            fileName = self.core.convertPath(path=fileName, target="global")
            versionUser = user or self.core.user

            entityBase = self.core.getEntityBasePath(fileName)
            outputFolder = os.path.join(entityBase, "Export", task)
            if fnameData["entity"] == "shot":
                if version == "next":
                    version = self.core.getHighestTaskVersion(outputFolder)

                outputFolder = os.path.join(
                    outputFolder,
                    version
                    + self.core.filenameSeparator
                    + comment
                    + self.core.filenameSeparator
                    + versionUser,
                    prefUnit,
                )
                outputPath = os.path.join(
                    outputFolder,
                    "shot"
                    + self.core.filenameSeparator
                    + fnameData["entityName"]
                    + self.core.filenameSeparator
                    + task
                    + self.core.filenameSeparator
                    + version
                    + ".hda",
                )
            elif fnameData["entity"] == "asset":
                if version == "next":
                    version = self.core.getHighestTaskVersion(outputFolder)

                outputFolder = os.path.join(
                    outputFolder,
                    version
                    + self.core.filenameSeparator
                    + comment
                    + self.core.filenameSeparator
                    + versionUser,
                    prefUnit,
                )
                outputPath = os.path.join(
                    outputFolder,
                    fnameData["entityName"]
                    + self.core.filenameSeparator
                    + task
                    + self.core.filenameSeparator
                    + version
                    + ".hda",
                )
            else:
                logger.warning("Invalid entity.")
                return

        basePath = self.core.getExportPaths()[location]
        prjPath = os.path.normpath(self.core.projectPath)
        basePath = os.path.normpath(basePath)
        outputPath = outputPath.replace(prjPath, basePath)
        outputFolder = outputFolder.replace(prjPath, basePath)

        result = {
            "outputPath": outputPath.replace("\\", "/"),
            "outputFolder": outputFolder.replace("\\", "/"),
            "version": version,
        }

        return result

    @err_catcher(name=__name__)
    def executeScript(self, origin, code, execute=False, globalVars=None, localVars=None):
        try:
            if not execute:
                return eval(code)
            else:
                exec(code, globalVars, localVars)
        except Exception as e:
            msg = "\npython code:\n%s" % code
            exec("raise type(e), type(e)(e.message + msg), sys.exc_info()[2]")

    @err_catcher(name=__name__)
    def getCurrentFileName(self, origin, path=True):
        if path:
            return hou.hipFile.path()
        else:
            return hou.hipFile.basename()

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
    def saveScene(self, origin, filepath, details={}):
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
        setGobalFrangeExpr = "tset `(%d-1)/$FPS` `%d/$FPS`" % (startFrame, endFrame)
        hou.hscript(setGobalFrangeExpr)
        hou.playbar.setPlaybackRange(startFrame, endFrame)
        currentFrame = currentFrame or startFrame
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
    def cacheHouTmp(self, ropNode):
        if not os.path.exists(self.core.prismIni):
            curPrj = self.core.getConfig("globals", "current project")
            if curPrj != "" and curPrj is not None:
                QMessageBox.warning(
                    self.core.messageParent,
                    "Warning (cacheHouTmp)",
                    "Could not find project:\n%s"
                    % os.path.dirname(os.path.dirname(curPrj)),
                )

            self.core.projects.setProject(openUi="stateManager")
            return False

        if not self.core.users.ensureUser():
            return False

        if not self.core.fileInPipeline():
            QMessageBox.warning(
                self.core.messageParent,
                "Could not write the cache",
                "The current file is not inside the Pipeline.\nUse the Project Browser to create a file in the Pipeline.",
            )
            return False

        if self.core.useLocalFiles:
            basePath = self.core.getScenePath(location="local")
        else:
            basePath = self.core.getScenePath(location="global")

        exportNode = hou.node(ropNode.path() + "/ropnet1/RENDER")

        sceneBase = os.path.splitext(os.path.basename(self.core.getCurrentFileName()))[
            0
        ]
        outputPath = os.path.join(
            basePath,
            "Caches",
            sceneBase,
            ropNode.name(),
        )
        if not os.path.exists(outputPath):
            os.makedirs(outputPath)

        outputFile = "%s_%s.$F4.bgeo.sc" % (sceneBase, ropNode.name())

        outputStr = os.path.join(outputPath, outputFile)
        if not self.setNodeParm(ropNode, "outputpath", outputStr):
            return False

        exportNode.parm("execute").pressButton()

    @err_catcher(name=__name__)
    def getAppVersion(self, origin):
        return hou.applicationVersion()[1:-1]

    @err_catcher(name=__name__)
    def onProjectBrowserStartup(self, origin):
        if platform.system() == "Darwin":
            origin.menubar.setNativeMenuBar(False)
        origin.checkColor = "rgb(185, 134, 32)"

    @err_catcher(name=__name__)
    def preLoadEmptyScene(self, origin, filepath):
        self.curDesktop = hou.ui.curDesktop()

    @err_catcher(name=__name__)
    def postLoadEmptyScene(self, origin, filepath):
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
    def setSaveColor(self, origin, btn):
        btn.setStyleSheet("background-color: " + origin.checkColor)

    @err_catcher(name=__name__)
    def clearSaveColor(self, origin, btn):
        btn.setStyleSheet("")

    @err_catcher(name=__name__)
    def setProject_loading(self, origin):
        if self.core.uiAvailable:
            origin.sa_recent.setStyleSheet(
                hou.qt.styleSheet().replace("QLabel", "QScrollArea")
                + "QScrollArea { border: 0px;}"
            )

    @err_catcher(name=__name__)
    def onPrismSettingsOpen(self, origin):
        if self.core.uiAvailable:
            origin.scrollArea.setStyleSheet(
                hou.qt.styleSheet().replace("QLabel", "QScrollArea")
            )

            origin.sp_curPfps.setStyleSheet(
                hou.qt.styleSheet().replace("QSpinBox", "QDoubleSpinBox")
            )

        for i in origin.groupboxes:
            self.fixStyleSheet(i)

    @err_catcher(name=__name__)
    def createProject_startup(self, origin):
        if self.core.uiAvailable:
            origin.scrollArea.setStyleSheet(
                hou.qt.styleSheet().replace("QLabel", "QScrollArea")
            )

    @err_catcher(name=__name__)
    def editShot_startup(self, origin):
        pass

    @err_catcher(name=__name__)
    def shotgunPublish_startup(self, origin):
        if self.core.uiAvailable:
            origin.te_description.setStyleSheet(
                hou.qt.styleSheet().replace("QTextEdit", "QPlainTextEdit")
            )

    @err_catcher(name=__name__)
    def fixImportPath(self, path):
        base, ext = self.splitExtension(path)
        pad = self.core.framePadding
        if len(base) > pad and base[-(pad+1)] != "v":
            try:
                int(base[-pad:])
                return base[:-pad] + "$F" + str(pad) + ext
            except:
                return path

        return path

    @err_catcher(name=__name__)
    def splitExtension(self, path):
        if path.endswith(".bgeo.sc"):
            return [path[: -len(".bgeo.sc")], ".bgeo.sc"]
        else:
            return os.path.splitext(path)

    @err_catcher(name=__name__)
    def setNodeParm(self, node, parm, val=None, clear=False):
        try:
            if clear:
                node.parm(parm).deleteAllKeyframes()
            else:
                node.parm(parm).set(val)
        except:
            if not node.parm(parm):
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
            msg = QMessageBox(
                QMessageBox.Question,
                "Delete state",
                (
                    "Do you also want to delete the connected node?\n\n%s"
                    % (item.ui.node.path())
                ),
                QMessageBox.No,
            )
            msg.addButton("Yes", QMessageBox.YesRole)
            msg.setParent(self.core.messageParent, Qt.Window)
            action = msg.exec_()

            if action == 0:
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

        if (
            item.ui.className == "ImportFile"
            and os.path.splitext(item.ui.e_file.text())[1] == ".hda"
        ):
            fpath = item.ui.e_file.text().replace("\\", "/")
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
        root = self.core.prismRoot.replace("\\", "/")
        ssheet = ""
        ssheet += (
            "QGroupBox::indicator::checked\n{\n    image: url(%s/Plugins/Apps/Houdini/UserInterfaces/checkbox_on.svg);\n}"
            % root
        )
        ssheet += (
            "QGroupBox::indicator::unchecked\n{\n    image: url(%s/Plugins/Apps/Houdini/UserInterfaces/checkbox_off.svg);\n}"
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

        root = self.core.prismRoot.replace("\\", "/")
        ssheet = ""
        ssheet += (
            "QTreeWidget::indicator::checked\n{\n    image: url(%s/Plugins/Apps/Houdini/UserInterfaces/checkbox_on.svg);\n}"
            % root
        )
        ssheet += (
            "QTreeWidget::indicator::unchecked\n{\n    image: url(%s/Plugins/Apps/Houdini/UserInterfaces/checkbox_off.svg);\n}"
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
        origin.b_getRange.setMaximumWidth(200 * self.core.uiScaleFactor)
        origin.b_setRange.setMaximumWidth(200 * self.core.uiScaleFactor)

        startframe = hou.playbar.playbackRange()[0]
        endframe = hou.playbar.playbackRange()[1]
        origin.sp_rangeStart.setValue(startframe)
        origin.sp_rangeEnd.setValue(endframe)

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
        if extension in self.assetFormats:
            return "Install HDA"
        else:
            return "ImportFile"

    @err_catcher(name=__name__)
    def sm_getExternalFiles(self, origin):
        # 	hou.setFrame(hou.playbar.playbackRange()[0])
        whitelist = [
            "$HIP/$OS-bounce.rat",
            "$HIP/$OS-fill.rat",
            "$HIP/$OS-key.rat",
            "$HIP/$OS-rim.rat",
        ]
        expNodes = [
            x.ui.node
            for x in self.core.sm.states
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

            if not os.path.isabs(hou.expandString(x[1])):
                continue

            if os.path.splitext(hou.expandString(x[1]))[1] == "":
                continue

            if x[0] is not None and x[0].name() in [
                "RS_outputFileNamePrefix",
                "vm_picture",
            ]:
                continue

            if (
                x[0] is not None
                and x[0].name() in ["taskgraphfile"]
                and x[0].node().type().name()
                in ["topnet"]
            ):
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
                and x[0].name() in ["default_image_filename", "default_export_nsi_filename"]
                and x[0].node().type().name()
                in ["3Delight"]
            ):
                continue

            extFiles.append(hou.expandString(x[1]).replace("\\", "/"))
            extFilesSource.append(x[0])

        return [extFiles, extFilesSource]

    @err_catcher(name=__name__)
    def isNodeValid(self, origin, node):
        try:
            node.name()
            return True
        except:
            return False

    @err_catcher(name=__name__)
    def sm_createRenderPressed(self, origin):
        renderers = self.getRendererPlugins()
        if len(hou.selectedNodes()) > 0:
            for i in renderers:
                if hou.selectedNodes()[0].type().name() in i.ropNames:
                    origin.createPressed("Render")
                    return

        if len(renderers) == 1:
            origin.createPressed("Render", renderer=renderers[0].label)
        else:
            rndMenu = QMenu(origin)
            for i in renderers:
                mAct = QAction(i.label, origin)
                mAct.triggered.connect(
                    lambda x=None, y=i.label: origin.createPressed("Render", renderer=y)
                )
                rndMenu.addAction(mAct)

            if rndMenu.isEmpty():
                origin.createPressed("Render")
                return False

            rndMenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def getRendererPlugins(self):
        gpath = os.path.dirname(os.path.abspath(__file__)) + "/Prism_Houdini_Renderer_*"
        files = glob.glob(gpath)

        rplugs = []
        for f in files:
            if f.endswith(".pyc"):
                continue

            rname = os.path.splitext(os.path.basename(f))[0]

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
    def sm_openStateFromNode(self, origin, menu):
        renderers = self.getRendererPlugins()
        if len(hou.selectedNodes()) > 0:
            for i in renderers:
                if hou.selectedNodes()[0].type().name() in i.ropNames:
                    origin.createPressed("Render")
                    return

        nodeMenu = QMenu("From node", origin)

        renderMenu = QMenu("ImageRender", origin)

        renderNodes = []
        for node in hou.node("/").allSubChildren():
            if node.type().name() in ["ifd", "Redshift_ROP"]:
                renderNodes.append(node)

        for i in origin.states:
            if (
                i.ui.className == "ImageRender"
                and i.ui.node is not None
                and i.ui.node in renderNodes
            ):
                renderNodes.remove(i.ui.node)

        for i in renderNodes:
            actRender = QAction(i.path(), origin)
            actRender.triggered.connect(
                lambda y=None, x=i: origin.createState(
                    "ImageRender", node=x, setActive=True
                )
            )
            renderMenu.addAction(actRender)

        if not renderMenu.isEmpty():
            nodeMenu.addMenu(renderMenu)

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
                and i.ui.node is not None
                and i.ui.node in ropNodes
            ):
                ropNodes.remove(i.ui.node)

        for i in ropNodes:
            actExport = QAction(i.path(), origin)
            actExport.triggered.connect(
                lambda y=None, x=i: origin.createState("Export", node=x, setActive=True)
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

        dlParams["pluginInfos"]["OutputDriver"] = origin.node.path()
        dlParams["pluginInfos"]["IgnoreInputs"] = "True"

        if (
            int(
                self.core.rfManagers["Deadline"]
                .deadlineCommand(["-version"])
                .split(".")[0][1:]
            )
            > 9
        ):
            dlParams["pluginInfos"]["Version"] = "%s.%s" % (
                hou.applicationVersion()[0],
                hou.applicationVersion()[1],
            )
        else:
            dlParams["pluginInfos"]["Version"] = hou.applicationVersion()[0]

        if hasattr(origin, "chb_resOverride") and origin.chb_resOverride.isChecked():
            dlParams["pluginInfos"]["Width"] = origin.sp_resWidth.value()
            dlParams["pluginInfos"]["Height"] = origin.sp_resHeight.value()

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
            parm = node.parm(setting.keys()[0])
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
            origin.b_node.nodeSelected.connect(lambda x: origin.e_node.setText(x.path()))
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
    def getStateFromNode(self, kwargs):
        sm = self.core.getStateManager()
        knode = kwargs["node"]

        for state in sm.states:
            node = getattr(state.ui, "node", None)
            if not self.isNodeValid(None, node):
                node = None

            if node and node.path() == knode.path():
                return state

        state = self.createStateForNode(kwargs)
        return state

    @err_catcher(name=__name__)
    def showInStateManagerFromNode(self, kwargs):
        sm = self.core.getStateManager()
        if not sm.isVisible():
            sm.show()

        state = self.getStateFromNode(kwargs)
        sm.selectState(state)

    @err_catcher(name=__name__)
    def openInExplorerFromNode(self, kwargs):
        path = kwargs["node"].parm("filepath").eval()
        self.core.openFolder(path)

    @err_catcher(name=__name__)
    def onNodeCreated(self, kwargs):
        self.createStateForNode(kwargs)

        if kwargs["node"].type().name().startswith("prism::ImportFile"):
            kwargs["node"].setColor(hou.Color(0.451, 0.369, 0.796))

    @err_catcher(name=__name__)
    def createStateForNode(self, kwargs):
        sm = self.core.getStateManager()

        if kwargs["node"].type().name().startswith("prism::ImportFile"):
            state = sm.createState("ImportFile", node=kwargs["node"], setActive=True, openProductsBrowser=False)
        elif kwargs["node"].type().name().startswith("prism::Filecache"):
            state = sm.createState("Export", node=kwargs["node"], setActive=True)

        return state
