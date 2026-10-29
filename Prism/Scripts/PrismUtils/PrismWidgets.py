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
import sys
import platform
from typing import Any, Optional, List, Dict, Union

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher
from UserInterfacesPrism import CreateItem_ui, EnterText_ui, SetPath_ui, SaveComment_ui


class ContentSizedComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.setMinimumContentsLength(20)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def minimumSizeHint(self):
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        option.currentText = "M" * self.minimumContentsLength()
        metrics = self.fontMetrics()
        content = QSize(metrics.horizontalAdvance(option.currentText), metrics.height())
        return self.style().sizeFromContents(QStyle.CT_ComboBox, option, content, self)


class CreateItem(QDialog, CreateItem_ui.Ui_dlg_CreateItem):
    """Dialog for creating/entering item names with validation and task presets.
    
    A versatile dialog used throughout Prism for creating entities, tasks,
    departments, and other named items. Supports preset selection, character
    validation, and optional department/step creation.
    
    Attributes:
        core: PrismCore instance.
        getStep (bool): Whether to show department name field.
        taskType (str): Type of task for preset loading ('export', 'import', etc.).
        valueRequired (bool): Whether empty values are allowed.
        mode (str): Special behavior mode ('assetHierarchy', etc.).
        validate (bool): Whether to validate input characters.
        presets (Optional[List[str]]): List of preset values to offer.
        clickedButton: Which button the user clicked.
        itemName (str): The entered item name.
        taskList (List[str]): Available task presets.
        isTaskName (bool): Whether this is for a task name.
        allowChars (List[str]): Characters explicitly allowed.
        denyChars (List[str]): Characters explicitly denied.
        b_next: Optional "Next" button.
    """

    def __init__(
        self,
        startText: str = "",
        showTasks: bool = False,
        taskType: str = "",
        core: Optional[Any] = None,
        getStep: bool = False,
        showType: bool = False,
        allowChars: Optional[List[str]] = None,
        denyChars: Optional[List[str]] = None,
        valueRequired: bool = True,
        mode: str = "",
        validate: bool = True,
        presets: Optional[List[str]] = None,
        allowNext: bool = False,
    ) -> None:
        """Initialize the CreateItem dialog.
        
        Args:
            startText: Initial text to display in the input field. Defaults to "".
            showTasks: Whether to show task presets button. Defaults to False.
            taskType: Type of task for preset loading. Defaults to "".
            core: PrismCore instance. Defaults to None.
            getStep: Whether to show department name field. Defaults to False.
            showType: Whether to show asset type options. Defaults to False.
            allowChars: Characters explicitly allowed in input. Defaults to None.
            denyChars: Characters explicitly denied in input. Defaults to None.
            valueRequired: Whether empty values are allowed. Defaults to True.
            mode: Special behavior mode. Defaults to "".
            validate: Whether to validate input characters. Defaults to True.
            presets: List of preset values to offer. Defaults to None.
            allowNext: Whether to show a "Next" button. Defaults to False.
        """
        QDialog.__init__(self)
        self.setupUi(self)
        self.core = core
        self.getStep = getStep
        self.taskType = taskType
        self.valueRequired = valueRequired
        self.mode = mode
        self.validate = validate
        self.presets = presets
        self.clickedButton = None
        self.e_item.setText(startText)
        self.e_item.selectAll()
        self.taskList = []

        if self.valueRequired and not startText:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

        self.isTaskName = showTasks

        self.allowChars = allowChars or []
        self.denyChars = denyChars or []

        if not self.allowChars and not self.denyChars:
            if self.isTaskName:
                if self.taskType == "export":
                    self.denyChars = ["-"]

        if not showTasks and not presets:
            self.b_showTasks.setHidden(True)
        else:
            self.b_showTasks.setMinimumWidth(30)
            self.b_showTasks.setMinimumHeight(0)
            self.b_showTasks.setMaximumHeight(500)
            if self.presets:
                self.taskList = self.presets
            else:
                self.getTasks()

        if getStep:
            self.setWindowTitle("Create Department")
            self.l_item.setText("Abbreviation:")
            self.l_stepName = QLabel("Department Name:")
            self.e_stepName = QLineEdit()
            self.w_item.layout().addWidget(self.l_stepName)
            self.w_item.layout().addWidget(self.e_stepName)
            self.e_item.setMaximumWidth(100)
            self.resize(500 * self.core.uiScaleFactor, self.height())
            self.setTabOrder(self.e_item, self.e_stepName)

        if showType:
            self.core.callback(name="onCreateAssetDlgOpen", args=[self])
        else:
            self.w_type.setVisible(False)

        self.buttonBox.buttons()[0].setText("Create")
        self.btext = "Next"

        if self.mode in ["assetHierarchy"] or allowNext:
            self.b_next = self.buttonBox.addButton(self.btext, QDialogButtonBox.AcceptRole)
            if self.mode == "assetHierarchy":
                self.b_next.setToolTip("Create entity and open the department dialog")

            if not startText:
                self.b_next.setEnabled(False)
            self.b_next.setFocusPolicy(Qt.StrongFocus)
            self.b_next.setTabOrder(self.b_next, self.buttonBox.buttons()[0])
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "arrow_right.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            self.b_next.setIcon(icon)
        else:
            self.b_next = None

        self.resize(self.width(), 10)
        self.connectEvents()

    @err_catcher(name=__name__)
    def showEvent(self, event: QShowEvent) -> None:
        """Handle show event to hide empty options widget.
        
        Args:
            event: Qt show event.
        """
        if self.w_options.layout().count() == 0:
            self.w_options.setVisible(False)

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect all widget signals to their handler methods."""
        self.buttonBox.clicked.connect(self.buttonboxClicked)
        self.b_showTasks.clicked.connect(self.showTasks)
        if self.getStep:
            self.e_item.textEdited.connect(lambda x: self.enableOkStep(self.e_item))
            self.e_stepName.textEdited.connect(
                lambda x: self.enableOkStep(self.e_stepName)
            )
        else:
            self.e_item.textEdited.connect(lambda x: self.enableOk(self.e_item))
        self.rb_asset.toggled.connect(self.typeChanged)

    @err_catcher(name=__name__)
    def getTasks(self) -> None:
        """Load available task presets from core."""
        self.taskList = sorted(self.core.getTaskNames(self.taskType))

        if len(self.taskList) == 0:
            self.b_showTasks.setHidden(True)
        else:
            camProduct = self.core.products.getShotcamProductName()
            if camProduct in self.taskList:
                self.taskList.remove(camProduct)

    @err_catcher(name=__name__)
    def showTasks(self) -> None:
        """Display a context menu with available task presets."""
        tmenu = QMenu(self)

        for i in self.taskList:
            tAct = QAction(i, self)
            tAct.triggered.connect(lambda x=None, t=i: self.taskClicked(t))
            tmenu.addAction(tAct)

        tmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def taskClicked(self, task: str) -> None:
        """Handle when a task preset is selected from the menu.
        
        Args:
            task: Task name that was clicked.
        """
        self.e_item.setText(task)
        self.enableOk(self.e_item)

    @err_catcher(name=__name__)
    def typeChanged(self, state: bool) -> None:
        """Handle when asset type radio button state changes.
        
        Args:
            state: New state of the radio button.
        """
        self.core.callback(name="onCreateAssetDlgTypeChanged", args=[self, state])

    @err_catcher(name=__name__)
    def enableOk(self, widget: QLineEdit) -> None:
        """Enable/disable OK button based on input validation.
        
        Args:
            widget: Line edit widget to validate.
        """
        if self.validate:
            text = self.core.validateLineEdit(
                widget, allowChars=self.allowChars, denyChars=self.denyChars
            )
        else:
            text = widget.text()

        if self.valueRequired:
            if text != "":
                self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
            else:
                self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

        if self.b_next:
            self.b_next.setEnabled(bool(text))

    @err_catcher(name=__name__)
    def enableOkStep(self, widget: QLineEdit) -> None:
        """Enable/disable OK button for step/department creation mode.
        
        Requires both abbreviation and department name to be filled.
        
        Args:
            widget: Line edit widget being edited.
        """
        self.core.validateLineEdit(widget)

        if self.valueRequired:
            if self.e_item.text() != "" and self.e_stepName.text() != "":
                self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
            else:
                self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

    @err_catcher(name=__name__)
    def returnName(self) -> None:
        """Store the entered item name in self.itemName."""
        self.itemName = self.e_item.text()

    @err_catcher(name=__name__)
    def buttonboxClicked(self, button: QPushButton) -> None:
        """Handle button box clicks.
        
        Args:
            button: Button that was clicked.
        """
        self.clickedButton = button
        if button.text() == "Create":
            self.returnName()
            self.accept()
        elif button.text() == self.btext:
            self.accept()
        elif button.text() == "Cancel":
            self.reject()
        else:
            self.accept()

    @err_catcher(name=__name__)
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events for keyboard shortcuts.
        
        Args:
            event: Qt key event.
        """
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            if self.b_next:
                self.buttonboxClicked(self.b_next)
            else:
                if self.buttonBox.button(QDialogButtonBox.Ok).isEnabled():
                    self.accept()

        elif event.key() == Qt.Key_Escape:
            self.reject()


class CreateDepartmentDlg(QDialog):
    """Dialog for creating or editing a department configuration.
    
    Allows users to define a department with a name, abbreviation,
    and default task list for either asset or shot workflows.
    
    Signals:
        departmentCreated: Emitted when a department is created/edited. Args: (department dict).
    
    Attributes:
        core: PrismCore instance.
        entity: Optional entity string ('asset' or 'shot') to lock the entity type.
        configData: Optional config data dict.
    """

    departmentCreated = Signal(object)

    def __init__(self, core: Any, entity: Optional[str] = None, configData: Optional[Dict] = None, department: Optional[Dict] = None, parent: Optional[QWidget] = None) -> None:
        """Initialize the CreateDepartmentDlg.
        
        Args:
            core: PrismCore instance.
            entity: Optional entity type to lock ('asset' or 'shot').
            configData: Optional config data dict.
            department: Optional existing department dict for editing.
            parent: Optional parent widget.
        """
        QDialog.__init__(self)
        self.core = core
        self.entity = entity
        self.configData = configData
        self.core.parentWindow(self, parent)
        self.setupUi()
        if department:
            self.setWindowTitle("Edit Department")
            self.setName(department["name"])
            self.setAbbreviation(department["abbreviation"])
            self.setDefaultTasks(department["defaultTasks"])
            self.bb_main.buttons()[0].setText("Save")

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Set up the user interface for the dialog."""
        self.setWindowTitle("Create Department")
        self.lo_main = QGridLayout()
        self.setLayout(self.lo_main)

        self.l_entity = QLabel("Entity:")
        self.cb_entity = QComboBox()
        self.cb_entity.addItems(["Asset", "Shot"])
        self.l_name = QLabel("Department Name:")
        self.e_name = QLineEdit()
        self.l_abbreviation = QLabel("Abbreviation:")
        self.e_abbreviation = QLineEdit()
        self.l_defaultTasks = QLabel("Default Tasks:\n(each line = one taskname)")
        self.te_defaultTasks = QTextEdit()

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Create", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Cancel", QDialogButtonBox.RejectRole)
        self.bb_main.accepted.connect(self.createClicked)
        self.bb_main.rejected.connect(self.reject)

        self.lo_main.addWidget(self.l_entity, 0, 0)
        self.lo_main.addWidget(self.cb_entity, 0, 1)
        self.lo_main.addWidget(self.l_name, 1, 0)
        self.lo_main.addWidget(self.e_name, 1, 1)
        self.lo_main.addWidget(self.l_abbreviation, 2, 0)
        self.lo_main.addWidget(self.e_abbreviation, 2, 1)
        self.lo_main.addWidget(self.l_defaultTasks, 3, 0)
        self.lo_main.addWidget(self.te_defaultTasks, 3, 1)
        self.lo_main.addWidget(self.bb_main, 4, 1)

        if self.entity:
            self.l_entity.setVisible(False)
            self.cb_entity.setVisible(False)

    @err_catcher(name=__name__)
    def getEntity(self) -> str:
        """Get the selected entity type ('asset' or 'shot').
        
        Returns:
            str: Entity type string.
        """
        if self.entity:
            return self.entity

        return self.cb_entity.currentText().lower()

    @err_catcher(name=__name__)
    def setEntity(self, entity: str) -> None:
        """Set the entity type in the combobox.
        
        Args:
            entity: Entity type string ('asset' or 'shot').
        """
        idx = self.cb_entity.findItems(entity, (Qt.MatchExactly & Qt.MatchCaseSensitive))
        if len(idx) != -1:
            self.cb_entity.setCurrentIndex(idx)

    @err_catcher(name=__name__)
    def getName(self) -> str:
        """Get the department name.
        
        Returns:
            Department name from text field
        """
        return self.e_name.text()

    @err_catcher(name=__name__)
    def setName(self, name: str) -> None:
        """Set the department name.
        
        Args:
            name: Department name to set
        """
        self.e_name.setText(name)

    @err_catcher(name=__name__)
    def getAbbreviation(self) -> str:
        """Get the department abbreviation.
        
        Returns:
            str: Department abbreviation.
        """
        return self.e_abbreviation.text()

    @err_catcher(name=__name__)
    def setAbbreviation(self, abbreviation: str) -> None:
        """Set the department abbreviation.
        
        Args:
            abbreviation: Department abbreviation.
        """
        self.e_abbreviation.setText(abbreviation)

    @err_catcher(name=__name__)
    def getDefaultTasks(self) -> List[str]:
        """Get the list of default tasks.
        
        Returns:
            List[str]: List of task names.
        """
        taskStr = self.te_defaultTasks.toPlainText()
        tasks = [t.strip(" ,") for t in taskStr.split("\n") if t.strip(" ,")]
        return tasks

    @err_catcher(name=__name__)
    def setDefaultTasks(self, tasks: List[str]) -> None:
        """Set the default tasks list.
        
        Args:
            tasks: List of task names.
        """
        taskStr = "\n".join(tasks)
        self.te_defaultTasks.setPlainText(taskStr)

    @err_catcher(name=__name__)
    def getDepartment(self) -> Dict[str, Any]:
        """Get the complete department configuration as a dict.
        
        Returns:
            Dict[str, Any]: Department dict with 'name', 'abbreviation', and 'defaultTasks' keys.
        """
        name = self.getName()
        abbreviation = self.getAbbreviation()
        defaultTasks = self.getDefaultTasks()
        department = {"name": name, "abbreviation": abbreviation, "defaultTasks": defaultTasks}
        return department

    @err_catcher(name=__name__)
    def createClicked(self) -> None:
        """Handle when create/save button is clicked.
        
        Validates input and either creates a new department or saves edits.
        """
        entity = self.getEntity()
        name = self.getName()
        abbreviation = self.getAbbreviation()
        defaultTasks = self.getDefaultTasks()

        if not name:
            self.core.popup("Please specify a department name.")
            return

        if not abbreviation:
            self.core.popup("Please specify a department abbreviation.")
            return

        if self.bb_main.buttons()[0].text() == "Create":
            department = self.core.projects.addDepartment(
                entity=entity,
                name=name,
                abbreviation=abbreviation,
                defaultTasks=defaultTasks,
                configData=self.configData
            )
            self.departmentCreated.emit(department)

        self.accept()


class CreateTaskPresetDlg(QDialog):
    """Dialog for creating or editing a task preset configuration.
    
    Allows users to define a task preset with a name and associate it with
    specific departments, making it available for those departments.
    
    Signals:
        taskPresetCreated: Emitted when a task preset is created/edited. Args: (preset dict).
    
    Attributes:
        core: PrismCore instance.
        entity: Optional entity string ('asset' or 'shot') to lock the entity type.
        configData: Optional config data dict.
    """

    taskPresetCreated = Signal(object)

    def __init__(self, core: Any, entity: Optional[str] = None, configData: Optional[Dict] = None, preset: Optional[Dict] = None, parent: Optional[QWidget] = None) -> None:
        """Initialize the CreateTaskPresetDlg.
        
        Args:
            core: PrismCore instance.
            entity: Optional entity type to lock ('asset' or 'shot').
            configData: Optional config data dict.
            preset: Optional existing preset dict for editing.
            parent: Optional parent widget.
        """
        QDialog.__init__(self)
        self.core = core
        self.entity = entity
        self.configData = configData
        self.core.parentWindow(self, parent)
        self.setupUi()
        self.refreshDepartments()
        if preset:
            self.setWindowTitle("Edit Task Preset")
            self.setName(preset["name"])
            self.selectDepartments(preset["departments"])
            self.bb_main.buttons()[0].setText("Save")

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Set up the user interface for the dialog."""
        self.setWindowTitle("Create Task Preset")
        self.lo_main = QVBoxLayout(self)

        self.w_name = QWidget()
        self.lo_name = QHBoxLayout(self.w_name)
        self.l_name = QLabel("Task Preset Name:")
        self.e_name = QLineEdit()
        self.lo_name.addWidget(self.l_name)
        self.lo_name.addWidget(self.e_name)

        self.w_presetDepartments = QWidget()
        self.lo_presetDepartments = QHBoxLayout(self.w_presetDepartments)
        self.lo_presetDepartments.setContentsMargins(0, 0, 0, 0)
        self.w_departments = QWidget()
        self.lo_departments = QVBoxLayout(self.w_departments)
        self.l_departments = QLabel("Departments:")
        self.lw_departments = QListWidget()
        self.lw_departments.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.lw_departments.itemSelectionChanged.connect(self.onDepartmentSelectionChanged)
        self.lo_departments.addWidget(self.l_departments)
        self.lo_departments.addWidget(self.lw_departments)

        self.w_tasks = QWidget()
        self.lo_tasks = QVBoxLayout(self.w_tasks)
        self.l_tasks = QLabel("Tasks:")
        self.lw_tasks = QListWidget()
        self.lw_tasks.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.lw_tasks.itemSelectionChanged.connect(self.onTaskSelectionChanged)
        self.lo_tasks.addWidget(self.l_tasks)
        self.lo_tasks.addWidget(self.lw_tasks)

        self.lo_presetDepartments.addWidget(self.w_departments)
        self.lo_presetDepartments.addWidget(self.w_tasks)

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Create", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Cancel", QDialogButtonBox.RejectRole)
        self.bb_main.accepted.connect(self.createClicked)
        self.bb_main.rejected.connect(self.reject)

        self.lo_main.addWidget(self.w_name)
        self.lo_main.addWidget(self.w_presetDepartments)
        self.lo_main.addWidget(self.bb_main)

    @err_catcher(name=__name__)
    def onDepartmentSelectionChanged(self) -> None:
        """Handle when department selection changes in the list.
        
        Updates the tasks list to show tasks for the selected department.
        """
        self.lw_tasks.blockSignals(True)
        self.lw_tasks.clear()
        self.lw_tasks.blockSignals(False)
        depItems = self.lw_departments.selectedItems()
        if len(depItems) != 1:
            return

        depData = depItems[0].data(Qt.UserRole)
        depName = depData["name"]
        if self.entity == "asset":
            departments = self.core.projects.getAssetDepartments()
        else:
            departments = self.core.projects.getShotDepartments()

        for department in departments:
            if department["name"] == depName:
                tasks = department.get("defaultTasks", [])
                break
        else:
            return

        for task in tasks:
            item = QListWidgetItem(task)
            self.lw_tasks.addItem(item)
            if task in depData["tasks"]:
                item.setSelected(True)

    @err_catcher(name=__name__)
    def onTaskSelectionChanged(self) -> None:
        """Handle when task selection changes.
        
        Updates the department item to reflect which tasks are selected.
        """
        item = self.lw_departments.selectedItems()[0]
        data = item.data(Qt.UserRole)
        data["tasks"] = [item.text() for item in self.lw_tasks.selectedItems()]
        item.setData(Qt.UserRole, data)
        name = data["name"]
        if data["tasks"]:
            name += " (%s)" % (", ".join(data["tasks"]))
        item.setText(name)

    @err_catcher(name=__name__)
    def getName(self) -> str:
        """Get the entity name.
        
        Returns:
            Entity name from text field
        """
        return self.e_name.text()

    @err_catcher(name=__name__)
    def setName(self, name: str) -> None:
        """Set the entity name.
        
        Args:
            name: Entity name to set
        """
        self.e_name.setText(name)

    @err_catcher(name=__name__)
    def getDepartments(self) -> List[Dict[str, Any]]:
        """Get the list of selected departments with their tasks.
        
        Returns:
            List[Dict[str, Any]]: List of department dicts with 'name' and 'tasks' keys.
        """
        departments = []
        for item in self.lw_departments.selectedItems():
            dep = item.data(Qt.UserRole)
            departments.append(dep)

        return departments

    @err_catcher(name=__name__)
    def selectDepartments(self, departments: List[Dict[str, Any]]) -> None:
        """Select and configure departments in the list.
        
        Args:
            departments: List of department dicts to select.
        """
        self.lw_departments.clearSelection()
        for idx in range(self.lw_departments.count()):
            item = self.lw_departments.item(idx)
            itemData = item.data(Qt.UserRole)
            for department in departments:
                if department["name"] == itemData["name"]:
                    item.setSelected(True)
                    item.setData(Qt.UserRole, department)
                    name = department["name"]
                    if department["tasks"]:
                        name += " (%s)" % (", ".join(department["tasks"]))

                    item.setText(name)

        self.onDepartmentSelectionChanged()

    @err_catcher(name=__name__)
    def refreshDepartments(self) -> None:
        """Refresh the departments list from project configuration."""
        self.lw_departments.clear()
        if self.entity == "asset":
            departments = self.core.projects.getAssetDepartments()
        else:
            departments = self.core.projects.getShotDepartments()

        for department in departments:
            item = QListWidgetItem(department["name"])
            data = {"name": department["name"], "tasks": []}
            item.setData(Qt.UserRole, data)
            self.lw_departments.addItem(item)

    @err_catcher(name=__name__)
    def createClicked(self) -> None:
        """Handle when create/save button is clicked.
        
        Validates input and creates or updates the task preset.
        """
        name = self.getName()
        departments = self.getDepartments()

        if not name:
            self.core.popup("Please specify a preset name.")
            return

        if self.bb_main.buttons()[0].text() == "Create":
            preset = self.core.projects.addTaskPreset(
                entity=self.entity,
                name=name,
                departments=departments,
                configData=self.configData
            )
            self.taskPresetCreated.emit(preset)

        self.accept()


class EnterText(QDialog, EnterText_ui.Ui_dlg_EnterText):
    """Simple dialog for entering text input.
    
    A minimal dialog that displays a text entry field and standard OK/Cancel buttons.
    Uses the UI definition from EnterText_ui.
    """

    def __init__(self) -> None:
        """Initialize the EnterText dialog."""
        QDialog.__init__(self)
        self.setupUi(self)


class SetPath(QDialog, SetPath_ui.Ui_dlg_SetPath):
    """Dialog for setting a project folder path.
    
    Allows users to browse for or manually enter a folder path for storing
    local project scenefiles. Validates that a path is provided.
    
    Attributes:
        core: PrismCore instance.
        browseTitle (str): Title for the folder browse dialog.
    """

    def __init__(self, core: Any) -> None:
        """Initialize the SetPath dialog.
        
        Args:
            core: PrismCore instance.
        """
        QDialog.__init__(self)
        self.setupUi(self)
        self.core = core

        self.l_description.setText(
            """All your local scenefiles are saved in this folder.
This folder should be empty or should not exist.
The project name will NOT be appended automatically to this path.
This folder should be on your local hard drive and don't need to be synrchonized to any server.

"""
        )

        self.browseTitle = "Select Project Folder"
        self.connectEvents()

    def connectEvents(self) -> None:
        """Connect widget signals to their handler methods."""
        self.b_browse.clicked.connect(self.browse)
        self.e_path.textChanged.connect(self.enableOk)

    def enableOk(self, text: str) -> None:
        """Enable/disable OK button based on whether path is provided.
        
        Args:
            text: Current path text.
        """
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(text != "")

    def browse(self) -> None:
        """Open a folder browser dialog to select the project path."""
        path = QFileDialog.getExistingDirectory(
            self.core.messageParent, self.browseTitle, self.e_path.text()
        )
        if path != "":
            self.e_path.setText(path)


class SaveComment(QDialog, SaveComment_ui.Ui_dlg_SaveComment):
    """Dialog for adding a comment and preview to a scene save.
    
    Allows users to enter a description and capture or set a preview image
    when saving a scene file. Supports screen capture and clipboard paste.
    
    Attributes:
        core: PrismCore instance.
        previewDefined (bool): Whether a custom preview has been set.
    """

    def __init__(self, core: Any) -> None:
        """Initialize the SaveComment dialog.
        
        Args:
            core: PrismCore instance.
        """
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.core.parentWindow(self)
        self.previewDefined = False
        self.b_changePreview.clicked.connect(lambda checked: self.grabArea())
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.setEmptyPreview()
        self.core.callback(name="onSaveExtendedOpen", args=[self])
        self.resize(0, self.geometry().size().height())

    def enterEvent(self, event: QEvent) -> None:
        """Handle mouse enter event to restore cursor.
        
        Args:
            event: Qt enter event.
        """
        QApplication.restoreOverrideCursor()

    @err_catcher(name=__name__)
    def setEmptyPreview(self) -> None:
        """Set the preview to a default 'no file' placeholder image."""
        imgFile = os.path.join(self.core.projects.getFallbackFolder(), "noFileBig.jpg")
        pmap = self.core.media.getPixmapFromPath(imgFile)
        if pmap:
            pmap = pmap.scaled(QSize(self.core.scenePreviewWidth, self.core.scenePreviewHeight))
        else:
            pmap = QPixmap(self.core.scenePreviewWidth, self.core.scenePreviewHeight)
            pmap.fill(Qt.black)

        self.l_preview.setPixmap(pmap)

    @err_catcher(name=__name__)
    def grabArea(self) -> None:
        """Capture a screen area as the preview image.
        
        Temporarily hides the dialog, allows user to select a screen area,
        then displays the captured image as the preview.
        """
        self.setWindowOpacity(0)
        from PrismUtils import ScreenShot

        previewImg = ScreenShot.grabScreenArea(self.core)
        self.setWindowOpacity(1)

        if previewImg is not None:
            self.l_preview.setPixmap(
                previewImg.scaled(
                    self.l_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
            self.previewDefined = True

    @err_catcher(name=__name__)
    def getDetails(self) -> Dict[str, Any]:
        """Get the save details including description and username.
        
        Returns:
            Dict with 'description', 'username', and callback-added keys
        """
        details = {
            "description": self.e_description.toPlainText(),
            "username": self.core.getConfig("globals", "username"),
        }
        self.core.callback(
            name="onGetSaveExtendedDetails",
            args=[self, details],
        )
        return details


class MediaPlayersWidget(QGroupBox):
    """Widget for managing external media player applications.
    
    Allows adding, removing, and configuring media players with name, path,
    and frame pattern understanding.
    
    Attributes:
        core: PrismCore instance
    """
    
    def __init__(self, origin: Any, playerData: Optional[Dict] = None) -> None:
        """Initialize MediaPlayersWidget.
        
        Args:
            origin: Parent widget with core attribute
            playerData: Player configuration dictionary. Defaults to None.
        """
        super(MediaPlayersWidget, self).__init__()
        self.core = origin.core
        self.loadLayout()
        self.connectEvents()
        if playerData:
            self.loadPlayerData(playerData)

    @err_catcher(name=__name__)
    def loadLayout(self) -> None:
        """Set up the widget layout with add button and player list area."""
        self.w_add = QWidget()
        self.b_add = QToolButton()
        self.lo_add = QHBoxLayout()
        self.w_add.setLayout(self.lo_add)
        self.lo_add.addStretch()
        self.lo_add.addWidget(self.b_add)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_add.setIcon(icon)
        self.b_add.setIconSize(QSize(20, 20))
        self.b_add.setToolTip("Add Media Player")
        if self.core.appPlugin.pluginName != "Standalone":
            self.b_add.setStyleSheet(
                "QWidget{padding: 0; border-width: 0px;background-color: transparent} QWidget:hover{border-width: 1px; }"
            )

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "reset.png"
        )
        icon = self.core.media.getColoredIcon(path)

        self.lo_player = QVBoxLayout()
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.addLayout(self.lo_player)
        self.lo_main.addWidget(self.w_add)
        self.setTitle("Media Players")

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect widget signals to their handler methods."""
        self.b_add.clicked.connect(self.addItem)

    @err_catcher(name=__name__)
    def refresh(self) -> None:
        """Refresh the player list by reloading current data."""
        data = self.getPlayerData()
        self.clearItems()
        self.loadPlayerData(data)

    @err_catcher(name=__name__)
    def loadPlayerData(self, playerData: List[Dict[str, Any]]) -> None:
        """Load player configurations into the widget.
        
        Args:
            playerData: List of player dicts with 'name', 'path', and 'understandsFramepattern' keys.
        """
        self.clearItems()
        for player in playerData:
            self.addItem(
                name=player["name"],
                path=player["path"],
                understandsFramepattern=player["understandsFramepattern"],
            )

    @err_catcher(name=__name__)
    def addItem(self, name: Optional[str] = None, path: Optional[str] = None, understandsFramepattern: Optional[bool] = None) -> Any:
        """Add a new media player item to the list.
        
        Args:
            name: Optional player name.
            path: Optional executable path.
            understandsFramepattern: Optional flag for frame pattern support.
            
        Returns:
            MediaPlayerItem: The created item widget.
        """
        item = MediaPlayerItem(self)
        item.removed.connect(self.removeItem)
        if name:
            item.setName(name)

        if path:
            item.setPath(path)

        if understandsFramepattern is not None:
            item.setUnderstandsFramepattern(understandsFramepattern)

        self.lo_player.addWidget(item)
        return item

    @err_catcher(name=__name__)
    def removeItem(self, item: QWidget) -> None:
        """Remove a player item from the list.
        
        Args:
            item: The MediaPlayerItem widget to remove.
        """
        idx = self.lo_player.indexOf(item)
        if idx != -1:
            w = self.lo_player.takeAt(idx)
            if w.widget():
                w.widget().deleteLater()

    @err_catcher(name=__name__)
    def clearItems(self) -> None:
        """Remove all player items from the list."""
        for idx in reversed(range(self.lo_player.count())):
            item = self.lo_player.takeAt(idx)
            w = item.widget()
            if w:
                w.setVisible(False)
                w.deleteLater()

    @err_catcher(name=__name__)
    def getPlayerData(self) -> List[Dict[str, Any]]:
        """Get all player configurations as a list of dicts.
        
        Returns:
            List[Dict[str, Any]]: List of player dicts with configuration data.
        """
        playerData = []
        for idx in range(self.lo_player.count()):
            w = self.lo_player.itemAt(idx)
            widget = w.widget()
            if widget:
                if isinstance(widget, MediaPlayerItem):
                    if not widget.name():
                        continue

                    sdata = {
                        "name": widget.name(),
                        "path": widget.path(),
                        "understandsFramepattern": widget.understandsFramepattern(),
                    }
                    playerData.append(sdata)

        return playerData


class MediaPlayerItem(QWidget):
    """Widget representing a single media player configuration item.
    
    Displays editable fields for media player name, executable path, and
    frame pattern support. Includes browse and remove buttons.
    
    Signals:
        removed: Emitted when the remove button is clicked. Args: (self).
    
    Attributes:
        origin: Parent MediaPlayersWidget.
        core: PrismCore instance.
        e_name (QLineEdit): Name input field.
        e_path (QLineEdit): Executable path input field.
        chb_understandsFramepattern (QCheckBox): Frame pattern support checkbox.
        b_browse (QToolButton): Browse button for selecting executable.
        b_remove (QToolButton): Remove button.
    """

    removed = Signal(object)

    def __init__(self, origin: Any) -> None:
        """Initialize the MediaPlayerItem.
        
        Args:
            origin: Parent MediaPlayersWidget instance.
        """
        super(MediaPlayerItem, self).__init__()
        self.origin = origin
        self.core = self.origin.core
        self.loadLayout()

    @err_catcher(name=__name__)
    def loadLayout(self) -> None:
        """Set up the widget layout with all input fields and buttons."""
        self.e_name = QLineEdit()
        self.e_name.setPlaceholderText("Name")
        self.e_path = QLineEdit()
        self.e_path.setPlaceholderText("Executable Path")
        # self.b_browseMediaPlayer.clicked.connect(lambda: self.browse("mediaPlayer", getFile=True))
        # self.b_browseMediaPlayer.customContextMenuRequested.connect(
        #     lambda: self.core.openFolder(self.e_mediaPlayerPath.text())
        # )
        self.b_browse = QToolButton()
        self.b_browse.setToolTip("Browse...")
        self.b_browse.clicked.connect(self.browse)
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "browse.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.b_browse.setIcon(icon)
        self.b_browse.customContextMenuRequested.connect(
            lambda: self.core.openFolder(self.e_path.text())
        )

        self.chb_understandsFramepattern = QCheckBox("Understands Framepatterns")
        self.chb_understandsFramepattern.setChecked(True)

        self.b_remove = QToolButton()
        self.b_remove.clicked.connect(lambda: self.removed.emit(self))

        self.lo_main = QHBoxLayout()
        self.lo_main.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.lo_main)
        self.lo_main.addWidget(self.e_name, 3)
        self.lo_main.addWidget(self.e_path, 10)
        self.lo_main.addWidget(self.b_browse, 0)
        self.lo_main.addWidget(self.chb_understandsFramepattern, 0)
        self.lo_main.addWidget(self.b_remove, 0)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "delete.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_remove.setIcon(icon)
        self.b_remove.setIconSize(QSize(20, 20))
        self.b_remove.setToolTip("Delete")
        if self.core.appPlugin.pluginName != "Standalone":
            self.b_remove.setStyleSheet(
                "QWidget{padding: 0; border-width: 0px;background-color: transparent} QWidget:hover{border-width: 1px; }"
            )

    @err_catcher(name=__name__)
    def browse(self) -> None:
        """Browse for media player executable file."""
        windowTitle = "Select Media Player executable"
        if platform.system() == "Windows":
            fStr = "Executable (*.exe);;All files (*)"
        else:
            fStr = "All files (*)"

        selectedPath = QFileDialog.getOpenFileName(
            self, windowTitle, self.e_path.text(), fStr
        )[0]

        if selectedPath != "":
            self.e_path.setText(self.core.fixPath(selectedPath))

    @err_catcher(name=__name__)
    def name(self) -> str:
        """Get the media player name.
        
        Returns:
            Player name
        """
        return self.e_name.text()

    @err_catcher(name=__name__)
    def setName(self, name: str) -> None:
        """Set the media player name.
        
        Args:
            name: Player name
        """
        return self.e_name.setText(name)

    @err_catcher(name=__name__)
    def path(self) -> str:
        """Get the media player executable path.
        
        Returns:
            Normalized path to player executable
        """
        return os.path.normpath(self.e_path.text())

    @err_catcher(name=__name__)
    def setPath(self, text: str) -> None:
        """Set the media player executable path.
        
        Args:
            text: Path to player executable
        """
        self.e_path.setText(text)

    @err_catcher(name=__name__)
    def understandsFramepattern(self) -> bool:
        """Check if player understands frame pattern placeholders.
        
        Returns:
            True if player can handle #### frame patterns
        """
        return self.chb_understandsFramepattern.isChecked()

    @err_catcher(name=__name__)
    def setUnderstandsFramepattern(self, understandsFramepattern: bool) -> None:
        """Set whether player understands frame patterns.
        
        Args:
            understandsFramepattern: Whether player can handle #### patterns
        """
        self.chb_understandsFramepattern.setChecked(understandsFramepattern)
