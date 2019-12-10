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
# Copyright (C) 2016-2019 Richard Frangenberg
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


import sys, os, traceback, time, platform

prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    try:
        if "standalone" in sys.argv:
            raise

        from PySide.QtCore import *
        from PySide.QtGui import *

        psVersion = 1
    except:
        sys.path.insert(0, os.path.join(prismRoot, "PythonLibs", "Python27", "PySide"))
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

from functools import wraps

from UserInterfacesPrism import qdarkstyle


class ChangeUser(QDialog, ChangeUser_ui.Ui_dlg_ChangeUser):
    def __init__(self, core):
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.core.parentWindow(self)

        self.connectEvents()

        self.setNames()

        self.validate()

    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "%s ERROR - ChangeUser %s:\n%s\n\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    args[0].core.version,
                    "".join(traceback.format_stack()),
                    traceback.format_exc(),
                )
                args[0].core.writeErrorLog(erStr)

        return func_wrapper

    @err_decorator
    def connectEvents(self):
        self.e_fname.textChanged.connect(lambda x: self.validate(x, self.e_fname))
        self.e_lname.textChanged.connect(lambda x: self.validate(x, self.e_lname))
        self.buttonBox.accepted.connect(self.setUser)
        self.e_fname.cursorPositionChanged.connect(self.cursorMoved)
        self.e_lname.cursorPositionChanged.connect(self.cursorMoved)

    @err_decorator
    def enterEvent(self, event):
        QApplication.restoreOverrideCursor()

    @err_decorator
    def setNames(self):
        if not os.path.exists(self.core.userini):
            self.core.createUserPrefs()

        try:
            uname = self.core.getConfig("globals", "username").split()

            if len(uname) == 2:
                self.e_fname.setText(uname[0])
                self.e_lname.setText(uname[1])

            self.validate()

        except Exception as e:
            pass

    @err_decorator
    def validate(self, text=None, editfield=None):
        if text != None:
            startpos = editfield.cursorPosition()

            validText = self.core.validateStr(text)

            if not text == validText:
                startpos = self.newCursorPos

            editfield.setText(validText)

            editfield.setCursorPosition(startpos)

        if len(self.e_fname.text()) > 0 and len(self.e_lname.text()) > 1:

            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

    @err_decorator
    def cursorMoved(self, old, new):
        self.newCursorPos = new

    @err_decorator
    def setUser(self):
        if not os.path.exists(self.core.userini):
            self.core.createUserPrefs()

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


def show():
    cu = ChangeUser()
    cu.show()


if __name__ == "__main__":
    qapp = QApplication(sys.argv)
    qapp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))
    appIcon = QIcon(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "UserInterfacesPrism",
            "p_tray.png",
        )
    )
    qapp.setWindowIcon(appIcon)
    import PrismCore

    pc = PrismCore.PrismCore()
    pc.openUser()
    qapp.exec_()
