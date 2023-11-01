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

import hou

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


label = "3Delight"
ropNames = ["3Delight"]


def isActive():
    return hou.nodeType(hou.ropNodeTypeCategory(), ropNames[0]) is not None


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
    fmt = node.parm("default_image_format").eval()
    if fmt == "deepexr":
        fmt = ".exr (deep)"
    else:
        fmt = "." + fmt

    return fmt


def createROP(origin):
    origin.node = origin.core.appPlugin.createRop(ropNames[0])


def setAOVData(origin, node, aovNum, item):
    origin.core.appPlugin.setNodeParm(node, "aov_name_" + aovNum, val=item.text())


def getDefaultPasses(origin):
    aovs = origin.core.getConfig(
        "defaultpasses", "houdini_3delight", configPath=origin.core.prismIni
    )
    if aovs is None:
        aovs = origin.core.appPlugin.renderPasses["houdini_3delight"]

    return aovs


def addAOV(origin, aovData):
    passNum = origin.node.parm("aov").evalAsInt() + 1
    origin.core.appPlugin.setNodeParm(origin.node, "aov", val=passNum)
    origin.core.appPlugin.setNodeParm(
        origin.node, "aov_name_" + str(passNum), val=aovData[0]
    )


def refreshAOVs(origin):
    origin.tw_passes.horizontalHeaderItem(0).setText("Name")
    origin.tw_passes.setColumnHidden(1, True)

    passNum = 0

    if origin.node is None:
        return

    for i in range(origin.node.parm("aov").eval()):
        if origin.node.parm("active_layer_" + str(i + 1)).eval() == 0:
            continue

        labelParm = origin.node.parm("aov_name_" + str(i + 1))
        passTypeToken = labelParm.eval()
        passTypeName = QTableWidgetItem(passTypeToken)
        passNItem = QTableWidgetItem(str(i))
        origin.tw_passes.insertRow(passNum)
        origin.tw_passes.setItem(passNum, 0, passTypeName)
        origin.tw_passes.setItem(passNum, 2, passNItem)
        passNum += 1


def deleteAOV(origin, row):
    pid = int(origin.tw_passes.item(row, 2).text())
    origin.node.parm("aov").removeMultiParmInstance(pid)


def aovDbClick(origin, event):
    if origin.node is None or event.button() != Qt.LeftButton:
        origin.tw_passes.mouseDbcEvent(event)
        return

    curItem = origin.tw_passes.itemFromIndex(origin.tw_passes.indexAt(event.pos()))
    if curItem is not None and curItem.column() == 0:
        typeMenu = QMenu()

        aovNames = getDefaultPasses(origin)
        for idx, aovName in enumerate(aovNames):
            tAct = QAction(aovName, origin)
            tAct.triggered.connect(lambda z=None, x=curItem, y=aovName: x.setText(y))
            tAct.triggered.connect(lambda z=None, x=curItem: origin.setPassData(x))
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
        and origin.chb_rjNSIs.isChecked()
    ):
        nsi = True

        nsiOutput = getNsiOutputPath(origin, outputName)
        parmPath = origin.core.appPlugin.getPathRelativeToProject(nsiOutput) if origin.core.appPlugin.getUseRelativePath() else nsiOutput
        if not origin.core.appPlugin.setNodeParm(
            origin.node, "default_export_nsi_filename", val=parmPath
        ):
            return [
                origin.state.text(0)
                + ": error - could not set filename. Publish canceled"
            ]

    else:
        nsi = False

    if not origin.core.appPlugin.setNodeParm(
        origin.node, "display_rendered_images", val=False
    ):
        return [
            origin.state.text(0)
            + ": error - could not set display images. Publish canceled"
        ]

    if not origin.core.appPlugin.setNodeParm(
        origin.node, "save_rendered_images", val=False
    ):
        return [
            origin.state.text(0)
            + ": error - could not set save images. Publish canceled"
        ]

    if not origin.core.appPlugin.setNodeParm(
        origin.node, "display_and_save_rendered_images", val=not nsi
    ):
        return [
            origin.state.text(0)
            + ": error - could not set display and save images. Publish canceled"
        ]

    if not origin.core.appPlugin.setNodeParm(origin.node, "output_nsi_files", val=nsi):
        return [
            origin.state.text(0)
            + ": error - could not set nsi export. Publish canceled"
        ]

    parmPath = origin.core.appPlugin.getPathRelativeToProject(outputName) if origin.core.appPlugin.getUseRelativePath() else outputName
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "default_image_filename", val=parmPath
    ):
        return [
            origin.state.text(0) + ": error - could not set filename. Publish canceled"
        ]

    base, ext = os.path.splitext(outputName)
    if ext == ".exr":
        if origin.cb_format.currentText() == ".exr (deep)":
            formatVal = "deepexr"
        else:
            formatVal = "exr"
    elif ext == ".png":
        formatVal = "png"
    else:
        return [
            origin.state.text(0) + ": error - invalid image format. Publish canceled"
        ]

    if not origin.core.appPlugin.setNodeParm(
        origin.node, "default_image_format", val=formatVal
    ):
        return [
            origin.state.text(0) + ": error - could not set format. Publish canceled"
        ]

    return True


def setResolution(origin):
    cam = getCam(origin.node)
    width = origin.sp_resWidth.value()
    height = origin.sp_resHeight.value()
    if not origin.core.appPlugin.setNodeParm(cam, "resx", val=width):
        return [origin.state.text(0) + ": error - Publish canceled"]

    if not origin.core.appPlugin.setNodeParm(cam, "resy", val=height):
        return [origin.state.text(0) + ": error - Publish canceled"]

    return True


def executeRender(origin):
    if origin.node.parm("sequence_render"):
        origin.node.parm("sequence_render").pressButton()
    else:
        origin.node.parm("execute").pressButton()

    while origin.node.parm("rendering").eval() or (
        origin.node.parm("sequence_rendering")
        and origin.node.parm("sequence_rendering").eval()
    ):
        time.sleep(1)

    return True


def postExecute(origin):
    return True


def getNsiRenderScript():
    script = """

import os
import sys
import subprocess

imgOutput = sys.argv[-1]
nsiOutput = sys.argv[-2]
endFrame = int(sys.argv[-3])
startFrame = int(sys.argv[-4])

dlbase = os.getenv("DELIGHT")
dlpath = os.path.join(dlbase, "bin", "renderdl")

for frame in range(startFrame, (endFrame+1)):
    nsi = nsiOutput.replace("####", "%04d" % (frame))
    output = imgOutput.replace("####", "%04d" % (frame))
    args = [dlpath, nsi]
    print("command args: %s" % (args))
    p = subprocess.Popen(args)
    p.communicate()
    if p.returncode:
        raise RuntimeError("renderer exited with code %s" % p.returncode)
    elif not os.path.exists(output) and "<aov>" not in output:
        raise RuntimeError("expected output doesn't exist %s" % (output))
    else:
        print("successfully rendered frame %s" % (frame))

print("task completed successfully")

"""
    return script


def getCleanupScript():
    script = """

import os
import sys
import shutil

nsiOutput = sys.argv[-1]

delDir = os.path.dirname(nsiOutput)
if os.path.basename(delDir) != "_nsi":
    raise RuntimeError("invalid nsi directory: %s" % (delDir))

if os.path.exists(delDir):
    shutil.rmtree(delDir)
    print("task completed successfully")
else:
    print("directory doesn't exist")

"""
    return script


def getNsiOutputPath(origin, renderOutputPath):
    jobOutputFile = os.path.join(
        os.path.dirname(renderOutputPath), "_nsi", os.path.basename(renderOutputPath)
    )
    jobOutputFile = os.path.splitext(jobOutputFile)[0] + ".nsi"
    return jobOutputFile
