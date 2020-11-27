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


import hou

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

label = "Octane"
ropNames = ["Octane_ROP"]


def isActive():
    return hou.nodeType(hou.ropNodeTypeCategory(), "Octane_ROP") is not None


def getCam(node):
    return hou.node(node.parm("HO_renderCamera").eval())


def createROP(origin):
    origin.node = origin.core.appPlugin.createRop("Octane_ROP")


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
    return origin.core.appPlugin.setNodeParm(node, "HO_renderCamera", val=val)


def executeAOVs(origin, outputName):
    if not origin.core.appPlugin.setNodeParm(origin.node, "HO_img_enable", val=True):
        return [origin.state.text(0) + ": error - Publish canceled"]

    if not origin.core.appPlugin.setNodeParm(origin.node, "HO_img_fileName", val=outputName):
        return [origin.state.text(0) + ": error - Publish canceled"]

    return True


def setResolution(origin):
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "HO_overrideCameraRes", val=True
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "HO_overrideResScale", val="user"
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "HO_overrideRes1", val=origin.sp_resWidth.value()
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "HO_overrideRes2", val=origin.sp_resHeight.value()
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]

    return True


def executeRender(origin):
    origin.node.parm("execute").pressButton()
    return True


def postExecute(origin):
    return True
