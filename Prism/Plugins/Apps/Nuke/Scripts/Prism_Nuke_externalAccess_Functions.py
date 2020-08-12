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
import platform
import subprocess

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

if platform.system() == "Windows":
    if sys.version[0] == "3":
        import winreg as _winreg
    else:
        import _winreg

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_Nuke_externalAccess_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

    @err_catcher(name=__name__)
    def prismSettings_loadUI(self, origin, tab):
        origin.chb_nukeX = QCheckBox("Use NukeX instead of Nuke")
        tab.layout().addWidget(origin.chb_nukeX)

    @err_catcher(name=__name__)
    def prismSettings_saveSettings(self, origin, settings):
        if "nuke" not in settings:
            settings["nuke"] = {}

        settings["nuke"]["usenukex"] = origin.chb_nukeX.isChecked()

    @err_catcher(name=__name__)
    def prismSettings_loadSettings(self, origin, settings):
        if "nuke" in settings:
            if "usenukex" in settings["nuke"]:
                origin.chb_nukeX.setChecked(settings["nuke"]["usenukex"])

    @err_catcher(name=__name__)
    def getAutobackPath(self, origin, tab):
        autobackpath = ""

        fileStr = "Nuke Script ("
        for i in self.sceneFormats:
            fileStr += "*%s " % i

        fileStr += ")"

        return autobackpath, fileStr

    @err_catcher(name=__name__)
    def customizeExecutable(self, origin, appPath, filepath):
        fileStarted = False
        if self.core.getConfig("nuke", "usenukex"):
            if appPath == "":
                if not hasattr(self, "nukePath"):
                    self.getNukePath(origin)

                if self.nukePath is not None and os.path.exists(self.nukePath):
                    appPath = self.nukePath
                else:
                    QMessageBox.warning(
                        self.core.messageParent,
                        "Warning",
                        "Nuke executable doesn't exist:\n\n%s" % self.nukePath,
                    )

            if appPath is not None and appPath != "":
                subprocess.Popen([appPath, "--nukex", self.core.fixPath(filepath)])
                fileStarted = True

        return fileStarted

    @err_catcher(name=__name__)
    def getNukePath(self, origin):
        try:
            ext = ".nk"
            class_root = _winreg.QueryValue(_winreg.HKEY_CLASSES_ROOT, ext)

            with _winreg.OpenKey(
                _winreg.HKEY_CLASSES_ROOT, r"%s\\shell\\open\\command" % class_root
            ) as key:
                command = _winreg.QueryValueEx(key, "")[0]

            command = command.rsplit(" ", 1)[0][1:-1]

            self.nukePath = command
        except:
            self.nukePath = None
