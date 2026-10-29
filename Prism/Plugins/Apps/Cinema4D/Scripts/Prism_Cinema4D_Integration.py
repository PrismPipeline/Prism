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
from typing import Any, List, Optional

if platform.system() == "Windows":
    import winreg as _winreg

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_Cinema4D_Integration(object):
    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize Cinema4D integration.
        
        Sets up integration manager for installing/removing Cinema4D plugin.
        
        Args:
            core: Prism core instance
            plugin: Plugin instance
        """
        self.core = core
        self.plugin = plugin

        if platform.system() == "Windows":
            self.examplePath = self.getExamplePath()
        elif platform.system() == "Linux":
            self.examplePath = os.path.join(
                os.path.expanduser("~"), ".config", "Maxon", "Maxon Cinema4D 2026"
            )
        elif platform.system() == "Darwin":
            self.examplePath = os.path.join(
                os.path.expanduser("~"),
                "Library",
                "Preferences",
                "Maxon",
                "Maxon Cinema4D 2026",
            )

    @err_catcher(name=__name__)
    def getExamplePath(self) -> str:
        """Get example Cinema4D user preferences path.
        
        Returns latest Maxon Cinema 4D version path from APPDATA, or default 2026.
        
        Returns:
            Example user preferences directory path
        """
        base = (
            os.environ["APPDATA"] + "\\Maxon"
        )

        paths = glob.glob(base + "\\Maxon Cinema 4D *")
        if paths:
            examplePath = sorted(paths)[-1]
        else:
            examplePath = base + "\\Maxon Cinema4D 2026"

        return examplePath

    @err_catcher(name=__name__)
    def getExecutable(self) -> str:
        """Get path to Cinema4D.exe.
        
        Returns:
            Path to Cinema4D executable, or empty string if not found
        """
        execPath = ""
        if platform.system() == "Windows":
            base = self.getCinema4DPath() or ""
            defaultpath = os.path.join(base, "Cinema4D.exe")
            if os.path.exists(defaultpath):
                execPath = defaultpath

        return execPath

    @err_catcher(name=__name__)
    def getCinema4DPath(self) -> Optional[str]:
        """Get first Cinema4D installation path.
        
        Returns:
            First Cinema4D install path, or None if not found
        """
        paths = self.getCinema4DPaths()
        if not paths:
            return

        return paths[0]

    @err_catcher(name=__name__)
    def getCinema4DPaths(self) -> List[str]:
        """Get all Cinema4D installation paths from Windows registry.
        
        Reads registry at SOFTWARE\\Maxon to find all numeric Cinema 4D versions.
        
        Returns:
            List of installation directory paths, or empty list if none found
        """
        try:
            key = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Maxon",
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )

            versions = []
            try:
                i = 0
                while True:
                    vers = _winreg.EnumKey(key, i)
                    if vers.replace("Maxon Cinema 4D ", "").isnumeric():
                        versions.append(vers)

                    i += 1
            except WindowsError:
                pass

            paths = []
            for version in versions:
                key = _winreg.OpenKey(
                    _winreg.HKEY_LOCAL_MACHINE,
                    "SOFTWARE\\Maxon\\%s" % version,
                    0,
                    _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
                )

                try:
                    installDir = _winreg.QueryValueEx(key, "Location")[0]
                except:
                    continue

                paths.append(installDir)

            return paths
        except Exception:
            return []

    def addIntegration(self, installPath: str) -> bool:
        """Install Prism integration into Cinema4D.
        
        Copies Prism.pyp plugin file to Cinema4D plugins directory, replacing
        PRISMROOT placeholder with actual Prism installation path.
        
        Args:
            installPath: Cinema4D installation directory path
            
        Returns:
            True if installation successful, False otherwise
        """
        try:
            integrationBase = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Integration"
            )
            integrationBase = os.path.realpath(integrationBase)
            addedFiles = []

            initpath = os.path.join(installPath, "plugins/Prism/Prism.pyp")
            if not os.path.exists(os.path.dirname(initpath)):
                os.makedirs(os.path.dirname(initpath))

            if os.path.exists(initpath):
                os.remove(initpath)

            origInitFile = os.path.join(integrationBase, "Prism.pyp")
            shutil.copy2(origInitFile, initpath)
            addedFiles.append(initpath)

            with open(initpath, "r") as init:
                initStr = init.read()

            with open(initpath, "w") as init:
                initStr = initStr.replace(
                    "PRISMROOT", '"%s"' % self.core.prismRoot.replace("\\", "/")
                )
                init.write(initStr)

            if platform.system() in ["Linux", "Darwin"]:
                for i in addedFiles:
                    os.chmod(i, 0o777)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            msgStr = (
                "Errors occurred during the installation of the Cinema4D integration.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."
            self.core.popup(msgStr)
            return False

    @err_catcher(name=__name__)
    def getIntegrationStatus(self, path: str) -> str:
        """Compare the installed plugin script with the configured Prism template."""
        installedFile = os.path.join(path, "plugins", "Prism", "Prism.pyp")
        if not os.path.isfile(installedFile):
            return "not added"

        integrationBase = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Integration")
        prismRoot = self.core.prismRoot.replace("\\", "/")
        with open(os.path.join(integrationBase, "Prism.pyp"), "r") as stream:
            expected = stream.read().replace("PRISMROOT", f'"{prismRoot}"')
        with open(installedFile, "r") as stream:
            installed = stream.read()
        return "added" if installed == expected else "update needed"

    def removeIntegration(self, installPath: str) -> bool:
        """Remove Prism integration from Cinema4D.
        
        Deletes Prism.pyp plugin file from Cinema4D plugins directory.
        
        Args:
            installPath: Cinema4D installation directory path
            
        Returns:
            True if removal successful, False otherwise
        """
        try:
            initPy = os.path.join(installPath, "plugins/Prism/Prism.pyp")
            for i in [initPy]:
                if os.path.exists(i):
                    os.remove(i)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            msgStr = (
                "Errors occurred during the removal of the Cinema4D integration.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."
            self.core.popup(msgStr)
            return False

    def updateInstallerUI(self, userFolders: Any, pItem: Any) -> None:
        """Populate Cinema4D section in Prism installer UI.
        
        Adds tree items for each detected Cinema4D installation and custom path option.
        
        Args:
            userFolders: User folders configuration
            pItem: Parent tree widget item to populate
        """
        try:
            pluginItem = QTreeWidgetItem(["Cinema4D"])
            pluginItem.setCheckState(0, Qt.Checked)
            pItem.addChild(pluginItem)

            pluginPaths = self.getCinema4DPaths() or []
            pluginCustomItem = QTreeWidgetItem(["Custom"])
            pluginCustomItem.setToolTip(0, 'e.g. "%s"' % self.examplePath)
            pluginCustomItem.setToolTip(1, 'e.g. "%s"' % self.examplePath)
            pluginCustomItem.setText(1, "< doubleclick to browse path >")
            pluginCustomItem.setCheckState(0, Qt.Unchecked)
            pluginItem.addChild(pluginCustomItem)
            pluginItem.setExpanded(True)

            activeVersion = False
            for pluginPath in pluginPaths:
                pluginVItem = QTreeWidgetItem([os.path.basename(pluginPath).replace("Maxon Cinema 4D ", "")])
                pluginItem.addChild(pluginVItem)

                pluginVItem.setCheckState(0, Qt.Checked)
                pluginVItem.setText(1, pluginPath)
                pluginVItem.setToolTip(0, pluginPath)
                pluginVItem.setText(1, pluginPath)
                activeVersion = True

            if not activeVersion:
                pluginItem.setCheckState(0, Qt.Unchecked)
                pluginCustomItem.setFlags(~Qt.ItemIsEnabled)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s" % (__file__, str(e), exc_type, exc_tb.tb_lineno)
            self.core.popup(msg)
            return False

    def installerExecute(self, pluginItem: Any, result: dict) -> List[str]:
        """Execute Cinema4D integration during Prism installation.
        
        Installs Prism into all checked Cinema4D paths from installer UI.
        
        Args:
            pluginItem: Tree widget item with checkbox states
            result: Dictionary to store installation results
            
        Returns:
            List of successfully integrated installation paths
        """
        try:
            pluginPaths = []
            installLocs = []

            if pluginItem.checkState(0) != Qt.Checked:
                return installLocs

            for i in range(pluginItem.childCount()):
                item = pluginItem.child(i)
                if item.checkState(0) == Qt.Checked and os.path.exists(item.text(1)):
                    pluginPaths.append(item.text(1))

            for i in pluginPaths:
                result["Cinema4D integration"] = self.core.integration.addIntegration(
                    self.plugin.pluginName, path=i, quiet=True
                )
                if result["Cinema4D integration"]:
                    installLocs.append(i)

            return installLocs
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s" % (__file__, str(e), exc_type, exc_tb.tb_lineno)
            self.core.popup(msg)
            return False
