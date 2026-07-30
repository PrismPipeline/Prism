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
import time
import logging
import importlib
from typing import Any, Dict, List, Optional, Tuple, Union

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher as err_catcher


logger = logging.getLogger(__name__)


class Prism_Deadline_Functions(object):
    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize Deadline plugin functions and register callbacks.
        
        Args:
            core: Prism core instance
            plugin: Plugin instance reference
        """
        self.core = core
        self.plugin = plugin
        if self.core.appPlugin.pluginName == "Houdini":
            self.hou = importlib.import_module("hou")

        self.sceneDescriptions = {
            "mantra": {
                "submitFunction": self.submitSceneDescriptionMantra,
                "getOutputPath": self.getMantraOutputPath,
                "suffix": "_ifd_export",
            },
            "3delight": {
                "submitFunction": self.submitSceneDescription3Delight,
                "getOutputPath": self.get3DelightOutputPath,
                "suffix": "_nsi_export",
            },
            "redshift": {
                "submitFunction": self.submitSceneDescriptionRedshift,
                "getOutputPath": self.getRedshiftOutputPath,
                "suffix": "_rs_export",
            },
            "arnold": {
                "submitFunction": self.submitSceneDescriptionArnold,
                "getOutputPath": self.getArnoldOutputPath,
                "suffix": "_ass_export",
            },
            "vray": {
                "submitFunction": self.submitSceneDescriptionVray,
                "getOutputPath": self.getVrayOutputPath,
                "suffix": "_vrscene_export",
            },
        }
        self.core.plugins.registerRenderfarmPlugin(self)
        self.core.registerCallback("onStateStartup", self.onStateStartup, plugin=self.plugin)
        self.core.registerCallback("onStateGetSettings", self.onStateGetSettings, plugin=self.plugin)
        self.core.registerCallback("onStateSettingsLoaded", self.onStateSettingsLoaded, plugin=self.plugin)
        self.core.registerCallback("projectSettings_loadUI", self.projectSettings_loadUI, plugin=self.plugin)
        self.core.registerCallback(
            "preProjectSettingsLoad", self.preProjectSettingsLoad, plugin=self.plugin
        )
        self.core.registerCallback(
            "preProjectSettingsSave", self.preProjectSettingsSave, plugin=self.plugin
        )
        self.core.registerCallback("prePublish", self.prePublish, plugin=self.plugin)
        self.core.registerCallback("postPublish", self.postPublish, plugin=self.plugin)
        dft = """[expression,#  available variables:
#  "core" - PrismCore
#  "context" - dict

if context.get("type") == "asset":
    base = "@asset@"
else:
    base = "@sequence@-@shot@"

template = base + "_@product@@identifier@_@version@@_(layer)@@_(comment)@"]"""

        data = {"label": "Deadline Job Name", "key": "@deadline_job_name@", "value": dft, "requires": []}
        self.core.projects.addProjectStructureItem("deadlineJobName", data)

    @err_catcher(name=__name__)
    def isActive(self) -> bool:
        """Check if Deadline is active and available.
        
        Returns:
            Always True (Deadline groups check disabled)
        """
        try:
            return True  # len(self.getDeadlineGroups()) > 0
        except:
            return False

    @err_catcher(name=__name__)
    def unregister(self) -> None:
        """Unregister Deadline as a renderfarm plugin."""
        self.core.plugins.unregisterRenderfarmPlugin(self)

    def GetDeadlineCommand(self) -> str:
        """Get path to deadlinecommand executable from environment.
        
        Checks DEADLINE_PATH environment variable or on macOS reads from
        /Users/Shared/Thinkbox/DEADLINE_PATH file.
        
        Returns:
            Full path to deadlinecommand executable
        """
        deadlineBin = ""
        try:
            deadlineBin = os.environ['DEADLINE_PATH']
        except KeyError:
            #if the error is a key error it means that DEADLINE_PATH is not set. however Deadline command may be in the PATH or on OSX it could be in the file /Users/Shared/Thinkbox/DEADLINE_PATH
            pass

        # On OSX, we look for the DEADLINE_PATH file if the environment variable does not exist.
        if deadlineBin == "" and  os.path.exists( "/Users/Shared/Thinkbox/DEADLINE_PATH" ):
            with open( "/Users/Shared/Thinkbox/DEADLINE_PATH" ) as f:
                deadlineBin = f.read().strip()

        deadlineCommand = os.path.join(deadlineBin, "deadlinecommand")

        return deadlineCommand

    def CallDeadlineCommand(self, arguments: List[str], hideWindow: bool = True, readStdout: bool = True, silent: bool = False) -> Union[str, bool]:
        """Execute deadlinecommand with given arguments.
        
        Args:
            arguments: List of command-line arguments to pass to deadlinecommand
            hideWindow: If True, hide console window on Windows
            readStdout: If True, read and return stdout from command
            silent: If True, log warnings instead of showing popup on errors
            
        Returns:
            Command stdout output as string, or False on error
        """
        deadlineCommand = self.GetDeadlineCommand()
        startupinfo = None
        creationflags = 0
        if os.name == 'nt':
            if hideWindow:
                # Python 2.6 has subprocess.STARTF_USESHOWWINDOW, and Python 2.7 has subprocess._subprocess.STARTF_USESHOWWINDOW, so check for both.
                if hasattr( subprocess, '_subprocess' ) and hasattr( subprocess._subprocess, 'STARTF_USESHOWWINDOW' ):
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
                elif hasattr( subprocess, 'STARTF_USESHOWWINDOW' ):
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            else:
                # still show top-level windows, but don't show a console window
                CREATE_NO_WINDOW = 0x08000000   #MSDN process creation flag
                creationflags = CREATE_NO_WINDOW

        arguments.insert( 0, deadlineCommand )
        # Specifying PIPE for all handles to workaround a Python bug on Windows. The unused handles are then closed immediately afterwards.
        try:
            proc = subprocess.Popen(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, creationflags=creationflags)
        except Exception as e:
            if e.errno == 2:
                msg = "Cannot connect to Deadline. Unable to find the \"deadlinecommand\" executable."
                if silent:
                    logger.warning(msg)
                else:
                    self.core.popup(msg)

                return False

        output = ""
        if readStdout:
            output, errors = proc.communicate()

        output = output.strip()

        if sys.version_info[0] > 2 and type(output) == bytes:
            output = output.decode('utf-8', errors='replace')

        return output

    @err_catcher(name=__name__)
    def refreshPools(self) -> List[str]:
        """Refresh Deadline pools from Deadline command and store in project config.
        
        Returns:
            List of available Deadline pool names
        """
        if not hasattr(self.core, "projectPath"):
            return []

        with self.core.waitPopup(self.core, "Getting pools from Deadline. Please wait..."):
            output = self.CallDeadlineCommand(["-pools"], silent=True)

        if output and "Error" not in output:
            deadlinePools = output.splitlines()
        else:
            deadlinePools = []

        self.core.setConfig("deadline", "pools", val=deadlinePools, config="project")
        return deadlinePools

    @err_catcher(name=__name__)
    def getDeadlinePools(self) -> List[str]:
        """Get available Deadline pools from project config, refreshing if needed.
        
        Returns:
            List of available Deadline pool names
        """
        if not hasattr(self.core, "projectPath"):
            return []

        pools = self.core.getConfig("deadline", "pools", config="project")
        if pools is None:
            self.refreshPools()
            pools = self.core.getConfig("deadline", "pools", config="project")

        pools = pools or []
        return pools

    @err_catcher(name=__name__)
    def refreshGroups(self) -> List[str]:
        """Refresh Deadline groups from Deadline command and store in project config.
        
        Returns:
            List of available Deadline group names
        """
        if not hasattr(self.core, "projectPath"):
            return []

        with self.core.waitPopup(self.core, "Getting groups from Deadline. Please wait..."):
            output = self.CallDeadlineCommand(["-groups"], silent=True)

        if output and "Error" not in output:
            deadlineGroups = output.splitlines()
        else:
            deadlineGroups = []

        self.core.setConfig("deadline", "groups", val=deadlineGroups, config="project")
        return deadlineGroups

    @err_catcher(name=__name__)
    def getDeadlineGroups(self) -> List[str]:
        """Get available Deadline groups from project config, refreshing if needed.
        
        Returns:
            List of available Deadline group names
        """
        if not hasattr(self.core, "projectPath"):
            return []

        groups = self.core.getConfig("deadline", "groups", config="project")
        if groups is None:
            self.refreshGroups()
            groups = self.core.getConfig("deadline", "groups", config="project")

        groups = groups or []
        return groups

    @err_catcher(name=__name__)
    def getUseDeadlinePoolPresets(self) -> bool:
        """Check if pool presets are enabled in project config.
        
        Returns:
            True if pool presets should be used
        """
        usePresets = self.core.getConfig("deadline", "usePoolPresets", config="project")
        return usePresets

    @err_catcher(name=__name__)
    def getDeadlinePoolPresets(self) -> List[str]:
        """Get names of configured Deadline pool presets.
        
        Returns:
            List of pool preset names
        """
        if not self.getUseDeadlinePoolPresets():
            return []

        presets = self.core.getConfig("deadline", "poolPresets", config="project")
        names = [p.get("name", "") for p in presets]
        return names

    @err_catcher(name=__name__)
    def getPoolPresetData(self, preset: str) -> Optional[Dict[str, Any]]:
        """Get configuration data for a specific pool preset.
        
        Args:
            preset: Name of the pool preset
            
        Returns:
            Dictionary with preset configuration or None if not found
        """
        presets = self.core.getConfig("deadline", "poolPresets", config="project")
        matches = [p for p in presets if p.get("name") == preset]
        if matches:
            return matches[0]

    @err_catcher(name=__name__)
    def onRefreshPoolsClicked(self, settings: Any) -> None:
        """Handle refresh pools button click in project settings.
        
        Args:
            settings: Project settings dialog instance
        """
        self.refreshPools()
        self.refreshGroups()
        settings.gb_dlPoolPresets.refresh()

    @err_catcher(name=__name__)
    def getDeadlineUsername(self) -> Union[str, bool]:
        """Get current Deadline username from deadlinecommand.
        
        Returns:
            Current Deadline username, or False if Deadline not available
        """
        name = self.CallDeadlineCommand(["-GetCurrentUserName"], silent=True)
        return name

    @err_catcher(name=__name__)
    def onSubmitPythonJobClicked(self, settings: Any) -> None:
        """Handle submit Python job button click in project settings.
        
        Args:
            settings: Project settings dialog instance
        """
        if hasattr(self, "dlg_pythonJob") and self.dlg_pythonJob.isVisible():
            self.dlg_pythonJob.close()

        self.dlg_pythonJob = SubmitPythonJobDlg(self, parent=settings)
        self.dlg_pythonJob.show()

    @err_catcher(name=__name__)
    def projectSettings_loadUI(self, origin: Any) -> None:
        """Load Deadline UI into project settings dialog.
        
        Args:
            origin: Project settings dialog instance
        """
        self.addUiToProjectSettings(origin)

    @err_catcher(name=__name__)
    def addUiToProjectSettings(self, projectSettings: Any) -> None:
        """Add Deadline configuration UI tab to project settings dialog.
        
        Creates UI controls for scene submission, script dependencies, pool presets,
        environment variables, and refresh actions.
        
        Args:
            projectSettings: Project settings dialog instance
        """
        projectSettings.w_deadline = QWidget()
        lo_deadline = QGridLayout()
        projectSettings.w_deadline.setLayout(lo_deadline)

        projectSettings.chb_submitScenes = QCheckBox("Submit scenefiles together with jobs")
        projectSettings.chb_submitScenes.setToolTip("When checked the scenefile, from which a Deadline job gets submitted, will be copied to the Deadline repository.\nWhen disabled When disabled the Deadline Workers will open the scenefile at the original location. This can be useful when using relative filepaths, but has the risk of getting overwritten by artists while a job is rendering.")
        projectSettings.chb_submitScenes.setChecked(True)
        lo_deadline.addWidget(projectSettings.chb_submitScenes)

        projectSettings.chb_scriptDeps = QCheckBox("Use Script Dependencies for Scene Description Jobs")
        projectSettings.chb_scriptDeps.setToolTip("When checked Scene Description render jobs jobs will be submitted with script dependencies which makes tasks dependent on the existence of the scene description file. If unchecked normal job dependencies will be used.")
        projectSettings.chb_scriptDeps.setChecked(False)
        lo_deadline.addWidget(projectSettings.chb_scriptDeps)

        projectSettings.gb_dlPoolPresets = PresetWidget(self)
        projectSettings.gb_dlPoolPresets.setCheckable(True)
        projectSettings.gb_dlPoolPresets.setChecked(False)
        lo_deadline.addWidget(projectSettings.gb_dlPoolPresets)

        projectSettings.w_refreshPools = QWidget()
        projectSettings.lo_refreshPools = QHBoxLayout()
        projectSettings.w_refreshPools.setLayout(projectSettings.lo_refreshPools)
        projectSettings.lo_refreshPools.addStretch()
        projectSettings.b_refreshPools = QPushButton("Refresh Pools/Groups")
        projectSettings.b_refreshPools.clicked.connect(lambda: self.onRefreshPoolsClicked(projectSettings))
        projectSettings.lo_refreshPools.addWidget(projectSettings.b_refreshPools)
        lo_deadline.addWidget(projectSettings.w_refreshPools)

        projectSettings.w_submitPythonJob = QWidget()
        projectSettings.lo_submitPythonJob = QHBoxLayout(projectSettings.w_submitPythonJob)
        projectSettings.lo_submitPythonJob.addStretch()
        projectSettings.b_submitPythonJob = QPushButton("Submit Python Job...")
        projectSettings.b_submitPythonJob.clicked.connect(lambda: self.onSubmitPythonJobClicked(projectSettings))
        projectSettings.lo_submitPythonJob.addWidget(projectSettings.b_submitPythonJob)
        lo_deadline.addWidget(projectSettings.w_submitPythonJob)

        projectSettings.tw_dlenvs = EnvironmentTable(self)
        projectSettings.tw_dlenvs.setMaximumHeight(160)
        projectSettings.tw_dlenvs.w_footer.setHidden(True)
        projectSettings.tw_dlenvs.tw_environment.horizontalHeader().setVisible(False)
        lo_deadline.addWidget(projectSettings.tw_dlenvs)

        sp_stretch = QSpacerItem(0, 0, QSizePolicy.Fixed, QSizePolicy.Expanding)
        lo_deadline.addItem(sp_stretch)
        projectSettings.addTab(projectSettings.w_deadline, "Deadline")

    @err_catcher(name=__name__)
    def preProjectSettingsLoad(self, origin: Any, settings: Dict[str, Any]) -> None:
        """Load Deadline settings from config into project settings UI.
        
        Args:
            origin: Project settings dialog instance
            settings: Dictionary containing project settings
        """
        if not settings:
            return
        
        if "deadline" in settings:
            if "submitScenes" in settings["deadline"]:
                val = settings["deadline"]["submitScenes"]
                origin.chb_submitScenes.setChecked(val)

            if "useScriptDependencies" in settings["deadline"]:
                val = settings["deadline"]["useScriptDependencies"]
                origin.chb_scriptDeps.setChecked(val)

            if "usePoolPresets" in settings["deadline"]:
                val = settings["deadline"]["usePoolPresets"]
                origin.gb_dlPoolPresets.setChecked(val)

            if "poolPresets" in settings["deadline"]:
                val = settings["deadline"]["poolPresets"]
                if val:
                    origin.gb_dlPoolPresets.loadPresetData(val)

            if "jobEnvVars" in settings["deadline"]:
                val = settings["deadline"]["jobEnvVars"]
                if val:
                    origin.tw_dlenvs.loadEnvironmant(val)

    @err_catcher(name=__name__)
    def preProjectSettingsSave(self, origin: Any, settings: Dict[str, Any]) -> None:
        """Save Deadline settings from project settings UI to config.
        
        Args:
            origin: Project settings dialog instance
            settings: Dictionary to store project settings
        """
        if "deadline" not in settings:
            settings["deadline"] = {}

        settings["deadline"]["submitScenes"] = origin.chb_submitScenes.isChecked()
        settings["deadline"]["useScriptDependencies"] = origin.chb_scriptDeps.isChecked()
        settings["deadline"]["usePoolPresets"] = origin.gb_dlPoolPresets.isChecked()
        settings["deadline"]["poolPresets"] = origin.gb_dlPoolPresets.getPresetData()
        settings["deadline"]["jobEnvVars"] = origin.tw_dlenvs.getEnvironmentVariables()

    @err_catcher(name=__name__)
    def useScriptDependencies(self) -> bool:
        """Check if script dependencies should be used for scene description jobs.
        
        Returns:
            True if script dependencies are enabled in project config
        """
        return self.core.getConfig(
            "deadline", "useScriptDependencies", dft=False, config="project"
        )

    @err_catcher(name=__name__)
    def getJobEnvVars(self) -> Union[bool, Dict[str, str]]:
        """Get job environment variables from project config.
        
        Returns:
            Dictionary of environment variables or False if not configured
        """
        return self.core.getConfig(
            "deadline", "jobEnvVars", dft=False, config="project"
        )

    @err_catcher(name=__name__)
    def prePublish(self, origin: Any) -> None:
        """Initialize job tracking dictionaries before publish.
        
        Args:
            origin: Publishing state instance
        """
        origin.submittedDlJobs = {}
        origin.submittedDlJobData = {}

    @err_catcher(name=__name__)
    def postPublish(self, origin: Any, pubType: str, result: Any) -> None:
        """Post-publish callback (currently no action taken).
        
        Args:
            origin: Publishing state instance
            pubType: Type of publish operation
            result: Result of publish operation
        """
        pass
        # origin.submittedDlJobs = {}
        # origin.submittedDlJobData = {}

    @err_catcher(name=__name__)
    def sm_updateDlDeps(self, origin: Any, item: Any, column: int) -> None:
        """Update Deadline dependencies when checkbox state changes.
        
        Handles three dependency types: Job Completed, Frames Completed, File Exists.
        Updates origin.dependencies["Deadline"] list based on checkbox state.
        
        Args:
            origin: Dependency state instance
            item: Tree widget item that was checked/unchecked
            column: Column index (unused)
        """
        itemData = item.data(0, Qt.UserRole)
        if not itemData:
            return

        curType = origin.cb_depType.currentText()
        if curType == "Job Completed":
            curIds = origin.dependencies["Deadline"]
            if itemData.ui.uuid in curIds and item.checkState(0) == Qt.Unchecked:
                origin.dependencies["Deadline"].remove(itemData.ui.uuid)
            elif itemData.ui.uuid not in curIds and item.checkState(0) == Qt.Checked:
                origin.dependencies["Deadline"].append(itemData.ui.uuid)
        elif curType == "Frames Completed":
            curIds = origin.dependencies["Deadline"]
            if itemData.ui.uuid in curIds and item.checkState(0) == Qt.Unchecked:
                origin.dependencies["Deadline"].remove(itemData.ui.uuid)
            elif itemData.ui.uuid not in curIds and item.checkState(0) == Qt.Checked:
                origin.dependencies["Deadline"].append(itemData.ui.uuid)
        elif curType == "File Exists":
            curParms = [dep["parm"] for dep in origin.dependencies["Deadline"]]
            if itemData["parm"] in curParms and item.checkState(0) == Qt.Unchecked:
                origin.dependencies["Deadline"].remove(itemData)
            elif itemData["parm"] not in curParms and item.checkState(0) == Qt.Checked:
                origin.dependencies["Deadline"].append(itemData)

        origin.nameChanged(origin.e_name.text())
        origin.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def sm_dlGoToNode(self, item: Any, column: int) -> None:
        """Navigate to and select Houdini node in network editor.
        
        Args:
            item: Tree widget item containing node reference
            column: Column index (unused)
        """
        if item.parent() is None:
            return

        node = item.data(0, Qt.UserRole).node()
        if node:
            node.setCurrent(True, clear_all_selected=True)
            paneTab = self.hou.ui.paneTabOfType(self.hou.paneTabType.NetworkEditor)
            if paneTab is not None:
                paneTab.setCurrentNode(self.node)
                paneTab.homeToSelection()

    @err_catcher(name=__name__)
    def sm_dep_updateUI(self, origin: Any) -> None:
        """Update dependency UI based on selected dependency type.
        
        Shows appropriate tree widget items for Job Completed, Frames Completed,
        or File Exists dependency types.
        
        Args:
            origin: Dependency state instance
        """
        origin.gb_dlDependency.setVisible(True)

        curType = origin.cb_depType.currentText()
        origin.cb_depType.clear()
        items = ["Job Completed", "Frames Completed", "File Exists"]
        origin.cb_depType.addItems(items)
        if curType in items:
            origin.cb_depType.setCurrentText(curType)

        origin.tw_caches.clear()
        curType = origin.cb_depType.currentText()
        if curType == "Job Completed":
            newActive = self.updateUiJobCompleted(origin)
        elif curType == "Frames Completed":
            newActive = self.updateUiFramesCompleted(origin)
        elif curType == "File Exists":
            newActive = self.updateUiFileExists(origin)

        origin.dependencies["Deadline"] = newActive

    @err_catcher(name=__name__)
    def updateUiJobCompleted(self, origin: Any) -> List[str]:
        """Update UI for Job Completed dependency type.
        
        Lists all states with submit capability that precede the current state
        in execution order.
        
        Args:
            origin: Dependency state instance
            
        Returns:
            List of state UUIDs that are marked as dependencies
        """
        newActive = []
        sm = origin.stateManager
        items = []
        origin.w_offset.setHidden(True)
        origin.tw_caches.setHeaderLabel("States")
        parent = origin.tw_caches.invisibleRootItem()
        stateOrder = sm.getStateExecutionOrder()
        if origin.state in stateOrder:
            curOrder = stateOrder.index(origin.state)
        else:
            curOrder = -1

        for state in sm.states:
            if not hasattr(state.ui, "gb_submit"):
                continue

            if curOrder != -1 and stateOrder.index(state) > curOrder:
                continue

            itemName = state.text(0)
            item = QTreeWidgetItem(parent, [itemName])
            item.setData(0, Qt.UserRole, state)
            item.setToolTip(0, state.ui.uuid)
            items.append(item)

        newActive = origin.dependencies.get("Deadline", [])
        newActive = [n for n in newActive if self.core.isStr(n)]
        for item in items:
            state = item.data(0, Qt.UserRole)
            depids = origin.dependencies.get("Deadline", [])
            if state.ui.uuid in depids:
                item.setCheckState(0, Qt.Checked)
                if state.ui.uuid not in newActive:
                    newActive.append(state.ui.uuid)
            else:
                item.setCheckState(0, Qt.Unchecked)

        return newActive

    @err_catcher(name=__name__)
    def updateUiFramesCompleted(self, origin: Any) -> List[str]:
        """Update UI for Frames Completed dependency type.
        
        Lists all states with submit capability that precede the current state
        in execution order. Shows frame offset control.
        
        Args:
            origin: Dependency state instance
            
        Returns:
            List of state UUIDs that are marked as dependencies
        """
        newActive = []
        sm = origin.stateManager
        items = []
        origin.w_offset.setHidden(False)
        origin.tw_caches.setHeaderLabel("States")
        parent = origin.tw_caches.invisibleRootItem()
        stateOrder = sm.getStateExecutionOrder()
        if origin.state in stateOrder:
            curOrder = stateOrder.index(origin.state)
        else:
            curOrder = -1

        for state in sm.states:
            if not hasattr(state.ui, "gb_submit"):
                continue

            if curOrder != -1 and stateOrder.index(state) > curOrder:
                continue

            itemName = state.text(0)
            item = QTreeWidgetItem(parent, [itemName])
            item.setData(0, Qt.UserRole, state)
            item.setToolTip(0, state.ui.uuid)
            items.append(item)

        newActive = origin.dependencies.get("Deadline", [])
        newActive = [n for n in newActive if self.core.isStr(n)]
        for item in items:
            state = item.data(0, Qt.UserRole)
            depids = origin.dependencies.get("Deadline", [])
            if state.ui.uuid in depids:
                item.setCheckState(0, Qt.Checked)
                if state.ui.uuid not in newActive:
                    newActive.append(state.ui.uuid)
            else:
                item.setCheckState(0, Qt.Unchecked)

        return newActive

    @err_catcher(name=__name__)
    def updateUiFileExists(self, origin: Any) -> List[Dict[str, Any]]:
        """Update UI for File Exists dependency type.
        
        Lists all Houdini nodes with file parameters (file, rop, filecache nodes).
        Shows frame offset control.
        
        Args:
            origin: Dependency state instance
            
        Returns:
            List of dictionaries containing parm and node info for dependencies
        """
        origin.w_offset.setHidden(False)
        origin.tw_caches.setHeaderLabel("Nodes with filepath parms")
        QTreeWidgetItem(origin.tw_caches, ["Import"])
        QTreeWidgetItem(origin.tw_caches, ["Export"])

        fileNodeList = []
        copFileNodeList = []
        ropDopNodeList = []
        ropCopNodeList = []
        ropSopNodeList = []
        ropAbcNodeList = []
        filecacheNodeList = []

        for node in self.hou.node("/").allSubChildren():
            if node.type().name() == "file":
                if (
                    node.type().category().name() == "Sop"
                    and len(node.parm("file").keyframes()) == 0
                ):
                    fileNodeList.append(node)
                elif (
                    node.type().category().name() == "Cop2"
                    and len(node.parm("filename1").keyframes()) == 0
                ):
                    copFileNodeList.append(node)
            elif (
                node.type().name() == "rop_dop"
                and len(node.parm("dopoutput").keyframes()) == 0
            ):
                ropDopNodeList.append(node)
            elif (
                node.type().name() == "rop_comp"
                and len(node.parm("copoutput").keyframes()) == 0
            ):
                ropCopNodeList.append(node)
            elif (
                node.type().name() == "rop_geometry"
                and len(node.parm("sopoutput").keyframes()) == 0
            ):
                ropSopNodeList.append(node)
            elif (
                node.type().name() == "rop_alembic"
                and len(node.parm("filename").keyframes()) == 0
            ):
                ropAbcNodeList.append(node)
            elif (
                node.type().name() == "filecache"
                and len(node.parm("file").keyframes()) == 0
            ):
                filecacheNodeList.append(node)

        deps = []

        for node in fileNodeList:
            data = {"parm": node.parm("file").path(), "type": "input"}
            deps.append(data)

        for node in copFileNodeList:
            data = {"parm": node.parm("filename1").path(), "type": "input"}
            deps.append(data)

        for node in ropDopNodeList:
            data = {"parm": node.parm("dopoutput").path(), "type": "output"}
            deps.append(data)

        for node in ropCopNodeList:
            data = {"parm": node.parm("copoutput").path(), "type": "output"}
            deps.append(data)

        for node in ropSopNodeList:
            data = {"parm": node.parm("sopoutput").path(), "type": "output"}
            deps.append(data)

        for node in filecacheNodeList:
            data = {"parm": node.parm("file").path(), "type": "output"}
            deps.append(data)

        for node in ropAbcNodeList:
            data = {"parm": node.parm("filename").path(), "type": "output"}
            deps.append(data)

        for dep in deps:
            nodepath = os.path.dirname(dep["parm"])
            itemName = os.path.basename(os.path.dirname(nodepath)) + "/" + os.path.basename(nodepath)
            if dep["type"] == "input":
                parent = origin.tw_caches.topLevelItem(0)
            else:
                parent = origin.tw_caches.topLevelItem(1)

            item = QTreeWidgetItem(parent, [itemName])
            item.setData(0, Qt.UserRole, dep)
            item.setToolTip(0, self.hou.parm(dep["parm"]).unexpandedString() + "\n" + dep["parm"])

        items = []
        for i in range(origin.tw_caches.topLevelItemCount()):
            origin.tw_caches.topLevelItem(i).setExpanded(True)
            for k in range(origin.tw_caches.topLevelItem(i).childCount()):
                items.append(origin.tw_caches.topLevelItem(i).child(k))

        newActive = []
        for item in items:
            data = item.data(0, Qt.UserRole)
            deppaths = [
               dep["parm"] for dep in origin.dependencies.get("Deadline", []) if isinstance(dep, dict)
            ]
            if data["parm"] in deppaths:
                item.setCheckState(0, Qt.Checked)
                newActive.append(data)
            else:
                item.setCheckState(0, Qt.Unchecked)

        return newActive

    @err_catcher(name=__name__)
    def sm_dep_preExecute(self, origin: Any) -> List[str]:
        """Pre-execution validation for dependency state.
        
        Args:
            origin: Dependency state instance
            
        Returns:
            List of warning messages (currently empty)
        """
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def sm_dep_execute(self, origin: Any, parent: Any) -> None:
        """Execute dependency configuration by adding dependencies to parent state.
        
        Processes three types of dependencies:
        - Job Completed: Wait for entire job to complete
        - Frames Completed: Wait for matching frames with offset
        - File Exists: Wait for file parameters to exist with offset
        
        Args:
            origin: Dependency state instance
            parent: Parent state that will receive the dependency configuration
        """
        if origin.chb_clear.isChecked():
            parent.dependencies = []

        curType = origin.cb_depType.currentText()
        if curType == "Job Completed":
            for dep in origin.dependencies["Deadline"]:
                jobIds = self.getSubmittedJobIdsFromState(origin.stateManager, dep)
                if not jobIds:
                    continue

                depData = {"type": "job", "jobids": jobIds}
                parent.dependencies.append(depData)

        elif curType == "Frames Completed":
            for dep in origin.dependencies["Deadline"]:
                jobIds = self.getSubmittedJobIdsFromState(origin.stateManager, dep)
                if not jobIds:
                    continue

                depData = {"type": "frame", "offset": origin.sp_offset.value(), "jobids": jobIds}
                parent.dependencies.append(depData)

        elif curType == "File Exists":
            for dep in origin.dependencies["Deadline"]:
                depData = {"type": "file", "offset": origin.sp_offset.value(), "filepath": self.hou.parm(dep["parm"]).eval()}
                parent.dependencies.append(depData)

    @err_catcher(name=__name__)
    def onStateStartup(self, state: Any) -> None:
        """Called when state is initialized, skips if manager is not Deadline.
        
        Args:
            state: State instance being initialized
        """
        if hasattr(state, "cb_manager") and state.cb_manager.currentText() != "Deadline":
            return

    @err_catcher(name=__name__)
    def reloadStateUi(self, state: Any) -> None:
        """Reload and rebuild Deadline UI elements for render or dependency states.
        
        For Dependency states: Connects tree widget signals for dependency management.
        For Render states: Adds comprehensive Deadline submission controls including
        pools, groups, machine limit, priorities, presets, and tile rendering options.
        
        Args:
            state: State instance to configure UI for
        """
        if state.className == "Dependency":
            state.tw_caches.itemClicked.connect(
                lambda x, y: self.sm_updateDlDeps(state, x, y)
            )
            state.tw_caches.itemDoubleClicked.connect(self.sm_dlGoToNode)
        else:
            settings = {}
            self.onStateGetSettings(state, settings)
            if hasattr(state, "gb_submit"):
                lo = state.gb_submit.layout()

                if self.core.appPlugin.pluginName == "3dsMax":
                    state.w_redshift = QWidget()
                    state.lo_redshift = QHBoxLayout(state.w_redshift)
                    state.lo_redshift.setContentsMargins(9, 0, 9, 0)
                    state.l_redshift = QLabel("Render .rs files:")
                    state.chb_redshift = QCheckBox()
                    state.lo_redshift.addWidget(state.l_redshift)
                    state.lo_redshift.addStretch()
                    state.lo_redshift.addWidget(state.chb_redshift)
                    state.chb_redshift.toggled.connect(state.stateManager.saveStatesToScene)
                    lo.addWidget(state.w_redshift)

                    state.w_tileJob = QWidget()
                    state.lo_tileJob = QHBoxLayout()
                    state.lo_tileJob.setContentsMargins(9, 0, 9, 0)
                    state.l_tileJob = QLabel("Tile Job:")
                    state.chb_tileJob = QCheckBox()
                    state.cb_tileJob = QComboBox()
                    tiles = ["2x2", "3x3", "4x4", "5x5", "6x6", "7x7", "8x8"]
                    state.cb_tileJob.addItems(tiles)
                    state.cb_tileJob.setEnabled(False)
                    state.w_tileJob.setLayout(state.lo_tileJob)
                    state.lo_tileJob.addWidget(state.l_tileJob)
                    state.lo_tileJob.addStretch()
                    state.lo_tileJob.addWidget(state.chb_tileJob)
                    state.lo_tileJob.addWidget(state.cb_tileJob)
                    state.chb_tileJob.toggled.connect(lambda s: state.cb_tileJob.setEnabled(s))
                    state.chb_tileJob.toggled.connect(lambda s: state.stateManager.saveStatesToScene())
                    state.cb_tileJob.activated.connect(lambda s: state.stateManager.saveStatesToScene())
                    lo.addWidget(state.w_tileJob)

                if self.core.appPlugin.pluginName == "Maya":
                    state.w_vrscene = QWidget()
                    state.lo_vrscene = QHBoxLayout(state.w_vrscene)
                    state.lo_vrscene.setContentsMargins(9, 0, 9, 0)
                    state.l_vrscene = QLabel("Render .vrscene files:")
                    state.chb_vrscene = QCheckBox()
                    state.lo_vrscene.addWidget(state.l_vrscene)
                    state.lo_vrscene.addStretch()
                    state.lo_vrscene.addWidget(state.chb_vrscene)
                    state.chb_vrscene.toggled.connect(state.stateManager.saveStatesToScene)
                    lo.addWidget(state.w_vrscene)

                    state.w_exportSceneLocally = QWidget()
                    state.lo_exportSceneLocally = QHBoxLayout(state.w_exportSceneLocally)
                    state.lo_exportSceneLocally.setContentsMargins(9, 0, 9, 0)
                    state.l_exportSceneLocally = QLabel("Export scene description locally:")
                    state.chb_exportSceneLocally = QCheckBox()
                    state.lo_exportSceneLocally.addWidget(state.l_exportSceneLocally)
                    state.lo_exportSceneLocally.addStretch()
                    state.lo_exportSceneLocally.addWidget(state.chb_exportSceneLocally)
                    state.chb_exportSceneLocally.toggled.connect(state.stateManager.saveStatesToScene)
                    lo.addWidget(state.w_exportSceneLocally)

                state.w_machineLimit = QWidget()
                state.lo_machineLimit = QHBoxLayout()
                state.lo_machineLimit.setContentsMargins(9, 0, 9, 0)
                state.l_machineLimit = QLabel("Machine Limit:")
                state.sp_machineLimit = QSpinBox()
                state.sp_machineLimit.setMaximum(99999)
                state.w_machineLimit.setLayout(state.lo_machineLimit)
                state.lo_machineLimit.addWidget(state.l_machineLimit)
                state.lo_machineLimit.addStretch()
                state.lo_machineLimit.addWidget(state.sp_machineLimit)
                state.sp_machineLimit.editingFinished.connect(state.stateManager.saveStatesToScene)
                lo.addWidget(state.w_machineLimit)

                state.w_dlPreset = QWidget()
                state.lo_dlPreset = QHBoxLayout()
                state.lo_dlPreset.setContentsMargins(9, 0, 9, 0)
                state.l_dlPreset = QLabel("Pool Preset:")
                state.cb_dlPreset = QComboBox()
                state.cb_dlPreset.setMinimumWidth(150)
                state.w_dlPreset.setLayout(state.lo_dlPreset)
                state.lo_dlPreset.addWidget(state.l_dlPreset)
                state.lo_dlPreset.addStretch()
                state.lo_dlPreset.addWidget(state.cb_dlPreset)
                presets = self.getDeadlinePoolPresets()
                state.cb_dlPreset.addItems(presets)
                state.cb_dlPreset.currentIndexChanged.connect(lambda x: self.presetChanged(state))
                lo.addWidget(state.w_dlPreset)

                state.w_dlPool = QWidget()
                state.lo_dlPool = QHBoxLayout()
                state.lo_dlPool.setContentsMargins(9, 0, 9, 0)
                state.l_dlPool = QLabel("Pool:")
                state.cb_dlPool = QComboBox()
                state.cb_dlPool.setToolTip("Deadline Pool (can be updated in the Prism Project Settings)")
                state.cb_dlPool.setMinimumWidth(150)
                state.w_dlPool.setLayout(state.lo_dlPool)
                state.lo_dlPool.addWidget(state.l_dlPool)
                state.lo_dlPool.addStretch()
                state.lo_dlPool.addWidget(state.cb_dlPool)
                state.cb_dlPool.activated.connect(state.stateManager.saveStatesToScene)
                lo.addWidget(state.w_dlPool)

                state.w_sndPool = QWidget()
                state.lo_sndPool = QHBoxLayout()
                state.lo_sndPool.setContentsMargins(9, 0, 9, 0)
                state.l_sndPool = QLabel("Secondary Pool:")
                state.cb_sndPool = QComboBox()
                state.cb_sndPool.setToolTip("Deadline Seconday Pool (can be updated in the Prism Project Settings)")
                state.cb_sndPool.setMinimumWidth(150)
                state.w_sndPool.setLayout(state.lo_sndPool)
                state.lo_sndPool.addWidget(state.l_sndPool)
                state.lo_sndPool.addStretch()
                state.lo_sndPool.addWidget(state.cb_sndPool)
                state.cb_sndPool.activated.connect(state.stateManager.saveStatesToScene)
                lo.addWidget(state.w_sndPool)

                state.w_dlGroup = QWidget()
                state.lo_dlGroup = QHBoxLayout()
                state.lo_dlGroup.setContentsMargins(9, 0, 9, 0)
                state.l_dlGroup = QLabel("Group:")
                state.cb_dlGroup = QComboBox()
                state.cb_dlGroup.setToolTip("Deadline Group (can be updated in the Prism Project Settings)")
                state.cb_dlGroup.setMinimumWidth(150)
                state.w_dlGroup.setLayout(state.lo_dlGroup)
                state.lo_dlGroup.addWidget(state.l_dlGroup)
                state.lo_dlGroup.addStretch()
                state.lo_dlGroup.addWidget(state.cb_dlGroup)
                state.cb_dlGroup.activated.connect(state.stateManager.saveStatesToScene)
                lo.addWidget(state.w_dlGroup)

                state.gb_prioJob = QGroupBox("Submit High Prio Job")
                state.gb_prioJob.setCheckable(True)
                state.gb_prioJob.setChecked(False)
                lo.addWidget(state.gb_prioJob)

                state.lo_prioJob = QVBoxLayout()
                state.gb_prioJob.setLayout(state.lo_prioJob)
                state.gb_prioJob.toggled.connect(state.stateManager.saveStatesToScene)

                state.w_highPrio = QWidget()
                state.lo_highPrio = QHBoxLayout()
                state.l_highPrio = QLabel("Priority:")
                state.sp_highPrio = QSpinBox()
                state.sp_highPrio.setMaximum(100)
                state.sp_highPrio.setValue(70)
                state.lo_prioJob.addWidget(state.w_highPrio)
                state.w_highPrio.setLayout(state.lo_highPrio)
                state.lo_highPrio.addWidget(state.l_highPrio)
                state.lo_highPrio.addStretch()
                state.lo_highPrio.addWidget(state.sp_highPrio)
                state.lo_highPrio.setContentsMargins(0, 0, 0, 0)
                state.sp_highPrio.editingFinished.connect(state.stateManager.saveStatesToScene)

                state.w_highPrioFrames = QWidget()
                state.lo_highPrioFrames = QHBoxLayout()
                state.l_highPrioFrames = QLabel("Frames:")
                state.e_highPrioFrames = QLineEdit()
                state.e_highPrioFrames.setText("{first}, {middle}, {last}")
                state.b_highPrioFrames = QToolButton()
                state.b_highPrioFrames.setArrowType(Qt.DownArrow)
                state.lo_prioJob.addWidget(state.w_highPrioFrames)
                state.w_highPrioFrames.setLayout(state.lo_highPrioFrames)
                state.lo_highPrioFrames.addWidget(state.l_highPrioFrames)
                state.lo_highPrioFrames.addStretch()
                state.lo_highPrioFrames.addWidget(state.e_highPrioFrames)
                state.lo_highPrioFrames.addWidget(state.b_highPrioFrames)
                state.lo_highPrioFrames.setContentsMargins(0, 0, 0, 0)
                state.e_highPrioFrames.editingFinished.connect(
                    state.stateManager.saveStatesToScene
                )
                state.b_highPrioFrames.clicked.connect(lambda x=None, s=state: self.showHighPrioJobPresets(s))

                if presets:
                    state.w_dlPool.setHidden(True)
                    state.w_sndPool.setHidden(True)
                    state.w_dlGroup.setHidden(True)
                    self.presetChanged(state)
                else:
                    state.w_dlPreset.setHidden(True)

            if hasattr(state, "cb_dlPool"):
                state.cb_dlPool.addItems(self.getDeadlinePools())

            if hasattr(state, "cb_sndPool"):
                state.cb_sndPool.addItems(self.getDeadlinePools())

            if hasattr(state, "cb_dlGroup"):
                state.cb_dlGroup.addItems(self.getDeadlineGroups())

            self.onStateSettingsLoaded(state, settings)

    @err_catcher(name=__name__)
    def unsetManager(self, state: Any) -> None:
        """Remove Deadline UI elements from state when switching managers.
        
        Deletes and hides all Deadline-specific widgets including pool/group controls,
        machine limit, and priority job settings.
        
        Args:
            state: State instance to clean up
        """
        if hasattr(state, "w_machineLimit"):
            state.w_machineLimit.setHidden(True)
            state.w_machineLimit.setParent(None)
            state.w_machineLimit.deleteLater()

        if hasattr(state, "w_dlPreset"):
            state.w_dlPreset.setHidden(True)
            state.w_dlPreset.setParent(None)
            state.w_dlPreset.deleteLater()

        if hasattr(state, "w_dlPool"):
            state.w_dlPool.setHidden(True)
            state.w_dlPool.setParent(None)
            state.w_dlPool.deleteLater()

        if hasattr(state, "w_sndPool"):
            state.w_sndPool.setHidden(True)
            state.w_sndPool.setParent(None)
            state.w_sndPool.deleteLater()

        if hasattr(state, "w_dlGroup"):
            state.w_dlGroup.setHidden(True)
            state.w_dlGroup.setParent(None)
            state.w_dlGroup.deleteLater()

        if hasattr(state, "gb_prioJob"):
            state.gb_prioJob.setHidden(True)
            state.gb_prioJob.setParent(None)
            state.gb_prioJob.deleteLater()

        if hasattr(state, "w_vrscene"):
            state.w_vrscene.setHidden(True)
            state.w_vrscene.setParent(None)
            state.w_vrscene.deleteLater()

        if hasattr(state, "w_exportSceneLocally"):
            state.w_exportSceneLocally.setHidden(True)
            state.w_exportSceneLocally.setParent(None)
            state.w_exportSceneLocally.deleteLater()

    @err_catcher(name=__name__)
    def presetChanged(self, state: Any) -> None:
        """Apply pool preset settings when preset selection changes.
        
        Updates pool, secondary pool, and group based on selected preset data.
        
        Args:
            state: State instance with preset controls
        """
        if not self.getUseDeadlinePoolPresets():
            return

        preset = state.cb_dlPreset.currentText()
        data = self.getPoolPresetData(preset)
        if not data:
            return

        if data["pool"]:
            idx = state.cb_dlPool.findText(data["pool"])
            if idx != -1:
                state.cb_dlPool.setCurrentIndex(idx)

        if data["secondaryPool"]:
            idx = state.cb_sndPool.findText(data["secondaryPool"])
            if idx != -1:
                state.cb_sndPool.setCurrentIndex(idx)

        if data["group"]:
            idx = state.cb_dlGroup.findText(data["group"])
            if idx != -1:
                state.cb_dlGroup.setCurrentIndex(idx)

        state.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def showHighPrioJobPresets(self, state: Any) -> None:
        """Show context menu with preset frame patterns for high priority jobs.
        
        Args:
            state: State instance with high priority job controls
        """
        presets = [
            "{first}, {middle}, {last}",
            "{first}-{last}x10"
        ]
        
        menu = QMenu(state)

        for preset in presets:
            act_open = QAction(preset, state)
            act_open.triggered.connect(lambda x=None, p=preset: state.e_highPrioFrames.setText(p))
            menu.addAction(act_open)

        menu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def onStateGetSettings(self, state: Any, settings: Dict[str, Any]) -> None:
        """Save Deadline settings from state UI into settings dictionary.
        
        Args:
            state: State instance to get settings from
            settings: Dictionary to store settings
        """
        if hasattr(state, "gb_submit") and state.cb_manager.currentText() == "Deadline" and hasattr(state, "sp_machineLimit"):
            settings["dl_machineLimit"] = state.sp_machineLimit.value()
            settings["dl_poolPreset"] = state.cb_dlPreset.currentText()
            settings["curdlpool"] = state.cb_dlPool.currentText()
            settings["dl_sndPool"] = state.cb_sndPool.currentText()
            settings["curdlgroup"] = state.cb_dlGroup.currentText()
            settings["dl_useSecondJob"] = state.gb_prioJob.isChecked()
            settings["dl_secondJobPrio"] = state.sp_highPrio.value()
            settings["dl_secondJobFrames"] = state.e_highPrioFrames.text()
            if hasattr(state, "w_redshift"):
                settings["rjRenderRS"] = state.chb_redshift.isChecked()

            if hasattr(state, "w_tileJob"):
                settings["useTiles"] = state.chb_tileJob.isChecked()
                settings["tileCount"] = state.cb_tileJob.currentText()

            if hasattr(state, "w_vrscene"):
                settings["rjRendervrscene"] = state.chb_vrscene.isChecked()
                settings["exportSceneLocally"] = state.chb_exportSceneLocally.isChecked()

    @err_catcher(name=__name__)
    def onStateSettingsLoaded(self, state: Any, settings: Dict[str, Any]) -> None:
        """Load Deadline settings from dictionary into state UI controls.
        
        Args:
            state: State instance to load settings into
            settings: Dictionary containing saved settings
        """
        if hasattr(state, "gb_submit") and state.cb_manager.currentText() == "Deadline" and hasattr(state, "sp_machineLimit"):
            if "dl_machineLimit" in settings:
                state.sp_machineLimit.setValue(settings["dl_machineLimit"])

            if "curdlpool" in settings:
                idx = state.cb_dlPool.findText(settings["curdlpool"])
                if idx != -1:
                    state.cb_dlPool.setCurrentIndex(idx)

            if "dl_sndPool" in settings:
                idx = state.cb_sndPool.findText(settings["dl_sndPool"])
                if idx != -1:
                    state.cb_sndPool.setCurrentIndex(idx)

            if "curdlgroup" in settings:
                idx = state.cb_dlGroup.findText(settings["curdlgroup"])
                if idx != -1:
                    state.cb_dlGroup.setCurrentIndex(idx)

            if "dl_useSecondJob" in settings:
                state.gb_prioJob.setChecked(settings["dl_useSecondJob"])

            if "dl_secondJobPrio" in settings:
                state.sp_highPrio.setValue(settings["dl_secondJobPrio"])

            if "dl_secondJobFrames" in settings:
                state.e_highPrioFrames.setText(settings["dl_secondJobFrames"])

            if "dl_poolPreset" in settings:
                idx = state.cb_dlPreset.findText(settings["dl_poolPreset"])
                if idx != -1:
                    state.cb_dlPreset.setCurrentIndex(idx)

            self.presetChanged(state)

            if hasattr(state, "w_redshift"):
                if "rjRenderRS" in settings:
                    state.chb_redshift.setChecked(settings["rjRenderRS"])

            if hasattr(state, "w_tileJob"):
                if "useTiles" in settings:
                    state.chb_tileJob.setChecked(settings["useTiles"])
                if "tileCount" in settings:
                    idx = state.cb_tileJob.findText(settings["tileCount"])
                    if idx != -1:
                        state.cb_tileJob.setCurrentIndex(idx)

            if hasattr(state, "w_vrscene"):
                if "rjRendervrscene" in settings:
                    state.chb_vrscene.setChecked(settings["rjRendervrscene"])
                if "exportSceneLocally" in settings:
                    state.chb_exportSceneLocally.setChecked(settings["exportSceneLocally"])

    @err_catcher(name=__name__)
    def sm_houExport_activated(self, origin: Any) -> None:
        """Called when Houdini Export state is activated with Deadline manager.
        
        Reloads UI and hides OS-specific controls not used by Deadline.
        
        Args:
            origin: Export state instance
        """
        self.reloadStateUi(origin)
        origin.f_osDependencies.setVisible(False)
        origin.f_osUpload.setVisible(False)
        origin.f_osPAssets.setVisible(False)
        origin.gb_osSlaves.setVisible(False)

    @err_catcher(name=__name__)
    def sm_houExport_preExecute(self, origin: Any) -> List[str]:
        """Pre-execution validation for Houdini Export state.
        
        Args:
            origin: Export state instance
            
        Returns:
            List of warning messages (currently empty)
        """
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def sm_dep_managerChanged(self, origin: Any) -> None:
        """Called when renderfarm manager changes in dependency state.
        
        Args:
            origin: Dependency state instance
        """
        self.reloadStateUi(origin)

    @err_catcher(name=__name__)
    def sm_houRender_updateUI(self, origin: Any) -> None:
        """Update UI for Houdini Render state, showing GPU settings for Redshift.
        
        Args:
            origin: Houdini Render state instance
        """
        showGPUsettings = (
            origin.node is not None and origin.node.type().name() == "Redshift_ROP"
        )
        origin.w_dlGPUpt.setVisible(showGPUsettings)
        origin.w_dlGPUdevices.setVisible(showGPUsettings)

    @err_catcher(name=__name__)
    def sm_houRender_managerChanged(self, origin: Any) -> None:
        """Called when renderfarm manager changes in Houdini Render state.
        
        Reloads UI, calls app plugin manager changed, and hides OS dependencies.
        
        Args:
            origin: Houdini Render state instance
        """
        self.reloadStateUi(origin)
        getattr(self.core.appPlugin, "sm_render_managerChanged", lambda x, y: None)(
            origin, False
        )
        
        origin.f_osDependencies.setVisible(False)
        origin.f_osUpload.setVisible(False)

        origin.f_osPAssets.setVisible(False)
        origin.gb_osSlaves.setVisible(False)
        origin.w_dlConcurrentTasks.setVisible(True)

        showGPUsettings = (
            origin.node is not None and origin.node.type().name() == "Redshift_ROP"
        )
        origin.w_dlGPUpt.setVisible(showGPUsettings)
        origin.w_dlGPUdevices.setVisible(showGPUsettings)

    @err_catcher(name=__name__)
    def sm_houRender_preExecute(self, origin: Any) -> List[str]:
        """Pre-execution validation for Houdini Render state.
        
        Args:
            origin: Houdini Render state instance
            
        Returns:
            List of warning messages (currently empty)
        """
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def sm_render_updateUI(self, origin: Any) -> None:
        """Update UI for generic Render state with Deadline manager.
        
        Hides OS-specific controls and shows pool presets or individual pool/group
        controls based on project configuration. Handles GPU settings visibility
        for Redshift renderer.
        
        Args:
            origin: Render state instance
        """
        if hasattr(origin, "f_osDependencies"):
            origin.f_osDependencies.setVisible(False)

        if hasattr(origin, "gb_osSlaves"):
            origin.gb_osSlaves.setVisible(False)

        if hasattr(origin, "f_osUpload"):
            origin.f_osUpload.setVisible(False)

        if hasattr(origin, "f_osPAssets"):
            origin.f_osPAssets.setVisible(False)

        origin.w_dlConcurrentTasks.setVisible(True)

        presets = self.getDeadlinePoolPresets()
        if presets:
            origin.w_dlPool.setHidden(True)
            origin.w_sndPool.setHidden(True)
            origin.w_dlGroup.setHidden(True)
            self.presetChanged(origin)
        else:
            origin.w_dlPreset.setHidden(True)

        curRenderer = getattr(self.core.appPlugin, "getCurrentRenderer", lambda x: "")(
            origin
        ).lower()

        if hasattr(origin, "w_dlGPUpt"):
            showGPUsettings = "redshift" in curRenderer if curRenderer else False
            origin.w_dlGPUpt.setVisible(showGPUsettings)
            origin.w_dlGPUdevices.setVisible(showGPUsettings)

        if hasattr(origin, "w_redshift"):
            isRs = self.core.appPlugin.getCurrentRenderer(origin) == "Redshift_Renderer"
            origin.w_redshift.setHidden(not isRs)

        if hasattr(origin, "w_vrscene"):
            isVray = getattr(self.core.appPlugin, "getCurrentRenderer", lambda x: "")(origin) == "vray"
            origin.w_vrscene.setHidden(not isVray)
            origin.w_exportSceneLocally.setHidden(not isVray)

    @err_catcher(name=__name__)
    def sm_render_managerChanged(self, origin: Any) -> None:
        """Called when renderfarm manager changes in Render state.
        
        Reloads UI, calls app plugin manager changed, and refreshes submit UI.
        
        Args:
            origin: Render state instance
        """
        self.reloadStateUi(origin)
        getattr(self.core.appPlugin, "sm_render_managerChanged", lambda x, y: None)(
            origin, False
        )
        origin.refreshSubmitUi()

    @err_catcher(name=__name__)
    def sm_export_managerChanged(self, origin: Any) -> None:
        """Called when renderfarm manager changes in Export state.
        
        Reloads UI, calls app plugin manager changed, and refreshes submit UI.
        
        Args:
            origin: Export state instance
        """
        self.reloadStateUi(origin)
        getattr(self.core.appPlugin, "sm_export_managerChanged", lambda x, y: None)(
            origin, False
        )
        origin.refreshSubmitUi()

    @err_catcher(name=__name__)
    def sm_render_preExecute(self, origin: Any) -> List[str]:
        """Pre-execution validation for generic Render state.
        
        Args:
            origin: Render state instance
            
        Returns:
            List of warning messages (currently empty)
        """
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def getCurrentSceneFiles(self, origin: Any) -> List[str]:
        """Get list of current scene files to submit with Deadline job.
        
        Args:
            origin: State instance
            
        Returns:
            List containing current scene file path, or empty list if no scene
        """
        curFileName = self.core.getCurrentFileName()
        if not curFileName:
            return []

        scenefiles = [curFileName]
        return scenefiles

    @err_catcher(name=__name__)
    def getJobName(self, details: Optional[Dict[str, Any]] = None, origin: Optional[Any] = None, quiet: bool = False) -> str:
        """Generate Deadline job name from project template.
        
        Uses the @deadline_job_name@ project structure template with context from
        current scene and ROP node.
        
        Args:
            details: Optional context dictionary for template resolution
            origin: Optional state instance with node reference
            quiet: If True, suppress popup warnings for empty job names
            
        Returns:
            Resolved job name string
        """
        scenefileName = os.path.splitext(self.core.getCurrentFileName(path=False))[0]
        details = details or {}
        context = details.copy()
        context["scenefilename"] = scenefileName
        if origin and getattr(origin, "node", None):
            try:
                context["ropname"] = origin.node.name()
            except:
                pass

        jobName = self.core.projects.getResolvedProjectStructurePath("deadlineJobName", context=context, fallback="") or ""
        if not jobName and not quiet:
            logger.warning("invalid Deadline jobname: %s" % context)
            self.core.popup("Empty Deadline jobname.\nCheck your Deadline jobname template in the Project Settings.")

        return jobName

    @err_catcher(name=__name__)
    def processHoudiniPath(self, origin: Any, jobOutputFile: str) -> str:
        """Process Houdini output path, replacing $F4 with padding and expanding variables.
        
        Args:
            origin: State instance with optional node reference
            jobOutputFile: Output file path with Houdini variables
            
        Returns:
            Processed file path with correct frame padding
        """
        jobOutputFile = jobOutputFile.replace("$F4", "#" * self.core.framePadding)
        if getattr(origin, "node", None):
            jobOutputFile = jobOutputFile.replace("$OS", origin.node.name())

        jobOutputFile = self.hou.expandString(jobOutputFile)
        if jobOutputFile.startswith("\\") and not jobOutputFile.startswith("\\\\"):
            jobOutputFile = "\\" + jobOutputFile

        return jobOutputFile

    @err_catcher(name=__name__)
    def sm_render_submitJob(
        self,
        origin: Any,
        jobOutputFile: str,
        parent: Any,
        files: Optional[List[str]] = None,
        isSecondJob: bool = False,
        prio: Optional[int] = None,
        frames: Optional[str] = None,
        handleMaster: bool = False,
        details: Optional[Dict[str, Any]] = None,
        allowCleanup: bool = True,
        jobnameSuffix: Optional[str] = None,
        useBatch: Optional[bool] = None,
        sceneDescription: Optional[str] = None,
        skipSubmission: bool = False
    ) -> Any:
        """Submit render job to Deadline with comprehensive configuration.
        
        Handles various render types including scene descriptions (mantra, redshift, etc),
        high priority sub-jobs, master version handling, dependencies, and app-specific
        submission (Houdini, Maya, Nuke, Max, 3dsMax, Blender).
        
        Args:
            origin: Render state instance
            jobOutputFile: Output file path for rendered frames
            parent: Parent state for dependency configuration
            files: Optional list of additional files to submit
            isSecondJob: If True, submitting high priority sub-job
            prio: Custom priority override
            frames: Custom frame range override
            handleMaster: If True, handle master version submission
            details: Optional context dictionary for job name resolution
            allowCleanup: If True, allow cleanup job submission
            jobnameSuffix: Optional suffix to append to job name
            useBatch: If True, use batch submissions
            sceneDescription: Renderer for scene description export (mantra/redshift/arnold/vray/3delight)
            skipSubmission: If True, prepare data but don't submit
            
        Returns:
            Result string/dict from Deadline submission or error message
        """
        if self.core.appPlugin.pluginName == "Houdini":
            jobOutputFile = self.processHoudiniPath(origin, jobOutputFile)

        homeDir = (
            self.CallDeadlineCommand(["-GetCurrentUserHomeDirectory"])
        )

        if homeDir is False:
            return "Execute Canceled: Deadline is not installed"

        homeDir = homeDir.replace("\r", "").replace("\n", "")

        if parent:
            dependencies = parent.dependencies
        else:
            dependencies = []

        jobOutputFileOrig = jobOutputFile
        if sceneDescription:
            jobOutputFile = self.sceneDescriptions[sceneDescription]["getOutputPath"](origin, jobOutputFile)
            if self.core.appPlugin.pluginName == "Houdini":
                jobOutputFile = self.processHoudiniPath(origin, jobOutputFile)

        jobName = self.getJobName(details, origin)
        rangeType = origin.cb_rangeType.currentText()
        frameRange = origin.getFrameRange(rangeType)
        if rangeType != "Expression":
            startFrame, endFrame = frameRange
            if rangeType == "Single Frame":
                endFrame = startFrame
            frameStr = "%s-%s" % (int(startFrame), int(endFrame))
        else:
            frameStr = ",".join([str(x) for x in frameRange])

        renderSecondJob = False
        if isSecondJob:
            jobPrio = prio
            frameStr = frames
            jobName += "_high_prio"
        else:
            if (
                hasattr(origin, "gb_prioJob")
                and not origin.gb_prioJob.isHidden()
                and origin.gb_prioJob.isChecked()
            ):
                renderSecondJob = True
                sndPrio = origin.sp_highPrio.value()

                resolvedFrames = self.core.resolveFrameExpression(frameStr)
                first = resolvedFrames[0]
                middle = resolvedFrames[int((len(resolvedFrames) - 1)/2)]
                last = resolvedFrames[-1]
                sndFrames = origin.e_highPrioFrames.text()

                sndFrames = sndFrames.format(first=first, middle=middle, last=last)
                sndResolved = self.core.resolveFrameExpression(sndFrames)
                frameStr = ",".join([str(f) for f in resolvedFrames if int(f) not in sndResolved])
                highPrioResult = self.sm_render_submitJob(
                    origin,
                    jobOutputFileOrig,
                    parent,
                    files=None,
                    isSecondJob=True,
                    prio=sndPrio,
                    frames=sndFrames,
                    handleMaster=handleMaster,
                    details=details,
                    allowCleanup=allowCleanup and bool(not frameStr),
                    jobnameSuffix=jobnameSuffix,
                    useBatch=useBatch,
                    sceneDescription=sceneDescription,
                    skipSubmission=skipSubmission,
                )
                if not frameStr:
                    return highPrioResult

            jobPrio = origin.sp_rjPrio.value()

        submitScene = self.core.getConfig(
            "deadline", "submitScenes", dft=True, config="project"
        )
        jobPool = origin.cb_dlPool.currentText()
        jobSndPool = origin.cb_sndPool.currentText()
        jobGroup = origin.cb_dlGroup.currentText()
        
        jobTimeOut = str(origin.sp_rjTimeout.value())
        jobMachineLimit = str(origin.sp_machineLimit.value())
        jobFramesPerTask = origin.sp_rjFramesPerTask.value()
        jobBatchName = jobName.replace("_high_prio", "")
        suspended = origin.chb_rjSuspended.isChecked()
        if (
            hasattr(origin, "w_dlConcurrentTasks")
            and not origin.w_dlConcurrentTasks.isHidden()
        ):
            jobConcurrentTasks = origin.sp_dlConcurrentTasks.value()
        else:
            jobConcurrentTasks = None

        # Create submission info file

        jobInfos = {}
        jobInfos["Name"] = jobName
        if sceneDescription:
            jobInfos["Name"] += self.sceneDescriptions[sceneDescription]["suffix"]

        if jobnameSuffix:
            jobInfos["Name"] += jobnameSuffix

        jobInfos["Pool"] = jobPool
        jobInfos["SecondaryPool"] = jobSndPool
        jobInfos["Group"] = jobGroup
        jobInfos["Priority"] = jobPrio
        jobInfos["TaskTimeoutMinutes"] = jobTimeOut
        jobInfos["MachineLimit"] = jobMachineLimit
        jobInfos["Frames"] = frameStr
        jobInfos["ChunkSize"] = jobFramesPerTask
        jobInfos["OutputFilename0"] = jobOutputFile
        self.addEnvironmentItem(jobInfos, "prism_project", self.core.prismIni.replace("\\", "/"))
        self.addEnvironmentItem(jobInfos, "prism_source_scene", self.core.getCurrentFileName())
        if os.getenv("PRISM_LAUNCH_ENV"):
            envData = self.core.configs.readJson(data=os.getenv("PRISM_LAUNCH_ENV"))
            for item in envData.items():
                self.addEnvironmentItem(jobInfos, item[0], item[1])

        if suspended:
            jobInfos["InitialStatus"] = "Suspended"

        if jobConcurrentTasks:
            jobInfos["ConcurrentTasks"] = jobConcurrentTasks

        if hasattr(origin, "chb_tileJob") and origin.chb_tileJob.isChecked() and not origin.w_tileJob.isHidden():
            jobInfos["Name"] += " - Tile Render"
            jobInfos["TileJob"] = True
            rows = int(origin.cb_tileJob.currentText().split("x")[0])
            jobInfos["TileJobTileCount"] = rows**2
            # jobInfos["TileJobTilesInX"] = rows
            # jobInfos["TileJobTilesInY"] = rows
            jobInfos["TileJobFrame"] = startFrame
            jobInfos["OverrideTaskExtraInfoNames"] = "false"

        if sceneDescription or handleMaster or useBatch or jobInfos.get("TileJob") or renderSecondJob or isSecondJob:
            if jobInfos.get("TileJob"):
                jobBatchName += " (%s tiles)" % rows**2

            jobInfos["BatchName"] = jobBatchName

        if sceneDescription:
            sdePool = os.getenv("PRISM_DEADLINE_SCENE_DESCRIPTION_EXPORT_POOL")
            if sdePool:
                jobInfos["Pool"] = sdePool

            sde2ndPool = os.getenv("PRISM_DEADLINE_SCENE_DESCRIPTION_EXPORT_2NDPOOL")
            if sde2ndPool:
                jobInfos["SecondaryPool"] = sde2ndPool

            sdeGroup = os.getenv("PRISM_DEADLINE_SCENE_DESCRIPTION_EXPORT_GROUP")
            if sdeGroup:
                jobInfos["Group"] = sdeGroup

        if len(dependencies) > 0:
            depType = dependencies[0]["type"]
            jobInfos["IsFrameDependent"] = "false" if depType == "job" else "true"
            if depType in ["job", "frame"]:
                jobids = []
                for dep in dependencies:
                    jobids += dep["jobids"]

                jobInfos["JobDependencies"] = ",".join(jobids)
                if depType == "frame":
                    jobInfos["FrameDependencyOffsetStart"] = dependencies[0]["offset"]

            elif depType == "file":
                jobInfos["ScriptDependencies"] = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "DeadlineDependency.py")
                )

        # Create plugin info file

        pluginInfos = {}
        pluginInfos["Build"] = "64bit"

        if hasattr(origin, "w_dlGPUpt") and not origin.w_dlGPUpt.isHidden():
            pluginInfos["GPUsPerTask"] = origin.sp_dlGPUpt.value()

        if hasattr(origin, "w_dlGPUdevices") and not origin.w_dlGPUdevices.isHidden():
            pluginInfos["GPUsSelectDevices"] = origin.le_dlGPUdevices.text()

        if not submitScene:
            pluginInfos["SceneFile"] = self.core.getCurrentFileName()

        if hasattr(origin, "chb_tileJob") and origin.chb_tileJob.isChecked() and not origin.w_tileJob.isHidden():
            base, ext = os.path.splitext(jobOutputFile)
            del jobInfos["OutputFilename0"]
            del jobInfos["ChunkSize"]
            del jobInfos["Frames"]
            if origin.chb_resOverride.isChecked():
                res = [origin.sp_resWidth.value(), origin.sp_resHeight.value()]
            else:
                res = self.core.appPlugin.getResolution()

            jobInfos["AssembledRenderWidth"] = res[0]
            jobInfos["AssembledRenderHeight"] = res[1]
            aovs = [""]
        #    if self.core.appPlugin.pluginName == "3dsMax":
        #        aovs += self.core.appPlugin.sm_render_getAovNames(rsFilter=True)

            tileWidth = int(jobInfos["AssembledRenderWidth"] / rows)
            tileHeight = int(jobInfos["AssembledRenderHeight"] / rows)
            lastTileWidth = jobInfos["AssembledRenderWidth"] - (tileWidth * (rows-1))
            lastTileHeight = jobInfos["AssembledRenderHeight"] - (tileHeight * (rows-1))

            for idx, aov in enumerate(aovs):
                for row in range(rows):
                    for column in range(rows):
                        tileStr = "_tile_%sx%s_%sx%s_" % (column+1, row+1, rows, rows)
                        tileNum = (row*rows)+(column)
                        curTileWidth = tileWidth if column != (rows-1) else lastTileWidth
                        curTileHeight = tileHeight if row != (rows-1) else lastTileHeight
                        # tileOutname = base + tileStr + ".%04d" % startFrame + ext

                        if aov:
                            aovBase = os.path.join(os.path.dirname(os.path.dirname(base)), aov, os.path.basename(base).replace("beauty", aov).replace("Beauty", aov))
                            tileOutname = aovBase + tileStr + "." + ext
                            pluginInfos["RegionReFilename%s_%s" % (tileNum, idx-1)] = tileOutname
                        else:
                            tileOutname = base + tileStr + "." + ext
                            pluginInfos["RegionTop%s" % tileNum] = int(tileHeight * row)
                            pluginInfos["RegionBottom%s" % tileNum] = int(pluginInfos["RegionTop%s" % tileNum] + curTileHeight)
                            pluginInfos["RegionLeft%s" % tileNum] = int(tileWidth * column)
                            pluginInfos["RegionRight%s" % tileNum] = int(pluginInfos["RegionLeft%s" % tileNum] + curTileWidth)
                            pluginInfos["RegionFilename%s" % tileNum] = tileOutname

                        jobInfos["OutputFilename%sTile%s" % (idx, tileNum)] = tileOutname

            pluginInfos["RegionType"] = "CROP"
            pluginInfos["RegionPadding"] = 0
            pluginInfos["RegionRendering"] = 1
            if len(aovs) > 1:
                pluginInfos["RenderElementTiles"] = 1

        dlParams = {
            "jobInfos": jobInfos,
            "pluginInfos": pluginInfos,
            "jobInfoFile": "",
            "pluginInfoFile": "",
            "arguments": files or getattr(self.core.appPlugin, "getCurrentSceneFiles", self.getCurrentSceneFiles)(origin),
            "sceneDescription": sceneDescription,
            "details": details,
        }
        getattr(
            self.core.appPlugin, "sm_render_getDeadlineParams", lambda x, y, z: None
        )(origin, dlParams, homeDir)
        self.core.callback(
            "sm_render_getDeadlineParams", args=[origin, dlParams, homeDir]
        )

        if "OutputFilename0" in jobInfos:
            jobOutputFile = jobInfos["OutputFilename0"]

        if len(dependencies) > 0 and dependencies[0]["type"] == "file":
            dependencyFile = os.path.join(homeDir, "temp", "dependencies.txt")
            fileHandle = open(dependencyFile, "w")

            for dependency in dependencies:
                fileHandle.write(str(dependency["offset"]) + "\n")
                fileHandle.write(str(dependency["filepath"]) + "\n")

            fileHandle.close()

        arguments = []
        arguments.append(dlParams["jobInfoFile"])
        arguments.append(dlParams["pluginInfoFile"])

        if submitScene:
            if dlParams["arguments"]:
                for arg in dlParams["arguments"]:
                    arguments.append(arg)

        if "dependencyFile" in locals():
            arguments.append(dependencyFile)

        result = None
        jobId = None
        skipNonPrioExport = renderSecondJob and (sceneDescription and not self.sceneDescriptions[sceneDescription].get("filePerFrame", True))
        if (not skipSubmission) and (not skipNonPrioExport):
            result = self.deadlineSubmitJob(jobInfos, pluginInfos, arguments)
            self.registerSubmittedJob(origin, result, data=dlParams)
            jobId = self.getJobIdFromSubmitResult(result)
        elif skipNonPrioExport:
            jobId = self.getJobIdFromSubmitResult(highPrioResult)

        if (jobId or skipSubmission or skipNonPrioExport) and sceneDescription:
            result = self.sceneDescriptions[sceneDescription]["submitFunction"](
                origin,
                jobId=jobId,
                jobOutputFile=jobOutputFile,
                jobOutputFileOrig=jobOutputFileOrig,
                allowCleanup=allowCleanup,
                jobParams=dlParams,
            )

        if result:
            jobId = self.getJobIdFromSubmitResult(result)
            if dlParams["jobInfos"].get("TileJob"):
                if origin.chb_resOverride.isChecked():
                    res = [origin.sp_resWidth.value(), origin.sp_resHeight.value()]
                elif "width" in dlParams["details"]:
                    res = [dlParams["details"]["width"], dlParams["details"]["height"]]
                else:
                    res = self.core.appPlugin.getResolution()

                if "tilesY" in dlParams["details"]:
                    rows = dlParams["details"]["tilesY"]

                self.submitDraftTileAssemblerJob(
                    jobName=dlParams["jobInfos"]["Name"],
                    jobOutput=jobOutputFile,
                    jobPool=dlParams["jobInfos"]["Pool"],
                    jobSndPool=dlParams["jobInfos"]["SecondaryPool"],
                    jobGroup=dlParams["jobInfos"]["Group"],
                    jobPrio=dlParams["jobInfos"]["Priority"],
                    jobTimeOut=dlParams["jobInfos"]["TaskTimeoutMinutes"],
                    jobMachineLimit=dlParams["jobInfos"]["MachineLimit"],
                    jobConcurrentTasks=dlParams["jobInfos"].get("ConcurrentTasks"),
                    jobBatchName=dlParams["jobInfos"].get("BatchName"),
                    suspended=dlParams["jobInfos"].get("InitialStatus") == "Suspended",
                    state=origin,
                    rows=rows,
                    resX=res[0],
                    resY=res[1],
                    startFrame=startFrame,
                    jobDependencies=[jobId],
                    cropped=False
                )

                self.submitDraftTileAssemblerJob(
                    jobName=dlParams["jobInfos"]["Name"],
                    jobOutput=jobOutputFile,
                    jobPool=dlParams["jobInfos"]["Pool"],
                    jobSndPool=dlParams["jobInfos"]["SecondaryPool"],
                    jobGroup=dlParams["jobInfos"]["Group"],
                    jobPrio=dlParams["jobInfos"]["Priority"],
                    jobTimeOut=dlParams["jobInfos"]["TaskTimeoutMinutes"],
                    jobMachineLimit=dlParams["jobInfos"]["MachineLimit"],
                    jobConcurrentTasks=dlParams["jobInfos"].get("ConcurrentTasks"),
                    jobBatchName=dlParams["jobInfos"].get("BatchName"),
                    suspended=dlParams["jobInfos"].get("InitialStatus") == "Suspended",
                    state=origin,
                    rows=rows,
                    resX=res[0],
                    resY=res[1],
                    startFrame=startFrame,
                    jobDependencies=[jobId],
                    cropped=True,
                )

            if jobId and handleMaster and not isSecondJob:
                self.handleMaster(origin, handleMaster, jobId, jobOutputFileOrig, jobName)

        return result

    @err_catcher(name=__name__)
    def registerSubmittedJob(self, state: Any, submitResult: Any, data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Register submitted Deadline job ID with state for dependency tracking.
        
        Args:
            state: State instance that submitted the job
            submitResult: Deadline command output containing job ID
            data: Optional dictionary with job submission data
            
        Returns:
            Extracted job ID or None if not found
        """
        jobId = self.getJobIdFromSubmitResult(submitResult)
        if not jobId:
            return

        if state.uuid not in state.stateManager.submittedDlJobs:
            state.stateManager.submittedDlJobs[state.uuid] = []

        state.stateManager.submittedDlJobs[state.uuid].append(jobId)
        state.stateManager.submittedDlJobData[jobId] = data
        return jobId

    @err_catcher(name=__name__)
    def getSubmittedJobIdsFromState(self, sm: Any, stateId: str) -> Optional[List[str]]:
        """Get list of Deadline job IDs submitted by a specific state.
        
        Args:
            sm: State manager instance
            stateId: UUID of state to get job IDs for
            
        Returns:
            List of job IDs or None if state has no submitted jobs
        """
        if not sm.submittedDlJobs:
            return

        if stateId not in sm.submittedDlJobs:
            return

        return sm.submittedDlJobs[stateId]

    @err_catcher(name=__name__)
    def addEnvironmentItem(self, data: Dict[str, Any], key: str, value: str) -> Dict[str, Any]:
        """Add environment variable to Deadline job submission data.
        
        Finds next available EnvironmentKeyValue slot and adds key=value pair.
        
        Args:
            data: Job submission dictionary
            key: Environment variable name
            value: Environment variable value
            
        Returns:
            Updated data dictionary
        """
        idx = 0
        while True:
            k = "EnvironmentKeyValue" + str(idx)
            if k not in data:
                data[k] = "%s=%s" % (key, value)
                break

            idx += 1

        return data

    @err_catcher(name=__name__)
    def handleMaster(self, origin: Any, masterType: str, jobId: str, jobOutputFile: str, jobName: str) -> None:
        """Submit Python job to update master version after render completes.
        
        Creates dependent job that runs Prism Python API to update master version
        (media master or product master) when render job finishes.
        
        Args:
            origin: Render state instance
            masterType: "media" or "product" - type of master to update
            jobId: Parent render job ID for dependency
            jobOutputFile: Output file path to set as master
            jobName: Base job name for master update job
        """
        jobData = origin.stateManager.submittedDlJobData[jobId]
        code = """
import sys

root = \"%s\"
sys.path.append(root + "/Scripts")

import PrismCore
pcore = PrismCore.create(prismArgs=["noUI", "loadProject"])
path = r\"%s\"
""" % (self.core.prismRoot, os.path.expandvars(jobOutputFile))

        if masterType == "media":
            if self.core.appPlugin.appType == "2d":
                mediaType = "2drenders"
            else:
                mediaType = "3drenders"

            masterAction = origin.cb_master.currentText()
            if masterAction == "Set as master":
                code += "pcore.mediaProducts.updateMasterVersion(path, mediaType=\"%s\")" % mediaType
            elif masterAction == "Add to master":
                code += "pcore.mediaProducts.addToMasterVersion(path, mediaType=\"%s\")" % mediaType
        elif masterType == "product":
            code += "pcore.products.updateMasterVersion(path)"

        if jobId:
            masterDep = [jobId]
        else:
            masterDep = None

        prio = os.getenv("PRISM_DEADLINE_MASTER_UPDATE_PRIO")
        if prio:
            prio = int(prio)
        else:
            prio = 80

        jobPool = jobData["jobInfos"]["Pool"]
        umPool = os.getenv("PRISM_DEADLINE_UPDATE_MASTER_POOL")
        if umPool:
            jobPool = umPool

        jobSndPool = jobData["jobInfos"]["SecondaryPool"]
        um2ndPool = os.getenv("PRISM_DEADLINE_UPDATE_MASTER_2NDPOOL")
        if um2ndPool:
            jobSndPool = um2ndPool

        jobGroup = jobData["jobInfos"]["Group"]
        umGroup = os.getenv("PRISM_DEADLINE_UPDATE_MASTER_GROUP")
        if umGroup:
            jobGroup = umGroup

        jobName = jobName + "_updateMaster"
        self.submitPythonJob(
            code=code,
            jobName=jobName,
            jobPrio=prio,
            jobPool=jobPool,
            jobSndPool=jobSndPool,
            jobGroup=jobGroup,
            jobTimeOut=jobData["jobInfos"]["TaskTimeoutMinutes"],
            jobMachineLimit=jobData["jobInfos"]["MachineLimit"],
            jobComment="Prism-Submission-Update_Master",
            jobBatchName=jobData["jobInfos"].get("BatchName"),
            frames="1",
            suspended=jobData["jobInfos"].get("InitialStatus") == "Suspended",
            jobDependencies=masterDep,
            state=origin,
        )

    @err_catcher(name=__name__)
    def submitSceneDescriptionMantra(self, origin: Any, jobId: Optional[str], jobOutputFile: str, jobOutputFileOrig: str, allowCleanup: bool, jobParams: Dict[str, Any]) -> Any:
        """Submit Mantra .ifd scene description render job to Deadline.
        
        Args:
            origin: Render state instance
            jobId: Export job ID for dependency (if using job dependencies)
            jobOutputFile: Path to .ifd scene description file
            jobOutputFileOrig: Original output path for final renders
            allowCleanup: If True, submit cleanup job to delete .ifd files
            jobParams: Job configuration dictionary from parent submission
            
        Returns:
            Deadline submission result
        """
        if self.useScriptDependencies():
            dep = [{"offset": 0, "filepath": jobOutputFile, "type": "file"}]
        else:
            dep = []
            if jobId:
                dep.append({"jobids": [jobId], "type": "job"})

        args = [jobOutputFile, jobOutputFileOrig]
        if self.core.getConfig(
            "render", "MantraCleanupJob", dft=True, config="project"
        ) and allowCleanup:
            cleanupScript = origin.curRenderer.getCleanupScript()
        else:
            cleanupScript = None

        jobData = jobParams
        basename = jobData["jobInfos"]["Name"][:-len(self.sceneDescriptions["mantra"]["suffix"])]
        jobPool = jobData["jobInfos"]["Pool"]
        sdrPool = os.getenv("PRISM_DEADLINE_SCENE_DESCRIPTION_RENDER_POOL")
        if sdrPool:
            jobPool = sdrPool

        jobSndPool = jobData["jobInfos"]["SecondaryPool"]
        sdr2ndPool = os.getenv("PRISM_DEADLINE_SCENE_DESCRIPTION_RENDER_2NDPOOL")
        if sdr2ndPool:
            jobSndPool = sdr2ndPool

        jobGroup = jobData["jobInfos"]["Group"]
        sdrGroup = os.getenv("PRISM_DEADLINE_SCENE_DESCRIPTION_RENDER_GROUP")
        if sdrGroup:
            jobGroup = sdrGroup

        result = self.submitMantraJob(
            jobName=basename + "_render",
            jobOutput=jobOutputFileOrig,
            jobPrio=jobData["jobInfos"]["Priority"],
            jobPool=jobPool,
            jobSndPool=jobSndPool,
            jobGroup=jobGroup,
            jobTimeOut=jobData["jobInfos"]["TaskTimeoutMinutes"],
            jobMachineLimit=jobData["jobInfos"]["MachineLimit"],
            jobFramesPerTask=jobData["jobInfos"]["ChunkSize"],
            jobConcurrentTasks=jobData["jobInfos"].get("ConcurrentTasks"),
            jobBatchName=jobData["jobInfos"].get("BatchName"),
            frames=jobData["jobInfos"]["Frames"],
            suspended=jobData["jobInfos"].get("InitialStatus") == "Suspended",
            dependencies=dep,
            archivefile=jobOutputFile,
            args=args,
            cleanupScript=cleanupScript,
            state=origin,
        )

        return result

    @err_catcher(name=__name__)
    def submitSceneDescription3Delight(self, origin: Any, jobId: Optional[str], jobOutputFile: str, jobOutputFileOrig: str, allowCleanup: bool, jobParams: Dict[str, Any]) -> Any:
        """Submit 3Delight .nsi scene description render job to Deadline.
        
        Args:
            origin: Render state instance
            jobId: Export job ID for dependency (if using job dependencies)
            jobOutputFile: Path to .nsi scene description file
            jobOutputFileOrig: Original output path for final renders
            allowCleanup: If True, submit cleanup job to delete .nsi files
            jobParams: Job configuration dictionary from parent submission
            
        Returns:
            Deadline submission result
        """
        code = origin.curRenderer.getNsiRenderScript()
        if self.useScriptDependencies():
            nsiDep = [{"offset": 0, "filepath": jobOutputFile, "type": "file"}]
        else:
            nsiDep = []
            if jobId:
                nsiDep.append({"jobids": [jobId], "type": "job"})

        dlpath = os.getenv("DELIGHT")
        environment = [["DELIGHT", dlpath]]
        args = [jobOutputFile, jobOutputFileOrig]
        jobData = jobParams
        basename = jobData["jobInfos"]["Name"][:-len(self.sceneDescriptions["3delight"]["suffix"])]
        jobPool = jobData["jobInfos"]["Pool"]
        sdrPool = os.getenv("PRISM_DEADLINE_SCENE_DESCRIPTION_RENDER_POOL")
        if sdrPool:
            jobPool = sdrPool

        jobSndPool = jobData["jobInfos"]["SecondaryPool"]
        sdr2ndPool = os.getenv("PRISM_DEADLINE_SCENE_DESCRIPTION_RENDER_2NDPOOL")
        if sdr2ndPool:
            jobSndPool = sdr2ndPool

        jobGroup = jobData["jobInfos"]["Group"]
        sdrGroup = os.getenv("PRISM_DEADLINE_SCENE_DESCRIPTION_RENDER_GROUP")
        if sdrGroup:
            jobGroup = sdrGroup

        result = self.submitPythonJob(
            code=code,
            jobName=basename + "_render",
            jobOutput=jobOutputFileOrig,
            jobPrio=jobData["jobInfos"]["Priority"],
            jobPool=jobPool,
            jobSndPool=jobSndPool,
            jobGroup=jobGroup,
            jobTimeOut=jobData["jobInfos"]["TaskTimeoutMinutes"],
            jobMachineLimit=jobData["jobInfos"]["MachineLimit"],
            jobFramesPerTask=jobData["jobInfos"]["ChunkSize"],
            jobConcurrentTasks=jobData["jobInfos"].get("ConcurrentTasks"),
            jobBatchName=jobData["jobInfos"].get("BatchName"),
            frames=jobData["jobInfos"]["Frames"],
            suspended=jobData["jobInfos"].get("InitialStatus") == "Suspended",
            dependencies=nsiDep,
            environment=environment,
            args=args,
            state=origin,
        )

        if self.core.getConfig(
            "render", "3DelightCleanupJob", dft=True, config="project"
        ) and allowCleanup:
            cleanupScript = origin.curRenderer.getCleanupScript()
        else:
            cleanupScript = None

        if cleanupScript:
            arguments = [args[0]]
            depId = self.getJobIdFromSubmitResult(result)
            if depId:
                cleanupDep = [depId]
            else:
                cleanupDep = None

            result = self.submitCleanupScript(
                jobName=basename,
                jobPool=jobData["jobInfos"]["Pool"],
                jobSndPool=jobData["jobInfos"]["SecondaryPool"],
                jobGroup=jobData["jobInfos"]["Group"],
                jobPrio=jobData["jobInfos"]["Priority"],
                jobTimeOut=jobData["jobInfos"]["TaskTimeoutMinutes"],
                jobMachineLimit=jobData["jobInfos"]["MachineLimit"],
                jobBatchName=jobData["jobInfos"].get("BatchName"),
                suspended=jobData["jobInfos"].get("InitialStatus") == "Suspended",
                jobDependencies=cleanupDep,
                environment=environment,
                cleanupScript=cleanupScript,
                arguments=arguments,
                state=origin,
            )

        return result

    @err_catcher(name=__name__)
    def submitSceneDescriptionRedshift(self, origin: Any, jobId: Optional[str], jobOutputFile: str, jobOutputFileOrig: str, allowCleanup: bool, jobParams: Dict[str, Any]) -> Any:
        """Submit Redshift .rs scene description render job to Deadline.
        
        Args:
            origin: Render state instance
            jobId: Export job ID for dependency (if using job dependencies)
            jobOutputFile: Path to .rs scene description file
            jobOutputFileOrig: Original output path for final renders
            allowCleanup: If True, submit cleanup job to delete .rs files
            jobParams: Job configuration dictionary from parent submission
            
        Returns:
            Deadline submission result
        """
        if self.useScriptDependencies():
            rsDep = [{"offset": 0, "filepath": jobOutputFile, "type": "file"}]
        else:
            rsDep = []
            if jobId:
                rsDep.append({"jobids": [jobId], "type": "job"})

        args = [jobOutputFile, jobOutputFileOrig]
        gpusPerTask = origin.sp_dlGPUpt.value()
        gpuDevices = origin.le_dlGPUdevices.text()
        if self.core.getConfig(
            "render", "RedshiftCleanupJob", dft=True, config="project"
        ) and allowCleanup:
            cleanupScript = self.getRedshiftCleanupScript()
        else:
            cleanupScript = None

        jobData = jobParams
        basename = jobData["jobInfos"]["Name"][:-len(self.sceneDescriptions["redshift"]["suffix"])]
        jobPool = jobData["jobInfos"]["Pool"]
        sdrPool = os.getenv("PRISM_DEADLINE_SCENE_DESCRIPTION_RENDER_POOL")
        if sdrPool:
            jobPool = sdrPool

        jobSndPool = jobData["jobInfos"]["SecondaryPool"]
        sdr2ndPool = os.getenv("PRISM_DEADLINE_SCENE_DESCRIPTION_RENDER_2NDPOOL")
        if sdr2ndPool:
            jobSndPool = sdr2ndPool

        jobGroup = jobData["jobInfos"]["Group"]
        sdrGroup = os.getenv("PRISM_DEADLINE_SCENE_DESCRIPTION_RENDER_GROUP")
        if sdrGroup:
            jobGroup = sdrGroup

        result = self.submitRedshiftJob(
            jobName=basename + "_render",
            jobOutput=jobOutputFileOrig,
            jobPrio=jobData["jobInfos"]["Priority"],
            jobPool=jobPool,
            jobSndPool=jobSndPool,
            jobGroup=jobGroup,
            jobTimeOut=jobData["jobInfos"]["TaskTimeoutMinutes"],
            jobMachineLimit=jobData["jobInfos"]["MachineLimit"],
            jobFramesPerTask=jobData["jobInfos"]["ChunkSize"],
            jobConcurrentTasks=jobData["jobInfos"].get("ConcurrentTasks"),
            jobBatchName=jobData["jobInfos"].get("BatchName"),
            frames=jobData["jobInfos"]["Frames"],
            suspended=jobData["jobInfos"].get("InitialStatus") == "Suspended",
            dependencies=rsDep,
            archivefile=jobOutputFile,
            gpusPerTask=gpusPerTask,
            gpuDevices=gpuDevices,
            args=args,
            cleanupScript=cleanupScript,
            state=origin,
        )
        return result

    @err_catcher(name=__name__)
    def submitSceneDescriptionArnold(self, origin: Any, jobId: Optional[str], jobOutputFile: str, jobOutputFileOrig: str, allowCleanup: bool, jobParams: Dict[str, Any]) -> Any:
        """Submit Arnold .ass scene description render job to Deadline.
        
        Args:
            origin: Render state instance
            jobId: Export job ID for dependency (if using job dependencies)
            jobOutputFile: Path to .ass scene description file
            jobOutputFileOrig: Original output path for final renders
            allowCleanup: If True, submit cleanup job to delete .ass files
            jobParams: Job configuration dictionary from parent submission
            
        Returns:
            Deadline submission result
        """
        if self.useScriptDependencies():
            rsDep = [{"offset": 0, "filepath": jobOutputFile, "type": "file"}]
        else:
            rsDep = []
            if jobId:
                rsDep.append({"jobids": [jobId], "type": "job"})

        args = [jobOutputFile, jobOutputFileOrig]
        if self.core.getConfig(
            "render", "ArnoldCleanupJob", dft=True, config="project"
        ) and allowCleanup:
            cleanupScript = origin.curRenderer.getCleanupScript()
        else:
            cleanupScript = None

        jobData = jobParams
        basename = jobData["jobInfos"]["Name"][:-len(self.sceneDescriptions["arnold"]["suffix"])]
        jobPool = jobData["jobInfos"]["Pool"]
        sdrPool = os.getenv("PRISM_DEADLINE_SCENE_DESCRIPTION_RENDER_POOL")
        if sdrPool:
            jobPool = sdrPool

        jobSndPool = jobData["jobInfos"]["SecondaryPool"]
        sdr2ndPool = os.getenv("PRISM_DEADLINE_SCENE_DESCRIPTION_RENDER_2NDPOOL")
        if sdr2ndPool:
            jobSndPool = sdr2ndPool

        jobGroup = jobData["jobInfos"]["Group"]
        sdrGroup = os.getenv("PRISM_DEADLINE_SCENE_DESCRIPTION_RENDER_GROUP")
        if sdrGroup:
            jobGroup = sdrGroup

        result = self.submitArnoldJob(
            jobName=basename + "_render",
            jobOutput=jobOutputFileOrig,
            jobPrio=jobData["jobInfos"]["Priority"],
            jobPool=jobPool,
            jobSndPool=jobSndPool,
            jobGroup=jobGroup,
            jobTimeOut=jobData["jobInfos"]["TaskTimeoutMinutes"],
            jobMachineLimit=jobData["jobInfos"]["MachineLimit"],
            jobFramesPerTask=jobData["jobInfos"]["ChunkSize"],
            jobConcurrentTasks=jobData["jobInfos"].get("ConcurrentTasks"),
            jobBatchName=jobData["jobInfos"].get("BatchName"),
            frames=jobData["jobInfos"]["Frames"],
            suspended=jobData["jobInfos"].get("InitialStatus") == "Suspended",
            dependencies=rsDep,
            archivefile=jobOutputFile,
            args=args,
            cleanupScript=cleanupScript,
            state=origin,
        )
        return result

    @err_catcher(name=__name__)
    def submitSceneDescriptionVray(self, origin: Any, jobId: Optional[str], jobOutputFile: str, jobOutputFileOrig: str, allowCleanup: bool, jobParams: Dict[str, Any]) -> Any:
        """Submit V-Ray .vrscene scene description render job to Deadline.
        
        Args:
            origin: Render state instance
            jobId: Export job ID for dependency (if using job dependencies)
            jobOutputFile: Path to .vrscene scene description file
            jobOutputFileOrig: Original output path for final renders
            allowCleanup: If True, submit cleanup job to delete .vrscene files
            jobParams: Job configuration dictionary from parent submission
            
        Returns:
            Deadline submission result
        """
        if self.useScriptDependencies():
            rsDep = [{"offset": 0, "filepath": jobOutputFile, "type": "file"}]
        else:
            rsDep = []
            if jobId:
                rsDep.append({"jobids": [jobId], "type": "job"})

        args = [jobOutputFile, jobOutputFileOrig]
        if self.core.getConfig(
            "render", "VrayCleanupJob", dft=True, config="project"
        ) and allowCleanup:
            cleanupScript = self.getVrayCleanupScript()
        else:
            cleanupScript = None

        jobData = jobParams
        basename = jobData["jobInfos"]["Name"][:-len(self.sceneDescriptions["vray"]["suffix"])]
        jobPool = jobData["jobInfos"]["Pool"]
        sdrPool = os.getenv("PRISM_DEADLINE_SCENE_DESCRIPTION_RENDER_POOL")
        if sdrPool:
            jobPool = sdrPool

        jobSndPool = jobData["jobInfos"]["SecondaryPool"]
        sdr2ndPool = os.getenv("PRISM_DEADLINE_SCENE_DESCRIPTION_RENDER_2NDPOOL")
        if sdr2ndPool:
            jobSndPool = sdr2ndPool

        jobGroup = jobData["jobInfos"]["Group"]
        sdrGroup = os.getenv("PRISM_DEADLINE_SCENE_DESCRIPTION_RENDER_GROUP")
        if sdrGroup:
            jobGroup = sdrGroup

        result = self.submitVrayJob(
            jobName=basename + "_render",
            jobOutput=jobOutputFileOrig,
            jobPrio=jobData["jobInfos"]["Priority"],
            jobPool=jobPool,
            jobSndPool=jobSndPool,
            jobGroup=jobGroup,
            jobTimeOut=jobData["jobInfos"]["TaskTimeoutMinutes"],
            jobMachineLimit=jobData["jobInfos"]["MachineLimit"],
            jobFramesPerTask=jobData["jobInfos"]["ChunkSize"],
            jobConcurrentTasks=jobData["jobInfos"].get("ConcurrentTasks"),
            jobBatchName=jobData["jobInfos"].get("BatchName"),
            frames=jobData["jobInfos"]["Frames"],
            suspended=jobData["jobInfos"].get("InitialStatus") == "Suspended",
            dependencies=rsDep,
            archivefile=jobOutputFile,
            args=args,
            cleanupScript=cleanupScript,
            state=origin,
        )
        return result

    @err_catcher(name=__name__)
    def getVrayCleanupScript(self) -> str:
        """Get cleanup script for V-Ray.
    
        Returns:
            Cleanup script as a string.
        """
        script = """
import os
import sys
import shutil

vrsceneOutput = sys.argv[-1]

delDir = os.path.dirname(vrsceneOutput)
if os.path.basename(delDir) != "_vrscene":
    raise RuntimeError("invalid vrscene directory: %s" % (delDir))

if os.path.exists(delDir):
    shutil.rmtree(delDir)
    print("task completed successfully")
else:
    print("directory doesn't exist")

"""
        return script

    @err_catcher(name=__name__)
    def getMantraOutputPath(self, origin: Any, jobOutputFile: str) -> str:
        """Get Mantra scene description output path (_ifd subdirectory).
        
        Args:
            origin: Render state instance
            jobOutputFile: Original render output path
            
        Returns:
            Path to .ifd file in _ifd subdirectory
        """
        jobOutputFile = os.path.join(
            os.path.dirname(jobOutputFile), "_ifd", os.path.basename(jobOutputFile)
        )
        jobOutputFile = os.path.splitext(jobOutputFile)[0] + ".ifd"
        return jobOutputFile

    @err_catcher(name=__name__)
    def get3DelightOutputPath(self, origin: Any, jobOutputFile: str) -> str:
        """Get 3Delight scene description output path from renderer.
        
        Args:
            origin: Render state instance
            jobOutputFile: Original render output path
            
        Returns:
            Path to .nsi file
        """
        jobOutputFile = origin.curRenderer.getNsiOutputPath(
            origin, jobOutputFile
        )
        return jobOutputFile

    @err_catcher(name=__name__)
    def getRedshiftOutputPath(self, origin: Any, jobOutputFile: str) -> str:
        """Get Redshift scene description output path (_rs subdirectory).
        
        Args:
            origin: Render state instance
            jobOutputFile: Original render output path
            
        Returns:
            Path to .rs file in _rs subdirectory
        """
        jobOutputFile = os.path.join(
            os.path.dirname(jobOutputFile), "_rs", os.path.basename(jobOutputFile)
        )
        jobOutputFile = os.path.splitext(jobOutputFile)[0] + ".rs"
        return jobOutputFile

    @err_catcher(name=__name__)
    def getArnoldOutputPath(self, origin: Any, jobOutputFile: str) -> str:
        """Get Arnold scene description output path from renderer.
        
        Args:
            origin: Render state instance
            jobOutputFile: Original render output path
            
        Returns:
            Path to .ass file
        """
        jobOutputFile = origin.curRenderer.getAssOutputPath(
            origin, jobOutputFile
        )
        return jobOutputFile

    @err_catcher(name=__name__)
    def getVrayOutputPath(self, origin: Any, jobOutputFile: str) -> str:
        """Get V-Ray scene description output path (_vrscene subdirectory).
        
        Args:
            origin: Render state instance
            jobOutputFile: Original render output path
            
        Returns:
            Path to .vrscene file in _vrscene subdirectory
        """
        jobOutputFile = os.path.join(
            os.path.dirname(jobOutputFile), "_vrscene", os.path.basename(jobOutputFile)
        )
        jobOutputFile = os.path.splitext(jobOutputFile)[0] + ".vrscene"
        return jobOutputFile

    @err_catcher(name=__name__)
    def submitPythonJob(
        self,
        code: str = "",
        version: str = "3.13",
        jobName: Optional[str] = None,
        jobOutput: Optional[str] = None,
        jobPool: str = "None",
        jobSndPool: str = "None",
        jobGroup: str = "None",
        jobPrio: int = 50,
        jobTimeOut: int = 180,
        jobMachineLimit: int = 0,
        jobFramesPerTask: int = 1,
        jobConcurrentTasks: Optional[int] = None,
        jobComment: Optional[str] = None,
        jobBatchName: Optional[str] = None,
        frames: str = "1",
        suspended: bool = False,
        dependencies: Optional[List[Dict[str, Any]]] = None,
        jobDependencies: Optional[List[str]] = None,
        environment: Optional[List[List[str]]] = None,
        args: Optional[List[str]] = None,
        state: Optional[Any] = None,
        extraFiles: Optional[List[str]] = None,
        submitScenefile: bool = False,
        userName: Optional[str] = None,
    ) -> str:
        """Submit Python code execution job to Deadline.
        
        Creates Python script file and submits to Deadline with CommandLine plugin.
        Used for master version updates, cleanup scripts, and custom Python tasks.
        
        Args:
            code: Python code to execute
            version: Python version ("3.13", "3.11", etc)
            jobName: Job name (defaults to current scene filename)
            jobOutput: Output file path for job
            jobPool: Deadline pool name
            jobSndPool: Secondary pool name
            jobGroup: Deadline group name
            jobPrio: Job priority (0-100)
            jobTimeOut: Task timeout in minutes
            jobMachineLimit: Maximum concurrent machines
            jobFramesPerTask: Frames per task (chunk size)
            jobConcurrentTasks: Maximum concurrent tasks
            jobComment: Job comment
            jobBatchName: Batch name for grouping jobs
            frames: Frame range string
            suspended: If True, submit in suspended state
            dependencies: List of file/job/frame dependencies
            jobDependencies: List of job IDs to depend on
            environment: List of [key, value] environment variable pairs
            args: Arguments to pass to Python script
            state: Optional state instance for registration
            extraFiles: Additional files to copy to repository
            submitScenefile: If True, include current scene file
            userName: Deadline username override
            
        Returns:
            Deadline command output with job ID
        """
        homeDir = (
            self.CallDeadlineCommand(["-GetCurrentUserHomeDirectory"])
        )

        if homeDir is False:
            return "Execute Canceled: Deadline is not installed"

        homeDir = homeDir.replace("\r", "").replace("\n", "")

        if not jobName:
            jobName = os.path.splitext(self.core.getCurrentFileName(path=False))[
                0
            ].strip("_")

        scriptFile = os.path.join(
            homeDir, "temp", "%s_%s.py" % (jobName.replace(":", "_").split("/")[-1].split("\\")[-1], int(time.time()))
        )
        with open(scriptFile, "w", encoding='utf-8') as f:
            f.write(code)

        environment = environment or []
        environment.insert(0, ["prism_project", self.core.prismIni.replace("\\", "/")])

        # Create submission info file

        jobInfos = {}

        jobInfos["Name"] = jobName
        jobInfos["Pool"] = jobPool
        jobInfos["SecondaryPool"] = jobSndPool
        jobInfos["Group"] = jobGroup
        jobInfos["Priority"] = jobPrio
        jobInfos["TaskTimeoutMinutes"] = jobTimeOut
        jobInfos["MachineLimit"] = jobMachineLimit
        jobInfos["Frames"] = frames
        jobInfos["ChunkSize"] = jobFramesPerTask
        if userName:
            jobInfos["UserName"] = userName

        for idx, env in enumerate(environment):
            self.addEnvironmentItem(jobInfos, env[0], env[1])

        if os.getenv("PRISM_LAUNCH_ENV"):
            envData = self.core.configs.readJson(data=os.getenv("PRISM_LAUNCH_ENV"))
            for item in envData.items():
                self.addEnvironmentItem(jobInfos, item[0], item[1])

        jobInfos["Plugin"] = "Python"
        jobInfos["Comment"] = jobComment or "Prism-Submission-Python"

        if jobOutput:
            jobInfos["OutputFilename0"] = jobOutput

        if suspended:
            jobInfos["InitialStatus"] = "Suspended"

        if jobConcurrentTasks:
            jobInfos["ConcurrentTasks"] = jobConcurrentTasks

        if jobBatchName:
            jobInfos["BatchName"] = jobBatchName

        if dependencies:
            depType = dependencies[0]["type"]
            jobInfos["IsFrameDependent"] = "false" if depType == "job" else "true"
            if depType in ["job", "frame"]:
                jobids = []
                for dep in dependencies:
                    jobids += dep["jobids"]

                jobInfos["JobDependencies"] = ",".join(jobids)
            elif depType == "file":
                jobInfos["ScriptDependencies"] = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "DeadlineDependency.py")
                )

        if jobDependencies:
            jobInfos["JobDependencies"] = ",".join(jobDependencies)

        # Create plugin info file

        pluginInfos = {}

        envKey = "PRISM_DEADLINE_PYTHON_VERSION"
        if envKey in os.environ:
            version = os.environ[envKey]

        pluginInfos["Version"] = version

        # pluginInfos["ScriptFile"] = scriptFile
        pluginInfos["Arguments"] = "<STARTFRAME> <ENDFRAME>"
        if args:
            pluginInfos["Arguments"] += " " + " ".join(args)

        dlParams = {
            "jobInfos": jobInfos,
            "pluginInfos": pluginInfos,
            "jobInfoFile": os.path.join(homeDir, "temp", "python_plugin_info.job"),
            "pluginInfoFile": os.path.join(homeDir, "temp", "python_job_info.job"),
        }

        if dependencies and dependencies[0]["type"] == "file":
            dependencyFile = os.path.join(homeDir, "temp", "dependencies.txt")
            fileHandle = open(dependencyFile, "w")

            for dependency in dependencies:
                fileHandle.write(str(dependency["offset"]) + "\n")
                fileHandle.write(str(dependency["filepath"]) + "\n")

            fileHandle.close()

        arguments = []
        arguments.append(dlParams["jobInfoFile"])
        arguments.append(dlParams["pluginInfoFile"])
        arguments.append(scriptFile)
        if submitScenefile:
            for i in getattr(self.core.appPlugin, "getCurrentSceneFiles", self.getCurrentSceneFiles)(self):
                arguments.append(i)

        if "dependencyFile" in locals():
            arguments.append(dependencyFile)

        if extraFiles:
            arguments += extraFiles

        result = self.deadlineSubmitJob(jobInfos, pluginInfos, arguments)
        if state:
            self.registerSubmittedJob(state, result, dlParams)

        return result

    @err_catcher(name=__name__)
    def submitDraftTileAssemblerJob(
        self,
        jobName: Optional[str] = None,
        jobOutput: Optional[str] = None,
        jobPool: str = "None",
        jobSndPool: str = "None",
        jobGroup: str = "None",
        jobPrio: int = 50,
        jobTimeOut: int = 180,
        jobMachineLimit: int = 0,
        jobFramesPerTask: int = 1,
        jobConcurrentTasks: Optional[int] = None,
        jobComment: Optional[str] = None,
        jobBatchName: Optional[str] = None,
        frames: str = "1",
        suspended: bool = False,
        dependencies: Optional[List[Dict[str, Any]]] = None,
        jobDependencies: Optional[List[str]] = None,
        environment: Optional[List[List[str]]] = None,
        args: Optional[List[str]] = None,
        state: Optional[Any] = None,
        rows: int = 2,
        resX: int = 1920,
        resY: int = 1080,
        startFrame: int = 1,
        cropped: bool = False,
        y_up: bool = False,
        additionalAssemblies: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Submit Draft tile assembler job to stitch tiled renders together.
        
        Used for Redshift tiled rendering to assemble individual tiles into final image.
        Creates Draft config files for each AOV/pass and submits assembly job.
        
        Args:
            jobName: Job name (defaults to current scene filename)
            jobOutput: Output file path for assembled image
            jobPool: Deadline pool name
            jobSndPool: Secondary pool name
            jobGroup: Deadline group name
            jobPrio: Job priority (0-100)
            jobTimeOut: Task timeout in minutes
            jobMachineLimit: Maximum concurrent machines
            jobFramesPerTask: Frames per task (chunk size)
            jobConcurrentTasks: Maximum concurrent tasks
            jobComment: Job comment
            jobBatchName: Batch name for grouping jobs
            frames: Frame range string
            suspended: If True, submit in suspended state
            dependencies: List of file/job/frame dependencies
            jobDependencies: List of job IDs to depend on
            environment: List of [key, value] environment variable pairs
            args: Arguments to pass
            state: Optional state instance for registration
            rows: Number of tile rows/columns (for NxN grid)
            resX: Output image width
            resY: Output image height
            startFrame: Starting frame number
            cropped: If True, only assemble cryptomatte AOV
            y_up: If True, use Y-up coordinate system
            additionalAssemblies: Additional AOVs to assemble
            
        Returns:
            Deadline command output with job ID
        """
        homeDir = (
            self.CallDeadlineCommand(["-GetCurrentUserHomeDirectory"])
        )

        if homeDir is False:
            return "Execute Canceled: Deadline is not installed"

        homeDir = homeDir.replace("\r", "").replace("\n", "")

        if not jobName:
            jobName = os.path.splitext(self.core.getCurrentFileName(path=False))[
                0
            ].strip("_")

        assemblies = []
        if not cropped:
            assemblies.append({"key": "", "path": jobOutput})

        if self.core.appPlugin.pluginName == "3dsMax":
            aovs = self.core.appPlugin.sm_render_getAovNamesRedshiftLightGroups()
            for aov in aovs:
                if aov["aovType"] != "ReferenceTarget:RsBeauty":
                    if (cropped and aov["aovType"] != "ReferenceTarget:RsCryptomatte") or (not cropped and aov["aovType"] == "ReferenceTarget:RsCryptomatte"):
                        filename = os.path.basename(jobOutput).replace("beauty", aov["name"]).replace("Beauty", aov["name"])
                        aovPath = os.path.join(os.path.dirname(os.path.dirname(jobOutput)), aov["name"], filename)
                        assemblies.append({"key": "_" + aov["name"], "path": aovPath})

                if not cropped:
                    for lightAov in aov["lightgroups"]:
                        lightAovName = aov["name"] + "_" + lightAov
                        filename = os.path.basename(jobOutput).replace("beauty", lightAovName).replace("Beauty", lightAovName)
                        aovPath = os.path.join(os.path.dirname(os.path.dirname(jobOutput)), aov["name"], filename)
                        assemblies.append({"key": "_" + lightAovName, "path": aovPath})

        if additionalAssemblies:
            assemblies += additionalAssemblies

        cfgFiles = []
        for idx, assembly in enumerate(assemblies):
            cfgFile = os.path.join(
                homeDir, "temp", "%s%s_%s.txt" % (jobName, assembly["key"], int(time.time()))
            )
            aout = assembly["path"]
            cfgData = {
                "ImageFileName": aout,
                "TileCount": rows**2,
                "TilesCropped": cropped,
                "DistanceAsPixels": True,
                "ImageWidth": resX,
                "ImageHeight": resY,
            }
            base, ext = os.path.splitext(assembly["path"])
            tileWidth = int(resX / rows)
            tileHeight = int(resY / rows)
            lastTileWidth = resX - (tileWidth * (rows-1))
            lastTileHeight = resY - (tileHeight * (rows-1))
            for row in range(rows):
                for column in range(rows):
                    tileStr = "_tile_%sx%s_%sx%s_" % (column+1, row+1, rows, rows)
                    tileNum = (row*rows)+(column)
                    if startFrame is None:
                        frameStr = ""
                    else:
                        frameStr = ".%04d" % startFrame

                    cfgData["Tile%sFileName" % tileNum] = base + tileStr + frameStr + ext
                    # cfgData["Tile%sFileName" % tileNum] = base + tileStr + ext
                    cfgData["Tile%sWidth" % tileNum] = tileWidth if column != (rows-1) else lastTileWidth
                    cfgData["Tile%sHeight" % tileNum] = tileHeight if row != (rows-1) else lastTileHeight
                    cfgData["Tile%sX" % tileNum] = tileWidth * column
                    if y_up:
                        cfgData["Tile%sY" % tileNum] = tileHeight * row
                    else:
                        cfgData["Tile%sY" % tileNum] = resY - ((tileHeight * row) + cfgData["Tile%sHeight" % tileNum])

            with open(cfgFile, "w") as fileHandle:
                for key in cfgData:
                    fileHandle.write("%s=%s\n" % (key, cfgData[key]))

            cfgFiles.append(cfgFile)

        environment = environment or []
        environment.insert(0, ["prism_project", self.core.prismIni.replace("\\", "/")])

        # Create submission info file

        jobInfos = {}

        jobInfos["Name"] = jobName.replace(" - Tile Render", "") + " - Draft Tile Assembly"
        if cropped:
            jobInfos["Name"] += " (cropped)"

        jobInfos["Pool"] = jobPool
        jobInfos["SecondaryPool"] = jobSndPool
        jobInfos["Group"] = jobGroup
        jobInfos["Priority"] = jobPrio
        jobInfos["TaskTimeoutMinutes"] = jobTimeOut
        jobInfos["MachineLimit"] = jobMachineLimit
        if len(assemblies) > 1:
            jobInfos["Frames"] = "0-%s" % (len(assemblies)-1)
        else:
            jobInfos["Frames"] = frames
        jobInfos["ChunkSize"] = jobFramesPerTask
        for idx, env in enumerate(environment):
            self.addEnvironmentItem(jobInfos, env[0], env[1])

        if os.getenv("PRISM_LAUNCH_ENV"):
            envData = self.core.configs.readJson(data=os.getenv("PRISM_LAUNCH_ENV"))
            for item in envData.items():
                self.addEnvironmentItem(jobInfos, item[0], item[1])

        jobInfos["Plugin"] = "DraftTileAssembler"
        jobInfos["Comment"] = jobComment or "Prism-Submission-DraftTileAssembler"

        if jobOutput:
            jobInfos["OutputFilename0"] = jobOutput
            if self.core.appPlugin.pluginName == "3dsMax":
                num = 1
                for idx, assembly in enumerate(assemblies):
                    if assembly["key"]:
                        jobInfos["OutputFilename%s" % (num)] = assembly["path"]
                        num += 1

        if suspended:
            jobInfos["InitialStatus"] = "Suspended"

        if jobConcurrentTasks:
            jobInfos["ConcurrentTasks"] = jobConcurrentTasks

        if jobBatchName:
            jobInfos["BatchName"] = jobBatchName

        if dependencies:
            depType = dependencies[0]["type"]
            jobInfos["IsFrameDependent"] = "false" if depType == "job" else "true"
            if depType in ["job", "frame"]:
                jobids = []
                for dep in dependencies:
                    jobids += dep["jobids"]

                jobInfos["JobDependencies"] = ",".join(jobids)
            elif depType == "file":
                jobInfos["ScriptDependencies"] = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "DeadlineDependency.py")
                )

        if jobDependencies:
            jobInfos["JobDependencies"] = ",".join(jobDependencies)

        # Create plugin info file

        pluginInfos = {
            "CleanupTiles": "false",
            "ErrorOnMissing": "true",
            "MultipleConfigFiles": "true",
            "ErrorOnMissingBackground": "false",
        }

        dlParams = {
            "jobInfos": jobInfos,
            "pluginInfos": pluginInfos,
            "jobInfoFile": os.path.join(homeDir, "temp", "draftTileAssembler_plugin_info.job"),
            "pluginInfoFile": os.path.join(homeDir, "temp", "draftTileAssembler_job_info.job"),
        }

        arguments = []
        arguments.append(dlParams["jobInfoFile"])
        arguments.append(dlParams["pluginInfoFile"])
        arguments += cfgFiles

        result = self.deadlineSubmitJob(jobInfos, pluginInfos, arguments)
        if state:
            self.registerSubmittedJob(state, result, dlParams)

        return result

    @err_catcher(name=__name__)
    def submitMantraJob(
        self,
        jobName: Optional[str] = None,
        jobOutput: Optional[str] = None,
        jobPool: str = "None",
        jobSndPool: str = "None",
        jobGroup: str = "None",
        jobPrio: int = 50,
        jobTimeOut: int = 180,
        jobMachineLimit: int = 0,
        jobFramesPerTask: int = 1,
        jobConcurrentTasks: Optional[int] = None,
        jobComment: Optional[str] = None,
        jobBatchName: Optional[str] = None,
        frames: str = "1",
        suspended: bool = False,
        dependencies: Optional[List[Dict[str, Any]]] = None,
        archivefile: Optional[str] = None,
        environment: Optional[List[List[str]]] = None,
        args: Optional[List[str]] = None,
        cleanupScript: Optional[str] = None,
        state: Optional[Any] = None,
    ) -> str:
        """Submit Mantra .ifd rendering job to Deadline.
        
        Uses Deadline Mantra plugin to render pre-exported .ifd scene description files.
        Optionally submits cleanup job to delete .ifd files after completion.
        
        Args:
            jobName: Job name (defaults to current scene filename)
            jobOutput: Output file path for rendered frames
            jobPool: Deadline pool name
            jobSndPool: Secondary pool name
            jobGroup: Deadline group name
            jobPrio: Job priority (0-100)
            jobTimeOut: Task timeout in minutes
            jobMachineLimit: Maximum concurrent machines
            jobFramesPerTask: Frames per task (chunk size)
            jobConcurrentTasks: Maximum concurrent tasks
            jobComment: Job comment
            jobBatchName: Batch name for grouping jobs
            frames: Frame range string
            suspended: If True, submit in suspended state
            dependencies: List of file/job/frame dependencies
            archivefile: Path to .ifd file to render
            environment: List of [key, value] environment variable pairs
            args: Additional arguments (unused)
            cleanupScript: Optional Python cleanup script code
            state: Optional state instance for registration
            
        Returns:
            Deadline command output with job ID
        """
        homeDir = (
            self.CallDeadlineCommand(["-GetCurrentUserHomeDirectory"])
        )

        if homeDir is False:
            return "Execute Canceled: Deadline is not installed"

        homeDir = homeDir.replace("\r", "").replace("\n", "")

        if not jobName:
            jobName = os.path.splitext(self.core.getCurrentFileName(path=False))[
                0
            ].strip("_")

        environment = environment or []
        environment.insert(0, ["prism_project", self.core.prismIni.replace("\\", "/")])

        # Create submission info file

        jobInfos = {}

        jobInfos["Name"] = jobName
        jobInfos["Pool"] = jobPool
        jobInfos["SecondaryPool"] = jobSndPool
        jobInfos["Group"] = jobGroup
        jobInfos["Priority"] = jobPrio
        jobInfos["TaskTimeoutMinutes"] = jobTimeOut
        jobInfos["MachineLimit"] = jobMachineLimit
        jobInfos["Frames"] = frames
        jobInfos["ChunkSize"] = jobFramesPerTask
        for idx, env in enumerate(environment):
            self.addEnvironmentItem(jobInfos, env[0], env[1])

        if os.getenv("PRISM_LAUNCH_ENV"):
            envData = self.core.configs.readJson(data=os.getenv("PRISM_LAUNCH_ENV"))
            for item in envData.items():
                self.addEnvironmentItem(jobInfos, item[0], item[1])

        jobInfos["Plugin"] = "Mantra"
        jobInfos["Comment"] = jobComment or "Prism-Submission-Mantra"

        if jobOutput:
            jobInfos["OutputFilename0"] = jobOutput

        if suspended:
            jobInfos["InitialStatus"] = "Suspended"

        if jobConcurrentTasks:
            jobInfos["ConcurrentTasks"] = jobConcurrentTasks

        if jobBatchName:
            jobInfos["BatchName"] = jobBatchName

        if dependencies:
            depType = dependencies[0]["type"]
            jobInfos["IsFrameDependent"] = "false" if depType == "job" else "true"
            if depType in ["job", "frame"]:
                jobids = []
                for dep in dependencies:
                    jobids += dep["jobids"]

                jobInfos["JobDependencies"] = ",".join(jobids)
            elif depType == "file":
                jobInfos["ScriptDependencies"] = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "DeadlineDependency.py")
                )

        # Create plugin info file

        pluginInfos = {}

        startFrame = frames.split("-")[0].split(",")[0]
        paddedStartFrame = str(startFrame).zfill(self.core.framePadding)
        pluginInfos["SceneFile"] = archivefile.replace(
            "#" * self.core.framePadding, paddedStartFrame
        )

        pluginInfos["Version"] = self.core.appPlugin.getDeadlineHoudiniVersion()

        dlParams = {
            "jobInfos": jobInfos,
            "pluginInfos": pluginInfos,
            "jobInfoFile": os.path.join(homeDir, "temp", "mantra_plugin_info.job"),
            "pluginInfoFile": os.path.join(homeDir, "temp", "mantra_job_info.job"),
        }

        if dependencies and dependencies[0]["type"] == "file":
            dependencyFile = os.path.join(homeDir, "temp", "dependencies.txt")
            fileHandle = open(dependencyFile, "w")

            for dependency in dependencies:
                fileHandle.write(str(dependency["offset"]) + "\n")
                fileHandle.write(str(dependency["filepath"]) + "\n")

            fileHandle.close()

        arguments = []
        arguments.append(dlParams["jobInfoFile"])
        arguments.append(dlParams["pluginInfoFile"])

        for i in getattr(self.core.appPlugin, "getCurrentSceneFiles", self.getCurrentSceneFiles)(self):
            arguments.append(i)

        if "dependencyFile" in locals():
            arguments.append(dependencyFile)

        result = self.deadlineSubmitJob(jobInfos, pluginInfos, arguments)
        if state:
            self.registerSubmittedJob(state, result, dlParams)

        if cleanupScript:
            jobName = jobName.rsplit("_", 1)[0]
            arguments = [args[0]]
            depId = self.getJobIdFromSubmitResult(result)
            if depId:
                cleanupDep = [depId]
            else:
                cleanupDep = None

            result = self.submitCleanupScript(
                jobName=jobName,
                jobPool=jobPool,
                jobSndPool=jobSndPool,
                jobGroup=jobGroup,
                jobPrio=jobPrio,
                jobTimeOut=jobTimeOut,
                jobMachineLimit=jobMachineLimit,
                jobComment=jobComment,
                jobBatchName=jobBatchName,
                suspended=suspended,
                jobDependencies=cleanupDep,
                environment=environment,
                cleanupScript=cleanupScript,
                arguments=arguments,
                state=state,
            )

        return result

    @err_catcher(name=__name__)
    def submitRedshiftJob(
        self,
        jobName: Optional[str] = None,
        jobOutput: Optional[str] = None,
        jobPool: str = "None",
        jobSndPool: str = "None",
        jobGroup: str = "None",
        jobPrio: int = 50,
        jobTimeOut: int = 180,
        jobMachineLimit: int = 0,
        jobFramesPerTask: int = 1,
        jobConcurrentTasks: Optional[int] = None,
        jobComment: Optional[str] = None,
        jobBatchName: Optional[str] = None,
        frames: str = "1",
        suspended: bool = False,
        dependencies: Optional[List[Dict[str, Any]]] = None,
        archivefile: Optional[str] = None,
        gpusPerTask: Optional[int] = None,
        gpuDevices: Optional[str] = None,
        environment: Optional[List[List[str]]] = None,
        args: Optional[List[str]] = None,
        cleanupScript: Optional[str] = None,
        state: Optional[Any] = None,
    ) -> str:
        """Submit Redshift .rs rendering job to Deadline.
        
        Uses Deadline Redshift plugin to render pre-exported .rs scene description files.
        Optionally submits cleanup job to delete .rs files after completion.
        
        Args:
            jobName: Job name (defaults to current scene filename)
            jobOutput: Output file path for rendered frames
            jobPool: Deadline pool name
            jobSndPool: Secondary pool name
            jobGroup: Deadline group name
            jobPrio: Job priority (0-100)
            jobTimeOut: Task timeout in minutes
            jobMachineLimit: Maximum concurrent machines
            jobFramesPerTask: Frames per task (chunk size)
            jobConcurrentTasks: Maximum concurrent tasks
            jobComment: Job comment
            jobBatchName: Batch name for grouping jobs
            frames: Frame range string
            suspended: If True, submit in suspended state
            dependencies: List of file/job/frame dependencies
            archivefile: Path to .rs file to render
            gpusPerTask: Number of GPUs per task
            gpuDevices: Comma-separated GPU device indices
            environment: List of [key, value] environment variable pairs
            args: Additional arguments (unused)
            cleanupScript: Optional Python cleanup script code
            state: Optional state instance for registration
            
        Returns:
            Deadline command output with job ID
        """
        homeDir = (
            self.CallDeadlineCommand(["-GetCurrentUserHomeDirectory"])
        )

        if homeDir is False:
            return "Execute Canceled: Deadline is not installed"

        homeDir = homeDir.replace("\r", "").replace("\n", "")

        if not jobName:
            jobName = os.path.splitext(self.core.getCurrentFileName(path=False))[
                0
            ].strip("_")

        environment = environment or []
        environment.insert(0, ["prism_project", self.core.prismIni.replace("\\", "/")])

        # Create submission info file

        jobInfos = {}

        jobInfos["Name"] = jobName
        jobInfos["Pool"] = jobPool
        jobInfos["SecondaryPool"] = jobSndPool
        jobInfos["Group"] = jobGroup
        jobInfos["Priority"] = jobPrio
        jobInfos["TaskTimeoutMinutes"] = jobTimeOut
        jobInfos["MachineLimit"] = jobMachineLimit
        jobInfos["Frames"] = frames
        jobInfos["ChunkSize"] = jobFramesPerTask
        for idx, env in enumerate(environment):
            self.addEnvironmentItem(jobInfos, env[0], env[1])

        if os.getenv("PRISM_LAUNCH_ENV"):
            envData = self.core.configs.readJson(data=os.getenv("PRISM_LAUNCH_ENV"))
            for item in envData.items():
                self.addEnvironmentItem(jobInfos, item[0], item[1])

        jobInfos["Plugin"] = "Redshift"
        jobInfos["Comment"] = jobComment or "Prism-Submission-Redshift"

        if jobOutput:
            jobInfos["OutputFilename0"] = jobOutput

        if suspended:
            jobInfos["InitialStatus"] = "Suspended"

        if jobConcurrentTasks:
            jobInfos["ConcurrentTasks"] = jobConcurrentTasks

        if jobBatchName:
            jobInfos["BatchName"] = jobBatchName

        if dependencies:
            depType = dependencies[0]["type"]
            jobInfos["IsFrameDependent"] = "false" if depType == "job" else "true"
            if depType in ["job", "frame"]:
                jobids = []
                for dep in dependencies:
                    jobids += dep["jobids"]

                jobInfos["JobDependencies"] = ",".join(jobids)
            elif depType == "file":
                jobInfos["ScriptDependencies"] = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "DeadlineDependency.py")
                )

        # Create plugin info file

        pluginInfos = {}

        startFrame = frames.split("-")[0].split(",")[0]
        paddedStartFrame = str(startFrame).zfill(self.core.framePadding)
        pluginInfos["SceneFile"] = archivefile.replace(
            "#" * self.core.framePadding, paddedStartFrame
        )

        pluginInfos["GPUsPerTask"] = gpusPerTask
        pluginInfos["GPUsSelectDevices"] = gpuDevices

        dlParams = {
            "jobInfos": jobInfos,
            "pluginInfos": pluginInfos,
            "jobInfoFile": os.path.join(homeDir, "temp", "redshift_plugin_info.job"),
            "pluginInfoFile": os.path.join(homeDir, "temp", "redshift_job_info.job"),
        }

        if dependencies and dependencies[0]["type"] == "file":
            dependencyFile = os.path.join(homeDir, "temp", "dependencies.txt")
            fileHandle = open(dependencyFile, "w")

            for dependency in dependencies:
                fileHandle.write(str(dependency["offset"]) + "\n")
                fileHandle.write(str(dependency["filepath"]) + "\n")

            fileHandle.close()

        arguments = []
        arguments.append(dlParams["jobInfoFile"])
        arguments.append(dlParams["pluginInfoFile"])

        for i in getattr(self.core.appPlugin, "getCurrentSceneFiles", self.getCurrentSceneFiles)(self):
            arguments.append(i)

        if "dependencyFile" in locals():
            arguments.append(dependencyFile)

        result = self.deadlineSubmitJob(jobInfos, pluginInfos, arguments)
        if state:
            self.registerSubmittedJob(state, result, dlParams)

        if cleanupScript:
            jobName = jobName.rsplit("_", 1)[0]
            arguments = [args[0]]
            depId = self.getJobIdFromSubmitResult(result)
            if depId:
                cleanupDep = [depId]
            else:
                cleanupDep = None

            result = self.submitCleanupScript(
                jobName=jobName,
                jobPool=jobPool,
                jobSndPool=jobSndPool,
                jobGroup=jobGroup,
                jobPrio=jobPrio,
                jobTimeOut=jobTimeOut,
                jobMachineLimit=jobMachineLimit,
                jobComment=jobComment,
                jobBatchName=jobBatchName,
                suspended=suspended,
                jobDependencies=cleanupDep,
                environment=environment,
                cleanupScript=cleanupScript,
                arguments=arguments,
                state=state,
            )

        return result

    @err_catcher(name=__name__)
    def submitArnoldJob(
        self,
        jobName: Optional[str] = None,
        jobOutput: Optional[str] = None,
        jobPool: str = "None",
        jobSndPool: str = "None",
        jobGroup: str = "None",
        jobPrio: int = 50,
        jobTimeOut: int = 180,
        jobMachineLimit: int = 0,
        jobFramesPerTask: int = 1,
        jobConcurrentTasks: Optional[int] = None,
        jobComment: Optional[str] = None,
        jobBatchName: Optional[str] = None,
        frames: str = "1",
        suspended: bool = False,
        dependencies: Optional[List[Dict[str, Any]]] = None,
        archivefile: Optional[str] = None,
        environment: Optional[List[List[str]]] = None,
        args: Optional[List[str]] = None,
        cleanupScript: Optional[str] = None,
        state: Optional[Any] = None,
    ) -> str:
        """Submit Arnold .ass rendering job to Deadline.
        
        Uses Deadline Arnold plugin to render pre-exported .ass scene description files.
        Optionally submits cleanup job to delete .ass files after completion.
        
        Args:
            jobName: Job name (defaults to current scene filename)
            jobOutput: Output file path for rendered frames
            jobPool: Deadline pool name
            jobSndPool: Secondary pool name
            jobGroup: Deadline group name
            jobPrio: Job priority (0-100)
            jobTimeOut: Task timeout in minutes
            jobMachineLimit: Maximum concurrent machines
            jobFramesPerTask: Frames per task (chunk size)
            jobConcurrentTasks: Maximum concurrent tasks
            jobComment: Job comment
            jobBatchName: Batch name for grouping jobs
            frames: Frame range string
            suspended: If True, submit in suspended state
            dependencies: List of file/job/frame dependencies
            archivefile: Path to .ass file to render
            environment: List of [key, value] environment variable pairs
            args: Additional arguments (unused)
            cleanupScript: Optional Python cleanup script code
            state: Optional state instance for registration
            
        Returns:
            Deadline command output with job ID
        """
        homeDir = (
            self.CallDeadlineCommand(["-GetCurrentUserHomeDirectory"])
        )

        if homeDir is False:
            return "Execute Canceled: Deadline is not installed"

        homeDir = homeDir.replace("\r", "").replace("\n", "")

        if not jobName:
            jobName = os.path.splitext(self.core.getCurrentFileName(path=False))[
                0
            ].strip("_")

        environment = environment or []
        environment.insert(0, ["prism_project", self.core.prismIni.replace("\\", "/")])

        # Create submission info file

        jobInfos = {}

        jobInfos["Name"] = jobName
        jobInfos["Pool"] = jobPool
        jobInfos["SecondaryPool"] = jobSndPool
        jobInfos["Group"] = jobGroup
        jobInfos["Priority"] = jobPrio
        jobInfos["TaskTimeoutMinutes"] = jobTimeOut
        jobInfos["MachineLimit"] = jobMachineLimit
        jobInfos["Frames"] = frames
        jobInfos["ChunkSize"] = jobFramesPerTask
        for idx, env in enumerate(environment):
            self.addEnvironmentItem(jobInfos, env[0], env[1])

        if os.getenv("PRISM_LAUNCH_ENV"):
            envData = self.core.configs.readJson(data=os.getenv("PRISM_LAUNCH_ENV"))
            for item in envData.items():
                self.addEnvironmentItem(jobInfos, item[0], item[1])

        jobInfos["Plugin"] = "Arnold"
        jobInfos["Comment"] = jobComment or "Prism-Submission-Arnold"

        if jobOutput:
            jobInfos["OutputFilename0"] = jobOutput

        if suspended:
            jobInfos["InitialStatus"] = "Suspended"

        if jobConcurrentTasks:
            jobInfos["ConcurrentTasks"] = jobConcurrentTasks

        if jobBatchName:
            jobInfos["BatchName"] = jobBatchName

        if dependencies:
            depType = dependencies[0]["type"]
            jobInfos["IsFrameDependent"] = "false" if depType == "job" else "true"
            if depType in ["job", "frame"]:
                jobids = []
                for dep in dependencies:
                    jobids += dep["jobids"]

                jobInfos["JobDependencies"] = ",".join(jobids)
            elif depType == "file":
                jobInfos["ScriptDependencies"] = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "DeadlineDependency.py")
                )

        # Create plugin info file

        pluginInfos = {}

        startFrame = frames.split("-")[0].split(",")[0]
        paddedStartFrame = str(startFrame).zfill(self.core.framePadding)
        pluginInfos["InputFile"] = archivefile.replace(
            "#" * self.core.framePadding, paddedStartFrame
        )

        dlParams = {
            "jobInfos": jobInfos,
            "pluginInfos": pluginInfos,
            "jobInfoFile": os.path.join(homeDir, "temp", "arnold_plugin_info.job"),
            "pluginInfoFile": os.path.join(homeDir, "temp", "arnold_job_info.job"),
        }

        if dependencies and dependencies[0]["type"] == "file":
            dependencyFile = os.path.join(homeDir, "temp", "dependencies.txt")
            fileHandle = open(dependencyFile, "w")

            for dependency in dependencies:
                fileHandle.write(str(dependency["offset"]) + "\n")
                fileHandle.write(str(dependency["filepath"]) + "\n")

            fileHandle.close()

        arguments = []
        arguments.append(dlParams["jobInfoFile"])
        arguments.append(dlParams["pluginInfoFile"])

        for i in getattr(self.core.appPlugin, "getCurrentSceneFiles", self.getCurrentSceneFiles)(self):
            arguments.append(i)

        if "dependencyFile" in locals():
            arguments.append(dependencyFile)

        result = self.deadlineSubmitJob(jobInfos, pluginInfos, arguments)
        if state:
            self.registerSubmittedJob(state, result, dlParams)

        if cleanupScript:
            jobName = jobName.rsplit("_", 1)[0]
            arguments = [args[0]]
            depId = self.getJobIdFromSubmitResult(result)
            if depId:
                cleanupDep = [depId]
            else:
                cleanupDep = None

            result = self.submitCleanupScript(
                jobName=jobName,
                jobPool=jobPool,
                jobSndPool=jobSndPool,
                jobGroup=jobGroup,
                jobPrio=jobPrio,
                jobTimeOut=jobTimeOut,
                jobMachineLimit=jobMachineLimit,
                jobComment=jobComment,
                jobBatchName=jobBatchName,
                suspended=suspended,
                jobDependencies=cleanupDep,
                environment=environment,
                cleanupScript=cleanupScript,
                arguments=arguments,
                state=state,
            )

        return result

    @err_catcher(name=__name__)
    def submitVrayJob(
        self,
        jobName: Optional[str] = None,
        jobOutput: Optional[str] = None,
        jobPool: str = "None",
        jobSndPool: str = "None",
        jobGroup: str = "None",
        jobPrio: int = 50,
        jobTimeOut: int = 180,
        jobMachineLimit: int = 0,
        jobFramesPerTask: int = 1,
        jobConcurrentTasks: Optional[int] = None,
        jobComment: Optional[str] = None,
        jobBatchName: Optional[str] = None,
        frames: str = "1",
        suspended: bool = False,
        dependencies: Optional[List[Dict[str, Any]]] = None,
        archivefile: Optional[str] = None,
        environment: Optional[List[List[str]]] = None,
        args: Optional[List[str]] = None,
        cleanupScript: Optional[str] = None,
        state: Optional[Any] = None,
    ) -> str:
        """Submit V-Ray .vrscene rendering job to Deadline.
        
        Submits V-Ray standalone job that renders pre-exported .vrscene files per frame.
        Optionally submits cleanup job to delete scene description files after render.
        
        Args:
            jobName: Job name displayed in Deadline (uses scene name if None)
            jobOutput: Output image file path
            jobPool: Deadline pool name
            jobSndPool: Secondary pool name
            jobGroup: Deadline group name
            jobPrio: Job priority (0-100, default 50)
            jobTimeOut: Task timeout in minutes
            jobMachineLimit: Maximum concurrent machines
            jobFramesPerTask: Frames per render task
            jobConcurrentTasks: Maximum concurrent tasks
            jobComment: Job comment
            jobBatchName: Batch name for grouping jobs
            frames: Frame range string (e.g. "1-100", "1,5,10")
            suspended: If True, submit in suspended state
            dependencies: List of job/frame/file dependencies
            archivefile: Path to .vrscene file with frame padding
            environment: List of [key, value] environment variable pairs
            args: Additional V-Ray command line arguments
            cleanupScript: Python code for cleanup job
            state: Optional state instance for registration
            
        Returns:
            Deadline command output with job ID
        """
        homeDir = (
            self.CallDeadlineCommand(["-GetCurrentUserHomeDirectory"])
        )

        if homeDir is False:
            return "Execute Canceled: Deadline is not installed"

        homeDir = homeDir.replace("\r", "").replace("\n", "")

        if not jobName:
            jobName = os.path.splitext(self.core.getCurrentFileName(path=False))[
                0
            ].strip("_")

        environment = environment or []
        environment.insert(0, ["prism_project", self.core.prismIni.replace("\\", "/")])

        # Create submission info file

        jobInfos = {}

        jobInfos["Name"] = jobName
        jobInfos["Pool"] = jobPool
        jobInfos["SecondaryPool"] = jobSndPool
        jobInfos["Group"] = jobGroup
        jobInfos["Priority"] = jobPrio
        jobInfos["TaskTimeoutMinutes"] = jobTimeOut
        jobInfos["MachineLimit"] = jobMachineLimit
        jobInfos["Frames"] = frames
        jobInfos["ChunkSize"] = jobFramesPerTask
        for idx, env in enumerate(environment):
            self.addEnvironmentItem(jobInfos, env[0], env[1])

        if os.getenv("PRISM_LAUNCH_ENV"):
            envData = self.core.configs.readJson(data=os.getenv("PRISM_LAUNCH_ENV"))
            for item in envData.items():
                self.addEnvironmentItem(jobInfos, item[0], item[1])

        jobInfos["Plugin"] = "Vray"
        jobInfos["Comment"] = jobComment or "Prism-Submission-Vray"

        if jobOutput:
            jobInfos["OutputFilename0"] = jobOutput

        if suspended:
            jobInfos["InitialStatus"] = "Suspended"

        if jobConcurrentTasks:
            jobInfos["ConcurrentTasks"] = jobConcurrentTasks

        if jobBatchName:
            jobInfos["BatchName"] = jobBatchName

        if dependencies:
            depType = dependencies[0]["type"]
            jobInfos["IsFrameDependent"] = "false" if depType == "job" else "true"
            if depType in ["job", "frame"]:
                jobids = []
                for dep in dependencies:
                    jobids += dep["jobids"]

                jobInfos["JobDependencies"] = ",".join(jobids)
            elif depType == "file":
                jobInfos["ScriptDependencies"] = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "DeadlineDependency.py")
                )

        # Create plugin info file

        pluginInfos = {}

        startFrame = frames.split("-")[0].split(",")[0]
        paddedStartFrame = str(startFrame).zfill(self.core.framePadding)
        if self.core.appPlugin.pluginName == "Maya":
            pluginInfos["InputFilename"] = archivefile.replace(
                "." + "#" * self.core.framePadding, "_" + paddedStartFrame
            )
        else:
            pluginInfos["InputFilename"] = archivefile.replace(
                "#" * self.core.framePadding, paddedStartFrame
            )

        pluginInfos["SeparateFilesPerFrame"] = "#" in archivefile
        pluginInfos["OutputFilename"] = jobOutput.replace("#" * self.core.framePadding, "#")

        dlParams = {
            "jobInfos": jobInfos,
            "pluginInfos": pluginInfos,
            "jobInfoFile": os.path.join(homeDir, "temp", "vray_plugin_info.job"),
            "pluginInfoFile": os.path.join(homeDir, "temp", "vray_job_info.job"),
        }

        if dependencies and dependencies[0]["type"] == "file":
            dependencyFile = os.path.join(homeDir, "temp", "dependencies.txt")
            fileHandle = open(dependencyFile, "w")

            for dependency in dependencies:
                fileHandle.write(str(dependency["offset"]) + "\n")
                fileHandle.write(str(dependency["filepath"]) + "\n")

            fileHandle.close()

        arguments = []
        arguments.append(dlParams["jobInfoFile"])
        arguments.append(dlParams["pluginInfoFile"])

        for i in getattr(self.core.appPlugin, "getCurrentSceneFiles", self.getCurrentSceneFiles)(self):
            arguments.append(i)

        if "dependencyFile" in locals():
            arguments.append(dependencyFile)

        result = self.deadlineSubmitJob(jobInfos, pluginInfos, arguments)
        if state:
            self.registerSubmittedJob(state, result, dlParams)

        if cleanupScript:
            jobName = jobName.rsplit("_", 1)[0]
            arguments = [args[0]]
            depId = self.getJobIdFromSubmitResult(result)
            if depId:
                cleanupDep = [depId]
            else:
                cleanupDep = None

            result = self.submitCleanupScript(
                jobName=jobName,
                jobPool=jobPool,
                jobSndPool=jobSndPool,
                jobGroup=jobGroup,
                jobPrio=jobPrio,
                jobTimeOut=jobTimeOut,
                jobMachineLimit=jobMachineLimit,
                jobComment=jobComment,
                jobBatchName=jobBatchName,
                suspended=suspended,
                jobDependencies=cleanupDep,
                environment=environment,
                cleanupScript=cleanupScript,
                arguments=arguments,
                state=state,
            )

        return result

    @err_catcher(name=__name__)
    def getJobIdFromSubmitResult(self, result: Any) -> Optional[str]:
        """Extract Deadline job ID from submission command output.
        
        Args:
            result: Deadline command output containing JobID line
            
        Returns:
            Job ID string or None if not found
        """
        result = str(result)
        lines = result.split("\n")
        for line in lines:
            if line.startswith("JobID"):
                jobId = line.split("=")[1].strip("\r")
                return jobId

    @err_catcher(name=__name__)
    def submitCleanupScript(
        self,
        jobName: Optional[str] = None,
        jobOutput: Optional[str] = None,
        jobPool: str = "None",
        jobSndPool: str = "None",
        jobGroup: str = "None",
        jobPrio: int = 50,
        jobTimeOut: int = 180,
        jobMachineLimit: int = 0,
        jobComment: Optional[str] = None,
        jobBatchName: Optional[str] = None,
        suspended: bool = False,
        jobDependencies: Optional[List[str]] = None,
        environment: Optional[List[List[str]]] = None,
        cleanupScript: Optional[str] = None,
        arguments: Optional[List[str]] = None,
        state: Optional[Any] = None,
    ) -> str:
        """Submit cleanup script job to delete temporary scene description files.
        
        Submits Python job that runs after render completion to clean up intermediate
        files (.ifd, .rs, .ass, .nsi, .vrscene files).
        
        Args:
            jobName: Job name for cleanup job
            jobOutput: Output file path (unused)
            jobPool: Deadline pool name (overrideable via PRISM_DEADLINE_CLEANUP_POOL)
            jobSndPool: Secondary pool name (overrideable via PRISM_DEADLINE_CLEANUP_2NDPOOL)
            jobGroup: Deadline group name (overrideable via PRISM_DEADLINE_CLEANUP_GROUP)
            jobPrio: Job priority (0-100)
            jobTimeOut: Task timeout in minutes
            jobMachineLimit: Maximum concurrent machines
            jobComment: Job comment
            jobBatchName: Batch name for grouping jobs
            suspended: If True, submit in suspended state
            jobDependencies: List of job IDs to depend on
            environment: List of [key, value] environment variable pairs
            cleanupScript: Python code for cleanup
            arguments: Arguments to pass to cleanup script
            state: Optional state instance for registration
            
        Returns:
            Deadline command output with job ID
        """
        cuPool = os.getenv("PRISM_DEADLINE_CLEANUP_POOL")
        if cuPool:
            jobPool = cuPool

        cu2ndPool = os.getenv("PRISM_DEADLINE_CLEANUP_2NDPOOL")
        if cu2ndPool:
            jobSndPool = cu2ndPool

        cuGroup = os.getenv("PRISM_DEADLINE_CLEANUP_GROUP")
        if cuGroup:
            jobGroup = cuGroup

        return self.submitPythonJob(
            code=cleanupScript,
            jobName=jobName + "_cleanup",
            jobPrio=jobPrio,
            jobPool=jobPool,
            jobSndPool=jobSndPool,
            jobGroup=jobGroup,
            jobTimeOut=jobTimeOut,
            jobMachineLimit=jobMachineLimit,
            jobComment=jobComment,
            jobBatchName=jobBatchName,
            frames="1",
            suspended=suspended,
            jobDependencies=jobDependencies,
            environment=environment,
            args=arguments,
            state=state,
        )

    @err_catcher(name=__name__)
    def submitHoudiniJob(
        self,
        jobName: Optional[str] = None,
        jobOutput: Optional[str] = None,
        jobPool: str = "None",
        jobSndPool: str = "None",
        jobGroup: str = "None",
        jobPrio: int = 50,
        jobTimeOut: int = 180,
        jobMachineLimit: int = 0,
        jobFramesPerTask: int = 1,
        jobConcurrentTasks: Optional[int] = None,
        jobComment: Optional[str] = None,
        jobBatchName: Optional[str] = None,
        frames: str = "1",
        suspended: bool = False,
        dependencies: Optional[List[Dict[str, Any]]] = None,
        jobDependencies: Optional[List[str]] = None,
        environment: Optional[List[List[str]]] = None,
        args: Optional[List[str]] = None,
        state: Optional[Any] = None,
        version: Optional[str] = None,
        driver: Optional[str] = None,
        extraFiles: Optional[List[str]] = None,
    ) -> str:
        """Submit Houdini batch rendering job to Deadline.
        
        Submits Houdini scene job using Deadline's Houdini plugin to render
        directly from .hip files with optional output driver specification.
        
        Args:
            jobName: Job name displayed in Deadline (uses scene name if None)
            jobOutput: Output image file path
            jobPool: Deadline pool name
            jobSndPool: Secondary pool name
            jobGroup: Deadline group name
            jobPrio: Job priority (0-100, default 50)
            jobTimeOut: Task timeout in minutes
            jobMachineLimit: Maximum concurrent machines
            jobFramesPerTask: Frames per render task
            jobConcurrentTasks: Maximum concurrent tasks
            jobComment: Job comment
            jobBatchName: Batch name for grouping jobs
            frames: Frame range string (e.g. "1-100", "1,5,10")
            suspended: If True, submit in suspended state
            dependencies: List of job/frame/file dependencies
            jobDependencies: List of job IDs to depend on
            environment: List of [key, value] environment variable pairs
            args: Additional Houdini command line arguments
            state: Optional state instance for registration
            version: Houdini version (auto-detected if None)
            driver: Output driver name to render
            extraFiles: Additional files to include with submission
            
        Returns:
            Deadline command output with job ID
        """
        homeDir = (
            self.CallDeadlineCommand(["-GetCurrentUserHomeDirectory"])
        )

        if homeDir is False:
            return "Execute Canceled: Deadline is not installed"

        homeDir = homeDir.replace("\r", "").replace("\n", "")

        if not jobName:
            jobName = os.path.splitext(self.core.getCurrentFileName(path=False))[
                0
            ].strip("_")

        environment = environment or []
        environment.insert(0, ["prism_project", self.core.prismIni.replace("\\", "/")])

        # Create submission info file

        jobInfos = {}

        jobInfos["Name"] = jobName
        jobInfos["Pool"] = jobPool
        jobInfos["SecondaryPool"] = jobSndPool
        jobInfos["Group"] = jobGroup
        jobInfos["Priority"] = jobPrio
        jobInfos["TaskTimeoutMinutes"] = jobTimeOut
        jobInfos["MachineLimit"] = jobMachineLimit
        jobInfos["Frames"] = frames
        jobInfos["ChunkSize"] = jobFramesPerTask
        for idx, env in enumerate(environment):
            self.addEnvironmentItem(jobInfos, env[0], env[1])

        if os.getenv("PRISM_LAUNCH_ENV"):
            envData = self.core.configs.readJson(data=os.getenv("PRISM_LAUNCH_ENV"))
            for item in envData.items():
                self.addEnvironmentItem(jobInfos, item[0], item[1])

        jobInfos["Plugin"] = "Houdini"
        jobInfos["Comment"] = jobComment or "Prism-Submission-Houdini"

        if jobOutput:
            jobInfos["OutputFilename0"] = jobOutput

        if suspended:
            jobInfos["InitialStatus"] = "Suspended"

        if jobConcurrentTasks:
            jobInfos["ConcurrentTasks"] = jobConcurrentTasks

        if jobBatchName:
            jobInfos["BatchName"] = jobBatchName

        if dependencies:
            depType = dependencies[0]["type"]
            jobInfos["IsFrameDependent"] = "false" if depType == "job" else "true"
            if depType in ["job", "frame"]:
                jobids = []
                for dep in dependencies:
                    jobids += dep["jobids"]

                jobInfos["JobDependencies"] = ",".join(jobids)
            elif depType == "file":
                jobInfos["ScriptDependencies"] = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "DeadlineDependency.py")
                )

        if jobDependencies:
            jobInfos["JobDependencies"] = ",".join(jobDependencies)

        # Create plugin info file

        pluginInfos = {}
        if driver:
            pluginInfos["OutputDriver"] = driver
    
        pluginInfos["IgnoreInputs"] = "False"
        if not version and self.core.appPlugin.pluginName == "Houdini":
            version = self.core.appPlugin.getDeadlineHoudiniVersion()

        if version:
            pluginInfos["Version"] = version
    
        pluginInfos["Arguments"] = "<STARTFRAME> <ENDFRAME>"
        if args:
            pluginInfos["Arguments"] += " " + " ".join(args)

        dlParams = {
            "jobInfos": jobInfos,
            "pluginInfos": pluginInfos,
            "jobInfoFile": os.path.join(homeDir, "temp", "houdini_plugin_info.job"),
            "pluginInfoFile": os.path.join(homeDir, "temp", "houdini_job_info.job"),
        }

        if dependencies and dependencies[0]["type"] == "file":
            dependencyFile = os.path.join(homeDir, "temp", "dependencies.txt")
            fileHandle = open(dependencyFile, "w")

            for dependency in dependencies:
                fileHandle.write(str(dependency["offset"]) + "\n")
                fileHandle.write(str(dependency["filepath"]) + "\n")

            fileHandle.close()

        arguments = []
        arguments.append(dlParams["jobInfoFile"])
        arguments.append(dlParams["pluginInfoFile"])
        for i in getattr(self.core.appPlugin, "getCurrentSceneFiles", self.getCurrentSceneFiles)(self):
            arguments.append(i)

        if "dependencyFile" in locals():
            arguments.append(dependencyFile)

        if extraFiles:
            arguments += extraFiles

        result = self.deadlineSubmitJob(jobInfos, pluginInfos, arguments)
        if state:
            self.registerSubmittedJob(state, result, dlParams)

        return result

    @err_catcher(name=__name__)
    def submitMayaJob(
        self,
        jobName: Optional[str] = None,
        jobOutput: Optional[str] = None,
        jobPool: str = "None",
        jobSndPool: str = "None",
        jobGroup: str = "None",
        jobPrio: int = 50,
        jobTimeOut: int = 180,
        jobMachineLimit: int = 0,
        jobFramesPerTask: int = 1,
        jobConcurrentTasks: Optional[int] = None,
        jobComment: Optional[str] = None,
        jobBatchName: Optional[str] = None,
        frames: str = "1",
        suspended: bool = False,
        dependencies: Optional[List[Dict[str, Any]]] = None,
        jobDependencies: Optional[List[str]] = None,
        environment: Optional[List[List[str]]] = None,
        args: Optional[List[str]] = None,
        state: Optional[Any] = None,
        version: Optional[str] = None,
        script: Optional[str] = None,
        extraFiles: Optional[List[str]] = None,
    ) -> str:
        """Submit Maya batch rendering job to Deadline.
        
        Submits Maya batch job using Deadline's MayaBatch plugin. Supports both scene
        rendering and Python script execution with optional render setup layer handling.
        
        Args:
            jobName: Job name displayed in Deadline (uses scene name if None)
            jobOutput: Output image file path
            jobPool: Deadline pool name
            jobSndPool: Secondary pool name
            jobGroup: Deadline group name
            jobPrio: Job priority (0-100, default 50)
            jobTimeOut: Task timeout in minutes
            jobMachineLimit: Maximum concurrent machines
            jobFramesPerTask: Frames per render task
            jobConcurrentTasks: Maximum concurrent tasks
            jobComment: Job comment
            jobBatchName: Batch name for grouping jobs
            frames: Frame range string (e.g. "1-100", "1,5,10")
            suspended: If True, submit in suspended state
            dependencies: List of job/frame/file dependencies
            jobDependencies: List of job IDs to depend on
            environment: List of [key, value] environment variable pairs
            args: Additional Maya command line arguments
            state: Optional state instance for registration
            version: Maya version (auto-detected if None)
            script: Python script code for script job execution
            extraFiles: Additional files to include with submission
            
        Returns:
            Deadline command output with job ID
        """
        homeDir = (
            self.CallDeadlineCommand(["-GetCurrentUserHomeDirectory"])
        )

        if homeDir is False:
            return "Execute Canceled: Deadline is not installed"

        homeDir = homeDir.replace("\r", "").replace("\n", "")

        if not jobName:
            jobName = os.path.splitext(self.core.getCurrentFileName(path=False))[
                0
            ].strip("_")

        environment = environment or []
        environment.insert(0, ["prism_project", self.core.prismIni.replace("\\", "/")])

        # Create submission info file

        jobInfos = {}
        pluginInfos = {}

        jobInfos["Name"] = jobName
        jobInfos["Pool"] = jobPool
        jobInfos["SecondaryPool"] = jobSndPool
        jobInfos["Group"] = jobGroup
        jobInfos["Priority"] = jobPrio
        jobInfos["TaskTimeoutMinutes"] = jobTimeOut
        jobInfos["MachineLimit"] = jobMachineLimit
        jobInfos["Frames"] = frames
        jobInfos["ChunkSize"] = jobFramesPerTask
        for idx, env in enumerate(environment):
            self.addEnvironmentItem(jobInfos, env[0], env[1])

        if os.getenv("PRISM_LAUNCH_ENV"):
            envData = self.core.configs.readJson(data=os.getenv("PRISM_LAUNCH_ENV"))
            for item in envData.items():
                self.addEnvironmentItem(jobInfos, item[0], item[1])

        jobInfos["Plugin"] = "MayaBatch"
        jobInfos["Comment"] = jobComment or "Prism-Submission-Maya"

        if jobOutput:
            jobInfos["OutputFilename0"] = jobOutput
            pluginInfos["OutputFilePath"] = os.path.split(
                jobInfos["OutputFilename0"]
            )[0]
            pluginInfos["OutputFilePrefix"] = os.path.splitext(
                os.path.basename(jobInfos["OutputFilename0"])
            )[0].strip("#.")

            import maya.app.renderSetup.model.renderSetup as renderSetup

            render_setup = renderSetup.instance()
            rlayers = render_setup.getRenderLayers()

            if rlayers:
                prefixBase = os.path.splitext(
                    os.path.basename(jobInfos["OutputFilename0"])
                )[0].strip("#.")
                passName = prefixBase.split("_")[-1]
                pluginInfos["OutputFilePrefix"] = os.path.join(
                    "..", "..", passName, prefixBase
                )

        if suspended:
            jobInfos["InitialStatus"] = "Suspended"

        if jobConcurrentTasks:
            jobInfos["ConcurrentTasks"] = jobConcurrentTasks

        if jobBatchName:
            jobInfos["BatchName"] = jobBatchName

        if dependencies:
            depType = dependencies[0]["type"]
            jobInfos["IsFrameDependent"] = "false" if depType == "job" else "true"
            if depType in ["job", "frame"]:
                jobids = []
                for dep in dependencies:
                    jobids += dep["jobids"]

                jobInfos["JobDependencies"] = ",".join(jobids)
            elif depType == "file":
                jobInfos["ScriptDependencies"] = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "DeadlineDependency.py")
                )

        if jobDependencies:
            jobInfos["JobDependencies"] = ",".join(jobDependencies)

        # Create plugin info file
    
        pluginInfos["IgnoreInputs"] = "False"
        if not version and self.core.appPlugin.pluginName == "Maya":
            version = self.core.appPlugin.getProgramVersion()

        if version:
            pluginInfos["Version"] = str(version)
    
        pluginInfos["Arguments"] = "<STARTFRAME> <ENDFRAME>"
        if args:
            pluginInfos["Arguments"] += " " + " ".join(args)

        dlParams = {
            "jobInfos": jobInfos,
            "pluginInfos": pluginInfos,
            "jobInfoFile": os.path.join(homeDir, "temp", "maya_job_info.job"),
            "pluginInfoFile": os.path.join(homeDir, "temp", "maya_plugin_info.job"),
        }

        if dependencies and dependencies[0]["type"] == "file":
            dependencyFile = os.path.join(homeDir, "temp", "dependencies.txt")
            fileHandle = open(dependencyFile, "w")

            for dependency in dependencies:
                fileHandle.write(str(dependency["offset"]) + "\n")
                fileHandle.write(str(dependency["filepath"]) + "\n")

            fileHandle.close()

        arguments = []
        arguments.append(dlParams["jobInfoFile"])
        arguments.append(dlParams["pluginInfoFile"])
        for i in getattr(self.core.appPlugin, "getCurrentSceneFiles", self.getCurrentSceneFiles)(self):
            arguments.append(i)

        if script:
            pluginInfos["ScriptJob"] = True
            scriptPath = os.path.join(homeDir, "temp", "mayaScriptJob.py")
            with open(scriptPath, "w") as f:
                f.write(script)

            pluginInfos["SceneFile"] = arguments[-1]
            arguments.append(scriptPath)
            pluginInfos["ScriptFilename"] = "mayaScriptJob.py"

        if "dependencyFile" in locals():
            arguments.append(dependencyFile)

        if extraFiles:
            arguments += extraFiles

        result = self.deadlineSubmitJob(jobInfos, pluginInfos, arguments)
        if state:
            self.registerSubmittedJob(state, result, dlParams)

        return result

    @err_catcher(name=__name__)
    def submitNukeJob(
        self,
        jobName: Optional[str] = None,
        jobOutput: Optional[str] = None,
        jobPool: str = "None",
        jobSndPool: str = "None",
        jobGroup: str = "None",
        jobPrio: int = 50,
        jobTimeOut: int = 180,
        jobMachineLimit: int = 0,
        jobFramesPerTask: int = 1,
        jobConcurrentTasks: Optional[int] = None,
        jobComment: Optional[str] = None,
        jobBatchName: Optional[str] = None,
        frames: str = "1",
        suspended: bool = False,
        dependencies: Optional[List[Dict[str, Any]]] = None,
        jobDependencies: Optional[List[str]] = None,
        environment: Optional[List[List[str]]] = None,
        args: Optional[List[str]] = None,
        state: Optional[Any] = None,
        version: Optional[str] = None,
        script: Optional[str] = None,
        extraFiles: Optional[List[str]] = None,
        writeNode: Optional[str] = None,
        userName: Optional[str] = None,
        scenefile: Optional[str] = None,
    ) -> str:
        """Submit Nuke rendering job to Deadline.
        
        Submits Nuke batch job using Deadline's Nuke plugin. Supports both scene
        rendering and Python script execution with optional write node specification.
        
        Args:
            jobName: Job name displayed in Deadline (uses scene name if None)
            jobOutput: Output image file path
            jobPool: Deadline pool name
            jobSndPool: Secondary pool name
            jobGroup: Deadline group name
            jobPrio: Job priority (0-100, default 50)
            jobTimeOut: Task timeout in minutes
            jobMachineLimit: Maximum concurrent machines
            jobFramesPerTask: Frames per render task
            jobConcurrentTasks: Maximum concurrent tasks
            jobComment: Job comment
            jobBatchName: Batch name for grouping jobs
            frames: Frame range string (e.g. "1-100", "1,5,10")
            suspended: If True, submit in suspended state
            dependencies: List of job/frame/file dependencies
            jobDependencies: List of job IDs to depend on
            environment: List of [key, value] environment variable pairs
            args: Additional Nuke command line arguments
            state: Optional state instance for registration
            version: Nuke version (auto-detected if None)
            script: Python script code for script job execution
            extraFiles: Additional files to include with submission
            writeNode: Write node name to render
            userName: Deadline username for submission
            scenefile: Explicit scene file path
            
        Returns:
            Deadline command output with job ID
        """
        homeDir = (
            self.CallDeadlineCommand(["-GetCurrentUserHomeDirectory"])
        )

        if homeDir is False:
            return "Execute Canceled: Deadline is not installed"

        homeDir = homeDir.replace("\r", "").replace("\n", "")

        if not jobName:
            jobName = os.path.splitext(self.core.getCurrentFileName(path=False))[
                0
            ].strip("_")

        environment = environment or []
        environment.insert(0, ["prism_project", self.core.prismIni.replace("\\", "/")])

        # Create submission info file

        jobInfos = {}
        pluginInfos = {}

        jobInfos["Name"] = jobName
        jobInfos["Pool"] = jobPool
        jobInfos["SecondaryPool"] = jobSndPool
        jobInfos["Group"] = jobGroup
        jobInfos["Priority"] = jobPrio
        jobInfos["TaskTimeoutMinutes"] = jobTimeOut
        jobInfos["MachineLimit"] = jobMachineLimit
        jobInfos["Frames"] = frames
        jobInfos["ChunkSize"] = jobFramesPerTask
        if userName:
            jobInfos["UserName"] = userName

        for idx, env in enumerate(environment):
            self.addEnvironmentItem(jobInfos, env[0], env[1])

        if os.getenv("PRISM_LAUNCH_ENV"):
            envData = self.core.configs.readJson(data=os.getenv("PRISM_LAUNCH_ENV"))
            for item in envData.items():
                self.addEnvironmentItem(jobInfos, item[0], item[1])

        jobInfos["Plugin"] = "Nuke"
        jobInfos["Comment"] = jobComment or "Prism-Submission-Nuke"

        if jobOutput:
            jobInfos["OutputFilename0"] = jobOutput
            pluginInfos["OutputFilePath"] = os.path.split(
                jobInfos["OutputFilename0"]
            )[0]
            pluginInfos["OutputFilePrefix"] = os.path.splitext(
                os.path.basename(jobInfos["OutputFilename0"])
            )[0].strip("#.")

        if suspended:
            jobInfos["InitialStatus"] = "Suspended"

        if jobConcurrentTasks:
            jobInfos["ConcurrentTasks"] = jobConcurrentTasks

        if jobBatchName:
            jobInfos["BatchName"] = jobBatchName

        if dependencies:
            depType = dependencies[0]["type"]
            jobInfos["IsFrameDependent"] = "false" if depType == "job" else "true"
            if depType in ["job", "frame"]:
                jobids = []
                for dep in dependencies:
                    jobids += dep["jobids"]

                jobInfos["JobDependencies"] = ",".join(jobids)
            elif depType == "file":
                jobInfos["ScriptDependencies"] = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "DeadlineDependency.py")
                )

        if jobDependencies:
            jobInfos["JobDependencies"] = ",".join(jobDependencies)

        # Create plugin info file
    
        pluginInfos["IgnoreInputs"] = "False"
        if not version and self.core.appPlugin.pluginName == "Nuke":
            version = self.core.appPlugin.getProgramVersion()

        if version:
            pluginInfos["Version"] = str(version)
    
        pluginInfos["Arguments"] = "<STARTFRAME> <ENDFRAME>"
        if args:
            pluginInfos["Arguments"] += " " + " ".join(args)

        if writeNode:
            pluginInfos["WriteNode"] = writeNode

        dlParams = {
            "jobInfos": jobInfos,
            "pluginInfos": pluginInfos,
            "jobInfoFile": os.path.join(homeDir, "temp", "nuke_job_info.job"),
            "pluginInfoFile": os.path.join(homeDir, "temp", "nuke_plugin_info.job"),
        }

        if dependencies and dependencies[0]["type"] == "file":
            dependencyFile = os.path.join(homeDir, "temp", "dependencies.txt")
            fileHandle = open(dependencyFile, "w")

            for dependency in dependencies:
                fileHandle.write(str(dependency["offset"]) + "\n")
                fileHandle.write(str(dependency["filepath"]) + "\n")

            fileHandle.close()

        arguments = []
        arguments.append(dlParams["jobInfoFile"])
        arguments.append(dlParams["pluginInfoFile"])
        for i in getattr(self.core.appPlugin, "getCurrentSceneFiles", self.getCurrentSceneFiles)(self):
            arguments.append(i)

        if script:
            pluginInfos["BatchMode"] = True
            pluginInfos["ScriptJob"] = True
            scriptPath = os.path.join(homeDir, "temp", "nukeScriptJob.py")
            with open(scriptPath, "w") as f:
                f.write(script)

            if self.core.appPlugin.pluginName == "Nuke":
                pluginInfos["SceneFile"] = arguments[-1]

            arguments.append(scriptPath)
            pluginInfos["ScriptFilename"] = "nukeScriptJob.py"

        if scenefile:
            pluginInfos["SceneFile"] = scenefile

        if "dependencyFile" in locals():
            arguments.append(dependencyFile)

        if extraFiles:
            arguments += extraFiles

        result = self.deadlineSubmitJob(jobInfos, pluginInfos, arguments)
        if state:
            self.registerSubmittedJob(state, result, dlParams)

        return result

    @err_catcher(name=__name__)
    def submitKarmaJob(
        self,
        jobName: Optional[str] = None,
        jobOutput: Optional[str] = None,
        jobPool: str = "None",
        jobSndPool: str = "None",
        jobGroup: str = "None",
        jobPrio: int = 50,
        jobTimeOut: int = 180,
        jobMachineLimit: int = 0,
        jobFramesPerTask: int = 1,
        jobConcurrentTasks: Optional[int] = None,
        jobComment: Optional[str] = None,
        jobBatchName: Optional[str] = None,
        frames: str = "1",
        suspended: bool = False,
        dependencies: Optional[List[Dict[str, Any]]] = None,
        archivefile: Optional[str] = None,
        environment: Optional[List[List[str]]] = None,
        args: Optional[List[str]] = None,
        cleanupScript: Optional[str] = None,
        state: Optional[Any] = None,
        jobInfos: Optional[Dict[str, Any]] = None,
        pluginInfos: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Submit Karma USD rendering job to Deadline.
        
        Submits Houdini Karma job that renders pre-exported USD scene description files.
        Optionally submits cleanup job to delete scene files after render.
        
        Args:
            jobName: Job name displayed in Deadline (uses scene name if None)
            jobOutput: Output image file path
            jobPool: Deadline pool name
            jobSndPool: Secondary pool name
            jobGroup: Deadline group name
            jobPrio: Job priority (0-100, default 50)
            jobTimeOut: Task timeout in minutes
            jobMachineLimit: Maximum concurrent machines
            jobFramesPerTask: Frames per render task
            jobConcurrentTasks: Maximum concurrent tasks
            jobComment: Job comment
            jobBatchName: Batch name for grouping jobs
            frames: Frame range string (e.g. "1-100", "1,5,10")
            suspended: If True, submit in suspended state
            dependencies: List of job/frame/file dependencies
            archivefile: Path to USD scene file with frame padding
            environment: List of [key, value] environment variable pairs
            args: Additional Karma command line arguments
            cleanupScript: Python code for cleanup job
            state: Optional state instance for registration
            jobInfos: Optional job info dictionary to extend
            pluginInfos: Optional plugin info dictionary to extend
            
        Returns:
            Deadline command output with job ID
        """
        homeDir = (
            self.CallDeadlineCommand(["-GetCurrentUserHomeDirectory"])
        )

        if homeDir is False:
            return "Execute Canceled: Deadline is not installed"

        homeDir = homeDir.replace("\r", "").replace("\n", "")

        if not jobName:
            jobName = os.path.splitext(self.core.getCurrentFileName(path=False))[
                0
            ].strip("_")

        environment = environment or []
        environment.insert(0, ["prism_project", self.core.prismIni.replace("\\", "/")])

        # Create submission info file

        jobInfos = jobInfos or {}

        jobInfos["Name"] = jobName
        jobInfos["Pool"] = jobPool
        jobInfos["SecondaryPool"] = jobSndPool
        jobInfos["Group"] = jobGroup
        jobInfos["Priority"] = jobPrio
        jobInfos["TaskTimeoutMinutes"] = jobTimeOut
        jobInfos["MachineLimit"] = jobMachineLimit
        jobInfos["Frames"] = frames
        jobInfos["ChunkSize"] = jobFramesPerTask
        for idx, env in enumerate(environment):
            self.addEnvironmentItem(jobInfos, env[0], env[1])

        if os.getenv("PRISM_LAUNCH_ENV"):
            envData = self.core.configs.readJson(data=os.getenv("PRISM_LAUNCH_ENV"))
            for item in envData.items():
                self.addEnvironmentItem(jobInfos, item[0], item[1])

        jobInfos["Plugin"] = "Karma"
        jobInfos["Comment"] = jobComment or "Prism-Submission-Karma"

        if jobOutput:
            jobInfos["OutputFilename0"] = jobOutput

        if suspended:
            jobInfos["InitialStatus"] = "Suspended"

        if jobConcurrentTasks:
            jobInfos["ConcurrentTasks"] = jobConcurrentTasks

        if jobBatchName:
            jobInfos["BatchName"] = jobBatchName

        if dependencies:
            depType = dependencies[0]["type"]
            jobInfos["IsFrameDependent"] = "false" if depType == "job" else "true"
            if depType in ["job", "frame"]:
                jobids = []
                for dep in dependencies:
                    jobids += dep["jobids"]

                jobInfos["JobDependencies"] = ",".join(jobids)
            elif depType == "file":
                jobInfos["ScriptDependencies"] = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "DeadlineDependency.py")
                )

        # Create plugin info file

        pluginInfos = pluginInfos or {}

        startFrame = frames.split("-")[0].split(",")[0]
        paddedStartFrame = str(startFrame).zfill(self.core.framePadding)
        pluginInfos["SceneFile"] = archivefile.replace(
            "#" * self.core.framePadding, paddedStartFrame
        )
        if jobOutput:
            pluginInfos["OutputFile"] = jobOutput

        dlParams = {
            "jobInfos": jobInfos,
            "pluginInfos": pluginInfos,
            "jobInfoFile": os.path.join(homeDir, "temp", "karma_plugin_info.job"),
            "pluginInfoFile": os.path.join(homeDir, "temp", "karma_job_info.job"),
        }

        if dependencies and dependencies[0]["type"] == "file":
            dependencyFile = os.path.join(homeDir, "temp", "dependencies.txt")
            fileHandle = open(dependencyFile, "w")

            for dependency in dependencies:
                fileHandle.write(str(dependency["offset"]) + "\n")
                fileHandle.write(str(dependency["filepath"]) + "\n")

            fileHandle.close()

        arguments = []
        arguments.append(dlParams["jobInfoFile"])
        arguments.append(dlParams["pluginInfoFile"])

        if "dependencyFile" in locals():
            arguments.append(dependencyFile)

        result = self.deadlineSubmitJob(jobInfos, pluginInfos, arguments)
        if state:
            self.registerSubmittedJob(state, result, dlParams)

        if cleanupScript:
            jobName = jobName.rsplit("_", 1)[0]
            arguments = [args[0]]
            depId = self.getJobIdFromSubmitResult(result)
            if depId:
                cleanupDep = [depId]
            else:
                cleanupDep = None

            result = self.submitCleanupScript(
                jobName=jobName,
                jobPool=jobPool,
                jobSndPool=jobSndPool,
                jobGroup=jobGroup,
                jobPrio=jobPrio,
                jobTimeOut=jobTimeOut,
                jobMachineLimit=jobMachineLimit,
                jobComment=jobComment,
                jobBatchName=jobBatchName,
                suspended=suspended,
                jobDependencies=cleanupDep,
                environment=environment,
                cleanupScript=cleanupScript,
                arguments=arguments,
                state=state,
            )

        return result

    @err_catcher(name=__name__)
    def deadlineSubmitJob(
        self,
        jobInfos: Dict[str, Any],
        pluginInfos: Dict[str, Any],
        arguments: List[str]
    ) -> str:
        """Core Deadline job submission function.
        
        Writes job info and plugin info files, calls Deadline command line tool,
        and processes callbacks for all job submissions.
        
        Args:
            jobInfos: Dictionary of Deadline job parameters (name, pool, frames, etc)
            pluginInfos: Dictionary of plugin-specific parameters (scene file, version, etc)
            arguments: List of command arguments starting with info file paths
            
        Returns:
            Deadline command output containing job ID or error message
        """
        envVars = self.getJobEnvVars()
        if envVars:
            for key in envVars:
                self.addEnvironmentItem(jobInfos, key, envVars[key])

        result = self.core.callback(
            name="preSubmit_Deadline",
            args=[self, jobInfos, pluginInfos, arguments],
        )
        for res in result:
            if isinstance(res, dict) and res.get("cancel", False):
                return "Execute Canceled: preSubmit_Deadline callback return False."

        with open(arguments[0], "w") as fileHandle:
            for i in jobInfos:
                fileHandle.write("%s=%s\n" % (i, jobInfos[i]))

        with open(arguments[1], "w") as fileHandle:
            for i in pluginInfos:
                fileHandle.write("%s=%s\n" % (i, pluginInfos[i]))

        logger.debug("submitting job: " + str(arguments))
        jobResult = self.CallDeadlineCommand(arguments)

        if jobResult is False:
            return "Execute Canceled: Deadline is not installed"

        for line in jobResult.split("\n"):
            if "Key-value pair not supported" in line:
                logger.debug("Deadline Submission Warning: %s" % line)

        if "Error: " in jobResult:
            logger.warning(jobResult)

        self.core.callback(name="postSubmit_Deadline", args=[self, jobResult, jobInfos, pluginInfos, arguments],)
        logger.debug("submitted job: %s - %s - %s - %s" % (jobInfos, pluginInfos, arguments, jobResult))
        return jobResult

    @err_catcher(name=__name__)
    def getRedshiftCleanupScript(self) -> str:
        """Get Python script for cleaning up Redshift scene description files.
        
        Returns Python code that deletes the _rs directory containing temporary
        .rs scene description files after rendering completes.
        
        Returns:
            Python script code as string
        """
        script = """

import os
import sys
import shutil

rsOutput = sys.argv[-1]

delDir = os.path.dirname(rsOutput)
if os.path.basename(delDir) != "_rs":
    raise RuntimeError("invalid rs directory: %s" % (delDir))

if os.path.exists(delDir):
    shutil.rmtree(delDir)
    print("task completed successfully")
else:
    print("directory doesn't exist")

"""
        return script


class PresetWidget(QGroupBox):
    def __init__(self, plugin: Any, presetData: Optional[List[Dict[str, str]]] = None) -> None:
        """Initialize pool preset widget.
        
        Args:
            plugin: Deadline plugin instance
            presetData: Optional list of preset dictionaries to load
        """
        super(PresetWidget, self).__init__()
        self.plugin = plugin
        self.core = self.plugin.core
        self.core.parentWindow(self)

        self.loadLayout()
        self.connectEvents()
        if presetData:
            self.loadPresetData(presetData)

    @err_catcher(name=__name__)
    def loadLayout(self) -> None:
        """Build UI layout with preset list and add button.
        
        Creates vertical layout containing preset items and add button for
        creating new pool presets.
        """
        self.w_add = QWidget()
        self.b_add = QToolButton()
        self.lo_add = QHBoxLayout()
        self.w_add.setLayout(self.lo_add)
        self.lo_add.addStretch()
        self.lo_add.addWidget(self.b_add)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_add.setIcon(icon)
        self.b_add.setIconSize(QSize(20, 20))
        self.b_add.setToolTip("Add Preset")
        if self.core.appPlugin.pluginName != "Standalone":
            self.b_add.setStyleSheet(
                "QWidget{padding: 0; border-width: 0px;background-color: transparent} QWidget:hover{border-width: 1px; }"
            )

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "reset.png"
        )
        icon = self.core.media.getColoredIcon(path)

        self.lo_preset = QVBoxLayout()
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.addLayout(self.lo_preset)
        self.lo_main.addWidget(self.w_add)
        self.setTitle("Pool Presets")

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect UI signals to event handlers.
        
        Connects add button click to addItem method.
        """
        self.b_add.clicked.connect(self.addItem)

    @err_catcher(name=__name__)
    def refresh(self) -> None:
        """Refresh widget by saving and reloading preset data.
        
        Clears all items and rebuilds from current preset data.
        """
        data = self.getPresetData()
        self.clearItems()
        self.loadPresetData(data)

    @err_catcher(name=__name__)
    def loadPresetData(self, presetData: List[Dict[str, str]]) -> None:
        """Load preset items from data list.
        
        Args:
            presetData: List of dicts with 'name', 'pool', 'secondaryPool', 'group'
        """
        self.clearItems()
        for preset in presetData:
            self.addItem(
                name=preset["name"],
                pool=preset["pool"],
                secondaryPool=preset["secondaryPool"],
                group=preset["group"]
            )

    @err_catcher(name=__name__)
    def addItem(
        self,
        name: Optional[str] = None,
        pool: Optional[str] = None,
        secondaryPool: Optional[str] = None,
        group: Optional[str] = None
    ) -> Any:
        """Add new preset item to the list.
        
        Args:
            name: Preset name
            pool: Pool name
            secondaryPool: Secondary pool name
            group: Group name
            
        Returns:
            Created PresetItem widget
        """
        item = PresetItem(self.plugin)
        item.removed.connect(self.removeItem)
        if name:
            item.setName(name)

        if pool:
            item.setPool(pool)

        if secondaryPool:
            item.setSecondaryPool(secondaryPool)

        if group:
            item.setGroup(group)

        self.lo_preset.addWidget(item)
        return item

    @err_catcher(name=__name__)
    def removeItem(self, item: Any) -> None:
        """Remove preset item from layout.
        
        Args:
            item: PresetItem widget to remove
        """
        idx = self.lo_preset.indexOf(item)
        if idx != -1:
            w = self.lo_preset.takeAt(idx)
            if w.widget():
                w.widget().deleteLater()

    @err_catcher(name=__name__)
    def clearItems(self) -> None:
        """Remove all preset items from layout.
        
        Clears layout by removing and deleting all preset item widgets.
        """
        for idx in reversed(range(self.lo_preset.count())):
            item = self.lo_preset.takeAt(idx)
            w = item.widget()
            if w:
                w.setVisible(False)
                w.deleteLater()

    @err_catcher(name=__name__)
    def getPresetData(self) -> List[Dict[str, str]]:
        """Extract preset data from UI items.
        
        Returns:
            List of dicts with 'name', 'pool', 'secondaryPool', 'group' keys
        """
        presetData = []
        for idx in range(self.lo_preset.count()):
            w = self.lo_preset.itemAt(idx)
            widget = w.widget()
            if widget:
                if isinstance(widget, PresetItem):
                    if not widget.name():
                        continue

                    sdata = {
                        "name": widget.name(),
                        "pool": widget.pool(),
                        "secondaryPool": widget.secondaryPool(),
                        "group": widget.group(),
                    }
                    presetData.append(sdata)

        return presetData


class PresetItem(QWidget):

    removed = Signal(object)

    def __init__(self, plugin: Any) -> None:
        """Initialize preset item widget.
        
        Args:
            plugin: Deadline plugin instance
        """
        super(PresetItem, self).__init__()
        self.plugin = plugin
        self.core = self.plugin.core
        self.loadLayout()

    @err_catcher(name=__name__)
    def loadLayout(self) -> None:
        """Build UI layout with name field, pool dropdowns, and remove button.
        
        Creates horizontal layout with preset name input, pool/group selectors,
        and delete button.
        """
        self.e_name = QLineEdit()
        self.e_name.setPlaceholderText("Name")
        self.cb_pool = QComboBox()
        self.cb_pool.setToolTip("Pool")
        self.cb_pool.addItems(["< Pool >"] + self.plugin.getDeadlinePools())
        self.cb_secondaryPool = QComboBox()
        self.cb_secondaryPool.setToolTip("Secondary Pool")
        self.cb_secondaryPool.addItems(["< Secondary Pool >"] + self.plugin.getDeadlinePools())
        self.cb_group = QComboBox()
        self.cb_group.setToolTip("Group")
        self.cb_group.addItems(["< Group >"] + self.plugin.getDeadlineGroups())

        self.b_remove = QToolButton()
        self.b_remove.clicked.connect(lambda: self.removed.emit(self))

        self.lo_main = QHBoxLayout()
        self.lo_main.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.lo_main)
        self.lo_main.addWidget(self.e_name, 10)
        self.lo_main.addWidget(self.cb_pool, 10)
        self.lo_main.addWidget(self.cb_secondaryPool, 10)
        self.lo_main.addWidget(self.cb_group, 10)
        self.lo_main.addWidget(self.b_remove)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "delete.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_remove.setIcon(icon)
        self.b_remove.setIconSize(QSize(20, 20))
        self.b_remove.setToolTip("Delete")
        if self.core.appPlugin.pluginName != "Standalone":
            self.b_remove.setStyleSheet(
                "QWidget{padding: 0; border-width: 0px;background-color: transparent} QWidget:hover{border-width: 1px; }"
            )

    @err_catcher(name=__name__)
    def name(self) -> str:
        """Get preset name.
        
        Returns:
            Preset name text
        """
        return self.e_name.text()

    @err_catcher(name=__name__)
    def setName(self, name: str) -> bool:
        """Set preset name.
        
        Args:
            name: Preset name text
            
        Returns:
            True if successful
        """
        return self.e_name.setText(name)

    @err_catcher(name=__name__)
    def pool(self) -> str:
        """Get selected pool name.
        
        Returns:
            Pool name from combobox
        """
        return self.cb_pool.currentText()

    @err_catcher(name=__name__)
    def setPool(self, pool: str) -> None:
        """Set selected pool name.
        
        Args:
            pool: Pool name to select in combobox
        """
        idx = self.cb_pool.findText(pool)
        if idx != -1:
            self.cb_pool.setCurrentIndex(idx)

    @err_catcher(name=__name__)
    def secondaryPool(self) -> str:
        """Get selected secondary pool name.
        
        Returns:
            Secondary pool name from combobox
        """
        return self.cb_secondaryPool.currentText()

    @err_catcher(name=__name__)
    def setSecondaryPool(self, secondaryPool: str) -> None:
        """Set selected secondary pool name.
        
        Args:
            secondaryPool: Secondary pool name to select in combobox
        """
        idx = self.cb_secondaryPool.findText(secondaryPool)
        if idx != -1:
            self.cb_secondaryPool.setCurrentIndex(idx)

    @err_catcher(name=__name__)
    def group(self) -> str:
        """Get selected group name.
        
        Returns:
            Group name from combobox
        """
        return self.cb_group.currentText()

    @err_catcher(name=__name__)
    def setGroup(self, group: str) -> None:
        """Set selected group name.
        
        Args:
            group: Group name to select in combobox
        """
        idx = self.cb_group.findText(group)
        if idx != -1:
            self.cb_group.setCurrentIndex(idx)


class SubmitPythonJobDlg(QDialog):
    def __init__(self, origin: Any, parent: Optional[Any] = None) -> None:
        """Initialize Python job submission dialog.
        
        Args:
            origin: Plugin instance
            parent: Optional parent widget
        """
        super(SubmitPythonJobDlg, self).__init__()
        self.plugin = origin
        self.core = self.plugin.core
        self.core.parentWindow(self, parent=parent)
        self.setupUi()

    def sizeHint(self) -> QSize:
        """Suggest preferred size for dialog.
        
        Returns:
            Preferred size (1000x800)
        """
        return QSize(1000, 800)

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Build UI layout with text editor and submit button.
        
        Creates dialog with Python code editor, syntax highlighting, and
        submit/close buttons.
        """
        self.lo_main = QVBoxLayout(self)
        self.te_text = QTextEdit()
        dft = """import sys
sys.path.append(r"%s/Scripts")
import PrismCore
pcore = PrismCore.create(prismArgs=["noUI", "loadProject"])
print(pcore)
""" % self.core.prismRoot.replace("\\", "/")

        self.te_text.setText(dft)
        self.lo_main.addWidget(self.te_text)
        self.core.pythonHighlighter(self.te_text.document())

        self.bb_main = QDialogButtonBox()
        self.b_submit = self.bb_main.addButton("Submit", QDialogButtonBox.AcceptRole)
        if os.getenv("PRISM_CODE_EDITOR"):
            self.b_openExternal = self.bb_main.addButton("Open in External Editor...", QDialogButtonBox.AcceptRole)
            self.b_openExternal.clicked.connect(self.openInExternalEditor)

        self.bb_main.addButton("Close", QDialogButtonBox.RejectRole)
        self.b_submit.clicked.connect(lambda: self.onAccepted("submit"))
        self.bb_main.rejected.connect(self.reject)
        self.lo_main.addWidget(self.bb_main)

        self.setWindowTitle("Submit Python Script")

    @err_catcher(name=__name__)
    def openInExternalEditor(self) -> None:
        """Open Python code in external editor.
        
        Uses PRISM_CODE_EDITOR environment variable to launch external editor,
        writes current code to temp file, waits for edits, then reloads.
        """
        exe = os.getenv("PRISM_CODE_EDITOR")
        if not exe:
            self.core.popup("Invalid code editor executable.")
            return

        text = self.layer.ExportToString()
        import tempfile, subprocess
        file = tempfile.NamedTemporaryFile(prefix="prism_", suffix=".py")
        tmpPath = file.name
        file.close()
        with open(tmpPath, "w") as f:
            f.write(text)

        args = [exe, tmpPath]
        logger.debug("opening external editor: %s" % args)
        subprocess.call(args)

        with open(tmpPath, "r") as f:
            newText = f.read()

        try:
            os.remove(tmpPath)
        except:
            pass

        self.te_text.setText(newText)

    @err_catcher(name=__name__)
    def onAccepted(self, mode: str) -> None:
        """Handle dialog acceptance.
        
        Args:
            mode: Accept mode ('submit' to submit job to Deadline)
        """
        pythonCode = self.te_text.toPlainText()
        if mode == "submit":
            with self.core.waitPopup(self.core, "Submitting Job. Please wait..."):
                result = self.plugin.submitPythonJob(pythonCode)

            if "Result=Success" in result:
                self.core.popup("Submitted Publish Successfully.", severity="info")
            else:
                self.core.popup("Failed to Submit Publish:\n\n%s" % result)


class EnvironmentTable(QWidget):
    def __init__(self, parent: Any) -> None:
        """Initialize environment variable table widget.
        
        Args:
            parent: Parent widget containing plugin reference
        """
        super(EnvironmentTable, self).__init__()
        self.plugin = parent.plugin
        self.core = self.plugin.core
        self.setupUI()

    @err_catcher(name=__name__)
    def setupUI(self) -> None:
        """Build UI layout with environment variable table.
        
        Creates table widget with Variable/Value columns, context menu for
        adding/removing rows, and button to show current environment.
        """
        self.lo_main = QVBoxLayout()
        self.lo_main.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.lo_main)

        self.tw_environment = QTableWidget()
        self.l_header = QLabel("Job Environment Variables:")
        self.lo_main.addWidget(self.l_header)
        self.lo_main.addWidget(self.tw_environment)
        self.w_footer = QWidget()
        self.lo_footer = QHBoxLayout()
        self.w_footer.setLayout(self.lo_footer)
        self.lo_main.addWidget(self.w_footer)
        self.lo_footer.addStretch()
        self.b_showEnvironment = QPushButton("Show current environment")
        self.lo_footer.addWidget(self.b_showEnvironment)
        self.tw_environment.setColumnCount(2)
        self.tw_environment.horizontalHeader().setStretchLastSection(True)
        self.tw_environment.horizontalHeader().setHighlightSections(False)
        self.tw_environment.verticalHeader().setVisible(False)
        self.tw_environment.setHorizontalHeaderLabels(["Variable", "Value"])
        self.tw_environment.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tw_environment.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tw_environment.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tw_environment.customContextMenuRequested.connect(self.rclEnvironment)
        self.addEnvironmentRow()
        self.tw_environment.resizeColumnsToContents()
        self.b_showEnvironment.clicked.connect(self.showEnvironment)

    @err_catcher(name=__name__)
    def rclEnvironment(self, pos: Any) -> None:
        """Show context menu for environment table.
        
        Args:
            pos: Mouse position for context menu
        """
        rcmenu = QMenu(self)

        exp = QAction("Add row", self)
        exp.triggered.connect(self.addEnvironmentRow)
        rcmenu.addAction(exp)

        item = self.tw_environment.itemFromIndex(self.tw_environment.indexAt(pos))
        if item:
            exp = QAction("Remove", self)
            exp.triggered.connect(lambda: self.removeEnvironmentRow(item.row()))
            rcmenu.addAction(exp)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def addEnvironmentRow(self, variable: Optional[str] = None, value: Optional[str] = None) -> None:
        """Add new row to environment table.
        
        Args:
            variable: Environment variable name (uses placeholder if None)
            value: Environment variable value (uses placeholder if None)
        """
        count = self.tw_environment.rowCount()
        self.tw_environment.insertRow(count)
        if variable is None:
            variable = "< doubleclick to edit >"

        if value is None:
            value = "< doubleclick to edit >"

        item = QTableWidgetItem(variable)
        self.tw_environment.setItem(count, 0, item)
        item = QTableWidgetItem(value)
        self.tw_environment.setItem(count, 1, item)

    @err_catcher(name=__name__)
    def removeEnvironmentRow(self, idx: int) -> None:
        """Remove row from environment table.
        
        Args:
            idx: Row index to remove
        """
        self.tw_environment.removeRow(idx)

    @err_catcher(name=__name__)
    def addEnvs(self, envs: Dict[str, str]) -> None:
        """Add multiple environment variables to table.
        
        Args:
            envs: Dictionary of environment variable key-value pairs
        """
        for key in envs:
            self.addEnvironmentRow(variable=key, value=envs[key])

        self.tw_environment.resizeColumnsToContents()

    @err_catcher(name=__name__)
    def showEnvironment(self) -> None:
        """Show dialog with current process environment variables.
        
        Opens EnvironmentWidget dialog displaying all environment variables
        from current process.
        """
        self.w_env = EnvironmentWidget(self)
        self.w_env.show()

    @err_catcher(name=__name__)
    def getEnvironmentVariables(self) -> Dict[str, str]:
        """Extract environment variables from table.
        
        Returns:
            Dictionary of variable names to values (excludes placeholder rows)
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
        """Load environment variables into table.
        
        Args:
            variables: Dictionary of environment variable key-value pairs
        """
        self.tw_environment.setRowCount(0)
        for idx, key in enumerate(sorted(variables)):
            self.tw_environment.insertRow(idx)
            item = QTableWidgetItem(key)
            self.tw_environment.setItem(idx, 0, item)
            item = QTableWidgetItem(variables[key])
            self.tw_environment.setItem(idx, 1, item)


class EnvironmentWidget(QDialog):
    def __init__(self, parent: Any) -> None:
        """Initialize environment viewer dialog.
        
        Args:
            parent: Parent widget (EnvironmentTable instance)
        """
        super(EnvironmentWidget, self).__init__()
        self.parent = parent
        self.core = self.parent.core
        self.core.parentWindow(self, parent=self.parent)
        self.setupUi()
        self.refreshEnvironment()

    def sizeHint(self) -> QSize:
        """Suggest preferred size for dialog.
        
        Returns:
            Preferred size (1000x700)
        """
        return QSize(1000, 700)

    def setupUi(self) -> None:
        """Build UI layout with environment table.
        
        Creates read-only table widget displaying environment variables from
        current process.
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
        """Populate table with current environment variables.
        
        Reads all environment variables from os.environ and displays them
        sorted alphabetically in the table.
        """
        self.tw_environment.setRowCount(0)
        for idx, key in enumerate(sorted(os.environ)):
            self.tw_environment.insertRow(idx)
            item = QTableWidgetItem(key)
            self.tw_environment.setItem(idx, 0, item)
            item = QTableWidgetItem(os.environ[key])
            self.tw_environment.setItem(idx, 1, item)

        self.tw_environment.resizeColumnsToContents()
