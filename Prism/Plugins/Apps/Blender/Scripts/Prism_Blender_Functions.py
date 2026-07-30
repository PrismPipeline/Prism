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
import math
from typing import Any, Dict, List, Optional, Tuple

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


def renderFinished_handler(dummy: Any) -> None:
    """Handler called when render finishes.
    
    Args:
        dummy: Unused handler argument.
    """
    bpy.context.scene["PrismIsRendering"] = False


class Prism_Blender_Functions(object):
    """Core functions for Blender plugin.
    
    Provides main DCC functionality including scene management, import/export,
    rendering, playblasts, and State Manager integration for Blender.
    
    Attributes:
        core: PrismCore instance.
        plugin: Plugin instance.
        importHandlers (Dict): File format import handlers.
        exportHandlers (Dict): File format export handlers.
    """
    
    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize Blender plugin functions.
        
        Registers callbacks and sets up import/export handlers.
        
        Args:
            core: PrismCore instance.
            plugin: Plugin instance.
        """
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
        self.core.registerCallback(
            "onGenerateStateNameContext", self.onGenerateStateNameContext, plugin=self.plugin
        )

        self.importHandlers = {
            ".abc": {"importFunction": self.importAlembic},
            ".fbx": {"importFunction": self.importFBX},
            ".obj": {"importFunction": self.importObj},
            ".glb": {"importFunction": self.importGlb},
        }

        self.exportHandlers = {
            ".abc": {"exportFunction": self.exportAlembic},
            ".fbx": {"exportFunction": self.exportFBX},
            ".obj": {"exportFunction": self.exportObj},
            ".glb": {"exportFunction": self.exportGLB},
            ".blend": {"exportFunction": self.exportBlend},
        }
        os.environ["PRISM_PRODUCT_BROWSER_ADD_GL_DUMMY"] = "0"

    @err_catcher(name=__name__)
    def startup(self, origin: Any) -> Optional[bool]:
        """Initialize plugin on Prism startup.
        
        Sets up Blender-specific UI elements and registers Prism menu.
        
        Args:
            origin: PrismCore instance.
        
        Returns:
            False to continue startup, or None on early exit.
        """
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

        if not hasattr(bpy.types, "TOPBAR_MT_prism"):
            self.registerPrismMenu()

    @err_catcher(name=__name__)
    def autosaveEnabled(self, origin: Any) -> bool:
        """Check if Blender autosave is enabled.
        
        Args:
            origin: Originating object.
        
        Returns:
            True if autosave enabled in Blender preferences.
        """
        if bpy.app.version < (2, 80, 0):
            return bpy.context.user_preferences.filepaths.use_auto_save_temporary_files
        else:
            return bpy.context.preferences.filepaths.use_auto_save_temporary_files

    @err_catcher(name=__name__)
    def sceneOpen(self, origin: Any) -> None:
        """Callback when scene file is opened.
        
        Restarts autosave timer if conditions are met.
        
        Args:
            origin: PrismCore instance.
        """
        if self.core.shouldAutosaveTimerRun():
            origin.startAutosaveTimer()

    @err_catcher(name=__name__)
    def getCurrentFileName(self, origin: Any, path: bool = True) -> str:
        """Get current scene file name.
        
        Args:
            origin: Originating object.
            path: If True returns full path, if False returns basename only.
        
        Returns:
            Scene file path or name.
        """
        currentFileName = bpy.data.filepath

        if not path:
            currentFileName = os.path.basename(currentFileName)

        return currentFileName

    @err_catcher(name=__name__)
    def getSceneExtension(self, origin: Any) -> str:
        """Get scene file extension.
        
        Args:
            origin: Originating object.
        
        Returns:
            Scene file extension (.blend).
        """
        return self.sceneFormats[0]

    @err_catcher(name=__name__)
    def saveScene(self, origin: Any, filepath: str, details: Optional[Dict] = None, usedTimer: bool = False) -> Any:
        """Save current scene to file.
        
        Args:
            origin: Originating object.
            filepath: Path to save scene file.
            details: Additional details (unused). Defaults to None.
            usedTimer: Whether called from timer. Defaults to False.
        
        Returns:
            Result from Blender save operation or None.
        """
        if bpy.app.is_job_running("RENDER"):
            self.core.popup("Unable to save blendfile while rendering.")
            return False

        result = None
        filepath = os.path.normpath(filepath)
        if not os.path.exists(os.path.dirname(filepath)):
            while not os.path.exists(os.path.dirname(filepath)):
                try:
                    os.makedirs(os.path.dirname(filepath))
                except Exception as e:
                    msg = "Failed to create folder:\n\n%s\n\nError: %s" % (os.path.dirname(filepath), str(e))
                    result = self.core.popupQuestion(msg, buttons=["Retry", "Cancel"], escapeButton="Cancel", icon=QMessageBox.Warning)
                    if result == "Retry":
                        continue
                    else:
                        return False

        try:
            if bpy.app.version < (4, 0, 0):
                result = bpy.ops.wm.save_as_mainfile(self.getOverrideContext(origin), filepath=filepath, copy=False)
            else:
                with bpy.context.temp_override(**self.getOverrideContext(origin)):
                    result = bpy.ops.wm.save_as_mainfile(filepath=filepath, copy=False)
        except Exception as e:
            if "cannot modify blend data in this state (drawing/rendering)" in str(e):
                logger.warning("saving with timer")
                bpy.app.timers.register(lambda: self.saveScene(origin, filepath, details, usedTimer=True))
            elif "Cannot open file" in str(e) and "Permission denied" in str(e):
                logger.warning(e)
                self.core.popup("Unable to save blendfile. Permission denied.\n\n%s" % filepath)
            else:
                logger.warning(e)
                self.core.popup("Unable to save blendfile. Error:\n\n%s" % str(e))
        else:
            if usedTimer:
                try:
                    self.core.pb.sceneBrowser.refreshScenefilesThreaded()
                except:
                    pass

                result = None

        return result

    @err_catcher(name=__name__)
    def getImportPaths(self, origin: Any) -> Any:
        """Get list of import paths from scene.
        
        Args:
            origin: State Manager instance.
        
        Returns:
            False if no imports, otherwise list of import paths.
        """
        if "PrismImports" not in bpy.context.scene:
            return False
        else:
            return bpy.context.scene["PrismImports"]

    @err_catcher(name=__name__)
    def getFrameRange(self, origin: Any) -> List[int]:
        """Get animation frame range.
        
        Args:
            origin: Originating object.
        
        Returns:
            List of [start frame, end frame].
        """
        startframe = bpy.context.scene.frame_start
        endframe = bpy.context.scene.frame_end

        return [startframe, endframe]

    @err_catcher(name=__name__)
    def getCurrentFrame(self) -> int:
        """Get current frame number.
        
        Returns:
            Current frame number.
        """
        currentFrame = bpy.context.scene.frame_current
        return currentFrame

    @err_catcher(name=__name__)
    def setFrameRange(self, origin: Any, startFrame: int, endFrame: int) -> None:
        """Set animation frame range.
        
        Args:
            origin: Originating object.
            startFrame: Start frame number.
            endFrame: End frame number.
        """
        bpy.context.scene.frame_start = int(startFrame)
        bpy.context.scene.frame_end = int(endFrame)
        bpy.context.scene.frame_current = int(startFrame)
        try:
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
        except:
            pass  # if no timeline is visible

    @err_catcher(name=__name__)
    def getFPS(self, origin: Any) -> float:
        """Get scene framerate.
        
        Args:
            origin: Originating object.
        
        Returns:
            Frames per second.
        """
        intFps = bpy.context.scene.render.fps
        baseFps = bpy.context.scene.render.fps_base
        return round(intFps / baseFps, 2)

    @err_catcher(name=__name__)
    def setFPS(self, origin: Any, fps: float) -> None:
        """Set scene framerate.
        
        Args:
            origin: Originating object.
            fps: Frames per second to set.
        """
        if int(fps) == fps:
            bpy.context.scene.render.fps = int(fps)
        else:
            intFps = math.ceil(fps)
            bpy.context.scene.render.fps = intFps
            bpy.context.scene.render.fps_base = intFps/fps

    @err_catcher(name=__name__)
    def getResolution(self) -> List[int]:
        """Get render resolution.
        
        Returns:
            List of [width, height] in pixels.
        """
        width = bpy.context.scene.render.resolution_x
        height = bpy.context.scene.render.resolution_y
        return [width, height]

    @err_catcher(name=__name__)
    def setResolution(self, width: Optional[int] = None, height: Optional[int] = None) -> None:
        """Set render resolution.
        
        Args:
            width: Width in pixels. Defaults to None (unchanged).
            height: Height in pixels. Defaults to None (unchanged).
        """
        if width:
            bpy.context.scene.render.resolution_x = width
        if height:
            bpy.context.scene.render.resolution_y = height

    @err_catcher(name=__name__)
    def getAppVersion(self, origin: Any) -> str:
        """Get Blender version string.
        
        Args:
            origin: Originating object.
        
        Returns:
            Blender version number.
        """
        return bpy.app.version_string.split()[0]

    @err_catcher(name=__name__)
    def onProjectBrowserStartup(self, origin: Any) -> None:
        """Callback on Project Browser startup.
        
        Sets UI colors for older Blender versions.
        
        Args:
            origin: Project Browser instance.
        """
        if bpy.app.version < (2, 80, 0):
            origin.publicColor = QColor(50, 100, 170)

    @err_catcher(name=__name__)
    def newScene(self, force: bool = False) -> bool:
        """Create new empty scene.
        
        Args:
            force: Force creation without prompt. Defaults to False.
        
        Returns:
            True if scene created.
        """
        ctx = self.getOverrideContext(dftContext=False)
        if bpy.app.version < (4, 0, 0):
            bpy.ops.wm.read_homefile(ctx, "INVOKE_DEFAULT", use_empty=True)
        else:
            with bpy.context.temp_override(**ctx):
                bpy.ops.wm.read_homefile("INVOKE_DEFAULT", use_empty=True)

        return True

    @err_catcher(name=__name__)
    def openScene(self, origin: Any, filepath: str, force: bool = False) -> bool:
        """Open scene file.
        
        Args:
            origin: Originating object.
            filepath: Path to scene file to open.
            force: Force open without prompt. Defaults to False.
        
        Returns:
            False if not a blend file, otherwise continues with open.
        """
        if not filepath.endswith(".blend"):
            return False

        ctx = self.getOverrideContext(dftContext=False)
        filepath = os.path.normpath(filepath)
        try:
            if bpy.app.version < (4, 0, 0):
                bpy.ops.wm.open_mainfile(ctx, "INVOKE_DEFAULT", filepath=filepath, display_file_selector=False)
            else:
                if "screen" in ctx:
                    ctx.pop("screen")

                with bpy.context.temp_override(**ctx):
                    bpy.ops.wm.open_mainfile("INVOKE_DEFAULT", filepath=filepath, display_file_selector=False)
        except Exception as e:
            if "File written by newer Blender binary" in str(e):
                msg = "Warning occurred while opening file:\n\n%s\n\nError: %s" % (filepath, str(e))
                self.core.popup(msg)
            elif "Failed to read blend file" in str(e):
                msg = "Warning occurred while opening file:\n\n%s\n\nError: %s" % (filepath, str(e))
                self.core.popup(msg)
            else:
                self.core.popup("Unable to open blendfile. Error:\n\n%s" % str(e))

        return True

    @err_catcher(name=__name__)
    def onUserSettingsOpen(self, origin: Any) -> None:
        """Callback when user settings dialog opens.
        
        Adjusts dialog size.
        
        Args:
            origin: User settings dialog instance.
        """
        origin.resize(origin.width(), origin.height() + 60)

    @err_catcher(name=__name__)
    def getGroups(self) -> Any:
        """Get groups/collections from scene.
        
        Returns:
            Blender data groups (2.7x) or collections (2.8+).
        """
        if bpy.app.version < (2, 80, 0):
            return bpy.data.groups
        else:
            return bpy.data.collections

    @err_catcher(name=__name__)
    def createGroups(self, name: str) -> Any:
        """Create new group/collection.
        
        Args:
            name: Name for new group/collection.
        
        Returns:
            Result of creation operation.
        """
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
    def getSelectObject(self, obj: Any) -> bool:
        """Get selection state of object.
        
        Args:
            obj: Blender object.
        
        Returns:
            True if object is selected.
        """
        if bpy.app.version < (2, 80, 0):
            return obj.select
        else:
            return obj.select_get()

    @err_catcher(name=__name__)
    def selectObjects(self, objs: List, select: bool = True, quiet: bool = False) -> None:
        """Select multiple objects.
        
        Args:
            objs: List of objects to select.
            select: True to select, False to deselect. Defaults to True.
            quiet: Suppress error messages. Defaults to False.
        """
        for obj in objs:
            self.selectObject(obj, select=select, quiet=quiet)

    @err_catcher(name=__name__)
    def deselectObjects(self) -> None:
        """Deselect all objects in scene."""
        viewLayer = getattr(bpy.context, "view_layer", None)
        if not viewLayer and bpy.context.window_manager.windows:
            viewLayer = bpy.context.window_manager.windows[0].view_layer

        if viewLayer:
            try:
                viewLayer.objects.active = None
            except Exception:
                pass

            for obj in list(viewLayer.objects):
                try:
                    obj.select_set(False, view_layer=viewLayer)
                except TypeError:
                    obj.select_set(False)

            return

        try:
            if bpy.app.version < (4, 0, 0):
                bpy.ops.object.select_all(
                    self.getOverrideContext(), action="DESELECT"
                )
            else:
                with bpy.context.temp_override(**self.getOverrideContext()):
                    bpy.ops.object.select_all(action="DESELECT")
        except RuntimeError:
            pass

    @err_catcher(name=__name__)
    def selectObject(self, obj: Any, select: bool = True, quiet: bool = False) -> None:
        """Select single object.
        
        Handles viewlayer switching if object not on current viewlayer.
        
        Args:
            obj: Blender object to select.
            select: True to select, False to deselect. Defaults to True.
            quiet: Suppress viewlayer prompts. Defaults to False.
        """
        if bpy.app.version < (2, 80, 0):
            obj.select = select
            bpy.context.scene.objects.active = obj
        else:
            curlayer = bpy.context.window_manager.windows[0].view_layer
            if obj.bl_rna.identifier.upper() == "COLLECTION":
                self.selectObjects(obj.all_objects, quiet=quiet)
            else:
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
                        else:
                            return
                    else:
                        if not quiet:
                            self.core.popup(
                                "The object '%s' is not on the current viewlayer and couldn't be found on any other viewlayer. This object can't be selected and will be skipped in the current process."
                                % obj.name
                            )
                        return

                obj.select_set(select, view_layer=curlayer)
                curlayer.objects.active = obj

    @err_catcher(name=__name__)
    def sm_export_addObjects(self, origin: Any, objects: Optional[List] = None) -> None:
        """Add objects to export state.
        
        Args:
            origin: Export state instance.
            objects: Objects to add. Defaults to None (uses selection).
        """
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
            objects = self.getSelectedNodes()

        for obj in objects:
            if obj.bl_rna.identifier.upper() == "COLLECTION":
                children = self.getGroups()[taskName].children
                if obj not in list(children):
                    children.link(obj)
            elif obj.bl_rna.identifier.upper() == "OBJECT":
                collection = self.getGroups()[taskName]
                if obj not in list(collection.objects):
                    collection.objects.link(obj)

    @err_catcher(name=__name__)
    def getNodeName(self, origin: Any, node: Dict) -> str:
        """Get node name.
        
        Args:
            origin: Originating object.
            node: Node dictionary.
        
        Returns:
            Node name.
        """
        return node["name"]

    @err_catcher(name=__name__)
    def getSelectedNodes(self) -> List:
        """Get currently selected nodes/objects.
        
        Returns:
            List of selected objects and collections.
        """
        if bpy.app.version < (4, 0, 0):
            objects = [
                o
                for o in bpy.context.scene.objects
                if self.getSelectObject(o)
            ]
        else:
            window = bpy.context.window_manager.windows[0]
            area = next((area for area in window.screen.areas if area.type == 'OUTLINER'), None)
            if area:
                region = next((region for region in area.regions if region.type == 'WINDOW'), None)
                if region:
                    with bpy.context.temp_override(
                        window=window,
                        area=area,
                        region=region,
                        screen=window.screen
                    ):
                        ids = bpy.context.selected_ids
                        objects = ids
                else:
                    # No WINDOW region found, fallback to pre-4.0 approach
                    objects = [
                        o
                        for o in bpy.context.scene.objects
                        if self.getSelectObject(o)
                    ]
            else:
                # No OUTLINER area found, fallback to pre-4.0 approach
                objects = [
                    o
                    for o in bpy.context.scene.objects
                    if self.getSelectObject(o)
                ]

        return objects

    @err_catcher(name=__name__)
    def selectNodes(self, origin: Any) -> None:
        """Select nodes from export state list.
        
        Args:
            origin: Export state instance with node list.
        """
        if origin.lw_objects.selectedItems() != []:
            self.deselectObjects()
            for i in origin.lw_objects.selectedItems():
                node = origin.nodes[origin.lw_objects.row(i)]
                if self.getObject(node):
                    self.selectObject(self.getObject(node), quiet=True)

    @err_catcher(name=__name__)
    def isNodeValid(self, origin: Any, node: Any) -> bool:
        """Check if node is valid.
        
        Args:
            origin: Originating object.
            node: Node to check (string or dict).
        
        Returns:
            True if node exists in scene.
        """
        if type(node) == str:
            node = self.getNode(node)

        return bool(self.getObject(node))

    @err_catcher(name=__name__)
    def getCamNodes(self, origin: Any, cur: bool = False) -> List[str]:
        """Get list of camera node names.
        
        Args:
            origin: Originating object.
            cur: Unused parameter.
        
        Returns:
            List of camera names.
        """
        return [x.name for x in bpy.context.scene.objects if x.type == "CAMERA"]

    @err_catcher(name=__name__)
    def getCamName(self, origin: Any, handle: str) -> str:
        """Get camera name from handle.
        
        Args:
            origin: Originating object.
            handle: Camera handle (name).
        
        Returns:
            Camera name.
        """
        return handle

    @err_catcher(name=__name__)
    def selectCam(self, origin: Any) -> None:
        """Select camera from export state.
        
        Args:
            origin: Export state with curCam attribute.
        """
        if self.getObject(origin.curCam):
            self.deselectObjects()
            self.selectObject(self.getObject(origin.curCam))

    @err_catcher(name=__name__)
    def sm_export_startup(self, origin: Any) -> None:
        """Initialize export state UI.
        
        Args:
            origin: Export state instance.
        """
        if origin.className == "Export":
            origin.w_additionalOptions.setVisible(False)

    @err_catcher(name=__name__)
    def getValidGroupName(self, groupName: str) -> str:
        """Get unique group name.
        
        Adds numeric suffix if name already exists.
        
        Args:
            groupName: Desired group name.
        
        Returns:
            Unique group name.
        """
        extension = 1
        while groupName in self.getGroups() and extension < 999:
            if "%s_%s" % (groupName, extension) not in self.getGroups():
                groupName += "_%s" % extension
            extension += 1

        return groupName

    @err_catcher(name=__name__)
    def sm_export_setTaskText(self, origin: Any, prevTaskName: str, newTaskName: str) -> str:
        """Set export task name and rename collection.
        
        Args:
            origin: Export state instance.
            prevTaskName: Previous task/collection name.
            newTaskName: New task/collection name.
        
        Returns:
            Final set name.
        """
        setName = newTaskName
        if prevTaskName and prevTaskName in self.getGroups():
            self.getGroups()[prevTaskName].name = setName
        else:
            self.createGroups(name=setName)

        return setName

    @err_catcher(name=__name__)
    def sm_export_removeSetItem(self, origin: Any, node: Dict) -> None:
        """Remove item from export set.
        
        Args:
            origin: Export state instance.
            node: Node to remove.
        """
        if origin.getTaskname() not in self.getGroups():
            return

        obj = self.getObject(node)
        if obj.bl_rna.identifier.upper() == "COLLECTION":
            if obj in list(self.getGroups()[origin.getTaskname()].children):
                self.getGroups()[origin.getTaskname()].children.unlink(obj)
        else:
            if obj in list(self.getGroups()[origin.getTaskname()].objects):
                self.getGroups()[origin.getTaskname()].objects.unlink(obj)

    @err_catcher(name=__name__)
    def sm_export_clearSet(self, origin: Any) -> None:
        """Clear all objects from export set.
        
        Args:
            origin: Export state instance.
        """
        if origin.getTaskname() not in self.getGroups():
            return

        for node in self.getGroups()[origin.getTaskname()].objects:
            self.getGroups()[origin.getTaskname()].objects.unlink(node)

        for node in self.getGroups()[origin.getTaskname()].children:
            self.getGroups()[origin.getTaskname()].children.unlink(node)

    @err_catcher(name=__name__)
    def sm_export_updateObjects(self, origin: Any) -> None:
        """Update export objects list from collection.
        
        Args:
            origin: Export state instance.
        """
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

            for obj in group.children:
                nodes.append(self.getNode(obj))

            origin.nodes = nodes

    @err_catcher(name=__name__)
    def sm_export_exportShotcam(self, origin: Any, startFrame: int, endFrame: int, outputName: str) -> None:
        """Export shot camera to Alembic and FBX.
        
        Args:
            origin: Export state instance.
            startFrame: Start frame number.
            endFrame: End frame number.
            outputName: Output file path (without extension).
        """
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

        self.deselectObjects()

    @err_catcher(name=__name__)
    def exportObj(self, outputName: str, origin: Any, startFrame: int, endFrame: int, expNodes: List) -> str:
        """Export objects to OBJ format.
        
        Args:
            outputName: Output file path with #### frame placeholder.
            origin: Export state instance.
            startFrame: Start frame number.
            endFrame: End frame number.
            expNodes: Nodes to export.
        
        Returns:
            Final output file path.
        """
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
    def exportSelectionToObj(self, outputName: str) -> bool:
        """Export selected objects to OBJ format (Blender 4.0+).
        
        Args:
            outputName: Output file path.
        
        Returns:
            True if export succeeded.
        """
        with bpy.context.temp_override(**self.getOverrideContext()):
            bpy.ops.wm.obj_export(
                filepath=outputName,
                export_selected_objects=True,
                export_colors=True,
            )

        return True

    @err_catcher(name=__name__)
    def exportSelectionToFbx(self, outputName: str) -> bool:
        """Export selected objects to FBX format (Blender 4.0+).
        
        Args:
            outputName: Output file path.
        
        Returns:
            True if export succeeded.
        """
        with bpy.context.temp_override(**self.getOverrideContext()):
            bpy.ops.export_scene.fbx(
                filepath=outputName,
                use_selection=True,
                bake_anim=False,
                colors_type="LINEAR",
                apply_unit_scale=False,
                global_scale=0.01,
            )

        return True

    @err_catcher(name=__name__)
    def exportFBX(self, outputName: str, origin: Any, startFrame: int, endFrame: int, expNodes: List) -> str:
        """Export objects to FBX format.
        
        Args:
            outputName: Output file path.
            origin: Export state instance.
            startFrame: Start frame number.
            endFrame: End frame number.
            expNodes: Nodes to export.
        
        Returns:
            Output file path.
        """
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
    def exportAlembic(self, outputName: str, origin: Any, startFrame: int, endFrame: int, expNodes: List, additionalSettings: Optional[Dict] = None) -> str:
        """Export objects to Alembic format.
        
        Args:
            outputName: Output file path.
            origin: Export state instance.
            startFrame: Start frame number.
            endFrame: End frame number.
            expNodes: Nodes to export.
            additionalSettings: Additional export settings. Defaults to None.
        
        Returns:
            Output file path.
        """
        if getattr(origin, "additionalSettings", None):
            additionalSettings = additionalSettings or {}
            for setting in origin.additionalSettings:
                if setting["name"] == "abcScale":
                    additionalSettings["global_scale"] = setting["value"]

        if bpy.app.version < (4, 0, 0):
            bpy.ops.wm.alembic_export(
                self.getOverrideContext(origin),
                filepath=outputName,
                start=startFrame,
                end=endFrame,
                selected=(not origin.chb_wholeScene.isChecked()),
                as_background_job=False,
                **additionalSettings,
            )
        else:
            with bpy.context.temp_override(**self.getOverrideContext(origin)):
                bpy.ops.wm.alembic_export(
                    filepath=outputName,
                    start=startFrame,
                    end=endFrame,
                    selected=(not origin.chb_wholeScene.isChecked()),
                    as_background_job=False,
                    **additionalSettings,
                )

        return outputName

    @err_catcher(name=__name__)
    def exportGLB(self, outputName: str, origin: Any, startFrame: int, endFrame: int, expNodes: List) -> str:
        """Export objects to GLB format.
        
        Args:
            outputName: Output file path.
            origin: Export state instance.
            startFrame: Start frame number.
            endFrame: End frame number.
            expNodes: Nodes to export.
        
        Returns:
            Output file path.
        """
        with bpy.context.temp_override(**self.getOverrideContext(origin)):
            bpy.ops.export_scene.gltf(
                filepath=outputName,
                use_selection=(not origin.chb_wholeScene.isChecked()),
                export_format="GLB",
            )

        return outputName

    @err_catcher(name=__name__)
    def exportBlend(self, outputName: str, origin: Any, startFrame: int, endFrame: int, expNodes: List) -> str:
        """Export objects to Blend format.
        
        Copies whole file or saves selection to new file.
        
        Args:
            outputName: Output file path.
            origin: Export state instance.
            startFrame: Start frame number.
            endFrame: End frame number.
            expNodes: Nodes to export.
        
        Returns:
            Output file path.
        """
        if origin.chb_wholeScene.isChecked():
            try:
                shutil.copyfile(self.core.getCurrentFileName(), outputName)
            except Exception as e:
                self.core.popup("Couldn't copy blend file. Error:\n\n%s" % str(e))

        else:
            origin.setLastPath(outputName)
            self.core.saveScene(prismReq=False)
            expObjects = [self.getObject(x) for x in expNodes]
            for expObject in expObjects:
                if expObject.bl_rna.identifier.upper() == "COLLECTION":
                    for obj in expObject.all_objects:
                        if obj not in expObjects:
                            expObjects.append(obj)

            for object_ in bpy.data.objects:
                if object_ not in expObjects:
                    bpy.data.objects.remove(object_, do_unlink=True)

            bpy.ops.wm.save_as_mainfile(filepath=outputName, copy=True)
            try:
                bpy.ops.wm.revert_mainfile()
            except Exception as e:
                self.core.popup("Warning: Couldn't revert to original file after saving selection to new blend file. Error:\n\n%s" % str(e))

            self.core.stateManager()

        return outputName

    @err_catcher(name=__name__)
    def exportUsd(self, outputName: str, origin: Any, startFrame: int, endFrame: int, expNodes: List, catchError: bool = True, additionalSettings: Optional[Dict] = None) -> Any:
        """Export objects to USD format.
        
        Args:
            outputName: Output file path.
            origin: Export state instance.
            startFrame: Start frame number.
            endFrame: End frame number.
            expNodes: Nodes to export.
            catchError: Catch errors and return False. Defaults to True.
            additionalSettings: Additional export settings. Defaults to None.
        
        Returns:
            Output file path or False if export failed.
        """
        from _bpy import ops as _ops_module
        additionalSettings = additionalSettings or {}
        if bpy.app.version < (5, 1, 0):
            try:
                _ops_module.as_string("WM_OT_usd_export")
                valid = True
            except:
                valid = False
        else:
            valid = "WM_OT_usd_export" in _ops_module.dir()

        if not valid:
            ext = os.path.splitext(outputName)[1]
            msg = "Format \"%s\" is not supported in this Blender version. Exporting USD requires at least Blender 2.82" % ext
            self.core.popup(msg)
            return False

        self.setFrameRange(origin, startFrame, endFrame)
        try:
            if bpy.app.version < (4, 0, 0):
                bpy.ops.wm.usd_export(
                    self.getOverrideContext(origin),
                    filepath=outputName,
                    export_animation=startFrame != endFrame,
                    selected_objects_only=(not origin.chb_wholeScene.isChecked()),
                    **additionalSettings,
                )
            else:
                with bpy.context.temp_override(**self.getOverrideContext(origin)):
                    bpy.ops.wm.usd_export(
                        filepath=outputName,
                        export_animation=startFrame != endFrame,
                        selected_objects_only=(not origin.chb_wholeScene.isChecked()),
                        **additionalSettings,
                    )
        except:
            if catchError:
                return False
            else:
                raise

        return outputName

    @err_catcher(name=__name__)
    def sm_export_exportAppObjects(
        self,
        origin: Any,
        startFrame: int,
        endFrame: int,
        outputName: str,
        additionalSettings: Optional[Dict] = None
    ) -> str:
        """Export objects using app-specific export handlers.
        
        Args:
            origin: Export state instance.
            startFrame: Start frame number.
            endFrame: End frame number.
            outputName: Output file path.
            additionalSettings: Additional export settings. Defaults to None.
        
        Returns:
            Output file path or error message.
        """
        expNodes = origin.nodes
        ctx = self.getOverrideContext(origin)
        if bpy.app.version >= (2, 80, 0):
            ctx.pop("screen")
            ctx.pop("area")

        if bpy.app.version < (4, 0, 0):
            try:
                bpy.ops.object.mode_set(ctx, mode="OBJECT")
            except:
                pass
        else:
            with bpy.context.temp_override(**ctx):
                if bpy.context.object:
                    try:
                        bpy.ops.object.mode_set(mode="OBJECT")
                    except:
                        pass

        if bpy.app.version < (4, 0, 0):
            bpy.ops.object.select_all(ctx, action="DESELECT")
        else:
            with bpy.context.temp_override(**ctx):
                bpy.ops.object.select_all(action="DESELECT")

        ext = origin.getOutputType()
        if ext != ".blend":
            for expNode in expNodes:
                if self.getObject(expNode):
                    self.selectObject(self.getObject(expNode))
        
        if ext in self.exportHandlers:
            if additionalSettings:
                kwargs = {"additionalSettings": additionalSettings}
            else:
                kwargs = {}

            outputName = self.exportHandlers[ext]["exportFunction"](
                outputName, origin, startFrame, endFrame, expNodes, **kwargs
            )
        else:
            msg = "Canceled: Format \"%s\" is not supported." % ext
            return msg

        if bpy.app.version < (4, 0, 0):
            bpy.ops.object.select_all(ctx, action="DESELECT")
        else:
            if ext != ".blend":
                with bpy.context.temp_override(**ctx):
                    bpy.ops.object.select_all(action="DESELECT")

        return outputName

    @err_catcher(name=__name__)
    def sm_export_preDelete(self, origin: Any) -> None:
        """Clean up on export state deletion.
        
        Removes associated collection.
        
        Args:
            origin: Export state instance.
        """
        try:
            self.getGroups().remove(self.getGroups()[origin.getTaskname()], do_unlink=True)
        except Exception as e:
            logger.warning(e)

    @err_catcher(name=__name__)
    def getOverrideContext(self, origin: Optional[Any] = None, context: Optional[str] = None, dftContext: bool = True) -> Dict:
        """Get Blender context override for operators.
        
        Args:
            origin: Originating object.
            context: Specific context type to find. Defaults to None.
            dftContext: Use default context copy. Defaults to True.
        
        Returns:
            Context dictionary for operator execution.
        """
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
                    ctx["region"] = None
                    return ctx

            for area in screen.areas:
                if area.type == "IMAGE_EDITOR":
                    ctx["area"] = area
                    ctx["region"] = None
                    return ctx

            for area in screen.areas:
                if area.type == "NODE_EDITOR":
                    ctx["area"] = area
                    ctx["region"] = None
                    return ctx

        return ctx

    @err_catcher(name=__name__)
    def registerPrismMenu(self) -> None:
        """Register Prism menu in Blender top menu bar."""
        options = []

        op = {"name": "save", "label": "Save Version", "code": "import PrismInit\nif platform.system() == \"Linux\":\n    PrismInit.pcore.saveScene()\n    for i in QApplication.topLevelWidgets():\n        if i.isVisible():\n            qApp.exec_()\n            break\nelse:\n    PrismInit.pcore.saveScene()"}
        options.append(op)

        op = {"name": "savecomment", "label": "Save with Comment", "code": "import PrismInit\nif platform.system() == \"Linux\":\n    PrismInit.pcore.saveWithComment()\n    for i in QApplication.topLevelWidgets():\n        if i.isVisible():\n            qApp.exec_()\n            break\nelse:\n    PrismInit.pcore.saveWithComment()"}
        options.append(op)

        op = {"name": "browser", "label": "Project Browser", "code": "import PrismInit\nif platform.system() == \"Linux\":\n    PrismInit.pcore.projectBrowser()\n    qApp.exec_()\nelse:\n    PrismInit.pcore.projectBrowser()"}
        options.append(op)

        op = {"name": "manager", "label": "State Manager", "code": "import PrismInit\nif platform.system() == \"Linux\":\n    PrismInit.pcore.stateManager()\n    qApp.exec_()\nelse:\n    PrismInit.pcore.stateManager()"}
        options.append(op)

        op = {"name": "settings", "label": "Settings", "code": "import PrismInit\nif platform.system() == \"Linux\":\n    PrismInit.pcore.prismSettings()\n    qApp.exec_()\nelse:\n    PrismInit.pcore.prismSettings()"}
        options.append(op)

        self.addMenuToMainMenuBar(
            "prism",
            "Prism",
            options
        )

    @err_catcher(name=__name__)
    def registerOperator(self, name: str, label: str, code: str) -> None:
        """Register custom Blender operator.
        
        Args:
            name: Operator name.
            label: Display label.
            code: Python code to execute.
        """
        def execute(self, context):
            exec(code)
            return {"FINISHED"}

        opClass = type(
            "Prism_" + name,
            (bpy.types.Operator,),
            {
                "bl_idname": "object.prism_%s" % name,
                "bl_label": label,
                "execute": execute
            },
        )

        bpy.utils.register_class(opClass)

    @err_catcher(name=__name__)
    def addMenuToMainMenuBar(self, name: str, label: str, options: List[Dict]) -> None:
        """Add menu to Blender main menu bar.
        
        Args:
            name: Menu name.
            label: Display label.
            options: List of menu option dictionaries.
        """
        for option in options:
            self.registerOperator(option["name"], option["label"], option["code"])

        def draw(self, context):
            layout = self.layout

            for option in options:
                row = layout.row()
                row.operator("object.prism_%s" % option["name"])

        menuClass = type(
            "TOPBAR_MT_" + name,
            (bpy.types.Menu,),
            {
                "bl_label": label,
                "draw": draw,
            },
        )

        def draw(self, context):
            self.layout.menu("TOPBAR_MT_" + name)

        bpy.utils.register_class(menuClass)
        bpy.types.TOPBAR_MT_editor_menus.append(draw)

    @err_catcher(name=__name__)
    def sm_export_preExecute(self, origin: Any, startFrame: int, endFrame: int) -> List:
        """Pre-execution checks for export state.
        
        Args:
            origin: Export state instance.
            startFrame: Start frame number.
            endFrame: End frame number.
        
        Returns:
            List of warning messages.
        """
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
    def sm_render_startup(self, origin: Any) -> None:
        """Initialize render state.
        
        Args:
            origin: Render state instance.
        """
        origin.gb_passes.setCheckable(False)
        origin.sp_rangeStart.setValue(bpy.context.scene.frame_start)
        origin.sp_rangeEnd.setValue(bpy.context.scene.frame_end)

        origin.b_resPresets.setMinimumWidth(30 * self.core.uiScaleFactor)
        origin.b_resPresets.setMinimumHeight(0)
        origin.b_resPresets.setMaximumHeight(500 * self.core.uiScaleFactor)

        origin.b_osSlaves.setMinimumWidth(50 * self.core.uiScaleFactor)

    @err_catcher(name=__name__)
    def sm_render_rightclickPasses(self, origin: Any, menu: Any, pos: Any) -> None:
        """Handle right-click on render passes list.
        
        Args:
            origin: Render state instance.
            menu: Context menu.
            pos: Click position.
        """
        idx = origin.tw_passes.indexAt(pos)
        item = origin.tw_passes.itemFromIndex(idx)
        if not item:
            return

        data = item.data(0, Qt.UserRole)
        if data and data.get("node"):
            if data.get("node").mute:
                act = QAction("Enable", origin)
                act.triggered.connect(lambda: setattr(data["node"], "mute", False))
                act.triggered.connect(lambda: self.sm_render_refreshPasses(origin))
            else:
                act = QAction("Disable", origin)
                act.triggered.connect(lambda: setattr(data["node"], "mute", True))
                act.triggered.connect(lambda: self.sm_render_refreshPasses(origin))

            menu.addAction(act)

    @err_catcher(name=__name__)
    def sm_render_refreshPasses(self, origin: Any) -> None:
        """Refresh render passes list.
        
        Args:
            origin: Render state instance.
        """
        origin.tw_passes.clear()

        passNames = self.getNodeAOVs()
        logger.debug("node aovs: %s" % passNames)
        origin.b_addPasses.setVisible(not passNames)
        self.plugin.canDeleteRenderPasses = True  # bool(not passNames)
        if not passNames:
            passNames = self.getViewLayerAOVs()
            logger.debug("viewlayer aovs: %s" % passNames)

        if passNames:
            for group in passNames:
                if group["name"]:
                    item = QTreeWidgetItem([group["name"]])
                    item.setData(0, Qt.UserRole, {"node": group["node"]})
                    origin.tw_passes.addTopLevelItem(item)
                    item.setExpanded(True)
                    if not group.get("enabled", True):
                        item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                else:
                    item = origin.tw_passes.invisibleRootItem()

                for passName in group["passes"]:
                    citem = QTreeWidgetItem([passName])
                    item.addChild(citem)
                    if not group.get("enabled", True):
                        citem.setFlags(citem.flags() & ~Qt.ItemIsEnabled)

    @err_catcher(name=__name__)
    def getNodeAOVs(self) -> Optional[List[Dict]]:
        """Get AOVs from compositor file output nodes.
        
        Returns:
            List of AOV groups or None if no compositor nodes.
        """
        if bpy.app.version >= (5, 0, 0):
            if not bpy.context.scene.compositing_node_group:
                return

            nodes = bpy.context.scene.compositing_node_group.nodes
        else:
            if bpy.context.scene.node_tree is None or not bpy.context.scene.use_nodes:
                return

            nodes = bpy.context.scene.node_tree.nodes

        outNodes = [
            x for x in nodes if x.type == "OUTPUT_FILE"
        ]
        passNames = []
        for outNode in outNodes:
            nodePassNames = []
            layername = outNode.label
            connections = []
            for i in outNode.inputs:
                if len(list(i.links)) > 0:
                    connections.append(i.links[0])

            if outNode.format.file_format == "OPEN_EXR_MULTILAYER":
                if hasattr(outNode, "layer_slots"):  # removed in Blender 5.0
                    _inputs = outNode.layer_slots
                else:
                    _inputs = outNode.file_output_items

                for _input in _inputs:
                    nodePassNames.append(_input.name)
            else:
                if hasattr(outNode, "file_slots"):  # removed in Blender 5.0
                    _inputs = outNode.file_slots
                    for _input in _inputs:
                        nodePassNames.append(os.path.basename(_input.path))
                else:
                    _inputs = outNode.file_output_items
                    for _input in _inputs:
                        nodePassNames.append(_input.name)

            if not layername and connections:
                if connections[0].from_node.type == "R_LAYERS":
                    layername = connections[0].from_node.layer

            if not layername:
                layername = outNode.name

            if nodePassNames:
                passNames.append({"name": layername, "passes": nodePassNames, "enabled": not outNode.mute, "node": outNode})

        return passNames

    @err_catcher(name=__name__)
    def getViewLayerAOVs(self) -> List[Dict]:
        """Get AOVs from view layer settings.
        
        Returns:
            List containing view layer AOV dictionary.
        """
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
                if aa["name"] == "Cryptomatte Accurate" and bpy.app.version >= (4, 0, 0):
                    continue

                aovNames.append(aa["name"])

        return [{"name": "", "passes": aovNames}]

    @err_catcher(name=__name__)
    def getAvailableAOVs(self) -> List[Dict]:
        """Get list of available AOVs.
        
        Returns:
            List of AOV dictionaries with name and parameter.
        """
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
    def sm_render_openPasses(self, origin: Any, item: Optional[Any] = None) -> None:
        """Open render passes manager (not implemented for Blender).
        
        Args:
            origin: Render state instance.
            item: Selected item. Defaults to None.
        """
        pass

    @err_catcher(name=__name__)
    def useNodeAOVs(self) -> bool:
        """Check if compositor node AOVs are used.
        
        Returns:
            True if node AOVs exist.
        """
        return bool(self.getNodeAOVs())

    @err_catcher(name=__name__)
    def removeAOV(self, aovName: str) -> None:
        """Remove AOV/render pass.
        
        Args:
            aovName: Name of AOV to remove.
        """
        if self.useNodeAOVs():
            if bpy.app.version >= (5, 0, 0):
                nodes = bpy.context.scene.compositing_node_group.nodes
            else:
                nodes = bpy.context.scene.node_tree.nodes

            outNodes = [
                x for x in nodes if x.type == "OUTPUT_FILE"
            ]
            for outNode in outNodes:
                if outNode.format.file_format == "OPEN_EXR_MULTILAYER":
                    if hasattr(outNode, "layer_slots"):  # removed in Blender 5.0
                        _inputs = outNode.layer_slots
                        for idx, layer_slot in enumerate(_inputs):
                            if layer_slot.name == aovName:
                                outNode.inputs.remove(outNode.inputs[idx])
                                return
                    else:
                        _inputs = outNode.file_output_items
                        for idx, layer_slot in enumerate(_inputs):
                            if layer_slot.name == aovName:
                                outNode.file_output_items.remove(outNode.file_output_items[idx])
                                return

                else:
                    if hasattr(outNode, "file_slots"):  # removed in Blender 5.0
                        for idx, file_slot in enumerate(outNode.file_slots):
                            if os.path.basename(file_slot.path) == aovName:
                                outNode.inputs.remove(outNode.inputs[idx])
                                return
                    else:
                        _inputs = outNode.file_output_items
                        for idx, layer_slot in enumerate(_inputs):
                            if layer_slot.name == aovName:
                                outNode.file_output_items.remove(outNode.file_output_items[idx])
                                return

        else:
            self.enableViewLayerAOV(aovName, enable=False)

    @err_catcher(name=__name__)
    def enableViewLayerAOV(self, name: str, enable: bool = True) -> None:
        """Enable or disable view layer AOV.
        
        Args:
            name: AOV name.
            enable: Enable state. Defaults to True.
        """
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
    def sm_render_preSubmit(self, origin: Any, rSettings: Dict) -> None:
        """Configure render settings before submission.
        
        Modifies rSettings dictionary in place.
        
        Args:
            origin: Render state instance.
            rSettings: Render settings dictionary.
        """
        if origin.chb_resOverride.isChecked():
            rSettings["width"] = bpy.context.scene.render.resolution_x
            rSettings["height"] = bpy.context.scene.render.resolution_y
            bpy.context.scene.render.resolution_x = origin.sp_resWidth.value()
            bpy.context.scene.render.resolution_y = origin.sp_resHeight.value()

        nodeAOVs = self.getNodeAOVs()
        imgFormat = origin.cb_format.currentText()
        if imgFormat == ".exr":
            if not nodeAOVs and self.getViewLayerAOVs() and bpy.app.version < (5, 0, 0):
                fileFormat = "OPEN_EXR_MULTILAYER"
            else:
                if bpy.app.version >= (5, 0, 0) and bpy.context.scene.render.image_settings.file_format == "OPEN_EXR_MULTILAYER":
                    fileFormat = "OPEN_EXR_MULTILAYER"
                else:
                    fileFormat = "OPEN_EXR"

        elif imgFormat == ".png":
            fileFormat = "PNG"
        elif imgFormat == ".jpg":
            fileFormat = "JPEG"

        rSettings["prev_start"] = bpy.context.scene.frame_start
        rSettings["prev_end"] = bpy.context.scene.frame_end
        rSettings["mediaType"] = bpy.context.scene.render.image_settings.media_type
        rSettings["fileformat"] = bpy.context.scene.render.image_settings.file_format
        rSettings["overwrite"] = bpy.context.scene.render.use_overwrite
        rSettings["fileextension"] = bpy.context.scene.render.use_file_extension
        rSettings["resolutionpercent"] = bpy.context.scene.render.resolution_percentage
        rSettings["origOutputName"] = rSettings["outputName"]
        bpy.context.scene["PrismIsRendering"] = True
        bpy.context.scene.render.filepath = rSettings["outputName"]
        bpy.context.scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE" if fileFormat == "OPEN_EXR_MULTILAYER" else "IMAGE"
        bpy.context.scene.render.image_settings.file_format = fileFormat
        bpy.context.scene.render.use_overwrite = True
        if bpy.app.version < (5, 0, 0):
            bpy.context.scene.render.use_file_extension = False

        bpy.context.scene.render.resolution_percentage = 100
        bpy.context.scene.camera = bpy.context.scene.objects[origin.curCam]

        usePasses = False
        if self.useNodeAOVs():
            if bpy.app.version >= (5, 0, 0):
                nodes = bpy.context.scene.compositing_node_group.nodes
            else:
                nodes = bpy.context.scene.node_tree.nodes

            outNodes = [
                x for x in nodes if x.type == "OUTPUT_FILE"
            ]
            rlayerNodes = [
                x for x in nodes if x.type == "R_LAYERS"
            ]

            for m in outNodes:
                connections = []
                for idx, i in enumerate(m.inputs):
                    if len(list(i.links)) > 0:
                        connections.append([i.links[0], idx])

                extensions = {
                    "PNG": ".png",
                    "JPEG": ".jpg",
                    "JPEG2000": "jpg",
                    "TARGA": ".tga",
                    "TARGA_RAW": ".tga",
                    "OPEN_EXR_MULTILAYER": ".exr",
                    "OPEN_EXR": ".exr",
                    "TIFF": ".tif",
                    "AVIF": ".avif",
                    "WEBP": ".webp",
                    "DPX": ".dpx",
                }
                nodeExt = extensions[m.format.file_format]
                if m.format.file_format == "OPEN_EXR_MULTILAYER":
                    filename, ext = os.path.splitext(os.path.basename(rSettings["outputName"]))
                    layername = ""
                    if len(outNodes) > 1:
                        layername = m.label
                        if not layername and connections:
                            if connections[0][0].from_node.type == "R_LAYERS":
                                layername = connections[0][0].from_node.layer

                        if not layername:
                            layername = m.name

                    if layername:
                        filename = filename.replace("beauty", "beauty_" + layername)

                    newOutputPath = os.path.abspath(
                        os.path.join(
                            rSettings["outputName"],
                            "..",
                            filename + ext,
                        )
                    )
                    if bpy.app.version < (5, 0, 0):
                        m.base_path = newOutputPath
                    else:
                        m.directory = os.path.dirname(newOutputPath)
                        m.file_name = os.path.basename(newOutputPath)

                    if connections:
                        usePasses = True
                else:
                    if bpy.app.version < (5, 0, 0):
                        m.base_path = os.path.dirname(rSettings["outputName"])
                    else:
                        layername = ""
                        if len(outNodes) > 1:
                            layername = m.label or m.name

                        if bpy.app.version < (5, 1, 0) or True:
                            m.directory = os.path.dirname(os.path.dirname(rSettings["outputName"])) + "/" + (layername or "beauty")
                            m.file_name = os.path.splitext(os.path.basename(rSettings["outputName"]))[0].replace("beauty", layername).strip("#._") + "."
                        # else:
                            # m.directory = os.path.dirname(rSettings["outputName"])
                            # m.file_name = os.path.basename(rSettings["outputName"]).replace("beauty", layername)

                    for i, idx in connections:
                        passName = i.from_socket.name
                        layername = ""
                        if i.from_node.type == "R_LAYERS":
                            if len(rlayerNodes) > 1:
                                layername = i.from_node.layer
                                passName = "%s_%s" % (layername, passName)

                        else:
                            if hasattr(i.from_node, "label") and i.from_node.label != "":
                                passName = i.from_node.label

                        if hasattr(m, "file_slots"):  # removed in Blender 5.0
                            curSlot = m.file_slots[idx]
                            useNodeFormat = curSlot.use_node_format
                        else:
                            curSlot = m.file_output_items[idx]
                            useNodeFormat = not curSlot.override_node_format

                        if useNodeFormat:
                            ext = nodeExt
                        else:
                            ext = extensions[curSlot.format.file_format]

                        filename = os.path.splitext(os.path.basename(rSettings["outputName"]))[
                            0
                        ]
                        if len(outNodes) > 1:
                            layername = m.label or layername
                            if not layername:
                                layername = m.name

                        if layername:
                            filename = filename.replace("beauty", passName + "_" + layername)
                        else:
                            filename = filename.replace("beauty", passName)

                        if bpy.app.version < (5, 0, 0):
                            curSlot.path = "../%s/%s" % (
                                passName, filename + ext
                            )

                            newOutputPath = os.path.abspath(
                                os.path.join(
                                    rSettings["outputName"],
                                    "../..",
                                    passName,
                                    filename + ext,
                                )
                            )
                        else:
                            if bpy.app.version < (5, 1, 0) or True:
                                newOutputPath = m.directory + "/" + m.file_name + passName + ext
                            # else:
                            #     curSlot.file_name = "../%s/%s" % (
                            #         passName, filename + ext
                            #     )

                            #     newOutputPath = os.path.abspath(
                            #         os.path.join(
                            #             rSettings["outputName"],
                            #             "../..",
                            #             passName,
                            #             filename + ext,
                            #         )
                            #     )

                        usePasses = True

        if usePasses:
            rSettings["outputName"] = newOutputPath
            if platform.system() == "Windows":
                tmpOutput = os.path.join(
                    os.path.dirname(self.core.getTempFilepath()), "PrismRender", "tmp.####" + imgFormat
                )
                bpy.context.scene.render.filepath = tmpOutput
                if not os.path.exists(os.path.dirname(tmpOutput)):
                    os.makedirs(os.path.dirname(tmpOutput))

    @err_catcher(name=__name__)
    def sm_render_startLocalRender(self, origin: Any, outputName: str, rSettings: Dict) -> str:
        """Start local render.
        
        Args:
            origin: Render state instance.
            outputName: Output file path.
            rSettings: Render settings dictionary.
        
        Returns:
            Result message string.
        """
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
                        try:
                            bpy.ops.render.render(
                                "INVOKE_DEFAULT",
                                animation=not singleFrame,
                                write_still=singleFrame,
                            )
                        except RuntimeError as e:
                            if "No Group Output or File Output nodes in scene" in str(e):
                                if hasattr(origin, "waitmsg") and origin.waitmsg.isVisible():
                                    origin.waitmsg.close()

                                return "Execute Canceled: %s" % str(e)
                            else:
                                raise e
                
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
    def checkRenderFinished(self, origin: Any) -> None:
        """Check if render has finished.
        
        Args:
            origin: Render state instance.
        """
        if not bpy.context.scene.get("PrismIsRendering"):
            origin.stateManager.publish(continuePublish=True)
            return

        self.startRenderThread(origin)

    @err_catcher(name=__name__)
    def startRenderThread(self, origin: Any) -> None:
        """Start render checking thread.
        
        Args:
            origin: Render state instance.
        """
        if hasattr(self, "checkIsRenderingTimer") and self.checkIsRenderingTimer.isActive():
            self.checkIsRenderingTimer.stop()

        self.checkIsRenderingTimer = QTimer()
        self.checkIsRenderingTimer.setSingleShot(True)
        self.checkIsRenderingTimer.timeout.connect(lambda: self.checkRenderFinished(origin))
        self.checkIsRenderingTimer.start(1000)

    @err_catcher(name=__name__)
    def sm_render_undoRenderSettings(self, origin: Any, rSettings: Dict) -> None:
        """Restore original render settings.
        
        Args:
            origin: Render state instance.
            rSettings: Render settings dictionary with original values.
        """
        if "width" in rSettings:
            bpy.context.scene.render.resolution_x = rSettings["width"]
        if "height" in rSettings:
            bpy.context.scene.render.resolution_y = rSettings["height"]
        if "prev_start" in rSettings:
            bpy.context.scene.frame_start = rSettings["prev_start"]
        if "prev_end" in rSettings:
            bpy.context.scene.frame_end = rSettings["prev_end"]
        if "mediaType" in rSettings:
            bpy.context.scene.render.image_settings.media_type = rSettings[
                "mediaType"
            ]
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

        # if platform.system() == "Windows":
        #     tmpOutput = os.path.join(os.path.dirname(self.core.getTempFilepath()), "PrismRender")
        #     if os.path.exists(tmpOutput):
        #         try:
        #             shutil.rmtree(tmpOutput)
        #         except:
        #             pass

        bDir = os.path.dirname(rSettings.get("origOutputName", ""))
        if os.path.exists(bDir) and len(os.listdir(bDir)) == 0:
            try:
                shutil.rmtree(bDir)
            except:
                pass

            origin.l_pathLast.setText(rSettings["outputName"])
            origin.l_pathLast.setToolTip(rSettings["outputName"])
            origin.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def sm_render_getDeadlineParams(self, origin: Any, dlParams: Dict, homeDir: str) -> None:
        """Get Deadline render farm submission parameters.
        
        Modifies dlParams dictionary in place.
        
        Args:
            origin: Render state instance.
            dlParams: Deadline parameters dictionary.
            homeDir: Home directory path.
        """
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
    def getCurrentRenderer(self, origin: Any) -> str:
        """Get current render engine name.
        
        Args:
            origin: Originating object.
        
        Returns:
            Renderer name.
        """
        return bpy.context.window_manager.windows[0].scene.render.engine

    @err_catcher(name=__name__)
    def getCurrentSceneFiles(self, origin: Any) -> List[str]:
        """Get list of current scene files.
        
        Args:
            origin: Originating object.
        
        Returns:
            List containing current scene file path.
        """
        return [self.core.getCurrentFileName()]

    @err_catcher(name=__name__)
    def sm_render_getRenderPasses(self, origin: Any) -> List[str]:
        """Get list of available render passes.
        
        Args:
            origin: Render state instance.
        
        Returns:
            List of available pass names.
        """
        aovNames = [
            x["name"]
            for x in self.getAvailableAOVs()
            if x["name"] not in self.getViewLayerAOVs()
        ]
        return aovNames

    @err_catcher(name=__name__)
    def sm_render_addRenderPass(self, origin: Any, passName: str, steps: Optional[List] = None) -> None:
        """Add render pass.
        
        Args:
            origin: Render state instance.
            passName: Pass name to add.
            steps: UI steps list. Defaults to None.
        """
        self.enableViewLayerAOV(passName)

    @err_catcher(name=__name__)
    def sm_render_managerChanged(self, origin: Any, isPandora: bool) -> None:
        """Handle render manager change (not implemented for Blender).
        
        Args:
            origin: Render state instance.
            isPandora: Whether Pandora is selected.
        """
        pass

    @err_catcher(name=__name__)
    def sm_render_preExecute(self, origin: Any) -> List:
        """Pre-execution checks for render state.
        
        Args:
            origin: Render state instance.
        
        Returns:
            List of warning messages.
        """
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def sm_render_fixOutputPath(self, origin: Any, outputName: str, singleFrame: bool = False, state: Optional[Any] = None) -> str:
        """Fix output path format for rendering.
        
        Args:
            origin: Originating object.
            outputName: Original output name.
            singleFrame: Whether single frame render. Defaults to False.
            state: Render state object. Defaults to None.
        
        Returns:
            Fixed output path.
        """
        if (not singleFrame) or self.useNodeAOVs() or (state and not state.gb_submit.isHidden() and state.gb_submit.isChecked()):
            outputName = (
                os.path.splitext(outputName)[0].rstrip("#.")
                + "." + "#"*self.core.framePadding
                + os.path.splitext(outputName)[1]
            )
        return outputName

    @err_catcher(name=__name__)
    def sm_render_submitScene(self, origin: Any, jobPath: str) -> None:
        """Submit scene for rendering.
        
        Args:
            origin: Render state instance.
            jobPath: Job submission path.
        """
        jobFilePath = os.path.join(jobPath, self.core.getCurrentFileName(path=False))
        bpy.ops.wm.save_as_mainfile(filepath=jobFilePath, copy=True)
        try:
            bpy.ops.wm.revert_mainfile()
        except Exception as e:
            self.core.popup("Warning: Couldn't revert to original file after saving selection to new blend file. Error:\n\n%s" % str(e))

        self.core.stateManager()

    @err_catcher(name=__name__)
    def deleteNodes(self, origin: Any, handles: List) -> None:
        """Delete nodes from scene.
        
        Args:
            origin: Originating object.
            handles: List of node handles to delete.
        """
        for handle in handles:
            obj = self.getObject(handle)
            if obj.bl_rna.identifier.upper() == "COLLECTION":
                bpy.data.collections.remove(obj)
            else:
                bpy.data.objects.remove(obj)

    #   bpy.ops.object.select_all(self.getOverrideContext(origin), action='DESELECT')
    #   for i in handles:
    #       self.selectObject(bpy.data.objects[i])
    #   bpy.ops.object.make_local(self.getOverrideContext(origin), type='SELECT_OBDATA_MATERIAL')
    #   bpy.ops.object.delete(self.getOverrideContext(origin))

    @err_catcher(name=__name__)
    def sm_import_startup(self, origin: Any) -> None:
        """Initialize import state UI.
        
        Args:
            origin: Import state instance.
        """
        origin.f_abcPath.setVisible(True)

    @err_catcher(name=__name__)
    def importAlembic(self, importPath: str, origin: Optional[Any] = None) -> Any:
        """Import Alembic file.
        
        Args:
            importPath: Path to Alembic file.
            origin: Import state instance. Defaults to None.
        
        Returns:
            True if successful.
        """
        if origin and origin.chb_abcPath.isChecked() and len(origin.nodes) > 0:
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
    def importFBX(self, importPath: str, origin: Optional[Any] = None) -> None:
        """Import FBX file.
        
        Args:
            importPath: Path to FBX file.
            origin: Import state instance. Defaults to None.
        """
        if bpy.app.version < (4, 0, 0):
            bpy.ops.import_scene.fbx(self.getOverrideContext(origin), filepath=importPath)
        else:
            with bpy.context.temp_override(**self.getOverrideContext(origin)):
                bpy.ops.import_scene.fbx(filepath=importPath)

    @err_catcher(name=__name__)
    def importObj(self, importPath: str, origin: Optional[Any] = None) -> None:
        """Import OBJ file.
        
        Args:
            importPath: Path to OBJ file.
            origin: Import state instance. Defaults to None.
        """
        if bpy.app.version < (4, 0, 0):
            bpy.ops.import_scene.obj(self.getOverrideContext(origin), filepath=importPath)
        else:
            with bpy.context.temp_override(**self.getOverrideContext(origin)):
                bpy.ops.wm.obj_import(filepath=importPath)

    @err_catcher(name=__name__)
    def importGlb(self, importPath: str, origin: Optional[Any] = None) -> None:
        """Import GLB file.
        
        Args:
            importPath: Path to GLB file.
            origin: Import state instance. Defaults to None.
        """
        with bpy.context.temp_override(**self.getOverrideContext(origin)):
            bpy.ops.import_scene.gltf(filepath=importPath)

    @err_catcher(name=__name__)
    def importUsd(self, filepath: str, origin: Optional[Any] = None) -> Any:
        """Import USD file.
        
        Args:
            filepath: Path to USD file.
            origin: Import state instance. Defaults to None.
        
        Returns:
            False if USD not supported, otherwise None.
        """
        from _bpy import ops as _ops_module
        if bpy.app.version < (5, 1, 0):
            try:
                _ops_module.as_string("WM_OT_usd_import")
                valid = True
            except:
                valid = False
        else:
            valid = "WM_OT_usd_import" in _ops_module.dir()

        if not valid:
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
    def importFile(self, importPath: str) -> Any:
        """Import file using appropriate handler.
        
        Args:
            importPath: Path to file to import.
        
        Returns:
            Result from import handler.
        """
        if not importPath:
            return

        base, ext = os.path.splitext(importPath)
        ext = ext.lower()
        if ext in self.importHandlers:
            return self.importHandlers[ext]["importFunction"](importPath)

    @err_catcher(name=__name__)
    def sm_import_importToApp(self, origin: Any, doImport: bool, update: bool, impFileName: str) -> Optional[Dict]:
        """Import file into Blender.
        
        Args:
            origin: Import state instance.
            doImport: Whether to proceed with import.
            update: Whether this is an update operation.
            impFileName: Path to file to import.
        
        Returns:
            Dictionary with  result and doImport status, or None if cancelled.
        """
        if bpy.app.is_job_running("RENDER"):
            self.core.popup("Unable to import file while rendering.")
            return

        fileName = os.path.splitext(os.path.basename(impFileName))
        result = False

        ext = fileName[1].lower()
        importedNodes = None
        if ext in [".blend"]:
            prevSceneContent = list(bpy.data.scenes[0].collection.objects) + list(bpy.data.scenes[0].collection.children)
            origin.setName = ""
            dlg_sceneData = widget_import_scenedata.Import_SceneData(
                self.core, self.plugin
            )
            dlgResult = dlg_sceneData.importScene(impFileName, update, origin)
            if not dlgResult or not dlgResult.get("result"):
                return

            if dlg_sceneData.updated:
                result = True

            if dlgResult.get("mode") == "link":
                importedNodes = dlgResult.get("importedNodes")

            existingNodes = dlg_sceneData.existingNodes
        else:
            if not (ext == ".abc" and origin.chb_abcPath.isChecked()):
                origin.preDelete(
                    baseText="Do you want to delete the currently connected objects?\n\n"
                )
            existingNodes = list(bpy.data.objects) + list(bpy.data.collections)
            prevSceneContent = list(bpy.data.scenes[0].collection.objects) + list(bpy.data.scenes[0].collection.children)
            origin.setName = ""

            if ext in self.importHandlers:
                result = self.importHandlers[ext]["importFunction"](impFileName, origin)
            else:
                self.core.popup("Format is not supported.")
                return {"result": False, "doImport": doImport}

        if not result:
            if importedNodes is None:
                importedNodes = self.getImportedNodes(existingNodes, prevSceneContent)

            origin.setName = "Import_" + fileName[0]
            extension = 1
            while origin.setName in self.getGroups() and extension < 999:
                if "%s_%s" % (origin.setName, extension) not in self.getGroups():
                    origin.setName += "_%s" % extension
                extension += 1

            if origin.chb_trackObjects.isChecked():
                origin.nodes = importedNodes

            if len(origin.nodes) > 0:
                self.deselectObjects()
                self.createGroups(name=origin.setName)

                for node in origin.nodes:
                    obj = self.getObject(node)
                    if obj.bl_rna.identifier.upper() == "COLLECTION":
                        children = self.getGroups()[origin.setName].children
                        if obj not in list(children):
                            children.link(obj)

                for node in origin.nodes:
                    obj = self.getObject(node)
                    if obj.bl_rna.identifier.upper() != "COLLECTION":
                        collection = self.getGroups()[origin.setName]
                        colls = [collection] + collection.children_recursive
                        curObjs = []
                        for col in colls:
                            curObjs += list(col.objects)

                        if obj and obj not in curObjs:
                            collection.objects.link(obj)

            self.deselectObjects()
            objs = [self.getObject(x) for x in importedNodes]
            self.selectObjects(objs, quiet=True)

            result = len(importedNodes) > 0
            if not result and ext in [".blend"]:
                if impFileName in [lib.filepath for lib in bpy.data.libraries]:
                    result = True
                    self.core.popup("The library \"%s\" is already linked into the current scenefile.\nTo link the same object multiple times, create an Library Override on the existing objects first." % impFileName)

        return {"result": result, "doImport": doImport}

    @err_catcher(name=__name__)
    def getImportedNodes(self, existingNodes: List, prevSceneContent: List) -> List:
        """Get list of newly imported nodes.
        
        Args:
            existingNodes: List of nodes before import.
            prevSceneContent: Scene content before import.
        
        Returns:
            List of imported node handles.
        """
        importedNodes = []
        for obj in bpy.data.objects:
            if obj not in existingNodes:
                importedNodes.append(self.getNode(obj))

        for col in bpy.data.collections:
            if col not in existingNodes:
                importedNodes.append(self.getNode(col))

        if not importedNodes:
            for obj in bpy.data.scenes[0].collection.objects:
                if obj not in prevSceneContent:
                    importedNodes.append(self.getNode(obj))

            for col in bpy.data.scenes[0].collection.children:
                if col not in prevSceneContent:
                    importedNodes.append(self.getNode(col))

        return importedNodes

    @err_catcher(name=__name__)
    def createOverride(self, obj: Any) -> None:
        """Create library override for object.
        
        Args:
            obj: Object or collection to create override for.
        """
        node = self.getNode(obj)
        ctx = self.getOverrideContext()
        if bpy.app.version >= (2, 80, 0):
            ctx.pop("screen")
            ctx.pop("area")

        if bpy.context.mode != 'OBJECT':
            if bpy.app.version < (4, 0, 0):
                try:
                    bpy.ops.object.mode_set(ctx, mode="OBJECT")
                except:
                    pass
            else:
                with bpy.context.temp_override(**ctx):
                    if bpy.context.object:
                        try:
                            bpy.ops.object.mode_set(mode="OBJECT")
                        except:
                            pass

        if obj.bl_rna.identifier.upper() == "COLLECTION":
            if obj and obj.library:
                bpy.context.view_layer.objects.active = None
                self.deselectObjects()
                for lobj in obj.objects:
                    lobj.select_set(True)

                if bpy.app.version < (4, 0, 0):
                    bpy.ops.object.make_override_library(ctx, collection=obj)
                else:
                    with bpy.context.temp_override(**ctx):
                        bpy.ops.object.make_override_library(collection=obj)
        else:
            if obj and obj.library:
                bpy.context.view_layer.objects.link(obj)
                bpy.context.view_layer.objects.active = obj
                obj.select_set(True)

            if bpy.app.version < (4, 0, 0):
                result = bpy.ops.object.make_override_library(ctx)
            else:
                with bpy.context.temp_override(**ctx):
                    result = bpy.ops.object.make_override_library()

            self.core.popup(result)

        obj = self.getObject(node)
        # self.core.popup(obj)
        obj.override_library.is_system_override = False

    @err_catcher(name=__name__)
    def getNode(self, obj: Any) -> Dict:
        """Get node dictionary from object.
        
        Args:
            obj: Blender object or string name.
        
        Returns:
            Node dictionary with name and library path.
        """
        if type(obj) == str:
            node = {"name": obj, "library": ""}
        else:
            lib = obj.library
            if not lib and obj.override_library and obj.override_library.reference:
                lib = obj.override_library.reference.library

            libpath = getattr(lib, "filepath", "")
            node = {"name": obj.name, "library": libpath}
        return node

    @err_catcher(name=__name__)
    def getObject(self, node: Any) -> Optional[Any]:
        """Get Blender object from node.
        
        Args:
            node: Node dictionary or string name.
        
        Returns:
            Blender object or collection, or None if not found.
        """
        if type(node) == str:
            node = self.getNode(node)

        for obj in bpy.data.objects:
            libMatch = getattr(obj.library, "filepath", "") == node["library"]
            overrideMatch = obj.override_library and obj.override_library.reference and getattr(obj.override_library.reference.library, "filepath", "") == node["library"]
            if (
                obj.name == node["name"]
                and (libMatch or overrideMatch)
            ):
                return obj

        for obj in bpy.data.collections:
            libMatch = getattr(obj.library, "filepath", "") == node["library"]
            overrideMatch = obj.override_library and obj.override_library.reference and getattr(obj.override_library.reference.library, "filepath", "") == node["library"]
            if (
                obj.name == node["name"]
                and (libMatch or overrideMatch)
            ):
                return obj

    @err_catcher(name=__name__)
    def isolateSelection(self) -> None:
        """Toggle selection isolation in viewport."""
        if bpy.app.version < (4, 0, 0):
            bpy.ops.view3d.localview(self.getOverrideContext(context="VIEW_3D"))
        else:
            with bpy.context.temp_override(**self.getOverrideContext(context="VIEW_3D")):
                if bpy.context.space_data.local_view:
                    bpy.ops.view3d.localview()

                bpy.ops.view3d.localview()

    @err_catcher(name=__name__)
    def onGenerateStateNameContext(self, *args: Any) -> None:
        """Callback for state name generation context.
        
        Args:
            *args: State and context arguments.
        """
        if args[0].className == "ImportFile":
            args[1]["collection"] = args[0].setName

    @err_catcher(name=__name__)
    def sm_import_disableObjectTracking(self, origin: Any) -> None:
        """Disable object tracking for import state.
        
        Removes associated collection.
        
        Args:
            origin: Import state instance.
        """
        stateGroup = [x for x in self.getGroups() if x.name == origin.setName]
        if len(stateGroup) > 0:
            self.getGroups().remove(stateGroup[0])

    @err_catcher(name=__name__)
    def sm_import_updateObjects(self, origin: Any) -> None:
        """Update imported objects list from collection.
        
        Args:
            origin: Import state instance.
        """
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

            for child in group.children:
                nodes.append(self.getNode(child))

            origin.nodes = nodes

    @err_catcher(name=__name__)
    def sm_import_removeNameSpaces(self, origin: Any) -> None:
        """Remove namespaces from imported node names.
        
        Args:
            origin: Import state instance.
        """
        for i in origin.nodes:
            if not self.getObject(i):
                continue

            nodeName = self.getNodeName(origin, i)
            newName = nodeName.rsplit(":", 1)[-1]
            if newName != nodeName and not i["library"]:
                self.getObject(i).name = newName

        origin.updateUi()

    @err_catcher(name=__name__)
    def sm_import_fixImportPath(self, filepath: str) -> str:
        """Fix import file path format.
        
        Args:
            filepath: Original file path.
        
        Returns:
            Fixed file path.
        """
        return filepath.replace("\\\\", "\\")

    @err_catcher(name=__name__)
    def sm_import_preDelete(self, origin: Any) -> None:
        """Clean up on import state deletion.
        
        Removes associated collection.
        
        Args:
            origin: Import state instance.
        """
        try:
            self.getGroups().remove(self.getGroups()[origin.setName], do_unlink=True)
        except Exception as e:
            logger.warning(e)

    @err_catcher(name=__name__)
    def sm_playblast_startup(self, origin: Any) -> None:
        """Initialize playblast state.
        
        Args:
            origin: Playblast state instance.
        """
        frange = self.getFrameRange(origin)
        origin.sp_rangeStart.setValue(frange[0])
        origin.sp_rangeEnd.setValue(frange[1])
        origin.b_resPresets.setMinimumWidth(30 * self.core.uiScaleFactor)
        origin.b_resPresets.setMinimumHeight(0)
        origin.b_resPresets.setMaximumHeight(500 * self.core.uiScaleFactor)
        origin.cb_formats.addItem(".mp4 (with audio)")

    @err_catcher(name=__name__)
    def prePlayblast(self, **kwargs: Any) -> Optional[Dict]:
        """Pre-playblast processing.
        
        Args:
            **kwargs: Playblast parameters.
        
        Returns:
            Dictionary with modified outputName if changed, otherwise None.
        """
        outputName = origOutputName = kwargs["outputpath"]
        tmpOutputName = os.path.splitext(kwargs["outputpath"])[0].rstrip("#")
        tmpOutputName = tmpOutputName.strip(".")
        selFmt = kwargs["state"].cb_formats.currentText()
        if selFmt == ".mp4 (with audio)":
            outputName = tmpOutputName + ".mp4"

        renderAnim = kwargs["startframe"] != kwargs["endframe"]
        if not renderAnim:
            outputName = (
                os.path.splitext(outputName)[0]
                + "."
                + ("%0" + str(self.core.framePadding) + "d") % kwargs["startframe"]
                + os.path.splitext(outputName)[1]
            )

        if outputName != origOutputName:
            return {"outputName": outputName}

    @err_catcher(name=__name__)
    def sm_playblast_createPlayblast(self, origin: Any, jobFrames: List, outputName: str) -> None:
        """Create playblast/viewport capture.
        
        Args:
            origin: Playblast state instance.
            jobFrames: List of [start frame, end frame].
            outputName: Output file path.
        """
        renderAnim = jobFrames[0] != jobFrames[1]
        if origin.curCam is not None:
            bpy.context.scene.camera = bpy.context.scene.objects[origin.curCam]
            for window in bpy.context.window_manager.windows:
                screen = window.screen
                for area in screen.areas:
                    if area.type == "VIEW_3D":
                        area.spaces[0].region_3d.view_perspective = "CAMERA"
                        break

        viewLayer = None
        for window in bpy.context.window_manager.windows:
            screen = window.screen
            for area in screen.areas:
                if area.type == "VIEW_3D":
                    viewLayer = window.view_layer
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
            bpy.context.scene.render.image_settings.media_type,
        ]

        bpy.context.scene.frame_start = jobFrames[0]
        bpy.context.scene.frame_end = jobFrames[1]

        if origin.chb_resOverride.isChecked():
            bpy.context.scene.render.resolution_x = origin.sp_resWidth.value()
            bpy.context.scene.render.resolution_y = origin.sp_resHeight.value()
            bpy.context.scene.render.resolution_percentage = 100

        bpy.context.scene.render.filepath = os.path.normpath(outputName)
        base, ext = os.path.splitext(outputName)
        if ext == ".jpg":
            bpy.context.scene.render.image_settings.media_type = "IMAGE"
            bpy.context.scene.render.image_settings.file_format = "JPEG"
        if ext == ".mp4":
            bpy.context.scene.render.image_settings.media_type = "VIDEO"
            bpy.context.scene.render.image_settings.file_format = "FFMPEG"
            bpy.context.scene.render.ffmpeg.format = "MPEG4"
            bpy.context.scene.render.ffmpeg.audio_codec = "MP3"
            renderAnim = True
   
        ctx = self.core.appPlugin.getOverrideContext(origin)
        if viewLayer:
            ctx['view_layer'] = viewLayer

        if bpy.app.version < (4, 0, 0):
            bpy.ops.render.opengl(
                ctx, animation=renderAnim, write_still=True, view_context=True)
        else:
            with bpy.context.temp_override(**ctx):
                bpy.ops.render.opengl(animation=renderAnim, write_still=True, view_context=True)

        bpy.context.scene.frame_start = prevRange[0]
        bpy.context.scene.frame_end = prevRange[1]
        bpy.context.scene.render.resolution_x = prevRes[0]
        bpy.context.scene.render.resolution_y = prevRes[1]
        bpy.context.scene.render.resolution_percentage = prevRes[2]
        bpy.context.scene.render.filepath = prevOutput[0]
        bpy.context.scene.render.image_settings.media_type = prevOutput[2]
        bpy.context.scene.render.image_settings.file_format = prevOutput[1]

    @err_catcher(name=__name__)
    def sm_playblast_preExecute(self, origin: Any) -> List:
        """Pre-execution checks for playblast state.
        
        Args:
            origin: Playblast state instance.
        
        Returns:
            List of warning messages.
        """
        warnings = []

        return warnings

    @err_catcher(name=__name__)
    def sm_playblast_execute(self, origin: Any) -> None:
        """Execute playblast state (not implemented).
        
        Args:
            origin: Playblast state instance.
        """
        pass

    @err_catcher(name=__name__)
    def captureViewportThumbnail(self) -> Optional[Any]:
        """Capture current viewport as thumbnail image.
        
        Returns:
            QPixmap of viewport capture or None if in background mode.
        """
        if bpy.app.background:
            return

        path = tempfile.NamedTemporaryFile(suffix=".jpg").name
        while True:
            try:
                if bpy.app.version < (4, 0, 0):
                    bpy.ops.screen.screenshot(self.getOverrideContext(), filepath=path)
                else:
                    with bpy.context.temp_override(**self.getOverrideContext()):
                        bpy.ops.screen.screenshot(filepath=path)

                break
            except Exception as e:
                msg = "Error capturing viewport thumbnail:\n\n%s" % str(e)
                result = self.core.popupQuestion(msg, buttons=["Retry", "Cancel"], default="Cancel", escapeButton="Cancel", icon=QMessageBox.Warning)
                if result == "Cancel":
                    return

        pm = self.core.media.getPixmapFromPath(path)
        try:
            os.remove(path)
        except:
            pass

        return pm

    @err_catcher(name=__name__)
    def sm_setActivePalette(self, origin: Any, listWidget: Any, inactive: Any, inactivef: Any, activef: Any) -> None:
        """Set active palette styling for list widgets.
        
        Args:
            origin: Originating object.
            listWidget: Active list widget.
            inactive: Inactive list widget.
            inactivef: Unused parameter.
            activef: Unused parameter.
        """
        listWidget.setStyleSheet("QTreeWidget { border: 1px solid rgb(30,130,230); }")
        inactive.setStyleSheet("QTreeWidget { border: 1px solid rgb(30,30,30); }")

    @err_catcher(name=__name__)
    def onStateManagerOpen(self, origin: Any) -> None:
        """Callback when State Manager opens.
        
        Adjusts button sizes and styles.
        
        Args:
            origin: State Manager instance.
        """
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
    def sm_saveStates(self, origin: Any, buf: str) -> None:
        """Save State Manager states to scene.
        
        Args:
            origin: State Manager instance.
            buf: Serialized state data.
        """
        try:
            bpy.context.scene["PrismStates"] = buf
        except Exception as e:
            logger.debug("failed to save states: %s" % str(e))

    @err_catcher(name=__name__)
    def sm_saveImports(self, origin: Any, importPaths: str) -> None:
        """Save import paths to scene.
        
        Args:
            origin: State Manager instance.
            importPaths: Serialized import paths string.
        """
        try:
            bpy.context.scene["PrismImports"] = importPaths.replace("\\\\", "\\")
        except Exception as e:
            logger.debug("failed to save imports: %s" % str(e))

    @err_catcher(name=__name__)
    def sm_readStates(self, origin: Any) -> Optional[str]:
        """Read State Manager states from scene.
        
        Args:
            origin: State Manager instance.
        
        Returns:
            Serialized state data or None if not found.
        """
        if "PrismStates" in bpy.context.scene:
            return bpy.context.scene["PrismStates"]

    @err_catcher(name=__name__)
    def sm_deleteStates(self, origin: Any) -> None:
        """Delete State Manager states from scene.
        
        Args:
            origin: State Manager instance.
        """
        if "PrismStates" in bpy.context.scene:
            del bpy.context.scene["PrismStates"]

    @err_catcher(name=__name__)
    def sm_getExternalFiles(self, origin: Any) -> List:
        """Get list of external files referenced in scene.
        
        Args:
            origin: State Manager instance.
        
        Returns:
            Empty lists (not implemented for Blender).
        """
        return [[], []]

    @err_catcher(name=__name__)
    def sm_createRenderPressed(self, origin: Any) -> None:
        """Handle create render button press.
        
        Args:
            origin: State Manager instance.
        """
        origin.createPressed("Render")

    @err_catcher(name=__name__)
    def onStateCreated(self, origin: Any, state: Any, stateData: Optional[Dict]) -> None:
        """Callback when state is created.
        
        Adds Blender-specific settings to states.
        
        Args:
            origin: State Manager instance.
            state: Created state instance.
            stateData: State data dictionary. Defaults to None.
        """
        if state.className == "ImageRender":
            state.b_resPresets.setStyleSheet("padding-left: 1px;padding-right: 1px;")
        elif state.className == "Playblast":
            state.b_resPresets.setStyleSheet("padding-left: 1px;padding-right: 1px;")

        if state.className in ["Export"]:
            abcSettings = []
            additionalSettingsValues = (stateData or {}).get("additionalSettings") or {}
            abcSettings += [
                {
                    "name": "abcScale",
                    "label": "Scale",
                    "type": "float",
                    "value": 1.0 if "abcScale" not in additionalSettingsValues else additionalSettingsValues["abcScale"],
                    "visible": lambda dlg, state: state.getOutputType() in [".abc"]
                }
            ]

            state.additionalSettings += abcSettings
