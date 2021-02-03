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


class Prism_Nuke_Integration(object):
    def __init__(self, core, plugin):
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
    def getExecutable(self):
        execPath = ""
        if platform.system() == "Windows":
            execPath = "C:\\Program Files\\Nuke11.2v2\\Nuke11.2.exe"

        return execPath

    def addIntegration(self, installPath):
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

    def removeIntegration(self, installPath):
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

    def updateInstallerUI(self, userFolders, pItem):
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

    def installerExecute(self, nukeItem, result):
        try:
            installLocs = []

            if nukeItem.checkState(0) == Qt.Checked and os.path.exists(
                nukeItem.text(1)
            ):
                result["Nuke integration"] = self.core.integration.addIntegration(self.plugin.pluginName, path=nukeItem.text(1), quiet=True)
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
