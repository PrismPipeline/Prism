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

"""Houdini Dependency state for Prism State Manager.

Manages renderfarm job dependencies in Houdini, allowing states to wait
for other jobs to complete before execution. Supports different dependency
types and frame offset handling for sequential rendering workflows.
"""

import sys
import time
import traceback
from typing import Any, Optional, Dict, List

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

import hou

from PrismUtils.Decorators import err_catcher as err_catcher


class DependencyClass(object):
    """Renderfarm dependency state for sequential job execution.
    
    Manages dependencies between renderfarm jobs, allowing jobs to wait
    for completion of other jobs before starting. Supports frame offsets
    and dependency type selection.
    
    Attributes:
        className (str): State class identifier.
        listType (str): State list category.
        state: State Manager tree item.
        core: PrismCore instance.
        stateManager: State Manager instance.
        dependencies (Dict): Render farm manager to dependency mapping.
    """
    
    className = "Dependency"
    listType = "Export"

    @err_catcher(name=__name__)
    def setup(self, state: Any, core: Any, stateManager: Any, stateData: Optional[Dict] = None) -> None:
        """Initialize dependency state.
        
        Sets up UI, connects events, populates renderfarm managers,
        and loads saved state data.
        
        Args:
            state: State Manager tree item for this state.
            core: PrismCore instance.
            stateManager: State Manager instance.
            stateData: Optional saved state data to load.
        """
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
    def loadData(self, data: Dict) -> None:
        """Load state data from dictionary.
        
        Restores state settings including manager, dependencies, dependency type,
        frame offset, and enabled state.
        
        Args:
            data: Dictionary containing saved state data.
        """
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
            if type(data["stateenabled"]) == int:
                self.state.setCheckState(
                    0, Qt.CheckState(data["stateenabled"]),
                )

        self.core.callback("onStateSettingsLoaded", self, data)
        self.updateUi()

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect UI widget signals to handlers.
        
        Links text edits, checkboxes, combobboxes, and spinboxes to their
        respective change handlers and state save operations.
        """
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.chb_clear.toggled.connect(self.stateManager.saveStatesToScene)
        self.cb_manager.activated.connect(self.managerChanged)
        self.cb_depType.activated.connect(self.depTypeChanged)
        self.sp_offset.editingFinished.connect(self.stateManager.saveStatesToScene)

    @err_catcher(name=__name__)
    def managerChanged(self, text: Optional[str] = None) -> None:
        """Handle renderfarm manager selection change.
        
        Updates UI and saves state when user changes the renderfarm plugin.
        
        Args:
            text: unused parameter from signal.
        """
        rfm = self.cb_manager.currentText()
        plugin = self.core.plugins.getRenderfarmPlugin(rfm)
        if plugin:
            plugin.sm_dep_managerChanged(self)

        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def depTypeChanged(self, text: Optional[str] = None) -> None:
        """Handle dependency type change.
        
        Updates UI and saves state when dependency type is changed.
        
        Args:
            text: Unused parameter from signal.
        """
        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def getDependencyType(self) -> str:
        """Get selected dependency type.
        
        Returns:
            Current dependency type text from combobox.
        """
        return self.cb_depType.currentText()

    @err_catcher(name=__name__)
    def setDependencyType(self, depType: str) -> None:
        """Set dependency type from string.
        
        Args:
            depType: Dependency type to set.
        """
        idx = self.cb_depType.findText(depType)
        if idx != -1:
            self.cb_depType.setCurrentIndex(idx)

        self.depTypeChanged()

    @err_catcher(name=__name__)
    def setDependencies(self, deps: Any) -> None:
        """Set job dependencies for current manager.
        
        Stores dependency data for the currently selected renderfarm manager.
        
        Args:
            deps: Dependency data specific to the renderfarm plugin.
        """
        self.dependencies[self.cb_manager.currentText()] = deps
        self.updateUi()

    @err_catcher(name=__name__)
    def nameChanged(self, text: str) -> None:
        """Handle state name change.
        
        Updates state name with dependency count substitution and ensures
        unique names by appending numbers if needed. Supports {count} and {#}
        placeholders.
        
        Args:
            text: New name text.
        """
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
                    name = text.format_map(self.core.safeFormatDict(context))
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
                name = text.format_map(self.core.safeFormatDict(context))
        except Exception:
            name = text

        if self.state.text(0).endswith(" - disabled"):
            name += " - disabled"

        self.state.setText(0, name)

    @err_catcher(name=__name__)
    def updateUi(self) -> None:
        """Update UI visibility and content.
        
        Updates UI based on current manager plugin and refreshes state name
        with dependency count.
        """
        plugin = self.core.plugins.getRenderfarmPlugin(self.cb_manager.currentText())
        if plugin:
            plugin.sm_dep_updateUI(self)
        
        vis = bool(plugin and (self.cb_manager.count() > 1))
        self.f_manager.setVisible(vis)

        self.nameChanged(self.e_name.text())

    @err_catcher(name=__name__)
    def preDelete(self, item: Any, silent: bool = False) -> None:
        """Handle pre-delete event.
        
        Args:
            item: Tree item being deleted.
            silent: Whether to skip confirmation dialogs.
        """
        self.core.appPlugin.sm_preDelete(self, item, silent)

    @err_catcher(name=__name__)
    def preExecuteState(self) -> List[Any]:
        """Check for warnings before state execution.
        
        Validates dependency configuration and returns any warnings.
        
        Returns:
            List containing state name and list of warning messages.
        """
        warnings = []

        plugin = self.core.plugins.getRenderfarmPlugin(self.cb_manager.currentText())
        if plugin:
            warnings += plugin.sm_dep_preExecute(self)

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def executeState(self, parent: Any) -> List[str]:
        """Execute dependency state.
        
        Delegates to renderfarm plugin to set up job dependencies.
        
        Args:
            parent: Parent state or submission object.
            
        Returns:
            List with status message.
        """
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
    def getStateProps(self) -> Dict[str, Any]:
        """Get state properties for saving.
        
        Returns:
            Dictionary of state data for serialization.
        """
        return {
            "stateName": self.e_name.text(),
            "rjmanager": str(self.cb_manager.currentText()),
            "clearDeps": self.chb_clear.isChecked(),
            "dependencyType": self.cb_depType.currentText(),
            "frameoffset": self.sp_offset.value(),
            "dependencies": str(self.dependencies),
            "stateenabled": self.core.getCheckStateValue(self.state.checkState(0)),
        }
