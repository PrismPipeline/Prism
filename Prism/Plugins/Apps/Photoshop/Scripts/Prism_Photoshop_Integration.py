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


class Prism_Photoshop_Integration(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        self.examplePath = str(self.getPhotoshopPath())

    @err_catcher(name=__name__)
    def getPhotoshopPath(self):
        try:
            if platform.system() == "Windows":
                key = _winreg.OpenKey(
                    _winreg.HKEY_LOCAL_MACHINE,
                    "SOFTWARE\\Adobe\\Photoshop",
                    0,
                    _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
                )
                psVersion = _winreg.EnumKey(key, 0)
                psKey = _winreg.OpenKey(
                    _winreg.HKEY_LOCAL_MACHINE,
                    "SOFTWARE\\Adobe\\Photoshop\\" + psVersion,
                    0,
                    _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
                )
                psPath = (_winreg.QueryValueEx(psKey, "ApplicationPath"))[0]
            elif platform.system() == "Darwin":
                for foldercont in os.walk("/Applications"):
                    for folder in reversed(sorted(foldercont[1])):
                        if folder.startswith("Adobe Photoshop"):
                            psPath = os.path.join(foldercont[0], folder)
                            break
                    break

            return psPath
        except:
            return None

    def addIntegration(self, installPath):
        try:
            if not os.path.exists(installPath):
                QMessageBox.warning(
                    self.core.messageParent,
                    "Prism Integration",
                    "Invalid Photoshop path: %s.\nThe path doesn't exist."
                    % installPath,
                    QMessageBox.Ok,
                )
                return False

            integrationBase = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Integration"
            )

            if platform.system() == "Windows":
                osName = "Windows"
            elif platform.system() == "Darwin":
                osName = "Mac"

            for i in [
                "Prism - 1 Tools.jsx",
                "Prism - 2 Save Version.jsx",
                "Prism - 3 Save Extended.jsx",
                "Prism - 4 Export.jsx",
                "Prism - 5 Project Browser.jsx",
                "Prism - 6 Settings.jsx",
            ]:
                origFile = os.path.join(integrationBase, osName, i)
                targetFile = os.path.join(installPath, "Presets", "Scripts", i)

                if not os.path.exists(os.path.dirname(targetFile)):
                    os.makedirs(os.path.dirname(targetFile))

                if os.path.exists(targetFile):
                    os.remove(targetFile)

                shutil.copy2(origFile, targetFile)

                with open(targetFile, "r") as init:
                    initStr = init.read()

                initStr = initStr.replace("PRISMROOT", "%s" % self.core.prismRoot)
                initStr = initStr.replace("PRISMLIBS", "%s" % self.core.prismLibs)

                with open(targetFile, "w") as init:
                    init.write(initStr)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msgStr = (
                "Errors occurred during the installation of the Photoshop integration.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            self.core.popup(msgStr, title="Prism Integration")
            return False

    def removeIntegration(self, installPath):
        try:
            for i in [
                "Prism - 1 Tools.jsx",
                "Prism - 2 Save version.jsx",
                "Prism - 3 Save comment.jsx",
                "Prism - 4 Export",
                "Prism - 5 ProjectBrowser.jsx",
                "Prism - 6 Settings.jsx",
            ]:
                fPath = os.path.join(installPath, "Presets", "Scripts", i)
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

    def updateInstallerUI(self, userFolders, pItem):
        try:
            photoshopItem = QTreeWidgetItem(["Photoshop"])
            pItem.addChild(photoshopItem)

            photoshopPath = self.examplePath
            if photoshopPath is not None and os.path.exists(photoshopPath):
                photoshopItem.setCheckState(0, Qt.Checked)
                photoshopItem.setText(1, photoshopPath)
                photoshopItem.setToolTip(0, photoshopPath)
            else:
                photoshopItem.setCheckState(0, Qt.Unchecked)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = QMessageBox.warning(
                self.core.messageParent,
                "Prism Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s"
                % (__file__, str(e), exc_type, exc_tb.tb_lineno),
            )
            return False

    def installerExecute(self, photoshopItem, result):
        try:
            installLocs = []

            if photoshopItem.checkState(0) == Qt.Checked and os.path.exists(
                photoshopItem.text(1)
            ):
                result["Photoshop integration"] = self.core.integration.addIntegration(self.plugin.pluginName, path=photoshopItem.text(1), quiet=True)
                if result["Photoshop integration"]:
                    installLocs.append(photoshopItem.text(1))

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
