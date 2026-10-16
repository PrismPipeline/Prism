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
import subprocess
import sys
import platform
import logging
from typing import Any, List, Optional, Union

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

if platform.system() == "Windows":
    import winreg as _winreg

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


logger = logging.getLogger(__name__)


class Prism_Photoshop_Integration(object):
    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize Photoshop integration module.
        
        Sets up integration paths for Windows or macOS.
        
        Args:
            core: Prism core instance
            plugin: Plugin instance (self)
        """
        self.core = core
        self.plugin = plugin

        if platform.system() == "Windows":
            self.examplePath = str(self.getPhotoshopPath())
        elif platform.system() == "Darwin":
            installPath = str(self.getPhotoshopPath())
            # self.examplePath = os.path.expanduser("~/Library/Application Support/Adobe/%s" % os.path.basename(installPath))
            self.examplePath = installPath

    @err_catcher(name=__name__)
    def getPhotoshopPath(self, single: bool = True) -> Optional[Union[str, List[str]]]:
        """Get Photoshop installation path(s) from system registry or filesystem.
        
        On Windows, reads registry SOFTWARE\\\\Adobe\\\\Photoshop for installation paths.
        On macOS, searches /Applications for Adobe Photoshop folders.
        
        Args:
            single: If True, return only the first path found; if False, return all paths
            
        Returns:
            Single path string if single=True, list of paths if single=False, or None if none found
        """
        try:
            psPaths = []
            if platform.system() == "Windows":
                key = _winreg.OpenKey(
                    _winreg.HKEY_LOCAL_MACHINE,
                    "SOFTWARE\\Adobe\\Photoshop",
                    0,
                    _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
                )
                idx = 0
                while True:
                    try:
                        psVersion = _winreg.EnumKey(key, idx)
                        psKey = _winreg.OpenKey(
                            _winreg.HKEY_LOCAL_MACHINE,
                            "SOFTWARE\\Adobe\\Photoshop\\" + psVersion,
                            0,
                            _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
                        )
                        path = _winreg.QueryValueEx(psKey, "ApplicationPath")[0]
                        path = os.path.normpath(path)
                        psPaths.append(path)
                        idx += 1
                    except:
                        break
            elif platform.system() == "Darwin":
                for foldercont in os.walk("/Applications"):
                    for folder in reversed(sorted(foldercont[1])):
                        if folder.startswith("Adobe Photoshop"):
                            psPaths.append(os.path.join(foldercont[0], folder))
                            if single:
                                break
                    break

            if single:
                return psPaths[0] if psPaths else None
            else:
                return psPaths if psPaths else []
        except:
            return None

    def addIntegration(self, installPath: str) -> Union[str, bool]:
        """Add Prism integration to Photoshop.
        
        Delegates to addUXP() for UXP plugin or addCEP() for CEP integration.
        
        Args:
            installPath: Either "UXP" string or path to Photoshop installation
            
        Returns:
            "UXP" string if UXP installed, True if CEP installed, False on failure
        """
        if installPath == "UXP":
            return self.addUXP()
        else:
            return self.addCEP(installPath)

    def addUXP(self) -> Union[str, bool]:
        """Install Prism UXP plugin to Photoshop.
        
        Uses Adobe's UPI installer agent to install the .ccx plugin package.
        Starts the server after installation.
        
        Returns:
            "UXP" string on success, False on failure
        """
        exe = self.getUXPExe()
        if not os.path.exists(exe):
            msg = "Unable to find UPI installer agent at path: %s.\nPlease make sure that Adobe Creative Cloud is installed and up to date." % exe
            self.core.popup(msg, title="Prism Integration")
            return False

        while True:
            try:
                subprocess.run([exe, "/install", os.path.join(self.pluginDirectory, "Integration", "UXP", "com.prism.photoshop_PS.ccx")], check=True)
            except Exception as e:
                result = self.core.popupQuestion(f"Failed to install UXP plugin for Photoshop.\n\nError: {str(e)}", buttons=["Retry", "Cancel"], escapeButton="Cancel", icon=QMessageBox.Warning, default="Cancel")
                if result == "Retry":
                    continue
                elif result == "Cancel":
                    return False
            
            break

        self.startServer()
        return "UXP"

    def addCEP(self, installPath: str) -> bool:
        """Install Prism CEP scripts to Photoshop.
        
        Copies JSX script files to Photoshop's Scripts folder with paths customized
        for the current Prism installation.
        
        Args:
            installPath: Path to Photoshop installation directory
            
        Returns:
            True on successful installation, False on failure
            
        Raises:
            Exception: If file operations fail during installation
        """
        try:
            if not os.path.exists(installPath):
                msg = "Invalid Photoshop path: %s.\nThe path doesn't exist." % installPath
                self.core.popup(msg, title="Prism Integration")
                return False

            integrationBase = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Integration"
            )
            integrationBase = os.path.realpath(integrationBase)

            if platform.system() == "Windows":
                osName = "Windows"
                scriptdir = os.path.join(installPath, "Presets", "Scripts")
            elif platform.system() == "Darwin":
                osName = "Mac"
                # scriptdir = os.path.expanduser("~/Library/Application Support/Adobe/%s/Presets/Scripts" % os.path.basename(installPath))
                scriptdir = os.path.join(installPath, "Presets", "Scripts")

            cmds = []
            if not os.path.exists(scriptdir):
                cmd = {"type": "createFolder", "args": [scriptdir]}
                cmds.append(cmd)

            for filename in [
                "Prism - 1 Tools.jsx",
                "Prism - 2 Save Version.jsx",
                "Prism - 3 Save Extended.jsx",
                "Prism - 4 Export.jsx",
                "Prism - 5 Project Browser.jsx",
                "Prism - 6 Settings.jsx",
            ]:
                origFile = os.path.join(integrationBase, osName, filename)
                targetFile = os.path.join(scriptdir, filename)

                if os.path.exists(targetFile):
                    cmd = {
                        "type": "removeFile",
                        "args": [targetFile],
                        "validate": False,
                    }
                    cmds.append(cmd)

                cmd = {"type": "copyFile", "args": [origFile, targetFile]}
                cmds.append(cmd)

                with open(origFile, "r") as init:
                    initStr = init.read()

                initStr = initStr.replace("PLUGINROOT", "%s" % os.path.dirname(self.pluginPath).replace("\\", "/"))
                initStr = initStr.replace("PRISMROOT", "%s" % self.core.prismRoot)
                initStr = initStr.replace("PRISMLIBS", "%s" % self.core.prismLibs)

                cmd = {"type": "writeToFile", "args": [targetFile, initStr]}
                cmds.append(cmd)

            if platform.system() == "Windows":
                result = self.core.runFileCommands(cmds)
            else:
                script = ""
                for cmd in cmds:
                    if cmd["type"] == "writeToFile":
                        target = cmd["args"][0]
                        cmd["args"][0] = "/tmp/" + os.path.basename(cmd["args"][0])
                        self.core.runFileCommand(cmd)
                        script += '''do shell script "cp '%s' '%s'" with administrator privileges\n''' % (cmd["args"][0], target)

                logger.debug("running osascript: %s" % script)
                subprocess.run(["osascript", "-"], input=script, text=True)
                for cmd in cmds:
                    if not cmd.get("validate", True):
                        continue

                    result = self.core.validateFileCommand(cmd)
                    if not result:
                        msg = "failed to run command: %s, args: %s" % (
                            cmd["type"],
                            cmd["args"],
                        )
                        result = msg
                        break
                else:
                    result = True

            if result is True:
                return True
            elif result is False:
                return False
            else:
                raise Exception(result)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msgStr = (
                "Errors occurred during the installation of the Photoshop integration.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            self.core.popup(msgStr, title="Prism Integration")
            return False

    @err_catcher(name=__name__)
    def getIntegrationStatus(self, path: str) -> str:
        """Compare installed JSX scripts; UXP installation status is not folder-based."""
        if path == "UXP":
            return ""

        integrationBase = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Integration")
        osName = "Mac" if platform.system() == "Darwin" else "Windows"
        scriptdir = os.path.join(path, "Presets", "Scripts")
        filenames = [
            "Prism - 1 Tools.jsx",
            "Prism - 2 Save Version.jsx",
            "Prism - 3 Save Extended.jsx",
            "Prism - 4 Export.jsx",
            "Prism - 5 Project Browser.jsx",
            "Prism - 6 Settings.jsx",
        ]
        foundIntegration = False
        currentIntegration = True
        for filename in filenames:
            installedFile = os.path.join(scriptdir, filename)
            if not os.path.isfile(installedFile):
                currentIntegration = False
                continue

            foundIntegration = True
            with open(os.path.join(integrationBase, osName, filename), "r") as stream:
                expected = stream.read()
            expected = expected.replace("PLUGINROOT", os.path.dirname(self.pluginPath).replace("\\", "/"))
            expected = expected.replace("PRISMROOT", self.core.prismRoot)
            expected = expected.replace("PRISMLIBS", self.core.prismLibs)
            with open(installedFile, "r") as stream:
                if stream.read() != expected:
                    currentIntegration = False

        if not foundIntegration:
            return "not added"
        return "added" if currentIntegration else "update needed"

    def removeIntegration(self, installPath: str) -> bool:
        """Remove Prism integration from Photoshop.
        
        Delegates to removeUXPIntegration() or removeCEP() based on path.
        
        Args:
            installPath: Either "UXP" string or path to Photoshop installation
            
        Returns:
            True on successful removal, False on failure
        """
        if installPath == "UXP":
            return self.removeUXPIntegration()
        else:
            return self.removeCEP(installPath)
        
    def removeUXPIntegration(self) -> bool:
        """Remove Prism UXP plugin from Photoshop.
        
        Uses Adobe's UPI installer agent to uninstall the plugin.
        
        Returns:
            True on successful removal, False on failure
        """
        try:
            exe = self.getUXPExe()
            if not os.path.exists(exe):
                msg = "Unable to find UPI installer agent at path: %s.\nPlease make sure that Adobe Creative Cloud is installed and up to date." % exe
                self.core.popup(msg, title="Prism Integration")
                return False

            subprocess.run([exe, "/remove", "Prism Pipeline"], check=True)
            return True
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msgStr = (
                "Errors occurred during the removal of the Photoshop UXP integration.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."
            self.core.popup(msgStr, title="Prism Integration")
            return False
    
    def removeCEP(self, installPath: str) -> bool:
        """Remove Prism CEP scripts from Photoshop.
        
        Deletes all Prism JSX script files from Photoshop's Scripts folder.
        
        Args:
            installPath: Path to Photoshop installation directory
            
        Returns:
            True on successful removal, False on failure
        """
        try:
            for filename in [
                "Prism - 1 Tools.jsx",
                "Prism - 2 Save version.jsx",
                "Prism - 3 Save comment.jsx",
                "Prism - 4 Export",
                "Prism - 5 ProjectBrowser.jsx",
                "Prism - 6 Settings.jsx",
            ]:
                fPath = os.path.join(installPath, "Presets", "Scripts", filename)
                if os.path.exists(fPath):
                    os.remove(fPath)

            return True
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            msgStr = (
                "Errors occurred during the removal of the Photoshop integration.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."
            self.core.popup(msgStr, title="Prism Integration")
            return False

    def updateInstallerUI(self, userFolders: Any, pItem: Any) -> None:
        """Update the Prism installer UI with Photoshop integration options.
        
        Creates tree widget items for detected Photoshop versions and UXP option.
        
        Args:
            userFolders: User folders configuration (unused in Photoshop)
            pItem: Parent tree widget item to add Photoshop integration options to
        """
        try:
            psItem = QTreeWidgetItem(["Photoshop"])
            psItem.setCheckState(0, Qt.Checked)
            pItem.addChild(psItem)

            psPaths = self.getPhotoshopPath(single=False) or []
            uxpExe = self.getUXPExe()
            if os.path.exists(uxpExe):
                psPaths.append("UXP")

            psCustomItem = QTreeWidgetItem(["Custom"])
            psCustomItem.setToolTip(0, 'e.g. "%s"' % self.examplePath)
            psCustomItem.setToolTip(1, 'e.g. "%s"' % self.examplePath)
            psCustomItem.setText(1, "< doubleclick to browse path >")
            psCustomItem.setCheckState(0, Qt.Unchecked)
            psItem.addChild(psCustomItem)
            psItem.setExpanded(True)

            activeVersion = False
            for path in reversed(psPaths):
                name = os.path.basename(path).replace("Adobe Photoshop ", "")
                psVItem = QTreeWidgetItem([name])
                psItem.addChild(psVItem)

                if os.path.exists(path) or path == "UXP":
                    psVItem.setCheckState(0, Qt.Checked)
                    psVItem.setText(1, path)
                    psVItem.setToolTip(0, path)
                    psVItem.setText(1, path)
                    activeVersion = True
                else:
                    psVItem.setCheckState(0, Qt.Unchecked)
                    psVItem.setFlags(~Qt.ItemIsEnabled)

            if not activeVersion:
                psItem.setCheckState(0, Qt.Unchecked)
                psCustomItem.setFlags(~Qt.ItemIsEnabled)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s" % (__file__, str(e), exc_type, exc_tb.tb_lineno)
            self.core.popup(msg, title="Prism Installation")
            return False

    def installerExecute(self, photoshopItem: Any, result: dict) -> Union[List[str], bool]:
        """Execute Photoshop integration installation.
        
        Installs Prism to all checked Photoshop versions in the installer UI.
        
        Args:
            photoshopItem: Tree widget item containing Photoshop version checkboxes
            result: Dictionary to store installation results
            
        Returns:
            List of successfully installed paths, or False on failure
        """
        try:
            psPaths = []
            installLocs = []

            if photoshopItem.checkState(0) != Qt.Checked:
                return installLocs

            for idx in range(photoshopItem.childCount()):
                item = photoshopItem.child(idx)
                path = item.text(1)
                valid = os.path.exists(path) or path == "UXP"
                if item.checkState(0) == Qt.Checked and valid:
                    psPaths.append(path)

            for path in psPaths:
                result["Photoshop integration"] = self.core.integration.addIntegration(
                    self.plugin.pluginName, path=path, quiet=True
                )
                if result["Photoshop integration"]:
                    installLocs.append(path)

            return installLocs
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s" % (__file__, str(e), exc_type, exc_tb.tb_lineno)
            self.core.popup(msg, title="Prism Installation")
            return False
