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

import NatronEngine
import NatronGui

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

from PrismUtils.Decorators import err_catcher as err_catcher


class Prism_Natron_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

    @err_catcher(name=__name__)
    def instantStartup(self, origin):
        NatronGui.natron.addMenuCommand("Prism/Save Version", "pcore.saveScene")
        NatronGui.natron.addMenuCommand("Prism/Save Comment", "pcore.saveWithComment")
        NatronGui.natron.addMenuCommand("Prism/Project Browser", "pcore.projectBrowser")
        NatronGui.natron.addMenuCommand(
            "Prism/Update selected read nodes", "pcore.appPlugin.updateNatronNodes"
        )
        NatronGui.natron.addMenuCommand("Prism/Settings", "pcore.prismSettings")

    @err_catcher(name=__name__)
    def startup(self, origin):
        for obj in QApplication.topLevelWidgets():
            if (
                obj.inherits("QMainWindow")
                and obj.metaObject().className() == "Gui"
                and "Natron" in obj.windowTitle()
            ):
                natronQtParent = obj
                break
        else:
            return False

        origin.messageParent = QWidget()
        origin.messageParent.setParent(natronQtParent, Qt.Window)
        origin.timer.stop()

        if platform.system() == "Darwin":
            if self.core.useOnTop:
                origin.messageParent.setWindowFlags(
                    origin.messageParent.windowFlags() ^ Qt.WindowStaysOnTopHint
                )

        # else:
        # 	origin.messageParent = QWidget()

        # 	with open("D:/tst.txt", "a") as l:
        # 		l.write("\nn2")

        # 	toolbar = natron.toolbar("Nodes")
        # 	iconPath = os.path.join(origin.prismRoot, "Scripts", "UserInterfacesPrism", "p_tray.png")
        # 	toolbar.addMenu( 'Prism', icon=iconPath )
        # 	toolbar.addCommand( "Prism/WritePrism", lambda: natron.createNode('WritePrism'))

        # 	natron.addOnScriptLoad(origin.sceneOpen)

        ss = QApplication.instance().styleSheet()
        ss += QApplication.instance().styleSheet().replace("QTreeWidget", "QListWidget")
        ss += QApplication.instance().styleSheet().replace("QTreeWidget", "QTreeView")
        ss += QApplication.instance().styleSheet().replace("QTreeWidget", "QTableView")
        ss += QApplication.instance().styleSheet().replace("QTreeWidget", "QListView")
        ss += (
            QApplication.instance()
            .styleSheet()
            .replace("QTreeView,", "QTreeView, QTableView,")
        )
        origin.messageParent.setStyleSheet(ss)

        self.isRendering = [False, ""]
        self.useLastVersion = False
        self.natronApp = NatronEngine.natron.getInstance(0)

    @err_catcher(name=__name__)
    def onProjectChanged(self, origin):
        pass

    @err_catcher(name=__name__)
    def sceneOpen(self, origin):
        if hasattr(origin, "asThread") and origin.asThread.isRunning():
            origin.startasThread()

    @err_catcher(name=__name__)
    def executeScript(self, origin, code, preventError=False):
        if preventError:
            try:
                return eval(code)
            except Exception as e:
                msg = "\npython code:\n%s" % code
                exec("raise type(e), type(e)(e.message + msg), sys.exc_info()[2]")
        else:
            return eval(code)

    @err_catcher(name=__name__)
    def getCurrentFileName(self, origin, path=True):
        try:
            pPath = NatronEngine.App.getProjectParam(
                self.natronApp, "projectPath"
            ).get()
            pName = NatronEngine.App.getProjectParam(
                self.natronApp, "projectName"
            ).get()

            currentFileName = pPath + pName
        except:
            currentFileName = ""

        return currentFileName

    @err_catcher(name=__name__)
    def getSceneExtension(self, origin):
        return self.sceneFormats[0]

    @err_catcher(name=__name__)
    def saveScene(self, origin, filepath, details={}):
        try:
            return NatronEngine.App.saveProjectAs(self.natronApp, filepath)
        except:
            return ""

    @err_catcher(name=__name__)
    def getImportPaths(self, origin):
        return False

    @err_catcher(name=__name__)
    def getFrameRange(self, origin):
        startframe = (
            NatronEngine.App.getProjectParam(self.natronApp, "frameRange").get().x
        )
        endframe = (
            NatronEngine.App.getProjectParam(self.natronApp, "frameRange").get().y
        )

        return [startframe, endframe]

    @err_catcher(name=__name__)
    def setFrameRange(self, origin, startFrame, endFrame):
        NatronEngine.App.getProjectParam(self.natronApp, "frameRange").set(
            startFrame, endFrame
        )

    @err_catcher(name=__name__)
    def getFPS(self, origin):
        return NatronEngine.App.getProjectParam(self.natronApp, "frameRate").get()

    @err_catcher(name=__name__)
    def setFPS(self, origin, fps):
        return NatronEngine.App.getProjectParam(self.natronApp, "frameRate").set(fps)

    @err_catcher(name=__name__)
    def updateNatronNodes(self):
        updatedNodes = []

        selNodes = NatronGui.natron.getGuiInstance(
            self.natronApp.getAppID()
        ).getSelectedNodes()
        for i in selNodes:
            if str(i.getPluginID()) != "fr.inria.built-in.Read":
                continue

            curPath = i.getParam("filename").get()

            newPath = self.core.getLatestCompositingVersion(curPath)

            if os.path.exists(os.path.dirname(newPath)) and not curPath.startswith(
                os.path.dirname(newPath)
            ):
                i.getParam("filename").set(newPath)
                updatedNodes.append(i)

        if len(updatedNodes) == 0:
            QMessageBox.information(
                self.core.messageParent, "Information", "No nodes were updated"
            )
        else:
            mStr = "%s nodes were updated:\n\n" % len(updatedNodes)
            for i in updatedNodes:
                mStr += i.getScriptName() + "\n"

            QMessageBox.information(self.core.messageParent, "Information", mStr)

    @err_catcher(name=__name__)
    def getAppVersion(self, origin):
        return NatronEngine.natron.getNatronVersionString()

    @err_catcher(name=__name__)
    def onProjectBrowserStartup(self, origin):
        origin.actionStateManager.setEnabled(False)

    @err_catcher(name=__name__)
    def projectBrower_loadLibs(self, origin):
        pass

    @err_catcher(name=__name__)
    def openScene(self, origin, filepath, force=False):
        if os.path.splitext(filepath)[1] not in self.sceneFormats:
            return False

        if NatronEngine.App.resetProject(self.natronApp):
            NatronEngine.App.loadProject(self.natronApp, filepath)

        return True

    @err_catcher(name=__name__)
    def correctExt(self, origin, lfilepath):
        return lfilepath

    @err_catcher(name=__name__)
    def setSaveColor(self, origin, btn):
        btn.setPalette(origin.savedPalette)

    @err_catcher(name=__name__)
    def clearSaveColor(self, origin, btn):
        btn.setPalette(origin.oldPalette)

    @err_catcher(name=__name__)
    def importImages(self, origin):
        fString = "Please select an import option:"
        msg = QMessageBox(
            QMessageBox.NoIcon, "Natron Import", fString, QMessageBox.Cancel
        )
        msg.addButton("Current pass", QMessageBox.YesRole)
        msg.addButton("All passes", QMessageBox.YesRole)
        # 	msg.addButton("Layout all passes", QMessageBox.YesRole)
        self.core.parentWindow(msg)
        action = msg.exec_()

        if action == 0:
            self.natronImportSource(origin)
        elif action == 1:
            self.natronImportPasses(origin)
        else:
            return

    @err_catcher(name=__name__)
    def natronImportSource(self, origin):
        sourceData = origin.compGetImportSource()

        for i in sourceData:
            self.natronApp.createReader(i[0])

    @err_catcher(name=__name__)
    def natronImportPasses(self, origin):
        sourceData = origin.compGetImportPasses()

        for i in sourceData:
            self.natronApp.createReader(i[0])

    @err_catcher(name=__name__)
    def setProject_loading(self, origin):
        pass

    @err_catcher(name=__name__)
    def onPrismSettingsOpen(self, origin):
        pass

    @err_catcher(name=__name__)
    def createProject_startup(self, origin):
        pass

    @err_catcher(name=__name__)
    def editShot_startup(self, origin):
        pass

    @err_catcher(name=__name__)
    def editShot_loadLibs(self, origin):
        pass

    @err_catcher(name=__name__)
    def projectBrower_loadLibs(self, origin):
        pass

    @err_catcher(name=__name__)
    def shotgunPublish_startup(self, origin):
        pass

    def wpParamChanged(
        self, thisParam=None, thisNode=None, thisGroup=None, app=None, userEdited=None
    ):
        if not hasattr(thisNode, "refresh"):
            return

        if app is not None:
            self.natronApp = app

        if thisParam == thisNode.refresh:
            self.getOutputPath(thisNode.getNode("WritePrismBase"), thisNode)
        elif thisParam == thisNode.createDir:
            self.core.createFolder(
                os.path.dirname(thisNode.getParam("fileName").get()), showMessage=True
            )
        elif thisParam == thisNode.openDir:
            self.core.openFolder(os.path.dirname(thisNode.getParam("fileName").get()))
        elif thisParam == thisNode.b_startRender:
            self.startRender(thisNode.getNode("WritePrismBase"), thisNode)
        elif thisParam == thisNode.b_startRenderLastVersion:
            self.startRender(
                thisNode.getNode("WritePrismBase"), thisNode, useLastVersion=True
            )
        elif thisParam == thisNode.WritePrismBaseframeRange:
            self.wpRangeChanged(thisNode.getNode("WritePrismBase"), thisNode)

    @err_catcher(name=__name__)
    def getOutputPath(self, node, group=None, app=None, render=False):
        if app is not None:
            self.natronApp = app

        self.isRendering = [False, ""]

        try:
            taskName = group.getParam("prismTask").get()
            fileType = group.getParam("outputFormat").getOption(
                group.getParam("outputFormat").get()
            )
            saveLocal = group.getParam("localOutput").get()
        except:
            return ""

        if self.core.useLocalFiles and saveLocal:
            location = "local"
        else:
            location = "global"

        outputName = self.core.getCompositingOut(
            taskName, fileType, self.useLastVersion, render, location
        )

        group.getParam("fileName").set(outputName)
        node.getParam("filename").set(outputName)

        return outputName

    @err_catcher(name=__name__)
    def startRender(self, node, group, useLastVersion=False):
        taskName = group.getParam("prismTask").get()

        if taskName is None or taskName == "":
            QMessageBox.warning(
                self.core.messageParent, "Warning", "Please choose a taskname"
            )
            return

        if useLastVersion:
            msg = QMessageBox(
                QMessageBox.Information,
                "Render",
                "Are you sure you want to execute this state as the previous version?\nThis may overwrite existing files.",
                QMessageBox.Cancel,
            )
            msg.addButton("Continue", QMessageBox.YesRole)
            self.core.parentWindow(msg)
            action = msg.exec_()

            if action != 0:
                return

            self.useLastVersion = True
        else:
            self.useLastVersion = False

        fileName = self.getOutputPath(node, group, render=True)

        if fileName == "FileNotInPipeline":
            QMessageBox.warning(
                self.core.messageParent,
                "Warning",
                "The current file is not inside the Pipeline.\nUse the Project Browser to create a file in the Pipeline.",
            )
            return

        self.core.saveScene(versionUp=False)
        node.getParam("startRender").trigger()

        self.useLastVersion = False

    @err_catcher(name=__name__)
    def wpRangeChanged(self, node, group):
        fVisible = group.getParam("WritePrismBaseframeRange").get() == 2

        group.getParam("WritePrismBasefirstFrame").setVisible(fVisible)
        group.getParam("WritePrismBaselastFrame").setVisible(fVisible)
