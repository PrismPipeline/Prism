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
import platform
import random
import logging
import tempfile
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import nuke
if nuke.env.get("gui"):
    try:
        from nukescripts import flipbooking, renderdialog, fnFlipbookRenderer
    except:
        pass

try:
    from qtpy.QtCore import *
    from qtpy.QtGui import *
    from qtpy.QtWidgets import *
except:
    if nuke.NUKE_VERSION_MAJOR >= 16:
        from PySide6.QtCore import *
        from PySide6.QtGui import *
        from PySide6.QtWidgets import *
    else:
        from PySide2.QtCore import *
        from PySide2.QtGui import *
        from PySide2.QtWidgets import *


try:
    from PrismUtils.Decorators import err_catcher as err_catcher
except:
    # err_catcher = lambda name: lambda func, *args, **kwargs: func(*args, **kwargs)
    from functools import wraps
    def err_catcher(name: str) -> Any:
        """Create error catching decorator (fallback when Prism not available).
        
        Args:
            name: Module name for error logging
            
        Returns:
            Decorator function
        """
        return lambda x, y=name, z=False: err_handler(x, name=y, plugin=z)

    def err_handler(func: Any, name: str = "", plugin: bool = False) -> Any:
        """Wrap function with error handling (fallback when Prism not available).
        
        Args:
            func: Function to wrap
            name: Module name for error logging
            plugin: Whether this is a plugin function
            
        Returns:
            Wrapped function
        """
        @wraps(func)
        def func_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Execute wrapped function (no-op wrapper when Prism unavailable)."""
            return func(*args, **kwargs)

        return func_wrapper


logger = logging.getLogger(__name__)


class Prism_Nuke_Functions(object):
    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize Nuke functions module.
        
        Sets up callbacks for scene events, file drops, environment variables,
        and OCIO refresh handlers.
        
        Args:
            core: The Prism core instance
            plugin: The plugin instance
        """
        self.core = core
        self.plugin = plugin
        self.outputEntityOverride = None

        self.isRendering = {}
        self.core.registerCallback(
            "postSaveScene", self.postSaveScene, plugin=self.plugin
        )
        self.core.registerCallback("postBuildScene", self.postBuildScene, plugin=self.plugin)
        self.core.registerCallback(
            "onProjectBrowserStartup", self.onProjectBrowserStartup, plugin=self.plugin
        )
        self.core.registerCallback(
            "onPreMediaPlayerDragged", self.onPreMediaPlayerDragged, plugin=self.plugin
        )
        self.core.registerCallback(
            "onStateManagerOpen", self.onStateManagerOpen, plugin=self.plugin
        )
        self.core.registerCallback(
            "productSelectorContextMenuRequested", self.productSelectorContextMenuRequested, plugin=self.plugin
        )
        self.core.registerCallback(
            "updatedEnvironmentVars", self.updatedEnvironmentVars, plugin=self.plugin
        )
        if "OCIO" in [item["key"] for item in self.core.users.getUserEnvironment()]:
            self.refreshOcio()

        self.core.registerCallback(
            "postInitialize", self.postInitialize, plugin=self.plugin
        )
        self.core.registerCallback(
            "onSceneOpen", self.onSceneOpen, plugin=self.plugin
        )
        self.core.registerCallback(
            "sceneSaved", self.sceneSaved, plugin=self.plugin
        )
        nuke.addOnUserCreate(self.refreshOcio, nodeClass="Root")
        self.isRenderingFlipbook = False

        self.core.plugins.monkeyPatch(self.core.media.getOIIO, self.getOIIO, self.plugin)
        if self.core.status not in ["starting", "waitingForDelayedPlugins"]:
            self.addCallbacks()

    @err_catcher(name=__name__)
    def getOIIO(self) -> Any:
        """Get OpenImageIO module if loading is enabled in config.

        Returns:
            OIIO module if loadOIIO is True, None otherwise
        """
        if not self.getLoadOIIO():
            return None

        return self.core.plugins.callUnpatchedFunction(self.core.media.getOIIO)

    @err_catcher(name=__name__)
    def getLoadOIIO(self) -> bool:
        """Check if OIIO loading is enabled in config.
        
        Returns:
            True if OIIO should be loaded, False otherwise
        """
        return self.core.getConfig("nuke", "loadOIIO", dft=False, config="user")

    @err_catcher(name=__name__)
    def setLoadOIIO(self, value: bool) -> None:
        """Set OIIO loading preference in config.
        
        Args:
            value: True to enable OIIO loading, False to disable
        """
        self.core.setConfig("nuke", "loadOIIO", value, config="user")

    @err_catcher(name=__name__)
    def startup(self, origin: Any) -> None:
        """Execute Nuke plugin startup sequence.
        
        Initializes Qt parent, adds plugin paths, menus, and callbacks.
        
        Args:
            origin: The Prism core instance initiating startup
        """
        if self.core.uiAvailable:
            origin.timer.stop()

            for obj in QApplication.topLevelWidgets():
                if (
                    obj.inherits("QMainWindow")
                    and obj.metaObject().className() == "Foundry::UI::DockMainWindow"
                ):
                    nukeQtParent = obj
                    break
            else:
                nukeQtParent = QWidget()

            # origin.messageParent = QWidget()
            # origin.messageParent.setParent(nukeQtParent, Qt.Window)
            origin.messageParent = nukeQtParent
            # if platform.system() != "Windows" and self.core.useOnTop:  # not needed in newer Nuke versions and seems to crash Nuke
            #     origin.messageParent.setWindowFlags(
            #         origin.messageParent.windowFlags() ^ Qt.WindowStaysOnTopHint
            #     )

        self.addPluginPaths()
        if self.core.uiAvailable:
            self.addMenus()

        self.addCallbacks()

    @err_catcher(name=__name__)
    def addPluginPaths(self) -> None:
        """Add Prism Gizmos directory to Nuke's plugin path."""
        gdir = os.path.join(
            os.path.abspath(os.path.dirname(os.path.dirname(__file__))), "Gizmos"
        )
        gdir = gdir.replace("\\", "/")
        nuke.pluginAddPath(gdir)

    @err_catcher(name=__name__)
    def getMultiShotEnabled(self) -> bool:
        """Check if Nuke multi-shot mode is enabled.
        
        Returns:
            True if Nuke 17+ and PRISM_NUKE_ENABLE_MULTISHOT=1
        """
        return (nuke.NUKE_VERSION_MAJOR >= 17) and os.getenv("PRISM_NUKE_ENABLE_MULTISHOT", "0") == "1"

    @err_catcher(name=__name__)
    def addMenus(self) -> None:
        """Add Prism menu items to Nuke's menu bar and toolbar."""
        nuke.menu("Nuke").addCommand("Prism/Save", self.saveScene, "Ctrl+s")
        nuke.menu("Nuke").addCommand("Prism/Save Version", self.core.saveScene, "Alt+Shift+s")
        nuke.menu("Nuke").addCommand("Prism/Save Comment...", self.core.saveWithComment, "Ctrl+Shift+S")
        nuke.menu("Nuke").addCommand("Prism/Project Browser...", self.core.projectBrowser)
        nuke.menu("Nuke").addCommand("Prism/Settings...", self.core.prismSettings)
        nuke.menu("Nuke").addCommand("Prism/Manage Media Versions...", self.openMediaVersionsDialog)
        if self.getMultiShotEnabled():
            nuke.menu("Nuke").addCommand("Prism/Import Shots...", self.onImportShotsTriggered)

        nuke.menu("Nuke").addCommand("Prism/Export Nodes...", self.onExportTriggered)

        toolbar = nuke.toolbar("Nodes")
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "p_tray.png"
        )
        toolbar.addMenu("Prism", icon=iconPath)
        useReadPrism = self.core.getConfig("nuke", "useReadPrism", dft=True, config="user")
        if useReadPrism:
            nuke.menu("Nuke").addCommand("Prism/Read...", self.createReadWithBrowse, "r", shortcutContext=2)
        else:
            nuke.menu("Nuke").addCommand("Prism/Read...", self.createReadWithBrowse)

        useWritePrism = self.core.getConfig("nuke", "useWritePrism", dft=False, config="user")
        if useWritePrism:
            toolbar.addCommand("Prism/WritePrism", lambda: nuke.createNode("WritePrism"), "w", shortcutContext=2)

    @err_catcher(name=__name__)
    def postInitialize(self):
        self.refreshNukeShotMenu()

    @err_catcher(name=__name__)
    def unregister(self):
        nuke.removeOnScriptLoad(self.core.sceneOpen)
        nuke.removeFilenameFilter(self.expandEnvVarsInFilepath)
        nuke.removeOnScriptSave(self.core.scenefileSaved)
        nuke.removeOnUserCreate(self.onUserNodeCreated)
        nuke.removeOnScriptClose(self.onScriptClosed)
        if self.getMultiShotEnabled():
            nuke.removeAfterUserSetGsvValue(self.onAfterUserSetGsvValue)

    @err_catcher(name=__name__)
    def onSceneOpen(self, filepath):
        if not self.getMultiShotEnabled():
            return

        self.refreshNukeShotMenu()
        shotname = None
        if not os.getenv("prism_source_scene"):
            data = self.core.getScenefileData(filepath)
            if data and data.get("shot") == "_sequence":
                shotNames = self.getShotnamesForMenu()
                if shotNames:
                    shotname = shotNames[0]
            else:
                shotname = self.core.entities.getShotName(data) or ""

        elif os.getenv("PRISM_GSV_SHOT"):
            shotname = os.getenv("PRISM_GSV_SHOT")

        if shotname is not None:
            self.setShot(shotname)

    @err_catcher(name=__name__)
    def sceneSaved(self):
        self.refreshNukeShotMenu()

    @err_catcher(name=__name__)
    def onScriptClosed(self):
        self.refreshNukeShotMenu(clear=True)

    @err_catcher(name=__name__)
    def refreshNukeShotMenu(self, clear=False):
        if not self.getMultiShotEnabled():
            return

        if getattr(self, "nukeShotMenu", None):
            nuke.menu("Nuke").removeItem(self.nukeShotMenu.name())

        if clear:
            shotName = "-"
        else:
            gsv_knob = nuke.root()["gsv"]
            shotName = gsv_knob.getGsvValue("prism.shot") or "-"

        self.nukeShotMenu = nuke.menu("Nuke").addMenu("Shot: " + shotName)
        shotNames = self.getShotnamesForMenu()
        for shot in shotNames:
            if shot == shotName:
                shot += "  ✓"

            self.nukeShotMenu.addCommand(shot, lambda s=shot: self.setShot(s))

    @err_catcher(name=__name__)
    def setShot(self, shotName):
        gsv_knob = nuke.root()["gsv"]
        if shotName != gsv_knob.getGsvValue("prism.shot"):
            gsv_knob.setGsvValue("prism.shot", shotName)
            logger.debug("set context option: shot - %s" % shotName)

    @err_catcher(name=__name__)
    def getShotnamesForMenu(self):
        shotNames = self.getShotsFromScene()
        shotNames = sorted([s for s in shotNames], key=lambda x: x.lower())
        return shotNames

    @err_catcher(name=__name__)
    def addCallbacks(self) -> None:
        """Register Nuke callbacks for script events and file operations."""
        nuke.addOnScriptLoad(self.core.sceneOpen)
        nuke.addFilenameFilter(self.expandEnvVarsInFilepath)
        nuke.addOnScriptSave(self.core.scenefileSaved)
        nuke.addOnUserCreate(self.onUserNodeCreated)
        nuke.addOnScriptClose(self.onScriptClosed)
        if self.getMultiShotEnabled():
            nuke.addAfterUserSetGsvValue(self.onAfterUserSetGsvValue)

        import nukescripts
        nukescripts.drop.addDropDataCallback(self.dropHandler)

    @err_catcher(name=__name__)
    def dropHandler(self, mimeType: str, text: str) -> Optional[bool]:
        """Handle drag-and-drop of media files into Nuke.
        
        Creates Read nodes for dropped image sequences or files.
        
        Args:
            mimeType: MIME type of dropped data
            text: File or directory path that was dropped
            
        Returns:
            True if media was imported successfully, None otherwise
        """
        if not getattr(self.core, "projectPath", None):
            return

        text = text.replace("\\", "/")
        useRel = self.core.getConfig("nuke", "useRelativePaths", dft=False, config="user")
        try:
            isDir = os.path.isdir(text)
        except Exception:
            return None

        if isDir:
            srcs = self.core.media.getImgSources(text)
        elif os.path.isfile(text):
            srcs = [text]
        else:
            return

        success = False
        for src in srcs:
            if os.path.splitext(src)[1] not in self.core.media.supportedFormats:
                continue

            if "#"*self.core.framePadding not in src:
                src = self.core.media.getSequenceFromFilename(src)

            if "#"*self.core.framePadding in src:
                files = self.core.media.getFilesFromSequence(src)
                start, end = self.core.media.getFrameRangeFromSequence(files)
                if start and end and start != "?" and end != "?":
                    src += " %s-%s" % (start, end)

            if useRel and text.replace("\\", "/").startswith(self.core.projectPath.replace("\\", "/")):
                src = self.makePathRelative(src)

            read_node = nuke.createNode("Read", inpanel=False)
            read_node["file"].fromUserText(src)
            success = True
            
            if success:
                return True

    @err_catcher(name=__name__)
    def makePathRelative(self, path: str) -> str:
        """Convert absolute path to project-relative path using PRISM_JOB variable.
        
        Args:
            path: Absolute file path
            
        Returns:
            Path with project root replaced by %PRISM_JOB or %PRISM_JOB%
        """
        path = path.replace("\\", "/")
        prjPath = self.core.projectPath.replace("\\", "/").rstrip("/")
        newVars = (nuke.NUKE_VERSION_MAJOR >= 16) or (nuke.NUKE_VERSION_MAJOR == 15 and nuke.NUKE_VERSION_MINOR >= 2)
        if newVars:
            relPath = path.replace(prjPath, "%PRISM_JOB")
        else:
            relPath = path.replace(prjPath, "%PRISM_JOB%")

        return relPath

    @err_catcher(name=__name__)
    def expandEnvVarsInFilepath(self, path: str) -> str:
        """Expand environment variables in file paths.
        
        Replaces %PRISM_JOB% with actual project path when relative paths are enabled.
        
        Args:
            path: File path potentially containing environment variables
            
        Returns:
            Expanded file path
        """
        if not self.core.getConfig("nuke", "useRelativePaths", dft=False, config="user"):
            return path

        expanded_path = os.path.expandvars(path)
        if hasattr(self.core, "projectPath"):
            prjPath = self.core.projectPath.replace("\\", "/").rstrip("/")
            expanded_path = expanded_path.replace("%PRISM_JOB", prjPath)

        return expanded_path

    @err_catcher(name=__name__)
    def updatedEnvironmentVars(self, reason: str, envVars: List[Dict[str, str]], beforeRefresh: bool = False) -> None:
        """Handle environment variable updates.
        
        Refreshes OCIO configuration when OCIO environment variable changes.
        
        Args:
            reason: Reason for update (e.g., "refreshProject", "unloadProject")
            envVars: List of changed environment variables
            beforeRefresh: Whether this is called before project refresh
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
        """Refresh Nuke's OCIO color management configuration.
        
        Updates Nuke's root node to use custom OCIO config from environment variable.
        """
        ocio = os.getenv("OCIO", "")
        if ocio:
            r = nuke.root()
            try:
                r["colorManagement"].setValue("OCIO")
            except Exception:
                return

            r["OCIO_config"].setValue("custom")
            r["customOCIOConfigPath"].setValue(ocio.replace("\\", "/"))
            r.knob("reloadConfig").execute()

    @err_catcher(name=__name__)
    def sceneOpen(self, origin: Any) -> None:
        """Handle scene open event.
        
        Starts autosave timer if enabled.
        
        Args:
            origin: The Prism core instance
        """
        if self.core.shouldAutosaveTimerRun():
            origin.startAutosaveTimer()

        if os.getenv("PRISM_NUKE_CHECK_MEDIA_ON_SCENE_OPEN", "1") == "1":
            dlg = MediaVersionsDialog(self)
            if dlg.getOutdatedMedia():
                msgStr = "There are new media versions available."
                msg = self.core.popupQuestion(
                    msgStr,
                    buttons=["Show Versions...", "Ignore"],
                    icon=QMessageBox.Information,
                    escapeButton="Ignore",
                    default="Ignore",
                    doExec=False,
                )
                if not self.core.isStr(msg):
                    msg.buttonClicked.connect(self.onShowVersionsClicked)
                    msg.show()

        self.refreshWriteNodes()

    @err_catcher(name=__name__)
    def onShowVersionsClicked(self, button: Any) -> None:
        """Handle Show Versions button click from media update notification.
        
        Args:
            button: The button that was clicked
        """
        result = button.text()
        if result == "Show Versions...":
            self.openMediaVersionsDialog()

    @err_catcher(name=__name__)
    def getCurrentFileName(self, origin: Any, path: bool = True) -> str:
        """Get current Nuke script filename.
        
        Args:
            origin: The calling instance
            path: If True return full path, if False return basename only
            
        Returns:
            Current script filepath or empty string if no script loaded
        """
        try:
            currentFileName = nuke.value("root.name")
            if currentFileName:
                currentFileName = os.path.abspath(currentFileName)

        except:
            currentFileName = ""

        if currentFileName == "Root":
            currentFileName = ""

        if not path:
            currentFileName = os.path.basename(currentFileName)

        return currentFileName

    @err_catcher(name=__name__)
    def getCurrentSceneFiles(self, origin: Any) -> List[str]:
        """Get list of files associated with current scene.
        
        Args:
            origin: The calling instance
            
        Returns:
            List containing current scene filepath
        """
        return [self.core.getCurrentFileName()]

    @err_catcher(name=__name__)
    def getSceneExtension(self, origin: Any) -> str:
        """Get the default scene file extension.
        
        Args:
            origin: The calling instance
            
        Returns:
            Default Nuke script extension (.nk)
        """
        return self.sceneFormats[0]

    @err_catcher(name=__name__)
    def saveScene(self, origin: Optional[Any] = None, filepath: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> str:
        """Save the current Nuke script.
        
        Args:
            origin: The calling instance
            filepath: Destination filepath, or None to save to current location
            details: Dictionary of save details
            
        Returns:
            Saved filepath
        """
        if details is None:
            details = {}
        try:
            if filepath:
                return nuke.scriptSaveAs(filename=filepath, overwrite=1)
            else:
                return nuke.scriptSave()

        except:
            return ""

    @err_catcher(name=__name__)
    def getImportPaths(self, origin: Any) -> bool:
        """Get import paths from the scene.
        
        Args:
            origin: The calling instance
            
        Returns:
            False (not implemented for Nuke)
        """
        return False

    @err_catcher(name=__name__)
    def getFrameRange(self, origin: Any) -> List[float]:
        """Get current frame range from Nuke script.
        
        Args:
            origin: The calling instance
            
        Returns:
            List containing [start_frame, end_frame]
        """
        startframe = nuke.root().knob("first_frame").value()
        endframe = nuke.root().knob("last_frame").value()

        return [startframe, endframe]

    @err_catcher(name=__name__)
    def getCurrentFrame(self) -> float:
        """Get current frame number.
        
        Returns:
            Current frame in timeline
        """
        currentFrame = nuke.root().knob("frame").value()
        return currentFrame

    @err_catcher(name=__name__)
    def setCurrentFrame(self, frame: Union[int, float]) -> None:
        """Set current frame number.
        
        Args:
            frame: Frame number to set
        """
        nuke.root().knob("frame").setValue(float(frame))

    @err_catcher(name=__name__)
    def setFrameRange(self, origin: Any, startFrame: Union[int, float], endFrame: Union[int, float]) -> None:
        """Set frame range in Nuke script.
        
        Args:
            origin: The calling instance
            startFrame: First frame
            endFrame: Last frame
        """
        nuke.root().knob("first_frame").setValue(float(startFrame))
        nuke.root().knob("last_frame").setValue(float(endFrame))

    @err_catcher(name=__name__)
    def getFPS(self, origin: Any) -> Any:
        """Get frames per second from Nuke script.
        
        Args:
            origin: The calling instance
            
        Returns:
            Frames per second
        """
        return nuke.knob("root.fps")

    @err_catcher(name=__name__)
    def setFPS(self, origin: Any, fps: Union[int, float]) -> Any:
        """Set frames per second in Nuke script.
        
        Args:
            origin: The calling instance
            fps: Frames per second
            
        Returns:
            Result of nuke.knob() call
        """
        return nuke.knob("root.fps", str(fps))

    @err_catcher(name=__name__)
    def getResolution(self) -> List[int]:
        """Get resolution from Nuke script format.
        
        Returns:
            List containing [width, height]
        """
        resFormat = [nuke.root().width(), nuke.root().height()]
        return resFormat

    @err_catcher(name=__name__)
    def setResolution(self, width: Optional[int] = None, height: Optional[int] = None, pixelAspect: Optional[float] = None) -> Any:
        """Set resolution in Nuke script.
        
        Args:
            width: Image width in pixels
            height: Image height in pixels
            pixelAspect: Pixel aspect ratio
            
        Returns:
            Result of nuke.knob() call
        """
        if pixelAspect:
            return nuke.knob("root.format", "%s %s 0 0 %s %s %s" % (width, height, width, height, pixelAspect))
        else:
            return nuke.knob("root.format", "%s %s" % (width, height))

    @err_catcher(name=__name__)
    def getPixelAspectRatio(self) -> float:
        """Get pixel aspect ratio from Nuke script.
        
        Returns:
            Pixel aspect ratio
        """
        return nuke.root().pixelAspect()

    @err_catcher(name=__name__)
    def setPixelAspectRatio(self, pixelAspect: float) -> None:
        """Set pixel aspect ratio in Nuke script.
        
        Args:
            pixelAspect: Pixel aspect ratio
        """
        fmt = nuke.root().format()
        res = self.getResolution()
        self.setResolution(res[0], res[1], pixelAspect)

    @err_catcher(name=__name__)
    def updateNukeNodes(self) -> None:
        """Update selected Read nodes to latest media versions.
        
        Scans selected Read nodes and updates file paths to use the latest
        available versions from Prism's media products.
        """
        updatedNodes = []

        for i in nuke.selectedNodes():
            if i.Class() != "Read":
                continue

            curPath = i.knob("file").value()
            curPath = self.expandEnvVarsInFilepath(curPath)
            version = self.core.mediaProducts.getLatestVersionFromFilepath(curPath)
            if version and version["path"] not in curPath:
                filepattern = self.core.mediaProducts.getFilePatternFromVersion(version)
                filepaths = self.core.media.getFilesFromSequence(filepattern)
                if not filepaths:
                    sources = self.core.media.getImgSources(os.path.dirname(filepattern))
                    if not sources:
                        continue

                    filepattern = sources[0]

                if self.core.getConfig("nuke", "useRelativePaths", dft=False, config="user"):
                    filepattern = self.makePathRelative(filepattern)

                filepattern = filepattern.replace("\\", "/")
                i.knob("file").setValue(filepattern)
                updatedNodes.append(i)

        if len(updatedNodes) == 0:
            self.core.popup("No nodes were updated", severity="info")
        else:
            mStr = "%s nodes were updated:\n\n" % len(updatedNodes)
            for i in updatedNodes:
                mStr += i.name() + "\n"

            self.core.popup(mStr, severity="info")

    # @err_catcher(name=__name__)
    # def renderAllWritePrismNodes(self):
    #     wpNodes = [node for node in nuke.allNodes() if node.Class() == "WritePrism"]
    #     self.renderWritePrismNodes(wpNodes)

    # @err_catcher(name=__name__)
    # def renderSelectedWritePrismNodes(self):
    #     wpNodes = [node for node in nuke.selectedNodes() if node.Class() == "WritePrism"]
    #     self.renderWritePrismNodes(wpNodes)

    # @err_catcher(name=__name__)
    # def renderWritePrismNodes(self, nodes):
    #     for node in nodes:
    #         self.getOutputPath(node.node("WritePrismBase"), node)

    #     import nukescripts
    #     nukescripts.showRenderDialog(nodes, False)

    @err_catcher(name=__name__)
    def getCamNodes(self, origin: Any, cur: bool = False) -> List[str]:
        """Get list of cameras in the scene.
        
        Args:
            origin: The calling instance
            cur: If True, only return currently selected camera
            
        Returns:
            List of camera names
        """
        sceneCams = ["nuke"]
        return sceneCams

    @err_catcher(name=__name__)
    def getCamName(self, origin: Any, handle: Any) -> Any:
        """Get name of a camera from its handle.
        
        Args:
            origin: The calling instance
            handle: Camera handle
            
        Returns:
            Camera name (same as handle)
        """
        return handle

    @err_catcher(name=__name__)
    def isNodeValid(self, origin: Any, handle: Any) -> bool:
        """Check if a node handle is valid.
        
        Args:
            origin: The calling instance
            handle: Node handle to check
            
        Returns:
            True (all nodes considered valid in Nuke)
        """
        return True

    @err_catcher(name=__name__)
    def readNode_onBrowseClicked(self, node: Any, quiet: bool = False) -> None:
        """Handle Browse button click on Read node.
        
        Opens media browser dialog to select media files.
        
        Args:
            node: The Read node
            quiet: If True, suppress error popups
        """
        if hasattr(self, "dlg_media"):
            self.dlg_media.close()

        if not getattr(self.core, "projectPath", None):
            if not quiet:
                self.core.popup("There is no active project in Prism.")

            return

        self.dlg_media = ReadMediaDialog(self, node)
        self.dlg_media.mediaSelected.connect(lambda x: self.readNode_mediaSelected(node, x))
        self.dlg_media.show()

    @err_catcher(name=__name__)
    def readNode_mediaSelected(self, node: Any, version: Dict[str, Any]) -> None:
        """Handle media selection from browser for Read node.
        
        Sets the selected media version as the Read node's file path.
        
        Args:
            node: The Read node
            version: Selected media version context
        """
        mediaFiles = self.core.mediaProducts.getFilesFromContext(version)
        validFiles = self.core.media.filterValidMediaFiles(mediaFiles)
        if not validFiles:
            return

        validFiles = sorted(validFiles, key=lambda x: x if "cryptomatte" not in os.path.basename(x) else "zzz" + x)
        baseName, extension = os.path.splitext(validFiles[0])
        seqFiles = self.core.media.detectSequences(validFiles)
        if seqFiles:
            path = list(seqFiles)[0].replace("\\", "/")
            useRel = self.core.getConfig("nuke", "useRelativePaths", dft=False, config="user")
            if "#"*self.core.framePadding not in path:
                path = self.core.media.getSequenceFromFilename(path)

            if "#"*self.core.framePadding in path:
                files = self.core.media.getFilesFromSequence(path)
                start, end = self.core.media.getFrameRangeFromSequence(files)
                if start and end and start != "?" and end != "?":
                    path += " %s-%s" % (start, end)

            if useRel:
                path = self.makePathRelative(path)

            node.knob("file").fromUserText(path)

    @err_catcher(name=__name__)
    def readNode_onOpenInClicked(self, node: Any) -> None:
        """Handle Open In Explorer button click on Read node.
        
        Args:
            node: The Read node
        """
        self.core.openFolder(node.knob("file").value())

    @err_catcher(name=__name__)
    def createReadWithBrowse(self) -> None:
        """Create a new Read node and immediately open media browser."""
        readNode = nuke.createNode("Read")
        self.readNode_onBrowseClicked(readNode, quiet=True)

    @err_catcher(name=__name__)
    def getIdentifierFromNode(self, node: Any) -> str:
        """Get state identifier from a node's knobs.
        
        Args:
            node: The Nuke node
            
        Returns:
            Identifier string or empty string  if none found
        """
        try:
            idf = node.knob("identifier").evaluate()
        except Exception:
            idf = ""

        return idf

    @err_catcher(name=__name__)
    def getCommentFromNode(self, node: Any) -> str:
        """Get comment from a node's comment knob.
        
        Args:
            node: The Nuke node
            
        Returns:
            Comment string
        """
        try:
            comment = node.knob("comment").value()
        except Exception:
            comment = ""

        return comment

    @err_catcher(name=__name__)
    def sm_render_fixOutputPath(self, origin: Any, outputName: str, singleFrame: bool = False, state: Optional[Any] = None) -> str:
        """Fix output path for rendering (convert to relative if enabled).
        
        Args:
            origin: The calling instance
            outputName: Output file path
            singleFrame: Whether rendering a single frame
            state: The state manager state
            
        Returns:
            Fixed output path
        """
        if self.core.getConfig("nuke", "useRelativePaths", dft=False, config="user"):
            outputName = self.makePathRelative(outputName)

        return outputName

    @err_catcher(name=__name__)
    def getRenderVersionFromWriteNode(self, node: Any) -> Optional[str]:
        """Get render version string from Write node knobs.
        
        Args:
            node: The Write node or group
            
        Returns:
            Version string (e.g. "v0001") or None if autoversion enabled
        """
        version = None
        if node.knob("autoversion") and not node.knob("autoversion").value():
            intVersion = node.knob("renderversion").value()
            version = self.core.versionFormat % intVersion

        return version

    @err_catcher(name=__name__)
    def getOutputPath(self, node: Any, group: Optional[Any] = None, render: bool = False, updateValues: bool = True, force: bool = False, entity: Optional[Any] = None) -> str:
        """Get output path for a Write node.
        
        Generates output filepath based on task, file type, version, and location.
        
        Args:
            node: The Write node
            group: The node group (WritePrism gizmo)
            render: Whether this is for an actual render
            updateValues: Whether to update node knob values
            force: Force path calculation even in non-GUI mode
            entity: Optional entity to use for path calculation

        Returns:
            Output file path
        """
        if self.isRenderingFlipbook:
            return

        if not group:
            group = node

        if not nuke.env.get("gui") and not force:
            filename = group.knob("fileName").toScript()
            if render and self.core.getConfig("globals", "backupScenesOnPublish", config="project"):
                self.core.entities.backupScenefile(os.path.dirname(filename))

            return filename

        try:
            taskName = self.getIdentifierFromNode(group)
            comment = self.getCommentFromNode(group)
            fileType = group.knob("file_type").value()
            location = group.knob("location").value()
        except Exception as e:
            logger.warning("failed to get node knob values: %s" % str(e))
            return ""

        if not bool(location.strip()):
            location = "global"

        if not entity and self.outputEntityOverride:
            entity = self.outputEntityOverride

        version = self.getRenderVersionFromWriteNode(group)
        outputName = self.core.getCompositingOut(
            taskName,
            fileType,
            version,
            render,
            location,
            comment=comment,
            node=node,
            entity=entity,
        )

        isNukeAssist = "--nukeassist" in nuke.rawArgs
        if not self.isNodeRendering(node) and not isNukeAssist and updateValues or render:
            group.knob("fileName").setValue(outputName)
            # group.knob("fileName").clearFlag(0x10000000) # makes knob read-only, but leads to double property Uis

        return outputName

    @err_catcher(name=__name__)
    def startRender(
        self,
        node: Any,
        group: Optional[Any] = None,
        start: Optional[int] = None,
        end: Optional[int] = None,
        dependencies: Optional[List[Any]] = None,
        submit: Optional[bool] = None,
        _skipMultiShot: bool = False,
        entity: Optional[Any] = None,
        showSubmitUi: bool = True,
    ) -> Optional[bool]:
        """Start rendering a Write node.
        
        Either submits to render farm or renders locally.
        
        Args:
            node: The Write node
            group: The node group (WritePrism gizmo)
            start: Start frame
            end: End frame
            dependencies: List of dependency nodes 
            submit: Whether to submit to farm (overrides node knob)
            _skipMultiShot: Internal flag to bypass multi-shot dialog (used by NukeMultiShotRenderer)
            entity: Optional entity to use for path calculation
            
        Returns:
            True if render started successfully, None/False otherwise
        """
        if not group:
            group = node

        if not _skipMultiShot and self.getMultiShotEnabled():
            shots = self.getShotsFromScene()
            if shots:
                dlg = NukeMultiShotRenderer(self, node, group, start, end, dependencies, submit)
                dlg.exec_()
                return
            
        if entity:
            self.outputEntityOverride = entity

        submit = submit if submit is not None else group.knob("submitJob").value()
        if submit:
            return self.openFarmSubmitter(node, group, dependencies=dependencies, entity=entity, showSubmitUi=showSubmitUi)

        taskName = self.getIdentifierFromNode(group)
        if not taskName:
            self.core.popup("Please choose an identifier")
            return

        fileName = self.getOutputPath(node, group, force=True)
        if fileName == "FileNotInPipeline":
            self.core.showFileNotInProjectWarning(title="Warning")
            return

        if start is None and not self.core.uiAvailable:
            start = nuke.root().knob("first_frame").value()
            end = nuke.root().knob("last_frame").value()

        settings = {
            "outputName": fileName,
            "node": node,
            "group": group,
            "start": start,
            "end": end,
            "identifier": taskName,
            "entity": entity,
        }
        scenefile = self.core.getCurrentFileName()
        kwargs = {
            "state": self,
            "scenefile": scenefile,
            "settings": settings,
        }

        result = self.core.callback("preRender", **kwargs)
        for res in result:
            if isinstance(res, dict) and res.get("cancel", False):
                return [
                    "Nuke Render - error - %s" % res.get("details", "preRender hook returned False")
                ]

        self.core.saveScene(versionUp=False, prismReq=False)
        if start is None:
            node.knob("Render").execute()
        else:
            nuke.execute(node, start, end)

        self.outputEntityOverride = None
        self.getOutputPath(node, group)
        kwargs = {
            "state": self,
            "scenefile": scenefile,
            "settings": settings,
        }

        self.core.callback("postRender", **kwargs)
        return True

    @err_catcher(name=__name__)
    def showPrevVersions(self, node: Any, group: Optional[Any] = None) -> None:
        """Show version selection dialog for a Write node.
        
        Args:
            node: The Write node
            group: The node group (WritePrism gizmo)
        """
        if not group:
            group = node

        self.dlg_version = VersionDlg(self, node, group)
        if not self.dlg_version.isValid:
            return

        if group.knob("renderversion"):
            self.dlg_version.versionSelected.connect(lambda x: group.knob("autoversion").setValue(0))
            self.dlg_version.versionSelected.connect(group.knob("renderversion").setValue)

        self.dlg_version.show()

    @err_catcher(name=__name__)
    def startedRendering(self, node: Any, outputPath: str) -> None:
        """Mark a node as currently rendering.
        
        Args:
            node: The Write node that started rendering
            outputPath: Output file path being rendered
        """
        nodePath = node.fullName()
        self.isRendering[nodePath] = [True, outputPath]

        nodeName = "root." + node.fullName()
        parentName = ".".join(nodeName.split(".")[:-1])
        group = nuke.toNode(parentName)
        if not group or group.Class() != "WritePrism":
            group = node

        prevKnob = group.knob("prevFileName")
        if prevKnob:
            prevKnob.setValue(outputPath.replace("\\", "/"))
            prevKnobE = group.knob("prevFileNameEdit")
            if prevKnobE:
                prevKnobE.setValue(outputPath.replace("\\", "/"))

    @err_catcher(name=__name__)
    def isNodeRendering(self, node: Any) -> bool:
        """Check if a node is currently rendering.
        
        Args:
            node: The Write node to check
            
        Returns:
            True if node is rendering, False otherwise
        """
        nodePath = node.fullName()
        rendering = nodePath in self.isRendering and self.isRendering[nodePath][0]
        return rendering

    @err_catcher(name=__name__)
    def getPathFromRenderingNode(self, node: Any) -> str:
        """Get the output path for a rendering node.
        
        Args:
            node: The Write node
            
        Returns:
            Output path or empty string if not rendering
        """
        nodePath = node.fullName()
        if nodePath in self.isRendering:
            return self.isRendering[nodePath][1]
        else:
            return ""

    @err_catcher(name=__name__)
    def finishedRendering(self, node: Any) -> None:
        """Mark a node as finished rendering.
        
        Args:
            node: The Write node that finished rendering
        """
        nodePath = node.fullName()
        if nodePath in self.isRendering:
            del self.isRendering[nodePath]

    @err_catcher(name=__name__)
    def getAppVersion(self, origin: Any) -> str:
        """Get Nuke version string.
        
        Args:
            origin: The calling instance
            
        Returns:
            Nuke version string (e.g. "15.0v4")
        """
        return nuke.NUKE_VERSION_STRING

    @err_catcher(name=__name__)
    def onProjectBrowserStartup(self, origin: Any) -> None:
        """Handle Project Browser startup event.
        
        Disables State Manager action in Nuke.
        
        Args:
            origin: The Project Browser instance
        """
        origin.actionStateManager.setEnabled(False)

    @err_catcher(name=__name__)
    def onPreMediaPlayerDragged(self, origin: Any, urlList: List[str]) -> None:
        """Handle pre-drag event for media player.
        
        Limits to first URL only.
        
        Args:
            origin: The media player instance
            urlList: List of URLs being dragged (modified in-place)
        """
        urlList[:] = [urlList[0]]

    @err_catcher(name=__name__)
    def newScene(self, force: bool = False) -> bool:
        """Create a new empty Nuke script.
        
        Args:
            force: Force new scene without saving
            
        Returns:
            True if successful
        """
        nuke.scriptClear()
        return True

    @err_catcher(name=__name__)
    def openScene(self, origin: Any, filepath: str, force: bool = False) -> bool:
        """Open a Nuke script file.
        
        Args:
            origin: The calling instance
            filepath: Path to the .nk file
            force: Force open without saving current script
            
        Returns:
            True if successful, False otherwise
        """
        if os.path.splitext(filepath)[1] not in self.sceneFormats:
            return False

        try:
            cleared = nuke.scriptSaveAndClear()
        except Exception as e:
            if "cannot clear script whilst executing" in str(e):
                self.core.popup(e)

            cleared = False

        if cleared:
            try:
                nuke.scriptOpen(filepath)
            except:
                pass

        return True

    @err_catcher(name=__name__)
    def importImages(self, filepath: Optional[str] = None, mediaBrowser: Optional[Any] = None, parent: Optional[Any] = None) -> None:
        """Import images into Nuke.
        
        Provides options to import current AOV, all AOVs, or layout all AOVs.
        
        Args:
            filepath: File path to import
            mediaBrowser: Media browser instance
            parent: Parent widget for dialogs
        """
        if mediaBrowser:
            if mediaBrowser.origin.getCurrentAOV() and mediaBrowser.origin.w_preview.cb_layer.count() > 1:
                fString = "Please select an import option:"
                buttons = ["Current AOV", "All AOVs", "Layout all AOVs"]
                parent = parent or mediaBrowser.origin.projectBrowser
                result = self.core.popupQuestion(fString, buttons=buttons, icon=QMessageBox.NoIcon, parent=parent)
            else:
                result = "Current AOV"

            if result == "Current AOV":
                self.nukeImportSource(mediaBrowser)
            elif result == "All AOVs":
                self.nukeImportPasses(mediaBrowser)
            elif result == "Layout all AOVs":
                self.nukeLayout(mediaBrowser)
            else:
                return

    @err_catcher(name=__name__)
    def importMedia(self, filepath: str, start: Optional[int] = None, end: Optional[int] = None) -> Any:
        """Import media file(s) as a Read node.
        
        Args:
            filepath: Path to media file or sequence
            start: Start frame for sequence
            end: End frame for sequence
            
        Returns:
            The created Read node
        """
        if "#"*self.core.framePadding not in filepath:
            filepath = self.core.media.getSequenceFromFilename(filepath)

        if start is None:
            if "#"*self.core.framePadding in filepath:
                files = self.core.media.getFilesFromSequence(filepath)
                s, e = self.core.media.getFrameRangeFromSequence(files)
                if s and e and s != "?" and e != "?":
                    start = s
                    end = e

        if start is not None:
            filepath += " %s-%s" % (start, end)

        if self.core.getConfig("nuke", "useRelativePaths", dft=False, config="user"):
            filepath = self.makePathRelative(filepath)

        read_node = nuke.createNode("Read", inpanel=False)
        read_node["file"].fromUserText(filepath)
        return read_node

    @err_catcher(name=__name__)
    def nukeImportSource(self, origin: Any) -> None:
        """Import source media product as Read nodes.
        
        Args:
            origin: The media browser instance
        """
        sourceData = origin.compGetImportSource()

        for i in sourceData:
            filePath = i[0]
            firstFrame = i[1]
            lastFrame = i[2]
            if self.core.getConfig("nuke", "useRelativePaths", dft=False, config="user"):
                filePath = self.makePathRelative(filePath)

            node = nuke.createNode(
                "Read",
                "file \"%s\"" % filePath,
                False,
            )
            if firstFrame is not None:
                node.knob("first").setValue(firstFrame)
            if lastFrame is not None:
                node.knob("last").setValue(lastFrame)

    @err_catcher(name=__name__)
    def nukeImportPasses(self, origin: Any) -> None:
        """Import all passes/AOVs from media product as Read nodes.
        
        Args:
            origin: The media browser instance
        """
        sourceData = origin.compGetImportPasses()

        for i in sourceData:
            filePath = i[0]
            firstFrame = i[1]
            lastFrame = i[2]
            if self.core.getConfig("nuke", "useRelativePaths", dft=False, config="user"):
                filePath = self.makePathRelative(filePath)

            node = nuke.createNode(
                "Read",
                "file \"%s\"" % filePath,
                False,
            )
            if firstFrame is not None:
                node.knob("first").setValue(firstFrame)
            if lastFrame is not None:
                node.knob("last").setValue(lastFrame)

    @err_catcher(name=__name__)
    def nukeLayout(self, origin: Any) -> None:
        """Layout all AOVs/passes in organized node tree with compositing setup.
        
        Creates Read nodes for all passes and sets up merge operations, shuffle
        nodes, and beauty pass output.
        
        Args:
            origin: The media browser instance
        """
        if nuke.env["nc"]:
            msg = "This feature is disabled because of the scripting limitations in Nuke non-commercial."
            self.core.popup(msg)
            return

        allExistingNodes = nuke.allNodes()
        try:
            allBBx = max([node.xpos() for node in allExistingNodes])
        except:
            allBBx = 0

        self.nukeYPos = 0
        xOffset = 200
        nukeXPos = allBBx + xOffset
        nukeSetupWidth = 950
        nukeSetupHeight = 400
        nukeYDistance = 700
        nukeBeautyYDistance = 500
        nukeBackDropFontSize = 100
        self.nukeIdxNode = None
        passFolder = os.path.dirname(os.path.dirname(origin.seq[0])).replace("\\", "/")

        if not os.path.exists(passFolder):
            return

        beautyTriggers = ["beauty", "rgb", "rgba"]
        componentsTriggers = [
            "ls",
            "select",
            "gi",
            "spec",
            "refr",
            "refl",
            "light",
            "lighting",
            "highlight",
            "diff",
            "diffuse",
            "emission",
            "sss",
            "vol",
        ]
        masksTriggers = ["mm", "mask", "puzzleMatte", "matte", "puzzle"]

        beautyPass = []
        componentPasses = []
        maskPasses = []
        utilityPasses = []

        self.maskNodes = []
        self.utilityNodes = []

        passes = [
            x
            for x in os.listdir(passFolder)
            if x[-5:] not in ["(mp4)", "(jpg)", "(png)"]
            and os.path.isdir(os.path.join(passFolder, x))
            and len(os.listdir(os.path.join(passFolder, x))) > 0
        ]

        passesBeauty = []
        passesComponents = []
        passesMasks = []
        passesUtilities = []

        for curPass in passes:
            assigned = False

            for trigger in beautyTriggers:
                if trigger in curPass.lower():
                    passesBeauty.append(curPass)
                    assigned = True
                    break

            if assigned:
                continue

            for trigger in componentsTriggers:
                if trigger in curPass.lower():
                    passesComponents.append(curPass)
                    assigned = True
                    break

            if assigned:
                continue

            for trigger in masksTriggers:
                if trigger in curPass.lower():
                    passesMasks.append(curPass)
                    assigned = True
                    break

            if assigned:
                continue

            passesUtilities.append(curPass)

        passes = passesBeauty + passesComponents + passesMasks + passesUtilities
        maskNum = 0
        utilsNum = 0

        for curPass in passes:
            curPassPath = os.path.join(passFolder, curPass)
            curPassName = os.listdir(curPassPath)[0].split(".")[0]

            if len(os.listdir(curPassPath)) > 1:
                if (
                    origin.pstart is None
                    or origin.pend is None
                    or origin.pstart == "?"
                    or origin.pend == "?"
                ):
                    self.core.popup(origin.pstart)
                    return

                firstFrame = origin.pstart
                lastFrame = origin.pend

                increment = "####"
                curPassFormat = os.listdir(curPassPath)[0].split(".")[-1]

                filePath = os.path.join(
                    passFolder,
                    curPass,
                    ".".join([curPassName, increment, curPassFormat]),
                ).replace("\\", "/")
            else:
                filePath = os.path.join(
                    curPassPath, os.listdir(curPassPath)[0]
                ).replace("\\", "/")
                firstFrame = 0
                lastFrame = 0

            # createPasses
            # beauty
            if curPass in passesBeauty:
                self.createBeautyPass(
                    origin,
                    filePath,
                    firstFrame,
                    lastFrame,
                    curPass,
                    nukeXPos,
                    nukeSetupWidth,
                    nukeBeautyYDistance,
                    nukeBackDropFontSize,
                )

            # components
            elif curPass in passesComponents:
                self.createComponentPass(
                    origin,
                    filePath,
                    firstFrame,
                    lastFrame,
                    curPass,
                    nukeXPos,
                    nukeSetupWidth,
                    nukeSetupHeight,
                    nukeBackDropFontSize,
                    nukeYDistance,
                )

            # masks
            elif curPass in passesMasks:
                maskNum += 1
                self.createMaskPass(
                    origin,
                    filePath,
                    firstFrame,
                    lastFrame,
                    nukeXPos,
                    nukeSetupWidth,
                    maskNum,
                )

            # utility
            elif curPass in passesUtilities:
                utilsNum += 1
                self.createUtilityPass(
                    origin,
                    filePath,
                    firstFrame,
                    lastFrame,
                    nukeXPos,
                    nukeSetupWidth,
                    utilsNum,
                )

        # maskbackdrop
        if len(self.maskNodes) > 0:
            bdX = min([node.xpos() for node in self.maskNodes])
            bdY = min([node.ypos() for node in self.maskNodes])
            bdW = (
                max([node.xpos() + node.screenWidth() for node in self.maskNodes]) - bdX
            )
            bdH = (
                max([node.ypos() + node.screenHeight() for node in self.maskNodes])
                - bdY
            )

            # backdrop boundry offsets
            left, top, right, bottom = (-160, -135, 160, 80)

            # boundry offsets
            bdX += left
            bdY += top
            bdW += right - left
            bdH += bottom - top

            # createbackdrop
            maskBackdropColor = int("%02x%02x%02x%02x" % (255, 125, 125, 1), 16)
            backDrop = nuke.nodes.BackdropNode(
                xpos=bdX,
                bdwidth=bdW,
                ypos=bdY,
                bdheight=bdH,
                tile_color=maskBackdropColor,
                note_font_size=nukeBackDropFontSize,
                label="<center><b>" + "Masks" + "</b><c/enter>",
            )

        # utilitybackdrop
        if len(self.utilityNodes) > 0:
            bdX = min([node.xpos() for node in self.utilityNodes])
            bdY = min([node.ypos() for node in self.utilityNodes])
            bdW = (
                max([node.xpos() + node.screenWidth() for node in self.utilityNodes])
                - bdX
            )
            bdH = (
                max([node.ypos() + node.screenHeight() for node in self.utilityNodes])
                - bdY
            )

            # backdrop boundry offsets
            left, top, right, bottom = (-160, -135, 160, 80)

            # boundry offsets
            bdX += left
            bdY += top
            bdW += right - left
            bdH += bottom - top

            # createbackdrop
            maskBackdropColor = int("%02x%02x%02x%02x" % (125, 255, 125, 1), 16)
            backDrop = nuke.nodes.BackdropNode(
                xpos=bdX,
                bdwidth=bdW,
                ypos=bdY,
                bdheight=bdH,
                tile_color=maskBackdropColor,
                note_font_size=nukeBackDropFontSize,
                label="<center><b>" + "Utilities" + "</b><c/enter>",
            )

    @err_catcher(name=__name__)
    def createBeautyPass(
        self,
        origin: Any,
        filePath: str,
        firstFrame: int,
        lastFrame: int,
        curPass: str,
        nukeXPos: int,
        nukeSetupWidth: int,
        nukeBeautyYDistance: int,
        nukeBackDropFontSize: int,
    ) -> None:
        """Create beauty/RGB pass Read node in layout.
        
        Args:
            origin: The media browser instance
            filePath: Path to beauty pass files
            firstFrame: First frame
            lastFrame: Last frame
            curPass: Pass name
            nukeXPos: X position for node
            nukeSetupWidth: Width of setup area
            nukeBeautyYDistance: Y distance for beauty pass
            nukeBackDropFontSize: Backdrop font size
        """
        curReadNode = nuke.createNode(
            "Read",
            'file "%s" first %s last %s origfirst %s origlast %s'
            % (filePath, firstFrame, lastFrame, firstFrame, lastFrame),
            False,
        )

        nodeArray = [curReadNode]

        # backdropcolor
        r = (float(random.randint(30 + int((self.nukeYPos / 3) % 3), 80))) / 100
        g = (float(random.randint(20 + int((self.nukeYPos / 3) % 3), 80))) / 100
        b = (float(random.randint(15 + int((self.nukeYPos / 3) % 3), 80))) / 100
        hexColour = int("%02x%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255), 1), 16)

        # positions
        curReadNodeWidth = int(curReadNode.screenWidth() * 0.5 - 6)
        curReadNodeHeight = int(curReadNode.screenHeight() * 0.5 - 3)

        curReadNode.setYpos(self.nukeYPos + curReadNodeHeight)
        curReadNode.setXpos(nukeXPos + nukeSetupWidth)

        # backdrop boundries
        bdX = min([node.xpos() for node in nodeArray])
        bdY = min([node.ypos() for node in nodeArray])
        bdW = max([node.xpos() + node.screenWidth() for node in nodeArray]) - bdX
        bdH = max([node.ypos() + node.screenHeight() for node in nodeArray]) - bdY

        # backdrop boundry offsets
        left, top, right, bottom = (-160, -135, 160, 80)

        # boundry offsets
        bdX += left
        bdY += top
        bdW += right - left
        bdH += bottom - top

        # createbackdrop
        backDrop = nuke.nodes.BackdropNode(
            xpos=bdX,
            bdwidth=bdW,
            ypos=bdY,
            bdheight=bdH,
            tile_color=hexColour,
            note_font_size=nukeBackDropFontSize,
            label="<center><b>" + curPass + "</b><c/enter>",
        )

        # increment position
        self.nukeYPos += nukeBeautyYDistance

        # current nukeIdxNode
        self.nukeIdxNode = curReadNode

    @err_catcher(name=__name__)
    def createComponentPass(
        self,
        origin: Any,
        filePath: str,
        firstFrame: int,
        lastFrame: int,
        curPass: str,
        nukeXPos: int,
        nukeSetupWidth: int,
        nukeSetupHeight: int,
        nukeBackDropFontSize: int,
        nukeYDistance: int,
    ) -> None:
        """Create component pass Read node in layout with merge operations.
        
        Args:
            origin: The media browser instance
            filePath: Path to component pass files
            firstFrame: First frame
            lastFrame: Last frame
            curPass: Pass name
            nukeXPos: X position for node
            nukeSetupWidth: Width of setup area
            nukeSetupHeight: Height of setup area
            nukeBackDropFontSize: Backdrop font size
            nukeYDistance: Y distance between passes
        """

        curReadNode = nuke.createNode(
            "Read",
            'file "%s" first %s last %s origfirst %s origlast %s'
            % (filePath, firstFrame, lastFrame, firstFrame, lastFrame),
            False,
        )
        mergeNode1 = nuke.createNode("Merge", "operation difference", False)
        dotNode = nuke.createNode("Dot", "", False)
        dotNodeCorner = nuke.createNode("Dot", "", False)
        mergeNode2 = nuke.createNode("Merge", "operation plus", False)

        nodeArray = [curReadNode, dotNode, mergeNode1, mergeNode2, dotNodeCorner]

        # positions
        curReadNode.setYpos(self.nukeYPos)
        curReadNode.setXpos(nukeXPos)

        curReadNodeWidth = int(curReadNode.screenWidth() * 0.5 - 6)
        curReadNodeHeight = int(curReadNode.screenHeight() * 0.5 - 3)

        mergeNode1.setYpos(self.nukeYPos + curReadNodeHeight)
        mergeNode1.setXpos(nukeXPos + nukeSetupWidth)

        dotNode.setYpos(
            self.nukeYPos + curReadNodeHeight + int(curReadNode.screenWidth() * 0.7)
        )
        dotNode.setXpos(nukeXPos + curReadNodeWidth)

        dotNodeCorner.setYpos(self.nukeYPos + nukeSetupHeight)
        dotNodeCorner.setXpos(nukeXPos + curReadNodeWidth)

        mergeNode2.setYpos(self.nukeYPos + nukeSetupHeight - 4)
        mergeNode2.setXpos(nukeXPos + nukeSetupWidth)

        # #inputs
        mergeNode1.setInput(1, curReadNode)
        dotNode.setInput(0, curReadNode)
        dotNodeCorner.setInput(0, dotNode)
        mergeNode2.setInput(1, dotNodeCorner)
        mergeNode2.setInput(0, mergeNode1)

        if self.nukeIdxNode != None:
            mergeNode1.setInput(0, self.nukeIdxNode)

        # backdrop boundry offsets
        left, top, right, bottom = (-10, -125, 100, 50)

        # backdropcolor
        r = (float(random.randint(30 + int((self.nukeYPos / 3) % 3), 80))) / 100
        g = (float(random.randint(20 + int((self.nukeYPos / 3) % 3), 80))) / 100
        b = (float(random.randint(15 + int((self.nukeYPos / 3) % 3), 80))) / 100
        hexColour = int("%02x%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255), 1), 16)

        # backdrop boundries
        bdX = min([node.xpos() for node in nodeArray])
        bdY = min([node.ypos() for node in nodeArray])
        bdW = max([node.xpos() + node.screenWidth() for node in nodeArray]) - bdX
        bdH = max([node.ypos() + node.screenHeight() for node in nodeArray]) - bdY

        # boundry offsets
        bdX += left
        bdY += top
        bdW += right - left
        bdH += bottom - top

        # createbackdrop
        backDrop = nuke.nodes.BackdropNode(
            xpos=bdX,
            bdwidth=bdW,
            ypos=bdY,
            bdheight=bdH,
            tile_color=hexColour,
            note_font_size=nukeBackDropFontSize,
            label="<b>" + curPass + "</b>",
        )

        # increment position
        self.nukeYPos += nukeYDistance

        # current nukeIdxNode
        self.nukeIdxNode = mergeNode2

    @err_catcher(name=__name__)
    def createMaskPass(
        self, origin: Any, filePath: str, firstFrame: int, lastFrame: int, nukeXPos: int, nukeSetupWidth: int, idx: int
    ) -> None:
        """Create mask/matte pass Read node with RGB shuffle nodes.
        
        Args:
            origin: The media browser instance
            filePath: Path to mask pass files
            firstFrame: First frame
            lastFrame: Last frame
            nukeXPos: X position for node
            nukeSetupWidth: Width of setup area
            idx: Index for positioning multiple masks
        """
        curReadNode = nuke.createNode(
            "Read",
            'file "%s" first %s last %s origfirst %s origlast %s'
            % (filePath, firstFrame, lastFrame, firstFrame, lastFrame),
            False,
        )
        curReadNode.setYpos(0)
        curReadNode.setXpos(nukeXPos + nukeSetupWidth + 500 + idx * 350)

        val = 0.5
        r = int("%02x%02x%02x%02x" % (int(val * 255), 0, 0, 1), 16)
        g = int("%02x%02x%02x%02x" % (0, int(val * 255), 0, 1), 16)
        b = int("%02x%02x%02x%02x" % (0, 0, int(val * 255), 1), 16)

        created = False
        if "cryptomatte" in os.path.basename(filePath):
            try:
                cmatte = nuke.createNode("Cryptomatte", inpanel=False)
            except:
                pass
            else:
                created = True
                cmatte.setInput(0, curReadNode)
                self.maskNodes.append(curReadNode)
                self.maskNodes.append(cmatte)

        if not created:
            redShuffle = nuke.createNode(
                "Shuffle", "red red blue red green red alpha red", inpanel=False
            )
            greenShuffle = nuke.createNode(
                "Shuffle", "red green blue green green green alpha green", inpanel=False
            )
            blueShuffle = nuke.createNode(
                "Shuffle", "red blue blue blue green blue alpha blue", inpanel=False
            )

            redShuffle["tile_color"].setValue(r)
            greenShuffle["tile_color"].setValue(g)
            blueShuffle["tile_color"].setValue(b)

            redShuffle.setInput(0, curReadNode)
            greenShuffle.setInput(0, curReadNode)
            blueShuffle.setInput(0, curReadNode)

            redShuffle.setXpos(redShuffle.xpos() - 110)
            # 	greenShuffle.setXpos(greenShuffle.xpos()-110)
            blueShuffle.setXpos(blueShuffle.xpos() + 110)

            self.maskNodes.append(curReadNode)
            self.maskNodes.append(redShuffle)
            self.maskNodes.append(greenShuffle)
            self.maskNodes.append(blueShuffle)

    @err_catcher(name=__name__)
    def createUtilityPass(
        self, origin: Any, filePath: str, firstFrame: int, lastFrame: int, nukeXPos: int, nukeSetupWidth: int, idx: int
    ) -> None:
        """Create utility pass Read node.
        
        Args:
            origin: The media browser instance
            filePath: Path to utility pass files
            firstFrame: First frame
            lastFrame: Last frame
            nukeXPos: X position for node
            nukeSetupWidth: Width of setup area
            idx: Index for positioning multiple utility passes
        """
        curReadNode = nuke.createNode(
            "Read",
            'file "%s" first %s last %s origfirst %s origlast %s'
            % (filePath, firstFrame, lastFrame, firstFrame, lastFrame),
            False,
        )
        curReadNode.setYpos(0)
        curReadNode.setXpos(nukeXPos + nukeSetupWidth + 500 + idx * 100)
        try:
            curReadNode.setXpos(
                curReadNode.xpos()
                + self.maskNodes[-1].xpos()
                - nukeXPos
                - nukeSetupWidth
            )
        except:
            pass

        self.utilityNodes.append(curReadNode)

    @err_catcher(name=__name__)
    def postSaveScene(self, origin: Any, filepath: str, versionUp: bool, comment: str, isPublish: bool, details: Dict[str, Any]) -> None:
        """Post-save callback to refresh Write nodes after scene save.
        
        Args:
            origin: PrismCore instance
            filepath: The filepath of the scene that was saved
            versionUp: True if this save increments the version
            comment: Comment for the scenefile
            isPublish: True if this was a publish save
            details: Additional save details
        """
        self.refreshWriteNodes()

    @err_catcher(name=__name__)
    def postBuildScene(self, **kwargs: Any) -> None:
        """Post-build callback after scene build completes.
        
        Refreshes OCIO and optionally loads media based on project settings.
        
        Args:
            **kwargs: Keyword arguments with entity, department, task details
        """
        self.core.appPlugin.refreshOcio()

    @err_catcher(name=__name__)
    def buildSceneLoadMedia(self, step: Dict[str, Any], context: Dict[str, Any]) -> None:
        """
        Scene building step function to load media for an entity.
        
        Args:
            step: Step settings dict.
            context: Current scene building context dict with entity, department, task info.
        """
        idfs = self.core.mediaProducts.getIdentifiersFromEntity(context)
        matchingIdfs = []

        import fnmatch
        stepsNames = [name.strip().lower() for name in step["settings"][0]["value"].split(",")]
        for idf in idfs:
            group = (self.core.mediaProducts.getGroupFromIdentifier(idf) or "").lower()
            idfName = idf["identifier"].lower()
            valid = False
            for stepsName in stepsNames:
                if fnmatch.fnmatch(group, stepsName) or fnmatch.fnmatch(idfName, stepsName):
                    valid = True
                    break

            if valid:
                matchingIdfs.append(idfName)

        self.loadMediaForEntity(context, matchingIdfs)

    @err_catcher(name=__name__)
    def buildSceneMultishotSetup(self, step: Dict[str, Any], context: Dict[str, Any]) -> None:
        """
        Scene building step function to set up multishot for a sequence.
        
        Args:
            step: Step settings dict.
            context: Current scene building context dict with entity, department, task info.
        """
        entity = self.core.getCurrentScenefileData()
        if entity.get("type") != "shot":
            return

        shots = self.core.entities.getShots(sequence=entity.get("sequence"))
        self.loadShotsIntoNuke(shots)

    @err_catcher(name=__name__)
    def loadMediaForEntity(self, entity: Dict[str, Any], identifiers: list[str]) -> None:
        """Load media files for an entity based on specified identifiers.
        
        Args:
            entity: The entity dictionary containing media information.
            identifiers: List of identifier strings to filter media.
        """
        idfs = self.core.mediaProducts.getIdentifiersFromEntity(entity)
        mediaPaths = []
        identifiers = [idf.lower() for idf in identifiers]

        import fnmatch
        for idf in idfs:
            idfName = idf["identifier"].lower()
            if idfName not in identifiers:
                continue

            version = self.core.mediaProducts.getVersion(entity, idf["identifier"], mediaType=idf.get("mediaType"))
            if not version:
                continue

            platePath = self.core.mediaProducts.getFileFromVersion(version, findExisting=True)
            if platePath:
                mediaPaths.append(platePath)

        readNodes = []
        for idx, mediaPath in enumerate(mediaPaths):
            readNode = self.core.appPlugin.importMedia(mediaPath)
            readNode.setXpos(idx * 200)
            readNode.setYpos(0)
            readNodes.append(readNode)

        useWritePrism = self.core.getConfig("nuke", "useWritePrism", dft=False, config="user")
        if useWritePrism:
            writeType = "WritePrism"
        else:
            writeType = "Write"

        writeNode = nuke.createNode(writeType)
        if readNodes:
            writeNode.setInput(0, readNodes[0])

        writeNode.setXpos(0)
        writeNode.setYpos(300)
        viewers = [node for node in nuke.allNodes() if node.Class() == "Viewer"]
        if not viewers:
            viewer = nuke.createNode("Viewer")
            viewers = [viewer]

        viewers[0].setInput(0, writeNode)
        viewers[0].setYpos(400)

    @err_catcher(name=__name__)
    def refreshWriteNodes(self) -> None:
        """Refresh all Write and WritePrism nodes to update output paths."""
        for node in nuke.allNodes():
            nodeClass = node.Class()
            if nodeClass == "WritePrism" and node.knob("refresh"):
                node.knob("refresh").execute()
            elif nodeClass == "Write":
                if node.knob("tab_prism") and node.knob("refresh"):
                    node.knob("refresh").execute()

    @err_catcher(name=__name__)
    def onUserNodeCreated(self, node: nuke.Node=None) -> None:
        """Callback when user creates a node.
        
        Adds Prism UI elements to Write and Read nodes automatically.

        Args:
            node: The node that was created (optional, will attempt to get from context if not provided)
        """
        if not node:
            try:
                node = nuke.thisNode()
                bool(node)
            except Exception:
                # Node not properly attached in callback context
                return

        if not node:
            return

        try:
            nodeClass = node.Class()
        except Exception:
            # Unable to get node class
            return

        try:
            group = nuke.thisGroup()
        except Exception:
            group = None

        addWriteKnobs = os.environ.get("PRISM_NUKE_WRITE_ADD_KNOBS", "1") == "1"
        if nodeClass == "Write" and (not group or group.Class() != "WritePrism") and addWriteKnobs:
            if not node.knob("tab_prism"):
                self.addUiToWriteNode(node)

            self.updateNodeUI("write", node)
            self.getOutputPath(node)

            cmd = "try:\n\tpcore.getPlugin(\"Nuke\").updateNodeUI(\"write\", nuke.toNode(nuke.thisNode().fullName().rsplit(\".\", 1)[0]))\nexcept:\n\tpass"
            node.knob("knobChanged").setValue(cmd)
            idfKnob = node.knob("identifier")
            if idfKnob and not idfKnob.value():
                idf = self.core.getCurrentScenefileData().get("task")
                if idf:
                    idfKnob.setValue(idf)
                    self.getOutputPath(node)

        elif nodeClass == "Read" and os.getenv("PRISM_NUKE_READ_ADD_KNOBS", "1") == "1":
            if not node.knob("tab_prism"):
                self.addUiToReadNode(node)

            self.updateNodeUI("read", node)
            cmd = "try:\n\tpcore.getPlugin(\"Nuke\").updateNodeUI(\"read\", nuke.toNode(nuke.thisNode().fullName().rsplit(\".\", 1)[0]))\nexcept:\n\tpass"
            node.knob("knobChanged").setValue(cmd)

        elif nodeClass == "VariableSwitch" and os.getenv("PRISM_NUKE_VAR_SWITCH_ADD_KNOBS", "1") == "1":
            if not node.knob("tab_prism"):
                self.addUiToVariableSwitchNode(node)

            self.updateNodeUI("read", node)

        kwargs = {"origin": self, "node": node}
        self.core.callback("onNukeNodeCreated", **kwargs)

    # @err_catcher(name=__name__)
    # def onRootKnobChanged(self) -> None:
    #     """Callback when root node knob changes.
        
    #     Refreshes GSVs when multi-shot GSV knob is modified.
    #     """
    #     try:
    #         knob = nuke.thisKnob()
    #     except (ValueError, RuntimeError):
    #         return

    #     if not knob or knob.name() != "gsv":
    #         return

    #     self.refreshGSVs()

    @err_catcher(name=__name__)
    def onAfterUserSetGsvValue(self, gsv: str) -> None:
        """Callback after GSV value is set.
        
        Args:
            gsv: The GSV that was modified
        """
        if gsv == "root.prism.shot":
            self.refreshNukeShotMenu()
            self.refreshGSVs()

    @err_catcher(name=__name__)
    def addUiToWriteNode(self, node: Any) -> None:
        """Add Prism UI elements (knobs) to a Write node.
        
        Args:
            node: The Write node
        """
        knobs = ["identifier", "comment", "location", "fileName", "refresh", "startRender", "showPrevVersions", "submitJob", "prevFileName", "openDir", "farmSubmissionSettings"]
        for knob in knobs:
            k = node.knob(knob)
            if k:
                node.removeKnob(k)

        tab = node.knob("tab_prism")
        if not tab:
            tab = nuke.Tab_Knob('tab_prism', 'Prism')
            node.addKnob(tab)

        knobIdf = nuke.EvalString_Knob("identifier", "identifier")
        node.addKnob(knobIdf)
        knobComment = nuke.EvalString_Knob("comment", "comment (optional)")
        node.addKnob(knobComment)
        knobVersion = nuke.Int_Knob("renderversion", "Version")
        knobVersion.setValue(1)
        node.addKnob(knobVersion)
        knobVersion.setEnabled(False)
        knobAutoVersion = nuke.Boolean_Knob("autoversion", "auto")
        knobAutoVersion.setValue(True)
        node.addKnob(knobAutoVersion)
        knobPrevVersions = nuke.PyScript_Knob("showPrevVersions", "Show Previous Versions...", "pcore.appPlugin.showPrevVersions(nuke.thisNode())")
        node.addKnob(knobPrevVersions)
        knobLoc = nuke.Enumeration_Knob("location", "location", ["                              "])
        node.addKnob(knobLoc)
        knobDiv = nuke.Text_Knob("")
        node.addKnob(knobDiv)
        knobFilepath = nuke.EvalString_Knob("fileName", "filepath")
        knobFilepath.setValue("FileNotInPipeline")
        node.addKnob(knobFilepath)
        knobRefresh = nuke.PyScript_Knob("refresh", "Refresh", "pcore.appPlugin.getOutputPath(nuke.thisNode())")
        knobRefresh.setFlag(nuke.STARTLINE)
        node.addKnob(knobRefresh)
        knobDiv = nuke.Text_Knob("")
        node.addKnob(knobDiv)
        knobRender = nuke.PyScript_Knob("startRender", "Render", "pcore.appPlugin.startRender(nuke.thisNode())")
        node.addKnob(knobRender)
        knobSubmit = nuke.Boolean_Knob("submitJob", "Submit Job")
        node.addKnob(knobSubmit)
        knobPrev = nuke.Text_Knob("prevFileName", "previous filepath", "-")
        node.addKnob(knobPrev)
        knobOpen = nuke.PyScript_Knob("openDir", "Open In...", "pcore.appPlugin.openInClicked(nuke.thisNode())")
        knobOpen.setFlag(nuke.STARTLINE)
        node.addKnob(knobOpen)
        knobOpen = nuke.PyScript_Knob("createRead", "Create Read", "pcore.appPlugin.createRead(nuke.thisNode())")
        node.addKnob(knobOpen)
        knobFarmSettings = nuke.String_Knob("farmSubmissionSettings", "Farm Submission Settings")
        knobFarmSettings.setVisible(False)
        node.addKnob(knobFarmSettings)

        node.knob("create_directories").setValue(True)
        node.knob("file").setValue("[value fileName]")
        node.knob("file_type").setValue("exr")
        node.knob("beforeRender").setValue("try: pcore.appPlugin.getOutputPath(nuke.thisNode(), render=True)\nexcept: pass")
        node.knob("afterRender").setValue("try: pcore.appPlugin.finishedRendering(nuke.thisNode())\nexcept: pass")

    @err_catcher(name=__name__)
    def addUiToReadNode(self, node: Any) -> None:
        """Add Prism UI elements (knobs) to a Read node.
        
        Args:
            node: The Read node
        """
        knobs = ["identifier", "comment", "location", "fileName", "refresh", "startRender", "showPrevVersions", "submitJob", "prevFileName", "openDir"]
        for knob in knobs:
            k = node.knob(knob)
            if k:
                node.removeKnob(k)

        tab = node.knob("tab_prism")
        if not tab:
            tab = nuke.Tab_Knob('tab_prism', 'Prism')
            node.addKnob(tab)

        knobFilepath = nuke.Text_Knob("fileName", "File", "")
        node.addKnob(knobFilepath)
        knobBrowse = nuke.PyScript_Knob("browse", "Browse...", "pcore.appPlugin.readNode_onBrowseClicked(nuke.thisNode())")
        knobBrowse.setFlag(nuke.STARTLINE)
        node.addKnob(knobBrowse)
        knobExplorer = nuke.PyScript_Knob("openExplorer", "Open In Explorer...", "pcore.appPlugin.readNode_onOpenInClicked(nuke.thisNode())")
        node.addKnob(knobExplorer)
        self.ensureReadNodeMediaVersionExclusionKnob(node)

    @err_catcher(name=__name__)
    def ensureReadNodeMediaVersionExclusionKnob(self, node: Any) -> None:
        """Add the media version exclusion checkbox to Prism Read node UI."""
        if not node.knob("tab_prism"):
            return

        if node.knob("excludeFromMediaVersionUpdates"):
            return

        knobExclude = nuke.Boolean_Knob(
            "excludeFromMediaVersionUpdates",
            "Exclude from Manage Media Versions",
        )
        node.addKnob(knobExclude)

    @err_catcher(name=__name__)
    def isReadNodeExcludedFromMediaVersions(self, node: Any) -> bool:
        """Check whether a Read node should be ignored by Manage Media Versions."""
        knob = node.knob("excludeFromMediaVersionUpdates")
        if not knob:
            return False

        return bool(knob.value())

    @err_catcher(name=__name__)
    def addUiToVariableSwitchNode(self, node: Any) -> None:
        """Add Prism UI elements (knobs) to a VariableSwitch node.
        
        Args:
            node: The VariableSwitch node
        """
        knobs = ["addShot"]
        for knob in knobs:
            k = node.knob(knob)
            if k:
                node.removeKnob(k)

        tab = node.knob("tab_prism")
        if not tab:
            tab = nuke.Tab_Knob('tab_prism', 'Prism')
            node.addKnob(tab)

        knobAdd = nuke.PyScript_Knob("addShot", "Add Shot...", "pcore.appPlugin.variableSwitch_onAddShotClicked(nuke.thisNode())")
        knobAdd.setFlag(nuke.STARTLINE)
        node.addKnob(knobAdd)

    @err_catcher(name=__name__)
    def variableSwitch_onAddShotClicked(self, node: Any) -> None:
        """Handle Add Shot button click on VariableSwitch node.
        
        Opens media browser dialog to select media files.
        
        Args:
            node: The VariableSwitch node
        """
        if not getattr(self.core, "projectPath", None):
            self.core.popup("There is no active project in Prism.")
            return
        
        callback = lambda x, insert=False: self.addShotsToVariableSwitchSelected(node, x, insert=insert)
        dlg = ShotListDlg(self)
        dlg.entitiesAdded.connect(callback)
        dlg.entitiesInserted.connect(lambda x: callback(x, insert=True))
        dlg.exec_()

    @err_catcher(name=__name__)
    def addShotsToVariableSwitchSelected(self, node, data, insert=False):
        DOT_SPACING = 200
        DOT_END_Y_OFFSET = 50   # pixels above the switch
        DOT_START_Y_OFFSET = 200  # pixels above the switch (higher than _end)

        with self.core.waitPopup(self.core, "Loading Shots. Please wait..."):
            gsv_knob = nuke.root()["gsv"]
            if gsv_knob.getGsvValue("prism.shot") is None:
                gsv_knob.setGsvValue("prism.shot", "")

            if gsv_knob.getDataType("prism.shot") != nuke.gsv.DataType.List:
                gsv_knob.setDataType("prism.shot", nuke.gsv.DataType.List)

            node.knob("variable").setValue("prism.shot")
            shots = [shot for shot in data if shot.get("type") == "shot"]
            # input 0 is reserved as the free default; shots start at index 1
            existing_input_count = 1
            while node.input(existing_input_count) is not None:
                existing_input_count += 1

            switch_x = node.xpos()
            switch_y = node.ypos()
            dot_end_y = switch_y - DOT_END_Y_OFFSET
            dot_start_y = switch_y - DOT_START_Y_OFFSET

            # Whatever is currently wired into switch input 0 becomes the source
            # for all new _start dots
            input0_node = node.input(0)

            cur_shots = list(self.getShotsFromScene())

            for i, shot in enumerate(shots):
                shot_name = self.core.entities.getShotName(shot)
                input_idx = existing_input_count + i

                dot_x = switch_x + 200 + (input_idx - 1) * DOT_SPACING

                dot_start = nuke.nodes.Dot(
                    xpos=dot_x,
                    ypos=dot_start_y,
                    label=shot_name,
                    name="shot_%s_start" % shot_name,
                )
                if input0_node is not None:
                    dot_start.connectInput(0, input0_node)

                dot_end = nuke.nodes.Dot(
                    xpos=dot_x,
                    ypos=dot_end_y,
                    label=shot_name,
                    name="shot_%s_end" % shot_name,
                )
                dot_end.connectInput(0, dot_start)

                node.connectInput(input_idx, dot_end)
                iknob = node.knob("i%d" % input_idx)
                if iknob is not None:
                    iknob.setValue(shot_name)

                if shot_name not in cur_shots:
                    cur_shots.append(shot_name)

            gsv_knob.setListOptions("prism.shot", sorted(cur_shots))



    # @err_catcher(name=__name__)
    # def addShotToVariableSwitch(self, node, entity, insert=False):
    #     shotName = self.core.entities.getShotName(entity)
    #     shotInName = "shot_switch_start"
    #     shotIn = node.parent().item(shotInName)
    #     if not shotIn:
    #         self.core.popup("Can't find node \"%s\"." % shotInName)
    #         return

    #     curShotNames = self.getShotsFromVariableSwitch(node)
    #     if shotName in curShotNames:
    #         self.core.popup("Shot %s exists already in %s" % (shotName, node.path()))
    #         return

    #     if insert:
    #         shotIdx = 0
    #         for idx, curShotName in enumerate(curShotNames):
    #             if shotName > curShotName:
    #                 shotIdx = idx + 1

    #         for idx, curShotName in enumerate(curShotNames):
    #             if idx >= shotIdx:
    #                 self.houdini_moveShot(node, idx, x=7)

    #     else:
    #         shotIdx = len(curShotNames)

    #     NODE_HALF_W   = 34
    #     COLUMN_WIDTH  = 820
    #     input_idx    = existing_input_count + i
    #     col_center_x = base_col_x + shotIdx * COLUMN_WIDTH

    #     shotInNode = node.parent().createNode("null", "shot_in_%s_%s" % (depName, shotName))
    #     shotInNode.setInput(0, shotIn)
    #     shotInNode.setPosition(hou.Vector2(node.position().x() + (shotIdx * 7), shotIn.position().y() - 2))
    #     shotOutNode = node.parent().createNode("null", "shot_out_%s_%s" % (depName, shotName))

    #     shotOutNode.setPosition(hou.Vector2(node.position().x() + (shotIdx * 7), node.position().y() + 2))
    #     shotIpointNode = node.parent().createNode("insertionpoint", "insertion_point_%s_%s" % (depName, shotName))
    #     shotIpointNode.parm("descriptor").set("$OS")
    #     shotOutNode.setInput(0, shotIpointNode)

    #     shotIpointNode.setInput(0, shotInNode)
    #     shotIpointNode.setPosition(hou.Vector2(shotOutNode.position().x(), shotOutNode.position().y() + 1))

    #     vgroup = nuke.nodes.VariableGroup(
    #         xpos=col_center_x - NODE_HALF_W,
    #         ypos=Y_VGROUP,
    #     )
    #     vgroup.begin()
    #     _grp_in  = nuke.nodes.Input(xpos=0, ypos=0)
    #     _grp_out = nuke.nodes.Output(xpos=0, ypos=200)
    #     _grp_out.connectInput(0, _grp_in)
    #     vgroup.end()
    #     vgroup.connectInput(0, shotInNode)

    #     if not curShotNames and node.inputs():
    #         node.setInput(0, None)

    #     node.connectInput(shotIdx, shotOutNode)
    #     iknob = node.knob("i%d" % shotIdx)
    #     if iknob is not None:
    #         iknob.setValue(shotName)

    @err_catcher(name=__name__)
    def readGizmoCreated(self) -> None:
        """Callback when ReadPrism gizmo is created."""
        pass

    @err_catcher(name=__name__)
    def writeGizmoCreated(self) -> None:
        """Callback when WritePrism gizmo is created.
        
        Initializes output path, knobs, and default identifier.
        """
        group = nuke.thisGroup()
        self.getOutputPath(nuke.thisNode(), group)

        cmd = "try:\n\tpcore.getPlugin(\"Nuke\").updateNodeUI(\"writePrism\", nuke.toNode(nuke.thisNode().fullName().rsplit(\".\", 1)[0]))\nexcept:\n\tpass"
        base = nuke.thisNode().node("WritePrismBase")
        if base:
            base.knob("knobChanged").setValue(cmd)

        idfKnob = nuke.thisNode().knob("identifier")
        if idfKnob and not idfKnob.value():
            idf = self.core.getCurrentScenefileData().get("task")
            if idf:
                idfKnob.setValue(idf)
                self.getOutputPath(nuke.thisNode(), group)

        val = group.knob("prevFileName").value()
        if not val or val == "-":
            knobe = group.knob("prevFileNameEdit")
            if knobe:
                vale = knobe.value()
                if vale and vale != val:
                    group.knob("prevFileName").setValue(vale.replace("\\", "/"))

        kwargs = {"origin": self, "node": nuke.thisNode()}
        self.core.callback("onWriteGizmoCreated", **kwargs)

    @err_catcher(name=__name__)
    def updateNodeUI(self, nodeType: str, node: Any) -> None:
        """Update node UI elements based on node type.
        
        Updates location dropdowns and other dynamic UI elements.
        
        Args:
            nodeType: Type of node ("writePrism", "write", "read")
            node: The node to update
        """
        if not nuke.env.get("gui"):
            return

        if nodeType in ["writePrism", "write"]:
            locations = self.core.paths.getRenderProductBasePaths()
            locNames = list(locations.keys())
            try:
                node.knob("location").setValues(locNames)
            except:
                pass

            if nodeType == "WritePrismBase":
                base = node.node("WritePrismBase")
                if base:
                    knobs = base.knobs()
                    try:
                        node.knobs()["datatype"].setVisible(bool(knobs.get("datatype")))
                    except:
                        pass

                    try:
                        node.knobs()["compression"].setVisible(bool(knobs.get("compression")))
                    except:
                        pass

            knob = nuke.thisKnob()
            if knob and knob.name() in ["identifier", "location", "renderversion", "autoversion"]:
                self.getOutputPath(node)

            if knob and knob.name() == "autoversion":
                nuke.thisNode().knob("renderversion").setEnabled(not knob.value())

        elif nodeType in ["read"]:
            self.ensureReadNodeMediaVersionExclusionKnob(node)
            try:
                if node.knob("file"):
                    node.knob("fileName").setValue(node.knob("file").value())
            except:
                pass

    @err_catcher(name=__name__)
    def createRead(self, node: Any, group: Optional[Any] = None) -> None:
        """Create Read node from Write node output.
        
        Args:
            node: The Write node
            group: The node group
        """
        if group:
            group.end()

        if not group:
            group = node

        filepath = group.knob("prevFileName").value()
        if not os.path.exists(os.path.dirname(filepath)):
            filepath = group.knob("fileName").value()
            if not os.path.exists(os.path.dirname(filepath)):
                context = self.core.paths.getRenderProductData(filepath, mediaType="2drenders")
                intVersion = self.core.products.getIntVersionFromVersionName(context.get("version") or "")
                if intVersion is not None:
                    context["version"] = self.core.versionFormat % (intVersion - 1)
                    filepath = self.core.mediaProducts.generateMediaProductPath(
                        entity=context,
                        task=context["identifier"],
                        version=context["version"],
                        extension=context.get("extension", ""),
                        mediaType="2drenders",
                        comment=context.get("comment", ""),
                        location=context.get("location", "global"),
                        framePadding="#",
                    )

                filepath = self.expandEnvVarsInFilepath(filepath)
                if not os.path.exists(os.path.dirname(filepath)):
                    self.core.popup("Folder doesn't exist: %s" % os.path.dirname(filepath))
                    return

        seqs = nuke.getFileNameList(os.path.dirname(filepath))
        if not seqs:
            self.core.popup("No renderings exist in current filepath.")
            return

        if "#" not in os.path.basename(filepath):
            base, ext = os.path.splitext(filepath)
            filepath = base + "#" + ext

        pattern = os.path.basename(filepath).replace("#", ".*")
        useRel = self.core.getConfig("nuke", "useRelativePaths", dft=False, config="user")
        for seq in seqs:
            if re.match(pattern, seq):
                readNode = nuke.createNode('Read')
                filepath = os.path.join(os.path.dirname(filepath), seq)
                if useRel:
                    filepath = self.makePathRelative(filepath)

                readNode.knob('file').fromUserText(filepath)
                break
        else:
            self.core.popup("No media files found.\nMake sure the rendering is completed and try again.")

    @err_catcher(name=__name__)
    def sm_render_getDeadlineParams(self, origin: Any, dlParams: Dict[str, Any], homeDir: str) -> None:
        """Get Deadline render farm submission parameters.
        
        Args:
            origin: The state manager instance
            dlParams: Dictionary of Deadline parameters to populate
            homeDir: Prism home directory
        """
        dlParams["jobInfoFile"] = os.path.join(homeDir, "temp", "nuke_submit_info.job")
        dlParams["pluginInfoFile"] = os.path.join(
            homeDir, "temp", "nuke_plugin_info.job"
        )

        dlParams["jobInfos"]["Plugin"] = "Nuke"
        dlParams["jobInfos"]["Comment"] = "Prism-Submission-Nuke_ImageRender"

        if hasattr(self, "submitter") and getattr(self.submitter, "useBatchname", False):
            dlParams["jobInfos"]["BatchName"] = dlParams["jobInfos"]["Name"]

        self.core.getPlugin("Deadline").addEnvironmentItem(
            dlParams["jobInfos"],
            "PRISM_NUKE_TERMINAL_FILES",
            os.path.abspath(__file__)
        )
        self.core.getPlugin("Deadline").addEnvironmentItem(
            dlParams["jobInfos"],
            "PRISM_NUKE_USE_RELATIVE_PATHS",
            self.core.getConfig("nuke", "useRelativePaths", dft=False, config="user")
        )
        self.core.getPlugin("Deadline").addEnvironmentItem(
            dlParams["jobInfos"],
            "PRISM_JOB",
            os.getenv("PRISM_JOB", "")
        )

        dlParams["jobInfos"]["OutputFilename0"] = self.expandEnvVarsInFilepath(dlParams["jobInfos"]["OutputFilename0"])
        dlParams["pluginInfos"]["Version"] = self.getAppVersion(origin).split("v")[0]
        dlParams["pluginInfos"]["OutputFilePath"] = os.path.split(
            dlParams["jobInfos"]["OutputFilename0"]
        )[0]
        base, ext = os.path.splitext(
            os.path.basename(dlParams["jobInfos"]["OutputFilename0"])
        )
        dlParams["pluginInfos"]["OutputFilePrefix"] = base
        dlParams["pluginInfos"]["BatchMode"] = True
        dlParams["pluginInfos"]["BatchModeIsMovie"] = ext in self.core.media.videoFormats
        dlParams["pluginInfos"]["WriteNode"] = origin.node.fullName()

    @err_catcher(name=__name__)
    def openFarmSubmitter(self, node: Any, group: Optional[Any] = None, dependencies: Optional[List[Any]] = None, entity: Optional[Any] = None, showSubmitUi: bool = True) -> Optional[Any]:
        """Open farm submission dialog for Write node rendering.
        
        Args:
            node: The Write node
            group: The node group
            dependencies: List of dependency jobs
            entity: Optional entity to use for path calculation
            showSubmitUi: Whether to show the submit UI
            
        Returns:
            Error list if failed, True otherwise
        """
        if not group:
            group = node

        taskName = self.getIdentifierFromNode(group)
        if not taskName:
            self.core.popup("Please choose an identifier")
            return

        fileName = self.getOutputPath(node, group, force=True, entity=entity)
        if fileName == "FileNotInPipeline":
            self.core.showFileNotInProjectWarning(title="Warning")
            return

        settings = {
            "outputName": fileName,
            "node": node,
            "group": group,
            "identifier": taskName,
        }
        scenefile = self.core.getCurrentFileName()
        kwargs = {
            "state": self,
            "scenefile": scenefile,
            "settings": settings,
        }

        result = self.core.callback("onNukeOpenFarmSubmitter", **kwargs)
        for res in result:
            if isinstance(res, dict) and res.get("cancel", False):
                return [
                    "Nuke Submitter - error - %s" % res.get("details", "onNukeOpenFarmSubmitter hook returned False")
                ]

        sm = self.core.getStateManager()
        if not sm:
            self.core.popup("Failed to create the State Manager.")
            return

        state = sm.createState("ImageRender")
        state.ui.mediaType = "2drenders"
        if not state.ui.cb_manager.count():
            msg = "No farm submitter is installed."
            self.core.popup(msg)
            return

        if hasattr(self, "submitter") and self.submitter.isVisible():
            self.submitter.close()

        state.ui.node = node
        state.ui.group = group
        self.submitter = Farm_Submitter(self, state, dependencies=dependencies)
        self.submitter.loadSettings()
        if entity:
            state.ui.allowCustomContext = True
            state.ui.setContextType("Custom")
            state.ui.setCustomContext(context=entity)
            name = "Submit Renderjob - %s - %s" % (self.core.entities.getEntityName(entity), taskName)
            state.ui.e_name.setText(name)
            state.ui.nameChanged()
            
        state.ui.chb_version.setChecked(False)
        state.ui.setTaskname(self.getIdentifierFromNode(group))
        fmt = "." + group.knob("file_type").value()
        if state.ui.cb_format.findText(fmt) == -1:
            state.ui.cb_format.addItem(fmt)

        state.ui.setFormat(fmt)
        if self.core.uiAvailable and showSubmitUi:
            if entity:
                self.submitter.quiet = True
                self.submitter.exec_()
            else:
                self.submitter.show()

        else:
            self.submitter.submit(quiet=not showSubmitUi)

        return True

    @err_catcher(name=__name__)
    def openInClicked(self, node: Any, group: Optional[Any] = None) -> None:
        """Handle Open In Explorer button click on Write node.
        
        Shows context menu with options to play, browse, or open folder.
        
        Args:
            node: The Write node
            group: The node group
        """
        if not group:
            group = node

        path = group.knob("prevFileName").value()
        if path == "None":
            return

        path = self.expandEnvVarsInFilepath(path)
        menu = QMenu()

        act_play = QAction("Play")
        act_play.triggered.connect(lambda: self.core.media.playMediaInExternalPlayer(path))
        menu.addAction(act_play)

        act_browser = QAction("Open in Media Browser")
        act_browser.triggered.connect(lambda: self.openInMediaBrowser(path))
        menu.addAction(act_browser)

        act_open = QAction("Open in explorer")
        act_open.triggered.connect(lambda: self.core.openFolder(path))
        menu.addAction(act_open)

        act_copy = self.core.getCopyAction(path)
        menu.addAction(act_copy)

        menu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def openInMediaBrowser(self, path: str) -> None:
        """Open path in Prism Media Browser.
        
        Args:
            path: File path to show in Media Browser
        """
        self.core.projectBrowser()
        self.core.pb.showTab("Media")
        data = self.core.paths.getRenderProductData(path, mediaType="2drenders")
        self.core.pb.mediaBrowser.showRender(entity=data, identifier=data.get("identifier", "") + " (2d)", version=data.get("version"))

    @err_catcher(name=__name__)
    def sm_getExternalFiles(self, origin: Any) -> List[Any]:
        """Get external files referenced by nodes in the scene.
        
        Scans Read nodes and other file-referencing nodes for dependencies.
        
        Args:
            origin: The state manager instance
            
        Returns:
            List containing [absolute file paths set, empty list]
        """
        import re
        from collections import defaultdict
        prevSelectedNodes = nuke.selectedNodes() or []

        found = defaultdict(set)
        file_knob_names = {
            "file", "files", "filename", "proxy", "proxy_input", "root",
            "clip", "frame", "file0", "file1", "file2", "gizmo", "font", "icon"
        }

        [n.setSelected(False) for n in nuke.selectedNodes()]
        if os.getenv("PRISM_NUKE_TRACK_UNCONNECTED_DEPENDENCIES", "1") == "1":
            nodes = nuke.allNodes(recurseGroups=True)
        else:
            for node in nuke.allNodes(recurseGroups=True):
                if node.Class() == "Write" or node.Class() == "WritePrism":
                    node.setSelected(True)

            nuke.selectConnectedNodes()
            nodes = nuke.selectedNodes()

        for node in nodes:
            if node.Class() == "Write" or node.Class() == "WritePrism":
                continue

            for kname, knob in node.knobs().items():
                if kname.lower() in file_knob_names or knob.Class() in ("File_Knob", "InputFile_Knob"):
                    try:
                        val = knob.getValue()
                    except Exception:
                        # fallback: try to get as string
                        try:
                            val = str(knob)
                        except Exception:
                            val = None
                    if val is None:
                        continue

                    # knob.getValue may return list/tuple for multi-file knobs
                    if isinstance(val, (list, tuple)):
                        vals = val
                    else:
                        vals = [val]

                    for v in vals:
                        if not v:
                            continue
                        # try to evaluate/expand expressions: nuke.filename? nuke.toNode?
                        # nuke.knob(value) may contain expressions. nuke.filename(node) gives filename for Read nodes:
                        # Try some special cases:
                        if hasattr(node, "knob") and kname == "file":
                            # Try nuke.filename for read nodes
                            try:
                                resolved = nuke.filename(node)
                            except Exception:
                                resolved = v
                        else:
                            resolved = nuke.expression(v) if isinstance(v, str) and "$" in v else v

                        resolved = os.path.expanduser(os.path.expandvars(str(resolved)))
                        resolved = resolved.replace('\\', os.sep)
                        found['all'].add(resolved)

                        if resolved.endswith(('.gizmo', '.nk')):
                            found['gizmos'].add(resolved)
                        elif resolved.endswith(('.py',)):
                            found['plugins'].add(resolved)
                        elif resolved.endswith(('.otf', '.ttf')):
                            found['fonts'].add(resolved)
                        elif resolved.endswith(('.ocio', '.icc', '.cube', '.3dl')):
                            found['ocio'].add(resolved)
                        elif re.search(r'\.exr$|\.dpx$|\.jpg$|\.png$|\.tif$|\.tiff$|\.mov$|\.mp4$|\.cin$', resolved.lower()):
                            found['files'].add(resolved)
                        else:
                            found['others'].add(resolved)

        # existence checking
        found['absolute'] = [p for p in found['all'] if os.path.isabs(p)]
        # found['relative'] = [p for p in found['all'] if not os.path.isabs(p)]
        # found['exists'] = [p for p in found['all'] if os.path.exists(p)]
        # found['missing'] = [p for p in found['all'] if not os.path.exists(p)]
        [n.setSelected(False) for n in nuke.selectedNodes()]
        [n.setSelected(True) for n in prevSelectedNodes]
        return [found['absolute'], []]

    @err_catcher(name=__name__)
    def sm_render_preExecute(self, origin: Any) -> List[str]:
        """Pre-render execution callback.
        
        Args:
            origin: The state manager instance
            
        Returns:
            List of warnings
        """
        warnings = []
        return warnings

    @err_catcher(name=__name__)
    def sm_render_preSubmit(self, origin: Any, rSettings: Dict[str, Any]) -> None:
        """Pre-farm-submission callback.
        
        Args:
            origin: The state manager instance
            rSettings: Render settings dictionary
        """
        pass

    @err_catcher(name=__name__)
    def sm_render_undoRenderSettings(self, origin: Any, rSettings: Dict[str, Any]) -> None:
        """Undo render settings changes.
        
        Args:
            origin: The state manager instance
            rSettings: Render settings dictionary
        """
        pass

    @err_catcher(name=__name__)
    def captureViewportThumbnail(self) -> Optional[Any]:
        """Capture Nuke viewer as thumbnail image.
        
        Returns:
            QPixmap of captured frame or None if failed
        """
        if "fnFlipbookRenderer" not in globals():
            logger.debug("failed to capture thumbnail because the \"fnFlipbookRenderer\" module isn't available.")
            return

        path = tempfile.NamedTemporaryFile(suffix=".jpg").name
        viewer = nuke.activeViewer()
        if not viewer:
            return

        inputNr = viewer.activeInput()
        if inputNr is None:
            return

        prevSelectedNodes = nuke.selectedNodes() or []

        inputNode = viewer.node().input(inputNr)
        try:
            dlg = renderdialog._getFlipbookDialog(inputNode)
        except Exception as e:
            logger.warning("Error getting flipbook dialog for thumbnail capture: %s" % e)
            return

        factory = flipbooking.gFlipbookFactory
        names = factory.getNames()
        flipbook = factory.getApplication(names[0])

        prevFrame = self.getCurrentFrame()
        fb = PrismRenderedFlipbook(dlg, flipbook)
        self.isRenderingFlipbook = True
        fb.doFlipbook(path.replace("\\", "/"), self.getCurrentFrame())
        self.isRenderingFlipbook = False
        pm = self.core.media.getPixmapFromPath(path)
        try:
            os.remove(path)
        except:
            pass

        [n.setSelected(False) for n in nuke.selectedNodes()]
        [n.setSelected(True) for n in prevSelectedNodes]
        curFrame = self.getCurrentFrame()
        if curFrame != prevFrame:  # the flipbook resets the current frame to the first frame in some cases
            self.setCurrentFrame(prevFrame)

        return pm

    @err_catcher(name=__name__)
    def onImportShotsTriggered(self) -> None:
        """Handle Import Shots menu action.
        
        Opens shot list dialog for multi-shot workflow.
        """
        dlg = ShotListDlg(self)
        dlg.w_entities.getPage("Shots").tw_tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        dlg.entitiesAdded.connect(self.loadShotsIntoNuke)
        dlg.entitiesInserted.connect(lambda x: callback(x, insert=True))
        dlg.exec_()

    @err_catcher(name=__name__)
    def loadShotsIntoNuke(self, data: List[Dict[str, Any]], insert: bool = False, node: Optional[Any] = None) -> None:
        """Load shots into Nuke sequencer (multi-shot workflow).

        For each new shot creates an input Dot (connected to Shot_Read), a
        VariableGroup, and an output Dot (connected to Shot_Switch). All three
        are covered by a labelled BackdropNode. If a Shot_Switch already exists
        in the script the new shots are appended to it; otherwise the full
        Shot_Read / Shot_Switch / Shot_Write setup is created first.

        Args:
            data: List of shot data dictionaries
            insert: Insert mode flag
            node: The VariableSwitch node to add shots to
        """
        COLUMN_WIDTH  = 820
        DOT_HALF_W    = 0
        NODE_HALF_W   = 34
        BDROP_PAD_X   = 200
        BDROP_PAD_TOP = 100
        BDROP_PAD_BOT = 50
        Y_READ        = -900
        Y_SWITCH_START = -500
        Y_INPUT_DOT   = -300
        Y_VGROUP      = 50
        Y_OUTPUT_DOT  = 250
        Y_SWITCH      = 540
        Y_WRITE       = 740

        gsv_knob = nuke.root()["gsv"]
        curShots = self.getShotsFromScene()
        newShotNames = [self.core.entities.getShotName(d) for d in data]
        newShotNames = [s for s in newShotNames if s not in curShots]

        if gsv_knob.getGsvValue("prism.shot") is None:
            gsv_knob.setGsvValue("prism.shot", "")

        if gsv_knob.getDataType("prism.shot") != nuke.gsv.DataType.List:
            gsv_knob.setDataType("prism.shot", nuke.gsv.DataType.List)

        if not newShotNames:
            self.refreshGSVs()
            self.refreshNukeShotMenu()
            return

        total_new = len(newShotNames)

        # ---- find or create the shared Read / Switch / Write nodes ----
        if node and node.Class() == "VariableSwitch":
            existing_switch = node
        else:
            existing_switch = next(
                (n for n in nuke.allNodes("VariableSwitch") if n.name() == "Shot_Switch"),
                None,
            )

        if existing_switch:
            node_switch = existing_switch
            node_read = next(
                (n for n in nuke.allNodes("Read") if n.name() == "Shot_Read"), None
            )
            dot_switch_start = next(
                (n for n in nuke.allNodes("Dot") if n.name() == "shot_switch_start"), None
            )
            # count currently wired inputs
            existing_input_count = 0
            while node_switch.input(existing_input_count) is not None:
                existing_input_count += 1
            base_col_x = existing_input_count * COLUMN_WIDTH
        else:
            switch_center_x = int((total_new - 1) / 2.0 * COLUMN_WIDTH)
            identifiers = [idf.strip() for idf in os.getenv("PRISM_NUKE_MULTISHOT_IDENTIFIERS", "Plate").split(",")]
            READ_SPACING = 200
            read_nodes = []
            read_start_x = switch_center_x - (len(identifiers) - 1) * READ_SPACING // 2
            # Store sanitized-name → original-identifier map as a JSON string in a flat GSV entry
            import json as _json
            idf_map_dict = {}
            read_node_global_idx = 0

            for r_idx, identifier in enumerate(identifiers):
                shot_entity = data[0] if data else None
                version = self.core.mediaProducts.getVersion(
                    shot_entity, identifier, mediaType="3drenders"
                )
                aovs_raw = self.core.mediaProducts.getAOVsFromVersion(version) if version else []
                aovs_to_create = aovs_raw if aovs_raw else [None]
                for aov in aovs_to_create:
                    aov_name = aov["aov"] if aov else ""
                    idf_with_aov = "%s_%s" % (identifier, aov_name) if aov_name else identifier
                    sanitized = idf_with_aov.replace(" ", "_").replace("(", "").replace(")", "")
                    idf_map_dict[sanitized] = {"identifier": identifier, "aov": aov_name}
                    varname = "prism.multishot_read_%s" % sanitized

                    r_xpos = read_start_x + read_node_global_idx * READ_SPACING - NODE_HALF_W
                    read_node_global_idx += 1

                    node_read = nuke.nodes.Read(
                        name="Shot_Read_%s" % sanitized if read_nodes else "Shot_Read",
                        xpos=r_xpos,
                        ypos=Y_READ,
                        file="%%{%s}" % varname,
                        first=1001,
                        last=1100,
                    )
                    self.addUiToReadNode(node_read)
                    read_nodes.append(node_read)
                    if gsv_knob.getGsvValue(varname) is None:
                        gsv_knob.setGsvValue(varname, "")

            if gsv_knob.getGsvValue("prism.multishot_identifier_map") is None:
                gsv_knob.setGsvValue("prism.multishot_identifier_map", "")
            gsv_knob.setGsvValue("prism.multishot_identifier_map", _json.dumps(idf_map_dict))

            # Backdrop behind all read nodes
            if read_nodes:
                bd_pad = 60
                bd_rx = min(n.xpos() for n in read_nodes) - bd_pad
                bd_ry = Y_READ - bd_pad
                bd_rw = max(n.xpos() + n.screenWidth() for n in read_nodes) - bd_rx + bd_pad
                bd_rh = read_nodes[0].screenHeight() + bd_pad * 2
                nuke.nodes.BackdropNode(
                    xpos=bd_rx,
                    bdwidth=bd_rw,
                    ypos=bd_ry,
                    bdheight=bd_rh,
                    tile_color=int("2a2a4aff", 16),
                    note_font_color=4278190079,
                    note_font_size=24,
                    label="<b>Shot Reads</b>",
                )

            dot_switch_start = nuke.nodes.Dot(
                xpos=switch_center_x - DOT_HALF_W,
                ypos=Y_SWITCH_START,
                label="Shot Switch Start",
                name="shot_switch_start",
            )
            node_switch = nuke.nodes.VariableSwitch(
                name="Shot_Switch",
                xpos=switch_center_x - NODE_HALF_W,
                ypos=Y_SWITCH,
                variable="prism.shot",
            )
            self.addUiToVariableSwitchNode(node_switch)
            node_write = nuke.nodes.Write(
                name="Shot_Write",
                xpos=switch_center_x - NODE_HALF_W,
                ypos=Y_WRITE,
                file="%{prism.multishot_write}",
            )
            self.onUserNodeCreated(node_write)

            # Backdrop behind the write node
            wr_pad = 60
            nuke.nodes.BackdropNode(
                xpos=node_write.xpos() - wr_pad,
                bdwidth=node_write.screenWidth() + wr_pad * 2,
                ypos=node_write.ypos() - wr_pad,
                bdheight=node_write.screenHeight() + wr_pad * 2,
                tile_color=int("4a2a2aff", 16),
                note_font_color=4278190079,
                note_font_size=24,
                label="<b>Shot Write</b>",
            )

            # Only the first read node feeds the switch start dot
            dot_switch_start.connectInput(0, read_nodes[0])
            node_write.connectInput(0, node_switch)
            node_read = read_nodes[0]
            existing_input_count = 0
            base_col_x = 0

        # ---- per-shot nodes ----
        for i, shot_name in enumerate(newShotNames):
            input_idx    = existing_input_count + i
            col_center_x = base_col_x + i * COLUMN_WIDTH

            # input dot — sits above the VariableGroup, connected to the Read
            dot_input = nuke.nodes.Dot(
                xpos=col_center_x - DOT_HALF_W,
                ypos=Y_INPUT_DOT,
                label=shot_name,
                name="shot_in_%s" % shot_name,
            )
            if dot_switch_start is not None:
                dot_input.connectInput(0, dot_switch_start)

            # VariableGroup — between the two dots with space above.
            # Must enter the group and create Input/Output nodes inside it first;
            # nuke.nodes.VariableGroup() does NOT do this automatically, so without
            # these the node has no connection ports in the graph.
            vgroup = nuke.nodes.VariableGroup(
                xpos=col_center_x - NODE_HALF_W,
                ypos=Y_VGROUP,
            )
            vgroup.begin()
            _grp_in  = nuke.nodes.Input(xpos=0, ypos=0)
            _grp_out = nuke.nodes.Output(xpos=0, ypos=200)
            _grp_out.connectInput(0, _grp_in)
            vgroup.end()
            vgroup.connectInput(0, dot_input)

            # output dot — feeds into the VariableSwitch
            dot_output = nuke.nodes.Dot(
                xpos=col_center_x - DOT_HALF_W,
                ypos=Y_OUTPUT_DOT,
                label=shot_name,
                name="shot_out_%s" % shot_name,
            )
            dot_output.connectInput(0, vgroup)

            # wire output dot into the switch and label its input knob
            node_switch.connectInput(input_idx, dot_output)
            iknob = node_switch.knob("i%d" % input_idx)
            if iknob is not None:
                iknob.setValue(shot_name)

            # backdrop covering dot_input, vgroup and dot_output
            bd_left   = col_center_x - NODE_HALF_W - BDROP_PAD_X
            bd_top    = Y_INPUT_DOT  - BDROP_PAD_TOP
            bd_right  = col_center_x + NODE_HALF_W + BDROP_PAD_X
            bd_bottom = Y_OUTPUT_DOT + 12 + BDROP_PAD_BOT  # 12 ≈ Dot height

            hex_colour = int("1a2a3aff", 16)  # consistent dark slate-blue for all shot backdrops
            nuke.nodes.BackdropNode(
                xpos=bd_left,
                bdwidth=bd_right - bd_left,
                ypos=bd_top,
                bdheight=bd_bottom - bd_top,
                tile_color=hex_colour,
                note_font_color=4278190079,  # opaque white
                note_font_size=24,
                label="<b>%s</b>" % shot_name,
            )

            curShots.append(shot_name)

        # ---- update GSVs ----
        gsv_knob.setListOptions("prism.shot", sorted(curShots))
        
        # Select and frame all created nodes
        allCreatedNodes = []
        for node in nuke.allNodes():
            # Find nodes that were just created (have shot names in them)
            try:
                nodeName = node.name()
                if any(name in nodeName for name in newShotNames):
                    allCreatedNodes.append(node)
                elif node.name() in ["Shot_Read", "shot_switch_start", "Shot_Switch", "Shot_Write"]:
                    allCreatedNodes.append(node)
            except:
                pass
        
        # Select all created nodes
        for node in allCreatedNodes:
            node.setSelected(True)
        
        self.refreshGSVs()
        self.refreshNukeShotMenu()
        self.setShot(shotName=newShotNames[0] if newShotNames else "")

    @err_catcher(name=__name__)
    def refreshGSVs(self) -> None:
        """Refresh Global Script Variables for multi-shot workflow."""
        try:
            gsv_knob = nuke.root()["gsv"]
        except:
            return

        curShots = self.getShotsFromScene()
        val = gsv_knob.value()
        import copy
        origVal = copy.deepcopy(val)
        if "prism" not in val:
            val["prism"] = {}

        if "shot" not in val["prism"]:
            val["prism"]["shot"] = ""

        # Refresh multishot_read_* GSVs for the current shot
        shotName = gsv_knob.getGsvValue("prism.shot") or ""
        shotData = shotName.split("-")
        if len(shotData) == 2:
            shot_entity = {"type": "shot", "sequence": shotData[0], "shot": shotData[1]}
            idfs_from_entity = self.core.mediaProducts.getIdentifiersFromEntity(shot_entity)
            idf_map = {idf["identifier"].lower(): idf for idf in idfs_from_entity}
        else:
            shot_entity = None
            idf_map = {}

        import json as _json
        _idf_map_raw = gsv_knob.getGsvValue("prism.multishot_identifier_map") or ""
        try:
            idf_name_map = _json.loads(_idf_map_raw) if _idf_map_raw else {}
            if not isinstance(idf_name_map, dict):
                idf_name_map = {}
        except (ValueError, TypeError):
            logger.warning("Failed to parse prism.multishot_identifier_map GSV. Expected JSON string of dict, got: %s" % _idf_map_raw)
            idf_name_map = {}

        for key in list(val.get("prism", {}).keys()):
            if not key.startswith("multishot_read_"):
                continue
            sanitized = key[len("multishot_read_"):]
            varname = "prism.%s" % key
            readpath = ""
            entry = idf_name_map.get(sanitized)
            # Support new dict format {"identifier": ..., "aov": ...} and legacy str format
            if isinstance(entry, dict):
                original_identifier = entry.get("identifier", sanitized)
                aov_name = entry.get("aov") or None
            else:
                original_identifier = entry if isinstance(entry, str) else sanitized
                aov_name = None

            matched_idf = idf_map.get(original_identifier.lower())
            if matched_idf and shot_entity:
                version = self.core.mediaProducts.getVersion(
                    shot_entity, matched_idf["identifier"], mediaType=matched_idf.get("mediaType")
                )
                if version:
                    readpath = self.core.mediaProducts.getFileFromVersion(version, aov=aov_name, findExisting=True) or ""
                    readpath = readpath.replace("\\", "/")

            if not readpath:
                logger.warning("No media file found for shot '%s' with identifier '%s' and AOV '%s'. Setting empty path." % (shotName, original_identifier, aov_name))

            if gsv_knob.getGsvValue(varname) != readpath:
                gsv_knob.setGsvValue(varname, readpath)

        # if "identifier" not in val["prism"]:
        #     val["prism"]["identifier"] = ""

        # if "version" not in val["prism"]:
        #     val["prism"]["version"] = ""

        # if "aov" not in val["prism"]:
        #     val["prism"]["aov"] = ""

        # shotData = val["prism"]["shot"].split("-")
        # if len(shotData) != 2:
        #     identifiers = []
        # else:
        #     entity = {"type": "shot", "sequence": shotData[0], "shot": shotData[1]}
        #     identifiers = self.core.mediaProducts.getIdentifierNames(entity)

        # if identifiers:
        #     ctx = entity.copy()
        #     ctx["identifier"] = val["prism"]["identifier"]
        #     versions = sorted([version["version"] for version in self.core.mediaProducts.getVersionsFromContext(ctx)], reverse=True)
        # else:
        #     versions = []

        # if versions:
        #     ctx["version"] = val["prism"]["version"]
        #     if ctx["version"] == "latest":
        #         ctx["version"] = versions[0]

        #     aovs = [aov["aov"] for aov in self.core.mediaProducts.getAOVsFromVersion(ctx)]
        # else:
        #     aovs = []

        # readpath = ""
        # if versions:
        #     ctx["aov"] = val["prism"]["aov"]
        #     mediaFiles = self.core.mediaProducts.getFilesFromContext(ctx)
        #     validFiles = self.core.media.filterValidMediaFiles(mediaFiles)
        #     if validFiles:
        #         validFiles = sorted(validFiles, key=lambda x: x if "cryptomatte" not in os.path.basename(x) else "zzz" + x)
        #         seqFiles = self.core.media.detectSequences(validFiles)
        #         if seqFiles:
        #             readpath = list(seqFiles)[0].replace("\\", "/")

        # writepath = self.core.projectPath + "test_write.exr"

        # val["prism"]["multishot_read"] = readpath
        # val["prism"]["multishot_write"] = writepath
        if val != origVal:
            gsv_knob.setValue(val)

        changed = False
        if gsv_knob.getDataType("prism.shot") != nuke.gsv.DataType.List:
            gsv_knob.setDataType("prism.shot", nuke.gsv.DataType.List)
            gsv_knob.setFavorite("prism.shot", True)

        if gsv_knob.getListOptions("prism.shot") != curShots:
            gsv_knob.setListOptions("prism.shot", curShots)
            changed = True

        # if gsv_knob.getDataType("prism.identifier") != nuke.gsv.DataType.List:
        #     gsv_knob.setDataType("prism.identifier", nuke.gsv.DataType.List)
        #     gsv_knob.setFavorite("prism.identifier", True)

        # if gsv_knob.getListOptions("prism.identifier") != sorted(identifiers):
        #     gsv_knob.setListOptions("prism.identifier", sorted(identifiers))
        #     changed = True

        # if gsv_knob.getDataType("prism.version") != nuke.gsv.DataType.List:
        #     gsv_knob.setDataType("prism.version", nuke.gsv.DataType.List)
        #     gsv_knob.setFavorite("prism.version", True)

        # if gsv_knob.getListOptions("prism.version") != ["latest"] + sorted(versions):
        #     gsv_knob.setListOptions("prism.version", ["latest"] + sorted(versions))
        #     changed = True

        # if gsv_knob.getDataType("prism.aov") != nuke.gsv.DataType.List:
        #     gsv_knob.setDataType("prism.aov", nuke.gsv.DataType.List)
        #     gsv_knob.setFavorite("prism.aov", True)

        # if gsv_knob.getListOptions("prism.aov") != sorted(aovs):
        #     gsv_knob.setListOptions("prism.aov", sorted(aovs))
        #     changed = True

        if changed:
            self.refreshGSVs()

    @err_catcher(name=__name__)
    def getShotsFromScene(self) -> List[str]:
        """Get shot list from Nuke script (multi-shot workflow).
        
        Returns:
            List of shot names
        """
        knob = nuke.root()["gsv"]
        return knob.getListOptions("prism.shot")

    @err_catcher(name=__name__)
    def onExportTriggered(self, selectedPaths: Optional[List[str]] = None) -> Optional[bool]:
        """Handle Export Nodes menu action.
        
        Opens export dialog for selected nodes.
        
        Args:
            selectedPaths: Optional list of file paths
            
        Returns:
            False if file not in pipeline, None otherwise
        """
        sm = self.core.getStateManager()
        if not sm:
            return

        if not self.core.fileInPipeline():
            self.core.showFileNotInProjectWarning(title="Warning")
            return False

        for state in sm.states:
            if state.ui.className == "NukeExport":
                break
        else:
            state = sm.createState("NukeExport")
            if not state:
                msg = "Failed to create export state. Please contact the support."
                self.core.popup(msg)
                return

        if hasattr(self, "dlg_export"):
            self.dlg_export.close()

        self.dlg_export = ExporterDlg(self, state)
        state.ui.setTaskname("nuke")
        self.dlg_export.show()

    @err_catcher(name=__name__)
    def onStateManagerOpen(self, origin: Any) -> None:
        """Callback when State Manager opens.
        
        Loads Nuke export state class.
        
        Args:
            origin: The State Manager instance
        """
        import default_Export
        import default_Export_ui

        class NukeExportClass(QWidget, default_Export_ui.Ui_wg_Export, NukeExport, default_Export.ExportClass):
            def __init__(self) -> None:
                """Initialize Nuke export state widget combining default export and Nuke-specific functionality."""
                QWidget.__init__(self)
                self.setupUi(self)

        origin.loadState(NukeExportClass)

    @err_catcher(name=__name__)
    def sm_export_addObjects(self, origin: Any, objects: Optional[List[Any]] = None) -> None:
        """Add objects to export state.
        
        Args:
            origin: The export state instance
            objects: List of objects to add
        """
        pass

    @err_catcher(name=__name__)
    def sm_export_preExecute(self, origin: Any, startFrame: int, endFrame: int) -> List[List[Any]]:
        """Pre-export execution callback.
        
        Args:
            origin: The export state instance
            startFrame: First frame
            endFrame: Last frame
            
        Returns:
            List of warnings
        """
        warnings = []

        if not nuke.selectedNodes():
            warnings.append(
                [
                    "No nodes selected.",
                    "Select nodes to export.",
                    3,
                ]
            )

        return warnings

    @err_catcher(name=__name__)
    def sm_export_exportAppObjects(
        self,
        origin: Any,
        startFrame: int,
        endFrame: Any,
        outputName: str,
    ) -> str:
        """Export selected Nuke nodes to file.
        
        Args:
            origin: The export state instance
            startFrame: First frame
            endFrame: Last frame
            outputName: Output file path
            
        Returns:
            Output file path
        """
        nuke.nodeCopy(outputName)
        return outputName

    @err_catcher(name=__name__)
    def sm_import_importToApp(self, origin: Any, doImport: Any, update: Any, impFileName: str) -> Dict[str, Any]:
        """Import file into Nuke.
        
        Handles .nk scripts (pasted, livegroup, precomp) and 3D files (obj, fbx, abc).
        
        Args:
            origin: The import state instance
            doImport: Import mode
            update: Update mode
            impFileName: File path to import
            
        Returns:
            Dictionary with result and doImport keys
        """
        fileName = os.path.splitext(os.path.basename(impFileName))
        result = False

        ext = fileName[1].lower()
        if ext in self.plugin.sceneFormats:
            path = impFileName.replace("\\", "/")
            msg = "How do you want to import the nuke script?"
            result = self.core.popupQuestion(msg, buttons=["Paste Nodes", "Livegroup", "Precomp"])
            if result == "Paste Nodes":
                result = nuke.nodePaste(path)
            elif result == "Livegroup":
                liveGroup = nuke.createNode("LiveGroup")
                liveGroup.knob("published").fromScript("1")
                liveGroup.knob("file").setValue(path)
            elif result == "Precomp":
                nuke.createNode("Precomp", "file \"%s\"" % path)

        elif ext in [".obj", ".fbx", ".abc"]:
            path = impFileName.replace("\\", "/")
            node_read = nuke.nodes.ReadGeo2()
            node_read['file'].setValue(path) 
            node_scene = nuke.nodes.Scene(xpos=node_read.xpos() + 10, ypos=node_read.ypos()+200)
            node_render = nuke.nodes.ScanlineRender(xpos=node_read.xpos(), ypos=node_read.ypos()+400)
            node_render.connectInput(1, node_scene)
            node_scene.connectInput(0, node_read)
            result = [node_read]
        else:
            self.core.popup("Format is not supported.")
            return {"result": False, "doImport": doImport}

        return {"result": result, "doImport": doImport}

    @err_catcher(name=__name__)
    def importCamera(self, data: Dict[str, Any], filepath: str) -> None:
        """Import camera from file into Nuke.
        
        Creates Camera3, Scene, and ScanlineRender nodes.
        
        Args:
            data: Camera data dictionary
            filepath: Path to camera file
        """
        path = filepath.replace("\\", "/")
        node_read = nuke.nodes.Camera3(read_from_file_link=True, file_link=path)
        node_scene = nuke.nodes.Scene(xpos=node_read.xpos()+300, ypos=node_read.ypos())
        node_render = nuke.nodes.ScanlineRender(xpos=node_scene.xpos()-10, ypos=node_read.ypos()+200)
        node_render.connectInput(0, node_read)
        node_render.connectInput(1, node_scene)
        node_scene.connectInput(0, node_read)

    @err_catcher(name=__name__)
    def productSelectorContextMenuRequested(self, origin: Any, widget: Any, pos: Any, menu: Any) -> None:
        """Add custom menu items to product selector context menu.
        
        Adds Import Camera option for FBX/ABC files.
        
        Args:
            origin: The product selector instance
            widget: The tree widget
            pos: Click position
            menu: Context menu
        """
        if widget == origin.tw_versions:
            row = widget.rowAt(pos.y())
            if row != -1:
                pathC = widget.model().columnCount() - 1
                path = widget.model().index(row, pathC).data()
                ext = os.path.splitext(path)[1]
                if ext in [".fbx", ".abc"]:
                    item = origin.tw_identifier.currentItem()
                    data = item.data(0, Qt.UserRole)
                    action = QAction("Import Camera", origin)
                    action.triggered.connect(lambda: self.importCamera(data, filepath=path))
                    for idx, act in enumerate(menu.actions()):
                        if act.text() == "Import":
                            menu.insertAction(menu.actions()[idx+1], action)
                            break
                    else:
                        menu.insertAction(0, action)

    @err_catcher(name=__name__)
    def openMediaVersionsDialog(self) -> None:
        """Open media versions management dialog.
        
        Shows dialog to update Read nodes to latest media versions.
        """
        if hasattr(self, "dlg_mediaVersions") and self.core.isObjectValid(self.dlg_mediaVersions) and self.dlg_mediaVersions.isVisible():
            self.dlg_mediaVersions.close()

        self.dlg_mediaVersions = MediaVersionsDialog(self, useSelectedReadNodes=True)
        self.dlg_mediaVersions.show()


class NukeMultiShotRenderer(QDialog):
    """Dialog for rendering or submitting all shots in a multi-shot Nuke script."""

    def __init__(self, plugin: Any, node: Any, group: Optional[Any] = None, start: Optional[int] = None, end: Optional[int] = None, dependencies: Optional[List[Any]] = None, submit: Optional[bool] = None) -> None:
        """Initialize multi-shot renderer dialog.

        Args:
            plugin: The Nuke plugin instance
            node: The Write node
            group: The node group (WritePrism gizmo)
            start: Start frame
            end: End frame
            dependencies: List of dependency jobs
            submit: Whether to submit to farm (overrides node knob)
        """
        super(NukeMultiShotRenderer, self).__init__()
        self.plugin = plugin
        self.core = plugin.core
        self.node = node
        self.group = group if group is not None else node
        self.start = start
        self.end = end
        self.dependencies = dependencies
        self.submit = submit if submit is not None else self.group.knob("submitJob").value()
        self.core.parentWindow(self)
        self.setupUi()
        self.loadShots()

    @err_catcher(name=__name__)
    def sizeHint(self) -> QSize:
        return QSize(1000, 500)

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Build the dialog UI."""
        actionText = "Submit Jobs" if self.submit else "Render Locally"
        self.setWindowTitle("Prism - %s - All Shots" % actionText)
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        # Top toolbar
        self.lo_top = QHBoxLayout()
        self.lo_top.addStretch()

        self.btn_checkAll = QToolButton()
        self.btn_checkAll.setFocusPolicy(Qt.NoFocus)
        self.btn_checkAll.setText("All")
        self.btn_checkAll.setToolTip("Check All Shots")
        self.btn_checkAll.clicked.connect(self.checkAll)
        self.lo_top.addWidget(self.btn_checkAll)

        self.btn_uncheckAll = QToolButton()
        self.btn_uncheckAll.setFocusPolicy(Qt.NoFocus)
        self.btn_uncheckAll.setText("None")
        self.btn_uncheckAll.setToolTip("Uncheck All Shots")
        self.btn_uncheckAll.clicked.connect(self.uncheckAll)
        self.lo_top.addWidget(self.btn_uncheckAll)

        self.btn_refresh = QToolButton()
        self.btn_refresh.setFocusPolicy(Qt.NoFocus)
        refreshIconPath = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "refresh.png")
        self.btn_refresh.setIcon(self.core.media.getColoredIcon(refreshIconPath))
        self.btn_refresh.setToolTip("Refresh Shots")
        self.btn_refresh.clicked.connect(self.loadShots)
        self.lo_top.addWidget(self.btn_refresh)

        self.lo_main.addLayout(self.lo_top)

        # Shot list
        self.tw_shots = QTreeWidget()
        self.tw_shots.setHeaderLabels(["Enabled", "Shot", "Start", "End"])
        self.tw_shots.setAlternatingRowColors(True)
        self.tw_shots.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tw_shots.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tw_shots.customContextMenuRequested.connect(self.onContextMenu)
        self.tw_shots.itemChanged.connect(self.onItemChanged)
        self.tw_shots.setIconSize(QSize(100, 56))
        self.lo_main.addWidget(self.tw_shots)

        # Bottom buttons
        self.bb_main = QDialogButtonBox()
        self.btn_render = self.bb_main.addButton(actionText, QDialogButtonBox.AcceptRole)
        self.btn_cancel = self.bb_main.addButton("Cancel", QDialogButtonBox.RejectRole)
        self.bb_main.accepted.connect(self.onRenderClicked)
        self.bb_main.rejected.connect(self.reject)
        self.lo_main.addWidget(self.bb_main)

    @err_catcher(name=__name__)
    def loadShots(self) -> None:
        """Load shots from scene and populate tree widget."""
        self.tw_shots.blockSignals(True)
        self.tw_shots.clear()

        shots = self.plugin.getShotsFromScene()
        scriptStart = int(nuke.root().knob("first_frame").value())
        scriptEnd = int(nuke.root().knob("last_frame").value())

        for shotName in shots:
            item = QTreeWidgetItem(self.tw_shots)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Checked)
            item.setText(1, shotName)

            preview = self.getShotPreview(shotName)
            if preview:
                item.setIcon(1, QIcon(preview))

            start, end = self.getShotFrameRange(shotName, scriptStart, scriptEnd)

            sb_start = QSpinBox()
            sb_start.setRange(-99999, 99999)
            sb_start.setValue(start)
            sb_start.setButtonSymbols(QAbstractSpinBox.NoButtons)
            self.tw_shots.setItemWidget(item, 2, sb_start)

            sb_end = QSpinBox()
            sb_end.setRange(-99999, 99999)
            sb_end.setValue(end)
            sb_end.setButtonSymbols(QAbstractSpinBox.NoButtons)
            self.tw_shots.setItemWidget(item, 3, sb_end)

        self.tw_shots.resizeColumnToContents(0)
        self.tw_shots.setColumnWidth(0, self.tw_shots.columnWidth(0) + 20)
        self.tw_shots.resizeColumnToContents(1)
        self.tw_shots.resizeColumnToContents(2)
        self.tw_shots.setColumnWidth(2, max(self.tw_shots.columnWidth(2) + 20, 70))
        self.tw_shots.resizeColumnToContents(3)
        self.tw_shots.setColumnWidth(3, max(self.tw_shots.columnWidth(3) + 20, 70))
        self.tw_shots.blockSignals(False)

    @err_catcher(name=__name__)
    def getShotFrameRange(self, shotName: str, fallbackStart: Optional[int] = None, fallbackEnd: Optional[int] = None) -> tuple:
        """Get start/end frame range for a shot from Prism entities.

        Args:
            shotName: Shot name string
            fallbackStart: Start frame to use if shot range not found
            fallbackEnd: End frame to use if shot range not found

        Returns:
            Tuple of (start, end) as ints
        """
        shot = {"type": "shot", "shot": shotName.split("-")[1], "sequence": shotName.split("-")[0]}
        frameRange = self.core.entities.getShotRange(shot, handles=True)
        if frameRange:
            return frameRange

        if fallbackStart is not None and fallbackEnd is not None:
            return fallbackStart, fallbackEnd

        return (
            int(nuke.root().knob("first_frame").value()),
            int(nuke.root().knob("last_frame").value()),
        )

    @err_catcher(name=__name__)
    def getShotPreview(self, shotName: str) -> Optional[Any]:
        """Get scaled preview pixmap for a shot.

        Args:
            shotName: Shot name string

        Returns:
            Scaled QPixmap or None
        """
        try:
            shots = self.core.entities.getShots()
            shot = next((s for s in shots if self.core.entities.getEntityName(s) == shotName), None)
            if not shot:
                return None

            preview = self.core.entities.getEntityPreview(shot)
            if preview:
                return preview.scaled(100, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception:
            pass

        return None

    @err_catcher(name=__name__)
    def onItemChanged(self, item: Any, column: int) -> None:
        """Gray out unchecked shots."""
        if column == 0:
            enabled = item.checkState(0) == Qt.Checked
            color = self.tw_shots.palette().color(QPalette.Text) if enabled else QColor(Qt.gray)
            for col in range(self.tw_shots.columnCount()):
                item.setForeground(col, color)

    @err_catcher(name=__name__)
    def onContextMenu(self, pos: Any) -> None:
        """Show check/uncheck context menu."""
        menu = QMenu(self)
        act_checkAll = QAction("Check All", self)
        act_checkAll.triggered.connect(self.checkAll)
        menu.addAction(act_checkAll)
        act_uncheckAll = QAction("Uncheck All", self)
        act_uncheckAll.triggered.connect(self.uncheckAll)
        menu.addAction(act_uncheckAll)
        menu.exec_(self.tw_shots.viewport().mapToGlobal(pos))

    @err_catcher(name=__name__)
    def checkAll(self) -> None:
        """Check all shots."""
        for i in range(self.tw_shots.topLevelItemCount()):
            self.tw_shots.topLevelItem(i).setCheckState(0, Qt.Checked)

    @err_catcher(name=__name__)
    def uncheckAll(self) -> None:
        """Uncheck all shots."""
        for i in range(self.tw_shots.topLevelItemCount()):
            self.tw_shots.topLevelItem(i).setCheckState(0, Qt.Unchecked)

    @err_catcher(name=__name__)
    def getEnabledShots(self) -> List[str]:
        """Return list of checked shot names."""
        shots = []
        for i in range(self.tw_shots.topLevelItemCount()):
            item = self.tw_shots.topLevelItem(i)
            if item.checkState(0) == Qt.Checked:
                shots.append(item.text(1))
        return shots

    @err_catcher(name=__name__)
    def onRenderClicked(self) -> None:
        """Render or submit each enabled shot sequentially."""
        if not self.getEnabledShots():
            self.core.popup("No shots selected.")
            return

        self.accept()

        # Remember original shot to restore after all renders
        currentShot = nuke.root()["gsv"].getGsvValue("prism.shot") or ""
        success = True
        for i in range(self.tw_shots.topLevelItemCount()):
            item = self.tw_shots.topLevelItem(i)
            if item.checkState(0) != Qt.Checked:
                continue
            shotName = item.text(1)
            sb_start = self.tw_shots.itemWidget(item, 2)
            sb_end = self.tw_shots.itemWidget(item, 3)
            shotStart = sb_start.value() if sb_start else self.start
            shotEnd = sb_end.value() if sb_end else self.end
            self.plugin.setShot(shotName)
            entity = {"type": "shot", "sequence": shotName.split("-")[0], "shot": shotName.split("-")[1]}
            mods = QApplication.keyboardModifiers()
            showSubmitUi = self.submit and i == 0 and mods != Qt.ControlModifier  # Show submit UI only for the first shot
            result = self.plugin.startRender(
                self.node,
                self.group,
                start=shotStart,
                end=shotEnd,
                dependencies=self.dependencies,
                submit=self.submit,
                _skipMultiShot=True,
                entity=entity,
                showSubmitUi=showSubmitUi,
            )
            if not result:
                logger.debug("Render failed or cancelled for shot %s, stopping further renders.", shotName)
                success = False
                break

        # Restore the original shot context
        self.plugin.setShot(currentShot)
        if success:
            if self.submit:
                msg = "Render jobs submitted for %d shot(s)." % len(self.getEnabledShots())
            else:
                msg = "Rendering completed for %d shot(s)." % len(self.getEnabledShots())

            self.core.popup(msg, severity="info")


if nuke.env.get("gui") and "fnFlipbookRenderer" in globals():
    class PrismRenderedFlipbook(fnFlipbookRenderer.SynchronousRenderedFlipbook):

        def __init__(self, flipbookDialog: Any, flipbookToRun: Any) -> None:
            """Initialize Prism flipbook renderer.
            
            Args:
                flipbookDialog: The flipbook dialog instance
                flipbookToRun: The flipbook application to run
            """
            fnFlipbookRenderer.SynchronousRenderedFlipbook.__init__(self, flipbookDialog, flipbookToRun)

        def doFlipbook(self, outputpath: str, frame: int) -> None:
            """Execute flipbook render.
            
            Args:
                outputpath: Output file path
                frame: Frame number to render
            """
            self.initializeFlipbookNode()
            self.renderFlipbookNode(outputpath, frame)

        def renderFlipbookNode(self, outputpath: str, frame: int) -> None:
            """Render flipbook node to file.
            
            Args:
                outputpath: Output file path
                frame: Frame number to render
            """
            self._writeNode['file'].setValue(outputpath)
            self._writeNode['file_type'].setValue("jpeg")
            curSpace = self._writeNode['colorspace'].value()
            result = self._writeNode['colorspace'].setValue("sRGB")
            if not result:
                result = self._writeNode['colorspace'].setValue("Output - sRGB")
                if not result:
                    self._writeNode['colorspace'].setValue(curSpace)

            frange = nuke.FrameRanges(str(int(frame)))
            try:
                frameRange, views = self.getFlipbookOptions()
                nuke.executeMultiple(
                    (self._writeNode,),
                    frange,
                    views,
                    self._flipbookDialog._continueOnError.value()
                )
            except Exception as msg:
                import traceback
                print(traceback.format_exc())
                nuke.delete(self._nodeToFlipbook)
                self._nodeToFlipbook = None
                if msg.args[0][0:9] != "Cancelled":
                    nuke.message("Flipbook render failed:\n%s" % (msg.args[0],))
            finally:
                nuke.delete(self._nodeToFlipbook)
                self._nodeToFlipbook = None


class Farm_Submitter(QDialog):
    def __init__(self, plugin: Any, state: Any, dependencies: Optional[List[Any]] = None) -> None:
        """Initialize farm submission dialog.
        
        Args:
            plugin: The Nuke plugin instance
            state: The ImageRender state
            dependencies: List of dependency jobs
        """
        super(Farm_Submitter, self).__init__()
        self.plugin = plugin
        self.core = self.plugin.core
        self.core.parentWindow(self)
        self.state = state
        self.quiet = False
        self.dependencies = dependencies
        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Setup farm submission dialog UI."""
        self.setWindowTitle("Prism Farm Submitter - %s" % self.state.ui.node.fullName())
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.addWidget(self.state.ui)
        self.state.ui.f_name.setVisible(False)
        self.state.ui.w_format.setVisible(False)
        self.state.ui.f_taskname.setVisible(False)
        self.state.ui.f_resolution.setVisible(False)
        self.state.ui.gb_passes.setHidden(True)
        self.state.ui.gb_previous.setHidden(True)
        self.state.ui.gb_submit.setChecked(True)
        self.state.ui.gb_submit.setCheckable(False)
        self.state.ui.w_version.setVisible(False)
        self.state.ui.chb_version.setChecked(False)
        self.state.ui.f_cam.setVisible(False)
        if self.state.ui.cb_manager.count() == 1:
            self.state.ui.f_manager.setVisible(False)
            self.state.ui.gb_submit.setTitle(self.state.ui.cb_manager.currentText())

        self.lo_main.addStretch()
        self.b_submit = QPushButton("Submit")
        self.lo_main.addWidget(self.b_submit)
        self.b_submit.clicked.connect(self.submit)

    @err_catcher(name=__name__)
    def closeEvent(self, event: Any) -> None:
        """Handle dialog close event.
        
        Args:
            event: The close event
        """
        self.saveCurrentSettings()

    @err_catcher(name=__name__)
    def saveCurrentSettings(self) -> None:
        """Save current farm submission settings to user config and node knob."""
        import json
        settings = self.state.ui.getStateProps()
        group = getattr(self.state.ui, "group", None)
        if group:
            knob = group.knob("farmSubmissionSettings")
            if knob:
                try:
                    knob.setValue(json.dumps(settings))
                except Exception:
                    pass

    @err_catcher(name=__name__)
    def loadSettings(self, settings: Optional[Dict[str, Any]] = None) -> None:
        """Load farm submission settings.

        Loads from the node's farmSubmissionSettings knob if present,
        otherwise falls back to user config.
        
        Args:
            settings: Settings dictionary, or None to load from node knob / config
        """
        if settings is None:
            import json
            group = getattr(self.state.ui, "group", None)
            if group:
                knob = group.knob("farmSubmissionSettings")
                if knob and knob.getText():
                    try:
                        settings = json.loads(knob.getText())
                    except Exception:
                        pass

        if settings:
            self.state.ui.loadData(settings)

    @err_catcher(name=__name__)
    def submit(self, quiet=False) -> None:
        """Submit render job to farm.
        
        Args:
            quiet: If True, suppress success popup
        """
        self.hide()
        self.state.ui.gb_submit.setCheckable(True)
        self.state.ui.gb_submit.setChecked(True)

        sm = self.core.getStateManager()
        comment = self.plugin.getCommentFromNode(self.state.ui.group)
        sm.e_comment.setText(comment)
        incrementScene = os.getenv("PRISM_NUKE_SUBMISSION_INCREMENT_SCENE", "0") == "1"
        versionWarning = os.getenv("PRISM_NUKE_SUBMISSION_VERSION_WARNING", "0") == "1"
        version = self.plugin.getRenderVersionFromWriteNode(self.state.ui.group) or "next"
        result = sm.publish(
            successPopup=False,
            executeState=True,
            states=[self.state],
            saveScene=True,
            incrementScene=incrementScene,
            dependencies=self.dependencies,
            useVersion=version,
            versionWarning=versionWarning,
        )
        prevKnob = self.state.ui.group.knob("prevFileName")
        if prevKnob:
            path = self.state.ui.l_pathLast.text() or "-"
            prevKnob.setValue(path.replace("\\", "/"))
            prevKnobE = self.state.ui.group.knob("prevFileNameEdit")
            if prevKnobE:
                prevKnobE.setValue(path.replace("\\", "/"))

        sm.deleteState(self.state)
        self.plugin.getOutputPath(self.state.ui.node, self.state.ui.group)
        if result:
            msg = "Job submitted successfully."
            if quiet or self.quiet:
                logger.info(msg)
            else:
                self.core.popup(msg, severity="info")

        self.close()


class ShotListDlg(QDialog):

    entitiesAdded = Signal(object)
    entitiesInserted = Signal(object)

    def __init__(self, origin: Any, parent: Optional[Any] = None) -> None:
        """Initialize shot list dialog.
        
        Args:
            origin: The Nuke plugin instance
            parent: Parent widget
        """
        super(ShotListDlg, self).__init__()
        self.parentDlg = parent
        self.plugin = origin.plugin
        self.core = self.plugin.core
        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Setup shot list dialog UI."""
        title = "Choose Shots"

        self.setWindowTitle(title)
        self.core.parentWindow(self, parent=self.parentDlg)

        import EntityWidget
        self.w_entities = EntityWidget.EntityWidget(core=self.core, refresh=True, pages=["Shots"])
        self.w_entities.editEntitiesOnDclick = False
        self.w_entities.getPage("Shots").tw_tree.itemDoubleClicked.connect(self.itemDoubleClicked)
        self.w_entities.getPage("Shots").setSearchVisible(False)

        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Add", QDialogButtonBox.AcceptRole)
        if self.plugin.getShotsFromScene():
            self.bb_main.addButton("Insert", QDialogButtonBox.AcceptRole)

        self.bb_main.addButton("Cancel", QDialogButtonBox.RejectRole)
        self.bb_main.clicked.connect(self.buttonClicked)

        self.lo_main.addWidget(self.w_entities)
        self.lo_main.addWidget(self.bb_main)

    @err_catcher(name=__name__)
    def itemDoubleClicked(self, item: Any, column: int) -> None:
        """Handle item double click.
        
        Args:
            item: The tree widget item
            column: Column number
        """
        self.buttonClicked("add")

    @err_catcher(name=__name__)
    def buttonClicked(self, button: Any) -> None:
        """Handle button click.
        
        Args:
            button: The button or button text
        """
        if button == "add" or button.text() in ["Add", "Insert"]:
            entities = self.w_entities.getCurrentData(returnOne=False)
            if isinstance(entities, dict):
                entities = [entities]

            validEntities = []
            for entity in entities:
                if entity.get("type", "") not in ["asset", "shot"]:
                    continue

                validEntities.append(entity)

            if not validEntities:
                msg = "Invalid shot selected."
                self.core.popup(msg, parent=self)
                return

            if button == "add" or button.text() in ["Add"]:
                self.entitiesAdded.emit(validEntities)
            else:
                self.entitiesInserted.emit(validEntities)

        self.close()

    @err_catcher(name=__name__)
    def sizeHint(self) -> QSize:
        """Get recommended dialog size.
        
        Returns:
            QSize with width and height
        """
        return QSize(500, 500)


class NukeExport(object):
    className = "NukeExport"

    def setup(self, state: Any, core: Any, stateManager: Any, node: Optional[Any] = None, stateData: Optional[Dict[str, Any]] = None) -> None:
        """Setup Nuke export state.
        
        Args:
            state: The state instance
            core: The Prism core instance
            stateManager: The State Manager instance
            node: Optional node to export
            stateData: Optional state data to load
        """
        super(NukeExport, self).setup(state, core, stateManager, node, stateData)
        self.w_name.setVisible(False)
        self.w_range.setVisible(False)
        self.f_frameRange_2.setVisible(False)
        self.w_wholeScene.setVisible(False)
        self.chb_wholeScene.setChecked(True)
        self.gb_objects.setVisible(False)
        self.w_additionalOptions.setVisible(False)
        self.w_outType.setVisible(False)
        self.gb_previous.setVisible(False)
        self.cb_context.setVisible(False)
        self.setRangeType("Single Frame")


class ExporterDlg(QDialog):
    def __init__(self, origin: Any, state: Any) -> None:
        """Initialize node export dialog.
        
        Args:
            origin: The Nuke plugin instance
            state: The export state
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
    def sizeHint(self) -> QSize:
        """Get recommended dialog size.
        
        Returns:
            QSize with width and height
        """
        hint = super(ExporterDlg, self).sizeHint()
        hint += QSize(100, 0)
        return hint

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Setup export dialog UI."""
        self.setWindowTitle("Prism - Export Selected Nodes")
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.addWidget(self.state.ui)

        self.b_submit = QPushButton("Export")
        self.lo_main.addWidget(self.b_submit)
        self.b_submit.clicked.connect(self.submit)

    @err_catcher(name=__name__)
    def closeEvent(self, event: Any) -> None:
        """Handle dialog close event.
        
        Args:
            event: The close event
        """
        curItem = self.core.sm.getCurrentItem(self.core.sm.activeList)
        if self.state and curItem and id(self.state) == id(curItem):
            self.core.sm.showState()

        if self.showSm:
            self.core.sm.setHidden(False)

        event.accept()

    @err_catcher(name=__name__)
    def submit(self) -> None:
        """Submit export operation with selected nodes."""
        self.hide()

        sanityChecks = True
        version = None
        saveScene = False
        incrementScene = False

        sm = self.core.getStateManager()
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
            msg = "Exported nodes successfully."
            result = self.core.popupQuestion(msg, buttons=["Open in Product Browser", "Open in Explorer", "Close"], icon=QMessageBox.Information)
            path = self.state.ui.l_pathLast.text()
            if result == "Open in Product Browser":
                self.core.projectBrowser()
                self.core.pb.showTab("Products")
                data = self.core.paths.getCachePathData(path)
                self.core.pb.productBrowser.navigateToProduct(data["product"], entity=data)
            elif result == "Open in Explorer":
                self.core.openFolder(path)

            self.close()
        else:
            self.show()


class Prism_NoQt(object):
    def __init__(self) -> None:
        """Initialize Nuke plugin in non-Qt mode (command line rendering)."""
        self.addPluginPaths()
        nuke.addFilenameFilter(self.expandEnvVarsInFilepath)

    def addPluginPaths(self) -> None:
        """Add Prism Gizmos directory to Nuke's plugin path."""
        gdir = os.path.join(
            os.path.abspath(os.path.dirname(os.path.dirname(__file__))), "Gizmos"
        )
        gdir = gdir.replace("\\", "/")
        nuke.pluginAddPath(gdir)

    @err_catcher(name=__name__)
    def expandEnvVarsInFilepath(self, path: str) -> str:
        """Expand environment variables in file paths (non-Qt mode).
        
        Args:
            path: File path potentially containing environment variables
            
        Returns:
            Expanded file path
        """
        if os.getenv("PRISM_NUKE_USE_RELATIVE_PATHS", "1") == "0":
            return path

        expanded_path = os.path.expandvars(path)
        expanded_path = expanded_path.replace("%PRISM_JOB", os.getenv("PRISM_JOB"))
        return expanded_path


class VersionDlg(QDialog):

    versionSelected = Signal(object)

    def __init__(self, parent: Any, node: Any, group: Any) -> None:
        """Initialize version selection dialog.
        
        Args:
            parent: Parent plugin instance
            node: The Write node
            group: The node group
        """
        super(VersionDlg, self).__init__()
        self.plugin = parent
        self.core = self.plugin.core
        self.node = node
        self.group = group
        self.isValid = False
        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Setup version selection dialog UI with MediaBrowser.
        
        Validates scene is saved in Prism project and node has identifier.
        Creates UI with embedded MediaBrowser and accept/cancel buttons.
        """
        filepath = self.core.getCurrentFileName()
        entity = self.core.getScenefileData(filepath)
        if not entity or not entity.get("type"):
            msg = "Please save your scene in the Prism project first."
            self.core.popup(msg)
            return

        identifier = self.plugin.getIdentifierFromNode(self.group)
        if not identifier:
            msg = "Please enter an identifier in the settings of this node first."
            self.core.popup(msg)
            return

        if entity.get("type") == "asset":
            entityName = entity["asset_path"]
        elif entity.get("type") == "shot":
            entityName = self.core.entities.getShotName(entity)

        title = "Select version (%s - %s)" % (entityName, identifier)

        self.setWindowTitle(title)
        self.core.parentWindow(self)

        import MediaBrowser
        self.w_browser = MediaBrowser.MediaBrowser(core=self.core)
        self.w_browser.headerHeightSet = True
        self.w_browser.w_entities.setVisible(False)
        self.w_browser.w_identifier.setVisible(False)
        self.w_browser.lw_version.itemDoubleClicked.disconnect()
        self.w_browser.lw_version.itemDoubleClicked.connect(self.itemDoubleClicked)

        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Use Selected Version", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Cancel", QDialogButtonBox.RejectRole)

        self.bb_main.clicked.connect(self.buttonClicked)

        self.lo_main.addWidget(self.w_browser)
        self.lo_main.addWidget(self.bb_main)

        self.w_browser.navigate([entity, identifier + " (2d)"])
        idf = self.w_browser.getCurrentIdentifier()
        if not idf or idf["identifier"] != identifier:
            msg = "The identifier \"%s\" doesn't exist yet." % identifier
            self.core.popup(msg)
            return

        self.isValid = self.w_browser.lw_version.count() > 0
        if not self.isValid:
            msg = "No version exists under the current identifier."
            self.core.popup(msg)
            return

    @err_catcher(name=__name__)
    def itemDoubleClicked(self, item: Any) -> None:
        """Handle double-click on version list item.
        
        Args:
            item: The clicked list widget item
        """
        self.buttonClicked("select")

    @err_catcher(name=__name__)
    def buttonClicked(self, button: Any) -> None:
        """Handle dialog button clicks.
        
        Validates selected version and emits versionSelected signal.
        
        Args:
            button: Either 'select' string or QPushButton object
        """
        if button == "select" or button.text() == "Use Selected Version":
            version = self.w_browser.getCurrentVersion()
            if not version:
                msg = "Invalid version selected."
                self.core.popup(msg, parent=self)
                return

            intVersion = self.core.products.getIntVersionFromVersionName(version.get("version") or "")
            if intVersion is None:
                msg = "Invalid version selected."
                self.core.popup(msg, parent=self)
                return

            self.versionSelected.emit(intVersion)

        self.close()


class ReadMediaDialog(QDialog):

    mediaSelected = Signal(object)

    def __init__(self, parent: Any, node: Any) -> None:
        """Initialize media selection dialog.
        
        Args:
            parent: Parent plugin instance
            node: The Read node to update
        """
        super(ReadMediaDialog, self).__init__()
        self.plugin = parent
        self.core = self.plugin.core
        self.node = node
        self.isValid = False
        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Setup media selection dialog UI with MediaBrowser.
        
        Creates UI with embedded MediaBrowser for navigating entities and selecting media.
        """
        filepath = self.core.getCurrentFileName()
        entity = self.core.getScenefileData(filepath)
        title = "Select Media"
        self.setWindowTitle(title)
        self.core.parentWindow(self)

        import MediaBrowser
        self.w_browser = MediaBrowser.MediaBrowser(core=self.core)
        self.w_browser.headerHeightSet = True
        self.w_browser.lw_version.itemDoubleClicked.disconnect()
        self.w_browser.lw_version.itemDoubleClicked.connect(self.itemDoubleClicked)

        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Open", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Cancel", QDialogButtonBox.RejectRole)

        self.bb_main.clicked.connect(self.buttonClicked)

        self.lo_main.addWidget(self.w_browser)
        self.lo_main.addWidget(self.bb_main)

        self.w_browser.navigate([entity])

    @err_catcher(name=__name__)
    def itemDoubleClicked(self, item: Any) -> None:
        """Handle double-click on version list item.
        
        Args:
            item: The clicked list widget item
        """
        self.buttonClicked("select")

    @err_catcher(name=__name__)
    def buttonClicked(self, button: Any) -> None:
        """Handle dialog button clicks.
        
        Retrieves selected media (source, AOV, version, or identifier) and emits signal.
        
        Args:
            button: Either 'select' string or QPushButton object
        """
        if button == "select" or button.text() == "Open":
            data = self.w_browser.getCurrentSource()
            if not data:
                data = self.w_browser.getCurrentAOV()
                if not data:
                    data = self.w_browser.getCurrentVersion()
                    if not data:
                        data = self.w_browser.getCurrentIdentifier()

            if not data:
                msg = "Invalid version selected."
                self.core.popup(msg, parent=self)
                return

            self.mediaSelected.emit(data)

        self.close()


class MediaVersionsDialog(QDialog):
    """Non-modal dialog for managing media versions in Read nodes"""
    
    def __init__(self, plugin: Any, useSelectedReadNodes: bool = False) -> None:
        """Initialize media versions management dialog.
        
        Args:
            plugin: The Nuke plugin instance
            useSelectedReadNodes: Use selected Read nodes when available
        """
        super(MediaVersionsDialog, self).__init__()
        self.plugin = plugin
        self.core = plugin.core
        self.useSelectedReadNodes = useSelectedReadNodes
        self.groupByShot = False
        self.nodeItems = []
        self.shotContextPlaceholderText = "Switch Shot..."
        self.noReadNodeSelectedPlaceholderText = "No Read Node Selected"
        self.shotContextComboPopulated = False
        self.shotContextComboShots = []
        self.syncingShotContextCombo = False
        self.suspendNukeSelectionSync = False
        self.readNodesForRefreshOverride = None
        self.shotContextComboShowsShots = False
        
        self.setupUi()
        self.connectEvents()
        self.refreshNodes()
    
    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Setup the dialog UI with tree widget and toolbar."""
        self.setWindowTitle("Manage Media Versions")
        self.resize(1200, 600)
        self.core.parentWindow(self)
        
        # Make it non-modal
        self.setWindowModality(Qt.NonModal)
        
        # Main layout
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setToolTip("Refresh the list of Read nodes")
        toolbar.addWidget(self.btn_refresh)

        self.l_shotContext = QLabel("Shot:")
        toolbar.addWidget(self.l_shotContext)
        self.cb_shotContext = QComboBox()
        self.cb_shotContext.setMinimumWidth(180)
        self.cb_shotContext.setToolTip("Switch managed Read nodes to another shot")
        self.cb_shotContext.addItem(self.noReadNodeSelectedPlaceholderText, None)
        toolbar.addWidget(self.cb_shotContext)
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
        
        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setAlternatingRowColors(True)
        self.tree.setSortingEnabled(True)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        
        # Setup columns
        self.setupColumns()
        
        layout.addWidget(self.tree)
        
        # Status bar
        self.statusLabel = QLabel("Ready")
        toolbar.addWidget(self.statusLabel)
        
        self.setLayout(layout)
        
    @err_catcher(name=__name__)
    def setupColumns(self) -> None:
        """Setup tree widget columns with proper widths."""
        columns = ["Node Name", "Asset/Shot", "Identifier", "Version", "Status", "Filepath"]
        self.tree.setHeaderLabels(columns)
        
        # Set column widths
        self.tree.setColumnWidth(0, 150)  # Node Name
        self.tree.setColumnWidth(1, 120)  # Shot
        self.tree.setColumnWidth(2, 150)  # Identifier
        self.tree.setColumnWidth(3, 100)  # Version
        self.tree.setColumnWidth(4, 120)  # Status
        self.tree.setColumnWidth(5, 400)  # Filepath
    
    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect UI events to handler methods."""
        self.btn_refresh.clicked.connect(self.refreshNodes)
        self.cb_shotContext.activated.connect(self.onShotContextChanged)
        self.tree.customContextMenuRequested.connect(self.showContextMenu)
        self.tree.itemSelectionChanged.connect(self.onSelectionChanged)
        self.tree.itemDoubleClicked.connect(self.onItemDoubleClicked)

    @err_catcher(name=__name__)
    def showEvent(self, event: Any) -> None:
        """Populate the shot switch combo only when the dialog is shown."""
        super(MediaVersionsDialog, self).showEvent(event)
        if not self.shotContextComboPopulated:
            self.populateShotContextCombo()

        self.syncShotContextComboToSelection()

    @err_catcher(name=__name__)
    def populateShotContextCombo(self) -> None:
        """Load available shots into the shot switch combo."""
        currentText = self.cb_shotContext.currentText()
        self.syncingShotContextCombo = True
        try:
            shots = self.core.entities.getShots()
            self.shotContextComboShots = sorted(shots, key=lambda shot: (self.core.entities.getShotName(shot) or "").lower())
            self.shotContextComboPopulated = True
            self.rebuildShotContextCombo(showShots=self.hasSelectedReadNodeItem())
            idx = self.cb_shotContext.findText(currentText)
            if idx != -1:
                self.cb_shotContext.setCurrentIndex(idx)

        finally:
            self.syncingShotContextCombo = False

    @err_catcher(name=__name__)
    def rebuildShotContextCombo(self, showShots: bool) -> None:
        """Switch shot combo contents between no-selection placeholder and shot list."""
        if self.shotContextComboShowsShots == showShots and self.cb_shotContext.count():
            return

        self.cb_shotContext.clear()
        if not showShots:
            self.cb_shotContext.addItem(self.noReadNodeSelectedPlaceholderText, None)
            self.shotContextComboShowsShots = False
            return

        self.cb_shotContext.addItem(self.shotContextPlaceholderText, None)
        for shot in getattr(self, "shotContextComboShots", []):
            shotName = self.core.entities.getShotName(shot)
            if not shotName:
                continue

            self.cb_shotContext.addItem(shotName, shot)

        self.shotContextComboShowsShots = True

    @err_catcher(name=__name__)
    def hasSelectedReadNodeItem(self) -> bool:
        """Check whether the dialog tree has a selected managed Read row."""
        for item in self.tree.selectedItems():
            try:
                data = item.data(0, Qt.UserRole) or {}
            except Exception:
                continue

            node = data.get("node") if isinstance(data, dict) else None
            if node:
                return True

        return False

    @err_catcher(name=__name__)
    def getOutdatedMedia(self) -> List[Any]:
        """Get list of Read nodes with update available status.
        
        Returns:
            List of tree widget items with 'update available' status
        """
        items = []
        for item in self.nodeItems:
            status = item.text(4).lower()
            if status == "update available":
                items.append(item)

        return items

    @err_catcher(name=__name__)
    def refreshNodes(self) -> None:
        """Scan all Read nodes and populate the tree widget."""
        selectedNodeNames = self.getSelectedNodeNames()
        wasSuspended = self.suspendNukeSelectionSync
        self.suspendNukeSelectionSync = True
        try:
            self.tree.clear()
            self.nodeItems = []
        finally:
            self.suspendNukeSelectionSync = wasSuspended
        
        # Get all Read nodes in the script
        allReadNodes = [node for node in nuke.allNodes(recurseGroups=True) if node.Class() in ["Read", "DeepRead"]]
        usingSelectedReadNodes = False
        if self.readNodesForRefreshOverride is not None:
            readNodes = []
            for node in self.readNodesForRefreshOverride:
                try:
                    if node.Class() in ["Read", "DeepRead"]:
                        readNodes.append(node)
                except Exception:
                    pass

            usingSelectedReadNodes = self.useSelectedReadNodes

        else:
            readNodes = allReadNodes

        if self.readNodesForRefreshOverride is None and self.useSelectedReadNodes:
            selectedReadNodes = [node for node in allReadNodes if node.isSelected()]
            if selectedReadNodes:
                readNodes = selectedReadNodes
                usingSelectedReadNodes = True
        
        if not allReadNodes:
            self.statusLabel.setText("No Read nodes found in script")
            self.syncShotContextComboToSelection()
            return
            
        items = []
        for node in readNodes:
            if node.Class() == "Read" and node.knob("tab_prism"):
                self.plugin.ensureReadNodeMediaVersionExclusionKnob(node)

            if self.plugin.isReadNodeExcludedFromMediaVersions(node):
                continue

            item = self.createTreeItem(node)
            if item:
                items.append(item)
        
        if self.groupByShot:
            self.groupItemsByShot(items)
        else:
            for item in items:
                self.tree.addTopLevelItem(item)

        for item in items:
            # Create version combo box
            self.createVersionComboBox(item)

        self.nodeItems = items
        if usingSelectedReadNodes:
            self.statusLabel.setText(f"Found {len(items)} selected managed Read nodes")
        else:
            self.statusLabel.setText(f"Found {len(items)} managed Read nodes")

        self.tree.expandAll()
        self.tree.resizeColumnToContents(0)
        self.tree.setColumnWidth(0, self.tree.columnWidth(0) + 20)
        self.tree.resizeColumnToContents(1)
        self.tree.setColumnWidth(1, self.tree.columnWidth(1) + 20)
        self.tree.resizeColumnToContents(2)
        self.tree.setColumnWidth(2, self.tree.columnWidth(2) + 20)
        self.tree.resizeColumnToContents(3)
        self.tree.setColumnWidth(3, self.tree.columnWidth(3) + 20)
        self.restoreSelectedNodeNames(selectedNodeNames)
        self.syncShotContextComboToSelection()

    @err_catcher(name=__name__)
    def getSelectedNodeNames(self) -> List[str]:
        """Return full node names selected in the dialog tree."""
        nodeNames = []
        for item in self.tree.selectedItems():
            try:
                data = item.data(0, Qt.UserRole) or {}
            except Exception:
                continue

            node = data.get("node") if isinstance(data, dict) else None
            if not node:
                continue

            try:
                nodeNames.append(node.fullName())
            except Exception:
                pass

        return nodeNames

    @err_catcher(name=__name__)
    def restoreSelectedNodeNames(self, nodeNames: List[str]) -> None:
        """Restore dialog tree selection by full node name after refresh."""
        if not nodeNames:
            return

        nodeNames = set(nodeNames)
        wasSuspended = self.suspendNukeSelectionSync
        self.suspendNukeSelectionSync = True
        try:
            for item in self.nodeItems:
                try:
                    data = item.data(0, Qt.UserRole) or {}
                    node = data.get("node") if isinstance(data, dict) else None
                    if node and node.fullName() in nodeNames:
                        item.setSelected(True)
                except Exception:
                    pass
        finally:
            self.suspendNukeSelectionSync = wasSuspended

    @err_catcher(name=__name__)
    def createTreeItem(self, node: Any) -> Optional[Any]:
        """Create a tree widget item for a Read node.
        
        Args:
            node: The Read or DeepRead node
            
        Returns:
            QTreeWidgetItem with node information, or None on error
        """
        filepath = node.knob("file").value() or ""
        entityName = ""
        identifier = ""
        version = ""
        pathData = {}
        if filepath:                
            # Expand environment variables
            filepath = self.plugin.expandEnvVarsInFilepath(filepath)
            
            # Try to get information from Prism path structure
            pathData = self.getContextFromFilepath(filepath)
            if pathData:
                identifier = pathData.get("identifier", "")
                version = pathData.get("version", "")
                entityName = self.core.entities.getEntityName(pathData)
        
        # Calculate status
        status, statusColor = self.calculateVersionStatus(filepath, version)
        
        # Create the tree item
        item = QTreeWidgetItem([
            node.fullName(),
            entityName,
            identifier,
            version,
            status,
            filepath
        ])
        
        # Store the node reference and additional data
        item.setData(0, Qt.UserRole, {"node": node, "context": pathData})
        item.setData(4, Qt.UserRole + 1, statusColor)  # Store status color
        item.setToolTip(5, filepath)
        
        # Set status column background color
        if statusColor:
            item.setBackground(4, QColor(statusColor))
        
        return item

    @err_catcher(name=__name__)
    def getContextFromFilepath(self, filepath: str) -> Dict[str, Any]:
        """Extract Prism context from a file path.
        
        Parses file path to extract entity, identifier, version, and other metadata.
        
        Args:
            filepath: Path to the media file
            
        Returns:
            Dictionary with context data (entity, identifier, version, etc.)
        """
        mediaType = self.core.mediaProducts.getMediaTypeFromPath(filepath) or "2drenders"
        pathData = self.core.paths.getRenderProductData(filepath, mediaType=mediaType)
        if pathData and not pathData.get("identifier"):
            entityType = self.core.paths.getEntityTypeFromPath(filepath)
            key = None
            if mediaType == "playblasts":
                if entityType == "asset":
                    key = "playblastFilesAssets"
                elif entityType == "shot":
                    key = "playblastFilesShots"
            else:
                if entityType == "asset":
                    key = "renderFilesAssets"
                elif entityType == "shot":
                    key = "renderFilesShots"

            if not key:
                return pathData
            
            context = {
                "type": entityType,
                "entityType": entityType,
            }

            context["mediaType"] = mediaType
            location = self.core.paths.getLocationFromPath(filepath)
            if location:
                context["project_path"] = self.core.paths.getRenderProductBasePaths()[location]

            template = self.core.projects.getResolvedProjectStructurePath(key, context=context)
            context.update(pathData)
            pathData = self.core.projects.extractKeysFromPath(os.path.dirname(os.path.normpath(filepath)), os.path.dirname(template), context=context)

        return pathData
    
    @err_catcher(name=__name__)
    def calculateVersionStatus(self, filepath: str, currentVersion: str) -> Tuple[str, str]:
        """Calculate version status for a media file.
        
        Args:
            filepath: Path to the media file
            currentVersion: Current version string from the node
            
        Returns:
            Tuple of (status_text, background_color):
                - ('latest', '#266D26') if current version is latest
                - ('update available', '#AF571C') if newer version exists
                - ('unknown', '#636363') if status cannot be determined
        """
        if filepath and "Prism_missing_media" in filepath.replace("\\", "/"):
            return "error", "#8A1F1F"

        if not filepath or not currentVersion:
            return "unknown", "#636363"  # Gray background
        
        try:
            # Get available versions
            versions = self.getAvailableVersions(filepath)
            if not versions:
                return "unknown", "#636363"  # Gray background
            
            # Get the latest version (first in sorted list)
            latestVersion = versions[0] if versions else None
            
            if not latestVersion:
                return "unknown", "#636363"  # Gray background
            
            if currentVersion == latestVersion:
                return "latest", "#266D26"  # Light green background
            else:
                return "update available", "#AF571C"  # Light orange background
                
        except Exception as e:
            logger.warning(f"Failed to calculate version status for {filepath}: {str(e)}")
            return "unknown", "#636363"  # Gray background

    @err_catcher(name=__name__)
    def createVersionComboBox(self, item: Any) -> None:
        """Create version combo box widget for tree item.
        
        Populates combo box with available versions and sets current selection.
        Connects version change signal to update Read node.
        
        Args:
            item: The tree widget item to add combo box to
        """
        node = item.data(0, Qt.UserRole)["node"]
        filepath = node.knob("file").value() or ""
        filepath = self.plugin.expandEnvVarsInFilepath(filepath)
        combo = QComboBox()
        
        # Get available versions
        versions = self.getAvailableVersions(filepath)
        
        if versions:
            combo.addItems(versions)
            
            # Set current version
            try:
                mediaType = self.core.mediaProducts.getMediaTypeFromPath(filepath) or "2drenders"
                pathData = self.core.paths.getRenderProductData(filepath, mediaType=mediaType)
                currentVersion = pathData.get("version", "")
                if currentVersion and currentVersion in versions:
                    combo.setCurrentText(currentVersion)
            except:
                pass
            
            # Connect version change signal
            combo.currentTextChanged.connect(
                lambda version, n=node: self.onVersionChanged(n, version)
            )
        else:
            combo.addItem("No versions found")
            combo.setEnabled(False)
            
        # Set the combo box in the tree
        self.tree.setItemWidget(item, 3, combo)

    @err_catcher(name=__name__)
    def getAvailableVersions(self, filepath: str) -> List[str]:
        """Get available versions for a media file.
        
        Args:
            filepath: Path to the media file
            
        Returns:
            List of version strings sorted in descending order (latest first)
        """
        mediaType = self.core.mediaProducts.getMediaTypeFromPath(filepath) or "2drenders"
        pathData = self.core.paths.getRenderProductData(filepath, mediaType=mediaType)
        if not pathData:
            return []
            
        # Create context for version lookup
        ctx = {
            "type": pathData.get("type"),
            "identifier": pathData.get("identifier", ""),
            "mediaType": mediaType,
        }
        if ctx["type"] == "asset":
            ctx["asset_path"] = pathData.get("asset_path", "")
        elif ctx["type"] == "shot":
            ctx["sequence"] = pathData.get("sequence", "")
            ctx["shot"] = pathData.get("shot", "")
        
        # Get all versions
        versions = self.core.mediaProducts.getVersionsFromContext(ctx)
        versionNames = [v["version"] for v in versions]
        
        # Sort versions (latest first)
        return sorted(versionNames, reverse=True)

    @err_catcher(name=__name__)
    def syncShotContextComboToSelection(self) -> None:
        """Select the current shot of the selected Read node in the shot combo."""
        if self.syncingShotContextCombo:
            return

        shotName = ""
        selectedItems = self.tree.selectedItems()
        hasSelectedReadNode = False
        for item in selectedItems:
            try:
                data = item.data(0, Qt.UserRole) or {}
            except Exception:
                continue

            node = data.get("node") if isinstance(data, dict) else None
            if not node:
                continue

            hasSelectedReadNode = True
            pathData = self.getShotContextFromReadNode(node)
            if not pathData:
                continue

            shotName = self.core.entities.getShotName(pathData) or ""
            if shotName:
                break

        self.syncingShotContextCombo = True
        try:
            if self.shotContextComboPopulated:
                self.rebuildShotContextCombo(showShots=hasSelectedReadNode)

            idx = 0
            if shotName and hasSelectedReadNode and self.shotContextComboPopulated:
                idx = self.cb_shotContext.findText(shotName)
                if idx == -1:
                    idx = 0

            self.cb_shotContext.setCurrentIndex(idx)
        finally:
            self.syncingShotContextCombo = False

    @err_catcher(name=__name__)
    def getShotContextFromReadNode(self, node: Any) -> Optional[Dict[str, Any]]:
        """Get shot media context from a Read node file path."""
        filepath = node.knob("file").value() or ""
        if not filepath:
            return None

        filepath = self.plugin.expandEnvVarsInFilepath(filepath)
        mediaType = self.core.mediaProducts.getMediaTypeFromPath(filepath) or "2drenders"
        pathData = self.core.paths.getMediaProductData(filepath, mediaType=mediaType)
        if not pathData:
            pathData = self.getContextFromFilepath(filepath)

        if not pathData or pathData.get("type") != "shot":
            return None

        if not pathData.get("sequence") or not pathData.get("shot"):
            return None

        return pathData

    @err_catcher(name=__name__)
    def onShotContextChanged(self, index: int) -> None:
        """Switch managed Read nodes to the shot selected in the toolbar combo."""
        if self.syncingShotContextCombo:
            return

        if not isinstance(index, int):
            index = self.cb_shotContext.findText(index)

        targetShot = self.cb_shotContext.itemData(index)
        if not targetShot:
            return

        targetShotName = self.core.entities.getShotName(targetShot) or self.cb_shotContext.itemText(index)
        self.statusLabel.setText("Switching managed Read nodes to %s..." % targetShotName)

        selectedReadNodes = self.getSelectedReadNodesFromTree()
        nodesToSwitch = selectedReadNodes or self.getVisibleReadNodes()
        if not nodesToSwitch:
            self.statusLabel.setText("No managed Read nodes selected")
            return

        if selectedReadNodes:
            self.statusLabel.setText(
                "Switching %s selected Read node(s) to %s..." % (len(selectedReadNodes), targetShotName)
            )

        visibleReadNodes = []
        for item in self.nodeItems:
            try:
                data = item.data(0, Qt.UserRole) or {}
                node = data.get("node") if isinstance(data, dict) else None
            except Exception:
                node = None

            if node:
                visibleReadNodes.append(node)

        selectedNodes = nuke.selectedNodes() or []
        updatedCount, missingCount, skippedCount = self.switchManagedReadNodesToShot(targetShot, readNodes=nodesToSwitch)
        self.suspendNukeSelectionSync = True
        self.readNodesForRefreshOverride = visibleReadNodes
        try:
            self.refreshNodes()
        finally:
            self.readNodesForRefreshOverride = None
            for node in nuke.selectedNodes():
                node.setSelected(False)

            for node in selectedNodes:
                try:
                    node.setSelected(True)
                except Exception:
                    pass

            self.suspendNukeSelectionSync = False

        self.statusLabel.setText(
            "Switched %s Read nodes to %s, %s missing, %s skipped"
            % (updatedCount, targetShotName, missingCount, skippedCount)
        )
        self.syncShotContextComboToSelection()

    @err_catcher(name=__name__)
    def getSelectedReadNodesFromTree(self) -> List[Any]:
        """Return Read nodes selected in the dialog tree."""
        nodes = []
        seen = set()
        for item in self.tree.selectedItems():
            try:
                data = item.data(0, Qt.UserRole) or {}
            except Exception:
                continue

            node = data.get("node") if isinstance(data, dict) else None
            if not node:
                continue

            try:
                nodeName = node.fullName()
            except Exception:
                continue

            if nodeName in seen:
                continue

            seen.add(nodeName)
            nodes.append(node)

        return nodes

    @err_catcher(name=__name__)
    def getVisibleReadNodes(self) -> List[Any]:
        """Return all currently visible managed Read nodes from the tree."""
        nodes = []
        seen = set()
        for item in self.nodeItems:
            try:
                data = item.data(0, Qt.UserRole) or {}
            except Exception:
                continue

            node = data.get("node") if isinstance(data, dict) else None
            if not node:
                continue

            try:
                nodeName = node.fullName()
            except Exception:
                continue

            if nodeName in seen:
                continue

            seen.add(nodeName)
            nodes.append(node)

        return nodes

    @err_catcher(name=__name__)
    def switchManagedReadNodesToShot(self, targetShot: Dict[str, Any], readNodes: Optional[List[Any]] = None) -> Tuple[int, int, int]:
        """Rewrite visible managed Read node paths to matching media in target shot."""
        updatedCount = 0
        missingCount = 0
        skippedCount = 0
        targetShotName = self.core.entities.getShotName(targetShot) or "shot"

        if readNodes is None:
            readNodes = self.getVisibleReadNodes()

        nodeDataByName = {}
        for item in self.nodeItems:
            try:
                data = item.data(0, Qt.UserRole) or {}
                node = data.get("node")
            except Exception:
                node = None

            if not node:
                continue

            try:
                nodeDataByName[node.fullName()] = data
            except Exception:
                pass

        for node in readNodes:
            data = {}
            try:
                data = nodeDataByName.get(node.fullName(), {})
            except Exception:
                pass

            if not node or not node.knob("file"):
                skippedCount += 1
                continue

            currentPath = node.knob("file").value() or ""
            if not currentPath:
                skippedCount += 1
                continue

            currentPath = self.plugin.expandEnvVarsInFilepath(currentPath)
            mediaType = self.core.mediaProducts.getMediaTypeFromPath(currentPath) or "2drenders"
            pathData = self.core.paths.getMediaProductData(currentPath, mediaType=mediaType)
            if not pathData:
                pathData = data.get("context") or self.getContextFromFilepath(currentPath)

            if not pathData or pathData.get("type") != "shot":
                skippedCount += 1
                continue

            identifier = pathData.get("identifier")
            if not identifier:
                skippedCount += 1
                continue

            targetContext = pathData.copy()
            targetContext.update(targetShot)
            targetContext["type"] = "shot"
            targetContext["entityType"] = "shot"
            targetContext["identifier"] = identifier
            targetContext["mediaType"] = mediaType

            newPath = self.resolvePathForTargetShot(targetContext, pathData, mediaType)
            logger.debug(f"Switching Read node {node.fullName()} from {currentPath} to {newPath} for shot {targetShotName}")
            if newPath:
                node.knob("file").fromUserText(newPath)
                updatedCount += 1
                continue

            missingCount += 1

        return updatedCount, missingCount, skippedCount

    @err_catcher(name=__name__)
    def resolvePathForTargetShot(self, targetContext: Dict[str, Any], sourceContext: Dict[str, Any], mediaType: str) -> Optional[str]:
        """Resolve latest matching target-shot media and format it for a Nuke Read knob."""
        version = self.core.mediaProducts.getVersion(
            targetContext,
            targetContext["identifier"],
            mediaType=mediaType,
        )
        if not version:
            return None

        if "aov" in version:
            del version["aov"]

        aovs = self.core.mediaProducts.getAOVsFromVersion(version)
        if aovs:
            aovNames = [aov["aov"] for aov in aovs]
            aov = sourceContext.get("aov") if sourceContext.get("aov") in aovNames else aovNames[0]
        else:
            aov = None

        newPath = self.core.mediaProducts.getFileFromVersion(version, aov=aov, findExisting=True)
        if not newPath:
            return None

        useRel = self.core.getConfig("nuke", "useRelativePaths", dft=False, config="user")
        if useRel:
            newPath = self.plugin.makePathRelative(newPath)

        if "#" in newPath:
            files = self.core.media.getFilesFromSequence(newPath)
            start, end = self.core.media.getFrameRangeFromSequence(files)
            if start and end and start != "?" and end != "?":
                newPath += " %s-%s" % (start, end)

        return newPath

    @err_catcher(name=__name__)
    def onVersionChanged(self, node: Any, version: str) -> bool:
        """Handle version change in combo box.
        
        Updates the Read node's file path to the selected version.
        
        Args:
            node: The Read node to update
            version: Version string selected from combo box
            
        Returns:
            True if successful, False otherwise
        """
        # Get current filepath
        currentPath = node.knob("file").value()
        currentPath = self.plugin.expandEnvVarsInFilepath(currentPath)
        
        # Get path data
        mediaType = self.core.mediaProducts.getMediaTypeFromPath(currentPath) or "2drenders"
        pathData = self.core.paths.getRenderProductData(currentPath, mediaType=mediaType)
        if not pathData:
            return

        version = self.core.mediaProducts.getVersion(pathData, pathData["identifier"], mediaType=mediaType, version=version)
        if not version:
            self.core.popup(f"Version {version} not found.")
            return
    
        aovs = self.core.mediaProducts.getAOVsFromVersion(pathData)
        if aovs:
            aosNames = [aov["aov"] for aov in aovs]
            aov = pathData.get("aov") if pathData.get("aov") and pathData.get("aov") in aosNames else aosNames[0]
        else:
            aov = None

        newPath = self.core.mediaProducts.getFileFromVersion(version, aov=aov, findExisting=True)
        if not newPath:
            self.core.popup(f"File for version {version} not found.")
            return
        
        # Update the Read node
        useRel = self.core.getConfig("nuke", "useRelativePaths", dft=False, config="user")
        if useRel:
            newPath = self.plugin.makePathRelative(newPath)
        
        # Handle frame range
        if "#" in newPath:
            files = self.core.media.getFilesFromSequence(newPath)
            start, end = self.core.media.getFrameRangeFromSequence(files)
            if start and end and start != "?" and end != "?":
                newPath += f" {start}-{end}"
        
        node.knob("file").fromUserText(newPath)
        
        # Refresh the item
        self.refreshSingleItem(node)
        return True
                
    @err_catcher(name=__name__)
    def refreshSingleItem(self, node: Any) -> None:
        """Refresh a single tree item.
        
        Updates filepath, version, and status for the specified node's tree item.
        
        Args:
            node: The Read node whose tree item should be refreshed
        """
        # Find the item for this node
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.data(0, Qt.UserRole)["node"] == node:
                # Update filepath and version info
                filepath = node.knob("file").value()
                filepath = self.plugin.expandEnvVarsInFilepath(filepath)
                item.setText(5, filepath)  # Filepath column is now index 5
                
                # Update version
                try:
                    pathData = self.getContextFromFilepath(filepath)
                    version = pathData.get("version", "") if pathData else ""
                    item.setText(3, version)  # Version column
                    
                    # Update status
                    status, statusColor = self.calculateVersionStatus(filepath, version)
                    item.setText(4, status)  # Status column
                    if statusColor:
                        item.setBackground(4, QColor(statusColor))
                        
                except Exception as e:
                    logger.warning(f"Failed to refresh item for node {node.name()}: {str(e)}")
                    
                break
    
    @err_catcher(name=__name__)
    def groupItemsByShot(self, items: List[Any]) -> None:
        """Group tree items by shot.
        
        Creates parent shot items and nests Read nodes under them.
        
        Args:
            items: List of QTreeWidgetItem objects to group
        """
        shotGroups = {}
        
        for item in items:
            shotName = item.text(1)  # Shot column
            if not shotName:
                shotName = "Unknown"
                
            if shotName not in shotGroups:
                # Create shot group
                shotItem = QTreeWidgetItem([shotName, "", "", "", "", ""])  # Added extra column for Status
                font = shotItem.font(0)
                font.setBold(True)
                shotItem.setFont(0, font)
                shotGroups[shotName] = shotItem
                self.tree.addTopLevelItem(shotItem)
            
            # Add item under shot group
            shotGroups[shotName].addChild(item)

    @err_catcher(name=__name__)
    def showContextMenu(self, position: Any) -> None:
        """Show context menu for tree widget.
        
        Provides options to update nodes, toggle grouping, and refresh.
        
        Args:
            position: Mouse position in tree widget coordinates
        """
        menu = QMenu()
        
        # Check if any items are selected
        selectedItems = self.tree.selectedItems()
        if selectedItems:
            # Update to latest action
            updateAction = menu.addAction("Update to Latest")
            updateAction.triggered.connect(self.updateSelectedToLatest)
            menu.addSeparator()
        
        # Group by shot toggle
        if self.groupByShot:
            action = menu.addAction("Ungroup by Shot")
        else:
            action = menu.addAction("Group by Shot")
        action.triggered.connect(self.toggleGroupByShot)
        
        menu.addSeparator()
        
        # Refresh action
        refreshAction = menu.addAction("Refresh")
        refreshAction.triggered.connect(self.refreshNodes)
        
        # Show menu at cursor position
        menu.exec_(self.tree.mapToGlobal(position))
    
    @err_catcher(name=__name__)
    def updateSelectedToLatest(self) -> None:
        """Update all selected nodes to their latest versions.
        
        Iterates through selected tree items and updates their Read nodes
        to the latest available version.
        """
        selectedItems = self.tree.selectedItems()
        if not selectedItems:
            return
        
        updatedCount = 0
        failedCount = 0
        
        for item in selectedItems:
            try:
                node = item.data(0, Qt.UserRole)["node"]
                if not node or not hasattr(node, 'knob'):
                    continue
                
                # Get current filepath
                currentPath = node.knob("file").value()
                if not currentPath:
                    continue
                    
                currentPath = self.plugin.expandEnvVarsInFilepath(currentPath)
                
                # Get available versions
                versions = self.getAvailableVersions(currentPath)
                if not versions:
                    failedCount += 1
                    continue
                
                # Get latest version
                latestVersion = versions[0]
                currentVersion = item.text(3)  # Version column
                
                if currentVersion == latestVersion:
                    continue  # Already latest
                
                # Update to latest version
                result = self.onVersionChanged(node, latestVersion)
                if result:
                    updatedCount += 1
                else:
                    failedCount += 1
                
            except Exception as e:
                logger.warning(f"Failed to update node {node.name() if node else 'unknown'}: {str(e)}")
                failedCount += 1
        
        # Show result message
        if updatedCount > 0 or failedCount > 0:
            message = f"Updated {updatedCount} nodes"
            if failedCount > 0:
                message += f", {failedCount} failed"

            logger.info(message)
            # self.core.popup(message, severity="info" if failedCount == 0 else "warning")
        
        # Refresh the tree to update status indicators
        self.refreshNodes()
    
    @err_catcher(name=__name__)
    def toggleGroupByShot(self) -> None:
        """Toggle grouping by shot and refresh tree display."""
        self.groupByShot = not self.groupByShot
        self.refreshNodes()
    
    @err_catcher(name=__name__)
    def onSelectionChanged(self) -> None:
        """Handle tree widget selection change - sync with Nuke node selection.
        
        Synchronizes tree selection with Nuke's node graph selection.
        """
        try:
            if self.suspendNukeSelectionSync:
                return

            # Get selected tree items
            selectedItems = self.tree.selectedItems()
            
            # Clear current Nuke selection
            for node in nuke.selectedNodes():
                node.setSelected(False)
            
            # Select corresponding nodes in Nuke
            for item in selectedItems:
                data = item.data(0, Qt.UserRole) or {}
                node = data.get("node") if isinstance(data, dict) else None
                if node and hasattr(node, 'setSelected'):
                    try:
                        node.setSelected(True)
                    except:
                        # Node might have been deleted
                        pass

            self.syncShotContextComboToSelection()
                        
        except Exception as e:
            logger.warning(f"Failed to sync selection: {str(e)}")
    
    @err_catcher(name=__name__)
    def onItemDoubleClicked(self, item: Any, column: int) -> None:
        """Handle double-click on tree item - frame to node in Nuke.
        
        Selects the node and frames it in the node graph.
        
        Args:
            item: The double-clicked tree widget item
            column: The column index that was double-clicked
        """
        try:
            node = item.data(0, Qt.UserRole)["node"]
            if not node or not hasattr(node, 'setSelected'):
                return
                
            # Clear current selection and select only this node
            for n in nuke.selectedNodes():
                n.setSelected(False)
            node.setSelected(True)
            
            # Frame to the node in the node graph
            # This uses Nuke's zoom functionality to frame the selected node
            nuke.zoom(2, [node.xpos(), node.ypos()])
            
        except Exception as e:
            logger.warning(f"Failed to frame to node: {str(e)}")
