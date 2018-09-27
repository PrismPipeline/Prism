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



import os, sys
import traceback, time, platform, shutil
from functools import wraps

class Prism_Maya_externalAccess_Functions(object):
	def __init__(self, core, plugin):
		self.core = core
		self.plugin = plugin


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			exc_info = sys.exc_info()
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - Prism_Plugin_Maya_ext %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].plugin.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def prismSettings_loadUI(self, origin, tab):
		pass


	@err_decorator
	def prismSettings_saveSettings(self, origin):
		pass

	
	@err_decorator
	def prismSettings_loadSettings(self, origin):
		pass


	@err_decorator
	def getAutobackPath(self, origin, tab):
		if self.core.plugin.appName == "Maya":
			autobackpath = self.executeScript(origin, "cmds.autoSave( q=True, destinationFolder=True )")
		else:
			if platform.system() == "Windows":
				autobackpath = os.path.join(os.getenv('USERPROFILE'), "Documents", "maya", "projects", "default", "autosave")
			else:
				if tab == "a":
					autobackpath = os.path.join(origin.tw_aHierarchy.currentItem().text(1), "Scenefiles", "step_" + origin.lw_aPipeline.currentItem().text())
				elif tab == "sf":
					autobackpath = os.path.join(origin.sBasePath, origin.cursShots, "Scenefiles", origin.cursStep, origin.cursCat)


		fileStr = "Maya Scene File ("
		for i in self.sceneFormats:
			fileStr += "*%s " % i

		fileStr += ")"

		return autobackpath, fileStr


	@err_decorator
	def copySceneFile(self, origin, origFile, targetPath):
		xgenfiles = [x for x in os.listdir(os.path.dirname(origFile)) if x.startswith(os.path.splitext(os.path.basename(origFile))[0]) and os.path.splitext(x)[1] in [".xgen", "abc"]]
		for i in xgenfiles:
			curFilePath = os.path.join(os.path.dirname(origFile), i)
			tFilePath = os.path.join(os.path.dirname(targetPath), i)
			shutil.copy2(curFilePath, tFilePath)
