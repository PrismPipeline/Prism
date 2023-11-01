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

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher as err_catcher


logger = logging.getLogger(__name__)


class Prism_Deadline_Functions(object):
    def __init__(self, core, plugin):
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

template = base + "_@product@@identifier@_@version@"]"""

        data = {"label": "Deadline Job Name", "key": "@deadline_job_name@", "value": dft, "requires": []}
        self.core.projects.addProjectStructureItem("deadlineJobName", data)

    @err_catcher(name=__name__)
    def isActive(self):
        try:
            return True  # len(self.getDeadlineGroups()) > 0
        except:
            return False

    @err_catcher(name=__name__)
    def unregister(self):
        self.core.plugins.unregisterRenderfarmPlugin(self)

    def GetDeadlineCommand(self):
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

    def CallDeadlineCommand(self, arguments, hideWindow=True, readStdout=True, silent=False):
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
            output = output.decode()

        return output

    @err_catcher(name=__name__)
    def refreshPools(self):
        if not hasattr(self.core, "projectPath"):
            return

        with self.core.waitPopup(self.core, "Getting pools from Deadline. Please wait..."):
            output = self.CallDeadlineCommand(["-pools"], silent=True)

        if output and "Error" not in output:
            deadlinePools = output.splitlines()
        else:
            deadlinePools = []

        self.core.setConfig("deadline", "pools", val=deadlinePools, config="project")
        return deadlinePools

    @err_catcher(name=__name__)
    def getDeadlinePools(self):
        if not hasattr(self.core, "projectPath"):
            return

        pools = self.core.getConfig("deadline", "pools", config="project")
        if pools is None:
            self.refreshPools()
            pools = self.core.getConfig("deadline", "pools", config="project")

        pools = pools or []
        return pools

    @err_catcher(name=__name__)
    def refreshGroups(self):
        if not hasattr(self.core, "projectPath"):
            return

        with self.core.waitPopup(self.core, "Getting groups from Deadline. Please wait..."):
            output = self.CallDeadlineCommand(["-groups"], silent=True)

        if output and "Error" not in output:
            deadlineGroups = output.splitlines()
        else:
            deadlineGroups = []

        self.core.setConfig("deadline", "groups", val=deadlineGroups, config="project")
        return deadlineGroups

    @err_catcher(name=__name__)
    def getDeadlineGroups(self):
        if not hasattr(self.core, "projectPath"):
            return

        groups = self.core.getConfig("deadline", "groups", config="project")
        if groups is None:
            self.refreshGroups()
            groups = self.core.getConfig("deadline", "groups", config="project")

        groups = groups or []
        return groups

    @err_catcher(name=__name__)
    def getUseDeadlinePoolPresets(self):
        usePresets = self.core.getConfig("deadline", "usePoolPresets", config="project")
        return usePresets

    @err_catcher(name=__name__)
    def getDeadlinePoolPresets(self):
        if not self.getUseDeadlinePoolPresets():
            return []

        presets = self.core.getConfig("deadline", "poolPresets", config="project")
        names = [p.get("name", "") for p in presets]
        return names

    @err_catcher(name=__name__)
    def getPoolPresetData(self, preset):
        presets = self.core.getConfig("deadline", "poolPresets", config="project")
        matches = [p for p in presets if p.get("name") == preset]
        if matches:
            return matches[0]

    @err_catcher(name=__name__)
    def onRefreshPoolsClicked(self, settings):
        self.refreshPools()
        self.refreshGroups()
        settings.gb_dlPoolPresets.refresh()

    @err_catcher(name=__name__)
    def projectSettings_loadUI(self, origin):
        self.addUiToProjectSettings(origin)

    @err_catcher(name=__name__)
    def addUiToProjectSettings(self, projectSettings):
        projectSettings.w_deadline = QWidget()
        lo_deadline = QGridLayout()
        projectSettings.w_deadline.setLayout(lo_deadline)

        projectSettings.chb_submitScenes = QCheckBox("Submit scenefiles together with jobs")
        projectSettings.chb_submitScenes.setToolTip("When checked the scenefile, from which a Deadline job gets submitted, will be copied to the Deadline repository.\nWhen disabled When disabled the Deadline Workers will open the scenefile at the original location. This can be useful when using relative filepaths, but has the risk of getting overwritten by artists while a job is rendering.")
        projectSettings.chb_submitScenes.setChecked(True)
        lo_deadline.addWidget(projectSettings.chb_submitScenes)

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

        sp_stretch = QSpacerItem(0, 0, QSizePolicy.Fixed, QSizePolicy.Expanding)
        lo_deadline.addItem(sp_stretch)
        projectSettings.addTab(projectSettings.w_deadline, "Deadline")

    @err_catcher(name=__name__)
    def preProjectSettingsLoad(self, origin, settings):
        if not settings:
            return
        
        if "deadline" in settings:
            if "submitScenes" in settings["deadline"]:
                val = settings["deadline"]["submitScenes"]
                origin.chb_submitScenes.setChecked(val)

            if "usePoolPresets" in settings["deadline"]:
                val = settings["deadline"]["usePoolPresets"]
                origin.gb_dlPoolPresets.setChecked(val)

            if "poolPresets" in settings["deadline"]:
                val = settings["deadline"]["poolPresets"]
                if val:
                    origin.gb_dlPoolPresets.loadPresetData(val)

    @err_catcher(name=__name__)
    def preProjectSettingsSave(self, origin, settings):
        if "deadline" not in settings:
            settings["deadline"] = {}
            settings["deadline"]["submitScenes"] = origin.chb_submitScenes.isChecked()
            settings["deadline"]["usePoolPresets"] = origin.gb_dlPoolPresets.isChecked()
            settings["deadline"]["poolPresets"] = origin.gb_dlPoolPresets.getPresetData()

    @err_catcher(name=__name__)
    def prePublish(self, origin):
        origin.submittedDlJobs = {}
        origin.submittedDlJobData = {}

    @err_catcher(name=__name__)
    def postPublish(self, origin, pubType, result):
        origin.submittedDlJobs = {}
        origin.submittedDlJobData = {}

    @err_catcher(name=__name__)
    def sm_updateDlDeps(self, origin, item, column):
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
    def sm_dlGoToNode(self, item, column):
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
    def sm_dep_updateUI(self, origin):
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
    def updateUiJobCompleted(self, origin):
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
    def updateUiFramesCompleted(self, origin):
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
    def updateUiFileExists(self, origin):
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
    def sm_dep_preExecute(self, origin):
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def sm_dep_execute(self, origin, parent):
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
    def onStateStartup(self, state):
        if state.className == "Dependency":
            state.tw_caches.itemClicked.connect(
                lambda x, y: self.sm_updateDlDeps(state, x, y)
            )
            state.tw_caches.itemDoubleClicked.connect(self.sm_dlGoToNode)
        else:
            if hasattr(state, "cb_dlPool"):
                state.cb_dlPool.addItems(self.getDeadlinePools())

            if hasattr(state, "cb_dlGroup"):
                state.cb_dlGroup.addItems(self.getDeadlineGroups())

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
                state.cb_dlPool.addItems(self.getDeadlinePools())
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
                state.cb_sndPool.addItems(self.getDeadlinePools())
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
                state.cb_dlGroup.addItems(self.getDeadlineGroups())
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

    @err_catcher(name=__name__)
    def presetChanged(self, state):
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
    def showHighPrioJobPresets(self, state):
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
    def onStateGetSettings(self, state, settings):
        if hasattr(state, "gb_submit"):
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

    @err_catcher(name=__name__)
    def onStateSettingsLoaded(self, state, settings):
        if hasattr(state, "gb_submit"):
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

    @err_catcher(name=__name__)
    def sm_houExport_activated(self, origin):
        origin.f_osDependencies.setVisible(False)
        origin.f_osUpload.setVisible(False)
        origin.f_osPAssets.setVisible(False)
        origin.gb_osSlaves.setVisible(False)

    @err_catcher(name=__name__)
    def sm_houExport_preExecute(self, origin):
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def sm_houRender_updateUI(self, origin):
        showGPUsettings = (
            origin.node is not None and origin.node.type().name() == "Redshift_ROP"
        )
        origin.w_dlGPUpt.setVisible(showGPUsettings)
        origin.w_dlGPUdevices.setVisible(showGPUsettings)

    @err_catcher(name=__name__)
    def sm_houRender_managerChanged(self, origin):
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
    def sm_houRender_preExecute(self, origin):
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def sm_render_updateUI(self, origin):
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

    @err_catcher(name=__name__)
    def sm_render_managerChanged(self, origin):
        getattr(self.core.appPlugin, "sm_render_managerChanged", lambda x, y: None)(
            origin, False
        )

    @err_catcher(name=__name__)
    def sm_render_preExecute(self, origin):
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def getCurrentSceneFiles(self, origin):
        curFileName = self.core.getCurrentFileName()
        scenefiles = [curFileName]
        return scenefiles

    @err_catcher(name=__name__)
    def getJobName(self, details=None, origin=None):
        scenefileName = os.path.splitext(self.core.getCurrentFileName(path=False))[0]
        details = details or {}
        context = details.copy()
        context["scenefilename"] = scenefileName
        if origin and getattr(origin, "node", None):
            try:
                context["ropname"] = origin.node.name()
            except:
                pass

        jobName = self.core.projects.getResolvedProjectStructurePath("deadlineJobName", context=context, fallback="")
        return jobName

    @err_catcher(name=__name__)
    def processHoudiniPath(self, origin, jobOutputFile):
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
        origin,
        jobOutputFile,
        parent,
        files=None,
        isSecondJob=False,
        prio=None,
        frames=None,
        handleMaster=False,
        details=None,
        allowCleanup=True,
        jobnameSuffix=None,
        useBatch=None,
        sceneDescription=None,
        skipSubmission=False
    ):
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
                result = self.sm_render_submitJob(
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
                    sceneDescription=sceneDescription,
                )
                
                if not frameStr:
                    return result
            else:
                renderSecondJob = False

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

        if sceneDescription or handleMaster or useBatch or jobInfos.get("TileJob"):
            if jobInfos.get("TileJob"):
                jobBatchName += " (%s tiles)" % rows**2

            jobInfos["BatchName"] = jobBatchName

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
            res = self.core.appPlugin.getResolution()
            jobInfos["AssembledRenderWidth"] = res[0]
            jobInfos["AssembledRenderHeight"] = res[1]
            aovs = [""]
            if self.core.appPlugin.pluginName == "3dsMax":
                aovs += self.core.appPlugin.sm_render_getAovNames()

            for idx, aov in enumerate(aovs):
                for row in range(rows):
                    for column in range(rows):
                        tileStr = "_tile_%sx%s_%sx%s_" % (column+1, row+1, rows, rows)
                        tileNum = (row*rows)+(column)
                        # tileOutname = base + tileStr + ".%04d" % startFrame + ext

                        if aov:
                            aovBase = os.path.join(os.path.dirname(os.path.dirname(base)), aov, os.path.basename(base).replace("beauty", aov))
                            tileOutname = aovBase + tileStr + "." + ext
                            pluginInfos["RegionReFilename%s_%s" % (tileNum, idx-1)] = tileOutname
                        else:
                            tileOutname = base + tileStr + "." + ext
                            pluginInfos["RegionTop%s" % tileNum] = int((jobInfos["AssembledRenderHeight"] / rows) * row)
                            pluginInfos["RegionBottom%s" % tileNum] = int(pluginInfos["RegionTop%s" % tileNum] + (jobInfos["AssembledRenderHeight"] / rows))
                            pluginInfos["RegionLeft%s" % tileNum] = int((jobInfos["AssembledRenderWidth"] / rows) * column)
                            pluginInfos["RegionRight%s" % tileNum] = int(pluginInfos["RegionLeft%s" % tileNum] + (jobInfos["AssembledRenderWidth"] / rows))
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
        if not skipSubmission:
            result = self.deadlineSubmitJob(jobInfos, pluginInfos, arguments)
            self.registerSubmittedJob(origin, result, data=dlParams)
            jobId = self.getJobIdFromSubmitResult(result)

        if (jobId or skipSubmission) and sceneDescription:
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
                res = self.core.appPlugin.getResolution()
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
                )

            if handleMaster and not isSecondJob:
                self.handleMaster(origin, handleMaster, jobId, jobOutputFileOrig, jobName)

        return result

    @err_catcher(name=__name__)
    def registerSubmittedJob(self, state, submitResult, data=None):
        jobId = self.getJobIdFromSubmitResult(submitResult)
        if not jobId:
            return

        if state.uuid not in state.stateManager.submittedDlJobs:
            state.stateManager.submittedDlJobs[state.uuid] = []

        state.stateManager.submittedDlJobs[state.uuid].append(jobId)
        state.stateManager.submittedDlJobData[jobId] = data
        return jobId

    @err_catcher(name=__name__)
    def getSubmittedJobIdsFromState(self, sm, stateId):
        if not sm.submittedDlJobs:
            return

        if stateId not in sm.submittedDlJobs:
            return

        return sm.submittedDlJobs[stateId]

    @err_catcher(name=__name__)
    def addEnvironmentItem(self, data, key, value):
        idx = 0
        while True:
            k = "EnvironmentKeyValue" + str(idx)
            if k not in data:
                data[k] = "%s=%s" % (key, value)
                break

            idx += 1

        return data

    @err_catcher(name=__name__)
    def handleMaster(self, origin, masterType, jobId, jobOutputFile, jobName):
        jobData = origin.stateManager.submittedDlJobData[jobId]
        code = """
import sys

root = \"%s\"
sys.path.append(root + "/Scripts")

import PrismCore
pcore = PrismCore.create(prismArgs=["noUI", "loadProject"])
path = r\"%s\"
""" % (self.core.prismRoot, jobOutputFile)

        if masterType == "media":
            masterAction = origin.cb_master.currentText()
            if masterAction == "Set as master":
                code += "pcore.mediaProducts.updateMasterVersion(path)"
            elif masterAction == "Add to master":
                code += "pcore.mediaProducts.addToMasterVersion(path)"
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

        jobName = jobName + "_updateMaster"
        self.submitPythonJob(
            code=code,
            jobName=jobName,
            jobPrio=prio,
            jobPool=jobData["jobInfos"]["Pool"],
            jobSndPool=jobData["jobInfos"]["SecondaryPool"],
            jobGroup=jobData["jobInfos"]["Group"],
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
    def submitSceneDescriptionMantra(self, origin, jobId, jobOutputFile, jobOutputFileOrig, allowCleanup, jobParams):
        dep = [{"offset": 0, "filepath": jobOutputFile, "type": "file"}]
        args = [jobOutputFile, jobOutputFileOrig]
        if self.core.getConfig(
            "render", "MantraCleanupJob", dft=True, config="project"
        ) and allowCleanup:
            cleanupScript = origin.curRenderer.getCleanupScript()
        else:
            cleanupScript = None

        jobData = jobParams
        basename = jobData["jobInfos"]["Name"][:-len(self.sceneDescriptions["mantra"]["suffix"])]
        result = self.submitMantraJob(
            jobName=basename + "_render",
            jobOutput=jobOutputFileOrig,
            jobPrio=jobData["jobInfos"]["Priority"],
            jobPool=jobData["jobInfos"]["Pool"],
            jobSndPool=jobData["jobInfos"]["SecondaryPool"],
            jobGroup=jobData["jobInfos"]["Group"],
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
    def submitSceneDescription3Delight(self, origin, jobId, jobOutputFile, jobOutputFileOrig, allowCleanup, jobParams):
        code = origin.curRenderer.getNsiRenderScript()
        nsiDep = [{"offset": 0, "filepath": jobOutputFile, "type": "file"}]
        dlpath = os.getenv("DELIGHT")
        environment = [["DELIGHT", dlpath]]
        args = [jobOutputFile, jobOutputFileOrig]
        jobData = jobParams
        basename = jobData["jobInfos"]["Name"][:-len(self.sceneDescriptions["3delight"]["suffix"])]
        result = self.submitPythonJob(
            code=code,
            jobName=basename + "_render",
            jobOutput=jobOutputFileOrig,
            jobPrio=jobData["jobInfos"]["Priority"],
            jobPool=jobData["jobInfos"]["Pool"],
            jobSndPool=jobData["jobInfos"]["SecondaryPool"],
            jobGroup=jobData["jobInfos"]["Group"],
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
            arguments = ["\"%s\"" % args[0]]
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
    def submitSceneDescriptionRedshift(self, origin, jobId, jobOutputFile, jobOutputFileOrig, allowCleanup, jobParams):
        rsDep = [{"offset": 0, "filepath": jobOutputFile, "type": "file"}]
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
        result = self.submitRedshiftJob(
            jobName=basename + "_render",
            jobOutput=jobOutputFileOrig,
            jobPrio=jobData["jobInfos"]["Priority"],
            jobPool=jobData["jobInfos"]["Pool"],
            jobSndPool=jobData["jobInfos"]["SecondaryPool"],
            jobGroup=jobData["jobInfos"]["Group"],
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
    def submitSceneDescriptionArnold(self, origin, jobId, jobOutputFile, jobOutputFileOrig, allowCleanup, jobParams):
        rsDep = [{"offset": 0, "filepath": jobOutputFile, "type": "file"}]
        args = [jobOutputFile, jobOutputFileOrig]
        if self.core.getConfig(
            "render", "ArnoldCleanupJob", dft=True, config="project"
        ) and allowCleanup:
            cleanupScript = origin.curRenderer.getCleanupScript()
        else:
            cleanupScript = None

        jobData = jobParams
        basename = jobData["jobInfos"]["Name"][:-len(self.sceneDescriptions["arnold"]["suffix"])]
        result = self.submitArnoldJob(
            jobName=basename + "_render",
            jobOutput=jobOutputFileOrig,
            jobPrio=jobData["jobInfos"]["Priority"],
            jobPool=jobData["jobInfos"]["Pool"],
            jobSndPool=jobData["jobInfos"]["SecondaryPool"],
            jobGroup=jobData["jobInfos"]["Group"],
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
    def getMantraOutputPath(self, origin, jobOutputFile):
        jobOutputFile = os.path.join(
            os.path.dirname(jobOutputFile), "_ifd", os.path.basename(jobOutputFile)
        )
        jobOutputFile = os.path.splitext(jobOutputFile)[0] + ".ifd"
        return jobOutputFile

    @err_catcher(name=__name__)
    def get3DelightOutputPath(self, origin, jobOutputFile):
        jobOutputFile = origin.curRenderer.getNsiOutputPath(
            origin, jobOutputFile
        )
        return jobOutputFile

    @err_catcher(name=__name__)
    def getRedshiftOutputPath(self, origin, jobOutputFile):
        jobOutputFile = os.path.join(
            os.path.dirname(jobOutputFile), "_rs", os.path.basename(jobOutputFile)
        )
        jobOutputFile = os.path.splitext(jobOutputFile)[0] + ".rs"
        return jobOutputFile

    @err_catcher(name=__name__)
    def getArnoldOutputPath(self, origin, jobOutputFile):
        jobOutputFile = os.path.join(
            os.path.dirname(jobOutputFile), "_ass", os.path.basename(jobOutputFile)
        )
        jobOutputFile = os.path.splitext(jobOutputFile)[0] + ".ass"
        return jobOutputFile

    @err_catcher(name=__name__)
    def submitPythonJob(
        self,
        code="",
        version="3.9",
        jobName=None,
        jobOutput=None,
        jobPool="None",
        jobSndPool="None",
        jobGroup="None",
        jobPrio=50,
        jobTimeOut=180,
        jobMachineLimit=0,
        jobFramesPerTask=1,
        jobConcurrentTasks=None,
        jobComment=None,
        jobBatchName=None,
        frames="1",
        suspended=False,
        dependencies=None,
        jobDependencies=None,
        environment=None,
        args=None,
        state=None,
    ):
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
            homeDir, "temp", "%s_%s.py" % (jobName, int(time.time()))
        )
        with open(scriptFile, "w") as f:
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
        for i in getattr(self.core.appPlugin, "getCurrentSceneFiles", self.getCurrentSceneFiles)(self):
            arguments.append(i)

        if "dependencyFile" in locals():
            arguments.append(dependencyFile)

        result = self.deadlineSubmitJob(jobInfos, pluginInfos, arguments)
        if state:
            self.registerSubmittedJob(state, result, dlParams)

        return result

    @err_catcher(name=__name__)
    def submitDraftTileAssemblerJob(
        self,
        jobName=None,
        jobOutput=None,
        jobPool="None",
        jobSndPool="None",
        jobGroup="None",
        jobPrio=50,
        jobTimeOut=180,
        jobMachineLimit=0,
        jobFramesPerTask=1,
        jobConcurrentTasks=None,
        jobComment=None,
        jobBatchName=None,
        frames="1",
        suspended=False,
        dependencies=None,
        jobDependencies=None,
        environment=None,
        args=None,
        state=None,
        rows=2,
        resX=1920,
        resY=1080,
        startFrame=1,
    ):
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

        aovs = [""]
        if self.core.appPlugin.pluginName == "3dsMax":
            aovs += self.core.appPlugin.sm_render_getAovNames()

        cfgFiles = []
        for idx, aov in enumerate(aovs):
            if aov:
                aovKey = "_" + aov
            else:
                aovKey = aov

            cfgFile = os.path.join(
                homeDir, "temp", "%s%s_%s.txt" % (jobName, aovKey, int(time.time()))
            )

            if aov:
                aovPath = os.path.join(os.path.dirname(os.path.dirname(jobOutput)), aov, os.path.basename(jobOutput).replace("beauty", aov))
            else:
                aovPath = jobOutput

            cfgData = {
                "ImageFileName": aovPath,
                "TileCount": rows**2,
                "TilesCropped": True,
                "DistanceAsPixels": True,
                "ImageWidth": resX,
                "ImageHeight": resY,
            }
            base, ext = os.path.splitext(aovPath)
            for row in range(rows):
                for column in range(rows):
                    tileStr = "_tile_%sx%s_%sx%s_" % (column+1, row+1, rows, rows)
                    tileNum = (row*rows)+(column)
                    cfgData["Tile%sFileName" % tileNum] = base + tileStr + ".%04d" % startFrame + ext
                    # cfgData["Tile%sFileName" % tileNum] = base + tileStr + ext
                    cfgData["Tile%sX" % tileNum] = (resX / rows) * column
                    cfgData["Tile%sY" % tileNum] = resY - ((resY / rows) * (row + 1))

            with open(cfgFile, "w") as fileHandle:
                for key in cfgData:
                    fileHandle.write("%s=%s\n" % (key, cfgData[key]))

            cfgFiles.append(cfgFile)

        environment = environment or []
        environment.insert(0, ["prism_project", self.core.prismIni.replace("\\", "/")])

        # Create submission info file

        jobInfos = {}

        jobInfos["Name"] = jobName.replace(" - Tile Render", "") + " - Draft Tile Assembly"
        jobInfos["Pool"] = jobPool
        jobInfos["SecondaryPool"] = jobSndPool
        jobInfos["Group"] = jobGroup
        jobInfos["Priority"] = jobPrio
        jobInfos["TaskTimeoutMinutes"] = jobTimeOut
        jobInfos["MachineLimit"] = jobMachineLimit
        if len(aovs) > 1:
            jobInfos["Frames"] = "0-%s" % (len(aovs)-1)
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
                aovs = self.core.appPlugin.sm_render_getAovNames()
                for idx, aov in enumerate(aovs):
                    jobInfos["OutputFilename%s" % (idx + 1)] = os.path.join(os.path.dirname(os.path.dirname(jobOutput)), aov, os.path.basename(jobOutput).replace("beauty", aov))

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
        jobName=None,
        jobOutput=None,
        jobPool="None",
        jobSndPool="None",
        jobGroup="None",
        jobPrio=50,
        jobTimeOut=180,
        jobMachineLimit=0,
        jobFramesPerTask=1,
        jobConcurrentTasks=None,
        jobComment=None,
        jobBatchName=None,
        frames="1",
        suspended=False,
        dependencies=None,
        archivefile=None,
        environment=None,
        args=None,
        cleanupScript=None,
        state=None,
    ):
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
            arguments = ["\"%s\"" % args[0]]
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
        jobName=None,
        jobOutput=None,
        jobPool="None",
        jobSndPool="None",
        jobGroup="None",
        jobPrio=50,
        jobTimeOut=180,
        jobMachineLimit=0,
        jobFramesPerTask=1,
        jobConcurrentTasks=None,
        jobComment=None,
        jobBatchName=None,
        frames="1",
        suspended=False,
        dependencies=None,
        archivefile=None,
        gpusPerTask=None,
        gpuDevices=None,
        environment=None,
        args=None,
        cleanupScript=None,
        state=None,
    ):
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
            arguments = ["\"%s\"" % args[0]]
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
        jobName=None,
        jobOutput=None,
        jobPool="None",
        jobSndPool="None",
        jobGroup="None",
        jobPrio=50,
        jobTimeOut=180,
        jobMachineLimit=0,
        jobFramesPerTask=1,
        jobConcurrentTasks=None,
        jobComment=None,
        jobBatchName=None,
        frames="1",
        suspended=False,
        dependencies=None,
        archivefile=None,
        environment=None,
        args=None,
        cleanupScript=None,
        state=None,
    ):
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
            arguments = ["\"%s\"" % args[0]]
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
    def getJobIdFromSubmitResult(self, result):
        result = str(result)
        lines = result.split("\n")
        for line in lines:
            if line.startswith("JobID"):
                jobId = line.split("=")[1]
                return jobId

    @err_catcher(name=__name__)
    def submitCleanupScript(
        self,
        jobName=None,
        jobOutput=None,
        jobPool="None",
        jobSndPool="None",
        jobGroup="None",
        jobPrio=50,
        jobTimeOut=180,
        jobMachineLimit=0,
        jobComment=None,
        jobBatchName=None,
        suspended=False,
        jobDependencies=None,
        environment=None,
        cleanupScript=None,
        arguments=None,
        state=None,
    ):
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
    def deadlineSubmitJob(self, jobInfos, pluginInfos, arguments):
        self.core.callback(
            name="preSubmit_Deadline",
            args=[self, jobInfos, pluginInfos, arguments],
        )

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

        self.core.callback(name="postSubmit_Deadline", args=[self, jobResult, jobInfos, pluginInfos, arguments],)

        return jobResult

    @err_catcher(name=__name__)
    def getRedshiftCleanupScript(self):
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
    def __init__(self, plugin, presetData=None):
        super(PresetWidget, self).__init__()
        self.plugin = plugin
        self.core = self.plugin.core
        self.core.parentWindow(self)

        self.loadLayout()
        self.connectEvents()
        if presetData:
            self.loadPresetData(presetData)

    @err_catcher(name=__name__)
    def loadLayout(self):
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
    def connectEvents(self):
        self.b_add.clicked.connect(self.addItem)

    @err_catcher(name=__name__)
    def refresh(self):
        data = self.getPresetData()
        self.clearItems()
        self.loadPresetData(data)

    @err_catcher(name=__name__)
    def loadPresetData(self, presetData):
        self.clearItems()
        for preset in presetData:
            self.addItem(
                name=preset["name"],
                pool=preset["pool"],
                secondaryPool=preset["secondaryPool"],
                group=preset["group"]
            )

    @err_catcher(name=__name__)
    def addItem(self, name=None, pool=None, secondaryPool=None, group=None):
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
    def removeItem(self, item):
        idx = self.lo_preset.indexOf(item)
        if idx != -1:
            w = self.lo_preset.takeAt(idx)
            if w.widget():
                w.widget().deleteLater()

    @err_catcher(name=__name__)
    def clearItems(self):
        for idx in reversed(range(self.lo_preset.count())):
            item = self.lo_preset.takeAt(idx)
            w = item.widget()
            if w:
                w.setVisible(False)
                w.deleteLater()

    @err_catcher(name=__name__)
    def getPresetData(self):
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

    def __init__(self, plugin):
        super(PresetItem, self).__init__()
        self.plugin = plugin
        self.core = self.plugin.core
        self.loadLayout()

    @err_catcher(name=__name__)
    def loadLayout(self):
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
    def name(self):
        return self.e_name.text()

    @err_catcher(name=__name__)
    def setName(self, name):
        return self.e_name.setText(name)

    @err_catcher(name=__name__)
    def pool(self):
        return self.cb_pool.currentText()

    @err_catcher(name=__name__)
    def setPool(self, pool):
        idx = self.cb_pool.findText(pool)
        if idx != -1:
            self.cb_pool.setCurrentIndex(idx)

    @err_catcher(name=__name__)
    def secondaryPool(self):
        return self.cb_secondaryPool.currentText()

    @err_catcher(name=__name__)
    def setSecondaryPool(self, secondaryPool):
        idx = self.cb_secondaryPool.findText(secondaryPool)
        if idx != -1:
            self.cb_secondaryPool.setCurrentIndex(idx)

    @err_catcher(name=__name__)
    def group(self):
        return self.cb_group.currentText()

    @err_catcher(name=__name__)
    def setGroup(self, group):
        idx = self.cb_group.findText(group)
        if idx != -1:
            self.cb_group.setCurrentIndex(idx)
