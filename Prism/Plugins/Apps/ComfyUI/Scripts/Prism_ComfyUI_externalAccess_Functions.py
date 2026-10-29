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
# Copyright (C) 2023-2026 Prism Software GmbH
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
import asyncio
import json
import subprocess
import logging
import uuid
import glob
import fnmatch
import shutil
from typing import Any, List


from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


logger = logging.getLogger(__name__)


class Prism_ComfyUI_externalAccess_Functions(object):
    """
    Prism <-> ComfyUI WebSocket Communication
    
    Usage Examples:
    
    # Send commands to ComfyUI:
    self.send_create_node_command("LoadImage", [100, 200], {"image": "my_image.png"})
    self.send_load_image_node_command("render_001.png")  # Convenience method
    self.send_get_workflow_command()
    self.send_load_workflow_command(workflow_dict)
    self.send_execute_workflow_command()
    
    # Receive commands from ComfyUI:
    # Handled in handle_comfyui_command() - override to add custom behavior
    """
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        self.comfyuiInstanceProcess = None
        self.workflow_save_path = None
        self.comfyui_root = ""
        self._has_seen_active_connection = False
        self._shutdown_scheduled = False
        self._initial_connection_timeout_ms = 30000
        self._reconnect_grace_timeout_ms = 15000
        self._initial_connection_timer = None
        self._reconnect_grace_timer = None
        self._context_ready = False
        self._pending_project_browser = False

        extModPath = os.path.join(self.pluginDirectory, "ExternalModules")
        cpModPath = os.path.join(extModPath, "CrossPlatform")
        if cpModPath not in sys.path:
            sys.path.append(cpModPath)

        ssheetPath = os.path.join(
            self.pluginDirectory,
            "UserInterfaces",
            "ComfyUIStyleSheet"
        )
        self.core.registerStyleSheet(ssheetPath)

        if self.core.requestedApp in ["ComfyUI"] and self.core.uiAvailable:
            self.core.registerCallback("postInitialize", self.onContextInitialized, plugin=self.plugin)
            self.ws_server = PrismWebSocketServer(self.core)
            self.ws_server.command_received.connect(self.handle_comfyui_command)
            self.ws_server.connection_state_changed.connect(self.onConnectionStateChanged)
            self.ws_server.start()
            self._startConnectionWatchdogTimers()
            QApplication.instance().aboutToQuit.connect(self.ws_server.stop)

        self.core.registerCallback("pluginLoaded", self.onPluginLoaded, plugin=self.plugin)
        egPlugin = self.core.getPlugin("ExecutionGraph")
        if egPlugin:
            self.onExecutionGraphLoaded(egPlugin)

        self.core.registerCallback("getPresetScenes", self.getPresetScenes, plugin=self.plugin)
        self.core.registerCallback("openPBFileContextMenu", self.openPBFileContextMenu, plugin=self.plugin)

    def onContextInitialized(self):
        QTimer.singleShot(0, self._finishContextStartup)

    def _finishContextStartup(self):
        if self.core.status != "loaded":
            QTimer.singleShot(50, self._finishContextStartup)
            return
        self._context_ready = True
        self.ws_server.send_command({"action": "prism_context_ready", "ready": True})
        if self._pending_project_browser:
            self._pending_project_browser = False
            self.openProjectBrowserWhenReady()

    def openProjectBrowserWhenReady(self):
        if not self._context_ready:
            self._pending_project_browser = True
            return
        browser = getattr(self.core, "pb", None)
        if browser and browser.isVisible():
            if browser.isMinimized():
                browser.showNormal()
            browser.activateWindow()
            browser.raise_()
            return
        self.core.projectBrowser()

    @err_catcher(name=__name__)
    def onPluginLoaded(self, plugin):
        if plugin.pluginName == "ExecutionGraph":
            self.onExecutionGraphLoaded(plugin)

    @err_catcher(name=__name__)
    def onExecutionGraphLoaded(self, plugin):
        nodeDefPath = os.path.join(self.pluginDirectory, "Resources", "ExecutionGraphNodes.json")
        iconPath = os.path.join(self.pluginDirectory, "Resources")
        os.environ["PRISM_EG_ICON_PATHS"] = os.environ.get("PRISM_EG_ICON_PATHS", "") + os.pathsep + iconPath
        plugin.registerNodeDefs(nodeDefPath)

    @err_catcher(name=__name__)
    def getPresetScenes(self, presetScenes: List[Any]) -> None:
        """Add plugin preset scenes to the preset scenes list.
        
        Loads preset .json files from plugin Presets directory and adds them to
        the provided list if PRISM_SHOW_DEFAULT_SCENEFILE_PRESETS is enabled.
        
        Args:
            presetScenes: List to append preset scene dictionaries to
        """
        if os.getenv("PRISM_SHOW_DEFAULT_SCENEFILE_PRESETS", "1") != "1":
            return
        
        presetDir = os.path.join(self.pluginDirectory, "Presets")
        scenes = self.core.entities.getPresetScenesFromFolder(presetDir)
        presetScenes += scenes

    @err_catcher(name=__name__)
    def openPBFileContextMenu(self, origin, menu, filepath):
        if os.path.splitext(filepath)[1].lower() != ".json":
            return

        action = QAction("Run ComfyUI Workflow...", origin)
        action.triggered.connect(lambda: self.openComfyAppWorkflow(filepath, parent=origin))
        menu.insertAction(menu.actions()[0], action)

    @err_catcher(name=__name__)
    def openComfyAppWorkflow(self, filepath, parent=None):
        try:
            self.dlg_comfyAppWorkflow = ComfyAppWorkflowDialog(self, filepath, parent=parent)
        except (OSError, ValueError) as exc:
            self.core.popup("This is not a usable ComfyUI workflow:\n\n%s" % exc)
            return
        self.dlg_comfyAppWorkflow.show()

    @err_catcher(name=__name__)
    def _startConnectionWatchdogTimers(self):
        self._initial_connection_timer = QTimer()
        self._initial_connection_timer.setSingleShot(True)
        self._initial_connection_timer.timeout.connect(self.onInitialConnectionTimeout)
        self._initial_connection_timer.start(self._initial_connection_timeout_ms)

        self._reconnect_grace_timer = QTimer()
        self._reconnect_grace_timer.setSingleShot(True)
        self._reconnect_grace_timer.timeout.connect(self.onReconnectGraceTimeout)

    @err_catcher(name=__name__)
    def _stopTimer(self, timer):
        if timer and timer.isActive():
            timer.stop()

    @err_catcher(name=__name__)
    def onConnectionStateChanged(self, has_clients, client_count):
        logger.info("ComfyUI websocket connection state changed: has_clients=%s, clients=%s", has_clients, client_count)
        if has_clients:
            self._has_seen_active_connection = True
            self._stopTimer(self._initial_connection_timer)
            self._stopTimer(self._reconnect_grace_timer)
            return

        if self._has_seen_active_connection and self._reconnect_grace_timer:
            self._reconnect_grace_timer.start(self._reconnect_grace_timeout_ms)

    @err_catcher(name=__name__)
    def onInitialConnectionTimeout(self):
        if self._has_seen_active_connection:
            return

        self._shutdownDueToMissingConnection(
            "No active ComfyUI websocket connection was established within %s seconds."
            % (self._initial_connection_timeout_ms // 1000)
        )

    @err_catcher(name=__name__)
    def onReconnectGraceTimeout(self):
        self._shutdownDueToMissingConnection(
            "ComfyUI websocket connection was lost and did not reconnect within %s seconds."
            % (self._reconnect_grace_timeout_ms // 1000)
        )

    @err_catcher(name=__name__)
    def _shutdownDueToMissingConnection(self, reason):
        if self._shutdown_scheduled:
            return

        self._shutdown_scheduled = True
        logger.warning(reason)
        self._stopTimer(self._initial_connection_timer)
        self._stopTimer(self._reconnect_grace_timer)

        ws_server = getattr(self, "ws_server", None)
        if ws_server:
            ws_server.stop()

        qapp = QApplication.instance()
        if qapp:
            qapp.quit()
        else:
            os._exit(0)
    
    def handle_comfyui_command(self, data):
        """Handle commands received from ComfyUI"""
        action = data.get("action")
        logger.info(f"Received command from ComfyUI: {data}")
        
        if action == "connectComfyUI":
            comfyuiRoot = data.get("comfyui_root")
            if comfyuiRoot:
                self.comfyui_root = os.path.normpath(comfyuiRoot)

            self.connectToComfyUI()
        elif action == "set_comfyui_root":
            comfyuiRoot = data.get("comfyui_root")
            if comfyuiRoot:
                self.comfyui_root = os.path.normpath(comfyuiRoot)
                logger.info(f"Received ComfyUI root from context connection: {self.comfyui_root}")

        elif action == "open_project_browser":
            self.openProjectBrowserWhenReady()
        elif action == "get_context_status":
            self.ws_server.send_command({"action": "prism_context_ready", "ready": self._context_ready})
        elif action == "open_settings":
            self.core.prismSettings()
        elif action == "save_version":
            self.core.saveScene()
        elif action == "save_with_comment":
            self.core.saveWithComment()
        elif action == "select_entity":
            self.selectEntity(
                node_name=data.get("node_name"),
                node_type=data.get("node_type"),
                node_id=data.get("node_id")
            )
        elif action == "select_version":
            self.selectVersion(
                node_name=data.get("node_name"),
                node_type=data.get("node_type"),
                node_id=data.get("node_id")
            )
        elif action == "capture_canvas":
            self.handleWebSocketResponse(data)
        elif action == "current_workflow_info":
            self.onCurrentWorkflowInfo(data)
        elif action == "get_output_filepath":
            self.getOutputFilepath(data.get("asset"), data.get("episode"), data.get("sequence"), data.get("shot"), data.get("identifier"), data.get("version"), data.get("extension"))
        elif action == "resolve_media_filepath":
            self.resolveMediaFilepath(
                filepath=data.get("filepath"),
                asset=data.get("asset"),
                episode=data.get("episode"),
                sequence=data.get("sequence"),
                shot=data.get("shot"),
                identifier=data.get("identifier"),
                version=data.get("version"),
                aov=data.get("aov"),
                source=data.get("source"),
                requestId=data.get("request_id"),
            )
        elif action == "set_comfyui_root":
            self.setComfyUIRootFolder(data.get("comfyui_root"))

    def _normalizeWsValue(self, value):
        if value is None:
            return ""

        text = str(value).strip()
        if text.lower() in ["none", "null"]:
            return ""

        return text

    def _findVersionForIdentifier(self, identifierData, versionName, location=""):
        locations = None
        normalizedLocation = self._normalizeWsValue(location)
        if normalizedLocation and normalizedLocation.lower() != "all":
            locations = [normalizedLocation]

        versions = self.core.mediaProducts.getVersionsFromIdentifier(identifierData, locations=locations) or []
        if not versions:
            return None

        normalized = self._normalizeWsValue(versionName)
        if not normalized or normalized.lower() in ["latest", "next"]:
            return self.core.mediaProducts.getLatestVersionFromVersions(versions, includeMaster=True)

        if normalized.isdigit():
            normalized = "v%04d" % int(normalized)

        lowered = normalized.lower()
        for version in versions:
            current = str(version.get("version", ""))
            if current == normalized or current.lower() == lowered:
                return version

        return None

    def _pickMediaFileFromVersion(self, versionData, sourceFilter=""):
        files = self.core.mediaProducts.getFilesFromContext(versionData) or []
        files = [os.path.normpath(path) for path in files if path]
        if not files:
            return ""

        sourceFilter = self._normalizeWsValue(sourceFilter).replace("\\", "/")
        if sourceFilter:
            filtered = []
            for path in files:
                normalizedPath = path.replace("\\", "/")
                baseName = os.path.basename(path)
                if fnmatch.fnmatch(baseName, sourceFilter) or fnmatch.fnmatch(normalizedPath, sourceFilter):
                    filtered.append(path)

            if filtered:
                files = filtered

        mediaType = versionData.get("mediaType")
        if mediaType == "2drenders":
            nonPreview = [path for path in files if not path.lower().endswith("preview.jpg")]
            if nonPreview:
                files = nonPreview
        elif mediaType == "playblasts":
            videoExts = [ext.lower() for ext in self.core.media.videoFormats]
            videos = [path for path in files if os.path.splitext(path)[1].lower() in videoExts]
            if videos:
                files = videos

        files = sorted(files)
        firstFile = files[0]
        firstExt = os.path.splitext(firstFile)[1].lower()

        if sourceFilter and any(ch in sourceFilter for ch in ["*", "?", "#", "%"]) and firstExt not in [ext.lower() for ext in self.core.media.videoFormats]:
            if os.path.isabs(sourceFilter):
                return os.path.normpath(sourceFilter)

            return os.path.normpath(os.path.join(os.path.dirname(firstFile), sourceFilter))

        sequencePattern = self.core.media.getSequenceFromFilename(firstFile)
        if sequencePattern != firstFile:
            sequenceFiles = [path for path in files if self.core.media.isFilenameInSequence(path, sequencePattern)]
            if len(sequenceFiles) > 1:
                return os.path.normpath(sequencePattern)

        latestFile = max(files, key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0)
        return latestFile

    def _resolveMediaFilepathFromContext(self, asset, episode, sequence, shot, identifier, version, aov, source):
        asset = self._normalizeWsValue(asset)
        episode = self._normalizeWsValue(episode)
        sequence = self._normalizeWsValue(sequence)
        shot = self._normalizeWsValue(shot)
        identifier = self._normalizeWsValue(identifier)
        aov = self._normalizeWsValue(aov)
        source = self._normalizeWsValue(source)
        location = "global"

        if not identifier:
            return "", "Missing identifier for media filepath resolution."

        if asset:
            entity = {
                "type": "asset",
                "asset_path": asset,
                "asset": os.path.basename(asset),
            }
        else:
            if not sequence or not shot:
                return "", "Missing shot context. Provide asset or sequence+shot."

            entity = {
                "type": "shot",
                "sequence": sequence,
                "shot": shot,
            }
            if episode:
                entity["episode"] = episode

        mediaTypes = ["2drenders", "playblasts", "3drenders"]
        for curMediaType in mediaTypes:
            identifierData = entity.copy()
            identifierData["identifier"] = identifier
            identifierData["mediaType"] = curMediaType
            if curMediaType == "3drenders" and aov:
                identifierData["aov"] = aov

            versionData = self._findVersionForIdentifier(identifierData, version, location=location)
            if not versionData:
                continue

            if curMediaType == "3drenders":
                if aov:
                    versionData = versionData.copy()
                    versionData["aov"] = aov
                elif "aov" not in versionData:
                    aovs = self.core.mediaProducts.getAOVsFromVersion(versionData) or []
                    if aovs:
                        versionData = aovs[0]

            selectedPath = self._pickMediaFileFromVersion(versionData, sourceFilter=source)
            if selectedPath:
                return selectedPath, ""

        return "", "No media filepath could be resolved from the provided context."

    def resolveMediaFilepath(self, filepath=None, asset=None, episode=None, sequence=None, shot=None, identifier=None,
                             version=None, aov=None, source=None, requestId=None):
        filepath = self._normalizeWsValue(filepath)
        expandedPath = ""
        if filepath:
            expandedPath = os.path.normpath(os.path.expandvars(os.path.expanduser(filepath)))

        response = {
            "action": "resolve_media_filepath",
            "request_id": requestId,
        }

        if expandedPath:
            response.update({
                "status": "success",
                "filepath": expandedPath,
            })
            self.ws_server.send_command(response)
            return

        resolvedPath, error = self._resolveMediaFilepathFromContext(
            asset=asset,
            episode=episode,
            sequence=sequence,
            shot=shot,
            identifier=identifier,
            version=version,
            aov=aov,
            source=source,
        )

        if resolvedPath:
            response.update({
                "status": "success",
                "filepath": os.path.normpath(resolvedPath),
            })
        else:
            response.update({
                "status": "error",
                "message": error,
            })

        self.ws_server.send_command(response)

    def selectEntity(self, node_name=None, node_type=None, node_id=None):
        """Handle entity selection from ComfyUI node"""
        if hasattr(self, "dlg_entity") and self.dlg_entity.isVisible():
            self.dlg_entity.close()

        self.dlg_entity = self.core.entities.entityDlg(self)
        self.dlg_entity.entitySelected.connect(lambda entity: self.onEntitiesSelected(entity, node_id))
        self.dlg_entity.show()

    def onEntitiesSelected(self, entity, node_id):
        asset = entity.get("asset_path")
        episode = entity.get("episode") or ""
        sequence = entity.get("sequence")
        shot = entity.get("shot")
        self.ws_server.send_command({
            "action": "set_node_inputs",
            "node_id": node_id,
            "inputs": {
                "asset": asset,
                "episode": episode,
                "sequence": sequence,
                "shot": shot,
            }
        })

    def selectVersion(self, node_name=None, node_type=None, node_id=None):
        if hasattr(self, "dlg_mediaVersion") and self.dlg_mediaVersion.isVisible():
            self.dlg_mediaVersion.close()

        self.dlg_mediaVersion = ComfyReadMediaDialog(self)
        self.dlg_mediaVersion.mediaSelected.connect(lambda data: self.onVersionSelected(data, node_id))
        self.dlg_mediaVersion.show()

    def _getIdentifierFromMediaData(self, mediaData):
        identifier = mediaData.get("identifier") or ""
        if identifier:
            return identifier

        displayName = mediaData.get("displayName") or ""
        if " (" in displayName and displayName.endswith(")"):
            displayName = displayName.rsplit(" (", 1)[0]

        return displayName

    def _getMediaPathFromSelection(self, mediaData):
        mediaFiles = self.core.mediaProducts.getFilesFromContext(mediaData) or []
        validFiles = self.core.media.filterValidMediaFiles(mediaFiles)

        if not validFiles and mediaData.get("path"):
            validFiles = self.core.media.getFilesFromSequence(mediaData.get("path"))

        if not validFiles:
            return ""

        validFiles = sorted(
            validFiles,
            key=lambda x: x if "cryptomatte" not in os.path.basename(x) else "zzz" + x,
        )
        seqFiles = self.core.media.detectSequences(validFiles)
        if seqFiles:
            return os.path.normpath(list(seqFiles)[0])

        return os.path.normpath(validFiles[0])

    def onVersionSelected(self, mediaData, node_id):
        if not mediaData:
            return

        filepath = self._getMediaPathFromSelection(mediaData)
        if not filepath:
            self.core.popup("Could not resolve a media filepath from the selected version.")
            return

        asset = mediaData.get("asset_path") or ""
        episode = mediaData.get("episode") or ""
        sequence = mediaData.get("sequence") or ""
        shot = mediaData.get("shot") or ""
        identifier = self._getIdentifierFromMediaData(mediaData)
        version = mediaData.get("version") or "latest"
        aov = mediaData.get("aov") or ""
        source = mediaData.get("source") or os.path.basename(filepath)

        self.ws_server.send_command({
            "action": "set_node_inputs",
            "node_id": node_id,
            "inputs": {
                "filepath": filepath,
                "asset": asset,
                "episode": episode,
                "sequence": sequence,
                "shot": shot,
                "identifier": identifier,
                "version": version,
                "aov": aov,
                "source": source,
            },
        })

    def getOutputFilepath(self, asset, episode, sequence, shot, identifier, version, extension):
        # ComfyUI STRING widgets coerce null/None to the string "None"
        if asset == "None":
            asset = None
        if episode == "None":
            episode = None
        if sequence == "None":
            sequence = None
        if shot == "None":
            shot = None

        if asset:
            entity = {"type": "asset", "asset_path": asset, "asset": os.path.basename(asset)}
        else:
            entity = {"type": "shot", "sequence": sequence, "shot": shot}
            if episode:
                entity["episode"] = episode

        comment = ""
        version = version or "next"
        location = "global"
        outputPathData = self.core.mediaProducts.generateMediaProductPath(
            entity=entity,
            task=identifier,
            extension=extension,
            comment=comment,
            framePadding="",
            version=version if version != "next" else None,
            location=location,
            returnDetails=True,
            mediaType="2drenders",
        )

        filepath = outputPathData["path"]
        outputFolder = os.path.dirname(outputPathData["path"])
        hVersion = outputPathData["version"]

        if not os.path.exists(outputFolder):
            os.makedirs(outputFolder)

        details = entity.copy()
        if "filename" in details:
            del details["filename"]

        if "extension" in details:
            del details["extension"]

        details["version"] = hVersion
        details["sourceScene"] = ""
        details["identifier"] = identifier

        self.core.saveVersionInfo(
            filepath=outputFolder,
            details=details,
        )

        command = {
            "status": "success",
            "filepath": filepath
        }
        self.ws_server.send_command(command)

        # Track pre-save state so we can detect both single files and numbered sequences.
        existing_file_mtime = os.path.getmtime(filepath) if os.path.exists(filepath) else None
        sequence_pattern = None
        existing_sequence_mtimes = {}
        base_root, base_ext = os.path.splitext(filepath)
        if base_ext:
            sequence_pattern = f"{base_root}_*{base_ext}"
            for sequence_path in glob.glob(sequence_pattern):
                try:
                    existing_sequence_mtimes[sequence_path] = os.path.getmtime(sequence_path)
                except OSError:
                    pass

        saved_path = None
        saved_sequence_files = []

        for _ in range(5):
            if os.path.exists(filepath):
                try:
                    current_mtime = os.path.getmtime(filepath)
                    if existing_file_mtime is None or current_mtime != existing_file_mtime:
                        saved_path = filepath
                        break
                except OSError:
                    pass

            if sequence_pattern:
                current_sequence_files = sorted(glob.glob(sequence_pattern))
                changed_sequence_files = []
                for sequence_path in current_sequence_files:
                    try:
                        current_mtime = os.path.getmtime(sequence_path)
                    except OSError:
                        continue

                    previous_mtime = existing_sequence_mtimes.get(sequence_path)
                    if previous_mtime is None or current_mtime != previous_mtime:
                        changed_sequence_files.append(sequence_path)

                if changed_sequence_files:
                    saved_sequence_files = changed_sequence_files
                    break

            QThread.sleep(1)

        # Backward-compatible fallback: if the expected file or sequence exists, treat save as successful.
        if not saved_path and not saved_sequence_files:
            if os.path.exists(filepath):
                saved_path = filepath
            elif sequence_pattern:
                saved_sequence_files = sorted(glob.glob(sequence_pattern))

        if saved_path or saved_sequence_files:
            if saved_sequence_files:
                msg = "Saved output successfully.\nDetected %d sequence files." % len(saved_sequence_files)
            else:
                msg = "Saved output successfully."

            result = self.core.popupQuestion(msg, buttons=["Open in Project Browser", "Open in Explorer", "Close"], icon=QMessageBox.Information)
            if result == "Open in Project Browser":
                pb = self.core.projectBrowser()
                pb.showTab("Media")
                pb.mediaBrowser.showRender(entity, identifier + " (2d)")
            elif result == "Open in Explorer":
                if saved_sequence_files:
                    self.core.openFolder(outputFolder)
                else:
                    self.core.openFolder(saved_path)

        else:
            msg = "Saving output failed. The expected mediafile doesn't exist:\n\n%s" % filepath
            self.core.popup(msg)

    def send_create_node_command(self, node_type, position=None, widget_values=None):
        """
        Send command to ComfyUI to create a node with optional widget values
        
        Args:
            node_type: String name of the node type (e.g., "LoadImage", "KSampler")
            position: [x, y] list for node position, or None to center
            widget_values: Dict of widget_name: value pairs to set on the node
                          e.g., {"image": "example.png"} for LoadImage
        
        Example:
            # Create LoadImage node with specific image
            self.send_create_node_command(
                "LoadImage", 
                [100, 200], 
                {"image": "my_image.png"}
            )
        """
        command = {
            "action": "create_node",
            "node_type": node_type,
            "position": position
        }
        if widget_values:
            command["widget_values"] = widget_values
        self.ws_server.send_command(command)
    
    def send_get_workflow_command(self):
        """Request current workflow from ComfyUI"""
        command = {"action": "get_workflow"}
        self.ws_server.send_command(command)
    
    def send_load_workflow_command(self, workflow):
        """Send workflow data to ComfyUI to load"""
        command = {
            "action": "load_workflow",
            "workflow": workflow
        }
        self.ws_server.send_command(command)

    def send_load_image_node_command(self, image_filename, position=None):
        """
        Convenience method to create a LoadImage node with a specific image
        
        Args:
            image_filename: Just the filename (e.g., "my_image.png")
                          The file must exist in ComfyUI's input directory
            position: [x, y] list for node position, or None to center
        
        Example:
            self.send_load_image_node_command("render_001.png", [100, 200])
        """
        self.send_create_node_command(
            "LoadImage",
            position,
            {"image": image_filename}
        )
    
    # Example workflow save/load methods
    def save_workflow_to_file(self, filepath):
        """
        Example: Request workflow from ComfyUI and save to file
        Note: The actual workflow will be received in handle_comfyui_command
        """
        self.workflow_save_path = filepath
        self.send_get_workflow_command()
    
    def load_workflow_from_file(self, filepath):
        """Example: Load workflow from file and send to ComfyUI"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                workflow = json.load(f)
            self.send_load_workflow_command(workflow)
            logger.info(f"Loaded and sent workflow from: {filepath}")
        except Exception as e:
            logger.error(f"Failed to load workflow from {filepath}: {e}")

    @err_catcher(name=__name__)
    def connectToComfyUI(self):
        # Check if existing instance is still running
        if self.comfyuiInstanceProcess is not None:
            if self.comfyuiInstanceProcess.poll() is None:
                # Process is still running
                logger.info(f"ComfyUI instance already running (PID: {self.comfyuiInstanceProcess.pid})")
                return
            else:
                # Process has terminated
                logger.info("Previous ComfyUI instance has terminated, starting new one")
                self.comfyuiInstanceProcess = None
        
        pythonPath = self.core.getPythonPath(executable="pythonw" if self.core.debugMode else "python")
        plugin = self.core.getPlugin("ComfyUI")
        menuPath = os.path.join(plugin.pluginPath, "Prism_ComfyUI_MenuTools.py")
        args = [pythonPath, menuPath, self.core.prismRoot]
        logger.debug("starting Prism instance for ComfyUI: " + str(args))
        if platform.system() == "Windows":
            self.comfyuiInstanceProcess = subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            self.comfyuiInstanceProcess = subprocess.Popen(args)

        logger.info(f"Started ComfyUI instance with PID: {self.comfyuiInstanceProcess.pid}")

    @err_catcher(name=__name__)
    def submitGraphToLocal(self, path=None, workflow=None, inputs=None, waitForCompletion=False, output_dir=None, server_address=None, api_key=None, workflow_id=None):
        import uuid
        from websockets.sync.client import connect

        # Load workflow from file if not provided directly
        if workflow is None:
            if path is None:
                msg = "submitGraphToLocal: either 'path' or 'workflow' must be provided"
                logger.error(msg)
                return {"error": msg}
            with open(path, "r", encoding="utf-8") as f:
                workflow = json.load(f)

        app_mode_output_node_ids = self._get_app_mode_output_node_ids(workflow)
        try:
            workflow = self._get_api_workflow(workflow)
        except ValueError as e:
            msg = "submitGraphToLocal: %s" % e
            logger.error(msg)
            return {"error": msg}

        server_address = server_address or self._get_local_server_address()
        api_key = api_key or self._get_comfy_api_key()

        load3d_result = self._prepare_missing_load3d_inputs(
            workflow, server_address
        )
        if load3d_result.get("error"):
            return load3d_result

        # Apply input overrides: {node_id: {input_name: value}, ...}
        if inputs:
            prepared_inputs = self._prepare_local_inputs(
                workflow, inputs, server_address
            )
            if prepared_inputs.get("error"):
                return prepared_inputs
            self._apply_workflow_inputs(workflow, prepared_inputs)

        client_id = str(uuid.uuid4())
        should_wait = waitForCompletion or (output_dir is not None)

        # Connect the WebSocket BEFORE queuing so we never miss a fast completion message
        ws = None
        if should_wait:
            ws = connect(f"ws://{server_address}/ws?clientId={client_id}")

        try:
            # Queue the prompt
            queue_result = self._queue_local_prompt(
                workflow,
                server_address,
                client_id,
                api_key=api_key,
                workflow_id=workflow_id,
            )
            prompt_id = queue_result.get("prompt_id")
            if not prompt_id:
                msg = "submitGraphToLocal: failed to queue prompt: %s" % queue_result
                logger.error(msg)
                return {"error": msg}

            logger.info(f"submitGraphToLocal: prompt queued, prompt_id={prompt_id}")

            if not should_wait:
                return {"prompt_id": prompt_id, "status": "queued"}

            # Wait for execution to finish using the already-connected WebSocket
            completion = self._wait_local_completion(prompt_id, ws)
            if completion["status"] != "success":
                result = {
                    "prompt_id": prompt_id,
                    "status": "failed",
                    "error": completion["error"],
                    "comfyui_response": completion["response"],
                }
                logger.error("submitGraphToLocal: prompt %s failed: %s", prompt_id, completion["error"])
                return result

            logger.info(f"submitGraphToLocal: prompt {prompt_id} completed")
        finally:
            if ws is not None:
                ws.close()

        result = {"prompt_id": prompt_id, "status": "completed"}

        if output_dir:
            outputs = self._get_local_history(prompt_id, server_address)
            logger.debug("submitGraphToLocal: ComfyUI output nodes for %s: %s", prompt_id, list(outputs))
            downloaded = self._download_local_outputs(
                outputs,
                output_dir,
                server_address,
                app_mode_output_node_ids=app_mode_output_node_ids,
            )
            result["downloaded_files"] = downloaded

        # self._delete_local_history(prompt_id, server_address)
        self._reset_local_cache(server_address)

        return result

    def _get_app_mode_output_node_ids(self, workflow):
        if not isinstance(workflow, dict):
            return set()

        linear_data = (workflow.get("extra") or {}).get("linearData") or {}
        output_nodes = linear_data.get("outputs") or []
        output_node_ids = set()
        for output_node in output_nodes:
            if isinstance(output_node, dict):
                output_node = output_node.get("node_id") or output_node.get("id")
            if output_node is not None:
                output_node_ids.add(str(output_node))
        return output_node_ids

    def _get_local_server_address(self):
        """Return local server address from Prism user config (default: 127.0.0.1:8188)."""
        return (
            self.core.getConfig("comfyui", "localServerAddress", config="user")
            or "127.0.0.1:8188"
        )

    def _get_api_workflow(self, workflow):
        """Return an API-format prompt, converting a ComfyUI save-format workflow when needed."""
        if not isinstance(workflow, dict):
            raise ValueError("workflow must be a JSON object.")

        if "nodes" not in workflow:
            if all(isinstance(node, dict) and "class_type" in node for node in workflow.values()):
                return workflow
            raise ValueError("workflow is neither ComfyUI API format nor save format.")

        nodes = workflow.get("nodes")
        if not isinstance(nodes, list):
            raise ValueError("save-format workflow has no node list.")

        link_sources = {}
        for link in workflow.get("links") or []:
            if isinstance(link, dict):
                link_id = link.get("id")
                source_node = link.get("origin_id")
                source_slot = link.get("origin_slot")
            elif isinstance(link, (list, tuple)) and len(link) >= 3:
                link_id, source_node, source_slot = link[:3]
            else:
                continue

            if link_id is not None and source_node is not None and source_slot is not None:
                link_sources[link_id] = [str(source_node), source_slot]

        api_workflow = {}
        for node in nodes:
            node_id = node.get("id")
            class_type = node.get("type")
            if node_id is None or not class_type:
                raise ValueError("save-format workflow contains a node without an ID or type.")

            named_values = node.get("widgets_values_named") or {}
            positional_values = iter(node.get("widgets_values") or [])
            api_inputs = {}
            for input_data in node.get("inputs") or []:
                input_name = input_data.get("name")
                if not input_name:
                    continue

                link_id = input_data.get("link")
                if link_id is not None:
                    source = link_sources.get(link_id)
                    if source is None:
                        raise ValueError(
                            "save-format workflow has an unresolved link %s on node %s."
                            % (link_id, node_id)
                        )
                    api_inputs[input_name] = source
                    continue

                widget = input_data.get("widget")
                widget_name = widget.get("name") if isinstance(widget, dict) else input_name if widget else None
                if not widget_name:
                    continue

                if widget_name in named_values:
                    value = named_values[widget_name]
                else:
                    try:
                        value = next(positional_values)
                    except StopIteration:
                        continue

                # Load3D's empty editor placeholder is not valid API input.
                if input_data.get("type") == "LOAD_3D" and value in (None, ""):
                    continue

                api_inputs[input_name] = value

            api_workflow[str(node_id)] = {
                "class_type": class_type,
                "inputs": api_inputs,
                "_meta": {"title": node.get("title") or class_type},
            }

        logger.info("Converted ComfyUI save-format workflow to API format (%s nodes).", len(api_workflow))
        return api_workflow

    def _get_comfy_api_key(self):
        """Return the Comfy API key for API-node workflow submissions."""
        return os.getenv("PRISM_COMFYUI_API_KEY") or self.core.getConfig("comfyui", "cloudApiKey", config="user") or ""

    def _prepare_local_inputs(self, workflow, inputs, server_address):
        """Upload absolute LoadImage paths to ComfyUI and return prompt inputs."""
        prepared_inputs = {}
        uploaded_cache = {}
        for node_name, node_inputs in inputs.items():
            node_id = str(node_name)
            node = workflow.get(node_id, {})
            if not node:
                found_node_id = self.getNodeIdFromName(workflow, node_name)
                node = workflow.get(found_node_id, {}) if found_node_id else {}

            upload_input_names = {
                "LoadImage": {"image"},
                "LoadVideo": {"file"},
            }.get(node.get("class_type"), set())
            prepared_inputs[node_name] = {}
            for input_name, value in node_inputs.items():
                if not (
                    input_name in upload_input_names
                    and self._is_absolute_local_filepath(value)
                ):
                    prepared_inputs[node_name][input_name] = value
                    continue

                filepath = os.path.expanduser(os.path.expandvars(value))
                if not os.path.isfile(filepath):
                    return {"error": "Input file does not exist: %s" % value}

                if filepath not in uploaded_cache:
                    uploaded = self._upload_local_input_file(filepath, server_address)
                    if uploaded.get("error"):
                        return uploaded
                    uploaded_cache[filepath] = uploaded["name"]
                prepared_inputs[node_name][input_name] = uploaded_cache[filepath]

        return prepared_inputs

    def _upload_local_input_file(self, filepath, server_address):
        """Upload a file to ComfyUI's input folder and return its input name."""
        import mimetypes
        import urllib.error
        import urllib.request

        filename = "%s_%s%s" % (
            os.path.splitext(os.path.basename(filepath))[0],
            uuid.uuid4().hex,
            os.path.splitext(filepath)[1],
        )
        content_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
        with open(filepath, "rb") as input_file:
            file_bytes = input_file.read()
        body, multipart_content_type = self._encode_multipart_formdata(
            fields=[("type", "input"), ("overwrite", "true")],
            files=[("image", filename, file_bytes, content_type)],
        )
        request = urllib.request.Request(
            "http://%s/upload/image" % server_address,
            data=body,
            headers={"Content-Type": multipart_content_type},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            logger.error("Failed to upload ComfyUI input image: %s", exc)
            return {"error": "Failed to upload input image: %s" % exc}

        uploaded_name = result.get("name") or result.get("filename")
        if not uploaded_name:
            return {"error": "ComfyUI did not return an input filename: %s" % result}
        return {"name": uploaded_name}

    def _prepare_missing_load3d_inputs(self, workflow, server_address):
        """Provide editor-only Load3D metadata required by ComfyUI's API node."""
        for node in workflow.values():
            if node.get("class_type") != "Load3D":
                continue

            node_inputs = node.get("inputs", {})
            if node_inputs.get("image") not in (None, ""):
                continue

            uploaded = self._upload_load3d_placeholder(server_address)
            if uploaded.get("error"):
                return uploaded

            image_name = uploaded["name"]
            node_inputs["image"] = {
                "image": image_name,
                "mask": image_name,
                "normal": image_name,
                "camera_info": {
                    "position": {"x": 0, "y": 0, "z": 1},
                    "target": {"x": 0, "y": 0, "z": 0},
                    "zoom": 1,
                    "cameraType": "perspective",
                    "quaternion": {"x": 0, "y": 0, "z": 0, "w": 1},
                    "fov": 35,
                    "aspect": 1,
                    "near": 0.01,
                    "far": 10000,
                    "frustum": {"left": -5, "right": 5, "top": 5, "bottom": -5},
                },
                "recording": "",
                "model_3d_info": [],
            }

        return {}

    def _upload_load3d_placeholder(self, server_address):
        """Upload a transparent image for Load3D nodes without saved preview data."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as image_file:
            filepath = image_file.name

        try:
            image = QImage(1, 1, QImage.Format_ARGB32)
            image.fill(0)
            if not image.save(filepath):
                return {"error": "Failed to create a Load3D placeholder image."}
            return self._upload_local_input_file(filepath, server_address)
        finally:
            try:
                os.remove(filepath)
            except OSError:
                pass

    def _queue_local_prompt(self, workflow, server_address, client_id=None, api_key=None, workflow_id=None):
        """POST workflow to local ComfyUI /prompt. Returns dict with prompt_id, or error key."""
        import urllib.request
        import urllib.error
        import uuid

        if client_id is None:
            client_id = str(uuid.uuid4())
        payload_data = {"prompt": workflow, "client_id": client_id}
        extra_data = {}
        if api_key:
            extra_data.update({
                "api_key_comfy_org": api_key,
                "comfy_usage_source": "prism",
            })

        if workflow_id:
            extra_data["extra_pnginfo"] = {"workflow": {"id": str(workflow_id)}}

        if extra_data:
            payload_data["extra_data"] = extra_data

        payload = json.dumps(payload_data).encode("utf-8")
        req = urllib.request.Request(
            f"http://{server_address}/prompt",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            msg = f"submitGraphToLocal: HTTP {e.code} queuing prompt: {body}"
            logger.error(msg)
            return {"error": msg}
        except urllib.error.URLError as e:
            msg = f"submitGraphToLocal: network error queuing prompt: {e.reason}"
            logger.error(msg)
            return {"error": msg}

        prompt_id = result.get("prompt_id")
        if not prompt_id:
            msg = f"submitGraphToLocal: no prompt_id in response: {result}"
            logger.error(msg)
            return {"error": msg}

        return {"prompt_id": prompt_id, "client_id": client_id}

    def _wait_local_completion(self, prompt_id, ws):
        """Block on an already-connected WebSocket until the prompt finishes.

        Listens for an 'executing' message where data['node'] is None and
        data['prompt_id'] matches ours — the ComfyUI signal for end of execution.
        Returns ComfyUI error details for failed or interrupted prompts.
        The WebSocket must be connected before the prompt is queued to avoid
        missing completion messages from fast workflows.
        """
        while True:
            out = ws.recv()
            if not isinstance(out, str):
                # Binary frames are preview images — ignore them
                continue
            message = json.loads(out)
            msg_type = message.get("type")
            data = message.get("data", {})
            if msg_type == "executing":
                if data.get("node") is None and data.get("prompt_id") == prompt_id:
                    logger.debug("submitGraphToLocal: ComfyUI terminal response for %s: %s", prompt_id, message)
                    return {"status": "success"}
            elif msg_type == "execution_success":
                if data.get("prompt_id") == prompt_id:
                    logger.debug("submitGraphToLocal: ComfyUI terminal response for %s: %s", prompt_id, message)
                    return {"status": "success"}
            elif msg_type in ("execution_error", "execution_interrupted"):
                if data.get("prompt_id") != prompt_id:
                    continue

                response = {
                    key: data[key]
                    for key in (
                        "node_id",
                        "node_type",
                        "exception_type",
                        "exception_message",
                        "executed",
                    )
                    if key in data
                }
                if msg_type == "execution_interrupted":
                    error = "ComfyUI workflow execution was interrupted."
                else:
                    error = response.get("exception_message") or "ComfyUI workflow execution failed."
                    node_type = response.get("node_type")
                    node_id = response.get("node_id")
                    if node_type:
                        error = "ComfyUI node '%s'%s failed: %s" % (
                            node_type,
                            " (%s)" % node_id if node_id else "",
                            error.strip(),
                        )

                return {
                    "status": "error",
                    "error": error,
                    "response": response,
                }

    def _get_local_history(self, prompt_id, server_address, attempts=5, retry_delay=0.5):
        """GET /history/{prompt_id}, allowing ComfyUI time to persist completed output metadata."""
        import urllib.request
        import urllib.error
        import time

        for attempt in range(1, attempts + 1):
            try:
                with urllib.request.urlopen(f"http://{server_address}/history/{prompt_id}") as resp:
                    history = json.loads(resp.read().decode("utf-8"))
            except (urllib.error.HTTPError, urllib.error.URLError) as e:
                logger.error(f"runGraphLocal: failed to fetch history: {e}")
                return {}

            job_data = history.get(prompt_id, {})
            logger.debug("submitGraphToLocal: ComfyUI history for %s: %s", prompt_id, job_data)
            outputs = job_data.get("outputs", {})
            if job_data or attempt == attempts:
                return outputs

            logger.debug(
                "submitGraphToLocal: history for %s is not available yet (attempt %s/%s)",
                prompt_id,
                attempt,
                attempts,
            )
            time.sleep(retry_delay)

        return {}

    def getLocalWorkflowJobs(self, workflow_id, server_address=None):
        """Return local ComfyUI jobs for one Prism workflow identifier."""
        import urllib.parse
        import urllib.request

        if not workflow_id:
            return []

        server_address = server_address or self._get_local_server_address()
        query = urllib.parse.urlencode({"workflow_id": str(workflow_id)})
        try:
            with urllib.request.urlopen(
                "http://%s/api/jobs?%s" % (server_address, query), timeout=10
            ) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            logger.warning("Failed to query ComfyUI workflow history: %s", exc)
            return []

        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("jobs") or data.get("data") or []
        return []

    def _delete_local_history(self, prompt_id, server_address):
        """POST /history with delete=[prompt_id] to remove the job from ComfyUI's history."""
        import urllib.request
        import urllib.error

        payload = json.dumps({"delete": [prompt_id]}).encode("utf-8")
        req = urllib.request.Request(
            f"http://{server_address}/history",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req):
                pass
            logger.debug(f"submitGraphToLocal: deleted history for prompt_id={prompt_id}")
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            logger.warning(f"submitGraphToLocal: failed to delete history for {prompt_id}: {e}")

    def _reset_local_cache(self, server_address):
        """POST /free with free_memory=true to clear the ComfyUI node output cache.

        This causes PromptExecutor.reset() to be called at the start of the next
        queue loop, creating a fresh CacheSet so the same workflow can be re-run
        without hitting cached outputs.

        unload_models is explicitly set to false to avoid evicting loaded models
        from VRAM (which would slow down subsequent runs significantly).
        """
        import urllib.request
        import urllib.error

        payload = json.dumps({"free_memory": True, "unload_models": False}).encode("utf-8")
        req = urllib.request.Request(
            f"http://{server_address}/free",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req):
                pass
            logger.debug(f"submitGraphToLocal: requested cache reset on {server_address}")
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            logger.warning(f"submitGraphToLocal: failed to reset cache on {server_address}: {e}")

    def _download_local_outputs(
        self, outputs, output_dir, server_address, app_mode_output_node_ids=None
    ):
        """Download all media and 3D files from node outputs via /view to output_dir.

        Returns a list of local file paths that were written.
        """
        import urllib.request
        import urllib.parse

        downloaded = []

        for node_id, node_outputs in outputs.items():
            if app_mode_output_node_ids and str(node_id) not in app_mode_output_node_ids:
                logger.debug(
                    "submitGraphToLocal: skipping non-App-Mode output node %s", node_id
                )
                continue
            logger.debug(
                "submitGraphToLocal: processing ComfyUI output node %s with keys: %s",
                node_id,
                list(node_outputs),
            )
            for media_key in ("images", "video", "audio", "3d"):
                for file_info in node_outputs.get(media_key) or []:
                    if file_info.get("type") == "input":
                        logger.debug(
                            "submitGraphToLocal: skipping input file reported by node %s: %s",
                            node_id,
                            file_info,
                        )
                        continue
                    filename = file_info.get("filename")
                    if not filename:
                        logger.debug(
                            "submitGraphToLocal: skipping %s output without a filename: %s",
                            media_key,
                            file_info,
                        )
                        continue
                    direct_path = file_info.get("filepath")
                    params = urllib.parse.urlencode({
                        "filename": filename,
                        "subfolder": file_info.get("subfolder", ""),
                        "type": file_info.get("type", "output"),
                    })
                    dest_path = self._resolve_output_path(output_dir, filename, len(downloaded))
                    try:
                        if direct_path and os.path.isfile(direct_path):
                            shutil.copy2(direct_path, dest_path)
                            logger.info(
                                "runGraphLocal: copied %s -> %s", direct_path, dest_path
                            )
                            downloaded.append(self._convert_glb_output_to_usd(dest_path))
                            continue
                        logger.debug(
                            "submitGraphToLocal: downloading %s output from node %s: %s",
                            media_key,
                            node_id,
                            file_info,
                        )
                        with urllib.request.urlopen(f"http://{server_address}/view?{params}") as resp:
                            with open(dest_path, "wb") as f:
                                f.write(resp.read())
                        logger.info(f"runGraphLocal: downloaded {filename} -> {dest_path}")
                        downloaded.append(self._convert_glb_output_to_usd(dest_path))
                    except Exception as e:
                        logger.error(f"runGraphLocal: failed to download {filename}: {e}")

        return downloaded

    def _convert_glb_output_to_usd(self, filepath):
        """Convert a ComfyUI GLB result before exposing it to Prism's output UI."""
        if os.path.splitext(filepath)[1].lower() != ".glb":
            return filepath

        core = getattr(self, "core", None)
        usd_plugin = core.getPlugin("USD") if core else None
        usd_api = getattr(usd_plugin, "api", None)
        if not usd_api:
            logger.warning("ComfyUI output is GLB, but the USD plugin is unavailable.")
            return filepath

        usd_path = os.path.splitext(filepath)[0] + ".usd"
        try:
            converted_path = usd_api.convertGlbToUsd(filepath, usd_path)
        except Exception as exc:
            logger.warning("Failed to convert ComfyUI GLB output to USD: %s", exc)
            return filepath

        if not converted_path or not os.path.isfile(converted_path):
            logger.warning("Failed to convert ComfyUI GLB output to USD: %s", filepath)
            return filepath

        try:
            os.remove(filepath)
        except OSError:
            logger.warning("Failed to remove converted ComfyUI GLB output: %s", filepath)

        return converted_path

    def _resolve_output_path(self, output_dir, source_filename, file_index):
        """Resolve destination path for a downloaded file.

        output_dir can be either:
        - a directory path (default behavior)
        - a file path (e.g. C:/tmp/result.png), which renames output files.
        """
        normalized_output = os.path.expanduser(os.path.expandvars(output_dir))

        # Existing directories must always be treated as directories.
        is_dir_target = os.path.isdir(normalized_output)

        # If the path has a file extension and is not an existing directory,
        # treat it as a file target.
        file_ext = os.path.splitext(normalized_output)[1]
        is_file_target = (not is_dir_target) and bool(file_ext)

        if is_file_target:
            base, ext = os.path.splitext(normalized_output)
            os.makedirs(os.path.dirname(normalized_output) or ".", exist_ok=True)
            if file_index == 0:
                return normalized_output

            # Multiple outputs with a file target: append an index suffix.
            return f"{base}_{file_index + 1}{ext}"

        os.makedirs(normalized_output, exist_ok=True)
        return os.path.join(normalized_output, source_filename)

    def _get_cloud_config(self):
        """Return (api_key, base_url) from Prism user config."""
        api_key = self._get_comfy_api_key()
        base_url = (
            self.core.getConfig("comfyui", "cloudBaseUrl", config="user")
            or "https://cloud.comfy.org"
        ).rstrip("/")
        return api_key, base_url

    def _apply_workflow_inputs(self, workflow, inputs):
        """Apply {node_name: {input_name: value}} overrides to workflow dict in-place."""
        for node_name, node_inputs in inputs.items():
            node_key = str(node_name) if str(node_name) in workflow else self.getNodeIdFromName(workflow, node_name)
            if node_key in workflow:
                for input_name, value in node_inputs.items():
                    workflow[node_key]["inputs"][input_name] = value
                    logger.debug(f"Applied input override: node {node_key} input '{input_name}' = {value}")
            else:
                logger.warning(f"Workflow input override node '{node_name}' was not found")

    def _is_absolute_local_filepath(self, value):
        """Return True when value is an absolute local filesystem path string."""
        if not isinstance(value, str):
            return False

        lowered = value.lower()
        if lowered.startswith(("http://", "https://", "s3://", "file://")):
            return False

        expanded = os.path.expanduser(os.path.expandvars(value))
        return os.path.isabs(expanded)

    def _encode_multipart_formdata(self, fields, files):
        """Build a multipart/form-data request body.

        fields: list of (name, value)
        files: list of (field_name, filename, file_bytes, content_type)
        """
        boundary = f"----PrismBoundary{uuid.uuid4().hex}"
        body = bytearray()

        for name, value in fields:
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8")
            )
            body.extend(str(value).encode("utf-8"))
            body.extend(b"\r\n")

        for field_name, filename, file_bytes, content_type in files:
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(
                (
                    f'Content-Disposition: form-data; name="{field_name}"; '
                    f'filename="{filename}"\r\n'
                ).encode("utf-8")
            )
            body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
            body.extend(file_bytes)
            body.extend(b"\r\n")

        body.extend(f"--{boundary}--\r\n".encode("utf-8"))
        content_type = f"multipart/form-data; boundary={boundary}"
        return bytes(body), content_type

    def _upload_cloud_input_file(self, file_path, api_key, base_url):
        """Upload a local file to cloud input storage and return its reference name."""
        import urllib.request
        import urllib.error
        import mimetypes

        expanded_path = os.path.expanduser(os.path.expandvars(file_path))
        if not os.path.isfile(expanded_path):
            msg = f"submitGraphToCloud: input path does not exist: {file_path}"
            logger.error(msg)
            return {"error": msg}

        filename = os.path.basename(expanded_path)
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        with open(expanded_path, "rb") as f:
            file_bytes = f.read()

        body, multipart_content_type = self._encode_multipart_formdata(
            fields=[("type", "input"), ("overwrite", "true")],
            files=[("image", filename, file_bytes, content_type)],
        )

        req = urllib.request.Request(
            f"{base_url}/api/upload/image",
            data=body,
            headers={"X-API-Key": api_key, "Content-Type": multipart_content_type},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            msg = f"submitGraphToCloud: HTTP {e.code} uploading input '{file_path}': {body}"
            logger.error(msg)
            return {"error": msg}
        except urllib.error.URLError as e:
            msg = f"submitGraphToCloud: network error uploading input '{file_path}': {e.reason}"
            logger.error(msg)
            return {"error": msg}

        uploaded_name = result.get("name") or result.get("filename")
        if not uploaded_name:
            msg = f"submitGraphToCloud: upload succeeded but no file reference returned: {result}"
            logger.error(msg)
            return {"error": msg}

        logger.info(
            "submitGraphToCloud: uploaded input '%s' -> '%s'",
            expanded_path,
            uploaded_name,
        )
        return {
            "name": uploaded_name,
            "subfolder": result.get("subfolder", ""),
            "type": result.get("type", "input"),
        }

    def _prepare_cloud_inputs(self, inputs, api_key, base_url):
        """Upload absolute local filepaths in input overrides and replace with cloud refs."""
        prepared_inputs = {}
        uploaded_cache = {}

        for node_name, node_inputs in inputs.items():
            prepared_inputs[node_name] = {}
            for input_name, value in node_inputs.items():
                new_value = value

                if self._is_absolute_local_filepath(value):
                    expanded_path = os.path.expanduser(os.path.expandvars(value))
                    if os.path.isfile(expanded_path):
                        if expanded_path in uploaded_cache:
                            uploaded_ref = uploaded_cache[expanded_path]
                        else:
                            uploaded_ref = self._upload_cloud_input_file(
                                expanded_path, api_key, base_url
                            )
                            if isinstance(uploaded_ref, dict) and uploaded_ref.get("error"):
                                return uploaded_ref

                            uploaded_cache[expanded_path] = uploaded_ref

                        new_value = uploaded_ref["name"]
                    else:
                        logger.warning(
                            "submitGraphToCloud: absolute input path not found, using original value: %s",
                            value,
                        )

                prepared_inputs[node_name][input_name] = new_value

        return prepared_inputs

    def getNodeIdFromName(self, workflow, node_name):
        """Helper to find node_id by node name in workflow dict."""
        for node_id, node_data in workflow.items():
            if node_data.get("_meta", {}).get("title") == node_name:
                return node_id

        return None

    def _submit_workflow(self, workflow, api_key, base_url):
        """POST workflow to /api/prompt. Returns prompt_id string, or None on error."""
        import urllib.request
        import urllib.error

        payloadDict = {
            "prompt": workflow,
            "extra_data": {
                "api_key_comfy_org": api_key
            }
        }

        payload = json.dumps(payloadDict).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/prompt",
            data=payload,
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            msg = f"submitGraphToCloud: HTTP {e.code} submitting workflow: {body}"
            logger.error(msg)
            return {"error": msg}
        except urllib.error.URLError as e:
            msg = f"submitGraphToCloud: network error submitting workflow: {e.reason}"
            logger.error(msg)
            return {"error": msg}

        prompt_id = result.get("prompt_id")
        if not prompt_id:
            msg = f"submitGraphToCloud: no prompt_id in response: {result}"
            logger.error(msg)
            return {"error": msg}
    
        logger.info(f"submitGraphToCloud: received prompt_id={prompt_id}")
        return prompt_id

    def _poll_job_status(self, prompt_id, api_key, base_url, poll_interval=2.0):
        """Poll /api/job/{prompt_id}/status until a terminal state. Returns final status string."""
        import urllib.request
        import urllib.error
        import time

        terminal_states = {"completed", "cancelled", "error", "success"}
        status_url = f"{base_url}/api/job/{prompt_id}/status"

        while True:
            req = urllib.request.Request(status_url, headers={"X-API-Key": api_key}, method="GET")
            try:
                with urllib.request.urlopen(req) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")
                msg = f"submitGraphToCloud: HTTP {e.code} polling status: {body}"
                logger.error(msg)
                return {"status": "error", "error_message": msg}
            except urllib.error.URLError as e:
                msg = f"submitGraphToCloud: network error polling status: {e.reason}"
                logger.error(msg)
                return {"status": "error", "error_message": msg}

            status = result.get("status", "unknown")
            logger.debug(f"submitGraphToCloud: job {prompt_id} status={status} response={result}")

            if status in terminal_states:
                if status == "error":
                    logger.error(f"submitGraphToCloud: job {prompt_id} finished with error: {result.get('error_message', 'no error message')}")
                else:
                    logger.info(f"submitGraphToCloud: job {prompt_id} finished with status={status}")

                return result

            time.sleep(poll_interval)

    def _get_job_outputs(self, prompt_id, api_key, base_url):
        """Fetch node outputs from /api/history/{prompt_id}. Returns outputs dict."""
        import urllib.request
        import urllib.error

        req = urllib.request.Request(
            f"{base_url}/api/history/{prompt_id}",
            headers={"X-API-Key": api_key},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                history = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            logger.error(f"submitGraphToCloud: failed to fetch job history: {e}")
            return {}

        # History is keyed by prompt_id
        job_data = history.get(prompt_id, {})
        return job_data.get("outputs", {})

    def _wait_cloud_completion_ws(self, prompt_id, api_key, base_url, timeout=300):
        """Wait for cloud completion via WebSocket and collect node outputs.

        Returns a dict with at least:
            {"status": "success|completed|error|cancelled", "outputs": {...}}
        """
        from websockets.sync.client import connect
        import urllib.parse
        import time

        ws_scheme = "wss" if base_url.startswith("https://") else "ws"
        ws_base = base_url.replace("https://", "", 1).replace("http://", "", 1)
        query = urllib.parse.urlencode({"clientId": str(uuid.uuid4()), "token": api_key})
        ws_url = f"{ws_scheme}://{ws_base}/ws?{query}"

        outputs = {}
        ws = connect(ws_url)

        start_time = time.time()
        try:
            while True:
                if timeout and (time.time() - start_time) > timeout:
                    return {"status": "error", "error_message": "cloud websocket timeout", "outputs": outputs}

                out = ws.recv()
                if not isinstance(out, str):
                    # Ignore preview binary frames
                    continue

                message = json.loads(out)
                msg_type = message.get("type")
                data = message.get("data", {}) or {}

                if data.get("prompt_id") != prompt_id:
                    continue

                if msg_type == "executed" and data.get("output"):
                    node_id = data.get("node")
                    if node_id:
                        outputs[node_id] = data.get("output")
                elif msg_type == "execution_success":
                    return {"status": "success", "outputs": outputs}
                elif msg_type == "execution_error":
                    return {
                        "status": "error",
                        "error_message": data.get("exception_message", "unknown error"),
                        "outputs": outputs,
                    }
                elif msg_type == "execution_interrupted":
                    return {"status": "cancelled", "outputs": outputs}
        finally:
            ws.close()

    def _download_cloud_outputs(
        self, outputs, output_dir, api_key, base_url, app_mode_output_node_ids=None
    ):
        """Download all image/video/audio files from node outputs to output_dir.

        The cloud API returns a 302 redirect to a signed URL for each file.
        The signed URL must be fetched without the X-API-Key header.

        Returns a list of local file paths that were written.
        """
        import urllib.request
        import urllib.error
        import urllib.parse

        downloaded = []

        # Intercept redirects so we can fetch the signed URL without auth headers
        class _NoRedirect(urllib.request.HTTPRedirectHandler):
            def http_error_302(self, req, fp, code, msg, headers):
                raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)
            http_error_301 = http_error_302
            http_error_303 = http_error_302
            http_error_307 = http_error_302
            http_error_308 = http_error_302

        no_redirect_opener = urllib.request.build_opener(_NoRedirect())

        for node_id, node_outputs in outputs.items():
            if app_mode_output_node_ids and str(node_id) not in app_mode_output_node_ids:
                logger.debug(
                    "submitGraphToCloud: skipping non-App-Mode output node %s", node_id
                )
                continue
            for media_key in ("images", "video", "audio"):
                for file_info in node_outputs.get(media_key) or []:
                    filename = file_info.get("filename")
                    if not filename:
                        continue

                    params = urllib.parse.urlencode({
                        "filename": filename,
                        "subfolder": file_info.get("subfolder", ""),
                        "type": file_info.get("type", "output"),
                    })
                    view_req = urllib.request.Request(
                        f"{base_url}/api/view?{params}",
                        headers={"X-API-Key": api_key},
                        method="GET",
                    )

                    # Expect a redirect to a signed storage URL
                    signed_url = None
                    try:
                        with no_redirect_opener.open(view_req) as resp:
                            # No redirect — fall back to direct download via the same URL
                            signed_url = f"{base_url}/api/view?{params}"
                    except urllib.error.HTTPError as e:
                        if e.code in (301, 302, 303, 307, 308):
                            signed_url = e.headers.get("Location")
                            if not signed_url:
                                logger.error(f"submitGraphToCloud: no Location header for {filename}")
                                continue
                        else:
                            logger.error(f"submitGraphToCloud: HTTP {e.code} fetching view URL for {filename}")
                            continue
                    except urllib.error.URLError as e:
                        logger.error(f"submitGraphToCloud: network error fetching view URL for {filename}: {e.reason}")
                        continue

                    # Download from signed URL — no auth header
                    dest_path = self._resolve_output_path(output_dir, filename, len(downloaded))
                    try:
                        with urllib.request.urlopen(signed_url) as resp:
                            with open(dest_path, "wb") as f:
                                f.write(resp.read())
                        logger.info(f"submitGraphToCloud: downloaded {filename} -> {dest_path}")
                        downloaded.append(dest_path)
                    except Exception as e:
                        logger.error(f"submitGraphToCloud: failed to download {filename}: {e}")

        return downloaded

    @err_catcher(name=__name__)
    def submitGraphToCloud(self, path=None, workflow=None, inputs=None, waitForCompletion=False, output_dir=None):
        # Load workflow from file if not provided directly
        if workflow is None:
            if path is None:
                msg = "submitGraphToCloud: either 'path' or 'workflow' must be provided"
                logger.error(msg)
                return {"error": msg}
            with open(path, "r", encoding="utf-8") as f:
                workflow = json.load(f)

        app_mode_output_node_ids = self._get_app_mode_output_node_ids(workflow)
        try:
            workflow = self._get_api_workflow(workflow)
        except ValueError as e:
            msg = "submitGraphToCloud: %s" % e
            logger.error(msg)
            return {"error": msg}

        # Read API key and base URL from Prism user config
        api_key, base_url = self._get_cloud_config()
        if not api_key:
            msg = "submitGraphToCloud: no Comfy API key configured ( PRISM_COMFYUI_API_KEY environment variable or comfyui > cloudApiKey in user config)"
            logger.error(msg)
            return {"error": msg}

        # Apply input overrides: upload absolute local filepaths and replace with cloud refs.
        if inputs:
            prepared_inputs = self._prepare_cloud_inputs(inputs, api_key, base_url)
            if isinstance(prepared_inputs, dict) and prepared_inputs.get("error"):
                return prepared_inputs

            self._apply_workflow_inputs(workflow, prepared_inputs)

        # Submit
        result = self._submit_workflow(workflow, api_key, base_url)
        prompt_id = result if not isinstance(result, dict) else None
        if not prompt_id:
            return result

        logger.info(f"submitGraphToCloud: job submitted, prompt_id={prompt_id}")

        # Return immediately if neither completion nor download was requested
        should_wait = waitForCompletion or (output_dir is not None)
        if not should_wait:
            return {"prompt_id": prompt_id, "status": "submitted"}

        # Wait for the job to reach a terminal state.
        # Prefer WebSocket completion/output events and fall back to status polling.
        status_result = {}
        ws_outputs = {}
        try:
            ws_result = self._wait_cloud_completion_ws(prompt_id, api_key, base_url)
            status_result = {"status": ws_result.get("status")}
            if ws_result.get("error_message"):
                status_result["error_message"] = ws_result.get("error_message")
            ws_outputs = ws_result.get("outputs") or {}
        except Exception as e:
            logger.warning(f"submitGraphToCloud: websocket completion failed, falling back to polling: {e}")
            status_result = self._poll_job_status(prompt_id, api_key, base_url)

        result = {"prompt_id": prompt_id, "status": status_result.get("status")}
        if status_result.get("status") in ["error", "failed"]:
            result["error_message"] = status_result.get("error_message", "unknown error")

        # Download outputs to the requested directory
        if output_dir and status_result.get("status") in ["completed", "success"]:
            outputs = ws_outputs or self._get_job_outputs(prompt_id, api_key, base_url)
            downloaded = self._download_cloud_outputs(
                outputs,
                output_dir,
                api_key,
                base_url,
                app_mode_output_node_ids=app_mode_output_node_ids,
            )
            result["downloaded_files"] = downloaded

        return result


class PrismWebSocketServer(QThread):
    command_received = Signal(dict)
    connection_state_changed = Signal(bool, int)
    
    def __init__(self, core, host="localhost", port=8765):
        super().__init__()
        self.core = core
        self.host = host
        if self.core.requestedApp == "ComfyUI":
            port = 8765  # Default port for ComfyUI
        else:
            return

        self.port = port
        self.clients = set()
        self.server = None
        self.loop = None
        self.pending_messages = []
        self._stop_event = None
        
    async def handle_client(self, websocket):
        import websockets
        """Handle incoming WebSocket connections from ComfyUI"""
        
        try:
            async for message in websocket:
                data = json.loads(message)
                print(f"Received from ComfyUI: {data}")
                if data.get("action") == "get_context_identity":
                    await websocket.send(json.dumps({
                        "protocol": "prism-comfyui-context-v1",
                        "pid": os.getpid(),
                        "prism_root": self.core.prismRoot,
                        "comfyui_root": os.environ.get("PRISM_COMFYUI_ROOT", ""),
                        "closing": bool(self._stop_event and self._stop_event.is_set()),
                    }))
                    continue
                if websocket not in self.clients:
                    self.clients.add(websocket)
                    self.connection_state_changed.emit(True, len(self.clients))
                    print(f"ComfyUI client connected. Total clients: {len(self.clients)}")
                
                # Process command from ComfyUI
                self.command_received.emit(data)
                
                # # Send response back to ComfyUI
                # response = {"status": "success", "action": "info"}
                # await websocket.send(json.dumps(response))
                
        except websockets.exceptions.ConnectionClosed:
            print("ComfyUI client disconnected")
        finally:
            if websocket in self.clients:
                self.clients.discard(websocket)
                self.connection_state_changed.emit(bool(self.clients), len(self.clients))
    
    async def start_server(self):
        import websockets
        """Start the WebSocket server"""
        self._stop_event = asyncio.Event()
        self.server = await websockets.serve(
            self.handle_client, 
            self.host, 
            self.port
        )
        print(f"WebSocket server started on ws://{self.host}:{self.port}")
        
        # Process pending messages periodically until stop is signalled
        while not self._stop_event.is_set():
            if self.pending_messages:
                messages = self.pending_messages.copy()
                self.pending_messages.clear()
                for command in messages:
                    await self.send_to_comfyui(command)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=0.1)
            except asyncio.TimeoutError:
                pass

        self.server.close()
        await self.server.wait_closed()
    
    def run(self):
        """Qt thread entry point"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.start_server())
    
    async def send_to_comfyui(self, command):
        """Send command to all connected ComfyUI clients"""
        if self.clients:
            message = json.dumps(command)
            await asyncio.gather(
                *[client.send(message) for client in self.clients],
                return_exceptions=True
            )
    
    def send_command(self, command):
        """Thread-safe method to queue a command to send to ComfyUI"""
        self.pending_messages.append(command)

    def stop(self):
        """Signal the server loop to exit cleanly and wait for the thread to finish."""
        if self.loop is None or self._stop_event is None:
            return
        self.loop.call_soon_threadsafe(self._stop_event.set)
        self.wait()


class ComfyAppOutputList(QListWidget):
    def startDrag(self, supported_actions):
        item = self.currentItem()
        if not item:
            return

        filepath = item.data(Qt.UserRole)
        if not filepath:
            return

        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(filepath)])
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec_(Qt.CopyAction)


class ComfyAppModelDragButton(QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filepath = ""
        self.drag_start_position = None
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip("Drag model file into another application")

    def setFilepath(self, filepath):
        self.filepath = filepath or ""
        self.setVisible(bool(self.filepath))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.filepath:
            self.drag_start_position = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self.filepath or not (event.buttons() & Qt.LeftButton):
            return super().mouseMoveEvent(event)

        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(self.filepath)])
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        self.setCursor(Qt.OpenHandCursor)
        drag.exec_(Qt.CopyAction)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)


class ComfyAppFileThumbnail(QLabel):
    def __init__(self, file_input):
        super().__init__()
        self.file_input = file_input
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)

    def dragEnterEvent(self, event):
        if self.file_input.getDroppedVisualFile(event):
            self.file_input.setDropHover(True)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.file_input.setDropHover(False)
        event.accept()

    def dropEvent(self, event):
        filepath = self.file_input.getDroppedVisualFile(event)
        self.file_input.setDropHover(False)
        if filepath:
            self.file_input.setText(filepath)
            event.acceptProposedAction()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.file_input.showThumbnailMenu()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.file_input.refreshThumbnailPixmap()


class ComfyAppReferenceMediaPlayerMixin(object):
    def getSelectedContexts(self):
        filepath = self.mediaVersionPlayer.text()
        return [{"path": filepath}] if filepath else []

    def getFilesFromContext(self, context):
        filepath = context.get("path")
        return [filepath] if filepath and os.path.isfile(filepath) else []


class ComfyAppFileInput(QWidget):
    def __init__(self, dialog, value=""):
        super().__init__()
        self.dialog = dialog
        self.origin = dialog
        self.core = self.dialog.core
        self.thumbnail_size = QSize(260, 150)
        self.thumbnail_pixmap = QPixmap()
        self.setAcceptDrops(True)
        self.thumbnail = ComfyAppFileThumbnail(self)
        self.thumbnail.setMinimumSize(260, 180)
        self.thumbnail.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.thumbnail.setToolTip("Drop a file here or click for options")
        import MediaBrowser
        media_class = type(
            "ComfyAppReferenceMediaPlayer",
            (ComfyAppReferenceMediaPlayerMixin, MediaBrowser.MediaPlayer),
            {},
        )
        self.media_player = media_class(self)
        self.media_player.l_info.setHidden(True)
        self.media_player.l_preview.setAcceptDrops(False)
        self.media_player.hide()
        self.path = QLineEdit()
        self.path.setText(value)
        self.path.setContextMenuPolicy(Qt.CustomContextMenu)
        self.path.customContextMenuRequested.connect(self.showPathMenu)
        self.path.textChanged.connect(self.updateThumbnail)
        self.browse_button = QToolButton()
        self.browse_button.setToolTip("Browse for a reference file")
        self.browse_button.clicked.connect(self.browse)
        browse_path = os.path.join(
            self.dialog.core.prismRoot, "Scripts", "UserInterfacesPrism", "browse.png"
        )
        self.browse_button.setIcon(self.dialog.core.media.getColoredIcon(browse_path))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        path_layout = QHBoxLayout()
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.addWidget(self.path, 1)
        path_layout.addWidget(self.browse_button)
        layout.addLayout(path_layout)
        layout.addWidget(self.thumbnail)
        layout.addWidget(self.media_player)
        self.updateThumbnail(value)

    def text(self):
        return self.path.text()

    def setText(self, value):
        self.path.setText(value)

    def dragEnterEvent(self, event):
        if self.getDroppedVisualFile(event):
            self.setDropHover(True)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setDropHover(False)
        event.accept()

    def dropEvent(self, event):
        filepath = self.getDroppedVisualFile(event)
        self.setDropHover(False)
        if filepath:
            self.setText(filepath)
            event.acceptProposedAction()
        else:
            event.ignore()

    def getDroppedVisualFile(self, event):
        if not event.mimeData().hasUrls():
            return ""

        for url in event.mimeData().urls():
            if url.isLocalFile() and self.isVisualMediaFile(url.toLocalFile()):
                return url.toLocalFile()
        return ""

    def isVisualMediaFile(self, filepath):
        extension = os.path.splitext(filepath)[1].lower()
        video_extensions = {
            item.lower() for item in getattr(self.core.media, "videoFormats", [])
        }
        image_extensions = {
            "." + bytes(image_format).decode().lower()
            for image_format in QImageReader.supportedImageFormats()
        }
        image_extensions.update({".dpx", ".exr", ".hdr"})
        return extension in video_extensions or extension in image_extensions

    def setDropHover(self, hovered):
        self.thumbnail.setStyleSheet(
            "border-radius: 8px; border-style: dashed; border-color: rgb(100, 200, 100); border-width: 2px;"
            if hovered else ""
        )

    def showPathMenu(self, pos):
        menu = self.path.createStandardContextMenu()
        if self.path.text():
            menu.addSeparator()
            menu.addAction("Open in explorer", lambda: self.dialog.core.openFolder(self.path.text()))
        menu.addAction("Paste image from clipboard", self.pasteClipboardImage)
        menu.exec_(self.path.mapToGlobal(pos))

    def showThumbnailMenu(self):
        menu = QMenu(self)
        menu.addAction("Browse...", self.browse)
        menu.addAction("Paste from Clipboard", self.pasteClipboardImage)
        menu.addAction("Capture Screen", self.captureScreen)
        menu.addSeparator()
        menu.addAction("Clear", lambda: self.setText(""))
        menu.exec_(QCursor.pos())

    def browse(self):
        self.dialog.browseReferenceFile(self)

    def pasteClipboardImage(self):
        pixmap = self.dialog.core.media.getPixmapFromClipboard()
        if not pixmap:
            self.dialog.core.popup("No image in clipboard.", parent=self.dialog)
            return
        path = self.dialog.saveClipboardPixmap(pixmap)
        if path:
            self.setText(path)

    def captureScreen(self):
        pixmap = self.dialog.captureScreen()
        if pixmap:
            path = self.dialog.saveClipboardPixmap(pixmap)
            if path:
                self.setText(path)

    def updateThumbnail(self, filepath):
        extension = os.path.splitext(filepath)[1].lower()
        is_video = extension in {
            item.lower() for item in getattr(self.core.media, "videoFormats", [])
        }
        if filepath and os.path.isfile(filepath) and is_video:
            self.thumbnail.hide()
            self.media_player.show()
            self.media_player.w_timeslider.show()
            self.media_player.w_playerCtrls.show()
            self.media_player.updatePreview()
            return

        timeline = getattr(self.media_player, "timeline", None)
        if timeline:
            timeline.stop()
        self.media_player.hide()
        self.thumbnail.show()
        pixmap = QPixmap()
        if filepath and os.path.isfile(filepath):
            try:
                pixmap = self.dialog.core.media.getPixmapFromPath(filepath)
            except Exception:
                pixmap = QPixmap()

        if not pixmap or pixmap.isNull():
            icon = self.core.media.getColoredIcon(self.dialog.dragdrop_thumbnail_path)
            pixmap = icon.pixmap(self.thumbnail_size)

        self.thumbnail_pixmap = pixmap
        self.refreshThumbnailPixmap()

    def refreshThumbnailPixmap(self):
        if self.thumbnail_pixmap.isNull():
            return

        available_size = self.thumbnail.contentsRect().size()
        if available_size.width() <= 0 or available_size.height() <= 0:
            available_size = self.thumbnail_size
        self.thumbnail.setPixmap(
            self.thumbnail_pixmap.scaled(
                available_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )


class ComfyAppMediaPlayerMixin(object):
    def getSelectedContexts(self):
        filepath = self.mediaVersionPlayer.selected_output
        return [{"path": filepath}] if filepath else []

    def getFilesFromContext(self, context):
        filepath = context.get("path")
        return [filepath] if filepath and os.path.isfile(filepath) else []


class ComfyAppWorkflowWorker(QThread):
    resultReady = Signal(object)

    def __init__(self, plugin, filepath, inputs, output_dir, workflow_id, cloud=False):
        super().__init__()
        self.plugin = plugin
        self.filepath = filepath
        self.inputs = inputs
        self.output_dir = output_dir
        self.workflow_id = workflow_id
        self.cloud = cloud

    def run(self):
        try:
            if self.cloud:
                result = self.plugin.submitGraphToCloud(
                    path=self.filepath,
                    inputs=self.inputs,
                    waitForCompletion=True,
                    output_dir=self.output_dir,
                )
            else:
                result = self.plugin.submitGraphToLocal(
                    path=self.filepath,
                    inputs=self.inputs,
                    waitForCompletion=True,
                    output_dir=self.output_dir,
                    workflow_id=self.workflow_id,
                )
        except Exception as exc:
            logger.exception("Failed to run ComfyUI App Mode workflow")
            result = {"error": str(exc)}

        self.resultReady.emit(result)


class ComfyAppHistoryWorker(QThread):
    resultReady = Signal(object)

    def __init__(self, plugin, workflow_id, output_dir):
        super().__init__()
        self.plugin = plugin
        self.workflow_id = workflow_id
        self.output_dir = output_dir

    def run(self):
        files = self._getPersistedFiles()
        try:
            jobs = self.plugin.getLocalWorkflowJobs(self.workflow_id)
            for job_index, job in enumerate(jobs):
                outputs = self._get_outputs(job)
                if not outputs:
                    continue
                job_dir = os.path.join(self.output_dir, "history_%s" % job_index)
                files += self.plugin._download_local_outputs(
                    outputs,
                    job_dir,
                    self.plugin._get_local_server_address(),
                )
        except Exception:
            logger.exception("Failed to load ComfyUI workflow history")
        self.resultReady.emit(files)

    def _getPersistedFiles(self):
        files = []
        for root, directories, filenames in os.walk(self.output_dir):
            directories[:] = [directory for directory in directories if directory != "_thumbs"]
            for filename in filenames:
                filepath = os.path.join(root, filename)
                if os.path.isfile(filepath):
                    files.append(filepath)
        return sorted(files, key=os.path.getmtime, reverse=True)

    def _get_outputs(self, job):
        if not isinstance(job, dict):
            return {}
        candidates = [job.get("outputs"), job.get("ui"), job.get("result")]
        result = job.get("result")
        if isinstance(result, dict):
            candidates.append(result.get("ui"))

        for outputs in candidates:
            if not isinstance(outputs, dict):
                continue
            normalized = self._normalize_outputs(outputs)
            if normalized:
                return {"history": normalized}
        return {}

    def _normalize_outputs(self, data):
        outputs = {}
        for key in ("images", "video", "videos", "audio", "3d"):
            values = data.get(key)
            if values:
                outputs["video" if key == "videos" else key] = values
        return outputs


class ComfyAppWorkflowDialog(QDialog):
    model_extensions = {".usd", ".usda", ".usdc", ".usdz", ".fbx", ".obj", ".glb", ".gltf", ".abc"}

    def __init__(self, plugin, filepath, parent=None):
        self._parent = parent
        super().__init__()
        self.plugin = plugin
        self.core = plugin.core
        self.origin = self
        self.filepath = filepath
        self.input_widgets = {}
        self.worker = None
        self.history_worker = None
        self.selected_output = ""
        self.quickview = None
        self.pending_model_previews = set()
        self.output_loading_active = False
        self.thumbnail_size = QSize(132, 96)
        self.dragdrop_thumbnail_path = os.path.join(
            self.plugin.pluginDirectory, "Resources", "dragdrop.png"
        )
        self._load_workflow()
        history_id = "".join(
            char if char.isalnum() or char in ("-", "_") else "_"
            for char in self.workflow_id
        )
        self.output_dir = os.path.join(
            self.core.getUserPrefDir(), "ComfyUI", "WorkflowHistory", history_id
        )
        os.makedirs(self.output_dir, exist_ok=True)
        self.setupUi()
        QTimer.singleShot(0, self.refresh_history)

    def _load_workflow(self):
        with open(self.filepath, "r", encoding="utf-8") as workflow_file:
            self.workflow = json.load(workflow_file)

        self.nodes = {
            str(node.get("id")): node
            for node in self.workflow.get("nodes", [])
            if node.get("id") is not None
        }
        linear_data = (self.workflow.get("extra") or {}).get("linearData") or {}
        self.exposed_inputs = linear_data.get("inputs") or []
        self.workflow_id = self.workflow.get("id") or linear_data.get("workflow_id")
        if not self.workflow_id:
            self.workflow_id = str(uuid.uuid5(uuid.NAMESPACE_URL, os.path.abspath(self.filepath)))

    def sizeHint(self):
        return QSize(1780, 720)

    def setupUi(self):
        workflow_name = os.path.splitext(os.path.basename(self.filepath))[0]
        self.setWindowTitle("ComfyUI | %s" % workflow_name)
        self.core.parentWindow(self, parent=self._parent)
        self.setStyleSheet("""
            QGroupBox#comfyInputs { font-weight: bold; margin-top: 10px; padding-top: 12px; }
            QFrame#comfyViewer { border: 1px solid rgba(140, 155, 170, 110); border-radius: 10px; background: rgba(0, 0, 0, 22); }
            QFrame#comfyHistory { border-left: 1px solid rgba(140, 155, 170, 80); }
            QLabel#comfyEmptyOutput { color: rgba(215, 225, 235, 180); font-size: 14px; }
            QListWidget#comfyHistoryList { border: 0; background: transparent; }
            QListWidget#comfyHistoryList::item { border: 1px solid transparent; border-radius: 6px; padding: 4px; }
            QListWidget#comfyHistoryList::item:selected { border-color: rgba(110, 180, 240, 190); background: rgba(70, 120, 165, 80); }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 1)

        controls = QGroupBox("Inputs")
        controls.setObjectName("comfyInputs")
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(12, 16, 12, 12)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(10)
        for exposed_input in self.exposed_inputs:
            parsed = self._parse_exposed_input(exposed_input)
            if not parsed:
                continue

            node_id, input_name, display_name = parsed
            value = self._get_input_value(node_id, input_name)
            widget = self._create_input_widget(node_id, input_name, value)
            self.input_widgets[(node_id, input_name)] = widget
            form.addRow(display_name, widget)

        if self.input_widgets:
            controls_layout.addLayout(form)
        controls_layout.addStretch()

        inputs_scroll_area = QScrollArea()
        inputs_scroll_area.setWidgetResizable(True)
        inputs_scroll_area.setFrameShape(QFrame.NoFrame)
        inputs_scroll_area.setWidget(controls)

        workspace = QWidget()
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(8)
        self.history_button = QToolButton()
        self.history_button.setCheckable(True)
        history_icon_path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "history.png"
        )
        self.history_button.setIcon(self.core.media.getColoredIcon(history_icon_path))
        self.history_button.setToolTip("Show previous generations")
        self.history_button.toggled.connect(self.setHistoryVisible)

        preview = QFrame()
        preview.setObjectName("comfyViewer")
        self.preview_layout = QVBoxLayout(preview)
        self.preview_layout.setContentsMargins(12, 12, 12, 12)
        import MediaBrowser
        media_class = type("ComfyAppMediaPlayer", (ComfyAppMediaPlayerMixin, MediaBrowser.MediaPlayer), {})
        self.media_player = media_class(self)
        self.media_player.l_info.setHidden(True)
        self.media_player.l_preview.setAcceptDrops(False)
        self.preview_layout.addWidget(self.media_player)
        self.output_media_spacer = QSpacerItem(
            0, 0, QSizePolicy.Minimum, QSizePolicy.Fixed
        )
        self.preview_message = QLabel("Select an output to preview")
        self.preview_message.setObjectName("comfyEmptyOutput")
        self.preview_message.setAlignment(Qt.AlignCenter)
        self.preview_message.setText("No output generated yet")
        self.media_player.setHidden(True)
        self.preview_layout.addWidget(self.preview_message)
        self.output_loading = QWidget(preview)
        loading_layout = QVBoxLayout(self.output_loading)
        self.output_loading_label = QLabel(self.output_loading)
        self.output_loading_label.setAlignment(Qt.AlignCenter)
        self.output_loading_label.setFixedSize(144, 144)
        loading_layout.addWidget(self.output_loading_label, alignment=Qt.AlignCenter)
        loading_path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "prism-loading-dark.gif"
        )
        self.output_loading_movie = QMovie(loading_path, QByteArray(), self.output_loading)
        self.output_loading_movie.setCacheMode(QMovie.CacheAll)
        self.output_loading_movie.frameChanged.connect(self._updateOutputLoadingFrame)
        self.output_loading.hide()
        self.model_drag_button = ComfyAppModelDragButton()
        drag_icon_path = os.path.join(
            self.plugin.pluginDirectory, "Resources", "hand.svg"
        )
        self.model_drag_button.setIcon(self.core.media.getColoredIcon(drag_icon_path))
        self.model_drag_button.hide()
        workspace_layout.addWidget(preview, 1)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        status_footer = QHBoxLayout()
        status_footer.addWidget(self.status_label, 1)
        status_footer.addWidget(self.model_drag_button)
        status_footer.addWidget(self.history_button)
        workspace_layout.addLayout(status_footer)
        workspace_layout.addItem(self.output_media_spacer)
        self.workspace_layout = workspace_layout

        self.history_sidebar = QFrame()
        self.history_sidebar.setObjectName("comfyHistory")
        self.history_sidebar.setMinimumWidth(190)
        self.history_sidebar.setMaximumWidth(230)
        history_layout = QVBoxLayout(self.history_sidebar)
        history_layout.setContentsMargins(10, 8, 10, 10)
        history_label = QLabel("Generation History")
        history_font = history_label.font()
        history_font.setBold(True)
        history_label.setFont(history_font)
        refresh_button = QToolButton()
        refresh_button.setToolTip("Refresh generation history")
        refresh_icon_path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "refresh.png"
        )
        refresh_button.setIcon(self.core.media.getColoredIcon(refresh_icon_path))
        refresh_button.clicked.connect(self.refresh_history)
        history_header = QHBoxLayout()
        history_header.addWidget(history_label)
        history_header.addStretch()
        history_header.addWidget(refresh_button)
        history_layout.addLayout(history_header)

        self.output_list = ComfyAppOutputList()
        self.output_list.setObjectName("comfyHistoryList")
        self.output_list.setViewMode(QListView.IconMode)
        self.output_list.setResizeMode(QListView.Adjust)
        self.output_list.setIconSize(QSize(132, 96))
        self.output_list.setGridSize(QSize(158, 126))
        self.output_list.setSpacing(6)
        self.output_list.setWordWrap(True)
        self.output_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.output_list.setDragEnabled(True)
        self.output_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.output_list.customContextMenuRequested.connect(self.showOutputMenu)
        self.output_list.currentItemChanged.connect(self.outputSelected)
        self.output_list.itemDoubleClicked.connect(self.openSelectedOutput)
        history_layout.addWidget(self.output_list, 1)
        self.history_sidebar.setHidden(True)

        if self.input_widgets:
            splitter.addWidget(inputs_scroll_area)
        splitter.addWidget(workspace)
        splitter.addWidget(self.history_sidebar)
        splitter.setSizes([600, 710, 0] if self.input_widgets else [1080, 0])

        self.button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.run_button = self.button_box.addButton("Run", QDialogButtonBox.AcceptRole)
        run_icon_path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "play.png"
        )
        self.run_button.setIcon(self.core.media.getColoredIcon(run_icon_path))
        self.run_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.run_button.customContextMenuRequested.connect(self.showRunMenu)
        close_button = self.button_box.button(QDialogButtonBox.Cancel)
        close_icon_path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "delete.png"
        )
        close_button.setIcon(self.core.media.getColoredIcon(close_icon_path))
        self.button_box.accepted.connect(self.run_workflow)
        self.button_box.rejected.connect(self.close)
        layout.addWidget(self.button_box)
        self.resize(1080, 680)

    def setHistoryVisible(self, visible):
        self.history_sidebar.setVisible(visible)
        if visible:
            self.refresh_history()

    def _parse_exposed_input(self, exposed_input):
        if isinstance(exposed_input, dict):
            exposed_input = exposed_input.get("value")

        if not isinstance(exposed_input, (list, tuple)) or not exposed_input:
            return None

        identifier = exposed_input[0]
        if not isinstance(identifier, str):
            return None

        parts = identifier.rsplit(":", 2)
        if len(parts) != 3 or parts[1] not in self.nodes:
            return None

        metadata = exposed_input[2] if len(exposed_input) > 2 else {}
        description = metadata.get("description") if isinstance(metadata, dict) else ""
        input_data = next(
            (
                item for item in self.nodes[parts[1]].get("inputs") or []
                if item.get("name") == parts[2]
                or (item.get("widget") or {}).get("name") == parts[2]
            ),
            {},
        )
        node_label = input_data.get("label")
        linear_label = exposed_input[1] if len(exposed_input) > 1 else ""
        display_name = description or node_label or linear_label or parts[2]
        return parts[1], parts[2], str(display_name)

    def _get_input_value(self, node_id, input_name):
        node = self.nodes[node_id]
        named_values = node.get("widgets_values_named") or {}
        if input_name in named_values:
            return named_values[input_name]

        for index, input_data in enumerate(node.get("inputs") or []):
            widget = input_data.get("widget") or {}
            widget_name = widget.get("name") if isinstance(widget, dict) else None
            if input_name == widget_name or input_name == input_data.get("name"):
                values = node.get("widgets_values") or []
                return values[index] if index < len(values) else ""
        return ""

    def _create_input_widget(self, node_id, input_name, value):
        if isinstance(value, bool):
            widget = QCheckBox()
            widget.setChecked(value)
        elif isinstance(value, int):
            widget = QSpinBox()
            widget.setRange(-2147483648, 2147483647)
            widget.setValue(value)
        elif isinstance(value, float):
            widget = QDoubleSpinBox()
            widget.setRange(-1000000000.0, 1000000000.0)
            widget.setDecimals(6)
            widget.setValue(value)
        elif self._is_reference_input(node_id, input_name):
            widget = ComfyAppFileInput(self, str(value))
        elif any(
            name_part in {"prompt", "text", "positive", "negative"}
            for name_part in input_name.lower().split(".")
        ) or (
            isinstance(value, str) and ("\n" in value or len(value) > 160)
        ):
            widget = QPlainTextEdit()
            widget.setPlainText(value)
            widget.setMinimumHeight(100)
        else:
            widget = QLineEdit(str(value))
        return widget

    def _is_reference_input(self, node_id, input_name):
        node_type = str(self.nodes[node_id].get("type", "")).lower()
        return node_type.startswith("load") and input_name.lower() in {
            "image", "video", "audio", "file", "filepath", "path"
        }

    def _widget_value(self, widget):
        if isinstance(widget, ComfyAppFileInput):
            return widget.text()
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        if isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
            return widget.value()
        if isinstance(widget, QPlainTextEdit):
            return widget.toPlainText()
        return widget.text()

    def showRunMenu(self, pos):
        menu = QMenu(self.run_button)
        menu.addAction("Run on ComfyUI Cloud", lambda: self.run_workflow(cloud=True))
        menu.exec_(self.run_button.mapToGlobal(pos))

    def run_workflow(self, cloud=False):
        inputs = {}
        for (node_id, input_name), widget in self.input_widgets.items():
            inputs.setdefault(node_id, {})[input_name] = self._widget_value(widget)

        self.run_button.setEnabled(False)
        self.status_label.setText(
            "Submitting ComfyUI workflow to cloud..." if cloud else "Submitting ComfyUI workflow..."
        )
        self._setOutputLoading(True)
        self.worker = ComfyAppWorkflowWorker(
            self.plugin, self.filepath, inputs, self.output_dir, self.workflow_id, cloud=cloud
        )
        self.worker.resultReady.connect(self.workflow_finished)
        self.worker.start()

    def workflow_finished(self, result):
        self.run_button.setEnabled(True)
        self._setOutputLoading(False)
        if result.get("error"):
            self.status_label.setText("Workflow failed.")
            self.core.popup(result["error"], parent=self)
            return

        files = result.get("downloaded_files") or []
        if not files:
            self.status_label.setText("Workflow completed, but produced no downloadable media.")
            return

        self.status_label.setText("Workflow completed.")
        self.pending_model_previews.update(
            filepath for filepath in files
            if os.path.splitext(filepath)[1].lower() in self.model_extensions
        )
        self.addOutputFiles(files, select=True)
        self.refresh_history()

    def browseReferenceFile(self, widget):
        path = QFileDialog.getOpenFileName(
            self, "Select Reference File", widget.text() or self.core.projectPath,
            "All files (*.*)",
        )[0]
        if path:
            widget.setText(self.core.fixPath(path))

    def saveClipboardPixmap(self, pixmap):
        path = os.path.join(self.output_dir, "reference_%s.png" % uuid.uuid4().hex)
        return path if pixmap.save(path, "PNG") else ""

    def captureScreen(self):
        from PrismUtils import ScreenShot

        self.setWindowOpacity(0)
        pixmap = ScreenShot.grabScreenArea(self.core)
        self.setWindowOpacity(1)
        return pixmap

    def addOutputFiles(self, files, select=False):
        known_paths = {
            self.output_list.item(index).data(Qt.UserRole)
            for index in range(self.output_list.count())
        }
        first_item = None
        for filepath in files:
            if not filepath or filepath in known_paths or not os.path.isfile(filepath):
                continue
            item = QListWidgetItem(os.path.basename(filepath))
            item.setData(Qt.UserRole, filepath)
            item.setToolTip(self._getOutputTooltip(filepath))
            item.setIcon(QIcon(self.getThumbnail(filepath)))
            self.output_list.addItem(item)
            known_paths.add(filepath)
            first_item = first_item or item
        if select and first_item:
            self.output_list.setCurrentItem(first_item)

    def _getOutputTooltip(self, filepath):
        try:
            details = os.stat(filepath)
            created = QDateTime.fromSecsSinceEpoch(int(details.st_mtime)).toString(
                "yyyy-MM-dd HH:mm:ss"
            )
            size_kb = details.st_size / 1024.0
            return "\n".join([
                os.path.basename(filepath),
                "Created: %s" % created,
                "Size: %.1f KB" % size_kb,
            ])
        except OSError:
            return filepath

    def refresh_history(self):
        if self.history_worker and self.history_worker.isRunning():
            return
        self.history_worker = ComfyAppHistoryWorker(
            self.plugin, self.workflow_id, self.output_dir
        )
        self.history_worker.resultReady.connect(self.addOutputFiles)
        self.history_worker.start()

    def getThumbnail(self, filepath):
        pixmap = QPixmap()
        thumbnail_path = self.core.media.getThumbnailPath(filepath)
        if os.path.isfile(thumbnail_path):
            try:
                pixmap = self.core.media.getPixmapFromPath(thumbnail_path)
            except Exception:
                pixmap = QPixmap()
        try:
            if not pixmap or pixmap.isNull():
                pixmap = self.core.media.getPixmapFromPath(filepath)
        except Exception:
            pass
        if not pixmap or pixmap.isNull():
            pixmap = self.core.media.emptyPrvPixmap

        return pixmap.scaled(132, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def _setOutputLoading(self, loading):
        if loading:
            self.output_loading_active = True
            self.media_player.hide()
            self.preview_message.hide()
            self.model_drag_button.hide()
            self._setPreviewTransportVisible(False)
            self._clearUsdPreview()
            self._positionPreviewOverlays()
            self.output_loading.show()
            self.output_loading.raise_()
            self.output_loading_movie.start()
        else:
            self.output_loading_active = False
            self.output_loading_movie.stop()
            self.output_loading.hide()
            self.updatePreview()

    def _updateOutputLoadingFrame(self, frame_number):
        pixmap = self.output_loading_movie.currentPixmap()
        if pixmap.isNull():
            return

        self.output_loading_label.setPixmap(
            pixmap.scaled(
                self.output_loading_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def _positionPreviewOverlays(self):
        preview = self.output_loading.parentWidget()
        self.output_loading.setGeometry(preview.rect())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._positionPreviewOverlays()

    def _saveOutputPreview(self, filepath, pixmap):
        if not pixmap or pixmap.isNull():
            return

        thumbnail_path = self.core.media.getThumbnailPath(filepath)
        preview = self.core.media.scalePixmap(
            pixmap, 264, 192, fitIntoBounds=False, crop=True
        )
        self.core.media.savePixmap(preview, thumbnail_path)
        self._refreshOutputThumbnail(filepath)

    def _refreshOutputThumbnail(self, filepath):
        for index in range(self.output_list.count()):
            item = self.output_list.item(index)
            if item.data(Qt.UserRole) == filepath:
                item.setIcon(QIcon(self.getThumbnail(filepath)))
                break

    def captureOutputPreview(self, filepath):
        pixmap = self.captureScreen()
        if pixmap:
            self._saveOutputPreview(filepath, pixmap)

    def browseOutputPreview(self, filepath):
        path = QFileDialog.getOpenFileName(
            self, "Select Preview Image", os.path.dirname(filepath),
            "Image Files (*.jpg *.jpeg *.png *.exr)",
        )[0]
        if not path:
            return

        pixmap = self.core.media.getPixmapFromPath(path)
        if not pixmap or pixmap.isNull():
            self.core.popup("Cannot read image: %s" % path, parent=self)
            return

        self._saveOutputPreview(filepath, pixmap)

    def pasteOutputPreview(self, filepath):
        pixmap = self.core.media.getPixmapFromClipboard()
        if not pixmap:
            self.core.popup("No image in clipboard.", parent=self)
            return

        self._saveOutputPreview(filepath, pixmap)

    def outputSelected(self, current, previous):
        self.selected_output = current.data(Qt.UserRole) if current else ""
        self.updatePreview()

    def updatePreview(self):
        if self.output_loading_active:
            return

        filepath = self.selected_output
        is_model = os.path.splitext(filepath)[1].lower() in self.model_extensions
        is_video = os.path.splitext(filepath)[1].lower() in {
            item.lower() for item in self.core.media.videoFormats
        }
        self._setOutputMediaSpacerVisible(is_video)
        self.model_drag_button.setFilepath(filepath if is_model else "")
        self._positionPreviewOverlays()
        if is_model:
            self._setPreviewTransportVisible(False)
            self._showUsdPreview(filepath)
        else:
            self._clearUsdPreview()
            has_output = bool(filepath)
            self.media_player.setVisible(has_output)
            self.preview_message.setVisible(not has_output)
            if has_output:
                self.media_player.updatePreview()
            self._setPreviewTransportVisible(has_output and not self._isSingleImage(filepath))

    def getCurRenders(self):
        return [{"path": self.selected_output}] if self.selected_output else []

    def getCurrentVersions(self):
        return []

    def _isSingleImage(self, filepath):
        extension = os.path.splitext(filepath)[1].lower()
        if extension in [item.lower() for item in self.core.media.videoFormats]:
            return False
        try:
            sequence = self.core.media.getSequenceFromFilename(filepath)
            files = self.core.media.getFilesFromSequence(sequence)
            return len(files) <= 1
        except Exception:
            return True

    def _setPreviewTransportVisible(self, visible):
        self.media_player.w_timeslider.setVisible(visible)
        self.media_player.w_playerCtrls.setVisible(visible)

    def _setOutputMediaSpacerVisible(self, visible):
        self.output_media_spacer.changeSize(
            0,
            0,
            QSizePolicy.Minimum,
            QSizePolicy.Expanding if visible else QSizePolicy.Fixed,
        )
        self.workspace_layout.setStretch(0, 0 if visible else 1)
        self.workspace_layout.setStretch(2, 1 if visible else 0)
        self.workspace_layout.invalidate()

    def _showUsdPreview(self, filepath):
        self.media_player.setVisible(False)
        self.preview_message.setVisible(False)
        self._clearUsdPreview()
        usd_plugin = self.core.getPlugin("USD")
        if not usd_plugin or not getattr(usd_plugin, "api", None):
            self.preview_message.setText("USD preview is unavailable in this application.")
            self.preview_message.setVisible(True)
            return
        try:
            self.quickview = usd_plugin.api.getQuickView(path=filepath, parent=self)
        except Exception as exc:
            logger.warning("Failed to create USD quick view: %s", exc)
            self.quickview = None
        if self.quickview:
            self.preview_layout.insertWidget(1, self.quickview)
            self._captureGeneratedModelPreview(filepath, self.quickview)
        else:
            self.preview_message.setText("Unable to preview this model.")
            self.preview_message.setVisible(True)

    def _clearUsdPreview(self):
        quickview = self.quickview
        self.quickview = None
        if not quickview:
            return

        is_object_valid = getattr(self.core, "isObjectValid", None)
        if is_object_valid:
            try:
                if not is_object_valid(quickview):
                    return
            except RuntimeError:
                return

        try:
            self.preview_layout.removeWidget(quickview)
            quickview.close()
            quickview.deleteLater()
        except RuntimeError:
            logger.debug("USD quick view was deleted before preview cleanup.")

    def _captureGeneratedModelPreview(self, filepath, quickview):
        if filepath not in self.pending_model_previews:
            return

        self.pending_model_previews.discard(filepath)
        if os.path.isfile(self.core.media.getThumbnailPath(filepath)):
            return

        QTimer.singleShot(
            500,
            lambda: self._captureQuickviewPreview(filepath, quickview),
        )

    def _captureQuickviewPreview(self, filepath, quickview):
        if self.quickview is not quickview or self.selected_output != filepath:
            return

        is_object_valid = getattr(self.core, "isObjectValid", None)
        if is_object_valid and not is_object_valid(quickview):
            return

        try:
            image = quickview.view.grabFrameBuffer()
            pixmap = QPixmap.fromImage(image)
        except Exception as exc:
            logger.warning("Failed to capture ComfyUI model preview: %s", exc)
            return

        self._saveOutputPreview(filepath, pixmap)

    def showOutputMenu(self, pos):
        item = self.output_list.itemAt(pos)
        menu = QMenu(self.output_list)
        if item:
            filepath = item.data(Qt.UserRole)
            menu.addAction("Open", self.openSelectedOutput)
            menu.addAction("Open in explorer", lambda: self.core.openFolder(filepath))
            menu.addAction("Copy Path", lambda: self.core.copyToClipboard(filepath))
            menu.addSeparator()
            menu.addAction("Capture Preview", lambda: self.captureOutputPreview(filepath))
            menu.addAction("Browse Preview...", lambda: self.browseOutputPreview(filepath))
            menu.addAction("Paste Preview", lambda: self.pasteOutputPreview(filepath))
            menu.addSeparator()
        menu.addAction("Clear Session Outputs", self.clearSessionOutputs)
        menu.exec_(self.output_list.mapToGlobal(pos))

    def clearSessionOutputs(self):
        self.output_list.clear()
        self.selected_output = ""
        self.updatePreview()

    def openSelectedOutput(self):
        if self.selected_output:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.selected_output))

    def closeEvent(self, event):
        self._clearUsdPreview()
        super().closeEvent(event)


class ComfyReadMediaDialog(QDialog):
    mediaSelected = Signal(object)

    def __init__(self, parent):
        super().__init__()
        self.plugin = parent
        self.core = self.plugin.core
        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self):
        import MediaBrowser

        filepath = self.core.getCurrentFileName()
        entity = self.core.getScenefileData(filepath)
        title = "Select Version"
        self.setWindowTitle(title)
        self.core.parentWindow(self)

        self.w_browser = MediaBrowser.MediaBrowser(core=self.core)
        self.w_browser.headerHeightSet = True
        self.w_browser.lw_version.itemDoubleClicked.disconnect()
        self.w_browser.lw_version.itemDoubleClicked.connect(self.itemDoubleClicked)

        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Select Version", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Cancel", QDialogButtonBox.RejectRole)
        self.bb_main.clicked.connect(self.buttonClicked)

        self.lo_main.addWidget(self.w_browser)
        self.lo_main.addWidget(self.bb_main)

        if entity and entity.get("type") in ["asset", "shot"]:
            self.w_browser.navigate([entity])

    @err_catcher(name=__name__)
    def itemDoubleClicked(self, item):
        self.buttonClicked("select")

    @err_catcher(name=__name__)
    def buttonClicked(self, button):
        isSelect = button == "select"
        if not isSelect and hasattr(button, "text"):
            isSelect = button.text() == "Select Version"

        if isSelect:
            data = self.w_browser.getCurrentSource()
            if not data:
                data = self.w_browser.getCurrentAOV()
                if not data:
                    data = self.w_browser.getCurrentVersion()
                    if not data:
                        data = self.w_browser.getCurrentIdentifier()

            if not data:
                self.core.popup("Invalid version selected.", parent=self)
                return

            self.mediaSelected.emit(data)

        self.close()
