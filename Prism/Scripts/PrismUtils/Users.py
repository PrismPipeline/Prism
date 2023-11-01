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
import socket

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher
from UserInterfacesPrism import ChangeUser_ui


class Users(object):
    def __init__(self, core):
        super(Users, self).__init__()
        self.core = core
        self.userReadOnly = False
        self.abbreviationReadOnly = False

    @err_catcher(name=__name__)
    def validateUser(self):
        uname = self.getUser()
        if uname is None:
            return False

        if len(uname) > 2:
            self.setUser(uname, force=True)
            return True

        return False

    @err_catcher(name=__name__)
    def changeUser(self):
        if not self.core.uiAvailable:
            self.core.popup(
                "No username is defined. Open the Prism Settings and set a username."
            )
            return

        if hasattr(self.core, "user"):
            del self.core.user

        cu = ChangeUser(core=self.core)
        result = cu.exec_()

        if result == 0:
            if self.core.appPlugin.pluginName == "Standalone":
                sys.exit()
            return
        else:
            return True

    @err_catcher(name=__name__)
    def getUserAbbreviation(self, userName=None, fromConfig=True):
        if fromConfig:
            if os.getenv("PRISM_USER_ABBREVIATION"):
                abbr = os.getenv("PRISM_USER_ABBREVIATION")
            else:
                abbr = self.core.getConfig("globals", "username_abbreviation")

            if abbr:
                return abbr

        if not userName:
            return ""

        abbrev = ""
        userName = userName.split()
        if userName:
            if len(userName) == 2 and len(userName[0]) > 0 and len(userName[1]) > 1:
                abbrev = (userName[0][0] + userName[1][:2]).lower()
            elif len(userName[0]) > 2:
                abbrev = userName[0][:3].lower()

        return abbrev

    @err_catcher(name=__name__)
    def getUser(self):
        if os.getenv("PRISM_USERNAME"):
            return os.getenv("PRISM_USERNAME")

        return self.core.getConfig("globals", "username")

    @err_catcher(name=__name__)
    def setUser(self, username, setAbbreviation=True, abbreviation=None, force=False):
        if username != self.getUser() and not os.getenv("PRISM_USERNAME"):
            self.core.setConfig("globals", "username", username)

        if setAbbreviation:
            if not abbreviation:
                abbreviation = self.getUserAbbreviation(userName=username)

            self.setUserAbbreviation(abbreviation, force=force)

        if os.getenv("PRISM_USERNAME"):
            self.setUserReadOnly(True)

        if not self.isUserReadOnly() or force:
            self.core.username = username

    @err_catcher(name=__name__)
    def setUserAbbreviation(self, abbreviation, force=False):
        if hasattr(self.core, "user") and self.core.user == abbreviation:
            return

        if os.getenv("PRISM_USER_ABBREVIATION"):
            self.setAbbreviationReadOnly(True)

        if not self.isAbbreviationReadOnly() or force:
            self.core.user = abbreviation
            if abbreviation != self.getUserAbbreviation(fromConfig=True) and not os.getenv("PRISM_USER_ABBREVIATION"):
                self.core.setConfig("globals", "username_abbreviation", abbreviation)

    @err_catcher(name=__name__)
    def ensureUser(self):
        if self.validateUser():
            return True
        else:
            dftUser = self.getDefaultUsername()
            if dftUser:
                self.setUser(dftUser)
                if self.validateUser():
                    return True

            return self.changeUser()

    @err_catcher(name=__name__)
    def getDefaultUsername(self):
        user = os.getenv("USERNAME", "")
        if not user:
            user = socket.gethostname()

        return user

    @err_catcher(name=__name__)
    def setUserEnvironmentVariable(self, key, value):
        variables = self.getUserEnvironmentVariables()
        variables[key] = value
        self.core.setConfig("environmentVariables", val=variables, config="user", updateNestedData={"exclude": "environmentVariables"})
        self.refreshEnvironment()

    @err_catcher(name=__name__)
    def getUserEnvironmentVariables(self):
        variables = self.core.getConfig("environmentVariables", config="user", dft={})
        return variables

    @err_catcher(name=__name__)
    def refreshEnvironment(self):
        variables = self.getUserEnvironmentVariables()
        envVars = []
        for key in variables:
            val = os.path.expandvars(str(variables[key]))
            res = self.core.callback(name="expandEnvVar", args=[val])
            for r in res:
                if r:
                    val = r

            if key.lower().startswith("ocio") and hasattr(self.core, "appPlugin") and self.core.appPlugin.pluginName.lower() == key.split("_")[-1]:
                key = "OCIO"

            item = {
                "key": str(key),
                "value": val,
                "orig": os.getenv(key),
            }
            envVars.append(item)
            os.environ[str(key)] = val

        self.core.callback(name="updatedEnvironmentVars", args=["refreshUser", envVars])

    @err_catcher(name=__name__)
    def isUserReadOnly(self):
        return self.userReadOnly

    @err_catcher(name=__name__)
    def setUserReadOnly(self, readOnly):
        self.userReadOnly = readOnly

    @err_catcher(name=__name__)
    def isAbbreviationReadOnly(self):
        return self.abbreviationReadOnly

    @err_catcher(name=__name__)
    def setAbbreviationReadOnly(self, readOnly):
        self.abbreviationReadOnly = readOnly


class ChangeUser(QDialog, ChangeUser_ui.Ui_dlg_ChangeUser):
    def __init__(self, core):
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.core.parentWindow(self)
        self.loadUi()
        self.connectEvents()
        self.setNames()
        self.validate()

    @err_catcher(name=__name__)
    def loadUi(self):
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "help.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        pixmap = icon.pixmap(20, 20)
        self.l_helpUser = HelpLabel(self)
        self.l_helpUser.setPixmap(pixmap)
        self.l_helpUser.setMouseTracking(True)
        msg = (
            "This username is used to identify, which scenefiles and renders you create in a project with other people.\n"
            "Typically this would be: \"Firstname Lastname\""
        )
        self.l_helpUser.msg = msg
        self.w_username.layout().addWidget(self.l_helpUser)

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.e_username.textChanged.connect(lambda x: self.validate(self.e_username))
        self.buttonBox.accepted.connect(self.setUser)

    @err_catcher(name=__name__)
    def enterEvent(self, event):
        QApplication.restoreOverrideCursor()

    @err_catcher(name=__name__)
    def setNames(self):
        uname = self.core.users.getUser() or ""
        self.e_username.setText(uname)
        self.validate()

    @err_catcher(name=__name__)
    def validate(self, editfield=None):
        if editfield:
            self.core.validateLineEdit(editfield, allowChars=[" "])

        if len(self.e_username.text()) > 2:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

    @err_catcher(name=__name__)
    def setUser(self):
        self.core.users.setUser(self.e_username.text())


class HelpLabel(QLabel):

    signalEntered = Signal(object)

    def __init__(self, parent):
        super(HelpLabel, self).__init__()
        self.parent = parent

    def enterEvent(self, event):
        self.signalEntered.emit(self)

    def mouseMoveEvent(self, event):
        QToolTip.showText(QCursor.pos(), self.msg)
