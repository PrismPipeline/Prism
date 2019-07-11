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
# Copyright (C) 2016-2019 Richard Frangenberg
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
		self.version = "v1.2.1.0"
		self.pluginName = "Houdini"
		self.pluginType = "App"
		self.appShortName = "Hou"
		self.appType = "3d"
		self.hasQtParent = True
		self.sceneFormats = [".hip", ".hipnc", ".hiplc"]
		self.outputFormats = [".bgeo", ".bgeo.sc", ".abc", ".obj", ".hda", "ShotCam", "other"]
		self.appSpecificFormats = self.sceneFormats + [".bgeo", ".bgeo.sc", ".hda"]
		self.appColor = [242,103,34]
		self.appVersionPresets = ["16, 5, 323", "16, 0, 559"]
		self.arnoldPasses = ['defaultpasses', 'houdini_mantra', str([["direct", "DirectLight"], ["indirect", "IndirectLight"], ["emission", "Emission"], ["diffuse", "DiffuseReflection"], ["specular", "SpecularReflection"], ["transmission", "SpecularTransmisson"], ["sss", "SSS"], ["volume", "Volume"], ["albedo", "Albedo"], ["direct", "Beauty"], ["Z", "Depth"], ["N", "Normal"], ["crypto_asset", "CryptoAsset"], ["crypto_object", "CryptoObject"], ["crypto_material", "CryptoMaterial"]])]
		self.mantraPasses = ['defaultpasses', 'houdini_mantra', str([["Color", "Cf"], ["Opacity", "Of"], ["Alpha", "Af"], ["Position", "P"], ["Position-Z", "Pz"], ["Normal", "N"], ["Emission", "Ce"]])]
		self.redshiftPasses = ['defaultpasses', 'houdini_redshift', str([["Cryptomatte", "cryptomatte"], ["Z Depth", "Z"], ["Puzzle Matte", "puzzleMatte"], ["Diffuse Lighting", "diffuse"], ["Reflections", "reflection"], ["Refractions", "refraction"], ["Global Illumination", "gi"], ["Shadows", "shadows"], ["Normals", "N"]])]
		self.vrayPasses= ['defaultpasses', "houdini_vray", str([["Diffuse", "diffuse"], ["Reflection", "reflection"], ["Refraction", "refraction"], ["Self Illumination", "illum"], ["Shadow", "shadow"], ["Specular", "specular"], ["Lighting", "lighting"], ["GI", "gi"], ["Z-Depth", "Z"], ["SSS", "sss"], ["Normal", "N"]])]
		self.renderPasses = [self.mantraPasses, self.redshiftPasses, self.vrayPasses]
		self.preferredUnit = "meter"
		self.platforms = ["Windows", "Linux", "Darwin"]