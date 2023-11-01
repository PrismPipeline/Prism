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

import hou

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


label = "Renderman"
ropNames = ["ris", "ris::3.0"]


def isActive():
    return hou.nodeType(hou.ropNodeTypeCategory(), "ris")


def getCam(node):
    return hou.node(node.parm("camera").eval())


def getFormatFromNode(node):
    ext = os.path.splitext(node.parm("ri_display").eval())[1]
    return ext


def createROP(origin):
    origin.node = origin.core.appPlugin.createRop("ris")


def setAOVData(origin, node, aovNum, item):
    pass


def getDefaultPasses(origin):
    pass


def addAOV(origin, aovData):
    pass


def refreshAOVs(origin):
    origin.gb_passes.setVisible(False)
    return


def deleteAOV(origin, row):
    pass


def aovDbClick(origin, event):
    pass


def setCam(origin, node, val):
    return origin.core.appPlugin.setNodeParm(node, "camera", val=val)


def executeAOVs(origin, outputName):
    parmPath = origin.core.appPlugin.getPathRelativeToProject(outputName) if origin.core.appPlugin.getUseRelativePath() else outputName
    if not origin.core.appPlugin.setNodeParm(origin.node, "ri_display", val=parmPath):
        return [origin.state.text(0) + ": error - Publish canceled"]

    return True


def setResolution(origin):
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "override_camerares", val=True
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "res_fraction", val="specific"
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "res_overridex", val=origin.sp_resWidth.value()
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "res_overridey", val=origin.sp_resHeight.value()
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]

    return True


def executeRender(origin):
    bkrender = origin.stateManager.publishInfos["backgroundRender"]
    if bkrender is None:
        msg = "How do you want to render?"
        result = origin.core.popupQuestion(
            msg, buttons=["Render", "Render in background", "Cancel"], default="Render"
        )
        origin.stateManager.publishInfos["backgroundRender"] = result
    else:
        if bkrender:
            result = "Render in background"
        else:
            result = "Render"

    if result == "Render":
        origin.node.parm("execute").pressButton()
    elif result == "Remder in background":
        hou.hipFile.save()
        origin.node.parm("executebackground").pressButton()
    else:
        return "Rendering cancled."

    return True


def postExecute(origin):
    return True
