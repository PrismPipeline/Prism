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

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


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
        self.customContext = None
        self.allowCustomContext = False

        self.e_name.setText(state.text(0) + " ({product})")

        self.l_name.setVisible(False)
        self.e_name.setVisible(False)
        self.gb_submit.setChecked(False)

        self.cb_context.addItems(["From scenefile", "Custom"])
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

        self.rangeTypes = ["Scene", "Shot", "Single Frame", "Custom"]
        self.cb_rangeType.addItems(self.rangeTypes)
        for idx, rtype in enumerate(self.rangeTypes):
            self.cb_rangeType.setItemData(
                idx, self.stateManager.getFrameRangeTypeToolTip(rtype), Qt.ToolTipRole
            )

        if self.stateManager.standalone:
            outputFormats = []
            if self.core.appPlugin.pluginName != "Houdini" and hasattr(self.core.appPlugin, "outputFormats"):
                outputFormats += list(self.core.appPlugin.outputFormats)

            for i in self.core.unloadedAppPlugins.values():
                if i.pluginName != "Houdini":
                    outputFormats += getattr(i, "outputFormats", [])
            outputFormats = sorted(set(outputFormats))
        else:
            outputFormats = getattr(self.core.appPlugin, "outputFormats", [])

        self.cb_outType.addItems(outputFormats)
        self.export_paths = self.core.paths.getExportProductBasePaths()
        self.cb_outPath.addItems(list(self.export_paths.keys()))
        if len(self.export_paths) < 2:
            self.w_outPath.setVisible(False)
        getattr(self.core.appPlugin, "sm_export_startup", lambda x: None)(self)
        self.nameChanged(state.text(0))
        self.connectEvents()

        if hasattr(self, "gb_submit"):
            self.gb_submit.setVisible(False)
            self.cb_manager.addItems([p.pluginName for p in self.core.plugins.getRenderfarmPlugins()])
        
        self.core.callback("onStateStartup", self)
        self.f_rjWidgetsPerTask.setVisible(False)
        self.managerChanged(True)

        if stateData is not None:
            self.loadData(stateData)
        else:
            context = self.getCurrentContext()
            if (
                context.get("type") == "shot"
                and "sequence" in context
            ):
                self.refreshShotCameras()
                shotName = self.core.entities.getShotName(context)
                idx = self.cb_sCamShot.findText(shotName)
                if idx != -1:
                    self.cb_sCamShot.setCurrentIndex(idx)

            startFrame, endFrame = self.getFrameRange("Scene")
            if startFrame is not None:
                self.sp_rangeStart.setValue(startFrame)

            if endFrame is not None:
                self.sp_rangeEnd.setValue(endFrame)

            if context.get("type") == "asset":
                self.setRangeType("Single Frame")
                self.sp_rangeEnd.setValue(startFrame)
            elif context.get("type") == "shot":
                self.setRangeType("Shot")
            elif self.stateManager.standalone:
                self.setRangeType("Custom")
            else:
                self.setRangeType("Scene")

            if context.get("task"):
                self.setTaskname(context.get("task"))

            getattr(self.core.appPlugin, "sm_export_updateObjects", lambda x: None)(
                self
            )

            if not self.stateManager.standalone:
                self.addObjects()

        self.typeChanged(self.getOutputType())

    @err_catcher(name=__name__)
    def loadData(self, data):
        if "contextType" in data:
            self.setContextType(data["contextType"])
        if "customContext" in data:
            self.customContext = data["customContext"]
        if "taskname" in data:
            self.setTaskname(data["taskname"])
        if "connectednodes" in data:
            self.nodes = eval(data["connectednodes"])

        self.updateUi()

        if "stateName" in data:
            self.e_name.setText(data["stateName"])
        elif "statename" in data:
            self.e_name.setText(data["statename"] + " ({product})")
        if "rangeType" in data:
            idx = self.cb_rangeType.findText(data["rangeType"])
            if idx != -1:
                self.cb_rangeType.setCurrentIndex(idx)
                self.updateRange()
        if "startframe" in data:
            self.sp_rangeStart.setValue(int(data["startframe"]))
        if "endframe" in data:
            self.sp_rangeEnd.setValue(int(data["endframe"]))
        if "updateMasterVersion" in data:
            self.chb_master.setChecked(data["updateMasterVersion"])
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
            self.setLastPath(lePath)
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
        self.core.callback("onStateSettingsLoaded", self, data)

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.cb_context.activated.connect(self.onContextTypeChanged)
        self.b_context.clicked.connect(self.selectContextClicked)
        self.b_changeTask.clicked.connect(self.changeTask)
        self.cb_rangeType.activated.connect(self.rangeTypeChanged)
        self.sp_rangeStart.editingFinished.connect(self.startChanged)
        self.sp_rangeEnd.editingFinished.connect(self.endChanged)
        self.chb_master.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.cb_outPath.activated[str].connect(self.stateManager.saveStatesToScene)
        self.cb_outType.activated[str].connect(self.typeChanged)
        self.chb_wholeScene.stateChanged.connect(self.wholeSceneChanged)
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
        if not self.stateManager.standalone:
            self.b_add.clicked.connect(self.addObjects)
        self.b_pathLast.clicked.connect(self.showLastPathMenu)

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
    def selectContextClicked(self):
        self.dlg_entity = self.stateManager.entityDlg(self)
        data = self.getCurrentContext()
        self.dlg_entity.w_entities.navigate(data)
        self.dlg_entity.entitySelected.connect(lambda x: self.setCustomContext(x))
        self.dlg_entity.show()

    @err_catcher(name=__name__)
    def setCustomContext(self, context):
        self.customContext = context
        self.refreshContext()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def onContextTypeChanged(self, state):
        self.refreshContext()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def rangeTypeChanged(self, state):
        self.updateRange()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def wholeSceneChanged(self, state):
        if self.w_wholeScene.isHidden():
            enabled = True
        else:
            enabled = not state == Qt.Checked

        self.gb_objects.setEnabled(enabled)
        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def nameChanged(self, text):
        text = self.e_name.text()
        context = {}
        if self.getOutputType() == "ShotCam":
            context["product"] = "ShotCam - %s" % self.cb_cam.currentText()
        else:
            context["product"] = self.getTaskname() or "None"

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
    def getUpdateMasterVersion(self):
        return self.chb_master.isChecked()

    @err_catcher(name=__name__)
    def setUpdateMasterVersion(self, master):
        self.chb_master.setChecked(master)

    @err_catcher(name=__name__)
    def getOutputType(self):
        return self.cb_outType.currentText()

    @err_catcher(name=__name__)
    def setOutputType(self, outType):
        idx = self.cb_outType.findText(outType)
        if idx != -1:
            self.cb_outType.setCurrentIndex(idx)

    @err_catcher(name=__name__)
    def getContextType(self):
        contextType = self.cb_context.currentText()
        return contextType

    @err_catcher(name=__name__)
    def setContextType(self, contextType):
        idx = self.cb_context.findText(contextType)
        if idx != -1:
            self.cb_context.setCurrentIndex(idx)
            self.refreshContext()
            return True

        return False

    @err_catcher(name=__name__)
    def getTaskname(self):
        if self.getOutputType() == "ShotCam":
            taskName = "_ShotCam"
        else:
            taskName = self.l_taskName.text()

        return taskName

    @err_catcher(name=__name__)
    def setTaskname(self, taskname):
        prevTaskName = self.getTaskname()
        default_func = lambda x1, x2, newTaskName: taskname
        taskname = getattr(self.core.appPlugin, "sm_export_setTaskText", default_func)(
            self, prevTaskName, taskname
        )
        self.l_taskName.setText(taskname)
        self.updateUi()
        return taskname

    @err_catcher(name=__name__)
    def getSortKey(self):
        return self.getTaskname()

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
            self.setTaskname(self.nameWin.e_item.text())
            self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def preDelete(self, item):
        self.core.appPlugin.sm_export_preDelete(self)

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
        self.updateObjectList()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def removeItem(self, item):
        items = self.lw_objects.selectedItems()
        for item in reversed(items):
            rowNum = self.lw_objects.row(item)
            self.core.appPlugin.sm_export_removeSetItem(self, self.nodes[rowNum])
            del self.nodes[rowNum]
            self.lw_objects.takeItem(rowNum)

        self.updateObjectList()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def clearItems(self):
        self.lw_objects.clear()
        self.nodes = []
        if not self.stateManager.standalone:
            getattr(self.core.appPlugin, "sm_export_clearSet", lambda x: None)(self)

        self.updateObjectList()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def refreshShotCameras(self):
        curShot = self.cb_sCamShot.currentText()
        self.cb_sCamShot.clear()
        _, shots = self.core.entities.getShots()
        for shot in sorted(shots, key=lambda s: self.core.entities.getShotName(s).lower()):
            shotData = {"type": "shot", "sequence": shot["sequence"], "shot": shot["shot"]}
            shotName = self.core.entities.getShotName(shot)
            self.cb_sCamShot.addItem(shotName, shotData)

        idx = self.cb_sCamShot.findText(curShot)
        if idx != -1:
            self.cb_sCamShot.setCurrentIndex(idx)
        else:
            self.cb_sCamShot.setCurrentIndex(0)
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

        if not self.core.products.getUseMaster():
            self.w_master.setVisible(False)

        self.w_context.setHidden(not self.allowCustomContext)
        self.refreshContext()
        self.updateRange()
        self.refreshShotCameras()
        self.updateObjectList()
        if self.getTaskname():
            self.b_changeTask.setPalette(self.oldPalette)

        self.refreshSubmitUi()
        self.nameChanged(self.e_name.text())
        self.core.callback("sm_export_updateUi", self)

    @err_catcher(name=__name__)
    def updateObjectList(self):
        selObjects = [x.text() for x in self.lw_objects.selectedItems()]
        self.lw_objects.clear()

        newObjList = []
        getattr(self.core.appPlugin, "sm_export_updateObjects", lambda x: None)(self)
        if not self.stateManager.standalone:
            for node in self.nodes:
                if self.core.appPlugin.isNodeValid(self, node):
                    item = QListWidgetItem(self.core.appPlugin.getNodeName(self, node))
                    self.lw_objects.addItem(item)
                    newObjList.append(node)

        self.updateObjectListStyle()
        for i in range(self.lw_objects.count()):
            if self.lw_objects.item(i).text() in selObjects:
                self.lw_objects.item(i).setSelected(True)

        self.nodes = newObjList

    @err_catcher(name=__name__)
    def refreshContext(self):
        context = self.getCurrentContext()
        contextStr = self.getContextStrFromEntity(context)
        self.l_context.setText(contextStr)
        if contextStr:
            self.b_context.setPalette(self.oldPalette)
        else:
            self.b_context.setPalette(self.warnPalette)

    @err_catcher(name=__name__)
    def getCurrentContext(self):
        context = None
        if self.allowCustomContext:
            ctype = self.getContextType()
            if ctype == "Custom":
                context = self.customContext

        if not context:
            if self.getOutputType() == "ShotCam":
                context = self.cb_sCamShot.currentData()
            else:
                fileName = self.core.getCurrentFileName()
                context = self.core.getScenefileData(fileName)

        if "username" in context:
            del context["username"]

        if "user" in context:
            del context["user"]

        return context

    @err_catcher(name=__name__)
    def updateObjectListStyle(self, warn=True):
        if self.lw_objects.count() == 0 and not self.chb_wholeScene.isChecked() and self.lw_objects.isEnabled():
            self.setObjectListStyle(warn=True)
        else:
            self.setObjectListStyle(warn=False)

    @err_catcher(name=__name__)
    def setObjectListStyle(self, warn=True):
        if warn:
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
                    "QListWidget { border: 3px solid rgba(114,114,114,0); }"
                ),
            )(self)

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
    def rjToggled(self, checked):
        self.refreshSubmitUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def managerChanged(self, text=None):
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def setLastPath(self, path):
        self.l_pathLast.setText(path)
        self.l_pathLast.setToolTip(path)
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def getContextStrFromEntity(self, entity):
        if not entity:
            return ""

        entityType = entity.get("type", "")
        if entityType == "asset":
            entityName = entity.get("asset_path", "").replace("\\", "/")
        elif entityType == "shot":
            entityName = self.core.entities.getShotName(entity)
        else:
            return ""

        context = "%s - %s" % (entityType.capitalize(), entityName)
        return context

    @err_catcher(name=__name__)
    def preExecuteState(self):
        warnings = []

        rangeType = self.cb_rangeType.currentText()
        startFrame, endFrame = self.getFrameRange(rangeType)

        if self.getOutputType() == "ShotCam":
            if self.curCam is None:
                warnings.append(["No camera specified.", "", 3])
        else:
            if not self.getTaskname():
                warnings.append(["No productname is given.", "", 3])

            if not self.chb_wholeScene.isChecked() and len(self.nodes) == 0:
                warnings.append(["No objects are selected for export.", "", 3])

        if startFrame is None:
            warnings.append(["Framerange is invalid.", "", 3])

        warnings += self.core.appPlugin.sm_export_preExecute(self, startFrame, endFrame)

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def getOutputName(self, useVersion="next"):
        context = self.getCurrentContext()
        location = self.cb_outPath.currentText()
        version = useVersion if useVersion != "next" else None
        if "type" not in context:
            return

        task = self.getTaskname()
        if not task:
            return

        if self.getOutputType() == "ShotCam":
            context["entityType"] = "shot"
            context["type"] = "shot"
            if "asset_path" in context:
                del context["asset_path"]

            if "asset" in context:
                del context["asset"]

            extension = ""
            framePadding = None
        else:
            rangeType = self.cb_rangeType.currentText()
            extension = self.getOutputType()

            if rangeType == "Single Frame" or extension != ".obj":
                framePadding = ""
            else:
                framePadding = "#" * self.core.framePadding

        outputPathData = self.core.products.generateProductPath(
            entity=context,
            task=task,
            extension=extension,
            framePadding=framePadding,
            comment=self.stateManager.publishComment,
            version=version,
            location=location,
            returnDetails=True,
        )

        outputFolder = os.path.dirname(outputPathData["path"])
        hVersion = outputPathData["version"]

        return outputPathData["path"], outputFolder, hVersion

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
    def executeState(self, parent, useVersion="next"):
        rangeType = self.cb_rangeType.currentText()
        startFrame, endFrame = self.getFrameRange(rangeType)
        if startFrame is None:
            return [self.state.text(0) + ": error - Framerange is invalid"]

        if rangeType == "Single Frame":
            endFrame = startFrame

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

            fileName = self.core.getCurrentFileName()
            context = self.getCurrentContext()
            outputName, outputPath, hVersion = self.getOutputName(useVersion=useVersion)

            outLength = len(outputName)
            if platform.system() == "Windows" and os.getenv("PRISM_IGNORE_PATH_LENGTH") != "1" and outLength > 255:
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
                if isinstance(res, dict) and res.get("cancel", False):
                    return [
                        self.state.text(0)
                        + " - error - %s" % res.get("details", "preExport hook returned False")
                    ]

                if res and "outputName" in res:
                    outputName = res["outputName"]

            outputPath = os.path.dirname(outputName)
            if not os.path.exists(outputPath):
                os.makedirs(outputPath)

            details = context.copy()
            if "filename" in details:
                del details["filename"]

            if "extension" in details:
                del details["extension"]

            details["version"] = hVersion
            details["sourceScene"] = fileName
            details["product"] = self.getTaskname()
            details["resolution"] = self.core.appPlugin.getResolution()
            details["comment"] = self.stateManager.publishComment

            details.update(self.cb_sCamShot.currentData())
            details["entityType"] = "shot"
            details["type"] = "shot"
            if "asset_path" in details:
                del details["asset_path"]

            if startFrame != endFrame:
                details["fps"] = self.core.getFPS()

            infoPath = self.core.products.getVersionInfoPathFromProductFilepath(
                outputName
            )
            self.core.saveVersionInfo(filepath=infoPath, details=details)

            self.core.appPlugin.sm_export_exportShotcam(
                self, startFrame=startFrame, endFrame=endFrame, outputName=outputName
            )

            outputName += ".abc"
            self.setLastPath(outputName)

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

            result = self.core.callback("postExport", **kwargs)
            validateOutput = True
            for res in result:
                if isinstance(res, dict) and res.get("cancel", False):
                    return [
                        self.state.text(0)
                        + " - error - %s" % res.get("details", "postExport hook returned False")
                    ]

                if res and "outputName" in res:
                    outputName = res["outputName"]

                if res and "validateOutput" in res:
                    validateOutput = res["validateOutput"]

            self.stateManager.saveStatesToScene()

            if not validateOutput or os.path.exists(outputName):
                return [self.state.text(0) + " - success"]
            else:
                return [self.state.text(0) + " - unknown error"]
        else:

            if not self.getTaskname():
                return [
                    self.state.text(0)
                    + ": error - No productname is given. Skipped the activation of this state."
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
            context = self.getCurrentContext()
            outputName, outputPath, hVersion = self.getOutputName(useVersion=useVersion)

            outLength = len(outputName)
            if platform.system() == "Windows" and os.getenv("PRISM_IGNORE_PATH_LENGTH") != "1" and outLength > 255:
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
                if isinstance(res, dict) and res.get("cancel", False):
                    return [
                        self.state.text(0)
                        + " - error - %s" % res.get("details", "preExport hook returned False")
                    ]
                
                if res and "outputName" in res:
                    outputName = res["outputName"]

            outputPath = os.path.dirname(outputName)
            if not os.path.exists(outputPath):
                os.makedirs(outputPath)

            details = context.copy()
            if "filename" in details:
                del details["filename"]

            if "extension" in details:
                del details["extension"]

            details["version"] = hVersion
            details["sourceScene"] = fileName
            details["product"] = self.getTaskname()

            if startFrame != endFrame:
                details["fps"] = self.core.getFPS()

            infoPath = self.core.products.getVersionInfoPathFromProductFilepath(
                outputName
            )
            self.core.saveVersionInfo(filepath=infoPath, details=details)
            updateMaster = True
            try:
                if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
                    handleMaster = "product" if self.isUsingMasterVersion() else False
                    plugin = self.core.plugins.getRenderfarmPlugin(self.cb_manager.currentText())
                    submitResult = plugin.sm_render_submitJob(self, outputName, parent, handleMaster=handleMaster, details=details)
                    updateMaster = False
                else:
                    outputName = self.core.appPlugin.sm_export_exportAppObjects(
                        self,
                        startFrame=startFrame,
                        endFrame=endFrame,
                        outputName=outputName,
                    )

                    if not outputName:
                        return [self.state.text(0) + " - error"]

                    if outputName.startswith("Canceled"):
                        return [self.state.text(0) + " - error: %s" % outputName]

                logger.debug("exported to: %s" % outputName)
                self.setLastPath(outputName)
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

            if updateMaster:
                self.handleMasterVersion(outputName)

            kwargs = {
                "state": self,
                "scenefile": fileName,
                "startframe": startFrame,
                "endframe": endFrame,
                "outputpath": outputName,
            }

            result = self.core.callback("postExport", **kwargs)
            validateOutput = True
            for res in result:
                if res:
                    if res and "outputName" in res:
                        outputName = res["outputName"]

                    if res and "validateOutput" in res:
                        validateOutput = res["validateOutput"]

            if not self.gb_submit.isHidden() and self.gb_submit.isChecked() and "Result=Success" in submitResult:
                return [self.state.text(0) + " - success"]
            elif os.path.exists(outputName) or not validateOutput:
                return [self.state.text(0) + " - success"]
            else:
                return [self.state.text(0) + " - unknown error (files do not exist)"]

    @err_catcher(name=__name__)
    def getStateProps(self):
        stateProps = {}

        nodes = []
        if not self.stateManager.standalone:
            for node in self.nodes:
                if self.core.appPlugin.isNodeValid(self, node):
                    nodes.append(node)

        stateProps.update(
            {
                "stateName": self.e_name.text(),
                "contextType": self.getContextType(),
                "customContext": self.customContext,
                "taskname": self.getTaskname(),
                "rangeType": str(self.cb_rangeType.currentText()),
                "startframe": self.sp_rangeStart.value(),
                "endframe": self.sp_rangeEnd.value(),
                "additionaloptions": str(self.chb_additionalOptions.isChecked()),
                "updateMasterVersion": self.chb_master.isChecked(),
                "curoutputpath": self.cb_outPath.currentText(),
                "curoutputtype": self.getOutputType(),
                "wholescene": str(self.chb_wholeScene.isChecked()),
                "connectednodes": str(nodes),
                "currentcam": str(self.curCam),
                "currentscamshot": self.cb_sCamShot.currentText(),
                "submitrender": str(self.gb_submit.isChecked()),
                "rjmanager": str(self.cb_manager.currentText()),
                "rjprio": self.sp_rjPrio.value(),
                "rjframespertask": self.sp_rjFramesPerTask.value(),
                "rjtimeout": self.sp_rjTimeout.value(),
                "rjsuspended": str(self.chb_rjSuspended.isChecked()),
                "dlconcurrent": self.sp_dlConcurrentTasks.value(),
                "lastexportpath": self.l_pathLast.text().replace("\\", "/"),
                "stateenabled": str(self.state.checkState(0)),
            }
        )
        getattr(self.core.appPlugin, "sm_export_getStateProps", lambda x, y: None)(
            self, stateProps
        )
        self.core.callback("onStateGetSettings", self, stateProps)
        return stateProps
