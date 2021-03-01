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


class Prism_Houdini_ImportFile(object):
    def __init__(self, plugin):
        self.plugin = plugin
        self.core = self.plugin.core

    @err_catcher(name=__name__)
    def getTypeName(self):
        return "prism::ImportFile"

    @err_catcher(name=__name__)
    def onNodeCreated(self, kwargs):
        self.plugin.onNodeCreated(kwargs)
        kwargs["node"].setColor(hou.Color(0.451, 0.369, 0.796))

    @err_catcher(name=__name__)
    def onNodeDeleted(self, kwargs):
        self.plugin.onNodeDeleted(kwargs)

    @err_catcher(name=__name__)
    def getStateFromNode(self, kwargs):
        return self.plugin.getStateFromNode(kwargs)

    @err_catcher(name=__name__)
    def showInStateManagerFromNode(self, kwargs):
        self.plugin.showInStateManagerFromNode(kwargs)

    @err_catcher(name=__name__)
    def openInExplorerFromNode(self, kwargs):
        self.plugin.openInExplorerFromNode(kwargs)

    @err_catcher(name=__name__)
    def openProductBrowserFromNode(self, kwargs):
        state = self.getStateFromNode(kwargs)
        state.ui.browse()
        self.refreshUiFromNode(kwargs, state)
        if state.parent() and state.parent().text(0) == "ImportNodes":
            self.updateStateParent(kwargs["node"], state)

    @err_catcher(name=__name__)
    def refreshUiFromNode(self, kwargs, state=None):
        state = state or self.getStateFromNode(kwargs)
        path = state.ui.getImportPath()
        if path != kwargs["node"].parm("filepath").eval():
            try:
                kwargs["node"].parm("filepath").set(path)
            except:
                logger.debug("failed to set parm \"filepath\" on node %s" % kwargs["node"].path())

        data = self.core.paths.getCachePathData(path)
        if data["entityType"]:
            date = self.core.getFileModificationDate(os.path.dirname(path))
            task = data.get("task", "")
            versionDir = os.path.basename(os.path.dirname(os.path.dirname(path)))
            versionData = versionDir.split(self.core.filenameSeparator)
            if len(versionData) == 3:
                _, comment, user = versionData
            else:
                comment = data.get("comment", "")
                user = data.get("user", "")
        else:
            expandedPath = hou.expandString(path)
            if os.path.exists(expandedPath):
                date = self.core.getFileModificationDate(expandedPath)
            else:
                date = ""
            task = ""
            comment = ""
            user = ""

        versionLabel = data.get("version", "")
        versionName = self.core.products.getVersionNameFromFilepath(path)
        if versionName == "master":
            versionLabel = self.core.products.getMasterVersionLabel(path)

        try:
            kwargs["node"].parm("entity").set(data.get("fullEntity"))
        except:
            logger.debug("failed to set parm \"entity\" on node %s" % kwargs["node"].path())

        try:
            kwargs["node"].parm("task").set(task)
        except:
            logger.debug("failed to set parm \"task\" on node %s" % kwargs["node"].path())

        try:
            kwargs["node"].parm("version").set(versionLabel)
        except:
            logger.debug("failed to set parm \"version\" on node %s" % kwargs["node"].path())

        try:
            kwargs["node"].parm("comment").set(comment)
        except:
            logger.debug("failed to set parm \"comment\" on node %s" % kwargs["node"].path())

        try:
            kwargs["node"].parm("user").set(user)
        except:
            logger.debug("failed to set parm \"user\" on node %s" % kwargs["node"].path())

        try:
            kwargs["node"].parm("date").set(date)
        except:
            logger.debug("failed to set parm \"date\" on node %s" % kwargs["node"].path())

    @err_catcher(name=__name__)
    def setPathFromNode(self, kwargs):
        state = self.getStateFromNode(kwargs)
        state.ui.e_file.setText(kwargs["script_value"])
        state.ui.importObject()
        state.ui.updateUi()
        self.refreshUiFromNode(kwargs)

    @err_catcher(name=__name__)
    def getParentFolder(self, create=True, node=None):
        parents = ["ImportNodes"]
        if node:
            cachePath = node.parm("filepath").eval()
            data = self.core.paths.getCachePathData(cachePath)
            if data["entityType"] == "asset":
                parents = data["fullEntity"].replace("\\", "/").split("/")
            elif data["entityType"] == "shot":
                parents = [data["sequence"], data["shot"]]

        sm = self.core.getStateManager()
        state = None
        states = sm.states
        for parent in parents:
            cstate = self.findFolderState(states, parent)
            if cstate:
                state = cstate
            else:
                if not create:
                    return

                stateData = {
                    "statename": parent,
                    "listtype": "Import",
                    "stateexpanded": False,
                }
                state = sm.createState("Folder", stateData=stateData, parent=state)

            states = [state.child(idx) for idx in range(state.childCount())]

        return state

    @err_catcher(name=__name__)
    def updateStateParent(self, node, state):
        parent = self.getParentFolder(node=node)
        if parent is not state.parent():
            prevParent = state.parent()
            s = prevParent.takeChild(prevParent.indexOfChild(state))
            parent.addChild(s)
            sm = self.core.getStateManager()
            if prevParent:
                while True:
                    nextParent = prevParent.parent()
                    if prevParent.childCount() == 0:
                        sm.deleteState(prevParent)

                    if nextParent:
                        prevParent = nextParent
                    else:
                        return

    @err_catcher(name=__name__)
    def findFolderState(self, states, name):
        for state in states:
            if state.ui.listType != "Import" or state.ui.className != "Folder":
                continue

            if state.ui.e_name.text() == name:
                return state

    @err_catcher(name=__name__)
    def getNodeDescription(self):
        node = hou.pwd()
        task = node.parm("task").eval()
        version = node.parm("version").eval()

        descr = task + "\n" + version
        return descr

    @err_catcher(name=__name__)
    def abcGroupsToggled(self, kwargs):
        abcNode = self.getStateFromNode(kwargs).ui.fileNode
        if kwargs["node"].parm("groupsAbc").eval():
            abcNode.parm("groupnames").set(4)
        else:
            abcNode.parm("groupnames").set(0)
