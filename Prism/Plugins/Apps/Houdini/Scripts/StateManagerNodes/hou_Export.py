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

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

import hou

from PrismUtils.Decorators import err_catcher as err_catcher


logger = logging.getLogger(__name__)


class ExportClass(object):
    className = "Export"
    listType = "Export"
    stateCategories = {"Export": [{"label": className, "stateType": className}]}

    @err_catcher(name=__name__)
    def setup(self, state, core, stateManager, node=None, stateData=None):
        self.state = state
        self.core = core
        self.stateManager = stateManager
        self.canSetVersion = True

        self.e_name.setText(state.text(0) + " - {product} ({node})")

        self.node = None
        self.curCam = None
        self.initsim = True

        self.setTaskname("")
        self.cb_outType.addItems(self.core.appPlugin.outputFormats)
        self.export_paths = self.core.paths.getExportProductBasePaths()

        self.cb_outPath.addItems(list(self.export_paths.keys()))
        if len(self.export_paths) < 2:
            self.w_outPath.setVisible(False)

        self.l_name.setVisible(False)
        self.e_name.setVisible(False)
        self.f_cam.setVisible(False)
        self.w_sCamShot.setVisible(False)
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
            "prism::Filecache::1.0": {"outputparm": "outputPath"},
            "vellumio": {"outputparm": "file"},
            "vellumio::2.0": {"outputparm": "file"},
        }

        self.rangeTypes = [
            "Scene",
            "Shot",
            "Node",
            "Single Frame",
            "Custom",
        ]
        self.cb_rangeType.addItems(self.rangeTypes)
        for idx, rtype in enumerate(self.rangeTypes):
            self.cb_rangeType.setItemData(
                idx, self.stateManager.getFrameRangeTypeToolTip(rtype), Qt.ToolTipRole
            )

        self.cb_manager.addItems([p.pluginName for p in self.core.plugins.getRenderfarmPlugins()])
        self.core.callback("onStateStartup", self)
        self.stateManager.stateInCreation = self.state

        if self.cb_manager.count() == 0:
            self.gb_submit.setVisible(False)

        if node is None and not self.stateManager.standalone:
            if stateData is None:
                if not self.connectNode():
                    self.createNode()
        else:
            self.connectNode(node)

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
                self.typeChanged(self.getOutputType())

        elif stateData is None:
            self.sp_rangeStart.setValue(hou.playbar.playbackRange()[0])
            self.sp_rangeEnd.setValue(hou.playbar.playbackRange()[1])

        self.managerChanged(True)
        self.connectEvents()
        self.core.appPlugin.fixStyleSheet(self.gb_submit)
        self.e_osSlaves.setText("All")

        self.updateUi()
        if stateData is not None:
            self.loadData(stateData)
        else:
            context = self.getOutputEntity()
            if (
                context.get("type") == "shot"
                and "sequence" in context
            ):
                if self.getOutputType() == "ShotCam":
                    self.refreshShotCameras()

                shotName = self.core.entities.getShotName(context)
                idx = self.cb_sCamShot.findText(shotName)
                if idx != -1:
                    self.cb_sCamShot.setCurrentIndex(idx)

            if self.getRangeType() != "Node":
                if context.get("type") == "asset":
                    self.setRangeType("Single Frame")
                elif context.get("type") == "shot":
                    self.setRangeType("Shot")
                else:
                    self.setRangeType("Scene")

            if context.get("task") and not self.isPrismFilecacheNode(self.node):
                self.setTaskname(context.get("task"))

    @err_catcher(name=__name__)
    def loadData(self, data):
        if "stateName" in data:
            self.e_name.setText(data["stateName"])
        elif "statename" in data:
            name = data["statename"] + " - {product} ({node})"
            self.e_name.setText(name)
        if "taskname" in data:
            self.setTaskname(data["taskname"])
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
        if "updateMasterVersion" in data:
            self.chb_master.setChecked(data["updateMasterVersion"])
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
                self.typeChanged(self.getOutputType(), createMissing=False)
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
        if "currentcam" in data:
            idx = self.cb_cam.findText(data["currentcam"])
            if idx != -1:
                self.curCam = self.camlist[idx]
                if self.getOutputType() == "ShotCam":
                    self.nameChanged(self.e_name.text())
        if "currentscamshot" in data:
            idx = self.cb_sCamShot.findText(data["currentscamshot"])
            if idx != -1:
                self.cb_sCamShot.setCurrentIndex(idx)
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

        self.nameChanged(self.e_name.text())
        self.core.callback("onStateSettingsLoaded", self, data)

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

        if self.getOutputType() == ".abc":
            if curContext == "Sop":
                ropType = "rop_alembic"
            else:
                ropType = "alembic"
        elif self.getOutputType() == ".fbx":
            ropType = "rop_fbx"
        elif self.getOutputType() == ".usd":
            ropType = "usd"
        elif self.getOutputType() == ".rs":
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
        self.cb_outPath.activated[str].connect(self.onLocationChanged)
        self.cb_outType.activated[str].connect(self.typeChanged)
        self.chb_useTake.stateChanged.connect(self.useTakeChanged)
        self.cb_take.activated.connect(self.stateManager.saveStatesToScene)
        self.chb_master.stateChanged.connect(self.onUpdateMasterChanged)
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
        self.cb_cam.activated.connect(self.setCam)
        self.cb_sCamShot.activated.connect(self.stateManager.saveStatesToScene)
        self.b_pathLast.clicked.connect(self.showLastPathMenu)

        if not self.stateManager.standalone:
            self.b_goTo.clicked.connect(self.goToNode)
            self.b_connect.clicked.connect(self.connectNode)
            self.b_connect.setContextMenuPolicy(Qt.CustomContextMenu)
            self.b_connect.customContextMenuRequested.connect(self.onConnectMenuTriggered)

    @err_catcher(name=__name__)
    def showLastPathMenu(self):
        path = self.l_pathLast.text()
        if path == "None":
            return
        
        menu = QMenu(self)

        act_open = QAction("Open in Product Browser", self)
        act_open.triggered.connect(lambda: self.openInProductBrowser(path))
        menu.addAction(act_open)

        act_open = QAction("Open in explorer", self)
        act_open.triggered.connect(lambda: self.core.openFolder(path))
        menu.addAction(act_open)

        act_copy = QAction("Copy", self)
        act_copy.triggered.connect(lambda: self.core.copyToClipboard(path, file=True))
        menu.addAction(act_copy)

        menu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def openInProductBrowser(self, path):
        self.core.projectBrowser()
        self.core.pb.showTab("Products")
        data = self.core.paths.getCachePathData(path)
        self.core.pb.productBrowser.navigateToVersion(version=data["version"], product=data["product"], entity=data)

    @err_catcher(name=__name__)
    def rangeTypeChanged(self, state):
        if self.isPrismFilecacheNode(self.node):
            if self.getRangeType() != "Node":
                self.core.appPlugin.filecache.setRangeOnNode(self.node, "From State Manager")

        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def nameChanged(self, text):
        text = self.e_name.text()
        context = {}
        if self.getOutputType() == "ShotCam":
            context["product"] = "Shotcam"
            context["node"] = self.curCam
        else:
            context["product"] = self.getTaskname(expanded=True)
            if self.isNodeValid():
                context["node"] = self.node
            else:
                context["node"] = "None"

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
    def isPrismFilecacheNode(self, node):
        if not self.core.appPlugin.isNodeValid(self, node):
            return False

        if node.type().name().startswith("prism::Filecache"):
            return True

        return False

    @err_catcher(name=__name__)
    def changeTask(self):
        from PrismUtils import PrismWidgets
        self.nameWin = PrismWidgets.CreateItem(
            startText=self.getTaskname(),
            showTasks=True,
            taskType="export",
            core=self.core,
        )
        self.core.parentWindow(self.nameWin)
        self.nameWin.setWindowTitle("Change Productname")
        self.nameWin.l_item.setText("Productname:")
        self.nameWin.buttonBox.buttons()[0].setText("Ok")
        self.nameWin.e_item.selectAll()
        result = self.nameWin.exec_()

        if result == 1:
            taskName = self.nameWin.e_item.text()
            self.setTaskname(taskName)
            self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def setTaskname(self, taskname):
        self.l_taskName.setText(taskname)
        self.nameChanged(self.e_name.text())
        if taskname:
            self.b_changeTask.setStyleSheet("")
        else:
            self.b_changeTask.setStyleSheet(
                "QPushButton { background-color: rgb(150,0,0); border: none;}"
            )

        if self.isPrismFilecacheNode(self.node):
            self.core.appPlugin.setNodeParm(self.node, "task", taskname, clear=True)

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def getTaskname(self, expanded=False):
        if self.getOutputType() == "ShotCam":
            taskName = "_ShotCam"
        else:
            taskName = self.l_taskName.text()
            if expanded:
                if self.node:
                    taskName = taskName.replace("$OS", self.node.name())

                taskName = hou.text.expandString(taskName)

        return taskName

    @err_catcher(name=__name__)
    def getSortKey(self):
        return self.getTaskname(expanded=True)

    @err_catcher(name=__name__)
    def getOutputType(self):
        return self.cb_outType.currentText()

    @err_catcher(name=__name__)
    def setOutputType(self, outputtype):
        idx = self.cb_outType.findText(outputtype)
        if idx == self.cb_outType.currentIndex():
            return True

        if idx != -1:
            self.cb_outType.setCurrentIndex(idx)
            self.typeChanged(self.getOutputType(), createMissing=False)
            return True

        return False

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
    def onUpdateMasterChanged(self, master):
        if self.isPrismFilecacheNode(self.node):
            self.core.appPlugin.filecache.setUpdateMasterVersionOnNode(self.node, master)

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def getUpdateMasterVersion(self):
        return self.chb_master.isChecked()

    @err_catcher(name=__name__)
    def setUpdateMasterVersion(self, master):
        self.chb_master.setChecked(master)

    @err_catcher(name=__name__)
    def onLocationChanged(self, location):
        if self.isPrismFilecacheNode(self.node):
            self.core.appPlugin.filecache.setLocationOnNode(self.node, location)

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def getLocation(self):
        return self.cb_outPath.currentText()

    @err_catcher(name=__name__)
    def setLocation(self, location):
        idx = self.cb_outPath.findText(location)
        if idx != -1:
            self.cb_outPath.setCurrentIndex(idx)
            self.stateManager.saveStatesToScene()
            return True

        return False

    @err_catcher(name=__name__)
    def setCam(self, index):
        self.curCam = self.camlist[index]
        self.nameChanged(self.e_name.text())

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def refreshShotCameras(self):
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

    @err_catcher(name=__name__)
    def updateUi(self):
        if self.isNodeValid():
            self.l_status.setText(self.node.name())
            self.l_status.setToolTip(self.node.path())
            self.l_status.setStyleSheet("QLabel { background-color : rgb(0,150,0); }")
        else:
            self.l_status.setText("Not connected")
            self.l_status.setToolTip("")
            self.l_status.setStyleSheet("QLabel { background-color : rgb(150,0,0); }")

        if self.gb_previous.isHidden():
            self.w_name.setVisible(True)
            self.gb_general.setVisible(True)
            self.gb_previous.setHidden(False)
            self.gb_submit.setCheckable(True)

            if self.cb_manager.count() == 1:
                self.f_manager.setVisible(True)
                self.gb_submit.setTitle("Submit Render Job")

        curTake = self.cb_take.currentText()
        self.cb_take.clear()
        self.cb_take.addItems([x.name() for x in hou.takes.takes()])
        idx = self.cb_take.findText(curTake)
        if idx != -1:
            self.cb_take.setCurrentIndex(idx)

        if self.getOutputType() == "ShotCam":
            self.refreshShotCameras()

        if self.isPrismFilecacheNode(self.node):
            self.core.appPlugin.filecache.nodeInit(self.node, self.state)
            self.core.appPlugin.filecache.refreshNodeUi(self.node, self)

        self.updateRange()
        if not self.core.products.getUseMaster():
            self.w_master.setVisible(False)

        curShot = self.cb_sCamShot.currentText()
        self.cb_sCamShot.clear()
        _, shots = self.core.entities.getShots()
        for shot in sorted(shots, key=lambda s: self.core.entities.getShotName(s).lower()):
            shotData = {"sequence": shot["sequence"], "shot": shot["shot"], "type": "shot"}
            shotName = self.core.entities.getShotName(shot)
            self.cb_sCamShot.addItem(shotName, shotData)

        idx = self.cb_sCamShot.findText(curShot)
        if idx != -1:
            self.cb_sCamShot.setCurrentIndex(idx)
        else:
            self.cb_sCamShot.setCurrentIndex(0)
            self.stateManager.saveStatesToScene()

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
        if rangeType == "Scene":
            startFrame, endFrame = self.core.appPlugin.getFrameRange(self)
        elif rangeType == "Shot":
            context = self.getOutputEntity()
            if context.get("type") == "shot" and "sequence" in context:
                frange = self.core.entities.getShotRange(context)
                if frange:
                    startFrame, endFrame = frange
        elif rangeType == "Node" and self.node:
            api = self.core.appPlugin.getApiFromNode(self.node)
            if api:
                startFrame, endFrame = api.getFrameRange(self.node)

            if startFrame is None:
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
            self.f_taskName.setVisible(True)
            self.f_status.setVisible(True)
            self.f_connect.setVisible(True)
            self.f_frameRange.setVisible(True)
            self.w_frameRangeValues.setVisible(True)
            if self.cb_manager.count() > 0:
                self.gb_submit.setVisible(True)
            if (
                self.node is None
                or self.node.type().name()
                not in ["rop_alembic", "alembic", "wedge", "prism::Filecache::1.0"]
            ) and createMissing:
                self.createNode()
        elif idx == ".fbx":
            self.f_cam.setVisible(False)
            self.w_sCamShot.setVisible(False)
            self.f_taskName.setVisible(True)
            self.f_status.setVisible(True)
            self.f_connect.setVisible(True)
            self.f_frameRange.setVisible(True)
            self.w_frameRangeValues.setVisible(True)
            if self.cb_manager.count() > 0:
                self.gb_submit.setVisible(True)
            if (
                self.node is None
                or self.node.type().name()
                not in ["rop_fbx", "wedge", "prism::Filecache::1.0"]
            ) and createMissing:
                self.createNode()
        elif idx == ".usd":
            self.f_cam.setVisible(False)
            self.w_sCamShot.setVisible(False)
            self.f_taskName.setVisible(True)
            self.f_status.setVisible(True)
            self.f_connect.setVisible(True)
            self.f_frameRange.setVisible(True)
            self.w_frameRangeValues.setVisible(True)
            if self.cb_manager.count() > 0:
                self.gb_submit.setVisible(True)
            if (
                self.node is None
                or self.node.type().name()
                not in ["pixar::usdrop", "usd", "wedge", "prism::Filecache::1.0"]
            ) and createMissing:
                self.createNode()
        elif idx == ".rs":
            self.f_cam.setVisible(False)
            self.w_sCamShot.setVisible(False)
            self.f_taskName.setVisible(True)
            self.f_status.setVisible(True)
            self.f_connect.setVisible(True)
            self.f_frameRange.setVisible(True)
            self.w_frameRangeValues.setVisible(True)
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
            self.f_taskName.setVisible(False)
            self.f_status.setVisible(False)
            self.f_connect.setVisible(False)
            self.f_frameRange.setVisible(True)
            self.w_frameRangeValues.setVisible(True)
            self.gb_submit.setVisible(False)
        elif idx == "other":
            self.f_cam.setVisible(False)
            self.w_sCamShot.setVisible(False)
            self.f_taskName.setVisible(True)
            self.f_status.setVisible(True)
            self.f_connect.setVisible(True)
            self.f_frameRange.setVisible(True)
            self.w_frameRangeValues.setVisible(True)
            if self.cb_manager.count() > 0:
                self.gb_submit.setVisible(True)

            from PrismUtils import PrismWidgets
            typeWin = PrismWidgets.CreateItem(core=self.core)
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
                (
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
                )
                and createMissing
                and not self.isPrismFilecacheNode(self.node)
            ):
                self.createNode()

        else:
            self.f_cam.setVisible(False)
            self.w_sCamShot.setVisible(False)
            self.f_taskName.setVisible(True)
            self.f_status.setVisible(True)
            self.f_connect.setVisible(True)
            self.f_frameRange.setVisible(True)
            self.w_frameRangeValues.setVisible(True)
            if self.cb_manager.count() > 0:
                self.gb_submit.setVisible(True)
            if (
                (
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
                )
                and createMissing
                and not self.isPrismFilecacheNode(self.node)
            ):
                self.createNode()

        self.rjToggled()
        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def goToNode(self):
        if not self.isNodeValid():
            self.createNode()

        if not self.isNodeValid():
            self.updateUi()
            return False

        self.node.setCurrent(True, clear_all_selected=True)
        paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        if paneTab is not None:
            paneTab.setCurrentNode(self.node)
            paneTab.homeToSelection()

    @staticmethod
    def isConnectableNode(node):
        typeName = node.type().name()
        cat = node.type().category().name()
        validType = typeName in [
            "rop_geometry",
            "rop_dop",
            "rop_comp",
            "rop_alembic",
            "rop_fbx",
            "filecache",
            "pixar::usdrop",
            "usd",
            "Redshift_Proxy_Output",
            "prism::Filecache::1.0",
            "vellumio",
            "vellumio::2.0"
        ] or cat == "Driver" and typeName in ["geometry", "alembic", "wedge"]
        return validType

    @err_catcher(name=__name__)
    def onConnectMenuTriggered(self, pos):
        menu = QMenu(self)
        callback = lambda node: self.connectNode(node=node)
        self.core.appPlugin.sm_openStateFromNode(
            self.stateManager, menu, stateType="Export", callback=callback
        )

        if not menu.isEmpty():
            menu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def connectNode(self, node=None):
        if node is None:
            if len(hou.selectedNodes()) == 0:
                return False

            node = hou.selectedNodes()[0]

        typeName = node.type().name()
        validType = self.isConnectableNode(node)
        if not validType:
            return False

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
        elif typeName in ["rop_geometry", "filecache", "vellumio", "vellumio::2.0"]:
            if outVal.endswith(".bgeo.sc"):
                extension = ".bgeo.sc"
            else:
                extension = os.path.splitext(outVal)[1]
        elif typeName in ["prism::Filecache::1.0"]:
            extension = node.parm("format").evalAsString()
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

        if self.cb_outType.findText(extension) != -1:
            self.cb_outType.setCurrentIndex(self.cb_outType.findText(extension))
            self.typeChanged(self.getOutputType(), createMissing=False)

        self.nameChanged(self.e_name.text())
        self.updateUi()
        if self.isPrismFilecacheNode(self.node):
            self.core.appPlugin.filecache.nodeInit(self.node, self.state)

        self.stateManager.saveStatesToScene()
        return True

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
        if self.isPrismFilecacheNode(self.node):
            if self.getRangeType() != "Node":
                self.core.appPlugin.filecache.setRangeOnNode(self.node, "From State Manager")
                rangeType = self.getRangeType()
                startFrame, endFrame = self.getFrameRange(rangeType)
                if endFrame is None:
                    endFrame = startFrame

                if startFrame != self.node.parm("f1").eval():
                    self.core.appPlugin.setNodeParm(self.node, "f1", startFrame, clear=True)

                if endFrame != self.node.parm("f2").eval():
                    self.core.appPlugin.setNodeParm(self.node, "f2", endFrame, clear=True)

        if self.sp_rangeStart.value() > self.sp_rangeEnd.value():
            self.sp_rangeEnd.setValue(self.sp_rangeStart.value())

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def endChanged(self):
        if self.isPrismFilecacheNode(self.node):
            if self.getRangeType() != "Node":
                self.core.appPlugin.filecache.setRangeOnNode(self.node, "From State Manager")
                rangeType = self.getRangeType()
                startFrame, endFrame = self.getFrameRange(rangeType)
                if endFrame is None:
                    endFrame = startFrame

                if startFrame != self.node.parm("f1").eval():
                    self.core.appPlugin.setNodeParm(self.node, "f1", startFrame, clear=True)

                if endFrame != self.node.parm("f2").eval():
                    self.core.appPlugin.setNodeParm(self.node, "f2", endFrame, clear=True)
        
        if self.sp_rangeEnd.value() < self.sp_rangeStart.value():
            self.sp_rangeStart.setValue(self.sp_rangeEnd.value())

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def useTakeChanged(self, state):
        self.cb_take.setEnabled(state)
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def rjToggled(self, checked=None):
        if checked is None:
            checked = self.gb_submit.isChecked()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def managerChanged(self, text=None):
        plugin = self.core.plugins.getRenderfarmPlugin(self.cb_manager.currentText())
        if plugin:
            plugin.sm_houExport_activated(self)

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def openSlaves(self):
        if eval(os.getenv("PRISM_DEBUG", "False")):
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
    def getRenderNode(self):
        if self.isPrismFilecacheNode(self.node):
            node = self.core.appPlugin.filecache.getRenderNode(self.node)
        else:
            node = self.node

        return node

    @err_catcher(name=__name__)
    def preDelete(self, item, silent=False):
        self.core.appPlugin.sm_preDelete(self, item, silent)

    @err_catcher(name=__name__)
    def preExecuteState(self):
        warnings = []

        if self.getOutputType() == "ShotCam":
            if self.curCam is None:
                warnings.append(["No camera specified.", "", 3])

            if str(hou.licenseCategory()) == "licenseCategoryType.Apprentice":
                warnings.append(["Shotcam exports are not supported in Houdini Apprentice.", "", 3])
        else:
            if not self.getTaskname(expanded=True):
                warnings.append(["No productname is given.", "", 3])

            if not self.isNodeValid():
                warnings.append(["Node is invalid.", "", 3])

        if self.getCurrentWedgeIndex() is not None and "wedge" not in self.core.projects.getTemplatePath("productVersions"):
            warnings.append(["A wedge index is set, but the outputpath template doesn't contain a \"wedge\" key.", "", 2])

        rangeType = self.cb_rangeType.currentText()
        startFrame, endFrame = self.getFrameRange(rangeType)

        if startFrame is None:
            warnings.append(["Framerange is invalid.", "", 3])

        if not hou.simulationEnabled():
            warnings.append(["Simulations are disabled.", "", 2])

        if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
            plugin = self.core.plugins.getRenderfarmPlugin(self.cb_manager.currentText())
            warnings += plugin.sm_houExport_preExecute(self)

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def getCurrentWedgeIndex(self):
        if self.isPrismFilecacheNode(self.node):
            if self.node.parm("wedge").eval():
                wedge = self.node.parm("wedgeNum").evalAsString()
            else:
                wedge = None
            
        else:
            wedge = hou.text.expandString("`@wedgeindex`") or None

        return wedge

    @err_catcher(name=__name__)
    def isContextSourceCooked(self):
        contextSource = self.node.parm("contextSource").evalAsString()
        if contextSource not in ["From USD stage meta data"]:
            return True

        stageNode = None

        parent = self.node.parent()
        while parent and not isinstance(parent, hou.LopNode):
            parent = parent.parent()

        if isinstance(parent, hou.LopNode):
            parent3 = parent
        else:
            parent3 = None

        if parent3 and parent3.inputs():
            stageNode = parent3.inputs()[0]

        if not stageNode:
            return True
        
        isCooked = not stageNode.needsToCook()
        return isCooked

    @err_catcher(name=__name__)
    def getOutputEntity(self, forceCook=False):
        if self.isPrismFilecacheNode(self.node):
            contextSource = self.node.parm("contextSource").evalAsString()
            entityData = None
            if contextSource == "From USD stage meta data":
                stageNode = None

                parent = self.node.parent()
                while parent and not isinstance(parent, hou.LopNode):
                    parent = parent.parent()

                if isinstance(parent, hou.LopNode):
                    parent3 = parent
                else:
                    parent3 = None

                if parent3 and parent3.inputs():
                    stageNode = parent3.inputs()[0]

                if stageNode:
                    if stageNode.needsToCook():
                        if forceCook:
                            stageNode.cook(force=True)

                        if stageNode.needsToCook():
                            entityData = self.core.configs.readJson(data=self.node.parm("customContext").eval().replace("\\", "/"), ignoreErrors=False)
                            return entityData

                    if parent3 and parent3.inputs():
                        stage = stageNode.stage()
                        if stage:
                            entityData = self.core.getPlugin("USD").api.getEntityFromStage(stage)
                else:
                    entityData = None

            elif contextSource == "Custom":
                entityData = self.core.configs.readJson(data=self.node.parm("customContext").eval().replace("\\", "/"), ignoreErrors=False)

            if contextSource == "From scenefile" or not entityData:
                if "prism_source_scene" in os.environ:
                    entityData = self.core.getScenefileData(os.getenv("prism_source_scene"))
                else:
                    fileName = self.core.getCurrentFileName()
                    entityData = self.core.getScenefileData(fileName)
        
                if "type" not in entityData:
                    return {}

                if contextSource == "From USD stage meta data" and not entityData:
                    self.core.appPlugin.filecache.setCustomContext({"node": self.node}, entityData)

        elif self.getOutputType() == "ShotCam":
            entityData = self.cb_sCamShot.currentData()
        else:
            fileName = self.core.getCurrentFileName()
            entityData = self.core.getScenefileData(fileName)

        if "username" in entityData:
            del entityData["username"]

        if "user" in entityData:
            del entityData["user"]

        if "date" in entityData:
            del entityData["date"]

        return entityData

    @err_catcher(name=__name__)
    def getOutputName(self, useVersion="next"):
        entity = self.getOutputEntity()
        location = self.cb_outPath.currentText()
        version = useVersion if useVersion != "next" else None

        task = self.getTaskname(expanded=True)
        if not task:
            return

        if self.getOutputType() == "ShotCam":
            entity["entityType"] = "shot"
            entity["type"] = "shot"
            if "asset_path" in entity:
                del entity["asset_path"]

            if "asset" in entity:
                del entity["asset"]
            
            extension = ".ext"
            framePadding = None
        else:
            rangeType = self.cb_rangeType.currentText()
            if self.isPrismFilecacheNode(self.node):
                if self.core.appPlugin.filecache.isSingleFrame(self.node):
                    rangeType = "Single Frame"

            framePadding = "$F4" if rangeType != "Single Frame" else ""
            extension = self.getOutputType()

        wedge = self.getCurrentWedgeIndex()

        outputPathData = self.core.products.generateProductPath(
            entity=entity,
            task=task,
            extension=extension,
            framePadding=framePadding,
            comment=self.stateManager.publishComment,
            version=version,
            location=location,
            returnDetails=True,
            wedge=wedge
        )

        if not outputPathData:
            return

        outputPath = outputPathData["path"].replace("\\", "/")
        outputFolder = os.path.dirname(outputPath)
        hVersion = outputPathData["version"]
        return outputPath, outputFolder, hVersion

    @err_catcher(name=__name__)
    def executeState(self, parent, useVersion="next"):
        rangeType = self.cb_rangeType.currentText()
        startFrame, endFrame = self.getFrameRange(rangeType)
        if startFrame is None:
            return [self.state.text(0) + ": error - Framerange is invalid"]

        if rangeType == "Single Frame":
            endFrame = startFrame

        if self.getCurrentWedgeIndex() is not None and "wedge" not in self.core.projects.getTemplatePath("productVersions"):
            msg = "A wedge index is set, but the outputpath template doesn't contain a \"wedge\" key.\nThe recommended default is:\n\n\"@product_path@/@version@@_(wedge)@\""
            result = self.core.popupQuestion(msg, buttons=["Update template", "Ignore", "Cancel"], icon=QMessageBox.Warning)
            if result == "Update template":
                self.core.projects.setTemplatePath("productVersions", "@product_path@/@version@@_(wedge)@")
            elif result == "Cancel":
                return [self.state.text(0) + ": error - Invalid outputpath template for wedging"]

        if self.getOutputType() == "ShotCam":
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

            if str(hou.licenseCategory()) == "licenseCategoryType.Apprentice":
                return [
                    self.state.text(0)
                    + ": error - Shotcam exports are not supported in Houdini Apprentice."
                ]

            fileName = self.core.getCurrentFileName()
            outputName, outputPath, hVersion = self.getOutputName(useVersion=useVersion)

            outLength = len(outputName)
            if platform.system() == "Windows" and os.getenv("PRISM_IGNORE_PATH_LENGTH") != "1" and outLength > 255:
                return [
                    self.state.text(0)
                    + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, productname or projectpath."
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
                if isinstance(res, dict) and res.get("cancel", False):
                    return [
                        self.state.text(0)
                        + " - error - %s" % res.get("details", "preExport hook returned False")
                    ]

                if res and "outputName" in res:
                    outputName = res["outputName"]

            outputPath = os.path.dirname(outputName)
            infoPath = self.core.products.getVersionInfoPathFromProductFilepath(
                outputName
            )
            details = (self.getOutputEntity() or {}).copy()
            if self.isPrismFilecacheNode(self.node):
                self.core.appPlugin.filecache.refreshContextFromEntity(self.node, details)

            if "filename" in details:
                del details["filename"]

            if "extension" in details:
                del details["extension"]

            details["version"] = hVersion
            details["sourceScene"] = fileName
            details["product"] = self.getTaskname(expanded=True)
            details["comment"] = self.stateManager.publishComment

            details.update(self.cb_sCamShot.currentData())
            details["entityType"] = "shot"
            details["type"] = "shot"
            if "asset_path" in details:
                del details["asset_path"]

            if startFrame != endFrame:
                details["fps"] = self.core.getFPS()

            self.core.saveVersionInfo(filepath=infoPath, details=details)

            abc_rop = self.core.appPlugin.createRop("alembic")

            abc_rop.parm("trange").set(1)
            abc_rop.parm("f1").set(startFrame)
            abc_rop.parm("f2").set(endFrame)
            abc_rop.parm("filename").set(os.path.splitext(outputName)[0] + ".abc")
            abc_rop.parm("root").set("/" + self.curCam.path().split("/", 2)[1])
            abc_rop.parm("objects").set(self.curCam.path().split("/", 2)[-1])

            fbx_rop = self.core.appPlugin.createRop("filmboxfbx")
            fbx_rop.parm("sopoutput").set(os.path.splitext(outputName)[0] + ".fbx")
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

            try:
                abc_rop.render()
            except Exception as e:
                if "Alembic export is only supported in Houdini" in str(e):
                    logger.debug("Alembic export is not available with the current Houdini license.")
                else:
                    raise

            fbx_rop.render(frame_range=(startFrame, endFrame))

            abc_rop.destroy()
            fbx_rop.destroy()

            outputName = os.path.splitext(outputName)[0] + ".abc"
            self.l_pathLast.setText(outputName)
            self.l_pathLast.setToolTip(outputName)

            useMaster = self.core.products.getUseMaster()
            if useMaster and self.getUpdateMasterVersion():
                self.core.products.updateMasterVersion(outputName)

            kwargs = {
                "state": self,
                "scenefile": fileName,
                "startframe": startFrame,
                "endframe": endFrame,
                "outputpath": outputName,
            }

            self.core.callback("postExport", **kwargs)

            self.stateManager.saveStatesToScene()

            if os.path.exists(outputName):
                return [self.state.text(0) + " - success"]
            else:
                return [self.state.text(0) + " - unknown error (files do not exist)"]

        else:
            if not self.getTaskname(expanded=True):
                return [
                    self.state.text(0)
                    + ": error - No productname is given. Skipped the activation of this state."
                ]

            if not self.isNodeValid():
                return [
                    self.state.text(0)
                    + ": error - Node is invalid. Skipped the activation of this state."
                ]

            if self.node.isInsideLockedHDA() and not self.node.isEditableInsideLockedHDA():
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
            if platform.system() == "Windows" and os.getenv("PRISM_IGNORE_PATH_LENGTH") != "1" and outLength > 255:
                return [
                    self.state.text(0)
                    + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, productname or projectpath."
                    % outLength
                ]

            if self.getOutputType() in [".abc", ".fbx", ".usd"]:
                outputName = outputName.replace(".$F4", "")

            api = self.core.appPlugin.getApiFromNode(self.node)
            isStart = ropNode.parm("f1").eval() == startFrame
            isEnd = ropNode.parm("f2").eval() == endFrame

            if not api:
                if not self.core.appPlugin.setNodeParm(ropNode, "trange", val=1):
                    return [self.state.text(0) + ": error - Publish canceled"]

            if not (api and isStart):
                if not self.core.appPlugin.setNodeParm(ropNode, "f1", clear=True):
                    return [self.state.text(0) + ": error - Publish canceled"]

                if not self.core.appPlugin.setNodeParm(ropNode, "f1", val=startFrame):
                    return [self.state.text(0) + ": error - Publish canceled"]

            if not (api and isEnd):
                if not self.core.appPlugin.setNodeParm(ropNode, "f2", clear=True):
                    return [self.state.text(0) + ": error - Publish canceled"]

                if not self.core.appPlugin.setNodeParm(ropNode, "f2", val=endFrame):
                    return [self.state.text(0) + ": error - Publish canceled"]

            if (
                ropNode.type().name()
                in [
                    "rop_geometry",
                    "rop_alembic",
                    "rop_dop",
                    "geometry",
                    "filecache",
                    "alembic",
                    "vellumio",
                    "vellumio::2.0",
                ]
                and self.initsim
            ):
                if not self.core.appPlugin.setNodeParm(ropNode, "initsim", val=True):
                    return [self.state.text(0) + ": error - Publish canceled"]

            if ropNode.type().name() in ["vellumio::2.0"]:
                if not self.core.appPlugin.setNodeParm(ropNode, "filemethod", val=1):
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
                            return [self.state.text(0) + ": error - Publish canceled"]
                else:
                    return [
                        self.state.text(0)
                        + ": error - take '%s' doesn't exist." % pTake
                    ]

            expandedOutputPath = hou.text.expandString(outputPath)
            expandedOutputName = hou.text.expandString(outputName)
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

            infoPath = self.core.products.getVersionInfoPathFromProductFilepath(
                expandedOutputName
            )

            details = (self.getOutputEntity() or {}).copy()
            if self.isPrismFilecacheNode(self.node):
                self.core.appPlugin.filecache.refreshContextFromEntity(self.node, details)

            if "filename" in details:
                del details["filename"]

            if "extension" in details:
                del details["extension"]

            details["version"] = hVersion
            details["sourceScene"] = fileName
            details["product"] = self.getTaskname(expanded=True)

            if startFrame != endFrame:
                details["fps"] = self.core.getFPS()

            self.core.saveVersionInfo(filepath=infoPath, details=details)

            outputNames = [outputName]

            self.l_pathLast.setText(outputNames[0])
            self.l_pathLast.setToolTip(outputNames[0])

            self.stateManager.saveStatesToScene()
            updateMaster = True

            for idx, outputName in enumerate(outputNames):
                outputName = outputName.replace("\\", "/")
                expandedOutputName = hou.text.expandString(outputName)
                parmName = False

                if ropNode.type().name() in self.nodeTypes:
                    parmName = self.nodeTypes[ropNode.type().name()]["outputparm"]

                if parmName is not False:
                    self.stateManager.publishInfos["updatedExports"][
                        ropNode.parm(parmName).unexpandedString()
                    ] = outputName

                    parmPath = self.core.appPlugin.getPathRelativeToProject(outputName) if self.core.appPlugin.getUseRelativePath() else outputName
                    if not self.core.appPlugin.setNodeParm(
                        ropNode, parmName, val=parmPath
                    ):
                        return [self.state.text(0) + ": error - Publish canceled"]

                if self.isPrismFilecacheNode(self.node):
                    if self.node.parm("saveScene").eval():
                        hou.hipFile.save()
                else:
                    hou.hipFile.save()

                if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
                    wasLocked = False
                    if self.isPrismFilecacheNode(self.node) and self.node.matchesCurrentDefinition():
                        self.node.allowEditingOfContents()
                        self.core.saveScene(versionUp=False, prismReq=False)
                        wasLocked = True

                    handleMaster = "product" if self.isUsingMasterVersion() else False
                    plugin = self.core.plugins.getRenderfarmPlugin(self.cb_manager.currentText())
                    result = plugin.sm_render_submitJob(self, outputName, parent, handleMaster=handleMaster, details=details)

                    if wasLocked:
                        self.node.matchCurrentDefinition()

                    updateMaster = False
                else:
                    try:
                        result = self.executeNode()
                        if result in [True, "background"]:
                            if result == "background":
                                updateMaster = False

                            if (
                                result == "background"
                                or len(os.listdir(os.path.dirname(expandedOutputName)))
                                > 1
                            ):
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

            if updateMaster:
                self.handleMasterVersion(expandedOutputName)

            kwargs = {
                "state": self,
                "scenefile": fileName,
                "startframe": startFrame,
                "endframe": endFrame,
                "outputpath": expandedOutputName,
            }

            self.core.callback("postExport", **kwargs)

            if result and "Result=Success" in result:
                return [self.state.text(0) + " - success"]
            else:
                erStr = "%s ERROR - houExportPublish %s:\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    self.core.version,
                    result,
                )
                if result == "unknown error (files do not exist)":
                    msg = "No files were created during the rendering. If you think this is a Prism bug please report it in the forum:\nwww.prism-pipeline.com/forum/\nor write a mail to contact@prism-pipeline.com"
                    self.core.popup(msg)
                elif not result or (not result.startswith(
                    "Execute Canceled"
                ) and not result.startswith("Execute failed")):
                    self.core.writeErrorLog(erStr)
                return [self.state.text(0) + " - error - " + result]

    @err_catcher(name=__name__)
    def executeNode(self):
        result = True
        if self.isPrismFilecacheNode(self.node):
            result = self.core.appPlugin.filecache.executeNode(self.node)
            errs = self.node.errors()
            if not errs:
                errs = self.core.appPlugin.filecache.getRenderNode(self.node).errors()
        else:
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
    def isUsingMasterVersion(self):
        useMaster = self.core.products.getUseMaster()
        if not useMaster:
            return False

        return useMaster and self.getUpdateMasterVersion()

    @err_catcher(name=__name__)
    def handleMasterVersion(self, outputName):
        if not self.isUsingMasterVersion():
            return

        self.core.products.updateMasterVersion(outputName)

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
            "stateName": self.e_name.text(),
            "taskname": self.getTaskname(),
            "rangeType": str(self.cb_rangeType.currentText()),
            "startframe": self.sp_rangeStart.value(),
            "endframe": self.sp_rangeEnd.value(),
            "usetake": str(self.chb_useTake.isChecked()),
            "take": self.cb_take.currentText(),
            "updateMasterVersion": self.chb_master.isChecked(),
            "curoutputpath": self.cb_outPath.currentText(),
            "outputtypes": str(outputTypes),
            "curoutputtype": self.getOutputType(),
            "connectednode": curNode,
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
            "currentcam": str(curCam),
            "currentscamshot": self.cb_sCamShot.currentText(),
            "lastexportpath": self.l_pathLast.text().replace("\\", "/"),
            "stateenabled": str(self.state.checkState(0)),
        }
        self.core.callback("onStateGetSettings", self, stateProps)
        return stateProps
