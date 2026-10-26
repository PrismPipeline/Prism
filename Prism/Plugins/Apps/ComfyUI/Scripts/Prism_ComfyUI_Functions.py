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
import time
import shutil
import logging
import base64
import glob
import json
import mimetypes
import re
import tempfile
import urllib.error
import urllib.request
import uuid
from typing import Optional, Any

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher as err_catcher


logger = logging.getLogger(__name__)


class Prism_ComfyUI_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        
        self._capture_responses = {}  # Store capture responses by temp_path
        self._comfyWorkflowToPrismWorkflow = {}
        self._lastOpenedPrismWorkflowPath = ""
        self._currentWorkflowInfoRequestId = None
        self._currentWorkflowInfoResponse = {}
        self._currentWorkflowInfoLoop = None
        self.core.registerCallback("onEntityWidgetCreated", self.onEntityWidgetCreated, plugin=self)

    @err_catcher(name=__name__)
    def onEntityWidgetCreated(self, origin):
        for page in origin.pages:
            page.tw_tree.selectionModel().selectionChanged.connect(lambda x, y, p=page: self.onItemChanged(p, x, y))

    @err_catcher(name=__name__)
    def onItemChanged(self, origin, selected=None, deselected=None):
        for index in selected.indexes():
            item = origin.tw_tree.itemFromIndex(index)
            widget = origin.tw_tree.itemWidget(item, 0)
            if widget:
                widget.setStyleSheet("color: rgb(5, 5, 5);")

        for index in deselected.indexes():
            item = origin.tw_tree.itemFromIndex(index)
            widget = origin.tw_tree.itemWidget(item, 0)
            if widget:
                widget.setStyleSheet("")

    @err_catcher(name=__name__)
    def startup(self, origin):
        origin.timer.stop()
        self.core.setActiveStyleSheet("ComfyUI")
        origin.messageParent = QWidget()
        if self.core.useOnTop:
            origin.messageParent.setWindowFlags(
                origin.messageParent.windowFlags() ^ Qt.WindowStaysOnTopHint
            )

    def _normalizeWorkflowPathKey(self, workflowPath):
        if not workflowPath:
            return ""

        normalized = str(workflowPath).replace("\\", "/").strip()
        if normalized.startswith("./"):
            normalized = normalized[2:]

        while normalized.startswith("/"):
            normalized = normalized[1:]

        return normalized

    def _rememberWorkflowPathMapping(self, comfyWorkflowPath, prismWorkflowPath):
        if not prismWorkflowPath:
            return

        normalizedPrismPath = os.path.normpath(prismWorkflowPath).replace("\\", "/")
        keyCandidates = set()

        normalizedComfyPath = self._normalizeWorkflowPathKey(comfyWorkflowPath)
        if normalizedComfyPath:
            keyCandidates.add(normalizedComfyPath)
            keyCandidates.add(os.path.basename(normalizedComfyPath))

        baseName = os.path.basename(normalizedPrismPath)
        if baseName:
            keyCandidates.add(baseName)
            keyCandidates.add("workflows/%s" % baseName)
            keyCandidates.add("user/default/workflows/%s" % baseName)

            comfyRoot = self.getComfyUIRootFolder()
            if comfyRoot:
                comfyAbsolute = os.path.join(comfyRoot, "user", "default", "workflows", baseName)
                keyCandidates.add(self._normalizeWorkflowPathKey(comfyAbsolute))

        for key in keyCandidates:
            normalizedKey = self._normalizeWorkflowPathKey(key)
            if normalizedKey:
                self._comfyWorkflowToPrismWorkflow[normalizedKey] = normalizedPrismPath

        self._lastOpenedPrismWorkflowPath = normalizedPrismPath

    def _resolvePrismWorkflowPath(self, comfyWorkflowPath):
        normalizedComfyPath = self._normalizeWorkflowPathKey(comfyWorkflowPath)
        if not normalizedComfyPath:
            return ""

        if normalizedComfyPath in self._comfyWorkflowToPrismWorkflow:
            return self._comfyWorkflowToPrismWorkflow[normalizedComfyPath]

        baseName = os.path.basename(normalizedComfyPath)
        return self._comfyWorkflowToPrismWorkflow.get(baseName, "")

    def _requestCurrentWorkflowInfoFromComfyUI(self, timeoutMs=2000):
        wsServer = getattr(self, "ws_server", None)
        if wsServer is None:
            return {}

        self._currentWorkflowInfoRequestId = uuid.uuid4().hex
        self._currentWorkflowInfoResponse = {}
        self._currentWorkflowInfoLoop = QEventLoop()

        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(self._currentWorkflowInfoLoop.quit)
        timer.start(timeoutMs)

        wsServer.send_command(
            {
                "action": "get_current_workflow_info",
                "request_id": self._currentWorkflowInfoRequestId,
            }
        )
        self._currentWorkflowInfoLoop.exec_()

        timer.stop()
        self._currentWorkflowInfoLoop = None
        self._currentWorkflowInfoRequestId = None
        return self._currentWorkflowInfoResponse or {}

    @err_catcher(name=__name__)
    def onCurrentWorkflowInfo(self, response):
        requestId = response.get("request_id")
        if self._currentWorkflowInfoRequestId and requestId != self._currentWorkflowInfoRequestId:
            return

        self._currentWorkflowInfoResponse = response

        comfyWorkflowPath = response.get("path") or ""
        if comfyWorkflowPath and self._lastOpenedPrismWorkflowPath:
            self._rememberWorkflowPathMapping(comfyWorkflowPath, self._lastOpenedPrismWorkflowPath)

        if self._currentWorkflowInfoLoop and self._currentWorkflowInfoLoop.isRunning():
            self._currentWorkflowInfoLoop.quit()

    @err_catcher(name=__name__)
    def getCurrentFileName(self, origin, path=True):
        workflowInfo = self._requestCurrentWorkflowInfoFromComfyUI()
        comfyWorkflowPath = workflowInfo.get("path") or ""

        prismWorkflowPath = self._resolvePrismWorkflowPath(comfyWorkflowPath)
        if not prismWorkflowPath and self._lastOpenedPrismWorkflowPath:
            prismWorkflowPath = self._lastOpenedPrismWorkflowPath

        if not prismWorkflowPath:
            return ""

        return prismWorkflowPath if path else os.path.basename(prismWorkflowPath)

    @err_catcher(name=__name__)
    def getSceneExtension(self, origin):
        return self.sceneFormats[0]

    def getComfyUIRootFolder(self):
        envRoot = os.getenv("PRISM_COMFYUI_PATH", "")
        if envRoot:
            return envRoot

        return getattr(self, "comfyui_root", "")

    @err_catcher(name=__name__)
    def setComfyUIRootFolder(self, root_path):
        self.comfyui_root = root_path

    @err_catcher(name=__name__)
    def captureViewportThumbnail(self) -> Optional[Any]:
        """Capture ComfyUI node graph as thumbnail image.
        
        Returns:
            QPixmap of viewport capture or None if failed.
        """
        try:
            logger.debug("Starting ComfyUI viewport thumbnail capture")

            # Method 1: Try to find and capture the ComfyUI window specifically
            logger.debug("Trying window capture method")
            comfyui_window = self._findComfyUIWindow()
            if comfyui_window:
                pixmap = self._captureWindow(comfyui_window)
                if pixmap and not pixmap.isNull():
                    logger.debug(f"Window capture successful: {pixmap.width()}x{pixmap.height()}")
                    return pixmap
            logger.debug("Window capture failed, trying screen fallback")
            
            # Method 2: Fallback to screen capture with better targeting
            logger.debug("Trying screen fallback capture method")
            pixmap = self._captureScreenFallback()
            if pixmap and not pixmap.isNull():
                logger.debug(f"Screen fallback capture successful: {pixmap.width()}x{pixmap.height()}")
                return pixmap
            
            logger.warning("All capture methods failed")
            return None
            
        except Exception as e:
            logger.error(f"Error capturing viewport thumbnail: {e}")
            return None

    def _captureViaComfyUIAPI(self) -> Optional[QPixmap]:
        """Try to capture via ComfyUI WebSocket API."""
        try:
            # Create a unique temp path to identify this capture request
            temp_path = os.path.join(os.getenv("TEMP", "/tmp"), f"comfyui_canvas_capture_{int(time.time())}.png")
            command = {
                "action": "capture_canvas",
                "output_path": temp_path
            }
            
            # Clear any previous response for this path
            self._capture_responses.pop(temp_path, None)
            
            # Register a temporary response handler if the WebSocket server supports it
            if hasattr(self.ws_server, 'add_response_handler'):
                def handle_capture_response(response):
                    if (response.get('action') == 'capture_canvas' and 
                        response.get('path') == temp_path):
                        self._capture_responses[temp_path] = response
                        
                self.ws_server.add_response_handler(handle_capture_response)
            
            logger.debug(f"Sending capture command for path: {temp_path}")
            self.ws_server.send_command(command)
            
            # Wait for either file creation (backend endpoint) or WebSocket response
            for i in range(50):  # Wait up to 5 seconds
                # Check if file was created (backend endpoint worked)
                if os.path.exists(temp_path):
                    pixmap = QPixmap(temp_path)
                    try:
                        os.remove(temp_path)  # Clean up
                    except:
                        pass
                    if not pixmap.isNull():
                        logger.debug(f"ComfyUI API file capture successful: {pixmap.width()}x{pixmap.height()}")
                        return pixmap
                
                # Check if WebSocket response was received
                if temp_path in self._capture_responses:
                    response = self._capture_responses.pop(temp_path)
                    return self._processWebSocketCaptureResponse(response)
                
                QApplication.processEvents()
                time.sleep(0.2)
                
            logger.debug("ComfyUI API capture timed out - no file or WebSocket response received")
            return None
            
        except Exception as e:
            logger.debug(f"ComfyUI API capture failed: {e}")
            return None
    
    def _processWebSocketCaptureResponse(self, response) -> Optional[QPixmap]:
        """Process WebSocket response containing image data."""
        try:
            # Check if JavaScript is requesting fallback to screen capture
            if response.get('use_fallback'):
                logger.debug("JavaScript requested fallback to screen capture")
                return None
                
            if response.get('status') != 'success':
                logger.debug(f"WebSocket capture failed: {response.get('message', 'Unknown error')}")
                return None
                
            image_data = response.get('image_data')
            if not image_data:
                logger.debug("No image data in WebSocket response")
                return None
            
            # Extract base64 data from data URL (format: "data:image/png;base64,...")
            if image_data.startswith('data:image/'):
                # Find the base64 part after the comma
                comma_index = image_data.find(',')
                if comma_index != -1:
                    base64_data = image_data[comma_index + 1:]
                else:
                    base64_data = image_data
            else:
                base64_data = image_data
            
            # Fix base64 padding if necessary
            # Base64 strings must be multiples of 4 characters, padded with '='
            missing_padding = len(base64_data) % 4
            if missing_padding:
                base64_data += '=' * (4 - missing_padding)
            
            logger.debug(f"Processing base64 data: {len(base64_data)} characters")
            
            # Decode base64 to bytes
            image_bytes = base64.b64decode(base64_data)
            logger.debug(f"Decoded image data: {len(image_bytes)} bytes")
            
            # Create QPixmap from bytes
            pixmap = QPixmap()
            if pixmap.loadFromData(image_bytes):
                logger.debug(f"WebSocket capture successful: {pixmap.width()}x{pixmap.height()}")
                return pixmap
            else:
                logger.debug("Failed to create QPixmap from WebSocket image data")
                return None
                
        except Exception as e:
            logger.debug(f"Failed to process WebSocket capture response: {e}")
            return None
    
    def handleWebSocketResponse(self, response):
        """Handle incoming WebSocket responses. Call this from your WebSocket message handler."""
        try:
            if response.get('action') == 'capture_canvas':
                path = response.get('path')
                if path:
                    self._capture_responses[path] = response
                    logger.debug(f"Received capture response for path: {path}")
        except Exception as e:
            logger.debug(f"Error handling WebSocket response: {e}")

    def _findComfyUIWindow(self):
        """Find the ComfyUI window handle."""
        try:
            if sys.platform == "win32":
                import win32gui
                
                def enum_windows_proc(hwnd, windows):
                    if win32gui.IsWindowVisible(hwnd):
                        window_title = win32gui.GetWindowText(hwnd).lower()
                        print(f"Checking window: {window_title}")
                        # Look for ComfyUI window titles
                        if ("comfyui" in window_title or 
                            "comfy ui" in window_title or 
                            "127.0.0.1:8188" in window_title or
                            "localhost:8188" in window_title):
                            windows.append(hwnd)
                    return True
                
                windows = []
                win32gui.EnumWindows(enum_windows_proc, windows)
                if windows:
                    logger.debug(f"Found ComfyUI window: {windows[0]}")
                    return windows[0]
                
            # For Linux/Mac, you'd need different approaches
            return None
            
        except Exception as e:
            logger.debug(f"Failed to find ComfyUI window: {e}")
            return None

    def _captureWindow(self, window_handle) -> Optional[QPixmap]:
        """Capture the screen containing a specific ComfyUI window."""
        try:
            if sys.platform == "win32":
                import win32gui
                
                rect = win32gui.GetWindowRect(window_handle)
                x, y, x2, y2 = rect
                width = x2 - x
                height = y2 - y

                center = QPoint(x + width // 2, y + height // 2)
                screen = QGuiApplication.screenAt(center)
                if screen is None:
                    screen = QGuiApplication.primaryScreen()
                if screen:
                    geometry = screen.geometry()
                    margin_x = int(geometry.width() * 0.2)
                    margin_y = int(geometry.height() * 0.2)
                    capture_width = geometry.width() - (margin_x * 2)
                    capture_height = geometry.height() - (margin_y * 2)
                    logger.debug(
                        "Capturing %sx%s center of ComfyUI screen %sx%s at (%s, %s) for window at (%s, %s).",
                        capture_width,
                        capture_height,
                        geometry.width(),
                        geometry.height(),
                        geometry.x(),
                        geometry.y(),
                        x,
                        y,
                    )
                    pbHidden = False
                    if self.core.pb:
                        self.core.pb.hide()
                        QApplication.processEvents()
                        time.sleep(0.2)
                        pbHidden = True

                    pixmap = screen.grabWindow(
                        0, margin_x, margin_y, capture_width, capture_height
                    )
                    if pbHidden:
                        self.core.pb.show()

                    if not pixmap.isNull():
                        logger.debug(f"Window capture successful: {pixmap.width()}x{pixmap.height()}")
                        return pixmap
                        
        except Exception as e:
            logger.debug(f"Window capture failed: {e}")
            return None

    def _captureScreenFallback(self) -> Optional[QPixmap]:
        """Capture the primary screen when no ComfyUI window can be found."""
        try:
            screen = QGuiApplication.primaryScreen()
            if not screen:
                logger.debug("No screen available for capture")
                return None
                
            geometry = screen.geometry()
            margin_x = int(geometry.width() * 0.2)
            margin_y = int(geometry.height() * 0.2)
            capture_width = geometry.width() - (margin_x * 2)
            capture_height = geometry.height() - (margin_y * 2)
            logger.debug(
                "Capturing %sx%s center of primary screen %sx%s at (%s, %s).",
                capture_width,
                capture_height,
                geometry.width(),
                geometry.height(),
                geometry.x(),
                geometry.y(),
            )
            pixmap = screen.grabWindow(
                0, margin_x, margin_y, capture_width, capture_height
            )
            if not pixmap.isNull():
                logger.debug(f"Screen capture successful: {pixmap.width()}x{pixmap.height()}")
                return pixmap
            else:
                logger.debug("Screen capture produced null pixmap")
                return None
            
        except Exception as e:
            logger.debug(f"Screen capture fallback failed: {e}")
            return None

    @err_catcher(name=__name__)
    def saveScene(self, origin, filepath, details={}):
        command = {
            "action": "save_workflow",
            "path": os.path.basename(filepath),
        }
        self.ws_server.send_command(command)
        base = self.getComfyUIRootFolder() + r"/user/default/workflows"
        userfilepath = base + "/" + os.path.basename(filepath)
        self._rememberWorkflowPathMapping(userfilepath, filepath)
        idx = 0
        copied = False
        while idx < 10:
            if os.path.exists(userfilepath):
                shutil.copy2(userfilepath, filepath)
                copied = True
                break

            idx += 1
            time.sleep(0.5)

        if not copied:
            logger.warning(f"Failed to save workflow to {userfilepath} after 10 attempts.")
        else:
            logger.debug(f"Workflow saved to {filepath} successfully.")

    @err_catcher(name=__name__)
    def openScene(self, origin, filepath, force=False):
        _, ext = os.path.splitext(filepath)
        if ext.lower() != self.getSceneExtension(origin):
            logger.warning(f"File extension {ext} does not match expected scene extension {self.getSceneExtension(origin)}")
            return

        base = self.getComfyUIRootFolder() + r"/user/default/workflows"
        userfilepath = base + "/" + os.path.basename(filepath)
        self._rememberWorkflowPathMapping(userfilepath, filepath)
        if os.path.exists(userfilepath):
            try:
                os.remove(userfilepath)
            except:
                pass

        try:
            shutil.copy2(filepath, userfilepath)
        except Exception as e:
            if not os.path.exists(filepath):
                msg = f"Source workflow file does not exist: {filepath}"
            else:
                msg = f"Failed to copy workflow to {userfilepath}: {e}"

            self.core.popup(msg)
            return False

        command = {
            "action": "open_workflow",
            "path": os.path.basename(filepath)
        }
        self.ws_server.send_command(command)
        return True

    @err_catcher(name=__name__)
    def getInputFolder(self):
        sharedInput = os.getenv("USERPROFILE", "") + r"\ComfyUI-Shared\input"
        if os.path.exists(sharedInput):
            return sharedInput.replace("\\", "/")

        return self.getComfyUIRootFolder() + "/input"

    @err_catcher(name=__name__)
    def _uploadFileToComfyUIInput(self, filepath, subfolder):
        import json
        import mimetypes
        import urllib.error
        import urllib.request
        import uuid

        server_address = "127.0.0.1:8188"
        if hasattr(self, "_get_local_config"):
            server_address = self._get_local_config()

        filename = os.path.basename(filepath)
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        boundary = "----PrismUpload%s" % uuid.uuid4().hex

        with open(filepath, "rb") as media_file:
            file_data = media_file.read()

        body = []
        body.append(("--%s\r\n" % boundary).encode("utf-8"))
        body.append(
            (
                'Content-Disposition: form-data; name="image"; filename="%s"\r\n'
                % filename
            ).encode("utf-8")
        )
        body.append(("Content-Type: %s\r\n\r\n" % mime_type).encode("utf-8"))
        body.append(file_data)
        body.append(b"\r\n")

        body.append(("--%s\r\n" % boundary).encode("utf-8"))
        body.append(b'Content-Disposition: form-data; name="subfolder"\r\n\r\n')
        body.append(subfolder.encode("utf-8"))
        body.append(b"\r\n")

        body.append(("--%s\r\n" % boundary).encode("utf-8"))
        body.append(b'Content-Disposition: form-data; name="type"\r\n\r\n')
        body.append(b"input")
        body.append(b"\r\n")

        body.append(("--%s--\r\n" % boundary).encode("utf-8"))
        payload = b"".join(body)

        request = urllib.request.Request(
            "http://%s/upload/image" % server_address,
            data=payload,
            headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise Exception(
                "Failed to upload media to ComfyUI (HTTP %s): %s" % (error.code, details)
            )
        except urllib.error.URLError as error:
            raise Exception("Failed to upload media to ComfyUI: %s" % error.reason)

        return result

    @err_catcher(name=__name__)
    def importImages(self, filepath=None, mediaBrowser=None, parent=None):
        if mediaBrowser:
            filepath = mediaBrowser.seq[mediaBrowser.getCurrentFrame()].replace("\\", "/")

        sequence_path = self.core.media.getSequenceFromFilename(filepath)
        sequence_files = self.core.media.getFilesFromSequence(sequence_path)
        if mediaBrowser and len(getattr(mediaBrowser, "seq", [])) > 1:
            sequence_files = mediaBrowser.seq

        if len(sequence_files) > 1:
            choice = self.core.popupQuestion(
                "The selected media is an image sequence with %s frames.\n\n"
                "How should it be imported into ComfyUI?" % len(sequence_files),
                title="Import Image Sequence",
                buttons=["First Frame", "Image Sequence", "Convert to Video", "Cancel"],
                default="Image Sequence",
                escapeButton="Cancel",
                parent=parent,
            )
            if choice == "Cancel" or not choice:
                return

            if choice == "First Frame":
                filepath = sequence_files[0]
            elif choice == "Image Sequence":
                uploaded = None
                for sequence_file in sequence_files:
                    upload_result = self._uploadFileToComfyUIInput(sequence_file, "")
                    if uploaded is None:
                        uploaded = upload_result

                if not uploaded:
                    return

                load_path = self._buildComfyUIInputPath(
                    uploaded, os.path.basename(sequence_files[0])
                )
                self.ws_server.send_command(
                    {"action": "load_sequence", "path": load_path}
                )
                return
            elif choice == "Convert to Video":
                start_frame = self.core.media.getFrameNumberFromFilename(
                    sequence_files[0]
                )
                start_frame = int(start_frame) if start_frame is not None else None
                output_dir = os.path.join(tempfile.gettempdir(), "Prism", "ComfyUI")
                output_name = "%s_%s.mp4" % (
                    os.path.splitext(os.path.basename(sequence_files[0]))[0],
                    uuid.uuid4().hex,
                )
                output_path = os.path.join(output_dir, output_name)
                ffmpeg_input_path = re.sub(
                    r"#+",
                    lambda match: "%%0%sd" % len(match.group(0)),
                    sequence_path,
                )
                self.core.media.convertMedia(
                    ffmpeg_input_path, start_frame, output_path
                )
                if not os.path.isfile(output_path):
                    self.core.popup(
                        "Failed to convert the image sequence to a video.",
                        parent=parent,
                    )
                    return
                filepath = output_path

        filename = os.path.basename(filepath)
        
        ext = os.path.splitext(filename)[1]
        # subfolder = "videos" if ext.lower() in self.core.media.videoFormats else "images"
        subfolder = ""

        logger.debug(
            "Uploading %s to ComfyUI input subfolder '%s'" % (filepath, subfolder)
        )
        upload_result = self._uploadFileToComfyUIInput(filepath, subfolder)

        uploaded_name = upload_result.get("name") or filename
        uploaded_subfolder = upload_result.get("subfolder", "")
        upload_type = upload_result.get("type", "input")

        load_path = uploaded_name
        if uploaded_subfolder:
            load_path = "%s/%s" % (uploaded_subfolder, uploaded_name)
        load_path = "%s [%s]" % (load_path, upload_type)

        command = {
            "action": "load_image",
            "path": load_path
        }
        self.ws_server.send_command(command)

    @err_catcher(name=__name__)
    def _getComfyUIServerAddress(self):
        return (
            self.core.getConfig("comfyui", "localServerAddress", config="user")
            or "127.0.0.1:8188"
        )

    @err_catcher(name=__name__)
    def _uploadToComfyUIInput(self, filepath, subfolder):
        filename = os.path.basename(filepath)
        mimeType = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        boundary = "----PrismUpload%s" % uuid.uuid4().hex

        with open(filepath, "rb") as mediaFile:
            fileData = mediaFile.read()

        body = []
        body.append(("--%s\r\n" % boundary).encode("utf-8"))
        body.append(
            (
                'Content-Disposition: form-data; name="image"; filename="%s"\r\n'
                % filename
            ).encode("utf-8")
        )
        body.append(("Content-Type: %s\r\n\r\n" % mimeType).encode("utf-8"))
        body.append(fileData)
        body.append(b"\r\n")

        body.append(("--%s\r\n" % boundary).encode("utf-8"))
        body.append(b'Content-Disposition: form-data; name="subfolder"\r\n\r\n')
        body.append(subfolder.encode("utf-8"))
        body.append(b"\r\n")

        body.append(("--%s\r\n" % boundary).encode("utf-8"))
        body.append(b'Content-Disposition: form-data; name="type"\r\n\r\n')
        body.append(b"input")
        body.append(b"\r\n")

        body.append(("--%s--\r\n" % boundary).encode("utf-8"))
        payload = b"".join(body)

        request = urllib.request.Request(
            "http://%s/upload/image" % self._getComfyUIServerAddress(),
            data=payload,
            headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise Exception(
                "Failed to upload to ComfyUI (HTTP %s): %s" % (error.code, details)
            )
        except urllib.error.URLError as error:
            raise Exception("Failed to upload to ComfyUI: %s" % error.reason)

    @err_catcher(name=__name__)
    def _buildComfyUIInputPath(self, uploadResult, fallbackFilename):
        uploadedName = uploadResult.get("name") or fallbackFilename
        uploadedSubfolder = uploadResult.get("subfolder", "")
        # uploadedType = uploadResult.get("type", "input")

        loadPath = uploadedName
        if uploadedSubfolder:
            loadPath = "%s/%s" % (uploadedSubfolder, uploadedName)

        return loadPath

    @err_catcher(name=__name__)
    def sm_import_importToApp(self, origin, doImport, update, impFileName):
        result = False
        base, ext = os.path.splitext(impFileName.lower())
        if ext not in [".gltf", ".glb", ".fbx", ".obj"]:
            globPath = base + ".*"
            matches = glob.glob(globPath)
            if matches:
                validMatches = [match for match in matches if os.path.splitext(match)[1].lower() in [".gltf", ".glb", ".fbx", ".obj"]]
                if validMatches:
                    impFileName = validMatches[0]
                    logger.debug(f"Found matching file for import: {impFileName}")
                else:
                    logger.warning(f"No valid matching file found for import: {globPath}")
                    return {"result": False, "doImport": doImport}
            else:
                logger.warning(f"No matching file found for import: {globPath}")
                return {"result": False, "doImport": doImport}
            
        filename = os.path.basename(impFileName)
        subfolder = "3d"
        uploadResult = self._uploadToComfyUIInput(impFileName, subfolder)
        loadPath = self._buildComfyUIInputPath(uploadResult, filename)

        command = {
            "action": "load_product",
            "path": loadPath,
        }
        self.ws_server.send_command(command)
        return {"result": True, "doImport": doImport}
