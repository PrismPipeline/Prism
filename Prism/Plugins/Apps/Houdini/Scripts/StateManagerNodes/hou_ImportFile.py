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

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

import hou

from PrismUtils.Decorators import err_catcher as err_catcher


class ImportFileClass(object):
    className = "ImportFile"
    listType = "Import"

    @err_catcher(name=__name__)
    def setup(
        self, state, core, stateManager, node=None, importPath=None, stateData=None
    ):
        self.state = state
        self.core = core
        self.stateManager = stateManager
        self.taskName = None

        stateNameTemplate = "{entity}_{task}_{version}"
        self.stateNameTemplate = self.core.getConfig("globals", "defaultImportStateName", dft=stateNameTemplate, configPath=self.core.prismIni)
        self.e_name.setText(self.stateNameTemplate)

        # 	self.l_name.setVisible(False)
        # 	self.e_name.setVisible(False)

        self.node = node
        self.fileNode = None
        self.updatePrefUnits()

        self.importHandlers = {
            ".abc": self.importAlembic,
            ".fbx": self.importFBX,
            ".rs": self.importRedshiftProxy,
        }
        self.core.callback("getImportHandlers", args=[self, self.importHandlers])

        createEmptyState = (
            QApplication.keyboardModifiers() == Qt.ControlModifier
            or not self.core.uiAvailable
        )

        if (
            importPath is None
            and stateData is None
            and not createEmptyState
            and not self.stateManager.standalone
        ):
            import TaskSelection

            ts = TaskSelection.TaskSelection(core=core, importState=self)
            self.core.parentWindow(ts)
            if self.core.uiScaleFactor != 1:
                self.core.scaleUI(self.state, sFactor=0.5)
            ts.exec_()

            importPath = ts.productPath

        if importPath:
            self.e_file.setText(importPath)
            result = self.importObject()

            if not result:
                return False
        elif (
            stateData is None
            and not createEmptyState
            and not self.stateManager.standalone
        ):
            return False

        self.nameChanged()
        self.connectEvents()

        if stateData is not None:
            self.loadData(stateData)

        self.updateUi()

    @err_catcher(name=__name__)
    def loadData(self, data):
        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "filepath" in data:
            self.e_file.setText(data["filepath"])
        if "connectednode" in data:
            self.node = hou.node(data["connectednode"])
            if self.node is None:
                self.node = self.findNode(data["connectednode"])
            if self.node and self.node.type().name() == "merge":
                self.node = None
        if "filenode" in data:
            self.fileNode = hou.node(data["filenode"])
            if self.fileNode is None:
                self.fileNode = self.findNode(data["filenode"])
            if self.fileNode and self.fileNode.type().name() == "merge":
                self.fileNode = None
        if "updatepath" in data:
            self.chb_updateOnly.setChecked(eval(data["updatepath"]))
        if "autonamespaces" in data:
            self.chb_autoNameSpaces.setChecked(eval(data["autonamespaces"]))
        if "preferunit" in data:
            self.chb_preferUnit.setChecked(eval(data["preferunit"]))
            self.updatePrefUnits()
        if "autoUpdate" in data:
            self.chb_autoUpdate.setChecked(eval(data["autoUpdate"]))

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
    def connectEvents(self):
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.e_file.editingFinished.connect(self.pathChanged)
        self.b_browse.clicked.connect(self.browse)
        self.b_browse.customContextMenuRequested.connect(self.openFolder)
        self.b_importLatest.clicked.connect(self.importLatest)
        self.chb_autoUpdate.stateChanged.connect(self.autoUpdateChanged)
        self.chb_autoNameSpaces.stateChanged.connect(self.autoNameSpaceChanged)
        self.chb_preferUnit.stateChanged.connect(lambda x: self.updatePrefUnits())
        if not self.stateManager.standalone:
            self.b_goTo.clicked.connect(self.goToNode)
            self.b_import.clicked.connect(self.importObject)
            self.b_objMerge.clicked.connect(self.objMerge)
            self.b_nameSpaces.clicked.connect(self.removeNameSpaces)
            self.b_unitConversion.clicked.connect(self.unitConvert)
            self.chb_updateOnly.stateChanged.connect(
                self.stateManager.saveStatesToScene
            )

    @err_catcher(name=__name__)
    def nameChanged(self, text=None):
        text = self.e_name.text()
        cacheData = self.core.paths.getCachePathData(self.getImportPath())
        num = 0

        try:
            if "{#}" in text:
                while True:
                    cacheData["#"] = num or ""
                    name = text.format(**cacheData)
                    for state in self.stateManager.states:
                        if state.ui.listType != "Import":
                            continue

                        if state is self.state:
                            continue

                        if state.text(0) == name:
                            num += 1
                            break
                    else:
                        break
            else:
                name = text.format(**cacheData)
        except Exception:
            name = text

        self.state.setText(0, name)

    @err_catcher(name=__name__)
    def pathChanged(self):
        self.stateManager.saveImports()
        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def isShotCam(self, path=None):
        if not path:
            path = self.getImportPath()
        return path.endswith(".abc") and "/_ShotCam/" in path

    @err_catcher(name=__name__)
    def autoUpdateChanged(self, checked):
        self.w_latestVersion.setVisible(not checked)
        self.w_importLatest.setVisible(not checked)

        if checked:
            curVersion, latestVersion = self.checkLatestVersion()
            if self.chb_autoUpdate.isChecked():
                if curVersion and latestVersion and curVersion != latestVersion:
                    self.importLatest()

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def browse(self):
        import TaskSelection

        ts = TaskSelection.TaskSelection(core=self.core, importState=self)
        self.core.parentWindow(ts)
        if self.core.uiScaleFactor != 1:
            self.core.scaleUI(self.state, sFactor=0.5)
        ts.exec_()

        if ts.productPath:
            self.e_file.setText(ts.productPath)
            self.importObject()
            self.updateUi()

    @err_catcher(name=__name__)
    def openFolder(self, pos):
        path = hou.expandString(self.e_file.text())
        if os.path.isfile(path):
            path = os.path.dirname(path)

        self.core.openFolder(path)

    @err_catcher(name=__name__)
    def goToNode(self):
        if not self.core.uiAvailable:
            return

        try:
            self.node.name()
        except:
            self.updateUi()
            return False

        if self.node.type().name() == "alembicarchive":
            self.node.setCurrent(True, clear_all_selected=True)
        else:
            self.node.children()[0].setCurrent(True, clear_all_selected=True)

        paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        if paneTab is not None:
            paneTab.setCurrentNode(self.node)
            paneTab.homeToSelection()

    @err_catcher(name=__name__)
    def autoNameSpaceChanged(self, checked):
        self.b_nameSpaces.setEnabled(not checked)
        if not self.stateManager.standalone:
            if checked:
                self.removeNameSpaces()
            self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def getImportPath(self):
        return self.e_file.text().replace("\\", "/")

    @err_catcher(name=__name__)
    def runSanityChecks(self, cachePath):
        result = self.checkFrameRange(cachePath)
        if not result:
            return False

        return True

    @err_catcher(name=__name__)
    def checkFrameRange(self, cachePath):
        versionInfoPath = os.path.join(
            os.path.dirname(os.path.dirname(cachePath)), "versioninfo.yml"
        )
        impFPS = self.core.getConfig("information", "fps", configPath=versionInfoPath)
        curFPS = self.core.getFPS()
        if not impFPS or impFPS == curFPS:
            return True

        fString = (
            "The FPS of the import doesn't match the FPS of the current scene:\n\nCurrent scene FPS:\t%s\nImport FPS:\t\t%s"
            % (curFPS, impFPS)
        )

        result = self.core.popupQuestion(fString, title="FPS mismatch", buttons=["Continue", "Cancel"], icon=QMessageBox.Warning)

        if result == "Cancel":
            return False

        return True

    @err_catcher(name=__name__)
    def convertToPreferredUnit(self, path):
        parDirName = os.path.basename(os.path.dirname(path))
        if parDirName in ["centimeter", "meter"]:
            prefFile = os.path.join(
                os.path.dirname(os.path.dirname(path)),
                self.preferredUnit,
                os.path.basename(path),
            )
            if parDirName == self.unpreferredUnit and os.path.exists(prefFile):
                path = prefFile

        return path

    @err_catcher(name=__name__)
    def importHDA(self, path):
        try:
            self.node.destroy()
        except:
            pass

        if os.path.exists(path):
            hou.hda.installFile(path, force_use_assets=True)

    @err_catcher(name=__name__)
    def importShotCam(self, importPath):
        self.fileNode = None
        self.node = hou.node("/obj").createNode(
            "alembicarchive", "IMPORT_ShotCam"
        )
        self.node.parm("fileName").set(importPath)
        self.node.parm("buildHierarchy").pressButton()
        self.node.moveToGoodPosition()

    @err_catcher(name=__name__)
    def importAlembic(self, importPath, taskName):
        self.fileNode = self.node.createNode("alembic")
        self.fileNode.moveToGoodPosition()
        self.fileNode.parm("fileName").set(importPath)
        self.fileNode.parm("loadmode").set(1)
        self.fileNode.parm("polysoup").set(0)
        self.fileNode.parm("groupnames").set(4)

    @err_catcher(name=__name__)
    def importFBX(self, importPath, taskName):
        self.node.destroy()

        tlSettings = [hou.frame()]
        tlSettings += hou.playbar.playbackRange()

        self.node = hou.hipFile.importFBX(importPath)[0]

        if not self.node:
            self.core.popup("Import failed.")
            self.updateUi()
            self.stateManager.saveStatesToScene()
            return

        self.core.appPlugin.setFrameRange(tlSettings[1], tlSettings[2], tlSettings[0])

        self.node.setName("IMPORT_" + taskName, unique_name=True)
        fbxObjs = [
            x for x in self.node.children() if x.type().name() == "geo"
        ]
        mergeGeo = self.node.createNode("geo", "FBX_Objects")
        mergeGeo.moveToGoodPosition()
        if len(mergeGeo.children()) > 0:
            mergeGeo.children()[0].destroy()
        self.fileNode = mergeGeo.createNode("merge", "Merged_Objects")
        self.fileNode.moveToGoodPosition()
        for i in fbxObjs:
            i.setDisplayFlag(False)
            objmerge = mergeGeo.createNode("object_merge", i.name())
            objmerge.moveToGoodPosition()
            objmerge.parm("objpath1").set(i.path())
            objmerge.parm("xformtype").set(1)
            self.fileNode.setNextInput(objmerge)

        mergeGeo.layoutChildren()
        self.node.layoutChildren()

    @err_catcher(name=__name__)
    def importRedshiftProxy(self, importPath, taskName):
        if not hou.nodeType(hou.sopNodeTypeCategory(), "Redshift_Proxy_Output"):
            msg = "Format is not supported, because Redshift is not available in Houdini."
            self.core.popup(msg)
            self.removeImportNetworkBox()
            try:
                self.node.destroy()
            except:
                pass

            self.fileNode = None
            return

        self.fileNode = self.node.createNode("redshift_proxySOP")
        self.fileNode.moveToGoodPosition()
        self.node.setCurrent(True, clear_all_selected=True)
        hou.hscript("Redshift_objectSpareParameters")
        self.node.parm("RS_objprop_proxy_enable").set(True)
        self.node.parm("RS_objprop_proxy_file").set(importPath)

    @err_catcher(name=__name__)
    def importFile(self, importPath, taskName):
        self.fileNode = self.node.createNode("file")
        self.fileNode.moveToGoodPosition()
        self.fileNode.parm("file").set(importPath)

    @err_catcher(name=__name__)
    def getImportNetworkBox(self, create=True):
        nwBox = hou.node("/obj").findNetworkBox("Import")
        if not nwBox and create:
            nwBox = hou.node("/obj").createNetworkBox("Import")
            nwBox.setComment("Imports")

        return nwBox

    @err_catcher(name=__name__)
    def removeImportNetworkBox(self, force):
        nwBox = self.getImportNetworkBox(create=False)
        if nwBox:
            if not nwBox.nodes() or force:
                nwBox.destroy()

    @err_catcher(name=__name__)
    def createImportNodes(self, importPath, cacheData=None, objMerge=True):
        if self.node is not None:
            try:
                self.node.destroy()
            except:
                pass

        nwBox = self.getImportNetworkBox()

        extension = os.path.splitext(importPath)[1]
        taskName = cacheData.get("task")
        self.taskName = taskName

        if self.isShotCam(importPath):
            self.importShotCam(importPath)
        else:
            self.node = hou.node("/obj").createNode("geo", "IMPORT_" + taskName)
            self.node.moveToGoodPosition()

            if len(self.node.children()) > 0:
                self.node.children()[0].destroy()

            if extension in self.importHandlers:
                self.importHandlers[extension](importPath, taskName)
            else:
                self.importFile(importPath, taskName)

            outNode = self.fileNode.createOutputNode("null", "OUT_" + taskName)
            outNode.setDisplayFlag(True)
            outNode.setRenderFlag(True)

        nwBox.addNode(self.node)
        self.node.moveToGoodPosition()
        nwBox.fitAroundContents()

        self.node.setDisplayFlag(False)
        self.node.setColor(hou.Color(0.451, 0.369, 0.796))

        if self.chb_autoNameSpaces.isChecked():
            self.removeNameSpaces()

        if objMerge and "outNode" in locals():
            self.objMerge()

    @err_catcher(name=__name__)
    def updateImportNodes(self, importPath, cacheData=None):
        prevTaskName = self.node.name().split("IMPORT_")[-1]

        cacheData = cacheData or {}
        taskName = cacheData.get("task")
        if taskName:
            self.node.setName("IMPORT_" + taskName, unique_name=True)
            for child in self.node.children():
                if prevTaskName in child.name():
                    newName = child.name().replace(prevTaskName, taskName)
                    child.setName(newName, unique_name=True)

        extension = os.path.splitext(importPath)[1]
        if extension == ".abc" and "_ShotCam_" in importPath:
            if self.core.appPlugin.setNodeParm(
                self.node, "fileName", val=importPath
            ):
                self.node.parm("buildHierarchy").pressButton()
        elif extension == ".abc":
            self.core.appPlugin.setNodeParm(
                self.fileNode, "fileName", val=importPath
            )
        elif extension == ".usd":
            self.core.appPlugin.setNodeParm(
                self.fileNode, "import_file", val=importPath
            )
        elif extension == ".rs":
            self.core.appPlugin.setNodeParm(
                self.node, "RS_objprop_proxy_file", val=importPath
            )
        else:
            self.core.appPlugin.setNodeParm(
                self.fileNode, "file", val=importPath
            )

    @err_catcher(name=__name__)
    def importObject(self, objMerge=True):
        if self.stateManager.standalone:
            return False

        fileName = self.core.getCurrentFileName()
        impFileName = self.getImportPath()
        impFileName = self.convertToPreferredUnit(impFileName)

        kwargs = {
            "state": self,
            "scenefile": fileName,
            "importfile": impFileName,
        }
        result = self.core.callback("preImport", **kwargs)

        for res in result:
            if res and "importfile" in res:
                impFileName = res["importfile"]
                if not impFileName:
                    return

        if not impFileName:
            self.core.popup("Invalid importpath")
            return

        result = self.runSanityChecks(impFileName)
        if not result:
            return

        cacheData = self.core.paths.getCachePathData(impFileName)
        self.e_file.setText(impFileName)

        try:
            self.node.path()
        except:
            self.node = None
            self.fileNode = None

        extension = os.path.splitext(impFileName)[1]

        doImport = (
            self.node is None
            or (
                self.fileNode is None
                and not (
                    extension == ".abc"
                    and "_ShotCam_" in impFileName
                )
            )
            or not self.chb_updateOnly.isChecked()
            or (
                self.fileNode is not None
                and (self.fileNode.type().name() == "alembic")
                == (extension != ".abc")
            )
            or self.node.type().name() == "subnet"
        )

        if extension == ".hda":
            self.importHDA(impFileName)
        elif doImport:
            self.createImportNodes(impFileName, cacheData, objMerge=objMerge)
        else:
            self.updateImportNodes(impFileName, cacheData)

        impNodes = []
        try:
            curNode = self.node.path()
            impNodes.append(curNode)
        except:
            pass

        try:
            fNode = self.fileNode.path()
            impNodes.append(fNode)
        except:
            pass

        kwargs = {
            "state": self,
            "scenefile": fileName,
            "importfile": impFileName,
            "importedObjects": impNodes,
        }
        self.core.callback("postImport", **kwargs)

        self.stateManager.saveImports()
        self.updateUi()
        self.stateManager.saveStatesToScene()

        return True

    @err_catcher(name=__name__)
    def importLatest(self, refreshUi=True):
        if refreshUi:
            self.updateUi()

        latestVersion = self.core.products.getLatestVersionFromPath(self.getImportPath())
        filepath = self.core.products.getPreferredFileFromVersion(latestVersion, preferredUnit=self.preferredUnit)
        if not filepath:
            self.core.popup("Couldn't get latest version.")
            return

        filepath = getattr(self.core.appPlugin, "fixImportPath", lambda x: x)(filepath)
        self.e_file.setText(filepath)
        self.importObject()

    @err_catcher(name=__name__)
    def objMerge(self):
        if not self.core.uiAvailable:
            return

        paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        if paneTab is None:
            return

        nodePath = paneTab.pwd()

        if nodePath.isInsideLockedHDA():
            return

        if os.path.splitext(self.e_file.text())[1] == ".hda":
            if os.path.exists(self.e_file.text()):
                defs = hou.hda.definitionsInFile(self.e_file.text().replace("\\", "/"))
                if len(defs) > 0:
                    tname = defs[0].nodeTypeName()
                    mNode = None
                    try:
                        mNode = nodePath.createNode(tname)
                        mNode.moveToGoodPosition()
                    except:
                        return
            if mNode is None:
                return
        else:
            try:
                x = self.node.path()
            except:
                return

            mNode = None
            try:
                mNode = nodePath.createNode("object_merge")
                mNode.moveToGoodPosition()
            except:
                return

            outNodePath = ""
            if self.node.type().name() == "subnet":
                for i in self.node.children():
                    if getattr(i, "isDisplayFlagSet", lambda: None)():
                        outNodePath = i.displayNode().path()
                        break
            else:
                outNodePath = self.node.displayNode().path()

            mNode.parm("objpath1").set(outNodePath)

        mNode.setDisplayFlag(True)
        if hasattr(mNode, "setRenderFlag"):
            mNode.setRenderFlag(True)
        mNode.setPosition(paneTab.visibleBounds().center())
        mNode.setCurrent(True, clear_all_selected=True)

    @err_catcher(name=__name__)
    def checkLatestVersion(self):
        path = self.getImportPath()
        curVersionName = self.core.products.getVersionNameFromFilepath(path) or ""
        latestVersion = self.core.products.getLatestVersionFromPath(path)
        latestVersionName = latestVersion["name"] if latestVersion else ""

        return curVersionName, latestVersionName

    @err_catcher(name=__name__)
    def setStateColor(self, status):
        if status == "ok":
            statusColor = QColor(0, 130, 0)
        elif status == "warning":
            statusColor = QColor(150, 80, 0)
        elif status == "error":
            statusColor = QColor(130, 0, 0)
        else:
            statusColor = QColor(0, 0, 0, 0)

        self.statusColor = statusColor

    @err_catcher(name=__name__)
    def updateUi(self):
        if os.path.splitext(self.e_file.text())[1] == ".hda":
            self.gb_options.setVisible(False)
            self.b_goTo.setVisible(False)
            self.b_objMerge.setText("Create Node")
            self.l_status.setText("not installed")
            self.l_status.setStyleSheet("QLabel { background-color : rgb(130,0,0); }")
            status = "error"
            if os.path.exists(self.e_file.text()):
                defs = hou.hda.definitionsInFile(self.e_file.text().replace("\\", "/"))
                if len(defs) > 0:
                    if defs[0].isInstalled():
                        self.l_status.setText("installed")
                        self.l_status.setStyleSheet(
                            "QLabel { background-color : rgb(0,130,0); }"
                        )
                        status = "ok"
        else:
            self.gb_options.setVisible(True)
            self.b_goTo.setVisible(True)
            self.b_objMerge.setText("Create Obj Merge")
            try:
                self.node.name()
                self.l_status.setText(self.node.name())
                self.l_status.setStyleSheet(
                    "QLabel { background-color : rgb(0,130,0); }"
                )
                status = "ok"
                self.b_objMerge.setEnabled(True)
            except:
                self.nameChanged()
                self.l_status.setText("Not found in scene")
                self.l_status.setStyleSheet(
                    "QLabel { background-color : rgb(130,0,0); }"
                )
                status = "error"
                self.b_objMerge.setEnabled(False)

        versions = self.checkLatestVersion()
        if versions:
            curVersion, latestVersion = versions
        else:
            curVersion = latestVersion = ""

        self.l_curVersion.setText(curVersion or "-")
        self.l_latestVersion.setText(latestVersion or "-")

        if self.chb_autoUpdate.isChecked():
            if curVersion and latestVersion and curVersion != latestVersion:
                self.importLatest(refreshUi=False)
        else:
            if curVersion and latestVersion and curVersion != latestVersion:
                self.b_importLatest.setStyleSheet(
                    "QPushButton { background-color : rgb(150,80,0); border: none;}"
                )
                status = "warning"
            else:
                self.b_importLatest.setStyleSheet("")

        self.nameChanged()
        self.setStateColor(status)

        isShotCam = self.isShotCam()
        self.f_nameSpaces.setVisible(not isShotCam)
        self.b_objMerge.setVisible(not isShotCam)

    @err_catcher(name=__name__)
    def getCurrentVersion(self):
        return self.e_file.text().replace("\\", "/")

    @err_catcher(name=__name__)
    def getLatestVersion(self):
        parDir = os.path.dirname(self.e_file.text())
        if os.path.basename(parDir) in ["centimeter", "meter"]:
            versionData = os.path.basename(os.path.dirname(parDir)).split(
                self.core.filenameSeparator
            )
            taskPath = os.path.dirname(os.path.dirname(parDir))
        else:
            versionData = os.path.basename(parDir).split(self.core.filenameSeparator)
            taskPath = os.path.dirname(parDir)

        if (
            len(versionData) == 3
            and self.core.getScenePath().replace(self.core.projectPath, "")
            in self.e_file.text()
        ):
            self.l_curVersion.setText(
                versionData[0]
                + self.core.filenameSeparator
                + versionData[1]
                + self.core.filenameSeparator
                + versionData[2]
            )
            self.l_latestVersion.setText("-")
            for i in os.walk(taskPath):
                folders = i[1]
                folders.sort()
                for k in reversed(folders):
                    meterDir = os.path.join(i[0], k, "meter")
                    cmeterDir = os.path.join(i[0], k, "centimeter")
                    if (
                        len(k.split(self.core.filenameSeparator)) == 3
                        and k[0] == "v"
                        and len(k.split(self.core.filenameSeparator)[0]) == 5
                        and (
                            (os.path.exists(meterDir) and len(os.listdir(meterDir)) > 0)
                            or (
                                os.path.exists(cmeterDir)
                                and len(os.listdir(cmeterDir)) > 0
                            )
                        )
                    ):
                        return os.path.join(i[0], k).replace("\\", "/")
                break

        return ""

    @err_catcher(name=__name__)
    def removeNameSpaces(self):
        outputCons = self.fileNode.outputConnections()

        for i in outputCons:
            if (
                i.outputNode().type().name() == "grouprename"
                and i.outputNode().name() == "RemoveMayaNameSpaces"
            ):
                return

            if (
                i.outputNode().type().name() == "xform"
                and i.outputNode().name() == "UnitConversion"
            ):
                outputConsUnit = i.outputNode().outputConnections()

                for k in outputConsUnit:
                    if (
                        k.outputNode().type().name() == "grouprename"
                        and k.outputNode().name() == "RemoveMayaNameSpaces"
                    ):
                        return

        renameNode = self.fileNode.createOutputNode(
            "grouprename", "RemoveMayaNameSpaces"
        )
        for i in outputCons:
            i.outputNode().setInput(i.inputIndex(), renameNode, 0)

        groups = renameNode.geometry().primGroups()
        renames = 0
        for idx, val in enumerate(groups):
            groupName = val.name()
            newName = groupName.rsplit("_", 1)[-1]
            if newName != groupName:
                renames += 1
                renameNode.parm("renames").set(renames)
                renameNode.parm("group" + str(renames)).set(groupName)
                renameNode.parm("newname" + str(renames)).set(
                    newName + "_" + str(renames)
                )

        self.fileNode.parent().layoutChildren()

    @err_catcher(name=__name__)
    def unitConvert(self):
        if self.isShotCam():
            xforms = [
                x for x in self.node.children() if x.type().name() == "alembicxform"
            ]
            if len(xforms) == 0:
                return

            xNode = xforms[0]

            inputCons = xNode.inputConnections()
            unitNode = xNode.createInputNode(0, "null", "UnitConversion")

            for i in inputCons:
                if i.inputNode() is None:
                    unitNode.setInput(0, i.subnetIndirectInput(), 0)
                else:
                    unitNode.setInput(0, i.inputNode(), 0)

            unitNode.parm("scale").set(0.01)
            self.node.layoutChildren()
        else:
            outputCons = self.fileNode.outputConnections()

            unitNode = None
            for i in outputCons:
                if (
                    i.outputNode().type().name() == "xform"
                    and i.outputNode().name() == "UnitConversion"
                ):
                    unitNode = i.outputNode()

                if (
                    i.outputNode().type().name() == "grouprename"
                    and i.outputNode().name() == "RemoveMayaNameSpaces"
                ):
                    outputConsNS = i.outputNode().outputConnections()

                    for k in outputConsNS:
                        if (
                            k.outputNode().type().name() == "xform"
                            and k.outputNode().name() == "UnitConversion"
                        ):
                            unitNode = k.outputNode()

            if unitNode is None:
                unitNode = self.fileNode.createOutputNode("xform", "UnitConversion")

                for i in outputCons:
                    i.outputNode().setInput(i.inputIndex(), unitNode, 0)

            self.core.appPlugin.setNodeParm(unitNode, "scale", val=0.01)
            self.fileNode.parent().layoutChildren()

    @err_catcher(name=__name__)
    def updatePrefUnits(self):
        if self.chb_preferUnit.isChecked():
            self.preferredUnit = "centimeter"
            self.unpreferredUnit = "meter"
        else:
            self.preferredUnit = "meter"
            self.unpreferredUnit = "centimeter"

    @err_catcher(name=__name__)
    def preDelete(self, item, silent=False):
        self.core.appPlugin.sm_preDelete(self, item, silent)

    @err_catcher(name=__name__)
    def getStateProps(self):
        try:
            curNode = self.node.path()
            self.node.setUserData("PrismPath", curNode)
        except:
            curNode = None

        try:
            fNode = self.fileNode.path()
            self.fileNode.setUserData("PrismPath", fNode)
        except:
            fNode = None

        return {
            "statename": self.e_name.text(),
            "filepath": self.e_file.text(),
            "connectednode": curNode,
            "filenode": fNode,
            "autoUpdate": str(self.chb_autoUpdate.isChecked()),
            "updatepath": str(self.chb_updateOnly.isChecked()),
            "autonamespaces": str(self.chb_autoNameSpaces.isChecked()),
            "preferunit": str(self.chb_preferUnit.isChecked()),
        }
