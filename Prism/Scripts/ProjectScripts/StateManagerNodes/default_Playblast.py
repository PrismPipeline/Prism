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
import time
import traceback
import platform
import logging
import glob

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class PlayblastClass(object):
    className = "Playblast"
    listType = "Export"
    stateCategories = {"Playblast": [{"label": className, "stateType": className}]}

    @err_catcher(name=__name__)
    def setup(self, state, core, stateManager, stateData=None):
        self.state = state
        self.core = core
        self.stateManager = stateManager
        self.canSetVersion = True

        self.curCam = None
        self.e_name.setText(state.text(0) + " ({identifier})")

        self.l_name.setVisible(False)
        self.e_name.setVisible(False)
        self.gb_submit.setChecked(False)
        self.gb_submit.setVisible(False)

        self.camlist = []

        self.rangeTypes = ["Scene", "Shot", "Single Frame", "Custom"]
        self.cb_rangeType.addItems(self.rangeTypes)
        for idx, rtype in enumerate(self.rangeTypes):
            self.cb_rangeType.setItemData(
                idx, self.stateManager.getFrameRangeTypeToolTip(rtype), Qt.ToolTipRole
            )

        self.resolutionPresets = self.core.projects.getResolutionPresets()
        if "Get from rendersettings" not in self.resolutionPresets:
            self.resolutionPresets.append("Get from rendersettings")

        masterItems = ["Set as master", "Add to master", "Don't update master"]
        self.cb_master.addItems(masterItems)
        self.product_paths = self.core.paths.getRenderProductBasePaths()
        self.cb_location.addItems(list(self.product_paths.keys()))
        if len(self.product_paths) < 2:
            self.w_location.setVisible(False)

        self.outputformats = [".jpg", ".mp4"]
        self.cb_formats.addItems(self.outputformats)
        getattr(self.core.appPlugin, "sm_playblast_startup", lambda x: None)(self)
        self.connectEvents()

        self.cb_manager.addItems([p.pluginName for p in self.core.plugins.getRenderfarmPlugins()])
        self.core.callback("onStateStartup", self)
        if self.cb_manager.count() == 0:
            self.gb_submit.setVisible(False)

        self.f_rjWidgetsPerTask.setVisible(False)
        self.managerChanged(True)

        self.oldPalette = self.b_changeTask.palette()
        self.warnPalette = QPalette()
        self.warnPalette.setColor(QPalette.Button, QColor(200, 0, 0))
        self.warnPalette.setColor(QPalette.ButtonText, QColor(255, 255, 255))

        self.setTaskWarn(True)
        self.updateUi()
        if stateData is not None:
            self.loadData(stateData)
        else:
            context = self.getCurrentContext()
            if context.get("type") == "asset":
                self.setRangeType("Single Frame")
            elif context.get("type") == "shot":
                self.setRangeType("Shot")
            elif self.stateManager.standalone:
                self.setRangeType("Custom")
            else:
                self.setRangeType("Scene")

            if context.get("task"):
                self.setTaskname(context.get("task"))

    @err_catcher(name=__name__)
    def loadData(self, data):
        if "stateName" in data:
            self.e_name.setText(data["stateName"])
        elif "statename" in data:
            self.e_name.setText(data["statename"] + " ({identifier})")
        if "taskname" in data:
            self.setTaskname(data["taskname"])
            self.nameChanged(self.e_name.text())
        if "rangeType" in data:
            idx = self.cb_rangeType.findText(data["rangeType"])
            if idx != -1:
                self.cb_rangeType.setCurrentIndex(idx)
                self.updateRange()
        if "startframe" in data:
            self.sp_rangeStart.setValue(int(data["startframe"]))
        if "endframe" in data:
            self.sp_rangeEnd.setValue(int(data["endframe"]))
        if "currentcam" in data:
            camName = getattr(self.core.appPlugin, "getCamName", lambda x, y: "")(
                self, data["currentcam"]
            )
            idx = self.cb_cams.findText(camName)
            if idx > 0:
                self.curCam = self.camlist[idx - 1]
                self.cb_cams.setCurrentIndex(idx)
                self.stateManager.saveStatesToScene()
        if "resoverride" in data:
            res = eval(data["resoverride"])
            self.chb_resOverride.setChecked(res[0])
            self.sp_resWidth.setValue(res[1])
            self.sp_resHeight.setValue(res[2])
        if "masterVersion" in data:
            idx = self.cb_master.findText(data["masterVersion"])
            if idx != -1:
                self.cb_master.setCurrentIndex(idx)
        if "curLocation" in data:
            idx = self.cb_location.findText(data["curLocation"])
            if idx != -1:
                self.cb_location.setCurrentIndex(idx)
        if "outputformat" in data:
            idx = self.cb_formats.findText(data["outputformat"])
            if idx > 0:
                self.cb_formats.setCurrentIndex(idx)
        if "submitrender" in data:
            self.gb_submit.setChecked(eval(data["submitrender"]))
        if "rjmanager" in data:
            idx = self.cb_manager.findText(data["rjmanager"])
            if idx != -1:
                self.cb_manager.setCurrentIndex(idx)
            self.managerChanged(True)
        if "rjprio" in data:
            self.sp_rjPrio.setValue(int(data["rjprio"]))
        if "rjframespertask" in data:
            self.sp_rjFramesPerTask.setValue(int(data["rjframespertask"]))
        if "rjtimeout" in data:
            self.sp_rjTimeout.setValue(int(data["rjtimeout"]))
        if "rjsuspended" in data:
            self.chb_rjSuspended.setChecked(eval(data["rjsuspended"]))
        if "dlconcurrent" in data:
            self.sp_dlConcurrentTasks.setValue(int(data["dlconcurrent"]))
        if "lastexportpath" in data:
            lePath = self.core.fixPath(data["lastexportpath"])
            self.l_pathLast.setText(lePath)
            self.l_pathLast.setToolTip(lePath)
        if "stateenabled" in data:
            self.state.setCheckState(
                0,
                eval(
                    data["stateenabled"]
                    .replace("PySide.QtCore.", "")
                    .replace("PySide2.QtCore.", "")
                ),
            )

        getattr(self.core.appPlugin, "sm_playblast_loadData", lambda x, y: None)(
            self, data
        )
        self.core.callback("onStateSettingsLoaded", self, data)

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.b_changeTask.clicked.connect(self.changeTask)
        self.cb_rangeType.activated.connect(self.rangeTypeChanged)
        self.sp_rangeStart.editingFinished.connect(self.startChanged)
        self.sp_rangeEnd.editingFinished.connect(self.endChanged)
        self.cb_cams.activated.connect(self.setCam)
        self.chb_resOverride.stateChanged.connect(self.resOverrideChanged)
        self.sp_resWidth.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.sp_resHeight.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.b_resPresets.clicked.connect(self.showResPresets)
        self.cb_master.activated.connect(self.stateManager.saveStatesToScene)
        self.cb_location.activated[str].connect(self.stateManager.saveStatesToScene)
        self.cb_formats.activated.connect(self.stateManager.saveStatesToScene)
        self.gb_submit.toggled.connect(self.rjToggled)
        self.cb_manager.activated.connect(self.managerChanged)
        self.sp_rjPrio.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.sp_rjFramesPerTask.editingFinished.connect(
            self.stateManager.saveStatesToScene
        )
        self.sp_rjTimeout.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.chb_rjSuspended.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.sp_dlConcurrentTasks.editingFinished.connect(
            self.stateManager.saveStatesToScene
        )
        self.b_pathLast.clicked.connect(self.showLastPathMenu)

    @err_catcher(name=__name__)
    def showLastPathMenu(self):
        path = self.l_pathLast.text()
        if path == "None":
            return

        menu = QMenu(self)

        act_open = QAction("Play", self)
        act_open.triggered.connect(lambda: self.core.media.playMediaInExternalPlayer(path))
        menu.addAction(act_open)

        act_open = QAction("Open in Media Browser", self)
        act_open.triggered.connect(lambda: self.openInMediaBrowser(path))
        menu.addAction(act_open)

        act_open = QAction("Open in explorer", self)
        act_open.triggered.connect(lambda: self.core.openFolder(path))
        menu.addAction(act_open)

        act_copy = QAction("Copy", self)
        act_copy.triggered.connect(lambda: self.core.copyToClipboard(path, file=True))
        menu.addAction(act_copy)

        menu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def openInMediaBrowser(self, path):
        self.core.projectBrowser()
        self.core.pb.showTab("Media")
        data = self.core.paths.getPlayblastProductData(path)
        self.core.pb.mediaBrowser.showRender(entity=data, identifier=data.get("identifier") + " (playblast)", version=data.get("version"))

    @err_catcher(name=__name__)
    def rangeTypeChanged(self, state):
        self.updateRange()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def startChanged(self):
        if self.sp_rangeStart.value() > self.sp_rangeEnd.value():
            self.sp_rangeEnd.setValue(self.sp_rangeStart.value())

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def endChanged(self):
        if self.sp_rangeEnd.value() < self.sp_rangeStart.value():
            self.sp_rangeStart.setValue(self.sp_rangeEnd.value())

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def setCam(self, index):
        if index == 0:
            self.curCam = None
        else:
            self.curCam = self.camlist[index - 1]

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def nameChanged(self, text):
        text = self.e_name.text()
        context = {}
        context["identifier"] = self.getTaskname() or "None"
        num = 0
        try:
            if "{#}" in text:
                while True:
                    context["#"] = num or ""
                    name = text.format(**context)
                    for state in self.stateManager.states:
                        if state.ui.listType != "Export":
                            continue

                        if state is self.state:
                            continue

                        if state.text(0) == name:
                            num += 1
                            break
                    else:
                        break
            else:
                name = text.format(**context)
        except Exception:
            name = text

        if self.state.text(0).endswith(" - disabled"):
            name += " - disabled"

        self.state.setText(0, name)

    @err_catcher(name=__name__)
    def getTaskname(self):
        taskName = self.l_taskName.text()
        return taskName

    @err_catcher(name=__name__)
    def getSortKey(self):
        return self.getTaskname()

    @err_catcher(name=__name__)
    def setTaskname(self, taskname):
        self.l_taskName.setText(taskname)
        self.setTaskWarn(not bool(taskname))
        self.updateUi()

    @err_catcher(name=__name__)
    def changeTask(self):
        from PrismUtils import PrismWidgets
        self.nameWin = PrismWidgets.CreateItem(
            startText=self.getTaskname(),
            showTasks=True,
            taskType="playblast",
            core=self.core,
        )
        self.core.parentWindow(self.nameWin)
        self.nameWin.setWindowTitle("Change Identifier")
        self.nameWin.l_item.setText("Identifier:")
        self.nameWin.buttonBox.buttons()[0].setText("Ok")
        self.nameWin.e_item.selectAll()
        result = self.nameWin.exec_()

        if result == 1:
            self.setTaskname(self.nameWin.e_item.text())
            self.nameChanged(self.e_name.text())
            self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def resOverrideChanged(self, checked):
        self.sp_resWidth.setEnabled(checked)
        self.sp_resHeight.setEnabled(checked)
        self.b_resPresets.setEnabled(checked)

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def showResPresets(self):
        pmenu = QMenu(self.stateManager)

        for preset in self.resolutionPresets:
            pAct = QAction(preset, self)
            res = self.getResolution(preset)
            if not res:
                continue

            pwidth, pheight = res

            pAct.triggered.connect(
                lambda x=None, v=pwidth: self.sp_resWidth.setValue(v)
            )
            pAct.triggered.connect(
                lambda x=None, v=pheight: self.sp_resHeight.setValue(v)
            )
            pAct.triggered.connect(lambda: self.stateManager.saveStatesToScene())
            pmenu.addAction(pAct)

        pmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def getResolution(self, resolution):
        res = None
        if resolution == "Get from rendersettings":
            if hasattr(self.core.appPlugin, "getResolution"):
                res = self.core.appPlugin.getResolution()
            else:
                res = [1920, 1080]
        elif resolution.startswith("Project ("):
            res = resolution[9:-1].split("x")
            res = [int(r) for r in res]
        else:
            try:
                pwidth = int(resolution.split("x")[0])
                pheight = int(resolution.split("x")[1])
                res = [pwidth, pheight]
            except:
                res = getattr(
                    self.core.appPlugin, "evaluateResolution", lambda x: None
                )(resolution)

        return res

    @err_catcher(name=__name__)
    def getMasterVersion(self):
        return self.cb_master.currentText()

    @err_catcher(name=__name__)
    def setMasterVersion(self, master):
        idx = self.cb_master.findText(master)
        if idx != -1:
            self.cb_master.setCurrentIndex(idx)
            self.stateManager.saveStatesToScene()
            return True

        return False

    @err_catcher(name=__name__)
    def getLocation(self):
        return self.cb_location.currentText()

    @err_catcher(name=__name__)
    def setLocation(self, location):
        idx = self.cb_location.findText(location)
        if idx != -1:
            self.cb_location.setCurrentIndex(idx)
            self.stateManager.saveStatesToScene()
            return True

        return False

    @err_catcher(name=__name__)
    def updateUi(self):
        # update Cams
        self.cb_cams.clear()
        self.cb_cams.addItem("Don't override")
        self.camlist = camNames = []

        if not self.stateManager.standalone:
            self.camlist = self.core.appPlugin.getCamNodes(self)
            camNames = [self.core.appPlugin.getCamName(self, i) for i in self.camlist]

        self.cb_cams.addItems(camNames)

        if self.curCam in self.camlist:
            self.cb_cams.setCurrentIndex(self.camlist.index(self.curCam) + 1)
        else:
            self.cb_cams.setCurrentIndex(0)
            self.curCam = None

        if not self.core.mediaProducts.getUseMaster():
            self.w_master.setVisible(False)

        self.refreshSubmitUi()
        self.updateRange()
        self.nameChanged(self.e_name.text())
        return True

    @err_catcher(name=__name__)
    def getCurrentContext(self):
        fileName = self.core.getCurrentFileName()
        context = self.core.getScenefileData(fileName)

        if "username" in context:
            del context["username"]

        if "user" in context:
            del context["user"]

        return context

    @err_catcher(name=__name__)
    def refreshSubmitUi(self):
        if not self.gb_submit.isHidden():
            if not self.gb_submit.isCheckable():
                return

            submitChecked = self.gb_submit.isChecked()
            for idx in reversed(range(self.gb_submit.layout().count())):
                self.gb_submit.layout().itemAt(idx).widget().setHidden(not submitChecked)

            if submitChecked:
                self.core.plugins.getRenderfarmPlugin(self.cb_manager.currentText()).sm_render_updateUI(self)

    @err_catcher(name=__name__)
    def updateRange(self):
        rangeType = self.cb_rangeType.currentText()
        isCustom = rangeType == "Custom"
        self.l_rangeStart.setVisible(not isCustom)
        self.l_rangeEnd.setVisible(not isCustom)
        self.sp_rangeStart.setVisible(isCustom)
        self.sp_rangeEnd.setVisible(isCustom)

        if not isCustom:
            frange = self.getFrameRange(rangeType=rangeType)
            start = str(int(frange[0])) if frange[0] is not None else "-"
            end = str(int(frange[1])) if frange[1] is not None else "-"
            self.l_rangeStart.setText(start)
            self.l_rangeEnd.setText(end)

    @err_catcher(name=__name__)
    def getFrameRange(self, rangeType):
        startFrame = None
        endFrame = None
        if rangeType == "Scene":
            if hasattr(self.core.appPlugin, "getFrameRange"):
                startFrame, endFrame = self.core.appPlugin.getFrameRange(self)
            else:
                startFrame = 1001
                endFrame = 1100
        elif rangeType == "Shot":
            context = self.getCurrentContext()
            if context.get("type") == "shot" and "sequence" in context:
                frange = self.core.entities.getShotRange(context)
                if frange:
                    startFrame, endFrame = frange
        elif rangeType == "Single Frame":
            if hasattr(self.core.appPlugin, "getCurrentFrame"):
                startFrame = self.core.appPlugin.getCurrentFrame()
            else:
                startFrame = 1001
        elif rangeType == "Custom":
            startFrame = self.sp_rangeStart.value()
            endFrame = self.sp_rangeEnd.value()

        if startFrame == "":
            startFrame = None

        if endFrame == "":
            endFrame = None

        if startFrame is not None:
            startFrame = int(startFrame)

        if endFrame is not None:
            endFrame = int(endFrame)

        return startFrame, endFrame

    @err_catcher(name=__name__)
    def getRangeType(self):
        return self.cb_rangeType.currentText()

    @err_catcher(name=__name__)
    def setRangeType(self, rangeType):
        idx = self.cb_rangeType.findText(rangeType)
        if idx != -1:
            self.cb_rangeType.setCurrentIndex(idx)
            self.updateRange()
            return True

        return False

    @err_catcher(name=__name__)
    def rjToggled(self, checked):
        self.refreshSubmitUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def managerChanged(self, text=None):
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def updateLastPath(self, path):
        self.l_pathLast.setText(path)
        self.l_pathLast.setToolTip(path)

    @err_catcher(name=__name__)
    def preExecuteState(self):
        warnings = []

        if not self.getTaskname():
            warnings.append(["No identifier is given.", "", 3])

        rangeType = self.cb_rangeType.currentText()
        startFrame, endFrame = self.getFrameRange(rangeType)

        if startFrame is None:
            warnings.append(["Framerange is invalid.", "", 3])

        warnings += self.core.appPlugin.sm_playblast_preExecute(self)

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def getOutputName(self, useVersion="next", extension=None):
        if not self.getTaskname():
            return

        task = self.getTaskname()
        extension = extension or self.cb_formats.currentText()
        context = self.getCurrentContext()
        framePadding = (
            "#"*self.core.framePadding if self.cb_rangeType.currentText() != "Single Frame" else ""
        )
        comment = self.stateManager.publishComment

        if "type" not in context:
            return

        location = self.cb_location.currentText()
        if "version" in context:
            del context["version"]

        if "comment" in context:
            del context["comment"]

        outputPathData = self.core.mediaProducts.generatePlayblastPath(
            entity=context,
            task=task,
            extension=extension,
            framePadding=framePadding,
            comment=comment,
            version=useVersion if useVersion != "next" else None,
            location=location,
            returnDetails=True,
        )

        outputPath = outputPathData["path"].replace("\\", "/")
        outputFolder = os.path.dirname(outputPath)
        hVersion = outputPathData["version"]

        return outputPath, outputFolder, hVersion

    @err_catcher(name=__name__)
    def executeState(self, parent, useVersion="next"):
        # 	if not self.core.uiAvailable:
        # 		return [self.state.text(0) + ": error - Playblasts are not supported without UI."]

        if not self.getTaskname():
            return [
                self.state.text(0)
                + ": error - No identifier is given. Skipped the activation of this state."
            ]

        fileName = self.core.getCurrentFileName()
        context = self.getCurrentContext()
        result = self.getOutputName(useVersion=useVersion, extension=".jpg")
        if not result:
            return [
                self.state.text(0)
                + ": error - Couldn't generate an outputpath for this state.\nMake sure your scenefile is saved correctly in the pipeline."
            ]
            return

        outputName, outputPath, hVersion = result

        outLength = len(outputName)
        if platform.system() == "Windows" and os.getenv("PRISM_IGNORE_PATH_LENGTH") != "1" and outLength > 255:
            return [
                self.state.text(0)
                + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, taskname or projectpath."
                % outLength
            ]

        rangeType = self.cb_rangeType.currentText()
        startFrame, endFrame = self.getFrameRange(rangeType)
        if startFrame is None:
            return [self.state.text(0) + ": error - Framerange is invalid"]

        if rangeType == "Single Frame":
            endFrame = startFrame

        jobFrames = [startFrame, endFrame]

        updateMaster = True
        exCheck = self.core.appPlugin.sm_playblast_execute(self)
        if exCheck is not None:
            return exCheck

        if self.curCam is not None and not self.core.appPlugin.isNodeValid(
            self, self.curCam
        ):
            return [
                self.state.text(0) + ": error - Camera is invalid (%s)." % self.curCam
            ]

        kwargs = {
            "state": self,
            "scenefile": fileName,
            "startframe": jobFrames[0],
            "endframe": jobFrames[1],
            "outputpath": outputName,
        }
        result = self.core.callback("prePlayblast", **kwargs)
        for res in result:
            if isinstance(res, dict) and res.get("cancel", False):
                return [
                    self.state.text(0)
                    + " - error - %s" % res.get("details", "prePlayblast hook returned False")
                ]

            if res and "outputName" in res:
                outputName = res["outputName"]

        outputPath = os.path.dirname(outputName)
        if not os.path.exists(outputPath):
            os.makedirs(outputPath)

        details = context.copy()
        del details["filename"]
        del details["extension"]
        details["version"] = hVersion
        details["sourceScene"] = fileName
        details["identifier"] = self.getTaskname()
        details["comment"] = self.stateManager.publishComment

        self.core.saveVersionInfo(filepath=outputPath, details=details)

        self.updateLastPath(outputName)
        self.stateManager.saveStatesToScene()

        self.core.saveScene(versionUp=False, prismReq=False)

        try:
            if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
                handleMaster = "media" if self.isUsingMasterVersion() else False
                plugin = self.core.plugins.getRenderfarmPlugin(self.cb_manager.currentText())
                submitResult = plugin.sm_render_submitJob(self, outputName, parent, details=details, handleMaster=handleMaster)
                updateMaster = False
            else:
                self.core.appPlugin.sm_playblast_createPlayblast(
                    self, jobFrames=jobFrames, outputName=outputName
                )

            getattr(self.core.appPlugin, "sm_playblast_postExecute", lambda x: None)(
                self
            )

            if self.cb_formats.currentText() == ".mp4":
                mediaBaseName = os.path.splitext(outputName)[0][:-3]
                files = glob.glob(mediaBaseName + "*" + os.path.splitext(outputName)[1])
                if not files or self.core.media.checkOddResolution(files[0]):
                    mediaBaseName = os.path.splitext(outputName)[0].rstrip("#").rstrip(".")
                    videoOutput = mediaBaseName + ".mp4"
                    inputpath = (
                        os.path.splitext(outputName)[0].rstrip("#").rstrip(".")
                        + ".%04d".replace("4", str(self.core.framePadding))
                        + os.path.splitext(outputName)[1]
                    )
                    settings = {"-framerate": self.core.getFPS()}
                    result = self.core.media.convertMedia(
                        inputpath, jobFrames[0], videoOutput, settings=settings
                    )

                    self.deleteTmpJpgs(mediaBaseName)
                    if not os.path.exists(videoOutput):
                        logger.warning("fmmpeg output: %s" % str(result))
                        return [
                            self.state.text(0)
                            + " - error occurred during conversion of jpg files to mp4. Check the console for more information."
                        ]

                    outputName = videoOutput
                    self.updateLastPath(videoOutput)
                else:
                    self.deleteTmpJpgs(mediaBaseName)
                    return [
                        self.state.text(0)
                        + " - error - Media with odd resolution can't be converted to mp4."
                    ]

            if updateMaster:
                self.handleMasterVersion(outputName)

            kwargs = {
                "state": self,
                "scenefile": fileName,
                "startframe": jobFrames[0],
                "endframe": jobFrames[1],
                "outputpath": outputName,
            }
            result = self.core.callback("postPlayblast", **kwargs)

            validateOutput = True
            for res in result:
                if res and "outputName" in res:
                    outputPath = os.path.dirname(res["outputName"])

                if res and "validateOutput" in res:
                    validateOutput = res["validateOutput"]

            if not self.gb_submit.isHidden() and self.gb_submit.isChecked() and "Result=Success" in submitResult:
                return [self.state.text(0) + " - success"]
            elif not validateOutput or len(os.listdir(outputPath)) > 1:
                return [self.state.text(0) + " - success"]
            else:
                return [self.state.text(0) + " - unknown error (files do not exist)"]
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            erStr = "%s ERROR - sm_default_playblast %s:\n%s" % (
                time.strftime("%d/%m/%y %X"),
                self.core.version,
                traceback.format_exc(),
            )
            self.core.writeErrorLog(erStr)
            return [
                self.state.text(0)
                + " - unknown error (view console for more information)"
            ]

    @err_catcher(name=__name__)
    def deleteTmpJpgs(self, mediaBaseName):
        delFiles = []
        for i in os.listdir(os.path.dirname(mediaBaseName)):
            if i.startswith(os.path.basename(mediaBaseName)) and i.endswith(
                ".jpg"
            ):
                delFiles.append(os.path.join(os.path.dirname(mediaBaseName), i))

        for i in delFiles:
            try:
                os.remove(i)
            except:
                pass

    @err_catcher(name=__name__)
    def isUsingMasterVersion(self):
        useMaster = self.core.mediaProducts.getUseMaster()
        if not useMaster:
            return False

        masterAction = self.cb_master.currentText()
        if masterAction == "Don't update master":
            return False

        return True

    @err_catcher(name=__name__)
    def handleMasterVersion(self, outputName):
        if not self.isUsingMasterVersion():
            return

        masterAction = self.cb_master.currentText()
        if masterAction == "Set as master":
            self.core.mediaProducts.updateMasterVersion(outputName, mediaType="playblasts")
        elif masterAction == "Add to master":
            self.core.mediaProducts.addToMasterVersion(outputName, mediaType="playblasts")

    @err_catcher(name=__name__)
    def setTaskWarn(self, warn):
        useSS = getattr(self.core.appPlugin, "colorButtonWithStyleSheet", False)
        if warn:
            if useSS:
                self.b_changeTask.setStyleSheet(
                    "QPushButton { background-color: rgb(200,0,0); }"
                )
            else:
                self.b_changeTask.setPalette(self.warnPalette)
        else:
            if useSS:
                self.b_changeTask.setStyleSheet("")
            else:
                self.b_changeTask.setPalette(self.oldPalette)

    @err_catcher(name=__name__)
    def getStateProps(self):
        stateProps = {}
        stateProps.update(
            getattr(self.core.appPlugin, "sm_playblast_getStateProps", lambda x: {})(
                self
            )
        )
        stateProps.update(
            {
                "stateName": self.e_name.text(),
                "taskname": self.getTaskname(),
                "rangeType": str(self.cb_rangeType.currentText()),
                "startframe": self.sp_rangeStart.value(),
                "endframe": self.sp_rangeEnd.value(),
                "currentcam": str(self.curCam),
                "resoverride": str(
                    [
                        self.chb_resOverride.isChecked(),
                        self.sp_resWidth.value(),
                        self.sp_resHeight.value(),
                    ]
                ),
                "masterVersion": self.cb_master.currentText(),
                "curLocation": self.cb_location.currentText(),
                "submitrender": str(self.gb_submit.isChecked()),
                "rjmanager": str(self.cb_manager.currentText()),
                "rjprio": self.sp_rjPrio.value(),
                "rjframespertask": self.sp_rjFramesPerTask.value(),
                "rjtimeout": self.sp_rjTimeout.value(),
                "rjsuspended": str(self.chb_rjSuspended.isChecked()),
                "dlconcurrent": self.sp_dlConcurrentTasks.value(),
                "lastexportpath": self.l_pathLast.text().replace("\\", "/"),
                "stateenabled": str(self.state.checkState(0)),
                "outputformat": str(self.cb_formats.currentText()),
            }
        )
        self.core.callback("onStateGetSettings", self, stateProps)
        return stateProps
