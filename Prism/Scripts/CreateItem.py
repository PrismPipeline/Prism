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
import sys

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1

sys.path.append(os.path.join(os.path.dirname(__file__), "UserInterfacesPrism"))

if psVersion == 1:
    import CreateItem_ui
else:
    import CreateItem_ui_ps2 as CreateItem_ui

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2

from PrismUtils.Decorators import err_catcher


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
    ):
        QDialog.__init__(self)
        self.setupUi(self)
        self.core = core
        self.getStep = getStep
        self.taskType = taskType
        self.valueRequired = valueRequired
        self.mode = mode

        self.postEvents = []

        self.e_item.setText(startText)
        self.e_item.selectAll()

        if self.valueRequired and not startText:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

        self.isTaskName = showTasks

        self.allowChars = allowChars
        self.denyChars = denyChars

        if not self.allowChars and not self.denyChars:
            if self.isTaskName:
                self.allowChars = ["_"]
                if self.taskType == "Export":
                    self.denyChars = ["-"]

        if not showTasks:
            self.b_showTasks.setHidden(True)
        else:
            self.b_showTasks.setMinimumWidth(30)
            self.b_showTasks.setMinimumHeight(0)
            self.b_showTasks.setMaximumHeight(500)
            self.getTasks()

        if getStep:
            self.setWindowTitle("Create Step")
            self.l_item.setText("Abbreviation:")
            self.l_stepName = QLabel("Step Name:")
            self.e_stepName = QLineEdit()
            self.w_item.layout().addWidget(self.l_stepName)
            self.w_item.layout().addWidget(self.e_stepName)
            self.e_item.setMaximumWidth(100)
            self.resize(500 * self.core.uiScaleFactor, self.height())
            self.setTabOrder(self.e_item, self.e_stepName)

        if showType:
            for i in self.core.prjManagers.values():
                i.createAsset_open(self)
        else:
            self.w_type.setVisible(False)

        self.buttonBox.buttons()[0].setText("Create")
        self.btext = "Next"

        if self.mode in ["assetHierarchy", "assetCategory", "shotCategory"]:
            b = self.buttonBox.addButton(self.btext, QDialogButtonBox.RejectRole)
            if self.mode == "assetHierarchy":
                b.setToolTip("Create asset and open the step dialog")
            elif self.mode in ["assetCategory", "shotCategory"]:
                b.setToolTip("Create category and create a new scene from the current scene")
            if not startText:
                b.setEnabled(False)
            b.setFocusPolicy(Qt.StrongFocus)
            b.setTabOrder(b, self.buttonBox.buttons()[0])
            self.buttonBox.clicked.connect(self.bbClicked)

        self.resize(self.width(), 10)

        self.connectEvents()

    @err_catcher(name=__name__)
    def showEvent(self, event):
        if self.w_options.layout().count() == 0:
            self.w_options.setVisible(False)

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.buttonBox.accepted.connect(self.returnName)
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
        self.taskList = self.core.getTaskNames(self.taskType)

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
        for i in self.core.prjManagers.values():
            i.createAsset_typeChanged(self, state)

    @err_catcher(name=__name__)
    def enableOk(self, widget):
        text = self.core.validateLineEdit(
            widget, allowChars=self.allowChars, denyChars=self.denyChars
        )

        if self.valueRequired:
            if text != "":
                self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
            else:
                self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

        if self.mode in ["assetHierarchy", "assetCategory", "shotCategory"]:
            self.buttonBox.buttons()[-1].setEnabled(bool(text))

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
    def bbClicked(self, button):
        if button.text() == self.btext:
            if self.mode == "assetHierarchy":
                if self.rb_asset.isChecked():
                    self.postEvents.append("createCategory")
                else:
                    self.postEvents.append("createAsset")
                self.accept()
                return
            if self.mode == "assetCategory":
                tab = "ac"
            elif self.mode == "shotCategory":
                tab = "sc"

            self.core.pb.createCat(tab)
            self.reject()
            if self.core.appPlugin.pluginName != "Standalone":
                self.core.pb.createFromCurrent()
                self.core.pb.close()

    @err_catcher(name=__name__)
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            if self.mode in ["assetHierarchy", "assetCategory", "shotCategory"]:
                self.bbClicked(self.buttonBox.buttons()[-1])
            else:
                self.accept()
        elif event.key() == Qt.Key_Escape:
            self.reject()
