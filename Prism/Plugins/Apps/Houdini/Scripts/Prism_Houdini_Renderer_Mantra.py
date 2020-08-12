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

import hou

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *


label = "Mantra"
ropNames = ["ifd"]


def isActive():
    return True


def getCam(node):
    return hou.node(node.parm("camera").eval())


def createROP(origin):
    origin.node = hou.node("/out").createNode("ifd")


def setAOVData(origin, node, aovNum, item):
    if item.column() == 0:
        origin.core.appPlugin.setNodeParm(
            node, "vm_channel_plane" + aovNum, val=item.text()
        )
    elif item.column() == 1:
        origin.core.appPlugin.setNodeParm(
            node, "vm_variable_plane" + aovNum, val=item.text()
        )


def getDefaultPasses(origin):
    aovs = origin.core.getConfig(
        "defaultpasses", "houdini_mantra", configPath=origin.core.prismIni
    )
    if aovs is None:
        aovs = origin.core.appPlugin.renderPasses["houdini_mantra"]

    return aovs


def addAOV(origin, aovData):
    passNum = origin.node.parm("vm_numaux").eval() + 1
    origin.core.appPlugin.setNodeParm(origin.node, "vm_numaux", val=passNum)
    origin.core.appPlugin.setNodeParm(
        origin.node, "vm_channel_plane" + str(passNum), val=aovData[0]
    )
    origin.core.appPlugin.setNodeParm(
        origin.node, "vm_usefile_plane" + str(passNum), val=True
    )
    origin.core.appPlugin.setNodeParm(
        origin.node, "vm_variable_plane" + str(passNum), val=aovData[1]
    )


def refreshAOVs(origin):
    origin.tw_passes.horizontalHeaderItem(0).setText("Name")
    origin.tw_passes.horizontalHeaderItem(1).setText("VEX Variable")

    passNum = 0

    if origin.node is None:
        return

    for i in range(origin.node.parm("vm_numaux").eval()):
        if origin.node.parm("vm_disable_plane" + str(i + 1)).eval() == 1:
            continue

        passName = QTableWidgetItem(
            origin.node.parm("vm_channel_plane" + str(i + 1)).eval()
        )
        passVariable = QTableWidgetItem(
            origin.node.parm("vm_variable_plane" + str(i + 1)).eval()
        )
        passNItem = QTableWidgetItem(str(i))
        origin.tw_passes.insertRow(passNum)
        origin.tw_passes.setItem(passNum, 0, passName)
        origin.tw_passes.setItem(passNum, 1, passVariable)
        origin.tw_passes.setItem(passNum, 2, passNItem)
        passNum += 1


def deleteAOV(origin, row):
    pid = int(origin.tw_passes.item(row, 2).text())
    origin.node.parm("vm_numaux").removeMultiParmInstance(pid)


def aovDbClick(origin, event):
    origin.tw_passes.mouseDbcEvent(event)


def setCam(origin, node, val):
    return origin.core.appPlugin.setNodeParm(node, "camera", val=val)


def executeAOVs(origin, outputName):
    if not origin.core.appPlugin.setNodeParm(origin.node, "vm_picture", val=outputName):
        return [origin.state.text(0) + ": error - Publish canceled"]

    origin.passNames = []
    for i in range(origin.node.parm("vm_numaux").eval()):
        passVar = origin.node.parm("vm_variable_plane" + str(i + 1)).eval()
        passName = origin.node.parm("vm_channel_plane" + str(i + 1)).eval()
        origin.passNames.append([passName, passVar])
        passOutputName = os.path.join(
            os.path.dirname(os.path.dirname(outputName)),
            passName,
            os.path.basename(outputName).replace("beauty", passName),
        )
        if not os.path.exists(os.path.split(passOutputName)[0]):
            os.makedirs(os.path.split(passOutputName)[0])

        if not origin.core.appPlugin.setNodeParm(
            origin.node, "vm_usefile_plane" + str(i + 1), val=True
        ):
            return [origin.state.text(0) + ": error - Publish canceled"]
        if not origin.core.appPlugin.setNodeParm(
            origin.node, "vm_filename_plane" + str(i + 1), val=passOutputName
        ):
            return [origin.state.text(0) + ": error - Publish canceled"]

        if passVar != "all":
            if not origin.core.appPlugin.setNodeParm(
                origin.node, "vm_channel_plane" + str(i + 1), val="rgb"
            ):
                return [origin.state.text(0) + ": error - Publish canceled"]
        else:
            if not origin.core.appPlugin.setNodeParm(
                origin.node, "vm_channel_plane" + str(i + 1), val=""
            ):
                return [origin.state.text(0) + ": error - Publish canceled"]
            if not origin.core.appPlugin.setNodeParm(
                origin.node, "vm_lightexport" + str(i + 1), val=1
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
    bkrender = origin.stateManager.publishInfos["backgroundRender"]
    if bkrender is None:
        msg = QMessageBox(
            QMessageBox.Question,
            "Render",
            "How do you want to render?",
            QMessageBox.Cancel,
        )
        msg.addButton("Render", QMessageBox.YesRole)
        msg.addButton("Render in background", QMessageBox.YesRole)
        origin.core.parentWindow(msg)
        action = msg.exec_()
        origin.stateManager.publishInfos["backgroundRender"] = action
    else:
        if bkrender:
            action = 1
        else:
            action = 0

    if action == 0:
        origin.node.parm("execute").pressButton()
    elif action == 1:
        hou.hipFile.save()
        origin.node.parm("executebackground").pressButton()
    else:
        return "Rendering cancled."

    return True


def postExecute(origin):
    for i in range(origin.node.parm("vm_numaux").eval()):
        if not origin.core.appPlugin.setNodeParm(
            origin.node, "vm_channel_plane" + str(i + 1), val=origin.passNames[i][0]
        ):
            return [origin.state.text(0) + ": error - Publish canceled"]

    return True
