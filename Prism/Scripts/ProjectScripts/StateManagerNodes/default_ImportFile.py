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

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


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
        settings=None,
    ):
        self.state = state
        self.stateMode = "ImportFile"

        self.core = core
        self.stateManager = stateManager
        self.taskName = ""
        self.setName = ""

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

        self.nodes = []
        self.nodeNames = []

        self.f_abcPath.setVisible(False)
        self.f_keepRefEdits.setVisible(False)

        self.oldPalette = self.b_importLatest.palette()
        self.updatePalette = QPalette()
        self.updatePalette.setColor(QPalette.Button, QColor(200, 100, 0))
        self.updatePalette.setColor(QPalette.ButtonText, QColor(255, 255, 255))

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
            core.parentWindow(ts)
            ts.exec_()
            importPath = ts.productPath

        if importPath:
            self.setImportPath(importPath)
            result = self.importObject(settings=settings)

            if not result:
                return False
        elif (
            stateData is None
            and not createEmptyState
            and not self.stateManager.standalone
        ):
            return False

        getattr(self.core.appPlugin, "sm_import_startup", lambda x: None)(self)
        self.connectEvents()

        if stateData is not None:
            self.loadData(stateData)

        self.nameChanged()
        self.updateUi()

    @err_catcher(name=__name__)
    def setStateMode(self, stateMode):
        self.stateMode = stateMode
        self.l_class.setText(stateMode)

    @err_catcher(name=__name__)
    def loadData(self, data):
        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "statemode" in data:
            self.setStateMode(data["statemode"])
        if "filepath" in data:
            data["filepath"] = getattr(
                self.core.appPlugin, "sm_import_fixImportPath", lambda x: x
            )(data["filepath"])
            self.setImportPath(data["filepath"])
        if "keepedits" in data:
            self.chb_keepRefEdits.setChecked(eval(data["keepedits"]))
        if "autonamespaces" in data:
            self.chb_autoNameSpaces.setChecked(eval(data["autonamespaces"]))
        if "updateabc" in data:
            self.chb_abcPath.setChecked(eval(data["updateabc"]))
        if "trackobjects" in data:
            self.chb_trackObjects.setChecked(eval(data["trackobjects"]))
        if "connectednodes" in data:
            if self.core.isStr(data["connectednodes"]):
                data["connectednodes"] = eval(data["connectednodes"])
            self.nodes = [
                x[1]
                for x in data["connectednodes"]
                if self.core.appPlugin.isNodeValid(self, x[1])
            ]
        if "taskname" in data:
            self.taskName = data["taskname"]
        if "nodenames" in data:
            self.nodeNames = eval(data["nodenames"])
        if "setname" in data:
            self.setName = data["setname"]
        if "autoUpdate" in data:
            self.chb_autoUpdate.setChecked(eval(data["autoUpdate"]))

        self.core.callback("onStateSettingsLoaded", self, data)

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.b_browse.clicked.connect(self.browse)
        self.b_browse.customContextMenuRequested.connect(self.openFolder)
        self.b_import.clicked.connect(self.importObject)
        self.b_importLatest.clicked.connect(self.importLatest)
        self.chb_autoUpdate.stateChanged.connect(self.autoUpdateChanged)
        self.chb_keepRefEdits.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_autoNameSpaces.stateChanged.connect(self.autoNameSpaceChanged)
        self.chb_abcPath.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_trackObjects.toggled.connect(self.updateTrackObjects)
        self.b_selectAll.clicked.connect(self.lw_objects.selectAll)
        if not self.stateManager.standalone:
            self.b_nameSpaces.clicked.connect(
                lambda: self.core.appPlugin.sm_import_removeNameSpaces(self)
            )
            self.lw_objects.itemSelectionChanged.connect(
                lambda: self.core.appPlugin.selectNodes(self)
            )

    @err_catcher(name=__name__)
    def nameChanged(self, text=None):
        text = self.e_name.text()
        cacheData = self.core.paths.getCachePathData(self.getImportPath())
        if cacheData.get("type") == "asset":
            cacheData["entity"] = os.path.basename(cacheData.get("asset_path", ""))
        elif cacheData.get("type") == "shot":
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

        except Exception as e:
            name = text

        self.state.setText(0, name)

    @err_catcher(name=__name__)
    def getSortKey(self):
        cacheData = self.core.paths.getCachePathData(self.getImportPath())
        return cacheData.get("product")

    @err_catcher(name=__name__)
    def browse(self):
        import ProductBrowser

        ts = ProductBrowser.ProductBrowser(core=self.core, importState=self)
        self.core.parentWindow(ts)
        ts.exec_()
        importPath = ts.productPath

        if importPath:
            result = self.importObject(update=True, path=importPath)
            if result:
                self.setImportPath(importPath)
            self.updateUi()

    @err_catcher(name=__name__)
    def openFolder(self, pos):
        path = self.getImportPath()
        if os.path.isfile(path):
            path = os.path.dirname(path)

        self.core.openFolder(path)

    @err_catcher(name=__name__)
    def getImportPath(self):
        path = getattr(self, "importPath", "")
        if path:
            path = os.path.normpath(path)

        return path

    @err_catcher(name=__name__)
    def setImportPath(self, path):
        self.importPath = path
        self.w_currentVersion.setToolTip(path)
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
                if curVersion.get("version") and latestVersion.get("version") and curVersion["version"] != latestVersion["version"]:
                    self.importLatest()

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def autoNameSpaceChanged(self, checked):
        self.b_nameSpaces.setEnabled(not checked)
        if not self.stateManager.standalone:
            self.core.appPlugin.sm_import_removeNameSpaces(self)
            self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def runSanityChecks(self, cachePath):
        result = True

        if getattr(self.core.appPlugin, "hasFrameRange", True):
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
        if not impFPS or not curFPS or impFPS == curFPS:
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
    def importObject(self, update=False, path=None, settings=None):
        result = True
        if self.stateManager.standalone:
            return result

        fileName = self.core.getCurrentFileName()
        impFileName = path or self.getImportPath()
        impFileName = os.path.normpath(impFileName)

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
            self.core.popup("Invalid importpath:\n\n%s" % impFileName)
            return

        if not hasattr(self.core.appPlugin, "sm_import_importToApp"):
            self.core.popup("Import into %s is not supported." % self.core.appPlugin.pluginName)
            return

        result = self.runSanityChecks(impFileName)
        if not result:
            return

        cacheData = self.core.paths.getCachePathData(impFileName)
        self.taskName = cacheData.get("task")
        doImport = True

        if self.chb_trackObjects.isChecked():
            getattr(self.core.appPlugin, "sm_import_updateObjects", lambda x: None)(
                self
            )

        # temporary workaround until all plugin handle the settings argument
        if self.core.appPlugin.pluginName == "Maya":
            importResult = self.core.appPlugin.sm_import_importToApp(
                self, doImport=doImport, update=update, impFileName=impFileName, settings=settings
            )
        else:
            importResult = self.core.appPlugin.sm_import_importToApp(
                self, doImport=doImport, update=update, impFileName=impFileName
            )

        if not importResult:
            result = None
            doImport = False
        else:
            result = importResult["result"]
            doImport = importResult["doImport"]
            if result and "mode" in importResult:
                self.setStateMode(importResult["mode"])

        if doImport:
            if result == "canceled":
                return

            self.nodeNames = [
                self.core.appPlugin.getNodeName(self, x) for x in self.nodes
            ]
            illegalNodes = self.core.checkIllegalCharacters(self.nodeNames)
            if len(illegalNodes) > 0:
                msgStr = "Objects with non-ascii characters were imported. Prism supports only the first 128 characters in the ascii table. Please rename the following objects as they will cause errors with Prism:\n\n"
                for i in illegalNodes:
                    msgStr += i + "\n"
                self.core.popup(msgStr)

            if self.chb_autoNameSpaces.isChecked():
                self.core.appPlugin.sm_import_removeNameSpaces(self)

            if not result:
                msgStr = "Import failed: %s" % impFileName
                self.core.popup(msgStr, title="ImportFile")

        kwargs = {
            "state": self,
            "scenefile": fileName,
            "importfile": impFileName,
            "importedObjects": self.nodeNames,
        }
        self.core.callback("postImport", **kwargs)
        self.setImportPath(impFileName)
        self.stateManager.saveImports()
        self.updateUi()
        self.stateManager.saveStatesToScene()

        return result

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

        prevState = self.stateManager.applyChangesToSelection
        self.stateManager.applyChangesToSelection = False
        self.setImportPath(filepath)
        self.importObject(update=True)
        if selectedStates:
            selStates = self.stateManager.getSelectedStates()
            for state in selStates:
                if state.__hash__() == self.state.__hash__():
                    continue

                if hasattr(state.ui, "importLatest"):
                    state.ui.importLatest(refreshUi=refreshUi, selectedStates=False)

        self.stateManager.applyChangesToSelection = prevState

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
            statusColor = QColor(200, 100, 0)
        elif status == "error":
            statusColor = QColor(130, 0, 0)
        else:
            statusColor = QColor(0, 0, 0, 0)

        self.statusColor = statusColor
        self.stateManager.tw_import.repaint()

    @err_catcher(name=__name__)
    def updateUi(self):
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

        status = "error"
        if self.chb_autoUpdate.isChecked():
            if curVersionName and latestVersionName and curVersionName != latestVersionName:
                self.importLatest(refreshUi=False)

            if latestVersionName:
                status = "ok"
        else:
            useSS = getattr(self.core.appPlugin, "colorButtonWithStyleSheet", False)
            if (
                curVersionName
                and latestVersionName
                and curVersionName != latestVersionName
                and not curVersionName.startswith("master")
            ):
                status = "warning"
                if useSS:
                    self.b_importLatest.setStyleSheet(
                        "QPushButton { background-color: rgb(200,100,0); }"
                    )
                else:
                    self.b_importLatest.setPalette(self.updatePalette)
            else:
                if curVersionName and latestVersionName:
                    status = "ok"
                elif self.nodes:
                    status = "ok"

                if useSS:
                    self.b_importLatest.setStyleSheet("")
                else:
                    self.b_importLatest.setPalette(self.oldPalette)

        isCache = self.stateMode == "ApplyCache"
        self.f_nameSpaces.setVisible(not isCache)

        self.lw_objects.clear()

        if self.chb_trackObjects.isChecked():
            self.gb_objects.setVisible(True)
            getattr(self.core.appPlugin, "sm_import_updateObjects", lambda x: None)(
                self
            )

            for i in self.nodes:
                item = QListWidgetItem(self.core.appPlugin.getNodeName(self, i))
                getattr(
                    self.core.appPlugin,
                    "sm_import_updateListItem",
                    lambda x, y, z: None,
                )(self, item, i)

                self.lw_objects.addItem(item)
        else:
            self.gb_objects.setVisible(False)

        self.nameChanged()
        self.setStateColor(status)
        getattr(self.core.appPlugin, "sm_import_updateUi", lambda x: None)(self)

    @err_catcher(name=__name__)
    def updateTrackObjects(self, state):
        if not state:
            if len(self.nodes) > 0:
                msg = QMessageBox(
                    QMessageBox.Question,
                    "Track objects",
                    "When you disable object tracking Prism won't be able to delete or replace the imported objects at a later point in time. You cannot undo this action. Are you sure you want to disable object tracking?",
                    QMessageBox.Cancel,
                )
                msg.addButton("Continue", QMessageBox.YesRole)
                msg.setParent(self.core.messageParent, Qt.Window)
                action = msg.exec_()

                if action != 0:
                    self.chb_trackObjects.setChecked(True)
                    return

            self.nodes = []
            getattr(
                self.core.appPlugin, "sm_import_disableObjectTracking", lambda x: None
            )(self)

        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def preDelete(
        self,
        item=None,
        baseText="Do you also want to delete the connected objects?\n\n",
    ):
        if len(self.nodes) > 0 and self.stateMode != "ApplyCache":
            message = baseText
            validNodes = [
                x for x in self.nodes if self.core.appPlugin.isNodeValid(self, x)
            ]
            if len(validNodes) > 0:
                for idx, val in enumerate(validNodes):
                    if idx > 5:
                        message += "..."
                        break
                    else:
                        message += self.core.appPlugin.getNodeName(self, val) + "\n"

                if not self.core.uiAvailable:
                    action = 0
                    print("delete objects:\n\n%s" % message)
                else:
                    msg = QMessageBox(
                        QMessageBox.Question, "Delete state", message, QMessageBox.No
                    )
                    msg.addButton("Yes", QMessageBox.YesRole)
                    msg.setParent(self.core.messageParent, Qt.Window)
                    action = msg.exec_()

                if action == 0:
                    self.core.appPlugin.deleteNodes(self, validNodes)

    @err_catcher(name=__name__)
    def getStateProps(self):
        connectedNodes = []
        if self.chb_trackObjects.isChecked():
            for i in range(self.lw_objects.count()):
                connectedNodes.append([self.lw_objects.item(i).text(), self.nodes[i]])

        return {
            "statename": self.e_name.text(),
            "statemode": self.stateMode,
            "filepath": self.getImportPath(),
            "autoUpdate": str(self.chb_autoUpdate.isChecked()),
            "keepedits": str(self.chb_keepRefEdits.isChecked()),
            "autonamespaces": str(self.chb_autoNameSpaces.isChecked()),
            "updateabc": str(self.chb_abcPath.isChecked()),
            "trackobjects": str(self.chb_trackObjects.isChecked()),
            "connectednodes": connectedNodes,
            "taskname": self.taskName,
            "nodenames": str(self.nodeNames),
            "setname": self.setName,
        }
