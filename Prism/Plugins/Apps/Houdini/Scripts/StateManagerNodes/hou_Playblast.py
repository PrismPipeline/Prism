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
import glob
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
        self.e_name.setText(state.text(0) + " - {identifier}")

        self.camlist = []

        self.l_name.setVisible(False)
        self.e_name.setVisible(False)

        self.sp_rangeStart.setValue(hou.playbar.playbackRange()[0])
        self.sp_rangeEnd.setValue(hou.playbar.playbackRange()[1])

        self.resolutionPresets = self.core.projects.getResolutionPresets()
        if "Cam resolution" not in self.resolutionPresets:
            self.resolutionPresets.insert(0, "Cam resolution")

        masterItems = ["Set as master", "Add to master", "Don't update master"]
        self.cb_master.addItems(masterItems)

        self.outputformats = [".jpg", ".png", ".exr", ".mp4"]
        self.cb_formats.addItems(self.outputformats)

        self.rangeTypes = ["Scene", "Shot", "Single Frame", "Custom"]
        self.cb_rangeType.addItems(self.rangeTypes)
        for idx, rtype in enumerate(self.rangeTypes):
            self.cb_rangeType.setItemData(
                idx, self.stateManager.getFrameRangeTypeToolTip(rtype), Qt.ToolTipRole
            )

        self.cb_displayMode.addItems(
            ["Smooth Shaded", "Smooth Wire Shaded", "Wireframe"]
        )
        self.f_displayMode.setVisible(False)
        self.core.callback("onStateStartup", self)

        self.connectEvents()

        self.b_changeTask.setStyleSheet(
            "QPushButton { background-color: rgb(150,0,0); border: none;}"
        )
        self.location_paths = self.core.paths.getRenderProductBasePaths()
        self.cb_location.addItems(list(self.location_paths.keys()))
        if len(self.location_paths) < 2:
            self.w_location.setVisible(False)

        self.updateUi()
        if stateData is not None:
            self.loadData(stateData)
        else:
            entity = self.getOutputEntity()
            if entity.get("type") == "asset":
                self.setRangeType("Single Frame")
            elif entity.get("type") == "shot":
                self.setRangeType("Shot")
            else:
                self.setRangeType("Scene")

            if entity.get("task"):
                self.setTaskname(entity.get("task"))

    @err_catcher(name=__name__)
    def loadData(self, data):
        if "stateName" in data:
            self.e_name.setText(data["stateName"])
        elif "statename" in data:
            self.e_name.setText(data["statename"] + " - {identifier}")
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
        if "currentcam" in data:
            idx = self.cb_cams.findText(data["currentcam"])
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
        if "location" in data:
            idx = self.cb_location.findText(data["location"])
            if idx != -1:
                self.cb_location.setCurrentIndex(idx)
        if "outputformat" in data:
            idx = self.cb_formats.findText(data["outputformat"])
            if idx > 0:
                self.cb_formats.setCurrentIndex(idx)
        if "displaymode" in data:
            idx = self.cb_displayMode.findText(data["displaymode"])
            if idx != -1:
                self.cb_displayMode.setCurrentIndex(idx)
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
        idf = self.getTaskname() or "None"
        text = self.e_name.text()
        context = {}
        context["identifier"] = idf

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
    def setTaskname(self, taskname):
        self.l_taskName.setText(taskname)
        self.nameChanged(self.e_name.text())
        if taskname:
            self.b_changeTask.setStyleSheet("")
        else:
            self.b_changeTask.setStyleSheet(
                "QPushButton { background-color: rgb(150,0,0); border: none;}"
            )
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def getTaskname(self):
        taskName = self.l_taskName.text()
        return taskName

    @err_catcher(name=__name__)
    def getSortKey(self):
        return self.getTaskname()

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

            if preset == "Cam resolution":
                pAct.triggered.connect(lambda: self.setCamResolution())
            else:
                if preset.startswith("Project ("):
                    res = preset[9:-1].split("x")
                    pwidth = int(res[0])
                    pheight = int(res[1])
                else:
                    try:
                        pwidth = int(preset.split("x")[0])
                        pheight = int(preset.split("x")[1])
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

        pmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def setCamResolution(self):
        pbCam = None

        if self.curCam is None:
            if self.core.uiAvailable:
                sceneViewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
                if sceneViewer is not None:
                    pbCam = sceneViewer.curViewport().camera()
        else:
            pbCam = self.curCam

        if pbCam is None:
            QMessageBox.warning(
                self, "Resolution Override", "No camera is selected or active."
            )
            return

        self.sp_resWidth.setValue(pbCam.parm("resx").eval())
        self.sp_resHeight.setValue(pbCam.parm("resy").eval())

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def updateUi(self):
        # update Cams
        self.cb_cams.clear()
        self.cb_cams.addItem("Don't override")
        self.camlist = self.core.appPlugin.getCamNodes(self)
        self.cb_cams.addItems([(i.name() if not self.core.isStr(i) else i) for i in self.camlist])

        if self.isCurCamValid() and self.curCam in self.camlist:
            self.cb_cams.setCurrentIndex(self.camlist.index(self.curCam) + 1)
        else:
            self.cb_cams.setCurrentIndex(0)
            self.curCam = None
            self.stateManager.saveStatesToScene()

        if not self.core.mediaProducts.getUseMaster():
            self.w_master.setVisible(False)

        self.updateRange()
        self.nameChanged(self.e_name.text())

        return True

    @err_catcher(name=__name__)
    def isCurCamValid(self):
        results = self.core.callback("houdini_validateCamera", self.curCam)
        for result in results:
            if result is not None:
                return result

        try:
            validTST = self.curCam.name()
        except:
            self.curCam = None

        return self.curCam is not None

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
    def getFrameRange(self, rangeType):
        startFrame = None
        endFrame = None
        if rangeType == "Scene":
            startFrame, endFrame = self.core.appPlugin.getFrameRange(self)
        elif rangeType == "Shot":
            entity = self.getOutputEntity()
            if entity.get("type") == "shot" and "sequence" in entity:
                frange = self.core.entities.getShotRange(entity)
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

        return startFrame, endFrame

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
    def preDelete(self, item, silent=False):
        self.core.appPlugin.sm_preDelete(self, item, silent)

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

        if self.core.uiAvailable:
            sceneViewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
            if sceneViewer is None:
                warnings.append(
                    [
                        "No Scene View exists.",
                        "A Scene View needs to be open in the Houdini user interface in order to create a playblast.",
                        3,
                    ]
                )

        if (
            hou.licenseCategory() == hou.licenseCategoryType.Apprentice
            and self.chb_resOverride.isChecked()
            and (self.sp_resWidth.value() > 1280 or self.sp_resHeight.value() > 720)
        ):
            warnings.append(
                [
                    "The apprentice version of Houdini only allows flipbooks up to 720p.",
                    "The resolution will be reduced to fit this restriction.",
                    2,
                ]
            )

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def getOutputEntity(self):
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
    def getOutputName(self, useVersion="next", extension=None):
        if not self.getTaskname():
            return

        task = self.getTaskname()
        extension = extension or self.cb_formats.currentText()
        entity = self.getOutputEntity()
        comment = self.stateManager.publishComment
        framePadding = (
            "$F4" if self.cb_rangeType.currentText() != "Single Frame" else ""
        )

        if "type" not in entity:
            return

        location = self.getLocation()
        if "version" in entity:
            del entity["version"]

        if "comment" in entity:
            del entity["comment"]

        outputPathData = self.core.mediaProducts.generatePlayblastPath(
            entity=entity,
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
        if not self.core.uiAvailable:
            return [
                self.state.text(0)
                + ": error - Playblasts are not supported without UI. Use the OpenGL ROP with an ImageRender state instead."
            ]

        if not self.getTaskname():
            return [
                self.state.text(0)
                + ": error - No identifier is given. Skipped the activation of this state."
            ]

        sceneViewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
        if sceneViewer is None:
            return [
                self.state.text(0)
                + ": error - No Scene View exists. A Scene View needs to be open in the Houdini user interface in order to create a playblast."
            ]

        if self.curCam is not None:
            if not self.isCurCamValid():
                return [
                    self.state.text(0)
                    + ": error - Camera is invalid (%s)." % self.cb_cams.currentText()
                ]

        rangeType = self.cb_rangeType.currentText()
        startFrame, endFrame = self.getFrameRange(rangeType)

        if rangeType == "Single Frame":
            endFrame = startFrame

        if startFrame is None or endFrame is None:
            return [self.state.text(0) + ": error - Framerange is invalid"]

        fileName = self.core.getCurrentFileName()
        entity = self.getOutputEntity()
        fmt = self.cb_formats.currentText()
        if fmt == ".mp4":
            fmt = ".jpg"

        outputName, outputPath, hVersion = self.getOutputName(
            useVersion=useVersion, extension=fmt
        )
        outLength = len(outputName)
        if platform.system() == "Windows" and os.getenv("PRISM_IGNORE_PATH_LENGTH") != "1" and outLength > 255:
            return [
                self.state.text(0)
                + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, identifier or projectpath."
                % outLength
            ]

        if not os.path.exists(outputPath):
            os.makedirs(outputPath)

        details = entity.copy()
        del details["filename"]
        del details["extension"]
        details["project_path"] = self.core.paths.getRenderProductBasePaths()[self.getLocation()]
        details["version"] = hVersion
        details["sourceScene"] = fileName
        details["identifier"] = self.getTaskname()
        details["comment"] = self.stateManager.publishComment

        self.core.saveVersionInfo(filepath=outputPath, details=details)

        self.updateLastPath(outputName)
        self.stateManager.saveStatesToScene()

        hou.hipFile.save()

        kwargs = {
            "state": self,
            "scenefile": fileName,
            "startframe": startFrame,
            "endframe": endFrame,
            "outputpath": outputName,
        }
        self.core.callback("prePlayblast", **kwargs)

        wasCurrentTab = None
        psettings = sceneViewer.flipbookSettings()
        forceVp = os.getenv("PRISM_HOUDINI_PLAYBLAST_USE_NEW_VIEWPORT")
        if (self.chb_resOverride.isChecked() or self.curCam or forceVp == "1") and not forceVp == "0":
            if self.chb_resOverride.isChecked():
                res = [self.sp_resWidth.value(), self.sp_resHeight.value()]
            else:
                if not self.curCam or self.core.isStr(self.curCam):
                    res = [sceneViewer.curViewport().size()[2], sceneViewer.curViewport().size()[3]]
                else:
                    res = [self.curCam.parm("resx").eval(), self.curCam.parm("resy").eval()]

            if (
                hou.licenseCategory() == hou.licenseCategoryType.Apprentice
                and (res[0] > 1280 or res[1] > 720)
            ):
                aspect = res[0] / float(res[1])
                if aspect > (1280 / float(720)):
                    res = [1280, 1280 / aspect]
                else:
                    res = [720 * aspect, 720]

            sceneViewerClone = sceneViewer.clone()
            useOcio = sceneViewer.usingOCIO()
            sceneViewerClone.setUsingOCIO(useOcio)
            forceGamma = False
            if useOcio:
                sceneViewerClone.setOCIODisplayView(display=sceneViewer.getOCIODisplay(), view="")
                # setting the view is currently bugged in Houdini 19.5.493
                # sceneViewerClone.setOCIODisplayView(display=sceneViewer.getOCIODisplay(), view=sceneViewer.getOCIOView())
            else:
                forceGamma = True
                if fmt == ".exr":
                    gamma = 1
                else:
                    gamma = sceneViewer.selectedViewport().settings().sceneGamma()
    
                sceneViewerClone.selectedViewport().settings().setSceneGamma(gamma)

            panel = sceneViewerClone.pane().floatingPanel()
            dspSet = (
                sceneViewer.curViewport()
                .settings()
                .displaySet(hou.displaySetType.SceneObject)
            )
            shdMode = hou.GeometryViewportDisplaySet.shadedMode(dspSet)

            oldSceneviewer = sceneViewer
            sceneViewer = panel.paneTabOfType(hou.paneTabType.SceneViewer)

            vis = hou.viewportVisualizers.visualizers(hou.viewportVisualizerCategory.Common)
            vis += hou.viewportVisualizers.visualizers(hou.viewportVisualizerCategory.Scene)
            for vi in vis:
                vi.setIsActive(vi.isActive(viewport=oldSceneviewer.curViewport()), viewport=sceneViewer.curViewport())

            height = int(res[1]) + 200
            ratio = float(res[0]) / float(res[1])

            if sceneViewer.curViewport().settings().camera() is None:
                panel.setSize((height, height))
                rat1 = sceneViewer.curViewport().settings().viewAspectRatio()

                panel.setSize((int(height * ratio / rat1), int(height * rat1)))
            else:
                panel.setSize((int(res[0]) + 200, int(res[1]) + 200))

            fdspSet = (
                sceneViewer.curViewport()
                .settings()
                .displaySet(hou.displaySetType.SceneObject)
            )
            fdspSet.setShadedMode(shdMode)

            psettings = sceneViewer.flipbookSettings()
            if forceGamma:
                psettings.overrideGamma(True)
                psettings.gamma(gamma)
            else:
                psettings.overrideGamma(False)

            psettings.useResolution(True)
            psettings.resolution((int(res[0]), int(res[1])))

            if oldSceneviewer.isCurrentTab():
                tabs = oldSceneviewer.pane().tabs()
                for tab in tabs:
                    if tab != oldSceneviewer and tab.type() != hou.paneTabType.SceneViewer:
                        tab.setIsCurrentTab()
                        wasCurrentTab = oldSceneviewer

        else:
            if self.chb_resOverride.isChecked():
                psettings.useResolution(True)
                width = self.sp_resWidth.value()
                height = self.sp_resHeight.value()
                psettings.resolution((int(width), int(height)))
            else:
                if self.curCam:
                    width = self.curCam.parm("resx").eval()
                    height = self.curCam.parm("resy").eval()
                    psettings.useResolution(True)
                    psettings.resolution((int(width), int(height)))
                else:
                    psettings.useResolution(False)
                    size = sceneViewer.curViewport().size()
                    width = size[2]
                    height = size[3]

            if self.cb_formats.currentText() == ".mp4" and (width % 2 or height % 2):
                psettings.useResolution(True)
                if width % 2:
                    width -= 1

                if height % 2:
                    height -= 1

                psettings.resolution((width, height))
                logger.warning("setting viewport resolution to %sx%s to create an even resolution, which is required for mp4 videos." % (width, height))

        psettings.cropOutMaskOverlay(True)

        useMplay = os.getenv("PRISM_HOUDINI_PLAYBLAST_SHOW_MPLAY")
        if useMplay == "1":
            psettings.outputToMPlay(True)
        elif useMplay == "0":
            psettings.outputToMPlay(False)

        if self.curCam is not None:
            sceneViewer.curViewport().setCamera(self.curCam)

        psettings.output(outputName)
        jobFrames = (int(startFrame), int(endFrame))
        psettings.frameRange(jobFrames)

        try:
            with self.core.timeMeasure:
                sceneViewer.flipbook()
            if "panel" in locals():
                panel.close()

            if wasCurrentTab:
                wasCurrentTab.setIsCurrentTab()

            if self.cb_formats.currentText() == ".mp4":
                if self.cb_rangeType.currentText() == "Single Frame":
                    mediaBaseName = os.path.splitext(outputName)[0] + "."
                else:
                    mediaBaseName = os.path.splitext(outputName)[0][:-3]

                files = glob.glob(mediaBaseName + "*" + os.path.splitext(outputName)[1])
                if not files or self.core.media.checkOddResolution(files[0]):
                    videoOutput = mediaBaseName + "mp4"
                    if self.cb_rangeType.currentText() == "Single Frame":
                        inputpath = outputName
                    else:
                        inputpath = (
                            os.path.splitext(outputName)[0][:-3]
                            + "%04d".replace("4", str(self.core.framePadding))
                            + os.path.splitext(outputName)[1]
                        )

                    result = self.core.media.convertMedia(
                        inputpath, jobFrames[0], videoOutput
                    )

                    self.deleteTmpJpgs(mediaBaseName)
                    if not os.path.exists(videoOutput):
                        msg = "The images could not be converted to an mp4 video."
                        self.core.ffmpegError("Image conversion", msg, result)
                        return [
                            self.state.text(0)
                            + " - error occurred during conversion of image files to mp4"
                        ]

                    if os.stat(videoOutput).st_size == 0:
                        try:
                            os.remove(videoOutput)
                        except:
                            pass

                        msg = "The images could not be converted to an mp4 video."
                        self.core.ffmpegError("Image conversion", msg, result)
                        return [
                            self.state.text(0)
                            + " - error occurred during conversion of image files to mp4"
                        ]

                    self.updateLastPath(videoOutput)
                else:
                    self.deleteTmpJpgs(mediaBaseName)
                    return [
                        self.state.text(0)
                        + " - error - Media with odd resolution can't be converted to mp4."
                    ]

            self.handleMasterVersion(outputName)
            kwargs = {
                "state": self,
                "scenefile": fileName,
                "startframe": startFrame,
                "endframe": endFrame,
                "outputpath": outputName,
            }
            self.core.callback("postPlayblast", **kwargs)

            if len(os.listdir(outputPath)) > 0:
                return [self.state.text(0) + " - success"]
            else:
                return [self.state.text(0) + " - unknown error (files do not exist)"]
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            erStr = "%s ERROR - houPlayblast %s:\n%s" % (
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
        fmt = self.cb_formats.currentText()
        if fmt == ".mp4":
            fmt = ".jpg"

        for i in os.listdir(os.path.dirname(mediaBaseName)):
            if i.startswith(os.path.basename(mediaBaseName)) and i.endswith(
                fmt
            ):
                delFiles.append(os.path.join(os.path.dirname(mediaBaseName), i))

        for i in delFiles:
            try:
                os.remove(i)
            except:
                pass

    @err_catcher(name=__name__)
    def handleMasterVersion(self, outputName):
        useMaster = self.core.mediaProducts.getUseMaster()
        if not useMaster:
            return

        masterAction = self.cb_master.currentText()
        if masterAction == "Don't update master":
            return

        elif masterAction == "Set as master":
            self.core.mediaProducts.updateMasterVersion(outputName, mediaType="playblasts")
        elif masterAction == "Add to master":
            self.core.mediaProducts.addToMasterVersion(outputName)

    @err_catcher(name=__name__)
    def getStateProps(self):
        stateProps = {
            "stateName": self.e_name.text(),
            "taskname": self.getTaskname(),
            "rangeType": str(self.cb_rangeType.currentText()),
            "startframe": self.sp_rangeStart.value(),
            "endframe": self.sp_rangeEnd.value(),
            "currentcam": self.cb_cams.currentText(),
            "resoverride": str(
                [
                    self.chb_resOverride.isChecked(),
                    self.sp_resWidth.value(),
                    self.sp_resHeight.value(),
                ]
            ),
            "displaymode": self.cb_displayMode.currentText(),
            "masterVersion": self.cb_master.currentText(),
            "location": self.cb_location.currentText(),
            "outputformat": str(self.cb_formats.currentText()),
            "lastexportpath": self.l_pathLast.text().replace("\\", "/"),
            "stateenabled": str(self.state.checkState(0)),
        }
        self.core.callback("onStateGetSettings", self, stateProps)
        return stateProps
