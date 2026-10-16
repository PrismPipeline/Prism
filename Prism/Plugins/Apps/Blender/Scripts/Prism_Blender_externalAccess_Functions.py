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
import platform
from typing import Any, Dict, List, Tuple

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_Blender_externalAccess_Functions(object):
    """External access functions for Blender plugin.
    
    Provides UI elements, callbacks, and settings management for Blender
    integration that can be accessed from outside Blender.
    
    Attributes:
        core: PrismCore instance.
        plugin: Plugin instance.
    """
    
    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize external access functions.
        
        Registers callbacks for user settings and preset scenes.
        
        Args:
            core: PrismCore instance.
            plugin: Plugin instance.
        """
        self.core = core
        self.plugin = plugin
        self.core.registerCallback(
            "userSettings_saveSettings",
            self.userSettings_saveSettings,
            plugin=self.plugin,
        )
        self.core.registerCallback(
            "userSettings_loadSettings",
            self.userSettings_loadSettings,
            plugin=self.plugin,
        )
        self.core.registerCallback("getPresetScenes", self.getPresetScenes, plugin=self.plugin)
        ssheetPath = os.path.join(
            self.pluginDirectory,
            "UserInterfaces",
            "BlenderStyleSheet"
        )
        self.core.registerStyleSheet(ssheetPath)
        self.core.registerCallback(
            "preProjectSettingsLoad", self.preProjectSettingsLoad, plugin=self.plugin
        )
        self.core.registerCallback(
            "preProjectSettingsSave", self.preProjectSettingsSave, plugin=self.plugin
        )
        self.core.registerCallback(
            "projectSettings_loadUI", self.projectSettings_loadUI, plugin=self.plugin
        )
        self.core.registerCallback(
            "getAvailableSceneBuildingSteps", self.getAvailableSceneBuildingSteps, plugin=self.plugin
        )

    @err_catcher(name=__name__)
    def userSettings_loadUI(self, origin: Any, tab: Any) -> None:
        """Load Blender-specific UI elements in user settings.
        
        Creates auto-save render settings section with path configuration.
        
        Args:
            origin: User settings dialog instance.
            tab: Tab widget to add UI elements to.
        """
        origin.gb_bldAutoSave = QGroupBox("Auto save renderings")
        lo_bldAutoSave = QVBoxLayout()
        origin.gb_bldAutoSave.setLayout(lo_bldAutoSave)
        origin.gb_bldAutoSave.setCheckable(True)
        origin.gb_bldAutoSave.setChecked(False)

        origin.chb_bldRperProject = QCheckBox("use path only for current project")

        w_bldAutoSavePath = QWidget()
        lo_bldAutoSavePath = QHBoxLayout()
        origin.le_bldAutoSavePath = QLineEdit()
        b_bldAutoSavePath = QPushButton("...")

        lo_bldAutoSavePath.setContentsMargins(0, 0, 0, 0)
        b_bldAutoSavePath.setMinimumSize(40, 0)
        b_bldAutoSavePath.setMaximumSize(40, 1000)
        b_bldAutoSavePath.setFocusPolicy(Qt.NoFocus)
        b_bldAutoSavePath.setContextMenuPolicy(Qt.CustomContextMenu)
        w_bldAutoSavePath.setLayout(lo_bldAutoSavePath)
        lo_bldAutoSavePath.addWidget(origin.le_bldAutoSavePath)
        lo_bldAutoSavePath.addWidget(b_bldAutoSavePath)

        lo_bldAutoSave.addWidget(origin.chb_bldRperProject)
        lo_bldAutoSave.addWidget(w_bldAutoSavePath)
        tab.layout().addWidget(origin.gb_bldAutoSave)

        if hasattr(self.core, "projectPath") and self.core.projectPath is not None:
            origin.le_bldAutoSavePath.setText(self.core.projectPath)

        b_bldAutoSavePath.clicked.connect(
            lambda: origin.browse(
                windowTitle="Select render save path", uiEdit=origin.le_bldAutoSavePath
            )
        )
        b_bldAutoSavePath.customContextMenuRequested.connect(
            lambda: self.core.openFolder(origin.le_bldAutoSavePath.text())
        )

    @err_catcher(name=__name__)
    def userSettings_saveSettings(self, origin: Any, settings: Dict) -> None:
        """Save Blender-specific user settings.
        
        Saves auto-save render path and per-project settings.
        
        Args:
            origin: User settings dialog instance.
            settings: Settings dictionary to save to.
        """
        if "blender" not in settings:
            settings["blender"] = {}

        if hasattr(origin, "le_bldAutoSavePath"):
            bsPath = self.core.fixPath(origin.le_bldAutoSavePath.text())
            if not bsPath.endswith(os.sep):
                bsPath += os.sep

            if origin.chb_bldRperProject.isChecked():
                if os.path.exists(self.core.prismIni):
                    k = "autosavepath_%s" % self.core.projectName
                    settings["blender"][k] = bsPath
            else:
                settings["blender"]["autosavepath"] = bsPath

            settings["blender"]["autosaverender"] = origin.gb_bldAutoSave.isChecked()
            settings["blender"][
                "autosaveperproject"
            ] = origin.chb_bldRperProject.isChecked()

    @err_catcher(name=__name__)
    def userSettings_loadSettings(self, origin: Any, settings: Dict) -> None:
        """Load Blender-specific user settings.
        
        Loads auto-save render path from saved settings.
        
        Args:
            origin: User settings dialog instance.
            settings: Settings dictionary to load from.
        """
        if "blender" in settings:
            if "autosaverender" in settings["blender"]:
                origin.gb_bldAutoSave.setChecked(settings["blender"]["autosaverender"])

            if "autosaveperproject" in settings["blender"]:
                origin.chb_bldRperProject.setChecked(
                    settings["blender"]["autosaveperproject"]
                )

            pData = "autosavepath_%s" % getattr(self.core, "projectName", "")
            if pData in settings["blender"]:
                if origin.chb_bldRperProject.isChecked():
                    origin.le_bldAutoSavePath.setText(settings["blender"][pData])

            if "autosavepath" in settings["blender"]:
                if not origin.chb_bldRperProject.isChecked():
                    origin.le_bldAutoSavePath.setText(
                        settings["blender"]["autosavepath"]
                    )

    @err_catcher(name=__name__)
    def preProjectSettingsLoad(self, origin: Any, settings: Dict) -> None:
        """Load Blender project settings before UI is displayed.
        
        Args:
            origin: Project settings dialog.
            settings: Settings dictionary to load from.
        """
        if settings:
            if hasattr(origin, "chb_blenderRelative") and "useRelativePaths" in settings.get("blender", {}):
                origin.chb_blenderRelative.setChecked(settings["blender"]["useRelativePaths"])

            if hasattr(origin, "sb_blender"):
                sbData = settings.get("sceneBuilding", {})
                savedSteps = sbData.get("blender_steps") or []
                if savedSteps:
                    origin.sb_blender.tw_steps.clear()
                    origin.sb_blender.addSteps(savedSteps)

    @err_catcher(name=__name__)
    def preProjectSettingsSave(self, origin: Any, settings: Dict) -> None:
        """Save Blender project settings.
        
        Args:
            origin: Project settings dialog.
            settings: Settings dictionary to update.
        """
        if hasattr(origin, "chb_blenderRelative"):
            settings.setdefault("blender", {})["useRelativePaths"] = origin.chb_blenderRelative.isChecked()

        if hasattr(origin, "sb_blender"):
            if "sceneBuilding" not in settings:
                settings["sceneBuilding"] = {}

            settings["sceneBuilding"]["blender_steps"] = origin.sb_blender.getSteps()

    @err_catcher(name=__name__)
    def projectSettings_loadUI(self, origin: Any) -> None:
        """Load Blender-specific UI elements into project settings.
        
        Args:
            origin: Project settings dialog.
        """
        self.addUiToProjectSettings(origin)

    @err_catcher(name=__name__)
    def addUiToProjectSettings(self, projectSettings: Any) -> None:
        """Add Blender UI controls to project settings dialog.
        
        Creates group boxes for relative paths and scene building options.
        
        Args:
            projectSettings: Project settings dialog.
        """
        projectSettings.w_blender = QGroupBox("Blender")
        lo_blender = QGridLayout()
        projectSettings.w_blender.setLayout(lo_blender)

        label = QLabel("Use relative paths:")
        tooltip = "Store imported file references relative to the saved Blender scene."
        label.setToolTip(tooltip)
        projectSettings.chb_blenderRelative = QCheckBox()
        projectSettings.chb_blenderRelative.setToolTip(tooltip)
        lo_blender.addWidget(label, 0, 0)
        lo_blender.addWidget(projectSettings.chb_blenderRelative, 0, 2)
        lo_blender.setColumnStretch(1, 1)
        projectSettings.w_prjSettings.layout().addWidget(projectSettings.w_blender)

        projectSettings.sb_blender = projectSettings.addSceneBuildingApp("Blender", iconPath=self.appIcon)
        dftSteps = self.getAvailableSceneBuildingSteps()
        dftSteps = [s for s in dftSteps["results"] if s["name"] not in ["runCode"]]
        projectSettings.sb_blender.addSteps(dftSteps)

    @err_catcher(name=__name__)
    def createProject_startup(self, origin: Any) -> None:
        """Handle project creation dialog startup.
        
        Adjusts window flags when on-top behavior is enabled.
        
        Args:
            origin: Create project dialog instance.
        """
        if self.core.useOnTop:
            origin.setWindowFlags(origin.windowFlags() ^ Qt.WindowStaysOnTopHint)

    @err_catcher(name=__name__)
    def getAutobackPath(self, origin: Any) -> Tuple[str, str]:
        """Get default autoback path and file filter string.
        
        Args:
            origin: Originating object.
        
        Returns:
            Tuple of (autoback path, file filter string).
        """
        autobackpath = ""
        if platform.system() == "Windows":
            autobackpath = os.path.join(os.getenv("LocalAppdata"), "Temp")

        fileStr = "Blender Scene File ("
        for i in self.sceneFormats:
            fileStr += "*%s " % i

        fileStr += ")"

        return autobackpath, fileStr

    @err_catcher(name=__name__)
    def getPresetScenes(self, presetScenes: List) -> None:
        """Add Blender preset scenes to preset list.
        
        Loads preset scene files from plugin presets directory.
        
        Args:
            presetScenes: List to append preset scenes to.
        """
        if os.getenv("PRISM_SHOW_DEFAULT_SCENEFILE_PRESETS", "1") != "1":
            return

        presetDir = os.path.join(self.pluginDirectory, "Presets")
        scenes = self.core.entities.getPresetScenesFromFolder(presetDir)
        presetScenes += scenes

    @err_catcher(name=__name__)
    def getAvailableSceneBuildingSteps(self, app: str = "") -> dict:
        """Get available scene building steps.
        
        Args:
            app: Application name
            
        Returns:
            List of step names
        """
        if app and app != "Blender":
            return {"combine": True, "results": []}
        
        steps = self.core.entities.getDefaultSceneBuildingSteps()
        result = {"combine": True, "results": steps}
        return result
