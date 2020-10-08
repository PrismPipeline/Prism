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


import sys
import time
import traceback

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

import hou

from PrismUtils.Decorators import err_catcher as err_catcher


class DependencyClass(object):
    className = "Dependency"
    listType = "Export"

    @err_catcher(name=__name__)
    def setup(self, state, core, stateManager, stateData=None):
        self.state = state
        self.core = core
        self.stateManager = stateManager
        self.e_name.setText(state.text(0))

        self.dependencies = {}

        self.node = None

        self.l_name.setVisible(False)
        self.e_name.setVisible(False)
        self.lw_osStates.setMinimumSize(0, 700)
        self.tw_caches.setMinimumSize(0, 700)

        self.nameChanged(state.text(0))
        self.connectEvents()

        for i in self.core.rfManagers.values():
            self.cb_manager.addItem(i.pluginName)
            self.dependencies[i.pluginName] = []
            i.sm_dep_startup(self)

        self.managerChanged()

        if stateData is not None:
            self.loadData(stateData)

    @err_catcher(name=__name__)
    def loadData(self, data):
        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "rjmanager" in data:
            idx = self.cb_manager.findText(data["rjmanager"])
            if idx != -1:
                self.cb_manager.setCurrentIndex(idx)
            self.managerChanged()
        if "connectednode" in data:
            self.node = hou.node(data["connectednode"])
            if self.node is None:
                self.node = self.findNode(data["connectednode"])
        if "frameoffset" in data:
            self.sp_offset.setValue(int(data["frameoffset"]))
        if "dependencies" in data:
            self.dependencies = eval(data["dependencies"])
        if "stateenabled" in data:
            self.state.setCheckState(
                0,
                eval(
                    data["stateenabled"]
                    .replace("PySide.QtCore.", "")
                    .replace("PySide2.QtCore.", "")
                ),
            )
        self.updateUi()

    @err_catcher(name=__name__)
    def findNode(self, path):
        for node in hou.node("/").allSubChildren():
            if (
                node.userData("PrismPath") is not None
                and node.userData("PrismPath") == path
            ):
                node.setUserData("PrismPath", node.path())
                return node

        return None

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.cb_manager.activated.connect(self.managerChanged)
        self.b_connect.clicked.connect(self.connectNode)
        self.sp_offset.editingFinished.connect(self.stateManager.saveStatesToScene)

    @err_catcher(name=__name__)
    def managerChanged(self, text=None):
        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def nameChanged(self, text):
        if self.cb_manager.currentText() in self.dependencies:
            numDeps = len(self.dependencies[self.cb_manager.currentText()])
        else:
            numDeps = 0

        sText = text + " (" + str(numDeps) + ")"

        if self.state.text(0).endswith(" - disabled"):
            sText += " - disabled"

        self.state.setText(0, sText)

    @err_catcher(name=__name__)
    def connectNode(self):
        if len(hou.selectedNodes()) > 0 and (
            hou.selectedNodes()[0].type().name() == "file"
        ):
            self.node = hou.selectedNodes()[0]
            self.updateUi()
            self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def isNodeValid(self, node):
        try:
            node.name()
            return True
        except:
            return False

    @err_catcher(name=__name__)
    def updateUi(self):
        if self.cb_manager.currentText() in self.core.rfManagers:
            self.core.rfManagers[self.cb_manager.currentText()].sm_dep_updateUI(self)
        else:
            self.gb_osDependency.setVisible(False)
            self.gb_dlDependency.setVisible(False)

        self.nameChanged(self.e_name.text())

    @err_catcher(name=__name__)
    def preDelete(self, item, silent=False):
        self.core.appPlugin.sm_preDelete(self, item, silent)

    @err_catcher(name=__name__)
    def preExecuteState(self):
        warnings = []

        if self.cb_manager.currentText() in self.core.rfManagers:
            warnings += self.core.rfManagers[
                self.cb_manager.currentText()
            ].sm_dep_preExecute(self)

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def executeState(self, parent):
        try:
            if self.cb_manager.currentText() in self.core.rfManagers:
                self.core.rfManagers[self.cb_manager.currentText()].sm_dep_execute(
                    self, parent
                )

            return [self.state.text(0) + " - success"]

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            erStr = "%s ERROR - houDependency %s:\n%s" % (
                time.strftime("%d/%m/%y %X"),
                self.core.version,
                traceback.format_exc(),
            )
            self.core.writeErrorLog(erStr)
            return [
                self.state.text(0)
                + " - unknown error (view console for more information)"
            ]

    @err_catcher(name=__name__)
    def getStateProps(self):
        try:
            curNode = self.node.path()
            self.node.setUserData("PrismPath", curNode)
        except:
            curNode = None

        return {
            "statename": self.e_name.text(),
            "rjmanager": str(self.cb_manager.currentText()),
            "connectednode": str(curNode),
            "frameoffset": self.sp_offset.value(),
            "dependencies": str(self.dependencies),
            "stateenabled": str(self.state.checkState(0)),
        }
