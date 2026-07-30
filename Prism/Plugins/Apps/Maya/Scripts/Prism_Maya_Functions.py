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
import shutil
import platform
import logging
import tempfile
import copy
import fnmatch

import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMaya as api
import maya.OpenMayaUI as OpenMayaUI

try:
    import mtoa.aovs as maovs
except:
    pass

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from typing import Any, Dict, List, Optional, Tuple, Union

from PrismUtils.Decorators import err_catcher as err_catcher


logger = logging.getLogger(__name__)


class Prism_Maya_Functions(object):
    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize Maya functions and register callbacks.
        
        Args:
            core: Prism core instance
            plugin: Plugin instance
        """
        self.core = core
        self.plugin = plugin
        self.importHandlers = {}
        self.assetsInScene = None
        self.core.registerCallback(
            "onProjectBrowserStartup", self.onProjectBrowserStartup, plugin=self.plugin
        )
        self.core.registerCallback(
            "onStateManagerOpen", self.onStateManagerOpen, plugin=self.plugin
        )
        self.core.registerCallback(
            "onProjectChanged", self.onProjectChanged, plugin=self.plugin
        )
        self.core.registerCallback(
            "prePlayblast", self.prePlayblast, plugin=self.plugin
        )
        self.core.registerCallback(
            "preExport", self.preExport, plugin=self.plugin
        )
        self.core.registerCallback(
            "onStateCreated", self.onStateCreated, plugin=self.plugin
        )
        self.core.registerCallback(
            "updatedEnvironmentVars", self.updatedEnvironmentVars, plugin=self.plugin
        )
        self.core.registerCallback(
            "onGenerateStateNameContext", self.onGenerateStateNameContext, plugin=self.plugin
        )
        self.core.registerCallback("postBuildScene", self.postBuildScene, plugin=self.plugin)
        self.core.registerCallback("sm_export_updateUi", self.sm_export_updateUi, plugin=self.plugin)
        if "OCIO" in [item["key"] for item in self.core.users.getUserEnvironment()]:
            self.refreshOcio()

        os.environ["PRISM_PRODUCT_BROWSER_ADD_GL_DUMMY"] = "0"
        self.batchExportDlg = BatchExportDlg

    @err_catcher(name=__name__)
    def startup(self, origin: Any) -> Optional[bool]:
        """Initialize Maya plugin at startup.
        
        Args:
            origin: Prism core instance
            
        Returns:
            False if initialization failed, None on success
        """
        if self.core.uiAvailable:
            if QApplication.instance() is None:
                return False

            if not hasattr(QApplication, "topLevelWidgets"):
                return False

            for obj in QApplication.topLevelWidgets():
                if obj.objectName() == "MayaWindow":
                    mayaQtParent = obj
                    break
            else:
                return False

            try:
                topLevelShelf = mel.eval("string $m = $gShelfTopLevel")
            except:
                return False

            if not topLevelShelf:
                return False

            if (
                cmds.shelfTabLayout(topLevelShelf, query=True, tabLabelIndex=True)
                is None
            ):
                return False

            origin.timer.stop()

            if platform.system() == "Darwin":
                origin.messageParent = QWidget()
                origin.messageParent.setParent(mayaQtParent, Qt.Window)
                if self.core.useOnTop:
                    origin.messageParent.setWindowFlags(
                        origin.messageParent.windowFlags() ^ Qt.WindowStaysOnTopHint
                    )
            else:
                origin.messageParent = mayaQtParent

            self.addMenu()
            origin.startAutosaveTimer()
        else:
            origin.messageParent = QWidget()

        cmds.loadPlugin("AbcExport.mll", quiet=True)
        cmds.loadPlugin("AbcImport.mll", quiet=True)
        try:
            cmds.loadPlugin("fbxmaya.mll", quiet=True)
        except Exception as e:
            logger.warning("failed to load fbxmaya.mll: %s" % str(e))

        api.MSceneMessage.addCallback(api.MSceneMessage.kAfterOpen, origin.sceneOpen)

    @err_catcher(name=__name__)
    def addMenu(self) -> None:
        """Create Prism menu in Maya\'s menu bar."""
        if cmds.about(batch=True):
            return

        # destroy any pre-existing shotgun menu - the one that holds the apps
        if cmds.menu("PrismMenu", exists=True):
            cmds.deleteUI("PrismMenu")

        # create a new shotgun disabled menu if one doesn't exist already.
        if not cmds.menu("PrismMenu", exists=True):
            prism_menu = cmds.menu(
                "PrismMenu",
                label="Prism",
                parent=mel.eval("$retvalue = $gMainWindow;"),
            )
            cmds.menuItem(
                label="Save Version",
                annotation="Saves the current file to a new version",
                parent=prism_menu,
                command=lambda x: self.core.saveScene(),
            )
            cmds.menuItem(
                label="Save with Comment...",
                annotation="Saves the current file to a new version with a comment",
                parent=prism_menu,
                command=lambda x: self.core.saveWithComment(),
            )
            cmds.menuItem(
                label="Project Browser...",
                annotation="Opens the Project Browser",
                parent=prism_menu,
                command=lambda x: self.core.projectBrowser(),
            )
            cmds.menuItem(
                label="State Manager...",
                annotation="Opens the State Manager",
                parent=prism_menu,
                command=lambda x: self.core.stateManager(),
            )
            cmds.menuItem(
                label="Settings...",
                annotation="Opens the Prism Settings",
                parent=prism_menu,
                command=lambda x: self.core.prismSettings(),
            )

            if os.getenv("PRISM_MAYA_LAYOUT_TOOLS", "1") == "1":
                layoutMenu = cmds.menuItem(subMenu=True, label="Layout")
                cmds.menuItem(
                    label="Create Shots in Sequencer...",
                    annotation="Create Shots in Sequencer...",
                    parent=layoutMenu,
                    command=lambda x: self.layoutCreateShots(),
                )
                cmds.menuItem(
                    label="Duplicate Selected Shot...",
                    annotation="Duplicate Selected Shot...",
                    parent=layoutMenu,
                    command=lambda x: self.layoutDuplicateShot(),
                )
                cmds.menuItem(
                    label="Extend Selected Shot...",
                    annotation="Extend Selected Shot...",
                    parent=layoutMenu,
                    command=lambda x: self.layoutExtendShot(),
                )
                cmds.menuItem(
                    label="Split Shots...",
                    annotation="Split Shots",
                    parent=layoutMenu,
                    command=lambda x: self.layoutSplitShot(),
                )
                cmds.setParent("..", menu=True)

            self.core.callback(name="onMayaMenuCreated", args=[self, prism_menu])

    @err_catcher(name=__name__)
    def layoutCreateShots(self) -> None:
        """Create shots from camera sequencer layout."""
        def get_maya_window():
            """Get Maya's main window for parenting the UI."""
            from maya import OpenMayaUI as omui
            try:
                from shiboken6 import wrapInstance
            except:
                from shiboken2 import wrapInstance

            ptr = omui.MQtUtil.mainWindow()
            return wrapInstance(int(ptr), QMainWindow)

        class ShotCreator(QDialog):
            """UI for creating multiple sequential shots with cameras in Maya's Camera Sequencer."""
            def __init__(self, parent=get_maya_window()):
                """Initialize shot creator dialog.
                
                Args:
                    parent: Parent Maya window
                """
                super(ShotCreator, self).__init__(parent)
                self.setWindowTitle("Shot Creator")
                self.setMinimumWidth(300)

                # --- Widgets ---
                self.numShotsSpin = QSpinBox()
                self.numShotsSpin.setMinimum(1)
                self.numShotsSpin.setMaximum(999)
                self.numShotsSpin.setValue(5)

                self.framesPerShotSpin = QSpinBox()
                self.framesPerShotSpin.setMinimum(1)
                self.framesPerShotSpin.setMaximum(10000)
                self.framesPerShotSpin.setValue(100)

                self.bufferFramesSpin = QSpinBox()
                self.bufferFramesSpin.setMinimum(0)
                self.bufferFramesSpin.setMaximum(10000)
                self.bufferFramesSpin.setValue(10)

                okBtn = QPushButton("OK")
                okBtn.clicked.connect(self.create_shots)

                # --- Layout ---
                formLayout = QFormLayout()
                formLayout.addRow("Number of Shots:", self.numShotsSpin)
                formLayout.addRow("Frames per Shot:", self.framesPerShotSpin)
                formLayout.addRow("Buffer Frames:", self.bufferFramesSpin)

                mainLayout = QVBoxLayout(self)
                mainLayout.addLayout(formLayout)
                mainLayout.addWidget(okBtn)

            def create_camera_group(self):
                """Create or get the 'All_Cameras' group"""
                if cmds.objExists("All_Cameras"):
                    return "All_Cameras"
                else:
                    return cmds.group(empty=True, name="All_Cameras")

            def configure_camera_settings(self, camera_shape):
                """Configure camera settings with specified parameters"""
                # Set camera aperture (36mm x 24mm)
                # cmds.setAttr("%s.horizontalFilmAperture" % camera_shape, 1.41732)  # 36mm in inches
                # cmds.setAttr("%s.verticalFilmAperture" % camera_shape, 0.94488)    # 24mm in inches

                # Set film aspect ratio to 1.5 (36/24 = 1.5)
                # This is automatically calculated from the aperture settings

                # Set Fit Resolution Gate to Horizontal
                # cmds.setAttr("%s.filmFit" % camera_shape, 2)  # 2 = Horizontal

                # Ensure camera is not orthographic
                # cmds.setAttr("%s.orthographic" % camera_shape, 0)

            def create_shots(self):
                """Create multiple shots with cameras in sequencer."""
                num_shots = self.numShotsSpin.value()
                frames_per_shot = self.framesPerShotSpin.value()
                buffer_frames = self.bufferFramesSpin.value()

                if not num_shots:
                    self.core.popup("Please enter a valid number of shots.")
                    return
                
                logger.info("Creating %d shots with %d frames each and %d buffer frames in between." % (num_shots, frames_per_shot, buffer_frames))

                # Create or get the camera group
                camera_group = self.create_camera_group()

                # --- Ensure sequencer exists ---
                sequencers = cmds.ls(type="sequencer")
                if not sequencers:
                    sequencer = cmds.createNode("sequencer", name="sequencer1")
                else:
                    sequencer = sequencers[0]

                track_num = 1  # Track V1

                # --- Find existing shots on this track ---
                existing_shots = cmds.ls(type="shot") or []
                track_shots = [s for s in existing_shots if cmds.getAttr("%s.track" % s) == track_num]

                if track_shots:
                    # Find last shot's timeline end and sequence end
                    last_shot = max(track_shots, key=lambda s: cmds.getAttr("%s.sequenceEndFrame" % s))
                    cumulative_start = cmds.getAttr("%s.endFrame" % last_shot) + buffer_frames + 1
                    cumulative_starts = cmds.getAttr("%s.sequenceEndFrame" % last_shot) + 1
                else:
                    cumulative_start = 1
                    cumulative_starts = 1

                # List to store all created cameras
                created_cameras = []
                increment = int(os.getenv("PRISM_SHOT_INCREMENT", "10"))
                shotPrefix = os.getenv("PRISM_SHOT_PREFIX", "sh")
                shotPadding = os.getenv("PRISM_SHOT_PADDING", "3")
                camPrefix = os.getenv("PRISM_CAMERA_PREFIX", "")
                camSuffix = os.getenv("PRISM_CAMERA_SUFFIX", "_cam")

                logger.info("Starting shot creation. Initial frame: %d, Track: V%d, Shot Prefix: %s, Shot Padding: %s, Camera Name Format: %s{shot_name}%s" % (cumulative_start, track_num, shotPrefix, shotPadding, camPrefix, camSuffix))

                for idx in range(num_shots):
                    shot_index = len(existing_shots) * increment + (idx + 1) * increment
                    shot_name = ("%s%%0" % shotPrefix + shotPadding + "d") % (shot_index)
                    cam_name = "%s%s%s" % (camPrefix, shot_name, camSuffix)

                    # Create camera if it doesn't exist
                    if not cmds.objExists(cam_name):
                        logger.info("Creating camera '%s' for shot '%s'." % (cam_name, shot_name))
                        cam_transform, cam_shape = cmds.camera(filmFit="horizontal")
                        camera = cam_name
                        cmds.rename(cam_shape, cam_name + "Shape")
                        cmds.rename(cam_transform, cam_name)

                        # Configure camera settings
                        self.configure_camera_settings(cam_shape)

                        # Add to created cameras list
                        created_cameras.append(camera)
                    else:
                        logger.info("Using existing camera '%s' for shot '%s'." % (cam_name, shot_name))
                        camera = cam_name
                        # Configure existing camera settings
                        cam_shape = cmds.listRelatives(camera, shapes=True)[0]
                        self.configure_camera_settings(cam_shape)

                    # Compute shot end frames
                    cumulative_end = cumulative_start + frames_per_shot - 1
                    cumulative_ends = cumulative_starts + frames_per_shot - 1

                    # Create shot node
                    if cmds.objExists(shot_name):
                        logger.warning("An object with name '%s' already exists. Skipping shot creation." % shot_name)
                    else:
                        shot = cmds.shot(
                            shot_name,
                            sequenceStartTime=cumulative_starts,
                            startTime=cumulative_start,
                            endTime=cumulative_end,
                            track=track_num,
                            currentCamera=camera
                        )
                        logger.info("Created shot '%s' with camera '%s' from frame %d to %d" % (shot, camera, cumulative_start, cumulative_end))

                    # Advance for next shot
                    cumulative_start = cumulative_end + buffer_frames + 1
                    cumulative_starts = cumulative_ends + 1

                # Group all created cameras
                if created_cameras:
                    # Ungroup cameras first if they're in any other group
                    for cam in created_cameras:
                        parent = cmds.listRelatives(cam, parent=True)
                        if parent and parent[0] != camera_group:
                            cmds.parent(cam, world=True)

                    # Parent cameras to the group
                    cmds.parent(created_cameras, camera_group)

                # Update timeline to include new shots
                total_frames = cumulative_end + buffer_frames
                cmds.playbackOptions(minTime=1, maxTime=total_frames)

                cmds.inViewMessage(
                    amg="<hl>%s</hl> shots added sequentially to Track V1!" % num_shots,
                    pos="topCenter", fade=True
                )

        try:
            self.shot_creator_dialog.close()
            self.shot_creator_dialog.deleteLater()
        except:
            pass

        self.shot_creator_dialog = ShotCreator()
        self.shot_creator_dialog.show()

    @err_catcher(name=__name__)
    def layoutDuplicateShot(self) -> None:
        """Duplicate selected shot in sequencer."""
        def duplicate_keys(source_start, source_end, target_start):
            """
            Duplicate all animation keyframes from source_start..source_end
            into a new range starting at target_start.
            """

            # Calculate offset between target and source
            offset = target_start - source_start
            duration = source_end - source_start

            # Get all anim curves in the scene
            anim_curves = cmds.ls(type="animCurve")
            if not anim_curves:
                cmds.warning("No animation curves found in the scene.")
                return

            for anim_curve in anim_curves:
                connections = cmds.listConnections(anim_curve, source=False, destination=True) or []
                skip_curve = False

                for c in connections:
                    node_type = cmds.nodeType(c)

                    # Skip if it's a camera shape
                    if node_type == "camera":
                        skip_curve = True
                        break

                    # Skip if it's a transform that has a camera shape child
                    if node_type == "transform":
                        children = cmds.listRelatives(c, children=True, type="camera") or []
                        if children:
                            skip_curve = True
                            break

                if skip_curve:
                    continue  # skip this curve

                # Find keys inside source range
                keys = cmds.keyframe(
                    anim_curve,
                    query=True,
                    time=(source_start, source_end)
                )
                if not keys:
                    continue

                # Duplicate each key with offset
                for key_time in keys:
                    # Get key value
                    value = cmds.keyframe(anim_curve, query=True, time=(key_time,), valueChange=True)[0]
                    # Compute new time
                    new_time = key_time + offset
                    # Insert new key
                    cmds.setKeyframe(anim_curve, time=new_time, value=value)

        def copy_camera_keys(source_cam, source_start, source_end, target_cam, target_start):
            """
            Copy keyframes from source_cam (source_start..source_end)
            to target_cam (target_start..target_start + duration).
            """

            # Validate cameras
            if not cmds.objExists(source_cam):
                cmds.error("Source camera '%s' does not exist." % source_cam)
                return
            if not cmds.objExists(target_cam):
                cmds.error("Target camera '%s' does not exist." % target_cam)
                return

            # Ensure we're working with transform nodes (not shapes)
            if cmds.nodeType(source_cam) == "camera":
                source_cam = cmds.listRelatives(source_cam, parent=True)[0]
            if cmds.nodeType(target_cam) == "camera":
                target_cam = cmds.listRelatives(target_cam, parent=True)[0]

            offset = target_start - source_start
            duration = source_end - source_start

            # Find animCurves connected to source camera
            anim_curves = cmds.listConnections(source_cam, type="animCurve") or []
            if not anim_curves:
                cmds.warning("No animation found on %s." % source_cam)
                return

            for anim_curve in anim_curves:
                # What attribute is this animCurve driving?
                attrs = cmds.listConnections(anim_curve, plugs=True, source=False, destination=True) or []
                for attr in attrs:
                    if attr.startswith(source_cam + "."):
                        # Extract attribute name (e.g., translateX, rotateY)
                        short_attr = attr.split(".")[-1]
                        target_attr = "%s.%s" % (target_cam, short_attr)

                        if not cmds.objExists(target_attr):
                            continue  # target doesn't have this attribute

                        # Get keys in range
                        keys = cmds.keyframe(anim_curve, query=True, time=(source_start, source_end))
                        if not keys:
                            continue

                        for key_time in keys:
                            value = cmds.keyframe(anim_curve, query=True, time=(key_time,), valueChange=True)[0]
                            new_time = key_time + offset
                            cmds.setKeyframe(target_attr, time=new_time, value=value)

        objs = cmds.ls(selection=True)
        shots = [obj for obj in objs if cmds.objectType(obj) == "shot"]
        if len(shots) != 1:
            QMessageBox.warning(None, "Duplicate Shot", "Please select exactly one shot.")
        else:
            oldShot = shots[0]
            start = cmds.shot(oldShot, q=True, startTime=True)
            end = cmds.shot(oldShot, q=True, endTime=True)
            
            newStart = end + 10
            
            dlg = QDialog()
            dlg.setWindowTitle("Duplicate Shot")
            lo = QVBoxLayout(dlg)
            w_startframe = QWidget()
            lo_startframe = QHBoxLayout(w_startframe)
            l_startframe = QLabel("Startframe:")
            sp_startframe = QSpinBox()
            sp_startframe.setRange(1, 100000)
            sp_startframe.setValue(newStart)
            lo_startframe.addWidget(l_startframe)
            lo_startframe.addWidget(sp_startframe)
            lo.addWidget(w_startframe)
            bb = QDialogButtonBox()
            bb.addButton("Duplicate", QDialogButtonBox.AcceptRole)
            bb.addButton("Cancel", QDialogButtonBox.RejectRole)
            bb.accepted.connect(dlg.accept)
            bb.rejected.connect(dlg.reject)
            lo.addWidget(bb)
            
            result = dlg.exec_()
            if result != 0:
                newShot = cmds.duplicate(oldShot)[0]
                newStart = sp_startframe.value()
                newEnd = newStart + end - start
                
                cmds.setAttr(f"{newShot}.sequenceEndFrame", newEnd)
                cmds.setAttr(f"{newShot}.sequenceStartFrame", newStart)
                cmds.setAttr(f"{newShot}.endFrame", newEnd)
                cmds.setAttr(f"{newShot}.startFrame", newStart)
                cmds.setAttr(f"{newShot}.track", 1)
                
                duplicate_keys(start, end, newStart)
                
                oldCam = cmds.shot(oldShot, q=True, currentCamera=True)
                newCam = cmds.duplicate(oldCam)[0]
                cmds.shot(newShot, e=True, currentCamera=newCam)
                cam_name = "Camera%03d" % 1
                newCam = cmds.rename(newCam, cam_name)
                cmds.shot(newShot, e=True, currentCamera=newCam)
                copy_camera_keys(oldCam, start, end, newCam, newStart)

    @err_catcher(name=__name__)
    def layoutExtendShot(self) -> None:
        """Extend selected shot duration."""
        self.dlg_extendShots = ShotExtendWindow(self.core.messageParent)
        self.dlg_extendShots.show()

    @err_catcher(name=__name__)
    def layoutSplitShot(self) -> None:
        """Split shot at current frame."""
        self.dlg_splitShots = ShotSplitWindow(self.core.messageParent, plugin=self)
        self.dlg_splitShots.show()

    @err_catcher(name=__name__)
    def autosaveEnabled(self, origin: Any) -> bool:
        """Check if autosave is enabled.
        
        Args:
            origin: Originating instance
            
        Returns:
            True if autosave enabled
        """
        return cmds.autoSave(q=True, enable=True)

    @err_catcher(name=__name__)
    def onProjectChanged(self, origin: Any) -> None:
        """Handle project change event.
        
        Args:
            origin: Prism core instance
        """
        if self.core.getConfig("maya", "setMayaProject", dft=False):
            self.setMayaProject(self.core.projectPath)

        if self.core.getConfig("maya", "addProjectPluginPaths", dft=False):
            self.addProjectPaths()

    @err_catcher(name=__name__)
    def addProjectPaths(self) -> None:
        """Add project paths to Maya search paths."""
        if not getattr(self.core, "projectPath", ""):
            return

        mayaModPath = os.path.join(
            self.core.projects.getPipelineFolder(), "CustomModules", "Maya"
        )

        pluginPath = os.path.join(mayaModPath, "plug-ins")
        scriptPath = os.path.join(mayaModPath, "scripts")
        presetPath = os.path.join(mayaModPath, "presets")
        shelfPath = os.path.join(mayaModPath, "shelves")
        iconPath = os.path.join(mayaModPath, "icons")

        paths = [pluginPath, scriptPath, presetPath, shelfPath, iconPath]
        for path in paths:
            if not os.path.exists(path):
                os.makedirs(path)

        if pluginPath not in os.environ["MAYA_PLUG_IN_PATH"]:
            os.environ["MAYA_PLUG_IN_PATH"] += ";" + pluginPath

        if scriptPath not in os.environ["MAYA_SCRIPT_PATH"]:
            os.environ["MAYA_SCRIPT_PATH"] += ";" + scriptPath

        if presetPath not in os.environ["MAYA_PRESET_PATH"]:
            os.environ["MAYA_PRESET_PATH"] += ";" + presetPath

        if "MAYA_SHELF_PATH" not in os.environ:
            os.environ["MAYA_SHELF_PATH"] = ""

        if shelfPath not in os.environ["MAYA_SHELF_PATH"]:
            os.environ["MAYA_SHELF_PATH"] += ";" + shelfPath  # this is too late to be recognized by Maya during launch, so we needs to load shelves manually
            for file in os.listdir(shelfPath):
                if not file.endswith(".mel"):
                    continue

                filepath = os.path.join(shelfPath, file)
                try:
                    mel.eval('loadNewShelf "%s"' % filepath.replace("\\", "/"))
                except Exception as e:
                    logger.warning("failed to load shelf: %s - %s" % (filepath.replace("\\", "/"), e))

        if iconPath not in os.environ["XBMLANGPATH"]:
            os.environ["XBMLANGPATH"] += ";" + iconPath

        if scriptPath not in sys.path:
            sys.path.append(scriptPath)

    @err_catcher(name=__name__)
    def onShelfClickedImport(self, doubleclick: bool = False) -> None:
        """Handle Import shelf button click.
        
        Args:
            doubleclick: True if double-clicked
        """
        if doubleclick:
            self.onShelfClickedImportConnectedAssets()
            return

        sm = self.core.getStateManager()
        if not sm:
            return

        state = sm.createState(
            "ImportFile",
            setActive=True,
            openProductsBrowser=True,
        )

        return state

    @err_catcher(name=__name__)
    def onShelfClickedImportConnectedAssets(self, doubleclick: bool = False, quiet: bool = False) -> None:
        """Import connected assets.
        
        Args:
            doubleclick: True if double-clicked
            quiet: Suppress dialogs if True
        """
        self.core.products.importConnectedAssets(quiet=quiet)

    @err_catcher(name=__name__)
    def onShelfClickedExport(self, doubleclick: bool = False) -> None:
        """Handle Export shelf button click.
        
        Args:
            doubleclick: True if double-clicked
        """
        sm = self.core.getStateManager()
        if not sm:
            return

        if not self.core.fileInPipeline():
            self.core.showFileNotInProjectWarning(title="Warning")
            return False

        for state in sm.states:
            if state.ui.className == "Export" and state.ui.e_name.text() == "Default Export ({product})":
                state.ui.updateUi()
                break
        else:
            parent = self.getDftStateParent()
            state = sm.createState("Export", stateData={"stateName": "Default Export ({product})", "assetToExport": 1}, parent=parent, applyDefaults=True)
            if not state:
                msg = "Failed to create export state. Please contact the support."
                self.core.popup(msg)
                return

        if hasattr(self, "dlg_export"):
            self.dlg_export.showSm = False
            self.dlg_export.close()

        self.dlg_export = ExporterDlg(self, state)
        if doubleclick:
            state.ui.clearItems()
            state.ui.addObjects()
            self.dlg_export.submit(openOnFail=False)
        else:
            state.ui.w_name.setVisible(False)
            state.ui.gb_previous.setVisible(False)
            self.dlg_export.show()

    @err_catcher(name=__name__)
    def onShelfClickedPlayblast(self, doubleclick: bool = False) -> None:
        """Handle Playblast shelf button click.
        
        Args:
            doubleclick: True if double-clicked
        """
        sm = self.core.getStateManager()
        if not sm:
            return

        if not self.core.fileInPipeline():
            self.core.showFileNotInProjectWarning(title="Warning")
            return False

        for state in sm.states:
            if state.ui.className == "Playblast" and state.ui.e_name.text() == "Default Playblast ({identifier})":
                state.ui.updateUi()
                break
        else:
            parent = self.getDftStateParent()
            state = sm.createState("Playblast", stateData={"stateName": "Default Playblast ({identifier})"}, parent=parent, applyDefaults=True)
            if not state:
                msg = "Failed to create playblast state. Please contact the support."
                self.core.popup(msg)
                return

        if hasattr(self, "dlg_playblast"):
            self.dlg_playblast.showSm = False
            self.dlg_playblast.close()

        self.dlg_playblast = PlayblastDlg(self, state)
        if doubleclick:
            self.dlg_playblast.submit(openOnFail=False)
        else:
            state.ui.w_name.setVisible(False)
            state.ui.gb_previous.setVisible(False)
            self.dlg_playblast.show()

    @err_catcher(name=__name__)
    def onShelfClickedRender(self, doubleclick: bool = False) -> None:
        """Handle Render shelf button click.
        
        Args:
            doubleclick: True if double-clicked
        """
        sm = self.core.getStateManager()
        if not sm:
            return

        if not self.core.fileInPipeline():
            self.core.showFileNotInProjectWarning(title="Warning")
            return False

        for state in sm.states:
            if state.ui.className == "ImageRender" and state.ui.e_name.text() == "Default ImageRender - {identifier}":
                state.ui.updateUi()
                break
        else:
            parent = self.getDftStateParent()
            state = sm.createState("ImageRender", stateData={"stateName": "Default ImageRender - {identifier}"}, parent=parent, applyDefaults=True)
            if not state:
                msg = "Failed to create render state. Please contact the support."
                self.core.popup(msg)
                return

        if hasattr(self, "dlg_render"):
            self.dlg_render.showSm = False
            self.dlg_render.close()

        self.dlg_render = RenderDlg(self, state)
        if doubleclick:
            self.dlg_render.submit(openOnFail=False)
        else:
            state.ui.f_name.setVisible(False)
            state.ui.gb_previous.setVisible(False)
            self.dlg_render.show()

    @err_catcher(name=__name__)
    def openBatchExport(self) -> None:
        """Open batch export dialog."""
        """Open the batch export dialog for exporting multiple assets at once"""
        sm = self.core.getStateManager()
        if not sm:
            return

        if not self.core.fileInPipeline():
            self.core.showFileNotInProjectWarning(title="Warning")
            return False

        if hasattr(self, "dlg_batch_export"):
            self.dlg_batch_export.close()

        self.dlg_batch_export = BatchExportDlg(self, allowCache=False)
        self.dlg_batch_export.show()

    @err_catcher(name=__name__)
    def getSetPrefix(self) -> str:
        """Get selection set prefix from config.
        
        Returns:
            Selection set prefix string
        """
        return self.core.getConfig("maya", "setPrefix", config="project") or ""

    @err_catcher(name=__name__)
    def getDftStateParent(self, create: bool = True) -> Optional[str]:
        """Get default state parent group.
        
        Args:
            create: Create group if missing
            
        Returns:
            Group name or None
        """
        sm = self.core.getStateManager()
        if not sm:
            return

        for state in sm.states:
            if state.ui.listType != "Export" or state.ui.className != "Folder":
                continue

            if state.ui.e_name.text() != "Default States":
                continue

            return state

        if create:
            stateData = {
                "statename": "Default States",
                "listtype": "Export",
                "stateenabled": 2,
                "stateexpanded": False,
            }
            state = sm.createState("Folder", stateData=stateData)
            return state

    @err_catcher(name=__name__)
    def setMayaProject(self, path: Optional[str] = None, default: bool = False) -> None:
        """Set Maya workspace/project.
        
        Args:
            path: Project path, or None for Prism project
            default: Set to Maya\'s default project
        """
        if default:
            base = QDir.homePath()
            if platform.system() == "Windows":
                base = os.path.join(base, "Documents")

            path = os.path.join(base, "maya", "projects", "default")

        path = path.replace("\\", "/")
        if not os.path.exists(path):
            os.makedirs(path)

        wsPath = path + "/workspace.mel"
        if not os.path.exists(wsPath):
            try:
                cmds.workspace(path, newWorkspace=True)
                logger.debug("created new workspace: %s" % path)
            except Exception as e:
                logger.debug("failed to create workspace: %s - %s" % (path, e))

            template = os.getenv("PRISM_MAYA_WORKSPACE_TEMPLATE")
            if template and os.path.exists(template):
                if not os.path.basename(template) == "workspace.mel":
                    template = os.path.join(template, "workspace.mel")

                if os.path.exists(template):
                    shutil.copy2(template, wsPath)

        logger.debug("open workspace: %s" % path)
        cmds.workspace(path, update=True)
        cmds.workspace(path, openWorkspace=True)
        if not os.path.exists(wsPath):
            try:
                cmds.workspace(path, saveWorkspace=True)
                logger.debug("saved workspace: %s" % path)
            except Exception as e:
                logger.debug("failed to save workspace: %s - %s" % (path, e))

    @err_catcher(name=__name__)
    def getMayaProject(self) -> str:
        """Get current Maya workspace path.
        
        Returns:
            Maya workspace directory
        """
        return cmds.workspace(fullName=True, q=True)

    @err_catcher(name=__name__)
    def sceneOpen(self, origin: Any) -> None:
        """Handle scene open callback.
        
        Args:
            origin: Prism core instance
        """
        if self.core.shouldAutosaveTimerRun():
            origin.startAutosaveTimer()

    @err_catcher(name=__name__)
    def getCurrentFileName(self, origin: Any, path: bool = True) -> str:
        """Get current scene file name.
        
        Args:
            origin: Originating instance
            path: Return full path if True, basename if False
            
        Returns:
            Scene file path or name
        """
        if path:
            filename = cmds.file(q=True, sceneName=True)
            if not filename:
                filename = cmds.file(q=True, location=True)

        else:
            filename = cmds.file(q=True, sceneName=True, shortName=True)
            if not filename:
                filename = cmds.file(q=True, location=True, shortName=True)

        return filename

    @err_catcher(name=__name__)
    def getSceneExtension(self, origin: Optional[Any] = None) -> str:
        """Get scene file extension (.ma or .mb).
        
        Args:
            origin: Optional originating instance
            
        Returns:
            File extension
        """
        return self.sceneFormats[0]

    @err_catcher(name=__name__)
    def saveScene(self, origin: Any, filepath: str, details: Optional[Dict[str, Any]] = None, allowChangedExtension: bool = True) -> None:
        """Save Maya scene to file.
        
        Args:
            origin: Prism State Manager instance
            filepath: Target save path
            details: Optional scene details dict
            allowChangedExtension: Allow changing .ma <-> .mb
        """
        if not filepath:
            filepath = "untitled"

        if allowChangedExtension:
            saveSceneType = self.core.getConfig("maya", "saveSceneType")
            if saveSceneType == ".ma":
                sType = "mayaAscii"
            elif saveSceneType == ".mb":
                sType = "mayaBinary"
            else:
                curExt = os.path.splitext(self.core.getCurrentFileName())[1]
                if curExt == ".ma":
                    sType = "mayaAscii"
                elif curExt == ".mb":
                    sType = "mayaBinary"
                else:
                    if saveSceneType == ".ma (prefer current scene type)":
                        sType = "mayaAscii"
                    elif saveSceneType == ".mb (prefer current scene type)":
                        sType = "mayaBinary"
                    else:
                        sType = "mayaAscii"

            if sType == "mayaBinary":
                sceneExtension = ".mb"
            else:
                sceneExtension = ".ma"

            filepath = os.path.splitext(filepath)[0] + sceneExtension
        else:
            ext = os.path.splitext(filepath)[1]
            if ext == ".mb":
                sType = "mayaBinary"
            else:
                sType = "mayaAscii"

        cmds.file(rename=filepath)

        try:
            result = cmds.file(save=True, type=sType)
        except:
            return False
        else:
            if not cmds.about(batch=True):
                mel.eval("addRecentFile(\"%s\", \"%s\");" % (filepath, sType))

            return result

    @err_catcher(name=__name__)
    def getImportPaths(self, origin: Any) -> List[Dict[str, str]]:
        """Get paths for file import.
        
        Args:
            origin: Originating instance
            
        Returns:
            List of path dicts
        """
        val = cmds.fileInfo("PrismImports", query=True)

        if len(val) == 0:
            return False

        return eval('"%s"' % val[0])

    @err_catcher(name=__name__)
    def getFrameRange(self, origin: Optional[Any] = None) -> List[int]:
        """Get timeline frame range.
        
        Args:
            origin: Optional originating instance
            
        Returns:
            [start_frame, end_frame]
        """
        startframe = cmds.playbackOptions(q=True, minTime=True)
        endframe = cmds.playbackOptions(q=True, maxTime=True)

        return [startframe, endframe]

    @err_catcher(name=__name__)
    def getCurrentFrame(self) -> int:
        """Get current timeline frame.
        
        Returns:
            Current frame number
        """
        currentFrame = cmds.currentTime(q=True)
        return currentFrame

    @err_catcher(name=__name__)
    def setFrameRange(self, origin: Any, startFrame: int, endFrame: int) -> None:
        """Set timeline frame range.
        
        Args:
            origin: Originating instance
            startFrame: Start frame
            endFrame: End frame
        """
        cmds.playbackOptions(
            animationStartTime=startFrame,
            animationEndTime=endFrame,
            minTime=startFrame,
            maxTime=endFrame,
        )
        cmds.currentTime(startFrame, edit=True)

    @err_catcher(name=__name__)
    def getFPS(self, origin: Any) -> float:
        """Get frames per second.
        
        Args:
            origin: Originating instance
            
        Returns:
            FPS value
        """
        fps = mel.eval("currentTimeUnitToFPS")
        fps = int(fps * 1000) / 1000
        return fps

    @err_catcher(name=__name__)
    def setFPS(self, origin: Any, fps: Union[int, float, str]) -> None:
        """Set frames per second.
        
        Args:
            origin: Originating instance
            fps: FPS value or string like \'24fps\'
        """
        if int(fps) == float(fps):
            fps = int(fps)
        else:
            fps = float(fps)

        try:
            frange = self.getFrameRange(origin)
            mel.eval("currentUnit -time %sfps;" % fps)
            self.setFrameRange(origin, frange[0], frange[1])
        except:
            self.core.popup(
                "Cannot set the FPS in the current scene to %s." % fps,
            )

    @err_catcher(name=__name__)
    def getResolution(self) -> List[int]:
        """Get render resolution.
        
        Returns:
            [width, height]
        """
        width = cmds.getAttr("defaultResolution.width")
        height = cmds.getAttr("defaultResolution.height")
        return [width, height]

    @err_catcher(name=__name__)
    def setResolution(self, width: Optional[int] = None, height: Optional[int] = None) -> None:
        """Set render resolution.
        
        Args:
            width: Width in pixels
            height: Height in pixels
        """
        if width:
            cmds.setAttr("defaultResolution.width", width)
        if height:
            cmds.setAttr("defaultResolution.height", height)

        w, h = self.getResolution()
        cmds.setAttr("defaultResolution.deviceAspectRatio", (w / float(h)))

    @err_catcher(name=__name__)
    def getAppVersion(self, origin: Any) -> str:
        """Get Maya version.
        
        Args:
            origin: Originating instance
            
        Returns:
            Version string
        """
        return str(cmds.about(apiVersion=True))

    @err_catcher(name=__name__)
    def onProjectBrowserStartup(self, origin: Any) -> None:
        """Handle Project Browser startup.
        
        Args:
            origin: Project Browser instance
        """
        origin.mediaBrowser.w_preview.mediaPlayer.sl_preview.mousePressEvent = (
            origin.mediaBrowser.w_preview.mediaPlayer.sl_preview.origMousePressEvent
        )
        origin.setStyleSheet("QScrollArea { border: 0px solid rgb(150,150,150); }")

    @err_catcher(name=__name__)
    def newScene(self, force: bool = False) -> bool:
        """Create new scene.
        
        Args:
            force: Force new scene without save prompt
            
        Returns:
            True if successful
        """
        if cmds.file(q=True, modified=True) and not force and not cmds.about(batch=True):
            if cmds.file(q=True, exists=True):
                scenename = cmds.file(q=True, sceneName=True)
            else:
                scenename = "untitled scene"

            option = cmds.confirmDialog(
                title="Save Changes",
                message=("Save changes to %s?" % scenename),
                button=["Save", "Don't Save", "Cancel"],
                defaultButton="Save",
                cancelButton="Cancel",
                dismissString="Cancel",
            )
            if option == "Save":
                if cmds.file(q=True, exists=True):
                    cmds.file(save=True)
                else:
                    cmds.SaveScene()

                if cmds.file(q=True, exists=True):
                    cmds.file(new=True, force=True)

            elif option == "Don't Save":
                cmds.file(new=True, force=True)
            else:
                return False

        else:
            cmds.file(new=True, force=True)

        return True

    @err_catcher(name=__name__)
    def openScene(self, origin: Any, filepath: str, force: bool = False) -> bool:
        """Open Maya scene file.
        
        Args:
            origin: Originating instance
            filepath: Scene file path
            force: Force open without save prompt
            
        Returns:
            True if successful
        """
        if not filepath.endswith(".ma") and not filepath.endswith(".mb"):
            return False

        try:
            if cmds.file(q=True, modified=True) and not force and not cmds.about(batch=True):
                if cmds.file(q=True, exists=True):
                    scenename = cmds.file(q=True, sceneName=True)
                else:
                    scenename = "untitled scene"

                option = cmds.confirmDialog(
                    title="Save Changes",
                    message=("Save changes to %s?" % scenename),
                    button=["Save", "Don't Save", "Cancel"],
                    defaultButton="Save",
                    cancelButton="Cancel",
                    dismissString="Cancel",
                )
                if option == "Save":
                    if cmds.file(q=True, exists=True):
                        cmds.file(save=True)
                    else:
                        cmds.SaveScene()
                    if cmds.file(q=True, exists=True):
                        cmds.file(filepath, o=True, force=True)
                elif option == "Don't Save":
                    cmds.file(filepath, o=True, force=True)

            else:
                cmds.file(filepath, o=True, force=True)
        except Exception as e:
            logger.debug("error while opening scene: %s" % e)
        else:
            if not cmds.about(batch=True):
                if os.path.splitext(filepath)[1] == ".mb":
                    sType = "mayaBinary"
                else:
                    sType = "mayaAscii"

                mel.eval("addRecentFile(\"%s\", \"%s\");" % (filepath, sType))

        return True

    @err_catcher(name=__name__)
    def appendEnvFile(self, envVar: str = "MAYA_MODULE_PATH") -> None:
        """Append Prism paths to Maya environment variable.
        
        Args:
            envVar: Environment variable name
        """
        envPath = os.path.join(
            os.environ["MAYA_APP_DIR"], cmds.about(version=True), "Maya.env"
        )

        if not hasattr(self.core, "projectPath"):
            QMessageBox.warning(
                self.core.messageParent, "Prism", "No project is currently active."
            )
            return

        modPath = os.path.join(
            self.core.projects.getPipelineFolder(), "CustomModules", "Maya"
        )
        if not os.path.exists(modPath):
            os.makedirs(modPath)

        with open(os.path.join(modPath, "prism.mod"), "a") as modFile:
            modFile.write("\n+ prism 1.0 .\\")

        varText = "MAYA_MODULE_PATH=%s;&" % modPath

        if os.path.exists(envPath):
            with open(envPath, "r") as envFile:
                envText = envFile.read()

            if varText in envText:
                QMessageBox.information(
                    self.core.messageParent,
                    "Prism",
                    "The following path is already in the Maya.env file:\n\n%s"
                    % modPath,
                )
                return

        with open(envPath, "a") as envFile:
            envFile.write("\n" + varText)

        QMessageBox.information(
            self.core.messageParent,
            "Prism",
            "The following path was added to the MAYA_MODULE_PATH environment variable in the Maya.env file:\n\n%s\n\nRestart Maya to let this change take effect."
            % modPath,
        )

    @err_catcher(name=__name__)
    def updatedEnvironmentVars(self, reason: str, envVars: Dict[str, str], beforeRefresh: bool = False) -> None:
        """Handle environment variable updates.
        
        Args:
            reason: Reason for update
            envVars: Environment variables dict
            beforeRefresh: True if before refresh
        """
        doReload = False

        if reason == "refreshProject" and getattr(self, "unloadedOCIO", False):
            doReload = True
        else:
            for envVar in envVars:
                if envVar["key"] == "OCIO" and envVar["value"] != envVar["orig"]:
                    if reason == "unloadProject" and beforeRefresh:
                        self.unloadedOCIO = True
                        continue

                    doReload = True

        if doReload:
            self.unloadedOCIO = False
            self.refreshOcio()

    @err_catcher(name=__name__)
    def refreshOcio(self) -> None:
        """Refresh OCIO color management settings."""
        cmds.evalDeferred('import os;cmds.colorManagementPrefs(e=True, configFilePath=os.getenv("OCIO", ""))', lp=True)
        cmds.evalDeferred('cmds.colorManagementPrefs(refresh=True)', lp=True)

    @err_catcher(name=__name__)
    def importImages(self, filepath: Optional[str] = None, mediaBrowser: Optional[Any] = None, parent: Optional[Any] = None) -> None:
        """Import images as backplate or dome light.
        
        Args:
            filepath: Image file path
            mediaBrowser: Media browser instance
            parent: Parent widget
        """
        if mediaBrowser:
            sourceData = mediaBrowser.compGetImportSource()
            if not sourceData:
                return

            filepath = sourceData[0][0]
            firstFrame = sourceData[0][1]
            lastFrame = sourceData[0][2]
            parent = parent or mediaBrowser

        fString = "Please select an import option:"
        buttons = ["Camera Backplate", "Dome Light", "Cancel"]
        result = self.core.popupQuestion(fString, buttons=buttons, icon=QMessageBox.NoIcon, parent=parent)

        if result == "Camera Backplate":
            self.importBackplate(filepath)
        elif result == "Dome Light":
            self.importDomeLightTexture(filepath)
        else:
            return

    @err_catcher(name=__name__)
    def importBackplate(self, mediaPath: str, camera: Optional[Any] = None) -> None:
        """Import image as camera backplate.
        
        Args:
            mediaPath: Image file path
            camera: Maya camera node, or None for current
        """
        if camera:
            camShape = cmds.listRelatives(camera, shapes=True)[0]
        else:
            camera, camShape = cmds.camera()

        imagePlane = cmds.imagePlane(camera=camShape)
        cmds.setAttr(imagePlane[1] + ".imageName", mediaPath, type="string")
        if "#" in os.path.basename(mediaPath):
            cmds.setAttr(imagePlane[1] + ".useFrameExtension", 1)

        cmds.lookThru(camera)

    @err_catcher(name=__name__)
    def importDomeLightTexture(self, mediaPath: str) -> None:
        """Create dome light with texture.
        
        Args:
            mediaPath: HDR/image file path
        """
        import mtoa.utils as mutils
        lightShape, light = mutils.createLocator("aiSkyDomeLight", asLight=True)
        filenode = cmds.shadingNode("file", asTexture=True, isColorManaged=True)
        cmds.setAttr("%s.fileTextureName" % filenode, mediaPath, type="string")
        cmds.connectAttr("%s.outColor" % filenode, "%s.color" % lightShape, force=True)

    @err_catcher(name=__name__)
    def sm_export_addObjects(self, origin: Any, objects: Optional[List[str]] = None) -> None:
        """Add objects to export state.
        
        Args:
            origin: Export state instance
            objects: List of object names
        """
        if objects is None:
            objects = self.getSelectedNodes()
        
        validObjects = []
        for obj in objects:
            if self.isNodeValid(origin, obj):
                matches = cmds.ls(obj, long=True)
                if matches:
                    validObjects.append([m for m in matches if m not in validObjects][0])
            else:
                logger.debug("invalid object for export: %s" % obj)

        setName = self.validate(origin.getTaskname())
        if not setName:
            setName = origin.setTaskname("Export")

        setName = self.getSetPrefix() + setName
        valid = self.isNodeValid(origin, setName)
        if not valid:
            setName = cmds.sets(name=setName)
            taskName = setName.split(self.getSetPrefix(), 1)[-1] if self.getSetPrefix() else setName
            if taskName != origin.getTaskname():
                origin.setTaskname(taskName)

        for obj in validObjects:
            if obj not in origin.nodes:
                try:
                    cmds.sets(obj, include=setName)
                except Exception as e:
                    self.core.popup("Cannot add object:\n\n%s" % str(e))
                else:
                    origin.nodes.append(obj)

    @err_catcher(name=__name__)
    def getNodeName(self, origin: Any, node: str) -> str:
        """Get node display name.
        
        Args:
            origin: Originating instance
            node: Node identifier
            
        Returns:
            Node name
        """
        if self.isNodeValid(origin, node):
            return cmds.ls(node)[0]
        else:
            return "invalid"

    @err_catcher(name=__name__)
    def getSelectedNodes(self) -> List[str]:
        """Get selected nodes.
        
        Returns:
            List of selected node names
        """
        return cmds.ls(selection=True)

    @err_catcher(name=__name__)
    def selectNodes(self, origin: Any) -> None:
        """Select nodes from export state.
        
        Args:
            origin: Export state instance
        """
        if origin.lw_objects.selectedItems() != []:
            nodes = []
            for i in origin.lw_objects.selectedItems():
                row = origin.lw_objects.row(i)
                if row > (len(origin.nodes) - 1):
                    continue

                node = origin.nodes[row]
                if self.isNodeValid(origin, node):
                    nodes.append(node)
            cmds.select(nodes)

    @err_catcher(name=__name__)
    def isNodeValid(self, origin: Any, handle: str, isSet: bool = False) -> bool:
        """Check if node exists and is valid.
        
        Args:
            origin: Originating instance
            handle: Node identifier
            
        Returns:
            True if valid
        """
        if "," in handle:
            import mayaUsd
            usdPrim = mayaUsd.ufe.ufePathToPrim(handle)
            valid = usdPrim and usdPrim.IsValid()
        else:
            try:
                if isSet:
                    valid = len(cmds.ls(handle, set=True)) > 0
                else:
                    valid = len(cmds.ls(handle)) > 0
            except:
                valid = False

        return valid

    @err_catcher(name=__name__)
    def getCamNodes(self, origin: Any, cur: bool = False) -> List[Any]:
        """Get camera nodes.
        
        Args:
            origin: Originating instance  
            cur: Return only current camera if True
            
        Returns:
            List of camera nodes
        """
        sceneCams = cmds.listRelatives(
            cmds.ls(cameras=True, long=True), parent=True, fullPath=True
        )
        if cur:
            sceneCams = ["Current View"] + sceneCams

        self.core.callback("maya_getCameraNodes", sceneCams)
        return sceneCams

    @err_catcher(name=__name__)
    def getCamName(self, origin: Any, handle: Any) -> str:
        """Get camera name.
        
        Args:
            origin: Originating instance
            handle: Camera node
            
        Returns:
            Camera name
        """
        if handle == "Current View":
            return handle

        if "," in handle:
            import mayaUsd
            usdPrim = mayaUsd.ufe.ufePathToPrim(handle)
            if usdPrim and usdPrim.IsValid():
                nodes = [handle]
            else:
                nodes = []
        else:
            nodes = cmds.ls(handle)

        if len(nodes) == 0:
            return "invalid"
        else:
            return str(nodes[0])

    @err_catcher(name=__name__)
    def selectCam(self, origin: Any) -> None:
        """Select camera in viewport.
        
        Args:
            origin: Playblast/render state
        """
        if self.isNodeValid(origin, origin.curCam):
            cmds.select(origin.curCam)

    @err_catcher(name=__name__)
    def getUseRelativePath(self) -> bool:
        """Check if relative paths should be used.
        
        Returns:
            True if using relative paths
        """
        return self.core.getConfig(
            "maya", "useRelativePaths", dft=False, config="project"
        )

    @err_catcher(name=__name__)
    def getPathRelativeToProject(self, path: str) -> str:
        """Convert path to relative to Maya project.
        
        Args:
            path: Absolute file path
            
        Returns:
            Relative path or original if not in project
        """
        if not path:
            return path

        root = cmds.workspace(q=True, rd=True)
        try:
            absolute_path = os.path.normpath(os.path.abspath(path))
            reference_root = os.path.normpath(os.path.abspath(root))

            if os.name == "nt":
                abs_drive = os.path.splitdrive(absolute_path)[0].lower()
                ref_drive = os.path.splitdrive(reference_root)[0].lower()
                if abs_drive != ref_drive:
                    return absolute_path.replace("\\", "/")

            try:
                relative_path = os.path.relpath(absolute_path, reference_root)
            except ValueError:
                return absolute_path.replace("\\", "/")

            relative_path = relative_path.replace("\\", "/")
            if not relative_path.startswith("."):
                relative_path = "./" + relative_path

        except ValueError as e:
            logger.warning(str(e) + " - path: %s - start: %s" % (path, self.core.projectPath))

        return relative_path

    @err_catcher(name=__name__)
    def sm_export_startup(self, origin: Any) -> None:
        """Initialize export state UI.
        
        Args:
            origin: Export state instance
        """
        origin.f_objectList.setStyleSheet(
            "QFrame { border: 0px solid rgb(150,150,150); }"
        )
        if hasattr(origin, "w_additionalOptions"):
            origin.w_additionalOptions.setVisible(False)

        if hasattr(origin, "gb_submit"):
            origin.gb_submit.setVisible(True)

        origin.w_fbxSettings = QWidget()
        origin.lo_fbxSettings = QHBoxLayout()
        origin.lo_fbxSettings.setContentsMargins(9, 0, 9, 0)
        origin.w_fbxSettings.setLayout(origin.lo_fbxSettings)
        origin.l_fbxSettings = QLabel("Settings:")
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Expanding)
        origin.b_fbxSettings = QPushButton("Edit FBX Settings...")
        origin.lo_fbxSettings.addWidget(origin.l_fbxSettings)
        origin.lo_fbxSettings.addSpacerItem(spacer)
        origin.lo_fbxSettings.addWidget(origin.b_fbxSettings)

        origin.w_asset = QWidget()
        origin.lo_asset = QHBoxLayout()
        origin.lo_asset.setContentsMargins(9, 0, 9, 0)
        origin.w_asset.setLayout(origin.lo_asset)
        origin.l_asset = QLabel("Asset:")
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Expanding)
        origin.cb_asset = QComboBox()
        origin.lo_asset.addWidget(origin.l_asset)
        origin.lo_asset.addSpacerItem(spacer)
        origin.lo_asset.addWidget(origin.cb_asset)
        if not hasattr(origin, "onAssetChanged"):
            origin.onAssetChanged = self.onAssetChanged

        if not hasattr(origin, "refreshAssets"):
            origin.refreshAssets = self.refreshAssets

        origin.cb_asset.activated.connect(lambda x=None: origin.onAssetChanged(origin))

        origin.w_importReferences = QWidget()
        origin.lo_importReferences = QHBoxLayout()
        origin.lo_importReferences.setContentsMargins(9, 0, 9, 0)
        origin.w_importReferences.setLayout(origin.lo_importReferences)
        origin.l_importReferences = QLabel("Import references:")
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Expanding)
        origin.chb_importReferences = QCheckBox()
        origin.chb_importReferences.setChecked(True)
        origin.lo_importReferences.addWidget(origin.l_importReferences)
        origin.lo_importReferences.addSpacerItem(spacer)
        origin.lo_importReferences.addWidget(origin.chb_importReferences)

        origin.w_preserveReferences = QWidget()
        origin.lo_preserveReferences = QHBoxLayout()
        origin.lo_preserveReferences.setContentsMargins(9, 0, 9, 0)
        origin.w_preserveReferences.setLayout(origin.lo_preserveReferences)
        origin.l_preserveReferences = QLabel("Preserve references:")
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Expanding)
        origin.chb_preserveReferences = QCheckBox()
        origin.chb_preserveReferences.setChecked(True)
        origin.lo_preserveReferences.addWidget(origin.l_preserveReferences)
        origin.lo_preserveReferences.addSpacerItem(spacer)
        origin.lo_preserveReferences.addWidget(origin.chb_preserveReferences)
        origin.w_preserveReferences.setEnabled(False)

        origin.w_deleteUnknownNodes = QWidget()
        origin.lo_deleteUnknownNodes = QHBoxLayout()
        origin.lo_deleteUnknownNodes.setContentsMargins(9, 0, 9, 0)
        origin.w_deleteUnknownNodes.setLayout(origin.lo_deleteUnknownNodes)
        origin.l_deleteUnknownNodes = QLabel("Delete unknown nodes:")
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Expanding)
        origin.chb_deleteUnknownNodes = QCheckBox()
        origin.chb_deleteUnknownNodes.setChecked(True)
        origin.lo_deleteUnknownNodes.addWidget(origin.l_deleteUnknownNodes)
        origin.lo_deleteUnknownNodes.addSpacerItem(spacer)
        origin.lo_deleteUnknownNodes.addWidget(origin.chb_deleteUnknownNodes)

        origin.w_deleteDisplayLayers = QWidget()
        origin.lo_deleteDisplayLayers = QHBoxLayout()
        origin.lo_deleteDisplayLayers.setContentsMargins(9, 0, 9, 0)
        origin.w_deleteDisplayLayers.setLayout(origin.lo_deleteDisplayLayers)
        origin.l_deleteDisplayLayers = QLabel("Delete display layers:")
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Expanding)
        origin.chb_deleteDisplayLayers = QCheckBox()
        origin.chb_deleteDisplayLayers.setChecked(True)
        origin.lo_deleteDisplayLayers.addWidget(origin.l_deleteDisplayLayers)
        origin.lo_deleteDisplayLayers.addSpacerItem(spacer)
        origin.lo_deleteDisplayLayers.addWidget(origin.chb_deleteDisplayLayers)

        layout = origin.gb_export.layout()
        if hasattr(origin, "w_wholeScene"):
            idx = layout.indexOf(origin.w_wholeScene)
        else:
            idx = layout.count() - 3

        layout.insertWidget(idx, origin.w_asset)
        layout.insertWidget(idx, origin.w_fbxSettings)
        layout.insertWidget(idx, origin.w_importReferences)
        layout.insertWidget(idx, origin.w_preserveReferences)
        layout.insertWidget(idx, origin.w_deleteUnknownNodes)
        layout.insertWidget(idx, origin.w_deleteDisplayLayers)

        origin.b_fbxSettings.clicked.connect(self.editFbxSettings)
        origin.chb_importReferences.stateChanged.connect(
            lambda x: origin.w_preserveReferences.setEnabled(not x)
        )
        origin.chb_importReferences.stateChanged.connect(
            origin.stateManager.saveStatesToScene
        )
        origin.chb_deleteUnknownNodes.stateChanged.connect(
            origin.stateManager.saveStatesToScene
        )
        origin.chb_deleteDisplayLayers.stateChanged.connect(
            origin.stateManager.saveStatesToScene
        )
        origin.chb_preserveReferences.stateChanged.connect(
            origin.stateManager.saveStatesToScene
        )

    @err_catcher(name=__name__)
    def editFbxSettings(self) -> None:
        """Open FBX export settings dialog."""
        cmd = "FBXUICallBack -1 editExportPresetInNewWindow fbx;"
        mel.eval(cmd)

    @err_catcher(name=__name__)
    def validate(self, string: str) -> str:
        """Validate and sanitize Maya object name.
        
        Args:
            string: Name to validate
            
        Returns:
            Validated name
        """
        vstr = self.core.validateStr(string, denyChars=["-"])
        return vstr

    @err_catcher(name=__name__)
    def mergeSets(self, fromSet: str, toSet: str) -> None:
        """Merge one selection set into another.
        
        Args:
            fromSet: Source set name
            toSet: Target set name
        """
        objs = cmds.sets(fromSet, query=True)
        cmds.sets(objs, include=toSet)
        cmds.sets(objs, remove=fromSet)
        cmds.delete(fromSet)

    @err_catcher(name=__name__)
    def sm_export_setTaskText(self, origin: Any, prevTaskName: str, newTaskName: str, create: bool = True) -> None:
        """Update task name for export state.
        
        Args:
            origin: Export state instance
            prevTaskName: Previous task name
            newTaskName: New task name
            create: Create selection set if missing
        """
        prev = self.validate(prevTaskName) if prevTaskName else ""
        prevSet = self.getSetPrefix() + prev
        newSetName = self.getSetPrefix() + newTaskName
        if origin.stateManager.standalone:
            return newSetName

        if self.isNodeValid(origin, prevSet, isSet=True) and "objectSet" in cmds.nodeType(
            prevSet, inherited=True
        ):
            if create:
                if prevSet == newSetName:
                    return newSetName

                if not newSetName:
                    return prev

                if self.isNodeValid(origin, newSetName, isSet=True) and "objectSet" in cmds.nodeType(
                    newSetName, inherited=True
                ):
                    logger.debug(traceback.format_stack())
                    msg = "A selection set with the name \"%s\" does already exist." % newSetName
                    handleDups = os.getenv("PRISM_MAYA_DUPLICATE_EXPORT_SETS", "merge")
                    if not handleDups or handleDups.lower() == "ask":
                        result = self.core.popupQuestion(msg, buttons=["Merge sets", "Use unique name", "Cancel"], icon=QMessageBox.Warning)
                    elif handleDups.lower() == "merge":
                        result = "Merge sets"
                    elif handleDups.lower() == "unique":
                        result = "Use unique name"
                    else:
                        result = "Cancel"

                    if result == "Merge sets":
                        self.mergeSets(prevSet, newSetName)
                        return newTaskName
                    elif result == "Cancel":
                        return prev

                try:
                    setName = cmds.rename(prevSet, newSetName)
                    setName = setName.split(self.getSetPrefix(), 1)[-1] if self.getSetPrefix() else setName
                except Exception as e:
                    self.core.popup("Failed to rename set from \"%s\" to \"%s\": %s" % (prevSet, newSetName, e))
                    setName = prev
            else:
                cmds.delete(prevSet)
                setName = None
        elif create:
            valid = self.isNodeValid(origin, newSetName, isSet=True)
            isSet = "objectSet" in cmds.nodeType(newSetName, inherited=True) if valid else False
            if valid and isSet and origin.stateManager.loading:
                setName = newTaskName
            else:
                setName = cmds.sets(name=newSetName)
                setName = setName.split(self.getSetPrefix(), 1)[-1] if self.getSetPrefix() else setName
        else:
            setName = None

        return setName

    @err_catcher(name=__name__)
    def sm_export_removeSetItem(self, origin: Any, node: str) -> None:
        """Remove node from export selection set.
        
        Args:
            origin: Export state instance
            node: Node name to remove
        """
        setName = self.getSetPrefix() + self.validate(origin.getTaskname())
        cmds.sets(node, remove=setName)

    @err_catcher(name=__name__)
    def sm_export_clearSet(self, origin: Any) -> None:
        """Clear all nodes from export set.
        
        Args:
            origin: Export state instance
        """
        setName = self.getSetPrefix() + origin.getTaskname()
        if self.isNodeValid(origin, setName):
            cmds.sets(clear=setName)

    @err_catcher(name=__name__)
    def sm_export_updateObjects(self, origin: Any) -> None:
        """Update object list in export UI.
        
        Args:
            origin: Export state instance
        """
        if origin.stateManager.standalone:
            return

        prevSel = cmds.ls(selection=True, long=True)
        setName = self.validate(origin.getTaskname())
        if not setName:
            setName = origin.setTaskname("Export")
            return False

        setName = self.getSetPrefix() + setName
        try:
            # the nodes in the set need to be selected to get their long dag path
            cmds.select(setName)
            if "objectSet" not in cmds.nodeType(setName, inherited=True):
                cmds.select(clear=True)
                raise Exception
        except:
            newSetName = cmds.sets(name=setName)
            if newSetName != setName:
                newTaskName = newSetName.split(self.getSetPrefix(), 1)[-1] if self.getSetPrefix() else newSetName
                origin.setTaskname(newTaskName)
                return False

        origin.nodes = cmds.ls(selection=True, long=True)
        try:
            cmds.select(prevSel, noExpand=True)
        except:
            pass

    @err_catcher(name=__name__)
    def sm_export_exportShotcam(self, origin: Any, startFrame: int, endFrame: int, outputName: str) -> None:
        """Export shot camera.
        
        Args:
            origin: Export state instance
            startFrame: Start frame
            endFrame: End frame
            outputName: Output file path
        """
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

    @err_catcher(name=__name__)
    def isFbxPluginLoaded(self) -> bool:
        """Check if FBX plugin is loaded.
        
        Returns:
            True if loaded
        """
        try:
            mel.eval("FBXExtPlugin -l")
            return True
        except:
            pass

        return False

    @err_catcher(name=__name__)
    def preExport(self, **kwargs: Any) -> None:
        """Pre-export callback.
        
        Args:
            **kwargs: Export parameters
        """
        nodes = kwargs["state"].nodes
        if not nodes:
            return

        node = nodes[0]
        if not self.isNodeValid(None, node):
            return

        if not cmds.referenceQuery(node, isNodeReferenced=True) and cmds.objectType(node) != "reference":
            return

        refNode = cmds.referenceQuery(
            node, referenceNode=True, topReference=True
        )
        fileName = cmds.referenceQuery(refNode, filename=True)
        productData = self.core.paths.getCachePathData(fileName)
        if not productData or not productData.get("asset_path"):
            return

        extraVersionInfo = {
            "source_asset_path": productData["asset_path"]
        }
        return {"extraVersionInfo": extraVersionInfo}

    @err_catcher(name=__name__)
    def sm_export_exportAppObjects(
        self,
        origin: Any,
        startFrame: int,
        endFrame: int,
        outputName: str,
        nodes: Optional[List[str]] = None,
        expType: Optional[str] = None,
    ) -> Optional[str]:
        """Export objects from Maya in various formats.
        
        Handles export of selected objects or whole scene to ABC, FBX, OBJ, MA, MB, ATOM formats.
        Supports animation ranges, selection sets, and whole scene export.
        
        Args:
            origin: Export state instance
            startFrame: Animation start frame
            endFrame: Animation end frame
            outputName: Output file path
            nodes: Optional list of nodes to export
            expType: Export format type
            
        Returns:
            Error message string if cancelled, None on success
        """
        cmds.select(clear=True)
        if nodes is None:
            setName = self.getSetPrefix() + self.validate(origin.getTaskname())
            if not self.isNodeValid(origin, setName):
                return 'Canceled: The selection set "%s" is invalid.' % setName

            cmds.select(cmds.listConnections(setName), noExpand=True)
            expNodes = origin.nodes
        else:
            cmds.select(nodes)
            expNodes = [
                x for x in nodes if "dagNode" in cmds.nodeType(x, inherited=True)
            ]

        if expType is None:
            expType = origin.getOutputType()

        if expType == ".obj":
            self.exportAsObj(
                outputName,
                objects=origin.nodes,
                wholeScene=origin.chb_wholeScene.isChecked(),
                startFrame=startFrame,
                endFrame=endFrame
            )
        elif expType == ".fbx":
            origRange = self.getFrameRange()
            self.setFrameRange(None, startFrame, endFrame)
            fbxKeyframes = os.getenv("PRISM_MAYA_FBX_DELETE_OOR_KEYFRAMES", "0")
            if fbxKeyframes == "1":
                result = "Yes"
            elif fbxKeyframes == "2":
                msg = "By default Maya will export all keyframes to the fbx file even if a framerange is defined.\n\nDo you want to delete all keyframes outside of the defined range? (The scenefile will be reloaded after the publish.)"
                result = self.core.popupQuestion(msg)
            else:
                result = "No"

            if result == "Yes":
                self.deleteOutOfRangeKeys()
                origin.stateManager.reloadScenefile = True

            if not self.isFbxPluginLoaded():
                return "Canceled: The Maya FBX plugin isn't loaded"

            if origin.chb_wholeScene.isChecked():
                mel.eval('FBXExport -f "%s"' % outputName.replace("\\", "\\\\"))
            else:
                prevSel = cmds.ls(selection=True, long=True)
                cmds.select(expNodes)
                mel.eval('FBXExport -f "%s" -s' % outputName.replace("\\", "\\\\"))

                try:
                    cmds.select(prevSel, noExpand=True)
                except:
                    pass

            self.setFrameRange(None, origRange[0], origRange[1])
        elif expType == ".abc":
            wholeScene = origin.chb_wholeScene.isChecked()
            result = self.exportAlembic(
                outputName,
                startFrame,
                endFrame,
                nodes=expNodes,
                wholeScene=wholeScene,
                origin=origin,
            )
            if not result:
                return result

        elif expType == ".atom":
            wholeScene = origin.chb_wholeScene.isChecked()
            result = self.exportAtom(
                outputName,
                startFrame,
                endFrame,
                nodes=expNodes,
                wholeScene=wholeScene,
            )
            if not result:
                return result

        elif expType in [".ma", ".mb"]:
            requiresReload = False
            if origin.chb_importReferences.isChecked():
                refFiles = cmds.file(query=True, reference=True)
                prevSel = cmds.ls(selection=True, long=True)

                for i in refFiles:
                    if cmds.file(i, query=True, deferReference=True):
                        msgStr = (
                            'Referenced file "%s" is currently unloaded and cannot be imported.\nWould you like keep or remove this reference in the exported file (it will remain in the working scenefile file) ?'
                            % i
                        )
                        msg = QMessageBox(
                            QMessageBox.Question,
                            "Import Reference",
                            msgStr,
                            QMessageBox.NoButton,
                        )
                        msg.addButton("Keep", QMessageBox.YesRole)
                        msg.addButton("Remove", QMessageBox.YesRole)
                        self.core.parentWindow(msg)
                        result = msg.exec_()

                        if result == 1:
                            cmds.file(i, removeReference=True)
                            requiresReload = True
                    else:
                        cmds.file(i, importReference=True)
                        requiresReload = True

                try:
                    cmds.select(prevSel, noExpand=True)
                except:
                    pass

            if origin.chb_deleteUnknownNodes.isChecked():
                unknownDagNodes = cmds.ls(type="unknownDag")
                unknownNodes = cmds.ls(type="unknown")
                for item in unknownNodes:
                    if cmds.objExists(item):
                        if cmds.lockNode(item, query=True)[0]:
                            cmds.lockNode(item, lock=False)

                        cmds.delete(item)
                        requiresReload = True
                for item in unknownDagNodes:
                    if cmds.objExists(item):
                        if cmds.lockNode(item, query=True)[0]:
                            cmds.lockNode(item, lock=False)

                        cmds.delete(item)
                        requiresReload = True

                self.cleanUnknownPlugins()

            if origin.chb_deleteDisplayLayers.isChecked():
                layers = cmds.ls(type="displayLayer")
                for i in layers:
                    if i != "defaultLayer":
                        cmds.delete(i)
                        requiresReload = True

            if requiresReload:
                origin.stateManager.reloadScenefile = True

            curFileName = self.core.getCurrentFileName()
            if (
                origin.chb_wholeScene.isChecked()
                and os.path.splitext(curFileName)[1] == expType
                and not requiresReload
            ):
                self.core.copySceneFile(curFileName, outputName)
            else:
                if expType == ".ma":
                    typeStr = "mayaAscii"
                elif expType == ".mb":
                    typeStr = "mayaBinary"
                pr = origin.chb_preserveReferences.isChecked()
                try:
                    includeHistory = True
                    includeChannels = True
                    includeConstraints = True
                    includeExpressions = True
                    includeShader = True
                    removeNamespaces = False
                    if getattr(origin, "additionalSettings", None):
                        for setting in origin.additionalSettings:
                            if setting["name"] == "includeHistory":
                                includeHistory = setting["value"]
                            elif setting["name"] == "includeChannels":
                                includeChannels = setting["value"]
                            elif setting["name"] == "includeConstraints":
                                includeConstraints = setting["value"]
                            elif setting["name"] == "includeExpressions":
                                includeExpressions = setting["value"]
                            elif setting["name"] == "includeShader":
                                includeShader = setting["value"]
                            elif setting["name"] == "removeNamespaces":
                                removeNamespaces = setting["value"]

                    kwargs = {
                        "force": True,
                        "preserveReferences": pr,
                        "exportUnloadedReferences": pr,
                        "type": typeStr,
                        "constructionHistory": includeHistory,
                        "channels": includeChannels,
                        "constraints": includeConstraints,
                        "expressions": includeExpressions,
                        "shader": includeShader,
                    }

                    selected = not origin.chb_wholeScene.isChecked()
                    if removeNamespaces:
                        namespaces = self.getNamespaces(fromSelected=selected)
                        if len(namespaces) > 1:
                            msg = "Multiple namespaces found in the exported objects. Only a single namespace can be removed."
                            result = self.core.popupQuestion(msg, buttons=["Keep namespaces", "Cancel"], icon=QMessageBox.Warning)
                            if result == "Cancel":
                                return "Canceled: ..."
                        
                        relNamespace = namespaces[0] + ":" if namespaces else ""
                        if relNamespace:
                            kwargs["relativeNamespace"] = relNamespace
                            if "preserveReferences" in kwargs:
                                del kwargs["preserveReferences"]

                            if "exportUnloadedReferences" in kwargs:
                                del kwargs["exportUnloadedReferences"]

                    if selected:
                        kwargs["exportSelected"] = True
                    else:
                        kwargs["exportAll"] = True

                    logger.debug("Exporting with options: %s to %s" % (kwargs, outputName))
                    cmds.file(
                        outputName,
                        **kwargs,
                    )
                except Exception as e:
                    return "Canceled: %s" % str(e)

                for expNode in expNodes:
                    if not self.isNodeValid(origin, expNode):
                        continue

                    if cmds.nodeType(expNode) == "xgmPalette" and cmds.attributeQuery(
                        "xgFileName", node=expNode, exists=True
                    ):
                        xgenName = cmds.getAttr(expNode + ".xgFileName")
                        curXgenPath = os.path.join(
                            os.path.dirname(self.core.getCurrentFileName()), xgenName
                        )
                        tXgenPath = os.path.join(os.path.dirname(outputName), xgenName)
                        shutil.copyfile(curXgenPath, tXgenPath)

        elif expType == ".rs":
            cmds.select(expNodes)
            opt = ""
            if startFrame != endFrame:
                opt = "startFrame=%s;endFrame=%s;frameStep=1;" % (startFrame, endFrame)

            opt += "exportConnectivity=0;enableCompression=0;"

            outputName = os.path.splitext(outputName)[0] + ".####.rs"
            outDir = os.path.dirname(outputName)
            if not os.path.exists(outDir):
                os.makedirs(outDir, exist_ok=True)

            pr = origin.chb_preserveReferences.isChecked()

            if origin.chb_wholeScene.isChecked():
                cmds.file(
                    outputName,
                    force=True,
                    exportAll=True,
                    type="Redshift Proxy",
                    preserveReferences=pr,
                    exportUnloadedReferences=pr,
                    options=opt,
                )
            else:
                cmds.file(
                    outputName,
                    force=True,
                    exportSelected=True,
                    type="Redshift Proxy",
                    preserveReferences=pr,
                    exportUnloadedReferences=pr,
                    options=opt,
                )

            outputName = outputName.replace("####", format(endFrame, "04"))
        elif expType == ".abc (GPU Cache)":
            cmds.loadPlugin("gpuCache.mll", quiet=True)
            baseName = os.path.splitext(os.path.basename(outputName))[0]
            outDir = os.path.dirname(outputName)
            if not os.path.exists(outDir):
                os.makedirs(outDir, exist_ok=True)

            if origin.chb_wholeScene.isChecked():
                gpuNodes = cmds.ls(assemblies=True)
            else:
                gpuNodes = expNodes

            cmds.gpuCache(
                gpuNodes,
                startTime=startFrame,
                endTime=endFrame,
                optimize=True,
                optimizationThreshold=40000,
                writeMaterials=True,
                directory=outDir,
                fileName=baseName,
                saveMultipleFiles=False,
            )
            outputName = os.path.join(outDir, baseName + ".abc")
        elif expType == ".ass":
            cmds.select(expNodes)
            opt = ""
            if startFrame != endFrame:
                opt = "-startFrame %s;-endFrame %s;-frameStep 1;" % (startFrame, endFrame)

            opt += "-boundingBox;-fullPath;-lightLinks 1;-shadowLinks 1;-mask 6399"

            outputName = os.path.splitext(outputName)[0] + ".ass"
            pr = origin.chb_preserveReferences.isChecked()

            if origin.chb_wholeScene.isChecked():
                cmds.file(
                    outputName,
                    force=True,
                    exportAll=True,
                    type="ASS Export",
                    preserveReferences=pr,
                    exportUnloadedReferences=pr,
                    options=opt,
                )
            else:
                cmds.file(
                    outputName,
                    force=True,
                    exportSelected=True,
                    type="ASS Export",
                    preserveReferences=pr,
                    exportUnloadedReferences=pr,
                    options=opt,
                )

            base, ext = os.path.splitext(outputName)
            if startFrame != endFrame:
                outputName = base + "." + format(endFrame, "04") + ext
        
        elif expType == ".otio":
            self.exportSequencerOtio(outputName)

        cmds.select(clear=True)
        return outputName

    @err_catcher(name=__name__)
    def getNamespaces(self, fromSelected: bool = False) -> List[str]:
        """Get namespaces from the scene or selected objects.
        
        Args:
            fromSelected: If True, get namespaces from selected objects only.
        
        Returns:
            List of namespaces.
        """
        if fromSelected:
            objects = cmds.ls(selection=True)
        else:
            objects = cmds.ls(dag=True, long=True)

        namespaces = set()
        for obj in objects:
            ns = obj.rsplit(":", 1)[0] if ":" in obj else ""
            if ns:
                namespaces.add(":" + ns)

        return list(namespaces)

    @err_catcher(name=__name__)
    def cleanUnknownPlugins(self) -> None:
        """Remove unknown plugin references from scene."""
        unknownPlugins = cmds.unknownPlugin(q=True, list=True)
        if unknownPlugins:
            for plugin in unknownPlugins:
                cmds.unknownPlugin(plugin, remove=True)

    @err_catcher(name=__name__)
    def exportAsObj(self, outputPath: str, objects: Optional[List[str]] = None, wholeScene: bool = False, startFrame: Optional[int] = None, endFrame: Optional[int] = None) -> None:
        """Export geometry as OBJ file.
        
        Args:
            outputPath: Output file path
            objects: Objects to export, or None for selection
            wholeScene: Export entire scene
            startFrame: Animation start frame
            endFrame: Animation end frame
        """
        cmds.loadPlugin("objExport", quiet=True)
        if objects:
            cmds.select(clear=True)
            objNodes = [
                x
                for x in objects
                if cmds.listRelatives(x, shapes=True) is not None
            ]
            cmds.select(objNodes)

        if startFrame is None:
            startFrame = endFrame = int(self.getCurrentFrame())

        for i in range(startFrame, endFrame + 1):
            cmds.currentTime(i, edit=True)
            foutputName = outputPath.replace("####", format(i, "04"))
            if wholeScene:
                cmds.file(
                    foutputName,
                    force=True,
                    exportAll=True,
                    type="OBJexport",
                    options="groups=1;ptgroups=1;materials=1;smoothing=1;normals=1",
                )
            else:
                if cmds.ls(selection=True) == []:
                    return "Canceled: No valid objects are specified for .obj export. No output will be created."
                else:
                    cmds.file(
                        foutputName,
                        force=True,
                        exportSelected=True,
                        type="OBJexport",
                        options="groups=1;ptgroups=1;materials=1;smoothing=1;normals=1",
                    )

        return foutputName

    @err_catcher(name=__name__)
    def deleteOutOfRangeKeys(self) -> None:
        """Delete animation keys outside timeline range."""
        startframe = cmds.playbackOptions(q=True, minTime=True)
        endframe = cmds.playbackOptions(q=True, maxTime=True)
        anim_curves = cmds.ls(type=['animCurveTA', 'animCurveTL', 'animCurveTT', 'animCurveTU'])
        for each in anim_curves:
            try:
                cmds.cutKey(each, time=(-99999, startframe-1), clear=True)
            except:
                pass

            try:
                cmds.cutKey(each, time=(endframe+1, 99999), clear=True)
            except:
                pass

    @err_catcher(name=__name__)
    def getCustomAttributes(self, obj: str) -> List[str]:
        """Get custom attributes on object.
        
        Args:
            obj: Object name
            
        Returns:
            List of attribute names
        """
        attrs = []
        mobjs = [obj] + (cmds.listRelatives(obj, children=True, fullPath=True) or [])
        for mobj in mobjs:
            cattrs = cmds.listAttr(mobj, userDefined=True) or []
            for cattr in cattrs:
                if cattr not in attrs:
                    attrs.append(cattr)

        return attrs

    @err_catcher(name=__name__)
    def exportAlembic(self, outputName: str, startFrame: int, endFrame: int, nodes: Optional[List[str]] = None, wholeScene: bool = False, origin: Optional[Any] = None) -> None:
        """Export to Alembic format.
        
        Args:
            outputName: Output file path
            startFrame: Start frame
            endFrame: End frame
            nodes: Nodes to export
            wholeScene: Export entire scene
            origin: Originating state
        """
        rootString = ""
        customAttributes = []
        if wholeScene:
            for obj in cmds.ls(assemblies=True):
                customAttributes += self.getCustomAttributes(obj)
                customAttributes = list(set(customAttributes))
        else:
            rootNodes = [
                x
                for x in nodes
                if len([k for k in nodes if x.rsplit("|", 1)[0] == k]) == 0
            ]
            for i in rootNodes:
                rootString += "-root %s " % i
                customAttributes += self.getCustomAttributes(i)
                customAttributes = list(set(customAttributes))

        expStr = 'AbcExport -j "-frameRange %s %s %s' % (
            startFrame,
            endFrame,
            rootString
        )

        if getattr(origin, "additionalSettings", None):
            for setting in origin.additionalSettings:
                if setting["name"] == "abcStep":
                    expStr += " -step " + str(setting["value"])
                elif setting["name"] == "abcNoNormals" and setting["value"]:
                    expStr += " -noNormals"
                elif setting["name"] == "abcRenderableOnly" and setting["value"]:
                    expStr += " -ro"
                elif setting["name"] == "abcStripNamespaces" and setting["value"]:
                    expStr += " -stripNamespaces"
                elif setting["name"] == "abcUvWrite" and setting["value"]:
                    expStr += " -uvWrite"
                elif setting["name"] == "abcWriteColorSets" and setting["value"]:
                    expStr += " -writeColorSets"
                elif setting["name"] == "abcWriteFaceSets" and setting["value"]:
                    expStr += " -writeFaceSets"
                elif setting["name"] == "abcWholeFrameGeo" and setting["value"]:
                    expStr += " -wholeFrameGeo"
                elif setting["name"] == "abcWorldSpace" and setting["value"]:
                    expStr += " -worldSpace"
                elif setting["name"] == "abcWriteVisibility" and setting["value"]:
                    expStr += " -writeVisibility"
                elif setting["name"] == "abcFilterEulerRotations" and setting["value"]:
                    expStr += " -eulerFilter"
                elif setting["name"] == "abcWriteCreases" and setting["value"]:
                    expStr += " -autoSubd"
                elif setting["name"] == "abcWriteUvSets" and setting["value"]:
                    expStr += " -writeUVSets"

        for customAttribute in customAttributes:
            expStr += " -attr %s " % customAttribute

        expStr += " -file \\\"%s\\\"\"" % outputName.replace("\\", "\\\\\\\\")
        cmd = {"export_cmd": expStr}
        self.core.callback(name="maya_export_abc", args=[self, cmd])

        logger.debug(cmd["export_cmd"])

        try:
            mel.eval(cmd["export_cmd"])
        except Exception as e:
            if "Conflicting root node names specified" in str(e):
                fString = "You are trying to export multiple objects with the same name, which is not supported in alembic format.\n\nDo you want to export your objects with namespaces?\nThis may solve the problem."
                msg = QMessageBox(QMessageBox.NoIcon, "Export", fString)
                msg.addButton("Export with namesspaces", QMessageBox.YesRole)
                msg.addButton("Cancel export", QMessageBox.YesRole)
                self.core.parentWindow(msg)
                action = msg.exec_()

                if action == 0:
                    cmd = cmd["export_cmd"].replace("-stripNamespaces ", "")
                    try:
                        mel.eval(cmd)
                    except Exception as e:
                        if "Already have an Object named:" in str(e):
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            erStr = "You are trying to export two objects with the same name, which is not supported with the alemic format:\n\n"
                            self.core.popup(erStr + str(e))
                            return False

                else:
                    return False
            else:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                self.core.popup(str(e))
                return False

        return True

    @err_catcher(name=__name__)
    def exportAtom(self, outputName: str, startFrame: int, endFrame: int, nodes: Optional[List[str]] = None, wholeScene: bool = False) -> None:
        """Export animation as ATOM file.
        
        Args:
            outputName: Output file path
            startFrame: Start frame
            endFrame: End frame
            nodes: Nodes to export
            wholeScene: Export entire scene
        """
        cmds.loadPlugin("atomImportExport.mll", quiet=True)
        try:
            cmds.file(
                outputName,
                force=True,
                exportSelected=not wholeScene,
                type="atomExport",
                preserveReferences=True,
                exportUnloadedReferences=True,
                options="statics=1;targetTime=3;selected=childrenToo",
            )
        except Exception as e:
            self.core.popup("Error occured during publish:\n\n%s" % e)
            return False

        return True

    @err_catcher(name=__name__)
    def sm_export_preDelete(self, origin: Any) -> None:
        """Pre-delete callback for export state.
        
        Args:
            origin: Export state instance
        """
        setName = self.getSetPrefix() + self.validate(origin.getTaskname())
        try:
            cmds.delete(setName)
        except:
            pass

    @err_catcher(name=__name__)
    def sm_export_unColorObjList(self, origin: Any) -> None:
        """Remove color coding from object list.
        
        Args:
            origin: Export state instance
        """
        origin.lw_objects.setStyleSheet(
            "QListWidget { border: 3px solid rgb(50,50,50); }"
        )

    @err_catcher(name=__name__)
    def sm_export_typeChanged(self, origin: Any, idx: int) -> None:
        """Handle export type change.
        
        Args:
            origin: Export state instance
            idx: New type index
        """
        origin.w_fbxSettings.setVisible(idx == ".fbx")
        exportScene = idx in [".ma", ".mb"]
        origin.w_importReferences.setVisible(exportScene)
        origin.w_deleteUnknownNodes.setVisible(exportScene)
        origin.w_deleteDisplayLayers.setVisible(exportScene)
        isSCam = idx == "ShotCam"
        isOtio = idx == ".otio"
        origin.w_asset.setVisible(not isSCam and not isOtio)
        origin.w_wholeScene.setVisible(not isOtio)
        origin.gb_objects.setVisible(not isOtio)
        if hasattr(origin, "gb_submit"):
            origin.gb_submit.setVisible(not isOtio)

        origin.w_range.setVisible(not isOtio)
        if hasattr(origin, "w_rangeFrames"):
            origin.w_rangeFrames.setVisible(not isOtio)

        preserveReferences = idx in [".ma", ".mb", ".rs", ".ass"]
        origin.w_preserveReferences.setVisible(preserveReferences and idx != ".abc (GPU Cache)")
        origin.w_preserveReferences.setEnabled(not exportScene or not origin.chb_importReferences.isChecked())

    @err_catcher(name=__name__)
    def sm_export_preExecute(self, origin: Any, startFrame: int, endFrame: int) -> None:
        """Pre-execute callback for export.
        
        Args:
            origin: Export state instance
            startFrame: Start frame
            endFrame: End frame
        """
        warnings = []

        # if (
        #     not origin.w_importReferences.isHidden()
        #     and origin.chb_importReferences.isChecked()
        # ):
        #     warnings.append(
        #         [
        #             "References will be imported.",
        #             "This will affect all states that will be executed after this export state. The current scenefile will be reloaded after the publish to restore the original references.",
        #             2,
        #         ]
        #     )

        # if (
        #     not origin.w_deleteUnknownNodes.isHidden()
        #     and origin.chb_deleteUnknownNodes.isChecked()
        # ):
        #     warnings.append(
        #         [
        #             "Unknown nodes will be deleted.",
        #             "This will affect all states that will be executed after this export state. The current scenefile will be reloaded after the publish to restore all original nodes.",
        #             2,
        #         ]
        #     )

        # if (
        #     not origin.w_deleteDisplayLayers.isHidden()
        #     and origin.chb_deleteDisplayLayers.isChecked()
        # ):
        #     warnings.append(
        #         [
        #             "Display layers will be deleted.",
        #             "This will affect all states that will be executed after this export state. The current scenefile will be reloaded after the publish to restore the original display layers.",
        #             2,
        #         ]
        #     )

        return warnings

    @err_catcher(name=__name__)
    def sm_export_loadData(self, origin: Any, data: Dict[str, Any]) -> None:
        """Load export state data.
        
        Args:
            origin: Export state instance
            data: State data dict
        """
        if "assetToExport" in data:
            assetIdx = None
            if isinstance(data["assetToExport"], dict):
                for idx in range(origin.cb_asset.count()):
                    itemData = origin.cb_asset.itemData(idx)
                    if itemData["objects"] == data["assetToExport"]["objects"] and itemData["entityName"] == data["assetToExport"]["entityName"]:
                        assetIdx = idx
                        break
            elif isinstance(data["assetToExport"], int):
                assetIdx = data["assetToExport"]

            if assetIdx is not None and assetIdx < origin.cb_asset.count():
                origin.cb_asset.setCurrentIndex(assetIdx)
                self.onAssetChanged(origin)

        if "importreferences" in data:
            origin.chb_importReferences.setChecked(eval(data["importreferences"]))
        if "deleteunknownnodes" in data:
            origin.chb_deleteUnknownNodes.setChecked(eval(data["deleteunknownnodes"]))
        if "deletedisplaylayers" in data:
            origin.chb_deleteDisplayLayers.setChecked(eval(data["deletedisplaylayers"]))
        if "preserveReferences" in data:
            origin.chb_preserveReferences.setChecked(eval(data["preserveReferences"]))

    @err_catcher(name=__name__)
    def sm_export_getStateProps(self, origin: Any, stateProps: Dict[str, Any]) -> None:
        """Get export state properties.
        
        Args:
            origin: Export state instance
            stateProps: Properties dict to update
        """
        stateProps.pop("connectednodes")
        stateProps.update(
            {
                "assetToExport": origin.cb_asset.currentData(),
                "importreferences": str(origin.chb_importReferences.isChecked()),
                "deleteunknownnodes": str(origin.chb_deleteUnknownNodes.isChecked()),
                "deletedisplaylayers": str(origin.chb_deleteDisplayLayers.isChecked()),
                "preserveReferences": str(origin.chb_preserveReferences.isChecked()),
            }
        )

        return stateProps

    @err_catcher(name=__name__)
    def sm_export_updateUi(self, state: Any) -> None:
        """Update export state UI.
        
        Args:
            state: Export state instance
        """
        if not hasattr(state, "cb_asset"):
            return

        state.refreshAssets(state)

    @err_catcher(name=__name__)
    def refreshAssets(self, state: Any) -> None:
        """Refresh asset list in export state.
        
        Args:
            state: Export state instance
        """
        if state.stateManager.standalone:
            return
        
        assets = [{"entityName": "", "objects": []}]
        assets += self.getAssetsFromScene()

        isSCam = state.getOutputType() == "ShotCam"
        isOtio = state.getOutputType() == ".otio"
        if len(assets) > 1 and not isSCam and not isOtio:
            state.w_asset.setHidden(False)
        else:
            state.w_asset.setHidden(True)

        if assets != getattr(state, "_cachedAssets", None):
            state._cachedAssets = assets
            cur = state.cb_asset.currentData()
            state.cb_asset.clear()
            if not state.w_asset.isHidden():
                for asset in assets:
                    state.cb_asset.addItem(asset.get("label", asset["entityName"]), asset)

            if cur:
                for idx in range(state.cb_asset.count()):
                    itemData = state.cb_asset.itemData(idx)
                    if itemData["objects"] == cur.get("objects") and itemData["entityName"] == cur.get("entityName"):
                        state.cb_asset.setCurrentIndex(idx)
                        break

            state.onAssetChanged(state)

    @err_catcher(name=__name__)
    def onAssetChanged(self, state: Any) -> None:
        """Handle asset selection change.
        
        Args:
            state: Export state instance
        """
        curAsset = state.cb_asset.currentData()
        if curAsset and curAsset.get("entityName"):
            data = state.cb_asset.currentData()
            state.clearItems()
            if data.get("objects"):
                objs = data["objects"]
            else:
                objs = data["state"].ui.nodes

            state.addObjects(objects=objs)
            state.chb_wholeScene.setChecked(False)
            state.gb_objects.setEnabled(False)
            state.w_wholeScene.setEnabled(False)
        else:
            state.w_wholeScene.setEnabled(True)
            state.gb_objects.setEnabled(True and not state.chb_wholeScene.isChecked())

        state.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def sm_render_startup(self, origin: Any) -> None:
        """Initialize render state UI.
        
        Args:
            origin: Render state instance
        """
        origin.gb_passes.setCheckable(False)
        origin.sp_rangeStart.setValue(cmds.playbackOptions(q=True, minTime=True))
        origin.sp_rangeEnd.setValue(cmds.playbackOptions(q=True, maxTime=True))

        curRender = cmds.getAttr("defaultRenderGlobals.currentRenderer")
        if curRender in ["arnold", "vray", "redshift", "renderman"]:
            if curRender == "arnold":
                driver = cmds.ls("defaultArnoldDriver")
                if not driver:
                    import mtoa.core as core
                    try:
                        core.createOptions()
                    except Exception as e:
                        logger.debug("failed to create Arnold options: %s" % e)

                driver = cmds.ls("defaultArnoldDriver")
            elif curRender == "vray":
                driver = cmds.ls("vraySettings")
            elif curRender == "redshift":
                driver = cmds.ls("redshiftOptions")
            elif curRender == "renderman":
                driver = cmds.ls("rmanGlobals")

            if not driver:
                mel.eval("RenderGlobalsWindow;")

        if hasattr(origin, "f_renderLayer"):
            origin.f_renderLayer.setVisible(True)

    @err_catcher(name=__name__)
    def getRenderLayersFromScene(self) -> List[str]:
        """Get all render layers in scene.
        
        Returns:
            List of render layer names
        """
        return [
            x
            for x in cmds.ls(type="renderLayer")
            if x in cmds.listConnections("renderLayerManager")
        ]

    @err_catcher(name=__name__)
    def sm_render_getRenderLayer(self, origin: Any) -> str:
        """Get selected render layer.
        
        Args:
            origin: Render state instance
            
        Returns:
            Render layer name
        """
        rlayers = self.getRenderLayersFromScene()
        rlayerNames = []
        for i in rlayers:
            if i == "defaultRenderLayer":
                rlayerNames.append(os.getenv("PRISM_MAYA_DFT_RENDERLAYER_NAME", "masterLayer"))
            elif i.startswith("rs_"):
                rlayerNames.append(i[3:])
            else:
                rlayerNames.append(i)

        rlayerNames += [
            "All Renderable Renderlayers",
            "All Renderable Renderlayers (separate identifiers)",
            "All Renderlayers",
            "All Renderlayers (separate identifiers)"
        ]
        return rlayerNames

    @err_catcher(name=__name__)
    def getSelectedRenderlayer(self, origin: Any) -> str:
        """Get currently selected render layer.
        
        Args:
            origin: Render state instance
            
        Returns:
            Layer name
        """
        return origin.cb_renderLayer.currentText()

    @err_catcher(name=__name__)
    def sm_render_getIdentifiers(self, origin: Any) -> List[str]:
        """Get render identifier options.
        
        Args:
            origin: Render state instance
            
        Returns:
            List of identifier strings
        """
        layer = self.getSelectedRenderlayer(origin)
        if layer == "All Renderable Renderlayers (separate identifiers)":
            rlayers = self.getRenderLayersFromScene() or []
            rrlayers = []
            for layer in rlayers:
                if cmds.getAttr("%s.renderable" % layer):
                    rrlayers.append(layer)

            rlayers = rrlayers
        elif layer == "All Renderlayers (separate identifiers)":
            rlayers = self.getRenderLayersFromScene() or []
        else:
            return

        newRLayers = []
        for rlayer in rlayers:
            if rlayer.startswith("rs_"):
                rlayer = rlayer[len("rs_"):]

            if rlayer == "defaultRenderLayer":
                rlayer = os.getenv("PRISM_MAYA_DFT_RENDERLAYER_NAME", "masterLayer")

            newRLayers.append(rlayer)

        return newRLayers

    @err_catcher(name=__name__)
    def sm_render_getLayers(self, origin: Any) -> List[str]:
        """Get available render layers.
        
        Args:
            origin: Render state instance
            
        Returns:
            List of layer names
        """
        layer = self.getSelectedRenderlayer(origin)
        if layer == "All Renderable Renderlayers":
            rlayers = self.getRenderLayersFromScene() or []
            rrlayers = []
            for layer in rlayers:
                if cmds.getAttr("%s.renderable" % layer):
                    rrlayers.append(layer)

            rlayers = rrlayers
        elif layer == "All Renderlayers":
            rlayers = self.getRenderLayersFromScene() or []
        else:
            return

        newRLayers = []
        for rlayer in rlayers:
            if rlayer.startswith("rs_"):
                rlayer = rlayer[len("rs_"):]

            if rlayer == "defaultRenderLayer":
                rlayer = os.getenv("PRISM_MAYA_DFT_RENDERLAYER_NAME", "masterLayer")

            newRLayers.append(rlayer)

        return newRLayers

    @err_catcher(name=__name__)
    def sm_render_updateUi(self, origin: Any) -> None:
        """Update render state UI.
        
        Args:
            origin: Render state instance
        """
        multipleLayers = self.getSelectedRenderlayer(origin) in ["All Renderable Renderlayers (separate identifiers)", "All Renderlayers (separate identifiers)"]
        origin.f_taskname.setEnabled(not multipleLayers)
        if multipleLayers:
            origin.setTaskWarn(False)
        else:
            origin.setTaskWarn(not bool(origin.getTaskname()))

    @err_catcher(name=__name__)
    def sm_render_refreshPasses(self, origin: Any) -> None:
        """Refresh render passes list.
        
        Args:
            origin: Render state instance
        """
        curRender = cmds.getAttr("defaultRenderGlobals.currentRenderer")
        if curRender not in ["arnold", "vray", "redshift", "renderman"]:
            origin.gb_passes.setVisible(False)
            return

        origin.gb_passes.setVisible(True)
        origin.tw_passes.clear()

        aovs = []
        if curRender == "arnold":
            driver = cmds.ls("defaultArnoldDriver")
            if not driver:
                import mtoa.core as core
                try:
                    core.createOptions()
                except Exception as e:
                    logger.debug("failed to create Arnold options: %s" % e)

            if cmds.ls("defaultArnoldRenderOptions") and cmds.attributeQuery("aovMode", node="defaultArnoldRenderOptions", exists=True) and cmds.getAttr("defaultArnoldRenderOptions.aovMode") != 0:
                aAovs = maovs.AOVInterface().getAOVNodes(names=True)
                aovs = [x[0] for x in aAovs if cmds.getAttr(x[1] + ".enabled")]
        elif curRender == "vray":
            driver = cmds.ls("vraySettings")
            if not driver:
                mel.eval("RenderGlobalsWindow;")
                driver = cmds.ls("vraySettings")

            if driver and cmds.getAttr("vraySettings.relements_enableall") != 0:
                aovs = cmds.ls(type="VRayRenderElement")
                aovs += cmds.ls(type="VRayRenderElementSet")
                aovs = [x for x in aovs if cmds.getAttr(x + ".enabled")]
        elif curRender == "redshift":
            if cmds.ls("redshiftOptions") and cmds.attributeQuery("aovGlobalEnableMode", node="redshiftOptions", exists=True) and cmds.getAttr("redshiftOptions.aovGlobalEnableMode") != 0:
                aovs = cmds.ls(type="RedshiftAOV")
                aovs = [
                    [cmds.getAttr(x + ".name"), x]
                    for x in aovs
                    if cmds.getAttr(x + ".enabled")
                ]
        elif curRender == "renderman":
            glb = cmds.ls("rmanGlobals")[0]
            size = cmds.getAttr(glb + ".displays", size=True)
            aovs = []
            for idx in range(size):
                source = cmds.connectionInfo(glb + ".displays[%s]" % idx, sourceFromDestination=True)
                if not source:
                    continue

                sourceNode = source.rsplit(".", 1)[0]
                if not cmds.getAttr(sourceNode + ".enable"):
                    continue

                dsize = cmds.getAttr(sourceNode + ".displayChannels", size=True)
                for didx in range(dsize):
                    dsource = cmds.connectionInfo(sourceNode + ".displayChannels[%s]" % didx, sourceFromDestination=True)
                    if not dsource:
                        continue

                    aovNode = dsource.rsplit(".", 1)[0]
                    if cmds.getAttr(aovNode + ".enable"):
                        aovs.append(aovNode)

        for i in aovs:
            if type(i) == list:
                item = QTreeWidgetItem([i[0]])
                item.setToolTip(0, i[1])
            else:
                item = QTreeWidgetItem([i])

            origin.tw_passes.addTopLevelItem(item)

    @err_catcher(name=__name__)
    def sm_render_openPasses(self, origin: Any, item: Optional[Any] = None) -> None:
        """Open render passes settings.
        
        Args:
            origin: Render state instance
            item: Optional list item
        """
        curRender = cmds.getAttr("defaultRenderGlobals.currentRenderer")
        if curRender == "arnold":
            tabNum = 4
        elif curRender == "vray":
            tabNum = 6
        elif curRender == "redshift":
            tabNum = 3
        elif curRender == "renderman":
            tabNum = 2

        mel.eval(
            """unifiedRenderGlobalsWindow;
int $index = 2;

string $renderer = `currentRenderer`;
if (`isDisplayingAllRendererTabs`)
$renderer = `editRenderLayerGlobals -q -currentRenderLayer`;

string $tabLayout = `getRendererTabLayout $renderer`;
tabLayout -e -sti %s $tabLayout;"""
            % tabNum
        )

    @err_catcher(name=__name__)
    def removeAOV(self, aovName: str) -> None:
        """Remove AOV/render pass.
        
        Args:
            aovName: AOV name to remove
        """
        curRender = cmds.getAttr("defaultRenderGlobals.currentRenderer")
        if curRender == "arnold":
            try:
                maovs.AOVInterface().removeAOV(aovName)
            except:
                pass
        elif curRender == "vray":
            try:
                mel.eval('vrayRemoveRenderElement "%s"' % aovName)
            except:
                pass
        elif curRender == "redshift":
            aovs = cmds.ls(type="RedshiftAOV")
            aovs = [
                x
                for x in aovs
                if cmds.getAttr(x + ".enabled") and cmds.getAttr(x + ".name") == aovName
            ]

            for a in aovs:
                try:
                    cmds.delete(a)
                except:
                    pass

        elif curRender == "renderman":
            aovs = cmds.ls(type="rmanDisplayChannel")
            aovs = [
                x
                for x in aovs
                if cmds.getAttr(x + ".enable") and x == aovName
            ]

            for a in aovs:
                try:
                    cmds.delete(a)
                except:
                    pass

    @err_catcher(name=__name__)
    def sm_render_preSubmit(self, origin: Any, rSettings: Dict[str, Any]) -> None:
        """Pre-submit callback for render.
        
        Args:
            origin: Render state instance
            rSettings: Render settings dict
        """
        rlayers = cmds.ls(type="renderLayer")
        selRenderLayer = origin.cb_renderLayer.currentText()
        if selRenderLayer in ["All Renderable Renderlayers (separate identifiers)", "All Renderlayers (separate identifiers)"]:
            selRenderLayer = rSettings["identifier"]
        elif selRenderLayer in ["All Renderable Renderlayers", "All Renderlayers"]:
            selRenderLayer = rSettings["layer"]

        if selRenderLayer == os.getenv("PRISM_MAYA_DFT_RENDERLAYER_NAME", "masterLayer"):
            stateRenderLayer = "defaultRenderLayer"
        else:
            stateRenderLayer = "rs_" + selRenderLayer
            if stateRenderLayer not in rlayers and selRenderLayer in rlayers:
                stateRenderLayer = selRenderLayer

        for cam in self.getCamNodes(origin):
            if "," not in cam:
                cmds.setAttr("%s.renderable" % cam, False)

        if origin.curCam == "Current View":
            try:
                view = OpenMayaUI.M3dView.active3dView()
                cam = api.MDagPath()
                view.getCamera(cam)
                rndCam = cam.fullPathName()
            except Exception:
                # Fallback for batch/command-line mode where no active viewport exists
                perspCams = cmds.listCameras(perspective=True) or ["persp"]
                rndCam = perspCams[0]
        else:
            rndCam = origin.curCam

        if self.isNodeValid(origin, rndCam) and "," not in rndCam:
            cmds.setAttr("%s.renderable" % rndCam, True)

        if self.core.uiAvailable:
            cmds.lookThru(rndCam)

        curLayer = cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True)

        rlayerRenderable = {}
        for i in rlayers:
            rlayerRenderable[i] = cmds.getAttr("%s.renderable" % i)
            cmds.setAttr("%s.renderable" % i, i == stateRenderLayer)

        rSettings["renderLayerRenderable"] = rlayerRenderable

        if stateRenderLayer != curLayer:
            rSettings["renderLayer"] = curLayer
            try:
                cmds.editRenderLayerGlobals(currentRenderLayer=stateRenderLayer)
            except Exception as e:
                self.core.popup("Failed to switch render layer: %s" % e)

        if origin.chb_resOverride.isChecked():
            rSettings["width"] = cmds.getAttr("defaultResolution.width")
            rSettings["height"] = cmds.getAttr("defaultResolution.height")
            cmds.setAttr("defaultResolution.width", origin.sp_resWidth.value())
            cmds.setAttr("defaultResolution.height", origin.sp_resHeight.value())

        rSettings["imageFolder"] = cmds.workspace(fileRuleEntry="images")
        rSettings["imageFilePrefix"] = cmds.getAttr(
            "defaultRenderGlobals.imageFilePrefix"
        )
        rSettings["outFormatControl"] = cmds.getAttr(
            "defaultRenderGlobals.outFormatControl"
        )
        rSettings["animation"] = cmds.getAttr("defaultRenderGlobals.animation")
        rSettings["putFrameBeforeExt"] = cmds.getAttr(
            "defaultRenderGlobals.putFrameBeforeExt"
        )
        rSettings["extpadding"] = cmds.getAttr("defaultRenderGlobals.extensionPadding")

        outputPrefix = (
            "../" + os.path.splitext(os.path.basename(rSettings["outputName"]))[0]
        )
        outputPrefix = os.path.join(os.path.dirname(outputPrefix), os.path.basename(outputPrefix).replace("#" * self.core.framePadding, ""))

        if outputPrefix[-1] == ".":
            outputPrefix = outputPrefix[:-1]

        import maya.app.renderSetup.model.renderSetup as renderSetup

        render_setup = renderSetup.instance()
        rlayers = render_setup.getRenderLayers()

        if rlayers:
            outputPrefix = "../" + outputPrefix

        cmds.workspace(fileRule=["images", os.path.dirname(rSettings["outputName"])])
        cmds.setAttr(
            "defaultRenderGlobals.imageFilePrefix", outputPrefix, type="string"
        )
        cmds.setAttr("defaultRenderGlobals.outFormatControl", 0)
        cmds.setAttr("defaultRenderGlobals.animation", rSettings["rangeType"] != "Single Frame")
        cmds.setAttr("defaultRenderGlobals.putFrameBeforeExt", 1)
        cmds.setAttr("defaultRenderGlobals.extensionPadding", 4)

        curRenderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
        imgFormat = origin.cb_format.currentText()
        if curRenderer == "arnold":
            driver = cmds.ls("defaultArnoldDriver")
            if not driver:
                import mtoa.core as core
                try:
                    core.createOptions()
                except Exception as e:
                    logger.debug("failed to create Arnold options: %s" % e)

            rSettings["ar_fileformat"] = cmds.getAttr(
                "defaultArnoldDriver.ai_translator"
            )

            if imgFormat == ".exr":
                cmds.setAttr("defaultArnoldDriver.ai_translator", "exr", type="string")
            elif imgFormat == ".png":
                cmds.setAttr("defaultArnoldDriver.ai_translator", "png", type="string")
            elif imgFormat == ".jpg":
                cmds.setAttr("defaultArnoldDriver.ai_translator", "jpeg", type="string")

            cmds.setAttr("defaultArnoldDriver.prefix", "", type="string")

            aAovs = maovs.AOVInterface().getAOVNodes(names=True)
            multichannel = cmds.getAttr("defaultArnoldDriver.mergeAOVs") == 1
            if (
                cmds.getAttr("defaultArnoldRenderOptions.aovMode") != 0
                and not multichannel
                and len(aAovs) > 0
            ):
                if len(aAovs) != 1 or "RGBA" not in aAovs[0][0]:
                    outputPrefix = "../" + outputPrefix

                cmds.setAttr(
                    "defaultRenderGlobals.imageFilePrefix", outputPrefix, type="string"
                )

                passPrefix = os.path.join("..", "..", "..")
                if not origin.gb_submit.isHidden() and origin.gb_submit.isChecked():
                    rSettings["outputName"] = os.path.join(
                        os.path.dirname(os.path.dirname(rSettings["outputName"])),
                        os.path.basename(rSettings["outputName"]),
                    )
                    passPrefix = ".."

                if len(rlayers) > 1:
                    passPrefix = os.path.join(passPrefix, "..")

                drivers = ["defaultArnoldDriver"]
                for i in aAovs:
                    if not cmds.getAttr(i[1] + ".enabled"):
                        continue

                    aDriver = cmds.connectionInfo(
                        "%s.outputs[0].driver" % i[1], sourceFromDestination=True
                    ).rsplit(".", 1)[0]
                    if aDriver in drivers or aDriver == "":
                        aDriver = cmds.createNode("aiAOVDriver", n="%s_driver" % i[0])
                        cmds.connectAttr(
                            "%s.aiTranslator" % aDriver,
                            "%s.outputs[0].driver" % i[1],
                            force=True,
                        )

                    passPath = os.path.join(
                        passPrefix, i[0], os.path.basename(outputPrefix)
                    ).replace("beauty", i[0])
                    drivers.append(aDriver)
                    cmds.setAttr(aDriver + ".prefix", passPath, type="string")
        elif curRenderer == "vray":
            driver = cmds.ls("vraySettings")
            if not driver:
                mel.eval("RenderGlobalsWindow;")

            rSettings["vr_imageFilePrefix"] = cmds.getAttr(
                "vraySettings.fileNamePrefix"
            )
            rSettings["vr_fileformat"] = cmds.getAttr("vraySettings.imageFormatStr")
            rSettings["vr_sepRGBA"] = cmds.getAttr(
                "vraySettings.relements_separateRGBA"
            )
            rSettings["vr_animation"] = cmds.getAttr("vraySettings.animType")
            rSettings["vr_dontSave"] = cmds.getAttr("vraySettings.dontSaveImage")

            multichannel = cmds.getAttr("vraySettings.imageFormatStr") in [
                "exr (multichannel)",
                "exr (deep)",
            ]
            if not multichannel or imgFormat != ".exr":
                cmds.setAttr(
                    "vraySettings.imageFormatStr", imgFormat[1:], type="string"
                )
            cmds.setAttr("vraySettings.animType", 1)
            cmds.setAttr("vraySettings.dontSaveImage", 0)

            aovs = cmds.ls(type="VRayRenderElement")
            aovs += cmds.ls(type="VRayRenderElementSet")
            aovs = [x for x in aovs if cmds.getAttr(x + ".enabled")]

            if (
                cmds.getAttr("vraySettings.relements_enableall") != 0
                and not multichannel
                and len(aovs) > 0
            ):
                if origin.cleanOutputdir:
                    try:
                        shutil.rmtree(os.path.dirname(rSettings["outputName"]))
                    except:
                        pass

                rSettings["vr_sepFolders"] = cmds.getAttr(
                    "vraySettings.relements_separateFolders"
                )
                rSettings["vr_sepStr"] = cmds.getAttr(
                    "vraySettings.fileNameRenderElementSeparator"
                )

                imgPath = os.path.dirname(os.path.dirname(rSettings["outputName"]))
                cmds.workspace(fileRule=["images", imgPath])
                if outputPrefix.startswith("../"):
                    outputPrefix = outputPrefix[3:]

                cmds.setAttr("vraySettings.fileNamePrefix", outputPrefix, type="string")
                cmds.setAttr("vraySettings.relements_separateFolders", 1)
                cmds.setAttr("vraySettings.relements_separateRGBA", 1)
                cmds.setAttr(
                    "vraySettings.fileNameRenderElementSeparator", "_", type="string"
                )
            else:
                cmds.setAttr("vraySettings.relements_separateRGBA", 0)
                outputPrefix = outputPrefix[3:]
                cmds.setAttr("vraySettings.fileNamePrefix", outputPrefix, type="string")

            if (
                not origin.gb_submit.isHidden()
                and origin.gb_submit.isChecked()
                and hasattr(origin, "chb_vrscene")
                and origin.chb_vrscene.isChecked()
                and not origin.w_vrscene.isHidden()
            ):
                rSettings["vr_vrscene_on"] = cmds.getAttr("vraySettings.vrscene_on")
                rSettings["vr_vrscene_filename"] = cmds.getAttr("vraySettings.vrscene_filename")
                rSettings["vr_vrscene_render_on"] = cmds.getAttr("vraySettings.vrscene_render_on")
                rSettings["vr_vrscene_separateFiles"] = cmds.getAttr("vraySettings.misc_eachFrameInFile")

                vrsceneOutput = os.path.join(
                    os.path.dirname(rSettings["outputName"]), "_vrscene",
                    os.path.basename(rSettings["outputName"])
                )
                vrsceneOutput = os.path.splitext(vrsceneOutput)[0] + ".vrscene"
                vrsceneOutput = vrsceneOutput.replace("\\", "/").replace("." + "#" * self.core.framePadding, "")

                cmds.setAttr("vraySettings.vrscene_on", 1)
                cmds.setAttr("vraySettings.vrscene_filename", vrsceneOutput, type="string")
                cmds.setAttr("vraySettings.vrscene_render_on", 0)
                cmds.setAttr("vraySettings.misc_eachFrameInFile", rSettings["rangeType"] != "Single Frame")

        elif curRenderer == "redshift":
            driver = cmds.ls("redshiftOptions")
            if not driver:
                mel.eval("RenderGlobalsWindow;")

            rSettings["rs_fileformat"] = cmds.getAttr("redshiftOptions.imageFormat")

            if imgFormat == ".exr":
                idx = 1
            elif imgFormat == ".png":
                idx = 2
            elif imgFormat == ".jpg":
                idx = 4
            cmds.setAttr("redshiftOptions.imageFormat", idx)

            outputPrefix = outputPrefix[3:]
            cmds.setAttr(
                "defaultRenderGlobals.imageFilePrefix", outputPrefix, type="string"
            )

            aovs = cmds.ls(type="RedshiftAOV")
            aovs = [
                [cmds.getAttr(x + ".name"), x]
                for x in aovs
                if cmds.getAttr(x + ".enabled")
            ]
            for aov in aovs:
                if cmds.getAttr(aov[1] + ".aovType") == "Beauty":
                    rSettings["outputName"] = rSettings["outputName"].replace(
                        "beauty", aov[0]
                    )

            # multichannel = cmds.getAttr("redshiftOptions.exrForceMultilayer") == 1
            if (
                cmds.getAttr("redshiftOptions.aovGlobalEnableMode") != 0
                and len(aovs) > 0
            ):
                for i in aovs:
                    cmds.setAttr(
                        i[1] + ".filePrefix",
                        "<BeautyPath>/../<RenderPass>/%s"
                        % os.path.basename(outputPrefix).replace("beauty", i[0]),
                        type="string",
                    )
        elif curRenderer == "renderman":
            driver = cmds.ls("rmanGlobals")
            if not driver:
                mel.eval("RenderGlobalsWindow;")

            curType = cmds.objectType(cmds.connectionInfo("rmanDefaultDisplay.displayType", sourceFromDestination=True))
            if imgFormat == ".exr":
                if curType not in ["d_openexr", "d_deepexr"]:
                    imgFmt = cmds.createNode("d_openexr")
                    cmds.connectAttr(
                        "%s.message" % imgFmt,
                        "rmanDefaultDisplay.displayType",
                        force=True,
                    )
            elif imgFormat == ".png":
                if curType not in ["d_png"]:
                    imgFmt = cmds.createNode("d_png")
                    cmds.connectAttr(
                        "%s.message" % imgFmt,
                        "rmanDefaultDisplay.displayType",
                        force=True,
                    )

            outputPrefix = outputPrefix[3:]
            cmds.setAttr(
                "rmanGlobals.imageFileFormat", os.path.basename(outputPrefix).replace("beauty", "<aov>") + ".<f4>.<ext>", type="string"
            )

            cmds.setAttr(
                "rmanGlobals.imageOutputDir", os.path.dirname(rSettings["outputName"]).replace("beauty", "<aov>").replace("\\", "/"), type="string"
            )
            cmds.setAttr(
                "rmanGlobals.ribOutputDir", os.path.dirname(rSettings["outputName"]).replace("\\", "/"), type="string"
            )
        else:
            rSettings["fileformat"] = cmds.getAttr("defaultRenderGlobals.imageFormat")
            if imgFormat == ".exr":
                if curRenderer in ["mayaSoftware", "mayaHardware", "mayaVector"]:
                    rndFormat = 4  # .tif
                else:
                    rndFormat = 40  # .exr
            elif imgFormat == ".png":
                rndFormat = 32
            elif imgFormat == ".jpg":
                rndFormat = 8

            cmds.setAttr("defaultRenderGlobals.imageFormat", rndFormat)

    @err_catcher(name=__name__)
    def getAdditionalRenderContext(self, origin: Any, context: Optional[Dict[str, Any]] = None, identifier: Optional[str] = None, layer: Optional[str] = None) -> Dict[str, Any]:
        """Get additional render context.
        
        Args:
            origin: Render state instance
            context: Existing context dict
            identifier: Render identifier
            layer: Render layer
            
        Returns:
            Updated context dict
        """
        selRenderLayer = origin.cb_renderLayer.currentText()
        if selRenderLayer in ["All Renderable Renderlayers (separate identifiers)", "All Renderlayers (separate identifiers)"]:
            selRenderLayer = identifier
        elif selRenderLayer in ["All Renderable Renderlayers", "All Renderlayers"]:
            selRenderLayer = layer

        if selRenderLayer == os.getenv("PRISM_MAYA_DFT_RENDERLAYER_NAME", "masterLayer"):
            return

        return {"layer": selRenderLayer}

    @err_catcher(name=__name__)
    def sm_render_startLocalRender(self, origin: Any, outputName: str, rSettings: Dict[str, Any]) -> None:
        """Start local render.
        
        Args:
            origin: Render state instance
            outputName: Output file path
            rSettings: Render settings dict
        """
        curRenderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")

        if self.core.uiAvailable:
            if curRenderer == "arnold":
                mel.eval('tearOffPanel "Render View" "renderWindowPanel" true;')
            else:
                mel.eval("RenderViewWindow;")
                mel.eval("showWindow renderViewWindow;")
                mel.eval('tearOffPanel "Render View" "renderWindowPanel" true;')
            QApplication.processEvents()

        if origin.curCam == "Current View":
            if self.core.uiAvailable:
                try:
                    view = OpenMayaUI.M3dView.active3dView()
                    cam = api.MDagPath()
                    view.getCamera(cam)
                    rndCam = cam.fullPathName()
                except Exception:
                    perspCams = cmds.listCameras(perspective=True) or ["persp"]
                    rndCam = perspCams[0]
            else:
                perspCams = cmds.listCameras(perspective=True) or ["persp"]
                rndCam = perspCams[0]
        else:
            rndCam = origin.curCam

        logger.debug("Using camera '%s' for rendering" % rndCam)
        if self.core.uiAvailable:
            editor = cmds.renderWindowEditor(q=True, editorName=True)
            if len(editor) == 0:
                editor = cmds.renderWindowEditor("renderView")
            cmds.renderWindowEditor(editor, e=True, currentCamera=rndCam)

        if rSettings["startFrame"] is None:
            frameChunks = [[x, x] for x in rSettings["frames"]]
        else:
            frameChunks = [[rSettings["startFrame"], rSettings["endFrame"]]]

        try:
            if curRenderer == "vray":
                rSettings["prev_startFrame"] = cmds.getAttr(
                    "defaultRenderGlobals.startFrame"
                )
                rSettings["prev_endFrame"] = cmds.getAttr(
                    "defaultRenderGlobals.endFrame"
                )
                rSettings["vr_animBatchOnly"] = cmds.getAttr(
                    "vraySettings.animBatchOnly"
                )
                cmds.setAttr("vraySettings.animBatchOnly", 0)

                for frameChunk in frameChunks:
                    cmds.setAttr("defaultRenderGlobals.startFrame", frameChunk[0])
                    cmds.setAttr("defaultRenderGlobals.endFrame", frameChunk[1])
                    if self.core.uiAvailable:
                        mel.eval("renderWindowRender redoPreviousRender renderView;")
                    else:
                        for i in range(int(frameChunk[0]), int(frameChunk[1]) + 1):
                            cmds.currentTime(i, edit=True)
                            cmds.render(x=True)

            elif curRenderer == "redshift":
                rSettings["prev_startFrame"] = cmds.getAttr(
                    "defaultRenderGlobals.startFrame"
                )
                rSettings["prev_endFrame"] = cmds.getAttr(
                    "defaultRenderGlobals.endFrame"
                )

                try:
                    for frameChunk in frameChunks:
                        cmds.setAttr("defaultRenderGlobals.startFrame", frameChunk[0])
                        cmds.setAttr("defaultRenderGlobals.endFrame", frameChunk[1])
                        cmds.rsRender(
                            render=True, blocking=True, animation=True, cam=rndCam
                        )
                except RuntimeError as e:
                    if str(e) == "Maya command error":
                        warnStr = "Rendering canceled: %s" % origin.state.text(0)
                        self.core.popup(warnStr)
                    else:
                        raise e

            elif curRenderer == "renderman":
                import rfm2
                for frameChunk in frameChunks:
                    rfm2.render.frame("-s %s -e %s" % (frameChunk[0], frameChunk[1]))

            elif curRenderer == "arnold":
                rSettings["prev_startFrame"] = cmds.getAttr(
                    "defaultRenderGlobals.startFrame"
                )
                rSettings["prev_endFrame"] = cmds.getAttr(
                    "defaultRenderGlobals.endFrame"
                )
                for frameChunk in frameChunks:
                    cmds.setAttr("defaultRenderGlobals.startFrame", frameChunk[0])
                    cmds.setAttr("defaultRenderGlobals.endFrame", frameChunk[1])
                    try:
                        if self.core.uiAvailable:
                            cmds.arnoldRender(seq="", saveToRenderView=True)
                        else:
                            cmds.arnoldRender(seq="")
                    except RuntimeError as e:
                        if "[mtoa] Render aborted" in str(e):
                            pass
                        else:
                            raise

            else:
                for frameChunk in frameChunks:
                    for i in range(int(frameChunk[0]), int(frameChunk[1]) + 1):
                        cmds.currentTime(i, edit=True)
                        if self.core.uiAvailable:
                            mel.eval("renderWindowRender redoPreviousRender renderView;")
                        else:
                            cmds.render(x=True)

            tmpPath = os.path.join(os.path.dirname(rSettings["outputName"]), "tmp")
            if os.path.exists(tmpPath):
                try:
                    shutil.rmtree(tmpPath)
                except:
                    pass

            if (
                os.path.exists(os.path.dirname(outputName))
                and len(os.listdir(os.path.dirname(outputName))) > 0
            ):
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
    def sm_render_undoRenderSettings(self, origin: Any, rSettings: Dict[str, Any]) -> None:
        """Restore previous render settings.
        
        Args:
            origin: Render state instance
            rSettings: Settings to restore
        """
        if "renderLayerRenderable" in rSettings:
            for i in rSettings["renderLayerRenderable"]:
                cmds.setAttr("%s.renderable" % i, rSettings["renderLayerRenderable"][i])
        if "renderLayer" in rSettings:
            try:
                cmds.editRenderLayerGlobals(currentRenderLayer=rSettings["renderLayer"])
            except Exception as e:
                self.core.popup("Failed to switch render layer: %s" % e)

        if "width" in rSettings:
            cmds.setAttr("defaultResolution.width", rSettings["width"])
        if "height" in rSettings:
            cmds.setAttr("defaultResolution.height", rSettings["height"])
        if "imageFolder" in rSettings:
            cmds.workspace(fileRule=["images", rSettings["imageFolder"]])
        if "imageFilePrefix" in rSettings:
            if rSettings["imageFilePrefix"] is None:
                prefix = ""
            else:
                prefix = rSettings["imageFilePrefix"]
            cmds.setAttr("defaultRenderGlobals.imageFilePrefix", prefix, type="string")
        if "outFormatControl" in rSettings:
            cmds.setAttr(
                "defaultRenderGlobals.outFormatControl", rSettings["outFormatControl"]
            )
        if "animation" in rSettings:
            cmds.setAttr("defaultRenderGlobals.animation", rSettings["animation"])
        if "putFrameBeforeExt" in rSettings:
            cmds.setAttr(
                "defaultRenderGlobals.putFrameBeforeExt", rSettings["putFrameBeforeExt"]
            )
        if "extpadding" in rSettings:
            cmds.setAttr(
                "defaultRenderGlobals.extensionPadding", rSettings["extpadding"]
            )
        if "fileformat" in rSettings:
            cmds.setAttr("defaultRenderGlobals.imageFormat", rSettings["fileformat"])
        if "ar_fileformat" in rSettings:
            cmds.setAttr(
                "defaultArnoldDriver.ai_translator",
                rSettings["ar_fileformat"],
                type="string",
            )
        if "vr_fileformat" in rSettings:
            cmds.setAttr(
                "vraySettings.imageFormatStr", rSettings["vr_fileformat"], type="string"
            )
        if "vr_animation" in rSettings:
            cmds.setAttr("vraySettings.animType", rSettings["vr_animation"])
        if "vr_dontSave" in rSettings:
            cmds.setAttr("vraySettings.dontSaveImage", rSettings["vr_dontSave"])
        if "prev_startFrame" in rSettings:
            cmds.setAttr(
                "defaultRenderGlobals.startFrame", rSettings["prev_startFrame"]
            )
        if "prev_endFrame" in rSettings:
            cmds.setAttr("defaultRenderGlobals.endFrame", rSettings["prev_endFrame"])
        if "vr_animBatchOnly" in rSettings:
            cmds.setAttr("vraySettings.animBatchOnly", rSettings["vr_animBatchOnly"])
        if "vr_imageFilePrefix" in rSettings:
            if rSettings["vr_imageFilePrefix"] is None:
                rSettings["vr_imageFilePrefix"] = ""
            cmds.setAttr(
                "vraySettings.fileNamePrefix",
                rSettings["vr_imageFilePrefix"],
                type="string",
            )
        if "vr_sepFolders" in rSettings:
            cmds.setAttr(
                "vraySettings.relements_separateFolders", rSettings["vr_sepFolders"]
            )
        if "vr_sepRGBA" in rSettings:
            cmds.setAttr("vraySettings.relements_separateRGBA", rSettings["vr_sepRGBA"])
        if "vr_sepStr" in rSettings:
            cmds.setAttr(
                "vraySettings.fileNameRenderElementSeparator",
                rSettings["vr_sepStr"],
                type="string",
            )
        if "vr_vrscene_on" in rSettings:
            cmds.setAttr("vraySettings.vrscene_on", rSettings["vr_vrscene_on"])
        if "vr_vrscene_filename" in rSettings:
            cmds.setAttr("vraySettings.vrscene_filename", rSettings["vr_vrscene_filename"] or "", type="string")
        if "vr_vrscene_render_on" in rSettings:
            cmds.setAttr("vraySettings.vrscene_render_on", rSettings["vr_vrscene_render_on"])
        if "vr_vrscene_separateFiles" in rSettings:
            cmds.setAttr("vraySettings.misc_eachFrameInFile", rSettings["vr_vrscene_separateFiles"])

        if "rs_fileformat" in rSettings:
            cmds.setAttr("redshiftOptions.imageFormat", rSettings["rs_fileformat"])
        if "renderSettings" in rSettings:
            self.sm_renderSettings_setCurrentSettings(
                origin, self.core.readYaml(data=rSettings["renderSettings"])
            )

    @err_catcher(name=__name__)
    def sm_render_getDeadlineParams(self, origin: Any, dlParams: Dict[str, Any], homeDir: str) -> Dict[str, Any]:
        """Get Deadline render farm parameters.
        
        Args:
            origin: Render state instance
            dlParams: Deadline parameters dict
            homeDir: Deadline home directory
            
        Returns:
            Updated parameters dict
        """
        dlParams["jobInfoFile"] = os.path.join(homeDir, "temp", "maya_submit_info.job")
        dlParams["pluginInfoFile"] = os.path.join(
            homeDir, "temp", "maya_plugin_info.job"
        )

        dlParams["jobInfos"]["Plugin"] = "MayaBatch"
        dlParams["jobInfos"]["Comment"] = "Prism-Submission-Maya_%s" % origin.className
        dlParams["pluginInfos"]["Version"] = str(cmds.about(version=True))
        dlParams["pluginInfos"]["OutputFilePath"] = os.path.split(
            dlParams["jobInfos"]["OutputFilename0"]
        )[0]
        dlParams["pluginInfos"]["OutputFilePrefix"] = os.path.splitext(
            os.path.basename(dlParams["jobInfos"]["OutputFilename0"])
        )[0].strip("#.")

        import maya.app.renderSetup.model.renderSetup as renderSetup

        render_setup = renderSetup.instance()
        rlayers = render_setup.getRenderLayers()

        if rlayers:
            prefixBase = os.path.splitext(
                os.path.basename(dlParams["jobInfos"]["OutputFilename0"])
            )[0].strip("#.")
            passName = prefixBase.split("_")[-1]
            dlParams["pluginInfos"]["OutputFilePrefix"] = os.path.join(
                "..", "..", passName, prefixBase
            )

        if hasattr(origin, "chb_resOverride") and origin.chb_resOverride.isChecked():
            resString = "Image"
            dlParams["pluginInfos"][resString + "Width"] = str(
                origin.sp_resWidth.value()
            )
            dlParams["pluginInfos"][resString + "Height"] = str(
                origin.sp_resHeight.value()
            )

        if origin.className == "Export":
            dlParams["pluginInfos"]["ScriptJob"] = "True"
            scriptPath = os.path.join(homeDir, "temp", "mayaScriptJob.py")
            dlParams["pluginInfos"]["PrismStateIndex"] = [idx for idx, s in enumerate(self.core.getStateManager().states) if s.ui == origin][0]
            dlParams["pluginInfos"]["PrismStateVersion"] = self.core.products.getVersionFromFilepath(dlParams["jobInfos"]["OutputFilename0"])
            script = self.getDeadlineScript(stateType="Export")
            with open(scriptPath, "w") as f:
                f.write(script)

            dlParams["pluginInfos"]["SceneFile"] = dlParams["arguments"][0]
            dlParams["arguments"] = []
            dlParams["arguments"].append(scriptPath)
            dlParams["pluginInfos"]["ScriptFilename"] = "mayaScriptJob.py"
            self.core.saveScene()
        elif origin.className == "Playblast":
            dlParams["pluginInfos"]["ScriptJob"] = "True"
            scriptPath = os.path.join(homeDir, "temp", "mayaScriptJob.py")
            dlParams["pluginInfos"]["PrismStateIndex"] = [idx for idx, s in enumerate(self.core.getStateManager().states) if s.ui == origin][0]
            dlParams["pluginInfos"]["PrismStateVersion"] = self.core.products.getVersionFromFilepath(dlParams["jobInfos"]["OutputFilename0"])
            script = self.getDeadlineScript("Playblast")
            with open(scriptPath, "w") as f:
                f.write(script)

            dlParams["pluginInfos"]["SceneFile"] = dlParams["arguments"][0]
            dlParams["arguments"] = []
            dlParams["arguments"].append(scriptPath)
            dlParams["pluginInfos"]["ScriptFilename"] = "mayaScriptJob.py"
            self.core.saveScene()
        else:
            dlParams["pluginInfos"]["Renderer"] = self.getCurrentRenderer(origin)
            if dlParams["pluginInfos"]["Renderer"] == "renderman":
                dlParams["pluginInfos"]["Renderer"] = "renderman22"
                dlParams["pluginInfos"]["OutputFilePrefix"] += ".<f4>.<ext>"
                dlParams["pluginInfos"]["OutputFilePrefix"] = dlParams["pluginInfos"]["OutputFilePrefix"].replace("beauty", "<aov>")
                dlParams["pluginInfos"]["OutputFilePath"] = dlParams["pluginInfos"]["OutputFilePath"].replace("beauty", "<aov>")
            elif dlParams["pluginInfos"]["Renderer"] == "vray":
                if dlParams.get("sceneDescription") != "vray":
                    multichannel = cmds.getAttr("vraySettings.imageFormatStr") in [
                        "exr (multichannel)",
                        "exr (deep)",
                    ]

                    aovs = cmds.ls(type="VRayRenderElement")
                    aovs += cmds.ls(type="VRayRenderElementSet")
                    aovs = [x for x in aovs if cmds.getAttr(x + ".enabled")]
                    if (
                        cmds.getAttr("vraySettings.relements_enableall") != 0
                        and not multichannel
                        and len(aovs) > 0
                    ):
                        dlParams["pluginInfos"]["OutputFilePath"] = os.path.split(
                            os.path.dirname(dlParams["jobInfos"]["OutputFilename0"])
                        )[0].strip("#.")

            rlayer = self.getSelectedRenderlayer(origin)
            if rlayer in ["All Renderable Renderlayers", "All Renderlayers"]:
                rlayer = dlParams["details"]["layer"]
                sceneLayers = self.getRenderLayersFromScene()
                if rlayer not in sceneLayers and ("rs_" + rlayer) in sceneLayers:
                    rlayer = "rs_" + rlayer

            if rlayer in ["All Renderable Renderlayers (separate identifiers)", "All Renderlayers (separate identifiers)"]:
                rlayer = dlParams["details"]["identifier"]
                sceneLayers = self.getRenderLayersFromScene()
                if rlayer not in sceneLayers and ("rs_" + rlayer) in sceneLayers:
                    rlayer = "rs_" + rlayer

            if rlayer == os.getenv("PRISM_MAYA_DFT_RENDERLAYER_NAME", "masterLayer"):
                rlayer = "defaultRenderLayer"

            dlParams["pluginInfos"]["RenderLayer"] = rlayer
            dlParams["pluginInfos"]["UsingRenderLayers"] = 1

            if hasattr(origin, "curCam") and origin.curCam != "Current View":
                dlParams["pluginInfos"]["Camera"] = self.core.appPlugin.getCamName(
                    origin, origin.curCam
                )

            if dlParams.get("sceneDescription") == "vray":
                self.core.saveScene()

    @err_catcher(name=__name__)
    def getDeadlineScript(self, stateType: str) -> str:
        """Get Deadline submit script path.
        
        Args:
            stateType: State type identifier
            
        Returns:
            Script file path
        """
        script = """
import sys

try:
    from PySide6.QtCore import *
    from PySide6.QtGui import *
    from PySide6.QtWidgets import *
    import shiboken6 as shiboken
except:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    import shiboken2 as shiboken

qapp = QApplication.instance()
if not qapp:
    qapp = QApplication(sys.argv)

shiboken.delete(QApplication.instance())
QApplication.instance()
QApplication([])

import PrismInit
pcore = PrismInit.prismInit(prismArgs=["noUI"])
sm = pcore.getStateManager()

import maya.mel as mel
stateIdx = mel.eval('DeadlinePluginInfo("PrismStateIndex")')
stateVersion = mel.eval('DeadlinePluginInfo("PrismStateVersion")')
state = sm.states[int(stateIdx)]
if state.ui.className != "%s":
    raise Exception("wrong state type: " + str(state.ui))

state.ui.gb_submit.setChecked(False)
result = sm.publish(executeState=True, states=[state], useVersion=stateVersion)
if not result:
    raise Exception("Errors occurred during the publish. Render failed")

print( "READY FOR INPUT\\n" )
""" % stateType
        return script

    @err_catcher(name=__name__)
    def getCurrentRenderer(self, origin: Any) -> str:
        """Get current renderer name.
        
        Args:
            origin: Originating instance
            
        Returns:
            Renderer identifier
        """
        return cmds.getAttr("defaultRenderGlobals.currentRenderer")

    @err_catcher(name=__name__)
    def getCurrentSceneFiles(self, origin: Any) -> List[str]:
        """Get current scene file paths.
        
        Args:
            origin: Originating instance
            
        Returns:
            List of file paths
        """
        curFileName = self.core.getCurrentFileName()
        if not curFileName:
            return []

        curFileBase = os.path.splitext(os.path.basename(curFileName))[0]
        xgenfiles = [
            os.path.join(os.path.dirname(curFileName), x)
            for x in os.listdir(os.path.dirname(curFileName))
            if x.startswith(curFileBase) and os.path.splitext(x)[1] in [".xgen", "abc"]
        ]
        scenefiles = [curFileName] + xgenfiles
        return scenefiles

    @err_catcher(name=__name__)
    def sm_render_getRenderPasses(self, origin: Any) -> List[str]:
        """Get available render passes.
        
        Args:
            origin: Render state instance
            
        Returns:
            List of pass names
        """
        curRender = self.getCurrentRenderer(origin)
        if curRender == "vray":
            return self.core.getConfig(
                "defaultpasses", "maya_vray", configPath=self.core.prismIni
            )
        elif curRender == "arnold":
            return self.core.getConfig(
                "defaultpasses", "maya_arnold", configPath=self.core.prismIni
            )
        elif curRender == "redshift":
            return self.core.getConfig(
                "defaultpasses", "maya_redshift", configPath=self.core.prismIni
            )
        elif curRender == "renderman":
            return self.core.getConfig(
                "defaultpasses", "maya_renderman", configPath=self.core.prismIni
            )

    @err_catcher(name=__name__)
    def sm_render_addRenderPass(self, origin: Any, passName: str, steps: List[str]) -> None:
        """Add render pass/AOV.
        
        Args:
            origin: Render state instance
            passName: Pass name
            steps: Render steps
        """
        curRender = self.getCurrentRenderer(origin)
        if curRender == "vray":
            mel.eval("vrayAddRenderElement %s;" % steps[passName])
        elif curRender == "arnold":
            maovs.AOVInterface().addAOV(passName)
        elif curRender == "redshift":
            cmds.rsCreateAov(type=passName)
            try:
                mel.eval("redshiftUpdateActiveAovList;")
            except:
                pass
        elif curRender == "renderman":
            print("not implemented")

    @err_catcher(name=__name__)
    def sm_render_preExecute(self, origin: Any) -> None:
        """Pre-execute callback for render.
        
        Args:
            origin: Render state instance
        """
        warnings = []

        if platform.system() == "Windows":
            curRenderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
            if curRenderer == "vray":
                driver = cmds.ls("vraySettings")
                if not driver:
                    mel.eval("RenderGlobalsWindow;")

                multichannel = cmds.getAttr("vraySettings.imageFormatStr") in [
                    "exr (multichannel)",
                    "exr (deep)",
                ]

                aovs = cmds.ls(type="VRayRenderElement")
                aovs += cmds.ls(type="VRayRenderElementSet")
                aovs = [x for x in aovs if cmds.getAttr(x + ".enabled")]
                tooLong = 0
                longestAovPath = ""
                if (
                    cmds.getAttr("vraySettings.relements_enableall") != 0
                    and not multichannel
                    and len(aovs) > 0
                ):
                    for aov in aovs:
                        attrNames = cmds.listAttr(aov)
                        for attrName in attrNames:
                            if attrName.startswith("vray_name_"):
                                aovName = cmds.getAttr(aov + "." + attrName)
                                outputName = origin.getOutputName()[0]
                                aovPath = outputName.replace("rgba", aovName)
                                aovPath = (
                                    os.path.splitext(aovPath)[0]
                                    + "_"
                                    + aovName
                                    + "."
                                    + "#" * self.core.framePadding
                                    + os.path.splitext(aovPath)[1]
                                )
                                if len(aovPath) > 259 and len(aovPath) > tooLong:
                                    tooLong = len(aovPath)
                                    longestAovPath = aovPath

                if tooLong:
                    warning = [
                        "AOV path is too long",
                        "The outputpath of one AOV is longer than 259 characters. This might cause that it cannot be saved to disk.\n%s (%s)"
                        % (longestAovPath, tooLong),
                        2,
                    ]
                    warnings.append(warning)

            elif curRenderer == "renderman":
                if origin.cb_format.currentText() == ".jpg":
                    warning = [
                        "Output format .jpg is not supported in Renderman",
                        "Prism cannot set the output format to .jpg. The output format, which is currently set in the Remderman settings will be used.",
                        2,
                    ]
                    warnings.append(warning)

        renderCams = [cam for cam in cmds.ls(type="camera") if cmds.getAttr(cam + ".renderable")]
        if len(renderCams) > 1:
            warning = [
                "Multiple renderable cameras",
                "This can cause that the output files get written to an unintended directory. Make sure there is only one camera set as renderable in the Maya render settings.",
                2,
            ]
            warnings.append(warning)

        return warnings

    @err_catcher(name=__name__)
    def sm_render_fixOutputPath(self, origin: Any, outputName: str, singleFrame: bool = False, state: Optional[Any] = None) -> str:
        """Fix and standardize output path.
        
        Args:
            origin: Origin instance
            outputName: Output file path
            singleFrame: Single frame render
            state: Optional state instance
            
        Returns:
            Corrected output path
        """
        curRender = self.getCurrentRenderer(origin)

        if curRender == "vray":
            aovs = cmds.ls(type="VRayRenderElement")
            aovs += cmds.ls(type="VRayRenderElementSet")
            aovs = [x for x in aovs if cmds.getAttr(x + ".enabled")]
            multichannel = cmds.getAttr("vraySettings.imageFormatStr") in [
                "exr (multichannel)",
                "exr (deep)",
            ]
            if (
                cmds.getAttr("vraySettings.relements_enableall") != 0
                and not multichannel
                and len(aovs) > 0
            ):
                outputName = outputName.replace("_beauty", "")

            outputName = outputName.replace("beauty", "rgba")

        return outputName

    @err_catcher(name=__name__)
    def getProgramVersion(self, origin: Optional[Any] = None) -> str:
        """Get renderer version string.
        
        Args:
            origin: Optional originating instance
            
        Returns:
            Version string
        """
        return cmds.about(version=True)

    @err_catcher(name=__name__)
    def deleteNodes(self, origin: Any, handles: List[str], num: int = 0) -> None:
        """Delete nodes from scene.
        
        Args:
            origin: Originating instance
            handles: List of node handles
            num: Internal recursion counter
        """
        if (num + 1) > len(handles):
            return False

        if self.isNodeValid(origin, handles[num]) and (
            cmds.referenceQuery(handles[num], isNodeReferenced=True)
            or cmds.objectType(handles[num]) == "reference"
        ):
            try:
                refNode = cmds.referenceQuery(
                    handles[num], referenceNode=True, topReference=True
                )
                fileName = cmds.referenceQuery(refNode, filename=True)
            except:
                self.deleteNodes(origin, handles, num + 1)
                return False

            cmds.file(fileName, removeReference=True)
        else:
            for i in handles:
                if not self.isNodeValid(origin, i):
                    continue

                try:
                    cmds.delete(i)
                except RuntimeError as e:
                    if "Cannot delete locked node" in str(e):
                        try:
                            refNode = cmds.referenceQuery(
                                i, referenceNode=True, topReference=True
                            )
                            fileName = cmds.referenceQuery(refNode, filename=True)
                            cmds.file(fileName, removeReference=True)
                        except:
                            pass
                    else:
                        raise e

    @err_catcher(name=__name__)
    def sm_import_startup(self, origin: Any) -> None:
        """Initialize import state UI.
        
        Args:
            origin: Import state instance
        """
        origin.b_connectRefNode = QPushButton("Connect selected reference node")
        origin.b_connectRefNode.clicked.connect(lambda: self.connectRefNode(origin))
        origin.gb_import.layout().addWidget(origin.b_connectRefNode)
        origin.l_abcPath.setText("Update Path Only:")

    @err_catcher(name=__name__)
    def sm_import_updateUi(self, origin: Any) -> None:
        """Update import state UI.
        
        Args:
            origin: Import state instance
        """
        base, ext = os.path.splitext(origin.getImportPath() or "")
        showUpdatePath = ext.lower() in [".ass"]
        origin.f_abcPath.setHidden(not showUpdatePath)

    @err_catcher(name=__name__)
    def connectRefNode(self, origin: Any) -> None:
        """Connect reference node to import state.
        
        Args:
            origin: Import state instance
        """
        selection = cmds.ls(selection=True)
        if len(selection) == 0:
            QMessageBox.warning(self.core.messageParent, "Warning", "Nothing selected")
            return

        if not (
            cmds.referenceQuery(selection[0], isNodeReferenced=True)
            or cmds.objectType(selection[0]) == "reference"
        ):
            QMessageBox.warning(
                self.core.messageParent,
                "Warning",
                "%s is not a reference node" % selection[0],
            )
            return

        refNode = cmds.referenceQuery(
            selection[0], referenceNode=True, topReference=True
        )

        if len(origin.nodes) > 0:
            msg = QMessageBox(
                QMessageBox.Question,
                "Connect node",
                "This state is already connected to existing nodes. Do you want to continue and disconnect the current nodes?",
                QMessageBox.Cancel,
            )
            msg.addButton("Continue", QMessageBox.YesRole)
            msg.setParent(self.core.messageParent, Qt.Window)
            action = msg.exec_()

            if action != 0:
                return

        scenePath = cmds.referenceQuery(refNode, filename=True)
        origin.setImportPath(scenePath)
        self.deleteNodes(origin, [origin.setName])

        origin.chb_trackObjects.setChecked(True)
        origin.nodes = [refNode]
        setName = os.path.splitext(os.path.basename(scenePath))[0]
        name = self.getSetPrefix() + "Import_%s" % setName
        if self.isNodeValid(origin, name, isSet=True):
            name += "_1"

        origin.setName = cmds.sets(name=name)
        for i in origin.nodes:
            cmds.sets(i, include=origin.setName)

        origin.updateUi()

    @err_catcher(name=__name__)
    def sm_import_disableObjectTracking(self, origin: Any) -> bool:
        """Check if object tracking should be disabled.
        
        Args:
            origin: Import state instance
            
        Returns:
            True if tracking disabled
        """
        self.deleteNodes(origin, [origin.setName])

    @err_catcher(name=__name__)
    def sm_import_importToApp(self, origin: Any, doImport: bool, update: bool, impFileName: str, settings: Optional[Dict[str, Any]] = None) -> Any:
        """Import file into Maya.
        
        Args:
            origin: Import state instance
            doImport: Perform import
            update: Update existing import
            impFileName: File to import
            settings: Optional import settings
            
        Returns:
            Import result data
        """
        if not os.path.exists(impFileName):
            msg = "File doesn't exist:\n\n%s" % impFileName
            self.core.popup(msg)
            return

        fileName = os.path.splitext(os.path.basename(impFileName))
        base, ext = fileName
        importOnly = True
        applyCache = False
        updateCache = False
        doGpuCache = False
        importedNodes = []
        mergeNamespacesOnClash = False
        cacheData = None

        if fileName[1] in [".ma", ".mb", ".abc"]:
            validNodes = [x for x in origin.nodes if self.isNodeValid(origin, x)]
            if (
                not update
                and len(validNodes) > 0
                and (
                    cmds.referenceQuery(validNodes[0], isNodeReferenced=True)
                    or cmds.objectType(validNodes[0]) == "reference"
                )
                and origin.chb_keepRefEdits.isChecked()
            ):
                refNode = cmds.referenceQuery(
                    validNodes[0], referenceNode=True, topReference=True
                )
                msg = QMessageBox(
                    QMessageBox.Question,
                    "Create Reference",
                    "Do you want to replace the current reference?",
                    QMessageBox.No,
                )
                msg.addButton("Yes", QMessageBox.YesRole)
                msg.setParent(self.core.messageParent, Qt.Window)
                action = msg.exec_()

                if action == 0:
                    update = True
                else:
                    origin.preDelete(
                        baseText="Do you want to delete the currently connected objects?\n\n"
                    )
                    importedNodes = []

            validNodes = [x for x in origin.nodes if self.isNodeValid(origin, x)]
            if not update or len(validNodes) == 0:
                settings = settings or {}
                # default settings
                mode = settings.get("mode", "reference")
                applyCacheTarget = settings.get("applyCacheTarget", "selection")
                curEntity = self.core.getCurrentScenefileData()
                dftUseNameSpace = False if curEntity.get("type") == "asset" else True
                useNamespace = settings.get("useNamespace", dftUseNameSpace)

                if "namespace" in settings:
                    namespaceTemplate = settings["namespace"]
                else:
                    namespaceTemplate = "{entity}_{task}"
                    namespaceTemplate = self.core.getConfig(
                        "globals",
                        "defaultMayaNamespace",
                        dft=namespaceTemplate,
                        configPath=self.core.prismIni,
                    )

                cacheData = self.core.paths.getCachePathData(impFileName)
                if cacheData.get("type") == "asset":
                    cacheData["entity"] = cacheData.get("asset_path", "")
                    cacheData["asset"] = os.path.basename(cacheData.get("asset_path", ""))
                    cacheData["shot"] = ""
                elif cacheData.get("type") == "shot":
                    cacheData["entity"] = self.core.entities.getShotName(cacheData)
                    cacheData["asset"] = ""
                    cacheData["shot"] = cacheData.get("shot", "")

                try:
                    namespace = namespaceTemplate.format(**cacheData)
                    namespace = os.path.basename(namespace)
                except:
                    namespace = ""
                    useNamespace = False

                if self.core.uiAvailable and settings.get("showGui", True) and not settings.get("quiet", False):
                    refDlg = QDialog()

                    refDlg.setWindowTitle("Create Reference")
                    rb_reference = QRadioButton("Create Reference")
                    rb_reference.setChecked(mode == "reference")
                    rb_import = QRadioButton("Import Objects Only")
                    rb_import.setChecked(mode == "import")
                    rb_applyCache = QRadioButton("Apply As Cache")
                    w_caches = QWidget()
                    lo_caches = QVBoxLayout(w_caches)
                    lo_caches.setContentsMargins(20, 9, 9, 9)
                    rb_applyCacheSelection = QRadioButton("To Selection")
                    rb_applyCacheEntity = QRadioButton("To Asset")
                    w_applyCacheEntities = QWidget()
                    lo_applyCacheEntities = QHBoxLayout(w_applyCacheEntities)
                    lo_applyCacheEntities.setContentsMargins(20, 0, 0, 0)
                    cb_cacheEntities = QComboBox()
                    lo_applyCacheEntities.addWidget(cb_cacheEntities)
                    lo_applyCacheEntities.addStretch()
                    lo_caches.addWidget(rb_applyCacheSelection)
                    lo_caches.addWidget(rb_applyCacheEntity)
                    lo_caches.addWidget(w_applyCacheEntities)
                    rb_gpuCache = QRadioButton("Load As GPU Cache")
                    rb_gpuCache.setChecked(mode == "applyCache")
                    w_namespace = QWidget()
                    nLayout = QHBoxLayout()
                    nLayout.setContentsMargins(0, 15, 0, 0)
                    chb_namespace = QCheckBox("Create Namespace")
                    chb_namespace.setChecked(useNamespace)
                    e_namespace = QLineEdit()
                    e_namespace.setText(namespace)
                    e_namespace.setEnabled(useNamespace)
                    nLayout.addWidget(chb_namespace)
                    nLayout.addWidget(e_namespace)
                    chb_namespace.toggled.connect(lambda x: e_namespace.setEnabled(x))
                    w_namespace.setLayout(nLayout)

                    w_caches.setEnabled(False)
                    w_applyCacheEntities.setEnabled(False)
                    entities = self.getAssetsFromScene()
                    for entity in entities:
                        name = entity["entityName"]
                        if entity.get("stateName") and len([x["entityName"] for x in entities if x["entityName"] == name]) > 1:
                            name = entity["stateName"]

                        if entity.get("objects"):
                            objs = entity["objects"]
                        else:
                            objs = entity["state"].ui.nodes

                        if objs:
                            name += " (%s)" % objs[0]

                        cb_cacheEntities.addItem(name, entity)

                    rb_applyCache.toggled.connect(
                        lambda x: w_namespace.setEnabled(not x)
                    )
                    rb_applyCache.toggled.connect(
                        lambda x: w_caches.setEnabled(x)
                    )
                    rb_applyCacheEntity.toggled.connect(
                        lambda x: w_applyCacheEntities.setEnabled(x)
                    )

                    rb_applyCacheSelection.setChecked(True)
                    rb_applyCacheEntity.setChecked(len(cmds.ls(selection=True)) == 0 and cb_cacheEntities.count())

                    if fileName[1] != ".abc":
                        rb_applyCache.setEnabled(False)

                    rb_gpuCache.toggled.connect(lambda x: w_namespace.setEnabled(not x))
                    if fileName[1] != ".abc":
                        rb_gpuCache.setEnabled(False)

                    bb_warn = QDialogButtonBox()
                    bb_warn.addButton("Ok", QDialogButtonBox.AcceptRole)
                    bb_warn.addButton("Cancel", QDialogButtonBox.RejectRole)

                    bb_warn.accepted.connect(refDlg.accept)
                    bb_warn.rejected.connect(refDlg.reject)

                    bLayout = QVBoxLayout()
                    bLayout.addWidget(rb_reference)
                    bLayout.addWidget(rb_import)
                    bLayout.addWidget(rb_applyCache)
                    bLayout.addWidget(w_caches)
                    bLayout.addWidget(rb_gpuCache)
                    bLayout.addWidget(w_namespace)
                    bLayout.addWidget(bb_warn)
                    refDlg.setLayout(bLayout)
                    refDlg.setParent(self.core.messageParent, Qt.Window)
                    refDlg.resize(400, 100)

                    action = refDlg.exec_()

                    if action == 0:
                        doRef = False
                        importOnly = False
                        applyCache = False
                        return {"result": "canceled", "doImport": doImport}
                    else:
                        doRef = rb_reference.isChecked()
                        applyCache = rb_applyCache.isChecked()
                        applyCacheTarget = "selection" if rb_applyCacheSelection.isChecked() else cb_cacheEntities.currentData()
                        doGpuCache = rb_gpuCache.isChecked()
                        if chb_namespace.isChecked():
                            nSpace = e_namespace.text()
                        else:
                            nSpace = ":"
                else:
                    doRef = mode == "reference"
                    applyCache = mode == "applyCache"
                    doGpuCache = mode == "gpuCache"
                    if useNamespace:
                        nSpace = namespace
                    else:
                        nSpace = ":"
            else:
                doRef = (
                    cmds.referenceQuery(validNodes[0], isNodeReferenced=True)
                    or cmds.objectType(validNodes[0]) == "reference"
                )
                doGpuCache = bool(
                    [
                        node
                        for node in origin.nodes
                        if cmds.objectType(node) == "gpuCache"
                    ]
                )
                if ":" in validNodes[0]:
                    nSpace = [obj for obj in validNodes[0].split("|") if obj][0].rsplit(":", 1)[0]
                    mergeNamespacesOnClash = True
                else:
                    nSpace = ":"

                updateCache = origin.stateMode == "ApplyCache"

            if fileName[1] == ".ma":
                rtype = "mayaAscii"
            elif fileName[1] == ".mb":
                rtype = "mayaBinary"
            elif fileName[1] == ".abc":
                rtype = "Alembic"

            if updateCache:
                cmds.select(origin.setName)
                cmds.AbcImport(
                    impFileName,
                    mode="import",
                    connect=" ".join(cmds.ls(selection=True, long=True)),
                )
                importedNodes = cmds.ls(selection=True, long=True)
            elif doRef:
                validNodes = [x for x in origin.nodes if self.isNodeValid(origin, x)]
                if (
                    len(validNodes) > 0
                    and (
                        cmds.referenceQuery(validNodes[0], isNodeReferenced=True)
                        or cmds.objectType(validNodes[0]) == "reference"
                    )
                    and origin.chb_keepRefEdits.isChecked()
                ):
                    self.deleteNodes(origin, [origin.setName])
                    refNode = ""
                    for validNode in validNodes:
                        try:
                            refNode = cmds.referenceQuery(
                                validNode, referenceNode=True, topReference=True
                            )
                            break
                        except:
                            pass

                    oldFname = cmds.referenceQuery(refNode, filename=True)
                    try:
                        oldNs = cmds.referenceQuery(refNode, namespace=True)
                    except:
                        refPath = cmds.referenceQuery(refNode, filename=True)
                        oldNs = cmds.file(refPath, q=True, namespace=True)

                    oldf = os.path.splitext(os.path.basename(oldFname))[0].replace(
                        "-", "_"
                    )
                    cmds.file(impFileName, loadReference=refNode)
                    if oldNs == (":" + oldf):
                        newNs = fileName[0].replace("-", "_")
                        cmds.file(impFileName, e=True, namespace=newNs)

                    importedNodes = [refNode]
                else:
                    origin.preDelete(
                        baseText="Do you want to delete the currently connected objects?\n\n"
                    )
                    if nSpace == "new":
                        nSpace = fileName[0]

                    impFileName = self.getPathRelativeToProject(impFileName) if self.getUseRelativePath() else impFileName
                    try:
                        newNodes = cmds.file(
                            impFileName,
                            reference=True,
                            returnNewNodes=True,
                            type=rtype,
                            mergeNamespacesOnClash=False,
                            namespace=nSpace,
                        )
                    except RuntimeError as e:
                        msg = "Failed to create reference:\n\n%s\n\n%s" % (impFileName, str(e))
                        self.core.popup(msg)
                        return {"result": False, "doImport": doImport}

                    refNode = ""
                    for i in newNodes:
                        try:
                            refNode = cmds.referenceQuery(
                                i, referenceNode=True, topReference=True
                            )
                            break
                        except:
                            pass
                    importedNodes = [refNode]

            elif doGpuCache:
                if update:
                    gpuNode = [
                        node
                        for node in origin.nodes
                        if cmds.objectType(node) == "gpuCache"
                    ][0]
                    importedNodes = self.updateGpuCache(
                        gpuNode, impFileName, name=fileName[0]
                    )
                else:
                    origin.preDelete(
                        baseText="Do you want to delete the currently connected objects?\n\n"
                    )                
                    namespaceTemplate = "{entity}_{task}"
                    namespaceTemplate = self.core.getConfig(
                        "globals",
                        "defaultMayaNamespace",
                        dft=namespaceTemplate,
                        configPath=self.core.prismIni,
                    )

                    if not cacheData:
                        cacheData = self.core.paths.getCachePathData(impFileName)

                    if cacheData.get("type") == "asset":
                        cacheData["entity"] = cacheData.get("asset_path", "")
                        cacheData["asset"] = os.path.basename(cacheData.get("asset_path", ""))
                        cacheData["shot"] = ""
                    elif cacheData.get("type") == "shot":
                        cacheData["entity"] = self.core.entities.getShotName(cacheData)
                        cacheData["asset"] = ""
                        cacheData["shot"] = cacheData.get("shot", "")

                    try:
                        name = namespaceTemplate.format(**cacheData)
                        name = os.path.basename(name)
                    except:
                        name = fileName[0]

                    importedNodes = (
                        self.createGpuCache(impFileName, name=name) or []
                    )

            elif importOnly:
                origin.preDelete(
                    baseText="Do you want to delete the currently connected objects?\n\n"
                )
                if nSpace == "new":
                    nSpace = fileName[0]

                if applyCache:
                    objs = None
                    if applyCacheTarget == "selection":
                        if len(cmds.ls(selection=True)) == 0:
                            self.core.popup("No objects selected.")
                            return {"result": "canceled", "doImport": doImport}
                        else:
                            if update:
                                cmds.select(origin.setName)
                            objs = cmds.ls(selection=True, long=True)
                    elif applyCacheTarget:
                        prevSel = cmds.ls(selection=True, long=True)
                        cmds.select(clear=True)
                        if applyCacheTarget.get("objects"):
                            objs = applyCacheTarget["objects"]
                        else:
                            objs = applyCacheTarget["state"].ui.nodes

                        try:
                            # the nodes in the set need to be selected to get their long dag path
                            cmds.select(objs)
                        except:
                            pass

                        objs = cmds.ls(selection=True, long=True)
                        cmds.select(clear=True)
                        try:
                            cmds.select(prevSel)
                        except:
                            pass

                    if objs:
                        newObjs = []
                        for obj in objs:
                            if cmds.objectType(obj) == "reference":
                                newObjs += self.getNodesFromReference(obj)
                            else:
                                newObjs.append(obj)

                        newObjs = [
                            x for x in newObjs if "dagNode" in cmds.nodeType(x, inherited=True)
                        ]
                        objs = newObjs
                        logger.debug("applying alembic: %s - to objects: %s" % (impFileName, objs))
                        cmds.AbcImport(
                            impFileName,
                            mode="import",
                            connect=" ".join(objs),
                        )
                        importedNodes = objs
                    else:
                        msg = "Invalid entity selected."
                        self.core.popup(msg)
                        return {"result": "canceled", "doImport": doImport}

                else:
                    importedNodes = cmds.file(
                        impFileName,
                        i=True,
                        returnNewNodes=True,
                        type=rtype,
                        mergeNamespacesOnClash=mergeNamespacesOnClash,
                        namespace=nSpace,
                    )

            importOnly = False

        otioResult = None
        if importOnly:
            if (fileName[1] not in self.importHandlers or not self.importHandlers[fileName[1]].get("handlesUpdate")) and fileName[1] not in [".ass"]:
                origin.preDelete(
                    baseText="Do you want to delete the currently connected objects?\n\n"
                )

            import maya.mel as mel

            if ext == ".otio":
                otioResult = self.importSequencerOtio(impFileName)
                importedNodes = []
            elif ext == ".rs":
                if hasattr(cmds, "rsProxy"):
                    objName = os.path.basename(impFileName).split(".")[0]
                    importedNodes = mel.eval(
                        'redshiftDoCreateProxy("%sProxy", "%sShape", "", "", "%s");'
                        % (objName, objName, impFileName.replace("\\", "\\\\"))
                    )
                    if len(os.listdir(os.path.dirname(impFileName))) > 2:
                        for node in importedNodes:
                            if cmds.attributeQuery(
                                "useFrameExtension", n=node, exists=True
                            ):
                                cmds.setAttr(node + ".useFrameExtension", 1)
                            # 	seqName = impFileName[:-7] + "####.rs"
                            # 	cmds.setAttr(node + ".fileName", seqName, type="string")
                else:
                    self.core.popup("Format is not supported, because Redshift is not available in Maya.")
                    importedNodes = []

            elif fileName[1] == ".vdb":
                try:
                    import mtoa
                except:
                    self.core.popup("Format is not supported, because Arnold is not available in Maya.")
                    importedNodes = []
                else:
                    objName = os.path.basename(impFileName).split(".")[0]
                    importedNodes = [cmds.createNode('aiVolume', n=objName)]

                    cmds.setAttr(importedNodes[0] + ".filename", impFileName, type="string")
                    if len(os.listdir(os.path.dirname(impFileName))) > 2:
                        for node in importedNodes:
                            if cmds.attributeQuery(
                                "useFrameExtension", n=node, exists=True
                            ):
                                cmds.setAttr(node + ".useFrameExtension", 1)

            else:
                doImport = True
                if fileName[1] == ".fbx":
                    mel.eval("FBXImportMode -v merge")
                    mel.eval("FBXImportConvertUnitString  -v cm")
                elif fileName[1] == ".atom":
                    cmds.loadPlugin("atomImportExport.mll", quiet=True)
                    settings = settings or {}
                    settings["type"] = "atomImport"
                    settings["options"] = "targetTime=3;match=hierarchy;selected=childrenToo"
                elif fileName[1] == ".ass":
                    if origin.chb_abcPath.isChecked() and len(origin.nodes) > 0:
                        standins = [x for x in origin.nodes if cmds.objectType(x) == "aiStandIn"]
                        if standins:
                            cmds.setAttr(standins[0] + ".dso", impFileName, type="string")
                            doImport = False
                            importedNodes = origin.nodes

                    if doImport:
                        origin.preDelete(
                            baseText="Do you want to delete the currently connected objects?\n\n"
                        )

                if doImport:
                    kwargs = {
                        "i": True,
                        "returnNewNodes": True,
                        "importFunction": self.basicImport,
                        "settings": settings,
                        "update": update,
                        "origin": origin,
                    }

                    if fileName[1] in self.importHandlers:
                        kwargs.update(self.importHandlers[fileName[1]])

                    if "handlesUpdate" in kwargs:
                        del kwargs["handlesUpdate"]

                    result = kwargs["importFunction"](impFileName, kwargs)

                    if result and result["result"]:
                        importedNodes = result["nodes"]
                    else:
                        importedNodes = []
                        if result:
                            if "error" not in result:
                                return

                            error = str(result["error"])
                        else:
                            error = ""

                        msg = "An error occured while importing the file:\n\n%s\n\n%s" % (
                            impFileName,
                            error,
                        )
                        self.core.popup(msg, title="Import error")

        cams = cmds.listCameras()
        for i in importedNodes:
            if i in cams:
                cmds.camera(i, e=True, farClipPlane=1000000)

        if origin.chb_trackObjects.isChecked():
            origin.nodes = importedNodes
        else:
            origin.nodes = []

        # buggy
        # cmds.select([ x for x in origin.nodes if self.isNodeValid(origin, x)])
        self.validateSet(origin.setName)
        if self.isNodeValid(self, origin.setName):
            cmds.delete(origin.setName)

        if len(origin.nodes) > 0:
            name = self.getSetPrefix() + "Import_%s" % fileName[0]
            if self.isNodeValid(origin, name, isSet=True):
                name += "_1"

            origin.setName = cmds.sets(name=name)
            for node in origin.nodes:
                try:
                    cmds.sets(node, include=origin.setName)
                except Exception as e:
                    logger.warning("Couldn't add node %s to set %s: %s" % (node, origin.setName, e))

                if settings and settings.get("lookThroughCam"):
                    if cmds.objectType(node) == "reference":
                        snodes = self.getNodesFromReference(node)
                    else:
                        snodes = [node]

                    for snode in snodes:
                        if cmds.nodeType(snode) == "camera":
                            cmds.lookThru(snode)

        result = (len(importedNodes) > 0) or (ext in [".otio"] and otioResult)
        rDict = {"result": result, "doImport": doImport}
        rDict["mode"] = "ApplyCache" if (applyCache or updateCache) else "ImportFile"

        return rDict

    @err_catcher(name=__name__)
    def getAssetsFromScene(self, allowCache: bool = True) -> List[Dict[str, Any]]:
        """Get all assets in current scene.

        Args:
            allowCache: Whether to return cached assets
        
        Returns:
            List of asset info dicts
        """
        if allowCache and self.assetsInScene is not None:
            return self.assetsInScene

        entities = []
        curData = self.core.getCurrentScenefileData()
        if curData and curData.get("type") == "asset" and curData.get("asset_path"):
            entity = os.path.basename(curData.get("asset_path", ""))
            obj = "|" + entity
            if self.isNodeValid(None, obj):
                entities.append({"entityName": entity, "objects": [obj], "label": entity + " (from scene)"})

            try:
                matches = cmds.ls("*:" + entity.replace(" ", "_").replace("(", "_").replace(")", "_"), long=True) or []
            except RuntimeError:
                matches = []

            matches = [m for m in matches if m.count("|") == 1]
            for match in matches:
                entities.append({"entityName": entity, "objects": [match], "label": match.strip("|") + " (from scene)"})

        for state in self.core.getStateManager().states:
            if state.ui.className == "ImportFile":
                entity = None
                cacheData = self.core.paths.getCachePathData(state.ui.getImportPath())
                if cacheData.get("type") == "asset":
                    entity = os.path.basename(cacheData.get("asset_path", ""))
                elif cacheData.get("type") == "shot":
                    shotName = self.core.entities.getShotName(cacheData)
                    if shotName:
                        entity = shotName

                if entity:
                    objs = state.ui.nodes
                    if len(objs) == 1 and os.getenv("PRISM_MAYA_USE_GEO_FROM_ASSET_REFERENCES", "1") == "1":
                        if not self.isNodeValid(None, objs[0]):
                            continue

                        if cacheData.get("type") == "asset" and curData.get("type") == "shot" and cmds.objectType(objs[0]) == "reference":
                            refObjs = self.getNodesFromReference(objs[0])
                            if not refObjs:
                                continue

                            refObjs = [
                                x for x in refObjs if "dagNode" in cmds.nodeType(x, inherited=True)
                            ]
                            geoName = os.getenv("PRISM_MAYA_GEO_NAME", "geo")
                            if "{ENTITY_NAME}" in geoName:
                                geoName = geoName.replace("{ENTITY_NAME}", entity)

                            for refObj in refObjs:
                                geoObjs = cmds.listRelatives(refObj, fullPath=True) or []
                                for geoObj in geoObjs:
                                    if fnmatch.fnmatch(geoObj.split(":")[-1].split("|")[-1], geoName):
                                        objs = [geoObj]

                    duplicate = False
                    for curEntity in entities:
                        if curEntity["entityName"] == entity and curEntity["objects"] == objs:
                            duplicate = True

                    if duplicate:
                        continue

                    entities.append({"entityName": entity, "stateName": state.text(0), "state": state, "objects": objs, "label": entity + " (" + state.text(0) + ")"})

        self.assetsInScene = entities
        return entities

    @err_catcher(name=__name__)
    def getNodesFromReference(self, node: str) -> List[str]:
        """Get nodes from reference.
        
        Args:
            node: Reference node name
            
        Returns:
            List of nodes in reference
        """
        try:
            newObjs = cmds.referenceQuery(node, nodes=True, dagPath=True) or []
        except:
            newObjs = []

        subObjs = []
        for newObj in newObjs:
            if cmds.objectType(newObj) == "reference":
                subObjs += self.getNodesFromReference(newObj)

        newObjs += subObjs
        return newObjs

    @err_catcher(name=__name__)
    def basicImport(self, filepath: str, kwargs: Optional[Dict[str, Any]] = None) -> List[str]:
        """Perform basic file import.
        
        Args:
            filepath: File to import
            kwargs: Optional import parameters
            
        Returns:
            List of imported nodes
        """
        kwargs = kwargs or {}
        if "importFunction" in kwargs:
            del kwargs["importFunction"]

        if "settings" in kwargs:
            del kwargs["settings"]

        if "update" in kwargs:
            del kwargs["update"]

        if "origin" in kwargs:
            del kwargs["origin"]

        try:
            importedNodes = cmds.file(filepath, **kwargs)
        except Exception as e:
            result = {"result": False, "error": e}
            return result

        result = {"result": True, "nodes": importedNodes}
        return result

    @err_catcher(name=__name__)
    def createGpuCache(self, filepath: str, geoPath: str = "|", name: Optional[str] = None) -> str:
        """Create GPU cache node.
        
        Args:
            filepath: Cache file path
            geoPath: Geometry path in cache
            name: Optional node name
            
        Returns:
            Created node name
        """
        cmds.loadPlugin("gpuCache.mll", quiet=True)
        parent = cmds.createNode("transform", name=name)
        node = cmds.createNode("gpuCache", parent=parent)
        cmds.setAttr(node + ".cacheFileName", filepath, type="string")
        cmds.setAttr(node + ".cacheGeomPath", geoPath, type="string")
        return [parent, node]

    @err_catcher(name=__name__)
    def updateGpuCache(self, node: str, filepath: str, geoPath: str = "|", name: Optional[str] = None) -> None:
        """Update GPU cache node.
        
        Args:
            node: Cache node name
            filepath: New cache file path
            geoPath: Geometry path in cache
            name: Optional new node name
        """
        nodes = [node]
        cmds.setAttr(node + ".cacheFileName", filepath, type="string")
        cmds.setAttr(node + ".cacheGeomPath", geoPath, type="string")
        if name:
            parent = cmds.ls(node, long=True)[0].rsplit("|", 1)[0]
            renamedParent = cmds.rename(parent, name)
            nodes = [renamedParent]
            nodes += (cmds.listRelatives(renamedParent) or [])
        return nodes

    @err_catcher(name=__name__)
    def validateSet(self, setName: str) -> str:
        """Validate and correct set name.
        
        Args:
            setName: Set name to validate
            
        Returns:
            Validated set name
        """
        if not self.isNodeValid(self, setName):
            return

        members = cmds.sets(setName, q=True)
        if not members:
            return

        empty = True
        for member in members:
            if cmds.objectType(member) != "shadingEngine":
                empty = False

        if empty:
            for member in members:
                cmds.delete(member)

    @err_catcher(name=__name__)
    def sm_import_updateObjects(self, origin: Any) -> None:
        """Update imported objects list.
        
        Args:
            origin: Import state instance
        """
        if origin.setName == "":
            return

        prevSel = cmds.ls(selection=True, long=True)
        cmds.select(clear=True)
        try:
            # the nodes in the set need to be selected to get their long dag path
            cmds.select(origin.setName)
        except:
            pass

        origin.nodes = cmds.ls(selection=True, long=True)
        try:
            cmds.select(prevSel)
        except:
            pass

    @err_catcher(name=__name__)
    def sm_import_removeNameSpaces(self, origin: Any) -> None:
        """Remove namespaces from imported objects.
        
        Args:
            origin: Import state instance
        """
        for i in origin.nodes:
            if not self.isNodeValid(origin, i):
                continue

            nodeName = self.getNodeName(origin, i)
            newName = nodeName.rsplit(":", 1)[-1]

            if newName != nodeName and not (
                cmds.referenceQuery(i, isNodeReferenced=True)
                or cmds.objectType(i) == "reference"
            ):
                try:
                    cmds.rename(nodeName, newName)
                except:
                    pass

        origin.updateUi()

    @err_catcher(name=__name__)
    def getPreferredResolutionGate(self) -> str:
        """Get preferred camera resolution gate.
        
        Returns:
            Resolution gate setting
        """
        return "Fill" if os.getenv("PRISM_MAYA_RES_GATE", "").lower() == "fill" else "Horizontal"

    @err_catcher(name=__name__)
    def sm_playblast_startup(self, origin: Any) -> None:
        """Initialize playblast state UI.
        
        Args:
            origin: Playblast state instance
        """
        if hasattr(origin, "gb_submit"):
            origin.gb_submit.setVisible(True)

        frange = self.getFrameRange(origin)
        origin.sp_rangeStart.setValue(frange[0])
        origin.sp_rangeEnd.setValue(frange[1])

        origin.w_useRecommendedSettings = QWidget()
        origin.lo_useRecommendedSettings = QHBoxLayout()
        origin.lo_useRecommendedSettings.setContentsMargins(9, 0, 9, 0)
        origin.w_useRecommendedSettings.setLayout(origin.lo_useRecommendedSettings)
        origin.l_useRecommendedSettings = QLabel("Use recommended Settings:")
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Expanding)
        origin.chb_useRecommendedSettings = QCheckBox()
        origin.chb_useRecommendedSettings.setChecked(True)
        origin.lo_useRecommendedSettings.addWidget(origin.l_useRecommendedSettings)
        origin.lo_useRecommendedSettings.addSpacerItem(spacer)
        origin.lo_useRecommendedSettings.addWidget(origin.chb_useRecommendedSettings)
        resGate = self.getPreferredResolutionGate()
        self.playblastSettings["filmFit"] = 0 if resGate == "Fill" else 1
        origin.w_useRecommendedSettings.setToolTip(
            """Recommended playblast settings:
Fit Resolution Gate: %s
Display Film Gate: False
Display Resolution: False
Overscan: 1.0
Show only polygon objects, plugin shapes and image planes in viewport.
""" % resGate
        )

        origin.gb_playblast.layout().insertWidget(5, origin.w_useRecommendedSettings)
        origin.chb_useRecommendedSettings.stateChanged.connect(
            origin.stateManager.saveStatesToScene
        )
        origin.cb_formats.addItem(".png")
        origin.cb_formats.addItem(".mp4 (with audio)")
        if platform.system() == "Windows":
            origin.cb_formats.addItem(".avi (with audio)")

        origin.cb_formats.addItem(".qt (with audio)")

    @err_catcher(name=__name__)
    def sm_playblast_loadData(self, origin: Any, data: Dict[str, Any]) -> None:
        """Load playblast state data.
        
        Args:
            origin: Playblast state instance
            data: State data dict
        """
        if "useRecommendedSettings" in data:
            origin.chb_useRecommendedSettings.setChecked(
                eval(data["useRecommendedSettings"])
            )

    @err_catcher(name=__name__)
    def sm_playblast_getStateProps(self, origin: Any) -> Dict[str, Any]:
        """Get playblast state properties.
        
        Args:
            origin: Playblast state instance
            
        Returns:
            Properties dict
        """
        stateProps = {
            "useRecommendedSettings": str(origin.chb_useRecommendedSettings.isChecked())
        }

        return stateProps

    @err_catcher(name=__name__)
    def prePlayblast(self, **kwargs: Any) -> None:
        """Pre-playblast callback.
        
        Args:
            **kwargs: Playblast parameters
        """
        tmpOutputName = os.path.splitext(kwargs["outputpath"])[0].rstrip("#")
        tmpOutputName = tmpOutputName.strip(".")

        outputName = None
        selFmt = kwargs["state"].cb_formats.currentText()
        if selFmt == ".avi (with audio)":
            outputName = tmpOutputName + ".avi"
        elif selFmt == ".qt (with audio)":
            outputName = tmpOutputName + ".mov"
        elif selFmt == ".mp4 (with audio)":
            outputName = tmpOutputName + (".avi" if os.getenv("PRISM_MAYA_PLAYBLAST_MP4_SOURCE_FMT", "avi") == "avi" else ".mov")
        else:
            if not os.path.splitext(kwargs["outputpath"])[0].endswith("#"):
                outputName = (
                    os.path.splitext(kwargs["outputpath"])[0]
                    + "."
                    + "#" * self.core.framePadding
                    + os.path.splitext(kwargs["outputpath"])[1]
                )

            if selFmt == ".png":
                outputName = os.path.splitext(kwargs["outputpath"])[0] + ".png"
        
        if outputName and outputName != kwargs["outputpath"]:
            return {"outputName": outputName}

    @err_catcher(name=__name__)
    def sm_playblast_createPlayblast(self, origin: Any, jobFrames: List[int], outputName: str, useAvi: bool = False) -> None:
        """Create playblast video/images.
        
        Args:
            origin: Playblast state instance
            jobFrames: Frame range list
            outputName: Output file path
            useAvi: Use AVI format on Windows
        """
        self.pbSceneSettings = {}
        if self.core.uiAvailable:
            if origin.curCam is not None and self.isNodeValid(origin, origin.curCam):
                cmds.lookThru(origin.curCam)
                pbCam = origin.curCam
            else:
                view = OpenMayaUI.M3dView.active3dView()
                cam = api.MDagPath()
                view.getCamera(cam)
                pbCam = cam.fullPathName()

            self.pbSceneSettings["pbCam"] = pbCam

            if origin.chb_useRecommendedSettings.isChecked() and self.isNodeValid(None, pbCam) and "," not in pbCam:
                self.pbSceneSettings["filmFit"] = cmds.getAttr(pbCam + ".filmFit")
                self.pbSceneSettings["filmGate"] = cmds.getAttr(
                    pbCam + ".displayFilmGate"
                )
                self.pbSceneSettings["resGate"] = cmds.getAttr(
                    pbCam + ".displayResolution"
                )
                self.pbSceneSettings["overscan"] = cmds.getAttr(pbCam + ".overscan")

                vpName = cmds.getPanel(type="modelPanel")[-1]
                self.pbSceneSettings[
                    "visObjects"
                ] = 'string $editorName = "modelPanel4";\n' + cmds.modelEditor(
                    vpName, q=True, stateString=True
                )

                try:
                    cmds.setAttr(pbCam + ".filmFit", self.playblastSettings["filmFit"])
                except:
                    pass

                try:
                    cmds.setAttr(
                        pbCam + ".displayFilmGate",
                        self.playblastSettings["displayFilmGate"],
                    )
                except:
                    pass

                try:
                    cmds.setAttr(
                        pbCam + ".displayResolution",
                        self.playblastSettings["displayResolution"],
                    )
                except:
                    pass

                try:
                    cmds.setAttr(
                        pbCam + ".overscan", self.playblastSettings["overscan"]
                    )
                except:
                    pass

                if os.getenv("PRISM_MAYA_SET_VISIBLE_OBJECT_TYPES", True) in [True, "1", "True"]:
                    cmds.modelEditor(vpName, e=True, allObjects=False)
                    cmds.modelEditor(vpName, e=True, polymeshes=True)
                    cmds.modelEditor(vpName, e=True, pluginShapes=True)
                    cmds.modelEditor(vpName, e=True, imp=True)

        # set image format to jpeg
        cmds.setAttr(
            "defaultRenderGlobals.imageFormat", self.playblastSettings["imageFormat"]
        )
        outputName = os.path.splitext(outputName)[0].rstrip("#")
        outputName = outputName.strip(".")

        selFmt = origin.cb_formats.currentText()
        if selFmt == ".avi (with audio)":
            fmt = "avi"
            outputName += ".avi"
        elif selFmt == ".qt (with audio)":
            fmt = "qt"
            outputName += ".mov"
        elif selFmt == ".mp4 (with audio)":
            if os.getenv("PRISM_MAYA_PLAYBLAST_MP4_SOURCE_FMT", "avi") == "avi" or useAvi:
                fmt = "avi"
                outputName += ".avi"
            else:
                fmt = "qt"
                outputName += ".mov"
        else:
            fmt = "image"

        showOrnaments = os.getenv("PRISM_MAYA_SHOW_ORNAMENTS", "True")
        aPlayBackSliderPython = mel.eval("$tmpVar=$gPlayBackSlider")
        soundNode = cmds.timeControl(aPlayBackSliderPython, query=True, sound=True)

        cmdString = 'cmds.playblast( startTime=%s, endTime=%s, format="%s", percent=100, viewer=False, forceOverwrite=True, offScreen=True, showOrnaments=%s, filename="%s", sound="%s"' % (
            jobFrames[0],
            jobFrames[1],
            fmt,
            showOrnaments,
            outputName.replace("\\", "\\\\"),
            soundNode,
        )
        res = None
        if origin.chb_resOverride.isChecked():
            res = {"width": origin.sp_resWidth.value(), "height": origin.sp_resHeight.value()}
            cmdString += ", width=%s, height=%s" % (res["width"], res["height"])
        else:
            if origin.cb_formats.currentText() in [".mp4", ".mp4 (with audio)"]:
                res = self.getViewportResolution()
                if not self.isViewportResolutionEven(res):
                    evenRes = self.getEvenViewportResolution(res)
                    cmdString += ", width=%s, height=%s" % (
                        evenRes["width"],
                        evenRes["height"],
                    )
                    logger.debug("using even resolution to be able to convert to mp4")

        if selFmt == ".png":
            cmdString += ", compression=\"png\""
        elif fmt == "avi":
            useIyuv = os.getenv("PRISM_MAYA_PLAYBLAST_COMPRESSION", "IYUV") == "IYUV"
            if res and (res["width"] > 2048 or res["height"] > 2048):
                useIyuv = False

            if useIyuv:
                cmpr = "iyuv"
            else:
                cmpr = "none"

            cmdString += ", compression=\"%s\"" % cmpr

        cmdString += ")"
        cmds.currentTime(jobFrames[0], edit=True)
        logger.debug("running cmd: %s" % cmdString)
        try:
            eval(cmdString)
        except Exception as e:
            logger.warning(e)

        if len(os.listdir(os.path.dirname(outputName))) < 2 and fmt == "qt":
            if selFmt == ".mp4 (with audio)":
                return self.sm_playblast_createPlayblast(origin, jobFrames, outputName, useAvi=True)
            else:
                self.core.popup(
                    "Couldn't create quicktime video. Make sure quicktime is installed on your system and try again."
                )
        else:
            if selFmt == ".mp4 (with audio)":
                mp4path = os.path.splitext(outputName)[0] + ".mp4"
                result = self.core.media.convertMedia(outputName, 0, mp4path)
                try:
                    os.remove(outputName)
                except:
                    logger.warning("failed to remove file: %s" % outputName)

                outputName = mp4path
            
            if fmt != "image":
                origin.updateLastPath(outputName)

    @err_catcher(name=__name__)
    def captureViewportThumbnail(self) -> Optional[Any]:
        """Capture viewport as thumbnail.
        
        Returns:
            QPixmap thumbnail or None
        """
        if cmds.about(batch=True):
            return

        path = tempfile.NamedTemporaryFile(suffix=".jpg").name
        curFrame = int(cmds.currentTime(query=True))
        res = self.getViewportResolution()
        cmds.playblast(fr=curFrame, v=False, fmt="image", c="jpg", orn=True, cf=path, wh=[res["width"], res["height"]], p=100)
        pm = self.core.media.getPixmapFromPath(path)
        try:
            os.remove(path)
        except:
            pass

        return pm

    @err_catcher(name=__name__)
    def getViewFromName(self, viewportName: str) -> Optional[Any]:
        """Get Maya view from viewport name.
        
        Args:
            viewportName: Viewport name
            
        Returns:
            M3dView object or None
        """
        view = OpenMayaUI.M3dView()
        OpenMayaUI.M3dView.getM3dViewFromModelEditor(viewportName, view)
        return view

    @err_catcher(name=__name__)
    def getViewportResolution(self, view: Optional[Any] = None) -> Tuple[int, int]:
        """Get viewport resolution.
        
        Args:
            view: Optional M3dView, uses active if None
            
        Returns:
            (width, height) tuple
        """
        if not view:
            view = OpenMayaUI.M3dView.active3dView()
        width = view.portWidth()
        height = view.portHeight()
        return {"width": width, "height": height}

    @err_catcher(name=__name__)
    def isViewportResolutionEven(self, resolution: Tuple[int, int]) -> bool:
        """Check if resolution dimensions are even.
        
        Args:
            resolution: (width, height) tuple
            
        Returns:
            True if both even
        """
        evenRes = self.getEvenViewportResolution(resolution)
        return evenRes == resolution

    @err_catcher(name=__name__)
    def getEvenViewportResolution(self, resolution: Tuple[int, int]) -> Tuple[int, int]:
        """Round resolution to even dimensions.
        
        Args:
            resolution: (width, height) tuple
            
        Returns:
            (width_even, height_even) tuple
        """
        if resolution["width"] % 2:
            width = resolution["width"] - 1
        else:
            width = resolution["width"]

        if resolution["height"] % 2:
            height = resolution["height"] - 1
        else:
            height = resolution["height"]

        return {"width": width, "height": height}

    @err_catcher(name=__name__)
    def sm_playblast_preExecute(self, origin: Any) ->  None:
        """Pre-execute callback for playblast.
        
        Args:
            origin: Playblast state instance
        """
        self.pbSceneSettings = {}
        warnings = []

        if (
            hasattr(origin, "chb_resOverride")
            and not origin.chb_resOverride.isChecked()
        ):
            res = self.getViewportResolution()
            if not self.isViewportResolutionEven(res):
                if origin.cb_formats.currentText() == ".mp4":
                    warning = [
                        "Viewport resolution is not even",
                        "The resolution for mp4 files has to be even. The playblast resolution will be adjusted to be even.",
                        2,
                    ]
                else:
                    warning = [
                        "Viewport resolution is not even",
                        "Creating .jpg files with uneven resolution cannot be converted to mp4 videos later on.",
                        2,
                    ]
                warnings.append(warning)

        return warnings

    @err_catcher(name=__name__)
    def sm_playblast_execute(self, origin: Any) -> None:
        """Execute playblast.
        
        Args:
            origin: Playblast state instance
        """
        pass

    @err_catcher(name=__name__)
    def sm_playblast_postExecute(self, origin: Any) -> None:
        """Post-execute callback for playblast.
        
        Args:
            origin: Playblast state instance
        """
        if not hasattr(self, "pbSceneSettings"):
            return

        if "filmFit" in self.pbSceneSettings:
            try:
                cmds.setAttr(
                    self.pbSceneSettings["pbCam"] + ".filmFit",
                    self.pbSceneSettings["filmFit"],
                )
            except:
                pass
        if "filmGate" in self.pbSceneSettings:
            try:
                cmds.setAttr(
                    self.pbSceneSettings["pbCam"] + ".displayFilmGate",
                    self.pbSceneSettings["filmGate"],
                )
            except:
                pass
        if "resGate" in self.pbSceneSettings:
            try:
                cmds.setAttr(
                    self.pbSceneSettings["pbCam"] + ".displayResolution",
                    self.pbSceneSettings["resGate"],
                )
            except:
                pass
        if "overscan" in self.pbSceneSettings:
            try:
                cmds.setAttr(
                    self.pbSceneSettings["pbCam"] + ".overscan",
                    self.pbSceneSettings["overscan"],
                )
            except:
                pass
        if "visObjects" in self.pbSceneSettings:
            try:
                mel.eval(self.pbSceneSettings["visObjects"])
            except:
                pass

    @err_catcher(name=__name__)
    def onStateManagerOpen(self, origin: Any) -> None:
        """Handle State Manager open event.
        
        Args:
            origin: State Manager instance
        """
        origin.f_import.setStyleSheet("QFrame { border: 0px solid rgb(150,150,150); }")
        origin.f_export.setStyleSheet("QFrame { border: 0px solid rgb(68,68,68); }")
        origin.setStyleSheet("QScrollArea { border: 0px solid rgb(150,150,150); }")

        if hasattr(cmds, "rsProxy") and ".rs" not in self.plugin.outputFormats:
            self.plugin.outputFormats.insert(-1, ".rs")
        elif not hasattr(cmds, "rsProxy") and ".rs" in self.plugin.outputFormats:
            self.plugin.outputFormats.pop(self.plugin.outputFormats.index(".rs"))

        try:
            import arnold
            arnoldAvailable = True
        except:
            arnoldAvailable = False

        if arnoldAvailable and ".ass" not in self.plugin.outputFormats:
            self.plugin.outputFormats.insert(-1, ".ass")
        elif not arnoldAvailable and ".ass" in self.plugin.outputFormats:
            self.plugin.outputFormats.pop(self.plugin.outputFormats.index(".ass"))

        otioAvailable = int(self.getAppVersion(None)) >= 20270100
        if otioAvailable and ".otio" not in self.plugin.outputFormats:
            self.plugin.outputFormats.insert(-1, ".otio")
        elif not otioAvailable and ".otio" in self.plugin.outputFormats:
            self.plugin.outputFormats.pop(self.plugin.outputFormats.index(".otio"))

        try:
            cmds.loadPlugin("gpuCache.mll", quiet=True)
            gpuCacheAvailable = cmds.pluginInfo("gpuCache.mll", q=True, loaded=True)
        except Exception:
            gpuCacheAvailable = False

        if gpuCacheAvailable and ".abc (GPU Cache)" not in self.plugin.outputFormats:
            self.plugin.outputFormats.insert(-1, ".abc (GPU Cache)")
        elif not gpuCacheAvailable and ".abc (GPU Cache)" in self.plugin.outputFormats:
            self.plugin.outputFormats.pop(self.plugin.outputFormats.index(".abc (GPU Cache)"))

        if not self.core.smCallbacksRegistered:
            import maya.OpenMaya as api

            saveCallback = api.MSceneMessage.addCallback(
                api.MSceneMessage.kAfterSave, self.core.scenefileSaved
            )

            newCallback = api.MSceneMessage.addCallback(
                api.MSceneMessage.kBeforeNew, self.core.sceneUnload
            )

            loadCallback = api.MSceneMessage.addCallback(
                api.MSceneMessage.kBeforeOpen, self.core.sceneUnload
            )

        self.assetsInScene = None
        for state in origin.states:
            if state.ui.className == "Export":
                state._cachedAssets = None

    @err_catcher(name=__name__)
    def sm_saveStates(self, origin: Any, buf: Any) -> None:
        """Save State Manager states to scene.
        
        Args:
            origin: State Manager instance
            buf: State data buffer
        """
        cmds.fileInfo("PrismStates", buf)
        cmds.file(modified=True)

    @err_catcher(name=__name__)
    def sm_saveImports(self, origin: Any, importPaths: List[str]) -> None:
        """Save import paths to scene.
        
        Args:
            origin: State Manager instance
            importPaths: List of import paths
        """
        cmds.fileInfo("PrismImports", importPaths)
        cmds.file(modified=True)

    @err_catcher(name=__name__)
    def sm_readStates(self, origin: Any) -> Optional[str]:
        """Read states from scene.
        
        Args:
            origin: State Manager instance
            
        Returns:
            State data string or None
        """
        val = cmds.fileInfo("PrismStates", query=True)
        if len(val) != 0:
            if sys.version[0] == "2":
                stateStr = val[0].decode("string_escape")
            else:
                stateStr = str.encode(val[0]).decode("unicode_escape")

            # for backwards compatibility with scenes created before v1.3.0
            jsonData = self.core.configs.readJson(data=stateStr)
            if not jsonData:
                try:
                    stateStr = eval('"%s"' % val[0].replace("\\\\", "\\"))
                except Exception as e:
                    self.core.popup("Failed to load states from scene: %s" % e)
                    return

            return stateStr

    @err_catcher(name=__name__)
    def sm_deleteStates(self, origin: Any) -> None:
        """Delete states from scene.
        
        Args:
            origin: State Manager instance
        """
        val = cmds.fileInfo("PrismStates", query=True)
        if len(val) != 0:
            cmds.fileInfo(remove="PrismStates")

    @err_catcher(name=__name__)
    def onStateCreated(self, origin: Any, state: Any, stateData: Dict[str, Any]) -> None:
        """Handle state creation event.
        
        Args:
            origin: State Manager instance
            state: Created state instance
            stateData: State data dict
        """
        if state.className in ["Export"]:
            data = self.core.getCurrentScenefileData()
            additionalSettingsValues = {}
            settings = origin.getDefaultStateSettingsForContext(state.className, data)
            if settings and settings.get("stateData"):
                additionalSettingsValues.update(copy.deepcopy(settings.get("stateData", {}).get("additionalSettings", {})))

            abcSettings = []
            additionalSettingsValues.update((stateData or {}).get("additionalSettings") or {})

            abcSettings += [
                {
                    "name": "abcStep",
                    "label": "Step",
                    "type": "float",
                    "value": 1.0 if "abcStep" not in additionalSettingsValues else additionalSettingsValues["abcStep"],
                    "visible": lambda dlg, state: state.getOutputType() in [".abc"]
                },
                {
                    "name": "abcNoNormals",
                    "label": "No Normals",
                    "type": "checkbox",
                    "value": False if "abcNoNormals" not in additionalSettingsValues else additionalSettingsValues["abcNoNormals"],
                    "visible": lambda dlg, state: state.getOutputType() in [".abc"]
                },
                {
                    "name": "abcRenderableOnly",
                    "label": "Renderable Only",
                    "type": "checkbox",
                    "value": False if "abcRenderableOnly" not in additionalSettingsValues else additionalSettingsValues["abcRenderableOnly"],
                    "visible": lambda dlg, state: state.getOutputType() in [".abc"]
                },
                {
                    "name": "abcStripNamespaces",
                    "label": "Strip Namespaces",
                    "type": "checkbox",
                    "value": True if "abcStripNamespaces" not in additionalSettingsValues else additionalSettingsValues["abcStripNamespaces"],
                    "visible": lambda dlg, state: state.getOutputType() in [".abc"]
                },
                {
                    "name": "abcUvWrite",
                    "label": "UV Write",
                    "type": "checkbox",
                    "value": True if "abcUvWrite" not in additionalSettingsValues else additionalSettingsValues["abcUvWrite"],
                    "visible": lambda dlg, state: state.getOutputType() in [".abc"]
                },
                {
                    "name": "abcWriteColorSets",
                    "label": "Write Color Sets",
                    "type": "checkbox",
                    "value": False if "abcWriteColorSets" not in additionalSettingsValues else additionalSettingsValues["abcWriteColorSets"],
                    "visible": lambda dlg, state: state.getOutputType() in [".abc"]
                },
                {
                    "name": "abcWriteFaceSets",
                    "label": "Write Face Sets",
                    "type": "checkbox",
                    "value": False if "abcWriteFaceSets" not in additionalSettingsValues else additionalSettingsValues["abcWriteFaceSets"],
                    "visible": lambda dlg, state: state.getOutputType() in [".abc"]
                },
                {
                    "name": "abcWholeFrameGeo",
                    "label": "Whole Frame Geo",
                    "type": "checkbox",
                    "value": False if "abcWholeFrameGeo" not in additionalSettingsValues else additionalSettingsValues["abcWholeFrameGeo"],
                    "visible": lambda dlg, state: state.getOutputType() in [".abc"]
                },
                {
                    "name": "abcWorldSpace",
                    "label": "World Space",
                    "type": "checkbox",
                    "value": True if "abcWorldSpace" not in additionalSettingsValues else additionalSettingsValues["abcWorldSpace"],
                    "visible": lambda dlg, state: state.getOutputType() in [".abc"]
                },
                {
                    "name": "abcWriteVisibility",
                    "label": "Write Visibility",
                    "type": "checkbox",
                    "value": True if "abcWriteVisibility" not in additionalSettingsValues else additionalSettingsValues["abcWriteVisibility"],
                    "visible": lambda dlg, state: state.getOutputType() in [".abc"]
                },
                {
                    "name": "abcFilterEulerRotations",
                    "label": "Filter Euler Rotations",
                    "type": "checkbox",
                    "value": True if "abcFilterEulerRotations" not in additionalSettingsValues else additionalSettingsValues["abcFilterEulerRotations"],
                    "visible": lambda dlg, state: state.getOutputType() in [".abc"]
                },
                {
                    "name": "abcWriteCreases",
                    "label": "Write Creases",
                    "type": "checkbox",
                    "value": False if "abcWriteCreases" not in additionalSettingsValues else additionalSettingsValues["abcWriteCreases"],
                    "visible": lambda dlg, state: state.getOutputType() in [".abc"]
                },
                {
                    "name": "abcWriteUvSets",
                    "label": "Write UV Sets",
                    "type": "checkbox",
                    "value": True if "abcWriteUvSets" not in additionalSettingsValues else additionalSettingsValues["abcWriteUvSets"],
                    "visible": lambda dlg, state: state.getOutputType() in [".abc"]
                },
                {
                    "name": "includeHistory",
                    "label": "Include History",
                    "type": "checkbox",
                    "value": True if "includeHistory" not in additionalSettingsValues else additionalSettingsValues["includeHistory"],
                    "visible": lambda dlg, state: state.getOutputType() in [".ma", ".mb"]
                },
                {
                    "name": "includeChannels",
                    "label": "Include Channels",
                    "type": "checkbox",
                    "value": True if "includeChannels" not in additionalSettingsValues else additionalSettingsValues["includeChannels"],
                    "visible": lambda dlg, state: state.getOutputType() in [".ma", ".mb"]
                },
                {
                    "name": "includeConstraints",
                    "label": "Include Constraints",
                    "type": "checkbox",
                    "value": True if "includeConstraints" not in additionalSettingsValues else additionalSettingsValues["includeConstraints"],
                    "visible": lambda dlg, state: state.getOutputType() in [".ma", ".mb"]
                },
                {
                    "name": "includeExpressions",
                    "label": "Include Expressions",
                    "type": "checkbox",
                    "value": True if "includeExpressions" not in additionalSettingsValues else additionalSettingsValues["includeExpressions"],
                    "visible": lambda dlg, state: state.getOutputType() in [".ma", ".mb"]
                },
                {
                    "name": "includeShader",
                    "label": "Include Shader",
                    "type": "checkbox",
                    "value": True if "includeShader" not in additionalSettingsValues else additionalSettingsValues["includeShader"],
                    "visible": lambda dlg, state: state.getOutputType() in [".ma", ".mb"]
                },
                {
                    "name": "removeNamespaces",
                    "label": "Remove Namespaces",
                    "type": "checkbox",
                    "value": False if "removeNamespaces" not in additionalSettingsValues else additionalSettingsValues["removeNamespaces"],
                    "visible": lambda dlg, state: state.getOutputType() in [".ma", ".mb"]
                },
            ]
            state.additionalSettings += abcSettings
            if (not stateData) and state.cb_asset.count() > 1 and os.getenv("PRISM_MAYA_EXPORT_AUTO_SET_ASSET", "1") == "1":
                state.cb_asset.setCurrentIndex(1)
                self.onAssetChanged(state)

    @err_catcher(name=__name__)
    def onGenerateStateNameContext(self, origin: Any, cacheData: Dict[str, Any]) -> None:
        if not origin.nodes:
            return

        obj = origin.nodes[0]
        cacheData["object"] = self.getNodeName(origin, obj)
        try:
            if cmds.referenceQuery(obj, isNodeReferenced=True) or cmds.objectType(obj) == "reference":
                nameSpace = cmds.referenceQuery(obj, namespace=True)
            else:
                nameSpace = cmds.namespaceInfo(obj, fn=True)
        except:
            nameSpace = ""

        cacheData["nameSpace"] = nameSpace.strip(":") if nameSpace else ""

    @err_catcher(name=__name__)
    def sm_getExternalFiles(self, origin: Any) -> List[List[Any]]:
        """Get external files referenced in scene.
        
        Args:
            origin: State Manager instance
            
        Returns:
            [files_list, sources_list]
        """
        prjPath = cmds.workspace(fullName=True, query=True)
        if prjPath.endswith(":"):
            prjPath += "/"

        prjPath = os.path.join(prjPath, "untitled")
        extFiles = []
        for path in cmds.file(query=True, list=True, withoutCopyNumber=True):
            if not path:
                continue

            if self.core.fixPath(path) == self.core.fixPath(prjPath):
                continue

            extFiles.append(self.core.fixPath(path))

        return [extFiles, []]

    @err_catcher(name=__name__)
    def postBuildScene(self, **kwargs: Any) -> None:
        """Post-build scene callback.
        
        Args:
            **kwargs: Build parameters
        """
        curRenderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
        if curRenderer == "arnold":
            driver = cmds.ls("defaultArnoldDriver")
            if not driver:
                try:
                    import mtoa.core as core
                except ModuleNotFoundError:
                    logger.debug("mtoa module not found, skipping Arnold options creation")
                    return

                try:
                    core.createOptions()
                except Exception as e:
                    logger.debug("failed to create Arnold options: %s" % e)

                driver = cmds.ls("defaultArnoldDriver")

            if driver:
                if os.getenv("PRISM_MAYA_ARNOLD_SET_HALF_PRECISION", "1") == "1":
                    cmds.setAttr("defaultArnoldDriver.halfPrecision", 1)  # 16 bit

                if os.getenv("PRISM_MAYA_ARNOLD_SET_EXR_COMPRESSION", "1") == "1":
                    cmds.setAttr("defaultArnoldDriver.exrCompression", 3)  # ZIP compression

        elif curRenderer not in ["vray", "redshift", "renderman"]:
            if os.getenv("PRISM_MAYA_SET_HALF_PRECISION", "1") == "1":
                cmds.setAttr("defaultRenderGlobals.exrPixelType", 1)  # 16 bit

            if os.getenv("PRISM_MAYA_SET_EXR_COMPRESSION", "1") == "1":
                cmds.setAttr("defaultRenderGlobals.exrCompression", 3)  # ZIP compression

    @err_catcher(name=__name__)
    def onCreateModelHierarchyClicked(self) -> None:
        """Handle create model hierarchy button click."""
        self.createModelHierarchy(self.core.getCurrentScenefileData())

    @err_catcher(name=__name__)
    def buildSceneCreateModelHierarchy(self, step: Dict[str, Any], context: Dict[str, Any]) -> None:
        """
        Scene building step function to create model hierarchy for an entity.
        
        Args:
            step: Step settings dict.
            context: Current scene building context dict with entity, department, task info.
        """
        self.createModelHierarchy(context)

    @err_catcher(name=__name__)
    def createModelHierarchy(self, entity: Dict[str, Any]) -> None:
        """Create model hierarchy groups.
        
        Args:
            entity: Entity data dict
        """
        import maya.cmds as cmds
        assetName = os.path.basename(entity.get("asset_path", ""))
        if not assetName:
            logger.debug("can't get asset name from entity: %s" % entity)
            return

        if cmds.objExists("|" + assetName):
            logger.debug("asset hierarchy already exists: %s" % assetName)
            return

        asset = cmds.createNode("transform", name=assetName)
        geo = cmds.createNode("transform", name="geo", parent=asset)
        cube = cmds.polyCube(name="template_cube", width=1, height=1, depth=1)
        cmds.parent(cube[0], geo)

    @err_catcher(name=__name__)
    def buildSceneImportProducts(self, step: Dict[str, Any], context: Dict[str, Any]) -> None:
        """
        Scene building step function to import products for an entity.
        
        Args:
            step: Step settings dict.
            context: Current scene building context dict with entity, department, task info.
        """
        # Extract settings from step
        settings = {}
        includeMaster = True
        for setting in step.get("settings") or []:
            name = setting.get("name")
            value = setting.get("value")
            if name == "mode":
                # Convert UI label to lowercase mode value
                settings["mode"] = value.lower()
            elif name == "namespace":
                settings["namespace"] = value
            elif name == "ignoreMaster":
                includeMaster = not value

        settings["ignoreMaster"] = not includeMaster
        self.importProductsForTask(context, context["department"], context["task"], settings=settings, includeMaster=includeMaster)
        if context.get("type") in ["shot"]:
            self.core.products.importConnectedAssets(context, quietCheck=True, includeMaster=includeMaster, settings=settings)

    @err_catcher(name=__name__)
    def importProductsForTask(self, entity: Dict[str, Any], department: str, task: str, settings: Optional[Dict[str, Any]] = None, includeMaster: bool = True) -> None:
        """Import products for specific task.
        
        Args:
            entity: Entity data
            department: Department name
            task: Task name
            settings: Optional import settings (mode, namespace, etc.)
            includeMaster: Whether to include master products
        """
        # Use provided settings or default to import mode
        if settings is None:
            settings = {"mode": "import"}

        settings["ignoreMaster"] = not includeMaster
        self.core.products.importProductsForTask(entity, department, task, quietCheck=True, settings=settings, includeMaster=includeMaster)

    @err_catcher(name=__name__)
    def buildSceneApplyAbcCaches(self, step: Dict[str, Any], context: Dict[str, Any]) -> None:
        """
        Scene building step function to apply Alembic caches for an entity.
        
        Args:
            step: Step settings dict.
            context: Current scene building context dict with entity, department, task info.
        """
        self.applyAbcCaches(context, context["department"], quiet=True)

    @err_catcher(name=__name__)
    def applyAbcCaches(self, entity: Dict[str, Any], department: str, quiet: bool = True) -> None:
        """Apply Alembic caches to scene.
        
        Args:
            entity: Entity data
            department: Department name
            quiet: Suppress messages
        """
        logger.debug("applying abc caches...")
        tags = [x.strip() for x in os.getenv("PRISM_MAYA_IMPORT_TAGS", "animated").split(",") if x]
        products = self.core.products.getProductsByTags(entity, tags)
        productsToImport = products
        if not productsToImport:
            msg = "No products to import.\n(checking for tags: \"%s\")" % "\", \"".join(tags)
            logger.debug(msg)
            if not quiet:
                self.core.popup(msg)

            return

        importedProducts = []
        sm = self.core.getStateManager()
        for product in productsToImport:
            productPath = self.core.products.getLatestVersionpathFromProduct(product["product"], entity=product)
            if not productPath:
                logger.debug("can't get file of abc product: %s" % product)
                continue

            if not productPath.endswith(".abc"):
                logger.debug("abc product is not in .abc format: %s" % productPath)
                continue

            productData = self.core.paths.getCachePathData(productPath)
            assetName = productData.get("source_asset_path")
            if not assetName:
                logger.debug("can't get source asset from product: %s" % productData)
                continue

            asset = {"type": "asset", "asset_path": assetName}
            surfTags = [x.strip() for x in os.getenv("PRISM_MAYA_SURFACED_ASSET_TAGS", "static").split(",") if x]
            assetProducts = self.core.products.getProductsByTags(asset, surfTags)
            if not assetProducts:
                logger.debug("can't get product of source asset: %s, tags: %s" % (asset, surfTags))
                continue

            assetProduct = assetProducts[0]
            assetProductPath = self.core.products.getLatestVersionpathFromProduct(assetProduct["product"], entity=assetProduct)
            if not assetProductPath:
                logger.debug("can't get file of source asset product: %s" % assetProduct)
                continue

            state = sm.importFile(assetProductPath, settings={"quiet": True})
            settings = {
                "showGui": False,
                "mode": "applyCache",
                "applyCacheTarget": {"state": state},
            }
            if quiet:
                settings["quiet"] = True

            logger.debug("found product: %s" % productPath)
            sm.importFile(productPath, settings=settings)
            importedProducts.append(productPath)

        if not importedProducts:
            logger.debug("no products imported: %s" % productsToImport)

    @err_catcher(name=__name__)
    def sm_createRenderPressed(self, origin: Any) -> None:
        """Handle create render button press.
        
        Args:
            origin: Originating instance
        """
        origin.createPressed("Render")

    @err_catcher(name=__name__)
    def sm_renderSettings_startup(self, origin: Any) -> None:
        """Initialize render settings UI.
        
        Args:
            origin: Render settings instance
        """
        origin.cb_addSetting.setHidden(True)

    @err_catcher(name=__name__)
    def sm_renderSettings_getCurrentSettings(self, origin: Any, asString: bool = True) -> Union[str, Dict[str, Any]]:
        """Get current render settings.
        
        Args:
            origin: Render settings instance
            asString: Return as JSON string
            
        Returns:
            Settings string or dict
        """
        import maya.app.renderSetup.model.renderSettings as renderSettings

        settings = renderSettings.encode()

        if not asString:
            return settings

        settings = self.core.writeYaml(data=settings)
        return settings

    @err_catcher(name=__name__)
    def sm_renderSettings_setCurrentSettings(self, origin: Any, preset: str, state: Optional[Any] = None) -> None:
        """Apply render settings preset.
        
        Args:
            origin: Render settings instance
            preset: Preset JSON string
            state: Optional state instance
        """
        import maya.app.renderSetup.model.renderSettings as renderSettings

        try:
            renderSettings.decode(preset)
        except:
            self.core.popup("Failed to set rendersettings.")

    @err_catcher(name=__name__)
    def sm_renderSettings_applyDefaultSettings(self, origin: Any) -> None:
        """Apply default render settings.
        
        Args:
            origin: Render settings instance
        """
        import maya.app.renderSetup.views.renderSetupPreferences as prefs

        prefs.setDefaultPreset()

    @err_catcher(name=__name__)
    def importSequencerOtio(self, filepath: str, startFrame: Optional[int] = None) -> bool:
        """Import an OTIO file into the Maya Camera Sequencer.

        Requires Maya 2027.1 or later. Uses the built-in maya.app.edl.importExport
        module which supports OTIO timeline data including cameras, shots, audio,
        labels, colours, and thumbnails.

        Args:
            filepath (str): Path to the .otio file to import.
            startFrame (Optional[int]): Override the sequence start frame to this
                value. If None, the start frame stored in the OTIO file is used.

        Returns:
            bool: True on success, False if the module is unavailable or an error
                occurred.
        """
        try:
            from maya.app.edl import importExport as _edl
        except ImportError:
            self.core.popup(
                "OTIO import requires Maya 2027.1 or later.\n"
                "The maya.app.edl module is not available in this version of Maya."
            )
            return False

        if not os.path.isfile(filepath):
            self.core.popup("OTIO file not found:\n%s" % filepath)
            return False

        try:
            use_override = startFrame is not None
            _edl.doImport(filepath, use_override, startFrame if use_override else 0)
            logger.debug("Imported OTIO sequencer data from: %s" % filepath)
            return True
        except Exception as e:
            logger.warning("Failed to import OTIO file: %s\n%s" % (filepath, e))
            self.core.popup("OTIO import failed:\n%s" % str(e))
            return False

    @err_catcher(name=__name__)
    def exportSequencerOtio(self, filepath: str, allowPlayblast: bool = False) -> bool:
        """Export the Maya Camera Sequencer to an OTIO file.

        Requires Maya 2027.1 or later. Uses the built-in maya.app.edl.importExport
        module. The exported OTIO file preserves camera assignments, shot metadata,
        labels, colours, audio, and file references.

        Args:
            filepath (str): Destination path for the .otio file. The parent directory
                is created if it does not already exist.
            allowPlayblast (bool): When True, shots that are out of sync with their
                playblast clip are re-blasted before export. Defaults to False to
                avoid unexpected UI interactions during batch or background exports.

        Returns:
            bool: True on success, False if the module is unavailable or an error
                occurred.
        """
        try:
            from maya.app.edl import importExport as _edl
        except ImportError:
            self.core.popup(
                "OTIO export requires Maya 2027.1 or later.\n"
                "The maya.app.edl module is not available in this version of Maya."
            )
            return False

        outDir = os.path.dirname(filepath)
        if outDir and not os.path.exists(outDir):
            try:
                os.makedirs(outDir)
            except OSError as e:
                self.core.popup(
                    "Could not create output directory:\n%s\n%s" % (outDir, e)
                )
                return False

        try:
            _edl.doExport(filepath, allowPlayblast)
            logger.debug("Exported OTIO sequencer data to: %s" % filepath)
            return True
        except Exception as e:
            logger.warning("Failed to export OTIO file: %s\n%s" % (filepath, e))
            self.core.popup("OTIO export failed:\n%s" % str(e))
            return False


class BatchExportDlg(QDialog):
    def __init__(self, origin: Any, allowCache=True) -> None:
        """Initialize batch export dialog.
        
        Args:
            origin: Prism instance
        """
        super(BatchExportDlg, self).__init__()
        self.origin = origin
        self.plugin = self.origin.plugin
        self.core = self.plugin.core
        self.core.parentWindow(self)
        self.assets = []
        self.setupUi()
        self.refreshAssets(allowCache=allowCache)

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Setup the batch export UI."""
        self.setWindowTitle("Prism - Batch Export")
        self.setMinimumSize(900, 600)
        
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        # Create table
        self.tw_assets = QTableWidget()
        self.tw_assets.setColumnCount(5)
        self.tw_assets.setHorizontalHeaderLabels(["Enabled", "Asset Name", "Identifier", "Static", "Objects"])
        self.tw_assets.horizontalHeader().setStretchLastSection(True)
        self.tw_assets.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tw_assets.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.tw_assets.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.tw_assets.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tw_assets.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.tw_assets.setColumnWidth(2, 200)  # Set default width for Identifier column
        self.tw_assets.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tw_assets.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tw_assets.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tw_assets.customContextMenuRequested.connect(self.showContextMenu)
        self.tw_assets.itemChanged.connect(self.onIdentifierChanged)
        self.tw_assets.setAlternatingRowColors(True)
        
        self.lo_main.addWidget(self.tw_assets)

        # Bottom buttons
        self.lo_buttons = QHBoxLayout()
        self.lo_buttons.addStretch()
        
        self.b_export = QPushButton("Export")
        self.b_export.clicked.connect(self.exportAssets)
        self.lo_buttons.addWidget(self.b_export)
        
        self.b_cancel = QPushButton("Cancel")
        self.b_cancel.clicked.connect(self.reject)
        self.lo_buttons.addWidget(self.b_cancel)
        
        self.lo_main.addLayout(self.lo_buttons)

    @err_catcher(name=__name__)
    def refreshAssets(self, allowCache: bool = True) -> None:
        """Refresh the asset list from the scene
        
        Args:
            allowCache (bool): Whether to allow using cached data or force a refresh.
        """
        # Save current custom identifiers before refreshing
        # Use a composite key of (entityName, objects) to handle duplicate asset names
        saved_identifiers = {}
        saved_static_states = {}
        for row in range(self.tw_assets.rowCount()):
            if row < len(self.assets):
                asset = self.assets[row]
                # Create unique key from entityName and objects list
                objects = asset.get("objects", [])
                if not objects and "state" in asset and hasattr(asset["state"].ui, "nodes"):
                    objects = asset["state"].ui.nodes
                asset_key = (asset["entityName"], tuple(sorted(objects)))
                
                item = self.tw_assets.item(row, 2)
                if item:
                    saved_identifiers[asset_key] = item.text()

                static_widget = self.tw_assets.cellWidget(row, 3)
                if static_widget:
                    static_checkbox = static_widget.findChild(QCheckBox)
                    if static_checkbox:
                        saved_static_states[asset_key] = static_checkbox.isChecked()
        
        self.assets = self.origin.getAssetsFromScene(allowCache=allowCache)
        
        # Restore custom identifiers to matching assets
        for asset in self.assets:
            # Create the same unique key for matching
            objects = asset.get("objects", [])
            if not objects and "state" in asset and hasattr(asset["state"].ui, "nodes"):
                objects = asset["state"].ui.nodes
            asset_key = (asset["entityName"], tuple(sorted(objects)))

            existing_state = self.findExportStateForAsset(asset)
            if existing_state and hasattr(existing_state, "ui"):
                if hasattr(existing_state.ui, "getProductname"):
                    asset["identifier"] = existing_state.ui.getProductname()

                if hasattr(existing_state.ui, "getRangeType"):
                    asset["static"] = existing_state.ui.getRangeType() == "Single Frame"

                continue
            
            if asset_key in saved_identifiers:
                asset["identifier"] = saved_identifiers[asset_key]
            if asset_key in saved_static_states:
                asset["static"] = saved_static_states[asset_key]
        
        self.populateTable()

    @err_catcher(name=__name__)
    def populateTable(self) -> None:
        """Populate the table with assets"""
        # Block signals during population to avoid triggering itemChanged
        self.tw_assets.blockSignals(True)
        self.tw_assets.setRowCount(0)

        staticIdfTemplate, animIdfTemplate = self.getBatchIdentifierTemplates()

        curSceneData = self.core.getCurrentScenefileData()
        default_static = curSceneData.get("type") == "asset"
    
        # Generate unique identifiers only for assets that don't have one
        identifiers = {}
        for asset in self.assets:
            if "static" not in asset:
                existing_state = self.findExportStateForAsset(asset)
                if existing_state and hasattr(existing_state, "ui") and hasattr(existing_state.ui, "getRangeType"):
                    asset["static"] = existing_state.ui.getRangeType() == "Single Frame"
                else:
                    asset["static"] = default_static

            # Check if asset already has a custom identifier (preserved from before)
            if "identifier" in asset and asset["identifier"]:
                identifier = asset["identifier"]
            else:
                # Generate new identifier
                base_name = asset["entityName"]
                idfTemplate = staticIdfTemplate if asset["static"] else animIdfTemplate
                identifier = idfTemplate.format(entity=base_name, counter="")
                counter = 1
                while identifier in identifiers:
                    identifier = idfTemplate.format(entity=base_name, counter=counter)
                    counter += 1

                asset["identifier"] = identifier
            
            identifiers[identifier] = asset
        
        for asset in self.assets:
            row = self.tw_assets.rowCount()
            self.tw_assets.insertRow(row)
            
            # Enabled checkbox
            chb_enabled = QCheckBox()
            chb_enabled.setChecked(True)
            chb_enabled.stateChanged.connect(lambda state, r=row: self.onCheckboxChanged(r, state))
            w_checkbox = QWidget()
            lo_checkbox = QHBoxLayout(w_checkbox)
            lo_checkbox.addWidget(chb_enabled)
            lo_checkbox.setAlignment(Qt.AlignCenter)
            lo_checkbox.setContentsMargins(0, 0, 0, 0)
            self.tw_assets.setCellWidget(row, 0, w_checkbox)
            
            # Asset name
            entity = {"type": "asset", "asset_path": asset["entityName"]}
            preview = self.core.entities.getEntityPreview(entity)

            w_asset = QWidget()
            w_asset.setToolTip(asset.get("label", asset["entityName"]))
            lo_asset = QHBoxLayout(w_asset)
            if not preview:
                preview = self.core.media.emptyPrvPixmap

            if preview:
                preview = preview.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                l_thumbnail = QLabel()
                l_thumbnail.setPixmap(preview)
                lo_asset.addWidget(l_thumbnail)

            lo_asset.setAlignment(Qt.AlignCenter)
            lo_asset.setContentsMargins(0, 0, 0, 0)

            l_name = QLabel(asset["entityName"])
            lo_asset.addWidget(l_name)
            lo_asset.addStretch()

            self.tw_assets.setCellWidget(row, 1, w_asset)
            
            # Identifier (editable)
            item_identifier = QTableWidgetItem(asset.get("identifier", asset["entityName"]))
            item_identifier.setToolTip("Editable identifier for this asset")
            self.tw_assets.setItem(row, 2, item_identifier)

            # Static checkbox
            chb_static = QCheckBox()
            chb_static.setChecked(bool(asset.get("static", default_static)))
            chb_static.stateChanged.connect(lambda state, r=row: self.onStaticCheckboxChanged(r, state))
            w_static = QWidget()
            lo_static = QHBoxLayout(w_static)
            lo_static.addWidget(chb_static)
            lo_static.setAlignment(Qt.AlignCenter)
            lo_static.setContentsMargins(0, 0, 0, 0)
            self.tw_assets.setCellWidget(row, 3, w_static)
            
            # Objects list
            if asset.get("objects"):
                objects = asset.get("objects", [])
            else:
                objects = asset["state"].ui.nodes if hasattr(asset["state"].ui, "nodes") else []
                
            objects_text = ", ".join([obj.split("|")[-1] for obj in objects]) if objects else ""
            item_objects = QTableWidgetItem(objects_text)
            item_objects.setFlags(item_objects.flags() & ~Qt.ItemIsEditable)
            item_objects.setToolTip(objects_text)
            self.tw_assets.setItem(row, 4, item_objects)
        
        # Unblock signals after population is complete
        self.tw_assets.blockSignals(False)

    @err_catcher(name=__name__)
    def onIdentifierChanged(self, item: Any) -> None:
        """Handle identifier change to ensure uniqueness.
        
        Args:
            item: Changed table item
        """
        # Only handle identifier column (column 2)
        if item.column() != 2:
            return
        
        new_identifier = item.text().strip()
        if not new_identifier:
            # Don't allow empty identifiers
            row = item.row()
            if row < len(self.assets):
                item.setText(self.assets[row].get("identifier", self.assets[row]["entityName"]))
            return
        
        # Update the identifier in the asset dict immediately
        current_row = item.row()
        if current_row < len(self.assets):
            self.assets[current_row]["identifier"] = new_identifier
        
        # Check for duplicates
        for row in range(self.tw_assets.rowCount()):
            if row == current_row:
                continue
            
            other_item = self.tw_assets.item(row, 2)
            if other_item and other_item.text() == new_identifier:
                # Duplicate found - make it unique
                base_name = new_identifier
                counter = 1
                unique_identifier = f"{base_name}_{counter}"
                
                # Find a unique identifier
                while True:
                    is_unique = True
                    for check_row in range(self.tw_assets.rowCount()):
                        if check_row == current_row:
                            continue
                        check_item = self.tw_assets.item(check_row, 2)
                        if check_item and check_item.text() == unique_identifier:
                            is_unique = False
                            break
                    
                    if is_unique:
                        break
                    
                    counter += 1
                    unique_identifier = f"{base_name}_{counter}"
                
                # Block signals to avoid recursive calls
                self.tw_assets.blockSignals(True)
                item.setText(unique_identifier)
                # Update the asset dict with the corrected identifier
                if current_row < len(self.assets):
                    self.assets[current_row]["identifier"] = unique_identifier
                self.tw_assets.blockSignals(False)
                
                self.core.popup(f"Identifier '{new_identifier}' already exists. Changed to '{unique_identifier}'.", severity="warning")
                break

            self.applyAssetSettingsToState(current_row)

    @err_catcher(name=__name__)
    def onCheckboxChanged(self, row: int, state: int) -> None:
        """Handle checkbox state change.
        
        Args:
            row: Table row index
            state: Qt checkbox state
        """
        """Handle checkbox state change - if multiple rows selected, apply to all"""
        selected_rows = set([index.row() for index in self.tw_assets.selectedIndexes()])
        
        if row in selected_rows and len(selected_rows) > 1:
            # Apply the state to all selected rows
            is_checked = (state == Qt.Checked)
            for sel_row in selected_rows:
                checkbox_widget = self.tw_assets.cellWidget(sel_row, 0)
                if checkbox_widget:
                    checkbox = checkbox_widget.findChild(QCheckBox)
                    if checkbox:
                        checkbox.blockSignals(True)
                        checkbox.setChecked(is_checked)
                        checkbox.blockSignals(False)

    @err_catcher(name=__name__)
    def onStaticCheckboxChanged(self, row: int, state: int) -> None:
        """Handle static checkbox state changes.
        
        Args:
            row: Table row index
            state: Qt checkbox state
        """
        selected_rows = set([index.row() for index in self.tw_assets.selectedIndexes()])
        is_checked = bool(state)
        if row in selected_rows and len(selected_rows) > 1:
            target_rows = selected_rows
        else:
            target_rows = {row}

        for target_row in target_rows:
            if target_row < len(self.assets):
                self.assets[target_row]["static"] = is_checked

            if target_row != row:
                static_widget = self.tw_assets.cellWidget(target_row, 3)
                if static_widget:
                    static_checkbox = static_widget.findChild(QCheckBox)
                    if static_checkbox:
                        static_checkbox.blockSignals(True)
                        static_checkbox.setChecked(is_checked)
                        static_checkbox.blockSignals(False)

            self.refreshIdentifierFromTemplate(target_row)

            self.applyAssetSettingsToState(target_row)

    @err_catcher(name=__name__)
    def getBatchIdentifierTemplates(self) -> Tuple[str, str]:
        """Get identifier templates for static and animated assets."""
        staticIdfTemplate = self.core.getConfig(
            "globals",
            "defaultMayaBatchExportIdentifierTemplate",
            configPath=self.core.prismIni,
        )
        if not staticIdfTemplate:
            staticIdfTemplate = os.getenv(
                "PRISM_MAYA_BATCH_EXPORT_STATIC_IDENTIFIER_TEMPLATE",
                "static_{entity}{counter}",
            )

        animIdfTemplate = self.core.getConfig(
            "globals",
            "defaultMayaBatchExportAnimIdentifierTemplate",
            configPath=self.core.prismIni,
        )
        if not animIdfTemplate:
            animIdfTemplate = os.getenv(
                "PRISM_MAYA_BATCH_EXPORT_ANIM_IDENTIFIER_TEMPLATE",
                "anim_{entity}{counter}",
            )

        return staticIdfTemplate, animIdfTemplate

    @err_catcher(name=__name__)
    def isIdentifierUsed(self, identifier: str, current_row: int) -> bool:
        """Check if an identifier is already used by another row."""
        for row in range(self.tw_assets.rowCount()):
            if row == current_row:
                continue

            other_item = self.tw_assets.item(row, 2)
            if other_item and other_item.text() == identifier:
                return True

        return False

    @err_catcher(name=__name__)
    def refreshIdentifierFromTemplate(self, row: int) -> None:
        """Regenerate a row identifier based on static/animated template."""
        if row < 0 or row >= len(self.assets):
            return

        asset = self.assets[row]
        staticIdfTemplate, animIdfTemplate = self.getBatchIdentifierTemplates()
        idfTemplate = staticIdfTemplate if asset.get("static", False) else animIdfTemplate
        base_name = asset["entityName"]

        identifier = idfTemplate.format(entity=base_name, counter="")
        counter = 1
        while self.isIdentifierUsed(identifier, row):
            identifier = idfTemplate.format(entity=base_name, counter=counter)
            counter += 1

        asset["identifier"] = identifier
        item = self.tw_assets.item(row, 2)
        if item:
            self.tw_assets.blockSignals(True)
            item.setText(identifier)
            self.tw_assets.blockSignals(False)

    @err_catcher(name=__name__)
    def syncAssetSettingsFromTable(self) -> None:
        """Sync editable table values back to internal asset data."""
        for row in range(self.tw_assets.rowCount()):
            if row >= len(self.assets):
                continue

            item = self.tw_assets.item(row, 2)
            if item:
                self.assets[row]["identifier"] = item.text()

            static_widget = self.tw_assets.cellWidget(row, 3)
            if static_widget:
                static_checkbox = static_widget.findChild(QCheckBox)
                if static_checkbox:
                    self.assets[row]["static"] = static_checkbox.isChecked()

            self.applyAssetSettingsToState(row)

    @err_catcher(name=__name__)
    def getNonStaticRangeType(self, state: Any) -> str:
        """Get a sensible non-static range type for an export state."""
        context = {}
        if hasattr(state.ui, "getCurrentContext"):
            context = state.ui.getCurrentContext() or {}

        if context.get("type") == "shot":
            return "Shot"

        return "Scene"

    @err_catcher(name=__name__)
    def applyAssetSettingsToState(self, row: int) -> None:
        """Apply identifier/static settings to an existing export state immediately."""
        if row < 0 or row >= len(self.assets):
            return

        asset = self.assets[row]
        state = self.findExportStateForAsset(asset)
        if not state or not hasattr(state, "ui"):
            return

        identifier = asset.get("identifier")
        if identifier and hasattr(state.ui, "setProductname"):
            state.ui.setProductname(identifier)

        if hasattr(state.ui, "setRangeType") and hasattr(state.ui, "getRangeType"):
            is_static = bool(asset.get("static", False))
            if is_static:
                state.ui.setRangeType("Single Frame")
            elif state.ui.getRangeType() == "Single Frame":
                state.ui.setRangeType(self.getNonStaticRangeType(state))

        if hasattr(state.ui, "stateManager") and hasattr(state.ui.stateManager, "saveStatesToScene"):
            state.ui.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def showContextMenu(self, position: Any) -> None:
        """Show context menu.
        
        Args:
            position: Menu position
        """
        """Show context menu for the table"""
        menu = QMenu(self)
        
        action_refresh = menu.addAction("Refresh")
        action_open_sm = menu.addAction("Open State Manager")
        menu.addSeparator()
        action_create_states = menu.addAction("Create Export States for Selected Assets")
        
        action = menu.exec_(self.tw_assets.viewport().mapToGlobal(position))
        
        if action == action_refresh:
            self.refreshAssets(allowCache=False)
        elif action == action_open_sm:
            self.openStateManager()
        elif action == action_create_states:
            self.createExportStates()

    @err_catcher(name=__name__)
    def openStateManager(self) -> None:
        """Open the State Manager"""
        if self.core.sm:
            self.core.sm.setHidden(False)
            self.core.sm.raise_()
            self.core.sm.activateWindow()
        else:
            self.core.stateManager()

    @err_catcher(name=__name__)
    def createExportStates(self) -> None:
        """Create export states for selected assets"""
        self.syncAssetSettingsFromTable()
        
        selected_rows = set([index.row() for index in self.tw_assets.selectedIndexes()])
        
        if not selected_rows:
            self.core.popup("No assets selected.")
            return
        
        sm = self.core.getStateManager()
        if not sm:
            self.core.popup("State Manager not available.")
            return
        
        created_count = 0
        for row in selected_rows:
            if row >= len(self.assets):
                continue
                
            asset = self.assets[row]

            # Check if export state already exists for this asset
            existing_state = self.findExportStateForAsset(asset)

            if not existing_state:
                # Create new export state
                state = self.createExportState(asset)
                if state:
                    created_count += 1
        
        if created_count > 0:
            self.core.popup(f"Created {created_count} export state(s).", severity="info")
            self.refreshAssets(allowCache=True)
        else:
            self.core.popup("All selected assets already have export states.", severity="info")

    @err_catcher(name=__name__)
    def createExportState(self,  asset: Dict[str, Any]) -> Optional[Any]:
        """Create export state for asset.
        
        Args:
            asset: Asset data dict
            
        Returns:
            Created state or None
        """
        asset_name = asset["entityName"]
        # Use identifier if available, otherwise fall back to asset name
        identifier = asset.get("identifier", asset_name)
        sm = self.core.getStateManager()
        parent = self.origin.getDftStateParent()
        applyAnimTag = False
        curSceneData = self.core.getCurrentScenefileData()
        if not asset.get("static", False):
            applyAnimTag = os.getenv("PRISM_MAYA_AUTO_APPLY_ANIM_TAG", "1") == "1"

        productName = identifier
        if applyAnimTag:
            curSceneData["product"] = productName
            curTags = self.core.products.getTagsFromProduct(curSceneData)
            if not curTags:
                tags = ["animated"]
                self.core.products.setProductTags(curSceneData, tags)

        is_static = bool(asset.get("static", False))
        if "state" in asset or "static" in asset:
            asset = asset.copy()
            asset.pop("state", None)
            asset.pop("static", None)

        state_data = {"stateName": f"Export {asset_name}", "assetToExport": asset, "productname": productName}
        if is_static:
            state_data["rangeType"] = "Single Frame"

        state = sm.createState("Export", stateData=state_data, parent=parent, applyDefaults=True)
        return state

    @err_catcher(name=__name__)
    def findExportStateForAsset(self, asset: Dict[str, Any]) -> Optional[Any]:
        """Find existing export state for asset.
        
        Args:
            asset: Asset data dict
            
        Returns:
            Found state or None
        """
        """Find existing export state for an asset"""
        sm = self.core.getStateManager()
        if not sm:
            return None
        
        for state in sm.states:
            if state.ui.className == "Export":
                if hasattr(state.ui, "cb_asset"):
                    current_asset = state.ui.cb_asset.currentData().get("entityName")
                    if current_asset == asset["entityName"]:
                        data = state.ui.cb_asset.currentData()
                        if data["objects"] == asset["objects"]:
                            return state
        
        return None

    @err_catcher(name=__name__)
    def exportAssets(self) -> None:
        """Export all enabled assets"""
        self.syncAssetSettingsFromTable()
        
        sm = self.core.getStateManager()
        if not sm:
            self.core.popup("State Manager not available.")
            return
        
        # Collect enabled assets
        states_to_export = []
        not_found_assets = []
        
        for row in range(self.tw_assets.rowCount()):
            checkbox_widget = self.tw_assets.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    if row >= len(self.assets):
                        continue
                    
                    asset = self.assets[row]
                    asset_name = asset["entityName"]
                    
                    # Find or create export state for this asset
                    state = self.findExportStateForAsset(asset)
                    
                    if not state:
                        # Create new export state
                        state = self.createExportState(asset)

                    if state:
                        states_to_export.append(state)
                    else:
                        not_found_assets.append(asset_name)
        
        if not states_to_export:
            self.core.popup("No enabled assets to export.")
            return
        
        # Execute export for all states
        self.hide()
        
        success_count = 0
        failed_count = 0
        
        for state in states_to_export:
            result = sm.publish(
                successPopup=False,
                executeState=True,
                states=[state],
                useVersion=None,
                saveScene=None,
                incrementScene=False,
                sanityChecks=True,
                versionWarning=False,
            )
            
            if result:
                success_count += 1
            else:
                failed_count += 1
        
        # Show results
        msg = f"Batch export completed.\n\nSuccessful: {success_count}\nFailed: {failed_count}"
        if not_found_assets:
            msg += f"\n\nCould not create states for: {', '.join(not_found_assets)}"

        self.core.popup(msg, severity="info")
        self.close()


class ExporterDlg(QDialog):
    def __init__(self, origin: Any, state: Any) -> None:
        """Initialize export farm submitter.
        
        Args:
            origin: Parent instance
            state: Export state
        """
        super(ExporterDlg, self).__init__()
        self.origin = origin
        self.plugin = self.origin.plugin
        self.core = self.plugin.core
        self.core.parentWindow(self)
        self.state = state
        self.showSm = False
        if self.core.sm.isVisible():
            self.core.sm.setHidden(True)
            self.showSm = True

        self.setupUi()

    @err_catcher(name=__name__)
    def sizeHint(self) -> Any:
        """Get preferred dialog size.
        
        Returns:
            QSize object
        """
        hint = super(ExporterDlg, self).sizeHint()
        hint += QSize(100, 0)
        return hint

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Setup export dialog UI with state widget and comment field."""
        self.setWindowTitle("Prism - Export")
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.addWidget(self.state.ui)

        self.lo_main.addStretch()

        self.e_comment = QLineEdit()
        self.e_comment.setPlaceholderText("Comment...")
        self.lo_main.addWidget(self.e_comment)

        self.b_submit = QPushButton("Export")
        self.lo_main.addWidget(self.b_submit)
        self.b_submit.clicked.connect(self.submit)

    @err_catcher(name=__name__)
    def closeEvent(self, event: Any) -> None:
        """Handle dialog close.
        
        Args:
            event: Close event
        """
        if self.core.sm:
            curItem = self.core.sm.getCurrentItem(self.core.sm.activeList)
            if self.state and curItem and id(self.state) == id(curItem):
                self.core.sm.showState()

            if self.showSm:
                self.core.sm.setHidden(False)

        event.accept()

    @err_catcher(name=__name__)
    def submit(self, openOnFail: bool = True) -> None:
        """Submit job to farm.
        
        Args:
            openOnFail: Open output folder on failure
        """
        self.hide()

        sm = self.core.getStateManager()
        sanityChecks = True
        version = None
        saveScene = None
        incrementScene = sm.actionVersionUp.isChecked()
        sm.e_comment.setText(self.e_comment.text())

        result = sm.publish(
            successPopup=False,
            executeState=True,
            states=[self.state],
            useVersion=version,
            saveScene=saveScene,
            incrementScene=incrementScene,
            sanityChecks=sanityChecks,
            versionWarning=False,
        )
        if result:
            msg = "Export completed successfully."
            result = self.core.popupQuestion(msg, buttons=["Open in Product Browser", "Open in Explorer", "Close"], icon=QMessageBox.Information)
            path = self.state.ui.l_pathLast.text()
            if result == "Open in Product Browser":
                self.core.projectBrowser()
                self.core.pb.showTab("Products")
                data = self.core.paths.getCachePathData(path)
                self.core.pb.productBrowser.navigateToProduct(data.get("product", ""), entity=data)
            elif result == "Open in Explorer":
                self.core.openFolder(path)

            self.close()
        elif openOnFail:
            self.show()


class PlayblastDlg(QDialog):
    def __init__(self, origin: Any, state: Any) -> None:
        """Initialize playblast farm submitter.
        
        Args:
            origin: Parent instance
            state: Playblast state
        """
        super(PlayblastDlg, self).__init__()
        self.origin = origin
        self.plugin = self.origin.plugin
        self.core = self.plugin.core
        self.core.parentWindow(self)
        self.state = state
        self.showSm = False
        if self.core.sm.isVisible():
            self.core.sm.setHidden(True)
            self.showSm = True

        self.setupUi()

    @err_catcher(name=__name__)
    def sizeHint(self) -> Any:
        """Get preferred dialog size.
        
        Returns:
            QSize with extra width
        """
        hint = super(PlayblastDlg, self).sizeHint()
        hint += QSize(100, 0)
        return hint

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Setup playblast dialog UI with state widget and comment field."""
        self.setWindowTitle("Prism - Playblast")
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.addWidget(self.state.ui)

        self.e_comment = QLineEdit()
        self.e_comment.setPlaceholderText("Comment...")
        self.lo_main.addWidget(self.e_comment)

        self.b_submit = QPushButton("Playblast")
        self.lo_main.addWidget(self.b_submit)
        self.b_submit.clicked.connect(self.submit)

    @err_catcher(name=__name__)
    def closeEvent(self, event: Any) -> None:
        """Handle dialog close event.
        
        Restores State Manager visibility and shows current state.
        
        Args:
            event: Qt close event
        """
        curItem = self.core.sm.getCurrentItem(self.core.sm.activeList)
        if self.state and curItem and id(self.state) == id(curItem):
            self.core.sm.showState()

        if self.showSm:
            self.core.sm.setHidden(False)

        event.accept()

    @err_catcher(name=__name__)
    def submit(self, openOnFail: bool = True) -> None:
        """Submit playblast job to render farm.
        
        Args:
            openOnFail: Open output folder on failure
        """
        self.hide()

        sm = self.core.getStateManager()
        sanityChecks = True
        version = None
        saveScene = None
        incrementScene = sm.actionVersionUp.isChecked()
        sm.e_comment.setText(self.e_comment.text())

        result = sm.publish(
            successPopup=False,
            executeState=True,
            states=[self.state],
            useVersion=version,
            saveScene=saveScene,
            incrementScene=incrementScene,
            sanityChecks=sanityChecks,
            versionWarning=False,
        )
        if result:
            msg = "Playblast completed successfully."
            result = self.core.popupQuestion(msg, buttons=["Open in Media Browser", "Open in Explorer", "Close"], icon=QMessageBox.Information)
            path = self.state.ui.l_pathLast.text()
            if result == "Open in Media Browser":
                self.core.projectBrowser()
                self.core.pb.showTab("Media")
                data = self.core.paths.getPlayblastProductData(path)
                self.core.pb.mediaBrowser.showRender(entity=data, identifier=data.get("identifier") + " (playblast)", version=data.get("version"))
            elif result == "Open in Explorer":
                self.core.openFolder(path)

            self.close()
        elif openOnFail:
            self.show()


class RenderDlg(QDialog):
    def __init__(self, origin: Any, state: Any) -> None:
        """Initialize render farm submitter.
        
        Args:
            origin: Parent instance
            state: Render state
        """
        super(RenderDlg, self).__init__()
        self.origin = origin
        self.plugin = self.origin.plugin
        self.core = self.plugin.core
        self.core.parentWindow(self)
        self.state = state
        self.showSm = False
        if self.core.sm.isVisible():
            self.core.sm.setHidden(True)
            self.showSm = True

        self.setupUi()

    @err_catcher(name=__name__)
    def sizeHint(self) -> Any:
        """Get preferred dialog size.
        
        Returns:
            QSize with extra width
        """
        hint = super(RenderDlg, self).sizeHint()
        hint += QSize(100, 0)
        return hint

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Setup render dialog UI with state widget and comment field."""
        self.setWindowTitle("Prism - Render")
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.addWidget(self.state.ui)

        self.e_comment = QLineEdit()
        self.e_comment.setPlaceholderText("Comment...")
        self.lo_main.addWidget(self.e_comment)

        self.b_submit = QPushButton("Render")
        self.lo_main.addWidget(self.b_submit)
        self.b_submit.clicked.connect(self.submit)

    @err_catcher(name=__name__)
    def closeEvent(self, event: Any) -> None:
        """Handle dialog close event.
        
        Restores State Manager visibility and shows current state.
        
        Args:
            event: Qt close event
        """
        curItem = self.core.sm.getCurrentItem(self.core.sm.activeList)
        if self.state and curItem and id(self.state) == id(curItem):
            self.core.sm.showState()

        if self.showSm:
            self.core.sm.setHidden(False)

        event.accept()

    @err_catcher(name=__name__)
    def submit(self, openOnFail: bool = True) -> None:
        """Submit render job to render farm.
        
        Args:
            openOnFail: Open output folder on failure
        """
        self.hide()

        sm = self.core.getStateManager()
        sanityChecks = True
        version = None
        saveScene = None
        incrementScene = sm.actionVersionUp.isChecked()
        sm.e_comment.setText(self.e_comment.text())

        result = sm.publish(
            successPopup=False,
            executeState=True,
            states=[self.state],
            useVersion=version,
            saveScene=saveScene,
            incrementScene=incrementScene,
            sanityChecks=sanityChecks,
            versionWarning=False,
        )
        if result:
            msg = "Render completed successfully."
            result = self.core.popupQuestion(msg, buttons=["Open in Media Browser", "Open in Explorer", "Close"], icon=QMessageBox.Information)
            path = self.state.ui.l_pathLast.text()
            if result == "Open in Media Browser":
                self.core.projectBrowser()
                self.core.pb.showTab("Media")
                data = self.core.paths.getRenderProductData(path)
                self.core.pb.mediaBrowser.showRender(entity=data, identifier=data.get("identifier"), version=data.get("version"))
            elif result == "Open in Explorer":
                self.core.openFolder(path)

            self.close()
        elif openOnFail:
            self.show()


class ShotExtendWindow(QDialog):
    def __init__(self, parent: Optional[Any] = None) -> None:
        """Initialize shot extend dialog.
        
        Args:
            parent: Parent widget
        """
        super(ShotExtendWindow, self).__init__(parent)
        self.setWindowTitle("Shot Extend Tool")
        self.setMinimumSize(500, 250)  # Adjusted window size for this simpler UI
        
        # Store the current shot
        self.current_shot = None
        
        # Create the UI
        self.initUI()
        
        # Load the currently selected shot
        self.refreshSelectedShot()
        
    def initUI(self) -> None:
        """Initialize UI widgets."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)
        
        # Shot information section
        info_group = QGroupBox("Shot Information")
        info_layout = QVBoxLayout(info_group)
        
        # Shot label
        self.shot_label = QLabel("No shot selected")
        self.shot_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        info_layout.addWidget(self.shot_label)
        
        # Shot details (start and end frame)
        self.frame_info_label = QLabel("Start frame: N/A   End frame: N/A   Duration: N/A")
        info_layout.addWidget(self.frame_info_label)
        
        # Refresh button
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()
        self.refresh_btn = QPushButton("Refresh Selected Shot")
        self.refresh_btn.clicked.connect(self.refreshSelectedShot)
        refresh_layout.addWidget(self.refresh_btn)
        info_layout.addLayout(refresh_layout)
        
        main_layout.addWidget(info_group)
        
        # Extension settings
        extend_group = QGroupBox("Extension Settings")
        extend_layout = QHBoxLayout(extend_group)
        
        # Spinbox for frame extension
        extend_layout.addWidget(QLabel("Extend by frames:"))
        self.frames_spinbox = QSpinBox()
        self.frames_spinbox.setMinimum(1)
        self.frames_spinbox.setMaximum(1000)
        self.frames_spinbox.setValue(10)
        extend_layout.addWidget(self.frames_spinbox)
        
        main_layout.addWidget(extend_group)
        
        # Create a spacer to push buttons to the bottom
        main_layout.addStretch()
        
        # Action buttons at the bottom
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.extend_btn = QPushButton("Extend Shot")
        self.extend_btn.clicked.connect(self.extendShot)
        self.extend_btn.setStyleSheet("background-color: #3498db; color: white; font-weight: bold;")
        button_layout.addWidget(self.extend_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(button_layout)
        
    def refreshSelectedShot(self) -> None:
        """Refresh selected shot info."""
        """Get the currently selected shot from Maya's sequencer"""
        # Get selected shot
        selected_shots = cmds.ls(selection=True, type="shot")
        
        if not selected_shots:
            self.shot_label.setText("No shot selected")
            self.frame_info_label.setText("Start frame: N/A   End frame: N/A   Duration: N/A")
            self.current_shot = None
            return
        
        # Use the first selected shot
        self.current_shot = selected_shots[0]
        
        # Get shot details
        shot_name = cmds.getAttr(self.current_shot + ".shotName")
        start_frame = cmds.getAttr(self.current_shot + ".startFrame")
        end_frame = cmds.getAttr(self.current_shot + ".endFrame")
        duration = end_frame - start_frame + 1
        
        # Update UI
        self.shot_label.setText("Selected Shot: %s" % shot_name)
        self.frame_info_label.setText("Start frame: %s   End frame: %s   Duration: %s" % (start_frame, end_frame, duration))
    
    def extendShot(self) -> None:
        """Extend shot duration."""
        """Extend the selected shot and adjust subsequent shots"""
        if not self.current_shot:
            QMessageBox.warning(self, "Shot Extend", "No shot is selected. Please select a shot first.")
            return
        
        # Get the extension amount
        extension_frames = self.frames_spinbox.value()
        
        # Get shot data
        shot_name = cmds.getAttr(self.current_shot + ".shotName")
        start_frame = cmds.getAttr(self.current_shot + ".startFrame")
        end_frame = cmds.getAttr(self.current_shot + ".endFrame")
        
        # Find all shots in the scene
        all_shots = cmds.ls(type="shot")
        
        # Separate shots into those that come after the current shot
        shots_after = []
        for shot in all_shots:
            if shot != self.current_shot:
                shot_start = cmds.getAttr(shot + ".startFrame")
                if shot_start > end_frame:
                    shots_after.append(shot)
        
        # Confirm operation
        message = "This will extend shot '%s' by %s frames and move %s subsequent shots. Continue?" % (shot_name, extension_frames, len(shots_after))
        result = QMessageBox.question(
            self, "Confirm Extension", message, 
            QMessageBox.Yes | QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
        
        # Start the undoable operation
        cmds.undoInfo(openChunk=True)
        try:
            # 1. Move keyframes in subsequent shots
            if shots_after:
                # Get a list of all animated objects in the scene
                animated_objects = set()
                for shot_node in shots_after:
                    # Get the shot's start frame to filter keyframes
                    shot_start = cmds.getAttr(shot_node + ".startFrame")
                    
                    # Find all animated attributes in the scene with keyframes at or after this shot's start
                    anim_curves = cmds.ls(type=["animCurveTA", "animCurveTL", "animCurveTT", "animCurveTU"])
                    for curve in anim_curves:
                        keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
                        # Check if any keyframe is at or after this shot's start
                        if any(keyframe >= shot_start for keyframe in keyframes):
                            animated_objects.add(curve)
                
                # Move all the keyframes in one operation if possible
                if animated_objects:
                    try:
                        cmds.keyframe(list(animated_objects), edit=True, relative=True, timeChange=extension_frames, time=(end_frame+1, 1e10))
                    except Exception as e:
                        print("Warning: Error moving keyframes: %s" % str(e))
                        # Fall back to moving shot by shot if the bulk operation fails
                        for shot_node in shots_after:
                            shot_start = cmds.getAttr(shot_node + ".startFrame")
                            # Move keyframes for this shot
                            try:
                                cmds.keyframe(list(animated_objects), edit=True, relative=True, 
                                             timeChange=extension_frames, time=(shot_start, 1e10))
                            except Exception as e:
                                print("Warning: Error moving keyframes for shot %s: %s" % (shot_node, str(e)))
            
            # 2. Move subsequent shots
            for shot in reversed(shots_after):
                shot_start = cmds.getAttr(shot + ".startFrame")
                shot_end = cmds.getAttr(shot + ".endFrame")
                shot_sequence_start = cmds.getAttr(shot + ".sequenceStartFrame")
                
                # Move the shot
                cmds.setAttr(shot + ".startFrame", shot_start + extension_frames)
                cmds.setAttr(shot + ".endFrame", shot_end + extension_frames)
                cmds.setAttr(shot + ".sequenceStartFrame", shot_sequence_start + extension_frames)
            
            # 3. Extend the current shot
            cmds.setAttr(self.current_shot + ".endFrame", end_frame + extension_frames)
            
            # Show success message
            QMessageBox.information(self, "Shot Extended", 
                                  "Shot '%s' has been extended by %s frames." % (shot_name, extension_frames))
            
            # Refresh the UI to show updated information
            self.refreshSelectedShot()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", "An error occurred: %s" % str(e))
        finally:
            cmds.undoInfo(closeChunk=True)


class ShotSplitWindow(QDialog):
    def __init__(self, parent: Optional[Any] = None, plugin: Optional[Any] = None) -> None:
        """Initialize shot split dialog.
        
        Args:
            parent: Parent widget
            plugin: Maya plugin instance
        """
        super(ShotSplitWindow, self).__init__(parent)
        self.plugin = plugin
        self.setWindowTitle("Shot Split Tool")
        self.setMinimumSize(1000, 700)  # Increased window size
        
        # Store shot-asset selections
        self.shot_asset_selections = {}
        self.all_assets = []
        
        # Create UI first to ensure all widgets are created
        self.initUI()
        
        # Populate data after UI is fully set up
        QApplication.processEvents()
        self.populateShots()
        self.populateAssets()
        
    def initUI(self) -> None:
        """Initialize shot split dialog UI with shot list, assets, and controls."""
        # Create the main window layout first (without setting it to the dialog yet)
        main_window_layout = QVBoxLayout()
        
        # Left side - Shots
        left_widget = QWidget(self)  # Parent explicitly to the dialog
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        shot_label = QLabel("Shots:", left_widget)  # Parent explicitly to left_widget
        shot_label.setStyleSheet("font-weight: bold; font-size: 20px;")
        left_layout.addWidget(shot_label)
        
        # Create list widget with explicit parent
        self.shot_list = QListWidget(left_widget)
        self.shot_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.shot_list.itemClicked.connect(self.onShotSelected)
        self.shot_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.shot_list.customContextMenuRequested.connect(self.showShotContextMenu)
        left_layout.addWidget(self.shot_list)
        
        # Right side - Assets
        right_widget = QWidget(self)  # Parent explicitly to the dialog
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        asset_label = QLabel("Assets:", right_widget)  # Parent explicitly to right_widget
        asset_label.setStyleSheet("font-weight: bold; font-size: 20px;")
        right_layout.addWidget(asset_label)
        
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter:", right_widget)  # Explicit parent
        self.filter_edit = QLineEdit(right_widget)  # Explicit parent
        self.filter_edit.setPlaceholderText("Type to filter assets...")
        self.filter_edit.textChanged.connect(self.filterAssets)
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_edit)
        
        right_layout.addLayout(filter_layout)
        
        self.asset_list = QListWidget(right_widget)  # Explicit parent
        self.asset_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.asset_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.asset_list.customContextMenuRequested.connect(self.showAssetContextMenu)
        self.asset_list.itemSelectionChanged.connect(self.onAssetSelectionChanged)
        # Set the asset list to word wrap so long paths are readable
        self.asset_list.setWordWrap(True)
        self.asset_list.setTextElideMode(Qt.ElideMiddle)
        # Adjust the height to accommodate wrapped text
        self.asset_list.setStyleSheet("QListWidget::item { padding: 4px; }")
        right_layout.addWidget(self.asset_list)
        
        # Add asset buttons
        asset_buttons_layout = QHBoxLayout()
        self.add_selected_btn = QPushButton("Add Selected", right_widget)
        self.add_selected_btn.clicked.connect(self.addSelectedAssetsToShot)
        asset_buttons_layout.addWidget(self.add_selected_btn)
        right_layout.addLayout(asset_buttons_layout)
        
        # Create a splitter with explicit parent
        splitter = QSplitter(self)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 500])
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Create a vertical layout for the main window
        main_window_layout = QVBoxLayout()
        main_window_layout.addWidget(splitter)
        
        # Bottom button
        bottom_widget = QWidget(self)  # Explicit parent
        button_layout = QVBoxLayout(bottom_widget)

        w_settings = QWidget(bottom_widget)  # Explicit parent
        lo_settings = QHBoxLayout(w_settings)
        chb_deleteKeys = QCheckBox("Delete Keys Outside Shot Range", w_settings)  # Explicit parent
        chb_deleteKeys.setChecked(True)
        lo_settings.addWidget(chb_deleteKeys)
        lo_settings.addStretch()
        button_layout.addWidget(w_settings)

        self.split_btn = QPushButton("Split Shots", bottom_widget)  # Explicit parent
        self.split_btn.setMinimumHeight(50)  # Taller button
        self.split_btn.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; font-size: 20px;")
        self.split_btn.clicked.connect(self.splitShots)
        
        button_layout.addWidget(self.split_btn)
        
        # Add bottom widget to the main window layout
        main_window_layout.addWidget(bottom_widget)
        
        # Set the main window layout
        self.setLayout(main_window_layout)
        
    def populateAllAssets(self):
        """Populate all available assets in the scene with long names"""
        self.all_assets = []
        # Get all transforms in the scene as potential assets
        transforms = cmds.ls(type="transform", long=True)  # Use long=True to get full paths
        for transform in transforms:
            # Skip camera and sequencer related transforms
            if ("sequencer" in transform.lower() or 
                "shot" in transform.lower() or 
                transform.startswith("|persp") or 
                transform.startswith("|front") or 
                transform.startswith("|side") or 
                transform.startswith("|top")):
                continue
            
            # Skip empty transform groups with no shapes
            shapes = cmds.listRelatives(transform, shapes=True)
            if not shapes and not cmds.listRelatives(transform, children=True):
                continue
                
            self.all_assets.append(transform)

        self.all_assets = sorted(self.all_assets, key=lambda s: s.lower())
        
        return self.all_assets
    
    def getDefaultAssetsForShot(self, shot):
        """Get default assets for a shot (camera and Layout group if it exists)"""
        default_assets = set()
        
        # Get the camera for this shot
        cam = cmds.shot(shot, q=True, currentCamera=True)
        if cam:
            # Get the long path for the camera
            cam_long = cmds.ls(cam, long=True)
            if cam_long:
                default_assets.add(cam_long[0])
        
        # Check if Layout group exists and add it
        layout_groups = cmds.ls("*Layout*", long=True, type="transform")
        for layout in layout_groups:
            if cmds.objExists(layout):
                default_assets.add(layout)
        
        return default_assets
    
    def populateShots(self):
        """Get all shots from Maya's sequencer and populate the list"""
        self.shot_list.clear()
        
        # Get shots from Maya
        shots = cmds.ls(type="shot") or []
        
        # First, prepare all assets for selection
        # Populate all_assets if not already populated
        if not self.all_assets:
            self.populateAllAssets()
        
        for shot in shots:
            # Get shot name
            shot_name = cmds.getAttr(shot + ".shotName")
            
            # By default, only assign the shot's camera and Layout group if it exists
            if shot not in self.shot_asset_selections:
                self.shot_asset_selections[shot] = self.getDefaultAssetsForShot(shot)
            
            # Create list item with asset count
            asset_count = len(self.shot_asset_selections[shot])
            item = QListWidgetItem("%s (%s)" % (shot_name, asset_count))
            item.setData(Qt.UserRole, shot)  # Store the Maya shot node
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            
            self.shot_list.addItem(item)
            
        # Select first shot by default if any exist
        if self.shot_list.count() > 0:
            self.shot_list.setCurrentRow(0)
            self.onShotSelected(self.shot_list.item(0))
            
    def populateAssets(self):
        """Populate assets list for the current shot"""
        self.asset_list.clear()
        
        # Get current selected shot
        current_item = self.shot_list.currentItem()
        if not current_item:
            return
        
        shot_node = current_item.data(Qt.UserRole)
        
        # If we haven't populated all_assets yet or need to refresh
        if not self.all_assets:
            self.populateAllAssets()
        
        # Ensure this shot has a selection set initialized
        if shot_node not in self.shot_asset_selections:
            # By default, only include camera and Layout group
            self.shot_asset_selections[shot_node] = self.getDefaultAssetsForShot(shot_node)
        
        # Initial population with assigned assets only
        self.updateAssetList()
            
    def updateAssetList(self):
        """Update the asset list based on current shot selection"""
        self.asset_list.clear()
        
        # Get selected shots
        current_items = self.shot_list.selectedItems()
        if not current_items:
            return
        
        # If multiple shots are selected, show assets common to all selected shots
        selected_shots = [item.data(Qt.UserRole) for item in current_items]
        
        # Get assets that are selected in all shots
        if len(selected_shots) > 1:
            # Find common assets among all selected shots
            common_assets = self.shot_asset_selections.get(selected_shots[0], set())
            for shot in selected_shots[1:]:
                common_assets = common_assets.intersection(self.shot_asset_selections.get(shot, set()))
            selected_assets = common_assets
        else:
            # Single shot selection
            current_shot = selected_shots[0]
            # Ensure this shot has a selection set initialized with default assets
            if current_shot not in self.shot_asset_selections:
                self.shot_asset_selections[current_shot] = self.getDefaultAssetsForShot(current_shot)
                
            selected_assets = self.shot_asset_selections.get(current_shot, set())
        
        # Filter assets if filter is set
        filter_text = self.filter_edit.text().lower()
        
        # Only show assigned assets (not all assets)
        filtered_assets = [asset for asset in selected_assets 
                            if not filter_text or filter_text in asset.lower()]
        
        # Add assigned assets to the list
        for asset in sorted(filtered_assets, key=lambda s: s.lower()):
            item = QListWidgetItem(asset)
            
            # Set tooltip to show the full path for easier reference
            item.setToolTip(asset)
                
            self.asset_list.addItem(item)
        
        # Update the shot status display
        self.updateShotStatus()
        
    def showShotContextMenu(self, position):
        """Display context menu for the shot list"""
        menu = QMenu(self)
        
        # Always show these options
        check_all_action = menu.addAction("Check All Shots")
        uncheck_all_action = menu.addAction("Uncheck All Shots")
        menu.addSeparator()
        
        # Options for selected items
        selected_items = self.shot_list.selectedItems()
        if selected_items:
            check_action = menu.addAction("Check Selected")
            uncheck_action = menu.addAction("Uncheck Selected")
            
        # Add refresh option
        menu.addSeparator()
        refresh_action = menu.addAction("Refresh Shot List")
        
        action = menu.exec_(self.shot_list.mapToGlobal(position))
        
        # Handle action
        if selected_items and action == check_action:
            for item in selected_items:
                item.setCheckState(Qt.Checked)
        elif selected_items and action == uncheck_action:
            for item in selected_items:
                item.setCheckState(Qt.Unchecked)
        elif action == check_all_action:
            for i in range(self.shot_list.count()):
                self.shot_list.item(i).setCheckState(Qt.Checked)
        elif action == uncheck_all_action:
            for i in range(self.shot_list.count()):
                self.shot_list.item(i).setCheckState(Qt.Unchecked)
        elif action == refresh_action:
            # Remember selected shots
            current_selection = self.shot_list.selectedItems()
            selected_shot_nodes = [item.data(Qt.UserRole) for item in current_selection]
            
            # Refresh the shot list
            self.populateShots()
            
            # Restore selection if possible
            if selected_shot_nodes:
                for i in range(self.shot_list.count()):
                    item = self.shot_list.item(i)
                    if item.data(Qt.UserRole) in selected_shot_nodes:
                        item.setSelected(True)
    
    def showAssetContextMenu(self, position):
        """Display context menu for the asset list"""
        menu = QMenu(self)
        
        # Options for selected items
        selected_items = self.asset_list.selectedItems()
        if selected_items:
            remove_selected_action = menu.addAction("Remove Selected")
            select_in_scene_action = menu.addAction("Select in Scene")
            menu.addSeparator()
        
        # Clear option
        clear_action = menu.addAction("Clear All")
        
        # Add selection sync and refresh options
        menu.addSeparator()
        get_selection_action = menu.addAction("Get Selection From Outliner")
        refresh_action = menu.addAction("Refresh Asset List")
        
        action = menu.exec_(self.asset_list.mapToGlobal(position))
        
        # Handle action
        if selected_items and action == remove_selected_action:
            self.removeSelectedAssets()
        elif selected_items and action == select_in_scene_action:
            self.selectAssetsInScene()
        elif action == clear_action:
            self.clearAssetList()
        elif action == get_selection_action:
            self.getSelectionFromOutliner()
        elif action == refresh_action:
            # Remember the selected assets
            current_selection = self.asset_list.selectedItems()
            selected_assets = [item.text() for item in current_selection]
            
            # Refresh all_assets with long names
            self.populateAllAssets()
            
            # Refresh the asset list
            self.populateAssets()
            
            # Restore selection if possible
            if selected_assets:
                for i in range(self.asset_list.count()):
                    item = self.asset_list.item(i)
                    if item.text() in selected_assets:
                        item.setSelected(True)
    
    def onAssetSelectionChanged(self):
        """When assets are selected in the list, select them in Maya too"""
        selected_items = self.asset_list.selectedItems()
        if not selected_items:
            return
            
        # Get all the assets to select in Maya
        assets_to_select = []
        for item in selected_items:
            asset_path = item.text()
            if cmds.objExists(asset_path):
                assets_to_select.append(asset_path)
        
        # Select the assets in Maya if any exist
        if assets_to_select:
            cmds.select(assets_to_select, replace=True)
        
    def addSelectedAssetsToShot(self):
        """Add Maya-selected assets to the current shot"""
        # Get currently selected shots in UI
        selected_shots = self.shot_list.selectedItems()
        if not selected_shots:
            return
        
        # Get Maya-selected objects
        maya_selection = cmds.ls(selection=True, long=True)
        if not maya_selection:
            QMessageBox.warning(self, "Add Selected", "No objects selected in Maya scene.")
            return
        
        # Add selected assets to each selected shot
        for shot_item in selected_shots:
            shot_node = shot_item.data(Qt.UserRole)
            if shot_node not in self.shot_asset_selections:
                self.shot_asset_selections[shot_node] = set()
            
            # Add the selected assets
            self.shot_asset_selections[shot_node].update(maya_selection)
        
        # Refresh the asset list to show the newly added assets
        self.updateAssetList()
        
    def removeSelectedAssets(self):
        """Remove selected assets from the current shot"""
        # Get selected shots
        selected_shots = self.shot_list.selectedItems()
        if not selected_shots:
            return
        
        # Get selected assets in the list
        selected_assets = self.asset_list.selectedItems()
        if not selected_assets:
            return
        
        assets_to_remove = [item.text() for item in selected_assets]
        
        # Remove assets from each selected shot
        for shot_item in selected_shots:
            shot_node = shot_item.data(Qt.UserRole)
            if shot_node in self.shot_asset_selections:
                self.shot_asset_selections[shot_node] = self.shot_asset_selections[shot_node] - set(assets_to_remove)
        
        # Refresh the asset list
        self.updateAssetList()
        
    def clearAssetList(self):
        """Clear all assets from the selected shots"""
        # Get selected shots
        selected_shots = self.shot_list.selectedItems()
        if not selected_shots:
            return
        
        # Confirm operation
        result = QMessageBox.question(
            self, 
            "Clear Assets", 
            "Remove all assets from the selected shot(s)?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
        
        # Reset assets for each shot to just the defaults
        for shot_item in selected_shots:
            shot_node = shot_item.data(Qt.UserRole)
            self.shot_asset_selections[shot_node] = set()
        
        # Refresh the asset list
        self.updateAssetList()
        
    def selectAssetsInScene(self):
        """Select the currently selected assets in the Maya scene"""
        selected_items = self.asset_list.selectedItems()
        if not selected_items:
            return
            
        # Get all the assets to select in Maya
        assets_to_select = []
        for item in selected_items:
            asset_path = item.text()
            if cmds.objExists(asset_path):
                assets_to_select.append(asset_path)
        
        # Select the assets in Maya if any exist
        if assets_to_select:
            cmds.select(assets_to_select, replace=True)
        else:
            cmds.select(clear=True)
            QMessageBox.warning(self, "Select in Scene", "None of the selected assets exist in the Maya scene.")
    
    def getSelectionFromOutliner(self):
        """Get current Maya selection and select corresponding items in the asset list"""
        # Get current Maya selection
        maya_selection = cmds.ls(selection=True, long=True)
        if not maya_selection:
            QMessageBox.information(self, "Get Selection", "No objects are currently selected in Maya.")
            return
        
        # Clear current selection in asset list
        self.asset_list.clearSelection()
        
        # Try to find and select these items in the asset list
        selected_count = 0
        for i in range(self.asset_list.count()):
            item = self.asset_list.item(i)
            asset_path = item.text()
            
            if asset_path in maya_selection:
                item.setSelected(True)
                selected_count += 1
        
        if selected_count == 0:
            QMessageBox.information(
                self, 
                "Get Selection", 
                "None of the selected objects in Maya are in the current asset list."
            )
        else:
            # Ensure the asset list has focus and the selected items are visible
            self.asset_list.setFocus()
            if selected_count == 1:
                self.asset_list.scrollToItem(self.asset_list.selectedItems()[0])
            else:
                # If multiple items are selected, scroll to the first one
                self.asset_list.scrollToItem(self.asset_list.selectedItems()[0])
    
    def updateAssetSelections(self):
        """Update selection sets after context menu actions"""
        selected_shots = self.shot_list.selectedItems()
        if not selected_shots:
            return
            
        # The assets are now managed via the add/remove methods instead of checkboxes
        # This method is kept for compatibility
        
        # Update the shot status display
        self.updateShotStatus()
            
    def onShotSelected(self, item):
        """Handle shot selection changes"""
        # Update the asset list to show assets for this shot
        self.updateAssetList()
        
        # Update shot status display
        self.updateShotStatus()
        
    def updateShotStatus(self):
        """Update the shot list items to show number of selected assets"""
        for i in range(self.shot_list.count()):
            item = self.shot_list.item(i)
            shot = item.data(Qt.UserRole)
            selected_assets = len(self.shot_asset_selections.get(shot, set()))
            
            # Get shot name without count suffix
            shot_name = cmds.getAttr(shot + ".shotName")
            item.setText("%s (%s)" % (shot_name, selected_assets))

    def filterAssets(self, text):
        """Filter assets based on text input"""
        # Store current shot selection
        selected_items = self.shot_list.selectedItems()
        if selected_items:
            current_shot = selected_items[0].data(Qt.UserRole)
            self.updateAssetList()
        
    def splitShots(self):
        """Perform the shot splitting operation"""
        # Get checked shots
        shots_to_split = []
        for i in range(self.shot_list.count()):
            item = self.shot_list.item(i)
            if item.checkState() == Qt.Checked:
                shot_node = item.data(Qt.UserRole)
                # Get associated assets
                assets = self.shot_asset_selections.get(shot_node, set())
                shots_to_split.append((shot_node, assets))
        
        if not shots_to_split:
            QMessageBox.warning(self, "Shot Split", "No shots selected for splitting.")
            return
            
        # Confirm operation
        result = QMessageBox.question(
            self,
            "Confirm Split",
            "You are about to split %s shot(s). Continue?" % len(shots_to_split),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            self._perform_split(shots_to_split)

    def saveNewShotFile(self, shot_name, start, end):
        """Save the current scene to a new file"""
        if self.plugin:
            ctx = self.plugin.core.getCurrentScenefileData()
            if ctx and ctx.get("sequence") and ctx.get("department") and ctx.get("task"):
                seq = ctx["sequence"]
                dep = ctx.get("department")
                task = ctx.get("task")
                entity = {
                    "type": "shot",
                    "shot": shot_name,
                    "sequence": seq,
                }
                result = self.plugin.core.entities.createShot(entity, frameRange=[int(start), int(end)])
                if result:
                    self.plugin.core.entities.createDepartment(dep, entity)
                    self.plugin.core.entities.createCategory(entity, dep, task)
                    self.plugin.core.entities.createVersionFromCurrentScene(result["entity"], dep, task)
                    return

        try:
            # Build new filename
            scene_path = cmds.file(q=True, sn=True)
            scene_dir = os.path.dirname(scene_path)
            new_file = os.path.join(scene_dir, "%s.ma" % shot_name)
            cmds.file(rename=new_file)
            cmds.file(save=True, type="mayaAscii")
            print("Saved new shot file: %s" % new_file)
        except Exception as e:
            print("Error saving file %s: %s" % (new_file, str(e)))
            raise e
            
    def _perform_split(self, shots_to_split):
        """Perform the actual splitting operation"""
        # Ensure scene is saved
        scene_path = cmds.file(q=True, sn=True)
        if not scene_path:
            QMessageBox.warning(self, "Shot Split", "Please save your scene before running this tool.")
            return

        scene_dir = os.path.dirname(scene_path)
        original_file = cmds.file(q=True, sceneName=True)
        
        # Create progress dialog
        progress = QProgressDialog("Preparing to split shots...", "Cancel", 0, len(shots_to_split), self)
        progress.setWindowTitle("Shot Split Progress")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)  # Show immediately
        progress.setValue(0)
        QApplication.processEvents()

        if self.plugin:
            self.plugin.core.sceneOpenChecksEnabled = False
        
        # Store current undo state
        current_undo_state = cmds.undoInfo(q=True, state=True)
        cmds.undoInfo(state=True)  # Make sure undo is enabled
        
        # Process each shot
        for i, (shot, assets) in enumerate(shots_to_split):
            # Update progress dialog
            shot_name = cmds.getAttr(shot + ".shotName") if cmds.objExists(shot) else "Shot %s" % (i+1)
            progress.setLabelText("Processing shot %s of %s: %s" % (i+1, len(shots_to_split), shot_name))
            progress.setValue(i)
            QApplication.processEvents()
            
            # Check if the user canceled the operation
            if progress.wasCanceled():
                cmds.file(original_file, open=True, force=True)
                cmds.undoInfo(state=current_undo_state)
                if self.plugin:
                    self.plugin.core.sceneOpenChecksEnabled = True
                return
            if i > 0:
                # Instead of reloading, undo all changes from the previous shot processing
                # cmds.undo()
                
                # Verify the undo worked correctly by checking if nodes exist
                # If undo failed for any reason, reload the original scene as fallback
                # if not cmds.objExists(shot):
                    # cmds.warning("Undo didn't restore all nodes properly. Falling back to reload.")
                cmds.file(original_file, open=True, force=True)
            
            start = cmds.getAttr("%s.startFrame" % shot)
            end = cmds.getAttr("%s.endFrame" % shot)
            shot_name = cmds.getAttr(shot + ".shotName")
            
            # Set timeline
            cmds.playbackOptions(
                animationStartTime=start,
                animationEndTime=end,
                minTime=start,
                maxTime=end,
            )
            cmds.currentTime(start, edit=True)

            prev_file = cmds.file(q=True, sceneName=True)

            # Keep only this shot and the selected assets
            cmds.undoInfo(openChunk=True)
            try:
                # Handle referenced objects first
                # Get all references
                references = cmds.ls(references=True) or []
                referenced_nodes = {}
                
                # Build a dictionary of referenced nodes and their reference node
                for ref in references:
                    nodes = cmds.referenceQuery(ref, nodes=True, dagPath=True) or []
                    longNodes = cmds.ls(nodes, long=True)
                    for node in longNodes:
                        referenced_nodes[node] = ref
                
                # Create sets to track what to keep and what to remove
                references_to_remove = set()
                references_to_keep = set()
                
                # Check if any referenced nodes are in our assets list
                for asset in assets:
                    if asset in referenced_nodes:
                        ref = referenced_nodes[asset]
                        references_to_keep.add(ref)
                
                # Identify references to remove (those not containing any assets)
                for ref in references:
                    if ref not in references_to_keep:
                        references_to_remove.add(ref)
                
                # Remove references that don't contain assets
                for ref in references_to_remove:
                    try:
                        cmds.file(referenceNode=ref, removeReference=True)
                    except Exception as e:
                        print("Warning: Failed to remove reference %s: %s" % (ref, str(e)))
                
                # Now delete all non-referenced nodes not in assets list
                all_nodes = cmds.ls(type="transform", long=True)
                nodes_to_delete = []
                
                # Build a set of nodes to keep - including parents and children of assets
                nodes_to_keep = set()
                
                # First add all assets
                for asset in assets:
                    if cmds.objExists(asset):
                        nodes_to_keep.add(asset)
                        
                        # Add all parent nodes in hierarchy
                        parent = cmds.listRelatives(asset, parent=True, fullPath=True)
                        while parent:
                            parent_path = parent[0]
                            nodes_to_keep.add(parent_path)
                            parent = cmds.listRelatives(parent_path, parent=True, fullPath=True)
                        
                        # Add all children nodes
                        children = cmds.listRelatives(asset, allDescendents=True, fullPath=True) or []
                        for child in children:
                            nodes_to_keep.add(child)
                
                # Collect nodes to delete
                for node in all_nodes:
                    try:
                        # Skip if it's the shot node or in our assets list or their parents/children
                        if node == shot or node in nodes_to_keep:
                            continue
                            
                        # Skip if it's referenced (these were handled above)
                        if cmds.referenceQuery(node, isNodeReferenced=True):
                            continue
                            
                        # Skip default cameras and nodes
                        if (node.startswith("|persp") or 
                            node.startswith("|front") or 
                            node.startswith("|side") or 
                            node.startswith("|top") or
                            "sequencer" in node.lower() or
                            "defaultLayer" in node or
                            "defaultLightSet" in node or
                            "defaultObjectSet" in node):
                            continue
                        
                        # Add to delete list
                        nodes_to_delete.append(node)
                    except Exception as e:
                        print("Warning: Error processing node %s: %s" % (node, str(e)))
                
                # Delete collected nodes
                if nodes_to_delete:
                    try:
                        cmds.delete(nodes_to_delete)
                    except Exception as e:
                        print("Warning: Failed to delete some nodes: %s" % str(e))
                
                # Save the file
                self.saveNewShotFile(shot_name, start, end)
            finally:
                cmds.undoInfo(closeChunk=True)
        
        # Update progress for completing the operation
        progress.setLabelText("Restoring original scene...")
        progress.setValue(len(shots_to_split))
        QApplication.processEvents()
        
        # After processing all shots, try to restore the original scene state using undo
        try:
            # cmds.undo()
            
            # Verify the scene has been properly restored (check if the first shot exists)
            # if shots_to_split and not cmds.objExists(shots_to_split[0][0]):
                # cmds.warning("Final undo didn't restore the scene properly. Falling back to reload.")
            cmds.file(original_file, open=True, force=True)
        except Exception as e:
            # If undo fails for any reason, fall back to reloading the file
            print("Warning: Scene restore with undo failed: %s" % str(e))
            cmds.file(original_file, open=True, force=True)
        
        # Restore original undo state
        cmds.undoInfo(state=current_undo_state)
        
        if self.plugin:
            self.plugin.core.sceneOpenChecksEnabled = True
            if self.plugin.core.pb:
                self.plugin.core.pb.refreshUI()
        
        # Close the progress dialog
        progress.close()

        QMessageBox.information(self, "Shot Split", "Split shots completed successfully!")
        self.accept()
