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
import subprocess

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_Photoshop_externalAccess_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

    @err_catcher(name=__name__)
    def getAutobackPath(self, origin, tab):
        autobackpath = ""

        fileStr = "Photoshop Script ("
        for i in self.sceneFormats:
            fileStr += "*%s " % i

        fileStr += ")"

        return autobackpath, fileStr

    @err_catcher(name=__name__)
    def projectBrowser_loadUI(self, origin):
        if self.core.appPlugin.pluginName == "Standalone":
            psMenu = QMenu("Photoshop")
            psAction = QAction("Connect", origin)
            psAction.triggered.connect(lambda: self.connectToPhotoshop(origin))
            psMenu.addAction(psAction)
            origin.menuTools.insertSeparator(origin.menuTools.actions()[-2])
            origin.menuTools.insertMenu(origin.menuTools.actions()[-2], psMenu)

    @err_catcher(name=__name__)
    def customizeExecutable(self, origin, appPath, filepath):
        self.connectToPhotoshop(origin, filepath=filepath)
        return True

    @err_catcher(name=__name__)
    def connectToPhotoshop(self, origin, filepath=""):
        pythonPath = self.core.getPythonPath(executable="Prism Project Browser")

        menuPath = os.path.join(
            self.core.prismRoot,
            "Plugins",
            "Apps",
            "Photoshop",
            "Scripts",
            "Prism_Photoshop_MenuTools.py",
        )
        subprocess.Popen([pythonPath, menuPath, "Tools", filepath])
