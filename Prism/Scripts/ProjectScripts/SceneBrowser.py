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
import shutil
import logging
import traceback
import re

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2

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
    def __init__(self, core, projectBrowser=None, refresh=True):
        QWidget.__init__(self)
        self.setupUi(self)
        self.core = core
        self.projectBrowser = projectBrowser

        logger.debug("Initializing Scene Browser")

        self.core.parentWindow(self)

        self.filteredAssets = []
        self.scenefileData = []
        self.sceneItemWidgets = []
        self.depIcons = {}
        self.initialized = False

        self.shotPrvXres = 250
        self.shotPrvYres = 141

        self.tabLabels = {
            "Assets": "Assets",
            "Shots": "Shots",
            "Recent": "Recent",
        }
        self.tableColumnLabels = {
            "Version": "Version",
            "Comment": "Comment",
            "Date": "Date",
            "User": "User",
            "Name": "Name",
            "Department": "Department",
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
                result = self.navigate(navData)
            else:
                result = self.navigateToCurrent()

            if not result:
                self.entityChanged()

            self.initialized = True

        if prevTab:
            if hasattr(prevTab, "w_entities"):
                self.w_entities.syncFromWidget(prevTab.w_entities)
            elif hasattr(prevTab, "getSelectedData"):
                self.w_entities.navigate(prevTab.getSelectedData())

    @err_catcher(name=__name__)
    def loadLayout(self):
        import EntityWidget

        self.w_entities = EntityWidget.EntityWidget(core=self.core, refresh=False)
        self.splitter_5.insertWidget(0, self.w_entities)

        self.tw_scenefiles.setShowGrid(False)

        self.w_scenefileItems = QWidget()
        self.w_scenefileItems.setObjectName("itemview")
        self.lo_scenefileItems = QVBoxLayout()
        self.w_scenefileItems.setLayout(self.lo_scenefileItems)
        self.sa_scenefileItems.setWidget(self.w_scenefileItems)
        self.sa_scenefileItems.setWidgetResizable(True)
        # self.sa_scenefileItems.setStyleSheet("QScrollArea { border: 0px}")

        cData = self.core.getConfig()
        brsData = cData.get("browser", {})
        self.refreshAppFilters(browserData=brsData)
        self.b_scenefilter.setToolTip(
            "Filter scenefiles (hold CTRL to toggle multiple types)"
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

        if hasattr(QApplication.instance(), "styleSheet"):
            ssheet = QApplication.instance().styleSheet()
            ssheet = ssheet.replace("QScrollArea", "Qdisabled")
            ssheet = ssheet.replace("QListView", "QScrollArea")
            self.sa_scenefileItems.setStyleSheet(ssheet)

    @err_catcher(name=__name__)
    def refreshAppFilters(self, browserData=None):
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
    def showEvent(self, event):
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
        if self.core.pb:
            self.core.pb.productBrowser.setHeaderHeight(h)
            self.core.pb.mediaBrowser.setHeaderHeight(h)

    @err_catcher(name=__name__)
    def connectEvents(self):
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
        self.tw_scenefiles.customContextMenuRequested.connect(self.rclFile)
        self.tw_scenefiles.doubleClicked.connect(self.sceneDoubleClicked)
        self.tw_scenefiles.setMouseTracking(True)
        self.tw_scenefiles.mouseMoveEvent = lambda x: self.tableMoveEvent(x)
        self.tw_scenefiles.leaveEvent = lambda x: self.tableLeaveEvent(x)
        self.tw_scenefiles.focusOutEvent = lambda x: self.tableFocusOutEvent(x)

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
        self.sa_scenefileItems.customContextMenuRequested.connect(self.rclItemView)

    @err_catcher(name=__name__)
    def saveSettings(self, data):
        from qtpy import QT5
        if QT5:
            sortOrder = int(self.tw_scenefiles.horizontalHeader().sortIndicatorOrder())
        else:
            sortOrder = self.tw_scenefiles.horizontalHeader().sortIndicatorOrder().value

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

    @err_catcher(name=__name__)
    def navigateToCurrent(self):
        fileName = self.core.getCurrentFileName()
        fileNameData = self.core.getScenefileData(fileName)
        return self.navigate(fileNameData)

    @err_catcher(name=__name__)
    def navigate(self, data):
        # logger.debug("navigate to: %s" % data)
        if not isinstance(data, dict):
            return

        prevEntity = self.getCurrentEntity()
        prevDep = self.getCurrentDepartment()
        self.lw_departments.blockSignals(True)
        if data.get("type") in ["asset", "assetFolder"]:
            self.w_entities.navigate(data)
        elif data.get("type") in ["shot", "sequence"]:
            shotName = data.get("shot", "")
            seqName = data.get("sequence", "")

            self.w_entities.navigate(
                {"type": "shot", "sequence": seqName, "shot": shotName}
            )

        if "department" not in data:
            self.lw_departments.blockSignals(False)
            if prevDep != self.getCurrentDepartment() or prevEntity != self.getCurrentEntity():
                self.departmentChanged()

            return

        fItems = self.lw_departments.findItems(data["department"], Qt.MatchExactly)
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

        if "task" not in data:
            self.lw_tasks.blockSignals(False)
            if prevTask != self.getCurrentTask():
                self.taskChanged()

            return

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

        if os.path.isabs(data.get("filename", "")):
            curFname = data["filename"]
            self.selectScenefile(curFname)

        return True

    @err_catcher(name=__name__)
    def selectScenefile(self, curFname):
        globalCurFname = self.core.convertPath(curFname, "global")
        if self.b_sceneLayoutItems.isChecked():
            for widget in self.sceneItemWidgets:
                cmpFname = os.path.normpath(widget.data["filename"])
                if cmpFname in [curFname, globalCurFname]:
                    widget.select()
                    self.sa_scenefileItems.ensureWidgetVisible(widget)
                    break
        else:
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
    def sceneTabChanged(self):
        self.entityChanged()

    @err_catcher(name=__name__)
    def entityChanged(self, item=None):
        self.refreshEntityInfo()
        self.refreshDepartments(restoreSelection=True)

    @err_catcher(name=__name__)
    def entityCreated(self, data):
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
    def mousedb(self, event, widget):
        entity = self.getCurrentEntity()
        if not entity:
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
    def mouseClickEvent(self, event, widget):
        if event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                index = widget.indexAt(event.pos())
                if index.data() is None:
                    widget.setCurrentIndex(widget.model().createIndex(-1, 0))
                widget.mouseClickEvent(event)

    @err_catcher(name=__name__)
    def mouseClickItemViewEvent(self, event):
        if event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                self.deselectItems()

    @err_catcher(name=__name__)
    def tableMoveEvent(self, event):
        self.showDetailWin(event)
        if hasattr(self, "detailWin") and self.detailWin.isVisible():
            self.detailWin.move(QCursor.pos().x() + 20, QCursor.pos().y())

    @err_catcher(name=__name__)
    def showDetailWin(self, event):
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

        if not os.path.exists(infoPath) and not os.path.exists(prvPath):
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
            self.core.parentWindow(self.detailWin)
            winwidth = 320
            winheight = 10
            VBox = QVBoxLayout()
            if os.path.exists(prvPath):
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
                    descriptionL = QLabel("Description:\t")
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

                sizeL = QLabel("Size:\t")
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
    def tableLeaveEvent(self, event):
        if hasattr(self, "detailWin") and self.detailWin.isVisible():
            self.detailWin.close()

    @err_catcher(name=__name__)
    def tableFocusOutEvent(self, event):
        if hasattr(self, "detailWin") and self.detailWin.isVisible():
            self.detailWin.close()

    @err_catcher(name=__name__)
    def sceneLayoutItemsToggled(self, state, refresh=True):
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
            self.refreshScenefiles(reloadFiles=False)

    @err_catcher(name=__name__)
    def sceneLayoutListToggled(self, state, refresh=True):
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
            self.refreshScenefiles(reloadFiles=False)

    @err_catcher(name=__name__)
    def showSceneFilterMenu(self, state=None):
        self.showContextMenu("sceneFilter")

    @err_catcher(name=__name__)
    def getContextMenu(self, menuType, **kwargs):
        menu = None
        if menuType == "sceneFilter":
            menu = self.getSceneFilterMenu(**kwargs)

        return menu

    @err_catcher(name=__name__)
    def showContextMenu(self, menuType, **kwargs):
        menu = self.getContextMenu(menuType, **kwargs)
        self.core.callback(
            name="sceneBrowserContextMenuRequested",
            args=[self, menuType, menu],
        )
        if not menu or menu.isEmpty():
            return

        menu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def getSceneFilterMenu(self):
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
    def reopenContextMenu(self, menuType, menu, pos):
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
    def getAppFilter(self, key):
        return self.appFilters[key]["show"]

    @err_catcher(name=__name__)
    def setAppFilter(self, key, value, refresh=True):
        self.appFilters[key]["show"] = value
        self.refreshAppFilterIndicator()

        if refresh:
            self.refreshScenefiles()

    @err_catcher(name=__name__)
    def refreshAppFilterIndicator(self):
        isActive = False
        for app in self.appFilters:
            if not self.appFilters[app]["show"]:
                isActive = True
        
        ssheet = "QWidget{padding: 0; margin: 0;}"
        if isActive:
            ssheet += "QWidget{background-color: rgba(220, 90, 40, 255);}"

        self.b_scenefilter.setStyleSheet(ssheet)

    @err_catcher(name=__name__)
    def rightClickedList(self, widget, pos):
        entity = self.getCurrentEntity()
        if not entity or entity["type"] not in ["asset", "shot", "sequence"]:
            return

        rcmenu = QMenu(self)
        typename = "Task"
        callbackName = ""

        widgetType = "department" if widget == self.lw_departments else "task"

        if entity["type"] == "asset" and widgetType == "department":
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
            if not entity["shot"]:
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

        createAct = QAction(label, self)
        if widgetType == "department":
            createAct.triggered.connect(self.createDepartmentDlg)
        else:
            createAct.triggered.connect(self.createTaskDlg)

        rcmenu.addAction(createAct)
        if widgetType == "department":
            iname = (widget.indexAt(pos)).data(Qt.UserRole)
        else:
            iname = (widget.indexAt(pos)).data()

        if refresh:
            act_refresh = QAction("Refresh", self)
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

            openex = QAction("Open in explorer", self)
            openex.triggered.connect(lambda: self.core.openFolder(dirPath))
            rcmenu.addAction(openex)
            copAct = QAction("Copy", self)
            copAct.triggered.connect(lambda: self.core.copyToClipboard(dirPath, file=True))
            rcmenu.addAction(copAct)
            for i in prjMngMenus:
                if i:
                    rcmenu.addAction(i)
        elif "path" in locals():
            widget.setCurrentIndex(widget.model().createIndex(-1, 0))
            openex = QAction("Open in explorer", self)
            openex.triggered.connect(lambda: self.core.openFolder(path))
            rcmenu.addAction(openex)
            copAct = QAction("Copy", self)
            copAct.triggered.connect(lambda: self.core.copyToClipboard(path, file=True))
            rcmenu.addAction(copAct)

        if callbackName:
            self.core.callback(
                name=callbackName,
                args=[self, rcmenu, widget.indexAt(pos)],
            )

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def rclFile(self, pos):
        if self.tw_scenefiles.selectedIndexes() != []:
            idx = self.tw_scenefiles.selectedIndexes()[0]
            irow = idx.row()
            filepath = self.core.fixPath(
                self.tw_scenefiles.model().index(irow, 0).data(Qt.UserRole)
            )
            self.tw_scenefiles.setCurrentIndex(
                self.tw_scenefiles.model().createIndex(irow, 0)
            )
        else:
            filepath = ""

        self.openScenefileContextMenu(filepath)

    @err_catcher(name=__name__)
    def rclItemView(self, pos):
        self.deselectItems()
        self.openScenefileContextMenu()

    @err_catcher(name=__name__)
    def openScenefileContextMenu(self, filepath=None):
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
        current = QAction("Create new version from current", self)
        current.triggered.connect(lambda: self.createFromCurrent())
        if self.core.appPlugin.pluginName == "Standalone":
            current.setEnabled(False)
        rcmenu.addAction(current)
        emp = QMenu("Create new version from preset", self)
        scenes = self.core.entities.getPresetScenes()
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

        newPreset = QAction("< Create new preset from current >", self)
        newPreset.triggered.connect(self.core.entities.createPresetScene)
        emp.addAction(newPreset)
        if self.core.appPlugin.pluginName == "Standalone":
            newPreset.setEnabled(False)

        rcmenu.addMenu(emp)
        autob = QMenu("Create new version from autobackup", self)
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
            globalAct = QAction("Copy to global", self)
            if self.core.useLocalFiles and filepath.startswith(
                self.core.localProjectPath
            ):
                globalAct.triggered.connect(lambda: self.copyToGlobal(filepath))
            else:
                globalAct.setEnabled(False)
            rcmenu.addAction(globalAct)

            actDeps = QAction("Show dependencies...", self)
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

            actCom = QAction("Edit Comment...", self)
            actCom.triggered.connect(lambda: self.editComment(filepath))
            rcmenu.addAction(actCom)

            actCom = QAction("Edit Description...", self)
            actCom.triggered.connect(lambda: self.editDescription(filepath))
            rcmenu.addAction(actCom)

        act_refresh = QAction("Refresh", self)
        act_refresh.triggered.connect(lambda: self.refreshScenefiles(restoreSelection=True))
        rcmenu.addAction(act_refresh)

        if self.core.useLocalFiles:
            locations = ["Global", "Local"]
            for location in locations:
                fpath = self.core.convertPath(filepath, location.lower())
                m_loc = QMenu(location, self)

                openex = QAction("Open in Explorer", self)
                openex.triggered.connect(lambda x=None, f=fpath: self.core.openFolder(f))
                m_loc.addAction(openex)

                copAct = QAction("Copy", self)
                copAct.triggered.connect(lambda x=None, f=fpath: self.core.copyToClipboard(f, file=True))
                m_loc.addAction(copAct)

                copAct = QAction("Copy path for next version", self)
                copAct.triggered.connect(lambda x=None, l=location: self.prepareNewVersion(location=l.lower()))
                m_loc.addAction(copAct)

                past = QAction("Paste new version", self)
                past.triggered.connect(lambda x=None, l=location: self.pastefile(location=l.lower()))
                m_loc.addAction(past)

                rcmenu.addMenu(m_loc)
        else:
            openex = QAction("Open in Explorer", self)
            openex.triggered.connect(lambda: self.core.openFolder(filepath))
            rcmenu.addAction(openex)

            copAct = QAction("Copy", self)
            copAct.triggered.connect(lambda: self.core.copyToClipboard(filepath, file=True))
            rcmenu.addAction(copAct)

            copAct = QAction("Copy path for next version", self)
            copAct.triggered.connect(self.prepareNewVersion)
            rcmenu.addAction(copAct)

            past = QAction("Paste new version", self)
            past.triggered.connect(self.pastefile)
            rcmenu.addAction(past)

        self.core.callback(name="openPBFileContextMenu", args=[self, rcmenu, filepath])

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def prepareNewVersion(self, location="global"):
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
    def sceneDoubleClicked(self, index):
        filepath = index.model().index(index.row(), 0).data(Qt.UserRole)
        self.exeFile(filepath)

    @err_catcher(name=__name__)
    def exeFile(self, filepath):
        if self.core.getLockScenefilesEnabled():
            from PrismUtils import Lockfile
            lf = Lockfile.Lockfile(self.core, filepath)
            if lf.isLocked():
                showPopup = True

                modTime = self.core.getFileModificationDate(lf.lockPath, asString=False, asDatetime=True)
                age = datetime.datetime.now() - modTime
                if age < datetime.timedelta(minutes=11):
                    lfData = self.core.configs.readJson(path=lf.lockPath, ignoreErrors=True) or {}
                    if lfData.get("username2"):
                        if lfData.get("username") == self.core.username:
                            showPopup = False
                        else:
                            msg = "This scenefile is currently being used by \"%s\"." % lfData.get("username")
                    else:
                        msg = "This scenefile is currently being used."

                    if showPopup:
                        result = self.core.popupQuestion(msg, buttons=["Continue", "Cancel"], icon=QMessageBox.Warning)
                        if result != "Continue":
                            return

        wasSmOpen = self.core.isStateManagerOpen()
        if wasSmOpen:
            self.core.sm.close()

        if self.core.useLocalFiles and self.core.fileInPipeline(filepath):
            lfilepath = self.core.convertPath(filepath, "local")

            if not os.path.exists(lfilepath):
                if not os.path.exists(os.path.dirname(lfilepath)):
                    try:
                        os.makedirs(os.path.dirname(lfilepath))
                    except:
                        self.core.popup("The directory could not be created")
                        return

                self.core.copySceneFile(filepath, lfilepath)

            filepath = lfilepath

        if self.core.appPlugin.pluginName == "Standalone":
            self.core.openFile(filepath)
        else:
            filepath = filepath.replace("\\", "/")
            logger.debug("Opening scene " + filepath)
            self.core.appPlugin.openScene(self, filepath)

        self.core.addToRecent(filepath)
        if wasSmOpen:
            self.core.stateManager()

        navData = self.getSelectedContext()
        self.refreshScenefiles()
        self.navigate(data=navData)

        if (
            self.core.getCurrentFileName().replace("\\", "/") == filepath
            and self.projectBrowser.actionCloseAfterLoad.isChecked()
        ):
            self.window().close()

    @err_catcher(name=__name__)
    def createFromCurrent(self):
        entity = self.getCurrentEntity()
        curDep = self.getCurrentDepartment()
        curTask = self.getCurrentTask()
        filepath = self.core.entities.createVersionFromCurrentScene(
            entity=entity, department=curDep, task=curTask
        )
        self.core.addToRecent(filepath)
        self.refreshScenefiles()

    @err_catcher(name=__name__)
    def autoback(self, prog):
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
            self.refreshScenefiles()

    @err_catcher(name=__name__)
    def createSceneFromPreset(
        self,
        scene,
        entity=None,
        step=None,
        category=None,
        comment=None,
        openFile=True,
        version=None,
        location="local",
    ):
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
                self.core.callback(
                    name="postLoadPresetScene",
                    args=[self, filePath],
                )
            else:
                self.core.addToRecent(filePath)
                self.refreshScenefiles()

        return filePath

    @err_catcher(name=__name__)
    def pastefile(self, location=None):
        copiedFile = self.core.getClipboard()
        if not copiedFile or not os.path.isfile(copiedFile):
            msg = "No valid filepath in clipboard."
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

        self.refreshScenefiles()

    @err_catcher(name=__name__)
    def getStep(self, departments):
        entity = self.getCurrentEntity()
        self.ss = ItemList.ItemList(core=self.core, entity=entity)
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

        self.ss.setWindowTitle("Add Departments")
        self.core.parentWindow(self.ss, parent=self)
        self.ss.tw_steps.setFocus()
        self.ss.tw_steps.doubleClicked.connect(lambda x=None, b=self.ss.buttonBox.buttons()[0]:self.ss.buttonboxClicked(b))

        self.ss.tw_steps.setColumnCount(1)
        self.ss.tw_steps.setHorizontalHeaderLabels(["Department"])
        self.ss.tw_steps.horizontalHeader().setVisible(False)
        for department in departments:
            rc = self.ss.tw_steps.rowCount()
            self.ss.tw_steps.insertRow(rc)
            name = "%s (%s)" % (department["name"], department["abbreviation"])
            nameItem = QTableWidgetItem(name)
            nameItem.setData(Qt.UserRole, department)
            self.ss.tw_steps.setItem(rc, 0, nameItem)

        self.core.callback(name="onDepartmentDlgOpen", args=[self, self.ss])
        if not getattr(self.ss, "allowShow", True):
            return False

        self.ss.exec_()

    @err_catcher(name=__name__)
    def createSteps(self, entity, steps, createTask=True):
        if len(steps) > 0:
            navData = entity.copy()
            createdDirs = []

            for step in steps:
                result = self.core.entities.createDepartment(
                    step, entity, createCat=createTask
                )
                if result:
                    createdDirs.append(step)
                    navData["department"] = self.core.entities.getLongDepartmentName(entity["type"], step) or step

            if createdDirs:
                self.refreshDepartments()
                self.navigate(data=navData)

    @err_catcher(name=__name__)
    def getSelectedContext(self):
        navData = self.getCurrentEntity() or {}
        navData["department"] = self.getCurrentDepartment()
        navData["task"] = self.getCurrentTask()
        navData["filename"] = self.getSelectedScenefile()
        return navData

    @err_catcher(name=__name__)
    def refreshUI(self):
        self.w_entities.getCurrentPage().tw_tree.blockSignals(True)
        self.w_entities.refreshEntities(restoreSelection=True)
        self.w_entities.getCurrentPage().tw_tree.blockSignals(False)
        self.entityChanged()
        self.refreshStatus = "valid"

    @err_catcher(name=__name__)
    def refreshDepartments(self, restoreSelection=False):
        if restoreSelection:
            curDep = self.getCurrentDepartment()

        wasBlocked = self.lw_departments.signalsBlocked()
        if not wasBlocked:
            self.lw_departments.blockSignals(True)

        self.lw_departments.clear()

        curEntities = self.getCurrentEntities()
        if len(curEntities) != 1 or curEntities[0]["type"] not in ["asset", "shot", "sequence"]:
            self.lw_departments.blockSignals(False)
            self.refreshTasks()
            return

        steps = self.core.entities.getSteps(entity=curEntities[0])
        for s in steps:
            longName = self.core.entities.getLongDepartmentName(curEntities[0]["type"], s) or s
            sItem = QListWidgetItem(longName)
            sItem.setData(Qt.UserRole, s)
            icon = self.getDepartmentIcon(longName)
            if icon:
                sItem.setIcon(icon)

            self.lw_departments.addItem(sItem)

        if self.lw_departments.count() > 0:
            if restoreSelection and curDep in steps:
                self.lw_departments.setCurrentRow(steps.index(curDep))
            else:
                self.lw_departments.setCurrentRow(0)

        if not wasBlocked:
            self.lw_departments.blockSignals(False)
            self.refreshTasks(restoreSelection=True)

    @err_catcher(name=__name__)
    def getDepartmentIcon(self, department):
        if department in self.depIcons:
            return self.depIcons[department]

        path = os.path.join(self.core.projects.getPipelineFolder(), "Icons", department + ".png")
        icon = QIcon(path)
        self.depIcons[department] = icon
        return icon

    @err_catcher(name=__name__)
    def refreshTasks(self, restoreSelection=False):
        if restoreSelection:
            curTask = self.getCurrentTask()

        wasBlocked = self.lw_tasks.signalsBlocked()
        if not wasBlocked:
            self.lw_tasks.blockSignals(True)

        self.lw_tasks.clear()

        curEntities = self.getCurrentEntities()
        curDep = self.getCurrentDepartment()
        if len(curEntities) != 1 or not curDep:
            self.refreshScenefiles()
            if not wasBlocked:
                self.lw_tasks.blockSignals(False)

            return

        curEntity = curEntities[0]
        if curEntity["type"] == "asset":
            if (
                self.core.compareVersions(self.core.projectVersion, "v1.2.1.6")
                == "lower"
            ):
                cats = []
            else:
                cats = self.core.entities.getCategories(entity=curEntity, step=curDep)
        elif curEntity["type"] in ["shot", "sequence"]:
            cats = self.core.entities.getCategories(entity=curEntity, step=curDep)

        for c in cats:
            aItem = QListWidgetItem(c)
            self.lw_tasks.addItem(aItem)

        if self.lw_tasks.count() > 0:
            if restoreSelection and curTask in cats:
                self.lw_tasks.setCurrentRow(cats.index(curTask))
            else:
                self.lw_tasks.setCurrentRow(0)

        if not wasBlocked:
            self.lw_tasks.blockSignals(False)
            self.refreshScenefiles(restoreSelection=True)

    @err_catcher(name=__name__)
    def getCurrentEntity(self):
        return self.w_entities.getCurrentPage().getCurrentData()

    @err_catcher(name=__name__)
    def getCurrentEntities(self):
        return self.w_entities.getCurrentPage().getCurrentData(returnOne=False)

    @err_catcher(name=__name__)
    def getCurrentDepartment(self):
        item = self.lw_departments.currentItem()
        if not item:
            return

        return item.data(Qt.UserRole)

    @err_catcher(name=__name__)
    def getCurrentTask(self):
        item = self.lw_tasks.currentItem()
        if not item:
            return

        return item.text()

    @err_catcher(name=__name__)
    def getScenefileData(self):
        sceneData = []
        curEntity = self.getCurrentEntity()
        curDep = self.getCurrentDepartment()
        curTask = self.getCurrentTask()
        if curEntity and curDep and curTask:
            appfilter = []

            for pluginName in self.appFilters:
                if self.appFilters[pluginName]["show"]:
                    appfilter += self.appFilters[pluginName]["formats"]

            scenefiles = self.core.entities.getScenefiles(
                entity=curEntity, step=curDep, category=curTask, extensions=appfilter
            )

            for scenefile in scenefiles:
                data = self.core.getScenefileData(scenefile, preview=True)
                publicFile = (
                    len(self.projectBrowser.locations) > 1
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

                if not data.get("comment") or data["comment"] == "nocomment":
                    data["comment"] = ""

                if "date" not in data or type(data["date"]) != int:
                    cdate = self.core.getFileModificationDate(scenefile, asString=False)
                    data["date"] = cdate

                data["public"] = publicFile
                sceneData.append(data)

        return sceneData

    @err_catcher(name=__name__)
    def refreshScenefiles(self, reloadFiles=True, restoreSelection=False):
        if restoreSelection:
            file = self.getSelectedScenefile()

        if reloadFiles:
            self.scenefileData = self.getScenefileData()

        if self.b_sceneLayoutItems.isChecked():
            self.refreshScenefileItems(self.scenefileData)
        elif self.b_sceneLayoutList.isChecked():
            self.refreshScenefileList(self.scenefileData)

        if restoreSelection:
            self.selectScenefile(file)

    @err_catcher(name=__name__)
    def refreshScenefileItems(self, sceneData):
        self.clearScenefileItems()
        # if sceneData:
        for data in sorted(sceneData, key=lambda x: x.get("version", ""), reverse=True):
            self.addScenefileItem(data)
        # else:
        #     self.w_emptyScenes = QWidget()
        #     self.lo_emptyScenes = QHBoxLayout()
        #     self.w_emptyScenes.setLayout(self.lo_emptyScenes)
        #     self.l_emptyScenes = QLabel("< no scenefiles to show >")
        #     self.lo_emptyScenes.addStretch()
        #     self.lo_emptyScenes.addWidget(self.l_emptyScenes)
        #     self.lo_emptyScenes.addStretch()
        #     self.lo_scenefileItems.addWidget(self.w_emptyScenes)

        self.w_sceneItemsStretch = QWidget()
        self.lo_sceneItemsStretch = QVBoxLayout()
        self.lo_sceneItemsStretch.setContentsMargins(0, 0, 0, 0)
        self.w_sceneItemsStretch.setLayout(self.lo_sceneItemsStretch)
        self.lo_sceneItemsStretch.addStretch()
        self.lo_scenefileItems.addWidget(self.w_sceneItemsStretch)
        policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        policy.setVerticalStretch(10)
        self.w_sceneItemsStretch.setSizePolicy(policy)

    @err_catcher(name=__name__)
    def clearScenefileItems(self):
        self.sceneItemWidgets = []
        for idx in reversed(range(self.lo_scenefileItems.count())):
            item = self.lo_scenefileItems.takeAt(idx)
            w = item.widget()
            if w:
                w.setVisible(False)
                w.setParent(None)
                w.deleteLater()

    @err_catcher(name=__name__)
    def addScenefileItem(self, data):
        item = ScenefileItem(self, data)
        item.signalSelect.connect(self.itemSelected)
        item.signalReleased.connect(self.itemReleased)
        self.sceneItemWidgets.append(item)
        self.lo_scenefileItems.addWidget(item)

    @err_catcher(name=__name__)
    def itemSelected(self, item):
        if not item.isSelected():
            self.deselectItems(ignore=[item])

    @err_catcher(name=__name__)
    def itemReleased(self, item):
        self.deselectItems(ignore=[item])

    @err_catcher(name=__name__)
    def deselectItems(self, ignore=None):
        for item in self.sceneItemWidgets:
            if ignore and item in ignore:
                continue

            item.deselect()

    @err_catcher(name=__name__)
    def getSelectedScenefile(self):
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
    def refreshScenefileList(self, sceneData):
        twSorting = [
            self.tw_scenefiles.horizontalHeader().sortIndicatorSection(),
            self.tw_scenefiles.horizontalHeader().sortIndicatorOrder(),
        ]
        self.tw_scenefiles.setSortingEnabled(False)

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(
            [
                "",
                self.tableColumnLabels["Version"],
                self.tableColumnLabels["Comment"],
                self.tableColumnLabels["Date"],
                self.tableColumnLabels["User"],
            ]
        )
        # example filename: Body_mod_Modelling_v0002_details-added_rfr_.max
        # example filename: shot_0010_mod_main_v0002_details-added_rfr_.max

        for data in sceneData:
            row = []
            if pVersion == 2:
                item = QStandardItem(unicode("█", "utf-8"))
            else:
                item = QStandardItem("█")
            item.setFont(QFont("SansSerif", 100))
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            item.setData(data["filename"], Qt.UserRole)

            if data.get("icon", ""):
                item.setIcon(data["icon"])
            else:
                item.setForeground(data["color"])

            row.append(item)

            item = QStandardItem(data.get("version", ""))
            item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
            row.append(item)

            item = QStandardItem(data.get("comment", ""))
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

    @err_catcher(name=__name__)
    def departmentChanged(self, current=None, prev=None):
        self.refreshTasks(restoreSelection=True)

    @err_catcher(name=__name__)
    def taskChanged(self, current=None, prev=None):
        self.refreshScenefiles(restoreSelection=True)

    @err_catcher(name=__name__)
    def refreshEntityInfo(self):
        page = self.w_entities.getCurrentPage()
        if page.entityType == "asset":
            self.refreshAssetinfo()
        elif page.entityType in ["shot", "sequence"]:
            self.refreshShotinfo()

    @err_catcher(name=__name__)
    def refreshAssetinfo(self):
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

        curEntities = self.getCurrentEntities()
        self.gb_entityInfo.setTitle("Assetinfo")

        if curEntities:
            if len(curEntities) > 1:
                description = "Multiple assets selected"
                l_info = QLabel(description)
                self.lo_entityInfo.addWidget(l_info)
            else:
                curEntity = curEntities[0]
                if curEntity["type"] == "asset":
                    assetName = self.core.entities.getAssetNameFromPath(curEntity["paths"][0])
                    description = (
                        self.core.entities.getAssetDescription(assetName)
                        or "< no description >"
                    )

                    l_key = QLabel("Description:    ")
                    l_val = QLabel(description)
                    l_val.setWordWrap(True)
                    self.lo_entityInfo.addWidget(l_key, 0, 0)
                    self.lo_entityInfo.addWidget(l_val, 0, 1)

                    sp_info = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Fixed)
                    self.lo_entityInfo.addItem(sp_info, 0, 2)

                    pmap = self.core.entities.getEntityPreview(
                        curEntity, self.shotPrvXres, self.shotPrvYres
                    )
                    metadata = self.core.entities.getMetaData(curEntity)
                    if metadata:
                        idx = 1
                        for key in metadata:
                            if metadata[key]["show"]:
                                l_key = QLabel(key + ":    ")
                                l_val = QLabel(metadata[key]["value"])
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
            description = "No asset selected"
            l_info = QLabel(description)
            self.lo_entityInfo.addWidget(l_info)

        if pmap is None:
            pmap = self.emptypmapPrv

        self.l_entityPreview.setMinimumSize(pmap.width(), pmap.height())
        self.l_entityPreview.setPixmap(pmap)

    @err_catcher(name=__name__)
    def refreshShotinfo(self):
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

        curEntities = self.getCurrentEntities()
        self.gb_entityInfo.setTitle("Shotinfo")

        if curEntities:
            if len(curEntities) > 1:
                l_info = QLabel("Multiple shots selected")
                self.lo_entityInfo.addWidget(l_info)
            else:
                curEntity = curEntities[0]
                if curEntity["sequence"] and (not curEntity.get("shot") or (curEntity["shot"] == "_sequence")):
                    pass
                else:
                    startFrame = "?"
                    endFrame = "?"

                    shotRange = self.core.entities.getShotRange(curEntity)
                    if shotRange:
                        if shotRange[0] is not None:
                            startFrame = shotRange[0]

                        if shotRange[1] is not None:
                            endFrame = shotRange[1]

                    l_range1 = QLabel("Framerange:    ")
                    l_range2 = QLabel("%s - %s" % (startFrame, endFrame))
                    self.lo_entityInfo.addWidget(l_range1, 0, 0)
                    self.lo_entityInfo.addWidget(l_range2, 0, 1)

                sp_info = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Fixed)
                self.lo_entityInfo.addItem(sp_info, 0, 2)

                pmap = self.core.entities.getEntityPreview(
                    curEntity, self.shotPrvXres, self.shotPrvYres
                )
                metadata = self.core.entities.getMetaData(curEntity)
                if metadata:
                    idx = 1
                    for key in metadata:
                        if metadata[key]["show"]:
                            l_key = QLabel(key + ":    ")
                            l_val = QLabel(metadata[key]["value"])
                            l_val.setWordWrap(True)
                            self.lo_entityInfo.addWidget(l_key, idx, 0)
                            self.lo_entityInfo.addWidget(l_val, idx, 1)
                            idx += 1
        else:
            l_info = QLabel("No shot selected")
            self.lo_entityInfo.addWidget(l_info)

        if pmap is None:
            pmap = self.emptypmapPrv

        self.l_entityPreview.setMinimumSize(pmap.width(), pmap.height())
        self.l_entityPreview.setPixmap(pmap)

    @err_catcher(name=__name__)
    def rclEntityPreview(self, pos):
        rcmenu = QMenu(self)

        entity = self.getCurrentEntity()
        if not entity:
            return

        if entity["type"] == "asset":
            exp = QAction("Edit asset description...", self)
            exp.triggered.connect(self.editAsset)
            rcmenu.addAction(exp)

            copAct = QAction("Capture assetpreview", self)
            copAct.triggered.connect(lambda: self.captureEntityPreview(entity))
            rcmenu.addAction(copAct)

            copAct = QAction("Browse assetpreview...", self)
            copAct.triggered.connect(lambda: self.browseEntityPreview(entity))
            rcmenu.addAction(copAct)

            clipAct = QAction("Paste assetpreview from clipboard", self)
            clipAct.triggered.connect(
                lambda: self.pasteEntityPreviewFromClipboard(entity)
            )
            rcmenu.addAction(clipAct)

        elif entity["type"] == "shot":
            exp = QAction("Edit shot settings...", self)
            exp.triggered.connect(lambda: self.editShot(entity))
            rcmenu.addAction(exp)

            copAct = QAction("Capture shotpreview", self)
            copAct.triggered.connect(lambda: self.captureEntityPreview(entity))
            rcmenu.addAction(copAct)

            copAct = QAction("Browse shotpreview...", self)
            copAct.triggered.connect(lambda: self.browseEntityPreview(entity))
            rcmenu.addAction(copAct)

            clipAct = QAction("Paste shotpreview from clipboard", self)
            clipAct.triggered.connect(
                lambda: self.pasteEntityPreviewFromClipboard(entity)
            )
            rcmenu.addAction(clipAct)
        elif entity["type"] == "sequence":
            exp = QAction("Edit sequence settings...", self)
            exp.triggered.connect(lambda: self.editShot(entity))
            rcmenu.addAction(exp)

            copAct = QAction("Capture sequencepreview", self)
            copAct.triggered.connect(lambda: self.captureEntityPreview(entity))
            rcmenu.addAction(copAct)

            copAct = QAction("Browse sequencepreview...", self)
            copAct.triggered.connect(lambda: self.browseEntityPreview(entity))
            rcmenu.addAction(copAct)

            clipAct = QAction("Paste sequencepreview from clipboard", self)
            clipAct.triggered.connect(
                lambda: self.pasteEntityPreviewFromClipboard(entity)
            )
            rcmenu.addAction(clipAct)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def browseEntityPreview(self, entity):
        formats = "Image File (*.jpg *.png *.exr)"

        imgPath = QFileDialog.getOpenFileName(
            self, "Select preview-image", self.core.projectPath, formats
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
                warnStr = "Cannot read image: %s" % imgPath
                self.core.popup(warnStr)
                return

        self.core.entities.setEntityPreview(
            entity, previewImg, width=self.shotPrvXres, height=self.shotPrvYres
        )
        self.refreshEntityInfo()
        if self.core.getConfig("browser", "showEntityPreviews", config="user"):
            self.refreshUI()

    @err_catcher(name=__name__)
    def captureEntityPreview(self, entity):
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
    def pasteEntityPreviewFromClipboard(self, entity):
        pmap = self.core.media.getPixmapFromClipboard()
        if not pmap:
            self.core.popup("No image in clipboard.")
            return

        self.core.entities.setEntityPreview(
            entity, pmap, width=self.shotPrvXres, height=self.shotPrvYres
        )
        self.refreshEntityInfo()
        if self.core.getConfig("browser", "showEntityPreviews", config="user"):
            self.refreshUI()

    @err_catcher(name=__name__)
    def editEntity(self):
        entity = self.getCurrentEntity()
        if entity.get("type") == "asset":
            self.editAsset()
        elif entity.get("type") in ["shot", "sequence"]:
            self.editShot(entity)

    @err_catcher(name=__name__)
    def editAsset(self):
        assetData = self.getCurrentEntity()
        if not assetData:
            return

        assetName = self.core.entities.getAssetNameFromPath(assetData["asset_path"])
        description = self.core.entities.getAssetDescription(assetName) or ""

        descriptionDlg = PrismWidgets.EnterText()
        self.core.parentWindow(descriptionDlg)
        descriptionDlg.setWindowTitle("Assetinfo")
        descriptionDlg.l_info.setText("Description:")
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
    def editShot(self, shotData=None):
        self.w_entities.getCurrentPage().editShotDlg(shotData)

    @err_catcher(name=__name__)
    def setRecent(self):
        model = QStandardItemModel()

        model.setHorizontalHeaderLabels(
            [
                "",
                self.tableColumnLabels["Name"],
                self.tableColumnLabels["Department"],
                self.tableColumnLabels["Version"],
                self.tableColumnLabels["Comment"],
                self.tableColumnLabels["Date"],
                self.tableColumnLabels["User"],
                "Filepath",
            ]
        )
        # example filename: Body_mod_v0002_details-added_rfr_.max
        # example filename: shot_0010_mod_main_v0002_details-added_rfr_.max
        rSection = "recent_files_" + self.core.projectName
        recentfiles = self.core.getConfig(cat=rSection) or []

        for i in recentfiles:
            if not self.core.isStr(i):
                continue

            row = []
            fname = self.core.getScenefileData(i)

            if "type" not in fname:
                continue

            if os.path.exists(i):
                if pVersion == 2:
                    item = QStandardItem(unicode("█", "utf-8"))
                else:
                    item = QStandardItem("█")
                item.setFont(QFont("SansSerif", 100))
                item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
                item.setData(i, Qt.UserRole)

                icon = self.core.getIconForFileType(fname["extension"])
                if icon:
                    item.setIcon(icon)
                else:
                    colorVals = [128, 128, 128]
                    if fname["extension"] in self.core.appPlugin.sceneFormats:
                        colorVals = self.core.appPlugin.appColor
                    else:
                        for k in self.core.unloadedAppPlugins.values():
                            if fname["extension"] in k.sceneFormats:
                                colorVals = k.appColor

                    item.setForeground(QColor(colorVals[0], colorVals[1], colorVals[2]))

                row.append(item)
                if fname["type"] == "asset":
                    item = QStandardItem(fname["asset_path"])
                    item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
                    row.append(item)
                    item = QStandardItem(fname.get("department", ""))
                    item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
                    row.append(item)
                    item = QStandardItem(fname["version"])
                    item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
                    row.append(item)
                    if fname["comment"] == "nocomment":
                        item = QStandardItem("")
                    else:
                        item = QStandardItem(fname["comment"])
                    row.append(item)
                    cdate = datetime.datetime.fromtimestamp(os.path.getmtime(i))
                    cdate = cdate.replace(microsecond=0)
                    cdate = cdate.strftime("%d.%m.%y,  %H:%M:%S")
                    item = QStandardItem(str(cdate))
                    item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
                    item.setData(
                        QDateTime.fromString(cdate, "dd.MM.yy,  hh:mm:ss").addYears(
                            100
                        ),
                        0,
                    )
                    #   item.setToolTip(cdate)
                    row.append(item)
                    item = QStandardItem(fname["user"])
                    item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
                    row.append(item)
                elif fname["type"] == "shot":
                    item = QStandardItem(self.core.entities.getShotName(fname))
                    item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
                    row.append(item)
                    item = QStandardItem(fname.get("department", ""))
                    item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
                    row.append(item)
                    item = QStandardItem(fname["version"])
                    item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
                    row.append(item)
                    if fname.get("comment", "nocomment") == "nocomment":
                        item = QStandardItem("")
                    else:
                        item = QStandardItem(fname["comment"])
                    row.append(item)
                    cdate = datetime.datetime.fromtimestamp(os.path.getmtime(i))
                    cdate = cdate.replace(microsecond=0)
                    cdate = cdate.strftime("%d.%m.%y,  %H:%M:%S")
                    item = QStandardItem(str(cdate))
                    item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
                    item.setData(
                        QDateTime.fromString(cdate, "dd.MM.yy,  hh:mm:ss").addYears(
                            100
                        ),
                        0,
                    )
                    #   item.setToolTip(cdate)
                    row.append(item)
                    item = QStandardItem(fname["user"])
                    item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
                    row.append(item)
                else:
                    continue

                item = QStandardItem(i)
                item.setToolTip(i)
                row.append(item)

                model.appendRow(row)

        self.tw_recent.setModel(model)
        self.tw_recent.resizeColumnsToContents()
        self.tw_recent.horizontalHeader().setMinimumSectionSize(10)
        self.tw_recent.setColumnWidth(0, 20 * self.core.uiScaleFactor)
        #   self.tw_recent.setColumnWidth(2,40*self.core.uiScaleFactor)
        #   self.tw_recent.setColumnWidth(3,60*self.core.uiScaleFactor)
        #   self.tw_recent.setColumnWidth(6,50*self.core.uiScaleFactor)

        self.tw_recent.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)

    @err_catcher(name=__name__)
    def createTaskDlg(self):
        entity = self.getCurrentEntity()
        curDep = self.getCurrentDepartment()
        presets = self.core.entities.getDefaultTasksForDepartment(entity["type"], curDep) or []
        existingTasks = self.core.entities.getCategories(entity, step=curDep)
        presets = [p for p in presets if p not in existingTasks]

        self.newItem = ItemList.ItemList(core=self.core, entity=entity, mode="tasks")
        self.newItem.setModal(True)
        self.newItem.tw_steps.setColumnCount(1)
        self.newItem.tw_steps.setHorizontalHeaderLabels(["Department"])
        self.newItem.tw_steps.horizontalHeader().setVisible(False)
        self.core.parentWindow(self.newItem)
        self.newItem.e_tasks.setFocus()
        self.newItem.tw_steps.doubleClicked.connect(lambda x=None, b=self.newItem.buttonBox.buttons()[0]:self.newItem.buttonboxClicked(b))
        self.newItem.setWindowTitle("Add Tasks")

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

        self.core.callback(name="onTaskDlgOpen", args=[self, self.newItem])
        if not getattr(self.newItem, "allowShow", True):
            return False

        self.newItem.exec_()

    @err_catcher(name=__name__)
    def createTask(self, tasks):
        self.activateWindow()

        curEntity = self.getCurrentEntity()
        curDep = self.getCurrentDepartment()

        for task in tasks:
            self.core.entities.createCategory(
                entity=curEntity, step=curDep, category=task
            )

        self.refreshTasks()
        for i in range(self.lw_tasks.model().rowCount()):
            if self.lw_tasks.model().index(i, 0).data() == tasks[0]:
                self.lw_tasks.selectionModel().setCurrentIndex(
                    self.lw_tasks.model().index(i, 0),
                    QItemSelectionModel.ClearAndSelect,
                )

    @err_catcher(name=__name__)
    def createDepartmentDlg(self):
        entity = self.getCurrentEntity()
        basePath = self.core.getEntityPath(reqEntity="step", entity=entity)

        if entity.get("type", "") == "asset":
            deps = self.core.projects.getAssetDepartments()
        elif entity.get("type", "") in ["shot", "sequence"]:
            deps = self.core.projects.getShotDepartments()
        else:
            return

        validDeps = []
        for dep in deps:
            if not os.path.exists(os.path.join(basePath, dep["abbreviation"])):
                validDeps.append(dep)

        self.getStep(validDeps)

    @err_catcher(name=__name__)
    def copyToGlobal(self, localPath):
        dstPath = localPath.replace(self.core.localProjectPath, self.core.projectPath)

        if os.path.isdir(localPath):
            if os.path.exists(dstPath):
                for i in os.walk(dstPath):
                    if i[2] != []:
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

        else:
            if not os.path.exists(os.path.dirname(dstPath)):
                os.makedirs(os.path.dirname(dstPath))

            self.core.copySceneFile(localPath, dstPath)

            self.refreshScenefiles()

    @err_catcher(name=__name__)
    def editComment(self, filepath):
        data = self.core.getScenefileData(filepath)
        comment = data["comment"] if "comment" in data else ""

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
        newPath = self.core.entities.setComment(filepath, comment)

        self.refreshScenefiles()
        fileNameData = self.core.getScenefileData(newPath)
        self.navigate(data=fileNameData)

    @err_catcher(name=__name__)
    def editDescription(self, filepath):
        data = self.core.getScenefileData(filepath)
        description = data.get("description", "")

        descriptionDlg = PrismWidgets.EnterText()
        descriptionDlg.setModal(True)
        self.core.parentWindow(descriptionDlg, parent=self)
        descriptionDlg.setWindowTitle("Enter description")
        descriptionDlg.l_info.setText("Description:")
        descriptionDlg.te_text.setPlainText(description)
        descriptionDlg.te_text.selectAll()
        result = descriptionDlg.exec_()

        if not result:
            return

        description = descriptionDlg.te_text.toPlainText()
        self.core.entities.setDescription(filepath, description)
        self.refreshScenefiles()
        fileNameData = self.core.getScenefileData(filepath)
        self.navigate(data=fileNameData)

    @err_catcher(name=__name__)
    def sceneDragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def sceneDragMoveEvent(self, e):
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
    def sceneDragLeaveEvent(self, e):
        if self.b_sceneLayoutList.isChecked():
            self.tw_scenefiles.setStyleSheet("")
        elif self.b_sceneLayoutItems.isChecked():
            self.w_scenefileItems.setStyleSheet("")

    @err_catcher(name=__name__)
    def sceneDropEvent(self, e):
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
    def ingestScenefiles(self, entity, files):
        task = self.getCurrentTask()
        if not task:
            self.core.popup("No valid context is selected")
            return

        if getattr(self, "dlg_ingestSettings", None):
            self.dlg_ingestSettings.close()

        self.dlg_ingestSettings = IngestSettings(self, entity, files)
        self.dlg_ingestSettings.show()


class IngestSettings(QDialog):
    def __init__(self, browser, entity, files):
        super(IngestSettings, self).__init__()
        self.core = browser.core
        self.browser = browser
        self.entity = entity
        self.files = files
        self.setupUi()
        self.setVersionNext()

    @err_catcher(name=__name__)
    def setupUi(self):
        self.setWindowTitle("Ingest Scenefile")
        self.core.parentWindow(self, parent=self.browser)

        self.l_version = QLabel("Version:")
        self.sp_version = QSpinBox()
        self.sp_version.setValue(1)
        self.sp_version.setMinimum(1)
        self.sp_version.setMaximum(99999)
        self.sp_version.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sp_version.customContextMenuRequested.connect(self.onVersionRightClicked)
        self.l_comment = QLabel("Comment:")
        self.e_comment = QLineEdit()

        self.l_rename = QLabel("Rename files:")
        self.chb_rename = QCheckBox()
        self.chb_rename.setChecked(True)

        self.lo_main = QGridLayout()
        self.setLayout(self.lo_main)

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Ingest", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Cancel", QDialogButtonBox.RejectRole)

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
    def sizeHint(self):
        return QSize(300, 150)

    @err_catcher(name=__name__)
    def onVersionRightClicked(self, pos):
        rcmenu = QMenu(self)

        copAct = QAction("Next available version", self)
        copAct.triggered.connect(self.setVersionNext)
        rcmenu.addAction(copAct)

        exp = QAction("Detect version from filename", self)
        exp.triggered.connect(self.setVersionFromSource)
        rcmenu.addAction(exp)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def setVersionNext(self):
        department = self.browser.getCurrentDepartment()
        task = self.browser.getCurrentTask()
        version = self.core.entities.getHighestVersion(self.entity, department, task)
        versionNum = self.core.products.getIntVersionFromVersionName(version)
        self.sp_version.setValue(versionNum)

    @err_catcher(name=__name__)
    def setVersionFromSource(self):
        result = re.search(r"\d{%s}" % self.core.versionPadding, os.path.basename(self.files[0]))
        if not result:
            return

        versionNum = int(result.group())
        self.sp_version.setValue(versionNum)

    @err_catcher(name=__name__)
    def onButtonClicked(self, button):
        if button.text() == "Ingest":
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
                finishCallback=self.browser.refreshScenefiles,
                data=data,
                rename=self.chb_rename.isChecked(),
            )
            self.accept()
        elif button.text() == "Cancel":
            self.close()


class ScenefileItem(QWidget):

    signalSelect = Signal(object)
    signalReleased = Signal(object)

    def __init__(self, browser, data):
        super(ScenefileItem, self).__init__()
        self.core = browser.core
        self.browser = browser
        self.data = data
        self.state = "deselected"
        self.previewSize = [self.core.scenePreviewWidth, self.core.scenePreviewHeight]
        self.itemPreviewWidth = 120
        self.itemPreviewHeight = 69
        self.setupUi()
        self.refreshUi()

    def mouseReleaseEvent(self, event):
        super(ScenefileItem, self).mouseReleaseEvent(event)
        self.signalReleased.emit(self)
        event.accept()

    @err_catcher(name=__name__)
    def setupUi(self):
        self.setObjectName("texture")
        self.applyStyle(self.state)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.lo_main = QHBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.setSpacing(15)
        self.lo_main.setContentsMargins(0, 0, 0, 0)

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
        path = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "user.png")
        icon = self.core.media.getColoredIcon(path)
        self.w_user = QWidget()
        self.lo_userIcon = QHBoxLayout(self.w_user)
        self.lo_userIcon.setContentsMargins(0, 0, 0, 0)
        self.l_userIcon = QLabel()
        self.l_userIcon.setPixmap(icon.pixmap(15, 15))
        self.l_user = QLabel()
        self.l_user.setAlignment(Qt.AlignRight)
        self.lo_userIcon.addStretch()
        self.lo_userIcon.addWidget(self.l_userIcon)
        self.lo_userIcon.addWidget(self.l_user)

        path = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "date.png")
        icon = self.core.media.getColoredIcon(path)
        self.w_date = QWidget()
        self.lo_dateIcon = QHBoxLayout(self.w_date)
        self.lo_dateIcon.setContentsMargins(0, 0, 0, 0)
        self.l_dateIcon = QLabel()
        self.l_dateIcon.setPixmap(icon.pixmap(15, 15))
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
        self.lo_main.addStretch()
        self.locationLabels = {}
        if len(self.browser.projectBrowser.locations) > 1:
            self.spacer7 = QSpacerItem(0, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.spacer8 = QSpacerItem(0, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.lo_location = QVBoxLayout()
            self.lo_location.addItem(self.spacer7)

            for location in self.browser.projectBrowser.locations:
                l_loc = QLabel()
                l_loc.setToolTip("Version exists in %s" % location["name"])
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
    def refreshUi(self):
        version = self.getVersion()
        descr = self.getDescription()
        comment = self.getComment()
        date = self.getDate()
        user = self.getUser()
        icon = self.getIcon()

        self.refreshPreview()
        self.l_version.setText(version)
        self.setIcon(icon)
        self.l_comment.setText(comment)
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

                elif loc.get("name") in self.data.get("locations", []):
                    self.locationLabels[loc["name"]].setHidden(False)

    @err_catcher(name=__name__)
    def setIcon(self, icon):
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
    def refreshPreview(self):
        ppixmap = self.getPreviewImage()
        ppixmap = self.core.media.scalePixmap(
            ppixmap, self.itemPreviewWidth, self.itemPreviewHeight, fitIntoBounds=False, crop=True
        )
        self.l_preview.setPixmap(ppixmap)

    @err_catcher(name=__name__)
    def getPreviewImage(self):
        if self.data.get("preview", ""):
            pixmap = self.core.media.getPixmapFromPath(self.data.get("preview", ""))
        else:
            pixmap = QPixmap(300, 169)
            pixmap.fill(Qt.black)

        return pixmap

    @err_catcher(name=__name__)
    def getVersion(self):
        version = self.data.get("version", "")
        return version

    @err_catcher(name=__name__)
    def getComment(self):
        comment = self.data.get("comment", "")
        return comment

    @err_catcher(name=__name__)
    def getDescription(self):
        description = self.data.get("description", "")
        return description

    @err_catcher(name=__name__)
    def getDate(self):
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
    def getUser(self):
        user = self.data.get("username", "")
        if user:
            return user

        user = self.data.get("user", "")
        return user

    @err_catcher(name=__name__)
    def getIcon(self):
        if self.data.get("icon", ""):
            return self.data["icon"]
        else:
            return self.data["color"]

    @err_catcher(name=__name__)
    def applyStyle(self, styleType):
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
    def mousePressEvent(self, event):
        self.select()

    @err_catcher(name=__name__)
    def enterEvent(self, event):
        if self.isSelected():
            self.applyStyle("hoverSelected")
        else:
            self.applyStyle("hover")

    @err_catcher(name=__name__)
    def leaveEvent(self, event):
        self.applyStyle(self.state)

    @err_catcher(name=__name__)
    def mouseDoubleClickEvent(self, event):
        self.browser.exeFile(self.data["filename"])

    @err_catcher(name=__name__)
    def select(self):
        wasSelected = self.isSelected()
        self.signalSelect.emit(self)
        if not wasSelected:
            self.state = "selected"
            self.applyStyle(self.state)
            self.setFocus()

    @err_catcher(name=__name__)
    def deselect(self):
        if self.state != "deselected":
            self.state = "deselected"
            self.applyStyle(self.state)

    @err_catcher(name=__name__)
    def isSelected(self):
        return self.state == "selected"

    @err_catcher(name=__name__)
    def rightClicked(self, pos):
        self.browser.openScenefileContextMenu(self.data["filename"])

    @err_catcher(name=__name__)
    def previewRightClicked(self, pos):
        rcmenu = QMenu(self.browser)

        copAct = QAction("Capture preview", self.browser)
        copAct.triggered.connect(lambda: self.captureScenePreview(self.data))

        exp = QAction("Browse preview...", self.browser)
        exp.triggered.connect(self.browseScenePreview)
        rcmenu.addAction(exp)

        rcmenu.addAction(copAct)
        clipAct = QAction("Paste preview from clipboard", self.browser)
        clipAct.triggered.connect(
            lambda: self.pasteScenePreviewFromClipboard(self.data)
        )
        rcmenu.addAction(clipAct)

        prvAct = QAction("Set as %spreview" % self.data.get("type", ""), self)
        prvAct.triggered.connect(self.setPreview)
        rcmenu.addAction(prvAct)
        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def setPreview(self):
        pm = self.getPreviewImage()
        self.core.entities.setEntityPreview(self.data, pm)
        self.browser.refreshEntityInfo()

    @err_catcher(name=__name__)
    def browseScenePreview(self):
        formats = "Image File (*.jpg *.png *.exr)"

        imgPath = QFileDialog.getOpenFileName(
            self, "Select preview-image", self.core.projectPath, formats
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
                warnStr = "Cannot read image: %s" % imgPath
                self.core.popup(warnStr)
                return

            pmsmall = self.core.media.scalePixmap(
                pm, self.previewSize[0], self.previewSize[1], fitIntoBounds=False, crop=True
            )

        self.core.entities.setScenePreview(self.data["filename"], pmsmall)
        self.data.update(self.core.entities.getScenefileData(
            self.data["filename"], preview=True
        ))
        self.refreshPreview()

    @err_catcher(name=__name__)
    def captureScenePreview(self, entity):
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
            self.data.update(self.core.entities.getScenefileData(
                self.data["filename"], preview=True
            ))
            self.refreshPreview()

    @err_catcher(name=__name__)
    def pasteScenePreviewFromClipboard(self, pos):
        pmap = self.core.media.getPixmapFromClipboard()
        if not pmap:
            self.core.popup("No image in clipboard.")
            return

        pmap = self.core.media.scalePixmap(
            pmap, self.previewSize[0], self.previewSize[1], fitIntoBounds=False, crop=True
        )
        self.core.entities.setScenePreview(self.data["filename"], pmap)
        self.data.update(self.core.entities.getScenefileData(
            self.data["filename"], preview=True
        ))
        self.refreshPreview()


class DateDelegate(QStyledItemDelegate):
    def displayText(self, value, locale):
        return self.core.getFormattedDate(value)
