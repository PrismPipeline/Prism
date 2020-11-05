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


try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1

import os
import sys
import time
import traceback
import platform

import hou

from PrismUtils.Decorators import err_catcher as err_catcher


class ImageRenderClass(object):
    className = "ImageRender"
    listType = "Export"

    @err_catcher(name=__name__)
    def setup(
        self, state, core, stateManager, node=None, stateData=None, renderer="Mantra"
    ):
        self.state = state
        self.core = core
        self.stateManager = stateManager

        self.curCam = None
        self.e_name.setText(state.text(0))

        self.renderPresets = (
            self.stateManager.stateTypes["RenderSettings"].getPresets(self.core)
            if "RenderSettings" in self.stateManager.stateTypes
            else {}
        )
        if self.renderPresets:
            self.cb_renderPreset.addItems(self.renderPresets.keys())
        else:
            self.w_renderPreset.setVisible(False)

        self.camlist = []

        self.renderers = [
            x for x in self.core.appPlugin.getRendererPlugins() if x.isActive()
        ]
        self.cb_renderer.addItems([x.label for x in self.renderers])

        dftResPresets = [
            "Cam resolution",
            "3840x2160",
            "1920x1080",
            "1280x720",
            "960x540",
            "640x360",
        ]

        self.resolutionPresets = self.core.getConfig("globals", "resolutionPresets", configPath=self.core.prismIni, dft=dftResPresets)

        if "Cam resolution" not in self.resolutionPresets:
            self.resolutionPresets.insert(0, "Cam resolution")

        self.outputFormats = [
            ".exr",
            ".png",
            ".jpg",
        ]

        self.cb_format.addItems(self.outputFormats)

        self.rangeTypes = ["State Manager", "Scene", "Shot", "Node", "Single Frame", "Custom", "Expression"]
        self.cb_rangeType.addItems(self.rangeTypes)
        for idx, rtype in enumerate(self.rangeTypes):
            self.cb_rangeType.setItemData(idx, self.stateManager.getFrameRangeTypeToolTip(rtype), Qt.ToolTipRole)
        self.w_frameExpression.setToolTip(self.stateManager.getFrameRangeTypeToolTip("ExpressionField"))

        self.l_name.setVisible(False)
        self.e_name.setVisible(False)
        self.tw_passes.setColumnWidth(0, 130)
        self.setPassDataEnabled = True
        self.gb_submit.setChecked(False)

        for i in self.core.rfManagers.values():
            self.cb_manager.addItem(i.pluginName)
            i.sm_houExport_startup(self)

        if self.cb_manager.count() == 0:
            self.gb_submit.setVisible(False)

        self.node = None

        if node is None:
            if stateData is None:
                if not self.connectNode():
                    idx = self.cb_renderer.findText(renderer)
                    if idx != -1:
                        self.cb_renderer.setCurrentIndex(idx)
        else:
            self.node = node
            ropType = node.type().name()
            for i in self.renderers:
                if ropType in i.ropNames:
                    self.cb_renderer.setCurrentIndex(self.cb_renderer.findText(i.label))

        self.rendererChanged(self.cb_renderer.currentText(), create=stateData is None)

        if hasattr(self, "node") and self.node is not None:
            self.sp_rangeStart.setValue(self.node.parm("f1").eval())
            self.sp_rangeEnd.setValue(self.node.parm("f2").eval())

        self.core.appPlugin.fixStyleSheet(self.gb_submit)

        self.connectEvents()

        self.managerChanged(True)

        self.b_changeTask.setStyleSheet(
            "QPushButton { background-color: rgb(150,0,0); border: none;}"
        )
        self.f_localOutput.setVisible(self.core.useLocalFiles)
        self.e_osSlaves.setText("All")

        if stateData is not None:
            self.loadData(stateData)
        else:
            if node is None:
                self.nameChanged(state.text(0))

            fileName = self.core.getCurrentFileName()
            fnameData = self.core.getScenefileData(fileName)
            if fnameData.get("category"):
                self.l_taskName.setText(fnameData.get("category"))
                self.b_changeTask.setStyleSheet("")

            self.updateUi()

    @err_catcher(name=__name__)
    def loadData(self, data):
        if "connectednode" in data:
            self.node = hou.node(data["connectednode"])
            if self.node is None:
                self.node = self.findNode(data["connectednode"])
            if self.node is not None:
                ropType = self.node.type().name()
                for i in self.renderers:
                    if ropType in i.ropNames:
                        self.cb_renderer.setCurrentIndex(
                            self.cb_renderer.findText(i.label)
                        )
            if self.node and self.node.type().name() == "merge":
                self.node = None
        if "connectednode2" in data:
            self.node2 = hou.node(data["connectednode2"])
            if self.node2 is None:
                self.node2 = self.findNode(data["connectednode2"])

        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "taskname" in data:
            self.l_taskName.setText(data["taskname"])
            if data["taskname"] != "":
                self.b_changeTask.setStyleSheet("")
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
        if "camoverride" in data:
            res = eval(data["camoverride"])
            self.chb_camOverride.setChecked(res)
            if not res and self.node is not None:
                self.curCam = self.curRenderer.getCam(self.node)
        if "currentcam" in data:
            idx = self.cb_cams.findText(data["currentcam"])
            if idx != -1:
                if self.chb_camOverride.isChecked():
                    self.curCam = self.camlist[idx]
                self.cb_cams.setCurrentIndex(idx)
                self.stateManager.saveStatesToScene()
        if "resoverride" in data:
            res = eval(data["resoverride"])
            self.chb_resOverride.setChecked(res[0])
            self.sp_resWidth.setValue(res[1])
            self.sp_resHeight.setValue(res[2])
        if "usetake" in data:
            self.chb_useTake.setChecked(eval(data["usetake"]))
        if "take" in data:
            idx = self.cb_take.findText(data["take"])
            if idx != -1:
                self.cb_take.setCurrentIndex(idx)
        if "localoutput" in data:
            self.chb_localOutput.setChecked(eval(data["localoutput"]))
        if "outputFormat" in data:
            idx = self.cb_format.findText(data["outputFormat"])
            if idx != -1:
                self.cb_format.setCurrentIndex(idx)
        if "renderer" in data:
            idx = self.cb_renderer.findText(data["renderer"])
            if idx != -1:
                self.cb_renderer.setCurrentIndex(idx)
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
        if "rjRenderNSIs" in data:
            self.chb_rjNSIs.setChecked(eval(data["rjRenderNSIs"]))
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

        self.nameChanged(self.e_name.text())

    @err_catcher(name=__name__)
    def findNode(self, path):
        for node in hou.node("/").allSubChildren():
            if (
                node.userData("PrismPath") is not None
                and node.userData("PrismPath") == path
            ):
                node.setUserData("PrismPath", node.path())
                return node

        return None

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
        self.chb_camOverride.stateChanged.connect(self.camOverrideChanged)
        self.cb_cams.activated.connect(self.setCam)
        self.chb_resOverride.stateChanged.connect(self.resOverrideChanged)
        self.sp_resWidth.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.sp_resHeight.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.b_resPresets.clicked.connect(self.showResPresets)
        self.chb_useTake.stateChanged.connect(self.useTakeChanged)
        self.cb_take.activated.connect(self.stateManager.saveStatesToScene)
        self.chb_localOutput.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.cb_format.activated.connect(self.stateManager.saveStatesToScene)
        self.cb_renderer.currentIndexChanged[str].connect(self.rendererChanged)
        self.gb_submit.toggled.connect(self.rjToggled)
        self.cb_manager.activated.connect(self.managerChanged)
        self.sp_rjPrio.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.sp_rjFramesPerTask.editingFinished.connect(
            self.stateManager.saveStatesToScene
        )
        self.sp_rjTimeout.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.chb_rjSuspended.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_rjNSIs.stateChanged.connect(self.stateManager.saveStatesToScene)
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
        self.tw_passes.itemChanged.connect(self.setPassData)
        self.tw_passes.customContextMenuRequested.connect(self.rclickPasses)
        self.tw_passes.mouseDbcEvent = self.tw_passes.mouseDoubleClickEvent
        self.tw_passes.mouseDoubleClickEvent = self.passesDbClick

        self.b_addPasses.clicked.connect(self.showPasses)
        self.b_openLast.clicked.connect(
            lambda: self.core.openFolder(os.path.dirname(self.l_pathLast.text()))
        )
        self.b_copyLast.clicked.connect(
            lambda: self.core.copyToClipboard(self.l_pathLast.text())
        )

        if not self.stateManager.standalone:
            self.b_goTo.clicked.connect(self.goToNode)
            self.b_connect.clicked.connect(self.connectNode)

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
        self.expressionWin.resize(1,1)

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
    def useTakeChanged(self, state):
        self.cb_take.setEnabled(state)
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def setCam(self, index):
        self.curCam = self.camlist[index]
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def rendererChanged(self, renderer, create=True):
        self.curRenderer = [x for x in self.renderers if x.label == renderer][0]
        if not self.stateManager.standalone and (
            self.node is None
            or self.node.type().name() not in self.curRenderer.ropNames
        ):
            self.deleteNode()
            if create:
                self.curRenderer.createROP(self)
                self.node.moveToGoodPosition()

        self.refreshPasses()

        self.nameChanged(self.e_name.text())
        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def deleteNode(self):
        try:
            self.node.name()
        except:
            return

        msg = QMessageBox(
            QMessageBox.Question,
            "Renderer changed",
            (
                "Do you want to delete the current render node?\n\n%s"
                % (self.node.path())
            ),
            QMessageBox.No,
        )
        msg.addButton("Yes", QMessageBox.YesRole)
        msg.setParent(self.core.messageParent, Qt.Window)
        action = msg.exec_()

        if action == 0:
            try:
                self.node.destroy()
                if hasattr(self, "node2"):
                    self.node2.destroy()
            except:
                pass

    @err_catcher(name=__name__)
    def nameChanged(self, text):
        try:
            sText = text + " - %s (%s)" % (self.l_taskName.text(), self.node)
        except:
            sText = text + " - %s (None)" % self.l_taskName.text()

        if self.state.text(0).endswith(" - disabled"):
            sText += " - disabled"

        self.state.setText(0, sText)

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
        result = self.nameWin.exec_()

        if result == 1:
            self.l_taskName.setText(self.nameWin.e_item.text())
            self.nameChanged(self.e_name.text())

            self.b_changeTask.setStyleSheet("")

            self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def presetOverrideChanged(self, checked):
        self.cb_renderPreset.setEnabled(checked)
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def camOverrideChanged(self, checked):
        self.cb_cams.setEnabled(checked)
        self.updateCams()

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

        for i in self.resolutionPresets:
            pAct = QAction(i, self)
            if i == "Cam resolution":
                pAct.triggered.connect(lambda: self.setCamResolution())
            else:
                try:
                    pwidth = int(i.split("x")[0])
                    pheight = int(i.split("x")[1])
                except ValueError:
                    continue

                pAct.triggered.connect(
                    lambda x=None, v=pwidth: self.sp_resWidth.setValue(v)
                )
                pAct.triggered.connect(
                    lambda x=None, v=pheight: self.sp_resHeight.setValue(v)
                )
                pAct.triggered.connect(lambda: self.stateManager.saveStatesToScene())

            pmenu.addAction(pAct)

        pmenu.setStyleSheet(self.stateManager.parent().styleSheet())
        pmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def setCamResolution(self):
        pbCam = None

        if self.node:
            camParm = self.node.parm("camera")
            if camParm:
                cam = camParm.evalAsNode()

        if cam is None:
            QMessageBox.warning(
                self, "Resolution Override", "No camera is selected or active."
            )
            return

        self.sp_resWidth.setValue(cam.parm("resx").eval())
        self.sp_resHeight.setValue(cam.parm("resy").eval())

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def updateUi(self):
        try:
            self.node.name()
            self.l_status.setText(self.node.name())
            self.l_status.setStyleSheet("QLabel { background-color : rgb(0,150,0); }")
        except:
            self.node = None
            self.l_status.setText("Not connected")
            self.l_status.setStyleSheet("QLabel { background-color : rgb(150,0,0); }")

        curTake = self.cb_take.currentText()
        self.cb_take.clear()
        self.cb_take.addItems([x.name() for x in hou.takes.takes()])
        idx = self.cb_take.findText(curTake)
        if idx != -1:
            self.cb_take.setCurrentIndex(idx)

        self.updateRange()
        self.refreshPasses()

        if self.cb_manager.currentText() in self.core.rfManagers:
            self.core.rfManagers[self.cb_manager.currentText()].sm_houRender_updateUI(
                self
            )

        # update Cams
        self.updateCams()
        self.nameChanged(self.e_name.text())

        return True

    @err_catcher(name=__name__)
    def updateCams(self):
        if self.chb_camOverride.isChecked():
            self.cb_cams.clear()
            self.camlist = []

            for node in hou.node("/").allSubChildren():

                if (
                    node.type().name() == "cam" and node.name() != "ipr_camera"
                ) or node.type().name() == "vrcam":
                    self.camlist.append(node)

            self.cb_cams.addItems([i.name() for i in self.camlist])

            try:
                x = self.curCam.name()
            except:
                self.curCam = None

            if self.curCam is not None and self.curCam in self.camlist:
                self.cb_cams.setCurrentIndex(self.camlist.index(self.curCam))
            else:
                self.cb_cams.setCurrentIndex(0)
                if len(self.camlist) > 0:
                    self.curCam = self.camlist[0]
                else:
                    self.curCam = None
                self.stateManager.saveStatesToScene()
        elif self.node is not None:
            self.curCam = self.curRenderer.getCam(self.node)

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
        elif rangeType == "Shot":
            fileName = self.core.getCurrentFileName()
            fnameData = self.core.getScenefileData(fileName)
            if fnameData["entity"] == "shot":
                frange = self.core.entities.getShotRange(fnameData["entityName"])
                if frange:
                    startFrame, endFrame = frange
        elif rangeType == "Node" and self.node:
            startFrame = self.node.parm("f1").eval()
            endFrame = self.node.parm("f2").eval()
        elif rangeType == "Single Frame":
            startFrame = self.core.appPlugin.getCurrentFrame()
        elif rangeType == "Custom":
            startFrame = self.sp_rangeStart.value()
            endFrame = self.sp_rangeEnd.value()
        elif rangeType == "Expression":
            return self.core.resolveFrameExpression(self.le_frameExpression.text())

        return startFrame, endFrame

    @err_catcher(name=__name__)
    def goToNode(self):
        try:
            self.node.name()
        except:
            self.stateManager.showState()
            return False

        self.node.setCurrent(True, clear_all_selected=True)

        paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        if paneTab is not None:
            paneTab.setCurrentNode(self.node)
            paneTab.homeToSelection()

    @err_catcher(name=__name__)
    def connectNode(self):
        if len(hou.selectedNodes()) == 0:
            return False

        ropType = hou.selectedNodes()[0].type().name()
        for i in self.renderers:
            if ropType in i.ropNames:
                self.node = hou.selectedNodes()[0]
                self.cb_renderer.setCurrentIndex(self.cb_renderer.findText(i.label))
                self.rendererChanged(self.cb_renderer.currentText())
                return True

        return False

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
        rfm = self.cb_manager.currentText()
        self.f_localOutput.setEnabled(
            self.gb_submit.isHidden()
            or not self.gb_submit.isChecked()
            or (
                self.gb_submit.isChecked()
                and self.core.rfManagers[rfm].canOutputLocal
            )
        )

        if rfm in self.core.rfManagers:
            self.core.rfManagers[rfm].sm_houRender_managerChanged(self)

        is3dl = self.node and (self.node.type().name() == "3Delight")
        self.w_renderNSIs.setVisible(bool(is3dl and (rfm == "Deadline")))

        self.stateManager.saveStatesToScene()

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
    def setPassData(self, item):
        if not self.setPassDataEnabled:
            return

        passNum = str(int(self.tw_passes.item(item.row(), 2).text()) + 1)
        self.curRenderer.setAOVData(self, self.node, passNum, item)

    @err_catcher(name=__name__)
    def showPasses(self):
        steps = None
        if self.node is not None:
            steps = self.curRenderer.getDefaultPasses(self)

        if not steps:
            return False

        try:
            del sys.modules["ItemList"]
        except:
            pass

        import ItemList

        self.il = ItemList.ItemList(core=self.core)
        self.il.setWindowTitle("Select Passes")
        self.core.parentWindow(self.il)
        self.il.tw_steps.doubleClicked.connect(self.il.accept)
        self.il.b_addStep.setVisible(False)
        if self.curRenderer.label == "Mantra":
            self.il.tw_steps.horizontalHeaderItem(0).setText("Name")
            self.il.tw_steps.horizontalHeaderItem(1).setText("VEX Variable")
        else:
            self.il.tw_steps.horizontalHeaderItem(0).setText("Type")
            self.il.tw_steps.horizontalHeaderItem(1).setText("Name")

        if len(steps[0]) == 1:
            self.il.tw_steps.setColumnHidden(1, True)

        for i in steps:
            rc = self.il.tw_steps.rowCount()
            self.il.tw_steps.insertRow(rc)
            item1 = QTableWidgetItem(i[0])
            self.il.tw_steps.setItem(rc, 0, item1)
            if len(steps[0]) > 1:
                item2 = QTableWidgetItem(i[1])
                self.il.tw_steps.setItem(rc, 1, item2)

        self.il.tw_steps.resizeColumnsToContents()

        result = self.il.exec_()

        if result != 1:
            return False

        for i in self.il.tw_steps.selectedItems():
            if i.column() == 0:
                self.curRenderer.addAOV(self, steps[i.row()])

        self.updateUi()

    @err_catcher(name=__name__)
    def refreshPasses(self):
        try:
            self.node.name()
        except:
            return

        self.setPassDataEnabled = False

        self.e_name.setText(self.e_name.text())
        self.tw_passes.setRowCount(0)
        self.tw_passes.setColumnCount(3)
        self.tw_passes.setColumnHidden(2, True)
        self.tw_passes.setStyleSheet("")
        self.curRenderer.refreshAOVs(self)

        self.setPassDataEnabled = True

    @err_catcher(name=__name__)
    def rclickPasses(self, pos):
        if self.tw_passes.selectedIndexes() == []:
            return

        rcmenu = QMenu()

        delAct = QAction("Delete", self)
        delAct.triggered.connect(self.removeAOVs)
        rcmenu.addAction(delAct)

        rcmenu.setStyleSheet(self.stateManager.parent().styleSheet())
        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def removeAOVs(self):
        rows = [x for x in self.tw_passes.selectedIndexes() if x.column() == 0]
        for p in sorted(rows, reverse=True):
            self.curRenderer.deleteAOV(self, p.row())
        self.updateUi()

    @err_catcher(name=__name__)
    def passesDbClick(self, event):
        self.curRenderer.aovDbClick(self, event)

    @err_catcher(name=__name__)
    def preDelete(self, item, silent=False):
        self.core.appPlugin.sm_preDelete(self, item, silent)

    @err_catcher(name=__name__)
    def preExecuteState(self):
        self.updateCams()

        warnings = []

        if self.l_taskName.text() == "":
            warnings.append(["No taskname is given.", "", 3])

        if self.curCam is None:
            warnings.append(["No camera is selected", "", 3])

        rangeType = self.cb_rangeType.currentText()
        frames = self.getFrameRange(rangeType)
        if rangeType != "Expression":
            frames = frames[0]

        if frames is None or frames == []:
            warnings.append(["Framerange is invalid.", "", 3])

        try:
            self.node.name()
        except:
            warnings.append(["Node is invalid.", "", 3])

        if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
            warnings += self.core.rfManagers[
                self.cb_manager.currentText()
            ].sm_houRender_preExecute(self)

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def getOutputName(self, useVersion="next"):
        if self.l_taskName.text() == "":
            return

        fileName = self.core.getCurrentFileName()

        if self.core.useLocalFiles:
            if self.chb_localOutput.isChecked() and (
                self.gb_submit.isHidden()
                or not self.gb_submit.isChecked()
                or (
                    self.gb_submit.isChecked()
                    and self.core.rfManagers[
                        self.cb_manager.currentText()
                    ].canOutputLocal
                )
            ):
                fileName = self.core.convertPath(fileName, target="local")
            else:
                fileName = self.core.convertPath(fileName, target="global")

        hVersion = ""
        if useVersion != "next":
            hVersion = useVersion.split(self.core.filenameSeparator)[0]
            pComment = useVersion.split(self.core.filenameSeparator)[1]

        fnameData = self.core.getScenefileData(fileName)
        framePadding = ".$F4" if self.cb_rangeType.currentText() != "Single Frame" else ""
        if fnameData["entity"] == "shot":
            outputPath = os.path.join(
                self.core.getEntityBasePath(fileName),
                "Rendering",
                "3dRender",
                self.l_taskName.text(),
            )
            if hVersion == "":
                hVersion = self.core.getHighestTaskVersion(outputPath)
                pComment = fnameData["comment"]

            outputPath = os.path.join(
                outputPath, hVersion + self.core.filenameSeparator + pComment, "beauty"
            )
            outputFile = os.path.join(
                "shot"
                + self.core.filenameSeparator
                + fnameData["entityName"]
                + self.core.filenameSeparator
                + self.l_taskName.text()
                + self.core.filenameSeparator
                + hVersion
                + self.core.filenameSeparator
                + "beauty"
                + framePadding
                + self.cb_format.currentText()
            )
        elif fnameData["entity"] == "asset":
            outputPath = os.path.join(
                self.core.getEntityBasePath(fileName),
                "Rendering",
                "3dRender",
                self.l_taskName.text(),
            )
            if hVersion == "":
                hVersion = self.core.getHighestTaskVersion(outputPath)
                pComment = fnameData["comment"]

            outputPath = os.path.join(
                outputPath, hVersion + self.core.filenameSeparator + pComment, "beauty"
            )
            outputFile = os.path.join(
                fnameData["entityName"]
                + self.core.filenameSeparator
                + self.l_taskName.text()
                + self.core.filenameSeparator
                + hVersion
                + self.core.filenameSeparator
                + "beauty"
                + framePadding
                + self.cb_format.currentText()
            )
        else:
            return

        outputName = os.path.join(outputPath, outputFile)

        return outputName.replace("\\", "/"), outputPath.replace("\\", "/"), hVersion

    @err_catcher(name=__name__)
    def executeState(self, parent, useVersion="next"):
        if self.l_taskName.text() == "":
            return [
                self.state.text(0)
                + ": error - No taskname is given. Skipped the activation of this state."
            ]

        if self.curCam is None:
            return [
                self.state.text(0)
                + ": error - No camera is selected. Skipped the activation of this state."
            ]

        try:
            self.curCam.name()
        except:
            return [
                self.state.text(0)
                + ": error - The selected camera is invalid. Skipped the activation of this state."
            ]

        try:
            self.node.name()
        except:
            return [self.state.text(0) + ": error - Node is invalid."]

        if not self.curRenderer.setCam(self, self.node, self.curCam.path()):
            return [self.state.text(0) + ": error - Publish canceled"]

        fileName = self.core.getCurrentFileName()

        outputName, outputPath, hVersion = self.getOutputName(useVersion=useVersion)

        outLength = len(outputName)
        if platform.system() == "Windows" and outLength > 255:
            return [
                self.state.text(0)
                + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, taskname or projectpath."
                % outLength
            ]

        if not os.path.exists(outputPath):
            os.makedirs(outputPath)

        self.core.saveVersionInfo(
            location=os.path.dirname(outputPath), version=hVersion, origin=fileName
        )

        rSettings = {"outputName": outputName}

        if (
            self.chb_renderPreset.isChecked()
            and "RenderSettings" in self.stateManager.stateTypes
        ):
            rSettings["renderSettings"] = getattr(
                self.core.appPlugin,
                "sm_renderSettings_getCurrentSettings",
                lambda x: {},
            )(self, node=self.node)
            self.stateManager.stateTypes["RenderSettings"].applyPreset(
                self.core,
                self.renderPresets[self.cb_renderPreset.currentText()],
                node=self.node,
            )

        result = self.curRenderer.executeAOVs(self, outputName)
        if result is not True:
            return result

        self.l_pathLast.setText(outputName)
        self.l_pathLast.setToolTip(outputName)
        self.b_openLast.setEnabled(True)
        self.b_copyLast.setEnabled(True)
        self.stateManager.saveStatesToScene()

        if self.chb_resOverride.isChecked():
            result = self.curRenderer.setResolution(self)
            if not result:
                return result

        if self.chb_useTake.isChecked():
            pTake = self.cb_take.currentText()
            takeLabels = [x.strip() for x in self.node.parm("take").menuLabels()]
            if pTake in takeLabels:
                idx = takeLabels.index(pTake)
                if idx != -1:
                    token = self.node.parm("take").menuItems()[idx]
                    if not self.core.appPlugin.setNodeParm(
                        self.node, "take", val=token
                    ):
                        return [self.state.text(0) + ": error - Publish canceled"]
            else:
                return [
                    self.state.text(0) + ": error - take '%s' doesn't exist." % pTake
                ]

        hou.hipFile.save()

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

        rSettings["startFrame"] = startFrame
        rSettings["endFrame"] = endFrame
        rSettings["frames"] = frames

        kwargs = {
            "state": self,
            "scenefile": fileName,
            "settings": rSettings,
        }
        self.core.callback("preRender", **kwargs)

        if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
            result = self.core.rfManagers[
                self.cb_manager.currentText()
            ].sm_render_submitJob(self, outputName, parent)
        else:
            if not self.core.appPlugin.setNodeParm(self.node, "trange", val=1):
                return [self.state.text(0) + ": error - Publish canceled"]

            if rangeType == "Expression":
                frameChunks = [[x, x] for x in frames]
            else:
                frameChunks = [[startFrame, endFrame]]

            try:
                for frameChunk in frameChunks:
                    if not self.core.appPlugin.setNodeParm(self.node, "f1", clear=True):
                        return [self.state.text(0) + ": error - Publish canceled"]
                    if not self.core.appPlugin.setNodeParm(self.node, "f2", clear=True):
                        return [self.state.text(0) + ": error - Publish canceled"]

                    if not self.core.appPlugin.setNodeParm(self.node, "f1", val=frameChunk[0]):
                        return [self.state.text(0) + ": error - Publish canceled"]

                    if not self.core.appPlugin.setNodeParm(self.node, "f2", val=frameChunk[1]):
                        return [self.state.text(0) + ": error - Publish canceled"]

                    result = self.curRenderer.executeRender(self)
                    if not result:
                        return result

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "%s ERROR - houImageRender %s:\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    self.core.version,
                    traceback.format_exc(),
                )
                self.core.writeErrorLog(erStr)
                return [
                    self.state.text(0)
                    + " - unknown error (view console for more information)"
                ]

        postResult = self.curRenderer.postExecute(self)
        if not postResult:
            return postResult

        self.undoRenderSettings(rSettings)

        kwargs = {
            "state": self,
            "scenefile": fileName,
            "settings": rSettings,
        }
        self.core.callback("postRender", **kwargs)

        if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
            if result and "Result=Success" in result:
                return [self.state.text(0) + " - success"]
            else:
                erStr = "%s ERROR - houImageRenderPublish %s:\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    self.core.version,
                    result,
                )
                if not result.startswith("Execute Canceled"):
                    self.core.writeErrorLog(erStr)
                return [self.state.text(0) + " - error - " + result]
        else:
            if len(os.listdir(outputPath)) > 0:
                return [self.state.text(0) + " - success"]
            else:
                result = self.state.text(0) + " - unknown error (files do not exist)"
                errs = self.node.errors()
                if len(errs) > 0:
                    result += "\n\n\nNode errors:\n" + "\n" + "\n\n".join(errs)

                return [result]

    @err_catcher(name=__name__)
    def undoRenderSettings(self, rSettings):
        if "renderSettings" in rSettings:
            self.core.appPlugin.sm_renderSettings_setCurrentSettings(
                self,
                self.core.readYaml(data=rSettings["renderSettings"]),
                node=self.node,
            )

    @err_catcher(name=__name__)
    def getStateProps(self):
        try:
            curNode = self.node.path()
            self.node.setUserData("PrismPath", curNode)
        except:
            curNode = None

        try:
            curNode2 = self.node2.path()
            self.node2.setUserData("PrismPath", curNode2)
        except:
            curNode2 = None

        stateProps = {
            "statename": self.e_name.text(),
            "taskname": self.l_taskName.text(),
            "renderpresetoverride": str(self.chb_renderPreset.isChecked()),
            "currentrenderpreset": self.cb_renderPreset.currentText(),
            "rangeType": str(self.cb_rangeType.currentText()),
            "startframe": self.sp_rangeStart.value(),
            "endframe": self.sp_rangeEnd.value(),
            "frameExpression": self.le_frameExpression.text(),
            "camoverride": str(self.chb_camOverride.isChecked()),
            "currentcam": self.cb_cams.currentText(),
            "resoverride": str(
                [
                    self.chb_resOverride.isChecked(),
                    self.sp_resWidth.value(),
                    self.sp_resHeight.value(),
                ]
            ),
            "usetake": str(self.chb_useTake.isChecked()),
            "take": self.cb_take.currentText(),
            "localoutput": str(self.chb_localOutput.isChecked()),
            "outputFormat": self.cb_format.currentText(),
            "connectednode": curNode,
            "connectednode2": curNode2,
            "renderer": str(self.cb_renderer.currentText()),
            "submitrender": str(self.gb_submit.isChecked()),
            "rjmanager": str(self.cb_manager.currentText()),
            "rjprio": self.sp_rjPrio.value(),
            "rjframespertask": self.sp_rjFramesPerTask.value(),
            "rjtimeout": self.sp_rjTimeout.value(),
            "rjsuspended": str(self.chb_rjSuspended.isChecked()),
            "rjRenderNSIs": str(self.chb_rjNSIs.isChecked()),
            "osdependencies": str(self.chb_osDependencies.isChecked()),
            "osupload": str(self.chb_osUpload.isChecked()),
            "ospassets": str(self.chb_osPAssets.isChecked()),
            "osslaves": self.e_osSlaves.text(),
            "curdlgroup": self.cb_dlGroup.currentText(),
            "dlconcurrent": self.sp_dlConcurrentTasks.value(),
            "dlgpupt": self.sp_dlGPUpt.value(),
            "dlgpudevices": self.le_dlGPUdevices.text(),
            "lastexportpath": self.l_pathLast.text().replace("\\", "/"),
            "stateenabled": str(self.state.checkState(0)),
        }
        return stateProps
