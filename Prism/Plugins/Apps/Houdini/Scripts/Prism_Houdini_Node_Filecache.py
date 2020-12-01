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
    def onNodeCreated(self, kwargs):
        self.plugin.onNodeCreated(kwargs)
        state = self.getStateFromNode(kwargs)
        task = state.ui.getTaskname()
        kwargs["node"].parm("task").set(task)
        state.ui.setOutputType(kwargs["node"].parm("format").evalAsString())
        kwargs["node"].setColor(hou.Color(0.95, 0.5, 0.05))

    @err_catcher(name=__name__)
    def getStateFromNode(self, kwargs):
        return self.plugin.getStateFromNode(kwargs)

    @err_catcher(name=__name__)
    def setTaskFromNode(self, kwargs):
        state = self.getStateFromNode(kwargs)
        state.ui.setTaskname(kwargs["script_value"])

    @err_catcher(name=__name__)
    def showInStateManagerFromNode(self, kwargs):
        self.plugin.showInStateManagerFromNode(kwargs)

    @err_catcher(name=__name__)
    def openInExplorerFromNode(self, kwargs):
        self.plugin.openInExplorerFromNode(kwargs)

    @err_catcher(name=__name__)
    def refreshNodeUi(self, node, state):
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
