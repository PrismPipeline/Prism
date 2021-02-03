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
import time
import traceback
import platform
import logging

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class PlayblastClass(object):
    className = "Playblast"
    listType = "Export"

    @err_catcher(name=__name__)
    def setup(self, state, core, stateManager, stateData=None):
        self.state = state
        self.core = core
        self.stateManager = stateManager

        self.curCam = None
        self.e_name.setText(state.text(0))

        self.l_name.setVisible(False)
        self.e_name.setVisible(False)

        self.camlist = []

        self.rangeTypes = ["State Manager", "Scene", "Shot", "Single Frame", "Custom"]
        self.cb_rangeType.addItems(self.rangeTypes)
        for idx, rtype in enumerate(self.rangeTypes):
            self.cb_rangeType.setItemData(idx, self.stateManager.getFrameRangeTypeToolTip(rtype), Qt.ToolTipRole)

        dftResPresets = [
            "3840x2160",
            "1920x1080",
            "1280x720",
            "960x540",
            "640x360",
            "Get from rendersettings",
        ]

        self.resolutionPresets = self.core.getConfig("globals", "resolutionPresets", configPath=self.core.prismIni, dft=dftResPresets)

        if "Get from rendersettings" not in self.resolutionPresets:
            self.resolutionPresets.append("Get from rendersettings")

        self.outputformats = [".jpg", ".mp4"]
        self.cb_formats.addItems(self.outputformats)
        getattr(self.core.appPlugin, "sm_playblast_startup", lambda x: None)(self)
        self.connectEvents()

        self.oldPalette = self.b_changeTask.palette()
        self.warnPalette = QPalette()
        self.warnPalette.setColor(QPalette.Button, QColor(200, 0, 0))
        self.warnPalette.setColor(QPalette.ButtonText, QColor(255, 255, 255))

        self.setTaskWarn(True)

        self.f_localOutput.setVisible(self.core.useLocalFiles)

        self.updateUi()
        if stateData is not None:
            self.loadData(stateData)
        else:
            fileName = self.core.getCurrentFileName()
            fnameData = self.core.getScenefileData(fileName)
            if fnameData.get("category"):
                self.l_taskName.setText(fnameData.get("category"))

    @err_catcher(name=__name__)
    def loadData(self, data):
        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "taskname" in data:
            self.l_taskName.setText(data["taskname"])
            if data["taskname"] != "":
                self.setTaskWarn(False)
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
        if "localoutput" in data:
            self.chb_localOutput.setChecked(eval(data["localoutput"]))
        if "outputformat" in data:
            idx = self.cb_formats.findText(data["outputformat"])
            if idx > 0:
                self.cb_formats.setCurrentIndex(idx)
        if "lastexportpath" in data:
            lePath = self.core.fixPath(data["lastexportpath"])
            self.l_pathLast.setText(lePath)
            self.l_pathLast.setToolTip(lePath)
            pathIsNone = self.l_pathLast.text() == "None"
            self.b_openLast.setEnabled(not pathIsNone)
            self.b_copyLast.setEnabled(not pathIsNone)
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
        self.chb_localOutput.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.cb_formats.activated.connect(self.stateManager.saveStatesToScene)
        self.b_openLast.clicked.connect(
            lambda: self.core.openFolder(os.path.dirname(self.l_pathLast.text()))
        )
        self.b_copyLast.clicked.connect(
            lambda: self.core.copyToClipboard(self.l_pathLast.text())
        )

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
        taskname = self.l_taskName.text()
        if taskname == "":
            taskname = "None"

        sText = text + " (%s)" % taskname
        if self.state.text(0).endswith(" - disabled"):
            sText += " - disabled"

        self.state.setText(0, sText)

    @err_catcher(name=__name__)
    def setTaskname(self, taskname):
        self.l_taskName.setText(taskname)
        self.updateUi()

    @err_catcher(name=__name__)
    def changeTask(self):
        import CreateItem

        self.nameWin = CreateItem.CreateItem(
            startText=self.l_taskName.text(),
            showTasks=True,
            taskType="playblast",
            core=self.core,
        )
        self.core.parentWindow(self.nameWin)
        self.nameWin.setWindowTitle("Change Taskname")
        self.nameWin.l_item.setText("Taskname:")
        self.nameWin.buttonBox.buttons()[0].setText("Ok")
        self.nameWin.e_item.selectAll()
        result = self.nameWin.exec_()

        if result == 1:
            self.l_taskName.setText(self.nameWin.e_item.text())
            self.nameChanged(self.e_name.text())

            self.setTaskWarn(False)

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
            res = self.core.appPlugin.getResolution()
        else:
            try:
                pwidth = int(resolution.split("x")[0])
                pheight = int(resolution.split("x")[1])
                res = [pwidth, pheight]
            except:
                res = getattr(self.core.appPlugin, "evaluateResolution", lambda x: None)(resolution)

        return res

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

        self.updateRange()

        if self.l_taskName.text() != "":
            self.setTaskWarn(False)

        self.nameChanged(self.e_name.text())

        return True

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
        if rangeType == "State Manager":
            startFrame = self.stateManager.sp_rangeStart.value()
            endFrame = self.stateManager.sp_rangeEnd.value()
        elif rangeType == "Scene":
            startFrame, endFrame = self.core.appPlugin.getFrameRange(self)
        elif rangeType == "Shot":
            fileName = self.core.getCurrentFileName()
            fnameData = self.core.getScenefileData(fileName)
            if fnameData["entity"] == "shot":
                frange = self.core.entities.getShotRange(fnameData["entityName"])
                if frange:
                    startFrame, endFrame = frange
        elif rangeType == "Single Frame":
            startFrame = self.core.appPlugin.getCurrentFrame()
        elif rangeType == "Custom":
            startFrame = self.sp_rangeStart.value()
            endFrame = self.sp_rangeEnd.value()

        if startFrame is not None:
            startFrame = int(startFrame)

        if endFrame is not None:
            endFrame = int(endFrame)

        return startFrame, endFrame

    @err_catcher(name=__name__)
    def updateLastPath(self, path):
        self.l_pathLast.setText(path)
        self.l_pathLast.setToolTip(path)
        self.b_openLast.setEnabled(True)
        self.b_copyLast.setEnabled(True)

    @err_catcher(name=__name__)
    def preExecuteState(self):
        warnings = []

        if self.l_taskName.text() == "":
            warnings.append(["No taskname is given.", "", 3])

        rangeType = self.cb_rangeType.currentText()
        startFrame, endFrame = self.getFrameRange(rangeType)

        if startFrame is None:
            warnings.append(["Framerange is invalid.", "", 3])

        warnings += self.core.appPlugin.sm_playblast_preExecute(self)

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def getOutputName(self, useVersion="next", extension=None):
        if self.l_taskName.text() == "":
            return

        task = self.l_taskName.text()
        extension = extension or self.cb_formats.currentText()
        fileName = self.core.getCurrentFileName()
        fnameData = self.core.getScenefileData(fileName)
        framePadding = "." if self.cb_rangeType.currentText() != "Single Frame" else ""

        if "entityName" not in fnameData:
            return

        location = "global"
        if (
            self.core.useLocalFiles
            and self.chb_localOutput.isChecked()
        ):
            location = "local"

        if fnameData["entity"] == "asset":
            assetPath = self.core.getEntityBasePath(fileName)
            entityName = self.core.entities.getAssetRelPathFromPath(assetPath)
        else:
            entityName = fnameData["entityName"]

        outputPath = self.core.mediaProducts.generatePlayblastPath(
            entity=fnameData["entity"],
            entityName=entityName,
            task=task,
            extension=extension,
            framePadding=framePadding,
            comment=fnameData["comment"],
            version=useVersion if useVersion != "next" else None,
            location=location
        )

        outputPath = outputPath.replace("\\", "/")
        outputFolder = os.path.dirname(outputPath)
        hVersion = self.core.mediaProducts.getVersionFromPlayblastFilepath(outputPath)

        return outputPath, outputFolder, hVersion

    @err_catcher(name=__name__)
    def executeState(self, parent, useVersion="next"):
        # 	if not self.core.uiAvailable:
        # 		return [self.state.text(0) + ": error - Playblasts are not supported without UI."]

        if self.l_taskName.text() == "":
            return [
                self.state.text(0)
                + ": error - No taskname is given. Skipped the activation of this state."
            ]

        fileName = self.core.getCurrentFileName()

        result = self.getOutputName(useVersion=useVersion, extension=".jpg")
        if not result:
            return [
                self.state.text(0)
                + ": error - Couldn't generate an outputpath for this state.\nMake sure your scenefile is saved correctly in the pipeline."
            ]
            return

        outputName, outputPath, hVersion = result

        outLength = len(outputName)
        if platform.system() == "Windows" and outLength > 255:
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
            if res and "outputName" in res:
                outputName = res["outputName"]

        outputPath = os.path.dirname(outputName)
        if not os.path.exists(outputPath):
            os.makedirs(outputPath)

        self.core.saveVersionInfo(
            location=outputPath, version=hVersion, origin=fileName
        )

        self.updateLastPath(outputName)
        self.stateManager.saveStatesToScene()

        self.core.saveScene(versionUp=False, prismReq=False)

        try:
            self.core.appPlugin.sm_playblast_createPlayblast(
                self, jobFrames=jobFrames, outputName=outputName
            )

            getattr(self.core.appPlugin, "sm_playblast_postExecute", lambda x: None)(
                self
            )

            if self.cb_formats.currentText() == ".mp4":
                mediaBaseName = os.path.splitext(outputName)[0]
                videoOutput = mediaBaseName + "mp4"
                inputpath = (
                    os.path.splitext(outputName)[0]
                    + "%04d".replace("4", str(self.core.framePadding))
                    + os.path.splitext(outputName)[1]
                )
                result = self.core.media.convertMedia(inputpath, jobFrames[0], videoOutput)

                if not os.path.exists(videoOutput):
                    logger.warning("fmmpeg output: %s" % str(result))
                    return [
                        self.state.text(0)
                        + " - error occurred during conversion of jpg files to mp4. Check the console for more information."
                    ]

                delFiles = []
                for i in os.listdir(outputPath):
                    if i.startswith(os.path.basename(mediaBaseName)) and i.endswith(
                        ".jpg"
                    ):
                        delFiles.append(os.path.join(outputPath, i))

                for i in delFiles:
                    try:
                        os.remove(i)
                    except:
                        pass

                self.updateLastPath(videoOutput)

            kwargs = {
                "state": self,
                "scenefile": fileName,
                "startframe": jobFrames[0],
                "endframe": jobFrames[1],
                "outputpath": outputName,
            }
            result = self.core.callback("postPlayblast", **kwargs)

            for res in result:
                if res and "outputName" in res:
                    outputPath = os.path.dirname(res["outputName"])

            if len(os.listdir(outputPath)) > 1:
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
                "statename": self.e_name.text(),
                "taskname": self.l_taskName.text(),
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
                "localoutput": str(self.chb_localOutput.isChecked()),
                "lastexportpath": self.l_pathLast.text().replace("\\", "/"),
                "stateenabled": str(self.state.checkState(0)),
                "outputformat": str(self.cb_formats.currentText()),
            }
        )
        return stateProps
