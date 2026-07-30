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


from __future__ import annotations

import os
import sys
import socket
import platform
from typing import Optional, Dict, List, Any, Union

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher
from UserInterfacesPrism import ChangeUser_ui


class Users(object):
    """Manages user-related functionality in Prism.
    
    This class handles user identification, username/abbreviation management,
    and user-specific environment variables. It ensures each Prism user
    has a valid username and abbreviation for tracking work.
    
    Attributes:
        core: PrismCore instance
        userReadOnly (bool): Whether username is read-only
        abbreviationReadOnly (bool): Whether abbreviation is read-only
    
    Example:
        ```python
        users = Users(core)
        if users.validateUser():
            username = users.getUser()
            abbr = users.getUserAbbreviation()
        ```
    """

    def __init__(self, core: Any) -> None:
        """Initialize Users manager.
        
        Args:
            core: PrismCore instance
        """
        super(Users, self).__init__()
        self.core = core
        self.userReadOnly = False
        self.abbreviationReadOnly = False

    @err_catcher(name=__name__)
    def validateUser(self) -> bool:
        """Validate that a user is configured.
        
        Returns:
            True if user is valid (name length > 2), False otherwise
        """
        uname = self.getUser()
        if uname is None:
            return False

        if len(uname) > 2:
            self.setUser(uname, force=True)
            return True

        return False

    @err_catcher(name=__name__)
    def changeUser(self) -> Optional[bool]:
        """Open dialog to change current user.
        
        Returns:
            True if user was changed, None if cancelled or app exit
        """
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
            if getattr(self.core, "appPlugin", None) and self.core.appPlugin.pluginName == "Standalone":
                sys.exit()
            return
        else:
            return True

    @err_catcher(name=__name__)
    def getUserAbbreviation(self, userName: Optional[str] = None, fromConfig: bool = True) -> str:
        """Get user abbreviation (short form of username).
        
        Args:
            userName: Username to get abbreviation for. Defaults to None.
            fromConfig: Whether to read from config. Defaults to True.
            
        Returns:
            User abbreviation string, empty string if not found
        """
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
    def getUser(self) -> Optional[str]:
        """Get current username.
        
        Returns:
            Username string, None if not set
        """
        if os.getenv("PRISM_USERNAME"):
            return os.getenv("PRISM_USERNAME")

        return self.core.getConfig("globals", "username")

    @err_catcher(name=__name__)
    def setUser(self, username: str, setAbbreviation: bool = True, abbreviation: Optional[str] = None, force: bool = False) -> None:
        """Set the current username.
        
        Args:
            username: Full username to set
            setAbbreviation: If True, also set abbreviation
            abbreviation: Optional specific abbreviation to use
            force: If True, override read-only restrictions
        """
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
    def setUserAbbreviation(self, abbreviation: str, force: bool = False) -> None:
        """Set the user abbreviation.
        
        Args:
            abbreviation: User abbreviation/initials
            force: If True, override read-only restrictions
        """
        if hasattr(self.core, "user") and self.core.user == abbreviation:
            return

        if os.getenv("PRISM_USER_ABBREVIATION"):
            self.setAbbreviationReadOnly(True)

        if not self.isAbbreviationReadOnly() or force:
            self.core.user = abbreviation
            if abbreviation != self.getUserAbbreviation(fromConfig=True) and not os.getenv("PRISM_USER_ABBREVIATION"):
                self.core.setConfig("globals", "username_abbreviation", abbreviation)

    @err_catcher(name=__name__)
    def ensureUser(self) -> None:
        """Ensure a valid user is set, prompting if needed."""
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
    def getDefaultUsername(self) -> str:
        """Get default username from environment or system.
        
        Returns:
            Username from USERNAME env var, getpass, or hostname
        """
        user = os.getenv("USERNAME", "")
        if not user:
            if platform.system() == "Linux":
                import getpass
                user = getpass.getuser()
            else:
                user = socket.gethostname()

        return user

    @err_catcher(name=__name__)
    def setUserEnvironmentVariable(self, key: str, value: str) -> None:
        """Set a user-specific environment variable.
        
        Args:
            key: Environment variable name
            value: Environment variable value
        """
        variables = self.getUserEnvironmentVariables()
        variables[key] = value
        self.core.setConfig("environmentVariables", val=variables, config="user", updateNestedData={"exclude": "environmentVariables"})
        self.refreshEnvironment()

    @err_catcher(name=__name__)
    def getUserEnvironmentVariables(self) -> Dict[str, str]:
        """Get user-specific environment variables from config.
        
        Returns:
            Dictionary of environment variable names and values
        """
        variables = self.core.getConfig("environmentVariables", config="user", dft={})
        return variables

    @err_catcher(name=__name__)
    def getUserEnvironment(self, appPluginName: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get user environment variables with expanded values.
        
        Args:
            appPluginName: Application plugin name. Defaults to None.
            
        Returns:
            List of environment variable dictionaries
        """
        variables = self.getUserEnvironmentVariables()
        envVars = []
        if not appPluginName:
            if getattr(self.core, "appPlugin", None):
                appPluginName = self.core.appPlugin.pluginName
            else:
                appPluginName = ""

        for key in variables:
            val = os.path.expandvars(str(variables[key]))
            res = self.core.callback(name="expandEnvVar", args=[val])
            for r in res:
                if r:
                    val = r

            if key.lower().startswith("ocio") and appPluginName.lower() == key.split("_")[-1]:
                key = "OCIO"

            item = {
                "key": str(key),
                "value": val,
                "orig": os.getenv(key),
            }
            envVars.append(item)

        return envVars

    @err_catcher(name=__name__)
    def refreshEnvironment(self) -> None:
        """Refresh and apply user environment variables."""
        envVars = []
        usrVars = self.getUserEnvironment()
        for envVar in usrVars:
            envVars.append(envVar)
            os.environ[envVar["key"].strip()] = envVar["value"]

        self.core.callback(name="updatedEnvironmentVars", args=["refreshUser", envVars])

    @err_catcher(name=__name__)
    def isUserReadOnly(self) -> bool:
        """Check if username is read-only.
        
        Returns:
            True if username cannot be changed, False otherwise
        """
        return self.userReadOnly

    @err_catcher(name=__name__)
    def setUserReadOnly(self, readOnly: bool) -> None:
        """Set whether username is read-only.
        
        Args:
            readOnly: True to make read-only, False otherwise
        """
        self.userReadOnly = readOnly

    @err_catcher(name=__name__)
    def isAbbreviationReadOnly(self) -> bool:
        """Check if abbreviation is read-only.
        
        Returns:
            True if abbreviation cannot be changed, False otherwise
        """
        return self.abbreviationReadOnly

    @err_catcher(name=__name__)
    def setAbbreviationReadOnly(self, readOnly: bool) -> None:
        """Set whether abbreviation is read-only.
        
        Args:
            readOnly: True to make read-only, False otherwise
        """
        self.abbreviationReadOnly = readOnly


class ChangeUser(QDialog, ChangeUser_ui.Ui_dlg_ChangeUser):
    """Dialog for changing the current Prism user.
    
    This dialog allows users to enter a username and abbreviation,
    with validation to ensure proper formatting.
    
    Attributes:
        core: PrismCore instance
    """

    def __init__(self, core: Any) -> None:
        """Initialize ChangeUser dialog.
        
        Args:
            core: PrismCore instance
        """
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.core.parentWindow(self)
        self.loadUi()
        self.connectEvents()
        self.setNames()
        self.validate()

    @err_catcher(name=__name__)
    def loadUi(self) -> None:
        """Load CreateUser dialog UI with help icon and tooltip."""
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
    def connectEvents(self) -> None:
        """Connect UI widget signals to handler functions."""
        self.e_username.textChanged.connect(lambda x: self.validate(self.e_username))
        self.buttonBox.accepted.connect(self.setUser)

    @err_catcher(name=__name__)
    def enterEvent(self, event: Any) -> None:
        """Handle mouse enter event.
        
        Args:
            event: Qt enter event
        """
        QApplication.restoreOverrideCursor()

    @err_catcher(name=__name__)
    def setNames(self) -> None:
        """Load and display current username in UI."""
        uname = self.core.users.getUser() or ""
        self.e_username.setText(uname)
        self.validate()

    @err_catcher(name=__name__)
    def validate(self, editfield: Optional[QLineEdit] = None) -> None:
        """Validate username input.
        
        Args:
            editfield: Optional line edit widget to validate
        """
        if editfield:
            self.core.validateLineEdit(editfield, allowChars=[" "])

        if len(self.e_username.text()) > 2:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

    @err_catcher(name=__name__)
    def setUser(self) -> None:
        """Apply username from UI input."""
        self.core.users.setUser(self.e_username.text())


class HelpLabel(QLabel):

    signalEntered = Signal(object)

    def __init__(self, parent: Any) -> None:
        """Initialize help label.
        
        Args:
            parent: Parent widget
        """
        super(HelpLabel, self).__init__()
        self.parent = parent

    def enterEvent(self, event: Any) -> None:
        """Handle mouse enter event.
        
        Args:
            event: Qt enter event
        """
        self.signalEntered.emit(self)

    def mouseMoveEvent(self, event: Any) -> None:
        """Show tooltip on mouse move.
        
        Args:
            event: Qt mouse event
        """
        QToolTip.showText(QCursor.pos(), self.msg)
