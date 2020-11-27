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
import threading
import platform
import traceback
import time
import shutil
import logging
import operator

import bpy

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
    del sys.modules["widget_import_scenedata"]
except:
    pass

import widget_import_scenedata
from PrismUtils.Decorators import err_catcher as err_catcher

logger = logging.getLogger(__name__)


class bldRenderTimer(QObject):
    finished = Signal()

    def __init__(self, thread):
        QObject.__init__(self)
        self.thread = thread
        self.active = True

    def run(self):
        try:
            # The time interval after which the timer checks if the rendering is finished(in seconds)
            duration = 1

            t = threading.Timer(duration, self.stopThread)
            t.start()

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            erStr = "ERROR - bldRenderTimer run:\n%s" % traceback.format_exc()
            print(erStr)

    def stopThread(self):
        if self.active:
            self.finished.emit()


def renderFinished_handler(dummy):
    bpy.context.scene["PrismIsRendering"] = False


class Prism_Blender_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

    @err_catcher(name=__name__)
    def startup(self, origin):
        if platform.system() == "Linux":
            origin.timer.stop()

            if "prism_project" in os.environ and os.path.exists(
                os.environ["prism_project"]
            ):
                curPrj = os.environ["prism_project"]
            else:
                curPrj = self.core.getConfig("globals", "current project")

            if curPrj != "":
                self.core.changeProject(curPrj)
            return False

        try:
            bpy.data.filepath
        except:
            return False

        origin.timer.stop()

        origin.startasThread()

    @err_catcher(name=__name__)
    def autosaveEnabled(self, origin):
        if bpy.app.version < (2, 80, 0):
            return bpy.context.user_preferences.filepaths.use_auto_save_temporary_files
        else:
            return bpy.context.preferences.filepaths.use_auto_save_temporary_files

    @err_catcher(name=__name__)
    def onProjectChanged(self, origin):
        pass

    @err_catcher(name=__name__)
    def sceneOpen(self, origin):
        if hasattr(origin, "asThread") and origin.asThread.isRunning():
            origin.startasThread()

    @err_catcher(name=__name__)
    def executeScript(self, origin, code):
        try:
            return eval(code)
        except Exception as e:
            raise type(e)(str(e) + "\npython code:\n%s" % code).with_traceback(
                sys.exc_info()[2]
            )

    @err_catcher(name=__name__)
    def getCurrentFileName(self, origin, path=True):
        currentFileName = bpy.data.filepath

        if not path:
            currentFileName = os.path.basename(currentFileName)

        return currentFileName

    @err_catcher(name=__name__)
    def getSceneExtension(self, origin):
        return self.sceneFormats[0]

    @err_catcher(name=__name__)
    def saveScene(self, origin, filepath, details={}):
        return bpy.ops.wm.save_as_mainfile(filepath=filepath)

    @err_catcher(name=__name__)
    def getImportPaths(self, origin):
        if not "PrismImports" in bpy.context.scene:
            return False
        else:
            return bpy.context.scene["PrismImports"]

    @err_catcher(name=__name__)
    def getFrameRange(self, origin):
        startframe = bpy.context.scene.frame_start
        endframe = bpy.context.scene.frame_end

        return [startframe, endframe]

    @err_catcher(name=__name__)
    def getCurrentFrame(self):
        currentFrame = bpy.context.scene.frame_current
        return currentFrame

    @err_catcher(name=__name__)
    def setFrameRange(self, origin, startFrame, endFrame):
        bpy.context.scene.frame_start = startFrame
        bpy.context.scene.frame_end = endFrame
        bpy.context.scene.frame_current = startFrame
        bpy.ops.action.view_all(self.getOverrideContext(origin, context="DOPESHEET_EDITOR"))

    @err_catcher(name=__name__)
    def getFPS(self, origin):
        return bpy.context.scene.render.fps

    @err_catcher(name=__name__)
    def setFPS(self, origin, fps):
        bpy.context.scene.render.fps = fps

    @err_catcher(name=__name__)
    def getResolution(self):
        width = bpy.context.scene.render.resolution_x
        height = bpy.context.scene.render.resolution_y
        return [width, height]

    @err_catcher(name=__name__)
    def setResolution(self, width=None, height=None):
        if width:
            bpy.context.scene.render.resolution_x = width
        if height:
            bpy.context.scene.render.resolution_y = height

    @err_catcher(name=__name__)
    def getAppVersion(self, origin):
        return bpy.app.version_string.split()[0]

    @err_catcher(name=__name__)
    def onProjectBrowserStartup(self, origin):
        if bpy.app.version < (2, 80, 0):
            origin.publicColor = QColor(50, 100, 170)

    @err_catcher(name=__name__)
    def openScene(self, origin, filepath, force=False):
        if not filepath.endswith(".blend"):
            return False

        bpy.ops.wm.open_mainfile(filepath=filepath)

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
        origin.resize(origin.width(), origin.height() + 60)

    @err_catcher(name=__name__)
    def getGroups(self):
        if bpy.app.version < (2, 80, 0):
            return bpy.data.groups
        else:
            return bpy.data.collections

    @err_catcher(name=__name__)
    def createGroups(self, name):
        if bpy.app.version < (2, 80, 0):
            bpy.ops.group.create(name=name)
        else:
            bpy.ops.collection.create(name=name)

    @err_catcher(name=__name__)
    def getSelectObject(self, obj):
        if bpy.app.version < (2, 80, 0):
            return obj.select
        else:
            return obj.select_get()

    @err_catcher(name=__name__)
    def selectObjects(self, objs, select=True, quiet=False):
        for obj in objs:
            self.selectObject(obj, select=select, quiet=quiet)

    @err_catcher(name=__name__)
    def selectObject(self, obj, select=True, quiet=False):
        if bpy.app.version < (2, 80, 0):
            obj.select = select
            bpy.context.scene.objects.active = obj
        else:
            curlayer = bpy.context.window_manager.windows[0].view_layer
            if obj not in list(curlayer.objects):
                obj_layer = None
                for vlayer in list(bpy.context.scene.view_layers):
                    if obj in list(vlayer.objects):
                        obj_layer = vlayer
                        break

                if obj_layer:
                    if quiet:
                        action = 1
                    else:
                        msgText = (
                            "The object '%s' is not on the current viewlayer, but it's on viewlayer '%s'.\nOnly objects on the current viewlayer can be selected, which is necessary to process this object.\n\nHow do you want to coninue?"
                            % (obj.name, obj_layer.name)
                        )
                        msg = QMessageBox(QMessageBox.Question, "Prism", msgText)
                        msg.addButton(
                            "Set viewlayer '%s' active" % obj_layer.name,
                            QMessageBox.YesRole,
                        )
                        msg.addButton("Skip object '%s'" % obj.name, QMessageBox.YesRole)

                        self.core.parentWindow(msg)
                        action = msg.exec_()

                    if action == 0:
                        bpy.context.window_manager.windows[0].view_layer = obj_layer
                        curlayer = obj_layer
                    elif action == 1:
                        return
                else:
                    if not quiet:
                        self.core.popup(
                            "The object '%s' is not on the current viewlayer and couldn't be found on any other viewlayer. This object can't be selected and will be skipped in the current process."
                            % obj.name
                        )
                    return

            obj.select_set(select, view_layer=curlayer)
            bpy.context.view_layer.objects.active = obj

    @err_catcher(name=__name__)
    def sm_export_addObjects(self, origin, objects=None):
        taskName = origin.getTaskname()
        if not taskName:
            taskName = self.sm_export_setTaskText(origin, None, "Export")

        if taskName not in self.getGroups():
            self.createGroups(name=taskName)

        if not objects:
            objects = [
                o
                for o in bpy.context.scene.objects
                if self.getSelectObject(o)
                and o not in list(self.getGroups()[taskName].objects)
            ]

        for i in objects:
            self.getGroups()[taskName].objects.link(i)

        origin.updateUi()
        origin.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def getNodeName(self, origin, node):
        return node["name"]

    @err_catcher(name=__name__)
    def selectNodes(self, origin):
        if origin.lw_objects.selectedItems() != []:
            bpy.ops.object.select_all(
                self.getOverrideContext(origin), action="DESELECT"
            )
            for i in origin.lw_objects.selectedItems():
                node = origin.nodes[origin.lw_objects.row(i)]
                if self.getObject(node):
                    self.selectObject(self.getObject(node))

    @err_catcher(name=__name__)
    def isNodeValid(self, origin, node):
        if type(node) == str:
            node = self.getNode(node)

        return bool(self.getObject(node))

    @err_catcher(name=__name__)
    def getCamNodes(self, origin, cur=False):
        return [x.name for x in bpy.context.scene.objects if x.type == "CAMERA"]

    @err_catcher(name=__name__)
    def getCamName(self, origin, handle):
        return handle

    @err_catcher(name=__name__)
    def selectCam(self, origin):
        if self.getObject(origin.curCam):
            bpy.ops.object.select_all(
                self.getOverrideContext(origin), action="DESELECT"
            )
            self.selectObject(self.getObject(origin.curCam))

    @err_catcher(name=__name__)
    def sm_export_startup(self, origin):
        if origin.className == "Export":
            origin.l_convertExport.setText("Additional export in centimeters:")
            origin.w_additionalOptions.setVisible(False)

    @err_catcher(name=__name__)
    def sm_export_setTaskText(self, origin, prevTaskName, newTaskName):
        setName = newTaskName
        extension = 1
        while setName in self.getGroups() and extension < 999:
            if "%s_%s" % (setName, extension) not in self.getGroups():
                setName += "_%s" % extension
            extension += 1

        if prevTaskName and prevTaskName in self.getGroups():
            self.getGroups()[prevTaskName].name = setName
        else:
            self.createGroups(name=setName)

        origin.l_taskName.setText(setName)
        return setName

    @err_catcher(name=__name__)
    def sm_export_removeSetItem(self, origin, node):
        if origin.getTaskname() not in self.getGroups():
            return

        self.getGroups()[origin.getTaskname()].objects.unlink(
            self.getObject(node)
        )

    @err_catcher(name=__name__)
    def sm_export_clearSet(self, origin):
        if origin.getTaskname() not in self.getGroups():
            return

        for node in self.getGroups()[origin.getTaskname()].objects:
            self.getGroups()[origin.getTaskname()].objects.unlink(node)

    @err_catcher(name=__name__)
    def sm_export_updateObjects(self, origin):
        origin.nodes = []
        taskName = origin.getTaskname()
        if taskName in self.getGroups():
            group = self.getGroups()[taskName]
            nodes = []
            for obj in group.objects:
                if not obj.users_scene:
                    group.objects.unlink(obj)
                    continue

                nodes.append(self.getNode(obj))

            origin.nodes = nodes

    @err_catcher(name=__name__)
    def sm_export_exportShotcam(self, origin, startFrame, endFrame, outputName):
        self.selectCam(origin)
        bpy.ops.wm.alembic_export(
            self.getOverrideContext(origin),
            filepath=(outputName + ".abc"),
            start=startFrame,
            end=endFrame,
            selected=True,
            as_background_job=False,
        )
        self.selectCam(origin)
        bpy.ops.export_scene.fbx(
            self.getOverrideContext(origin),
            filepath=(outputName + ".fbx"),
            use_selection=True,
        )

        if (
            origin.chb_convertExport.isChecked()
        ):  # disabled because of a blender bug (rescales animated object back to 1 on export)
            prevObjs = list(bpy.context.scene.objects)
            bpy.ops.object.empty_add(type="PLAIN_AXES")
            empObj = [x for x in bpy.context.scene.objects if x not in prevObjs][0]
            empObj.name = "SCALEOVERRIDE"
            empObj.location = [0, 0, 0]

            self.getObject(origin.curCam).parent = empObj
            sVal = 100
            empObj.scale = [sVal, sVal, sVal]

            outputName = os.path.join(
                os.path.dirname(os.path.dirname(outputName)),
                "centimeter",
                os.path.basename(outputName),
            )
            if not os.path.exists(os.path.dirname(outputName)):
                os.makedirs(os.path.dirname(outputName))

            self.selectCam(origin)
            bpy.ops.wm.alembic_export(
                self.getOverrideContext(origin),
                filepath=(outputName + ".abc"),
                start=startFrame,
                end=endFrame,
                selected=True,
                as_background_job=False,
            )
            self.selectCam(origin)
            bpy.ops.export_scene.fbx(
                self.getOverrideContext(origin),
                filepath=(outputName + ".fbx"),
                use_selection=True,
            )

            sVal = 0.01
            empObj.scale = [sVal, sVal, sVal]

            bpy.ops.object.select_all(
                self.getOverrideContext(origin), action="DESELECT"
            )
            self.selectObject(empObj)
            bpy.ops.object.delete(self.getOverrideContext(origin))

        bpy.ops.object.select_all(self.getOverrideContext(origin), action="DESELECT")

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
        if expNodes is None:
            expNodes = origin.nodes

        ctx = self.getOverrideContext(origin)
        if bpy.app.version >= (2, 80, 0):
            ctx.pop("screen")
            ctx.pop("area")
        bpy.ops.object.select_all(ctx, action="DESELECT")
        for i in expNodes:
            if self.getObject(i):
                self.selectObject(self.getObject(i))

        outType = origin.getOutputType()

        if outType == ".obj":
            for i in range(startFrame, endFrame + 1):
                bpy.context.scene.frame_current = i
                foutputName = outputName.replace("####", format(i, "04"))
                bpy.ops.export_scene.obj(
                    self.getOverrideContext(origin),
                    filepath=foutputName,
                    use_selection=(not origin.chb_wholeScene.isChecked()),
                )
            outputName = foutputName

        elif outType == ".fbx":
            useAnim = startFrame != endFrame
            if bpy.app.version >= (2, 79, 7):
                bpy.ops.export_scene.fbx(
                    self.getOverrideContext(origin),
                    filepath=outputName,
                    use_selection=(not origin.chb_wholeScene.isChecked()),
                    bake_anim=useAnim,
                    global_scale=0.01,
                )
            else:
                bpy.ops.export_scene.fbx(
                    self.getOverrideContext(origin),
                    filepath=outputName,
                    use_selection=(not origin.chb_wholeScene.isChecked()),
                    use_anim=useAnim,
                    global_scale=0.01,
                )

        elif outType == ".abc":
            bpy.ops.wm.alembic_export(
                self.getOverrideContext(origin),
                filepath=outputName,
                start=startFrame,
                end=endFrame,
                selected=(not origin.chb_wholeScene.isChecked()),
                as_background_job=False,
            )

        elif outType == ".usd":
            bpy.ops.wm.usd_export(
                self.getOverrideContext(origin),
                filepath=outputName,
                export_animation=startFrame!=endFrame,
                selected_objects_only=(not origin.chb_wholeScene.isChecked()),
            )

        elif outType == ".blend":
            if origin.chb_wholeScene.isChecked():
                shutil.copyfile(self.core.getCurrentFileName(), outputName)
            else:
                for object_ in bpy.data.objects:
                    if object_ not in [self.getObject(x) for x in expNodes]:
                        bpy.data.objects.remove(object_, do_unlink=True)
                bpy.ops.wm.save_as_mainfile(filepath=outputName, copy=True)
                bpy.ops.wm.revert_mainfile()
                self.core.stateManager()

        fileName = os.path.splitext(os.path.basename(outputName))
        if scaledExport:
            bpy.ops.wm.revert_mainfile()
        elif origin.className == "Export" and origin.chb_convertExport.isChecked():
            #   for i in expNodes:
            #       bpy.data.objects.remove(bpy.data.objects[i], True)
            #   existingNodes = list(bpy.data.objects)
            #   if fileName[1] == ".fbx":
            #       bpy.ops.import_scene.fbx(filepath=outputName, global_scale=100)
            #   elif fileName[1] == ".obj":
            #       bpy.ops.import_scene.obj(filepath=outputName)
            #   elif fileName[1] == ".abc":
            #       bpy.ops.wm.alembic_import(self.getOverrideContext(origin), filepath=outputName, set_frame_range=False, as_background_job=False)
            #   elif fileName[1] == ".blend":
            #       with bpy.data.libraries.load(outputName, link=False) as (data_from, data_to):
            #           data_to.objects = data_from.objects
            #
            #               for obj in data_to.objects:
            #                   if obj in existingNodes:
            #                       del existingNodes[existingNodes.index(obj)]
            #                   elif obj is not None:
            #                       bpy.context.scene.objects.link(obj)
            #
            #           impNodes = []
            #           for i in bpy.data.objects:
            #               if i not in existingNodes:
            #                   impNodes.append(i.name)

            bpy.context.scene.frame_current = origin.sp_rangeStart.value()

            scaleNodes = [x for x in expNodes if self.getObject(x).parent is None]
            bpy.ops.object.select_all(ctx, action="DESELECT")
            for i in scaleNodes:
                if self.getObject(i):
                    self.selectObject(self.getObject(i))
            # bpy.ops.object.transform_apply(self.getOverrideContext(origin), location=True, rotation=True, scale=True)

            for i in scaleNodes:
                prevObjs = list(bpy.context.scene.objects)
                bpy.ops.object.empty_add(type="PLAIN_AXES")
                empObj = [x for x in bpy.context.scene.objects if x not in prevObjs][0]
                empObj.name = "SCALEOVERRIDE_" + i["name"]
                empObj.location = [0, 0, 0]

                self.getObject(i).parent = empObj
                sVal = 100
                empObj.scale = [sVal, sVal, sVal]

            bpy.ops.object.select_all(ctx, action="DESELECT")
            for i in expNodes:
                if self.getObject(i):
                    self.selectObject(self.getObject(i))
            #   bpy.ops.object.transform_apply(self.getOverrideContext(origin), location=True, rotation=True, scale=True)

            outputName = os.path.join(
                os.path.dirname(os.path.dirname(outputName)),
                "centimeter",
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
                expNodes=expNodes,
            )

        bpy.ops.object.select_all(ctx, action="DESELECT")

        return outputName

    @err_catcher(name=__name__)
    def sm_export_preDelete(self, origin):
        try:
            self.getGroups().remove(self.getGroups()[origin.getTaskname()], True)
        except:
            pass

    @err_catcher(name=__name__)
    def getOverrideContext(self, origin, context=None):
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            if context:
                for area in screen.areas:
                    if area.type == context:
                        override = {"window": window, "screen": screen, "area": area}
                        for region in area.regions:
                            if region.type == 'WINDOW':
                                override = {"window": window, "screen": screen, "area": area, "region": region}
                                return override

            for area in screen.areas:
                if area.type == "VIEW_3D":
                    override = {"window": window, "screen": screen, "area": area}
                    return override

            for area in screen.areas:
                if area.type == "IMAGE_EDITOR":
                    override = {"window": window, "screen": screen, "area": area}
                    return override

    @err_catcher(name=__name__)
    def sm_export_preExecute(self, origin, startFrame, endFrame):
        warnings = []

        outType = origin.getOutputType()

        if outType != "ShotCam":
            if (
                outType == ".fbx"
                and startFrame != endFrame
                and bpy.app.version < (2, 80, 0)
            ):
                warnings.append(
                    [
                        "FBX animation export seems to be broken in Blender 2.79.",
                        "Please check the exported file for animation offsets.",
                        2,
                    ]
                )

        return warnings

    @err_catcher(name=__name__)
    def sm_render_isVray(self, origin):
        return False

    @err_catcher(name=__name__)
    def sm_render_setVraySettings(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_render_startup(self, origin):
        origin.gb_passes.setCheckable(False)
        origin.sp_rangeStart.setValue(bpy.context.scene.frame_start)
        origin.sp_rangeEnd.setValue(bpy.context.scene.frame_end)

        origin.b_resPresets.setMinimumWidth(30 * self.core.uiScaleFactor)
        origin.b_resPresets.setMinimumHeight(0)
        origin.b_resPresets.setMaximumHeight(500 * self.core.uiScaleFactor)

        origin.b_osSlaves.setMinimumWidth(50 * self.core.uiScaleFactor)

    @err_catcher(name=__name__)
    def sm_render_refreshPasses(self, origin):
        origin.lw_passes.clear()

        passNames = self.getNodeAOVs()
        logger.debug("node aovs: %s" % passNames)
        origin.b_addPasses.setVisible(not passNames)
        self.plugin.canDeleteRenderPasses = bool(not passNames)
        if not passNames:
            passNames = self.getViewLayerAOVs()
            logger.debug("viewlayer aovs: %s" % passNames)

        if passNames:
            origin.lw_passes.addItems(passNames)

    @err_catcher(name=__name__)
    def getNodeAOVs(self):
        if bpy.context.scene.node_tree is None or bpy.context.scene.use_nodes:
            return

        outNodes = [
            x for x in bpy.context.scene.node_tree.nodes if x.type == "OUTPUT_FILE"
        ]
        rlayerNodes = [
            x for x in bpy.context.scene.node_tree.nodes if x.type == "R_LAYERS"
        ]

        passNames = []

        for m in outNodes:
            connections = []
            for i in m.inputs:
                if len(list(i.links)) > 0:
                    connections.append(i.links[0])

            for i in connections:
                passName = i.from_socket.name

                if passName == "Image":
                    passName = "beauty"

                if i.from_node.type == "R_LAYERS":
                    if len(rlayerNodes) > 1:
                        passName = "%s_%s" % (i.from_node.layer, passName)

                else:
                    if hasattr(i.from_node, "label") and i.from_node.label != "":
                        passName = i.from_node.label

                passNames.append(passName)

        return passNames

    @err_catcher(name=__name__)
    def getViewLayerAOVs(self):
        availableAOVs = self.getAvailableAOVs()
        curlayer = bpy.context.window_manager.windows[0].view_layer
        aovNames = []
        for aa in availableAOVs:
            val = None
            try:
                val = operator.attrgetter(aa["parm"])(curlayer)
            except AttributeError:
                logging.debug("Couldn't access aov %s" % aa["parm"])

            if val:
                aovNames.append(aa["name"])

        return aovNames

    @err_catcher(name=__name__)
    def getAvailableAOVs(self):
        curlayer = bpy.context.window_manager.windows[0].view_layer
        aovParms = [x for x in dir(curlayer) if x.startswith("use_pass_")]
        aovParms += ["cycles." + x for x in dir(curlayer.cycles) if x.startswith("use_pass_")]
        aovs = [
            {"name": "Denoising Data", "parm": "cycles.denoising_store_passes"},
            {"name": "Render Time", "parm": "cycles.pass_debug_render_time"},
        ]
        nameOverrides = {
            "Emit": "Emission",
        }
        for aov in aovParms:
            name = aov.replace("use_pass_", "").replace("cycles.", "")
            name = [x[0].upper() + x[1:] for x in name.split("_")]
            name = " ".join(name)
            name = nameOverrides[name] if name in nameOverrides else name
            aovs.append({"name": name, "parm": aov})

        aovs = sorted(aovs, key= lambda x: x["name"])

        return aovs

    @err_catcher(name=__name__)
    def sm_render_openPasses(self, origin, item=None):
        pass

    @err_catcher(name=__name__)
    def useNodeAOVs(self):
        return bool(self.getNodeAOVs())

    @err_catcher(name=__name__)
    def removeAOV(self, aovName):
        if self.useNodeAOVs():
            rlayerNodes = [
                x for x in bpy.context.scene.node_tree.nodes if x.type == "R_LAYERS"
            ]

            for m in rlayerNodes:
                connections = []
                for i in m.outputs:
                    if len(list(i.links)) > 0:
                        connections.append(i.links[0])
                        break

                for i in connections:
                    if i.to_node.type == "OUTPUT_FILE":
                        for idx, k in enumerate(i.to_node.file_slots):
                            links = i.to_node.inputs[idx].links
                            if len(links) > 0:
                                if links[0].from_socket.node != m:
                                    continue

                                passName = links[0].from_socket.name
                                layerName = links[0].from_socket.node.layer

                                if passName == "Image":
                                    passName = "beauty"

                                if (
                                    passName == aovName.split("_", 1)[1]
                                    and layerName == aovName.split("_", 1)[0]
                                ):
                                    i.to_node.inputs.remove(i.to_node.inputs[idx])
                                    return
        else:
            self.enableViewLayerAOV(aovName, enable=False)

    @err_catcher(name=__name__)
    def enableViewLayerAOV(self, name, enable=True):
        aa = self.getAvailableAOVs()
        curAOV = [x for x in aa if x["name"] == name]
        if not curAOV:
            return

        curAOV = curAOV[0]
        curlayer = bpy.context.window_manager.windows[0].view_layer

        attrs = curAOV["parm"].split(".")
        obj = curlayer
        for a in attrs[:-1]:
            obj = getattr(obj, a)

        setattr(obj, attrs[-1], enable)

    @err_catcher(name=__name__)
    def sm_render_preSubmit(self, origin, rSettings):
        if origin.chb_resOverride.isChecked():
            rSettings["width"] = bpy.context.scene.render.resolution_x
            rSettings["height"] = bpy.context.scene.render.resolution_y
            bpy.context.scene.render.resolution_x = origin.sp_resWidth.value()
            bpy.context.scene.render.resolution_y = origin.sp_resHeight.value()

        nodeAOVs = self.getNodeAOVs()
        imgFormat = origin.cb_format.currentText()
        if imgFormat == ".exr":
            if not nodeAOVs and self.getViewLayerAOVs():
                fileFormat = "OPEN_EXR_MULTILAYER"
            else:
                fileFormat = "OPEN_EXR"
        elif imgFormat == ".png":
            fileFormat = "PNG"
        elif imgFormat == ".jpg":
            fileFormat = "JPEG"

        rSettings["prev_start"] = bpy.context.scene.frame_start
        rSettings["prev_end"] = bpy.context.scene.frame_end
        rSettings["fileformat"] = bpy.context.scene.render.image_settings.file_format
        rSettings["overwrite"] = bpy.context.scene.render.use_overwrite
        rSettings["fileextension"] = bpy.context.scene.render.use_file_extension
        rSettings["resolutionpercent"] = bpy.context.scene.render.resolution_percentage
        rSettings["origOutputName"] = rSettings["outputName"]
        bpy.context.scene["PrismIsRendering"] = True
        bpy.context.scene.render.filepath = rSettings["outputName"]
        bpy.context.scene.render.image_settings.file_format = fileFormat
        if imgFormat != ".jpg":
            bpy.context.scene.render.image_settings.color_depth = "16"
        bpy.context.scene.render.use_overwrite = True
        bpy.context.scene.render.use_file_extension = False
        bpy.context.scene.render.resolution_percentage = 100
        bpy.context.scene.camera = bpy.context.scene.objects[origin.curCam]

        usePasses = False
        if self.useNodeAOVs():
            outNodes = [
                x for x in bpy.context.scene.node_tree.nodes if x.type == "OUTPUT_FILE"
            ]
            rlayerNodes = [
                x for x in bpy.context.scene.node_tree.nodes if x.type == "R_LAYERS"
            ]

            for m in outNodes:
                connections = []
                for idx, i in enumerate(m.inputs):
                    if len(list(i.links)) > 0:
                        connections.append([i.links[0], idx])

                m.base_path = os.path.dirname(rSettings["outputName"])

                for i, idx in connections:
                    passName = i.from_socket.name

                    if passName == "Image":
                        passName = "beauty"

                    if i.from_node.type == "R_LAYERS":
                        if len(rlayerNodes) > 1:
                            passName = "%s_%s" % (i.from_node.layer, passName)

                    else:
                        if hasattr(i.from_node, "label") and i.from_node.label != "":
                            passName = i.from_node.label

                    extensions = {
                        "PNG": ".png",
                        "JPEG": ".jpg",
                        "JPEG2000": "jpg",
                        "TARGA": ".tga",
                        "TARGA_RAW": ".tga",
                        "OPEN_EXR_MULTILAYER": ".exr",
                        "OPEN_EXR": ".exr",
                        "TIFF": ".tif",
                    }
                    nodeExt = extensions[m.format.file_format]
                    curSlot = m.file_slots[idx]
                    if curSlot.use_node_format:
                        ext = nodeExt
                    else:
                        ext = extensions[curSlot.format.file_format]

                    curSlot.path = "../%s/%s" % (
                        passName,
                        os.path.splitext(os.path.basename(rSettings["outputName"]))[
                            0
                        ].replace("beauty", passName)
                        + ext,
                    )
                    newOutputPath = os.path.abspath(
                        os.path.join(
                            rSettings["outputName"],
                            "../..",
                            passName,
                            os.path.splitext(os.path.basename(rSettings["outputName"]))[
                                0
                            ].replace("beauty", passName)
                            + ext,
                        )
                    )
                    usePasses = True

        if usePasses:
            rSettings["outputName"] = newOutputPath
            if platform.system() == "Windows":
                tmpOutput = os.path.join(
                    os.environ["temp"], "PrismRender", "tmp.####" + imgFormat
                )
                bpy.context.scene.render.filepath = tmpOutput
                if not os.path.exists(os.path.dirname(tmpOutput)):
                    os.makedirs(os.path.dirname(tmpOutput))

    @err_catcher(name=__name__)
    def sm_render_startLocalRender(self, origin, outputName, rSettings):
        # renderAnim = bpy.context.scene.frame_start != bpy.context.scene.frame_end
        try:
            if not origin.renderingStarted:
                origin.waitmsg = QMessageBox(
                    QMessageBox.NoIcon,
                    "ImageRender",
                    "Local rendering - %s - please wait.." % origin.state.text(0),
                    QMessageBox.Cancel,
                )
            #    self.core.parentWindow(origin.waitmsg)
            #    origin.waitmsg.buttons()[0].setHidden(True)
            #    origin.waitmsg.show()
            #    QCoreApplication.processEvents()

                bpy.app.handlers.render_complete.append(renderFinished_handler)
                bpy.app.handlers.render_cancel.append(renderFinished_handler)

                self.renderedChunks = []

            ctx = self.getOverrideContext(origin)
            if bpy.app.version >= (2, 80, 0):
                ctx.pop("screen")
                ctx.pop("area")

            if rSettings["startFrame"] is None:
                frameChunks = [[x, x] for x in rSettings["frames"]]
            else:
                frameChunks = [[rSettings["startFrame"], rSettings["endFrame"]]]

            for frameChunk in frameChunks:
                if frameChunk in self.renderedChunks:
                    continue

                bpy.context.scene.frame_start = frameChunk[0]
                bpy.context.scene.frame_end = frameChunk[1]
                singleFrame = rSettings["rangeType"] == "Single Frame"
                bpy.ops.render.render(ctx, "INVOKE_DEFAULT", animation=not singleFrame, write_still=singleFrame)
                origin.renderingStarted = True
                origin.LastRSettings = rSettings

                self.startRenderThread(origin)
                self.renderedChunks.append(frameChunk)

                return "publish paused"

            origin.renderingStarted = False

            if hasattr(origin, "waitmsg") and origin.waitmsg.isVisible():
                origin.waitmsg.close()

            if len(os.listdir(os.path.dirname(outputName))) > 0:
                return "Result=Success"
            else:
                return "unknown error (files do not exist)"

        except Exception as e:
            if hasattr(origin, "waitmsg") and origin.waitmsg.isVisible():
                origin.waitmsg.close()

            exc_type, exc_obj, exc_tb = sys.exc_info()
            erStr = "%s ERROR - sm_default_imageRender %s:\n%s" % (
                time.strftime("%d/%m/%y %X"),
                origin.core.version,
                traceback.format_exc(),
            )
            self.core.writeErrorLog(erStr)
            return "Execute Canceled: unknown error (view console for more information)"

    @err_catcher(name=__name__)
    def CheckRenderFinished(self, origin):
        if not bpy.context.scene["PrismIsRendering"]:
            self.startRenderThread(origin, quit=True)
            origin.stateManager.publish(continuePublish=True)
            return

        self.startRenderThread(origin, restart=True)

    @err_catcher(name=__name__)
    def startRenderThread(self, origin, quit=False, restart=False):
        if quit and hasattr(self, "brThread") and self.brThread.isRunning():
            self.brObject.active = False
            self.brThread.quit()
            return

        if restart:
            self.brObject.run()
        else:
            self.brThread = QThread()
            self.brObject = bldRenderTimer(self.brThread)
            self.brObject.moveToThread(self.brThread)
            self.brThread.started.connect(self.brObject.run)
            self.brObject.finished.connect(lambda: self.CheckRenderFinished(origin))

            self.brThread.start()

    @err_catcher(name=__name__)
    def sm_render_undoRenderSettings(self, origin, rSettings):
        if "width" in rSettings:
            bpy.context.scene.render.resolution_x = rSettings["width"]
        if "height" in rSettings:
            bpy.context.scene.render.resolution_y = rSettings["height"]
        if "prev_start" in rSettings:
            bpy.context.scene.frame_start = rSettings["prev_start"]
        if "prev_end" in rSettings:
            bpy.context.scene.frame_end = rSettings["prev_end"]
        if "fileformat" in rSettings:
            bpy.context.scene.render.image_settings.file_format = rSettings[
                "fileformat"
            ]
        if "overwrite" in rSettings:
            bpy.context.scene.render.use_overwrite = rSettings["overwrite"]
        if "fileextension" in rSettings:
            bpy.context.scene.render.use_file_extension = rSettings["fileextension"]
        if "resolutionpercent" in rSettings:
            bpy.context.scene.render.resolution_percentage = rSettings[
                "resolutionpercent"
            ]

        if platform.system() == "Windows":
            tmpOutput = os.path.join(os.environ["temp"], "PrismRender")
            if os.path.exists(tmpOutput):
                try:
                    shutil.rmtree(tmpOutput)
                except:
                    pass

        bDir = os.path.dirname(rSettings["origOutputName"])
        if os.path.exists(bDir) and len(os.listdir(bDir)) == 0:
            try:
                shutil.rmtree(bDir)
            except:
                pass

            origin.l_pathLast.setText(rSettings["outputName"])
            origin.l_pathLast.setToolTip(rSettings["outputName"])
            origin.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def sm_render_getDeadlineParams(self, origin, dlParams, homeDir):
        dlParams["jobInfoFile"] = os.path.join(
            homeDir, "temp", "blender_submit_info.job"
        )
        dlParams["pluginInfoFile"] = os.path.join(
            homeDir, "temp", "blender_plugin_info.job"
        )

        dlParams["jobInfos"]["Plugin"] = "Blender"
        dlParams["jobInfos"]["Comment"] = "Prism-Submission-Blender_ImageRender"
        dlParams["pluginInfos"]["OutputFile"] = dlParams["jobInfos"]["OutputFilename0"]

    @err_catcher(name=__name__)
    def getCurrentRenderer(self, origin):
        return bpy.context.window_manager.windows[0].scene.render.engine

    @err_catcher(name=__name__)
    def getCurrentSceneFiles(self, origin):
        return [self.core.getCurrentFileName()]

    @err_catcher(name=__name__)
    def sm_render_getRenderPasses(self, origin):
        aovNames = [x["name"] for x in self.getAvailableAOVs() if x["name"] not in self.getViewLayerAOVs()]
        return aovNames

    @err_catcher(name=__name__)
    def sm_render_addRenderPass(self, origin, passName, steps):
        self.enableViewLayerAOV(passName)

    @err_catcher(name=__name__)
    def sm_render_managerChanged(self, origin, isPandora):
        origin.f_osPAssets.setVisible(isPandora)

    @err_catcher(name=__name__)
    def sm_render_preExecute(self, origin):
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def sm_render_fixOutputPath(self, origin, outputName, singleFrame=False):
        if not singleFrame:
            outputName = (
                os.path.splitext(outputName)[0] + "####" + os.path.splitext(outputName)[1]
            )
        return outputName

    @err_catcher(name=__name__)
    def sm_render_submitScene(self, origin, jobPath):
        jobFilePath = os.path.join(jobPath, self.core.getCurrentFileName(path=False))
        bpy.ops.wm.save_as_mainfile(filepath=jobFilePath, copy=True)
        bpy.ops.wm.revert_mainfile()
        self.core.stateManager()

    @err_catcher(name=__name__)
    def deleteNodes(self, origin, handles):
        for i in handles:
            bpy.data.objects.remove(self.getObject(i))

    #   bpy.ops.object.select_all(self.getOverrideContext(origin), action='DESELECT')
    #   for i in handles:
    #       self.selectObject(bpy.data.objects[i])
    #   bpy.ops.object.make_local(self.getOverrideContext(origin), type='SELECT_OBDATA_MATERIAL')
    #   bpy.ops.object.delete(self.getOverrideContext(origin))

    @err_catcher(name=__name__)
    def sm_import_startup(self, origin):
        origin.b_browse.setMinimumWidth(50 * self.core.uiScaleFactor)
        origin.b_browse.setMaximumWidth(50 * self.core.uiScaleFactor)
        origin.f_abcPath.setVisible(True)
        origin.f_unitConversion.setVisible(False)
        origin.l_preferUnit.setText("Prefer versions in cm:")

    @err_catcher(name=__name__)
    def sm_import_importToApp(self, origin, doImport, update, impFileName):
        fileName = os.path.splitext(os.path.basename(impFileName))
        origin.setName = ""
        result = False

        ext = fileName[1].lower()
        if ext in [".blend"]:
            dlg_sceneData = widget_import_scenedata.Import_SceneData(self.core, self.plugin)
            dlgResult = dlg_sceneData.importScene(impFileName, update, origin)
            if not dlgResult:
                return

            if dlg_sceneData.updated:
                result = True
            existingNodes = dlg_sceneData.existingNodes
        else:
            if ext not in [".fbx", ".obj", ".abc"]:
                self.core.popup("Format is not supported.")
                return {"result": False, "doImport": doImport}

            if not (ext == ".abc" and origin.chb_abcPath.isChecked()):
                origin.preDelete(
                    baseText="Do you want to delete the currently connected objects?\n\n"
                )
            existingNodes = list(bpy.data.objects)
            if ext == ".fbx":
                bpy.ops.import_scene.fbx(filepath=impFileName, global_scale=100)
            elif ext == ".obj":
                bpy.ops.import_scene.obj(filepath=impFileName)
            elif ext == ".abc":
                if origin.chb_abcPath.isChecked() and len(origin.nodes) > 0:
                    cache = None
                    for i in origin.nodes:
                        constraints = [
                            x
                            for x in self.getObject(i).constraints
                            if x.type == "TRANSFORM_CACHE"
                        ]
                        modifiers = [
                            x
                            for x in self.getObject(i).modifiers
                            if x.type == "MESH_SEQUENCE_CACHE"
                        ]
                        if len(constraints) > 0:
                            cache = constraints[0].cache_file
                        elif len(modifiers) > 0:
                            cache = modifiers[0].cache_file

                    if cache is not None:
                        cache.filepath = impFileName
                        cache.name = os.path.basename(impFileName)
                    #       bpy.context.scene.frame_current += 1        #updates the cache, but leads to crashes
                    #       bpy.context.scene.frame_current -= 1
                    else:
                        self.core.popup("No caches updated.")
                    result = True
                else:
                    bpy.ops.wm.alembic_import(
                        self.getOverrideContext(origin),
                        filepath=impFileName,
                        set_frame_range=False,
                        as_background_job=False,
                    )

        if not result:
            importedNodes = []
            for i in bpy.data.objects:
                if i not in existingNodes:
                    importedNodes.append(self.getNode(i))

            origin.setName = "Import_" + fileName[0]
            extension = 1
            while origin.setName in self.getGroups() and extension < 999:
                if "%s_%s" % (origin.setName, extension) not in self.getGroups():
                    origin.setName += "_%s" % extension
                extension += 1

            if origin.chb_trackObjects.isChecked():
                origin.nodes = importedNodes
            if len(origin.nodes) > 0:
                self.createGroups(name=origin.setName)

                for i in origin.nodes:
                    obj = self.getObject(i)
                    if obj and obj.name not in self.getGroups()[origin.setName].objects:
                        self.getGroups()[origin.setName].objects.link(obj)

            bpy.ops.object.select_all(
                self.getOverrideContext(origin), action="DESELECT"
            )

            objs = [self.getObject(x) for x in importedNodes]
            self.selectObjects(objs, quiet=True)

            result = len(importedNodes) > 0

        return {"result": result, "doImport": doImport}

    @err_catcher(name=__name__)
    def getNode(self, obj):
        if type(obj) == str:
            node = {"name": obj, "library": ""}
        else:
            node = {"name": obj.name, "library": getattr(obj.library, "filepath", "")}
        return node

    @err_catcher(name=__name__)
    def getObject(self, node):
        if type(node) == str:
            node = self.getNode(node)

        for obj in bpy.data.objects:
            if obj.name == node["name"] and getattr(obj.library, "filepath", "") == node["library"]:
                return obj

    @err_catcher(name=__name__)
    def sm_import_disableObjectTracking(self, origin):
        stateGroup = [x for x in self.getGroups() if x.name == origin.setName]
        if len(stateGroup) > 0:
            self.getGroups().remove(stateGroup[0])

    @err_catcher(name=__name__)
    def sm_import_updateObjects(self, origin):
        if origin.setName == "":
            return

        origin.nodes = []
        if origin.setName in self.getGroups() and origin.chb_trackObjects.isChecked():
            group = self.getGroups()[origin.setName]
            nodes = []
            for obj in group.objects:
                if not obj.users_scene:
                    group.objects.unlink(obj)
                    continue

                nodes.append(self.getNode(obj))

            origin.nodes = nodes

    @err_catcher(name=__name__)
    def sm_import_removeNameSpaces(self, origin):
        for i in origin.nodes:
            if not self.getObject(i):
                continue

            nodeName = self.getNodeName(origin, i)
            newName = nodeName.rsplit(":", 1)[-1]
            if newName != nodeName and not i["library"]:
                self.getObject(i).name = newName

        origin.updateUi()

    @err_catcher(name=__name__)
    def sm_import_unitConvert(self, origin):
        if origin.taskName == "ShotCam" and len(origin.nodes) == 1:
            prevObjs = list(bpy.context.scene.objects)
            bpy.ops.object.empty_add(type="PLAIN_AXES")
            empObj = [x for x in bpy.context.scene.objects if x not in prevObjs][0]
            empObj.name = "UnitConversion"
            empObj.location = [0, 0, 0]

            self.getObject(origin.nodes[0]).parent = empObj
            sVal = 0.01
            empObj.scale = [sVal, sVal, sVal]

            bpy.ops.object.select_all(
                self.getOverrideContext(origin), action="DESELECT"
            )
            self.selectObject(self.getObject(origin.nodes[0]))
            bpy.ops.object.parent_clear(
                self.getOverrideContext(origin), type="CLEAR_KEEP_TRANSFORM"
            )

            bpy.ops.object.select_all(
                self.getOverrideContext(origin), action="DESELECT"
            )
            self.selectObject(empObj)
            bpy.ops.object.delete(self.getOverrideContext(origin))

    @err_catcher(name=__name__)
    def sm_import_fixImportPath(self, filepath):
        return filepath.replace("\\\\", "\\")

    @err_catcher(name=__name__)
    def sm_import_updateUi(self, origin):
        origin.f_unitConversion.setVisible(origin.taskName == "ShotCam")

    @err_catcher(name=__name__)
    def sm_playblast_startup(self, origin):
        frange = self.getFrameRange(origin)
        origin.sp_rangeStart.setValue(frange[0])
        origin.sp_rangeEnd.setValue(frange[1])
        origin.b_resPresets.setMinimumWidth(30 * self.core.uiScaleFactor)
        origin.b_resPresets.setMinimumHeight(0)
        origin.b_resPresets.setMaximumHeight(500 * self.core.uiScaleFactor)

    @err_catcher(name=__name__)
    def sm_playblast_createPlayblast(self, origin, jobFrames, outputName):
        singleFrame = origin.cb_rangeType.currentText() == "Single Frame"
        if not singleFrame:
            outputName = (
                os.path.splitext(outputName)[0] + "####" + os.path.splitext(outputName)[1]
            )

        if origin.curCam is not None:
            bpy.context.scene.camera = bpy.context.scene.objects[origin.curCam]
            for window in bpy.context.window_manager.windows:
                screen = window.screen
                for area in screen.areas:
                    if area.type == "VIEW_3D":
                        area.spaces[0].region_3d.view_perspective = "CAMERA"
                        break

        renderAnim = jobFrames[0] != jobFrames[1]

        prevRange = [bpy.context.scene.frame_start, bpy.context.scene.frame_end]
        prevRes = [
            bpy.context.scene.render.resolution_x,
            bpy.context.scene.render.resolution_y,
            bpy.context.scene.render.resolution_percentage,
        ]
        prevOutput = [
            bpy.context.scene.render.filepath,
            bpy.context.scene.render.image_settings.file_format,
        ]

        bpy.context.scene.frame_start = jobFrames[0]
        bpy.context.scene.frame_end = jobFrames[1]

        if origin.chb_resOverride.isChecked():
            bpy.context.scene.render.resolution_x = origin.sp_resWidth.value()
            bpy.context.scene.render.resolution_y = origin.sp_resHeight.value()
            bpy.context.scene.render.resolution_percentage = 100

        bpy.context.scene.render.filepath = outputName
        bpy.context.scene.render.image_settings.file_format = "JPEG"

        bpy.ops.render.opengl(
            self.getOverrideContext(origin), animation=renderAnim, write_still=True
        )

        bpy.context.scene.frame_start = prevRange[0]
        bpy.context.scene.frame_end = prevRange[1]
        bpy.context.scene.render.resolution_x = prevRes[0]
        bpy.context.scene.render.resolution_y = prevRes[1]
        bpy.context.scene.render.resolution_percentage = prevRes[2]
        bpy.context.scene.render.filepath = prevOutput[0]
        bpy.context.scene.render.image_settings.file_format = prevOutput[1]

    @err_catcher(name=__name__)
    def sm_playblast_preExecute(self, origin):
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def sm_playblast_execute(self, origin):
        pass

    @err_catcher(name=__name__)
    def sm_setActivePalette(self, origin, listWidget, inactive, inactivef, activef):
        listWidget.setStyleSheet("QTreeWidget { border: 1px solid rgb(30,130,230); }")
        inactive.setStyleSheet("QTreeWidget { border: 1px solid rgb(30,30,30); }")

    @err_catcher(name=__name__)
    def onStateManagerOpen(self, origin):
        startframe, endframe = self.getFrameRange(origin)
        origin.sp_rangeStart.setValue(startframe)
        origin.sp_rangeEnd.setValue(endframe)

        origin.b_showImportStates.setStyleSheet("padding-left: 1px;padding-right: 1px;")
        origin.b_showExportStates.setStyleSheet("padding-left: 1px;padding-right: 1px;")

        origin.b_createImport.setMinimumWidth(70 * self.core.uiScaleFactor)
        origin.b_createImport.setMaximumWidth(70 * self.core.uiScaleFactor)
        origin.b_createImport.setMinimumHeight(0)
        origin.b_createImport.setMaximumHeight(500 * self.core.uiScaleFactor)
        origin.b_shotCam.setMinimumHeight(0)
        origin.b_shotCam.setMaximumHeight(50 * self.core.uiScaleFactor)
        origin.b_showImportStates.setMinimumWidth(30 * self.core.uiScaleFactor)
        origin.b_showImportStates.setMaximumWidth(30 * self.core.uiScaleFactor)
        origin.b_showExportStates.setMinimumWidth(30 * self.core.uiScaleFactor)
        origin.b_showExportStates.setMaximumWidth(30 * self.core.uiScaleFactor)
        origin.b_createExport.setMinimumWidth(70 * self.core.uiScaleFactor)
        origin.b_createExport.setMaximumWidth(70 * self.core.uiScaleFactor)
        origin.b_createRender.setMinimumWidth(70 * self.core.uiScaleFactor)
        origin.b_createRender.setMaximumWidth(70 * self.core.uiScaleFactor)
        origin.b_createPlayblast.setMinimumWidth(80 * self.core.uiScaleFactor)
        origin.b_createPlayblast.setMaximumWidth(80 * self.core.uiScaleFactor)
        origin.b_getRange.setMaximumWidth(200 * self.core.uiScaleFactor)
        origin.b_setRange.setMaximumWidth(200 * self.core.uiScaleFactor)
        origin.b_description.setMinimumWidth(35 * self.core.uiScaleFactor)
        origin.b_description.setMaximumWidth(35 * self.core.uiScaleFactor)
        origin.b_preview.setMinimumWidth(35 * self.core.uiScaleFactor)
        origin.b_preview.setMaximumWidth(35 * self.core.uiScaleFactor)

    @err_catcher(name=__name__)
    def sm_saveStates(self, origin, buf):
        bpy.context.scene["PrismStates"] = buf

    @err_catcher(name=__name__)
    def sm_saveImports(self, origin, importPaths):
        bpy.context.scene["PrismImports"] = importPaths.replace("\\\\", "\\")

    @err_catcher(name=__name__)
    def sm_readStates(self, origin):
        if "PrismStates" in bpy.context.scene:
            return bpy.context.scene["PrismStates"]

    @err_catcher(name=__name__)
    def sm_deleteStates(self, origin):
        if "PrismStates" in bpy.context.scene:
            del bpy.context.scene["PrismStates"]

    @err_catcher(name=__name__)
    def sm_getExternalFiles(self, origin):
        return [[], []]

    @err_catcher(name=__name__)
    def sm_createRenderPressed(self, origin):
        origin.createPressed("Render")
