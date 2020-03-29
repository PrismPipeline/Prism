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
import platform
import shutil

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

if platform.system() == "Windows":
    if sys.version[0] == "3":
        import winreg as _winreg
    else:
        import _winreg

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_Houdini_Integration(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        if platform.system() == "Windows":
            self.examplePath = os.environ["userprofile"] + "\\Documents\\houdini18.0"
        elif platform.system() == "Linux":
            userName = (
                os.environ["SUDO_USER"]
                if "SUDO_USER" in os.environ
                else os.environ["USER"]
            )
            self.examplePath = os.path.join("/home", userName, "houdini18.0")
        elif platform.system() == "Darwin":
            userName = (
                os.environ["SUDO_USER"]
                if "SUDO_USER" in os.environ
                else os.environ["USER"]
            )
            self.examplePath = "/Users/%s/Library/Preferences/houdini/18.0" % userName

        if not os.path.exists(self.examplePath):
            for i in ["18.0", "17.5", "17.0", "16.5", "16.0"]:
                path = self.examplePath[:-4] + i
                if os.path.exists(path):
                    self.examplePath = path
                    break

    @err_catcher(name=__name__)
    def getExecutable(self):
        execPath = ""
        if platform.system() == "Windows":
            defaultpath = os.path.join(self.getHoudiniPath(), "bin", "houdini.exe")
            if os.path.exists(defaultpath):
                execPath = defaultpath

        return execPath

    @err_catcher(name=__name__)
    def getHoudiniPath(self):
        try:
            key = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Side Effects Software",
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )
            validVersion = (_winreg.QueryValueEx(key, "ActiveVersion"))[0]

            key = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Side Effects Software\\Houdini " + validVersion,
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )

            return (_winreg.QueryValueEx(key, "InstallPath"))[0]

        except:
            return ""

    def addIntegration(self, installPath):
        try:

            # python rc
            pyrc = os.path.join(installPath, "python2.7libs", "pythonrc.py")

            if not os.path.exists(installPath):
                msg = QMessageBox(
                    QMessageBox.Warning,
                    "Prism Installation",
                    "Invalid Houdini path: %s.\n\nThe path has to be the Houdini preferences folder, which usually looks like this: (with your Houdini version):\n\n%s"
                    % (installPath, self.examplePath),
                    QMessageBox.Ok,
                )
                msg.setFocus()
                msg.exec_()
                return False

            addedFiles = []

            integrationBase = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Integration"
            )

            packagePath = os.path.join(installPath, "packages", "Prism.json")

            if os.path.exists(packagePath):
                os.remove(packagePath)

            if not os.path.exists(os.path.dirname(packagePath)):
                os.makedirs(os.path.dirname(packagePath))

            origpackagePath = os.path.join(integrationBase, "Prism.json")
            shutil.copy2(origpackagePath, packagePath)
            addedFiles.append(packagePath)

            with open(packagePath, "r") as init:
                initStr = init.read()

            with open(packagePath, "w") as init:
                initStr = initStr.replace(
                    "PRISMROOT", "%s" % self.core.prismRoot.replace("\\", "/")
                )
                init.write(initStr)

            if platform.system() in ["Linux", "Darwin"]:
                for i in addedFiles:
                    os.chmod(i, 0o777)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msgStr = (
                "Errors occurred during the installation of the Houdini integration.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
            return False

    def removeIntegration(self, installPath):
        try:
            if os.path.exists(os.path.join(installPath, "houdini", "python2.7libs")):
                installBase = os.path.join(installPath, "houdini")
            else:
                installBase = installPath
            initPy = os.path.join(installBase, "python2.7libs", "PrismInit.py")
            initPyc = initPy + "c"

            packagePath = os.path.join(installBase, "packages", "Prism.json")
            shelfpath = os.path.join(installBase, "toolbar", "Prism.shelf")
            iconPathSave = os.path.join(installBase, "config", "Icons", "prismSave.png")
            iconPathSaveComment = os.path.join(
                installBase, "config", "Icons", "prismSaveComment.png"
            )
            iconPathBrowser = os.path.join(
                installBase, "config", "Icons", "prismBrowser.png"
            )
            iconPathStates = os.path.join(
                installBase, "config", "Icons", "prismStates.png"
            )
            iconPathSettings = os.path.join(
                installBase, "config", "Icons", "prismSettings.png"
            )

            for i in [
                initPy,
                initPyc,
                packagePath,
                shelfpath,
                iconPathSave,
                iconPathSaveComment,
                iconPathBrowser,
                iconPathStates,
                iconPathSettings,
            ]:
                if os.path.exists(i):
                    os.remove(i)

            prc = os.path.join(installBase, "python2.7libs", "pythonrc.py")
            sceneOpen = os.path.join(installBase, "scripts", "456.py")
            sceneSave = os.path.join(installBase, "scripts", "afterscenesave.py")

            result = self.core.integration.removeIntegrationData(filepath=[prc, sceneOpen, sceneSave])
            if result is not None:
                return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            msgStr = (
                "Errors occurred during the removal of the Houdini integration.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
            return False

    def updateInstallerUI(self, userFolders, pItem):
        try:
            houItem = QTreeWidgetItem(["Houdini"])
            pItem.addChild(houItem)

            houdiniPath = self.examplePath

            if houdiniPath != None and os.path.exists(houdiniPath):
                houItem.setCheckState(0, Qt.Checked)
                houItem.setText(1, houdiniPath)
                houItem.setToolTip(0, houdiniPath)
            else:
                houItem.setCheckState(0, Qt.Unchecked)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = QMessageBox.warning(
                self.core.messageParent,
                "Prism Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s"
                % (__file__, str(e), exc_type, exc_tb.tb_lineno),
            )
            return False

    def installerExecute(self, houItem, result):
        try:
            installLocs = []

            if houItem.checkState(0) == Qt.Checked and os.path.exists(houItem.text(1)):
                result["Houdini integration"] = self.core.integration.addIntegration(self.plugin.pluginName, path=houItem.text(1), quiet=True)
                if result["Houdini integration"]:
                    installLocs.append(houItem.text(1))

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
