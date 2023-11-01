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
import subprocess
import logging
import traceback
from collections import OrderedDict
import shutil

prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

if __name__ == "__main__":
    sys.path.append(os.path.join(prismRoot, "Scripts"))
    import PrismCore

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

import ExternalTask
from PrismUtils import PrismWidgets
from PrismUtils.Decorators import err_catcher
from UserInterfaces import MediaBrowser_ui


logger = logging.getLogger(__name__)


class MediaBrowser(QWidget, MediaBrowser_ui.Ui_w_mediaBrowser):
    def __init__(self, core, projectBrowser=None, refresh=True):
        QWidget.__init__(self)
        self.setupUi(self)
        self.core = core
        self.projectBrowser = projectBrowser

        logger.debug("Initializing Media Browser")

        self.core.parentWindow(self)
        self.b_refresh.setEnabled(True)
        self.chb_autoUpdate.setToolTip(
            "Automatically refresh tasks, versions and renders, when the current asset/shot changes."
        )
        self.b_refresh.setToolTip("Refresh tasks, versions and renders.")

        self.initialized = False
        self.closeParm = "closeafterload"
        self.loadLayout()
        self.connectEvents()
        self.core.callback(name="onMediaBrowserOpen", args=[self])

        if refresh:
            self.entered()

    @err_catcher(name=__name__)
    def entered(self, prevTab=None, navData=None):
        if not self.initialized:
            self.w_entities.getPage("Assets").blockSignals(True)
            self.w_entities.getPage("Shots").blockSignals(True)
            self.w_entities.blockSignals(True)
            self.w_entities.refreshEntities(defaultSelection=False)
            self.w_entities.getPage("Assets").blockSignals(False)
            self.w_entities.getPage("Shots").blockSignals(False)
            self.w_entities.blockSignals(False)
            self.oiio = self.core.media.getOIIO()
            if navData:
                self.navigate(navData)
            else:
                self.navigateToCurrent()

            if not self.getCurrentEntity():
                self.entityChanged()

            self.initialized = True

        if prevTab:
            if hasattr(prevTab, "w_entities"):
                self.w_entities.syncFromWidget(prevTab.w_entities)
            elif hasattr(prevTab, "getSelectedData"):
                self.navigateToEntity(prevTab.getSelectedData())

    @err_catcher(name=__name__)
    def loadLayout(self):
        import EntityWidget

        self.w_entities = EntityWidget.EntityWidget(core=self.core, refresh=False, mode="media")
        self.splitter.insertWidget(0, self.w_entities)

        self.w_autoUpdate.setVisible(False)

        cData = self.core.getConfig()
        brsData = cData.get("browser", {})

        if "autoUpdateRenders" in brsData:
            self.chb_autoUpdate.setChecked(brsData["autoUpdateRenders"])

        if "expandedAssets_" + self.core.projectName in brsData:
            self.aExpanded = brsData["expandedAssets_" + self.core.projectName]

        if "expandedSequences_" + self.core.projectName in brsData:
            self.sExpanded = brsData["expandedSequences_" + self.core.projectName]

        self.w_entities.getPage("Assets").setSearchVisible(
            brsData.get("showAssetSearch", False)
        )

        self.w_entities.getPage("Shots").setSearchVisible(brsData.get("showShotSearch", False))

        if "showSearchAlways" in brsData:
            self.w_entities.getPage("Assets").setShowSearchAlways(
                brsData["showSearchAlways"]
            )
            self.w_entities.getPage("Shots").setShowSearchAlways(
                brsData["showSearchAlways"]
            )

        self.w_preview = MediaVersionPlayer(self)
        self.w_preview.layout().addStretch()
        self.splitter.addWidget(self.w_preview)

        self.lw_task.setAcceptDrops(True)
        self.lw_task.dragEnterEvent = self.taskDragEnterEvent
        self.lw_task.dragMoveEvent = self.taskDragMoveEvent
        self.lw_task.dragLeaveEvent = self.taskDragLeaveEvent
        self.lw_task.dropEvent = self.taskDropEvent

        if self.projectBrowser and len(self.projectBrowser.locations) > 1:
            self.VersionDelegate = VersionDelegate(self)
            self.lw_version.setItemDelegate(self.VersionDelegate)

        if "previewDisabled" in brsData:
            self.w_preview.mediaPlayer.state = "disabled" if brsData["previewDisabled"] else "enabled"

        self.setStyleSheet("QSplitter::handle{background-color: transparent}")

    @err_catcher(name=__name__)
    def showEvent(self, event):
        if not getattr(self, "headerHeightSet", False):
            spacing = self.w_identifier.layout().spacing()
            h = self.w_entities.w_header.geometry().height() - spacing
            self.setHeaderHeight(h)

    @err_catcher(name=__name__)
    def setHeaderHeight(self, height):
        spacing = self.w_identifier.layout().spacing()
        self.w_entities.w_header.setMinimumHeight(height + spacing)
        self.l_identifier.setMinimumHeight(height)
        self.l_version.setMinimumHeight(height)
        self.w_preview.l_layer.setMinimumHeight(height)
        self.headerHeightSet = True

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.w_entities.getPage("Assets").itemChanged.connect(self.entityChanged)
        self.w_entities.getPage("Shots").itemChanged.connect(self.entityChanged)
        self.w_entities.tabChanged.connect(self.entityTabChanged)

        self.chb_autoUpdate.stateChanged.connect(self.updateChanged)
        self.b_refresh.clicked.connect(self.refreshRender)

        self.lw_task.itemSelectionChanged.connect(self.taskClicked)
        self.lw_version.itemSelectionChanged.connect(self.versionClicked)
        self.lw_version.mmEvent = self.lw_version.mouseMoveEvent
        self.lw_version.mouseMoveEvent = lambda x: self.w_preview.mediaPlayer.mouseDrag(x, self.lw_version)
        self.lw_version.itemDoubleClicked.connect(self.onVersionDoubleClicked)
        self.lw_task.customContextMenuRequested.connect(
            lambda x: self.rclList(x, self.lw_task)
        )
        self.lw_version.customContextMenuRequested.connect(
            lambda x: self.rclList(x, self.lw_version)
        )

    @err_catcher(name=__name__)
    def saveSettings(self, data):
        data["browser"]["autoUpdateRenders"] = self.chb_autoUpdate.isChecked()
        data["browser"]["previewDisabled"] = self.w_preview.mediaPlayer.state == "disabled"

    @err_catcher(name=__name__)
    def updateChanged(self, state):
        if state:
            self.updateTasks()

    @err_catcher(name=__name__)
    def entityTabChanged(self):
        self.entityChanged()

    @err_catcher(name=__name__)
    def entityChanged(self, item=None):
        self.updateTasks(restoreSelection=True)

    @err_catcher(name=__name__)
    def refreshUI(self):
        self.core.media.invalidateOiioCache()
        self.w_entities.getCurrentPage().tw_tree.blockSignals(True)
        self.w_entities.refreshEntities(restoreSelection=True)
        self.w_entities.getCurrentPage().tw_tree.blockSignals(False)
        self.entityChanged()
        self.refreshStatus = "valid"

    @err_catcher(name=__name__)
    def getCurrentData(self):
        curIdentifier = self.getCurrentIdentifier()
        if curIdentifier:
            identifier = curIdentifier["displayName"]
        else:
            identifier = ""

        curVersion = self.getCurrentVersion()
        if curVersion:
            version = curVersion["version"]
        else:
            version = ""

        curAov = self.getCurrentAOV()
        if curAov:
            aov = curAov["aov"]
        else:
            aov = ""

        curSource = self.getCurrentSource()
        if curSource:
            source = curSource["source"]
        else:
            source = ""

        curData = [
            self.getCurrentEntity(),
            identifier,
            version,
            aov,
            source,
        ]
        return curData

    @err_catcher(name=__name__)
    def refreshRender(self):
        curData = self.getCurrentData()
        self.showRender(*curData)

    @err_catcher(name=__name__)
    def getCurrentEntity(self):
        return self.w_entities.getCurrentPage().getCurrentData()

    @err_catcher(name=__name__)
    def getCurrentEntities(self):
        return self.w_entities.getCurrentPage().getCurrentData(returnOne=False)

    @err_catcher(name=__name__)
    def getCurrentIdentifier(self):
        items = self.lw_task.selectedItems()
        if not items:
            return

        return items[0].data(Qt.UserRole)

    @err_catcher(name=__name__)
    def getCurrentVersion(self):
        items = self.lw_version.selectedItems()
        if not items:
            return

        return items[0].data(Qt.UserRole)

    @err_catcher(name=__name__)
    def getCurrentVersions(self):
        items = self.lw_version.selectedItems()
        if not items:
            return []

        versions = [item.data(Qt.UserRole) for item in items]
        return versions

    @err_catcher(name=__name__)
    def getCurrentAOV(self):
        return self.w_preview.getCurrentAOV()

    @err_catcher(name=__name__)
    def getCurrentSource(self):
        return self.w_preview.getCurrentSource()

    @err_catcher(name=__name__)
    def getCurrentFilelayer(self):
        return self.w_preview.getCurrentFilelayer()

    @err_catcher(name=__name__)
    def getMediaTasks(self, entity=None):
        mediaTasks = {"3d": [], "2d": [], "playblast": [], "external": []}

        if not entity:
            entity = self.getCurrentEntities()
            if isinstance(entity, list) and len(entity) == 1:
                entity = entity[0]

            if not entity or not isinstance(entity, dict) or entity["type"] not in ["asset", "shot"]:
                return mediaTasks

        location = self.w_entities.getCurrentLocation()
        mediaTasks = self.core.mediaProducts.getIdentifiersByType(entity=entity, locations=[location])
        return mediaTasks

    @err_catcher(name=__name__)
    def updateTasks(self, restoreSelection=False):
        if restoreSelection:
            curTask = None
            identifier = self.getCurrentIdentifier()
            if identifier:
                curTask = identifier.get("displayName")

        wasBlocked = self.lw_task.signalsBlocked()
        if not wasBlocked:
            self.lw_task.blockSignals(True)

        self.lw_task.clear()

        mediaTasks = self.getMediaTasks()
        if mediaTasks:
            addedItems = []
            for pType in ["3d", "2d", "playblast", "external"]:
                for task in sorted(mediaTasks[pType], key=lambda x: x["displayName"]):
                    if task["displayName"] in addedItems:
                        continue

                    item = QListWidgetItem(task["displayName"])
                    addedItems.append(task["displayName"])
                    item.setData(Qt.UserRole, task)
                    self.lw_task.addItem(item)

        if self.lw_task.count() > 0:
            selectFirst = True
            if restoreSelection and curTask:
                items = self.lw_task.findItems(curTask, Qt.MatchFlag(Qt.MatchExactly & Qt.MatchCaseSensitive))
                if items:
                    self.lw_task.setCurrentItem(items[0])
                    selectFirst = False

            if selectFirst:
                mIdx = self.lw_task.findItems("main", Qt.MatchFlag(Qt.MatchExactly & Qt.MatchCaseSensitive))
                if len(mIdx) > 0:
                    self.lw_task.setCurrentItem(mIdx[0])
                else:
                    self.lw_task.setCurrentRow(0)

        if not wasBlocked:
            self.lw_task.blockSignals(False)
            self.updateVersions(restoreSelection=True)

    @err_catcher(name=__name__)
    def sortVersions(self, key):
        val = key["version"]
        if val == "master":
            val = "zz_master"

        return val

    @err_catcher(name=__name__)
    def updateVersions(self, restoreSelection=False):
        if restoreSelection:
            curVersion = None
            version = self.getCurrentVersion()
            if version:
                curVersion = version.get("version")

        wasBlocked = self.lw_version.signalsBlocked()
        if not wasBlocked:
            self.lw_version.blockSignals(True)
        
        self.lw_version.clear()
        selectFirst = True
        if len(self.lw_task.selectedItems()) == 1:
            identifier = self.getCurrentIdentifier()
            location = self.w_entities.getCurrentLocation()
            versions = self.core.mediaProducts.getVersionsFromIdentifier(
                identifier=identifier, locations=[location]
            )
            locs = self.core.paths.getRenderProductBasePaths()
            for version in sorted(versions, key=self.sortVersions, reverse=True):
                if version["version"] == "master":
                    versionName = self.core.mediaProducts.getMasterVersionLabel(version["path"])
                else:
                    versionName = version["version"]

                vdata = self.core.paths.getRenderProductData(version["path"], isFilepath=False, addPathData=False, mediaType="3drenders", validateModTime=False)
                if "project_path" in vdata:
                    del vdata["project_path"]

                comment = vdata.get("comment")
                if comment:
                    versionName += " - " + comment

                versionData = version.copy()
                if versionData["version"] == "master":
                    vdata["version"] = "master"

                versionData.update(vdata)
                if len(locs) > 1:
                    locStr = ", ".join([loc for loc in versionData.get("locations", []) if loc != "global"])
                    if locStr:
                        versionName += " (%s)" % locStr

                item = QListWidgetItem(versionName)
                item.setData(Qt.UserRole, versionData)
                if len(locs) > 1:
                    item.setToolTip(", ".join(versionData.get("locations", [])))

                self.lw_version.addItem(item)

                if restoreSelection and curVersion:
                    if curVersion == version["version"]:
                        self.lw_version.setCurrentItem(item)
                        selectFirst = False

        if self.lw_version.count() > 0 and selectFirst:
            self.lw_version.setCurrentRow(0)

        if not wasBlocked:
            self.lw_version.blockSignals(False)
            self.versionClicked()

    @err_catcher(name=__name__)
    def getSelectedContexts(self):
        contexts = []
        if len(self.lw_task.selectedItems()) > 1:
            contexts = self.lw_task.selectedItems()
        elif len(self.lw_version.selectedItems()) > 1:
            contexts = self.lw_version.selectedItems()
        else:
            data = self.getCurrentFilelayer()
            if not data:
                data = self.getCurrentSource()
                if not data:
                    data = self.getCurrentAOV()
                    if not data:
                        items = self.lw_version.selectedItems()
                        if items:
                            data = items[0].data(Qt.UserRole)

            if data:
                contexts = [data]

        return contexts

    @err_catcher(name=__name__)
    def taskClicked(self):
        self.updateVersions()

    @err_catcher(name=__name__)
    def versionClicked(self):
        self.w_preview.updateLayers(restoreSelection=True)

    @err_catcher(name=__name__)
    def onVersionDoubleClicked(self, item):
        mods = QApplication.keyboardModifiers()
        if mods == Qt.ControlModifier:
            for selItem in self.lw_version.selectedItems():
                self.core.openFolder(selItem.data(Qt.UserRole).get("path"))
        else:
            self.showVersionInfoForItem(item)

    @err_catcher(name=__name__)
    def mouseDrag(self, event, element):
        if (
            (event.buttons() != Qt.LeftButton and element != self.cb_layer)
            or (
                event.buttons() == Qt.LeftButton
                and (event.modifiers() & Qt.ShiftModifier)
            )
        ):
            element.mmEvent(event)
            return
        elif element == self.cb_layer and event.buttons() != Qt.MiddleButton:
            element.mmEvent(event)
            return

        contexts = self.getCurRenders()
        urlList = []
        mods = QApplication.keyboardModifiers()
        for context in contexts:
            if element == self.cb_layer:
                version = self.getCurrentVersion()
                aovs = self.core.mediaProducts.getAOVsFromVersion(version)
                for aov in aovs:
                    url = os.path.normpath(aov["path"])
                    urlList.append(QUrl(url))
                break
            else:
                if mods == Qt.ControlModifier:
                    url = os.path.normpath(context["path"])
                    urlList.append(url)
                else:
                    imgSrc = self.core.media.getImgSources(context["path"], sequencePattern=False)
                    for k in imgSrc:
                        url = os.path.normpath(k)
                        urlList.append(url)

        if len(urlList) == 0:
            return

        drag = QDrag(self)
        mData = QMimeData()

        urlData = [QUrl.fromLocalFile(urll) for urll in urlList]
        mData.setUrls(urlData)
        drag.setMimeData(mData)

        drag.exec_(Qt.CopyAction | Qt.MoveAction)

    @err_catcher(name=__name__)
    def editComment(self, filepath):
        data = self.core.paths.getRenderProductData(filepath)
        comment = data.get("comment", "")

        dlg_ec = PrismWidgets.CreateItem(
            core=self.core, startText=comment, showType=False, valueRequired=False, validate=False
        )

        dlg_ec.setModal(True)
        self.core.parentWindow(dlg_ec, parent=self)
        dlg_ec.e_item.setFocus()
        dlg_ec.setWindowTitle("Edit Comment")
        dlg_ec.l_item.setText("New comment:")
        dlg_ec.buttonBox.buttons()[0].setText("Save")

        result = dlg_ec.exec_()

        if not result:
            return

        comment = dlg_ec.e_item.text()
        self.core.mediaProducts.setComment(filepath, comment)
        self.updateVersions(restoreSelection=True)

    @err_catcher(name=__name__)
    def goToSource(self, source):
        if not source:
            msg = "This version doesn't have a source scene."
            self.core.popup(msg)
            return

        self.core.pb.showTab("Scenefiles")
        fileNameData = self.core.getScenefileData(source)
        self.core.pb.sceneBrowser.navigate(data=fileNameData)

    @err_catcher(name=__name__)
    def showVersionInfoForItem(self, item):
        context = item.data(Qt.UserRole)
        self.showVersionInfo(context)

    @err_catcher(name=__name__)
    def showVersionInfo(self, context):
        vInfo = "No information is saved with this version."

        path = self.core.mediaProducts.getVersionInfoPathFromContext(context)

        if os.path.exists(path):
            vData = self.core.getConfig(configPath=path)

            vInfo = []
            for key in vData:
                label = key[0].upper() + key[1:]
                vInfo.append([label, vData[key]])

        if type(vInfo) == str or len(vInfo) == 0:
            self.core.popup(vInfo, severity="info")
            return

        infoDlg = QDialog()
        lay_info = QGridLayout()

        identifier = self.getCurrentIdentifier()
        version = self.getCurrentVersion() or context

        infoDlg.setWindowTitle(
            "Versioninfo %s %s:" % (identifier["identifier"], version["version"])
        )
        for idx, val in enumerate(vInfo):
            l_infoName = QLabel(val[0] + ":\t")
            l_info = QLabel(str(val[1]))
            lay_info.addWidget(l_infoName)
            lay_info.addWidget(l_info, idx, 1)

        lay_info.addItem(
            QSpacerItem(10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )
        lay_info.addItem(
            QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum), 0, 2
        )

        sa_info = QScrollArea()

        lay_info.setContentsMargins(10, 10, 10, 10)
        w_info = QWidget()
        w_info.setLayout(lay_info)
        sa_info.setWidget(w_info)
        sa_info.setWidgetResizable(True)

        bb_info = QDialogButtonBox()

        bb_info.addButton("Ok", QDialogButtonBox.AcceptRole)

        bb_info.accepted.connect(infoDlg.accept)

        bLayout = QVBoxLayout()
        bLayout.addWidget(sa_info)
        bLayout.addWidget(bb_info)
        infoDlg.setLayout(bLayout)
        infoDlg.setParent(self.core.messageParent, Qt.Window)
        infoDlg.resize(900 * self.core.uiScaleFactor, 400 * self.core.uiScaleFactor)

        infoDlg.exec_()

    @err_catcher(name=__name__)
    def showDependencies(self, context):
        path = self.core.mediaProducts.getVersionInfoPathFromContext(context)

        if not os.path.exists(path):
            self.core.popup("No dependency information was saved with this version.")
            return

        self.core.dependencyViewer(path)

    @err_catcher(name=__name__)
    def getSelectedContext(self):
        return self.getCurrentData()

    @err_catcher(name=__name__)
    def navigateToCurrent(self):
        fileName = self.core.getCurrentFileName()
        fileNameData = self.core.getScenefileData(fileName)
        self.showRender(entity=fileNameData)

    @err_catcher(name=__name__)
    def navigate(self, data):
        if isinstance(data, list):
            self.showRender(*data)
        else:
            self.showRender(
                entity=data.get("entity"),
                identifier=data.get("identifier"),
                version=data.get("version"),
                aov=data.get("aov"),
                source=data.get("source"),
            )

    @err_catcher(name=__name__)
    def navigateToEntity(self, entity):
        self.w_entities.navigate(entity)

    @err_catcher(name=__name__)
    def showRender(self, entity=None, identifier=None, version=None, aov=None, source=None, filelayer=None):
        prevIdf = self.getCurrentIdentifier()
        self.lw_task.blockSignals(True)
        if entity:
            self.navigateToEntity(entity)

        if not identifier:
            self.lw_task.blockSignals(False)
            if prevIdf != self.getCurrentIdentifier() or not self.initialized:
                self.taskClicked()

            return

        matches = self.lw_task.findItems(
            identifier, Qt.MatchFlag(Qt.MatchExactly & Qt.MatchCaseSensitive)
        )
        if not matches:
            self.lw_task.blockSignals(False)
            if prevIdf != self.getCurrentIdentifier() or not self.initialized:
                self.taskClicked()

            return

        self.lw_task.setCurrentItem(matches[0])
        self.lw_task.blockSignals(False)
        prevVersion = self.getCurrentVersion()
        self.lw_version.blockSignals(True)
        if prevIdf != self.getCurrentIdentifier():
            self.taskClicked()

        if not version:
            self.lw_version.blockSignals(False)
            if prevVersion != self.getCurrentVersion() or not self.initialized:
                self.versionClicked()

            return

        items = [self.lw_version.item(x) for x in range(self.lw_version.count())]
        vMatches = [item for item in items if item.data(Qt.UserRole) and item.data(Qt.UserRole).get("version") == version]
        if not vMatches:
            self.lw_version.blockSignals(False)
            if prevVersion != self.getCurrentVersion() or not self.initialized:
                self.versionClicked()

            return

        self.lw_version.setCurrentItem(vMatches[0])
        self.lw_version.blockSignals(False)
        if prevVersion != self.getCurrentVersion():
            result = self.w_preview.navigate(aov, source, filelayer)
            if not result:
                self.w_preview.layerChanged()

    @err_catcher(name=__name__)
    def setPreview(self):
        entity = self.getCurrentEntity()
        pm = self.w_preview.mediaPlayer.l_preview.pixmap()
        self.core.entities.setEntityPreview(entity, pm)
        self.core.pb.sceneBrowser.refreshEntityInfo()
        self.w_entities.getCurrentPage().refreshEntities(restoreSelection=True)

    @err_catcher(name=__name__)
    def rclList(self, pos, lw):
        cpos = QCursor.pos()
        item = lw.itemAt(pos)
        if item is not None:
            itemName = item.text()
        else:
            itemName = ""

        entity = self.getCurrentEntity()
        if not entity:
            return False

        if lw == self.lw_task:
            if itemName:
                path = item.data(Qt.UserRole)["path"]
            else:
                path = self.core.mediaProducts.getIdentifierPathFromEntity(entity)
        elif lw == self.lw_version:
            if itemName:
                data = item.data(Qt.UserRole)
                path = data["path"]
            else:
                identifier = self.getCurrentIdentifier()
                if not identifier:
                    return

                path = self.core.mediaProducts.getVersionPathFromIdentifier(identifier)

        rcmenu = QMenu(self)
        if lw == self.lw_task:
            refresh = self.updateTasks
            if entity.get("type") in ["asset", "shot"]:
                depAct = QAction("Create Identifier...", self)
                depAct.triggered.connect(self.createIdentifierDlg)
                rcmenu.addAction(depAct)

                exAct = QAction("Add external media", self)
                exAct.triggered.connect(self.createExternalTask)
                rcmenu.addAction(exAct)

        elif lw == self.lw_version:
            refresh = self.updateVersions
            identifier = self.getCurrentIdentifier()
            if identifier:
                depAct = QAction("Create Version...", self)
                depAct.triggered.connect(self.createVersionDlg)
                rcmenu.addAction(depAct)

            if identifier["mediaType"] == "externalMedia":
                nvAct = QAction("Create new external version", self)
                nvAct.triggered.connect(self.newExternalVersion)
                rcmenu.addAction(nvAct)

            if item:
                infAct = QAction("Edit comment...", self)
                infAct.triggered.connect(lambda: self.editComment(path))
                rcmenu.addAction(infAct)

                infAct = QAction("Show version info", self)
                infAct.triggered.connect(lambda: self.showVersionInfoForItem(item))
                rcmenu.addAction(infAct)

                depAct = QAction("Show dependencies", self)
                depAct.triggered.connect(lambda: self.showDependencies(data))
                rcmenu.addAction(depAct)

                infoPath = self.core.mediaProducts.getVersionInfoPathFromContext(data)
                source = self.core.getConfig("sourceScene", configPath=infoPath)
                depAct = QAction("Go to source scene", self)
                depAct.triggered.connect(lambda: self.goToSource(source))
                rcmenu.addAction(depAct)
                if source:
                    depAct.setToolTip(source)
                else:
                    depAct.setEnabled(False)

                try:
                    rcmenu.setToolTipsVisible(True)
                except:
                    pass

                useMaster = self.core.mediaProducts.getUseMaster()
                if useMaster:
                    if itemName.startswith("master"):
                        masterAct = QAction("Delete master", self)
                        masterAct.triggered.connect(
                            lambda: self.core.mediaProducts.deleteMasterVersion(data["path"])
                        )
                        masterAct.triggered.connect(self.updateVersions)
                        rcmenu.addAction(masterAct)
                    else:
                        masterAct = QAction("Set as master", self)
                        masterAct.triggered.connect(lambda: self.setMaster(data))
                        rcmenu.addAction(masterAct)

                        masterAct = QAction("Add to master", self)
                        masterAct.triggered.connect(lambda: self.addMaster(data))
                        rcmenu.addAction(masterAct)

        act_refresh = QAction("Refresh", self)
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "refresh.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        act_refresh.setIcon(icon)
        act_refresh.triggered.connect(lambda: refresh(restoreSelection=True))
        rcmenu.addAction(act_refresh)

        if os.path.exists(path):
            opAct = QAction("Open in Explorer", self)
            opAct.triggered.connect(lambda: self.core.openFolder(path))
            rcmenu.addAction(opAct)

            copAct = QAction("Copy", self)
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "copy.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            copAct.setIcon(icon)
            copAct.triggered.connect(lambda: self.core.copyToClipboard(path, file=True))
            rcmenu.addAction(copAct)

        if lw == self.lw_version:
            copAct = QAction("Copy path for next version", self)
            copAct.triggered.connect(self.prepareNewVersion)
            rcmenu.addAction(copAct)

            curLoc = self.core.mediaProducts.getLocationFromPath(path)
            locMenu = QMenu("Copy to", self)
            rcmenu.addMenu(locMenu)
            locs = self.core.paths.getRenderProductBasePaths()
            for loc in locs:
                if loc == curLoc:
                    continue

                copAct = QAction(loc, self)
                copAct.triggered.connect(lambda x=None, l=loc: self.copyToLocation(path, l))
                locMenu.addAction(copAct)

        self.core.callback(
            name="openPBListContextMenu",
            args=[self, rcmenu, lw, item, path],
        )

        if rcmenu.isEmpty():
            return False

        rcmenu.exec_(cpos)

    @err_catcher(name=__name__)
    def prepareNewVersion(self):
        curEntity = self.getCurrentEntity()
        curIdentifier = self.getCurrentIdentifier()
        if not curIdentifier:
            return

        extension = ""
        framePadding = ""
        comment = ""
        if curIdentifier["mediaType"] == "playblasts":
            outputPathData = self.core.mediaProducts.generatePlayblastPath(
                entity=curEntity,
                task=curIdentifier["identifier"],
                extension=extension,
                framePadding=framePadding,
                comment=comment,
                returnDetails=True,
            )
        else:
            outputPathData = self.core.mediaProducts.generateMediaProductPath(
                entity=curEntity,
                task=curIdentifier["identifier"],
                extension=extension,
                framePadding=framePadding,
                comment=comment,
                singleFrame=True,
                returnDetails=True,
                mediaType=curIdentifier["mediaType"],
            )

        nextPath = outputPathData["path"]
        details = curEntity.copy()
        details["identifier"] = curIdentifier
        details["version"] = outputPathData["version"]

        self.core.saveSceneInfo(nextPath + ".", details=details)
        self.core.copyToClipboard(nextPath)

    @err_catcher(name=__name__)
    def copyToLocation(self, path, location):
        newPath = self.core.convertPath(path, target=location)
        if newPath:
            if os.path.exists(newPath):
                msg = "The target folder does already exist:\n\n%s" % newPath
                result = self.core.popupQuestion(msg, buttons=["Delete existing files", "Cancel"], icon=QMessageBox.Warning)
                if result == "Delete existing files":
                    try:
                        shutil.rmtree(newPath)
                    except Exception as e:
                        msg = "Failed to delete folder:\n\n%s" % e
                        self.core.popup(msg)

                    self.copyToLocation(path, location)
                    return
                else:
                    return

            logger.debug("copying version: %s to %s" % (path, newPath))
            self.core.copyWithProgress(path, newPath, finishCallback=lambda: self.updateVersions(restoreSelection=True))

    @err_catcher(name=__name__)
    def createIdentifierDlg(self):
        self.newItem = PrismWidgets.CreateItem(
            core=self.core, showType=False, mode="identifier"
        )
        self.newItem.setModal(True)
        self.core.parentWindow(self.newItem, parent=self)
        self.newItem.e_item.setFocus()
        self.newItem.setWindowTitle("Create Identifier")
        self.newItem.l_item.setText("Identifier:")
        self.newItem.accepted.connect(self.createIdentifier)
        self.newItem.w_mediaType = QWidget()
        self.newItem.l_mediaType = QLabel("Type:")
        self.newItem.cb_mediaType = QComboBox()
        self.newItem.lo_mediaType = QHBoxLayout()
        self.newItem.lo_mediaType.setContentsMargins(0, 0, 0, 0)
        self.newItem.w_mediaType.setLayout(self.newItem.lo_mediaType)
        self.newItem.lo_mediaType.addWidget(self.newItem.l_mediaType)
        self.newItem.lo_mediaType.addWidget(self.newItem.cb_mediaType)
        self.newItem.cb_mediaType.addItems(["3D", "2D", "Playblast"])
        self.newItem.verticalLayout.insertWidget(2, self.newItem.w_mediaType)

        self.core.callback(name="onCreateIdentifierDlgOpen", args=[self, self.newItem])

        self.newItem.show()

    @err_catcher(name=__name__)
    def createIdentifier(self):
        self.activateWindow()
        itemName = self.newItem.e_item.text()
        curEntity = self.getCurrentEntity()
        mediaTypeLabel = self.newItem.cb_mediaType.currentText()
        suffix = ""
        if mediaTypeLabel == "3D":
            mediaType = "3drenders"
        elif mediaTypeLabel == "2D":
            mediaType = "2drenders"
            suffix = " (2d)"
        elif mediaTypeLabel == "Playblast":
            mediaType = "playblasts"
            suffix = " (playblast)"

        self.core.mediaProducts.createIdentifier(entity=curEntity, identifier=itemName, identifierType=mediaType)
        self.updateTasks()
        if itemName is not None:
            matches = self.lw_task.findItems(
                itemName + suffix, Qt.MatchFlag(Qt.MatchExactly & Qt.MatchCaseSensitive)
            )
            if matches:
                self.lw_task.setCurrentItem(matches[0])

    @err_catcher(name=__name__)
    def createVersionDlg(self):
        identifier = self.getCurrentIdentifier()
        context = identifier.copy()

        version = self.core.mediaProducts.getHighestMediaVersion(context)
        self.newItem = PrismWidgets.CreateItem(
            core=self.core, showType=False, mode="version", startText=version
        )
        self.newItem.setModal(True)
        self.core.parentWindow(self.newItem)
        self.newItem.e_item.setFocus()
        self.newItem.setWindowTitle("Create Version")
        self.newItem.l_item.setText("Version:")
        self.newItem.accepted.connect(self.createVersion)
        self.core.callback(name="onCreateVersionDlgOpen", args=[self, self.newItem])
        self.newItem.show()

    @err_catcher(name=__name__)
    def createVersion(self):
        self.activateWindow()
        itemName = self.newItem.e_item.text()
        curEntity = self.getCurrentEntity()
        identifier = self.getCurrentIdentifier()
        self.core.mediaProducts.createVersion(
            entity=curEntity,
            identifier=identifier["identifier"],
            identifierType=identifier["mediaType"],
            version=itemName
        )
        self.updateVersions()
        if itemName is not None:
            matches = self.lw_version.findItems(
                itemName, Qt.MatchFlag(Qt.MatchExactly & Qt.MatchCaseSensitive)
            )
            if matches:
                self.lw_version.setCurrentItem(matches[0])

    @err_catcher(name=__name__)
    def setMaster(self, context):
        self.core.mediaProducts.updateMasterVersion(context=context, isFilepath=False)
        self.updateVersions()
        QPixmapCache.clear()

    @err_catcher(name=__name__)
    def addMaster(self, context):
        self.core.mediaProducts.addToMasterVersion(context=context, isFilepath=False)
        self.updateVersions()
        QPixmapCache.clear()

    @err_catcher(name=__name__)
    def taskDragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def taskDragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
            self.lw_task.setStyleSheet(
                "QWidget { border-style: dashed; border-color: rgb(100, 200, 100);  border-width: 2px; }"
            )
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def taskDragLeaveEvent(self, e):
        self.lw_task.setStyleSheet("")

    @err_catcher(name=__name__)
    def taskDropEvent(self, e):
        if e.mimeData().hasUrls():
            self.lw_task.setStyleSheet("")
            e.setDropAction(Qt.LinkAction)
            e.accept()

            if not self.getCurrentEntity():
                self.core.popup("Select an asset or a shot to add external media.")
                return

            fname = [
                os.path.normpath(str(url.toLocalFile())) for url in e.mimeData().urls()
            ]
            self.createExternalTask(filepath=os.pathsep.join(fname))
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def ingestMedia(self, entity, files):
        identifier = self.getCurrentIdentifier()
        version = self.getCurrentVersion()
        aov = self.getCurrentAOV()

        if not identifier:
            self.core.popup("Select an identifier to add media.")
            return

        if not version:
            self.core.popup("Select a version to add media.")
            return

        if aov:
            aovLabel = aov["aov"]
        else:
            aovLabel = ""
            if identifier["mediaType"] == "3drenders":
                self.core.popup("Select an AOV to add media.")
                return

        entity = identifier
        identifierLabel = identifier["identifier"]
        versionLabel = version["version"]
        result = self.core.mediaProducts.ingestMedia(files, entity, identifierLabel, versionLabel, aovLabel, mediaType=identifier["mediaType"])
        if result.get("versionAdded"):
            self.updateVersions()
        else:
            self.w_preview.updateSources()

    @err_catcher(name=__name__)
    def createExternalTask(self, data=None, filepath=""):
        entity = self.getCurrentEntity()
        if entity.get("type") not in ["asset", "shot"]:
            self.core.popup("Invalid entity is selected. Select an asset or a shot and try again.")
            return

        if not data:
            self.ep = ExternalTask.ExternalTask(core=self.core, startText=filepath)
            self.activateWindow()
            result = self.ep.exec_()

            if result == 1:
                taskName = self.ep.e_taskName.text()
                versionName = self.ep.e_versionName.text()
                targetPath = self.ep.e_taskPath.text()
                if self.ep.rb_copy.isChecked():
                    action = "copy"
                elif self.ep.rb_move.isChecked():
                    action = "move"
                elif self.ep.rb_link.isChecked():
                    action = "link"
            else:
                return

        else:
            taskName = data["taskName"]
            versionName = data["versionName"]
            targetPath = data["targetPath"]
            action = data["action"]

        self.core.mediaProducts.createExternalMedia(
            targetPath, entity, taskName, versionName, action=action
        )

        curData = [entity, taskName + " (external)", versionName, ""]
        self.showRender(*curData)

    @err_catcher(name=__name__)
    def newExternalVersion(self):
        identifier = self.getCurrentIdentifier()
        version = self.core.mediaProducts.getLatestVersionFromIdentifier(identifier)
        startPath = self.core.mediaProducts.getExternalPathFromVersion(version)

        intVersion = self.core.products.getIntVersionFromVersionName(version["version"])
        newVersion = self.core.versionFormat % (intVersion + 1)

        self.ep = ExternalTask.ExternalTask(core=self.core)
        self.ep.e_taskName.setText(identifier["identifier"])
        self.ep.w_taskName.setEnabled(False)
        self.ep.e_taskPath.setText(startPath)
        self.ep.e_versionName.setText(newVersion)
        self.ep.enableOk(startPath, self.ep.e_taskPath)
        self.ep.setWindowTitle("Create new version")

        result = self.ep.exec_()

        if result == 1:
            entity = self.getCurrentEntity()
            targetPath = self.ep.e_taskPath.text()
            idf = identifier["identifier"]
            versionName = self.ep.e_versionName.text()
            self.core.mediaProducts.createExternalMedia(
                targetPath, entity, idf, versionName
            )

            curData = [
                self.getCurrentEntity(),
                identifier["displayName"],
                self.ep.e_versionName.text(),
                "",
            ]
            self.showRender(*curData)

    @err_catcher(name=__name__)
    def getCurRenders(self):
        renders = []
        sTasks = self.lw_task.selectedItems()
        sVersions = self.lw_version.selectedItems()

        if len(sTasks) > 1:
            for identifierItem in sTasks:
                identifier = identifierItem.data(Qt.UserRole)
                versions = self.core.mediaProducts.getVersionsFromIdentifier(
                    identifier=identifier
                )

                if versions:
                    versions = sorted(
                        versions, key=lambda x: x["version"], reverse=True
                    )
                    aovs = self.core.mediaProducts.getAOVsFromVersion(versions[0])
                    context = versions[0].copy()

                    if aovs:
                        for aov in aovs:
                            if aov["aov"] in ["beauty", "rgb", "rgba"]:
                                context = aov
                                break
                        else:
                            context = aovs[0]

                renders.append(context)

        elif len(sVersions) > 1:
            for versionItem in sVersions:
                version = versionItem.data(Qt.UserRole)
                aovs = self.core.mediaProducts.getAOVsFromVersion(version)
                context = version.copy()

                if aovs:
                    for aov in aovs:
                        if aov["aov"] in ["beauty", "rgb", "rgba"]:
                            context = aov
                            break
                    else:
                        context = aovs[0]

                renders.append(context)

        else:
            data = self.getCurrentSource()
            if not data:
                data = self.getCurrentAOV()
                if not data:
                    data = self.getCurrentVersion()
                    if not data:
                        data = self.getCurrentIdentifier()

            if data:
                context = data.copy()
                renders.append(context)

        return renders

    @err_catcher(name=__name__)
    def triggerAutoplay(self, checked=False):
        self.w_preview.mediaPlayer.triggerAutoplay(checked)


class MediaVersionPlayer(QWidget):
    def __init__(self, origin):
        super(MediaVersionPlayer, self).__init__()
        self.origin = origin
        self.core = self.origin.core
        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self):
        self.lo_main = QVBoxLayout(self)
        self.lo_main.setContentsMargins(0, 0, 0, 0)

        self.l_layer = QLabel("AOVs:")
        self.cb_layer = QComboBox()
        self.lo_main.addWidget(self.l_layer)
        self.lo_main.addWidget(self.cb_layer)

        self.l_source = QLabel("Source:")
        self.cb_source = QComboBox()
        self.lo_main.addWidget(self.l_source)
        self.lo_main.addWidget(self.cb_source)

        self.l_filelayer = QLabel("Channel:")
        self.cb_filelayer = QComboBox()
        self.lo_main.addWidget(self.l_filelayer)
        self.lo_main.addWidget(self.cb_filelayer)

        self.mediaPlayer = self.getMediaPlayer()
        self.lo_main.addWidget(self.mediaPlayer)

        self.cb_layer.currentIndexChanged.connect(self.layerChanged)
        self.cb_layer.mmEvent = self.cb_layer.mouseMoveEvent
        self.cb_layer.mouseMoveEvent = lambda x: self.mediaPlayer.mouseDrag(x, self.cb_layer)
        self.cb_layer.setContextMenuPolicy(Qt.CustomContextMenu)
        self.cb_layer.customContextMenuRequested.connect(self.rclLayer)
        self.cb_source.currentIndexChanged.connect(self.sourceChanged)
        self.cb_filelayer.currentIndexChanged.connect(self.filelayerChanged)

    @err_catcher(name=__name__)
    def getMediaPlayer(self):
        return MediaPlayer(self)

    @err_catcher(name=__name__)
    def getCurrentAOV(self):
        data = self.cb_layer.currentData(Qt.UserRole)
        return data

    @err_catcher(name=__name__)
    def getCurrentSource(self):
        data = self.cb_source.currentData(Qt.UserRole)
        return data

    @err_catcher(name=__name__)
    def getCurrentFilelayer(self):
        data = self.cb_filelayer.currentData(Qt.UserRole)
        return data

    @err_catcher(name=__name__)
    def layerChanged(self, layer=None):
        self.updateSources(restoreSelection=True)

    @err_catcher(name=__name__)
    def sourceChanged(self, layer=None):
        self.updateFilelayers(restoreSelection=True)

    @err_catcher(name=__name__)
    def filelayerChanged(self, layer=None):
        self.mediaPlayer.updatePreview()

    @err_catcher(name=__name__)
    def getCurrentVersions(self):
        return self.origin.getCurrentVersions()

    @err_catcher(name=__name__)
    def updateLayers(self, restoreSelection=False):
        if restoreSelection:
            curLayer = self.cb_layer.currentText()

        wasBlocked = self.cb_layer.signalsBlocked()
        if not wasBlocked:
            self.cb_layer.blockSignals(True)
    
        self.cb_layer.clear()

        versions = self.getCurrentVersions()
        if len(versions) == 1:
            aovs = self.core.mediaProducts.getAOVsFromVersion(versions[0])
            for aov in aovs:
                self.cb_layer.addItem(aov["aov"], aov)

        selectFirst = True
        if restoreSelection and curLayer:
            bIdx = self.cb_layer.findText(curLayer)
            if bIdx != -1:
                self.cb_layer.setCurrentIndex(bIdx)
                selectFirst = False

        if selectFirst:
            bIdx = self.cb_layer.findText("beauty")
            if bIdx != -1:
                self.cb_layer.setCurrentIndex(bIdx)
            else:
                bIdx = self.cb_layer.findText("rgba")
                if bIdx != -1:
                    self.cb_layer.setCurrentIndex(bIdx)
                else:
                    self.cb_layer.setCurrentIndex(0)

        if not wasBlocked:
            self.cb_layer.blockSignals(False)
            self.updateSources(restoreSelection=True)

    @err_catcher(name=__name__)
    def updateSources(self, restoreSelection=False):
        if restoreSelection:
            curSource = self.cb_source.currentText()

        wasBlocked = self.cb_source.signalsBlocked()
        if not wasBlocked:
            self.cb_source.blockSignals(True)
    
        self.cb_source.clear()
        versions = self.getCurrentVersions()
        if len(versions) == 1:
            curAov = self.getCurrentAOV()
            if not curAov:
                curAov = versions[0]

            if curAov:
                mediaFiles = self.core.mediaProducts.getFilesFromContext(curAov)
                validFiles = self.core.media.filterValidMediaFiles(mediaFiles)

                if validFiles:
                    validFiles = sorted(validFiles, key=lambda x: x if "cryptomatte" not in os.path.basename(x) else "zzz" + x)
                    baseName, extension = os.path.splitext(validFiles[0])
                    seqFiles = self.core.media.detectSequences(validFiles)
                    for seqFile in seqFiles:
                        source = curAov.copy()
                        source["source"] = os.path.basename(seqFile)
                        self.cb_source.addItem(source["source"], source)

        selectFirst = True
        if restoreSelection and curSource:
            bIdx = self.cb_source.findText(curSource)
            if bIdx != -1:
                self.cb_source.setCurrentIndex(bIdx)
                selectFirst = False

        if selectFirst:
            self.cb_source.setCurrentIndex(0)

        self.l_source.setHidden(self.cb_source.count() < 2)
        self.cb_source.setHidden(self.cb_source.count() < 2)

        if not wasBlocked:
            self.cb_source.blockSignals(False)
            self.updateFilelayers(restoreSelection=True)

    @err_catcher(name=__name__)
    def updateFilelayers(self, restoreSelection=False, threaded=True, layers=None):
        if restoreSelection:
            curFileLayer = self.cb_filelayer.currentText()

        wasBlocked = self.cb_filelayer.signalsBlocked()
        if not wasBlocked:
            self.cb_filelayer.blockSignals(True)
    
        self.cb_filelayer.clear()
        versions = self.getCurrentVersions()
        if len(versions) == 1 and os.getenv("PRISM_SHOW_EXR_LAYERS") != "0":
            curSource = self.getCurrentSource()
            if curSource:
                mediaFiles = self.core.mediaProducts.getFilesFromContext(curSource)
                validFiles = self.core.media.filterValidMediaFiles(mediaFiles)

                if validFiles:
                    if threaded:
                        layers = ["Loading..."]

                        thread = self.core.worker(self.core)
                        thread.function = lambda: self.getLayersFromFileThreaded(
                            validFiles[0], thread, restoreSelection
                        )
                        thread.errored.connect(self.core.writeErrorLog)
                        thread.finished.connect(self.onWorkerThreadFinished)
                        thread.warningSent.connect(self.core.popup)
                        thread.dataSent.connect(self.onWorkerDataSent)
                        # self.mediaThreads.append(thread)
                        if not getattr(self, "curMediaThread", None):
                            self.curMediaThread = thread
                            thread.start()
                        else:
                            self.nextMediaThread = thread

                    elif layers and layers.get("file") == validFiles[0]:
                        layers = layers.get("layers", [])
                    else:
                        layers = self.core.media.getLayersFromFile(validFiles[0])

                    for flayer in layers:
                        layer = curSource.copy()
                        layer["channel"] = flayer
                        self.cb_filelayer.addItem(layer["channel"], layer)

        selectFirst = True
        if restoreSelection and curFileLayer:
            bIdx = self.cb_filelayer.findText(curFileLayer)
            if bIdx != -1:
                self.cb_filelayer.setCurrentIndex(bIdx)
                selectFirst = False

        if selectFirst:
            self.cb_filelayer.setCurrentIndex(0)

        self.l_filelayer.setHidden(self.cb_filelayer.count() < 2)
        self.cb_filelayer.setHidden(self.cb_filelayer.count() < 2)

        if not wasBlocked:
            self.cb_filelayer.blockSignals(False)
            self.mediaPlayer.updatePreview()

    @err_catcher(name=__name__)
    def getLayersFromFileThreaded(self, filepath, thread, restoreSelection):
        if thread.isInterruptionRequested():
            return

        layers = self.core.media.getLayersFromFile(filepath)
        layerData = {"file": filepath, "layers": layers}
        data = {"function": "updateFilelayers", "args": [], "kwargs": {"restoreSelection": restoreSelection, "threaded": False, "layers": layerData}}
        thread.dataSent.emit(data)

    @err_catcher(name=__name__)
    def onWorkerDataSent(self, data):
        getattr(self, data["function"])(*data["args"], **data["kwargs"])

    @err_catcher(name=__name__)
    def onWorkerThreadFinished(self):
        if getattr(self, "nextMediaThread", None):
            self.curMediaThread = self.nextMediaThread
            self.nextMediaThread = None
            self.curMediaThread.start()
        else:
            self.curMediaThread = None

    @err_catcher(name=__name__)
    def navigate(self, aov=None, source=None, filelayer=None, restoreSelection=False):
        prevLayer = self.getCurrentAOV()
        self.cb_layer.blockSignals(True)
        self.updateLayers(restoreSelection=True)
        if not aov:
            self.cb_layer.blockSignals(False)
            if prevLayer != self.getCurrentAOV() or not self.origin.initialized:
                self.layerChanged()
                return True

            return

        idx = self.cb_layer.findText(aov)
        if idx != -1:
            self.cb_layer.setCurrentIndex(idx)

        self.cb_layer.blockSignals(False)
        prevSource = self.getCurrentSource()
        self.cb_source.blockSignals(True)
        if prevLayer != self.getCurrentAOV():
            self.layerChanged()

        if not source:
            self.cb_source.blockSignals(False)
            if prevSource != self.getCurrentSource() or not self.origin.initialized:
                self.sourceChanged()
                return True

            return

        idx = self.cb_source.findText(aov)
        if idx != -1:
            self.cb_source.setCurrentIndex(idx)

        self.cb_source.blockSignals(False)
        prevFilelayer = self.getCurrentFilelayer()
        self.cb_filelayer.blockSignals(True)
        if prevSource != self.getCurrentSource():
            self.sourceChanged()

        if not filelayer:
            self.cb_filelayer.blockSignals(False)
            if prevFilelayer != self.getCurrentFilelayer() or not self.origin.initialized:
                self.filelayerChanged()
                return True

            return

        idx = self.cb_filelayer.findText(aov)
        if idx != -1:
            self.cb_filelayer.setCurrentIndex(idx)

        self.cb_filelayer.blockSignals(False)
        if prevFilelayer != self.getCurrentFilelayer():
            self.filelayerChanged()
            return True

    @err_catcher(name=__name__)
    def rclLayer(self, pos):
        cpos = QCursor.pos()
        if not hasattr(self.origin, "getCurrentIdentifier"):
            return

        identifier = self.origin.getCurrentIdentifier()
        if identifier["mediaType"] != "3drenders":
            return

        data = self.getCurrentAOV()
        if data:
            path = data["path"]
        else:
            version = self.origin.getCurrentVersion()
            if not version:
                return

            path = self.core.mediaProducts.getAovPathFromVersion(version)

        rcmenu = QMenu(self)

        depAct = QAction("Create AOV...", self)
        depAct.triggered.connect(self.createAovDlg)
        rcmenu.addAction(depAct)

        act_refresh = QAction("Refresh", self)
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "refresh.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        act_refresh.setIcon(icon)
        act_refresh.triggered.connect(lambda: self.updateLayers(restoreSelection=True))
        rcmenu.addAction(act_refresh)

        if os.path.exists(path):
            opAct = QAction("Open in Explorer", self)
            opAct.triggered.connect(lambda: self.core.openFolder(path))
            rcmenu.addAction(opAct)

            copAct = QAction("Copy", self)
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "copy.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            copAct.setIcon(icon)
            copAct.triggered.connect(lambda: self.core.copyToClipboard(path, file=True))
            rcmenu.addAction(copAct)

        if rcmenu.isEmpty():
            return False

        rcmenu.exec_(cpos)

    @err_catcher(name=__name__)
    def createAovDlg(self):
        entity = self.origin.getCurrentEntity()
        identifier = self.origin.getCurrentIdentifier().get("identifier")
        version = identifier = self.origin.getCurrentVersion().get("version")
        context = entity.copy()
        context["identifier"] = identifier
        context["version"] = version

        self.newItem = PrismWidgets.CreateItem(
            core=self.core, showType=False, mode="aov", startText="rgb"
        )
        self.newItem.setModal(True)
        self.core.parentWindow(self.newItem)
        self.newItem.e_item.setFocus()
        self.newItem.setWindowTitle("Create AOV")
        self.newItem.l_item.setText("AOV:")
        self.newItem.accepted.connect(self.createAov)
        self.core.callback(name="onCreateAovDlgOpen", args=[self, self.newItem])
        self.newItem.show()

    @err_catcher(name=__name__)
    def createAov(self):
        self.activateWindow()
        itemName = self.newItem.e_item.text()
        curEntity = self.origin.getCurrentEntity()
        identifier = self.origin.getCurrentIdentifier().get("identifier")
        version = self.origin.getCurrentVersion().get("version")
        self.core.mediaProducts.createAov(entity=curEntity, identifier=identifier, version=version, aov=itemName)
        self.updateLayers()
        if itemName is not None:
            idx = self.cb_layer.findText(itemName)
            if idx != -1:
                self.cb_layer.setCurrentIndex(idx)


class MediaPlayer(QWidget):
    def __init__(self, origin):
        super(MediaPlayer, self).__init__()
        self.mediaVersionPlayer = origin
        self.origin = self.mediaVersionPlayer.origin
        self.core = self.origin.core

        self.renderResX = 300
        self.renderResY = 169
        self.videoReaders = {}
        self.currentMediaPreview = None
        self.mediaThreads = []
        self.timeline = None
        self.tlPaused = False
        self.seq = []
        self.pduration = 0
        self.pwidth = 0
        self.pheight = 0
        self.pstart = 0
        self.pend = 0
        self.openMediaPlayer = False
        self.emptypmap = self.createPMap(self.renderResX, self.renderResY)
        self.previewTooltip = "Left mouse drag to drag media files.\nCtrl+Left mouse drag to drag media folder."
        self.previewEnabled = True
        self.state = "enabled"
        self.core.registerCallback("onUserSettingsSave", self.onUserSettingsSave)
        self.updateExternalMediaPlayer()
        self.setupUi()
        self.connectEvents()

    @err_catcher(name=__name__)
    def sizeHint(self):
        return QSize(400, 100)

    @err_catcher(name=__name__)
    def setupUi(self):
        self.lo_main = QVBoxLayout(self)
        self.lo_main.setContentsMargins(0, 0, 0, 0)
        self.l_info = QLabel(self)
        self.l_info.setText("")
        self.l_info.setObjectName("l_info")
        self.lo_main.addWidget(self.l_info)
        self.l_preview = QLabel(self)
        self.l_preview.setContextMenuPolicy(Qt.CustomContextMenu)
        self.l_preview.setText("")
        self.l_preview.setAlignment(Qt.AlignCenter)
        self.l_preview.setObjectName("l_preview")
        self.lo_main.addWidget(self.l_preview)

        self.l_loading = QLabel(self)
        self.l_loading.setAlignment(Qt.AlignCenter)
        self.l_loading.setVisible(False)

        self.w_timeslider = QWidget()
        self.lo_timeslider = QHBoxLayout(self.w_timeslider)
        self.lo_timeslider.setContentsMargins(0, 0, 0, 0)
        self.l_start = QLabel()
        self.l_end = QLabel()
        self.sl_preview = QSlider(self)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sl_preview.sizePolicy().hasHeightForWidth())
        self.sl_preview.setSizePolicy(sizePolicy)
        self.sl_preview.setOrientation(Qt.Horizontal)
        self.sl_preview.setObjectName("sl_preview")
        self.sl_preview.setMaximum(999)
        self.lo_timeslider.addWidget(self.l_start)
        self.lo_timeslider.addWidget(self.sl_preview)
        self.lo_timeslider.addWidget(self.l_end)
        self.sp_current = QSpinBox()
        self.sp_current.sizeHint = lambda: QSize(30, 0)
        self.sp_current.setStyleSheet("min-width: 30px;")
        self.sp_current.setValue(self.pstart)
        self.sp_current.setButtonSymbols(QAbstractSpinBox.NoButtons)
        sizePolicy = self.sp_current.sizePolicy()
        sizePolicy.setHorizontalPolicy(QSizePolicy.Preferred)
        self.sp_current.setSizePolicy(sizePolicy)
        self.lo_timeslider.addWidget(self.sp_current)
        self.lo_main.addWidget(self.w_timeslider)

        self.w_playerCtrls = QWidget()
        self.lo_playerCtrls = QHBoxLayout(self.w_playerCtrls)
        self.lo_playerCtrls.setContentsMargins(0, 0, 0, 0)
        
        self.b_first = QToolButton()
        self.b_first.clicked.connect(self.onFirstClicked)
        self.b_prev = QToolButton()
        self.b_prev.clicked.connect(self.onPrevClicked)
        self.b_play = QToolButton()
        self.b_play.clicked.connect(self.onPlayClicked)
        self.b_next = QToolButton()
        self.b_next.clicked.connect(self.onNextClicked)
        self.b_last = QToolButton()
        self.b_last.clicked.connect(self.onLastClicked)
        
        self.lo_playerCtrls.addWidget(self.b_first)
        self.lo_playerCtrls.addStretch()
        self.lo_playerCtrls.addWidget(self.b_prev)
        self.lo_playerCtrls.addWidget(self.b_play)
        self.lo_playerCtrls.addWidget(self.b_next)
        self.lo_playerCtrls.addStretch()
        self.lo_playerCtrls.addWidget(self.b_last)
        self.lo_main.addWidget(self.w_playerCtrls)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "first.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_first.setIcon(icon)
        self.b_first.setToolTip("First Frame")

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "prev.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_prev.setIcon(icon)
        self.b_prev.setToolTip("Previous Frame")

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "play.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_play.setIcon(icon)
        self.b_play.setToolTip("Play")

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "next.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_next.setIcon(icon)
        self.b_next.setToolTip("Next Frame")

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "last.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_last.setIcon(icon)
        self.b_last.setToolTip("Last Frame")

        if self.core.appPlugin.pluginName != "Standalone":
            ssheet = "QWidget{padding: 0; border-width: 0px;background-color: transparent} QWidget:hover{border-width: 0px;background-color: rgba(255,255,255,50) }"
            self.b_first.setStyleSheet(ssheet)
            self.b_prev.setStyleSheet(ssheet)
            self.b_play.setStyleSheet(ssheet)
            self.b_next.setStyleSheet(ssheet)
            self.b_last.setStyleSheet(ssheet)

        self.l_preview.setAcceptDrops(True)
        self.l_preview.dragEnterEvent = self.previewDragEnterEvent
        self.l_preview.dragMoveEvent = self.previewDragMoveEvent
        self.l_preview.dragLeaveEvent = self.previewDragLeaveEvent
        self.l_preview.dropEvent = self.previewDropEvent
        self.l_preview.setStyleSheet("QWidget { border-style: dashed; border-color: rgba(0, 0, 0, 0);  border-width: 2px; }")

        self.l_preview.setMinimumWidth(self.renderResX)
        self.l_preview.setMinimumHeight(self.renderResY)
        self.l_preview.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.l_preview.clickEvent = self.l_preview.mouseReleaseEvent
        self.l_preview.mouseReleaseEvent = self.previewClk
        self.l_preview.dclickEvent = self.l_preview.mouseDoubleClickEvent
        self.l_preview.mouseDoubleClickEvent = self.previewDclk
        self.l_preview.resizeEventOrig = self.l_preview.resizeEvent
        self.l_preview.resizeEvent = self.previewResizeEvent
        self.l_preview.customContextMenuRequested.connect(self.rclPreview)
        self.l_preview.mouseMoveEvent = lambda x: self.mouseDrag(x, self.l_preview)

        self.sl_preview.valueChanged.connect(self.sliderChanged)
        self.sl_preview.sliderPressed.connect(self.sliderClk)
        self.sl_preview.sliderReleased.connect(self.sliderRls)
        self.sl_preview.origMousePressEvent = self.sl_preview.mousePressEvent
        self.sl_preview.mousePressEvent = self.sliderDrag
        self.sp_current.valueChanged.connect(self.onCurrentChanged)

    @err_catcher(name=__name__)
    def onUserSettingsSave(self, origin):
        self.updateExternalMediaPlayer()

    @err_catcher(name=__name__)
    def setPreviewEnabled(self, state):
        self.previewEnabled = state
        self.l_preview.setVisible(state)
        self.w_timeslider.setVisible(state)
        self.w_playerCtrls.setVisible(state)

    @err_catcher(name=__name__)
    def onFirstClicked(self):
        self.timeline.setCurrentTime(0)

    @err_catcher(name=__name__)
    def onPrevClicked(self):
        time = self.timeline.currentTime() - self.timeline.updateInterval()
        if time < 0:
            time = self.timeline.duration() - self.timeline.updateInterval()

        self.timeline.setCurrentTime(time)

    @err_catcher(name=__name__)
    def onPlayClicked(self):
        if not self.seq:
            return

        self.setTimelinePaused(self.timeline.state() == QTimeLine.Running)

    @err_catcher(name=__name__)
    def onNextClicked(self):
        time = self.timeline.currentTime() + self.timeline.updateInterval()
        time = min(self.timeline.duration(), time)
        self.timeline.setCurrentTime(time)

    @err_catcher(name=__name__)
    def onLastClicked(self):
        self.timeline.setCurrentTime(self.timeline.updateInterval() * (self.pduration - 1))

    @err_catcher(name=__name__)
    def sliderChanged(self, val):
        if not self.seq:
            return

        time = int(val / self.sl_preview.maximum() * self.timeline.duration())
        if time == self.timeline.duration():
            time -= 1

        self.timeline.setCurrentTime(time)

    @err_catcher(name=__name__)
    def onCurrentChanged(self, value):
        if not self.timeline:
            return

        time = (value - self.pstart) * self.timeline.updateInterval()
        self.timeline.setCurrentTime(time)

    @err_catcher(name=__name__)
    def getAutoplay(self):
        if not getattr(self.origin, "projectBrowser", None):
            return

        return self.origin.projectBrowser.actionAutoplay.isChecked()

    @err_catcher(name=__name__)
    def getSelectedContexts(self):
        return self.origin.getSelectedContexts()

    @err_catcher(name=__name__)
    def getFilesFromContext(self, context):
        return self.core.mediaProducts.getFilesFromContext(context)

    @err_catcher(name=__name__)
    def updatePreview(self, regenerateThumb=False):
        if not self.previewEnabled:
            return

        if self.timeline:
            curFrame = self.getCurrentFrame()
            if self.timeline.state() != QTimeLine.NotRunning:
                if self.timeline.state() == QTimeLine.Running:
                    self.tlPaused = False
                elif self.timeline.state() == QTimeLine.Paused:
                    self.tlPaused = True

                self.timeline.stop()
        else:
            self.tlPaused = not self.getAutoplay()
            curFrame = 0

        for thread in reversed(self.mediaThreads):
            if thread.isRunning():
                thread.requestInterruption()

        prevFrame = self.pstart + curFrame
        self.sl_preview.setValue(0)
        self.sp_current.setValue(0)
        self.seq = []
        self.prvIsSequence = False

        QPixmapCache.clear()
        for videoReader in self.videoReaders:
            if not self.core.isStr(self.videoReaders[videoReader]):
                try:
                    self.videoReaders[videoReader].close()
                except:
                    pass

        self.videoReaders = {}

        contexts = self.getSelectedContexts()
        if len(contexts) > 1:
            self.l_info.setText("\nMultiple items selected\n")
            self.l_info.setToolTip("")
            self.l_preview.setToolTip("")
        else:
            if contexts:
                mediaFiles = self.getFilesFromContext(contexts[0])
                validFiles = self.core.media.filterValidMediaFiles(mediaFiles)

                if validFiles:
                    validFiles = sorted(validFiles, key=lambda x: x if "cryptomatte" not in os.path.basename(x) else "zzz" + x)
                    baseName, extension = os.path.splitext(validFiles[0])
                    seqFiles = self.core.media.detectSequence(validFiles)

                    if (
                        len(seqFiles) > 1
                        and extension not in self.core.media.videoFormats
                    ):
                        self.seq = seqFiles
                        self.prvIsSequence = True
                        (
                            self.pstart,
                            self.pend,
                        ) = self.core.media.getFrameRangeFromSequence(seqFiles)
                    else:
                        self.prvIsSequence = False
                        self.seq = validFiles

                    self.pduration = len(self.seq)
                    imgPath = validFiles[0]
                    if (
                        self.pduration == 1
                        and os.path.splitext(imgPath)[1] in self.core.media.videoFormats
                    ):
                        self.vidPrw = "loading"
                        self.updatePrvInfo(
                            imgPath,
                            vidReader="loading",
                            frame=prevFrame,
                        )
                    else:
                        self.updatePrvInfo(imgPath, frame=prevFrame)

                    if self.tlPaused:
                        self.changeImage_threaded(regenerateThumb=regenerateThumb)
                    elif self.pduration < 3:
                        self.changeImage_threaded(regenerateThumb=regenerateThumb)

                    return True

            self.updatePrvInfo()

        pmap = self.core.media.scalePixmap(self.emptypmap, self.getThumbnailWidth(), self.getThumbnailHeight())
        self.currentMediaPreview = pmap
        self.l_preview.setPixmap(pmap)
        self.sl_preview.setEnabled(False)
        self.l_start.setText("")
        self.l_end.setText("")
        self.w_playerCtrls.setEnabled(False)
        self.sp_current.setEnabled(False)

    @err_catcher(name=__name__)
    def updatePrvInfo(self, prvFile="", vidReader=None, seq=None, frame=None):
        if seq is not None:
            if self.seq != seq:
                logger.debug("exit preview info update")
                return

        if not os.path.exists(prvFile):
            self.l_info.setText("\nNo image found\n")
            self.l_info.setToolTip("")
            self.l_preview.setToolTip("")
            return

        if self.state == "disabled" or os.getenv("PRISM_DISPLAY_MEDIA_RESOLUTION") == "0":
            self.pwidth = "?"
            self.pheight = "?"
        else:
            if vidReader == "loading":
                self.pwidth = "loading..."
                self.pheight = ""
            else:
                resolution = self.core.media.getMediaResolution(prvFile, videoReader=vidReader)
                self.pwidth = resolution["width"]
                self.pheight = resolution["height"]

        ext = os.path.splitext(prvFile)[1]
        if ext in self.core.media.videoFormats:
            if len(self.seq) == 1:
                if self.core.isStr(vidReader) or self.state == "disabled":
                    duration = 1
                else:
                    duration = self.core.media.getVideoDuration(prvFile, videoReader=vidReader)
                    if not duration:
                        duration = 1

                self.pduration = duration

        self.pformat = "*" + ext

        pdate = self.core.getFileModificationDate(prvFile)
        self.sl_preview.setEnabled(True)
        start = "1"
        end = "1"
        if self.prvIsSequence:
            start = str(self.pstart)
            end = str(self.pend)
        elif ext in self.core.media.videoFormats:
            if self.pwidth != "?":
                end = str(int(start) + self.pduration - 1)

        self.l_start.setText(start)
        self.l_end.setText(end)
        self.sp_current.setMinimum(int(start))
        self.sp_current.setMaximum(int(end))
        self.w_playerCtrls.setEnabled(True)
        self.sp_current.setEnabled(True)

        if self.timeline:
            self.timeline.stop()

        fps = self.core.projects.getFps() or 25
        self.timeline = QTimeLine(
            int(1000/float(fps)) * self.pduration, self
        )
        self.timeline.setEasingCurve(QEasingCurve.Linear)
        self.timeline.setLoopCount(0)
        self.timeline.setUpdateInterval(int(1000/float(fps)))
        self.timeline.valueChanged.connect(
            lambda x: self.changeImg(x)
        )
        QPixmapCache.setCacheLimit(2097151)
        frame = frame or self.pstart
        if frame != self.sp_current.value():
            self.sp_current.setValue(frame)
        else:
            self.onCurrentChanged(self.sp_current.value())

        self.timeline.resume()

        if self.tlPaused or self.state == "disabled":
            self.setTimelinePaused(True)

        if self.pduration == 1:
            frStr = "frame"
        else:
            frStr = "frames"

        width = self.pwidth if self.pwidth is not None else "?"
        height = self.pheight if self.pheight is not None else "?"

        if self.prvIsSequence:
            infoStr = "%sx%s   %s   %s-%s (%s %s)" % (
                width,
                height,
                self.pformat,
                self.pstart,
                self.pend,
                self.pduration,
                frStr,
            )
        elif len(self.seq) > 1:
            infoStr = "%s files %sx%s   %s\n%s" % (
                self.pduration,
                width,
                height,
                self.pformat,
                os.path.basename(prvFile),
            )
        elif ext in self.core.media.videoFormats:
            if self.pwidth == "?":
                duration = "?"
                frStr = "frames"
            else:
                duration = self.pduration

            if self.pwidth == "loading...":
                infoStr = "\n" + os.path.basename(prvFile)
            else:
                infoStr = "%sx%s   %s %s\n%s" % (
                    width,
                    height,
                    duration,
                    frStr,
                    os.path.basename(prvFile),
                )
                if self.core.isStr(duration) or duration <= 1:
                    self.sl_preview.setEnabled(False)
                    self.l_start.setText("")
                    self.l_end.setText("")
                    self.w_playerCtrls.setEnabled(False)
                    self.sp_current.setEnabled(False)
        else:
            infoStr = "%sx%s\n%s" % (
                width,
                height,
                os.path.basename(prvFile),
            )
            self.sl_preview.setEnabled(False)
            self.l_start.setText("")
            self.l_end.setText("")
            self.w_playerCtrls.setEnabled(False)
            self.sp_current.setEnabled(False)

        infoStr += "\n" + pdate

        if self.core.getConfig("globals", "showFileSizes"):
            size = 0
            for file in self.seq:
                if os.path.exists(file):
                    size += float(os.stat(file).st_size / 1024.0 / 1024.0)

            infoStr += " - %.2f mb" % size

        if self.state == "disabled":
            infoStr += "\nPreview is disabled"
            self.sl_preview.setEnabled(False)
            self.w_playerCtrls.setEnabled(False)
            self.sp_current.setEnabled(False)

        self.setInfoText(infoStr)
        self.l_info.setToolTip(infoStr)
        self.l_preview.setToolTip(self.previewTooltip)

    @err_catcher(name=__name__)
    def setInfoText(self, text):
        metrics = QFontMetrics(self.l_info.font())
        lines = []
        for line in text.split("\n"):
            elidedText = metrics.elidedText(line, Qt.ElideRight, self.l_preview.width()-20)
            lines.append(elidedText)

        self.l_info.setText("\n".join(lines))

    @err_catcher(name=__name__)
    def createPMap(self, resx, resy):
        fbFolder = self.core.projects.getFallbackFolder()
        if resx == 300:
            imgFile = os.path.join(fbFolder, "noFileBig.jpg")
        else:
            imgFile = os.path.join(fbFolder, "noFileSmall.jpg")

        return self.core.media.getPixmapFromPath(imgFile)

    @err_catcher(name=__name__)
    def moveLoadingLabel(self):
        geo = QRect()
        pos = self.l_preview.parent().mapToGlobal(self.l_preview.geometry().topLeft())
        pos = self.mapFromGlobal(pos)
        geo.setWidth(self.l_preview.width())
        geo.setHeight(self.l_preview.height())
        geo.moveTopLeft(pos)
        self.l_loading.setGeometry(geo)

    @err_catcher(name=__name__)
    def changeImage_threaded(self, frame=0, regenerateThumb=False):
        for thread in reversed(self.mediaThreads):
            if thread.isRunning():
                thread.requestInterruption()
            else:
                self.mediaThreads.remove(thread)

        self.moveLoadingLabel()
        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "loading.gif"
        )
        self.loadingGif = QMovie(path, QByteArray(), self) 
        self.loadingGif.setCacheMode(QMovie.CacheAll) 
        self.loadingGif.setSpeed(100) 
        self.l_loading.setMovie(self.loadingGif)
        self.loadingGif.start()
        self.l_loading.setVisible(True)

        if (self.getSelectedContexts() or [{}])[0].get("channel") == "Loading...":
            return

        thread = self.core.worker(self.core)
        thread.function = lambda x=list(self.seq): self.changeImg(
            frame=frame, seq=x, thread=thread, regenerateThumb=regenerateThumb
        )
        thread.errored.connect(self.core.writeErrorLog)
        thread.finished.connect(self.onMediaThreadFinished)
        thread.warningSent.connect(self.core.popup)
        thread.dataSent.connect(self.onChangeImgDataSent)
        # self.mediaThreads.append(thread)
        if not getattr(self, "curMediaThread", None):
            self.curMediaThread = thread
            thread.start()
        else:
            self.nextMediaThread = thread

    @err_catcher(name=__name__)
    def onMediaThreadFinished(self):
        if getattr(self, "nextMediaThread", None):
            self.curMediaThread = self.nextMediaThread
            self.nextMediaThread = None
            self.curMediaThread.start()
        else:
            self.curMediaThread = None
            self.l_loading.setVisible(False)
            self.loadingGif.stop()

    @err_catcher(name=__name__)
    def onChangeImgDataSent(self, data):
        getattr(self, data["function"])(*data["args"], **data["kwargs"])

    @err_catcher(name=__name__)
    def getThumbnailWidth(self):
        return self.l_preview.width()

    @err_catcher(name=__name__)
    def getThumbnailHeight(self):
        return self.l_preview.height()

    @err_catcher(name=__name__)
    def getCurrentFrame(self):
        if not self.timeline:
            return

        return int(self.timeline.currentTime() / self.timeline.updateInterval())

    @err_catcher(name=__name__)
    def changeImg(self, frame=0, seq=None, thread=None, regenerateThumb=False):
        if seq is not None:
            if self.seq != seq:
                logger.debug("exit thread")
                return

        if thread and thread.isInterruptionRequested():
            return

        if not self.seq:
            return

        curFrame = self.getCurrentFrame()
        pmsmall = QPixmap()
        if (
            len(self.seq) == 1
            and os.path.splitext(self.seq[0])[1]
            in self.core.media.videoFormats
        ):
            fileName = self.seq[0]
        else:
            fileName = self.seq[curFrame]

        _, ext = os.path.splitext(fileName)
        if self.state == "disabled":
            pmsmall = self.core.media.scalePixmap(self.emptypmap, self.getThumbnailWidth(), self.getThumbnailHeight())
        else:
            pmsmall = QPixmapCache.find(("Frame" + str(curFrame)))
            if not pmsmall:
                if ext in [
                    ".jpg",
                    ".jpeg",
                    ".JPG",
                    ".png",
                    ".PNG",
                    ".tif",
                    ".tiff",
                    ".tga"
                ]:
                    pm = self.core.media.getPixmapFromPath(fileName, self.getThumbnailWidth(), self.getThumbnailHeight(), colorAdjust=True)
                    if pm:
                        if pm.width() == 0 or pm.height() == 0:
                            filename = "%s.jpg" % ext[1:].lower()
                            imgPath = os.path.join(
                                self.core.projects.getFallbackFolder(), filename
                            )
                            pmsmall = self.core.media.getPixmapFromPath(imgPath)
                            pmsmall = self.core.media.scalePixmap(
                                pmsmall, self.getThumbnailWidth(), self.getThumbnailHeight()
                            )
                        elif (pm.width() / float(pm.height())) > 1.7778:
                            pmsmall = pm.scaledToWidth(self.getThumbnailWidth())
                        else:
                            pmsmall = pm.scaledToHeight(self.getThumbnailHeight())
                    else:
                        pmsmall = self.core.media.getPixmapFromPath(
                            os.path.join(
                                self.core.projects.getFallbackFolder(),
                                "%s.jpg" % ext[1:].lower(),
                            )
                        )
                        pmsmall = self.core.media.scalePixmap(
                            pmsmall, self.getThumbnailWidth(), self.getThumbnailHeight()
                        )
                elif ext in [".exr", ".dpx", ".hdr"]:
                    channel = (self.getSelectedContexts() or [{}])[0].get("channel")
                    try:
                        pmsmall = self.core.media.getPixmapFromExrPath(
                            fileName,
                            self.getThumbnailWidth(),
                            self.getThumbnailHeight(),
                            channel=channel,
                            allowThumb=self.mediaVersionPlayer.cb_filelayer.currentIndex() == 0,
                            regenerateThumb=regenerateThumb,
                        )
                        if not pmsmall:
                            raise RuntimeError("no image loader available")
                    except Exception as e:
                        logger.debug(e)
                        pmsmall = self.core.media.getPixmapFromPath(
                            os.path.join(
                                self.core.projects.getFallbackFolder(),
                                "%s.jpg" % ext[1:].lower(),
                            )
                        )
                        pmsmall = self.core.media.scalePixmap(
                            pmsmall, self.getThumbnailWidth(), self.getThumbnailHeight()
                        )
                elif ext in self.core.media.videoFormats:
                    try:
                        if len(self.seq) > 1:
                            imgNum = 0
                            vidFile = self.core.media.getVideoReader(fileName)
                        else:
                            imgNum = curFrame
                            vidFile = self.vidPrw
                            if vidFile == "loading":
                                if fileName in self.videoReaders:
                                    vidFile = self.videoReaders[fileName]
                                else:
                                    self.vidPrw = self.core.media.getVideoReader(fileName)
                                    vidFile = self.vidPrw
                                    if self.core.isStr(vidFile):
                                        logger.warning(vidFile)

                                    self.videoReaders[fileName] = vidFile

                                if thread:
                                    data = {"function": "updatePrvInfo", "args": [fileName], "kwargs": {"vidReader": vidFile, "seq": seq}}
                                    thread.dataSent.emit(data)
                                else:
                                    self.updatePrvInfo(fileName, vidReader=vidFile, seq=seq)

                        pm = self.core.media.getPixmapFromVideoPath(
                                fileName,
                                videoReader=vidFile,
                                imgNum=imgNum,
                                regenerateThumb=regenerateThumb
                            )
                        pmsmall = self.core.media.scalePixmap(
                            pm, self.getThumbnailWidth(), self.getThumbnailHeight()
                        )
                    except Exception as e:
                        logger.debug(traceback.format_exc())
                        imgPath = os.path.join(
                            self.core.projects.getFallbackFolder(),
                            "%s.jpg" % ext[1:].lower(),
                        )
                        pmsmall = self.core.media.getPixmapFromPath(imgPath)
                        pmsmall = self.core.media.scalePixmap(
                            pmsmall, self.getThumbnailWidth(), self.getThumbnailHeight()
                        )
                else:
                    return False

                if seq is not None:
                    if self.seq != seq:
                        logger.debug("exit preview update")
                        return

                QPixmapCache.insert(("Frame" + str(curFrame)), pmsmall)

        if not self.prvIsSequence and len(self.seq) > 1:
            fileName = self.seq[curFrame]
            if thread:
                thread.dataSent.emit({"function": "updatePrvInfo", "args": [fileName], "kwargs": {"seq": seq}})
            else:
                self.updatePrvInfo(fileName, seq=seq)

        if thread:
            thread.dataSent.emit({"function": "completeChangeImg", "args": [pmsmall, curFrame, ext], "kwargs": {}})
        else:
            self.completeChangeImg(pmsmall, curFrame, ext)

    @err_catcher(name=__name__)
    def completeChangeImg(self, pmsmall, curFrame, ext):
        self.currentMediaPreview = pmsmall
        self.l_preview.setPixmap(pmsmall)
        if self.pduration > 1:
            newVal = int(self.sl_preview.maximum() * (curFrame / float(self.pduration-1)))
        else:
            newVal = 0

        curSliderVal = int((self.sl_preview.value() / self.sl_preview.maximum()) * float(self.pduration))
        if curSliderVal != curFrame:
            self.sl_preview.blockSignals(True)
            self.sl_preview.setValue(newVal)
            self.sl_preview.blockSignals(False)

        if ext in self.core.media.videoFormats:
            curFrame += 1

        if self.sp_current.value() != (self.pstart + curFrame):
            self.sp_current.blockSignals(True)
            self.sp_current.setValue((self.pstart + curFrame))
            self.sp_current.blockSignals(False)

    @err_catcher(name=__name__)
    def setTimelinePaused(self, state):
        self.timeline.setPaused(state)
        if state:
            path = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "play.png"
            )
            icon = self.core.media.getColoredIcon(path)
            self.b_play.setIcon(icon)
            self.b_play.setToolTip("Play")
        else:
            path = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "pause.png"
            )
            icon = self.core.media.getColoredIcon(path)
            self.b_play.setIcon(icon)
            self.b_play.setToolTip("Pause")

    @err_catcher(name=__name__)
    def previewClk(self, event):
        if (len(self.seq) > 1 or self.pduration > 1) and event.button() == Qt.LeftButton:
            if (
                self.timeline.state() == QTimeLine.Paused
                and not self.openMediaPlayer
            ):
                self.setTimelinePaused(False)
            else:
                if self.timeline.state() == QTimeLine.Running:
                    self.setTimelinePaused(True)
                self.openMediaPlayer = False
        self.l_preview.clickEvent(event)

    @err_catcher(name=__name__)
    def previewDclk(self, event):
        if self.seq != [] and event.button() == Qt.LeftButton:
            self.openMediaPlayer = True
            self.compare()

        self.l_preview.dclickEvent(event)

    @err_catcher(name=__name__)
    def rclPreview(self, pos):
        menu = self.getMediaPreviewMenu()
        self.core.callback(
            name="mediaPlayerContextMenuRequested",
            args=[self, menu],
        )
        if not menu or menu.isEmpty():
            return

        menu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def getMediaPreviewMenu(self):
        contexts = self.getCurRenders()
        if not contexts or not contexts[0].get("version"):
            return

        data = contexts[0]
        path = data["path"]

        if not path:
            return

        rcmenu = QMenu(self)

        if self.core.appPlugin.appType == "2d" and len(self.seq) > 0 and hasattr(self.core.appPlugin, "importImages"):
            impAct = QAction("Import images...", self)
            impAct.triggered.connect(lambda: self.core.appPlugin.importImages(self))
            rcmenu.addAction(impAct)

        if len(self.seq) > 0:
            if len(self.seq) == 1:
                path = os.path.join(path, self.seq[0])

            playMenu = QMenu("Play in", self)
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "play.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            playMenu.setIcon(icon)

            if self.mediaPlayerPath is not None:
                pAct = QAction(self.mediaPlayerName, self)
                pAct.triggered.connect(self.compare)
                playMenu.addAction(pAct)

            pAct = QAction("Default", self)
            pAct.triggered.connect(
                lambda: self.compare(prog="default")
            )
            playMenu.addAction(pAct)
            rcmenu.addMenu(playMenu)

        if len(self.seq) == 1 or self.prvIsSequence:
            cvtMenu = QMenu("Convert", self)
            qtAct = QAction("jpg", self)
            qtAct.triggered.connect(
                lambda: self.convertImgs(".jpg")
            )
            cvtMenu.addAction(qtAct)
            qtAct = QAction("png", self)
            qtAct.triggered.connect(
                lambda: self.convertImgs(".png")
            )
            cvtMenu.addAction(qtAct)
            qtAct = QAction("mp4", self)
            qtAct.triggered.connect(
                lambda: self.convertImgs(".mp4")
            )
            cvtMenu.addAction(qtAct)

            settings = OrderedDict()
            settings["-c"] = "prores"
            settings["-profile"] = 2
            settings["-pix_fmt"] = "yuv422p10le"

            movAct = QAction("mov (prores 422)", self)
            movAct.triggered.connect(
                lambda x=None, s=settings: self.convertImgs(".mov", settings=s)
            )
            cvtMenu.addAction(movAct)
            rcmenu.addMenu(cvtMenu)

            settings = OrderedDict()
            settings["-c"] = "prores"
            settings["-profile"] = 4
            settings["-pix_fmt"] = "yuva444p10le"

            movAct = QAction("mov (prores 4444)", self)
            movAct.triggered.connect(
                lambda x=None, s=settings: self.convertImgs(".mov", settings=s)
            )
            cvtMenu.addAction(movAct)
            rcmenu.addMenu(cvtMenu)

        if (
            len(self.seq) == 1
            and os.path.splitext(self.seq[0])[1]
            in self.core.media.videoFormats
        ):
            curSeqIdx = 0
        else:
            curSeqIdx = self.getCurrentFrame()

        if len(self.seq) > 0 and self.core.media.getUseThumbnailForFile(self.seq[curSeqIdx]):
            prvAct = QAction("Use thumbnail", self)
            prvAct.setCheckable(True)
            prvAct.setChecked(self.core.media.getUseThumbnails())
            prvAct.toggled.connect(self.core.media.setUseThumbnails)
            prvAct.triggered.connect(self.updatePreview)
            rcmenu.addAction(prvAct)

            if self.core.media.getUseThumbnails():
                prvAct = QAction("Regenerate thumbnail", self)
                prvAct.triggered.connect(self.regenerateThumbnail)
                rcmenu.addAction(prvAct)

        if len(self.seq) > 0 and hasattr(self.origin, "getCurrentEntity"):
            entity = self.origin.getCurrentEntity()
            if entity["type"] == "asset":
                prvAct = QAction("Set as assetpreview", self)
                prvAct.triggered.connect(self.origin.setPreview)
                rcmenu.addAction(prvAct)

            elif entity["type"] == "shot":
                prvAct = QAction("Set as shotpreview", self)
                prvAct.triggered.connect(self.origin.setPreview)
                rcmenu.addAction(prvAct)

        act_refresh = QAction("Refresh", self)
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "refresh.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        act_refresh.setIcon(icon)
        act_refresh.triggered.connect(self.updatePreview)
        rcmenu.addAction(act_refresh)

        act_disable = QAction("Disabled", self)
        act_disable.setCheckable(True)
        act_disable.setChecked(self.state == "disabled")
        act_disable.triggered.connect(self.onDisabledTriggered)
        rcmenu.addAction(act_disable)

        exp = QAction("Open in Explorer", self)
        exp.triggered.connect(lambda: self.core.openFolder(path))
        rcmenu.addAction(exp)

        copAct = QAction("Copy", self)
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "copy.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        copAct.setIcon(icon)
        copAct.triggered.connect(lambda: self.core.copyToClipboard(path, file=True))
        rcmenu.addAction(copAct)

        return rcmenu

    @err_catcher(name=__name__)
    def onDisabledTriggered(self):
        if self.state == "enabled":
            self.state = "disabled"
        else:
            self.state = "enabled"

        self.updatePreview()

    @err_catcher(name=__name__)
    def regenerateThumbnail(self):
        self.clearCurrentThumbnails()
        self.updatePreview(regenerateThumb=True)

    @err_catcher(name=__name__)
    def clearCurrentThumbnails(self):
        if not self.seq:
            return

        thumbdir = os.path.dirname(self.core.media.getThumbnailPath(self.seq[0]))
        if not os.path.exists(thumbdir):
            return

        try:
            shutil.rmtree(thumbdir)
        except Exception as e:
            logger.warning("Failed to remove thumbnail: %s" % e)

    @err_catcher(name=__name__)
    def previewResizeEvent(self, event):
        self.l_preview.resizeEventOrig(event)
        height = int(self.l_preview.width()*(self.renderResY/self.renderResX))
        self.l_preview.setMinimumHeight(height)
        self.l_preview.setMaximumHeight(height)
        if self.currentMediaPreview:
            pmap = self.core.media.scalePixmap(
                self.currentMediaPreview, self.getThumbnailWidth(), self.getThumbnailHeight()
            )
            self.l_preview.setPixmap(pmap)

        if hasattr(self, "loadingGif") and self.loadingGif.state() == QMovie.Running:
            self.moveLoadingLabel()

        QPixmapCache.clear()
        text = self.l_info.toolTip()
        if not text:
            text = self.l_info.text()

        self.setInfoText(text)

    @err_catcher(name=__name__)
    def sliderDrag(self, event):
        custEvent = QMouseEvent(
            QEvent.MouseButtonPress,
            event.pos(),
            Qt.MidButton,
            Qt.MidButton,
            Qt.NoModifier,
        )
        self.sl_preview.origMousePressEvent(custEvent)

    @err_catcher(name=__name__)
    def sliderClk(self):
        if (
            self.timeline
            and self.timeline.state() == QTimeLine.Running
        ):
            self.slStop = True
            self.setTimelinePaused(True)
        else:
            self.slStop = False

    @err_catcher(name=__name__)
    def sliderRls(self):
        if self.slStop:
            self.setTimelinePaused(False)

    @err_catcher(name=__name__)
    def previewDragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            dragPath = os.path.normpath(e.mimeData().urls()[0].toLocalFile())
            if self.seq:
                path = os.path.dirname(self.seq[0])
            else:
                path = ""

            if not dragPath or os.path.dirname(dragPath.strip("/\\")) == path.strip("/\\"):
                e.ignore()
            else:
                e.accept()
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def previewDragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
            self.l_preview.setStyleSheet(
                "QWidget { border-style: dashed; border-color: rgb(100, 200, 100);  border-width: 2px; }"
            )
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def previewDragLeaveEvent(self, e):
        self.l_preview.setStyleSheet("QWidget { border-style: dashed; border-color: rgba(0, 0, 0, 0);  border-width: 2px; }")

    @err_catcher(name=__name__)
    def previewDropEvent(self, e):
        if e.mimeData().hasUrls():
            self.l_preview.setStyleSheet("QWidget { border-style: dashed; border-color: rgba(0, 0, 0, 0);  border-width: 2px; }")
            e.setDropAction(Qt.LinkAction)
            e.accept()

            files = [
                os.path.normpath(str(url.toLocalFile())) for url in e.mimeData().urls()
            ]
            entity = self.origin.getCurrentEntity()
            self.origin.ingestMedia(entity, files)
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def compare(self, prog=""):
        if (
            self.timeline
            and self.timeline.state() == QTimeLine.Running
        ):
            self.setTimelinePaused(True)

        if prog == "default":
            progPath = ""
        else:
            progPath = self.mediaPlayerPath or ""

        comd = []
        filePath = ""
        contexts = self.getCurRenders()
        if contexts:
            files = self.getFilesFromContext(contexts[0])
            if files:
                filePath = files[0]
                baseName, extension = os.path.splitext(filePath)
                if extension in self.core.media.supportedFormats:
                    if not progPath:
                        cmd = ["start", "", "%s" % self.core.fixPath(filePath)]
                        subprocess.call(cmd, shell=True)
                        return
                    else:
                        if self.mediaPlayerPattern:
                            filePath = self.core.media.getSequenceFromFilename(filePath)

                        comd = [progPath, filePath]

        if comd != []:
            with open(os.devnull, "w") as f:
                logger.debug("launching: %s" % comd)
                try:
                    subprocess.Popen(comd, stdin=subprocess.PIPE, stdout=f, stderr=f)
                except:
                    try:
                        subprocess.Popen(
                            comd, stdin=subprocess.PIPE, stdout=f, stderr=f, shell=True
                        )
                    except Exception as e:
                        raise RuntimeError("%s - %s" % (comd, e))

    @err_catcher(name=__name__)
    def mouseDrag(self, event, element):
        if event.buttons() != Qt.LeftButton:
            return

        contexts = self.getCurRenders()
        urlList = []
        mods = QApplication.keyboardModifiers()
        for context in contexts:
            if mods == Qt.ControlModifier:
                url = os.path.normpath(context["path"])
                urlList.append(url)
            else:
                imgSrc = self.getFilesFromContext(context)
                for k in imgSrc:
                    url = os.path.normpath(k)
                    urlList.append(url)

        if len(urlList) == 0:
            return

        drag = QDrag(self.l_preview)
        mData = QMimeData()
        self.core.callback(name="onPreMediaPlayerDragged", args=[self, urlList])
        urlData = [QUrl.fromLocalFile(urll) for urll in urlList]
        mData.setUrls(urlData)
        drag.setMimeData(mData)

        drag.exec_(Qt.CopyAction | Qt.MoveAction)

    @err_catcher(name=__name__)
    def getCurRenders(self):
        return self.origin.getCurRenders()

    @err_catcher(name=__name__)
    def updateExternalMediaPlayer(self):
        player = self.core.media.getExternalMediaPlayer()
        self.mediaPlayerPath = player.get("path", None)
        self.mediaPlayerName = player.get("name", None)
        self.mediaPlayerPattern = player.get("framePattern", None)

    @err_catcher(name=__name__)
    def getRVdLUT(self):
        dlut = None

        assets = self.core.getConfig("paths", "assets", configPath=self.core.prismIni)

        if assets is not None:
            lutPath = os.path.join(self.core.projectPath, assets, "LUTs", "RV_dLUT")
            if os.path.exists(lutPath) and len(os.listdir(lutPath)) > 0:
                dlut = os.path.join(lutPath, os.listdir(lutPath)[0])

        return dlut

    @err_catcher(name=__name__)
    def convertImgs(self, extension, checkRes=True, settings=None):
        if not extension:
            if settings:
                extension = settings.get("extension")

            if not extension:
                logger.warning("No extension specified")
                return

            settings.pop("extension")

        if extension[0] != ".":
            extension = "." + extension

        inputpath = self.seq[0].replace("\\", "/")
        inputExt = os.path.splitext(inputpath)[1]

        if checkRes:
            if self.pwidth and self.pwidth == "?":
                self.core.popup("Cannot read media file.")
                return

            if (
                extension == ".mp4"
                and self.pwidth is not None
                and self.pheight is not None
                and (
                    int(self.pwidth) % 2 == 1
                    or int(self.pheight) % 2 == 1
                )
            ):
                self.core.popup("Media with odd resolution can't be converted to mp4.")
                return

        conversionSettings = settings or OrderedDict()

        if extension == ".mov" and not settings:
            conversionSettings["-c"] = "prores"
            conversionSettings["-profile"] = 2
            conversionSettings["-pix_fmt"] = "yuv422p10le"

        if self.prvIsSequence:
            inputpath = (
                os.path.splitext(inputpath)[0][: -self.core.framePadding]
                + "%04d".replace("4", str(self.core.framePadding))
                + inputExt
            )

        context = self.origin.getCurrentAOV()
        if not context:
            context = self.origin.getCurrentVersion()
        outputpath = self.core.paths.getMediaConversionOutputPath(
            context, inputpath, extension
        )

        if not outputpath:
            return

        if self.prvIsSequence:
            startNum = self.pstart
        else:
            startNum = 0
            conversionSettings["-start_number"] = None
            conversionSettings["-start_number_out"] = None

        result = self.core.media.convertMedia(
            inputpath, startNum, outputpath, settings=conversionSettings
        )

        if (
            extension not in self.core.media.videoFormats
            and self.prvIsSequence
        ):
            outputpath = outputpath % int(startNum)

        self.origin.updateVersions(restoreSelection=True)

        if os.path.exists(outputpath) and os.stat(outputpath).st_size > 0:
            self.core.copyToClipboard(outputpath, file=True)
            msg = "The images were converted successfully. (path is in clipboard)"
            self.core.popup(msg, severity="info")
        else:
            msg = "The images could not be converted."
            logger.debug("expected outputpath: %s" % outputpath)
            self.core.ffmpegError("Image conversion", msg, result)

    @err_catcher(name=__name__)
    def compGetImportSource(self):
        sourceFolder = os.path.dirname(self.seq[0]).replace("\\", "/")
        sources = self.core.media.getImgSources(sourceFolder)
        sourceData = []

        for curSourcePath in sources:
            if "####" in curSourcePath:
                if self.pstart == "?" or self.pend == "?":
                    firstFrame = None
                    lastFrame = None
                else:
                    firstFrame = self.pstart
                    lastFrame = self.pend

                filePath = curSourcePath.replace("\\", "/")
            else:
                filePath = curSourcePath.replace("\\", "/")
                firstFrame = None
                lastFrame = None

            sourceData.append([filePath, firstFrame, lastFrame])

        return sourceData

    @err_catcher(name=__name__)
    def compGetImportPasses(self):
        sourceFolder = os.path.dirname(
            os.path.dirname(self.seq[0])
        ).replace("\\", "/")
        passes = [
            x
            for x in os.listdir(sourceFolder)
            if x[-5:] not in ["(mp4)", "(jpg)", "(png)"]
            and os.path.isdir(os.path.join(sourceFolder, x))
        ]
        sourceData = []

        for curPass in passes:
            curPassPath = os.path.join(sourceFolder, curPass)

            imgs = os.listdir(curPassPath)
            if len(imgs) == 0:
                continue

            if (
                len(imgs) > 1
                and self.pstart
                and self.pend
                and self.pstart != "?"
                and self.pend != "?"
            ):
                firstFrame = self.pstart
                lastFrame = self.pend

                curPassName = imgs[0].split(".")[0]
                increment = "####"
                curPassFormat = imgs[0].split(".")[-1]

                filePath = os.path.join(
                    sourceFolder,
                    curPass,
                    ".".join([curPassName, increment, curPassFormat]),
                ).replace("\\", "/")
            else:
                filePath = os.path.join(curPassPath, imgs[0]).replace("\\", "/")
                firstFrame = None
                lastFrame = None

            sourceData.append([filePath, firstFrame, lastFrame])

        return sourceData

    @err_catcher(name=__name__)
    def triggerAutoplay(self, checked=False):
        self.core.setConfig("browser", "autoplaypreview", checked)

        if self.timeline:
            if checked and self.timeline.state() == QTimeLine.Paused:
                self.setTimelinePaused(False)
            elif not checked and self.timeline.state() == QTimeLine.Running:
                self.setTimelinePaused(True)
        else:
            self.tlPaused = not checked


class VersionDelegate(QStyledItemDelegate):
    def __init__(self, origin):
        super(VersionDelegate, self).__init__()
        self.origin = origin
        self.widget = self.origin.lw_version

    def paint(self, painterQPainter, optionQStyleOptionViewItem, indexQModelIndex):
        item = self.widget.itemFromIndex(indexQModelIndex)
        QStyledItemDelegate.paint(
            self, painterQPainter, optionQStyleOptionViewItem, indexQModelIndex
        )

        data = item.data(Qt.UserRole)
        offset = 0
        if len(self.origin.projectBrowser.locations) > 1:
            for location in reversed(self.origin.projectBrowser.locations):
                if location.get("name") not in data.get("locations", []):
                    continue

                if "icon" not in location:
                    location["icon"] = self.origin.projectBrowser.getLocationIcon(location["name"])

                if location["icon"]:
                    rect = QRect(optionQStyleOptionViewItem.rect)
                    curRight = rect.right() - offset
                    rect.setTop(rect.top() + 2)
                    rect.setBottom(rect.bottom() - 2)
                    rect.setLeft(curRight - 30)
                    rect.setRight(curRight - 0)
                    painterQPainter.setRenderHint(QPainter.Antialiasing)
                    location["icon"].paint(painterQPainter, rect)
                    offset += 25
