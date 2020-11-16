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


class Prism_Nuke_Variables(object):
    def __init__(self, core, plugin):
        self.version = "v1.3.0.0"
        self.pluginName = "Nuke"
        self.pluginType = "App"
        self.appShortName = "Nuke"
        self.appType = "2d"
        self.hasQtParent = True
        self.sceneFormats = [".nk", ".nknc", ".nkple", ".nuke", ".nkind"]
        self.appSpecificFormats = self.sceneFormats
        self.appColor = [160, 52, 66]
        self.appVersionPresets = ["11.0v1", "10.5v2"]
        self.platforms = ["Windows", "Linux", "Darwin"]
