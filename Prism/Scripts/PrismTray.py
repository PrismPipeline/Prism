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
import logging
import traceback
import time
from typing import Any, Optional, List

if sys.version[0] == "3":
    sys.path.append(os.path.dirname(__file__))

if __name__ == "__main__":
    import PrismCore

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


logger = logging.getLogger(__name__)


class PrismTray:
    """System tray application for Prism pipeline management.
    
    This class manages the system tray icon and menu, handles user interactions,
    and provides quick access to common Prism functions like the Project Browser
    and Settings.
    
    Attributes:
        core: The core Prism instance
        launching: Flag indicating if browser launch is in progress
        browserStarted: Flag indicating if browser has been opened
        trayIcon: Qt system tray icon instance
        trayIconMenu: Context menu for the tray icon
        listenerThread: Background thread for IPC listening
    """
    
    def __init__(self, core: Any) -> None:
        """Initialize the PrismTray.
        
        Creates the system tray icon, menu, and starts the IPC listener thread.

        Args:
            core: The core Prism object
        
        Raises:
            Exception: If tray initialization fails, displays critical error dialog
        """
        self.core = core

        try:
            self.launching = False
            self.browserStarted = False
            self.createTrayIcon()
            self.trayIcon.show()
            self.startListener()

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            QMessageBox.critical(
                self.core.messageParent,
                "Unknown Error",
                "initTray - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno),
            )

    def startListener(self) -> None:
        """Start the listener thread for inter-process communication.
        
        Creates and starts a background thread that listens for commands
        from other Prism processes on port 7571.
        """
        self.listenerThread = ListenerThread()
        self.listenerThread.dataReceived.connect(self.onDataReceived)
        self.listenerThread.errored.connect(self.core.writeErrorLog)
        self.listenerThread.start()

    def onDataReceived(self, data: Any) -> None:
        """Handle data received from the listener thread.
        
        Processes inter-process communication commands such as opening
        the project browser, handling protocol URLs, or closing the tray.

        Args:
            data: The received command string or data object
        """
        logger.warning("received data: %s" % data)
        if data == "openProjectBrowser":
            self.startBrowser()
        elif data.startswith("protocolHandler:"):
            url = data[len("protocolHandler:"):]
            self.core.protocolHandler(url)
        elif data == "close":
            self.exitTray()

    def createTrayIcon(self) -> None:
        """Create and configure the system tray icon and its menu.
        
        Sets up the context menu with options for Project Browser, Settings,
        directory navigation, restart, and exit. Also configures the tray icon
        appearance and click behavior.
        
        Raises:
            Exception: If tray icon creation fails, displays critical error dialog
        """
        try:
            self.trayIconMenu = QMenu(self.core.messageParent)
            self.browserAction = QAction(
                "Project Browser...",
                self.core.messageParent,
                triggered=self.startBrowser,
            )
            self.trayIconMenu.addAction(self.browserAction)

            self.settingsAction = QAction(
                "Settings...",
                self.core.messageParent,
                triggered=lambda: self.core.prismSettings(),
            )
            self.trayIconMenu.addAction(self.settingsAction)
            self.trayIconMenu.addSeparator()

            self.pDirAction = QAction(
                "Open Prism directory",
                self.core.messageParent,
                triggered=lambda: self.openFolder(location="Prism"),
            )
            self.trayIconMenu.addAction(self.pDirAction)
            self.prjDirAction = QAction(
                "Open project directory",
                self.core.messageParent,
                triggered=lambda: self.openFolder(location="Project"),
            )
            self.trayIconMenu.addAction(self.prjDirAction)
            self.trayIconMenu.addSeparator()
            self.restartAction = QAction(
                "Restart", self.core.messageParent, triggered=self.restartTray
            )
            self.trayIconMenu.addAction(self.restartAction)
            self.exitAction = QAction(
                "Exit", self.core.messageParent, triggered=self.exitTray
            )
            self.trayIconMenu.addAction(self.exitAction)

            self.core.callback(
                name="trayContextMenuRequested",
                args=[self, self.trayIconMenu],
            )

            self.trayIcon = QSystemTrayIcon()
            self.trayIcon.setContextMenu(self.trayIconMenu)
            self.trayIcon.setToolTip("Prism Tools")

            self.icon = QIcon(
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "UserInterfacesPrism",
                    "p_tray.png",
                )
            )

            self.trayIcon.setIcon(self.icon)

            self.trayIcon.activated.connect(self.iconActivated)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            QMessageBox.critical(
                self.core.messageParent,
                "Unknown Error",
                "createTray - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno),
            )

    def iconActivated(self, reason: Any) -> None:
        """Handle tray icon activation events.
        
        Responds to different types of user interactions with the tray icon,
        including single clicks, double clicks, and context menu requests.
        Platform-specific behavior is handled for Windows and macOS.

        Args:
            reason: The reason for activation (Trigger, DoubleClick, or Context)
        """
        try:
            if reason == QSystemTrayIcon.Trigger:
                self.browserStarted = False
                if (
                    platform.system() == "Darwin"
                    and reason != QSystemTrayIcon.DoubleClick
                ):
                    return

                if (
                    platform.system() == "Windows"
                    and reason == QSystemTrayIcon.DoubleClick
                ):
                    return

                results = self.core.callback(name="trayIconClicked", args=[self, reason])
                if not [r for r in results if r == "handled"]:
                    self.browserStarted = True
                    self.startBrowser()

            elif reason == QSystemTrayIcon.DoubleClick:
                if not self.browserStarted:
                    self.startBrowser()

            elif reason == QSystemTrayIcon.Context:
                self.core.callback(
                    name="openTrayContextMenu",
                    args=[self, self.trayIconMenu],
                )

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
        #   QMessageBox.critical(self.core.messageParent, "Unknown Error", "iconActivated - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno))

    def startBrowser(self) -> None:
        """Start the project browser window.
        
        Launches the Prism Project Browser if not already launching.
        Prevents multiple simultaneous launch attempts.
        """
        if self.launching:
            logger.debug("Launching in progress. Skipped opening Project Browser")
            return

        self.launching = True
        self.core.projectBrowser()
        self.launching = False
        return

    def openFolder(self, path: str = "", location: Optional[str] = None) -> None:
        """Open a folder in the file explorer.
        
        Opens either a specified path or a predefined location (Prism root
        or current project directory) in the system file explorer.

        Args:
            path: The explicit path to open (default: "")
            location: Predefined location type - 'Prism' for Prism root directory
                     or 'Project' for current project directory (default: None)
        """
        if location == "Prism":
            path = self.core.prismRoot
        elif location == "Project":
            curProject = self.core.getConfig("globals", "current project")
            if curProject is None:
                QMessageBox.warning(
                    self.core.messageParent,
                    "Open directory",
                    "No active project is set.",
                )
                return
            else:
                path = os.path.dirname(os.path.dirname(curProject))

        self.core.openFolder(path)

    def openSettings(self) -> None:
        """Open the Prism settings window.
        
        Launches the Prism Settings dialog for configuring application preferences.
        """
        self.core.prismSettings()

    def restartTray(self) -> None:
        """Restart the Prism tray application.
        
        Shuts down the listener thread (releasing port 7571), spawns a new
        Prism tray process, and exits the current process.
        """
        self.listenerThread.shutDown()  # release port 7571 so the new process can acquire it

        pythonPath = self.core.getPythonPath(executable="Prism")
        filepath = os.path.join(self.core.prismRoot, "Scripts", "PrismTray.py")
        cmd = """start "" "%s" "%s" showSplash""" % (pythonPath, filepath)
        subprocess.Popen(cmd, cwd=self.core.prismRoot, shell=True, env=self.core.startEnv)
        sys.exit(0)

    def exitTray(self) -> None:
        """Exit the Prism tray application.
        
        Cleanly shuts down the listener thread and closes the Qt application.
        """
        if hasattr(self, "listenerThread"):
            self.listenerThread.shutDown()

        QApplication.instance().quit()


class ListenerThread(QThread):
    """Thread for listening to inter-process communication events.
    
    This thread runs a listener on localhost:7571 that accepts connections
    from other Prism processes and emits signals when data is received.
    
    Attributes:
        dataReceived: Signal emitted when data is received from a client
        errored: Signal emitted when an exception occurs
        listener: The multiprocessing Listener instance
        conn: The current client connection
    """

    dataReceived = Signal(object)
    errored = Signal(object)

    def __init__(self, function: Optional[Any] = None) -> None:
        """Initialize the ListenerThread.
        
        Args:
            function: Optional function parameter (unused, for compatibility)
        """
        super(ListenerThread, self).__init__()

    def run(self) -> None:
        """Run the listener thread.
        
        Creates a listener on localhost:7571 and accepts client connections.
        Continuously receives data from connected clients and emits the
        dataReceived signal. Handles port-in-use errors gracefully.
        
        Raises:
            Exception: Emits errored signal with traceback if unexpected error occurs
        """
        try:
            from multiprocessing.connection import Listener

            port = _ipc_port()
            address = ('localhost', port)
            try:
                self.listener = Listener(address)
            except Exception as e:
                if platform.system() == "Windows":
                    errid = 10048
                    permid = 10013
                else:
                    errid = 98
                    permid = 13

                winerr = getattr(e, "winerror", None)
                if e.errno == errid or winerr == errid:
                    logging.warning("Port %s is already in use. Please contact the support." % port)
                    return
                elif e.errno == permid or winerr == permid:
                    logging.warning("Port %s cannot be bound: access denied. The port may be blocked by a firewall or antivirus, or reserved by Windows." % port)
                    return
                else:
                    raise

            while True:
                try:
                    self.conn = self.listener.accept()
                except OSError:
                    break  # Listener was closed by shutDown()

                while True:
                    try:
                        data = self.conn.recv()
                    except Exception as e:
                        break

                    if data == "getPid":
                        try:
                            self.conn.send((os.getpid(), sys.executable))
                        except Exception:
                            pass
                        continue

                    self.dataReceived.emit(data)

            self.listener.close()
            self.quit()
        except Exception as e:
            self.errored.emit(traceback.format_exc())

    def shutDown(self) -> None:
        """Shut down the listener thread.
        
        Closes the listener socket and terminates the thread cleanly.
        """
        if hasattr(self, "listener"):
            self.listener.close()

        self.quit()


class SenderThread(QThread):
    """Thread for sending inter-process communication events.
    
    This thread creates a client connection to the Prism listener on
    localhost:7571 and can send commands to it.
    
    Attributes:
        canceled: Flag indicating if the thread has been canceled
        conn: The client connection to the listener
    """
    
    def __init__(self, function: Optional[Any] = None) -> None:
        """Initialize the SenderThread.
        
        Args:
            function: Optional function parameter (unused, for compatibility)
        """
        super(SenderThread, self).__init__()
        self.canceled = False

    def run(self) -> None:
        """Run the sender thread.
        
        Establishes a client connection to the Prism listener on localhost:7571.
        """
        from multiprocessing.connection import Client
        port = _ipc_port()
        address = ('localhost', port)
        self.conn = Client(address)

    def shutDown(self) -> None:
        """Shut down the sender thread.
        
        Closes the client connection and terminates the thread.
        """
        self.conn.close()
        self.quit()

    def send(self, data: Any) -> None:
        """Send data to the listener.
        
        Transmits a command or data object to the connected Prism listener.

        Args:
            data: The data to send to the listener process
        """
        self.conn.send(data)


def _ipc_port() -> int:
    """Return the IPC listener port, overrideable via PRISM_IPC_PORT env var."""
    import os as _os
    return int(_os.environ.get('PRISM_IPC_PORT', 7571))


def isAlreadyRunning() -> bool:
    """Check if Prism tray is already running by probing the IPC listener port.

    Attempts a TCP connection to the listener port (7571). If the connection
    succeeds, another instance already owns the port and is listening for
    commands. Works regardless of which Python executable or shell launched
    Prism, and produces no stale state on crash.

    Returns:
        True if another Prism tray instance is running, False otherwise
    """
    import socket as _socket
    sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        sock.connect(('127.0.0.1', _ipc_port()))
        return True
    except OSError:
        return False
    finally:
        try:
            sock.close()
        except Exception:
            pass


def queryPrismProcess() -> Optional[tuple]:
    """Query the running Prism tray instance for its PID and executable path.

    Sends a 'getPid' request over the IPC port and waits for the reply.
    Returns a (pid, exe) tuple, or None if no instance is reachable.
    """
    from multiprocessing.connection import Client
    try:
        conn = Client(('localhost', _ipc_port()))
        conn.send('getPid')
        result = conn.recv()
        conn.close()
        return result
    except Exception:
        return None


def findPrismProcesses() -> List[str]:
    """Find the running Prism tray process.

    Queries the existing Prism instance over IPC to obtain its PID and
    executable path. Works regardless of which Python executable or shell
    launched Prism.

    Returns:
        List of process descriptions in format "path (pid)"
    """
    info = queryPrismProcess()
    if info is None:
        return []
    pid, exe = info
    return ["%s (%s)" % (exe, pid)]


def showDetailPopup(msgTxt: str, parent: Any) -> str:
    """Show a popup with details about running Prism processes.
    
    Displays a dialog listing all currently running Prism processes
    with options to stop them or close the dialog.

    Args:
        msgTxt: The base message text to display
        parent: The parent QMessageBox widget

    Returns:
        The text of the clicked button ("Stop processes" or "Close")
    """
    procUserTxt = findPrismProcesses()
    if procUserTxt:
        msgTxt += "\n\nThe following Prism processes are already running:\n\n"
        msgTxt += "\n".join(procUserTxt)

    title = "Details"
    icon = QMessageBox.Information
    buttons = ["Stop processes", "Close"]
    default = buttons[0]
    escapeButton = "Close"

    msg = QMessageBox(
        icon,
        title,
        msgTxt,
        parent=parent,
    )

    for button in buttons:
        if button in ["Close", "Cancel", "Ignore"]:
            role = QMessageBox.RejectRole
        else:
            role = QMessageBox.YesRole

        b = msg.addButton(button, role)
        if default == button:
            msg.setDefaultButton(b)

        if escapeButton == button:
            msg.setEscapeButton(b)

    msg.exec_()
    result = msg.clickedButton().text()
    if result == "Stop processes":
        closePrismProcesses()
        parent._result = "Stop running process"
        parent.close()
    elif result == "Close":
        pass

    return result


def popupQuestion(text: str, buttons: List[str]) -> str:
    """Show a question popup with custom buttons.
    
    Creates a warning dialog with custom button options. The "Details..." button
    triggers a detail popup showing running processes.

    Args:
        text: The question text to display
        buttons: List of button labels to show

    Returns:
        The text of the clicked button
    """
    text = str(text)
    title = "Prism"
    icon = QMessageBox.Warning
    default = buttons[0]
    escapeButton = "Close"

    msg = QMessageBox(
        icon,
        title,
        text,
    )
    for button in buttons:
        if button in ["Close", "Cancel", "Ignore"]:
            role = QMessageBox.RejectRole
        else:
            role = QMessageBox.YesRole

        b = msg.addButton(button, role)
        if default == button:
            msg.setDefaultButton(b)

        if button == "Details...":
            b.clicked.disconnect()
            b.clicked.connect(lambda: showDetailPopup(text, msg))

        if escapeButton == button:
            msg.setEscapeButton(b)

    msg.exec_()
    result = msg.clickedButton().text()
    if hasattr(msg, "_result"):
        result = msg._result

    return result


def closePrismProcesses() -> None:
    """Close the running Prism tray process.

    Queries the existing instance over IPC for its PID, then terminates it
    using os.kill. Skips if the resolved PID matches the current process.
    """
    import signal
    info = queryPrismProcess()
    if info is None:
        return
    pid, _ = info
    if pid == os.getpid():
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except Exception as e:
        logger.warning("error while killing process: %s" % str(e))


def sendCommandToPrismProcess(command: str) -> bool:
    """Send a command to the running Prism tray process.
    
    Creates a sender thread, establishes connection to the listener,
    and sends the specified command. Waits up to 3 seconds for connection.
    
    Args:
        command: The command string to send (e.g., "openProjectBrowser")
    
    Returns:
        True if command was sent successfully, False if connection failed
    """
    senderThread = SenderThread()
    senderThread.start()
    idx = 0
    while True:
        if hasattr(senderThread, "conn"):
            break

        time.sleep(1)
        idx += 1
        if idx > 3:
            break

    if hasattr(senderThread, "conn"):
        senderThread.send(command)
        senderThread.shutDown()
        return True
    else:
        senderThread.quit()
        return False


def launch() -> None:
    """Launch the Prism tray application.
    
    Main entry point for starting the Prism tray. Checks if Prism is already
    running and either sends commands to the existing instance or starts a new
    instance. Handles the Qt application lifecycle and tray icon initialization.
    """
    if isAlreadyRunning():
        qApp = QApplication.instance()
        if not qApp:
            qApp = QApplication(sys.argv)

        result = sendCommandToPrismProcess("openProjectBrowser")
        if not result:
            qApp = QApplication.instance()
            wIcon = QIcon(
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "UserInterfacesPrism",
                    "p_tray.png",
                )
            )
            qApp.setWindowIcon(wIcon)

            from UserInterfacesPrism.stylesheets import blue_moon
            qApp.setStyleSheet(blue_moon.load_stylesheet(pyside=True))

            result = popupQuestion("Prism is already running.", buttons=["Stop running process", "Details...", "Close"])
            if result == "Stop running process":
                closePrismProcesses()
                return launch()
            elif result == "Close":
                pass
            elif result == "Ignore":
                return

        sys.exit()
    else:
        args = ["loadProject", "tray"]
        if "projectBrowser" not in sys.argv:
            args.append("noProjectBrowser")
            if "showSplash" not in sys.argv:
                args.append("noSplash")

        pc = PrismCore.create(prismArgs=args)
        qApp = QApplication.instance()
        qApp.setQuitOnLastWindowClosed(False)
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(
                None,
                "PrismTray",
                "Could not launch PrismTray. Tray icons are not supported on this OS.",
            )
            sys.exit(1)

        pc.startTray()
        sys.exit(qApp.exec_())


if __name__ == "__main__":
    launch()
