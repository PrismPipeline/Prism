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
import ast
import imp

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1

if psVersion == 1:
    from UserInterfaces import ItemList_ui
else:
    from UserInterfaces import ItemList_ui_ps2 as ItemList_ui

try:
    del sys.modules["CreateItem"]
except:
    pass

try:
    import CreateItem
except:
    modPath = imp.find_module("CreateItem")[1]
    if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
        os.remove(modPath)
    import CreateItem


class ItemList(QDialog, ItemList_ui.Ui_dlg_ItemList):
    def __init__(self, core, entity="passes"):
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.entity = entity

        self.tw_steps.setColumnCount(2)
        self.tw_steps.setHorizontalHeaderLabels(["Abbreviation", "Step"])
        self.tw_steps.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)

        if entity not in ["asset", "shot"] or (
            entity == "asset"
            and self.core.compareVersions(self.core.projectVersion, "v1.2.1.6")
            == "lower"
        ):
            self.chb_category.setVisible(False)

        if entity in ["asset", "shot"]:
            btext = u"⯈" if self.core.appPlugin.pluginName != "Standalone" else u"➤"
            b = self.buttonBox.addButton(btext, QDialogButtonBox.RejectRole)
            b.setToolTip("Create step and open category dialog")
            b.setEnabled(False)
            b.setStyleSheet("QPushButton::disabled{ color: rgb(50,50,50);} QPushButton{ color: rgb(50,150,50);}")
            self.buttonBox.clicked.connect(self.stepBbClicked)

        self.b_addStep.clicked.connect(self.addStep)
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self.tw_steps.itemSelectionChanged.connect(self.enableOk)

    def enableOk(self):
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(
            len(self.tw_steps.selectedItems()) > 0
        )
        if self.entity in ["asset", "shot"]:
            self.buttonBox.buttons()[-1].setEnabled(
                len([x for x in self.tw_steps.selectedItems() if x.column() == 0]) == 1
            )

    def addStep(self):
        self.newItem = CreateItem.CreateItem(core=self.core, getStep=True)
        self.core.parentWindow(self.newItem)

        result = self.newItem.exec_()
        if result == 1:
            abrName = self.newItem.e_item.text()
            stepName = self.newItem.e_stepName.text()

            rc = self.tw_steps.rowCount()
            self.tw_steps.insertRow(rc)
            abrItem = QTableWidgetItem(abrName)
            self.tw_steps.setItem(rc, 0, abrItem)
            stepItem = QTableWidgetItem(stepName)
            self.tw_steps.setItem(rc, 1, stepItem)
            self.tw_steps.selectRow(rc)

            self.saveStep(abrName, stepName)

    def saveStep(self, abrev, name):
        psteps = ast.literal_eval(
            self.core.getConfig(
                "globals", "pipeline_steps", configPath=self.core.prismIni
            )
        )
        if abrev not in psteps:
            psteps[str(abrev)] = str(name)
            self.core.setConfig(
                "globals", "pipeline_steps", str(psteps), configPath=self.core.prismIni
            )

    def stepBbClicked(self, button):
        btext = u"⯈" if self.core.appPlugin.pluginName != "Standalone" else u"➤"
        if button.text() == btext:
            if self.entity == "asset":
                tab = "ac"
            elif self.entity == "shot":
                tab = "sc"

            for i in self.tw_steps.selectedItems():
                if i.column() == 0:
                    step = i.text()

            startText = self.core.pb.getSteps().get(step, "")
            self.core.pb.createSteps(self.entity, [step], createCat=False)
            self.core.pb.createCatWin(tab, "Category", startText=startText)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return and self.entity in ["asset", "shot"]:
            self.reject()
            self.stepBbClicked(self.buttonBox.buttons()[-1])
        else:
            self.accept()
