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
    from UserInterfaces import ExternalTask_ui
else:
    from UserInterfaces import ExternalTask_ui_ps2 as ExternalTask_ui

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2


class ExternalTask(QDialog, ExternalTask_ui.Ui_dlg_ExternalTask):
    def __init__(self, core, startText=""):
        QDialog.__init__(self)
        self.setupUi(self)
        self.core = core

        self.core.parentWindow(self)

        self.e_taskPath.setText(startText)
        self.e_versionName.setText("v0001")

        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

        self.connectEvents()

    def connectEvents(self):
        self.b_browseFolder.clicked.connect(self.browseFolder)
        self.b_browseFile.clicked.connect(self.browseFile)
        self.b_browseFolder.customContextMenuRequested.connect(self.openFolder)
        self.b_browseFile.customContextMenuRequested.connect(self.openFolder)
        self.e_taskPath.textChanged.connect(lambda x: self.enableOk(x, self.e_taskPath))
        self.e_taskName.textChanged.connect(lambda x: self.enableOk(x, self.e_taskName))
        self.e_versionName.textChanged.connect(
            lambda x: self.enableOk(x, self.e_versionName)
        )

    def browseFolder(self):
        if self.e_taskPath.text() == "":
            startpath = self.core.projectPath
        else:
            startpath = self.e_taskPath.text()

        selectedPath = QFileDialog.getExistingDirectory(
            self, "Select external folder", startpath
        )

        if selectedPath != "":
            self.e_taskPath.setText(selectedPath.replace("\\", "/"))

    def browseFile(self):
        if self.e_taskPath.text() == "":
            startpath = self.core.projectPath
        else:
            startpath = self.e_taskPath.text()

        selectedFile = QFileDialog.getOpenFileName(
            self, "Select external file", startpath
        )[0]

        if selectedFile != "":
            self.e_taskPath.setText(selectedFile.replace("\\", "/"))

    def openFolder(self):
        path = self.e_taskPath.text()
        self.core.openFolder(path)

    def enableOk(self, origText, editWidget):
        if editWidget != self.e_taskPath:
            self.core.validateLineEdit(editWidget)

        if (
            self.e_taskPath.text() != ""
            and self.e_taskName.text() != ""
            and self.e_versionName.text() != ""
        ):
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
