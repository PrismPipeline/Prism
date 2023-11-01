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


label = "Arnold"
ropNames = ["arnold"]


def isActive():
    return hou.nodeType(hou.ropNodeTypeCategory(), "arnold") is not None


def activated(origin):
    origin.w_separateAovs.setHidden(False)
    deep = ".exr (deep)"
    idx = origin.cb_format.findText(deep)
    if idx == -1:
        origin.cb_format.addItem(deep)


def deactivated(origin):
    origin.w_separateAovs.setHidden(True)
    deep = ".exr (deep)"
    idx = origin.cb_format.findText(deep)
    if idx != -1:
        origin.cb_format.removeItem(idx)


def getCam(node):
    return hou.node(node.parm("camera").eval())


def getFormatFromNode(node):
    fmt = node.parm("ar_picture_format").eval()
    if fmt == "jpeg":
        fmt = "jpg"
    elif fmt == "deepexr":
        fmt = "exr (deep)"

    fmt = "." + fmt
    return fmt


def setFormatOnNode(fmt, node):
    if fmt == ".jpg":
        fmt = "jpeg"
    elif fmt == ".png":
        fmt = "png"
    elif fmt == ".exr":
        fmt = "exr"
    elif fmt == ".exr (deep)":
        fmt = "deepexr"
    else:
        return

    node.parm("ar_picture_format").set(fmt)
    return True


def createROP(origin):
    origin.node = origin.core.appPlugin.createRop("arnold")


def setAOVData(origin, node, aovNum, item):
    if item.column() == 0:
        origin.core.appPlugin.setNodeParm(
            node, "ar_aov_label" + aovNum, val=item.text()
        )
    elif item.column() == 1:
        origin.core.appPlugin.setNodeParm(
            origin.node, "ar_aov_exr_enable_layer_name" + aovNum, val=True
        )
        origin.core.appPlugin.setNodeParm(
            node, "ar_aov_exr_layer_name" + aovNum, val=item.text()
        )


def getDefaultPasses(origin):
    aovs = origin.core.getConfig(
        "defaultpasses", "houdini_arnold", configPath=origin.core.prismIni
    )
    if aovs is None:
        aovs = origin.core.appPlugin.renderPasses["houdini_arnold"]

    return aovs


def addAOV(origin, aovData):
    passNum = origin.node.parm("ar_aovs").evalAsInt() + 1
    origin.core.appPlugin.setNodeParm(origin.node, "ar_aovs", val=passNum)
    origin.core.appPlugin.setNodeParm(
        origin.node, "ar_aov_label" + str(passNum), val=aovData[0]
    )
    origin.core.appPlugin.setNodeParm(
        origin.node, "ar_aov_exr_enable_layer_name" + str(passNum), val=True
    )
    origin.core.appPlugin.setNodeParm(
        origin.node, "ar_aov_exr_layer_name" + str(passNum), val=aovData[1]
    )


def refreshAOVs(origin):
    origin.tw_passes.horizontalHeaderItem(0).setText("Type")
    origin.tw_passes.horizontalHeaderItem(1).setText("Name")

    passNum = 0

    if origin.node is None:
        return

    for i in range(origin.node.parm("ar_aovs").eval()):
        if origin.node.parm("ar_enable_aov" + str(i + 1)).eval() == 0:
            continue

        labelParm = origin.node.parm("ar_aov_label" + str(i + 1))
        passTypeToken = labelParm.eval()
        passTypeName = QTableWidgetItem(passTypeToken)

        if origin.node.parm("ar_aov_exr_enable_layer_name" + str(i + 1)).eval():
            passName = origin.node.parm("ar_aov_exr_layer_name" + str(i + 1)).eval()
        else:
            passName = passTypeToken

        passName = QTableWidgetItem(passName)
        passNItem = QTableWidgetItem(str(i))
        origin.tw_passes.insertRow(passNum)
        origin.tw_passes.setItem(passNum, 0, passTypeName)
        origin.tw_passes.setItem(passNum, 1, passName)
        origin.tw_passes.setItem(passNum, 2, passNItem)
        passNum += 1


def deleteAOV(origin, row):
    pid = int(origin.tw_passes.item(row, 2).text())
    origin.node.parm("ar_aovs").removeMultiParmInstance(pid)


def aovDbClick(origin, event):
    if origin.node is None or event.button() != Qt.LeftButton:
        origin.tw_passes.mouseDbcEvent(event)
        return

    curItem = origin.tw_passes.itemFromIndex(origin.tw_passes.indexAt(event.pos()))
    if curItem is not None and curItem.column() == 0:
        typeMenu = QMenu()

        types = origin.node.parm("ar_aov_label1").menuLabels()
        token = origin.node.parm("ar_aov_label1").menuItems()
        for idx, i in enumerate(token):
            tAct = QAction(types[idx], origin)
            tAct.triggered.connect(lambda z=None, x=curItem, y=i: x.setText(y))
            tAct.triggered.connect(lambda z=None, x=curItem: origin.setPassData(x))
            nameItem = origin.tw_passes.item(curItem.row(), 1)
            tAct.triggered.connect(lambda z=None, x=nameItem, y=i: x.setText(y))
            tAct.triggered.connect(lambda z=None, x=nameItem: origin.setPassData(x))
            typeMenu.addAction(tAct)

        typeMenu.setStyleSheet(origin.stateManager.parent().styleSheet())
        typeMenu.exec_(QCursor.pos())
    else:
        origin.tw_passes.mouseDbcEvent(event)


def setCam(origin, node, val):
    return origin.core.appPlugin.setNodeParm(node, "camera", val=val)


def executeAOVs(origin, outputName):
    if (
        not origin.gb_submit.isHidden()
        and origin.gb_submit.isChecked()
        and origin.cb_manager.currentText() == "Deadline"
        and origin.chb_rjASSs.isChecked()
    ):
        renderASSs = True

        assOutput = os.path.join(
            os.path.dirname(outputName), "_ass", os.path.basename(outputName)
        )
        assOutput = os.path.splitext(assOutput)[0] + ".ass"
        parmPath = origin.core.appPlugin.getPathRelativeToProject(assOutput) if origin.core.appPlugin.getUseRelativePath() else assOutput
        if not origin.core.appPlugin.setNodeParm(
            origin.node, "ar_ass_file", val=parmPath
        ):
            return [
                origin.state.text(0)
                + ": error - could not set archive filename. Publish canceled"
            ]

        os.makedirs(os.path.dirname(assOutput))

    else:
        renderASSs = False

    if not origin.core.appPlugin.setNodeParm(
        origin.node, "ar_ass_export_enable", val=renderASSs
    ):
        return [
            origin.state.text(0)
            + ": error - could not set archive enabled. Publish canceled"
        ]

    base, ext = os.path.splitext(outputName)
    if ext == ".exr":
        formatVal = "exr"
    elif ext == ".png":
        formatVal = "png"
    elif ext == ".jpg":
        formatVal = "jpeg"
    else:
        return [
            origin.state.text(0) + ": error - invalid image format. Publish canceled"
        ]

    if not origin.core.appPlugin.setNodeParm(
        origin.node, "ar_picture_format", val=formatVal
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]

    parmPath = origin.core.appPlugin.getPathRelativeToProject(outputName) if origin.core.appPlugin.getUseRelativePath() else outputName
    if not origin.core.appPlugin.setNodeParm(origin.node, "ar_picture", val=parmPath):
        return [origin.state.text(0) + ": error - Publish canceled"]

    origin.passNames = []
    for i in range(origin.node.parm("ar_aovs").eval()):
        passVar = origin.node.parm("ar_aov_label" + str(i + 1)).eval()
        if origin.node.parm("ar_aov_exr_enable_layer_name" + str(i + 1)).eval():
            passName = origin.node.parm("ar_aov_exr_layer_name" + str(i + 1)).eval()
        else:
            passName = passVar

        origin.passNames.append([passName, passVar])
        passOutputName = os.path.join(
            os.path.dirname(os.path.dirname(outputName)),
            passName,
            os.path.basename(outputName).replace("beauty", passName),
        )
        separateAovs = origin.chb_separateAovs.isChecked()

        if separateAovs:
            if not os.path.exists(os.path.split(passOutputName)[0]):
                os.makedirs(os.path.split(passOutputName)[0])

        if not origin.core.appPlugin.setNodeParm(
            origin.node, "ar_aov_separate" + str(i + 1), val=separateAovs
        ):
            return [origin.state.text(0) + ": error - Publish canceled"]

        if not separateAovs:
            continue

        parmPath = origin.core.appPlugin.getPathRelativeToProject(passOutputName) if origin.core.appPlugin.getUseRelativePath() else passOutputName
        if not origin.core.appPlugin.setNodeParm(
            origin.node, "ar_aov_separate_file" + str(i + 1), val=parmPath
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


def getCleanupScript():
    script = """

import os
import sys
import shutil

assOutput = sys.argv[-1]

delDir = os.path.dirname(assOutput)
if os.path.basename(delDir) != "_ass":
    raise RuntimeError("invalid rs directory: %s" % (delDir))

if os.path.exists(delDir):
    shutil.rmtree(delDir)
    print("task completed successfully")
else:
    print("directory doesn't exist")

"""
    return script
