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
import copy
import datetime
import shutil
import logging
import traceback
import re
import time
import uuid
import platform
from typing import Any, Optional, List, Dict, Tuple

prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

if __name__ == "__main__":
    sys.path.append(os.path.join(prismRoot, "Scripts"))
    import PrismCore

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

uiPath = os.path.join(os.path.dirname(__file__), "UserInterfaces")
if uiPath not in sys.path:
    sys.path.append(uiPath)

import ItemList
import MetaDataWidget
from PrismUtils import PrismWidgets
from PrismUtils.Decorators import err_catcher
from UserInterfaces import SceneBrowser_ui


logger = logging.getLogger(__name__)


class SceneBrowser(QWidget, SceneBrowser_ui.Ui_w_sceneBrowser):
    """Scene browser for managing project scenefiles.
    
    Provides interface for browsing, creating, and managing scenefiles organized by
    entity (assets/shots), department, and task. Supports both list and item grid views
    with filtering, previews, and version management.
    
    Attributes:
        core: Prism core instance.
        projectBrowser: Parent ProjectBrowser instance.
        filteredAssets (List): Filtered asset list.
        scenefileData (List[Dict]): Loaded scenefile information.
        scenefileQueue (List): Queue of scenefiles waiting to be displayed.
        sceneItemWidgets (List): List of ScenefileItem widgets.
        initialized (bool): Whether browser has been initialized.
        lastProcess (float): Timestamp of last QApplication.processEvents call.
        processEventsOnShow (bool): Whether to process events on show.
        shotPrvXres (int): Shot preview width in pixels.
        shotPrvYres (int): Shot preview height in pixels.
        tableColumnLabels (Dict[str, str]): Mapping of column keys to display labels.
        publicColor (QColor): Color for public/global files.
        closeParm (str): Config key for close-after-load setting.
        emptypmapPrv (QPixmap): Empty preview placeholder.
        w_entities: Entity widget for selecting assets/shots.
        lw_departments: List widget for departments.
        lw_tasks: List widget for tasks.
        tw_scenefiles: Table widget for scenefiles (list view).
        w_scenefileItems: Container widget for scenefile items (grid view).
        appFilters (Dict): Application file format filters.
    """
    def __init__(self, core: Any, projectBrowser: Optional[Any] = None, refresh: bool = True) -> None:
        """Initialize the Scene Browser.
        
        Args:
            core: Prism core instance.
            projectBrowser: Optional parent ProjectBrowser instance.
            refresh: Whether to refresh data on initialization.
        """
        QWidget.__init__(self)
        self.setupUi(self)
        self.core = core
        self.projectBrowser = projectBrowser

        logger.debug("Initializing Scene Browser")

        self.core.parentWindow(self)

        self.filteredAssets = []
        self.scenefileData = []
        self.scenefileQueue = []
        self.curSceneThread = None
        self.pendingSceneRefresh = None
        self.staleScenefileWorker = None
        self.sceneItemWidgets = []
        self.initialized = False
        self.lastProcess = -1
        self.processEventsOnShow = True if os.getenv("PRISM_SCENEBROWSER_SKIP_PROCESS_EVENTS", "1") == "0" else False
        self.departmentRefreshId = 0
        self.taskRefreshId = 0
        self.entityListWorkers = []
        self.entityListWorkerCallbacks = {}
        self.entityListWorkerWidgets = {}
        self.pendingNavigationData = None
        self.taskToSelect = None
        self.refreshSelection = None
        self.entityInfoRefreshId = 0
        self.entityInfoWorkers = []
        self.entityInfoWorkerCallbacks = {}

        self.shotPrvXres = 250
        self.shotPrvYres = 141

        self.tableColumnLabels = {
            "Version": self.core.tr("Version"),
            "Comment": self.core.tr("Comment"),
            "Date": self.core.tr("Date"),
            "User": self.core.tr("User"),
            "Name": self.core.tr("Name"),
            "Department": self.core.tr("Department"),
        }

        self.publicColor = QColor(150, 200, 220)
        self.closeParm = "closeafterload"
        self.emptypmapPrv = self.core.media.getFallbackPixmap()
        self.loadLayout()
        self.connectEvents()
        self.core.callback(name="onSceneBrowserOpen", args=[self])

        if refresh:
            self.entered()

    @err_catcher(name=__name__)
    def entered(self, prevTab: Optional[Any] = None, navData: Optional[Dict[str, Any]] = None) -> None:
        """Handle browser activation and navigation.
        
        Called when tab becomes active or when navigating to specific data.
        Initializes entity tree and navigates to specified scenefile.
        
        Args:
            prevTab: Previous tab widget for syncing navigation state.
            navData: Optional navigation data containing entity, department, task, and filename.
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
            if navData and not self.w_entities.navigate(
                navData, deferSelection=True
            ):
                self.w_entities.getCurrentPage().pendingRestoreData = navData
            self.pendingNavigationData = navData
            self.w_entities.refreshEntities(defaultSelection=False)
            self.w_entities.getPage("Assets").blockSignals(False)
            self.w_entities.getPage("Shots").blockSignals(False)
            self.w_entities.tb_entities.blockSignals(False)
            self.w_entities.blockSignals(False)
            if not navData:
                self.entityChanged()

            self.initialized = True

        if prevTab:
            if hasattr(prevTab, "w_entities"):
                self.w_entities.syncFromWidget(prevTab.w_entities, navData=navData)
            elif hasattr(prevTab, "getSelectedData"):
                self.w_entities.navigate(navData)

    @err_catcher(name=__name__)
    def loadLayout(self) -> None:
        """Load and configure the UI layout.
        
        Sets up entity widget, scenefile widgets, table/item views, drag-drop,
        and loads saved browser settings.
        """
        import EntityWidget

        self.w_entities = EntityWidget.EntityWidget(core=self.core, refresh=False)
        self.splitter1.insertWidget(0, self.w_entities)

        self.tw_scenefiles.setShowGrid(False)

        self.w_scenefileItems = QWidget()
        self.w_scenefileItems.setObjectName("itemview")
        self.lo_scenefileItems = QVBoxLayout()
        self.w_scenefileItems.setLayout(self.lo_scenefileItems)
        self.sa_scenefileItems.setWidget(self.w_scenefileItems)
        self.sa_scenefileItems.setWidgetResizable(True)
        self.sa_scenefileItems.verticalScrollBar().valueChanged.connect(self.onScrolled)
        # self.sa_scenefileItems.setStyleSheet("QScrollArea { border: 0px}")

        self.lw_departments.setIconSize(QSize(16, 16))

        cData = self.core.getConfig()
        brsData = cData.get("browser", {})
        self.refreshAppFilters(browserData=brsData)
        self.b_scenefilter.setToolTip(
            self.core.tr("Filter scenefiles (hold CTRL to toggle multiple types)")
        )

        sceneSort = brsData.get("scenefileSorting", [1, 1])
        self.tw_scenefiles.sortByColumn(sceneSort[0], Qt.SortOrder(sceneSort[1]))

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

        if "scenefileLayout" in brsData:
            if brsData["scenefileLayout"] == "items":
                self.sceneLayoutItemsToggled(False, refresh=False)
            elif brsData["scenefileLayout"] == "list":
                self.sceneLayoutListToggled(False, refresh=False)
        else:
            self.sceneLayoutItemsToggled(False, refresh=False)

        if self.projectBrowser and self.projectBrowser.act_rememberWidgetSizes.isChecked():
            if "scenefileSplitter1" in brsData:
                self.splitter1.setSizes(brsData["scenefileSplitter1"])

            if "scenefileSplitter2" in brsData:
                self.splitter2.setSizes(brsData["scenefileSplitter2"])

            if "scenefileSplitter3" in brsData:
                self.splitter3.setSizes(brsData["scenefileSplitter3"])

        if self.core.compareVersions(self.core.projectVersion, "v1.2.1.6") == "lower":
            self.w_tasks.setVisible(False)

        self.tw_scenefiles.setAcceptDrops(True)
        self.tw_scenefiles.dragEnterEvent = self.sceneDragEnterEvent
        self.tw_scenefiles.dragMoveEvent = self.sceneDragMoveEvent
        self.tw_scenefiles.dragLeaveEvent = self.sceneDragLeaveEvent
        self.tw_scenefiles.dropEvent = self.sceneDropEvent

        self.w_scenefileItems.setAcceptDrops(True)
        self.w_scenefileItems.dragEnterEvent = self.sceneDragEnterEvent
        self.w_scenefileItems.dragMoveEvent = self.sceneDragMoveEvent
        self.w_scenefileItems.dragLeaveEvent = self.sceneDragLeaveEvent
        self.w_scenefileItems.dropEvent = self.sceneDropEvent
        self.initScenesLoadingWidget()
        self.initEntityListLoadingWidgets()
        self.setStyleSheet(
            'QSplitter::handle{background-image: "";background-color: transparent}'
        )
        self.sw_scenefiles.setObjectName("transparent")
        self.sw_scenefiles.setStyleSheet(
            "QWidget#transparent{background-color: transparent}"
        )
        delegate = DateDelegate()
        delegate.core = self.core
        self.tw_scenefiles.setItemDelegateForColumn(3, delegate)

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "list.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.b_sceneLayoutList.setIcon(icon)

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "items.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.b_sceneLayoutItems.setIcon(icon)

        path = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "user.png")
        icon = self.core.media.getColoredIcon(path)
        self.pmapUser = icon.pixmap(15, 15)

        path = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "date.png")
        icon = self.core.media.getColoredIcon(path)
        self.pmapDate = icon.pixmap(15, 15)

        if self.core.useTranslation:
            self.l_departments.setText(self.core.tr("Departments:"))
            self.l_tasks.setText(self.core.tr("Tasks:"))

        if hasattr(QApplication.instance(), "styleSheet"):
            ssheet = QApplication.instance().styleSheet()
            ssheet = ssheet.replace("QScrollArea", "Qdisabled")
            ssheet = ssheet.replace("QListView", "QScrollArea")
            self.sa_scenefileItems.setStyleSheet(ssheet)

    @err_catcher(name=__name__)
    def refreshAppFilters(self, browserData: Optional[Dict[str, Any]] = None) -> None:
        """Refresh application file format filters.
        
        Builds filter dictionary from plugin scene formats.
        
        Args:
            browserData: Optional browser configuration data.
        """
        if browserData is None:
            cData = self.core.getConfig()
            browserData = cData.get("browser", {})

        self.appFilters = {}

        for pluginName in self.core.getPluginNames():
            if len(self.core.getPluginData(pluginName, "sceneFormats")) == 0:
                continue

            self.appFilters[pluginName] = {
                "formats": self.core.getPluginData(pluginName, "sceneFormats"),
                "show": True,
            }

        self.appFilters["Other"] = {
            "formats": "*",
            "show": True,
        }

        for pluginName in self.appFilters:
            if "sceneFilter" in browserData and pluginName in browserData["sceneFilter"]:
                self.appFilters[pluginName]["show"] = browserData["sceneFilter"][pluginName]

        self.refreshAppFilterIndicator()

    @err_catcher(name=__name__)
    def showEvent(self, event: Any) -> None:
        """Handle show event.
        
        Aligns header heights and validates visible scenefile items.
        
        Args:
            event: Show event.
        """
        spacing = self.w_departmentsHeader.layout().spacing()
        h = max(
            self.w_scenefileHeader.geometry().height(),
            self.w_entities.w_header.geometry().height() - spacing,
        )
        self.w_departmentsHeader.setMinimumHeight(h)
        self.w_tasksHeader.setMinimumHeight(h)
        self.w_entities.w_header.setMinimumHeight(h + spacing)
        self.w_scenefileHeader.setMinimumHeight(h)
        self.w_scenefileHeader.setMaximumHeight(h)
        if self.core.pb and self.core.pb == self.projectBrowser:
            if hasattr(self.core.pb, "productBrowser"):
                self.core.pb.productBrowser.setHeaderHeight(h)

            if hasattr(self.core.pb, "mediaBrowser"):
                self.core.pb.mediaBrowser.setHeaderHeight(h)

        refreshId = uuid.uuid4().hex
        self.prevRefreshId = refreshId
        self.validateVisibleScenefileItems(processEvents=self.processEventsOnShow)

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect UI signals to handler methods.
        
        Sets up event connections for entity changes, mouse clicks, double-clicks,
        context menus, and drag-drop operations.
        """
        self.w_entities.getPage("Assets").itemChanged.connect(self.entityChanged)
        self.w_entities.getPage("Shots").itemChanged.connect(self.entityChanged)
        self.w_entities.getPage("Assets").entityCreated.connect(self.entityCreated)
        self.w_entities.getPage("Shots").entityCreated.connect(self.entityCreated)

        self.w_entities.getPage("Shots").shotSaved.connect(self.refreshShotinfo)
        self.w_entities.getPage("Shots").nextClicked.connect(self.createDepartmentDlg)

        self.w_entities.tabChanged.connect(self.sceneTabChanged)

        self.lw_departments.mouseClickEvent = self.lw_departments.mouseReleaseEvent
        self.lw_departments.mouseReleaseEvent = lambda x: self.mouseClickEvent(
            x, self.lw_departments
        )
        self.lw_departments.mouseDClick = self.lw_departments.mouseDoubleClickEvent
        self.lw_departments.mouseDoubleClickEvent = lambda x: self.mousedb(
            x, self.lw_departments
        )
        self.lw_departments.currentItemChanged.connect(self.departmentChanged)
        self.lw_departments.customContextMenuRequested.connect(
            lambda x: self.rightClickedList(self.lw_departments, x)
        )

        self.lw_tasks.mouseClickEvent = self.lw_tasks.mouseReleaseEvent
        self.lw_tasks.mouseReleaseEvent = lambda x: self.mouseClickEvent(
            x, self.lw_tasks
        )
        self.lw_tasks.mouseDClick = self.lw_tasks.mouseDoubleClickEvent
        self.lw_tasks.mouseDoubleClickEvent = lambda x: self.mousedb(x, self.lw_tasks)
        self.lw_tasks.currentItemChanged.connect(self.taskChanged)
        self.lw_tasks.customContextMenuRequested.connect(
            lambda x: self.rightClickedList(self.lw_tasks, x)
        )

        self.tw_scenefiles.mouseClickEvent = self.tw_scenefiles.mouseReleaseEvent
        self.tw_scenefiles.mouseReleaseEvent = lambda x: self.mouseClickEvent(
            x, self.tw_scenefiles
        )
        self.tw_scenefiles.mouseDClick = self.tw_scenefiles.mouseDoubleClickEvent
        self.tw_scenefiles.mouseDoubleClickEvent = lambda x: self.sceneAreaDoubleClicked(
            x, self.tw_scenefiles
        )
        self.tw_scenefiles.customContextMenuRequested.connect(self.rclFile)
        self.tw_scenefiles.doubleClicked.connect(self.sceneDoubleClicked)
        self.tw_scenefiles.setMouseTracking(True)
        self.tw_scenefiles.mouseMoveEvent = lambda x: self.tableMoveEvent(x)
        self.tw_scenefiles.leaveEvent = lambda x: self.tableLeaveEvent(x)
        self.tw_scenefiles.focusOutEvent = lambda x: self.tableFocusOutEvent(x)
        self.tw_scenefiles.verticalScrollBar().valueChanged.connect(
            self.onScenefileListScrolled
        )
        self.tw_scenefiles.horizontalHeader().sortIndicatorChanged.connect(
            lambda section, order: self.validateVisibleScenefileRows()
        )

        self.gb_entityInfo.mouseDoubleClickEvent = lambda x: self.editEntity()
        self.gb_entityInfo.customContextMenuRequested.connect(self.rclEntityPreview)
        self.l_entityPreview.customContextMenuRequested.connect(self.rclEntityPreview)

        self.b_sceneLayoutItems.toggled.connect(self.sceneLayoutItemsToggled)
        self.b_sceneLayoutList.toggled.connect(self.sceneLayoutListToggled)
        self.b_scenefilter.clicked.connect(self.showSceneFilterMenu)

        self.sa_scenefileItems.mouseClickEvent = (
            self.sa_scenefileItems.mouseReleaseEvent
        )
        self.sa_scenefileItems.mouseReleaseEvent = self.mouseClickItemViewEvent
        self.sa_scenefileItems.mouseDClick = self.sa_scenefileItems.mouseDoubleClickEvent
        self.sa_scenefileItems.mouseDoubleClickEvent = lambda x: self.sceneAreaDoubleClicked(
            x, self.sa_scenefileItems
        )
        self.sa_scenefileItems.customContextMenuRequested.connect(self.rclItemView)

    @err_catcher(name=__name__)
    def saveSettings(self, data: Dict[str, Any]) -> None:
        """Save browser settings to configuration.
        
        Args:
            data: Configuration dictionary to update with browser settings.
        """
        sortOrderObj = self.tw_scenefiles.horizontalHeader().sortIndicatorOrder()
        if hasattr(sortOrderObj, "value"):
            sortOrder = sortOrderObj.value
        else:
            try:
                sortOrder = int(sortOrderObj)
            except (TypeError, ValueError):
                sortOrder = 0 if sortOrderObj == Qt.AscendingOrder else 1

        data["browser"]["scenefileSorting"] = [
            self.tw_scenefiles.horizontalHeader().sortIndicatorSection(),
            sortOrder,
        ]
        data["browser"][
            "expandedAssets_" + self.core.projectName
        ] = self.w_entities.getPage("Assets").getExpandedItems()
        data["browser"][
            "expandedSequences_" + self.core.projectName
        ] = self.w_entities.getPage("Shots").getExpandedItems()
        data["browser"]["showAssetSearch"] = self.w_entities.getPage(
            "Assets"
        ).isSearchVisible()
        data["browser"]["showShotSearch"] = self.w_entities.getPage(
            "Shots"
        ).isSearchVisible()
        data["browser"]["sceneFilter"] = {}

        layout = "list" if self.b_sceneLayoutList.isChecked() else "items"
        data["browser"]["scenefileLayout"] = layout

        data["browser"]["sceneFilter"] = {}
        for pluginName in getattr(self, "appFilters", []):
            data["browser"]["sceneFilter"][pluginName] = self.appFilters[pluginName][
                "show"
            ]

        data["browser"]["scenefileSplitter1"] = self.splitter1.sizes()
        data["browser"]["scenefileSplitter2"] = self.splitter2.sizes()
        data["browser"]["scenefileSplitter3"] = self.splitter3.sizes()

    @err_catcher(name=__name__)
    def getCurrentNavData(self) -> Dict[str, Any]:
        """Get navigation data for current file.
        
        Returns:
            Dictionary with scenefile data from current file.
        """
        fileName = self.core.getCurrentFileName()
        navData = self.core.getScenefileData(fileName)
        return navData

    @err_catcher(name=__name__)
    def navigateToCurrent(self) -> bool:
        """Navigate to the current file.
        
        Returns:
            True if navigation was successful.
        """
        navData = self.getCurrentNavData()
        return self.navigate(navData)

    @err_catcher(name=__name__)
    def navigate(self, data: Optional[Dict[str, Any]]) -> Optional[bool]:
        """Navigate to specific entity, department, task, and scenefile.
        
        Args:
            data: Navigation data dictionary with entity, department, task, filename keys.
            
        Returns:
            True if navigation was queued, None if data invalid.
        """
        if not isinstance(data, dict):
            return

        self.pendingNavigationData = data.copy()
        self._navigatingEntity = True
        try:
            entity = data.copy()
            if entity.get("type") in ["sequence", "episode"]:
                entity["type"] = "shot"

            result = self.w_entities.navigate(entity, deferSelection=True)
            if result is False:
                self.w_entities.getCurrentPage().pendingRestoreData = entity
                return True
        finally:
            self._navigatingEntity = False

        self.entityChanged()
        return True

    @err_catcher(name=__name__)
    def _applyNavigation(self, data: Dict[str, Any]) -> Optional[bool]:
        """Apply navigation after the entity's department and task lists load."""
        prevEntities = self.getCurrentEntities()
        if len(prevEntities) == 1:
            prevEntity = prevEntities[0]
        else:
            prevEntity = None

        prevDep = self.getCurrentDepartment()
        self.lw_departments.blockSignals(True)

        if not data.get("department"):
            self.lw_departments.blockSignals(False)
            if prevDep != self.getCurrentDepartment() or prevEntity != self.getCurrentEntity():
                self.departmentChanged()

            return True

        longDep = self.core.entities.getLongDepartmentName(data.get("type"), data["department"]) or data["department"]
        fItems = self.lw_departments.findItems(longDep, Qt.MatchExactly)
        if not fItems:
            self.lw_departments.blockSignals(False)
            if prevDep != self.getCurrentDepartment() or prevEntity != self.getCurrentEntity():
                self.departmentChanged()

            return

        self.lw_departments.setCurrentItem(fItems[0])
        self.lw_departments.blockSignals(False)
        prevTask = self.getCurrentTask()
        self.lw_tasks.blockSignals(True)
        if prevDep != self.getCurrentDepartment() or prevEntity != self.getCurrentEntity():
            self.departmentChanged()

        if not data.get("task"):
            self.lw_tasks.blockSignals(False)
            if prevTask != self.getCurrentTask():
                self.taskChanged()

            return True

        fItems = self.lw_tasks.findItems(data["task"], Qt.MatchExactly)
        if not fItems:
            self.lw_tasks.blockSignals(False)
            if prevTask != self.getCurrentTask():
                self.taskChanged()

            return

        self.lw_tasks.setCurrentItem(fItems[0])
        self.lw_tasks.blockSignals(False)
        if prevTask != self.getCurrentTask():
            self.taskChanged()

        if os.path.isabs(data.get("filename") or ""):
            curFname = data["filename"]
            if self.curSceneThread:
                self.scenefileToSelect = curFname
            else:
                self.selectScenefile(curFname)

        return True

    @err_catcher(name=__name__)
    def selectScenefile(self, curFname: str) -> None:
        """Select a specific scenefile by path.
        
        Args:
            curFname: Scenefile path to select.
        """
        globalCurFname = self.core.convertPath(curFname, "global")
        if self.b_sceneLayoutItems.isChecked():
            for widget in self.sceneItemWidgets:
                cmpFname = os.path.normpath(widget.data["filename"])
                if cmpFname in [curFname, globalCurFname]:
                    widget.select()
                    self.sa_scenefileItems.ensureWidgetVisible(widget)
                    break
        else:
            if not self.tw_scenefiles.model():
                return

            for idx in range(self.tw_scenefiles.model().rowCount()):
                cmpFname = (
                    self.tw_scenefiles.model().index(idx, 0).data(Qt.UserRole)
                )
                cmpFname = os.path.normpath(cmpFname)
                if cmpFname in [curFname, globalCurFname]:
                    idx = self.tw_scenefiles.model().index(idx, 0)
                    self.tw_scenefiles.selectRow(idx.row())
                    break

    @err_catcher(name=__name__)
    def sceneTabChanged(self) -> None:
        """Handle entity tab (Assets/Shots) change.
        """
        self.entityChanged()

    @err_catcher(name=__name__)
    def entityChanged(self, item: Optional[Any] = None) -> None:
        """Handle entity selection change.
        
        Refreshes entity info and departments list.
        
        Args:
            item: Optional tree item that changed.
        """
        if getattr(self, "_navigatingEntity", False):
            return

        if self.pendingNavigationData:
            pendingEntity = self.pendingNavigationData
            currentEntity = self.getCurrentEntity() or {}
            pendingType = pendingEntity.get("type")
            if pendingType in ["asset", "assetFolder"]:
                matchesPendingEntity = (
                    currentEntity.get("type") in ["asset", "assetFolder"]
                    and (currentEntity.get("asset_path") or "").replace("\\", "/")
                    == (pendingEntity.get("asset_path") or "").replace("\\", "/")
                )
            elif pendingType in ["shot", "sequence", "episode"]:
                matchesPendingEntity = (
                    currentEntity.get("sequence")
                    == pendingEntity.get("sequence")
                    and currentEntity.get("shot") == pendingEntity.get("shot")
                    and currentEntity.get("episode")
                    == pendingEntity.get("episode")
                )
            else:
                matchesPendingEntity = False

            isLoadingShotParent = (
                pendingType == "shot"
                and pendingEntity.get("shot") not in [None, "", "_sequence"]
                and currentEntity.get("type") == "shot"
                and currentEntity.get("shot") == "_sequence"
                and currentEntity.get("loaded") == "loading"
                and (
                    currentEntity.get("sequence") == pendingEntity.get("sequence")
                    or (
                        pendingEntity.get("episode")
                        and currentEntity.get("sequence") == "_episode"
                        and currentEntity.get("episode") == pendingEntity.get("episode")
                    )
                )
            )
            isIncompleteAsset = (
                pendingType in ["asset", "assetFolder"]
                and currentEntity.get("type") in ["asset", "assetFolder"]
                and not currentEntity.get("asset_path")
            )
            if (
                currentEntity
                and not isIncompleteAsset
                and not isLoadingShotParent
                and not matchesPendingEntity
            ):
                self.pendingNavigationData = None

        if self.pendingNavigationData and isLoadingShotParent:
            return

        self.refreshEntityInfo()
        self.refreshDepartments(restoreSelection=True)

    @err_catcher(name=__name__)
    def entityCreated(self, data: Dict[str, Any]) -> None:
        """Handle entity creation callback.
        
        Args:
            data: Entity creation data including type and action.
        """
        if data.get("type", "") == "asset":
            if data.get("action") == "next":
                self.createDepartmentDlg()

        elif data.get("type", "") == "shot":
            if self.core.uiAvailable:
                shotName = data["shot"]
                seqName = data["sequence"]

                page = self.w_entities.getCurrentPage()
                page.navigate({"type": "shot", "sequence": seqName, "shot": shotName})

    @err_catcher(name=__name__)
    def mousedb(self, event: Any, widget: Any) -> None:
        """Handle mouse double-click on department or task lists.
        
        Opens creation dialogs when double-clicking empty space.
        
        Args:
            event: Mouse event.
            widget: List widget that was double-clicked.
        """
        entity = self.getCurrentEntity()
        if not entity or (entity.get("type") == "asset" and not entity.get("asset_path")) or (entity.get("type") == "shot" and not entity.get("shot")):
            return

        widgetType = "department" if widget == self.lw_departments else "task"
        if entity["type"] == "asset" and widgetType == "department":
            self.createDepartmentDlg()
        elif entity["type"] == "asset" and widgetType == "task":
            if (
                self.getCurrentDepartment()
                and not self.lw_tasks.indexAt(event.pos()).data()
            ):
                self.createTaskDlg()
        elif entity["type"] in ["shot", "sequence"] and widgetType == "department":
            if entity["shot"] and not self.lw_departments.indexAt(event.pos()).data():
                self.createDepartmentDlg()
        elif entity["type"] in ["shot", "sequence"] and widgetType == "task":
            if (
                self.getCurrentDepartment()
                and not self.lw_tasks.indexAt(event.pos()).data()
            ):
                self.createTaskDlg()

        widget.mouseDClick(event)

    @err_catcher(name=__name__)
    def mouseClickEvent(self, event: Any, widget: Any) -> None:
        """Handle mouse click events.
        
        Clears selection on empty space and copies scenefile paths on middle-click.
        
        Args:
            event: Mouse event.
            widget: Widget that received click.
        """
        if event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.MiddleButton and widget is self.tw_scenefiles:
                index = widget.indexAt(event.pos())
                if index.isValid():
                    filepath = widget.model().index(index.row(), 0).data(Qt.UserRole)
                    if filepath:
                        self.core.copyToClipboard(filepath)
                event.accept()
            elif event.button() == Qt.LeftButton:
                index = widget.indexAt(event.pos())
                if index.data() is None:
                    widget.setCurrentIndex(
                        widget.model().createIndex(-1, 0)
                    )

                widget.mouseClickEvent(event)

    @err_catcher(name=__name__)
    def mouseClickItemViewEvent(self, event: Any) -> None:
        """Handle mouse click in item view.
        
        Deselects all items when clicking empty space.
        
        Args:
            event: Mouse event.
        """
        if event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                self.deselectItems()

    @err_catcher(name=__name__)
    def tableMoveEvent(self, event: Any) -> None:
        """Handle mouse move over scenefiles table.
        
        Shows detail window with preview and info.
        
        Args:
            event: Mouse move event.
        """
        self.showDetailWin(event)
        if hasattr(self, "detailWin") and self.detailWin.isVisible():
            self.detailWin.move(QCursor.pos().x() + 20, QCursor.pos().y())

    @err_catcher(name=__name__)
    def showDetailWin(self, event: Any) -> None:
        """Show hover detail window for a scenefile.
        
        Displays preview image and scenefile info in a floating window.
        
        Args:
            event: Mouse event with position.
        """
        index = self.tw_scenefiles.indexAt(event.pos())
        if index.data() is None:
            if hasattr(self, "detailWin") and self.detailWin.isVisible():
                self.detailWin.close()
            return

        scenePath = self.tw_scenefiles.model().index(index.row(), 0).data(Qt.UserRole)
        if scenePath is None:
            if hasattr(self, "detailWin") and self.detailWin.isVisible():
                self.detailWin.close()
            return

        infoPath = (
            os.path.splitext(scenePath)[0]
            + "versioninfo"
            + self.core.configs.getProjectExtension()
        )
        prvPath = os.path.splitext(scenePath)[0] + "preview.jpg"

        if (
            not hasattr(self, "detailWin")
            or not self.detailWin.isVisible()
            or self.detailWin.scenePath != scenePath
        ):
            if hasattr(self, "detailWin"):
                self.detailWin.close()

            self.detailWin = QFrame()

            ss = getattr(self.core.appPlugin, "getFrameStyleSheet", lambda x: "")(self)
            self.detailWin.setStyleSheet(
                ss + """ .QFrame{ border: 2px solid rgb(100,100,100);} """
            )

            self.detailWin.scenePath = scenePath
            self.core.parentWindow(self.detailWin)
            winwidth = 320
            winheight = 10
            VBox = QVBoxLayout()
            if os.path.exists(prvPath):
                imgmap = self.core.media.getPixmapFromPath(prvPath)
                if imgmap:
                    l_prv = QLabel()
                    l_prv.setPixmap(imgmap)
                    l_prv.setStyleSheet(
                        """
                        border: 1px solid rgb(100,100,100);
                    """
                    )
                    VBox.addWidget(l_prv)

            w_info = QWidget()
            GridL = QGridLayout()
            GridL.setColumnStretch(1, 1)
            rc = 0
            sPathL = QLabel("Scene:\t")
            sPath = QLabel(os.path.basename(scenePath))
            GridL.addWidget(sPathL, rc, 0, Qt.AlignLeft)
            GridL.addWidget(sPath, rc, 1, Qt.AlignLeft)
            rc += 1
            if os.path.exists(infoPath):
                sceneInfo = self.core.getConfig(configPath=infoPath)
                if sceneInfo is None:
                    sceneInfo = {}
                if "username" in sceneInfo:
                    unameL = QLabel("User:\t")
                    uname = QLabel(sceneInfo["username"])
                    GridL.addWidget(unameL, rc, 0, Qt.AlignLeft)
                    GridL.addWidget(uname, rc, 1, Qt.AlignLeft)
                    GridL.addWidget(uname, rc, 1, Qt.AlignLeft)
                    rc += 1
                if "description" in sceneInfo and sceneInfo["description"] != "":
                    descriptionL = QLabel(self.core.tr("Description:") + "\t")
                    description = QLabel(sceneInfo["description"])
                    GridL.addWidget(descriptionL, rc, 0, Qt.AlignLeft | Qt.AlignTop)
                    GridL.addWidget(description, rc, 1, Qt.AlignLeft)
                    rc += 1

            if self.projectBrowser.act_filesizes.isChecked():
                if os.path.exists(scenePath):
                    size = float(os.stat(scenePath).st_size / 1024.0 / 1024.0)
                else:
                    size = 0

                sizeStr = "%.2f mb" % size

                sizeL = QLabel(self.core.tr("Size") + ":\t")
                size = QLabel(sizeStr)
                GridL.addWidget(sizeL, rc, 0, Qt.AlignLeft | Qt.AlignTop)
                GridL.addWidget(size, rc, 1, Qt.AlignLeft)

            w_info.setLayout(GridL)
            GridL.setContentsMargins(0, 0, 0, 0)
            VBox.addWidget(w_info)
            self.detailWin.setLayout(VBox)
            self.detailWin.setWindowFlags(
                Qt.FramelessWindowHint  # hides the window controls
                | Qt.WindowStaysOnTopHint  # forces window to top... maybe
                | Qt.SplashScreen  # this one hides it from the task bar!
            )
            self.detailWin.setAttribute(Qt.WA_ShowWithoutActivating)
            self.detailWin.setGeometry(0, 0, winwidth, winheight)
            self.detailWin.move(QCursor.pos().x() + 20, QCursor.pos().y())
            self.detailWin.show()

    @err_catcher(name=__name__)
    def tableLeaveEvent(self, event: Any) -> None:
        """Handle mouse leaving scenefiles table.
        
        Closes detail window if visible.
        
        Args:
            event: Leave event.
        """
        if hasattr(self, "detailWin") and self.detailWin.isVisible():
            self.detailWin.close()

    @err_catcher(name=__name__)
    def tableFocusOutEvent(self, event: Any) -> None:
        """Handle focus loss on scenefiles table.
        
        Closes detail window if visible.
        
        Args:
            event: Focus out event.
        """
        if hasattr(self, "detailWin") and self.detailWin.isVisible():
            self.detailWin.close()

    @err_catcher(name=__name__)
    def sceneLayoutItemsToggled(self, state: bool, refresh: bool = True) -> None:
        """Handle item layout button toggle.
        
        Switches to grid item view.
        
        Args:
            state: Toggle state.
            refresh: Whether to refresh scenefile display.
        """
        if state:
            self.b_sceneLayoutList.blockSignals(True)
            self.b_sceneLayoutList.setChecked(False)
            self.b_sceneLayoutList.blockSignals(False)
        else:
            self.b_sceneLayoutItems.blockSignals(True)
            self.b_sceneLayoutItems.setChecked(True)
            self.b_sceneLayoutItems.blockSignals(False)

        self.sw_scenefiles.setCurrentIndex(1)
        if refresh:
            self.refreshScenefilesThreaded(reloadFiles=False)

    @err_catcher(name=__name__)
    def sceneLayoutListToggled(self, state: bool, refresh: bool = True) -> None:
        """Handle list layout button toggle.
        
        Switches to table list view.
        
        Args:
            state: Toggle state.
            refresh: Whether to refresh scenefile display.
        """
        if state:
            self.b_sceneLayoutItems.blockSignals(True)
            self.b_sceneLayoutItems.setChecked(False)
            self.b_sceneLayoutItems.blockSignals(False)
        else:
            self.b_sceneLayoutList.blockSignals(True)
            self.b_sceneLayoutList.setChecked(True)
            self.b_sceneLayoutList.blockSignals(False)

        self.sw_scenefiles.setCurrentIndex(0)
        if refresh:
            self.refreshScenefilesThreaded(reloadFiles=False)

    @err_catcher(name=__name__)
    def showSceneFilterMenu(self, state: Optional[bool] = None) -> None:
        """Show scene filter context menu.
        
        Args:
            state: Button state (unused).
        """
        self.showContextMenu("sceneFilter")

    @err_catcher(name=__name__)
    def getContextMenu(self, menuType: str, **kwargs: Any) -> Optional[Any]:
        """Get a context menu of specified type.
        
        Args:
            menuType: Type of menu to create.
            **kwargs: Additional menu parameters.
            
        Returns:
            QMenu instance or None.
        """
        menu = None
        if menuType == "sceneFilter":
            menu = self.getSceneFilterMenu(**kwargs)

        return menu

    @err_catcher(name=__name__)
    def showContextMenu(self, menuType: str, **kwargs: Any) -> None:
        """Show context menu of specified type.
        
        Args:
            menuType: Type of menu to show.
            **kwargs: Additional menu parameters.
        """
        menu = self.getContextMenu(menuType, **kwargs)
        self.core.callback(
            name="sceneBrowserContextMenuRequested",
            args=[self, menuType, menu],
        )
        if not menu or menu.isEmpty():
            return

        menu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def getSceneFilterMenu(self) -> Any:
        """Get scene file format filter menu.
        
        Returns:
            QMenu with file type filter options.
        """
        menu = QMenu(self)
        pos = QCursor.pos()
        for pluginName in self.appFilters:
            action = QAction(pluginName, self)
            action.setCheckable(True)
            checked = self.getAppFilter(pluginName)
            action.setChecked(checked)
            action.toggled.connect(lambda x, k=pluginName: self.setAppFilter(k, x))
            action.toggled.connect(
                lambda x, k=pluginName: self.reopenContextMenu("sceneFilter", menu, pos)
            )
            menu.addAction(action)

        return menu

    @err_catcher(name=__name__)
    def reopenContextMenu(self, menuType: str, menu: Any, pos: Any) -> None:
        """Reopen context menu at same position.
        
        Used when Ctrl is held to keep menu open when toggling filters.
        
        Args:
            menuType: Type of menu.
            menu: Menu widget.
            pos: Menu position.
        """
        mods = QApplication.keyboardModifiers()
        if mods != Qt.ControlModifier:
            return

        self.core.callback(
            name="sceneBrowserContextMenuRequested",
            args=[self, menuType, menu],
        )
        if not menu or menu.isEmpty():
            return

        menu.exec_(pos)

    @err_catcher(name=__name__)
    def getAppFilter(self, key: str) -> bool:
        """Get filter state for an application.
        
        Args:
            key: Application filter key.
            
        Returns:
            True if filter is active.
        """
        return self.appFilters[key]["show"]

    @err_catcher(name=__name__)
    def setAppFilter(self, key: str, value: bool, refresh: bool = True) -> None:
        """Set filter state for an application.
        
        Args:
            key: Application filter key.
            value: Whether filter should be active.
            refresh: Whether to refresh scenefile list.
        """
        self.appFilters[key]["show"] = value
        self.refreshAppFilterIndicator()

        if refresh:
            self.refreshScenefilesThreaded()

    @err_catcher(name=__name__)
    def refreshAppFilterIndicator(self) -> None:
        """Update filter button visual indicator.
        
        Shows active state if any filters are disabled.
        """
        isActive = False
        for app in self.appFilters:
            if not self.appFilters[app]["show"]:
                isActive = True
        
        ssheet = "QWidget{padding: 0; margin: 0;}"
        if isActive:
            ssheet += "QWidget{background-color: rgba(220, 90, 40, 255);}"

        self.b_scenefilter.setStyleSheet(ssheet)

    @err_catcher(name=__name__)
    def rightClickedList(self, widget: Any, pos: Any) -> Optional[bool]:
        """Handle right-click on department or task list.
        
        Shows context menu with create/refresh/navigate options.
        
        Args:
            widget: List widget that was right-clicked.
            pos: Click position.
            
        Returns:
            False if entity invalid, None otherwise.
        """
        entity = self.getCurrentEntity()
        if not entity or entity["type"] not in ["asset", "shot", "sequence"]:
            return

        rcmenu = QMenu(self)
        typename = "Task"
        callbackName = ""

        widgetType = "department" if widget == self.lw_departments else "task"

        if entity["type"] == "asset" and widgetType == "department":
            if not entity.get("asset_path"):
                return False

            path = self.core.getEntityPath(reqEntity="step", entity=entity)
            typename = "Department"
            callbackName = "openPBAssetDepartmentContextMenu"
            refresh = self.refreshDepartments

        elif entity["type"] == "asset" and widgetType == "task":
            curDep = self.getCurrentDepartment()
            if curDep:
                path = self.core.getEntityPath(entity=entity, step=curDep)
            else:
                return False

            callbackName = "openPBAssetTaskContextMenu"
            refresh = self.refreshTasks

        elif entity["type"] in ["shot", "sequence"] and widgetType == "department":
            if not entity.get("shot"):
                return False

            path = self.core.getEntityPath(reqEntity="step", entity=entity)
            typename = "Department"
            callbackName = "openPBShotDepartmentContextMenu"
            refresh = self.refreshDepartments

        elif entity["type"] in ["shot", "sequence"] and widgetType == "task":
            curDep = self.getCurrentDepartment()
            if curDep:
                path = self.core.getEntityPath(entity=entity, step=curDep)
            else:
                return False

            callbackName = "openPBShotTaskContextMenu"
            refresh = self.refreshTasks

        if typename in ["Department", "Task"]:
            label = "Add %s..." % typename
        else:
            label = "Create %s..." % typename

        createAct = QAction(self.core.tr(label), self)
        if widgetType == "department":
            createAct.triggered.connect(lambda x=None: self.createDepartmentDlg())
        else:
            createAct.triggered.connect(lambda x=None: self.createTaskDlg())

        rcmenu.addAction(createAct)
        if widgetType == "department":
            iname = (widget.indexAt(pos)).data(Qt.UserRole)
        else:
            iname = (widget.indexAt(pos)).data()

        if refresh:
            act_refresh = QAction(self.core.tr("Refresh"), self)
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "refresh.png"
            )
            act_refresh.setIcon(self.core.media.getColoredIcon(iconPath))
            act_refresh.triggered.connect(lambda: refresh(restoreSelection=True))
            rcmenu.addAction(act_refresh)

        if iname:
            prjMngMenus = []
            if widgetType == "department":
                dirPath = self.core.getEntityPath(entity=entity, step=iname)
            else:
                dirPath = self.core.getEntityPath(entity=entity, step=curDep, category=iname)

            if (
                not os.path.exists(dirPath)
                and self.core.useLocalFiles
                and os.path.exists(self.core.convertPath(dirPath, "local"))
            ):
                dirPath = self.core.convertPath(dirPath, "local")

            openex = QAction(self.core.tr("Open in explorer"), self)
            openex.triggered.connect(lambda: self.core.openFolder(dirPath))
            rcmenu.addAction(openex)
            copAct = self.core.getCopyAction(dirPath, parent=self)
            rcmenu.addAction(copAct)
            for i in prjMngMenus:
                if i:
                    rcmenu.addAction(i)
        elif "path" in locals():
            widget.setCurrentItem(None)
            openex = QAction(self.core.tr("Open in explorer"), self)
            openex.triggered.connect(lambda: self.core.openFolder(path))
            rcmenu.addAction(openex)
            copAct = self.core.getCopyAction(path, parent=self)
            rcmenu.addAction(copAct)

        if callbackName:
            self.core.callback(
                name=callbackName,
                args=[self, rcmenu, widget.indexAt(pos)],
            )

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def rclFile(self, pos: Any) -> None:
        """Handle right-click on scenefile table.
        
        Args:
            pos: Click position.
        """
        idx = self.tw_scenefiles.indexAt(pos)
        if idx != -1:
            irow = idx.row()
            filepath = self.core.fixPath(
                self.tw_scenefiles.model().index(irow, 0).data(Qt.UserRole)
            )
            self.tw_scenefiles.setCurrentIndex(
                self.tw_scenefiles.model().createIndex(irow, 0)
            )
        else:
            filepath = ""
            self.tw_scenefiles.setCurrentIndex(
                self.tw_scenefiles.model().createIndex(-1, 0)
            )

        self.openScenefileContextMenu(filepath)

    @err_catcher(name=__name__)
    def rclItemView(self, pos: Any) -> None:
        """Handle right-click on scenefile item view.
        
        Args:
            pos: Click position.
        """
        self.deselectItems()
        self.openScenefileContextMenu()

    @err_catcher(name=__name__)
    def openScenefileContextMenu(self, filepath: Optional[str] = None) -> None:
        """Open scenefile context menu.
        
        Shows options for creating, building, loading, and managing scenefiles.
        
        Args:
            filepath: Optional specific scenefile path, None for task directory.
        """
        curDep = self.getCurrentDepartment()
        curTask = self.getCurrentTask()
        if not curDep or not curTask:
            return

        if filepath:
            isScenefile = True
        else:
            isScenefile = False
            filepath = self.core.getEntityPath(
                entity=self.getCurrentEntity(), step=curDep, category=curTask
            )

            if (
                not os.path.exists(filepath)
                and self.core.useLocalFiles
                and os.path.exists(self.core.convertPath(filepath, "local"))
            ):
                filepath = self.core.convertPath(filepath, "local")

        rcmenu = QMenu(self)
        if getattr(self.core.appPlugin, "canBuildScene", False) and os.getenv("PRISM_SHOW_BUILD", "1") == "1":
            if os.path.normpath(filepath) == os.path.normpath(self.core.getCurrentFileName()):
                buildAct = QAction("Update Scene...", self)
                buildAct.triggered.connect(lambda: self.rebuildScene())
                rcmenu.addAction(buildAct)

            buildAct = QAction("Build new Scene (hold CTRL for settings)", self)
            buildAct.triggered.connect(lambda: self.buildScene())
            if self.core.appPlugin.pluginName == "Standalone":
                buildAct.setEnabled(False)

            rcmenu.addAction(buildAct)

        current = QAction(self.core.tr("Create new version from current"), self)
        current.triggered.connect(lambda: self.createFromCurrent())
        if self.core.appPlugin.pluginName == "Standalone":
            current.setEnabled(False)

        rcmenu.addAction(current)
        emp = QMenu(self.core.tr("Create new version from preset"), self)
        context = self.getCurrentEntity().copy()
        context["department"] = curDep
        context["task"] = curTask
        scenes = self.core.entities.getPresetScenes(context)
        dirMenus = {}
        for scene in sorted(scenes, key=lambda x: os.path.basename(x["label"]).lower()):
            folders = scene["label"].split("/")
            curPath = ""
            for idx, folder in enumerate(folders):
                if idx == (len(folders) - 1):
                    empAct = QAction(folder, self)
                    empAct.triggered.connect(
                        lambda y=None, fname=scene: self.createSceneFromPreset(fname)
                    )
                    dirMenus.get(curPath, emp).addAction(empAct)
                else:
                    curMenu = dirMenus.get(curPath, emp)
                    curPath = os.path.join(curPath, folder)
                    if curPath not in dirMenus:
                        dirMenus[curPath] = QMenu(folder, self)
                        curMenu.addMenu(dirMenus[curPath])

        newPreset = QAction(self.core.tr("< Create new preset from current >"), self)
        newPreset.triggered.connect(self.core.entities.createPresetScene)
        emp.addAction(newPreset)
        if self.core.appPlugin.pluginName == "Standalone":
            newPreset.setEnabled(False)

        rcmenu.addMenu(emp)
        autob = QMenu(self.core.tr("Create new version from autobackup"), self)
        for pluginName in self.core.getPluginNames():
            if self.core.getPluginData(pluginName, "appType") == "standalone":
                continue

            if not self.core.getPluginData(pluginName, "getAutobackPath"):
                continue

            autobAct = QAction(pluginName, self)
            autobAct.triggered.connect(lambda y=None, x=pluginName: self.autoback(x))
            autob.addAction(autobAct)

        rcmenu.addMenu(autob)

        if isScenefile:
            globalAct = QAction(self.core.tr("Copy to global"), self)
            if self.core.useLocalFiles and os.path.normpath(filepath).startswith(
                self.core.localProjectPath
            ):
                globalAct.triggered.connect(lambda: self.copyToGlobal(os.path.normpath(filepath)))
            else:
                globalAct.setEnabled(False)
            rcmenu.addAction(globalAct)

            actDeps = QAction(self.core.tr("Show dependencies..."), self)
            infoPath = (
                os.path.splitext(filepath)[0]
                + "versioninfo"
                + self.core.configs.getProjectExtension()
            )

            self.core.configs.findDeprecatedConfig(infoPath)
            if os.path.exists(infoPath):
                actDeps.triggered.connect(lambda: self.core.dependencyViewer(infoPath))
            else:
                actDeps.setEnabled(False)
            rcmenu.addAction(actDeps)

            actCom = QAction(self.core.tr("Edit Comment..."), self)
            actCom.triggered.connect(lambda: self.editComment(filepath))
            rcmenu.addAction(actCom)

            actCom = QAction(self.core.tr("Edit Description..."), self)
            actCom.triggered.connect(lambda: self.editDescription(filepath))
            rcmenu.addAction(actCom)

        act_refresh = QAction(self.core.tr("Refresh"), self)
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "refresh.png"
        )
        act_refresh.setIcon(self.core.media.getColoredIcon(iconPath))
        act_refresh.triggered.connect(lambda: self.refreshScenefilesThreaded(restoreSelection=True))
        rcmenu.addAction(act_refresh)

        if self.core.useLocalFiles:
            locations = ["Global", "Local"]
            for location in locations:
                fpath = self.core.convertPath(filepath, location.lower())
                m_loc = QMenu(location, self)

                openex = QAction(self.core.tr("Open in Explorer"), self)
                openex.triggered.connect(lambda x=None, f=fpath: self.core.openFolder(f))
                m_loc.addAction(openex)

                copAct = self.core.getCopyAction(fpath, parent=self)
                m_loc.addAction(copAct)

                copAct = QAction(self.core.tr("Copy path for next version"), self)
                copAct.triggered.connect(lambda x=None, l=location: self.prepareNewVersion(location=l.lower()))
                m_loc.addAction(copAct)

                past = QAction(self.core.tr("Paste new version"), self)
                past.triggered.connect(lambda x=None, l=location: self.pastefile(location=l.lower()))
                m_loc.addAction(past)

                rcmenu.addMenu(m_loc)
        else:
            openex = QAction(self.core.tr("Open in Explorer"), self)
            openex.triggered.connect(lambda: self.core.openFolder(filepath))
            rcmenu.addAction(openex)

            copAct = self.core.getCopyAction(filepath, parent=self)
            rcmenu.addAction(copAct)

            copAct = QAction(self.core.tr("Copy path for next version"), self)
            copAct.triggered.connect(self.prepareNewVersion)
            rcmenu.addAction(copAct)

            past = QAction(self.core.tr("Paste new version"), self)
            past.triggered.connect(self.pastefile)
            rcmenu.addAction(past)

        self.core.callback(name="openPBFileContextMenu", args=[self, rcmenu, filepath])

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def prepareNewVersion(self, location: str = "global") -> None:
        """Prepare and copy path for next version to clipboard.
        
        Generates next version path and saves version info.
        
        Args:
            location: Storage location ("global" or "local").
        """
        curEntity = self.getCurrentEntity()
        curDep = self.getCurrentDepartment()
        curTask = self.getCurrentTask()
        if not curDep or not curTask:
            return

        version = self.core.entities.getHighestVersion(curEntity, curDep, curTask)
        nextPath = self.core.generateScenePath(
            entity=curEntity,
            department=curDep,
            task=curTask,
            version=version,
            location=location,
        )

        details = curEntity.copy()
        details["department"] = curDep
        details["task"] = curTask
        details["version"] = version

        self.core.saveSceneInfo(nextPath + ".", details=details)
        self.core.copyToClipboard(nextPath)

    @err_catcher(name=__name__)
    def sceneAreaDoubleClicked(self, event: Any, widget: Any) -> None:
        """Open the current task folder when empty scenefile space is double-clicked."""
        if event.button() == Qt.LeftButton and (
            widget is not self.tw_scenefiles or not widget.indexAt(event.pos()).isValid()
        ):
            entity = self.getCurrentEntity()
            department = self.getCurrentDepartment()
            task = self.getCurrentTask()
            if entity and department and task:
                path = self.core.getEntityPath(entity=entity, step=department, category=task)
                if (
                    not os.path.exists(path)
                    and self.core.useLocalFiles
                    and os.path.exists(self.core.convertPath(path, "local"))
                ):
                    path = self.core.convertPath(path, "local")
                self.core.openFolder(path)

            event.accept()
            return

        widget.mouseDClick(event)

    @err_catcher(name=__name__)
    def sceneDoubleClicked(self, index: Any) -> None:
        """Handle double-click on scenefile.
        
        Opens the scenefile in its application.
        
        Args:
            index: Table index of double-clicked item.
        """
        filepath = index.model().index(index.row(), 0).data(Qt.UserRole)
        self.exeFile(filepath, source=index)

    @err_catcher(name=__name__)
    def exeFile(self, filepath: str, source: Optional[Any] = None) -> None:
        """Execute/open a scenefile.
        
        Opens file and optionally closes browser.
        
        Args:
            filepath: Path to scenefile to open.
            source: Optional source of the open request (e.g., table index). Defaults to None.
        """
        result = self.core.entities.openScenefile(filepath)
        if not result:
            return

        if self.core.useLocalFiles:
            navData = self.getSelectedContext()
            self.refreshScenefilesThreaded(wait=True)
            self.navigate(data=navData)

        import subprocess
        if (
            self.core.getCurrentFileName().replace("\\", "/") == filepath
            and self.projectBrowser.actionCloseAfterLoad.isChecked()
        ):
            self.window().close()
        elif self.core.appPlugin.pluginName == "Standalone" and isinstance(result, subprocess.Popen) and source:
            self.showFileOpenedAnim(result, source, filepath)

    def _cleanupFileOpenedAnim(self) -> None:
        """Stop and remove the temporary scene-open loading indicator."""
        state = getattr(self, "_fileOpenAnimState", None)
        if not state:
            return

        self._fileOpenAnimState = None

        for timerKey in ["checkTimer", "fadeOutTimer", "cleanupTimer"]:
            timer = state.get(timerKey)
            if timer:
                try:
                    timer.stop()
                except RuntimeError:
                    pass

        movie = state.get("movie")
        if movie:
            try:
                movie.stop()
            except RuntimeError:
                pass

        widget = state.get("widget")
        if widget:
            try:
                widget.hide()
                widget.deleteLater()
            except RuntimeError:
                pass

    @err_catcher(name=__name__)
    def showFileOpenedAnim(self, process: Any, source: Any, filepath: str) -> None:
        """Show a short loading indicator while an external scene process starts.

        The indicator fades in quickly, stays visible for three seconds,
        and then fades out. If the process exits during that period a warning
        is shown after the indicator disappears.

        Args:
            process: External process object (typically subprocess.Popen).
            source: Source UI element that triggered opening.
            filepath: Path to the scenefile being opened.
        """
        self._cleanupFileOpenedAnim()

        try:
            initialExitCode = process.poll()
        except Exception:
            initialExitCode = None

        if initialExitCode not in [None, 0]:
            msg = self.core.tr(
                "The launched process closed immediately.\n"
                "Please verify that the correct executable is configured or that a default application for %s files is set in your system settings." % os.path.splitext(filepath)[1]
            )
            msg += "\n\n%s %s" % (self.core.tr("Exit code:"), initialExitCode)
            self.core.popup(msg, parent=self)
            return

        targetParent = self
        targetRect = self.rect()
        radius = 10
        if isinstance(source, QModelIndex):
            if source.isValid():
                targetParent = self.tw_scenefiles.viewport()
                targetRect = self.tw_scenefiles.visualRect(source)
                targetRect.setLeft(0)
                targetRect.setWidth(targetParent.width())
                radius = 0
        elif isinstance(source, QWidget):
            targetParent = source
            targetRect = source.rect()

        if not targetRect.isValid() or targetRect.width() <= 0 or targetRect.height() <= 0:
            targetRect = targetParent.rect()

        indicator = QFrame(targetParent)
        indicator.setObjectName("scene_open_indicator")
        indicator.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        indicator.setStyleSheet(
            """
            QFrame#scene_open_indicator {
                background-color: rgba(24, 24, 24, 225);
                border: 1px solid rgba(255, 255, 255, 55);
                border-radius: %spx;
            }
            QLabel#scene_open_text {
                font-size: 9pt;
            }
            """ % radius
        )

        compactMode = targetRect.height() < 64
        if compactMode:
            lo_indicator = QHBoxLayout(indicator)
            lo_indicator.setContentsMargins(10, 2, 10, 2)
            lo_indicator.setSpacing(8)
            lo_indicator.addStretch()
        else:
            lo_indicator = QVBoxLayout(indicator)
            lo_indicator.setContentsMargins(12, 10, 12, 10)
            lo_indicator.setSpacing(6)

        l_anim = QLabel(indicator)
        l_anim.setAlignment(Qt.AlignCenter)
        lo_indicator.addWidget(l_anim)

        text = self.core.tr("Opening scene...")
        if compactMode:
            text = self.core.tr("Opening...")

        l_text = QLabel(text, indicator)
        l_text.setObjectName("scene_open_text")
        l_text.setAlignment(Qt.AlignCenter if not compactMode else Qt.AlignVCenter | Qt.AlignLeft)
        lo_indicator.addWidget(l_text)

        if compactMode:
            lo_indicator.addStretch()

        gifPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "loading.gif"
        )
        movie = QMovie(gifPath, QByteArray(), indicator)
        if movie and movie.isValid():
            movie.setCacheMode(QMovie.CacheAll)
            movie.setSpeed(100)
            movie.setScaledSize(QSize(18, 18) if compactMode else QSize(54, 30))
            l_anim.setMovie(movie)
            movie.start()
        else:
            l_anim.setText("...")

        indicator.setGeometry(targetRect)

        opacity = QGraphicsOpacityEffect(indicator)
        opacity.setOpacity(0.0)
        indicator.setGraphicsEffect(opacity)

        fadeIn = QPropertyAnimation(opacity, b"opacity", indicator)
        fadeIn.setDuration(170)
        fadeIn.setStartValue(0.0)
        fadeIn.setEndValue(1.0)
        fadeIn.setEasingCurve(QEasingCurve.OutCubic)

        fadeOut = QPropertyAnimation(opacity, b"opacity", indicator)
        fadeOut.setDuration(700)
        fadeOut.setStartValue(1.0)
        fadeOut.setEndValue(0.0)
        fadeOut.setEasingCurve(QEasingCurve.InOutCubic)

        checkTimer = QTimer(indicator)
        checkTimer.setInterval(120)
        fadeOutTimer = QTimer(indicator)
        fadeOutTimer.setSingleShot(True)
        cleanupTimer = QTimer(indicator)
        cleanupTimer.setSingleShot(True)

        state = {
            "widget": indicator,
            "movie": movie,
            "checkTimer": checkTimer,
            "fadeOutTimer": fadeOutTimer,
            "cleanupTimer": cleanupTimer,
            "closedEarly": False,
            "exitCode": None,
            "startTime": time.time(),
        }
        self._fileOpenAnimState = state

        def checkProcessClosed() -> None:
            if getattr(self, "_fileOpenAnimState", None) is not state:
                return

            elapsed = time.time() - state["startTime"]
            if elapsed >= 3.0:
                checkTimer.stop()
                return

            try:
                exitCode = process.poll()
            except Exception:
                exitCode = None

            if exitCode not in [None, 0]:
                state["closedEarly"] = True
                state["exitCode"] = exitCode
                checkTimer.stop()

        def startFadeOut() -> None:
            if getattr(self, "_fileOpenAnimState", None) is not state:
                return

            fadeOut.start()

        def finishAnim() -> None:
            if getattr(self, "_fileOpenAnimState", None) is not state:
                return

            closedEarly = state.get("closedEarly", False)
            exitCode = state.get("exitCode")
            self._cleanupFileOpenedAnim()

            if closedEarly:
                msg = self.core.tr(
                    "The launched process closed within 3 seconds.\n"
                    "Please verify that the correct executable is configured or that a default application for %s files is set in your system settings." % os.path.splitext(filepath)[1]
                )
                if exitCode not in [None, 0]:
                    msg += "\n\n%s %s" % (self.core.tr("Exit code:"), exitCode)

                self.core.popup(msg, parent=self)

        checkTimer.timeout.connect(checkProcessClosed)
        fadeOutTimer.timeout.connect(startFadeOut)
        cleanupTimer.timeout.connect(finishAnim)

        indicator.show()
        indicator.raise_()
        fadeIn.start()
        checkTimer.start()
        fadeOutTimer.start(2300)
        cleanupTimer.start(3000)

    @err_catcher(name=__name__)
    def buildScene(self) -> None:
        """Build a new scene from app template.
        """
        entity = self.getCurrentEntity()
        curDep = self.getCurrentDepartment()
        curTask = self.getCurrentTask()
        if not entity or not curDep or not curTask:
            return

        stepOverrides = None
        modifiers = QApplication.keyboardModifiers()
        if modifiers & Qt.ControlModifier:
            stepContext = entity.copy()
            stepContext["department"] = curDep
            stepContext["task"] = curTask
            stepContext["extension"] = self.core.appPlugin.getSceneExtension(self)
            presetScene = self.core.entities.getDefaultPresetSceneForContext(stepContext)
            useTemplate = bool(
                presetScene
                and os.path.splitext(presetScene)[1] in self.core.appPlugin.sceneFormats
            )

            evaluatedSteps, stepContext = (
                self.core.entities.getSceneBuildingStepsWithUpdateData(
                    entity, curDep, curTask, includeUnevaluated=True, newScenePreview=True
                )
            )
            dlg = SceneReBuildStepRunDlg(
                self.core,
                evaluatedSteps,
                templateScene=presetScene if useTemplate else None,
                stepContext=stepContext,
                useCurrentScene=False,
                parent=self,
            )
            if dlg.exec_() != QDialog.Accepted:
                return

            stepOverrides = dlg.getEnabledSteps()
            presetScene = dlg.templateScene

        filepath = self.core.entities.buildScene(
            entity=entity,
            department=curDep,
            task=curTask,
            stepOverrides=stepOverrides,
            templateScene=presetScene if modifiers & Qt.ControlModifier else None,
        )
        if filepath:
            self.core.addToRecent(filepath)

    @err_catcher(name=__name__)
    def rebuildScene(self) -> None:
        """Update the current scene with the latest scenebuilding steps
        """
        entity = self.getCurrentEntity()
        curDep = self.getCurrentDepartment()
        curTask = self.getCurrentTask()
        if not entity or not curDep or not curTask:
            return

        evaluatedSteps, stepContext = (
            self.core.entities.getSceneBuildingStepsWithUpdateData(
                entity, curDep, curTask
            )
        )

        if not evaluatedSteps:
            self.core.popup(
                self.core.tr("No rebuildable scenebuilding steps are available for this context."),
                parent=self,
            )
            return

        dlg = SceneReBuildStepRunDlg(
            self.core,
            evaluatedSteps,
            templateScene=None,
            stepContext=stepContext,
            parent=self,
        )
        if getattr(self, "dlg_sceneRebuild", None):
            try:
                self.dlg_sceneRebuild.close()
            except Exception:
                pass

        self.dlg_sceneRebuild = dlg
        dlg.setModal(False)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    @err_catcher(name=__name__)
    def createFromCurrent(self) -> None:
        """Create new version from current scene.
        """
        entity = self.getCurrentEntity()
        curDep = self.getCurrentDepartment()
        curTask = self.getCurrentTask()
        filepath = self.core.entities.createVersionFromCurrentScene(
            entity=entity, department=curDep, task=curTask
        )
        self.core.addToRecent(filepath)

    @err_catcher(name=__name__)
    def autoback(self, prog: str) -> None:
        """Create version from autobackup file.
        
        Args:
            prog: Application name for autobackup.
        """
        entity = self.getCurrentEntity()
        curDep = self.getCurrentDepartment()
        curTask = self.getCurrentTask()
        filepath = self.core.entities.createVersionFromAutoBackupDlg(
            prog, entity=entity, department=curDep, task=curTask, parent=self
        )
        if not filepath:
            return

        if prog == self.core.appPlugin.pluginName:
            self.exeFile(filepath=filepath)
        else:
            self.core.addToRecent(filepath)
            self.refreshScenefilesThreaded()

    @err_catcher(name=__name__)
    def createSceneFromPreset(
        self,
        scene: Dict[str, str],
        entity: Optional[Dict[str, Any]] = None,
        step: Optional[str] = None,
        category: Optional[str] = None,
        comment: Optional[str] = None,
        openFile: bool = True,
        version: Optional[str] = None,
        location: str = "local",
    ) -> Optional[str]:
        """Create scenefile from preset template.
        
        Args:
            scene: Scene preset data with path and label.
            entity: Optional entity, uses current if None.
            step: Optional department, uses current if None.
            category: Optional task, uses current if None.
            comment: Optional version comment.
            openFile: Whether to open file after creation.
            version: Optional specific version string.
            location: Storage location ("local" or "global").
            
        Returns:
            Created file path, or None if creation failed.
        """
        ext = os.path.splitext(scene["path"])[1]
        entity = entity or self.getCurrentEntity()
        step = step or self.getCurrentDepartment()
        category = category or self.getCurrentTask()

        filePath = self.core.entities.createSceneFromPreset(
            entity,
            scene["path"],
            step=step,
            category=category,
            comment=comment,
            version=version,
            location=location,
        )

        if self.core.uiAvailable and filePath:
            if ext in self.core.appPlugin.sceneFormats and openFile:
                self.core.callback(
                    name="preLoadPresetScene",
                    args=[self, filePath],
                )
                self.exeFile(filepath=filePath)
                if not self.projectBrowser.actionCloseAfterLoad.isChecked():
                    self.refreshScenefilesThreaded()

                self.core.callback(
                    name="postLoadPresetScene",
                    args=[self, filePath],
                )
            else:
                self.core.addToRecent(filePath)
                self.refreshScenefilesThreaded()

        return filePath

    @err_catcher(name=__name__)
    def pastefile(self, location: Optional[str] = None) -> None:
        """Paste scenefile from clipboard path.
        
        Args:
            location: Optional target location ("local" or "global").
        """
        copiedFile = self.core.getClipboard()
        if not copiedFile or not os.path.isfile(copiedFile):
            msg = self.core.tr("No valid filepath in clipboard.")
            self.core.popup(msg)
            return

        entity = self.getCurrentEntity()
        curDep = self.getCurrentDepartment()
        curTask = self.getCurrentTask()

        dstname = self.core.entities.copySceneFile(
            copiedFile, entity=entity, department=curDep, task=curTask, location=location
        )

        if os.path.splitext(dstname)[1] in self.core.appPlugin.sceneFormats:
            self.exeFile(filepath=dstname)
        else:
            self.core.addToRecent(dstname)

        self.refreshScenefilesThreaded()

    @err_catcher(name=__name__)
    def createSteps(self, entities: List[Dict[str, Any]], steps: List[str], createTask: bool = True) -> None:
        """Create departments for entities.
        
        Args:
            entities: List of entity data dictionaries.
            steps: List of department abbreviations to create.
            createTask: Whether to create default task in each department.
        """
        if len(steps) > 0:
            navData = entities[0]
            createdDirs = []

            for step in steps:
                for entity in entities:
                    result = self.core.entities.createDepartment(
                        step, entity, createCat=createTask
                    )
                    if result:
                        createdDirs.append(step)
                        navData["department"] = self.core.entities.getLongDepartmentName(entity["type"], step) or step

            if createdDirs:
                self.pendingNavigationData = navData
                self.refreshDepartments(restoreSelection=True)

    @err_catcher(name=__name__)
    def getSelectedContext(self) -> Dict[str, Any]:
        """Get current selection context.
        
        Returns:
            Dictionary with entity, department, task, and filename.
        """
        navData = self.getCurrentEntity() or {}
        navData["department"] = self.getCurrentDepartment()
        navData["task"] = self.getCurrentTask()
        navData["filename"] = self.getSelectedScenefile()
        return navData

    @err_catcher(name=__name__)
    def refreshUI(self) -> None:
        """Refresh the entire UI.
        
        Reloads entity tree and navigates back to current selection.
        """
        previousSelection = self.refreshSelection or {}
        self.refreshSelection = {
            "department": self.getCurrentDepartment() or previousSelection.get("department"),
            "task": self.getCurrentTask() or previousSelection.get("task"),
        }
        self.staleScenefileWorker = self.curSceneThread
        self.pendingSceneRefresh = None
        self.hideScenesLoading()
        self.departmentRefreshId += 1
        self.taskRefreshId += 1
        for listWidget in [self.lw_departments, self.lw_tasks]:
            self.hideEntityListLoading(listWidget, force=True)
            wasBlocked = listWidget.signalsBlocked()
            listWidget.blockSignals(True)
            listWidget.clear()
            listWidget.blockSignals(wasBlocked)

        self.clearScenefileItems()
        model = self.tw_scenefiles.model()
        if model:
            model.clear()

        self.entityInfoRefreshId += 1
        page = self.w_entities.getCurrentPage()
        if page.entityType == "asset":
            self.refreshAssetinfo(info={"entities": []})
        elif page.entityType in ["shot", "sequence"]:
            self.refreshShotinfo(info={"entities": []})

        page.tw_tree.blockSignals(True)
        page.tw_tree.selectionModel().blockSignals(True)
        self.w_entities.refreshEntities(restoreSelection=True)
        page.tw_tree.blockSignals(False)
        page.tw_tree.selectionModel().blockSignals(False)
        self.refreshStatus = "valid"

    @err_catcher(name=__name__)
    def refreshDepartments(self, restoreSelection: bool = False) -> None:
        """Refresh departments list for current entity.
        
        Args:
            restoreSelection: Whether to restore previous department selection.
        """
        curDep = None
        if restoreSelection:
            curDep = (self.pendingNavigationData or {}).get("department") or self.getCurrentDepartment() or (self.refreshSelection or {}).get("department")

        self.departmentRefreshId += 1
        refreshId = self.departmentRefreshId
        self.taskRefreshId += 1
        curEntities = self.getCurrentEntities()
        if len(curEntities) != 1 or curEntities[0]["type"] not in ["asset", "shot", "sequence"]:
            self.refreshSelection = None
            wasBlocked = self.lw_departments.blockSignals(True)
            self.lw_departments.clear()
            self.lw_departments.blockSignals(wasBlocked)
            self.refreshTasks()
            return

        entity = curEntities[0].copy()

        def loadDepartments() -> List[str]:
            return self.core.entities.getSteps(entity=entity)

        def applyDepartments(steps: List[str]) -> None:
            if refreshId != self.departmentRefreshId:
                return

            wasBlocked = self.lw_departments.signalsBlocked()
            if not wasBlocked:
                self.lw_departments.blockSignals(True)

            self.lw_departments.clear()
            for step in steps:
                longName = self.core.entities.getLongDepartmentName(entity["type"], step) or step
                stepItem = QListWidgetItem(longName)
                stepItem.setData(Qt.UserRole, step)
                icon = self.core.entities.getDepartmentIcon(longName)
                if icon:
                    stepItem.setIcon(icon)
                self.lw_departments.addItem(stepItem)

            if self.lw_departments.count() > 0:
                selectedRow = 0
                if restoreSelection:
                    for idx in range(self.lw_departments.count()):
                        item = self.lw_departments.item(idx)
                        if curDep in (item.data(Qt.UserRole), item.text()):
                            selectedRow = idx
                            break

                self.lw_departments.setCurrentRow(selectedRow)
            else:
                self.pendingNavigationData = None

            if not wasBlocked:
                self.lw_departments.blockSignals(False)
            self.refreshTasks(restoreSelection=True)

        self.runEntityListWorker(loadDepartments, applyDepartments, self.lw_departments)

    @err_catcher(name=__name__)
    def refreshTasks(self, restoreSelection: bool = False) -> None:
        """Refresh tasks list for current department.
        
        Args:
            restoreSelection: Whether to restore previous task selection.
        """
        if restoreSelection:
            curTask = (self.pendingNavigationData or {}).get("task") or self.getCurrentTask()
            if not curTask and self.refreshSelection and self.getCurrentDepartment() == self.refreshSelection["department"]:
                curTask = self.refreshSelection["task"]

        self.taskRefreshId += 1
        refreshId = self.taskRefreshId
        curEntities = self.getCurrentEntities()
        curDep = self.getCurrentDepartment()
        if len(curEntities) != 1 or not curDep:
            self.refreshSelection = None
            wasBlocked = self.lw_tasks.blockSignals(True)
            self.lw_tasks.clear()
            self.lw_tasks.blockSignals(wasBlocked)
            self.refreshScenefilesThreaded()
            return

        curEntity = curEntities[0]
        entity = curEntity.copy()

        def loadTasks() -> List[str]:
            if (
                entity["type"] == "asset"
                and self.core.compareVersions(self.core.projectVersion, "v1.2.1.6") == "lower"
            ):
                return []
            return self.core.entities.getCategories(entity=entity, step=curDep)

        def applyTasks(cats: List[str]) -> None:
            if refreshId != self.taskRefreshId:
                return

            wasBlocked = self.lw_tasks.signalsBlocked()
            if not wasBlocked:
                self.lw_tasks.blockSignals(True)

            self.lw_tasks.clear()
            for category in cats:
                self.lw_tasks.addItem(QListWidgetItem(category))

            if self.lw_tasks.count() > 0:
                if self.taskToSelect in cats:
                    self.lw_tasks.setCurrentRow(cats.index(self.taskToSelect))
                    self.taskToSelect = None
                elif restoreSelection and curTask in cats:
                    self.lw_tasks.setCurrentRow(cats.index(curTask))
                else:
                    self.lw_tasks.setCurrentRow(0)

            self.taskToSelect = None

            if not wasBlocked:
                self.lw_tasks.blockSignals(False)
            self.refreshSelection = None
            self.core.callback(
                name="onSceneBrowserTasksLoaded",
                args=[self, entity, curDep, cats, refreshId],
            )
            self.refreshScenefilesThreaded(restoreSelection=True)
            if self.pendingNavigationData:
                navData = self.pendingNavigationData
                self.pendingNavigationData = None
                self._applyNavigation(navData)

        self.runEntityListWorker(loadTasks, applyTasks, self.lw_tasks)

    @err_catcher(name=__name__)
    def initEntityListLoadingWidgets(self) -> None:
        """Create loading overlays for the department and task list viewports."""
        self.entityListLoadingWidgets = {}
        gifPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "loading.gif"
        )

        for listWidget in [self.lw_departments, self.lw_tasks]:
            viewport = listWidget.viewport()
            overlay = QWidget(viewport)
            overlay.setObjectName("entitylist_loading")
            overlay.setStyleSheet(
                "#entitylist_loading {background-color: rgba(0, 0, 0, 50)}"
            )
            overlay.setAttribute(Qt.WA_StyledBackground, True)
            overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            overlay.hide()

            layout = QHBoxLayout(overlay)
            layout.setContentsMargins(0, 0, 0, 0)
            label = QLabel(overlay)
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)

            movie = QMovie(gifPath, QByteArray(), overlay)
            movie.setCacheMode(QMovie.CacheAll)
            movie.setScaledSize(QSize(72, 40))
            label.setMovie(movie)
            self.entityListLoadingWidgets[listWidget] = (overlay, movie)
            viewport.installEventFilter(self)

    @err_catcher(name=__name__)
    def eventFilter(self, obj: Any, event: Any) -> bool:
        if event.type() == QEvent.Resize:
            for listWidget, loadingData in getattr(
                self, "entityListLoadingWidgets", {}
            ).items():
                if obj == listWidget.viewport():
                    loadingData[0].setGeometry(obj.rect())
                    break

        return QWidget.eventFilter(self, obj, event)

    @err_catcher(name=__name__)
    def showEntityListLoading(self, listWidget: Any) -> None:
        for otherWidget, (otherOverlay, otherMovie) in self.entityListLoadingWidgets.items():
            if otherWidget != listWidget:
                otherOverlay.hide()
                otherMovie.stop()

        wasBlocked = listWidget.signalsBlocked()
        listWidget.blockSignals(True)
        listWidget.clear()
        listWidget.blockSignals(wasBlocked)
        overlay, movie = self.entityListLoadingWidgets[listWidget]
        overlay.setGeometry(listWidget.viewport().rect())
        overlay.show()
        overlay.raise_()
        movie.start()

    @err_catcher(name=__name__)
    def hideEntityListLoading(self, listWidget: Any, force: bool = False) -> None:
        if not force and listWidget in self.entityListWorkerWidgets.values():
            return

        overlay, movie = self.entityListLoadingWidgets[listWidget]
        overlay.hide()
        movie.stop()

    @err_catcher(name=__name__)
    def runEntityListWorker(self, function: Any, callback: Any, listWidget: Any, showLoading: bool = True) -> None:
        """Run department or task discovery without blocking the scene browser."""
        worker = self.core.worker(self.core)
        self.entityListWorkers.append(worker)
        self.entityListWorkerCallbacks[worker] = callback
        self.entityListWorkerWidgets[worker] = listWidget if showLoading else None
        if showLoading:
            self.showEntityListLoading(listWidget)

        def sendData() -> None:
            worker.dataSent.emit({"worker": worker, "result": function()})

        worker.function = sendData
        worker.errored.connect(self.core.writeErrorLog)
        worker.dataSent.connect(self.onEntityListWorkerData)
        worker.finished.connect(self.onEntityListWorkerFinished)
        worker.start()

    @err_catcher(name=__name__)
    def onEntityListWorkerData(self, data: Dict[str, Any]) -> None:
        callback = self.entityListWorkerCallbacks.get(data["worker"])
        if callback:
            callback(data["result"])

    @err_catcher(name=__name__)
    def onEntityListWorkerFinished(self) -> None:
        worker = self.sender()
        if worker in self.entityListWorkers:
            self.entityListWorkers.remove(worker)
        self.entityListWorkerCallbacks.pop(worker, None)
        listWidget = self.entityListWorkerWidgets.pop(worker, None)
        if listWidget is not None:
            self.hideEntityListLoading(listWidget)
        worker.deleteLater()

    @err_catcher(name=__name__)
    def runEntityInfoWorker(self, function: Any, callback: Any) -> None:
        worker = self.core.worker(self.core)
        self.entityInfoWorkers.append(worker)
        self.entityInfoWorkerCallbacks[worker] = callback

        def sendData() -> None:
            worker.dataSent.emit({"worker": worker, "result": function()})

        worker.function = sendData
        worker.errored.connect(self.core.writeErrorLog)
        worker.dataSent.connect(self.onEntityInfoWorkerData)
        worker.finished.connect(self.onEntityInfoWorkerFinished)
        worker.start()

    @err_catcher(name=__name__)
    def onEntityInfoWorkerData(self, data: Dict[str, Any]) -> None:
        callback = self.entityInfoWorkerCallbacks.get(data["worker"])
        if callback:
            callback(data["result"])

    @err_catcher(name=__name__)
    def onEntityInfoWorkerFinished(self) -> None:
        worker = self.sender()
        if worker in self.entityInfoWorkers:
            self.entityInfoWorkers.remove(worker)
        self.entityInfoWorkerCallbacks.pop(worker, None)
        worker.deleteLater()

    @err_catcher(name=__name__)
    def getCurrentEntity(self) -> Optional[Dict[str, Any]]:
        """Get currently selected entity.
        
        Returns:
            Entity data dictionary, or None if no selection.
        """
        return self.w_entities.getCurrentPage().getCurrentData()

    @err_catcher(name=__name__)
    def getCurrentEntities(self) -> List[Dict[str, Any]]:
        """Get all currently selected entities.
        
        Returns:
            List of entity data dictionaries.
        """
        return self.w_entities.getCurrentPage().getCurrentData(returnOne=False)

    @err_catcher(name=__name__)
    def getCurrentDepartment(self) -> Optional[str]:
        """Get currently selected department.
        
        Returns:
            Department abbreviation string, or None if no selection.
        """
        item = self.lw_departments.currentItem()
        if not item:
            return

        if not item.isSelected():
            item.setSelected(True)

        return item.data(Qt.UserRole)

    @err_catcher(name=__name__)
    def getCurrentTask(self) -> Optional[str]:
        """Get currently selected task.
        
        Returns:
            Task name string, or None if no selection.
        """
        item = self.lw_tasks.currentItem()
        if not item:
            return

        if not item.isSelected():
            item.setSelected(True)

        return item.text()

    @err_catcher(name=__name__)
    def getScenefileData(
        self,
        entity: Optional[Dict[str, Any]] = None,
        department: Optional[str] = None,
        task: Optional[str] = None,
        appfilter: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get scenefile data for current context.
        
        Loads and processes all scenefiles for the current entity, department, and task.
        
        Returns:
            List of scenefile data dictionaries with preview, comment, date, user, etc.
        """
        sceneData = []
        curEntity = entity if entity is not None else self.getCurrentEntity()
        curDep = department if department is not None else self.getCurrentDepartment()
        curTask = task if task is not None else self.getCurrentTask()
        if curEntity and curDep and curTask:
            if appfilter is None:
                appfilter = []
                for pluginName in self.appFilters:
                    if self.appFilters[pluginName]["show"]:
                        appfilter += self.appFilters[pluginName]["formats"]

            scenefiles = self.core.entities.getScenefiles(
                entity=curEntity, step=curDep, category=curTask, extensions=appfilter
            )

            for scenefile in scenefiles:
                data = self.core.getScenefileData(scenefile, getEntityFromPath=True, cfg="if_version_missing", entityType=curEntity["type"])
                if "__cfg_loaded__" not in data:
                    data["__cfg_loaded__"] = False

                data["extension"] = os.path.splitext(scenefile)[1].lower()
                data["filename"] = scenefile
                publicFile = (
                    self.projectBrowser
                    and len(self.projectBrowser.locations) > 1
                    and self.core.paths.getLocationFromPath(os.path.normpath(scenefile)) == "global"
                )
                icon = self.core.getIconForFileType(data["extension"])
                if icon:
                    data["icon"] = icon
                else:
                    colorVals = [128, 128, 128]
                    if data["extension"] in self.core.appPlugin.sceneFormats:
                        colorVals = self.core.appPlugin.appColor
                    else:
                        for k in self.core.unloadedAppPlugins.values():
                            if data["extension"] in k.sceneFormats:
                                colorVals = k.appColor

                    data["color"] = QColor(colorVals[0], colorVals[1], colorVals[2])

                if data.get("comment") == "nocomment":
                    data["comment"] = ""

                data["public"] = publicFile
                sceneData.append(data)

            sceneData = sorted(sceneData, key=lambda x: x.get("version") or "")

        return sceneData

    @err_catcher(name=__name__)
    def initScenesLoadingWidget(self) -> None:
        """Initialize the loading indicator widget.
        """
        self.w_scenesLoading = QWidget()
        self.w_scenesLoading.setObjectName("scenewidget")
        self.w_scenesLoading.setStyleSheet("#scenewidget {background-color: rgba(0,0,0,100)}")
        self.w_scenesLoading.setAttribute(Qt.WA_StyledBackground, True)
        self.w_scenesLoading.setParent(self)
        self.sw_scenefiles.resizeEventOrig = self.sw_scenefiles.resizeEvent
        self.sw_scenefiles.resizeEvent = self.sceneFilesResizeEvent
        self.w_scenesLoading.setHidden(True)
        self.l_scenesLoading = QLabel()
        self.l_scenesLoading.setAlignment(Qt.AlignCenter)
        self.lo_scenesLoading = QHBoxLayout(self.w_scenesLoading)
        self.lo_scenesLoading.addWidget(self.l_scenesLoading)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "loading.gif"
        )
        self.loadingGif = QMovie(path, QByteArray(), self) 
        self.loadingGif.setCacheMode(QMovie.CacheAll) 
        self.loadingGif.setSpeed(100)

        self.l_scenesLoading.setMovie(self.loadingGif)
        self.loadingGif.setScaledSize(QSize(self.shotPrvXres, int(self.shotPrvXres / (300/169.0))))

    @err_catcher(name=__name__)
    def sceneFilesResizeEvent(self, event: Any) -> None:
        """Handle scenefile widget resize.
        
        Args:
            event: Resize event.
        """
        self.sw_scenefiles.resizeEventOrig(event)
        if hasattr(self, "loadingGif") and self.loadingGif.state() == QMovie.Running:
            self.moveLoadingLabel()

    @err_catcher(name=__name__)
    def moveLoadingLabel(self) -> None:
        """Move loading indicator to correct position.
        """
        geo = QRect()
        pos = self.sw_scenefiles.parent().mapToGlobal(self.sw_scenefiles.geometry().topLeft())
        pos = self.mapFromGlobal(pos)
        geo.setWidth(self.sw_scenefiles.width())
        geo.setHeight(self.sw_scenefiles.height())
        geo.moveTopLeft(pos)
        self.w_scenesLoading.setGeometry(geo)

    @err_catcher(name=__name__)
    def showScenesLoading(self) -> None:
        """Show the loading indicator.
        """
        self.w_scenesLoading.setHidden(False)
        self.loadingGif.start()
        self.moveLoadingLabel()

    @err_catcher(name=__name__)
    def hideScenesLoading(self) -> None:
        """Hide the loading indicator.
        """
        self.w_scenesLoading.setHidden(True)
        self.loadingGif.stop()

    @err_catcher(name=__name__)
    def processEvents(self, times: int = 1) -> None:
        """Process Qt events with throttling.
        
        Args:
            times: Number of times to process events.
        """
        if (time.time() - self.lastProcess) > 0.05:
            for idx in range(times):
                QApplication.processEvents()

            self.lastProcess = time.time()

    @err_catcher(name=__name__)
    def refreshScenefilesThreaded(self, reloadFiles: bool = True, restoreSelection: bool = False, wait: bool = False) -> None:
        """Refresh scenefiles in background thread.
        
        Args:
            reloadFiles: Whether to reload file data from disk.
            restoreSelection: Whether to restore previous selection.
            wait: Whether to block until refresh completes.
        """
        if restoreSelection:
            file = self.getSelectedScenefile()
        else:
            file = ""

        refreshArgs = {
            "reloadFiles": reloadFiles,
            "restoreSelection": restoreSelection,
            "file": file,
            "itemsLayout": self.b_sceneLayoutItems.isChecked(),
        }
        if self.curSceneThread:
            self.pendingSceneRefresh = refreshArgs
        else:
            self.startScenefileRefresh(**refreshArgs)

        if wait:
            while self.curSceneThread or self.pendingSceneRefresh:
                QApplication.processEvents()

    @err_catcher(name=__name__)
    def startScenefileRefresh(
        self,
        reloadFiles: bool,
        restoreSelection: bool,
        file: str,
        itemsLayout: bool,
    ) -> None:
        """Start one scenefile worker using only GUI-thread state snapshots."""
        self.scenefileToSelect = None
        if self.getCurrentTask():
            self.showScenesLoading()

        entity = self.getCurrentEntity()
        context = {
            "entity": entity.copy() if entity else None,
            "department": self.getCurrentDepartment(),
            "task": self.getCurrentTask(),
            "appfilter": [
                extension
                for pluginData in self.appFilters.values()
                if pluginData["show"]
                for extension in pluginData["formats"]
            ],
        }
        self.scenefileQueue = []
        worker_scenes = self.core.worker(self.core)
        worker_scenes.function = lambda w=worker_scenes: self.refreshScenefiles(
            reloadFiles=reloadFiles,
            restoreSelection=restoreSelection,
            worker=w,
            file=file,
            itemsLayout=itemsLayout,
            context=context,
        )
        worker_scenes.errored.connect(self.core.writeErrorLog)
        worker_scenes.dataSent.connect(self.refreshScenesDataSent)
        worker_scenes.warningSent.connect(self.core.popup)
        worker_scenes.finished.connect(self.onSceneThreadFinished)
        self.curSceneThread = worker_scenes
        if itemsLayout:
            self.clearScenefileItems()
            self.addSceneItemsStretch()
        else:
            model = self.tw_scenefiles.model()
            if model:
                model.clear()

        worker_scenes.start()

    @err_catcher(name=__name__)
    def addSceneItemsStretch(self) -> None:
        """Add vertical stretch spacer to scenefile items layout."""
        sp_main = QSpacerItem(0, 1000, QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.lo_scenefileItems.addItem(sp_main)

    @err_catcher(name=__name__)
    def onSceneThreadFinished(self) -> None:
        """Handle scene loading thread completion.
        
        Starts queued thread if exists and refreshes UI.
        """
        if self.sender() is self.staleScenefileWorker:
            self.staleScenefileWorker = None
        self.curSceneThread = None
        if self.pendingSceneRefresh:
            refreshArgs = self.pendingSceneRefresh
            self.pendingSceneRefresh = None
            self.startScenefileRefresh(**refreshArgs)
        else:
            if self.b_sceneLayoutItems.isChecked():
                if (self.lo_scenefileItems.count()-1) == len(self.scenefileData):
                    self.hideScenesLoading()
            elif self.b_sceneLayoutList.isChecked():
                model = self.tw_scenefiles.model()
                if model:
                    count = model.rowCount()
                else:
                    count = 0

                if count == len(self.scenefileData):
                    self.hideScenesLoading()

            if self.scenefileToSelect:
                self.selectScenefile(self.scenefileToSelect)
                self.scenefileToSelect = None

    @err_catcher(name=__name__)
    def refreshScenesDataSent(self, data: Dict[str, Any]) -> None:
        """Handle data updates from scene loading worker thread.
        
        Args:
            data: Dict with 'action' and action-specific keys
        """
        if self.staleScenefileWorker is not None and data.get("worker") is self.staleScenefileWorker:
            return
        if data["action"] == "selectScenefile":
            self.selectScenefile(data["file"])
        elif data["action"] == "addScenefileItems":
            refreshId = uuid.uuid4().hex
            self.prevRefreshId = refreshId
            self.scenefileQueue = data["data"][20:]
            self.addScenefileItems(data["data"][:20], refreshId=refreshId)
            if refreshId and refreshId == self.prevRefreshId:
                self.validateVisibleScenefileItems(refreshId=refreshId)

            self.hideScenesLoading()
        elif data["action"] == "refreshScenefileList":
            self.refreshScenefileList(data["data"])
            self.hideScenesLoading()

    @err_catcher(name=__name__)
    def refreshScenefiles(self, reloadFiles: bool = True, restoreSelection: bool = False, worker: Optional[Any] = None, file: Optional[str] = None, itemsLayout: Optional[bool] = None, context: Optional[Dict[str, Any]] = None) -> None:
        """Refresh scenefile list in items or table view.
        
        Args:
            reloadFiles: If True, reload scenefile data from disk
            restoreSelection: If True, restore previous selection
            worker: Worker thread instance
            file: Specific file to select
        """
        if not worker:
            if restoreSelection:
                file = self.getSelectedScenefile()

        if itemsLayout is None:
            itemsLayout = self.b_sceneLayoutItems.isChecked()

        if reloadFiles:
            self.scenefileData = self.getScenefileData(**(context or {}))

        if itemsLayout:
            self.scenefileData = sorted(self.scenefileData, key=lambda x: x.get("version", "") or "", reverse=True)
            worker.dataSent.emit({
                "action": "addScenefileItems",
                "data": self.scenefileData,
                "worker": worker,
            })
        else:
            worker.dataSent.emit({
                "action": "refreshScenefileList",
                "data": self.scenefileData,
                "worker": worker,
            })

        if self.scenefileToSelect:
            fileToSelect = self.scenefileToSelect
        elif restoreSelection:
            fileToSelect = file
        else:
            fileToSelect = None

        if fileToSelect:
            worker.dataSent.emit({
                "action": "selectScenefile",
                "file": file,
                "worker": worker,
            })

    @err_catcher(name=__name__)
    def onScrolled(self, value: int) -> None:
        """Handle scroll event to validate visible scene items.
        
        Args:
            value: Scroll position value
        """
        self.validateVisibleScenefileItems()

    @err_catcher(name=__name__)
    def onScenefileListScrolled(self, value: int) -> None:
        """Handle table list view scroll event.

        Args:
            value: Scroll position value.
        """
        self.validateVisibleScenefileRows()

    @err_catcher(name=__name__)
    def _getScenefileDataByFilename(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get scenefile data entry from current cached list by filename.

        Args:
            filename: Scenefile path.

        Returns:
            Matching scenefile data dict or None.
        """
        if not filename:
            return

        cmpPath = os.path.normpath(filename)
        for data in self.scenefileData:
            if os.path.normpath(data.get("filename", "")) == cmpPath:
                return data

    @err_catcher(name=__name__)
    def _findScenefileRowByFilename(self, model: Any, filename: str) -> Optional[int]:
        """Find the current model row for a scenefile path.

        Args:
            model: Scenefile table model.
            filename: Scenefile path.

        Returns:
            Row index when found.
        """
        if not model or not filename:
            return

        cmpPath = os.path.normpath(filename)
        for row in range(model.rowCount()):
            idx = model.index(row, 0)
            rowPath = model.data(idx, Qt.UserRole)
            if rowPath and os.path.normpath(rowPath) == cmpPath:
                return row

    @err_catcher(name=__name__)
    def _loadScenefileCfgData(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Load and merge config data for a scenefile entry when needed.

        Args:
            data: Existing scenefile data dict.

        Returns:
            Updated scenefile data dict.
        """
        if not data:
            return data

        mergedData = dict(data)
        if not data.get("__cfg_loaded__"):
            cfgData = self.core.getScenefileData(
                data.get("filename", ""),
                entityType=data.get("type"),
            )
            mergedData.update(cfgData)
        if type(mergedData.get("date")) not in (int, float):
            cdate = self.core.getFileModificationDate(data["filename"], asString=False)
            mergedData["date"] = cdate

        mergedData["__cfg_loaded__"] = True
        data.update(mergedData)
        return data

    @err_catcher(name=__name__)
    def validateVisibleScenefileRows(self) -> None:
        """Load config data for currently visible table rows when missing.

        This keeps initial list refresh fast while ensuring visible rows show
        comment/user/date as soon as they are in view.
        """
        if not self.b_sceneLayoutList.isChecked():
            return

        model = self.tw_scenefiles.model()
        if not model or model.rowCount() == 0:
            return

        firstRow = self.tw_scenefiles.rowAt(0)
        if firstRow < 0:
            return

        viewportHeight = self.tw_scenefiles.viewport().height()
        lastRow = self.tw_scenefiles.rowAt(max(0, viewportHeight - 1))
        if lastRow < 0:
            lastRow = model.rowCount() - 1

        lastRow = min(lastRow, model.rowCount() - 1)
        for row in range(firstRow, lastRow + 1):
            idx = model.index(row, 0)
            filename = model.data(idx, Qt.UserRole)
            if not filename:
                continue

            rowData = self._getScenefileDataByFilename(filename)
            if not rowData or (rowData.get("__cfg_loaded__") and type(rowData.get("date")) in (int, float)):
                continue

            rowData = self._loadScenefileCfgData(rowData)
            currentRow = self._findScenefileRowByFilename(model, filename)
            if currentRow is None:
                continue

            version = rowData.get("version", "")
            comment = rowData.get("comment", "")
            if not comment and not version:
                comment = os.path.basename(rowData.get("filename", ""))

            date = rowData.get("date")
            dateStr = self.core.getFormattedDate(date) if date else ""
            user = rowData.get("username") or rowData.get("user", "")

            model.item(currentRow, 1).setText(version)
            model.item(currentRow, 2).setText(str(comment))
            model.item(currentRow, 3).setText(dateStr)
            model.item(currentRow, 3).setData(date, 0)
            model.item(currentRow, 4).setText(str(user))

    @err_catcher(name=__name__)
    def validateVisibleScenefileItems(self, refreshId: Optional[Any] = None, processEvents: bool = True) -> None:
        """Load visible scene item widgets and queue more if needed.
        
        Args:
            refreshId: Refresh operation ID. Defaults to None.
            processEvents: Whether to process Qt events. Defaults to True.
        """
        if self.b_sceneLayoutList.isChecked():
            self.validateVisibleScenefileRows()
            return

        refreshId = refreshId or self.prevRefreshId
        if processEvents:
            self.lo_scenefileItems.activate()
            QApplication.processEvents()

        if refreshId and refreshId == self.prevRefreshId:
            for widget in self.sceneItemWidgets:
                if not widget.isLoaded and not widget.visibleRegion().isEmpty():
                    widget.refreshUi()
        
        if (not self.sceneItemWidgets or self.sceneItemWidgets[-1].isLoaded) and self.scenefileQueue:
            self.addScenefileItems(self.scenefileQueue[:20], refreshId=refreshId)
            self.scenefileQueue = self.scenefileQueue[20:]
            self.validateVisibleScenefileItems(refreshId=refreshId, processEvents=processEvents)

    @err_catcher(name=__name__)
    def clearScenefileItems(self) -> None:
        """Remove all scenefile item widgets from layout."""
        self.prevRefreshId = None
        self.sceneItemWidgets = []
        for idx in reversed(range(self.lo_scenefileItems.count())):
            item = self.lo_scenefileItems.takeAt(idx)
            if not item:
                continue

            w = item.widget()
            if w:
                w.setVisible(False)
                w.setParent(None)
                w.deleteLater()

    @err_catcher(name=__name__)
    def addScenefileItems(self, itemsData: List[Dict[str, Any]], refreshId: str) -> None:
        """Add scenefile item widgets to the layout.
        
        Args:
            itemsData: List of scenefile data dicts
            refreshId: Unique ID for this refresh operation
        """
        for data in itemsData:
            item = ScenefileItem(self, data)
            item.signalSelect.connect(self.itemSelected)
            item.signalReleased.connect(self.itemReleased)
            if refreshId and refreshId == self.prevRefreshId:
                self.sceneItemWidgets.append(item)
                self.lo_scenefileItems.insertWidget(self.lo_scenefileItems.count()-1, item)

    @err_catcher(name=__name__)
    def itemSelected(self, item: Any) -> None:
        """Handle scenefile item selection.
        
        Args:
            item: Selected ScenefileItem widget
        """
        if not item.isSelected():
            self.deselectItems(ignore=[item])

    @err_catcher(name=__name__)
    def itemReleased(self, item: Any) -> None:
        """Handle mouse release on scenefile item.
        
        Args:
            item: Released ScenefileItem widget
        """
        self.deselectItems(ignore=[item])

    @err_catcher(name=__name__)
    def deselectItems(self, ignore: Optional[List[Any]] = None) -> None:
        """Deselect all scenefile items except those in ignore list.
        
        Args:
            ignore: List of items to keep selected
        """
        for item in self.sceneItemWidgets:
            if ignore and item in ignore:
                continue

            item.deselect()

    @err_catcher(name=__name__)
    def getSelectedScenefile(self) -> str:
        """Get the filepath of the currently selected scenefile.
        
        Returns:
            Filepath of selected scenefile or empty string
        """
        filepath = ""
        if self.b_sceneLayoutItems.isChecked():
            for item in self.sceneItemWidgets:
                if item.isSelected():
                    filepath = item.data["filename"]

        elif self.b_sceneLayoutList.isChecked():
            idxs = self.tw_scenefiles.selectedIndexes()
            if idxs:
                irow = idxs[0].row()
                filepath = self.tw_scenefiles.model().index(irow, 0).data(Qt.UserRole)

        return filepath

    @err_catcher(name=__name__)
    def refreshScenefileList(self, sceneData: List[Dict[str, Any]], worker: Optional[Any] = None) -> None:
        """Refresh the table view with scenefile data.
        
        Args:
            sceneData: List of scenefile data dicts
            worker: Optional worker thread instance
        """
        twSorting = [
            self.tw_scenefiles.horizontalHeader().sortIndicatorSection(),
            self.tw_scenefiles.horizontalHeader().sortIndicatorOrder(),
        ]
        self.tw_scenefiles.setSortingEnabled(False)

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(
            [
                "",
                self.tableColumnLabels[self.core.tr("Version")],
                self.tableColumnLabels[self.core.tr("Comment")],
                self.tableColumnLabels[self.core.tr("Date")],
                self.tableColumnLabels[self.core.tr("User")],
            ]
        )
        # example filename: Body_mod_Modelling_v0002_details-added_rfr_.max
        # example filename: shot_0010_mod_main_v0002_details-added_rfr_.max

        for data in sceneData:
            row = []
            item = QStandardItem("█")
            item.setFont(QFont("SansSerif", 100))
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            item.setData(data["filename"], Qt.UserRole)

            if data.get("icon", ""):
                item.setIcon(data["icon"])
            else:
                item.setForeground(data["color"])

            row.append(item)

            version = data.get("version", "")
            item = QStandardItem(version)
            item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
            row.append(item)

            comment = data.get("comment", "")
            if not comment and not version:
                comment = os.path.basename(data.get("filename", ""))

            item = QStandardItem(str(comment))
            item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
            row.append(item)

            date = data.get("date")
            dateStr = self.core.getFormattedDate(date) if date else ""
            item = QStandardItem(dateStr)
            item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
            item.setData(data.get("date"), 0)
            row.append(item)

            item = QStandardItem(data.get("user", ""))
            item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
            row.append(item)

            if data["public"]:
                for k in row[1:]:
                    iFont = k.font()
                    iFont.setBold(True)
                    k.setFont(iFont)
                    k.setForeground(self.publicColor)

            model.appendRow(row)

        self.tw_scenefiles.setModel(model)
        self.tw_scenefiles.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Fixed
        )
        self.tw_scenefiles.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch
        )

        self.tw_scenefiles.resizeColumnsToContents()
        self.tw_scenefiles.horizontalHeader().setMinimumSectionSize(10)
        self.tw_scenefiles.setColumnWidth(0, 20 * self.core.uiScaleFactor)
        self.tw_scenefiles.setColumnWidth(1, 100 * self.core.uiScaleFactor)
        self.tw_scenefiles.setColumnWidth(3, 200 * self.core.uiScaleFactor)
        self.tw_scenefiles.setColumnWidth(4, 100 * self.core.uiScaleFactor)
        self.tw_scenefiles.sortByColumn(twSorting[0], twSorting[1])
        self.tw_scenefiles.setSortingEnabled(True)
        self.validateVisibleScenefileRows()

    @err_catcher(name=__name__)
    def departmentChanged(self, current: Optional[Any] = None, prev: Optional[Any] = None) -> None:
        """Handle department filter change.
        
        Args:
            current: Current selection
            prev: Previous selection
        """
        if current is not None or prev is not None:
            self.pendingNavigationData = None

        self.refreshTasks(restoreSelection=True)

    @err_catcher(name=__name__)
    def taskChanged(self, current: Optional[Any] = None, prev: Optional[Any] = None) -> None:
        """Handle task filter change.
        
        Args:
            current: Current selection
            prev: Previous selection
        """
        if current is not None or prev is not None:
            self.pendingNavigationData = None

        self.refreshScenefilesThreaded(restoreSelection=True)

    @err_catcher(name=__name__)
    def refreshEntityInfo(self) -> None:
        """Refresh entity info panel based on current entity type.
        """
        page = self.w_entities.getCurrentPage()
        entityType = page.entityType
        entities = [entity.copy() for entity in self.getCurrentEntities()]
        self.entityInfoRefreshId += 1
        refreshId = self.entityInfoRefreshId
        if len(entities) != 1 or (entityType == "asset" and entities[0]["type"] != "asset"):
            info = {"entities": entities}
            if entityType == "asset":
                self.refreshAssetinfo(info=info)
            elif entityType in ["shot", "sequence"]:
                self.refreshShotinfo(info=info)
            return

        def loadEntityInfo() -> Dict[str, Any]:
            info = {"entities": entities}
            entity = entities[0]
            if entityType == "asset" and entity["type"] == "asset":
                assetName = self.core.entities.getAssetNameFromPath(entity["paths"][0])
                info["description"] = self.core.entities.getAssetDescription(assetName)
            elif entityType in ["shot", "sequence"] and entity.get("shot") not in [None, "", "_sequence"]:
                info["range"] = self.core.entities.getShotRange(entity)
                if info["range"]:
                    info["handleRange"] = self.core.entities.getShotRange(entity, handles=True)

            info["metadata"] = self.core.entities.getMetaData(entity)
            previewPath = self.core.entities.getEntityPreviewPath(entity)
            if os.path.exists(previewPath):
                info["previewPath"] = previewPath
                info["previewImage"] = QImage(previewPath)
            else:
                handled = False
                for preview in self.core.callback(name="onSceneBrowserEntityPreviewRequested", args=[entity]):
                    if preview is not None:
                        handled = True
                        if isinstance(preview, QImage):
                            info["previewImage"] = preview
                            info["cachePreview"] = True
                        elif preview == "fallback":
                            info["previewFallback"] = True
                        break

                if not handled:
                    info["previewFallback"] = True

            return info

        def applyEntityInfo(info: Dict[str, Any]) -> None:
            if refreshId != self.entityInfoRefreshId or entityType != self.w_entities.getCurrentPage().entityType:
                return

            if entityType == "asset":
                self.refreshAssetinfo(info=info)
            elif entityType in ["shot", "sequence"]:
                self.refreshShotinfo(info=info)

        if entityType == "asset":
            self.refreshAssetinfo(info={"entities": entities})
        elif entityType in ["shot", "sequence"]:
            self.refreshShotinfo(info={"entities": entities})
        self.runEntityInfoWorker(loadEntityInfo, applyEntityInfo)

    @err_catcher(name=__name__)
    def refreshAssetinfo(self, info: Optional[Dict[str, Any]] = None) -> None:
        """Refresh asset information panel.
        
        Displays description, preview, and metadata for selected asset(s).
        """
        if info is None:
            self.refreshEntityInfo()
            return

        pmap = None
        for idx in reversed(range(self.lo_entityInfo.count())):
            item = self.lo_entityInfo.takeAt(idx)
            if not item:
                continue

            w = item.widget()
            if w:
                w.setVisible(False)
                w.setParent(None)
                w.deleteLater()

        curEntities = info["entities"]
        self.gb_entityInfo.setTitle(self.core.tr("Assetinfo"))

        if curEntities:
            if len(curEntities) > 1:
                description = self.core.tr("Multiple assets selected")
                l_info = QLabel(description)
                self.lo_entityInfo.addWidget(l_info)
            else:
                curEntity = curEntities[0]
                if curEntity["type"] == "asset":
                    description = info.get("description") or self.core.tr("< no description >")

                    l_key = QLabel(self.core.tr("Description:    "))
                    l_val = QLabel(description)
                    l_val.setWordWrap(True)
                    self.lo_entityInfo.addWidget(l_key, 0, 0)
                    self.lo_entityInfo.addWidget(l_val, 0, 1)

                    sp_info = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Fixed)
                    self.lo_entityInfo.addItem(sp_info, 0, 2)

                    pmap = self.getEntityInfoPreview(curEntity, info)
                    metadata = info.get("metadata")
                    if metadata:
                        idx = 1
                        for key in metadata:
                            if metadata[key]["show"]:
                                l_key = QLabel(key + ":    ")
                                l_val = QLabel(str(metadata[key]["value"]))
                                l_val.setWordWrap(True)
                                self.lo_entityInfo.addWidget(l_key, idx, 0)
                                self.lo_entityInfo.addWidget(l_val, idx, 1)
                                idx += 1
                else:
                    description = "%s selected" % (
                        curEntity["type"][0].upper() + curEntity["type"][1:]
                    )

                    l_info = QLabel(description)
                    self.lo_entityInfo.addWidget(l_info)
        else:
            description = self.core.tr("No asset selected")
            l_info = QLabel(description)
            self.lo_entityInfo.addWidget(l_info)

        if pmap is None:
            pmap = self.emptypmapPrv

        self.l_entityPreview.setMinimumSize(pmap.width(), pmap.height())
        self.l_entityPreview.setPixmap(pmap)

    @err_catcher(name=__name__)
    def getEntityInfoPreview(self, entity: Dict[str, Any], info: Dict[str, Any]) -> Optional[QPixmap]:
        image = info.get("previewImage")
        if image is not None and not image.isNull():
            pmap = QPixmap.fromImage(image)
            if info.get("cachePreview"):
                pmap = self.core.plugins.callUnpatchedFunction(
                    self.core.entities.setEntityPreview,
                    entity,
                    pmap,
                    width=self.shotPrvXres,
                    height=self.shotPrvYres,
                ) or pmap

            return self.core.media.scalePixmap(pmap, self.shotPrvXres, self.shotPrvYres)

        if info.get("previewPath"):
            return self.core.media.getPixmapFromPath(
                info["previewPath"], width=self.shotPrvXres, height=self.shotPrvYres
            )

        if info.get("previewFallback"):
            return self.core.entities.getEntityPreview(entity, self.shotPrvXres, self.shotPrvYres)

    @err_catcher(name=__name__)
    def refreshShotinfo(self, info: Optional[Dict[str, Any]] = None) -> None:
        """Refresh shot information panel.
        
        Displays framerange, preview, and metadata for selected shot(s).
        """
        if info is None:
            self.refreshEntityInfo()
            return

        pmap = None
        for idx in reversed(range(self.lo_entityInfo.count())):
            item = self.lo_entityInfo.takeAt(idx)
            if not item:
                continue

            w = item.widget()
            if w:
                w.setVisible(False)
                w.setParent(None)
                w.deleteLater()

        curEntities = info["entities"]
        self.gb_entityInfo.setTitle(self.core.tr("Shotinfo"))

        if curEntities:
            if len(curEntities) > 1:
                l_info = QLabel(self.core.tr("Multiple shots selected"))
                self.lo_entityInfo.addWidget(l_info)
            else:
                curEntity = curEntities[0]
                if curEntity["sequence"] and (not curEntity.get("shot") or (curEntity["shot"] == "_sequence")):
                    pass
                else:
                    startFrame = "?"
                    endFrame = "?"
                    suffix = ""

                    shotRange = info.get("range")
                    if shotRange and isinstance(shotRange, (list, tuple)):
                        if shotRange[0] is not None:
                            startFrame = shotRange[0]

                        if shotRange[1] is not None:
                            endFrame = shotRange[1]

                        handleRange = info.get("handleRange")
                        if handleRange != shotRange:
                            handleStartFrame = None
                            if handleRange[0] is not None:
                                handleStartFrame = handleRange[0]

                            handleEndFrame = None
                            if handleRange[1] is not None:
                                handleEndFrame = handleRange[1]

                            if handleStartFrame is not None and handleEndFrame is not None:
                                suffix = " (%s - %s)" % (handleStartFrame, handleEndFrame)

                    rangeStr = "%s - %s%s" % (startFrame, endFrame, suffix)
                    l_range1 = QLabel(self.core.tr("Framerange") + ":    ")
                    l_range2 = QLabel(rangeStr)
                    self.lo_entityInfo.addWidget(l_range1, 0, 0)
                    self.lo_entityInfo.addWidget(l_range2, 0, 1)

                sp_info = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Fixed)
                self.lo_entityInfo.addItem(sp_info, 0, 2)

                pmap = self.getEntityInfoPreview(curEntity, info)
                metadata = info.get("metadata")
                if metadata:
                    idx = 1
                    for key in metadata:
                        if not isinstance(metadata[key], dict):
                            continue

                        if metadata[key].get("show"):
                            l_key = QLabel(key + ":    ")
                            l_val = QLabel(str(metadata[key]["value"]))
                            l_val.setWordWrap(True)
                            self.lo_entityInfo.addWidget(l_key, idx, 0)
                            self.lo_entityInfo.addWidget(l_val, idx, 1)
                            idx += 1

        else:
            l_info = QLabel(self.core.tr("No shot selected"))
            self.lo_entityInfo.addWidget(l_info)

        if not pmap:
            pmap = self.emptypmapPrv

        self.l_entityPreview.setMinimumSize(pmap.width(), pmap.height())
        self.l_entityPreview.setPixmap(pmap)

    @err_catcher(name=__name__)
    def rclEntityPreview(self, pos: Any) -> None:
        """Handle right-click on entity preview.
        
        Shows context menu for capture/browse/edit preview.
        
        Args:
            pos: Click position.
        """
        rcmenu = QMenu(self)

        entity = self.getCurrentEntity()
        if not entity or (entity.get("type") == "asset" and not entity.get("asset_path")) or (entity.get("type") == "shot" and not entity.get("shot")):
            return

        if entity["type"] == "asset":
            exp = QAction(self.core.tr("Edit asset description..."), self)
            exp.triggered.connect(self.editAsset)
            rcmenu.addAction(exp)

            copAct = QAction(self.core.tr("Capture assetpreview"), self)
            copAct.triggered.connect(lambda: self.captureEntityPreview(entity))
            rcmenu.addAction(copAct)

            copAct = QAction(self.core.tr("Browse assetpreview..."), self)
            copAct.triggered.connect(lambda: self.browseEntityPreview(entity))
            rcmenu.addAction(copAct)

            clipAct = QAction(self.core.tr("Paste assetpreview from clipboard"), self)
            clipAct.triggered.connect(
                lambda: self.pasteEntityPreviewFromClipboard(entity)
            )
            rcmenu.addAction(clipAct)

        elif entity["type"] == "shot":
            exp = QAction(self.core.tr("Edit shot settings..."), self)
            exp.triggered.connect(lambda: self.editShot(entity))
            rcmenu.addAction(exp)

            copAct = QAction(self.core.tr("Capture shotpreview"), self)
            copAct.triggered.connect(lambda: self.captureEntityPreview(entity))
            rcmenu.addAction(copAct)

            copAct = QAction(self.core.tr("Browse shotpreview..."), self)
            copAct.triggered.connect(lambda: self.browseEntityPreview(entity))
            rcmenu.addAction(copAct)

            clipAct = QAction(self.core.tr("Paste shotpreview from clipboard"), self)
            clipAct.triggered.connect(
                lambda: self.pasteEntityPreviewFromClipboard(entity)
            )
            rcmenu.addAction(clipAct)
        elif entity["type"] == "sequence":
            exp = QAction(self.core.tr("Edit sequence settings..."), self)
            exp.triggered.connect(lambda: self.editShot(entity))
            rcmenu.addAction(exp)

            copAct = QAction(self.core.tr("Capture sequencepreview"), self)
            copAct.triggered.connect(lambda: self.captureEntityPreview(entity))
            rcmenu.addAction(copAct)

            copAct = QAction(self.core.tr("Browse sequencepreview..."), self)
            copAct.triggered.connect(lambda: self.browseEntityPreview(entity))
            rcmenu.addAction(copAct)

            clipAct = QAction(self.core.tr("Paste sequencepreview from clipboard"), self)
            clipAct.triggered.connect(
                lambda: self.pasteEntityPreviewFromClipboard(entity)
            )
            rcmenu.addAction(clipAct)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def browseEntityPreview(self, entity: Dict[str, Any]) -> None:
        """Browse for entity preview image file.
        
        Args:
            entity: Entity data dictionary.
        """
        formats = "Image File (*.jpg *.png *.exr)"

        imgPath = QFileDialog.getOpenFileName(
            self, self.core.tr("Select preview-image"), self.core.projectPath, formats
        )[0]

        if not imgPath:
            return

        if os.path.splitext(imgPath)[1] == ".exr":
            previewImg = self.core.media.getPixmapFromExrPath(
                imgPath, width=self.shotPrvXres, height=self.shotPrvYres
            )
        else:
            previewImg = self.core.media.getPixmapFromPath(imgPath)
            if previewImg.width() == 0:
                warnStr = self.core.tr("Cannot read image") + ": %s" % imgPath
                self.core.popup(warnStr)
                return

        self.core.entities.setEntityPreview(
            entity, previewImg, width=self.shotPrvXres, height=self.shotPrvYres
        )
        self.refreshEntityInfo()
        if self.core.getConfig("browser", "showEntityPreviews", config="user"):
            self.refreshUI()

    @err_catcher(name=__name__)
    def captureEntityPreview(self, entity: Dict[str, Any]) -> None:
        """Capture screen area as entity preview.
        
        Args:
            entity: Entity data dictionary.
        """
        from PrismUtils import ScreenShot
        self.window().setWindowOpacity(0)

        previewImg = ScreenShot.grabScreenArea(self.core)
        self.window().setWindowOpacity(1)

        if previewImg:
            self.core.entities.setEntityPreview(
                entity, previewImg, width=self.shotPrvXres, height=self.shotPrvYres
            )
            self.refreshEntityInfo()
            if self.core.getConfig("browser", "showEntityPreviews", config="user"):
                self.refreshUI()

    @err_catcher(name=__name__)
    def pasteEntityPreviewFromClipboard(self, entity: Dict[str, Any]) -> None:
        """Paste entity preview from clipboard.
        
        Args:
            entity: Entity data dictionary.
        """
        pmap = self.core.media.getPixmapFromClipboard()
        if not pmap:
            self.core.popup(self.core.tr("No image in clipboard."))
            return

        self.core.entities.setEntityPreview(
            entity, pmap, width=self.shotPrvXres, height=self.shotPrvYres
        )
        self.refreshEntityInfo()
        if self.core.getConfig("browser", "showEntityPreviews", config="user"):
            self.refreshUI()

    @err_catcher(name=__name__)
    def editEntity(self) -> None:
        """Edit the current entity (asset or shot).
        """
        entity = self.getCurrentEntity()
        if entity.get("type") == "asset":
            self.editAsset()
        elif entity.get("type") in ["shot", "sequence"]:
            self.editShot(entity)

    @err_catcher(name=__name__)
    def editAsset(self) -> None:
        """Open asset edit dialog.
        """
        assetData = self.getCurrentEntity()
        if not assetData or (assetData.get("type") == "asset" and not assetData.get("asset_path")):
            return

        assetName = self.core.entities.getAssetNameFromPath(assetData["asset_path"])
        description = self.core.entities.getAssetDescription(assetName) or ""

        descriptionDlg = PrismWidgets.EnterText()
        self.core.parentWindow(descriptionDlg)
        descriptionDlg.setWindowTitle(self.core.tr("Assetinfo"))
        descriptionDlg.l_info.setText(self.core.tr("Description:"))
        descriptionDlg.te_text.setPlainText(description)

        c = descriptionDlg.te_text.textCursor()
        c.setPosition(0)
        c.setPosition(len(description), QTextCursor.KeepAnchor)
        descriptionDlg.te_text.setTextCursor(c)

        descriptionDlg.metaWidget = MetaDataWidget.MetaDataWidget(self.core, assetData)
        descriptionDlg.layout().insertWidget(
            descriptionDlg.layout().count() - 1, descriptionDlg.metaWidget
        )

        result = descriptionDlg.exec_()

        if result:
            descriptionDlg.metaWidget.save(assetData)
            description = descriptionDlg.te_text.toPlainText()
            self.core.entities.setAssetDescription(assetName, description)
            self.refreshEntityInfo()

    @err_catcher(name=__name__)
    def editShot(self, shotData: Optional[Dict[str, Any]] = None) -> None:
        """Open shot edit dialog.
        
        Args:
            shotData: Optional shot data, uses current if None.
        """
        self.w_entities.getCurrentPage().editShotDlg(shotData)

    @err_catcher(name=__name__)
    def createTaskDlg(self) -> Optional[bool]:
        """Open dialog to create new tasks.
        
        Returns:
            False if dialog creation prevented by callback, None otherwise.
        """
        entities = self.getCurrentEntities()
        curDep = self.getCurrentDepartment()
        presets = self.core.entities.getDefaultTasksForDepartment(entities[0]["type"], curDep) or []
        existingTasks = self.core.entities.getCategories(entities[0], step=curDep)
        presets = [p for p in presets if p not in existingTasks]

        self.newItem = ItemList.ItemList(core=self.core, entities=entities, mode="tasks")
        self.newItem.setModal(True)
        self.newItem.tw_steps.setColumnCount(1)
        self.newItem.tw_steps.setHorizontalHeaderLabels([self.core.tr("Department")])
        self.newItem.tw_steps.horizontalHeader().setVisible(False)
        self.core.parentWindow(self.newItem, parent=self)
        self.newItem.tw_steps.doubleClicked.connect(lambda x=None, b=self.newItem.buttonBox.buttons()[0]:self.newItem.buttonboxClicked(b))
        self.newItem.setWindowTitle(self.core.tr("Add Tasks"))

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "create.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.newItem.buttonBox.buttons()[0].setIcon(icon)

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "delete.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.newItem.buttonBox.buttons()[-1].setIcon(icon)

        for task in presets:
            rc = self.newItem.tw_steps.rowCount()
            self.newItem.tw_steps.insertRow(rc)
            nameItem = QTableWidgetItem(task)
            nameItem.setData(Qt.UserRole, task)
            self.newItem.tw_steps.setItem(rc, 0, nameItem)
            nameItem.setSelected(True)

        if presets:
            self.newItem.l_title = QLabel("Default Tasks:")
            self.newItem.layout().insertWidget(0, self.newItem.l_title)
            self.newItem.tw_steps.setFocus()
            height = 250 if len(presets) < 3 else 350
            self.newItem.resize(self.newItem.width(), height)
        else:
            self.newItem.e_tasks.setFocus()
            self.newItem.tw_steps.setHidden(True)
            if hasattr(self.newItem, "l_tasks"):
                self.newItem.l_tasks.setText("Tasks:")

            self.newItem.updateGeometry()
            self.newItem.adjustSize()
            self.newItem.update()
            self.newItem.resize(self.newItem.width(), 0)

        self.core.callback(name="onTaskDlgOpen", args=[self, self.newItem])
        if not getattr(self.newItem, "allowShow", True):
            return False

        self.newItem.exec_()

    @err_catcher(name=__name__)
    def createTask(self, tasks: List[str]) -> None:
        """Create tasks in current department.
        
        Args:
            tasks: List of task names to create.
        """
        self.activateWindow()

        curEntities = self.getCurrentEntities()
        curDep = self.getCurrentDepartment()

        for task in tasks:
            for curEntity in curEntities:
                self.core.entities.createCategory(
                    entity=curEntity, step=curDep, category=task
                )

        self.taskToSelect = tasks[0]
        self.refreshTasks(restoreSelection=True)

    @err_catcher(name=__name__)
    def createDepartmentDlg(self) -> Optional[bool]:
        """Open dialog to create new departments.
        
        Returns:
            False if dialog creation prevented by callback, None otherwise.
        """
        entities = self.getCurrentEntities() or []
        entities = [entity for entity in entities if entity.get("type") != "assetFolder"]
        if not entities:
            return

        if entities[0].get("type", "") == "asset":
            deps = self.core.projects.getAssetDepartments()
        elif entities[0].get("type", "") in ["shot", "sequence"]:
            deps = self.core.projects.getShotDepartments()
        else:
            return

        validDeps = []
        for dep in deps:
            if not dep.get("abbreviation"):
                continue

            for entity in entities:
                basePath = self.core.getEntityPath(reqEntity="step", entity=entity)
                if not os.path.exists(os.path.join(basePath, dep["abbreviation"])):
                    validDeps.append(dep)
                    break

        self.ss = ItemList.ItemList(core=self.core, entities=entities, mode="departments")
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "create.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.ss.buttonBox.buttons()[0].setIcon(icon)

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "delete.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.ss.buttonBox.buttons()[-1].setIcon(icon)

        self.ss.setWindowTitle(self.core.tr("Add Departments"))
        self.core.parentWindow(self.ss, parent=self)
        self.ss.tw_steps.setFocus()
        self.ss.tw_steps.doubleClicked.connect(lambda x=None, b=self.ss.buttonBox.buttons()[0]:self.ss.buttonboxClicked(b))

        self.ss.tw_steps.setColumnCount(1)
        self.ss.tw_steps.setHorizontalHeaderLabels([self.core.tr("Department")])
        self.ss.tw_steps.horizontalHeader().setVisible(False)
        for department in validDeps:
            rc = self.ss.tw_steps.rowCount()
            self.ss.tw_steps.insertRow(rc)
            name = "%s (%s)" % (department["name"], department["abbreviation"])
            nameItem = QTableWidgetItem(name)
            departmentIcon = self.core.entities.getDepartmentIcon(
                department["name"]
            )
            if not departmentIcon.isNull():
                nameItem.setIcon(departmentIcon)

            nameItem.setData(Qt.UserRole, department)
            self.ss.tw_steps.setItem(rc, 0, nameItem)

        self.core.callback(name="onDepartmentDlgOpen", args=[self, self.ss])
        if not getattr(self.ss, "allowShow", True):
            return False

        self.ss.exec_()

    @err_catcher(name=__name__)
    def copyToGlobal(self, localPath: str) -> None:
        """Copy scenefile from local to global storage.
        
        Args:
            localPath: Local file or directory path.
        """
        dstPath = localPath.replace(self.core.localProjectPath, self.core.projectPath)

        if os.path.isdir(localPath):
            if os.path.exists(dstPath):
                for i in os.walk(dstPath):
                    if i[2] != []:
                        msg = self.core.tr("Found existing files in the global directory. Copy to global was canceled.")
                        self.core.popup(msg)
                        return

                shutil.rmtree(dstPath)

            shutil.copytree(localPath, dstPath)

            try:
                shutil.rmtree(localPath)
            except:
                msg = self.core.tr("Could not delete the local file. Probably it is used by another process.")
                self.core.popup(msg)

        else:
            if not os.path.exists(os.path.dirname(dstPath)):
                os.makedirs(os.path.dirname(dstPath))

            self.core.copySceneFile(localPath, dstPath)
            self.refreshScenefilesThreaded()

    @err_catcher(name=__name__)
    def editComment(self, filepath: str) -> None:
        """Edit scenefile comment.
        
        Args:
            filepath: Path to scenefile.
        """
        data = self.core.getScenefileData(filepath)
        comment = data["comment"] if "comment" in data else ""

        dlg_ec = PrismWidgets.CreateItem(
            core=self.core, startText=comment, showType=False, valueRequired=False, validate=False
        )

        dlg_ec.setModal(True)
        self.core.parentWindow(dlg_ec, parent=self)
        dlg_ec.e_item.setFocus()
        dlg_ec.setWindowTitle(self.core.tr("Edit Comment"))
        dlg_ec.l_item.setText(self.core.tr("New comment:"))
        dlg_ec.buttonBox.buttons()[0].setText(self.core.tr("Save"))

        result = dlg_ec.exec_()

        if not result:
            return

        comment = dlg_ec.e_item.text()
        newPath = self.core.entities.setComment(filepath, comment)

        self.refreshScenefilesThreaded(wait=True)
        fileNameData = self.core.getScenefileData(newPath)
        self.navigate(data=fileNameData)

    @err_catcher(name=__name__)
    def editDescription(self, filepath: str) -> None:
        """Edit scenefile description.
        
        Args:
            filepath: Path to scenefile.
        """
        data = self.core.getScenefileData(filepath)
        description = data.get("description", "")

        descriptionDlg = PrismWidgets.EnterText()
        descriptionDlg.setModal(True)
        self.core.parentWindow(descriptionDlg, parent=self)
        descriptionDlg.setWindowTitle(self.core.tr("Enter description"))
        descriptionDlg.l_info.setText(self.core.tr("Description:"))
        descriptionDlg.te_text.setPlainText(description)
        descriptionDlg.te_text.selectAll()
        result = descriptionDlg.exec_()

        if not result:
            return

        description = descriptionDlg.te_text.toPlainText()
        self.core.entities.setDescription(filepath, description)
        self.refreshScenefilesThreaded(wait=True)
        fileNameData = self.core.getScenefileData(filepath)
        self.navigate(data=fileNameData)

    @err_catcher(name=__name__)
    def sceneDragEnterEvent(self, e: Any) -> None:
        """Handle drag enter event for scenefile ingestion.
        
        Args:
            e: Drag enter event.
        """
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def sceneDragMoveEvent(self, e: Any) -> None:
        """Handle drag move event and update visual feedback.
        
        Args:
            e: Drag move event.
        """
        if e.mimeData().hasUrls():
            e.accept()
            if self.b_sceneLayoutList.isChecked():
                if not self.tw_scenefiles.styleSheet():
                    self.tw_scenefiles.setStyleSheet(
                        "QTableView { border-style: dashed; border-color: rgb(100, 200, 100);  border-width: 2px; }"
                    )
            elif self.b_sceneLayoutItems.isChecked():
                if not self.w_scenefileItems.styleSheet():
                    self.w_scenefileItems.setStyleSheet(
                        "QWidget#itemview { border-style: dashed; border-color: rgb(100, 200, 100);  border-width: 2px; }"
                    )

        else:
            e.ignore()

    @err_catcher(name=__name__)
    def sceneDragLeaveEvent(self, e: Any) -> None:
        """Handle drag leave event and reset visual feedback.
        
        Args:
            e: Drag leave event.
        """
        if self.b_sceneLayoutList.isChecked():
            self.tw_scenefiles.setStyleSheet("")
        elif self.b_sceneLayoutItems.isChecked():
            self.w_scenefileItems.setStyleSheet("")

    @err_catcher(name=__name__)
    def sceneDropEvent(self, e: Any) -> None:
        """Handle drop event for scenefile ingestion.
        
        Args:
            e: Drop event.
        """
        if e.mimeData().hasUrls():
            if self.b_sceneLayoutList.isChecked():
                self.tw_scenefiles.setStyleSheet("")
            elif self.b_sceneLayoutItems.isChecked():
                self.w_scenefileItems.setStyleSheet("")

            e.setDropAction(Qt.LinkAction)
            e.accept()

            files = [
                os.path.normpath(str(url.toLocalFile())) for url in e.mimeData().urls()
            ]
            entity = self.getCurrentEntity()
            self.ingestScenefiles(entity, files)
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def ingestScenefiles(self, entity: Dict[str, Any], files: List[str]) -> None:
        """Ingest external files as new scenefiles.
        
        Opens dialog to configure version and comment before ingesting.
        
        Args:
            entity: Entity context dictionary.
            files: List of file paths to ingest.
        """
        task = self.getCurrentTask()
        if not task:
            self.core.popup(self.core.tr("No valid context is selected"))
            return

        if getattr(self, "dlg_ingestSettings", None):
            self.dlg_ingestSettings.close()

        self.dlg_ingestSettings = IngestSettings(self, entity, files)
        self.dlg_ingestSettings.show()


class IngestSettings(QDialog):
    """Dialog for configuring scenefile ingestion settings.
    
    Allows setting version, comment, and rename option before ingesting files.
    
    Attributes:
        core: Prism core instance.
        browser: Parent SceneBrowser widget.
        entity: Entity context.
        files: List of files to ingest.
    """
    def __init__(self, browser: Any, entity: Dict[str, Any], files: List[str]) -> None:
        """Initialize the ingest settings dialog.
        
        Args:
            browser: Parent SceneBrowser widget.
            entity: Entity data dictionary.
            files: List of file paths to ingest.
        """
        super(IngestSettings, self).__init__()
        self.core = browser.core
        self.browser = browser
        self.entity = entity
        self.files = files
        self.setupUi()
        self.setVersionNext()

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Set up the dialog UI.
        """
        self.setWindowTitle(self.core.tr("Ingest Scenefile"))
        self.core.parentWindow(self, parent=self.browser)

        self.l_version = QLabel(self.core.tr("Version:"))
        self.sp_version = QSpinBox()
        self.sp_version.setValue(1)
        self.sp_version.setMinimum(1)
        self.sp_version.setMaximum(99999)
        self.sp_version.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sp_version.customContextMenuRequested.connect(self.onVersionRightClicked)
        self.l_comment = QLabel(self.core.tr("Comment:"))
        self.e_comment = QLineEdit()

        self.l_rename = QLabel(self.core.tr("Rename files:"))
        self.chb_rename = QCheckBox()
        self.chb_rename.setChecked(True)

        self.lo_main = QGridLayout()
        self.setLayout(self.lo_main)

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton(self.core.tr("Ingest"), QDialogButtonBox.AcceptRole)
        self.bb_main.addButton(self.core.tr("Cancel"), QDialogButtonBox.RejectRole)

        self.bb_main.clicked.connect(self.onButtonClicked)
        self.lo_main.addWidget(self.l_version)
        self.lo_main.addWidget(self.sp_version, 0, 1)
        self.lo_main.addWidget(self.l_comment)
        self.lo_main.addWidget(self.e_comment, 1, 1)
        self.lo_main.addWidget(self.l_rename)
        self.lo_main.addWidget(self.chb_rename, 2, 1)
        self.e_comment.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.sp_main = QSpacerItem(0, 0, QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.lo_main.addItem(self.sp_main, 3, 0)
        self.lo_main.addWidget(self.bb_main, 4, 1)
        self.e_comment.setFocus()

    @err_catcher(name=__name__)
    def sizeHint(self) -> Any:
        """Get preferred dialog size.
        
        Returns:
            QSize with preferred dimensions.
        """
        return QSize(300, 150)

    @err_catcher(name=__name__)
    def onVersionRightClicked(self, pos: Any) -> None:
        """Show version spinbox context menu.
        
        Args:
            pos: Click position.
        """
        rcmenu = QMenu(self)

        copAct = QAction(self.core.tr("Next available version"), self)
        copAct.triggered.connect(self.setVersionNext)
        rcmenu.addAction(copAct)

        exp = QAction(self.core.tr("Detect version from filename"), self)
        exp.triggered.connect(self.setVersionFromSource)
        rcmenu.addAction(exp)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def setVersionNext(self) -> None:
        """Set version to next available number.
        """
        department = self.browser.getCurrentDepartment()
        task = self.browser.getCurrentTask()
        version = self.core.entities.getHighestVersion(self.entity, department, task)
        versionNum = self.core.products.getIntVersionFromVersionName(version)
        self.sp_version.setValue(versionNum)

    @err_catcher(name=__name__)
    def setVersionFromSource(self) -> None:
        """Detect and set version from source filename.
        """
        result = re.search(r"\d{%s}" % self.core.versionPadding, os.path.basename(self.files[0]))
        if not result:
            return

        versionNum = int(result.group())
        self.sp_version.setValue(versionNum)

    @err_catcher(name=__name__)
    def onButtonClicked(self, button: Any) -> None:
        """Handle button clicks.
        
        Args:
            button: Clicked button widget.
        """
        if button.text() == self.core.tr("Ingest"):
            department = self.browser.getCurrentDepartment()
            task = self.browser.getCurrentTask()
            data = {
                "version": self.core.versionFormat % self.sp_version.value(),
                "comment": self.e_comment.text()
            }
            self.core.entities.ingestScenefiles(
                self.files,
                self.entity,
                department,
                task,
                finishCallback=self.browser.refreshScenefilesThreaded,
                data=data,
                rename=self.chb_rename.isChecked(),
            )
            self.accept()
        elif button.text() == self.core.tr("Cancel"):
            self.close()


class SceneReBuildStepRunDlg(QDialog):
    """Dialog to review and run scenebuilding updates on the current scene."""

    def __init__(
        self,
        core: Any,
        steps: List[Dict[str, Any]],
        templateScene: Optional[str] = None,
        stepContext: Optional[Dict[str, Any]] = None,
        useCurrentScene: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        super(SceneReBuildStepRunDlg, self).__init__(parent)
        self.core = core
        self.steps = self._cloneStepsForDialog(steps)
        self.templateScene = templateScene
        self.stepContext = dict(stepContext or {})
        self.useCurrentScene = useCurrentScene
        self._setupUi()
        self._populateSteps()

    def _cloneStepsForDialog(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        cloned = []
        for step in steps or []:
            cloned.append(self._cloneStepForDialog(step))

        return cloned

    def _cloneStepForDialog(self, step: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return copy.deepcopy(step)
        except Exception:
            pass

        data = dict(step or {})
        updateData = data.get("update_data")
        if isinstance(updateData, dict):
            updateDataCopy = {}
            for key, value in updateData.items():
                if isinstance(value, QWidget):
                    updateDataCopy[key] = value
                    continue

                try:
                    updateDataCopy[key] = copy.deepcopy(value)
                except Exception:
                    updateDataCopy[key] = value

            data["update_data"] = updateDataCopy

        return data

    def _setupUi(self) -> None:
        windowTitle = "Update Scene" if self.useCurrentScene else "Build Scene"
        self.setWindowTitle(self.core.tr(windowTitle))
        self.setMinimumWidth(840)
        self.setMinimumHeight(460)
        scaleFactor = getattr(self.core, "uiScaleFactor", 1) or 1
        self.resize(int(1400 * scaleFactor), int(680 * scaleFactor))

        lo_main = QVBoxLayout(self)
        w_header = QWidget(self)
        lo_header = QHBoxLayout(w_header)
        lo_header.setContentsMargins(0, 0, 0, 0)

        info = (
            "Select scenebuilding steps to update the current scene."
            if self.useCurrentScene
            else "Select scenebuilding steps to run when building the new scene."
        )
        l_info = QLabel(self.core.tr(info))
        l_info.setWordWrap(True)
        lo_header.addWidget(l_info)

        if not self.useCurrentScene:
            self.b_template = QPushButton(self)
            self._updateTemplateButton()
            self.b_template.clicked.connect(self._showTemplateMenu)

        self.chb_showUpToDate = QCheckBox(self.core.tr("show up-to-date steps"))
        self.chb_showUpToDate.setChecked(not self.useCurrentScene)
        self.chb_showUpToDate.toggled.connect(self._onShowUpToDateToggled)
        if self.useCurrentScene:
            lo_header.addWidget(self.chb_showUpToDate, 0, Qt.AlignRight | Qt.AlignVCenter)

        lo_main.addWidget(w_header)

        if not self.useCurrentScene:
            lo_template = QHBoxLayout()
            lo_template.setContentsMargins(0, 0, 0, 0)
            lo_template.addWidget(self.b_template)
            lo_template.addStretch()
            lo_main.addLayout(lo_template)

        self.splitter = QSplitter(Qt.Horizontal, self)
        lo_main.addWidget(self.splitter, 1)

        w_left = QWidget(self.splitter)
        lo_left = QVBoxLayout(w_left)
        lo_left.setContentsMargins(0, 0, 0, 0)

        self.tw_steps = QTreeWidget()
        self.tw_steps.setRootIsDecorated(False)
        self.tw_steps.setColumnCount(3)
        self.tw_steps.setHeaderLabels(["", self.core.tr("Step"), self.core.tr("Summary")])
        self.tw_steps.header().setSectionResizeMode(0, QHeaderView.Fixed)
        self.tw_steps.header().resizeSection(0, 28)
        self.tw_steps.header().setSectionResizeMode(1, QHeaderView.Interactive)
        self.tw_steps.header().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tw_steps.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tw_steps.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tw_steps.customContextMenuRequested.connect(self._openStepsContextMenu)
        self.tw_steps.itemSelectionChanged.connect(self._onSelectionChanged)
        self.tw_steps.itemChanged.connect(self._onStepItemChanged)
        lo_left.addWidget(self.tw_steps, 1)

        self.l_status = QLabel()
        statusFont = self.l_status.font()
        if statusFont.pointSize() > 8:
            statusFont.setPointSize(statusFont.pointSize() - 1)

        self.l_status.setFont(statusFont)
        statusPal = self.l_status.palette()
        statusPal.setColor(
            QPalette.WindowText,
            statusPal.color(QPalette.Disabled, QPalette.WindowText),
        )
        self.l_status.setPalette(statusPal)
        self.l_status.setStyleSheet("padding-top: 2px;")
        lo_left.addWidget(self.l_status)

        w_right = QWidget(self.splitter)
        lo_right = QVBoxLayout(w_right)
        lo_right.setContentsMargins(8, 0, 0, 0)

        self.l_detailsTitle = QLabel(self.core.tr("Details"))
        lo_right.addWidget(self.l_detailsTitle)

        self.w_detailsStack = QStackedWidget()

        self.te_details = QPlainTextEdit()
        self.te_details.setReadOnly(True)
        self.w_detailsStack.addWidget(self.te_details)

        self.w_detailsWidget = QWidget()
        self.lo_detailsWidget = QVBoxLayout(self.w_detailsWidget)
        self.lo_detailsWidget.setContentsMargins(0, 0, 0, 0)
        self.lo_detailsWidget.setSpacing(0)
        self.w_detailsStack.addWidget(self.w_detailsWidget)

        lo_right.addWidget(self.w_detailsStack)

        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.setSizes(
            [int(600 * scaleFactor), int(600 * scaleFactor)]
        )

        self.bb_main = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.bb_main.accepted.connect(self._runCheckedSteps)
        self.bb_main.rejected.connect(self.close)
        b_run = self.bb_main.button(QDialogButtonBox.Ok)
        if b_run:
            b_run.setText(self.core.tr("Run" if self.useCurrentScene else "Build"))

        lo_main.addWidget(self.bb_main)

    def _updateTemplateButton(self) -> None:
        templateName = (
            os.path.basename(self.templateScene)
            if self.templateScene
            else self.core.tr("New Scene")
        )
        self.b_template.setText(self.core.tr("Template: %s") % templateName)

    def _showTemplateMenu(self) -> None:
        menu = QMenu(self.b_template)
        emptyAction = QAction(self.core.tr("New Scene"), menu)
        emptyAction.triggered.connect(lambda: self._setTemplateScene(None))
        menu.addAction(emptyAction)

        scenes = [
            scene
            for scene in self.core.entities.getPresetScenes(self.stepContext)
            if os.path.splitext(scene["path"])[1] in self.core.appPlugin.sceneFormats
        ]
        dirMenus = {}
        for scene in sorted(scenes, key=lambda x: os.path.basename(x["label"]).lower()):
            folders = scene["label"].split("/")
            curPath = ""
            for index, folder in enumerate(folders):
                if index == len(folders) - 1:
                    action = QAction(folder, menu)
                    action.triggered.connect(
                        lambda checked=False, path=scene["path"]: self._setTemplateScene(path)
                    )
                    dirMenus.get(curPath, menu).addAction(action)
                else:
                    curMenu = dirMenus.get(curPath, menu)
                    curPath = os.path.join(curPath, folder)
                    if curPath not in dirMenus:
                        dirMenus[curPath] = QMenu(folder, menu)
                        curMenu.addMenu(dirMenus[curPath])

        menu.exec_(self.b_template.mapToGlobal(self.b_template.rect().bottomLeft()))

    def _setTemplateScene(self, filepath: Optional[str]) -> None:
        self.templateScene = filepath
        self._updateTemplateButton()

    def _getSelectedStepIndices(self) -> List[int]:
        indices = []
        for item in self.tw_steps.selectedItems():
            stepIdx = item.data(0, Qt.UserRole + 1)
            if stepIdx is None:
                continue

            if stepIdx not in indices:
                indices.append(stepIdx)

        return indices

    def _refreshSteps(self, stepIndices: Optional[List[int]] = None) -> None:
        if not self.stepContext:
            return

        selectedStepIndices = self._getSelectedStepIndices()
        self._storeVisibleStepStates()

        if stepIndices is None:
            stepIndices = list(range(len(self.steps)))

        for stepIdx in stepIndices:
            if stepIdx is None or stepIdx < 0 or stepIdx >= len(self.steps):
                continue

            step = self.steps[stepIdx]
            updateData = self.core.entities.getSceneBuildingStepUpdateData(step, self.stepContext)
            if updateData:
                step["update_data"] = updateData

        self._populateSteps(selectedStepIndices=selectedStepIndices)

    def _openStepsContextMenu(self, pos: QPoint) -> None:
        menu = QMenu(self.tw_steps)

        selectedStepIndices = self._getSelectedStepIndices()

        refreshIconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "refresh.png"
        )
        refreshIcon = self.core.media.getColoredIcon(refreshIconPath)
        runSelectedIconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "play.png"
        )
        runSelectedIcon = self.core.media.getColoredIcon(runSelectedIconPath)

        act_runSelected = QAction(runSelectedIcon, self.core.tr("Run selected"), self.tw_steps)
        act_runSelected.setEnabled(self.useCurrentScene and bool(selectedStepIndices))
        act_runSelected.triggered.connect(self._runSelectedSteps)
        menu.addAction(act_runSelected)

        act_refresh = QAction(refreshIcon, self.core.tr("Refresh"), self.tw_steps)
        act_refresh.triggered.connect(lambda: self._refreshSteps())
        menu.addAction(act_refresh)

        menu.exec_(self.tw_steps.viewport().mapToGlobal(pos))

    def _runSelectedSteps(self) -> None:
        if not self.useCurrentScene:
            return

        selectedItems = self.tw_steps.selectedItems()
        if not selectedItems:
            return

        self._storeVisibleStepStates()

        if not self.stepContext:
            self.core.popup(self.core.tr("Missing rebuild context."), parent=self)
            return

        department = self.stepContext.get("department")
        task = self.stepContext.get("task")
        if not department or not task:
            self.core.popup(self.core.tr("Missing rebuild context."), parent=self)
            return

        entity = dict(self.stepContext)
        entity.pop("department", None)
        entity.pop("task", None)
        entity.pop("extension", None)

        stepOverrides = []
        for item in selectedItems:
            data = dict(self.steps[item.data(0, Qt.UserRole + 1)])
            data["enabled"] = True
            data.pop("_checked", None)
            data.pop("update_data", None)
            stepOverrides.append(data)

        if not stepOverrides:
            return

        self.core.entities.buildScene(
            entity=entity,
            department=department,
            task=task,
            stepOverrides=stepOverrides,
            useCurrentScene=True,
        )
        self._refreshSteps()

    def _runCheckedSteps(self) -> None:
        if not self.useCurrentScene:
            self.accept()
            return

        if not self.stepContext:
            self.core.popup(self.core.tr("Missing rebuild context."), parent=self)
            return

        stepOverrides = self.getEnabledSteps()
        if not stepOverrides:
            self.core.popup(
                self.core.tr("No scenebuilding steps are selected."),
                parent=self,
            )
            return

        department = self.stepContext.get("department")
        task = self.stepContext.get("task")
        if not department or not task:
            self.core.popup(self.core.tr("Missing rebuild context."), parent=self)
            return

        entity = dict(self.stepContext)
        entity.pop("department", None)
        entity.pop("task", None)
        entity.pop("extension", None)

        filepath = self.core.entities.buildScene(
            entity=entity,
            department=department,
            task=task,
            stepOverrides=stepOverrides,
            useCurrentScene=True,
        )
        if filepath:
            self.core.addToRecent(filepath)

        self.accept()

    def _syncStepRuntimeData(self, step: Dict[str, Any]) -> None:
        if not isinstance(step, dict):
            return

        updateData = step.get("update_data") or {}
        if not isinstance(updateData, dict):
            return

        summaryWidget = updateData.get("summary_widget")
        if not isinstance(summaryWidget, QWidget):
            return

        runtimeDataFn = getattr(summaryWidget, "getSceneBuildRuntimeData", None)
        if not callable(runtimeDataFn):
            return

        runtimeData = runtimeDataFn() or {}
        if not isinstance(runtimeData, dict):
            return

        importProductsSelection = runtimeData.get("importProductsSelection")
        if isinstance(importProductsSelection, dict):
            step["_importProductsSelection"] = dict(importProductsSelection)

    def _storeVisibleStepStates(self) -> None:
        for idx in range(self.tw_steps.topLevelItemCount()):
            item = self.tw_steps.topLevelItem(idx)
            stepIdx = item.data(0, Qt.UserRole + 1)
            if stepIdx is None:
                continue

            self.steps[stepIdx]["_checked"] = item.checkState(0) == Qt.Checked
            self._syncStepRuntimeData(self.steps[stepIdx])

    def _shouldShowStep(self, step: Dict[str, Any]) -> bool:
        updateData = step.get("update_data") or {}
        action = (updateData.get("action") or "").lower()
        if self.chb_showUpToDate.isChecked():
            return True

        return action != "no change"

    def _getStepSummary(self, step: Dict[str, Any]) -> str:
        updateData = step.get("update_data") or {}
        action = (updateData.get("action") or "").lower()
        summary = updateData.get("summary") or ""
        if summary:
            return summary

        if action == "no change":
            return self.core.tr("Up to date" if self.useCurrentScene else "Nothing to import")

        return self.core.tr("No summary available.")

    def _getStepDescription(self, step: Dict[str, Any]) -> str:
        return (step.get("description") or "").strip()

    def _getStepDetailsText(self, step: Dict[str, Any]) -> str:
        description = self._getStepDescription(step)
        summary = self._getStepSummary(step)
        if description:
            return self.core.tr("Description:\n%s\n\nSummary:\n%s") % (description, summary)

        return summary

    def _wrapDetailsWidgetWithDescription(self, widget: QWidget, description: str) -> QWidget:
        wrapper = QWidget()
        lo_wrapper = QVBoxLayout(wrapper)
        lo_wrapper.setContentsMargins(0, 0, 0, 0)
        lo_wrapper.setSpacing(8)

        l_desc = QLabel(description)
        l_desc.setWordWrap(True)
        l_desc.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lo_wrapper.addWidget(l_desc)
        lo_wrapper.addWidget(widget)

        return wrapper

    def _clearDetailsWidget(self) -> None:
        while self.lo_detailsWidget.count() > 0:
            item = self.lo_detailsWidget.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

    def _showDetailsText(self, text: str) -> None:
        self._clearDetailsWidget()
        self.te_details.setPlainText(text)
        self.w_detailsStack.setCurrentWidget(self.te_details)

    def _showDetailsWidget(self, widget: Any) -> None:
        self._clearDetailsWidget()
        self.lo_detailsWidget.addWidget(widget)
        self.w_detailsStack.setCurrentWidget(self.w_detailsWidget)

    def _refreshStatusLabel(self) -> None:
        updates = 0
        upToDate = 0
        for step in self.steps:
            action = ((step.get("update_data") or {}).get("action") or "").lower()
            if action == "update":
                updates += 1
            elif action == "no change":
                upToDate += 1

        shown = self.tw_steps.topLevelItemCount()
        checked = 0
        for idx in range(shown):
            item = self.tw_steps.topLevelItem(idx)
            if item and item.checkState(0) == Qt.Checked:
                checked += 1

        if self.useCurrentScene:
            self.l_status.setText(
                self.core.tr("Updates: %s | Up-to-date: %s | Showing: %s | Checked: %s")
                % (updates, upToDate, shown, checked)
            )
        else:
            self.l_status.setText(
                self.core.tr("Steps: %s | Checked: %s") % (shown, checked)
            )

    def _populateSteps(self, selectedStepIndices: Optional[List[int]] = None) -> None:
        self.tw_steps.blockSignals(True)
        self.tw_steps.clear()
        selectedStepIndices = selectedStepIndices or []
        firstItem = None
        for stepIdx, step in enumerate(self.steps):
            if not self._shouldShowStep(step):
                continue

            item = QTreeWidgetItem(
                [
                    "",
                    step.get("label", step.get("name", "")),
                    self._getStepSummary(step),
                ]
            )
            flags = item.flags() | Qt.ItemIsUserCheckable
            item.setFlags(flags)
            checked = step.get("_checked", step.get("enabled", True))
            item.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
            item.setData(0, Qt.UserRole + 1, stepIdx)
            self.tw_steps.addTopLevelItem(item)
            if firstItem is None:
                firstItem = item

            if stepIdx in selectedStepIndices:
                item.setSelected(True)

        self.tw_steps.resizeColumnToContents(0)
        self.tw_steps.resizeColumnToContents(1)

        self._refreshStatusLabel()

        if self.tw_steps.topLevelItemCount() > 0:
            if not self.tw_steps.selectedItems() and firstItem:
                self.tw_steps.setCurrentItem(firstItem)
            elif self.tw_steps.selectedItems():
                self.tw_steps.scrollToItem(self.tw_steps.selectedItems()[0])
        else:
            self._showDetailsText(self.core.tr("No steps to display."))

        self.tw_steps.blockSignals(False)
        self._onSelectionChanged()

    def _onShowUpToDateToggled(self, checked: bool) -> None:
        selectedStepIndices = self._getSelectedStepIndices()
        self._storeVisibleStepStates()
        self._populateSteps(selectedStepIndices=selectedStepIndices)

    def _onSelectionChanged(self) -> None:
        items = self.tw_steps.selectedItems()
        if not items:
            self._showDetailsText(self.core.tr("Select a step to see details."))
            return

        if len(items) > 1:
            self._showDetailsText(
                self.core.tr("%s steps selected. Right-click to refresh or run selected steps.")
                % len(items)
            )
            return

        step = self.steps[items[0].data(0, Qt.UserRole + 1)]
        updateData = step.get("update_data") or {}
        description = self._getStepDescription(step)
        summaryWidget = updateData.get("summary_widget")
        if isinstance(summaryWidget, QWidget):
            if description:
                widget = self._wrapDetailsWidgetWithDescription(summaryWidget, description)
                self._showDetailsWidget(widget)
            else:
                self._showDetailsWidget(summaryWidget)
        else:
            self._showDetailsText(self._getStepDetailsText(step))

    def _onStepItemChanged(self, item: QTreeWidgetItem, column: int) -> None:
        if column == 0:
            self._refreshStatusLabel()

    def getEnabledSteps(self) -> List[Dict[str, Any]]:
        self._storeVisibleStepStates()

        steps = []
        for idx in range(self.tw_steps.topLevelItemCount()):
            item = self.tw_steps.topLevelItem(idx)
            if item.checkState(0) != Qt.Checked:
                continue

            data = dict(self.steps[item.data(0, Qt.UserRole + 1)])
            data["enabled"] = True
            data.pop("_checked", None)
            data.pop("update_data", None)
            steps.append(data)

        return steps


class ScenefileItem(QWidget):
    """Widget representing a scenefile in grid view.
    
    Displays preview, version, comment, date, user, and location info.
    
    Attributes:
        signalSelect (Signal): Emitted when item is selected.
        signalReleased (Signal): Emitted when mouse is released on item.
        core: Prism core instance.
        browser: Parent SceneBrowser widget.
        data (Dict): Scenefile data.
        isLoaded (bool): Whether UI has been loaded with data.
        state (str): Selection state ("selected" or "deselected").
        previewSize (List[int]): Preview image dimensions.
        itemPreviewWidth (int): Item preview width in pixels.
        itemPreviewHeight (int): Item preview height in pixels.
    """

    signalSelect = Signal(object)
    signalReleased = Signal(object)

    def __init__(self, browser: Any, data: Dict[str, Any]) -> None:
        """Initialize scenefile item widget.
        
        Args:
            browser: Parent SceneBrowser widget.
            data: Scenefile data dictionary.
        """
        super(ScenefileItem, self).__init__()
        self.core = browser.core
        self.browser = browser
        self.data = data
        self.isLoaded = False
        self.state = "deselected"
        self.previewSize = [self.core.scenePreviewWidth, self.core.scenePreviewHeight]
        self.itemPreviewWidth = 120
        self.itemPreviewHeight = 69
        self.setupUi()

    def mouseReleaseEvent(self, event: Any) -> None:
        """Handle mouse release event.
        
        Args:
            event: Qt mouse event
        """
        if event.button() == Qt.MiddleButton:
            self.core.copyToClipboard(self.data["filename"])
            event.accept()
            return

        super(ScenefileItem, self).mouseReleaseEvent(event)
        self.signalReleased.emit(self)
        event.accept()

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Set up the item UI with preview, info, and location widgets.
        """
        self.setObjectName("texture")
        self.applyStyle(self.state)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.lo_main = QHBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.setSpacing(15)
        # Keep a horizontal inner frame so the preview doesn't paint over card border.
        self.lo_main.setContentsMargins(1, 1, 1, 1)

        self.l_preview = QLabel()
        self.l_preview.setMinimumWidth(self.itemPreviewWidth)
        self.l_preview.setMinimumHeight(self.itemPreviewHeight)
        self.l_preview.setMaximumWidth(self.itemPreviewWidth)
        self.l_preview.setMaximumHeight(self.itemPreviewHeight)
        self.spacer1 = QSpacerItem(0, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.l_version = QLabel()
        # self.l_version.setWordWrap(True)
        font = self.l_version.font()
        font.setBold(True)
        self.l_version.setStyleSheet("font-size: 8pt;")
        self.l_version.setFont(font)

        self.spacer2 = QSpacerItem(0, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.lo_info = QVBoxLayout()
        self.lo_info.setSpacing(0)
        self.l_icon = QLabel()

        self.lo_description = QVBoxLayout()
        self.l_comment = QLabel()
        self.l_description = QLabel()

        self.lo_user = QVBoxLayout()
        self.lo_user.setSpacing(0)
        self.w_user = QWidget()
        self.lo_userIcon = QHBoxLayout(self.w_user)
        self.lo_userIcon.setContentsMargins(0, 0, 0, 0)
        self.l_userIcon = QLabel()
        self.l_userIcon.setPixmap(self.browser.pmapUser)
        self.l_user = QLabel()
        self.l_user.setAlignment(Qt.AlignRight)
        self.lo_userIcon.addStretch()
        self.lo_userIcon.addWidget(self.l_userIcon)
        self.lo_userIcon.addWidget(self.l_user)

        self.w_date = QWidget()
        self.lo_dateIcon = QHBoxLayout(self.w_date)
        self.lo_dateIcon.setContentsMargins(0, 0, 0, 0)
        self.l_dateIcon = QLabel()
        self.l_dateIcon.setPixmap(self.browser.pmapDate)
        self.l_date = QLabel()
        self.l_date.setAlignment(Qt.AlignRight)
        self.lo_dateIcon.addStretch()
        self.lo_dateIcon.addWidget(self.l_dateIcon)
        self.lo_dateIcon.addWidget(self.l_date)

        self.spacer3 = QSpacerItem(0, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacer4 = QSpacerItem(15, 0, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacer5 = QSpacerItem(0, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacer6 = QSpacerItem(0, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacer7 = QSpacerItem(20, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.lo_info.addItem(self.spacer1)
        self.lo_info.addWidget(self.l_version)
        self.lo_info.addItem(self.spacer2)
        self.lo_info.addWidget(self.l_icon)
        self.lo_info.addStretch()

        self.lo_description.addItem(self.spacer3)
        self.lo_description.addWidget(self.l_comment)
        self.lo_description.addWidget(self.l_description)
        self.lo_description.addStretch()

        self.lo_user.addItem(self.spacer5)
        self.lo_user.addWidget(self.w_user)
        self.lo_user.addStretch()
        self.lo_user.addWidget(self.w_date)
        self.lo_user.addItem(self.spacer6)

        self.lo_main.addWidget(self.l_preview)
        self.lo_main.addLayout(self.lo_info)
        self.lo_main.addItem(self.spacer7)
        self.lo_main.addLayout(self.lo_description)
        self.lo_main.addStretch(1000)
        self.locationLabels = {}
        if self.browser.projectBrowser and len(self.browser.projectBrowser.locations) > 1:
            self.spacer7 = QSpacerItem(0, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.spacer8 = QSpacerItem(0, 20, QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.lo_location = QVBoxLayout()
            self.lo_location.addItem(self.spacer7)

            for location in self.browser.projectBrowser.locations:
                l_loc = QLabel()
                l_loc.setToolTip(self.core.tr("Version exists in") + " %s" % location["name"])
                self.locationLabels[location["name"]] = l_loc
                if "icon" not in location:
                    location["icon"] = self.browser.projectBrowser.getLocationIcon(location["name"])

                if location["icon"]:
                    l_loc.setPixmap(location["icon"].pixmap(18, 18))
                else:
                    l_loc.setText(location["name"])
                
                self.lo_location.addWidget(l_loc)

            self.lo_location.addItem(self.spacer8)
            self.lo_main.addLayout(self.lo_location)

        self.lo_main.addLayout(self.lo_user)
        self.lo_main.addItem(self.spacer4)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.rightClicked)
        self.l_preview.setContextMenuPolicy(Qt.CustomContextMenu)
        self.l_preview.customContextMenuRequested.connect(self.previewRightClicked)

    @err_catcher(name=__name__)
    def refreshUi(self) -> None:
        """Refresh UI with scenefile data.
        
        Loads and displays version, comment, date, user, preview, and location info.
        """
        self.isLoaded = True
        if not self.data["__cfg_loaded__"]:
            cfgData = self.core.getScenefileData(self.data["filename"], entityType=self.data["type"])
            cfgData.update(self.data)
            self.data = cfgData

            self.data["__cfg_loaded__"] = True

        if type(self.data.get("date")) not in (int, float):
            self.data["date"] = self.core.getFileModificationDate(self.data["filename"], asString=False)

        version = self.getVersion()
        descr = self.getDescription()
        comment = self.getComment()
        date = self.getDate()
        user = self.getUser()
        icon = self.getIcon()

        if not comment and not version:
            comment = os.path.basename(self.data.get("filename", ""))

        self.refreshPreview()
        self.l_version.setText(version)
        self.setIcon(icon)
        self.l_comment.setText(str(comment))
        self.l_description.setText(descr)
        self.l_date.setText(date)
        self.l_user.setText(user)

        if len(self.browser.projectBrowser.locations) > 1:
            for loc in self.locationLabels:
                self.locationLabels[loc].setHidden(True)

            for loc in self.browser.projectBrowser.locations:
                if loc.get("name") == "global" and self.data.get("public"):
                    self.locationLabels["global"].setHidden(False)

                elif loc.get("name") == "local" and self.core.useLocalFiles:
                    localPath = self.core.convertPath(self.data["filename"], "local")
                    if os.path.exists(localPath):
                        self.locationLabels["local"].setHidden(False)

                elif loc.get("name") in self.data.get("locations", {}):
                    self.locationLabels[loc["name"]].setHidden(False)

    @err_catcher(name=__name__)
    def setIcon(self, icon: Any) -> None:
        """Set the file type icon.
        
        Args:
            icon: QIcon or QColor for the icon.
        """
        self.l_icon.setToolTip(os.path.basename(self.data["filename"]))
        if isinstance(icon, QIcon):
            self.l_icon.setPixmap(icon.pixmap(24, 24))
        else:
            pmap = QPixmap(20, 20)
            pmap.fill(Qt.transparent)
            painter = QPainter(pmap)
            painter.setPen(Qt.NoPen)
            painter.setBrush(icon)
            painter.drawEllipse(0, 0, 10, 10)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.end()
            self.l_icon.setPixmap(pmap)

    @err_catcher(name=__name__)
    def refreshPreview(self) -> None:
        """Refresh the preview image.
        """
        windowHandle = self.window().windowHandle()
        screen = windowHandle.screen() if windowHandle else QApplication.primaryScreen()
        devicePixelRatio = screen.devicePixelRatio() if screen else 1
        ppixmap = self.getPreviewImage()
        ppixmap = self.core.media.scalePixmap(
            ppixmap,
            round(self.itemPreviewWidth * devicePixelRatio),
            round(self.itemPreviewHeight * devicePixelRatio),
            fitIntoBounds=False,
            crop=True,
        )
        ppixmap = self.getRoundedLeftPreviewPixmap(
            ppixmap, radius=round(10 * devicePixelRatio)
        )
        ppixmap.setDevicePixelRatio(devicePixelRatio)
        self.l_preview.setPixmap(ppixmap)

    @err_catcher(name=__name__)
    def getRoundedLeftPreviewPixmap(self, pixmap: QPixmap, radius: int = 10) -> QPixmap:
        """Return a preview pixmap with only left corners rounded.

        Args:
            pixmap: Source preview pixmap.
            radius: Radius in pixels for top-left and bottom-left corners.

        Returns:
            Rounded preview pixmap.
        """
        if not pixmap or pixmap.isNull():
            return pixmap

        width = pixmap.width()
        height = pixmap.height()
        if width <= 0 or height <= 0:
            return pixmap

        insetX = 0
        insetY = 0
        targetWidth = max(0, width - insetX)
        targetHeight = max(0, height - (insetY * 2))
        if targetWidth <= 0 or targetHeight <= 0:
            return pixmap

        radius = max(0, min(int(radius), int(targetHeight / 2), int(targetWidth / 2)))
        if radius == 0:
            return pixmap

        rounded = QPixmap(width, height)
        rounded.fill(Qt.transparent)

        x = insetX
        y = insetY
        right = width
        bottom = height - insetY

        path = QPainterPath()
        path.moveTo(x + radius, y)
        path.lineTo(right, y)
        path.lineTo(right, bottom)
        path.lineTo(x + radius, bottom)
        path.quadTo(x, bottom, x, bottom - radius)
        path.lineTo(x, y + radius)
        path.quadTo(x, y, x + radius, y)
        path.closeSubpath()

        targetRect = QRect(x, y, targetWidth, targetHeight)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setClipPath(path)
        painter.drawPixmap(targetRect, pixmap, pixmap.rect())
        painter.end()
        return rounded

    @err_catcher(name=__name__)
    def getPreviewImage(self) -> Any:
        """Get preview image pixmap.
        
        Returns:
            QPixmap with preview image or black placeholder.
        """
        pixmap = None
        if self.data.get("preview", ""):
            pixmap = self.core.media.getPixmapFromPath(self.data.get("preview", ""))
        
        if not pixmap:
            pixmap = QPixmap(300, 169)
            pixmap.fill(Qt.black)

        return pixmap

    @err_catcher(name=__name__)
    def getVersion(self) -> str:
        """Get version string.
        
        Returns:
            Version string (e.g., "v0001").
        """
        version = self.data.get("version", "")
        return version

    @err_catcher(name=__name__)
    def getComment(self) -> str:
        """Get comment string.
        
        Returns:
            Comment text.
        """
        comment = self.data.get("comment", "")
        return comment

    @err_catcher(name=__name__)
    def getDescription(self) -> str:
        """Get description string.
        
        Returns:
            Description text.
        """
        description = self.data.get("description", "")
        return description

    @err_catcher(name=__name__)
    def getDate(self) -> str:
        """Get formatted date string with optional file size.
        
        Returns:
            Date string, optionally with file size.
        """
        date = self.data.get("date")
        dateStr = self.core.getFormattedDate(date) if date else ""

        if self.browser.projectBrowser.act_filesizes.isChecked():
            if "size" in self.data:
                size = self.data["size"]
            elif os.path.exists(self.data["filename"]):
                size = float(os.stat(self.data["filename"]).st_size / 1024.0 / 1024.0)
            else:
                size = 0

            dateStr += " - %.2f mb" % size

        return dateStr

    @err_catcher(name=__name__)
    def getUser(self) -> str:
        """Get username string.
        
        Returns:
            Username who created the scenefile.
        """
        user = self.data.get("username", "")
        if user:
            return user

        user = self.data.get("user", "")
        return user

    @err_catcher(name=__name__)
    def getIcon(self) -> Any:
        """Get file type icon.
        
        Returns:
            QIcon or QColor for the file type.
        """
        if self.data.get("icon", ""):
            return self.data["icon"]
        else:
            return self.data.get("color", [128, 128, 128])

    @err_catcher(name=__name__)
    def applyStyle(self, styleType: str) -> None:
        """Apply visual style to item.
        
        Args:
            styleType: Style name ("deselected", "selected", "hover", "hoverSelected").
        """
        borderColor = (
            "rgb(70, 90, 120)" if self.state == "selected" else "rgb(70, 90, 120)"
        )
        ssheet = (
            """
            QWidget#texture {
                border: 1px solid %s;
                border-radius: 10px;
            }
        """
            % borderColor
        )
        if styleType == "deselected":
            pass
        elif styleType == "selected":
            ssheet = """
                QWidget#texture {
                    border: 1px solid rgb(70, 90, 120);
                    background-color: rgba(255, 255, 255, 30);
                    border-radius: 10px;
                }
                QWidget {
                    background-color: rgba(255, 255, 255, 0);
                }

            """
        elif styleType == "hoverSelected":
            ssheet = """
                QWidget#texture {
                    border: 1px solid rgb(70, 90, 120);
                    background-color: rgba(255, 255, 255, 35);
                    border-radius: 10px;
                }
                QWidget {
                    background-color: rgba(255, 255, 255, 0);
                }

            """
        elif styleType == "hover":
            ssheet += """
                QWidget {
                    background-color: rgba(255, 255, 255, 0);
                }
                QWidget#texture {
                    background-color: rgba(255, 255, 255, 20);
                }
            """

        self.setStyleSheet(ssheet)

    @err_catcher(name=__name__)
    def mousePressEvent(self, event: Any) -> None:
        """Handle mouse press.
        
        Args:
            event: Mouse event.
        """
        if event.button() == Qt.MiddleButton:
            event.accept()
            return

        self.select()

    @err_catcher(name=__name__)
    def enterEvent(self, event: Any) -> None:
        """Handle mouse enter.
        
        Args:
            event: Enter event.
        """
        if self.isSelected():
            self.applyStyle("hoverSelected")
        else:
            self.applyStyle("hover")

    @err_catcher(name=__name__)
    def leaveEvent(self, event: Any) -> None:
        """Handle mouse leave.
        
        Args:
            event: Leave event.
        """
        self.applyStyle(self.state)

    @err_catcher(name=__name__)
    def mouseDoubleClickEvent(self, event: Any) -> None:
        """Handle double-click to open scenefile.
        
        Args:
            event: Mouse event.
        """
        if event.button() == Qt.MiddleButton:
            event.accept()
            return

        self.browser.exeFile(self.data["filename"], source=self)

    @err_catcher(name=__name__)
    def select(self) -> None:
        """Select this item.
        """
        wasSelected = self.isSelected()
        self.signalSelect.emit(self)
        if not wasSelected:
            self.state = "selected"
            self.applyStyle(self.state)
            self.setFocus()

    @err_catcher(name=__name__)
    def deselect(self) -> None:
        """Deselect this item.
        """
        if self.state != "deselected":
            self.state = "deselected"
            self.applyStyle(self.state)

    @err_catcher(name=__name__)
    def isSelected(self) -> bool:
        """Check if item is selected.
        
        Returns:
            True if selected, False otherwise.
        """
        return self.state == "selected"

    @err_catcher(name=__name__)
    def rightClicked(self, pos: Any) -> None:
        """Handle right-click.
        
        Args:
            pos: Click position.
        """
        self.browser.openScenefileContextMenu(self.data["filename"])

    @err_catcher(name=__name__)
    def previewRightClicked(self, pos: Any) -> None:
        """Handle right-click on preview.
        
        Args:
            pos: Click position.
        """
        rcmenu = QMenu(self.browser)

        copAct = QAction(self.core.tr("Capture preview"), self.browser)
        copAct.triggered.connect(lambda: self.captureScenePreview(self.data))

        exp = QAction(self.core.tr("Browse preview..."), self.browser)
        exp.triggered.connect(self.browseScenePreview)
        rcmenu.addAction(exp)

        rcmenu.addAction(copAct)
        clipAct = QAction(self.core.tr("Paste preview from clipboard"), self.browser)
        clipAct.triggered.connect(
            lambda: self.pasteScenePreviewFromClipboard(self.data)
        )
        rcmenu.addAction(clipAct)

        prvAct = QAction(self.core.tr("Set as %spreview" % self.data.get("type", "")), self)
        prvAct.triggered.connect(self.setPreview)
        rcmenu.addAction(prvAct)
        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def setPreview(self) -> None:
        """Set this scenefile's preview as entity preview.
        """
        pm = self.getPreviewImage()
        self.core.entities.setEntityPreview(self.data, pm)
        self.browser.refreshEntityInfo()

    @err_catcher(name=__name__)
    def browseScenePreview(self) -> None:
        """Browse for preview image file.
        """
        formats = "Image File (*.jpg *.png *.exr)"

        imgPath = QFileDialog.getOpenFileName(
            self, self.core.tr("Select preview-image"), self.core.projectPath, formats
        )[0]

        if not imgPath:
            return

        if os.path.splitext(imgPath)[1] == ".exr":
            pmsmall = self.core.media.getPixmapFromExrPath(
                imgPath, width=self.previewSize[0], height=self.previewSize[1]
            )
        else:
            pm = self.core.media.getPixmapFromPath(imgPath)
            if pm.width() == 0:
                warnStr = self.core.tr("Cannot read image") + ": %s" % imgPath
                self.core.popup(warnStr)
                return

            pmsmall = self.core.media.scalePixmap(
                pm, self.previewSize[0], self.previewSize[1], fitIntoBounds=False, crop=True
            )

        self.core.entities.setScenePreview(self.data["filename"], pmsmall)
        self.refreshPreview()

    @err_catcher(name=__name__)
    def captureScenePreview(self, entity: Dict[str, Any]) -> None:
        """Capture screen area as scenefile preview.
        
        Args:
            entity: Entity data dictionary.
        """
        from PrismUtils import ScreenShot
        self.window().setWindowOpacity(0)
        previewImg = ScreenShot.grabScreenArea(self.core)
        self.window().setWindowOpacity(1)
        if previewImg:
            previewImg = self.core.media.scalePixmap(
                previewImg,
                self.previewSize[0],
                self.previewSize[1],
                fitIntoBounds=False, crop=True
            )
            self.core.entities.setScenePreview(self.data["filename"], previewImg)
            self.refreshPreview()

    @err_catcher(name=__name__)
    def pasteScenePreviewFromClipboard(self, pos: Any) -> None:
        """Paste scenefile preview from clipboard.
        
        Args:
            pos: Click position (unused).
        """
        pmap = self.core.media.getPixmapFromClipboard()
        if not pmap:
            self.core.popup(self.core.tr("No image in clipboard."))
            return

        pmap = self.core.media.scalePixmap(
            pmap, self.previewSize[0], self.previewSize[1], fitIntoBounds=False, crop=True
        )
        self.core.entities.setScenePreview(self.data["filename"], pmap)
        self.refreshPreview()


class DateDelegate(QStyledItemDelegate):
    """Delegate for formatting date columns.
    """
    def displayText(self, value: Any, locale: Any) -> str:
        """Format date value for display.
        
        Args:
            value: Date value (timestamp).
            locale: Locale for formatting.
            
        Returns:
            Formatted date string.
        """
        return self.core.getFormattedDate(value)
