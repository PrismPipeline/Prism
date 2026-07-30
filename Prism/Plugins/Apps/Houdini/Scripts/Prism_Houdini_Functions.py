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

"""Houdini plugin core functions for Prism Pipeline.

This module provides the main integration between Prism Pipeline and SideFX Houdini.
Handles scene management, state manager integration, HDA operations, render node management,
environment variable handling, and UI callbacks throughout the Houdini application.

Main responsibilities:
- Scene event callbacks and lifecycle management
- HDA (Houdini Digital Asset) installation and management
- State Manager node integration (ImportFile, Filecache)
- Render node operations and ROP management
- Environment variable synchronization
- UI customization and thumbnail capture
- External file detection and path resolution
"""

import os
import sys
import platform
import glob
import logging
import tempfile
import time
import re
from typing import Any, Optional, List, Dict, Tuple, Union

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

import hou

if eval(os.getenv("PRISM_DEBUG", "False")):
    try:
        del sys.modules["Prism_Houdini_Node_ImportFile"]
    except:
        pass

    try:
        del sys.modules["Prism_Houdini_Node_Filecache"]
    except:
        pass

import Prism_Houdini_Node_Filecache
import Prism_Houdini_Node_ImportFile

from PrismUtils.Decorators import err_catcher as err_catcher


logger = logging.getLogger(__name__)


class Prism_Houdini_Functions(object):
    """Houdini DCC integration functions for Prism Pipeline.
    
    Provides comprehensive integration between Prism and Houdini including scene management,
    node operations, HDA handling, environment setup, and UI customization.
    
    Attributes:
        core: Prism core instance
        plugin: Houdini plugin instance
        eventLoopIterations (int): Counter for GUI initialization
        eventLoopCallbackAdded (bool): Whether event loop callback is registered
        guiReady (bool): Whether GUI is fully initialized
        savingScenePath (Optional[str]): Path currently being saved
        skipPreDeletePopup (bool): Whether to skip deletion confirmation
        assetFormats (List[str]): Supported HDA file extensions
        whiteListedExternalFiles (List[Dict]): External file parameters to ignore
        importHandlerTypes (Dict[str, str]): File extension to import handler mapping
        ropLocation (str): Default ROP node location path
        filecache: Filecache node type API
        importFile: ImportFile node type API
        nodeTypeAPIs (List): All custom node type APIs
        opmenuActions (List[Dict]): Custom operator menu actions
    """
    
    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize Houdini integration functions.
        
        Args:
            core: Prism core instance
            plugin: Houdini plugin instance
        """
        self.core = core
        self.plugin = plugin
        self.eventLoopIterations = 0
        self.eventLoopCallbackAdded = False
        self.guiReady = False
        self.savingScenePath = None
        self.skipPreDeletePopup = False
        self.assetFormats = [
            ".hda",
            ".hdanc",
            ".hdalc",
            ".otl",
            ".otlnc",
            ".otllc",
        ]
        self.whiteListedExternalFiles = [
            {
                "nodeType": "topnet",
                "parmName": "taskgraphfile",
            },
        ]
        self.importHandlerTypes = {}
        for assetFormat in self.assetFormats:
            self.importHandlerTypes[assetFormat] = "Install HDA"

        self.ropLocation = "/out"
        self.filecache = Prism_Houdini_Node_Filecache.Prism_Houdini_Filecache(
            self.plugin
        )
        self.importFile = Prism_Houdini_Node_ImportFile.Prism_Houdini_ImportFile(
            self.plugin
        )
        self.nodeTypeAPIs = [self.filecache, self.importFile]
        self.opmenuActions = [
            {
                "label": "Publish...",
                "validator": lambda x: True,
                "callback": self.onNodePublishTriggered,
            },
            {
                "label": "Capture Thmbnail",
                "validator": lambda x: True,
                "callback": self.onCaptureThumbnailTriggered,
            },
            {
                "label": "Edit Thumbnails",
                "validator": lambda x: True,
                "callback": self.onEditThumbnailsTriggered,
                "checkable": True,
                "checked": lambda kwargs: self.getNetworkPane(node=kwargs["node"].parent()).getPref("backgroundimageediting") == "1"
            }
        ]
        self.registerCallbacks()
        logging.getLogger("whoosh").setLevel(logging.WARNING)

    @err_catcher(name=__name__)
    def registerCallbacks(self) -> None:
        """Register all Prism callback handlers for Houdini events.
        
        Registers callbacks for scene events, project changes, UI dialogs,
        environment updates, and other integration points.
        """
        self.core.registerCallback(
            "sceneSaved", self.updateEnvironment, plugin=self.plugin
        )
        self.core.registerCallback(
            "preSaveScene", self.onPreSaveScene, plugin=self.plugin
        )
        self.core.registerCallback(
            "postSaveScene", self.onPostSaveScene, plugin=self.plugin
        )
        self.core.registerCallback(
            "onProjectSettingsOpen", self.onProjectSettingsOpen, plugin=self.plugin
        )
        self.core.registerCallback(
            "onUserSettingsOpen", self.onUserSettingsOpen, plugin=self.plugin
        )
        self.core.registerCallback(
            "onProjectBrowserStartup", self.onProjectBrowserStartup, plugin=self.plugin
        )
        self.core.registerCallback(
            "preLoadPresetScene", self.preLoadPresetScene, plugin=self.plugin
        )
        self.core.registerCallback(
            "postLoadPresetScene", self.postLoadPresetScene, plugin=self.plugin
        )
        self.core.registerCallback(
            "onStateManagerOpen", self.onStateManagerOpen, plugin=self.plugin
        )
        self.core.registerCallback(
            "onStateManagerShow", self.onStateManagerShow, plugin=self.plugin
        )
        self.core.registerCallback(
            "onProjectChanged", self.onProjectChanged, plugin=self.plugin
        )
        self.core.registerCallback(
            "expandEnvVar", self.expandEnvVar, plugin=self.plugin
        )
        self.core.registerCallback(
            "updatedEnvironmentVars", self.updatedEnvironmentVars, plugin=self.plugin
        )
        self.core.registerCallback("postBuildScene", self.postBuildScene, plugin=self.plugin)

    @err_catcher(name=__name__)
    def onEventLoopCallback(self) -> None:
        """Handle Qt event loop iterations for GUI initialization.
        
        Called repeatedly until GUI is fully ready. After 5 iterations,
        marks GUI as ready and removes itself from event loop.
        """
        self.eventLoopIterations += 1
        if self.eventLoopIterations == 5:
            self.guiReady = True
            hou.ui.removeEventLoopCallback(self.onEventLoopCallback)

    @err_catcher(name=__name__)
    def startup(self, origin: Any) -> Optional[bool]:
        """Initialize Prism integration when Houdini starts.
        
        Sets up parent widgets, message dialogs, Qt application, event callbacks,
        and ensures GUI is ready before completing startup.
        
        Args:
            origin: Prism startup manager instance
            
        Returns:
            False if GUI not ready or unavailable, otherwise None
        """
        if platform.system() == "Darwin":
            QApplication.setAttribute(Qt.AA_DontUseNativeMenuBar)

        if self.core.uiAvailable:
            if not hou.isUIAvailable():
                return False

            if not hou.qt.mainWindow():
                return False

            if not self.eventLoopCallbackAdded:
                self.eventLoopCallbackAdded = True
                hou.ui.addEventLoopCallback(self.onEventLoopCallback)

            if not self.guiReady:
                return False

            if platform.system() == "Darwin":
                origin.messageParent = QWidget()
                origin.messageParent.setParent(hou.qt.mainWindow(), Qt.Window)
                if self.core.useOnTop:
                    origin.messageParent.setWindowFlags(
                        origin.messageParent.windowFlags() ^ Qt.WindowStaysOnTopHint
                    )
            else:
                origin.messageParent = hou.qt.mainWindow()

            origin.timer.stop()
            origin.startAutosaveTimer()
        else:
            QApplication.addLibraryPath(
                os.path.join(hou.text.expandString("$HFS"), "bin", "Qt_plugins")
            )
            qApp = QApplication.instance()
            if qApp is None:
                qApp = QApplication(sys.argv)
            origin.messageParent = QWidget()

        hou.hipFile.addEventCallback(self.sceneEventCallback)

    @err_catcher(name=__name__)
    def sceneEventCallback(self, eventType: Any) -> None:
        """Handle Houdini scene file events.
        
        Responds to scene clear, load, and save events with appropriate Prism callbacks.
        
        Args:
            eventType: hou.hipFileEventType enum value
        """
        if eventType == hou.hipFileEventType.AfterClear:
            self.core.sceneUnload()
        elif eventType == hou.hipFileEventType.AfterLoad:
            if self.core.status != "starting":
                self.core.sceneOpen()
        elif eventType == hou.hipFileEventType.AfterSave:
            self.core.scenefileSaved()

    @err_catcher(name=__name__)
    def autosaveEnabled(self, origin: Any) -> bool:
        """Check if Houdini autosave is enabled.
        
        Args:
            origin: Prism manager instance
            
        Returns:
            True if autosave is enabled, False otherwise
        """
        return hou.hscript("autosave")[0] == "autosave on\n"

    @err_catcher(name=__name__)
    def onProjectChanged(self, origin: Any) -> None:
        """Handle Prism project change event.
        
        Reloads project HDAs and updates environment variables.
        
        Args:
            origin: Prism core instance
        """
        self.loadPrjHDAs(origin)
        self.updateProjectEnvironment()

    @err_catcher(name=__name__)
    def sceneOpen(self, origin: Any) -> None:
        """Handle scene open event.
        
        Updates environment variables when a scene is opened.
        
        Args:
            origin: Prism core instance
        """
        self.updateEnvironment()

    @err_catcher(name=__name__)
    def onPreSaveScene(self, origin: Any, filepath: str, versionUp: bool, comment: str, publish: bool, details: Dict) -> None:
        """Handle pre-save scene event.
        
        Stores the saving path to track save operations.
        
        Args:
            origin: Prism save manager
            filepath: Target save path
            versionUp: Whether version is being incremented
            comment: Save comment
            publish: Whether this is a publish operation
            details: Additional save details
        """
        self.savingScenePath = filepath

    @err_catcher(name=__name__)
    def onPostSaveScene(self, origin: Any, filepath: str, versionUp: bool, comment: str, publish: bool, details: Dict) -> None:
        """Handle post-save scene event.
        
        Clears saving path and updates environment variables.
        
        Args:
            origin: Prism save manager
            filepath: Saved file path
            versionUp: Whether version was incremented
            comment: Save comment
            publish: Whether this was a publish operation
            details: Additional save details
        """
        self.savingScenePath = None
        self.updateEnvironment()

    @err_catcher(name=__name__)
    def updateEnvironment(self) -> None:
        """Update Houdini environment variables from current scene context.
        
        Sets environment variables for current scene, shot, asset, department,
        task, version, framerange, and project paths. Skips updates during
        active save operations.
        """
        fn = self.core.getCurrentFileName()
        if self.savingScenePath and os.path.normpath(fn) == os.path.normpath(self.savingScenePath):
            return

        envvars = {
            "PRISM_SEQUENCE": "",
            "PRISM_SHOT": "",
            "PRISM_ASSET": "",
            "PRISM_ASSETPATH": "",
            "PRISM_DEPARTMENT": "",
            "PRISM_TASK": "",
            "PRISM_USER": "",
            "PRISM_FILE_VERSION": "",
        }

        useEpisodes = self.core.getConfig(
            "globals",
            "useEpisodes",
            config="project",
        ) or False
        if useEpisodes:
            envvars["PRISM_EPISODE"] = ""

        for envvar in envvars:
            envvars[envvar] = hou.hscript("echo $%s" % envvar)

        newenv = {}
        data = self.core.getScenefileData(fn)

        if data.get("type") == "asset":
            if useEpisodes:
                newenv["PRISM_EPISODE"] = ""

            newenv["PRISM_SEQUENCE"] = ""
            newenv["PRISM_SHOT"] = ""
            newenv["PRISM_ASSET"] = os.path.basename(data.get("asset_path", ""))
            newenv["PRISM_ASSETPATH"] = data.get("asset_path", "").replace("\\", "/")
        elif data.get("type") == "shot":
            newenv["PRISM_ASSET"] = ""
            newenv["PRISM_ASSETPATH"] = ""
            if useEpisodes:
                newenv["PRISM_EPISODE"] = data.get("episode", "")

            newenv["PRISM_SEQUENCE"] = data.get("sequence", "")
            newenv["PRISM_SHOT"] = data.get("shot", "")
        else:
            if useEpisodes:
                newenv["PRISM_EPISODE"] = ""

            newenv["PRISM_SEQUENCE"] = ""
            newenv["PRISM_SHOT"] = ""
            newenv["PRISM_ASSET"] = ""
            newenv["PRISM_ASSETPATH"] = ""

        if data.get("type") in ["asset", "shot"]:
            newenv["PRISM_DEPARTMENT"] = data.get("department", "")
            newenv["PRISM_TASK"] = data.get("task", "")
            newenv["PRISM_USER"] = getattr(self.core, "user", "")
            version = data.get("version", "")
            try:
                intVersion = int(version[-self.core.versionPadding:])
            except:
                intVersion = version

            newenv["PRISM_FILE_VERSION"] = intVersion
        else:
            newenv["PRISM_DEPARTMENT"] = ""
            newenv["PRISM_TASK"] = ""
            newenv["PRISM_USER"] = ""
            newenv["PRISM_FILE_VERSION"] = ""

        for var in newenv:
            if newenv[var] != envvars[var]:
                hou.hscript("setenv %s=%s" % (var, newenv[var]))
                hou.hscript("varchange %s" % var)

        self.updateProjectEnvironment()

    @err_catcher(name=__name__)
    def updateProjectEnvironment(self) -> None:
        """Update Houdini project-level environment variables.
        
        Sets PRISM_JOB and PRISM_JOB_LOCAL variables (and deprecated equivalents)
        pointing to current project paths.
        """
        job = getattr(self.core, "projectPath", "").replace("\\", "/")
        if job.endswith("/"):
            job = job[:-1]
        hou.hscript("setenv PRISMJOB=" + job)  # deprecated
        hou.hscript("varchange PRISMJOB")  # deprecated
        hou.hscript("setenv PRISM_JOB=" + job)
        hou.hscript("varchange PRISM_JOB")

        if self.core.useLocalFiles:
            ljob = self.core.localProjectPath.replace("\\", "/")
            if ljob.endswith("/"):
                ljob = ljob[:-1]
        else:
            ljob = ""

        hou.hscript("setenv PRISMJOBLOCAL=" + ljob)  # deprecated
        hou.hscript("varchange PRISMJOBLOCAL")  # deprecated
        hou.hscript("setenv PRISM_JOB_LOCAL=" + ljob)
        hou.hscript("varchange PRISM_JOB_LOCAL")

    @err_catcher(name=__name__)
    def expandEnvVar(self, var: str) -> str:
        """Expand environment variables and Houdini expressions in a string.
        
        Handles backslash escaping and uses Houdini's expandString for variable expansion.
        
        Args:
            var: String containing variables to expand
            
        Returns:
            Expanded string with resolved variables
        """
        if "`" not in var:
            var = var.replace("\\", "\\\\")
            var = hou.text.expandString(var)

        return var

    @err_catcher(name=__name__)
    def updatedEnvironmentVars(self, reason: str, envVars: List[Dict], beforeRefresh: bool = False) -> None:
        """Handle environment variable updates from Prism.
        
        Monitors OCIO variable changes and refreshes Houdini's color management system.
        
        Args:
            reason: Reason for update ("refreshProject", "unloadProject", etc.)
            envVars: List of changed environment variable dicts with "key", "value", "orig"
            beforeRefresh: Whether this is called before refresh operation
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
        """Reload OCIO color management and update viewport settings.
        
        Reloads OCIO configuration from environment and applies default display/view
        to all scene viewer panes.
        """
        hou.Color.reloadOCIO()
        if hou.isUIAvailable():
            try:
                panes = hou.ui.paneTabs()
            except:
                return

            for pane in panes:
                if pane.type() == hou.paneTabType.SceneViewer:
                    display = hou.Color.ocio_defaultDisplay()
                    view = hou.Color.ocio_defaultView()
                    otherViews = [v for v in hou.Color.ocio_activeViews() if v != view]
                    otherView = otherViews[0] if otherViews else view
                    logger.debug("setting OCIO to: display: %s, view: %s" % (display, view))
                    try:
                        pane.setOCIODisplayView(display=display, view=otherView)  # required to force the viewport refresh to show the correct colors
                        pane.setOCIODisplayView(display=display, view=view)
                    except Exception as e:
                        logger.warning("failed to set OCIO DisplayView: %s - %s - %s" % (str(e), display, view))

    @err_catcher(name=__name__)
    def loadPrjHDAs(self, origin: Any) -> None:
        """Load and install project HDAs from project HDA folders.
        
        Searches project HDA folders and user-specific HDA folders, uninstalls
        old definitions, and installs found HDAs to the project oplib.
        
        Args:
            origin: Prism core instance with projectPath and user attributes
        """
        if not hasattr(origin, "projectPath") or not os.path.exists(origin.projectPath):
            return

        self.core.users.ensureUser()
        self.uninstallHDAs(origin.prjHDAs)

        hdaFolders = []

        prjHDAs = self.getProjectHDAFolder()
        if prjHDAs and hasattr(self.core, "user"):
            hdaUFolder = os.path.join(prjHDAs, origin.user)
            hdaFolders += [prjHDAs, hdaUFolder]

        origin.prjHDAs = self.findHDAs(hdaFolders)

        oplib = os.path.join(
            self.core.projects.getPipelineFolder(), "ProjectHDAs.oplib"
        )
        self.installHDAs(origin.prjHDAs, oplib)

    @err_catcher(name=__name__)
    def uninstallHDAs(self, hdaPaths: List[str]) -> None:
        """Uninstall HDA definitions from Houdini session.
        
        Args:
            hdaPaths: List of HDA file paths to uninstall
        """
        for path in hdaPaths:
            if not os.path.exists(path):
                continue

            defs = hou.hda.definitionsInFile(path)
            if len(defs) > 0 and defs[0].isInstalled():
                hou.hda.uninstallFile(path)

    @err_catcher(name=__name__)
    def installHDAs(self, hdaPaths: List[str], oplibPath: str) -> None:
        """Install HDA files to a specific operator library path.
        
        Args:
            hdaPaths: List of HDA file paths to install
            oplibPath: Target operator library path
        """
        oplibPath = oplibPath.replace("\\", "/")
        for path in hdaPaths:
            hou.hda.installFile(path, oplibPath)

    @err_catcher(name=__name__)
    def findHDAs(self, paths: Union[str, List[str]]) -> List[str]:
        """Search directories for HDA files.
        
        Recursively searches for files with HDA extensions, excluding backup folders.
        
        Args:
            paths: Directory path or list of paths to search
            
        Returns:
            List of found HDA file paths
        """
        if self.core.isStr(paths):
            paths = [paths]  # type: ignore[assignment]

        hdas = []

        for path in paths:
            if not os.path.exists(path):
                continue

            for root, folders, files in os.walk(path):
                if os.path.basename(root) == "backup":
                    continue

                for file in files:
                    if os.path.splitext(file)[1] in self.assetFormats:
                        hdaPath = os.path.join(root, file).replace("\\", "/")
                        hdas.append(hdaPath)

        return hdas

    @err_catcher(name=__name__)
    def getProjectHDAFolder(self, filename: Optional[str] = None) -> Optional[str]:
        """Get the project's HDA folder path.
        
        Resolves project structure path for Houdini HDAs. Optionally appends filename.
        
        Args:
            filename: Optional HDA filename to append to folder path
            
        Returns:
            Full path to HDA folder or file, or None if no HDA folder configured
        """
        folder = self.core.projects.getResolvedProjectStructurePath("houdini_HDAs")
        if not folder:
            logger.debug("project has no HDA folder")
            return

        if filename:
            filename = filename.replace(":", "_")
            if not os.path.splitext(filename)[1]:
                filename += ".hda"

            folder = os.path.join(folder, filename)

        return folder

    @err_catcher(name=__name__)
    def createHDA(
        self,
        nodes: Any,
        outputPath: str = "",
        typeName: str = "prism_hda",
        label: Optional[str] = None,
        saveToExistingHDA: bool = False,
        version: Union[int, str, None] = 1,
        blackBox: bool = False,
        allowExternalReferences: bool = False,
        projectHDA: bool = False,
        setDefinitionCurrent: bool = True,
        convertNode: bool = False,
        recipe: bool = False,
    ) -> Union[bool, Any]:
        """Create a new HDA from a node or save to existing HDA definition.
        
        Handles HDA creation, versioning, namespace prefixing, black box conversion,
        and installation into project or custom locations.
        
        Args:
            nodes: Houdini node(s) to convert to HDA
            outputPath: Target HDA file path (generated if empty for projectHDA)
            typeName: HDA type name without namespace
            label: HDA description label
            saveToExistingHDA: Save new definition to existing HDA file
            version: Version number, "increment" for auto-increment, or None for no version
            blackBox: Convert definition to black box (locked)
            allowExternalReferences: Allow external node references in HDA
            projectHDA: Save to project HDA folder
            setDefinitionCurrent: Make new definition current after installation
            convertNode: Change source node type to new HDA type
            recipe: Save a recipe HDA
        Returns:
            Created HDA node, converted node, True on success, or False on cancellation
        """
        namespace = self.core.getConfig(
            "houdini", "assetNamespace", dft="prism", configPath=self.core.prismIni
        )
        if namespace:
            typeName = namespace + "::" + typeName

        if recipe:
            if projectHDA and not outputPath:
                filename = typeName.split("::", 1)[1]
                tempPath = self.getProjectHDAFolder(filename)
                if not tempPath:
                    return False
                outputPath = tempPath
                if os.path.exists(outputPath):
                    msg = (
                        "The HDA file already exists:\n\n%s\n\nDo you want to save a new definition into this file and possibly overwrite an existing definition?"
                        % outputPath
                    )
                    result = self.core.popupQuestion(msg, buttons=["Save", "Cancel"])
                    if result == "Cancel":
                        return False

            return self.createToolRecipeHDA(nodes, outputPath, typeName, label)

        node = nodes[0]
        if node.canCreateDigitalAsset():
            if projectHDA and not outputPath:
                filename = typeName.split("::", 1)[1]
                tempPath = self.getProjectHDAFolder(filename)
                if not tempPath:
                    return False
                outputPath = tempPath
                if os.path.exists(outputPath):
                    msg = (
                        "The HDA file already exists:\n\n%s\n\nDo you want to save a new definition into this file and possibly overwrite an existing definition?"
                        % outputPath
                    )
                    result = self.core.popupQuestion(msg, buttons=["Save", "Cancel"])
                    if result == "Cancel":
                        return False

            if version is not None:
                if version == "increment":
                    version = 1
                typeName += "::" + str(version)

            inputNum = len(node.inputs())

            try:
                hda = node.createDigitalAsset(
                    typeName,
                    hda_file_name=outputPath,
                    description=label,
                    min_num_inputs=inputNum,
                    max_num_inputs=inputNum,
                    ignore_external_references=allowExternalReferences,
                    change_node_type=convertNode,
                )
            except hou.OperationFailed as e:
                msg = e.instanceMessage()
                if msg.startswith("The selected subnet has references to nodes"):
                    msg = (
                        "Canceled HDA creation.\n\n"
                        + msg
                        + '\n\nYou can enable "Allow external references" in the state settings to ignore this warning.'
                    )
                self.core.popup(msg)
                return False

            if blackBox:
                hou.hda.installFile(outputPath, force_use_assets=True)
                defs = hou.hda.definitionsInFile(outputPath)
                definition = [df for df in defs if df.nodeTypeName() == typeName][0]
                self.convertDefinitionToBlackBox(definition)
            else:
                return hda
        else:
            if saveToExistingHDA:
                libFile = node.type().definition().libraryFilePath()
                if version is not None:
                    if version == "increment":
                        highestVersion = self.getHighestHDAVersion(libFile, typeName)
                        version = highestVersion + 1
                    typeName += "::" + str(version)

                self.saveNodeDefinitionToFile(
                    node, libFile, typeName=typeName, label=label, blackBox=blackBox
                )
                if convertNode:
                    node = node.changeNodeType(typeName)

                return node
            else:
                if projectHDA and not outputPath:
                    filename = typeName.split("::", 1)[1]
                    tempPath = self.getProjectHDAFolder(filename)
                    if not tempPath:
                        return False
                    outputPath = tempPath
                    libFile = node.type().definition().libraryFilePath()
                    if version == "increment":
                        highestVersion = self.getHighestHDAVersion(libFile, typeName)
                        version = highestVersion + 1
                else:
                    if version == "increment":
                        version = 1

                if version is not None:
                    typeName += "::" + str(version)

                self.saveNodeDefinitionToFile(
                    node, outputPath, typeName=typeName, label=label, blackBox=blackBox
                )

                if projectHDA:
                    oplib = os.path.join(
                        os.path.dirname(outputPath), "ProjectHDAs.oplib"
                    ).replace("\\", "/")
                    hou.hda.installFile(
                        outputPath, oplib, force_use_assets=setDefinitionCurrent
                    )
                else:
                    hou.hda.installFile(
                        outputPath, force_use_assets=setDefinitionCurrent
                    )

                if convertNode:
                    defs = hou.hda.definitionsInFile(outputPath)
                    changeTypeName = defs[0].nodeTypeName() if defs else typeName
                    try:
                        node.changeNodeType(changeTypeName)
                    except hou.OperationFailed as e:
                        logger.warning("Failed to change node type to %s: %s" % (changeTypeName, e))

        return True
    
    @err_catcher(name=__name__)
    def createToolRecipeHDA(
        self,
        items: Any,
        outputPath: str = "",
        typeName: str = "prism_tool_recipe",
        label: Optional[str] = None,
    ) -> Union[bool, Any]:
        """Create a tool recipe HDA from a list of items.
        
        Similar to createHDA but with specific handling for tool recipes, including
        custom metadata and installation behavior.
        
        Args:
            items: List of items to include in the tool recipe
            outputPath: Target HDA file path (generated if empty for projectHDA)
            typeName: HDA type name without namespace
            label: HDA description label
            
        Returns:
            True on success, or False on cancellation
        """
        nodes = [item for item in items if isinstance(item, hou.Node)]
        if not nodes:
            self.core.popup("No valid nodes found to create tool recipe HDA.")
            return False

        anchor = nodes[0] if len(nodes) > 0 else None
        hou.data.saveToolRecipe(
            name=typeName,
            label=label,
            location=outputPath,
            anchor_node=anchor,
            items=items,
        )
        return True
    
    @err_catcher(name=__name__)
    def saveToolRecipeToPath(self, path: str) -> Union[bool, str]:
        """Save the selected nodes as a tool recipe to the specified path.
        
        Args:
            path: File path to save the tool recipe to
            
        Returns:
            The path to the saved tool recipe HDA if saved successfully, False otherwise
        """
        items = hou.selectedItems()
        if not items:
            self.core.popup("No nodes selected to save as a tool recipe.")
            return False
        
        from PrismUtils import PrismWidgets
        self.nameWin = PrismWidgets.CreateItem(
            startText=items[0].name(),
            showTasks=False,
            core=self.core,
        )
        self.core.parentWindow(self.nameWin)
        self.nameWin.setWindowTitle("Save Tool Recipe")
        self.nameWin.l_item.setText("Label:                   ")
        self.nameWin.buttonBox.buttons()[0].setText("Save")
        self.nameWin.w_type = QWidget()
        self.nameWin.lo_type = QHBoxLayout(self.nameWin.w_type)
        self.nameWin.lo_type.setContentsMargins(9, 0, 9, 0)
        self.nameWin.l_typeLabel = QLabel("Type Name:       ")
        self.nameWin.e_typeName = QLineEdit()
        self.nameWin.e_typeName.setText(items[0].name().replace(" ", "_").lower() + "_recipe")
        self.nameWin.lo_type.addWidget(self.nameWin.l_typeLabel)
        self.nameWin.lo_type.addWidget(self.nameWin.e_typeName)
        self.nameWin.layout().insertWidget(2, self.nameWin.w_type)
        self.nameWin.e_item.selectAll()
        result = self.nameWin.exec_()

        if result != 1:
            return False

        label = self.nameWin.e_item.text()
        typeName = self.nameWin.e_typeName.text()

        if os.path.isdir(path):
            path = os.path.join(path, label + ".hda")

        try:
            self.createToolRecipeHDA(items, path, typeName=typeName, label=label)
            return path
        except Exception as e:
            self.core.popup("Failed to save tool recipe:\n\n%s" % e)
            return False
        
    @err_catcher(name=__name__)
    def loadToolRecipeHDA(self, parentNode: Any, hdaPath: str) -> dict:
        """Load a tool recipe HDA and create nodes under the specified parent node.
        
        Args:
            parentNode: Houdini node to create the tool recipe nodes under
            hdaPath: Path to the HDA file to load
        """
        hou.hda.installFile(hdaPath, force_use_assets=True)
        from hrecipes import storage
        storage.recipeStorage().rescan()

        defs = hou.hda.definitionsInFile(hdaPath)
        if len(defs) > 0:
            if parentNode.childTypeCategory() == hou.objNodeTypeCategory() and defs[0].nodeType().category() == hou.sopNodeTypeCategory():
                typeNameData = defs[0].nodeTypeName().split("::")
                if len(typeNameData) > 2:
                    name = typeNameData[-2] + "_container"
                else:
                    name = typeNameData[-1] + "_container"

                parentNode = parentNode.createNode("geo", name)
            elif parentNode.childTypeCategory() == hou.lopNodeTypeCategory() and defs[0].nodeType().category() == hou.sopNodeTypeCategory():
                typeNameData = defs[0].nodeTypeName().split("::")
                if len(typeNameData) > 2:
                    name = typeNameData[-2] + "_sopcreate"
                else:
                    name = typeNameData[-1] + "_sopcreate"

                sopcreate = parentNode.createNode("sopcreate", name)
                parentNode = sopcreate.node("sopnet/create")

            tname = defs[0].nodeTypeName()
            isToolRecipe = self.isToolRecipe(tname)
            print("isToolRecipe", isToolRecipe, tname)
            if isToolRecipe or True:  # new installed HDAs are sometimes not immediately recognized as tool recipes
                result = hou.data.applyTabToolRecipe(
                    name=tname,
                    parent=parentNode,
                    click_to_place=False,
                    skip_notes=False
                )
                print("applyTabToolRecipe result", result)
                return result
    @err_catcher(name=__name__)
    def isToolRecipe(self, typeName: str) -> bool:
        """Check if HDA type is a tool recipe.
        
        Determines if the given HDA type name corresponds to a tool recipe
        by checking for the "prism_tool_recipe" substring.
        
        Args:
            typeName: HDA type name to check.
            
        Returns:
            True if it's a tool recipe, False otherwise.
        """
        try:
            import recipeutils as ru
        except Exception as e:
            return False

        isToolRecipe = bool(ru.recipeNames(ru.RecipeCategory.tool, name_pattern=typeName))
        return isToolRecipe

    @err_catcher(name=__name__)
    def getHighestHDAVersion(self, libraryFilePath: str, typeName: str) -> int:
        """Find the highest version number of an HDA type in a library file.
        
        Searches all definitions in the library for matching typename and returns
        the highest numeric version found.
        
        Args:
            libraryFilePath: Path to HDA library file
            typeName: Base type name to search for (without version suffix)
            
        Returns:
            Highest version number found, or 0 if none
        """
        definitions = hou.hda.definitionsInFile(libraryFilePath)
        highestVersion = 0
        for definition in definitions:
            name = definition.nodeTypeName()
            basename = name.rsplit("::", 1)[0]
            if basename != typeName:
                continue

            v = name.split("::")[-1]
            if sys.version[0] == "2":
                v = unicode(v)

            if not v.isnumeric():
                continue

            if int(v) > highestVersion:
                highestVersion = int(v)

        return highestVersion

    @err_catcher(name=__name__)
    def saveNodeDefinitionToFile(
        self, node: Any, filepath: str, typeName: Optional[str] = None, label: Optional[str] = None, blackBox: bool = False
    ) -> None:
        """Save a node's HDA definition to a file.
        
        Creates temporary HDA file, saves definition, then copies to target with optional
        type name and label changes. Handles version-specific save parameters.
        
        Args:
            node: Node with HDA definition to save
            filepath: Target file path
            typeName: Optional new type name for definition
            label: Optional new label
            blackBox: Whether to compile as black box
        """
        tmpPath = filepath + "tmp"
        kwargs = {
            "file_name": tmpPath,
            "template_node": node,
            "create_backup": False,
            "compile_contents": blackBox,
            "black_box": blackBox,
        }

        major, minor, patch = hou.applicationVersion()
        noBackup = major <= 16 and minor <= 5 and patch <= 185
        blackBoxChanged = major > 19 or (major == 19 and minor > 0)

        if noBackup:
            kwargs.pop("create_backup")

        if blackBoxChanged:
            kwargs.pop("compile_contents")
            kwargs["black_box"] = blackBox

        node.type().definition().save(**kwargs)

        defs = hou.hda.definitionsInFile(tmpPath)
        defs[0].copyToHDAFile(filepath, new_name=typeName, new_menu_name=label)
        os.remove(tmpPath)

    @err_catcher(name=__name__)
    def convertDefinitionToBlackBox(self, definition: Any) -> None:
        """Convert an HDA definition to black box (compiled/locked).
        
        Saves definition with black box compilation. Handles version-specific parameters.
        
        Args:
            definition: HDA definition to convert
        """
        filepath = definition.libraryFilePath()
        kwargs = {
            "file_name": filepath,
            "create_backup": False,
            "compile_contents": True,
            "black_box": True,
        }

        major, minor, patch = hou.applicationVersion()
        noBackup = major <= 16 and minor <= 5 and patch <= 185
        blackBoxChanged = major > 19 or (major == 19 and minor > 0)

        if noBackup:
            kwargs.pop("create_backup")

        if blackBoxChanged:
            kwargs.pop("compile_contents")
            kwargs["black_box"] = True

        definition.save(**kwargs)

    @err_catcher(name=__name__)
    def getHDAOutputpath(
        self,
        node: Optional[Any] = None,
        task: str = "",
        comment: str = "",
        user: Optional[str] = None,
        version: str = "next",
        location: str = "global",
        saveToExistingHDA: bool = False,
        projectHDA: bool = False,
        entity: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Generate output path for HDA publication.
        
        Determines output path based on save mode (existing HDA, project HDA, or new product).
        Generates versioned paths using Prism's product path structure.
        
        Args:
            node: Source node (required for existing HDA mode)
            task: Task name for HDA
            comment: Version comment
            user: User name for version
            version: Version string or "next" for auto-increment
            location: "global" or "local" for path generation
            saveToExistingHDA: Save to node's existing HDA file
            projectHDA: Save to project HDA folder
            entity: Optional entity dict for product path generation (if not provided, uses current scene data)
            
        Returns:
            Dict with "outputPath", "outputFolder", "version" keys, or None if invalid
        """
        if not entity:
            fileName = self.core.getCurrentFileName()
            entity = self.core.getScenefileData(fileName)

        if node and isinstance(node, hou.Node) and node.type().definition() and saveToExistingHDA:
            outputPath = node.type().definition().libraryFilePath()
            outputFolder = os.path.dirname(outputPath)
        elif node and projectHDA:
            outputPath = self.getProjectHDAFolder(task)
            if not outputPath:
                msg = "The current project has no HDA folder set up in the Project Settings"
                self.core.popup(msg)
                return

            outputFolder = os.path.dirname(outputPath)
            version = None  # type: ignore[assignment]
        else:
            version = version if version != "next" else None  # type: ignore[assignment]

            if "type" not in entity:
                return

            if not task:
                return

            extension = ".hda"
            outputPathData = self.core.products.generateProductPath(
                entity=entity,
                task=task,
                extension=extension,
                framePadding="",
                comment=entity.get("comment", ""),
                version=version,
                location=location,
                returnDetails=True,
            )

            outputPath = outputPathData["path"].replace("\\", "/")
            outputFolder = os.path.dirname(outputPath)
            version = outputPathData["version"]

        result = {
            "outputPath": outputPath.replace("\\", "/"),
            "outputFolder": outputFolder.replace("\\", "/"),
            "version": version,
        }

        return result

    @err_catcher(name=__name__)
    def getCurrentFileName(self, origin: Any, path: bool = True) -> str:
        """Get the current Houdini scene file name.
        
        Args:
            origin: Prism core instance
            path: Return full path if True, basename if False
            
        Returns:
            Scene file path/name, or empty string if untitled
        """
        if path:
            filepath = hou.hipFile.path()
            if os.path.splitext(os.path.basename(filepath))[0] == "untitled":
                return ""

            return filepath
        else:
            return hou.hipFile.basename()

    @err_catcher(name=__name__)
    def getCurrentSceneFiles(self, origin: Any) -> List[str]:
        """Get list of all current scene files.
        
        Args:
            origin: Prism core instance
            
        Returns:
            List containing current scene file path
        """
        return [self.core.getCurrentFileName()]

    @err_catcher(name=__name__)
    def getSceneExtension(self, origin: Any) -> str:
        """Get the default scene file extension for Houdini.
        
        Args:
            origin: Prism core instance
            
        Returns:
            ".hip" extension string
        """
        if str(hou.licenseCategory()) == "licenseCategoryType.Commercial":
            return ".hip"
        elif str(hou.licenseCategory()) == "licenseCategoryType.Indie":
            return ".hiplc"
        else:
            return ".hipnc"

    @err_catcher(name=__name__)
    def saveScene(self, origin: Any, filepath: str, details: Optional[Dict] = None) -> bool:
        """Save current Houdini scene to a file.
        
        Handles .hip and .hipnc extensions, ensures directory exists.
        
        Args:
            origin: Prism core instance
            filepath: Target save path
            details: Optional save details dict
            
        Returns:
            True if the scene was saved successfully, False otherwise
        """
        filepath = filepath.replace("\\", "/")
        saved = False
        while True:
            try:
                saved = hou.hipFile.save(file_name=filepath, save_to_recent_files=True)
                break
            except Exception as e:
                msg = "Failed to save hipfile.\nFilepath:\n\n%s\n\nError: %s" % (filepath, e)
                result = self.core.popupQuestion(msg, buttons=["Retry", "Ignore"], icon=QMessageBox.Warning)
                if result != "Retry":
                    break

        return saved

    @err_catcher(name=__name__)
    def getImportPaths(self, origin: Any) -> Dict[str, str]:
        """Get import path mapping from State Manager.
        
        Args:
            origin: Prism core instance
            
        Returns:
            Dict mapping import names to file paths
        """
        val = hou.node("/obj").userData("PrismImports")

        if val is None:
            return {}

        return val

    @err_catcher(name=__name__)
    def getFrameRange(self, origin: Any) -> List[int]:
        """Get the current scene frame range.
        
        Args:
            origin: Prism core instance
            
        Returns:
            List [startFrame, endFrame] from scene timeline
        """
        startframe = hou.playbar.playbackRange()[0]
        endframe = hou.playbar.playbackRange()[1]

        return [startframe, endframe]

    @err_catcher(name=__name__)
    def getCurrentFrame(self) -> int:
        """Get the current timeline frame.
        
        Returns:
            Current frame number as integer
        """
        currentFrame = hou.frame()
        return currentFrame

    @err_catcher(name=__name__)
    def setFrameRange(self, origin: Any, startFrame: int, endFrame: int, currentFrame: Optional[int] = None) -> None:
        """Set the scene frame range.
        
        Args:
            origin: Prism core instance
            startFrame: Timeline start frame
            endFrame: Timeline end frame
            currentFrame: Optional frame to set as current
        """
        hou.playbar.setFrameRange(int(startFrame), int(endFrame))
        hou.playbar.setPlaybackRange(int(startFrame), int(endFrame))
        currentFrame = currentFrame or int(startFrame)
        hou.setFrame(currentFrame)

    @err_catcher(name=__name__)
    def getFPS(self, origin: Any) -> float:
        """Get the current scene FPS.
        
        Args:
            origin: Prism core instance
            
        Returns:
            Frames per second as float
        """
        return hou.fps()

    @err_catcher(name=__name__)
    def setFPS(self, origin: Any, fps: Union[int, float]) -> None:
        """Set the scene FPS.
        
        Args:
            origin: Prism core instance
            fps: Target frames per second
        """
        frange = self.getFrameRange(origin)
        hou.setFps(fps)
        self.setFrameRange(origin, frange[0], frange[1])

    @err_catcher(name=__name__)
    def getAppVersion(self, origin: Any) -> str:
        """Get the Houdini application version.
        
        Args:
            origin: Prism core instance
            
        Returns:
            Version string
        """
        return hou.applicationVersion()[1:-1]

    @err_catcher(name=__name__)
    def onProjectBrowserStartup(self, origin: Any) -> None:
        """Handle Project Browser startup event.
        
        Loads project HDAs and opens network pane if no UI available.
        
        Args:
            origin: Prism Project Browser instance
        """
        origin.checkColor = "rgb(185, 134, 32)"
        origin.sceneBrowser.lo_entityDetails.setContentsMargins(9, 18, 9, 9)
        origin.sceneBrowser.setStyleSheet(origin.sceneBrowser.styleSheet() + " QToolButton{ border-width: 0px; background-color: transparent} QToolButton::checked{background-color: rgba(200, 200, 200, 100)}")

        ssheet = hou.qt.styleSheet()
        ssheet = ssheet.replace("QScrollArea", "Qdisabled")
        ssheet = ssheet.replace("QAbstractItemView", "QWidget#sceneItems")
        ssheet = ssheet.replace("QListView", "QWidget#sceneItems")

        origin.sceneBrowser.w_scenefileItems.setObjectName("sceneItems")
        origin.sceneBrowser.w_scenefileItems.setStyleSheet(ssheet)

    @err_catcher(name=__name__)
    def preLoadPresetScene(self, origin: Any, filepath: str) -> None:
        """Handle pre-load preset scene event.
        
        Args:
            origin: Prism manager
            filepath: Preset scene path to load
        """
        self.curDesktop = hou.ui.curDesktop()

    @err_catcher(name=__name__)
    def postLoadPresetScene(self, origin: Any, filepath: str) -> None:
        """Handle post-load preset scene event.
        
        Removes /obj context from loaded preset.
        
        Args:
            origin: Prism manager
            filepath: Loaded preset scene path
        """
        if hasattr(self, "curDesktop"):
            self.curDesktop.setAsCurrent()

    @err_catcher(name=__name__)
    def newScene(self, force: bool = False) -> bool:
        """Create a new empty Houdini scene.
        
        Args:
            force: Force new scene without save prompt
            
        Returns:
            True on success
        """
        hou.hipFile.clear()
        return True

    @err_catcher(name=__name__)
    def openScene(self, origin: Any, filepath: str, force: bool = False) -> bool:
        """Open a Houdini scene file.
        
        Args:
            origin: Prism core instance
            filepath: Scene file path to open
            force: Force open without save prompt
            
        Returns:
            True on success
        """
        if (
            not filepath.endswith(".hip")
            and not filepath.endswith(".hipnc")
            and not filepath.endswith(".hiplc")
        ):
            return False

        if hou.hipFile.isLoadingHipFile():
            self.core.popup("Houdini is loading another hipfile currently.\nPlease wait or cancel the hipfile loading and try again.")
            return False

        mods = QApplication.keyboardModifiers()
        if self.core.getConfig("houdini", "openInManual") or mods == Qt.AltModifier:
            hou.setUpdateMode(hou.updateMode.Manual)

        if hou.isUIAvailable():
            import hdefereval
            hdefereval.executeDeferred(lambda: hou.hipFile.load(file_name=filepath))
        else:
            hou.hipFile.load(file_name=filepath)

        return True

    @err_catcher(name=__name__)
    def correctExt(self, origin: Any, lfilepath: str) -> str:
        """Correct scene file extension.
        
        Args:
            origin: Prism core instance
            lfilepath: File path to check
            
        Returns:
            Path with corrected extension
        """
        if str(hou.licenseCategory()) == "licenseCategoryType.Commercial":
            return os.path.splitext(lfilepath)[0] + ".hip"
        elif str(hou.licenseCategory()) == "licenseCategoryType.Indie":
            return os.path.splitext(lfilepath)[0] + ".hiplc"
        else:
            return os.path.splitext(lfilepath)[0] + ".hipnc"

    @err_catcher(name=__name__)
    def onUserSettingsOpen(self, origin: Any) -> None:
        """Handle User Settings dialog open event.
        
        Args:
            origin: User Settings dialog instance
        """
        if self.core.uiAvailable:
            origin.scrollArea.setStyleSheet(
                hou.qt.styleSheet().replace("QLabel", "QScrollArea")
            )

    @err_catcher(name=__name__)
    def onProjectSettingsOpen(self, origin: Any) -> None:
        """Handle Project Settings dialog open event.
        
        Args:
            origin: Project Settings dialog instance
        """
        if self.core.uiAvailable:
            origin.sp_curPfps.setStyleSheet(
                hou.qt.styleSheet().replace("QSpinBox", "QDoubleSpinBox")
            )

    @err_catcher(name=__name__)
    def createProject_startup(self, origin: Any) -> None:
        """Handle Create Project dialog startup.
        
        Args:
            origin: Create Project dialog instance
        """
        if self.core.uiAvailable:
            origin.scrollArea.setStyleSheet(
                hou.qt.styleSheet().replace("QLabel", "QScrollArea")
            )

    @err_catcher(name=__name__)
    def shotgunPublish_startup(self, origin: Any) -> None:
        """Handle ShotGrid Publish dialog startup.
        
        Args:
            origin: ShotGrid Publish dialog instance
        """
        if self.core.uiAvailable:
            origin.te_description.setStyleSheet(
                hou.qt.styleSheet().replace("QTextEdit", "QPlainTextEdit")
            )

    @err_catcher(name=__name__)
    def fixImportPath(self, path: str) -> str:
        """Fix import path format for Houdini.
        
        Replaces percent padding with dollar frame variable and normalizes slashes.
        
        Args:
            path: File path to fix
            
        Returns:
            Fixed path with Houdini frame variable
        """
        if not path:
            return path

        base, ext = self.splitExtension(path)
        pad = self.core.framePadding
        if len(base) > pad and base[-(pad + 1)] != "v":
            try:
                int(base[-pad:])
                return base[:-pad] + "$F" + str(pad) + ext
            except:
                return path

        return path

    @err_catcher(name=__name__)
    def getUseRelativePath(self) -> bool:
        """Check if relative paths should be used.
        
        Returns:
            True if relative paths are enabled in Houdini preferences
        """
        return self.core.getConfig(
            "houdini", "useRelativePaths", dft=False, config="project"
        )

    @err_catcher(name=__name__)
    def getPathRelativeToProject(self, path: str) -> str:
        """Convert absolute path to project-relative path.
        
        Uses $JOB variable if path is within project, otherwise returns absolute path.
        
        Args:
            path: Absolute file path
            
        Returns:
            Relative path with $JOB variable, or absolute path if outside project
        """
        if not path:
            return path

        try:
            if path.startswith("$"):
                path = path.replace("\\", "/")
                pathdata = path.split("/", 1)
                path = "$PRISM_JOB/" + os.path.relpath(hou.text.expandString(pathdata[0]) + "/" + pathdata[1], self.core.projectPath)
            else:
                path = "$PRISM_JOB/" + os.path.relpath(path, self.core.projectPath)
        except ValueError as e:
            logger.warning(str(e) + " - path: %s - start: %s" % (path, self.core.projectPath))

        path = path.replace("\\", "/")
        return path

    @err_catcher(name=__name__)
    def splitExtension(self, path: str) -> List[str]:
        """Split file path into base and extension.
        
        Handles multi-part extensions like .sc.hip.
        
        Args:
            path: File path to split
            
        Returns:
            List [base_path, extension]
        """
        if path.endswith(".bgeo.sc"):
            return [path[: -len(".bgeo.sc")], ".bgeo.sc"]
        else:
            return list(os.path.splitext(path))

    @err_catcher(name=__name__)
    def importImages(self, filepath: Optional[str] = None, mediaBrowser: Optional[Any] = None, parent: Optional[Any] = None) -> None:
        """Import images as backplate or environment light.
        
        Prompts user to choose between backplate or dome light texture import.
        
        Args:
            filepath: Optional path to import (prompts if not provided)
            mediaBrowser: Media Browser instance if called from browser
            parent: Parent widget for dialogs
        """
        if mediaBrowser:
            sourceData = mediaBrowser.compGetImportSource()
            if not sourceData:
                return

            filepath = sourceData[0][0].replace("#"*self.core.framePadding, "$F" + str(self.core.framePadding))
            firstFrame = sourceData[0][1]
            lastFrame = sourceData[0][2]
            parent = parent or mediaBrowser

        if not filepath:
            logger.warning("No filepath provided for importImages")
            return

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
    def importBackplate(self, mediaPath: str) -> None:
        """Import image sequence as camera backplate.
        
        Creates or updates ropnet with background image settings for all cameras.
        
        Args:
            mediaPath: Path to image sequence (may contain frame variables)
        """
        camParms = {
            "cam": "vm_background",
            "vrcam": "vm_background",
            "lopimportcam": "vm_background",
            "camera": "xn__houdinibackgroundimage_xcb",
        }
        cams = [n for n in hou.selectedNodes() if n.type().name().split("::")[0] in camParms]
        if cams:
            cam = cams[0]
        else:
            cam = hou.node("/stage").createNode("camera")
            cam.moveToGoodPosition()

        cam.parm(camParms[cam.type().name().split("::")[0]]).set(mediaPath)
        cam.setDisplayFlag(True)
        if hasattr(cam, "setRenderFlag"):
            cam.setRenderFlag(True)

        desktop = hou.ui.curDesktop()
        sceneViewer = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        viewport = sceneViewer.curViewport()
        if cam.type().name().split("::")[0] == "camera":
            vpcam = cam.parm("primpath").eval()
        else:
            vpcam = cam

        viewport.setCamera(vpcam)
        self.goToNode(cam)

    @err_catcher(name=__name__)
    def importDomeLightTexture(self, mediaPath: str) -> None:
        """Import HDR environment texture for dome light.
        
        Creates or updates Environment Light with texture map.
        
        Args:
            mediaPath: Path to HDR/EXR texture file
        """
        lightParms = {
            "domelight": "xn__inputstexturefile_r3ah",
            "envlight": "env_map",
        }
        lights = [n for n in hou.selectedNodes() if n.type().name().split("::")[0] in lightParms]
        if lights:
            light = lights[0]
        else:
            light = hou.node("/stage").createNode("domelight")
            light.moveToGoodPosition()

        light.parm(lightParms[light.type().name().split("::")[0]]).set(mediaPath)
        light.setDisplayFlag(True)
        if hasattr(light, "setRenderFlag"):
            light.setRenderFlag(True)

        self.goToNode(light)

    @err_catcher(name=__name__)
    def setNodeParm(self, node: Any, parm: str, val: Optional[Any] = None, clear: bool = False, severity: str = "warning") -> bool:
        """Set node parameter value with error handling.
        
        Attempts to set parameter, handling keyframes, expressions, locked parameters,
        and multiparm indexing.
        
        Args:
            node: Target node
            parm: Parameter name to set
            val: Value to set (None to skip)
            clear: Clear existing keyframes and expressions
            severity: Error message severity ("warning", "error", etc.)
            
        Returns:
            True on success, False on failure
        """
        try:
            if clear:
                if node.parm(parm).isLocked():
                    node.parm(parm).lock(False)

                node.parm(parm).deleteAllKeyframes()

            if val is not None:
                node.parm(parm).set(val)
        except Exception as e:
            logger.debug(str(e))
            if not node.parm(parm):
                msg = 'parm doesn\'t exist: "%s" on node "%s"' % (parm, node.path())
                if severity == "warning":
                    logger.warning(msg)
                else:
                    logger.debug(msg)

                return False

            curTake = hou.takes.currentTake()
            if (
                curTake.hasParmTuple(node.parm(parm).tuple())
                or curTake.parent() is None
            ):
                msgString = (
                    "Cannot set this parameter. Probably because it is locked:\n\n%s"
                    % node.parm(parm).path()
                )
                if os.getenv("PRISM_HOUDINI_IGNORE_LOCKED_PARM_WARNING", "0") == "1":
                    action = 0
                else:
                    msg = QMessageBox(
                        QMessageBox.Warning,
                        "Cannot set Parameter",
                        msgString,
                        QMessageBox.Cancel,
                    )
                    msg.addButton("Ignore", QMessageBox.YesRole)
                    self.core.parentWindow(msg)
                    action = msg.exec_()

                if action == 0:
                    return True
                else:
                    return False
            else:
                msgString = (
                    "The parameter is not included in the current take.\nTo continue the parameter should be added to the current take.\n\n%s"
                    % node.parm(parm).path()
                )
                msg = QMessageBox(
                    QMessageBox.Warning,
                    "Locked Parameter",
                    msgString,
                    QMessageBox.Cancel,
                )
                msg.addButton("Add to current take", QMessageBox.YesRole)
                msg.addButton("Ignore", QMessageBox.YesRole)
                self.core.parentWindow(msg)
                action = msg.exec_()

                if action == 0:
                    curTake.addParmTuple(node.parm(parm).tuple())
                    self.setNodeParm(node, parm, val, clear)
                elif action == 1:
                    return True
                else:
                    return False

        return True

    @err_catcher(name=__name__)
    def sm_preDelete(self, origin: Any, item: Any, silent: bool = False) -> None:
        """Handle State Manager state pre-delete event.
        
        Prompts user for confirmation and optionally deletes associated node.
        
        Args:
            origin: State Manager instance
            item: State being deleted
            silent: Skip confirmation dialog
        """
        if not hasattr(item.ui, "node") or silent:
            return

        try:
            item.ui.node.name()
            nodeExists = True
        except:
            nodeExists = False

        if nodeExists:
            if self.skipPreDeletePopup:
                result = "Yes"
            else:
                msg = "Do you also want to delete the connected node?\n\n%s" % (
                    item.ui.node.path()
                )

                buttons = ["Yes", "No"]
                if len(origin.stateManager.getSelectedStates()) > 1:
                    buttons.insert(1, "Yes to all")

                result = self.core.popupQuestion(msg, buttons=buttons, title="Delete State", default="No")

            if result in ["Yes", "Yes to all"]:
                try:
                    if item.ui.className == "ImportFile":
                        nwBox = hou.node("/obj").findNetworkBox("Import")
                        if nwBox is not None:
                            if (
                                len(nwBox.nodes()) == 1
                                and nwBox.nodes()[0] == item.ui.node
                            ):
                                nwBox.destroy()
                    item.ui.node.destroy()
                    if hasattr(item.ui, "node2"):
                        item.ui.node2.destroy()
                except:
                    pass

                if result == "Yes to all":
                    self.skipPreDeletePopup = True
                    origin.stateManager.finishedDeletionCallbacks.append(lambda: setattr(self, "skipPreDeletePopup", False))

        if (
            item.ui.className == "Install HDA"
            and os.path.splitext(item.ui.importPath)[1] == ".hda"
        ):
            fpath = item.ui.importPath.replace("\\", "/")
            defs = hou.hda.definitionsInFile(fpath)
            if len(defs) > 0 and defs[0].isInstalled():
                hou.hda.uninstallFile(fpath)

    @err_catcher(name=__name__)
    def sm_preSaveToScene(self, origin: Any) -> Optional[bool]:
        """Handle State Manager pre-save to scene event.
        
        Creates or updates Prism shelf in Houdini.
        
        Args:
            origin: State Manager instance
            
        Returns:
            False if save cancelled or scene needs reloading, None otherwise
        """
        if origin.scenename == self.core.getCurrentFileName():
            return

        origin.saveEnabled = False

        msg = QMessageBox(
            QMessageBox.NoIcon,
            "State Manager",
            "A problem happened with the scene load callbacks.",
        )
        msg.addButton("Save current states to scene", QMessageBox.YesRole)
        msg.addButton("Reload states from scene", QMessageBox.NoRole)
        msg.addButton("Close", QMessageBox.NoRole)

        msg.setParent(self.core.messageParent, Qt.Window)

        action = msg.exec_()

        origin.scenename = self.core.getCurrentFileName()

        if action == 1:
            self.core.closeSM(restart=True)
            return False
        elif action == 2:
            self.core.closeSM()
            return False

        origin.saveEnabled = True
        return

    def fixStyleSheet(self, widget: Any) -> None:
        """Apply custom checkbox stylesheet to a widget.
        
        Sets custom checkbox indicator images for checked/unchecked states
        using SVG icons from the plugin's UserInterfaces folder.
        
        Args:
            widget: Qt widget to apply stylesheet to.
        """
        if hou.applicationVersion()[0] >= 22:
            return

        root = os.path.dirname(self.pluginPath).replace("\\", "/")
        ssheet = ""
        ssheet += (
            "QGroupBox::indicator::checked\n{\n    image: url(%s/UserInterfaces/checkbox_on.svg);\n}"
            % root
        )
        ssheet += (
            "QGroupBox::indicator::unchecked\n{\n    image: url(%s/UserInterfaces/checkbox_off.svg);\n}"
            % root
        )
        ssheet += "QGroupBox::indicator { width: 16px; height: 16px;}"
        widget.setStyleSheet(ssheet)

    @err_catcher(name=__name__)
    def getFrameStyleSheet(self, origin: Any) -> str:
        """Get frame stylesheet for Prism UI elements.
        
        Args:
            origin: UI widget requesting stylesheet
            
        Returns:
            CSS stylesheet string
        """
        if self.core.uiAvailable:
            return hou.qt.styleSheet().replace("QWidget", "QFrame")
        else:
            return ""

    @err_catcher(name=__name__)
    def onOpmenuActionsTriggered(self, kwargs: Dict) -> None:
        """Handle custom operator menu action trigger.
        
        Executes Prism-registered node context menu actions.
        
        Args:
            kwargs: Houdini callback kwargs with 'node' and 'action_id' keys
        """
        menu = QMenu(self.core.messageParent)
        pos = QCursor.pos()

        for action in self.opmenuActions:
            if not action["validator"](kwargs):
                continue

            mAct = QAction(action["label"], self.core.messageParent)
            if action.get("checkable", False):
                mAct.setCheckable(True)
                mAct.setChecked(action["checked"](kwargs))
                mAct.toggled.connect(lambda x=None, act=action: act["callback"](kwargs))
            else:
                mAct.triggered.connect(lambda x=None, act=action: act["callback"](kwargs))

            menu.addAction(mAct)

        if not menu.isEmpty():
            menu.exec_(pos)

    @err_catcher(name=__name__)
    def removeImage(self, **kwargs: Any) -> None:
        """Remove background image from network editor pane.
        
        Args:
            **kwargs: Houdini callback arguments with 'pane' key
        """
        import nodegraphutils as utils
        nwPane = self.getNetworkPane(node=kwargs["node"].parent())
        curImgs = nwPane.backgroundImages()
        newImgs = ()
        for img in curImgs:
            if img.relativeToPath() != kwargs["node"].path():
                newImgs = newImgs + (img,)
            else:
                try:
                    os.remove(img.path())
                except:
                    pass

        nwPane.setBackgroundImages(newImgs)
        utils.saveBackgroundImages(nwPane.pwd(), newImgs)
        
    @err_catcher(name=__name__)
    def changeBrightness(self, **kwargs: Any) -> None:
        """Adjust network background image brightness.
        
        Args:
            **kwargs: Houdini callback arguments with 'pane' and 'brightness' keys
        """
        import nodegraphutils as utils
        brightness = 0.3 if kwargs["node"].isBypassed() else 1.0
        nwPane = self.getNetworkPane(node=kwargs["node"].parent())
        curImgs = nwPane.backgroundImages()
        for img in curImgs:
            if img.relativeToPath() == kwargs["node"].path():
                img.setBrightness(brightness)
                
        nwPane.setBackgroundImages(curImgs)
        utils.saveBackgroundImages(nwPane.pwd(), curImgs)

    @err_catcher(name=__name__)
    def onCaptureThumbnailTriggered(self, kwargs: Dict) -> None:
        """Capture thumbnail image for node in network editor.
        
        Allows user to select screen area for thumbnail, saves to network_previews folder.
        
        Args:
            kwargs: Houdini callback with 'node' key
        """
        from PrismUtils import ScreenShot
        import hou
        import nodegraphutils as utils

        node = kwargs.get("node", None)
        if not node:
            return

        previewImg = ScreenShot.grabScreenArea(self.core)

        if previewImg:
            hip = os.path.dirname(hou.hipFile.path())
            prvPath = hip + '/network_previews/%s_%s.jpg' % (node.name(), int(time.time()))
            relPath = prvPath.replace(hip, "$HIP")
            if not os.path.exists(os.path.dirname(prvPath)):
                os.makedirs(os.path.dirname(prvPath))
                
            previewImg.save(prvPath, "JPG")

            ratio = previewImg.size().width() / float(previewImg.size().height())

            width = 4.0
            height = width/ratio

            if height > width:
                maxBound = width
                width = width/(height/width)
                height = maxBound

            startX = 1.07
            startY = -0.4

            rect = hou.BoundingRect(startX, startY, startX+width, startY-height)
            img = hou.NetworkImage(relPath, rect)
            img.setRelativeToPath(node.path())
            nwPane = self.getNetworkPane(node=kwargs["node"].parent())
            curImgs = nwPane.backgroundImages()
            newImgs = curImgs + (img,)
            nwPane.setBackgroundImages(newImgs)
            utils.saveBackgroundImages(nwPane.pwd(), newImgs)
            
            node.addEventCallback((hou.nodeEventType.BeingDeleted,), self.removeImage)
            node.addEventCallback((hou.nodeEventType.FlagChanged,), self.changeBrightness)

    @err_catcher(name=__name__)
    def onNodePublishTriggered(self, kwargs: Dict) -> None:
        """Open publish dialog for node.
        
        Creates temporary publish dialog for selected node.
        
        Args:
            kwargs: Houdini callback with 'node' key
        """
        sm = self.core.getStateManager()
        if not sm:
            return

        validTypes = []
        for stateType in sm.stateTypes:
            if not hasattr(sm.stateTypes[stateType], "isConnectableNode"):
                continue

            valid = sm.stateTypes[stateType].isConnectableNode(kwargs["node"])
            if valid:
                validTypes.append(stateType)
        
        if not validTypes:
            msg = "This node type cannot be published by any of the available state types."
            self.core.popup(msg)
            return

        if len(validTypes) > 1:
            msg = "Which statetype do you want to use to publish this node?"
            result = self.core.popupQuestion(msg, buttons=validTypes + ["Cancel"])
            if result in validTypes:
                stateType = result
            else:
                return
        else:
            stateType = validTypes[0]

        state = self.getStateFromNode(kwargs, create=False)
        if not state or state.ui.className != stateType:
            node = kwargs["node"]
            if stateType == "Save HDA":
                node = list(hou.selectedNodes()) or node

            state = sm.createState(stateType, node=node)

        dlg = PublishDialog(self, state)
        dlg.show()

    @err_catcher(name=__name__)
    def onEditThumbnailsTriggered(self, kwargs: Dict) -> None:
        """Toggle background image editing mode.
        
        Args:
            kwargs: Houdini callback with 'node' key
        """
        nwPane = self.getNetworkPane(node=kwargs["node"].parent())
        isEditing = nwPane.getPref("backgroundimageediting") == "1"
        if isEditing:
            nwPane.setPref("backgroundimageediting", "0")
        else:
            nwPane.setPref("backgroundimageediting", "1")

    @err_catcher(name=__name__)
    def onStateManagerShow(self, origin: Any) -> None:
        """Handle State Manager dialog show event.
        
        Args:
            origin: State Manager instance
        """
        if self.core.uiAvailable and hou.applicationVersion()[0] >= 22:
            origin.splitter.setStyleSheet("")

    @err_catcher(name=__name__)
    def onStateManagerOpen(self, origin: Any) -> None:
        """Handle State Manager dialog open event.
        
        Sets up Prism shelf and initializes node APIs.
        
        Args:
            origin: State Manager instance
        """
        if self.core.uiAvailable:
            origin.enabledCol = QBrush(QColor(204, 204, 204))

        if self.core.uiAvailable:
            origin.scrollArea.setStyleSheet(
                hou.qt.styleSheet().replace("QLabel", "QScrollArea")
            )

        origin.f_import.setStyleSheet("QFrame { border: 0px; }")
        origin.f_export.setStyleSheet("QFrame { border: 0px; }")
        if hou.applicationVersion()[0] < 22:
            origin.sa_stateSettings.setStyleSheet("QScrollArea { border: 0px; }")
            origin.b_createExport.setStyleSheet("padding-left: 1px;padding-right: 1px;")
            origin.b_createRender.setStyleSheet("padding-left: 1px;padding-right: 1px;")
            origin.b_createPlayblast.setStyleSheet("padding-left: 1px;padding-right: 1px;")
            origin.b_showImportStates.setStyleSheet("padding-left: 1px;padding-right: 1px;")
            origin.b_showExportStates.setStyleSheet("padding-left: 1px;padding-right: 1px;")

        root = os.path.dirname(self.pluginPath).replace("\\", "/")
        ssheet = ""
        ssheet += (
            "QTreeWidget::indicator::checked\n{\n    image: url(%s/UserInterfaces/checkbox_on.svg);\n}"
            % root
        )
        ssheet += (
            "QTreeWidget::indicator::unchecked\n{\n    image: url(%s/UserInterfaces/checkbox_off.svg);\n}"
            % root
        )
        ssheet += "QTreeWidget::indicator { width: 16px; height: 16px;}"

        origin.tw_export.setStyleSheet(ssheet)

        origin.layout().setContentsMargins(0, 0, 0, 0)
        origin.b_createImport.setMinimumWidth(70 * self.core.uiScaleFactor)
        origin.b_createImport.setMaximumWidth(70 * self.core.uiScaleFactor)
        origin.b_createExport.setMinimumWidth(70 * self.core.uiScaleFactor)
        origin.b_createExport.setMaximumWidth(70 * self.core.uiScaleFactor)
        origin.b_createRender.setMinimumWidth(70 * self.core.uiScaleFactor)
        origin.b_createRender.setMaximumWidth(70 * self.core.uiScaleFactor)
        origin.b_createPlayblast.setMinimumWidth(70 * self.core.uiScaleFactor)
        origin.b_createPlayblast.setMaximumWidth(70 * self.core.uiScaleFactor)
        origin.b_showImportStates.setMinimumWidth(30 * self.core.uiScaleFactor)
        origin.b_showImportStates.setMaximumWidth(30 * self.core.uiScaleFactor)
        origin.b_showExportStates.setMinimumWidth(30 * self.core.uiScaleFactor)
        origin.b_showExportStates.setMaximumWidth(30 * self.core.uiScaleFactor)

        usdType = hou.nodeType(hou.sopNodeTypeCategory(), "pixar::usdrop")
        if usdType is not None and ".usd" not in self.plugin.outputFormats:
            self.plugin.outputFormats.insert(-2, ".usd")
        elif usdType is None and ".usd" in self.plugin.outputFormats:
            self.plugin.outputFormats.pop(self.plugin.outputFormats.index(".usd"))

        rsType = hou.nodeType(hou.sopNodeTypeCategory(), "Redshift_Proxy_Output")
        if rsType is not None and ".rs" not in self.plugin.outputFormats:
            self.plugin.outputFormats.insert(-2, ".rs")
        elif rsType is None and ".rs" in self.plugin.outputFormats:
            self.plugin.outputFormats.pop(self.plugin.outputFormats.index(".rs"))

    @err_catcher(name=__name__)
    def sm_saveStates(self, origin: Any, buf: str) -> None:
        """Save State Manager states to scene.
        
        Args:
            origin: State Manager instance
            buf: Serialized state data
        """
        hou.node("/obj").setUserData("PrismStates", buf)

    @err_catcher(name=__name__)
    def sm_saveImports(self, origin: Any, importPaths: Dict) -> None:
        """Save import paths to scene user data.
        
        Args:
            origin: State Manager instance
            importPaths: Dict mapping import names to file paths
        """
        hou.node("/obj").setUserData("PrismImports", importPaths)

    @err_catcher(name=__name__)
    def sm_readStates(self, origin: Any) -> Optional[str]:
        """Read State Manager states from scene.
        
        Args:
            origin: State Manager instance
            
        Returns:
            Serialized state data string, or None if not found
        """
        stateData = hou.node("/obj").userData("PrismStates")
        if stateData is not None:
            return stateData

    @err_catcher(name=__name__)
    def sm_deleteStates(self, origin: Any) -> None:
        """Delete State Manager states from scene.
        
        Args:
            origin: State Manager instance
        """
        if hou.node("/obj").userData("PrismStates") is not None:
            hou.node("/obj").destroyUserData("PrismStates")

    @err_catcher(name=__name__)
    def sm_getImportHandlerType(self, extension: str) -> Optional[str]:
        """Get import handler type for file extension.
        
        Args:
            extension: File extension
            
        Returns:
            Handler type string or None
        """
        return self.importHandlerTypes.get(extension, "ImportFile")

    @err_catcher(name=__name__)
    def sm_getExternalFiles(self, origin: Any) -> List[List[Any]]:
        """Get list of external files referenced in scene.
        
        Scans all nodes for file parameters, filtering out ignored types and paths.
        
        Args:
            origin: State Manager instance
            
        Returns:
            Two-element list: [file_paths_list, source_parameters_list]
        """
        # 	hou.setFrame(hou.playbar.playbackRange()[0])
        if not os.getenv("PRISM_USE_HOUDINI_FILEREFERENCES"):
            return [[], []]

        whitelist = [
            "$HIP/$OS-bounce.rat",
            "$HIP/$OS-fill.rat",
            "$HIP/$OS-key.rat",
            "$HIP/$OS-rim.rat",
        ]
        expNodes = [
            x.ui.node
            for x in self.core.getStateManager().states
            if x.ui.className in ["Export", "ImageRender"]
            and x.ui.node is not None
            and self.isNodeValid(origin, x.ui.node)
        ]
        houdeps = hou.fileReferences()
        extFiles = []
        extFilesSource = []
        for x in houdeps:
            if "/Redshift/Plugins/Houdini/" in x[1]:
                continue

            if x[0] is None:
                continue

            if x[0].node() in expNodes:
                continue

            if x[0].node().parent() in expNodes and x[0].node().type().name() == "file":
                continue

            if x[1] in whitelist:
                continue

            if not os.path.isabs(hou.text.expandString(x[1])):
                continue

            if os.path.splitext(hou.text.expandString(x[1]))[1] == "":
                continue

            if x[0] is not None and x[0].name() in [
                "RS_outputFileNamePrefix",
                "vm_picture",
            ]:
                continue

            doContinue = False
            for whiteListed in self.whiteListedExternalFiles:
                if (
                    x[0]
                    and x[0].name() == whiteListed["parmName"]
                    and x[0].node().type().name() == whiteListed["nodeType"]
                ):
                    doContinue = True
                    break

            if doContinue:
                continue

            if (
                x[0] is not None
                and x[0].name() in ["filename", "dopoutput", "copoutput", "sopoutput"]
                and x[0].node().type().name()
                in ["rop_alembic", "rop_dop", "rop_comp", "rop_geometry"]
            ):
                continue

            if (
                x[0] is not None
                and x[0].name() in ["filename", "sopoutput"]
                and x[0].node().type().category().name() == "Driver"
                and x[0].node().type().name() in ["geometry", "alembic"]
            ):
                continue

            if (
                x[0] is not None
                and x[0].name()
                in ["default_image_filename", "default_export_nsi_filename"]
                and x[0].node().type().name() in ["3Delight"]
            ):
                continue

            extFiles.append(hou.text.expandString(x[1]).replace("\\", "/"))
            extFilesSource.append(x[0])

        return [extFiles, extFilesSource]

    @err_catcher(name=__name__)
    def onPlayblastMenuClicked(self, showDlg: bool = False) -> None:
        """Handle Playblast menu click.
        
        Args:
            showDlg: True to show the dialog
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

            entity = state.ui.getOutputEntity()
            if entity.get("type") == "asset":
                state.ui.setRangeType("Single Frame")
            elif entity.get("type") == "shot":
                state.ui.setRangeType("Shot")
            else:
                state.ui.setRangeType("Scene")

            if entity.get("task"):
                state.ui.setIdentifier(entity.get("task"))

        if hasattr(self, "dlg_playblast"):
            self.dlg_playblast.showSm = False
            self.dlg_playblast.close()

        self.dlg_playblast = PlayblastDlg(self, state)
        if not showDlg:
            self.dlg_playblast.submit(openOnFail=False)
        else:
            state.ui.w_name.setVisible(False)
            state.ui.gb_previous.setVisible(False)
            self.dlg_playblast.show()

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
    def postBuildScene(self, **kwargs: Any) -> None:
        """Handle post-build scene event.
        
        Applies ABC caches if entity in kwargs.
        
        Args:
            **kwargs: Build scene arguments with optional 'entity' and 'department' keys
        """
        sbData = self.core.getConfig("sceneBuilding", config="project") or {}
        details = kwargs["entity"].copy()
        details["department"] = kwargs["department"]
        details["task"] = kwargs["task"]
        if "houdini_apply_abc_caches" in sbData:
            if self.core.entities.doesContextMatchTaskFilters(sbData["houdini_apply_abc_caches"], details):
                self.applyAbcCaches(kwargs["entity"], kwargs["department"], quiet=True)

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
    def applyAbcCaches(self, entity: Dict, department: str, quiet: bool = False) -> None:
        """Apply ABC cache files to scene.
        
        Searches for ABC cache products and creates import nodes.
        
        Args:
            entity: Entity dict with path and name
            department: Department name for cache search
            quiet: Suppress status messages
        """
        logger.debug("applying abc caches...")
        tags = [x.strip() for x in os.getenv("PRISM_HOUDINI_ANIM_IMPORT_TAGS", "animated").split(",") if x]
        products = self.core.products.getProductsByTags(entity, tags)
        productsToImport = products
        if not productsToImport:
            msg = "No products to import.\n(checking for tags: \"%s\")" % "\", \"".join(tags)
            logger.debug(msg)
            if not quiet:
                self.core.popup(msg)

            return
        
        paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        if paneTab is None:
            return

        curNode = paneTab.pwd()
        curContext = curNode.childTypeCategory().name()
        if curContext == "Sop":
            geo = curNode
        else:
            obj = hou.node("/obj")
            geo = obj.createNode("geo")
            geo.moveToGoodPosition()
            self.goToNode(geo)

        itemsToLayout = []
        filecache = geo.createNode("prism::Filecache::1.0")
        itemsToLayout.append(filecache)
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
            surfTags = [x.strip() for x in os.getenv("PRISM_HOUDINI_STATIC_ASSET_TAGS", "static").split(",") if x]
            assetProducts = self.core.products.getProductsByTags(asset, surfTags)
            if not assetProducts:
                logger.debug("can't get product of source asset: %s, tags: %s" % (asset, surfTags))
                continue

            assetProduct = assetProducts[0]
            assetProductPath = self.core.products.getLatestVersionpathFromProduct(assetProduct["product"], entity=assetProduct)
            if not assetProductPath:
                logger.debug("can't get file of source asset product: %s" % assetProduct)
                continue

            if not assetProductPath.endswith(".hda"):
                logger.debug("source asset product is not in .hda format: %s" % assetProductPath)
                continue

            state = sm.importFile(assetProductPath, settings={"createNodeAfterImport": False})
            static = state.ui.createNode(geo)
            if not static:
                logger.debug("can't create node from asset hda: %s" % assetProductPath)
                continue

            logger.debug("found product: %s" % productPath)
            animCache = geo.createNode("prism::ImportFile::1.0")
            state = self.getStateFromNode({"node": animCache})
            state.ui.setImportPath(productPath)
            state.ui.importObject(objMerge=False)
            attrcopy = static.createOutputNode("attribcopy")
            attrcopy.setInput(1, animCache)
            attrcopy.parm("attribname").set("P")
            attrcopy.setDisplayFlag(True)
            if hasattr(attrcopy, "setRenderFlag"):
                attrcopy.setRenderFlag(True)

            filecache.setInput(0, attrcopy)
            itemsToLayout.append(static)
            itemsToLayout.append(animCache)
            itemsToLayout.append(attrcopy)
            importedProducts.append(productPath)

        geo.layoutChildren(items=itemsToLayout)

        if not importedProducts:
            logger.debug("no products imported: %s" % productsToImport)

    @err_catcher(name=__name__)
    def captureViewportThumbnail(self) -> Optional[QPixmap]:
        """Capture thumbnail from current viewport.
        
        Renders the active scene viewer to a pixmap.
        
        Returns:
            QPixmap image of viewport, or None on failure
        """
        if not hou.isUIAvailable():
            return False

        file = tempfile.NamedTemporaryFile(suffix=".jpg")
        path = file.name
        file.close()
        frame = hou.frame()
        cur_desktop = hou.ui.curDesktop()
        scene = cur_desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if not scene:
            return

        if not scene.isCurrentTab():
            scene.setIsCurrentTab()

        flip_options = scene.flipbookSettings().stash()
        flip_options.outputToMPlay(False)
        flip_options.frameRange((frame, frame))
        flip_options.output(path)
        scene.flipbook(scene.curViewport(), flip_options)
        pm = self.core.media.getPixmapFromPath(path)
        try:
            os.remove(path)
        except:
            pass

        return pm

    @err_catcher(name=__name__)
    def getPreferredStateType(self, category: str) -> Optional[str]:
        """Get preferred state type for category.
        
        Args:
            category: State category
            
        Returns:
            Preferred state type name or None
        """
        if category == "Export":
            if self.core.getStateManager().stateTypes["Save HDA"].canConnectNode():
                msg = 'The selected node can be connected to a "Save HDA" state.\nDo you want to create a "Save HDA" state?'
                result = self.core.popupQuestion(msg, parent=self.core.sm)
                self.core.getStateManager().activateWindow()
                if result == "Yes":
                    return "Save HDA"

            return "Export"
        else:
            return category

    @err_catcher(name=__name__)
    def isNodeValid(self, origin: Any, node: Any) -> bool:
        """Check if node reference is valid.
        
        Args:
            origin: Prism manager
            node: Node to validate
            
        Returns:
            True if node exists and isn't destroyed
        """
        try:
            node.name()
            return True
        except:
            return False

    @err_catcher(name=__name__)
    def isNodeValidFromState(self, state: Any) -> bool:
        """Check if state's node is valid.
        
        Args:
            state: State to check
            
        Returns:
            True if state has valid node
        """
        try:
            return self.isNodeValid(None, state.node)
        except:
            return False

    @err_catcher(name=__name__)
    def goToNode(self, node: Any) -> None:
        """Navigate network editor to node and select it.
        
        Args:
            node: Target node to navigate to
        """
        if not self.isNodeValid(self, node):
            return False

        node.setCurrent(True, clear_all_selected=True)
        paneTab = self.getNetworkPane(node=node.parent())
        if paneTab is not None:
            paneTab.setCurrentNode(node)
            paneTab.homeToSelection()

    @err_catcher(name=__name__)
    def getNetworkPane(self, cursor: bool = True, node: Optional[Any] = None, multiple: bool = False) -> Any:
        """Get network editor pane.
        
        Args:
            cursor: Use pane under cursor if True
            node: Get pane showing this node
            multiple: Return list of all network panes
            
        Returns:
            Network pane, list of panes if multiple=True, or None
        """
        ptype = hou.paneTabType.NetworkEditor
        underCursor = hou.ui.paneTabUnderCursor()
        if underCursor and underCursor.type() == ptype and not multiple:
            if not node or node == underCursor.pwd():
                return underCursor

        if node:
            validTabs = []
            for tab in hou.ui.paneTabs():
                if tab.type() == ptype and tab.pwd() == node:
                    validTabs.append(tab)

            if validTabs:
                if multiple:
                    return validTabs
                else:
                    return validTabs[0]

        if underCursor and underCursor.type() == ptype:
            return underCursor

        paneTab = hou.ui.paneTabOfType(ptype)
        if paneTab and multiple:
            return [paneTab]
        else:
            return paneTab

    @err_catcher(name=__name__)
    def getCamNodes(self, origin: Any, cur: bool = False) -> List[str]:
        """Get list of camera node paths.
        
        Args:
            origin: Prism manager
            cur: Return only current viewport camera
            
        Returns:
            List of camera node path strings
        """
        sceneCams = []
        for node in hou.node("/").allSubChildren():
            if (
                (node.type().name() == "cam" and node.name() != "ipr_camera")
                or node.type().name() == "vrcam"
                or node.type().name() == "lopimportcam"
            ):
                sceneCams.append(node)

        if cur:
            sceneCams = ["Current View"] + sceneCams

        self.core.callback("houdini_getCameraNodes", sceneCams)
        return sceneCams

    @err_catcher(name=__name__)
    def getCamName(self, origin: Any, handle: str) -> str:
        """Get camera display name from handle.
        
        Args:
            origin: Prism manager
            handle: Camera node path
            
        Returns:
            Camera name string
        """
        if handle == "Current View":
            return handle

        if self.core.isStr(handle):
            name = [x.name() for x in self.getCamNodes(origin) if x.name() == handle]
            if not name:
                return "invalid"
            else:
                name = name[0]
        else:
            name = handle.name()

        return name

    @err_catcher(name=__name__)
    def getValidNodeName(self, name: str) -> str:
        """Sanitize string for use as node name.
        
        Replaces invalid characters with underscores.
        
        Args:
            name: Desired node name
            
        Returns:
            Valid node name string
        """
        # valid node name characters: https://www.sidefx.com/docs/houdini/hom/hou/Node.html#methods-from-hou-networkmovableitem
        pattern = r"[^a-zA-Z0-9._-]"
        validName = re.sub(pattern, '_', name)
        return validName

    @err_catcher(name=__name__)
    def sm_createStatePressed(self, origin: Any, stateType: str) -> None:
        """Handle State Manager create state button press.
        
        Args:
            origin: State Manager instance
            stateType: Type of state to create
        """
        stateCategories = []
        if stateType == "Render":
            renderers = self.getRendererPlugins()
            validNodes = [n for n in hou.selectedNodes() if origin.stateTypes["ImageRender"].isConnectableNode(n)]
            if len(validNodes) > 1:
                for node in hou.selectedNodes():
                    curSel = origin.getCurrentItem(origin.activeList)
                    if (
                        origin.activeList == origin.tw_export
                        and curSel is not None
                        and curSel.ui.className == "Folder"
                    ):
                        parent = curSel
                    else:
                        parent = None

                    origin.createState("ImageRender", parent=parent, setActive=True, node=node)

                return

            if len(validNodes) > 0:
                for i in renderers:
                    if validNodes[0].type().name() in i.ropNames:
                        stateData = {"label": "Render", "stateType": "ImageRender"}
                        return stateData

            for renderer in renderers:
                stateCategories.append({"label": "Render (%s)" % renderer.label, "stateType": "ImageRender", "kwargs": {"renderer": renderer.label}})

        return stateCategories

    @err_catcher(name=__name__)
    def getRendererPlugins(self) -> Dict[str, Any]:
        """Get available renderer plugins.
        
        Returns:
            Dict mapping renderer names to plugin modules
        """
        gpath = os.path.dirname(os.path.abspath(__file__)) + "/Prism_Houdini_Renderer_*"
        files = glob.glob(gpath)

        rplugs = []
        for f in files:
            if f.endswith(".pyc"):
                continue

            rname = os.path.splitext(os.path.basename(f))[0]

            if eval(os.getenv("PRISM_DEBUG", "False")):
                try:
                    del sys.modules[rname]
                except:
                    pass

            rplug = __import__(rname)
            if hasattr(rplug, "isActive") and rplug.isActive():
                rplugs.append(rplug)

        return rplugs

    @err_catcher(name=__name__)
    def sm_existExternalAsset(self, origin: Any, asset: Dict) -> bool:
        """Check if external asset file exists.
        
        Args:
            origin: State Manager
            asset: Asset dict with file path
            
        Returns:
            True if asset file exists
        """
        if asset.startswith("op:") and hou.node(asset.replace("\\", "/")) is not None:
            return True

        return False

    @err_catcher(name=__name__)
    def sm_fixWarning(self, origin: Any, asset: Dict, extFiles: List, extFilesSource: List) -> bool:
        """Attempt to fix external file warnings.
        
        Args:
            origin: State Manager
            asset: Asset dict
            extFiles: List of external file paths
            extFilesSource: Source paths for external files
            
        Returns:
            True on success, False if no changes made
        """
        parm = extFilesSource[extFiles.index(asset.replace("\\", "/"))]
        if parm is None:
            parmStr = ""
        else:
            parmStr = "In parameter: %s" % parm.path()

        return parmStr

    @err_catcher(name=__name__)
    def getRenderRopTypes(self) -> List[str]:
        """Get list of valid render ROP node types.
        
        Returns:
            List of ROP type name strings
        """
        types = []
        renderers = self.getRendererPlugins()
        for renderer in renderers:
            types += renderer.ropNames

        return types

    @err_catcher(name=__name__)
    def sm_openStateFromNode(self, origin: Any, menu: Any, stateType: Optional[str] = None, callback: Optional[Any] = None) -> None:
        """Open State Manager from node context menu.
        
        Prompts user to select nodes and creates/opens linked states.
        
        Args:
            origin: State Manager instance
            menu: Qt menu to populate
            stateType: Optional state type filter
            callback: Optional callback after state creation
        """
        nodeMenu = QMenu("From node", origin)

        if not stateType or stateType == "Render":
            renderMenu = QMenu("ImageRender", origin)
            ropTypes = self.getRenderRopTypes()

            renderNodes = []
            for node in hou.node("/").allSubChildren():
                if node.type().name() in ropTypes:
                    renderNodes.append(node)

            for i in origin.states:
                if (
                    i.ui.className == "ImageRender"
                    and self.isNodeValid(None, i.ui.node)
                    and i.ui.node in renderNodes
                ):
                    renderNodes.remove(i.ui.node)

            callback = callback or (lambda node: origin.createState(
                "ImageRender", node=node, setActive=True
            ))

            for node in renderNodes:
                actRender = QAction(node.path(), origin)
                actRender.triggered.connect(
                    lambda y=None, n=node: callback(node=n)
                )
                renderMenu.addAction(actRender)

            if not renderMenu.isEmpty():
                nodeMenu.addMenu(renderMenu)

        if not stateType or stateType == "Export":
            ropMenu = QMenu("Export", origin)
            ropNodes = []
            for node in hou.node("/").allSubChildren():
                if node.type().name() in [
                    "rop_dop",
                    "rop_comp",
                    "rop_geometry",
                    "rop_alembic",
                    "filecache",
                    "pixar::usdrop",
                    "Redshift_Proxy_Output",
                ]:
                    ropNodes.append(node)

                if node.type().category().name() == "Driver" and node.type().name() in [
                    "geometry",
                    "alembic",
                ]:
                    ropNodes.append(node)

            for i in origin.states:
                if (
                    i.ui.className == "Export"
                    and self.isNodeValidFromState(i.ui)
                    and i.ui.node in ropNodes
                ):
                    ropNodes.remove(i.ui.node)

            callback = callback or (lambda node: origin.createState(
                "Export", node=node, setActive=True
            ))

            for node in ropNodes:
                actExport = QAction(node.path(), origin)
                actExport.triggered.connect(
                    lambda y=None, n=node: callback(node=n)
                )
                ropMenu.addAction(actExport)

            if not ropMenu.isEmpty():
                nodeMenu.addMenu(ropMenu)

        if not nodeMenu.isEmpty():
            menu.addMenu(nodeMenu)

    @err_catcher(name=__name__)
    def sm_render_getDeadlineParams(self, origin: Any, dlParams: Dict, homeDir: str) -> Dict:
        """Get Deadline submission parameters for render.
        
        Args:
            origin: Render state
            dlParams: Base Deadline parameters
            homeDir: Deadline home directory
            
        Returns:
            Updated Deadline parameters dict
        """
        dlParams["pluginInfoFile"] = os.path.join(
            homeDir, "temp", "houdini_plugin_info.job"
        )
        dlParams["jobInfoFile"] = os.path.join(
            homeDir, "temp", "houdini_submit_info.job"
        )

        dlParams["jobInfos"]["Plugin"] = "Houdini"
        dlParams["jobInfos"]["Comment"] = (
            "Prism-Submission-Houdini_%s" % origin.className
        )

        if hasattr(origin, "getRenderNode"):
            driver = origin.getRenderNode()
            if driver.isInsideLockedHDA():
                if "OutputDirectory0" in dlParams["jobInfos"]:
                    del dlParams["jobInfos"]["OutputDirectory0"]

                if "OutputFilename0" in dlParams["jobInfos"]:
                    del dlParams["jobInfos"]["OutputFilename0"]
        else:
            driver = origin.node

        dlParams["pluginInfos"]["OutputDriver"] = driver.path()
        dlParams["pluginInfos"]["IgnoreInputs"] = "False"
        dlParams["pluginInfos"]["Version"] = self.getDeadlineHoudiniVersion()

        if hasattr(origin, "chb_resOverride") and origin.chb_resOverride.isChecked():
            dlParams["pluginInfos"]["Width"] = origin.sp_resWidth.value()
            dlParams["pluginInfos"]["Height"] = origin.sp_resHeight.value()

    @err_catcher(name=__name__)
    def getDeadlineHoudiniVersion(self) -> str:
        """Get Houdini version string for Deadline.
        
        Returns:
            Version string in format "major.minor"
        """
        envKey = "PRISM_DEADLINE_HOUDINI_VERSION"
        if envKey in os.environ:
            version = os.environ[envKey]
        elif (
            int(
                self.core.plugins.getRenderfarmPlugin("Deadline")
                .CallDeadlineCommand(["-version"])
                .split(".")[0][1:]
            )
            > 9
        ):
            version = "%s.%s" % (
                hou.applicationVersion()[0],
                hou.applicationVersion()[1],
            )
        else:
            version = hou.applicationVersion()[0]

        return version

    @err_catcher(name=__name__)
    def sm_renderSettings_getCurrentSettings(self, origin: Any, node: Optional[Any] = None, asString: bool = True) -> Union[str, Dict]:
        """Get current render settings from node.
        
        Args:
            origin: Render settings state
            node: Source node (uses origin.nodeType if None)
            asString: Return as JSON string if True
            
        Returns:
            JSON string or dict of render settings
        """
        settings = []
        if not node:
            node = hou.node(origin.e_node.text())

        if not node:
            return ""

        for parm in sorted(node.parms(), key=lambda x: x.name().lower()):
            setting = {}
            if len(parm.keyframes()) == 1:
                setting[parm.name()] = parm.expression() + " [expression]"
            elif parm.parmTemplate().dataType() == hou.parmData.String:
                setting[parm.name()] = parm.unexpandedString()
            else:
                setting[parm.name()] = parm.eval()
            settings.append(setting)

        if not asString:
            return settings

        settingsStr = self.core.writeYaml(data=settings)
        return settingsStr

    @err_catcher(name=__name__)
    def sm_renderSettings_setCurrentSettings(
        self, origin: Any, preset: List[Dict[str, Any]], state: Optional[Any] = None, node: Optional[Any] = None
    ) -> None:
        """Apply render settings preset to a render node.
        
        Sets parameter values from preset dictionary, handling both direct values
        and Houdini expressions (marked with \" [expression]\" suffix).
        
        Args:
            origin: Render settings state.
            preset: List of parameter dictionaries with {parameter: value} pairs.
            state: Optional state with node reference.
            node: Optional direct node reference.
        """
        if not node:
            if state:
                node = hou.node(state.e_node.text())
        if not node:
            return

        for setting in preset:
            parm = node.parm(list(setting.keys())[0])
            if not parm:
                continue

            value = list(setting.values())[0]
            if sys.version[0] == "2":
                isStr = isinstance(value, basestring)
            else:
                isStr = isinstance(value, str)

            if isStr and value.endswith(" [expression]"):
                value = value[: -len(" [expression")]
                parm.setExpression(value)
            else:
                parm.deleteAllKeyframes()
                try:
                    parm.set(value)
                except:
                    pass

    @err_catcher(name=__name__)
    def sm_renderSettings_applyDefaultSettings(self, origin: Any) -> None:
        """Apply default render settings to node.
        
        Args:
            origin: Render settings state
        """
        node = hou.node(origin.e_node.text())
        if not node:
            return

        for parm in node.parms():
            parm.revertToDefaults()

    @err_catcher(name=__name__)
    def sm_renderSettings_startup(self, origin: Any) -> None:
        """Initialize render settings state on startup.
        
        Args:
            origin: Render settings state
        """
        origin.w_node = QWidget()
        origin.lo_node = QHBoxLayout()
        origin.w_node.setLayout(origin.lo_node)
        origin.l_node = QLabel("Node:")
        origin.e_node = QLineEdit()
        origin.e_node.setContextMenuPolicy(Qt.CustomContextMenu)
        origin.e_node.customContextMenuRequested.connect(
            lambda x: self.showNodeContext(origin)
        )
        origin.e_node.editingFinished.connect(origin.stateManager.saveStatesToScene)
        origin.e_node.textChanged.connect(lambda x: origin.updateUi())

        origin.lo_node.addWidget(origin.l_node)
        origin.lo_node.addWidget(origin.e_node)
        if self.core.uiAvailable:
            origin.b_node = hou.qt.NodeChooserButton()
            origin.b_node.nodeSelected.connect(
                lambda x: origin.e_node.setText(x.path())
            )
            origin.b_node.nodeSelected.connect(origin.stateManager.saveStatesToScene)
            origin.lo_node.addWidget(origin.b_node)

        origin.gb_general.layout().insertWidget(0, origin.w_node)

    @err_catcher(name=__name__)
    def sm_renderSettings_loadData(self, origin: Any, data: Dict) -> None:
        """Load render settings from data dict.
        
        Args:
            origin: Render settings state
            data: Settings data dict
        """
        if "node" in data:
            origin.e_node.setText(data["node"])

    @err_catcher(name=__name__)
    def sm_renderSettings_getStateProps(self, origin: Any) -> Dict:
        """Get state properties for render settings.
        
        Args:
            origin: Render settings state
            
        Returns:
            Dict of state properties
        """
        stateProps = {"node": origin.e_node.text()}

        return stateProps

    @err_catcher(name=__name__)
    def sm_renderSettings_addSelected(self, origin: Any) -> None:
        """Add selected node to render settings state.
        
        Args:
            origin: Render settings state
        """
        if len(hou.selectedNodes()) == 0:
            return False

        origin.e_node.setText(hou.selectedNodes()[0].path())

    @err_catcher(name=__name__)
    def sm_renderSettings_preExecute(self, origin: Any) -> None:
        """Execute render settings before render.
        
        Args:
            origin: Render settings state
        """
        warnings = []

        if not hou.node(origin.e_node.text()):
            warnings.append(["Invalid node specified.", "", 2])

        return warnings

    @err_catcher(name=__name__)
    def showNodeContext(self, origin: Any) -> None:
        """Show node in network editor context.
        
        Args:
            origin: State with node reference
        """
        rcMenu = QMenu(origin.stateManager)
        mAct = QAction("Add selected", origin)
        mAct.triggered.connect(lambda: self.sm_renderSettings_addSelected(origin))
        rcMenu.addAction(mAct)

        rcMenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def createRop(self, nodeType: str, parent: Optional[Any] = None) -> Any:
        """Create ROP node in appropriate context.
        
        Args:
            nodeType: ROP node type name
            parent: Optional parent node (uses self.ropLocation if None)
            
        Returns:
            Created ROP node
        """
        parent = parent or hou.node(self.ropLocation)
        node = parent.createNode(nodeType)
        return node

    @err_catcher(name=__name__)
    def getStateFromNode(self, kwargs: Dict, create: bool = True, ignoreTypes: Optional[List] = None) -> Optional[Any]:
        """Get or create Prism state for node.
        
        Args:
            kwargs: Houdini callback with 'node' key
            create: Create new state if none exists
            ignoreTypes: State types to ignore
            
        Returns:
            State instance or None
        """
        sm = self.core.getStateManager()
        if not sm:
            return

        knode = kwargs["node"]

        for state in sm.states:
            node = getattr(state.ui, "node", None)
            if not self.isNodeValid(None, node):
                node = None

            if ignoreTypes and state.ui.className in ignoreTypes:
                continue

            if node and node.path() == knode.path():
                return state

        if getattr(sm, "stateInCreation", None):
            return sm.stateInCreation

        if not create:
            return

        state = self.createStateForNode(kwargs)
        return state

    @err_catcher(name=__name__)
    def showInStateManagerFromNode(self, kwargs: Dict) -> None:
        """Show State Manager and navigate to node's state.
        
        Args:
            kwargs: Houdini callback with 'node' key
        """
        sm = self.core.getStateManager()
        if not sm:
            return

        if not sm.isVisible():
            sm.show()
            QCoreApplication.processEvents()

        sm.activateWindow()
        sm.raise_()
        if sm.isMinimized():
            sm.showNormal()

        state = self.getStateFromNode(kwargs)
        if not state:
            return

        parent = state.parent()
        while parent:
            parent.setExpanded(True)
            parent = parent.parent()

        sm.selectState(state)

    @err_catcher(name=__name__)
    def findNode(self, path: str) -> Optional[Any]:
        """Find node by path string.
        
        Args:
            path: Node path
            
        Returns:
            Node object or None
        """
        for node in hou.node("/").allSubChildren():
            if (
                node.userData("PrismPath") is not None
                and node.userData("PrismPath") == path
            ):
                node.setUserData("PrismPath", node.path())
                return node

        return

    @err_catcher(name=__name__)
    def openInExplorerFromNode(self, kwargs: Dict) -> None:
        """Open file explorer to node's output folder.
        
        Args:
            kwargs: Houdini callback with 'node' key
        """
        path = kwargs["node"].parm("filepath").eval()
        self.core.openFolder(path)

    @err_catcher(name=__name__)
    def onNodeCreated(self, kwargs: Dict) -> None:
        """Handle node creation event.
        
        Args:
            kwargs: Houdini callback with 'node' key
        """
        pass

    @err_catcher(name=__name__)
    def getApiFromNode(self, node: Any) -> Optional[Any]:
        """Get Prism API instance for node type.
        
        Args:
            node: Node to check
            
        Returns:
            Node API instance or None
        """
        for api in self.nodeTypeAPIs:
            validApi = self.isValidNodeApi(node, api)

            if validApi:
                return api

    @err_catcher(name=__name__)
    def onNodeDeleted(self, kwargs: Dict) -> None:
        """Handle node deletion event.
        
        Removes associated Prism states.
        
        Args:
            kwargs: Houdini callback with 'node' key
        """
        if hou.hipFile.isLoadingHipFile() or hou.hipFile.isShuttingDown():
            return

        state = self.getStateFromNode(kwargs, create=False)
        if not state:
            return

        parent = None
        api = self.getApiFromNode(kwargs["node"])
        if api:
            parent = api.getParentFolder(create=False, node=kwargs["node"])

        sm = self.core.getStateManager()
        if not sm:
            return

        sm.deleteState(state, silent=True)
        while parent:
            if parent and parent.childCount() == 0:
                newParent = parent.parent()
                sm.deleteState(parent)
                parent = newParent
            else:
                break

    @err_catcher(name=__name__)
    def isValidNodeApi(self, node: Any, api: Any) -> bool:
        """Check if API instance is valid for node type.
        
        Args:
            node: Node to validate
            api: API instance to check
            
        Returns:
            True if API matches node type
        """
        validApi = False
        typeName = api.getTypeName()
        if isinstance(typeName, list):
            typeNames = typeName
        else:
            typeNames = [typeName]

        for name in typeNames:
            validApi = node.type().name().startswith(name)
            if validApi:
                break

        return validApi

    @err_catcher(name=__name__)
    def createStateForNode(self, kwargs: Dict) -> Optional[Any]:
        """Create Prism state for node.
        
        Args:
            kwargs: Houdini callback with 'node' key
            
        Returns:
            Created state or None
        """
        sm = self.core.getStateManager()

        parent = None
        api = self.getApiFromNode(kwargs["node"])
        if not api:
            return

        parent = api.getParentFolder(create=True, node=kwargs["node"])
        if parent:
            parentExpanded = parent.isExpanded()

        stateType = getattr(api, "getStateTypeForNode", lambda x: api.stateType)(kwargs["node"])
        openBrowser = False if api.listType == "Import" else None
        state = sm.createState(
            stateType,
            node=kwargs["node"],
            setActive=True,
            openProductsBrowser=openBrowser,
            parent=parent,
        )

        if parent:
            parent.setExpanded(parentExpanded)
            for state in sm.getSelectedStates():
                sm.ensureVisibility(state)

        return state

    @err_catcher(name=__name__)
    def detectCacheSequence(self, path: str, subframeStr: Optional[str] = None) -> str:
        """Detect frame sequence pattern in cache path.
        
        Converts numeric sequences to Houdini frame variable format.
        
        Args:
            path: File path potentially containing frame numbers
            subframeStr: Optional subframe string pattern
            
        Returns:
            Path with $F frame variable, or original path if no sequence detected
        """
        folder = os.path.dirname(path)
        fname = os.path.basename(path)
        base, ext = self.splitExtension(fname)
        convertedParts = []
        addedIntF = None
        for idx, part in enumerate(base.split(".")):
            if len(part) == self.core.framePadding:
                part = part.strip("-")
                if sys.version[0] == "2":
                    part = unicode(part)

                if part.isnumeric():
                    part = "$F" + str(self.core.framePadding)
                    addedIntF = idx
            elif subframeStr:
                if len(part) == 3 and addedIntF is not None and addedIntF == (idx - 1):
                    part = part.strip("-")
                    if sys.version[0] == "2":
                        part = unicode(part)

                    if part.isnumeric():
                        part = subframeStr
                        convertedParts = convertedParts[:-1]

            convertedParts.append(part)

        convertedFilename = ".".join(convertedParts) + ext
        convertedPath = os.path.join(folder, convertedFilename).replace("\\", "/")
        return convertedPath

    @err_catcher(name=__name__)
    def handleNetworkDrop(self, fileList: List[str]) -> None:
        """Handle files dropped into network editor.
        
        Args:
            fileList: List of dropped file paths
        """
        return False


class PublishDialog(QDialog):
    """Temporary publish dialog for individual nodes.
    
    Creates a standalone dialog for publishing a single state's output
    without the full State Manager interface.
    
    Attributes:
        plugin: Houdini plugin instance
        state: State to publish
        core: Prism core instance
        showSm: Whether State Manager was visible before opening dialog
    """
    
    def __init__(self, plugin: Any, state: Any) -> None:
        """Initialize publish dialog.
        
        Args:
            plugin: Houdini plugin instance
            state: State to publish from
        """
        super(PublishDialog, self).__init__()
        self.plugin = plugin
        self.state = state
        self.core = self.plugin.core
        self.core.parentWindow(self)
        self.showSm = False
        if self.core.sm.isVisible():
            self.core.sm.setHidden(True)
            self.showSm = True

        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Set up dialog UI with state widget and publish button."""
        self.setWindowTitle("Publish Node - %s" % self.state.ui.node.path())
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.addWidget(self.state.ui)
        if hasattr(self.state.ui, "gb_previous"):
            self.state.ui.gb_previous.setHidden(True)

        self.b_publish = QPushButton("Publish")
        self.lo_main.addWidget(self.b_publish)
        self.b_publish.clicked.connect(self.publish)

    @err_catcher(name=__name__)
    def closeEvent(self, event: Any) -> None:
        """Handle dialog close event.
        
        Restores State Manager visibility and selects current state.
        
        Args:
            event: Qt close event
        """
        if self.state == self.core.sm.getCurrentItem(self.core.sm.activeList):
            self.core.sm.showState()

        if self.showSm:
            self.core.sm.setHidden(False)

        event.accept()

    @err_catcher(name=__name__)
    def publish(self) -> None:
        """Execute publish operation and close dialog."""
        self.hide()
        sm = self.core.getStateManager()
        sm.publish(
            executeState=True,
            states=[self.state],
        )
        self.close()


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
        """Triggers playblast.
        
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