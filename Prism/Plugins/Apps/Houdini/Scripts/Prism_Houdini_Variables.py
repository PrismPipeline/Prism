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


class Prism_Houdini_Variables(object):
    def __init__(self, core, plugin):
        self.version = "v1.3.0.0"
        self.pluginName = "Houdini"
        self.pluginType = "App"
        self.appShortName = "Hou"
        self.appType = "3d"
        self.hasQtParent = True
        self.sceneFormats = [".hip", ".hipnc", ".hiplc"]
        self.outputFormats = [
            ".bgeo",
            ".bgeo.sc",
            ".vdb",
            ".abc",
            ".fbx",
            ".obj",
            ".hda",
            "ShotCam",
            "other",
        ]
        self.appSpecificFormats = self.sceneFormats + [".bgeo", ".bgeo.sc", ".hda"]
        self.appColor = [242, 103, 34]
        self.appVersionPresets = ["18, 0, 566", "17, 5, 425"]
        self.renderPasses = {
            "houdini_arnold":
                [
                    ["direct", "DirectLight"],
                    ["indirect", "IndirectLight"],
                    ["emission", "Emission"],
                    ["diffuse", "DiffuseReflection"],
                    ["specular", "SpecularReflection"],
                    ["transmission", "SpecularTransmisson"],
                    ["sss", "SSS"],
                    ["volume", "Volume"],
                    ["albedo", "Albedo"],
                    ["direct", "Beauty"],
                    ["Z", "Depth"],
                    ["N", "Normal"],
                    ["crypto_asset", "CryptoAsset"],
                    ["crypto_object", "CryptoObject"],
                    ["crypto_material", "CryptoMaterial"],
                ],

            "houdini_mantra":
                [
                    ["Color", "Cf"],
                    ["Opacity", "Of"],
                    ["Alpha", "Af"],
                    ["Position", "P"],
                    ["Position-Z", "Pz"],
                    ["Normal", "N"],
                    ["Emission", "Ce"],
                ],

            "houdini_redshift":
                [
                    ["Cryptomatte", "cryptomatte"],
                    ["Z Depth", "Z"],
                    ["Puzzle Matte", "puzzleMatte"],
                    ["Diffuse Lighting", "diffuse"],
                    ["Reflections", "reflection"],
                    ["Refractions", "refraction"],
                    ["Global Illumination", "gi"],
                    ["Shadows", "shadows"],
                    ["Normals", "N"],
                ],

            "houdini_vray":
                [
                    ["Diffuse", "diffuse"],
                    ["Reflection", "reflection"],
                    ["Refraction", "refraction"],
                    ["Self Illumination", "illum"],
                    ["Shadow", "shadow"],
                    ["Specular", "specular"],
                    ["GI", "gi"],
                    ["SSS", "sss"],
                ],

            "houdini_3delight":
                [
                    ["Ci"],
                    ["Diffuse"],
                    ["Subsurface-scattering"],
                    ["Reflection"],
                    ["Refraction"],
                    ["Volume scattering"],
                    ["Incandescence"],
                    ["Z (depth)"],
                    ["Ci"],
                    ["Camera space position"],
                    ["Camera space normal"],
                ],
        }
        self.preferredUnit = "meter"
        self.colorButtonWithStyleSheet = True
        self.platforms = ["Windows", "Linux", "Darwin"]
