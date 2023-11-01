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

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher
from UserInterfacesPrism import CreateItem_ui, EnterText_ui, SetPath_ui, SaveComment_ui


class CreateItem(QDialog, CreateItem_ui.Ui_dlg_CreateItem):
    def __init__(
        self,
        startText="",
        showTasks=False,
        taskType="",
        core=None,
        getStep=False,
        showType=False,
        allowChars=[],
        denyChars=[],
        valueRequired=True,
        mode="",
        validate=True,
        presets=None,
        allowNext=False,
    ):
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

        if self.valueRequired and not startText:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

        self.isTaskName = showTasks

        self.allowChars = allowChars
        self.denyChars = denyChars

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
                self.b_next.setToolTip("Create asset and open the department dialog")

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
    def showEvent(self, event):
        if self.w_options.layout().count() == 0:
            self.w_options.setVisible(False)

    @err_catcher(name=__name__)
    def connectEvents(self):
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
    def getTasks(self):
        self.taskList = sorted(self.core.getTaskNames(self.taskType))

        if len(self.taskList) == 0:
            self.b_showTasks.setHidden(True)
        else:
            if "_ShotCam" in self.taskList:
                self.taskList.remove("_ShotCam")

    @err_catcher(name=__name__)
    def showTasks(self):
        tmenu = QMenu(self)

        for i in self.taskList:
            tAct = QAction(i, self)
            tAct.triggered.connect(lambda x=None, t=i: self.taskClicked(t))
            tmenu.addAction(tAct)

        tmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def taskClicked(self, task):
        self.e_item.setText(task)
        self.enableOk(self.e_item)

    @err_catcher(name=__name__)
    def typeChanged(self, state):
        self.core.callback(name="onCreateAssetDlgTypeChanged", args=[self, state])

    @err_catcher(name=__name__)
    def enableOk(self, widget):
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
    def enableOkStep(self, widget):
        self.core.validateLineEdit(widget)

        if self.valueRequired:
            if self.e_item.text() != "" and self.e_stepName.text() != "":
                self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
            else:
                self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

    @err_catcher(name=__name__)
    def returnName(self):
        self.itemName = self.e_item.text()

    @err_catcher(name=__name__)
    def buttonboxClicked(self, button):
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
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            if self.b_next:
                self.buttonboxClicked(self.b_next)
            else:
                if self.buttonBox.button(QDialogButtonBox.Ok).isEnabled():
                    self.accept()

        elif event.key() == Qt.Key_Escape:
            self.reject()


class CreateDepartmentDlg(QDialog):

    departmentCreated = Signal(object)

    def __init__(self, core, entity=None, configData=None, department=None, parent=None):
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
    def setupUi(self):
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
    def getEntity(self):
        if self.entity:
            return self.entity

        return self.cb_entity.currentText().lower()

    @err_catcher(name=__name__)
    def setEntity(self, entity):
        idx = self.cb_entity.findItems(entity, (Qt.MatchExactly & Qt.MatchCaseSensitive))
        if len(idx) != -1:
            self.cb_entity.setCurrentIndex(idx)

    @err_catcher(name=__name__)
    def getName(self):
        return self.e_name.text()

    @err_catcher(name=__name__)
    def setName(self, name):
        self.e_name.setText(name)

    @err_catcher(name=__name__)
    def getAbbreviation(self):
        return self.e_abbreviation.text()

    @err_catcher(name=__name__)
    def setAbbreviation(self, abbreviation):
        self.e_abbreviation.setText(abbreviation)

    @err_catcher(name=__name__)
    def getDefaultTasks(self):
        taskStr = self.te_defaultTasks.toPlainText()
        tasks = [t.strip(" ,") for t in taskStr.split("\n") if t.strip(" ,")]
        return tasks

    @err_catcher(name=__name__)
    def setDefaultTasks(self, tasks):
        taskStr = "\n".join(tasks)
        self.te_defaultTasks.setPlainText(taskStr)

    @err_catcher(name=__name__)
    def getDepartment(self):
        name = self.getName()
        abbreviation = self.getAbbreviation()
        defaultTasks = self.getDefaultTasks()
        department = {"name": name, "abbreviation": abbreviation, "defaultTasks": defaultTasks}
        return department

    @err_catcher(name=__name__)
    def createClicked(self):
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


class EnterText(QDialog, EnterText_ui.Ui_dlg_EnterText):
    def __init__(self):
        QDialog.__init__(self)
        self.setupUi(self)


class SetPath(QDialog, SetPath_ui.Ui_dlg_SetPath):
    def __init__(self, core):
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

    def connectEvents(self):
        self.b_browse.clicked.connect(self.browse)
        self.e_path.textChanged.connect(self.enableOk)

    def enableOk(self, text):
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(text != "")

    def browse(self):
        path = QFileDialog.getExistingDirectory(
            self.core.messageParent, self.browseTitle, self.e_path.text()
        )
        if path != "":
            self.e_path.setText(path)


class SaveComment(QDialog, SaveComment_ui.Ui_dlg_SaveComment):
    def __init__(self, core):
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

    def enterEvent(self, event):
        QApplication.restoreOverrideCursor()

    @err_catcher(name=__name__)
    def setEmptyPreview(self):
        imgFile = os.path.join(self.core.projects.getFallbackFolder(), "noFileBig.jpg")
        pmap = self.core.media.getPixmapFromPath(imgFile)
        pmap = pmap.scaled(QSize(self.core.scenePreviewWidth, self.core.scenePreviewHeight))
        self.l_preview.setPixmap(pmap)

    @err_catcher(name=__name__)
    def grabArea(self):
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
    def getDetails(self):
        details = {
            "description": self.e_description.toPlainText(),
            "username": self.core.getConfig("globals", "username"),
        }
        self.core.callback(
            name="onGetSaveExtendedDetails",
            args=[self, details],
        )
        return details
