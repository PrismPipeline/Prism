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
import platform

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_3dsMax_externalAccess_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        self.core.registerCallback("getPresetScenes", self.getPresetScenes, plugin=self.plugin)

    @err_catcher(name=__name__)
    def getAutobackPath(self, origin):
        autobackpath = ""
        if self.core.appPlugin.pluginName == "3dsmax":
            autobackpath = self.executeScript(self, "getdir #autoback")
        else:
            if platform.system() == "Windows":
                autobackpath = os.path.join(
                    self.core.getWindowsDocumentsPath(), "3dsMax", "autoback"
                )

        fileStr = "3ds Max Scene File ("
        for i in self.sceneFormats:
            fileStr += "*%s " % i

        fileStr += ")"

        return autobackpath, fileStr

    @err_catcher(name=__name__)
    def getPresetScenes(self, presetScenes):
        presetDir = os.path.join(self.pluginDirectory, "Presets")
        scenes = self.core.entities.getPresetScenesFromFolder(presetDir)
        presetScenes += scenes
