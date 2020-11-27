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
import shutil
import time
import platform
import imp
import subprocess
import logging
import traceback
import copy
from collections import OrderedDict

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2

prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

if __name__ == "__main__":
    sys.path.append(os.path.join(prismRoot, "Scripts"))
    import PrismCore

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *
    psVersion = 1

if platform.system() == "Windows":
    if pVersion == 3:
        import winreg as _winreg
    elif pVersion == 2:
        import _winreg

uiPath = os.path.join(os.path.dirname(__file__), "UserInterfaces")
if uiPath not in sys.path:
    sys.path.append(uiPath)

for i in [
    "ProjectBrowser_ui",
    "ProjectBrowser_ui_ps2",
    "CreateItem",
    "CreateItem_ui",
    "CreateItem_ui_ps2",
]:
    try:
        del sys.modules[i]
    except:
        pass

if psVersion == 1:
    import ProjectBrowser_ui
else:
    import ProjectBrowser_ui_ps2 as ProjectBrowser_ui


try:
    import CreateItem
except:
    modPath = imp.find_module("CreateItem")[1]
    if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
        os.remove(modPath)
    import CreateItem

try:
    import EnterText
except:
    modPath = imp.find_module("EnterText")[1]
    if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
        os.remove(modPath)
    import EnterText

from PrismUtils.Decorators import err_catcher

logger = logging.getLogger(__name__)


class ProjectBrowser(QMainWindow, ProjectBrowser_ui.Ui_mw_ProjectBrowser):
    def __init__(self, core):
        QMainWindow.__init__(self)
        self.setupUi(self)
        self.core = core

        logger.debug("Initializing Project Browser")

        self.core.parentWindow(self)

        self.setWindowTitle("Prism %s - Project Browser - %s" %(self.core.version, self.core.projectName))
        self.sceneBasePath = self.core.getScenePath()
        self.aBasePath = self.core.getAssetPath()
        self.sBasePath = self.core.getShotPath()

        self.aExpanded = []
        self.sExpanded = []
        self.filteredAssets = []
        self.copiedFile = None
        self.copiedsFile = None

        self.dclick = False
        self.adclick = False
        self.sdclick = False

        self.shotPrvXres = 250
        self.shotPrvYres = 141

        self.curAsset = None
        self.curaStep = None
        self.curaCat = None

        self.cursShots = None
        self.cursStep = None
        self.cursCat = None

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
            "Step": "Step",
        }
        self.tw_aHierarchy.setHeaderLabels(["Assets"])

        self.curRTask = ""
        self.curRVersion = ""
        self.curRLayer = ""

        self.b_refresh.setEnabled(True)
        self.b_compareRV.setEnabled(False)
        self.b_combineVersions.setEnabled(False)
        self.b_clearRV.setEnabled(False)

        self.chb_autoUpdate.setToolTip(
            "Automatically refresh tasks, versions and renderings, when the current asset/shot changes."
        )
        self.b_refresh.setToolTip("Refresh tasks, versions and renderings.")
        self.b_compareRV.setToolTip(
            "Click to compare media files in layout view in RV.\nRight-Click for additional compare modes."
        )
        self.b_combineVersions.setToolTip(
            "Click to combine media files to one video file.\nRight-Click for additional combine modes."
        )

        self.renderResX = 300
        self.renderResY = 169

        self.renderRefreshEnabled = True
        self.compareStates = []
        self.mediaPlaybacks = {
            "shots": {
                "name": "shots",
                "sl_preview": self.sl_preview,
                "prevCurImg": 0,
                "l_info": self.l_info,
                "l_date": self.l_date,
                "l_preview": self.l_preview,
                "openRV": False,
                "getMediaBase": self.getShotMediaPath,
                "getMediaBaseFolder": self.core.mediaProducts.getMediaProductPath,
            }
        }

        self.savedPalette = QPalette()
        self.savedPalette.setColor(QPalette.Button, QColor(200, 100, 0))
        self.savedPalette.setColor(QPalette.ButtonText, QColor(255, 255, 255))

        self.publicColor = QColor(150, 200, 220)
        self.closeParm = "closeafterload"
        getattr(
            self.core.appPlugin, "projectBrower_loadLibs", lambda x: self.loadLibs()
        )(self)
        self.emptypmap = self.createPMap(self.renderResX, self.renderResY)
        self.emptypmapPrv = self.createPMap(self.shotPrvXres, self.shotPrvYres)
        self.core.entities.refreshOmittedEntities()
        self.loadLayout()
        self.setRecent()
        self.getRVpath()
        self.getDJVpath()
        self.getVLCpath()
        self.connectEvents()
        self.core.callback(
            name="onProjectBrowserStartup", types=["curApp", "custom"], args=[self]
        )
        self.oiio = self.core.media.getOIIO()
        self.refreshAHierarchy(load=True)
        self.refreshShots()
        self.navigateToCurrent()
        self.updateTasks()

        self.l_preview.setAcceptDrops(True)
    #   self.tw_sFiles.setStyleSheet("QTableView,QListView,QHeaderView {color: rgb(199,199,199);background-color: rgb(71,71,71);selection-color: rgb(0,0,0);selection-background-color: rgb(242,138,0);}")

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.tw_aHierarchy.mousePrEvent = self.tw_aHierarchy.mousePressEvent
        self.tw_aHierarchy.mousePressEvent = lambda x: self.mouseClickEvent(x, "ah")
        self.tw_aHierarchy.mouseClickEvent = self.tw_aHierarchy.mouseReleaseEvent
        self.tw_aHierarchy.mouseReleaseEvent = lambda x: self.mouseClickEvent(x, "ah")
        self.tw_aHierarchy.mouseDClick = self.tw_aHierarchy.mouseDoubleClickEvent
        self.tw_aHierarchy.mouseDoubleClickEvent = lambda x: self.mousedb(
            x, "ah", self.tw_aHierarchy
        )
        self.tw_aHierarchy.enterEvent = lambda x: self.mouseEnter(x, "assets")
        self.tw_aHierarchy.origKeyPressEvent = self.tw_aHierarchy.keyPressEvent
        self.tw_aHierarchy.keyPressEvent = lambda x: self.keyPressed(x, "assets")
        self.e_assetSearch.origKeyPressEvent = self.e_assetSearch.keyPressEvent
        self.e_assetSearch.keyPressEvent = lambda x: self.keyPressed(x, "assetSearch")
        self.lw_aPipeline.mouseClickEvent = self.lw_aPipeline.mouseReleaseEvent
        self.lw_aPipeline.mouseReleaseEvent = lambda x: self.mouseClickEvent(x, "ap")
        self.lw_aPipeline.mouseDClick = self.lw_aPipeline.mouseDoubleClickEvent
        self.lw_aPipeline.mouseDoubleClickEvent = lambda x: self.mousedb(
            x, "ap", self.lw_aPipeline
        )
        self.lw_aCategory.mouseClickEvent = self.lw_aCategory.mouseReleaseEvent
        self.lw_aCategory.mouseReleaseEvent = lambda x: self.mouseClickEvent(x, "ac")
        self.lw_aCategory.mouseDClick = self.lw_aCategory.mouseDoubleClickEvent
        self.lw_aCategory.mouseDoubleClickEvent = lambda x: self.mousedb(
            x, "ac", self.lw_aCategory
        )
        self.tw_aFiles.mouseClickEvent = self.tw_aFiles.mouseReleaseEvent
        self.tw_aFiles.mouseReleaseEvent = lambda x: self.mouseClickEvent(x, "af")

        self.tw_sShot.mousePrEvent = self.tw_sShot.mousePressEvent
        self.tw_sShot.mousePressEvent = lambda x: self.mouseClickEvent(x, "ss")
        self.tw_sShot.mouseClickEvent = self.tw_sShot.mouseReleaseEvent
        self.tw_sShot.mouseReleaseEvent = lambda x: self.mouseClickEvent(x, "ss")
        self.tw_sShot.mouseDClick = self.tw_sShot.mouseDoubleClickEvent
        self.tw_sShot.mouseDoubleClickEvent = lambda x: self.mousedb(
            x, "ss", self.tw_sShot
        )
        self.tw_sShot.enterEvent = lambda x: self.mouseEnter(x, "shots")
        self.tw_sShot.origKeyPressEvent = self.tw_sShot.keyPressEvent
        self.tw_sShot.keyPressEvent = lambda x: self.keyPressed(x, "shots")
        self.e_shotSearch.origKeyPressEvent = self.e_shotSearch.keyPressEvent
        self.e_shotSearch.keyPressEvent = lambda x: self.keyPressed(x, "shotSearch")
        self.lw_sPipeline.mouseClickEvent = self.lw_sPipeline.mouseReleaseEvent
        self.lw_sPipeline.mouseReleaseEvent = lambda x: self.mouseClickEvent(x, "sp")
        self.lw_sPipeline.mouseDClick = self.lw_sPipeline.mouseDoubleClickEvent
        self.lw_sPipeline.mouseDoubleClickEvent = lambda x: self.mousedb(
            x, "sp", self.lw_sPipeline
        )
        self.lw_sCategory.mouseClickEvent = self.lw_sCategory.mouseReleaseEvent
        self.lw_sCategory.mouseReleaseEvent = lambda x: self.mouseClickEvent(x, "sc")
        self.lw_sCategory.mouseDClick = self.lw_sCategory.mouseDoubleClickEvent
        self.lw_sCategory.mouseDoubleClickEvent = lambda x: self.mousedb(
            x, "sc", self.lw_sCategory
        )
        self.tw_sFiles.mouseClickEvent = self.tw_sFiles.mouseReleaseEvent
        self.tw_sFiles.mouseReleaseEvent = lambda x: self.mouseClickEvent(x, "sf")

        self.tw_recent.mouseClickEvent = self.tw_recent.mouseReleaseEvent
        self.tw_recent.mouseReleaseEvent = lambda x: self.mouseClickEvent(x, "r")

        self.tw_aHierarchy.currentItemChanged.connect(lambda x, y: self.Assetclicked(x))
        self.tw_aHierarchy.itemExpanded.connect(self.hItemExpanded)
        self.tw_aHierarchy.itemCollapsed.connect(self.hItemCollapsed)
        self.tw_aHierarchy.customContextMenuRequested.connect(
            lambda x: self.rclCat("ah", x)
        )
        self.b_assetSearch.toggled.connect(lambda x: self.searchClicked(x, "assets"))
        self.e_assetSearch.textChanged.connect(lambda x: self.refreshAHierarchy())
        self.lw_aPipeline.currentItemChanged.connect(self.aPipelineclicked)
        self.lw_aPipeline.customContextMenuRequested.connect(
            lambda x: self.rclCat("ap", x)
        )
        self.lw_aCategory.currentItemChanged.connect(self.aCatclicked)
        self.lw_aCategory.customContextMenuRequested.connect(
            lambda x: self.rclCat("ac", x)
        )
        self.tw_aFiles.customContextMenuRequested.connect(
            lambda x: self.rclFile("a", x)
        )
        self.tw_aFiles.doubleClicked.connect(self.sceneDoubleClicked)
        self.tw_aFiles.setMouseTracking(True)
        self.tw_aFiles.mouseMoveEvent = lambda x: self.tableMoveEvent(x, "af")
        self.tw_aFiles.leaveEvent = lambda x: self.tableLeaveEvent(x, "af")
        self.tw_aFiles.focusOutEvent = lambda x: self.tableFocusOutEvent(x, "af")

        self.gb_assetInfo.mouseDoubleClickEvent = lambda x: self.editAsset(
            self.curAsset
        )
        self.gb_assetInfo.customContextMenuRequested.connect(
            lambda x: self.rclEntityPreview(x, "asset")
        )
        self.l_assetPreview.customContextMenuRequested.connect(
            lambda x: self.rclEntityPreview(x, "asset")
        )

        self.tw_sShot.currentItemChanged.connect(lambda x, y: self.sShotclicked(x))
        self.tw_sShot.itemExpanded.connect(self.sItemCollapsed)
        self.tw_sShot.itemCollapsed.connect(self.sItemCollapsed)
        self.tw_sShot.customContextMenuRequested.connect(lambda x: self.rclCat("ss", x))
        self.b_shotSearch.toggled.connect(lambda x: self.searchClicked(x, "shots"))
        self.e_shotSearch.textChanged.connect(lambda x: self.refreshShots())
        self.lw_sPipeline.customContextMenuRequested.connect(
            lambda x: self.rclCat("sp", x)
        )
        self.lw_sPipeline.currentItemChanged.connect(self.sPipelineclicked)
        self.lw_sCategory.currentItemChanged.connect(self.sCatclicked)
        self.lw_sCategory.customContextMenuRequested.connect(
            lambda x: self.rclCat("sc", x)
        )
        self.tw_sFiles.customContextMenuRequested.connect(
            lambda x: self.rclFile("sf", x)
        )
        self.tw_sFiles.doubleClicked.connect(self.sceneDoubleClicked)
        self.tw_sFiles.setMouseTracking(True)
        self.tw_sFiles.mouseMoveEvent = lambda x: self.tableMoveEvent(x, "sf")
        self.tw_sFiles.leaveEvent = lambda x: self.tableLeaveEvent(x, "sf")
        self.tw_sFiles.focusOutEvent = lambda x: self.tableFocusOutEvent(x, "sf")

        self.gb_shotInfo.mouseDoubleClickEvent = lambda x: self.editShot(
            self.cursShots
        )
        self.gb_shotInfo.customContextMenuRequested.connect(
            lambda x: self.rclEntityPreview(x, "shot")
        )
        self.l_shotPreview.customContextMenuRequested.connect(
            lambda x: self.rclEntityPreview(x, "shot")
        )

        self.actionPrismSettings.triggered.connect(self.core.prismSettings)
        self.actionStateManager.triggered.connect(self.core.stateManager)
        self.actionOpenOnStart.toggled.connect(self.triggerOpen)
        self.actionCheckForUpdates.toggled.connect(self.triggerUpdates)
        self.actionCheckForShotFrameRange.toggled.connect(self.triggerFrameranges)
        self.actionCloseAfterLoad.toggled.connect(self.triggerCloseLoad)
        self.actionAutoplay.toggled.connect(self.triggerAutoplay)
        self.actionAssets.toggled.connect(self.triggerAssets)
        self.actionShots.toggled.connect(self.triggerShots)
        self.actionRecent.toggled.connect(self.triggerRecent)
        self.actionRenderings.toggled.connect(self.triggerRenderings)
        self.tbw_browser.currentChanged.connect(self.tabChanged)
        self.tw_recent.customContextMenuRequested.connect(
            lambda x: self.rclFile("r", x)
        )
        self.tw_recent.doubleClicked.connect(self.sceneDoubleClicked)
        self.tw_recent.setMouseTracking(True)
        self.tw_recent.mouseMoveEvent = lambda x: self.tableMoveEvent(x, "r")
        self.tw_recent.leaveEvent = lambda x: self.tableLeaveEvent(x, "r")
        self.tw_recent.focusOutEvent = lambda x: self.tableFocusOutEvent(x, "r")

        for i in self.appFilters:
            self.appFilters[i]["assetChb"].stateChanged.connect(self.refreshAFile)
            self.appFilters[i]["shotChb"].stateChanged.connect(self.refreshSFile)

        self.chb_autoUpdate.stateChanged.connect(self.updateChanged)
        self.b_refresh.clicked.connect(self.refreshRender)

        self.l_preview.clickEvent = self.l_preview.mouseReleaseEvent
        self.l_preview.mouseReleaseEvent = self.previewClk
        self.l_preview.dclickEvent = self.l_preview.mouseDoubleClickEvent
        self.l_preview.mouseDoubleClickEvent = self.previewDclk
        self.l_preview.customContextMenuRequested.connect(self.rclPreview)
        self.l_preview.mouseMoveEvent = lambda x: self.mouseDrag(x, self.l_preview)

        self.lw_task.itemSelectionChanged.connect(self.taskClicked)
        self.lw_version.itemSelectionChanged.connect(self.versionClicked)
        self.lw_version.mmEvent = self.lw_version.mouseMoveEvent
        self.lw_version.mouseMoveEvent = lambda x: self.mouseDrag(x, self.lw_version)
        self.lw_version.itemDoubleClicked.connect(self.showVersionInfo)
        self.cb_layer.currentIndexChanged.connect(self.layerChanged)
        self.cb_layer.mmEvent = self.cb_layer.mouseMoveEvent
        self.cb_layer.mouseMoveEvent = lambda x: self.mouseDrag(x, self.cb_layer)
        self.b_addRV.clicked.connect(self.addCompare)
        self.b_compareRV.clicked.connect(self.compare)
        self.b_compareRV.customContextMenuRequested.connect(self.compareOptions)
        self.b_combineVersions.clicked.connect(self.combineVersions)
        self.b_combineVersions.customContextMenuRequested.connect(self.combineOptions)
        self.b_clearRV.clicked.connect(self.clearCompare)
        self.sl_preview.valueChanged.connect(self.sliderChanged)
        self.sl_preview.sliderPressed.connect(self.sliderClk)
        self.sl_preview.sliderReleased.connect(self.sliderRls)
        self.sl_preview.origMousePressEvent = self.sl_preview.mousePressEvent
        self.sl_preview.mousePressEvent = self.sliderDrag
        self.lw_task.customContextMenuRequested.connect(
            lambda x: self.rclList(x, self.lw_task)
        )
        self.lw_version.customContextMenuRequested.connect(
            lambda x: self.rclList(x, self.lw_version)
        )
        self.lw_compare.customContextMenuRequested.connect(self.rclCompare)

    def enterEvent(self, event):
        try:
            QApplication.restoreOverrideCursor()
        except:
            pass

    @err_catcher(name=__name__)
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_F5:
            self.refreshUI()

    @err_catcher(name=__name__)
    def loadLayout(self):
        self.helpMenu = QMenu("Help", self)

        self.actionWebsite = QAction("Visit website", self)
        self.actionWebsite.triggered.connect(lambda: self.core.openWebsite("home"))
        self.helpMenu.addAction(self.actionWebsite)

        self.actionWebsite = QAction("Tutorials", self)
        self.actionWebsite.triggered.connect(lambda: self.core.openWebsite("tutorials"))
        self.helpMenu.addAction(self.actionWebsite)

        self.actionWebsite = QAction("Documentation", self)
        self.actionWebsite.triggered.connect(
            lambda: self.core.openWebsite("documentation")
        )
        self.helpMenu.addAction(self.actionWebsite)

        self.actionCheckVersion = QAction("Check for Prism updates", self)
        self.actionCheckVersion.triggered.connect(self.core.updater.checkForUpdates)
        self.helpMenu.addAction(self.actionCheckVersion)

        self.actionAbout = QAction("About...", self)
        self.actionAbout.triggered.connect(self.core.showAbout)
        self.helpMenu.addAction(self.actionAbout)

        self.menubar.addMenu(self.helpMenu)

        self.actionSendFeedback = QAction("Send feedback...", self)
        self.actionSendFeedback.triggered.connect(self.core.sendFeedback)
        self.menubar.addAction(self.actionSendFeedback)

        self.w_menuCorner = QWidget()
        self.b_refreshTabs = QPushButton()
        self.lo_corner = QHBoxLayout()
        self.w_menuCorner.setLayout(self.lo_corner)
        self.lo_corner.addWidget(self.b_refreshTabs)
        self.lo_corner.setContentsMargins(0, 0, 10, 0)
        self.b_refreshTabs.setIcon(QIcon(os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "refresh.png")))
        self.b_refreshTabs.clicked.connect(self.refreshUI)
        self.b_refreshTabs.setIconSize(QSize(20, 20))
        self.b_refreshTabs.setToolTip("Refresh")
        self.b_refreshTabs.setStyleSheet("QWidget{padding: 0; border-width: 0px;} QWidget:hover{border-width: 1px; }")
        self.b_refreshTabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.b_refreshTabs.customContextMenuRequested.connect(lambda x: self.showContextMenu("refresh"))

        searchIcon = QIcon(os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "search.png"))
        self.b_assetSearch.setIcon(searchIcon)
        self.b_shotSearch.setIcon(searchIcon)
        self.b_assetSearch.setStyleSheet("QWidget{padding: 0; border-width: 0px;} QWidget:hover{border-width: 1px; }")
        self.b_shotSearch.setStyleSheet("QWidget{padding: 0; border-width: 0px;} QWidget:hover{border-width: 1px; }")

        if platform.system() == "Darwin":
            parentWidget = self.tbw_browser
        else:
            parentWidget = self.menubar

        parentWidget.setCornerWidget(self.w_menuCorner)

        self.appFilters = {}

        for i in self.core.getPluginNames():
            if len(self.core.getPluginData(i, "sceneFormats")) == 0:
                continue

            chb_aApp = QCheckBox(i)
            chb_sApp = QCheckBox(i)
            chb_aApp.setChecked(True)
            chb_sApp.setChecked(True)
            self.w_aShowFormats.layout().addWidget(chb_aApp)
            self.w_sShowFormats.layout().addWidget(chb_sApp)
            setattr(
                self,
                "chb_aShow%s" % self.core.getPluginData(i, "appShortName"),
                chb_aApp,
            )
            setattr(
                self,
                "chb_sShow%s" % self.core.getPluginData(i, "appShortName"),
                chb_sApp,
            )
            self.appFilters[i] = {
                "assetChb": chb_aApp,
                "shotChb": chb_sApp,
                "shortName": self.core.getPluginData(i, "appShortName"),
                "formats": self.core.getPluginData(i, "sceneFormats"),
            }

        # custom checkbox
        chb_aApp = QCheckBox("Other")
        chb_sApp = QCheckBox("Other")
        chb_aApp.setChecked(True)
        chb_sApp.setChecked(True)
        self.w_aShowFormats.layout().addWidget(chb_aApp)
        self.w_sShowFormats.layout().addWidget(chb_sApp)
        setattr(self, "chb_aShowOther", chb_aApp)
        setattr(self, "chb_sShowOther", chb_sApp)
        self.appFilters["other"] = {
            "assetChb": chb_aApp,
            "shotChb": chb_sApp,
            "shortName": "Other",
            "formats": "*",
        }

        cData = self.core.getConfig()
        glbData = cData.get("globals", {})
        brsData = cData.get("browser", {})

        if "showonstartup" in glbData:
            self.actionOpenOnStart.setChecked(glbData["showonstartup"])

        if "check_import_versions" in glbData:
            self.actionCheckForUpdates.setChecked(glbData["check_import_versions"])

        if "checkframeranges" in glbData:
            self.actionCheckForShotFrameRange.setChecked(glbData["checkframeranges"])

        if self.closeParm in brsData:
            self.actionCloseAfterLoad.setChecked(brsData[self.closeParm])

        if "autoplaypreview" in brsData:
            state = brsData["autoplaypreview"]
            self.actionAutoplay.setChecked(state)

        try:
            self.menuRecentProjects.setToolTipsVisible(True)
        except:
            pass

        recentProjects = self.core.projects.getRecentProjects()
        for project in recentProjects:
            rpAct = QAction(project["name"], self)
            rpAct.setToolTip(project["configPath"])

            rpAct.triggered.connect(lambda y=None, x=project["configPath"]: self.core.changeProject(x))
            self.menuRecentProjects.addAction(rpAct)

        if self.menuRecentProjects.isEmpty():
            self.menuRecentProjects.setEnabled(False)

        for i in self.core.prjManagers.values():
            prjMngMenu = i.pbBrowser_getMenu(self)
            if prjMngMenu is not None:
                self.menuTools.addSeparator()
                self.menuTools.addMenu(prjMngMenu)

        self.tabOrder = {
            "Assets": {"order": 0, "showRenderings": True},
            "Shots": {"order": 1, "showRenderings": True},
            "Recent": {"order": 2, "showRenderings": False},
        }
        if (
            "assetsOrder" in brsData
            and "shotsOrder" in brsData
            and "filesOrder" in brsData
            and "recentOrder" in brsData
        ):
            for i in ["assetsOrder", "shotsOrder", "filesOrder", "recentOrder"]:
                if brsData[i] >= len(self.tabOrder):
                    brsData[i] = -1

            self.tabOrder["Assets"]["order"] = brsData["assetsOrder"]
            self.tabOrder["Shots"]["order"] = brsData["shotsOrder"]
            self.tabOrder["Recent"]["order"] = brsData["recentOrder"]

        self.tbw_browser.insertTab(
            self.tabOrder["Assets"]["order"], self.t_assets, self.tabLabels["Assets"]
        )
        self.tbw_browser.insertTab(
            self.tabOrder["Shots"]["order"], self.t_shots, self.tabLabels["Shots"]
        )
        self.tbw_browser.insertTab(
            self.tabOrder["Recent"]["order"], self.t_recent, self.tabLabels["Recent"]
        )

        self.t_assets.setProperty("tabType", "Assets")
        self.t_shots.setProperty("tabType", "Shots")
        self.t_recent.setProperty("tabType", "Recent")

        if brsData.get("assetsVisible", True) is False:
            self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_assets))
            self.actionAssets.setChecked(False)

        if brsData.get("shotsVisible", True) is False:
            self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_shots))
            self.actionShots.setChecked(False)

        if brsData.get("recentVisible", True) is False:
            self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_recent))
            self.actionRecent.setChecked(False)

        if brsData.get("renderVisible", True) is False:
            self.actionRenderings.setChecked(False)
            self.gb_renderings.setVisible(False)

        for i in self.appFilters:
            sa = self.appFilters[i]["shortName"]
            if "show%sAssets" % sa in brsData:
                chbName = "chb_aShow%s" % sa
                getattr(self, chbName).setChecked(brsData["show%sAssets" % sa])

            if "show%sShots" % sa in brsData:
                chbName = "chb_sShow%s" % sa
                getattr(self, chbName).setChecked(brsData["show%sShots" % sa])

        assetSort = brsData.get("assetSorting", [1, 1])
        self.tw_aFiles.sortByColumn(assetSort[0], Qt.SortOrder(assetSort[1]))

        shotSort = brsData.get("shotSorting", [1, 1])
        self.tw_sFiles.sortByColumn(shotSort[0], Qt.SortOrder(shotSort[1]))

        self.core.callback(
            name="projectBrowser_loadUI", types=["custom", "unloadedApps"], args=[self]
        )
        if brsData.get("current", "None") in self.tabOrder:
            for i in range(self.tbw_browser.count()):
                if self.tbw_browser.widget(i).property("tabType") == brsData["current"]:
                    self.tbw_browser.setCurrentIndex(i)
                    break
        else:
            self.tbw_browser.setCurrentIndex(0)

        if self.tbw_browser.count() == 0:
            self.tbw_browser.setVisible(False)
            self.gb_renderings.setVisible(False)
        else:
            if self.actionRenderings.isChecked():
                self.gb_renderings.setVisible(
                    self.tabOrder[self.tbw_browser.currentWidget().property("tabType")][
                        "showRenderings"
                    ]
                )

        if "autoUpdateRenders" in brsData:
            self.chb_autoUpdate.setChecked(brsData["autoUpdateRenders"])

        if "windowSize" in brsData:
            wsize = brsData["windowSize"]
            self.resize(wsize[0], wsize[1])
        else:
            screenW = QApplication.desktop().screenGeometry().width()
            screenH = QApplication.desktop().screenGeometry().height()
            space = 200
            if screenH < (self.height() + space):
                self.resize(self.width(), screenH - space)

            if screenW < (self.width() + space):
                self.resize(screenW - space, self.height())

        if "expandedAssets_" + self.core.projectName in brsData:
            self.aExpanded = brsData["expandedAssets_" + self.core.projectName]

        if "expandedSequences_" + self.core.projectName in brsData:
            self.sExpanded = brsData["expandedSequences_" + self.core.projectName]

        if "showAssetSearch" in brsData:
            self.b_assetSearch.setChecked(brsData["showAssetSearch"])

        if "showShotSearch" in brsData:
            self.b_shotSearch.setChecked(brsData["showShotSearch"])

        self.e_assetSearch.setVisible(self.b_assetSearch.isChecked())
        self.e_shotSearch.setVisible(self.b_shotSearch.isChecked())

        if "showSearchAlways" in brsData:
            self.b_assetSearch.setHidden(brsData["showSearchAlways"])
            self.b_shotSearch.setHidden(brsData["showSearchAlways"])

        if psVersion == 2:
            self.e_assetSearch.setClearButtonEnabled(True)
            self.e_shotSearch.setClearButtonEnabled(True)

        if self.core.compareVersions(self.core.projectVersion, "v1.2.1.6") == "lower":
            self.w_aCategory.setVisible(False)

        self.updateTabSize(self.tbw_browser.currentIndex())

        self.lw_task.setAcceptDrops(True)
        self.lw_task.dragEnterEvent = self.taskDragEnterEvent
        self.lw_task.dragMoveEvent = self.taskDragMoveEvent
        self.lw_task.dragLeaveEvent = self.taskDragLeaveEvent
        self.lw_task.dropEvent = self.taskDropEvent

        self.tw_aFiles.setAcceptDrops(True)
        self.tw_aFiles.dragEnterEvent = self.sceneDragEnterEvent
        self.tw_aFiles.dragMoveEvent = lambda x: self.sceneDragMoveEvent(x, self.tw_aFiles)
        self.tw_aFiles.dragLeaveEvent = lambda x: self.sceneDragLeaveEvent(x, self.tw_aFiles)
        self.tw_aFiles.dropEvent = lambda x: self.sceneDropEvent(x, "asset", self.tw_aFiles)

        self.tw_sFiles.setAcceptDrops(True)
        self.tw_sFiles.dragEnterEvent = self.sceneDragEnterEvent
        self.tw_sFiles.dragMoveEvent = lambda x: self.sceneDragMoveEvent(x, self.tw_sFiles)
        self.tw_sFiles.dragLeaveEvent = lambda x: self.sceneDragLeaveEvent(x, self.tw_sFiles)
        self.tw_sFiles.dropEvent = lambda x: self.sceneDropEvent(x, "shot", self.tw_sFiles)

    @err_catcher(name=__name__)
    def addTab(self, name, widget, showRenderings=False):
        widget.setProperty("tabType", name)
        self.tabLabels[name] = name
        self.tbw_browser.insertTab(-1, widget, self.tabLabels[name])
        self.tabOrder[name] = {"order": self.tbw_browser.count(), "showRenderings": showRenderings}

    @err_catcher(name=__name__)
    def closeEvent(self, event):
        tabOrder = []
        for i in range(self.tbw_browser.count()):
            tabOrder.append(self.tbw_browser.widget(i).property("tabType"))

        if "Assets" not in tabOrder:
            tabOrder.append("Assets")

        if "Shots" not in tabOrder:
            tabOrder.append("Shots")

        if "Recent" not in tabOrder:
            tabOrder.append("Recent")

        visible = []
        for i in range(self.tbw_browser.count()):
            visible.append(self.tbw_browser.widget(i).property("tabType"))

        cData = []

        curW = self.tbw_browser.widget(self.tbw_browser.currentIndex())
        if curW:
            currentType = curW.property("tabType")
        else:
            currentType = ""

        cData = {
            "browser": {
                "current": currentType,
                "assetsOrder": tabOrder.index("Assets"),
                "shotsOrder": tabOrder.index("Shots"),
                "recentOrder": tabOrder.index("Recent"),
                "assetsVisible": "Assets" in visible,
                "shotsVisible": "Shots" in visible,
                "recentVisible": "Recent" in visible,
                "renderVisible": self.actionRenderings.isChecked(),
                "assetSorting": [
                    self.tw_aFiles.horizontalHeader().sortIndicatorSection(),
                    int(self.tw_aFiles.horizontalHeader().sortIndicatorOrder()),
                ],
                "shotSorting": [
                    self.tw_sFiles.horizontalHeader().sortIndicatorSection(),
                    int(self.tw_sFiles.horizontalHeader().sortIndicatorOrder()),
                ],
                "windowSize": [self.width(), self.height()],
                "expandedAssets_" + self.core.projectName: self.getExpandedAssets(),
                "expandedSequences_" + self.core.projectName: self.getExpandedSequences(),
                "showAssetSearch": self.b_assetSearch.isChecked(),
                "showShotSearch": self.b_shotSearch.isChecked(),
                "autoUpdateRenders": self.chb_autoUpdate.isChecked(),
            }
        }

        for i in getattr(self, "appFilters", []):
            sa = self.appFilters[i]["shortName"]
            cData["browser"]["show%sAssets" % sa] = getattr(self, "chb_aShow%s" % sa).isChecked()
            cData["browser"]["show%sShots" % sa] = getattr(self, "chb_sShow%s" % sa).isChecked()

        self.core.setConfig(data=cData)

        for i in getattr(self, "mediaPlaybacks", []):
            pb = self.mediaPlaybacks[i]
            if "timeline" in pb and pb["timeline"].state() != QTimeLine.NotRunning:
                pb["timeline"].setPaused(True)

        QPixmapCache.clear()

        self.core.callback(
            name="onProjectBrowserClose", types=["curApp", "custom", "prjManagers"], args=[self]
        )

        event.accept()

    @err_catcher(name=__name__)
    def loadLibs(self):
        global imageio
        os.environ["IMAGEIO_FFMPEG_EXE"] = self.core.media.getFFmpeg()
        try:
            import imageio
        except:
            logger.debug("failed to load imageio: %s" % traceback.format_exc())

    @err_catcher(name=__name__)
    def getExpandedAssets(self):
        expandedAssets = []
        for i in range(self.tw_aHierarchy.topLevelItemCount()):
            item = self.tw_aHierarchy.topLevelItem(i)
            expandedAssets += self.getExpandedChildren(item)

        return expandedAssets

    @err_catcher(name=__name__)
    def getExpandedChildren(self, item):
        expandedAssets = []
        if item.isExpanded():
            expandedAssets.append(item.text(1))

        for i in range(item.childCount()):
            expandedAssets += self.getExpandedChildren(item.child(i))

        return expandedAssets

    @err_catcher(name=__name__)
    def getExpandedSequences(self):
        expandedSeqs = []
        for i in range(self.tw_sShot.topLevelItemCount()):
            item = self.tw_sShot.topLevelItem(i)
            if item.isExpanded():
                expandedSeqs.append(item.text(0))

        return expandedSeqs

    @err_catcher(name=__name__)
    def tabChanged(self, tab):
        if not self.tbw_browser.widget(tab):
            tabType = ""
            self.gb_renderings.setVisible(False)
        else:
            tabType = self.tbw_browser.widget(tab).property("tabType")

            if tabType == "Assets":
                self.refreshAFile()
            elif tabType == "Shots":
                self.refreshSFile()
            elif tabType == "Recent":
                self.setRecent()

            if self.actionRenderings.isChecked():
                self.gb_renderings.setVisible(self.tabOrder[tabType]["showRenderings"])

        if self.gb_renderings.isVisible() and self.chb_autoUpdate.isChecked():
            self.updateTasks()

        self.updateTabSize(tab)

    @err_catcher(name=__name__)
    def updateTabSize(self, tab):
        for idx in range(self.tbw_browser.count()):
            if idx != tab:
                self.tbw_browser.widget(idx).setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        curWidget = self.tbw_browser.widget(tab)
        if not curWidget:
            return

        curWidget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

    @err_catcher(name=__name__)
    def checkVisibleTabs(self):
        cw = self.tbw_browser.currentWidget()
        if not cw:
            self.core.popup(
                'No tabs are currently enabled. Use the "View" menu to enable available tabs.'
            )
            return False

        return True

    @err_catcher(name=__name__)
    def refreshUI(self):
        if not self.checkVisibleTabs():
            return

        self.setEnabled(False)
        QCoreApplication.processEvents()
        cw = self.tbw_browser.currentWidget()
        curTab = cw.property("tabType")
        curData = [
            curTab,
            self.cursShots,
            self.curRTask,
            self.curRVersion,
            self.curRLayer,
        ]

        if curTab == "Assets":
            curAssetItem = self.tw_aHierarchy.currentItem()
            if not curAssetItem:
                navData = {"entity": "asset"}
            else:
                basePath = self.tw_aHierarchy.currentItem().text(1)
                navData = {
                    "entity": "asset",
                    "basePath": basePath,
                    "step": self.curaStep,
                    "category": self.curaCat,
                }
            self.refreshAHierarchy()
        elif curTab == "Shots":
            navData = {
                "entity": "shot",
                "entityName": self.cursShots,
                "step": self.cursStep,
                "category": self.cursCat,
            }

            self.refreshShots()
        elif curTab == "Recent":
            self.setRecent()

        self.core.callback(name="onProjectBrowserRefreshUI", args=[self])
        self.setEnabled(True)

        if curTab in ["Assets", "Shots"]:
            self.navigate(data=navData)
            self.showRender(curData[0], curData[1], curData[2], curData[3], curData[4])

    @err_catcher(name=__name__)
    def mousedb(self, event, tab, uielement):
        createCat = True
        if tab == "ah":
            cItem = uielement.itemFromIndex(uielement.indexAt(event.pos()))
            if cItem and cItem.text(2) != "folder":
                createCat = False
            name = "Entity"
        elif tab == "ap":
            if self.curAsset:
                self.createStepWindow("a")
        elif tab == "ac":
            if (
                self.curaStep is not None
                and self.lw_aCategory.indexAt(event.pos()).data() == None
            ):
                name = "Category"
        elif tab == "ss":
            mIndex = uielement.indexAt(event.pos())
            if mIndex.data() == None:
                self.editShot()
            else:
                if (
                    mIndex.parent().column() == -1
                    and uielement.mapFromGlobal(QCursor.pos()).x() > 10
                ):
                    uielement.setExpanded(mIndex, not uielement.isExpanded(mIndex))
                    uielement.mouseDClick(event)
        elif tab == "sp":
            shotName = self.core.entities.splitShotname(self.cursShots)
            if (
                shotName
                and len(shotName) == 2
                and shotName[0]
                and self.lw_sPipeline.indexAt(event.pos()).data() == None
            ):
                self.createStepWindow("s")
        elif tab == "sc":
            if (
                self.cursStep is not None
                and self.lw_sCategory.indexAt(event.pos()).data() == None
            ):
                name = "Category"

        if (
            createCat
            and (
                (tab != "ah" and tab != "ss")
                or self.dclick
                or self.adclick
                or self.sdclick
            )
        ):
            if "name" in locals():
                self.createCatWin(tab, name)

            uielement.mouseDClick(event)

        if tab == "ah" and not self.adclick:
            pos = self.tw_aHierarchy.mapFromGlobal(QCursor.pos())
            item = self.tw_aHierarchy.itemAt(pos.x(), pos.y())
            if item is not None:
                item.setExpanded(not item.isExpanded())
        elif tab == "ss" and not self.sdclick:
            pos = self.tw_sShot.mapFromGlobal(QCursor.pos())
            item = self.tw_sShot.itemAt(pos.x(), pos.y())
            if item is not None:
                item.setExpanded(not item.isExpanded())

    @err_catcher(name=__name__)
    def mouseClickEvent(self, event, uielement):
        if QEvent != None:
            if event.type() == QEvent.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    if uielement == "ah":
                        index = self.tw_aHierarchy.indexAt(event.pos())
                        if index.data() == None:
                            self.tw_aHierarchy.setCurrentIndex(
                                self.tw_aHierarchy.model().createIndex(-1, 0)
                            )
                        self.tw_aHierarchy.mouseClickEvent(event)
                    elif uielement == "ap":
                        index = self.lw_aPipeline.indexAt(event.pos())
                        if index.data() == None:
                            self.lw_aPipeline.setCurrentIndex(
                                self.lw_aPipeline.model().createIndex(-1, 0)
                            )
                        self.lw_aPipeline.mouseClickEvent(event)
                    elif uielement == "ac":
                        index = self.lw_aCategory.indexAt(event.pos())
                        if index.data() == None:
                            self.lw_aCategory.setCurrentIndex(
                                self.lw_aCategory.model().createIndex(-1, 0)
                            )
                        self.lw_aCategory.mouseClickEvent(event)
                    elif uielement == "af":
                        index = self.tw_aFiles.indexAt(event.pos())
                        if index.data() == None:
                            self.tw_aFiles.setCurrentIndex(
                                self.tw_aFiles.model().createIndex(-1, 0)
                            )
                        self.tw_aFiles.mouseClickEvent(event)
                    elif uielement == "ss":
                        index = self.tw_sShot.indexAt(event.pos())
                        if index.data() == None:
                            self.tw_sShot.setCurrentIndex(
                                self.tw_sShot.model().createIndex(-1, 0)
                            )
                        self.tw_sShot.mouseClickEvent(event)
                    elif uielement == "sp":
                        index = self.lw_sPipeline.indexAt(event.pos())
                        if index.data() == None:
                            self.lw_sPipeline.setCurrentIndex(
                                self.lw_sPipeline.model().createIndex(-1, 0)
                            )
                        self.lw_sPipeline.mouseClickEvent(event)
                    elif uielement == "sc":
                        index = self.lw_sCategory.indexAt(event.pos())
                        if index.data() == None:
                            self.lw_sCategory.setCurrentIndex(
                                self.lw_sCategory.model().createIndex(-1, 0)
                            )
                        self.lw_sCategory.mouseClickEvent(event)
                    elif uielement == "sf":
                        index = self.tw_sFiles.indexAt(event.pos())
                        if index.data() == None:
                            self.tw_sFiles.setCurrentIndex(
                                self.tw_sFiles.model().createIndex(-1, 0)
                            )
                        self.tw_sFiles.mouseClickEvent(event)
                    elif uielement == "r":
                        index = self.tw_recent.indexAt(event.pos())
                        if index.data() == None:
                            self.tw_recent.setCurrentIndex(
                                self.tw_recent.model().createIndex(-1, 0)
                            )
                        self.tw_recent.mouseClickEvent(event)
            elif event.type() == QEvent.MouseButtonPress:
                if uielement == "ah":
                    self.adclick = True
                    self.tw_aHierarchy.mousePrEvent(event)
                elif uielement == "ss":
                    self.sdclick = True
                    self.tw_sShot.mousePrEvent(event)

    @err_catcher(name=__name__)
    def mouseEnter(self, event, entity):
        if entity == "assets":
            self.tw_aHierarchy.setFocus()
        elif entity == "shots":
            self.tw_sShot.setFocus()

    @err_catcher(name=__name__)
    def keyPressed(self, event, entity):
        if entity in ["assets", "assetSearch"]:
            etext = self.e_assetSearch
            elist = self.tw_aHierarchy
            searchButton = self.b_assetSearch
        elif entity in ["shots", "shotSearch"]:
            etext = self.e_shotSearch
            elist = self.tw_sShot
            searchButton = self.b_shotSearch

        if entity in ["assets", "shots"]:
            if event.key() == Qt.Key_Escape:
                searchButton.setChecked(False)
            elif event.text():
                searchButton.setChecked(True)
                etext.keyPressEvent(event)
            else:
                elist.origKeyPressEvent(event)
        elif entity in ["assetSearch", "shotSearch"]:
            if event.key() == Qt.Key_Escape:
                searchButton.setChecked(False)
            else:
                searchButton.setChecked(True)
                etext.origKeyPressEvent(event)

        event.accept()

    @err_catcher(name=__name__)
    def searchClicked(self, state, entity):
        if entity in ["assets"]:
            etext = self.e_assetSearch
            searchButton = self.b_assetSearch
        elif entity in ["shots"]:
            etext = self.e_shotSearch
            searchButton = self.b_shotSearch

        if not searchButton.isHidden():
            etext.setVisible(state)

        if state:
            etext.setFocus()
        else:
            etext.setText("")
            etext.textChanged.emit("")

    @err_catcher(name=__name__)
    def tableMoveEvent(self, event, table):
        self.showDetailWin(event, table)
        if hasattr(self, "detailWin") and self.detailWin.isVisible():
            self.detailWin.move(QCursor.pos().x() + 20, QCursor.pos().y())

    @err_catcher(name=__name__)
    def showDetailWin(self, event, table):
        if table == "af":
            table = self.tw_aFiles
        elif table == "sf":
            table = self.tw_sFiles
        elif table == "r":
            table = self.tw_recent

        index = table.indexAt(event.pos())
        if index.data() is None:
            if hasattr(self, "detailWin") and self.detailWin.isVisible():
                self.detailWin.close()
            return

        scenePath = table.model().index(index.row(), 0).data(Qt.UserRole)
        if scenePath is None:
            if hasattr(self, "detailWin") and self.detailWin.isVisible():
                self.detailWin.close()
            return

        infoPath = os.path.splitext(scenePath)[0] + "versioninfo.yml"
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
    def tableLeaveEvent(self, event, table):
        if hasattr(self, "detailWin") and self.detailWin.isVisible():
            self.detailWin.close()

    @err_catcher(name=__name__)
    def tableFocusOutEvent(self, event, table):
        if hasattr(self, "detailWin") and self.detailWin.isVisible():
            self.detailWin.close()

    @err_catcher(name=__name__)
    def getContextMenu(self, menuType, **kwargs):
        menu = None
        if menuType == "mediaPreview":
            menu = self.getMediaPreviewMenu(**kwargs)
        elif menuType == "refresh":
            menu = self.getRefreshMenu(**kwargs)

        return menu

    @err_catcher(name=__name__)
    def showContextMenu(self, menuType, **kwargs):
        menu = self.getContextMenu(menuType, **kwargs)
        self.core.callback(
            name="projectBrowserContextMenuRequested",
            types=["custom"],
            args=[self, menuType, menu],
        )
        if not menu:
            return

        menu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def getMediaPreviewMenu(self, mediaPlayback=None):
        path = mediaPlayback["getMediaBaseFolder"](
                basepath=self.renderBasePath,
                product=self.curRTask,
                version=self.curRVersion,
                layer=self.curRLayer
            )[0]

        if not path:
            return

        rcmenu = QMenu(self)

        if len(mediaPlayback["seq"]) > 0:
            if len(mediaPlayback["seq"]) == 1:
                path = os.path.join(path, mediaPlayback["seq"][0])

            playMenu = QMenu("Play in", self)

            if self.rv is not None:
                pAct = QAction("RV", self)
                pAct.triggered.connect(
                    lambda: self.compare(
                        current=True, prog="RV", mediaPlayback=mediaPlayback
                    )
                )
                playMenu.addAction(pAct)

            if self.djv is not None:
                pAct = QAction("DJV", self)
                pAct.triggered.connect(
                    lambda: self.compare(
                        current=True, prog="DJV", mediaPlayback=mediaPlayback
                    )
                )
                playMenu.addAction(pAct)

            if self.vlc is not None:
                pAct = QAction("VLC", self)
                pAct.triggered.connect(
                    lambda: self.compare(
                        current=True, prog="VLC", mediaPlayback=mediaPlayback
                    )
                )
                playMenu.addAction(pAct)

                if mediaPlayback["pformat"] == "*.exr":
                    pAct.setEnabled(False)

            pAct = QAction("Default", self)
            pAct.triggered.connect(
                lambda: self.compare(
                    current=True, prog="default", mediaPlayback=mediaPlayback
                )
            )
            playMenu.addAction(pAct)
            rcmenu.addMenu(playMenu)

        for i in self.core.prjManagers.values():
            pubAct = i.pbBrowser_getPublishMenu(self)
            if pubAct is not None:
                rcmenu.addAction(pubAct)

        exp = QAction("Open in Explorer", self)
        exp.triggered.connect(lambda: self.core.openFolder(path))
        rcmenu.addAction(exp)

        copAct = QAction("Copy path", self)
        copAct.triggered.connect(lambda: self.core.copyToClipboard(path))
        rcmenu.addAction(copAct)

        if len(mediaPlayback["seq"]) == 1 or mediaPlayback["prvIsSequence"]:
            cvtMenu = QMenu("Convert", self)
            qtAct = QAction("jpg", self)
            qtAct.triggered.connect(
                lambda: self.convertImgs(".jpg", mediaPlayback=mediaPlayback)
            )
            cvtMenu.addAction(qtAct)
            qtAct = QAction("png", self)
            qtAct.triggered.connect(
                lambda: self.convertImgs(".png", mediaPlayback=mediaPlayback)
            )
            cvtMenu.addAction(qtAct)
            qtAct = QAction("mp4", self)
            qtAct.triggered.connect(
                lambda: self.convertImgs(".mp4", mediaPlayback=mediaPlayback)
            )
            cvtMenu.addAction(qtAct)
            movAct = QAction("mov", self)
            movAct.triggered.connect(
                lambda: self.convertImgs(".mov", mediaPlayback=mediaPlayback)
            )
            cvtMenu.addAction(movAct)
            rcmenu.addMenu(cvtMenu)

        if len(mediaPlayback["seq"]) > 0:
            if self.tbw_browser.currentWidget().property("tabType") == "Assets":
                prvAct = QAction("Set as assetpreview", self)
                prvAct.triggered.connect(self.setPreview)
                rcmenu.addAction(prvAct)

            elif self.tbw_browser.currentWidget().property("tabType") == "Shots":
                prvAct = QAction("Set as shotpreview", self)
                prvAct.triggered.connect(self.setPreview)
                rcmenu.addAction(prvAct)

        if (
            len(mediaPlayback["seq"]) > 0
            and not self.curRVersion.endswith(" (local)")
            and self.core.getConfig("paths", "dailies", configPath=self.core.prismIni)
            is not None
        ):
            dliAct = QAction("Send to dailies", self)
            dliAct.triggered.connect(
                lambda: self.sendToDailies(mediaPlayback=mediaPlayback)
            )
            rcmenu.addAction(dliAct)

        if self.core.appPlugin.appType == "2d" and len(mediaPlayback["seq"]) > 0:
            impAct = QAction("Import images...", self)
            impAct.triggered.connect(lambda: self.core.appPlugin.importImages(self))
            rcmenu.addAction(impAct)

        return rcmenu

    @err_catcher(name=__name__)
    def getRefreshMenu(self):
        menu = QMenu(self)
        menu.addAction("Clear configcache", self.core.configs.clearCache)
        menu.addActions(self.b_refreshTabs.actions())
        return menu

    @err_catcher(name=__name__)
    def rclCat(self, tab, pos):
        rcmenu = QMenu(self)
        typename = "Category"
        callbackName = ""

        if tab == "ah":
            lw = self.tw_aHierarchy
            cItem = lw.itemFromIndex(lw.indexAt(pos))
            if cItem is None:
                path = self.aBasePath
            else:
                path = os.path.dirname(cItem.text(1))
            typename = "Entity"
            callbackName = "openPBAssetContextMenu"
        elif tab == "ap":
            lw = self.lw_aPipeline

            if not self.curAsset:
                return

            path = self.core.getEntityPath(entity="step", asset=self.curAsset)
            typename = "Step"
            callbackName = "openPBAssetStepContextMenu"

        elif tab == "ac":
            lw = self.lw_aCategory
            if self.curaStep is not None:
                path = self.core.getEntityPath(asset=self.curAsset, step=self.curaStep)
            else:
                return False

            callbackName = "openPBAssetCategoryContextMenu"

        elif tab == "ss":
            lw = self.tw_sShot
            path = self.sBasePath
            typename = "Shot"
            callbackName = "openPBShotContextMenu"

        elif tab == "sp":
            lw = self.lw_sPipeline
            shotName = self.core.entities.splitShotname(self.cursShots)
            if not (
                shotName
                and len(shotName) == 2
                and shotName[0]
            ):
                return False

            path = self.core.getEntityPath(entity="step", shot=self.cursShots)
            typename = "Step"
            callbackName = "openPBShotStepContextMenu"

        elif tab == "sc":
            lw = self.lw_sCategory
            if self.cursStep is not None:
                path = self.core.getEntityPath(shot=self.cursShots, step=self.cursStep)
            else:
                return False

            callbackName = "openPBShotCategoryContextMenu"

        if tab in ["ap", "ac", "ss", "sp", "sc"]:
            createAct = QAction("Create " + typename, self)
            if tab == "ap":
                createAct.triggered.connect(lambda: self.createStepWindow("a"))
            elif tab == "sp":
                createAct.triggered.connect(lambda: self.createStepWindow("s"))
            elif tab == "ss":
                createAct.triggered.connect(self.editShot)
            else:
                createAct.triggered.connect(lambda: self.createCatWin(tab, typename))
            rcmenu.addAction(createAct)

        iname = (lw.indexAt(pos)).data()

        if iname:
            prjMngMenus = []
            addOmit = False
            dirPath = None
            if tab == "ah":
                args = [self, iname, cItem.text(1).replace(self.aBasePath, "")[1:], cItem.text(2)]
                cmenu = self.core.callback(name="projectBrowser_getAssetMenu", args=args)
                if cmenu:
                    prjMngMenus += cmenu

                if cItem and cItem.text(2) == "folder":
                    subcat = QAction("Create entity", self)
                    typename = "Entity"
                    subcat.triggered.connect(lambda: self.createCatWin(tab, typename))
                    rcmenu.addAction(subcat)

                oAct = QAction("Omit Asset", self)
                oAct.triggered.connect(
                    lambda: self.omitEntity(
                        "asset", cItem.text(1).replace(self.aBasePath, "")[1:]
                    )
                )
                addOmit = True
            elif tab == "ss":
                iname = self.cursShots or iname
                shotName, seqName = self.core.entities.splitShotname(iname)
                if lw.itemAt(pos).childCount() == 0:
                    dirPath = lw.itemAt(pos).data(0, Qt.UserRole)[0]["path"]
                    editAct = QAction("Edit shot settings", self)
                    editAct.triggered.connect(lambda: self.editShot(iname))
                    rcmenu.addAction(editAct)

                    args = [self, iname]
                    cmenu = self.core.callback(name="projectBrowser_getShotMenu", args=args)
                    if cmenu:
                        prjMngMenus += cmenu

                    oAct = QAction("Omit shot", self)
                    oAct.triggered.connect(lambda: self.omitEntity("shot", self.cursShots))
                    addOmit = True
            dirPath = dirPath or os.path.join(path, iname)
            if (
                not os.path.exists(dirPath)
                and self.core.useLocalFiles
                and os.path.exists(
                    self.core.convertPath(dirPath, "local")
                )
            ):
                dirPath = self.core.convertPath(dirPath, "local")
            openex = QAction("Open in explorer", self)
            openex.triggered.connect(lambda: self.core.openFolder(dirPath))
            rcmenu.addAction(openex)
            copAct = QAction("Copy path", self)
            copAct.triggered.connect(lambda: self.core.copyToClipboard(dirPath))
            rcmenu.addAction(copAct)
            for i in prjMngMenus:
                if i:
                    rcmenu.addAction(i)
            if addOmit:
                rcmenu.addAction(oAct)
        elif "path" in locals():
            if iname is None:
                lw.setCurrentIndex(lw.model().createIndex(-1, 0))
            if tab not in ["ap", "ac", "ss", "sp", "sc"]:
                cat = QAction("Create " + typename, self)
                cat.triggered.connect(lambda: self.createCatWin(tab, typename))
                rcmenu.addAction(cat)
            openex = QAction("Open in explorer", self)
            openex.triggered.connect(lambda: self.core.openFolder(path))
            rcmenu.addAction(openex)
            copAct = QAction("Copy path", self)
            copAct.triggered.connect(lambda: self.core.copyToClipboard(path))
            rcmenu.addAction(copAct)

        if tab in ["ah", "ss"]:
            if tab == "ah":
                widget = self.tw_aHierarchy
            elif tab == "ss":
                widget = self.tw_sShot
            expAct = QAction("Expand all", self)
            expAct.triggered.connect(lambda x=None, tw=widget: self.setWidgetItemsExpanded(tw))
            clpAct = QAction("Collapse all", self)
            clpAct.triggered.connect(lambda x=None, tw=widget: self.setWidgetItemsExpanded(tw, expanded=False))
            rcmenu.insertAction(openex, expAct)
            rcmenu.insertAction(openex, clpAct)

        if callbackName:
            self.core.callback(
                name=callbackName,
                types=["custom"],
                args=[self, rcmenu, lw.indexAt(pos)],
            )

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def rclFile(self, tab, pos):
        if tab == "a":
            if self.curaStep is None or self.curaCat is None:
                return

            tw = self.tw_aFiles
            filepath = self.core.getEntityPath(asset=self.curAsset, step=self.curaStep, category=self.curaCat)
            tabName = "asset"
        elif tab == "sf":
            if self.cursStep is None or self.cursCat is None:
                return

            tw = self.tw_sFiles
            filepath = self.core.getEntityPath(shot=self.cursShots, step=self.cursStep, category=self.cursCat)
            tabName = "shot"
        elif tab == "r":
            tw = self.tw_recent

        rcmenu = QMenu(self)

        if tw.selectedIndexes() != []:
            idx = tw.selectedIndexes()[0]
            irow = idx.row()
        else:
            idx = None
            irow = -1
        cop = QAction("Copy", self)
        if irow == -1:
            if tab == "r":
                return False
            cop.setEnabled(False)
            if (
                not os.path.exists(filepath)
                and self.core.useLocalFiles
                and os.path.exists(self.core.convertPath(filepath, "local"))
            ):
                filepath = self.core.convertPath(filepath, "local")
        else:
            filepath = self.core.fixPath(tw.model().index(irow, 0).data(Qt.UserRole))
            cop.triggered.connect(lambda: self.copyfile(filepath))
            tw.setCurrentIndex(tw.model().createIndex(irow, 0))
        if tab != "r":
            rcmenu.addAction(cop)
            past = QAction("Paste as new version", self)
            past.triggered.connect(lambda: self.pastefile(tab))
            if not (tab == "a" and self.copiedFile != None) and not (
                tab == "sf" and self.copiedsFile != None
            ):
                past.setEnabled(False)
            rcmenu.addAction(past)
            current = QAction("Create new version from current", self)
            current.triggered.connect(lambda: self.createFromCurrent())
            if self.core.appPlugin.pluginName == "Standalone":
                current.setEnabled(False)
            rcmenu.addAction(current)
            emp = QMenu("Create new version from preset", self)
            emptyDir = os.path.join(os.path.dirname(self.core.prismIni), "EmptyScenes")
            if os.path.exists(emptyDir):
                for i in sorted(os.listdir(emptyDir)):
                    base, ext = os.path.splitext(i)
                    if ext in self.core.getPluginSceneFormats():
                        empAct = QAction(base, self)
                        empAct.triggered.connect(
                            lambda y=None, x=tabName, fname=i: self.createEmptyScene(
                                x, fname
                            )
                        )
                        emp.addAction(empAct)

            newPreset = QAction("< Create new preset from current >", self)
            newPreset.triggered.connect(self.core.entities.createPresetScene)
            emp.addAction(newPreset)
            if self.core.appPlugin.pluginName == "Standalone":
                newPreset.setEnabled(False)

            rcmenu.addMenu(emp)
            autob = QMenu("Create new version from autoback", self)
            for i in self.core.getPluginNames():
                if self.core.getPluginData(i, "appType") == "standalone":
                    continue

                autobAct = QAction(i, self)
                autobAct.triggered.connect(lambda y=None, x=i: self.autoback(tab, x))
                autob.addAction(autobAct)

            rcmenu.addMenu(autob)

        if irow != -1:
            if tab != "r":
                globalAct = QAction("Copy to global", self)
                if self.core.useLocalFiles and filepath.startswith(
                    self.core.localProjectPath
                ):
                    globalAct.triggered.connect(lambda: self.copyToGlobal(filepath))
                else:
                    globalAct.setEnabled(False)
                rcmenu.addAction(globalAct)

            actDeps = QAction("Show dependencies...", self)
            infoPath = os.path.splitext(filepath)[0] + "versioninfo.yml"
            self.core.configs.findDeprecatedConfig(infoPath)
            if os.path.exists(infoPath):
                actDeps.triggered.connect(lambda: self.core.dependencyViewer(infoPath))
            else:
                actDeps.setEnabled(False)
            rcmenu.addAction(actDeps)

            actCom = QAction("Edit Comment...", self)
            actCom.triggered.connect(lambda: self.editComment(filepath))
            rcmenu.addAction(actCom)

        openex = QAction("Open in Explorer", self)
        openex.triggered.connect(lambda: self.core.openFolder(filepath))
        rcmenu.addAction(openex)

        copAct = QAction("Copy path", self)
        copAct.triggered.connect(lambda: self.core.copyToClipboard(filepath))
        rcmenu.addAction(copAct)

        self.core.callback(
            name="openPBFileContextMenu", types=["custom"], args=[self, rcmenu, idx]
        )

        rcmenu.exec_((tw.viewport()).mapToGlobal(pos))

    @err_catcher(name=__name__)
    def sceneDoubleClicked(self, index):
        filepath = index.model().index(index.row(), 0).data(Qt.UserRole)
        self.exeFile(filepath)

    @err_catcher(name=__name__)
    def exeFile(self, filepath):
        sm = getattr(self.core, "sm", None)
        if sm:
            openSm = not self.core.sm.isHidden()
            self.core.sm.close()

        if self.tbw_browser.currentWidget().property("tabType") == "Assets":
            refresh = self.refreshAFile
        elif self.tbw_browser.currentWidget().property("tabType") == "Shots":
            refresh = self.refreshSFile
        elif self.tbw_browser.currentWidget().property("tabType") == "Recent":
            refresh = self.setRecent

        if self.core.useLocalFiles and self.sceneBasePath in filepath:
            lfilepath = self.core.convertPath(filepath, "local")

            if not os.path.exists(lfilepath):
                if not os.path.exists(os.path.dirname(lfilepath)):
                    try:
                        os.makedirs(os.path.dirname(lfilepath))
                    except:
                        self.core.popup(self.core.messageParent, "The directory could not be created")
                        return

                self.core.copySceneFile(filepath, lfilepath)

            filepath = lfilepath

        filepath = filepath.replace("\\", "/")

        logger.debug("Opening scene " + filepath)
        isOpen = self.core.appPlugin.openScene(self, filepath)

        if not isOpen and self.core.appPlugin.pluginName == "Standalone":
            fileStarted = False
            ext = os.path.splitext(filepath)[1]
            appPath = ""

            for i in self.core.unloadedAppPlugins.values():
                if ext in i.sceneFormats:
                    orApp = self.core.getConfig(
                        "dccoverrides",
                        "%s_override" % i.pluginName,
                    )
                    if orApp:
                        appOrPath = self.core.getConfig(
                            "dccoverrides", "%s_path" % i.pluginName
                        )
                        if appOrPath and os.path.exists(appOrPath):
                            appPath = appOrPath

                    fileStarted = getattr(
                        i, "customizeExecutable", lambda x1, x2, x3: False
                    )(self, appPath, filepath)

            if appPath != "" and not fileStarted:
                try:
                    subprocess.Popen([appPath, self.core.fixPath(filepath)])
                except:
                    msg = "Could not execute file:\n\n%s" % traceback.format_exc()
                    self.core.popup(msg)
                fileStarted = True

            if not fileStarted:
                try:
                    if platform.system() == "Windows":
                        os.startfile(self.core.fixPath(filepath))
                    elif platform.system() == "Linux":
                        subprocess.Popen(["xdg-open", filepath])
                    elif platform.system() == "Darwin":
                        subprocess.Popen(["open", filepath])
                except:
                    ext = os.path.splitext(filepath)[1]
                    warnStr = (
                        'Could not open the scenefile.\n\nPossibly there is no application connected to "%s" files on your computer.\nUse the overrides in the "DCC apps" tab of the Prism Settings to specify an application for this filetype.'
                        % ext
                    )
                    self.core.popup(warnStr)

        self.core.addToRecent(filepath)
        self.setRecent()

        self.core.callback(name="onSceneOpen", types=["custom"], args=[self, filepath])

        if sm and openSm:
            self.core.stateManager()

        refresh()
        if (
            self.core.getCurrentFileName().replace("\\", "/") == filepath
            and self.actionCloseAfterLoad.isChecked()
        ):
            self.close()

    @err_catcher(name=__name__)
    def createFromCurrent(self):
        if self.tbw_browser.currentWidget().property("tabType") == "Assets":
            dstname = self.curAsset
            refresh = self.refreshAFile

            prefix = self.core.entities.getAssetNameFromPath(self.curAsset)
            filepath = self.core.generateScenePath(
                entity="asset",
                entityName=prefix,
                step=self.curaStep,
                category=self.curaCat,
                basePath=dstname,
                extension=self.core.appPlugin.getSceneExtension(self),
            )

        elif self.tbw_browser.currentWidget().property("tabType") == "Shots":
            refresh = self.refreshSFile
            filepath = self.core.generateScenePath(
                entity="shot",
                entityName=self.cursShots,
                step=self.cursStep,
                category=self.cursCat,
                extension=self.core.appPlugin.getSceneExtension(self),
            )
        else:
            return

        if self.core.useLocalFiles:
            filepath = self.core.convertPath(filepath, "local")

        if not os.path.exists(os.path.dirname(filepath)):
            try:
                os.makedirs(os.path.dirname(filepath))
            except:
                self.core.popup("The directory could not be created")
                return

        filepath = filepath.replace("\\", "/")

        asRunning = hasattr(self.core, "asThread") and self.core.asThread.isRunning()
        self.core.startasThread(quit=True)

        filepath = self.core.saveScene(filepath=filepath)
        self.core.sceneOpen()
        if asRunning:
            self.core.startasThread()

        self.core.addToRecent(filepath)
        self.setRecent()
        logger.debug("Created scene from current: %s" % filepath)

        refresh()

    @err_catcher(name=__name__)
    def getAutobackPath(self, tab, prog):
        if prog == self.core.appPlugin.pluginName:
            autobackpath, fileStr = self.core.appPlugin.getAutobackPath(self, tab)
        else:
            for i in self.core.unloadedAppPlugins.values():
                if i.pluginName == prog:
                    autobackpath, fileStr = i.getAutobackPath(self, tab)

        if not autobackpath:
            if tab == "a":
                cVersion = self.core.compareVersions(self.core.projectVersion, "v1.2.1.6")
                asset = self.tw_aHierarchy.currentItem().text(1)
                step = self.lw_aPipeline.currentItem().text()
                if cVersion == "lower":
                    autobackpath = self.core.getEntityPath(asset=asset, step=step)
                else:
                    category = self.lw_aCategory.currentItem().text()
                    autobackpath = self.core.getEntityPath(asset=asset, step=step, category=category)

            elif tab == "sf":
                autobackpath = self.core.getEntityPath(shot=self.cursShots, step=self.cursStep, category=self.cursCat)

        return autobackpath, fileStr

    @err_catcher(name=__name__)
    def autoback(self, tab, prog):
        autobackpath, fileStr = self.getAutobackPath(tab, prog)

        autobfile = QFileDialog.getOpenFileName(
            self, "Select Autoback File", autobackpath, fileStr
        )[0]

        if not autobfile:
            return

        if tab == "a":
            dstname = self.curAsset
            refresh = self.refreshAFile

            prefix = self.core.entities.getAssetNameFromPath(self.curAsset)
            filepath = self.core.generateScenePath(
                entity="asset",
                entityName=prefix,
                step=self.curaStep,
                extension=os.path.splitext(autobfile)[1],
                category=self.curaCat,
                basePath=dstname,
            )
        elif tab == "sf":
            refresh = self.refreshSFile
            filepath = self.core.generateScenePath(
                entity="shot",
                entityName=self.cursShots,
                step=self.cursStep,
                category=self.cursCat,
                extension=os.path.splitext(autobfile)[1],
            )
        else:
            return

        if self.core.useLocalFiles:
            filepath = self.core.convertPath(filepath, "local")

        if not os.path.exists(os.path.dirname(filepath)):
            try:
                os.makedirs(os.path.dirname(filepath))
            except:
                self.core.popup("The directory could not be created")
                return

        filepath = filepath.replace("\\", "/")

        self.core.copySceneFile(autobfile, filepath)
        logger.debug("Created scene from autoback: %s" % filepath)

        if prog == self.core.appPlugin.pluginName:
            self.exeFile(filepath=filepath)
        else:
            self.core.addToRecent(filepath)
            self.setRecent()
            refresh()

    @err_catcher(name=__name__)
    def createEmptyScene(
        self,
        entity,
        fileName,
        entityName=None,
        assetPath=None,
        step=None,
        category=None,
        comment=None,
        openFile=True,
        version=None,
        location="local",
    ):
        ext = os.path.splitext(fileName)[1]
        if entity == "asset":
            refresh = self.refreshAFile
            assetPath = self.curAsset
            entityName = self.core.entities.getAssetNameFromPath(self.curAsset)
            step = step or self.curaStep
            category = category or self.curaCat
        elif entity == "shot":
            refresh = self.refreshSFile
            entityName = entityName or self.cursShots
            step = step or self.cursStep
            category = category or self.cursCat
        else:
            self.core.popup("Invalid entity:\n\n%s" % entity)
            return

        filePath = self.core.entities.createEmptyScene(
            entity,
            fileName,
            entityName=entityName,
            assetPath=assetPath,
            step=step,
            category=category,
            comment=comment,
            version=version,
            location=location,
        )

        if self.core.uiAvailable:
            if ext in self.core.appPlugin.sceneFormats and openFile:
                self.core.callback(
                    name="preLoadEmptyScene",
                    types=["curApp", "custom"],
                    args=[self, filePath],
                )
                self.exeFile(filepath=filePath)
                self.core.callback(
                    name="postLoadEmptyScene",
                    types=["curApp", "custom"],
                    args=[self, filePath],
                )
            else:
                self.core.addToRecent(filePath)
                self.setRecent()
                refresh()

        return filePath

    @err_catcher(name=__name__)
    def copyfile(self, path, mode=None):
        if self.tbw_browser.currentWidget().property("tabType") == "Assets":
            self.copiedFile = path
        elif self.tbw_browser.currentWidget().property("tabType") == "Shots":
            self.copiedsFile = path

    @err_catcher(name=__name__)
    def pastefile(self, tab):
        if tab == "a":
            dstname = self.curAsset

            prefix = self.core.entities.getAssetNameFromPath(self.curAsset)
            dstname = self.core.generateScenePath(
                entity="asset",
                entityName=prefix,
                step=self.curaStep,
                category=self.curaCat,
                extension=os.path.splitext(self.copiedFile)[1],
                basePath=dstname,
            )

            if self.core.useLocalFiles:
                dstname = self.core.convertPath(dstname, "local")

            if not os.path.exists(os.path.dirname(dstname)):
                try:
                    os.makedirs(os.path.dirname(dstname))
                except:
                    self.core.popup("The directory could not be created")
                    return

            dstname = dstname.replace("\\", "/")

            self.core.copySceneFile(self.copiedFile, dstname)

            if os.path.splitext(dstname)[1] in self.core.appPlugin.sceneFormats:
                self.exeFile(filepath=dstname)
            else:
                self.core.addToRecent(dstname)
                self.setRecent()

            self.refreshAFile()

        elif tab == "sf":
            oldfname = os.path.basename(self.copiedsFile)
            dstname = self.core.generateScenePath(
                entity="shot",
                entityName=self.cursShots,
                step=self.cursStep,
                category=self.cursCat,
                extension=os.path.splitext(oldfname)[1],
            )

            if self.core.useLocalFiles:
                dstname = self.core.convertPath(dstname, "local")

            if not os.path.exists(os.path.dirname(dstname)):
                try:
                    os.makedirs(os.path.dirname(dstname))
                except:
                    self.core.popup("The directory could not be created")
                    return

            dstname = dstname.replace("\\", "/")

            self.core.copySceneFile(self.copiedsFile, dstname)

            if os.path.splitext(dstname)[1] in self.core.appPlugin.sceneFormats:
                self.exeFile(filepath=dstname)
            else:
                self.core.addToRecent(dstname)
                self.setRecent()

            self.refreshSFile()

    @err_catcher(name=__name__)
    def getStep(self, steps, tab):
        try:
            del sys.modules["ItemList"]
        except:
            pass

        if tab == "a":
            entity = "asset"
        elif tab == "s":
            entity = "shot"

        import ItemList

        self.ss = ItemList.ItemList(core=self.core, entity=entity)
        self.core.parentWindow(self.ss)
        self.ss.tw_steps.setFocus()
        self.ss.tw_steps.doubleClicked.connect(self.ss.accept)

        abrSteps = list(steps.keys())
        abrSteps.sort()
        for i in abrSteps:
            catName = steps[i]
            if isinstance(catName, list):
                catName = catName[0]
            rc = self.ss.tw_steps.rowCount()
            self.ss.tw_steps.insertRow(rc)
            abrItem = QTableWidgetItem(i)
            self.ss.tw_steps.setItem(rc, 0, abrItem)
            stepItem = QTableWidgetItem(catName)
            self.ss.tw_steps.setItem(rc, 1, stepItem)

        self.core.callback(name="onStepDlgOpen", types=["custom"], args=[self, self.ss])

        result = self.ss.exec_()

        if result != 1:
            return False

        steps = []
        for i in self.ss.tw_steps.selectedItems():
            if i.column() == 0:
                steps.append(i.text())

        self.createSteps(entity, steps, createCat=self.ss.chb_category.isChecked())

    @err_catcher(name=__name__)
    def createSteps(self, entity, steps, createCat=True):
        if len(steps) > 0:
            if entity == "asset":
                basePath = self.core.getEntityPath(entity="step", asset=self.curAsset)
                navData = {
                    "entity": "asset",
                    "basePath": self.curAsset,
                }
            elif entity == "shot":
                basePath = self.core.getEntityPath(entity="step", shot=self.cursShots)
                navData = {
                    "entity": "shot",
                    "entityName": self.cursShots,
                }
            else:
                return

            createdDirs = []

            for i in steps:
                dstname = os.path.join(basePath, i)
                result = self.core.entities.createStep(i, entity, stepPath=dstname, createCat=createCat)
                if result:
                    createdDirs.append(i)
                    navData["step"] = i

            if createdDirs:
                if entity == "asset":
                    self.curaStep = createdDirs[-1]
                    self.refreshAHierarchy()
                    self.navigate(data=navData)
                elif entity == "shot":
                    self.cursStep = createdDirs[-1]
                    self.refreshsStep()
                    self.navigate(data=navData)

    @err_catcher(name=__name__)
    def refreshAHierarchy(self, load=False):
        self.tw_aHierarchy.blockSignals(True)
        self.tw_aHierarchy.clear()
        self.tw_aHierarchy.blockSignals(False)

        if self.e_assetSearch.isVisible():
            assets, folders = self.core.entities.getAssetPaths(returnFolders=True, depth=0)
            filterStr = self.e_assetSearch.text()
            self.filteredAssets = []
            self.filteredAssets += self.core.entities.filterAssets(assets, filterStr)
            self.filteredAssets += self.core.entities.filterAssets(folders, filterStr)

        self.refreshAssets()
        self.tw_aHierarchy.resizeColumnToContents(0)

        if self.tw_aHierarchy.topLevelItemCount() > 0 and not self.e_assetSearch.isVisible():
            self.tw_aHierarchy.setCurrentItem(self.tw_aHierarchy.topLevelItem(0))
        else:
            self.curAsset = None
            self.refreshAStep()
            self.refreshAssetinfo()

    @err_catcher(name=__name__)
    def refreshAssets(self, path=None, parent=None, refreshChildren=True):
        if not path and parent:
            path = parent.text(1)

        assets, folders = self.core.entities.getAssetPaths(path=path, returnFolders=True, depth=1)

        assets = self.core.entities.filterOmittedAssets(assets)
        folders = self.core.entities.filterOmittedAssets(folders)

        if self.e_assetSearch.isVisible():
            filteredAssets = []
            for asset in assets:
                for fasset in self.filteredAssets:
                    if (asset == fasset or asset + os.sep in fasset) and asset not in filteredAssets:
                        filteredAssets.append(asset)

            assets = filteredAssets

            filteredFolders = []
            for folder in folders:
                for fasset in self.filteredAssets:
                    if (folder == fasset or folder + os.sep in fasset) and folder not in filteredFolders:
                        filteredFolders.append(folder)

            folders = filteredFolders

        itemPaths = copy.copy(assets)
        itemPaths += folders
        for path in sorted(itemPaths):
            if path in assets:
                pathType = "asset"
            else:
                pathType = "folder"
            self.addAssetItem(path, itemType=pathType, parent=parent, refreshItem=refreshChildren)

    @err_catcher(name=__name__)
    def addAssetItem(self, path, itemType, parent=None, refreshItem=True):
        name = os.path.basename(path)
        item = QTreeWidgetItem([name, path, itemType])
        if parent:
            parent.addChild(item)
        else:
            self.tw_aHierarchy.addTopLevelItem(item)
        if refreshItem:
            self.refreshAItem(item)

    @err_catcher(name=__name__)
    def refreshAItem(self, item):
        item.takeChildren()
        path = item.text(1)
        itemType = item.text(2)

        if itemType == "asset":
            item.setText(2, "asset")
        else:
            item.setText(2, "folder")
            self.refreshAssets(path=path, parent=item, refreshChildren=False)

        if itemType == "asset":
            iFont = item.font(0)
            iFont.setBold(True)
            item.setFont(0, iFont)

        if path in self.aExpanded or (self.e_assetSearch.isVisible() and self.e_assetSearch.text()):
            item.setExpanded(True)

    @err_catcher(name=__name__)
    def hItemExpanded(self, item):
        self.adclick = False
        if (
            item.text(1) not in self.aExpanded
            and not (self.e_assetSearch.isVisible() and self.e_assetSearch.text())
        ):
            self.aExpanded.append(item.text(1))

        mods = QApplication.keyboardModifiers()
        if mods == Qt.ControlModifier:
            self.setItemChildrenExpanded(item)

        for childnum in range(item.childCount()):
            self.refreshAItem(item.child(childnum))

    @err_catcher(name=__name__)
    def hItemCollapsed(self, item):
        self.adclick = False
        if item.text(1) in self.aExpanded:
            self.aExpanded.remove(item.text(1))

        mods = QApplication.keyboardModifiers()
        if mods == Qt.ControlModifier:
            self.setItemChildrenExpanded(item, expanded=False)

    @err_catcher(name=__name__)
    def setWidgetItemsExpanded(self, widget, expanded=True):
        for idx in range(widget.topLevelItemCount()):
            item = widget.topLevelItem(idx)
            item.setExpanded(expanded)
            self.setItemChildrenExpanded(item, expanded=expanded, recursive=True)

    @err_catcher(name=__name__)
    def setItemChildrenExpanded(self, item, expanded=True, recursive=False):
        for childIdx in range(item.childCount()):
            if recursive:
                self.setItemChildrenExpanded(item.child(childIdx), expanded=expanded, recursive=True)
            item.child(childIdx).setExpanded(expanded)

    @err_catcher(name=__name__)
    def refreshAStep(self, cur=None, prev=None):
        self.lw_aPipeline.blockSignals(True)
        self.lw_aPipeline.clear()
        self.lw_aPipeline.blockSignals(False)

        if not self.curAsset:
            self.curaStep = None
            self.refreshaCat()
            return

        steps = self.core.entities.getSteps(asset=self.curAsset)

        for s in steps:
            sItem = QListWidgetItem(s)
            self.lw_aPipeline.addItem(sItem)

        if self.lw_aPipeline.count() > 0:
            self.lw_aPipeline.setCurrentRow(0)
        else:
            self.curaStep = None
            self.refreshaCat()

    @err_catcher(name=__name__)
    def refreshaCat(self):
        self.lw_aCategory.blockSignals(True)
        self.lw_aCategory.clear()
        self.lw_aCategory.blockSignals(False)

        if not self.curAsset or not self.curaStep:
            if (
                self.core.compareVersions(self.core.projectVersion, "v1.2.1.6")
                == "lower"
            ):
                self.curaCat = "category"
            else:
                self.curaCat = None

            self.refreshAFile()
            return

        if (
                self.core.compareVersions(self.core.projectVersion, "v1.2.1.6")
                == "lower"
        ):
            cats = []
        else:
            cats = self.core.entities.getCategories(asset=self.curAsset, step=self.curaStep)

        for c in cats:
            aItem = QListWidgetItem(c)
            self.lw_aCategory.addItem(aItem)

        if self.lw_aCategory.count() > 0:
            self.lw_aCategory.setCurrentRow(0)
        else:
            if (
                self.core.compareVersions(self.core.projectVersion, "v1.2.1.6")
                == "lower"
            ):
                self.curaCat = "category"
            else:
                self.curaCat = None

            self.refreshAFile()

    @err_catcher(name=__name__)
    def refreshAFile(self, cur=None, prev=None):
        twSorting = [
            self.tw_aFiles.horizontalHeader().sortIndicatorSection(),
            self.tw_aFiles.horizontalHeader().sortIndicatorOrder(),
        ]
        self.tw_aFiles.setSortingEnabled(False)

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

        if self.curAsset and self.curaStep and self.curaCat:
            appfilter = []

            for i in self.appFilters:
                chbName = "chb_aShow%s" % self.appFilters[i]["shortName"]
                if getattr(self, chbName).isChecked():
                    appfilter += self.appFilters[i]["formats"]

            scenefiles = self.core.entities.getScenefiles(asset=self.curAsset, step=self.curaStep, category=self.curaCat, extensions=appfilter)

            for i in scenefiles:
                row = []
                fname = self.core.getScenefileData(i)

                publicFile = self.core.useLocalFiles and i.startswith(self.aBasePath)

                if pVersion == 2:
                    item = QStandardItem(unicode("█", "utf-8"))
                else:
                    item = QStandardItem("█")
                item.setFont(QFont("SansSerif", 100))
                item.setFlags(~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
                item.setData(i, Qt.UserRole)

                colorVals = [128, 128, 128]
                if fname["extension"] in self.core.appPlugin.sceneFormats:
                    colorVals = self.core.appPlugin.appColor
                else:
                    for k in self.core.unloadedAppPlugins.values():
                        if fname["extension"] in k.sceneFormats:
                            colorVals = k.appColor

                item.setForeground(QColor(colorVals[0], colorVals[1], colorVals[2]))

                row.append(item)
                item = QStandardItem(fname["version"])
                item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
                row.append(item)
                if fname["comment"] == "nocomment":
                    item = QStandardItem("")
                else:
                    item = QStandardItem(fname["comment"])
                item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
                row.append(QStandardItem(item))
                cdate = self.core.getFileModificationDate(i)
                item = QStandardItem(str(cdate))
                item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
                item.setData(
                    QDateTime.fromString(cdate, "dd.MM.yy,  hh:mm:ss").addYears(100), 0
                )
                #   item.setToolTip(cdate)
                row.append(item)
                item = QStandardItem(fname["user"])
                item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
                row.append(item)

                if publicFile:
                    for k in row[1:]:
                        iFont = k.font()
                        iFont.setBold(True)
                        k.setFont(iFont)
                        k.setForeground(self.publicColor)

                model.appendRow(row)

        self.tw_aFiles.setModel(model)
        if psVersion == 1:
            self.tw_aFiles.horizontalHeader().setResizeMode(0, QHeaderView.Fixed)
            self.tw_aFiles.horizontalHeader().setResizeMode(2, QHeaderView.Stretch)
        else:
            self.tw_aFiles.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
            self.tw_aFiles.horizontalHeader().setSectionResizeMode(
                2, QHeaderView.Stretch
            )

        self.tw_aFiles.resizeColumnsToContents()
        self.tw_aFiles.horizontalHeader().setMinimumSectionSize(10)
        self.tw_aFiles.setColumnWidth(0, 10 * self.core.uiScaleFactor)
        self.tw_aFiles.setColumnWidth(1, 100 * self.core.uiScaleFactor)
        self.tw_aFiles.setColumnWidth(3, 200 * self.core.uiScaleFactor)
        self.tw_aFiles.setColumnWidth(4, 100 * self.core.uiScaleFactor)
        self.tw_aFiles.sortByColumn(twSorting[0], twSorting[1])
        self.tw_aFiles.setSortingEnabled(True)

    @err_catcher(name=__name__)
    def Assetclicked(self, item):
        if (
            item is not None
            and item.childCount() == 0
            and item.text(0) != None
            and item.text(2) == "asset"
        ):
            self.curAsset = item.text(1)
        else:
            self.curAsset = None

        self.refreshAssetinfo()
        self.refreshAStep()

        if self.gb_renderings.isVisible() and self.chb_autoUpdate.isChecked():
            self.updateTasks()

    @err_catcher(name=__name__)
    def aPipelineclicked(self, current, prev):
        if current:
            self.curaStep = current.text()
        else:
            self.curaStep = None

        self.refreshaCat()

    @err_catcher(name=__name__)
    def aCatclicked(self, current, prev):
        if self.core.compareVersions(self.core.projectVersion, "v1.2.1.6") == "lower":
            self.curaCat = "category"

        elif current:
            self.curaCat = current.text()

        else:
            self.curaCat = None

        self.refreshAFile()

    @err_catcher(name=__name__)
    def refreshAssetinfo(self):
        pmap = None

        if self.curAsset:
            assetName = self.core.entities.getAssetNameFromPath(self.curAsset)
            assetFile = os.path.join(
                os.path.dirname(self.core.prismIni), "Assetinfo", "assetInfo.yml"
            )

            description = "< no description >"

            assetInfos = self.core.getConfig(configPath=assetFile)
            if not assetInfos:
                assetInfos = {}

            if assetName in assetInfos and "description" in assetInfos[assetName]:
                description = assetInfos[assetName]["description"]

            imgPath = self.core.entities.getEntityPreviewPath("asset", assetName)

            if os.path.exists(imgPath):
                pm = self.core.media.getPixmapFromPath(imgPath)
                if pm.width() > 0 and pm.height() > 0:
                    if (pm.width() / float(pm.height())) > 1.7778:
                        pmap = pm.scaledToWidth(self.shotPrvXres)
                    else:
                        pmap = pm.scaledToHeight(self.shotPrvYres)
        else:
            curItem = self.tw_aHierarchy.currentItem()
            if not curItem:
                description = "No asset selected"
            else:
                description = "%s selected" % (curItem.text(2)[0].upper() + curItem.text(2)[1:])

        if pmap is None:
            pmap = self.emptypmapPrv

        self.l_aDescription.setText(description)
        self.l_assetPreview.setMinimumSize(pmap.width(), pmap.height())
        self.l_assetPreview.setPixmap(pmap)

    @err_catcher(name=__name__)
    def refreshShots(self):
        self.lw_sPipeline.blockSignals(True)
        self.tw_sShot.clear()
        self.lw_sPipeline.blockSignals(False)

        searchFilter = ""
        if self.e_shotSearch.isVisible():
            searchFilter = self.e_shotSearch.text()

        sequences, shots = self.core.entities.getShots(searchFilter=searchFilter)

        if "" in sequences and "no sequence" not in sequences:
            sequences.append("no sequence")

        for seqName in sequences:
            if not seqName:
                continue

            seqItem = QTreeWidgetItem([seqName, seqName + self.core.sequenceSeparator])
            self.tw_sShot.addTopLevelItem(seqItem)
            if seqName in self.sExpanded or (self.e_shotSearch.isVisible() and self.e_shotSearch.text()):
                seqItem.setExpanded(True)

        for i in shots:
            for k in range(self.tw_sShot.topLevelItemCount()):
                tlItem = self.tw_sShot.topLevelItem(k)
                seqName = i[0]
                if not seqName:
                    seqName = "no sequence"

                if tlItem.text(0) == seqName:
                    seqItem = tlItem

            sItem = QTreeWidgetItem([i[1], i[2]])
            sItem.setData(0, Qt.UserRole, i[3])
            seqItem.addChild(sItem)

        self.tw_sShot.resizeColumnToContents(0)

        if self.tw_sShot.topLevelItemCount() > 0:
            if self.tw_sShot.topLevelItem(0).isExpanded():
                self.tw_sShot.setCurrentItem(self.tw_sShot.topLevelItem(0).child(0))
            else:
                self.tw_sShot.setCurrentItem(self.tw_sShot.topLevelItem(0))
        else:
            self.cursShots = None
            self.refreshsStep()
            self.refreshShotinfo()

    @err_catcher(name=__name__)
    def sItemCollapsed(self, item):
        if self.e_shotSearch.isVisible() and self.e_shotSearch.text():
            return

        self.sdclick = False
        exp = item.isExpanded()

        if exp:
            if item.text(0) not in self.sExpanded:
                self.sExpanded.append(item.text(0))
        else:
            if item.text(0) in self.sExpanded:
                self.sExpanded.remove(item.text(0))

    @err_catcher(name=__name__)
    def refreshsStep(self, cur=None, prev=None):
        self.lw_sPipeline.blockSignals(True)
        self.lw_sPipeline.clear()
        self.lw_sPipeline.blockSignals(False)

        if not self.cursShots:
            self.cursStep = None
            self.refreshsCat()
            return

        steps = self.core.entities.getSteps(shot=self.cursShots)

        for s in steps:
            sItem = QListWidgetItem(s)
            self.lw_sPipeline.addItem(sItem)

        if self.lw_sPipeline.count() > 0:
            self.lw_sPipeline.setCurrentRow(0)
        else:
            self.cursStep = None
            self.refreshsCat()

    @err_catcher(name=__name__)
    def refreshsCat(self):
        self.lw_sCategory.blockSignals(True)
        self.lw_sCategory.clear()
        self.lw_sCategory.blockSignals(False)

        if not self.cursStep:
            self.cursCat = None
            self.refreshSFile()
            return

        cats = self.core.entities.getCategories(shot=self.cursShots, step=self.cursStep)

        for c in cats:
            sItem = QListWidgetItem(c)
            self.lw_sCategory.addItem(sItem)

        if self.lw_sCategory.count() > 0:
            self.lw_sCategory.setCurrentRow(0)
        else:
            self.cursCat = None
            self.refreshSFile()

    @err_catcher(name=__name__)
    def refreshSFile(self, parm=None):
        twSorting = [
            self.tw_sFiles.horizontalHeader().sortIndicatorSection(),
            self.tw_sFiles.horizontalHeader().sortIndicatorOrder(),
        ]
        self.tw_sFiles.setSortingEnabled(False)

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
        # example filename: shot_0010_mod_main_v0002_details-added_rfr_.max

        if self.cursCat is not None:
            appfilter = []

            for i in self.appFilters:
                chbName = "chb_sShow%s" % self.appFilters[i]["shortName"]
                if getattr(self, chbName).isChecked():
                    appfilter += self.appFilters[i]["formats"]

            scenefiles = self.core.entities.getScenefiles(shot=self.cursShots, step=self.cursStep, category=self.cursCat, extensions=appfilter)

            for i in scenefiles:
                row = []
                fname = self.core.getScenefileData(i)

                publicFile = self.core.useLocalFiles and i.startswith(self.sBasePath)

                if pVersion == 2:
                    item = QStandardItem(unicode("█", "utf-8"))
                else:
                    item = QStandardItem("█")
                item.setFont(QFont("SansSerif", 100))
                item.setFlags(~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
                item.setData(i, Qt.UserRole)

                colorVals = [128, 128, 128]
                if fname["extension"] in self.core.appPlugin.sceneFormats:
                    colorVals = self.core.appPlugin.appColor
                else:
                    for k in self.core.unloadedAppPlugins.values():
                        if fname["extension"] in k.sceneFormats:
                            colorVals = k.appColor

                item.setForeground(QColor(colorVals[0], colorVals[1], colorVals[2]))

                row.append(item)
                item = QStandardItem(fname["version"])
                item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
                row.append(item)
                if fname["comment"] == "nocomment":
                    item = QStandardItem("")
                else:
                    item = QStandardItem(fname["comment"])
                #   self.tw_sFiles.setItemDelegate(ColorDelegate(self.tw_sFiles))
                item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
                row.append(item)
                cdate = self.core.getFileModificationDate(i)
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

                if publicFile:
                    for k in row[1:]:
                        iFont = k.font()
                        iFont.setBold(True)
                        k.setFont(iFont)
                        k.setForeground(self.publicColor)

                model.appendRow(row)

        self.tw_sFiles.setModel(model)
        if psVersion == 1:
            self.tw_sFiles.horizontalHeader().setResizeMode(0, QHeaderView.Fixed)
            self.tw_sFiles.horizontalHeader().setResizeMode(2, QHeaderView.Stretch)
        else:
            self.tw_sFiles.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
            self.tw_sFiles.horizontalHeader().setSectionResizeMode(
                2, QHeaderView.Stretch
            )

        self.tw_sFiles.resizeColumnsToContents()
        self.tw_sFiles.horizontalHeader().setMinimumSectionSize(10)
        self.tw_sFiles.setColumnWidth(0, 10 * self.core.uiScaleFactor)
        self.tw_sFiles.setColumnWidth(1, 100 * self.core.uiScaleFactor)
        self.tw_sFiles.setColumnWidth(3, 200 * self.core.uiScaleFactor)
        self.tw_sFiles.setColumnWidth(4, 100 * self.core.uiScaleFactor)
        self.tw_sFiles.sortByColumn(twSorting[0], twSorting[1])
        self.tw_sFiles.setSortingEnabled(True)

    @err_catcher(name=__name__)
    def sShotclicked(self, item):
        if item is not None and item.text(0) != None and item.text(0) != "no sequence":
            self.cursShots = item.text(1)
        else:
            self.cursShots = None

        self.refreshShotinfo()
        self.refreshsStep()

        if self.gb_renderings.isVisible() and self.chb_autoUpdate.isChecked():
            self.updateTasks()

    @err_catcher(name=__name__)
    def sPipelineclicked(self, current, prev):
        if current:
            self.cursStep = current.text()
        else:
            self.cursStep = None

        self.refreshsCat()

    @err_catcher(name=__name__)
    def sCatclicked(self, current, prev):
        if current:
            self.cursCat = current.text()
        else:
            self.cursCat = None

        self.refreshSFile()

    @err_catcher(name=__name__)
    def refreshShotinfo(self):
        pmap = None

        if self.cursShots is not None:
            startFrame = "?"
            endFrame = "?"

            shotRange = self.core.entities.getShotRange(self.cursShots)
            if shotRange:
                startFrame, endFrame = shotRange

            shotName, seqName = self.core.entities.splitShotname(self.cursShots)
            if not shotName and seqName:
                rangeText = "Sequence selected"
                entityType = "sequence"
                entityName = seqName
            else:
                rangeText = "Framerange:    %s - %s" % (startFrame, endFrame)
                entityType = "shot"
                entityName = self.cursShots

            imgPath = self.core.entities.getEntityPreviewPath(entityType, entityName)

            if os.path.exists(imgPath):
                pm = self.core.media.getPixmapFromPath(imgPath)
                if pm.width() > 0 and pm.height() > 0:
                    if (pm.width() / float(pm.height())) > 1.7778:
                        pmap = pm.scaledToWidth(self.shotPrvXres)
                    else:
                        pmap = pm.scaledToHeight(self.shotPrvYres)
        else:
            rangeText = "No shot selected"

        if pmap is None:
            pmap = self.emptypmapPrv

        self.l_framerange.setText(rangeText)
        self.l_shotPreview.setMinimumSize(pmap.width(), pmap.height())
        self.l_shotPreview.setPixmap(pmap)

    @err_catcher(name=__name__)
    def rclEntityPreview(self, pos, entity):
        rcmenu = QMenu(self)

        if entity == "asset":
            if not self.curAsset:
                return

            exp = QAction("Edit asset description", self)
            exp.triggered.connect(lambda: self.editAsset(self.curAsset))
            rcmenu.addAction(exp)

            copAct = QAction("Capture assetpreview", self)
            copAct.triggered.connect(
                lambda: self.captureEntityPreview("asset", self.curAsset)
            )
            rcmenu.addAction(copAct)
            clipAct = QAction("Paste assetpreview from clipboard", self)
            clipAct.triggered.connect(
                lambda: self.PasteEntityPreviewFromClipboard("asset", self.curAsset)
            )
            rcmenu.addAction(clipAct)
        else:
            shotName, seqName = self.core.entities.splitShotname(self.cursShots)
            if shotName:
                exp = QAction("Edit shot settings", self)
                exp.triggered.connect(lambda: self.editShot(self.cursShots))
                rcmenu.addAction(exp)

                copAct = QAction("Capture shotpreview", self)
                copAct.triggered.connect(
                    lambda: self.captureEntityPreview("shot", self.cursShots)
                )
                rcmenu.addAction(copAct)
                clipAct = QAction("Paste shotpreview from clipboard", self)
                clipAct.triggered.connect(
                    lambda: self.PasteEntityPreviewFromClipboard("shot", self.cursShots)
                )
                rcmenu.addAction(clipAct)
            else:
                copAct = QAction("Capture sequencepreview", self)
                copAct.triggered.connect(
                    lambda: self.captureEntityPreview("sequence", seqName)
                )
                rcmenu.addAction(copAct)
                clipAct = QAction("Paste sequencepreview from clipboard", self)
                clipAct.triggered.connect(
                    lambda: self.PasteEntityPreviewFromClipboard("sequence", seqName)
                )
                rcmenu.addAction(clipAct)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def captureEntityPreview(self, entity, entityname):
        if entity == "asset":
            entityname = os.path.basename(entityname)
            refresh = self.refreshAssetinfo
        elif entity in ["shot", "sequence"]:
            refresh = self.refreshShotinfo

        from PrismUtils import ScreenShot

        previewImg = ScreenShot.grabScreenArea(self.core)

        if previewImg:
            self.core.entities.setEntityPreview(entity, entityname, previewImg)
            refresh()

    @err_catcher(name=__name__)
    def PasteEntityPreviewFromClipboard(self, entity, entityname):
        pmap = self.core.media.getPixmapFromClipboard()
        if not pmap:
            self.core.popup("No image in clipboard.")
            return

        if entity == "asset":
            entityname = os.path.basename(entityname)
            refresh = self.refreshAssetinfo
        elif entity in ["shot", "sequence"]:
            refresh = self.refreshShotinfo

        self.core.entities.setEntityPreview(entity, entityname, pmap, width=self.shotPrvXres, height=self.shotPrvYres)
        refresh()

    @err_catcher(name=__name__)
    def editAsset(self, assetPath=None):
        if not assetPath:
            return

        assetName = self.core.entities.getAssetNameFromPath(assetPath)

        descriptionDlg = EnterText.EnterText()
        self.core.parentWindow(descriptionDlg)
        descriptionDlg.setWindowTitle("Enter description")
        descriptionDlg.l_info.setText("Description:")
        descriptionDlg.te_text.setPlainText(self.l_aDescription.text())

        c = descriptionDlg.te_text.textCursor()
        c.setPosition(0)
        c.setPosition(len(self.l_aDescription.text()), QTextCursor.KeepAnchor)
        descriptionDlg.te_text.setTextCursor(c)

        result = descriptionDlg.exec_()

        if result:
            description = descriptionDlg.te_text.toPlainText()
            self.l_aDescription.setText(description)

            assetFile = os.path.join(
                os.path.dirname(self.core.prismIni), "Assetinfo", "assetInfo.yml"
            )
            assetInfos = self.core.getConfig(configPath=assetFile)
            if not assetInfos:
                assetInfos = {}

            if assetName not in assetInfos:
                assetInfos[assetName] = {}

            assetInfos[assetName]["description"] = description

            self.core.writeYaml(assetFile, assetInfos)

    @err_catcher(name=__name__)
    def editShot(self, shotName=None):
        sequs = []
        for i in range(self.tw_sShot.topLevelItemCount()):
            sName = self.tw_sShot.topLevelItem(i).text(0)
            if sName != "no sequence":
                sequs.append(sName)

        if not shotName:
            shotName, seqName = self.core.entities.splitShotname(self.cursShots)
            shotName = seqName + self.core.sequenceSeparator

        try:
            del sys.modules["EditShot"]
        except:
            pass

        import EditShot

        self.es = EditShot.EditShot(core=self.core, shotName=shotName, sequences=sequs)

        result = self.core.callback(
            name="onShotDlgOpen", types=["custom"], args=[self, self.es, shotName]
        )

        if False in result:
            return

        result = self.es.exec_()

        if result != 1 or self.es.shotName is None:
            return

        if shotName is None:
            return

        self.refreshShots()

        shotName, seqName = self.core.entities.splitShotname(self.es.shotName)
        if not seqName:
            seqName = "no sequence"

        for i in range(self.tw_sShot.topLevelItemCount()):
            sItem = self.tw_sShot.topLevelItem(i)
            if sItem.text(0) == seqName:
                sItem.setExpanded(True)
                for k in range(sItem.childCount()):
                    shotItem = sItem.child(k)
                    if shotItem.text(0) == shotName:
                        self.tw_sShot.setCurrentItem(shotItem)
                        break
                else:
                    self.tw_sShot.setCurrentItem(sItem)

    @err_catcher(name=__name__)
    def createShot(self, shotName, frameRange=None):
        result = self.core.entities.createEntity("shot", shotName, frameRange=frameRange)

        if self.core.uiAvailable:
            self.refreshShots()
            shotName, seqName = self.core.entities.splitShotname(shotName)
            if not seqName:
                seqName = "no sequence"

            for i in range(self.tw_sShot.topLevelItemCount()):
                sItem = self.tw_sShot.topLevelItem(i)
                if sItem.text(0) == seqName:
                    sItem.setExpanded(True)
                    for k in range(sItem.childCount()):
                        shotItem = sItem.child(k)
                        if shotItem.text(0) == shotName:
                            self.tw_sShot.setCurrentItem(shotItem)

        return result

    @err_catcher(name=__name__)
    def setRecent(self):
        model = QStandardItemModel()

        model.setHorizontalHeaderLabels(
            [
                "",
                self.tableColumnLabels["Name"],
                self.tableColumnLabels["Step"],
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

            if fname["entity"] == "invalid":
                continue
            if os.path.exists(i):
                if pVersion == 2:
                    item = QStandardItem(unicode("█", "utf-8"))
                else:
                    item = QStandardItem("█")
                item.setFont(QFont("SansSerif", 100))
                item.setFlags(~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
                item.setData(i, Qt.UserRole)

                colorVals = [128, 128, 128]
                if fname["extension"] in self.core.appPlugin.sceneFormats:
                    colorVals = self.core.appPlugin.appColor
                else:
                    for k in self.core.unloadedAppPlugins.values():
                        if fname["extension"] in k.sceneFormats:
                            colorVals = k.appColor

                item.setForeground(QColor(colorVals[0], colorVals[1], colorVals[2]))

                row.append(item)
                if fname["entity"] == "asset":
                    item = QStandardItem(fname["entityName"])
                    item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
                    row.append(item)
                    item = QStandardItem(fname.get("step", ""))
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
                elif fname["entity"] == "shot":
                    item = QStandardItem(fname["entityName"])
                    item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
                    row.append(item)
                    item = QStandardItem(fname.get("step", ""))
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
        self.tw_recent.setColumnWidth(0, 10 * self.core.uiScaleFactor)
        #   self.tw_recent.setColumnWidth(2,40*self.core.uiScaleFactor)
        #   self.tw_recent.setColumnWidth(3,60*self.core.uiScaleFactor)
        #   self.tw_recent.setColumnWidth(6,50*self.core.uiScaleFactor)

        if psVersion == 1:
            self.tw_recent.horizontalHeader().setResizeMode(0, QHeaderView.Fixed)
        else:
            self.tw_recent.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)

    @err_catcher(name=__name__)
    def refreshCurrent(self):
        if self.tbw_browser.currentWidget().property("tabType") == "Assets":
            self.refreshAFile()
        elif self.tbw_browser.currentWidget().property("tabType") == "Shots":
            self.refreshSFile()
        elif self.tbw_browser.currentWidget().property("tabType") == "Recent":
            self.setRecent()

    @err_catcher(name=__name__)
    def triggerOpen(self, checked=False):
        self.core.setConfig("globals", "showonstartup", checked)

    @err_catcher(name=__name__)
    def triggerUpdates(self, checked=False):
        self.core.setConfig("globals", "check_import_versions", checked)

    @err_catcher(name=__name__)
    def triggerFrameranges(self, checked=False):
        self.core.setConfig("globals", "checkframeranges", checked)

    @err_catcher(name=__name__)
    def triggerCloseLoad(self, checked=False):
        self.core.setConfig("browser", self.closeParm, checked)

    @err_catcher(name=__name__)
    def triggerAutoplay(self, checked=False, mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        self.core.setConfig("browser", "autoplaypreview", checked)

        if "timeline" in mediaPlayback:
            if checked and mediaPlayback["timeline"].state() == QTimeLine.Paused:
                mediaPlayback["timeline"].setPaused(False)
            elif not checked and mediaPlayback["timeline"].state() == QTimeLine.Running:
                mediaPlayback["timeline"].setPaused(True)
        else:
            mediaPlayback["tlPaused"] = not checked

    @err_catcher(name=__name__)
    def triggerAssets(self, checked=False):
        if checked:
            self.tbw_browser.insertTab(
                self.tabOrder["Assets"]["order"],
                self.t_assets,
                self.tabLabels["Assets"],
            )
            if self.tbw_browser.count() == 1:
                self.tbw_browser.setVisible(True)
        else:
            self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_assets))
            if self.tbw_browser.count() == 0:
                self.tbw_browser.setVisible(False)

    @err_catcher(name=__name__)
    def triggerShots(self, checked=False):
        if checked:
            self.tbw_browser.insertTab(
                self.tabOrder["Shots"]["order"], self.t_shots, self.tabLabels["Shots"]
            )
            if self.tbw_browser.count() == 1:
                self.tbw_browser.setVisible(True)
        else:
            self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_shots))
            if self.tbw_browser.count() == 0:
                self.tbw_browser.setVisible(False)

    @err_catcher(name=__name__)
    def triggerRecent(self, checked=False):
        if checked:
            self.tbw_browser.insertTab(
                self.tabOrder["Recent"]["order"],
                self.t_recent,
                self.tabLabels["Recent"],
            )
            if self.tbw_browser.count() == 1:
                self.tbw_browser.setVisible(True)
        else:
            self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_recent))
            if self.tbw_browser.count() == 0:
                self.tbw_browser.setVisible(False)

    @err_catcher(name=__name__)
    def triggerRenderings(self, checked=False):
        if (
            self.tbw_browser.currentWidget()
            and self.tabOrder[self.tbw_browser.currentWidget().property("tabType")][
                "showRenderings"
            ]
        ):
            self.gb_renderings.setVisible(checked)

    @err_catcher(name=__name__)
    def createCatWin(self, tab, name, startText=""):
        if tab == "ah":
            mode = "assetHierarchy"
        elif tab == "ac":
            mode = "assetCategory"
        elif tab == "sc":
            mode = "shotCategory"
        else:
            mode = ""

        self.newItem = CreateItem.CreateItem(startText=startText, core=self.core, showType=tab == "ah", mode=mode)

        self.newItem.setModal(True)
        self.core.parentWindow(self.newItem)
        self.newItem.e_item.setFocus()
        self.newItem.setWindowTitle("Create " + name)
        nameLabel = "Name:" if name == "Entity" else name + " Name:"
        self.newItem.l_item.setText(nameLabel)
        self.newItem.accepted.connect(lambda: self.createCat(tab))

        if tab == "ah":
            self.core.callback(
                name="onAssetDlgOpen", types=["custom"], args=[self, self.newItem]
            )
        elif tab in ["ac", "sc"]:
            self.core.callback(
                name="onCategroyDlgOpen", types=["custom"], args=[self, self.newItem]
            )

        self.newItem.show()

    @err_catcher(name=__name__)
    def createCat(self, tab):
        self.activateWindow()
        self.itemName = self.newItem.e_item.text()

        if tab == "ah":
            curItem = self.tw_aHierarchy.currentItem()
            if curItem is None:
                path = self.aBasePath
            else:
                path = self.tw_aHierarchy.currentItem().text(1)
            refresh = self.refreshAHierarchy
            uielement = self.tw_aHierarchy
        elif tab == "ac":
            path = self.core.getEntityPath(asset=self.curAsset, step=self.curaStep)
            refresh = self.refreshaCat
            uielement = self.lw_aCategory
            self.curaCat = self.itemName
        elif tab == "sc":
            path = self.core.getEntityPath(shot=self.cursShots, step=self.cursStep)
            refresh = self.refreshsCat
            uielement = self.lw_sCategory
            self.cursCat = self.itemName

        if tab == "ah":
            assetPath = os.path.join(path, self.itemName)
            if self.newItem.rb_asset.isChecked():
                result = self.core.entities.createEntity("asset", assetPath, dialog=self.newItem)
            else:
                result = self.core.entities.createEntity("assetFolder", assetPath, dialog=self.newItem)
            dirName = result.get("entityPath", "")
        else:
            catPath = os.path.join(path, self.itemName)
            self.core.entities.createCategory(self.itemName, catPath)

        refresh()
        if tab == "ah":
            self.navigate(data={"entity": "asset", "basePath": dirName})
            if "createAsset" in self.newItem.postEvents:
                self.createCatWin("ah", "Entity")
            elif "createCategory" in self.newItem.postEvents:
                self.createStepWindow("a")
        else:
            for i in range(uielement.model().rowCount()):
                if uielement.model().index(i, 0).data() == self.itemName:
                    uielement.selectionModel().setCurrentIndex(
                        uielement.model().index(i, 0),
                        QItemSelectionModel.ClearAndSelect,
                    )

    @err_catcher(name=__name__)
    def createStepWindow(self, tab):
        if tab == "a":
            basePath = self.core.getEntityPath(entity="step", asset=self.curAsset)
        elif tab == "s":
            basePath = self.core.getEntityPath(entity="step", shot=self.cursShots)
        else:
            return

        steps = self.getSteps()
        steps = {
            validSteps: steps[validSteps]
            for validSteps in steps
            if not os.path.exists(os.path.join(basePath, validSteps))
        }

        self.getStep(steps, tab)

    @err_catcher(name=__name__)
    def getSteps(self):
        try:
            steps = self.core.getConfig(
                        "globals", "pipeline_steps", configPath=self.core.prismIni
                    )
        except:
            msgStr = "Could not read steps from configuration file.\nCheck this file for errors:\n\n%s" % self.core.prismIni
            self.core.popup(msgStr)
            return {}

        try:
            dict(steps)
        except:
            steps = {}

        return steps

    @err_catcher(name=__name__)
    def copyToGlobal(self, localPath, mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

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

            if "vidPrw" in mediaPlayback and not mediaPlayback["vidPrw"].closed:
                for i in range(6):
                    mediaPlayback["vidPrw"].close()
                    time.sleep(0.5)
                    if mediaPlayback["vidPrw"].closed:
                        break

            try:
                shutil.rmtree(localPath)
            except:
                msg = "Could not delete the local file. Probably it is used by another process."
                self.core.popup(msg)

            curTab = self.tbw_browser.currentWidget().property("tabType")
            curData = [
                curTab,
                self.cursShots,
                self.curRTask,
                self.curRVersion,
                self.curRLayer,
            ]
            self.updateTasks()
            self.showRender(
                curData[0],
                curData[1],
                curData[2],
                curData[3].replace(" (local)", ""),
                curData[4],
            )
        else:
            if not os.path.exists(os.path.dirname(dstPath)):
                os.makedirs(os.path.dirname(dstPath))

            self.core.copySceneFile(localPath, dstPath)

            self.refreshCurrent()

    @err_catcher(name=__name__)
    def editComment(self, filepath):
        data = self.core.getScenefileData(filepath)
        comment = data["comment"] if "comment" in data else ""

        dlg_ec = CreateItem.CreateItem(core=self.core,  startText=comment, showType=False, valueRequired=False)

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

        self.refreshCurrent()
        fileNameData = self.core.getScenefileData(newPath)
        self.navigate(data=fileNameData)

    @err_catcher(name=__name__)
    def omitEntity(self, eType, ePath):
        msgText = (
            'Are you sure you want to omit %s "%s"?\n\nThis will make the %s be ignored by Prism, but all scenefiles and renderings remain on the hard drive.'
            % (eType.lower(), ePath, eType.lower())
        )
        result = self.core.popupQuestion(msgText)

        if result == "Yes":
            self.core.entities.omitEntity(eType, ePath)

            if eType == "asset":
                self.refreshAHierarchy()
            elif eType == "shot":
                self.refreshShots()

    @err_catcher(name=__name__)
    def navigateToCurrent(self):
        fileName = self.core.getCurrentFileName()
        fileNameData = self.core.getScenefileData(fileName)

        self.navigate(fileNameData)

    @err_catcher(name=__name__)
    def navigate(self, data):
        # logger.debug("navigate to: %s" % data)
        if data["entity"] == "asset":
            self.showTab("Assets")

            itemPath = self.core.entities.getAssetRelPathFromPath(data.get("basePath", ""))
            hierarchy = itemPath.split(os.sep)
            hierarchy = [x for x in hierarchy if x != ""]
            if not hierarchy:
                return
            hItem = self.tw_aHierarchy.findItems(hierarchy[0], Qt.MatchExactly, 0)
            if len(hItem) == 0:
                return
            hItem = hItem[-1]

            if len(hierarchy) > 1:
                hItem.setExpanded(True)
                if hItem.text(1) not in self.aExpanded:
                    self.aExpanded.append(hItem.text(1))

                for idx, i in enumerate((hierarchy[1:])):
                    for k in range(hItem.childCount() - 1, -1, -1):
                        if hItem.child(k).text(0) == i:
                            hItem = hItem.child(k)
                            if len(hierarchy) > (idx + 2):
                                hItem.setExpanded(True)
                                if hItem.text(1) not in self.aExpanded:
                                    self.aExpanded.append(hItem.text(1))
                            break
                    else:
                        break

            self.tw_aHierarchy.setCurrentItem(hItem)

            if "step" in data:
                fItems = self.lw_aPipeline.findItems(data["step"], Qt.MatchExactly)
                if len(fItems) > 0:
                    self.lw_aPipeline.setCurrentItem(fItems[0])
                    if "category" in data:
                        fItems = self.lw_aCategory.findItems(data["category"], Qt.MatchExactly)
                        if len(fItems) > 0:
                            self.lw_aCategory.setCurrentItem(fItems[0])
                            if os.path.isabs(data.get("filename", "")):
                                for i in range(self.tw_aFiles.model().rowCount()):
                                    if data["filename"] == self.tw_aFiles.model().index(i, 0).data(
                                        Qt.UserRole
                                    ):
                                        idx = self.tw_aFiles.model().index(i, 0)
                                        self.tw_aFiles.selectRow(idx.row())
                                        break

        elif data["entity"] == "shot" and self.tw_sShot.topLevelItemCount() > 0:
            self.showTab("Shots")
            shotName = data.get("entityName", "")
            stepName = data.get("step", "")
            catName = data.get("category", "")

            shotName, seqName = self.core.entities.splitShotname(shotName)
            if not seqName:
                seqName = "no sequence"

            for i in range(self.tw_sShot.topLevelItemCount()):
                sItem = self.tw_sShot.topLevelItem(i)

                if sItem.text(0) == seqName:
                    if shotName == "":
                        self.tw_sShot.setCurrentItem(sItem)
                    else:
                        sItem.setExpanded(True)
                        for k in range(sItem.childCount()):
                            shotItem = sItem.child(k)
                            if shotItem.text(0) == shotName:
                                self.tw_sShot.setCurrentItem(shotItem)
                                break

            if stepName:
                for i in range(self.lw_sPipeline.model().rowCount()):
                    if stepName == self.lw_sPipeline.model().index(i, 0).data():
                        idx = self.lw_sPipeline.model().index(i, 0)
                        self.lw_sPipeline.selectionModel().setCurrentIndex(
                            idx, QItemSelectionModel.ClearAndSelect
                        )
                        break
                if catName:
                    for i in range(self.lw_sCategory.model().rowCount()):
                        if catName == self.lw_sCategory.model().index(i, 0).data():
                            idx = self.lw_sCategory.model().index(i, 0)
                            self.lw_sCategory.selectionModel().setCurrentIndex(
                                idx, QItemSelectionModel.ClearAndSelect
                            )
                            break

                    if os.path.isabs(data.get("filename", "")):
                        for i in range(self.tw_sFiles.model().rowCount()):
                            if data["filename"] == self.tw_sFiles.model().index(i, 0).data(
                                Qt.UserRole
                            ):
                                idx = self.tw_sFiles.model().index(i, 0)
                                self.tw_sFiles.selectRow(idx.row())
                                break

    @err_catcher(name=__name__)
    def showTab(self, tab):
        if tab != self.tbw_browser.currentWidget().property("tabType"):
            for i in range(self.tbw_browser.count()):
                if self.tbw_browser.widget(i).property("tabType") == tab:
                    idx = i
                    break
            else:
                return False

            self.tbw_browser.setCurrentIndex(idx)
            return True

    @err_catcher(name=__name__)
    def updateChanged(self, state):
        if state:
            self.updateTasks()

    @err_catcher(name=__name__)
    def refreshRender(self):
        curTab = self.tbw_browser.currentWidget().property("tabType")
        curData = [
            curTab,
            self.cursShots,
            self.curRTask,
            self.curRVersion,
            self.curRLayer,
        ]
        self.updateTasks()
        self.showRender(curData[0], curData[1], curData[2], curData[3], curData[4])

    @err_catcher(name=__name__)
    def getMediaTasks(self, entityName=None, entityType=None):
        mediaTasks = {"3d": [], "2d": [], "playblast": [], "external": []}

        if entityType is None:
            if not self.tbw_browser.currentWidget():
                self.renderBasePath = ""
                return mediaTasks

            entityType = self.tbw_browser.currentWidget().property("tabType")

        if entityType == "Assets":
            entityType = "asset"
            entityName = self.curAsset
            step = self.curaStep
            cat = self.curaCat
        elif entityType == "Shots":
            entityType = "shot"
            entityName = self.cursShots
            step = self.cursStep
            cat = self.cursCat
        else:
            self.renderBasePath = ""
            return

        self.renderBasePath = self.core.mediaProducts.getMediaProductBase(entityType, entityName, step=step, category=cat)
        mediaTasks = self.core.mediaProducts.getMediaProductNames(
            basepath=self.renderBasePath,
            entityType=entityType,
            entityName=entityName,
            step=step,
            category=cat
        )

        return mediaTasks

    @err_catcher(name=__name__)
    def updateTasks(self):
        self.renderRefreshEnabled = False

        self.curRTask = ""
        self.lw_task.clear()

        taskNames = []
        mediaTasks = self.getMediaTasks()
        if mediaTasks:
            for i in ["3d", "2d", "playblast", "external"]:
                taskNames += sorted(list({x[0] for x in mediaTasks[i]}))

        self.lw_task.addItems(taskNames)

        mIdx = self.lw_task.findItems("main", (Qt.MatchExactly & Qt.MatchCaseSensitive))
        if len(mIdx) > 0:
            self.lw_task.setCurrentItem(mIdx[0])
            self.curRTask = "main"
        elif self.lw_task.count() > 0:
            self.lw_task.setCurrentRow(0)

        self.renderRefreshEnabled = True

        self.updateVersions()

    @err_catcher(name=__name__)
    def updateVersions(self):
        if not self.renderRefreshEnabled:
            return

        self.curRVersion = ""
        self.lw_version.clear()

        if len(self.lw_task.selectedItems()) == 1:
            versions = self.core.mediaProducts.getMediaVersions(basepath=self.renderBasePath, product=self.curRTask)
            for version in sorted(versions, key=lambda x: x["label"], reverse=True):
                item = QListWidgetItem(version["label"])
                item.setData(Qt.UserRole, version["path"])
                versionInfoPath = self.getVersionInfoPath()
                vData = self.core.getConfig("information", configPath=versionInfoPath)
                if vData:
                    prjMngNames = [
                        [x, x.lower() + "-url"] for x in self.core.prjManagers
                    ]
                    for prjMngName in prjMngNames:
                        if prjMngName[1] in vData:
                            f = item.font()
                            f.setBold(True)
                            item.setFont(f)
                            break

                self.lw_version.addItem(item)

        self.renderRefreshEnabled = False
        self.lw_version.setCurrentRow(0)
        self.renderRefreshEnabled = True

        if self.lw_version.currentItem() is not None:
            self.curRVersion = self.lw_version.currentItem().text()

        self.updateLayers()

    @err_catcher(name=__name__)
    def updateLayers(self):
        if not self.renderRefreshEnabled:
            return

        self.curRLayer = ""
        self.cb_layer.clear()

        if len(self.lw_version.selectedItems()) == 1:
            foldercont = self.core.mediaProducts.getRenderLayers(self.renderBasePath, self.curRTask, self.curRVersion)
            for i in foldercont:
                self.cb_layer.addItem(i)

        self.cb_layer.blockSignals(True)
        bIdx = self.cb_layer.findText("beauty")
        if bIdx != -1:
            self.cb_layer.setCurrentIndex(bIdx)
        else:
            bIdx = self.cb_layer.findText("rgba")
            if bIdx != -1:
                self.cb_layer.setCurrentIndex(bIdx)
            else:
                self.cb_layer.setCurrentIndex(0)
        self.cb_layer.blockSignals(False)

        if self.cb_layer.currentIndex() != -1:
            self.curRLayer = self.cb_layer.currentText()

        self.updatePreview()

    @err_catcher(name=__name__)
    def getShotMediaPath(self):
        foldercont = [None, None, None]
        if (
            len(self.lw_task.selectedItems()) > 1
            or len(self.lw_version.selectedItems()) > 1
        ):
            mediaPlayback = self.mediaPlaybacks["shots"]

            mediaPlayback["l_info"].setText("Multiple items selected")
            mediaPlayback["l_info"].setToolTip("")
            mediaPlayback["l_date"].setText("")
            self.b_addRV.setEnabled(True)
            self.b_compareRV.setEnabled(True)
            self.b_combineVersions.setEnabled(True)
            return ["multiple", None, None]
        else:
            self.b_addRV.setEnabled(False)
            if len(self.compareStates) == 0:
                self.b_compareRV.setEnabled(False)
                self.b_combineVersions.setEnabled(False)

            foldercont = self.core.mediaProducts.getMediaProductPath(
                basepath=self.renderBasePath,
                product=self.curRTask,
                version=self.curRVersion,
                layer=self.curRLayer
            )

        return foldercont

    @err_catcher(name=__name__)
    def updatePreview(self, mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        if "timeline" in mediaPlayback:
            if mediaPlayback["timeline"].state() != QTimeLine.NotRunning:
                if mediaPlayback["timeline"].state() == QTimeLine.Running:
                    mediaPlayback["tlPaused"] = False
                elif mediaPlayback["timeline"].state() == QTimeLine.Paused:
                    mediaPlayback["tlPaused"] = True
                mediaPlayback["timeline"].stop()
        else:
            mediaPlayback["tlPaused"] = not self.actionAutoplay.isChecked()

        mediaPlayback["sl_preview"].setValue(0)
        mediaPlayback["prevCurImg"] = 0
        mediaPlayback["curImg"] = 0
        mediaPlayback["seq"] = []
        mediaPlayback["prvIsSequence"] = False

        QPixmapCache.clear()

        mediaBase, mediaFolders, mediaFiles = mediaPlayback["getMediaBase"]()

        if mediaBase != "multiple":
            if mediaBase is not None:
                mediaPlayback["basePath"] = mediaBase
                base = None
                for i in sorted(mediaFiles):
                    if os.path.splitext(i)[1] in [
                        ".jpg",
                        ".jpeg",
                        ".JPG",
                        ".png",
                        ".PNG",
                        ".tif",
                        ".tiff",
                        ".exr",
                        ".dpx",
                        ".mp4",
                        ".mov",
                        ".avi",
                    ]:
                        base = i
                        break

                if base is not None:
                    baseName, extension = os.path.splitext(base)
                    for i in sorted(mediaFiles):
                        if i.startswith(baseName[:-4]) and (i.endswith(extension)):
                            mediaPlayback["seq"].append(i)

                    if len(mediaPlayback["seq"]) > 1 and extension not in [
                        ".mp4",
                        ".mov",
                        ".avi",
                    ]:
                        mediaPlayback["prvIsSequence"] = True
                        try:
                            mediaPlayback["pstart"] = int(baseName[-4:])
                        except:
                            mediaPlayback["pstart"] = "?"

                        try:
                            mediaPlayback["pend"] = int(
                                os.path.splitext(
                                    mediaPlayback["seq"][len(mediaPlayback["seq"]) - 1]
                                )[0][-4:]
                            )
                        except:
                            mediaPlayback["pend"] = "?"

                    else:
                        mediaPlayback["prvIsSequence"] = False
                        mediaPlayback["seq"] = []
                        for i in mediaFiles:
                            if os.path.splitext(i)[1] in [
                                ".jpg",
                                ".jpeg",
                                ".JPG",
                                ".png",
                                ".PNG",
                                ".tif",
                                ".tiff",
                                ".exr",
                                ".dpx",
                                ".mp4",
                                ".mov",
                                ".avi",
                            ]:
                                mediaPlayback["seq"].append(i)

                    if not (
                        self.curRTask == ""
                        or self.curRVersion == ""
                        or len(mediaPlayback["seq"]) == 0
                    ):
                        self.b_addRV.setEnabled(True)

                    mediaPlayback["pduration"] = len(mediaPlayback["seq"])
                    imgPath = str(os.path.join(mediaBase, base))
                    if (
                        os.path.exists(imgPath)
                        and mediaPlayback["pduration"] == 1
                        and os.path.splitext(imgPath)[1] in [".mp4", ".mov", ".avi"]
                    ):
                        if os.stat(imgPath).st_size == 0:
                            mediaPlayback["vidPrw"] = "Error"
                        else:
                            try:
                                mediaPlayback["vidPrw"] = imageio.get_reader(
                                    imgPath, "ffmpeg"
                                )
                            except:
                                mediaPlayback["vidPrw"] = "Error"
                                logger.debug("failed to read videofile: %s" % traceback.format_exc())

                        self.updatePrvInfo(
                            imgPath,
                            vidReader=mediaPlayback["vidPrw"],
                            mediaPlayback=mediaPlayback,
                        )
                    else:
                        self.updatePrvInfo(imgPath, mediaPlayback=mediaPlayback)

                    if os.path.exists(imgPath):
                        mediaPlayback["timeline"] = QTimeLine(
                            mediaPlayback["pduration"] * 40, self
                        )
                        mediaPlayback["timeline"].setFrameRange(
                            0, mediaPlayback["pduration"] - 1
                        )
                        mediaPlayback["timeline"].setEasingCurve(QEasingCurve.Linear)
                        mediaPlayback["timeline"].setLoopCount(0)
                        mediaPlayback["timeline"].frameChanged.connect(
                            lambda x: self.changeImg(x, mediaPlayback=mediaPlayback)
                        )
                        QPixmapCache.setCacheLimit(2097151)
                        mediaPlayback["curImg"] = 0
                        mediaPlayback["timeline"].start()

                        if mediaPlayback["tlPaused"]:
                            mediaPlayback["timeline"].setPaused(True)
                            self.changeImg(mediaPlayback=mediaPlayback)
                        elif mediaPlayback["pduration"] < 3:
                            self.changeImg(mediaPlayback=mediaPlayback)

                        return True
                else:
                    self.updatePrvInfo(mediaPlayback=mediaPlayback)
            else:
                self.updatePrvInfo(mediaPlayback=mediaPlayback)

        mediaPlayback["l_preview"].setPixmap(self.emptypmap)
        mediaPlayback["sl_preview"].setEnabled(False)

    @err_catcher(name=__name__)
    def updatePrvInfo(self, prvFile="", vidReader=None, mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        if not os.path.exists(prvFile):
            mediaPlayback["l_info"].setText("No image found")
            mediaPlayback["l_info"].setToolTip("")
            mediaPlayback["l_date"].setText("")
            mediaPlayback["l_preview"].setToolTip("")
            return

        mediaPlayback["pwidth"], mediaPlayback["pheight"] = self.getMediaResolution(
            prvFile, vidReader=vidReader, setDuration=True, mediaPlayback=mediaPlayback
        )

        mediaPlayback["pformat"] = "*" + os.path.splitext(prvFile)[1]

        cdate = datetime.datetime.fromtimestamp(os.path.getmtime(prvFile))
        cdate = cdate.replace(microsecond=0)
        pdate = cdate.strftime("%d.%m.%y,  %H:%M:%S")

        mediaPlayback["sl_preview"].setEnabled(True)

        if mediaPlayback["pduration"] == 1:
            frStr = "frame"
        else:
            frStr = "frames"

        if mediaPlayback["prvIsSequence"]:
            infoStr = "%sx%s   %s   %s-%s (%s %s)" % (
                mediaPlayback["pwidth"],
                mediaPlayback["pheight"],
                mediaPlayback["pformat"],
                mediaPlayback["pstart"],
                mediaPlayback["pend"],
                mediaPlayback["pduration"],
                frStr,
            )
        elif len(mediaPlayback["seq"]) > 1:
            infoStr = "%s files %sx%s   %s   %s" % (
                mediaPlayback["pduration"],
                mediaPlayback["pwidth"],
                mediaPlayback["pheight"],
                mediaPlayback["pformat"],
                os.path.basename(prvFile),
            )
        elif os.path.splitext(mediaPlayback["seq"][0])[1] in [".mp4", ".mov", ".avi"]:
            if mediaPlayback["pwidth"] == "?":
                duration = "?"
                frStr = "frames"
            else:
                duration = mediaPlayback["pduration"]

            infoStr = "%sx%s   %s   %s %s" % (
                mediaPlayback["pwidth"],
                mediaPlayback["pheight"],
                mediaPlayback["seq"][0],
                duration,
                frStr,
            )
        else:
            infoStr = "%sx%s   %s" % (
                mediaPlayback["pwidth"],
                mediaPlayback["pheight"],
                os.path.basename(prvFile),
            )
            mediaPlayback["sl_preview"].setEnabled(False)

        mediaPlayback["l_info"].setText(infoStr)
        mediaPlayback["l_info"].setToolTip(infoStr)
        mediaPlayback["l_date"].setText(pdate)
        mediaPlayback["l_preview"].setToolTip(
            "Drag to drop the media to RV\nCtrl+Drag to drop the media to Nuke"
        )

    @err_catcher(name=__name__)
    def getMediaResolution(
        self, prvFile, vidReader=None, setDuration=False, mediaPlayback=None
    ):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        pwidth = 0
        pheight = 0

        if os.path.splitext(prvFile)[1] in [
            ".jpg",
            ".jpeg",
            ".JPG",
            ".png",
            ".PNG",
            ".tif",
            ".tiff",
        ]:
            size = self.core.media.getPixmapFromPath(prvFile).size()
            pwidth = size.width()
            pheight = size.height()
        elif os.path.splitext(prvFile)[1] in [".exr", ".dpx"]:
            pwidth = pheight = "?"
            if self.oiio:
                imgSpecs = self.oiio.ImageBuf(str(prvFile)).spec()
                pwidth = imgSpecs.full_width
                pheight = imgSpecs.full_height

        elif os.path.splitext(prvFile)[1] in [".mp4", ".mov", ".avi"]:
            if vidReader is None:
                if os.stat(prvFile).st_size == 0:
                    vidReader = "Error"
                else:
                    try:
                        vidReader = imageio.get_reader(prvFile, "ffmpeg")
                    except:
                        vidReader = "Error"
                        logger.debug("failed to read videofile: %s" % traceback.format_exc())

            if vidReader == "Error":
                pwidth = pheight = "?"
                if setDuration:
                    mediaPlayback["pduration"] = 1
            else:
                pwidth = vidReader._meta["size"][0]
                pheight = vidReader._meta["size"][1]
                if len(mediaPlayback["seq"]) == 1 and setDuration:
                    mediaPlayback["pduration"] = vidReader._meta["nframes"]

        if pwidth == 0 and pheight == 0:
            pwidth = pheight = "?"

        return pwidth, pheight

    @err_catcher(name=__name__)
    def createPMap(self, resx, resy):
        if resx == 300:
            imgFile = os.path.join(
                self.core.projectPath, "00_Pipeline", "Fallbacks", "noFileBig.jpg"
            )
        else:
            imgFile = os.path.join(
                self.core.projectPath, "00_Pipeline", "Fallbacks", "noFileSmall.jpg"
            )

        return self.core.media.getPixmapFromPath(imgFile)

    @err_catcher(name=__name__)
    def changeImg(self, frame=0, mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        pmsmall = QPixmap()
        if not QPixmapCache.find(("Frame" + str(mediaPlayback["curImg"])), pmsmall):
            if len(mediaPlayback["seq"]) == 1 and os.path.splitext(
                mediaPlayback["seq"][0]
            )[1] in [".mp4", ".mov", ".avi"]:
                curFile = mediaPlayback["seq"][0]
            else:
                curFile = mediaPlayback["seq"][mediaPlayback["curImg"]]
            fileName = os.path.join(mediaPlayback["basePath"], curFile)

            if os.path.splitext(curFile)[1] in [
                ".jpg",
                ".jpeg",
                ".JPG",
                ".png",
                ".PNG",
                ".tif",
                ".tiff",
            ]:
                pm = self.core.media.getPixmapFromPath(fileName)

                if pm.width() == 0 or pm.height() == 0:
                    pmsmall = self.core.media.getPixmapFromPath(
                        os.path.join(
                            self.core.projectPath,
                            "00_Pipeline",
                            "Fallbacks",
                            "%s.jpg" % os.path.splitext(curFile)[1][1:].lower(),
                        )
                    )
                elif (pm.width() / float(pm.height())) > 1.7778:
                    pmsmall = pm.scaledToWidth(self.renderResX)
                else:
                    pmsmall = pm.scaledToHeight(self.renderResY)
            elif os.path.splitext(curFile)[1] in [".exr", ".dpx"]:
                try:
                    qimg = QImage(self.renderResX, self.renderResY, QImage.Format_RGB16)

                    if self.oiio:
                        imgSrc = self.oiio.ImageBuf(str(fileName))
                        rgbImgSrc = self.oiio.ImageBuf()
                        self.oiio.ImageBufAlgo.channels(rgbImgSrc, imgSrc, (0, 1, 2))
                        imgWidth = rgbImgSrc.spec().full_width
                        imgHeight = rgbImgSrc.spec().full_height
                        xOffset = 0
                        yOffset = 0
                        if (imgWidth / float(imgHeight)) > 1.7778:
                            newImgWidth = self.renderResX
                            newImgHeight = self.renderResX / float(imgWidth) * imgHeight
                        else:
                            newImgHeight = self.renderResY
                            newImgWidth = self.renderResY / float(imgHeight) * imgWidth
                        imgDst = self.oiio.ImageBuf(
                            self.oiio.ImageSpec(
                                int(newImgWidth), int(newImgHeight), 3, self.oiio.UINT8
                            )
                        )
                        self.oiio.ImageBufAlgo.resample(imgDst, rgbImgSrc)
                        sRGBimg = self.oiio.ImageBuf()
                        self.oiio.ImageBufAlgo.pow(
                            sRGBimg, imgDst, (1.0 / 2.2, 1.0 / 2.2, 1.0 / 2.2)
                        )
                        bckImg = self.oiio.ImageBuf(
                            self.oiio.ImageSpec(
                                int(newImgWidth), int(newImgHeight), 3, self.oiio.UINT8
                            )
                        )
                        self.oiio.ImageBufAlgo.fill(bckImg, (0.5, 0.5, 0.5))
                        self.oiio.ImageBufAlgo.paste(bckImg, xOffset, yOffset, 0, 0, sRGBimg)
                        qimg = QImage(
                            int(newImgWidth), int(newImgHeight), QImage.Format_RGB16
                        )
                        for i in range(int(newImgWidth)):
                            for k in range(int(newImgHeight)):
                                rgb = qRgb(
                                    bckImg.getpixel(i, k)[0] * 255,
                                    bckImg.getpixel(i, k)[1] * 255,
                                    bckImg.getpixel(i, k)[2] * 255,
                                )
                                qimg.setPixel(i, k, rgb)
                        pmsmall = QPixmap.fromImage(qimg)

                    else:
                        raise RuntimeError("no image loader available")
                except:
                    pmsmall = self.core.media.getPixmapFromPath(
                        os.path.join(
                            self.core.projectPath,
                            "00_Pipeline",
                            "Fallbacks",
                            "%s.jpg" % os.path.splitext(curFile)[1][1:].lower(),
                        )
                    )
            elif os.path.splitext(curFile)[1] in [".mp4", ".mov", ".avi"]:
                try:
                    if len(mediaPlayback["seq"]) > 1:
                        imgNum = 0
                        vidFile = imageio.get_reader(fileName, "ffmpeg")
                    else:
                        imgNum = mediaPlayback["curImg"]
                        vidFile = mediaPlayback["vidPrw"]

                    image = vidFile.get_data(imgNum)
                    qimg = QImage(
                        image,
                        vidFile._meta["size"][0],
                        vidFile._meta["size"][1],
                        QImage.Format_RGB888,
                    )
                    pm = QPixmap.fromImage(qimg)
                    if (pm.width() / float(pm.height())) > 1.7778:
                        pmsmall = pm.scaledToWidth(self.renderResX)
                    else:
                        pmsmall = pm.scaledToHeight(self.renderResY)
                except:
                    pmsmall = self.core.media.getPixmapFromPath(
                        os.path.join(
                            self.core.projectPath,
                            "00_Pipeline",
                            "Fallbacks",
                            "%s.jpg" % os.path.splitext(curFile)[1][1:].lower(),
                        )
                    )
            else:
                return False

            QPixmapCache.insert(("Frame" + str(mediaPlayback["curImg"])), pmsmall)

        if not mediaPlayback["prvIsSequence"] and len(mediaPlayback["seq"]) > 1:
            curFile = mediaPlayback["seq"][mediaPlayback["curImg"]]
            fileName = os.path.join(mediaPlayback["basePath"], curFile)
            self.updatePrvInfo(fileName, mediaPlayback=mediaPlayback)

        mediaPlayback["l_preview"].setPixmap(pmsmall)
        if mediaPlayback["timeline"].state() == QTimeLine.Running:
            mediaPlayback["sl_preview"].setValue(
                int(100 * (mediaPlayback["curImg"] / float(mediaPlayback["pduration"])))
            )
        mediaPlayback["curImg"] += 1
        if mediaPlayback["curImg"] == mediaPlayback["pduration"]:
            mediaPlayback["curImg"] = 0

    @err_catcher(name=__name__)
    def taskClicked(self):
        sItems = self.lw_task.selectedItems()
        if len(sItems) == 1 and sItems[0].text() != self.curRTask:
            self.curRTask = sItems[0].text()
        else:
            self.curRTask = ""

        self.updateVersions()

    @err_catcher(name=__name__)
    def versionClicked(self):
        sItems = self.lw_version.selectedItems()
        if len(sItems) == 1 and sItems[0].text() != self.curRVersion:
            self.curRVersion = sItems[0].text()
        else:
            self.curRVersion = ""

        self.updateLayers()

    @err_catcher(name=__name__)
    def layerChanged(self, layer):
        layertext = self.cb_layer.itemText(layer)
        if layertext != "" and layer != self.curRLayer:
            self.curRLayer = layertext
            self.updatePreview()

    @err_catcher(name=__name__)
    def sliderChanged(self, val, mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        if mediaPlayback["seq"] != []:
            if (
                val != (mediaPlayback["prevCurImg"] + 1)
                or mediaPlayback["timeline"].state() != QTimeLine.Running
            ):
                mediaPlayback["prevCurImg"] = val
                mediaPlayback["curImg"] = int(
                    val / 99.0 * (mediaPlayback["pduration"] - 1)
                )

                if mediaPlayback["timeline"].state() != QTimeLine.Running:
                    self.changeImg(mediaPlayback=mediaPlayback)
            else:
                mediaPlayback["prevCurImg"] = val

    @err_catcher(name=__name__)
    def getVersionInfoPath(self):
        path = self.core.mediaProducts.getMediaVersionInfoPath(self.renderBasePath, self.curRTask, self.curRVersion)
        return path

    @err_catcher(name=__name__)
    def showVersionInfo(self, item=None):
        vInfo = "No information is saved with this version."

        path = self.getVersionInfoPath()

        if os.path.exists(path):
            vData = self.core.getConfig("information", configPath=path)

            vInfo = []
            for i in vData:
                i = i[0].upper() + i[1:]
                vInfo.append([i, vData[i]])

        if type(vInfo) == str or len(vInfo) == 0:
            self.core.popup(vInfo, severity="info")
            return

        infoDlg = QDialog()
        lay_info = QGridLayout()

        infoDlg.setWindowTitle("Versioninfo %s %s:" % (self.curRTask, self.curRVersion))
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
        infoDlg.resize(900 * self.core.uiScaleFactor, 200 * self.core.uiScaleFactor)

        infoDlg.exec_()

    @err_catcher(name=__name__)
    def showDependencies(self):
        path = self.getVersionInfoPath()

        if not os.path.exists(path):
            self.core.popup("No dependency information was saved with this version.")
            return

        self.core.dependencyViewer(path)

    @err_catcher(name=__name__)
    def showRender(self, tab, shot, task, version, layer):
        if tab != self.tbw_browser.currentWidget().property("tabType"):
            for i in range(self.tbw_browser.count()):
                if self.tbw_browser.widget(i).property("tabType") == tab:
                    idx = i
                    break
            else:
                return False

            self.tbw_browser.setCurrentIndex(idx)

        if tab == "Shots" and self.tw_sShot.currentIndex().data() != shot:
            for i in range(self.tw_sShot.model().rowCount()):
                if self.tw_sShot.model().index(i, 0).data() == shot:
                    self.tw_sShot.selectionModel().setCurrentIndex(
                        self.tw_sShot.model().index(i, 0),
                        QItemSelectionModel.ClearAndSelect,
                    )
                    break

        self.updateTasks()
        if (
            len(self.lw_task.findItems(task, (Qt.MatchExactly & Qt.MatchCaseSensitive)))
            != 0
        ):
            self.lw_task.setCurrentItem(
                self.lw_task.findItems(task, (Qt.MatchExactly & Qt.MatchCaseSensitive))[
                    0
                ]
            )
            if (
                len(
                    self.lw_version.findItems(
                        version, (Qt.MatchExactly & Qt.MatchCaseSensitive)
                    )
                )
                != 0
            ):
                self.lw_version.setCurrentItem(
                    self.lw_version.findItems(
                        version, (Qt.MatchExactly & Qt.MatchCaseSensitive)
                    )[0]
                )
                if self.cb_layer.findText(layer) != -1:
                    self.cb_layer.setCurrentIndex(self.cb_layer.findText(layer))
                    self.updatePreview()

    @err_catcher(name=__name__)
    def previewClk(self, event, mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        if mediaPlayback["seq"] != [] and event.button() == Qt.LeftButton:
            if (
                mediaPlayback["timeline"].state() == QTimeLine.Paused
                and not mediaPlayback["openRV"]
            ):
                mediaPlayback["timeline"].setPaused(False)
            else:
                if mediaPlayback["timeline"].state() == QTimeLine.Running:
                    mediaPlayback["timeline"].setPaused(True)
                mediaPlayback["openRV"] = False
        mediaPlayback["l_preview"].clickEvent(event)

    @err_catcher(name=__name__)
    def previewDclk(self, event, mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        if mediaPlayback["seq"] != [] and event.button() == Qt.LeftButton:
            mediaPlayback["openRV"] = True
            self.compare(current=True, mediaPlayback=mediaPlayback)
        mediaPlayback["l_preview"].dclickEvent(event)

    @err_catcher(name=__name__)
    def rclPreview(self, pos, mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        self.showContextMenu(menuType="mediaPreview", mediaPlayback=mediaPlayback)

    @err_catcher(name=__name__)
    def setPreview(self):
        if self.tbw_browser.currentWidget().property("tabType") == "Assets":
            folderName = "Assetinfo"
            entityName = self.core.entities.getAssetNameFromPath(self.curAsset)
            refresh = self.refreshAssetinfo
        else:
            folderName = "Shotinfo"
            entityName = self.cursShots
            refresh = self.refreshShotinfo

        prvPath = os.path.join(
            os.path.dirname(self.core.prismIni),
            folderName,
            "%s_preview.jpg" % entityName,
        )

        pm = self.l_preview.pixmap()
        if (pm.width() / float(pm.height())) > 1.7778:
            pmap = pm.scaledToWidth(self.shotPrvXres)
        else:
            pmap = pm.scaledToHeight(self.shotPrvYres)

        self.core.media.savePixmap(pmap, prvPath)

        refresh()

    @err_catcher(name=__name__)
    def sendToDailies(self, mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        dailiesName = self.core.getConfig(
            "paths", "dailies", configPath=self.core.prismIni
        )

        curDate = time.strftime("%Y_%m_%d", time.localtime())

        dailiesFolder = os.path.join(
            self.core.projectPath,
            dailiesName,
            curDate,
            self.core.getConfig("globals", "username"),
        )
        if not os.path.exists(dailiesFolder):
            os.makedirs(dailiesFolder)

        prvData = mediaPlayback["seq"][0].split(self.core.filenameSeparator)

        refName = ""

        if self.tbw_browser.currentWidget().property("tabType") == "Assets":
            refName += prvData[0] + self.core.filenameSeparator
        elif self.tbw_browser.currentWidget().property("tabType") == "Shots":
            refName += (
                prvData[0]
                + self.core.filenameSeparator
                + prvData[1]
                + self.core.filenameSeparator
            )

        refName += self.curRTask + self.core.filenameSeparator + self.curRVersion
        if self.curRLayer != "":
            refName += self.core.filenameSeparator + self.curRLayer

        sourcePath = os.path.join(mediaPlayback["basePath"], mediaPlayback["seq"][0])

        result = True
        if platform.system() == "Windows":
            folderLinkName = refName + self.core.filenameSeparator + "Folder.lnk"
            refName += ".lnk"

            seqLnk = os.path.join(dailiesFolder, refName)
            folderLnk = os.path.join(dailiesFolder, folderLinkName)

            result = self.core.createShortcut(seqLnk, sourcePath)
            result = result and self.core.createShortcut(folderLnk, mediaPlayback["basePath"])
        else:
            slinkPath = os.path.join(dailiesFolder, refName + "_Folder")
            if os.path.exists(slinkPath):
                try:
                    os.remove(slinkPath)
                except:
                    msg = "An existing reference in the dailies folder couldn't be replaced."
                    self.core.popup(msg)
                    return

            os.symlink(mediaPlayback["basePath"], slinkPath)

        if result:
            self.core.copyToClipboard(dailiesFolder)

            msg = "The version was sent to the current dailies folder. (path in clipboard)"
            self.core.popup(msg, severity="info")
        else:
            self.core.popup("Errors occurred while sending version to dailies.")

    @err_catcher(name=__name__)
    def sliderDrag(self, event, mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        custEvent = QMouseEvent(
            QEvent.MouseButtonPress,
            event.pos(),
            Qt.MidButton,
            Qt.MidButton,
            Qt.NoModifier,
        )
        mediaPlayback["sl_preview"].origMousePressEvent(custEvent)

    @err_catcher(name=__name__)
    def sliderClk(self, mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        if (
            "timeline" in mediaPlayback
            and mediaPlayback["timeline"].state() == QTimeLine.Running
        ):
            mediaPlayback["slStop"] = True
            mediaPlayback["timeline"].setPaused(True)
        else:
            mediaPlayback["slStop"] = False

    @err_catcher(name=__name__)
    def sliderRls(self, mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        if mediaPlayback["slStop"]:
            mediaPlayback["timeline"].setPaused(False)

    @err_catcher(name=__name__)
    def rclList(self, pos, lw, mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        item = lw.itemAt(pos)
        if item is not None:
            itemName = item.text()
        else:
            itemName = ""

        if self.renderBasePath is None:
            return False

        if lw == self.lw_task:
            path = mediaPlayback["getMediaBaseFolder"](
                basepath=self.renderBasePath,
                product=itemName,
            )[0]
        elif lw == self.lw_version:
            if itemName:
                path = item.data(Qt.UserRole)
            else:
                path = mediaPlayback["getMediaBaseFolder"](
                    basepath=self.renderBasePath,
                    product=itemName,
                )[0]

        rcmenu = QMenu(self)

        add = QAction("Add current to compare", self)
        add.triggered.connect(self.addCompare)
        if self.rv is not None and (
            (
                self.curRTask != ""
                and self.curRVersion != ""
                and len(mediaPlayback["seq"]) > 0
            )
            or len(self.lw_task.selectedItems()) > 1
            or len(self.lw_version.selectedItems()) > 1
        ):
            rcmenu.addAction(add)

        if lw == self.lw_task and self.renderBasePath and self.renderBasePath != self.aBasePath:
            exAct = QAction("Create external task", self)
            exAct.triggered.connect(self.createExternalTask)
            rcmenu.addAction(exAct)

        if lw == self.lw_version:
            infAct = QAction("Show version info", self)
            infAct.triggered.connect(self.showVersionInfo)
            rcmenu.addAction(infAct)

            depAct = QAction("Show dependencies", self)
            depAct.triggered.connect(self.showDependencies)
            rcmenu.addAction(depAct)

            if self.curRTask.endswith(" (external)"):
                nvAct = QAction("Create new version", self)
                nvAct.triggered.connect(self.newExVersion)
                rcmenu.addAction(nvAct)

        if os.path.exists(path):
            opAct = QAction("Open in Explorer", self)
            opAct.triggered.connect(lambda: self.core.openFolder(path))
            rcmenu.addAction(opAct)

            copAct = QAction("Copy path", self)
            copAct.triggered.connect(lambda: self.core.copyToClipboard(path))
            rcmenu.addAction(copAct)

        if lw == self.lw_version and itemName.endswith(" (local)"):
            glbAct = QAction("Move to global", self)
            glbAct.triggered.connect(lambda: self.copyToGlobal(path))
            rcmenu.addAction(glbAct)

        self.core.callback(
            name="openPBListContextMenu",
            types=["custom"],
            args=[self, rcmenu, lw, item, path],
        )

        if rcmenu.isEmpty():
            return False

        rcmenu.exec_((lw.viewport()).mapToGlobal(pos))

    @err_catcher(name=__name__)
    def sceneDragEnterEvent(self, e):
        if e.mimeData().hasUrls:
            e.accept()
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def sceneDragMoveEvent(self, e, widget):
        if e.mimeData().hasUrls:
            e.accept()
            widget.setStyleSheet("QTableView { border-style: dashed; border-color: rgb(100, 200, 100);  border-width: 2px; }")
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def sceneDragLeaveEvent(self, e, widget):
        widget.setStyleSheet("")

    @err_catcher(name=__name__)
    def sceneDropEvent(self, e, entityType, widget):
        if e.mimeData().hasUrls:
            widget.setStyleSheet("")
            e.setDropAction(Qt.LinkAction)
            e.accept()

            files = [os.path.normpath(str(url.toLocalFile())) for url in e.mimeData().urls()]
            self.ingestScenefiles(entityType, files)
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def ingestScenefiles(self, entityType, files):
        kwargs = {"entity": entityType}

        if entityType == "asset":
            if not self.curaCat:
                self.core.popup("No valid asset context is selected")
                return

            assetName = self.core.entities.getAssetNameFromPath(self.curAsset)
            kwargs["entityName"] = assetName
            kwargs["step"] = self.curaStep
            kwargs["category"] = self.curaCat
            kwargs["basePath"] = self.curAsset
            refresh = self.refreshAFile
        elif entityType == "shot":
            if not self.cursCat:
                self.core.popup("No valid shot context is selected")
                return

            kwargs["entityName"] = self.cursShots
            kwargs["step"] = self.cursStep
            kwargs["category"] = self.cursCat
            kwargs["basePath"] = self.cursShots
            refresh = self.refreshSFile

        for file in files:
            kwargs["extension"] = os.path.splitext(file)[1]
            targetPath = self.core.paths.generateScenePath(**kwargs)
            targetPath = self.core.convertPath(targetPath, target="local")

            if not os.path.exists(os.path.dirname(targetPath)):
                try:
                    os.makedirs(os.path.dirname(targetPath))
                except:
                    self.core.popup("The directory could not be created")
                    return

            targetPath = targetPath.replace("\\", "/")

            self.core.copyWithProgress(file, targetPath)
            self.core.saveSceneInfo(targetPath)

        refresh()

    @err_catcher(name=__name__)
    def taskDragEnterEvent(self, e):
        if e.mimeData().hasUrls:
            e.accept()
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def taskDragMoveEvent(self, e):
        if e.mimeData().hasUrls:
            e.accept()
            self.lw_task.setStyleSheet("QWidget { border-style: dashed; border-color: rgb(100, 200, 100);  border-width: 2px; }")
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def taskDragLeaveEvent(self, e):
        self.lw_task.setStyleSheet("")

    @err_catcher(name=__name__)
    def taskDropEvent(self, e):
        if e.mimeData().hasUrls:
            self.lw_task.setStyleSheet("")
            e.setDropAction(Qt.LinkAction)
            e.accept()

            if not self.renderBasePath:
                self.core.popup("Select an asset or a shot to create an external task.")
                return

            fname = [os.path.normpath(str(url.toLocalFile())) for url in e.mimeData().urls()]
            self.createExternalTask(filepath=fname[0])
        else:
            e.ignore()

    @err_catcher(name=__name__)
    def createExternalTask(self, data=None, filepath=""):
        if not data:
            try:
                del sys.modules["ExternalTask"]
            except:
                pass

            import ExternalTask

            self.ep = ExternalTask.ExternalTask(core=self.core, startText=filepath)
            self.activateWindow()
            result = self.ep.exec_()

            if result == 1:
                taskName = self.ep.e_taskName.text()
                versionName = self.ep.e_versionName.text()
                targetPath = self.ep.e_taskPath.text()
            else:
                return

        else:
            taskName = data["taskName"]
            versionName = data["versionName"]
            targetPath = data["targetPath"]

        tPath = os.path.join(
            self.renderBasePath, "Rendering", "external", taskName, versionName
        )
        if not os.path.exists(tPath):
            os.makedirs(tPath)

        redirectFile = os.path.join(tPath, "REDIRECT.txt")
        with open(redirectFile, "w") as rfile:
            rfile.write(targetPath)

        curTab = self.tbw_browser.currentWidget().property("tabType")
        curData = [curTab, self.cursShots, taskName + " (external)", versionName, ""]
        self.showRender(curData[0], curData[1], curData[2], curData[3], curData[4])

    @err_catcher(name=__name__)
    def newExVersion(self):
        vPath = os.path.join(
            self.renderBasePath,
            "Rendering",
            "external",
            self.curRTask.replace(" (external)", ""),
        )
        for i in os.walk(vPath):
            dirs = i[1]
            break

        highversion = 0
        cHighVersion = ""
        for i in dirs:
            fname = i.split(self.core.filenameSeparator)

            try:
                version = int(i[1:])
            except:
                continue

            if version > highversion:
                highversion = version
                cHighVersion = i

        newVersion = "v" + format(highversion + 1, "04")

        curLoc = ""
        rdPath = os.path.join(vPath, cHighVersion, "REDIRECT.txt")
        if os.path.exists(rdPath):
            with open(rdPath, "r") as rdFile:
                curLoc = rdFile.read()

        try:
            del sys.modules["ExternalTask"]
        except:
            pass

        import ExternalTask

        self.ep = ExternalTask.ExternalTask(core=self.core)
        self.ep.e_taskName.setText(self.curRTask.replace(" (external)", ""))
        self.ep.w_taskName.setEnabled(False)
        self.ep.e_taskPath.setText(curLoc)
        self.ep.e_versionName.setText(newVersion)
        self.ep.enableOk(curLoc, self.ep.e_taskPath)
        self.ep.setWindowTitle("Create new version")

        result = self.ep.exec_()

        if result == 1:
            vPath = os.path.join(
                self.renderBasePath,
                "Rendering",
                "external",
                self.curRTask.replace(" (external)", ""),
                self.ep.e_versionName.text(),
            )
            if not os.path.exists(vPath):
                os.makedirs(vPath)

            redirectFile = os.path.join(vPath, "REDIRECT.txt")
            with open(redirectFile, "w") as rfile:
                rfile.write(self.ep.e_taskPath.text())

            curTab = self.tbw_browser.currentWidget().property("tabType")
            curData = [
                curTab,
                self.cursShots,
                self.curRTask,
                self.ep.e_versionName.text(),
                "",
            ]
            self.showRender(curData[0], curData[1], curData[2], curData[3], curData[4])

    @err_catcher(name=__name__)
    def rclCompare(self, pos, mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        rcmenu = QMenu(self)

        add = QAction("Add current", self)
        add.triggered.connect(self.addCompare)
        if self.rv is not None and (
            (
                self.curRTask != ""
                and self.curRVersion != ""
                and len(mediaPlayback["seq"]) > 0
            )
            or len(self.lw_task.selectedItems()) > 1
            or len(self.lw_version.selectedItems()) > 1
        ):
            rcmenu.addAction(add)
        com = QAction("Compare", self)
        com.triggered.connect(self.compare)
        if self.lw_compare.count() > 0:
            rcmenu.addAction(com)
        delc = QAction("Remove", self)
        delc.triggered.connect(self.removeCompare)
        if len(self.lw_compare.selectedItems()) > 0:
            rcmenu.addAction(delc)
        clear = QAction("Clear", self)
        clear.triggered.connect(self.clearCompare)
        if self.lw_compare.count() > 0:
            rcmenu.addAction(clear)

        if not rcmenu.isEmpty():
            rcmenu.exec_((self.lw_compare.viewport()).mapToGlobal(pos))

    @err_catcher(name=__name__)
    def getCurRenders(self):
        renders = []
        sTasks = self.lw_task.selectedItems()
        sVersions = self.lw_version.selectedItems()

        if len(sTasks) > 1:
            for i in sTasks:
                render = {"task": i.text(), "version": "", "layer": ""}
                versions = self.core.mediaProducts.getMediaVersions(basepath=self.renderBasePath, product=i.text())

                if len(versions) > 0:
                    versions = sorted(versions, key=lambda x: x["label"], reverse=True)

                    render["version"] = versions[0]["label"]
                    layers = self.core.mediaProducts.getRenderLayers(self.renderBasePath, i.text(), versions[0]["label"])

                    if len(layers) > 0:
                        if "beauty" in layers:
                            render["layer"] = "beauty"
                        elif "rgba" in layers:
                            render["layer"] = "rgba"
                        else:
                            render["layer"] = layers[0]

                renders.append(render)

        elif len(sVersions) > 1:
            for i in sVersions:
                render = {"task": self.curRTask, "version": i.text(), "layer": ""}
                layers = self.core.mediaProducts.getRenderLayers(self.renderBasePath, self.curRTask, i.text())

                if len(layers) > 0:
                    if "beauty" in layers:
                        render["layer"] = "beauty"
                    elif "rgba" in layers:
                        render["layer"] = "rgba"
                    else:
                        render["layer"] = layers[0]

                renders.append(render)

        else:
            renders.append(
                {
                    "task": self.curRTask,
                    "version": self.curRVersion,
                    "layer": self.curRLayer,
                }
            )

        paths = []

        for i in renders:
            foldercont = self.core.mediaProducts.getMediaProductPath(basepath=self.renderBasePath, product=i["task"], version=i["version"], layer=i["layer"])
            if foldercont[0]:
                paths.append(foldercont[0])

        return [paths, renders]

    @err_catcher(name=__name__)
    def addCompare(self):
        if self.tbw_browser.currentWidget().property("tabType") == "Assets":
            shotName = "Asset"
        else:
            shotName = self.cursShots

        curRnd = self.getCurRenders()

        for idx, path in enumerate(curRnd[0]):
            cFiles = []

            if os.path.isfile(path):
                cFiles = [path]
            else:
                for k in os.walk(path):
                    cFiles = k[2]
                    break

            if len(cFiles) > 0 and path not in self.compareStates:
                self.compareStates.insert(0, path)
                self.lw_compare.insertItem(
                    0,
                    str(self.lw_compare.count() + 1)
                    + ": "
                    + shotName
                    + " - "
                    + curRnd[1][idx]["task"]
                    + " - "
                    + curRnd[1][idx]["version"]
                    + " - "
                    + curRnd[1][idx]["layer"],
                )

        if len(self.compareStates) > 0:
            self.b_compareRV.setEnabled(True)
            self.b_combineVersions.setEnabled(True)
            self.b_clearRV.setEnabled(True)

    @err_catcher(name=__name__)
    def removeCompare(self):
        for i in self.lw_compare.selectedItems():
            del self.compareStates[self.lw_compare.row(i)]
            self.lw_compare.takeItem(self.lw_compare.row(i))

        for i in range(self.lw_compare.count()):
            item = self.lw_compare.item(i)
            item.setText(
                str(len(self.compareStates) - (self.lw_compare.row(item)))
                + ": "
                + item.text().split(": ", 1)[1]
            )

        if len(self.compareStates) == 0:
            if (
                len(self.lw_task.selectedItems()) < 2
                and len(self.lw_version.selectedItems()) < 2
            ):
                self.b_compareRV.setEnabled(False)
                self.b_combineVersions.setEnabled(False)
            self.b_clearRV.setEnabled(False)

    @err_catcher(name=__name__)
    def clearCompare(self):
        self.compareStates = []
        self.lw_compare.clear()

        if (
            len(self.lw_task.selectedItems()) < 2
            and len(self.lw_version.selectedItems()) < 2
        ):
            self.b_compareRV.setEnabled(False)
            self.b_combineVersions.setEnabled(False)
        self.b_clearRV.setEnabled(False)

    @err_catcher(name=__name__)
    def compare(self, current=False, ctype="layout", prog="", mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        if (
            "timeline" in mediaPlayback
            and mediaPlayback["timeline"].state() == QTimeLine.Running
        ):
            mediaPlayback["timeline"].setPaused(True)

        if prog in ["DJV", "VLC", "default"] or (
            prog == ""
            and (
                (self.rv is None)
                or (
                    self.djv is not None
                    and self.core.getConfig("globals", "prefer_djv")
                )
            )
        ):
            if prog in ["DJV", ""] and self.djv is not None:
                progPath = self.djv
            elif prog == "VLC":
                progPath = self.vlc
            elif prog in ["default", ""]:
                progPath = ""

            comd = []
            filePath = ""

            if mediaPlayback["name"] == "shots":
                curRenders = self.getCurRenders()[0]
            else:
                curRenders = [mediaPlayback["getMediaBaseFolder"](
                    basepath=self.renderBasePath,
                    product=self.curRTask,
                    version=self.curRVersion,
                    layer=self.curRLayer
                )[0]]

            if len(curRenders) > 0:
                if os.path.isfile(curRenders[0]):
                    filePath = curRenders[0]
                else:
                    for i in os.walk(curRenders[0]):
                        for m in i[2]:
                            filePath = os.path.join(i[0], m)
                            break

                        break

                if filePath != "":
                    baseName, extension = os.path.splitext(filePath)
                    if extension in [
                        ".jpg",
                        ".jpeg",
                        ".JPG",
                        ".png",
                        ".PNG",
                        ".tif",
                        ".tiff",
                        ".exr",
                        ".dpx",
                        ".mp4",
                        ".mov",
                        ".avi",
                    ]:
                        if progPath == "":
                            if platform.system() == "Windows":
                                cmd = ["start", "", "%s" % self.core.fixPath(filePath)]
                                subprocess.call(cmd, shell=True)
                            elif platform.system() == "Linux":
                                subprocess.call(
                                    ["xdg-open", self.core.fixPath(filePath)]
                                )
                            elif platform.system() == "Darwin":
                                subprocess.call(["open", self.core.fixPath(filePath)])

                            return
                        else:
                            comd = [progPath, filePath]

        elif prog in ["RV", ""]:
            comd = [self.rv]

            if current:
                if len(mediaPlayback["seq"]) == 1:
                    cStates = [
                        os.path.join(mediaPlayback["basePath"], mediaPlayback["seq"][0])
                    ]
                else:
                    cStates = [mediaPlayback["basePath"]]
            elif len(self.compareStates) > 0:
                cStates = self.compareStates
            else:
                cStates = self.getCurRenders()[0]

            if ctype in ["layout", "sequence"]:
                cStates = reversed(cStates)

            for i in cStates:
                if os.path.isfile(i):
                    comd.append(i)
                else:
                    comd += self.getImgSources(i)

            if ctype == "layout":
                comd += ["-view", "defaultLayout"]
            elif ctype == "sequence":
                comd += ["-view", "defaultSequence"]
            elif ctype == "stack":
                comd += ["-over"]
            elif ctype == "stackDif":
                comd += ["-diff"]

        if comd != []:
            with open(os.devnull, "w") as f:
                try:
                    subprocess.Popen(comd, stdin=subprocess.PIPE, stdout=f, stderr=f)
                except:
                    try:
                        subprocess.Popen(
                            comd, stdin=subprocess.PIPE, stdout=f, stderr=f, shell=True
                        )
                    except Exception as e:
                        raise RuntimeError("%s - %s" % (comd, e))

    @err_catcher(name=__name__)
    def combineVersions(self, ctype="sequence", mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        if (
            "timeline" in mediaPlayback
            and mediaPlayback["timeline"].state() == QTimeLine.Running
        ):
            mediaPlayback["timeline"].setPaused(True)

        try:
            del sys.modules["CombineMedia"]
        except:
            pass

        import CombineMedia

        self.cm = CombineMedia.CombineMedia(core=self.core, ctype=ctype)

        result = self.cm.exec_()

    @err_catcher(name=__name__)
    def compareOptions(self, event):
        cmenu = QMenu(self)

        sAct = QAction("Sequence", self)
        sAct.triggered.connect(lambda: self.compare(ctype="sequence"))
        cmenu.addAction(sAct)

        lAct = QAction("Layout", self)
        lAct.triggered.connect(lambda: self.compare(ctype="layout"))
        cmenu.addAction(lAct)

        lAct = QAction("Stack (over)", self)
        lAct.triggered.connect(lambda: self.compare(ctype="stack"))
        cmenu.addAction(lAct)

        lAct = QAction("Stack (difference)", self)
        lAct.triggered.connect(lambda: self.compare(ctype="stackDif"))
        cmenu.addAction(lAct)

        cmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def combineOptions(self, event):
        cmenu = QMenu(self)

        sAct = QAction("Sequence", self)
        sAct.triggered.connect(lambda: self.combineVersions(ctype="sequence"))
        cmenu.addAction(sAct)

        # lAct = QAction("Layout", self)
        # lAct.triggered.connect(lambda: self.combineVersions(ctype="layout"))
        # cmenu.addAction(lAct)

        # lAct = QAction("Stack (over)", self)
        # lAct.triggered.connect(lambda: self.combineVersions(ctype="stack"))
        # cmenu.addAction(lAct)

        # lAct = QAction("Stack (difference)", self)
        # lAct.triggered.connect(lambda: self.combineVersions(ctype="stackDif"))
        # cmenu.addAction(lAct)

        cmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def mouseDrag(self, event, element, mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        if (element == mediaPlayback["l_preview"]) and event.buttons() != Qt.LeftButton:
            return
        elif (event.buttons() != Qt.LeftButton and element != self.cb_layer) or (
            event.buttons() == Qt.LeftButton and (event.modifiers() & Qt.ShiftModifier)
        ) and element != mediaPlayback["l_preview"]:
            element.mmEvent(event)
            return
        elif element == self.cb_layer and event.buttons() != Qt.MiddleButton:
            element.mmEvent(event)
            return

        curRnd = self.getCurRenders()
        urlList = []
        mods = QApplication.keyboardModifiers()
        for i in curRnd[0]:
            if element == self.cb_layer:
                for k in os.walk(os.path.dirname(i)):
                    for m in k[1]:
                        url = "file:///%s" % os.path.join(k[0], m)
                        url = url.replace("\\", "/")
                        urlList.append(QUrl(url))
                    break
            else:
                if os.path.isfile(i):
                    imgSrc = [i]
                else:
                    imgSrc = self.getImgSources(i)

                for k in imgSrc:
                    if mods == Qt.ControlModifier:
                        url = "file:///%s" % os.path.dirname(k)
                    else:
                        url = "file:///%s" % k

                    url = url.replace("\\", "/")

                    urlList.append(QUrl(url))

        if len(urlList) == 0:
            return

        drag = QDrag(mediaPlayback["l_preview"])
        mData = QMimeData()

        mData.setUrls(urlList)
        mData.setData("text/plain", str(urlList[0].toLocalFile()).encode())
        drag.setMimeData(mData)

        drag.exec_()

    @err_catcher(name=__name__)
    def getImgSources(self, path, getFirstFile=False):
        foundSrc = []
        for k in os.walk(path):
            sources = []
            psources = []
            for m in k[2]:
                baseName, extension = os.path.splitext(m)
                if extension in [
                    ".jpg",
                    ".jpeg",
                    ".JPG",
                    ".png",
                    ".PNG",
                    ".tif",
                    ".tiff",
                    ".exr",
                    ".mp4",
                    ".mov",
                    ".avi",
                    ".dpx",
                ]:
                    src = [baseName, extension]
                    if len(baseName) > 3:
                        endStr = baseName[-4:]
                        if pVersion == 2:
                            endStr = unicode(endStr)
                        if endStr.isnumeric():
                            src = [baseName[:-4], extension]

                    psources.append(src)

            for m in sorted(k[2]):
                baseName, extension = os.path.splitext(m)
                if extension in [
                    ".jpg",
                    ".jpeg",
                    ".JPG",
                    ".png",
                    ".PNG",
                    ".tif",
                    ".tiff",
                    ".exr",
                    ".mp4",
                    ".mov",
                    ".avi",
                    ".dpx",
                ]:
                    fname = m
                    if getFirstFile:
                        return [os.path.join(path, m)]

                    if len(baseName) > 3:
                        endStr = baseName[-4:]
                        if pVersion == 2:
                            endStr = unicode(endStr)
                        if (
                            endStr.isnumeric()
                            and len(psources) == psources.count(psources[0])
                            and extension not in [".mp4", ".mov", ".avi"]
                        ):
                            fname = "%s@@@@%s" % (baseName[:-4], extension)

                    if fname in sources:
                        if len(sources) == 1:
                            break  # sequence detected
                    else:
                        foundSrc.append(os.path.join(path, fname))
                        sources.append(fname)
            break

        return foundSrc

    @err_catcher(name=__name__)
    def getRVpath(self):
        try:
            if platform.system() == "Windows":
                cRVPath = self.core.getConfig("globals", "rvpath")
                if cRVPath is not None and os.path.exists(
                    os.path.join(cRVPath, "bin", "rv.exe")
                ):
                    self.rv = os.path.join(cRVPath, "bin", "rv.exe")
                else:
                    key = _winreg.OpenKey(
                        _winreg.HKEY_LOCAL_MACHINE,
                        "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\rv.exe",
                        0,
                        _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
                    )

                    self.rv = _winreg.QueryValue(key, None)
            else:
                self.rv = "/usr/local/rv-Linux-x86-64-7.2.5/bin/rv"

            if not os.path.exists(self.rv):
                self.rv = None
        except:
            self.rv = None

    @err_catcher(name=__name__)
    def getRVdLUT(self):
        dlut = None

        assets = self.core.getConfig("paths", "assets", configPath=self.core.prismIni)

        if assets is not None:
            lutPath = os.path.join(self.core.projectPath, assets, "LUTs", "RV_dLUT")
            if os.path.exists(lutPath) and len(os.listdir(lutPath)) > 0:
                dlut = os.path.join(lutPath, os.listdir(lutPath)[0])

        return dlut

    @err_catcher(name=__name__)
    def getDJVpath(self):
        try:
            cDJVPath = self.core.getConfig("globals", "djvpath")

            if platform.system() == "Windows":
                for i in ["djv_view.exe", "djv.exe"]:
                    djvPath = os.path.join(cDJVPath, "bin", i)
                    if cDJVPath is not None and os.path.exists(djvPath):
                        self.djv = djvPath
                        break
                else:
                    key = _winreg.OpenKey(
                        _winreg.HKEY_LOCAL_MACHINE,
                        "SOFTWARE\\Classes\\djv_view\\shell\\open\\command",
                        0,
                        _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
                    )

                    self.djv = (_winreg.QueryValue(key, None)).split(' "%1"')[0]
            else:
                for i in ["djv_view.sh", "djv.sh"]:
                    djvPath = os.path.join(cDJVPath, "bin", i)
                    if cDJVPath is not None and os.path.exists(djvPath):
                        self.djv = djvPath
                        break
                else:
                    self.djv = "/usr/local/djv-1.1.0-Linux-64/bin/djv_view.sh"

            if not os.path.exists(self.djv):
                self.djv = None
        except:
            self.djv = None

    @err_catcher(name=__name__)
    def getVLCpath(self):
        if platform.system() == "Windows":
            try:
                key = _winreg.OpenKey(
                    _winreg.HKEY_LOCAL_MACHINE,
                    "SOFTWARE\\VideoLAN\\VLC",
                    0,
                    _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
                )

                self.vlc = _winreg.QueryValue(key, None)

                if not os.path.exists(self.vlc):
                    self.vlc = None

            except:
                try:
                    key = _winreg.OpenKey(
                        _winreg.HKEY_LOCAL_MACHINE,
                        "SOFTWARE\\WOW6432Node\\VideoLAN\\VLC",
                        0,
                        _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
                    )

                    self.vlc = _winreg.QueryValue(key, None)
                    if not os.path.exists(self.vlc):
                        self.vlc = None

                except:
                    self.vlc = None

        else:
            self.vlc = "/usr/bin/vlc"
            if not os.path.exists(self.vlc):
                self.vlc = None

    @err_catcher(name=__name__)
    def convertImgs(self, extension, mediaPlayback=None, checkRes=True, settings=None):
        if not extension:
            if settings:
                extension = settings.get("extension")

            if not extension:
                logger.warning("No extension specified")
                return

            settings.pop("extension")

        if extension[0] != ".":
            extension = "." + extension

        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        inputpath = os.path.join(
            mediaPlayback["basePath"], mediaPlayback["seq"][0]
        ).replace("\\", "/")
        inputExt = os.path.splitext(inputpath)[1]

        if checkRes:
            if "pwidth" in mediaPlayback and mediaPlayback["pwidth"] == "?":
                self.core.popup("Cannot read media file.")
                return

            if (
                extension == ".mp4"
                and "pwidth" in mediaPlayback
                and "pheight" in mediaPlayback
                and (
                    int(mediaPlayback["pwidth"]) % 2 == 1
                    or int(mediaPlayback["pheight"]) % 2 == 1
                )
            ):
                self.core.popup("Media with odd resolution can't be converted to mp4.")
                return

        conversionSettings = settings or OrderedDict()

        if extension == ".mov" and not settings:
            conversionSettings["-c"] = "prores"
            conversionSettings["-profile"] = 2
            conversionSettings["-pix_fmt"] = "yuv422p10le"

        if mediaPlayback["prvIsSequence"]:
            inputpath = os.path.splitext(inputpath)[0][:-self.core.framePadding] + "%04d".replace("4", str(self.core.framePadding)) + inputExt

        outputpath = self.core.paths.getMediaConversionOutputPath(self.curRTask, inputpath, extension)

        if not outputpath:
            return

        if self.curRTask.endswith(" (external)"):
            curPath = os.path.join(
                self.renderBasePath,
                "Rendering",
                "external",
                self.curRTask.replace(" (external)", ""),
                self.curRVersion,
            )
            rpath = os.path.join(curPath + "(%s)" % extension[1:], "REDIRECT.txt")

            if not os.path.exists(os.path.dirname(rpath)):
                os.makedirs(os.path.dirname(rpath))

            with open(rpath, "w") as rfile:
                rfile.write(os.path.dirname(outputpath))

        if mediaPlayback["prvIsSequence"]:
            startNum = mediaPlayback["pstart"]
        else:
            startNum = 0
            if inputExt == ".dpx":
                conversionSettings["-start_number"] = None
                conversionSettings["-start_number_out"] = None

        result = self.core.media.convertMedia(inputpath, startNum, outputpath, settings=conversionSettings)

        if extension not in self.core.mediaProducts.videoFormats:
            outputpath = outputpath % int(startNum)

        curTab = self.tbw_browser.currentWidget().property("tabType")
        curData = [
            curTab,
            self.cursShots,
            self.curRTask,
            self.curRVersion,
            self.curRLayer,
        ]
        self.showRender(curData[0], curData[1], curData[2], curData[3], curData[4])

        if os.path.exists(outputpath) and os.stat(outputpath).st_size > 0:
            self.core.copyToClipboard(outputpath)
            msg = "The images were converted successfully. (path is in clipboard)"
            self.core.popup(msg, severity="info")
        else:
            msg = "The images could not be converted."
            logger.debug("expected outputpath: %s" % outputpath)
            self.core.ffmpegError("Image conversion", msg, result)

    @err_catcher(name=__name__)
    def compGetImportSource(self, mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        sourceFolder = os.path.dirname(
            os.path.join(mediaPlayback["basePath"], mediaPlayback["seq"][0])
        ).replace("\\", "/")
        sources = self.getImgSources(sourceFolder)
        sourceData = []

        for curSourcePath in sources:

            if "@@@@" in curSourcePath:
                if (
                    not "pstart" in mediaPlayback
                    or not "pend" in mediaPlayback
                    or mediaPlayback["pstart"] == "?"
                    or mediaPlayback["pend"] == "?"
                ):
                    firstFrame = 0
                    lastFrame = 0
                else:
                    firstFrame = mediaPlayback["pstart"]
                    lastFrame = mediaPlayback["pend"]

                filePath = curSourcePath.replace("@@@@", "####").replace("\\", "/")
            else:
                filePath = curSourcePath.replace("\\", "/")
                firstFrame = 0
                lastFrame = 0

            sourceData.append([filePath, firstFrame, lastFrame])

        return sourceData

    @err_catcher(name=__name__)
    def compGetImportPasses(self, mediaPlayback=None):
        if mediaPlayback is None:
            mediaPlayback = self.mediaPlaybacks["shots"]

        sourceFolder = os.path.dirname(
            os.path.dirname(
                os.path.join(mediaPlayback["basePath"], mediaPlayback["seq"][0])
            )
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
                and "pstart" in mediaPlayback
                and "pend" in mediaPlayback
                and mediaPlayback["pstart"] != "?"
                and mediaPlayback["pend"] != "?"
            ):
                firstFrame = mediaPlayback["pstart"]
                lastFrame = mediaPlayback["pend"]

                curPassName = imgs[0].split(".")[0]
                increment = "####"
                curPassFormat = imgs[0].split(".")[-1]

                filePath = os.path.join(
                    sourceFolder,
                    curPass,
                    ".".join([curPassName, increment, curPassFormat]),
                ).replace("\\", "/")
            else:
                filePath = os.path.join(curPassPath, imgs[0]).replace("\\", "/")
                firstFrame = 0
                lastFrame = 0

            sourceData.append([filePath, firstFrame, lastFrame])

        return sourceData


if __name__ == "__main__":
    qapp = QApplication(sys.argv)

    from UserInterfacesPrism import qdarkstyle

    qapp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))

    appIcon = QIcon(
        os.path.join(prismRoot, "Scripts", "UserInterfacesPrism", "p_tray.ico")
    )

    qapp.setWindowIcon(appIcon)

    pc = PrismCore.PrismCore(prismArgs=["loadProject", "noProjectBrowser"])
    pc.projectBrowser()

    sys.exit(qapp.exec_())
