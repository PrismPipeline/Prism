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


class Prism_Maya_Variables(object):
    def __init__(self, core, plugin):
        self.version = "v1.3.0.0"
        self.pluginName = "Maya"
        self.pluginType = "App"
        self.appShortName = "Maya"
        self.appType = "3d"
        self.hasQtParent = True
        self.sceneFormats = [".ma", ".mb"]
        self.appSpecificFormats = self.sceneFormats
        self.outputFormats = [".abc", ".obj", ".fbx", ".ma", ".mb", "ShotCam"]
        self.appColor = [44, 121, 207]
        self.appVersionPresets = ["20180100", "201720", "201600"]
        self.renderPasses = {
            "maya_vray":
                {
                    "Background": "backgroundChannel",
                    "Caustics": "causticsChannel",
                    "Diffuse": "diffuseChannel",
                    "Extra Tex": "ExtraTexElement",
                    "GI": "giChannel",
                    "Lighting": "lightingChannel",
                    "Multi Matte": "MultiMatteElement",
                    "Normals": "normalsChannel",
                    "Reflection": "reflectChannel",
                    "Refraction": "refractChannel",
                    "SSS": "FastSSS2Channel",
                    "Self Illumination": "selfIllumChannel",
                    "Shadow": "shadowChannel",
                    "Specular": "specularChannel",
                    "Velocity": "velocityChannel",
                    "Z-depth": "zdepthChannel",
                },

            "maya_arnold":
                [
                    "N",
                    "Z",
                    "albedo",
                    "background",
                    "diffuse",
                    "direct",
                    "emission",
                    "indirect",
                    "motionvector",
                    "opacity",
                    "specular",
                    "sss",
                    "transmission",
                    "volume",
                    "shadow",
                ],

            "maya_redshift":
                [
                    "Ambient Occlusion",
                    "Background",
                    "Caustics",
                    "Depth",
                    "Diffuse Filter",
                    "Diffuse Lighting",
                    "Emission",
                    "Global Illumination",
                    "Matte",
                    "Motion Vectors",
                    "Normals",
                    "Puzzle Matte",
                    "Reflections",
                    "Refractions",
                    "Shadows",
                    "Specular Lighting",
                    "Volume Lighting",
                    "World Position",
                ],
        }
        self.preferredUnit = "centimeter"
        self.platforms = ["Windows", "Linux", "Darwin"]
        self.playblastSettings = {
            "imageFormat": 8,
            "filmFit": 1,
            "displayFilmGate": False,
            "displayResolution": False,
            "overscan": 1.0,
        }
