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

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_Natron_Integration(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        if platform.system() == "Windows":
            self.examplePath = os.path.join(os.environ["userprofile"], ".Natron")
        elif platform.system() == "Linux":
            userName = (
                os.environ["SUDO_USER"]
                if "SUDO_USER" in os.environ
                else os.environ["USER"]
            )
            self.examplePath = os.path.join("/home", userName, ".Natron")
        elif platform.system() == "Darwin":
            userName = (
                os.environ["SUDO_USER"]
                if "SUDO_USER" in os.environ
                else os.environ["USER"]
            )
            self.examplePath = "/Users/%s/.Natron" % userName

    @err_catcher(name=__name__)
    def getExecutable(self):
        execPath = ""
        if platform.system() == "Windows":
            execPath = "C:\\Program Files\\INRIA\\Natron-2.3.14\\bin\\Natron.exe"

        return execPath

    def addIntegration(self, installPath):
        try:
            if not os.path.exists(installPath):
                QMessageBox.warning(
                    self.core.messageParent,
                    "Prism Integration",
                    "Invalid Natron path: %s.\nThe path doesn't exist." % installPath,
                    QMessageBox.Ok,
                )
                return False

            integrationBase = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Integration"
            )
            addedFiles = []

            origMenuFile = os.path.join(integrationBase, "initGui.py")
            with open(origMenuFile, "r") as mFile:
                initStr = mFile.read()

            initFile = os.path.join(installPath, "initGui.py")
            self.core.integration.removeIntegrationData(filepath=initFile)

            with open(initFile, "a") as initfile:
                initStr = initStr.replace(
                    "PRISMROOT", '"%s"' % self.core.prismRoot.replace("\\", "/")
                )
                initfile.write(initStr)

            addedFiles.append(initFile)

            wPrismFile = os.path.join(integrationBase, "WritePrism.py")
            wPrismtFile = os.path.join(installPath, "WritePrism.py")

            if os.path.exists(wPrismtFile):
                os.remove(wPrismtFile)

            shutil.copy2(wPrismFile, wPrismtFile)
            addedFiles.append(wPrismtFile)

            wPrismIcon = os.path.join(integrationBase, "WritePrism.png")
            wPrismtIcon = os.path.join(installPath, "WritePrism.png")

            if os.path.exists(wPrismtIcon):
                os.remove(wPrismtIcon)

            shutil.copy2(wPrismIcon, wPrismtIcon)
            addedFiles.append(wPrismtIcon)

            if platform.system() in ["Linux", "Darwin"]:
                for i in addedFiles:
                    os.chmod(i, 0o777)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            msgStr = (
                "Errors occurred during the installation of the Natron integration.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
            return False

    def removeIntegration(self, installPath):
        try:
            gizmo = os.path.join(installPath, "WritePrism.py")
            gizmoc = os.path.join(installPath, "WritePrism.pyc")
            gizmoIcon = os.path.join(installPath, "WritePrism.png")

            for i in [gizmo, gizmoc, gizmoIcon]:
                if os.path.exists(i):
                    os.remove(i)

            initFile = os.path.join(installPath, "initGui.py")
            self.core.integration.removeIntegrationData(filepath=initFile)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            msgStr = (
                "Errors occurred during the removal of the Natron integration.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
            return False

    def updateInstallerUI(self, userFolders, pItem):
        try:
            natronItem = QTreeWidgetItem(["Natron"])
            pItem.addChild(natronItem)

            natronPath = self.examplePath
            if os.path.exists(natronPath):
                natronItem.setCheckState(0, Qt.Checked)
                natronItem.setText(1, natronPath)
                natronItem.setToolTip(0, natronPath)
            else:
                natronItem.setCheckState(0, Qt.Unchecked)
                natronItem.setText(1, "< doubleclick to browse path >")
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = QMessageBox.warning(
                self.core.messageParent,
                "Prism Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s"
                % (__file__, str(e), exc_type, exc_tb.tb_lineno),
            )
            return False

    def installerExecute(self, natronItem, result):
        try:
            installLocs = []

            if natronItem.checkState(0) == Qt.Checked and os.path.exists(
                natronItem.text(1)
            ):
                result["Natron integration"] = self.core.integration.addIntegration(self.plugin.pluginName, path=natronItem.text(1), quiet=True)
                if result["Natron integration"]:
                    installLocs.append(natronItem.text(1))

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
