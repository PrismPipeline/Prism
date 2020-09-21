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


class Prism_Maya_Integration(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        if platform.system() == "Windows":
            self.examplePath = os.environ["userprofile"] + "\\Documents\\maya\\2020"
        elif platform.system() == "Linux":
            userName = (
                os.environ["SUDO_USER"]
                if "SUDO_USER" in os.environ
                else os.environ["USER"]
            )
            self.examplePath = os.path.join("/home", userName, "maya", "2020")
        elif platform.system() == "Darwin":
            userName = (
                os.environ["SUDO_USER"]
                if "SUDO_USER" in os.environ
                else os.environ["USER"]
            )
            self.examplePath = (
                "/Users/%s/Library/Preferences/Autodesk/maya/2020" % userName
            )

    @err_catcher(name=__name__)
    def getExecutable(self):
        execPath = ""
        if platform.system() == "Windows":
            defaultpath = os.path.join(self.getMayaPath(), "bin", "maya.exe")
            if os.path.exists(defaultpath):
                execPath = defaultpath

        return execPath

    @err_catcher(name=__name__)
    def getMayaPath(self):
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

    def addIntegration(self, installPath):
        try:
            if not os.path.exists(
                os.path.join(installPath, "scripts")
            ) or not os.path.exists(os.path.join(installPath, "prefs", "shelves")):
                QMessageBox.warning(
                    self.core.messageParent,
                    "Prism Installation",
                    "Invalid Maya path: %s.\n\nThe path has to be the Maya preferences folder, which usually looks like this: (with your username and Maya version):\n\nC:\\Users\\Richard\\Documents\\maya\\2018"
                    % installPath,
                    QMessageBox.Ok,
                )
                return False

            integrationBase = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Integration"
            )
            addedFiles = []

            integrationFiles = {}
            integrationFiles["userSetup.py"] = os.path.join(integrationBase, "userSetup.py")
            integrationFiles["PrismInit.py"] = os.path.join(integrationBase, "PrismInit.py")
            integrationFiles["shelf_Prism.mel"] = os.path.join(integrationBase, "shelf_Prism.mel")

            self.core.callback(name="preIntegrationAdded", types=["custom"], args=[self, integrationFiles])

            origSetupFile = integrationFiles["userSetup.py"]
            with open(origSetupFile, "r") as mFile:
                setupString = mFile.read()

            prismSetup = os.path.join(installPath, "scripts", "userSetup.py")
            self.core.integration.removeIntegrationData(filepath=prismSetup)

            with open(prismSetup, "a") as setupfile:
                setupfile.write(setupString)

            addedFiles.append(prismSetup)

            initpath = os.path.join(installPath, "scripts", "PrismInit.py")

            if os.path.exists(initpath):
                os.remove(initpath)

            if os.path.exists(initpath + "c"):
                os.remove(initpath + "c")

            origInitFile = integrationFiles["PrismInit.py"]
            shutil.copy2(origInitFile, initpath)
            addedFiles.append(initpath)

            with open(initpath, "r") as init:
                initStr = init.read()

            with open(initpath, "w") as init:
                initStr = initStr.replace(
                    "PRISMROOT", '"%s"' % self.core.prismRoot.replace("\\", "/")
                )
                init.write(initStr)

            shelfpath = os.path.join(installPath, "prefs", "shelves", "shelf_Prism.mel")

            if os.path.exists(shelfpath):
                os.remove(shelfpath)

            origShelfFile = integrationFiles["shelf_Prism.mel"]
            shutil.copy2(origShelfFile, shelfpath)
            addedFiles.append(shelfpath)

            icons = [
                "prismSave.png",
                "prismSaveComment.png",
                "prismBrowser.png",
                "prismStates.png",
                "prismSettings.png",
            ]

            for i in icons:
                iconPath = os.path.join(
                    self.core.prismRoot, "Scripts", "UserInterfacesPrism", i
                )
                tPath = os.path.join(installPath, "prefs", "icons", i)

                if os.path.exists(tPath):
                    os.remove(tPath)

                shutil.copy2(iconPath, tPath)
                addedFiles.append(tPath)

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

    def removeIntegration(self, installPath):
        try:
            initPy = os.path.join(installPath, "scripts", "PrismInit.py")
            initPyc = os.path.join(installPath, "scripts", "PrismInit.pyc")
            shelfpath = os.path.join(installPath, "prefs", "shelves", "shelf_Prism.mel")

            for i in [initPy, initPyc, shelfpath]:
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

    def updateInstallerUI(self, userFolders, pItem):
        try:
            if platform.system() == "Windows":
                mayaPath = [
                    os.path.join(userFolders["Documents"], "maya", "2016"),
                    os.path.join(userFolders["Documents"], "maya", "2017"),
                    os.path.join(userFolders["Documents"], "maya", "2018"),
                    os.path.join(userFolders["Documents"], "maya", "2019"),
                    os.path.join(userFolders["Documents"], "maya", "2020"),
                ]
            elif platform.system() == "Linux":
                userName = (
                    os.environ["SUDO_USER"]
                    if "SUDO_USER" in os.environ
                    else os.environ["USER"]
                )
                mayaPath = [
                    os.path.join("/home", userName, "maya", "2016"),
                    os.path.join("/home", userName, "maya", "2017"),
                    os.path.join("/home", userName, "maya", "2018"),
                    os.path.join("/home", userName, "maya", "2019"),
                    os.path.join("/home", userName, "maya", "2020"),
                ]
            elif platform.system() == "Darwin":
                userName = (
                    os.environ["SUDO_USER"]
                    if "SUDO_USER" in os.environ
                    else os.environ["USER"]
                )
                mayaPath = [
                    "/Users/%s/Library/Preferences/Autodesk/maya/2016" % userName,
                    "/Users/%s/Library/Preferences/Autodesk/maya/2017" % userName,
                    "/Users/%s/Library/Preferences/Autodesk/maya/2018" % userName,
                    "/Users/%s/Library/Preferences/Autodesk/maya/2019" % userName,
                    "/Users/%s/Library/Preferences/Autodesk/maya/2020" % userName,
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
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = QMessageBox.warning(
                self.core.messageParent,
                "Prism Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s"
                % (__file__, str(e), exc_type, exc_tb.tb_lineno),
            )
            return False

    def installerExecute(self, mayaItem, result):
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
                result["Maya integration"] = self.core.integration.addIntegration(self.plugin.pluginName, path=i, quiet=True)
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
