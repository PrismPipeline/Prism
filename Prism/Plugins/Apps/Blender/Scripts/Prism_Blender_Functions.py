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
import threading
import platform
import traceback
import time
import shutil
import logging
import operator
import tempfile

import bpy

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

if eval(os.getenv("PRISM_DEBUG", "False")):
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
        self.core.registerCallback(
            "onUserSettingsOpen", self.onUserSettingsOpen, plugin=self.plugin
        )
        self.core.registerCallback(
            "onProjectBrowserStartup", self.onProjectBrowserStartup, plugin=self.plugin
        )
        self.core.registerCallback(
            "onStateManagerOpen", self.onStateManagerOpen, plugin=self.plugin
        )
        self.core.registerCallback(
            "onStateCreated", self.onStateCreated, plugin=self.plugin
        )
        self.core.registerCallback(
            "prePlayblast", self.prePlayblast, plugin=self.plugin
        )

        self.importHandlers = {
            ".abc": {"importFunction": self.importAlembic},
            ".fbx": {"importFunction": self.importFBX},
            ".obj": {"importFunction": self.importObj},
        }

        self.exportHandlers = {
            ".abc": {"exportFunction": self.exportAlembic},
            ".fbx": {"exportFunction": self.exportFBX},
            ".obj": {"exportFunction": self.exportObj},
            ".blend": {"exportFunction": self.exportBlend},
        }

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

        self.core.setActiveStyleSheet("Blender")
        appIcon = QIcon(
            os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "p_tray.png")
        )
        qapp = QApplication.instance()
        qapp.setWindowIcon(appIcon)

        origin.timer.stop()
        origin.startAutosaveTimer()

    @err_catcher(name=__name__)
    def autosaveEnabled(self, origin):
        if bpy.app.version < (2, 80, 0):
            return bpy.context.user_preferences.filepaths.use_auto_save_temporary_files
        else:
            return bpy.context.preferences.filepaths.use_auto_save_temporary_files

    @err_catcher(name=__name__)
    def sceneOpen(self, origin):
        if self.core.shouldAutosaveTimerRun():
            origin.startAutosaveTimer()

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
        filepath = os.path.normpath(filepath)
        if bpy.app.version < (4, 0, 0):
            return bpy.ops.wm.save_as_mainfile(self.getOverrideContext(origin), filepath=filepath)
        else:
            with bpy.context.temp_override(**self.getOverrideContext(origin)):
                return bpy.ops.wm.save_as_mainfile(filepath=filepath)

    @err_catcher(name=__name__)
    def getImportPaths(self, origin):
        if "PrismImports" not in bpy.context.scene:
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
        bpy.context.scene.frame_start = int(startFrame)
        bpy.context.scene.frame_end = int(endFrame)
        bpy.context.scene.frame_current = int(startFrame)
        if bpy.app.version < (4, 0, 0):
            try:
                bpy.ops.action.view_all(
                    self.getOverrideContext(origin, context="DOPESHEET_EDITOR")
                )
            except:
                pass
        else:
            with bpy.context.temp_override(**self.getOverrideContext(context="DOPESHEET_EDITOR")):
                bpy.ops.action.view_all()

    @err_catcher(name=__name__)
    def getFPS(self, origin):
        return bpy.context.scene.render.fps

    @err_catcher(name=__name__)
    def setFPS(self, origin, fps):
        bpy.context.scene.render.fps = int(fps)

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

        ctx = self.getOverrideContext(dftContext=False)
        try:
            if bpy.app.version < (4, 0, 0):
                bpy.ops.wm.open_mainfile(ctx, "INVOKE_DEFAULT", filepath=filepath, display_file_selector=False)
            else:
                bpy.ops.wm.open_mainfile(filepath=filepath, display_file_selector=False)
        except Exception as e:
            if "File written by newer Blender binary" in str(e):
                msg = "Warning occurred while opening file:\n\n%s" % str(e)
                self.core.popup(msg)
            else:
                raise

        return True

    @err_catcher(name=__name__)
    def onUserSettingsOpen(self, origin):
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
            return bpy.ops.group.create(self.getOverrideContext(), name=name)
        else:
            if bpy.app.version < (4, 0, 0):
                if bpy.ops.collection.create.poll(self.getOverrideContext()):
                    return bpy.ops.collection.create(self.getOverrideContext(), name=name)
            else:
                ctx = self.getOverrideContext()
                ctx.pop("region")
                with bpy.context.temp_override(**ctx):
                    if bpy.ops.collection.create.poll():
                        return bpy.ops.collection.create(name=name)

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
                        msg.addButton(
                            "Skip object '%s'" % obj.name, QMessageBox.YesRole
                        )

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
            origin.setTaskname("Export")
            taskName = origin.getTaskname()

        if taskName not in self.getGroups():
            result = self.createGroups(name=taskName)
            if not result:
                self.core.popup("Couldn't add objects. Make sure you are in a context where collections can be created.")
                return

        if not objects:
            objects = [
                o
                for o in bpy.context.scene.objects
                if self.getSelectObject(o)
                and o not in list(self.getGroups()[taskName].objects)
            ]

        for i in objects:
            self.getGroups()[taskName].objects.link(i)

    @err_catcher(name=__name__)
    def getNodeName(self, origin, node):
        return node["name"]

    @err_catcher(name=__name__)
    def selectNodes(self, origin):
        if origin.lw_objects.selectedItems() != []:
            if bpy.app.version < (4, 0, 0):
                bpy.ops.object.select_all(
                    self.getOverrideContext(origin), action="DESELECT"
                )
            else:
                with bpy.context.temp_override(**self.getOverrideContext()):
                    bpy.ops.object.select_all(action="DESELECT")

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
            if bpy.app.version < (4, 0, 0):
                bpy.ops.object.select_all(
                    self.getOverrideContext(origin), action="DESELECT"
                )
            else:
                with bpy.context.temp_override(**self.getOverrideContext()):
                    bpy.ops.object.select_all(action="DESELECT")

            self.selectObject(self.getObject(origin.curCam))

    @err_catcher(name=__name__)
    def sm_export_startup(self, origin):
        if origin.className == "Export":
            origin.w_additionalOptions.setVisible(False)

    @err_catcher(name=__name__)
    def getValidGroupName(self, groupName):
        extension = 1
        while groupName in self.getGroups() and extension < 999:
            if "%s_%s" % (groupName, extension) not in self.getGroups():
                groupName += "_%s" % extension
            extension += 1

        return groupName

    @err_catcher(name=__name__)
    def sm_export_setTaskText(self, origin, prevTaskName, newTaskName):
        setName = newTaskName
        if prevTaskName and prevTaskName in self.getGroups():
            self.getGroups()[prevTaskName].name = setName
        else:
            self.createGroups(name=setName)

        return setName

    @err_catcher(name=__name__)
    def sm_export_removeSetItem(self, origin, node):
        if origin.getTaskname() not in self.getGroups():
            return

        self.getGroups()[origin.getTaskname()].objects.unlink(self.getObject(node))

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
        if bpy.app.version < (4, 0, 0):
            bpy.ops.wm.alembic_export(
                self.getOverrideContext(origin),
                filepath=(outputName + ".abc"),
                start=startFrame,
                end=endFrame,
                selected=True,
                as_background_job=False,
            )
        else:
            with bpy.context.temp_override(**self.getOverrideContext()):
                bpy.ops.wm.alembic_export(
                    filepath=(outputName + ".abc"),
                    start=startFrame,
                    end=endFrame,
                    selected=True,
                    as_background_job=False,
                )

        self.selectCam(origin)
        if bpy.app.version < (4, 0, 0):
            bpy.ops.export_scene.fbx(
                self.getOverrideContext(origin),
                filepath=(outputName + ".fbx"),
                use_selection=True,
            )
        else:
            with bpy.context.temp_override(**self.getOverrideContext()):
                bpy.ops.export_scene.fbx(
                    filepath=(outputName + ".fbx"),
                    use_selection=True,
                )

        if bpy.app.version < (4, 0, 0):
            bpy.ops.object.select_all(
                self.getOverrideContext(origin), action="DESELECT"
            )
        else:
            with bpy.context.temp_override(**self.getOverrideContext()):
                bpy.ops.object.select_all(action="DESELECT")

    @err_catcher(name=__name__)
    def exportObj(self, outputName, origin, startFrame, endFrame, expNodes):
        for i in range(startFrame, endFrame + 1):
            bpy.context.scene.frame_current = i
            foutputName = outputName.replace("####", format(i, "04"))
            if bpy.app.version < (4, 0, 0):
                bpy.ops.export_scene.obj(
                    self.getOverrideContext(origin),
                    filepath=foutputName,
                    use_selection=(not origin.chb_wholeScene.isChecked()),
                )
            else:
                with bpy.context.temp_override(**self.getOverrideContext()):
                    bpy.ops.wm.obj_export(
                        filepath=foutputName,
                        export_selected_objects=(not origin.chb_wholeScene.isChecked()),
                    )

        outputName = foutputName
        return outputName

    @err_catcher(name=__name__)
    def exportFBX(self, outputName, origin, startFrame, endFrame, expNodes):
        useAnim = startFrame != endFrame
        if bpy.app.version >= (2, 79, 7):
            if bpy.app.version < (4, 0, 0):
                bpy.ops.export_scene.fbx(
                    self.getOverrideContext(origin),
                    filepath=outputName,
                    use_selection=(not origin.chb_wholeScene.isChecked()),
                    bake_anim=useAnim
                )
            else:
                with bpy.context.temp_override(**self.getOverrideContext(origin)):
                    bpy.ops.export_scene.fbx(
                        filepath=outputName,
                        use_selection=(not origin.chb_wholeScene.isChecked()),
                        bake_anim=useAnim
                    )
        else:
            bpy.ops.export_scene.fbx(
                self.getOverrideContext(origin),
                filepath=outputName,
                use_selection=(not origin.chb_wholeScene.isChecked()),
                use_anim=useAnim
            )
        return outputName

    @err_catcher(name=__name__)
    def exportAlembic(self, outputName, origin, startFrame, endFrame, expNodes):
        if bpy.app.version < (4, 0, 0):
            bpy.ops.wm.alembic_export(
                self.getOverrideContext(origin),
                filepath=outputName,
                start=startFrame,
                end=endFrame,
                selected=(not origin.chb_wholeScene.isChecked()),
                as_background_job=False,
            )
        else:
            with bpy.context.temp_override(**self.getOverrideContext(origin)):
                bpy.ops.wm.alembic_export(
                    filepath=outputName,
                    start=startFrame,
                    end=endFrame,
                    selected=(not origin.chb_wholeScene.isChecked()),
                    as_background_job=False,
                )

        return outputName

    @err_catcher(name=__name__)
    def exportBlend(self, outputName, origin, startFrame, endFrame, expNodes):
        if origin.chb_wholeScene.isChecked():
            shutil.copyfile(self.core.getCurrentFileName(), outputName)
        else:
            origin.setLastPath(outputName)
            self.core.saveScene(prismReq=False)
            for object_ in bpy.data.objects:
                if object_ not in [self.getObject(x) for x in expNodes]:
                    bpy.data.objects.remove(object_, do_unlink=True)
            bpy.ops.wm.save_as_mainfile(filepath=outputName, copy=True)
            bpy.ops.wm.revert_mainfile()
            self.core.stateManager()

        return outputName

    @err_catcher(name=__name__)
    def exportUsd(self, outputName, origin, startFrame, endFrame, expNodes):
        from _bpy import ops as _ops_module
        try:
            _ops_module.as_string("WM_OT_usd_export")
        except:
            ext = os.path.splitext(outputName)[1]
            msg = "Format \"%s\" is not supported in this Blender version. Exporting USD requires at least Blender 2.82" % ext
            self.core.popup(msg)
            return False

        self.setFrameRange(origin, startFrame, endFrame)
        if bpy.app.version < (4, 0, 0):
            bpy.ops.wm.usd_export(
                self.getOverrideContext(origin),
                filepath=outputName,
                export_animation=startFrame != endFrame,
                selected_objects_only=(not origin.chb_wholeScene.isChecked()),
            )
        else:
            with bpy.context.temp_override(**self.getOverrideContext(origin)):
                bpy.ops.wm.usd_export(
                    filepath=outputName,
                    export_animation=startFrame != endFrame,
                    selected_objects_only=(not origin.chb_wholeScene.isChecked()),
                )
        return outputName

    @err_catcher(name=__name__)
    def sm_export_exportAppObjects(
        self,
        origin,
        startFrame,
        endFrame,
        outputName,
    ):
        expNodes = origin.nodes
        ctx = self.getOverrideContext(origin)
        if bpy.app.version >= (2, 80, 0):
            ctx.pop("screen")
            ctx.pop("area")
        if bpy.app.version < (4, 0, 0):
            bpy.ops.object.select_all(ctx, action="DESELECT")
        else:
            with bpy.context.temp_override(**ctx):
                bpy.ops.object.select_all(action="DESELECT")

        for i in expNodes:
            if self.getObject(i):
                self.selectObject(self.getObject(i))

        ext = origin.getOutputType()
        if ext in self.exportHandlers:
            outputName = self.exportHandlers[ext]["exportFunction"](
                outputName, origin, startFrame, endFrame, expNodes
            )
        else:
            msg = "Canceled: Format \"%s\" is not supported." % ext
            return msg

        if bpy.app.version < (4, 0, 0):
            bpy.ops.object.select_all(ctx, action="DESELECT")
        else:
            with bpy.context.temp_override(**ctx):
                bpy.ops.object.select_all(action="DESELECT")

        return outputName

    @err_catcher(name=__name__)
    def sm_export_preDelete(self, origin):
        try:
            self.getGroups().remove(self.getGroups()[origin.getTaskname()], do_unlink=True)
        except Exception as e:
            logger.debug(e)

    @err_catcher(name=__name__)
    def getOverrideContext(self, origin=None, context=None, dftContext=True):
        if dftContext:
            ctx = bpy.context.copy()
        else:
            ctx = {}

        for window in bpy.context.window_manager.windows:
            ctx["window"] = window
            screen = window.screen
            ctx["screen"] = screen

            if context:
                for area in screen.areas:
                    if area.type == context:
                        ctx["area"] = area
                        for region in area.regions:
                            if region.type == "WINDOW":
                                ctx["region"] = region
                                return ctx

            for area in screen.areas:
                if area.type == "VIEW_3D":
                    ctx["area"] = area
                    return ctx

            for area in screen.areas:
                if area.type == "IMAGE_EDITOR":
                    ctx["area"] = area
                    return ctx

        return ctx

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
        if bpy.context.scene.node_tree is None or not bpy.context.scene.use_nodes:
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
        aovParms += [
            "cycles." + x for x in dir(curlayer.cycles) if x.startswith("use_pass_")
        ]
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

        aovs = sorted(aovs, key=lambda x: x["name"])

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
                if "screen" in ctx:
                    ctx.pop("screen")

                if "area" in ctx:
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
                if bpy.app.version < (4, 0, 0):
                    bpy.ops.render.render(
                        ctx,
                        "INVOKE_DEFAULT",
                        animation=not singleFrame,
                        write_still=singleFrame,
                    )
                else:
                    with bpy.context.temp_override(**ctx):
                        bpy.ops.render.render(
                            "INVOKE_DEFAULT",
                            animation=not singleFrame,
                            write_still=singleFrame,
                        )
                
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
        aovNames = [
            x["name"]
            for x in self.getAvailableAOVs()
            if x["name"] not in self.getViewLayerAOVs()
        ]
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
                os.path.splitext(outputName)[0]
                + "." + "#"*self.core.framePadding
                + os.path.splitext(outputName)[1]
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
        origin.f_abcPath.setVisible(True)

    @err_catcher(name=__name__)
    def importAlembic(self, importPath, origin):
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
                cache.filepath = importPath
                cache.name = os.path.basename(importPath)
            #       bpy.context.scene.frame_current += 1        #updates the cache, but leads to crashes
            #       bpy.context.scene.frame_current -= 1
            else:
                self.core.popup("No caches updated.")
            return True
        else:
            if bpy.app.version < (4, 0, 0):
                bpy.ops.wm.alembic_import(
                    self.getOverrideContext(origin),
                    filepath=importPath,
                    set_frame_range=False,
                    as_background_job=False,
                )
            else:
                with bpy.context.temp_override(**self.getOverrideContext(origin)):
                    bpy.ops.wm.alembic_import(
                        filepath=importPath,
                        set_frame_range=False,
                        as_background_job=False,
                    )

    @err_catcher(name=__name__)
    def importFBX(self, importPath, origin):
        if bpy.app.version < (4, 0, 0):
            bpy.ops.import_scene.fbx(self.getOverrideContext(origin), filepath=importPath)
        else:
            with bpy.context.temp_override(**self.getOverrideContext(origin)):
                bpy.ops.import_scene.fbx(filepath=importPath)

    @err_catcher(name=__name__)
    def importObj(self, importPath, origin):
        if bpy.app.version < (4, 0, 0):
            bpy.ops.import_scene.obj(self.getOverrideContext(origin), filepath=importPath)
        else:
            with bpy.context.temp_override(**self.getOverrideContext(origin)):
                bpy.ops.wm.obj_import(filepath=importPath)

    @err_catcher(name=__name__)
    def importUsd(self, filepath, origin):
        from _bpy import ops as _ops_module
        try:
            _ops_module.as_string("WM_OT_usd_import")
        except:
            ext = os.path.splitext(filepath)[1]
            msg = "Format \"%s\" is not supported in this Blender version. Importing USD requires at least Blender 3.0." % ext
            self.core.popup(msg)
            return False

        if bpy.app.version < (4, 0, 0):
            bpy.ops.wm.usd_import(
                self.getOverrideContext(origin),
                filepath=filepath,
                set_frame_range=False,
                import_usd_preview=True,
            )
        else:
            with bpy.context.temp_override(**self.getOverrideContext(origin)):
                bpy.ops.wm.usd_import(
                    filepath=filepath,
                    set_frame_range=False,
                    import_usd_preview=True,
                )

    @err_catcher(name=__name__)
    def sm_import_importToApp(self, origin, doImport, update, impFileName):
        fileName = os.path.splitext(os.path.basename(impFileName))
        origin.setName = ""
        result = False

        ext = fileName[1].lower()
        if ext in [".blend"]:
            dlg_sceneData = widget_import_scenedata.Import_SceneData(
                self.core, self.plugin
            )
            dlgResult = dlg_sceneData.importScene(impFileName, update, origin)
            if not dlgResult:
                return

            if dlg_sceneData.updated:
                result = True
            existingNodes = dlg_sceneData.existingNodes
        else:
            if not (ext == ".abc" and origin.chb_abcPath.isChecked()):
                origin.preDelete(
                    baseText="Do you want to delete the currently connected objects?\n\n"
                )
            existingNodes = list(bpy.data.objects)

            if ext in self.importHandlers:
                result = self.importHandlers[ext]["importFunction"](impFileName, origin)
            else:
                self.core.popup("Format is not supported.")
                return {"result": False, "doImport": doImport}

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

            if bpy.app.version < (4, 0, 0):
                bpy.ops.object.select_all(
                    self.getOverrideContext(origin), action="DESELECT"
                )
            else:
                with bpy.context.temp_override(**self.getOverrideContext(origin)):
                    bpy.ops.object.select_all(action="DESELECT")

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
            if (
                obj.name == node["name"]
                and getattr(obj.library, "filepath", "") == node["library"]
            ):
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
    def sm_import_fixImportPath(self, filepath):
        return filepath.replace("\\\\", "\\")

    @err_catcher(name=__name__)
    def sm_playblast_startup(self, origin):
        frange = self.getFrameRange(origin)
        origin.sp_rangeStart.setValue(frange[0])
        origin.sp_rangeEnd.setValue(frange[1])
        origin.b_resPresets.setMinimumWidth(30 * self.core.uiScaleFactor)
        origin.b_resPresets.setMinimumHeight(0)
        origin.b_resPresets.setMaximumHeight(500 * self.core.uiScaleFactor)

    @err_catcher(name=__name__)
    def prePlayblast(self, **kwargs):
        renderAnim = kwargs["startframe"] != kwargs["endframe"]
        if not renderAnim:
            outputName = (
                os.path.splitext(kwargs["outputpath"])[0]
                + "."
                + ("%0" + str(self.core.framePadding) + "d") % kwargs["startframe"]
                + os.path.splitext(kwargs["outputpath"])[1]
            )

            return {"outputName": outputName}

    @err_catcher(name=__name__)
    def sm_playblast_createPlayblast(self, origin, jobFrames, outputName):
        renderAnim = jobFrames[0] != jobFrames[1]
        if origin.curCam is not None:
            bpy.context.scene.camera = bpy.context.scene.objects[origin.curCam]
            for window in bpy.context.window_manager.windows:
                screen = window.screen
                for area in screen.areas:
                    if area.type == "VIEW_3D":
                        area.spaces[0].region_3d.view_perspective = "CAMERA"
                        break

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

        bpy.context.scene.render.filepath = os.path.normpath(outputName)
        bpy.context.scene.render.image_settings.file_format = "JPEG"

        if bpy.app.version < (4, 0, 0):
            bpy.ops.render.opengl(
                self.getOverrideContext(origin), animation=renderAnim, write_still=True
            )
        else:
            with bpy.context.temp_override(**self.getOverrideContext(origin)):
                bpy.ops.render.opengl(animation=renderAnim, write_still=True)

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
    def captureViewportThumbnail(self):
        path = tempfile.NamedTemporaryFile(suffix=".jpg").name
        if bpy.app.version < (4, 0, 0):
            bpy.ops.screen.screenshot(self.getOverrideContext(), filepath=path)
        else:
            with bpy.context.temp_override(**self.getOverrideContext()):
                bpy.ops.screen.screenshot(filepath=path)

        pm = self.core.media.getPixmapFromPath(path)
        try:
            os.remove(path)
        except:
            pass

        return pm

    @err_catcher(name=__name__)
    def sm_setActivePalette(self, origin, listWidget, inactive, inactivef, activef):
        listWidget.setStyleSheet("QTreeWidget { border: 1px solid rgb(30,130,230); }")
        inactive.setStyleSheet("QTreeWidget { border: 1px solid rgb(30,30,30); }")

    @err_catcher(name=__name__)
    def onStateManagerOpen(self, origin):
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

    @err_catcher(name=__name__)
    def onStateCreated(self, origin, state, stateData):
        if state.className == "ImageRender":
            state.b_resPresets.setStyleSheet("padding-left: 1px;padding-right: 1px;")
        elif state.className == "Playblast":
            state.b_resPresets.setStyleSheet("padding-left: 1px;padding-right: 1px;")
