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
import platform

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
    from UserInterfacesPrism import SetPath_ui
else:
    from UserInterfacesPrism import SetPath_ui_ps2 as SetPath_ui


class SetPath(QDialog, SetPath_ui.Ui_dlg_SetPath):
    def __init__(self, core):
        QDialog.__init__(self)
        self.setupUi(self)
        self.core = core

        if hasattr(self.core, "projectName"):
            prjName = self.core.projectName
        else:
            prjName = ""

        self.l_description.setText(
            """All your local scenefiles are saved in this folder.
This folder should be empty or should not exist.
The project name will NOT be appended automatically to this path.
This folder should be on your local hard drive and don't need to be synrchonized to any server.

"""
        )

        if platform.system() == "Windows":
            defaultLocalPath = os.path.join(
                os.getenv("USERPROFILE"), "Documents", "LocalProjects", prjName
            )
        elif platform.system() == "Linux":
            defaultLocalPath = os.path.join(
                os.path.expanduser("~"), "Documents", "LocalProjects", prjName
            )
        elif platform.system() == "Darwin":
            defaultLocalPath = os.path.join(
                os.path.expanduser("~"), "Documents", "LocalProjects", prjName
            )

        self.e_path.setText(defaultLocalPath)

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
