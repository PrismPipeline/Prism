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
# Copyright (C) 2016-2020 Richard Frangenberg
#
# Licensed under GNU GPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


import os
import sys
import time
import subprocess
import platform
import logging

if sys.version[0] == "3":
    sys.path.append(os.path.dirname(__file__))

if __name__ == "__main__":
    import PrismCore

if platform.system() == "Windows":
    import psutil

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

from UserInterfacesPrism import qdarkstyle


logger = logging.getLogger(__name__)


class PrismTray:
    def __init__(self, core):
        self.core = core

        try:
            self.launching = False

            pIcon = QIcon(
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "UserInterfacesPrism",
                    "p_tray.ico",
                )
            )
            QApplication.setWindowIcon(pIcon)

            if platform.system() == "Windows":
                coreProc = []
                for x in psutil.pids():
                    try:
                        if x != os.getpid() and os.path.basename(psutil.Process(x).exe()) == "Prism Tray.exe":
                            coreProc.append(x)
                    except:
                        pass

                if len(coreProc) > 0:
                    QMessageBox.warning(self.core.messageParent, "PrismTray", "PrismTray is already running.")
                    QApplication.quit()
                    sys.exit()
                    return

            self.createTrayIcon()
            self.trayIcon.show()

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            QMessageBox.critical(
                self.core.messageParent,
                "Unknown Error",
                "initTray - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno),
            )

    def createTrayIcon(self):
        try:
            self.trayIconMenu = QMenu(self.core.messageParent)
            self.browserAction = QAction(
                "Project Browser...",
                self.core.messageParent,
                triggered=self.startBrowser,
            )
            self.trayIconMenu.addAction(self.browserAction)
            self.dailiesAction = QAction(
                "Open dailies folder...",
                self.core.messageParent,
                triggered=self.openDailies,
            )
            self.trayIconMenu.addAction(self.dailiesAction)
            self.trayIconMenu.addSeparator()

            self.settingsAction = QAction(
                "Prism Settings...",
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
            self.exitAction = QAction(
                "Exit", self.core.messageParent, triggered=self.exitTray
            )
            self.trayIconMenu.addAction(self.exitAction)

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
            if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
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

                self.startBrowser()
            elif reason == QSystemTrayIcon.Context:
                curProject = self.core.getConfig("globals", "current project")
                self.dailiesAction.setEnabled(
                    curProject is not None and curProject is not ""
                )

                self.core.callback(
                    name="openTrayContextMenu",
                    types=["custom"],
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
                PROCNAME = "Prism Project Browser.exe"
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

    def openDailies(self):
        try:
            dailiesName = self.core.getConfig("paths", "dailies", config="project")

            if not dailiesName:
                self.trayIcon.showMessage(
                    "Information missing",
                    "The dailies folder is not set in the project config.",
                    icon=QSystemTrayIcon.Warning,
                )
                return

            curDate = time.strftime("%Y_%m_%d", time.localtime())

            dailiesFolder = os.path.join(self.core.projectPath, dailiesName, curDate)
            if os.path.exists(dailiesFolder):
                self.openFolder(dailiesFolder)
            else:
                msg = QMessageBox(
                    QMessageBox.Question,
                    "Dailies folder",
                    "The dailies folder for today does not exist yet.\n\nDo you want to create it?",
                    QMessageBox.No,
                )
                msg.addButton("Yes", QMessageBox.YesRole)
                msg.setParent(self.core.messageParent, Qt.Window)
                action = msg.exec_()

                if action == 0:
                    os.makedirs(dailiesFolder)
                    self.openFolder(dailiesFolder)
                else:
                    self.openFolder(os.path.dirname(dailiesFolder))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.trayIcon.showMessage(
                "Unknown Error",
                "openDailies - %s - %s - %s" % (str(e), exc_type, exc_tb.tb_lineno),
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
                PROCNAME = "Prism Settings.exe"
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

    def exitTray(self):
        qApp.quit()


if __name__ == "__main__":
    qApp = QApplication(sys.argv)
    qApp.setQuitOnLastWindowClosed(False)
    qApp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "PrismTray", "Could not launch PrismTray. Tray icons are not supported on this OS.")
        sys.exit(1)

    pc = PrismCore.PrismCore(prismArgs=["loadProject", "noProjectBrowser", "tray"])
    pc.startTray()
    sys.exit(qApp.exec_())
