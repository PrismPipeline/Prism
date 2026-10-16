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
import shutil
import glob
import json

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_ComfyUI_Integration(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        if platform.system() == "Windows":
            installs = self.getInstallPaths()
            if not installs:
                installs = [os.environ["USERPROFILE"] + "\\ComfyUI-Installs\\ComfyUI\\ComfyUI"]

            self.examplePath = (installs[0])
        elif platform.system() == "Linux":
            userName = (
                os.environ["SUDO_USER"]
                if "SUDO_USER" in os.environ
                else os.environ["USER"]
            )
            self.examplePath = os.path.join("/home", userName, "ComfyUI")
        elif platform.system() == "Darwin":
            userName = (
                os.environ["SUDO_USER"]
                if "SUDO_USER" in os.environ
                else os.environ["USER"]
            )
            self.examplePath = (
                "/Users/%s/Library/Preferences/ComfyUI" % userName
            )

    @err_catcher(name=__name__)
    def getInstallPaths(self):
        if platform.system() == "Windows":
            globPath = os.environ["USERPROFILE"] + "\\ComfyUI-Installs\\*\\ComfyUI"
            installs = glob.glob(globPath)
            return installs
        else:
            return []

    @err_catcher(name=__name__)
    def getExecutable(self):
        execPath = ""
        if platform.system() == "Windows":
            defaultpath = os.path.join(self.getComfyUIPath(), ".venv\\Scripts\\python.exe")
            if os.path.exists(defaultpath):
                execPath = defaultpath

        return execPath

    @err_catcher(name=__name__)
    def getComfyUIPath(self):
        return self.examplePath if os.path.exists(self.examplePath) else ""

    @err_catcher(name=__name__)
    def getComfyConfigPath(self):
        overridePath = os.getenv("PRISM_COMFYUI_CONFIG_PATH", "")
        if overridePath:
            return os.path.normpath(os.path.expandvars(os.path.expanduser(overridePath)))

        userProfile = os.getenv("USERPROFILE") or os.path.expanduser("~")
        return os.path.join(userProfile, "Documents", "Prism2", "comfy.json")

    @err_catcher(name=__name__)
    def writeComfyConfig(self):
        configPath = self.getComfyConfigPath()
        configDir = os.path.dirname(configPath)
        if configDir and not os.path.exists(configDir):
            os.makedirs(configDir)

        configData = {}
        if os.path.exists(configPath):
            try:
                with open(configPath, "r") as configFile:
                    existingData = json.load(configFile)
                    if isinstance(existingData, dict):
                        configData = existingData
            except Exception:
                configData = {}

        configData["prism_root"] = self.core.prismRoot.replace("\\", "/")
        configData["plugin_root"] = self.pluginDirectory.replace("\\", "/")

        with open(configPath, "w") as configFile:
            json.dump(configData, configFile, indent=4)

    def addIntegration(self, installPath):
        try:
            integrationBase = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Integration"
            )
            addedFiles = []

            initpath = os.path.join(installPath, "custom_nodes", "prism_pipeline")

            if os.path.exists(initpath):
                shutil.rmtree(initpath)

            origNodeDir = os.path.join(integrationBase, "custom_nodes", "prism_pipeline")
            shutil.copytree(origNodeDir, initpath)
            addedFiles.append(initpath)

            self.writeComfyConfig()

            if platform.system() in ["Linux", "Darwin"]:
                for i in addedFiles:
                    os.chmod(i, 0o777)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msgStr = (
                "Errors occurred during the installation of the ComfyUI integration.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."
            self.core.popup(msgStr, title="Prism Integration")
            return False

    @err_catcher(name=__name__)
    def getIntegrationStatus(self, path: str) -> str:
        """Check copied custom nodes and the shared Prism configuration."""
        package = os.path.join(path, "custom_nodes", "prism_pipeline")
        if not os.path.exists(package):
            return "not added"

        source = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Integration", "custom_nodes", "prism_pipeline")
        for folder, directories, filenames in os.walk(source):
            directories[:] = [name for name in directories if name != "__pycache__"]
            for filename in filenames:
                if filename.endswith(".pyc"):
                    continue
                template = os.path.join(folder, filename)
                target = os.path.join(package, os.path.relpath(template, source))
                if not os.path.isfile(target):
                    return "update needed"
                with open(template, "rb") as stream:
                    expected = stream.read()
                with open(target, "rb") as stream:
                    if stream.read() != expected:
                        return "update needed"

        configPath = self.getComfyConfigPath()
        if not os.path.isfile(configPath):
            return "update needed"
        try:
            with open(configPath, "r") as stream:
                config = json.load(stream)
        except ValueError:
            return "update needed"
        expectedConfig = {
            "prism_root": self.core.prismRoot.replace("\\", "/"),
            "plugin_root": self.pluginDirectory.replace("\\", "/"),
        }
        if not isinstance(config, dict) or any(config.get(key) != value for key, value in expectedConfig.items()):
            return "update needed"
        return "added"

    def removeIntegration(self, installPath):
        try:
            prismNodeDir = os.path.join(installPath, "custom_nodes", "prism_pipeline")
            if os.path.exists(prismNodeDir):
                shutil.rmtree(prismNodeDir)

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msgStr = (
                "Errors occurred during the removal of the ComfyUI integration.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno)
            )
            msgStr += "\n\nRunning this application as administrator could solve this problem eventually."
            self.core.popup(msgStr, title="Prism Integration")
            return False

    def updateInstallerUI(self, userFolders, pItem):
        try:
            pluginItem = QTreeWidgetItem([self.plugin.pluginName])
            pluginItem.setCheckState(0, Qt.Checked)
            pItem.addChild(pluginItem)

            comfyPaths = self.getInstallPaths() or []
            customItem = QTreeWidgetItem(["Custom"])
            customItem.setToolTip(0, 'e.g. "%s"' % self.examplePath)
            customItem.setToolTip(1, 'e.g. "%s"' % self.examplePath)
            customItem.setText(1, "< doubleclick to browse path >")
            customItem.setCheckState(0, Qt.Unchecked)
            pluginItem.addChild(customItem)
            pluginItem.setExpanded(True)

            activeVersion = False
            for comfyPath in comfyPaths:
                versionName = os.path.basename(os.path.dirname(comfyPath))
                vItem = QTreeWidgetItem([versionName])
                pluginItem.addChild(vItem)

                if os.path.exists(comfyPath):
                    vItem.setCheckState(0, Qt.Checked)
                    vItem.setText(1, comfyPath)
                    vItem.setToolTip(0, comfyPath)
                    vItem.setText(1, comfyPath)
                    activeVersion = True
                else:
                    vItem.setCheckState(0, Qt.Unchecked)
                    vItem.setFlags(~Qt.ItemIsEnabled)

            if not activeVersion:
                pluginItem.setCheckState(0, Qt.Unchecked)
                customItem.setFlags(~Qt.ItemIsEnabled)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msgStr = "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s" % (__file__, str(e), exc_type, exc_tb.tb_lineno)
            self.core.popup(msgStr, title="Prism ComfyUI Integration")
            return False

    def installerExecute(self, pluginItem, result):
        try:
            pluginPaths = []
            installLocs = []

            if pluginItem.checkState(0) != Qt.Checked:
                return installLocs

            for idx in range(pluginItem.childCount()):
                item = pluginItem.child(idx)
                if item.checkState(0) == Qt.Checked and os.path.exists(item.text(1)):
                    pluginPaths.append(item.text(1))

            for pluginPath in pluginPaths:
                result[
                    "ComfyUI integration"
                ] = self.core.integration.addIntegration(
                    self.plugin.pluginName, path=pluginPath, quiet=True
                )
                if result["ComfyUI integration"]:
                    installLocs.append(pluginPath)

            return installLocs
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msgStr = "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s" % (__file__, str(e), exc_type, exc_tb.tb_lineno)
            self.core.popup(msgStr, title="Prism ComfyUI Integration")
            return False
