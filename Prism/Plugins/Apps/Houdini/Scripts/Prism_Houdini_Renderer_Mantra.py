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


label = "Mantra"
ropNames = ["ifd"]


def isActive():
    return True


def activated(origin):
    deep = ".exr (deep)"
    idx = origin.cb_format.findText(deep)
    if idx == -1:
        origin.cb_format.addItem(deep)


def deactivated(origin):
    deep = ".exr (deep)"
    idx = origin.cb_format.findText(deep)
    if idx != -1:
        origin.cb_format.removeItem(idx)


def getCam(node):
    return hou.node(node.parm("camera").eval())


def getFormatFromNode(node):
    ext = os.path.splitext(node.parm("vm_picture").eval())[1]
    if ext == ".exr" and node.parm("vm_deepresolver").eval() != "null":
        ext = ".exr (deep)"

    return ext


def createROP(origin):
    origin.node = origin.core.appPlugin.createRop("ifd")


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
    if (
        not origin.gb_submit.isHidden()
        and origin.gb_submit.isChecked()
        and origin.cb_manager.currentText() == "Deadline"
        and origin.chb_rjIFDs.isChecked()
    ):
        renderIFD = True

        ifdOutput = os.path.join(
            os.path.dirname(outputName), "_ifd", os.path.basename(outputName)
        )
        ifdOutput = os.path.splitext(ifdOutput)[0] + ".ifd"
        parmPath = origin.core.appPlugin.getPathRelativeToProject(ifdOutput) if origin.core.appPlugin.getUseRelativePath() else ifdOutput
        if not origin.core.appPlugin.setNodeParm(
            origin.node, "soho_diskfile", val=parmPath
        ):
            return [
                origin.state.text(0)
                + ": error - could not set archive filename. Publish canceled"
            ]

        os.makedirs(os.path.dirname(ifdOutput))

    else:
        renderIFD = False

    if not origin.core.appPlugin.setNodeParm(
        origin.node, "soho_outputmode", val=renderIFD
    ):
        return [
            origin.state.text(0)
            + ": error - could not set archive enabled. Publish canceled"
        ]

    parmPath = origin.core.appPlugin.getPathRelativeToProject(outputName) if origin.core.appPlugin.getUseRelativePath() else outputName
    if not origin.core.appPlugin.setNodeParm(origin.node, "vm_picture", val=parmPath):
        return [origin.state.text(0) + ": error - Publish canceled"]

    if origin.cb_format.currentText() == ".exr (deep)":
        if not origin.core.appPlugin.setNodeParm(origin.node, "vm_deepresolver", val="camera"):
            return [origin.state.text(0) + ": error - Publish canceled"]

        deepPath = os.path.splitext(parmPath)[0]
        if deepPath.endswith(".$F4"):
            deepPath = deepPath[:-4] + "_deep" + ".$F4"
        else:
            deepPath += "_deep"

        deepPath += os.path.splitext(parmPath)[1]
        if not origin.core.appPlugin.setNodeParm(origin.node, "vm_dcmfilename", val=deepPath):
            return [origin.state.text(0) + ": error - Publish canceled"]
    else:
        if not origin.core.appPlugin.setNodeParm(origin.node, "vm_deepresolver", val="null"):
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

        parmPath = origin.core.appPlugin.getPathRelativeToProject(passOutputName) if origin.core.appPlugin.getUseRelativePath() else passOutputName
        if not origin.core.appPlugin.setNodeParm(
            origin.node, "vm_filename_plane" + str(i + 1), val=parmPath
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
        msg = "How do you want to render?"
        result = origin.core.popupQuestion(
            msg, buttons=["Render", "Render in background", "Cancel"], default="Render"
        )
        origin.stateManager.publishInfos["backgroundRender"] = result
    else:
        result = bkrender

    if result == "Render":
        origin.node.parm("execute").pressButton()
    elif result == "Render in background":
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


def getCleanupScript():
    script = """

import os
import sys
import shutil

ifdOutput = sys.argv[-1]

delDir = os.path.dirname(ifdOutput)
if os.path.basename(delDir) != "_ifd":
    raise RuntimeError("invalid ifd directory: %s" % (delDir))

if os.path.exists(delDir):
    shutil.rmtree(delDir)
    print("task completed successfully")
else:
    print("directory doesn't exist")

"""
    return script
