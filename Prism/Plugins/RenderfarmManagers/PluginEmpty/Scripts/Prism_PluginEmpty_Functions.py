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



import os, sys, traceback, time, subprocess
from functools import wraps

try:
	import hou
except:
	pass

try:
	from PySide2.QtCore import *
	from PySide2.QtGui import *
	from PySide2.QtWidgets import *
	psVersion = 2
except:
	from PySide.QtCore import *
	from PySide.QtGui import *
	psVersion = 1


class Prism_PluginEmpty_Functions(object):
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
				erStr = ("%s ERROR - Prism_Plugin_PluginEmpty - Core: %s - Plugin: %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, args[0].plugin.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def isActive(self):
		return True


	@err_decorator
	def getPluginEmptyGroups(self, subdir=None):
		return []


	@err_decorator
	def sm_dep_startup(self, origin):
		pass


	@err_decorator
	def sm_dep_updateUI(self, origin):
		pass


	@err_decorator
	def sm_dep_preExecute(self, origin):
		warnings = []

		return warnings


	@err_decorator
	def sm_dep_execute(self, origin, parent):
		pass


	@err_decorator
	def sm_houExport_startup(self, origin):
		origin.cb_dlGroup.addItems(self.getPluginEmptyGroups())


	@err_decorator
	def sm_houExport_activated(self, origin):
		origin.f_osDependencies.setVisible(False)
		origin.f_osUpload.setVisible(False)
		origin.f_osPAssets.setVisible(False)
		origin.gb_osSlaves.setVisible(False)
		origin.f_dlGroup.setVisible(True)


	@err_decorator
	def sm_houExport_preExecute(self, origin):
		warnings = []

		return warnings
		

	@err_decorator
	def sm_houRender_updateUI(self, origin):
		showGPUsettings = origin.node is not None and origin.node.type().name() == "Redshift_ROP"
		origin.w_dlGPUpt.setVisible(showGPUsettings)
		origin.w_dlGPUdevices.setVisible(showGPUsettings)


	@err_decorator
	def sm_houRender_managerChanged(self, origin):
		origin.f_osDependencies.setVisible(False)
		origin.f_osUpload.setVisible(False)

		origin.f_osPAssets.setVisible(False)
		origin.gb_osSlaves.setVisible(False)
		origin.f_dlGroup.setVisible(True)

		origin.w_dlConcurrentTasks.setVisible(True)

		showGPUsettings = origin.node is not None and origin.node.type().name() == "Redshift_ROP"
		origin.w_dlGPUpt.setVisible(showGPUsettings)
		origin.w_dlGPUdevices.setVisible(showGPUsettings)


	@err_decorator
	def sm_houRender_preExecute(self, origin):
		warnings = []

		return warnings


	@err_decorator
	def sm_render_updateUI(self, origin):
		showGPUsettings = "redshift" in self.core.appPlugin.getCurrentRenderer(origin).lower()
		origin.w_dlGPUpt.setVisible(showGPUsettings)
		origin.w_dlGPUdevices.setVisible(showGPUsettings)


	@err_decorator
	def sm_render_managerChanged(self, origin):
		origin.f_osDependencies.setVisible(False)
		origin.gb_osSlaves.setVisible(False)
		origin.f_osUpload.setVisible(False)

		origin.f_dlGroup.setVisible(True)
		origin.w_dlConcurrentTasks.setVisible(True)

		showGPUsettings = "redshift" in self.core.appPlugin.getCurrentRenderer(origin).lower()
		origin.w_dlGPUpt.setVisible(showGPUsettings)
		origin.w_dlGPUdevices.setVisible(showGPUsettings)

		getattr(self.core.appPlugin, "sm_render_managerChanged", lambda x,y: None)(origin, False)


	@err_decorator
	def sm_render_preExecute(self, origin):
		warnings = []

		return warnings


	@err_decorator
	def sm_render_submitJob(self, origin, jobOutputFile, parent):
		return "not implemented"