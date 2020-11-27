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


import re

import hou

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *


label = "V-Ray"
ropNames = ["vray_renderer"]


def isActive():
    return "Unknown command" not in hou.hscript("vrayproxy")[1]


def getCam(node):
    return hou.node(node.parm("render_camera").eval())


def createROP(origin):
    origin.node = origin.core.appPlugin.createRop("vray_renderer")


def setAOVData(origin, node, aovNum, item):
    aovNode = node.node(node.parm("render_network_render_channels").eval())
    if aovNode is None:
        refreshAOVs(origin)
        return

    for i in aovNode.children():
        if i.type().name() == "VRayNodeRenderChannelsContainer":
            channelNode = i
            break
    else:
        refreshAOVs(origin)
        return

    ccNode = channelNode.inputs()[int(aovNum) - 1]

    if ccNode.type().name() != "VRayNodeRenderChannelColor":
        refreshAOVs(origin)
        return

    if item.column() == 0:
        typeItems = ccNode.parm("alias").menuLabels()
        for idx, k in enumerate(typeItems):
            if k == item.text():
                typeToken = ccNode.parm("alias").menuItems()[idx]
                break
        else:
            refreshAOVs(origin)
            return

        origin.core.appPlugin.setNodeParm(ccNode, "alias", val=typeToken)
    elif item.column() == 1:
        origin.core.appPlugin.setNodeParm(ccNode, "name", val=item.text())
        ccNode.setName(re.sub("[^0-9a-zA-Z\\.]+", "_", item.text()))


def getDefaultPasses(origin):
    aovs = origin.core.getConfig(
        "defaultpasses", "houdini_vray", configPath=origin.core.prismIni
    )
    if aovs is None:
        aovs = origin.core.appPlugin.renderPasses["houdini_vray"]

    return aovs


def addAOV(origin, aovData):
    aovNode = origin.node.node(
        origin.node.parm("render_network_render_channels").eval()
    )
    if aovNode is None:
        aovNode = origin.core.appPlugin.createRop("vray_render_channels")
        aovNode.moveToGoodPosition()
        origin.node.parm("render_network_render_channels").set(aovNode.path())

    for i in aovNode.children():
        if i.type().name() == "VRayNodeRenderChannelsContainer":
            channelNode = i
            break
    else:
        channelNode = aovNode.createNode("VRayNodeRenderChannelsContainer")
        channelNode.moveToGoodPosition()

    ccNode = aovNode.createNode(
        "VRayNodeRenderChannelColor", re.sub("[^0-9a-zA-Z\\.]+", "_", aovData[1])
    )
    ccNode.moveToGoodPosition()
    channelNode.setNextInput(ccNode)
    typeItems = ccNode.parm("alias").menuLabels()
    for idx, k in enumerate(typeItems):
        if k == aovData[0]:
            typeToken = ccNode.parm("alias").menuItems()[idx]
            break
    else:
        refreshAOVs(origin)
        return

    origin.core.appPlugin.setNodeParm(ccNode, "alias", val=typeToken)
    origin.core.appPlugin.setNodeParm(ccNode, "name", val=aovData[1])


def refreshAOVs(origin):
    origin.tw_passes.horizontalHeaderItem(0).setText("Type")
    origin.tw_passes.horizontalHeaderItem(1).setText("Name")
    passNum = 0

    if origin.node is None:
        return

    aovNode = origin.node.node(
        origin.node.parm("render_network_render_channels").eval()
    )
    if aovNode is None:
        return

    for i in aovNode.children():
        if i.type().name() == "VRayNodeRenderChannelsContainer":
            channelNode = i
            break
    else:
        return

    origin.setPassDataEnabled = False
    for idx, i in enumerate(channelNode.inputs()):
        if i is None or i.type().name() != "VRayNodeRenderChannelColor":
            continue

        passTypeID = i.parm("alias").eval()
        typeItems = i.parm("alias").menuItems()
        for idxt, k in enumerate(typeItems):
            if k == passTypeID:
                typeName = i.parm("alias").menuLabels()[idxt]
                break
        else:
            continue

        passTypeName = QTableWidgetItem(typeName)
        passName = QTableWidgetItem(i.parm("name").eval())
        passNItem = QTableWidgetItem(str(idx))
        origin.tw_passes.insertRow(passNum)
        origin.tw_passes.setItem(passNum, 0, passTypeName)
        origin.tw_passes.setItem(passNum, 1, passName)
        origin.tw_passes.setItem(passNum, 2, passNItem)
        passNum += 1

    origin.setPassDataEnabled = True


def deleteAOV(origin, row):
    pid = int(origin.tw_passes.item(row, 2).text())

    aovNode = origin.node.node(
        origin.node.parm("render_network_render_channels").eval()
    )
    if aovNode is None:
        return

    for i in aovNode.children():
        if i.type().name() == "VRayNodeRenderChannelsContainer":
            channelNode = i
            break
    else:
        return

    ccNode = channelNode.inputs()[pid]
    ccNode.destroy()


def aovDbClick(origin, event):
    if origin.node is None or event.button() != Qt.LeftButton:
        origin.tw_passes.mouseDbcEvent(event)
        return

    curItem = origin.tw_passes.itemFromIndex(origin.tw_passes.indexAt(event.pos()))
    if curItem is not None and curItem.column() == 0:
        aovNode = origin.node.node(
            origin.node.parm("render_network_render_channels").eval()
        )
        if aovNode is None:
            refreshAOVs(origin)
            return

        for i in aovNode.children():
            if i.type().name() == "VRayNodeRenderChannelsContainer":
                channelNode = i
                break
        else:
            refreshAOVs(origin)
            return

        aovNum = int(origin.tw_passes.item(curItem.row(), 2).text())
        ccNode = channelNode.inputs()[aovNum]

        if ccNode.type().name() != "VRayNodeRenderChannelColor":
            refreshAOVs(origin)
            return

        typeMenu = QMenu()

        types = ccNode.parm("alias").menuLabels()

        for i in types:
            tAct = QAction(i, origin)
            tAct.triggered.connect(lambda z=None, x=curItem, y=i: x.setText(y))
            tAct.triggered.connect(lambda z=None, x=curItem: origin.setPassData(x))
            typeMenu.addAction(tAct)

        typeMenu.setStyleSheet(origin.stateManager.parent().styleSheet())
        typeMenu.exec_(QCursor.pos())
    else:
        origin.tw_passes.mouseDbcEvent(event)


def setCam(origin, node, val):
    return origin.core.appPlugin.setNodeParm(node, "render_camera", val=val)


def executeAOVs(origin, outputName):
    outputName = outputName.replace(".$F4", "")

    if not origin.core.appPlugin.setNodeParm(
        origin.node, "SettingsOutput_img_save", val=True
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "SettingsOutput_img_file_path", val=outputName
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]

    if not origin.core.appPlugin.setNodeParm(
        origin.node, "SettingsOutput_img_file_needFrameNumber", val=True
    ):
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
    origin.node.parm("execute").pressButton()
    return True


def postExecute(origin):
    return True
