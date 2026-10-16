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
import re
import sys
import platform
from typing import Any, Dict, List, Union

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_Nuke_Integration(object):
    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize Nuke integration handler.
        
        Sets up the integration with platform-specific .nuke directory paths
        for menu.py and init.py integration files.
        
        Args:
            core: The Prism core instance
            plugin: The plugin instance
        """
        self.core = core
        self.plugin = plugin
        if platform.system() == "Windows":
            self.examplePath = os.path.join(os.environ["userprofile"], ".nuke")
        elif platform.system() == "Linux":
            userName = (
                os.environ["SUDO_USER"]
                if "SUDO_USER" in os.environ
                else os.environ["USER"]
            )
            self.examplePath = os.path.join("/home", userName, ".nuke")
        elif platform.system() == "Darwin":
            userName = (
                os.environ["SUDO_USER"]
                if "SUDO_USER" in os.environ
                else os.environ["USER"]
            )
            self.examplePath = "/Users/%s/.nuke" % userName

    @err_catcher(name=__name__)
    def getExecutable(self) -> str:
        """Get the default Nuke executable path.
        
        Returns:
            Path to the Nuke executable, or empty string if not on Windows
        """
        execPath = ""
        if platform.system() == "Windows":
            execPath = "C:\\Program Files\\Nuke15.0v4\\Nuke15.0.exe"

        return execPath

    def addIntegration(self, installPath: str) -> bool:
        """Install Prism integration to a Nuke .nuke directory.
        
        Installs menu.py and init.py files with Prism initialization code.
        
        Args:
            installPath: Path to the .nuke directory
            
        Returns:
            True if installation succeeded, False otherwise
        """
        try:
            if not os.path.exists(installPath):
                QMessageBox.warning(
                    self.core.messageParent,
                    "Prism Integration",
                    "Invalid Nuke path: %s.\nThe path doesn't exist." % installPath,
                    QMessageBox.Ok,
                )
                return False

            integrationBase = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Integration"
            )
            integrationBase = os.path.realpath(integrationBase)
            addedFiles = []

            integrationFiles = ["menu.py", "init.py"]

            for integrationFile in integrationFiles:
                origMenuFile = os.path.join(integrationBase, integrationFile)
                with open(origMenuFile, "r") as mFile:
                    initStr = mFile.read()

                menuFile = os.path.join(installPath, integrationFile)
                self.core.integration.removeIntegrationData(filepath=menuFile)

                with open(menuFile, "a") as initfile:
                    initStr = initStr.replace(
                        "PRISMROOT", '"%s"' % self.core.prismRoot.replace("\\", "/")
                    )
                    initfile.write(initStr)

                addedFiles.append(menuFile)

            if platform.system() in ["Linux", "Darwin"]:
                for i in addedFiles:
                    os.chmod(i, 0o777)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            msgStr = (
                "Errors occurred during the installation of the Nuke integration.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
            return False

    def removeIntegration(self, installPath: str) -> bool:
        """Remove Prism integration from a Nuke .nuke directory.
        
        Removes integration code from menu.py and init.py, and cleans up
        legacy files.
        
        Args:
            installPath: Path to the .nuke directory
            
        Returns:
            True if removal succeeded, False otherwise
        """
        try:
            # kept for backwards compatibility
            gizmo = os.path.join(installPath, "WritePrism.gizmo")

            for i in [gizmo]:
                if os.path.exists(i):
                    os.remove(i)

            integrationFiles = ["menu.py", "init.py"]

            for integrationFile in integrationFiles:
                fpath = os.path.join(installPath, integrationFile)

                self.core.integration.removeIntegrationData(filepath=fpath)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            msgStr = (
                "Errors occurred during the removal of the Nuke integration.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
            return False

    def updateInstallerUI(self, userFolders: Dict[str, str], pItem: QTreeWidgetItem) -> None:
        """Update the installer UI with Nuke integration options.
        
        Adds a tree item for Nuke with its .nuke directory path.
        
        Args:
            userFolders: Dictionary of user folder paths
            pItem: Parent tree widget item to add Nuke item to
        """
        try:
            nukeItem = QTreeWidgetItem(["Nuke"])
            pItem.addChild(nukeItem)

            if platform.system() == "Windows":
                nukePath = os.path.join(userFolders["UserProfile"], ".nuke")
            elif platform.system() == "Linux":
                userName = (
                    os.environ["SUDO_USER"]
                    if "SUDO_USER" in os.environ
                    else os.environ["USER"]
                )
                nukePath = os.path.join("/home", userName, ".nuke")
            elif platform.system() == "Darwin":
                userName = (
                    os.environ["SUDO_USER"]
                    if "SUDO_USER" in os.environ
                    else os.environ["USER"]
                )
                nukePath = "/Users/%s/.nuke" % userName

            if os.path.exists(nukePath):
                nukeItem.setCheckState(0, Qt.Checked)
                nukeItem.setText(1, nukePath)
                nukeItem.setToolTip(0, nukePath)
            else:
                nukeItem.setCheckState(0, Qt.Unchecked)
                nukeItem.setText(1, "< doubleclick to browse path >")
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = QMessageBox.warning(
                self.core.messageParent,
                "Prism Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s"
                % (__file__, str(e), exc_type, exc_tb.tb_lineno),
            )
            return False

    def installerExecute(self, nukeItem: QTreeWidgetItem, result: Dict[str, Any]) -> Union[List[str], bool]:
        """Execute Nuke integration installation.
        
        Called by the Prism installer to perform the integration.
        
        Args:
            nukeItem: Tree widget item containing Nuke integration settings
            result: Dictionary to store integration results
            
        Returns:
            List of installed paths on success, False on error
        """
        try:
            installLocs = []

            if nukeItem.checkState(0) == Qt.Checked and os.path.exists(
                nukeItem.text(1)
            ):
                result["Nuke integration"] = self.core.integration.addIntegration(
                    self.plugin.pluginName, path=nukeItem.text(1), quiet=True
                )
                if result["Nuke integration"]:
                    installLocs.append(nukeItem.text(1))

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

    @err_catcher(name=__name__)
    def getIntegrationStatus(self, path: str) -> str:
        """Check the integration status for the given path.

        Args:
            path: Path to check for integration

        Returns:
            "added", "not added", or "update needed" based on installed Prism blocks.
        """
        integrationBase = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Integration")
        blockPattern = re.compile(r"#\s*>>>PrismStart.*?#\s*<<<PrismEnd", re.DOTALL)
        foundIntegration = False
        currentIntegration = True
        for filename in ["menu.py", "init.py"]:
            installedFile = os.path.join(path, filename)
            if not os.path.isfile(installedFile):
                currentIntegration = False
                continue

            with open(installedFile, "r") as stream:
                installed = stream.read()

            blocks = blockPattern.findall(installed)
            if not re.search(r"#\s*>>>PrismStart", installed):
                currentIntegration = False
                continue

            foundIntegration = True
            with open(os.path.join(integrationBase, filename), "r") as stream:
                expected = stream.read().replace(
                    "PRISMROOT", '"%s"' % self.core.prismRoot.replace("\\", "/")
                )

            if blocks != blockPattern.findall(expected):
                currentIntegration = False

        if not foundIntegration:
            return "not added"

        return "added" if currentIntegration else "update needed"
