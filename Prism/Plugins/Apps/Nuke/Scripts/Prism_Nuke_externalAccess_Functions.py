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
import subprocess
import traceback
from typing import Any, Dict, List, Tuple

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_Nuke_externalAccess_Functions(object):
    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize Nuke external access functions.
        
        Registers callbacks for user settings, project settings, and scene presets.
        
        Args:
            core: The Prism core instance
            plugin: The plugin instance
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
    def userSettings_loadUI(self, origin: Any, tab: QWidget) -> None:
        """Load Nuke settings UI into user settings dialog.
        
        Adds controls for Nuke version selection, relative paths, and keyboard shortcuts.
        
        Args:
            origin: The user settings dialog instance
            tab: The tab widget to add Nuke settings to
        """
        origin.w_nukeVersion = QWidget()
        origin.lo_nukeVersion = QHBoxLayout(origin.w_nukeVersion)
        origin.lo_nukeVersion.setContentsMargins(0, 0, 0, 0)
        origin.l_nukeVersion = QLabel("Nuke Version:")
        origin.cb_nukeVersion = QComboBox()
        origin.cb_nukeVersion.addItems(["Default", "NukeX", "NukeX (Non-Commercial)", "Indie", "Assist", "Studio", "Studio (Non-Commercial)", "Non-Commercial"])
        origin.lo_nukeVersion.addWidget(origin.l_nukeVersion)
        origin.lo_nukeVersion.addWidget(origin.cb_nukeVersion)
        origin.lo_nukeVersion.addStretch()
        tab.layout().addWidget(origin.w_nukeVersion)

        origin.chb_nukeRelativePaths = QCheckBox("Use relative paths")
        tab.layout().addWidget(origin.chb_nukeRelativePaths)

        origin.chb_nukeUseReadPrism = QCheckBox("Open Prism window with \"R\" shortcut")
        origin.chb_nukeUseReadPrism.setChecked(True)
        tab.layout().addWidget(origin.chb_nukeUseReadPrism)

        origin.chb_nukeUseWritePrism = QCheckBox("Use WritePrism gizmo")
        origin.chb_nukeUseWritePrism.setChecked(False)
        tab.layout().addWidget(origin.chb_nukeUseWritePrism)

        origin.chb_nukeLoadOIIO = QCheckBox("Load OIIO")
        origin.chb_nukeLoadOIIO.setChecked(False)
        tab.layout().addWidget(origin.chb_nukeLoadOIIO)

    @err_catcher(name=__name__)
    def userSettings_saveSettings(self, origin: Any, settings: Dict[str, Any]) -> None:
        """Save Nuke user settings.
        
        Stores Nuke version, relative paths preference, and shortcut preferences.
        
        Args:
            origin: The user settings dialog instance
            settings: Dictionary to save settings to
        """
        if not hasattr(origin, "cb_nukeVersion"):
            return

        if "nuke" not in settings:
            settings["nuke"] = {}

        settings["nuke"]["nukeVersion"] = origin.cb_nukeVersion.currentText()
        settings["nuke"]["useRelativePaths"] = origin.chb_nukeRelativePaths.isChecked()
        settings["nuke"]["useReadPrism"] = origin.chb_nukeUseReadPrism.isChecked()
        settings["nuke"]["useWritePrism"] = origin.chb_nukeUseWritePrism.isChecked()
        settings["nuke"]["loadOIIO"] = origin.chb_nukeLoadOIIO.isChecked()

    @err_catcher(name=__name__)
    def userSettings_loadSettings(self, origin: Any, settings: Dict[str, Any]) -> None:
        """Load Nuke user settings into the UI.
        
        Restores previously saved Nuke preferences.
        
        Args:
            origin: The user settings dialog instance
            settings: Dictionary containing saved settings
        """
        if "nuke" in settings:
            if "nukeVersion" in settings["nuke"]:
                origin.cb_nukeVersion.setCurrentText(settings["nuke"]["nukeVersion"])
            if "useRelativePaths" in settings["nuke"]:
                origin.chb_nukeRelativePaths.setChecked(settings["nuke"]["useRelativePaths"])
            if "useReadPrism" in settings["nuke"]:
                origin.chb_nukeUseReadPrism.setChecked(settings["nuke"]["useReadPrism"])
            if "useWritePrism" in settings["nuke"]:
                origin.chb_nukeUseWritePrism.setChecked(settings["nuke"]["useWritePrism"])
            if "loadOIIO" in settings["nuke"]:
                origin.chb_nukeLoadOIIO.setChecked(settings["nuke"]["loadOIIO"])

    @err_catcher(name=__name__)
    def getAutobackPath(self, origin: Any) -> Tuple[str, str]:
        """Get autobackup path and file filter for Nuke.
        
        Args:
            origin: The calling instance
            
        Returns:
            Tuple of (autoback path, file filter string)
        """
        autobackpath = ""

        fileStr = "Nuke Script ("
        for i in self.sceneFormats:
            fileStr += "*%s " % i

        fileStr += ")"

        return autobackpath, fileStr

    @err_catcher(name=__name__)
    def customizeExecutable(self, origin: Any, appPath: str, filepath: str) -> bool:
        """Customize Nuke executable launch with version-specific flags.
        
        Launches Nuke with appropriate arguments based on version selection
        (NukeX, Studio, Non-Commercial, etc.).
        
        Args:
            origin: The calling instance
            appPath: Path to the Nuke executable
            filepath: Path to the scene file to open
            
        Returns:
            True if file was started successfully, False otherwise
        """
        fileStarted = False
        nukeVersion = self.core.getConfig("nuke", "nukeVersion")
        if nukeVersion and nukeVersion != "Default":
            if appPath == "":
                if not hasattr(self, "nukePath"):
                    self.nukePath = self.core.getDefaultAppByExtension(".nk")

                if self.nukePath is not None and os.path.exists(self.nukePath):
                    appPath = self.nukePath
                else:
                    QMessageBox.warning(
                        self.core.messageParent,
                        "Warning",
                        "Nuke executable doesn't exist:\n\n%s" % self.nukePath,
                    )

            if appPath is not None and appPath != "":
                args = [appPath, self.core.fixPath(filepath)]
                if nukeVersion == "NukeX":
                    args.insert(-1, "--nukex")
                elif nukeVersion == "NukeX (Non-Commercial)":
                    args.insert(-1, "--nukex")
                    args.insert(-1, "--nc")
                elif nukeVersion == "Indie":
                    args.insert(-1, "--indie")
                elif nukeVersion == "Assist":
                    args.insert(-1, "--nukeassist")
                elif nukeVersion == "Studio":
                    args.insert(-1, "--studio")
                elif nukeVersion == "Studio (Non-Commercial)":
                    args.insert(-1, "--studio")
                    args.insert(-1, "--nc")
                elif nukeVersion == "Non-Commercial":
                    args.insert(-1, "--nc")

                dccEnv = self.core.startEnv.copy()
                usrEnv = self.core.users.getUserEnvironment(appPluginName="Nuke")
                for envVar in usrEnv:
                    dccEnv[envVar["key"]] = envVar["value"]

                prjEnv = self.core.projects.getProjectEnvironment(appPluginName="Nuke")
                for envVar in prjEnv:
                    dccEnv[envVar["key"]] = envVar["value"]

                self.core.callback(name="preLaunchApp", args=[args, dccEnv])

                try:
                    subprocess.Popen(args, env=dccEnv)
                except:
                    mods = QApplication.keyboardModifiers()
                    if mods == Qt.ControlModifier:
                        if os.path.isfile(args[0]):
                            msg = "Could not execute file:\n\n%s\n\nUsed arguments: %s" % (traceback.format_exc(), args)
                        else:
                            msg = "Executable doesn't exist:\n\n%s\n\nCheck your executable override in the Prism User Settings." % args[0]
                        self.core.popup(msg)
                    else:
                        subprocess.Popen(" ".join(args), env=dccEnv, shell=True)
                        fileStarted = True
                else:
                    fileStarted = True

        return fileStarted

    @err_catcher(name=__name__)
    def getPresetScenes(self, presetScenes: List[Any]) -> None:
        """Add Nuke preset scenes to the preset list.
        
        Args:
            presetScenes: List to append preset scene information to
        """
        if os.getenv("PRISM_SHOW_DEFAULT_SCENEFILE_PRESETS", "1") != "1":
            return

        presetDir = os.path.join(self.pluginDirectory, "Presets")
        scenes = self.core.entities.getPresetScenesFromFolder(presetDir)
        presetScenes += scenes

    @err_catcher(name=__name__)
    def preProjectSettingsLoad(self, origin: Any, settings: Dict[str, Any]) -> None:
        """Load Nuke-specific project settings before the UI is shown.
        
        Args:
            origin: The project settings dialog instance
            settings: Dictionary containing project settings
        """
        if settings:
            if hasattr(origin, "sb_nuke"):
                sbData = settings.get("sceneBuilding", {})
                savedSteps = sbData.get("nuke_steps") or []
                if savedSteps:
                    origin.sb_nuke.tw_steps.clear()
                    origin.sb_nuke.addSteps(savedSteps)

    @err_catcher(name=__name__)
    def preProjectSettingsSave(self, origin: Any, settings: Dict[str, Any]) -> None:
        """Save Nuke-specific project settings before persistence.
        
        Args:
            origin: The project settings dialog instance
            settings: Dictionary to save settings to
        """
        if hasattr(origin, "sb_nuke"):
            if "sceneBuilding" not in settings:
                settings["sceneBuilding"] = {}

            settings["sceneBuilding"]["nuke_steps"] = origin.sb_nuke.getSteps()

    @err_catcher(name=__name__)
    def projectSettings_loadUI(self, origin: Any) -> None:
        """Load Nuke UI elements into project settings dialog.
        
        Args:
            origin: The project settings dialog instance
        """
        self.addUiToProjectSettings(origin)

    @err_catcher(name=__name__)
    def addUiToProjectSettings(self, projectSettings: Any) -> None:
        """Add Nuke-specific UI widgets to project settings.
        
        Adds controls for scene building preferences like media loading defaults.
        
        Args:
            projectSettings: The project settings dialog instance
        """
        projectSettings.sb_nuke = projectSettings.addSceneBuildingApp("Nuke", iconPath=self.appIcon)
        dftSteps = self.getAvailableSceneBuildingSteps()
        dftSteps = [s for s in dftSteps["results"] if s["name"] not in ["importProducts", "importShotcam", "runCode", "multishotSetup"]]
        projectSettings.sb_nuke.addSteps(dftSteps)

    @err_catcher(name=__name__)
    def getAvailableSceneBuildingSteps(self, app: str = "") -> dict:
        """Get available scene building steps.
        
        Args:
            app: Application name
            
        Returns:
            List of step names
        """
        if app and app != "Nuke":
            return {"combine": True, "results": []}
        
        steps = self.core.entities.getDefaultSceneBuildingSteps()

        nukeSteps = [
            {
                "name": "loadMedia",
                "label": "Load Media",
                "function": "self.core.appPlugin.buildSceneLoadMedia",
                "settings": [
                    {
                        "type": "lineedit",
                        "label": "Identifiers:",
                        "value": "plate*, light*",
                    }
                ]
            }
        ]
        if os.getenv("PRISM_NUKE_ENABLE_MULTISHOT", "0") == "1":
            nukeSteps.append(
                {
                    "name": "multishotSetup",
                    "label": "Multishot Setup",
                    "function": "self.core.appPlugin.buildSceneMultishotSetup",
                    "settings": []
                }
            )

        steps += nukeSteps
        result = {"combine": True, "results": steps}
        return result
