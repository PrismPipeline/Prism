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
import platform
import logging

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

prjScriptPath = os.path.join(os.path.dirname(__file__))
if prjScriptPath not in sys.path:
    sys.path.append(prjScriptPath)

if eval(os.getenv("PRISM_DEBUG", "False")):
    for module in [
        "ProjectBrowser_ui",
        "SceneBrowser",
        "ProductBrowser",
        "MediaBrowser",
    ]:
        try:
            del sys.modules[module]
        except:
            pass

import SceneBrowser
import ProductBrowser
import MediaBrowser

from PrismUtils.Decorators import err_catcher
from UserInterfaces import ProjectBrowser_ui


logger = logging.getLogger(__name__)


class ProjectBrowser(QMainWindow, ProjectBrowser_ui.Ui_mw_ProjectBrowser):
    showing = Signal(object)

    def __init__(self, core):
        QMainWindow.__init__(self)
        self.setupUi(self)
        self.core = core

        logger.debug("Initializing Project Browser")

        self.core.parentWindow(self)

        self.setWindowTitle(
            "Prism %s - Project Browser - %s"
            % (self.core.version, self.core.projectName)
        )
        self.tabs = []
        self.previousTab = None
        self.locations = [{"name": "global"}]
        if self.core.useLocalFiles:
            self.locations.append({"name": "local"})

        self.closeParm = "closeafterload"
        self.loadLayout()
        self.connectEvents()
        self.core.callback(name="onProjectBrowserStartup", args=[self])

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.actionPrismSettings.triggered.connect(self.core.prismSettings)
        self.actionStateManager.triggered.connect(self.core.stateManager)
        self.actionOpenOnStart.toggled.connect(self.triggerOpen)
        self.actionCheckForUpdates.toggled.connect(self.triggerUpdates)
        self.actionCheckForShotFrameRange.toggled.connect(self.triggerFrameranges)
        self.actionCloseAfterLoad.toggled.connect(self.triggerCloseLoad)
        self.actionAutoplay.toggled.connect(self.mediaBrowser.triggerAutoplay)
        self.act_filesizes.toggled.connect(self.triggerShowFileSizes)
        self.act_rememberTab.toggled.connect(self.triggerRememberTab)
        self.tbw_project.currentChanged.connect(self.tabChanged)

    def enterEvent(self, event):
        try:
            QApplication.restoreOverrideCursor()
        except:
            pass

    def showEvent(self, event):
        self.showing.emit(self)
        self.core.callback(name="onProjectBrowserShow", args=[self])

    def resizeEvent(self, event):
        self.closeMenus()

    def moveEvent(self, event):
        self.closeMenus()

    @err_catcher(name=__name__)
    def closeMenus(self):
        if hasattr(self, "w_user") and self.w_user.isVisible():
            self.w_user.close()

        if hasattr(self, "w_projects") and self.w_projects.isVisible():
            self.w_projects.close()

    @err_catcher(name=__name__)
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_F5:
            self.refreshUiTriggered()

    @err_catcher(name=__name__)
    def loadLayout(self):
        self.setCentralWidget(self.scrollArea)
        self.helpMenu = QMenu("Help", self)

        self.actionWebsite = QAction("Visit website", self)
        self.actionWebsite.triggered.connect(lambda: self.core.openWebsite("home"))
        path = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "open-web.png")
        icon = self.core.media.getColoredIcon(path)
        self.actionWebsite.setIcon(icon)
        self.helpMenu.addAction(self.actionWebsite)

        self.actionWebsite = QAction("Tutorials", self)
        self.actionWebsite.triggered.connect(lambda: self.core.openWebsite("tutorials"))
        path = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "tutorials.png")
        icon = self.core.media.getColoredIcon(path)
        self.actionWebsite.setIcon(icon)
        self.helpMenu.addAction(self.actionWebsite)

        self.actionWebsite = QAction("Documentation", self)
        self.actionWebsite.triggered.connect(
            lambda: self.core.openWebsite("documentation")
        )
        path = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "book.png")
        icon = self.core.media.getColoredIcon(path)
        self.actionWebsite.setIcon(icon)
        self.helpMenu.addAction(self.actionWebsite)

        self.actionAbout = QAction("About...", self)
        self.actionAbout.triggered.connect(self.core.showAbout)
        path = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "info.png")
        icon = self.core.media.getColoredIcon(path)
        self.actionAbout.setIcon(icon)
        self.helpMenu.addAction(self.actionAbout)

        self.menubar.addMenu(self.helpMenu)

        self.act_filesizes = QAction("Show filesizes", self)
        self.act_filesizes.setCheckable(True)
        self.act_filesizes.setChecked(False)
        self.menuTools.insertAction(self.actionAutoplay, self.act_filesizes)

        self.act_rememberTab = QAction("Remember active tab", self)
        self.act_rememberTab.setCheckable(True)
        self.act_rememberTab.setChecked(True)
        self.menuTools.insertAction(self.actionAutoplay, self.act_rememberTab)

        path = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "configure.png")
        icon = self.core.media.getColoredIcon(path)
        self.actionPrismSettings.setIcon(icon)

        if self.core.debugMode:
            self.act_console = QAction("Console...", self)
            self.act_console.triggered.connect(self.core.openConsole)
            path = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "console.png")
            icon = self.core.media.getColoredIcon(path)
            self.act_console.setIcon(icon)
            self.menuTools.addAction(self.act_console)

        self.recentMenu = QMenu("Recent", self)
        path = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "history.png")
        icon = self.core.media.getColoredIcon(path)
        self.recentMenu.setIcon(icon)
        try:
            self.recentMenu.setToolTipsVisible(True)
        except:
            pass

        self.menuTools.addMenu(self.recentMenu)
        self.refreshRecentMenu()

        self.actionSendFeedback = QAction("Send feedback...", self)
        self.actionSendFeedback.triggered.connect(self.core.sendFeedbackDlg)
        self.menubar.addAction(self.actionSendFeedback)
        self.w_menuCorner = QWidget()
        self.lo_corner = QHBoxLayout()
        self.w_menuCorner.setLayout(self.lo_corner)

        path = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "user.png")
        icon = self.core.media.getColoredIcon(path)
        self.b_user = QToolButton()
        self.b_user.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.b_user.setIcon(icon)
        self.b_user.clicked.connect(self.onUserClicked)
        self.b_user.setFocusPolicy(Qt.StrongFocus)
        self.b_user.setToolTip("Current User")
        if self.core.appPlugin.pluginName != "Standalone":
            self.b_user.setStyleSheet(
                "QWidget{padding: 0; border-width: 0px;background-color: transparent} QWidget:hover{background-color: rgba(250, 250, 250, 40); }"
            )

        path = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "project.png")
        icon = self.core.media.getColoredIcon(path)
        self.b_projects = QToolButton(self.w_menuCorner)
        self.b_projects.setText(self.core.projectName)
        self.b_projects.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.b_projects.setIcon(icon)
        self.b_projects.clicked.connect(self.onProjectsClicked)
        self.b_projects.setFocusPolicy(Qt.StrongFocus)
        self.b_projects.setToolTip("Current Project")
        if self.core.appPlugin.pluginName != "Standalone":
            self.b_projects.setStyleSheet(
                "QWidget{padding: 0; border-width: 0px;background-color: transparent} QWidget:hover{background-color: rgba(250, 250, 250, 40); }"
            )

        self.b_refreshTabs = QToolButton()
        self.lo_corner.addWidget(self.b_user)
        self.lo_corner.addWidget(self.b_projects)
        self.lo_corner.addWidget(self.b_refreshTabs)
        
        self.lo_corner.setContentsMargins(0, 0, 10, 0)
        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "refresh.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_refreshTabs.setIcon(icon)
        self.b_refreshTabs.clicked.connect(self.refreshUiTriggered)
        self.b_refreshTabs.setIconSize(QSize(20, 20))
        self.b_refreshTabs.setToolTip("Refresh")
        if self.core.appPlugin.pluginName != "Standalone":
            self.b_refreshTabs.setStyleSheet(
                "QWidget{padding: 0; border-width: 0px;background-color: transparent} QWidget:hover{background-color: rgba(250, 250, 250, 40); }"
            )
        self.b_refreshTabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.b_refreshTabs.customContextMenuRequested.connect(
            lambda x: self.showContextMenu("refresh")
        )

        if platform.system() == "Darwin":
            parentWidget = self.tbw_project
        else:
            parentWidget = self.menubar

        parentWidget.setCornerWidget(self.w_menuCorner)

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

        if "showFileSizes" in glbData:
            self.act_filesizes.setChecked(glbData["showFileSizes"])

        if "rememberTab" in glbData:
            self.act_rememberTab.setChecked(glbData["rememberTab"])

        self.sceneBrowser = SceneBrowser.SceneBrowser(
            core=self.core, projectBrowser=self, refresh=False
        )
        self.addTab("Scenefiles", self.sceneBrowser)

        self.productBrowser = ProductBrowser.ProductBrowser(core=self.core, refresh=False, projectBrowser=self)
        self.productBrowser.autoClose = False
      #  self.productBrowser.handleImport = False
        self.addTab("Products", self.productBrowser)

        self.mediaBrowser = MediaBrowser.MediaBrowser(
            core=self.core, projectBrowser=self, refresh=False
        )
        self.addTab("Media", self.mediaBrowser)

        self.tbw_project.setStyleSheet("QTabWidget::tab-bar {alignment: center;}")

        self.core.callback(name="projectBrowser_loadUI", args=[self])
        if brsData.get("selectedContext", None):
            navData = brsData["selectedContext"]
        else:
            navData = None

        if self.act_rememberTab.isChecked() and brsData.get("currentProjectTab", None):
            for idx in range(self.tbw_project.count()):
                if (
                    self.tbw_project.widget(idx).property("tabType")
                    == brsData["currentProjectTab"]
                ):
                    self.showTab(brsData["currentProjectTab"])
                    self.tabChanged(idx, navData)
                    break
            else:
                self.tabChanged(0, navData)
        else:
            self.tabChanged(0, navData)

        if self.tbw_project.count() == 0:
            self.tbw_project.setVisible(False)

        if "windowSize" in brsData:
            wsize = brsData["windowSize"]
            self.resize(wsize[0], wsize[1])
        else:
            screen = self.core.getQScreenGeo()
            if screen:
                screenW = screen.width()
                screenH = screen.height()
                space = 200
                if screenH < (self.height() + space):
                    self.resize(self.width(), screenH - space)

                if screenW < (self.width() + space):
                    self.resize(screenW - space, self.height())

        self.updateTabSize(self.tbw_project.currentIndex())

        self.scrollArea.setStyleSheet("QScrollArea { border-width: 0px;}")
        self.lo_scrollArea.setContentsMargins(0, 9, 0, 0)
        self.refreshUser()

    #         ssheet = """
    # QWidget#header {
    #     background-image: url("D:/test.png");
    #     background-repeat: no-repeat;
    # }
    # """
    #         self.centralwidget.setObjectName("header")
    #         self.centralwidget.setStyleSheet(ssheet)

    @err_catcher(name=__name__)
    def refreshRecentMenu(self):
        self.recentMenu.clear()
        recents = self.core.getRecentScenefiles()
        for recent in recents:
            recentName = os.path.basename(recent)
            entity = self.core.getScenefileData(recent)
            entityName = self.core.entities.getEntityName(entity)
            if entityName:
                recentName = "%s - %s" % (entityName, recentName)

            act = QAction(recentName, self)
            act.setToolTip(recent)
            act.triggered.connect(lambda x=None, r=recent: self.onRecentClicked(r))
            icon = self.core.getIconForFileType(os.path.splitext(recent)[1])
            if icon:
                act.setIcon(icon)
            self.recentMenu.addAction(act)

        self.recentMenu.setEnabled(not self.recentMenu.isEmpty())

    @err_catcher(name=__name__)
    def onRecentClicked(self, recent):
        mods = QApplication.keyboardModifiers()
        if mods == Qt.ControlModifier:
            self.showTab("Scenefiles")
            data = self.core.getScenefileData(recent)
            self.sceneBrowser.navigate(data)
        else:
            self.sceneBrowser.exeFile(recent)

    @err_catcher(name=__name__)
    def refreshUser(self):
        self.b_user.setText(self.core.username)
        self.menubar.adjustSize()
        self.b_projects.adjustSize()

    @err_catcher(name=__name__)
    def addTab(self, name, widget, position=-1):
        widget.setProperty("tabType", name)
        self.tbw_project.insertTab(position, widget, name)
        self.tabs.append(widget)

    @err_catcher(name=__name__)
    def closeEvent(self, event):
        visible = []
        for i in range(self.tbw_project.count()):
            visible.append(self.tbw_project.widget(i).property("tabType"))

        cData = []

        curW = self.tbw_project.widget(self.tbw_project.currentIndex())
        if curW:
            currentType = curW.property("tabType")
            selContext = curW.getSelectedContext()
        else:
            currentType = ""
            selContext = None

        cData = {
            "browser": {
                "currentProjectTab": currentType,
                "windowSize": [self.width(), self.height()],
                "selectedContext": selContext
            }
        }

        for pluginName in getattr(self, "appFilters", []):
            cData["browser"]["sceneFilter"][pluginName] = self.appFilters[pluginName][
                "show"
            ]

        for tab in self.tabs:
            if hasattr(tab, "saveSettings"):
                tab.saveSettings(cData)

        self.core.setConfig(data=cData, updateNestedData={"exclude": ["selectedContext"]})

        if hasattr(self, "mediaBrowser"):
            pb = self.mediaBrowser.w_preview.mediaPlayer
            if pb.timeline and pb.timeline.state() != QTimeLine.NotRunning:
                pb.timeline.setPaused(True)

        QPixmapCache.clear()
        if hasattr(self, "sceneBrowser"):
            if hasattr(self.sceneBrowser, "detailWin") and self.sceneBrowser.detailWin.isVisible():
                self.sceneBrowser.detailWin.close()

        self.core.callback(name="onProjectBrowserClose", args=[self])

        event.accept()

    @err_catcher(name=__name__)
    def onUserClicked(self, state=None):
        if hasattr(self, "w_user") and self.w_user.isVisible():
            self.w_user.close()
            return

        if not hasattr(self, "w_user"):
            self.w_user = UserWidget(self)
            self.b_user.setFocusProxy(self.w_user)

        self.w_user.showWidget()
        pos = self.b_user.mapToGlobal(self.b_user.geometry().bottomRight())
        y = self.menubar.mapToGlobal(self.menubar.geometry().bottomRight()).y()
        newPos = QPoint((pos-QPoint(self.w_user.geometry().width(), 0)).x(), y)
        self.w_user.move(newPos)

    @err_catcher(name=__name__)
    def onProjectsClicked(self, state=None):
        if hasattr(self, "w_projects") and self.w_projects.isVisible():
            self.w_projects.close()
            return

        if not hasattr(self, "w_projects"):
            self.w_projects = self.core.projects.ProjectListWidget(self)
            self.b_projects.setFocusProxy(self.w_projects)

        mright = self.menubar.mapToGlobal(self.menubar.geometry().bottomRight()).x()
        y = self.menubar.mapToGlobal(self.menubar.geometry().bottomRight()).y()
        self.w_projects.adjustSize()
        widgetWidth = self.w_projects.geometry().width()
        x = mright - self.w_menuCorner.width() + self.b_projects.pos().x() + self.b_projects.width()
        x -= widgetWidth
        newPos = QPoint(x, y)
        self.w_projects.move(newPos)

        self.w_projects.showWidget()
        QApplication.processEvents()

        x = mright - self.w_menuCorner.width() + self.b_projects.pos().x() + self.b_projects.width()
        widgetWidth = self.w_projects.geometry().width()
        x -= widgetWidth
        newPos = QPoint(x, y)
        self.w_projects.move(newPos)

    @err_catcher(name=__name__)
    def tabChanged(self, tab, navData=None):
        if self.previousTab is not None:
            prev = self.tbw_project.widget(self.previousTab)
        else:
            prev = None

        self.tbw_project.currentWidget().entered(prevTab=prev, navData=navData)
        if getattr(self.tbw_project.currentWidget(), "refreshStatus", "valid") == "invalid":
            self.tbw_project.currentWidget().refreshUI()

        self.updateTabSize(tab)
        self.previousTab = tab

    @err_catcher(name=__name__)
    def updateTabSize(self, tab):
        for idx in range(self.tbw_project.count()):
            if idx != tab:
                self.tbw_project.widget(idx).setSizePolicy(
                    QSizePolicy.Ignored, QSizePolicy.Ignored
                )

        curWidget = self.tbw_project.widget(tab)
        if not curWidget:
            return

        curWidget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

    @err_catcher(name=__name__)
    def checkVisibleTabs(self):
        cw = self.tbw_project.currentWidget()
        if not cw:
            self.core.popup(
                "The Project Browser couldn't load correctly. Please restart Prism and contact the support in case of any errors."
            )
            return False

        return True

    @err_catcher(name=__name__)
    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if event.oldState() == Qt.WindowMinimized:
                if getattr(self.tbw_project.currentWidget(), "refreshStatus", "valid") == "invalid":
                    self.tbw_project.currentWidget().refreshUI()

    @err_catcher(name=__name__)
    def refreshUiTriggered(self, state=None):
        self.core.callback(name="onProjectBrowserRefreshUiTriggered", args=[self])
        self.refreshUI()

    @err_catcher(name=__name__)
    def refreshUI(self):
        if not self.checkVisibleTabs():
            return

        self.setEnabled(False)
        QCoreApplication.processEvents()

        for idx in range(self.tbw_project.count()):
            self.tbw_project.widget(idx).refreshStatus = "invalid"

        if self.isVisible() and not self.isMinimized():
            cw = self.tbw_project.currentWidget()
            cw.refreshUI()

        self.core.callback(name="onProjectBrowserRefreshUI", args=[self])
        self.setEnabled(True)

    @err_catcher(name=__name__)
    def getLocationIcon(self, name):
        icon = None
        if name == "global":
            icon = QIcon(os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "global.png"))
        elif name == "local":
            icon = QIcon(os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "local.png"))
        else:
            result = self.core.callback("getLocationIcon", {"name": name})
            for res in result:
                if res:
                    icon = res

        return icon

    @err_catcher(name=__name__)
    def getContextMenu(self, menuType, **kwargs):
        menu = None
        if menuType == "refresh":
            menu = self.getRefreshMenu(**kwargs)

        return menu

    @err_catcher(name=__name__)
    def showContextMenu(self, menuType, **kwargs):
        menu = self.getContextMenu(menuType, **kwargs)
        self.core.callback(
            name="projectBrowserContextMenuRequested",
            args=[self, menuType, menu],
        )
        if not menu or menu.isEmpty():
            return

        menu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def getRefreshMenu(self):
        menu = QMenu(self)
        menu.addAction("Clear configcache", self.core.configs.clearCache)
        menu.addActions(self.b_refreshTabs.actions())
        return menu

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
    def triggerShowFileSizes(self, checked=False):
        self.core.setConfig("globals", "showFileSizes", checked)
        self.refreshUI()

    @err_catcher(name=__name__)
    def triggerRememberTab(self, checked=False):
        self.core.setConfig("globals", "rememberTab", checked)

    @err_catcher(name=__name__)
    def triggerCloseLoad(self, checked=False):
        self.core.setConfig("browser", self.closeParm, checked)

    @err_catcher(name=__name__)
    def showTab(self, tab):
        if tab != self.tbw_project.currentWidget().property("tabType"):
            for i in range(self.tbw_project.count()):
                if self.tbw_project.widget(i).property("tabType") == tab:
                    idx = i
                    break
            else:
                return False

            self.tbw_project.setCurrentIndex(idx)
            return True


class UserWidget(QDialog):

    signalShowing = Signal()

    def __init__(self, origin):
        super(UserWidget, self).__init__()
        self.origin = origin
        self.core = origin.core
        self.allowClose = True
        self.core.parentWindow(self, parent=origin)
        self.setupUi()

    @err_catcher(name=__name__)
    def focusInEvent(self, event):
        self.activateWindow()

    @err_catcher(name=__name__)
    def focusOutEvent(self, event):
        if self.allowClose and not self.e_user.hasFocus() and not self.e_abbreviation.hasFocus():
            self.close()

    @err_catcher(name=__name__)
    def showWidget(self):
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("QDialog { border: 1px solid rgb(70, 90, 120); }")
        self.refreshUi()
        self.show()
        self.allowClose = False
        self.e_user.setFocus()
        QApplication.processEvents()
        self.allowClose = True

        if not hasattr(self, "baseWidth"):
            self.baseWidth = self.width()

        self.resize(self.baseWidth + 100, self.height())

    @err_catcher(name=__name__)
    def setupUi(self):
        self.setFocusPolicy(Qt.StrongFocus)

        self.lo_main = QGridLayout()
        self.setLayout(self.lo_main)

        self.l_user = QLabel("Username:")
        self.e_user = QLineEdit()
        self.e_user.installEventFilter(self)
        self.l_abbreviation = QLabel("Abbreviation:")
        self.e_abbreviation = QLineEdit()
        self.e_abbreviation.installEventFilter(self)
        self.sp_apply = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.b_apply = QPushButton("Apply")
        self.b_apply.setFocusProxy(self)

        readOnly = self.core.users.isUserReadOnly()
        abbrReadOnly = self.core.users.isAbbreviationReadOnly()
        self.e_user.setReadOnly(readOnly)
        self.e_abbreviation.setReadOnly(readOnly or abbrReadOnly)

        self.lo_main.addWidget(self.l_user, 0, 0)
        self.lo_main.addWidget(self.e_user, 0, 1, 1, 2)
        self.lo_main.addWidget(self.l_abbreviation, 1, 0)
        self.lo_main.addWidget(self.e_abbreviation, 1, 1, 1, 2)
        if not readOnly:
            self.lo_main.addItem(self.sp_apply, 2, 1)
            self.lo_main.addWidget(self.b_apply, 2, 2)

        self.e_user.textChanged.connect(self.onUserChanged)
        self.b_apply.clicked.connect(self.onApply)

    @err_catcher(name=__name__)
    def eventFilter(self, target, event):
        try:
            if event.type() == QEvent.Type.FocusOut:
                self.focusOutEvent(event)
        except:
            pass

        return False

    @err_catcher(name=__name__)
    def refreshUi(self):
        self.e_user.setText(self.core.username)
        self.e_abbreviation.setText(self.core.user)

    @err_catcher(name=__name__)
    def showEvent(self, event):
        self.signalShowing.emit()

    @err_catcher(name=__name__)
    def onUserChanged(self, text):
        abbr = self.core.users.getUserAbbreviation(userName=text, fromConfig=False)
        self.e_abbreviation.setText(abbr)

    @err_catcher(name=__name__)
    def onApply(self):
        user = self.e_user.text()
        abbr = self.e_abbreviation.text()

        if not user:
            msg = "Invalid username."
            self.core.popup(msg)
            return

        if not abbr:
            msg = "Invalid abbreviation."
            self.core.popup(msg)
            return

        self.core.users.setUser(user)
        self.core.users.setUserAbbreviation(abbr)
        self.close()
        self.origin.refreshUser()


if __name__ == "__main__":
    qapp = QApplication(sys.argv)
    pc = PrismCore.PrismCore(prismArgs=["loadProject", "noProjectBrowser"])
    pc.projectBrowser()
    sys.exit(qapp.exec_())
