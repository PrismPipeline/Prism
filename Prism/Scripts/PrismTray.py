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

if sys.version[0] == "3":
    sys.path.append(os.path.dirname(__file__))

if __name__ == "__main__":
    import PrismCore

if platform.system() == "Windows":
    import psutil

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


logger = logging.getLogger(__name__)


class PrismTray:
    def __init__(self, core):
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

    def startListener(self):
        self.listenerThread = ListenerThread()
        self.listenerThread.dataReceived.connect(self.onDataReceived)
        self.listenerThread.errored.connect(self.core.writeErrorLog)
        self.listenerThread.start()

    def onDataReceived(self, data):
        logger.warning("received data: %s" % data)
        if data == "openProjectBrowser":
            self.startBrowser()
        elif data == "close":
            self.exitTray()

    def createTrayIcon(self):
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
                triggered=self.openSettings,
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

    def iconActivated(self, reason):
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

    def startBrowser(self):
        if self.launching:
            logger.debug("Launching in progress. Skipped opening Project Browser")
            return

        self.launching = True
        self.core.projectBrowser()
        self.launching = False
        return

        # the following code starts the RenderHandler in a new process, but is a lot slower
        try:
            browserPath = os.path.join(os.path.dirname(__file__), "PrismCore.py")
            if not os.path.exists(browserPath):
                self.trayIcon.showMessage(
                    "Script missing",
                    "PrismCore.py does not exist.",
                    icon=QSystemTrayIcon.Warning,
                )
                return None

            if platform.system() == "Windows":
                command = '"%s/Tools/Prism Project Browser.lnk"' % self.core.prismLibs
            else:
                command = "python %s" % os.path.join(
                    self.core.prismRoot, "Scripts", "PrismCore.py"
                )

            self.browserProc = subprocess.Popen(command, shell=True)

            if platform.system() == "Windows":
                PROCNAME = "Prism.exe"
                for proc in psutil.process_iter():
                    if proc.name() == PROCNAME:
                        if proc.pid == self.browserProc.pid:
                            continue

                        p = psutil.Process(proc.pid)

                        if not "SYSTEM" in p.username():
                            proc.kill()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.trayIcon.showMessage(
                "Unknown Error",
                "startBrowser - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno),
                icon=QSystemTrayIcon.Critical,
            )

    def openFolder(self, path="", location=None):
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

    def openSettings(self):
        self.core.prismSettings()
        return

        # the following code starts the RenderHandler in a new process, but is a lot slower
        try:
            settingsPath = os.path.join(os.path.dirname(__file__), "PrismSettings.py")
            if not os.path.exists(settingsPath):
                self.trayIcon.showMessage(
                    "Script missing",
                    "PrismSettings.py does not exist.",
                    icon=QSystemTrayIcon.Warning,
                )
                return None

            if platform.system() == "Windows":
                command = '"%s/Tools/PrismSettings.lnk"' % self.core.prismLibs
            else:
                command = "python %s" % os.path.join(
                    self.core.prismRoot, "Scripts", "PrismSettings.py"
                )

            self.settingsProc = subprocess.Popen(command, shell=True)

            if platform.system() == "Windows":
                PROCNAME = "Prism.exe"
                for proc in psutil.process_iter():
                    if proc.name() == PROCNAME:
                        if proc.pid == self.settingsProc.pid:
                            continue
                        p = psutil.Process(proc.pid)

                        if not "SYSTEM" in p.username():
                            proc.kill()

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.trayIcon.showMessage(
                "Unknown Error",
                "openSettings - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno),
                icon=QSystemTrayIcon.Critical,
            )

    def restartTray(self):
        self.listenerThread.shutDown()

        pythonPath = self.core.getPythonPath(executable="Prism")
        filepath = os.path.join(self.core.prismRoot, "Scripts", "PrismTray.py")
        cmd = """start "" "%s" "%s" showSplash""" % (pythonPath, filepath)
        subprocess.Popen(cmd, cwd=self.core.prismRoot, shell=True)
        sys.exit(0)

    def exitTray(self):
        self.listenerThread.shutDown()
        qApp.quit()


class ListenerThread(QThread):

    dataReceived = Signal(object)
    errored = Signal(object)

    def __init__(self, function=None):
        super(ListenerThread, self).__init__()

    def run(self):
        try:
            from multiprocessing.connection import Listener

            port = 7571
            address = ('localhost', port)
            try:
                self.listener = Listener(address)
            except Exception as e:
                if e.errno == 10048:
                    logging.warning("Port %s is already in use. Please contact the support." % port)
                    return
                else:
                    raise

            while True:
                self.conn = self.listener.accept()
                while True:
                    try:
                        data = self.conn.recv()
                    except Exception as e:
                        break

                    self.dataReceived.emit(data)

            self.listener.close()
            self.quit()
        except Exception as e:
            self.errored.emit(traceback.format_exc())

    def shutDown(self):
        if hasattr(self, "listener"):
            self.listener.close()

        self.quit()


class SenderThread(QThread):
    def __init__(self, function=None):
        super(SenderThread, self).__init__()
        self.canceled = False

    def run(self):
        from multiprocessing.connection import Client
        port = 7571
        address = ('localhost', port)
        self.conn = Client(address)

    def shutDown(self):
        self.conn.close()
        self.quit()

    def send(self, data):
        self.conn.send(data)


def isAlreadyRunning():
    if platform.system() == "Windows":
        coreProc = []
        for proc in psutil.process_iter():
            try:
                if (
                    proc.pid != os.getpid()
                    and os.path.basename(proc.exe()) == "Prism.exe"
                    and proc.username() == psutil.Process(os.getpid()).username()
                ):
                    coreProc.append(proc.pid)
                    return True
            except:
                pass

    return False


if __name__ == "__main__":
    qApp = QApplication(sys.argv)
    qApp.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            None,
            "PrismTray",
            "Could not launch PrismTray. Tray icons are not supported on this OS.",
        )
        sys.exit(1)

    if isAlreadyRunning():
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
            senderThread.send("openProjectBrowser")
            senderThread.shutDown()
        else:
            senderThread.quit()
            QMessageBox.warning(None, "Prism", "Prism is already running.")
        
        sys.exit()
    else:
        args = ["loadProject", "tray"]
        if "projectBrowser" not in sys.argv:
            args.append("noProjectBrowser")
            if "showSplash" not in sys.argv:
                args.append("noSplash")

        pc = PrismCore.create(prismArgs=args)
        pc.startTray()
        sys.exit(qApp.exec_())
