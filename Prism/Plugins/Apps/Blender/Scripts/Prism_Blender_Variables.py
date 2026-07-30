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
from typing import Any, List


class Prism_Blender_Variables(object):
    """Blender plugin configuration and variables.
    
    Defines plugin metadata, supported formats, and configuration settings
    for Blender integration with Prism.
    
    Attributes:
        version (str): Plugin version number.
        pluginName (str): Display name of the plugin.
        pluginType (str): Type of plugin (App).
        appShortName (str): Short name for Blender.
        appType (str): Application type (3d).
        hasQtParent (bool): Whether app has Qt parent.
        sceneFormats (List[str]): Supported scene file formats.
        canBuildScene (bool): Whether plugin can build scenes.
        appSpecificFormats (List[str]): App-specific file formats.
        outputFormats (List[str]): Supported export formats.
        appColor (List[int]): RGB color for UI identification.
        canDeleteRenderPasses (bool): Whether render passes can be deleted.
        colorButtonWithStyleSheet (bool): Style button coloring method.
        platforms (List[str]): Supported operating systems.
        pluginDirectory (str): Path to plugin directory.
        appIcon (str): Path to application icon.
    """
    
    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize Blender plugin variables.
        
        Args:
            core: PrismCore instance.
            plugin: Plugin instance.
        """
        self.version = "v2.1.3"
        self.pluginName = "Blender"
        self.pluginType = "App"
        self.appShortName = "Bld"
        self.appType = "3d"
        self.hasQtParent = False
        self.sceneFormats = [".blend"]
        self.canBuildScene = True
        self.appSpecificFormats = self.sceneFormats
        self.outputFormats = [".abc", ".obj", ".fbx", ".glb", ".blend", "ShotCam"]
        self.appColor = [200, 180, 0]
        self.canDeleteRenderPasses = False
        self.colorButtonWithStyleSheet = True
        self.platforms = ["Windows", "Linux", "Darwin"]
        self.pluginDirectory = os.path.abspath(
            os.path.dirname(os.path.dirname(__file__))
        )
        self.appIcon = os.path.join(
            self.pluginDirectory, "UserInterfaces", "blender.ico"
        )
