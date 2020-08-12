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
import imp

from PrismUtils.Decorators import err_catcher


class Users(object):
    def __init__(self, core):
        super(Users, self).__init__()
        self.core = core

    @err_catcher(name=__name__)
    def validateUser(self):
        uname = self.core.getConfig("globals", "username")
        if uname is None:
            return False

        uname = uname.split()
        if len(uname) == 2:
            if len(uname[0]) > 0 and len(uname[1]) > 1:
                self.core.username = "%s %s" % (uname[0], uname[1])
                self.core.user = self.getUserAbbreviation(self.core.username)
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

        try:
            del sys.modules["ChangeUser"]
        except:
            pass

        try:
            import ChangeUser
        except:
            modPath = imp.find_module("ChangeUser")[1]
            if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
                os.remove(modPath)
            import ChangeUser

        cu = ChangeUser.ChangeUser(core=self.core)
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
    def ensureUser(self):
        if self.validateUser():
            return True
        else:
            return self.changeUser()
