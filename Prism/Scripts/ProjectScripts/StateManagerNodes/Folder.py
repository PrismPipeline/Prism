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


from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


class FolderClass(object):
    className = "Folder"

    def setup(self, state, core, stateManager, stateData=None, listType=None):
        self.core = core
        self.state = state
        self.stateManager = stateManager
        self.canSetVersion = True
        self.e_name.setText(state.text(0))

        if listType is None:
            if stateManager.activeList == stateManager.tw_import:
                listType = "Import"
            else:
                listType = "Export"

        self.listType = listType

        self.connectEvents()

        if stateData is not None:
            self.loadData(stateData)

    def loadData(self, data):
        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "listtype" in data:
            self.listType = data["listtype"]
        if "stateenabled" in data and self.listType == "Export":
            self.state.setCheckState(
                0,
                eval(
                    data["stateenabled"]
                    .replace("PySide.QtCore.", "")
                    .replace("PySide2.QtCore.", "")
                ),
            )
        if "stateexpanded" in data:
            if not data["stateexpanded"]:
                self.stateManager.collapsedFolders.append(self.state)

        self.core.callback("onStateSettingsLoaded", self, data)

    def connectEvents(self):
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)

    def nameChanged(self, text):
        self.state.setText(0, text)

    def updateUi(self):
        return True

    def preExecuteState(self, states=None):
        warnings = [[self.state.text(0), []]]

        for i in range(self.state.childCount()):
            curState = self.state.child(i)
            if (states is None or id(curState) in [id(s) for s in states] or curState.ui.className == "Folder") and curState.checkState(0) == Qt.Checked:
                if curState.ui.className == "Folder":
                    warnings += curState.ui.preExecuteState(states=states)
                else:
                    warnings.append(curState.ui.preExecuteState())

        return warnings

    def executeState(self, parent, useVersion="next"):
        result = []
        self.osSubmittedJobs = {}
        self.osDependencies = []
        self.dependencies = []

        for i in range(self.state.childCount()):
            curState = self.state.child(i)
            if (self.stateManager.publishType == "execute" or curState.checkState(0) == Qt.Checked) and (curState.ui.className == "Folder" or curState in set(
                self.stateManager.execStates
            )):
                if getattr(curState.ui, "canSetVersion", False):
                    exResult = curState.ui.executeState(
                        parent=self, useVersion=useVersion
                    )
                else:
                    exResult = curState.ui.executeState(parent=self)

                if curState.ui.className == "Folder":
                    result += exResult

                    for k in exResult:
                        if "publish paused" in k["result"][0]:
                            return result
                else:
                    result.append({"state": curState.ui, "result": exResult})

                    if exResult and "publish paused" in exResult[0]:
                        return result

        self.osSubmittedJobs = {}
        self.osDependencies = []
        self.dependencies = []
        return result

    def getStateProps(self):
        return {
            "statename": self.e_name.text(),
            "listtype": self.listType,
            "stateenabled": str(self.state.checkState(0)),
            "stateexpanded": self.state.isExpanded(),
        }
