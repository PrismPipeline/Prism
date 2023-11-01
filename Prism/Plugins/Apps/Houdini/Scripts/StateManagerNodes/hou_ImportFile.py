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
import logging

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

import hou

from PrismUtils.Decorators import err_catcher as err_catcher


logger = logging.getLogger(__name__)


class ImportFileClass(object):
    className = "ImportFile"
    listType = "Import"

    @err_catcher(name=__name__)
    def setup(
        self,
        state,
        core,
        stateManager,
        node=None,
        importPath=None,
        stateData=None,
        openProductsBrowser=True,
    ):
        self.state = state
        self.core = core
        self.stateManager = stateManager
        self.taskName = None

        stateNameTemplate = "{entity}_{product}_{version}"
        self.stateNameTemplate = self.core.getConfig(
            "globals",
            "defaultImportStateName",
            dft=stateNameTemplate,
            configPath=self.core.prismIni,
        )
        self.e_name.setText(self.stateNameTemplate)
        self.l_name.setVisible(False)
        self.e_name.setVisible(False)

        self.node = None
        self.importTarget = None
        self.fileNode = None
        if node:
            self.setNode(node)

        self.importHandlers = {
            ".abc": {"import": self.importAlembic, "update": self.updateImportNodes},
            ".fbx": {"import": self.importFBX, "update": self.updateImportNodes},
            ".rs": {
                "import": self.importRedshiftProxy,
                "update": self.updateImportNodes,
            },
        }
        self.core.callback("getImportHandlers", args=[self, self.importHandlers])
        self.core.callback("onStateStartup", self)

        createEmptyState = (
            QApplication.keyboardModifiers() == Qt.ControlModifier
            or not self.core.uiAvailable
        ) or not openProductsBrowser

        if (
            importPath is None
            and stateData is None
            and not createEmptyState
            and not self.stateManager.standalone
        ):
            import ProductBrowser

            ts = ProductBrowser.ProductBrowser(core=core, importState=self)
            self.core.parentWindow(ts)
            if self.core.uiScaleFactor != 1:
                self.core.scaleUI(self.state, sFactor=0.5)
            ts.exec_()

            importPath = ts.productPath

        if importPath:
            self.setImportPath(importPath)
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
            self.setImportPath(data["filepath"])
        if "connectednode" in data:
            node = hou.node(data["connectednode"])
            if node is None:
                node = self.findNode(data["connectednode"])
            if node and node.type().name() == "merge":
                node = None
            self.setNode(node)
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
        if "autoUpdate" in data:
            self.chb_autoUpdate.setChecked(eval(data["autoUpdate"]))

        self.core.callback("onStateSettingsLoaded", self, data)

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
    def setNode(self, node):
        if not self.core.appPlugin.isNodeValid(self, node):
            return

        self.node = node
        if self.isPrismImportNode(self.node):
            self.importTarget = node.node("IMPORT")
        else:
            self.importTarget = node
            self.node.addEventCallback([hou.nodeEventType.BeingDeleted], self.onNodeDeleted)

    def onNodeDeleted(self, event_type, **kwargs):
        if kwargs["node"] == self.node:
            self.stateManager.deleteState(self.state, silent=True)

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.b_browse.clicked.connect(self.browse)
        self.b_browse.customContextMenuRequested.connect(self.openFolder)
        self.b_importLatest.clicked.connect(self.importLatest)
        self.chb_autoUpdate.stateChanged.connect(self.autoUpdateChanged)
        self.chb_autoNameSpaces.stateChanged.connect(self.autoNameSpaceChanged)
        if not self.stateManager.standalone:
            self.b_goTo.clicked.connect(self.goToNode)
            self.b_import.clicked.connect(self.importObject)
            self.b_objMerge.clicked.connect(self.objMerge)
            self.b_nameSpaces.clicked.connect(self.removeNameSpaces)
            self.chb_updateOnly.stateChanged.connect(
                self.stateManager.saveStatesToScene
            )

    @err_catcher(name=__name__)
    def nameChanged(self, text=None):
        text = self.e_name.text()
        cacheData = self.core.paths.getCachePathData(self.getImportPath())
        if cacheData.get("type") == "asset":
            cacheData["entity"] = os.path.basename(cacheData.get("asset_path", ""))
        elif cacheData.get("type") == "shot" and "sequence" in cacheData:
            shotName = self.core.entities.getShotName(cacheData)
            if shotName:
                cacheData["entity"] = shotName

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
    def getSortKey(self):
        cacheData = self.core.paths.getCachePathData(self.getImportPath())
        return cacheData.get("product")

    @err_catcher(name=__name__)
    def isShotCam(self, path=None):
        if not path:
            path = self.getImportPath()
        return path.endswith(".abc") and "/_ShotCam/" in path

    @err_catcher(name=__name__)
    def isPrismImportNode(self, node):
        if not self.core.appPlugin.isNodeValid(self, node):
            return False

        if node.type().name().startswith("prism::ImportFile"):
            return True

        return False

    @err_catcher(name=__name__)
    def autoUpdateChanged(self, checked):
        self.w_latestVersion.setVisible(not checked)
        self.w_importLatest.setVisible(not checked)

        if checked:
            curVersion, latestVersion = self.checkLatestVersion()
            if self.chb_autoUpdate.isChecked():
                if curVersion.get("version") and latestVersion.get("version") and curVersion["version"] != latestVersion["version"]:
                    self.importLatest()

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def browse(self):
        import ProductBrowser

        ts = ProductBrowser.ProductBrowser(core=self.core, importState=self)
        self.core.parentWindow(ts)
        if self.core.uiScaleFactor != 1:
            self.core.scaleUI(self.state, sFactor=0.5)
        ts.exec_()

        if ts.productPath:
            self.setImportPath(ts.productPath)
            self.importObject()
            self.updateUi()

    @err_catcher(name=__name__)
    def openFolder(self, pos):
        path = hou.text.expandString(self.getImportPath())
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
    def getImportPath(self, expand=True):
        path = getattr(self, "importPath", "")
        if path:
            path = path.replace("\\", "/")

        if expand:
            path = hou.text.expandString(path)

        return path

    @err_catcher(name=__name__)
    def setImportPath(self, path):
        path = self.core.appPlugin.getPathRelativeToProject(path) if self.core.appPlugin.getUseRelativePath() else path
        self.importPath = path
        self.w_currentVersion.setToolTip(path)
        self.stateManager.saveImports()
        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def runSanityChecks(self, cachePath):
        result = self.checkFrameRange(cachePath)
        if not result:
            return False

        return True

    @err_catcher(name=__name__)
    def checkFrameRange(self, cachePath):
        versionInfoPath = self.core.getVersioninfoPath(
            self.core.products.getVersionInfoPathFromProductFilepath(cachePath)
        )

        impFPS = self.core.getConfig("fps", configPath=versionInfoPath)
        curFPS = self.core.getFPS()
        if not impFPS or impFPS == curFPS:
            return True

        fString = (
            "The FPS of the import doesn't match the FPS of the current scene:\n\nCurrent scene FPS:\t%s\nImport FPS:\t\t%s"
            % (curFPS, impFPS)
        )

        result = self.core.popupQuestion(
            fString,
            title="FPS mismatch",
            buttons=["Continue", "Cancel"],
            icon=QMessageBox.Warning,
        )

        if result == "Cancel":
            return False

        return True

    @err_catcher(name=__name__)
    def importHDA(self, path):
        try:
            self.node.destroy()
        except:
            pass

        if os.path.exists(path):
            hou.hda.installFile(path, force_use_assets=True)

    @err_catcher(name=__name__)
    def importShotCam(self, importPath, cacheData=None):
        self.fileNode = None
        entityName = self.core.entities.getEntityName(cacheData)
        node = hou.node("/obj").createNode("alembicarchive", "IMPORT_%s_ShotCam" % entityName, force_valid_node_name=True)
        self.setNode(node)
        parmPath = self.core.appPlugin.getPathRelativeToProject(importPath) if self.core.appPlugin.getUseRelativePath() else importPath
        self.node.parm("fileName").set(parmPath)
        self.node.parm("buildHierarchy").pressButton()
        self.node.moveToGoodPosition()
        self.addNodeToImportNetworkBox(self.node)
        self.loadShotcamResolution(cacheData)

    @err_catcher(name=__name__)
    def loadShotcamResolution(self, cacheData):
        resolution = cacheData.get("resolution") if cacheData else None
        if resolution:
            for node in self.node.allSubChildren():
                if node.type().name() == "cam":
                    self.core.appPlugin.setNodeParm(node, "resx", val=resolution[0])
                    self.core.appPlugin.setNodeParm(node, "resy", val=resolution[1])

    @err_catcher(name=__name__)
    def importAlembic(self, importPath, taskName):
        self.fileNode = self.importTarget.createNode("alembic")
        self.fileNode.moveToGoodPosition()
        parmPath = self.core.appPlugin.getPathRelativeToProject(importPath) if self.core.appPlugin.getUseRelativePath() else importPath
        self.fileNode.parm("fileName").set(parmPath)
        if self.isPrismImportNode(self.node):
            if self.node.parm("groupsAbc").eval():
                self.fileNode.parm("groupnames").set(4)
        else:
            self.fileNode.parm("loadmode").set(1)
            self.fileNode.parm("polysoup").set(0)
            self.fileNode.parm("groupnames").set(4)

    @err_catcher(name=__name__)
    def importFBX(self, importPath, taskName):
        if self.isPrismImportNode(self.node):
            self.importFile(importPath, taskName)
        else:
            self.node.destroy()

            tlSettings = [hou.frame()]
            tlSettings += hou.playbar.playbackRange()

            node = hou.hipFile.importFBX(importPath)[0]
            self.setNode(node)
            self.node.moveToGoodPosition()
            self.addNodeToImportNetworkBox(self.node)

            if not self.node:
                self.core.popup("Import failed.")
                self.updateUi()
                self.stateManager.saveStatesToScene()
                return

            self.core.appPlugin.setFrameRange(
                tlSettings[1], tlSettings[2], tlSettings[0]
            )
            cacheData = self.core.paths.getCachePathData(importPath)
            entityName = (self.core.entities.getEntityName(cacheData) or "").replace("/", "_").replace("\\", "_")
            if entityName:
                nodeName = "IMPORT_%s_%s" % (entityName, taskName)
            else:
                nodeName = "IMPORT_%s" % os.path.splitext(os.path.basename(importPath))[0]

            try:
                self.node.setName(nodeName, unique_name=True)
            except:
                logger.warning("cannot set nodename: %s" % nodeName)

            fbxObjs = [x for x in self.node.children() if x.type().name() == "geo"]
            mergeGeo = self.importTarget.createNode("geo", "FBX_Objects")
            mergeGeo.moveToGoodPosition()
            if len(mergeGeo.children()) > 0:
                mergeGeo.children()[0].destroy()
            self.fileNode = mergeGeo.createNode("merge", "Merged_Objects")
            self.fileNode.moveToGoodPosition()
            for i in fbxObjs:
                i.setDisplayFlag(False)
                objmerge = mergeGeo.createNode("object_merge", i.name(), force_valid_node_name=True)
                objmerge.moveToGoodPosition()
                objmerge.parm("objpath1").set(i.path())
                objmerge.parm("xformtype").set(1)
                namenode = objmerge.createOutputNode("name", "Add_Name_" + i.name())
                namenode.parm("name1").set('`opinput(".", 0)`')
                self.fileNode.setNextInput(namenode)

            mergeGeo.layoutChildren()
            self.node.layoutChildren()

    @err_catcher(name=__name__)
    def importRedshiftProxy(self, importPath, taskName):
        if not hou.nodeType(hou.sopNodeTypeCategory(), "Redshift_Proxy_Output"):
            msg = (
                "Format is not supported, because Redshift is not available in Houdini."
            )
            self.core.popup(msg)
            self.removeImportNetworkBox()
            try:
                self.node.destroy()
            except:
                pass

            self.fileNode = None
            return

        self.fileNode = self.importTarget.createNode("redshift_proxySOP")
        self.fileNode.moveToGoodPosition()
        self.node.setCurrent(True, clear_all_selected=True)
        hou.hscript("Redshift_objectSpareParameters")
        self.node.parm("RS_objprop_proxy_enable").set(True)
        parmPath = self.core.appPlugin.getPathRelativeToProject(importPath) if self.core.appPlugin.getUseRelativePath() else importPath
        self.node.parm("RS_objprop_proxy_file").set(parmPath)

    @err_catcher(name=__name__)
    def importFile(self, importPath, taskName):
        try:
            self.fileNode = self.importTarget.createNode("file")
        except:
            if self.importTarget.isInsideLockedHDA():
                msg = (
                    'Cannot create node inside"%s".\nMake sure the node is set as editable node in youe HDA.'
                    % self.importTarget.path()
                )
                self.core.popup(msg)
                return

        self.fileNode.moveToGoodPosition()
        parmPath = self.core.appPlugin.getPathRelativeToProject(importPath) if self.core.appPlugin.getUseRelativePath() else importPath
        self.fileNode.parm("file").set(parmPath)

    @err_catcher(name=__name__)
    def getImportNetworkBox(self, create=True):
        nwBox = hou.node("/obj").findNetworkBox("Import")
        if not nwBox and create:
            nwBox = hou.node("/obj").createNetworkBox("Import")
            nwBox.setComment("Imports")

        return nwBox

    @err_catcher(name=__name__)
    def addNodeToImportNetworkBox(self, node):
        nwBox = self.getImportNetworkBox()
        nwBox.addNode(node)
        nwBox.fitAroundContents()

        node.setDisplayFlag(False)
        node.setColor(hou.Color(0.451, 0.369, 0.796))

    @err_catcher(name=__name__)
    def removeImportNetworkBox(self, force=False):
        nwBox = self.getImportNetworkBox(create=False)
        if nwBox:
            if not nwBox.nodes() or force:
                nwBox.destroy()

    @err_catcher(name=__name__)
    def createImportNodes(self, importPath, cacheData=None):
        if self.node is not None:
            try:
                self.node.destroy()
            except:
                pass

        if self.isShotCam(importPath):
            return

        self.taskName = cacheData.get("product") or ""
        entityName = self.core.entities.getEntityName(cacheData)
        if entityName:
            nodeName = "IMPORT_%s_%s" % (entityName, self.taskName)
        else:
            nodeName = "IMPORT_%s" % os.path.splitext(os.path.basename(importPath))[0]

        node = hou.node("/obj").createNode("geo", nodeName, force_valid_node_name=True)
        self.setNode(node)
        self.node.moveToGoodPosition()
        self.addNodeToImportNetworkBox(self.node)

    @err_catcher(name=__name__)
    def handleImport(self, importPath, cacheData=None, objMerge=True):
        if self.isShotCam(importPath):
            self.importShotCam(importPath, cacheData)
        else:
            for node in self.importTarget.children():
                try:
                    node.destroy()
                except:
                    self.core.popup(
                        "Import canceled.\nFailed to delete node:\n\n%s" % node.path()
                    )
                    return

            self.taskName = cacheData.get("product") or ""
            extension = os.path.splitext(importPath)[1]
            if extension in self.importHandlers:
                self.importHandlers[extension]["import"](importPath, self.taskName)
            else:
                self.importFile(importPath, self.taskName)

            if not self.core.appPlugin.isNodeValid(self, self.fileNode):
                return

            if self.taskName:
                suffix = self.taskName
            else:
                suffix = os.path.splitext(os.path.basename(importPath))[0]

            outNode = self.fileNode.parent().createNode("null", "OUT_" + suffix, force_valid_node_name=True)
            outNode.setInput(0, self.fileNode)
            outNode.moveToGoodPosition()
            outNode.setDisplayFlag(True)
            outNode.setRenderFlag(True)

        if self.chb_autoNameSpaces.isChecked():
            self.removeNameSpaces()

        if objMerge and "outNode" in locals():
            self.objMerge()

    @err_catcher(name=__name__)
    def handleUpdate(self, importPath, cacheData=None):
        extension = os.path.splitext(importPath)[1]
        if extension in self.importHandlers:
            self.importHandlers[extension]["update"](importPath, cacheData)
        else:
            self.updateImportNodes(importPath, cacheData)

    @err_catcher(name=__name__)
    def updateImportNodes(self, importPath, cacheData=None):
        prevTaskName = self.node.name().split("_")[-1]
        cacheData = cacheData or {}
        taskName = cacheData.get("product")
        if taskName:
            entityName = self.core.entities.getEntityName(cacheData)
            if not self.isPrismImportNode(self.node):
                nodeName = "IMPORT_%s_%s" % (entityName, taskName)
                try:
                    self.node.setName(nodeName, unique_name=True)
                except:
                    logger.warning("cannot set nodename: %s" % nodeName)
                
                for child in self.node.children():
                    if prevTaskName in child.name():
                        newName = child.name().replace(prevTaskName, taskName)
                        try:
                            child.setName(newName, unique_name=True)
                        except:
                            logger.warning("cannot set nodename: %s" % newName)

        extension = os.path.splitext(importPath)[1]
        parmPath = self.core.appPlugin.getPathRelativeToProject(importPath) if self.core.appPlugin.getUseRelativePath() else importPath
        if extension == ".abc" and "_ShotCam_" in parmPath:
            if self.core.appPlugin.setNodeParm(self.node, "fileName", val=parmPath):
                self.node.parm("buildHierarchy").pressButton()
                self.loadShotcamResolution(cacheData)
        elif extension == ".abc":
            self.core.appPlugin.setNodeParm(self.fileNode, "fileName", val=parmPath)
        elif extension == ".usd":
            self.core.appPlugin.setNodeParm(
                self.fileNode, "import_file", val=parmPath
            )
        elif extension == ".rs":
            self.core.appPlugin.setNodeParm(
                self.node, "RS_objprop_proxy_file", val=parmPath
            )
        else:
            pathParm = "file"
            if not self.fileNode.parm(pathParm):
                pathParm = "filepath1"

            self.core.appPlugin.setNodeParm(self.fileNode, pathParm, val=parmPath)

    @err_catcher(name=__name__)
    def importObject(self, objMerge=True):
        if self.stateManager.standalone:
            return False

        fileName = self.core.getCurrentFileName()
        impFileName = self.getImportPath(expand=False)

        kwargs = {
            "state": self,
            "scenefile": fileName,
            "importfile": impFileName,
        }
        result = self.core.callback("preImport", **kwargs)
        for res in result:
            if isinstance(res, dict) and res.get("cancel", False):
                return

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
        self.setImportPath(impFileName)

        try:
            self.node.path()
        except:
            self.node = None
            self.importTarget = None
            self.fileNode = None

        extension = os.path.splitext(impFileName)[1]

        doImport = (
            self.node is None
            or (
                self.fileNode is None
                and not (extension == ".abc" and "_ShotCam_" in impFileName)
            )
            or not self.chb_updateOnly.isChecked()
            or (
                self.core.appPlugin.isNodeValid(self, self.fileNode)
                and (self.fileNode.type().name() == "alembic") == (extension != ".abc")
            )
            or self.node.type().name() == "subnet"
        )

        if extension == ".hda":
            self.importHDA(impFileName)
        elif doImport:
            if not self.isPrismImportNode(self.node):
                self.createImportNodes(impFileName, cacheData)
            else:
                objMerge = False

            self.handleImport(impFileName, cacheData=cacheData, objMerge=objMerge)
        else:
            self.handleUpdate(impFileName, cacheData)

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
    def importLatest(self, refreshUi=True, selectedStates=True):
        if refreshUi:
            self.updateUi()

        latestVersion = self.core.products.getLatestVersionFromPath(
            self.getImportPath()
        )
        filepath = self.core.products.getPreferredFileFromVersion(latestVersion)
        if not filepath:
            if not self.chb_autoUpdate.isChecked():
                self.core.popup("Couldn't get latest version.")
            return

        filepath = getattr(self.core.appPlugin, "fixImportPath", lambda x: x)(filepath)
        prevState = self.stateManager.applyChangesToSelection
        self.stateManager.applyChangesToSelection = False
        self.setImportPath(filepath)
        self.importObject()
        if selectedStates:
            selStates = self.stateManager.getSelectedStates()
            for state in selStates:
                if state.__hash__() == self.state.__hash__():
                    continue

                if hasattr(state.ui, "importLatest"):
                    state.ui.importLatest(refreshUi=refreshUi, selectedStates=False)

        self.stateManager.applyChangesToSelection = prevState

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

        if os.path.splitext(self.getImportPath())[1] == ".hda":
            if os.path.exists(self.getImportPath()):
                defs = hou.hda.definitionsInFile(self.getImportPath())
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
        curVersionName = self.core.products.getVersionFromFilepath(path) or ""
        curVersionData = {"version": curVersionName, "path": path}
        latestVersion = self.core.products.getLatestVersionFromPath(path)
        if latestVersion:
            latestVersionData = {"version": latestVersion["version"], "path": latestVersion["path"]}
        else:
            latestVersionData = {}

        return curVersionData, latestVersionData

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
        self.stateManager.tw_import.repaint()

    @err_catcher(name=__name__)
    def updateUi(self):
        if os.path.splitext(self.getImportPath())[1] == ".hda":
            self.gb_options.setVisible(False)
            self.b_goTo.setVisible(False)
            self.b_objMerge.setText("Create Node")
            self.l_status.setText("not installed")
            self.l_status.setToolTip("")
            self.l_status.setStyleSheet("QLabel { background-color : rgb(130,0,0); }")
            status = "error"
            if os.path.exists(self.getImportPath()):
                defs = hou.hda.definitionsInFile(self.getImportPath())
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
            if self.core.appPlugin.isNodeValid(self, self.node):
                self.l_status.setText(self.node.name())
                self.l_status.setToolTip(self.node.path())
                self.l_status.setStyleSheet(
                    "QLabel { background-color : rgb(0,130,0); }"
                )
                if self.isPrismImportNode(self.node) and not self.node.parm("filepath").eval():
                    status = "error"
                else:
                    status = "ok"
                self.b_objMerge.setEnabled(True)
            else:
                self.nameChanged()
                self.l_status.setText("Not found in scene")
                self.l_status.setToolTip("")
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

        if curVersion.get("version") == "master":
            filepath = self.getImportPath()
            curVersionName = self.core.products.getMasterVersionLabel(filepath)
        else:
            curVersionName = curVersion.get("version")

        if latestVersion.get("version") == "master":
            filepath = latestVersion["path"]
            latestVersionName = self.core.products.getMasterVersionLabel(filepath)
        else:
            latestVersionName = latestVersion.get("version")

        self.l_curVersion.setText(curVersionName or "-")
        self.l_latestVersion.setText(latestVersionName or "-")

        if self.chb_autoUpdate.isChecked():
            if curVersionName and latestVersionName and curVersionName != latestVersionName:
                self.importLatest(refreshUi=False)
        else:
            if (
                curVersionName
                and latestVersionName
                and curVersionName != latestVersionName
                and not curVersionName.startswith("master")
            ):
                self.b_importLatest.setStyleSheet(
                    "QPushButton { background-color : rgb(150,80,0); border: none;}"
                )
                status = "warning"
            else:
                self.b_importLatest.setStyleSheet("")

        if self.isPrismImportNode(self.node):
            self.core.appPlugin.importFile.refreshUiFromNode(
                {"node": self.node}, self.state
            )

        self.nameChanged()
        self.setStateColor(status)

        isShotCam = self.isShotCam()
        self.f_nameSpaces.setVisible(not isShotCam)
        self.b_objMerge.setVisible(not isShotCam)

    @err_catcher(name=__name__)
    def removeNameSpaces(self):
        if not self.fileNode:
            msg = "No valid node connected."
            self.core.popup(msg)
            return

        outputCons = self.fileNode.outputConnections()

        for i in outputCons:
            if (
                i.outputNode().type().name() == "grouprename"
                and i.outputNode().name() == "RemoveMayaNameSpaces"
            ):
                return

            if (
                i.outputNode().type().name() == "grouprename"
                and i.outputNode().name() == "RemoveMayaNameSpaces"
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
            "filepath": self.getImportPath(expand=False),
            "connectednode": curNode,
            "filenode": fNode,
            "autoUpdate": str(self.chb_autoUpdate.isChecked()),
            "updatepath": str(self.chb_updateOnly.isChecked()),
            "autonamespaces": str(self.chb_autoNameSpaces.isChecked()),
        }
