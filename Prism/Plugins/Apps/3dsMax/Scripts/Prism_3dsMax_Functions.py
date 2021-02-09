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
import traceback
import time

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1

try:
    import MaxPlus
except:
    pass

from PrismUtils.Decorators import err_catcher as err_catcher


class Prism_3dsMax_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        if not "MaxPlus" in globals() and sys.version[0] == "3":
            self.enabled = False
            self.core.popup("Prism works in 3ds Max with Python 2.7 only.\nSet the environment variable ADSK_3DSMAX_PYTHON_VERSION to \"2\" to use Prism in this version of 3ds Max")

    @err_catcher(name=__name__)
    def startup(self, origin):
        origin.timer.stop()
        if psVersion == 1:
            origin.messageParent = MaxPlus.GetQMaxWindow()
        else:
            origin.messageParent = MaxPlus.GetQMaxMainWindow()
        MaxPlus.NotificationManager.Register(
            MaxPlus.NotificationCodes.FilePostOpenProcess, origin.sceneOpen
        )

        origin.startasThread()

    @err_catcher(name=__name__)
    def autosaveEnabled(self, origin):
        return self.executeScript(origin, "autosave.Enable")

    @err_catcher(name=__name__)
    def onProjectChanged(self, origin):
        pass

    @err_catcher(name=__name__)
    def sceneOpen(self, origin):
        if hasattr(origin, "asThread") and origin.asThread.isRunning():
            origin.startasThread()

    @err_catcher(name=__name__)
    def executeScript(self, origin, code, returnVal=True):
        try:
            val = MaxPlus.Core.EvalMAXScript(code)
        except Exception as e:
            msg = "\nmaxscript code:\n%s" % code
            exec("raise type(e), type(e)(e.message + msg), sys.exc_info()[2]")

        if returnVal:
            try:
                return val.Get()
            except:
                return None

    @err_catcher(name=__name__)
    def getCurrentFileName(self, origin, path=True):
        if path:
            return self.executeScript(origin, "maxFilePath + maxFileName")
        else:
            return self.executeScript(origin, "maxFileName")

    @err_catcher(name=__name__)
    def getSceneExtension(self, origin):
        return self.sceneFormats[0]

    @err_catcher(name=__name__)
    def saveScene(self, origin, filepath, details={}):
        return self.executeScript(origin, 'saveMaxFile "%s"' % filepath)

    @err_catcher(name=__name__)
    def getImportPaths(self, origin):
        num = self.executeScript(
            origin, 'fileProperties.findProperty #custom "PrismImports"'
        )
        if num == 0:
            return False
        else:
            return self.executeScript(
                origin, "fileProperties.getPropertyValue #custom %s" % num
            )

    @err_catcher(name=__name__)
    def getFrameRange(self, origin):
        startframe = self.executeScript(origin, "animationrange.start.frame")
        endframe = self.executeScript(origin, "animationrange.end.frame")

        return [startframe, endframe]

    @err_catcher(name=__name__)
    def getCurrentFrame(self):
        currentFrame = self.executeScript(self, "sliderTime.frame")
        return currentFrame

    @err_catcher(name=__name__)
    def setFrameRange(self, origin, startFrame, endFrame):
        if startFrame == endFrame:
            QMessageBox.warning(
                self.core.messageParent,
                "Warning",
                "The startframe and the endframe cannot be the same in 3dsMax.",
            )
            return

        MaxPlus.Animation.SetRange(
            MaxPlus.Interval(
                startFrame * MaxPlus.Animation.GetTicksPerFrame(),
                endFrame * MaxPlus.Animation.GetTicksPerFrame(),
            )
        )
        MaxPlus.Animation.SetTime(startFrame * MaxPlus.Animation.GetTicksPerFrame())

    @err_catcher(name=__name__)
    def getFPS(self, origin):
        return self.executeScript(origin, "frameRate")

    @err_catcher(name=__name__)
    def setFPS(self, origin, fps):
        return self.executeScript(origin, "frameRate = %s" % fps)

    @err_catcher(name=__name__)
    def getResolution(self):
        width = MaxPlus.RenderSettings.GetWidth()
        height = MaxPlus.RenderSettings.GetHeight()
        return [width, height]

    @err_catcher(name=__name__)
    def setResolution(self, width=None, height=None):
        if width:
            MaxPlus.RenderSettings.SetWidth(width)
        if height:
            MaxPlus.RenderSettings.SetHeight(height)

    @err_catcher(name=__name__)
    def getAppVersion(self, origin):
        return self.executeScript(origin, 'getFileVersion "$max/3dsmax.exe"').split()[0]

    @err_catcher(name=__name__)
    def onProjectBrowserStartup(self, origin):
        pass

    @err_catcher(name=__name__)
    def openScene(self, origin, filepath, force=False):
        if not filepath.endswith(".max"):
            return False

        if force or self.executeScript(origin, "checkforsave()"):
            self.executeScript(origin, 'loadMaxFile "%s" useFileUnits:true' % filepath)

        return True

    @err_catcher(name=__name__)
    def correctExt(self, origin, lfilepath):
        return lfilepath

    @err_catcher(name=__name__)
    def setSaveColor(self, origin, btn):
        btn.setPalette(origin.savedPalette)

    @err_catcher(name=__name__)
    def clearSaveColor(self, origin, btn):
        btn.setPalette(origin.oldPalette)

    @err_catcher(name=__name__)
    def setProject_loading(self, origin):
        pass

    @err_catcher(name=__name__)
    def onPrismSettingsOpen(self, origin):
        pass

    @err_catcher(name=__name__)
    def createProject_startup(self, origin):
        pass

    @err_catcher(name=__name__)
    def editShot_startup(self, origin):
        pass

    @err_catcher(name=__name__)
    def shotgunPublish_startup(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_export_addObjects(self, origin, objects=None):
        if not objects:
            objects = MaxPlus.SelectionManager_GetNodes()

        for i in objects:
            handle = i.GetHandle()
            if not handle in origin.nodes:
                origin.nodes.append(handle)

        origin.updateUi()
        origin.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def getNodeName(self, origin, node):
        if self.isNodeValid(origin, node):
            return MaxPlus.INode.GetINodeByHandle(node).GetName()
        else:
            return origin.nodeNames[origin.nodes.index(node)]

    @err_catcher(name=__name__)
    def selectNodes(self, origin):
        if origin.lw_objects.selectedItems() != []:
            MaxPlus.SelectionManager_ClearNodeSelection()
            nodes = MaxPlus.INodeTab()
            for i in origin.lw_objects.selectedItems():
                node = origin.nodes[origin.lw_objects.row(i)]
                if self.isNodeValid(origin, node):
                    nodes.Append(MaxPlus.INode.GetINodeByHandle(node))
            MaxPlus.SelectionManager_SelectNodes(nodes)

    @err_catcher(name=__name__)
    def isNodeValid(self, origin, handle):
        return not (
            handle is None
            or MaxPlus.INode.GetINodeByHandle(handle).GetUnwrappedPtr() is None
        )

    @err_catcher(name=__name__)
    def getCamNodes(self, origin, cur=False):
        cams = self.executeScript(
            origin, "for i in cameras where (superclassof i) == camera collect i"
        )
        sceneCams = [cams.GetItem(x).GetHandle() for x in range(cams.GetCount())]
        if cur:
            sceneCams = ["Current View"] + sceneCams

        return sceneCams

    @err_catcher(name=__name__)
    def getCamName(self, origin, handle):
        if handle == "Current View":
            return handle

        if type(handle) != long:
            try:
                handle = long(handle)
            except:
                return "invalid"

        node = MaxPlus.INode.GetINodeByHandle(handle)

        if node.GetUnwrappedPtr() is None:
            return "invalid"
        else:
            return node.GetName()

    @err_catcher(name=__name__)
    def selectCam(self, origin):
        if self.isNodeValid(origin, origin.curCam):
            MaxPlus.SelectionManager_ClearNodeSelection()
            camNode = MaxPlus.INode.GetINodeByHandle(origin.curCam)
            if camNode.GetTarget().GetUnwrappedPtr() is not None:
                camNodes = MaxPlus.INodeTab()
                camNodes.Append(camNode)
                camNodes.Append(camNode.GetTarget())
                MaxPlus.SelectionManager_SelectNodes(camNodes)
            else:
                MaxPlus.SelectionManager_SelectNode(camNode)

    @err_catcher(name=__name__)
    def sm_export_startup(self, origin):
        origin.lw_objects.setStyleSheet("QListWidget { background: rgb(100,100,100);}")

    @err_catcher(name=__name__)
    def sm_export_removeSetItem(self, origin, node):
        pass

    @err_catcher(name=__name__)
    def sm_export_clearSet(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_export_updateObjects(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_export_exportShotcam(self, origin, startFrame, endFrame, outputName):
        if startFrame == endFrame:
            self.setFrameRange(origin, startFrame=startFrame, endFrame=endFrame + 1)
        else:
            self.setFrameRange(origin, startFrame=startFrame, endFrame=endFrame)

        self.executeScript(origin, "AlembicExport.CoordinateSystem = #Maya")

        if self.executeScript(origin, 'getFileVersion "$max/3dsmax.exe"')[:2] in [
            "19",
            "20",
        ]:
            self.executeScript(origin, "AlembicExport.CacheTimeRange = #StartEnd")
            self.executeScript(origin, "AlembicExport.StepFrameTime = 1")
            self.executeScript(
                origin, "AlembicExport.StartFrameTime = %s" % startFrame
            )
            self.executeScript(origin, "AlembicExport.EndFrameTime = %s" % endFrame)
            self.executeScript(origin, "AlembicExport.ParticleAsMesh = False")
        else:
            self.executeScript(origin, "AlembicExport.AnimTimeRange = #StartEnd")
            self.executeScript(origin, "AlembicExport.SamplesPerFrame = 1")
            self.executeScript(origin, "AlembicExport.StartFrame = %s" % startFrame)
            self.executeScript(origin, "AlembicExport.EndFrame = %s" % endFrame)
            self.executeScript(origin, "AlembicExport.ParticleAsMesh = False")

        if startFrame == endFrame:
            self.executeScript(
                origin, 'FbxExporterSetParam "Animation" False', returnVal=False
            )
            MaxPlus.Animation.SetTime(
                startFrame * MaxPlus.Animation.GetTicksPerFrame(), False
            )
        else:
            self.executeScript(
                origin, 'FbxExporterSetParam "Animation" True', returnVal=False
            )

        self.selectCam(origin)
        MaxPlus.FileManager.ExportSelected(outputName + ".abc", True)

        exportFBX = self.executeScript(
            origin, "(classof (maxOps.getNodeByHandle %s)) != Physical" % origin.curCam
        )

        if exportFBX:
            self.selectCam(origin)
            MaxPlus.FileManager.ExportSelected(outputName + ".fbx", True)

        if origin.chb_convertExport.isChecked():
            outputName = os.path.join(
                os.path.dirname(os.path.dirname(outputName)),
                "meter",
                os.path.basename(outputName),
            )
            if not os.path.exists(os.path.dirname(outputName)):
                os.makedirs(os.path.dirname(outputName))
            self.executeScript(
                origin,
                """
sHelper = point()
sHelper.name = ("SCALEOVERRIDE_%s")
for obj in selection do(
	obj.parent = sHelper
)
sVal = 0.01
sHelper.scale = [sVal, sVal, sVal]
"""
                % MaxPlus.INode.GetINodeByHandle(origin.curCam).GetName(),
            )

            self.selectCam(origin)
            MaxPlus.FileManager.ExportSelected(outputName + ".abc", True)

            if exportFBX:
                self.selectCam(origin)
                MaxPlus.FileManager.ExportSelected(outputName + ".fbx", True)

            self.executeScript(
                origin,
                """
for obj in selection do(
	if obj.parent != undefined and obj.parent.name == ("SCALEOVERRIDE_" + obj.name) do (
		sVal = 1
		sHelper = obj.parent
		sHelper.scale = [sVal, sVal, sVal]
		delete sHelper
	)
)
""",
            )

        MaxPlus.SelectionManager_ClearNodeSelection(False)

    @err_catcher(name=__name__)
    def sm_export_exportAppObjects(
        self,
        origin,
        startFrame,
        endFrame,
        outputName,
        scaledExport=False,
        expNodes=None,
    ):
        if startFrame == endFrame:
            self.setFrameRange(origin, startFrame=startFrame, endFrame=endFrame + 1)
        else:
            self.setFrameRange(origin, startFrame=startFrame, endFrame=endFrame)

        if expNodes is None:
            expNodes = origin.nodes

        if not origin.chb_wholeScene.isChecked() or scaledExport:
            MaxPlus.SelectionManager_ClearNodeSelection(False)
            nodes = MaxPlus.INodeTab()
            for node in expNodes:
                if self.isNodeValid(origin, node):
                    nodes.Append(MaxPlus.INode.GetINodeByHandle(node))
            MaxPlus.SelectionManager_SelectNodes(nodes)

        if origin.cb_outType.currentText() == ".obj":
            for i in range(startFrame, endFrame + 1):
                MaxPlus.Animation.SetTime(
                    i * MaxPlus.Animation.GetTicksPerFrame(), False
                )
                foutputName = outputName.replace("####", format(i, "04"))
                if origin.chb_wholeScene.isChecked():
                    MaxPlus.FileManager.Export(
                        foutputName, not origin.chb_additionalOptions.isChecked()
                    )
                else:
                    MaxPlus.FileManager.ExportSelected(
                        foutputName, not origin.chb_additionalOptions.isChecked()
                    )

            outputName = foutputName
        elif origin.cb_outType.currentText() == ".fbx":
            if startFrame == endFrame:
                self.executeScript(
                    origin, 'FbxExporterSetParam "Animation" False', returnVal=False
                )
                MaxPlus.Animation.SetTime(
                    startFrame * MaxPlus.Animation.GetTicksPerFrame(), False
                )
            else:
                self.executeScript(
                    origin, 'FbxExporterSetParam "Animation" True', returnVal=False
                )
            if origin.chb_wholeScene.isChecked():
                MaxPlus.FileManager.Export(
                    outputName, not origin.chb_additionalOptions.isChecked()
                )
            else:
                MaxPlus.FileManager.ExportSelected(
                    outputName, not origin.chb_additionalOptions.isChecked()
                )

        elif origin.cb_outType.currentText() == ".abc":
            self.executeScript(origin, "AlembicExport.CoordinateSystem = #Maya")
            if self.executeScript(origin, 'getFileVersion "$max/3dsmax.exe"')[:2] in [
                "19",
                "20",
            ]:
                self.executeScript(origin, "AlembicExport.CacheTimeRange = #StartEnd")
                self.executeScript(origin, "AlembicExport.StepFrameTime = 1")
                self.executeScript(
                    origin, "AlembicExport.StartFrameTime = %s" % startFrame
                )
                self.executeScript(origin, "AlembicExport.EndFrameTime = %s" % endFrame)
                self.executeScript(origin, "AlembicExport.ParticleAsMesh = False")
            else:
                self.executeScript(origin, "AlembicExport.AnimTimeRange = #StartEnd")
                self.executeScript(origin, "AlembicExport.SamplesPerFrame = 1")
                self.executeScript(origin, "AlembicExport.StartFrame = %s" % startFrame)
                self.executeScript(origin, "AlembicExport.EndFrame = %s" % endFrame)
                self.executeScript(origin, "AlembicExport.ParticleAsMesh = False")
            if origin.chb_wholeScene.isChecked():
                MaxPlus.FileManager.Export(
                    outputName, not origin.chb_additionalOptions.isChecked()
                )
            else:
                MaxPlus.FileManager.ExportSelected(
                    outputName, not origin.chb_additionalOptions.isChecked()
                )
        elif origin.cb_outType.currentText() == ".max":
            if origin.chb_wholeScene.isChecked():
                MaxPlus.FileManager.Save(outputName, True, False)
            else:
                MaxPlus.FileManager.SaveSelected(outputName)

        if not origin.chb_wholeScene.isChecked():
            MaxPlus.SelectionManager_ClearNodeSelection(False)

        if scaledExport:
            nodes = MaxPlus.INodeTab()
            for i in expNodes:
                iNode = MaxPlus.INode.GetINodeByHandle(i)
                nodes.Append(iNode)
                scaleHelper = MaxPlus.INode.GetINodeByName(
                    "SCALEOVERRIDE_" + iNode.GetName()
                )
                if scaleHelper.GetUnwrappedPtr() is not None:
                    nodes.Append(scaleHelper)

            MaxPlus.INode.DeleteNodes(nodes)
        elif origin.chb_convertExport.isChecked():
            fileName = os.path.splitext(os.path.basename(outputName))
            if fileName[1] == ".max":
                MaxPlus.FileManager.Merge(outputName, True, True)
            else:
                if fileName[1] == ".abc":
                    self.executeScript(origin, "AlembicImport.ImportToRoot = True")
                elif fileName[1] == ".fbx":
                    self.executeScript(origin, 'FBXImporterSetParam "Mode" #create')
                    self.executeScript(origin, 'FBXImporterSetParam "ConvertUnit" #cm')
                self.executeScript(
                    origin,
                    """
fn checkDialog = (
	local hwnd = dialogMonitorOps.getWindowHandle()
	if (uiAccessor.getWindowText hwnd == "Import Name Conflict") then (
		uiAccessor.PressButtonByName hwnd "OK"
	)
	true
)

dialogMonitorOps.enabled = true
dialogMonitorOps.registerNotification checkDialog id:#test
""",
                )
                MaxPlus.FileManager.Import(outputName, True)
                self.executeScript(
                    origin,
                    """
dialogMonitorOps.unRegisterNotification id:#test
dialogMonitorOps.enabled = false""",
                )

            impNodes = [x.GetHandle() for x in MaxPlus.SelectionManager_GetNodes()]
            scaleNodes = [
                x
                for x in impNodes
                if (MaxPlus.INode.GetINodeByHandle(x)).GetParent().GetName()
                == "Scene Root"
            ]
            for i in scaleNodes:
                self.executeScript(
                    origin,
                    """obj = (maxOps.getNodeByHandle %s)
sHelper = point()
sHelper.name = ("SCALEOVERRIDE_" + obj.name)
obj.parent = sHelper
sVal = 0.01
sHelper.scale = [sVal, sVal, sVal]"""
                    % i,
                )

            MaxPlus.Animation.SetTime(
                origin.sp_rangeStart.value() * MaxPlus.Animation.GetTicksPerFrame()
            )
            # 		for i in impNodes:
            # 			self.executeScript(origin, "ResetXForm (maxOps.getNodeByHandle %s)" % i)

            outputName = os.path.join(
                os.path.dirname(os.path.dirname(outputName)),
                "meter",
                os.path.basename(outputName),
            )
            if not os.path.exists(os.path.dirname(outputName)):
                os.makedirs(os.path.dirname(outputName))

            outputName = self.sm_export_exportAppObjects(
                origin,
                startFrame,
                endFrame,
                outputName,
                scaledExport=True,
                expNodes=impNodes,
            )

        return outputName

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

    @err_catcher(name=__name__)
    def sm_export_preExecute(self, origin, startFrame, endFrame):
        warnings = []

        if origin.cb_outType.currentText() != "ShotCam":
            if origin.cb_outType.currentText() != ".fbx":
                for handle in origin.nodes:
                    if not self.isNodeValid(origin, handle):
                        continue

                    if MaxPlus.INode.GetINodeByHandle(handle).IsHidden():
                        warnings.append(
                            [
                                "Some chosen objects are hidden.",
                                "Hidden objects are only supported with fbx exports.",
                                2,
                            ]
                        )
                        break

            if origin.chb_convertExport.isChecked():
                warnings.append(
                    [
                        "Unit conversion is enabled.",
                        "This causes a renaming of the exported converted objects.",
                        2,
                    ]
                )

        if (
            origin.cb_outType.currentText() == ".fbx"
            or origin.cb_outType.currentText() == "ShotCam"
            and startFrame == endFrame
        ):
            warnings.append(
                ["Single frame FBX exports will export Frame 0 only.", "", 2]
            )

        return warnings

    @err_catcher(name=__name__)
    def sm_render_isVray(self, origin):
        return self.executeScript(
            origin,
            'matchpattern (classof renderers.current as string) pattern: "V_Ray*"',
        )

    @err_catcher(name=__name__)
    def sm_render_setVraySettings(self, origin):
        if self.sm_render_isVray(origin):
            self.executeScript(
                origin,
                'rs = renderers.current\nif matchpattern (classof rs as string) pattern: "V_Ray*" then(\nrs.imageSampler_type = 1\nrs.twoLevel_baseSubdivs = %s\nrs.twoLevel_fineSubdivs = %s\nrs.twoLevel_threshold = %s\nrs.dmc_earlyTermination_threshold = %s)'
                % (
                    origin.sp_minSubdivs.value(),
                    origin.sp_maxSubdivs.value(),
                    origin.sp_cThres.value(),
                    origin.sp_nThres.value(),
                ),
            )

    @err_catcher(name=__name__)
    def sm_render_startup(self, origin):
        origin.sp_rangeStart.setValue(
            self.executeScript(origin, "animationrange.start.frame")
        )
        origin.sp_rangeEnd.setValue(
            self.executeScript(origin, "animationrange.end.frame")
        )

    @err_catcher(name=__name__)
    def sm_render_refreshPasses(self, origin):
        origin.lw_passes.clear()
        elementMgr = MaxPlus.RenderSettings.GetRenderElementMgr(0)
        for i in range(elementMgr.NumRenderElements()):
            element = elementMgr.GetRenderElement(i)
            item = QListWidgetItem(element.GetElementName())
            item.setToolTip(element.GetClassName())
            origin.lw_passes.addItem(item)

    @err_catcher(name=__name__)
    def sm_render_openPasses(self, origin, item=None):
        MaxPlus.RenderSettings.OpenDialog()

    @err_catcher(name=__name__)
    def removeAOV(self, aovName):
        elementMgr = MaxPlus.RenderSettings.GetRenderElementMgr(0)
        for i in range(elementMgr.NumRenderElements()):
            element = elementMgr.GetRenderElement(i)
            if element.GetElementName() == aovName:
                elementMgr.RemoveRenderElement(element)
                break

    @err_catcher(name=__name__)
    def sm_render_preSubmit(self, origin, rSettings):
        MaxPlus.RenderSettings.CloseDialog()

        elementMgr = MaxPlus.RenderSettings.GetRenderElementMgr(0)
        rSettings["elementsActive"] = MaxPlus.RenderElementMgr.GetElementsActive(
            elementMgr
        )
        MaxPlus.RenderElementMgr.SetElementsActive(
            elementMgr, origin.gb_passes.isChecked()
        )

        if origin.gb_passes.isChecked():
            for i in range(elementMgr.NumRenderElements()):
                element = elementMgr.GetRenderElement(i)
                passName = element.GetElementName()
                passOutputName = os.path.join(
                    os.path.dirname(os.path.dirname(rSettings["outputName"])),
                    passName,
                    os.path.basename(rSettings["outputName"]).replace(
                        "beauty", passName
                    ),
                )
                try:
                    os.makedirs(os.path.dirname(passOutputName))
                except:
                    pass
                self.executeScript(
                    origin,
                    '(maxOps.GetCurRenderElementMgr()).SetRenderElementFilename %s "%s"'
                    % (i, passOutputName.replace("\\", "\\\\")),
                    returnVal=False,
                )

        rSettings["savefile"] = MaxPlus.RenderSettings.GetSaveFile()
        rSettings["savefilepath"] = MaxPlus.RenderSettings.GetOutputFile()
        MaxPlus.RenderSettings.SetSaveFile(True)
        MaxPlus.RenderSettings.SetOutputFile(rSettings["outputName"])

    @err_catcher(name=__name__)
    def sm_render_startLocalRender(self, origin, outputName, rSettings):
        if origin.chb_resOverride.isChecked():
            rSettings["width"] = MaxPlus.RenderSettings.GetWidth()
            rSettings["height"] = MaxPlus.RenderSettings.GetHeight()
            MaxPlus.RenderSettings.SetWidth(origin.sp_resWidth.value())
            MaxPlus.RenderSettings.SetHeight(origin.sp_resHeight.value())

        rSettings["timetype"] = MaxPlus.RenderSettings.GetTimeType()
        rSettings["prev_start"] = MaxPlus.RenderSettings.GetStart()
        rSettings["prev_end"] = MaxPlus.RenderSettings.GetEnd()

        self.executeScript(origin, "rendUseActiveView = True")
        if origin.curCam != "Current View":
            MaxPlus.Viewport.SetViewCamera(
                MaxPlus.ViewportManager.GetActiveViewport(),
                MaxPlus.INode.GetINodeByHandle(origin.curCam),
            )

        if rSettings["startFrame"] is None:
            frameChunks = [[x, x] for x in rSettings["frames"]]
        else:
            frameChunks = [[rSettings["startFrame"], rSettings["endFrame"]]]

        try:
            for frameChunk in frameChunks:
                if rSettings["rangeType"] == "Single Frame":
                    timeType = 0
                else:
                    timeType = 2
                MaxPlus.RenderSettings.SetTimeType(timeType)
                MaxPlus.RenderSettings.SetStart(
                    frameChunk[0] * MaxPlus.Animation.GetTicksPerFrame()
                )
                MaxPlus.RenderSettings.SetEnd(
                    frameChunk[1] * MaxPlus.Animation.GetTicksPerFrame()
                )
                self.executeScript(origin, "max quick render")

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
            elementMgr = MaxPlus.RenderSettings.GetRenderElementMgr(0)
            MaxPlus.RenderElementMgr.SetElementsActive(
                elementMgr, rSettings["elementsActive"]
            )
        if "width" in rSettings:
            MaxPlus.RenderSettings.SetWidth(rSettings["width"])
        if "height" in rSettings:
            MaxPlus.RenderSettings.SetHeight(rSettings["height"])
        if "timetype" in rSettings:
            MaxPlus.RenderSettings.SetTimeType(rSettings["timetype"])
        if "prev_start" in rSettings:
            MaxPlus.RenderSettings.SetStart(rSettings["prev_start"])
        if "prev_end" in rSettings:
            MaxPlus.RenderSettings.SetEnd(rSettings["prev_end"])
        if "savefile" in rSettings:
            MaxPlus.RenderSettings.SetSaveFile(rSettings["savefile"])
        if "savefilepath" in rSettings:
            MaxPlus.RenderSettings.SetOutputFile(rSettings["savefilepath"])

    @err_catcher(name=__name__)
    def sm_render_getDeadlineParams(self, origin, dlParams, homeDir):
        maxversion = self.executeScript(origin, "maxversion()").GetItem(0)
        if type(maxversion) != int:
            maxversion = maxversion.GetInt()
        dlParams["pluginInfoFile"] = os.path.join(
            homeDir, "temp", "3dsmax_plugin_info.job"
        )
        dlParams["jobInfoFile"] = os.path.join(
            homeDir, "temp", "3dsmax_submit_info.job"
        )

        dlParams["jobInfos"]["Plugin"] = "3dsmax"
        dlParams["jobInfos"]["Comment"] = "Prism-Submission-3dsmax_ImageRender"
        dlParams["pluginInfos"]["Version"] = str(maxversion / 1000 - 2 + 2000)
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

    @err_catcher(name=__name__)
    def getCurrentRenderer(self, origin):
        return self.executeScript(origin, "classof renderers.current as string")

    @err_catcher(name=__name__)
    def getCurrentSceneFiles(self, origin):
        return [self.core.getCurrentFileName()]

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
        if self.executeScript(origin, passName) is not None:
            self.executeScript(
                origin,
                "(MaxOps.GetCurRenderElementMgr()).AddRenderElement(%s())" % passName,
            )

    @err_catcher(name=__name__)
    def sm_render_preExecute(self, origin):
        warnings = []

        if self.sm_render_isVray(origin):
            if self.executeScript(origin, "renderers.current.output_on"):
                warnings.append(["VrayFrameBuffer is activated.", "", 2])

            if self.executeScript(origin, "renderers.current.system_frameStamp_on"):
                warnings.append(["FrameStamp is activated.", "", 2])

            if self.executeScript(origin, "vrayVFBGetRegionEnabled()"):
                warnings.append(["Region rendering is enabled.", "", 2])

        return warnings

    @err_catcher(name=__name__)
    def deleteNodes(self, origin, handles):
        nodes = MaxPlus.INodeTab()
        for i in handles:
            nodes.Append(MaxPlus.INode.GetINodeByHandle(i))

        xref = self.executeScript(
            origin,
            "item = objXRefMgr.IsNodeXRefed (maxOps.getNodeByHandle %s)\n\
if item == undefined then (\n\
	False\n\
) else (\n\
	objXRefMgr.RemoveRecordFromScene item.xrefRecord\n\
	True\n\
)\n\
"
            % handles[0],
        )

        if not xref:
            MaxPlus.INode.DeleteNodes(nodes)

    @err_catcher(name=__name__)
    def onSelectTaskOpen(self, origin):
        origin.l_versionRight.setText(
            "(Press CTRL and double click a version to show the import options)"
        )

    @err_catcher(name=__name__)
    def sm_import_startup(self, origin):
        origin.f_abcPath.setVisible(True)
        origin.b_unitConversion.setText("m -> cm")

    @err_catcher(name=__name__)
    def sm_import_importToApp(self, origin, doImport, update, impFileName):
        impFileName = os.path.normpath(impFileName)
        fileName = os.path.splitext(os.path.basename(impFileName))

        if fileName[1] == ".max":
            validNodes = [x for x in origin.nodes if self.isNodeValid(origin, x)]
            if not update or len(validNodes) == 0:
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
                    self.executeScript(
                        origin,
                        """
(
	item = objXRefMgr.IsNodeXRefed (maxOps.getNodeByHandle %s)
	item != undefined
)"""
                        % validNodes[0],
                    )
                )

            if action == 0:
                createNewXref = True

                if len(validNodes) > 0:
                    isXref = self.executeScript(
                        origin,
                        """
(
	item = objXRefMgr.IsNodeXRefed (maxOps.getNodeByHandle %s)
	item != undefined
)"""
                        % validNodes[0],
                    )

                    if isXref:
                        createNewXref = False
                        result = self.executeScript(
                            origin,
                            """
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
                            % (validNodes[0], impFileName.replace("\\", "\\\\")),
                        )
                    else:
                        origin.preDelete(
                            baseText="Do you want to delete the currently connected objects?\n\n"
                        )

                if createNewXref:
                    result = self.executeScript(
                        origin,
                        '(\n\
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
                result = MaxPlus.FileManager.Merge(impFileName, True, True)
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
                        MaxPlus.INode.GetINodeByHandle(
                            i
                        ).BaseObject.ParameterBlock.source.Value = impFileName
                        result = True
                        doImport = False
                self.executeScript(origin, "AlembicImport.ImportToRoot = True")
            elif fileName[1] == ".fbx":
                self.executeScript(origin, 'FBXImporterSetParam "Mode" #create')
                self.executeScript(origin, 'FBXImporterSetParam "ConvertUnit" #cm')
                prevLayers = []
                for i in range(MaxPlus.LayerManager.GetNumLayers()):
                    prevLayers.append(MaxPlus.LayerManager.GetLayer(i))

            if doImport:
                showProps = True
                modifiers = QApplication.keyboardModifiers()
                if modifiers == Qt.ControlModifier:
                    showProps = False

                result = MaxPlus.FileManager.Import(impFileName, showProps)

            if fileName[1] == ".fbx":
                delLayers = []
                for i in range(MaxPlus.LayerManager.GetNumLayers()):
                    curLayer = MaxPlus.LayerManager.GetLayer(i)
                    if not curLayer in prevLayers and not curLayer.Used():
                        delLayers.append(curLayer.GetName())

                for i in delLayers:
                    MaxPlus.LayerManager.DeleteLayer(i)

        if doImport:
            importedNodes = [x.GetHandle() for x in MaxPlus.SelectionManager_GetNodes()]

            if origin.chb_trackObjects.isChecked():
                origin.nodes = importedNodes

        if origin.taskName == "ShotCam":
            self.executeScript(origin, "setTransformLockFlags selection #all")
            camLayer = MaxPlus.LayerManager_GetLayer("00_Cams")
            if camLayer.GetUnwrappedPtr() is not None:
                for i in origin.nodes:
                    camLayer.AddToLayer(MaxPlus.INode.GetINodeByHandle(i))

        return {"result": result, "doImport": doImport}

    @err_catcher(name=__name__)
    def sm_import_updateObjects(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_import_removeNameSpaces(self, origin):
        for i in origin.nodes:
            if not self.isNodeValid(origin, i):
                continue

            nodeName = self.getNodeName(origin, i)
            newName = nodeName.rsplit(":", 1)[-1]
            if newName != nodeName:
                MaxPlus.INode.GetINodeByHandle(i).SetName(newName)

        origin.updateUi()

    @err_catcher(name=__name__)
    def sm_import_unitConvert(self, origin):
        if origin.taskName == "ShotCam":
            for i in origin.nodes:
                if not self.isNodeValid(origin, i):
                    continue

                self.executeScript(
                    origin,
                    """
scaleVal = 100
obj = (maxOps.getNodeByHandle %s)
obj.transform=obj.transform*(matrix3 [scaleVal,0,0] [0,scaleVal,0] [0,0,scaleVal] [0,0,0])
"""
                    % i,
                )
        else:
            QMessageBox.information(
                self.core.messageParent,
                "Unit conversion",
                "Please note that only vertex transformations will be converted. Object transformations and offset from origin are not supported.\nYou can delete the XForm modifier on the imported objects to undo the unit conversion.",
            )
            for i in origin.nodes:
                if not self.isNodeValid(origin, i):
                    continue

                self.executeScript(
                    origin,
                    """
obj = (maxOps.getNodeByHandle %s)
addmodifier obj (XForm())
obj.modifiers[1].gizmo.scale = [100,100,100]
"""
                    % i,
                )

    @err_catcher(name=__name__)
    def sm_import_updateListItem(self, origin, item, node):
        if self.isNodeValid(origin, node):
            item.setBackground(QColor(0, 150, 0))
        else:
            item.setBackground(QColor(150, 0, 0))

    @err_catcher(name=__name__)
    def sm_playblast_startup(self, origin):
        frange = self.getFrameRange(origin)
        origin.sp_rangeStart.setValue(frange[0])
        origin.sp_rangeEnd.setValue(frange[1])
        origin.cb_rangeType.removeItem(origin.cb_rangeType.findText("Single Frame"))

    @err_catcher(name=__name__)
    def sm_playblast_createPlayblast(self, origin, jobFrames, outputName):
        if origin.curCam is not None:
            MaxPlus.Viewport.SetViewCamera(
                MaxPlus.ViewportManager.GetActiveViewport(),
                MaxPlus.INode.GetINodeByHandle(origin.curCam),
            )
            # prevSettings = MaxPlus.PreviewParams.GetViewportPreview()

            # prevSettings.SetStart(jobFrames[0])
            # prevSettings.SetEnd(jobFrames[1])

            # MaxPlus.RenderExecute.CreatePreview(prevSettings)

        if origin.chb_resOverride.isChecked():
            MaxPlus.RenderSettings.SetWidth(origin.sp_resWidth.value())
            MaxPlus.RenderSettings.SetHeight(origin.sp_resHeight.value())

        self.executeScript(
            origin,
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

    @err_catcher(name=__name__)
    def sm_setActivePalette(self, origin, listWidget, inactive, inactivef, activef):
        activef.setPalette(origin.activePalette)
        inactivef.setPalette(origin.inactivePalette)

    @err_catcher(name=__name__)
    def sm_preExecute(self, origin):
        origin.origTimeRange = MaxPlus.Animation.GetAnimRange()
        origin.origTime = MaxPlus.Animation.GetTime()

    @err_catcher(name=__name__)
    def sm_postExecute(self, origin):
        MaxPlus.Animation.SetRange(origin.origTimeRange)
        MaxPlus.Animation.SetTime(origin.origTime)

    @err_catcher(name=__name__)
    def onStateManagerOpen(self, origin):
        origin.disabledCol = QColor(40, 40, 40)
        origin.activePalette = QPalette()
        origin.activePalette.setColor(QPalette.Window, QColor(150, 150, 150))
        origin.inactivePalette = QPalette()
        origin.inactivePalette.setColor(QPalette.Window, QColor(68, 68, 68))
        origin.f_import.setAutoFillBackground(True)
        origin.f_export.setAutoFillBackground(True)
        startframe = self.executeScript(origin, "animationrange.start.frame")
        endframe = self.executeScript(origin, "animationrange.end.frame")
        origin.sp_rangeStart.setValue(startframe)
        origin.sp_rangeEnd.setValue(endframe)
        origin.shotcamFileType = ".fbx"

        if not origin.core.smCallbacksRegistered:
            MaxPlus.NotificationManager.Register(
                MaxPlus.NotificationCodes.FilePostSave, origin.core.scenefileSaved
            )
            MaxPlus.NotificationManager.Register(
                MaxPlus.NotificationCodes.PostSceneReset, origin.core.sceneUnload
            )
            MaxPlus.NotificationManager.Register(
                MaxPlus.NotificationCodes.FilePreOpen, origin.core.sceneUnload
            )

    @err_catcher(name=__name__)
    def sm_saveStates(self, origin, buf):
        self.executeScript(
            origin,
            'fileProperties.addProperty #custom "PrismStates" "%s"'
            % buf.replace('"', '\\"'),
        )

    @err_catcher(name=__name__)
    def sm_saveImports(self, origin, importPaths):
        self.executeScript(
            origin,
            'fileProperties.addProperty #custom "PrismImports" "%s"' % importPaths,
        )

    @err_catcher(name=__name__)
    def sm_readStates(self, origin):
        num = self.executeScript(
            origin, 'fileProperties.findProperty #custom "PrismStates"'
        )
        if num != 0:
            return self.executeScript(
                origin, "fileProperties.getPropertyValue #custom %s" % num
            )

    @err_catcher(name=__name__)
    def sm_deleteStates(self, origin):
        num = self.executeScript(
            origin, 'fileProperties.findProperty #custom "PrismStates"'
        )
        if num != 0:
            self.executeScript(
                origin, 'fileProperties.deleteProperty #custom "PrismStates"'
            )

    def sm_getExternalFiles(self, origin):
        extFiles = self.executeScript(
            origin,
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
    def sm_createRenderPressed(self, origin):
        origin.createPressed("Render")
