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



import sys, os, bpy, platform
from bpy.app.handlers import persistent
from configparser import ConfigParser


@persistent
def saveRender(scene):
	userConfig = ConfigParser()
	configPath = os.path.join(os.environ["userprofile"], "Documents", "Prism", "Prism.ini")
	userConfig.read(configPath)

	saveActive = userConfig.has_option('blender', "autosaverender") and userConfig.getboolean('blender', "autosaverender")
	if not saveActive:
		return

	if "PrismIsRendering" in bpy.context.scene and bpy.context.scene["PrismIsRendering"]:
		return

	if userConfig.has_option('blender', "autosaveperproject") and userConfig.getboolean('blender', "autosaveperproject"):
		if not (userConfig.has_option('globals', "current project") and os.path.exists(userConfig.get('globals', "current project"))):
			return

		prjConfig = ConfigParser()
		prjConfig.read(userConfig.get('globals', "current project"))

		if not prjConfig.has_option('globals', "project_name"): 
			return

		prjName = prjConfig.get('globals', "project_name")

		if not userConfig.has_option('blender', "autosavepath_%s" % prjName): 
			return

		savePath = userConfig.get('blender', "autosavepath_%s" % prjName)

	elif userConfig.has_option('blender', "autosavepath"):
		savePath = userConfig.get('blender', "autosavepath")
	else:
		return

	if not os.path.exists(savePath):
		try:
			os.makedirs(savePath)
		except:
			return

	if not os.path.exists(savePath):
		return

	fileName = os.path.splitext(os.path.basename(bpy.data.filepath))[0]

	renderFiles = [x for x in os.listdir(savePath) if x.startswith(fileName) and os.path.splitext(x)[1] == ".png"]

	highversion = 0
	for i in renderFiles:
		try:
			vNum = int(i[-8:-4])
		except:
			continue

		if vNum > highversion:
			highversion = vNum
				
	fileName = os.path.join(savePath, fileName) + "{:04d}.png".format(highversion+1)

	prevFormat = scene.render.image_settings.file_format
	scene.render.image_settings.file_format = "PNG"

	rndImage = bpy.data.images['Render Result']

	if not rndImage:
		return

	rndImage.save_render(fileName)
	scene.render.image_settings.file_format = prevFormat
	

def register():
	if bpy.app.background:
		return

	bpy.app.handlers.render_post.append(saveRender)

def unregister():
	if bpy.app.background:
		return
	
	bpy.app.handlers.render_post.remove(saveRender)