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
import shutil
import logging

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

if platform.system() == "Windows":
    if sys.version[0] == "3":
        import winreg as _winreg
    else:
        import _winreg
else:
    import pwd

from PrismUtils.Decorators import err_catcher as err_catcher


logger = logging.getLogger(__name__)


class Prism_Standalone_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        self.core.registerCallback(
            "onProjectBrowserStartup", self.onProjectBrowserStartup, plugin=self.plugin
        )
        self.core.registerCallback(
            "onPluginsLoaded", self.onPluginsLoaded, plugin=self.plugin
        )
        stylesheet = self.core.getConfig("globals", "standalone_stylesheet", config="user")
        stylesheet = stylesheet or "Blue Moon"
        result = self.core.setActiveStyleSheet(stylesheet)
        self.stylesheetToBeSet = None
        if not result:
            self.core.setActiveStyleSheet("Blue Moon")
            self.stylesheetToBeSet = stylesheet

        appIcon = QIcon(
            os.path.join(
                self.core.prismRoot,
                "Scripts",
                "UserInterfacesPrism",
                "p_tray.png",
            )
        )
        qapp = QApplication.instance()
        qapp.setWindowIcon(appIcon)

    @err_catcher(name=__name__)
    def startup(self, origin):
        if "loadProject" not in self.core.prismArgs:
            return False

    @err_catcher(name=__name__)
    def onPluginsLoaded(self):
        if self.stylesheetToBeSet:
            self.core.setActiveStyleSheet(self.stylesheetToBeSet)

    @err_catcher(name=__name__)
    def getCurrentFileName(self, origin, path=True):
        return ""

    @err_catcher(name=__name__)
    def getCurrentSceneFiles(self, origin):
        return []

    @err_catcher(name=__name__)
    def onProjectBrowserStartup(self, origin):
        origin.closeParm = "closeafterloadsa"
        origin.actionStateManager.setEnabled(False)

    @err_catcher(name=__name__)
    def openScene(self, origin, filepath, force=False):
        return False

    @err_catcher(name=__name__)
    def saveScene(self, origin, filepath, details={}, underscore=True):
        return

    @err_catcher(name=__name__)
    def createWinStartMenu(self, origin):
        if os.environ.get("prism_skip_root_install"):
            logger.warning(
                "skipped creating Prism startmenu because of missing permissions."
            )
            return

        if platform.system() == "Windows":
            startMenuPath = os.path.join(
                os.environ["AppData"], "Microsoft", "Windows", "Start Menu", "Programs"
            )
            trayStartup = os.path.join(startMenuPath, "Startup", "Prism.lnk")
            trayStartupOld = os.path.join(startMenuPath, "Startup", "Prism Tray.lnk")
            trayStartupOld2 = os.path.join(startMenuPath, "Startup", "PrismTray.lnk")
            prismStartMenu = os.path.join(startMenuPath, "Prism")
            trayStartMenu = os.path.join(prismStartMenu, "Prism.lnk")
            desktopIcon = os.path.join(os.environ["USERPROFILE"], "Desktop", "Prism.lnk")

            if os.path.exists(prismStartMenu):
                try:
                    shutil.rmtree(prismStartMenu)
                    logger.debug("removed %s" % prismStartMenu)
                except:
                    logger.debug("couldn't remove %s" % prismStartMenu)

            tools = [trayStartup, trayStartupOld, trayStartupOld2]
            for tool in tools:
                if os.path.exists(tool):
                    try:
                        os.remove(tool)
                        logger.debug("removed %s" % tool)
                    except:
                        logger.debug("couldn't remove %s" % tool)

            trayLnk = os.path.join(self.core.prismLibs, "Tools", "Prism.lnk")

            if not os.path.exists(os.path.dirname(trayLnk)):
                try:
                    os.makedirs(os.path.dirname(trayLnk))
                except:
                    pass

            if not os.path.exists(os.path.dirname(trayStartup)):
                try:
                    os.makedirs(os.path.dirname(trayStartup))
                except:
                    pass

            target = "%s\\%s\\Prism.exe" % (self.core.prismLibs, self.core.pythonVersion)
            args = '""%s\\Scripts\\PrismTray.py""' % (self.core.prismRoot.replace("/", "\\"))
            args2 = '""%s\\Scripts\\PrismTray.py"" projectBrowser' % (self.core.prismRoot.replace("/", "\\"))
            self.core.createShortcut(trayStartup, target, args=args)
            self.core.createShortcut(trayLnk, target, args=args2, ignoreError=True)
            if not os.path.exists(prismStartMenu):
                try:
                    os.makedirs(prismStartMenu)
                except:
                    logger.warning("failed to create folder: %s" % prismStartMenu)

            if os.path.exists(prismStartMenu):
                self.core.createShortcut(trayStartMenu, target, args=args2)

            if os.path.exists(os.path.dirname(desktopIcon)):
                self.core.createShortcut(desktopIcon, target, args=args2)

        return True

    @err_catcher(name=__name__)
    def addWindowsStartMenuEntry(self, name, executable, script, args=None):
        startMenuPath = os.path.join(
            os.environ["AppData"], "Microsoft", "Windows", "Start Menu", "Programs"
        )
        scPath = os.path.join(startMenuPath, "Prism", name + ".lnk")

        if not os.path.isabs(executable):
            executable = os.path.join(self.core.prismLibs, self.core.pythonVersion, executable)
            if not executable.endswith(".exe"):
                executable += ".exe"

        if not os.path.exists(executable):
            self.core.popup("Executable doesn't exist: %s" % executable)
            return

        script
        if not os.path.isabs(script):
            script = os.path.join(
                self.core.prismRoot.replace("/", "\\"), "Scripts", script
            )
            if not script.endswith(".py"):
                script += ".py"

        if not os.path.exists(script):
            self.core.popup("Script doesn't exist: %s" % script)
            return

        scDir = os.path.dirname(scPath)
        if not os.path.exists(scDir):
            os.makedirs(scDir)

        args = args or []
        args = ['""%s""' % script] + args
        argStr = " ".join(args)
        self.core.createShortcut(scPath, executable, args=argStr)
        return scPath

    @err_catcher(name=__name__)
    def addUninstallerToWindowsRegistry(self):
        if platform.system() != "Windows":
            return

        try:
            key = _winreg.CreateKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Prism Pipeline 2.0",
            )
        except Exception as e:
            logger.warning("failed to create key. %s" % (e))
            return

        iconPath = self.core.getPythonPath(executable="Prism")
        installer = os.path.normpath(os.path.join(self.core.prismRoot, "Scripts", "PrismInstaller.py"))
        uninstallStr = "\"%s\" \"%s\" uninstall" % (os.path.normpath(self.core.getPythonPath()), installer)
        items = {
            "DisplayIcon": iconPath,
            "DisplayName": "Prism Pipeline 2.0",
            "DisplayVersion": self.core.version[1:],
            "HelpLink": "https://prism-pipeline.com",
            "InstallLocation": self.core.prismRoot,
            "Publisher": "Prism",
            "UninstallString": uninstallStr,
        }

        for item in items.items():
            _winreg.SetValueEx(
                key,
                item[0],
                0,
                _winreg.REG_SZ,
                item[1],
            )

        logger.debug("added uninstaller to Windows registry")
        return True

    @err_catcher(name=__name__)
    def validateUninstallerInWindowsRegistry(self):
        try:
            key = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Prism Pipeline 2.0",
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )
        except:
            return False

        installDir = _winreg.QueryValueEx(key, "InstallLocation")[0]
        if installDir == self.core.prismRoot:
            return True

        return False
