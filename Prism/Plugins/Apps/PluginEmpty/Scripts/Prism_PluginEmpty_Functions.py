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
# Copyright (C) 2016-2019 Richard Frangenberg
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


import os, sys
import traceback, time, shutil, platform
from functools import wraps

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1


class Prism_PluginEmpty_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            exc_info = sys.exc_info()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = (
                    "%s ERROR - Prism_Plugin_PluginEmpty - Core: %s - Plugin: %s:\n%s\n\n%s"
                    % (
                        time.strftime("%d/%m/%y %X"),
                        args[0].core.version,
                        args[0].plugin.version,
                        "".join(traceback.format_stack()),
                        traceback.format_exc(),
                    )
                )
                args[0].core.writeErrorLog(erStr)

        return func_wrapper

    @err_decorator
    def startup(self, origin):
        # 	for obj in qApp.topLevelWidgets():
        # 		if obj.objectName() == 'PluginEmptyWindow':
        # 			QtParent = obj
        # 			break
        # 	else:
        # 		return False

        origin.timer.stop()

        origin.messageParent = QWidget()
        # 	origin.messageParent.setParent(QtParent, Qt.Window)
        if self.core.useOnTop:
            origin.messageParent.setWindowFlags(
                origin.messageParent.windowFlags() ^ Qt.WindowStaysOnTopHint
            )

        origin.startasThread()

    @err_decorator
    def autosaveEnabled(self, origin):
        # get autosave enabled
        return False

    @err_decorator
    def onProjectChanged(self, origin):
        pass

    @err_decorator
    def sceneOpen(self, origin):
        if hasattr(origin, "asThread") and origin.asThread.isRunning():
            origin.startasThread()

    @err_decorator
    def executeScript(self, origin, code, execute=False, logErr=True):
        if logErr:
            try:
                if not execute:
                    return eval(code)
                else:
                    exec(code)
            except Exception as e:
                msg = "\npython code:\n%s" % code
                exec("raise type(e), type(e)(e.message + msg), sys.exc_info()[2]")
        else:
            try:
                if not execute:
                    return eval(code)
                else:
                    exec(code)
            except:
                pass

    @err_decorator
    def getCurrentFileName(self, origin, path=True):
        return ""

    @err_decorator
    def getSceneExtension(self, origin):
        return self.sceneFormats[0]

    @err_decorator
    def saveScene(self, origin, filepath, details={}):
        # save scenefile
        return True

    @err_decorator
    def getImportPaths(self, origin):
        return []

    @err_decorator
    def getFrameRange(self, origin):
        startframe = 0
        endframe = 100

        return [startframe, endframe]

    @err_decorator
    def setFrameRange(self, origin, startFrame, endFrame):
        pass

    @err_decorator
    def getFPS(self, origin):
        return 24

    @err_decorator
    def setFPS(self, origin, fps):
        pass

    @err_decorator
    def getAppVersion(self, origin):
        return "1.0"

    @err_decorator
    def onProjectBrowserStartup(self, origin):
        origin.loadOiio()
        # 	origin.sl_preview.mousePressEvent = origin.sliderDrag
        origin.sl_preview.mousePressEvent = origin.sl_preview.origMousePressEvent

    @err_decorator
    def projectBrowserLoadLayout(self, origin):
        pass

    @err_decorator
    def setRCStyle(self, origin, rcmenu):
        pass

    @err_decorator
    def openScene(self, origin, filepath, force=False):
        # load scenefile
        return True

    @err_decorator
    def correctExt(self, origin, lfilepath):
        return lfilepath

    @err_decorator
    def setSaveColor(self, origin, btn):
        btn.setPalette(origin.savedPalette)

    @err_decorator
    def clearSaveColor(self, origin, btn):
        btn.setPalette(origin.oldPalette)

    @err_decorator
    def setProject_loading(self, origin):
        pass

    @err_decorator
    def onPrismSettingsOpen(self, origin):
        pass

    @err_decorator
    def createProject_startup(self, origin):
        pass

    @err_decorator
    def editShot_startup(self, origin):
        origin.loadOiio()

    @err_decorator
    def shotgunPublish_startup(self, origin):
        pass

    @err_decorator
    def sm_export_addObjects(self, origin):
        selectedObjects = []  # get selected objects from scene
        for i in selectedObjects:
            if not i in origin.nodes:
                origin.nodes.append(i)

        origin.updateUi()
        origin.stateManager.saveStatesToScene()

    @err_decorator
    def getNodeName(self, origin, node):
        if self.isNodeValid(origin, node):
            try:
                return node.name
            except:
                QMessageBox.warning(
                    self.core.messageParent, "Warning", "Cannot get name from %s" % node
                )
                return node
        else:
            return "invalid"

    @err_decorator
    def selectNodes(self, origin):
        if origin.lw_objects.selectedItems() != []:
            nodes = []
            for i in origin.lw_objects.selectedItems():
                node = origin.nodes[origin.lw_objects.row(i)]
                if self.isNodeValid(origin, node):
                    nodes.append(node)
            # select(nodes)

    @err_decorator
    def isNodeValid(self, origin, handle):
        return True

    @err_decorator
    def getCamNodes(self, origin, cur=False):
        sceneCams = []  # get cams from scene
        if cur:
            sceneCams = ["Current View"] + sceneCams

        return sceneCams

    @err_decorator
    def getCamName(self, origin, handle):
        if handle == "Current View":
            return handle

        return str(nodes[0])

    @err_decorator
    def selectCam(self, origin):
        if self.isNodeValid(origin, origin.curCam):
            select(origin.curCam)

    @err_decorator
    def sm_export_startup(self, origin):
        pass

    # 	@err_decorator
    # 	def sm_export_setTaskText(self, origin, prevTaskName, newTaskName):
    # 		origin.l_taskName.setText(newTaskName)

    @err_decorator
    def sm_export_removeSetItem(self, origin, node):
        pass

    @err_decorator
    def sm_export_clearSet(self, origin):
        pass

    @err_decorator
    def sm_export_updateObjects(self, origin):
        pass

    @err_decorator
    def sm_export_exportShotcam(self, origin, startFrame, endFrame, outputName):
        result = self.sm_export_exportAppObjects(
            origin,
            startFrame,
            endFrame,
            (outputName + ".abc"),
            nodes=[origin.curCam],
            expType=".abc",
        )
        result = self.sm_export_exportAppObjects(
            origin,
            startFrame,
            endFrame,
            (outputName + ".fbx"),
            nodes=[origin.curCam],
            expType=".fbx",
        )
        return result

    @err_decorator
    def sm_export_exportAppObjects(
        self,
        origin,
        startFrame,
        endFrame,
        outputName,
        scaledExport=False,
        nodes=None,
        expType=None,
    ):
        pass

    @err_decorator
    def sm_export_preDelete(self, origin):
        pass

    @err_decorator
    def sm_export_unColorObjList(self, origin):
        origin.lw_objects.setStyleSheet(
            "QListWidget { border: 3px solid rgb(50,50,50); }"
        )

    @err_decorator
    def sm_export_typeChanged(self, origin, idx):
        pass

    @err_decorator
    def sm_export_preExecute(self, origin, startFrame, endFrame):
        warnings = []

        return warnings

    @err_decorator
    def sm_export_loadData(self, origin, data):
        pass

    @err_decorator
    def sm_export_getStateProps(self, origin):
        stateProps = {}

        return stateProps

    @err_decorator
    def sm_render_isVray(self, origin):
        return False

    @err_decorator
    def sm_render_setVraySettings(self, origin):
        pass

    @err_decorator
    def sm_render_startup(self, origin):
        pass

    @err_decorator
    def sm_render_getRenderLayer(self, origin):
        rlayerNames = []

        return rlayerNames

    @err_decorator
    def sm_render_refreshPasses(self, origin):
        pass

    @err_decorator
    def sm_render_openPasses(self, origin, item=None):
        pass

    @err_decorator
    def sm_render_deletePass(self, origin, item):
        pass

    @err_decorator
    def sm_render_preSubmit(self, origin, rSettings):
        pass

    @err_decorator
    def sm_render_startLocalRender(self, origin, outputName, rSettings):
        pass

    @err_decorator
    def sm_render_undoRenderSettings(self, origin, rSettings):
        pass

    @err_decorator
    def sm_render_getDeadlineParams(self, origin, dlParams, homeDir):
        pass

    @err_decorator
    def getCurrentRenderer(self, origin):
        return "Renderer"

    @err_decorator
    def getCurrentSceneFiles(self, origin):
        curFileName = self.core.getCurrentFileName()
        scenefiles = [curFileName]
        return scenefiles

    @err_decorator
    def sm_render_getRenderPasses(self, origin):
        return []

    @err_decorator
    def sm_render_addRenderPass(self, origin, passName, steps):
        pass

    @err_decorator
    def sm_render_preExecute(self, origin):
        warnings = []

        return warnings

    @err_decorator
    def sm_render_fixOutputPath(self, origin, outputName):
        return outputName

    @err_decorator
    def getProgramVersion(self, origin):
        return "1.0"

    @err_decorator
    def sm_render_getDeadlineSubmissionParams(self, origin, dlParams, jobOutputFile):
        dlParams["Build"] = dlParams["build"]
        dlParams["OutputFilePath"] = os.path.split(jobOutputFile)[0]
        dlParams["OutputFilePrefix"] = os.path.splitext(
            os.path.basename(jobOutputFile)
        )[0]
        dlParams["Renderer"] = self.getCurrentRenderer(origin)

        if origin.chb_resOverride.isChecked() and "resolution" in dlParams:
            resString = "Image"
            dlParams[resString + "Width"] = str(origin.sp_resWidth.value())
            dlParams[resString + "Height"] = str(origin.sp_resHeight.value())

        return dlParams

    @err_decorator
    def deleteNodes(self, origin, handles, num=0):
        pass

    @err_decorator
    def sm_import_startup(self, origin):
        pass

    @err_decorator
    def sm_import_disableObjectTracking(self, origin):
        self.deleteNodes(origin, [origin.setName])

    @err_decorator
    def sm_import_importToApp(self, origin, doImport, update, impFileName):
        return {"result": result, "doImport": doImport}

    @err_decorator
    def sm_import_updateObjects(self, origin):
        pass

    @err_decorator
    def sm_import_removeNameSpaces(self, origin):
        pass

    @err_decorator
    def sm_import_unitConvert(self, origin):
        pass

    @err_decorator
    def sm_playblast_startup(self, origin):
        frange = self.getFrameRange(origin)
        origin.sp_rangeStart.setValue(frange[0])
        origin.sp_rangeEnd.setValue(frange[1])

    @err_decorator
    def sm_playblast_createPlayblast(self, origin, jobFrames, outputName):
        pass

    @err_decorator
    def sm_playblast_preExecute(self, origin):
        warnings = []

        return warnings

    @err_decorator
    def sm_playblast_execute(self, origin):
        pass

    @err_decorator
    def sm_playblast_postExecute(self, origin):
        pass

    @err_decorator
    def onStateManagerOpen(self, origin):
        pass

    @err_decorator
    def sm_saveStates(self, origin, buf):
        pass

    @err_decorator
    def sm_saveImports(self, origin, importPaths):
        pass

    @err_decorator
    def sm_readStates(self, origin):
        return []

    @err_decorator
    def sm_deleteStates(self, origin):
        pass

    @err_decorator
    def sm_getExternalFiles(self, origin):
        extFiles = []
        return [extFiles, []]

    @err_decorator
    def sm_createRenderPressed(self, origin):
        origin.createPressed("Render")
