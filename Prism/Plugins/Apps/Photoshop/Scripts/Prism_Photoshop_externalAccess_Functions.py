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
import subprocess
import platform
import threading
import logging
import atexit
from typing import Any, List, Optional, Tuple, Union

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


logger = logging.getLogger(__name__)


class Prism_Photoshop_externalAccess_Functions(object):
    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize Photoshop external access functions.
        
        Sets up server, callbacks, and process tracking for communication
        between Prism and Photoshop.
        
        Args:
            core: Prism core instance
            plugin: Plugin instance (self)
        """
        self.core = core
        self.plugin = plugin        
        if platform.system() not in self.platforms:
            return

        self.photoshopInstanceProcess = None  # Track spawned Photoshop instance
        
        # Register cleanup handler for when Standalone closes
        if self.core.requestedApp == "Standalone":
            atexit.register(self.cleanupPhotoshopInstance)
        
        self.core.registerCallback(
            "projectBrowser_loadUI", self.projectBrowser_loadUI, plugin=self.plugin
        )
        self.core.registerCallback("getPresetScenes", self.getPresetScenes, plugin=self.plugin)
        ssheetPath = os.path.join(
            self.pluginDirectory,
            "UserInterfaces",
            "PhotoshopStyleSheet"
        )
        self.core.registerStyleSheet(ssheetPath)
        
        # Start server based on app mode
        if self.getUXPInstalled() or os.getenv("PRISM_PHOTOSHOP_LAUNCH_UXP_SERVER", "1") == "1":
            if self.core.requestedApp in ["Standalone", "Photoshop"]:
                self.startServer()

    @err_catcher(name=__name__)
    def userSettings_loadUI(self, origin: Any, tab: Any) -> None:
        """Load Photoshop-specific settings UI in Prism settings dialog.
        
        Adds UXP plugin install/remove buttons to the user settings tab.
        
        Args:
            origin: Settings dialog instance
            tab: Tab widget to add settings to
        """
        tab.lo_settings = QGridLayout()
        tab.layout().addLayout(tab.lo_settings)
        spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)

        origin.l_uxp = QLabel("Recommended for Photoshop 2026+:")
        origin.b_installUXP = QPushButton("Install UXP Plugin")
        origin.b_installUXP.clicked.connect(lambda: self.core.integration.addIntegration("Photoshop", "UXP"))
        origin.b_installUXP.clicked.connect(origin.refreshIntegrations)
        origin.b_removeUXP = QPushButton("Remove UXP Plugin")
        origin.b_removeUXP.clicked.connect(lambda: self.core.integration.removeIntegration("Photoshop", "UXP"))
        origin.b_removeUXP.clicked.connect(origin.refreshIntegrations)
        # origin.chb_mayaPluginPaths.setLayoutDirection(Qt.RightToLeft)

        tab.lo_settings.addWidget(origin.l_uxp, 0, 1)
        tab.lo_settings.addWidget(origin.b_installUXP, 0, 2)
        tab.lo_settings.addWidget(origin.b_removeUXP, 0, 3)
        tab.lo_settings.addItem(spacer, 1, 0)

    @err_catcher(name=__name__)
    def getUXPInstalled(self) -> bool:
        """Check if UXP plugin is installed.
        
        Returns:
            True if UXP plugin is in integration list, False otherwise
        """
        integrations = self.core.integration.getIntegrations() or {}
        return "UXP" in (integrations.get("Photoshop") or [])

    @err_catcher(name=__name__)
    def getUXPExe(self) -> str:
        """Get path to Adobe UPI installer agent executable.
        
        Returns:
            Path to UnifiedPluginInstallerAgent executable for the current platform
        """
        if platform.system() == "Windows":
            return r"C:\Program Files\Common Files\Adobe\Adobe Desktop Common\RemoteComponents\UPI\UnifiedPluginInstallerAgent\UnifiedPluginInstallerAgent.exe"

        if platform.system() == "Darwin":
            candidates = [
                "/Library/Application Support/Adobe/Adobe Desktop Common/RemoteComponents/UPI/UnifiedPluginInstallerAgent/UnifiedPluginInstallerAgent.app/Contents/MacOS/UnifiedPluginInstallerAgent",
                os.path.expanduser("~/Library/Application Support/Adobe/Adobe Desktop Common/RemoteComponents/UPI/UnifiedPluginInstallerAgent/UnifiedPluginInstallerAgent.app/Contents/MacOS/UnifiedPluginInstallerAgent"),
            ]
            for candidate in candidates:
                if os.path.exists(candidate):
                    return candidate

            return candidates[0]

        return ""

    @err_catcher(name=__name__)
    def createSignalBridge(self) -> Any:
        """Create a QObject bridge for cross-thread communication.
        
        Returns:
            SignalBridge instance for executing functions in main Qt thread
        """
        class SignalBridge(QObject):
            executeInMainThread = Signal(object)
            
            def __init__(self) -> None:
                """Initialize SignalBridge and connect signal to executor."""
                super(SignalBridge, self).__init__()
                self.executeInMainThread.connect(self._execute)
                
            def _execute(self, func: Any) -> None:
                """Execute a function in the main thread with error handling.
                
                Args:
                    func: Callable to execute in main thread
                """
                try:
                    func()
                except Exception as e:
                    logger.error(f"Error executing function in main thread: {str(e)}")
        
        return SignalBridge()

    @err_catcher(name=__name__)
    def startServer(self, port: Optional[int] = None) -> None:
        """Start Flask server to listen for commands from Photoshop UXP plugin.
        
        Creates HTTP server on localhost that receives commands from Photoshop.
        Uses port 6400 for Standalone, 6401 for Photoshop app mode.
        
        Args:
            port: TCP port number to listen on (auto-selected if None)
        """
        if getattr(self, "serverApp", None):
            logger.debug("Photoshop server already running")
            return

        if port is None:
            if self.core.requestedApp == "Standalone":
                port = 6400
            elif self.core.requestedApp == "Photoshop":
                port = 6401
            else:
                return

        extModPath = os.path.join(self.pluginDirectory, "ExternalModules")
        if sys.version[0] == "3":
            cpModPath = os.path.join(extModPath, "Python3")
            if cpModPath not in sys.path:
                sys.path.append(cpModPath)

        try:
            from flask import Flask, request, jsonify
            from flask_cors import CORS
        except Exception as e:
            logger.warning("failed to import flask: %s" % str(e))
            Flask = None

        """Start Flask server to listen for commands from Photoshop UXP plugin"""
        if Flask is None:
            logger.warning("unable to start Photoshop server: Flask not installed")
            return

        import flask.cli
        flask.cli.show_server_banner = lambda *args: None
        
        # Create signal bridge for cross-thread communication
        self.signalBridge = self.createSignalBridge()

        logger.debug("starting Photoshop flask server on port %d" % port)
        # Create Flask app
        app = Flask(__name__)
        CORS(app)  # Enable CORS for cross-origin requests
        
        # Disable Flask logging to console
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        
        self.serverApp = app
        self.serverPort = port
        
        @app.route('/prism', methods=['POST'])
        def handle_command():
            """Handle incoming commands from Photoshop plugin"""
            try:
                data = request.get_json()
                command = data.get('command')
                app_name = data.get('app', 'unknown')
                
                logger.debug(f"Received command from {app_name}: {command}")
                
                # Map commands to functions
                result = self.executeCommand(command)
                
                return jsonify({
                    'status': 'success',
                    'command': command,
                    'result': result
                }), 200
                
            except Exception as e:
                logger.error(f"Error handling command: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500
        
        @app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({'status': 'running'}), 200
        
        # Start server in background thread
        def run_server() -> None:
            """Run Flask server in background thread."""
            try:
                logger.info(f"Starting Prism server on http://localhost:{port}")
                app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
            except Exception as e:
                logger.error(f"Error starting server: {str(e)}")
                msg = "Failed to start Photoshop server on port %s.\n\n%s" % (port, str(e))
                if getattr(self, "signalBridge", None):
                    self.signalBridge.executeInMainThread.emit(
                        lambda m=msg: self.core.popup(m, severity="warning")
                    )
        
        self.serverThread = threading.Thread(target=run_server, daemon=True)
        self.serverThread.start()
        
    @err_catcher(name=__name__)
    def executeCommand(self, command):
        """Execute the command received from Photoshop"""
        command_map = {
            'connectPhotoshop': self.handleConnectPhotoshop,
            'disconnect': self.handleDisconnect,
            'saveVersion': self.handleSaveVersion,
            'saveExtended': self.handleSaveExtended,
            'export': self.handleExport,
            'projectBrowser': self.handleProjectBrowser,
            'settings': self.handleSettings
        }
        
        handler = command_map.get(command)
        if handler:
            return handler()
        else:
            return f"Unknown command: {command}"
    
    @err_catcher(name=__name__)
    def handleConnectPhotoshop(self):
        """Handle connection request from Photoshop UXP plugin"""
        logger.info("Photoshop connection requested")
        # Launch Photoshop-specific Prism instance
        self.signalBridge.executeInMainThread.emit(
            lambda: self.connectToPhotoshop(None, filepath="", mode="Background")
        )
        return "Photoshop instance launched"
    
    @err_catcher(name=__name__)
    def handleDisconnect(self):
        """Handle disconnect request from Photoshop"""
        logger.info("Photoshop disconnect requested - closing Prism instance")
        # Close this Prism instance
        if self.core.appPlugin.pluginName == "Photoshop":
            # Schedule the exit to allow response to be sent first
            QTimer.singleShot(500, lambda: sys.exit(0))
            return "Prism instance closing"
        return "Disconnect acknowledged"
    
    @err_catcher(name=__name__)
    def handleSaveVersion(self):
        """Handle Save Version command"""
        print("Save Version requested")
        self.signalBridge.executeInMainThread.emit(lambda: self.core.saveScene())
        return "Save Version executed"
    
    @err_catcher(name=__name__)
    def handleSaveExtended(self):
        """Handle Save Extended command"""
        print("Save Extended requested")
        self.signalBridge.executeInMainThread.emit(lambda: self.core.saveWithComment())
        return "Save Extended executed"
    
    @err_catcher(name=__name__)
    def handleExport(self):
        """Handle Export command"""
        print("Export requested")
        self.signalBridge.executeInMainThread.emit(lambda: self.core.appPlugin.exportImage())
        return "Export executed"
    
    @err_catcher(name=__name__)
    def handleProjectBrowser(self):
        """Handle Project Browser command"""
        print("Project Browser requested")
        # Execute in main GUI thread using QMetaObject
        self.signalBridge.executeInMainThread.emit(lambda: self.core.projectBrowser())
        return "Project Browser executed"
    
    @err_catcher(name=__name__)
    def handleSettings(self):
        """Handle Settings command"""
        print("Settings requested")
        # Execute in main GUI thread using signal
        self.signalBridge.executeInMainThread.emit(lambda: self.core.prismSettings())
        return "Settings executed"

    @err_catcher(name=__name__)
    def getAutobackPath(self, origin: Any) -> Tuple[str, str]:
        """Get autoback path and file filter for Photoshop scenes.
        
        Args:
            origin: Calling instance (unused)
            
        Returns:
            Tuple of (autoback_path, file_filter_string)
        """
        autobackpath = ""

        fileStr = "Photoshop Script ("
        for i in self.sceneFormats:
            fileStr += "*%s " % i

        fileStr += ")"

        return autobackpath, fileStr

    @err_catcher(name=__name__)
    def projectBrowser_loadUI(self, origin: Any) -> None:
        """Add Photoshop connection menu to Project Browser.
        
        Only adds menu when running in Standalone mode and UXP is not installed.
        
        Args:
            origin: Project Browser instance
        """
        if self.core.appPlugin.pluginName == "Standalone":
            if self.getUXPInstalled():
                return

            psMenu = QMenu("Photoshop")
            path = self.appIcon
            icon = QIcon(path)
            psMenu.setIcon(icon)
            psAction = QAction("Connect", origin)
            psAction.triggered.connect(lambda: self.connectToPhotoshop(origin))
            psMenu.addAction(psAction)
            origin.menuTools.addSeparator()
            origin.menuTools.addMenu(psMenu)

    @err_catcher(name=__name__)
    def customizeExecutable(self, origin: Any, appPath: str, filepath: str) -> bool:
        """Customize Photoshop executable launch behavior.
        
        Connects to Photoshop instead of launching it directly.
        
        Args:
            origin: Calling instance
            appPath: Path to Photoshop executable (unused)
            filepath: Scene file path to open
            
        Returns:
            Always True to indicate custom handling
        """
        self.connectToPhotoshop(origin, filepath=filepath)
        return True

    @err_catcher(name=__name__)
    def connectToPhotoshop(self, origin: Optional[Any] = None, filepath: str = "", mode: str = "Tools") -> None:
        """Start Prism instance for Photoshop integration.
        
        Launches Python process running Prism_Photoshop_MenuTools.py to handle
        communication with Photoshop.
        
        Args:
            origin: Calling instance (unused)
            filepath: Scene file path to open after connection
            mode: Launch mode ('Tools' or 'Background')
        """
        # Check if existing instance is still running
        if self.photoshopInstanceProcess is not None:
            if self.photoshopInstanceProcess.poll() is None:
                # Process is still running
                logger.info(f"Photoshop instance already running (PID: {self.photoshopInstanceProcess.pid})")
                return
            else:
                # Process has terminated
                logger.info("Previous Photoshop instance has terminated, starting new one")
                self.photoshopInstanceProcess = None
        
        pythonPath = self.core.getPythonPath(executable="Prism")
        plugin = self.core.getPlugin("Photoshop")
        menuPath = os.path.join(plugin.pluginPath, "Prism_Photoshop_MenuTools.py")
        args = [pythonPath, menuPath, self.core.prismRoot, mode, filepath]
        logger.debug("starting Prism instance for Photoshop: " + str(args))
        self.photoshopInstanceProcess = subprocess.Popen(args)
        logger.info(f"Started Photoshop instance with PID: {self.photoshopInstanceProcess.pid}")

    @err_catcher(name=__name__)
    def cleanupPhotoshopInstance(self):
        """Clean up Photoshop instance process when Standalone closes"""
        if self.photoshopInstanceProcess is None:
            return
        
        if self.photoshopInstanceProcess.poll() is None:
            # Process is still running, terminate it
            logger.info(f"Terminating Photoshop instance (PID: {self.photoshopInstanceProcess.pid})")
            try:
                self.photoshopInstanceProcess.terminate()
                # Wait up to 3 seconds for graceful shutdown
                try:
                    self.photoshopInstanceProcess.wait(timeout=3)
                    logger.info("Photoshop instance terminated gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if still running
                    logger.warning("Photoshop instance did not terminate gracefully, forcing kill")
                    self.photoshopInstanceProcess.kill()
                    self.photoshopInstanceProcess.wait()
                    logger.info("Photoshop instance killed")
            except Exception as e:
                logger.error(f"Error terminating Photoshop instance: {str(e)}")

    @err_catcher(name=__name__)
    def getPresetScenes(self, presetScenes: List[dict]) -> None:
        """Add Photoshop preset scenes to the scene presets list.
        
        Args:
            presetScenes: List to append preset scene dictionaries to
        """
        if os.getenv("PRISM_SHOW_DEFAULT_SCENEFILE_PRESETS", "1") != "1":
            return

        presetDir = os.path.join(self.pluginDirectory, "Presets")
        scenes = self.core.entities.getPresetScenesFromFolder(presetDir)
        presetScenes += scenes
