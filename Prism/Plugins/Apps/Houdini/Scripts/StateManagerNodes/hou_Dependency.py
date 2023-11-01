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
        self.e_name.setText(state.text(0) + " ({count})")

        self.dependencies = {}

        self.l_name.setVisible(False)
        self.e_name.setVisible(False)

        self.nameChanged(state.text(0))
        self.connectEvents()

        self.cb_manager.addItems([p.pluginName for p in self.core.plugins.getRenderfarmPlugins()])
        self.core.callback("onStateStartup", self)

        self.managerChanged()

        if stateData is not None:
            self.loadData(stateData)

    @err_catcher(name=__name__)
    def loadData(self, data):
        if "stateName" in data:
            self.e_name.setText(data["stateName"])
        elif "statename" in data:
            self.e_name.setText(data["statename"] + " ({count})")
        if "rjmanager" in data:
            idx = self.cb_manager.findText(data["rjmanager"])
            if idx != -1:
                self.cb_manager.setCurrentIndex(idx)

            self.managerChanged()
        if "clearDeps" in data:
            self.chb_clear.setChecked(data["clearDeps"])
        if "dependencyType" in data:
            idx = self.cb_depType.findText(data["dependencyType"])
            if idx != -1:
                self.cb_depType.setCurrentIndex(idx)

            self.depTypeChanged()
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

        self.core.callback("onStateSettingsLoaded", self, data)
        self.updateUi()

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.chb_clear.toggled.connect(self.stateManager.saveStatesToScene)
        self.cb_manager.activated.connect(self.managerChanged)
        self.cb_depType.activated.connect(self.depTypeChanged)
        self.sp_offset.editingFinished.connect(self.stateManager.saveStatesToScene)

    @err_catcher(name=__name__)
    def managerChanged(self, text=None):
        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def depTypeChanged(self, text=None):
        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def getDependencyType(self):
        return self.cb_depType.currentText()

    @err_catcher(name=__name__)
    def setDependencyType(self, depType):
        idx = self.cb_depType.findText(depType)
        if idx != -1:
            self.cb_depType.setCurrentIndex(idx)

        self.depTypeChanged()

    @err_catcher(name=__name__)
    def setDependencies(self, deps):
        self.dependencies[self.cb_manager.currentText()] = deps
        self.updateUi()

    @err_catcher(name=__name__)
    def nameChanged(self, text):
        if self.cb_manager.currentText() in self.dependencies:
            numDeps = len(self.dependencies[self.cb_manager.currentText()])
        else:
            numDeps = 0

        text = self.e_name.text()
        context = {"count": numDeps}

        num = 0
        try:
            if "{#}" in text:
                while True:
                    context["#"] = num or ""
                    name = text.format(**context)
                    for state in self.stateManager.states:
                        if state.ui.listType != "Export":
                            continue

                        if state is self.state:
                            continue

                        if state.text(0) == name:
                            num += 1
                            break
                    else:
                        break
            else:
                name = text.format(**context)
        except Exception:
            name = text

        if self.state.text(0).endswith(" - disabled"):
            name += " - disabled"

        self.state.setText(0, name)

    @err_catcher(name=__name__)
    def updateUi(self):
        plugin = self.core.plugins.getRenderfarmPlugin(self.cb_manager.currentText())
        if plugin:
            plugin.sm_dep_updateUI(self)
        
        vis = bool(plugin and (self.cb_manager.count() > 1))
        self.f_manager.setVisible(vis)

        self.nameChanged(self.e_name.text())

    @err_catcher(name=__name__)
    def preDelete(self, item, silent=False):
        self.core.appPlugin.sm_preDelete(self, item, silent)

    @err_catcher(name=__name__)
    def preExecuteState(self):
        warnings = []

        plugin = self.core.plugins.getRenderfarmPlugin(self.cb_manager.currentText())
        if plugin:
            warnings += plugin.sm_dep_preExecute(self)

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def executeState(self, parent):
        try:
            plugin = self.core.plugins.getRenderfarmPlugin(self.cb_manager.currentText())
            if plugin:
                plugin.sm_dep_execute(
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
        return {
            "stateName": self.e_name.text(),
            "rjmanager": str(self.cb_manager.currentText()),
            "clearDeps": self.chb_clear.isChecked(),
            "dependencyType": self.cb_depType.currentText(),
            "frameoffset": self.sp_offset.value(),
            "dependencies": str(self.dependencies),
            "stateenabled": str(self.state.checkState(0)),
        }
