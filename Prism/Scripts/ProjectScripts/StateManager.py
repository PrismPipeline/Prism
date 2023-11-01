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
import traceback
import time
import logging
import uuid

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2

uiPath = os.path.join(os.path.dirname(__file__), "UserInterfaces")
if uiPath not in sys.path:
    sys.path.append(uiPath)

if eval(os.getenv("PRISM_DEBUG", "False")):
    for module in ["StateManager_ui", "StateManager_ui_ps2"]:
        try:
            del sys.modules[module]
        except:
            pass

from PrismUtils import PrismWidgets
from PrismUtils.Decorators import err_catcher
from UserInterfaces import StateManager_ui


logger = logging.getLogger(__name__)


class StateManager(QMainWindow, StateManager_ui.Ui_mw_StateManager):
    def __init__(self, core, stateDataPath=None, forceStates=[], standalone=False):
        QMainWindow.__init__(self)
        self.setupUi(self)

        self.core = core
        self.core.parentWindow(self)

        logger.debug("Initializing State Manager")

        self.setWindowTitle(
            "Prism %s - State Manager - %s" % (self.core.version, self.core.projectName)
        )

        self.forceStates = forceStates
        self.scenename = self.core.getCurrentFileName()
        self.standalone = standalone
        self.prevStateData = None
        self.core.stateManagerInCreation = self
        self.finishedDeletionCallbacks = []

        self.enabledCol = QBrush(
            self.tw_import.palette().color(self.tw_import.foregroundRole())
        )

        self.layout().setContentsMargins(6, 6, 6, 0)

        self.disabledCol = QBrush(QColor(100, 100, 100))
        self.styleExists = "QWidget{padding: 0; border-width: 1px;border-color: transparent;background-color: rgba(60, 200, 100, 150)} QWidget:hover{background-color: rgba(60, 200, 100, 200); }"
        self.styleMissing = "QWidget{padding: 0; border-width: 1px;border-color: transparent;background-color: transparent} QWidget:hover{background-color: rgba(250, 250, 250, 40); }"

        if eval(os.getenv("PRISM_DEBUG", "False")):
            for module in ["ProductBrowser"]:
                try:
                    del sys.modules[module]
                except:
                    pass

                try:
                    del sys.modules[module + "_ui"]
                except:
                    pass

                try:
                    del sys.modules[module + "_ui_ps2"]
                except:
                    pass

        self.states = []
        self.stateUis = []
        self.stateTypes = {}

        self.description = ""
        self.previewImg = None
        self.publishComment = ""

        foldercont = ["", "", ""]

        self.saveEnabled = True
        self.loading = False
        self.shotcamFileType = ".abc"
        self.publishPaused = False
        self.entityDlg = EntityDlg
        self.applyChangesToSelection = True

        stateFiles = []
        pluginUiPath = os.path.join(
            self.core.appPlugin.pluginPath,
            "StateManagerNodes",
            "StateUserInterfaces",
        )
        if os.path.exists(pluginUiPath):
            sys.path.append(os.path.dirname(pluginUiPath))
            sys.path.append(pluginUiPath)

            for i in os.walk(os.path.dirname(pluginUiPath)):
                foldercont = i
                break
            stateFiles += foldercont[2]

        sys.path.append(os.path.join(os.path.dirname(__file__), "StateManagerNodes"))
        sys.path.append(
            os.path.join(
                os.path.dirname(__file__), "StateManagerNodes", "StateUserInterfaces"
            )
        )

        statePath = os.path.join(os.path.dirname(__file__), "StateManagerNodes")
        for root, folders, files in os.walk(statePath):
            stateFiles += [os.path.join(root, file) for file in files]
            break

        for file in stateFiles:
            self.loadStateTypeFromFile(file)

        self.core.callback(name="onStateManagerOpen", args=[self])

        self.loadLayout()
        self.setListActive(self.tw_export)
        self.core.smCallbacksRegistered = True
        self.connectEvents()
        self.loadStates()
        self.gb_import.setChecked(False)
        self.setListActive(self.tw_export)
        self.showState()
        self.activeList.setFocus()
        self.stateListToggled(self.gb_export, True)
        self.commentChanged(self.e_comment.text())

        screen = self.core.getQScreenGeo()
        if screen:
            screenW = screen.width()
            screenH = screen.height()
            space = 100
            if screenH < (self.height() + space):
                self.resize(self.width(), screenH - space)

            if screenW < (self.width() + space):
                self.resize(screenW - space, self.height())

    @err_catcher(name=__name__)
    def loadStateTypeFromFile(self, filepath):
        try:
            filename = os.path.basename(filepath)

            if os.path.splitext(filename)[0] == "__init__":
                return

            if os.path.splitext(filename)[1] == ".pyc" and os.path.exists(
                os.path.splitext(filename)[0] + ".py"
            ):
                return

            stateName = os.path.splitext(filename)[0]
            stateNameBase = stateName

            if " " in stateName or "(" in stateName:
                if getattr(self.core, "deleteInvalidStates", False):
                    try:
                        os.remove(filepath)
                    except:
                        logger.warning("failed to remove file: %s" % filepath)

                return

            if stateName.startswith("default_") or stateName.startswith(
                self.core.appPlugin.appShortName.lower()
            ):
                stateNameBase = stateNameBase.replace(
                    stateName.split("_", 1)[0] + "_", ""
                )

            if stateNameBase in self.stateTypes and stateName not in self.forceStates:
                return

            stateUi = stateName + "_ui"
            if eval(os.getenv("PRISM_DEBUG", "False")):
                try:
                    del sys.modules[stateName]
                except:
                    pass

                try:
                    del sys.modules[stateName + "_ui"]
                except:
                    pass

            try:
                exec(
                    """
import %s
import %s
class %s(QWidget, %s.%s, %s.%sClass):
    def __init__(self):
        QWidget.__init__(self)
        self.setupUi(self)"""
                    % (
                        stateName,
                        stateUi,
                        stateNameBase + "Class",
                        stateName + "_ui",
                        "Ui_wg_" + stateNameBase,
                        stateName,
                        stateNameBase,
                    )
                )
                validState = True
            except:
                logger.warning(traceback.format_exc())
                validState = False

            if validState:
                classDef = eval(stateNameBase + "Class")
                self.loadState(classDef, filename=filename)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            erStr = "%s ERROR - StateManager %s:\n%s" % (
                time.strftime("%d/%m/%y %X"),
                self.core.version,
                traceback.format_exc(),
            )
            self.core.writeErrorLog(erStr)

    @err_catcher(name=__name__)
    def loadState(self, clsDef, filename=None):
        try:
            if not clsDef.isActive(self.core):
                return
        except:
            pass

        clsDef.core = self.core
        logger.debug("loaded state %s" % (filename or clsDef.className))
        self.stateTypes[clsDef.className] = clsDef

    @err_catcher(name=__name__)
    def loadLayout(self):
        self.actionVersionUp = QAction("Version Up scenefile on publish", self)
        self.actionVersionUp.setCheckable(True)
        self.actionVersionUp.setChecked(self.core.getConfig("stateManager", "versionUpSceneOnPublish", dft=True))
        self.actionVersionUp.toggled.connect(self.onVersionUpToggled)
        self.menuAbout.insertAction(self.actionCopyStates, self.actionVersionUp)
        self.menuAbout.insertSeparator(self.actionCopyStates)

        helpMenu = QMenu("Help", self)

        self.actionWebsite = QAction("Visit website", self)
        self.actionWebsite.triggered.connect(lambda: self.core.openWebsite("home"))
        helpMenu.addAction(self.actionWebsite)

        self.actionWebsite = QAction("Tutorials", self)
        self.actionWebsite.triggered.connect(lambda: self.core.openWebsite("tutorials"))
        helpMenu.addAction(self.actionWebsite)

        self.actionWebsite = QAction("Documentation", self)
        self.actionWebsite.triggered.connect(
            lambda: self.core.openWebsite("documentation")
        )
        helpMenu.addAction(self.actionWebsite)

        self.actionAbout = QAction("About...", self)
        self.actionAbout.triggered.connect(self.core.showAbout)
        helpMenu.addAction(self.actionAbout)

        self.menubar.addMenu(helpMenu)

        self.actionSendFeedback = QAction("Send feedback...", self)
        self.actionSendFeedback.triggered.connect(self.core.sendFeedbackDlg)
        self.menubar.addAction(self.actionSendFeedback)

        try:
            self.menuRecentProjects.setToolTipsVisible(True)
        except:
            pass

        rpAct = QAction("Manage Projects...", self)
        rpAct.setToolTip("Open Project Overview")
        rpAct.triggered.connect(self.core.projects.setProject)
        self.menuRecentProjects.addAction(rpAct)

        recentProjects = self.core.projects.getRecentProjects()
        for project in recentProjects:
            rpAct = QAction(project["name"], self)
            rpAct.setToolTip(project["configPath"])

            rpAct.triggered.connect(
                lambda y=None, x=project["configPath"]: self.core.changeProject(x)
            )
            self.menuRecentProjects.addAction(rpAct)

        if self.description == "":
            self.b_description.setStyleSheet(self.styleMissing)
        else:
            self.b_description.setStyleSheet(self.styleExists)
        self.b_preview.setStyleSheet(self.styleMissing)

        self.gb_import.setObjectName("list")
        self.gb_export.setObjectName("list")

        if "Render Settings" in self.stateTypes:
            self.actionRenderSettings = QAction("Rendersettings presets...", self)
            self.actionRenderSettings.triggered.connect(self.showRenderPresets)
            self.menuAbout.addSeparator()
            self.menuAbout.addAction(self.actionRenderSettings)

        self.ImportDelegate = ImportDelegate(self)
        self.tw_import.setItemDelegate(self.ImportDelegate)

        self.gb_import.setCheckable(True)
        self.gb_export.setCheckable(True)

        self.splitter.setStyleSheet(
            'QSplitter::handle{background-image: "";background-color: transparent}'
        )

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "shot.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.b_preview.setIcon(icon)

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "text.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.b_description.setIcon(icon)

    @err_catcher(name=__name__)
    def onVersionUpToggled(self, state):
        self.core.setConfig("stateManager", "versionUpSceneOnPublish", val=state, config="user")

    @err_catcher(name=__name__)
    def showRenderPresets(self):
        rsUi = self.stateTypes["Render Settings"]()
        rsUi.setup(None, self.core, self)
        rsUi.f_name.setVisible(False)
        rsUi.setMinimumHeight(0)
        rsUi.setMaximumWidth(16777215)
        rsUi.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        rsUi.chb_editSettings.stateChanged.connect(self.editPresetChanged)
        rsUi.updateUi()
        self.dlg_settings = QDialog()
        self.dlg_settings.setWindowTitle("Rendersettings - Presets")
        bb_settings = QDialogButtonBox()
        bb_settings.addButton("Close", QDialogButtonBox.RejectRole)
        bb_settings.rejected.connect(self.dlg_settings.reject)

        lo_settings = QVBoxLayout()
        lo_settings.addWidget(rsUi)

        self.dlg_settings.spacer = QWidget()
        policy = QSizePolicy()
        policy.setVerticalPolicy(QSizePolicy.Expanding)
        policy.setVerticalStretch(5)
        self.dlg_settings.spacer.setSizePolicy(policy)
        lo_settings.addWidget(self.dlg_settings.spacer)

        lo_settings.addWidget(bb_settings)
        self.dlg_settings.setLayout(lo_settings)
        self.core.parentWindow(self.dlg_settings)

        self.dlg_settings.show()

    @err_catcher(name=__name__)
    def editPresetChanged(self, state):
        QCoreApplication.processEvents()
        self.dlg_settings.resize(0, 0)
        self.dlg_settings.spacer.setVisible(not state)

    @err_catcher(name=__name__)
    def setTreePalette(self, listWidget, inactive, inactivef, activef):
        actStyle = "QTreeWidget { border: 1px solid rgb(150,150,150); }"
        inActStyle = "QTreeWidget { border: 1px solid rgb(30,30,30); }"
        listWidget.setStyleSheet(
            listWidget.styleSheet().replace(actStyle, "").replace(inActStyle, "")
            + actStyle
        )
        inactive.setStyleSheet(
            inactive.styleSheet().replace(actStyle, "").replace(inActStyle, "")
            + inActStyle
        )

    @err_catcher(name=__name__)
    def collapseFolders(self):
        if not hasattr(self, "collapsedFolders"):
            return

        for i in self.collapsedFolders:
            i.setExpanded(False)

        for state in self.getSelectedStates():
            self.ensureVisibility(state)

    @err_catcher(name=__name__)
    def selectState(self, state):
        if not state:
            return

        if state.ui.listType == "Import":
            listwidget = self.tw_import
        else:
            listwidget = self.tw_export

        self.setListActive(listwidget)
        listwidget.clearSelection()
        state.setSelected(True)
        listwidget.setCurrentItem(state)
        self.showState()

    @err_catcher(name=__name__)
    def ensureVisibility(self, state):
        parent = state.parent()
        while parent:
            parent.setExpanded(True)
            parent = parent.parent()

    @err_catcher(name=__name__)
    def getSelectedStates(self):
        states = []
        for state in self.states:
            if state.isSelected():
                states.append(state)

        return states

    @err_catcher(name=__name__)
    def showState(self):
        try:
            grid = QGridLayout()
        except:
            return False

        if self.getCurrentItem(self.activeList) is not None:
            grid.addWidget(self.getCurrentItem(self.activeList).ui)

        widget = QWidget()
        widget.setLayout(grid)

        if hasattr(self, "curUi"):
            self.lo_stateUi.takeAt(0)
            self.curUi.setVisible(False)

        self.lo_stateUi.addWidget(widget)
        if self.getCurrentItem(self.activeList) is not None:
            self.getCurrentItem(self.activeList).ui.updateUi()

        self.curUi = widget

    @err_catcher(name=__name__)
    def stateChanged(self, activeList):
        if self.loading:
            return False

        self.showState()

    @err_catcher(name=__name__)
    def setListActive(self, listWidget):
        if listWidget == self.tw_import:
            inactive = self.tw_export
            inactivef = self.f_export
            activef = self.f_import
            self.gb_import.setChecked(True)
        else:
            inactive = self.tw_import
            inactivef = self.f_import
            activef = self.f_export
            self.gb_export.setChecked(True)

        inactive.clearSelection()
        inactive.setCurrentIndex(QModelIndex())

        getattr(
            self.core.appPlugin,
            "sm_setActivePalette",
            lambda x1, x2, x3, x4, x5: self.setTreePalette(x2, x3, x4, x5),
        )(self, listWidget, inactive, inactivef, activef)

        self.inactiveList = inactive
        self.activeList = listWidget
        self.activeList.setFocus()

    @err_catcher(name=__name__)
    def focusImport(self, event):
        self.setListActive(self.tw_import)
        self.tw_export.setCurrentIndex(self.tw_export.model().createIndex(-1, 0))
        event.accept()

    @err_catcher(name=__name__)
    def focusExport(self, event):
        self.setListActive(self.tw_export)
        self.tw_import.setCurrentIndex(self.tw_import.model().createIndex(-1, 0))
        event.accept()

    @err_catcher(name=__name__)
    def updateForeground(self, item=None, column=None, activeList=None):
        if activeList is not None:
            if activeList == self.tw_import:
                inactive = self.tw_export
            else:
                inactive = self.tw_import
            # inactive.setCurrentIndex(inactive.model().createIndex(-1,0))

        for i in range(self.tw_export.topLevelItemCount()):
            item = self.tw_export.topLevelItem(i)
            if item.checkState(0) == Qt.Checked:
                fcolor = self.enabledCol
                if item.text(0).endswith(" - disabled"):
                    item.setText(0, item.text(0)[: -len(" - disabled")])
            else:
                fcolor = self.disabledCol
                if not item.text(0).endswith(" - disabled"):
                    item.setText(0, item.text(0) + " - disabled")

            item.setForeground(0, fcolor)
            for k in range(item.childCount()):
                self.enableChildren(item.child(k), fcolor)

    @err_catcher(name=__name__)
    def enableChildren(self, item, fcolor):
        if item.checkState(0) == Qt.Unchecked:
            fcolor = self.disabledCol

        if fcolor == self.disabledCol:
            if not item.text(0).endswith(" - disabled"):
                item.setText(0, item.text(0) + " - disabled")
        elif item.text(0).endswith(" - disabled"):
            item.setText(0, item.text(0)[: -len(" - disabled")])

        item.setForeground(0, fcolor)
        for i in range(item.childCount()):
            self.enableChildren(item.child(i), fcolor)

    @err_catcher(name=__name__)
    def updateStateList(self):
        stateData = []
        for i in range(self.tw_import.topLevelItemCount()):
            stateData.append([self.tw_import.topLevelItem(i), None])
            self.appendChildStates(stateData[len(stateData) - 1][0], stateData)

        for i in range(self.tw_export.topLevelItemCount()):
            stateData.append([self.tw_export.topLevelItem(i), None])
            self.appendChildStates(stateData[len(stateData) - 1][0], stateData)

        self.states = [x[0] for x in stateData]

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.actionPrismSettings.triggered.connect(self.core.prismSettings)
        self.actionProjectBrowser.triggered.connect(self.core.projectBrowser)
        self.actionCopyStates.triggered.connect(self.copyAllStates)
        self.actionPasteStates.triggered.connect(self.pasteStates)
        self.actionRemoveStates.triggered.connect(self.removeAllStates)

        self.gb_import.toggled.connect(
            lambda x, y=self.gb_import: self.stateListToggled(y, x)
        )
        self.gb_export.toggled.connect(
            lambda x, y=self.gb_export: self.stateListToggled(y, x)
        )

        self.tw_import.customContextMenuRequested.connect(
            lambda x: self.rclTree(x, self.tw_import)
        )
        self.tw_import.itemSelectionChanged.connect(
            lambda: self.stateChanged(self.tw_import)
        )
        self.tw_import.itemClicked.connect(
            lambda x, y: self.updateForeground(x, y, self.tw_import)
        )
        self.tw_import.itemDoubleClicked.connect(self.focusRename)
        self.tw_import.focusOutEvent = self.checkFocusOut
        self.tw_import.keyPressEvent = self.checkKeyPressed
        self.tw_import.focusInEvent = self.focusImport
        self.tw_import.origDropEvent = self.tw_import.dropEvent
        self.tw_import.dropEvent = self.handleImportDrop
        self.tw_import.itemCollapsed.connect(self.saveStatesToScene)
        self.tw_import.itemExpanded.connect(self.saveStatesToScene)

        self.tw_export.customContextMenuRequested.connect(
            lambda x: self.rclTree(x, self.tw_export)
        )
        self.tw_export.itemSelectionChanged.connect(
            lambda: self.stateChanged(self.tw_export)
        )
        self.tw_export.itemClicked.connect(
            lambda x, y: self.updateForeground(x, y, self.tw_export)
        )
        self.tw_export.itemChanged.connect(lambda x, y: self.saveStatesToScene())
        self.tw_export.itemDoubleClicked.connect(self.focusRename)
        self.tw_export.focusOutEvent = self.checkFocusOut
        self.tw_export.keyPressEvent = self.checkKeyPressed
        self.tw_export.focusInEvent = self.focusExport
        self.tw_export.origDropEvent = self.tw_export.dropEvent
        self.tw_export.dropEvent = self.handleExportDrop
        self.tw_export.itemCollapsed.connect(self.saveStatesToScene)
        self.tw_export.itemExpanded.connect(self.saveStatesToScene)

        self.b_createImport.clicked.connect(lambda: self.createPressed("Import"))
        self.b_createExport.clicked.connect(lambda: self.createPressed("Export"))
        self.b_createRender.clicked.connect(lambda: self.createPressed("Render"))
        self.b_createPlayblast.clicked.connect(lambda: self.createPressed("Playblast"))
        self.b_shotCam.clicked.connect(self.shotCam)
        self.b_showImportStates.clicked.connect(
            lambda: self.showStateMenu("Import", useSelection=True)
        )
        self.b_showExportStates.clicked.connect(
            lambda: self.showStateMenu("Export", useSelection=True)
        )

        self.e_comment.textChanged.connect(self.commentChanged)
        self.e_comment.editingFinished.connect(self.saveStatesToScene)
        self.b_description.clicked.connect(self.showDescription)
        self.b_description.customContextMenuRequested.connect(self.clearDescription)
        self.b_preview.clicked.connect(self.getPreview)
        self.b_preview.customContextMenuRequested.connect(self.clearPreview)
        self.b_description.setMouseTracking(True)
        self.b_description.mouseMoveEvent = lambda x: self.detailMoveEvent(x, "d")
        self.b_description.leaveEvent = lambda x: self.detailLeaveEvent(x, "d")
        self.b_description.focusOutEvent = lambda x: self.detailFocusOutEvent(x, "d")
        self.b_preview.setMouseTracking(True)
        self.b_preview.mouseMoveEvent = lambda x: self.detailMoveEvent(x, "p")
        self.b_preview.leaveEvent = lambda x: self.detailLeaveEvent(x, "p")
        self.b_preview.focusOutEvent = lambda x: self.detailFocusOutEvent(x, "p")
        self.b_publish.clicked.connect(self.publish)

    @err_catcher(name=__name__)
    def closeEvent(self, event):
        self.core.callback(name="onStateManagerClose", args=[self])
        event.accept()

    @err_catcher(name=__name__)
    def focusRename(self, item, column):
        if item is not None:
            item.ui.e_name.setFocus()

    @err_catcher(name=__name__)
    def checkKeyPressed(self, event):
        if event.key() == Qt.Key_Tab:
            self.showStateMenu()
        elif event.key() == Qt.Key_Delete:
            self.deleteState()
        elif event.key() == Qt.Key_Up:
            self.selectPreviousState()
        elif event.key() == Qt.Key_Down:
            self.selectNextState()

        event.accept()

    @err_catcher(name=__name__)
    def checkFocusOut(self, event):
        if event.reason() == Qt.FocusReason.TabFocusReason:
            event.ignore()
            self.activeList.setFocus()
            self.showStateMenu()
        else:
            event.accept()

    @err_catcher(name=__name__)
    def handleImportDrop(self, event):
        self.tw_import.origDropEvent(event)
        self.updateForeground()
        self.saveStatesToScene()

    @err_catcher(name=__name__)
    def handleExportDrop(self, event):
        self.tw_export.origDropEvent(event)
        self.updateForeground()
        self.updateStateList()
        self.saveStatesToScene()

    @err_catcher(name=__name__)
    def stateListToggled(self, widget, state):
        for idx in reversed(range(widget.layout().count())):
            item = widget.layout().itemAt(idx)
            w = item.widget()
            if w:
                w.setHidden(not state)

        imgRight = self.core.prismRoot + "/Scripts/UserInterfacesPrism/right_arrow_light.png"
        imgDown = self.core.prismRoot + "/Scripts/UserInterfacesPrism/down_arrow_light.png"
        ssheet = """
QGroupBox::indicator:checked:hover,
QGroupBox::indicator:unchecked:hover
{
    background: rgba(255, 255, 255, 40);
    border-radius: 2px;
}
QGroupBox#list::title
{
    padding: 5px;
    margin: 5px;
    background: transparent;
}
QGroupBox::indicator:unchecked {
    image:url(%s);
    background: transparent;
    border-width: 0px;
}
QGroupBox::indicator:checked {
    image:url(%s);
    background: transparent;
    border-width: 0px;
}
""" % (
            imgRight,
            imgDown,
        )

        if self.core.appPlugin.pluginName == "3dsMax":
            ssheet += "QGroupBox#list::title{color: rgb(220, 220, 220);}"

        if not state:
            ssheet += "QWidget{ border-width: 0px;}"
            widget.layout().setContentsMargins(0, 0, 0, 0)
        else:
            widget.layout().setContentsMargins(5, 14, 5, 5)

        widget.setStyleSheet(ssheet)

    @err_catcher(name=__name__)
    def getStateTypes(self, listType=None):
        stateTypes = []
        stateNames = sorted(self.stateTypes.keys())

        for stateName in stateNames:
            if (
                stateName == "Folder"
                or listType is None
                or self.stateTypes[stateName].listType == listType
            ):
                stateTypes.append(stateName)

        return stateTypes

    @err_catcher(name=__name__)
    def getStateMenu(self, listType=None, parentState=None):
        if listType is None:
            listType = "Import" if self.activeList == self.tw_import else "Export"

        createMenu = QMenu("Create", self)
        typeNames = self.getStateTypes(listType)

        listWidget = self.tw_import if listType == "Import" else self.tw_export
        for typeName in typeNames:
            act = createMenu.addAction(typeName)
            act.triggered.connect(lambda: self.setListActive(listWidget))
            act.triggered.connect(
                lambda x=None, typeName=typeName: self.createState(
                    typeName, parentState, setActive=True
                )
            )

        if listType == "Export":
            getattr(self.core.appPlugin, "sm_openStateFromNode", lambda x, y: None)(
                self, createMenu
            )

        self.core.callback("getStateMenu", args=[self, createMenu])
        return createMenu

    @err_catcher(name=__name__)
    def getCurrentItem(self, widget):
        items = widget.selectedItems()
        if not items:
            return

        item = widget.currentItem()
        if not item:
            item = items[0]

        return item

    @err_catcher(name=__name__)
    def showStateMenu(self, listType=None, useSelection=False):
        globalPos = QCursor.pos()
        parentState = None
        if useSelection:
            listWidget = self.tw_import if listType == "Import" else self.tw_export
            if listWidget == self.activeList:
                parentState = self.getCurrentItem(self.activeList)
        else:
            pos = self.activeList.mapFromGlobal(globalPos)
            idx = self.activeList.indexAt(pos)
            parentState = self.activeList.itemFromIndex(idx)

        if parentState and parentState.ui.className != "Folder":
            parentState = None

        menu = self.getStateMenu(listType, parentState)
        menu.exec_(globalPos)

    @err_catcher(name=__name__)
    def rclTree(self, pos, activeList):
        rcmenu = QMenu(self)
        idx = self.activeList.indexAt(pos)
        parentState = self.activeList.itemFromIndex(idx)
        self.rClickedItem = parentState

        actExecute = QAction("Execute", self)
        actExecute.triggered.connect(lambda: self.publish(executeState=True))

        menuExecuteV = QMenu("Execute as previous version", self)

        actSort = None
        selItems = self.getSelectedStates()
        if len(selItems) > 1:
            parents = []
            for item in selItems:
                if item.parent() not in parents:
                    parents.append(item.parent())

            if len(parents) == 1:
                actSort = QAction("Sort", self)
                actSort.triggered.connect(lambda: self.sortStates(selItems))

        actCopy = QAction("Copy", self)
        actCopy.triggered.connect(self.copyState)

        actPaste = QAction("Paste", self)
        actPaste.triggered.connect(self.pasteStates)

        actRename = QAction("Rename", self)
        actRename.triggered.connect(self.renameState)

        actDel = QAction("Delete", self)
        actDel.triggered.connect(self.deleteState)

        if parentState is None:
            actCopy.setEnabled(False)
            actRename.setEnabled(False)
            actDel.setEnabled(False)
            actExecute.setEnabled(False)
            menuExecuteV.setEnabled(False)
        elif hasattr(parentState.ui, "l_pathLast"):
            outPath = parentState.ui.getOutputName()
            if not outPath or not outPath[0]:
                menuExecuteV.setEnabled(False)
            else:
                outPath = outPath[0]
                if "render" in parentState.ui.className.lower():
                    existingVersions = self.core.mediaProducts.getVersionsFromSameVersionStack(
                        outPath
                    )
                elif "playblast" in parentState.ui.className.lower():
                    existingVersions = self.core.mediaProducts.getVersionsFromSameVersionStack(
                        outPath, mediaType="playblasts"
                    )
                else:
                    existingVersions = self.core.products.getVersionsFromSameVersionStack(
                        outPath
                    )
                for version in sorted(
                    existingVersions, key=lambda x: x["version"], reverse=True
                ):
                    name = version["version"]
                    actV = QAction(name, self)
                    actV.triggered.connect(
                        lambda y=None, v=version["version"]: self.publish(
                            executeState=True, useVersion=v
                        )
                    )
                    menuExecuteV.addAction(actV)

        if menuExecuteV.isEmpty():
            menuExecuteV.setEnabled(False)

        if parentState is None or parentState.ui.className == "Folder":
            createMenu = self.getStateMenu(parentState=parentState)
            rcmenu.addMenu(createMenu)

        if self.activeList == self.tw_export:
            if not self.standalone:
                rcmenu.addAction(actExecute)
                rcmenu.addMenu(menuExecuteV)

        if actSort:
            rcmenu.addAction(actSort)

        rcmenu.addAction(actCopy)
        rcmenu.addAction(actPaste)
        rcmenu.addAction(actRename)
        rcmenu.addAction(actDel)

        rcmenu.exec_(self.activeList.mapToGlobal(pos))

    @err_catcher(name=__name__)
    def createState(
        self,
        statetype,
        parent=None,
        node=None,
        importPath=None,
        stateData=None,
        setActive=False,
        renderer=None,
        openProductsBrowser=None,
        settings=None
    ):
        logger.debug("create state: %s" % statetype)
        if statetype not in self.stateTypes:
            logger.warning("invalid state type: %s" % statetype)
            logger.debug("available state types: %s" % self.stateTypes)
            return False

        item = QTreeWidgetItem([statetype])
        item.ui = self.stateTypes[statetype]()
        self.stateUis.append(item.ui)

        kwargs = {
            "state": item,
            "core": self.core,
            "stateManager": self,
        }

        if node:
            kwargs["node"] = node
        else:
            kwargs["stateData"] = stateData
            if importPath:
                kwargs["importPath"] = importPath
            else:
                if renderer:
                    kwargs["renderer"] = renderer

        if openProductsBrowser is not None:
            kwargs["openProductsBrowser"] = openProductsBrowser

        if settings is not None:
            kwargs["settings"] = settings

        if item.ui.className == "Folder" and stateData is None:
            if self.activeList == self.tw_import:
                listType = "Import"
            else:
                listType = "Export"
        else:
            if stateData and "listtype" in stateData:
                listType = stateData["listtype"]
            else:
                listType = item.ui.listType

        if listType == "Import":
            pList = self.tw_import
        else:
            pList = self.tw_export

        if pList == self.tw_export:
            item.setCheckState(0, Qt.Checked)
            item.setFlags(item.flags() & ~Qt.ItemIsAutoTristate)

        stateSetup = item.ui.setup(**kwargs)

        if stateSetup is False:
            return

        if stateData and "uuid" in stateData:
            item.ui.uuid = stateData["uuid"]
        else:
            stateId = uuid.uuid4().hex
            item.ui.uuid = stateId

        self.core.scaleUI(item)

        if parent is None:
            pList.addTopLevelItem(item)
        else:
            parent.addChild(item)
            parent.setExpanded(True)

        self.updateStateList()
        self.stateInCreation = None

        if statetype != "Folder":
            item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled)

        self.core.callback(
            name="onStateCreated", args=[self, item.ui], **{"stateData": stateData}
        )

        if setActive:
            self.setListActive(pList)

        pList.clearSelection()
        self.selectState(item)
        self.updateForeground()

        if statetype != "Folder" and self.stateTypes[statetype].listType == "Import":
            self.saveImports()

        self.saveStatesToScene()
        return item

    @err_catcher(name=__name__)
    def copyAllStates(self):
        stateData = getattr(self.core.appPlugin, "sm_readStates", lambda x: None)(self)

        cb = QClipboard()
        cb.setText(stateData)

    @err_catcher(name=__name__)
    def pasteStates(self):
        cb = QClipboard()
        try:
            rawText = cb.text("plain")[0]
        except:
            QMessageBox.warning(
                self.core.messageParent,
                "Paste states",
                "No valid state data in clipboard.",
            )
            return

        self.loadStates(rawText)

        self.showState()
        self.activeList.clearFocus()
        self.activeList.setFocus()

    @err_catcher(name=__name__)
    def selectNextState(self):
        states = self.getSelectedStates()
        if not states:
            return

        state = self.getStateAfterState(states[-1])
        if state:
            self.selectState(state)

    @err_catcher(name=__name__)
    def selectPreviousState(self):
        states = self.getSelectedStates()
        if not states:
            return

        state = self.getStateBeforeState(states[0])
        if state:
            self.selectState(state)

    @err_catcher(name=__name__)
    def removeAllStates(self, quiet=False):
        if self.core.uiAvailable and not quiet:
            msg = "Are you sure you want to delete all states in the current scene?"
            result = self.core.popupQuestion(msg, buttons=["Yes", "Cancel"])

            if result == "Cancel":
                return

        self.core.appPlugin.sm_deleteStates(self)
        return self.core.closeSM(restart=True)

    @err_catcher(name=__name__)
    def sortStates(self, states):
        states = sorted(states, key=lambda x: getattr(x.ui, "getSortKey", lambda: "")() or "")
        for idx, state in enumerate(states[1:]):
            afterState = states[idx]
            self.moveStateAfterState(state, afterState)

    @err_catcher(name=__name__)
    def copyState(self):
        selStateData = [[s, None] for s in self.getSelectedStates()]
        self.appendChildStates(selStateData[len(selStateData) - 1][0], selStateData)

        stateData = {"states": []}

        for idx, i in enumerate(selStateData):
            stateProps = {}
            stateProps["stateparent"] = str(i[1])
            stateProps["stateclass"] = i[0].ui.className
            stateProps.update(i[0].ui.getStateProps())
            stateData["states"].append(stateProps)

        stateStr = self.core.configs.writeJson(stateData)

        cb = QClipboard()
        cb.setText(stateStr)

    @err_catcher(name=__name__)
    def renameState(self):
        states = self.getSelectedStates()
        name = states[0].ui.e_name.text()
        dlg_ec = PrismWidgets.CreateItem(
            core=self.core, startText=name, showType=False, valueRequired=False, validate=False
        )

        dlg_ec.setModal(True)
        self.core.parentWindow(dlg_ec)
        dlg_ec.e_item.setFocus()
        dlg_ec.setWindowTitle("Rename State")
        dlg_ec.l_item.setText("Name:")
        dlg_ec.buttonBox.buttons()[0].setText("Ok")
        result = dlg_ec.exec_()
        if not result:
            return

        newName = dlg_ec.e_item.text()
        for state in states:
            state.ui.e_name.setText(newName)

    @err_catcher(name=__name__)
    def deleteState(self, state=None, **kwargs):
        if state is None:
            items = self.getSelectedStates()
        else:
            items = [state]

        if not items:
            return

        self.finishedDeletionCallbacks = []
        for item in items:
            for i in range(item.childCount()):
                self.deleteState(item.child(i))

            delKwargs = {"item": item}
            delKwargs.update(kwargs)

            try:
                getattr(item.ui, "preDelete", lambda **kwargs: None)(**delKwargs)
            except:
                pass

            # self.states.remove(item) #buggy in qt 4

            newstates = []
            for i in self.states:
                if id(i) != id(item):
                    newstates.append(i)

            self.states = newstates

            parent = item.parent()
            if parent is None:
                if item.ui.listType == "Export":
                    iList = self.tw_export
                else:
                    iList = self.tw_import
                try:

                    idx = iList.indexOfTopLevelItem(item)
                except:
                    # bug in PySide2
                    for i in range(iList.topLevelItemCount()):
                        if iList.topLevelItem(i) is item:
                            idx = i

                if "idx" in locals():
                    iList.takeTopLevelItem(idx)
            else:
                idx = parent.indexOfChild(item)
                parent.takeChild(idx)

            self.core.callback(name="onStateDeleted", args=[self, item.ui])

            if item.ui.listType == "Import":
                self.saveImports()

        for cb in self.finishedDeletionCallbacks:
            cb()

        self.finishedDeletionCallbacks = []
        self.activeList.clearSelection()
        self.saveStatesToScene()

    @err_catcher(name=__name__)
    def createPressed(self, stateType, renderer=None):
        curSel = self.getCurrentItem(self.activeList)
        if stateType == "Import":
            if (
                self.activeList == self.tw_import
                and curSel is not None
                and curSel.ui.className == "Folder"
            ):
                parent = curSel
            else:
                parent = None

            createEmptyState = (
                QApplication.keyboardModifiers() == Qt.ControlModifier
                or not self.core.uiAvailable
            )

            if createEmptyState:
                stateType = "ImportFile"
                productPath = None
            else:
                import ProductBrowser

                ts = ProductBrowser.ProductBrowser(core=self.core)
                self.core.parentWindow(ts)
                ts.exec_()

                productPath = ts.productPath
                if not productPath:
                    return

                extension = os.path.splitext(productPath)[1]
                stateType = (
                    getattr(self.core.appPlugin, "sm_getImportHandlerType", lambda x: None)(
                        extension
                    )
                    or "ImportFile"
                )

            state = self.createState(stateType, parent=parent, importPath=productPath, setActive=True)
            if not createEmptyState and ts.customProduct and state:
                state.ui.e_name.setText(os.path.basename(productPath))

            self.activateWindow()

        elif stateType in ["Export", "Playblast", "Render"]:
            if (
                self.activeList == self.tw_export
                and curSel is not None
                and curSel.ui.className == "Folder"
            ):
                parent = curSel
            else:
                parent = None

            exportStates = []
            appStates = getattr(self.core.appPlugin, "sm_createStatePressed", lambda x, y: [])(self, stateType)
            if not isinstance(appStates, list):
                self.createState(appStates["stateType"], parent=parent, setActive=True, **appStates.get("kwargs", {}))
                return

            exportStates += appStates
            for state in self.stateTypes:
                exportStates += getattr(self.stateTypes[state], "stateCategories", {}).get(stateType, [])

            if len(exportStates) == 1:
                self.createState(exportStates[0]["stateType"], parent=parent, setActive=True)
            else:
                menu = QMenu(self)
                for exportState in exportStates:
                    actSet = QAction(exportState["label"], self)
                    actSet.triggered.connect(
                        lambda x=None, st=exportState: self.createState(st["stateType"], parent=parent, setActive=True, **st.get("kwargs", {}))
                    )
                    menu.addAction(actSet)

                getattr(self.core.appPlugin, "sm_openStateFromNode", lambda x, y, stateType: None)(
                    self, menu, stateType=stateType
                )

                if not menu.isEmpty():
                    menu.exec_(QCursor.pos())

        self.activeList.setFocus()

    @err_catcher(name=__name__)
    def shotCam(self):
        self.saveEnabled = False
        for i in self.states:
            if i.ui.className == "ImportFile" and i.ui.taskName == "ShotCam":
                mCamState = i.ui
                camState = i

        if "mCamState" in locals():
            mCamState.importLatest()
            self.selectState(mCamState)
        else:
            fileName = self.core.getCurrentFileName()
            fnameData = self.core.getScenefileData(fileName)
            if not (
                os.path.exists(fileName)
                and self.core.fileInPipeline(fileName)
            ):
                self.core.showFileNotInProjectWarning(title="Warning")
                self.saveEnabled = True
                return False

            if fnameData.get("type") != "shot":
                msgStr = "Shotcams are not supported for assets."
                self.core.popup(msgStr)
                self.saveEnabled = True
                return False

            filepath = self.core.products.getLatestVersionpathFromProduct(
                "_ShotCam", entity=fnameData
            )
            if not filepath:
                self.core.popup("Could not find a shotcam for the current shot.")
                self.saveEnabled = True
                return False

            self.createState("ImportFile", importPath=filepath, setActive=True)

        self.setListActive(self.tw_import)
        self.activateWindow()
        self.activeList.setFocus()
        self.saveEnabled = True
        self.saveStatesToScene()

    def enterEvent(self, event):
        try:
            QApplication.restoreOverrideCursor()
        except:
            pass

    def showEvent(self, event):
        for state in self.states:
            state.ui.updateUi()

        self.b_publish.setMinimumWidth(self.b_publish.width())
        self.core.callback("onStateManagerShow", args=[self])

    @err_catcher(name=__name__)
    def loadStates(self, stateText=None):
        if self.standalone and not stateText:
            return False

        self.saveEnabled = False
        self.loading = True
        if stateText is None:
            stateText = getattr(self.core.appPlugin, "sm_readStates", lambda x: None)(
                self
            )

        stateData = None
        if stateText is not None:
            stateData = []
            jsonData = self.core.configs.readJson(data=stateText)
            if jsonData and "states" in jsonData:
                stateData = jsonData["states"]
            else:
                stateConfig = self.core.configs.readIni(data=stateText)
                if not stateConfig.sections():
                    self.core.popup("Loading states failed.", "Prism - Load states")
                    stateData = None
                else:
                    for i in stateConfig.sections():
                        stateProps = {}
                        stateProps["statename"] = i
                        for k in stateConfig.options(i):
                            stateProps[k] = stateConfig.get(i, k)

                        stateData.append(stateProps)

        self.collapsedFolders = []

        if stateData:
            loadedStates = []
            for i in stateData:
                if i.get("statename") == "publish":
                    self.loadSettings(i)
                else:
                    stateParent = None
                    if i["stateparent"] != "None":
                        stateParent = loadedStates[int(i["stateparent"]) - 1]
                    state = self.createState(
                        i["stateclass"], parent=stateParent, stateData=i
                    )
                    loadedStates.append(state)

        self.inactiveList.clearSelection()
        self.loading = False
        self.saveEnabled = True
        self.saveStatesToScene()

    @err_catcher(name=__name__)
    def loadSettings(self, data):
        if "comment" in data:
            self.e_comment.setText(data["comment"])
        if "description" in data:
            self.description = data["description"]
            if self.description == "":
                self.b_description.setStyleSheet(self.styleMissing)
            else:
                self.b_description.setStyleSheet(self.styleExists)

    @err_catcher(name=__name__)
    def getSettings(self):
        stateProps = {}
        stateProps.update(
            {
                "statename": "publish",
                "comment": str(self.e_comment.text()),
                "description": self.description,
            }
        )
        return stateProps

    @err_catcher(name=__name__)
    def saveStatesToScene(self, param=None):
        if not self.saveEnabled:
            return False

        if self.standalone:
            return False

        getattr(self.core.appPlugin, "sm_preSaveToScene", lambda x: None)(self)
        stateStr = self.getStateSettings()
        getattr(self.core.appPlugin, "sm_saveStates", lambda x, y: None)(self, stateStr)

    @err_catcher(name=__name__)
    def getStateSettings(self):
        self.stateData = []
        for i in range(self.tw_import.topLevelItemCount()):
            self.stateData.append([self.tw_import.topLevelItem(i), None])
            self.appendChildStates(
                self.stateData[len(self.stateData) - 1][0], self.stateData
            )

        for i in range(self.tw_export.topLevelItemCount()):
            self.stateData.append([self.tw_export.topLevelItem(i), None])
            self.appendChildStates(
                self.stateData[len(self.stateData) - 1][0], self.stateData
            )

        selStates = self.getSelectedStates()
        if self.applyChangesToSelection and len(selStates) > 1 and self.prevStateData and len(self.prevStateData["states"]) == (len(self.stateData) + 1):
            curItem = self.getCurrentItem(self.activeList)
            curData = curItem.ui.getStateProps()
            for idx, val in enumerate(self.stateData):
                if val[0].__hash__() == curItem.__hash__():
                    cid = idx
                    break

            prevData = self.prevStateData["states"][cid+1]
            changes = {}
            for item in curData.items():
                if item[1] != prevData[item[0]]:
                    changes.update({item[0]: item[1]})

            self.saveEnabled = False
            for selState in selStates:
                if selState.__hash__() == self.getCurrentItem(self.activeList).__hash__():
                    continue

                selState.ui.loadData(changes)

            self.saveEnabled = True

        stateData = {"states": []}
        stateData["states"].append(self.getSettings())

        for idx, i in enumerate(self.stateData):
            stateProps = {}
            stateProps["stateparent"] = str(i[1])
            stateProps["stateclass"] = i[0].ui.className
            stateProps["uuid"] = i[0].ui.uuid
            stateProps.update(i[0].ui.getStateProps())
            if "statename" not in stateProps and "stateName" not in stateProps:
                continue

            stateData["states"].append(stateProps)

        self.prevStateData = stateData
        stateStr = self.core.configs.writeJson(stateData)
        return stateStr

    @err_catcher(name=__name__)
    def saveImports(self):
        if not self.saveEnabled:
            return False

        if self.standalone:
            return False

        importPaths = str(self.getFilePaths(self.tw_import.invisibleRootItem(), []))
        getattr(self.core.appPlugin, "sm_saveImports", lambda x, y: None)(self, importPaths)

    @err_catcher(name=__name__)
    def updateAllImportStates(self):
        for state in self.states:
            if state.ui.listType != "Import":
                continue

            if not hasattr(state.ui, "checkLatestVersion"):
                continue

            versions = state.ui.checkLatestVersion()
            if versions:
                curVersion, latestVersion = versions
            else:
                curVersion = latestVersion = ""

            if curVersion.get("version") == "master":
                filepath = state.ui.getImportPath()
                curVersionName = self.core.products.getMasterVersionLabel(filepath)
            else:
                curVersionName = curVersion.get("version")

            if latestVersion.get("version") == "master":
                filepath = latestVersion["path"]
                latestVersionName = self.core.products.getMasterVersionLabel(filepath)
            else:
                latestVersionName = latestVersion.get("version")

            if curVersionName and latestVersionName and curVersionName != latestVersionName:
                state.ui.importLatest(refreshUi=False)

    @err_catcher(name=__name__)
    def getFilePaths(self, item, paths=[]):
        if (
            hasattr(item, "ui")
            and item.ui.className != "Folder"
            and item.ui.listType == "Import"
        ):
            paths.append([item.ui.getImportPath(), item.text(0)])
        for i in range(item.childCount()):
            paths = self.getFilePaths(item.child(i), paths)

        return paths

    @err_catcher(name=__name__)
    def appendChildStates(self, state, stateList):
        stateNum = len(stateList)
        for i in range(state.childCount()):
            stateList.append([state.child(i), stateNum])
            self.appendChildStates(state.child(i), stateList)

    @err_catcher(name=__name__)
    def commentChanged(self, text):
        required = self.core.getConfig("globals", "requirePublishComment", config="project", dft=True)
        if required:
            minLength = self.core.getConfig("globals", "publishCommentLength", config="project", dft=3)
        else:
            minLength = 0

        text = self.e_comment.text()
        if len(text) >= minLength:
            self.b_publish.setEnabled(True)
            self.b_publish.setText("Publish")
        else:
            self.b_publish.setEnabled(False)
            self.b_publish.setText(
                "Publish - (%s more chars needed in comment)"
                % (minLength - len(text))
            )

    @err_catcher(name=__name__)
    def showDescription(self):
        descriptionDlg = PrismWidgets.EnterText()
        descriptionDlg.buttonBox.removeButton(descriptionDlg.buttonBox.buttons()[1])
        descriptionDlg.setModal(True)
        self.core.parentWindow(descriptionDlg)
        descriptionDlg.setWindowTitle("Enter description")
        descriptionDlg.l_info.setText("Description:")
        descriptionDlg.te_text.setPlainText(self.description)
        descriptionDlg.exec_()

        self.description = descriptionDlg.te_text.toPlainText()
        if self.description == "":
            self.b_description.setStyleSheet(self.styleMissing)
        else:
            self.b_description.setStyleSheet(self.styleExists)
        self.saveStatesToScene()

    @err_catcher(name=__name__)
    def getPreview(self):
        from PrismUtils import ScreenShot

        self.setHidden(True)
        self.previewImg = ScreenShot.grabScreenArea(self.core)
        self.setHidden(False)
        if self.previewImg is None:
            self.b_preview.setStyleSheet(self.styleMissing)
        else:
            self.previewImg = self.previewImg.scaled(
                500, 281, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.b_preview.setStyleSheet(self.styleExists)

    @err_catcher(name=__name__)
    def clearDescription(self, pos=None):
        self.description = ""
        self.b_description.setStyleSheet(self.styleMissing)
        if hasattr(self, "detailWin") and self.detailWin.isVisible():
            self.detailWin.close()
        self.saveStatesToScene()

    @err_catcher(name=__name__)
    def clearPreview(self, pos=None):
        self.previewImg = None
        self.b_preview.setStyleSheet(self.styleMissing)
        if hasattr(self, "detailWin") and self.detailWin.isVisible():
            self.detailWin.close()

    @err_catcher(name=__name__)
    def detailMoveEvent(self, event, table):
        self.showDetailWin(event, table)
        if hasattr(self, "detailWin") and self.detailWin.isVisible():
            self.detailWin.move(
                QCursor.pos().x() + 20, QCursor.pos().y() - self.detailWin.height()
            )

    @err_catcher(name=__name__)
    def showDetailWin(self, event, detailType):
        if detailType == "d":
            detail = self.description
        elif detailType == "p":
            detail = self.previewImg

        if not detail:
            if hasattr(self, "detailWin") and self.detailWin.isVisible():
                self.detailWin.close()
            return

        if (
            not hasattr(self, "detailWin")
            or not self.detailWin.isVisible()
            or self.detailWin.detail != detail
        ):
            if hasattr(self, "detailWin"):
                self.detailWin.close()

            self.detailWin = QFrame()
            ss = getattr(self.core.appPlugin, "getFrameStyleSheet", lambda x: "")(self)
            self.detailWin.setStyleSheet(
                ss + """ .QFrame{ border: 2px solid rgb(100,100,100);} """
            )

            self.detailWin.detail = detail
            self.core.parentWindow(self.detailWin)
            winwidth = 320
            winheight = 10
            VBox = QVBoxLayout()
            if detailType == "p":
                l_prv = QLabel()
                l_prv.setPixmap(detail)
                l_prv.setStyleSheet("border: 1px solid rgb(100,100,100);")
                VBox.addWidget(l_prv)
                VBox.setContentsMargins(0, 0, 0, 0)
            elif detailType == "d":
                descr = QLabel(self.description)
                VBox.addWidget(descr)
            self.detailWin.setLayout(VBox)
            self.detailWin.setWindowFlags(
                Qt.FramelessWindowHint  # hides the window controls
                | Qt.WindowStaysOnTopHint  # forces window to top... maybe
                | Qt.SplashScreen  # this one hides it from the task bar!
            )

            self.detailWin.setGeometry(0, 0, winwidth, winheight)
            self.detailWin.setAttribute(Qt.WA_ShowWithoutActivating)
            self.detailWin.move(QCursor.pos().x() + 20, QCursor.pos().y())
            self.detailWin.show()

    @err_catcher(name=__name__)
    def detailLeaveEvent(self, event, table):
        if hasattr(self, "detailWin") and self.detailWin.isVisible():
            self.detailWin.close()

    @err_catcher(name=__name__)
    def detailFocusOutEvent(self, event, table):
        if hasattr(self, "detailWin") and self.detailWin.isVisible():
            self.detailWin.close()

    @err_catcher(name=__name__)
    def getImportStateOrder(self, par=None, stateOrder=None):
        if not par:
            par = self.tw_import.invisibleRootItem()

        stateOrder = stateOrder or []
        for idx in range(par.childCount()):
            child = par.child(idx)
            stateOrder.append(child)
            self.getImportStateOrder(par=child, stateOrder=stateOrder)

        return stateOrder

    @err_catcher(name=__name__)
    def getStateExecutionOrder(self, par=None, stateOrder=None):
        if not par:
            par = self.tw_export.invisibleRootItem()

        stateOrder = stateOrder or []
        for idx in range(par.childCount()):
            child = par.child(idx)
            stateOrder.append(child)
            self.getStateExecutionOrder(par=child, stateOrder=stateOrder)

        return stateOrder

    @err_catcher(name=__name__)
    def getStateBeforeState(self, state):
        if state.ui.listType == "Import":
            stateOrder = self.getImportStateOrder()
        else:
            stateOrder = self.getStateExecutionOrder()
    
        idx = stateOrder.index(state)
        if idx == 0:
            return

        state = stateOrder[idx-1]
        return state

    @err_catcher(name=__name__)
    def getStateAfterState(self, state):
        if state.ui.listType == "Import":
            stateOrder = self.getImportStateOrder()
        else:
            stateOrder = self.getStateExecutionOrder()

        idx = stateOrder.index(state)
        if idx == (len(stateOrder)-1):
            return

        state = stateOrder[idx+1]
        return state

    @err_catcher(name=__name__)
    def moveStateBeforeState(self, state, beforeState):
        par = state.parent()
        listWidget = self.tw_import if state.ui.listType == "Import" else self.tw_export
        if not par:
            par = listWidget.invisibleRootItem()

        state = par.takeChild(par.indexOfChild(state))
        par = beforeState.parent()
        if not par:
            par = listWidget.invisibleRootItem()

        par.insertChild(par.indexOfChild(beforeState), state)

    @err_catcher(name=__name__)
    def moveStateAfterState(self, state, afterState):
        par = state.parent()
        listWidget = self.tw_import if state.ui.listType == "Import" else self.tw_export
        if not par:
            par = listWidget.invisibleRootItem()

        state = par.takeChild(par.indexOfChild(state))
        par = afterState.parent()
        if not par:
            par = listWidget.invisibleRootItem()

        par.insertChild(par.indexOfChild(afterState)+1, state)

    @err_catcher(name=__name__)
    def getChildStates(self, state):
        states = [state]

        for i in range(state.childCount()):
            states.append(state.child(i))
            if state.child(i).ui.className == "Folder":
                states += self.getChildStates(state.child(i))

        return states

    @err_catcher(name=__name__)
    def publish(
        self,
        executeState=False,
        continuePublish=False,
        useVersion="next",
        states=None,
        successPopup=True,
        saveScene=None,
        incrementScene=None,
        sanityChecks=True,
        versionWarning=True,
    ):
        if self.publishPaused and not continuePublish:
            return

        if continuePublish:
            executeState = self.publishType == "execute"

        if executeState:
            self.publishType = "execute"
            if not continuePublish:
                self.execStates = states or self.getChildStates(
                    self.getCurrentItem(self.tw_export)
                )
            actionString = "Execute"
            actionString2 = "execution"
        else:
            self.publishType = "publish"
            if not continuePublish:
                self.execStates = states or self.states
    
            actionString = "Publish"
            actionString2 = "publish"

        if not executeState and not [
            x for x in self.execStates if x.checkState(0) == Qt.Checked
        ]:
            self.core.popup("No states to publish.")
            return

        if continuePublish:
            skipStates = [
                x["state"].state
                for x in self.publishResult
                if "publish paused" not in x["result"][0]
            ]
            self.execStates = [x for x in self.execStates if x not in set(skipStates)]
            self.publishPaused = False
            if self.pubMsg and self.pubMsg.msg.isVisible():
                self.pubMsg.msg.close()
        else:
            if useVersion != "next" and versionWarning:
                msg = (
                    'Are you sure you want to execute this state as version "%s"?\nThis may overwrite existing files.'
                    % useVersion
                )
                result = self.core.popupQuestion(
                    msg,
                    title=actionString,
                    buttons=["Continue", "Cancel"],
                    icon=QMessageBox.Warning,
                    escapeButton="Cancel",
                )

                if result == "Cancel":
                    return

            if sanityChecks:
                sanityResult = self.runSantityChecks(executeState)
                if not sanityResult:
                    return

            details = {}
            if self.description != "":
                details = {
                    "description": self.description,
                    "username": self.core.getConfig("globals", "username"),
                }

            if saveScene is None or saveScene is True:
                if executeState:
                    increment = False if incrementScene is None else incrementScene
                    sceneSaved = self.core.saveScene(
                        versionUp=increment, details=details, preview=self.previewImg
                    )
                else:
                    increment = self.actionVersionUp.isChecked() if incrementScene is None else incrementScene
                    sceneSaved = self.core.saveScene(
                        comment=self.e_comment.text(),
                        publish=True,
                        versionUp=increment,
                        details=details,
                        preview=self.previewImg,
                    )

                if not sceneSaved:
                    logger.debug(actionString + " canceled")
                    return

            self.publishStartTime = time.time()
            self.description = ""
            self.previewImg = None
            self.b_description.setStyleSheet(self.styleMissing)
            self.b_preview.setStyleSheet(self.styleMissing)
            self.saveStatesToScene()

            self.publishResult = []
            self.dependencies = []
            self.reloadScenefile = False
            self.publishInfos = {"updatedExports": {}, "backgroundRender": None}
            self.core.sceneOpenChecksEnabled = False
            self.publishComment = self.e_comment.text()

            getattr(self.core.appPlugin, "sm_preExecute", lambda x: None)(self)
            result = self.core.callback(name="prePublish", args=[self])
            for res in result:
                if isinstance(res, dict) and res.get("cancel", False):
                    return

        if executeState:
            for i in range(self.tw_export.topLevelItemCount()):
                curUi = self.tw_export.topLevelItem(i).ui
                if curUi.className == "Folder" or id(curUi.state) in set([id(s) for s in self.execStates]):
                    text = 'Executing "%s" - please wait..' % curUi.state.text(0)
                    self.pubMsg = self.core.waitPopup(self.core, text)
                    with self.pubMsg:
                        self.curExecutedState = curUi
                        if getattr(curUi, "canSetVersion", False):
                            result = curUi.executeState(
                                parent=self, useVersion=useVersion
                            )
                        else:
                            result = curUi.executeState(parent=self)

                        self.curExecutedState = None
                        if curUi.className == "Folder":
                            self.publishResult += result

                            for k in result:
                                if "publish paused" in k["result"][0]:
                                    self.publishPaused = True
                                    return
                        else:
                            self.publishResult.append(
                                {"state": curUi, "result": result}
                            )

                            if "publish paused" in result[0]:
                                self.publishPaused = True
                                return

        else:
            for i in range(self.tw_export.topLevelItemCount()):
                curUi = self.tw_export.topLevelItem(i).ui
                checked = self.tw_export.topLevelItem(i).checkState(0) == Qt.Checked
                if checked and curUi.state in set(self.execStates):
                    text = 'Executing "%s" - please wait..' % curUi.state.text(0)
                    self.pubMsg = self.core.waitPopup(self.core, text)
                    with self.pubMsg:
                        self.curExecutedState = curUi
                        exResult = curUi.executeState(parent=self)
                        self.curExecutedState = None
                        if curUi.className == "Folder":
                            self.publishResult += exResult

                            for k in exResult:
                                if "publish paused" in k["result"][0]:
                                    self.publishPaused = True
                                    return
                        else:
                            self.publishResult.append(
                                {"state": curUi, "result": exResult}
                            )

                            if exResult and "publish paused" in exResult[0]:
                                self.publishPaused = True
                                return

        getattr(self.core.appPlugin, "sm_postExecute", lambda x: None)(self)
        pubType = "stateExecution" if executeState else "publish"
        self.core.callback(
            name="postPublish", args=[self, pubType], **{"result": self.publishResult}
        )

        self.publishInfos = {"updatedExports": {}, "backgroundRender": None}
        self.dependencies = []
        self.core.sceneOpenChecksEnabled = True

        success = True
        for i in self.publishResult:
            if "error" in i["result"][0]:
                success = False

        try:
            self.core.pb.refreshUI()
        except:
            pass

        result = False
        if success:
            if getattr(self.core, "lastErrorTime", 0) > self.publishStartTime:
                msgStr = "The %s was completed with errors." % actionString2
            else:
                msgStr = "The %s was successful." % actionString2
                result = True

            if successPopup:
                self.core.popup(msgStr, title=actionString, severity="info", parent=self)
        else:
            infoString = ""
            for i in self.publishResult:
                if not i["result"]:
                    infoString += "unknown error\n"
                elif "publish paused" not in i["result"][0]:
                    infoString += i["result"][0] + "\n"

            msgStr = "Errors occured during the %s:\n\n" % actionString2 + infoString

            self.core.popup(msgStr, title=actionString, parent=self)

        if self.reloadScenefile:
            self.core.appPlugin.openScene(
                self, self.core.getCurrentFileName(), force=True
            )

        return result

    @err_catcher(name=__name__)
    def runSantityChecks(self, executeState):
        result = []
        extResult = getattr(self.core.appPlugin, "sm_getExternalFiles", lambda x: None)(self)
        if extResult is not None:
            extFiles, extFilesSource = extResult
        else:
            extFiles = []
            extFilesSource = []

        invalidFiles = []
        nonExistend = []
        for idx, i in enumerate(extFiles):
            i = self.core.fixPath(i)

            if not (
                i.startswith(self.core.projectPath)
                or (
                    self.core.useLocalFiles and i.startswith(self.core.localProjectPath)
                )
            ):
                if os.path.exists(i) and not i in invalidFiles:
                    invalidFiles.append(i)

            if (
                not os.path.exists(i)
                and not i in nonExistend
                and i != self.core.getCurrentFileName()
            ):
                exists = getattr(
                    self.core.appPlugin, "sm_existExternalAsset", lambda x, y: False
                )(self, i)
                if exists:
                    continue

                nonExistend.append(i)

        if len(invalidFiles) > 0:
            depTitle = "The current scene contains dependencies from outside the project folder:\n\n"
            depwarn = ""
            for i in invalidFiles:
                parmStr = getattr(
                    self.core.appPlugin, "sm_fixWarning", lambda x1, x2, x3, x4: ""
                )(self, i, extFiles, extFilesSource)

                depwarn += "\t%s\n\t%s\n\n" % (parmStr, i)

            result.append([depTitle, depwarn, 2])

        if len(nonExistend) > 0:
            depTitle = (
                "The current scene contains dependencies, which does not exist:\n\n"
            )
            depwarn = ""
            for i in nonExistend:
                parmStr = getattr(
                    self.core.appPlugin, "sm_fixWarning", lambda x1, x2, x3, x4: ""
                )(self, i, extFiles, extFilesSource)
                depwarn += "\t%s\n\t%s\n\n" % (parmStr, i)

            result.append([depTitle, depwarn, 2])

        warnings = []
        if len(result) > 0:
            warnings.append(["", result])

        if executeState:
            for i in range(self.tw_export.topLevelItemCount()):
                curState = self.tw_export.topLevelItem(i)
                if curState.ui.className == "Folder" or id(curState) in set([id(s) for s in self.execStates]):
                    if curState.ui.className == "Folder":
                        warnings += curState.ui.preExecuteState(states=self.execStates)
                    else:
                        warnings.append(curState.ui.preExecuteState())
        else:
            for i in range(self.tw_export.topLevelItemCount()):
                curState = self.tw_export.topLevelItem(i)
                if curState.checkState(0) == Qt.Checked and curState in set(
                    self.execStates
                ):
                    if curState.ui.className == "Folder":
                        warnings += curState.ui.preExecuteState()
                    else:
                        warnings.append(curState.ui.preExecuteState())

        warnString = ""
        if self.core.uiAvailable:
            for i in warnings:
                if len(i[1]) == 0:
                    continue

                if i[0] == "":
                    warnBase = ""
                else:
                    warnString += "- <b>%s</b>\n\n" % i[0]
                    warnBase = "\t"

                for k in i[1]:
                    if k[2] == 2:
                        warnString += (
                            warnBase
                            + (
                                '- <font color="yellow">%s</font>\n  %s\n'
                                % (k[0], k[1])
                            ).replace("\n", "\n" + warnBase)
                            + "\n"
                        )
                    elif k[2] == 3:
                        warnString += (
                            warnBase
                            + (
                                '- <font color="red">%s</font>\n  %s\n' % (k[0], k[1])
                            ).replace("\n", "\n" + warnBase)
                            + "\n"
                        )
        else:
            for i in warnings:
                if len(i[1]) == 0:
                    continue

                if i[0] == "":
                    warnBase = ""
                else:
                    warnString += "- %s\n" % i[0]
                    warnBase = "\t"

                for k in i[1]:
                    warnTitle = k[0].replace("\n", "")
                    warnMsg = k[1].replace("\n", "")
                    if k[2] == 2:
                        warnString += (
                            warnBase
                            + ("- %s\n  %s" % (warnTitle, warnMsg)).replace(
                                "\n", "\n" + warnBase
                            )
                            + "\n"
                        )
                    elif k[2] == 3:
                        warnString += (
                            warnBase
                            + ("- %s\n  %s" % (warnTitle, warnMsg)).replace(
                                "\n", "\n" + warnBase
                            )
                            + "\n"
                        )

        if warnString != "":
            if self.core.uiAvailable:
                warnDlg = QDialog()

                warnDlg.setWindowTitle("Publish warnings")
                l_info = QLabel(str("The following warnings have occurred:\n"))

                warnString = "<pre>%s</pre>" % warnString.replace(
                    "\n", "<br />"
                ).replace("\t", "    ")
                l_warnings = QLabel(warnString)
                l_warnings.setAlignment(Qt.AlignTop)

                sa_warns = QScrollArea()

                lay_warns = QHBoxLayout()
                lay_warns.addWidget(l_warnings)
                lay_warns.setContentsMargins(10, 10, 10, 10)
                lay_warns.addStretch()
                w_warns = QWidget()
                w_warns.setLayout(lay_warns)
                sa_warns.setWidget(w_warns)
                sa_warns.setWidgetResizable(True)

                bb_warn = QDialogButtonBox()

                bb_warn.addButton("Continue", QDialogButtonBox.AcceptRole)
                bb_warn.addButton("Cancel", QDialogButtonBox.RejectRole)

                bb_warn.accepted.connect(warnDlg.accept)
                bb_warn.rejected.connect(warnDlg.reject)

                bLayout = QVBoxLayout()
                bLayout.addWidget(l_info)
                bLayout.addWidget(sa_warns)
                bLayout.addWidget(bb_warn)
                warnDlg.setLayout(bLayout)
                warnDlg.setParent(self.core.messageParent, Qt.Window)
                warnDlg.resize(
                    1000 * self.core.uiScaleFactor, 500 * self.core.uiScaleFactor
                )

                action = warnDlg.exec_()

                if action == 0:
                    return

            else:
                logger.warning(warnString)

        return True

    @err_catcher(name=__name__)
    def getFrameRangeTypeToolTip(self, rangeType):
        tt = ""
        if rangeType == "Scene":
            tt = "The framerange from the timeline in the currently open scenefile is used."
        elif rangeType == "Shot":
            tt = "The shotrange is used, which can be set in the Project Browser per shot."
        elif rangeType == "Node":
            tt = "The framerange parameters on the node connected to this state will be used."
        elif rangeType == "Single Frame":
            tt = "Only the current frame in your scene will be evaluated."
        elif rangeType == "Custom":
            tt = "The startframe and endframe can be specified for this state."
        elif rangeType == "Expression":
            tt = "Allows to specify frames to render by an expression. Look at the tooltip of the expression field for more information."
        elif rangeType == "ExpressionField":
            tt = """* Single frames are defined by a single framenumber.
    Example: "55" will render frame 55

* Frameranges are defined by the startframe and endframe separated by a "-".
    Example: "30-75" will render frames 30, 31, 32, ... 74, 75

* Stepping is defined by "xn" after a framerange, where "n" is the amount of stepping (rendering every Nth frame).
    Example: "1-100x4" will render frames 1, 5, 9, 13 ... 93, 97

* Frameranges can be inverted by starting with the higher number first to render the frames with the higher number first.
    Example: "50-40" will render frames 50, 49, 48 ... 41, 40

* Multiple elements can be combined by a "," in any order.
    Example: "34, 5-10x2, 3, 150-200, 60" will render frames 34, 5, 7, 9, 3, 150, 151 ... 200, 60

Each framenumber will be evaluated not more than once. Specifying a frame multiple times in an expression like "2, 3, 3, 4" will render frame 3 only once.

This can be used to render a few frames across the whole range before rendering every frame from start to end.
Example: "1-100x10, 1-100" will render every 10th frame and then it will render all frames between 1-100, which haven't been rendered yet.

No frame will be rendered twice. This makes it easier to spot problems in the sequence at an early stage of the rendering."""

        return tt

    @err_catcher(name=__name__)
    def getStateProps(self):
        return {
            "comment": self.e_comment.text(),
            "description": self.description,
        }

    @err_catcher(name=__name__)
    def importFile(self, path, activateWindow=True, settings=None):
        if not path:
            return

        extension = os.path.splitext(path)[1]
        stateType = (
            getattr(self.core.appPlugin, "sm_getImportHandlerType", lambda x: None)(
                extension
            )
            or "ImportFile"
        )

        state = self.createState(stateType, importPath=path, setActive=True, settings=settings)
        if activateWindow:
            self.activateWindow()

        return state


class ImportDelegate(QStyledItemDelegate):
    def __init__(self, stateManager):
        super(ImportDelegate, self).__init__()
        self.stateManager = stateManager

    def paint(self, painterQPainter, optionQStyleOptionViewItem, indexQModelIndex):
        QStyledItemDelegate.paint(
            self, painterQPainter, optionQStyleOptionViewItem, indexQModelIndex
        )

        item = self.stateManager.tw_import.itemFromIndex(indexQModelIndex)
        color = getattr(item.ui, "statusColor", None)
        if not color:
            return

        rect = QRect(optionQStyleOptionViewItem.rect)
        curRight = optionQStyleOptionViewItem.rect.right()
        rect.setLeft(curRight - 10)

        painterQPainter.fillRect(rect, QBrush(item.ui.statusColor))


def getStateWindow(core, stateType, settings=None, connectBBox=True, parent=None):
    settings = settings or None
    #  stateNameBase = stateType.replace(stateType.split("_", 1)[0] + "_", "")
    sm = StateManager(core, forceStates=[stateType], standalone=True)
    item = sm.createState(stateType, stateData=settings)
    if not item:
        return

    dlg_settings = QDialog()
    core.parentWindow(dlg_settings, parent=parent)
    dlg_settings.setWindowTitle("Statesettings - %s" % stateType)
    dlg_settings.bb_settings = QDialogButtonBox()
    dlg_settings.bb_settings.addButton("Accept", QDialogButtonBox.AcceptRole)
    dlg_settings.bb_settings.addButton("Cancel", QDialogButtonBox.RejectRole)
    if connectBBox:
        dlg_settings.bb_settings.accepted.connect(dlg_settings.accept)
        dlg_settings.bb_settings.rejected.connect(dlg_settings.reject)

    dlg_settings.sa_state = QScrollArea()
    dlg_settings.sa_state.setWidget(item.ui)
    dlg_settings.sa_state.setWidgetResizable(True)
    dlg_settings.sa_state.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    lo_settings = QVBoxLayout()
    lo_settings.addWidget(dlg_settings.sa_state)
    lo_settings.addWidget(dlg_settings.bb_settings)
    dlg_settings.setLayout(lo_settings)
    dlg_settings.stateItem = item
    dlg_settings.sizeHint = lambda: QSize(420, dlg_settings.sa_state.viewportSizeHint().height() + 200)
    return dlg_settings


def openStateSettings(core, stateType, settings=None):
    dlg_settings = getStateWindow(stateType, settings)
    action = dlg_settings.exec_()

    if action == 0:
        return

    return dlg_settings.stateItem.ui.getStateProps()


class EntityDlg(QDialog):

    entitySelected = Signal(object)

    def __init__(self, origin, parent=None):
        super(EntityDlg, self).__init__()
        self.origin = origin
        self.parentDlg = parent
        self.core = self.origin.core
        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self):
        title = "Select entity"

        self.setWindowTitle(title)
        self.core.parentWindow(self, parent=self.parentDlg)

        import EntityWidget
        self.w_entities = EntityWidget.EntityWidget(core=self.core, refresh=True)
        self.w_entities.getPage("Assets").tw_tree.itemDoubleClicked.connect(self.itemDoubleClicked)
        self.w_entities.getPage("Shots").tw_tree.itemDoubleClicked.connect(self.itemDoubleClicked)
        self.w_entities.getPage("Assets").setSearchVisible(False)
        self.w_entities.getPage("Shots").setSearchVisible(False)

        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Select", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Close", QDialogButtonBox.RejectRole)

        self.bb_main.clicked.connect(self.buttonClicked)

        self.lo_main.addWidget(self.w_entities)
        self.lo_main.addWidget(self.bb_main)

    @err_catcher(name=__name__)
    def itemDoubleClicked(self, item, column):
        self.buttonClicked("select")

    @err_catcher(name=__name__)
    def buttonClicked(self, button):
        if button == "select" or button.text() == "Select":
            entities = self.w_entities.getCurrentData()
            if isinstance(entities, dict):
                entities = [entities]

            validEntities = []
            for entity in entities:
                if entity.get("type", "") not in ["asset", "shot"]:
                    continue

                validEntities.append(entity)

            if not validEntities:
                msg = "Invalid entity selected."
                self.core.popup(msg, parent=self)
                return

            self.entitySelected.emit(validEntities[0])

        self.close()

    @err_catcher(name=__name__)
    def sizeHint(self):
        return QSize(400, 400)
