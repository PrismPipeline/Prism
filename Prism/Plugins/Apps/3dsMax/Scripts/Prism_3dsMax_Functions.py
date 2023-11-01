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
import traceback
import time
import logging

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from pymxs import runtime as rt

try:
    import MaxPlus
except:
    pass

from PrismUtils.Decorators import err_catcher as err_catcher


logger = logging.getLogger(__name__)


class Prism_3dsMax_Functions(object):
    # TODO smaller stuff
    #region Init
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        # 3dsMax major version is offset by 2
        # 3dsMax2020 will be 22 for example
        self.appVersion = self.getAppVersion(None)

        self.core.registerCallback(
            "onProductBrowserOpen", self.onProductBrowserOpen, plugin=self.plugin
        )
        self.core.registerCallback(
            "onStateManagerOpen", self.onStateManagerOpen, plugin=self.plugin
        )

    @err_catcher(name=__name__)
    def onProductBrowserOpen(self, origin):
        origin.l_versionRight.setText(
            "(Press CTRL and double click a version to show the import options)"
        )

    @err_catcher(name=__name__)
    def startup(self, origin):
        origin.timer.stop()
        parent = QWidget.find(rt.windows.getMAXHWND())
        origin.messageParent = parent

        if self.appVersion[0] < 23: # before Max2021
            MaxPlus.NotificationManager.Register(
                MaxPlus.NotificationCodes.FilePostOpenProcess, origin.sceneOpen
            )
        else: # Max2021+
            rt.callbacks.addScript(rt.Name("filePostOpenProcess"), origin.sceneOpen, id=rt.Name("filePostOpenProcess_sceneOpen"))
            
        
        origin.startAutosaveTimer()

    @err_catcher(name=__name__)
    def sceneOpen(self, origin):
        if self.core.shouldAutosaveTimerRun():
            origin.startAutosaveTimer()

    @err_catcher(name=__name__)
    def onStateManagerOpen(self, origin):
        origin.disabledCol = QColor(40, 40, 40)
        origin.activePalette = QPalette()
        origin.activePalette.setColor(QPalette.Window, QColor(150, 150, 150))
        origin.inactivePalette = QPalette()
        origin.inactivePalette.setColor(QPalette.Window, QColor(68, 68, 68))
        origin.f_import.setAutoFillBackground(True)
        origin.f_export.setAutoFillBackground(True)
        origin.gb_publish.setStyleSheet("QGroupBox::title{color: rgb(220, 220, 220);}")
        origin.shotcamFileType = ".fbx"

        # TODO callbacks
        if not origin.core.smCallbacksRegistered:
            if self.appVersion[0] < 23:
                MaxPlus.NotificationManager.Register(
                    MaxPlus.NotificationCodes.FilePostSave, origin.core.scenefileSaved
                )
                MaxPlus.NotificationManager.Register(
                    MaxPlus.NotificationCodes.PostSceneReset, origin.core.sceneUnload
                )
                MaxPlus.NotificationManager.Register(
                    MaxPlus.NotificationCodes.FilePreOpen, origin.core.sceneUnload
                )
            else:
                rt.callbacks.addScript(rt.Name("filePostSave"), origin.core.scenefileSaved, id=rt.Name("filePostSave_scenefileSaved"))
                rt.callbacks.addScript(rt.Name("postSceneReset"), origin.core.sceneUnload, id=rt.Name("postSceneReset_sceneUnload"))
                rt.callbacks.addScript(rt.Name("filePreOpen"), origin.core.sceneUnload, id=rt.Name("filePreOpen_sceneUnload"))
        
    #endregion

    #region Scene
    @err_catcher(name=__name__)
    def getCurrentFileName(self, origin, path=True):
        if path:
            return rt.execute( "maxFilePath + maxFileName")
        else:
            return rt.execute( "maxFileName")

    @err_catcher(name=__name__)
    def getCurrentSceneFiles(self, origin):
        return [self.core.getCurrentFileName()]

    @err_catcher(name=__name__)
    def getSceneExtension(self, origin):
        return self.sceneFormats[0]

    @err_catcher(name=__name__)
    def saveScene(self, origin, filepath, details={}):
        return rt.execute( 'saveMaxFile "%s"' % filepath)

    @err_catcher(name=__name__)
    def openScene(self, origin, filepath, force=False):
        if not filepath.endswith(".max"):
            return False

        if force or rt.execute( "checkforsave()"):
            rt.execute( 'loadMaxFile "%s" useFileUnits:true' % filepath)

        return True
    #endregion

    #region Frames
    @err_catcher(name=__name__)
    def getFrameRange(self, origin):
        startframe = rt.execute( "animationrange.start.frame")
        endframe = rt.execute( "animationrange.end.frame")

        return [startframe, endframe]

    @err_catcher(name=__name__)
    def setFrameRange(self, origin, startFrame, endFrame):
        if startFrame == endFrame:
            QMessageBox.warning(
                self.core.messageParent,
                "Warning",
                "The startframe and the endframe cannot be the same in 3dsMax.",
            )
            return
            
        rt.animationRange = rt.Interval(startFrame, endFrame)

    @err_catcher(name=__name__)
    def getCurrentFrame(self):
        sliderTime = rt.sliderTime
        currentFrame = sliderTime.frame
        return currentFrame

    @err_catcher(name=__name__)
    def setCurrentFrame(self, origin, frame):
        rt.sliderTime = frame

    @err_catcher(name=__name__)
    def getFPS(self, origin):
        return rt.frameRate

    @err_catcher(name=__name__)
    def setFPS(self, origin, fps):
        # Max changes the framerange when changing the fps
        # so we store the framerange and then restore later
        framerange = self.getFrameRange(origin)

        rt.frameRate = fps

        self.setFrameRange(origin, framerange[0], framerange[1])
    #endregion

    #region Nodes
    @err_catcher(name=__name__)
    def getCamNodes(self, origin, cur=False):
        sceneCamHandles = rt.execute("for i in cameras where (superclassof i) == camera collect i.handle")
        sceneCamHandles = list(sceneCamHandles)

        if cur:
            sceneCamHandles = ["Current View"] + sceneCamHandles

        return sceneCamHandles

    @err_catcher(name=__name__)
    def getCamName(self, origin, nodeHandle):
        if nodeHandle == "Current View":
            return nodeHandle

        # stateProps["currentcam"] gets force saved as string for some reason
        # it has to be integer to be read from max
        if not isinstance(nodeHandle, int):
            try:
                nodeHandle = int(nodeHandle)
            except:
                return "invalid"

        if not self.isNodeValid(origin, nodeHandle):
            return "invalid"
        else:
            return self.getNodeName(origin, nodeHandle)

    @err_catcher(name=__name__)
    def isNodeValid(self, origin, nodeHandle):
        node = rt.maxOps.getNodeByHandle(nodeHandle)
        return rt.isValidNode(node)

    @err_catcher(name=__name__)
    def getNodeName(self, origin, nodeHandle):
        if self.isNodeValid(origin, nodeHandle):
            node = rt.maxOps.getNodeByHandle(nodeHandle)
            return node.name
        else:
            return origin.nodeNames[origin.nodes.index(nodeHandle)]

    @err_catcher(name=__name__)
    def selectNodes(self, origin):
        if origin.lw_objects.selectedItems() != []:
            rt.clearSelection()

            nodes = []
            for i in origin.lw_objects.selectedItems():
                nodeHandle = origin.nodes[origin.lw_objects.row(i)]
                if self.isNodeValid(origin, nodeHandle):
                    node = rt.maxOps.getNodeByHandle(nodeHandle)
                    nodes.append(node)
            rt.select(nodes)

    @err_catcher(name=__name__)
    def selectCam(self, origin):
        if self.isNodeValid(origin, origin.curCam):
            curCamNode = rt.maxOps.getNodeByHandle(origin.curCam)
            rt.select(curCamNode)
    #endregion

    #region Export
    @err_catcher(name=__name__)
    def sm_export_startup(self, origin):
        origin.lw_objects.setStyleSheet("QListWidget { background: rgb(100,100,100);}")

    @err_catcher(name=__name__)
    def sm_export_addObjects(self, origin, objects=None):
        if not objects:
            sel = rt.selection
            objects = [i for i in sel]
        
        for object in objects:
            objectHandle = object.handle
            if objectHandle not in origin.nodes:
                origin.nodes.append(objectHandle)

    @err_catcher(name=__name__)
    def sm_export_exportShotcam(self, origin, startFrame, endFrame, outputName):
        # We always additionally export an .fbx because imported .abc cameras
        # are basically blackboxes in 3dsmax.
        if startFrame == endFrame:
            self.setFrameRange(origin, startFrame=startFrame, endFrame=endFrame + 1)
        else:
            self.setFrameRange(origin, startFrame=startFrame, endFrame=endFrame)

        rt.execute( "AlembicExport.CoordinateSystem = #Maya")

        if 18 <= self.appVersion[0] < 21: # Max 2016 - 2018
            rt.execute( "AlembicExport.CacheTimeRange = #StartEnd")
            rt.execute( "AlembicExport.StepFrameTime = 1")
            rt.execute( "AlembicExport.StartFrameTime = %s" % startFrame)
            rt.execute( "AlembicExport.EndFrameTime = %s" % endFrame)
            rt.execute( "AlembicExport.ParticleAsMesh = False")
        elif self.appVersion[0] >= 21: # Max 2019+
            rt.execute( "AlembicExport.AnimTimeRange = #StartEnd")
            rt.execute( "AlembicExport.SamplesPerFrame = 1")
            rt.execute( "AlembicExport.StartFrame = %s" % startFrame)
            rt.execute( "AlembicExport.EndFrame = %s" % endFrame)
            rt.execute( "AlembicExport.ParticleAsMesh = False")
        else:
            rt.messageBox("There is no alembic support for this version of 3dsMax.", title="Alembic not supported")

        if startFrame == endFrame:
            rt.execute('FbxExporterSetParam "Animation" False')
            self.setCurrentFrame(origin, startFrame)
        else:
            rt.execute('FbxExporterSetParam "Animation" True')

        self.selectCam(origin)
        rt.exportFile(outputName + ".abc", rt.Name("NoPrompt"), selectedOnly=True, using=rt.Alembic_Export)

        exportFBX = rt.execute("(classof (maxOps.getNodeByHandle %s)) != Physical" % origin.curCam)

        if exportFBX:
            self.selectCam(origin)
            rt.exportFile(outputName + ".fbx", rt.Name("NoPrompt"), selectedOnly=True, using=rt.FBXEXP)

        # TODO: store and restore selection
        rt.clearSelection()

    #region sm_export_exportAppObjects
    @err_catcher(name=__name__)
    def sm_export_exportAppObjects(
        self,
        origin,
        startFrame,
        endFrame,
        outputName,
    ):
        if startFrame == endFrame:
            self.setFrameRange(origin, startFrame=startFrame, endFrame=endFrame + 1)
        else:
            self.setFrameRange(origin, startFrame=startFrame, endFrame=endFrame)

        expNodeHandles = origin.nodes

        additionalOptions = origin.chb_additionalOptions.isChecked()
        selectedOnly = not origin.chb_wholeScene.isChecked()

        if selectedOnly:
            rt.clearSelection()

            nodeHandles = [handle for handle in expNodeHandles if self.isNodeValid(origin,handle)]
            nodes = [rt.maxOps.getNodeByHandle(handle) for handle in nodeHandles]
            rt.select(nodes)

        if origin.cb_outType.currentText() == ".obj":
            for i in range(startFrame, endFrame + 1):
                self.setCurrentFrame(origin,i)

                foutputName = outputName.replace("####", format(i, "04"))
                
                if additionalOptions:
                    rt.exportFile(foutputName, selectedOnly=selectedOnly)
                else:
                    rt.exportFile(foutputName, rt.Name("NoPrompt"), selectedOnly=selectedOnly)

            outputName = foutputName

        elif origin.cb_outType.currentText() == ".fbx":
            if startFrame == endFrame:
                rt.execute('FbxExporterSetParam "Animation" False')

                self.setCurrentFrame(origin, startFrame)
            else:
                rt.execute('FbxExporterSetParam "Animation" True')

            if additionalOptions:
                rt.exportFile(outputName, selectedOnly=selectedOnly, using=rt.FBXEXP)
            else:
                rt.exportFile(outputName, rt.Name("NoPrompt"), selectedOnly=selectedOnly, using=rt.FBXEXP)

        elif origin.cb_outType.currentText() == ".abc":
            rt.execute( "AlembicExport.CoordinateSystem = #Maya")

            # TODO fix versions
            if 18 <= self.appVersion[0] < 21: # Max 2016 - 2018
                rt.execute( "AlembicExport.CacheTimeRange = #StartEnd")
                rt.execute( "AlembicExport.StepFrameTime = 1")
                rt.execute("AlembicExport.StartFrameTime = %s" % startFrame)
                rt.execute( "AlembicExport.EndFrameTime = %s" % endFrame)
                rt.execute( "AlembicExport.ParticleAsMesh = False")
            elif self.appVersion[0] >= 21: # Max 2019+
                rt.execute( "AlembicExport.AnimTimeRange = #StartEnd")
                rt.execute( "AlembicExport.SamplesPerFrame = 1")
                rt.execute( "AlembicExport.StartFrame = %s" % startFrame)
                rt.execute( "AlembicExport.EndFrame = %s" % endFrame)
                rt.execute( "AlembicExport.ParticleAsMesh = False")
            else:
                rt.messageBox("There is no alembic support for this version of 3dsMax.", title="Alembic not supported")

            if additionalOptions:
                rt.exportFile(outputName, selectedOnly=selectedOnly, using=rt.Alembic_Export)
            else:
                rt.exportFile(outputName, rt.Name("NoPrompt"), selectedOnly=selectedOnly, using=rt.Alembic_Export)

        elif origin.cb_outType.currentText() == ".max":
            if selectedOnly:
                rt.saveNodes(nodes, outputName, quiet=True)
            else:
                rt.saveMaxFile(outputName, useNewFile=False, quiet=True)

        # TODO save and restore selection
        if selectedOnly:
            rt.clearSelection()

        return outputName
    #endregion

    @err_catcher(name=__name__)
    def sm_export_preExecute(self, origin, startFrame, endFrame):
        warnings = []

        if origin.cb_outType.currentText() != "ShotCam":
            if origin.cb_outType.currentText() != ".fbx":
                for nodeHandle in origin.nodes:
                    if not self.isNodeValid(origin, nodeHandle):
                        continue

                    if rt.maxOps.getNodeByHandle(nodeHandle).isHidden:
                        warnings.append(
                            [
                                "%s is hidden." % rt.maxOps.getNodeByHandle(nodeHandle).name,
                                "Hidden objects are only supported with fbx exports.",
                                2,
                            ]
                        )
                        break

        if (
            (
                origin.cb_outType.currentText() == ".fbx"
                or origin.cb_outType.currentText() == "ShotCam"
            )
            and startFrame == endFrame
        ):
            warnings.append(
                ["Single frame FBX exports will export Frame 0 only.", "", 2]
            )

        return warnings

    @err_catcher(name=__name__)
    def sm_export_clearSet(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_export_updateObjects(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_export_removeSetItem(self, origin, node):
        pass

    @err_catcher(name=__name__)
    def sm_export_preDelete(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_export_colorObjList(self, origin):
        origin.f_objectList.setStyleSheet("QFrame { border: 3px solid rgb(200,0,0); }")

    @err_catcher(name=__name__)
    def sm_export_unColorObjList(self, origin):
        origin.f_objectList.setStyleSheet("QFrame { border: 3px solid rgb(68,68,68); }")

    @err_catcher(name=__name__)
    def sm_export_typeChanged(self, origin, idx):
        origin.w_additionalOptions.setVisible(not idx in ["ShotCam", ".max"])
    #endregion

    #region Import
    @err_catcher(name=__name__)
    def sm_import_startup(self, origin):
        origin.f_abcPath.setVisible(True)

    @err_catcher(name=__name__)
    def sm_import_importToApp(self, origin, doImport, update, impFileName):
        impFileName = os.path.normpath(impFileName)
        fileName = os.path.splitext(os.path.basename(impFileName))
        result = False
        
        #region max
        if fileName[1] == ".max":
            validNodeHandles = [x for x in origin.nodes if self.isNodeValid(origin, x)]
            if not update or len(validNodeHandles) == 0:
                msg = QMessageBox(
                    QMessageBox.Question,
                    "Create Reference",
                    "Do you want to create a reference?",
                    QMessageBox.No,
                )
                msg.addButton("Yes", QMessageBox.YesRole)
                msg.setParent(self.core.messageParent, Qt.Window)
                action = msg.exec_()
            else:
                action = 1 - int(
                    rt.execute("""
(
	item = objXRefMgr.IsNodeXRefed (maxOps.getNodeByHandle %s)
	item != undefined
)"""
                        % validNodeHandles[0],
                    )
                )

            if action == 0:
                createNewXref = True

                if len(validNodeHandles) > 0:
                    isXref = rt.execute("""
(
	item = objXRefMgr.IsNodeXRefed (maxOps.getNodeByHandle %s)
	item != undefined
)"""
                        % validNodeHandles[0],
                    )

                    if isXref:
                        createNewXref = False
                        result = rt.execute("""
(
	item = objXRefMgr.IsNodeXRefed (maxOps.getNodeByHandle %s)
	item.xrefRecord.srcFileName =\"%s\"
	if item.xrefRecord == undefined then(
		False
	) else (
		items = #()
		item.xrefRecord.GetItems #XRefObjectType &items
		nodes = #()
		for i in items do (
				childs = #()
				i.GetNodes &childs
				join nodes childs
		)
		select nodes
		True
	)
)"""
                            % (validNodeHandles[0], impFileName.replace("\\", "\\\\")),
                        )
                    else:
                        origin.preDelete(
                            baseText="Do you want to delete the currently connected objects?\n\n"
                        )

                if createNewXref:
                    result = rt.execute('(\n\
clearselection()\n\
record = objXRefMgr.AddXRefItemsFromFile "%s" xrefOptions:#(#mergeModifiers,#selectNodes,#localControllers)\n\
record != undefined\n\
)'
                        % impFileName.replace("\\", "\\\\"),
                    )

            else:
                origin.preDelete(
                    baseText="Do you want to delete the currently connected objects?\n\n"
                )

                rt.mergeMaxFile(impFileName, rt.Name("select"))
        #endregion

        else:
            if not (fileName[1] == ".abc" and origin.chb_abcPath.isChecked()):
                origin.preDelete(
                    baseText="Do you want to delete the currently connected objects?\n\n"
                )
            if fileName[1] == ".abc":
                if origin.chb_abcPath.isChecked():
                    for i in origin.nodes:
                        if not self.isNodeValid(origin, i):
                            continue

                        i.source = impFileName

                        result = True
                        doImport = False
                rt.execute( "AlembicImport.ImportToRoot = True")

            elif fileName[1] == ".fbx":
                rt.execute( 'FBXImporterSetParam "Mode" #create')
                rt.execute( 'FBXImporterSetParam "ConvertUnit" #cm')

                prevLayers = []
                layerManager = rt.LayerManager

                for i in range(layerManager.count):
                    prevLayers.append(layerManager.getLayer(i))

            if doImport:
                showProps = False
                modifiers = QApplication.keyboardModifiers()
                if modifiers == Qt.ControlModifier:
                    showProps = True


                if fileName[1] == ".abc":
                    if showProps:
                        result = rt.importFile(impFileName, using=rt.Alembic_Import)
                    else:
                        result = rt.importFile(impFileName, rt.Name("NoPrompt"), using=rt.Alembic_Import)

                elif fileName[1] == ".fbx":
                    if showProps:
                        result = rt.importFile(impFileName, using=rt.FBXIMP)
                    else:
                        result = rt.importFile(impFileName, rt.Name("NoPrompt"), using=rt.FBXIMP)

                else:
                    if showProps:
                        result = rt.importFile(impFileName)
                    else:
                        result = rt.importFile(impFileName, rt.Name("NoPrompt"))

            if fileName[1] == ".fbx":
                delLayers = []

                layerManager = rt.LayerManager
                for i in range(layerManager.count):
                    curLayer = layerManager.getLayer(i)
                    isLayerUsed = layerManager.doesLayerHierarchyContainNodes(layerManager.getLayer(i).name)
                    if not curLayer in prevLayers and not isLayerUsed:
                        delLayers.append(curLayer.name)

                for i in delLayers:
                    layerManager.deleteLayerByName(i)

        if doImport:
            importedNodeHandles = [x.handle for x in rt.selection]

            if origin.chb_trackObjects.isChecked():
                origin.nodes = importedNodeHandles

        if origin.taskName == "ShotCam":
            rt.execute( "setTransformLockFlags selection #all")

            layerManager = rt.LayerManager
            camLayer = layerManager.getLayerFromName("00_Cams")

            if camLayer is not None:
                for nodeHandle in origin.nodes:
                    node = rt.maxOps.getNodeByHandle(nodeHandle)
                    camLayer.addnode(node)

        return {"result": result, "doImport": doImport}

    @err_catcher(name=__name__)
    def sm_import_updateObjects(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_import_removeNameSpaces(self, origin):
        for nodeHandle in origin.nodes:
            if not self.isNodeValid(origin, nodeHandle):
                continue

            node = rt.maxOps.getNodeByHandle(nodeHandle)
            
            nodeName = self.getNodeName(origin, nodeHandle)
            newName = nodeName.rsplit(":", 1)[-1]
            if newName != nodeName:
                node.name = newName

        origin.updateUi()

    @err_catcher(name=__name__)
    def sm_import_updateListItem(self, origin, item, nodeHandle):
        if self.isNodeValid(origin, nodeHandle):
            item.setBackground(QColor(0, 150, 0))
        else:
            item.setBackground(QColor(150, 0, 0))
    #endregion

    #region Statemanagement
    # states are stored in File > File properties > Custom > 
    # PrismStates and PrismImports (for import paths)
    @err_catcher(name=__name__)
    def getImportPaths(self, origin):
        num = rt.execute('fileProperties.findProperty #custom "PrismImports"')
        if num == 0:
            return False
        else:
            return rt.execute("fileProperties.getPropertyValue #custom %s" % num)

    @err_catcher(name=__name__)
    def sm_saveStates(self, origin, buf):
        rt.execute('fileProperties.addProperty #custom "PrismStates" "%s"'
            % buf.replace('"', '\\"').replace("\\\\", "\\\\\\\\"),
        )

    @err_catcher(name=__name__)
    def sm_saveImports(self, origin, importPaths):
        rt.execute('fileProperties.addProperty #custom "PrismImports" "%s"' % importPaths)

    @err_catcher(name=__name__)
    def sm_readStates(self, origin):
        num = rt.execute('fileProperties.findProperty #custom "PrismStates"')
        if num != 0:
            return rt.execute("fileProperties.getPropertyValue #custom %s" % num)

    @err_catcher(name=__name__)
    def sm_deleteStates(self, origin):
        num = rt.execute('fileProperties.findProperty #custom "PrismStates"')
        if num != 0:
            rt.execute('fileProperties.deleteProperty #custom "PrismStates"')
    #endregion

    #region Playblast
    @err_catcher(name=__name__)
    def sm_playblast_startup(self, origin):
        frange = self.getFrameRange(origin)
        origin.sp_rangeStart.setValue(frange[0])
        origin.sp_rangeEnd.setValue(frange[1])
        origin.cb_rangeType.removeItem(origin.cb_rangeType.findText("Single Frame"))

    @err_catcher(name=__name__)
    def sm_playblast_createPlayblast(self, origin, jobFrames, outputName):
        # TODO look for playblast api?
        if origin.curCam is not None:
            self.setCurrentViewportCamera(origin, origin.curCam)

        if origin.chb_resOverride.isChecked():
            self.setResolution(
                origin.sp_resWidth.value(),
                origin.sp_resHeight.value()
                )

        outputName = os.path.splitext(outputName)[0].rstrip("#") + os.path.splitext(outputName)[1]
        rt.execute(
            """
dnSendKeys = (dotNetClass "System.Windows.Forms.SendKeys")
dnmarshal = (dotNetClass "System.Runtime.InteropServices.Marshal")
insidedialog = false
global createPreviewVersion =(maxVersion())[1]
global pathstring = \"%s\"
global rStart = %s
global rEnd = %s
global sceneFps = frameRate

fn setoutput =
(
	window = (windows.getChildHWND 0 ("JPEG Image Control") )
	if window != undefined then
	(
		UIAccessor.pressbutton (UIAccessor.GetChildWindows window[1])[1]
	) else
	(
		window = undefined
		window = (windows.getChildHWND 0 ("File Exists") )
		if window != undefined then
		(
			UIAccessor.pressbutton ((UIAccessor.GetChildWindows (window[1]))[2])
		) else
		(
			window = (windows.getChildHWND 0 ("Create Animated Sequence File...") )
			if window != undefined then
			(
				if not insidedialog then
				(
					insidedialog = true
					createsequence = window[1]
					ptrstring = dnmarshal.StringToHGlobalUni(\"%s\")
					windows.sendMessage (UIAccessor.GetChildWindows createsequence)[13] 12 0 ptrstring
					windows.sendMessage (UIAccessor.GetChildWindows createsequence)[13] 6 1 0

					windows.sendMessage (UIAccessor.GetChildWindows createsequence)[15] 0x014E 8 0
					windows.sendMessage (UIAccessor.GetChildWindows createsequence)[15] 6 1 0
					dnSendKeys.sendwait ("{DOWN}")
					dnSendKeys.sendwait ("{UP}")

					UIAccessor.pressbutton (UIAccessor.GetChildWindows window[1])[17]
				)
			) else 
			(
				window = (windows.getChildHWND 0 ("Make Preview") )
				if window != undefined then
				(
					makepreview = window[1]
					tmpstyle = 2
					windows.sendMessage (UIAccessor.GetChildWindows makepreview)[56] 0x014E tmpstyle 0
					windows.sendMessage (UIAccessor.GetChildWindows makepreview)[56] 6 1 0
					if tmpstyle == 0 then (
						dnSendKeys.sendwait ("{DOWN}")
						dnSendKeys.sendwait ("{UP}")
					) else (
						dnSendKeys.sendwait ("{UP}")
						dnSendKeys.sendwait ("{DOWN}")
					)
					windows.sendMessage (UIAccessor.GetChildWindows makepreview)[33] 0x00F5 1 0
					UIAccessor.pressbutton (UIAccessor.GetChildWindows makepreview)[65]
					UIAccessor.pressbutton (UIAccessor.GetChildWindows makepreview)[37]
					return true
				)
			)
		)
	)
	return true
)


tmpanimrange = [animationrange.start, animationrange.end]
animationrange = interval rStart rEnd
ViewCubeOps.Visibility = false
    if createPreviewVersion<22000 then
    (
        DialogMonitorOPS.Enabled = true
        DialogMonitorOPS.RegisterNotification setoutput id:#myoutput
        max preview
        CreatePreview outputAVI:False percentsize:100 start:rStart end:rEnd skip:1 fps:sceneFps dspGeometry:True dspShapes:False dspLights:False dspCameras:False dspHelpers:False dspParticles:True dspBones:False dspGrid:False dspSafeFrame:False dspFrameNums:False dspBkg:True
        DialogMonitorOPS.UnRegisterNotification  id:#myoutput
        DialogMonitorOPS.Enabled = false
    )
    else
    (
        CreatePreview filename:pathstring outputAVI:False percentsize:100 start:rStart end:rEnd skip:1 fps:sceneFps dspGeometry:True dspShapes:False dspLights:False dspCameras:False dspHelpers:False dspParticles:True dspBones:False dspGrid:False dspSafeFrame:False dspFrameNums:False dspBkg:True
    )
ViewCubeOps.Visibility = True
animationrange = interval tmpanimrange.x tmpanimrange.y
"""
            % (
                outputName.replace("\\", "\\\\"),
                jobFrames[0],
                jobFrames[1],
                outputName.replace("\\", "\\\\"),
            ),
        )

    @err_catcher(name=__name__)
    def sm_playblast_preExecute(self, origin):
        warnings = []

        rangeType = origin.cb_rangeType.currentText()
        startFrame, endFrame = origin.getFrameRange(rangeType)

        if startFrame == endFrame:
            warnings.append(
                [
                    "Playblasts in 3ds Max are only supported with at least two frames.",
                    "",
                    3,
                ]
            )

        return warnings

    @err_catcher(name=__name__)
    def sm_playblast_execute(self, origin):
        rangeType = origin.cb_rangeType.currentText()
        startFrame, endFrame = origin.getFrameRange(rangeType)

        if startFrame == endFrame:
            return [
                origin.state.text(0)
                + ": error - Playblasts in 3ds Max are only supported with at least two frames."
            ]
    #endregion 

    #region render
    @err_catcher(name=__name__)
    def getCurrentRenderer(self, origin):
        return rt.execute("classof renderers.current as string")

    @err_catcher(name=__name__)
    def sm_render_isVray(self, origin):
        return rt.execute('matchpattern (classof renderers.current as string) pattern: "V_Ray*"')

    @err_catcher(name=__name__)
    def sm_render_startup(self, origin):
        origin.sp_rangeStart.setValue(
            rt.execute("animationrange.start.frame")
        )
        origin.sp_rangeEnd.setValue(
            rt.execute("animationrange.end.frame")
        )

    @err_catcher(name=__name__)
    def sm_render_getAovNames(self):
        aovs = []
        elementMgr = rt.maxOps.GetCurRenderElementMgr()
        if not elementMgr.GetElementsActive():
            return aovs

        for idx in range(elementMgr.NumRenderElements()):
            element = elementMgr.GetRenderElement(idx)
            aovs.append(element.elementName)

        return aovs

    @err_catcher(name=__name__)
    def sm_render_refreshPasses(self, origin):
        if hasattr(origin, "w_redshift"):
            isRs = self.getCurrentRenderer(origin) == "Redshift_Renderer"
            origin.w_redshift.setHidden((not isRs) or (not origin.gb_submit.isChecked()))

        origin.lw_passes.clear()
        elementMgr = rt.maxOps.GetCurRenderElementMgr()
        for i in range(elementMgr.NumRenderElements()):
            element = elementMgr.GetRenderElement(i)
            item = QListWidgetItem(element.elementName)
            origin.lw_passes.addItem(item)

    @err_catcher(name=__name__)
    def sm_render_openPasses(self, origin, item=None):
        rt.renderSceneDialog.open()

    @err_catcher(name=__name__)
    def removeAOV(self, aovName):
        elementMgr = rt.maxOps.GetCurRenderElementMgr()
        
        for i in range(elementMgr.NumRenderElements()):
            element = elementMgr.GetRenderElement(i)
            if element.elementName == aovName:
                elementMgr.RemoveRenderElement(element)
                break

    @err_catcher(name=__name__)
    def sm_render_preExecute(self, origin):
        warnings = []

        if self.sm_render_isVray(origin):
            if rt.execute( "renderers.current.output_on"):
                warnings.append(["VrayFrameBuffer is activated.", "", 2])

            if rt.execute( "renderers.current.system_frameStamp_on"):
                warnings.append(["FrameStamp is activated.", "", 2])

            if rt.execute( "vrayVFBGetRegionEnabled()"):
                warnings.append(["Region rendering is enabled.", "", 2])

        return warnings

    @err_catcher(name=__name__)
    def sm_render_preSubmit(self, origin, rSettings):
        if origin.cb_rangeType.currentText() != "Single Frame":
            base, ext = os.path.splitext(rSettings["outputName"])
            if not base.endswith("_"):
                rsOutput = base + "_" + ext
                rSettings["outputName"] = rsOutput

        outputName = rSettings["outputName"]
        if not origin.gb_submit.isHidden() and origin.gb_submit.isChecked():
            if hasattr(origin, "chb_redshift") and origin.chb_redshift.isChecked() and not origin.w_redshift.isHidden():
                base, ext = os.path.splitext(rSettings["outputName"])
                outputName = base.strip("_") + "." + ext
                rsOutput = base.strip("_") + "." + "#" * self.core.framePadding + ext
                rSettings["outputName"] = rsOutput
                rt.rendTimeType = 2  # needed for framepadding in outputpath

        rt.renderSceneDialog.close()

        elementMgr = rt.maxOps.GetCurRenderElementMgr()
        rSettings["elementsActive"] = elementMgr.GetElementsActive()

        elementMgr.SetElementsActive(origin.gb_passes.isChecked())

        if origin.gb_passes.isChecked():
            for i in range(elementMgr.NumRenderElements()):
                element = elementMgr.GetRenderElement(i)
                passName = element.elementName
                passOutputName = os.path.join(
                    os.path.dirname(os.path.dirname(rSettings["outputName"])),
                    passName,
                    os.path.basename(outputName).replace(
                        "beauty", passName
                    ),
                )
                try:
                    os.makedirs(os.path.dirname(passOutputName))
                except:
                    pass
                # TODO convert to rt.thingy
                rt.execute(
                    '(maxOps.GetCurRenderElementMgr()).SetRenderElementFilename %s "%s"'
                    % (i, passOutputName.replace("\\", "\\\\"))
                )

        rSettings["savefile"] = rt.rendSaveFile
        rSettings["savefilepath"] = rt.rendOutputFilename

        rt.rendSaveFile = True
        # if self.appVersion[0] < 25:  # before Max2023
        # outName = rSettings["outputName"].replace("#" * self.core.framePadding, "")
        # else:
        # outName = rSettings["outputName"]
        rt.rendOutPutFilename = outputName

    @err_catcher(name=__name__)
    def sm_render_startLocalRender(self, origin, outputName, rSettings):
        if origin.chb_resOverride.isChecked():
            resolution = self.getResolution()

            rSettings["width"] = resolution[0]
            rSettings["height"] = resolution[1]

            self.setResolution(
                origin.sp_resWidth.value(),
                origin.sp_resHeight.value())

        rSettings["timetype"] = rt.rendTimeType
        rSettings["prev_start"] = rt.rendStart
        rSettings["prev_end"] = rt.rendEnd

        rt.execute("rendUseActiveView = True")
        if origin.curCam != "Current View":
            self.setCurrentViewportCamera(origin, origin.curCam)

        if rSettings["startFrame"] is None:
            frameChunks = [[x, x] for x in rSettings["frames"]]
        else:
            frameChunks = [[rSettings["startFrame"], rSettings["endFrame"]]]

        try:
            for frameChunk in frameChunks:
                if rSettings["rangeType"] == "Single Frame":
                    timeType = 1
                else:
                    timeType = 3
                
                rt.rendTimeType = timeType
                rt.rendStart = frameChunk[0]
                rt.rendEnd = frameChunk[1]

                rt.execute("max quick render")

            if len(os.listdir(os.path.dirname(outputName))) > 0:
                return "Result=Success"
            else:
                return "unknown error (files do not exist)"
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            erStr = "%s ERROR - sm_default_imageRender %s:\n%s" % (
                time.strftime("%d/%m/%y %X"),
                origin.core.version,
                traceback.format_exc(),
            )
            self.core.writeErrorLog(erStr)
            return "Execute Canceled: unknown error (view console for more information)"

    @err_catcher(name=__name__)
    def sm_render_undoRenderSettings(self, origin, rSettings):
        if "elementsActive" in rSettings:
            elementMgr = rt.maxOps.GetCurRenderElementMgr()
            
            elementMgr.SetElementsActive(rSettings["elementsActive"])

        if "width" in rSettings:
            self.setResolution(width=rSettings["width"])
        if "height" in rSettings:
            self.setResolution(height=rSettings["height"])
        if "timetype" in rSettings:
            rt.rendTimeType = rSettings["timetype"]
        if "prev_start" in rSettings:
            rt.rendStart = rSettings["prev_start"]
        if "prev_end" in rSettings:
            rt.rendEnd = rSettings["prev_end"]
        if "savefile" in rSettings:
            rt.rendSaveFile = rSettings["savefile"]
        if "savefilepath" in rSettings:
            rt.rendOutputFilename = rSettings["savefilepath"]

    @err_catcher(name=__name__)
    def sm_render_getDeadlineParams(self, origin, dlParams, homeDir):
        dlParams["pluginInfoFile"] = os.path.join(
            homeDir, "temp", "3dsmax_plugin_info.job"
        )
        dlParams["jobInfoFile"] = os.path.join(
            homeDir, "temp", "3dsmax_submit_info.job"
        )

        dlParams["jobInfos"]["Plugin"] = "3dsmax"
        dlParams["jobInfos"]["Comment"] = "Prism-Submission-3dsmax_ImageRender"
        dlParams["pluginInfos"]["Version"] = str(self.getAppVersion(origin)[0] - 2 + 2000)
        dlParams["pluginInfos"]["MaxVersionToForce"] = dlParams["pluginInfos"]["Build"]
        dlParams["pluginInfos"]["PopupHandling"] = "1"

        if origin.chb_resOverride.isChecked():
            resString = "Render"
            dlParams["pluginInfos"][resString + "Width"] = str(
                origin.sp_resWidth.value()
            )
            dlParams["pluginInfos"][resString + "Height"] = str(
                origin.sp_resHeight.value()
            )

        if origin.curCam != "Current View":
            dlParams["pluginInfos"]["Camera"] = self.core.appPlugin.getCamName(
                origin, origin.curCam
            )
            cams = self.getCamNodes(self)
            for idx, cam in enumerate(cams):
                dlParams["pluginInfos"]["Camera%s" % idx] = self.getCamName(self, cam)

        if dlParams["sceneDescription"] == "redshift":
            dlParams["pluginInfos"]["MAXScriptJob"] = "1"
            msPath = self.core.getTempFilepath(ext=".ms", filenamebase="MAXScriptJob_")
            rsOutput = dlParams["jobInfos"]["OutputFilename0"]
            if origin.curCam == "Current View":
                camera = rt.execute("""
(
camName = ""
currentCamera = viewport.GetCamera()
if iskindof currentCamera camera then (
    camName = currentCamera.name
)
camName)""")
            else:
                camera = self.core.appPlugin.getCamName(
                    origin, origin.curCam
                )

            script = self.getMaxScriptDeadlineScript(rsOutput, camera)
            logger.debug("submitting Redshift job: output: %s, camera: %s" % (rsOutput, camera))
            with open(msPath, "w") as f:
                f.write(script)

            dlParams["arguments"].append(msPath)

    @err_catcher(name=__name__)
    def sm_render_getRenderPasses(self, origin):
        if self.sm_render_isVray(origin):
            return self.core.getConfig(
                "defaultpasses", "max_vray", configPath=self.core.prismIni
            )
        else:
            return self.core.getConfig(
                "defaultpasses", "max_scanline", configPath=self.core.prismIni
            )

    @err_catcher(name=__name__)
    def sm_render_addRenderPass(self, origin, passName, steps):
        if rt.execute(passName) is not None:
            rt.execute("(MaxOps.GetCurRenderElementMgr()).AddRenderElement(%s())" % passName)
    #endregion

    #region Pre/Post
    # TODO possible to rename origTime to origFrame?
    @err_catcher(name=__name__)
    def sm_preExecute(self, origin):
        origin.origTimeRange = self.getFrameRange(origin)
        origin.origTime = self.getCurrentFrame()

    @err_catcher(name=__name__)
    def sm_postExecute(self, origin):
        self.setFrameRange(origin, origin.origTimeRange[0],origin.origTimeRange[1])
        self.setCurrentFrame(origin, origin.origTime)
    #endregion

    @err_catcher(name=__name__)
    def getResolution(self):
        return [rt.renderWidth, rt.renderHeight]

    @err_catcher(name=__name__)
    def setResolution(self, width=None, height=None):
        if width:
            rt.renderWidth = width
        if height:
            rt.renderHeight = height

    @err_catcher(name=__name__)
    def getAppVersion(self, origin):
        # 3dsMax major version is offset by 2
        # 3dsMax2020 will be 22 for example
        versionSegmentStringList = rt.execute( 'getFileVersion "$max/3dsmax.exe"').split()[0].split(',')
        return [int(versionSegmentString) for versionSegmentString in versionSegmentStringList]

    @err_catcher(name=__name__)
    def autosaveEnabled(self, origin):
        return rt.execute( "autosave.Enable")
        
    @err_catcher(name=__name__)
    def sm_createRenderPressed(self, origin):
        origin.createPressed("Render")

    def sm_getExternalFiles(self, origin):
        extFiles = rt.execute(
            "mapfiles=#()\n\
fn addmap mapfile =\n\
(\n\
if (finditem mapfiles mapfile) == 0 do append mapfiles mapfile\n\
)\n\
enumeratefiles addmap\n\
for mapfile in mapfiles collect mapfile",
        )

        if extFiles is None:
            extFiles = []

        return [extFiles, []]

    @err_catcher(name=__name__)
    def sm_setActivePalette(self, origin, listWidget, inactive, inactivef, activef):
        activef.setPalette(origin.activePalette)
        inactivef.setPalette(origin.inactivePalette)

    @err_catcher(name=__name__)
    def setCurrentViewportCamera(self, origin, cameraHandle):
        viewport = rt.viewport
        camera = rt.maxOps.getNodeByHandle(cameraHandle)
        viewport.setCamera(camera)

    @err_catcher(name=__name__)
    def deleteNodes(self, origin, handles):
        # Called when import state gets deleted
        # Deletes nodes of connected import state
        nodes = [rt.maxOps.getNodeByHandle(handle) for handle in handles]

        #clear xrefs first
        xref = rt.execute("item = objXRefMgr.IsNodeXRefed (maxOps.getNodeByHandle %s)\n\
if item == undefined then (\n\
False\n\
) else (\n\
objXRefMgr.RemoveRecordFromScene item.xrefRecord\n\
True\n\
)\n\
"
            % handles[0],
        )
        
        # then delete nodes
        if not xref:
            rt.delete(nodes)

    @err_catcher(name=__name__)
    def getMaxScriptDeadlineScript(self, outputPath, camera):
        script = """
try
(
    local du = DeadlineUtil  --this is the interface exposed by the Lightning Plugin which provides communication between Deadline and 3ds Max
    if du == undefined do  --if the script is not being run on Deadline (for testing purposes),
    (
        struct DeadlineUtilStruct   --define a stand-in struct with the same methods as the Lightning plugin
        (
            fn SetTitle title = ( format "Title: %%\\n" title ),
            fn SetProgress percent = (true),
            fn FailRender msg = ( throw msg ),
            --For "Job Info Parameters" (as displayed in Monitor -> job -> job properties > Submission Params)
            --Please consult the Scripting API reference online -> Deadline.Jobs.Job Class Reference
            --http://docs.thinkboxsoftware.com/products/deadline/8.0/2_Scripting%%20Reference/class_deadline_1_1_jobs_1_1_job.html#properties
            --All of our job properties can be accessed here and are prefixed with "Job" such as:
            --fn GetSubmitInfoEntry( "JobSubmitMachine" ), --for "MachineName="
            fn GetSubmitInfoEntry key = ( undefined ),
            fn GetSubmitInfoEntryElementCount key = ( 0 ),
            fn GetSubmitInfoEntryElement index key = ( undefined ),
            --For "Plugin Info Parameters" (as displayed in Monitor -> job -> job properties > Submission Params)
            --Please consult the displayed Key=Value pairs in the "Plugin Info Parameters" in Monitor such as:
            --fn GetJobInfoEntry( "MaxVersion" ), --for "MaxVersion=2017"
            fn GetJobInfoEntry key = ( undefined ),
            fn GetAuxFilename index = ( undefined ),
            fn GetOutputFilename index = ( undefined ),
            fn LogMessage msg = ( format "INFO: %%\\n" msg ),
            fn WarnMessage msg = ( format "WARNING: %%\\n" msg ),
            CurrentFrame = ((sliderTime as string) as integer),
            CurrentTask = ( -1 ),
            SceneFileName = ( maxFilePath + maxFileName ),
            SceneFilePath = ( maxFilePath ),
            JobsDataFolder = ( "" ),
            PluginsFolder = ( "" )
        )
        du = DeadlineUtilStruct() --create an instance of the stand-in struct
    )--end if
    
    du.SetTitle "MAXScript Job" --set the job title 
    du.LogMessage "Starting MAXScript Job..." --output a message to the log
    local st = timestamp() --get the current system time
    
    
    
    --YOUR SCENE PROCESSING CODE GOES HERE
    frameString = formattedPrint du.CurrentFrame format:"04d"
    -- origOutputFilename = rendOutputFilename
    -- rendOutputFilename = substituteString rendOutputFilename "####" frameString
    f = "%s"
    f = substituteString f "####" frameString
    camObj = getNodeByName "%s"
    rsProxyExportRollout.doProxyExport f selected:false startFrame:du.CurrentFrame endFrame:du.CurrentFrame warnExisting:false camera:camObj
    -- rendOutputFilename = origOutputFilename
    
    
    
    du.LogMessage ("Finished MAXScript Job in "+ ((timestamp() - st)/1000.0) as string + " sec.") --output the job duration
    true  --return true if the task has finished successfully, return false to fail the task.
)--end script
catch
(
    if ((maxVersion())[1]/1000 as integer) >= 19 then --Max2017 or later only
    (
        if hasCurrentExceptionStackTrace() then
        (
            local stackTrace = getCurrentExceptionStackTrace()
            stackTrace =  filterString stackTrace "\\n"
            for line in stackTrace do
            (
                if DeadlineUtil == undefined then (format "WARNING: %%\\n" line) else DeadlineUtil.WarnMessage(line)
            )
        )
    )
    throw()
)""" % (outputPath.replace("\\", "\\\\"), camera)

        return script
