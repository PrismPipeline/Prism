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
import logging

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher as err_catcher

import hou

logger = logging.getLogger(__name__)


class Prism_Houdini_ImportFile(object):
    def __init__(self, plugin):
        self.plugin = plugin
        self.core = self.plugin.core
        self.stateType = "ImportFile"
        self.listType = "Import"

    @err_catcher(name=__name__)
    def getTypeName(self):
        return "prism::ImportFile"

    @err_catcher(name=__name__)
    def onNodeCreated(self, kwargs):
        self.plugin.onNodeCreated(kwargs)
        kwargs["node"].setColor(hou.Color(0.451, 0.369, 0.796))
        if os.getenv("PRISM_HOUDINI_IMPORT_SELECTABLE_PARMS") == "1":
            self.plugin.setNodeParm(kwargs["node"], "selectableInfo", 1)

        self.getStateFromNode(kwargs)

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
        if not state:
            return

        state.ui.browse()
        self.refreshUiFromNode(kwargs, state)
        if state.parent() and state.parent().text(0) == "ImportNodes":
            self.updateStateParent(kwargs["node"], state)

    @err_catcher(name=__name__)
    def refreshUiFromNode(self, kwargs, state=None):
        state = state or self.getStateFromNode(kwargs)
        path = state.ui.getImportPath(expand=False)
        parmPath = self.core.appPlugin.getPathRelativeToProject(path) if self.core.appPlugin.getUseRelativePath() else path
        if parmPath != kwargs["node"].parm("filepath").eval():
            try:
                kwargs["node"].parm("filepath").set(parmPath)
            except:
                logger.debug(
                    'failed to set parm "filepath" on node %s' % kwargs["node"].path()
                )

        data = self.core.paths.getCachePathData(path)
        if data.get("type"):
            date = self.core.getFileModificationDate(
                os.path.dirname(path), validate=True
            )
            product = data.get("product", "")
            comment = data.get("comment", "")
            user = data.get("user", "")
        else:
            expandedPath = hou.text.expandString(path)
            if os.path.exists(expandedPath):
                date = self.core.getFileModificationDate(expandedPath, validate=True)
            else:
                date = ""
            product = ""
            comment = ""
            user = ""

        versionLabel = data.get("version", "")
        if versionLabel == "master":
            versionLabel = self.core.products.getMasterVersionLabel(path)

        if data.get("type") == "asset":
            name = data.get("asset_path", "")
        elif data.get("type") == "shot":
            name = self.core.entities.getShotName(data)

        try:
            kwargs["node"].parm("entity").set(name)
        except:
            logger.debug(
                'failed to set parm "entity" on node %s' % kwargs["node"].path()
            )

        try:
            kwargs["node"].parm("product").set(product)
        except:
            logger.debug('failed to set parm "product" on node %s' % kwargs["node"].path())

        try:
            kwargs["node"].parm("version").set(versionLabel)
        except:
            logger.debug(
                'failed to set parm "version" on node %s' % kwargs["node"].path()
            )

        try:
            kwargs["node"].parm("comment").set(comment)
        except:
            logger.debug(
                'failed to set parm "comment" on node %s' % kwargs["node"].path()
            )

        try:
            kwargs["node"].parm("user").set(user)
        except:
            logger.debug('failed to set parm "user" on node %s' % kwargs["node"].path())

        try:
            kwargs["node"].parm("date").set(date)
        except:
            logger.debug('failed to set parm "date" on node %s' % kwargs["node"].path())

    @err_catcher(name=__name__)
    def setPathFromNode(self, kwargs):
        state = self.getStateFromNode(kwargs)
        state.ui.setImportPath(kwargs["script_value"])
        state.ui.importObject()
        state.ui.updateUi()
        self.refreshUiFromNode(kwargs)

    @err_catcher(name=__name__)
    def getParentFolder(self, create=True, node=None):
        parents = ["ImportNodes"]
        if node:
            cachePath = node.parm("filepath").eval()
            data = self.core.paths.getCachePathData(cachePath)
            if data.get("type") == "asset":
                parents = (
                    os.path.dirname(data["asset_path"]).replace("\\", "/").split("/")
                )
            elif data.get("type") == "shot":
                parents = [data["sequence"], data["shot"]]

        sm = self.core.getStateManager()
        if not sm:
            return

        state = None
        states = sm.states
        createdStates = []
        for parent in parents:
            cstate = self.findFolderState(states, parent)
            if cstate:
                state = cstate
            else:
                if not create:
                    return state

                stateData = {
                    "statename": parent,
                    "listtype": "Import",
                    "stateexpanded": True,
                }
                state = sm.createState("Folder", stateData=stateData, parent=state)
                createdStates.append(state)

            states = [state.child(idx) for idx in range(state.childCount())]

        for cs in createdStates:
            cs.setExpanded(True)

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
        product = node.parm("product").eval()
        version = node.parm("version").eval()

        descr = product + "\n" + version
        return descr

    @err_catcher(name=__name__)
    def abcGroupsToggled(self, kwargs):
        state = self.getStateFromNode(kwargs)
        if not state:
            return

        abcNode = state.ui.fileNode
        if not abcNode:
            return

        if abcNode.type().name() != "alembic":
            return

        if kwargs["node"].parm("groupsAbc").eval():
            abcNode.parm("groupnames").set(4)
        else:
            abcNode.parm("groupnames").set(0)
