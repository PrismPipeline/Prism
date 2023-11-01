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
import logging
from collections import OrderedDict

prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

if __name__ == "__main__":
    sys.path.append(os.path.join(prismRoot, "Scripts"))
    import PrismCore

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

import EditShot
from PrismUtils import PrismWidgets, ProjectWidgets
from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class EntityWidget(QWidget):
    tabChanged = Signal()

    def __init__(self, core, refresh=True, mode="scenefiles"):
        QWidget.__init__(self)
        self.core = core
        self.core.parentWindow(self)
        self.pages = []
        self.refresh = refresh
        self.mode = mode
        self.prevTab = None
        self.editEntitiesOnDclick = True
        self.core.entities.refreshOmittedEntities()
        self.setupUi()
        self.connectEvents()
        self.core.callback(name="onEntityWidgetCreated", args=[self])

    @err_catcher(name=__name__)
    def setupUi(self):
        pageNames = ["Assets", "Shots"]

        self.sw_tabs = QStackedWidget()
        self.w_header = QWidget()
        self.tb_entities = QTabBar()
        self.lo_headerV = QVBoxLayout()
        self.lo_header = QHBoxLayout()
        self.w_header.setLayout(self.lo_headerV)

        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        self.w_header.setSizePolicy(sizePolicy)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(100)
        self.sw_tabs.setSizePolicy(sizePolicy)
        self.lo_headerV.addStretch()
        self.lo_headerV.addLayout(self.lo_header)
        self.lo_header.addStretch()
        self.lo_header.addWidget(self.tb_entities)
        self.lo_header.addStretch()
        self.lo_header.setContentsMargins(0, 0, 0, 0)
        self.lo_headerV.setContentsMargins(0, 0, 0, 0)

        self.b_search = QToolButton()
        self.b_search.setCheckable(True)
        self.b_search.setAutoRaise(True)
        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "search.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_search.setIcon(icon)
        if self.core.appPlugin.pluginName != "Standalone":
            ssheet = """
                QWidget{padding: 0; border-width: 0px; border-radius: 4px; background-color: transparent}
                QWidget:hover{border-width: 0px; background-color: rgba(150, 210, 240, 50) }
                QWidget:checked{border-width: 0px; background-color: rgba(150, 210, 240, 100) }
            """
            self.b_search.setStyleSheet(ssheet)

        self.w_search = QWidget()
        self.lo_search = QHBoxLayout()
        self.w_search.setLayout(self.lo_search)
        self.lo_search.addStretch()
        self.lo_search.addWidget(self.b_search)
        self.b_search.setParent(self.w_header)
        self.b_search.setGeometry(100, 0, 25, 25)
        self.b_search.move(
            self.w_header.geometry().width() - self.b_search.geometry().width(), 0
        )

        for pageName in pageNames:
            page = EntityPage(self, pageName, refresh=self.refresh)
            self.tb_entities.addTab(page.objectName())
            self.sw_tabs.addWidget(page)
            self.pages.append(page)

        self.prevTab = self.getCurrentPage()
        self.lo_main = QVBoxLayout()
        self.lo_main.setContentsMargins(0, 0, 0, 0)
        self.lo_main.setSpacing(0)
        self.lo_main.addWidget(self.w_header)
        self.lo_main.addWidget(self.sw_tabs)
        self.setLayout(self.lo_main)

    @err_catcher(name=__name__)
    def resizeEvent(self, event):
        self.b_search.move(
            self.w_header.geometry().width() - self.b_search.geometry().width(), 0
        )

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.tb_entities.currentChanged.connect(self.ontabChanged)
        self.b_search.toggled.connect(self.searchClicked)

    @err_catcher(name=__name__)
    def refreshEntities(self, pages=None, restoreSelection=False, defaultSelection=True):
        for page in self.pages:
            if pages and page.objectName() not in pages:
                continue

            page.refreshEntities(restoreSelection=restoreSelection, defaultSelection=defaultSelection)

    @err_catcher(name=__name__)
    def getPage(self, pageName):
        for page in self.pages:
            if page.objectName() == pageName:
                return page

    @err_catcher(name=__name__)
    def getCurrentPage(self):
        return self.sw_tabs.currentWidget()

    @err_catcher(name=__name__)
    def getCurrentPageName(self):
        return self.sw_tabs.currentWidget().objectName()

    @err_catcher(name=__name__)
    def searchClicked(self, state):
        self.sw_tabs.currentWidget().searchClicked(state)

    @err_catcher(name=__name__)
    def ontabChanged(self, state):
        self.sw_tabs.setCurrentIndex(state)
        state = self.b_search.isChecked()
        widget = self.sw_tabs.currentWidget()
        if widget.e_search.isVisible() != state:
            widget.searchClicked(state)

        if self.prevTab:
            location = self.prevTab.getCurrentLocation()
            idx = self.getCurrentPage().cb_location.findText(location)
            if idx != -1:
                self.getCurrentPage().cb_location.setCurrentIndex(idx)

        self.tabChanged.emit()
        self.prevTab = self.getCurrentPage()

    @err_catcher(name=__name__)
    def getCurrentData(self, returnOne=True):
        return self.getCurrentPage().getCurrentData(returnOne=returnOne)

    @err_catcher(name=__name__)
    def getLocations(self):
        return self.getCurrentPage().getLocations()

    @err_catcher(name=__name__)
    def navigate(self, data, clear=False):
        if not data:
            if clear:
                self.getCurrentPage().tw_tree.selectionModel().clearSelection()

            return

        if isinstance(data, list):
            fdata = data[0]
        else:
            fdata = data

        if fdata.get("type") in ["asset", "assetFolder"]:
            page = self.getPage("Assets")
        elif fdata.get("type") in ["shot", "sequence"]:
            page = self.getPage("Shots")
        else:
            if clear:
                self.getCurrentPage().tw_tree.selectionModel().clearSelection()

            return False

        self.sw_tabs.setCurrentWidget(page)
        self.tb_entities.setCurrentIndex(self.sw_tabs.currentIndex())
        page.navigate(data)

    @err_catcher(name=__name__)
    def syncFromWidget(self, widget):
        data = widget.getCurrentData()
        if data:
            self.navigate(data)
        else:
            self.tb_entities.setCurrentIndex(widget.tb_entities.currentIndex())

        self.b_search.setChecked(widget.b_search.isChecked())
        location = widget.getCurrentPage().getCurrentLocation()
        idx = self.getCurrentPage().cb_location.findText(location)
        if idx != -1:
            self.getCurrentPage().cb_location.setCurrentIndex(idx)

    @err_catcher(name=__name__)
    def getCurrentLocation(self):
        return self.getCurrentPage().getCurrentLocation()


class EntityPage(QWidget):
    itemChanged = Signal(object)
    entityCreated = Signal(object)

    shotSaved = Signal()
    nextClicked = Signal()

    def __init__(self, widget, pageName, refresh=True):
        QWidget.__init__(self)
        self.entityWidget = widget
        self.core = widget.core
        self.pageName = pageName
        self.expandedItems = []
        self.dclick = None
        self.entityPreviewWidth = 107
        self.entityPreviewHeight = 60
        self.itemWidgets = []
        self.setObjectName(self.pageName)
        if pageName == "Assets":
            self.entityType = "asset"
        elif pageName == "Shots":
            self.entityType = "shot"

        self.setupUi()
        self.connectEvents()

        if refresh:
            self.refreshEntities()

    @err_catcher(name=__name__)
    def refreshEntities(self, restoreSelection=False, defaultSelection=True):
        prevData = self.getCurrentData()
        self.itemWidgets = []

        self.tw_tree.blockSignals(True)
        if self.entityType == "asset":
            self.refreshAssetHierarchy(defaultSelection=defaultSelection)
        elif self.entityType == "shot":
            self.refreshShots(defaultSelection=defaultSelection)

        if restoreSelection:
            self.navigate(prevData)

        self.tw_tree.blockSignals(False)
        if self.getCurrentData() != prevData:
            self.onItemChanged()

    @err_catcher(name=__name__)
    def setupUi(self):
        self.e_search = QLineEdit()
        self.e_search.setPlaceholderText("Search...")

        self.w_location = QWidget()
        self.lo_location = QHBoxLayout()
        self.lo_location.setContentsMargins(0, 0, 0, 0)
        self.w_location.setLayout(self.lo_location)
        self.l_location = QLabel("Location:")
        self.cb_location = QComboBox()
        self.lo_location.addWidget(self.l_location)
        self.lo_location.addWidget(self.cb_location)

        if self.entityWidget.mode in ["scenefiles", "products"]:
            self.locations = self.core.paths.getExportProductBasePaths()
        else:
            self.locations = self.core.paths.getRenderProductBasePaths()

        if len(self.locations) > 1:
            newExportPaths = OrderedDict([("all", "all")])
            newExportPaths.update(self.locations)
            self.locations = newExportPaths
        else:
            self.w_location.setVisible(False)

        self.cb_location.addItems(list(self.locations.keys()))

        self.tw_tree = QTreeWidget()
        self.tw_tree.header().setVisible(False)
        self.tw_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tw_tree.setIndentation(10)
        self.tw_tree.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tw_tree.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.lo_main = QVBoxLayout()
        self.lo_main.setContentsMargins(0, 0, 0, 0)
        self.lo_main.addWidget(self.e_search)
        self.lo_main.addWidget(self.w_location)
        self.lo_main.addWidget(self.tw_tree)
        self.setLayout(self.lo_main)

        self.tw_tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.e_search.setClearButtonEnabled(True)

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.tw_tree.mousePrEvent = self.tw_tree.mousePressEvent
        self.tw_tree.mousePressEvent = self.mouseClickEvent
        self.tw_tree.mouseClickEvent = self.tw_tree.mouseReleaseEvent
        self.tw_tree.mouseReleaseEvent = self.mouseClickEvent
        self.tw_tree.mouseDClick = self.tw_tree.mouseDoubleClickEvent
        self.tw_tree.mouseDoubleClickEvent = self.mousedb
        self.tw_tree.enterEvent = lambda x: self.mouseEnter()
        self.tw_tree.origKeyPressEvent = self.tw_tree.keyPressEvent
        self.tw_tree.keyPressEvent = lambda x: self.keyPressed(x, "tree")
        self.e_search.origKeyPressEvent = self.e_search.keyPressEvent
        self.e_search.keyPressEvent = lambda x: self.keyPressed(x, "search")

        self.tw_tree.itemSelectionChanged.connect(self.onItemChanged)
        self.tw_tree.itemExpanded.connect(self.itemExpanded)
        self.tw_tree.itemCollapsed.connect(self.itemCollapsed)
        self.tw_tree.customContextMenuRequested.connect(self.contextMenuTree)
        self.e_search.textChanged.connect(lambda x: self.refreshEntities(restoreSelection=True))
        self.cb_location.activated.connect(self.onLocationChanged)

    @err_catcher(name=__name__)
    def getLocations(self, includeAll=False):
        locs = self.locations.copy()
        if not includeAll:
            if "all" in locs:
                del locs["all"]

        return locs

    @err_catcher(name=__name__)
    def getCurrentLocation(self):
        if not self.cb_location.isHidden():
            locations = self.cb_location.currentText()
        else:
            locations = "all"

        return locations

    @err_catcher(name=__name__)
    def onLocationChanged(self, idx):
        self.refreshEntities(restoreSelection=True)

    @err_catcher(name=__name__)
    def refreshAssetHierarchy(self, defaultSelection=True):
        wasBlocked = self.tw_tree.signalsBlocked()
        if not wasBlocked:
            self.tw_tree.blockSignals(True)

        self.tw_tree.clear()
        self.addedAssetItems = {}
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "asset.png"
        )
        self.assetIcon = self.core.media.getColoredIcon(iconPath)

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "folder.png"
        )
        self.folderIcon = self.core.media.getColoredIcon(iconPath)

        self.filteredAssets = []
        if self.e_search.isVisible() and self.e_search.text():
            assets, folders = self.core.entities.getAssetPaths(
                returnFolders=True, depth=0
            )
            filterStr = self.e_search.text()
            self.filteredAssets += self.core.entities.filterAssets(assets, filterStr)
            assetFolders = []
            for fasset in self.filteredAssets:
                fasset = os.path.dirname(fasset)
                while fasset != self.core.assetPath:
                    assetFolders.append(fasset)
                    fasset = os.path.dirname(fasset)

            self.filteredAssets += assetFolders
            self.filteredAssets += self.core.entities.filterAssets(folders, filterStr)

        self.hasAssetPreview = False
        self.refreshAssets()
        self.tw_tree.resizeColumnToContents(0)

        if defaultSelection and self.tw_tree.topLevelItemCount() > 0 and not self.e_search.isVisible():
            self.tw_tree.setCurrentItem(self.tw_tree.topLevelItem(0))

        if not wasBlocked:
            self.tw_tree.blockSignals(False)
            self.itemChanged.emit(self.tw_tree.currentItem())

    @err_catcher(name=__name__)
    def refreshAssets(self, path=None, parent=None, refreshChildren=True):
        if not path:
            if parent:
                path = parent.data(0, Qt.UserRole)["paths"][0]
            else:
                path = self.core.assetPath

        location = self.getCurrentLocation()
        if location == "all":
            locations = list(self.getLocations().keys())
        else:
            locations = [location]

        assets = {}
        folders = {}
        for location in locations:
            basePath = self.getLocations()[location]
            path = self.core.convertPath(path, location)
            assetPaths, folderPaths = self.core.entities.getAssetPaths(
                path=path, returnFolders=True, depth=1
            )
            for assetPath in assetPaths:
                if self.core.entities.isAssetPathOmitted(assetPath):
                    continue

                if basePath not in assets:
                    assets[basePath] = []

                assets[basePath].append(assetPath)

            for folderPath in folderPaths:
                if self.core.entities.isAssetPathOmitted(folderPath):
                    continue

                if basePath not in folders:
                    folders[basePath] = []

                folders[basePath].append(folderPath)

        if self.e_search.isVisible() and self.e_search.text():
            filteredAssets = {}
            for location in assets:
                filteredAssets[location] = [a for a in assets[location] if a in self.filteredAssets]

            assets = filteredAssets

            filteredFolders = {}
            for location in folders:
                filteredFolders[location] = [f for f in folders[location] if f in self.filteredAssets]

            folders = filteredFolders

        itemPaths = []

        for location in assets:
            for path in assets[location]:
                data = {"path": path, "type": "asset"}
                itemPaths.append(data)

        for location in folders:
            for path in folders[location]:
                data = {"path": path, "type": "assetFolder"}
                itemPaths.append(data)

        for itemPath in sorted(
            itemPaths,
            key=lambda x: self.core.entities.getAssetRelPathFromPath(x["path"]).lower(),
        ):
            self.addAssetItem(
                itemPath["path"],
                itemType=itemPath["type"],
                parent=parent,
                refreshItem=refreshChildren,
            )

    @err_catcher(name=__name__)
    def addAssetItem(self, path, itemType, parent=None, refreshItem=True):
        name = os.path.basename(path)
        relPath = self.core.entities.getAssetRelPathFromPath(path)
        if relPath in self.addedAssetItems:
            item = self.addedAssetItems[relPath]
            data = item.data(0, Qt.UserRole)
            data["paths"].append(path)
            item.setData(0, Qt.UserRole, data)
            refreshItem = False
        else:
            item = QTreeWidgetItem([name, name])
            entity = {"asset_path": relPath, "asset": os.path.basename(relPath), "paths": [path], "type": itemType}
            item.setData(
                0,
                Qt.UserRole,
                entity,
            )
            self.addedAssetItems[relPath] = item

        if parent:
            parent.addChild(item)
        else:
            self.tw_tree.addTopLevelItem(item)

        if refreshItem:
            self.refreshAssetItem(item)

    @err_catcher(name=__name__)
    def refreshAssetItem(self, item):
        item.takeChildren()
        data = item.data(0, Qt.UserRole)
        path = data["paths"][0]
        itemType = data["type"]
        expand = path in self.expandedItems or (
            self.e_search.isVisible() and self.e_search.text()
        )
        showIcon = True
        if itemType == "asset":
            usePreview = self.core.getConfig("browser", "showEntityPreviews", config="user", dft=True)
            if usePreview:
                pm = self.core.entities.getEntityPreview(data)
                if not pm:
                    pm = self.core.media.emptyPrvPixmap

                w_entity = QWidget()
                w_entity.setStyleSheet("background-color: transparent;")
                lo_entity = QHBoxLayout()
                lo_entity.setContentsMargins(0, 0, 0, 0)
                w_entity.setLayout(lo_entity)
                l_preview = QLabel()
                l_label = QLabel(os.path.basename(path))
                lo_entity.addWidget(l_preview)
                lo_entity.addWidget(l_label)
                lo_entity.addStretch()
                if pm:
                    pmap = self.core.media.scalePixmap(pm, self.entityPreviewWidth, self.entityPreviewHeight, fitIntoBounds=False, crop=True)
                    l_preview.setPixmap(pmap)
        
                self.tw_tree.setItemWidget(item, 0, w_entity)
                self.itemWidgets.append(w_entity)
                showIcon = False
                self.hasAssetPreview = True
                item.setText(0, "")

        if itemType == "asset":
            if showIcon:
                item.setIcon(0, self.assetIcon)
        else:
            if showIcon:
                item.setIcon(0, self.folderIcon)

            refreshChildren = expand  # and self.tw_tree.signalsBlocked()
            self.refreshAssets(path=path, parent=item, refreshChildren=refreshChildren)

        if expand:
            item.setExpanded(True)

    @err_catcher(name=__name__)
    def itemExpanded(self, item):
        if self.entityType == "asset":
            name = item.data(0, Qt.UserRole)["paths"][0]
        elif self.entityType == "shot":
            name = self.core.entities.getShotName(item.data(0, Qt.UserRole))

        self.dclick = False
        if name not in self.expandedItems and not (
            self.e_search.isVisible() and self.e_search.text()
        ):
            self.expandedItems.append(name)

        mods = QApplication.keyboardModifiers()
        if mods == Qt.ControlModifier:
            self.setItemChildrenExpanded(item)

        if self.entityType == "asset":
            for childnum in range(item.childCount()):
                self.refreshAssetItem(item.child(childnum))

    @err_catcher(name=__name__)
    def itemCollapsed(self, item):
        if self.entityType == "asset":
            name = item.data(0, Qt.UserRole)["paths"][0]
        elif self.entityType == "shot":
            name = self.core.entities.getShotName(item.data(0, Qt.UserRole))

        self.dclick = False
        if name in self.expandedItems:
            self.expandedItems.remove(name)

        mods = QApplication.keyboardModifiers()
        if mods == Qt.ControlModifier:
            self.setItemChildrenExpanded(item, expanded=False)

    @err_catcher(name=__name__)
    def refreshShots(self, defaultSelection=True):
        wasBlocked = self.tw_tree.signalsBlocked()
        if not wasBlocked:
            self.tw_tree.blockSignals(True)

        self.tw_tree.clear()

        location = self.getCurrentLocation()
        if location == "all":
            locations = list(self.getLocations().keys())
        else:
            locations = [location]

        searchFilter = ""
        if self.e_search.isVisible():
            searchFilter = self.e_search.text()

        sequences, shotData = self.core.entities.getShots(
            locations=locations, searchFilter=searchFilter
        )

        shots = {}
        for shot in shotData:
            seqName = shot["sequence"]
            shotName = shot["shot"]
            shotPaths = shot["paths"]

            if seqName not in shots:
                shots[seqName] = {}

            if shotName not in shots[seqName]:
                shots[seqName][shotName] = []

            for shotPath in shotPaths:
                if shotPath not in shots[seqName][shotName]:
                    shots[seqName][shotName].append(shotPath)

        sequences = self.core.sortNatural(shots.keys())
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "sequence.png"
        )
        seqIcon = self.core.media.getColoredIcon(iconPath)

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "shot.png"
        )
        shotIcon = self.core.media.getColoredIcon(iconPath)
        usePreview = self.core.getConfig("browser", "showEntityPreviews", config="user", dft=True)
        for seqName in sequences:
            seqItem = QTreeWidgetItem([seqName])
            seqItem.setData(0, Qt.UserRole, {"type": "shot", "sequence": seqName, "shot": "_sequence"})
            seqItem.setIcon(0, seqIcon)
            self.tw_tree.addTopLevelItem(seqItem)
            if seqName in self.expandedItems or (
                self.e_search.isVisible() and self.e_search.text()
            ):
                seqItem.setExpanded(True)

            for shot in self.core.sortNatural(shots[seqName]):
                data = [shot]
                sItem = QTreeWidgetItem(data)
                entity = {
                    "type": "shot",
                    "sequence": seqName,
                    "shot": shot,
                    "paths": shots[seqName][shot],
                }
                sItem.setData(
                    0,
                    Qt.UserRole,
                    entity,
                )
                seqItem.addChild(sItem)
                showIcon = True
                if usePreview:
                    pm = self.core.entities.getEntityPreview(entity)
                    if not pm:
                        pm = self.core.media.emptyPrvPixmap

                    w_entity = QWidget()
                    w_entity.setStyleSheet("background-color: transparent;")
                    lo_entity = QHBoxLayout()
                    lo_entity.setContentsMargins(0, 0, 0, 0)
                    w_entity.setLayout(lo_entity)
                    l_preview = QLabel()
                    l_label = QLabel(shot)
                    lo_entity.addWidget(l_preview)
                    lo_entity.addWidget(l_label)
                    lo_entity.addStretch()
                    if pm:
                        pmap = self.core.media.scalePixmap(pm, self.entityPreviewWidth, self.entityPreviewHeight, fitIntoBounds=False, crop=True)
                        l_preview.setPixmap(pmap)
        
                    self.tw_tree.setItemWidget(sItem, 0, w_entity)
                    self.itemWidgets.append(w_entity)
                    showIcon = False
                    sItem.setText(0, "")

                if showIcon:
                    sItem.setIcon(0, shotIcon)

        self.tw_tree.resizeColumnToContents(0)
        if defaultSelection and self.tw_tree.topLevelItemCount() > 0:
            if self.tw_tree.topLevelItem(0).isExpanded():
                self.tw_tree.setCurrentItem(self.tw_tree.topLevelItem(0).child(0))
            else:
                self.tw_tree.setCurrentItem(self.tw_tree.topLevelItem(0))

        if not wasBlocked:
            self.tw_tree.blockSignals(False)
            self.itemChanged.emit(self.tw_tree.currentItem())

    @err_catcher(name=__name__)
    def omitEntity(self, entity):
        if entity["type"] in ["asset", "assetFolder"]:
            name = entity["asset_path"]
        elif entity["type"] == "shot":
            name = self.core.entities.getShotName(entity)

        msgText = (
            'Are you sure you want to omit %s "%s"?\n\nThis will hide the %s in Prism, but all scenefiles and renders remain on disk.'
            % (entity["type"].lower(), name, entity["type"].lower())
        )
        result = self.core.popupQuestion(msgText)
        if result == "Yes":
            self.core.entities.omitEntity(entity)
            self.refreshEntities(restoreSelection=True)

    @err_catcher(name=__name__)
    def setWidgetItemsExpanded(self, expanded=True):
        for idx in range(self.tw_tree.topLevelItemCount()):
            item = self.tw_tree.topLevelItem(idx)
            item.setExpanded(expanded)
            self.setItemChildrenExpanded(item, expanded=expanded, recursive=True)

    @err_catcher(name=__name__)
    def setItemChildrenExpanded(self, item, expanded=True, recursive=False):
        for childIdx in range(item.childCount()):
            if recursive:
                self.setItemChildrenExpanded(
                    item.child(childIdx), expanded=expanded, recursive=True
                )
            item.child(childIdx).setExpanded(expanded)

    @err_catcher(name=__name__)
    def onItemChanged(self):
        items = self.tw_tree.selectedItems()
        if self.tw_tree.selectionMode() == QAbstractItemView.SingleSelection:
            if items:
                items = items[0]
            else:
                items = None

        self.itemChanged.emit(items)

    @err_catcher(name=__name__)
    def showPreviewToggled(self, state):
        self.core.setConfig("browser", "showEntityPreviews", state, config="user")
        self.entityWidget.refreshEntities(restoreSelection=True)

    @err_catcher(name=__name__)
    def searchClicked(self, state):
        if not hasattr(self.entityWidget, "b_search") or not self.entityWidget.b_search.isHidden():
            self.e_search.setVisible(state)
            if len(self.locations) > 1:
                self.w_location.setVisible(state)

        if state:
            self.e_search.setFocus()
        else:
            self.e_search.setText("")
            self.cb_location.setCurrentIndex(0)
            self.e_search.textChanged.emit("")

    @err_catcher(name=__name__)
    def setSearchVisible(self, state):
        if hasattr(self.entityWidget, "b_search"):
            self.entityWidget.b_search.setChecked(state)

        self.e_search.setVisible(state)
        if len(self.locations) > 1:
            self.w_location.setVisible(state)

    @err_catcher(name=__name__)
    def setShowSearchAlways(self, state):
        self.b_shotSearch.setHidden(state)

    @err_catcher(name=__name__)
    def isSearchVisible(self):
        if hasattr(self.entityWidget, "b_search"):
            return self.entityWidget.b_search.isChecked()
        else:
            return self.e_search.isVisible()

    @err_catcher(name=__name__)
    def keyPressed(self, event, widgetType):
        if widgetType == "tree":
            if event.key() == Qt.Key_Escape:
                if hasattr(self.entityWidget, "b_search"):
                    self.entityWidget.b_search.setChecked(False)
                else:
                    self.searchClicked(False)

            elif event.text():
                if hasattr(self.entityWidget, "b_search"):
                    self.entityWidget.b_search.setChecked(True)
                else:
                    self.searchClicked(True)

                self.e_search.keyPressEvent(event)
            else:
                self.tw_tree.origKeyPressEvent(event)
        elif widgetType == "search":
            if event.key() == Qt.Key_Escape:
                if hasattr(self.entityWidget, "b_search"):
                    self.entityWidget.b_search.setChecked(False)
                else:
                    self.searchClicked(False)

            else:
                if hasattr(self.entityWidget, "b_search"):
                    self.entityWidget.b_search.setChecked(True)
                else:
                    self.searchClicked(True)

                self.e_search.origKeyPressEvent(event)

        event.accept()

    @err_catcher(name=__name__)
    def getExpandedItems(self):
        expandedAssets = []
        for idx in range(self.tw_tree.topLevelItemCount()):
            item = self.tw_tree.topLevelItem(idx)
            expandedAssets += self.getExpandedChildren(item)

        return expandedAssets

    @err_catcher(name=__name__)
    def getExpandedChildren(self, item):
        expandedAssets = []
        if item.isExpanded():
            if self.entityType == "asset":
                name = item.data(0, Qt.UserRole)["paths"][0]
            elif self.entityType == "shot":
                name = self.core.entities.getShotName(item.data(0, Qt.UserRole))

            expandedAssets.append(name)

        for idx in range(item.childCount()):
            expandedAssets += self.getExpandedChildren(item.child(idx))

        return expandedAssets

    @err_catcher(name=__name__)
    def mouseEnter(self):
        self.tw_tree.setFocus()

    @err_catcher(name=__name__)
    def mousedb(self, event):
        mIndex = self.tw_tree.indexAt(event.pos())
        cItem = self.tw_tree.itemFromIndex(mIndex)

        if self.dclick and self.entityWidget.editEntitiesOnDclick:
            if self.entityType == "asset":
                if not cItem:
                    self.createAssetDlg("asset")
            elif self.entityType == "shot":
                if not mIndex.data():
                    self.editShotDlg()

        if self.dclick:
            self.tw_tree.mouseDClick(event)

        if not self.dclick:
            pos = self.tw_tree.mapFromGlobal(QCursor.pos())
            item = self.tw_tree.itemAt(pos.x(), pos.y())
            if item is not None:
                item.setExpanded(not item.isExpanded())

    @err_catcher(name=__name__)
    def mouseClickEvent(self, event):
        if QEvent:
            if event.type() == QEvent.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    index = self.tw_tree.indexAt(event.pos())
                    if index.data() is None:
                        self.tw_tree.setCurrentIndex(
                            self.tw_tree.model().createIndex(-1, 0)
                        )

                    self.tw_tree.mouseClickEvent(event)
            elif event.type() == QEvent.MouseButtonPress:
                self.dclick = True
                item = self.tw_tree.itemAt(event.pos())
                wasExpanded = item.isExpanded() if item else None
                self.tw_tree.mousePrEvent(event)

                if event.button() == Qt.LeftButton:
                    if item and item.childCount() and wasExpanded == item.isExpanded():
                        item.setExpanded(not item.isExpanded())

    @err_catcher(name=__name__)
    def createAssetDlg(self, entityType, startText=None):
        if startText is None:
            curItem = self.tw_tree.currentItem()
            if curItem:
                data = curItem.data(0, Qt.UserRole)
                if data.get("type") == "assetFolder":
                    folderPath = data.get("asset_path", "")
                else:
                    folderPath = os.path.dirname(data.get("asset_path", ""))

                startText = folderPath.replace("\\", "/") + "/"

        startText = startText or ""
        if hasattr(self, "newItem") and self.core.isObjectValid(self.newItem):
            self.newItem.close()

        if entityType == "asset":
            self.newItem = ProjectWidgets.CreateAssetDlg(self.core, parent=self, startText=startText)
            self.newItem.accepted.connect(lambda: self.onCreateAssetDlgAccepted(entityType))
        else:
            self.newItem = ProjectWidgets.CreateAssetFolderDlg(self.core, parent=self, startText=startText)
            self.newItem.accepted.connect(lambda: self.onCreateAssetDlgAccepted(entityType))

        self.core.callback(name="onAssetDlgOpen", args=[self, self.newItem])
        if not getattr(self.newItem, "allowShow", True):
            return

        self.newItem.show()
        self.newItem.e_item.deselect()

    @err_catcher(name=__name__)
    def onCreateAssetDlgAccepted(self, entityType):
        self.createAsset(entityType)
        mods = QApplication.keyboardModifiers()
        if mods == Qt.ControlModifier and (not self.newItem.clickedButton or self.newItem.clickedButton.text() != self.newItem.btext):
            self.createAssetDlg(entityType, startText=self.newItem.e_item.text())

    @err_catcher(name=__name__)
    def createAsset(self, entityType):
        self.activateWindow()
        assetNames = self.newItem.e_item.text().replace(os.pathsep, ",").split(",")
        entityNames = [path.strip() for path in assetNames]
        for entityName in entityNames:
            path = self.core.assetPath
            data = {
                "type": "assetFolder" if entityType == "folder" else entityType,
                "asset_path": entityName,
                "asset": os.path.basename(entityName)
            }
            result = self.core.entities.createEntity(data, dialog=self.newItem)
            assetPath = os.path.join(path, entityName)
            if entityType == "asset":
                descr = self.newItem.getDescription()
                if descr:
                    self.core.entities.setAssetDescription(os.path.basename(entityName), descr)

                thumb = self.newItem.getThumbnail()
                if thumb:
                    self.core.entities.setEntityPreview(data, thumb)

                self.newItem.w_meta.save(data)

            self.refreshEntities()
            self.navigate(data=data)
            if not result or not result.get("entity", "") or result.get("existed", ""):
                return

            if self.newItem.clickedButton and self.newItem.clickedButton.text() == self.newItem.btext:
                data["action"] = "next"
                if entityType == "folder":
                    mods = QApplication.keyboardModifiers()
                    if mods == Qt.ControlModifier:
                        self.createAssetDlg("asset")
                    else:
                        self.createAssetDlg("folder")

            if "paths" not in data:
                data["paths"] = []

            data["paths"].append(assetPath)
            self.entityCreated.emit(data)

    @err_catcher(name=__name__)
    def shotCreated(self, shotData):
        self.refreshShots()

        seqName = shotData["sequence"]
        shotName = shotData["shot"]

        self.navigate({"type": "shot", "sequence": seqName, "shot": shotName})
        self.entityCreated.emit(shotData)

    @err_catcher(name=__name__)
    def editShotDlg(self, shotData=None):
        sequs = []
        for seqName in self.getTopLevelItemNames():
            sequs.append(seqName)

        if not shotData:
            sData = self.getCurrentData()
            if isinstance(sData, list) and len(sData) == 1:
                sData = sData[0]

            if not isinstance(sData, dict):
                return

            if sData:
                shotData = {"sequence": sData["sequence"]}

        if hasattr(self, "es") and self.core.isObjectValid(self.es):
            self.es.close()

        self.es = EditShot.EditShot(core=self.core, shotData=shotData, sequences=sequs, parent=self)
        self.es.shotCreated.connect(self.shotCreated)
        self.es.shotSaved.connect(self.shotSaved.emit)
        self.es.nextClicked.connect(self.nextClicked.emit)
        if not getattr(self.es, "allowShow", True):
            return

        self.es.show()

    @err_catcher(name=__name__)
    def getItems(self, parent=None, items=None):
        if items is None:
            items = []

        if parent:
            for idx in range(parent.childCount()):
                item = parent.child(idx)
                items.append(item)
                self.getItems(parent=item, items=items)
        else:
            for idx in range(self.tw_tree.topLevelItemCount()):
                item = self.tw_tree.topLevelItem(idx)
                items.append(item)
                self.getItems(parent=item, items=items)

        return items

    @err_catcher(name=__name__)
    def selectItemType(self, itemType):
        self.tw_tree.selectionModel().clearSelection()
        items = self.getItems()
        for item in items:
            data = item.data(0, Qt.UserRole)
            if data.get("type") == itemType:
                item.setSelected(True)

    @err_catcher(name=__name__)
    def getCurrentData(self, returnOne=True):
        items = self.tw_tree.selectedItems()
        curData = []

        for item in items:
            data = self.getDataFromItem(item)
            curData.append(data)
        
        if returnOne:
            if curData:
                curData = curData[0]
            else:
                curData = {}

        return curData

    @err_catcher(name=__name__)
    def getDataFromItem(self, item):
        data = {}
        data = item.data(0, Qt.UserRole)
        if "type" not in data:
            data["type"] = self.entityType

        if data["type"] == "shot" and not data.get("shot"):
            data["type"] = "sequence"

        return data

    @err_catcher(name=__name__)
    def getTopLevelItemNames(self):
        names = []
        for i in range(self.tw_tree.topLevelItemCount()):
            name = self.tw_tree.topLevelItem(i).text(0)
            names.append(name)

        return names

    @err_catcher(name=__name__)
    def navigate(self, data):
        prevData = self.getCurrentData()
        wasBlocked = self.tw_tree.signalsBlocked()
        if not wasBlocked:
            self.tw_tree.blockSignals(True)

        self.tw_tree.selectionModel().clearSelection()
        if self.entityType == "asset":
            if not isinstance(data, list):
                data = [data]

            hItem = None
            for asset in data:
                itemPath = asset.get("asset_path", "")
                hierarchy = itemPath.replace("\\", "/").split("/")
                hierarchy = [x for x in hierarchy if x != ""]
                if not hierarchy:
                    continue

                hItem = self.tw_tree.invisibleRootItem()
                for idx, i in enumerate((hierarchy)):
                    for k in range(hItem.childCount() - 1, -1, -1):
                        itemName = os.path.basename(hItem.child(k).data(0, Qt.UserRole)["asset_path"])
                        if itemName == i:
                            hItem = hItem.child(k)
                            if len(hierarchy) > (idx + 1):
                                hItem.setExpanded(True)
                                self.itemExpanded(hItem)
                                if (
                                    hItem.data(0, Qt.UserRole)["asset_path"]
                                    not in self.expandedItems
                                ):
                                    self.expandedItems.append(
                                        hItem.data(0, Qt.UserRole)["asset_path"]
                                    )
                            break
                    else:
                        break            

                if hItem and not self.tw_tree.selectedItems():
                    self.tw_tree.setCurrentItem(hItem)

                hItem.setSelected(True)

            if hItem:
                self.tw_tree.scrollTo(self.tw_tree.indexFromItem(hItem))

        elif self.entityType == "shot":
            if not isinstance(data, list):
                data = [data]

            sItem = None
            for shot in data:
                for idx in range(self.tw_tree.topLevelItemCount()):
                    csItem = self.tw_tree.topLevelItem(idx)
                    if csItem.data(0, Qt.UserRole).get("sequence") == shot.get("sequence"):
                        if not shot.get("shot"):
                            csItem.setSelected(True)
                            sItem = csItem
                        else:
                            csItem.setExpanded(True)
                            for childIdx in range(csItem.childCount()):
                                shotItem = csItem.child(childIdx)
                                if shotItem.data(0, Qt.UserRole).get("shot") == shot["shot"]:
                                    shotItem.setSelected(True)
                                    break
                            else:
                                csItem.setSelected(True)
                                sItem = csItem

            if sItem:
                self.tw_tree.setCurrentItem(sItem)
                self.tw_tree.scrollTo(self.tw_tree.indexFromItem(sItem))

        if not wasBlocked:
            self.tw_tree.blockSignals(False)
            if self.getCurrentData() != prevData:
                self.onItemChanged()

    @err_catcher(name=__name__)
    def contextMenuTree(self, pos):
        rcmenu = QMenu(self)
        callbackName = ""

        if self.entityType == "asset":
            cItem = self.tw_tree.itemFromIndex(self.tw_tree.indexAt(pos))
            if cItem is None:
                path = self.core.assetPath
            else:
                path = cItem.data(0, Qt.UserRole)["paths"][0]
            typename = "Entity"
            callbackName = "openPBAssetContextMenu"
        elif self.entityType == "shot":
            path = self.core.shotPath
            typename = "Shot"
            callbackName = "openPBShotContextMenu"

            createAct = QAction("Create %s..." % typename, self)
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "shot.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            createAct.setIcon(icon)
            createAct.triggered.connect(self.editShotDlg)
            rcmenu.addAction(createAct)

        item = self.tw_tree.itemAt(pos)
        if item:
            if self.entityType == "asset":
                iname = os.path.basename(item.data(0, Qt.UserRole).get("asset_path"))
            elif self.entityType == "shot":
                data = item.data(0, Qt.UserRole)
                iname = data.get("shot")
                if not iname:
                    iname = data.get("sequence")
        else:
            iname = None

        data = self.getCurrentData()
        if iname:
            addOmit = False
            if self.entityType == "asset":
                if data:
                    subcat = QAction("Create Folder...", self)
                    iconPath = os.path.join(
                        self.core.prismRoot, "Scripts", "UserInterfacesPrism", "folder.png"
                    )
                    icon = self.core.media.getColoredIcon(iconPath)
                    subcat.setIcon(icon)
                    subcat.triggered.connect(lambda: self.createAssetDlg("folder"))
                    rcmenu.addAction(subcat)

                    subcat = QAction("Create Asset...", self)
                    iconPath = os.path.join(
                        self.core.prismRoot, "Scripts", "UserInterfacesPrism", "asset.png"
                    )
                    icon = self.core.media.getColoredIcon(iconPath)
                    subcat.setIcon(icon)
                    subcat.triggered.connect(lambda: self.createAssetDlg("asset"))
                    rcmenu.addAction(subcat)

                    oAct = QAction("Omit Asset", self)
                    oAct.triggered.connect(lambda: self.omitEntity(data))
                    addOmit = True

            elif self.entityType == "shot":
                if item.childCount() == 0 and data:
                    path = self.core.paths.getEntityPath(data)
                    editAct = QAction("Edit Shot Settings...", self)
                    iconPath = os.path.join(
                        self.core.prismRoot, "Scripts", "UserInterfacesPrism", "edit.png"
                    )
                    icon = self.core.media.getColoredIcon(iconPath)
                    editAct.setIcon(icon)
                    editAct.triggered.connect(lambda: self.editShotDlg(data))
                    rcmenu.addAction(editAct)
                    oAct = QAction("Omit Shot", self)
                    oAct.triggered.connect(lambda: self.omitEntity(data))
                    addOmit = True

            if (
                not os.path.exists(path)
                and self.core.useLocalFiles
                and os.path.exists(self.core.convertPath(path, "local"))
            ):
                path = self.core.convertPath(path, "local")

            act_refresh = QAction("Refresh", self)
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "refresh.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            act_refresh.setIcon(icon)
            act_refresh.triggered.connect(lambda: self.refreshEntities(restoreSelection=True))
            rcmenu.addAction(act_refresh)
            if self.entityType == "asset":
                actions = self.core.entities.getAssetActions()
            else:
                actions = self.core.entities.getShotActions()

            if actions:
                actMenu = QMenu("Actions", self)
                for action in actions:
                    openex = QAction(actions[action]["label"], self)
                    openex.triggered.connect(lambda x=None, act=actions[action]: self.runAction(act))
                    actMenu.addAction(openex)

                rcmenu.addMenu(actMenu)

            if self.entityWidget.parent().objectName() != "w_selEntities":
                if self.entityType == "asset":
                    openex = QAction("Connect Shots...", self)
                    openex.triggered.connect(self.openConnectEntitiesDlg)
                    rcmenu.addAction(openex)
                elif self.entityType == "shot":
                    openex = QAction("Connect Assets...", self)
                    openex.triggered.connect(self.openConnectEntitiesDlg)
                    rcmenu.addAction(openex)

            openex = QAction("Open in Explorer", self)
            openex.triggered.connect(lambda: self.core.openFolder(path))
            rcmenu.addAction(openex)
            copAct = QAction("Copy", self)
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "copy.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            copAct.setIcon(icon)
            copAct.triggered.connect(lambda: self.core.copyToClipboard(path, file=True))
            rcmenu.addAction(copAct)
            if addOmit:
                rcmenu.addAction(oAct)
        else:
            self.tw_tree.setCurrentIndex(self.tw_tree.model().createIndex(-1, 0))
            if self.entityType == "asset":
                subcat = QAction("Create Folder...", self)
                iconPath = os.path.join(
                    self.core.prismRoot, "Scripts", "UserInterfacesPrism", "folder.png"
                )
                icon = self.core.media.getColoredIcon(iconPath)
                subcat.setIcon(icon)
                subcat.triggered.connect(lambda: self.createAssetDlg("folder"))
                rcmenu.addAction(subcat)

                subcat = QAction("Create Asset...", self)
                iconPath = os.path.join(
                    self.core.prismRoot, "Scripts", "UserInterfacesPrism", "asset.png"
                )
                icon = self.core.media.getColoredIcon(iconPath)
                subcat.setIcon(icon)
                subcat.triggered.connect(lambda: self.createAssetDlg("asset"))
                rcmenu.addAction(subcat)

            act_refresh = QAction("Refresh", self)
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "refresh.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            act_refresh.setIcon(icon)
            act_refresh.triggered.connect(lambda: self.refreshEntities(restoreSelection=True))
            rcmenu.addAction(act_refresh)
            openex = QAction("Open in Explorer", self)
            openex.triggered.connect(lambda: self.core.openFolder(path))
            rcmenu.addAction(openex)
            copAct = QAction("Copy", self)
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "copy.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            copAct.setIcon(icon)
            copAct.triggered.connect(lambda: self.core.copyToClipboard(path, file=True))
            rcmenu.addAction(copAct)

        expAct = QAction("Expand all", self)
        expAct.triggered.connect(self.setWidgetItemsExpanded)
        clpAct = QAction("Collapse all", self)
        clpAct.triggered.connect(
            lambda x=None: self.setWidgetItemsExpanded(expanded=False)
        )
        prvAct = QAction("Show Previews", self)
        prvAct.setCheckable(True)
        showPrv = self.core.getConfig("browser", "showEntityPreviews", config="user", dft=True)
        prvAct.setChecked(showPrv)
        prvAct.toggled.connect(self.showPreviewToggled)
        rcmenu.insertAction(openex, expAct)
        rcmenu.insertAction(openex, clpAct)
        rcmenu.insertAction(openex, prvAct)

        if callbackName:
            self.core.callback(
                name=callbackName,
                args=[self, rcmenu, self.tw_tree.indexAt(pos)],
            )

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def runAction(self, action):
        data = self.getCurrentData(returnOne=False)
        action["function"](entities=data, parent=self.window())

    @err_catcher(name=__name__)
    def openConnectEntitiesDlg(self):
        data = self.getCurrentData(returnOne=False)
        if self.entityWidget.parent().objectName() == "gb_connectedEntities":
            self.entityWidget.parent().parent().parent().navigate(data)
        else:
            self.core.entities.connectEntityDlg(entities=data, parent=self)
