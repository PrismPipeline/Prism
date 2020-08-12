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

try:
    import hou
except:
    pass

try:
    import Pandora
except:
    pass

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1

from PrismUtils.Decorators import err_catcher as err_catcher


class Prism_Pandora_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        uiPath = os.path.abspath(
            os.path.join(__file__, os.pardir, os.pardir, "UserInterfaces")
        )
        sys.path.append(uiPath)

        try:
            if self.core.appPlugin.pluginName == "3dsMax":
                import PandoraCore

                self.Pandora = PandoraCore.PandoraCore(app="3dsMax")
            if self.core.appPlugin.pluginName == "Blender":
                import PandoraCore

                self.Pandora = PandoraCore.PandoraCore(app="Blender")
            if self.core.appPlugin.pluginName == "Houdini":
                self.Pandora = Pandora.core
            if self.core.appPlugin.pluginName == "Maya":
                import PandoraCore

                self.Pandora = PandoraCore.PandoraCore(app="Maya")
        except:
            pass

    @err_catcher(name=__name__)
    def isActive(self):
        return hasattr(self, "Pandora")

    @err_catcher(name=__name__)
    def sm_dep_startup(self, origin):
        origin.lw_osStates.itemClicked.connect(
            lambda x: self.sm_updatePandoraDeps(origin, x)
        )
        origin.b_goTo.clicked.connect(lambda: self.sm_pandoraGoToNode(origin))

    @err_catcher(name=__name__)
    def sm_updatePandoraDeps(self, origin, item):
        if item.checkState() == Qt.Checked:
            if item.toolTip().startswith("Node:"):
                origin.dependencies["Pandora"] = [[item.text(), "Node"]]
            elif item.toolTip().startswith("Job:"):
                origin.dependencies["Pandora"] = [[item.text(), "Job"]]
            origin.updateUi()
            origin.stateManager.saveStatesToScene()
        elif item.checkState() == Qt.Unchecked:
            if (
                len(origin.dependencies["Pandora"]) > 0
                and item.text() == origin.dependencies["Pandora"][0][0]
            ):
                origin.dependencies["Pandora"] = []
                origin.updateUi()
                origin.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def sm_pandoraGoToNode(self, origin):
        try:
            origin.node.name()
        except:
            return False

        origin.node.setCurrent(True, clear_all_selected=True)

        paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        if paneTab is not None:
            paneTab.frameSelection()

    @err_catcher(name=__name__)
    def sm_dep_updateUI(self, origin):
        origin.gb_osDependency.setVisible(True)
        origin.gb_dlDependency.setVisible(False)
        try:
            origin.node.name()
            origin.l_status.setText(origin.node.name())
            origin.l_status.setStyleSheet("QLabel { background-color : rgb(0,150,0); }")
        except:
            origin.l_status.setText("Not connected")
            origin.l_status.setStyleSheet("QLabel { background-color : rgb(150,0,0); }")

        origin.lw_osStates.clear()
        newDepStates = []

        curNum = -1
        for idx, i in enumerate(origin.stateManager.states):
            if i.ui == origin:
                curNum = idx

            if curNum != -1:
                continue

            if (
                i.ui.className in ["Export", "ImageRender"]
                and i.ui.node is not None
                and origin.isNodeValid(i.ui.node)
            ):
                item = QListWidgetItem(i.text(0))
                item.setToolTip("Node: " + i.text(0))

                if (
                    len(origin.dependencies["Pandora"]) > 0
                    and str(i.text(0)) == origin.dependencies["Pandora"][0][0]
                ):
                    cState = Qt.Checked
                    newDepStates.append([str(i.text(0)), "Node"])
                else:
                    cState = Qt.Unchecked

                item.setCheckState(cState)
                if psVersion == 2:
                    item.setFlags(item.flags() & ~Qt.ItemIsAutoTristate)
                origin.lw_osStates.addItem(item)

        osf = self.Pandora.getSubmissionPath()

        osFolder = ""
        if osf is not None:
            osFolder = osf

        if osFolder is not None and os.path.exists(osFolder):
            jobDir = os.path.join(
                os.path.dirname(os.path.dirname(osFolder)), "Logs", "Jobs"
            )
            if os.path.exists(jobDir):
                self.pandoraJobs = []
                for x in sorted(os.listdir(jobDir)):
                    jobName = os.path.splitext(x)[0]

                    jcode = self.Pandora.getConfig(
                        cat="information",
                        param="jobcode",
                        configPath=os.path.join(jobDir, x),
                    )

                    if jcode is not None:
                        jobCode = jcode
                    else:
                        continue

                    self.pandoraJobs.append([jobName, jobCode])

                for x in self.pandoraJobs:
                    jobName = x[0]

                    item = QListWidgetItem(jobName)
                    item.setToolTip("Job: %s" % (jobName))

                    if (
                        len(origin.dependencies["Pandora"]) > 0
                        and jobName == origin.dependencies["Pandora"][0][0]
                    ):
                        cState = Qt.Checked
                        newDepStates.append([jobName, "Job"])
                    else:
                        cState = Qt.Unchecked

                    item.setCheckState(cState)
                    if psVersion == 2:
                        item.setFlags(item.flags() & ~Qt.ItemIsAutoTristate)
                    origin.lw_osStates.addItem(item)

        origin.dependencies["Pandora"] = newDepStates

    @err_catcher(name=__name__)
    def sm_dep_preExecute(self, origin):
        warnings = []

        if origin.node is None or not origin.isNodeValid(origin.node):
            warnings.append(["Node is invalid.", "", 3])

        return warnings

    @err_catcher(name=__name__)
    def sm_dep_execute(self, origin, parent):
        if (
            len(origin.dependencies["Pandora"]) > 0
            and origin.node is not None
            and origin.isNodeValid(origin.node)
        ):
            if (
                origin.dependencies["Pandora"][0][1] == "Node"
                and origin.dependencies["Pandora"][0][0] in parent.osSubmittedJobs
            ):
                parent.osDependencies.append(
                    [
                        parent.osSubmittedJobs[origin.dependencies["Pandora"][0][0]],
                        origin.node.path(),
                    ]
                )
            elif origin.dependencies["Pandora"][0][1] == "Job":
                jobCodes = [
                    x[1]
                    for x in self.pandoraJobs
                    if origin.dependencies["Pandora"][0][0] == x[0]
                ]
                if len(jobCodes) > 0:
                    parent.osDependencies.append([jobCodes[0], origin.node.path()])

    @err_catcher(name=__name__)
    def sm_houExport_startup(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_houExport_activated(self, origin):
        origin.f_osDependencies.setVisible(True)
        origin.f_osUpload.setVisible(True)
        origin.f_osPAssets.setVisible(True)
        origin.gb_osSlaves.setVisible(True)
        origin.f_dlGroup.setVisible(False)

    @err_catcher(name=__name__)
    def sm_houExport_preExecute(self, origin):
        warnings = []

        submPath = self.Pandora.getSubmissionPath()

        if submPath in [None, ""]:
            warnings.append(["No Pandora submission folder is configured.", "", 3])

        extFiles, extFilesSource = self.core.appPlugin.sm_getExternalFiles(origin)

        if origin.chb_osDependencies.isChecked():
            lockedAssets = []
            for idx, i in enumerate(extFiles):
                i = self.core.fixPath(i)

                if (
                    not os.path.exists(i) and not i.startswith("op:")
                ) or i == self.core.getCurrentFileName():
                    continue

                if not extFilesSource[idx].node().isEditable():
                    lockedAssets.append(i)

            if len(lockedAssets) > 0:
                depTitle = "The current scene contains locked dependencies.\nWhen submitting Pandora jobs, this dependencies cannot be relinked and will not be found by the renderslave:\n\n"
                depwarn = ""
                for i in lockedAssets:
                    parmStr = (
                        "In parameter: %s"
                        % extFilesSource[extFiles.index(i.replace("\\", "/"))].path()
                    )
                    depwarn += "\t%s\n\t%s\n\n" % (parmStr, i)

                warnings.append([depTitle, depwarn, 2])

        return warnings

    @err_catcher(name=__name__)
    def startSubmission(self, origin, jobOutputFile, parent):
        fileName = self.core.getCurrentFileName()
        jobName = (
            os.path.splitext(os.path.basename(fileName))[0]
            + "---%s" % origin.l_taskName.text()
        )

        rangeType = origin.cb_rangeType.currentText()
        frames = origin.getFrameRange(rangeType)
        if rangeType == "Expression":
            return "Submission canceled: Expression frameranges are not supported by Pandora."

        startFrame, endFrame = frames
        if rangeType == "Single Frame":
            endFrame = startFrame

        jobData = {}
        jobData["projectName"] = self.core.projectName
        jobData["jobName"] = jobName
        jobData["startFrame"] = startFrame
        jobData["endFrame"] = endFrame
        jobData["priority"] = origin.sp_rjPrio.value()
        jobData["framesPerTask"] = origin.sp_rjFramesPerTask.value()
        jobData["suspended"] = origin.chb_rjSuspended.isChecked()
        jobData["submitDependendFiles"] = origin.chb_osDependencies.isChecked()
        jobData["uploadOutput"] = origin.chb_osUpload.isChecked()
        jobData["timeout"] = origin.sp_rjTimeout.value()
        jobData["outputFolder"] = os.path.dirname(os.path.dirname(jobOutputFile))
        jobData["outputPath"] = jobOutputFile
        jobData["useProjectAssets"] = origin.chb_osPAssets.isChecked()
        jobData["listSlaves"] = origin.e_osSlaves.text()
        jobData["userName"] = self.core.getConfig("globals", "username")

        if len(parent.osDependencies) > 0:
            jobData["jobDependecies"] = parent.osDependencies

        if hasattr(origin, "chb_resOverride"):
            jobData["overrideResolution"] = origin.chb_resOverride.isChecked()
            jobData["resolutionWidth"] = origin.sp_resWidth.value()
            jobData["resolutionHeight"] = origin.sp_resHeight.value()

        if hasattr(origin, "node"):
            jobData["renderNode"] = origin.node.path()

        if (
            hasattr(origin, "curCam")
            and hasattr(self.core.appPlugin, "getCamName")
            and origin.curCam != "Current View"
        ):
            jobData["renderCam"] = self.core.appPlugin.getCamName(origin, origin.curCam)

        result = self.Pandora.submitJob(jobData)

        return result

    @err_catcher(name=__name__)
    def sm_houRender_updateUI(self, origin):
        origin.w_dlGPUpt.setVisible(False)
        origin.w_dlGPUdevices.setVisible(False)

    @err_catcher(name=__name__)
    def sm_houRender_managerChanged(self, origin):
        origin.f_osDependencies.setVisible(True)

        showUpload = False
        lmode = self.Pandora.getConfig("globals", "localMode")
        if lmode != True:
            showUpload = True

        origin.f_osUpload.setVisible(showUpload)

        origin.f_osPAssets.setVisible(True)
        origin.gb_osSlaves.setVisible(True)
        origin.f_dlGroup.setVisible(False)

        origin.w_dlConcurrentTasks.setVisible(False)

        origin.w_dlGPUpt.setVisible(False)
        origin.w_dlGPUdevices.setVisible(False)

    @err_catcher(name=__name__)
    def sm_houRender_preExecute(self, origin):
        warnings = []

        submPath = self.Pandora.getSubmissionPath()

        if submPath in [None, ""]:
            warnings.append(["No Pandora submission folder is configured.", "", 3])

        rangeType = origin.cb_rangeType.currentText()
        if rangeType == "Expression":
            warnings.append(["Expression frameranges are not supported by Pandora.", "", 3])

        extFiles, extFilesSource = self.core.appPlugin.sm_getExternalFiles(origin)

        if origin.chb_osDependencies.isChecked():
            lockedAssets = []
            for idx, i in enumerate(extFiles):
                i = self.core.fixPath(i)

                if (
                    not os.path.exists(i) and not i.startswith("op:")
                ) or i == self.core.getCurrentFileName():
                    continue

                if not extFilesSource[idx].node().isEditable():
                    lockedAssets.append(i)

            if len(lockedAssets) > 0:
                depTitle = "The current scene contains locked dependencies.\nWhen submitting Pandora jobs, this dependencies cannot be relinked and will not be found by the renderslave:\n\n"
                depwarn = ""
                for i in lockedAssets:
                    parmStr = (
                        "In parameter: %s"
                        % extFilesSource[extFiles.index(i.replace("\\", "/"))].path()
                    )
                    depwarn += "\t%s\n\t%s\n\n" % (parmStr, i)

                warnings.append([depTitle, depwarn, 2])

        return warnings

    @err_catcher(name=__name__)
    def sm_render_updateUI(self, origin):
        origin.w_dlGPUpt.setVisible(False)
        origin.w_dlGPUdevices.setVisible(False)

    @err_catcher(name=__name__)
    def sm_render_managerChanged(self, origin):
        origin.f_osDependencies.setVisible(True)
        origin.gb_osSlaves.setVisible(True)

        showUpload = False
        lmode = self.Pandora.getConfig("globals", "localMode")
        if lmode != True:
            showUpload = True

        origin.f_osUpload.setVisible(showUpload)

        origin.f_dlGroup.setVisible(False)
        origin.w_dlConcurrentTasks.setVisible(False)

        origin.w_dlGPUpt.setVisible(False)
        origin.w_dlGPUdevices.setVisible(False)

        getattr(self.core.appPlugin, "sm_render_managerChanged", lambda x, y: None)(
            origin, True
        )

    @err_catcher(name=__name__)
    def sm_render_preExecute(self, origin):
        warnings = []

        submPath = self.Pandora.getSubmissionPath()

        if submPath in [None, ""]:
            warnings.append(["No Pandora submission folder is configured.", "", 3])

        rangeType = origin.cb_rangeType.currentText()
        if rangeType == "Expression":
            warnings.append(["Expression frameranges are not supported by Pandora.", "", 3])

        return warnings

    @err_catcher(name=__name__)
    def sm_render_submitJob(self, origin, jobOutputFile, parent):
        result = self.startSubmission(origin, jobOutputFile, parent)
        if self.core.appPlugin.pluginName == "Blender":
            self.core.stateManager()

        if isinstance(result, list) and result[0] == "Success":
            if self.core.appPlugin.pluginName == "Houdini":
                parent.osSubmittedJobs[origin.state.text(0)] = result[1]

            return "Result=Success"
        else:
            return result.replace("Submission canceled:", "Execute Canceled:")
