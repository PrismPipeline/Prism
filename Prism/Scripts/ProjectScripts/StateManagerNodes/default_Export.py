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

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

from PrismUtils.Decorators import err_catcher


class ExportClass(object):
    className = "Export"
    listType = "Export"

    @err_catcher(name=__name__)
    def setup(self, state, core, stateManager, node=None, stateData=None):
        self.state = state
        self.core = core
        self.stateManager = stateManager

        self.e_name.setText(state.text(0))

        self.l_name.setVisible(False)
        self.e_name.setVisible(False)

        self.curCam = None

        self.oldPalette = self.b_changeTask.palette()
        self.warnPalette = QPalette()
        self.warnPalette.setColor(QPalette.Button, QColor(200, 0, 0))
        self.warnPalette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        self.b_changeTask.setPalette(self.warnPalette)

        self.w_cam.setVisible(False)
        self.w_sCamShot.setVisible(False)
        self.w_selectCam.setVisible(False)

        self.nodes = []

        self.preDelete = lambda item: self.core.appPlugin.sm_export_preDelete(self)

        self.rangeTypes = ["State Manager", "Scene", "Shot", "Single Frame", "Custom"]
        self.cb_rangeType.addItems(self.rangeTypes)
        for idx, rtype in enumerate(self.rangeTypes):
            self.cb_rangeType.setItemData(idx, self.stateManager.getFrameRangeTypeToolTip(rtype), Qt.ToolTipRole)

        if self.stateManager.standalone:
            outputFormats = []
            if self.core.appPlugin.pluginName != "Houdini":
                outputFormats += list(self.core.appPlugin.outputFormats)
            for i in self.core.unloadedAppPlugins.values():
                if i.pluginName != "Houdini":
                    outputFormats += getattr(i, "outputFormats", [])
            outputFormats = sorted(set(outputFormats))
        else:
            outputFormats = self.core.appPlugin.outputFormats

        self.cb_outType.addItems(outputFormats)
        self.export_paths = self.core.paths.getExportProductBasePaths()
        self.cb_outPath.addItems(list(self.export_paths.keys()))
        if len(self.export_paths) < 2:
            self.w_outPath.setVisible(False)
        getattr(self.core.appPlugin, "sm_export_startup", lambda x: None)(self)
        self.nameChanged(state.text(0))
        self.connectEvents()

        if stateData is not None:
            self.loadData(stateData)
        else:
            startFrame = self.core.appPlugin.getFrameRange(self)[0]
            self.sp_rangeStart.setValue(startFrame)
            self.sp_rangeEnd.setValue(startFrame)
            fileName = self.core.getCurrentFileName()
            fnameData = self.core.getScenefileData(fileName)
            if (
                os.path.exists(fileName)
                and fnameData["entity"] == "shot"
                and self.core.fileInPipeline(fileName)
            ):
                idx = self.cb_sCamShot.findText(fnameData["entityName"])
                if idx != -1:
                    self.cb_sCamShot.setCurrentIndex(idx)

            if fnameData.get("category"):
                self.setTaskname(fnameData.get("category"))
                getattr(self.core.appPlugin, "sm_export_updateObjects", lambda x: None)(self)

            if not self.stateManager.standalone:
                self.addObjects()

        self.typeChanged(self.cb_outType.currentText())

    @err_catcher(name=__name__)
    def loadData(self, data):
        if "taskname" in data:
            self.setTaskname(data["taskname"])
        if "connectednodes" in data:
            self.nodes = eval(data["connectednodes"])

        self.updateUi()

        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "rangeType" in data:
            idx = self.cb_rangeType.findText(data["rangeType"])
            if idx != -1:
                self.cb_rangeType.setCurrentIndex(idx)
                self.updateRange()
        if "startframe" in data:
            self.sp_rangeStart.setValue(int(data["startframe"]))
        if "endframe" in data:
            self.sp_rangeEnd.setValue(int(data["endframe"]))
        if "curoutputpath" in data:
            idx = self.cb_outPath.findText(data["curoutputpath"])
            if idx != -1:
                self.cb_outPath.setCurrentIndex(idx)
        if "curoutputtype" in data:
            idx = self.cb_outType.findText(data["curoutputtype"])
            if idx != -1:
                self.cb_outType.setCurrentIndex(idx)
        if "wholescene" in data:
            self.chb_wholeScene.setChecked(eval(data["wholescene"]))
        if "unitconvert" in data:
            self.chb_convertExport.setChecked(eval(data["unitconvert"]))
        if "additionaloptions" in data:
            self.chb_additionalOptions.setChecked(eval(data["additionaloptions"]))
        if "currentcam" in data:
            camName = getattr(self.core.appPlugin, "getCamName", lambda x, y: "")(
                self, data["currentcam"]
            )
            idx = self.cb_cam.findText(camName)
            if idx != -1:
                self.curCam = self.camlist[idx]
                self.cb_cam.setCurrentIndex(idx)
                self.nameChanged(self.e_name.text())
        if "currentscamshot" in data:
            idx = self.cb_sCamShot.findText(data["currentscamshot"])
            if idx != -1:
                self.cb_sCamShot.setCurrentIndex(idx)
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

        getattr(self.core.appPlugin, "sm_export_loadData", lambda x, y: None)(
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
        self.cb_outPath.activated[str].connect(self.stateManager.saveStatesToScene)
        self.cb_outType.activated[str].connect(self.typeChanged)
        self.chb_wholeScene.stateChanged.connect(self.wholeSceneChanged)
        self.chb_convertExport.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_additionalOptions.stateChanged.connect(
            self.stateManager.saveStatesToScene
        )
        self.lw_objects.itemSelectionChanged.connect(
            lambda: self.core.appPlugin.selectNodes(self)
        )
        self.lw_objects.customContextMenuRequested.connect(self.rcObjects)
        self.cb_cam.activated.connect(self.setCam)
        self.cb_sCamShot.activated.connect(self.stateManager.saveStatesToScene)
        self.b_selectCam.clicked.connect(lambda: self.core.appPlugin.selectCam(self))
        self.b_openLast.clicked.connect(
            lambda: self.core.openFolder(os.path.dirname(self.l_pathLast.text()))
        )
        self.b_copyLast.clicked.connect(
            lambda: self.core.copyToClipboard(self.l_pathLast.text())
        )
        if not self.stateManager.standalone:
            self.b_add.clicked.connect(self.addObjects)

    @err_catcher(name=__name__)
    def rangeTypeChanged(self, state):
        self.updateRange()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def wholeSceneChanged(self, state):
        self.gb_objects.setEnabled(not state == Qt.Checked)
        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def nameChanged(self, text):
        if self.cb_outType.currentText() == "ShotCam":
            sText = text + " (ShotCam - %s)" % self.cb_cam.currentText()
        else:
            taskname = self.getTaskname()
            if taskname == "":
                taskname = "None"

            sText = text + " (%s)" % taskname

        if self.state.text(0).endswith(" - disabled"):
            sText += " - disabled"

        self.state.setText(0, sText)

    @err_catcher(name=__name__)
    def getOutputType(self):
        return self.cb_outType.currentText()

    @err_catcher(name=__name__)
    def getTaskname(self):
        taskName = self.l_taskName.text()
        return taskName

    @err_catcher(name=__name__)
    def setTaskname(self, taskname):
        prevTaskName = self.getTaskname()
        default_func = lambda x1, x2, newTaskName: self.l_taskName.setText(
            newTaskName
        )
        getattr(self.core.appPlugin, "sm_export_setTaskText", default_func)(
            self, prevTaskName, taskname
        )
        self.updateUi()

    @err_catcher(name=__name__)
    def getUnitConvert(self):
        return self.chb_convertExport.isChecked()

    @err_catcher(name=__name__)
    def changeTask(self):
        import CreateItem

        self.nameWin = CreateItem.CreateItem(
            startText=self.getTaskname(),
            showTasks=True,
            taskType="export",
            core=self.core,
        )
        self.core.parentWindow(self.nameWin)
        self.nameWin.setWindowTitle("Change Taskname")
        self.nameWin.l_item.setText("Taskname:")
        self.nameWin.buttonBox.buttons()[0].setText("Ok")
        self.nameWin.e_item.selectAll()
        result = self.nameWin.exec_()

        if result == 1:
            self.setTaskname(self.nameWin.e_item.text())
            self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def rcObjects(self, pos):
        item = self.lw_objects.itemAt(pos)

        if item is None:
            self.lw_objects.setCurrentRow(-1)

        createMenu = QMenu()

        if not item is None:
            actRemove = QAction("Remove", self)
            actRemove.triggered.connect(lambda: self.removeItem(item))
            createMenu.addAction(actRemove)
        else:
            self.lw_objects.setCurrentRow(-1)

        actClear = QAction("Clear", self)
        actClear.triggered.connect(self.clearItems)
        createMenu.addAction(actClear)

        self.updateUi()
        createMenu.exec_(self.lw_objects.mapToGlobal(pos))

    @err_catcher(name=__name__)
    def addObjects(self, objects=None):
        self.core.appPlugin.sm_export_addObjects(self, objects)

    @err_catcher(name=__name__)
    def removeItem(self, item):
        items = self.lw_objects.selectedItems()
        for i in reversed(self.lw_objects.selectedItems()):
            rowNum = self.lw_objects.row(i)
            self.core.appPlugin.sm_export_removeSetItem(self, self.nodes[rowNum])
            del self.nodes[rowNum]
            self.lw_objects.takeItem(rowNum)

        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def clearItems(self):
        self.lw_objects.clear()
        self.nodes = []
        if not self.stateManager.standalone:
            self.core.appPlugin.sm_export_clearSet(self)

        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def updateUi(self):
        self.cb_cam.clear()
        self.camlist = camNames = []
        if not self.stateManager.standalone:
            self.camlist = self.core.appPlugin.getCamNodes(self)
            camNames = [self.core.appPlugin.getCamName(self, i) for i in self.camlist]

        self.cb_cam.addItems(camNames)
        if self.curCam in self.camlist:
            self.cb_cam.setCurrentIndex(self.camlist.index(self.curCam))
        else:
            self.cb_cam.setCurrentIndex(0)
            if len(self.camlist) > 0:
                self.curCam = self.camlist[0]
            else:
                self.curCam = None
            self.stateManager.saveStatesToScene()

        self.updateRange()

        curShot = self.cb_sCamShot.currentText()
        self.cb_sCamShot.clear()
        shotPath = self.core.getShotPath()
        shotNames = []
        omittedShots = self.core.getConfig("shot", config="omit", dft=[])

        if os.path.exists(shotPath):
            shotNames += [
                x
                for x in os.listdir(shotPath)
                if not x.startswith("_") and x not in omittedShots
            ]
        self.cb_sCamShot.addItems(shotNames)
        if curShot in shotNames:
            self.cb_sCamShot.setCurrentIndex(shotNames.index(curShot))
        else:
            self.cb_sCamShot.setCurrentIndex(0)
            self.stateManager.saveStatesToScene()

        selObjects = [x.text() for x in self.lw_objects.selectedItems()]
        self.lw_objects.clear()

        newObjList = []

        getattr(self.core.appPlugin, "sm_export_updateObjects", lambda x: None)(self)

        for node in self.nodes:
            if self.core.appPlugin.isNodeValid(self, node):
                item = QListWidgetItem(self.core.appPlugin.getNodeName(self, node))
                self.lw_objects.addItem(item)
                newObjList.append(node)

        if self.getTaskname():
            self.b_changeTask.setPalette(self.oldPalette)

        if self.lw_objects.count() == 0 and not self.chb_wholeScene.isChecked():
            getattr(
                self.core.appPlugin,
                "sm_export_colorObjList",
                lambda x: self.lw_objects.setStyleSheet(
                    "QListWidget { border: 3px solid rgb(200,0,0); }"
                ),
            )(self)
        else:
            getattr(
                self.core.appPlugin,
                "sm_export_unColorObjList",
                lambda x: self.lw_objects.setStyleSheet(
                    "QListWidget { border: 3px solid rgb(114,114,114); }"
                ),
            )(self)

        for i in range(self.lw_objects.count()):
            if self.lw_objects.item(i).text() in selObjects:
                self.lw_objects.setCurrentItem(self.lw_objects.item(i))

        self.nodes = newObjList

        self.nameChanged(self.e_name.text())

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
    def typeChanged(self, idx):
        isSCam = idx == "ShotCam"
        self.w_cam.setVisible(isSCam)
        self.w_sCamShot.setVisible(isSCam)
        self.w_selectCam.setVisible(isSCam)
        self.w_taskname.setVisible(not isSCam)
        getattr(self.core.appPlugin, "sm_export_typeChanged", lambda x, y: None)(
            self, idx
        )
        self.w_wholeScene.setVisible(not isSCam)
        self.gb_objects.setVisible(not isSCam)

        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def setCam(self, index):
        self.curCam = self.camlist[index]
        self.updateUi()
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
    def preExecuteState(self):
        warnings = []

        rangeType = self.cb_rangeType.currentText()
        startFrame, endFrame = self.getFrameRange(rangeType)

        if self.cb_outType.currentText() == "ShotCam":
            if self.curCam is None:
                warnings.append(["No camera specified.", "", 3])
        else:
            if not self.getTaskname():
                warnings.append(["No taskname is given.", "", 3])

            if not self.chb_wholeScene.isChecked() and len(self.nodes) == 0:
                warnings.append(["No objects are selected for export.", "", 3])

        if startFrame is None:
            warnings.append(["Framerange is invalid.", "", 3])

        warnings += self.core.appPlugin.sm_export_preExecute(self, startFrame, endFrame)

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def getOutputName(self, useVersion="next"):
        fileName = self.core.getCurrentFileName()
        fnameData = self.core.getScenefileData(fileName)
        location = self.cb_outPath.currentText()
        version = useVersion if useVersion != "next" else None

        if "entityName" not in fnameData:
            return

        if self.cb_outType.currentText() == "ShotCam":
            shot = self.cb_sCamShot.currentText()
            task = "_ShotCam"
            comment = fnameData["comment"]

            outputPath = self.core.products.generateProductPath(
                entity="shot",
                entityName=shot,
                task=task,
                extension="",
                comment=comment,
                version=version,
                location=location
            )
        else:
            task = self.getTaskname()
            if not task:
                return

            rangeType = self.cb_rangeType.currentText()
            extension = self.cb_outType.currentText()

            if rangeType == "Single Frame" or extension != ".obj":
                framePadding = ""
            else:
                framePadding = "." + "#"*self.core.framePadding

            if fnameData["entity"] == "asset":
                assetPath = self.core.getEntityBasePath(fileName)
                entityName = self.core.entities.getAssetRelPathFromPath(assetPath)
            else:
                entityName = fnameData["entityName"]

            outputPath = self.core.products.generateProductPath(
                entity=fnameData["entity"],
                entityName=entityName,
                task=task,
                extension=extension,
                framePadding=framePadding,
                comment=fnameData["comment"],
                version=version,
                location=location
            )

        outputFolder = os.path.dirname(outputPath)
        hVersion = self.core.products.getVersionFromFilepath(outputPath)

        return outputPath, outputFolder, hVersion

    @err_catcher(name=__name__)
    def executeState(self, parent, useVersion="next"):
        rangeType = self.cb_rangeType.currentText()
        startFrame, endFrame = self.getFrameRange(rangeType)
        if startFrame is None:
            return [self.state.text(0) + ": error - Framerange is invalid"]

        if rangeType == "Single Frame":
            endFrame = startFrame

        if self.cb_outType.currentText() == "ShotCam":
            if self.curCam is None:
                return [
                    self.state.text(0)
                    + ": error - No camera specified. Skipped the activation of this state."
                ]

            if self.cb_sCamShot.currentText() == "":
                return [
                    self.state.text(0)
                    + ": error - No Shot specified. Skipped the activation of this state."
                ]

            fileName = self.core.getCurrentFileName()

            outputName, outputPath, hVersion = self.getOutputName(useVersion=useVersion)

            outLength = len(outputName)
            if platform.system() == "Windows" and outLength > 255:
                return [
                    self.state.text(0)
                    + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, taskname or projectpath."
                    % outLength
                ]

            kwargs = {
                "state": self,
                "scenefile": fileName,
                "startframe": startFrame,
                "endframe": endFrame,
                "outputpath": outputName,
            }

            result = self.core.callback("preExport", **kwargs)

            for res in result:
                if res and "outputName" in res:
                    outputName = res["outputName"]

            outputPath = os.path.dirname(outputName)
            if not os.path.exists(outputPath):
                os.makedirs(outputPath)

            self.core.saveVersionInfo(
                location=os.path.dirname(outputPath),
                version=hVersion,
                origin=fileName,
                fps=startFrame != endFrame,
            )

            self.core.appPlugin.sm_export_exportShotcam(
                self, startFrame=startFrame, endFrame=endFrame, outputName=outputName
            )

            self.l_pathLast.setText(outputName)
            self.l_pathLast.setToolTip(outputName)
            self.b_openLast.setEnabled(True)
            self.b_copyLast.setEnabled(True)

            kwargs = {
                "state": self,
                "scenefile": fileName,
                "startframe": startFrame,
                "endframe": endFrame,
                "outputpath": outputName,
            }

            result = self.core.callback("postExport", **kwargs)

            for res in result:
                if res and "outputName" in res:
                    outputName = res["outputName"]

            self.stateManager.saveStatesToScene()

            if os.path.exists(
                outputName + ".abc"
            ):  # and os.path.exists(outputName + ".fbx"):
                return [self.state.text(0) + " - success"]
            else:
                return [self.state.text(0) + " - unknown error"]
        else:

            if not self.getTaskname():
                return [
                    self.state.text(0)
                    + ": error - No taskname is given. Skipped the activation of this state."
                ]

            if (
                not self.chb_wholeScene.isChecked()
                and len(
                    [x for x in self.nodes if self.core.appPlugin.isNodeValid(self, x)]
                )
                == 0
            ):
                return [
                    self.state.text(0)
                    + ": error - No objects chosen. Skipped the activation of this state."
                ]

            fileName = self.core.getCurrentFileName()

            outputName, outputPath, hVersion = self.getOutputName(useVersion=useVersion)

            outLength = len(outputName)
            if platform.system() == "Windows" and outLength > 255:
                return [
                    self.state.text(0)
                    + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, taskname or projectpath."
                    % outLength
                ]

            kwargs = {
                "state": self,
                "scenefile": fileName,
                "startframe": startFrame,
                "endframe": endFrame,
                "outputpath": outputName,
            }

            result = self.core.callback("preExport", **kwargs)

            for res in result:
                if res and "outputName" in res:
                    outputName = res["outputName"]

            outputPath = os.path.dirname(outputName)
            if not os.path.exists(outputPath):
                os.makedirs(outputPath)

            self.core.saveVersionInfo(
                location=os.path.dirname(outputPath),
                version=hVersion,
                origin=fileName,
                fps=startFrame != endFrame,
            )

            try:
                outputName = self.core.appPlugin.sm_export_exportAppObjects(
                    self,
                    startFrame=startFrame,
                    endFrame=endFrame,
                    outputName=outputName,
                )

                if outputName == False:
                    return [self.state.text(0) + " - error"]

                if outputName.startswith("Canceled"):
                    return [self.state.text(0) + " - error: %s" % outputName]

                self.l_pathLast.setText(outputName)
                self.l_pathLast.setToolTip(outputName)
                self.b_openLast.setEnabled(True)
                self.b_copyLast.setEnabled(True)

                self.stateManager.saveStatesToScene()

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "%s ERROR - sm_default_export %s:\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    self.core.version,
                    traceback.format_exc(),
                )
                self.core.writeErrorLog(erStr)
                return [
                    self.state.text(0)
                    + " - unknown error (view console for more information)"
                ]

            useMaster = self.core.getConfig("globals", "useMasterVersion", dft=False, config="project")
            if useMaster:
                self.core.products.updateMasterVersion(outputName)

            kwargs = {
                "state": self,
                "scenefile": fileName,
                "startframe": startFrame,
                "endframe": endFrame,
                "outputpath": outputName,
            }

            result = self.core.callback("postExport", **kwargs)

            for res in result:
                if res and "outputName" in res:
                    outputName = res["outputName"]

            if os.path.exists(outputName):
                return [self.state.text(0) + " - success"]
            else:
                return [self.state.text(0) + " - unknown error (files do not exist)"]

    @err_catcher(name=__name__)
    def getStateProps(self):
        stateProps = {}
        stateProps.update(
            {
                "statename": self.e_name.text(),
                "taskname": self.getTaskname(),
                "rangeType": str(self.cb_rangeType.currentText()),
                "startframe": self.sp_rangeStart.value(),
                "endframe": self.sp_rangeEnd.value(),
                "unitconvert": str(self.chb_convertExport.isChecked()),
                "additionaloptions": str(self.chb_additionalOptions.isChecked()),
                "curoutputpath": self.cb_outPath.currentText(),
                "curoutputtype": self.cb_outType.currentText(),
                "wholescene": str(self.chb_wholeScene.isChecked()),
                "connectednodes": str(self.nodes),
                "currentcam": str(self.curCam),
                "currentscamshot": self.cb_sCamShot.currentText(),
                "lastexportpath": self.l_pathLast.text().replace("\\", "/"),
                "stateenabled": str(self.state.checkState(0)),
            }
        )
        getattr(self.core.appPlugin, "sm_export_getStateProps", lambda x, y: None)(self, stateProps)
        return stateProps
