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


class Prism_Blender_Variables(object):
    def __init__(self, core, plugin):
        self.version = "v1.3.0.0"
        self.pluginName = "Blender"
        self.pluginType = "App"
        self.appShortName = "Bld"
        self.appType = "3d"
        self.hasQtParent = False
        self.sceneFormats = [".blend"]
        self.appSpecificFormats = self.sceneFormats
        self.outputFormats = [".abc", ".obj", ".fbx", ".blend", "ShotCam"]
        self.appColor = [200, 180, 0]
        self.appVersionPresets = ["2.90"]
        self.preferredUnit = "meter"
        self.canDeleteRenderPasses = False
        self.colorButtonWithStyleSheet = True
        self.platforms = ["Windows", "Linux"]
