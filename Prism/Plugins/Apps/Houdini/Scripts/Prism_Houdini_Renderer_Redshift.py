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
import time
import glob

import hou

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


label = "Redshift"
ropNames = ["Redshift_ROP"]


def isActive():
    return hou.nodeType(hou.ropNodeTypeCategory(), "Redshift_ROP")


def getCam(node):
    return hou.node(node.parm("RS_renderCamera").eval())


def getFormatFromNode(node):
    fmt = node.parm("RS_outputFileFormat").evalAsString()
    return fmt


def createROP(origin):
    origin.node = origin.core.appPlugin.createRop("Redshift_ROP")
    origin.node2 = origin.core.appPlugin.createRop("Redshift_IPR")
    origin.node2.moveToGoodPosition()


def setAOVData(origin, node, aovNum, item):
    if item.column() == 0:
        typeNames = node.parm("RS_aovID_" + aovNum).menuLabels()
        typeId = typeNames.index(item.text())
        origin.core.appPlugin.setNodeParm(node, "RS_aovID_" + aovNum, val=typeId)
    elif item.column() == 1:
        origin.core.appPlugin.setNodeParm(
            node, "RS_aovSuffix_" + aovNum, val=item.text()
        )


def getDefaultPasses(origin):
    aovs = origin.core.getConfig(
        "defaultpasses", "houdini_redshift", configPath=origin.core.prismIni
    )
    if aovs is None:
        aovs = origin.core.appPlugin.renderPasses["houdini_redshift"]

    return aovs


def addAOV(origin, aovData):
    passNum = origin.node.parm("RS_aov").eval() + 1
    origin.core.appPlugin.setNodeParm(origin.node, "RS_aov", val=passNum)
    typeID = origin.node.parm("RS_aovID_" + str(passNum)).menuLabels().index(aovData[0])
    origin.core.appPlugin.setNodeParm(
        origin.node, "RS_aovID_" + str(passNum), val=typeID
    )
    origin.core.appPlugin.setNodeParm(
        origin.node, "RS_aovSuffix_" + str(passNum), val=aovData[1]
    )


def refreshAOVs(origin):
    origin.tw_passes.horizontalHeaderItem(0).setText("Type")
    origin.tw_passes.horizontalHeaderItem(1).setText("Name")

    passNum = 0

    if origin.node is None:
        return

    for i in range(origin.node.parm("RS_aov").eval()):
        if origin.node.parm("RS_aovEnable_" + str(i + 1)).eval() == 0:
            continue

        passTypeID = origin.node.parm("RS_aovID_" + str(i + 1)).eval()
        passTypeName = QTableWidgetItem(
            origin.node.parm("RS_aovID_" + str(i + 1)).menuLabels()[passTypeID]
        )
        passName = QTableWidgetItem(
            origin.node.parm("RS_aovSuffix_" + str(i + 1)).eval()
        )
        passNItem = QTableWidgetItem(str(i))
        origin.tw_passes.insertRow(passNum)
        origin.tw_passes.setItem(passNum, 0, passTypeName)
        origin.tw_passes.setItem(passNum, 1, passName)
        origin.tw_passes.setItem(passNum, 2, passNItem)
        passNum += 1


def deleteAOV(origin, row):
    pid = int(origin.tw_passes.item(row, 2).text())
    origin.node.parm("RS_aov").removeMultiParmInstance(pid)


def aovDbClick(origin, event):
    if origin.node is None or event.button() != Qt.LeftButton:
        origin.tw_passes.mouseDbcEvent(event)
        return

    curItem = origin.tw_passes.itemFromIndex(origin.tw_passes.indexAt(event.pos()))
    if curItem is not None and curItem.column() == 0:
        typeMenu = QMenu()

        types = origin.node.parm("RS_aovID_1").menuLabels()

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
    return origin.core.appPlugin.setNodeParm(node, "RS_renderCamera", val=val)


def executeAOVs(origin, outputName):
    if (
        not origin.gb_submit.isHidden()
        and origin.gb_submit.isChecked()
        and origin.cb_manager.currentText() == "Deadline"
        and origin.chb_rjRS.isChecked()
    ):
        renderRS = True

        rsOutput = os.path.join(
            os.path.dirname(outputName), "_rs", os.path.basename(outputName)
        )
        rsOutput = os.path.splitext(rsOutput)[0] + ".rs"
        parmPath = origin.core.appPlugin.getPathRelativeToProject(rsOutput) if origin.core.appPlugin.getUseRelativePath() else rsOutput
        if not origin.core.appPlugin.setNodeParm(
            origin.node, "RS_archive_file", val=parmPath
        ):
            return [
                origin.state.text(0)
                + ": error - could not set archive filename. Publish canceled"
            ]

        os.makedirs(os.path.dirname(rsOutput))

    else:
        renderRS = False

    if not origin.core.appPlugin.setNodeParm(
        origin.node, "RS_archive_enable", val=renderRS
    ):
        return [
            origin.state.text(0)
            + ": error - could not set archive enabled. Publish canceled"
        ]

    if not origin.core.appPlugin.setNodeParm(origin.node, "RS_outputEnable", val=True):
        return [origin.state.text(0) + ": error - Publish canceled"]

    parmPath = origin.core.appPlugin.getPathRelativeToProject(outputName) if origin.core.appPlugin.getUseRelativePath() else outputName
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "RS_outputFileNamePrefix", val=parmPath
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]

    if origin.node.parm("RS_outputMultilayerMode").eval() != "2":
        origin.core.appPlugin.setNodeParm(
            origin.node, "RS_outputDisableSuffixes", val=1, severity="debug"
        )

    for parm in origin.node.parms():
        if "RS_aovCustomPrefix" in parm.name():
            currentAOVID = parm.name().split("_")[-1]
            layerParmName = "RS_aovSuffix_" + currentAOVID
            layerName = origin.node.parm(layerParmName).eval()
            commonOutPut = origin.node.parm(
                "RS_outputFileNamePrefix"
            ).unexpandedString()
            outPut = commonOutPut.replace("beauty", layerName)

            if not origin.core.appPlugin.setNodeParm(
                origin.node, parm.name(), clear=True
            ):
                return [origin.state.text(0) + ": error - Publish canceled"]

            if origin.node.parm("RS_outputMultilayerMode").eval() == "2":
                outPut = ""

            if not origin.core.appPlugin.setNodeParm(
                origin.node, parm.name(), val=outPut
            ):
                return [origin.state.text(0) + ": error - Publish canceled"]

    base, ext = os.path.splitext(outputName)
    if ext in [".exr", ".png", ".jpg"]:
        formatVal = ext
    else:
        return [
            origin.state.text(0) + ": error - invalid image format. Publish canceled"
        ]

    if not origin.core.appPlugin.setNodeParm(
        origin.node, "RS_outputFileFormat", val=formatVal
    ):
        return [
            origin.state.text(0) + ": error - could not set format. Publish canceled"
        ]

    return True


def setResolution(origin):
    # RS resolution override in config doesn't work with Deadline, so it will be set before submittig
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "RS_overrideCameraRes", val=True
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "RS_overrideResScale", val="user"
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "RS_overrideRes1", val=origin.sp_resWidth.value()
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "RS_overrideRes2", val=origin.sp_resHeight.value()
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]

    return True


def executeRender(origin):
    origin.node.parm("execute").pressButton()
    waitForRenderCompleted(origin.node)
    return True


def waitForRenderCompleted(node):
    outputPath = node.parm("RS_outputFileNamePrefix").eval()
    outputDir = os.path.dirname(outputPath)
    globPath = outputDir + "/*.lock"
    # waitTime = 0
    # maxWaitTime = 10
    while glob.glob(globPath):
        time.sleep(1)
        # waitTime += 1
        # if waitTime >= maxWaitTime:
            # return False

    return True


def postExecute(origin):
    return True


def getCleanupScript():
    script = """

import os
import sys
import shutil

rsOutput = sys.argv[-1]

delDir = os.path.dirname(rsOutput)
if os.path.basename(delDir) != "_rs":
    raise RuntimeError("invalid rs directory: %s" % (delDir))

if os.path.exists(delDir):
    shutil.rmtree(delDir)
    print("task completed successfully")
else:
    print("directory doesn't exist")

"""
    return script
