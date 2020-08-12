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

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_Maya_externalAccess_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

    @err_catcher(name=__name__)
    def prismSettings_loadUI(self, origin, tab):
        if self.core.appPlugin.pluginName == "Maya":
            origin.w_addModulePath = QWidget()
            origin.b_addModulePath = QPushButton(
                "Add current project to Maya module path"
            )
            lo_addModulePath = QHBoxLayout()
            origin.w_addModulePath.setLayout(lo_addModulePath)
            lo_addModulePath.setContentsMargins(0, 9, 0, 9)
            lo_addModulePath.addStretch()
            lo_addModulePath.addWidget(origin.b_addModulePath)
            tab.layout().addWidget(origin.w_addModulePath)

            origin.b_addModulePath.clicked.connect(self.appendEnvFile)

            if not os.path.exists(self.core.prismIni):
                origin.b_addModulePath.setEnabled(False)

        origin.w_sceneType = QWidget()
        origin.l_sceneType = QLabel("Save scene as:")
        origin.cb_sceneType = QComboBox()
        lo_sceneType = QHBoxLayout()
        origin.w_sceneType.setLayout(lo_sceneType)
        lo_sceneType.setContentsMargins(0, 9, 0, 9)
        lo_sceneType.addStretch()
        lo_sceneType.addWidget(origin.l_sceneType)
        lo_sceneType.addWidget(origin.cb_sceneType)
        tab.layout().addWidget(origin.w_sceneType)

        self.saveSceneTypes = [
            ".ma",
            ".mb",
            ".ma (prefer current scene type)",
            ".mb (prefer current scene type)",
        ]

        origin.cb_sceneType.addItems(self.saveSceneTypes)

    @err_catcher(name=__name__)
    def prismSettings_saveSettings(self, origin, settings):
        if "maya" not in settings:
            settings["maya"] = {}

        settings["maya"]["saveSceneType"] = origin.cb_sceneType.currentText()

    @err_catcher(name=__name__)
    def prismSettings_loadSettings(self, origin, settings):
        if "maya" in settings:
            if "saveSceneType" in settings["maya"]:
                origin.cb_sceneType.setCurrentText(settings["maya"]["saveSceneType"])

    @err_catcher(name=__name__)
    def getAutobackPath(self, origin, tab):
        autobackpath = ""
        if self.core.appPlugin.pluginName == "Maya":
            autobackpath = self.executeScript(
                origin, "cmds.autoSave( q=True, destinationFolder=True )"
            )
        else:
            if platform.system() == "Windows":
                autobackpath = os.path.join(
                    os.getenv("USERPROFILE"),
                    "Documents",
                    "maya",
                    "projects",
                    "default",
                    "autosave",
                )

        fileStr = "Maya Scene File ("
        for i in self.sceneFormats:
            fileStr += "*%s " % i

        fileStr += ")"

        return autobackpath, fileStr

    @err_catcher(name=__name__)
    def copySceneFile(self, origin, origFile, targetPath, mode="copy"):
        xgenfiles = [
            x
            for x in os.listdir(os.path.dirname(origFile))
            if x.startswith(os.path.splitext(os.path.basename(origFile))[0])
            and os.path.splitext(x)[1] in [".xgen", "abc"]
        ]
        for i in xgenfiles:
            curFilePath = os.path.join(os.path.dirname(origFile), i).replace("\\", "/")
            tFilePath = os.path.join(os.path.dirname(targetPath), i).replace("\\", "/")
            if curFilePath != tFilePath:
                if mode == "copy":
                    shutil.copy2(curFilePath, tFilePath)
                elif mode == "move":
                    shutil.move(curFilePath, tFilePath)
