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



import sys, traceback, time
from functools import wraps


class Prism_Standalone_Functions(object):
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
				erStr = ("%s ERROR - Prism_Plugin_Standalone %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].plugin.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def startup(self, origin):
		return False


	@err_decorator
	def onProjectChanged(self, origin):
		pass

	
	@err_decorator
	def getCurrentFileName(self, origin, path=True):
		return ""


	@err_decorator
	def onProjectBrowserStartup(self, origin):
		origin.loadOiio()

		origin.closeParm = "closeafterloadsa"
		origin.actionStateManager.setEnabled(False)


	@err_decorator
	def projectBrowserLoadLayout(self, origin):
		pass


	@err_decorator
	def setRCStyle(self, origin, rcmenu):
		pass


	@err_decorator
	def openScene(self, origin, filepath):
		return False


	@err_decorator
	def correctExt(self, origin, lfilepath):
		return lfilepath


	@err_decorator
	def saveScene(self, origin, filepath, underscore=True):
		return


	@err_decorator
	def setSaveColor(self, origin, btn):
		btn.setPalette(origin.savedPalette)


	@err_decorator
	def clearSaveColor(self, origin, btn):
		btn.setPalette(origin.oldPalette)


	@err_decorator
	def setProject_loading(self, origin):
		pass


	@err_decorator
	def onPrismSettingsOpen(self, origin):
		pass


	@err_decorator
	def createProject_startup(self, origin):
		pass


	@err_decorator
	def editShot_startup(self, origin):
		origin.loadOiio()


	@err_decorator
	def shotgunPublish_startup(self, origin):
		pass