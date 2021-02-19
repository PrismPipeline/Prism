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


class Prism_Blender_Integration(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        if platform.system() == "Windows":
            self.examplePath = self.getBlenderPath() or "C:/Program Files/Blender Foundation/Blender 2.82/"
        elif platform.system() == "Linux":
            self.examplePath = "/usr/local/blender-2.79b-linux-glibc219-x86_64/2.79"
        elif platform.system() == "Darwin":
            self.examplePath = "/Applications/blender/blender.app/Resources/2.79"

    @err_catcher(name=__name__)
    def getExecutable(self):
        execPath = ""
        if platform.system() == "Windows":
            execPath = os.path.join(os.path.dirname(self.examplePath), "blender.exe")

        return execPath

    @err_catcher(name=__name__)
    def getBlenderPath(self):
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

            vpath = os.path.join(os.path.dirname(blenderPath), "2.81")

            if os.path.exists(vpath):
                return vpath
            else:
                return ""

        except:
            return ""

    def addIntegration(self, installPath):
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

            if not os.path.exists(os.path.join(installPath, "scripts", "startup")):
                msgStr = "Invalid Blender path: %s.\n\nThe path has to be the Blender version folder in the installation folder, which usually looks like this: (with your Blender version):\n\n%s" % (installPath, self.examplePath)
                self.core.popup(msgStr, title="Prism Integration")
                return False

            integrationBase = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Integration"
            )

            # prismInit
            initpath = os.path.join(installPath, "scripts", "startup", "PrismInit.py").replace("\\", "/")
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
                cmd = {"type": "removeFile", "args": [saveRenderPath], "validate": False}
                cmds.append(cmd)

            if os.path.exists(saveRenderPath + "c"):
                cmd = {"type": "removeFile", "args": [saveRenderPath + "c"]}
                cmds.append(cmd)

            baseinitfile = os.path.join(integrationBase, "PrismInit.py")
            cmd = {"type": "copyFile", "args": [baseinitfile, initpath]}
            cmds.append(cmd)
            addedFiles.append(initpath)

            with open(baseinitfile, "r") as init:
                initStr = init.read()

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

    def removeIntegration(self, installPath):
        try:
            if not os.path.exists(os.path.join(installPath, "scripts", "startup")):
                if os.path.exists(installPath):
                    for f in os.listdir(installPath):
                        try:
                            float(f)
                        except ValueError:
                            pass
                        else:
                            installPath = os.path.join(installPath, f)

            initPy = os.path.join(installPath, "scripts", "startup", "PrismInit.py")
            saveRenderPy = os.path.join(
                installPath, "scripts", "startup", "PrismAutoSaveRender.py"
            )

            for i in [initPy, saveRenderPy]:
                if os.path.exists(i):
                    os.remove(i)

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

                with open(topbarPath, "w") as init:
                    init.write(tbStr)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msgStr = (
                "Errors occurred during the removal of the Blender integration.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

            QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
            return False

    def updateInstallerUI(self, userFolders, pItem):
        try:
            bldItem = QTreeWidgetItem(["Blender"])
            pItem.addChild(bldItem)

            if platform.system() == "Windows":
                blenderPath = self.getBlenderPath()
            elif platform.system() == "Linux":
                blenderPath = "/usr/local/blender-2.79b-linux-glibc219-x86_64/2.79"
            elif platform.system() == "Darwin":
                blenderPath = "/Applications/blender/blender.app/Resources/2.79"

            if blenderPath != "":
                bldItem.setCheckState(0, Qt.Checked)
                bldItem.setText(1, blenderPath)
                bldItem.setToolTip(0, blenderPath)
            else:
                bldItem.setCheckState(0, Qt.Unchecked)
                bldItem.setText(1, "< doubleclick to browse path >")

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = QMessageBox.warning(
                self.core.messageParent,
                "Prism Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s"
                % (__file__, str(e), exc_type, exc_tb.tb_lineno),
            )
            return False

    def installerExecute(self, bldItem, result):
        try:
            installLocs = []

            if bldItem.checkState(0) == Qt.Checked and os.path.exists(bldItem.text(1)):
                result["Blender integration"] = self.core.integration.addIntegration(self.plugin.pluginName, path=bldItem.text(1), quiet=True)
                if result["Blender integration"]:
                    installLocs.append(bldItem.text(1))

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
