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
from typing import Any, List, Dict


class Prism_3dsMax_Variables(object):
    """Variables and configuration for 3ds Max plugin.
    
    Defines plugin metadata, supported formats, render passes, and basic
    configuration for 3ds Max integration with Prism.
    
    Attributes:
        version (str): Plugin version
        pluginName (str): Display name of the plugin
        pluginType (str): Type of plugin (App)
        appShortName (str): Short name for the application
        appType (str): Application type (3d)
        hasQtParent (bool): Whether app has Qt parent window
        sceneFormats (List[str]): Supported scene file formats
        appSpecificFormats (List[str]): App-specific file formats
        outputFormats (List[str]): Supported export formats
        appColor (List[int]): RGB color for UI elements
        renderPasses (Dict): Available render passes per renderer
        shotcamFormat (str): Format for shot camera export
        platforms (List[str]): Supported operating systems
        pluginDirectory (str): Path to plugin directory
        appIcon (str): Path to application icon
    """

    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize 3ds Max plugin variables.
        
        Args:
            core: PrismCore instance.
            plugin: Plugin instance.
        """
        self.version = "v2.1.3"
        self.pluginName = "3dsMax"
        self.pluginType = "App"
        self.appShortName = "Max"
        self.appType = "3d"
        self.hasQtParent = True
        self.sceneFormats = [".max"]
        self.appSpecificFormats = self.sceneFormats
        self.outputFormats = [".abc", ".obj", ".fbx", ".max", "ShotCam"]
        self.appColor = [0, 170, 170]
        self.renderPasses = {
            "max_scanline": [
                "diffuseRenderElement",
                "emissionRenderElement",
                "Lighting",
                "Material_ID",
                "MatteRenderElement",
                "Object_ID",
                "reflectionRenderElement",
                "refractionRenderElement",
                "Self_Illumination",
                "ShadowRenderElement",
                "specularRenderElement",
                "velocity",
                "ZRenderElement",
            ],
            "max_vray": [
                "MultiMatteElement",
                "VRayCaustics",
                "VRayExtraTex",
                "VRayGlobalIllumination",
                "VRayLighting",
                "VRayLightSelect",
                "VRayNormals",
                "VRayReflection",
                "VRayRefraction",
                "VRaySelfIllumination",
                "VRayShadows",
                "VRaySpecular",
                "VRayVelocity",
                "VRayZDepth",
            ],
        }
        self.shotcamFormat = ".fbx"
        self.platforms = ["Windows"]
        self.pluginDirectory = os.path.abspath(
            os.path.dirname(os.path.dirname(__file__))
        )
        self.appIcon = os.path.join(self.pluginDirectory, "Resources", "max.ico")
