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
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_Fusion_externalAccess_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

    @err_catcher(name=__name__)
    def prismSettings_loadUI(self, origin, tab):
        pass

    @err_catcher(name=__name__)
    def prismSettings_saveSettings(self, origin):
        saveData = []

        return saveData

    @err_catcher(name=__name__)
    def prismSettings_loadSettings(self, origin):
        loadData = {}
        loadFunctions = {}

        return loadData, loadFunctions

    @err_catcher(name=__name__)
    def getAutobackPath(self, origin, tab):
        autobackpath = ""

        if tab == "a":
            autobackpath = os.path.join(
                origin.tw_aHierarchy.currentItem().text(1),
                "Scenefiles",
                origin.lw_aPipeline.currentItem().text(),
            )
        elif tab == "sf":
            autobackpath = os.path.join(
                origin.sBasePath,
                origin.cursShots,
                "Scenefiles",
                origin.cursStep,
                origin.cursCat,
            )

        fileStr = "Fusion Composition ("
        for i in self.sceneFormats:
            fileStr += "*%s " % i

        fileStr += ")"

        return autobackpath, fileStr
