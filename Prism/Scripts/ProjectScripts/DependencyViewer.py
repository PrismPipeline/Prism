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
        self.connectEvents()
        self.setRoot(depRoot)

        self.tw_dependencies.setColumnWidth(0, 400)
        self.tw_dependencies.setColumnWidth(1, 10)
        self.tw_dependencies.setColumnWidth(2, 100)
        self.tw_dependencies.setColumnWidth(3, 150)
        self.tw_dependencies.resizeColumnToContents(4)

        self.core.callback(name="onDependencyViewerOpen", args=[self])

    @err_catcher(name=__name__)
    def setRoot(self, root: str) -> None:
        """Set the root version info file and update the dependency tree.
        
        Args:
            root: Path to the version info file to set as the root
            
        This method:
        1. Determines the display name from the version info
        2. Clears the existing dependency tree
        3. Updates dependencies starting from the new root
        """
        self.depRoot = root

        if os.path.basename(self.depRoot).startswith("versioninfo"):
            rootName = self.core.getConfig("version", configPath=self.depRoot)
        elif os.path.splitext(os.path.basename(self.depRoot))[0].endswith("versioninfo"):
            filenames = glob.glob(os.path.splitext(self.depRoot)[0][:-(len("versionInfo"))] + ".*")
            for filename in sorted(filenames):
                if os.path.splitext(filename)[1] != self.core.configs.getProjectExtension():
                    rootName = os.path.basename(filename)
                    break
        else:
            rootName = self.core.getConfig("filename", configPath=self.depRoot)

        self.l_root.setText(rootName)
        self.clearItem(self.tw_dependencies.invisibleRootItem())
        self.dependencies = {}
        self.updateDependencies("0", self.depRoot)

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
        - Open the dependency file location in Explorer
        - Copy the file path to clipboard
        """
        rcmenu = QMenu(self)

        if listType == "deps":
            lw = self.tw_dependencies
        else:
            return

        index = lw.indexAt(pos)
        iname = index.data()
        if iname is None:
            return

        item = lw.itemFromIndex(index)
        dirPath = item.data(4, Qt.DisplayRole)

        openex = QAction("Open in Explorer", self)
        openex.triggered.connect(lambda: self.core.openFolder(dirPath))
        rcmenu.addAction(openex)
        copAct = QAction("Copy path", self)
        copAct.triggered.connect(lambda: self.core.copyToClipboard(dirPath))
        rcmenu.addAction(copAct)

        if rcmenu.isEmpty():
            return False

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def updateDependencies(self, depID: str, versionInfo: str, ignore: Optional[List[str]] = None) -> None:
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
                self.updateDependencies(curID, depInfo, ignore=ignore[:])

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
                self.updateDependencies(curID, depInfo, ignore=ignore[:])

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
            self.dependencies = {}
            self.updateDependencies("0", self.depRoot)
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
