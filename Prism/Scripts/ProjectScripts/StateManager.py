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
import traceback
import time
import imp
import logging

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

uiPath = os.path.join(os.path.dirname(__file__), "UserInterfaces")
if uiPath not in sys.path:
    sys.path.append(uiPath)

for i in ["StateManager_ui", "StateManager_ui_ps2", "CreateItem"]:
    try:
        del sys.modules[i]
    except:
        pass

if psVersion == 1:
    import StateManager_ui
else:
    import StateManager_ui_ps2 as StateManager_ui

try:
    import EnterText
except:
    modPath = imp.find_module("EnterText")[1]
    if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
        os.remove(modPath)
    import EnterText

try:
    import CreateItem
except:
    modPath = imp.find_module("CreateItem")[1]
    if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
        os.remove(modPath)
    import CreateItem

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class StateManager(QMainWindow, StateManager_ui.Ui_mw_StateManager):
    def __init__(self, core, stateDataPath=None, forceStates=[], standalone=False):
        QMainWindow.__init__(self)
        self.setupUi(self)

        self.core = core
        self.core.parentWindow(self)

        logger.debug("Initializing State Manager")

        self.setWindowTitle("Prism %s - State Manager - %s" %(self.core.version, self.core.projectName))

        self.forceStates = forceStates
        self.scenename = self.core.getCurrentFileName()
        self.standalone = standalone

        self.enabledCol = QBrush(
            self.tw_import.palette().color(self.tw_import.foregroundRole())
        )

        self.layout().setContentsMargins(6, 6, 6, 0)

        self.disabledCol = QBrush(QColor(100, 100, 100))
        self.styleExists = "QPushButton { border: 1px solid rgb(100,200,100); }"
        self.styleMissing = "QPushButton { border: 1px solid rgb(200,100,100); }"

        self.draggedItem = None

        for i in ["TaskSelection"]:
            try:
                del sys.modules[i]
            except:
                pass

            try:
                del sys.modules[i + "_ui"]
            except:
                pass

            try:
                del sys.modules[i + "_ui_ps2"]
            except:
                pass

        self.states = []
        self.stateTypes = {}

        self.description = ""
        self.previewImg = None

        foldercont = ["", "", ""]

        self.saveEnabled = True
        self.loading = False
        self.shotcamFileType = ".abc"
        self.publishPaused = False

        files = []
        pluginUiPath = os.path.join(
            self.core.pluginPathApp,
            self.core.appPlugin.pluginName,
            "Scripts",
            "StateManagerNodes",
            "StateUserInterfaces",
        )
        if os.path.exists(pluginUiPath):
            sys.path.append(os.path.dirname(pluginUiPath))
            sys.path.append(pluginUiPath)

            for i in os.walk(os.path.dirname(pluginUiPath)):
                foldercont = i
                break
            files += foldercont[2]

        sys.path.append(os.path.join(os.path.dirname(__file__), "StateManagerNodes"))
        sys.path.append(
            os.path.join(
                os.path.dirname(__file__), "StateManagerNodes", "StateUserInterfaces"
            )
        )

        for i in os.walk(os.path.join(os.path.dirname(__file__), "StateManagerNodes")):
            foldercont = i
            break
        files += foldercont[2]

        for i in files:
            self.loadStateTypeFromFile(i)

        fileName = self.core.getCurrentFileName()
        fileNameData = self.core.getScenefileData(fileName)

        self.b_shotCam.setEnabled(fileNameData["entity"] == "shot")

        self.core.callback(
            name="onStateManagerOpen", types=["curApp", "custom"], args=[self]
        )
        self.loadLayout()
        self.setListActive(self.tw_import)
        self.core.smCallbacksRegistered = True
        self.connectEvents()
        self.loadStates()
        self.showState()
        self.activeList.setFocus()

        self.commentChanged(self.e_comment.text())

        screenW = QApplication.desktop().screenGeometry().width()
        screenH = QApplication.desktop().screenGeometry().height()
        space = 100
        if screenH < (self.height() + space):
            self.resize(self.width(), screenH - space)

        if screenW < (self.width() + space):
            self.resize(screenW - space, self.height())

    @err_catcher(name=__name__)
    def loadStateTypeFromFile(self, filepath):
        try:
            filepath = os.path.basename(filepath)

            if os.path.splitext(filepath)[0] == "__init__":
                return

            if os.path.splitext(filepath)[1] == ".pyc" and os.path.exists(os.path.splitext(filepath)[0] + ".py"):
                return

            stateName = os.path.splitext(filepath)[0]
            stateNameBase = stateName

            if stateName.startswith("default_") or stateName.startswith(
                self.core.appPlugin.appShortName.lower()
            ):
                stateNameBase = stateNameBase.replace(
                    stateName.split("_", 1)[0] + "_", ""
                )

            if (
                stateNameBase in self.stateTypes
                and stateName not in self.forceStates
            ):
                return

            if psVersion == 1:
                stateUi = stateName + "_ui"
            else:
                stateUi = stateName + "_ui_ps2 as " + stateName + "_ui"

            try:
                del sys.modules[stateName]
            except:
                pass

            try:
                del sys.modules[stateName + "_ui"]
            except:
                pass

            try:
                del sys.modules[stateName + "_ui_ps2"]
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
                try:
                    if not classDef.isActive(self.core):
                        validState = False
                except:
                    pass

                if validState:
                    logger.debug("loaded state %s" % filepath)
                    self.stateTypes[classDef.className] = classDef

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            erStr = "%s ERROR - StateManager %s:\n%s" % (
                time.strftime("%d/%m/%y %X"),
                self.core.version,
                traceback.format_exc(),
            )
            self.core.writeErrorLog(erStr)

    @err_catcher(name=__name__)
    def loadLayout(self):
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

        self.actionCheckVersion = QAction("Check for Prism updates", self)
        self.actionCheckVersion.triggered.connect(self.core.updater.checkForUpdates)
        helpMenu.addAction(self.actionCheckVersion)

        self.actionAbout = QAction("About...", self)
        self.actionAbout.triggered.connect(self.core.showAbout)
        helpMenu.addAction(self.actionAbout)

        self.menubar.addMenu(helpMenu)

        self.actionSendFeedback = QAction("Send feedback...", self)
        self.actionSendFeedback.triggered.connect(self.core.sendFeedback)
        self.menubar.addAction(self.actionSendFeedback)

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

        if self.description == "":
            self.b_description.setStyleSheet(self.styleMissing)
        else:
            self.b_description.setStyleSheet(self.styleExists)
        self.b_preview.setStyleSheet(self.styleMissing)

        if "Render Settings" in self.stateTypes:
            self.actionRenderSettings = QAction("Rendersettings presets...", self)
            self.actionRenderSettings.triggered.connect(self.showRenderPresets)
            self.menuAbout.addSeparator()
            self.menuAbout.addAction(self.actionRenderSettings)

        self.ImportDelegate = ImportDelegate(self)
        self.tw_import.setItemDelegate(self.ImportDelegate)

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

    @err_catcher(name=__name__)
    def selectState(self, state):
        if not state:
            return

        if state.ui.listType == "Import":
            listwidget = self.tw_import
        else:
            listwidget = self.tw_export

        self.setListActive(listwidget)
        listwidget.setCurrentItem(state)
        self.showState()

    @err_catcher(name=__name__)
    def showState(self):
        try:
            grid = QGridLayout()
        except:
            return False

        if self.activeList.currentItem() is not None:
            grid.addWidget(self.activeList.currentItem().ui)

        widget = QWidget()
        policy = QSizePolicy()
        policy.setHorizontalPolicy(QSizePolicy.Fixed)
        widget.setSizePolicy(policy)
        widget.setLayout(grid)

        if hasattr(self, "curUi"):
            self.lo_stateUi.removeWidget(self.curUi)
            self.curUi.setVisible(False)

        self.lo_stateUi.addWidget(widget)
        if self.activeList.currentItem() is not None:
            self.activeList.currentItem().ui.updateUi()

        self.curUi = widget

    @err_catcher(name=__name__)
    def stateChanged(self, cur, prev, activeList):
        if self.loading:
            return False

        self.showState()

    @err_catcher(name=__name__)
    def setListActive(self, listWidget):
        if listWidget == self.tw_import:
            inactive = self.tw_export
            inactivef = self.f_export
            activef = self.f_import
        else:
            inactive = self.tw_import
            inactivef = self.f_import
            activef = self.f_export

        inactive.setCurrentIndex(QModelIndex())

        getattr(
            self.core.appPlugin,
            "sm_setActivePalette",
            lambda x1, x2, x3, x4, x5: self.setTreePalette(x2, x3, x4, x5),
        )(self, listWidget, inactive, inactivef, activef)

        self.activeList = listWidget

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

        self.tw_import.customContextMenuRequested.connect(
            lambda x: self.rclTree(x, self.tw_import)
        )
        self.tw_import.currentItemChanged.connect(
            lambda x, y: self.stateChanged(x, y, self.tw_import)
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
        self.tw_export.currentItemChanged.connect(
            lambda x, y: self.stateChanged(x, y, self.tw_export)
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
        self.b_createRender.clicked.connect(
            lambda: self.core.appPlugin.sm_createRenderPressed(self)
        )
        self.b_createPlayblast.clicked.connect(lambda: self.createPressed("Playblast"))
        self.b_shotCam.clicked.connect(self.shotCam)
        self.b_showImportStates.clicked.connect(lambda: self.showStateMenu("Import", useSelection=True))
        self.b_showExportStates.clicked.connect(lambda: self.showStateMenu("Export", useSelection=True))

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

        self.b_getRange.clicked.connect(self.getRange)
        self.b_setRange.clicked.connect(
            lambda: self.core.setFrameRange(
                self.sp_rangeStart.value(), self.sp_rangeEnd.value()
            )
        )
        self.b_setRange.customContextMenuRequested.connect(self.setRangeContextMenu)
        self.sp_rangeStart.editingFinished.connect(self.startChanged)
        self.sp_rangeEnd.editingFinished.connect(self.endChanged)
        self.b_publish.clicked.connect(self.publish)

    @err_catcher(name=__name__)
    def closeEvent(self, event):
        self.core.callback(name="onStateManagerClose", types=["custom"], args=[self])
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
                lambda x=None, typeName=typeName: self.createState(typeName, parentState, setActive=True)
            )

        getattr(self.core.appPlugin, "sm_openStateFromNode", lambda x, y: None)(self, createMenu)
        return createMenu

    @err_catcher(name=__name__)
    def showStateMenu(self, listType=None, useSelection=False):
        globalPos = QCursor.pos()
        parentState = None
        if useSelection:
            listWidget = self.tw_import if listType == "Import" else self.tw_export
            if listWidget == self.activeList:
                parentState = self.activeList.currentItem()
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
        createMenu = self.getStateMenu(parentState=parentState)

        actExecute = QAction("Execute", self)
        actExecute.triggered.connect(lambda: self.publish(executeState=True))

        menuExecuteV = QMenu("Execute as previous version", self)

        actCopy = QAction("Copy", self)
        actCopy.triggered.connect(self.copyState)

        actPaste = QAction("Paste", self)
        actPaste.triggered.connect(self.pasteStates)

        actDel = QAction("Delete", self)
        actDel.triggered.connect(self.deleteState)

        if parentState is None:
            actCopy.setEnabled(False)
            actDel.setEnabled(False)
            actExecute.setEnabled(False)
            menuExecuteV.setEnabled(False)
        elif hasattr(parentState.ui, "l_pathLast"):
            outPath = parentState.ui.getOutputName()
            if outPath is None:
                menuExecuteV.setEnabled(False)
            else:
                outPath = outPath[0]
                existingVersions = []
                versionDir = os.path.dirname(os.path.dirname(outPath))
                if parentState.ui.className != "Playblast":
                    versionDir = os.path.dirname(versionDir)

                if os.path.exists(versionDir):
                    for i in reversed(sorted(os.listdir(versionDir))):
                        if len(i) < 5 or not i.startswith("v"):
                            continue

                        if pVersion == 2:
                            if not unicode(i[1:5]).isnumeric():
                                continue
                        else:
                            if not i[1:5].isnumeric():
                                continue

                        existingVersions.append(i)

                for i in existingVersions:
                    actV = QAction(i, self)
                    actV.triggered.connect(
                        lambda y=None, x=actV: self.publish(
                            executeState=True, useVersion=x.text()
                        )
                    )
                    menuExecuteV.addAction(actV)

            if menuExecuteV.isEmpty():
                menuExecuteV.setEnabled(False)

        if parentState is None or parentState.ui.className == "Folder":
            rcmenu.addMenu(createMenu)

        if self.activeList == self.tw_export:
            rcmenu.addAction(actExecute)
            rcmenu.addMenu(menuExecuteV)
        rcmenu.addAction(actCopy)
        rcmenu.addAction(actPaste)
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
    ):
        logger.debug("create state: %s" % statetype)
        if statetype not in self.stateTypes:
            return False

        item = QTreeWidgetItem([statetype])
        item.ui = self.stateTypes[statetype]()

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

        stateSetup = item.ui.setup(**kwargs)

        if stateSetup is False:
            return

        self.core.scaleUI(item)

        if item.ui.className == "Folder" and stateData is None:
            if self.activeList == self.tw_import:
                listType = "Import"
            else:
                listType = "Export"
        else:
            listType = item.ui.listType

        if listType == "Import":
            pList = self.tw_import
        else:
            pList = self.tw_export

        if stateData is None and pList == self.tw_export:
            item.setCheckState(0, Qt.Checked)
            if psVersion == 2:
                item.setFlags(item.flags() & ~Qt.ItemIsAutoTristate)

        if parent is None:
            pList.addTopLevelItem(item)
        else:
            parent.addChild(item)
            parent.setExpanded(True)

        self.updateStateList()

        if statetype != "Folder":
            item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled)

        self.core.callback(name="onStateCreated", types=["custom"], args=[self, item.ui], **{"stateData": stateData})

        if setActive:
            self.setListActive(pList)
        pList.setCurrentItem(item)
        self.updateForeground()

        if statetype != "Folder" and self.stateTypes[statetype].listType == "Import":
            self.saveImports()

        self.saveStatesToScene()

        return item

    @err_catcher(name=__name__)
    def copyAllStates(self):
        stateData = self.core.appPlugin.sm_readStates(self)

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
    def removeAllStates(self):
        if self.core.uiAvailable:
            msg = "Are you sure you want to delete all states in the current scene?"
            result = self.core.popupQuestion(msg, buttons=["Yes", "Cancel"])

            if result == "Cancel":
                return

        self.core.appPlugin.sm_deleteStates(self)
        self.core.closeSM(restart=True)

    @err_catcher(name=__name__)
    def copyState(self):
        selStateData = []
        selStateData.append([self.activeList.currentItem(), None])
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
    def deleteState(self, state=None):
        if state is None:
            item = self.activeList.currentItem()
        else:
            item = state

        if not item:
            return

        for i in range(item.childCount()):
            self.deleteState(item.child(i))

        getattr(item.ui, "preDelete", lambda item: None)(item=item)

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

        self.core.callback(name="onStateDeleted", types=["custom"], args=[self, item.ui])

        if item.ui.listType == "Import":
            self.saveImports()

        self.activeList.setCurrentItem(None)
        self.saveStatesToScene()

    @err_catcher(name=__name__)
    def createPressed(self, stateType, renderer=None):
        curSel = self.activeList.currentItem()
        if stateType == "Import":
            if (
                self.activeList == self.tw_import
                and curSel is not None
                and curSel.ui.className == "Folder"
            ):
                parent = curSel
            else:
                parent = None

            import TaskSelection
            ts = TaskSelection.TaskSelection(core=self.core)
            self.core.parentWindow(ts)
            ts.exec_()

            productPath = ts.productPath
            if not productPath:
                return

            extension = os.path.splitext(productPath)[1]
            stateType = getattr(self.core.appPlugin, "sm_getImportHandlerType", lambda x: None)(extension) or "ImportFile"

            self.createState(stateType, parent=parent, importPath=productPath)
            self.setListActive(self.tw_import)
            self.activateWindow()

        elif stateType == "Export":
            if (
                self.activeList == self.tw_export
                and curSel is not None
                and curSel.ui.className == "Folder"
            ):
                parent = curSel
            else:
                parent = None

            self.createState("Export", parent=parent)
            self.setListActive(self.tw_export)

        elif stateType == "Render":
            if (
                self.activeList == self.tw_export
                and curSel is not None
                and curSel.ui.className == "Folder"
            ):
                parent = curSel
            else:
                parent = None

            self.createState("ImageRender", parent=parent, renderer=renderer)
            self.setListActive(self.tw_export)

        elif stateType == "Playblast":
            if (
                self.activeList == self.tw_export
                and curSel is not None
                and curSel.ui.className == "Folder"
            ):
                parent = curSel
            else:
                parent = None

            self.createState("Playblast", parent=parent)
            self.setListActive(self.tw_export)

        elif stateType == "Dependency":
            if (
                self.activeList == self.tw_export
                and curSel is not None
                and curSel.ui.className == "Folder"
            ):
                parent = curSel
            else:
                parent = None

            self.createState("Dependency", parent=parent)
            self.setListActive(self.tw_export)

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
            self.tw_import.setCurrentItem(camState)
        else:
            fileName = self.core.getCurrentFileName()
            fnameData = self.core.getScenefileData(fileName)
            if not (
                os.path.exists(fileName)
                and fnameData["entity"] == "shot"
                and self.core.fileInPipeline(fileName)
            ):
                msgStr = "The current file is not inside the Pipeline.\nUse the Project Browser to create a file in the Pipeline."
                self.core.popup(msgStr)
                self.saveEnabled = True
                return False

            if self.core.useLocalFiles and self.core.localProjectPath in fileName:
                fileName = fileName.replace(
                    self.core.localProjectPath, self.core.projectPath
                )

            camPath = os.path.abspath(
                os.path.join(
                    fileName,
                    os.pardir,
                    os.pardir,
                    os.pardir,
                    os.pardir,
                    "Export",
                    "_ShotCam",
                )
            )

            for i in os.walk(camPath):
                camFolders = i[1]
                break

            if "camFolders" not in locals():
                self.core.popup("Could not find a shotcam for the current shot.")
                self.saveEnabled = True
                return False

            highversion = 0
            for i in camFolders:
                fname = i.split(self.core.filenameSeparator)
                if (
                    len(fname) == 3
                    and fname[0][0] == "v"
                    and len(fname[0]) == 5
                    and int(fname[0][1:5]) > highversion
                ):
                    highversion = int(fname[0][1:5])
                    highFolder = i

            if "highFolder" not in locals():
                self.core.popup("Could not find a shotcam for the current shot.")
                self.saveEnabled = True
                return False

            camPath = os.path.join(
                camPath, highFolder, self.core.appPlugin.preferredUnit
            )

            if not os.path.exists(camPath):
                self.core.popup("Could not find a shotcam in the right units (%s) for the current shot." % self.core.appPlugin.preferredUnit)
                self.saveEnabled = True
                return False

            for camFile in os.listdir(camPath):
                if camFile.endswith(self.shotcamFileType):
                    camPath = os.path.join(camPath, camFile)
                    break

            self.createState("ImportFile", importPath=camPath)

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

        self.core.callback("onStateManagerShow", args=[self])

    @err_catcher(name=__name__)
    def loadStates(self, stateText=None):
        self.saveEnabled = False
        self.loading = True
        if stateText is None:
            stateText = self.core.appPlugin.sm_readStates(self)

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
                if i["statename"] == "publish":
                    self.loadSettings(i)
                else:
                    stateParent = None
                    if i["stateparent"] != "None":
                        stateParent = loadedStates[int(i["stateparent"]) - 1]
                    state = self.createState(
                        i["stateclass"], parent=stateParent, stateData=i
                    )
                    loadedStates.append(state)

        self.loading = False
        self.saveEnabled = True
        self.saveStatesToScene()

    @err_catcher(name=__name__)
    def loadSettings(self, data):
        if "startframe" in data:
            self.sp_rangeStart.setValue(int(data["startframe"]))
        if "endframe" in data:
            self.sp_rangeEnd.setValue(int(data["endframe"]))
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
                "startframe": str(self.sp_rangeStart.value()),
                "endframe": str(self.sp_rangeEnd.value()),
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

        stateData = {"states": []}
        stateData["states"].append(self.getSettings())

        for idx, i in enumerate(self.stateData):
            stateProps = {}
            stateProps["stateparent"] = str(i[1])
            stateProps["stateclass"] = i[0].ui.className
            stateProps.update(i[0].ui.getStateProps())
            stateData["states"].append(stateProps)

        stateStr = self.core.configs.writeJson(stateData)

        self.core.appPlugin.sm_saveStates(self, stateStr)

    @err_catcher(name=__name__)
    def saveImports(self):
        importPaths = str(self.getFilePaths(self.tw_import.invisibleRootItem(), []))
        self.core.appPlugin.sm_saveImports(self, importPaths)

    @err_catcher(name=__name__)
    def getFilePaths(self, item, paths=[]):
        if hasattr(item, "ui") and item.ui.className != "Folder" and item.ui.listType == "Import":
            paths.append([item.ui.e_file.text(), item.text(0)])
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
        minLength = 2
        self.validateComment()
        text = self.e_comment.text()
        if len(text) > minLength:
            self.b_publish.setEnabled(True)
            self.b_publish.setText("Publish")
        else:
            self.b_publish.setEnabled(False)
            self.b_publish.setText(
                "Publish - (%s more chars needed in comment)"
                % (1 + minLength - len(text))
            )

    @err_catcher(name=__name__)
    def setRangeContextMenu(self, pos):
        fname = self.core.getCurrentFileName()
        fnameData = self.core.getScenefileData(fname)
        if fnameData["entity"] != "shot":
            return

        cMenu = QMenu(self)
        actSet = QAction("Set range for current shot", self)
        start = self.sp_rangeStart.value()
        end = self.sp_rangeEnd.value()
        actSet.triggered.connect(
            lambda x=None: self.core.entities.setShotRange(fnameData["entityName"], start, end)
        )
        cMenu.addAction(actSet)

        cMenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def showDescription(self):
        descriptionDlg = EnterText.EnterText()
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

        self.previewImg = ScreenShot.grabScreenArea(self.core)
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
            if detailType is "p":
                l_prv = QLabel()
                l_prv.setPixmap(detail)
                l_prv.setStyleSheet("border: 1px solid rgb(100,100,100);")
                VBox.addWidget(l_prv)
                VBox.setContentsMargins(0, 0, 0, 0)
            elif detailType is "d":
                descr = QLabel(self.description)
                VBox.addWidget(descr)
            self.detailWin.setLayout(VBox)
            self.detailWin.setWindowFlags(
                Qt.FramelessWindowHint  # hides the window controls
                | Qt.WindowStaysOnTopHint  # forces window to top... maybe
                | Qt.SplashScreen  # this one hides it from the task bar!
            )

            self.detailWin.setGeometry(0, 0, winwidth, winheight)
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
    def startChanged(self):
        if self.sp_rangeStart.value() > self.sp_rangeEnd.value():
            self.sp_rangeEnd.setValue(self.sp_rangeStart.value())

        self.saveStatesToScene()

    @err_catcher(name=__name__)
    def endChanged(self):
        if self.sp_rangeEnd.value() < self.sp_rangeStart.value():
            self.sp_rangeStart.setValue(self.sp_rangeEnd.value())

        self.saveStatesToScene()

    @err_catcher(name=__name__)
    def getRange(self):
        fileName = self.core.getCurrentFileName()
        fileNameData = self.core.getScenefileData(fileName)
        if fileNameData["entity"] == "shot":
            shotRange = self.core.entities.getShotRange(fileNameData["entityName"])
            if not shotRange:
                return False

            self.sp_rangeStart.setValue(shotRange[0])
            self.sp_rangeEnd.setValue(shotRange[1])
            self.saveStatesToScene()

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
        self, executeState=False, continuePublish=False, useVersion="next", states=None
    ):
        if self.publishPaused and not continuePublish:
            return

        if continuePublish:
            executeState = self.publishType == "execute"

        if executeState:
            self.publishType = "execute"
            self.execStates = states or self.getChildStates(
                self.tw_export.currentItem()
            )
            actionString = "Execute"
            actionString2 = "execution"
        else:
            self.publishType = "publish"
            self.execStates = states or self.states
            actionString = "Publish"
            actionString2 = "publish"

        if not [x for x in self.execStates if x.checkState(0) == Qt.Checked]:
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
            if useVersion != "next":
                msg = QMessageBox(
                    QMessageBox.Information,
                    actionString,
                    'Are you sure you want to execute this state as version "%s"?\nThis may overwrite existing files.'
                    % useVersion,
                    QMessageBox.Cancel,
                )
                msg.addButton("Continue", QMessageBox.YesRole)
                self.core.parentWindow(msg)
                action = msg.exec_()

                if action != 0:
                    return

            result = []
            extResult = self.core.appPlugin.sm_getExternalFiles(self)
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
                        self.core.useLocalFiles
                        and i.startswith(self.core.localProjectPath)
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
                warnings.append(self.execStates[0].ui.preExecuteState())
            else:
                for i in range(self.tw_export.topLevelItemCount()):
                    curState = self.tw_export.topLevelItem(i)
                    if curState.checkState(0) == Qt.Checked and curState in set(
                        self.execStates
                    ):
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
                                    '- <font color="red">%s</font>\n  %s\n'
                                    % (k[0], k[1])
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

            details = {}
            if self.description != "":
                details = {
                    "description": self.description,
                    "username": self.core.getConfig("globals", "username"),
                }

            if executeState:
                if not self.core.fileInPipeline():
                    msg = "The current scenefile is not inside the pipeline.\nUse the Project Browser to create a file in the pipeline."
                    self.core.popup(msg)
                    return False

                sceneSaved = self.core.saveScene(
                    versionUp=False, details=details, preview=self.previewImg
                )
            else:
                sceneSaved = self.core.saveScene(
                    comment=self.e_comment.text(),
                    publish=True,
                    details=details,
                    preview=self.previewImg,
                )

            if not sceneSaved:
                logger.debug(actionString + " canceled")
                return

            self.description = ""
            self.previewImg = None
            self.b_description.setStyleSheet(self.styleMissing)
            self.b_preview.setStyleSheet(self.styleMissing)
            self.saveStatesToScene()

            self.publishResult = []
            self.osSubmittedJobs = {}
            self.osDependencies = []
            self.dependencies = []
            self.reloadScenefile = False
            self.publishInfos = {"updatedExports": {}, "backgroundRender": None}
            self.core.sceneOpenChecksEnabled = False

            getattr(self.core.appPlugin, "sm_preExecute", lambda x: None)(self)
            self.core.callback(name="onPublish", types=["custom"], args=[self])

        if executeState:
            text = "Executing \"%s\" - please wait.." % self.execStates[0].ui.state.text(0)
            self.pubMsg = self.core.waitPopup(self.core, text)
            with self.pubMsg:
                if self.execStates[0].ui.className in [
                    "ImageRender",
                    "Export",
                    "Playblast",
                    "Folder",
                ]:
                    result = self.execStates[0].ui.executeState(
                        parent=self, useVersion=useVersion
                    )
                else:
                    result = self.execStates[0].ui.executeState(parent=self)

                if self.execStates[0].ui.className == "Folder":
                    self.publishResult += result

                    for k in result:
                        if "publish paused" in k["result"][0]:
                            self.publishPaused = True
                            return
                else:
                    self.publishResult.append(
                        {"state": self.execStates[0].ui, "result": result}
                    )

                    if "publish paused" in result[0]:
                        self.publishPaused = True
                        return

        else:
            for i in range(self.tw_export.topLevelItemCount()):
                curUi = self.tw_export.topLevelItem(i).ui
                if self.tw_export.topLevelItem(i).checkState(
                    0
                ) == Qt.Checked and curUi.state in set(self.execStates):
                    text = "Executing \"%s\" - please wait.." % curUi.state.text(0)
                    self.pubMsg = self.core.waitPopup(self.core, text)
                    with self.pubMsg:
                        exResult = curUi.executeState(parent=self)
                        if curUi.className == "Folder":
                            self.publishResult += exResult

                            for k in exResult:
                                if "publish paused" in k["result"][0]:
                                    self.publishPaused = True
                                    return
                        else:
                            self.publishResult.append({"state": curUi, "result": exResult})

                            if exResult and "publish paused" in exResult[0]:
                                self.publishPaused = True
                                return

        getattr(self.core.appPlugin, "sm_postExecute", lambda x: None)(self)
        pubType = "stateExecution" if executeState else "publish"
        self.core.callback(name="postPublish", types=["custom"], args=[self, pubType], **{"result": self.publishResult})

        self.publishInfos = {"updatedExports": {}, "backgroundRender": None}
        self.osSubmittedJobs = {}
        self.osDependencies = []
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

        if success:
            msgStr = "The %s was successful." % actionString2
            self.core.popup(msgStr, title=actionString, severity="info")
        else:
            infoString = ""
            for i in self.publishResult:
                if not i["result"]:
                    infoString += "unknown error\n"
                elif not "publish paused" in i["result"][0]:
                    infoString += i["result"][0] + "\n"

            msgStr = "Errors occured during the %s:\n\n" % actionString2 + infoString

            self.core.popup(msgStr, title=actionString)

        if self.reloadScenefile:
            self.core.appPlugin.openScene(
                self, self.core.getCurrentFileName(), force=True
            )

    @err_catcher(name=__name__)
    def getFrameRangeTypeToolTip(self, rangeType):
        tt = ""
        if rangeType == "State Manager":
            tt = "The framerange of the State Manager settings is used, which is located in the lower left corner of the State Manager window."
        elif rangeType == "Scene":
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
            tt = """* Single frames are defined by a single the framenumber.
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
    def validateComment(self):
        self.core.validateLineEdit(self.e_comment)

    @err_catcher(name=__name__)
    def getStateProps(self):
        return {
            "startframe": self.sp_rangeStart.value(),
            "endframe": self.sp_rangeEnd.value(),
            "comment": self.e_comment.text(),
            "description": self.description,
        }


class ImportDelegate(QStyledItemDelegate):
    def __init__(self, stateManager):
        super(ImportDelegate, self).__init__()
        self.stateManager = stateManager

    def paint(self, painterQPainter, optionQStyleOptionViewItem, indexQModelIndex):
        QStyledItemDelegate.paint(self, painterQPainter, optionQStyleOptionViewItem, indexQModelIndex)

        item = self.stateManager.tw_import.itemFromIndex(indexQModelIndex)
        color = getattr(item.ui, "statusColor", None)
        if not color:
            return

        rect = QRect(optionQStyleOptionViewItem.rect)
        curRight = optionQStyleOptionViewItem.rect.right()
        rect.setLeft(curRight-10)

        painterQPainter.fillRect(rect, QBrush(item.ui.statusColor))


def openStateSettings(core, stateType, settings=None):
    settings = settings or None
    stateNameBase = stateType.replace(stateType.split("_", 1)[0] + "_", "")
    sm = StateManager(core, forceStates=[stateType], standalone=True)
    item = sm.createState(stateNameBase, stateData=settings)

    dlg_settings = QDialog()
    dlg_settings.setWindowTitle("Statesettings - %s" % stateNameBase)
    w_settings = QWidget()
    bb_settings = QDialogButtonBox()
    bb_settings.addButton("Accept", QDialogButtonBox.AcceptRole)
    bb_settings.addButton("Cancel", QDialogButtonBox.RejectRole)
    bb_settings.accepted.connect(dlg_settings.accept)
    bb_settings.rejected.connect(dlg_settings.reject)

    lo_settings = QVBoxLayout()
    lo_settings.addWidget(item.ui)
    lo_settings.addWidget(bb_settings)
    dlg_settings.setLayout(lo_settings)
    dlg_settings.setParent(core.messageParent, Qt.Window)

    action = dlg_settings.exec_()

    if action == 0:
        return

    return item.ui.getStateProps()
