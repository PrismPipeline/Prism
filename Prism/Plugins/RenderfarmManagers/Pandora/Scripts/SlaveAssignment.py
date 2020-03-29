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

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "UserInterfaces")
)

try:
    del sys.modules["SlaveAssignment_ui"]
except:
    pass

if psVersion == 1:
    import SlaveAssignment_ui
else:
    import SlaveAssignment_ui_ps2 as SlaveAssignment_ui

from PrismUtils.Decorators import err_catcher as err_catcher


class SlaveAssignment(QDialog, SlaveAssignment_ui.Ui_dlg_SlaveAssignment):
    def __init__(self, core=None, curSlaves=""):
        QDialog.__init__(self)
        self.setupUi(self)

        if core is None:
            self.lw_slaves.setFocusPolicy(Qt.NoFocus)
        else:
            self.core = core
            self.core.parentWindow(self)

        self.slaveGroups = []
        self.activeGroups = []

        self.getSlaves()
        self.connectEvents()

        if curSlaves.startswith("exclude "):
            self.rb_exclude.setChecked(True)
            curSlaves = curSlaves[len("exclude ") :]

        if curSlaves == "All":
            self.rb_all.setChecked(True)
            self.lw_slaves.selectAll()
        elif curSlaves.startswith("groups: "):
            groupList = curSlaves[len("groups: ") :].split(", ")
            for i in self.slaveGroups:
                if i.text() in groupList:
                    i.setChecked(True)
            self.rb_group.setChecked(True)
        elif curSlaves != "":
            slaveList = curSlaves.split(", ")
            for i in range(self.lw_slaves.count()):
                item = self.lw_slaves.item(i)
                if item.text() in slaveList:
                    self.lw_slaves.setCurrentItem(item, QItemSelectionModel.Select)
            self.rb_custom.setChecked(True)
        else:
            self.rb_custom.setChecked(True)

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.lw_slaves.itemSelectionChanged.connect(self.selectionChanged)
        self.lw_slaves.itemDoubleClicked.connect(self.accept)
        self.rb_all.clicked.connect(lambda: self.optionChanged("all"))
        self.rb_group.clicked.connect(lambda: self.optionChanged("group"))
        self.rb_custom.clicked.connect(lambda: self.optionChanged("custom"))

    @err_catcher(name=__name__)
    def getSlaves(self):
        self.lw_slaves.clear()

        slaveData = self.core.rfManagers["Pandora"].Pandora.getSlaveData()

        gLayout = QVBoxLayout()
        self.w_slaveGroups.setLayout(gLayout)

        for i in slaveData["slaveNames"]:
            sItem = QListWidgetItem(i)
            self.lw_slaves.addItem(sItem)

        for i in slaveData["slaveGroups"]:
            chbGroup = QCheckBox(i)
            chbGroup.toggled.connect(self.groupToogled)
            gLayout.addWidget(chbGroup)
            self.slaveGroups.append(chbGroup)

    @err_catcher(name=__name__)
    def selectionChanged(self):
        if (
            len(self.lw_slaves.selectedItems()) == self.lw_slaves.count()
            and self.rb_all.isChecked()
        ):
            return

        self.rb_custom.setChecked(True)

    @err_catcher(name=__name__)
    def optionChanged(self, option):
        if option == "all":
            self.lw_slaves.selectAll()
        elif option == "group":
            self.selectGroups()

    @err_catcher(name=__name__)
    def groupToogled(self, checked=False):
        self.activeGroups = []

        for i in self.slaveGroups:
            if i.isChecked():
                self.activeGroups.append(i.text())

        if len(self.activeGroups) > 0:
            self.selectGroups()
        else:
            self.lw_slaves.clearSelection()
            self.rb_group.setChecked(True)

    @err_catcher(name=__name__)
    def selectGroups(self):
        self.lw_slaves.clearSelection()
        if len(self.activeGroups) > 0:
            for i in range(self.lw_slaves.count()):
                sGroups = self.lw_slaves.item(i).toolTip().split(", ")
                for k in self.activeGroups:
                    if k not in sGroups:
                        break
                else:
                    self.lw_slaves.setCurrentRow(i, QItemSelectionModel.Select)

        self.rb_group.setChecked(True)
