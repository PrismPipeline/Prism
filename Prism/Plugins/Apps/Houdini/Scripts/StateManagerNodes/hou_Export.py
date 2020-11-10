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

import hou

from PrismUtils.Decorators import err_catcher as err_catcher


class ExportClass(object):
    className = "Export"
    listType = "Export"

    @err_catcher(name=__name__)
    def setup(self, state, core, stateManager, node=None, stateData=None):
        self.state = state
        self.core = core
        self.stateManager = stateManager

        self.e_name.setText(state.text(0))

        self.node = None
        self.curCam = None
        self.initsim = True

        self.cb_outType.addItems(self.core.appPlugin.outputFormats)
        self.export_paths = self.core.getExportPaths()

        self.cb_outPath.addItems(list(self.export_paths.keys()))
        if len(self.export_paths) < 2:
            self.w_outPath.setVisible(False)

        self.l_name.setVisible(False)
        self.e_name.setVisible(False)
        self.f_cam.setVisible(False)
        self.w_sCamShot.setVisible(False)
        self.w_saveToExistingHDA.setVisible(False)
        self.w_blackboxHDA.setVisible(False)
        self.w_projectHDA.setVisible(False)
        self.w_externalReferences.setVisible(False)
        self.gb_submit.setChecked(False)

        self.nodeTypes = {
            "rop_geometry": {"outputparm": "sopoutput"},
            "rop_alembic": {"outputparm": "filename"},
            "rop_fbx": {"outputparm": "sopoutput"},
            "rop_dop": {"outputparm": "dopoutput"},
            "rop_comp": {"outputparm": "copoutput"},
            "filecache": {"outputparm": "file"},
            "geometry": {"outputparm": "sopoutput"},
            "alembic": {"outputparm": "filename"},
            "pixar::usdrop": {"outputparm": "usdfile"},
            "usd": {"outputparm": "lopoutput"},
            "Redshift_Proxy_Output": {"outputparm": "RS_archive_file"},
        }

        self.rangeTypes = ["State Manager", "Scene", "Shot", "Node", "Single Frame", "Custom"]
        self.cb_rangeType.addItems(self.rangeTypes)
        for idx, rtype in enumerate(self.rangeTypes):
            self.cb_rangeType.setItemData(idx, self.stateManager.getFrameRangeTypeToolTip(rtype), Qt.ToolTipRole)

        for i in self.core.rfManagers.values():
            self.cb_manager.addItem(i.pluginName)
            i.sm_houExport_startup(self)

        if self.cb_manager.count() == 0:
            self.gb_submit.setVisible(False)

        if node is None and not self.stateManager.standalone:
            if stateData is None:
                if not self.connectNode():
                    self.createNode()
        else:
            self.node = node

        if self.node is not None and self.node.parm("f1") is not None:
            self.sp_rangeStart.setValue(self.node.parm("f1").eval())
            self.sp_rangeEnd.setValue(self.node.parm("f2").eval())

            idx = -1
            if self.node.type().name() in ["rop_alembic", "alembic"]:
                idx = self.cb_outType.findText(".abc")
            elif self.node.type().name() in ["rop_fbx"]:
                idx = self.cb_outType.findText(".fbx")
            elif self.node.type().name() in ["pixar::usdrop", "usd"]:
                idx = self.cb_outType.findText(".usd")
            elif self.node.type().name() in ["Redshift_Proxy_Output"]:
                idx = self.cb_outType.findText(".rs")

            if idx != -1:
                self.cb_outType.setCurrentIndex(idx)
                self.typeChanged(self.cb_outType.currentText())
        elif stateData is None:
            self.sp_rangeStart.setValue(hou.playbar.playbackRange()[0])
            self.sp_rangeEnd.setValue(hou.playbar.playbackRange()[1])

        self.nameChanged(state.text(0))
        self.managerChanged(True)

        self.connectEvents()

        self.b_changeTask.setStyleSheet(
            "QPushButton { background-color: rgb(150,0,0); border: none;}"
        )

        self.core.appPlugin.fixStyleSheet(self.gb_submit)

        self.e_osSlaves.setText("All")

        self.updateUi()
        if stateData is not None:
            self.loadData(stateData)
        else:
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
                self.l_taskName.setText(fnameData.get("category"))
                self.b_changeTask.setStyleSheet("")

    @err_catcher(name=__name__)
    def loadData(self, data):
        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "taskname" in data:
            self.l_taskName.setText(data["taskname"])
            if data["taskname"] != "":
                self.b_changeTask.setStyleSheet("")
        if "rangeType" in data:
            idx = self.cb_rangeType.findText(data["rangeType"])
            if idx != -1:
                self.cb_rangeType.setCurrentIndex(idx)
                self.updateRange()
        if "startframe" in data:
            self.sp_rangeStart.setValue(int(data["startframe"]))
        if "endframe" in data:
            self.sp_rangeEnd.setValue(int(data["endframe"]))
        if "connectednode" in data:
            node = hou.node(data["connectednode"])
            if node is None:
                node = self.findNode(data["connectednode"])
            self.connectNode(node)
        if "usetake" in data:
            self.chb_useTake.setChecked(eval(data["usetake"]))
        if "take" in data:
            idx = self.cb_take.findText(data["take"])
            if idx != -1:
                self.cb_take.setCurrentIndex(idx)
        if "curoutputpath" in data:
            idx = self.cb_outPath.findText(data["curoutputpath"])
            if idx != -1:
                self.cb_outPath.setCurrentIndex(idx)
        if "outputtypes" in data:
            self.cb_outType.clear()
            self.cb_outType.addItems(eval(data["outputtypes"]))
        if "curoutputtype" in data:
            idx = self.cb_outType.findText(data["curoutputtype"])
            if idx != -1:
                self.cb_outType.setCurrentIndex(idx)
                self.typeChanged(self.cb_outType.currentText(), createMissing=False)
        if "savetoexistinghda" in data:
            self.chb_saveToExistingHDA.setChecked(eval(data["savetoexistinghda"]))
        if "projecthda" in data:
            self.chb_projectHDA.setChecked(eval(data["projecthda"]))
        if "externalReferences" in data:
            self.chb_externalReferences.setChecked(eval(data["externalReferences"]))
        if "blackboxhda" in data:
            self.chb_blackboxHDA.setChecked(eval(data["blackboxhda"]))
        if "unitconvert" in data:
            self.chb_convertExport.setChecked(eval(data["unitconvert"]))
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
        if "currentcam" in data:
            idx = self.cb_cam.findText(data["currentcam"])
            if idx != -1:
                self.curCam = self.camlist[idx]
                if self.cb_outType.currentText() == "ShotCam":
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
    def isNodeValid(self):
        try:
            validTST = self.node.name()
        except:
            self.node = None

        return self.node is not None

    @err_catcher(name=__name__)
    def createNode(self, nodePath=None):
        if self.stateManager.standalone:
            return False

        parentNode = None
        curContext = ""
        if not self.isNodeValid():
            if len(hou.selectedNodes()) > 0:
                curContext = hou.selectedNodes()[0].type().category().name()
                if len(hou.selectedNodes()[0].outputNames()) > 0:
                    parentNode = hou.selectedNodes()[0]
            else:
                if self.core.uiAvailable:
                    paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
                    if paneTab is None:
                        return

                    curContext = paneTab.pwd().childTypeCategory().name()
                    nodePath = paneTab.pwd()
                elif nodePath is not None:
                    curContext = hou.node(nodePath).type().category().name()
        else:
            curContext = self.node.type().category().name()
            if len(self.node.inputs()) > 0:
                parentNode = self.node.inputs()[0]
            else:
                nodePath = self.node.parent()

            if self.node.type().name() in self.nodeTypes.keys():
                try:
                    self.node.destroy()
                except:
                    pass
            elif self.node.outputConnectors():
                parentNode = self.node
                nodePath = None

            self.node = None

        ropType = ""
        if curContext == "Cop2":
            ropType = "rop_comp"
        elif curContext == "Dop":
            ropType = "rop_dop"
        elif curContext == "Sop":
            ropType = "rop_geometry"
        elif curContext == "Driver":
            ropType = "geometry"

        if self.cb_outType.currentText() == ".abc":
            if curContext == "Sop":
                ropType = "rop_alembic"
            else:
                ropType = "alembic"
        elif self.cb_outType.currentText() == ".fbx":
            ropType = "rop_fbx"
        elif self.cb_outType.currentText() == ".hda":
            ropType = ""
        elif self.cb_outType.currentText() == ".usd":
            ropType = "usd"
        elif self.cb_outType.currentText() == ".rs":
            ropType = "Redshift_Proxy_Output"

        if (
            ropType != ""
            and nodePath is not None
            and not nodePath.isInsideLockedHDA()
            and not nodePath.isLockedHDA()
        ):
            try:
                self.node = nodePath.createNode(ropType)
            except:
                pass
            else:
                paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
                if paneTab is not None:
                    self.node.setPosition(paneTab.visibleBounds().center())
                self.node.moveToGoodPosition()
        elif (
            ropType != ""
            and parentNode is not None
            and not (parentNode.parent().isInsideLockedHDA())
        ):
            try:
                self.node = parentNode.createOutputNode(ropType)
            except:
                pass
            else:
                self.node.moveToGoodPosition()

        if self.isNodeValid():
            self.goToNode()
        self.updateUi()

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
        self.chb_useTake.stateChanged.connect(self.useTakeChanged)
        self.cb_take.activated.connect(self.stateManager.saveStatesToScene)
        self.chb_saveToExistingHDA.stateChanged.connect(
            self.stateManager.saveStatesToScene
        )
        self.chb_saveToExistingHDA.stateChanged.connect(
            lambda x: self.w_outPath.setEnabled(not x)
        )
        self.chb_saveToExistingHDA.stateChanged.connect(
            lambda x: self.w_projectHDA.setEnabled(
                not x or not self.w_saveToExistingHDA.isEnabled()
            )
        )
        self.chb_projectHDA.stateChanged.connect(
            lambda x: self.w_outPath.setEnabled(not x)
        )
        self.chb_projectHDA.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_externalReferences.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_blackboxHDA.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_convertExport.stateChanged.connect(self.stateManager.saveStatesToScene)
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
        self.cb_cam.activated.connect(self.setCam)
        self.cb_sCamShot.activated.connect(self.stateManager.saveStatesToScene)
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
    def nameChanged(self, text):
        if self.cb_outType.currentText() == "ShotCam":
            sText = text + " - Shotcam (%s)" % (self.curCam)
        else:
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
            self.l_taskName.setText(self.nameWin.e_item.text())
            self.nameChanged(self.e_name.text())

            self.b_changeTask.setStyleSheet("")

            self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def setCam(self, index):
        self.curCam = self.camlist[index]
        self.nameChanged(self.e_name.text())

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def updateUi(self):
        try:
            self.node.name()
            self.l_status.setText(self.node.name())
            self.l_status.setStyleSheet("QLabel { background-color : rgb(0,150,0); }")
        except:
            self.l_status.setText("Not connected")
            self.l_status.setStyleSheet("QLabel { background-color : rgb(150,0,0); }")

        curTake = self.cb_take.currentText()
        self.cb_take.clear()
        self.cb_take.addItems([x.name() for x in hou.takes.takes()])
        idx = self.cb_take.findText(curTake)
        if idx != -1:
            self.cb_take.setCurrentIndex(idx)

        self.camlist = []
        for node in hou.node("/").allSubChildren():
            if node.type().name() == "cam" and node.name() != "ipr_camera":
                self.camlist.append(node)

        self.cb_cam.clear()
        self.cb_cam.addItems([str(i) for i in self.camlist])

        try:
            self.curCam.name()
        except:
            self.curCam = None

        if self.curCam in self.camlist:
            self.cb_cam.setCurrentIndex(self.camlist.index(self.curCam))
        else:
            self.cb_cam.setCurrentIndex(0)
            if len(self.camlist) > 0:
                self.curCam = self.camlist[0]
            else:
                self.curCam = None
            self.stateManager.saveStatesToScene()

        if self.cb_outType.currentText() != ".hda":
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

        if self.cb_outType.currentText() == ".hda":
            if self.isNodeValid() and (
                self.node.canCreateDigitalAsset()
                or self.node.type().definition() is not None
            ):
                self.w_saveToExistingHDA.setEnabled(
                    self.node.type().definition() is not None
                )
            else:
                self.w_saveToExistingHDA.setEnabled(True)

            self.w_blackboxHDA.setEnabled(
                not self.isNodeValid() or self.node.type().areContentsViewable()
            )

            self.w_projectHDA.setEnabled(
                not self.w_saveToExistingHDA.isEnabled()
                or not self.chb_saveToExistingHDA.isChecked()
            )

            self.w_externalReferences.setEnabled(bool(
                self.node and
                self.node.canCreateDigitalAsset())
            )

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
        elif rangeType == "Node" and self.node:
            try:
                startFrame = self.node.parm("f1").eval()
                endFrame = self.node.parm("f2").eval()
            except:
                pass
        elif rangeType == "Single Frame":
            startFrame = self.core.appPlugin.getCurrentFrame()
        elif rangeType == "Custom":
            startFrame = self.sp_rangeStart.value()
            endFrame = self.sp_rangeEnd.value()

        return startFrame, endFrame

    @err_catcher(name=__name__)
    def typeChanged(self, idx, createMissing=True):
        self.isNodeValid()

        if idx == ".abc":
            self.f_cam.setVisible(False)
            self.w_sCamShot.setVisible(False)
            self.w_saveToExistingHDA.setVisible(False)
            self.w_blackboxHDA.setVisible(False)
            self.w_projectHDA.setVisible(False)
            self.w_externalReferences.setVisible(False)
            self.f_taskName.setVisible(True)
            self.f_status.setVisible(True)
            self.f_connect.setVisible(True)
            self.f_frameRange.setVisible(True)
            self.w_frameRangeValues.setVisible(True)
            self.f_convertExport.setVisible(True)
            if self.cb_manager.count() > 0:
                self.gb_submit.setVisible(True)
            if (
                self.node is None
                or self.node.type().name() not in ["rop_alembic", "alembic", "wedge"]
            ) and createMissing:
                self.createNode()
        elif idx == ".fbx":
            self.f_cam.setVisible(False)
            self.w_sCamShot.setVisible(False)
            self.w_saveToExistingHDA.setVisible(False)
            self.w_blackboxHDA.setVisible(False)
            self.w_projectHDA.setVisible(False)
            self.w_externalReferences.setVisible(False)
            self.f_taskName.setVisible(True)
            self.f_status.setVisible(True)
            self.f_connect.setVisible(True)
            self.f_frameRange.setVisible(True)
            self.w_frameRangeValues.setVisible(True)
            self.f_convertExport.setVisible(True)
            if self.cb_manager.count() > 0:
                self.gb_submit.setVisible(True)
            if (
                self.node is None
                or self.node.type().name() not in ["rop_fbx", "wedge"]
            ) and createMissing:
                self.createNode()
        elif idx == ".hda":
            self.f_cam.setVisible(False)
            self.w_sCamShot.setVisible(False)
            self.w_saveToExistingHDA.setVisible(True)
            self.w_blackboxHDA.setVisible(True)
            self.w_projectHDA.setVisible(True)
            self.w_externalReferences.setVisible(True)
            self.f_taskName.setVisible(True)
            self.f_status.setVisible(True)
            self.f_connect.setVisible(True)
            self.f_frameRange.setVisible(False)
            self.w_frameRangeValues.setVisible(False)
            self.f_convertExport.setVisible(False)
            self.gb_submit.setVisible(False)
            if (
                self.node is None
                or (
                    self.node is not None
                    and not (self.node.canCreateDigitalAsset())
                    or self.node.type().definition() is not None
                )
            ) and createMissing:
                self.createNode()
        elif idx == ".usd":
            self.f_cam.setVisible(False)
            self.w_sCamShot.setVisible(False)
            self.w_saveToExistingHDA.setVisible(False)
            self.w_blackboxHDA.setVisible(False)
            self.w_projectHDA.setVisible(False)
            self.w_externalReferences.setVisible(False)
            self.f_taskName.setVisible(True)
            self.f_status.setVisible(True)
            self.f_connect.setVisible(True)
            self.f_frameRange.setVisible(True)
            self.w_frameRangeValues.setVisible(True)
            self.f_convertExport.setVisible(True)
            if self.cb_manager.count() > 0:
                self.gb_submit.setVisible(True)
            if (
                self.node is None
                or self.node.type().name() not in ["pixar::usdrop", "usd", "wedge"]
            ) and createMissing:
                self.createNode()
        elif idx == ".rs":
            self.f_cam.setVisible(False)
            self.w_sCamShot.setVisible(False)
            self.w_saveToExistingHDA.setVisible(False)
            self.w_blackboxHDA.setVisible(False)
            self.w_projectHDA.setVisible(False)
            self.w_externalReferences.setVisible(False)
            self.f_taskName.setVisible(True)
            self.f_status.setVisible(True)
            self.f_connect.setVisible(True)
            self.f_frameRange.setVisible(True)
            self.w_frameRangeValues.setVisible(True)
            self.f_convertExport.setVisible(True)
            if self.cb_manager.count() > 0:
                self.gb_submit.setVisible(True)
            if (
                self.node is None
                or self.node.type().name() not in ["Redshift_Proxy_Output", "wedge"]
            ) and createMissing:
                self.createNode()
        elif idx == "ShotCam":
            self.f_cam.setVisible(True)
            self.w_sCamShot.setVisible(True)
            self.w_saveToExistingHDA.setVisible(False)
            self.w_blackboxHDA.setVisible(False)
            self.w_projectHDA.setVisible(False)
            self.w_externalReferences.setVisible(False)
            self.f_taskName.setVisible(False)
            self.f_status.setVisible(False)
            self.f_connect.setVisible(False)
            self.f_frameRange.setVisible(True)
            self.w_frameRangeValues.setVisible(True)
            self.f_convertExport.setVisible(True)
            self.gb_submit.setVisible(False)
        elif idx == "other":
            self.f_cam.setVisible(False)
            self.w_sCamShot.setVisible(False)
            self.w_saveToExistingHDA.setVisible(False)
            self.w_blackboxHDA.setVisible(False)
            self.w_projectHDA.setVisible(False)
            self.w_externalReferences.setVisible(False)
            self.f_taskName.setVisible(True)
            self.f_status.setVisible(True)
            self.f_connect.setVisible(True)
            self.f_frameRange.setVisible(True)
            self.w_frameRangeValues.setVisible(True)
            self.f_convertExport.setVisible(True)
            if self.cb_manager.count() > 0:
                self.gb_submit.setVisible(True)

            import CreateItem

            typeWin = CreateItem.CreateItem(core=self.core)
            typeWin.setModal(True)
            self.core.parentWindow(typeWin)
            typeWin.setWindowTitle("Outputtype")
            typeWin.l_item.setText("Outputtype:")
            typeWin.exec_()

            if hasattr(typeWin, "itemName"):
                if self.cb_outType.findText(typeWin.itemName) == -1:
                    self.cb_outType.insertItem(
                        self.cb_outType.count() - 1, typeWin.itemName
                    )

                if typeWin.itemName == "other":
                    self.cb_outType.setCurrentIndex(0)
                else:
                    self.cb_outType.setCurrentIndex(
                        self.cb_outType.findText(typeWin.itemName)
                    )

            else:
                self.cb_outType.setCurrentIndex(0)

            if (
                self.node is None
                or self.node.type().name()
                in [
                    "rop_alembic",
                    "rop_fbx",
                    "alembic",
                    "pixar::usdrop",
                    "usd",
                    "Redshift_Proxy_Output",
                ]
                or self.node.canCreateDigitalAsset()
                or self.node.type().definition() is not None
            ) and createMissing:
                self.createNode()

        else:
            self.f_cam.setVisible(False)
            self.w_sCamShot.setVisible(False)
            self.w_saveToExistingHDA.setVisible(False)
            self.w_blackboxHDA.setVisible(False)
            self.w_projectHDA.setVisible(False)
            self.w_externalReferences.setVisible(False)
            self.f_taskName.setVisible(True)
            self.f_status.setVisible(True)
            self.f_connect.setVisible(True)
            self.f_frameRange.setVisible(True)
            self.w_frameRangeValues.setVisible(True)
            self.f_convertExport.setVisible(True)
            if self.cb_manager.count() > 0:
                self.gb_submit.setVisible(True)
            if (
                self.node is None
                or self.node.type().name()
                in [
                    "rop_alembic",
                    "rop_fbx",
                    "alembic",
                    "pixar::usdrop",
                    "usd",
                    "Redshift_Proxy_Output",
                ]
                or self.node.canCreateDigitalAsset()
                or (
                    self.node.type().definition() is not None
                    and self.node.type().name() not in ["wedge"]
                )
            ) and createMissing:
                self.createNode()

        self.rjToggled()
        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def goToNode(self):
        try:
            self.node.name()
        except:
            self.createNode()

        try:
            self.node.name()
        except:
            self.updateUi()
            return False

        self.node.setCurrent(True, clear_all_selected=True)
        paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        if paneTab is not None:
            paneTab.setCurrentNode(self.node)
            paneTab.homeToSelection()

    @err_catcher(name=__name__)
    def connectNode(self, node=None):
        if node is None:
            if len(hou.selectedNodes()) == 0:
                return False

            node = hou.selectedNodes()[0]

        typeName = node.type().name()
        if (
            typeName
            in [
                "rop_geometry",
                "rop_dop",
                "rop_comp",
                "rop_alembic",
                "rop_fbx",
                "filecache",
                "pixar::usdrop",
                "usd",
                "Redshift_Proxy_Output",
            ]
            or (
                node.type().category().name() == "Driver"
                and typeName in ["geometry", "alembic", "wedge"]
            )
            or node.canCreateDigitalAsset()
            or node.type().definition() is not None
        ):
            self.node = node

            extension = ""
            if typeName in self.nodeTypes:
                outVal = self.node.parm(self.nodeTypes[typeName]["outputparm"]).eval()

            if typeName in [
                "rop_dop",
                "rop_comp",
                "rop_alembic",
                "rop_fbx",
                "pixar::usdrop",
                "usd",
                "Redshift_Proxy_Output",
            ]:
                extension = os.path.splitext(outVal)[1]
            elif typeName in ["rop_geometry", "filecache"]:
                if outVal.endswith(".bgeo.sc"):
                    extension = ".bgeo.sc"
                else:
                    extension = os.path.splitext(outVal)[1]

            elif (
                typeName == "geometry"
                and self.node.type().category().name() == "Driver"
            ):
                if outVal.endswith(".bgeo.sc"):
                    extension = ".bgeo.sc"
                else:
                    extension = os.path.splitext(outVal)[1]
            elif (
                typeName == "alembic" and self.node.type().category().name() == "Driver"
            ):
                extension = os.path.splitext(outVal)[1]
            elif typeName == "wedge" and self.node.type().category().name() == "Driver":
                rop = self.getWedgeROP(self.node)
                if rop:
                    extension = os.path.splitext(
                        self.nodeTypes[rop.type().name()]["outputparm"]
                    )[1]
                else:
                    extension = ".bgeo.sc"
            elif (
                self.node.canCreateDigitalAsset()
                or self.node.type().definition() is not None
            ):
                extension = ".hda"

            if self.cb_outType.findText(extension) != -1:
                self.cb_outType.setCurrentIndex(self.cb_outType.findText(extension))
                self.typeChanged(self.cb_outType.currentText(), createMissing=False)

            self.nameChanged(self.e_name.text())
            self.updateUi()
            self.stateManager.saveStatesToScene()
            return True

        return False

    @err_catcher(name=__name__)
    def getWedgeROP(self, wedge):
        if wedge.inputs():
            return wedge.inputs()[0]
        else:
            node = hou.node(wedge.parm("driver").eval())
            if node.type().name() in self.nodeTypes:
                return node

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
    def useTakeChanged(self, state):
        self.cb_take.setEnabled(state)
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def getOutputType(self):
        return self.cb_outType.currentText()

    @err_catcher(name=__name__)
    def rjToggled(self, checked=None):
        if checked is None:
            checked = self.gb_submit.isChecked()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def managerChanged(self, text=None):
        if self.cb_manager.currentText() in self.core.rfManagers:
            self.core.rfManagers[self.cb_manager.currentText()].sm_houExport_activated(
                self
            )
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
    def preDelete(self, item, silent=False):
        self.core.appPlugin.sm_preDelete(self, item, silent)

    @err_catcher(name=__name__)
    def preExecuteState(self):
        warnings = []

        if self.cb_outType.currentText() == "ShotCam":
            if self.curCam is None:
                warnings.append(["No camera specified.", "", 3])
        else:
            if self.l_taskName.text() == "":
                warnings.append(["No taskname is given.", "", 3])

            try:
                self.node.name()
            except:
                warnings.append(["Node is invalid.", "", 3])

        if self.cb_outType.currentText() != ".hda":
            rangeType = self.cb_rangeType.currentText()
            startFrame, endFrame = self.getFrameRange(rangeType)

            if startFrame is None:
                warnings.append(["Framerange is invalid.", "", 3])

        if not hou.simulationEnabled():
            warnings.append(["Simulations are disabled.", "", 2])

        if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
            warnings += self.core.rfManagers[
                self.cb_manager.currentText()
            ].sm_houExport_preExecute(self)

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def getHDAOutputName(self, useVersion="next"):
        version = useVersion
        comment = None
        user = None
        if version != "next":
            versionData = version.split(self.core.filenameSeparator)
            if len(versionData) == 3:
                version, comment, user = versionData

        fileName = self.core.getCurrentFileName()
        fnameData = self.core.getScenefileData(fileName)
        if comment is None and fnameData.get("entity") != "invalid":
            comment = fnameData["comment"]

        result = self.core.appPlugin.getHDAOutputpath(
            node=self.node,
            task=self.l_taskName.text(),
            comment=comment,
            user=user,
            version=version,
            location=self.cb_outPath.currentText(),
            saveToExistingHDA=self.chb_saveToExistingHDA.isChecked(),
            projectHDA=self.chb_projectHDA.isChecked(),
        )

        return result["outputPath"], result["outputFolder"], result["version"]

    @err_catcher(name=__name__)
    def getOutputName(self, useVersion="next"):
        if self.cb_outType.currentText() == ".hda":
            return self.getHDAOutputName(useVersion)

        fileName = self.core.getCurrentFileName()
        fnameData = self.core.getScenefileData(fileName)
        prefUnit = "meter"

        if self.cb_outType.currentText() == "ShotCam":
            outputBase = os.path.join(
                self.core.getShotPath(), self.cb_sCamShot.currentText()
            )
            comment = fnameData["comment"]
            versionUser = self.core.user
            outputPath = os.path.abspath(os.path.join(outputBase, "Export", "_ShotCam"))

            if useVersion != "next":
                versionData = useVersion.split(self.core.filenameSeparator)
                if len(versionData) == 3:
                    hVersion, comment, versionUser = versionData
                else:
                    useVersion == "next"

            if useVersion == "next":
                hVersion = self.core.getHighestTaskVersion(outputPath)

            outputPath = os.path.join(
                outputPath,
                hVersion
                + self.core.filenameSeparator
                + comment
                + self.core.filenameSeparator
                + versionUser,
                prefUnit,
            )
            outputName = os.path.join(
                outputPath,
                "shot"
                + self.core.filenameSeparator
                + self.cb_sCamShot.currentText()
                + self.core.filenameSeparator
                + "ShotCam"
                + self.core.filenameSeparator
                + hVersion,
            )
        else:
            if self.l_taskName.text() == "":
                return

            if self.core.useLocalFiles and fileName.startswith(
                self.core.localProjectPath
            ):
                fileName = fileName.replace(
                    self.core.localProjectPath, self.core.projectPath
                )

            versionUser = self.core.user
            hVersion = ""
            if useVersion != "next":
                versionData = useVersion.split(self.core.filenameSeparator)
                if len(versionData) == 3:
                    hVersion, pComment, versionUser = versionData

            framePadding = ".$F4" if self.cb_rangeType.currentText() != "Single Frame" else ""
            if fnameData["entity"] == "shot":
                outputPath = os.path.join(
                    self.core.getEntityBasePath(fileName),
                    "Export",
                    self.l_taskName.text(),
                )
                if hVersion == "":
                    hVersion = self.core.getHighestTaskVersion(outputPath)
                    pComment = fnameData["comment"]

                hVersion = (
                    (hVersion + "-wedge`$WEDGENUM`")
                    if self.node and self.node.type().name() == "wedge"
                    else hVersion
                )

                outputPath = os.path.join(
                    outputPath,
                    hVersion
                    + self.core.filenameSeparator
                    + pComment
                    + self.core.filenameSeparator
                    + versionUser,
                    prefUnit,
                )
                outputName = os.path.join(
                    outputPath,
                    "shot"
                    + self.core.filenameSeparator
                    + fnameData["entityName"]
                    + self.core.filenameSeparator
                    + self.l_taskName.text()
                    + self.core.filenameSeparator
                    + hVersion
                    + framePadding
                    + self.cb_outType.currentText(),
                )
            elif fnameData["entity"] == "asset":
                outputPath = os.path.join(
                    self.core.getEntityBasePath(fileName),
                    "Export",
                    self.l_taskName.text(),
                )
                if hVersion == "":
                    hVersion = self.core.getHighestTaskVersion(outputPath)
                    pComment = fnameData["comment"]

                outputPath = os.path.join(
                    outputPath,
                    hVersion
                    + self.core.filenameSeparator
                    + pComment
                    + self.core.filenameSeparator
                    + versionUser,
                    prefUnit,
                )
                outputName = os.path.join(
                    outputPath,
                    fnameData["entityName"]
                    + self.core.filenameSeparator
                    + self.l_taskName.text()
                    + self.core.filenameSeparator
                    + hVersion
                    + framePadding
                    + self.cb_outType.currentText(),
                )
            else:
                return

        basePath = self.export_paths[self.cb_outPath.currentText()]
        prjPath = os.path.normpath(self.core.projectPath)
        basePath = os.path.normpath(basePath)
        outputName = outputName.replace(prjPath, basePath)
        outputPath = outputPath.replace(prjPath, basePath)

        return outputName.replace("\\", "/"), outputPath.replace("\\", "/"), hVersion

    @err_catcher(name=__name__)
    def executeState(self, parent, useVersion="next"):
        if self.cb_outType.currentText() != ".hda":
            rangeType = self.cb_rangeType.currentText()
            startFrame, endFrame = self.getFrameRange(rangeType)
            if startFrame is None:
                return [self.state.text(0) + ": error - Framerange is invalid"]

            if rangeType == "Single Frame":
                endFrame = startFrame
        else:
            startFrame = None
            endFrame = None

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

            if not os.path.exists(outputPath):
                os.makedirs(outputPath)

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

            self.core.saveVersionInfo(
                location=os.path.dirname(outputPath),
                version=hVersion,
                origin=fileName,
                fps=startFrame != endFrame,
            )

            if self.chb_convertExport.isChecked():
                inputCons = self.curCam.inputConnections()
                if (
                    len(inputCons) > 0
                    and inputCons[0].inputNode().type().name() == "null"
                    and inputCons[0].inputNode().name() == "SCALEOVERRIDE"
                ):
                    transformNode = inputCons[0].inputNode()
                else:
                    transformNode = self.curCam.createInputNode(
                        0, "null", "SCALEOVERRIDE"
                    )
                    for i in inputCons:
                        transformNode.setInput(0, i.inputNode(), i.inputIndex())

            abc_rop = hou.node("/out").createNode("alembic")

            abc_rop.parm("trange").set(1)
            abc_rop.parm("f1").set(startFrame)
            abc_rop.parm("f2").set(endFrame)
            abc_rop.parm("filename").set(outputName + ".abc")
            abc_rop.parm("root").set(self.curCam.parent().path())
            abc_rop.parm("objects").set(self.curCam.name())

            fbx_rop = hou.node("/out").createNode("filmboxfbx")
            fbx_rop.parm("sopoutput").set(outputName + ".fbx")
            fbx_rop.parm("startnode").set(self.curCam.path())

            for node in [abc_rop, fbx_rop]:
                if self.chb_useTake.isChecked():
                    pTake = self.cb_take.currentText()
                    takeLabels = [
                        x.strip() for x in self.node.parm("take").menuLabels()
                    ]
                    if pTake in takeLabels:
                        idx = takeLabels.index(pTake)
                        if idx != -1:
                            token = self.node.parm("take").menuItems()[idx]
                            if not self.core.appPlugin.setNodeParm(
                                self.node, "take", val=token
                            ):
                                return [
                                    self.state.text(0) + ": error - Publish canceled"
                                ]
                    else:
                        return [
                            self.state.text(0)
                            + ": error - take '%s' doesn't exist." % pTake
                        ]

            abc_rop.render()
            fbx_rop.render(frame_range=(startFrame, endFrame))

            if self.chb_convertExport.isChecked():
                transformNode.parm("scale").set(100)

                outputName = os.path.join(
                    os.path.dirname(os.path.dirname(outputName)),
                    "centimeter",
                    os.path.basename(outputName),
                )
                if not os.path.exists(os.path.dirname(outputName)):
                    os.makedirs(os.path.dirname(outputName))

                abc_rop.parm("filename").set(outputName + ".abc")
                abc_rop.render()
                fbx_rop.parm("sopoutput").set(outputName + ".fbx")
                fbx_rop.render(frame_range=(startFrame, endFrame))

                transformNode.destroy()

            abc_rop.destroy()
            fbx_rop.destroy()

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

            self.core.callback("postExport", **kwargs)

            self.stateManager.saveStatesToScene()

            if os.path.exists(outputName + ".abc") and os.path.exists(
                outputName + ".fbx"
            ):
                return [self.state.text(0) + " - success"]
            else:
                return [self.state.text(0) + " - error"]

        else:
            if self.l_taskName.text() == "":
                return [
                    self.state.text(0)
                    + ": error - No taskname is given. Skipped the activation of this state."
                ]

            try:
                self.node.name()
            except:
                return [
                    self.state.text(0)
                    + ": error - Node is invalid. Skipped the activation of this state."
                ]

            if (
                not (
                    self.node.isEditable()
                    or (
                        self.node.type().name() in ["filecache", "wedge"]
                        and self.node.isEditableInsideLockedHDA()
                    )
                )
                and self.cb_outType.currentText() != ".hda"
            ):
                return [
                    self.state.text(0)
                    + ": error - Node is locked. Skipped the activation of this state."
                ]

            if self.node.type().name() == "wedge":
                ropNode = self.getWedgeROP(self.node)
                if not ropNode:
                    return [
                        self.state.text(0)
                        + ": error - No valid ROP is connected to the Wedge node. Skipped the activation of this state."
                    ]
            else:
                ropNode = self.node

            fileName = self.core.getCurrentFileName()

            outputName, outputPath, hVersion = self.getOutputName(useVersion=useVersion)

            outLength = len(outputName)
            if platform.system() == "Windows" and outLength > 255:
                return [
                    self.state.text(0)
                    + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, taskname or projectpath."
                    % outLength
                ]

            if self.cb_outType.currentText() in [".abc", ".fbx", ".usd", ".hda"]:
                outputName = outputName.replace(".$F4", "")

            if self.cb_outType.currentText() == ".hda":
                if (
                    not ropNode.canCreateDigitalAsset()
                    and ropNode.type().definition() is None
                ):
                    return [
                        self.state.text(0)
                        + ": error - Cannot create a digital asset from this node: %s"
                        % ropNode.path()
                    ]
            else:
                if not self.core.appPlugin.setNodeParm(ropNode, "trange", val=1):
                    return [self.state.text(0) + ": error - Publish canceled"]

                if not self.core.appPlugin.setNodeParm(ropNode, "f1", clear=True):
                    return [self.state.text(0) + ": error - Publish canceled"]

                if not self.core.appPlugin.setNodeParm(ropNode, "f2", clear=True):
                    return [self.state.text(0) + ": error - Publish canceled"]

                if not self.core.appPlugin.setNodeParm(ropNode, "f1", val=startFrame):
                    return [self.state.text(0) + ": error - Publish canceled"]

                if not self.core.appPlugin.setNodeParm(ropNode, "f2", val=endFrame):
                    return [self.state.text(0) + ": error - Publish canceled"]

                if ropNode.type().name() in [
                    "rop_geometry",
                    "rop_alembic",
                    "rop_dop",
                    "geometry",
                    "filecache",
                    "alembic",
                ] and self.initsim:
                    if not self.core.appPlugin.setNodeParm(
                        ropNode, "initsim", val=True
                    ):
                        return [self.state.text(0) + ": error - Publish canceled"]

                if self.chb_useTake.isChecked():
                    pTake = self.cb_take.currentText()
                    takeLabels = [x.strip() for x in ropNode.parm("take").menuLabels()]
                    if pTake in takeLabels:
                        idx = takeLabels.index(pTake)
                        if idx != -1:
                            token = ropNode.parm("take").menuItems()[idx]
                            if not self.core.appPlugin.setNodeParm(
                                ropNode, "take", val=token
                            ):
                                return [
                                    self.state.text(0) + ": error - Publish canceled"
                                ]
                    else:
                        return [
                            self.state.text(0)
                            + ": error - take '%s' doesn't exist." % pTake
                        ]

            expandedOutputPath = hou.expandString(outputPath)
            expandedOutputName = hou.expandString(outputName)
            if not os.path.exists(expandedOutputPath):
                os.makedirs(expandedOutputPath)

            kwargs = {
                "state": self,
                "scenefile": fileName,
                "startframe": startFrame,
                "endframe": endFrame,
                "outputpath": expandedOutputName,
            }

            self.core.callback("preExport", **kwargs)
            self.core.saveVersionInfo(
                location=os.path.dirname(expandedOutputPath),
                version=hVersion,
                origin=fileName,
                fps=startFrame != endFrame,
            )

            outputNames = [outputName]
            if (
                not self.chb_convertExport.isHidden()
                and self.chb_convertExport.isChecked()
            ):
                inputCons = ropNode.inputConnections()
                if (
                    len(inputCons) > 0
                    and inputCons[0].inputNode().type().name() == "xform"
                    and inputCons[0].inputNode().name() == "SCALEOVERRIDE"
                ):
                    transformNode = inputCons[0].inputNode()
                else:
                    transformNode = ropNode.createInputNode(0, "xform", "SCALEOVERRIDE")
                    for i in inputCons:
                        transformNode.setInput(0, i.inputNode(), i.inputIndex())

                outputNames.append(
                    os.path.join(
                        os.path.dirname(os.path.dirname(expandedOutputName)),
                        "centimeter",
                        os.path.basename(expandedOutputName),
                    )
                )
                if not os.path.exists(os.path.dirname(outputNames[1])):
                    os.makedirs(os.path.dirname(outputNames[1]))

            self.l_pathLast.setText(outputNames[0])
            self.l_pathLast.setToolTip(outputNames[0])
            self.b_openLast.setEnabled(True)
            self.b_copyLast.setEnabled(True)

            self.stateManager.saveStatesToScene()

            for idx, outputName in enumerate(outputNames):
                outputName = outputName.replace("\\", "/")
                expandedOutputName = hou.expandString(outputName)
                parmName = False

                if ropNode.type().name() in self.nodeTypes:
                    parmName = self.nodeTypes[ropNode.type().name()]["outputparm"]

                if parmName != False:
                    self.stateManager.publishInfos["updatedExports"][
                        ropNode.parm(parmName).unexpandedString()
                    ] = outputName

                    if not self.core.appPlugin.setNodeParm(
                        ropNode, parmName, val=outputName
                    ):
                        return [self.state.text(0) + ": error - Publish canceled"]

                hou.hipFile.save()

                if idx == 1:
                    if not self.core.appPlugin.setNodeParm(
                        transformNode, "scale", val=100
                    ):
                        return [self.state.text(0) + ": error - Publish canceled"]

                if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
                    result = self.core.rfManagers[
                        self.cb_manager.currentText()
                    ].sm_render_submitJob(self, outputName, parent)
                else:
                    try:
                        if self.cb_outType.currentText() == ".hda":
                            result = self.exportHDA(ropNode, outputName)
                        else:
                            result = self.executeNode()

                        if result:
                            if len(os.listdir(os.path.dirname(expandedOutputName))) > 0:
                                result = "Result=Success"
                            else:
                                result = "unknown error (files do not exist)"

                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        erStr = "%s ERROR - houExport %s:\n%s" % (
                            time.strftime("%d/%m/%y %X"),
                            self.core.version,
                            traceback.format_exc(),
                        )
                        self.core.writeErrorLog(erStr)

                        return [
                            self.state.text(0)
                            + " - unknown error (view console for more information)"
                        ]

                if idx == 1:
                    if not self.core.appPlugin.setNodeParm(transformNode, "scale", val=1):
                        return [self.state.text(0) + ": error - Publish canceled"]

            kwargs = {
                "state": self,
                "scenefile": fileName,
                "startframe": startFrame,
                "endframe": endFrame,
                "outputpath": expandedOutputName,
            }

            self.core.callback("postExport", **kwargs)

            if "Result=Success" in result:
                return [self.state.text(0) + " - success"]
            else:
                erStr = "%s ERROR - houExportPublish %s:\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    self.core.version,
                    result,
                )
                if result == "unknown error (files do not exist)":
                    QMessageBox.warning(
                        self.core.messageParent,
                        "Warning",
                        "No files were created during the rendering. If you think this is a Prism bug please report it in the forum:\nwww.prism-pipeline.com/forum/\nor write a mail to contact@prism-pipeline.com",
                    )
                elif not result.startswith(
                    "Execute Canceled"
                ) and not result.startswith("Execute failed"):
                    self.core.writeErrorLog(erStr)
                return [self.state.text(0) + " - error - " + result]

    @err_catcher(name=__name__)
    def executeNode(self):
        result = True
        self.node.parm("execute").pressButton()
        errs = self.node.errors()
        if len(errs) > 0:
            errs = "\n" + "\n\n".join(errs)
            erStr = "%s ERROR - houExportnode %s:\n%s" % (
                time.strftime("%d/%m/%y %X"),
                self.core.version,
                errs,
            )
            result = "Execute failed: " + errs

        return result

    @err_catcher(name=__name__)
    def exportHDA(self, node, outputPath):
        fileName = self.core.getCurrentFileName()
        data = self.core.getScenefileData(fileName)
        entityName = data.get("entityName", "")
        taskName = self.l_taskName.text()
        typeName = "%s_%s" % (entityName, taskName)

        label = typeName
        saveToExistingHDA = self.chb_saveToExistingHDA.isChecked()
        createBlackBox = self.chb_blackboxHDA.isChecked()
        allowExtRef = self.chb_externalReferences.isChecked()
        projectHDA = self.chb_projectHDA.isChecked()

        if node.canCreateDigitalAsset():
            convertNode = not createBlackBox
        else:
            convertNode = saveToExistingHDA

        if projectHDA:
            typeName = taskName
            outputPath = None
            label = self.l_taskName.text()

        # hou.HDADefinition.copyToHDAFile converts "-" to "_"
        typeName = typeName.replace("-", "_")
        label = label.replace("-", "_")

        result = self.core.appPlugin.createHDA(
            node,
            outputPath=outputPath,
            typeName=typeName,
            label=label,
            saveToExistingHDA=saveToExistingHDA,
            blackBox=createBlackBox,
            allowExternalReferences=allowExtRef,
            projectHDA=projectHDA,
            convertNode=convertNode,
        )
        if result and not isinstance(result, bool):
            self.connectNode(result)

        self.updateUi()
        return True

    @err_catcher(name=__name__)
    def getStateProps(self):
        outputTypes = []
        for i in range(self.cb_outType.count()):
            outputTypes.append(str(self.cb_outType.itemText(i)))

        try:
            curNode = self.node.path()
            self.node.setUserData("PrismPath", curNode)
        except:
            curNode = None

        self.curCam
        try:
            curCam = self.curCam.name()
        except:
            curCam = None

        stateProps = {
            "statename": self.e_name.text(),
            "taskname": self.l_taskName.text(),
            "rangeType": str(self.cb_rangeType.currentText()),
            "startframe": self.sp_rangeStart.value(),
            "endframe": self.sp_rangeEnd.value(),
            "usetake": str(self.chb_useTake.isChecked()),
            "take": self.cb_take.currentText(),
            "curoutputpath": self.cb_outPath.currentText(),
            "outputtypes": str(outputTypes),
            "curoutputtype": self.cb_outType.currentText(),
            "connectednode": curNode,
            "unitconvert": str(self.chb_convertExport.isChecked()),
            "savetoexistinghda": str(self.chb_saveToExistingHDA.isChecked()),
            "projecthda": str(self.chb_projectHDA.isChecked()),
            "externalReferences": str(self.chb_externalReferences.isChecked()),
            "blackboxhda": str(self.chb_blackboxHDA.isChecked()),
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
            "currentcam": str(curCam),
            "currentscamshot": self.cb_sCamShot.currentText(),
            "lastexportpath": self.l_pathLast.text().replace("\\", "/"),
            "stateenabled": str(self.state.checkState(0)),
        }

        return stateProps
