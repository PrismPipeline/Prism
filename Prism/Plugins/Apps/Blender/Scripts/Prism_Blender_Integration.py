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
import glob
from typing import Any, List, Optional, Union

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

if platform.system() == "Windows":
    if sys.version[0] == "3":
        import winreg as _winreg
    else:
        import _winreg

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_Blender_Integration(object):
    """Blender integration management.
    
    Handles installation and removal of Prism integration files in
    Blender directories, including startup scripts and menu modifications.
    
    Attributes:
        core: PrismCore instance.
        plugin: Blender plugin instance.
        useUserPrefs: Whether to use user preferences folder.
        examplePath: Example installation path for reference.
    """
    
    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize Blender integration manager.
        
        Sets example paths based on platform.
        
        Args:
            core: PrismCore instance.
            plugin: Blender plugin instance.
        """
        self.core = core
        self.plugin = plugin

        self.useUserPrefs = True
        if platform.system() == "Windows":
            if self.useUserPrefs:
                self.examplePath = os.path.normpath(os.environ["appdata"] + "\\Blender Foundation\\Blender\\5.2")
            else:
                self.examplePath = self.getBlenderPath() or "C:/Program Files/Blender Foundation/Blender 5.2"
        elif platform.system() == "Linux":
            self.examplePath = "/usr/local/blender-5.2-linux-glibc219-x86_64/5.2"
        elif platform.system() == "Darwin":
            self.examplePath = os.path.expanduser("~/Library/Application Support/Blender/5.2")

    @err_catcher(name=__name__)
    def getExecutable(self) -> str:
        """Get Blender executable path.
        
        Returns:
            Path to blender.exe on Windows, empty string on other platforms.
        """
        execPath = ""
        if platform.system() == "Windows":
            bldPath = self.getBlenderPath()
            if bldPath:
                execPath = os.path.join(os.path.dirname(bldPath), "blender.exe")

        return execPath

    @err_catcher(name=__name__)
    def getBlenderPath(self) -> str:
        """Get Blender version path from Windows registry.
        
        Returns:
            Path to Blender version folder if found, empty string otherwise.
        """
        try:
            key = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Classes\\blendfile\\shell\\open\\command",
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )
            blenderPath = (
                (_winreg.QueryValueEx(key, ""))[0].split(' "%1"')[0].replace('"', "")
            )

            vpath = os.path.join(os.path.dirname(blenderPath), "5.2")

            if os.path.exists(vpath):
                return vpath
            else:
                return ""

        except:
            return ""

    @err_catcher(name=__name__)
    def getBlenderPaths(self) -> List[str]:
        """Get all available Blender installation paths.
        
        Searches for Blender installations and checks registry.
        
        Returns:
            List of Blender version folder paths.
        """
        blenderPaths = []
        basepath = os.path.dirname(self.examplePath)

        for path in glob.glob(basepath + "/Blender*"):
            if self.useUserPrefs:
                if os.path.exists(path + "/config"):
                    blenderPaths.append(os.path.normpath(path))
            else:
                if os.path.exists(path + "/blender.exe"):
                    blenderPaths.append(os.path.normpath(path))

        regPath = self.getBlenderPath()
        if regPath and os.path.exists(regPath) and regPath not in blenderPaths:
            blenderPaths.append(regPath)

        return blenderPaths

    def addIntegration(self, installPath: str) -> bool:
        """Install Prism integration into Blender.
        
        Copies integration files and modifies Blender startup scripts.
        
        Args:
            installPath: Path to Blender version folder.
        
        Returns:
            True if installation succeeded, False otherwise.
        """
        try:
            if not os.path.exists(os.path.join(installPath, "scripts", "startup")):
                if os.path.exists(installPath):
                    for f in sorted(os.listdir(installPath), reverse=True):
                        try:
                            float(f)
                        except ValueError:
                            pass
                        else:
                            installPath = os.path.join(installPath, f)
                            break

            if not os.path.exists(os.path.join(installPath, "scripts", "startup")) and not os.path.exists(os.path.join(installPath, "config")):
                msgStr = (
                    "Invalid Blender path: %s.\n\nThe path has to be the Blender version folder in the user preferences folder, which usually looks like this: (with your Blender version):\n\n%s"
                    % (installPath, self.examplePath)
                )
                self.core.popup(msgStr, title="Prism Integration")
                return False

            integrationBase = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Integration"
            )
            integrationBase = os.path.realpath(integrationBase)

            # prismInit
            initpath = os.path.join(
                installPath, "scripts", "startup", "PrismInit.py"
            ).replace("\\", "/")
            saveRenderPath = os.path.join(
                installPath, "scripts", "startup", "PrismAutoSaveRender.py"
            ).replace("\\", "/")
            addedFiles = []

            cmds = []
            if os.path.exists(initpath):
                cmd = {"type": "removeFile", "args": [initpath], "validate": False}
                cmds.append(cmd)

            if os.path.exists(initpath + "c"):
                cmd = {"type": "removeFile", "args": [initpath + "c"]}
                cmds.append(cmd)

            if os.path.exists(saveRenderPath):
                cmd = {
                    "type": "removeFile",
                    "args": [saveRenderPath],
                    "validate": False,
                }
                cmds.append(cmd)

            if os.path.exists(saveRenderPath + "c"):
                cmd = {"type": "removeFile", "args": [saveRenderPath + "c"]}
                cmds.append(cmd)

            if not os.path.exists(os.path.dirname(initpath)):
                cmd = {"type": "createFolder", "args": [os.path.dirname(initpath)]}
                cmds.append(cmd)

            baseinitfile = os.path.join(integrationBase, "PrismInit.py")
            cmd = {"type": "copyFile", "args": [baseinitfile, initpath]}
            cmds.append(cmd)
            addedFiles.append(initpath)

            with open(baseinitfile, "r") as init:
                initStr = init.read()

            initStr = initStr.replace(
                "PLUGINROOT", '"%s"' % os.path.dirname(self.pluginPath).replace("\\", "/")
            )

            initStr = initStr.replace(
                "PRISMROOT", '"%s"' % self.core.prismRoot.replace("\\", "/")
            )
            cmd = {"type": "writeToFile", "args": [initpath, initStr]}
            cmds.append(cmd)

            topbarPath = os.path.join(
                installPath, "scripts", "startup", "bl_ui", "space_topbar.py"
            )
            hMenuStr = 'layout.menu("TOPBAR_MT_help")'
            fClassStr = "class TOPBAR_MT_file(Menu):"
            hClassName = "TOPBAR_MT_help,"
            baseTopbarFile1 = os.path.join(integrationBase, "space_topbar1.py")

            with open(baseTopbarFile1, "r") as init:
                bTbStr1 = init.read()

            baseTopbarFile2 = os.path.join(integrationBase, "space_topbar2.py")

            with open(baseTopbarFile2, "r") as init:
                bTbStr2 = init.read()

            if not os.path.exists(topbarPath):
                topbarPath = os.path.join(
                    installPath, "scripts", "startup", "bl_ui", "space_info.py"
                )
                hMenuStr = 'layout.menu("INFO_MT_help")'
                fClassStr = "class INFO_MT_file(Menu):"
                hClassName = "INFO_MT_help,"

            if os.path.exists(topbarPath):
                with open(topbarPath, "r") as init:
                    tbStr = init.read()

                tbStr = self.core.integration.removeIntegrationData(content=tbStr)

                tbStr = tbStr.replace("    TOPBAR_MT_prism,", "")

                tbStr = tbStr.replace(hMenuStr, hMenuStr + bTbStr1)
                tbStr = tbStr.replace(fClassStr, bTbStr2 + fClassStr)
                tbStr = tbStr.replace(hClassName, hClassName + "\n    TOPBAR_MT_prism,")

                bakPath = topbarPath + ".bak"
                if not os.path.exists(bakPath):
                    cmd = {"type": "copyFile", "args": [topbarPath, bakPath]}
                    cmds.append(cmd)

                cmd = {"type": "writeToFile", "args": [topbarPath, tbStr]}
                cmds.append(cmd)

            baseRenderfile = os.path.join(integrationBase, "PrismAutoSaveRender.py")
            cmd = {"type": "copyFile", "args": [baseRenderfile, saveRenderPath]}
            cmds.append(cmd)
            addedFiles.append(saveRenderPath)

            if platform.system() == "Windows":
                baseWinfile = os.path.join(integrationBase, "qminimal.dll")
                winPath = os.path.join(
                    os.path.dirname(installPath), "platforms", "qminimal.dll"
                )

                dirPath = os.path.dirname(winPath)
                if not os.path.exists(dirPath):
                    cmd = {"type": "createFolder", "args": [dirPath]}
                    cmds.append(cmd)

                if not os.path.exists(winPath):
                    cmd = {"type": "copyFile", "args": [baseWinfile, winPath]}
                    cmds.append(cmd)

                baseWinfile = os.path.join(integrationBase, "qoffscreen.dll")
                winPath = os.path.join(
                    os.path.dirname(installPath), "platforms", "qoffscreen.dll"
                )

                if not os.path.exists(winPath):
                    cmd = {"type": "copyFile", "args": [baseWinfile, winPath]}
                    cmds.append(cmd)

                baseWinfile = os.path.join(integrationBase, "qwindows.dll")
                winPath = os.path.join(
                    os.path.dirname(installPath), "platforms", "qwindows.dll"
                )

                if not os.path.exists(winPath):
                    cmd = {"type": "copyFile", "args": [baseWinfile, winPath]}
                    cmds.append(cmd)

                baseWinfile = os.path.join(integrationBase, "python3.dll")
                winPath = os.path.join(os.path.dirname(installPath), "python3.dll")

                if not os.path.exists(winPath):
                    cmd = {"type": "copyFile", "args": [baseWinfile, winPath]}
                    cmds.append(cmd)

            result = self.core.runFileCommands(cmds)

            if platform.system() in ["Linux", "Darwin"]:
                for i in addedFiles:
                    os.chmod(i, 0o777)

            if result is True:
                return True
            elif result is False:
                return False
            else:
                raise Exception(result)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msgStr = (
                "Errors occurred during the installation of the Blender integration.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
            return False

    def removeIntegration(self, installPath: str) -> bool:
        """Remove Prism integration from Blender.
        
        Removes integration files and restores modified scripts.
        
        Args:
            installPath: Path to Blender version folder.
        
        Returns:
            True if removal succeeded, False otherwise.
        """
        try:
            cmds = []
            if not os.path.exists(os.path.join(installPath, "scripts", "startup")):
                if os.path.exists(installPath):
                    for f in os.listdir(installPath):
                        try:
                            float(f)
                        except ValueError:
                            pass
                        else:
                            installPath = os.path.join(installPath, f)

            initpath = os.path.join(installPath, "scripts", "startup", "PrismInit.py")
            saveRenderPath = os.path.join(
                installPath, "scripts", "startup", "PrismAutoSaveRender.py"
            )

            if os.path.exists(initpath):
                cmd = {"type": "removeFile", "args": [initpath], "validate": False}
                cmds.append(cmd)

            if os.path.exists(initpath + "c"):
                cmd = {"type": "removeFile", "args": [initpath + "c"]}
                cmds.append(cmd)

            if os.path.exists(saveRenderPath):
                cmd = {
                    "type": "removeFile",
                    "args": [saveRenderPath],
                    "validate": False,
                }
                cmds.append(cmd)

            if os.path.exists(saveRenderPath + "c"):
                cmd = {"type": "removeFile", "args": [saveRenderPath + "c"]}
                cmds.append(cmd)

            topbarPath = os.path.join(
                installPath, "scripts", "startup", "bl_ui", "space_topbar.py"
            )

            if not os.path.exists(topbarPath):
                topbarPath = os.path.join(
                    installPath, "scripts", "startup", "bl_ui", "space_info.py"
                )

            if os.path.exists(topbarPath):
                with open(topbarPath, "r") as init:
                    tbStr = init.read()

                tbStr = self.core.integration.removeIntegrationData(content=tbStr)

                tbStr = tbStr.replace("\n    TOPBAR_MT_prism,", "")

                cmd = {"type": "writeToFile", "args": [topbarPath, tbStr]}
                cmds.append(cmd)

            result = self.core.runFileCommands(cmds)
            if result is True:
                return True
            elif result is False:
                return False
            else:
                raise Exception(result)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msgStr = (
                "Errors occurred during the removal of the Blender integration.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
            return False

    def updateInstallerUI(self, userFolders: Any, pItem: Any) -> Optional[bool]:
        """Update installer UI with Blender installation options.
        
        Adds Blender versions to installer tree widget.
        
        Args:
            userFolders: User folders object.
            pItem: Parent tree widget item.
            
        Returns:
            None on success, False on error.
        """
        try:
            bldItem = QTreeWidgetItem(["Blender"])
            bldItem.setCheckState(0, Qt.Checked)
            pItem.addChild(bldItem)

            bldPaths = self.getBlenderPaths() or []
            bldCustomItem = QTreeWidgetItem(["Custom"])
            bldCustomItem.setToolTip(0, 'e.g. "%s"' % self.examplePath)
            bldCustomItem.setToolTip(1, 'e.g. "%s"' % self.examplePath)
            bldCustomItem.setText(1, "< doubleclick to browse path >")
            bldCustomItem.setCheckState(0, Qt.Unchecked)
            bldCustomItem.setFlags(bldCustomItem.flags() & ~Qt.ItemIsAutoTristate)
            bldItem.addChild(bldCustomItem)
            bldItem.setExpanded(True)

            activeVersion = False
            for bldPath in bldPaths:
                bldVItem = QTreeWidgetItem([os.path.basename(bldPath).replace("Blender ", "")])
                bldItem.addChild(bldVItem)

                bldVItem.setCheckState(0, Qt.Checked)
                bldVItem.setFlags(bldVItem.flags() & ~Qt.ItemIsAutoTristate)
                bldVItem.setText(1, bldPath)
                bldVItem.setToolTip(0, bldPath)
                bldVItem.setText(1, bldPath)
                activeVersion = True

            if not activeVersion:
                bldItem.setCheckState(0, Qt.Unchecked)
                bldCustomItem.setFlags(~Qt.ItemIsEnabled)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = QMessageBox.warning(
                self.core.messageParent,
                "Prism Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s"
                % (__file__, str(e), exc_type, exc_tb.tb_lineno),
            )
            return False

    def installerExecute(self, bldItem: Any, result: dict) -> Union[List[str], bool]:
        """Execute Blender integration installation.
        
        Installs integration for all checked Blender versions.
        
        Args:
            bldItem: Blender tree widget item.
            result: Result dictionary to update.
        
        Returns:
            List of successfully installed paths, or False on error.
        """
        try:
            bldPaths = []
            installLocs = []

            if bldItem.checkState(0) != Qt.Checked:
                return installLocs

            for i in range(bldItem.childCount()):
                item = bldItem.child(i)
                if item.checkState(0) == Qt.Checked and os.path.exists(item.text(1)):
                    bldPaths.append(item.text(1))

            for i in bldPaths:
                result["Blender integration"] = self.core.integration.addIntegration(
                    self.plugin.pluginName, path=i, quiet=True
                )
                if result["Blender integration"]:
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
