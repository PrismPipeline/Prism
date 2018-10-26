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



class Prism_Houdini_Variables(object):
	def __init__(self, core, plugin):
		self.version = "v1.1.1.0"
		self.pluginName = "Houdini"
		self.pluginType = "App"
		self.appShortName = "Hou"
		self.appType = "3d"
		self.hasQtParent = True
		self.sceneFormats = [".hip", ".hipnc", ".hiplc"]
		self.appSpecificFormats = self.sceneFormats + [".bgeo"]
		self.appColor = [242,103,34]
		self.appVersionPresets = ["16, 5, 323", "16, 0, 559"]
		mantraPasses = ['defaultpasses', 'houdini_mantra', str([["Color", "Cf"], ["Opacity", "Of"], ["Alpha", "Af"], ["Position", "P"], ["Position-Z", "Pz"], ["Normal", "N"], ["Emission", "Ce"]])]
		redshiftPasses = ['defaultpasses', 'houdini_redshift', str([["Z Depth", "Z"], ["Puzzle Matte", "puzzleMatte"], ["Diffuse Lighting", "diffuse"], ["Reflections", "reflection"], ["Refractions", "refraction"], ["Global Illumination", "gi"], ["Shadows", "shadows"], ["Normals", "N"]])]
		self.renderPasses = [mantraPasses, redshiftPasses]
		self.preferredUnit = "meter"
		self.platforms = ["Windows", "Linux", "Darwin"]