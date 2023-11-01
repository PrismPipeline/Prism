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

import bpy

if "PRISM_ROOT" in os.environ:
    prismRoot = os.environ["PRISM_ROOT"]
    if not prismRoot:
        raise Exception("PRISM_ROOT is not set")
else:
    prismRoot = PRISMROOT

pluginRoot = os.getenv("PRISM_APP_PLUGIN_ROOT")
if not pluginRoot:
    pluginRoot = PLUGINROOT

if sys.version_info[0] != 3 or sys.version_info[1] < 7:
    raise RuntimeError("Prism supports only Blender versions, which are using at least Python 3.7")

sys.path.insert(0, os.path.join(prismRoot, "Scripts"))
import PrismCore

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


from bpy.app.handlers import persistent


def prismInit():
    pcore = PrismCore.PrismCore(app="Blender")
    return pcore


@persistent
def sceneUnload(dummy):
    pcore.sceneUnload()


@persistent
def sceneSave(dummy):
    pcore.scenefileSaved()


@persistent
def sceneOpen(dummy):
    pcore.sceneOpen()


class PrismSave(bpy.types.Operator):
    bl_idname = "object.prism_save"
    bl_label = "Save"

    def execute(self, context):
        if platform.system() == "Linux":
            pcore.saveScene()
            for i in QApplication.topLevelWidgets():
                if i.isVisible():
                    qApp.exec_()
                    break
        else:
            pcore.saveScene()

        return {"FINISHED"}


class PrismSaveComment(bpy.types.Operator):
    bl_idname = "object.prism_savecomment"
    bl_label = "Save Comment"

    def execute(self, context):
        if platform.system() == "Linux":
            pcore.saveWithComment()
            for i in QApplication.topLevelWidgets():
                if i.isVisible():
                    qApp.exec_()
                    break
        else:
            pcore.saveWithComment()

        return {"FINISHED"}


class PrismProjectBrowser(bpy.types.Operator):
    bl_idname = "object.prism_browser"
    bl_label = "Project Browser"

    def execute(self, context):
        if platform.system() == "Linux":
            pcore.projectBrowser()
            qApp.exec_()
        else:
            pcore.projectBrowser()

        return {"FINISHED"}


class PrismStateManager(bpy.types.Operator):
    bl_idname = "object.prism_manager"
    bl_label = "State Manager"

    def execute(self, context):
        if platform.system() == "Linux":
            pcore.stateManager()
            qApp.exec_()
        else:
            pcore.stateManager()

        return {"FINISHED"}


class PrismSettings(bpy.types.Operator):
    bl_idname = "object.prism_settings"
    bl_label = "Settings"

    def execute(self, context):
        if platform.system() == "Linux":
            pcore.prismSettings()
            qApp.exec_()
        else:
            pcore.prismSettings()

        return {"FINISHED"}


if bpy.app.version < (2, 80, 0):
    Region = "TOOLS"
else:
    Region = "UI"


class PrismPanel(bpy.types.Panel):
    bl_label = "Prism Tools"
    bl_idname = "prismToolsPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = Region
    bl_category = "Prism"

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.operator("object.prism_save")

        row = layout.row()
        row.operator("object.prism_savecomment")

        row = layout.row()
        row.operator("object.prism_browser")

        row = layout.row()
        row.operator("object.prism_manager")

        row = layout.row()
        row.operator("object.prism_settings")


def register():
    if bpy.app.background:
        return

    try:
        qapp = QApplication.instance()
        if qapp is None:
            qapp = QApplication(sys.argv)

        global pcore
        pcore = prismInit()
        bpy.utils.register_class(PrismSave)
        bpy.utils.register_class(PrismSaveComment)
        bpy.utils.register_class(PrismProjectBrowser)
        bpy.utils.register_class(PrismStateManager)
        bpy.utils.register_class(PrismSettings)
        # bpy.utils.register_class(PrismPanel)

        bpy.app.handlers.load_pre.append(sceneUnload)
        bpy.app.handlers.save_post.append(sceneSave)
        bpy.app.handlers.load_post.append(sceneOpen)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(
            "ERROR - PrismInit - %s - %s - %s\n\n"
            % (str(e), exc_type, exc_tb.tb_lineno)
        )


def unregister():
    if bpy.app.background:
        return

    bpy.utils.unregister_class(PrismSave)
    bpy.utils.unregister_class(PrismSaveComment)
    bpy.utils.unregister_class(PrismProjectBrowser)
    bpy.utils.unregister_class(PrismStateManager)
    bpy.utils.unregister_class(PrismSettings)
    # bpy.utils.unregister_class(PrismPanel)

    bpy.app.handlers.load_pre.remove(sceneUnload)
    bpy.app.handlers.save_post.remove(sceneSave)
    bpy.app.handlers.load_post.remove(sceneOpen)
