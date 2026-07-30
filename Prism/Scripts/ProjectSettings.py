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
import logging
import subprocess
from collections import OrderedDict
from typing import Any, Optional, List, Dict, Tuple

scriptPath = os.path.abspath(os.path.dirname(__file__))
if scriptPath not in sys.path:
    sys.path.append(scriptPath)

if __name__ == "__main__":
    import PrismCore

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils import PrismWidgets, ProjectWidgets
from PrismUtils.Decorators import err_catcher
from UserInterfacesPrism import ProjectSettings_ui


logger = logging.getLogger(__name__)


class ProjectSettings(QDialog, ProjectSettings_ui.Ui_dlg_ProjectSettings):

    signalSaved = Signal(object)

    def __init__(self, core: Any, projectConfig: Optional[str] = None, projectData: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Project Settings dialog.
        
        Args:
            core: The Prism core instance
            projectConfig: Path to the project configuration file
            projectData: Optional pre-loaded project data dictionary
        """
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.core.parentWindow(self)
        self.projectConfig = projectConfig
        self.projectData = projectData
        self.previewMap = None

        self.dependencyStates = {
            "always": "Always",
            "publish": "On Publish",
            "never": "Never",
        }

        self.loadUI()
        self.loadSettings()

        self.core.callback(name="onProjectSettingsOpen", args=[self])

        self.connectEvents()
        self.setFocus()

        screen = self.core.getQScreenGeo()
        if screen:
            screenH = screen.height()
            space = 100
            if screenH < (self.height() + space):
                self.resize(self.width(), screenH - space)

    @err_catcher(name=__name__)
    def loadUI(self) -> None:
        """Load and initialize the project settings dialog UI.
        
        Creates all UI elements including tabs, tables, buttons, and layout configurations
        for managing project settings such as folder structure, export/render paths,
        departments, task presets, hooks, and scene building configuration.
        """
        tabBar = self.tw_settings.findChild(QTabBar)
        tabBar.hide()
        self.tw_settings.currentChanged.connect(self.tabChanged)
        for idx in range(self.tw_settings.count()):
            self.tw_settings.widget(idx).layout().setContentsMargins(0, 0, 0, 0)

        imgFile = os.path.join(
            self.core.prismRoot,
            "Presets/Projects/Default/00_Pipeline/Fallbacks/noFileBig.jpg",
        )
        pmap = self.core.media.getPixmapFromPath(imgFile)
        if pmap:
            self.l_preview.setMinimumSize(pmap.width(), pmap.height())
            self.l_preview.setPixmap(pmap)

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "help.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        pixmap = icon.pixmap(20, 20)
        self.l_helpExportLocations = HelpLabel(self)
        self.l_helpExportLocations.setPixmap(pixmap)
        self.l_helpExportLocations.setMouseTracking(True)
        msg = (
            "Export locations are project paths outside of the main project folder.\n"
            "They can be used to export files to different folders and harddrives.\n"
            "In the export settings artists can choose to which location they want to export their objects.\n"
            'The filepath of an exported file consists of the locationpath plus the relative projectpath, which is defined in the "Folder Structure" tab of the project settings.'
        )
        self.l_helpExportLocations.msg = msg
        self.lo_exportLocationsHeader.addWidget(self.l_helpExportLocations)
        self.l_helpRenderLocations = HelpLabel(self)
        self.l_helpRenderLocations.setPixmap(pixmap)
        self.l_helpRenderLocations.setMouseTracking(True)
        msg = (
            "Render locations are project paths outside of the main project folder.\n"
            "They can be used to render files to different folders and harddrives.\n"
            "In the render settings artists can choose to which location they want to render their images.\n"
            'The filepath of a rendered file consists of the locationpath plus the relative projectpath, which is defined in the "Folder Structure" tab of the project settings.'
        )
        self.l_helpRenderLocations.msg = msg
        self.lo_renderLocationsHeader.addWidget(self.l_helpRenderLocations)
        self.refreshFolderStructure()

        self.origKeyPressEvent = self.keyPressEvent
        self.keyPressEvent = lambda x: self.keyPressedDialog(x)

        self.tw_exportPaths.customContextMenuRequested.connect(self.rclExportPaths)
        self.tw_renderPaths.customContextMenuRequested.connect(self.rclRenderPaths)

        self.tw_environment.setHorizontalHeaderLabels(["Variable", "Value"])
        self.tw_environment.customContextMenuRequested.connect(self.rclEnvironment)
        self.addEnvironmentRow()
        self.tw_environment.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )

        if self.core.prism1Compatibility:
            self.tw_settings.removeTab(self.tw_settings.indexOf(self.tab_folderStructure))

        self.refreshHooks(reloadHooks=False)
        self.b_addHook.setToolTip("Add Hook")
        self.b_removeHook.setToolTip("Delete selected Hooks")
        self.b_assetDepAdd = QToolButton()
        self.b_assetDepAdd.setToolTip("Add asset department...")
        self.b_assetDepAdd.setFocusPolicy(Qt.NoFocus)
        self.w_assetDepartmentHeader.layout().addWidget(self.b_assetDepAdd)
        self.b_assetDepRemove = QToolButton()
        self.b_assetDepRemove.setToolTip("Remove selected asset departments")
        self.b_assetDepRemove.setFocusPolicy(Qt.NoFocus)
        self.w_assetDepartmentHeader.layout().addWidget(self.b_assetDepRemove)
        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_assetDepAdd.setIcon(icon)
        self.b_addTaskPresetsAsset.setIcon(icon)
        self.b_addTaskPresetsShot.setIcon(icon)
        self.b_addHook.setIcon(icon)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "remove.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_assetDepRemove.setIcon(icon)
        self.b_removeTaskPresetsAsset.setIcon(icon)
        self.b_removeTaskPresetsShot.setIcon(icon)
        self.b_removeHook.setIcon(icon)

        self.b_assetDepAdd.clicked.connect(self.addAssetDepartmentClicked)
        self.b_assetDepRemove.clicked.connect(self.removeAssetDepartmentClicked)
        self.b_addTaskPresetsAsset.clicked.connect(self.addTaskPresetsAssetClicked)
        self.b_removeTaskPresetsAsset.clicked.connect(self.removeTaskPresetsAssetClicked)
        self.b_addTaskPresetsShot.clicked.connect(self.addTaskPresetsShotClicked)
        self.b_removeTaskPresetsShot.clicked.connect(self.removeTaskPresetsShotClicked)
        self.b_addHook.clicked.connect(self.addHookClicked)
        self.b_removeHook.clicked.connect(self.removeHookClicked)
        self.lw_hooks.customContextMenuRequested.connect(self.hooksRightClicked)
        self.lw_hooks.itemSelectionChanged.connect(self.hookSelectionChanged)
        self.b_saveHook.clicked.connect(self.saveHook)
        self.core.pythonHighlighter(self.te_hook.document())

        self.tw_assetDepartments.verticalHeader().setSectionsMovable(True)
        self.tw_assetDepartments.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.tw_assetDepartments.customContextMenuRequested.connect(self.assetDepsRightClicked)
        self.tw_assetDepartments.verticalHeader().sectionMoved.connect(self.assetDepartmentRowMoved)
        self.tw_assetDepartments.itemDoubleClicked.connect(self.assetDepartmentDoubleClicked)
        self.tw_assetDepartments.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)

        self.b_shotDepAdd = QToolButton()
        self.b_shotDepAdd.setToolTip("Add shot department...")
        self.b_shotDepAdd.setFocusPolicy(Qt.NoFocus)
        self.w_shotDepartmentHeader.layout().addWidget(self.b_shotDepAdd)
        self.b_shotDepRemove = QToolButton()
        self.b_shotDepRemove.setToolTip("Remove selected shot departments")
        self.b_shotDepRemove.setFocusPolicy(Qt.NoFocus)
        self.w_shotDepartmentHeader.layout().addWidget(self.b_shotDepRemove)
        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_shotDepAdd.setIcon(icon)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "remove.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_shotDepRemove.setIcon(icon)
        self.b_shotDepAdd.clicked.connect(self.addShotDepartmentClicked)
        self.b_shotDepRemove.clicked.connect(self.removeShotDepartmentClicked)
        self.tw_shotDepartments.verticalHeader().setSectionsMovable(True)
        self.tw_shotDepartments.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.tw_shotDepartments.customContextMenuRequested.connect(self.shotDepsRightClicked)
        self.tw_shotDepartments.verticalHeader().sectionMoved.connect(self.shotDepartmentRowMoved)
        self.tw_shotDepartments.itemDoubleClicked.connect(self.shotDepartmentDoubleClicked)
        self.tw_shotDepartments.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)

        self.lw_taskPresetsAsset.customContextMenuRequested.connect(self.assetTaskPresetsRightClicked)
        self.lw_taskPresetsAsset.itemDoubleClicked.connect(self.assetTaskPresetsDoubleClicked)
        self.lw_taskPresetsShot.customContextMenuRequested.connect(self.shotTaskPresetsRightClicked)
        self.lw_taskPresetsShot.itemDoubleClicked.connect(self.shotTaskPresetDoubleClicked)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "import.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_importSettings.setIcon(icon)
        self.b_importSettings.setIconSize(QSize(22, 22))

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "export.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_exportSettings.setIcon(icon)
        self.b_exportSettings.setIconSize(QSize(22, 22))

        self.refreshCategories()
        policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        policy.setHorizontalStretch(58)
        self.lw_categories.setSizePolicy(policy)
        policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        policy.setHorizontalStretch(100)
        self.tw_settings.setSizePolicy(policy)
        self.lw_categories.currentItemChanged.connect(self.onCategoryChanged)
        self.selectCategory("General")

        self.w_sceneBuilding = QWidget()
        self.lo_sceneBuilding = QVBoxLayout(self.w_sceneBuilding)
        self.lo_sceneBuilding.setContentsMargins(0, 0, 0, 0)

        self.l_sceneBuildingDesc = QLabel(
            "Configure which steps are executed automatically when building a scene for each DCC application."
        )
        self.l_sceneBuildingDesc.setWordWrap(True)
        self.l_sceneBuildingDesc.setContentsMargins(4, 4, 4, 2)
        self.lo_sceneBuilding.addWidget(self.l_sceneBuildingDesc)

        self.lo_sceneBuilding.addStretch()

        self.sa_sceneBuilding = QScrollArea()
        self.sa_sceneBuilding.setWidget(self.w_sceneBuilding)
        self.sa_sceneBuilding.setWidgetResizable(True)
        self.sa_sceneBuilding.setFrameShape(QFrame.NoFrame)
        self.addTab(self.sa_sceneBuilding, "Scene Building")

        self.w_states = QWidget()
        self.lo_states = QVBoxLayout(self.w_states)

        self.gb_stateDefaults = ProjectWidgets.StateDefaults(self)
        self.lo_states.addWidget(self.gb_stateDefaults)

        self.gb_statePresets = ProjectWidgets.StatePresets(self)
        self.lo_states.addWidget(self.gb_statePresets)

        self.lo_states.addStretch()
        self.addTab(self.w_states, "States")

        self.w_presetScenes = QWidget()
        lo_presetScenes = QVBoxLayout()
        self.w_presetScenes.setLayout(lo_presetScenes)

        self.gb_presetScenes = ProjectWidgets.DefaultPresetScenes(self)
        lo_presetScenes.addWidget(self.gb_presetScenes)

        lo_presetScenes.addStretch()
        self.addTab(self.w_presetScenes, "Preset Scenes")

        self.cb_expectedPrismVersion.addItems(["Warn", "Enforce"])

        self.core.callback(name="projectSettings_loadUI", args=[self])

    @err_catcher(name=__name__)
    def showProductTags(self) -> None:
        """Open the product tags management dialog.
        
        Shows or brings to front the product tags dialog for managingproject-specific tags.
        """
        if hasattr(self, "dlg_productTags") and self.dlg_productTags.isVisible():
            self.dlg_productTags.close()

        self.dlg_productTags = ProjectWidgets.ProductTagsDlg(self.core, parent=self)
        self.dlg_productTags.show()

    @err_catcher(name=__name__)
    def addSceneBuildingApp(self, appName: str, iconPath: Optional[str] = None) -> "SceneBuildingAppWidget":
        """Add a scene building configuration widget for an application.

        Creates a collapsible group box for the given app containing a step list
        (QTreeWidget) and a tool button that lets users pick from availableSteps
        to add to the list.

        Args:
            appName: Display name of the DCC application (used as group title).
            iconPath: Optional path to an icon shown beside the group title.
                Defaults to the configure.png placeholder.

        Returns:
            The newly created SceneBuildingAppWidget.
        """
        widget = SceneBuildingAppWidget(self.core, appName, iconPath=iconPath, parent=self.w_sceneBuilding)

        # Skip any leading non-app widgets (e.g. description label) to find the base index
        insertIdx = 0
        for i in range(self.lo_sceneBuilding.count() - 1):  # skip trailing stretch
            existing = self.lo_sceneBuilding.itemAt(i).widget()
            if not isinstance(existing, SceneBuildingAppWidget):
                insertIdx = i + 1
            else:
                break

        # Insert in alphabetical order among the app widgets
        for i in range(insertIdx, self.lo_sceneBuilding.count() - 1):
            existing = self.lo_sceneBuilding.itemAt(i).widget()
            if isinstance(existing, SceneBuildingAppWidget) and existing.appName.lower() <= appName.lower():
                insertIdx = i + 1

        self.lo_sceneBuilding.insertWidget(insertIdx, widget)
        return widget

    @err_catcher(name=__name__)
    def refreshFolderStructure(self) -> None:
        """Refresh and rebuild the folder structure UI elements.
        
        Recreates all folder structure line edits and their associated help labels
        with validation and context menu capabilities.
        """
        for idx in reversed(range(self.lo_structure.count())):
            item = self.lo_structure.takeAt(idx)
            w = item.widget()
            if w:
                w.setVisible(False)
                w.setParent(None)
                w.deleteLater()

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "reset.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.b_resetStructure.setIcon(icon)
        self.b_resetStructure.setToolTip("Reset all fields to their default")

        if self.projectData:
            items = self.projectData.get("folder_structure", "")
            if items:
                items = self.core.projects.getProjectStructure(projectStructure=items)
            else:
                items = self.core.projects.getDefaultProjectStructure()
        else:
            items = self.core.projects.getProjectStructure()

        self.folderStructureWidgets = []
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "help.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.helpPixmap = icon.pixmap(20, 20)
        self.invalidHelpPixmap = self.core.media.getColoredIcon(
            iconPath, r=200, g=10, b=10
        ).pixmap(20, 20)
        for idx, key in enumerate(items):
            l_item = QLabel(items[key]["label"] + ":  ")
            l_item.setToolTip(items[key]["key"])
            e_item = QLineEdit(items[key]["value"])
            l_help = HelpLabel(self)
            e_item.textChanged.connect(lambda x, w=e_item: self.validateFolderWidget(w))
            e_item.helpWidget = l_help
            e_item.setContextMenuPolicy(Qt.CustomContextMenu)
            e_item.customContextMenuRequested.connect(
                lambda x, w=e_item: self.rclStructureKey(w)
            )
            l_help.editWidget = e_item
            l_help.key = key
            l_help.item = items[key]
            l_help.msg = ""
            l_help.setPixmap(self.helpPixmap)
            l_help.setMouseTracking(True)
            l_help.signalEntered.connect(self.structureItemEntered)
            self.validateFolderWidget(e_item)

            self.lo_structure.addWidget(l_item, idx, 0)
            self.lo_structure.addWidget(e_item, idx, 1)
            self.lo_structure.addWidget(l_help, idx, 2)

            data = {"key": key, "item": items[key], "widget": e_item}
            self.folderStructureWidgets.append(data)

        sp_structure = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.lo_structure.addItem(sp_structure, idx + 1, 1)

    @err_catcher(name=__name__)
    def addTab(self, widget: QWidget, name: str) -> None:
        """Add a new tab to the project settings tabs widget.
        
        Args:
            widget: The widget to display in the tab
            name: The name/label for the tab
        """
        self.tw_settings.addTab(widget, name)
        self.refreshCategories()

    @err_catcher(name=__name__)
    def tabChanged(self, tab: int) -> None:
        """Handle tab change event. 
        
        Syncs category list selection when active tab changes.
        
        Args:
            tab: Index of the newly selected tab
        """
        self.lw_categories.blockSignals(True)
        self.selectCategory(self.tw_settings.tabText(tab))
        self.lw_categories.blockSignals(False)

    @err_catcher(name=__name__)
    def refreshCategories(self) -> None:
        """Refresh the category list with sorted tab names.
        
        Rebuilds the categories list widget from current tabs, maintaining current selection.
        """
        self.lw_categories.blockSignals(True)
        curCat = self.getCurrentCategory()
        self.lw_categories.clear()
        cats = []
        for idx in range(self.tw_settings.count()):
            text = self.tw_settings.tabText(idx)
            cats.append(text)
        
        self.lw_categories.addItems(sorted(cats))
        if curCat:
            self.selectCategory(curCat)
        else:
            self.lw_categories.setCurrentRow(0)

        self.lw_categories.blockSignals(False)
        self.onCategoryChanged(self.lw_categories.currentItem())

    @err_catcher(name=__name__)
    def onCategoryChanged(self, current: Optional[QListWidgetItem], prev: Optional[QListWidgetItem] = None) -> None:
        """Handle category selection change in the category list.
        
        Updates the active tab to match the selected category.
        
        Args:
            current: The newly selected category item
            prev: The previously selected category item (optional)
        """
        text = current.text()
        for idx in range(self.tw_settings.count()):
            tabtext = self.tw_settings.tabText(idx)
            if text == tabtext:
                self.tw_settings.setCurrentIndex(idx)
                break

    @err_catcher(name=__name__)
    def selectCategory(self, name: str) -> None:
        """Select a category by name in the category list.
        
        Args:
            name: The name of the category to select
        """
        for idx in range(self.lw_categories.count()):
            cat = self.lw_categories.item(idx).text()
            if cat == name:
                self.lw_categories.setCurrentRow(idx)
                break

    @err_catcher(name=__name__)
    def getCurrentCategory(self) -> Optional[str]:
        """Get the name of the currently selected category.
        
        Returns:
            The text of the currently selected category item, or None if no item is selected
        """
        item = self.lw_categories.currentItem()
        if not item:
            return

        return item.text()

    @err_catcher(name=__name__)
    def keyPressedDialog(self, event: Any) -> None:
        """Handle key press events in the dialog.
        
        Intercepts Return key to prevent default behavior; passes other keys to original handler.
        
        Args:
            event: Qt key event
        """
        if event.key() == Qt.Key_Return:
            self.setFocus()
        else:
            self.origKeyPressEvent(event)

        event.accept()

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect all UI widget signals to their corresponding slot methods.
        
        Connects buttons, checkboxes, and other controls to preview, path, structure,
        environment, and settings management handlers.
        """
        self.l_preview.mouseDoubleClickEvent = lambda x: self.browsePreview()
        self.l_preview.customContextMenuRequested.connect(self.rclPreview)
        self.e_curPname.textEdited.connect(self.curPnameEdited)
        self.chb_curPuseFps.toggled.connect(self.pfpsToggled)
        self.chb_prjResolution.toggled.connect(self.prjResolutionToggled)
        self.chb_curPRequirePublishComment.toggled.connect(self.requirePublishCommentToggled)
        self.chb_curPepisodes.toggled.connect(self.episodesToggled)
        self.chb_curPproductTasks.toggled.connect(self.productTasksToggled)
        self.b_addExportPath.clicked.connect(self.addExportPathClicked)
        self.b_removeExportPath.clicked.connect(self.removeExportPathClicked)
        self.b_addRenderPath.clicked.connect(self.addRenderPathClicked)
        self.b_removeRenderPath.clicked.connect(self.removeRenderPathClicked)
        self.b_resetStructure.clicked.connect(self.resetProjectStructure)
        self.b_showEnvironment.clicked.connect(self.showEnvironment)
        self.b_importSettings.clicked.connect(self.onImportSettingsClicked)
        self.b_exportSettings.clicked.connect(self.onExportSettingsClicked)
        self.b_reqPlugins.clicked.connect(self.onRequiredPluginsClicked)
        self.b_disabledPlugins.clicked.connect(self.onDisabledPluginsClicked)
        self.b_expectedPrjPath.clicked.connect(self.onBrowseExpPathClicked)
        self.b_manageProductTags.clicked.connect(self.showProductTags)
        self.buttonBox.accepted.connect(self.saveSettings)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(
            lambda: self.saveSettings(changeProject=False)
        )

    @err_catcher(name=__name__)
    def rclPreview(self, pos: QPoint) -> None:
        """Display context menu for preview image label.
        
        Provides actions to browse for image, capture screenshot, or paste from clipboard.
        
        Args:
            pos: Position where context menu was requested
        """
        rcmenu = QMenu(self)

        exp = QAction("Browse...", self)
        exp.triggered.connect(self.browsePreview)
        rcmenu.addAction(exp)

        copAct = QAction("Capture image", self)
        copAct.triggered.connect(self.capturePreview)
        rcmenu.addAction(copAct)
        clipAct = QAction("Paste image from clipboard", self)
        clipAct.triggered.connect(self.pastePreviewFromClipboard)
        rcmenu.addAction(clipAct)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def rclStructureKey(self, widget: QLineEdit) -> None:
        """Display context menu for folder structure path editor.
        
        Provides actions to restore saved value, restore factory default, or edit expression.
        
        Args:
            widget: The line edit widget for folder structure path
        """
        rcmenu = QMenu(self)

        exp = QAction("Restore saved value", self)
        exp.triggered.connect(lambda: self.restoreStructurePath(widget))
        rcmenu.addAction(exp)

        exp = QAction("Restore factory default", self)
        exp.triggered.connect(lambda: self.restoreStructurePath(widget, default=True))
        rcmenu.addAction(exp)

        exp = QAction("Edit Expression...", self)
        exp.triggered.connect(lambda: self.editExpression(widget))
        rcmenu.addAction(exp)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def editExpression(self, widget: QLineEdit) -> None:
        """Open expression editor dialog for folder structure path.
        
        Allows editing dynamic path expressions for folder structure templates.
        
        Args:
            widget: The line edit widget containing the expression or template path
        """
        self.dlg_expression = ExpressionWindow(self)
        text = widget.text()
        if text.startswith("[expression,"):
            text = text[len("[expression,"):]
            if text.endswith("]"):
                text = text[:-1]
        else:
            text = "#  available variables:\n#  \"core\" - PrismCore\n#  \"context\" - dict\n\ntemplate = \"%s\"" % text

        self.dlg_expression.te_expression.setPlainText(text)
        newCursor = QTextCursor(self.dlg_expression.te_expression.document())
        newCursor.movePosition(QTextCursor.End)
        self.dlg_expression.te_expression.setTextCursor(newCursor)
        result = self.dlg_expression.exec_()

        if result == 1:
            text = self.dlg_expression.te_expression.toPlainText()
            text = "[expression,%s]" % text
            widget.setText(text)

    @err_catcher(name=__name__)
    def rclExportPaths(self, pos: QPoint) -> None:
        """Display context menu for export paths table.
        
        Provides actions to add, browse, or remove export location paths.
        
        Args:
            pos: Position where context menu was requested
        """
        rcmenu = QMenu(self)

        exp = QAction("Add location", self)
        exp.triggered.connect(self.addExportLocation)
        rcmenu.addAction(exp)

        item = self.tw_exportPaths.itemFromIndex(self.tw_exportPaths.indexAt(pos))
        if item:
            if item.column() == 1:
                exp = QAction("Browse...", self)
                exp.triggered.connect(lambda: self.browse(item, "export"))
                rcmenu.addAction(exp)

            exp = QAction("Remove", self)
            exp.triggered.connect(lambda: self.removeExportLocation(item.row()))
            rcmenu.addAction(exp)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def browse(self, item: QTableWidgetItem, location: str) -> None:
        """Browse for and set a path in a table item.
        
        Opens a folder selection dialog and sets the selected path in the given item.
        
        Args:
            item: Table widget item to update with selected path
            location: Type of location ('export' or 'render') for dialog title
        """
        windowTitle = "Select %s location" % location
        selectedPath = QFileDialog.getExistingDirectory(
            self, windowTitle, item.text()
        )

        if selectedPath:
            item.setText(self.core.fixPath(selectedPath))

    @err_catcher(name=__name__)
    def addExportLocation(self) -> None:
        """Add a new row to the export locations table.
        
        Inserts a new empty row ready for user to fill in location name and path.
        """
        count = self.tw_exportPaths.rowCount()
        self.tw_exportPaths.insertRow(count)
        item = QTableWidgetItem("< doubleclick to edit >")
        self.tw_exportPaths.setItem(count, 0, item)
        item = QTableWidgetItem("< doubleclick to edit >")
        self.tw_exportPaths.setItem(count, 1, item)
        self.tw_exportPaths.resizeColumnsToContents()

    @err_catcher(name=__name__)
    def removeExportLocation(self, idx: int) -> None:
        """Remove export location row from the table.
        
        Args:
            idx: Row index to remove
        """
        self.tw_exportPaths.removeRow(idx)

    @err_catcher(name=__name__)
    def rclRenderPaths(self, pos: QPoint) -> None:
        """Display context menu for render paths table.
        
        Provides actions to add, browse, or remove render location paths.
        
        Args:
            pos: Position where context menu was requested
        """
        rcmenu = QMenu(self)

        exp = QAction("Add location", self)
        exp.triggered.connect(self.addRenderLocation)
        rcmenu.addAction(exp)

        item = self.tw_renderPaths.itemFromIndex(self.tw_renderPaths.indexAt(pos))
        if item:
            if item.column() == 1:
                exp = QAction("Browse...", self)
                exp.triggered.connect(lambda: self.browse(item, "render"))
                rcmenu.addAction(exp)

            exp = QAction("Remove", self)
            exp.triggered.connect(lambda: self.removeRenderLocation(item.row()))
            rcmenu.addAction(exp)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def addRenderLocation(self) -> None:
        """Add a new row to the render locations table.
        
        Inserts a new empty row ready for user to fill in location name and path.
        """
        count = self.tw_renderPaths.rowCount()
        self.tw_renderPaths.insertRow(count)
        item = QTableWidgetItem("< doubleclick to edit >")
        self.tw_renderPaths.setItem(count, 0, item)
        item = QTableWidgetItem("< doubleclick to edit >")
        self.tw_renderPaths.setItem(count, 1, item)
        self.tw_renderPaths.resizeColumnsToContents()

    @err_catcher(name=__name__)
    def removeRenderLocation(self, idx: int) -> None:
        """Remove render location row from the table.
        
        Args:
            idx: Row index to remove
        """
        self.tw_renderPaths.removeRow(idx)

    @err_catcher(name=__name__)
    def rclEnvironment(self, pos: QPoint) -> None:
        """Display context menu for environment variables table.
        
        Provides actions to add, make persistent, or remove environment variable rows.
        
        Args:
            pos: Position where context menu was requested
        """
        rcmenu = QMenu(self)

        exp = QAction("Add row", self)
        exp.triggered.connect(self.addEnvironmentRow)
        rcmenu.addAction(exp)

        item = self.tw_environment.itemFromIndex(self.tw_environment.indexAt(pos))
        if item:
            exp = QAction("Make Persistent", self)
            exp.triggered.connect(lambda: self.makePersistent(item.row()))
            rcmenu.addAction(exp)

            exp = QAction("Remove", self)
            exp.triggered.connect(lambda: self.removeEnvironmentRow(item.row()))
            rcmenu.addAction(exp)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def addEnvironmentRow(self) -> None:
        """Add a new empty row to the environment variables table.
        
        Inserts a new row at the end of the table with placeholder text for
        key-value pairs to be filled in by the user.
        """
        count = self.tw_environment.rowCount()
        self.tw_environment.insertRow(count)
        item = QTableWidgetItem("< doubleclick to edit >")
        self.tw_environment.setItem(count, 0, item)
        item = QTableWidgetItem("< doubleclick to edit >")
        self.tw_environment.setItem(count, 1, item)
        self.tw_environment.resizeColumnsToContents()

    @err_catcher(name=__name__)
    def removeEnvironmentRow(self, idx: int) -> None:
        """Remove an environment variable row from the table.
        
        Args:
            idx: Row index to remove from the environment table.
        """
        self.tw_environment.removeRow(idx)

    @err_catcher(name=__name__)
    def makePersistent(self, idx: int) -> None:
        """Make an environment variable persistent in Windows registry.
        
        Sets an environment variable persistently using the Windows 'setx' command,
        making it available to future processes. Validates both key and value before
        attempting to set the variable.
        
        Args:
            idx: Row index in the environment table widget.
        
        Raises:
            Popup: Error if key or value is invalid or setx command fails.
        """
        dft = "< doubleclick to edit >"
        key = self.tw_environment.item(idx, 0).text()
        if not key or key == dft:
            self.core.popup("Invalid key.")
            return

        value = self.tw_environment.item(idx, 1).text()
        if value == dft:
            self.core.popup("Invalid value.")
            return

        with self.core.waitPopup(self.core, "Making env var persistent. Please wait..."):
            proc = subprocess.Popen("setx %s %s" % (key, value), stdout=subprocess.PIPE)
            stdout, _ = proc.communicate()
        
        if sys.version[0] == "3":
            stdout = stdout.decode("utf-8", "ignore")

        if "success" in stdout.lower():
            self.core.popup("Successfully set environment variable persistently.", severity="info")
        else:
            self.core.popup("Unknown result. The env var might not be set persistently. Result is:\n\n%s" % stdout)

    @err_catcher(name=__name__)
    def showEnvironment(self) -> None:
        """Display the environment widget dialog.
        
        Creates and shows a popup window with detailed environment information
        for the current project configuration.
        """
        self.w_env = EnvironmentWidget(self)
        self.w_env.show()

    @err_catcher(name=__name__)
    def onImportSettingsClicked(self) -> None:
        """Handle import settings button click.
        
        Opens a file dialog to select a project settings file (JSON or YAML),
        then loads the settings from that file into the dialog. Used to import
        previously exported project settings configurations.
        """
        path = self.core.paths.requestFilepath(
            title="Load project settings",
            startPath=self.core.prismIni,
            parent=self,
            fileFilter="Config files (*.json *.yml)",
            saveDialog=False
        )

        if not path:
            return

        self.loadSettings(configPath=path)

    @err_catcher(name=__name__)
    def onExportSettingsClicked(self) -> None:
        """Handle export settings button click.
        
        Opens a file dialog to select a destination for exporting current project
        settings. Saves all project configuration to a JSON or YAML file that can
        be later imported into another project.
        """
        path = self.core.paths.requestFilepath(
            title="Save project settings",
            startPath=self.core.prismIni,
            parent=self,
            fileFilter="Config files (*.json *.yml)",
            saveDialog=True
        )

        if not path:
            return

        self.saveSettings(configPath=path, export=True)

    @err_catcher(name=__name__)
    def onRequiredPluginsClicked(self) -> None:
        """Display context menu to toggle required plugins.
        
        Shows all available plugins in a context menu, allowing users to toggle
        each plugin's required status by toggling it on/off in the list.
        """
        pos = QCursor.pos()
        rcmenu = QMenu(self)

        plugins = self.core.plugins.getPlugins()
        pluginNames = []
        for pluginCat in plugins:
            if pluginCat == "inactive":
                continue

            pluginNames += plugins[pluginCat]

        for plugin in sorted(pluginNames):
            exp = QAction(plugin, self)
            exp.triggered.connect(lambda x=None, p=plugin: self.toggleRequiredPlugin(p))
            rcmenu.addAction(exp)

        rcmenu.exec_(pos)

    @err_catcher(name=__name__)
    def toggleRequiredPlugin(self, plugin: str) -> None:
        """Toggle required plugin on or off.
        
        Adds a plugin to the required plugins list if not present, otherwise
        removes it. Updates the text field with the modified list.
        
        Args:
            plugin: The name of the plugin to toggle.
        """
        plugins = [p.strip() for p in self.e_reqPlugins.text().split(",") if p]
        if plugin in plugins:
            plugins.remove(plugin)
        else:
            plugins.append(plugin)

        self.e_reqPlugins.setText(", ".join(plugins))

    @err_catcher(name=__name__)
    def onDisabledPluginsClicked(self) -> None:
        """Display context menu to toggle disabled plugins.
        
        Shows all available plugins in a context menu, allowing users to toggle
        each plugin's disabled status by toggling it on/off in the list.
        """
        pos = QCursor.pos()
        rcmenu = QMenu(self)

        plugins = self.core.plugins.getPlugins()
        pluginNames = []
        for pluginCat in plugins:
            if pluginCat == "inactive":
                continue

            pluginNames += plugins[pluginCat]

        for plugin in sorted(pluginNames):
            exp = QAction(plugin, self)
            exp.triggered.connect(lambda x=None, p=plugin: self.toggleDisabledPlugin(p))
            rcmenu.addAction(exp)

        rcmenu.exec_(pos)

    @err_catcher(name=__name__)
    def toggleDisabledPlugin(self, plugin: str) -> None:
        """Toggle disabled plugin on or off.
        
        Adds a plugin to the disabled plugins list if not present, otherwise
        removes it. Updates the text field with the modified list.
        
        Args:
            plugin: The name of the plugin to toggle.
        """
        plugins = [p.strip() for p in self.e_disabledPlugins.text().split(",") if p]
        if plugin in plugins:
            plugins.remove(plugin)
        else:
            plugins.append(plugin)

        self.e_disabledPlugins.setText(", ".join(plugins))

    @err_catcher(name=__name__)
    def onBrowseExpPathClicked(self) -> None:
        """Browse and select expected project path.
        
        Opens a folder selection dialog to choose the expected project path
        and updates the corresponding text field with the selected path.
        """
        windowTitle = "Select Expected Project Path"
        startPath = self.e_expectedPrjPath.text() or getattr(self.core, "projectPath", "")
        selectedPath = QFileDialog.getExistingDirectory(
            self, windowTitle, startPath
        )

        if selectedPath:
            self.e_expectedPrjPath.setText(self.core.fixPath(selectedPath))

    @err_catcher(name=__name__)
    def restoreStructurePath(self, widget: QLineEdit, default: bool = False) -> None:
        """Restore folder structure path to default or template value.
        
        Retrieves and sets the default template path for a folder structure key.
        
        Args:
            widget: The line edit widget to update with the path.
            default: If True, restore to original default. Defaults to False.
        """
        key = widget.helpWidget.key
        path = self.core.projects.getTemplatePath(key, default=default)
        widget.setText(path)

    @err_catcher(name=__name__)
    def capturePreview(self) -> None:
        """Capture a screenshot area for project preview image.
        
        Allows user to select a screen area to capture as the project preview image.
        The captured image is scaled to project preview dimensions and displayed in
        the UI. The internal pixmap is stored for later save.
        """
        from PrismUtils import ScreenShot

        previewImg = ScreenShot.grabScreenArea(self.core)

        if previewImg:
            previewImg = self.core.media.scalePixmap(
                previewImg,
                self.core.projects.previewWidth,
                self.core.projects.previewHeight,
            )
            self.previewMap = previewImg
            previewImg = self.core.media.scalePixmap(
                previewImg,
                self.l_preview.geometry().width(),
                self.l_preview.geometry().height(),
            )
            self.l_preview.setPixmap(previewImg)

    @err_catcher(name=__name__)
    def pastePreviewFromClipboard(self) -> None:
        """Paste image from clipboard as project preview.
        
        Retrieves an image from the system clipboard, scales it to the standard
        preview dimensions, and displays it in the preview label.
        """
        pmap = self.core.media.getPixmapFromClipboard()
        if not pmap:
            self.core.popup("No image in clipboard.")
            return

        pmap = self.core.media.scalePixmap(
            pmap, self.core.projects.previewWidth, self.core.projects.previewHeight
        )
        self.previewMap = pmap
        pmap = self.core.media.scalePixmap(
            pmap, self.l_preview.geometry().width(), self.l_preview.geometry().height()
        )
        self.l_preview.setPixmap(pmap)

    @err_catcher(name=__name__)
    def browsePreview(self) -> None:
        """Browse and select an image file for project preview.
        
        Opens a file dialog to select a JPG, PNG, or EXR image file for use as the
        project preview. Automatically scales the image to the standard preview
        dimensions and displays it in the preview label.
        """
        formats = "Image File (*.jpg *.png *.exr)"

        imgPath = QFileDialog.getOpenFileName(
            self, "Select Project Image", "", formats
        )[0]

        if not imgPath:
            return

        if os.path.splitext(imgPath)[1] == ".exr":
            pmsmall = self.core.media.getPixmapFromExrPath(
                imgPath, width=self.core.projects.previewWidth, height=self.core.projects.previewHeight
            )
        else:
            pm = self.core.media.getPixmapFromPath(imgPath)
            if pm.width() == 0:
                warnStr = "Cannot read image: %s" % imgPath
                self.core.popup(warnStr)
                return

            pmsmall = self.core.media.scalePixmap(pm, self.core.projects.previewWidth, self.core.projects.previewHeight)

        self.previewMap = pmsmall
        pmsmall = self.core.media.scalePixmap(
            pmsmall, self.l_preview.geometry().width(), self.l_preview.geometry().height()
        )
        self.l_preview.setPixmap(pmsmall)

    @err_catcher(name=__name__)
    def validate(self, uiWidget: QWidget, origText: Optional[str] = None) -> None:
        """Validate the content of a line edit widget.
        
        Delegates validation to the core's validateLineEdit method. Used to ensure
        input in text fields meets project naming and path conventions.
        
        Args:
            uiWidget: The UI widget to validate.
            origText: Optional original text value for comparison (currently unused).
        """
        self.core.validateLineEdit(uiWidget)

    @err_catcher(name=__name__)
    def pfpsToggled(self, checked: bool) -> None:
        """Handle force FPS checkbox toggle.
        
        Enables/disables the FPS value spinbox based on checkbox state.
        
        Args:
            checked: True if checkbox is checked, False otherwise.
        """
        self.sp_curPfps.setEnabled(checked)

    @err_catcher(name=__name__)
    def prjResolutionToggled(self, checked: bool) -> None:
        """Handle force project resolution checkbox toggle.
        
        Enables/disables resolution spinboxes based on checkbox state.
        
        Args:
            checked: True if checkbox is checked, False otherwise.
        """
        self.sp_prjResolutionWidth.setEnabled(checked)
        self.l_prjResolutionX.setEnabled(checked)
        self.sp_prjResolutionHeight.setEnabled(checked)

    @err_catcher(name=__name__)
    def requirePublishCommentToggled(self, checked: bool) -> None:
        """Handle require publish comment checkbox toggle.
        
        Enables/disables the publish comment length spinbox based on checkbox state.
        
        Args:
            checked: True if checkbox is checked, False otherwise.
        """
        self.sp_publishComment.setEnabled(checked)
        self.l_publishCommentChars.setEnabled(checked)

    @err_catcher(name=__name__)
    def episodesToggled(self, checked: bool) -> None:
        """Handle use episodes checkbox toggle.
        
        Updates the sequences folder template based on episode setting. Prompts
        user to update template if needed and saves settings.
        
        Args:
            checked: True if episodes are enabled, False otherwise.
        """
        if checked:
            template = "@episode_path@/@sequence@"
        else:
            template = "@project_path@/03_Production/Shots/@sequence@"            

        for widget in self.folderStructureWidgets:
            if widget["key"] == "sequences":
                if widget["widget"].text() != template:
                    msg = "Do you want to update your \"Sequences\" folder template to the recommended value?\n\nCurrent template:\n%s\n\nRecommended template:\n%s" % (widget["widget"].text(), template)
                    result = self.core.popupQuestion(msg)
                    if result == "Yes":
                        widget["widget"].setText(template)

        self.saveSettings(changeProject=False)
        self.core.projects.refreshUseEpisode(self.projectConfig)
        self.refreshFolderStructure()

    @err_catcher(name=__name__)
    def productTasksToggled(self, checked: bool) -> None:
        """Handle product tasks checkbox toggle.
        
        Updates export and render folder templates based on product tasks setting.
        Reflects whether departments and tasks should be part of the path structure.
        
        Args:
            checked: True if product tasks are enabled, False otherwise.
        """
        if checked:
            if os.getenv("PRISM_USE_DEPARTMENTS_FOR_PRODUCTS", "1") == "1":
                template = "@entity_path@/Export/@department@/@task@/@product@"
            else:
                template = "@entity_path@/Export/@task@/@product@"
        else:
            template = "@entity_path@/Export/@product@"

        yesAll = False
        for widget in self.folderStructureWidgets:
            if widget["key"] == "products":
                if widget["widget"].text() != template:
                    if yesAll:
                        result = "Yes"
                    else:
                        msg = "Do you want to update your \"Products\" folder template to the recommended value?\n\nCurrent template:\n%s\n\nRecommended template:\n%s" % (widget["widget"].text(), template)
                        result = self.core.popupQuestion(msg, buttons=["Yes", "Yes to all", "No"])
                        if result == "Yes to all":
                            result = "Yes"
                            yesAll = True

                    if result == "Yes":
                        widget["widget"].setText(template)

        if checked:
            if os.getenv("PRISM_USE_DEPARTMENTS_FOR_PRODUCTS", "1") == "1":
                template = "@entity_path@/Renders/@department@/@task@/3dRender/@identifier@"
            else:
                template = "@entity_path@/Renders/@task@/3dRender/@identifier@"
        else:
            template = "@entity_path@/Renders/3dRender/@identifier@"

        for widget in self.folderStructureWidgets:
            if widget["key"] == "3drenders":
                if widget["widget"].text() != template:
                    if yesAll:
                        result = "Yes"
                    else:
                        msg = "Do you want to update your \"3D Render\" folder template to the recommended value?\n\nCurrent template:\n%s\n\nRecommended template:\n%s" % (widget["widget"].text(), template)
                        result = self.core.popupQuestion(msg, buttons=["Yes", "Yes to all", "No"])
                        if result == "Yes to all":
                            result = "Yes"
                            yesAll = True

                    if result == "Yes":
                        widget["widget"].setText(template)

        if checked:
            if os.getenv("PRISM_USE_DEPARTMENTS_FOR_PRODUCTS", "1") == "1":
                template = "@entity_path@/Renders/@department@/@task@/2dRender/@identifier@"
            else:
                template = "@entity_path@/Renders/@task@/2dRender/@identifier@"
        else:
            template = "@entity_path@/Renders/2dRender/@identifier@"

        for widget in self.folderStructureWidgets:
            if widget["key"] == "2drenders":
                if widget["widget"].text() != template:
                    if yesAll:
                        result = "Yes"
                    else:
                        msg = "Do you want to update your \"2D Render\" folder template to the recommended value?\n\nCurrent template:\n%s\n\nRecommended template:\n%s" % (widget["widget"].text(), template)
                        result = self.core.popupQuestion(msg, buttons=["Yes", "Yes to all", "No"])
                        if result == "Yes to all":
                            result = "Yes"
                            yesAll = True

                    if result == "Yes":
                        widget["widget"].setText(template)

        if checked:
            if os.getenv("PRISM_USE_DEPARTMENTS_FOR_PRODUCTS", "1") == "1":
                template = "@entity_path@/Renders/@department@/@task@/external/@identifier@"
            else:
                template = "@entity_path@/Renders/@task@/external/@identifier@"
        else:
            template = "@entity_path@/Renders/external/@identifier@"

        for widget in self.folderStructureWidgets:
            if widget["key"] == "externalMedia":
                if widget["widget"].text() != template:
                    if yesAll:
                        result = "Yes"
                    else:
                        msg = "Do you want to update your \"External Media\" folder template to the recommended value?\n\nCurrent template:\n%s\n\nRecommended template:\n%s" % (widget["widget"].text(), template)
                        result = self.core.popupQuestion(msg, buttons=["Yes", "Yes to all", "No"])
                        if result == "Yes to all":
                            result = "Yes"
                            yesAll = True

                    if result == "Yes":
                        widget["widget"].setText(template)

        if checked:
            if os.getenv("PRISM_USE_DEPARTMENTS_FOR_PRODUCTS", "1") == "1":
                template = "@entity_path@/Renders/@department@/@task@/Playblasts/@identifier@"
            else:
                template = "@entity_path@/Renders/@task@/Playblasts/@identifier@"
        else:
            template = "@entity_path@/Playblasts/@identifier@"

        for widget in self.folderStructureWidgets:
            if widget["key"] == "playblasts":
                if widget["widget"].text() != template:
                    if yesAll:
                        result = "Yes"
                    else:
                        msg = "Do you want to update your \"Playblasts\" folder template to the recommended value?\n\nCurrent template:\n%s\n\nRecommended template:\n%s" % (widget["widget"].text(), template)
                        result = self.core.popupQuestion(msg, buttons=["Yes", "Yes to all", "No"])
                        if result == "Yes to all":
                            result = "Yes"
                            yesAll = True

                    if result == "Yes":
                        widget["widget"].setText(template)

    @err_catcher(name=__name__)
    def saveSettings(self, changeProject: bool = True, configPath: Optional[str] = None, export: bool = False) -> None:
        """Save all project settings to configuration file.
        
        Collects all current UI settings into a configuration dictionary and saves
        it to the specified config path. Handles folder structure validation,
        environment variables, departments, paths, and task presets. Triggers
        pre/post save callbacks and optionally changes the active project.
        
        Args:
            changeProject: If True and saving main project config, triggers project
                change after save. Defaults to True.
            configPath: Path where config should be saved. If None, uses the main
                project config path. Defaults to None.
            export: If True, indicates this is an export operation rather than a
                save of the main project config. Defaults to False.
        """
        logger.debug("save project settings")

        if configPath is None:
            configPath = self.projectConfig

        cData = {"globals": {}}

        cData["globals"]["project_name"] = self.e_curPname.text()
        cData["globals"]["uselocalfiles"] = self.chb_curPuseLocal.isChecked()
        cData["globals"]["track_dependencies"] = [
            x
            for x in self.dependencyStates
            if self.dependencyStates[x] == self.cb_dependencies.currentText()
        ][0]
        cData["globals"]["forcefps"] = self.chb_curPuseFps.isChecked()
        cData["globals"]["fps"] = self.sp_curPfps.value()
        cData["globals"]["forceResolution"] = self.chb_prjResolution.isChecked()
        cData["globals"]["resolution"] = [
            self.sp_prjResolutionWidth.value(),
            self.sp_prjResolutionHeight.value(),
        ]
        cData["globals"]["versionPadding"] = self.sp_curPversionPadding.value()
        cData["globals"]["framePadding"] = self.sp_curPframePadding.value()
        cData["globals"]["prism_version"] = self.e_version.text()
        cData["globals"]["useMasterVersion"] = self.chb_curPuseMaster.isChecked()
        cData["globals"][
            "useMasterRenderVersion"
        ] = self.chb_curPuseMasterRender.isChecked()
        cData["globals"][
            "useEpisodes"
        ] = self.chb_curPepisodes.isChecked()
        cData["globals"][
            "backupScenesOnPublish"
        ] = self.chb_curPbackupPublishes.isChecked()
        cData["globals"][
            "scenefileLocking"
        ] = self.chb_curPscenefileLocking.isChecked()
        cData["globals"][
            "productTasks"
        ] = self.chb_curPproductTasks.isChecked()
        cData["globals"][
            "matchScenefileVersions"
        ] = self.chb_matchScenefileVersions.isChecked()
        cData["globals"][
            "requirePublishComment"
        ] = self.chb_curPRequirePublishComment.isChecked()
        cData["globals"]["publishCommentLength"] = self.sp_publishComment.value()
        cData["globals"]["required_plugins"] = [x.strip() for x in self.e_reqPlugins.text().split(",") if x]
        cData["globals"]["disabled_plugins"] = [x.strip() for x in self.e_disabledPlugins.text().split(",") if x]
        cData["globals"]["expectedPrjPath"] = self.e_expectedPrjPath.text()
        cData["globals"]["expectedPrismVersions"] = self.e_expectedPrismVersion.text()
        cData["globals"]["expectedPrismVersionMode"] = self.cb_expectedPrismVersion.currentText()
        cData["globals"]["defaultImportStateName"] = self.e_defaultImportStateName.text()
        cData["changeProject"] = changeProject
        structure = self.getFolderStructure()
        if self.isValidStructure(structure) or os.getenv("PRISM_ENFORCE_FOLDER_STRUCTURE_RULES", "1") != "1":
            valStruct = self.core.projects.getStructureValues(structure)
            cData["folder_structure"] = valStruct
        else:
            msg = "The project folderstructure is invalid and cannot be saved"
            self.core.popup(msg)

        cData["globals"]["allowAdditionalTasks"] = self.chb_allowAdditionalTasks.isChecked()
        cData["environmentVariables"] = self.getEnvironmentVariables()
        cData["globals"]["departments_asset"] = self.getAssetDepartments()
        cData["globals"]["departments_shot"] = self.getShotDepartments()
        cData["export_paths"] = self.getExportLocations()
        cData["render_paths"] = self.getRenderLocations()

        if "studio" not in cData:
            cData["studio"] = {}

        if "globals" not in cData:
            cData["globals"] = {}

        cData["studio"]["stateDefaults"] = self.gb_stateDefaults.getItemData()
        cData["studio"]["statePresets"] = self.gb_statePresets.getItemData()
        cData["globals"]["presetScenes"] = self.gb_presetScenes.getItemData()

        self.tmp_configPath = configPath
        self.tmp_export = export
        self.core.callback(name="preProjectSettingsSave", args=[self, cData])
        self.tmp_configPath = None
        self.tmp_export = None
        changeProject = cData["changeProject"]
        cData.pop("changeProject")

        if configPath:
            image = self.previewMap
            if image:
                imagePath = self.core.projects.getProjectImage(
                    projectConfig=configPath, validate=False
                )
                self.core.media.savePixmap(image, imagePath)

            self.core.setConfig(data=cData, configPath=configPath, updateNestedData={"exclude": ["environmentVariables", "folder_structure", "jobEnvVars", "render_paths", "export_paths"]})

            if configPath == self.core.prismIni and not export:
                self.core.projects.refreshLocalFiles()
                if changeProject:
                    self.core.callback(name="postProjectSettingsSave", args=[self, cData])
                    self.signalSaved.emit(cData)
                    self.core.changeProject(
                        self.core.prismIni, settingsTab=self.tw_settings.currentIndex(), settingsType="Project",
                    )
                    return

        self.core.callback(name="postProjectSettingsSave", args=[self, cData])
        self.signalSaved.emit(cData)

    @err_catcher(name=__name__)
    def getFolderStructure(self) -> Dict[str, Any]:
        """Get the current folder structure configuration.
        
        Retrieves all folder structure template paths from UI widgets and returns
        them as an ordered dictionary with keys, items metadata, and current values.
        
        Returns:
            OrderedDict with folder structure configuration where each entry contains
            the key, item metadata, and the current template value.
        """
        data = OrderedDict([])
        for widgetData in self.folderStructureWidgets:
            data[widgetData["key"]] = widgetData["item"]
            data[widgetData["key"]]["value"] = widgetData["widget"].text()

        return data

    @err_catcher(name=__name__)
    def isValidStructure(self, structure: Dict[str, Any]) -> bool:
        """Validate the folder structure configuration.
        
        Checks each folder structure key using core validation rules to ensure
        all paths comply with project folder standards.
        
        Args:
            structure: Dictionary of folder structure configuration to validate.
        
        Returns:
            True if all structure keys are valid, False otherwise.
        """
        for key in structure:
            if (
                self.core.projects.validateFolderKey(structure[key]["value"], structure[key])
                is not True
            ):
                logger.debug("invalid key: %s" % key)
                return False

        return True

    @err_catcher(name=__name__)
    def getExportLocations(self) -> Dict[str, str]:
        """Get all export location paths from the export paths table.
        
        Retrieves key-value pairs from the export paths table widget, skipping
        placeholder or empty entries.
        
        Returns:
            Dictionary mapping export location names/keys to their file system paths.
        """
        locations = {}
        dft = "< doubleclick to edit >"
        for idx in range(self.tw_exportPaths.rowCount()):
            key = self.tw_exportPaths.item(idx, 0).text()
            if not key or key == dft:
                continue

            value = self.tw_exportPaths.item(idx, 1).text()
            if value == dft:
                continue

            locations[key] = value

        return locations

    @err_catcher(name=__name__)
    def getRenderLocations(self) -> Dict[str, str]:
        """Get all render location paths from the render paths table.
        
        Retrieves key-value pairs from the render paths table widget, skipping
        placeholder or empty entries.
        
        Returns:
            Dictionary mapping render location names/keys to their file system paths.
        """
        locations = {}
        dft = "< doubleclick to edit >"
        for idx in range(self.tw_renderPaths.rowCount()):
            key = self.tw_renderPaths.item(idx, 0).text()
            if not key or key == dft:
                continue

            value = self.tw_renderPaths.item(idx, 1).text()
            if value == dft:
                continue

            locations[key] = value

        return locations

    @err_catcher(name=__name__)
    def getEnvironmentVariables(self) -> Dict[str, str]:
        """Get all environment variables from the environment table.
        
        Retrieves key-value pairs from the environment variables table widget,
        skipping placeholder or empty entries.
        
        Returns:
            Dictionary mapping environment variable names to their values.
        """
        variables = {}
        dft = "< doubleclick to edit >"
        for idx in range(self.tw_environment.rowCount()):
            key = self.tw_environment.item(idx, 0).text()
            if not key or key == dft:
                continue

            value = self.tw_environment.item(idx, 1).text()
            if value == dft:
                continue

            variables[key] = value

        return variables

    @err_catcher(name=__name__)
    def loadEnvironmant(self, variables: Dict[str, str]) -> None:
        """Load environment variables into the environment table widget.
        
        Note: This method name contains a typo (should be 'loadEnvironment').
        Populates the environment variables table widget with key-value pairs.
        Variables are sorted by key for consistent display.
        
        Args:
            variables: Dictionary mapping environment variable names to their values.
        """
        self.tw_environment.setRowCount(0)
        for idx, key in enumerate(sorted(variables)):
            self.tw_environment.insertRow(idx)
            item = QTableWidgetItem(key)
            self.tw_environment.setItem(idx, 0, item)
            item = QTableWidgetItem(variables[key])
            self.tw_environment.setItem(idx, 1, item)

    @err_catcher(name=__name__)
    def loadSettings(self, configPath: Optional[str] = None) -> None:
        """Load project settings from configuration file and populate UI widgets.
        
        Loads all project configuration data from a config file or pre-loaded data,
        then populates all UI elements (text fields, checkboxes, tables, etc.) with
        the loaded values. Also loads preview image and triggers callbacks.
        
        Args:
            configPath: Optional path to a specific config file. If not provided,
                uses the pre-loaded projectData.
        """
        if configPath is not None:
            configData = self.core.getConfig(configPath=configPath)
        else:
            configData = self.projectData
        
        prjPath = None
        if self.projectConfig:
            configPath = self.projectConfig
            prjPath = self.core.projects.getProjectFolderFromConfigPath(configPath, norm=True) if configPath else None

        self.previewMap = None
        if not configData and os.path.exists(self.projectConfig):
            configData = self.core.getConfig(configPath=self.projectConfig)
            image = self.core.projects.getProjectImage(projectConfig=self.projectConfig)
            if image:
                self.previewMap = QPixmap(image)
                geo = self.l_preview.geometry()
                smallPixmap = self.core.media.scalePixmap(
                    self.previewMap, geo.width(), geo.height(), keepRatio=False
                )
                self.l_preview.setPixmap(smallPixmap)

        self.core.callback(name="preProjectSettingsLoad", args=[self, configData])
        gblData = configData.get("globals", {}) if configData else {}

        if prjPath:
            self.l_curPpath.setText(prjPath)

        if "project_name" in gblData:
            self.e_curPname.setText(gblData["project_name"])
        if "uselocalfiles" in gblData:
            self.chb_curPuseLocal.setChecked(gblData["uselocalfiles"])
        if "track_dependencies" in gblData:
            if not self.core.isStr(gblData["track_dependencies"]):
                gblData["track_dependencies"] = "publish"
            idx = self.cb_dependencies.findText(
                self.dependencyStates[gblData["track_dependencies"]]
            )
            if idx != -1:
                self.cb_dependencies.setCurrentIndex(idx)
        if "forcefps" in gblData:
            self.chb_curPuseFps.setChecked(gblData["forcefps"])
        if "fps" in gblData:
            self.sp_curPfps.setValue(gblData["fps"])
        if "forceResolution" in gblData:
            self.chb_prjResolution.setChecked(gblData["forceResolution"])
        if "resolution" in gblData:
            self.sp_prjResolutionWidth.setValue(gblData["resolution"][0])
            self.sp_prjResolutionHeight.setValue(gblData["resolution"][1])
        if "versionPadding" in gblData:
            self.sp_curPversionPadding.setValue(gblData["versionPadding"])
        if "framePadding" in gblData:
            self.sp_curPframePadding.setValue(gblData["framePadding"])
        if "prism_version" in gblData:
            self.e_version.setText(gblData["prism_version"])
        if "useMasterVersion" in gblData:
            self.chb_curPuseMaster.setChecked(gblData["useMasterVersion"])
        if "useMasterRenderVersion" in gblData:
            self.chb_curPuseMasterRender.setChecked(gblData["useMasterRenderVersion"])
        if "useEpisodes" in gblData:
            self.chb_curPepisodes.setChecked(
                gblData["useEpisodes"]
            )
        if "backupScenesOnPublish" in gblData:
            self.chb_curPbackupPublishes.setChecked(
                gblData["backupScenesOnPublish"]
            )
        if "scenefileLocking" in gblData:
            self.chb_curPscenefileLocking.setChecked(
                gblData["scenefileLocking"]
            )
        if "productTasks" in gblData:
            self.chb_curPproductTasks.setChecked(
                gblData["productTasks"]
            )
        if "matchScenefileVersions" in gblData:
            self.chb_matchScenefileVersions.setChecked(
                gblData["matchScenefileVersions"]
            )
        if "requirePublishComment" in gblData:
            self.chb_curPRequirePublishComment.setChecked(
                gblData["requirePublishComment"]
            )
        if "publishCommentLength" in gblData:
            self.sp_publishComment.setValue(gblData["publishCommentLength"])
        if "required_plugins" in gblData:
            self.e_reqPlugins.setText(", ".join(gblData["required_plugins"]))
        if "disabled_plugins" in gblData:
            self.e_disabledPlugins.setText(", ".join(gblData["disabled_plugins"]))
        if "expectedPrjPath" in gblData:
            self.e_expectedPrjPath.setText(gblData["expectedPrjPath"])
        if "expectedPrismVersions" in gblData:
            self.e_expectedPrismVersion.setText(gblData["expectedPrismVersions"])
        if "expectedPrismVersionMode" in gblData:
            idx = self.cb_expectedPrismVersion.findText(gblData["expectedPrismVersionMode"])
            if idx >= 0:
                self.cb_expectedPrismVersion.setCurrentIndex(idx)
        if "defaultImportStateName" in gblData:
            self.e_defaultImportStateName.setText(gblData["defaultImportStateName"])
        if "allowAdditionalTasks" in gblData:
            self.chb_allowAdditionalTasks.setChecked(gblData["allowAdditionalTasks"])
        if configData and "environmentVariables" in configData and configData["environmentVariables"]:
            self.loadEnvironmant(configData["environmentVariables"])

        self.refreshAssetDepartments(configData=configData)
        self.refreshShotDepartments(configData=configData)
        self.refreshAssetTaskPresets(configData=configData)
        self.refreshShotTaskPresets(configData=configData)
        self.refreshExportPaths(configData=configData)
        self.refreshRenderPaths(configData=configData)

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "folder.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.b_expectedPrjPath.setIcon(icon)

        self.pfpsToggled(self.chb_curPuseFps.isChecked())
        self.w_curPfps.setToolTip(
            "When this option is enabled, Prism checks the fps of scenefiles when they are opened and shows a warning, if they don't match the project fps."
        )

        self.prjResolutionToggled(self.chb_prjResolution.isChecked())
        self.w_prjResolution.setToolTip(
            "When this option is enabled, Prism checks the resolution of Nuke scripts when they are opened and shows a warning, if they don't match the project resolution."
        )
        self.requirePublishCommentToggled(self.chb_curPRequirePublishComment.isChecked())

        if configData and "studio" in configData:
            if "stateDefaults" in configData["studio"]:
                val = configData["studio"]["stateDefaults"]
                if val:
                    self.gb_stateDefaults.loadStateData(val)

            if "statePresets" in configData["studio"]:
                val = configData["studio"]["statePresets"]
                if val:
                    self.gb_statePresets.loadPresetData(val)

        if configData and "globals" in configData:
            if "presetScenes" in configData["globals"]:
                val = configData["globals"]["presetScenes"]
                if val:
                    self.gb_presetScenes.loadPresetData(val)

        self.core.callback(name="postProjectSettingsLoad", args=[self, configData])

    @err_catcher(name=__name__)
    def refreshAssetDepartments(self, departments: Optional[List[Dict[str, Any]]] = None, configData: Optional[Dict[str, Any]] = None) -> None:
        """Refresh asset departments table widget.
        
        Populates the asset departments table with department information including
        name, abbreviation, and default tasks.
        
        Args:
            departments: Optional list of asset department dicts. If None, fetches
                from project configuration. Defaults to None.
            configData: Optional project configuration data. Used if departments
                are not provided. Defaults to None.
        """
        if departments is None:
            if configData is None:
                configData = self.projectData

            departments = self.core.projects.getAssetDepartments(configData=configData) or []

        self.tw_assetDepartments.setRowCount(0)
        for dep in departments:
            name = "%s (%s)" % (dep.get("name"), dep.get("abbreviation"))
            nameItem = QTableWidgetItem(name)
            nameItem.setData(Qt.UserRole, dep)
            taskItem = QTableWidgetItem("\n".join(dep.get("defaultTasks") or []))

            rc = self.tw_assetDepartments.rowCount()
            self.tw_assetDepartments.insertRow(rc)

            self.tw_assetDepartments.setItem(rc, 0, nameItem)
            self.tw_assetDepartments.setItem(rc, 1, taskItem)

        self.tw_assetDepartments.resizeRowsToContents()
        self.tw_assetDepartments.resizeColumnsToContents()
        self.tw_assetDepartments.setColumnWidth(0, self.tw_assetDepartments.columnWidth(0) + 20)

    @err_catcher(name=__name__)
    def refreshShotDepartments(self, departments: Optional[List[Dict[str, Any]]] = None, configData: Optional[Dict[str, Any]] = None) -> None:
        """Refresh shot departments table widget.
        
        Populates the shot departments table with department information including
        name, abbreviation, and default tasks.
        
        Args:
            departments: Optional list of shot department dicts. If None, fetches
                from project configuration. Defaults to None.
            configData: Optional project configuration data. Used if departments
                are not provided. Defaults to None.
        """
        if departments is None:
            if configData is None:
                configData = self.projectData

            departments = self.core.projects.getShotDepartments(configData=configData) or []

        self.tw_shotDepartments.setRowCount(0)
        for dep in departments:
            name = "%s (%s)" % (dep.get("name"), dep.get("abbreviation"))
            nameItem = QTableWidgetItem(name)
            nameItem.setData(Qt.UserRole, dep)
            taskItem = QTableWidgetItem("\n".join(dep.get("defaultTasks")))

            rc = self.tw_shotDepartments.rowCount()
            self.tw_shotDepartments.insertRow(rc)

            self.tw_shotDepartments.setItem(rc, 0, nameItem)
            self.tw_shotDepartments.setItem(rc, 1, taskItem)

        self.tw_shotDepartments.resizeRowsToContents()
        self.tw_shotDepartments.resizeColumnsToContents()
        self.tw_shotDepartments.setColumnWidth(0, self.tw_shotDepartments.columnWidth(0) + 20)

    @err_catcher(name=__name__)
    def assetDepartmentRowMoved(self, logicalIdx: int, oldVisualIdx: int, newVisualIdx: int) -> None:
        """Handle asset department row reordering.
        
        Called when user reorders asset departments via drag-and-drop. Updates the
        department list and maintains the new selection.
        
        Args:
            logicalIdx: Logical column index being moved.
            oldVisualIdx: Previous visual position of the row.
            newVisualIdx: New visual position of the row.
        """
        departments = self.getAssetDepartments()
        self.refreshAssetDepartments(departments=departments)
        self.tw_assetDepartments.selectRow(newVisualIdx)

    @err_catcher(name=__name__)
    def shotDepartmentRowMoved(self, logicalIdx: int, oldVisualIdx: int, newVisualIdx: int) -> None:
        """Handle shot department row reordering.
        
        Called when user reorders shot departments via drag-and-drop. Updates the
        department list and maintains the new selection.
        
        Args:
            logicalIdx: Logical column index being moved.
            oldVisualIdx: Previous visual position of the row.
            newVisualIdx: New visual position of the row.
        """
        departments = self.getShotDepartments()
        self.refreshShotDepartments(departments=departments)
        self.tw_shotDepartments.selectRow(newVisualIdx)

    @err_catcher(name=__name__)
    def addAssetDepartmentClicked(self) -> None:
        """Handle add asset department button click.
        
        Opens the create department dialog for assets, saves existing departments,
        and refreshes the UI when a new department is created.
        """
        self.saveAssetDepartments()
        self.dlg_department = PrismWidgets.CreateDepartmentDlg(core=self.core, entity="asset", configData=self.projectData, parent=self)
        self.dlg_department.departmentCreated.connect(lambda x: self.onDepartmentCreated("asset"))
        self.dlg_department.exec_()

    @err_catcher(name=__name__)
    def saveAssetDepartments(self) -> None:
        """Save asset departments to project configuration.
        
        Collects all asset departments from the UI table and saves them to the
        project configuration data.
        """
        deps = self.getAssetDepartments()
        self.core.projects.setDepartments("asset", deps, configData=self.projectData)

    @err_catcher(name=__name__)
    def onDepartmentCreated(self, entity: str) -> None:
        """Handle department creation completion.
        
        Called after a new department is successfully created. Refreshes the
        appropriate department list (asset or shot).
        
        Args:
            entity: The entity type - either 'asset' or 'shot'.
        """
        if entity == "asset":
            self.refreshAssetDepartments()
        elif entity == "shot":
            self.refreshShotDepartments()

    @err_catcher(name=__name__)
    def removeAssetDepartmentClicked(self) -> None:
        """Remove selected asset departments.
        
        Deletes all selected asset department rows from the table widget.
        """
        items = self.tw_assetDepartments.selectedItems()
        rows = []
        for item in items:
            if item.column() == 0:
                rows.append(item.row())

        for idx in sorted(rows, reverse=True):
            self.tw_assetDepartments.removeRow(idx)

    @err_catcher(name=__name__)
    def addShotDepartmentClicked(self) -> None:
        """Handle add shot department button click.
        
        Opens the create department dialog for shots, saves existing departments,
        and refreshes the UI when a new department is created.
        """
        self.saveShotDepartments()
        self.dlg_department = PrismWidgets.CreateDepartmentDlg(core=self.core, entity="shot", configData=self.projectData, parent=self)
        self.dlg_department.departmentCreated.connect(lambda x: self.onDepartmentCreated("shot"))
        self.dlg_department.exec_()

    @err_catcher(name=__name__)
    def saveShotDepartments(self) -> None:
        """Save shot departments to project configuration.
        
        Collects all shot departments from the UI table and saves them to the
        project configuration data.
        """
        deps = self.getShotDepartments()
        self.core.projects.setDepartments("shot", deps, configData=self.projectData)

    @err_catcher(name=__name__)
    def removeShotDepartmentClicked(self) -> None:
        """Remove selected shot departments.
        
        Deletes all selected shot department rows from the table widget.
        """
        items = self.tw_shotDepartments.selectedItems()
        rows = []
        for item in items:
            if item.column() == 0:
                rows.append(item.row())

        for idx in sorted(rows, reverse=True):
            self.tw_shotDepartments.removeRow(idx)

    @err_catcher(name=__name__)
    def assetDepsRightClicked(self, pos: QPoint) -> None:
        """Display context menu for asset departments table.
        
        Shows options to add, edit, remove, reorder, and restore asset departments.
        Menu actions are enabled/disabled based on current selections.
        
        Args:
            pos: The position where the right-click occurred.
        """
        rcmenu = QMenu(self)

        exp = QAction("Add...", self)
        exp.triggered.connect(self.addAssetDepartmentClicked)
        rcmenu.addAction(exp)

        clipAct = QAction("Edit...", self)
        clipAct.triggered.connect(lambda: self.editAssetDepartment(self.tw_assetDepartments.selectedItems()[0]))
        rcmenu.addAction(clipAct)
        if not len(self.tw_assetDepartments.selectedItems()) == 2:
            clipAct.setEnabled(False)

        copAct = QAction("Remove", self)
        copAct.triggered.connect(self.removeAssetDepartmentClicked)
        rcmenu.addAction(copAct)
        if not self.tw_assetDepartments.selectedItems():
            copAct.setEnabled(False)

        clipAct = QAction("Move up", self)
        clipAct.triggered.connect(self.moveUpAssetDepartment)
        rcmenu.addAction(clipAct)
        if 0 in [i.row() for i in self.tw_assetDepartments.selectedItems()] or not self.tw_assetDepartments.selectedItems():
            clipAct.setEnabled(False)

        clipAct = QAction("Move down", self)
        clipAct.triggered.connect(self.moveDownAssetDepartment)
        rcmenu.addAction(clipAct)
        if (self.tw_assetDepartments.rowCount()-1) in [i.row() for i in self.tw_assetDepartments.selectedItems()] or not self.tw_assetDepartments.selectedItems():
            clipAct.setEnabled(False)

        clipAct = QAction("Restore defaults", self)
        clipAct.triggered.connect(self.restoreAssetDepsTriggered)
        rcmenu.addAction(clipAct)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def shotDepsRightClicked(self, pos: QPoint) -> None:
        """Display context menu for shot departments table.
        
        Shows options to add, edit, remove, reorder, and restore shot departments.
        Menu actions are enabled/disabled based on current selections.
        
        Args:
            pos: The position where the right-click occurred.
        """
        rcmenu = QMenu(self)

        exp = QAction("Add...", self)
        exp.triggered.connect(self.addShotDepartmentClicked)
        rcmenu.addAction(exp)

        clipAct = QAction("Edit...", self)
        clipAct.triggered.connect(lambda: self.editShotDepartment(self.tw_shotDepartments.selectedItems()[0]))
        rcmenu.addAction(clipAct)
        if not len(self.tw_shotDepartments.selectedItems()) == 2:
            clipAct.setEnabled(False)

        copAct = QAction("Remove", self)
        copAct.triggered.connect(self.removeShotDepartmentClicked)
        rcmenu.addAction(copAct)
        if not self.tw_shotDepartments.selectedItems():
            copAct.setEnabled(False)

        clipAct = QAction("Move up", self)
        clipAct.triggered.connect(self.moveUpShotDepartment)
        rcmenu.addAction(clipAct)
        if 0 in [i.row() for i in self.tw_shotDepartments.selectedItems()] or not self.tw_shotDepartments.selectedItems():
            clipAct.setEnabled(False)

        clipAct = QAction("Move down", self)
        clipAct.triggered.connect(self.moveDownShotDepartment)
        rcmenu.addAction(clipAct)
        if (self.tw_shotDepartments.rowCount()-1) in [i.row() for i in self.tw_shotDepartments.selectedItems()] or not self.tw_shotDepartments.selectedItems():
            clipAct.setEnabled(False)

        clipAct = QAction("Restore defaults", self)
        clipAct.triggered.connect(self.restoreShotDepsTriggered)
        rcmenu.addAction(clipAct)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def moveUpAssetDepartment(self) -> None:
        """Move selected asset department up in the table.
        
        Reorders selected asset departments one row higher, maintaining their
        relative order and updating the display.
        """
        items = self.tw_assetDepartments.selectedItems()
        rows = []
        for item in items:
            if item.column() == 0:
                rows.append(item.row())

        deps = self.getAssetDepartments()
        for idx in sorted(rows):
            row = deps.pop(idx)
            deps.insert(idx-1, row)

        self.refreshAssetDepartments(departments=deps)
        self.tw_assetDepartments.setSelectionMode(QAbstractItemView.MultiSelection)
        for idx in sorted(rows):
            self.tw_assetDepartments.selectRow(idx-1)

        self.tw_assetDepartments.setSelectionMode(QAbstractItemView.ExtendedSelection)

    @err_catcher(name=__name__)
    def moveDownAssetDepartment(self) -> None:
        """Move selected asset department down in the table.
        
        Reorders selected asset departments one row lower, maintaining their
        relative order and updating the display.
        """
        items = self.tw_assetDepartments.selectedItems()
        rows = []
        for item in items:
            if item.column() == 0:
                rows.append(item.row())

        deps = self.getAssetDepartments()
        for idx in sorted(rows):
            row = deps.pop(idx)
            deps.insert(idx+1, row)

        self.refreshAssetDepartments(departments=deps)
        self.tw_assetDepartments.setSelectionMode(QAbstractItemView.MultiSelection)
        for idx in sorted(rows):
            self.tw_assetDepartments.selectRow(idx+1)

        self.tw_assetDepartments.setSelectionMode(QAbstractItemView.ExtendedSelection)

    @err_catcher(name=__name__)
    def moveUpShotDepartment(self) -> None:
        """Move selected shot department up in the table.
        
        Reorders selected shot departments one row higher, maintaining their
        relative order and updating the display.
        """
        items = self.tw_shotDepartments.selectedItems()
        rows = []
        for item in items:
            if item.column() == 0:
                rows.append(item.row())

        deps = self.getShotDepartments()
        for idx in sorted(rows):
            row = deps.pop(idx)
            deps.insert(idx-1, row)

        self.refreshShotDepartments(departments=deps)
        self.tw_shotDepartments.setSelectionMode(QAbstractItemView.MultiSelection)
        for idx in sorted(rows):
            self.tw_shotDepartments.selectRow(idx-1)

        self.tw_shotDepartments.setSelectionMode(QAbstractItemView.ExtendedSelection)

    @err_catcher(name=__name__)
    def moveDownShotDepartment(self) -> None:
        """Move selected shot department down in the table.
        
        Reorders selected shot departments one row lower, maintaining their
        relative order and updating the display.
        """
        items = self.tw_shotDepartments.selectedItems()
        rows = []
        for item in items:
            if item.column() == 0:
                rows.append(item.row())

        deps = self.getShotDepartments()
        for idx in sorted(rows):
            row = deps.pop(idx)
            deps.insert(idx+1, row)

        self.refreshShotDepartments(departments=deps)
        self.tw_shotDepartments.setSelectionMode(QAbstractItemView.MultiSelection)
        for idx in sorted(rows):
            self.tw_shotDepartments.selectRow(idx+1)

        self.tw_shotDepartments.setSelectionMode(QAbstractItemView.ExtendedSelection)

    @err_catcher(name=__name__)
    def restoreAssetDepsTriggered(self) -> None:
        """Restore asset departments to project defaults.
        
        Resets the asset departments list to the default configuration from
        the default project settings.
        """
        configData = self.core.projects.getDefaultProjectSettings()
        self.refreshAssetDepartments(configData=configData)

    @err_catcher(name=__name__)
    def restoreShotDepsTriggered(self) -> None:
        """Restore shot departments to project defaults.
        
        Resets the shot departments list to the default configuration from
        the default project settings.
        """
        configData = self.core.projects.getDefaultProjectSettings()
        self.refreshShotDepartments(configData=configData)

    @err_catcher(name=__name__)
    def assetDepartmentDoubleClicked(self, item: QTableWidgetItem) -> None:
        """Handle asset department double-click for editing.
        
        Args:
            item: The table widget item that was double-clicked.
        """
        self.editAssetDepartment(item)

    @err_catcher(name=__name__)
    def editAssetDepartment(self, item: QTableWidgetItem) -> None:
        """Edit an asset department's properties.
        
        Opens the department edit dialog, retrieves department data, updates the
        UI table with modified information, and persists changes.
        
        Args:
            item: The table widget item representing the department to edit.
        """
        self.saveAssetDepartments()
        dep = self.tw_assetDepartments.item(item.row(), 0).data(Qt.UserRole)
        self.dlg_department = PrismWidgets.CreateDepartmentDlg(core=self.core, entity="asset", configData=self.projectData, department=dep, parent=self)
        result = self.dlg_department.exec_()
        if not result:
            return

        department = self.dlg_department.getDepartment()
        name = "%s (%s)" % (department["name"], department["abbreviation"])
        self.tw_assetDepartments.item(item.row(), 0).setText(name)
        self.tw_assetDepartments.item(item.row(), 0).setData(Qt.UserRole, department)
        self.tw_assetDepartments.item(item.row(), 1).setText("\n".join(department["defaultTasks"]))
        self.tw_assetDepartments.resizeRowsToContents()
        self.tw_assetDepartments.resizeColumnsToContents()
        self.tw_assetDepartments.setColumnWidth(0, self.tw_assetDepartments.columnWidth(0) + 20)

    @err_catcher(name=__name__)
    def shotDepartmentDoubleClicked(self, item: QTableWidgetItem) -> None:
        """Handle shot department double-click for editing.
        
        Args:
            item: The table widget item that was double-clicked.
        """
        self.editShotDepartment(item)

    @err_catcher(name=__name__)
    def editShotDepartment(self, item: QTableWidgetItem) -> None:
        """Edit a shot department's properties.
        
        Opens the department edit dialog, retrieves department data, updates the
        UI table with modified information, and persists changes.
        
        Args:
            item: The table widget item representing the department to edit.
        """
        self.saveShotDepartments()
        dep = self.tw_shotDepartments.item(item.row(), 0).data(Qt.UserRole)
        self.dlg_department = PrismWidgets.CreateDepartmentDlg(core=self.core, entity="shot", configData=self.projectData, department=dep, parent=self)
        result = self.dlg_department.exec_()
        if not result:
            return

        department = self.dlg_department.getDepartment()
        name = "%s (%s)" % (department["name"], department["abbreviation"])
        self.tw_shotDepartments.item(item.row(), 0).setText(name)
        self.tw_shotDepartments.item(item.row(), 0).setData(Qt.UserRole, department)
        self.tw_shotDepartments.item(item.row(), 1).setText("\n".join(department["defaultTasks"]))
        self.tw_shotDepartments.resizeRowsToContents()
        self.tw_shotDepartments.resizeColumnsToContents()
        self.tw_shotDepartments.setColumnWidth(0, self.tw_shotDepartments.columnWidth(0) + 20)

    @err_catcher(name=__name__)
    def getAssetDepartments(self) -> List[Dict[str, Any]]:
        """Get list of asset departments from the table widget.
        
        Returns:
            List of department dictionaries containing name, abbreviation, and
            default tasks information.
        """
        deps = []
        rowDict = {}
        for idx in range(self.tw_assetDepartments.rowCount()):
            rowDict[str(self.tw_assetDepartments.visualRow(idx))] = idx

        for idx in range(self.tw_assetDepartments.rowCount()):
            deps.append(self.tw_assetDepartments.item(rowDict[str(idx)], 0).data(Qt.UserRole))

        return deps

    @err_catcher(name=__name__)
    def getShotDepartments(self) -> List[Dict[str, Any]]:
        """Get list of shot departments from the table widget.
        
        Returns:
            List of department dictionaries containing name, abbreviation, and
            default tasks information.
        """
        deps = []
        rowDict = {}
        for idx in range(self.tw_shotDepartments.rowCount()):
            rowDict[str(self.tw_shotDepartments.visualRow(idx))] = idx

        for idx in range(self.tw_shotDepartments.rowCount()):
            deps.append(self.tw_shotDepartments.item(rowDict[str(idx)], 0).data(Qt.UserRole))

        return deps

    @err_catcher(name=__name__)
    def addTaskPresetsAssetClicked(self) -> None:
        """Handle add asset task preset button click.
        
        Opens the create task preset dialog for assets, saves existing presets,
        and refreshes the UI when a new preset is created.
        """
        self.saveAssetTaskPresets()
        dlg_createTaskPreset = PrismWidgets.CreateTaskPresetDlg(
            core=self.core, entity="asset", configData=self.projectData, parent=self
        )

        dlg_createTaskPreset.setWindowTitle("Create Asset Task Preset")
        result = dlg_createTaskPreset.exec_()
        if not result:
            return

        name = dlg_createTaskPreset.getName()
        departments = dlg_createTaskPreset.getDepartments()
        self.core.projects.addTaskPreset("asset", name, departments=departments)
        self.refreshAssetTaskPresets()

    @err_catcher(name=__name__)
    def removeTaskPresetsAssetClicked(self) -> None:
        """Remove selected asset task presets.
        
        Deletes all selected asset task preset items from the list widget.
        """
        items = self.lw_taskPresetsAsset.selectedItems()
        rows = []
        for item in items:
            rows.append(self.lw_taskPresetsAsset.row(item))

        for idx in sorted(rows, reverse=True):
            self.lw_taskPresetsAsset.takeItem(idx)

    @err_catcher(name=__name__)
    def addTaskPresetsShotClicked(self) -> None:
        """Handle add shot task preset button click.
        
        Opens the create task preset dialog for shots, saves existing presets,
        and refreshes the UI when a new preset is created.
        """
        self.saveShotTaskPresets()
        dlg_createTaskPreset = PrismWidgets.CreateTaskPresetDlg(
            core=self.core, entity="shot", configData=self.projectData, parent=self
        )

        dlg_createTaskPreset.setWindowTitle("Create Shot Task Preset")
        result = dlg_createTaskPreset.exec_()
        if not result:
            return

        name = dlg_createTaskPreset.getName()
        departments = dlg_createTaskPreset.getDepartments()
        self.core.projects.addTaskPreset("shot", name, departments=departments)
        self.refreshShotTaskPresets()

    @err_catcher(name=__name__)
    def removeTaskPresetsShotClicked(self) -> None:
        """Remove selected shot task presets.
        
        Deletes all selected shot task preset items from the list widget.
        """
        items = self.lw_taskPresetsShot.selectedItems()
        rows = []
        for item in items:
            rows.append(self.lw_taskPresetsShot.row(item))

        for idx in sorted(rows, reverse=True):
            self.lw_taskPresetsShot.takeItem(idx)

    @err_catcher(name=__name__)
    def refreshAssetTaskPresets(self, presets: Optional[List[Dict[str, Any]]] = None, configData: Optional[Dict[str, Any]] = None) -> None:
        """Refresh asset task presets list widget.
        
        Populates the asset task presets list widget with presets from either
        provided data or project configuration.
        
        Args:
            presets: Optional list of task presets to display. If None, fetches
                from project configuration. Defaults to None.
            configData: Optional project configuration data. Used if presets
                are not provided. Defaults to None.
        """
        if presets is None:
            if configData is None:
                configData = self.projectData

            presets = self.core.projects.getAssetTaskPresets(configData=configData)

        self.lw_taskPresetsAsset.clear()
        for preset in presets:
            name = preset.get("name", "")
            nameItem = QListWidgetItem(name)
            nameItem.setData(Qt.UserRole, preset)
            self.lw_taskPresetsAsset.addItem(nameItem)

    @err_catcher(name=__name__)
    def refreshShotTaskPresets(self, presets: Optional[List[Dict[str, Any]]] = None, configData: Optional[Dict[str, Any]] = None) -> None:
        """Refresh shot task presets list widget.
        
        Populates the shot task presets list widget with presets from either
        provided data or project configuration.
        
        Args:
            presets: Optional list of task presets to display. If None, fetches
                from project configuration. Defaults to None.
            configData: Optional project configuration data. Used if presets
                are not provided. Defaults to None.
        """
        if presets is None:
            if configData is None:
                configData = self.projectData

            presets = self.core.projects.getShotTaskPresets(configData=configData)

        self.lw_taskPresetsShot.clear()
        for preset in presets:
            name = preset.get("name", "")
            nameItem = QListWidgetItem(name)
            nameItem.setData(Qt.UserRole, preset)
            self.lw_taskPresetsShot.addItem(nameItem)

    @err_catcher(name=__name__)
    def assetTaskPresetsRightClicked(self, pos: QPoint) -> None:
        """Display context menu for asset task presets.
        
        Shows options to add, edit, remove, reorder, and restore asset task presets.
        Menu actions are enabled/disabled based on current selections.
        
        Args:
            pos: The position where the right-click occurred.
        """
        rcmenu = QMenu(self)

        exp = QAction("Add...", self)
        exp.triggered.connect(self.addTaskPresetsAssetClicked)
        rcmenu.addAction(exp)

        clipAct = QAction("Edit...", self)
        clipAct.triggered.connect(lambda: self.editAssetTaskPreset(self.lw_taskPresetsAsset.selectedItems()[0]))
        rcmenu.addAction(clipAct)
        if not len(self.lw_taskPresetsAsset.selectedItems()) == 1:
            clipAct.setEnabled(False)

        copAct = QAction("Remove", self)
        copAct.triggered.connect(self.removeTaskPresetsAssetClicked)
        rcmenu.addAction(copAct)
        if not self.lw_taskPresetsAsset.selectedItems():
            copAct.setEnabled(False)

        clipAct = QAction("Move up", self)
        clipAct.triggered.connect(self.moveUpAssetTaskPreset)
        rcmenu.addAction(clipAct)
        if 0 in [self.lw_taskPresetsAsset.row(i) for i in self.lw_taskPresetsAsset.selectedItems()] or not self.lw_taskPresetsAsset.selectedItems():
            clipAct.setEnabled(False)

        clipAct = QAction("Move down", self)
        clipAct.triggered.connect(self.moveDownAssetTaskPreset)
        rcmenu.addAction(clipAct)
        if (self.lw_taskPresetsAsset.count()-1) in [self.lw_taskPresetsAsset.row(i) for i in self.lw_taskPresetsAsset.selectedItems()] or not self.lw_taskPresetsAsset.selectedItems():
            clipAct.setEnabled(False)

        clipAct = QAction("Restore defaults", self)
        clipAct.triggered.connect(self.restoreAssetTaskPresetsTriggered)
        rcmenu.addAction(clipAct)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def shotTaskPresetsRightClicked(self, pos: QPoint) -> None:
        """Display context menu for shot task presets.
        
        Shows options to add, edit, remove, reorder, and restore shot task presets.
        Menu actions are enabled/disabled based on current selections.
        
        Args:
            pos: The position where the right-click occurred.
        """
        rcmenu = QMenu(self)

        exp = QAction("Add...", self)
        exp.triggered.connect(self.addTaskPresetsShotClicked)
        rcmenu.addAction(exp)

        clipAct = QAction("Edit...", self)
        clipAct.triggered.connect(lambda: self.editShotTaskPreset(self.lw_taskPresetsShot.selectedItems()[0]))
        rcmenu.addAction(clipAct)
        if not len(self.lw_taskPresetsShot.selectedItems()) == 1:
            clipAct.setEnabled(False)

        copAct = QAction("Remove", self)
        copAct.triggered.connect(self.removeTaskPresetsShotClicked)
        rcmenu.addAction(copAct)
        if not self.lw_taskPresetsShot.selectedItems():
            copAct.setEnabled(False)

        clipAct = QAction("Move up", self)
        clipAct.triggered.connect(self.moveUpShotTaskPreset)
        rcmenu.addAction(clipAct)
        if 0 in [self.lw_taskPresetsShot.row(i) for i in self.lw_taskPresetsShot.selectedItems()] or not self.lw_taskPresetsShot.selectedItems():
            clipAct.setEnabled(False)

        clipAct = QAction("Move down", self)
        clipAct.triggered.connect(self.moveDownShotTaskPreset)
        rcmenu.addAction(clipAct)
        if (self.lw_taskPresetsShot.count()-1) in [self.lw_taskPresetsShot.row(i) for i in self.lw_taskPresetsShot.selectedItems()] or not self.lw_taskPresetsShot.selectedItems():
            clipAct.setEnabled(False)

        clipAct = QAction("Restore defaults", self)
        clipAct.triggered.connect(self.restoreShotTaskPresetsTriggered)
        rcmenu.addAction(clipAct)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def moveUpAssetTaskPreset(self) -> None:
        """Move selected asset task preset up in the list.
        
        Reorders selected asset task presets one position higher, maintaining their
        relative order and updating the display.
        """
        items = self.lw_taskPresetsAsset.selectedItems()
        rows = []
        for item in items:
            rows.append(self.lw_taskPresetsAsset.row(item))

        presets = self.getAssetTaskPresets()
        for idx in sorted(rows):
            row = presets.pop(idx)
            presets.insert(idx-1, row)

        self.refreshAssetTaskPresets(presets=presets)
        for idx in sorted(rows):
            self.lw_taskPresetsAsset.setCurrentRow(idx-1)

    @err_catcher(name=__name__)
    def moveDownAssetTaskPreset(self) -> None:
        """Move selected asset task preset down in the list.
        
        Reorders selected asset task presets one position lower, maintaining their
        relative order and updating the display.
        """
        items = self.lw_taskPresetsAsset.selectedItems()
        rows = []
        for item in items:
            rows.append(self.lw_taskPresetsAsset.row(item))

        presets = self.getAssetTaskPresets()
        for idx in sorted(rows):
            row = presets.pop(idx)
            presets.insert(idx+1, row)

        self.refreshAssetTaskPresets(presets=presets)
        for idx in sorted(rows):
            self.lw_taskPresetsAsset.setCurrentRow(idx+1)

    @err_catcher(name=__name__)
    def moveUpShotTaskPreset(self) -> None:
        """Move selected shot task preset up in the list.
        
        Reorders selected shot task presets one position higher, maintaining their
        relative order and updating the display.
        """
        items = self.lw_taskPresetsShot.selectedItems()
        rows = []
        for item in items:
            rows.append(self.lw_taskPresetsShot.row(item))

        presets = self.getShotTaskPresets()
        for idx in sorted(rows):
            row = presets.pop(idx)
            presets.insert(idx-1, row)

        self.refreshShotTaskPresets(presets=presets)
        for idx in sorted(rows):
            self.lw_taskPresetsShot.setCurrentRow(idx-1)

    @err_catcher(name=__name__)
    def moveDownShotTaskPreset(self) -> None:
        """Move selected shot task preset down in the list.
        
        Reorders selected shot task presets one position lower, maintaining their
        relative order and updating the display.
        """
        items = self.lw_taskPresetsShot.selectedItems()
        rows = []
        for item in items:
            rows.append(self.lw_taskPresetsShot.row(item))

        presets = self.getShotTaskPresets()
        for idx in sorted(rows):
            row = presets.pop(idx)
            presets.insert(idx+1, row)

        self.refreshShotTaskPresets(presets=presets)
        for idx in sorted(rows):
            self.lw_taskPresetsShot.setCurrentRow(idx+1)

    @err_catcher(name=__name__)
    def restoreAssetTaskPresetsTriggered(self) -> None:
        """Restore asset task presets to project defaults.
        
        Resets the asset task presets list to the default configuration from
        the default project settings.
        """
        configData = self.core.projects.getDefaultProjectSettings()
        self.refreshAssetTaskPresets(configData=configData)

    @err_catcher(name=__name__)
    def restoreShotTaskPresetsTriggered(self) -> None:
        """Restore shot task presets to project defaults.
        
        Resets the shot task presets list to the default configuration from
        the default project settings.
        """
        configData = self.core.projects.getDefaultProjectSettings()
        self.refreshShotTaskPresets(configData=configData)

    @err_catcher(name=__name__)
    def assetTaskPresetsDoubleClicked(self, item: QListWidgetItem) -> None:
        """Handle asset task preset double-click for editing.
        
        Args:
            item: The list widget item that was double-clicked.
        """
        self.editAssetTaskPreset(item)

    @err_catcher(name=__name__)
    def editAssetTaskPreset(self, item: QListWidgetItem) -> None:
        """Edit an asset task preset's properties.
        
        Opens the task preset edit dialog, retrieves preset data, updates the UI
        with modified information, and persists changes.
        
        Args:
            item: The list widget item representing the preset to edit.
        """
        self.saveAssetTaskPresets()
        preset = item.data(Qt.UserRole)
        self.dlg_preset = PrismWidgets.CreateTaskPresetDlg(core=self.core, entity="asset", configData=self.projectData, preset=preset, parent=self)
        result = self.dlg_preset.exec_()
        if not result:
            return

        departments = self.dlg_preset.getDepartments()
        name = self.dlg_preset.getName()
        preset = {
            "name": name,
            "departments": departments
        }
        item.setText(name)
        item.setData(Qt.UserRole, preset)

    @err_catcher(name=__name__)
    def shotTaskPresetDoubleClicked(self, item: QListWidgetItem) -> None:
        """Handle shot task preset double-click for editing.
        
        Args:
            item: The list widget item that was double-clicked.
        """
        self.editShotTaskPreset(item)

    @err_catcher(name=__name__)
    def editShotTaskPreset(self, item: QListWidgetItem) -> None:
        """Edit a shot task preset's properties.
        
        Opens the task preset edit dialog, retrieves preset data, updates the UI
        with modified information, and persists changes.
        
        Args:
            item: The list widget item representing the preset to edit.
        """
        self.saveShotTaskPresets()
        preset = item.data(Qt.UserRole)
        self.dlg_preset = PrismWidgets.CreateTaskPresetDlg(core=self.core, entity="shot", configData=self.projectData, preset=preset, parent=self)
        result = self.dlg_preset.exec_()
        if not result:
            return

        departments = self.dlg_preset.getDepartments()
        name = self.dlg_preset.getName()
        preset = {
            "name": name,
            "departments": departments
        }
        item.setText(name)
        item.setData(Qt.UserRole, preset)

    @err_catcher(name=__name__)
    def getAssetTaskPresets(self) -> List[Dict[str, Any]]:
        """Get list of asset task presets from the list widget.
        
        Returns:
            List of task preset dictionaries containing name and departments information.
        """
        presets = []
        for idx in range(self.lw_taskPresetsAsset.count()):
            presets.append(self.lw_taskPresetsAsset.item(idx).data(Qt.UserRole))

        return presets

    @err_catcher(name=__name__)
    def getShotTaskPresets(self) -> List[Dict[str, Any]]:
        """Get list of shot task presets from the list widget.
        
        Returns:
            List of task preset dictionaries containing name and departments information.
        """
        presets = []
        for idx in range(self.lw_taskPresetsShot.count()):
            presets.append(self.lw_taskPresetsShot.item(idx).data(Qt.UserRole))

        return presets

    @err_catcher(name=__name__)
    def saveAssetTaskPresets(self) -> None:
        """Save asset task presets to project configuration.
        
        Collects all asset task presets from the UI list and saves them to the
        project configuration data.
        """
        deps = self.getAssetTaskPresets()
        self.core.projects.setTaskPresets("asset", deps, configData=self.projectData)

    @err_catcher(name=__name__)
    def saveShotTaskPresets(self) -> None:
        """Save shot task presets to project configuration.
        
        Collects all shot task presets from the UI list and saves them to the
        project configuration data.
        """
        deps = self.getShotTaskPresets()
        self.core.projects.setTaskPresets("shot", deps, configData=self.projectData)

    @err_catcher(name=__name__)
    def refreshHooks(self, reloadHooks: bool = False) -> None:
        """Refresh the hooks list widget.
        
        Clears and repopulates the hooks list with registered hooks. Optionally
        reloads hooks from project files first.
        
        Args:
            reloadHooks: If True, reloads hooks from project before refreshing.
                Defaults to False.
        """
        self.lw_hooks.clear()
        if reloadHooks:
            self.core.callbacks.registerProjectHooks()

        for hook in sorted(self.core.callbacks.registeredHooks, key=lambda x: x.lower()):
            item = QListWidgetItem(hook)
            self.lw_hooks.addItem(item)

    @err_catcher(name=__name__)
    def hooksRightClicked(self, pos: Optional[QPoint] = None) -> None:
        """Display context menu for hooks list.
        
        Shows options to add, delete, open in explorer, and refresh hooks.
        Menu actions are enabled/disabled based on current selections.
        
        Args:
            pos: The position where the right-click occurred. Defaults to None.
        """
        rcmenu = QMenu(self)

        exp = QAction("Add...", self)
        exp.triggered.connect(self.addHookClicked)
        rcmenu.addAction(exp)
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        exp.setIcon(icon)

        copAct = QAction("Delete Selected...", self)
        copAct.triggered.connect(self.removeHookClicked)
        rcmenu.addAction(copAct)
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "delete.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        copAct.setIcon(icon)

        iname = (self.lw_hooks.indexAt(pos)).data()
        if iname:
            clipAct = QAction("Open in explorer", self)
            clipAct.triggered.connect(lambda: self.openHookInExplorer(pos))
            rcmenu.addAction(clipAct)

        clipAct = QAction("Refresh", self)
        clipAct.triggered.connect(lambda: self.refreshHooks(reloadHooks=True))
        rcmenu.addAction(clipAct)
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "refresh.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        clipAct.setIcon(icon)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def hookSelectionChanged(self) -> None:
        """Handle hook selection change in the list.
        
        Loads and displays the content of the selected hook file in the text editor.
        Clears the editor if no valid hook is selected.
        """
        self.te_hook.clear()
        items = self.lw_hooks.selectedItems()
        if len(items) != 1:
            return

        filepath = self.core.callbacks.registeredHooks[items[0].text()][0]["filepath"]
        if not os.path.exists(filepath):
            return

        with open(filepath, "r") as f:
            text = f.read()

        self.te_hook.setPlainText(text)

    @err_catcher(name=__name__)
    def saveHook(self) -> None:
        """Save the currently edited hook file.
        
        Writes the text editor content back to the hook file on disk. Only saves
        if exactly one hook is selected.
        """
        text = self.te_hook.toPlainText()
        items = self.lw_hooks.selectedItems()
        if len(items) != 1:
            return

        filepath = self.core.callbacks.registeredHooks[items[0].text()][0]["filepath"]
        with open(filepath, "w") as f:
            f.write(text)

    @err_catcher(name=__name__)
    def addHookClicked(self) -> None:
        """Handle add hook button click.
        
        Opens a dialog to create a new project hook. Presents available callbacks
        that don't already have hooks, then creates the hook file with template
        content after user selection.
        """
        availableCallbacks = self.core.callbacks.availableCallbacks
        availableHooks = []
        existingHooks = [self.lw_hooks.item(idx).text() for idx in range(self.lw_hooks.count())]
        for availableCallback in availableCallbacks:
            if availableCallback not in existingHooks:
                availableHooks.append(availableCallback)

        availableHooks = sorted(availableHooks, key=lambda x: x.lower())
        dlg_ec = PrismWidgets.CreateItem(
            core=self.core, showType=False, valueRequired=True, validate=True, showTasks=bool(availableHooks), presets=availableHooks
        )

        dlg_ec.setModal(True)
        self.core.parentWindow(dlg_ec, parent=self)
        dlg_ec.e_item.setFocus()
        dlg_ec.setWindowTitle("Create Hook")
        dlg_ec.l_item.setText("Hook Name:")
        dlg_ec.buttonBox.buttons()[0].setText("Create")
        result = dlg_ec.exec_()
        if not result:
            return

        hookName = dlg_ec.e_item.text().strip()
        content = """# def main(*args, **kwargs):
#     print(args)
#     print(kwargs)"""
        self.core.callbacks.createProjectHook(hookName, content=content)
        self.refreshHooks(reloadHooks=True)
        if hookName.endswith(".py"):
            hookName = hookName[:-3]

        fItems = self.lw_hooks.findItems(hookName, Qt.MatchExactly)
        if fItems:
            for item in fItems:
                item.setSelected(True)

    @err_catcher(name=__name__)
    def removeHookClicked(self) -> None:
        """Handle remove hook button click.
        
        Deletes all selected hooks from the project after confirmation. Removes
        the hook files from disk and refreshes the hooks list.
        """
        items = self.lw_hooks.selectedItems()
        if not items:
            self.core.popup("No items selected.")
            return

        msg = "Are you sure you want to delete the following hooks?\n"
        for item in items:
            msg += "\n" + item.text()

        result = self.core.popupQuestion(msg)
        if result != "Yes":
            return

        for item in items:
            cb = item.text()
            if cb not in self.core.callbacks.registeredHooks:
                continue

            path = self.core.callbacks.registeredHooks[cb][0]["filepath"]
            try:
                os.remove(path)
            except:
                self.core.popup("Failed to remove file:\n\n%s\n\nError:\n%s" % (path, str(e)))

        self.refreshHooks(reloadHooks=True)

    @err_catcher(name=__name__)
    def openHookInExplorer(self, pos: QPoint) -> None:
        """Open selected hook file in file explorer.
        
        Locates and opens the file system folder containing the selected hook
        file in the default file browser.
        
        Args:
            pos: Position where context menu was clicked (used to find selected item).
        """
        iname = (self.lw_hooks.indexAt(pos)).data()
        if not iname:
            return

        filepath = self.core.callbacks.registeredHooks[iname][0]["filepath"]
        self.core.openFolder(filepath)

    @err_catcher(name=__name__)
    def validateFolderWidget(self, widget: QLineEdit) -> bool:
        """Validate a folder structure path template.
        
        Validates the path against project folder rules and updates the widget's
        visual style (border and help icon) based on validation result.
        
        Args:
            widget: The line edit widget containing the folder path template.
        
        Returns:
            True if validation passes, error message string otherwise.
        """
        path = widget.text()
        item = widget.helpWidget.item
        result = self.core.projects.validateFolderKey(path, item)
        invalidStyle = "border: 2px solid rgb(200, 10, 10)"

        if result is True:
            widget.setStyleSheet("border: 2px solid transparent")
            widget.helpWidget.setPixmap(self.helpPixmap)
        else:
            widget.setStyleSheet(invalidStyle)
            widget.helpWidget.setPixmap(self.invalidHelpPixmap)

        return result

    @err_catcher(name=__name__)
    def structureItemEntered(self, widget: Any) -> None:
        """Handle mouse enter event for folder structure help widget.
        
        Validates the related folder structure path and updates the help message
        to show validation result or resolved path information.
        
        Args:
            widget: The folder structure help widget being entered.
        """
        result = self.validateFolderWidget(widget.editWidget)
        if result is not True:
            widget.msg = result
            return

        entityType = (
            "shot"
            if widget.key
            in [
                "shots",
                "sequences",
                "shotScenefiles",
                "productFilesShots",
                "renderFilesShots",
                "playblastFilesShots",
            ]
            else "asset"
        )
        if widget.key in ["productFilesAssets", "productFilesShots"]:
            fileType = "product"
        elif widget.key in ["renderFilesShots", "playblastFilesShots"]:
            fileType = "media"
        else:
            fileType = "scene"

        widget.msg = self.getResolvedPath(
            widget.editWidget.text(), entityType=entityType, fileType=fileType
        )

        reqKeys = widget.item.get("requires", [])
        if reqKeys:
            msg = "\n\nThe following keys are required:"
            for key in reqKeys:
                if self.core.isStr(key):
                    msg += "\n@%s@" % key
                else:
                    msg += "\n" + " or ".join(["@%s@" % o for o in key])

            widget.msg += msg

    @err_catcher(name=__name__)
    def getResolvedPath(self, path: str, entityType: str = "asset", fileType: str = "scene") -> str:
        """Resolve folder structure path template with sample data.
        
        Expands path template variables using example data for asset/shot context.
        Useful for showing users what their paths will look like with actual values.
        
        Args:
            path: The folder structure path template with variables (e.g., @project_path@).
            entityType: Type of entity - 'asset' or 'shot'. Defaults to 'asset'.
            fileType: Type of file - 'scene', 'product', or 'media'. Defaults to 'scene'.
        
        Returns:
            Resolved path string with template variables replaced with example values.
        """
        if self.projectData:
            projectPath = self.projectData["globals"]["project_path"]
        else:
            projectPath = os.path.normpath(self.core.projectPath)

        context = {
            "project_path": projectPath,
            "project_name": "myProject",
            "department": "modeling",
            "task": "body",
            "comment": "my-comment",
            "version": "v0001",
            "user": "mmu",
            "product": "charGEO",
            "frame": "1001",
            "aov": "beauty",
            "identifier": "main",
        }

        if entityType == "asset":
            context["asset"] = "alien"
            context["asset_path"] = "character/alien"
        elif entityType == "shot":
            context["sequence"] = "seq01"
            context["shot"] = "0010"

        if fileType == "scene":
            context["extension"] = ".hip"
        elif fileType == "product":
            context["extension"] = ".abc"
        elif fileType == "media":
            context["extension"] = ".exr"

        paths = self.core.projects.resolveStructurePath(path, context)
        if paths:
            return paths[0]
        else:
            return ""

    @err_catcher(name=__name__)
    def resetProjectStructure(self) -> None:
        """Reset all folder structure paths to default values.
        
        Iterates through all folder structure widgets and resets their text to the
        default project structure values from the default project configuration.
        """
        for item in self.folderStructureWidgets:
            widget = item["widget"]
            key = item["key"]
            dftStructure = self.core.projects.getDefaultProjectStructure()
            dft = dftStructure[key]["value"]
            widget.setText(dft)

    @err_catcher(name=__name__)
    def refreshExportPaths(self, configData: Optional[Dict[str, Any]] = None) -> None:
        """Refresh export locations table widget.
        
        Populates the export paths table with location-to-path mappings from
        project configuration.
        
        Args:
            configData: Optional project configuration data. If not provided,
                uses the loaded project data. Defaults to None.
        """
        if configData is None:
            configData = self.projectData

        exportPaths = self.core.paths.getExportProductBasePaths(
            default=False, configData=configData
        )
        self.tw_exportPaths.setRowCount(0)
        for location in exportPaths:
            locationItem = QTableWidgetItem(location)
            pathItem = QTableWidgetItem(exportPaths[location])

            rc = self.tw_exportPaths.rowCount()
            self.tw_exportPaths.insertRow(rc)

            self.tw_exportPaths.setItem(rc, 0, locationItem)
            self.tw_exportPaths.setItem(rc, 1, pathItem)
            self.tw_exportPaths.setRowHeight(rc, 15)

        self.tw_exportPaths.resizeColumnsToContents()

    @err_catcher(name=__name__)
    def refreshRenderPaths(self, configData: Optional[Dict[str, Any]] = None) -> None:
        """Refresh render locations table widget.
        
        Populates the render paths table with location-to-path mappings from
        project configuration.
        
        Args:
            configData: Optional project configuration data. If not provided,
                uses the loaded project data. Defaults to None.
        """
        if configData is None:
            configData = self.projectData
        
        renderPaths = self.core.paths.getRenderProductBasePaths(
            default=False, configData=configData
        )
        self.tw_renderPaths.setRowCount(0)
        for location in renderPaths:
            locationItem = QTableWidgetItem(location)
            pathItem = QTableWidgetItem(renderPaths[location])

            rc = self.tw_renderPaths.rowCount()
            self.tw_renderPaths.insertRow(rc)

            self.tw_renderPaths.setItem(rc, 0, locationItem)
            self.tw_renderPaths.setItem(rc, 1, pathItem)
            self.tw_renderPaths.setRowHeight(rc, 15)

        self.tw_renderPaths.resizeColumnsToContents()

    @err_catcher(name=__name__)
    def addExportPathClicked(self) -> None:
        """Handle add export path button click.
        
        Opens a dialog to add a new export location path. Refreshes the export
        paths table when a new path is successfully added.
        """
        self.dlg_addExportPath = AddProductPathDialog(self.core, "export", self)
        self.dlg_addExportPath.pathAdded.connect(self.refreshExportPaths)
        self.dlg_addExportPath.show()

    @err_catcher(name=__name__)
    def removeExportPathClicked(self) -> None:
        """Handle remove export path button click.
        
        Deletes all selected export location paths from the project configuration
        and refreshes the display. Shows error if no paths are selected.
        """
        selection = self.tw_exportPaths.selectedItems()
        if selection:
            for item in selection:
                if item.column() == 0:
                    self.core.paths.removeExportProductBasePath(
                        item.text(), configData=self.projectData
                    )
            self.refreshExportPaths()
        else:
            self.core.popup("No path selected")

    @err_catcher(name=__name__)
    def addRenderPathClicked(self) -> None:
        """Handle add render path button click.
        
        Opens a dialog to add a new render location path. Refreshes the render
        paths table when a new path is successfully added.
        """
        self.dlg_addRenderPath = AddProductPathDialog(self.core, "render", self)
        self.dlg_addRenderPath.pathAdded.connect(self.refreshRenderPaths)
        self.dlg_addRenderPath.show()

    @err_catcher(name=__name__)
    def removeRenderPathClicked(self) -> None:
        """Handle remove render path button click.
        
        Deletes all selected render location paths from the project configuration
        and refreshes the display. Shows error if no paths are selected.
        """
        selection = self.tw_renderPaths.selectedItems()
        if selection:
            for item in selection:
                if item.column() == 0:
                    self.core.paths.removeRenderProductBasePath(
                        item.text(), configData=self.projectData
                    )
            self.refreshRenderPaths()
        else:
            self.core.popup("No path selected")

    @err_catcher(name=__name__)
    def reload(self) -> None:
        """Reload the project settings dialog.
        
        Restarts Prism settings while maintaining the current tab/settings tab index.
        Preserves the active category so users return to the same view.
        """
        idx = self.tw_settings.currentIndex()
        self.core.prismSettings(restart=True)
        self.core.ps.tw_settings.setCurrentIndex(idx)

    @err_catcher(name=__name__)
    def curPnameEdited(self, text: str) -> None:
        """Handle project name text edit.
        
        Validates the project name input when user edits it.
        
        Args:
            text: The edited project name text.
        """
        self.validate(self.e_curPname)

    @err_catcher(name=__name__)
    def enterEvent(self, event: QEvent) -> None:
        """Handle mouse enter event for the dialog.
        
        Restores the cursor when mouse enters the dialog area. Silently ignores
        any exceptions that may occur during cursor restoration.
        
        Args:
            event: The QEvent object generated when mouse enters the widget.
        """
        try:
            QApplication.restoreOverrideCursor()
        except:
            pass


class AddProductPathDialog(QDialog):
    """Dialog for adding export or render location paths to project.
    
    Allows users to specify a name and path for a new export or render location.
    """

    pathAdded = Signal()

    def __init__(self, core: Any, pathType: str, parent: Optional[QWidget] = None) -> None:
        """Initialize the Add Product Path dialog.
        
        Args:
            core: The Prism core instance.
            pathType: Type of path - either 'export' or 'render'.
            parent: Parent widget for the dialog. Defaults to None.
        """
        QDialog.__init__(self)
        self.core = core
        self.pathType = pathType
        self.parent = parent
        self.setupUi(parent=parent)
        self.connectEvents()

    @err_catcher(name=__name__)
    def setupUi(self, parent: Optional[QWidget] = None) -> None:
        """Set up dialog UI components.
        
        Creates the dialog layout with name, path, and browse button. Sets up
        the dialog window properties and button box.
        
        Args:
            parent: Parent widget for parenting the dialog. Defaults to None.
        """
        self.core.parentWindow(self, parent)
        self.setWindowTitle("Add additional %s location" % self.pathType)
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.lo_name = QGridLayout()
        self.l_name = QLabel("Location Name:")
        self.e_name = QLineEdit()
        self.lo_name.addWidget(self.l_name, 0, 0)
        self.lo_name.addWidget(self.e_name, 0, 1, 1, 2)
        self.lo_main.addLayout(self.lo_name)

        self.l_pathInfo = QLabel("Path:")
        self.l_path = QLabel("")
        self.l_path.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.e_path = QLineEdit()
        self.b_browse = QPushButton("...")
        self.lo_name.addWidget(self.l_pathInfo, 1, 0)
        self.lo_name.addWidget(self.e_path, 1, 1)
        self.lo_name.addWidget(self.b_browse, 1, 2)
        self.b_browse.setContextMenuPolicy(Qt.CustomContextMenu)

        self.lo_main.addStretch()

        self.bb_main = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.bb_main.buttons()[0].setText("Add")
        self.bb_main.accepted.connect(self.addPath)
        self.bb_main.rejected.connect(self.reject)

        self.lo_main.addWidget(self.bb_main)

        self.resize(500 * self.core.uiScaleFactor, 150 * self.core.uiScaleFactor)

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect UI events to their handlers.
        
        Connects text changes, button clicks, and context menu events to
        appropriate slots.
        """
        self.e_name.textChanged.connect(lambda x: self.validate(self.e_name, x))
        self.e_path.textChanged.connect(lambda x: self.validate(self.e_path, x))
        self.b_browse.clicked.connect(self.browse)
        self.b_browse.customContextMenuRequested.connect(
            lambda: self.core.openFolder(self.e_path.text())
        )

    @err_catcher(name=__name__)
    def browse(self) -> None:
        """Browse and select a path for the location.
        
        Opens a folder selection dialog and updates the path field with the
        selected directory.
        """
        windowTitle = "Select %s location" % self.pathType
        selectedPath = QFileDialog.getExistingDirectory(
            self, windowTitle, self.e_path.text()
        )

        if selectedPath:
            self.e_path.setText(self.core.fixPath(selectedPath))

    @err_catcher(name=__name__)
    def validate(self, uiWidget: QLineEdit, origText: Optional[str] = None) -> None:
        """Validate input in a location or path field.
        
        Ensures valid characters are used in name and path fields.
        
        Args:
            uiWidget: The line edit widget to validate.
            origText: Optional original text for comparison. Defaults to None.
        """
        if uiWidget == self.e_name:
            allowChars = ["_", " "]
        else:
            allowChars = ["/", "\\", "_", " ", ":"]

        self.core.validateLineEdit(uiWidget, allowChars=allowChars)

    @err_catcher(name=__name__)
    def addPath(self) -> None:
        """Add the configured path to the project.
        
        Validates input, adds the path to project configuration using the core
        API, and emits pathAdded signal before closing the dialog.
        """
        location = self.e_name.text()
        path = self.e_path.text()

        if not location:
            self.core.popup("No location specified")
            return

        if not path:
            self.core.popup("No path specified")
            return

        if self.pathType == "export":
            self.core.paths.addExportProductBasePath(
                location, path, configData=self.parent.projectData
            )
        else:
            self.core.paths.addRenderProductBasePath(
                location, path, configData=self.parent.projectData
            )

        self.pathAdded.emit()
        self.close()


class HelpLabel(QLabel):
    """Custom label widget for help text display in folder structure.
    
    Emits signals on enter events and displays tooltips on mouse movement.
    """

    signalEntered = Signal(object)

    def __init__(self, parent: Any) -> None:
        """Initialize the help label.
        
        Args:
            parent: The parent widget.
        """
        super(HelpLabel, self).__init__()
        self.parent = parent

    def enterEvent(self, event: QEvent) -> None:
        """Handle mouse enter event.
        
        Emits the signalEntered signal when mouse enters the label area.
        
        Args:
            event: The QEvent object generated when mouse enters the label.
        """
        self.signalEntered.emit(self)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move event.
        
        Displays tooltip with help message at cursor position on mouse movement.
        
        Args:
            event: The QMouseEvent object generated by mouse movement.
        """
        QToolTip.showText(QCursor.pos(), self.msg)


class EnvironmentWidget(QDialog):
    """Dialog displaying the current environment variables.
    
    Shows all system environment variables in a read-only table format.
    """
    
    def __init__(self, parent: Any) -> None:
        """Initialize the environment widget dialog.
        
        Args:
            parent: The parent ProjectSettings widget.
        """
        super(EnvironmentWidget, self).__init__()
        self.parent = parent
        self.core = self.parent.core
        self.core.parentWindow(self, parent=self.parent)
        self.setupUi()
        self.refreshEnvironment()

    def sizeHint(self) -> QSize:
        """Return recommended size for the dialog.
        
        Returns:
            QSize with dimensions 1000x700.
        """
        return QSize(1000, 700)

    def setupUi(self) -> None:
        """Set up the dialog UI components.
        
        Creates a table widget with two columns: Variable and Value.
        Configures scrolling and styling for the table.
        """
        self.setWindowTitle("Current Environment")
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.tw_environment = QTableWidget()
        self.tw_environment.setColumnCount(2)
        self.tw_environment.setHorizontalHeaderLabels(["Variable", "Value"])
        self.tw_environment.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tw_environment.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tw_environment.horizontalHeader().setStretchLastSection(True)
        self.tw_environment.verticalHeader().setVisible(False)
        self.tw_environment.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.lo_main.addWidget(self.tw_environment)

    def refreshEnvironment(self) -> None:
        """Populate the table with current environment variables.
        
        Reads system environment variables and displays them in sorted order
        in the table widget.
        """
        self.tw_environment.setRowCount(0)
        for idx, key in enumerate(sorted(os.environ)):
            self.tw_environment.insertRow(idx)
            item = QTableWidgetItem(key)
            self.tw_environment.setItem(idx, 0, item)
            item = QTableWidgetItem(os.environ[key])
            self.tw_environment.setItem(idx, 1, item)

        self.tw_environment.resizeColumnsToContents()


class ExpressionWindow(QDialog):
    """Dialog for editing dynamic path expressions in folder structures.
    
    Allows users to write Python expressions that generate folder paths with
    access to context variables like project path, department, task, etc.
    """
    
    def __init__(self, parent: Any) -> None:
        """Initialize the expression editor dialog.
        
        Args:
            parent: The parent ProjectSettings widget.
        """
        super(ExpressionWindow, self).__init__()
        self.parent = parent
        self.core = self.parent.core
        self.core.parentWindow(self, parent=self.parent)
        self.setupUi()

    def sizeHint(self) -> QSize:
        """Return recommended size for the dialog.
        
        Returns:
            QSize with dimensions 800x500.
        """
        return QSize(800, 500)

    def setupUi(self) -> None:
        """Set up the expression editor UI components.
        
        Creates a text editor with proper tab width and an OK/Cancel button box.
        """
        self.setWindowTitle("Edit Expression")
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.te_expression = QTextEdit()
        tabStop = 4
        metrics = QFontMetrics(self.te_expression.font())
        self.te_expression.setTabStopWidth(tabStop * metrics.width(' '))

        self.bb_main = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.bb_main.accepted.connect(self.onAcceptClicked)
        self.bb_main.rejected.connect(self.reject)

        self.lo_main.addWidget(self.te_expression)
        self.lo_main.addWidget(self.bb_main)

    def onAcceptClicked(self) -> None:
        """Handle OK button click.
        
        Validates the expression before accepting. If valid, closes the dialog
        with acceptance. If invalid, shows error message to the user.
        """
        result = self.core.projects.validateExpression(self.te_expression.toPlainText())
        if result and result["valid"]:
            self.accept()
        else:
            msg = "Invalid expression."
            if result and result.get("error"):
                msg += "\n\n%s" % result["error"]

            self.core.popup(msg)


class SceneBuildingAppWidget(QGroupBox):
    """A collapsible group box representing one DCC application's scene building steps.

    Contains a QTreeWidget listing the ordered build steps and a QToolButton
    that opens a menu of available steps to add.

    Columns:
        0 – Step name
        1 – Description
        2 – "Settings" button (set via setItemWidget)
    """

    def __init__(self, origin, appName: str, iconPath: Optional[str] = None, parent: Optional[QWidget] = None) -> None:
        """Initialize the app widget.

        Args:
            origin: The originating instance.
            appName: Display name shown as the group box title.
            iconPath: Optional path to a PNG icon shown beside the title.
                Defaults to the Prism configure.png placeholder.
            parent: Optional parent widget.
        """
        super(SceneBuildingAppWidget, self).__init__("", parent)
        self.appName = appName
        self.core = origin
        self.iconPath = iconPath
        self._setupUi()

    def _setupUi(self) -> None:
        """Build the internal layout: icon+title row, then tree widget + add button."""
        self.setStyleSheet("QGroupBox { border: none; }")
        lo_outer = QVBoxLayout(self)
        lo_outer.setContentsMargins(0, 8, 6, 0)

        # --- Title row (icon + bold label) ---
        lo_title = QHBoxLayout()
        lo_title.setContentsMargins(0, 0, 0, 4)
        lo_title.setSpacing(6)

        if self.iconPath:
            self.l_titleIcon = QLabel()
            icon = QIcon(self.iconPath)
            self.l_titleIcon.setPixmap(icon.pixmap(16, 16))
            self.l_titleIcon.setScaledContents(False)

        self.l_titleText = QLabel(self.appName)
        font = self.l_titleText.font()
        font.setBold(True)
        self.l_titleText.setFont(font)

        if self.iconPath:
            lo_title.addWidget(self.l_titleIcon)

        lo_title.addWidget(self.l_titleText)
        lo_title.addStretch()
        lo_outer.addLayout(lo_title)

        # --- Content row (tree + add button) ---
        lo_content = QHBoxLayout()
        lo_content.setContentsMargins(0, 0, 0, 0)

        # --- Tree widget ---
        self.tw_steps = QTreeWidget()
        self.tw_steps.setColumnCount(4)
        self.tw_steps.setHeaderLabels(["", "Step", "Description", ""])
        self.tw_steps.header().setSectionResizeMode(0, QHeaderView.Fixed)
        self.tw_steps.header().resizeSection(0, 28)
        self.tw_steps.header().setSectionResizeMode(1, QHeaderView.Interactive)
        self.tw_steps.header().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tw_steps.header().setSectionResizeMode(3, QHeaderView.Fixed)
        self.tw_steps.header().resizeSection(3, 110)
        self.tw_steps.setDragDropMode(QAbstractItemView.InternalMove)
        self.tw_steps.setDefaultDropAction(Qt.MoveAction)
        self.tw_steps.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tw_steps.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tw_steps.setRootIsDecorated(False)
        self.tw_steps.setMinimumHeight(120)
        self.tw_steps.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tw_steps.customContextMenuRequested.connect(self._onContextMenu)
        self.tw_steps.itemDoubleClicked.connect(self._onItemDoubleClicked)
        self.tw_steps.installEventFilter(self)

        lo_content.addWidget(self.tw_steps)

        # --- Add button (right side, top-aligned) ---
        lo_btn = QVBoxLayout()
        lo_btn.setContentsMargins(0, 0, 0, 0)

        self.tb_add = QToolButton()
        self.tb_add.setArrowType(Qt.DownArrow)
        self.tb_add.setToolTip("Add scene building step")
        self.tb_add.setFixedWidth(28)
        self.tb_add.clicked.connect(self.showAddMenu)

        lo_btn.addWidget(self.tb_add)
        lo_btn.addStretch()
        lo_content.addLayout(lo_btn)
        lo_outer.addLayout(lo_content)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Delete selected steps when Delete key is pressed in the tree.

        Args:
            obj: The object the event was sent to.
            event: The event to filter.

        Returns:
            True if the event was consumed, otherwise defers to super.
        """
        if obj is self.tw_steps and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
                self._removeSelectedSteps()
                return True
        return super(SceneBuildingAppWidget, self).eventFilter(obj, event)

    def _onContextMenu(self, pos: QPoint) -> None:
        """Show context menu for the steps tree.

        Args:
            pos: Position of the right-click within the tree widget.
        """
        item = self.tw_steps.itemAt(pos)
        selectedItems = self.tw_steps.selectedItems()
        idx = self.tw_steps.indexOfTopLevelItem(item) if item else -1
        count = self.tw_steps.topLevelItemCount()

        menu = QMenu(self.tw_steps)

        # Add submenu
        addMenu = self.getAddMenu()
        addMenu.setTitle("Add")
        menu.addMenu(addMenu)

        menu.addSeparator()

        actRemove = QAction("Remove", self)
        actRemove.triggered.connect(self._removeSelectedSteps)
        actRemove.setEnabled(bool(selectedItems))
        menu.addAction(actRemove)

        menu.addSeparator()

        actUp = QAction("Move Up", self)
        actUp.triggered.connect(self._moveStepUp)
        actUp.setEnabled(len(selectedItems) == 1 and idx > 0)
        menu.addAction(actUp)

        actDown = QAction("Move Down", self)
        actDown.triggered.connect(self._moveStepDown)
        actDown.setEnabled(len(selectedItems) == 1 and 0 <= idx < count - 1)
        menu.addAction(actDown)

        menu.exec_(QCursor.pos())

    def _removeSelectedSteps(self) -> None:
        """Remove all currently selected steps from the tree."""
        for item in self.tw_steps.selectedItems():
            idx = self.tw_steps.indexOfTopLevelItem(item)
            if idx >= 0:
                self.tw_steps.takeTopLevelItem(idx)

    def _moveStepUp(self) -> None:
        """Move the selected step one position up."""
        selectedItems = self.tw_steps.selectedItems()
        if len(selectedItems) != 1:
            return
        item = selectedItems[0]
        idx = self.tw_steps.indexOfTopLevelItem(item)
        if idx <= 0:
            return
        self._moveItem(item, idx, idx - 1)

    def _moveStepDown(self) -> None:
        """Move the selected step one position down."""
        selectedItems = self.tw_steps.selectedItems()
        if len(selectedItems) != 1:
            return
        item = selectedItems[0]
        idx = self.tw_steps.indexOfTopLevelItem(item)
        if idx < 0 or idx >= self.tw_steps.topLevelItemCount() - 1:
            return
        self._moveItem(item, idx, idx + 1)

    def _moveItem(self, item: QTreeWidgetItem, fromIdx: int, toIdx: int) -> None:
        """Reinsert item from fromIdx to toIdx, restoring its Settings button.

        Args:
            item: The tree item to move.
            fromIdx: Current top-level index.
            toIdx: Target top-level index.
        """
        data = item.data(0, Qt.UserRole)
        self.tw_steps.takeTopLevelItem(fromIdx)
        self.tw_steps.insertTopLevelItem(toIdx, item)
        item.setData(0, Qt.UserRole, data)
        self._setStepWidget(item)
        self.tw_steps.setCurrentItem(item)

    def showAddMenu(self) -> None:
        """Show the add menu. Rebuilds the menu each time to reflect current available steps."""
        menu = self.getAddMenu()
        menu.exec_(QCursor.pos())

    def getAddMenu(self) -> QMenu:
        """Rebuild the drop-down menu on the add button from availableSteps."""
        menu = QMenu(self.tb_add)
        availableSteps = self.core.entities.getAvailableSceneBuildingSteps(self.appName)
        if availableSteps:
            for step in availableSteps:
                name = step.get("label", "")
                if not name:
                    continue
                action = QAction(name, self)
                action.triggered.connect(lambda checked=False, s=step: self.addSteps([s]))
                menu.addAction(action)
        else:
            placeholder = QAction("(no steps available)", self)
            placeholder.setEnabled(False)
            menu.addAction(placeholder)

        return menu

    def _setStepWidget(self, item: QTreeWidgetItem) -> None:
        """Attach the Settings button widget to column 2 of a step item.

        Args:
            item: The tree item to attach the button to.
        """
        btn = QToolButton()
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "prismSettings.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        btn.setIcon(icon)
        btn.setText("Edit Settings...")
        btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        btn.setToolTip("Edit step settings")
        btn.setFixedHeight(22)
        btn.clicked.connect(lambda checked=False, i=item: self._openStepSettings(i))
        self.tw_steps.setItemWidget(item, 3, btn)

    def addSteps(self, stepsData: List[Dict[str, Any]]) -> None:
        """Add multiple steps to the tree widget.

        Args:
            stepsData: List of dicts with at minimum ``name``. Optionally ``description``.
                All keys are stored as item data for later retrieval.
        """
        for stepData in stepsData:
            self.addStep(stepData)

        # resize columns to fit new content, but keep description column wide enough
        self.tw_steps.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tw_steps.header().setSectionResizeMode(2, QHeaderView.Stretch)

    def addStep(self, stepData: Dict[str, Any]) -> QTreeWidgetItem:
        """Add a step to the tree widget.

        Args:
            stepData: Dict with at minimum ``name``. Optionally ``description``.
                All keys are stored as item data for later retrieval.

        Returns:
            The newly created QTreeWidgetItem.
        """
        name = stepData.get("label", "")
        description = stepData.get("description", "")
        enabled = stepData.get("enabled", True)

        item = QTreeWidgetItem(["", name, description, ""])
        item.setData(0, Qt.UserRole, dict(stepData))
        item.setFlags(item.flags() | Qt.ItemIsDragEnabled | Qt.ItemIsUserCheckable)
        item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled)
        item.setCheckState(0, Qt.Checked if enabled else Qt.Unchecked)
        self.tw_steps.addTopLevelItem(item)
        self._setStepWidget(item)
        return item

    def getSteps(self) -> List[Dict[str, Any]]:
        """Return the ordered list of step data dicts as currently shown in the tree.

        Returns:
            List of step data dicts in display order.
        """
        steps = []
        for idx in range(self.tw_steps.topLevelItemCount()):
            item = self.tw_steps.topLevelItem(idx)
            data = dict(item.data(0, Qt.UserRole) or {})
            data["enabled"] = item.checkState(0) == Qt.Checked
            steps.append(data)
        return steps

    def _onItemDoubleClicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Open step settings on double-click.

        Args:
            item: The clicked tree item.
            column: Column index that was clicked.
        """
        self._openStepSettings(item)

    def _openStepSettings(self, item: QTreeWidgetItem) -> None:
        """Show the settings dialog for a step item.

        Args:
            item: The tree item whose settings should be displayed.
        """
        data = item.data(0, Qt.UserRole) or {}
        dlg = SceneBuildingStepSettingsDlg(self, data, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            updated = dlg.getSettings()
            item.setData(0, Qt.UserRole, updated)
            item.setText(1, updated.get("label", item.text(1)))
            item.setText(2, updated.get("description", item.text(2)))


class SceneBuildingStepSettingsDlg(QDialog):
    """Settings dialog for a scene building step.

    Shows:
    - A QTextEdit for the step description.
    - A DefaultSettingItem defining for which tasks the step is active.
    - Dynamic widgets for each entry in stepData["settings"].
    """

    def __init__(self, origin, stepData: Dict[str, Any], parent: Optional[QWidget] = None) -> None:
        """Initialize the settings dialog.

        Args:
            origin: The origin widget or object containing the core reference.
            stepData: Current settings dict for the step.
            parent: Optional parent widget (SceneBuildingAppWidget).
        """
        super(SceneBuildingStepSettingsDlg, self).__init__(parent)
        self.core = origin.core
        self.stepData = dict(stepData)
        self._settingWidgets: List[Tuple[Dict, QWidget]] = []
        self._setupUi()

    def _setupUi(self) -> None:
        """Build the settings form UI."""
        self.setWindowTitle("Step Settings – %s" % self.stepData.get("label", ""))
        self.setMinimumWidth(480)

        lo_main = QVBoxLayout(self)

        # --- Description ---
        lo_main.addWidget(QLabel("Description:"))
        self.te_description = QTextEdit()
        self.te_description.setPlainText(self.stepData.get("description", ""))
        self.te_description.setFixedHeight(80)
        lo_main.addWidget(self.te_description)

        # --- Active tasks (DefaultSettingItem) ---
        origin = self.parent()
        if origin is not None and hasattr(origin, "core"):
            self.w_dftTasks = ProjectWidgets.DefaultSettingItem(
                origin,
                name="Active tasks",
                dftTasks=self.stepData.get("dftTasks"),
            )
            lo_main.addWidget(self.w_dftTasks)
        else:
            self.w_dftTasks = None

        # --- Additional settings ---
        additionalSettings = self.stepData.get("settings") or []
        if additionalSettings:
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setFrameShadow(QFrame.Sunken)
            lo_main.addWidget(sep)

            lo_main.addWidget(QLabel("Settings:"))
            form = QFormLayout()
            form.setLabelAlignment(Qt.AlignRight)

            for setting in additionalSettings:
                stype = setting.get("type", "lineedit")
                label = setting.get("label", setting.get("name", ""))
                default = setting.get("value")

                if stype == "combobox":
                    widget = QComboBox()
                    items = setting.get("items") or []
                    widget.addItems([str(i) for i in items])
                    if default is not None:
                        idx = widget.findText(str(default))
                        if idx >= 0:
                            widget.setCurrentIndex(idx)
                elif stype == "checkbox":
                    widget = QCheckBox()
                    if isinstance(default, bool):
                        widget.setChecked(default)
                    elif isinstance(default, str):
                        widget.setChecked(default.lower() in ("true", "1", "yes"))
                    else:
                        widget.setChecked(bool(default))
                elif stype == "code":
                    widget = QTextEdit()
                    widget.setPlainText(str(default) if default is not None else "")
                    widget.setMinimumHeight(180)
                    self.core.pythonHighlighter(widget.document())
                else:  # lineedit
                    widget = QLineEdit(str(default) if default is not None else "")

                self._settingWidgets.append((setting, widget))
                form.addRow(label + ":", widget)

            lo_main.addLayout(form)

        lo_main.addStretch()

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lo_main.addWidget(bb)

    def getSettings(self) -> Dict[str, Any]:
        """Return the updated step data dict.

        Returns:
            Full step data dict with description, dftTasks, and settings updated.
        """
        result = dict(self.stepData)
        result["description"] = self.te_description.toPlainText()

        if self.w_dftTasks is not None:
            result["dftTasks"] = self.w_dftTasks.dftTasks()

        if self._settingWidgets:
            updatedSettings = []
            for setting, widget in self._settingWidgets:
                updated = dict(setting)
                stype = setting.get("type", "lineedit")
                if stype == "combobox":
                    updated["value"] = widget.currentText()
                elif stype == "checkbox":
                    updated["value"] = widget.isChecked()
                elif stype == "code":
                    updated["value"] = widget.toPlainText()
                else:
                    updated["value"] = widget.text()
                updatedSettings.append(updated)
            result["settings"] = updatedSettings

        return result


if __name__ == "__main__":
    qapp = QApplication(sys.argv)
    from UserInterfacesPrism import qdarkstyle

    qapp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))
    appIcon = QIcon(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "UserInterfacesPrism",
            "p_tray.png",
        )
    )
    qapp.setWindowIcon(appIcon)

    pc = PrismCore.PrismCore(prismArgs=["loadProject", "noProjectBrowser"])

    pc.prismSettings()
    qapp.exec_()
