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
import subprocess
import time

try:
    import hou
except:
    pass

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

from PrismUtils.Decorators import err_catcher as err_catcher


class Prism_Deadline_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

    @err_catcher(name=__name__)
    def isActive(self):
        try:
            return len(self.getDeadlineGroups()) > 0
        except:
            return False

    @err_catcher(name=__name__)
    def deadlineCommand(self, arguments, background=True, readStdout=True):
        deadlineBin = os.getenv("DEADLINE_PATH")
        if deadlineBin is None:
            return False

        deadlineCommand = os.path.join(deadlineBin, "deadlinecommand.exe")
        if not os.path.exists(deadlineCommand):
            return False

        startupinfo = None
        creationflags = 0
        if background:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
        else:
            # still show top-level windows, but don't show a console window
            CREATE_NO_WINDOW = 0x08000000  # MSDN process creation flag
            creationflags = CREATE_NO_WINDOW

        arguments.insert(0, deadlineCommand)

        stdoutPipe = None
        if readStdout:
            stdoutPipe = subprocess.PIPE

        # Specifying PIPE for all handles to workaround a Python bug on Windows. The unused handles are then closed immediatley afterwards.
        proc = subprocess.Popen(
            arguments,
            cwd=deadlineBin,
            stdin=subprocess.PIPE,
            stdout=stdoutPipe,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )
        proc.stdin.close()
        proc.stderr.close()

        output = ""
        if readStdout:
            output = proc.stdout.read()
        return output

    @err_catcher(name=__name__)
    def blenderDeadlineCommand(self):
        deadlineBin = ""
        try:
            deadlineBin = os.environ["DEADLINE_PATH"]
        except KeyError:
            pass

        if deadlineBin == "":
            return

        deadlineCommand = os.path.join(deadlineBin, "deadlinecommand.exe")

        if not os.path.exists(deadlineCommand):
            return

        return deadlineCommand

    @err_catcher(name=__name__)
    def getDeadlineGroups(self, subdir=None):
        if not hasattr(self, "deadlineGroups"):
            if sys.version[0] == "3":
                deadlineCommand = self.blenderDeadlineCommand()

                if deadlineCommand is None:
                    return []

                startupinfo = None

                args = [deadlineCommand, "-groups"]
                if subdir != None and subdir != "":
                    args.append(subdir)

                # Specifying PIPE for all handles to workaround a Python bug on Windows. The unused handles are then closed immediatley afterwards.
                proc = subprocess.Popen(
                    args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    startupinfo=startupinfo,
                )

                proc.stdin.close()
                proc.stderr.close()

                output = proc.stdout.read()

                output = output.decode("utf_8")

            else:
                output = self.deadlineCommand(["-groups"])

            if output != False and not "Error" in output:
                self.deadlineGroups = output.splitlines()
            else:
                self.deadlineGroups = []

        return self.deadlineGroups

    @err_catcher(name=__name__)
    def sm_dep_startup(self, origin):
        origin.tw_caches.itemClicked.connect(
            lambda x, y: self.sm_updateDlDeps(origin, x, y)
        )
        origin.tw_caches.itemDoubleClicked.connect(self.sm_dlGoToNode)

    @err_catcher(name=__name__)
    def sm_updateDlDeps(self, origin, item, column):
        if len(item.toolTip(0).split("\n")) == 1:
            return

        if (
            item.toolTip(0).split("\n")[1]
            in [x.split("\n")[1] for x in origin.dependencies["Deadline"]]
            and item.checkState(0) == Qt.Unchecked
        ):
            origin.dependencies["Deadline"].remove(item.toolTip(0))
        elif (
            not item.toolTip(0).split("\n")[1]
            in [x.split("\n")[1] for x in origin.dependencies["Deadline"]]
        ) and item.checkState(0) == Qt.Checked:
            origin.dependencies["Deadline"].append(item.toolTip(0))

        origin.nameChanged(origin.e_name.text())

        origin.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def sm_dlGoToNode(self, item, column):
        if item.parent() is None:
            return

        node = hou.node(item.toolTip(0).split("\n")[1])

        if node is not None:
            node.setCurrent(True, clear_all_selected=True)
            paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
            if paneTab is not None:
                paneTab.frameSelection()

    @err_catcher(name=__name__)
    def sm_dep_updateUI(self, origin):
        origin.gb_osDependency.setVisible(False)
        origin.gb_dlDependency.setVisible(True)

        origin.tw_caches.clear()
        QTreeWidgetItem(origin.tw_caches, ["Import"])
        QTreeWidgetItem(origin.tw_caches, ["Export"])

        fileNodeList = []
        copFileNodeList = []
        ropDopNodeList = []
        ropCopNodeList = []
        ropSopNodeList = []
        ropAbcNodeList = []
        filecacheNodeList = []

        for node in hou.node("/").allSubChildren():
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

        for i in fileNodeList:
            itemName = os.path.basename(i.path())
            item = QTreeWidgetItem(origin.tw_caches.topLevelItem(0), [itemName])
            item.setToolTip(0, i.parm("file").unexpandedString() + "\n" + i.path())

        for i in copFileNodeList:
            itemName = os.path.basename(i.path())
            item = QTreeWidgetItem(origin.tw_caches.topLevelItem(0), [itemName])
            item.setToolTip(0, i.parm("filename1").unexpandedString() + "\n" + i.path())

        for i in ropDopNodeList:
            itemName = os.path.basename(i.path())
            item = QTreeWidgetItem(origin.tw_caches.topLevelItem(1), [itemName])
            item.setToolTip(0, i.parm("dopoutput").unexpandedString() + "\n" + i.path())

        for i in ropCopNodeList:
            itemName = os.path.basename(i.path())
            item = QTreeWidgetItem(origin.tw_caches.topLevelItem(1), [itemName])
            item.setToolTip(0, i.parm("copoutput").unexpandedString() + "\n" + i.path())

        for i in ropSopNodeList:
            itemName = os.path.basename(i.path())
            item = QTreeWidgetItem(origin.tw_caches.topLevelItem(1), [itemName])
            item.setToolTip(0, i.parm("sopoutput").unexpandedString() + "\n" + i.path())

        for i in filecacheNodeList:
            itemName = os.path.basename(i.path())
            item = QTreeWidgetItem(origin.tw_caches.topLevelItem(1), [itemName])
            item.setToolTip(0, i.parm("file").unexpandedString() + "\n" + i.path())

        # alembic dependency disabled because no progress measureable
        for i in ropAbcNodeList:
            itemName = os.path.basename(i.parm("filename").unexpandedString())
            item = QTreeWidgetItem(origin.tw_caches.topLevelItem(1), [itemName])
            item.setToolTip(0, i.parm("filename").unexpandedString() + "\n" + i.path())

        items = []
        for i in range(origin.tw_caches.topLevelItemCount()):
            origin.tw_caches.topLevelItem(i).setExpanded(True)
            for k in range(origin.tw_caches.topLevelItem(i).childCount()):
                items.append(origin.tw_caches.topLevelItem(i).child(k))

        newActive = []
        for i in items:
            if i.toolTip(0).split("\n")[1] in [
                x.split("\n")[1] for x in origin.dependencies["Deadline"]
            ]:
                i.setCheckState(0, Qt.Checked)
                newActive.append(i.toolTip(0))
            else:
                i.setCheckState(0, Qt.Unchecked)

        origin.dependencies["Deadline"] = newActive

    @err_catcher(name=__name__)
    def sm_dep_preExecute(self, origin):
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def sm_dep_execute(self, origin, parent):
        origin.dependencies["Deadline"] = [
            x
            if not x.split("\n")[0]
            in origin.stateManager.publishInfos["updatedExports"]
            else "%s\n%s"
            % (
                origin.stateManager.publishInfos["updatedExports"][x.split("\n")[0]],
                x.split("\n")[1],
            )
            for x in origin.dependencies["Deadline"]
        ]

        parent.dependencies += [
            [origin.sp_offset.value(), hou.expandString(x.split("\n")[0])]
            for x in origin.dependencies["Deadline"]
        ]

    @err_catcher(name=__name__)
    def sm_houExport_startup(self, origin):
        origin.cb_dlGroup.addItems(self.getDeadlineGroups())

    @err_catcher(name=__name__)
    def sm_houExport_activated(self, origin):
        origin.f_osDependencies.setVisible(False)
        origin.f_osUpload.setVisible(False)
        origin.f_osPAssets.setVisible(False)
        origin.gb_osSlaves.setVisible(False)
        origin.f_dlGroup.setVisible(True)

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
        origin.f_dlGroup.setVisible(True)

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
        curRenderer = getattr(self.core.appPlugin, "getCurrentRenderer", lambda x: "")(
            origin
        ).lower()
        showGPUsettings = "redshift" in curRenderer if curRenderer else True
        origin.w_dlGPUpt.setVisible(showGPUsettings)
        origin.w_dlGPUdevices.setVisible(showGPUsettings)

    @err_catcher(name=__name__)
    def sm_render_managerChanged(self, origin):
        origin.f_osDependencies.setVisible(False)
        origin.gb_osSlaves.setVisible(False)
        origin.f_osUpload.setVisible(False)

        origin.f_dlGroup.setVisible(True)
        origin.w_dlConcurrentTasks.setVisible(True)

        curRenderer = getattr(self.core.appPlugin, "getCurrentRenderer", lambda x: "")(
            origin
        ).lower()
        showGPUsettings = "redshift" in curRenderer if curRenderer else True
        origin.w_dlGPUpt.setVisible(showGPUsettings)
        origin.w_dlGPUdevices.setVisible(showGPUsettings)

        getattr(self.core.appPlugin, "sm_render_managerChanged", lambda x, y: None)(
            origin, False
        )

    @err_catcher(name=__name__)
    def sm_render_preExecute(self, origin):
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def sm_render_submitJob(self, origin, jobOutputFile, parent):
        if self.core.appPlugin.pluginName == "Houdini":
            jobOutputFile = jobOutputFile.replace("$F4", "#"*self.core.framePadding)

        homeDir = (
            self.deadlineCommand(["-GetCurrentUserHomeDirectory"], background=False)
        ).decode("utf-8")

        if homeDir is False:
            return "Execute Canceled: Deadline is not installed"

        homeDir = homeDir.replace("\r", "").replace("\n", "")

        dependencies = parent.dependencies

        if hasattr(origin, "w_renderNSIs") and not origin.w_renderNSIs.isHidden() and origin.chb_rjNSIs.isChecked():
            renderNSIs = True
            jobOutputFileOrig = jobOutputFile
            jobOutputFile = os.path.join(os.path.dirname(jobOutputFile), "_nsi", os.path.basename(jobOutputFile))
            jobOutputFile = os.path.splitext(jobOutputFile)[0] + ".nsi"
        else:
            renderNSIs = False

        if hasattr(origin, "w_renderRS") and not origin.w_renderRS.isHidden() and origin.chb_rjRS.isChecked():
            renderRS = True
            jobOutputFileOrig = jobOutputFile
            jobOutputFile = os.path.join(os.path.dirname(jobOutputFile), "_rs", os.path.basename(jobOutputFile))
            jobOutputFile = os.path.splitext(jobOutputFile)[0] + ".rs"
        else:
            renderRS = False

        jobName = (
            os.path.splitext(self.core.getCurrentFileName(path=False))[0]
            + origin.l_taskName.text()
        )
        jobGroup = origin.cb_dlGroup.currentText()
        jobPrio = origin.sp_rjPrio.value()
        jobTimeOut = str(origin.sp_rjTimeout.value())
        jobMachineLimit = "0"
        jobFramesPerTask = origin.sp_rjFramesPerTask.value()
        jobBatchName = jobName
        suspended = origin.chb_rjSuspended.isChecked()

        if (
            hasattr(origin, "w_dlConcurrentTasks")
            and not origin.w_dlConcurrentTasks.isHidden()
        ):
            jobConcurrentTasks = origin.sp_dlConcurrentTasks.value()
        else:
            jobConcurrentTasks = None

        rangeType = origin.cb_rangeType.currentText()
        frames = origin.getFrameRange(rangeType)
        if rangeType != "Expression":
            startFrame, endFrame = frames
            if rangeType == "Single Frame":
                endFrame = startFrame
            frameStr = "%s-%s" % (int(startFrame), int(endFrame))
        else:
            frameStr = ",".join([str(x) for x in frames])

        # Create submission info file

        jobInfos = {}

        if renderNSIs:
            jobInfos["Name"] = jobName + "_nsi"
        elif renderRS:
            jobInfos["Name"] = jobName + "_rs"
        else:
            jobInfos["Name"] = jobName

        jobInfos["Group"] = jobGroup
        jobInfos["Priority"] = jobPrio
        jobInfos["TaskTimeoutMinutes"] = jobTimeOut
        jobInfos["MachineLimit"] = jobMachineLimit
        jobInfos["Frames"] = frameStr
        jobInfos["ChunkSize"] = jobFramesPerTask
        jobInfos["OutputFilename0"] = jobOutputFile
        jobInfos[
            "EnvironmentKeyValue0"
        ] = "prism_project=%s" % self.core.prismIni.replace("\\", "/")

        if suspended:
            jobInfos["InitialStatus"] = "Suspended"

        if jobConcurrentTasks:
            jobInfos["ConcurrentTasks"] = jobConcurrentTasks

        if renderNSIs or renderRS:
            jobInfos["BatchName"] = jobBatchName

        if len(dependencies) > 0:
            jobInfos["IsFrameDependent"] = "true"
            jobInfos["ScriptDependencies"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "DeadlineDependency.py"))

        # Create plugin info file

        pluginInfos = {}
        pluginInfos["Build"] = "64bit"

        if hasattr(origin, "w_dlGPUpt") and not origin.w_dlGPUpt.isHidden():
            pluginInfos["GPUsPerTask"] = origin.sp_dlGPUpt.value()

        if hasattr(origin, "w_dlGPUdevices") and not origin.w_dlGPUdevices.isHidden():
            pluginInfos["GPUsSelectDevices"] = origin.le_dlGPUdevices.text()

        dlParams = {
            "jobInfos": jobInfos,
            "pluginInfos": pluginInfos,
            "jobInfoFile": "",
            "pluginInfoFile": "",
        }
        self.core.appPlugin.sm_render_getDeadlineParams(origin, dlParams, homeDir)

        if len(dependencies) > 0:
            dependencyFile = os.path.join(homeDir, "temp", "dependencies.txt")
            fileHandle = open(dependencyFile, "w")

            for i in dependencies:
                fileHandle.write(str(i[0]) + "\n")
                fileHandle.write(str(i[1]) + "\n")

            fileHandle.close()

        arguments = []
        arguments.append(dlParams["jobInfoFile"])
        arguments.append(dlParams["pluginInfoFile"])
        for i in self.core.appPlugin.getCurrentSceneFiles(origin):
            arguments.append(i)

        if "dependencyFile" in locals():
            arguments.append(dependencyFile)

        result = self.deadlineSubmitJob(jobInfos, pluginInfos, arguments)
        if renderNSIs:
            code = origin.curRenderer.getNsiRenderScript()
            nsiDep = [[0, jobOutputFile]]
            dlpath = os.getenv("DELIGHT")
            environment = [["DELIGHT", dlpath]]
            args = [jobOutputFile, jobOutputFileOrig]

            result = self.submitPythonJob(
                code=code,
                jobName=jobName + "_render",
                jobOutput=jobOutputFileOrig,
                jobPrio=jobPrio,
                jobGroup=jobGroup,
                jobTimeOut=jobTimeOut,
                jobMachineLimit=jobMachineLimit,
                jobFramesPerTask=jobFramesPerTask,
                jobConcurrentTasks=jobConcurrentTasks,
                jobBatchName=jobBatchName,
                frames=frameStr,
                suspended=suspended,
                dependencies=nsiDep,
                environment=environment,
                args=args,
            )

            if self.core.getConfig("render", "3DelightCleanupJob", dft=True, config="project"):
                cleanupScript = origin.curRenderer.getCleanupScript()
            else:
                cleanupScript = None

            if cleanupScript:
                arguments = [args[0]]
                depId = self.getJobIdFromSubmitResult(result)
                cleanupDep = [depId]
                self.submitCleanupScript(
                    jobName=jobName,
                    jobGroup=jobGroup,
                    jobPrio=jobPrio,
                    jobTimeOut=jobTimeOut,
                    jobMachineLimit=jobMachineLimit,
                    jobBatchName=jobBatchName,
                    suspended=suspended,
                    jobDependencies=cleanupDep,
                    environment=environment,
                    cleanupScript=cleanupScript,
                    arguments=arguments,
                )

        elif renderRS:
            rsDep = [[0, jobOutputFile]]
            args = [jobOutputFile, jobOutputFileOrig]
            gpusPerTask = origin.sp_dlGPUpt.value()
            gpuDevices = origin.le_dlGPUdevices.text()
            if self.core.getConfig("render", "RedshiftCleanupJob", dft=True, config="project"):
                cleanupScript = origin.curRenderer.getCleanupScript()
            else:
                cleanupScript = None

            self.submitRedshiftJob(
                jobName=jobName + "_render",
                jobOutput=jobOutputFileOrig,
                jobPrio=jobPrio,
                jobGroup=jobGroup,
                jobTimeOut=jobTimeOut,
                jobMachineLimit=jobMachineLimit,
                jobFramesPerTask=jobFramesPerTask,
                jobConcurrentTasks=jobConcurrentTasks,
                jobBatchName=jobBatchName,
                frames=frameStr,
                suspended=suspended,
                dependencies=rsDep,
                archivefile=jobOutputFile,
                gpusPerTask=gpusPerTask,
                gpuDevices=gpuDevices,
                args=args,
                cleanupScript=cleanupScript,
            )

        return result

    @err_catcher(name=__name__)
    def submitPythonJob(
            self,
            code="",
            version="3.7",
            jobName=None,
            jobOutput=None,
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
    ):
        homeDir = (
            self.deadlineCommand(["-GetCurrentUserHomeDirectory"], background=False)
        ).decode("utf-8")

        if homeDir is False:
            return "Execute Canceled: Deadline is not installed"

        homeDir = homeDir.replace("\r", "").replace("\n", "")

        if not jobName:
            jobName = os.path.splitext(self.core.getCurrentFileName(path=False))[0].strip("_")

        scriptFile = os.path.join(homeDir, "temp", "%s_%s.py" % (jobName, int(time.time())))
        with open(scriptFile, "w") as f:
            f.write(code)

        environment = environment or []
        environment.insert(0, ["prism_project", self.core.prismIni.replace("\\", "/")])

        # Create submission info file

        jobInfos = {}

        jobInfos["Name"] = jobName
        jobInfos["Group"] = jobGroup
        jobInfos["Priority"] = jobPrio
        jobInfos["TaskTimeoutMinutes"] = jobTimeOut
        jobInfos["MachineLimit"] = jobMachineLimit
        jobInfos["Frames"] = frames
        jobInfos["ChunkSize"] = jobFramesPerTask
        for idx, env in enumerate(environment):
            jobInfos["EnvironmentKeyValue%s" % idx] = "%s=%s" % (env[0], env[1])
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
            jobInfos["IsFrameDependent"] = "true"
            jobInfos["ScriptDependencies"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "DeadlineDependency.py"))

        if jobDependencies:
            jobInfos["JobDependencies"] = ",".join(jobDependencies)

        # Create plugin info file

        pluginInfos = {}
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

        if dependencies:
            dependencyFile = os.path.join(homeDir, "temp", "dependencies.txt")
            fileHandle = open(dependencyFile, "w")

            for i in dependencies:
                fileHandle.write(str(i[0]) + "\n")
                fileHandle.write(str(i[1]) + "\n")

            fileHandle.close()

        arguments = []
        arguments.append(dlParams["jobInfoFile"])
        arguments.append(dlParams["pluginInfoFile"])
        arguments.append(scriptFile)
        for i in self.core.appPlugin.getCurrentSceneFiles(self):
            arguments.append(i)

        if "dependencyFile" in locals():
            arguments.append(dependencyFile)

        result = self.deadlineSubmitJob(jobInfos, pluginInfos, arguments)
        return result

    @err_catcher(name=__name__)
    def submitRedshiftJob(
            self,
            jobName=None,
            jobOutput=None,
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
            cleanupScript=None
    ):
        homeDir = (
            self.deadlineCommand(["-GetCurrentUserHomeDirectory"], background=False)
        ).decode("utf-8")

        if homeDir is False:
            return "Execute Canceled: Deadline is not installed"

        homeDir = homeDir.replace("\r", "").replace("\n", "")

        if not jobName:
            jobName = os.path.splitext(self.core.getCurrentFileName(path=False))[0].strip("_")

        environment = environment or []
        environment.insert(0, ["prism_project", self.core.prismIni.replace("\\", "/")])

        # Create submission info file

        jobInfos = {}

        jobInfos["Name"] = jobName
        jobInfos["Group"] = jobGroup
        jobInfos["Priority"] = jobPrio
        jobInfos["TaskTimeoutMinutes"] = jobTimeOut
        jobInfos["MachineLimit"] = jobMachineLimit
        jobInfos["Frames"] = frames
        jobInfos["ChunkSize"] = jobFramesPerTask
        for idx, env in enumerate(environment):
            jobInfos["EnvironmentKeyValue%s" % idx] = "%s=%s" % (env[0], env[1])
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
            jobInfos["IsFrameDependent"] = "true"
            jobInfos["ScriptDependencies"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "DeadlineDependency.py"))

        # Create plugin info file

        pluginInfos = {}

        startFrame = frames.split("-")[0].split(",")[0]
        paddedStartFrame = str(startFrame).zfill(self.core.framePadding)
        pluginInfos["SceneFile"] = archivefile.replace("#"*self.core.framePadding, paddedStartFrame)

        pluginInfos["GPUsPerTask"] = gpusPerTask
        pluginInfos["GPUsSelectDevices"] = gpuDevices

        dlParams = {
            "jobInfos": jobInfos,
            "pluginInfos": pluginInfos,
            "jobInfoFile": os.path.join(homeDir, "temp", "redshift_plugin_info.job"),
            "pluginInfoFile": os.path.join(homeDir, "temp", "redshift_job_info.job"),
        }

        if dependencies:
            dependencyFile = os.path.join(homeDir, "temp", "dependencies.txt")
            fileHandle = open(dependencyFile, "w")

            for i in dependencies:
                fileHandle.write(str(i[0]) + "\n")
                fileHandle.write(str(i[1]) + "\n")

            fileHandle.close()

        arguments = []
        arguments.append(dlParams["jobInfoFile"])
        arguments.append(dlParams["pluginInfoFile"])

        for i in self.core.appPlugin.getCurrentSceneFiles(self):
            arguments.append(i)

        if "dependencyFile" in locals():
            arguments.append(dependencyFile)

        result = self.deadlineSubmitJob(jobInfos, pluginInfos, arguments)

        if cleanupScript:
            jobName = jobName.rsplit("_", 1)[0]
            arguments = [args[0]]
            depId = self.getJobIdFromSubmitResult(result)
            cleanupDep = [depId]
            self.submitCleanupScript(
                jobName=jobName,
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
    ):
        self.submitPythonJob(
            code=cleanupScript,
            jobName=jobName + "_cleanup",
            jobPrio=jobPrio,
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
        )

    @err_catcher(name=__name__)
    def deadlineSubmitJob(self, jobInfos, pluginInfos, arguments):
        self.core.callback(
            name="preSubmit_Deadline",
            types=["custom"],
            args=[self, jobInfos, pluginInfos, arguments],
        )

        with open(arguments[0], "w") as fileHandle:
            for i in jobInfos:
                fileHandle.write("%s=%s\n" % (i, jobInfos[i]))

        with open(arguments[1], "w") as fileHandle:
            for i in pluginInfos:
                fileHandle.write("%s=%s\n" % (i, pluginInfos[i]))

        jobResult = self.deadlineCommand(arguments, background=False).decode("utf-8")

        self.core.callback(
            name="postSubmit_Deadline", types=["custom"], args=[self, jobResult]
        )

        return jobResult
