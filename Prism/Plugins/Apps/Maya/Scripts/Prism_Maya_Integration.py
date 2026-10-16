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

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from typing import Any, Dict, List, Optional, Tuple

if platform.system() == "Windows":
    if sys.version[0] == "3":
        import winreg as _winreg
    else:
        import _winreg

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_Maya_Integration(object):
    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize Maya integration manager.
        
        Sets up platform-specific example paths for Maya preferences folder.
        
        Args:
            core: Prism core instance
            plugin: Plugin instance
        """
        self.core = core
        self.plugin = plugin

        if platform.system() == "Windows":
            self.examplePath = self.core.getWindowsDocumentsPath() + "\\maya\\2027"
        elif platform.system() == "Linux":
            userName = (
                os.environ["SUDO_USER"]
                if "SUDO_USER" in os.environ
                else os.environ["USER"]
            )
            self.examplePath = os.path.join("/home", userName, "maya", "2027")
        elif platform.system() == "Darwin":
            userName = (
                os.environ["SUDO_USER"]
                if "SUDO_USER" in os.environ
                else os.environ["USER"]
            )
            self.examplePath = (
                "/Users/%s/Library/Preferences/Autodesk/maya/2027" % userName
            )

    @err_catcher(name=__name__)
    def getExecutable(self) -> str:
        """Get path to Maya executable.
        
        Returns:
            Path to maya.exe on Windows, empty string otherwise
        """
        execPath = ""
        if platform.system() == "Windows":
            defaultpath = os.path.join(self.getMayaPath(), "bin", "maya.exe")
            if os.path.exists(defaultpath):
                execPath = defaultpath

        return execPath

    @err_catcher(name=__name__)
    def getMayaPath(self) -> str:
        """Get Maya installation directory from Windows registry.
        
        Returns:
           Installation directory path, or empty string if not found
        """
        try:
            key = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Autodesk\\Maya",
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )

            mayaVersions = []
            try:
                i = 0
                while True:
                    mayaVers = _winreg.EnumKey(key, i)
                    if sys.version[0] == "2":
                        mayaVers = unicode(mayaVers)

                    if mayaVers.isnumeric():
                        mayaVersions.append(mayaVers)
                    i += 1
            except WindowsError:
                pass

            validVersion = mayaVersions[-1]

            key = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Autodesk\\Maya\\%s\\Setup\\InstallPath" % validVersion,
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )

            installDir = (_winreg.QueryValueEx(key, "MAYA_INSTALL_LOCATION"))[0]

            return installDir

        except:
            return ""

    def addIntegration(self, installPath: str) -> bool:
        """Add Prism integration to Maya installation.
        
        Copies Prism module file and shelf to Maya preferences folder.
        
        Args:
            installPath: Path to Maya preferences folder
            
        Returns:
            True if integration successful, False otherwise
        """
        try:
            scriptPath = os.path.join(installPath, "scripts")
            shelfPath = os.path.join(installPath, "prefs", "shelves")
            if not os.path.exists(scriptPath) or not os.path.exists(shelfPath):
                msg = "Maya path appears invalid:\n\n%s\n\nThe expected paths don't exist:\n%s\n%s\n\nThe Maya path has to be the Maya preferences folder, which usually looks like this: (with your username and Maya version):\n\n%s" % (installPath, scriptPath, shelfPath, self.examplePath)
                result = self.core.popupQuestion(msg, buttons=["Continue", "Cancel"], icon=QMessageBox.Warning, default="Continue")
                if result != "Continue":
                    return False

            integrationBase = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Integration"
            )
            integrationBase = os.path.realpath(integrationBase)
            addedFiles = []

            integrationFiles = {}
            integrationFiles["Prism.mod"] = os.path.join(
                integrationBase, "Prism.mod"
            )
            integrationFiles["shelf_Prism.mel"] = os.path.join(
                integrationBase, "shelves", "shelf_Prism.mel"
            )

            self.core.callback(
                name="preIntegrationAdded", args=[self, integrationFiles]
            )

            origModFile = integrationFiles["Prism.mod"]
            modpath = os.path.join(installPath, "modules", "Prism.mod")
            if os.path.exists(modpath):
                os.remove(modpath)

            if not os.path.exists(os.path.dirname(modpath)):
                os.makedirs(os.path.dirname(modpath))

            shutil.copy2(origModFile, modpath)
            addedFiles.append(modpath)

            with open(modpath, "r") as init:
                initStr = init.read()

            with open(modpath, "w") as init:
                initStr = initStr.replace(
                    "PRISMROOT", self.core.prismRoot.replace("\\", "/")
                )
                initStr = initStr.replace(
                    "PLUGINROOT", os.path.dirname(self.pluginPath).replace("\\", "/")
                )
                init.write(initStr)

            if platform.system() in ["Linux", "Darwin"]:
                for i in addedFiles:
                    os.chmod(i, 0o777)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            msgStr = (
                "Errors occurred during the installation of the Maya integration.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
            return False

    @err_catcher(name=__name__)
    def getIntegrationStatus(self, path: str) -> str:
        """Compare the installed Prism module with the current integration template."""
        installedFile = os.path.join(path, "modules", "Prism.mod")
        if not os.path.isfile(installedFile):
            legacyFiles = [
                os.path.join(path, "scripts", "PrismInit.py"),
                os.path.join(path, "scripts", "PrismInit.pyc"),
                os.path.join(path, "prefs", "shelves", "shelf_Prism.mel"),
            ]
            if any(os.path.isfile(filename) for filename in legacyFiles):
                return "update needed"
            userSetup = os.path.join(path, "scripts", "userSetup.py")
            if os.path.isfile(userSetup):
                with open(userSetup, "r") as stream:
                    if ">>>PrismStart" in stream.read():
                        return "update needed"
            return "not added"

        integrationBase = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Integration")
        with open(os.path.join(integrationBase, "Prism.mod"), "r") as stream:
            expected = stream.read().replace("PRISMROOT", self.core.prismRoot.replace("\\", "/"))
        expected = expected.replace("PLUGINROOT", os.path.dirname(self.pluginPath).replace("\\", "/"))
        with open(installedFile, "r") as stream:
            installed = stream.read()
        return "added" if installed == expected else "update needed"

    def removeIntegration(self, installPath: str) -> bool:
        """Remove Prism integration from Maya installation.
        
        Deletes Prism module file, scripts, and shelf from Maya folder.
        
        Args:
            installPath: Path to Maya preferences folder
            
        Returns:
            True if removal successful, False otherwise
        """
        try:
            modPath = os.path.join(installPath, "modules", "Prism.mod")
            initPy = os.path.join(installPath, "scripts", "PrismInit.py")
            initPyc = os.path.join(installPath, "scripts", "PrismInit.pyc")
            shelfpath = os.path.join(installPath, "prefs", "shelves", "shelf_Prism.mel")

            for i in [modPath, initPy, initPyc, shelfpath]:
                if os.path.exists(i):
                    os.remove(i)

            userSetup = os.path.join(installPath, "scripts", "userSetup.py")
            self.core.integration.removeIntegrationData(filepath=userSetup)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            msgStr = (
                "Errors occurred during the removal of the Maya integration.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
            return False

    def updateInstallerUI(self, userFolders: Dict[str, str], pItem: Any) -> Optional[bool]:
        """Update installer UI with detected Maya versions.
        
        Scans for Maya installations and adds them to installer tree.
        
        Args:
            userFolders: Dict with paths like {"Documents": path}
            pItem: Parent QTreeWidgetItem to add Maya items to
            
        Returns:
            False on error, None on success
        """
        try:
            if platform.system() == "Windows":
                mayaPath = [
                    os.path.join(userFolders["Documents"], "maya", "2022"),
                    os.path.join(userFolders["Documents"], "maya", "2023"),
                    os.path.join(userFolders["Documents"], "maya", "2024"),
                    os.path.join(userFolders["Documents"], "maya", "2025"),
                    os.path.join(userFolders["Documents"], "maya", "2026"),
                    os.path.join(userFolders["Documents"], "maya", "2027"),
                ]
            elif platform.system() == "Linux":
                userName = (
                    os.environ["SUDO_USER"]
                    if "SUDO_USER" in os.environ
                    else os.environ["USER"]
                )
                mayaPath = [
                    os.path.join("/home", userName, "maya", "2022"),
                    os.path.join("/home", userName, "maya", "2023"),
                    os.path.join("/home", userName, "maya", "2024"),
                    os.path.join("/home", userName, "maya", "2025"),
                    os.path.join("/home", userName, "maya", "2026"),
                    os.path.join("/home", userName, "maya", "2027"),
                ]
            elif platform.system() == "Darwin":
                userName = (
                    os.environ["SUDO_USER"]
                    if "SUDO_USER" in os.environ
                    else os.environ["USER"]
                )
                mayaPath = [
                    "/Users/%s/Library/Preferences/Autodesk/maya/2022" % userName,
                    "/Users/%s/Library/Preferences/Autodesk/maya/2023" % userName,
                    "/Users/%s/Library/Preferences/Autodesk/maya/2024" % userName,
                    "/Users/%s/Library/Preferences/Autodesk/maya/2025" % userName,
                    "/Users/%s/Library/Preferences/Autodesk/maya/2026" % userName,
                    "/Users/%s/Library/Preferences/Autodesk/maya/2027" % userName,
                ]

            mayaItem = QTreeWidgetItem(["Maya"])
            mayaItem.setCheckState(0, Qt.Checked)
            pItem.addChild(mayaItem)

            mayacItem = QTreeWidgetItem(["Custom"])
            mayacItem.setToolTip(0, 'e.g. "%s"' % self.examplePath)
            mayacItem.setToolTip(1, 'e.g. "%s"' % self.examplePath)
            mayacItem.setText(1, "< doubleclick to browse path >")
            mayacItem.setCheckState(0, Qt.Unchecked)
            mayaItem.addChild(mayacItem)
            mayaItem.setExpanded(True)

            activeVersion = False
            for i in mayaPath:
                if not os.path.exists(i):
                    continue

                mayavItem = QTreeWidgetItem([i[-4:]])
                mayavItem.setCheckState(0, Qt.Checked)
                mayavItem.setText(1, i)
                mayavItem.setToolTip(0, i)
                activeVersion = True
                mayaItem.addChild(mayavItem)

            if not activeVersion:
                mayaItem.setCheckState(0, Qt.Unchecked)
                mayacItem.setFlags(~Qt.ItemIsEnabled)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = QMessageBox.warning(
                self.core.messageParent,
                "Prism Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s"
                % (__file__, str(e), exc_type, exc_tb.tb_lineno),
            )
            return False

    def installerExecute(self, mayaItem: Any, result: Dict[str, Any]) -> Any:
        """Execute integration installation for checked Maya versions.
        
        Args:
            mayaItem: QTreeWidgetItem containing Maya versions to install
            result: Dict to store installation results
            
        Returns:
            List of successfully installed paths, or False on error
        """
        try:
            mayaPaths = []
            installLocs = []

            if mayaItem.checkState(0) != Qt.Checked:
                return installLocs

            for i in range(mayaItem.childCount()):
                item = mayaItem.child(i)
                if item.checkState(0) == Qt.Checked and os.path.exists(item.text(1)):
                    mayaPaths.append(item.text(1))

            for i in mayaPaths:
                result["Maya integration"] = self.core.integration.addIntegration(
                    self.plugin.pluginName, path=i, quiet=True
                )
                if result["Maya integration"]:
                    installLocs.append(i)

            return installLocs
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = QMessageBox.warning(
                self.core.messageParent,
                "Prism Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s"
                % (__file__, str(e), exc_type, exc_tb.tb_lineno),
            )
            return False
