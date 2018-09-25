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
# Copyright (C) 2016-2018 Richard Frangenberg
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



class Prism_3dsMax_Variables(object):
	def __init__(self, core, plugin):
		self.version = "v1.0.11.0"
		self.appName = "3dsMax"
		self.appShortName = "Max"
		self.appType = "3d"
		self.hasQtParent = True
		self.sceneFormats = [".max"]
		self.appSpecificFormats = self.sceneFormats
		self.outputFormats = [".abc", ".obj", ".fbx", ".max", "ShotCam"]
		self.appColor = [0,170,170]
		self.appVersionPresets = ["21,0,0,845", "20,4,0,4254", "19,3,533"]
		scanlinePasses = ['defaultpasses', 'max_scanline', str(["diffuseRenderElement", "emissionRenderElement", "Lighting", "Material_ID", "MatteRenderElement", "Object_ID", "reflectionRenderElement", "refractionRenderElement", "Self_Illumination", "ShadowRenderElement", "specularRenderElement", "velocity", "ZRenderElement"])]
		vrayPasses = ['defaultpasses', 'max_vray', str(["MultiMatteElement", "VRayCaustics", "VRayExtraTex", "VRayGlobalIllumination", "VRayLighting", "VRayLightSelect", "VRayNormals", "VRayReflection", "VRayRefraction", "VRaySelfIllumination", "VRayShadows", "VRaySpecular", "VRayVelocity", "VRayZDepth"])]
		self.renderPasses = [scanlinePasses, vrayPasses]
		self.shotcamFormat = ".fbx"
		self.preferredUnit = "centimeter"
		self.platforms = ["Windows"]