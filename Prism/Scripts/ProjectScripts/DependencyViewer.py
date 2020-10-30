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
# Copyright (C) 2016-2020 Richard Frangenberg
#
# Licensed under GNU GPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


import os
import sys
import datetime

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2

for i in ["DependencyViewer_ui", "DependencyViewer_ui_ps2"]:
    try:
        del sys.modules[i]
    except:
        pass

if psVersion == 1:
    import DependencyViewer_ui
else:
    import DependencyViewer_ui_ps2 as DependencyViewer_ui

from PrismUtils.Decorators import err_catcher


class DependencyViewer(QDialog, DependencyViewer_ui.Ui_dlg_DependencyViewer):
    def __init__(self, core, depRoot):
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.core.parentWindow(self)

        if os.path.basename(depRoot).startswith("versioninfo"):
            rootName = self.core.getConfig(
                cat="information", param="version", configPath=depRoot
            )
        else:
            rootName = self.core.getConfig(
                cat="information", param="filename", configPath=depRoot
            )

        self.l_root.setText(rootName)

        self.tw_dependencies.setHeaderLabels(["Name", "", "Type", "Date", "Path"])

        if psVersion == 1:
            self.tw_dependencies.header().setResizeMode(1, QHeaderView.Fixed)
        else:
            self.tw_dependencies.header().setSectionResizeMode(1, QHeaderView.Fixed)

        self.dependencies = {}
        self.depRoot = depRoot

        self.connectEvents()
        self.updateDependencies("0", depRoot)

        self.tw_dependencies.setColumnWidth(0, 400)
        self.tw_dependencies.setColumnWidth(1, 10)
        self.tw_dependencies.setColumnWidth(2, 100)
        self.tw_dependencies.setColumnWidth(3, 150)
        self.tw_dependencies.resizeColumnToContents(4)

        self.core.callback(
            name="onDependencyViewerOpen", types=["curApp", "custom"], args=[self]
        )

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.e_search.textChanged.connect(self.filterDeps)
        self.tw_dependencies.mouseClickEvent = self.tw_dependencies.mouseReleaseEvent
        self.tw_dependencies.mouseReleaseEvent = lambda x: self.mouseClickEvent(
            x, "deps"
        )
        self.tw_dependencies.customContextMenuRequested.connect(
            lambda x: self.rclList("deps", x)
        )

    @err_catcher(name=__name__)
    def mouseClickEvent(self, event, uielement):
        if QEvent != None:
            if event.type() == QEvent.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    if uielement == "deps":
                        self.tw_dependencies.mouseClickEvent(event)
                        index = self.tw_dependencies.indexAt(event.pos())
                        if index.data() == None:
                            self.tw_dependencies.setCurrentIndex(
                                self.tw_dependencies.model().createIndex(-1, 0)
                            )

    @err_catcher(name=__name__)
    def rclList(self, listType, pos):
        rcmenu = QMenu(self)

        if listType == "deps":
            lw = self.tw_dependencies
        else:
            return

        iname = lw.indexAt(pos).data()

        if iname is None:
            return

        dirPath = lw.model().index(lw.indexAt(pos).row(), 4).data()

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
    def updateDependencies(self, depID, versionInfo):
        source = self.core.getConfig(
            cat="information", param="source scene", configPath=versionInfo
        )
        deps = self.core.getConfig(
            cat="information", param="Dependencies", configPath=versionInfo
        ) or []
        extFiles = self.core.getConfig(
            cat="information", param="External files", configPath=versionInfo
        ) or []

        if source is not None:
            deps.append(source)

        if depID == "0":
            depItem = self.tw_dependencies.invisibleRootItem()
        else:
            depItem = self.dependencies[depID][1]

        for i in deps:
            if pVersion == 2:
                existText = unicode("█", "utf-8")
            else:
                existText = "█"

            depPath = i

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

            depInfo = os.path.join(os.path.dirname(i), "versioninfo.yml")
            self.core.configs.findDeprecatedConfig(depInfo)
            if not os.path.exists(depInfo):
                depInfo = os.path.join(
                    os.path.dirname(os.path.dirname(i)), "versioninfo.yml"
                )
                self.core.configs.findDeprecatedConfig(depInfo)

            if os.path.exists(depInfo):
                self.updateDependencies(curID, depInfo)

        for i in extFiles:
            if i in deps:
                continue

            if pVersion == 2:
                existText = unicode("█", "utf-8")
            else:
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

    @err_catcher(name=__name__)
    def filterDeps(self, filterStr):
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
    def clearItem(self, item):
        for i in range(item.childCount()):
            self.clearItem(item.child(0))
            item.takeChild(0)
