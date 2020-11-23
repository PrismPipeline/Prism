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
import platform

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


class ImageRenderClass(object):
    className = "ImageRender"
    listType = "Export"

    @err_catcher(name=__name__)
    def setup(self, state, core, stateManager, node=None, stateData=None):
        self.state = state
        self.core = core
        self.stateManager = stateManager

        self.curCam = None
        self.renderingStarted = False
        self.cleanOutputdir = True

        self.e_name.setText(state.text(0))

        self.rangeTypes = ["State Manager", "Scene", "Shot", "Single Frame", "Custom", "Expression"]
        self.cb_rangeType.addItems(self.rangeTypes)
        for idx, rtype in enumerate(self.rangeTypes):
            self.cb_rangeType.setItemData(idx, self.stateManager.getFrameRangeTypeToolTip(rtype), Qt.ToolTipRole)
        self.w_frameExpression.setToolTip(self.stateManager.getFrameRangeTypeToolTip("ExpressionField"))

        self.renderPresets = (
            self.stateManager.stateTypes["RenderSettings"].getPresets(self.core)
            if "RenderSettings" in self.stateManager.stateTypes
            else {}
        )
        if self.renderPresets:
            self.cb_renderPreset.addItems(self.renderPresets.keys())
        else:
            self.w_renderPreset.setVisible(False)

        self.l_name.setVisible(False)
        self.e_name.setVisible(False)
        self.gb_submit.setChecked(False)
        self.f_renderLayer.setVisible(False)

        getattr(self.core.appPlugin, "sm_render_startup", lambda x: None)(self)

        if not getattr(self.core.appPlugin, "sm_render_startup", lambda x: False)(self):
            self.gb_Vray.setVisible(False)

        self.outputFormats = [
            ".exr",
            ".png",
            ".jpg",
        ]

        self.cb_format.addItems(self.outputFormats)

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

        self.f_localOutput.setVisible(self.core.useLocalFiles)
        self.e_osSlaves.setText("All")

        self.connectEvents()

        self.oldPalette = self.b_changeTask.palette()
        self.warnPalette = QPalette()
        self.warnPalette.setColor(QPalette.Button, QColor(200, 0, 0))
        self.warnPalette.setColor(QPalette.ButtonText, QColor(255, 255, 255))

        self.setTaskWarn(True)

        self.nameChanged(state.text(0))

        for i in self.core.rfManagers.values():
            self.cb_manager.addItem(i.pluginName)
            i.sm_houExport_startup(self)

        if self.cb_manager.count() == 0:
            self.gb_submit.setVisible(False)

        self.managerChanged(True)

        if stateData is not None:
            self.loadData(stateData)
        else:
            fileName = self.core.getCurrentFileName()
            fnameData = self.core.getScenefileData(fileName)
            if fnameData.get("category"):
                self.l_taskName.setText(fnameData.get("category"))

            self.updateUi()

    @err_catcher(name=__name__)
    def loadData(self, data):
        if "taskname" in data:
            self.l_taskName.setText(data["taskname"])
            if data["taskname"] != "":
                self.setTaskWarn(False)

        self.updateUi()

        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "renderpresetoverride" in data:
            res = eval(data["renderpresetoverride"])
            self.chb_renderPreset.setChecked(res)
        if "currentrenderpreset" in data:
            idx = self.cb_renderPreset.findText(data["currentrenderpreset"])
            if idx != -1:
                self.cb_renderPreset.setCurrentIndex(idx)
                self.stateManager.saveStatesToScene()
        if "rangeType" in data:
            idx = self.cb_rangeType.findText(data["rangeType"])
            if idx != -1:
                self.cb_rangeType.setCurrentIndex(idx)
                self.updateRange()
        if "startframe" in data:
            self.sp_rangeStart.setValue(int(data["startframe"]))
        if "endframe" in data:
            self.sp_rangeEnd.setValue(int(data["endframe"]))
        if "frameExpression" in data:
            self.le_frameExpression.setText(data["frameExpression"])
        if "currentcam" in data:
            camName = getattr(self.core.appPlugin, "getCamName", lambda x, y: "")(
                self, data["currentcam"]
            )
            idx = self.cb_cam.findText(camName)
            if idx != -1:
                self.curCam = self.camlist[idx]
                self.cb_cam.setCurrentIndex(idx)
                self.stateManager.saveStatesToScene()
        if "resoverride" in data:
            res = eval(data["resoverride"])
            self.chb_resOverride.setChecked(res[0])
            self.sp_resWidth.setValue(res[1])
            self.sp_resHeight.setValue(res[2])
        if "localoutput" in data:
            self.chb_localOutput.setChecked(eval(data["localoutput"]))
        if "renderlayer" in data:
            idx = self.cb_renderLayer.findText(data["renderlayer"])
            if idx != -1:
                self.cb_renderLayer.setCurrentIndex(idx)
                self.stateManager.saveStatesToScene()
        if "outputFormat" in data:
            idx = self.cb_format.findText(data["outputFormat"])
            if idx != -1:
                self.cb_format.setCurrentIndex(idx)
        if "vrayoverride" in data:
            self.chb_override.setChecked(eval(data["vrayoverride"]))
        if "vrayminsubdivs" in data:
            self.sp_minSubdivs.setValue(int(data["vrayminsubdivs"]))
        if "vraymaxsubdivs" in data:
            self.sp_maxSubdivs.setValue(int(data["vraymaxsubdivs"]))
        if "vraycthreshold" in data:
            self.sp_cThres.setValue(float(data["vraycthreshold"]))
        if "vraynthreshold" in data:
            self.sp_nThres.setValue(float(data["vraynthreshold"]))
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
        if "osdependencies" in data:
            self.chb_osDependencies.setChecked(eval(data["osdependencies"]))
        if "osupload" in data:
            self.chb_osUpload.setChecked(eval(data["osupload"]))
        if "ospassets" in data:
            self.chb_osPAssets.setChecked(eval(data["ospassets"]))
        if "osslaves" in data:
            self.e_osSlaves.setText(data["osslaves"])
        if "curdlgroup" in data:
            idx = self.cb_dlGroup.findText(data["curdlgroup"])
            if idx != -1:
                self.cb_dlGroup.setCurrentIndex(idx)
        if "dlconcurrent" in data:
            self.sp_dlConcurrentTasks.setValue(int(data["dlconcurrent"]))
        if "dlgpupt" in data:
            self.sp_dlGPUpt.setValue(int(data["dlgpupt"]))
            self.gpuPtChanged()
        if "dlgpudevices" in data:
            self.le_dlGPUdevices.setText(data["dlgpudevices"])
            self.gpuDevicesChanged()
        if "enablepasses" in data:
            self.gb_passes.setChecked(eval(data["enablepasses"]))
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

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.b_changeTask.clicked.connect(self.changeTask)
        self.chb_renderPreset.stateChanged.connect(self.presetOverrideChanged)
        self.cb_renderPreset.activated.connect(self.stateManager.saveStatesToScene)
        self.cb_rangeType.activated.connect(self.rangeTypeChanged)
        self.sp_rangeStart.editingFinished.connect(self.startChanged)
        self.sp_rangeEnd.editingFinished.connect(self.endChanged)
        self.le_frameExpression.textChanged.connect(self.frameExpressionChanged)
        self.le_frameExpression.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.le_frameExpression.setMouseTracking(True)
        self.le_frameExpression.origMoveEvent = self.le_frameExpression.mouseMoveEvent
        self.le_frameExpression.mouseMoveEvent = self.exprMoveEvent
        self.le_frameExpression.leaveEvent = self.exprLeaveEvent
        self.le_frameExpression.focusOutEvent = self.exprFocusOutEvent
        self.cb_cam.activated.connect(self.setCam)
        self.chb_resOverride.stateChanged.connect(self.resOverrideChanged)
        self.sp_resWidth.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.sp_resHeight.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.b_resPresets.clicked.connect(self.showResPresets)
        self.chb_localOutput.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.cb_renderLayer.activated.connect(self.stateManager.saveStatesToScene)
        self.cb_format.activated.connect(self.stateManager.saveStatesToScene)
        self.chb_override.stateChanged.connect(self.overrideChanged)
        self.sp_minSubdivs.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.sp_maxSubdivs.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.sp_cThres.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.sp_nThres.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.gb_submit.toggled.connect(self.rjToggled)
        self.cb_manager.activated.connect(self.managerChanged)
        self.sp_rjPrio.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.sp_rjFramesPerTask.editingFinished.connect(
            self.stateManager.saveStatesToScene
        )
        self.sp_rjTimeout.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.chb_rjSuspended.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_osDependencies.stateChanged.connect(
            self.stateManager.saveStatesToScene
        )
        self.chb_osUpload.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_osPAssets.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.e_osSlaves.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.b_osSlaves.clicked.connect(self.openSlaves)
        self.cb_dlGroup.activated.connect(self.stateManager.saveStatesToScene)
        self.sp_dlConcurrentTasks.editingFinished.connect(
            self.stateManager.saveStatesToScene
        )
        self.sp_dlGPUpt.editingFinished.connect(self.gpuPtChanged)
        self.le_dlGPUdevices.editingFinished.connect(self.gpuDevicesChanged)
        self.gb_passes.toggled.connect(self.stateManager.saveStatesToScene)
        self.b_addPasses.clicked.connect(self.showPasses)
        self.lw_passes.customContextMenuRequested.connect(self.rclickPasses)
        self.b_openLast.clicked.connect(
            lambda: self.core.openFolder(os.path.dirname(self.l_pathLast.text()))
        )
        self.b_copyLast.clicked.connect(
            lambda: self.core.copyToClipboard(self.l_pathLast.text())
        )
        self.lw_passes.itemDoubleClicked.connect(
            lambda x: self.core.appPlugin.sm_render_openPasses(self)
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
    def frameExpressionChanged(self, text=None):
        if not hasattr(self, "expressionWinLabel"):
            return

        frames = self.core.resolveFrameExpression(self.le_frameExpression.text())
        frameStr = ",".join([str(x) for x in frames]) or "invalid expression"
        self.expressionWinLabel.setText(frameStr)
        self.expressionWin.resize(1, 1)

    @err_catcher(name=__name__)
    def exprMoveEvent(self, event):
        self.showExpressionWin(event)
        if hasattr(self, "expressionWin") and self.expressionWin.isVisible():
            self.expressionWin.move(
                QCursor.pos().x() + 20, QCursor.pos().y() - self.expressionWin.height()
            )
        self.le_frameExpression.origMoveEvent(event)

    @err_catcher(name=__name__)
    def showExpressionWin(self, event):
        if (
            not hasattr(self, "expressionWin")
            or not self.expressionWin.isVisible()
        ):
            if hasattr(self, "expressionWin"):
                self.expressionWin.close()

            self.expressionWin = QFrame()
            ss = getattr(self.core.appPlugin, "getFrameStyleSheet", lambda x: "")(self)
            self.expressionWin.setStyleSheet(
                ss + """ .QFrame{ border: 2px solid rgb(100,100,100);} """
            )

            self.core.parentWindow(self.expressionWin)
            winwidth = 10
            winheight = 10
            VBox = QVBoxLayout()
            frames = self.core.resolveFrameExpression(self.le_frameExpression.text())
            frameStr = ",".join([str(x) for x in frames]) or "invalid expression"
            self.expressionWinLabel = QLabel(frameStr)
            VBox.addWidget(self.expressionWinLabel)
            self.expressionWin.setLayout(VBox)
            self.expressionWin.setWindowFlags(
                Qt.FramelessWindowHint  # hides the window controls
                | Qt.WindowStaysOnTopHint  # forces window to top... maybe
                | Qt.SplashScreen  # this one hides it from the task bar!
            )

            self.expressionWin.setGeometry(0, 0, winwidth, winheight)
            self.expressionWin.move(QCursor.pos().x() + 20, QCursor.pos().y())
            self.expressionWin.setAttribute(Qt.WA_ShowWithoutActivating)
            self.expressionWin.show()

    @err_catcher(name=__name__)
    def exprLeaveEvent(self, event):
        if hasattr(self, "expressionWin") and self.expressionWin.isVisible():
            self.expressionWin.close()

    @err_catcher(name=__name__)
    def exprFocusOutEvent(self, event):
        if hasattr(self, "expressionWin") and self.expressionWin.isVisible():
            self.expressionWin.close()

    @err_catcher(name=__name__)
    def setCam(self, index):
        self.curCam = self.camlist[index]
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
            taskType="render",
            core=self.core,
        )
        self.core.parentWindow(self.nameWin)
        self.nameWin.setWindowTitle("Change Taskname")
        self.nameWin.l_item.setText("Taskname:")
        self.nameWin.buttonBox.buttons()[0].setText("Ok")
        self.nameWin.e_item.selectAll()
        prevTaskName = self.l_taskName.text()
        result = self.nameWin.exec_()

        if result == 1:
            self.l_taskName.setText(self.nameWin.e_item.text())
            self.setTaskWarn(False)
            self.nameChanged(self.e_name.text())
            self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def presetOverrideChanged(self, checked):
        self.cb_renderPreset.setEnabled(checked)
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def resOverrideChanged(self, checked):
        self.sp_resWidth.setEnabled(checked)
        self.sp_resHeight.setEnabled(checked)
        self.b_resPresets.setEnabled(checked)

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def showResPresets(self):
        pmenu = QMenu()

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
    def overrideChanged(self, checked):
        if self.chb_override.isChecked():
            self.l_subdivs.setEnabled(True)
            self.sp_minSubdivs.setEnabled(True)
            self.sp_maxSubdivs.setEnabled(True)
            self.l_cThres.setEnabled(True)
            self.sp_cThres.setEnabled(True)
            self.l_nThres.setEnabled(True)
            self.sp_nThres.setEnabled(True)
        else:
            self.l_subdivs.setEnabled(False)
            self.sp_minSubdivs.setEnabled(False)
            self.sp_maxSubdivs.setEnabled(False)
            self.l_cThres.setEnabled(False)
            self.sp_cThres.setEnabled(False)
            self.l_nThres.setEnabled(False)
            self.sp_nThres.setEnabled(False)

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def updateUi(self):

        # update Cams
        self.cb_cam.clear()
        self.camlist = camNames = []

        if not self.stateManager.standalone:
            self.camlist = self.core.appPlugin.getCamNodes(self, cur=True)
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

        # update Render Layer
        curLayer = self.cb_renderLayer.currentText()
        self.cb_renderLayer.clear()

        layerList = getattr(
            self.core.appPlugin, "sm_render_getRenderLayer", lambda x: []
        )(self)

        self.cb_renderLayer.addItems(layerList)

        if curLayer in layerList:
            self.cb_renderLayer.setCurrentIndex(layerList.index(curLayer))
        else:
            self.cb_renderLayer.setCurrentIndex(0)
            self.stateManager.saveStatesToScene()

        if self.l_taskName.text() != "":
            self.setTaskWarn(False)

        if not self.gb_submit.isHidden():
            self.core.rfManagers[self.cb_manager.currentText()].sm_render_updateUI(self)

        getattr(self.core.appPlugin, "sm_render_refreshPasses", lambda x: None)(self)

        self.nameChanged(self.e_name.text())

        return True

    @err_catcher(name=__name__)
    def updateRange(self):
        rangeType = self.cb_rangeType.currentText()
        isCustom = rangeType == "Custom"
        isExp = rangeType == "Expression"
        self.l_rangeStart.setVisible(not isCustom and not isExp)
        self.l_rangeEnd.setVisible(not isCustom and not isExp)
        self.sp_rangeStart.setVisible(isCustom)
        self.sp_rangeEnd.setVisible(isCustom)
        self.w_frameRangeValues.setVisible(not isExp)
        self.w_frameExpression.setVisible(isExp)

        if not isCustom and not isExp:
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
            startFrame = int(startFrame)
            endFrame = int(endFrame)
        elif rangeType == "Shot":
            fileName = self.core.getCurrentFileName()
            fnameData = self.core.getScenefileData(fileName)
            if fnameData["entity"] == "shot":
                frange = self.core.entities.getShotRange(fnameData["entityName"])
                if frange:
                    startFrame, endFrame = frange
        elif rangeType == "Single Frame":
            startFrame = int(self.core.appPlugin.getCurrentFrame())
        elif rangeType == "Custom":
            startFrame = self.sp_rangeStart.value()
            endFrame = self.sp_rangeEnd.value()
        elif rangeType == "Expression":
            return self.core.resolveFrameExpression(self.le_frameExpression.text())

        if startFrame is not None:
            startFrame = int(startFrame)

        if endFrame is not None:
            endFrame = int(endFrame)

        return startFrame, endFrame

    @err_catcher(name=__name__)
    def openSlaves(self):
        try:
            del sys.modules["SlaveAssignment"]
        except:
            pass

        import SlaveAssignment

        self.sa = SlaveAssignment.SlaveAssignment(
            core=self.core, curSlaves=self.e_osSlaves.text()
        )
        result = self.sa.exec_()

        if result == 1:
            selSlaves = ""
            if self.sa.rb_exclude.isChecked():
                selSlaves = "exclude "
            if self.sa.rb_all.isChecked():
                selSlaves += "All"
            elif self.sa.rb_group.isChecked():
                selSlaves += "groups: "
                for i in self.sa.activeGroups:
                    selSlaves += i + ", "

                if selSlaves.endswith(", "):
                    selSlaves = selSlaves[:-2]

            elif self.sa.rb_custom.isChecked():
                slavesList = [x.text() for x in self.sa.lw_slaves.selectedItems()]
                for i in slavesList:
                    selSlaves += i + ", "

                if selSlaves.endswith(", "):
                    selSlaves = selSlaves[:-2]

            self.e_osSlaves.setText(selSlaves)
            self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def gpuPtChanged(self):
        self.w_dlGPUdevices.setEnabled(self.sp_dlGPUpt.value() == 0)
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def gpuDevicesChanged(self):
        self.w_dlGPUpt.setEnabled(self.le_dlGPUdevices.text() == "")
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def showPasses(self):
        steps = getattr(
            self.core.appPlugin, "sm_render_getRenderPasses", lambda x: None
        )(self)

        if steps is None or len(steps) == 0:
            return False

        if pVersion == 2:
            isStr = isinstance(steps, basestring)
        else:
            isStr = isinstance(steps, str)

        if isStr:
            steps = eval(steps)

        try:
            del sys.modules["ItemList"]
        except:
            pass

        import ItemList

        self.il = ItemList.ItemList(core=self.core)
        self.il.setWindowTitle("Select Passes")
        self.core.parentWindow(self.il)
        self.il.b_addStep.setVisible(False)
        self.il.tw_steps.doubleClicked.connect(self.il.accept)
        self.il.tw_steps.horizontalHeaderItem(0).setText("Name")
        self.il.tw_steps.setColumnHidden(1, True)
        for i in sorted(steps, key=lambda s: s.lower()):
            rc = self.il.tw_steps.rowCount()
            self.il.tw_steps.insertRow(rc)
            item1 = QTableWidgetItem(i)
            self.il.tw_steps.setItem(rc, 0, item1)

        result = self.il.exec_()

        if result != 1:
            return False

        for i in self.il.tw_steps.selectedItems():
            if i.column() == 0:
                self.core.appPlugin.sm_render_addRenderPass(
                    self, passName=i.text(), steps=steps
                )

        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def rclickPasses(self, pos):
        if self.lw_passes.currentItem() is None or not getattr(
            self.core.appPlugin, "canDeleteRenderPasses", True
        ):
            return

        rcmenu = QMenu()

        delAct = QAction("Delete", self)
        delAct.triggered.connect(self.deleteAOVs)
        rcmenu.addAction(delAct)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def deleteAOVs(self):
        items = self.lw_passes.selectedItems()
        for i in items:
            self.core.appPlugin.removeAOV(i.text())
        self.updateUi()

    @err_catcher(name=__name__)
    def rjToggled(self, checked):
        self.f_localOutput.setEnabled(
            self.gb_submit.isHidden()
            or not checked
            or (
                checked
                and self.core.rfManagers[self.cb_manager.currentText()].canOutputLocal
            )
        )

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def managerChanged(self, text=None):
        self.f_localOutput.setEnabled(
            self.gb_submit.isHidden()
            or not self.gb_submit.isChecked()
            or (
                self.gb_submit.isChecked()
                and self.core.rfManagers[self.cb_manager.currentText()].canOutputLocal
            )
        )

        if self.cb_manager.currentText() in self.core.rfManagers:
            self.core.rfManagers[
                self.cb_manager.currentText()
            ].sm_render_managerChanged(self)

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def preExecuteState(self):
        warnings = []

        self.updateUi()

        if self.l_taskName.text() == "":
            warnings.append(["No taskname is given.", "", 3])

        if self.curCam is None or (
            self.curCam != "Current View"
            and not self.core.appPlugin.isNodeValid(self, self.curCam)
        ):
            warnings.append(["No camera is selected.", "", 3])
        elif self.curCam == "Current View":
            warnings.append(["No camera is selected.", "", 2])

        rangeType = self.cb_rangeType.currentText()
        frames = self.getFrameRange(rangeType)
        if rangeType != "Expression":
            frames = frames[0]

        if frames is None or frames == []:
            warnings.append(["Framerange is invalid.", "", 3])

        if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
            warnings += self.core.rfManagers[
                self.cb_manager.currentText()
            ].sm_render_preExecute(self)

        warnings += self.core.appPlugin.sm_render_preExecute(self)

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def getOutputName(self, useVersion="next"):
        if self.l_taskName.text() == "":
            return

        task = self.l_taskName.text()
        extension = self.cb_format.currentText()
        fileName = self.core.getCurrentFileName()
        fnameData = self.core.getScenefileData(fileName)
        framePadding = "." if self.cb_rangeType.currentText() != "Single Frame" else ""

        location = "global"
        if (
            self.core.useLocalFiles
            and self.chb_localOutput.isChecked() and (
                self.gb_submit.isHidden()
                or not self.gb_submit.isChecked()
                or (
                    self.gb_submit.isChecked()
                    and self.core.rfManagers[
                        self.cb_manager.currentText()
                    ].canOutputLocal
                )
            )
        ):
            location = "local"

        if fnameData["entity"] == "asset":
            assetPath = self.core.getEntityBasePath(fileName)
            entityName = self.core.entities.getAssetRelPathFromPath(assetPath)
        else:
            entityName = fnameData["entityName"]

        outputPath = self.core.mediaProducts.generateMediaProductPath(
            entity=fnameData["entity"],
            entityName=entityName,
            task=task,
            extension=extension,
            framePadding=framePadding,
            comment=fnameData["comment"],
            version=useVersion if useVersion != "next" else None,
            location=location
        )

        outputFolder = os.path.dirname(outputPath)
        hVersion = self.core.mediaProducts.getVersionFromFilepath(outputPath)

        return outputPath, outputFolder, hVersion

    @err_catcher(name=__name__)
    def executeState(self, parent, useVersion="next"):
        rangeType = self.cb_rangeType.currentText()
        frames = self.getFrameRange(rangeType)
        if rangeType != "Expression":
            startFrame = frames[0]
            endFrame = frames[1]
        else:
            startFrame = None
            endFrame = None

        if frames is None or frames == [] or frames[0] is None:
            return [self.state.text(0) + ": error - Framerange is invalid"]

        if rangeType == "Single Frame":
            endFrame = startFrame

        fileName = self.core.getCurrentFileName()
        if not self.renderingStarted:
            if self.l_taskName.text() == "":
                return [
                    self.state.text(0)
                    + ": error - no taskname is given. Skipped the activation of this state."
                ]

            if self.curCam is None or (
                self.curCam != "Current View"
                and not self.core.appPlugin.isNodeValid(self, self.curCam)
            ):
                return [
                    self.state.text(0)
                    + ": error - no camera is selected. Skipping activation of this state."
                ]

            if self.chb_override.isChecked():
                self.core.appPlugin.sm_render_setVraySettings(self)

            outputName, outputPath, hVersion = self.getOutputName(useVersion=useVersion)

            outLength = len(outputName)
            if platform.system() == "Windows" and outLength > 255:
                return [
                    self.state.text(0)
                    + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, taskname or projectpath."
                    % outLength
                ]

            if not os.path.exists(os.path.dirname(outputPath)):
                os.makedirs(os.path.dirname(outputPath))

            self.core.saveVersionInfo(
                location=os.path.dirname(outputPath), version=hVersion, origin=fileName
            )

            self.l_pathLast.setText(outputName)
            self.l_pathLast.setToolTip(outputName)
            self.b_openLast.setEnabled(True)
            self.b_copyLast.setEnabled(True)

            self.stateManager.saveStatesToScene()

            rSettings = {
                "outputName": outputName,
                "startFrame": startFrame,
                "endFrame": endFrame,
                "frames": frames,
                "rangeType": rangeType,
            }

            if (
                self.chb_renderPreset.isChecked()
                and "RenderSettings" in self.stateManager.stateTypes
            ):
                rSettings["renderSettings"] = getattr(
                    self.core.appPlugin,
                    "sm_renderSettings_getCurrentSettings",
                    lambda x: {},
                )(self)
                self.stateManager.stateTypes["RenderSettings"].applyPreset(
                    self.core, self.renderPresets[self.cb_renderPreset.currentText()]
                )

            self.core.appPlugin.sm_render_preSubmit(self, rSettings)

            kwargs = {
                "state": self,
                "scenefile": fileName,
                "settings": rSettings,
            }

            self.core.callback("preRender", **kwargs)

            if not os.path.exists(os.path.dirname(rSettings["outputName"])):
                os.makedirs(os.path.dirname(rSettings["outputName"]))

            self.core.saveScene(versionUp=False, prismReq=False)

            if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
                result = self.core.rfManagers[
                    self.cb_manager.currentText()
                ].sm_render_submitJob(self, rSettings["outputName"], parent)
            else:
                result = self.core.appPlugin.sm_render_startLocalRender(
                    self, rSettings["outputName"], rSettings
                )
        else:
            rSettings = self.LastRSettings
            result = self.core.appPlugin.sm_render_startLocalRender(
                self, rSettings["outputName"], rSettings
            )
            outputName = rSettings["outputName"]

        if not self.renderingStarted:
            self.core.appPlugin.sm_render_undoRenderSettings(self, rSettings)

        if result == "publish paused":
            return [self.state.text(0) + " - publish paused"]
        else:
            kwargs = {
                "state": self,
                "scenefile": fileName,
                "settings": rSettings,
            }

            self.core.callback("postRender", **kwargs)

            if "Result=Success" in result:
                return [self.state.text(0) + " - success"]
            else:
                erStr = "%s ERROR - sm_default_imageRenderPublish %s:\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    self.core.version,
                    result,
                )
                if not result.startswith("Execute Canceled: "):
                    if result == "unknown error (files do not exist)":
                        QMessageBox.warning(
                            self.core.messageParent,
                            "Warning",
                            "No files were created during the rendering. If you think this is a Prism bug please report it in the forum:\nwww.prism-pipeline.com/forum/\nor write a mail to contact@prism-pipeline.com",
                        )
                    else:
                        self.core.writeErrorLog(erStr)
                return [self.state.text(0) + " - error - " + result]

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
        stateProps = {
            "statename": self.e_name.text(),
            "taskname": self.l_taskName.text(),
            "renderpresetoverride": str(self.chb_renderPreset.isChecked()),
            "currentrenderpreset": self.cb_renderPreset.currentText(),
            "rangeType": str(self.cb_rangeType.currentText()),
            "startframe": self.sp_rangeStart.value(),
            "endframe": self.sp_rangeEnd.value(),
            "frameExpression": self.le_frameExpression.text(),
            "currentcam": str(self.curCam),
            "resoverride": str(
                [
                    self.chb_resOverride.isChecked(),
                    self.sp_resWidth.value(),
                    self.sp_resHeight.value(),
                ]
            ),
            "localoutput": str(self.chb_localOutput.isChecked()),
            "renderlayer": str(self.cb_renderLayer.currentText()),
            "outputFormat": str(self.cb_format.currentText()),
            "vrayoverride": str(self.chb_override.isChecked()),
            "vrayminsubdivs": self.sp_minSubdivs.value(),
            "vraymaxsubdivs": self.sp_maxSubdivs.value(),
            "vraycthreshold": self.sp_cThres.value(),
            "vraynthreshold": self.sp_nThres.value(),
            "submitrender": str(self.gb_submit.isChecked()),
            "rjmanager": str(self.cb_manager.currentText()),
            "rjprio": self.sp_rjPrio.value(),
            "rjframespertask": self.sp_rjFramesPerTask.value(),
            "rjtimeout": self.sp_rjTimeout.value(),
            "rjsuspended": str(self.chb_rjSuspended.isChecked()),
            "osdependencies": str(self.chb_osDependencies.isChecked()),
            "osupload": str(self.chb_osUpload.isChecked()),
            "ospassets": str(self.chb_osPAssets.isChecked()),
            "osslaves": self.e_osSlaves.text(),
            "curdlgroup": self.cb_dlGroup.currentText(),
            "dlconcurrent": self.sp_dlConcurrentTasks.value(),
            "dlgpupt": self.sp_dlGPUpt.value(),
            "dlgpudevices": self.le_dlGPUdevices.text(),
            "lastexportpath": self.l_pathLast.text().replace("\\", "/"),
            "enablepasses": str(self.gb_passes.isChecked()),
            "stateenabled": str(self.state.checkState(0)),
        }
        return stateProps
