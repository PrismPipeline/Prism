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
import platform
from typing import Any, Optional, List, Dict, Tuple, Union

prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

if __name__ == "__main__":
    sys.path.append(os.path.join(prismRoot, "Scripts"))
    import PrismCore

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils import PrismWidgets, ProjectWidgets
from PrismUtils.Decorators import err_catcher
from UserInterfaces import MediaBrowser_ui


logger = logging.getLogger(__name__)


class MediaBrowser(QWidget, MediaBrowser_ui.Ui_w_mediaBrowser):
    """Main media browser widget for viewing and managing media products.
    
    The MediaBrowser provides a comprehensive interface for browsing, viewing,
    and managing rendered media products (images, image sequences, videos) in a
    Prism project. It supports:
    - Entity navigation (assets and shots)
    - Task/identifier browsing
    - Version management
    - AOV/layer/pass viewing
    - Media playback and preview
    - Media import and export
    - Version comparison
    
    Attributes:
        core: Prism core instance
        projectBrowser: Parent ProjectBrowser widget
        initialized: Whether the browser has been initialized
        oiio: OpenImageIO instance for image handling
    """
    
    def __init__(self, core: Any, projectBrowser: Optional[Any] = None, refresh: bool = True) -> None:
        """Initialize the MediaBrowser.
        
        Args:
            core: The Prism core instance
            projectBrowser: Parent ProjectBrowser widget (optional)
            refresh: Whether to refresh/load entities immediately
        """
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
    def entered(self, prevTab: Optional[Any] = None, navData: Optional[Any] = None) -> None:
        """Handle tab activation and initialization.
        
        Called when the MediaBrowser tab is entered/shown. Initializes the entity
        widget and navigates to the appropriate entity based on navigation data.
        
        Args:
            prevTab: Previously active tab widget
            navData: Navigation data specifying which entity to show
        """
        if prevTab:
            if hasattr(prevTab, "w_entities"):
                navData = prevTab.w_entities.getCurrentData()
            elif hasattr(prevTab, "getSelectedData"):
                navData = prevTab.getSelectedData()
        
        if not self.initialized:
            if not navData:
                navData = self.getCurrentNavData()

            self.w_entities.getPage("Assets").blockSignals(True)
            self.w_entities.getPage("Shots").blockSignals(True)
            self.w_entities.tb_entities.blockSignals(True)
            self.w_entities.blockSignals(True)
            self.w_entities.navigate(navData)
            self.w_entities.refreshEntities(defaultSelection=False)
            self.w_entities.getPage("Assets").blockSignals(False)
            self.w_entities.getPage("Shots").blockSignals(False)
            self.w_entities.tb_entities.blockSignals(False)
            self.w_entities.blockSignals(False)
            self.oiio = self.core.media.getOIIO()
            if navData:
                self.navigate(navData)

            if not self.getCurrentEntity():
                self.entityChanged()

            self.initialized = True

        if prevTab:
            if hasattr(prevTab, "w_entities"):
                self.w_entities.syncFromWidget(prevTab.w_entities, navData=navData)
            elif hasattr(prevTab, "getSelectedData"):
                self.navigateToEntity(navData)

    @err_catcher(name=__name__)
    def loadLayout(self) -> None:
        """Load and configure the UI layout.
        
        Sets up the entity widget, splitters, preview player, and drag-drop functionality.
        Restores saved window sizes and settings from configuration.
        """
        import EntityWidget

        self.w_entities = EntityWidget.EntityWidget(core=self.core, refresh=False, mode="media")
        self.splitter1.insertWidget(0, self.w_entities)

        self.w_autoUpdate.setVisible(False)

        cData = self.core.getConfig()
        brsData = cData.get("browser", {})

        doGroup = os.getenv("PRISM_MEDIA_GROUP_BY_TYPE")
        if doGroup is not None:
            self.groupByType = bool(doGroup.lower() == "1")
        else:
            self.groupByType = brsData.get("groupIdentifiersByType", True)

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
        self.splitter1.addWidget(self.w_preview)

        if self.projectBrowser and self.projectBrowser.act_rememberWidgetSizes.isChecked():
            if "mediaSplitter1" in brsData:
                self.splitter1.setSizes(brsData["mediaSplitter1"])

        self.tw_identifier.setAcceptDrops(True)
        self.tw_identifier.dragEnterEvent = self.taskDragEnterEvent
        self.tw_identifier.dragMoveEvent = self.taskDragMoveEvent
        self.tw_identifier.dragLeaveEvent = self.taskDragLeaveEvent
        self.tw_identifier.dropEvent = self.taskDropEvent
        self.tw_identifier.setObjectName("tw_identifier")

        self.lw_version.setAcceptDrops(True)
        self.lw_version.dragEnterEvent = self.versionDragEnterEvent
        self.lw_version.dragMoveEvent = self.versionDragMoveEvent
        self.lw_version.dragLeaveEvent = self.versionDragLeaveEvent
        self.lw_version.dropEvent = self.versionDropEvent
        self.lw_version.setObjectName("lw_version")

        if self.projectBrowser and len(self.projectBrowser.locations) > 1:
            self.VersionDelegate = VersionDelegate(self)
            self.lw_version.setItemDelegate(self.VersionDelegate)

        if "previewDisabled" in brsData:
            self.w_preview.mediaPlayer.state = "disabled" if brsData["previewDisabled"] else "enabled"

        self.setStyleSheet("QSplitter::handle{background-color: transparent}")

    @err_catcher(name=__name__)
    def showEvent(self, event: Any) -> None:
        """Handle widget show event.
        
        Adjusts header heights to align entity, identifier, version, and preview sections
        on first show.
        
        Args:
            event: Qt show event
        """
        if not getattr(self, "headerHeightSet", False):
            spacing = self.w_identifier.layout().spacing()
            h = self.w_entities.w_header.geometry().height() - spacing
            self.setHeaderHeight(h)

    @err_catcher(name=__name__)
    def setHeaderHeight(self, height: int) -> None:
        """Set uniform height for all column headers.
        
        Args:
            height: Target height in pixels for headers
        """
        spacing = self.w_identifier.layout().spacing()
        self.w_entities.w_header.setMinimumHeight(height + spacing)
        self.l_identifier.setMinimumHeight(height)
        self.l_version.setMinimumHeight(height)
        self.w_preview.l_layer.setMinimumHeight(height)
        self.headerHeightSet = True

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect UI signals to handler methods.
        
        Sets up connections for entity changes, task/version selection, context menus,
        and drag-drop functionality.
        """
        self.w_entities.getPage("Assets").itemChanged.connect(self.entityChanged)
        self.w_entities.getPage("Shots").itemChanged.connect(self.entityChanged)
        self.w_entities.tabChanged.connect(self.entityTabChanged)

        self.chb_autoUpdate.stateChanged.connect(self.updateChanged)
        self.b_refresh.clicked.connect(self.refreshRender)

        self.tw_identifier.itemSelectionChanged.connect(self.taskClicked)
        self.lw_version.itemSelectionChanged.connect(self.versionClicked)
        self.lw_version.mmEvent = self.lw_version.mouseMoveEvent
        self.lw_version._dragStartPos = None
        self.lw_version._origMousePressEvent = self.lw_version.mousePressEvent

        def _lw_version_mousePressEvent(event):
            self.lw_version._dragStartPos = event.pos()
            self.lw_version._origMousePressEvent(event)

        def _lw_version_mouseMoveEvent(event):
            if (
                self.lw_version._dragStartPos is not None
                and (event.pos() - self.lw_version._dragStartPos).manhattanLength() >= 30
            ):
                self.w_preview.mediaPlayer.mouseDrag(event, self.lw_version)
            else:
                self.lw_version.mmEvent(event)

        self.lw_version.mousePressEvent = _lw_version_mousePressEvent
        self.lw_version.mouseMoveEvent = _lw_version_mouseMoveEvent
        self.lw_version.itemDoubleClicked.connect(self.onVersionDoubleClicked)
        self.tw_identifier.customContextMenuRequested.connect(
            lambda x: self.rclList(x, self.tw_identifier)
        )
        self.lw_version.customContextMenuRequested.connect(
            lambda x: self.rclList(x, self.lw_version)
        )

    @err_catcher(name=__name__)
    def saveSettings(self, data: Dict[str, Any]) -> None:
        """Save MediaBrowser settings to configuration.
        
        Args:
            data: Configuration dictionary to update with current settings
        """
        data["browser"]["autoUpdateRenders"] = self.chb_autoUpdate.isChecked()
        data["browser"]["previewDisabled"] = self.w_preview.mediaPlayer.state == "disabled"
        data["browser"]["mediaSplitter1"] = self.splitter1.sizes()
        data["browser"]["groupIdentifiersByType"] = self.groupByType

    @err_catcher(name=__name__)
    def updateChanged(self, state: int) -> None:
        """Handle auto-update checkbox state change.
        
        Args:
            state: Checkbox state (Qt.Checked or Qt.Unchecked)
        """
        if state:
            self.updateTasks()

    @err_catcher(name=__name__)
    def entityTabChanged(self) -> None:
        """Handle switching between Assets and Shots tabs."""
        self.entityChanged()

    @err_catcher(name=__name__)
    def entityChanged(self, item: Optional[Any] = None) -> None:
        """Handle entity selection change.
        
        Args:
            item: Selected entity item (optional)
        """
        self.updateTasks(restoreSelection=True)

    @err_catcher(name=__name__)
    def refreshUI(self) -> None:
        """Refresh the entire UI including entities and renders.
        
        Clears caches and reloads all displayed data while maintaining current selection.
        """
        self.core.media.invalidateOiioCache()
        self.w_entities.getCurrentPage().tw_tree.blockSignals(True)
        self.w_entities.getCurrentPage().tw_tree.selectionModel().blockSignals(True)
        self.w_entities.refreshEntities(restoreSelection=True)
        self.w_entities.getCurrentPage().tw_tree.blockSignals(False)
        self.w_entities.getCurrentPage().tw_tree.selectionModel().blockSignals(False)
        self.entityChanged()
        self.refreshStatus = "valid"

    @err_catcher(name=__name__)
    def getCurrentData(self) -> Dict[str, Any]:
        """Get comprehensive data about current selection.
        
        Returns:
            Dictionary containing entity, identifier, version, aov, and source information
        """
        curIdentifier = self.getCurrentIdentifier()
        if curIdentifier:
            identifier = curIdentifier.get("displayName") or ""
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
            source = curSource.get("source") or ""
        else:
            source = ""

        curData = self.getCurrentEntity()
        curData["identifier"] = identifier
        curData["version"] = version
        curData["aov"] = aov
        curData["source"] = source
        return curData

    @err_catcher(name=__name__)
    def refreshRender(self) -> None:
        """Refresh the current render display by re-navigating to current selection."""
        curData = self.getCurrentData()
        self.navigate(curData)

    @err_catcher(name=__name__)
    def getCurrentEntity(self) -> Dict[str, Any]:
        """Get currently selected entity.
        
        Returns:
            Entity dictionary with type (asset/shot) and path information
        """
        return self.w_entities.getCurrentPage().getCurrentData()

    @err_catcher(name=__name__)
    def getCurrentEntities(self) -> List[Dict[str, Any]]:
        """Get all currently selected entities (supports multi-selection).
        
        Returns:
            List of entity dictionaries
        """
        return self.w_entities.getCurrentPage().getCurrentData(returnOne=False)

    @err_catcher(name=__name__)
    def getCurrentIdentifier(self, allowMultiple: bool = False) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Get currently selected identifier/task.
        
        Args:
            allowMultiple: If True, return list of identifiers; if False, return single or None
        
        Returns:
            Single identifier dict, list of identifier dicts, or None
        """
        items = self.tw_identifier.selectedItems()
        items = [item for item in items if not (item.data(0, Qt.UserRole) or {}).get("isGroup") and not (item.data(0, Qt.UserRole) or {}).get("isTypeGroup")]
        if not items:
            return

        if len(items) > 1:
            datas = []
            if allowMultiple:
                for item in items:
                    data = item.data(0, Qt.UserRole)
                    if data:
                        datas.append(data)

                return datas
            else:
                return
        else:
            data = items[0].data(0, Qt.UserRole)
            if allowMultiple:
                return [data]
            else:
                return data

    @err_catcher(name=__name__)
    def getCurrentVersion(self) -> Optional[Dict[str, Any]]:
        """Get currently selected version.
        
        Returns:
            Version dictionary with path and metadata, or None if no selection
        """
        items = self.lw_version.selectedItems()
        if not items:
            return

        return items[0].data(Qt.UserRole)

    @err_catcher(name=__name__)
    def getCurrentVersions(self) -> List[Dict[str, Any]]:
        """Get all currently selected versions (supports multi-selection).
        
        Returns:
            List of version dictionaries
        """
        items = self.lw_version.selectedItems()
        if not items:
            return []

        versions = [item.data(Qt.UserRole) for item in items]
        return versions

    @err_catcher(name=__name__)
    def getCurrentAOV(self) -> Optional[Dict[str, Any]]:
        """Get currently selected AOV/render pass.
        
        Returns:
            AOV dictionary with name and path, or None
        """
        return self.w_preview.getCurrentAOV()

    @err_catcher(name=__name__)
    def getCurrentSource(self) -> Optional[Dict[str, Any]]:
        """Get currently selected source (for multi-source renders).
        
        Returns:
            Source dictionary, or None
        """
        return self.w_preview.getCurrentSource()

    @err_catcher(name=__name__)
    def getCurrentFilelayer(self) -> Optional[Dict[str, Any]]:
        """Get currently selected file layer/channel (e.g., RGBA, depth).
        
        Returns:
            File layer dictionary, or None
        """
        return self.w_preview.getCurrentFilelayer()

    @err_catcher(name=__name__)
    def getMediaTasks(self, entity: Optional[Dict[str, Any]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get all media identifiers/tasks for an entity.
        
        Args:
            entity: Entity dict (defaults to current entity if not provided)
        
        Returns:
            Dictionary with keys '3d', '2d', 'playblast', 'external', each containing
            list of identifier dictionaries
        """
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
    def findIdentifierItemByDisplayName(self, displayName: str) -> Optional[Any]:
        """DFS search for the first tree item whose identifier displayName matches.

        Skips group items and type-group items. Returns None if not found.

        Args:
            displayName: The identifier displayName to search for

        Returns:
            Matching QTreeWidgetItem, or None
        """
        stack = [self.tw_identifier.invisibleRootItem()]
        while stack:
            node = stack.pop()
            data = node.data(0, Qt.UserRole)
            if data and not data.get("isGroup") and not data.get("isTypeGroup"):
                if data.get("displayName") == displayName:
                    return node
            for i in range(node.childCount()):
                stack.append(node.child(i))
        return None

    @err_catcher(name=__name__)
    def getFirstIdentifierItem(self) -> Optional[Any]:
        """DFS search for the first tree item that holds actual identifier data.

        Skips group and type-group items. Returns None if the tree is empty.

        Returns:
            First identifier QTreeWidgetItem, or None
        """
        stack = [self.tw_identifier.invisibleRootItem()]
        while stack:
            node = stack.pop(0)
            data = node.data(0, Qt.UserRole)
            if data and not data.get("isGroup") and not data.get("isTypeGroup"):
                return node
            for i in range(node.childCount()):
                stack.insert(i, node.child(i))
        return None

    @err_catcher(name=__name__)
    def toggleGroupByType(self) -> None:
        """Toggle the 'organize by type' grouping mode and refresh the task list."""
        self.groupByType = not self.groupByType
        self.core.setConfig("browser", "groupIdentifiersByType", self.groupByType)
        self.updateTasks(restoreSelection=True)

    @err_catcher(name=__name__)
    def updateTasks(self, restoreSelection: bool = False) -> None:
        """Update the identifier/task tree widget with available media tasks.
        
        Populates the task list organized by department and task (if configured),
        or as a flat list. Tasks can be grouped into folders.
        
        Args:
            restoreSelection: If True, attempt to restore previously selected task
        """
        if restoreSelection:
            curTask = None
            identifier = self.getCurrentIdentifier()
            if identifier:
                curTask = identifier.get("displayName")

        wasBlocked = self.tw_identifier.signalsBlocked()
        if not wasBlocked:
            self.tw_identifier.blockSignals(True)

        self.tw_identifier.clear()

        mediaTasks = self.getMediaTasks()
        if mediaTasks:
            useTasks = self.core.mediaProducts.getLinkedToTasks()
            if useTasks:
                groups, groupItems = self.createGroupItems(mediaTasks)
                items = {}
                for pType in ["3d", "2d", "playblast", "external"]:
                    for task in sorted(mediaTasks[pType], key=lambda x: x["displayName"].lower()):
                        useDep = os.getenv("PRISM_USE_DEPARTMENTS_FOR_PRODUCTS", "1") == "1"
                        if useDep:
                            dep = task.get("department") or "unknown"
                            if dep not in items:
                                item = QTreeWidgetItem([dep])
                                items[dep] = {"item": item, "tasks": {}}
                                self.tw_identifier.invisibleRootItem().addChild(item)

                            taskName = task.get("task") or "unknown"
                            if taskName not in items[dep]["tasks"]:
                                item = QTreeWidgetItem([taskName])
                                items[dep]["tasks"][taskName] = {"item": item}
                                items[dep]["item"].addChild(item)

                            if task["displayName"] in groups:
                                parent = groupItems[groups[task["displayName"]]]
                            else:
                                parent = items[dep]["tasks"][taskName]["item"]
                        else:
                            taskName = task.get("task") or "unknown"
                            if taskName not in items:
                                item = QTreeWidgetItem([taskName])
                                items[taskName] = {"item": item}
                                self.tw_identifier.invisibleRootItem().addChild(item)

                            if task["displayName"] in groups:
                                parent = groupItems[groups[task["displayName"]]]
                            else:
                                parent = items[taskName]["item"]

                        parChildren = [parent.child(idx).text(0) for idx in range(parent.childCount())]
                        if task["displayName"] in parChildren:
                            continue

                        item = QTreeWidgetItem([task["displayName"]])
                        item.setData(0, Qt.UserRole, task)
                        parent.addChild(item)
            elif getattr(self, "groupByType", True):
                typeLabels = {"3d": "3D", "2d": "2D", "playblast": "Playblast", "external": "External"}
                for pType in ["3d", "2d", "playblast", "external"]:
                    typeTasks = mediaTasks.get(pType, [])
                    if not typeTasks:
                        continue

                    typeItem = QTreeWidgetItem([typeLabels[pType]])
                    typeItem.setData(0, Qt.UserRole, {"isTypeGroup": True})
                    self.tw_identifier.invisibleRootItem().addChild(typeItem)

                    typeGroups, typeGroupItems = self.createGroupItems({pType: typeTasks}, rootItem=typeItem)
                    addedItems = []
                    for task in sorted(typeTasks, key=lambda x: x["identifier"].lower()):
                        if task["displayName"] in addedItems:
                            continue

                        addedItems.append(task["displayName"])
                        itemLabel = task["identifier"]
                        item = QTreeWidgetItem([itemLabel])
                        item.setData(0, Qt.UserRole, task)
                        if task["displayName"] in typeGroups:
                            parent = typeGroupItems[typeGroups[task["displayName"]]]
                        else:
                            parent = typeItem

                        parent.addChild(item)

                    typeItem.setExpanded(True)
            else:
                groups, groupItems = self.createGroupItems(mediaTasks)
                addedItems = []
                for pType in ["3d", "2d", "playblast", "external"]:
                    for task in sorted(mediaTasks[pType], key=lambda x: x["displayName"].lower()):
                        if task["displayName"] in addedItems:
                            continue

                        item = QTreeWidgetItem([task["displayName"]])
                        addedItems.append(task["displayName"])
                        item.setData(0, Qt.UserRole, task)
                        if task["displayName"] in groups:
                            parent = groupItems[groups[task["displayName"]]]
                        else:
                            parent = self.tw_identifier.invisibleRootItem()

                        parent.addChild(item)

        if self.tw_identifier.topLevelItemCount() > 0:
            selectFirst = True
            if restoreSelection and curTask:
                match = self.findIdentifierItemByDisplayName(curTask)
                if match:
                    self.tw_identifier.setCurrentItem(match)
                    selectFirst = False

            if selectFirst:
                mainMatch = self.findIdentifierItemByDisplayName("main")
                if mainMatch:
                    self.tw_identifier.setCurrentItem(mainMatch)
                else:
                    firstItem = self.getFirstIdentifierItem()
                    if firstItem:
                        self.tw_identifier.setCurrentItem(firstItem)

        if not wasBlocked:
            self.tw_identifier.blockSignals(False)
            self.updateVersions(restoreSelection=True)

    @err_catcher(name=__name__)
    def createGroupItems(self, identifiers: Dict[str, List[Dict[str, Any]]], rootItem: Optional[Any] = None) -> Tuple[Dict[str, str], Dict[str, Any]]:
        """Create tree items for identifier groups/folders.
        
        Args:
            identifiers: Dictionary of identifier lists by type
            rootItem: Parent item to attach top-level folder groups to.
                      Defaults to the tree's invisible root item.
        
        Returns:
            Tuple of (groups dict mapping identifier names to group paths,
                     groupItems dict mapping group paths to QTreeWidgetItems)
        """
        idfs = []
        for idfType in identifiers:
            for identifier in identifiers[idfType]:
                if identifier["displayName"] not in [idf["displayName"] for idf in idfs]:
                    idfs.append(identifier)

        groups = {}
        for idf in idfs:
            identifierName = idf["displayName"]
            group = self.core.mediaProducts.getGroupFromIdentifier(idf)
            if group:
                groups[identifierName] = group

        groupNames = sorted(list(set(groups.values())))
        groupItems = {}
        for group in groupNames:
            gfolders = group.split("/")
            curPath = ""
            for gfolder in gfolders:
                
                if not gfolder:
                    continue

                newPath = curPath
                if newPath:
                    newPath += "/"

                newPath += gfolder
                if newPath in groupItems:
                    curPath = newPath
                    continue

                item = QTreeWidgetItem([gfolder])
                item.setData(0, Qt.UserRole, {"isGroup": True})
                iconPath = os.path.join(
                    self.core.prismRoot, "Scripts", "UserInterfacesPrism", "folder.png"
                )
                icon = self.core.media.getColoredIcon(iconPath)
                item.setIcon(0, icon)
                if curPath and curPath in groupItems:
                    parent = groupItems[curPath]
                else:
                    parent = rootItem if rootItem is not None else self.tw_identifier.invisibleRootItem()

                parent.addChild(item)
                curPath = newPath
                groupItems[curPath] = item

        return groups, groupItems

    @err_catcher(name=__name__)
    def sortVersions(self, key: Dict[str, Any]) -> str:
        """Sort key function for version sorting.
        
        Args:
            key: Version dictionary
        
        Returns:
            Sort key string ("master" becomes "zz_master" to sort last)
        """
        val = key["version"]
        if val == "master":
            val = "zz_master"

        return val

    @err_catcher(name=__name__)
    def updateVersions(self, restoreSelection: bool = False) -> None:
        """Update version list widget with versions from selected identifier.
        
        Versions are sorted in reverse order (latest first), with "master" appearing first.
        
        Args:
            restoreSelection: If True, attempt to restore previously selected version
        """
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
        identifier = self.getCurrentIdentifier()
        if len(self.tw_identifier.selectedItems()) == 1 and identifier:
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

                vdata = self.core.paths.getRenderProductData(version["path"], isFilepath=False, addPathData=False, mediaType=version["mediaType"], validateModTime=False)
                if "project_path" in vdata:
                    del vdata["project_path"]

                comment = vdata.get("comment")
                if comment:
                    versionName += " - " + comment

                versionData = version.copy()
                if versionData["version"] == "master":
                    vdata["version"] = "master"

                locs = versionData["locations"]
                versionData.update(vdata)
                versionData["locations"] = locs
                if len(locs) > 1 or len(versionData.get("locations", {})) > 1 or ("global" not in versionData.get("locations", {})):
                    locStr = ", ".join([loc for loc in versionData.get("locations", {}) if ((loc and loc != "global") or len(versionData.get("locations", {})) > 1)])
                    if locStr:
                        versionName += " (%s)" % locStr

                item = QListWidgetItem(versionName)
                item.setData(Qt.UserRole, versionData)
                if len(locs) > 1:
                    item.setToolTip(", ".join(versionData.get("locations", {})))

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
    def getSelectedContexts(self) -> List[Dict[str, Any]]:
        """Get all currently selected contexts for operations.
        
        Checks for multiple selected identifiers, versions, or returns the most
        specific selection (filelayer > source > AOV > version).
        
        Returns:
            List of context dictionaries
        """
        contexts = []
        if len(self.tw_identifier.selectedItems()) > 1:
            items = self.tw_identifier.selectedItems()
            for item in items:
                contexts.append(item.data(0, Qt.UserRole))

        elif len(self.lw_version.selectedItems()) > 1:
            items = self.lw_version.selectedItems()
            for item in items:
                contexts.append(item.data(Qt.UserRole))

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
    def taskClicked(self) -> None:
        """Handle identifier/task selection in tree widget."""
        self.updateVersions()

    @err_catcher(name=__name__)
    def versionClicked(self) -> None:
        """Handle version selection in list widget."""
        self.w_preview.updateLayers(restoreSelection=True)

    @err_catcher(name=__name__)
    def onVersionDoubleClicked(self, item: Any) -> None:
        """Handle double-click on version item.
        
        Args:
            item: QListWidgetItem that was double-clicked
            
        Note:
            - Ctrl+Double-click opens file explorer to version folder
            - Normal double-click shows version info dialog
        """
        mods = QApplication.keyboardModifiers()
        if mods == Qt.ControlModifier:
            for selItem in self.lw_version.selectedItems():
                self.core.openFolder(selItem.data(Qt.UserRole).get("path"))
        else:
            self.showVersionInfoForItem(item)

    @err_catcher(name=__name__)
    def mouseDrag(self, event: Any, element: Any) -> None:
        """Handle mouse drag to initiate drag-and-drop operation.
        
        Allows dragging media files or folders to external applications.
        
        Args:
            event: Mouse event
            element: Widget element being dragged from
            
        Note:
            - Left drag: Drag media files
            - Ctrl+Left drag: Drag media folder
            - Middle drag on layer combo: Drag all AOVs
        """
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
    def editComment(self, filepath: str) -> None:
        """Open dialog to edit version comment.
        
        Args:
            filepath: Path to the version directory
        """
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
    def goToSource(self, source: str) -> None:
        """Navigate to the source scene in SceneBrowser.
        
        Args:
            source: Path to the source scene file
        """
        if not source:
            msg = "This version doesn't have a source scene."
            self.core.popup(msg)
            return

        self.projectBrowser.showTab("Scenefiles")
        fileNameData = self.core.getScenefileData(source)
        self.projectBrowser.sceneBrowser.navigate(data=fileNameData)

    @err_catcher(name=__name__)
    def showVersionInfoForItem(self, item: Any) -> None:
        """Show version info dialog for a list widget item.
        
        Args:
            item: QListWidgetItem containing version data
        """
        context = item.data(Qt.UserRole)
        self.showVersionInfo(context)

    @err_catcher(name=__name__)
    def showVersionInfo(self, context: Dict[str, Any]) -> None:
        """Display detailed version information dialog.
        
        Shows version metadata including source scene, comment, creation date, etc.
        
        Args:
            context: Version dictionary with metadata
        """
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
    def showDependencies(self, context: Dict[str, Any]) -> None:
        """Show dependency viewer for a version.
        
        Args:
            context: Version dictionary
        """
        path = self.core.mediaProducts.getVersionInfoPathFromContext(context)

        if not os.path.exists(path):
            self.core.popup("No dependency information was saved with this version.")
            return

        self.core.dependencyViewer(path)

    @err_catcher(name=__name__)
    def getSelectedContext(self) -> Dict[str, Any]:
        """Get current data as a context dictionary.
        
        Returns:
            Current selection data dictionary
        """
        return self.getCurrentData()

    @err_catcher(name=__name__)
    def getCurrentNavData(self) -> Dict[str, Any]:
        """Get navigation data for restoring browser state.
        
        Returns:
            Dictionary with type, asset_path/sequence/shot keys for current selection
        """
        fileName = self.core.getCurrentFileName()
        navData = self.core.getScenefileData(fileName)
        return navData

    @err_catcher(name=__name__)
    def navigateToCurrent(self) -> None:
        """Navigate to entity from currently open scene file."""
        navData = self.getCurrentNavData()
        self.showRender(entity=navData)

    @err_catcher(name=__name__)
    def navigate(self, data: Union[Dict[str, Any], List[Any]]) -> None:
        """Navigate to entity and selection state.
        
        Args:
            data: Navigation dictionary or list of navigation parameters
        """
        if isinstance(data, list):
            self.showRender(*data)
        else:
            self.showRender(
                entity=data,
                identifier=data.get("identifier"),
                version=data.get("version"),
                aov=data.get("aov"),
                source=data.get("source"),
            )

    @err_catcher(name=__name__)
    def navigateToEntity(self, entity: Dict[str, Any]) -> None:
        """Navigate entity widget to specified entity.
        
        Args:
            entity: Entity dictionary with type and path information
        """
        self.w_entities.navigate(entity)

    @err_catcher(name=__name__)
    def showRender(self, entity: Optional[Dict[str, Any]] = None, identifier: Optional[str] = None, 
                   version: Optional[str] = None, aov: Optional[str] = None, 
                   source: Optional[str] = None, filelayer: Optional[str] = None) -> None:
        """Display a specific render with given parameters.
        
        Args:
            entity: Entity dictionary
            identifier: Identifier/task name
            version: Version name
            aov: AOV/pass name
            source: Source name (for multi-source)
            filelayer: File layer/channel name
        """
        prevIdf = self.getCurrentIdentifier()
        self.tw_identifier.blockSignals(True)
        if entity:
            self.navigateToEntity(entity)

        if not identifier:
            self.tw_identifier.blockSignals(False)
            if prevIdf != self.getCurrentIdentifier() or not self.initialized:
                self.taskClicked()

            return

        match = self.findIdentifierItemByDisplayName(identifier)
        matches = [match] if match else []
        if not matches:
            self.tw_identifier.blockSignals(False)
            if prevIdf != self.getCurrentIdentifier() or not self.initialized:
                self.taskClicked()

            return

        self.tw_identifier.setCurrentItem(matches[0])
        self.tw_identifier.blockSignals(False)
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

        self.lw_version.clearSelection()
        self.lw_version.setCurrentItem(vMatches[0])
        self.lw_version.blockSignals(False)
        if prevVersion != self.getCurrentVersion():
            self.versionClicked()
            result = self.w_preview.navigate(aov, source, filelayer, updateLayers=False)
            if not result:
                self.w_preview.layerChanged()

    @err_catcher(name=__name__)
    def setPreview(self) -> None:
        """Set current preview image as entity thumbnail."""
        entity = self.getCurrentEntity()
        pm = self.w_preview.mediaPlayer.l_preview.pixmap()
        self.core.entities.setEntityPreview(entity, pm)
        self.core.pb.sceneBrowser.refreshEntityInfo()
        self.w_entities.getCurrentPage().refreshEntities(restoreSelection=True)

    @err_catcher(name=__name__)
    def rclList(self, pos: Any, lw: Any) -> None:
        """Show context menu for task or version list.
        
        Args:
            pos: Mouse position
            lw: List widget (identifier tree or version list)
        """
        cpos = QCursor.pos()
        item = lw.itemAt(pos)
        if item is not None:
            if lw == self.tw_identifier:
                itemName = item.text(0)
            else:
                itemName = item.text()
        else:
            itemName = ""

        entity = self.getCurrentEntity()
        if not entity:
            return False

        if lw == self.tw_identifier:
            path = None
            isGroup = False
            if itemName:
                data = item.data(0, Qt.UserRole)
                isGroup = data and data.get("isGroup")
                if data and not isGroup:
                    path = data.get("path")
            
            if not path:
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
        if lw == self.tw_identifier:
            refresh = self.updateTasks
            if entity.get("type") in ["asset", "shot"]:
                depAct = QAction("Create Identifier...", self)
                depAct.triggered.connect(self.createIdentifierDlg)
                rcmenu.addAction(depAct)

                exAct = QAction("Ingest media...", self)
                exAct.triggered.connect(self.ingestMediaDlg)
                rcmenu.addAction(exAct)

                if isGroup:
                    depAct = QAction("Ungroup", self)
                    iconPath = os.path.join(
                        self.core.prismRoot, "Scripts", "UserInterfacesPrism", "folder.png"
                    )
                    icon = self.core.media.getColoredIcon(iconPath)
                    depAct.setIcon(icon)
                    depAct.triggered.connect(lambda: self.ungroupIdentifiers(itemName))
                    rcmenu.addAction(depAct)
                else:
                    depAct = QAction("Group selected...", self)
                    iconPath = os.path.join(
                        self.core.prismRoot, "Scripts", "UserInterfacesPrism", "folder.png"
                    )
                    icon = self.core.media.getColoredIcon(iconPath)
                    depAct.setIcon(icon)
                    depAct.triggered.connect(self.groupIdentifiersDlg)
                    rcmenu.addAction(depAct)

        elif lw == self.lw_version:
            refresh = self.updateVersions
            identifier = self.getCurrentIdentifier()
            if identifier:
                depAct = QAction("Create Version...", self)
                depAct.triggered.connect(self.createVersionDlg)
                rcmenu.addAction(depAct)

                if identifier.get("mediaType") == "externalMedia":
                    nvAct = QAction("Create new External Version...", self)
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

                if self.projectBrowser:
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

        if lw == self.tw_identifier:
            useTasks = self.core.mediaProducts.getLinkedToTasks()
            if not useTasks:
                rcmenu.addSeparator()
                act_groupByType = QAction("Organize by Type", self)
                act_groupByType.setCheckable(True)
                act_groupByType.setChecked(getattr(self, "groupByType", True))
                act_groupByType.triggered.connect(self.toggleGroupByType)
                rcmenu.addAction(act_groupByType)

        if os.path.exists(path):
            opAct = QAction("Open in Explorer", self)
            opAct.triggered.connect(lambda: self.core.openFolder(path))
            rcmenu.addAction(opAct)

            copAct = self.core.getCopyAction(path, parent=self)
            rcmenu.addAction(copAct)

        if lw == self.lw_version:
            copAct = QAction("Copy path for next version", self)
            copAct.triggered.connect(self.prepareNewVersion)
            rcmenu.addAction(copAct)

            if itemName:
                existingLocs = list(data.get("locations", {}).keys())
                locMenu = QMenu("Copy to", self)
                locs = self.core.paths.getRenderProductBasePaths()
                for loc in locs:
                    if loc in existingLocs:
                        continue

                    copAct = QAction(loc, self)
                    copAct.triggered.connect(lambda x=None, l=loc: self.copyToLocation(path, l))
                    locMenu.addAction(copAct)

                if not locMenu.isEmpty():
                    rcmenu.addMenu(locMenu)

        self.core.callback(
            name="openPBListContextMenu",
            args=[self, rcmenu, lw, item, path],
        )

        if rcmenu.isEmpty():
            return False

        rcmenu.exec_(cpos)

    @err_catcher(name=__name__)
    def prepareNewVersion(self) -> None:
        """Copy the path for the next version to clipboard.
        
        Generates the output path for the next version and saves it to clipboard,
        also writing scene info for the new version.
        """
        curEntity = self.getCurrentEntity()
        curIdentifier = self.getCurrentIdentifier()
        if not curIdentifier:
            return

        if self.core.mediaProducts.getLinkedToTasks():
            curEntity["department"] = curIdentifier.get("department", "unknown")
            curEntity["task"] = curIdentifier.get("task", "unknown")

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
        self.updateVersions(restoreSelection=True)

    @err_catcher(name=__name__)
    def copyToLocation(self, path: str, location: str) -> None:
        """Copy version folder to a different location/server.
        
        Args:
            path: Source version folder path
            location: Target location name
        """
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
    def createIdentifierDlg(self) -> None:
        """Show dialog to create a new identifier/task."""
        curEntity = self.getCurrentEntity()
        self.newItem = ProjectWidgets.CreateIdentifierDlg(self, entity=curEntity)
        self.newItem.e_identifier.setFocus()
        self.newItem.accepted.connect(self.createIdentifier)
        self.core.callback(name="onCreateIdentifierDlgOpen", args=[self, self.newItem])
        self.newItem.show()

    @err_catcher(name=__name__)
    def createIdentifier(self) -> None:
        """Create a new identifier/task from the dialog.
        
        Creates the identifier folder structure and updates the task list.
        """
        self.activateWindow()
        itemName = self.newItem.e_identifier.text()
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
        elif mediaTypeLabel == "External":
            mediaType = "externalMedia"
            suffix = " (external)"

        if self.core.mediaProducts.getLinkedToTasks():
            curEntity["department"] = self.newItem.e_department.text() or "unknown"
            curEntity["task"] = self.newItem.e_task.text() or "unknown"

        location = self.newItem.cb_location.currentText()
        self.core.mediaProducts.createIdentifier(
            entity=curEntity,
            identifier=itemName,
            identifierType=mediaType,
            location=location,
        )
        selItems = self.tw_identifier.selectedItems()
        if len(selItems) == 1 and (selItems[0].data(0, Qt.UserRole) or {}).get("isGroup"):
            item = selItems[0]
            group = selItems[0].text(0)
            while item.parent():
                group = item.parent().text(0) + "/" + group
                item = item.parent()

            context = curEntity.copy()
            displayName = self.core.mediaProducts.getDisplayNameForIdentifier(itemName, mediaType)
            context["displayName"] = displayName
            self.core.mediaProducts.setIdentifiersGroup([context], group=group)

        self.updateTasks()
        if itemName is not None:
            displayName = self.core.mediaProducts.getDisplayNameForIdentifier(itemName, mediaType)
            match = self.findIdentifierItemByDisplayName(displayName)
            if match:
                self.tw_identifier.setCurrentItem(match)

    @err_catcher(name=__name__)
    def createVersionDlg(self) -> None:
        """Show dialog to create a new version folder."""
        context = self.getCurrentIdentifier()
        version = self.core.mediaProducts.getHighestMediaVersion(context)
        intVersion = self.core.products.getIntVersionFromVersionName(version)
        self.newItem = ProjectWidgets.CreateMediaVersionDlg(self, entity=context)
        if intVersion is not None:
            self.newItem.sp_version.setValue(intVersion)

        location = self.core.mediaProducts.getLocationFromPath(context["path"])
        if location:
            self.newItem.cb_location.setCurrentText(location)

        self.newItem.sp_version.setFocus()
        self.newItem.accepted.connect(self.createVersion)
        self.core.callback(name="onCreateVersionDlgOpen", args=[self, self.newItem])
        self.newItem.show()

    @err_catcher(name=__name__)
    def createVersion(self) -> None:
        """Create a new version folder from the dialog.
        
        Creates the version directory structure and updates the version list.
        """
        self.activateWindow()
        versionName = self.core.versionFormat % self.newItem.sp_version.value()
        curEntity = self.getCurrentEntity()
        identifier = self.getCurrentIdentifier()
        location = self.newItem.cb_location.currentText()
        if self.core.mediaProducts.getLinkedToTasks():
            curEntity["department"] = identifier.get("department", "unknown")
            curEntity["task"] = identifier.get("task", "unknown")

        self.core.mediaProducts.createVersion(
            entity=curEntity,
            identifier=identifier["identifier"],
            identifierType=identifier["mediaType"],
            version=versionName,
            location=location,
        )
        self.updateVersions()
        if versionName is not None:
            matches = self.lw_version.findItems(
                versionName, Qt.MatchFlag(Qt.MatchExactly & Qt.MatchCaseSensitive)
            )
            if matches:
                self.lw_version.setCurrentItem(matches[0])

    @err_catcher(name=__name__)
    def groupIdentifiersDlg(self) -> None:
        """Show dialog to group selected identifiers into a folder."""
        identifiers = self.getCurrentIdentifier(allowMultiple=True)
        if not identifiers:
            self.core.popup("Select at least one identifier to group.")
            return

        groups = [self.core.mediaProducts.getGroupFromIdentifier(identifier) for identifier in identifiers]
        if len(list(set(groups))) == 1:
            startText = groups[0]
        else:
            startText = ""

        self.newItem = PrismWidgets.CreateItem(
            core=self.core, showType=False, mode="identifier", startText=startText, valueRequired=False, allowChars="/"
        )
        self.newItem.setModal(True)
        self.core.parentWindow(self.newItem)
        self.newItem.e_item.setFocus()
        self.newItem.setWindowTitle("Group selected identifiers")
        self.newItem.l_item.setText("Group Name:")
        self.newItem.buttonBox.buttons()[0].setText("Group")
        self.newItem.accepted.connect(lambda: self.groupIdentifiers(self.newItem, identifiers))
        self.newItem.chb_projectWide = QCheckBox("Project-Wide")
        self.newItem.chb_projectWide.setToolTip("Creates this group for all identifiers with the same names for all assets and shots in the current project.")
        # self.newItem.w_options.layout().addWidget(self.newItem.chb_projectWide)
        self.newItem.show()

    @err_catcher(name=__name__)
    def groupIdentifiers(self, dlg: Any, identifiers: List[Dict[str, Any]]) -> None:
        """Apply group to selected identifiers.
        
        Args:
            dlg: Dialog widget containing group name
            identifiers: List of identifier dictionaries to group
        """
        group = dlg.e_item.text()
        projectWide = dlg.chb_projectWide.isChecked()
        self.core.mediaProducts.setIdentifiersGroup(identifiers, group=group, projectWide=projectWide)
        self.updateTasks(restoreSelection=True)

    @err_catcher(name=__name__)
    def ungroupIdentifiers(self, group: str) -> None:
        """Remove identifiers from a group.
        
        Args:
            group: Group path to remove identifiers from
        """
        identifiers = []
        mediaTasks = self.getMediaTasks()
        for idfType in mediaTasks:
            for identifier in mediaTasks[idfType]:
                if identifier["displayName"] not in [idf["displayName"] for idf in identifiers]:
                    igroup = self.core.mediaProducts.getGroupFromIdentifier(identifier)
                    if igroup == group:
                        identifiers.append(identifier)

        if identifiers:
            self.core.mediaProducts.setIdentifiersGroup(identifiers, group=None)
            self.updateTasks(restoreSelection=True)

    @err_catcher(name=__name__)
    def setMaster(self, context: Dict[str, Any]) -> None:
        """Set version as the master version.
        
        Args:
            context: Version context dictionary
        """
        self.core.mediaProducts.updateMasterVersion(context=context, isFilepath=False)
        self.updateVersions()
        QPixmapCache.clear()

    @err_catcher(name=__name__)
    def addMaster(self, context: Dict[str, Any]) -> None:
        """Add version to master version.
        
        Args:
            context: Version context dictionary
        """
        self.core.mediaProducts.addToMasterVersion(context=context, isFilepath=False)
        self.updateVersions()
        QPixmapCache.clear()

    @err_catcher(name=__name__)
    def taskDragEnterEvent(self, e: Any) -> None:
        """Handle drag enter event for task tree widget.
        
        Args:
            e: Drag event
        """
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def taskDragMoveEvent(self, e: Any) -> None:
        """Handle drag move event over task tree widget.
        
        Args:
            e: Drag move event
        """
        if e.mimeData().hasUrls():
            e.accept()
            self.tw_identifier.setStyleSheet(
                "QWidget#tw_identifier { border-style: dashed; border-color: rgb(100, 200, 100);  border-width: 2px; }"
            )
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def taskDragLeaveEvent(self, e: Any) -> None:
        """Handle drag leave event from task tree widget.
        
        Args:
            e: Drag leave event
        """
        self.tw_identifier.setStyleSheet("")

    @err_catcher(name=__name__)
    def taskDropEvent(self, e: Any) -> None:
        """Handle drop event for task tree widget.
        
        Allows dropping media files into the task list for import.
        
        Args:
            e: Drop event
        """
        if e.mimeData().hasUrls():
            self.tw_identifier.setStyleSheet("")
            e.setDropAction(Qt.LinkAction)
            e.accept()

            if not self.getCurrentEntity():
                self.core.popup("Select an asset or a shot to ingest media.")
                return

            fname = [
                os.path.normpath(str(url.toLocalFile())) for url in e.mimeData().urls()
            ]
            self.ingestMediaDlg(filepath="\n".join(sorted(fname)))
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def versionDragEnterEvent(self, e: Any) -> None:
        """Handle drag enter event for version list widget.
        
        Args:
            e: Drag enter event
        """
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def versionDragMoveEvent(self, e: Any) -> None:
        """Handle drag move event over version list widget.
        
        Args:
            e: Drag move event
        """
        if e.mimeData().hasUrls():
            e.accept()
            self.lw_version.setStyleSheet(
                "QWidget#lw_version { border-style: dashed; border-color: rgb(100, 200, 100);  border-width: 2px; }"
            )
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def versionDragLeaveEvent(self, e: Any) -> None:
        """Handle drag leave event from version list widget.
        
        Args:
            e: Drag leave event
        """
        self.lw_version.setStyleSheet("")

    @err_catcher(name=__name__)
    def versionDropEvent(self, e: Any) -> None:
        """Handle drop event for version list widget.
        
        Allows dropping media files into the version list for import.
        
        Args:
            e: Drop event
        """
        if e.mimeData().hasUrls():
            self.lw_version.setStyleSheet("")
            e.setDropAction(Qt.LinkAction)
            e.accept()

            if not self.getCurrentEntity():
                self.core.popup("Select an asset or a shot to ingest media.")
                return

            fname = [
                os.path.normpath(str(url.toLocalFile())) for url in e.mimeData().urls()
            ]
            self.ingestMediaDlg(filepath="\n".join(sorted(fname)))
            if hasattr(self, "ep") and self.ep.isVisible():
                self.ep.sp_version.setFocus()

        else:
            e.ignore()

    @err_catcher(name=__name__)
    def ingestMediaToSelection(self, entity: Dict[str, Any], files: List[str]) -> None:
        """Ingest media files to the selected entity and identifier.
        
        Args:
            entity: Target entity dictionary
            files: List of file paths to ingest
        """
        identifier = self.getCurrentIdentifier()
        version = self.getCurrentVersion()
        aov = self.getCurrentAOV()

        if not identifier:
            self.ingestMediaDlg(filepath="\n".join(files))
            return

        if not version:
            self.ingestMediaDlg(filepath="\n".join(files))
            self.ep.sp_version.setFocus()
            return

        if aov:
            aovLabel = aov["aov"]
        else:
            aovLabel = ""
            if identifier["mediaType"] == "3drenders":
                self.ingestMediaDlg(filepath="\n".join(files))
                self.ep.e_aov.setFocus()
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
    def ingestMediaDlg(self, filepath: str = "") -> None:
        """Show dialog to ingest external media files.
        
        Args:
            filepath: Initial file path (optional)
        """
        entity = self.getCurrentEntity()
        if entity.get("type") not in ["asset", "shot"]:
            self.core.popup("Invalid entity is selected. Select an asset or a shot and try again.")
            return

        location = None
        self.ep = ProjectWidgets.IngestMediaDlg(core=self.core, startText=filepath, entity=entity, parent=self)
        idf = self.getCurrentIdentifier()
        if idf:
            location = self.core.mediaProducts.getLocationFromPath(idf["path"])
            self.ep.e_identifier.setText(idf["identifier"])
            if idf.get("mediaType"):
                text = ""
                if idf.get("mediaType") == "3drenders":
                    text = "3D"
                elif idf.get("mediaType") == "2drenders":
                    text = "2D"
                elif idf.get("mediaType") == "playblasts":
                    text = "Playblast"
                elif idf.get("mediaType") == "externalMedia":
                    text = "External"

                if text:
                    self.ep.cb_identifierType.setCurrentText(text)

            version = self.core.mediaProducts.getLatestVersionFromIdentifier(idf, includeMaster=False)
            if version:
                location = self.core.mediaProducts.getLocationFromPath(version["path"])
                intVersion = self.core.products.getIntVersionFromVersionName(version["version"])
                if intVersion is not None:
                    self.ep.sp_version.setValue(intVersion + 1)

        if location:
            self.ep.cb_location.setCurrentText(location)

        self.ep.e_identifier.setFocus()
        self.activateWindow()
        self.ep.accepted.connect(self.ingestMedia)
        self.ep.show()

    @err_catcher(name=__name__)
    def ingestMedia(self, filepath: str = "") -> None:
        """Import media files into the project as external media.
        
        Args:
            filepath: Path to media file or directory
        """
        entity = self.ep.entity
        if entity.get("type") not in ["asset", "shot"]:
            self.core.popup("Invalid entity is selected. Select an asset or a shot and try again.")
            return

        identifier = self.ep.e_identifier.text()
        mediaType = self.ep.cb_identifierType.currentData()
        versionName = self.core.versionFormat % self.ep.sp_version.value()
        aov = self.ep.e_aov.text()
        targetPath = self.ep.l_mediaPath.text()
        files = targetPath.split("\n")
        entity = entity.copy()
        location = self.ep.cb_location.currentText()
        if self.core.mediaProducts.getLinkedToTasks():
            entity["department"] = self.ep.e_department.text()
            entity["task"] = self.ep.e_task.text()

        if mediaType == "externalMedia":
            if self.ep.rb_copy.isChecked():
                action = "copy"
            elif self.ep.rb_move.isChecked():
                action = "move"
            elif self.ep.rb_link.isChecked():
                action = "link"

            self.core.mediaProducts.createExternalMedia(
                os.pathsep.join(files), entity, identifier, versionName, action=action, location=location
            )
        else:
            rename = self.ep.chb_rename.isChecked()
            self.core.mediaProducts.ingestMedia(files, entity, identifier, versionName, aov, mediaType=mediaType, location=location, rename=rename)

        self.updateTasks()
        displayName = self.core.mediaProducts.getDisplayNameForIdentifier(identifier, mediaType)
        curData = [entity, displayName, versionName, ""]
        self.showRender(*curData)

    @err_catcher(name=__name__)
    def newExternalVersion(self) -> None:
        """Create a new external media version by selecting files."""
        entity = self.getCurrentEntity()
        identifier = self.getCurrentIdentifier()
        version = self.core.mediaProducts.getLatestVersionFromIdentifier(identifier)
        if version:
            startPath = self.core.mediaProducts.getExternalPathFromVersion(version)
            intVersion = self.core.products.getIntVersionFromVersionName(version["version"])
        else:
            startPath = None
            intVersion = self.core.lowestVersion

        self.ep = ProjectWidgets.IngestMediaDlg(core=self.core, entity=entity, parent=self)
        self.ep.e_identifier.setText(identifier["identifier"])
        if startPath:
            self.ep.setMediaPaths(startPath)

        self.ep.cb_identifierType.setCurrentText("External")
        self.ep.sp_version.setValue(intVersion)
        self.ep.enableOk()
        self.ep.setWindowTitle("Create new version")
        self.ep.sp_version.setFocus()
        self.activateWindow()
        self.ep.accepted.connect(self.ingestMedia)
        self.ep.show()

    @err_catcher(name=__name__)
    def getCurRenders(self) -> List[Dict[str, Any]]:
        """Get all render contexts from current selection.
        
        Returns:
            List of render context dictionaries with file paths
        """
        renders = []
        sTasks = self.tw_identifier.selectedItems()
        sVersions = self.lw_version.selectedItems()

        if len(sTasks) > 1:
            for identifierItem in sTasks:
                identifier = identifierItem.data(0, Qt.UserRole)
                if not identifier:
                    continue

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
                            if aov["aov"].lower() in ["beauty", "rgb", "rgba"]:
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
                        if aov["aov"].lower() in ["beauty", "rgb", "rgba"]:
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
    def triggerAutoplay(self, checked: bool = False) -> None:
        """Trigger autoplay in the media player.
        
        Args:
            checked: Whether autoplay should be enabled
        """
        self.w_preview.mediaPlayer.triggerAutoplay(checked)


class MediaVersionPlayer(QWidget):
    """Widget for displaying media versions with AOV/layer/channel selection.
    
    Manages the dropdown comboboxes for selecting AOVs (render passes), sources,
    and file layers, and contains the MediaPlayer widget for preview.
    
    Attributes:
        origin: Parent MediaBrowser instance
        core: Prism core instance
        l_layer: Label for AOV dropdown
        cb_layer: Combo box for AOV selection
        l_source: Label for source dropdown
        cb_source: Combo box for source selection
        l_filelayer: Label for file layer dropdown
        cb_filelayer: Combo box for file layer selection
        mediaPlayer: MediaPlayer instance for preview
    """
    
    def __init__(self, origin: Any) -> None:
        """Initialize MediaVersionPlayer.
        
        Args:
            origin: Parent MediaBrowser instance
        """
        super(MediaVersionPlayer, self).__init__()
        self.origin = origin
        self.core = self.origin.core
        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Setup the UI with AOV, source, and file layer dropdowns and media player."""
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
        self.cb_source.setContextMenuPolicy(Qt.CustomContextMenu)
        self.cb_source.customContextMenuRequested.connect(self.rclSource)
        self.cb_filelayer.currentIndexChanged.connect(self.filelayerChanged)

    @err_catcher(name=__name__)
    def getMediaPlayer(self) -> Any:
        """Create and return the media player instance.
        
        Returns:
            MediaPlayer instance
        """
        return MediaPlayer(self)

    @err_catcher(name=__name__)
    def getCurrentAOV(self) -> Optional[Dict[str, Any]]:
        """Get currently selected AOV/render pass.
        
        Returns:
            AOV dictionary with 'aov' and 'path' keys, or None
        """
        data = self.cb_layer.currentData(Qt.UserRole)
        return data

    @err_catcher(name=__name__)
    def getCurrentSource(self) -> Optional[Dict[str, Any]]:
        """Get currently selected source.
        
        Returns:
            Source dictionary, or None
        """
        data = self.cb_source.currentData(Qt.UserRole)
        return data

    @err_catcher(name=__name__)
    def getCurrentFilelayer(self) -> Optional[Dict[str, Any]]:
        """Get currently selected file layer/channel.
        
        Returns:
            File layer dictionary, or None
        """
        data = self.cb_filelayer.currentData(Qt.UserRole)
        return data

    @err_catcher(name=__name__)
    def layerChanged(self, layer: Optional[Any] = None) -> None:
        """Handle AOV/layer selection change.
        
        Args:
            layer: Selected layer (unused, kept for signal compatibility)
        """
        self.updateSources(restoreSelection=True)

    @err_catcher(name=__name__)
    def sourceChanged(self, layer: Optional[Any] = None) -> None:
        """Handle source selection change.
        
        Args:
            layer: Selected source (unused, kept for signal compatibility)
        """
        self.updateFilelayers(restoreSelection=True)

    @err_catcher(name=__name__)
    def filelayerChanged(self, layer: Optional[Any] = None) -> None:
        """Handle file layer/channel selection change.
        
        Args:
            layer: Selected file layer (unused, kept for signal compatibility)
        """
        self.mediaPlayer.updatePreview()

    @err_catcher(name=__name__)
    def getCurrentVersions(self) -> List[Dict[str, Any]]:
        """Get currently selected versions from parent MediaBrowser.
        
        Returns:
            List of version dictionaries
        """
        return self.origin.getCurrentVersions()

    @err_catcher(name=__name__)
    def updateLayers(self, restoreSelection: bool = False) -> None:
        """Update AOV/layer dropdown with available layers from current version.
        
        Args:
            restoreSelection: If True, attempt to restore previously selected layer
        """
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
            for idx in range(self.cb_layer.count()):
                aovPass = self.cb_layer.itemText(idx).lower()
                if aovPass == "beauty":
                    self.cb_layer.setCurrentIndex(idx)
                    break

            else:
                for idx in range(self.cb_layer.count()):
                    aovPass = self.cb_layer.itemText(idx).lower()
                    if aovPass in ["rgb", "rgba"]:
                        self.cb_layer.setCurrentIndex(idx)
                        break

                else:
                    self.cb_layer.setCurrentIndex(0)

        if not wasBlocked:
            self.cb_layer.blockSignals(False)
            self.updateSources(restoreSelection=True)

    @err_catcher(name=__name__)
    def updateSources(self, restoreSelection: bool = False) -> None:
        """Update source dropdown with available sources from current AOV.
        
        Args:
            restoreSelection: If True, attempt to restore previously selected source
        """
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
    def updateFilelayers(self, restoreSelection: bool = False, threaded: bool = True, layers: Optional[List[str]] = None) -> None:
        """Update file layer dropdown with available channels from current source.
        
        Reads image file layers (e.g., RGBA, depth) from OpenImageIO, optionally in a thread.
        
        Args:
            restoreSelection: If True, attempt to restore previously selected layer
            threaded: If True, read layers in background thread
            layers: Pre-loaded layer list (skips reading if provided)
        """
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
    def getLayersFromFileThreaded(self, filepath: str, thread: Any, restoreSelection: bool) -> None:
        """Read image file layers in a worker thread.
        
        Args:
            filepath: Path to the image file
            thread: Worker thread instance
            restoreSelection: Whether to restore layer selection after loading
        """
        if thread.isInterruptionRequested():
            return

        layers = self.core.media.getLayersFromFile(filepath)
        layerData = {"file": filepath, "layers": layers}
        data = {"function": "updateFilelayers", "args": [], "kwargs": {"restoreSelection": restoreSelection, "threaded": False, "layers": layerData}}
        thread.dataSent.emit(data)

    @err_catcher(name=__name__)
    def onWorkerDataSent(self, data: Dict[str, Any]) -> None:
        """Handle data sent from worker thread.
        
        Args:
            data: Dictionary with 'function', 'args', and 'kwargs' keys
        """
        getattr(self, data["function"])(*data["args"], **data["kwargs"])

    @err_catcher(name=__name__)
    def onWorkerThreadFinished(self) -> None:
        """Handle worker thread completion.
        
        Starts the next queued thread if one is waiting.
        """
        if getattr(self, "nextMediaThread", None):
            self.curMediaThread = self.nextMediaThread
            self.nextMediaThread = None
            self.curMediaThread.start()
        else:
            self.curMediaThread = None

    @err_catcher(name=__name__)
    def navigate(self, aov: Optional[str] = None, source: Optional[str] = None, 
                 filelayer: Optional[str] = None, restoreSelection: bool = False, 
                 updateLayers: bool = True) -> Optional[bool]:
        """Navigate to specific AOV, source, and file layer selection.
        
        Args:
            aov: AOV/pass name to select
            source: Source name to select
            filelayer: File layer/channel name to select
            restoreSelection: Whether to restore previous selection if parameter is None
            updateLayers: Whether to update layer list before navigating
            
        Returns:
            True if selection changed, False/None otherwise
        """
        prevLayer = self.getCurrentAOV()
        self.cb_layer.blockSignals(True)
        if updateLayers:
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
    def rclSource(self, pos: Any) -> None:
        """Show context menu for source dropdown.

        Args:
            pos: Mouse position for the context menu
        """
        if self.cb_source.count() < 2:
            return

        cpos = QCursor.pos()
        rcmenu = QMenu(self)

        act_compare = QAction("Compare...", self)
        act_compare.triggered.connect(self.compareAllSources)
        rcmenu.addAction(act_compare)

        rcmenu.exec_(cpos)

    @err_catcher(name=__name__)
    def compareAllSources(self) -> None:
        """Collect all source paths from cb_source and pass them to the media player's compare function."""
        paths = []
        for idx in range(self.cb_source.count()):
            source = self.cb_source.itemData(idx, Qt.UserRole)
            if not source:
                continue
            mediaFiles = self.core.mediaProducts.getFilesFromContext(source)
            validFiles = self.core.media.filterValidMediaFiles(mediaFiles)
            if validFiles:
                paths.append(validFiles[0])

        if paths:
            self.mediaPlayer.compare(paths=paths)

    @err_catcher(name=__name__)
    def rclLayer(self, pos: Any) -> None:
        """Show context menu for AOV layer dropdown.
        
        Args:
            pos: Mouse position for the context menu
        """
        cpos = QCursor.pos()
        if not hasattr(self.origin, "getCurrentIdentifier"):
            return

        identifier = self.origin.getCurrentIdentifier()
        if not identifier or identifier["mediaType"] != "3drenders":
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

            copAct = self.core.getCopyAction(path, parent=self)
            rcmenu.addAction(copAct)

        if rcmenu.isEmpty():
            return False

        rcmenu.exec_(cpos)

    @err_catcher(name=__name__)
    def createAovDlg(self) -> None:
        """Show dialog to create a new AOV/render pass folder."""
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
    def createAov(self) -> None:
        """Create a new AOV/render pass folder from the dialog."""
        self.activateWindow()
        itemName = self.newItem.e_item.text()
        curEntity = self.origin.getCurrentEntity()
        identifier = self.origin.getCurrentIdentifier()
        identifierName = identifier.get("identifier")
        version = self.origin.getCurrentVersion().get("version")
        if self.core.mediaProducts.getLinkedToTasks():
            curEntity["department"] = identifier.get("department", "unknown")
            curEntity["task"] = identifier.get("task", "unknown")

        self.core.mediaProducts.createAov(entity=curEntity, identifier=identifierName, version=version, aov=itemName)
        self.updateLayers()
        if itemName is not None:
            idx = self.cb_layer.findText(itemName)
            if idx != -1:
                self.cb_layer.setCurrentIndex(idx)


class MediaPlayer(QWidget):
    """Media preview player widget with timeline controls and image display.
    
    Handles preview playback of image sequences and video files, including:
    - Frame-by-frame navigation
    - Timeline scrubbing
    - Playback controls (play/pause/first/last)
    - Thumbnail caching
    - Drag-and-drop for external apps
    - Multi-media comparison
    - External media player integration (RV, DJV, etc.)
    
    Attributes:
        mediaVersionPlayer: Parent MediaVersionPlayer instance
        origin: Root MediaBrowser instance
        core: Prism core instance
        externalMediaPlayers: Available external media player apps
        renderResX: Thumbnail width in pixels
        renderResY: Thumbnail height in pixels
        videoReaders: Cache of video reader instances by filepath
        currentMediaPreview: Currently loaded media path
        mediaThreads: Active background worker threads for loading media
        timeline: QTimeLine for playback animation
        tlPaused: Whether timeline is paused
        prvIsSequence: Whether current preview is an image sequence
        seq: List of frame paths for current sequence
        l_preview: QLabel for displaying preview images
        sl_preview: QSlider for timeline scrubbing
        sp_current: QSpinBox for current frame number
        state: Preview state ('enabled' or 'disabled')
    """
    
    def __init__(self, origin: Any) -> None:
        """Initialize MediaPlayer.
        
        Args:
            origin: Parent MediaVersionPlayer instance
        """
        super(MediaPlayer, self).__init__()
        self.mediaVersionPlayer = origin
        self.origin = self.mediaVersionPlayer.origin
        self.core = self.origin.core

        self.externalMediaPlayers = None
        self.renderResX = 300
        self.renderResY = 169
        self.videoReaders = {}
        self.currentMediaPreview = None
        self.mediaThreads = []
        self.timeline = None
        self.tlPaused = False
        self.prvIsSequence = False
        self.seq = []
        self.pduration = 0
        self.pwidth = 0
        self.pheight = 0
        self.pstart = 0
        self.pend = 0
        self.openMediaPlayer = False
        self.thumbnailInfoText = ""
        self.isLoadingImage = False
        self.emptypmap = self.createPMap(self.renderResX, self.renderResY)
        self.previewTooltip = "Left mouse drag to drag media files.\nCtrl+Left mouse drag to drag media folder."
        self.previewEnabled = True
        self.state = "enabled"
        self.core.registerCallback("onUserSettingsSave", self.onUserSettingsSave)
        self.updateExternalMediaPlayer()
        self.setupUi()
        self.connectEvents()

    @err_catcher(name=__name__)
    def sizeHint(self) -> Any:
        """Provide size hint for layout.
        
        Returns:
            QSize of (400, 100)
        """
        return QSize(400, 100)

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Create and configure the media player UI with preview label, timeline, and controls."""
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
        self.l_thumbnailInfo = QLabel(self)
        self.l_thumbnailInfo.setAlignment(Qt.AlignCenter)
        self.l_thumbnailInfo.setHidden(True)
        self.l_thumbnailInfo.setStyleSheet("color: rgb(200, 100, 100);")
        self.lo_main.addWidget(self.l_preview)
        self.lo_main.addWidget(self.l_thumbnailInfo)

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
    def connectEvents(self) -> None:
        """Connect UI signals to their handler methods."""
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
    def onUserSettingsSave(self, origin: Any) -> None:
        """Handle user settings save event.
        
        Args:
            origin: Origin widget that triggered save
        """
        self.updateExternalMediaPlayer()

    @err_catcher(name=__name__)
    def setPreviewEnabled(self, state: bool) -> None:
        """Enable or disable the media preview display.
        
        Args:
            state: True to show preview, False to hide it
        """
        self.previewEnabled = state
        self.l_preview.setVisible(state)
        self.w_timeslider.setVisible(state)
        self.w_playerCtrls.setVisible(state)

    @err_catcher(name=__name__)
    def onFirstClicked(self) -> None:
        """Jump to first frame of the sequence."""
        self.timeline.setCurrentTime(0)

    @err_catcher(name=__name__)
    def onPrevClicked(self) -> None:
        """Jump to previous frame, wrapping to end if at beginning."""
        time = self.timeline.currentTime() - self.timeline.updateInterval()
        if time < 0:
            time = self.timeline.duration() - self.timeline.updateInterval()

        self.timeline.setCurrentTime(time)

    @err_catcher(name=__name__)
    def onPlayClicked(self) -> None:
        """Toggle playback of the sequence."""
        if not self.seq:
            return

        self.setTimelinePaused(self.timeline.state() == QTimeLine.Running)

    @err_catcher(name=__name__)
    def onNextClicked(self) -> None:
        """Jump to next frame."""
        time = self.timeline.currentTime() + self.timeline.updateInterval()
        time = min(self.timeline.duration(), time)
        self.timeline.setCurrentTime(time)

    @err_catcher(name=__name__)
    def onLastClicked(self) -> None:
        """Jump to last frame of the sequence."""
        self.timeline.setCurrentTime(self.timeline.updateInterval() * (self.pduration - 1))

    @err_catcher(name=__name__)
    def sliderChanged(self, val: int) -> None:
        """Handle timeline slider value change.
        
        Args:
            val: New slider value
        """
        if not self.seq:
            return

        time = int(val / self.sl_preview.maximum() * self.timeline.duration())
        if time == self.timeline.duration():
            time -= 1

        self.timeline.blockSignals(True)
        self.timeline.setCurrentTime(time)
        self.timeline.blockSignals(False)
        self.changeImage_threaded(self.getCurrentFrame())

    @err_catcher(name=__name__)
    def onCurrentChanged(self, value: int) -> None:
        """Handle current frame spinbox value change.
        
        Args:
            value: New frame number
        """
        if not self.timeline:
            return

        time = (value - self.pstart) * self.timeline.updateInterval()
        self.timeline.setCurrentTime(time)

    @err_catcher(name=__name__)
    def getAutoplay(self) -> bool:
        """Get autoplay preference from project browser.
        
        Returns:
            True if autoplay is enabled, False otherwise
        """
        if not getattr(self.origin, "projectBrowser", None):
            return

        return self.origin.projectBrowser.actionAutoplay.isChecked()

    @err_catcher(name=__name__)
    def getSelectedContexts(self) -> List[Dict[str, Any]]:
        """Get selected contexts from parent MediaBrowser.
        
        Returns:
            List of context dictionaries
        """
        return self.origin.getSelectedContexts()

    @err_catcher(name=__name__)
    def getFilesFromContext(self, context: Dict[str, Any]) -> List[str]:
        """Get media files from a context dictionary.
        
        Args:
            context: Context dictionary with path information
        
        Returns:
            List of file paths
        """
        return self.core.mediaProducts.getFilesFromContext(context)

    @err_catcher(name=__name__)
    def updatePreview(self, regenerateThumb: bool = False) -> Optional[bool]:
        """Update the media preview with currently selected media.
        
        Loads sequence/video into player, sets up timeline, and displays first frame.
        
        Args:
            regenerateThumb: If True, regenerate cached thumbnails
            
        Returns:
            True if preview was updated successfully
        """
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
                validFiles = self.getMediaFilesFromContext(contexts[0])
                if validFiles:
                    baseFile = self.getBaseFile(validFiles)
                    baseName, extension = os.path.splitext(baseFile)
                    extension = extension.lower()
                    seqFiles = self.core.media.detectSequence(validFiles, baseFile=baseFile)

                    if (
                        len(seqFiles) > 1
                        and extension not in self.core.media.videoFormats
                    ):
                        self.seq = self.getSeqFiles(seqFiles)
                        self.prvIsSequence = True
                        (
                            self.pstart,
                            self.pend,
                        ) = self.core.media.getFrameRangeFromSequence(self.seq, baseFile=baseFile)
                    else:
                        self.prvIsSequence = False
                        self.seq = validFiles

                    self.pduration = len(self.seq)
                    imgPath = baseFile
                    if (
                        self.pduration == 1
                        and os.path.splitext(imgPath)[1].lower() in self.core.media.videoFormats
                    ):
                        self.vidPrw = "loading"
                        self.updatePrvInfo_threaded(
                            imgPath,
                            vidReader="loading",
                            frame=prevFrame,
                        )
                    else:
                        self.updatePrvInfo_threaded(imgPath, frame=prevFrame)

                    if self.tlPaused:
                        self.changeImage_threaded(regenerateThumb=regenerateThumb)
                    elif self.pduration < 3:
                        self.changeImage_threaded(regenerateThumb=regenerateThumb)

                    return True

            self.updatePrvInfo_threaded()

        if not self.core.isObjectValid(self.l_preview):
            return

        pmap = self.core.media.scalePixmap(self.emptypmap, self.getThumbnailWidth(), self.getThumbnailHeight())
        self.currentMediaPreview = pmap
        self.l_preview.setPixmap(pmap)
        self.sl_preview.setEnabled(False)
        self.l_start.setText("")
        self.l_end.setText("")
        if self.thumbnailInfoText:
            self.thumbnailInfoText = ""
            self.l_thumbnailInfo.setText("")
            self.l_thumbnailInfo.setHidden(True)

        self.w_playerCtrls.setEnabled(False)
        self.sp_current.setEnabled(False)
        if hasattr(self, "loadingGif") and self.loadingGif.state() == QMovie.Running:
            self.l_loading.setVisible(False)
            self.loadingGif.stop()

    @err_catcher(name=__name__)
    def getSeqFiles(self, seqFiles: List[str]) -> List[str]:
        """Get sorted sequence files.
        
        Args:
            seqFiles: List of sequence file paths
            
        Returns:
            Sorted list of file paths
        """
        return seqFiles

    @err_catcher(name=__name__)
    def getBaseFile(self, files: List[str]) -> str:
        """Get the base/representative file from a list.
        
        Args:
            files: List of file paths
            
        Returns:
            Base file path (first in list)
        """
        baseFile = files[0]
        return baseFile

    @err_catcher(name=__name__)
    def getMediaFilesFromContext(self, context: Dict[str, Any]) -> List[str]:
        """Get valid media files from a context, sorted with cryptomatte last.
        
        Args:
            context: Context dictionary with path information
            
        Returns:
            Sorted list of valid media file paths
        """
        mediaFiles = self.getFilesFromContext(context)
        validFiles = self.core.media.filterValidMediaFiles(mediaFiles)
        if validFiles:
            validFiles = sorted(validFiles, key=lambda x: x if "cryptomatte" not in os.path.basename(x) else "zzz" + x)

        return validFiles

    @err_catcher(name=__name__)
    def updatePrvInfo_threaded(self, prvFile: str = "", vidReader: Optional[Any] = None, 
                               seq: Optional[List[str]] = None, frame: Optional[int] = None) -> None:
        """Update preview info (resolution, duration) in a worker thread.
        
        Args:
            prvFile: Path to the preview file
            vidReader: Video reader instance
            seq: Sequence file list
            frame: Frame number
        """
        self.l_info.setText("\nLoading...\n")
        self.l_info.setToolTip("")
        self.l_preview.setToolTip("")

        thread = self.core.worker(self.core)
        thread.function = lambda x=list(self.seq): self.getMediainfo(
            thread, prvFile, vidReader, seq, frame
        )
        thread.errored.connect(self.core.writeErrorLog)
        thread.finished.connect(self.onMediainfoThreadFinished)
        thread.warningSent.connect(self.core.popup)
        thread.dataSent.connect(self.onGetMediainfoDataSent)
        if not getattr(self, "curMediainfoThread", None):
            self.curMediainfoThread = thread
            thread.start()
        else:
            self.nextMediainfoThread = thread

    @err_catcher(name=__name__)
    def onGetMediainfoDataSent(self, data: Dict[str, Any]) -> None:
        """Handle media info data sent from worker thread.
        
        Args:
            data: Dictionary with 'function', 'args', and 'kwargs' keys
        """
        getattr(self, data["function"])(*data["args"], **data["kwargs"])

    @err_catcher(name=__name__)
    def onMediainfoThreadFinished(self) -> None:
        """Handle media info worker thread completion.
        
        Starts the next queued thread if one is waiting.
        """
        if getattr(self, "nextMediainfoThread", None):
            self.curMediainfoThread = self.nextMediainfoThread
            self.nextMediainfoThread = None
            self.curMediainfoThread.start()
        else:
            self.curMediainfoThread = None

    @err_catcher(name=__name__)
    def getMediainfo(self, thread: Any, prvFile: str, vidReader: Optional[Any], 
                     seq: Optional[List[str]], frame: Optional[int]) -> Optional[Dict[str, Any]]:
        """Get media information like resolution and duration.
        
        Args:
            thread: Worker thread instance
            prvFile: Path to the preview file
            vidReader: Video reader instance
            seq: Sequence file list
            frame: Frame number
            
        Returns:
            Dictionary with 'exists', 'width', 'height', 'duration' keys
        """
        info = {
            "exists": os.path.exists(prvFile)
        }
        if info["exists"]:
            if self.state == "disabled" or os.getenv("PRISM_DISPLAY_MEDIA_RESOLUTION") == "0":
                width = "?"
                height = "?"
            else:
                if vidReader == "loading":
                    width = "loading..."
                    height = ""
                else:
                    resolution = self.core.media.getMediaResolution(prvFile, videoReader=vidReader)
                    width = resolution["width"]
                    height = resolution["height"]

            info["width"] = width
            info["height"] = height

        ext = os.path.splitext(prvFile)[1].lower()
        if ext in self.core.media.videoFormats:
            if len(self.seq) == 1:
                if self.core.isStr(vidReader) or self.state == "disabled":
                    duration = 1
                else:
                    duration = self.core.media.getVideoDuration(prvFile, videoReader=vidReader)
                    if not duration:
                        duration = 1

                info["duration"] = duration

        if thread:
            kwargs = {"vidReader": vidReader, "seq": seq, "frame": frame, "mediaInfo": info}
            data = {"function": "updatePrvInfo", "args": [prvFile], "kwargs": kwargs}
            thread.dataSent.emit(data)
        else:
            return info

    @err_catcher(name=__name__)
    def updatePrvInfo(self, prvFile: str = "", vidReader: Optional[Any] = None, 
                      seq: Optional[List[str]] = None, frame: Optional[int] = None, 
                      mediaInfo: Optional[Dict[str, Any]] = None) -> None:
        """Update preview info display with media details.
        
        Args:
            prvFile: Path to the preview file
            vidReader: Video reader instance
            seq: Sequence file list
            frame: Frame number
            mediaInfo: Pre-loaded media information dictionary
        """
        if seq is not None:
            if self.seq != seq:
                logger.debug("exit preview info update")
                return

        if not mediaInfo:
            mediaInfo = self.getMediainfo(None, prvFile, vidReader, seq, frame)

        if not mediaInfo["exists"]:
            self.l_info.setText("\nNo image found\n")
            self.l_info.setToolTip("")
            self.l_preview.setToolTip("")
            return

        self.pwidth = mediaInfo["width"]
        self.pheight = mediaInfo["height"]

        if "duration" in mediaInfo:
            self.pduration = mediaInfo["duration"]

        ext = os.path.splitext(prvFile)[1].lower()
        self.pformat = "*" + ext

        pdate = ""
        contexts = self.getSelectedContexts()
        if contexts and len(contexts) == 1:
            context = contexts[0]
            if "date" in context:
                pdate = context["date"]
                if isinstance(pdate, int):
                    pdate = self.core.getFormattedDate(pdate) if pdate else ""

        if not pdate:
            pdate = self.core.getFileModificationDate(prvFile)
        self.sl_preview.setEnabled(True)
        start, end = self.getStartEnd(ext)
        self.pstart = int(start)
        self.pend = int(end)

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

        self.l_start.setText(start)
        self.l_end.setText(end)
        self.sp_current.setMinimum(int(start))
        self.sp_current.setMaximum(int(end))
        self.w_playerCtrls.setEnabled(True)
        self.sp_current.setEnabled(True)

        frame = frame or int(start)
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
    def getStartEnd(self, ext: str) -> Tuple[str, str]:
        """Get start and end frame numbers for display.
        
        Args:
            ext: File extension
            
        Returns:
            Tuple of (start_frame_string, end_frame_string)
        """
        start = "1"
        end = "1"
        if self.prvIsSequence:
            start = str(self.pstart)
            end = str(self.pend)
        elif ext in self.core.media.videoFormats:
            if self.pwidth != "?":
                end = str(int(start) + self.pduration - 1)

        return start, end

    @err_catcher(name=__name__)
    def setInfoText(self, text: str) -> None:
        """Set and format the info label text with elision.
        
        Args:
            text: Text to display
        """
        metrics = QFontMetrics(self.l_info.font())
        lines = []
        for line in text.split("\n"):
            elidedText = metrics.elidedText(line, Qt.ElideRight, self.l_preview.width()-20)
            lines.append(elidedText)

        self.l_info.setText("\n".join(lines))

    @err_catcher(name=__name__)
    def createPMap(self, resx: int, resy: int) -> QPixmap:
        """Create an empty/fallback preview pixmap.
        
        Args:
            resx: Width in pixels
            resy: Height in pixels
            
        Returns:
            QPixmap with fallback image or transparent pixmap
        """
        fbFolder = self.core.projects.getFallbackFolder()
        if resx == 300:
            imgFile = os.path.join(fbFolder, "noFileBig.jpg")
        else:
            imgFile = os.path.join(fbFolder, "noFileSmall.jpg")

        pmap = self.core.media.getPixmapFromPath(imgFile)
        if not pmap:
            pmap = QPixmap()

        return pmap

    @err_catcher(name=__name__)
    def moveLoadingLabel(self) -> None:
        """Position the loading label in the center of the preview area."""
        geo = QRect()
        pos = self.l_preview.parent().mapToGlobal(self.l_preview.geometry().topLeft())
        pos = self.mapFromGlobal(pos)
        geo.setWidth(self.l_preview.width())
        geo.setHeight(self.l_preview.height())
        geo.moveTopLeft(pos)
        self.l_loading.setGeometry(geo)

    @err_catcher(name=__name__)
    def changeImage_threaded(self, frame: int = 0, regenerateThumb: bool = False) -> None:
        """Load and display an image/frame in a worker thread.
        
        Args:
            frame: Frame number to load
            regenerateThumb: If True, regenerate cached thumbnail
        """
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
    def onMediaThreadFinished(self) -> None:
        """Handle media loading worker thread completion.
        
        Starts the next queued thread if one is waiting.
        """
        if getattr(self, "nextMediaThread", None):
            self.curMediaThread = self.nextMediaThread
            self.nextMediaThread = None
            self.curMediaThread.start()
        else:
            self.curMediaThread = None
            self.l_loading.setVisible(False)
            self.loadingGif.stop()

    @err_catcher(name=__name__)
    def onChangeImgDataSent(self, data: Dict[str, Any]) -> None:
        """Handle image data sent from media loading worker thread.
        
        Args:
            data: Dictionary with 'function', 'args', and 'kwargs' keys
        """
        getattr(self, data["function"])(*data["args"], **data["kwargs"])

    @err_catcher(name=__name__)
    def getThumbnailWidth(self) -> int:
        """Get current preview label width.
        
        Returns:
            Width in pixels
        """
        return self.l_preview.width()

    @err_catcher(name=__name__)
    def getThumbnailHeight(self) -> int:
        """Get current preview label height.
        
        Returns:
            Height in pixels
        """
        return self.l_preview.height()

    @err_catcher(name=__name__)
    def getCurrentFrame(self) -> int:
        """Get current frame number from timeline.
        
        Returns:
            Current frame number
        """
        if not self.timeline:
            return 0

        return int(self.timeline.currentTime() / self.timeline.updateInterval())

    @err_catcher(name=__name__)
    def getCurrentFilepath(self, curFrame=None) -> Optional[str]:
        """Get current file path based on current frame.
        
        Returns:
            Current file path or None if not available
        """
        if curFrame is None:
            curFrame = self.getCurrentFrame()
            if not self.seq or curFrame >= len(self.seq):
                return None

        isVideo = os.path.splitext(self.seq[0])[1].lower() in self.core.media.videoFormats
        if len(self.seq) == 1 and isVideo or curFrame >= len(self.seq):
            fileName = self.seq[0]
        else:
            fileName = self.seq[curFrame] if curFrame < len(self.seq) else self.seq[-1]

        return fileName

    @err_catcher(name=__name__)
    def changeImg(self, frame: int = 0, seq: Optional[List[str]] = None, 
                  thread: Optional[Any] = None, regenerateThumb: bool = False) -> None:
        """Load and display an image/frame from the sequence.
        
        Args:
            frame: Frame number to load (0-based)
            seq: Sequence file list to check against current sequence
            thread: Worker thread instance
            regenerateThumb: If True, regenerate cached thumbnail
        """
        if seq is not None:
            if self.seq != seq:
                logger.debug("exit thread")
                return

        if thread and thread.isInterruptionRequested():
            return

        if self.thumbnailInfoText:
            self.thumbnailInfoText = ""
            self.l_thumbnailInfo.setText("")

        if not self.seq:
            return

        curFrame = self.getCurrentFrame()
        if curFrame is None:
            return

        pmsmall = QPixmap()
        fileName = self.getCurrentFilepath(curFrame)
        _, ext = os.path.splitext(fileName)
        ext = ext.lower()
        self.isLoadingImage = True
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
                elif ext in [".exr", ".dpx", ".hdr", ".psd"]:
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
                elif ext in [".pdf"]:
                    try:
                        pmsmall = self.core.media.getPixmapFromPdfPath(
                            fileName,
                            self.getThumbnailWidth(),
                            self.getThumbnailHeight(),
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
                                        logger.warning("failed to read video file: %s" % vidFile)

                                    self.videoReaders[fileName] = vidFile

                                if thread:
                                    data = {"function": "updatePrvInfo_threaded", "args": [fileName], "kwargs": {"vidReader": vidFile, "seq": seq}}
                                    thread.dataSent.emit(data)
                                else:
                                    self.updatePrvInfo_threaded(fileName, vidReader=vidFile, seq=seq)

                        pm = self.core.media.getPixmapFromVideoPath(
                            fileName,
                            videoReader=vidFile,
                            imgNum=imgNum,
                            regenerateThumb=regenerateThumb
                        )
                        pmsmall = self.core.media.scalePixmap(
                            pm, self.getThumbnailWidth(), self.getThumbnailHeight()
                        ) or QPixmap()
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

                if pmsmall:
                    QPixmapCache.insert(("Frame" + str(curFrame)), pmsmall)

        if not self.prvIsSequence and len(self.seq) > 1:
            if curFrame >= len(self.seq):
                return

            fileName = self.seq[curFrame]
            if thread:
                thread.dataSent.emit({"function": "updatePrvInfo_threaded", "args": [fileName], "kwargs": {"seq": seq}})
            else:
                self.updatePrvInfo_threaded(fileName, seq=seq)

        if thread:
            thread.dataSent.emit({"function": "completeChangeImg", "args": [pmsmall, curFrame, ext], "kwargs": {}})
        else:
            self.completeChangeImg(pmsmall, curFrame, ext)

    @err_catcher(name=__name__)
    def completeChangeImg(self, pmsmall: Optional[QPixmap], curFrame: int, ext: str) -> None:
        """Complete the image change operation by displaying the pixmap.
        
        Args:
            pmsmall: Scaled pixmap to display
            curFrame: Current frame number
            ext: File extension
        """
        pmsmall = pmsmall or QPixmap()
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

        if self.sp_current.value() != (self.pstart + curFrame):
            self.sp_current.blockSignals(True)
            self.sp_current.setValue((self.pstart + curFrame))
            self.sp_current.blockSignals(False)

        infoTxt = self.thumbnailInfoText
        self.l_thumbnailInfo.setHidden(bool(not infoTxt))
        self.l_thumbnailInfo.setToolTip(infoTxt or "")
        wrappedInfo = self.wrapTextForLabel(
            infoTxt,
            self.l_preview.width() - 20,
            self.l_thumbnailInfo,
        )
        if wrappedInfo != self.l_thumbnailInfo.text():
            self.l_thumbnailInfo.setText(wrappedInfo)

        self.isLoadingImage = True

    @err_catcher(name=__name__)
    def wrapTextForLabel(self, text: str, maxWidth: int, label: QLabel) -> str:
        """Wrap text into multiple lines based on pixel width for a label.

        Args:
            text: Source text to wrap
            maxWidth: Maximum width in pixels
            label: Label whose font metrics should be used

        Returns:
            Wrapped text suitable for display without growing panel width
        """
        if not text:
            return ""

        maxWidth = max(80, int(maxWidth))
        metrics = QFontMetrics(label.font())
        wrappedLines = []

        for rawLine in str(text).splitlines() or [""]:
            if not rawLine:
                wrappedLines.append("")
                continue

            line = rawLine
            start = 0
            while start < len(line):
                low = start + 1
                high = len(line)
                best = start + 1

                # Find the longest chunk that fits into maxWidth.
                while low <= high:
                    mid = (low + high) // 2
                    chunk = line[start:mid]
                    if metrics.horizontalAdvance(chunk) <= maxWidth:
                        best = mid
                        low = mid + 1
                    else:
                        high = mid - 1

                split = best
                if split < len(line):
                    for idx in range(best, start, -1):
                        if line[idx - 1] in " /\\_-.,;:":
                            split = idx
                            break

                segment = line[start:split].rstrip()
                if segment:
                    wrappedLines.append(segment)

                start = max(split, start + 1)
                while start < len(line) and line[start] == " ":
                    start += 1

        return "\n".join(wrappedLines)

    @err_catcher(name=__name__)
    def setTimelinePaused(self, state: bool) -> None:
        """Pause or resume timeline playback.
        
        Args:
            state: True to pause, False to resume
        """
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
    def previewClk(self, event: Any) -> None:
        """Handle mouse click on preview label.
        
        Left click toggles playback pause.
        
        Args:
            event: Mouse event
        """
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
    def previewDclk(self, event: Any) -> None:
        """Handle double-click on preview label.
        
        Left double-click opens external media player.
        
        Args:
            event: Mouse event
        """
        if self.seq != [] and event.button() == Qt.LeftButton:
            self.openMediaPlayer = True
            self.compare()

        self.l_preview.dclickEvent(event)

    @err_catcher(name=__name__)
    def rclPreview(self, pos: Any) -> None:
        """Show context menu for preview label.
        
        Args:
            pos: Menu position
        """
        menu = self.getMediaPreviewMenu()
        self.core.callback(
            name="mediaPlayerContextMenuRequested",
            args=[self, menu],
        )
        if not menu or menu.isEmpty():
            return

        menu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def getMediaPreviewMenu(self) -> QMenu:
        """Create and return context menu for media preview.
        
        Returns:
            QMenu with preview actions (play, convert, compare, etc.)
        """
        contexts = self.getCurRenders()
        if not contexts or not contexts[0].get("version"):
            return

        data = contexts[0]
        path = data["path"]

        if not path:
            return

        rcmenu = QMenu(self)

        if len(self.seq) > 0 and hasattr(self.core.appPlugin, "importImages"):
            impAct = QAction("Import images...", self)
            impAct.triggered.connect(lambda: self.core.appPlugin.importImages(mediaBrowser=self))
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

            if self.externalMediaPlayers is not None:
                for player in self.externalMediaPlayers:
                    pAct = QAction(player.get("name", ""), self)
                    pAct.triggered.connect(lambda x=None, name=player.get("name", ""): self.compare(name))
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
            settings["-c"] = "prores_ks"
            settings["-profile:v"] = 2
            settings["-pix_fmt"] = "yuv422p10le"
            settings["-vf"] = "scale=in_color_matrix=auto:out_color_matrix=bt709"
            settings["-color_primaries"] = "bt709"
            settings["-color_trc"] = "bt709"
            settings["-colorspace"] = "bt709"

            movAct = QAction("mov (prores 422)", self)
            movAct.triggered.connect(
                lambda x=None, s=settings: self.convertImgs(".mov", settings=s)
            )
            cvtMenu.addAction(movAct)
            rcmenu.addMenu(cvtMenu)

            settings = OrderedDict()
            settings["-c"] = "prores_ks"
            settings["-profile:v"] = 4
            settings["-pix_fmt"] = "yuva444p10le"
            settings["-vf"] = "scale=in_color_matrix=auto:out_color_matrix=bt709"
            settings["-color_primaries"] = "bt709"
            settings["-color_trc"] = "bt709"
            settings["-colorspace"] = "bt709"

            movAct = QAction("mov (prores 4444)", self)
            movAct.triggered.connect(
                lambda x=None, s=settings: self.convertImgs(".mov", settings=s)
            )
            cvtMenu.addAction(movAct)
            rcmenu.addMenu(cvtMenu)
        if (
            len(self.seq) == 1
            and os.path.splitext(self.seq[0])[1].lower()
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

        copAct = self.core.getCopyAction(path, parent=self)
        rcmenu.addAction(copAct)

        return rcmenu

    @err_catcher(name=__name__)
    def onDisabledTriggered(self) -> None:
        """Toggle between enabled/disabled preview state."""
        if self.state == "enabled":
            self.state = "disabled"
        else:
            self.state = "enabled"

        self.updatePreview()

    @err_catcher(name=__name__)
    def regenerateThumbnail(self) -> None:
        """Clear thumbnails and regenerate current preview."""
        self.clearCurrentThumbnails()
        self.updatePreview(regenerateThumb=True)

    @err_catcher(name=__name__)
    def clearCurrentThumbnails(self) -> None:
        """Clear cached thumbnails for current sequence."""
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
    def previewResizeEvent(self, event: Any) -> None:
        """Handle preview label resize event.
        
        Updates preview display to fit new size.
        
        Args:
            event: Resize event
        """
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
    def sliderDrag(self, event: Any) -> None:
        """Handle slider drag event with optional PRISM_SLIDER_FIX.
        
        Args:
            event: Mouse event
        """
        if os.getenv("PRISM_SLIDER_FIX", "0") == "1":
            custEvent = QMouseEvent(
                QEvent.MouseButtonPress,
                event.pos(),
                Qt.MidButton,
                Qt.MidButton,
                Qt.NoModifier,
            )
        else:
            custEvent = event

        self.sl_preview.origMousePressEvent(custEvent)

    @err_catcher(name=__name__)
    def sliderClk(self) -> None:
        """Handle slider press event to pause playback."""
        if (
            self.timeline
            and self.timeline.state() == QTimeLine.Running
        ):
            self.slStop = True
            self.setTimelinePaused(True)
        else:
            self.slStop = False

    @err_catcher(name=__name__)
    def sliderRls(self) -> None:
        """Handle slider release event to resume playback."""
        if self.slStop:
            self.setTimelinePaused(False)

    @err_catcher(name=__name__)
    def previewDragEnterEvent(self, e: Any) -> None:
        """Handle drag enter event for preview label.
        
        Args:
            e: Drag enter event
        """
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
    def previewDragMoveEvent(self, e: Any) -> None:
        """Handle drag move event over preview label.
        
        Args:
            e: Drag move event
        """
        if e.mimeData().hasUrls():
            e.accept()
            self.l_preview.setStyleSheet(
                "QWidget { border-style: dashed; border-color: rgb(100, 200, 100);  border-width: 2px; }"
            )
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def previewDragLeaveEvent(self, e: Any) -> None:
        """Handle drag leave event from preview label.
        
        Args:
            e: Drag leave event
        """
        self.l_preview.setStyleSheet("QWidget { border-style: dashed; border-color: rgba(0, 0, 0, 0);  border-width: 2px; }")

    @err_catcher(name=__name__)
    def previewDropEvent(self, e: Any) -> None:
        """Handle drop event for preview label.
        
        Allows dropping media files for import/ingestion.
        
        Args:
            e: Drop event
        """
        if e.mimeData().hasUrls():
            self.l_preview.setStyleSheet("QWidget { border-style: dashed; border-color: rgba(0, 0, 0, 0);  border-width: 2px; }")
            e.setDropAction(Qt.LinkAction)
            e.accept()

            files = [
                os.path.normpath(str(url.toLocalFile())) for url in e.mimeData().urls()
            ]
            entity = self.origin.getCurrentEntity()
            self.origin.ingestMediaToSelection(entity, files)
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def compare(self, prog: str = "", paths: Optional[List[str]] = None) -> None:
        """Open media comparison in external tool.
        
        Args:
            prog: External program name (RV, DJV, etc.)
            paths: Additional file paths to pass as arguments to the media player
        """
        if (
            self.timeline
            and self.timeline.state() == QTimeLine.Running
        ):
            self.setTimelinePaused(True)

        if prog == "default":
            progPath = ""
        else:
            mediaPlayer = None
            if prog and self.externalMediaPlayers:
                matchingPlayers = [player for player in self.externalMediaPlayers if player.get("name") == prog]
                if matchingPlayers:
                    mediaPlayer = matchingPlayers[0]
                else:
                    self.core.popup("Can't find media player: %s" % prog)
                    return

            if not mediaPlayer:
                mediaPlayer = self.externalMediaPlayers[0] if self.externalMediaPlayers else None

            progPath = (mediaPlayer.get("path") or "") if mediaPlayer else ""

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
                        if mediaPlayer and mediaPlayer.get("framePattern"):
                            filePath = self.core.media.getSequenceFromFilename(filePath)

                        comd = [progPath]
                        if paths:
                            for extra in paths:
                                if mediaPlayer and mediaPlayer.get("framePattern"):
                                    extra = self.core.media.getSequenceFromFilename(extra)

                                comd.append(extra)

                            if len(paths) > 1 and "rv" in os.path.basename(progPath).lower():
                                comd += ["-view", "defaultLayout"]

                        else:
                            comd.append(filePath)

        if comd:
            mpEnv = self.core.startEnv.copy()
            usrEnv = self.core.users.getUserEnvironment()
            for envVar in usrEnv:
                mpEnv[envVar["key"]] = envVar["value"]

            prjEnv = self.core.projects.getProjectEnvironment()
            for envVar in prjEnv:
                mpEnv[envVar["key"]] = envVar["value"]

            comd[0] = os.path.expandvars(comd[0])
            if platform.system() == "Darwin" and progPath.endswith(".app"):
                comd = ["open", "-a"] + comd

            self.core.callback(name="preLaunchApp", args=[comd, mpEnv])
            with open(os.devnull, "w") as f:
                logger.debug("launching: %s - %s" % (comd, mpEnv))
                try:
                    subprocess.Popen(comd, stdin=subprocess.PIPE, stdout=f, stderr=f, env=mpEnv)
                except:
                    comd = "%s %s" % (comd[0], comd[1])
                    try:
                        subprocess.Popen(
                            comd, stdin=subprocess.PIPE, stdout=f, stderr=f, shell=True, env=mpEnv
                        )
                    except Exception as e:
                        raise RuntimeError("%s - %s" % (comd, e))

    @err_catcher(name=__name__)
    def mouseDrag(self, event: Any, element: Any) -> None:
        """Handle mouse drag to initiate drag-and-drop operation.
        
        Args:
            event: Mouse event
            element: Widget element being dragged from
        """
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
    def getCurRenders(self) -> List[Dict[str, Any]]:
        """Get current render contexts from parent MediaBrowser.
        
        Returns:
            List of context dictionaries
        """
        return self.origin.getCurRenders()

    @err_catcher(name=__name__)
    def updateExternalMediaPlayer(self) -> None:
        """Update the list of available external media players from user settings."""
        self.externalMediaPlayers = self.core.media.getExternalMediaPlayers()

    @err_catcher(name=__name__)
    def getRVdLUT(self) -> Optional[str]:
        """Get RV display LUT path from project settings.
        
        Returns:
            Path to RV display LUT file, or None
        """
        dlut = None

        assets = self.core.getConfig("paths", "assets", configPath=self.core.prismIni)

        if assets is not None:
            lutPath = os.path.join(self.core.projectPath, assets, "LUTs", "RV_dLUT")
            if os.path.exists(lutPath) and len(os.listdir(lutPath)) > 0:
                dlut = os.path.join(lutPath, os.listdir(lutPath)[0])

        return dlut

    @err_catcher(name=__name__)
    def convertImgs(self, extension: str, checkRes: bool = True, settings: Optional[Dict[str, Any]] = None) -> None:
        """Convert media to a different format.
        
        Args:
            extension: Target file extension
            checkRes: Whether to check resolution match
            settings: Conversion settings dictionary
        """
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
            if os.getenv("PRISM_COPY_FILE_CONTENT", "0") == "1":
                self.core.copyToClipboard(outputpath, file=True)
            else:
                self.core.copyToClipboard(outputpath, file=False)

            msg = "The images were converted successfully. (path is in clipboard)"
            self.core.popup(msg, severity="info")
        else:
            msg = "The images could not be converted."
            logger.debug("expected outputpath: %s" % outputpath)
            self.core.ffmpegError("Image conversion", msg, result)

    @err_catcher(name=__name__)
    def compGetImportSource(self) -> str:
        """Get import source path for compositor integration.
        
        Returns:
            Source folder path
        """
        sourceFolder = os.path.dirname(self.seq[0]).replace("\\", "/")
        sources = self.core.media.getImgSources(sourceFolder)
        sourceData = []

        for curSourcePath in sources:
            if ("#" * self.core.framePadding) in curSourcePath:
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
    def compGetImportPasses(self) -> List[str]:
        """Get list of available render passes for compositor import.
        
        Returns:
            List of pass folder paths
        """
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
                increment = "#" * self.core.framePadding
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
    def triggerAutoplay(self, checked: bool = False) -> None:
        """Toggle autoplay preference and save to config.
        
        Args:
            checked: Whether autoplay should be enabled
        """
        self.core.setConfig("browser", "autoplaypreview", checked)

        if self.timeline:
            if checked and self.timeline.state() == QTimeLine.Paused:
                self.setTimelinePaused(False)
            elif not checked and self.timeline.state() == QTimeLine.Running:
                self.setTimelinePaused(True)
        else:
            self.tlPaused = not checked


class VersionDelegate(QStyledItemDelegate):
    """Custom item delegate for version list widget.
    
    Renders location icons on version items  to indicate which storage
    locations contain the version.
    
    Attributes:
        origin: Parent MediaBrowser instance
        widget: Version list widget
    """
    
    def __init__(self, origin: Any) -> None:
        """Initialize the version delegate.
        
        Args:
            origin: Parent MediaBrowser instance
        """
        super(VersionDelegate, self).__init__()
        self.origin = origin
        self.widget = self.origin.lw_version

    def paint(self, painterQPainter: Any, optionQStyleOptionViewItem: Any, indexQModelIndex: Any) -> None:
        """Paint the version item with location icons.
        
        Args:
            painterQPainter: QPainter instance
            optionQStyleOptionViewItem: Style options
            indexQModelIndex: Model index of item to paint
        """
        item = self.widget.itemFromIndex(indexQModelIndex)
        QStyledItemDelegate.paint(
            self, painterQPainter, optionQStyleOptionViewItem, indexQModelIndex
        )

        data = item.data(Qt.UserRole)
        offset = 0
        if len(self.origin.projectBrowser.locations) > 1:
            for location in reversed(self.origin.projectBrowser.locations):
                if location.get("name") not in data.get("locations", {}):
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
                    painterQPainter.setRenderHint(QPainter.Antialiasing, True)
                    painterQPainter.setRenderHint(QPainter.SmoothPixmapTransform, True)
                    location["icon"].paint(painterQPainter, rect)
                    offset += 25
