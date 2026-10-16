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
import subprocess
import traceback
from typing import Any, List, Dict, Tuple, Optional

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


logger = logging.getLogger(__name__)


class Prism_Houdini_externalAccess_Functions(object):
    """External access functions for Houdini plugin.
    
    Handles user settings, project settings, preset scenes, and external
    file operations when Prism is accessed outside of Houdini.
    
    Attributes:
        core: PrismCore instance.
        plugin: Houdini plugin instance.
        houdiniPath: Path to Houdini executable.
    """
    
    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize external access functions.
        
        Registers callbacks for settings and project management.
        
        Args:
            core: PrismCore instance.
            plugin: Houdini plugin instance.
        """
        self.core = core
        self.plugin = plugin
        self.houdiniPath = None
        data = {
            "label": "Houdini HDAs",
            "key": "@houdini_HDAs@",
            "value": "@project_path@/04_Resources/HDAs",
            "requires": ["project_path"],
        }
        self.core.projects.addProjectStructureItem("houdini_HDAs", data)
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
    def userSettings_loadUI(self, origin: Any, tab: Any) -> None:
        """Load Houdini-specific UI elements into user settings.
        
        Adds checkboxes for external file drop handling and manual update mode.
        
        Args:
            origin: User settings dialog.
            tab: Tab widget to add controls to.
        """
        lo_settings = QGridLayout()
        tab.layout().addLayout(lo_settings)
        spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)
        lo_settings.addItem(spacer, 0, 0)

        origin.chb_houdiniHandleDrop = QCheckBox("Handle external file drops in Houdini")
        filepath = os.path.join(self.plugin.pluginDirectory, "Integration", "scripts", "externaldragdrop.py")
        handleDrops = os.path.exists(filepath)
        origin.chb_houdiniHandleDrop.setChecked(handleDrops)
        tab.layout().addWidget(origin.chb_houdiniHandleDrop)

        origin.chb_houdiniManual = QCheckBox("Open scenes in manual update mode")
        tab.layout().addWidget(origin.chb_houdiniManual)

    @err_catcher(name=__name__)
    def userSettings_saveSettings(self, origin: Any, settings: Dict) -> None:
        """Save Houdini-specific user settings.
        
        Args:
            origin: User settings dialog.
            settings: Settings dictionary to update.
        """
        if hasattr(origin, "chb_houdiniHandleDrop"):
            enabled = origin.chb_houdiniHandleDrop.isChecked()
            self.setDropHandlingEnabled(enabled)

        if hasattr(origin, "chb_houdiniManual"):
            if "houdini" not in settings:
                settings["houdini"] = {}

            settings["houdini"]["openInManual"] = origin.chb_houdiniManual.isChecked()

    @err_catcher(name=__name__)
    def userSettings_loadSettings(self, origin: Any, settings: Dict) -> None:
        """Load Houdini-specific user settings into UI.
        
        Args:
            origin: User settings dialog.
            settings: Settings dictionary to read from.
        """
        filepath = os.path.join(self.plugin.pluginDirectory, "Integration", "scripts", "externaldragdrop.py")
        handleDrops = os.path.exists(filepath)
        origin.chb_houdiniHandleDrop.setChecked(handleDrops)

        if "houdini" in settings:
            if "openInManual" in settings["houdini"]:
                origin.chb_houdiniManual.setChecked(settings["houdini"]["openInManual"])

    @err_catcher(name=__name__)
    def setDropHandlingEnabled(self, state: bool) -> None:
        """Enable or disable external file drop handling in Houdini.
        
        Renames the externaldragdrop.py file to activate/deactivate it.
        
        Args:
            state: True to enable, False to disable.
        """
        filepath = os.path.join(self.plugin.pluginDirectory, "Integration", "scripts", "externaldragdrop.py")
        inactivePath = os.path.join(os.path.dirname(filepath), "_" + os.path.basename(filepath))
        if state:
            if not os.path.exists(filepath):
                if not os.path.exists(inactivePath):
                    self.core.popup("Failed to enable external file drop handling in Houdini. The required file doesn't exist:\n\n%s" % (inactivePath))
                    return

                try:
                    os.rename(inactivePath, filepath)
                except:
                    self.core.popup("Failed to rename file.\n\nFrom: %s\nTo: %s" % (inactivePath, filepath))
                else:
                    logger.debug("enabled filedrop handling in Houdini.")
        else:
            if os.path.exists(filepath):                
                try:
                    os.rename(filepath, inactivePath)
                except:
                    self.core.popup("Failed to rename file.\n\nFrom: %s\nTo: %s" % (filepath, inactivePath))
                else:
                    logger.debug("disabled filedrop handling in Houdini.")

    @err_catcher(name=__name__)
    def getAutobackPath(self, origin: Any) -> Tuple[str, str]:
        """Get the autobackup path for Houdini scene files.
        
        Args:
            origin: Calling object.
        
        Returns:
            Tuple of (autobackup path, file filter string).
        """
        autobackpath = ""
        if platform.system() == "Windows":
            autobackpath = os.path.join(
                os.getenv("LocalAppdata"), "Temp", "houdini_temp"
            )

            if not os.path.exists(autobackpath):
                autobackpath = os.path.dirname(autobackpath)

        fileStr = "Houdini Scene File ("
        for i in self.sceneFormats:
            fileStr += "*%s " % i

        fileStr += ")"

        return autobackpath, fileStr

    @err_catcher(name=__name__)
    def getPresetScenes(self, presetScenes: List) -> None:
        """Add Houdini preset scenes to the preset scenes list.
        
        Args:
            presetScenes: List to append preset scenes to.
        """
        if os.getenv("PRISM_SHOW_DEFAULT_SCENEFILE_PRESETS", "1") != "1":
            return

        presetDir = os.path.join(self.pluginDirectory, "Presets")
        scenes = self.core.entities.getPresetScenesFromFolder(presetDir)
        presetScenes += scenes

    @err_catcher(name=__name__)
    def preProjectSettingsLoad(self, origin: Any, settings: Dict) -> None:
        """Load Houdini project settings before UI is displayed.
        
        Args:
            origin: Project settings dialog.
            settings: Settings dictionary to load from.
        """
        if settings:
            if "houdini" in settings and hasattr(origin, "chb_houdiniRelative"):
                if "useRelativePaths" in settings["houdini"]:
                    origin.chb_houdiniRelative.setChecked(settings["houdini"]["useRelativePaths"])

            if hasattr(origin, "sb_houdini"):
                sbData = settings.get("sceneBuilding", {})
                savedSteps = sbData.get("houdini_steps") or []
                if savedSteps:
                    origin.sb_houdini.tw_steps.clear()
                    origin.sb_houdini.addSteps(savedSteps)

    @err_catcher(name=__name__)
    def preProjectSettingsSave(self, origin: Any, settings: Dict) -> None:
        """Save Houdini project settings.
        
        Args:
            origin: Project settings dialog.
            settings: Settings dictionary to update.
        """
        if hasattr(origin, "chb_houdiniRelative"):
            if "houdini" not in settings:
                settings["houdini"] = {}

            rel = origin.chb_houdiniRelative.isChecked()
            settings["houdini"]["useRelativePaths"] = rel

        if hasattr(origin, "sb_houdini"):
            if "sceneBuilding" not in settings:
                settings["sceneBuilding"] = {}

            settings["sceneBuilding"]["houdini_steps"] = origin.sb_houdini.getSteps()

    @err_catcher(name=__name__)
    def projectSettings_loadUI(self, origin: Any) -> None:
        """Load Houdini-specific UI elements into project settings.
        
        Args:
            origin: Project settings dialog.
        """
        self.addUiToProjectSettings(origin)

    @err_catcher(name=__name__)
    def addUiToProjectSettings(self, projectSettings: Any) -> None:
        """Add Houdini UI controls to project settings dialog.
        
        Creates group boxes for relative paths and scene building options.
        
        Args:
            projectSettings: Project settings dialog.
        """
        projectSettings.w_houdini = QGroupBox("Houdini")
        lo_houdini = QGridLayout()
        projectSettings.w_houdini.setLayout(lo_houdini)

        ttip = "When enabled Prism will use filepaths, relative to the $PRISM_JOB environment variable when importing files in Houdini. When disabled, Prism will use absolute filepaths instead."
        l_relative = QLabel("Use relative paths:")
        l_relative.setToolTip(ttip)
        projectSettings.chb_houdiniRelative = QCheckBox()
        projectSettings.chb_houdiniRelative.setToolTip(ttip)

        lo_houdini.addWidget(l_relative, 0, 0)
        sp_stretch = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred)
        lo_houdini.addItem(sp_stretch, 0, 1)
        lo_houdini.addWidget(projectSettings.chb_houdiniRelative, 0, 2)
        projectSettings.w_prjSettings.layout().addWidget(projectSettings.w_houdini)
        projectSettings.sb_houdini = projectSettings.addSceneBuildingApp("Houdini", iconPath=self.appIcon)
        dftSteps = self.getAvailableSceneBuildingSteps()
        dftSteps = [s for s in dftSteps["results"] if s["name"] not in ["runCode", "apply_abc_caches"]]
        projectSettings.sb_houdini.addSteps(dftSteps)

    @err_catcher(name=__name__)
    def customizeExecutable(self, origin: Any, appPath: str, filepath: str) -> bool:
        """Customize Houdini executable launch with manual update mode.
        
        Opens Houdini with -n flag for manual update mode if configured.
        
        Args:
            origin: Calling object.
            appPath: Path to application executable.
            filepath: Path to scene file to open.
        
        Returns:
            True if file was started, False otherwise.
        """
        fileStarted = False
        if self.core.getConfig("houdini", "openInManual"):
            if not appPath:
                if not self.houdiniPath:
                    self.houdiniPath = self.core.getDefaultAppByExtension(".hip")
                    if self.houdiniPath and self.houdiniPath.endswith("hview.exe"):
                        hexe = os.path.join(os.path.dirname(self.houdiniPath), "houdini.exe")
                        if os.path.exists(hexe):
                            self.houdiniPath = hexe  # hview.exe doesn't support -n

                if self.houdiniPath and os.path.exists(self.houdiniPath):
                    appPath = self.houdiniPath
                else:
                    self.core.popup("Houdini executable doesn't exist:\n\n%s" % self.houdiniPath)

            if appPath:
                args = [appPath, "-n", self.core.fixPath(filepath)]
                logger.debug("opening Houdini: %s" % args)
                try:
                    subprocess.Popen(args, env=self.core.startEnv)
                except:
                    mods = QApplication.keyboardModifiers()
                    if mods == Qt.ControlModifier:
                        if os.path.isfile(args[0]):
                            msg = "Could not execute file:\n\n%s\n\nUsed arguments: %s" % (traceback.format_exc(), args)
                        else:
                            msg = "Executable doesn't exist:\n\n%s\n\nCheck your executable override in the Prism User Settings." % args[0]
                        self.core.popup(msg)
                    else:
                        subprocess.Popen(" ".join(args), env=self.core.startEnv, shell=True)
                        fileStarted = True
                else:
                    fileStarted = True

        return fileStarted

    @err_catcher(name=__name__)
    def getAvailableSceneBuildingSteps(self, app: str = "") -> dict:
        """Get available scene building steps.
        
        Args:
            app: Application name
            
        Returns:
            List of step names
        """
        if app and app != "Houdini":
            return {"combine": True, "results": []}
        
        steps = self.core.entities.getDefaultSceneBuildingSteps()

        houdiniSteps = [
            {
                "name": "apply_abc_caches",
                "label": "Apply Alembic Caches",
                "function": "self.core.appPlugin.buildSceneApplyAbcCaches",
                "get_update_data": "self.core.appPlugin.buildSceneGetApplyAbcCachesUpdateData",
                "description": "Create or update source/cache import states for tagged Alembic cache products.",
            }
        ]
        steps += houdiniSteps
        result = {"combine": True, "results": steps}
        return result
