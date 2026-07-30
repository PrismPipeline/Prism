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

from typing import Any, Optional, Dict, List

import os
import sys

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


class RenderSettingsClass(object):
    """State Manager node for managing render settings.
    
    Provides functionality to save, load, and apply render settings as presets
    or custom configurations. Supports application-specific render settings for
    Houdini, Maya, and other DCCs.
    
    Attributes:
        className (str): Node type identifier ("Render Settings")
        listType (str): State list type ("Export")
        core (Any): Reference to PrismCore instance
        state (Any): Reference to QTreeWidgetItem representing this state
        stateManager (Any): Reference to StateManager instance
    """
    className = "Render Settings"
    listType = "Export"

    @classmethod
    def isActive(cls, core: Any) -> bool:
        """Check if this state type is available in the current application.
        
        Args:
            core (Any): PrismCore instance
        
        Returns:
            bool: True if application is Houdini or Maya, False otherwise
        """
        return core.appPlugin.pluginName in ["Houdini", "Maya"]

    @classmethod
    def getPresets(cls, core: Any) -> Dict[str, str]:
        """Get all available render settings presets for current application.
        
        Scans the presets directory for saved render settings files specific
        to the current DCC application.
        
        Args:
            core (Any): PrismCore instance
        
        Returns:
            Dict[str, str]: Dictionary mapping preset names to file paths
        """
        presets = {}
        appName = core.appPlugin.pluginName
        presetPath = os.path.join(
            core.projects.getPresetFolder(), "RenderSettings", appName
        )
        if not os.path.exists(presetPath):
            return presets

        for pFile in os.listdir(presetPath):
            base, ext = os.path.splitext(pFile)
            if ext != core.configs.getProjectExtension():
                continue

            presets[base] = os.path.join(presetPath, pFile)

        return presets

    @classmethod
    def applyPreset(cls, core: Any, presetPath: str, **kwargs: Any) -> None:
        """Apply a render settings preset to the current scene.
        
        Loads render settings from a preset file and applies them to the
        current scene using application-specific methods.
        
        Args:
            core (Any): PrismCore instance
            presetPath (str): Path to preset file
            **kwargs (Any): Additional arguments passed to application plugin
        """
        preset = core.readYaml(presetPath)
        if "renderSettings" not in preset:
            return

        preset = preset["renderSettings"]

        getattr(
            core.appPlugin, "sm_renderSettings_setCurrentSettings", lambda x, y: None
        )(core, preset, **kwargs)

    @err_catcher(name=__name__)
    def setup(
        self, 
        state: Any, 
        core: Any, 
        stateManager: Any, 
        node: Optional[Any] = None, 
        stateData: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize the render settings state.
        
        Sets up the render settings node with core references, UI components,
        and loads saved state data if provided.
        
        Args:
            state (Any): QTreeWidgetItem representing this state in the state tree
            core (Any): PrismCore instance for accessing Prism functionality
            stateManager (Any): StateManager instance managing this state
            node (Any, optional): Scene node associated with this state. Defaults to None.
            stateData (Dict[str, Any], optional): Saved state configuration to restore.
                Defaults to None.
        """
        self.state = state
        self.core = core
        self.stateManager = stateManager

        self.cb_addSetting.lineEdit().setPlaceholderText("Select setting to add")
        self.cb_addSetting.wheelEvent = lambda event: None
        self.cb_presetOption.wheelEvent = lambda event: None

        getattr(self.core.appPlugin, "sm_renderSettings_startup", lambda x: None)(self)
        if state:
            self.e_name.setText("Render Settings")
            self.nameChanged("Render Settings")
        
        self.l_name.setVisible(False)
        self.e_name.setVisible(False)
        self.editChanged(self.chb_editSettings.isChecked())
        self.connectEvents()

        if stateData is not None:
            self.loadData(stateData)

    @err_catcher(name=__name__)
    def loadData(self, data: Dict[str, Any]) -> None:
        """Load saved state settings from data dictionary.
        
        Restores render settings including state name, preset option,
        edit mode, and render settings configuration.
        
        Args:
            data (Dict[str, Any]): Dictionary containing saved state settings with keys:
                - statename (str, optional): Name of the state
                - presetoption (str, optional): Selected preset name
                - editsettings (bool, optional): Whether in custom edit mode
                - rendersettings (Dict, optional): Render settings data
                - stateenabled (int, optional): Check state value
        """
        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "presetoption" in data:
            self.updateUi()
            idx = self.cb_presetOption.findText(data["presetoption"])
            if idx != -1:
                self.cb_presetOption.setCurrentIndex(idx)
        if "editsettings" in data:
            if type(data["editsettings"]) == bool:
                self.chb_editSettings.setChecked(data["editsettings"])

        if "rendersettings" in data:
            settings = self.core.writeYaml(data=data["rendersettings"])
            self.te_settings.setPlainText(settings)
        if "stateenabled" in data:
            if type(data["stateenabled"]) == int:
                self.state.setCheckState(
                    0, Qt.CheckState(data["stateenabled"]),
                )

        getattr(self.core.appPlugin, "sm_renderSettings_loadData", lambda x, y: None)(
            self, data
        )
        self.core.callback("onStateSettingsLoaded", self, data)

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect UI widget signals to handler methods.
        
        Sets up all signal connections for UI controls including preset selection,
        buttons, checkboxes, and text fields.
        """
        self.cb_presetOption.activated.connect(self.stateManager.saveStatesToScene)
        self.b_loadCurrent.clicked.connect(self.loadCurrent)
        self.b_resetSettings.clicked.connect(self.resetSettings)
        self.b_loadPreset.clicked.connect(self.showPresets)
        self.b_savePreset.clicked.connect(self.savePreset)
        self.chb_editSettings.stateChanged.connect(self.editChanged)
        self.cb_addSetting.activated.connect(self.settingActivated)
        self.cb_addSetting.lineEdit().editingFinished.connect(self.settingActivated)
        self.te_settings.origFocusOutEvent = self.te_settings.focusOutEvent
        self.te_settings.focusOutEvent = self.focusOut
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        if not self.stateManager.standalone:
            self.b_applySettings.clicked.connect(self.applySettings)

    @err_catcher(name=__name__)
    def nameChanged(self, text: str) -> None:
        """Handle state name changes.
        
        Updates the tree widget item text when the state name is changed,
        appending " - disabled" suffix if state is disabled.
        
        Args:
            text (str): New state name
        """
        sText = text

        if self.state.text(0).endswith(" - disabled"):
            sText += " - disabled"

        self.state.setText(0, sText)

    @err_catcher(name=__name__)
    def editChanged(self, state: int) -> None:
        """Handle edit settings checkbox state changes.
        
        Shows or hides UI elements based on whether custom edit mode
        is enabled or preset selection mode is active.
        
        Args:
            state (int): Checkbox state (Qt.Checked or Qt.Unchecked)
        """
        self.w_presetOption.setVisible(not state)
        self.w_loadCurrent.setVisible(state)
        self.w_addSetting.setVisible(state)
        self.gb_settings.setVisible(state)
        self.te_settings.setPlainText("")
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def updateUi(self) -> None:
        """Update the UI state and refresh preset list.
        
        Repopulates the preset dropdown with current presets, maintaining
        the current selection if it still exists. Updates available settings
        in the add setting dropdown if in edit mode.
        """
        curPreset = self.cb_presetOption.currentText()
        self.cb_presetOption.clear()
        self.cb_presetOption.addItems(
            sorted(self.getPresets(self.core).keys(), key=lambda x: x.lower())
        )
        idx = self.cb_presetOption.findText(curPreset)
        if idx != -1:
            self.cb_presetOption.setCurrentIndex(idx)
        else:
            self.stateManager.saveStatesToScene()
        if self.state:
            self.nameChanged(self.e_name.text())

        if not self.cb_addSetting.isHidden():
            settings = getattr(
                self.core.appPlugin,
                "sm_renderSettings_getCurrentSettings",
                lambda x, y: {},
            )(self, asString=False)
            self.cb_addSetting.clear()
            settingNames = [list(x.keys())[0] for x in settings]
            settingNames.insert(0, "")
            self.cb_addSetting.addItems(settingNames)

    @err_catcher(name=__name__)
    def focusOut(self, event: Any) -> None:
        """Handle focus out event for settings text field.
        
        Saves state to scene when focus leaves the settings text field.
        
        Args:
            event (Any): Focus out event
        """
        self.stateManager.saveStatesToScene()
        self.te_settings.origFocusOutEvent(event)

    @err_catcher(name=__name__)
    def loadCurrent(self) -> None:
        """Load current render settings from the scene.
        
        Queries the application plugin for current render settings and
        displays them in the settings text field.
        """
        settings = getattr(
            self.core.appPlugin, "sm_renderSettings_getCurrentSettings", lambda x: {}
        )(self)
        self.te_settings.setPlainText(settings)
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def resetSettings(self) -> None:
        """Reset render settings to application defaults.
        
        Calls the application plugin to apply default render settings.
        """
        getattr(
            self.core.appPlugin, "sm_renderSettings_applyDefaultSettings", lambda x: {}
        )(self)

    @err_catcher(name=__name__)
    def settingActivated(self, text: Optional[str] = None) -> None:
        """Handle adding a render setting to the settings text.
        
        When a setting is selected from the dropdown, appends its current
        value to the settings text field in YAML format.
        
        Args:
            text (str, optional): Setting name. Defaults to None (uses dropdown value).
        """
        text = self.cb_addSetting.currentText()
        settings = getattr(
            self.core.appPlugin, "sm_renderSettings_getCurrentSettings", lambda x, y: {}
        )(self, asString=False)
        setting = [x for x in settings if list(x.keys())[0] == text]
        if setting:
            settingsStr = self.core.writeYaml(data=setting)
            curStr = self.te_settings.toPlainText()
            self.te_settings.setPlainText(curStr + settingsStr)
            self.cb_addSetting.setCurrentIndex(0)

    @err_catcher(name=__name__)
    def showPresets(self) -> None:
        """Display a context menu of available render settings presets.
        
        Shows a menu listing all saved presets for the current application,
        allowing the user to select one to load.
        """
        presets = self.getPresets(self.core)
        if not presets:
            self.core.popup("No presets found.")
            return

        pmenu = QMenu(self.stateManager)

        for preset in sorted(presets):
            add = QAction(preset, self)
            add.triggered.connect(lambda x=None, p=preset: self.loadPreset(presets[p]))
            pmenu.addAction(add)

        pmenu.exec_(QCursor().pos())

    @err_catcher(name=__name__)
    def loadPreset(self, presetPath: str) -> None:
        """Load render settings from a preset file.
        
        Reads a preset file and displays its render settings in the
        settings text field.
        
        Args:
            presetPath (str): Path to preset file to load
        """
        preset = self.core.readYaml(presetPath)
        if "renderSettings" not in preset:
            return

        settings = self.core.writeYaml(data=preset["renderSettings"])
        self.te_settings.setPlainText(settings)
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def savePreset(self) -> None:
        """Save current render settings as a new preset.
        
        Prompts the user for a preset name and saves the current render
        settings to a preset file in the project's preset folder.
        """
        result = QInputDialog.getText(self, "Save preset", "Presetname:")
        if not result[1]:
            return

        appName = self.core.appPlugin.pluginName
        presetPath = os.path.join(
            self.core.projects.getPresetFolder(),
            "RenderSettings",
            appName,
            "%s%s" % (result[0], self.core.configs.getProjectExtension()),
        )

        if self.chb_editSettings.isChecked():
            presetStr = self.te_settings.toPlainText()
        else:
            presetStr = getattr(
                self.core.appPlugin,
                "sm_renderSettings_getCurrentSettings",
                lambda x: {},
            )(self)

        preset = self.core.readYaml(data=presetStr)
        if preset is None:
            self.core.popup("Invalid preset syntax.")
        else:
            self.core.writeYaml(presetPath, {"renderSettings": preset})

        self.updateUi()

    @err_catcher(name=__name__)
    def applySettings(self, settings: Optional[str] = None) -> None:
        """Apply render settings to the current scene.
        
        If in edit mode, applies custom settings from the text field.
        Otherwise, applies the selected preset.
        
        Args:
            settings (str, optional): Custom settings string. If None,
                uses settings from text field or selected preset. Defaults to None.
        """
        if self.chb_editSettings.isChecked():
            if not settings:
                settings = self.te_settings.toPlainText()
            preset = self.core.readYaml(data=settings)
            getattr(
                self.core.appPlugin,
                "sm_renderSettings_setCurrentSettings",
                lambda x, y: None,
            )(self, preset, state=self)
        else:
            presets = self.getPresets(self.core)
            selPreset = self.cb_presetOption.currentText()
            if selPreset not in presets:
                return

            self.applyPreset(self.core, presets[selPreset], state=self)

    @err_catcher(name=__name__)
    def preExecuteState(self) -> List[Any]:
        """Check for warnings before execution.
        
        Validates that render settings are specified if in edit mode.
        Collects application-specific warnings.
        
        Returns:
            List[Any]: List containing [state_name, [warnings]]
        """
        warnings = []

        if self.chb_editSettings.isChecked() and not self.te_settings.toPlainText():
            warnings.append(["No rendersettings are specified.", "", 2])

        warnings += getattr(
            self.core.appPlugin, "sm_renderSettings_preExecute", lambda x: []
        )(self)

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def executeState(self, parent: Any, useVersion: str = "next") -> List[str]:
        """Execute the render settings state.
        
        Applies the configured render settings to the current scene.
        
        Args:
            parent (Any): Parent state for context
            useVersion (str, optional): Version strategy. Defaults to "next".
        
        Returns:
            List[str]: List containing status message
        """
        self.applySettings()
        return [self.state.text(0) + " - success"]

    @err_catcher(name=__name__)
    def getStateProps(self) -> Dict[str, Any]:
        """Get current state settings for saving.
        
        Collects all render settings state including name, preset option,
        edit mode, and render settings data for serialization.
        
        Returns:
            Dict[str, Any]: Dictionary containing state settings with keys:
                - statename (str): Name of the state
                - presetoption (str): Selected preset name
                - editsettings (bool): Whether in custom edit mode
                - rendersettings (Dict): Render settings data
                - stateenabled (int): Check state value
        """
        stateProps = {}
        stateProps.update(
            getattr(
                self.core.appPlugin, "sm_renderSettings_getStateProps", lambda x: {}
            )(self)
        )
        stateProps.update(
            {
                "statename": self.e_name.text(),
                "presetoption": self.cb_presetOption.currentText(),
                "editsettings": self.chb_editSettings.isChecked(),
                "rendersettings": self.core.readYaml(
                    data=self.te_settings.toPlainText()
                ),
                "stateenabled": self.core.getCheckStateValue(self.state.checkState(0)),
            }
        )

        return stateProps
