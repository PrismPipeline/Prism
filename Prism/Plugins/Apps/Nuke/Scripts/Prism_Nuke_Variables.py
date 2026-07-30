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
from typing import Any


class Prism_Nuke_Variables(object):
    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize Nuke plugin variables.
        
        Sets up plugin metadata, supported file formats, and visual properties
        for Prism's Nuke integration.
        
        Args:
            core: The Prism core instance
            plugin: The plugin instance
        """
        self.version = "v2.1.3"
        self.pluginName = "Nuke"
        self.pluginType = "App"
        self.appShortName = "Nuke"
        self.appType = "2d"
        self.hasQtParent = True
        self.sceneFormats = [".nk", ".nknc", ".nkple", ".nuke", ".nkind"]
        self.appSpecificFormats = self.sceneFormats
        self.outputFormats = [".nk"]
        self.canBuildScene = True
        self.appColor = [160, 52, 66]
        self.platforms = ["Windows", "Linux", "Darwin"]
        self.pluginDirectory = os.path.abspath(
            os.path.dirname(os.path.dirname(__file__))
        )
        self.appIcon = os.path.join(self.pluginDirectory, "Resources", "NukeXApp.ico")
