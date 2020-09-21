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

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1

if platform.system() == "Windows":
    if sys.version[0] == "3":
        import winreg as _winreg
    else:
        import _winreg

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_3dsMax_Integration(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        if platform.system() == "Windows":
            self.examplePath = (
                os.environ["localappdata"] + "\\Autodesk\\3dsMax\\2020 - 64bit"
            )

    @err_catcher(name=__name__)
    def getExecutable(self):
        execPath = ""
        if platform.system() == "Windows":
            try:
                for i in ["23.0", "22.0", "21.0", "20.0", "19.0"]:
                    try:
                        key = _winreg.OpenKey(
                            _winreg.HKEY_LOCAL_MACHINE,
                            "SOFTWARE\\Autodesk\\3dsMax\\%s" % i,
                            0,
                            _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
                        )

                        installDir = (_winreg.QueryValueEx(key, "Installdir"))[0]
                    except:
                        pass

                execPath = os.path.join(installDir, "3dsmax.exe")
            except:
                pass

        return execPath

    def addIntegration(self, installPath):
        try:
            maxpath = os.path.join(installPath, "ENU", "scripts", "startup")

            if not os.path.exists(maxpath) or not os.path.exists(
                os.path.join(os.path.dirname(os.path.dirname(maxpath)), "usermacros")
            ):
                msgStr = "Invalid 3dsMax path:\n%s.\n\nThe path has to be the 3dsMax preferences folder, which usually looks like this: (with your username and 3dsMax version):\n\n%s" % (installPath, self.examplePath)
                self.core.popup(msgStr, title="Prism Integration")
                return False

            integrationBase = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Integration"
            )

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

    def removeIntegration(self, installPath):
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

    def updateInstallerUI(self, userFolders, pItem):
        try:
            if platform.system() == "Windows":
                maxPath = [
                    [
                        userFolders["LocalAppdata"]
                        + "\\Autodesk\\3dsMax\\2017 - 64bit",
                        "2017",
                    ],
                    [
                        userFolders["LocalAppdata"]
                        + "\\Autodesk\\3dsMax\\2018 - 64bit",
                        "2018",
                    ],
                    [
                        userFolders["LocalAppdata"]
                        + "\\Autodesk\\3dsMax\\2019 - 64bit",
                        "2019",
                    ],
                    [
                        userFolders["LocalAppdata"]
                        + "\\Autodesk\\3dsMax\\2020 - 64bit",
                        "2020",
                    ],
                    [
                        userFolders["LocalAppdata"]
                        + "\\Autodesk\\3dsMax\\2021 - 64bit",
                        "2021",
                    ],
                ]

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
            for i in maxPath:
                if not os.path.exists(i[0]):
                    continue

                maxvItem = QTreeWidgetItem([i[1]])
                maxItem.addChild(maxvItem)
                maxvItem.setCheckState(0, Qt.Checked)
                maxvItem.setText(1, i[0])
                maxvItem.setToolTip(0, i[0])
                activeVersion = True

            if not activeVersion:
                maxItem.setCheckState(0, Qt.Unchecked)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = QMessageBox.warning(
                self.core.messageParent,
                "Prism Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s"
                % (__file__, str(e), exc_type, exc_tb.tb_lineno),
            )
            return False

    def installerExecute(self, maxItem, result):
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
                result["3dsMax integration"] = self.core.integration.addIntegration(self.plugin.pluginName, path=i, quiet=True)
                if result["3dsMax integration"]:
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
