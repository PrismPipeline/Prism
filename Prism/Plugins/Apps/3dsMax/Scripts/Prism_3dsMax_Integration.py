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
import glob
from typing import Any, List, Dict

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

if platform.system() == "Windows":
    if sys.version[0] == "3":
        import winreg as _winreg
    else:
        import _winreg

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_3dsMax_Integration(object):
    """Integration functionality for 3ds Max plugin.
    
    Handles DCC installation/removal, registry access, and integration
    with 3ds Max preferences and startup scripts.
    
    Attributes:
        core: PrismCore instance
        plugin: Plugin instance
        examplePath (str): Example path for 3ds Max preferences (Windows only)
    """

    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize 3ds Max integration.
        
        Args:
            core: PrismCore instance.
            plugin: Plugin instance.
        """
        self.core = core
        self.plugin = plugin

        if platform.system() == "Windows":
            self.examplePath = (
                os.environ["localappdata"] + "\\Autodesk\\3dsMax\\2027 - 64bit"
            )

    @err_catcher(name=__name__)
    def getExecutable(self) -> str:
        """Get path to 3ds Max executable.
        
        Returns:
            Path to 3dsmax.exe or empty string if not found.
        """
        execPath = ""
        if platform.system() == "Windows":
            defaultpath = os.path.join(self.get3dsMaxPath(), "3dsmax.exe")
            if os.path.exists(defaultpath):
                execPath = defaultpath

        return execPath

    @err_catcher(name=__name__)
    def get3dsMaxPath(self) -> str:
        """Get 3ds Max installation directory from Windows registry.
        
        Returns:
            Install directory path or empty string if not found.
        """
        try:
            key = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Autodesk\\3dsMax",
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )
            versions = []
            try:
                i = 0
                while True:
                    vers = _winreg.EnumKey(key, i)
                    if sys.version[0] == "2":
                        vers = unicode(vers)

                    if vers.replace(".", "").isnumeric():
                        versions.append(vers)
                    i += 1
            except WindowsError:
                pass

            validVersion = versions[-1]
            key = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Autodesk\\3dsMax\\%s" % validVersion,
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )

            installDir = (_winreg.QueryValueEx(key, "Installdir"))[0]
            return installDir
        except:
            return ""

    def addIntegration(self, installPath: str) -> bool:
        """Install Prism integration to 3ds Max preferences folder.
        
        Copies startup scripts, Python init files, menu macros to the
        specified 3ds Max preferences path.
        
        Args:
            installPath: Path to 3ds Max preferences folder.
        
        Returns:
            True if installation successful, False otherwise.
        """
        try:
            maxpath = os.path.join(installPath, "ENU", "scripts", "startup")

            if not os.path.exists(maxpath) or not os.path.exists(
                os.path.join(os.path.dirname(os.path.dirname(maxpath)), "usermacros")
            ):
                msgStr = (
                    "Invalid 3dsMax path:\n%s.\n\nThe path has to be the 3dsMax preferences folder, which usually looks like this: (with your username and 3dsMax version):\n\n%s"
                    % (installPath, self.examplePath)
                )
                self.core.popup(msgStr, title="Prism Integration")
                return False

            integrationBase = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Integration"
            )
            integrationBase = os.path.realpath(integrationBase)

            # 	print "write max files: %s" % maxpath
            initprism = os.path.join(maxpath, "initPrism.ms")
            if os.path.exists(initprism):
                os.remove(initprism)

            origInitFile = os.path.join(integrationBase, "initPrism.ms")
            shutil.copy2(origInitFile, initprism)

            initPy = os.path.join(maxpath, "python", "initPrism.py")

            if not os.path.exists(os.path.dirname(initPy)):
                os.mkdir(os.path.dirname(initPy))

            if os.path.exists(initPy):
                os.remove(initPy)

            origInitFile = os.path.join(integrationBase, "initPrism.py")
            shutil.copy2(origInitFile, initPy)

            with open(initPy, "r") as init:
                initStr = init.read()

            with open(initPy, "w") as init:
                initStr = initStr.replace(
                    "PRISMROOT", '"%s"' % self.core.prismRoot.replace("\\", "/")
                )
                init.write(initStr)

            prismMenu = os.path.join(maxpath, "PrismMenu.ms")
            if os.path.exists(prismMenu):
                os.remove(prismMenu)

            origMenuFile = os.path.join(integrationBase, "PrismMenu.ms")
            shutil.copy2(origMenuFile, prismMenu)

            macroPath = os.path.abspath(
                os.path.join(
                    maxpath, os.pardir, os.pardir, "usermacros", "PrismMacros.mcr"
                )
            )

            if os.path.exists(macroPath):
                os.remove(macroPath)

            origMacroFile = os.path.join(integrationBase, "PrismMacros.mcr")
            shutil.copy2(origMacroFile, macroPath)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            msgStr = (
                "Errors occurred during the installation of the 3ds Max integration.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
            return False

    @err_catcher(name=__name__)
    def getIntegrationStatus(self, path: str) -> str:
        """Compare installed Prism startup and macro files with current templates."""
        integrationBase = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Integration")
        files = {
            "initPrism.ms": os.path.join(path, "ENU", "scripts", "startup", "initPrism.ms"),
            "initPrism.py": os.path.join(path, "ENU", "scripts", "startup", "python", "initPrism.py"),
            "PrismMenu.ms": os.path.join(path, "ENU", "scripts", "startup", "PrismMenu.ms"),
            "PrismMacros.mcr": os.path.join(path, "ENU", "usermacros", "PrismMacros.mcr"),
        }
        foundIntegration = False
        currentIntegration = True
        for filename, installedFile in files.items():
            if not os.path.isfile(installedFile):
                currentIntegration = False
                continue

            foundIntegration = True
            with open(installedFile, "r") as stream:
                installed = stream.read()
            with open(os.path.join(integrationBase, filename), "r") as stream:
                expected = stream.read()
            if filename == "initPrism.py":
                prismRoot = self.core.prismRoot.replace("\\", "/")
                expected = expected.replace("PRISMROOT", f'"{prismRoot}"')
            if installed != expected:
                currentIntegration = False

        if not foundIntegration:
            return "not added"
        return "added" if currentIntegration else "update needed"

    def removeIntegration(self, installPath: str) -> bool:
        """Remove Prism integration from 3ds Max preferences folder.
        
        Removes all Prism-related files from 3ds Max startup and macro folders.
        
        Args:
            installPath: Path to 3ds Max preferences folder.
        
        Returns:
            True if removal successful, False otherwise.
        """
        try:
            installPath = os.path.join(installPath, "ENU", "scripts", "startup")

            if not os.path.exists(installPath):
                return True

            initPy = os.path.join(installPath, "python", "initPrism.py")
            initMs = os.path.join(installPath, "initPrism.ms")
            menuMs = os.path.join(installPath, "PrismMenu.ms")
            macroMcr = os.path.join(
                os.path.dirname(os.path.dirname(installPath)),
                "usermacros",
                "PrismMacros.mcr",
            )

            for i in [initPy, initMs, menuMs, macroMcr]:
                if os.path.exists(i):
                    os.remove(i)

            uninstallStr = """
if menuMan.findMenu "Prism" != undefined then
(
    menuMan.unRegisterMenu (menuMan.findMenu "Prism")
)

curPath = getThisScriptFilename()
deleteFile curPath
"""

            uninstallPath = os.path.join(installPath, "uninstallPrism.ms")

            if os.path.exists(uninstallPath):
                os.remove(uninstallPath)

            with open(uninstallPath, "w") as uninstallFile:
                uninstallFile.write(uninstallStr)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msgStr = (
                "Errors occurred during the removal of the 3ds Max integration.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
            return False

    @err_catcher(name=__name__)
    def getPreferencesPaths(self) -> List[List[str]]:
        """Get all 3ds Max preferences paths found on system.
        
        Returns:
            List of [preferences_path, version_string] pairs.
        """
        paths = []
        basepath = os.environ["localappdata"] + "\\Autodesk\\3dsMax\\"

        for path in glob.glob(basepath + "*"):
            try:
                version = int(os.path.basename(path)[:4])
            except:
                continue

            paths.append([path, str(version)])

        return paths

    def updateInstallerUI(self, userFolders: Any, pItem: QTreeWidgetItem) -> None:
        """Update installer UI with 3ds Max installation options.
        
        Args:
            userFolders: User folders data.
            pItem: Parent tree widget item.
        """
        try:
            maxItem = QTreeWidgetItem(["3dsMax"])
            maxItem.setCheckState(0, Qt.Checked)
            pItem.addChild(maxItem)

            maxcItem = QTreeWidgetItem(["Custom"])
            maxcItem.setToolTip(0, 'e.g. "%s"' % self.examplePath)
            maxcItem.setToolTip(1, 'e.g. "%s"' % self.examplePath)
            maxcItem.setText(1, "< doubleclick to browse path >")
            maxcItem.setCheckState(0, Qt.Unchecked)
            maxItem.addChild(maxcItem)
            maxItem.setExpanded(True)

            activeVersion = False
            for path in self.getPreferencesPaths():
                if not os.path.exists(path[0]):
                    continue

                maxvItem = QTreeWidgetItem([path[1]])
                maxItem.addChild(maxvItem)
                maxvItem.setCheckState(0, Qt.Checked)
                maxvItem.setText(1, path[0])
                maxvItem.setToolTip(0, path[0])
                activeVersion = True

            if not activeVersion:
                maxItem.setCheckState(0, Qt.Unchecked)
                maxcItem.setFlags(~Qt.ItemIsEnabled)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            QMessageBox.warning(
                self.core.messageParent,
                "Prism Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s"
                % (__file__, str(e), exc_type, exc_tb.tb_lineno),
            )
            return False

    def installerExecute(self, maxItem: QTreeWidgetItem, result: Dict) -> List[str]:
        """Execute integration installation for checked items.
        
        Args:
            maxItem: Tree widget item containing 3ds Max paths.
            result: Dictionary to store installation results.
        
        Returns:
            List of successfully installed paths.
        """
        try:
            maxPaths = []
            installLocs = []

            if maxItem.checkState(0) != Qt.Checked:
                return installLocs

            for i in range(maxItem.childCount()):
                item = maxItem.child(i)
                if item.checkState(0) == Qt.Checked and os.path.exists(item.text(1)):
                    maxPaths.append(item.text(1))

            for i in maxPaths:
                result["3dsMax integration"] = self.core.integration.addIntegration(
                    self.plugin.pluginName, path=i, quiet=True
                )
                if result["3dsMax integration"]:
                    installLocs.append(i)

            return installLocs
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            QMessageBox.warning(
                self.core.messageParent,
                "Prism Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s"
                % (__file__, str(e), exc_type, exc_tb.tb_lineno),
            )
            return False
