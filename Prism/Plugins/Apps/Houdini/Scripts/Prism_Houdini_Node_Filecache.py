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


import logging

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

from PrismUtils.Decorators import err_catcher as err_catcher

import hou

logger = logging.getLogger(__name__)


class Prism_Houdini_Filecache(object):
    def __init__(self, plugin):
        self.plugin = plugin
        self.core = self.plugin.core

    @err_catcher(name=__name__)
    def getTypeName(self):
        return "prism::Filecache"

    @err_catcher(name=__name__)
    def getFormats(self):
        blacklisted = [".hda", "ShotCam", "other", ".rs"]
        appFormats = self.core.appPlugin.outputFormats
        nodeFormats = [f for f in appFormats if f not in blacklisted]
        bgsc = nodeFormats.pop(1)
        nodeFormats.insert(0, bgsc)

        tokens = []
        for f in nodeFormats:
            tokens.append(f)
            tokens.append(f)

        return tokens

    @err_catcher(name=__name__)
    def getReadVersions(self, kwargs):
        versions = []
        versions.insert(0, "latest")

        tokens = []
        for v in versions:
            tokens.append(v)
            tokens.append(v)

        return tokens

    @err_catcher(name=__name__)
    def getSaveVersions(self, kwargs):
        versions = []
        versions.insert(0, "next")

        tokens = []
        for v in versions:
            tokens.append(v)
            tokens.append(v)

        return tokens

    @err_catcher(name=__name__)
    def onNodeCreated(self, kwargs):
        self.plugin.onNodeCreated(kwargs)
        state = self.getStateFromNode(kwargs)
        task = state.ui.getTaskname()
        kwargs["node"].parm("task").set(task)
        state.ui.setRangeType("Node")
        state.ui.setOutputType(kwargs["node"].parm("format").evalAsString())
        kwargs["node"].setColor(hou.Color(0.95, 0.5, 0.05))
        kwargs["node"].parm("_init").set(1)

    @err_catcher(name=__name__)
    def onNodeDeleted(self, kwargs):
        self.plugin.onNodeDeleted(kwargs)

    @err_catcher(name=__name__)
    def getStateFromNode(self, kwargs):
        return self.plugin.getStateFromNode(kwargs)

    @err_catcher(name=__name__)
    def setTaskFromNode(self, kwargs):
        state = self.getStateFromNode(kwargs)
        state.ui.setTaskname(kwargs["script_value"])

    @err_catcher(name=__name__)
    def setFormatFromNode(self, kwargs):
        state = self.getStateFromNode(kwargs)
        state.ui.setOutputType(kwargs["script_value"])

    @err_catcher(name=__name__)
    def showInStateManagerFromNode(self, kwargs):
        self.plugin.showInStateManagerFromNode(kwargs)

    @err_catcher(name=__name__)
    def openInExplorerFromNode(self, kwargs):
        state = self.getStateFromNode(kwargs)
        folderpath = state.ui.l_pathLast.text()
        self.core.openFolder(folderpath)

    @err_catcher(name=__name__)
    def refreshNodeUi(self, node, state):
        if not node.parm("_init").eval():
            return

        taskname = state.getTaskname()
        self.plugin.setNodeParm(node, "task", taskname, clear=True)
        rangeType = state.getRangeType()
        startFrame, endFrame = state.getFrameRange(rangeType)
        if endFrame is None:
            endFrame = startFrame

        if startFrame != node.parm("f1").eval():
            self.plugin.setNodeParm(node, "f1", startFrame, clear=True)

        if endFrame != node.parm("f2").eval():
            self.plugin.setNodeParm(node, "f2", endFrame, clear=True)

        outType = state.getOutputType()
        self.plugin.setNodeParm(node, "format", outType, clear=True)

    @err_catcher(name=__name__)
    def executeNode(self, node):
        if node.parm("format").evalAsString() == ".abc":
            ropName = "write_alembic"
        else:
            ropName = "write_geo"

        rop = node.node(ropName)
        rop.parm("execute").pressButton()
        QCoreApplication.processEvents()
        self.core.popup("Finished caching successfully.", severity="info", modal=False)

    @err_catcher(name=__name__)
    def executePressed(self, kwargs):
        sm = self.core.getStateManager()
        state = self.getStateFromNode(kwargs)
        version = self.getWriteVersionFromNode(kwargs["node"])
        sm.publish(executeState=True, useVersion=version, states=[state], successPopup=False)

    @err_catcher(name=__name__)
    def getReadVersionFromNode(self, node):
        if node.parm("latestVersionRead").eval():
            version = "latest"
        else:
            version = node.parm("readVersion").evalAsString()

        return version

    @err_catcher(name=__name__)
    def getWriteVersionFromNode(self, node):
        if node.parm("nextVersionWrite").eval():
            version = "next"
        else:
            version = node.parm("writeVersion").evalAsString()

        return version

    @err_catcher(name=__name__)
    def getParentFolder(self, create=True):
        sm = self.core.getStateManager()
        for state in sm.states:
            if state.ui.listType != "Export" or state.ui.className != "Folder":
                continue

            if state.ui.e_name.text() != "Filecaches":
                continue

            return state

        if create:
            stateData = {
                "statename": "Filecaches",
                "listtype": "Export",
                "stateenabled": "PySide2.QtCore.Qt.CheckState.Checked",
                "stateexpanded": False,
            }
            state = sm.createState("Folder", stateData=stateData)
            return state

    @err_catcher(name=__name__)
    def findExistingVersion(self, kwargs, mode):
        import TaskSelection

        ts = TaskSelection.TaskSelection(core=self.core)
        widget = ts.tw_versions
        self.core.parentWindow(widget)
        widget.setWindowTitle("Select Version")
        widget.resize(1000, 600)

        ts.productPathSet.connect(lambda x, m=mode, k=kwargs: self.versionSelected(x, m, k))
        ts.productPathSet.connect(widget.close)

        widget.show()

    @err_catcher(name=__name__)
    def versionSelected(self, path, mode, kwargs):
        if not path:
            return

        version = self.core.products.getVersionFromFilepath(path, num=True)

        if mode == "write":
            kwargs["node"].parm("nextVersionWrite").set(0)
            kwargs["node"].parm("writeVersion").set(version)
        elif mode == "read":
            kwargs["node"].parm("latestVersionRead").set(0)
            kwargs["node"].parm("readVersion").set(version)
            kwargs["node"].parm("importPath").set(path)

        return version

    @err_catcher(name=__name__)
    def getImportPath(self):
        node = hou.pwd()
        product = node.parm("task").eval()
        version = self.getReadVersionFromNode(node)
        if version == "latest":
            path = self.core.products.getLatestVersionpathFromProduct(product)
        else:
            path = self.core.products.getVersionpathFromProductVersion(product, version)

        if path:
            path = path.replace("\\", "/")
        else:
            path = ""

        return path
