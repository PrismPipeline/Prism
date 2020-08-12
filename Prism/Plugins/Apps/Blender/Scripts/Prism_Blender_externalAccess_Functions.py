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


class Prism_Blender_externalAccess_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

    @err_catcher(name=__name__)
    def prismSettings_loadUI(self, origin, tab):
        origin.gb_bldAutoSave = QGroupBox("Auto save renderings")
        lo_bldAutoSave = QVBoxLayout()
        origin.gb_bldAutoSave.setLayout(lo_bldAutoSave)
        origin.gb_bldAutoSave.setCheckable(True)
        origin.gb_bldAutoSave.setChecked(False)

        origin.chb_bldRperProject = QCheckBox("use path only for current project")

        w_bldAutoSavePath = QWidget()
        lo_bldAutoSavePath = QHBoxLayout()
        origin.le_bldAutoSavePath = QLineEdit()
        b_bldAutoSavePath = QPushButton("...")

        lo_bldAutoSavePath.setContentsMargins(0, 0, 0, 0)
        b_bldAutoSavePath.setMinimumSize(40, 0)
        b_bldAutoSavePath.setMaximumSize(40, 1000)
        b_bldAutoSavePath.setFocusPolicy(Qt.NoFocus)
        b_bldAutoSavePath.setContextMenuPolicy(Qt.CustomContextMenu)
        w_bldAutoSavePath.setLayout(lo_bldAutoSavePath)
        lo_bldAutoSavePath.addWidget(origin.le_bldAutoSavePath)
        lo_bldAutoSavePath.addWidget(b_bldAutoSavePath)

        lo_bldAutoSave.addWidget(origin.chb_bldRperProject)
        lo_bldAutoSave.addWidget(w_bldAutoSavePath)
        tab.layout().addWidget(origin.gb_bldAutoSave)

        if hasattr(self.core, "projectPath") and self.core.projectPath is not None:
            origin.le_bldAutoSavePath.setText(self.core.projectPath)

        b_bldAutoSavePath.clicked.connect(
            lambda: origin.browse(
                windowTitle="Select render save path", uiEdit=origin.le_bldAutoSavePath
            )
        )
        b_bldAutoSavePath.customContextMenuRequested.connect(
            lambda: self.core.openFolder(origin.le_bldAutoSavePath.text())
        )

        origin.groupboxes.append(origin.gb_bldAutoSave)

    @err_catcher(name=__name__)
    def prismSettings_saveSettings(self, origin, settings):
        if "blender" not in settings:
            settings["blender"] = {}

        bsPath = self.core.fixPath(origin.le_bldAutoSavePath.text())
        if not bsPath.endswith(os.sep):
            bsPath += os.sep

        if origin.chb_bldRperProject.isChecked():
            if os.path.exists(self.core.prismIni):
                k = "autosavepath_%s" % self.core.projectName
                settings["blender"][k] = bsPath
        else:
            settings["blender"]["autosavepath"] = bsPath

        settings["blender"]["autosaverender"] = origin.gb_bldAutoSave.isChecked()
        settings["blender"]["autosaveperproject"] = origin.chb_bldRperProject.isChecked()

    @err_catcher(name=__name__)
    def prismSettings_loadSettings(self, origin, settings):
        if "blender" in settings:
            if "autosaverender" in settings["blender"]:
                origin.gb_bldAutoSave.setChecked(settings["blender"]["autosaverender"])

            if "autosaveperproject" in settings["blender"]:
                origin.chb_bldRperProject.setChecked(settings["blender"]["autosaveperproject"])

            pData = "autosavepath_%s" % getattr(self.core, "projectName", "")
            if pData in settings["blender"]:
                if origin.chb_bldRperProject.isChecked():
                    origin.le_bldAutoSavePath.setText(settings["blender"][pData])

            if "autosavepath" in settings["blender"]:
                if not origin.chb_bldRperProject.isChecked():
                    origin.le_bldAutoSavePath.setText(settings["blender"]["autosavepath"])

    @err_catcher(name=__name__)
    def createProject_startup(self, origin):
        if self.core.useOnTop:
            origin.setWindowFlags(origin.windowFlags() ^ Qt.WindowStaysOnTopHint)

    @err_catcher(name=__name__)
    def editShot_startup(self, origin):
        pass

    @err_catcher(name=__name__)
    def shotgunPublish_startup(self, origin):
        pass

    @err_catcher(name=__name__)
    def getAutobackPath(self, origin, tab):
        autobackpath = ""
        if platform.system() == "Windows":
            autobackpath = os.path.join(os.getenv("LocalAppdata"), "Temp")

        fileStr = "Blender Scene File ("
        for i in self.sceneFormats:
            fileStr += "*%s " % i

        fileStr += ")"

        return autobackpath, fileStr
