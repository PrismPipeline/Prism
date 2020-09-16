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
    from UserInterfacesPrism import ChangeUser_ui
else:
    from UserInterfacesPrism import ChangeUser_ui_ps2 as ChangeUser_ui

from PrismUtils.Decorators import err_catcher


class ChangeUser(QDialog, ChangeUser_ui.Ui_dlg_ChangeUser):
    def __init__(self, core):
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.core.parentWindow(self)

        self.connectEvents()

        self.setNames()

        self.validate()

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.e_fname.textChanged.connect(lambda x: self.validate(self.e_fname))
        self.e_lname.textChanged.connect(lambda x: self.validate(self.e_lname))
        self.buttonBox.accepted.connect(self.setUser)

    @err_catcher(name=__name__)
    def enterEvent(self, event):
        QApplication.restoreOverrideCursor()

    @err_catcher(name=__name__)
    def setNames(self):
        if not os.path.exists(self.core.userini):
            self.core.configs.createUserPrefs()

        try:
            uname = self.core.getConfig("globals", "username").split()

            if len(uname) == 2:
                self.e_fname.setText(uname[0])
                self.e_lname.setText(uname[1])

            self.validate()

        except Exception as e:
            pass

    @err_catcher(name=__name__)
    def validate(self, editfield=None):
        if editfield:
            self.core.validateLineEdit(editfield)

        if len(self.e_fname.text()) > 0 and len(self.e_lname.text()) > 1:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

    @err_catcher(name=__name__)
    def setUser(self):
        if not os.path.exists(self.core.userini):
            self.core.configs.createUserPrefs()

        try:
            self.core.setConfig(
                "globals", "username", (self.e_fname.text() + " " + self.e_lname.text())
            )
            self.core.user = (self.e_fname.text()[0] + self.e_lname.text()[:2]).lower()
            self.core.username = self.e_fname.text() + self.e_lname.text()
        except Exception as e:
            QMessageBox.warning(
                self, "Warning (setUser)", "Error - Setting user failed\n" + str(e)
            )
            return
