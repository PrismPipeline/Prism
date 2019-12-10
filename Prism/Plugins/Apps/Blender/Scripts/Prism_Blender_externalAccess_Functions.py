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
# Copyright (C) 2016-2019 Richard Frangenberg
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


import os, sys
import traceback, time, platform
from functools import wraps

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1


class Prism_Blender_externalAccess_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            exc_info = sys.exc_info()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = (
                    "%s ERROR - Prism_Plugin_Blender_ext - Core: %s - Plugin: %s:\n%s\n\n%s"
                    % (
                        time.strftime("%d/%m/%y %X"),
                        args[0].core.version,
                        args[0].plugin.version,
                        "".join(traceback.format_stack()),
                        traceback.format_exc(),
                    )
                )
                args[0].core.writeErrorLog(erStr)

        return func_wrapper

    @err_decorator
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

    @err_decorator
    def prismSettings_saveSettings(self, origin):
        saveData = []

        bsPath = self.core.fixPath(origin.le_bldAutoSavePath.text())
        if not bsPath.endswith(os.sep):
            bsPath += os.sep
        if origin.chb_bldRperProject.isChecked():
            if os.path.exists(self.core.prismIni):
                saveData.append(
                    ["blender", "autosavepath_%s" % origin.e_curPname.text(), bsPath]
                )
        else:
            saveData.append(["blender", "autosavepath", bsPath])

        saveData.append(
            ["blender", "autosaverender", str(origin.gb_bldAutoSave.isChecked())]
        )
        saveData.append(
            [
                "blender",
                "autosaveperproject",
                str(origin.chb_bldRperProject.isChecked()),
            ]
        )

        return saveData

    @err_decorator
    def prismSettings_loadSettings(self, origin):
        loadData = {}
        loadFunctions = {}

        loadData["bld_autosaverender"] = ["blender", "autosaverender", "bool"]
        loadFunctions[
            "bld_autosaverender"
        ] = lambda x: origin.gb_bldAutoSave.setChecked(x)

        loadData["bld_asPerproject"] = ["blender", "autosaveperproject", "bool"]
        loadFunctions[
            "bld_asPerproject"
        ] = lambda x: origin.chb_bldRperProject.setChecked(x)

        if hasattr(self.core, "projectName"):
            loadData["bld_autosavepathprj"] = [
                "blender",
                "autosavepath_%s" % self.core.projectName,
            ]
        else:
            loadData["bld_autosavepathprj"] = ["blender", "autosavepath_"]

        loadFunctions[
            "bld_autosavepathprj"
        ] = lambda x, y=origin: self.prismSettings_loadAutoSavePathPrj(y, x)

        loadData["bld_autosavepath"] = ["blender", "autosavepath"]
        loadFunctions[
            "bld_autosavepath"
        ] = lambda x, y=origin: self.prismSettings_loadAutoSavePath(y, x)

        return loadData, loadFunctions

    @err_decorator
    def prismSettings_loadAutoSavePathPrj(self, origin, loadData):
        if origin.chb_bldRperProject.isChecked():
            origin.le_bldAutoSavePath.setText(loadData)

    @err_decorator
    def prismSettings_loadAutoSavePath(self, origin, loadData):
        if not origin.chb_bldRperProject.isChecked():
            origin.le_bldAutoSavePath.setText(loadData)

    @err_decorator
    def createProject_startup(self, origin):
        if self.core.useOnTop:
            origin.setWindowFlags(origin.windowFlags() ^ Qt.WindowStaysOnTopHint)

    @err_decorator
    def editShot_startup(self, origin):
        pass

    @err_decorator
    def shotgunPublish_startup(self, origin):
        pass

    @err_decorator
    def getAutobackPath(self, origin, tab):
        if platform.system() == "Windows":
            autobackpath = os.path.join(os.getenv("LocalAppdata"), "Temp")
        else:
            if tab == "a":
                autobackpath = os.path.join(
                    origin.tw_aHierarchy.currentItem().text(1),
                    "Scenefiles",
                    origin.lw_aPipeline.currentItem().text(),
                )
            elif tab == "sf":
                autobackpath = os.path.join(
                    origin.sBasePath,
                    origin.cursShots,
                    "Scenefiles",
                    origin.cursStep,
                    origin.cursCat,
                )

        fileStr = "Blender Scene File ("
        for i in self.sceneFormats:
            fileStr += "*%s " % i

        fileStr += ")"

        return autobackpath, fileStr
