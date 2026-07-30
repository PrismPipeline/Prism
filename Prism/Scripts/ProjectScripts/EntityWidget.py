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
from typing import Any, Optional, List, Dict, Tuple

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
    """Widget for displaying and managing project entities (assets and shots).
    
    This widget provides a tabbed interface for browsing assets and shots within
    a project. It supports:
    - Multiple pages (typically Assets and Shots)
    - Location filtering (project, global, custom locations)
    - Search functionality
    - Entity selection and navigation
    - Entity creation and editing
    
    Signals:
        tabChanged: Emitted when the active tab (Assets/Shots) changes
    
    Attributes:
        core: The Prism core instance
        pageNames: Translated names of pages (e.g., ["Assets", "Shots"])
        pages: List of EntityPage instances
        refresh: Whether to refresh entities on creation
        mode: Operation mode ("scenefiles", "products", "renders")
        prevTab: Previously active EntityPage
        editEntitiesOnDclick: Whether double-click opens entity edit dialog
    """
    
    tabChanged = Signal()

    def __init__(self, core: Any, refresh: bool = True, mode: str = "scenefiles", pages: Optional[List[str]] = None) -> None:
        """Initialize the EntityWidget.
        
        Args:
            core: The Prism core instance providing access to pipeline functionality
            refresh: Whether to refresh entities immediately after creation
            mode: Operation mode - "scenefiles", "products", or "renders"
            pages: List of page names to display (defaults to ["Assets", "Shots"])
        """
        QWidget.__init__(self)
        self.core = core
        self.core.parentWindow(self)
        pages = pages or ["Assets", "Shots"]
        self.pageNames = [self.core.tr(page) for page in pages]
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
    def setupUi(self) -> None:
        """Set up the entity widget UI.
        
        Creates the tabbed interface with entity pages and search button.
        """
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

        for pageName in self.pageNames:
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
    def resizeEvent(self, event: Any) -> None:
        """Handle widget resize events.
        
        Args:
            event: The resize event object
            
        Repositions the search button to stay in the top-right corner.
        """
        self.b_search.move(
            self.w_header.geometry().width() - self.b_search.geometry().width(), 0
        )

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect UI widget signals to handler functions."""
        self.tb_entities.currentChanged.connect(self.ontabChanged)
        self.b_search.toggled.connect(self.searchClicked)

    @err_catcher(name=__name__)
    def refreshEntities(self, pages: Optional[List[str]] = None, restoreSelection: bool = False, defaultSelection: bool = True) -> None:
        """Refresh entities on one or more pages.
        
        Args:
            pages: List of page names to refresh, or None to refresh all
            restoreSelection: Whether to restore the previous selection after refresh
            defaultSelection: Whether to select a default item after refresh
        """
        for page in self.pages:
            if pages and page.objectName() not in pages:
                continue

            if page.objectName() == self.getCurrentPageName():
                page.refreshEntities(restoreSelection=restoreSelection, defaultSelection=defaultSelection)
            else:
                page.dirty = True

    @err_catcher(name=__name__)
    def getPage(self, pageName: str) -> Optional[Any]:
        """Get a page by its name.
        
        Args:
            pageName: Name of the page to retrieve
            
        Returns:
            EntityPage instance, or None if not found
        """
        for page in self.pages:
            if page.objectName() == self.core.tr(pageName):
                return page

    @err_catcher(name=__name__)
    def getCurrentPage(self) -> Optional[Any]:
        """Get the currently active page.
        
        Returns:
            Currently active EntityPage instance
        """
        return self.sw_tabs.currentWidget()

    @err_catcher(name=__name__)
    def getCurrentPageName(self) -> str:
        """Get the name of the currently active page.
        
        Returns:
            Name of the currently active page (e.g., "Assets", "Shots")
        """
        return self.sw_tabs.currentWidget().objectName()

    @err_catcher(name=__name__)
    def searchClicked(self, state: bool) -> None:
        """Handle search button click.
        
        Args:
            state: Whether search is enabled
        """
        self.sw_tabs.currentWidget().searchClicked(state)

    @err_catcher(name=__name__)
    def ontabChanged(self, state: int) -> None:
        """Handle tab change events.
        
        Args:
            state: Index of the newly active tab
            
        Switches the stacked widget to show the selected page, syncs location
        selection, and refreshes if the page is dirty.
        """
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

        if widget.dirty:
            widget.refreshEntities(restoreSelection=True)

        self.tabChanged.emit()
        self.prevTab = self.getCurrentPage()

    @err_catcher(name=__name__)
    def getCurrentData(self, returnOne: bool = True) -> Optional[Dict[str, Any]]:
        """Get data for currently selected entity.
        
        Args:
            returnOne: If True, return single item; if False, return list
            
        Returns:
            Entity data dict with type, paths, identifiers
        """
        data = self.getCurrentPage().getCurrentData(returnOne=returnOne)
        if not data:
            if self.getCurrentPageName() == "Assets":
                pageType = "asset"
            elif self.getCurrentPageName() == "Shots":
                pageType = "shot"

            data = {"type": pageType}
            if not returnOne:
                data = [data]

        return data

    @err_catcher(name=__name__)
    def getLocations(self) -> Dict[str, str]:
        """Get available locations for the current page.
        
        Returns:
            Dictionary mapping location names to paths
        """
        return self.getCurrentPage().getLocations()

    @err_catcher(name=__name__)
    def navigate(self, data: Any, clear: bool = False) -> Optional[bool]:
        """Navigate to and select specific entities.
        
        Args:
            data: Entity data dictionary or list of dictionaries to navigate to
            clear: Whether to clear selection if navigation fails
            
        Returns:
            False on failure, None on success
        """
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
    def syncFromWidget(self, widget: Any, navData: Optional[Any] = None) -> None:
        """Synchronize state from another EntityWidget.
        
        Args:
            widget: Source EntityWidget to sync from
            navData: Optional navigation data to use instead of getting from widget
        """
        data = navData or widget.getCurrentData()
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
    def getCurrentLocation(self) -> str:
        """Get the current location from the active page.
        
        Returns:
            Location key (e.g., 'global', 'local')
        """
        return self.getCurrentPage().getCurrentLocation()


class EntityPage(QWidget):
    """Individual page widget for displaying entities of a specific type.
    
    This class manages the display of either assets or shots in a tree view,
    with support for:
    - Hierarchical entity display (folders, sequences, shots)
    - Entity thumbnails/previews
    - Search filtering
    - Location filtering
    - Context menus for entity operations
    - Drag and drop operations
    
    Signals:
        itemChanged: Emitted when the selected item changes (passes item)
        entityCreated: Emitted when a new entity is created (passes entity data)
        shotSaved: Emitted when shot information is saved
        nextClicked: Emitted when Next button is clicked in edit dialog
    
    Attributes:
        entityWidget: Parent EntityWidget instance
        core: The Prism core instance
        pageName: Display name of this page ("Assets" or "Shots")
        entityType: Type of entities on this page ("asset" or "shot")
        expandedItems: List of expanded item paths
        dirty: Whether the page needs refreshing
        useCounter: Whether to display entity counters
    """
    
    itemChanged = Signal(object)
    entityCreated = Signal(object)

    shotSaved = Signal()
    nextClicked = Signal()

    def __init__(self, widget: Any, pageName: str, refresh: bool = True) -> None:
        """Initialize the EntityPage.
        
        Args:
            widget: Parent EntityWidget instance
            pageName: Display name for this page (e.g., "Assets", "Shots")
            refresh: Whether to refresh entities immediately after creation
        """
        QWidget.__init__(self)
        self.entityWidget = widget
        self.core = widget.core
        self.pageName = pageName
        self.expandedItems = []
        self.dclick = None
        self.entityPreviewWidth = 107
        self.entityPreviewHeight = 60
        self.itemWidgets = []
        self.dirty = True
        self.useCounter = False
        self.setObjectName(self.pageName)
        if pageName == self.core.tr("Assets"):
            self.entityType = "asset"
        elif pageName == self.core.tr("Shots"):
            self.entityType = "shot"

        self.setupUi()
        self.connectEvents()

        if refresh:
            self.refreshEntities()

    @err_catcher(name=__name__)
    def refreshEntities(self, restoreSelection: bool = False, defaultSelection: bool = True) -> None:
        """Refresh entity tree view with assets or shots.
        
        Args:
            restoreSelection: Restore previous selection after refresh. Defaults to False.
            defaultSelection: Select first item by default. Defaults to True.
        """
        prevData = self.getCurrentData()
        self.itemWidgets = []

        wasBlocked = self.tw_tree.signalsBlocked()
        if not wasBlocked:
            self.tw_tree.blockSignals(True)
            self.tw_tree.selectionModel().blockSignals(True)

        if self.entityType == "asset":
            self.refreshAssetHierarchy(defaultSelection=defaultSelection)
        elif self.entityType == "shot":
            self.refreshShots(defaultSelection=defaultSelection)

        if restoreSelection:
            self.navigate(prevData)

        if not wasBlocked:
            self.tw_tree.blockSignals(False)
            self.tw_tree.selectionModel().blockSignals(False)
            if self.getCurrentData() != prevData:
                self.onItemChanged()

        self.dirty = False

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Set up EntityPage UI with search bar, location selector, and tree view."""
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

        if self.entityType == "asset":
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "asset.png"
            )
            self.assetIcon = self.core.media.getColoredIcon(iconPath)

            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "folder.png"
            )
            self.folderIcon = self.core.media.getColoredIcon(iconPath)
        else:
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "folder.png"
            )
            self.folderIcon = self.core.media.getColoredIcon(iconPath)

            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "episode.png"
            )
            self.episodeIcon = self.core.media.getColoredIcon(iconPath)

            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "sequence.png"
            )
            self.seqIcon = self.core.media.getColoredIcon(iconPath)

            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "shot.png"
            )
            self.shotIcon = self.core.media.getColoredIcon(iconPath)

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect UI events and override tree widget mouse events."""
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

        self.tw_tree.selectionModel().selectionChanged.connect(self.onItemChanged)
        self.tw_tree.itemExpanded.connect(self.itemExpanded)
        self.tw_tree.itemCollapsed.connect(self.itemCollapsed)
        self.tw_tree.customContextMenuRequested.connect(self.contextMenuTree)
        self.e_search.textChanged.connect(self.onSearchTextChanged)
        self.cb_location.activated.connect(self.onLocationChanged)

    @err_catcher(name=__name__)
    def onSearchTextChanged(self, text: str) -> None:
        """Handle search text changes and refresh entities when criteria met.
        
        Args:
            text: The new search text entered by the user
        """
        minLength = int(os.getenv("PRISM_MINIMUM_SEARCH_LENGTH", "0"))
        if len(text) >= minLength or len(text) == 0:
            self.refreshEntities(restoreSelection=True)

    @err_catcher(name=__name__)
    def getLocations(self, includeAll: bool = False) -> Dict[str, str]:
        """Get available entity locations.
        
        Args:
            includeAll: Whether to include the 'all' location option
            
        Returns:
            Dictionary mapping location names to their file system paths
        """
        locs = self.locations.copy()
        if not includeAll:
            if "all" in locs:
                del locs["all"]

        return locs

    @err_catcher(name=__name__)
    def getCurrentLocation(self) -> str:
        """Get the currently selected location.
        
        Returns:
            The name of the current location, or 'all' if location selector is hidden
        """
        if not self.cb_location.isHidden():
            locations = self.cb_location.currentText()
        else:
            locations = "all"

        return locations

    @err_catcher(name=__name__)
    def onLocationChanged(self, idx: int) -> None:
        """Handle location selection changes and refresh entities.
        
        Args:
            idx: The index of the newly selected location
        """
        self.refreshEntities(restoreSelection=True)

    @err_catcher(name=__name__)
    def refreshAssetHierarchy(self, defaultSelection: bool = True) -> None:
        """Refresh the asset tree hierarchy with filtering support.
        
        Rebuilds the entire asset tree widget, applying search filters if active.
        Preserves expanded items and restores selection state.
        
        Args:
            defaultSelection: Whether to select the first item if no current selection exists
        """
        wasBlocked = self.tw_tree.signalsBlocked()
        if not wasBlocked:
            self.tw_tree.blockSignals(True)
            self.tw_tree.selectionModel().blockSignals(True)

        self.tw_tree.clear()
        self.addedAssetItems = {}
        self.filteredAssets = []
        if self.e_search.isVisible() and self.e_search.text():
            showOmitted = self.core.getConfig("browser", "showOmittedEntities", config="user", dft=False)
            assets, folders = self.core.entities.getAssetPaths(
                returnFolders=True, depth=0, includeOmitted=showOmitted
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
            self.tw_tree.selectionModel().blockSignals(False)
            self.itemChanged.emit(self.tw_tree.currentItem())

    @err_catcher(name=__name__)
    def refreshAssets(self, path: Optional[str] = None, parent: Optional[Any] = None, refreshChildren: bool = True) -> None:
        """Refresh assets and folders at a specific path in the hierarchy.
        
        Loads assets and asset folders from the file system, applying location
        and search filters. Adds items to the tree widget as children of the
        specified parent.
        
        Args:
            path: File system path to refresh from (defaults to asset root)
            parent: Parent tree widget item (None for root level)
            refreshChildren: Whether to refresh child items recursively
        """
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
        showOmitted = self.core.getConfig("browser", "showOmittedEntities", config="user", dft=False)
        for location in locations:
            basePath = self.getLocations()[location]
            path = self.core.convertPath(path, location)
            assetPaths, folderPaths = self.core.entities.getAssetPaths(
                path=path, returnFolders=True, depth=1, includeOmitted=showOmitted
            )
            for assetPath in assetPaths:
                if basePath not in assets:
                    assets[basePath] = []

                assets[basePath].append(assetPath)

            for folderPath in folderPaths:
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
    def addAssetItem(self, path: str, itemType: str, parent: Optional[Any] = None, refreshItem: bool = True) -> None:
        """Add an asset or asset folder item to the tree widget.
        
        Creates a new tree widget item for an asset or folder. If the asset already
        exists in the tree (by relative path), adds the new path to its location list.
        
        Args:
            path: File system path to the asset or folder
            itemType: Type of item - 'asset' or 'assetFolder'
            parent: Parent tree widget item (None for root level)
            refreshItem: Whether to refresh the item's children after adding
        """
        name = os.path.basename(path)
        relPath = self.core.entities.getAssetRelPathFromPath(path)
        if relPath in self.addedAssetItems:
            item = self.addedAssetItems[relPath]
            data = item.data(0, Qt.UserRole)
            data["paths"].append(path)
            item.setData(0, Qt.UserRole, data)
            if parent and parent.isExpanded():
                refreshItem = True
            else:
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
    def refreshAssetItem(self, item: Any) -> None:
        """Refresh an asset tree item's display and children.
        
        Updates the item's visual representation, including preview thumbnails,
        icons, and folder contents. Handles both asset and folder items.
        
        Args:
            item: The tree widget item to refresh
        """
        if not item:
            return

        item.takeChildren()
        data = item.data(0, Qt.UserRole)
        path = data["paths"][0]
        itemType = data["type"]
        expand = path in self.expandedItems
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
                if self.useCounter:
                    curCount = self.getCount(item)
                    item.l_counter = QLabel("")
                    lo_entity.addWidget(item.l_counter)
                    if curCount and curCount > 1:
                        self.setCount(item, curCount)

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
    def itemExpanded(self, item: Any) -> None:
        """Handle tree item expansion events.
        
        Called when a user expands a tree item. Updates the expanded items list,
        handles Ctrl+Click to expand all children, and lazily loads child items
        for shots.
        
        Args:
            item: The tree widget item that was expanded
        """
        itemData = item.data(0, Qt.UserRole)
        if self.entityType == "asset":
            name = itemData["paths"][0]
        elif self.entityType == "shot":
            name = self.core.entities.getShotName(itemData)

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
        elif self.entityType == "shot":
            if not self.core.isStr(itemData) and itemData.get("loaded") is False:
                self.refreshShotItemChildren(item)

    @err_catcher(name=__name__)
    def itemCollapsed(self, item: Any) -> None:
        """Handle tree item collapse events.
        
        Called when a user collapses a tree item. Updates the expanded items list
        and handles Ctrl+Click to collapse all children.
        
        Args:
            item: The tree widget item that was collapsed
        """
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
    def refreshShots(self, defaultSelection: bool = True) -> None:
        """Refresh the shot tree hierarchy.
        
        Rebuilds the entire shot tree widget with episodes (if enabled), sequences,
        and shots. Applies search filters and restores expanded/selected states.
        
        Args:
            defaultSelection: Whether to select the first item if no current selection exists
        """
        wasBlocked = self.tw_tree.signalsBlocked()
        if not wasBlocked:
            self.tw_tree.blockSignals(True)
            self.tw_tree.selectionModel().blockSignals(True)

        self.tw_tree.clear()

        location = self.getCurrentLocation()
        if location == "all":
            locations = list(self.getLocations().keys())
        else:
            locations = [location]

        searchFilter = ""
        if self.e_search.isVisible():
            searchFilter = self.e_search.text()

        showOmitted = self.core.getConfig("browser", "showOmittedEntities", config="user", dft=False)
        useEpisodes = self.core.getConfig(
            "globals",
            "useEpisodes",
            config="project",
        ) or False
        if useEpisodes:
            episodes = self.core.entities.getEpisodes(locations=locations, searchFilter=searchFilter, includeOmitted=showOmitted)
            parent = self.tw_tree.invisibleRootItem()
            for episode in episodes:
                item = self.addEpisodeItem(episode, parent=parent)

        else:
            sequences = self.core.entities.getSequences(locations=locations, searchFilter=searchFilter, includeOmitted=showOmitted)
            seqItems = {}
            for sequence in sequences:
                parent = self.tw_tree.invisibleRootItem()
                seqName = ""
                seqParts = sequence["sequence"].split("__") if os.getenv("PRISM_USE_SEQUENCE_FOLDERS") == "1" else [sequence["sequence"]]
                for idx, seqPart in enumerate(seqParts):
                    seqName = (seqName + "/" + seqPart).strip("/")
                    if seqName in seqItems:
                        item = seqItems[seqName]
                    else:
                        icon = self.seqIcon if idx == (len(seqParts) - 1) else self.folderIcon
                        data = {"sequence": seqPart}
                        if len(seqParts) > 1:
                            data["children"] = seqParts[idx+1:]

                        item = self.addSequenceItem(data, parent=parent, icon=icon, hierarchy=seqName)
                        seqItems[seqName] = item

                    parent = item

        self.tw_tree.resizeColumnToContents(0)
        if defaultSelection and self.tw_tree.topLevelItemCount() > 0:
            if self.tw_tree.topLevelItem(0).isExpanded():
                self.tw_tree.setCurrentItem(self.tw_tree.topLevelItem(0).child(0))
            else:
                self.tw_tree.setCurrentItem(self.tw_tree.topLevelItem(0))

        if not wasBlocked:
            self.tw_tree.blockSignals(False)
            self.tw_tree.selectionModel().blockSignals(False)
            self.itemChanged.emit(self.tw_tree.currentItem())

    @err_catcher(name=__name__)
    def addEpisodeItem(self, episode: Dict[str, Any], parent: Any) -> Any:
        """Add an episode item to the tree widget.
        
        Creates a tree widget item for an episode container. Episodes are only
        used when the project is configured to use episodic shot organization.
        
        Args:
            episode: Dictionary containing episode data including 'episode' key
            parent: Parent tree widget item to add this episode to
            
        Returns:
            The created episode QTreeWidgetItem
        """
        epName = episode["episode"]
        epItem = QTreeWidgetItem([epName])
        data = {"type": "shot", "episode": epName, "sequence": "_episode", "shot": "_sequence", "loaded": False, "itemType": "episode"}
        epItem.setData(0, Qt.UserRole, data)
        epItem.setIcon(0, self.episodeIcon)
        parent.addChild(epItem)
        if epName in self.expandedItems:
            epItem.setExpanded(True)
        else:
            placeHolder = QTreeWidgetItem(["__placeholder__"])
            placeHolder.setData(0, Qt.UserRole, "placeholder")
            epItem.addChild(placeHolder)

        return epItem

    @err_catcher(name=__name__)
    def addSequenceItem(self, sequence: Dict[str, Any], parent: Any, icon: Any, hierarchy: str) -> Any:
        """Add a sequence item to the tree widget.
        
        Creates a tree widget item for a shot sequence. Supports both flat and
        hierarchical sequence organization.
        
        Args:
            sequence: Dictionary containing sequence data including 'sequence' key
            parent: Parent tree widget item to add this sequence to
            icon: QIcon to display for this sequence
            hierarchy: Full hierarchical path to this sequence
            
        Returns:
            The created sequence QTreeWidgetItem
        """
        seqName = sequence["sequence"]
        seqItem = QTreeWidgetItem([seqName])
        data = {"type": "shot", "sequence": seqName, "shot": "_sequence", "hierarchy": hierarchy, "itemType": "sequence", "loaded": False}
        if os.getenv("PRISM_USE_SEQUENCE_FOLDERS") == "1" and sequence.get("children"):
            data["children"] = sequence["children"]
            data["loaded"] = True

        if "episode" in sequence:
            data["episode"] = sequence["episode"]

        seqItem.setData(0, Qt.UserRole, data)
        seqItem.setIcon(0, icon)
        parent.addChild(seqItem)
        if data.get("children"):
            if seqName in self.expandedItems:
                seqItem.setExpanded(True)

        else:
            if seqName in self.expandedItems:
                seqItem.setExpanded(True)
                self.refreshShotItemChildren(seqItem)
            else:
                placeHolder = QTreeWidgetItem(["__placeholder__"])
                placeHolder.setData(0, Qt.UserRole, "placeholder")
                seqItem.addChild(placeHolder)

        return seqItem

    @err_catcher(name=__name__)
    def addShotItem(self, shot: Dict[str, Any], parent: Any, hierarchy: str, showThumb: Optional[bool] = None) -> Any:
        """Add a shot item to the tree widget.
        
        Creates a tree widget item for a shot with optional thumbnail preview.
        
        Args:
            shot: Dictionary containing shot data including 'shot' and 'sequence' keys
            parent: Parent tree widget item to add this shot to
            hierarchy: Full hierarchical path to this shot
            showThumb: Whether to show thumbnail preview (uses user config if None)
            
        Returns:
            The created shot QTreeWidgetItem
        """
        shotName = shot["shot"]
        shotItem = QTreeWidgetItem([shotName])
        data = {"type": "shot", "sequence": shot["sequence"], "shot": shotName, "hierarchy": hierarchy, "itemType": "shot"}
        if "episode" in shot:
            data["episode"] = shot["episode"]

        shotItem.setData(0, Qt.UserRole, data)
        parent.addChild(shotItem)
        showThumb = self.core.getConfig("browser", "showEntityPreviews", config="user", dft=True) if showThumb is None else showThumb
        if showThumb:
            self.refreshShotThumbnail(shotItem)
        else:
            shotItem.setIcon(0, self.shotIcon)

        return shotItem

    @err_catcher(name=__name__)
    def refreshShotThumbnail(self, item: Any) -> None:
        """Refresh the thumbnail preview for a shot item.
        
        Loads and displays the shot's preview image as an inline widget
        in the tree view.
        
        Args:
            item: The shot tree widget item to update with a thumbnail
        """
        if self.tw_tree.itemWidget(item, 0):
            return

        if item.childCount():
            return

        entity = item.data(0, Qt.UserRole)
        pm = self.core.entities.getEntityPreview(entity)
        if not pm:
            pm = self.core.media.emptyPrvPixmap

        w_entity = QWidget()
        w_entity.setStyleSheet("background-color: transparent;")
        lo_entity = QHBoxLayout()
        lo_entity.setContentsMargins(0, 0, 0, 0)
        w_entity.setLayout(lo_entity)
        l_preview = QLabel()
        l_label = QLabel(entity.get("shot"))
        lo_entity.addWidget(l_preview)
        lo_entity.addWidget(l_label)
        lo_entity.addStretch()
        if pm:
            pmap = self.core.media.scalePixmap(pm, self.entityPreviewWidth, self.entityPreviewHeight, fitIntoBounds=False, crop=True)
            l_preview.setPixmap(pmap)

        self.tw_tree.setItemWidget(item, 0, w_entity)
        self.itemWidgets.append(w_entity)
        item.setText(0, "")

    @err_catcher(name=__name__)
    def refreshShotItemChildren(self, item: Any) -> None:
        """Refresh the children of a shot hierarchy item (episode or sequence).
        
        Lazily loads and displays sequences under episodes or shots under sequences.
        Marks the item as loaded to prevent redundant loading.
        
        Args:
            item: The episode or sequence tree widget item to refresh children for
        """
        data = item.data(0, Qt.UserRole)
        if data.get("loaded") is False:
            data["loaded"] = True
        elif data.get("loaded") is True:
            return

        item.takeChildren()
        item.setData(0, Qt.UserRole, data)
        searchFilter = ""
        if self.e_search.isVisible():
            searchFilter = self.e_search.text()

        location = self.getCurrentLocation()
        if location == "all":
            locations = list(self.getLocations().keys())
        else:
            locations = [location]

        showOmitted = self.core.getConfig("browser", "showOmittedEntities", config="user", dft=False)
        if data["itemType"] == "episode":
            sequences = self.core.entities.getSequences(episode=data["episode"], searchFilter=searchFilter, locations=locations, includeOmitted=showOmitted)
            for sequence in sequences:
                self.addSequenceItem(sequence, item, self.seqIcon, "%s/%s" % (data["episode"], sequence["sequence"]))
        elif data["itemType"] == "sequence":
            sequence = data["sequence"]
            if os.getenv("PRISM_USE_SEQUENCE_FOLDERS") == "1":
                sequence = data["hierarchy"].replace("/", "__")

            shots = self.core.entities.getShots(episode=data.get("episode", None), sequence=sequence, searchFilter=searchFilter, locations=locations, includeOmitted=showOmitted)
            showThumb = self.core.getConfig("browser", "showEntityPreviews", config="user", dft=True)
            for shot in shots:
                self.addShotItem(shot, item, "%s/%s" % (data["hierarchy"], shot["shot"]), showThumb=showThumb)

    @err_catcher(name=__name__)
    def toggleShowOmitted(self, state: bool) -> None:
        """Toggle visibility of omitted entities.

        Args:
            state: True to show omitted entities, False to hide them
        """
        self.core.setConfig("browser", "showOmittedEntities", state, config="user")
        self.refreshEntities(restoreSelection=True)

    @err_catcher(name=__name__)
    def omitEntity(self, entity: Dict[str, Any], omit: bool = True) -> None:
        """Omit or unomit an entity from the browser.
        
        Prompts the user for confirmation before marking the entity as omitted
        or restoring it. Omitted entities remain on disk but are hidden from
        Prism browsers.
        
        Args:
            entity: Entity data dictionary with 'type' and path information
            omit: If True, omit the entity. If False, restore it.
        """
        if entity["type"] in ["asset", "assetFolder"]:
            name = entity["asset_path"]
        elif entity["type"] == "shot":
            name = self.core.entities.getShotName(entity)

        if omit:
            msgText = (
                'Are you sure you want to omit %s "%s"?\n\nThis will hide the %s in Prism, but all scenefiles and renders remain on disk.'
                % (entity["type"].lower(), name, entity["type"].lower())
            )
        else:
            msgText = (
                'Are you sure you want to unomit %s "%s"?\n\nThis will make the %s visible again in Prism.'
                % (entity["type"].lower(), name, entity["type"].lower())
            )

        result = self.core.popupQuestion(msgText)
        if result == "Yes":
            self.core.entities.omitEntity(entity, omit=omit)
            self.refreshEntities(restoreSelection=True)

    @err_catcher(name=__name__)
    def setWidgetItemsExpanded(self, expanded: bool = True) -> None:
        """Expand or collapse all items in the tree widget.
        
        Args:
            expanded: True to expand all items, False to collapse all
        """
        for idx in range(self.tw_tree.topLevelItemCount()):
            item = self.tw_tree.topLevelItem(idx)
            item.setExpanded(expanded)
            self.setItemChildrenExpanded(item, expanded=expanded, recursive=True)

    @err_catcher(name=__name__)
    def setItemChildrenExpanded(self, item: Any, expanded: bool = True, recursive: bool = False) -> None:
        """Expand or collapse all children of a tree item.
        
        Args:
            item: The tree widget item whose children to expand/collapse
            expanded: True to expand, False to collapse
            recursive: Whether to recursively expand/collapse all descendants
        """
        for childIdx in range(item.childCount()):
            if recursive:
                self.setItemChildrenExpanded(
                    item.child(childIdx), expanded=expanded, recursive=True
                )
            item.child(childIdx).setExpanded(expanded)

    @err_catcher(name=__name__)
    def onItemChanged(self, selected: Optional[Any] = None, deselected: Optional[Any] = None) -> None:
        """Handle tree item selection changes.
        
        Updates selection counters if enabled and emits the itemChanged signal
        with the selected items.
        
        Args:
            selected: QItemSelection of newly selected items
            deselected: QItemSelection of newly deselected items
        """
        if self.useCounter:
            changed = False
            if selected:
                for index in selected.indexes():
                    item = self.tw_tree.itemFromIndex(index)
                    self.setCount(item, 1)
                    changed = True

            if deselected:
                for index in deselected.indexes():
                    item = self.tw_tree.itemFromIndex(index)
                    self.setCount(item, None)
                    changed = True

            if changed:
                return

        items = self.tw_tree.selectedItems()
        if self.tw_tree.selectionMode() == QAbstractItemView.SingleSelection:
            if items:
                items = items[0]
            else:
                items = None

        self.itemChanged.emit(items)

    @err_catcher(name=__name__)
    def showPreviewToggled(self, state: bool) -> None:
        """Handle toggling of entity preview display.
        
        Saves the user preference and refreshes the entity view to show or hide
        thumbnail previews.
        
        Args:
            state: True to show previews, False to hide them
        """
        self.core.setConfig("browser", "showEntityPreviews", state, config="user")
        self.entityWidget.refreshEntities(restoreSelection=True)

    @err_catcher(name=__name__)
    def searchClicked(self, state: bool) -> None:
        """Handle search button toggle.
        
        Shows or hides the search input and location filter. Clears search
        when hiding.
        
        Args:
            state: True to show search controls, False to hide them
        """
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
    def setSearchVisible(self, state: bool) -> None:
        """Programmatically show or hide the search controls.
        
        Args:
            state: True to show search controls, False to hide them
        """
        if hasattr(self.entityWidget, "b_search"):
            self.entityWidget.b_search.setChecked(state)

        self.e_search.setVisible(state)
        if len(self.locations) > 1:
            self.w_location.setVisible(state)

    @err_catcher(name=__name__)
    def setShowSearchAlways(self, state: bool) -> None:
        """Set whether the search button is always visible.
        
        Args:
            state: True to always show search, False to show toggle button
        """
        self.b_shotSearch.setHidden(state)

    @err_catcher(name=__name__)
    def isSearchVisible(self) -> bool:
        """Check if search controls are currently visible.
        
        Returns:
            True if search controls are visible, False otherwise
        """
        if hasattr(self.entityWidget, "b_search"):
            return self.entityWidget.b_search.isChecked()
        else:
            return self.e_search.isVisible()

    @err_catcher(name=__name__)
    def keyPressed(self, event: Any, widgetType: str) -> None:
        """Handle keyboard events for tree and search widgets.
        
        Implements keyboard shortcuts including Escape to hide search and
        automatic search activation when typing.
        
        Args:
            event: The keyboard event
            widgetType: Type of widget receiving the event ('tree' or 'search')
        """
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
    def getExpandedItems(self) -> List[str]:
        """Get list of all currently expanded items.
        
        Returns:
            List of paths/names for all expanded items in the tree
        """
        expandedAssets = []
        for idx in range(self.tw_tree.topLevelItemCount()):
            item = self.tw_tree.topLevelItem(idx)
            expandedAssets += self.getExpandedChildren(item)

        return expandedAssets

    @err_catcher(name=__name__)
    def getExpandedChildren(self, item: Any) -> List[str]:
        """Recursively get expanded items under a parent item.
        
        Args:
            item: The tree widget item to search under
            
        Returns:
            List of paths/names for all expanded items under the parent
        """
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
    def mouseEnter(self) -> None:
        """Handle mouse entering the tree widget.
        
        Sets focus to the tree widget when the mouse enters.
        """
        self.tw_tree.setFocus()

    @err_catcher(name=__name__)
    def mousedb(self, event: Any) -> None:
        """Handle mouse double-click events on the tree widget.
        
        Handles entity creation dialogs (for empty areas), item expansion/collapse,
        and selection counter adjustments (Ctrl+Click).
        
        Args:
            event: The mouse double-click event
        """
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
            if self.useCounter:
                mods = QApplication.keyboardModifiers()
                if mods == Qt.ControlModifier:
                    curCount = self.getCount(cItem)
                    if event.button() == Qt.LeftButton:
                        self.setCount(cItem, curCount+1)
                        if cItem.isSelected():
                            return

                    elif event.button() == Qt.RightButton:
                        self.setCount(cItem, curCount-1)
                        if cItem.isSelected():
                            return

        if not self.dclick:
            pos = self.tw_tree.mapFromGlobal(QCursor.pos())
            item = self.tw_tree.itemAt(pos.x(), pos.y())
            if item is not None:
                item.setExpanded(not item.isExpanded())

    @err_catcher(name=__name__)
    def mouseClickEvent(self, event: Any) -> None:
        """Handle mouse click and release events on the tree widget.
        
        Manages selection behavior, item expansion, and counter adjustments
        for Ctrl+Click operations.
        
        Args:
            event: The mouse event (press or release)
        """
        if not QEvent:
            return

        if event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                index = self.tw_tree.indexAt(event.pos())
                if index.data() is None:
                    self.tw_tree.setCurrentIndex(
                        self.tw_tree.model().createIndex(-1, 0)
                    )

                self.tw_tree.mouseClickEvent(event)
        elif event.type() == QEvent.MouseButtonPress:
            item = self.tw_tree.itemAt(event.pos())
            if self.useCounter:
                mods = QApplication.keyboardModifiers()
                if mods == Qt.ControlModifier:
                    curCount = self.getCount(item)
                    if event.button() == Qt.LeftButton:
                        self.setCount(item, curCount+1)
                        if item.isSelected():
                            return

                    elif event.button() == Qt.RightButton:
                        self.setCount(item, curCount-1)
                        if item.isSelected():
                            return

            self.dclick = True
            wasExpanded = item.isExpanded() if item else None
            self.tw_tree.mousePrEvent(event)

            if event.button() == Qt.LeftButton:
                if item and self.core.isObjectValid(item) and item.childCount() and wasExpanded == item.isExpanded():
                    item.setExpanded(not item.isExpanded())

    @err_catcher(name=__name__)
    def getCount(self, item: Any) -> int:
        """Get the selection count for an item.
        
        Args:
            item: The tree widget item to get count for
            
        Returns:
            The current count value (0 if no counter exists)
        """
        if not hasattr(item, "l_counter"):
            return 0

        return int(item.l_counter.text().strip("x") or "1")

    @err_catcher(name=__name__)
    def setCount(self, item: Any, count: Optional[int]) -> None:
        """Set the selection count for an item.
        
        Updates the counter label and deselects the item if count reaches zero.
        
        Args:
            item: The tree widget item to update
            count: The new count value (None to clear, 0 to deselect)
        """
        if not hasattr(item, "l_counter"):
            return

        if count is None:
            countStr = ""
        elif count == 0:
            countStr = ""
            item.setSelected(False)
        else:
            count = max(count, 1)
            countStr = "x" + str(count)

        item.l_counter.setText(countStr)
        item.l_counter.setHidden(False)
        self.onItemChanged()

    @err_catcher(name=__name__)
    def createFolderDlg(self, startText: Optional[str] = None) -> None:
        """Show dialog to create a new folder (asset or shot hierarchy).
        
        Opens a dialog for the user to enter a folder name. The folder type
        depends on the current entity type (asset folder or shot folder).
        
        Args:
            startText: Initial text to populate in the name field
        """
        if startText is None:
            curItem = self.tw_tree.currentItem()
            if curItem:
                data = curItem.data(0, Qt.UserRole)
                if data.get("type") == "assetFolder":
                    folderPath = data.get("asset_path", "")
                elif data.get("type") == "shotFolder":
                    folderPath = data.get("sequence", "")
                else:
                    if self.entityType == "asset":
                        folderPath = os.path.dirname(data.get("asset_path", ""))
                    else:
                        folderPath = os.path.dirname(data.get("sequence", ""))

                startText = folderPath.replace("\\", "/") + "/"

        startText = startText or ""
        if hasattr(self, "newItem") and self.core.isObjectValid(self.newItem):
            self.newItem.close()

        self.newItem = ProjectWidgets.CreateFolderDlg(self.core, parent=self, startText=startText)
        self.newItem.accepted.connect(self.onCreateFolderDlgAccepted)

        self.core.callback(name="onFolderDlgOpen", args=[self, self.newItem])
        if not getattr(self.newItem, "allowShow", True):
            return

        self.newItem.show()
        self.newItem.e_item.deselect()

    @err_catcher(name=__name__)
    def onCreateFolderDlgAccepted(self) -> None:
        """Handle acceptance of the create folder dialog.
        
        Creates the folder and optionally re-opens the dialog if Ctrl was held
        during acceptance (for batch creation).
        """
        if self.entityType == "asset":
            self.createAsset("folder")
            mods = QApplication.keyboardModifiers()
            if mods == Qt.ControlModifier and (not self.newItem.clickedButton or self.newItem.clickedButton.text() != self.newItem.btext):
                self.createAssetDlg("folder", startText=self.newItem.e_item.text())

        elif self.entityType == "shot":
            self.createShot("folder")
            mods = QApplication.keyboardModifiers()
            if mods == Qt.ControlModifier and (not self.newItem.clickedButton or self.newItem.clickedButton.text() != self.newItem.btext):
                self.createShotDlg("folder", startText=self.newItem.e_item.text())

    @err_catcher(name=__name__)
    def createAssetDlg(self, entityType: str, startText: Optional[str] = None) -> None:
        """Show dialog to create a new asset or asset folder.
        
        Opens the appropriate creation dialog based on entity type.
        
        Args:
            entityType: Type of entity to create ('asset' or 'folder')
            startText: Initial text to populate in the name field
        """
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
            self.newItem = ProjectWidgets.CreateFolderDlg(self.core, parent=self, startText=startText)
            self.newItem.accepted.connect(lambda: self.onCreateAssetDlgAccepted(entityType))

        self.core.callback(name="onAssetDlgOpen", args=[self, self.newItem])
        if not getattr(self.newItem, "allowShow", True):
            return

        self.newItem.show()
        self.newItem.e_item.deselect()

    @err_catcher(name=__name__)
    def onCreateAssetDlgAccepted(self, entityType: str) -> None:
        """Handle acceptance of the create asset dialog.
        
        Creates the asset and optionally re-opens the dialog if Ctrl was held
        during acceptance (for batch creation).
        
        Args:
            entityType: Type of entity being created ('asset' or 'folder')
        """
        self.createAsset(entityType)
        mods = QApplication.keyboardModifiers()
        if mods == Qt.ControlModifier and (not self.newItem.clickedButton or self.newItem.clickedButton.text() != self.newItem.btext):
            self.createAssetDlg(entityType, startText=self.newItem.e_item.text())

    @err_catcher(name=__name__)
    def createAsset(self, entityType: str) -> None:
        """Create a new asset or asset folder in the project.
        
        Validates the asset name, creates the entity on disk, optionally creates
        tasks from a preset, and navigates to the new entity.
        
        Args:
            entityType: Type of entity to create ('asset' or 'folder')
        """
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
            if entityType == "folder" and not self.core.entities.isValidAssetName(data["asset"]) and os.path.dirname(data["asset_path"]):
                msg = "\"%s\" is not a valid foldername, because it will turn the parent folder into an asset." % data["asset"]
                result = self.core.popupQuestion(msg, buttons=["Continue", "Cancel"], icon=QMessageBox.Warning)
                if result != "Continue":
                    continue

            description = None
            preview = None
            metaData = None
            if entityType == "asset":
                descr = self.newItem.getDescription()
                if descr:
                    description = descr

                thumb = self.newItem.getThumbnail()
                if thumb:
                    preview = thumb

                metaData = self.newItem.w_meta.getMetaData()

            result = self.core.entities.createEntity(data, description=description, preview=preview, metaData=metaData, dialog=self.newItem)
            assetPath = os.path.join(path, entityName)
            if entityType == "asset":
                if self.newItem.chb_taskPreset.isChecked():
                    self.core.entities.createTasksFromPreset(data, self.newItem.cb_taskPreset.currentData())

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
    def createShot(self, entityType: str) -> None:
        """Create a new shot or shot folder in the project.
        
        Validates the shot name, creates the entity on disk, sets description and
        preview if provided, optionally creates tasks from a preset, and navigates
        to the new shot.
        
        Args:
            entityType: Type of entity to create ('shot' or 'folder')
        """
        self.activateWindow()
        assetNames = self.newItem.e_item.text().replace(os.pathsep, ",").split(",")
        entityNames = [path.strip() for path in assetNames]
        for entityName in entityNames:
            path = self.core.sequencePath
            data = {
                "type": "shotFolder" if entityType == "folder" else entityType,
                "shot_path": entityName,
                "shot": os.path.basename(entityName)
            }
            result = self.core.entities.createEntity(data, dialog=self.newItem)
            assetPath = os.path.join(path, entityName)
            if entityType == "shot":
                descr = self.newItem.getDescription()
                if descr:
                    self.core.entities.setShotDescription(os.path.basename(entityName), descr)

                thumb = self.newItem.getThumbnail()
                if thumb:
                    self.core.entities.setEntityPreview(data, thumb)

                self.newItem.w_meta.save(data)

                if self.newItem.chb_taskPreset.isChecked():
                    self.core.entities.createTasksFromPreset(data, self.newItem.cb_taskPreset.currentData())

            self.refreshEntities()
            self.navigate(data=data)
            if not result or not result.get("entity", "") or result.get("existed", ""):
                return

            if self.newItem.clickedButton and self.newItem.clickedButton.text() == self.newItem.btext:
                data["action"] = "next"
                if entityType == "folder":
                    mods = QApplication.keyboardModifiers()
                    if mods == Qt.ControlModifier:
                        self.createShotDlg("shot")
                    else:
                        self.createShotDlg("folder")

            if "paths" not in data:
                data["paths"] = []

            data["paths"].append(assetPath)
            self.entityCreated.emit(data)

    @err_catcher(name=__name__)
    def shotCreated(self, shotData: Dict[str, Any]) -> None:
        """Handle shot creation completion.
        
        Refreshes the shot list, navigates to the new shot, and emits the
        entityCreated signal.
        
        Args:
            shotData: Dictionary containing the created shot's data
        """
        self.refreshShots()

        seqName = shotData["sequence"]
        shotName = shotData["shot"]

        self.navigate({"type": "shot", "sequence": seqName, "shot": shotName})
        self.entityCreated.emit(shotData)

    @err_catcher(name=__name__)
    def editShotDlg(self, shotData: Optional[Dict[str, Any]] = None) -> None:
        """Show dialog to edit or create a shot.
        
        Opens the EditShot dialog with the specified shot data or current selection.
        
        Args:
            shotData: Shot data to edit (uses current selection if None)
        """
        sequs = []
        for seqName in self.getTopLevelItemNames():
            sequs.append(seqName)

        if not shotData:
            sData = self.getCurrentData()
            if isinstance(sData, list) and len(sData) == 1:
                sData = sData[0]

            if not isinstance(sData, dict):
                return

            if sData and sData.get("sequence"):
                shotData = {"sequence": sData["sequence"]}
                if sData.get("episode"):
                    shotData["episode"] = sData["episode"]

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
    def getItems(self, parent: Optional[Any] = None, items: Optional[List[Any]] = None) -> List[Any]:
        """Get all tree widget items recursively.
        
        Args:
            parent: Parent item to start from (None for root level)
            items: Accumulator list for recursive collection
            
        Returns:
            List of all QTreeWidgetItems in the tree
        """
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
    def selectItemType(self, itemType: str) -> None:
        """Select all items of a specific type in the tree.
        
        Args:
            itemType: Type of items to select (e.g., 'asset', 'shot', 'assetFolder')
        """
        self.tw_tree.selectionModel().clearSelection()
        items = self.getItems()
        for item in items:
            data = item.data(0, Qt.UserRole)
            if data.get("type") == itemType:
                item.setSelected(True)

    @err_catcher(name=__name__)
    def getCurrentData(self, returnOne: bool = True) -> Any:
        """Get data from currently selected tree items.
        
        Args:
            returnOne: If True, return single item or default; if False, return list
            
        Returns:
            Entity data dictionary (if returnOne=True) or list of dictionaries
        """
        items = self.tw_tree.selectedItems()
        curData = []

        for item in items:
            data = self.getDataFromItem(item)
            curData.append(data)

        if returnOne:
            if curData:
                curData = curData[0]
            else:
                curData = {"type": self.entityType}

        return curData

    @err_catcher(name=__name__)
    def getDataFromItem(self, item: Any) -> Dict[str, Any]:
        """Extract entity data from a tree widget item.
        
        Args:
            item: Tree widget item to extract data from
            
        Returns:
            Entity data dictionary with type and relevant entity information
        """
        data = {}
        data = item.data(0, Qt.UserRole)
        if "type" not in data:
            data["type"] = self.entityType

        if data["type"] == "shot" and not data.get("shot"):
            data["type"] = "sequence"

        return data

    @err_catcher(name=__name__)
    def getTopLevelItemNames(self) -> List[str]:
        """Get names of all top-level items in the tree.
        
        Returns:
            List of names from top-level tree items
        """
        names = []
        for i in range(self.tw_tree.topLevelItemCount()):
            name = self.tw_tree.topLevelItem(i).text(0)
            names.append(name)

        return names

    @err_catcher(name=__name__)
    def navigate(self, data: Any) -> Optional[bool]:
        """Navigate to and select specific entities in the tree.
        
        Expands the tree hierarchy as needed and selects the specified entities.
        Supports both asset and shot navigation.
        
        Args:
            data: Entity data dictionary or list of dictionaries to navigate to
            
        Returns:
            False if navigation failed, None otherwise
        """
        prevData = self.getCurrentData(returnOne=False)
        wasBlocked = self.tw_tree.signalsBlocked()
        if not wasBlocked:
            self.tw_tree.blockSignals(True)
            self.tw_tree.selectionModel().blockSignals(True)

        self.tw_tree.selectionModel().clearSelection()
        if self.entityType == "asset":
            if not isinstance(data, list):
                data = [data]

            hItem = None
            for asset in data:
                if self.core.isStr(asset):
                    continue

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

                if hItem.isSelected() and self.useCounter:
                    curCount = self.getCount(hItem)
                    if curCount:
                        self.setCount(hItem, curCount + 1)

                if hItem and not self.tw_tree.selectedItems():
                    self.tw_tree.setCurrentItem(hItem)

                if self.core.isObjectValid(hItem):
                    hItem.setSelected(True)
                else:
                    hItem = False

            if hItem:
                self.tw_tree.scrollTo(self.tw_tree.indexFromItem(hItem))

        elif self.entityType == "shot":
            if not isinstance(data, list):
                if not isinstance(data, dict):
                    return False

                data = [data]

            useEpisodes = self.core.getConfig(
                "globals",
                "useEpisodes",
                config="project",
            ) or False
            sItem = None
            for shot in data:
                if useEpisodes:
                    seqParts = [shot.get("episode"), shot.get("sequence")]
                else:
                    if os.getenv("PRISM_USE_SEQUENCE_FOLDERS") == "1":
                        if "hierarchy" in shot:
                            seqParts = shot.get("hierarchy").split("/")
                        else:
                            seqParts = shot.get("sequence", "").split("__")
                    else:
                        seqParts = [shot.get("sequence")]

                shot = shot.get("shot", "")
                if shot and shot != "_sequence":
                    seqParts.append(shot)

                hItem = self.tw_tree.invisibleRootItem()
                for sidx, seqPart in enumerate(seqParts):
                    for idx in range(hItem.childCount() - 1, -1, -1):
                        cItem = hItem.child(idx)
                        if cItem.childCount():
                            if useEpisodes:
                                sdata = cItem.data(0, Qt.UserRole)
                                cItemName = sdata["episode"] if sdata["sequence"] == "_episode" else sdata["sequence"]
                            else:
                                cItemName = cItem.data(0, Qt.UserRole)["sequence"]
                        else:
                            cItemData = cItem.data(0, Qt.UserRole)
                            if cItemData.get("shot") == "_sequence":
                                if cItemData.get("sequence") == "_episode":
                                    cItemName = cItemData["episode"]
                                else:
                                    cItemName = cItemData["sequence"]
                            else:
                                cItemName = cItemData["shot"]

                        if cItemName == seqPart:
                            hItem = cItem
                            if len(seqParts) > (sidx + 1):
                                hItem.setExpanded(True)
                                self.itemExpanded(hItem)

                            if self.core.isObjectValid(hItem):
                                hItem.setSelected(True)
                            else:
                                hItem = False

                            sItem = hItem
                            break
                    else:
                        break

            if sItem:
                self.tw_tree.setCurrentItem(sItem)
                self.tw_tree.scrollTo(self.tw_tree.indexFromItem(sItem))

        if not wasBlocked:
            self.tw_tree.blockSignals(False)
            self.tw_tree.selectionModel().blockSignals(False)
            if self.getCurrentData(returnOne=False) != prevData:
                self.onItemChanged()

    @err_catcher(name=__name__)
    def contextMenuTree(self, pos: Any) -> None:
        """Show context menu for tree widget items.
        
        Displays a context menu with actions appropriate for the clicked item,
        including create, edit, refresh, open in explorer, omit, and custom actions.
        
        Args:
            pos: Position where the context menu was requested
        """
        rcmenu = QMenu(self)
        callbackName = ""

        if self.useCounter:
            mods = QApplication.keyboardModifiers()
            if mods == Qt.ControlModifier:
                return

        if self.entityType == "asset":
            cItem = self.tw_tree.itemFromIndex(self.tw_tree.indexAt(pos))
            if cItem is None:
                path = self.core.assetPath
            else:
                path = cItem.data(0, Qt.UserRole)["paths"][0]
            callbackName = "openPBAssetContextMenu"

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
        elif self.entityType == "shot":
            path = self.core.shotPath
            callbackName = "openPBShotContextMenu"

            createAct = QAction("Create Shot...", self)
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
            omitMenu = None
            showOmitted = self.core.getConfig("browser", "showOmittedEntities", config="user", dft=False)
            if self.entityType == "asset":
                if data:
                    isOmitted = self.core.entities.isAssetPathOmitted(data.get("asset_path", ""))
                    omitMenu = QMenu("Omit", self)
                    oActLabel = "Unomit Asset" if isOmitted else "Omit Asset"
                    oAct = QAction(oActLabel, self)
                    oAct.triggered.connect(lambda: self.omitEntity(data, omit=not isOmitted))
                    omitMenu.addAction(oAct)
                    showOmittedAct = QAction("Show Omitted Assets", self)
                    showOmittedAct.setCheckable(True)
                    showOmittedAct.setChecked(showOmitted)
                    showOmittedAct.toggled.connect(self.toggleShowOmitted)
                    omitMenu.addAction(showOmittedAct)
                    listOmittedAct = QAction("List Omitted Assets...", self)
                    listOmittedAct.triggered.connect(self.listOmittedEntitiesDlg)
                    omitMenu.addAction(listOmittedAct)

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
                    isOmitted = self.core.entities.isShotOmitted(data)
                    omitMenu = QMenu("Omit", self)
                    oActLabel = "Unomit Shot" if isOmitted else "Omit Shot"
                    oAct = QAction(oActLabel, self)
                    oAct.triggered.connect(lambda: self.omitEntity(data, omit=not isOmitted))
                    omitMenu.addAction(oAct)
                    showOmittedAct = QAction("Show Omitted Shots", self)
                    showOmittedAct.setCheckable(True)
                    showOmittedAct.setChecked(showOmitted)
                    showOmittedAct.toggled.connect(self.toggleShowOmitted)
                    omitMenu.addAction(showOmittedAct)
                    listOmittedAct = QAction("List Omitted Shots...", self)
                    listOmittedAct.triggered.connect(self.listOmittedEntitiesDlg)
                    omitMenu.addAction(listOmittedAct)
                elif data:
                    path = self.core.paths.getEntityPath(data)

                selectedItems = self.tw_tree.selectedItems()
                if (item.childCount() > 0 and data) or len(selectedItems) > 1:
                    createOtioAct = QAction("Create OTIO...", self)
                    createOtioAct.triggered.connect(lambda: self.openCreateOtioDlg())
                    rcmenu.addAction(createOtioAct)

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
            copAct = self.core.getCopyAction(path, parent=self)
            rcmenu.addAction(copAct)
            if omitMenu:
                rcmenu.addMenu(omitMenu)
        else:
            self.tw_tree.setCurrentIndex(self.tw_tree.model().createIndex(-1, 0))
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
            copAct = self.core.getCopyAction(path, parent=self)
            rcmenu.addAction(copAct)
            showOmitted = self.core.getConfig("browser", "showOmittedEntities", config="user", dft=False)
            if self.entityType == "asset":
                showOmittedAct = QAction("Show Omitted Assets", self)
            else:
                showOmittedAct = QAction("Show Omitted Shots", self)

            showOmittedAct.setCheckable(True)
            showOmittedAct.setChecked(showOmitted)
            showOmittedAct.toggled.connect(self.toggleShowOmitted)
            rcmenu.addAction(showOmittedAct)
            listOmittedAct = QAction("List Omitted %ss..." % self.entityType.capitalize(), self)
            listOmittedAct.triggered.connect(self.listOmittedEntitiesDlg)
            rcmenu.addAction(listOmittedAct)

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
    def runAction(self, action: Dict[str, Any]) -> None:
        """Execute a custom entity action.
        
        Args:
            action: Action dictionary with 'function' key containing the callable
        """
        data = self.getCurrentData(returnOne=False)
        action["function"](entities=data, parent=self.window())

    @err_catcher(name=__name__)
    def openCreateOtioDlg(self) -> None:
        """Collect shots from the current tree selection and open CreateOtioDlg.

        Sequences and episodes are expanded to their child shot items.
        The dialog is opened only when at least one shot is resolved.
        """
        shots = []
        for item in self.tw_tree.selectedItems():
            itemData = item.data(0, Qt.UserRole)
            if not isinstance(itemData, dict):
                continue

            itemType = itemData.get("itemType")
            if itemType == "shot":
                shots.append(itemData)
            elif itemType == "sequence":
                sequence = itemData.get("sequence")
                if os.getenv("PRISM_USE_SEQUENCE_FOLDERS") == "1":
                    sequence = itemData.get("hierarchy", sequence).replace("/", "__")
                seqShots = self.core.entities.getShots(
                    episode=itemData.get("episode"),
                    sequence=sequence,
                )
                shots.extend(seqShots)
            elif itemType == "episode":
                sequences = self.core.entities.getSequences(episode=itemData.get("episode"))
                for seq in sequences:
                    seqShots = self.core.entities.getShots(
                        episode=itemData.get("episode"),
                        sequence=seq.get("sequence"),
                    )
                    shots.extend(seqShots)

        if not shots:
            self.core.popup("No shots found in the current selection.")
            return

        initialEntity = {}
        selectedItems = self.tw_tree.selectedItems()
        if selectedItems:
            initialEntity = self.getDataFromItem(selectedItems[0])

        from PrismUtils.ProjectWidgets import CreateOtioDlg
        dlg = CreateOtioDlg(self.core, shots=shots, entity=initialEntity, parent=self)
        dlg.exec_()

    @err_catcher(name=__name__)
    def openConnectEntitiesDlg(self) -> None:
        """Open dialog to connect entities (assets to shots or vice versa).
        
        Opens the connection dialog or navigates to entities depending on the
        parent widget context.
        """
        data = self.getCurrentData(returnOne=False)
        if self.entityWidget.parent().objectName() == "gb_connectedEntities":
            self.entityWidget.parent().parent().parent().navigate(data)
        else:
            self.core.entities.connectEntityDlg(entities=data, parent=self)

    @err_catcher(name=__name__)
    def listOmittedEntitiesDlg(self) -> None:
        """Show a dialog listing all omitted entities of the current type."""
        self.core.entities.refreshOmittedEntities()
        if self.entityType == "asset":
            title = "Omitted Assets"
            omitted = self.core.entities.omittedEntities.get("asset", [])
            entries = sorted(omitted)
        else:
            title = "Omitted Shots"
            omitted = self.core.entities.omittedEntities.get("shot", {})
            entries = []
            for seq, shots in sorted(omitted.items()):
                for shot in sorted(shots):
                    entries.append("%s / %s" % (seq, shot))

        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.resize(400, 300)

        lo_dlg = QVBoxLayout(dlg)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w_content = QWidget()
        lo_content = QVBoxLayout(w_content)
        lo_content.setAlignment(Qt.AlignTop)

        if entries:
            for entry in entries:
                lo_content.addWidget(QLabel(entry))
        else:
            lo_content.addWidget(QLabel("No omitted %ss found." % self.entityType))

        scroll.setWidget(w_content)
        lo_dlg.addWidget(scroll)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
        btn_box.accepted.connect(dlg.accept)
        lo_dlg.addWidget(btn_box)

        dlg.exec_()
