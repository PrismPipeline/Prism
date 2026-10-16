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
import datetime
import glob
from typing import Any, Optional, List, Dict, Tuple

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

if eval(os.getenv("PRISM_DEBUG", "False")):
    for module in ["DependencyViewer_ui"]:
        try:
            del sys.modules[module]
        except:
            pass

import DependencyViewer_ui

from PrismUtils.Decorators import err_catcher


class DependencyViewer(QDialog, DependencyViewer_ui.Ui_dlg_DependencyViewer):
    """Dialog for visualizing version dependencies and external files.
    
    This class provides a tree view of all dependencies (source scenes, exports,
    external files) for a given version. Each dependency is displayed with its
    existence status, type, modification date, and path.
    
    Attributes:
        core: The Prism core instance
        depRoot: Path to the root version info file
        dependencies: Dictionary mapping dependency IDs to [path, item, parent_id]
    """
    
    def __init__(self, core: Any, depRoot: str) -> None:
        """Initialize the DependencyViewer dialog.
        
        Args:
            core: The Prism core instance providing access to pipeline functionality
            depRoot: Path to the version info file to analyze dependencies for
        """
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.core.parentWindow(self)

        self.tw_dependencies.setHeaderLabels(["Name", "", "Type", "Date", "Path"])
        self.tw_dependencies.header().setSectionResizeMode(1, QHeaderView.Fixed)

        self.dependencies = {}
        self.dependencyData = []
        self.loadRequestId = 0
        self.loadWorkers = []
        self.initLoadingIndicator()
        self.connectEvents()
        self.setRoot(depRoot)

        self.tw_dependencies.setColumnWidth(0, 400)
        self.tw_dependencies.setColumnWidth(1, 10)
        self.tw_dependencies.setColumnWidth(2, 100)
        self.tw_dependencies.setColumnWidth(3, 150)
        self.tw_dependencies.resizeColumnToContents(4)

        self.core.callback(name="onDependencyViewerOpen", args=[self])

    @err_catcher(name=__name__)
    def setRoot(self, root: str, allowCache: bool = True) -> None:
        """Load the root dependency tree without blocking the dialog."""
        self.depRoot = root
        self.loadRequestId += 1
        requestId = self.loadRequestId
        self.tw_dependencies.clear()
        self.dependencies = {}
        self.dependencyData = []
        self.l_root.setText("")
        self.e_search.setEnabled(False)
        self.showLoadingIndicator()

        worker = self.core.worker(self.core)
        self.loadWorkers.append(worker)

        def load():
            name = self.getRootName(root, allowCache=allowCache)
            data = self.collectDependencies(root, allowCache=allowCache)
            worker.dataSent.emit((requestId, name, data))

        worker.function = load
        worker.dataSent.connect(self.onDependenciesLoaded)
        worker.errored.connect(lambda error, request=requestId: self.onDependencyLoadError(request, error))
        worker.finished.connect(self.onDependencyWorkerFinished)
        worker.start()

    def getRootName(self, root: str, allowCache: bool = True) -> str:
        if os.path.basename(root).startswith("versioninfo"):
            return self.core.getConfig("version", configPath=root, allowCache=allowCache)
        if os.path.splitext(os.path.basename(root))[0].endswith("versioninfo"):
            filenames = glob.glob(os.path.splitext(root)[0][:-(len("versionInfo"))] + ".*")
            for filename in sorted(filenames):
                if os.path.splitext(filename)[1] != self.core.configs.getProjectExtension() or not filename.endswith("info.json"):
                    return os.path.basename(filename)
            return os.path.basename(root)

        return self.core.getConfig("filename", configPath=root, allowCache=allowCache)

    def initLoadingIndicator(self) -> None:
        viewport = self.tw_dependencies.viewport()
        self.w_loading = QWidget(viewport)
        self.w_loading.setObjectName("dependency_loading")
        self.w_loading.setStyleSheet("#dependency_loading {background-color: rgba(0, 0, 0, 50);}")
        self.w_loading.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(self.w_loading)
        layout.setAlignment(Qt.AlignCenter)
        self.l_loadingGif = QLabel(self.w_loading)
        self.l_loadingGif.setAlignment(Qt.AlignCenter)
        self.l_loadingGif.setFixedSize(60, 60)
        gifPath = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "prism-loading-dark.gif")
        self.loadingMovie = QMovie(gifPath, QByteArray(), self.w_loading)
        self.loadingMovie.frameChanged.connect(self.updateLoadingFrame)
        layout.addWidget(self.l_loadingGif, alignment=Qt.AlignHCenter)
        layout.addWidget(QLabel("Loading dependencies...", self.w_loading), alignment=Qt.AlignCenter)
        self.w_loading.hide()
        viewport.installEventFilter(self)

    def updateLoadingFrame(self, frameNumber: int) -> None:
        pixmap = self.loadingMovie.currentPixmap()
        if not pixmap.isNull():
            self.l_loadingGif.setPixmap(pixmap.scaled(self.l_loadingGif.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def eventFilter(self, obj: Any, event: Any) -> bool:
        if obj is self.tw_dependencies.viewport() and event.type() == QEvent.Resize:
            self.w_loading.setGeometry(obj.rect())
        return super(DependencyViewer, self).eventFilter(obj, event)

    def showLoadingIndicator(self) -> None:
        self.w_loading.setGeometry(self.tw_dependencies.viewport().rect())
        self.w_loading.show()
        self.w_loading.raise_()
        self.loadingMovie.start()

    def hideLoadingIndicator(self) -> None:
        self.loadingMovie.stop()
        self.w_loading.hide()

    @err_catcher(name=__name__)
    def onDependenciesLoaded(self, result: Tuple[int, str, List[Dict[str, Any]]]) -> None:
        requestId, rootName, data = result
        if requestId != self.loadRequestId:
            return

        self.l_root.setText(rootName or "")
        self.dependencyData = data
        self.populateDependencies()
        self.hideLoadingIndicator()
        self.e_search.setEnabled(True)
        if self.e_search.text():
            self.filterDeps(self.e_search.text())

    @err_catcher(name=__name__)
    def onDependencyLoadError(self, requestId: int, error: Any) -> None:
        if requestId != self.loadRequestId:
            return

        self.hideLoadingIndicator()
        self.e_search.setEnabled(True)
        self.core.popup("Failed to load dependencies: %s" % error)

    def onDependencyWorkerFinished(self) -> None:
        worker = self.sender()
        if worker in self.loadWorkers:
            self.loadWorkers.remove(worker)
        worker.deleteLater()

    def populateDependencies(self) -> None:
        self.tw_dependencies.clear()
        self.dependencies = {}

        def addItems(entries, parent, parentId):
            for entry in entries:
                item = QTreeWidgetItem([
                    os.path.basename(entry["path"]), "█", entry["type"],
                    entry["date"], entry["path"].replace("\\", "/"),
                ])
                item.setForeground(1, QColor(0, 255, 0) if entry["exists"] else QColor(255, 0, 0))
                parent.addChild(item)
                curId = str(len(self.dependencies) + 1)
                self.dependencies[curId] = [entry["path"], item, parentId]
                if entry["type"] != "File":
                    font = item.font(0)
                    font.setBold(True)
                    item.setFont(0, font)
                addItems(entry["children"], item, curId)

        addItems(self.dependencyData, self.tw_dependencies.invisibleRootItem(), "0")

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect UI signals to their respective slot methods.
        
        Connects search field changes, mouse events, and context menu requests
        to their corresponding handler methods.
        """
        self.e_search.textChanged.connect(self.filterDeps)
        self.tw_dependencies.mouseClickEvent = self.tw_dependencies.mouseReleaseEvent
        self.tw_dependencies.mouseReleaseEvent = lambda x: self.mouseClickEvent(
            x, "deps"
        )
        self.tw_dependencies.customContextMenuRequested.connect(
            lambda x: self.rclList("deps", x)
        )

    @err_catcher(name=__name__)
    def mouseClickEvent(self, event: Any, uielement: str) -> None:
        """Handle mouse click events on UI elements.
        
        Args:
            event: The mouse event object
            uielement: Identifier for the UI element that was clicked
            
        Processes left mouse button releases to clear selection when clicking
        empty areas of the tree widget.
        """
        if QEvent is not None:
            if event.type() == QEvent.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    if uielement == "deps":
                        self.tw_dependencies.mouseClickEvent(event)
                        index = self.tw_dependencies.indexAt(event.pos())
                        if index.data() is not None:
                            self.tw_dependencies.setCurrentIndex(
                                self.tw_dependencies.model().createIndex(-1, 0)
                            )

    @err_catcher(name=__name__)
    def rclList(self, listType: str, pos: Any) -> None:
        """Display context menu for tree items.
        
        Args:
            listType: Type of list ("deps" for dependencies)
            pos: Position where the context menu should appear
            
        Provides options to:
        - Refresh the dependency tree
        - Open the dependency file location in Explorer
        - Copy the file path to clipboard
        """
        rcmenu = QMenu(self)

        if listType == "deps":
            lw = self.tw_dependencies
        else:
            return

        refresh = QAction("Refresh", self)
        refresh.triggered.connect(lambda: self.setRoot(self.depRoot, allowCache=False))
        rcmenu.addAction(refresh)

        index = lw.indexAt(pos)
        iname = index.data()
        if iname is not None:
            item = lw.itemFromIndex(index)
            dirPath = item.data(4, Qt.DisplayRole)

            openex = QAction("Open in Explorer", self)
            openex.triggered.connect(lambda: self.core.openFolder(dirPath))
            rcmenu.addAction(openex)
            copAct = QAction("Copy path", self)
            copAct.triggered.connect(lambda: self.core.copyToClipboard(dirPath))
            rcmenu.addAction(copAct)

        rcmenu.exec_(QCursor.pos())

    def collectDependencies(self, versionInfo: str, ignore: Optional[List[str]] = None, visitedVersionInfos: Optional[set] = None, allowCache: bool = True) -> List[Dict[str, Any]]:
        """Read a dependency tree as plain data, without accessing Qt widgets."""
        ignore = ignore or []
        visitedVersionInfos = visitedVersionInfos or set()
        infoKey = os.path.normcase(os.path.abspath(versionInfo))
        if infoKey in visitedVersionInfos:
            return []

        visitedVersionInfos = visitedVersionInfos | {infoKey}
        source = self.core.getConfig("source scene", configPath=versionInfo, allowCache=allowCache)
        if not source:
            source = self.core.getConfig("sourceScene", configPath=versionInfo, allowCache=allowCache)

        deps = list(self.core.getConfig("dependencies", configPath=versionInfo, allowCache=allowCache) or [])
        extFiles = self.core.getConfig("externalFiles", configPath=versionInfo, allowCache=allowCache) or []
        if source is not None:
            deps.append(source)

        results = []
        for path in deps + [path for path in extFiles if path not in deps]:
            isExternal = path not in deps
            if not isExternal:
                if path in ignore:
                    continue
                ignore.append(path)

            checkPath = path
            if not isExternal and not os.path.exists(path):
                depDir = os.path.dirname(path)
                if os.path.exists(depDir) and os.listdir(depDir):
                    checkPath = depDir

            exists = os.path.exists(checkPath)
            date = ""
            if exists:
                cdate = datetime.datetime.fromtimestamp(os.path.getmtime(checkPath))
                date = cdate.replace(microsecond=0).strftime("%d.%m.%y,  %X")

            depInfo = self.core.getVersioninfoPath(path)
            self.core.configs.findDeprecatedConfig(depInfo)
            if not os.path.exists(depInfo):
                depInfo = os.path.join(os.path.dirname(path), "versioninfo" + self.core.configs.getProjectExtension())
                self.core.configs.findDeprecatedConfig(depInfo)
            if not os.path.exists(depInfo):
                depInfo = os.path.join(os.path.dirname(os.path.dirname(path)), "versioninfo" + self.core.configs.getProjectExtension())
                self.core.configs.findDeprecatedConfig(depInfo)

            children = []
            if os.path.exists(depInfo):
                children = self.collectDependencies(depInfo, ignore=ignore[:], visitedVersionInfos=visitedVersionInfos, allowCache=allowCache)

            results.append({
                "path": path,
                "type": "File" if isExternal else "Source Scene" if path == source else "Export",
                "date": date,
                "exists": exists,
                "children": children,
            })

        return results

    @err_catcher(name=__name__)
    def updateDependencies(self, depID: str, versionInfo: str, ignore: Optional[List[str]] = None, visitedVersionInfos: Optional[set] = None) -> None:
        """Recursively update the dependency tree from a version info file.
        
        Args:
            depID: Unique identifier for this dependency level ("0" for root)
            versionInfo: Path to the version info configuration file
            ignore: List of dependency paths already processed to avoid duplicates
            
        This method:
        1. Reads dependencies and external files from version info
        2. Creates tree items showing existence status (green/red indicator)
        3. Displays type (Source Scene/Export/File), date, and path
        4. Recursively processes dependencies of dependencies
        """
        ignore = ignore or []
        visitedVersionInfos = visitedVersionInfos or set()
        infoKey = os.path.normcase(os.path.abspath(versionInfo))
        if infoKey in visitedVersionInfos:
            return

        visitedVersionInfos = visitedVersionInfos | {infoKey}
        source = self.core.getConfig("source scene", configPath=versionInfo)
        if not source:
            source = self.core.getConfig("sourceScene", configPath=versionInfo)

        deps = (
            self.core.getConfig("dependencies", configPath=versionInfo)
            or []
        )
        extFiles = (
            self.core.getConfig("externalFiles", configPath=versionInfo)
            or []
        )

        if source is not None:
            deps.append(source)

        if depID == "0":
            depItem = self.tw_dependencies.invisibleRootItem()
        else:
            depItem = self.dependencies[depID][1]

        for i in deps:
            existText = "█"
            depPath = i
            if depPath in ignore:
                continue

            ignore.append(depPath)

            if not os.path.exists(i):
                depDir = os.path.dirname(i)
                if os.path.exists(depDir) and len(os.listdir(depDir)) > 0:
                    depPath = depDir

            if os.path.exists(depPath):
                cdate = datetime.datetime.fromtimestamp(os.path.getmtime(depPath))
                cdate = cdate.replace(microsecond=0)
                date = cdate.strftime("%d.%m.%y,  %X")
                existColor = QColor(0, 255, 0)
            else:
                date = ""
                existColor = QColor(255, 0, 0)

            if i == source:
                dType = "Source Scene"
            else:
                dType = "Export"

            item = QTreeWidgetItem(
                [os.path.basename(i), existText, dType, date, i.replace("\\", "/")]
            )

            item.setForeground(1, existColor)

            depItem.addChild(item)
            curID = str(len(self.dependencies) + 1)

            self.dependencies[curID] = [i, item, depID]

            iFont = item.font(0)
            iFont.setBold(True)
            item.setFont(0, iFont)
            depInfo = self.core.getVersioninfoPath(i)
            self.core.configs.findDeprecatedConfig(depInfo)
            if not os.path.exists(depInfo):
                depInfo = os.path.join(
                    os.path.dirname(i), "versioninfo" + self.core.configs.getProjectExtension()
                )
                self.core.configs.findDeprecatedConfig(depInfo)
            if not os.path.exists(depInfo):
                depInfo = os.path.join(
                    os.path.dirname(os.path.dirname(i)),
                    "versioninfo" + self.core.configs.getProjectExtension(),
                )
                self.core.configs.findDeprecatedConfig(depInfo)

            if os.path.exists(depInfo):
                self.updateDependencies(curID, depInfo, ignore=ignore[:], visitedVersionInfos=visitedVersionInfos)

        for i in extFiles:
            if i in deps:
                continue

            existText = "█"
            if os.path.exists(i):
                cdate = datetime.datetime.fromtimestamp(os.path.getmtime(i))
                cdate = cdate.replace(microsecond=0)
                date = cdate.strftime("%d.%m.%y,  %X")
                existColor = QColor(0, 255, 0)
            else:
                date = ""
                existColor = QColor(255, 0, 0)

            item = QTreeWidgetItem(
                [os.path.basename(i), existText, "File", date, i.replace("\\", "/")]
            )

            item.setForeground(1, existColor)
            depItem.addChild(item)

            curID = str(len(self.dependencies) + 1)
            self.dependencies[curID] = [i, item, depID]

            depInfo = self.core.getVersioninfoPath(i)
            self.core.configs.findDeprecatedConfig(depInfo)
            if not os.path.exists(depInfo):
                depInfo = os.path.join(
                    os.path.dirname(i), "versioninfo" + self.core.configs.getProjectExtension()
                )
                self.core.configs.findDeprecatedConfig(depInfo)
            if not os.path.exists(depInfo):
                depInfo = os.path.join(
                    os.path.dirname(os.path.dirname(i)),
                    "versioninfo" + self.core.configs.getProjectExtension(),
                )
                self.core.configs.findDeprecatedConfig(depInfo)

            if os.path.exists(depInfo):
                self.updateDependencies(curID, depInfo, ignore=ignore[:], visitedVersionInfos=visitedVersionInfos)

    @err_catcher(name=__name__)
    def filterDeps(self, filterStr: str) -> None:
        """Filter the dependency tree based on a search string.
        
        Args:
            filterStr: Text to filter dependencies by (case-insensitive)
            
        If filterStr is empty, displays all dependencies. Otherwise, shows only
        dependencies whose paths contain the filter string, along with their
        parent hierarchy.
        """
        self.clearItem(self.tw_dependencies.invisibleRootItem())

        if filterStr == "":
            self.populateDependencies()
        else:
            for i in self.dependencies:
                if filterStr.lower() in self.dependencies[i][0].lower():
                    depID = i
                    while depID != "0":
                        parID = self.dependencies[depID][2]
                        if parID == "0":
                            self.tw_dependencies.invisibleRootItem().addChild(
                                self.dependencies[depID][1]
                            )
                        else:
                            self.dependencies[parID][1].addChild(
                                self.dependencies[depID][1]
                            )
                        depID = parID

            self.tw_dependencies.expandAll()

    @err_catcher(name=__name__)
    def clearItem(self, item: QTreeWidgetItem) -> None:
        """Recursively clear all children from a tree widget item.
        
        Args:
            item: The tree widget item to clear
            
        Removes all child items recursively from the given item.
        """
        for i in range(item.childCount()):
            self.clearItem(item.child(0))
            item.takeChild(0)
