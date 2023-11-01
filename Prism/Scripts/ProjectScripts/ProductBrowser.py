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

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils import PrismWidgets
from PrismUtils.Decorators import err_catcher
from UserInterfaces import ProductBrowser_ui


logger = logging.getLogger(__name__)


class ProductBrowser(QDialog, ProductBrowser_ui.Ui_dlg_ProductBrowser):
    productPathSet = Signal(object)
    versionsUpdated = Signal()
    closing = Signal()

    def __init__(self, core, importState=None, refresh=True, projectBrowser=None):
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
    def entered(self, prevTab=None, navData=None):
        if not self.initialized:
            self.w_entities.getPage("Assets").blockSignals(True)
            self.w_entities.getPage("Shots").blockSignals(True)
            self.w_entities.blockSignals(True)
            self.w_entities.refreshEntities(defaultSelection=False)
            self.w_entities.getPage("Assets").blockSignals(False)
            self.w_entities.getPage("Shots").blockSignals(False)
            self.w_entities.blockSignals(False)
            if navData:
                self.navigate(navData)
            else:
                navPath = self.core.getCurrentFileName()
                if self.importState:
                    result = self.navigateToFile(self.importState.getImportPath())
                    if result:
                        navPath = None

                self.navigateToFile(navPath, scenefile=True)

            self.initialized = True

        if prevTab:
            if hasattr(prevTab, "w_entities"):
                self.w_entities.syncFromWidget(prevTab.w_entities)
            elif hasattr(prevTab, "getSelectedData"):
                self.w_entities.navigate(prevTab.getSelectedData())

    @err_catcher(name=__name__)
    def closeEvent(self, event=None):
        self.closing.emit()

    @err_catcher(name=__name__)
    def loadLayout(self):
        import EntityWidget

        self.w_entities = EntityWidget.EntityWidget(core=self.core, refresh=False, mode="products")
        self.splitter.insertWidget(0, self.w_entities)

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

        if len(self.w_entities.getLocations()) > 1 or (self.projectBrowser and len(self.projectBrowser.locations) > 1):
            self.versionLabels.insert(3, "Location")

        self.tw_versions.setAcceptDrops(True)
        self.tw_versions.dragEnterEvent = self.productDragEnterEvent
        self.tw_versions.dragMoveEvent = self.productDragMoveEvent
        self.tw_versions.dragLeaveEvent = self.productDragLeaveEvent
        self.tw_versions.dropEvent = self.productDropEvent

        self.tw_versions.setDragEnabled(True)
        self.setStyleSheet("QSplitter::handle{background-color: transparent}")
        self.updateSizeColumn()
        self.tw_versions.sortByColumn(0, Qt.DescendingOrder)

    @err_catcher(name=__name__)
    def versionHeaderChanged(self):
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
    def productDragEnterEvent(self, e):
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
    def productDragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
            self.tw_versions.setStyleSheet(
                "QTableView { border-style: dashed; border-color: rgb(100, 200, 100);  border-width: 2px; }"
            )
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def productDragLeaveEvent(self, e):
        self.tw_versions.setStyleSheet("")

    @err_catcher(name=__name__)
    def productDropEvent(self, e):
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
    def ingestProductVersion(self, entity, files):
        product = self.getCurrentProductName()
        if not product:
            self.core.popup("No valid context is selected")
            return

        self.core.products.ingestProductVersion(files, entity, product)
        self.updateVersions()

    @err_catcher(name=__name__)
    def showEvent(self, event):
        if not getattr(self, "headerHeightSet", False):
            spacing = self.w_tasks.layout().spacing()
            h = self.w_entities.w_header.geometry().height() - spacing
            self.setHeaderHeight(h)

    @err_catcher(name=__name__)
    def setHeaderHeight(self, height):
        spacing = self.w_tasks.layout().spacing()
        self.w_entities.w_header.setMinimumHeight(height + spacing)
        self.l_identifier.setMinimumHeight(height)
        self.w_version.setMinimumHeight(height)
        self.headerHeightSet = True

    @err_catcher(name=__name__)
    def connectEvents(self):
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
    def mouseClickEvent(self, event, widget):
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
    def keyPressEvent(self, event):
        if self.autoClose or (event.key() != Qt.Key_Escape):
            super(ProductBrowser, self).keyPressEvent(event)

    @err_catcher(name=__name__)
    def mouseDrag(self, event):
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
    def openCustom(self):
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
                    self.close()
                elif self.handleImport:
                    sm = self.core.getStateManager()
                    sm.importFile(self.productPath)

    @err_catcher(name=__name__)
    def loadVersion(self, index, currentVersion=False):
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
                    self.close()
                elif self.handleImport:
                    sm = self.core.getStateManager()
                    if sm:
                        sm.importFile(self.productPath)

    @err_catcher(name=__name__)
    def setProductPath(self, path, custom=False):
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
    def getCurrentEntity(self):
        return self.w_entities.getCurrentPage().getCurrentData()

    @err_catcher(name=__name__)
    def getCurrentEntities(self):
        return self.w_entities.getCurrentPage().getCurrentData(returnOne=False)

    @err_catcher(name=__name__)
    def getCurrentProduct(self, allowMultiple=False):
        items = self.tw_identifier.selectedItems()
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
    def getCurrentVersion(self):
        row = self.tw_versions.currentIndex().row()
        version = self.tw_versions.model().index(row, 0).data(Qt.UserRole)
        return version

    @err_catcher(name=__name__)
    def rclicked(self, pos, listType):
        if listType == "identifier":
            viewUi = self.tw_identifier
            refresh = self.updateIdentifiers
            rcmenu = QMenu(viewUi)
            item = self.tw_identifier.itemAt(pos)

            if not item:
                entity = self.getCurrentEntity()
                if not entity:
                    return

                self.tw_identifier.setCurrentItem(None)
                path = self.core.products.getProductPathFromEntity(entity)
            else:
                data = item.data(0, Qt.UserRole)
                if data:
                    path = data["locations"][0]
                else:
                    entity = self.getCurrentEntity()
                    if not entity:
                        return

                    path = self.core.products.getProductPathFromEntity(entity)
                    item = None

            depAct = QAction("Create Product...", viewUi)
            depAct.triggered.connect(self.createProductDlg)
            rcmenu.addAction(depAct)

            if item:
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

        elif listType == "versions":
            viewUi = self.tw_versions
            refresh = self.updateVersions
            rcmenu = QMenu(viewUi)
            row = self.tw_versions.rowAt(pos.y())

            if row == -1:
                self.tw_versions.setCurrentIndex(
                    self.tw_versions.model().createIndex(-1, 0)
                )
                if self.getCurrentProduct() is None:
                    return

                locs = self.getCurrentProduct()["locations"]
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
                    location = self.tw_versions.item(row, column).text()
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

        copAct = QAction("Copy", viewUi)
        copAct.triggered.connect(lambda: self.core.copyToClipboard(path, file=True))
        rcmenu.addAction(copAct)

        copAct = QAction("Copy path for next version", self)
        copAct.triggered.connect(self.prepareNewVersion)
        rcmenu.addAction(copAct)

        if listType == "versions" and row != -1:
            version = self.tw_versions.model().index(row, 0).data(Qt.UserRole)
            curLoc = self.core.paths.getLocationFromPath(path)
            locMenu = QMenu("Copy to", self)
            rcmenu.addMenu(locMenu)
            locs = self.core.paths.getExportProductBasePaths()
            for loc in locs:
                if loc == curLoc:
                    continue

                copAct = QAction(loc, self)
                copAct.triggered.connect(lambda x=None, l=loc: self.copyToLocation(version["path"], l))
                locMenu.addAction(copAct)

        self.core.callback(
            "productSelectorContextMenuRequested", args=[self, viewUi, pos, rcmenu]
        )
        rcmenu.exec_((viewUi.viewport()).mapToGlobal(pos))

    @err_catcher(name=__name__)
    def editTags(self, data):
        self.dlg_editTags = EditTagsDlg(self, data)
        self.dlg_editTags.show()

    @err_catcher(name=__name__)
    def groupProductsDlg(self):
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
    def groupProducts(self, dlg, products):
        group = dlg.e_item.text()
        projectWide = dlg.chb_projectWide.isChecked()
        self.core.products.setProductsGroup(products, group=group, projectWide=projectWide)
        self.updateIdentifiers(restoreSelection=True)

    @err_catcher(name=__name__)
    def prepareNewVersion(self):
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
    def createProductDlg(self):
        self.newItem = PrismWidgets.CreateItem(
            core=self.core, showType=False, mode="product"
        )
        self.newItem.setModal(True)
        self.core.parentWindow(self.newItem)
        self.newItem.e_item.setFocus()
        self.newItem.setWindowTitle("Create Product")
        self.newItem.l_item.setText("Productname:")
        self.newItem.accepted.connect(self.createProduct)

        self.core.callback(name="onCreateProductDlgOpen", args=[self, self.newItem])

        self.newItem.show()

    @err_catcher(name=__name__)
    def createProduct(self):
        self.activateWindow()
        itemName = self.newItem.e_item.text()

        curEntity = self.getCurrentEntity()

        self.core.products.createProduct(entity=curEntity, product=itemName)
        selItems = self.tw_identifier.selectedItems()
        if len(selItems) == 1 and not selItems[0].data(0, Qt.UserRole):
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
    def moveToGlobal(self, localPath):
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
    def editComment(self, filepath):
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
    def setPreferredFile(self, row):
        version = self.tw_versions.item(row, 0).data(Qt.UserRole)
        self.core.products.setPreferredFileForVersionDlg(version, callback=lambda: self.updateVersions(restoreSelection=True))

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
    def showVersionInfo(self, path):
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
    def getSelectedContext(self):
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
    def refreshUI(self):
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
        self.w_entities.refreshEntities(restoreSelection=True)
        self.w_entities.getCurrentPage().tw_tree.blockSignals(False)
        self.entityChanged()
        if (not path and not data) or not self.navigateToFile(
            path, identifier=identifier, version=version, data=data
        ):
            self.navigateToFile(self.core.getCurrentFileName(), scenefile=True)

        self.refreshStatus = "valid"

    @err_catcher(name=__name__)
    def updateSizeColumn(self):
        if self.core.getConfig("globals", "showFileSizes", config="user"):
            if "Size" not in self.versionLabels:
                self.versionLabels.insert(-2, "Size")
                self.versionHeaderChanged()
        elif "Size" in self.versionLabels:
            self.versionLabels = [l for l in self.versionLabels if l != "Size"]
            self.versionHeaderChanged()

    @err_catcher(name=__name__)
    def entityTabChanged(self):
        self.entityChanged()

    @err_catcher(name=__name__)
    def entityChanged(self, entityType=None):
        if entityType and entityType != self.w_entities.getCurrentPage().entityType:
            return

        self.updateIdentifiers(restoreSelection=True)

    @err_catcher(name=__name__)
    def identifierClicked(self):
        self.updateVersions()
        if hasattr(self, "dlg_editTags") and self.dlg_editTags.isVisible():
            self.dlg_editTags.setProductData(self.getCurrentProduct())

    @err_catcher(name=__name__)
    def getIdentifiers(self):
        curEntities = self.getCurrentEntities()
        if len(curEntities) != 1 or curEntities[0]["type"] not in ["asset", "shot"]:
            return {}

        location = self.w_entities.getCurrentLocation()
        identifiers = self.core.products.getProductNamesFromEntity(curEntities[0], locations=[location])
        return identifiers

    @err_catcher(name=__name__)
    def updateIdentifiers(self, item=None, restoreSelection=False):
        if restoreSelection:
            curId = self.getCurrentProductName() or ""

        wasBlocked = self.tw_identifier.signalsBlocked()
        if not wasBlocked:
            self.tw_identifier.blockSignals(True)

        self.tw_identifier.clear()

        identifiers = self.getIdentifiers()
        identifierNames = sorted(identifiers.keys(), key=lambda s: s.lower())
        groups, groupItems = self.createGroupItems(identifiers)
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
    def createGroupItems(self, identifiers):
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
    def updateVersions(self, restoreSelection=False):
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
                    if len(self.w_entities.getLocations()) > 1 or (self.projectBrowser and len(self.projectBrowser.locations) > 1):
                        location = [self.core.products.getLocationFromFilepath(path) for path in version["paths"]]
                    else:
                        location = None

                    if location:
                        filepath = self.core.products.getPreferredFileFromVersion(
                            version, location=location[0]
                        )
                    else:
                        filepath = self.core.products.getPreferredFileFromVersion(
                            version
                        )

                    if not filepath:
                        continue
                    
                    cfgData = self.core.paths.getCachePathData(filepath, addPathData=False)
                    cfgData.update(version)
                    comment = cfgData.get("comment", "")
                    user = cfgData.get("user", "")
                    versionName = self.core.products.getMasterVersionLabel(filepath)
                    self.addVersionToTable(
                        filepath, versionName, comment, user, location=location, data=cfgData
                    )
                else:
                    filepath = self.core.products.getPreferredFileFromVersion(version)
                    versionNameData = self.core.products.getDataFromVersionContext(
                        version
                    )
                    versionName = versionNameData.get("version")
                    if not versionName:
                        versionName = version.get("version")

                    if versionNameData.get("wedge"):
                        versionName += " (%s)" % versionNameData["wedge"]

                    comment = versionNameData.get("comment")
                    user = versionNameData.get("user")
                    if len(self.w_entities.getLocations()) > 1 or (self.projectBrowser and len(self.projectBrowser.locations) > 1):
                        location = [self.core.products.getLocationFromFilepath(path) for path in version["paths"]]
                    else:
                        location = None

                    self.addVersionToTable(
                        filepath, versionName, comment, user, location=location, data=versionNameData
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
    def addVersionToTable(self, filepath, versionName, comment, user, location=None, data=None):
        dateStamp = data.get("date", "") if data else ""
        if filepath:
            _, depExt = self.core.paths.splitext(filepath)
            dateStamp = dateStamp or self.core.getFileModificationDate(filepath, asString=False)
        else:
            depExt = ""

        row = self.tw_versions.rowCount()
        self.tw_versions.insertRow(row)

        versionName = versionName or ""
        if versionName.startswith("master") and sys.version[0] != "2":
            item = MasterItem(versionName)
        else:
            item = VersionItem(versionName)

        item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
        item.setData(Qt.UserRole, data)
        self.tw_versions.setItem(row, self.versionLabels.index("Version"), item)

        if comment == "nocomment":
            comment = ""

        item = QTableWidgetItem(comment)
        item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
        self.tw_versions.setItem(row, self.versionLabels.index("Comment"), item)

        item = QTableWidgetItem(depExt)
        item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
        self.tw_versions.setItem(row, self.versionLabels.index("Type"), item)

        if (location and len(self.w_entities.getLocations()) > 1) or (self.projectBrowser and len(self.projectBrowser.locations) > 1):
            self.locationLabels = {}
            locations = []
            if location:
                if self.core.isStr(location):
                    locations.append(location)
                else:
                    locations += location

            if self.projectBrowser and len(self.projectBrowser.locations) > 1:
                locations = []
                w_location = QWidget()
                lo_location = QHBoxLayout(w_location)
                lo_location.addStretch()
                for location in self.projectBrowser.locations:
                    if location.get("name") == "global":
                        globalPath = self.core.convertPath(filepath, "global")
                        if not os.path.exists(globalPath):
                            continue

                    elif location.get("name") == "local" and self.core.useLocalFiles:
                        localPath = self.core.convertPath(filepath, "local")
                        if not os.path.exists(localPath):
                            continue

                    elif location.get("name") not in data.get("locations", []):
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

                lo_location.addStretch()
                self.tw_versions.setCellWidget(row, self.versionLabels.index("Location"), w_location)
                item = QTableWidgetItem()
            else:
                item = QTableWidgetItem(", ".join(locations))
                item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))

            item.setData(Qt.UserRole, locations)
            self.tw_versions.setItem(row, self.versionLabels.index("Location"), item)

        item = QTableWidgetItem(user)
        item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
        self.tw_versions.setItem(row, self.versionLabels.index("User"), item)

        if self.core.getConfig("globals", "showFileSizes", config="user"):
            if "size" in data:
                size = data["size"]
            elif filepath and os.path.exists(filepath):
                size = float(os.stat(filepath).st_size / 1024.0 / 1024.0)
            else:
                size = 0

            sizeStr = "%.2f mb" % size

            item = QTableWidgetItem(sizeStr)
            item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
            self.tw_versions.setItem(row, self.versionLabels.index("Size"), item)

        item = QTableWidgetItem()
        item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
        
        item.setData(Qt.DisplayRole, dateStamp)
        self.tw_versions.setItem(row, self.versionLabels.index("Date"), item)

        impPath = getattr(self.core.appPlugin, "fixImportPath", lambda x: x)(filepath)
        item = QTableWidgetItem(impPath)
        self.tw_versions.setItem(row, self.versionLabels.index("Path"), item)

        self.core.callback(name="productVersionAdded", args=[self, row, filepath, versionName, comment, user, location])

    @err_catcher(name=__name__)
    def getCurSelection(self):
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
    def getCurrentProductName(self):
        product = self.getCurrentProduct()
        if not product:
            return

        productName = product["product"]
        return productName

    @err_catcher(name=__name__)
    def navigate(self, data):
        self.navigateToFile(data=data, identifier=data.get("product"), version=data.get("version"))

    @err_catcher(name=__name__)
    def navigateToFile(self, fileName=None, identifier=None, version=None, scenefile=False, data=None):
        if not data:
            if not fileName:
                return False

            if not os.path.exists(fileName):
                fileName = os.path.dirname(fileName)
                if not os.path.exists(fileName):
                    return False

            fileName = os.path.normpath(fileName)
            if scenefile:
                data = self.core.getScenefileData(fileName)
            else:
                data = self.core.paths.getCachePathData(fileName)

        if not identifier:
            identifier = data.get("product") or ""

        if not version:
            version = data.get("version") or ""

        versionName = version
        if not versionName and self.importState:
            versionName = self.importState.l_curVersion.text()

        if versionName and versionName != "-" and not versionName.startswith("master"):
            versionName = versionName[:5]

        return self.navigateToVersion(versionName, entity=data, product=identifier)

    @err_catcher(name=__name__)
    def navigateToEntity(self, entity):
        self.w_entities.navigate(entity)

    @err_catcher(name=__name__)
    def navigateToProduct(self, product, entity=None):
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
    def navigateToVersion(self, version, entity=None, product=None):
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
    def __lt__(self, other):
        return False if not other.text().startswith("master") else self.text() < other.text()


class VersionItem(QTableWidgetItem):
    def __lt__(self, other):
        return True if other.text().startswith("master") else self.text() < other.text()


class DateDelegate(QStyledItemDelegate):
    def displayText(self, value, locale):
        if self.core.isStr(value):
            return value

        return self.core.getFormattedDate(value)


class EditTagsDlg(QDialog):
    def __init__(self, origin, data):
        super(EditTagsDlg, self).__init__()
        self.origin = origin
        self.core = self.origin.core
        self.setupUi()
        self.setProductData(data)

    @err_catcher(name=__name__)
    def setupUi(self):
        title = "Edit Tags"
        self.setWindowTitle(title)
        self.core.parentWindow(self, parent=self.origin)

        self.w_tags = QWidget()
        self.lo_tags = QHBoxLayout()
        self.w_tags.setLayout(self.lo_tags)

        self.l_tags = QLabel("Tags:")
        self.e_tags = QLineEdit()

        self.lo_tags.addWidget(self.l_tags)
        self.lo_tags.addWidget(self.e_tags)

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
    def sizeHint(self):
        return QSize(400, 100)

    @err_catcher(name=__name__)
    def setProductData(self, data):
        self.productData = data
        self.setWindowTitle("Edit Tags - %s- %s" % (self.core.entities.getEntityName(self.productData), self.productData.get("product")))
        self.refreshTags()

    @err_catcher(name=__name__)
    def refreshTags(self):
        tags = self.core.products.getTagsFromProduct(self.productData)
        self.e_tags.setText(", ".join(tags))

    @err_catcher(name=__name__)
    def onButtonClicked(self, button):
        if button.text() == "Save":
            self.saveTags()
            self.accept()
        elif button.text() == "Apply":
            self.saveTags()
        elif button.text() == "Close":
            self.close()

    @err_catcher(name=__name__)
    def saveTags(self):
        tags = [t.strip() for t in self.e_tags.text().split(",")]
        self.core.products.setProductTags(self.productData, tags)
