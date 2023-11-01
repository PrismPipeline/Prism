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
import random
import logging
import tempfile
import re

import nuke
if nuke.env.get("gui"):
    try:
        from nukescripts import flipbooking, renderdialog, fnFlipbookRenderer
    except:
        pass

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

try:
    from PrismUtils.Decorators import err_catcher as err_catcher
except:
    err_catcher = lambda name: lambda func, *args, **kwargs: func(*args, **kwargs)


logger = logging.getLogger(__name__)


class Prism_Nuke_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        self.isRendering = {}
        self.useVersion = None
        self.core.registerCallback(
            "postSaveScene", self.postSaveScene, plugin=self.plugin
        )
        self.core.registerCallback(
            "onProjectBrowserStartup", self.onProjectBrowserStartup, plugin=self.plugin
        )
        self.core.registerCallback(
            "onPreMediaPlayerDragged", self.onPreMediaPlayerDragged, plugin=self.plugin
        )

    @err_catcher(name=__name__)
    def startup(self, origin):
        if self.core.uiAvailable:
            origin.timer.stop()

            for obj in QApplication.topLevelWidgets():
                if (
                    obj.inherits("QMainWindow")
                    and obj.metaObject().className() == "Foundry::UI::DockMainWindow"
                ):
                    nukeQtParent = obj
                    break
            else:
                nukeQtParent = QWidget()

            origin.messageParent = QWidget()
            origin.messageParent.setParent(nukeQtParent, Qt.Window)
            if platform.system() != "Windows" and self.core.useOnTop:
                origin.messageParent.setWindowFlags(
                    origin.messageParent.windowFlags() ^ Qt.WindowStaysOnTopHint
                )

        self.addPluginPaths()
        if self.core.uiAvailable:
            self.addMenus()

        self.addCallbacks()

    @err_catcher(name=__name__)
    def addPluginPaths(self):
        gdir = os.path.join(
            os.path.abspath(os.path.dirname(os.path.dirname(__file__))), "Gizmos"
        )
        gdir = gdir.replace("\\", "/")
        nuke.pluginAddPath(gdir)

    @err_catcher(name=__name__)
    def addMenus(self):
        nuke.menu("Nuke").addCommand("Prism/Save", self.saveScene, "Ctrl+s")
        nuke.menu("Nuke").addCommand("Prism/Save Version", self.core.saveScene, "Alt+Shift+s")
        nuke.menu("Nuke").addCommand("Prism/Save Comment", self.core.saveWithComment, "Ctrl+Shift+S")
        nuke.menu("Nuke").addCommand("Prism/Project Browser", self.core.projectBrowser)
        nuke.menu("Nuke").addCommand("Prism/Settings", self.core.prismSettings)
        nuke.menu("Nuke").addCommand(
            "Prism/Update selected read nodes", self.updateNukeNodes
        )

        toolbar = nuke.toolbar("Nodes")
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "p_tray.png"
        )
        toolbar.addMenu("Prism", icon=iconPath)
        toolbar.addCommand("Prism/ReadPrism", lambda: nuke.createNode("ReadPrism"))
        toolbar.addCommand("Prism/WritePrism", lambda: nuke.createNode("WritePrism"), "w", shortcutContext=2)

    @err_catcher(name=__name__)
    def addCallbacks(self):
        nuke.addOnScriptLoad(self.core.sceneOpen)
        nuke.addFilenameFilter(self.expandEnvVarsInFilepath)
        nuke.addOnScriptSave(self.core.scenefileSaved)

        import nukescripts
        nukescripts.drop.addDropDataCallback(self.dropHandler)

    @err_catcher(name=__name__)
    def dropHandler(self, mimeType, text):
        if not self.core.getConfig("nuke", "useRelativePaths", dft=False, config="user"):
            return

        if text.startswith(self.core.projectPath.replace("\\", "/")):
            if os.path.isdir(text):
                srcs = self.core.media.getImgSources(text)
            elif os.path.isfile(text):
                srcs = [text]
            else:
                return

            for src in srcs:
                if "#"*self.core.framePadding not in src:
                    src = self.core.media.getSequenceFromFilename(src)

                if "#"*self.core.framePadding in src:
                    files = self.core.media.getFilesFromSequence(src)
                    start, end = self.core.media.getFrameRangeFromSequence(files)
                    if start and end and start != "?" and end != "?":
                        src += " %s-%s" % (start, end)

                src = src.replace(self.core.projectPath.replace("\\", "/").rstrip("/"), "%PRISM_JOB%")
                read_node = nuke.createNode("Read", inpanel=False)
                read_node["file"].fromUserText(src)
            
            return True

    @err_catcher(name=__name__)
    def expandEnvVarsInFilepath(self, path):
        if not self.core.getConfig("nuke", "useRelativePaths", dft=False, config="user"):
            return

        expanded_path = os.path.expandvars(path)
        return expanded_path

    @err_catcher(name=__name__)
    def sceneOpen(self, origin):
        if self.core.shouldAutosaveTimerRun():
            origin.startAutosaveTimer()

    @err_catcher(name=__name__)
    def getCurrentFileName(self, origin, path=True):
        try:
            currentFileName = os.path.abspath(nuke.value("root.name"))
        except:
            currentFileName = ""

        if currentFileName == "Root":
            currentFileName = ""

        if not path:
            currentFileName = os.path.basename(currentFileName)

        return currentFileName

    @err_catcher(name=__name__)
    def getCurrentSceneFiles(self, origin):
        return [self.core.getCurrentFileName()]

    @err_catcher(name=__name__)
    def getSceneExtension(self, origin):
        return self.sceneFormats[0]

    @err_catcher(name=__name__)
    def saveScene(self, origin=None, filepath=None, details={}):
        try:
            if filepath:
                return nuke.scriptSaveAs(filename=filepath)
            else:
                return nuke.scriptSave()

        except:
            return ""

    @err_catcher(name=__name__)
    def getImportPaths(self, origin):
        return False

    @err_catcher(name=__name__)
    def getFrameRange(self, origin):
        startframe = nuke.root().knob("first_frame").value()
        endframe = nuke.root().knob("last_frame").value()

        return [startframe, endframe]

    @err_catcher(name=__name__)
    def getCurrentFrame(self):
        currentFrame = nuke.root().knob("frame").value()
        return currentFrame

    @err_catcher(name=__name__)
    def setFrameRange(self, origin, startFrame, endFrame):
        nuke.root().knob("first_frame").setValue(float(startFrame))
        nuke.root().knob("last_frame").setValue(float(endFrame))

    @err_catcher(name=__name__)
    def getFPS(self, origin):
        return nuke.knob("root.fps")

    @err_catcher(name=__name__)
    def setFPS(self, origin, fps):
        return nuke.knob("root.fps", str(fps))

    @err_catcher(name=__name__)
    def getResolution(self):
        resFormat = [nuke.root().width(), nuke.root().height()]
        return resFormat

    @err_catcher(name=__name__)
    def setResolution(self, width=None, height=None):
        return nuke.knob("root.format", "%s %s" % (width, height))

    @err_catcher(name=__name__)
    def updateNukeNodes(self):
        updatedNodes = []

        for i in nuke.selectedNodes():
            if i.Class() != "Read":
                continue

            curPath = i.knob("file").value()
            version = self.core.mediaProducts.getLatestVersionFromFilepath(curPath)
            if version and version["path"] not in curPath:
                filepattern = self.core.mediaProducts.getFilePatternFromVersion(version)
                filepattern = filepattern.replace("\\", "/")
                i.knob("file").setValue(filepattern)
                updatedNodes.append(i)

        if len(updatedNodes) == 0:
            self.core.popup("No nodes were updated", severity="info")
        else:
            mStr = "%s nodes were updated:\n\n" % len(updatedNodes)
            for i in updatedNodes:
                mStr += i.name() + "\n"

            self.core.popup(mStr, severity="info")

    # @err_catcher(name=__name__)
    # def renderAllWritePrismNodes(self):
    #     wpNodes = [node for node in nuke.allNodes() if node.Class() == "WritePrism"]
    #     self.renderWritePrismNodes(wpNodes)

    # @err_catcher(name=__name__)
    # def renderSelectedWritePrismNodes(self):
    #     wpNodes = [node for node in nuke.selectedNodes() if node.Class() == "WritePrism"]
    #     self.renderWritePrismNodes(wpNodes)

    # @err_catcher(name=__name__)
    # def renderWritePrismNodes(self, nodes):
    #     for node in nodes:
    #         self.getOutputPath(node.node("WritePrismBase"), node)

    #     import nukescripts
    #     nukescripts.showRenderDialog(nodes, False)

    @err_catcher(name=__name__)
    def getCamNodes(self, origin, cur=False):
        sceneCams = ["nuke"]
        return sceneCams

    @err_catcher(name=__name__)
    def getCamName(self, origin, handle):
        return handle

    @err_catcher(name=__name__)
    def isNodeValid(self, origin, handle):
        return True

    @err_catcher(name=__name__)
    def readNode_onBrowseClicked(self, node):
        if hasattr(self, "dlg_media"):
            self.dlg_media.close()

        self.dlg_media = ReadMediaDialog(self, node)
        self.dlg_media.mediaSelected.connect(lambda x: self.readNode_mediaSelected(node, x))
        self.dlg_media.show()

    @err_catcher(name=__name__)
    def readNode_mediaSelected(self, node, version):
        mediaFiles = self.core.mediaProducts.getFilesFromContext(version)
        validFiles = self.core.media.filterValidMediaFiles(mediaFiles)
        if not validFiles:
            return

        validFiles = sorted(validFiles, key=lambda x: x if "cryptomatte" not in os.path.basename(x) else "zzz" + x)
        baseName, extension = os.path.splitext(validFiles[0])
        seqFiles = self.core.media.detectSequences(validFiles)
        if seqFiles:
            node.knob("fileName").setValue(list(seqFiles)[0].replace("\\", "/"))

    @err_catcher(name=__name__)
    def readNode_onOpenInClicked(self, node):
        self.core.openFolder(node.knob("fileName").value())

    @err_catcher(name=__name__)
    def readNode_onCreateReadClicked(self, node):
        node.end()
        filepath = node.knob("fileName").value()
        readNode = nuke.createNode('Read')
        readNode.knob('file').fromUserText(filepath)

    @err_catcher(name=__name__)
    def getIdentifierFromNode(self, node):
        return node.knob("identifier").evaluate()

    @err_catcher(name=__name__)
    def getOutputPath(self, node, group, render=False, updateValues=True):
        if not nuke.env.get("gui"):
            filename = nuke.thisGroup().knob("fileName").toScript()
            if render and self.core.getConfig("globals", "backupScenesOnPublish", config="project"):
                self.core.entities.backupScenefile(os.path.dirname(filename))

            return filename

        try:
            taskName = self.getIdentifierFromNode(group)
            comment = group.knob("comment").value()
            fileType = group.knob("file_type").value()
            location = group.knob("location").value()
        except Exception as e:
            logger.warning("failed to get node knob values: %s" % str(e))
            return ""

        if not bool(location.strip()):
            location = "global"

        outputName = self.core.getCompositingOut(
            taskName,
            fileType,
            self.useVersion,
            render,
            location,
            comment=comment,
            node=node,
        )

        isNukeAssist = "--nukeassist" in nuke.rawArgs
        if not self.isNodeRendering(node) and not isNukeAssist and updateValues or render:
            group.knob("fileName").setValue(outputName)
            # group.knob("fileName").clearFlag(0x10000000) # makes knob read-only, but leads to double property Uis

        return outputName

    @err_catcher(name=__name__)
    def startRender(self, node, group, version=None):
        taskName = self.getIdentifierFromNode(group)

        if taskName is None or taskName == "":
            self.core.popup("Please choose an identifier")
            return

        fileName = self.getOutputPath(node, group)
        if fileName == "FileNotInPipeline":
            self.core.showFileNotInProjectWarning(title="Warning")
            return

        settings = {"outputName": fileName}
        scenefile = self.core.getCurrentFileName()
        kwargs = {
            "state": self,
            "scenefile": scenefile,
            "settings": settings,
        }

        result = self.core.callback("preRender", **kwargs)
        for res in result:
            if isinstance(res, dict) and res.get("cancel", False):
                return [
                    self.state.text(0)
                    + " - error - %s" % res.get("details", "preRender hook returned False")
                ]

        if version:
            msg = QMessageBox(
                QMessageBox.Information,
                "Render",
                "Are you sure you want to execute this state as version \"%s\"?\nThis may overwrite existing files." % version,
                QMessageBox.Cancel,
            )
            msg.addButton("Continue", QMessageBox.YesRole)
            self.core.parentWindow(msg)
            action = msg.exec_()

            if action != 0:
                return

        self.useVersion = version
        self.core.saveScene(versionUp=False)

        node.knob("Render").execute()
        kwargs = {
            "state": self,
            "scenefile": scenefile,
            "settings": settings,
        }

        self.core.callback("postRender", **kwargs)

        self.useVersion = None

    @err_catcher(name=__name__)
    def renderAsVersion(self, node, group):
        self.dlg_version = VersionDlg(self, node, group)
        if not self.dlg_version.isValid:
            return

        self.dlg_version.versionSelected.connect(lambda x: self.startRender(node, group, x))
        self.dlg_version.show()

    @err_catcher(name=__name__)
    def startedRendering(self, node, outputPath):
        nodePath = node.fullName()
        self.isRendering[nodePath] = [True, outputPath]

        nodeName = "root." + node.fullName()
        parentName = ".".join(nodeName.split(".")[:-1])
        group = nuke.toNode(parentName)
        prevKnob = group.knob("prevFileName")
        if prevKnob:
            prevKnob.setValue(outputPath)

    @err_catcher(name=__name__)
    def isNodeRendering(self, node):
        nodePath = node.fullName()
        rendering = nodePath in self.isRendering and self.isRendering[nodePath][0]
        return rendering

    @err_catcher(name=__name__)
    def getPathFromRenderingNode(self, node):
        nodePath = node.fullName()
        if nodePath in self.isRendering:
            return self.isRendering[nodePath][1]
        else:
            return ""

    @err_catcher(name=__name__)
    def finishedRendering(self, node):
        nodePath = node.fullName()
        if nodePath in self.isRendering:
            del self.isRendering[nodePath]

    @err_catcher(name=__name__)
    def getAppVersion(self, origin):
        return nuke.NUKE_VERSION_STRING

    @err_catcher(name=__name__)
    def onProjectBrowserStartup(self, origin):
        origin.actionStateManager.setEnabled(False)

    @err_catcher(name=__name__)
    def onPreMediaPlayerDragged(self, origin, urlList):
        urlList[:] = [urlList[0]]

    @err_catcher(name=__name__)
    def openScene(self, origin, filepath, force=False):
        if os.path.splitext(filepath)[1] not in self.sceneFormats:
            return False

        try:
            cleared = nuke.scriptSaveAndClear()
        except Exception as e:
            if "cannot clear script whilst executing" in str(e):
                self.core.popup(e)

            cleared = False

        if cleared:
            try:
                nuke.scriptOpen(filepath)
            except:
                pass

        return True

    @err_catcher(name=__name__)
    def importImages(self, origin):
        if origin.origin.getCurrentAOV():
            fString = "Please select an import option:"
            buttons = ["Current AOV", "All AOVs", "Layout all AOVs"]
            result = self.core.popupQuestion(fString, buttons=buttons, icon=QMessageBox.NoIcon)
        else:
            result = "Current AOV"

        if result == "Current AOV":
            self.nukeImportSource(origin)
        elif result == "All AOVs":
            self.nukeImportPasses(origin)
        elif result == "Layout all AOVs":
            self.nukeLayout(origin)
        else:
            return

    @err_catcher(name=__name__)
    def nukeImportSource(self, origin):
        sourceData = origin.compGetImportSource()

        for i in sourceData:
            filePath = i[0]
            firstFrame = i[1]
            lastFrame = i[2]

            node = nuke.createNode(
                "Read",
                "file \"%s\"" % filePath,
                False,
            )
            if firstFrame is not None:
                node.knob("first").setValue(firstFrame)
            if lastFrame is not None:
                node.knob("last").setValue(lastFrame)

    @err_catcher(name=__name__)
    def nukeImportPasses(self, origin):
        sourceData = origin.compGetImportPasses()

        for i in sourceData:
            filePath = i[0]
            firstFrame = i[1]
            lastFrame = i[2]

            node = nuke.createNode(
                "Read",
                "file \"%s\"" % filePath,
                False,
            )
            if firstFrame is not None:
                node.knob("first").setValue(firstFrame)
            if lastFrame is not None:
                node.knob("last").setValue(lastFrame)

    @err_catcher(name=__name__)
    def nukeLayout(self, origin):
        if nuke.env["nc"]:
            msg = "This feature is disabled because of the scripting limitations in Nuke non-commercial."
            self.core.popup(msg)
            return

        allExistingNodes = nuke.allNodes()
        try:
            allBBx = max([node.xpos() for node in allExistingNodes])
        except:
            allBBx = 0

        self.nukeYPos = 0
        xOffset = 200
        nukeXPos = allBBx + xOffset
        nukeSetupWidth = 950
        nukeSetupHeight = 400
        nukeYDistance = 700
        nukeBeautyYDistance = 500
        nukeBackDropFontSize = 100
        self.nukeIdxNode = None
        passFolder = os.path.dirname(os.path.dirname(origin.seq[0])).replace("\\", "/")

        if not os.path.exists(passFolder):
            return

        beautyTriggers = ["beauty", "rgb", "rgba"]
        componentsTriggers = [
            "ls",
            "select",
            "gi",
            "spec",
            "refr",
            "refl",
            "light",
            "lighting",
            "highlight",
            "diff",
            "diffuse",
            "emission",
            "sss",
            "vol",
        ]
        masksTriggers = ["mm", "mask", "puzzleMatte", "matte", "puzzle"]

        beautyPass = []
        componentPasses = []
        maskPasses = []
        utilityPasses = []

        self.maskNodes = []
        self.utilityNodes = []

        passes = [
            x
            for x in os.listdir(passFolder)
            if x[-5:] not in ["(mp4)", "(jpg)", "(png)"]
            and os.path.isdir(os.path.join(passFolder, x))
            and len(os.listdir(os.path.join(passFolder, x))) > 0
        ]

        passesBeauty = []
        passesComponents = []
        passesMasks = []
        passesUtilities = []

        for curPass in passes:
            assigned = False

            for trigger in beautyTriggers:
                if trigger in curPass.lower():
                    passesBeauty.append(curPass)
                    assigned = True
                    break

            if assigned:
                continue

            for trigger in componentsTriggers:
                if trigger in curPass.lower():
                    passesComponents.append(curPass)
                    assigned = True
                    break

            if assigned:
                continue

            for trigger in masksTriggers:
                if trigger in curPass.lower():
                    passesMasks.append(curPass)
                    assigned = True
                    break

            if assigned:
                continue

            passesUtilities.append(curPass)

        passes = passesBeauty + passesComponents + passesMasks + passesUtilities
        maskNum = 0
        utilsNum = 0

        for curPass in passes:
            curPassPath = os.path.join(passFolder, curPass)
            curPassName = os.listdir(curPassPath)[0].split(".")[0]

            if len(os.listdir(curPassPath)) > 1:
                if (
                    origin.pstart is None
                    or origin.pend is None
                    or origin.pstart == "?"
                    or origin.pend == "?"
                ):
                    self.core.popup(origin.pstart)
                    return

                firstFrame = origin.pstart
                lastFrame = origin.pend

                increment = "####"
                curPassFormat = os.listdir(curPassPath)[0].split(".")[-1]

                filePath = os.path.join(
                    passFolder,
                    curPass,
                    ".".join([curPassName, increment, curPassFormat]),
                ).replace("\\", "/")
            else:
                filePath = os.path.join(
                    curPassPath, os.listdir(curPassPath)[0]
                ).replace("\\", "/")
                firstFrame = 0
                lastFrame = 0

            # createPasses
            # beauty
            if curPass in passesBeauty:
                self.createBeautyPass(
                    origin,
                    filePath,
                    firstFrame,
                    lastFrame,
                    curPass,
                    nukeXPos,
                    nukeSetupWidth,
                    nukeBeautyYDistance,
                    nukeBackDropFontSize,
                )

            # components
            elif curPass in passesComponents:
                self.createComponentPass(
                    origin,
                    filePath,
                    firstFrame,
                    lastFrame,
                    curPass,
                    nukeXPos,
                    nukeSetupWidth,
                    nukeSetupHeight,
                    nukeBackDropFontSize,
                    nukeYDistance,
                )

            # masks
            elif curPass in passesMasks:
                maskNum += 1
                self.createMaskPass(
                    origin,
                    filePath,
                    firstFrame,
                    lastFrame,
                    nukeXPos,
                    nukeSetupWidth,
                    maskNum,
                )

            # utility
            elif curPass in passesUtilities:
                utilsNum += 1
                self.createUtilityPass(
                    origin,
                    filePath,
                    firstFrame,
                    lastFrame,
                    nukeXPos,
                    nukeSetupWidth,
                    utilsNum,
                )

        # maskbackdrop
        if len(self.maskNodes) > 0:
            bdX = min([node.xpos() for node in self.maskNodes])
            bdY = min([node.ypos() for node in self.maskNodes])
            bdW = (
                max([node.xpos() + node.screenWidth() for node in self.maskNodes]) - bdX
            )
            bdH = (
                max([node.ypos() + node.screenHeight() for node in self.maskNodes])
                - bdY
            )

            # backdrop boundry offsets
            left, top, right, bottom = (-160, -135, 160, 80)

            # boundry offsets
            bdX += left
            bdY += top
            bdW += right - left
            bdH += bottom - top

            # createbackdrop
            maskBackdropColor = int("%02x%02x%02x%02x" % (255, 125, 125, 1), 16)
            backDrop = nuke.nodes.BackdropNode(
                xpos=bdX,
                bdwidth=bdW,
                ypos=bdY,
                bdheight=bdH,
                tile_color=maskBackdropColor,
                note_font_size=nukeBackDropFontSize,
                label="<center><b>" + "Masks" + "</b><c/enter>",
            )

        # utilitybackdrop
        if len(self.utilityNodes) > 0:
            bdX = min([node.xpos() for node in self.utilityNodes])
            bdY = min([node.ypos() for node in self.utilityNodes])
            bdW = (
                max([node.xpos() + node.screenWidth() for node in self.utilityNodes])
                - bdX
            )
            bdH = (
                max([node.ypos() + node.screenHeight() for node in self.utilityNodes])
                - bdY
            )

            # backdrop boundry offsets
            left, top, right, bottom = (-160, -135, 160, 80)

            # boundry offsets
            bdX += left
            bdY += top
            bdW += right - left
            bdH += bottom - top

            # createbackdrop
            maskBackdropColor = int("%02x%02x%02x%02x" % (125, 255, 125, 1), 16)
            backDrop = nuke.nodes.BackdropNode(
                xpos=bdX,
                bdwidth=bdW,
                ypos=bdY,
                bdheight=bdH,
                tile_color=maskBackdropColor,
                note_font_size=nukeBackDropFontSize,
                label="<center><b>" + "Utilities" + "</b><c/enter>",
            )

    @err_catcher(name=__name__)
    def createBeautyPass(
        self,
        origin,
        filePath,
        firstFrame,
        lastFrame,
        curPass,
        nukeXPos,
        nukeSetupWidth,
        nukeBeautyYDistance,
        nukeBackDropFontSize,
    ):

        curReadNode = nuke.createNode(
            "Read",
            'file "%s" first %s last %s origfirst %s origlast %s'
            % (filePath, firstFrame, lastFrame, firstFrame, lastFrame),
            False,
        )

        nodeArray = [curReadNode]

        # backdropcolor
        r = (float(random.randint(30 + int((self.nukeYPos / 3) % 3), 80))) / 100
        g = (float(random.randint(20 + int((self.nukeYPos / 3) % 3), 80))) / 100
        b = (float(random.randint(15 + int((self.nukeYPos / 3) % 3), 80))) / 100
        hexColour = int("%02x%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255), 1), 16)

        # positions
        curReadNodeWidth = int(curReadNode.screenWidth() * 0.5 - 6)
        curReadNodeHeight = int(curReadNode.screenHeight() * 0.5 - 3)

        curReadNode.setYpos(self.nukeYPos + curReadNodeHeight)
        curReadNode.setXpos(nukeXPos + nukeSetupWidth)

        # backdrop boundries
        bdX = min([node.xpos() for node in nodeArray])
        bdY = min([node.ypos() for node in nodeArray])
        bdW = max([node.xpos() + node.screenWidth() for node in nodeArray]) - bdX
        bdH = max([node.ypos() + node.screenHeight() for node in nodeArray]) - bdY

        # backdrop boundry offsets
        left, top, right, bottom = (-160, -135, 160, 80)

        # boundry offsets
        bdX += left
        bdY += top
        bdW += right - left
        bdH += bottom - top

        # createbackdrop
        backDrop = nuke.nodes.BackdropNode(
            xpos=bdX,
            bdwidth=bdW,
            ypos=bdY,
            bdheight=bdH,
            tile_color=hexColour,
            note_font_size=nukeBackDropFontSize,
            label="<center><b>" + curPass + "</b><c/enter>",
        )

        # increment position
        self.nukeYPos += nukeBeautyYDistance

        # current nukeIdxNode
        self.nukeIdxNode = curReadNode

    @err_catcher(name=__name__)
    def createComponentPass(
        self,
        origin,
        filePath,
        firstFrame,
        lastFrame,
        curPass,
        nukeXPos,
        nukeSetupWidth,
        nukeSetupHeight,
        nukeBackDropFontSize,
        nukeYDistance,
    ):

        curReadNode = nuke.createNode(
            "Read",
            'file "%s" first %s last %s origfirst %s origlast %s'
            % (filePath, firstFrame, lastFrame, firstFrame, lastFrame),
            False,
        )
        mergeNode1 = nuke.createNode("Merge", "operation difference", False)
        dotNode = nuke.createNode("Dot", "", False)
        dotNodeCorner = nuke.createNode("Dot", "", False)
        mergeNode2 = nuke.createNode("Merge", "operation plus", False)

        nodeArray = [curReadNode, dotNode, mergeNode1, mergeNode2, dotNodeCorner]

        # positions
        curReadNode.setYpos(self.nukeYPos)
        curReadNode.setXpos(nukeXPos)

        curReadNodeWidth = int(curReadNode.screenWidth() * 0.5 - 6)
        curReadNodeHeight = int(curReadNode.screenHeight() * 0.5 - 3)

        mergeNode1.setYpos(self.nukeYPos + curReadNodeHeight)
        mergeNode1.setXpos(nukeXPos + nukeSetupWidth)

        dotNode.setYpos(
            self.nukeYPos + curReadNodeHeight + int(curReadNode.screenWidth() * 0.7)
        )
        dotNode.setXpos(nukeXPos + curReadNodeWidth)

        dotNodeCorner.setYpos(self.nukeYPos + nukeSetupHeight)
        dotNodeCorner.setXpos(nukeXPos + curReadNodeWidth)

        mergeNode2.setYpos(self.nukeYPos + nukeSetupHeight - 4)
        mergeNode2.setXpos(nukeXPos + nukeSetupWidth)

        # #inputs
        mergeNode1.setInput(1, curReadNode)
        dotNode.setInput(0, curReadNode)
        dotNodeCorner.setInput(0, dotNode)
        mergeNode2.setInput(1, dotNodeCorner)
        mergeNode2.setInput(0, mergeNode1)

        if self.nukeIdxNode != None:
            mergeNode1.setInput(0, self.nukeIdxNode)

        # backdrop boundry offsets
        left, top, right, bottom = (-10, -125, 100, 50)

        # backdropcolor
        r = (float(random.randint(30 + int((self.nukeYPos / 3) % 3), 80))) / 100
        g = (float(random.randint(20 + int((self.nukeYPos / 3) % 3), 80))) / 100
        b = (float(random.randint(15 + int((self.nukeYPos / 3) % 3), 80))) / 100
        hexColour = int("%02x%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255), 1), 16)

        # backdrop boundries
        bdX = min([node.xpos() for node in nodeArray])
        bdY = min([node.ypos() for node in nodeArray])
        bdW = max([node.xpos() + node.screenWidth() for node in nodeArray]) - bdX
        bdH = max([node.ypos() + node.screenHeight() for node in nodeArray]) - bdY

        # boundry offsets
        bdX += left
        bdY += top
        bdW += right - left
        bdH += bottom - top

        # createbackdrop
        backDrop = nuke.nodes.BackdropNode(
            xpos=bdX,
            bdwidth=bdW,
            ypos=bdY,
            bdheight=bdH,
            tile_color=hexColour,
            note_font_size=nukeBackDropFontSize,
            label="<b>" + curPass + "</b>",
        )

        # increment position
        self.nukeYPos += nukeYDistance

        # current nukeIdxNode
        self.nukeIdxNode = mergeNode2

    @err_catcher(name=__name__)
    def createMaskPass(
        self, origin, filePath, firstFrame, lastFrame, nukeXPos, nukeSetupWidth, idx
    ):

        curReadNode = nuke.createNode(
            "Read",
            'file "%s" first %s last %s origfirst %s origlast %s'
            % (filePath, firstFrame, lastFrame, firstFrame, lastFrame),
            False,
        )
        curReadNode.setYpos(0)
        curReadNode.setXpos(nukeXPos + nukeSetupWidth + 500 + idx * 350)

        val = 0.5
        r = int("%02x%02x%02x%02x" % (int(val * 255), 0, 0, 1), 16)
        g = int("%02x%02x%02x%02x" % (0, int(val * 255), 0, 1), 16)
        b = int("%02x%02x%02x%02x" % (0, 0, int(val * 255), 1), 16)

        created = False
        if "cryptomatte" in os.path.basename(filePath):
            try:
                cmatte = nuke.createNode("Cryptomatte", inpanel=False)
            except:
                pass
            else:
                created = True
                cmatte.setInput(0, curReadNode)
                self.maskNodes.append(curReadNode)
                self.maskNodes.append(cmatte)

        if not created:
            redShuffle = nuke.createNode(
                "Shuffle", "red red blue red green red alpha red", inpanel=False
            )
            greenShuffle = nuke.createNode(
                "Shuffle", "red green blue green green green alpha green", inpanel=False
            )
            blueShuffle = nuke.createNode(
                "Shuffle", "red blue blue blue green blue alpha blue", inpanel=False
            )

            redShuffle["tile_color"].setValue(r)
            greenShuffle["tile_color"].setValue(g)
            blueShuffle["tile_color"].setValue(b)

            redShuffle.setInput(0, curReadNode)
            greenShuffle.setInput(0, curReadNode)
            blueShuffle.setInput(0, curReadNode)

            redShuffle.setXpos(redShuffle.xpos() - 110)
            # 	greenShuffle.setXpos(greenShuffle.xpos()-110)
            blueShuffle.setXpos(blueShuffle.xpos() + 110)

            self.maskNodes.append(curReadNode)
            self.maskNodes.append(redShuffle)
            self.maskNodes.append(greenShuffle)
            self.maskNodes.append(blueShuffle)

    @err_catcher(name=__name__)
    def createUtilityPass(
        self, origin, filePath, firstFrame, lastFrame, nukeXPos, nukeSetupWidth, idx
    ):

        curReadNode = nuke.createNode(
            "Read",
            'file "%s" first %s last %s origfirst %s origlast %s'
            % (filePath, firstFrame, lastFrame, firstFrame, lastFrame),
            False,
        )
        curReadNode.setYpos(0)
        curReadNode.setXpos(nukeXPos + nukeSetupWidth + 500 + idx * 100)
        try:
            curReadNode.setXpos(
                curReadNode.xpos()
                + self.maskNodes[-1].xpos()
                - nukeXPos
                - nukeSetupWidth
            )
        except:
            pass

        self.utilityNodes.append(curReadNode)

    @err_catcher(name=__name__)
    def postSaveScene(self, origin, filepath, versionUp, comment, isPublish, details):
        """
        origin:     PrismCore instance
        filepath:   The filepath of the scenefile, which was saved
        versionUp:  (bool) True if this save increments the version of that scenefile
        comment:    The string, which is used as the comment for the scenefile. Empty string if no comment was given.
        isPublish:  (bool) True if this save was triggered by a publish
        """
        self.refreshWriteNodes()

    @err_catcher(name=__name__)
    def refreshWriteNodes(self):
        for node in nuke.allNodes():
            nodeClass = node.Class()

            if nodeClass == "WritePrism":
                node.knob("refresh").execute()

    @err_catcher(name=__name__)
    def readGizmoCreated(self):
        pass

    @err_catcher(name=__name__)
    def writeGizmoCreated(self):
        self.getOutputPath(nuke.thisNode(), nuke.thisGroup())

        cmd = "try:\n\tpcore.getPlugin(\"Nuke\").updateNodeUI(\"writePrism\", nuke.toNode(nuke.thisNode().fullName().rsplit(\".\", 1)[0]))\nexcept:\n\tpass"
        nuke.thisNode().node("WritePrismBase").knob("knobChanged").setValue(cmd)

    @err_catcher(name=__name__)
    def updateNodeUI(self, nodeType, node):
        if not nuke.env.get("gui"):
            return

        if nodeType == "writePrism":
            locations = self.core.paths.getRenderProductBasePaths()
            locNames = list(locations.keys())
            try:
                node.knob("location").setValues(locNames)
            except:
                pass

            base = node.node("WritePrismBase")
            if base:
                knobs = base.knobs()
                node.knobs()["datatype"].setVisible(bool(knobs.get("datatype")))
                node.knobs()["compression"].setVisible(bool(knobs.get("compression")))

    @err_catcher(name=__name__)
    def sm_render_getDeadlineParams(self, origin, dlParams, homeDir):
        dlParams["jobInfoFile"] = os.path.join(homeDir, "temp", "nuke_submit_info.job")
        dlParams["pluginInfoFile"] = os.path.join(
            homeDir, "temp", "nuke_plugin_info.job"
        )

        dlParams["jobInfos"]["Plugin"] = "Nuke"
        dlParams["jobInfos"]["Comment"] = "Prism-Submission-Nuke_ImageRender"
        self.core.getPlugin("Deadline").addEnvironmentItem(
            dlParams["jobInfos"],
            "PRISM_NUKE_TERMINAL_FILES",
            os.path.abspath(__file__)
        )

        dlParams["pluginInfos"]["Version"] = self.getAppVersion(origin).split("v")[0]
        dlParams["pluginInfos"]["OutputFilePath"] = os.path.split(
            dlParams["jobInfos"]["OutputFilename0"]
        )[0]
        dlParams["pluginInfos"]["OutputFilePrefix"] = os.path.splitext(
            os.path.basename(dlParams["jobInfos"]["OutputFilename0"])
        )[0]
        dlParams["pluginInfos"]["WriteNode"] = origin.node.fullName()

    @err_catcher(name=__name__)
    def openFarmSubmitter(self, node, group):
        taskName = self.getIdentifierFromNode(group)

        if taskName is None or taskName == "":
            self.core.popup("Please choose an identifier")
            return

        fileName = self.getOutputPath(node, group)

        if fileName == "FileNotInPipeline":
            self.core.showFileNotInProjectWarning(title="Warning")
            return

        sm = self.core.getStateManager()
        state = sm.createState("ImageRender")
        state.ui.mediaType = "2drenders"
        if not state.ui.cb_manager.count():
            msg = "No farm submitter is installed."
            self.core.popup(msg)
            return

        state.ui.setTaskname(self.getIdentifierFromNode(group))
        fmt = "." + group.knob("file_type").value()
        if state.ui.cb_format.findText(fmt) == -1:
            state.ui.cb_format.addItem(fmt)

        state.ui.setFormat(fmt)
        state.ui.node = node
        self.submitter = Farm_Submitter(self, state)
        self.submitter.show()

    @err_catcher(name=__name__)
    def openInClicked(self, node, group):
        path = group.knob("prevFileName").value()
        if path == "None":
            return
        
        menu = QMenu()

        act_play = QAction("Play")
        act_play.triggered.connect(lambda: self.core.media.playMediaInExternalPlayer(path))
        menu.addAction(act_play)

        act_browser = QAction("Open in Media Browser")
        act_browser.triggered.connect(lambda: self.openInMediaBrowser(path))
        menu.addAction(act_browser)

        act_open = QAction("Open in explorer")
        act_open.triggered.connect(lambda: self.core.openFolder(path))
        menu.addAction(act_open)

        act_copy = QAction("Copy")
        act_copy.triggered.connect(lambda: self.core.copyToClipboard(path, file=True))
        menu.addAction(act_copy)

        menu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def openInMediaBrowser(self, path):
        self.core.projectBrowser()
        self.core.pb.showTab("Media")
        data = self.core.paths.getRenderProductData(path, mediaType="2drenders")
        self.core.pb.mediaBrowser.showRender(entity=data, identifier=data.get("identifier", "") + " (2d)", version=data.get("version"))

    @err_catcher(name=__name__)
    def sm_getExternalFiles(self, origin):
        extFiles = []
        return [extFiles, []]

    @err_catcher(name=__name__)
    def sm_render_preExecute(self, origin):
        warnings = []
        return warnings

    @err_catcher(name=__name__)
    def sm_render_preSubmit(self, origin, rSettings):
        pass

    @err_catcher(name=__name__)
    def sm_render_undoRenderSettings(self, origin, rSettings):
        pass

    @err_catcher(name=__name__)
    def captureViewportThumbnail(self):
        if "fnFlipbookRenderer" not in globals():
            logger.debug("failed to capture thumbnail because the \"fnFlipbookRenderer\" module isn't available.")
            return

        path = tempfile.NamedTemporaryFile(suffix=".jpg").name
        viewer = nuke.activeViewer()
        if not viewer:
            return

        inputNr = viewer.activeInput()
        if inputNr is None:
            return

        inputNode = viewer.node().input(inputNr)
        dlg = renderdialog._getFlipbookDialog(inputNode)
        factory = flipbooking.gFlipbookFactory
        names = factory.getNames()
        flipbook = factory.getApplication(names[0])

        fb = PrismRenderedFlipbook(dlg, flipbook)
        fb.doFlipbook(path.replace("\\", "/"), self.getCurrentFrame())
        pm = self.core.media.getPixmapFromPath(path)
        try:
            os.remove(path)
        except:
            pass

        return pm


if nuke.env.get("gui") and "fnFlipbookRenderer" in globals():
    class PrismRenderedFlipbook(fnFlipbookRenderer.SynchronousRenderedFlipbook):

        def __init__(self, flipbookDialog, flipbookToRun):
            fnFlipbookRenderer.SynchronousRenderedFlipbook.__init__(self, flipbookDialog, flipbookToRun)

        def doFlipbook(self, outputpath, frame):
            self.initializeFlipbookNode()
            self.renderFlipbookNode(outputpath, frame)

        def renderFlipbookNode(self, outputpath, frame):
            self._writeNode['file'].setValue(outputpath)
            self._writeNode['file_type'].setValue("jpeg")
            curSpace = self._writeNode['colorspace'].value()
            result = self._writeNode['colorspace'].setValue("sRGB")
            if not result:
                result = self._writeNode['colorspace'].setValue("Output - sRGB")
                if not result:
                    self._writeNode['colorspace'].setValue(curSpace)

            frange = nuke.FrameRanges(str(int(frame)))
            try:
                frameRange, views = self.getFlipbookOptions()
                nuke.executeMultiple(
                    (self._writeNode,),
                    frange,
                    views,
                    self._flipbookDialog._continueOnError.value()
                )
            except Exception as msg:
                import traceback
                print(traceback.format_exc())
                nuke.delete(self._nodeToFlipbook)
                self._nodeToFlipbook = None
                if msg.args[0][0:9] != "Cancelled":
                    nuke.message("Flipbook render failed:\n%s" % (msg.args[0],))
            finally:
                nuke.delete(self._nodeToFlipbook)
                self._nodeToFlipbook = None


class Farm_Submitter(QDialog):
    def __init__(self, plugin, state):
        super(Farm_Submitter, self).__init__()
        self.plugin = plugin
        self.core = self.plugin.core
        self.core.parentWindow(self)
        self.state = state
        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self):
        self.setWindowTitle("Prism Farm Submitter - %s" % self.state.ui.node.fullName())
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.addWidget(self.state.ui)
        self.state.ui.f_name.setVisible(False)
        self.state.ui.w_master.setVisible(False)
        self.state.ui.w_format.setVisible(False)
        self.state.ui.f_taskname.setVisible(False)
        self.state.ui.f_resolution.setVisible(False)
        self.state.ui.gb_passes.setHidden(True)
        self.state.ui.gb_previous.setHidden(True)
        self.state.ui.gb_submit.setChecked(True)
        self.state.ui.gb_submit.setCheckable(False)
        self.state.ui.f_cam.setVisible(False)
        if self.state.ui.cb_manager.count() == 1:
            self.state.ui.f_manager.setVisible(False)
            self.state.ui.gb_submit.setTitle(self.state.ui.cb_manager.currentText())

        self.lo_main.addStretch()
        self.b_submit = QPushButton("Submit")
        self.lo_main.addWidget(self.b_submit)
        self.b_submit.clicked.connect(self.submit)

    @err_catcher(name=__name__)
    def submit(self):
        self.hide()
        self.state.ui.gb_submit.setCheckable(True)
        self.state.ui.gb_submit.setChecked(True)

        sm = self.core.getStateManager()
        result = sm.publish(successPopup=False, executeState=True, states=[self.state])
        sm.deleteState(self.state)
        if result:
            msg = "Job submitted successfully."
            self.core.popup(msg, severity="info")

        self.close()


class Prism_NoQt(object):
    def __init__(self):
        self.addPluginPaths()

    def addPluginPaths(self):
        gdir = os.path.join(
            os.path.abspath(os.path.dirname(os.path.dirname(__file__))), "Gizmos"
        )
        gdir = gdir.replace("\\", "/")
        nuke.pluginAddPath(gdir)


class VersionDlg(QDialog):

    versionSelected = Signal(object)

    def __init__(self, parent, node, group):
        super(VersionDlg, self).__init__()
        self.plugin = parent
        self.core = self.plugin.core
        self.node = node
        self.group = group
        self.isValid = False
        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self):
        filepath = self.core.getCurrentFileName()
        entity = self.core.getScenefileData(filepath)
        if not entity or not entity.get("type"):
            msg = "Please save your scene in the Prism project first."
            self.core.popup(msg)
            return

        identifier = self.plugin.getIdentifierFromNode(self.group)
        if not identifier:
            msg = "Please enter an identifier in the settings of this node first."
            self.core.popup(msg)
            return

        if entity.get("type") == "asset":
            entityName = entity["asset_path"]
        elif entity.get("type") == "shot":
            entityName = self.core.entities.getShotName(entity)

        title = "Select version (%s - %s)" % (entityName, identifier)

        self.setWindowTitle(title)
        self.core.parentWindow(self)

        import MediaBrowser
        self.w_browser = MediaBrowser.MediaBrowser(core=self.core)
        self.w_browser.headerHeightSet = True
        self.w_browser.w_entities.setVisible(False)
        self.w_browser.w_identifier.setVisible(False)
        self.w_browser.lw_version.itemDoubleClicked.disconnect()
        self.w_browser.lw_version.itemDoubleClicked.connect(self.itemDoubleClicked)

        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Render as selected version", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Cancel", QDialogButtonBox.RejectRole)

        self.bb_main.clicked.connect(self.buttonClicked)

        self.lo_main.addWidget(self.w_browser)
        self.lo_main.addWidget(self.bb_main)

        self.w_browser.navigate([entity, identifier + " (2d)"])
        idf = self.w_browser.getCurrentIdentifier()
        if idf["identifier"] != identifier:
            msg = "The identifier \"%s\" doesn't exist yet." % identifier
            self.core.popup(msg)
            return

        self.isValid = self.w_browser.lw_version.count() > 0
        if not self.isValid:
            msg = "No version exists under the current identifier."
            self.core.popup(msg)
            return

    @err_catcher(name=__name__)
    def itemDoubleClicked(self, item):
        self.buttonClicked("select")

    @err_catcher(name=__name__)
    def buttonClicked(self, button):
        if button == "select" or button.text() == "Render as selected version":
            version = self.w_browser.getCurrentVersion()
            if not version:
                msg = "Invalid version selected."
                self.core.popup(msg, parent=self)
                return

            self.versionSelected.emit(version["version"])

        self.close()


class ReadMediaDialog(QDialog):

    mediaSelected = Signal(object)

    def __init__(self, parent, node):
        super(ReadMediaDialog, self).__init__()
        self.plugin = parent
        self.core = self.plugin.core
        self.node = node
        self.isValid = False
        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self):
        filepath = self.core.getCurrentFileName()
        entity = self.core.getScenefileData(filepath)
        title = "Select Media"
        self.setWindowTitle(title)
        self.core.parentWindow(self)

        import MediaBrowser
        self.w_browser = MediaBrowser.MediaBrowser(core=self.core)
        self.w_browser.headerHeightSet = True
        self.w_browser.lw_version.itemDoubleClicked.disconnect()
        self.w_browser.lw_version.itemDoubleClicked.connect(self.itemDoubleClicked)

        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Open", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Cancel", QDialogButtonBox.RejectRole)

        self.bb_main.clicked.connect(self.buttonClicked)

        self.lo_main.addWidget(self.w_browser)
        self.lo_main.addWidget(self.bb_main)

        self.w_browser.navigate([entity])

    @err_catcher(name=__name__)
    def itemDoubleClicked(self, item):
        self.buttonClicked("select")

    @err_catcher(name=__name__)
    def buttonClicked(self, button):
        if button == "select" or button.text() == "Open":
            data = self.w_browser.getCurrentSource()
            if not data:
                data = self.w_browser.getCurrentAOV()
                if not data:
                    data = self.w_browser.getCurrentVersion()
                    if not data:
                        data = self.w_browser.getCurrentIdentifier()

            if not data:
                msg = "Invalid version selected."
                self.core.popup(msg, parent=self)
                return

            self.mediaSelected.emit(data)

        self.close()
