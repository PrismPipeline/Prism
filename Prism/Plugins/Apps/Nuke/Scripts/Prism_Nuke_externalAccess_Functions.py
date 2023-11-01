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
import subprocess

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

if platform.system() == "Windows":
    if sys.version[0] == "3":
        import winreg as _winreg
    else:
        import _winreg

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_Nuke_externalAccess_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        self.core.registerCallback(
            "userSettings_saveSettings",
            self.userSettings_saveSettings,
            plugin=self.plugin,
        )
        self.core.registerCallback(
            "userSettings_loadSettings",
            self.userSettings_loadSettings,
            plugin=self.plugin,
        )
        self.core.registerCallback("getPresetScenes", self.getPresetScenes, plugin=self.plugin)

    @err_catcher(name=__name__)
    def userSettings_loadUI(self, origin, tab):
        origin.w_nukeVersion = QWidget()
        origin.lo_nukeVersion = QHBoxLayout(origin.w_nukeVersion)
        origin.lo_nukeVersion.setContentsMargins(0, 0, 0, 0)
        origin.l_nukeVersion = QLabel("Nuke Version:")
        origin.cb_nukeVersion = QComboBox()
        origin.cb_nukeVersion.addItems(["Default", "NukeX", "NukeX (Non-Commercial)", "Indie", "Assist", "Studio", "Studio (Non-Commercial)", "Non-Commercial"])
        origin.lo_nukeVersion.addWidget(origin.l_nukeVersion)
        origin.lo_nukeVersion.addWidget(origin.cb_nukeVersion)
        origin.lo_nukeVersion.addStretch()
        tab.layout().addWidget(origin.w_nukeVersion)

        origin.chb_nukeRelativePaths = QCheckBox("Use relative paths")
        tab.layout().addWidget(origin.chb_nukeRelativePaths)

    @err_catcher(name=__name__)
    def userSettings_saveSettings(self, origin, settings):
        if "nuke" not in settings:
            settings["nuke"] = {}

        settings["nuke"]["nukeVersion"] = origin.cb_nukeVersion.currentText()
        settings["nuke"]["useRelativePaths"] = origin.chb_nukeRelativePaths.isChecked()

    @err_catcher(name=__name__)
    def userSettings_loadSettings(self, origin, settings):
        if "nuke" in settings:
            if "nukeVersion" in settings["nuke"]:
                origin.cb_nukeVersion.setCurrentText(settings["nuke"]["nukeVersion"])
            if "useRelativePaths" in settings["nuke"]:
                origin.chb_nukeRelativePaths.setChecked(settings["nuke"]["useRelativePaths"])

    @err_catcher(name=__name__)
    def getAutobackPath(self, origin):
        autobackpath = ""

        fileStr = "Nuke Script ("
        for i in self.sceneFormats:
            fileStr += "*%s " % i

        fileStr += ")"

        return autobackpath, fileStr

    @err_catcher(name=__name__)
    def customizeExecutable(self, origin, appPath, filepath):
        fileStarted = False
        nukeVersion = self.core.getConfig("nuke", "nukeVersion")
        if nukeVersion and nukeVersion != "Default":
            if appPath == "":
                if not hasattr(self, "nukePath"):
                    self.nukePath = self.core.getDefaultWindowsAppByExtension(".nk")

                if self.nukePath is not None and os.path.exists(self.nukePath):
                    appPath = self.nukePath
                else:
                    QMessageBox.warning(
                        self.core.messageParent,
                        "Warning",
                        "Nuke executable doesn't exist:\n\n%s" % self.nukePath,
                    )

            if appPath is not None and appPath != "":
                args = [appPath, self.core.fixPath(filepath)]
                if nukeVersion == "NukeX":
                    args.insert(-1, "--nukex")
                elif nukeVersion == "NukeX (Non-Commercial)":
                    args.insert(-1, "--nukex")
                    args.insert(-1, "--nc")
                elif nukeVersion == "Indie":
                    args.insert(-1, "--indie")
                elif nukeVersion == "Assist":
                    args.insert(-1, "--nukeassist")
                elif nukeVersion == "Studio":
                    args.insert(-1, "--studio")
                elif nukeVersion == "Studio (Non-Commercial)":
                    args.insert(-1, "--studio")
                    args.insert(-1, "--nc")
                elif nukeVersion == "Non-Commercial":
                    args.insert(-1, "--nc")

                subprocess.Popen(args, env=self.core.startEnv)
                fileStarted = True

        return fileStarted

    @err_catcher(name=__name__)
    def getPresetScenes(self, presetScenes):
        presetDir = os.path.join(self.pluginDirectory, "Presets")
        scenes = self.core.entities.getPresetScenesFromFolder(presetDir)
        presetScenes += scenes
