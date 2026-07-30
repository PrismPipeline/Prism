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
import shutil
import logging
from typing import Any, Optional, List, Dict, Tuple

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils import PrismWidgets, ProjectWidgets
from PrismUtils.Decorators import err_catcher
from UserInterfaces import ProductBrowser_ui


logger = logging.getLogger(__name__)


class ProductBrowser(QDialog, ProductBrowser_ui.Ui_dlg_ProductBrowser):
    """Product browser dialog for managing and viewing product versions.
    
    Displays a hierarchical view of entities (assets/shots), their products, and version history.
    Allows users to browse, import, and manage product versions with support for both local
    and global storage locations.
    
    Attributes:
        productPathSet (Signal): Emitted when a product path is selected, passes the file path.
        versionsUpdated (Signal): Emitted when the versions list is refreshed.
        closing (Signal): Emitted when the dialog is closing.
        core: Reference to the Prism core instance.
        projectBrowser: Reference to parent ProjectBrowser instance if embedded.
        importState: Reference to import state for filtering/validation.
        productPath (Optional[str]): Currently selected product file path.
        customProduct (bool): Whether the selected product is a custom file.
        autoClose (bool): Whether to auto-close after selecting a product.
        handleImport (bool): Whether to automatically handle import after selection.
        versionLabels (List[str]): Column headers for the version table.
        initialized (bool): Whether the browser has been initialized.
        prevDelIdx (Optional[int]): Previous delegate index for cleanup.
        w_entities: Entity widget for browsing assets/shots.
        tw_identifier: Tree widget displaying products.
        tw_versions: Table widget displaying versions.
    """
    productPathSet = Signal(object)
    versionsUpdated = Signal()
    closing = Signal()

    def __init__(self, core: Any, importState: Optional[Any] = None, refresh: bool = True, projectBrowser: Optional[Any] = None) -> None:
        """Initialize the Product Browser dialog.
        
        Args:
            core: Prism core instance.
            importState: Optional import state for filtering and validation.
            refresh: Whether to refresh data on initialization.
            projectBrowser: Optional parent ProjectBrowser instance.
        """
        QDialog.__init__(self)
        self.setupUi(self)
        self.core = core
        self.projectBrowser = projectBrowser
        self.core.parentWindow(self)

        logger.debug("Initializing Product Browser")

        self.importState = importState
        self.productPath = None
        self.customProduct = False
        self.autoClose = True
        self.handleImport = True
        self.versionLabels = ["Version", "Comment", "Type", "User", "Date", "Path"]
        self.initialized = False
        self.prevDelIdx = None

        self.loadLayout()
        self.connectEvents()
        self.core.callback(name="onProductBrowserOpen", args=[self])
        self.versionHeaderChanged()
        if refresh:
            self.entered()

    @err_catcher(name=__name__)
    def entered(self, prevTab: Optional[Any] = None, navData: Optional[Dict[str, Any]] = None) -> None:
        """Handle browser activation and navigation.
        
        Called when the tab becomes active or when navigating to specific data.
        Initializes the entity tree and navigates to the specified product/version.
        
        Args:
            prevTab: Previous tab widget for syncing navigation state.
            navData: Optional navigation data containing entity, product, and version info.
        """
        if prevTab:
            if hasattr(prevTab, "w_entities"):
                navData = prevTab.w_entities.getCurrentData()
            elif hasattr(prevTab, "getSelectedData"):
                navData = prevTab.getSelectedData()

        if not self.initialized:
            isScenefile = False
            if not navData:
                navPath = self.core.getCurrentFileName()
                if self.importState:
                    impPath = self.importState.getImportPath()
                    if impPath and os.path.exists(os.path.dirname(impPath)):
                        navData = self.getDataFromPath(impPath)

                if not navData:
                    isScenefile = True
                    navData = self.getDataFromPath(navPath, scenefile=isScenefile)

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
            if navData:
                self.navigateToFile(data=navData, identifier=navData.get("product"), version=navData.get("version"), scenefile=isScenefile)

            self.initialized = True

        if prevTab:
            if hasattr(prevTab, "w_entities"):
                self.w_entities.syncFromWidget(prevTab.w_entities, navData=navData)
            elif hasattr(prevTab, "getSelectedData"):
                self.w_entities.navigate(navData)

    @err_catcher(name=__name__)
    def closeEvent(self, event: Optional[Any] = None) -> None:
        """Handle dialog close event.
        
        Closes any open detail windows and emits the closing signal.
        
        Args:
            event: Close event object.
        """
        if hasattr(self, "detailWin") and self.detailWin.isVisible():
            self.detailWin.close()

        self.closing.emit()

    @err_catcher(name=__name__)
    def loadLayout(self) -> None:
        """Load and configure the UI layout.
        
        Sets up entity widget, custom import button, loading saved settings,
        configuring drag-drop functionality, and initializing table columns.
        """
        import EntityWidget

        self.w_entities = EntityWidget.EntityWidget(core=self.core, refresh=False, mode="products")
        self.splitter1.insertWidget(0, self.w_entities)
        if os.getenv("PRISM_PRODUCT_BROWSER_ADD_GL_DUMMY", "1") == "1":
            try:
                from PySide6.QtOpenGLWidgets import QOpenGLWidget
            except ImportError:
                logger.warning("PySide6.QtOpenGLWidgets is not available. Cannot add OpenGL widget.")
            else:
                self.gl_dummy = QOpenGLWidget()
                self.gl_dummy.setHidden(True)
                self.lo_main.addWidget(self.gl_dummy)

        self.b_custom = QPushButton("Import custom files")
        self.w_entities.layout().addWidget(self.b_custom)

        if self.core.appPlugin.pluginName == "Standalone":
            self.b_custom.setVisible(False)

        cData = self.core.getConfig()
        brsData = cData.get("browser", {})

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

        self.refreshLocations()
        if self.projectBrowser and self.projectBrowser.act_rememberWidgetSizes.isChecked():
            if "productsSplitter1" in brsData:
                self.splitter1.setSizes(brsData["productsSplitter1"])

        self.tw_versions.setAcceptDrops(True)
        self.tw_versions.dragEnterEvent = self.productDragEnterEvent
        self.tw_versions.dragMoveEvent = self.productDragMoveEvent
        self.tw_versions.dragLeaveEvent = self.productDragLeaveEvent
        self.tw_versions.dropEvent = self.productDropEvent

        if self.core.products.getUseProductPreviews():
            self.tw_versions.viewport().installEventFilter(self)
            self.tw_versions.viewport().setMouseTracking(True)

        self.tw_versions.setDragEnabled(True)
        self.setStyleSheet("QSplitter::handle{background-color: transparent}")
        self.updateSizeColumn()
        self.tw_versions.sortByColumn(0, Qt.DescendingOrder)

    # add this method to your class (e.g. QMainWindow or QWidget where self.tw_test lives)
    def eventFilter(self, source: Any, event: Any) -> bool:
        """Filter events for version table viewport.
        
        Handles mouse move, leave, and focus out events for hover previews.
        
        Args:
            source: Event source object.
            event: Event to filter.
            
        Returns:
            True if event was handled, False otherwise.
        """
        if event.type() == QEvent.MouseMove:
            self.tableMoveEvent(event)   # call your existing handler
        elif event.type() == QEvent.Leave:
            self.tableLeaveEvent(event)  # custom leave handler
        elif event.type() == QEvent.FocusOut:
            self.tableFocusOutEvent(event)  # custom focus out handler

        return super().eventFilter(source, event)

    @err_catcher(name=__name__)
    def refreshLocations(self) -> None:
        """Refresh the Location column visibility based on available locations.
        
        Adds or removes the Location column header depending on whether
        multiple storage locations (local/global) are available.
        """
        if len(self.w_entities.getLocations()) > 1 or (self.projectBrowser and len(self.projectBrowser.locations) > 1):
            if "Location" not in self.versionLabels:
                self.versionLabels.insert(3, "Location")
                self.versionHeaderChanged()

        else:
            if "Location" in self.versionLabels:
                self.versionLabels.remove("Location")
                self.versionHeaderChanged()

    @err_catcher(name=__name__)
    def saveSettings(self, data: Dict[str, Any]) -> None:
        """Save browser settings to configuration.
        
        Args:
            data: Configuration dictionary to update with browser settings.
        """
        data["browser"]["productsSplitter1"] = self.splitter1.sizes()

    @err_catcher(name=__name__)
    def versionHeaderChanged(self) -> None:
        """Update version table headers and column properties.
        
        Configures column visibility, resize modes, and delegates based on
        current version label configuration.
        """
        twSorting = [
            self.tw_versions.horizontalHeader().sortIndicatorSection(),
            self.tw_versions.horizontalHeader().sortIndicatorOrder(),
        ]

        self.tw_versions.setColumnCount(len(self.versionLabels))
        self.tw_versions.setHorizontalHeaderLabels(self.versionLabels)
        delegate = DateDelegate()
        delegate.core = self.core
        idx = self.versionLabels.index("Date")
        if self.prevDelIdx is not None and idx != self.prevDelIdx:
            self.tw_versions.setItemDelegateForColumn(self.prevDelIdx, self.prevDel)

        self.prevDel = self.tw_versions.itemDelegateForColumn(idx)
        self.tw_versions.setItemDelegateForColumn(self.versionLabels.index("Date"), delegate)
        self.prevDelIdx = idx
        for idx in range(len(self.versionLabels)):
            self.tw_versions.setColumnHidden(idx, idx == len(self.versionLabels) - 1)

        if "Version" in self.versionLabels:
            self.tw_versions.horizontalHeader().setSectionResizeMode(
                self.versionLabels.index("Version"), QHeaderView.ResizeToContents
            )
        if "Comment" in self.versionLabels:
            self.tw_versions.horizontalHeader().setSectionResizeMode(
                self.versionLabels.index("Comment"), QHeaderView.Stretch
            )
        if "Type" in self.versionLabels:
            self.tw_versions.horizontalHeader().setSectionResizeMode(
                self.versionLabels.index("Type"), QHeaderView.ResizeToContents
            )
        if "Location" in self.versionLabels:
            self.tw_versions.horizontalHeader().setSectionResizeMode(
                self.versionLabels.index("Location"), QHeaderView.ResizeToContents
            )
        if "User" in self.versionLabels:
            self.tw_versions.horizontalHeader().setSectionResizeMode(
                self.versionLabels.index("User"), QHeaderView.ResizeToContents
            )
        if "Size" in self.versionLabels:
            self.tw_versions.horizontalHeader().setSectionResizeMode(
                self.versionLabels.index("Size"), QHeaderView.ResizeToContents
            )
        if "Date" in self.versionLabels:
            self.tw_versions.horizontalHeader().setSectionResizeMode(
                self.versionLabels.index("Date"), QHeaderView.ResizeToContents
            )
        if "Date123" in self.versionLabels:
            self.tw_versions.horizontalHeader().setSectionResizeMode(
                self.versionLabels.index("Date123"), QHeaderView.ResizeToContents
            )
        self.tw_versions.sortByColumn(twSorting[0], twSorting[1])

    @err_catcher(name=__name__)
    def productDragEnterEvent(self, e: Any) -> None:
        """Handle drag enter event for product version ingestion.
        
        Validates dragged files and accepts or rejects the drag operation.
        
        Args:
            e: Drag enter event.
        """
        if e.mimeData().hasUrls() and e.mimeData().urls():
            dragPath = os.path.normpath(e.mimeData().urls()[0].toLocalFile())
            items = self.tw_versions.selectedItems()
            if items:
                row = items[0].row()
                pathC = self.tw_versions.model().columnCount() - 1
                path = self.tw_versions.item(row, pathC).text()
            else:
                path = ""

            if not dragPath or dragPath.strip("/\\") == path.strip("/\\"):
                e.ignore()
            else:
                e.accept()
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def productDragMoveEvent(self, e: Any) -> None:
        """Handle drag move event and update visual feedback.
        
        Args:
            e: Drag move event.
        """
        if e.mimeData().hasUrls():
            e.accept()
            self.tw_versions.setStyleSheet(
                "QTableView { border-style: dashed; border-color: rgb(100, 200, 100);  border-width: 2px; }"
            )
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def productDragLeaveEvent(self, e: Any) -> None:
        """Handle drag leave event and reset visual feedback.
        
        Args:
            e: Drag leave event.
        """
        self.tw_versions.setStyleSheet("")

    @err_catcher(name=__name__)
    def productDropEvent(self, e: Any) -> None:
        """Handle drop event for product version ingestion.
        
        Extracts file paths from drop data and initiates product ingestion.
        
        Args:
            e: Drop event.
        """
        if e.mimeData().hasUrls():
            self.tw_versions.setStyleSheet("")
            e.setDropAction(Qt.LinkAction)
            e.accept()

            files = [
                os.path.normpath(str(url.toLocalFile())) for url in e.mimeData().urls()
            ]
            entity = self.getCurrentEntity()
            self.ingestProductVersion(entity, files)
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def ingestProductVersion(self, entity: Dict[str, Any], files: List[str]) -> None:
        """Ingest files as a new product version.
        
        Args:
            entity: Entity context dictionary.
            files: List of file paths to ingest.
        """
        if self.core.products.getLinkedToTasks():
            product = self.getCurrentProduct() or {}
            productName = product.get("product")
            product.update(entity)
            entity = product
        else:
            productName = self.getCurrentProductName()

        if not productName:
            self.core.popup("No valid context is selected")
            return

        self.core.products.ingestProductVersion(files, entity, productName)
        self.updateVersions()

    @err_catcher(name=__name__)
    def showEvent(self, event: Any) -> None:
        """Handle show event to align header heights.
        
        Args:
            event: Show event.
        """
        if not getattr(self, "headerHeightSet", False):
            spacing = self.w_tasks.layout().spacing()
            if self.w_entities.isHidden():
                h = self.w_version.geometry().height()
            else:
                h = self.w_entities.w_header.geometry().height() - spacing

            self.setHeaderHeight(h)

    @err_catcher(name=__name__)
    def setHeaderHeight(self, height: int) -> None:
        """Set consistent height for all headers.
        
        Args:
            height: Header height in pixels.
        """
        spacing = self.w_tasks.layout().spacing()
        self.w_entities.w_header.setMinimumHeight(height + spacing)
        self.l_identifier.setMinimumHeight(height)
        self.w_version.setMinimumHeight(height)
        self.headerHeightSet = True

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect UI signals to their handler methods.
        
        Sets up event connections for entity changes, mouse clicks, context menus,
        and version loading.
        """
        self.w_entities.getPage("Assets").itemChanged.connect(lambda: self.entityChanged("asset"))
        self.w_entities.getPage("Shots").itemChanged.connect(lambda: self.entityChanged("shot"))
        self.w_entities.tabChanged.connect(self.entityTabChanged)

        self.tw_identifier.mousePrEvent = self.tw_identifier.mousePressEvent
        self.tw_identifier.mousePressEvent = lambda x: self.mouseClickEvent(x, self.tw_identifier)
        self.tw_identifier.mouseClickEvent = self.tw_identifier.mouseReleaseEvent
        self.tw_identifier.mouseReleaseEvent = lambda x: self.mouseClickEvent(x, self.tw_identifier)
        self.tw_identifier.itemSelectionChanged.connect(self.identifierClicked)
        if self.core.stateManagerEnabled() and self.core.appPlugin.pluginName != "Standalone":
            self.tw_identifier.doubleClicked.connect(
                lambda: self.loadVersion(None, currentVersion=True)
            )
            self.tw_versions.doubleClicked.connect(self.loadVersion)

        self.b_custom.clicked.connect(self.openCustom)
        self.tw_identifier.customContextMenuRequested.connect(
            lambda pos: self.rclicked(pos, "identifier")
        )
        self.tw_versions.customContextMenuRequested.connect(
            lambda pos: self.rclicked(pos, "versions")
        )
        self.tw_versions.mouseMoveEvent = self.mouseDrag

    @err_catcher(name=__name__)
    def mouseClickEvent(self, event: Any, widget: Any) -> None:
        """Handle mouse click events on widgets.
        
        Manages selection, deselection, and expand/collapse of tree items.
        
        Args:
            event: Mouse event.
            widget: Widget that received the click.
        """
        if QEvent is not None:
            if event.type() == QEvent.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    index = widget.indexAt(event.pos())
                    if index.data() is None:
                        widget.setCurrentIndex(
                            widget.model().createIndex(-1, 0)
                        )
                    widget.mouseClickEvent(event)
            elif event.type() == QEvent.MouseButtonPress:
                item = widget.itemAt(event.pos())
                wasExpanded = item.isExpanded() if item else None
                widget.mousePrEvent(event)

                if event.button() == Qt.LeftButton:
                    if item and wasExpanded == item.isExpanded():
                        item.setExpanded(not item.isExpanded())

    @err_catcher(name=__name__)
    def keyPressEvent(self, event: Any) -> None:
        """Handle keyboard events.
        
        Args:
            event: Key press event.
        """
        if self.autoClose or (event.key() != Qt.Key_Escape):
            super(ProductBrowser, self).keyPressEvent(event)

    @err_catcher(name=__name__)
    def mouseDrag(self, event: Any) -> None:
        """Handle mouse drag to initiate drag-drop operation.
        
        Creates a drag operation with selected version file paths.
        
        Args:
            event: Mouse move event.
        """
        if event.buttons() != Qt.LeftButton:
            return

        if getattr(self, "isClosing", False):
            return

        versions = [self.getCurSelection()]
        urlList = []
        for version in versions:
            if not os.path.isfile(version):
                continue

            url = QUrl.fromLocalFile(version)
            urlList.append(url)

        if len(urlList) == 0:
            return

        drag = QDrag(self)
        mData = QMimeData()

        mData.setUrls(urlList)
        mData.setData("text/plain", str(urlList[0].toLocalFile()).encode())
        drag.setMimeData(mData)

        drag.exec_(Qt.CopyAction | Qt.MoveAction)

    @err_catcher(name=__name__)
    def openCustom(self) -> None:
        """Open file dialog to select a custom file for import.
        
        Allows importing files outside the standard product structure.
        """
        startPath = os.path.dirname(self.getCurSelection())
        customFile = QFileDialog.getOpenFileName(
            self, "Select File to import", startPath, "All files (*.*)"
        )[0]
        customFile = self.core.fixPath(customFile)

        fileName = getattr(self.core.appPlugin, "fixImportPath", lambda x: x)(
            customFile
        )

        if fileName != "":
            result = self.setProductPath(path=fileName, custom=True)
            if result:
                if self.autoClose:
                    if hasattr(self, "detailWin") and self.detailWin.isVisible():
                        self.detailWin.close()

                    self.close()
                elif self.handleImport:
                    sm = self.core.getStateManager()
                    sm.importFile(self.productPath)

    @err_catcher(name=__name__)
    def loadVersion(self, index: Any, currentVersion: bool = False) -> None:
        """Load a product version for import.
        
        Validates file compatibility and sets the product path for import.
        
        Args:
            index: Table index of version to load, or None for current version.
            currentVersion: Whether to load the current/latest version.
        """
        if currentVersion:
            self.tw_versions.sortByColumn(0, Qt.DescendingOrder)
            pathC = self.tw_versions.model().columnCount() - 1
            versionPath = self.tw_versions.model().index(0, pathC).data()
            if versionPath is None:
                return

            identifierData = self.getCurrentProduct()
            versionPath = self.core.products.getLatestVersionpathFromProduct(identifierData["product"], entity=identifierData)
            if not versionPath:
                return

        else:
            pathC = index.model().columnCount() - 1
            versionPath = index.model().index(index.row(), pathC).data()

        incompatible = []
        for i in self.core.unloadedAppPlugins.values():
            incompatible += getattr(i, "appSpecificFormats", [])

        if os.path.splitext(versionPath)[1] in incompatible:
            self.core.popup(
                "This filetype is incompatible. Can't import the selected file."
            )
        else:
            result = self.setProductPath(path=versionPath)
            if result:
                if self.autoClose:
                    self.isClosing = True
                    if hasattr(self, "detailWin") and self.detailWin.isVisible():
                        self.detailWin.close()

                    self.close()
                elif self.handleImport:
                    sm = self.core.getStateManager()
                    if sm:
                        sm.importFile(self.productPath)

    @err_catcher(name=__name__)
    def setProductPath(self, path: str, custom: bool = False) -> bool:
        """Set the selected product path.
        
        Validates the path and emits the productPathSet signal.
        
        Args:
            path: File path to set as product path.
            custom: Whether this is a custom file outside product structure.
            
        Returns:
            True if path was successfully set, False otherwise.
        """
        if self.importState:
            result = getattr(self.importState, "validateFilepath", lambda x: True)(path)
            if result is not True:
                self.core.popup(result)
                return

        self.productPath = path
        self.customProduct = custom
        self.productPathSet.emit(path)
        return True

    @err_catcher(name=__name__)
    def getCurrentEntity(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected entity.
        
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
    def getCurrentProduct(self, allowMultiple: bool = False) -> Optional[Any]:
        """Get the currently selected product(s).
        
        Args:
            allowMultiple: Whether to return multiple products if selected.
            
        Returns:
            Product data dictionary, list of dictionaries if allowMultiple=True,
            or None if no selection.
        """
        items = self.tw_identifier.selectedItems()
        items = [item for item in items if not (item.data(0, Qt.UserRole) or {}).get("isGroup")]
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
        """Get the currently selected version.
        
        Returns:
            Version data dictionary, or None if no selection.
        """
        row = self.tw_versions.currentIndex().row()
        version = self.tw_versions.model().index(row, 0).data(Qt.UserRole)
        return version

    @err_catcher(name=__name__)
    def rclicked(self, pos: Any, listType: str) -> None:
        """Handle right-click context menu for products or versions.
        
        Creates and displays a context menu with actions appropriate for the
        clicked list type (identifier or versions).
        
        Args:
            pos: Click position.
            listType: Either "identifier" for products or "versions" for version list.
        """
        if listType == "identifier":
            viewUi = self.tw_identifier
            refresh = self.updateIdentifiers
            rcmenu = QMenu(viewUi)
            item = self.tw_identifier.itemAt(pos)
            isGroup = False
            if not item:
                entity = self.getCurrentEntity()
                if not entity:
                    return

                self.tw_identifier.setCurrentItem(None)
                path = self.core.products.getProductPathFromEntity(entity)
            else:
                data = item.data(0, Qt.UserRole)
                isGroup = data and data.get("isGroup")
                if data and not isGroup:
                    path = list(data["locations"].values())[0]
                else:
                    entity = self.getCurrentEntity()
                    if not entity:
                        return

                    path = self.core.products.getProductPathFromEntity(entity)

            depAct = QAction("Create Product...", viewUi)
            depAct.triggered.connect(self.createProductDlg)
            rcmenu.addAction(depAct)

            if item and not isGroup:
                depAct = QAction("Edit Tags...", viewUi)
                depAct.triggered.connect(lambda: self.editTags(data))
                rcmenu.addAction(depAct)

                depAct = QAction("Group selected...", viewUi)
                iconPath = os.path.join(
                    self.core.prismRoot, "Scripts", "UserInterfacesPrism", "folder.png"
                )
                icon = self.core.media.getColoredIcon(iconPath)
                depAct.setIcon(icon)
                depAct.triggered.connect(self.groupProductsDlg)
                rcmenu.addAction(depAct)

            if isGroup:
                depAct = QAction("Ungroup", viewUi)
                iconPath = os.path.join(
                    self.core.prismRoot, "Scripts", "UserInterfacesPrism", "folder.png"
                )
                icon = self.core.media.getColoredIcon(iconPath)
                depAct.setIcon(icon)
                depAct.triggered.connect(lambda: self.ungroupProducts(item.text(0)))
                rcmenu.addAction(depAct)

        elif listType == "versions":
            viewUi = self.tw_versions
            refresh = self.updateVersions
            rcmenu = QMenu(viewUi)
            row = self.tw_versions.rowAt(pos.y())

            act_create = QAction("Create Version...", self)
            act_create.triggered.connect(self.createVersionDlg)
            rcmenu.addAction(act_create)

            if row == -1:
                self.tw_versions.setCurrentIndex(
                    self.tw_versions.model().createIndex(-1, 0)
                )
                if self.getCurrentProduct() is None:
                    return

                locs = list(self.getCurrentProduct()["locations"].values())
                if locs:
                    path = locs[0]
                else:
                    path = ""
            else:
                if self.core.stateManagerEnabled() and self.core.appPlugin.pluginName != "Standalone":
                    index = self.tw_versions.indexAt(pos)
                    action = QAction("Import", viewUi)
                    action.triggered.connect(lambda idx=index: self.loadVersion(index))
                    rcmenu.addAction(action)

                pathC = self.tw_versions.model().columnCount() - 1
                path = self.tw_versions.model().index(row, pathC).data()

                useMaster = self.core.products.getUseMaster()
                if useMaster:
                    column = self.versionLabels.index("Version")
                    version = self.tw_versions.item(row, column).text()
                    if version.startswith("master"):
                        masterAct = QAction("Delete master", viewUi)
                        masterAct.triggered.connect(
                            lambda: self.core.products.deleteMasterVersion(path)
                        )
                        masterAct.triggered.connect(self.updateVersions)
                        rcmenu.addAction(masterAct)
                    else:
                        masterAct = QAction("Set as master", viewUi)
                        masterAct.triggered.connect(
                            lambda: self.core.products.updateMasterVersion(path)
                        )
                        masterAct.triggered.connect(self.updateVersions)
                        rcmenu.addAction(masterAct)

                if "Location" in self.versionLabels:
                    column = self.versionLabels.index("Location")
                    locItem = self.tw_versions.item(row, column)
                    if locItem:
                        location = locItem.text()
                        if "local" in location and "global" not in location:
                            glbAct = QAction("Move to global", viewUi)
                            versionDir = os.path.dirname(os.path.dirname(path))
                            glbAct.triggered.connect(lambda: self.moveToGlobal(versionDir))
                            rcmenu.addAction(glbAct)

                infAct = QAction("Edit comment...", self)
                infAct.triggered.connect(lambda: self.editComment(path))
                rcmenu.addAction(infAct)

                infoAct = QAction("Set preferred file...", viewUi)
                infoAct.triggered.connect(
                    lambda: self.setPreferredFile(row)
                )
                rcmenu.addAction(infoAct)

                if self.core.products.getUseProductPreviews():
                    prvAct = QAction(self.core.tr("Capture preview"), self)
                    prvAct.triggered.connect(lambda: self.captureProductPreview(os.path.dirname(path)))
                    rcmenu.addAction(prvAct)

                infoAct = QAction("Show version info", viewUi)
                infoAct.triggered.connect(
                    lambda: self.showVersionInfo(path)
                )
                rcmenu.addAction(infoAct)
                infoFolder = self.core.products.getVersionInfoPathFromProductFilepath(
                    path
                )
                infoPath = self.core.getVersioninfoPath(infoFolder)

                if not os.path.exists(infoPath):
                    self.core.configs.findDeprecatedConfig(infoPath)

                depAct = QAction("Show dependencies", viewUi)
                depAct.triggered.connect(
                    lambda: self.core.dependencyViewer(infoPath, modal=True)
                )
                rcmenu.addAction(depAct)

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

        act_refresh = QAction("Refresh", self)
        act_refresh.triggered.connect(lambda: refresh(restoreSelection=True))
        rcmenu.addAction(act_refresh)

        openex = QAction("Open in Explorer", viewUi)
        openex.triggered.connect(lambda: self.core.openFolder(path))
        rcmenu.addAction(openex)

        copAct = self.core.getCopyAction(path, parent=viewUi)
        rcmenu.addAction(copAct)

        copAct = QAction("Copy path for next version", self)
        copAct.triggered.connect(self.prepareNewVersion)
        rcmenu.addAction(copAct)

        if listType == "versions" and row != -1:
            version = self.tw_versions.model().index(row, 0).data(Qt.UserRole)
            curLoc = self.core.paths.getLocationFromPath(path)
            locMenu = QMenu("Copy to", self)
            locs = self.core.paths.getExportProductBasePaths()
            for loc in locs:
                if loc == curLoc:
                    continue

                copAct = QAction(loc, self)
                copAct.triggered.connect(lambda x=None, lc=loc: self.copyToLocation(version["path"], lc))
                locMenu.addAction(copAct)

            if not locMenu.isEmpty():
                rcmenu.addMenu(locMenu)

        self.core.callback(
            "productSelectorContextMenuRequested", args=[self, viewUi, pos, rcmenu]
        )
        rcmenu.exec_((viewUi.viewport()).mapToGlobal(pos))

    @err_catcher(name=__name__)
    def captureProductPreview(self, path: str) -> None:
        """Capture a screen area as product preview image.
        
        Args:
            path: Product directory path to save preview to.
        """
        from PrismUtils import ScreenShot
        self.window().setWindowOpacity(0)
        previewImg = ScreenShot.grabScreenArea(self.core)
        self.window().setWindowOpacity(1)
        if previewImg:
            previewImg = self.core.media.scalePixmap(
                previewImg,
                self.core.scenePreviewWidth,
                self.core.scenePreviewHeight,
                fitIntoBounds=False, crop=True
            )
            self.core.products.setProductPreview(path, previewImg)

    @err_catcher(name=__name__)
    def editTags(self, data: Dict[str, Any]) -> None:
        """Open dialog to edit product tags.
        
        Args:
            data: Product data dictionary.
        """
        self.dlg_editTags = EditTagsDlg(self, data)
        self.dlg_editTags.show()

    @err_catcher(name=__name__)
    def groupProductsDlg(self) -> None:
        """Open dialog to group selected products.
        
        Allows organizing products into named groups for better organization.
        """
        products = self.getCurrentProduct(allowMultiple=True)
        groups = [self.core.products.getGroupFromProduct(product) for product in products]
        if len(list(set(groups))) == 1:
            startText = groups[0]
        else:
            startText = ""

        self.newItem = PrismWidgets.CreateItem(
            core=self.core, showType=False, mode="product", startText=startText, valueRequired=False, allowChars="/"
        )
        self.newItem.setModal(True)
        self.core.parentWindow(self.newItem)
        self.newItem.e_item.setFocus()
        self.newItem.setWindowTitle("Group selected products")
        self.newItem.l_item.setText("Group Name:")
        self.newItem.buttonBox.buttons()[0].setText("Group")
        self.newItem.accepted.connect(lambda: self.groupProducts(self.newItem, products))
        self.newItem.chb_projectWide = QCheckBox("Project-Wide")
        self.newItem.chb_projectWide.setToolTip("Creates this group for all products with the same names for all assets and shots in the current project.")
        # self.newItem.w_options.layout().addWidget(self.newItem.chb_projectWide)
        self.newItem.show()

    @err_catcher(name=__name__)
    def groupProducts(self, dlg: Any, products: List[Dict[str, Any]]) -> None:
        """Apply grouping to products.
        
        Args:
            dlg: Dialog containing group name input.
            products: List of product data dictionaries to group.
        """
        group = dlg.e_item.text()
        projectWide = dlg.chb_projectWide.isChecked()
        self.core.products.setProductsGroup(products, group=group, projectWide=projectWide)
        self.updateIdentifiers(restoreSelection=True)

    @err_catcher(name=__name__)
    def ungroupProducts(self, group: str) -> None:
        """Remove products from a group.
        
        Args:
            group: Name of the group to ungroup.
        """
        products = []
        identifiers = self.getIdentifiers()
        for identifierName in identifiers:
            pgroup = self.core.products.getGroupFromProduct(identifiers[identifierName])
            if pgroup == group:
                products.append(identifiers[identifierName])

        if products:
            self.core.products.setProductsGroup(products, group=None)
            self.updateIdentifiers(restoreSelection=True)

    @err_catcher(name=__name__)
    def prepareNewVersion(self) -> None:
        """Prepare and copy path for next version to clipboard.
        
        Generates the next version path and saves version info.
        """
        curEntity = self.getCurrentEntity()
        curProduct = self.getCurrentProductName()
        if not curProduct:
            return

        extension = ""
        framePadding = ""
        comment = ""
        outputPathData = self.core.products.generateProductPath(
            entity=curEntity,
            task=curProduct,
            extension=extension,
            framePadding=framePadding,
            comment=comment,
            returnDetails=True,
        )

        nextPath = outputPathData["path"]
        details = curEntity.copy()
        details["product"] = curProduct
        details["version"] = outputPathData["version"]

        self.core.saveVersionInfo(os.path.dirname(nextPath), details=details)
        self.core.copyToClipboard(nextPath)
        self.updateVersions(restoreSelection=True)

    @err_catcher(name=__name__)
    def copyToLocation(self, path: str, location: str) -> None:
        """Copy version to a different storage location.
        
        Args:
            path: Source version path.
            location: Target location name (e.g., "local", "global").
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
    def createProductDlg(self) -> None:
        """Open dialog to create a new product.
        """
        curEntity = self.getCurrentEntity()
        self.newItem = ProjectWidgets.CreateProductDlg(self, entity=curEntity)
        self.newItem.e_product.setFocus()
        self.newItem.accepted.connect(self.createProduct)
        self.core.callback(name="onCreateProductDlgOpen", args=[self, self.newItem])
        self.newItem.show()

    @err_catcher(name=__name__)
    def createProduct(self) -> None:
        """Create a new product from dialog input.
        
        Creates product directory structure and optionally adds to group.
        """
        self.activateWindow()
        itemName = self.newItem.e_product.text()
        curEntity = self.getCurrentEntity()
        if self.core.products.getLinkedToTasks():
            curEntity["department"] = self.newItem.e_department.text() or "unknown"
            curEntity["task"] = self.newItem.e_task.text() or "unknown"

        location = self.newItem.cb_location.currentText()
        self.core.products.createProduct(entity=curEntity, product=itemName, location=location)
        selItems = self.tw_identifier.selectedItems()
        if len(selItems) == 1 and (selItems[0].data(0, Qt.UserRole) or {}).get("isGroup"):
            item = selItems[0]
            group = selItems[0].text(0)
            while item.parent():
                group = item.parent().text(0) + "/" + group
                item = item.parent()

            context = curEntity.copy()
            context["product"] = itemName
            self.core.products.setProductsGroup([context], group=group)

        self.updateIdentifiers()
        items = self.tw_identifier.findItems(itemName, Qt.MatchFlag(Qt.MatchExactly & Qt.MatchCaseSensitive ^ Qt.MatchRecursive))
        if items:
            self.tw_identifier.setCurrentItem(items[0])

    @err_catcher(name=__name__)
    def createVersionDlg(self) -> None:
        """Open dialog to create a new product version.
        """
        context = self.getCurrentProduct()
        version = self.core.products.getNextAvailableVersion(context, context["product"])
        intVersion = self.core.products.getIntVersionFromVersionName(version)
        self.newItem = ProjectWidgets.CreateProductVersionDlg(self, entity=context)
        if intVersion is not None:
            self.newItem.sp_version.setValue(intVersion)

        location = self.core.products.getLocationFromPath(context["path"])
        if location:
            self.newItem.cb_location.setCurrentText(location)

        self.newItem.sp_version.setFocus()
        self.newItem.accepted.connect(self.createVersion)
        self.core.callback(name="onCreateVersionDlgOpen", args=[self, self.newItem])
        self.newItem.show()

    @err_catcher(name=__name__)
    def createVersion(self) -> None:
        """Create a new product version from dialog input.
        
        Ingests selected files as a new version.
        """
        self.activateWindow()
        versionName = self.core.versionFormat % self.newItem.sp_version.value()
        curEntity = self.getCurrentEntity()
        product = self.getCurrentProduct()
        location = self.newItem.cb_location.currentText()
        if self.core.products.getLinkedToTasks():
            curEntity["department"] = product.get("department", "unknown")
            curEntity["task"] = product.get("task", "unknown")

        files = [f for f in self.newItem.l_filePath.text().replace("< Click or Drag & Drop files >", "").split("\n") if f]
        self.core.products.ingestProductVersion(
            files=files,
            entity=curEntity,
            product=product["product"],
            version=versionName,
            location=location,
        )
        self.updateVersions()
        if versionName is not None:
            self.navigateToVersion(versionName)

    @err_catcher(name=__name__)
    def moveToGlobal(self, localPath: str) -> None:
        """Move product version from local to global storage.
        
        Args:
            localPath: Local version directory path.
        """
        dstPath = self.core.convertPath(localPath, "global")

        if os.path.exists(dstPath):
            for root, folders, files in os.walk(dstPath):
                if files:
                    msg = "Found existing files in the global directory. Copy to global was canceled."
                    self.core.popup(msg)
                    return

            shutil.rmtree(dstPath)

        shutil.copytree(localPath, dstPath)

        try:
            shutil.rmtree(localPath)
        except:
            msg = "Could not delete the local file. Probably it is used by another process."
            self.core.popup(msg)

        self.updateVersions()

    @err_catcher(name=__name__)
    def editComment(self, filepath: str) -> None:
        """Edit the comment for a product version.
        
        Args:
            filepath: Path to version file.
        """
        if not filepath:
            msg = "Invalid filepath. Make sure the version contains valid files."
            self.core.popup(msg)
            return

        data = self.core.paths.getCachePathData(filepath)
        comment = data.get("comment", "")

        dlg_ec = PrismWidgets.CreateItem(
            core=self.core, startText=comment, showType=False, valueRequired=False, validate=False
        )

        dlg_ec.setModal(True)
        self.core.parentWindow(dlg_ec)
        dlg_ec.e_item.setFocus()
        dlg_ec.setWindowTitle("Edit Comment")
        dlg_ec.l_item.setText("New comment:")
        dlg_ec.buttonBox.buttons()[0].setText("Save")

        result = dlg_ec.exec_()

        if not result:
            return

        comment = dlg_ec.e_item.text()
        versionPath = os.path.dirname(filepath)
        self.core.products.setComment(versionPath, comment)
        self.updateVersions(restoreSelection=True)

    @err_catcher(name=__name__)
    def setPreferredFile(self, row: int) -> None:
        """Set the preferred file for a version.
        
        Args:
            row: Table row number of the version.
        """
        version = self.tw_versions.item(row, 0).data(Qt.UserRole)
        self.core.products.setPreferredFileForVersionDlg(version, callback=lambda: self.updateVersions(restoreSelection=True), parent=self)

    @err_catcher(name=__name__)
    def goToSource(self, source: Optional[str]) -> None:
        """Navigate to the source scenefile of a product version.
        
        Args:
            source: Path to source scenefile.
        """
        if not source:
            msg = "This version doesn't have a source scene."
            self.core.popup(msg)
            return

        self.core.pb.showTab("Scenefiles")
        fileNameData = self.core.getScenefileData(source)
        self.core.pb.sceneBrowser.navigate(data=fileNameData)

    @err_catcher(name=__name__)
    def showVersionInfo(self, path: str) -> None:
        """Display version information in a dialog.
        
        Args:
            path: Path to version file.
        """
        vInfo = "No information is saved with this version."

        infoFolder = self.core.products.getVersionInfoPathFromProductFilepath(
            path
        )

        infoPath = self.core.getVersioninfoPath(infoFolder)
        context = self.core.getConfig(configPath=infoPath) or {}

        if context:
            vInfo = []
            for key in context:
                label = key[0].upper() + key[1:]
                vInfo.append([label, context[key]])

        if type(vInfo) == str or len(vInfo) == 0:
            self.core.popup(vInfo, severity="info")
            return

        infoDlg = QDialog()
        lay_info = QGridLayout()

        infoDlg.setWindowTitle(
            "Versioninfo %s %s:" % (context.get("product", ""), context.get("version", ""))
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
    def getSelectedContext(self) -> Dict[str, Any]:
        """Get the current selection context.
        
        Returns:
            Dictionary containing entity, product, version, and path info.
        """
        navData = self.getCurrentEntity() or {}
        product = self.getCurrentProductName()
        navData["product"] = product
        row = self.tw_versions.currentIndex().row()
        navData["version"] = self.tw_versions.model().index(row, 0).data()
        pathC = self.tw_versions.model().columnCount() - 1
        path = self.tw_versions.model().index(row, pathC).data()
        navData["path"] = path
        return navData

    @err_catcher(name=__name__)
    def refreshUI(self) -> None:
        """Refresh the entire UI.
        
        Reloads entity tree and navigates back to current selection.
        """
        identifier = version = None
        row = self.tw_versions.currentIndex().row()
        pathC = self.tw_versions.model().columnCount() - 1
        path = self.tw_versions.model().index(row, pathC).data()

        if path:
            identifier = self.getCurrentProductName()
            version = self.tw_versions.model().index(row, 0).data()
            data = None
        else:
            product = self.getCurrentProduct()
            if product:
                data = product
            else:
                data = self.getCurrentEntity()

        self.updateSizeColumn()
        self.w_entities.getCurrentPage().tw_tree.blockSignals(True)
        self.w_entities.getCurrentPage().tw_tree.selectionModel().blockSignals(True)
        self.w_entities.refreshEntities(restoreSelection=True)
        self.w_entities.getCurrentPage().tw_tree.blockSignals(False)
        self.w_entities.getCurrentPage().tw_tree.selectionModel().blockSignals(False)
        self.entityChanged()
        if (not path and not data) or not self.navigateToFile(
            path, identifier=identifier, version=version, data=data
        ):
            self.navigateToFile(self.core.getCurrentFileName(), scenefile=True)

        self.refreshStatus = "valid"

    @err_catcher(name=__name__)
    def updateSizeColumn(self) -> None:
        """Update the Size column visibility based on user settings.
        """
        if self.core.getConfig("globals", "showFileSizes", config="user"):
            if "Size" not in self.versionLabels:
                self.versionLabels.insert(-2, "Size")
                self.versionHeaderChanged()
        elif "Size" in self.versionLabels:
            self.versionLabels = [l for l in self.versionLabels if l != "Size"]
            self.versionHeaderChanged()

    @err_catcher(name=__name__)
    def entityTabChanged(self) -> None:
        """Handle entity tab (Assets/Shots) change.
        """
        self.entityChanged()

    @err_catcher(name=__name__)
    def entityChanged(self, entityType: Optional[str] = None) -> None:
        """Handle entity selection change.
        
        Args:
            entityType: Optional entity type filter ("asset" or "shot").
        """
        if entityType and entityType != self.w_entities.getCurrentPage().entityType:
            return

        self.updateIdentifiers(restoreSelection=True)

    @err_catcher(name=__name__)
    def identifierClicked(self) -> None:
        """Handle product identifier selection change.
        
        Updates versions list and tag editor if visible.
        """
        self.updateVersions()
        if hasattr(self, "dlg_editTags") and self.dlg_editTags.isVisible():
            self.dlg_editTags.setProductData(self.getCurrentProduct())

    @err_catcher(name=__name__)
    def getIdentifiers(self) -> Dict[str, Dict[str, Any]]:
        """Get all product identifiers for the current entity.
        
        Returns:
            Dictionary mapping product names to product data.
        """
        curEntities = self.getCurrentEntities()
        if len(curEntities) != 1 or curEntities[0]["type"] not in ["asset", "shot"]:
            return {}

        location = self.w_entities.getCurrentLocation()
        identifiers = self.core.products.getProductNamesFromEntity(curEntities[0], locations=[location])
        return identifiers

    @err_catcher(name=__name__)
    def updateIdentifiers(self, item: Optional[Any] = None, restoreSelection: bool = False) -> None:
        """Update the product identifier tree.
        
        Args:
            item: Optional tree item to update.
            restoreSelection: Whether to restore previous selection.
        """
        if restoreSelection:
            curId = self.getCurrentProductName() or ""

        wasBlocked = self.tw_identifier.signalsBlocked()
        if not wasBlocked:
            self.tw_identifier.blockSignals(True)

        self.tw_identifier.clear()

        identifiers = self.getIdentifiers()
        identifierNames = sorted(identifiers.keys(), key=lambda s: s.lower())
        groups, groupItems = self.createGroupItems(identifiers)
        useTasks = self.core.products.getLinkedToTasks()
        if useTasks:
            items = {}
            for tn in identifierNames:
                item = QTreeWidgetItem([os.path.basename(tn).replace("_ShotCam", "ShotCam")])
                item.setData(0, Qt.UserRole, identifiers[tn])
                useDep = os.getenv("PRISM_USE_DEPARTMENTS_FOR_PRODUCTS", "1") == "1"
                if useDep:
                    dep = identifiers[tn].get("department") or "unknown"
                    if dep not in items:
                        ditem = QTreeWidgetItem([dep])
                        items[dep] = {"item": ditem, "tasks": {}}
                        self.tw_identifier.invisibleRootItem().addChild(ditem)

                    task = identifiers[tn].get("task") or "unknown"
                    if task not in items[dep]["tasks"]:
                        titem = QTreeWidgetItem([task])
                        items[dep]["tasks"][task] = {"item": titem}
                        items[dep]["item"].addChild(titem)

                    if tn in groups:
                        parent = groupItems[groups[tn]]
                    else:
                        parent = items[dep]["tasks"][task]["item"]
                else:
                    task = identifiers[tn].get("task") or "unknown"
                    if task not in items:
                        titem = QTreeWidgetItem([task])
                        items[task] = {"item": titem}
                        self.tw_identifier.invisibleRootItem().addChild(titem)

                    if tn in groups:
                        parent = groupItems[groups[tn]]
                    else:
                        parent = items[task]["item"]

                parent.addChild(item)

        else:
            for tn in identifierNames:
                item = QTreeWidgetItem([tn.replace("_ShotCam", "ShotCam")])
                item.setData(0, Qt.UserRole, identifiers[tn])
                if tn in groups:
                    parent = groupItems[groups[tn]]
                else:
                    parent = self.tw_identifier.invisibleRootItem()

                parent.addChild(item)

        if self.tw_identifier.topLevelItemCount() > 0:
            selectFirst = True
            if restoreSelection and curId:
                items = self.tw_identifier.findItems(curId, Qt.MatchFlag(Qt.MatchExactly & Qt.MatchCaseSensitive ^ Qt.MatchRecursive))
                if items:
                    self.tw_identifier.setCurrentItem(items[0])
                    selectFirst = False

            if selectFirst:
                self.tw_identifier.setCurrentItem(self.tw_identifier.topLevelItem(0))

        if not wasBlocked:
            self.tw_identifier.blockSignals(False)
            self.updateVersions(restoreSelection=True)

    @err_catcher(name=__name__)
    def createGroupItems(self, identifiers: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, str], Dict[str, Any]]:
        """Create tree items for product groups.
        
        Args:
            identifiers: Dictionary of product identifiers.
            
        Returns:
            Tuple of (groups dict mapping product to group name, groupItems dict mapping group path to tree item).
        """
        groups = {}
        for identifierName in identifiers:
            group = self.core.products.getGroupFromProduct(identifiers[identifierName])
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
                    parent = self.tw_identifier.invisibleRootItem()

                parent.addChild(item)
                curPath = newPath
                groupItems[curPath] = item

        return groups, groupItems

    @err_catcher(name=__name__)
    def updateVersions(self, restoreSelection: bool = False) -> None:
        """Update the versions table for the selected product.
        
        Args:
            restoreSelection: Whether to restore previous version selection.
        """
        curVersion = None
        indexes = self.tw_versions.selectionModel().selectedIndexes()
        if indexes:
            curVersion = self.tw_versions.model().index(indexes[0].row(), 0).data(Qt.UserRole)

        wasBlocked = self.tw_versions.signalsBlocked()
        if not wasBlocked:
            self.tw_versions.blockSignals(True)

        self.tw_versions.clearContents()
        self.tw_versions.setRowCount(0)

        twSorting = [
            self.tw_versions.horizontalHeader().sortIndicatorSection(),
            self.tw_versions.horizontalHeader().sortIndicatorOrder(),
        ]
        self.tw_versions.setSortingEnabled(False)
        identifierData = self.getCurrentProduct()

        if identifierData:
            location = self.w_entities.getCurrentLocation()
            versions = self.core.products.getVersionsFromContext(identifierData, locations=[location])
            for version in versions:
                if version["version"] == "master":
                    location = list(version.get("locations", [None]))[0]
                    filepath = self.core.products.getPreferredFileFromVersion(
                        version, location=location if location else None
                    )
                    if not filepath:
                        continue

                    versionNameData = self.core.products.getDataFromVersionContext(
                        version
                    ).copy()
                    versionNameData.update(version)
                    comment = versionNameData.get("comment", "")
                    user = versionNameData.get("user", "")
                    versionName = self.core.products.getMasterVersionLabel(filepath)
                    self.addVersionToTable(
                        filepath, versionName, comment, user, data=versionNameData
                    )
                else:
                    filepath = self.core.products.getPreferredFileFromVersion(version)
                    if not filepath:
                        continue

                    versionNameData = self.core.products.getDataFromVersionContext(
                        version
                    ).copy()
                    versionNameData.update(version)
                    versionName = versionNameData.get("version")
                    if not versionName:
                        versionName = version.get("version")

                    if versionNameData.get("wedge"):
                        versionName += " (%s)" % versionNameData["wedge"]

                    comment = versionNameData.get("comment")
                    user = versionNameData.get("user")

                    self.addVersionToTable(
                        filepath, versionName, comment, user, data=versionNameData
                    )

        self.tw_versions.resizeColumnsToContents()
        self.tw_versions.sortByColumn(twSorting[0], twSorting[1])
        self.tw_versions.setSortingEnabled(True)

        if self.tw_versions.model().rowCount() > 0:
            selectFirst = True
            if restoreSelection and curVersion:
                for versionNum in range(self.tw_versions.model().rowCount()):
                    if self.tw_versions.model().index(versionNum, 0).data() == curVersion["version"]:
                        self.tw_versions.selectRow(versionNum)
                        selectFirst = False
            
            if selectFirst:
                self.tw_versions.selectRow(0)

        if not wasBlocked:
            self.tw_versions.blockSignals(False)
            newVersion = None
            indexes = self.tw_versions.selectionModel().selectedIndexes()
            if indexes:
                newVersion = self.tw_versions.model().index(indexes[0].row(), 0).data(Qt.UserRole)

            if curVersion != newVersion:
                self.versionsUpdated.emit()

    @err_catcher(name=__name__)
    def addVersionToTable(self, filepath: str, versionName: str, comment: str, user: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Add a version row to the versions table.
        
        Args:
            filepath: Path to version file.
            versionName: Version string (e.g., "v0001").
            comment: Version comment.
            user: Username who created the version.
            data: Optional additional version data.
        """
        dateStamp = data.get("date", "") if data else ""
        if filepath:
            _, depExt = self.core.paths.splitext(filepath)
            dateStamp = dateStamp or self.core.getFileModificationDate(filepath, asString=False)
        else:
            depExt = ""

        if dateStamp and self.core.isStr(dateStamp):
            from datetime import datetime
            try:
                timeStamp = datetime.strptime(dateStamp, "%d.%m.%y %X")
                dateStamp = datetime.timestamp(timeStamp)
            except:
                pass

        row = self.tw_versions.rowCount()
        self.tw_versions.insertRow(row)

        versionName = versionName or ""
        if versionName.startswith("master") and sys.version[0] != "2":
            item = MasterItem(versionName)
        else:
            item = VersionItem(versionName)

        item.setTextAlignment(Qt.AlignCenter)
        item.setData(Qt.UserRole, data)
        self.tw_versions.setItem(row, self.versionLabels.index("Version"), item)

        if comment == "nocomment":
            comment = ""

        item = QTableWidgetItem(comment)
        item.setTextAlignment(Qt.AlignCenter)
        self.tw_versions.setItem(row, self.versionLabels.index("Comment"), item)

        item = QTableWidgetItem(depExt)
        item.setTextAlignment(Qt.AlignCenter)
        self.tw_versions.setItem(row, self.versionLabels.index("Type"), item)
        if (data.get("locations", {}) and len(self.w_entities.getLocations()) > 1) or (self.projectBrowser and len(self.projectBrowser.locations) > 1):
            self.locationLabels = {}
            locations = []
            if self.projectBrowser and len(self.projectBrowser.locations) > 1 and "Location" in self.versionLabels:
                locations = []
                w_location = QWidget()
                lo_location = QHBoxLayout(w_location)
                lo_location.addStretch()
                for location in self.projectBrowser.locations:
                    if not filepath:
                        continue

                    if location.get("name") == "global":
                        globalPath = self.core.convertPath(filepath, "global")
                        if not os.path.exists(globalPath):
                            continue

                    elif location.get("name") == "local" and self.core.useLocalFiles:
                        localPath = self.core.convertPath(filepath, "local")
                        if not os.path.exists(localPath):
                            continue

                    elif location.get("name") not in data.get("locations", {}):
                        continue

                    l_loc = QLabel()
                    l_loc.setToolTip("Version exists in %s" % location["name"])
                    self.locationLabels[location["name"]] = l_loc
                    if "icon" not in location:
                        location["icon"] = self.projectBrowser.getLocationIcon(location["name"])

                    if location["icon"]:
                        l_loc.setPixmap(location["icon"].pixmap(18, 18))
                        locations.append(location["name"])
                    else:
                        l_loc.setText(location["name"])
                    
                    lo_location.addWidget(l_loc)

                for location in data.get("locations", {}):
                    if location not in [loc["name"] for loc in self.projectBrowser.locations]:
                        l_loc = QLabel()
                        l_loc.setToolTip("Version exists in %s" % location)
                        self.locationLabels[location] = l_loc
                        l_loc.setText(location)
                        lo_location.addWidget(l_loc)

                lo_location.addStretch()
                self.tw_versions.setCellWidget(row, self.versionLabels.index("Location"), w_location)
                item = QTableWidgetItem()
            else:
                item = QTableWidgetItem(", ".join(data.get("locations", {})))
                item.setTextAlignment(Qt.AlignCenter)

            item.setData(Qt.UserRole, data.get("locations", {}))
            self.tw_versions.setItem(row, self.versionLabels.index("Location"), item)

        item = QTableWidgetItem(user)
        item.setTextAlignment(Qt.AlignCenter)
        self.tw_versions.setItem(row, self.versionLabels.index("User"), item)

        if self.core.getConfig("globals", "showFileSizes", config="user") and "Size" in self.versionLabels:
            if "size" in data:
                size = data["size"]
            elif filepath and os.path.exists(filepath):
                size = float(os.stat(filepath).st_size / 1024.0 / 1024.0)
            else:
                size = 0

            sizeStr = "%.2f mb" % size

            item = QTableWidgetItem(sizeStr)
            item.setTextAlignment(Qt.AlignCenter)
            self.tw_versions.setItem(row, self.versionLabels.index("Size"), item)

        item = QTableWidgetItem()
        item.setTextAlignment(Qt.AlignCenter)
        
        item.setData(Qt.DisplayRole, dateStamp)
        self.tw_versions.setItem(row, self.versionLabels.index("Date"), item)

        impPath = getattr(self.core.appPlugin, "fixImportPath", lambda x: x)(filepath)
        item = QTableWidgetItem(impPath)
        self.tw_versions.setItem(row, self.versionLabels.index("Path"), item)

        self.core.callback(name="productVersionAdded", args=[self, row, filepath, versionName, comment, user, data.get("locations", {})])

    @err_catcher(name=__name__)
    def tableMoveEvent(self, event: Any) -> None:
        """Handle mouse move over versions table.
        
        Shows detail window if previews are enabled.
        
        Args:
            event: Mouse move event.
        """
        self.showDetailWin(event)
        if hasattr(self, "detailWin") and self.detailWin.isVisible():
            self.detailWin.move(QCursor.pos().x() + 20, QCursor.pos().y())

    @err_catcher(name=__name__)
    def showDetailWin(self, event: Any) -> None:
        """Show hover detail window for a version.
        
        Displays preview image and version info in a floating window.
        
        Args:
            event: Mouse event with position.
        """
        index = self.tw_versions.indexAt(event.pos())
        if index.data() is None:
            if hasattr(self, "detailWin") and self.detailWin.isVisible():
                self.detailWin.close()
            return

        scenePath = self.tw_versions.model().index(index.row(), 0).data(Qt.UserRole)
        if scenePath is None:
            if hasattr(self, "detailWin") and self.detailWin.isVisible():
                self.detailWin.close()
            return

        scenePath = scenePath.get("path") or ""

        infoPath = (
            scenePath
            + "versioninfo"
            + self.core.configs.getProjectExtension()
        )
        prvPath = scenePath + "/preview.jpg"
        if not os.path.exists(prvPath):
            if hasattr(self, "detailWin") and self.detailWin.isVisible():
                self.detailWin.close()
            return

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
            self.core.parentWindow(self.detailWin, parent=self)
            winwidth = 320
            winheight = 10
            VBox = QVBoxLayout()
            imgmap = self.core.media.getPixmapFromPath(prvPath)
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
            sPathL = QLabel("Version:\t")
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

            if self.projectBrowser and self.projectBrowser.act_filesizes.isChecked():
                if os.path.exists(scenePath):
                    size = float(self.core.getFolderSize(scenePath)["size"] / 1024.0 / 1024.0)
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
        """Handle mouse leaving versions table.
        
        Closes detail window if visible.
        
        Args:
            event: Leave event.
        """
        if hasattr(self, "detailWin") and self.detailWin.isVisible():
            self.detailWin.close()

    @err_catcher(name=__name__)
    def tableFocusOutEvent(self, event: Any) -> None:
        """Handle focus loss on versions table.
        
        Closes detail window if visible.
        
        Args:
            event: Focus out event.
        """
        if hasattr(self, "detailWin") and self.detailWin.isVisible():
            self.detailWin.close()

    @err_catcher(name=__name__)
    def getCurSelection(self) -> str:
        """Get the currently selected file path.
        
        Returns:
            Full path to selected version file, or entity/product directory.
        """
        curPath = self.core.projectPath

        entity = self.getCurrentEntity()
        if not entity:
            return curPath

        curPath = self.core.products.getProductPathFromEntity(entity)

        if self.getCurrentProduct() is None:
            return curPath

        curPath = os.path.join(
            curPath, self.getCurrentProductName().replace("ShotCam", "_ShotCam")
        )

        indexes = self.tw_versions.selectionModel().selectedIndexes()
        if not indexes:
            return curPath

        pathC = self.tw_versions.model().columnCount() - 1
        row = self.tw_versions.selectionModel().selectedIndexes()[0].row()
        return self.tw_versions.model().index(row, pathC).data()

    @err_catcher(name=__name__)
    def getCurrentProductName(self) -> Optional[str]:
        """Get the currently selected product name.
        
        Returns:
            Product name string, or None if no selection.
        """
        product = self.getCurrentProduct()
        if not product:
            return

        productName = product["product"]
        return productName

    @err_catcher(name=__name__)
    def navigate(self, data: Dict[str, Any]) -> None:
        """Navigate to specific entity/product/version.
        
        Args:
            data: Navigation data dictionary.
        """
        self.navigateToFile(data=data, identifier=data.get("product"), version=data.get("version"))

    @err_catcher(name=__name__)
    def getDataFromPath(self, path: str, scenefile: bool = False) -> Optional[Dict[str, Any]]:
        """Extract entity/product/version data from a file path.
        
        Args:
            path: File or directory path.
            scenefile: Whether the path is a scenefile or product.
            
        Returns:
            Data dictionary, or False if path doesn't exist.
        """
        if os.path.exists(path):
            fileName = path
        else:
            fileName = os.path.dirname(path)
            if not os.path.exists(fileName):
                return False

        fileName = os.path.normpath(fileName)
        if scenefile:
            data = self.core.getScenefileData(fileName)
        else:
            data = self.core.paths.getCachePathData(fileName)

        return data

    @err_catcher(name=__name__)
    def navigateToFile(self, fileName: Optional[str] = None, identifier: Optional[str] = None, version: Optional[str] = None, scenefile: bool = False, data: Optional[Dict[str, Any]] = None) -> bool:
        """Navigate to a specific file by path or identifier/version.
        
        Args:
            fileName: Optional file path.
            identifier: Optional product identifier.
            version: Optional version string.
            scenefile: Whether the file is a scenefile.
            data: Optional navigation data dictionary.
            
        Returns:
            True if navigation was successful, False otherwise.
        """
        if not data:
            if not fileName and not (identifier and (version or scenefile)):
                return False

            if fileName:
                data = self.getDataFromPath(fileName) or {}

        if not identifier:
            identifier = data.get("product") or ""

        if not version and not scenefile:
            version = data.get("version") or ""

        versionName = version
        if not versionName and self.importState:
            versionName = self.importState.l_curVersion.text()

        if versionName and versionName != "-" and not versionName.startswith("master"):
            versionName = versionName[:5]

        return self.navigateToVersion(versionName, entity=data, product=identifier)

    @err_catcher(name=__name__)
    def navigateToEntity(self, entity: Dict[str, Any]) -> None:
        """Navigate to a specific entity.
        
        Args:
            entity: Entity data dictionary.
        """
        self.w_entities.navigate(entity)

    @err_catcher(name=__name__)
    def navigateToProduct(self, product: str, entity: Optional[Dict[str, Any]] = None) -> bool:
        """Navigate to a specific product.
        
        Args:
            product: Product name.
            entity: Optional entity to navigate to first.
            
        Returns:
            True if product was found and selected.
        """
        prevProduct = self.getCurrentProduct()
        self.tw_identifier.blockSignals(True)
        if entity:
            self.navigateToEntity(entity)

        if product == "_ShotCam":
            product = "ShotCam"

        matchingItems = self.tw_identifier.findItems(product, Qt.MatchFlag(Qt.MatchExactly & Qt.MatchCaseSensitive ^ Qt.MatchRecursive))
        result = False
        if matchingItems:
            self.tw_identifier.setCurrentItem(matchingItems[0])
            result = True

        self.tw_identifier.blockSignals(False)
        if prevProduct != self.getCurrentProduct():
            self.identifierClicked()

        return result

    @err_catcher(name=__name__)
    def navigateToVersion(self, version: Optional[str], entity: Optional[Dict[str, Any]] = None, product: Optional[str] = None) -> bool:
        """Navigate to a specific version.
        
        Args:
            version: Version string (e.g., "v0001", "master").
            entity: Optional entity to navigate to first.
            product: Optional product to navigate to first.
            
        Returns:
            True if version was found and selected.
        """
        prevVersion = self.getCurrentVersion()
        self.tw_versions.blockSignals(True)

        if entity:
            self.navigateToEntity(entity)

        if product:
            result = self.navigateToProduct(product)
            if not result:
                self.tw_versions.blockSignals(False)
                if prevVersion != self.getCurrentVersion():
                    self.versionsUpdated.emit()

                return False

        result = False
        if version is not None:
            for versionNum in range(self.tw_versions.model().rowCount()):
                curVerName = self.tw_versions.model().index(versionNum, 0).data()
                if curVerName == version or (version == "master" and curVerName.startswith("master")):
                    self.tw_versions.selectRow(versionNum)
                    result = True

        self.tw_versions.blockSignals(False)
        if prevVersion != self.getCurrentVersion():
            self.versionsUpdated.emit()

        return result


class MasterItem(QTableWidgetItem):
    """Table item that sorts master versions to the top.
    """
    def __lt__(self, other: Any) -> bool:
        """Compare items for sorting.
        
        Args:
            other: Other table item to compare against.
            
        Returns:
            False if other is not master (to stay at top), otherwise normal comparison.
        """
        return False if not other.text().startswith("master") else self.text() < other.text()


class VersionItem(QTableWidgetItem):
    """Table item that sorts regular versions below master.
    """
    def __lt__(self, other: Any) -> bool:
        """Compare items for sorting.
        
        Args:
            other: Other table item to compare against.
            
        Returns:
            True if other is master (to stay below), otherwise normal comparison.
        """
        return True if other.text().startswith("master") else self.text() < other.text()


class DateDelegate(QStyledItemDelegate):
    """Delegate for formatting date columns.
    """
    def displayText(self, value: Any, locale: Any) -> str:
        """Format date value for display.
        
        Args:
            value: Date value (timestamp or string).
            locale: Locale for formatting.
            
        Returns:
            Formatted date string.
        """
        if self.core.isStr(value):
            return value

        return self.core.getFormattedDate(value)


class EditTagsDlg(QDialog):
    """Dialog for editing product tags.
    
    Allows adding/removing tags for products with quick access to recommended tags.
    
    Attributes:
        origin: Parent ProductBrowser widget.
        core: Prism core instance.
        productData: Product data dictionary.
    """
    def __init__(self, origin: Any, data: Dict[str, Any]) -> None:
        """Initialize the edit tags dialog.
        
        Args:
            origin: Parent ProductBrowser widget.
            data: Product data dictionary.
        """
        super(EditTagsDlg, self).__init__()
        self.origin = origin
        self.core = self.origin.core
        self.setupUi()
        self.setProductData(data)

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Set up the dialog UI.
        """
        title = "Edit Tags"
        self.setWindowTitle(title)
        self.core.parentWindow(self, parent=self.origin)

        self.w_tags = QWidget()
        self.lo_tags = QHBoxLayout()
        self.w_tags.setLayout(self.lo_tags)

        self.l_tags = QLabel("Tags:")
        self.e_tags = QLineEdit()

        self.b_editTags = QToolButton()
        self.b_editTags.setArrowType(Qt.DownArrow)
        self.b_editTags.setToolTip("Recommended Tags")
        self.b_editTags.setMaximumSize(QSize(30, 16777215))
        self.b_editTags.clicked.connect(self.showRecommendedTags)

        self.lo_tags.addWidget(self.l_tags)
        self.lo_tags.addWidget(self.e_tags)
        self.lo_tags.addWidget(self.b_editTags)

        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Save", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Apply", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Close", QDialogButtonBox.RejectRole)

        self.bb_main.clicked.connect(self.onButtonClicked)
        self.lo_main.addWidget(self.w_tags)
        self.lo_main.addWidget(self.bb_main)

    @err_catcher(name=__name__)
    def sizeHint(self) -> Any:
        """Get the preferred dialog size.
        
        Returns:
            QSize with preferred dimensions.
        """
        return QSize(400, 100)

    @err_catcher(name=__name__)
    def setProductData(self, data: Dict[str, Any]) -> None:
        """Set the product to edit tags for.
        
        Args:
            data: Product data dictionary.
        """
        self.productData = data
        self.setWindowTitle("Edit Tags - %s- %s" % (self.core.entities.getEntityName(self.productData), self.productData.get("product")))
        self.refreshTags()

    @err_catcher(name=__name__)
    def refreshTags(self) -> None:
        """Refresh the tag list from product data.
        """
        tags = self.core.products.getTagsFromProduct(self.productData)
        self.e_tags.setText(", ".join(tags))

    @err_catcher(name=__name__)
    def showRecommendedTags(self) -> None:
        """Show menu with recommended tags.
        """
        tmenu = QMenu(self)

        tags = self.core.products.getRecommendedTags(self.productData)
        for tag in tags:
            tAct = QAction(tag, self)
            tAct.triggered.connect(lambda x=None, t=tag: self.toggleTag(t))
            tmenu.addAction(tAct)

        tmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def toggleTag(self, tag: str) -> None:
        """Toggle a tag on/off in the tag list.
        
        Args:
            tag: Tag name to toggle.
        """
        tags = [t.strip() for t in self.e_tags.text().split(",")]
        if tag in tags:
            tags = [t for t in tags if t != tag]
        else:
            tags.append(tag)

        tags = [t for t in tags if t]
        self.e_tags.setText(", ".join(tags))

    @err_catcher(name=__name__)
    def onButtonClicked(self, button: Any) -> None:
        """Handle button clicks.
        
        Args:
            button: Clicked button widget.
        """
        if button.text() == "Save":
            self.saveTags()
            self.accept()
        elif button.text() == "Apply":
            self.saveTags()
        elif button.text() == "Close":
            self.close()

    @err_catcher(name=__name__)
    def saveTags(self) -> None:
        """Save tags to product configuration.
        """
        tags = [t.strip() for t in self.e_tags.text().split(",")]
        self.core.products.setProductTags(self.productData, tags)
