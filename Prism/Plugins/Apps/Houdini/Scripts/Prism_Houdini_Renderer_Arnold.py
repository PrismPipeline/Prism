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


label = "Arnold"
ropNames = ["arnold"]


def isActive():
    return hou.nodeType(hou.ropNodeTypeCategory(), "arnold") is not None


def getCam(node):
    return hou.node(node.parm("camera").eval())


def createROP(origin):
    origin.node = origin.core.appPlugin.createRop("arnold")


def setAOVData(origin, node, aovNum, item):
    if item.column() == 0:
        origin.core.appPlugin.setNodeParm(
            node, "ar_aov_label" + aovNum, val=item.text()
        )
    elif item.column() == 1:
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
        passName = QTableWidgetItem(
            origin.node.parm("ar_aov_exr_layer_name" + str(i + 1)).eval()
        )
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
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "ar_picture_format", val="exr"
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]
    if not origin.core.appPlugin.setNodeParm(origin.node, "ar_picture", val=outputName):
        return [origin.state.text(0) + ": error - Publish canceled"]

    origin.passNames = []
    for i in range(origin.node.parm("ar_aovs").eval()):
        passVar = origin.node.parm("ar_aov_label" + str(i + 1)).eval()
        passName = origin.node.parm("ar_aov_exr_layer_name" + str(i + 1)).eval()
        origin.passNames.append([passName, passVar])
        passOutputName = os.path.join(
            os.path.dirname(os.path.dirname(outputName)),
            passName,
            os.path.basename(outputName).replace("beauty", passName),
        )
        if not os.path.exists(os.path.split(passOutputName)[0]):
            os.makedirs(os.path.split(passOutputName)[0])

        if not origin.core.appPlugin.setNodeParm(
            origin.node, "ar_aov_separate" + str(i + 1), val=True
        ):
            return [origin.state.text(0) + ": error - Publish canceled"]
        if not origin.core.appPlugin.setNodeParm(
            origin.node, "ar_aov_separate_file" + str(i + 1), val=passOutputName
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
