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



import sys, os, threading, shutil, time, socket, traceback, imp, platform, random, errno, stat, datetime, re

#check if python 2 or python 3 is used
if sys.version[0] == "3":
	from configparser import ConfigParser
	from io import StringIO
	pVersion = 3
else:
	from ConfigParser import ConfigParser
	from StringIO import StringIO
	pVersion = 2

prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

try:
	from PySide2.QtCore import *
	from PySide2.QtGui import *
	from PySide2.QtWidgets import *
	psVersion = 2
except:
	try:
		if "standalone" in sys.argv:
			raise
			
		from PySide.QtCore import *
		from PySide.QtGui import *
		psVersion = 1
	except:
		sys.path.insert(0, os.path.join(prismRoot, "PythonLibs", "Python27", "PySide"))
		try:
			from PySide2.QtCore import *
			from PySide2.QtGui import *
			from PySide2.QtWidgets import *
			psVersion = 2
		except:
			from PySide.QtCore import *
			from PySide.QtGui import *
			psVersion = 1

from functools import wraps
import subprocess

try:
	import EnterText
except:
	modPath = imp.find_module("EnterText")[1]
	if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
		os.remove(modPath)
	import EnterText



# Timer, which controls the autosave popup, when the autosave in the DCC is diabled
class asTimer(QObject):
	finished = Signal()

	def __init__(self, thread):
		QObject.__init__(self)
		self.thread = thread
		self.active = True

	def run(self):
		try:
			# The time interval after which the popup shows up (in minutes)
			autosaveMins = 15

			t = threading.Timer(autosaveMins*60, self.stopThread)
			t.start()

		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			erStr = ("ERROR - asTimer run:\n%s" % traceback.format_exc())
			print (erStr)

	def stopThread(self):
		if self.active:
			self.finished.emit()



# Prism core class, which holds various functions
class PrismCore():
	def __init__(self, app="Standalone", prismArgs=[]):
		self.prismIni = ""

		try:
			# set some general variables
			self.version = "v1.2.1.25"

			self.prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(__file__))).replace("\\", "/")

			if platform.system() == "Windows":
				self.userini = os.path.join(os.environ["userprofile"], "Documents", "Prism", "Prism.ini")
				self.installLocPath = os.path.join(os.environ["userprofile"], "Documents", "Prism", "InstallLocations.ini")
			elif platform.system() == "Linux":
				self.userini = os.path.join(os.environ["HOME"], "Prism", "Prism.ini")
				self.installLocPath = os.path.join(os.environ["HOME"], "Prism", "InstallLocations.ini")
			elif platform.system() == "Darwin":
				self.userini = os.path.join(os.environ["HOME"], "Library", "Preferences", "Prism", "Prism.ini")
				self.installLocPath = os.path.join(os.environ["HOME"], "Library", "Preferences", "Prism", "InstallLocations.ini")

			self.pluginPathApp = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, "Plugins", "Apps"))
			self.pluginPathCustom = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, "Plugins", "Custom"))
			self.pluginPathPrjMng = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, "Plugins", "ProjectManagers"))
			self.pluginPathRFMng = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, "Plugins", "RenderfarmManagers"))
			self.pluginDirs = [self.pluginPathApp, self.pluginPathCustom, self.pluginPathPrjMng, self.pluginPathRFMng]
			prjScriptPath = os.path.abspath(os.path.join(__file__, os.pardir, "ProjectScripts"))
			for i in self.pluginDirs:
				sys.path.append(i)
			sys.path.append(prjScriptPath)

			self.prismArgs = prismArgs
			if "silent" in sys.argv:
				self.prismArgs.append("silent")

			self.uiAvailable = False if "noUI" in self.prismArgs else True

			self.stateData = []
			self.prjHDAs = []
			self.uiScaleFactor = 1

			self.smCallbacksRegistered = False
			self.sceneOpenChecksEnabled = True
			self.parentWindows = True
			self.filenameSeparator = "_"
			self.sequenceSeparator = "-"
			self.separateOutputVersionStack = True

			# delete old paths from the path variable
			for val in sys.path:
				if "00_Pipeline" in val:
					sys.path.remove(val)

			# add the custom python libraries to the path variable, so they can be imported
			if pVersion == 2:
				pyLibs = os.path.join(self.prismRoot, "PythonLibs", "Python27")
			else:
				if sys.version_info[1] == 5:
					libFolder = "Python35"
				elif sys.version_info[1] == 7:
					libFolder = "Python37"
				pyLibs = os.path.join(self.prismRoot, "PythonLibs", "Python3")
				pyLibs = os.path.join(self.prismRoot, "PythonLibs", libFolder)
				QCoreApplication.addLibraryPath(os.path.join(self.prismRoot, "PythonLibs", libFolder, "PySide2", "plugins"))
				
			cpLibs = os.path.join(self.prismRoot, "PythonLibs", "CrossPlatform")
			win32Libs = os.path.join(cpLibs, "win32")

			if cpLibs not in sys.path:
				sys.path.append(cpLibs)

			if pyLibs not in sys.path:
				sys.path.append(pyLibs)

			if win32Libs not in sys.path:
				sys.path.append(win32Libs)

			# if no user ini exists, it will be created with default values
			if not os.path.exists(self.userini):
				self.createUserPrefs()

			self.useOnTop = self.getConfig("globals", "use_always_on_top", ptype="bool")
			if self.useOnTop is None:
				self.useOnTop = True

			if sys.argv[-1] == "setupStartMenu":
				self.prismArgs.pop(self.prismArgs.index("loadProject"))

			self.getUIscale()
			self.updatePlugins(app)

			if sys.argv[-1] == "setupStartMenu":
				self.setupStartMenu()
				sys.exit()

		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			erStr = ("%s ERROR - PrismCore init %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), self.version, ''.join(traceback.format_stack()), traceback.format_exc()))
			self.writeErrorLog(erStr)


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - PrismCore %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def updatePlugins(self, current=None, pluginLocation=None, startup=True):
		appPlugins = []
		customPlugins = []
		rfManagers = []
		prjManagers = []
	
		if pluginLocation is None:
			self.unloadedAppPlugins = {}
			self.customPlugins = {}
			self.rfManagers = {}
			self.prjManagers = {}

			pluginPath = os.path.join(self.pluginPathApp, current, "Scripts")
			sys.path.append(pluginPath)
			self.appPlugin = getattr(__import__("Prism_%s_init" % current), "Prism_Plugin_%s" % current)(self)

			if not self.appPlugin:
				QMessageBox.critical(QWidget(), "Prism Error", "Prism could not initialize correctly and may not work correctly in this session.")
				return

			self.appPlugin.location = "prismRoot"
			self.appPlugin.pluginPath = pluginPath

			pluginDirs = self.pluginDirs
		else:
			pluginDirs = [pluginLocation]

		for k in pluginDirs:
			if not os.path.exists(k):
				continue

			for i in os.listdir(k):
				if i == "PluginEmpty":
					continue

				initmodule = "Prism_%s_init" % i
				pluginPath = os.path.join(k, i, "Scripts")
				initPath = os.path.join(pluginPath, initmodule + ".py")

				if os.path.basename(k) == "Apps":
					if i == current or not (os.path.exists(initPath) or os.path.exists(initPath.replace("_init", "_init_unloaded"))):
						continue

					sys.path.append(os.path.dirname(initPath))
					pPlug = getattr(__import__("Prism_%s_init_unloaded" % (i)), "Prism_%s_unloaded" % i)(self)
				else:
					if not os.path.exists(initPath):
						continue

					sys.path.append(os.path.dirname(initPath))
					pPlug = getattr(__import__("Prism_%s_init" % (i)), "Prism_%s" % i)(self)

				if platform.system() in pPlug.platforms:
					if pluginLocation is None:
						pPlug.location = "prismRoot"
					else:
						pPlug.location = "prismProject"

					pPlug.pluginPath = pluginPath

					if pPlug.pluginType in ["App"]:
						appPlugins.append(pPlug)
					elif pPlug.pluginType in ["Custom"]:
						customPlugins.append(pPlug)
					elif pPlug.pluginType in ["RenderfarmManager"]:
						rfManagers.append(pPlug)
					elif pPlug.pluginType in ["ProjectManager"]:
						prjManagers.append(pPlug)

		for i in appPlugins:
			self.unloadedAppPlugins[i.pluginName] = i

		for i in customPlugins:
			if i.isActive():
				self.customPlugins[i.pluginName] = i

		if self.appPlugin.appType == "3d":
			for i in rfManagers:
				if i.isActive():
					self.rfManagers[i.pluginName] = i

		for i in prjManagers:
			if i.isActive():
				self.prjManagers[i.pluginName] = i

		if pluginLocation is not None:
			return

		if not startup:
			return

		if QApplication.instance() is not None:
			self.messageParent = QWidget()

		if not self.appPlugin.hasQtParent:
			self.parentWindows = False
			pyLibs = os.path.join(self.prismRoot, "PythonLibs", "Python27", "PySide")
			if pyLibs not in sys.path:
				sys.path.append(pyLibs)
			if self.appPlugin.pluginName != "Standalone" and self.useOnTop:
				self.messageParent.setWindowFlags(self.messageParent.windowFlags() ^ Qt.WindowStaysOnTopHint)

		getattr(self.appPlugin, "instantStartup", lambda x:None)(self)

		if self.appPlugin.pluginName != "Standalone":
			self.maxwait = 20
			self.elapsed = 0
			if self.uiAvailable:
				self.timer = QTimer()
			result = self.startup()
			if result == False:
				self.timer.timeout.connect(self.startup)
				self.timer.start(1000)
		else:
			self.startup()


	@err_decorator
	def reloadPlugins(self):
		appPlug = self.appPlugin.pluginName

		pluginDicts = [self.unloadedAppPlugins, self.customPlugins, self.rfManagers, self.prjManagers]
		curPlugins = []
		for k in pluginDicts:
			for i in k:
				curPlugins.append([i, k])
	
		for i in curPlugins:
			self.unloadPlugin(i[0], i[1])

		self.unloadPlugin(self.appPlugin.pluginName)
		self.updatePlugins(current=appPlug, startup=False)


	@err_decorator
	def reloadCustomPlugins(self):
		for i in self.customPlugins:
			mods = ["Prism_%s_init" % i, "Prism_%s_Functions" % i, "Prism_%s_Variables" % i]
			for k in mods:
				try:
					del sys.modules[k]
				except:
					pass

			cPlug = getattr(__import__("Prism_%s_init" % i), "Prism_%s" % i)(self)
			self.customPlugins[cPlug.pluginName] = cPlug



	@err_decorator
	def unloadProjectPlugins(self):
		pluginDicts = [self.unloadedAppPlugins, self.customPlugins, self.rfManagers, self.prjManagers]
		prjPlugins = []
		for k in pluginDicts:
			for i in k:
				if k[i].location == "prismProject":
					prjPlugins.append([i, k])
	
		for i in prjPlugins:
			self.unloadPlugin(i[0], i[1])


	@err_decorator
	def unloadPlugin(self, pluginName, pluginCategory=None):
		mods = ["Prism_%s_init" % pluginName, "Prism_%s_init_unloaded" % pluginName, "Prism_%s_Functions" % pluginName, "Prism_%s_Integration" % pluginName, "Prism_%s_externalAccess_Functions" % pluginName, "Prism_%s_Variables" % pluginName]
		for k in mods:
			try:
				del sys.modules[k]
			except:
				pass

		if pluginCategory is not None:
			del pluginCategory[pluginName]

		if pluginName == self.appPlugin.pluginName:
			self.appPlugin = None


	@err_decorator
	def getPluginNames(self):
		pluginNames = list(self.unloadedAppPlugins.keys())
		pluginNames.append(self.appPlugin.pluginName)

		return sorted(pluginNames)


	@err_decorator
	def getPluginSceneFormats(self):
		pluginFormats = list(self.appPlugin.sceneFormats)

		for i in self.unloadedAppPlugins.values():
			pluginFormats += i.sceneFormats

		return pluginFormats


	@err_decorator
	def getPluginData(self, pluginName, data):
		if pluginName == self.appPlugin.pluginName:
			return getattr(self.appPlugin, data, None)
		else:
			for i in self.unloadedAppPlugins:
				if i == pluginName:
					return getattr(self.unloadedAppPlugins[i], data, None)

		return None


	@err_decorator
	def getPlugin(self, pluginName):
		if pluginName == self.appPlugin.pluginName:
			return self.appPlugin
		else:
			for i in self.unloadedAppPlugins:
				if i == pluginName:
					return self.unloadedAppPlugins[i]

		return None


	@err_decorator
	def getLoadedPlugins(self):
		appPlugs = {self.appPlugin.pluginName: self.appPlugin}
		appPlugs.update(self.unloadedAppPlugins)
		plugs = {"App": appPlugs, "Renderfarm": self.rfManagers, "Projectmanager": self.prjManagers, "Custom": self.customPlugins}
		return plugs


	@err_decorator
	def createPlugin(self, pluginName, pluginType):
		if pluginType == "App":
			presetPath = os.path.join(self.prismRoot, "Plugins", "Apps", "PluginEmpty")
		elif pluginType == "Custom":
			presetPath = os.path.join(self.prismRoot, "Plugins", "Custom", "PluginEmpty")
		elif pluginType == "Projectmanager":
			presetPath = os.path.join(self.prismRoot, "Plugins", "ProjectManagers", "PluginEmpty")
		elif pluginType == "Renderfarm":
			presetPath = os.path.join(self.prismRoot, "Plugins", "RenderfarmManagers", "PluginEmpty")

		if not os.path.exists(presetPath):
			QMessageBox.warning(self.messageParent, "Prism", "Canceled plugin creation: Empty preset doesn't exist:\n\n%s" % self.fixPath(presetPath))
			return

		targetPath = os.path.join(os.path.dirname(presetPath), pluginName)

		if os.path.exists(targetPath):
			QMessageBox.warning(self.messageParent, "Prism", "Canceled plugin creation: Plugin already exists:\n\n%s" % targetPath)
			return

		shutil.copytree(presetPath, targetPath)

		for i in os.walk(targetPath):
			for folder in i[1]:
				if "PluginEmpty" in folder:
					folderPath = os.path.join(i[0], folder)
					newFolderPath = folderPath.replace("PluginEmpty", pluginName)
					os.rename(folderPath, newFolderPath)

			for file in i[2]:
				filePath = os.path.join(i[0], file)
				with open(filePath, "r") as f:
					content = f.read()

				with open(filePath, "w") as f:
					f.write(content.replace("PluginEmpty", pluginName))

				if "PluginEmpty" in filePath:
					newFilePath = filePath.replace("PluginEmpty", pluginName)
					os.rename(filePath, newFilePath)

		scriptPath = os.path.join(targetPath, "Scripts")
		if not os.path.exists(scriptPath):
			scriptPath = targetPath

		self.openFolder(scriptPath)


	@err_decorator
	def callback(self, name="", types=["custom"], args=[], kwargs={}):
		if "curApp" in types:
			getattr(self.appPlugin, name, lambda *args, **kwargs: None)(*args, **kwargs)

		if "unloadedApps" in types:
			for i in self.unloadedAppPlugins.values():
				getattr(i, name, lambda *args, **kwargs: None)(*args, **kwargs)

		if "custom" in types:
			for i in self.customPlugins.values():
				getattr(i, name, lambda *args, **kwargs: None)(*args, **kwargs)

		if "prjManagers" in types:
			for i in self.prjManagers.values():
				getattr(i, name, lambda *args, **kwargs: None)(*args, **kwargs)

		if "rfManagers" in types:
			for i in self.rfManagers.values():
				getattr(i, name, lambda *args, **kwargs: None)(*args, **kwargs)


	@err_decorator
	def startup(self):
		if self.appPlugin.hasQtParent:
			self.elapsed += 1
			if self.elapsed > self.maxwait and hasattr(self, "timer"):
				self.timer.stop()

		result = self.appPlugin.startup(self)

		if result is not None:
			return result

		if not "silent" in self.prismArgs:
			curPrj = self.getConfig("globals", "current project")
			if (curPrj is None or curPrj == "") and self.getConfig("globals", "showonstartup", ptype="bool") != False:
				self.setProject(startup=True, openUi="projectBrowser")

		if "prism_project" in os.environ and os.path.exists(os.environ["prism_project"]):
			curPrj = os.environ["prism_project"]
		else:
			curPrj = self.getConfig("globals", "current project")

		if curPrj != "":
			self.changeProject(curPrj)
			if not "silent" in self.prismArgs and self.getConfig("globals", "showonstartup", ptype="bool") != False and self.uiAvailable:
				self.projectBrowser()

		if self.getCurrentFileName() != "":
			self.sceneOpen()

		if self.uiAvailable:
			self.autoUpdateCheck()


	@err_decorator
	def startasThread(self, quit=False):
		if hasattr(self,  "asThread") and self.asThread.isRunning():
			self.asObject.active = False
			self.asThread.quit()

		if quit:
			return

		autoSave = self.getConfig("globals", "autosave", ptype="bool")
		if autoSave is None or not autoSave:
			return

		self.asThread = QThread()
		self.asObject = asTimer(self.asThread)
		self.asObject.moveToThread(self.asThread)
		self.asThread.started.connect(self.asObject.run)
		self.asObject.finished.connect(self.checkAutoSave)
		self.asThread.start()


	@err_decorator
	def checkAutoSave(self):
		if self.appPlugin.autosaveEnabled(self):
			return

		self.autosave_msg = QMessageBox()
		self.autosave_msg.setWindowTitle("Autosave")
		self.autosave_msg.setText("Autosave is disabled. Would you like to save now?")
		self.autosave_msg.addButton("Save", QMessageBox.YesRole)
		self.autosave_msg.addButton("Save new version", QMessageBox.YesRole)
		self.autosave_msg.addButton("No", QMessageBox.YesRole)
		self.autosave_msg.addButton("No, don't ask again in this session", QMessageBox.YesRole)

		self.parentWindow(self.autosave_msg)
		self.autosave_msg.finished.connect(self.autoSaveDone)
		self.autosave_msg.setModal(False)
		action = self.autosave_msg.show()


	@err_decorator
	def autoSaveDone(self, action=2):
		saved = False
		if action == 0:
			saved = self.saveScene(prismReq=False)
		elif action == 1:
			saved = self.saveScene()
		elif action == 3:
			self.startasThread(quit=True)
			return

		if saved:
			return

		self.startasThread()


	@err_decorator
	def createUserPrefs(self):
		if os.path.exists(self.userini):
			try:
				os.remove(self.userini)
			except:
				pass

		if not os.path.exists(os.path.dirname(self.userini)):
			os.makedirs(os.path.dirname(self.userini))

		uconfig = ConfigParser()
		uconfig.add_section('globals')
		uconfig.set('globals', "current project", "")
		uconfig.set('globals', "showonstartup", "True")
		uconfig.set('globals', "check_import_versions", "True")
		uconfig.set('globals', "checkframerange", "True")
		uconfig.set('globals', "username", "")
		uconfig.set('globals', "autosave", "True")
		uconfig.set('globals', "rvpath", "")
		uconfig.set('globals', "djvpath", "")
		uconfig.set('globals', "prefer_djv", "False")
		uconfig.set('globals', "usenukex", "False")
		uconfig.add_section('browser')
		uconfig.set('browser', "closeafterload", "True")
		uconfig.set('browser', "closeafterloadsa", "False")
		uconfig.set('browser', "current", "Assets")
		uconfig.set('browser', "assetsVisible", "True")
		uconfig.set('browser', "shotsVisible", "True")
		uconfig.set('browser', "filesVisible", "False")
		uconfig.set('browser', "recentVisible", "True")
		uconfig.set('browser', "rendervisible", "True")
		uconfig.set('browser', "assetsOrder", str(0))
		uconfig.set('browser', "shotsOrder", str(1))
		uconfig.set('browser', "filesOrder", str(2))
		uconfig.set('browser', "recentOrder", str(3))
		uconfig.set('browser', "assetStep", "All")
		uconfig.set('browser', "assetFileType", "All")
		uconfig.set('browser', "shotFileType", "All")
		uconfig.set('browser', "assetSorting", str([1, Qt.DescendingOrder]))
		uconfig.set('browser', "shotSorting", str([1, Qt.DescendingOrder]))
		uconfig.set('browser', "fileSorting", str([1, Qt.DescendingOrder]))
		uconfig.set('browser', "autoplaypreview", "False")
		uconfig.set('browser', "showmaxassets", "True")
		uconfig.set('browser', "showmayaassets", "True")
		uconfig.set('browser', "showhouassets", "True")
		uconfig.set('browser', "shownukeassets", "True")
		uconfig.set('browser', "showblenderassets", "True")
		uconfig.set('browser', "showmaxshots", "True")
		uconfig.set('browser', "showmayashots", "True")
		uconfig.set('browser', "showhoushots", "True")
		uconfig.set('browser', "shownukeshots", "True")
		uconfig.set('browser', "showblendershots", "True")
		uconfig.add_section('blender')
		uconfig.set('blender', "autosaverender", "False")
		uconfig.set('blender', "autosaveperproject", "False")
		uconfig.set('blender', "autosavepath", "")

		uconfig.add_section('localfiles')
		uconfig.add_section('recent_projects')

		# write the config to the file
		try:
			with open(self.userini, 'w') as inifile:
				uconfig.write(inifile)
		except Exception as e:
			QMessageBox.warning(self.messageParent, "Warning", "Could not create the Prism preferences:\n\n%s\n\nMake sure you have required permissions to write to that folder.\n\nError:\n%s" % (self.userini, str(e)))

		if platform.system() in ["Linux", "Darwin"]:
			if os.path.exists(self.userini):
				os.chmod(self.userini, 0o777)


	@err_decorator
	def changeProject(self, inipath, openUi="", settingsTab=1):
		if inipath is None:
			return

		if os.path.isdir(inipath):
			if os.path.basename(inipath) == "00_Pipeline":
				inipath = os.path.join(inipath, "pipeline.ini")
			else:
				inipath = os.path.join(inipath, "00_Pipeline", "pipeline.ini")
			
		delModules = []

		for i in sys.path:
			if self.prismIni != "" and os.path.dirname(self.prismIni) in i:
				delModules.append(i)

		for i in delModules:
			sys.path.remove(i)

		if hasattr(self, "projectPath"):
			modulePath = os.path.join(self.projectPath, "00_Pipeline", "CustomModules", "Python")
			if modulePath in sys.path:
				sys.path.remove(modulePath)

			curModules = list(sys.modules.keys())
			for i in curModules:
				if hasattr(sys.modules[i], "__file__") and sys.modules[i].__file__ is not None and modulePath in sys.modules[i].__file__:
					del sys.modules[i]

		self.unloadProjectPlugins()

		if not os.path.exists(inipath):
			self.prismIni = ""
			self.setConfig("globals", "current project", "")
			if hasattr(self, "projectName"):
				del self.projectName
			if hasattr(self, "projectPath"):
				del self.projectPath
			if hasattr(self, "useLocalFiles"):
				del self.useLocalFiles

			self.popup("Couldn't set project. File doesn't exist: %s" % inipath)
			return

		openPb=False
		openSm =False
		openPs = False

		try:
			if hasattr(self, "pb") and self.pb.isVisible():
				self.pb.close()
				openPb = True
		except:
			pass


		if hasattr(self, "sm"):
			if self.sm.isVisible():
				openSm =True
			self.closeSM()
		try:
			if hasattr(self, "sp") and self.sp.isVisible():
				self.sp.close()
		except:
			pass

		try:
			if hasattr(self, "ps") and self.ps.isVisible():
				self.ps.close()
				openPs = True
		except:
			pass

		inipath = self.fixPath(inipath)
		self.prismIni = inipath
		self.projectPath = os.path.abspath(os.path.join(self.prismIni, os.pardir, os.pardir))
		if not self.projectPath.endswith(os.sep):
			self.projectPath += os.sep
		self.projectName = self.getConfig("globals", "project_name", configPath=self.prismIni)
		self.projectVersion = self.getConfig("globals", "prism_version", configPath=self.prismIni) or ""
		if self.getConfig("globals", "uselocalfiles", configPath=self.prismIni) is not None:
			self.useLocalFiles = eval(self.getConfig("globals", "uselocalfiles", configPath=self.prismIni))
			if self.useLocalFiles:
				if self.getConfig("localfiles", self.projectName) is not None:
					self.localProjectPath = self.getConfig("localfiles", self.projectName)
				else:
					result = self.getLocalPath()
					if not result:
						self.changeProject("")
						return

				self.localProjectPath = self.fixPath(self.localProjectPath)
				if not self.localProjectPath.endswith(os.sep):
					self.localProjectPath += os.sep
		else:
			self.useLocalFiles = False

		if inipath != self.getConfig("globals", "current project"):
			self.setConfig("globals", "current project", inipath)

		modulePath = os.path.join(self.projectPath, "00_Pipeline", "CustomModules", "Python")
		if not os.path.exists(modulePath):
			os.makedirs(modulePath)
		
		sys.path.append(modulePath)

		pluginPath = os.path.join(self.projectPath, "00_Pipeline", "Plugins")
		if os.path.exists(pluginPath):
			self.updatePlugins(pluginLocation=pluginPath)

		rSection = "recent_files_" + self.projectName

		for i in range(10):
			if self.getConfig(rSection, "recent" + "%02d" % (i+1)) is None:
				self.setConfig(rSection, "recent" + "%02d" % (i+1), "")

		sep = self.getConfig("globals", "filenameSeparator", configPath=self.prismIni)
		if not sep:
			sep = self.getConfig("globals", "filenameseperator", configPath=self.prismIni)
		if sep:
			self.filenameSeparator = self.validateStr(sep, allowChars=[self.filenameSeparator])

		ssep = self.getConfig("globals", "sequenceSeparator", configPath=self.prismIni)
		if ssep:
			self.sequenceSeparator = self.validateStr(ssep, allowChars=[self.sequenceSeparator])

		if self.filenameSeparator == self.sequenceSeparator:
			self.popup("The filenameSeparator and the sequenceSeparator are equal. This will cause problems when working with sequences. Change the project settings to fix this.")

		self.setRecentPrj(inipath)
		self.checkAppVersion()
		self.checkCommands()
		self.callback(name="onProjectChanged", types=["curApp", "custom", "prjManagers"], args=[self])

		if self.uiAvailable:
			if openPb or openUi == "projectBrowser":
				self.projectBrowser()

			if openSm or openUi == "stateManager":
				self.stateManager()

			if openPs or openUi == "prismSettings":
				self.prismSettings()
				self.ps.tw_settings.setCurrentIndex(settingsTab)


	@err_decorator
	def setRecentPrj(self, path, action="add"):
		userConfig = ConfigParser()
		userConfig.read(self.userini)

		path = self.fixPath(path)

		rProjects = []
		if userConfig.has_section("recent_projects"):
			rProjects = userConfig.options("recent_projects")

		recentProjects = []

		for i in rProjects:
			if self.getConfig('recent_projects', i) is not None:
				prjName = self.getConfig('recent_projects', i)
				if prjName != "":
					recentProjects.append(self.fixPath(prjName))

		if path in recentProjects:
			recentProjects.remove(path)
		if action == "add":
			recentProjects = [path] + recentProjects
		elif action == "remove" and path in recentProjects:
			recentProjects.remove(path)

		userConfig.remove_section("recent_projects")
		with open(self.userini, 'w') as inifile:
			userConfig.write(inifile)

		for idx, i in enumerate(recentProjects):
			self.setConfig('recent_projects', "recent" + str(idx+1), i)


	@err_decorator
	def compareVersions(self, version1, version2):
		if not version1:
			if version2:
				return "lower"
			else:
				return "equal"
		if not version2:
			return "higher"

		if version1 == version2:
			return "equal"

		if version1[0] == "v":
			version1 = version1[1:]

		if version2[0] == "v":
			version2 = version2[1:]

		version1 = str(version1).split(".")
		version1 = [int(str(x)) for x in version1]

		version2 = str(version2).split(".")
		version2 = [int(str(x)) for x in version2]

		if version1[0] < version2[0] or (version1[0] == version2[0] and version1[1] < version2[1]) or (version1[0] == version2[0] and version1[1] == version2[1] and version1[2] < version2[2]) or (version1[0] == version2[0] and version1[1] == version2[1] and version1[2] == version2[2] and version1[3] < version2[3]):
			return "lower"
		else:
			return "higher"


	@err_decorator
	def checkCommands(self):
		if not os.path.exists(self.prismIni):
			return

		if not self.validateUser():
			return

		cmdDir = os.path.join(os.path.dirname(self.prismIni), "Commands", socket.gethostname())
		if not os.path.exists(cmdDir):
			try:
				os.makedirs(cmdDir)
			except:
				return

		for i in sorted(os.listdir(cmdDir)):
			if not i.startswith("prismCmd_"):
				continue

			filePath = os.path.join(cmdDir, i)
			if os.path.isfile(filePath) and os.path.splitext(filePath)[1] == ".txt":
				with open(filePath, 'r') as comFile:
					cmdText = comFile.read()

			command = None
			try:
				command = eval(cmdText)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				QMessageBox.warning(self.messageParent, "Warning", "Could evaluate command: %s\n - %s - %s - %s" % (cmdText, str(e), exc_type, exc_tb.tb_lineno))

			self.handleCmd(command)
			os.remove(filePath)


	@err_decorator
	def handleCmd(self, command):
		if command is None or type(command) != list:
			return

		if command[0] == "deleteShot":
			shotName = command[1]

			shotPath = os.path.join(self.projectPath, self.getConfig('paths', "scenes", configPath=self.prismIni), "Shots", shotName)
			while True:
				try:
					if os.path.exists(shotPath):
						shutil.rmtree(shotPath)
					if self.useLocalFiles:
						lShotPath = shotPath.replace(self.projectPath, self.localProjectPath)
						if os.path.exists(lShotPath):
							shutil.rmtree(lShotPath)
					break
				except Exception as e:
					msg = QMessageBox(QMessageBox.Warning, "Warning", "Permission denied.\nAnother programm uses files in the shotfolder.\n\nThe shot \"%s\" could not be deleted completly.\n\n%s" % (shotName, str(e)), QMessageBox.Cancel)
					msg.addButton("Retry", QMessageBox.YesRole)
					self.parentWindow(msg)
					action = msg.exec_()

					if action != 0:
						QMessageBox.warning(self.messageParent, "Warning", "Deleting shot canceled.")
						break


		elif command[0] == "renameShot":
			curName = command[1]
			newName = command[2]

			shotFolder = os.path.join(self.projectPath, self.getConfig('paths', "scenes", configPath=self.prismIni), "Shots", curName)
			newShotFolder = os.path.join(os.path.dirname(shotFolder), newName)
			shotFolders = {shotFolder: newShotFolder}
			if self.useLocalFiles:
				lShotFolder = shotFolder.replace(self.projectPath, self.localProjectPath)
				newLShotFolder = newShotFolder.replace(self.projectPath, self.localProjectPath)
				shotFolders[lShotFolder] = newLShotFolder

			while True:
				try:
					for k in shotFolders:
						if os.path.exists(k):
							os.rename(k, shotFolders[k])

						for i in os.walk(shotFolders[k]):
							os.chdir(i[0])
							for k in i[1]:
								if curName in k:
									os.rename(k, k.replace(curName, newName))
							for k in i[2]:
								if curName in k:
									os.rename(k, k.replace(curName, newName))

					prvPath = os.path.join(os.path.dirname(self.prismIni), "Shotinfo", "%s_preview.jpg" % curName)
					if os.path.exists(prvPath):
						os.chdir(os.path.dirname(prvPath))
						os.rename( curName + "_preview.jpg", newName + "_preview.jpg")

					break

				except Exception as e:
					msg = QMessageBox(QMessageBox.Warning, "Warning", "Permission denied.\nAnother programm uses files in the shotfolder.\n\nThe shot \"%s\" could not be renamed to \"%s\" completly.\n\n%s" % (curName, newName, str(e)) , QMessageBox.Cancel)
					msg.addButton("Retry", QMessageBox.YesRole)
					self.parentWindow(msg)
					action = msg.exec_()

					if action != 0:
						QMessageBox.warning(self.messageParent, "Warning", "Renaming shot canceled.")
						break

			shotFile = os.path.join(os.path.dirname(self.prismIni), "Shotinfo", "shotInfo.ini")

			if not os.path.exists(os.path.dirname(shotFile)):
				os.makedirs(os.path.dirname(shotFile))

			if os.path.exists(shotFile):
				sconfig = ConfigParser()
				sconfig.read(shotFile)

				if sconfig.has_option("shotRanges", curName):
					sconfig.remove_option("shotRanges", curName)
			else:
				open(shotFile, 'a').close()


		else:
			QMessageBox.warning(self.messageParent, "Warning", "Unknown command: %s" % (command))


	@err_decorator
	def createCmd(self, cmd):
		if not os.path.exists(self.prismIni):
			return

		cmdDir = os.path.join(os.path.dirname(self.prismIni), "Commands")
		if not os.path.exists(cmdDir):
			try:
				os.makedirs(cmdDir)
			except:
				return

		for i in os.listdir(cmdDir):
			if i == self.username:
				self.handleCmd(cmd)
				continue

			dirPath = os.path.join(cmdDir, i)
			if not os.path.isdir(dirPath):
				continue

			cmdFile = os.path.join(dirPath, "prismCmd_0001.txt")
			curNum = 1

			while os.path.exists(cmdFile):
				curNum += 1
				cmdFile = cmdFile[:-8] + format(curNum, '04') + ".txt"

			open(cmdFile, 'a').close()
			with open(cmdFile, 'w') as cFile:
				cFile.write(str(cmd))


	@err_decorator
	def getLocalPath(self):
		try:
			import SetPath
		except:
			modPath = imp.find_module("SetPath")[1]
			if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
				os.remove(modPath)
			import SetPath

		self.pathWin = SetPath.SetPath(core=self)
		self.pathWin.setModal(True)
		self.parentWindow(self.pathWin)
		result = self.pathWin.exec_()
		self.localProjectPath = ""
		if result == 1:
			setPathResult = self.setLocalPath(self.pathWin.e_path.text())
		else:
			return False

		if not setPathResult and result == 1:
			QMessageBox.warning(self.messageParent,"Warning", "Please enter a valid path to continue.")
			self.getLocalPath()

		return True


	@err_decorator
	def setLocalPath(self, path, projectName=None):
		if projectName is None:
			projectName = self.projectName

		self.localProjectPath = path

		try:
			os.makedirs(self.localProjectPath)
		except:
			pass

		if os.path.exists(self.localProjectPath):
			self.setConfig('localfiles', projectName, self.localProjectPath)
			return True
		else:
			return False


	@err_decorator
	def getUIscale(self):
		sFactor = 1
		highdpi = self.getConfig("globals", "highdpi", ptype="bool")
		if highdpi != "" and highdpi is not None:
			if highdpi:
				if 'PySide2.QtCore' in sys.modules:
					qtVers = sys.modules['PySide2.QtCore'].__version_info__
				elif 'PySide.QtCore' in sys.modules:
					qtVers = sys.modules['PySide.QtCore'].__version_info__

				if qtVers[0] >= 5 and qtVers >= 6:
					screen_resolution = qApp.desktop().screenGeometry()
					screenWidth, screenHeight = screen_resolution.width(), screen_resolution.height()
					wFactor = screenWidth/960.0
					hFactor = screenHeight/540.0
					if abs(wFactor-1) < abs(hFactor-1):
						sFactor = wFactor
					else:
						sFactor = hFactor
				else:
					sFactor = 1
			else:
				sFactor = 1

		self.uiScaleFactor = sFactor
		return self.uiScaleFactor


	@err_decorator
	def scaleUI(self, win=None, sFactor=0):
		if sFactor == 0:
			sFactor = self.uiScaleFactor

		if sFactor != 1:
			members = [attr for attr in dir(win) if not callable(getattr(win, attr)) and not attr.startswith("__")]
			for i in members:
				if hasattr(getattr(win, i), "maximumWidth"):
					maxW = getattr(win, i).maximumWidth()
					if maxW < 100000:
						getattr(win, i).setMaximumWidth(maxW*sFactor)
				if hasattr(getattr(win, i), "minimumWidth"):
					getattr(win, i).setMinimumWidth(getattr(win, i).minimumWidth()*sFactor)

				if hasattr(getattr(win, i), "maximumHeight"):
					maxH = getattr(win, i).maximumHeight()
					if maxH < 100000:
						getattr(win, i).setMaximumHeight(maxH*sFactor)
				if hasattr(getattr(win, i), "minimumHeight"):
					getattr(win, i).setMinimumHeight(getattr(win, i).minimumHeight()*sFactor)

			if hasattr(win, "width"):
				curWidth = win.width()
				curHeight = win.height()
				win.resize(curWidth*sFactor, curHeight*sFactor)


	@err_decorator
	def parentWindow(self, win):
		self.scaleUI(win)

		if not self.appPlugin.hasQtParent:
			if self.appPlugin.pluginName != "Standalone" and self.useOnTop:
				win.setWindowFlags(win.windowFlags() ^ Qt.WindowStaysOnTopHint)
	
		if not self.parentWindows or not self.uiAvailable:
			return
			
		win.setParent(self.messageParent, Qt.Window)

		if platform.system() == "Darwin" and self.useOnTop:
			win.setWindowFlags(win.windowFlags() ^ Qt.WindowStaysOnTopHint)


	@err_decorator
	def createProject(self, name=None, path=None, settings={}):
		try:
			del sys.modules["CreateProject"]
		except:
			pass

		try:
			self.cp.close()
		except:
			pass

		try:
			import CreateProject
		except:
			modPath = imp.find_module("CreateProject")[1]
			if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
				os.remove(modPath)
			import CreateProject

		if name is not None and path is not None:
			return CreateProject.createProject(core=self, name=name, path=path, settings=settings)
		else:
			self.cp = CreateProject.CreateProject(core=self)
			self.cp.show()


	@err_decorator
	def showAbout(self):
		pVersion = ""
		if os.path.exists(self.prismIni):
			prjVersion = self.getConfig('globals', "prism_version", configPath=self.prismIni)
			if prjVersion is not None:
				pVersion = "Project: %s" % prjVersion

		msg = QMessageBox(QMessageBox.Information, "About", "Prism: %s\n%s\n\nCopyright (C) 2016-2019 Richard Frangenberg\nLicense: GNU GPL-3.0-or-later\n\ncontact@prism-pipeline.com\n\nwww.prism-pipeline.com" % (self.version, pVersion), parent=self.messageParent)
		msg.addButton("Ok", QMessageBox.YesRole)
		action = msg.exec_()


	@err_decorator
	def sendFeedback(self):
		fbDlg = EnterText.EnterText()
		fbDlg.setModal(True)
		self.parentWindow(fbDlg)
		fbDlg.setWindowTitle("Send Message")
		fbDlg.l_info.setText("Message for the developer:\nYou may want to provide contact information (e.g. e-mail) for further discussions.")
		fbDlg.buttonBox.buttons()[0].setText("Send")
		result = fbDlg.exec_()

		if result == 1:
			self.sendEmail(fbDlg.te_text.toPlainText(), subject="Prism feedback")


	def openWebsite(self, location):
		if location == "home":
			url = "https://prism-pipeline.com/"
		elif location == "tutorials":
			url = "https://prism-pipeline.com/tutorials/"
		elif location == "documentation":
			url = "https://prism-pipeline.readthedocs.io/en/latest/"
		elif location == "downloads":
			url = "https://prism-pipeline.com/downloads/"
			
		import webbrowser
		webbrowser.open(url)


	@err_decorator
	def createEntity(self, entity):
		if type(entity) != dict:
			return False

		if entity["type"][0] != "project":
			if not hasattr(self, "pb"):
				self.projectBrowser(openUi=False)

			if not hasattr(self, "pb"):
				self.popup("Could not initialize the Project Browser.")
				return False

			self.pb.scenes = self.getConfig('paths', "scenes", configPath=self.prismIni)
			self.pb.aBasePath = os.path.join(self.projectPath, self.pb.scenes, "Assets")
			self.pb.sBasePath = os.path.join(self.projectPath, self.pb.scenes, "Shots")

		if entity["type"][0] == "project":
			result = self.createProject(name=entity["name"][0], path=entity["path"][0])

		elif entity["type"][0] == "asset":
			result = self.pb.createShotFolders(fname="%s/%s" % (entity["hierarchy"][0], entity["name"][0]), ftype="asset")

		elif entity["type"][0] == "shot":
			result = self.pb.createShot(shotName="%s%s%s" % (entity["sequence"][0], self.core.sequenceSeparator, entity["name"][0]), frameRange=[entity["framerange"][0], entity["framerange"][1]])

		elif entity["type"][0] == "step":
			if "assetName" in entity:
				entityType = "asset"
				entityName = entity["assetName"][0]
			else:
				entityType = "shot"
				entityName = "%s%s%s" % (entity["sequence"][0], self.core.sequenceSeparator, entity["shotName"][0])

			result = self.pb.createStep(stepName=entity["name"][0], entity=entityType, entityName=entityName, createCat=False)

		elif entity["type"][0] == "category":
			if "assetName" in entity:
				entityType = "asset"
				entityName = entity["assetName"][0]
				basePath = "%s/%s" % (entity["hierarchy"][0], entityName)
			else:
				entityType = "shot"
				entityName = "%s%s%s" % (entity["sequence"][0], self.core.sequenceSeparator, entity["shotName"][0])
				basePath = ""

			catPath = os.path.dirname(os.path.dirname(self.generateScenePath(entity=entityType, entityName=entityName, step=entity["step"][0], category=entity["name"][0], basePath=basePath)))

			result = self.pb.createCategory(catName=entity["name"][0], path=catPath)

		elif entity["type"][0] == "scenefile":
			if "assetName" in entity:
				entityType = "asset"
				entityName = entity["assetName"][0]
			else:
				entityType = "shot"
				entityName = "%s%s%s" % (entity["sequence"][0], self.core.sequenceSeparator, entity["shotName"][0])

			result = self.pb.createEmptyScene(entity=entityType, fileName=entity["source"][0], entityName=entityName, step=entity["step"][0], category=entity["category"][0], comment=entity["comment"][0], openFile=False)
		else:
			self.popup("invalid type: " + entity["type"][0])
			return False

		return result


	@err_decorator
	def stateManager(self, stateDataPath=None, restart=False):
		if self.appPlugin.appType != "3d":
			return False

		if not os.path.exists(self.userini):
			self.createUserPrefs()

		if not os.path.exists(self.prismIni):
			curPrj = self.getConfig("globals", "current project")
			if curPrj != "" and curPrj is not None:
				QMessageBox.warning(self.messageParent,"Warning (StateManager)", "Could not find project:\n%s" % os.path.dirname(os.path.dirname(curPrj)))

			self.setProject(openUi="stateManager")
			return False

		if not self.validateUser():
			self.changeUser()


		if hasattr(self, "user") and self.projectPath != None:
			
		#	if not hasattr(self, "sm"):
			if True:
				self.closeSM()

				if self.uiAvailable:
					try:
						del sys.modules["StateManager"]
					except:
						pass

				try:
					import StateManager
				except:
					try:
						modPath = imp.find_module("StateManager")[1]
						if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
							os.remove(modPath)

						import StateManager
					except Exception as e:
						msgString = "Could not load the StateManager:\n\n%s" % str(e)
						msg = QMessageBox(QMessageBox.Warning, "Prism Error", msgString, QMessageBox.Ok)
						self.parentWindow(msg)
						action = msg.exec_()
						return

				self.sm = StateManager.StateManager(core = self, stateDataPath=stateDataPath)

			if self.uiAvailable:
				self.sm.show()
				self.sm.collapseFolders()

			self.sm.saveStatesToScene()

			if hasattr(self, "sm"):
				if self.uiAvailable:
					self.sm.activateWindow()
					self.sm.raise_()

				return self.sm


	@err_decorator
	def closeSM(self, restart=False):
		if hasattr(self, "sm"):
			self.sm.saveEnabled = False
			if self.sm.isVisible():
				self.sm.close()
			del self.sm			

			if restart:
				self.stateManager()


	@err_decorator
	def projectBrowser(self, openUi=True):
		if not os.path.exists(self.userini):
			self.createUserPrefs()
	
		if not hasattr(self, "projectPath") or self.projectPath == None or not os.path.exists(self.prismIni):
			curPrj = self.getConfig("globals", "current project")
			if curPrj != "" and curPrj is not None:
				QMessageBox.warning(self.messageParent,"Warning (ProjectBrowser)", "Could not find project:\n%s" % os.path.dirname(os.path.dirname(curPrj)))

			self.setProject(openUi="projectBrowser")
			return False

		if hasattr(self, "pb") and self.pb.isVisible():
			self.pb.close()

		if not self.validateUser():
			self.changeUser()

		if hasattr(self, "user"):
			if self.uiAvailable:
				try:
					del sys.modules["ProjectBrowser"]
				except:
					pass

			try:
				import ProjectBrowser
			except:
				try:
					modPath = imp.find_module("ProjectBrowser")[1]
					if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
						os.remove(modPath)
				
					import ProjectBrowser
				except Exception as e:
					msgString = "Could not load the ProjectBrowser:\n\n%s" % str(e)
					msg = QMessageBox(QMessageBox.Warning, "Prism Error", msgString, QMessageBox.Ok)
					self.parentWindow(msg)
					action = msg.exec_()
					return False
			
			self.pb = ProjectBrowser.ProjectBrowser(core = self)
			if openUi:
				self.pb.show()

			return True


	@err_decorator
	def dependencyViewer(self, depRoot="", modal=False):
		if hasattr(self, "dv") and self.dv.isVisible():
			self.dv.close()

		try:
			del sys.modules["DependencyViewer"]
		except:
			pass

		try:
			import DependencyViewer
		except:
			try:
				modPath = imp.find_module("DependencyViewer")[1]
				if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
					os.remove(modPath)
			
				import DependencyViewer
			except Exception as e:
				msgString = "Could not load the DependencyViewer:\n\n%s" % str(e)
				QMessageBox.warning(self.messageParent, "Prism Error", msgString)
				return False
		
		self.dv = DependencyViewer.DependencyViewer(core=self, depRoot=depRoot)
		if modal:
			self.dv.exec_()
		else:
			self.dv.show()

		return True


	@err_decorator
	def prismSettings(self, tab=0):
		if not os.path.exists(self.userini):
			self.createUserPrefs()

		if hasattr(self, "ps") and self.ps.isVisible():
			self.ps.close()

		try:
			del sys.modules["PrismSettings"]
		except:
			pass

		try:
			import PrismSettings
		except:
			modPath = imp.find_module("PrismSettings")[1]
			if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
				os.remove(modPath)
			import PrismSettings

		self.ps = PrismSettings.PrismSettings(core = self)
		self.ps.show()

		self.ps.tw_settings.setCurrentIndex(tab)

		return True


	@err_decorator
	def openInstaller(self, uninstall=False):
		if hasattr(self, "pinst") and self.pinst.isVisible():
			self.pinst.close()

		try:
			del sys.modules["PrismInstaller"]
		except:
			pass

		try:
			import PrismInstaller
		except:
			modPath = imp.find_module("PrismInstaller")[1]
			if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
				os.remove(modPath)
			import PrismInstaller

		self.pinst = PrismInstaller.PrismInstaller(core=self, uninstall=uninstall)
		if uninstall:
			sys.exit()
		else:
			self.pinst.show()


	@err_decorator
	def startTray(self):
		if hasattr(self, "PrismTray") or self.appPlugin.pluginName != "Standalone":
			return

		import PrismTray

		self.PrismTray = PrismTray.PrismTray(core=self)


	@err_decorator
	def integrationAdded(self, appName, path):
		path = self.fixPath(path)
		items = self.getConfig(configPath=self.installLocPath, cat=appName, getItems=True)
		for i in items:
			if path == self.fixPath(i[1]):
				return

		self.setConfig(configPath=self.installLocPath, cat=appName, param="%02d" % (len(items)+1), val=path)


	@err_decorator
	def integrationRemoved(self, appName, path):
		path = self.fixPath(path)
		options = self.getConfig(configPath=self.installLocPath, cat=appName, getItems=True)
		cData = []
		for i in options:
			cData.append([appName, i[0], ""])

		self.setConfig(configPath=self.installLocPath, data=cData, delete=True)

		cData = []
		for idx, i in enumerate(options):
			if self.fixPath(i[1]) == path:
				continue

			cData.append([appName, "%02d" % (idx+1), i[1]])

		self.setConfig(configPath=self.installLocPath, data=cData)


	@err_decorator
	def setupStartMenu(self):
		if self.appPlugin.pluginName == "Standalone":
			result = self.appPlugin.createWinStartMenu(self)
			if not "silent" in self.prismArgs:
				if result == True:
					msg = "Successfully added start menu entries."
					QMessageBox.information(self.messageParent, "Prism", msg)
				else:
					msg = "Creating start menu entries failed"
					QMessageBox.warning(self.messageParent, "Prism", msg)

				
	@err_decorator
	def validateUser(self):
		uname = self.getConfig("globals", "username")
		if uname is None:
			return False

		uname = uname.split()
		if len(uname) == 2:
			if len(uname[0]) > 0 and len(uname[1]) > 1:
				self.username = "%s %s" % (uname[0], uname[1])
				self.user = self.getUserAbbreviation(self.username)
				return True


		return False


	@err_decorator
	def changeUser(self):
		if not self.uiAvailable:
			self.popup("No username is defined. Open the Prism Settings and set a username.")
			return

		if hasattr(self, "user"):
			del self.user

		try:
			del sys.modules["ChangeUser"]
		except:
			pass

		try:
			import ChangeUser
		except:
			modPath = imp.find_module("ChangeUser")[1]
			if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
				os.remove(modPath)
			import ChangeUser

		self.cu = ChangeUser.ChangeUser(core = self)
		self.cu.setModal(True)
		self.parentWindow(self.cu)

		if self.appPlugin.pluginName == "Standalone":
			self.cu.buttonBox.rejected.connect(self.changeUserRejected)

		self.cu.exec_()


	@err_decorator
	def getUserAbbreviation(self, userName=None, fromConfig=True):
		if fromConfig:
			abbr = self.getConfig("globals", "username_abbreviation")
			if abbr:
				return abbr

		if not userName:
			return ""

		abbrev = ""
		userName = userName.split()
		if len(userName) == 2 and len(userName[0]) > 0 and len(userName[1]) > 1:
			abbrev = (userName[0][0] + userName[1][:2]).lower()
		elif len(userName[0]) > 2:
			abbrev = userName[0][:3].lower()

		return abbrev
		

	@err_decorator
	def changeUserRejected(self):
		if not hasattr(self, "user"):
			sys.exit()


	@err_decorator
	def openUser(self):	#called from project browser
		if not os.path.exists(self.userini):
			self.createUserPrefs()

		self.changeUser()


	@err_decorator
	def setProject(self, startup=False, openUi=""):
		try:
			del sys.modules["SetProject"]
		except:
			pass

		try:
			import SetProject
		except:
			modPath = imp.find_module("SetProject")[1]
			if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
				os.remove(modPath)
			import SetProject

		self.sp = SetProject.SetProject(core=self, openUi=openUi)
		self.sp.setModal(True)
		if not startup:
			self.sp.projectsUi.chb_startup.setVisible(False)

		self.sp.show()


	@err_decorator
	def openProject(self):
		if self.prismIni == "":
			path = QFileDialog.getExistingDirectory(self.messageParent, "Select existing project folder")
		else:
			path = QFileDialog.getExistingDirectory(self.messageParent, "Select existing project folder", os.path.abspath(os.path.join(self.prismIni, os.pardir, os.pardir)))
		
		if os.path.basename(path) == "00_Pipeline":
			path = os.path.join(path, "pipeline.ini")
		else:
			path = os.path.join(path, "00_Pipeline", "pipeline.ini")

		if os.path.exists(path):
			try:
				self.sp.close()
			except:
				pass
			self.changeProject(path, openUi="projectBrowser")
		else:
			QMessageBox.warning(self.messageParent,"Warning", "Invalid project folder")


	@err_decorator
	def callHook(self, hookName, args={}):
		self.callback(name=hookName, types=["curApp", "custom"], kwargs=args)

		if not hasattr(self, "projectPath") or self.projectPath == None:
			return

		hookPath = os.path.join(self.projectPath, "00_Pipeline", "Hooks", hookName + ".py")
		if os.path.exists(os.path.dirname(hookPath)) and os.path.basename(hookPath) in os.listdir(os.path.dirname(hookPath)):
			hookDir = os.path.dirname(hookPath)
			if not hookDir in sys.path:
				sys.path.append(os.path.dirname(hookPath))

			try:
				hook = __import__(hookName)
				getattr(hook, "main", lambda x: None)(args)
			except Exception as e:
				QMessageBox.warning(self.messageParent, "Hook Error", "An Error occuredwhile calling the %s hook:\n\n%s" % (hookName, str(e)))

			if hookName in sys.modules:
				del sys.modules[hookName]
			
			if os.path.exists(hookPath+"c"):
				try:
					os.remove(hookPath+"c")
				except:
					pass


	@err_decorator
	def getConfig(self, cat=None, param=None, ptype="string", data=None, configPath=None, getOptions=False, getItems=False, getConf=False):
		if configPath is None:
			configPath = self.userini

		if configPath is None or configPath == "":
			return
			
		isUserIni = configPath == self.userini

		if isUserIni and not os.path.exists(configPath):
			self.createUserPrefs()

		if not os.path.exists(os.path.dirname(configPath)):
			return

		if len([x for x in os.listdir(os.path.dirname(configPath)) if x.startswith(os.path.basename(configPath) + ".bak")]):
			self.restoreConfig(configPath)

		userConfig = ConfigParser()
		try:
			if os.path.exists(configPath):
				userConfig.read(configPath)
		except:
			if isUserIni:
				warnStr = "The Prism preferences file seems to be corrupt.\n\nIt will be reset, which means all local Prism settings will fall back to their defaults.\nYou will need to set your last project again, but no project files (like scenefiles or renderings) are lost."
			else:
				warnStr = "Cannot read the following file:\n\n%s" % configPath
				
			msg = QMessageBox(QMessageBox.Warning, "Warning", warnStr, QMessageBox.Ok, parent=self.messageParent)
			msg.setFocus()
			action = msg.exec_()

			if isUserIni:
				self.createUserPrefs()
				userConfig.read(configPath)

		if getConf:
			return userConfig

		if getOptions:
			if userConfig.has_section(cat):
				return userConfig.options(cat)
			else:
				return []

		if getItems:
			if userConfig.has_section(cat):
				return userConfig.items(cat)
			else:
				return []

		returnData = {}
		if data is None:
			rData = {"val":[cat, param]}
		else:
			rData = data

		for i in rData:
			cat = rData[i][0]
			param = rData[i][1]

			if len(rData[i]) == 3:
				vtype = rData[i][2]
			else:
				vtype = ptype

			if userConfig.has_option(cat, param):
				try:
					if vtype == "string":
						returnData[i] = userConfig.get(cat, param)
					elif vtype == "bool":
						try:
							returnData[i] = userConfig.getboolean(cat, param)
						except:
							QMessageBox.warning(self.messageParent, "Warning", "Could not read '%s' - '%s' from config\n\n%s" % (cat, param, configPath))
							returnData[i] = False

					elif vtype == "int":
						try:
							returnData[i] = userConfig.getint(cat, param)
						except:
							QMessageBox.warning(self.messageParent, "Warning", "Could not read '%s' - '%s' from config %s" % (cat, param, configPath))
							returnData[i] = 0
				except:
					QMessageBox.warning(self.messageParent, "Warning", "Could not read '%s' - '%s' from config %s" % (cat, param, configPath))
					returnData[i] = None
			else:
				returnData[i] = None

		if data is None:
			return returnData["val"]
		else:
			return returnData


	@err_decorator
	def setConfig(self, cat=None, param=None, val=None, data=None, configPath=None, delete=False):
		if configPath is None:
			configPath = self.userini

		isUserIni = configPath == self.userini

		if isUserIni and not os.path.exists(configPath):
			self.createUserPrefs()

		fcontent = os.listdir(os.path.dirname(configPath))
		if len([x for x in fcontent if x.startswith(os.path.basename(configPath) + ".bak")]):
			self.restoreConfig(configPath)

		userConfig = ConfigParser()
		try:
			if os.path.exists(configPath):
				userConfig.read(configPath)
		except:
			if isUserIni:
				warnStr = "The Prism preferences file seems to be corrupt.\n\nIt will be reset, which means all local Prism settings will fall back to their defaults.\nYou will need to set your last project again, but no project files (like scenefiles or renderings) are lost."
			else:
				warnStr = "Cannot read the following file. It will be reset now:\n\n%s" % configPath

			msg = QMessageBox(QMessageBox.Warning, "Warning", warnStr, QMessageBox.Ok, parent=self.messageParent)
			msg.setFocus()
			action = msg.exec_()

			if isUserIni:
				self.createUserPrefs()
				userConfig.read(configPath)

		if data is None:
			data = [[cat, param, val]]

		for i in data:
			cat = i[0]
			param = i[1]
			val = i[2]

			if not userConfig.has_section(cat):
				userConfig.add_section(cat)

			if delete:
				userConfig.remove_option(cat, param)
				continue

			try:
				userConfig.set(cat, param, str(val))
			except UnicodeEncodeError:
				QMessageBox.warning(self.messageParent, "Save config", "Cannot save setting because it contains illegal characters:\n\n%s   -   %s" % (param, unicode(val)), QMessageBox.Ok)

		with open(configPath, 'w') as inifile:
			userConfig.write(inifile)

		testConfig = ConfigParser()
		try:
			testConfig.read(configPath)
			for i in userConfig.sections():
				for k in userConfig.options(i):
					if not testConfig.has_option(i,k):
						raise ConfigParser.Error
		except:
			backupPath = configPath + ".bak" + str(random.randint(1000000,9999999))
			with open(backupPath, 'w') as inifile:
				userConfig.write(inifile)


	@err_decorator
	def restoreConfig(self, configPath):
		path = os.path.dirname(configPath)
		backups = []
		for i in os.listdir(path):
			if not i.startswith(os.path.basename(configPath) + "."):
				continue

			try:
				backups.append({"name":i, "time":os.path.getmtime(os.path.join(path,i)), "size":os.stat(os.path.join(path,i)).st_size})
			except Exception:
				return False

		times = [x["time"] for x in backups]

		if len(times) == 0:
			return False

		minTime = min(times)

		validBackup = None
		for i in backups:
			if i["time"] == minTime and (validBackup is None or validBackup["size"] > i["size"]):
				validBackup = i

		if validBackup is None:
			return False

		while True:
			try:
				if os.path.exists(configPath):
					os.remove(configPath)
				break
			except Exception:
				msg = QMessageBox(QMessageBox.Warning, "Restore config", "Could not remove corrupt config in order to restore a backup config:\n\n%s" % configPath, QMessageBox.Cancel)
				msg.addButton("Retry", QMessageBox.YesRole)
				msg.setFocus()
				action = msg.exec_()

				if action != 0:
					return False

		validBuPath = os.path.join(path, validBackup["name"])

		try:
			shutil.copy2(validBuPath, configPath)
		except:
			msg = QMessageBox(QMessageBox.Warning, "Restore config", "Could not restore backup config:\n\n%s" % validBuPath, QMessageBox.Ok)
			msg.setFocus()
			msg.exec_()
			return False

		for i in backups:
			buPath = os.path.join(path, i["name"])
			try:
				os.remove(buPath)
			except:
				pass

		return True


	@err_decorator
	def readYaml(self, path=None, stream=None, data=None):
		try:
			from ruamel.yaml import YAML
		except:
			self.missingModule("ruamel.yaml")
			return

		yaml=YAML()
		yamlData = []
		if path:
			if not os.path.exists(path):
				return {}

			with open(path, "r") as config:
				yamlData = yaml.load(config)
		else:
			if not stream:
				if not data:
					return
				stream = StringIO(data)
			
			try:
				yamlData = yaml.load(stream)
			except ValueError:
				return

		return yamlData


	@err_decorator
	def writeYaml(self, path=None, data=None, stream=None):
		if not data:
			return

		try:
			from ruamel.yaml import YAML
		except:
			self.missingModule("ruamel.yaml")
			return

		yaml=YAML()

		if path:
			if not os.path.exists(os.path.dirname(path)):
				os.makedirs(os.path.dirname(path))

			with open(path, "w") as config:
				yaml.dump(data, config)
		else:
			if not stream:
				stream = StringIO()

			yaml.dump(data, stream)
			return stream.getvalue()


	@err_decorator
	def readJson(self, path=None, stream=None, data=None):
		import json
		jsonData = []
		if path:
			if not os.path.exists(path):
				return {}

			with open(configPath, 'r') as f:
				jsonData = json.load(f)
		else:
			if not stream:
				if not data:
					return
				stream = StringIO(data)
			
			try:
				jsonData = json.load(stream)
			except ValueError:
				return

		return jsonData

	@err_decorator
	def writeJson(self, data, path=None, stream=None):
		import json

		if path:
			if not os.path.exists(os.path.dirname(path)):
				os.makedirs(os.path.dirname(path))

			with open(path, "w") as config:
				json.dump(data, config, indent=4)
		else:
			if not stream:
				stream = StringIO()

			json.dump(data, stream, indent=4)
			return stream.getvalue()


	@err_decorator
	def missingModule(self, moduleName):
		QMessageBox.warning(self.messageParent, "Couldn't load module", "Module \"%s\" couldn't be loaded.\nMake sure you have the latest Prism version installed." % moduleName)


	@err_decorator
	def validateStr(self, text, allowChars=[], denyChars=[]):
		invalidChars = [" ", "\\", "/", ":", "*", "?", "\"", "<", ">", "|", "ä", "ö", "ü", "ß", self.filenameSeparator]
		for i in allowChars:
			if i in invalidChars:
				invalidChars.remove(i)

		for i in denyChars:
			if i not in invalidChars:
				invalidChars.append(i)

		if pVersion == 2:
			validText = ("".join(ch for ch in str(text.encode("ascii", errors="ignore")) if ch not in invalidChars))
		else:
			validText = ("".join(ch for ch in str(text.encode("ascii", errors="ignore").decode()) if ch not in invalidChars))

		if len(self.filenameSeparator) > 1:
			validText = validText.replace(self.filenameSeparator, "")

		return validText


	@err_decorator
	def getCurrentFileName(self, path=True):
		currentFileName = self.appPlugin.getCurrentFileName(self, path)
		currentFileName = self.fixPath(currentFileName)

		return currentFileName


	@err_decorator
	def fileInPipeline(self):
		fileName = self.fixPath(self.getCurrentFileName())

		fileNameData = self.getScenefileData(fileName)
		sceneDir = self.getConfig('paths', "scenes", configPath=self.prismIni)
		if (self.fixPath(os.path.join(self.projectPath, sceneDir)) in fileName or (self.useLocalFiles and self.fixPath(os.path.join(self.localProjectPath, sceneDir)) in fileName)) and fileNameData["type"] != "invalid":
			return True
		else:
			return False


	@err_decorator
	def getScenefiles(self, latestOnly=True, getAssets=True, getShots=True, localScenes=True, apps=[]):
		scenes = []

		sceneDirs = []
		sceneDirName = self.getConfig('paths', "scenes", configPath=self.prismIni)
		if getAssets:
			sceneDirs.append(os.path.join(self.projectPath, sceneDirName, "Assets"))
			if localScenes and self.useLocalFiles and not latestOnly:
				sceneDirs.append(os.path.join(self.localProjectPath, sceneDirName, "Assets"))

		if getShots:
			sceneDirs.append(os.path.join(self.projectPath, sceneDirName, "Shots"))
			if localScenes and self.useLocalFiles and not latestOnly:
				sceneDirs.append(os.path.join(self.localProjectPath, sceneDirName, "Shots"))

		fileTypes = []
		for app in apps:
			ftypes = self.getPluginData(app, "sceneFormats")
			if ftypes:
				fileTypes += ftypes

		for bPath in sceneDirs:
			for fcont in os.walk(bPath):
				if "/Scenefiles/" not in fcont[0].replace("\\", "/"):
					continue

				if latestOnly:
					result = self.getHighestVersion(fcont[0], getExistingPath=True, fileTypes=fileTypes, localVersions=localScenes)
					if result:
						scenes.append(result)
				else:
					for i in fcont[2]:
						if os.path.splitext(i)[1] in fileTypes:
							scenePath = os.path.join(fcont[0], i)
							scenes.append(scenePath)

		return scenes


	@err_decorator
	def getScenefileData(self, fileName):
		fname = os.path.basename(fileName).split(self.filenameSeparator)

		if len(fname) == 6:
			return {"type": "asset", "assetName": fname[0], "step": fname[1], "category": "", "version": fname[2], "comment": fname[3], "user": fname[4], "extension": fname[5]}
	
		elif len(fname) == 7:
			return  {"type": "asset", "assetName": fname[0], "step": fname[1], "category": fname[2], "version": fname[3], "comment": fname[4], "user": fname[5], "extension": fname[6]}

		elif len(fname) == 8:
			return  {"type": "shot", "shotName": fname[1], "step": fname[2], "category": fname[3], "version": fname[4], "comment": fname[5], "user": fname[6], "extension": fname[7]}
	
		else:
			return {"type": "invalid"}


	@err_decorator
	def getEntityBasePath(self, filepath):
		basePath = ""

		if self.useLocalFiles and filepath.startswith(self.localProjectPath):
			prjPath = self.localProjectPath
		else:
			prjPath = self.projectPath

		sceneDir = self.getConfig('paths', "scenes", configPath=self.prismIni)
		if filepath.startswith(os.path.join(prjPath, sceneDir, "Assets")):
			if self.compareVersions(self.projectVersion, "v1.2.1.6") == "lower":
				basePath = os.path.join(filepath, os.pardir, os.pardir, os.pardir)
			else:
				basePath = os.path.join(filepath, os.pardir, os.pardir, os.pardir, os.pardir)

		elif filepath.startswith(os.path.join(prjPath, sceneDir, "Shots")):
			basePath = os.path.join(filepath, os.pardir, os.pardir, os.pardir, os.pardir)

		return os.path.abspath(basePath)


	@err_decorator
	def generateScenePath(self, entity, entityName, step, assetPath="", category="", extension="", basePath="", version="", comment="", user=""):
		if entity == "asset":
			#example filename: Body_mod_v0002_details-added_rfr_.max
			assetPath = assetPath or basePath

			if os.path.basename(os.path.dirname(assetPath)) == "Scenefiles" or os.path.basename(os.path.dirname(os.path.dirname(assetPath))) == "Scenefiles":
				dstname = assetPath
			else:
				assetPath = assetPath.replace(self.pb.aBasePath, "")
				
				if self.useLocalFiles:
					assetPath = assetPath.replace(self.pb.aBasePath.replace(self.projectPath, self.localProjectPath), "")

				if assetPath[0] in ["/", "\\"]:
					assetPath = assetPath[1:]

				dstname = os.path.join(self.pb.aBasePath, assetPath, "Scenefiles", step)

				if self.compareVersions(self.projectVersion, "v1.2.1.6") != "lower":
					dstname = os.path.join(dstname, category)

			if self.compareVersions(self.projectVersion, "v1.2.1.6") == "lower":
				category = ""
			else:
				category = (category or "") + self.filenameSeparator

			version = version or self.getHighestVersion(dstname, "Asset")
			user = user or self.user

			fileName = entityName + self.filenameSeparator + step + self.filenameSeparator + category + version + self.filenameSeparator + comment + self.filenameSeparator + user
		elif entity == "shot":
			#example filename: shot_a-0010_mod_main_v0002_details-added_rfr_.max
			basePath = basePath or self.pb.sBasePath
			if os.path.basename(os.path.dirname(os.path.dirname(basePath))) == "Scenefiles":
				dstname = basePath
			else:
				dstname = os.path.join(basePath, entityName, "Scenefiles", step, category)
			version = version or self.getHighestVersion(dstname, "Shot")
			user = user or self.user

			fileName = "shot" + self.filenameSeparator + entityName + self.filenameSeparator + step + self.filenameSeparator + category
			fileName += self.filenameSeparator + version + self.filenameSeparator + comment + self.filenameSeparator + user
		else:
			return ""

		if extension:
			fileName += self.filenameSeparator + extension

		scenePath = os.path.join(dstname, fileName)

		return scenePath


	@err_decorator
	def getHighestVersion(self, dstname, scenetype=None, getExistingPath=False, fileTypes="*", localVersions=True):
		if not scenetype:
			glbDstname = dstname
			sceneDirName = self.getConfig('paths', "scenes", configPath=self.prismIni)
			assetPath = os.path.join(self.projectPath, sceneDirName, "Assets")
			shotPath = os.path.join(self.projectPath, sceneDirName, "Shots")

			if self.useLocalFiles:
				glbDstname = dstname.replace(self.localProjectPath, self.projectPath)

			if glbDstname.startswith(assetPath):
				scenetype = "Asset"
			elif glbDstname.startswith(shotPath):
				scenetype = "Shot"
			else:
				return 

		files = []
		if self.useLocalFiles and localVersions:
			dstname = dstname.replace(self.localProjectPath, self.projectPath)

		for i in os.walk(dstname):
			files += [os.path.join(i[0], x) for x in i[2]]
			break

		if self.useLocalFiles and localVersions:
			for i in os.walk(dstname.replace(self.projectPath, self.localProjectPath)):
				files += [os.path.join(i[0], x) for x in i[2]]
				break
			
		highversion = [0, ""]
		for i in files:
			if fileTypes != "*" and os.path.splitext(i)[1] not in fileTypes:
				continue

			fname = self.getScenefileData(i)

			if fname["type"] != scenetype.lower():
				continue

			try:
				version = int(fname["version"][-4:])
			except:
				continue

			if version > highversion[0]:
				highversion = [version, i]
			
		if getExistingPath:
			return highversion[1]
		else:
			return "v" + format(highversion[0] + 1, '04')


	@err_decorator
	def getHighestTaskVersion(self, dstname, getExisting=False, ignoreEmpty=False):
		taskDirs = []
		if self.useLocalFiles:
			dstname = dstname.replace(self.localProjectPath, self.projectPath)

		for i in os.walk(dstname):
			if ignoreEmpty:
				for k in i[1]:
					exFiles = os.listdir(os.path.join(i[0], k))
					if len(exFiles) > 1 or (len(exFiles) == 1 and exFiles[0] != "versioninfo.ini"):
						taskDirs.append(k)
			else:
				taskDirs += i[1]
			break

		if self.useLocalFiles:
			for i in os.walk(dstname.replace(self.projectPath, self.localProjectPath)):
				if ignoreEmpty:
					for k in i[1]:
						exFiles = os.listdir(os.path.join(i[0], k))
						if len(exFiles) > 1 or (len(exFiles) == 1 and exFiles[0] != "versioninfo.ini"):
							taskDirs.append(k)
				else:
					taskDirs += i[1]
				break
			
		highversion = 0
		for i in taskDirs:
			fname = i.split(self.filenameSeparator)

			if len(fname) in [1,2,3]:
				try:
					version = int(fname[0][1:5])
				except:
					continue

				if version > highversion:
					highversion = version

		if not getExisting and not self.separateOutputVersionStack:
			fileName = self.getCurrentFileName()
			fnameData = self.getScenefileData(fileName)
			if fnameData["type"] != "invalid":
				hVersion = fnameData["version"]
			else:
				hVersion = "v0001"

			return hVersion
			
		if getExisting and highversion != 0:
			return "v" + format(highversion, '04')
		else:		
			return "v" + format(highversion + 1, '04')


	@err_decorator
	def getTaskNames(self, taskType, basePath=""):
		taskList = []

		if basePath is None:
			basePath = ""

		if basePath == "":
			fname = self.getCurrentFileName()
			sceneDir = self.getConfig('paths', "scenes", configPath=self.prismIni)
			assetPath = os.path.abspath(os.path.join(fname, os.pardir, os.pardir, os.pardir))
			shotPath = os.path.join(self.projectPath, sceneDir, "Shots")

			if self.useLocalFiles:
				assetPath = assetPath.replace(self.localProjectPath, self.projectPath)
				lassetPath = assetPath.replace(self.projectPath, self.localProjectPath)
				lshotPath = shotPath.replace(self.projectPath, self.localProjectPath)

			fnameData = self.getScenefileData(fname)

			if fnameData["type"] == "asset" and (assetPath in fname or (self.useLocalFiles and lassetPath in fname)):
				basePath = assetPath

			elif fnameData["type"] == "shot" and (shotPath in fname or (self.useLocalFiles and lshotPath in fname)):
				basePath = os.path.join(shotPath, fnameData["shotName"])
			else:
				return taskList

			catPath = os.path.join(basePath, "Scenefiles", fnameData["step"])

		if self.useLocalFiles:
			lbasePath = basePath.replace(self.projectPath, self.localProjectPath)

		taskPath = ""

		if basePath != "":
			if taskType == "export":
				taskPath = os.path.join(basePath, "Export")
				if "lbasePath" in locals():
					ltaskPath = os.path.join(lbasePath, "Export")
			elif taskType == "render":
				taskPath = os.path.join(basePath, "Rendering", "3dRender")
				if "lbasePath" in locals():
					ltaskPath = os.path.join(lbasePath, "Rendering", "3dRender")
			elif taskType == "2d":
				taskPath = os.path.join(basePath, "Rendering", "2dRender")
				if "lbasePath" in locals():
					ltaskPath = os.path.join(lbasePath, "Rendering", "2dRender")
			elif taskType == "playblast":
				taskPath = os.path.join(basePath, "Playblasts")
				if "lbasePath" in locals():
					ltaskPath = os.path.join(lbasePath, "Playblasts")
			elif taskType == "external":
				taskPath = os.path.join(basePath, "Rendering", "external")
				if "lbasePath" in locals():
					ltaskPath = os.path.join(lbasePath, "Rendering", "external")

		taskList = []
		if os.path.exists(taskPath):
			taskList = [ x for x in os.listdir(taskPath) if os.path.isdir(os.path.join(taskPath, x))]

		if self.useLocalFiles and "ltaskPath" in locals() and os.path.exists(ltaskPath):
			taskList += [x for x in os.listdir(ltaskPath) if x not in taskList and os.path.isdir(os.path.join(ltaskPath, x))]

		if "catPath" in locals() and os.path.exists(catPath):
			taskList += [x for x in os.listdir(catPath) if x not in taskList and os.path.isdir(os.path.join(catPath, x))]

		return taskList


	@err_decorator
	def resolve(self, uri, uriType="exportProduct"):
		from PrismUtils import Resolver
		if pVersion == 2:
			reload(Resolver)
		else:
			import importlib
			importlib.reload(Resolver)

		resolver = Resolver.Resolver(self)
		return resolver.resolvePath(uri, uriType)


	@err_decorator
	def getAssetPath(self):
		path = ""
		if os.path.exists(self.prismIni) and hasattr(self, "projectPath") and self.projectPath != None:
			sceneFolder = self.getConfig('paths', "scenes", configPath=self.prismIni)
			if sceneFolder is not None:
				path = os.path.join(self.projectPath, sceneFolder, "Assets")

		return path


	@err_decorator
	def getShotPath(self):
		path = ""
		if os.path.exists(self.prismIni) and hasattr(self, "projectPath") and self.projectPath != None:
			sceneFolder = self.getConfig('paths', "scenes", configPath=self.prismIni)
			if sceneFolder is not None:
				path = os.path.join(self.projectPath, sceneFolder, "Shots")

		return path


	@err_decorator
	def getTexturePath(self):
		path = ""
		if os.path.exists(self.prismIni) and hasattr(self, "projectPath") and self.projectPath != None:
			assetFolder = self.getConfig('paths', "assets", configPath=self.prismIni)
			if assetFolder is not None:
				path = os.path.join(self.projectPath, assetFolder, "Textures")

		return path


	@err_decorator
	def getAssetPaths(self):
		scenesFolder = self.getConfig('paths', "scenes", configPath=self.prismIni)
		dirs = []
		aBasePath = os.path.join(self.projectPath, scenesFolder, "Assets")

		for i in os.walk(aBasePath):
			for k in i[1]:
				if k in ["Export", "Playblasts", "Rendering", "Scenefiles"]:
					continue

				adir = os.path.join(i[0], k)
				dirs.append(adir)
			break

		assetPaths = []
		for path in dirs:
			assetPaths += self.refreshAItem(path)

		return assetPaths


	@err_decorator
	def refreshAItem(self, path):
		self.adclick = False

		dirContent = []
		dirContentPaths = []

		if os.path.exists(path):
			dirContent += os.listdir(path)
			dirContentPaths += [os.path.join(path,x) for x in os.listdir(path)]

		isAsset = False
		if "Export" in dirContent and "Playblasts" in dirContent and "Rendering" in dirContent and "Scenefiles" in dirContent:
			isAsset = True
			return [path]
		else:
			childs = []
			assetPaths = []
			for i in dirContentPaths:
				if os.path.isdir(i):
					if os.path.basename(i) not in childs:
						childs.append(os.path.basename(i))
						assetPaths += self.refreshAItem(i)

			return assetPaths

		return []


	@err_decorator
	def setShotRange(self, shotName, start, end):
		shotFile = os.path.join(os.path.dirname(self.prismIni), "Shotinfo", "shotInfo.ini")

		if not os.path.exists(os.path.dirname(shotFile)):
			os.makedirs(os.path.dirname(shotFile))

		if not os.path.exists(shotFile):
			open(shotFile, 'a').close()

		saveRange = True
		sconfig = ConfigParser()
		while True:
			try:
				sconfig.read(shotFile)
				break
			except:
				warnStr = "Could not read the configuration file for the frameranges:\n%s\n\nYou can try to fix this problem manually and then press retry.\nYou can also overwrite this file, which means that the frameranges for all existing shots will be lost.\nYou can also continue without saving the framerange for the current shot." % shotFile
				msg = QMessageBox(QMessageBox.Warning, "Warning", warnStr, QMessageBox.NoButton, parent=self.messageParent)
				msg.addButton("Retry", QMessageBox.YesRole)
				msg.addButton("Overwrite", QMessageBox.YesRole)
				msg.addButton("Continue", QMessageBox.YesRole)
				msg.setFocus()
				action = msg.exec_()

				if action == 0:
					pass
				elif action == 1:
					break
				elif action == 2:
					saveRange = False
					break

		if saveRange:
			if not sconfig.has_section("shotRanges"):
				sconfig.add_section("shotRanges")

			sconfig.set("shotRanges", shotName, str([start, end]))

			with open(shotFile, 'w') as inifile:
				sconfig.write(inifile)


	@err_decorator
	def getShotRange(self, shotName):
		shotFile = os.path.join(os.path.dirname(self.prismIni), "Shotinfo", "shotInfo.ini")

		if os.path.exists(shotFile):
			sconfig = ConfigParser()
			sconfig.read(shotFile)

			if sconfig.has_option("shotRanges", shotName):
				shotRange = eval(sconfig.get("shotRanges", shotName))
				if type(shotRange) == list and len(shotRange) == 2:
					return shotRange


	@err_decorator
	def saveScene(self, comment="", publish=False, versionUp=True, prismReq=True, filepath="", details={}, preview=None):
		if filepath == "":
			curfile = self.getCurrentFileName()
			filepath = curfile.replace("\\","/")

		if prismReq:
			if not os.path.exists(self.prismIni):
				curPrj = self.getConfig("globals", "current project")
				if curPrj != "" and curPrj is not None:
					QMessageBox.warning(self.messageParent,"Warning (SaveScene)", "Could not find project:\n%s" % os.path.dirname(os.path.dirname(curPrj)))
				self.setProject(openUi="stateManager")
				return False

			if not self.validateUser():
				self.changeUser()

			if not hasattr(self, "user"):
				return False
		
			if not self.fileInPipeline():
				if self.uiAvailable:
					QMessageBox.warning(self.messageParent, "Could not save the file", "The current file is not inside the Pipeline.\nUse the Project Browser to create a file in the Pipeline.")
				else:
					print ("Could not save the file. The current file is not inside the Pipeline.")

				return False
				
			if self.useLocalFiles:
				filepath = self.fixPath(filepath).replace(self.projectPath, self.localProjectPath)
				if not os.path.exists(os.path.dirname(filepath)):
					try:
						os.makedirs(os.path.dirname(filepath))
					except Exception as e:
						title = "Could not save the file"
						msg = "Could not create this folder:\n\n%s\n\n%s" % (os.path.dirname(filepath), str(e))
						if self.uiAvailable:
							QMessageBox.warning(self.messageParent, title, msg)
						else:
							print ("%s. %s" % (title, msg))

						return False

			if versionUp:
				fnameData = self.getScenefileData(curfile)
				dstname = os.path.dirname(filepath)

				if fnameData["type"] == "asset":
					fVersion = self.getHighestVersion(dstname, "Asset")
					filepath = self.generateScenePath(
															entity="asset",
															entityName=fnameData["assetName"],
															step=fnameData["step"],
															category=fnameData["category"],
															comment=comment,
															version=fVersion,
															basePath=dstname,
															extension=self.appPlugin.getSceneExtension(self)
														)

				elif fnameData["type"] == "shot":
					fVersion = self.getHighestVersion(dstname, "Shot")
					filepath = self.generateScenePath(
															entity="shot",
															entityName=fnameData["shotName"],
															step=fnameData["step"],
															category=fnameData["category"],
															comment=comment,
															version=fVersion,
															basePath=dstname,
															extension=self.appPlugin.getSceneExtension(self)
														)
		
		filepath = filepath.replace("\\","/")
		outLength = len(filepath)
		if platform.system() == "Windows" and outLength > 255:
			QMessageBox.warning(self.messageParent, "Could not save the file", "The filepath is longer than 255 characters (%s), which is not supported on Windows." % outLength)
			return False

		self.callback(name="onAboutToSaveFile", types=["custom"], args=[self, filepath, versionUp, comment, publish])

		result = self.appPlugin.saveScene(self, filepath, details)
		if len(details) > 0:
			ymlPath = os.path.splitext(filepath)[0] + "info.yml"
			self.writeYaml(path=ymlPath, data=details)
		if preview is not None:
			prvPath = os.path.splitext(filepath)[0] + "preview.jpg"
			self.savePMap(preview, prvPath)

		self.callback(name="onSaveFile", types=["custom"], args=[self, filepath, versionUp, comment, publish])

		if result == False:
			return False			

		if not prismReq:
			return filepath

		if not os.path.exists(filepath) and os.path.splitext(self.fixPath(self.getCurrentFileName()))[0] != os.path.splitext(self.fixPath(filepath))[0]:
			return False

		self.addToRecent(filepath)

		if publish:
			pubFile = filepath
			if self.useLocalFiles:
				pubFile = self.fixPath(filepath).replace(self.localProjectPath, self.projectPath)
				self.copySceneFile(filepath, pubFile)
		
			fBase = os.path.splitext(os.path.basename(pubFile))[0]

			infoData = {"filename":os.path.basename(pubFile)}
			self.saveVersionInfo(location=os.path.dirname(pubFile), version=fVersion, fps=True, filenameBase=fBase, data=infoData)

		if hasattr(self, "sm"):
			self.sm.scenename = self.getCurrentFileName()

		try:
			self.pb.refreshCurrent()
		except:
			pass

		return filepath


	@err_decorator
	def saveWithComment(self):
		if not os.path.exists(self.prismIni):
			curPrj = self.getConfig("globals", "current project")
			if curPrj != "" and curPrj is not None:
				QMessageBox.warning(self.messageParent,"Warning (StateManager)", "Could not find project:\n%s" % os.path.dirname(os.path.dirname(curPrj)))

			self.setProject(openUi="stateManager")
			return False

		if not self.validateUser():
			self.changeUser()

		if not hasattr(self, "user"):
			return False

		if not self.fileInPipeline():
			QMessageBox.warning(self.messageParent,"Could not save the file", "The current file is not inside the Pipeline.\nUse the Project Browser to create a file in the Pipeline.")
			return False

		try:
			del sys.modules["SaveComment"]
		except:
			pass

		try:
			import SaveComment
		except:
			modPath = imp.find_module("SaveComment")[1]
			if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
				os.remove(modPath)
			import SaveComment

		savec = SaveComment.SaveComment(core = self)
		action = savec.exec_()
		if action != 0:
			if savec.previewDefined:
				prvPMap = savec.l_preview.pixmap()
			else:
				prvPMap = None

			details = savec.getDetails() or {}
			self.saveScene(comment=savec.e_comment.text(), details=details, preview=prvPMap)


	@err_decorator
	def savePMap(self, pmap, path):
		if platform.system() == "Windows":
			pmap.save(path, "JPG")
		else:
			try:
				img = pmap.toImage()
				buf = QBuffer()
				buf.open(QIODevice.ReadWrite)
				img.save(buf, "PNG")

				strio = StringIO()
				strio.write(buf.data())
				buf.close()
				strio.seek(0)
				pimg = Image.open(strio)
				pimg.save(path)
			except:
				pmap.save(path, "JPG")


	@err_decorator
	def copySceneFile(self, origFile, targetFile):
		origFile = self.fixPath(origFile)
		targetFile = self.fixPath(targetFile)
		if origFile == targetFile:
			return

		if not os.path.exists(os.path.dirname(targetFile)):
			os.makedirs(os.path.dirname(targetFile))

		shutil.copy2(origFile, targetFile)

		ymlPath = os.path.splitext(origFile)[0] + "info.yml"
		prvPath = os.path.splitext(origFile)[0] + "preview.jpg"
		ymlPatht = os.path.splitext(targetFile)[0] + "info.yml"
		prvPatht = os.path.splitext(targetFile)[0] + "preview.jpg"

		if os.path.exists(ymlPath) and not os.path.exists(ymlPatht):
			shutil.copy2(ymlPath, ymlPatht)

		if os.path.exists(prvPath) and not os.path.exists(prvPatht):
			shutil.copy2(prvPath, prvPatht)

		ext = os.path.splitext(origFile)[1]
		if ext in self.appPlugin.sceneFormats:
			getattr(self.appPlugin, "copySceneFile", lambda x1, x2, x3: None)(self, origFile, targetFile)
		else:
			for i in self.unloadedAppPlugins.values():
				if ext in i.sceneFormats:
					getattr(i, "copySceneFile", lambda x1, x2, x3: None)(self, origFile, targetFile)


	@err_decorator
	def addToRecent(self,filepath):
		recentfiles = []
		rSection = 'recent_files_' + self.projectName
		for i in range(10):
			recentfiles.append(self.getConfig(rSection, "recent" + "%02d" % (i+1)))
		if filepath in recentfiles:
			recentfiles.remove(filepath)
		recentfiles = [filepath] + recentfiles
		if len(recentfiles) > 10:
			recentfiles = recentfiles[:10]
		for i in range(10):
			if i < len(recentfiles):
				self.setConfig(rSection, "recent" + "%02d" % (i+1), recentfiles[i])
			else:
				self.setConfig(rSection, "recent" + "%02d" % (i+1), "")


	@err_decorator
	def fixPath(self, path):
		if path is None:
			return

		if platform.system() == "Windows":
			path = path.replace("/","\\")
		else:
			path = path.replace("\\","/")

		return path


	@err_decorator
	def openFolder(self, path):
		path = self.fixPath(path)

		if platform.system() == "Windows":
			if os.path.isfile(path):
				cmd = ['explorer', '/select,', path]
			else:
				if path != "" and not os.path.exists(path):
					path = os.path.dirname(path)

				cmd = ['explorer', path]
		elif platform.system() == "Linux":
			if os.path.isfile(path):
				path = os.path.dirname(path)

			cmd = ["xdg-open", "%s" % path]
		elif platform.system() == "Darwin":
			if os.path.isfile(path):
				path = os.path.dirname(path)

			cmd = ["open", "%s" % path]

		if os.path.exists(path):
			subprocess.call(cmd)


	@err_decorator
	def createFolder(self, path, showMessage=False):
		path = self.fixPath(path)

		if os.path.exists(path):
			if showMessage:
				QMessageBox.information(self.messageParent, "Create directory", "Directory already exists:\n\n%s" % path)
			return

		if os.path.isabs(path):
			try:
				os.makedirs(path)
			except:
				pass

		if os.path.exists(path) and showMessage:
			QMessageBox.information(self.messageParent, "Create directory", "Directory created successfully:\n\n%s" % path)


	@err_decorator
	def copyToClipboard(self, text, fixSlashes=True):
		if fixSlashes:
			text = self.fixPath(text)

		cb = QApplication.clipboard()
		cb.setText(text)


	@err_decorator
	def createShortcut(self, vPath, vTarget='', args='', vWorkingDir='', vIcon=''):
		try:
			import win32com.client
		except:
			return
		shell = win32com.client.Dispatch('WScript.Shell')
		shortcut = shell.CreateShortCut(vPath)
		vTarget = vTarget.replace("/", "\\")
		shortcut.Targetpath = vTarget
		shortcut.Arguments = args
		shortcut.WorkingDirectory = vWorkingDir
		if vIcon == '':
			pass
		else:
			shortcut.IconLocation = vIcon

		try:
			shortcut.save()
		except:
			QMessageBox.warning(self.messageParent, "Create Shortcut", "Could not create shortcut:\n\n%s\n\nProbably you don't have permissions to write to this folder. To fix this install Prism to a different location or change the permissions of this folder." % self.fixPath(vPath))


	@err_decorator
	def checkIllegalCharacters(self, strings):
		illegalStrs = []
		for i in strings:
			if not all(ord(c) < 128 for c in i):
				illegalStrs.append(i)

		return illegalStrs


	@err_decorator
	def atoi(self, text):
		return int(text) if text.isdigit() else text


	@err_decorator
	def naturalKeys(self, text):
		return [ self.atoi(c) for c in re.split(r'(\d+)', text) ]


	@err_decorator
	def sortNatural(self, alist):
		sortedList = sorted(alist, key=self.naturalKeys)
		return sortedList


	@err_decorator
	def scenefileSaved(self, arg=None): #callback function
		if hasattr(self, "sm"):
			self.sm.scenename = self.getCurrentFileName()
			self.sm.saveStatesToScene()

		if hasattr(self,  "asThread") and self.asThread.isRunning():
			self.startasThread()


	@err_decorator
	def sceneUnload(self, arg=None): #callback function
		if hasattr(self, "sm"):
			self.sm.close()
			del self.sm

		if hasattr(self,  "asThread") and self.asThread.isRunning():
			self.startasThread()


	@err_decorator
	def sceneOpen(self, arg=None): #callback function
		if not self.sceneOpenChecksEnabled:
			return

		self.appPlugin.sceneOpen(self)

		self.checkImportVersions()
		self.checkFramerange()
		self.checkFPS()


	def checkImportVersions(self):
		if self.getConfig('paths', "scenes", configPath=self.prismIni) is None:
			return

		checkImpVersions = self.getConfig("globals", "check_import_versions", ptype="bool")
		if checkImpVersions is None:
			self.setConfig("globals", "check_import_versions", True)
			checkImpVersions = True

		if not checkImpVersions:
			return

		paths = self.appPlugin.getImportPaths(self)

		if paths == False:
			return

		paths = eval(paths.replace("\\", "/"))
		paths = [[self.fixPath(str(x[0])), self.fixPath(str(x[1]))] for x in paths]

		if len(paths) == 0:
			return

		msgString = "For the following imports there is a newer version available:\n\n"
		updates = 0

		for i in paths:
			if not os.path.exists(os.path.dirname(i[0])):
				continue
			
			versionData = os.path.dirname(os.path.dirname(i[0])).rsplit(os.sep, 1)[1].split(self.filenameSeparator)

			if len(versionData) != 3 or not self.getConfig('paths', "scenes", configPath=self.prismIni) in i[0]:
				continue

			curVersion = versionData[0] + self.filenameSeparator + versionData[1] + self.filenameSeparator + versionData[2]
			latestVersion = None
			for m in os.walk(os.path.dirname(os.path.dirname(os.path.dirname(i[0])))):
				folders = m[1]
				folders.sort()
				for k in reversed(folders):
					if len(k.split(self.filenameSeparator)) == 3 and k[0] == "v" and len(k.split(self.filenameSeparator)[0]) == 5 and len(os.listdir(os.path.join(m[0], k))) > 0:
						latestVersion = k
						break
				break

			if latestVersion is None or curVersion == latestVersion:
				continue

			msgString += "%s\n    current: %s\n    latest: %s\n\n" % (i[1], curVersion, latestVersion)
			updates += 1

		msgString += "Please update the imports in the State Manager."

		if updates > 0:
			if self.uiAvailable:
				QMessageBox.information(self.messageParent, "State updates", msgString)


	def checkFramerange(self):
		if self.getConfig('paths', "scenes", configPath=self.prismIni) is None:
			return

		if not getattr(self.appPlugin, "hasFrameRange", True):
			return

		checkRange = self.getConfig("globals", "checkframeranges", ptype="bool")
		if checkRange is None:
			self.setConfig("globals", "checkframeranges", True)
			checkRange = True

		if not checkRange:
			return

		fileName = self.getCurrentFileName()

		fnameData = self.getScenefileData(fileName)
		if fnameData["type"] != "shot":
			return

		shotName = fnameData["shotName"]

		shotFile = os.path.join(os.path.dirname(self.prismIni), "Shotinfo", "shotInfo.ini")
		if not os.path.exists(shotFile):
			return

		shotConfig = ConfigParser()
		shotConfig.read(shotFile)
		sceneDir = self.getConfig('paths', "scenes", configPath=self.prismIni)

		if (os.path.join(self.projectPath, sceneDir) not in fileName and (self.useLocalFiles and os.path.join(self.localProjectPath, sceneDir) not in fileName)) or not shotConfig.has_option("shotRanges", shotName):
			return

		shotRange = eval(shotConfig.get("shotRanges", shotName))
		if type(shotRange) != list or len(shotRange) != 2:
			return

		curRange = self.appPlugin.getFrameRange(self)

		if int(curRange[0]) == shotRange[0] and int(curRange[1]) == shotRange[1]:
			return			

		msgString = "The framerange of the current scene doesn't match the framerange of the shot:\n\nFramerange of current scene:\n%s - %s\n\nFramerange of shot %s:\n%s - %s" % (int(curRange[0]), int(curRange[1]), shotName, shotRange[0], shotRange[1])

		if self.uiAvailable:
			msg = QMessageBox(QMessageBox.Information, "Framerange mismatch", msgString, QMessageBox.Ok)
			msg.addButton("Set shotrange in scene", QMessageBox.YesRole)
			self.parentWindow(msg)
			action = msg.exec_()

			if action == 0:
				self.setFrameRange(shotRange[0], shotRange[1])
		else:
			print (msgString)


	@err_decorator
	def getFrameRange(self):
		return self.appPlugin.getFrameRange(self)


	@err_decorator
	def setFrameRange(self, startFrame, endFrame):
		self.appPlugin.setFrameRange(self, startFrame, endFrame)


	def checkFPS(self):
		forceFPS = self.getConfig("globals", "forcefps", configPath=self.prismIni)

		if forceFPS != "True":
			return

		if not getattr(self.appPlugin, "hasFrameRange", True):
			return

		if not self.fileInPipeline():
			return

		pFps = self.getConfig('globals', "fps", configPath=self.prismIni)

		if pFps is None:
			return

		pFps = float(pFps)

		curFps = self.getFPS()

		if pFps == curFps:
			return

		vInfo = [["FPS of current scene:", str(curFps)], ["FPS of project", str(pFps)]]

		if self.uiAvailable:
			infoDlg = QDialog()
			lay_info = QGridLayout()

			msgString = "The FPS of the current scene doesn't match the FPS of the project:"
			l_title = QLabel(msgString)

			infoDlg.setWindowTitle("FPS mismatch")
			for idx, val in enumerate(vInfo):
				l_infoName = QLabel(val[0] + ":\t")
				l_info = QLabel(val[1])
				lay_info.addWidget(l_infoName)
				lay_info.addWidget(l_info, idx, 1)

			lay_info.addItem(QSpacerItem(10,10, QSizePolicy.Minimum, QSizePolicy.Expanding))
			lay_info.addItem(QSpacerItem(10,10, QSizePolicy.Expanding, QSizePolicy.Minimum), 0,2)

			lay_info.setContentsMargins(10,10,10,10)
			w_info = QWidget()
			w_info.setLayout(lay_info)
		
			bb_info = QDialogButtonBox()

			bb_info.addButton("Continue", QDialogButtonBox.RejectRole)
			bb_info.addButton("Set project FPS in current scene", QDialogButtonBox.AcceptRole)

			bb_info.accepted.connect(infoDlg.accept)
			bb_info.rejected.connect(infoDlg.reject)

			bLayout = QVBoxLayout()
			bLayout.addWidget(l_title)
			bLayout.addWidget(w_info)
			bLayout.addWidget(bb_info)
			infoDlg.setLayout(bLayout)
			infoDlg.setParent(self.messageParent, Qt.Window)
			infoDlg.resize(460*self.uiScaleFactor, 160*self.uiScaleFactor)

			action = infoDlg.exec_()

			if action == 1:
				self.appPlugin.setFPS(self, float(pFps))


	@err_decorator
	def getFPS(self):
		return float(self.appPlugin.getFPS(self))


	@err_decorator
	def checkAppVersion(self):
		fversion = self.getConfig("globals", "forceversions", configPath=self.prismIni)
		if fversion is None or not eval(fversion) or self.appPlugin.appType == "standalone":
			return

		rversion = self.getConfig("globals", "%s_version" % self.appPlugin.pluginName, configPath=self.prismIni)
		if rversion is None or rversion == "":
			return

		curVersion = self.appPlugin.getAppVersion(self)

		if curVersion != rversion:
			QMessageBox.warning(self.messageParent,"Warning", "You use a different %s version, than configured in your \
current project.\n\nYour current version: %s\nVersion configured in project: %s\n\nPlease use the required %s version to avoid incompatibility problems." % (self.appPlugin.pluginName, curVersion, rversion, self.appPlugin.pluginName))


	@err_decorator
	def getLatestCompositingVersion(self, curPath):

		curFile = os.path.basename(curPath)
		passName = os.path.basename(os.path.dirname(curPath))

		if passName.startswith("v") and unicode(passName[1:5]).isnumeric():
			curVersion = passName[:5]
			passName = ""
			taskPath = os.path.dirname(os.path.dirname(curPath))
		else:
			curVersion = os.path.basename(os.path.dirname(os.path.dirname(curPath)))[:5]
			taskPath = os.path.dirname(os.path.dirname(os.path.dirname(curPath)))

		latestVersion = self.getHighestTaskVersion(taskPath, getExisting=True, ignoreEmpty=True)

		newPath = ""
		for k in os.listdir(taskPath):
			if k.startswith(latestVersion):
				newPath = os.path.join(taskPath, k, passName)
				break

		newPath = os.path.join(newPath, curFile.replace(curVersion, latestVersion)).replace("\\","/")

		return newPath


	@err_decorator
	def getCompositingOut(self, taskName, fileType, useLastVersion, render, localOutput=False, comment="", ignoreEmpty=True):
		fileName = self.getCurrentFileName()

		if taskName is None:
			taskName = ""

		fnameData = self.getScenefileData(fileName)
		if fnameData["type"] == "shot":
			outputPath = os.path.abspath(os.path.join(fileName, os.pardir, os.pardir, os.pardir, os.pardir, "Rendering", "2dRender", taskName))
			if not self.separateOutputVersionStack:
				hVersion = fnameData["version"]
			else:
				hVersion = self.getHighestTaskVersion(outputPath, getExisting=useLastVersion, ignoreEmpty=ignoreEmpty)
			outputFile = "shot" + self.filenameSeparator + fnameData["shotName"] + self.filenameSeparator + taskName + self.filenameSeparator + hVersion + ".####." + fileType
		elif fnameData["type"] == "asset":
			if os.path.join(self.getConfig('paths', "scenes", configPath=self.prismIni), "Assets", "Scenefiles").replace("\\", "/") in fileName:
				outputPath = os.path.join(self.projectPath, self.getConfig('paths', "scenes", configPath=self.prismIni), "Assets", "Rendering", "2dRender", taskName)
			else:
				outputPath = os.path.abspath(os.path.join(fileName, os.pardir, os.pardir, os.pardir, "Rendering", "2dRender", taskName))
			if not self.separateOutputVersionStack:
				hVersion = fnameData["version"]
			else:
				hVersion = self.getHighestTaskVersion(outputPath, getExisting=useLastVersion, ignoreEmpty=ignoreEmpty)
			
			outputFile = fnameData["assetName"] + self.filenameSeparator + taskName + self.filenameSeparator + hVersion + ".####." + fileType
		else:
			outputName = "FileNotInPipeline"
			outputFile = ""

		if outputFile != "":
			outputPath = os.path.join(outputPath, hVersion)
			if comment != "":
				outputPath += self.filenameSeparator + comment
			outputName = os.path.join(outputPath, outputFile)

		if hasattr(self, "useLocalFiles") and self.useLocalFiles:
			if localOutput:
				outputName = outputName.replace(self.projectPath, self.localProjectPath)
			else:
				outputName = outputName.replace(self.localProjectPath, self.projectPath)

		outputName = outputName.replace("\\", "/")

		if render and outputName != "FileNotInPipeline":
			if not os.path.exists(os.path.dirname(outputName)):
				try:
					os.makedirs(os.path.dirname(outputName))
				except:
					QMessageBox.warning(self.messageParent, "Warning", "Could not create output folder")

			self.saveVersionInfo(location=os.path.dirname(outputName), version=hVersion, origin=self.getCurrentFileName())
			self.appPlugin.isRendering = [True, outputName]
		else:
			if self.appPlugin.isRendering[0]:
				return self.appPlugin.isRendering[1]
	
		return outputName


	@err_decorator
	def convertMedia(self, inputpath, startNum, outputpath, outputQuality=None):
		inputpath = inputpath.replace("\\", "/")
		inputExt = os.path.splitext(inputpath)[1]
		videoInput = inputExt in [".mp4", ".mov"]
		startNum = str(startNum)

		ffmpegIsInstalled = False
		if platform.system() == "Windows":
			ffmpegPath = os.path.join(self.prismRoot, "Tools", "FFmpeg" ,"bin", "ffmpeg.exe")
			if os.path.exists(ffmpegPath):
				ffmpegIsInstalled = True
		elif platform.system() == "Linux":
			ffmpegPath = "ffmpeg"
			try:
				subprocess.Popen([ffmpegPath])
				ffmpegIsInstalled = True
			except:
				pass
		elif platform.system() == "Darwin":
			ffmpegPath = os.path.join(self.prismRoot, "Tools", "ffmpeg")
			if os.path.exists(ffmpegPath):
				ffmpegIsInstalled = True

		if not ffmpegIsInstalled:
			QMessageBox.critical(self.messageParent, "Video conversion", "Could not find %s" % ffmpegPath)
			return

		if not os.path.exists(os.path.dirname(outputpath)):
			os.makedirs(os.path.dirname(outputpath))

		if not outputQuality:
			outputQuality = self.getConfig("globals", "media_conversion_quality", configPath=self.prismIni)

			if not outputQuality:
				outputQuality = "23"

		if videoInput:
			nProc = subprocess.Popen([ffmpegPath, "-apply_trc", "iec61966_2_1", "-i", inputpath, "-pix_fmt", "yuv420p", "-start_number", startNum, outputpath, "-y"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		else:
			fps = "24"
			if self.getConfig("globals", "forcefps", configPath=self.prismIni, ptype="bool"):
				fps = self.getConfig("globals", "fps", configPath=self.prismIni)

			nProc = subprocess.Popen([ffmpegPath, "-start_number", startNum, "-framerate", fps, "-apply_trc", "iec61966_2_1", "-i", inputpath, "-pix_fmt", "yuva420p", "-start_number", startNum, outputpath, "-y"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		result = nProc.communicate()

		return result


	@err_decorator
	def saveVersionInfo(self, location, version, origin=None, fps=None, filenameBase="", data={}):
		infoFilePath = os.path.join(location, filenameBase + "versioninfo.ini")
		vConfig = ConfigParser()

		vConfig.add_section("information")
		vConfig.set("information", "Version", version)
		vConfig.set("information", "Created by", self.getConfig("globals", "UserName"))
		vConfig.set("information", "Creation date", time.strftime("%d.%m.%y %X"))

		if origin is not None:
			vConfig.set("information", "Source scene", origin)

		if fps:
			vConfig.set("information", "FPS", str(self.getFPS()))

		depsEnabled = self.getConfig('globals', "track_dependencies", configPath=self.prismIni)
		if depsEnabled != "False":
			if depsEnabled is None:
				self.setConfig('globals', "track_dependencies", val="True", configPath=self.prismIni)

			deps = self.appPlugin.getImportPaths(self)

			if deps == False:
				deps = "[]"

			deps = eval(deps.replace("\\", "/").replace("//", "/"))
			deps = str([str(x[0]) for x in deps])

			extFiles =  getattr(self.appPlugin, "sm_getExternalFiles", lambda x: [[],[]])(self)[0]
			extFiles = str(list(set(extFiles)))

			data["Dependencies"] = deps
			data["External files"] = extFiles

		for i in data:
			vConfig.set("information", i, data[i])

		with open(infoFilePath, "w") as infoFile:
			vConfig.write(infoFile)


	@err_decorator
	def sendEmail(self, text, subject="Prism Error"):
		waitmsg = QMessageBox(QMessageBox.NoIcon, "Sending message", "Sending - please wait..", QMessageBox.Cancel)
		self.parentWindow(waitmsg)
		for i in waitmsg.buttons():
			i.setVisible(False)
		waitmsg.show()
		QCoreApplication.processEvents()

		try:
			pStr = """
try:
	import os, sys
	pyLibs = os.path.join('%s', 'PythonLibs', 'Python27')
	if pyLibs not in sys.path:
		sys.path.insert(0, pyLibs)

	pyLibs = os.path.join('%s', 'PythonLibs', 'CrossPlatform')
	if pyLibs not in sys.path:
		sys.path.insert(0, pyLibs)

	from robobrowser import RoboBrowser

	browser = RoboBrowser(parser='html.parser', history=True, max_age=0)
	browser.open('https://prism-pipeline.com/contact/', verify=False)
	#browser.open('https://prism-pipeline.com/contact/')

	signup_form = browser.get_forms()[1]

	signup_form['your-name'].value = 'PrismMessage'
	signup_form['your-subject'].value = '%s'
	signup_form['your-message'].value = '''%s'''

	signup_form.serialize()

	browser.submit_form(signup_form)
	response = str(browser.parsed)

	if 'Thank you for your message. It has been sent.' in response:
		sys.stdout.write('success')
	else:
		sys.stdout.write('failed')
except Exception as e:
	sys.stdout.write('failed %%s' %% e)
""" % (self.prismRoot.replace("\\", "\\\\"), self.prismRoot.replace("\\", "\\\\"), subject, text.replace("\\", "\\\\").replace("\"", "\\\"").replace("\'", "\\\""))
		#	print pStr
		
			if platform.system() == "Windows":
				pythonPath = os.path.join(self.prismRoot, "Python27", "pythonw.exe")
			else:
				pythonPath = "python"
			result = subprocess.Popen([pythonPath, "-c", pStr], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			stdOutData, stderrdata = result.communicate()

			if not "success" in str(stdOutData):
				exc_type, exc_obj, exc_tb = sys.exc_info()
				messageStr = "%s\n\n%s" % (unicode(stdOutData, errors='ignore'), text)
				raise RuntimeError(messageStr)

			msg = QMessageBox(QMessageBox.Information, "Information", "Sent message successfully.", QMessageBox.Ok, parent=self.messageParent)
			msg.setFocus()
			action = msg.exec_()

		except Exception as e:
			mailDlg = QDialog()

			mailDlg.setWindowTitle("Sending message failed.")
			l_info = QLabel("The message couldn't be sent. Maybe there is a problem with the internet connection or the connection was blocked by a firewall.\n\nPlease send an e-mail with the following text to contact@prism-pipeline.com")

			exc_type, exc_obj, exc_tb = sys.exc_info()

			messageStr = "%s - %s - %s - %s\n\n%s" % (str(e), exc_type, exc_tb.tb_lineno, traceback.format_exc(), text)
			messageStr = "<pre>%s</pre>" % messageStr.replace("\n", "<br />").replace("\t", "    ")
			l_warnings = QTextEdit(messageStr)
			l_warnings.setReadOnly(True)
			l_warnings.setAlignment(Qt.AlignTop)

			sa_warns = QScrollArea()
			sa_warns.setWidget(l_warnings)
			sa_warns.setWidgetResizable(True)
		
			bb_warn = QDialogButtonBox()

			bb_warn.addButton("Retry", QDialogButtonBox.AcceptRole)
			bb_warn.addButton("Ok", QDialogButtonBox.RejectRole)

			bb_warn.accepted.connect(mailDlg.accept)
			bb_warn.rejected.connect(mailDlg.reject)

			bLayout = QVBoxLayout()
			bLayout.addWidget(l_info)
			bLayout.addWidget(sa_warns)
			bLayout.addWidget(bb_warn)
			mailDlg.setLayout(bLayout)
			mailDlg.setParent(self.messageParent, Qt.Window)
			mailDlg.resize(750*self.uiScaleFactor,500*self.uiScaleFactor)

			self.parentWindow(mailDlg)

			action = mailDlg.exec_()

			if action == 1:
				self.sendEmail(text, subject)			


		if "waitmsg" in locals() and waitmsg.isVisible():
			waitmsg.close()


	@err_decorator
	def autoUpdateCheck(self):
		updateEnabled = self.getConfig(cat="globals", param="checkForUpdates")
		if updateEnabled == False:
			return

		lastUpdateCheck = self.getConfig(cat="globals", param="lastUpdateCheck")
		if lastUpdateCheck and (datetime.datetime.now() - datetime.datetime.strptime(lastUpdateCheck, '%Y-%m-%d %H:%M:%S.%f')).total_seconds() < 604800:
			return

		self.checkForUpdates(silent=True)
		self.setConfig(cat="globals", param="lastUpdateCheck", val=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))


	@err_decorator
	def checkForUpdates(self, silent=False):
		pStr = """
try:
	import os, sys

	pyLibs = os.path.join('%s', 'PythonLibs', 'Python27')
	if pyLibs not in sys.path:
		sys.path.insert(0, pyLibs)

	pyLibs = os.path.join('%s', 'PythonLibs', 'CrossPlatform')
	if pyLibs not in sys.path:
		sys.path.insert(0, pyLibs)

	import requests
	page = requests.get('https://raw.githubusercontent.com/RichardFrangenberg/Prism/development/Prism/Scripts/PrismCore.py', verify=False)

	cStr = page.content
	lines = cStr.split('\\n')
	latestVersionStr = '1'
	for line in lines:
		if 'self.version =' in line:
			latestVersionStr = line[line.find('\\"')+2:-1]
			break

	sys.stdout.write(latestVersionStr)

except Exception as e:
	sys.stdout.write('failed %%s' %% e)
""" % (self.prismRoot, self.prismRoot)

		if platform.system() == "Windows":
			pythonPath = os.path.join(self.prismRoot, "Python27", "pythonw.exe")
		else:
			pythonPath = "python"

		result = subprocess.Popen([pythonPath, "-c", pStr], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdOutData, stderrdata = result.communicate()

		if "failed" in str(stdOutData) or len(str(stdOutData).split(".")) < 4:
			if not silent:
				QMessageBox.information(self.messageParent, "Prism", "Unable to read https://raw.githubusercontent.com/RichardFrangenberg/Prism/development/Prism/Scripts/PrismCore.py. Could not check for updates.\n\n(%s)" % stdOutData)
			return

		if pVersion == 3:
			stdOutData = stdOutData.decode("utf-8")

		if self.compareVersions(self.version, stdOutData) == "lower":
			msg = QDialog()
			msg.setWindowTitle("Prism")
			msg.setLayout(QVBoxLayout())
			msg.layout().addWidget(QLabel("A newer version of Prism is available:\n"))
			self.parentWindow(msg)

			bb_update = QDialogButtonBox()
			bb_update.addButton("Ignore", QDialogButtonBox.RejectRole)
			bb_update.addButton("Update Prism", QDialogButtonBox.AcceptRole)
			bb_update.accepted.connect(msg.accept)
			bb_update.rejected.connect(msg.reject)

			
			lo_version = QGridLayout()
			l_curVersion = QLabel(self.version)
			l_latestVersion = QLabel("v" + stdOutData)
			l_curVersion.setAlignment(Qt.AlignRight)
			l_latestVersion.setAlignment(Qt.AlignRight)

			lo_version.addWidget(QLabel("Installed version:"), 0,0)
			lo_version.addWidget(l_curVersion, 0,1)


			lo_version.addWidget(QLabel("Latest version:\n"), 1,0)
			lo_version.addWidget(l_latestVersion, 1,1)
		
			msg.layout().addLayout(lo_version)

			msg.layout().addWidget(bb_update)
			msg.resize(300*self.uiScaleFactor, 10)
			action = msg.exec_()

			if action:
				self.updatePrism(source="github")

		else:
			if not silent:
				QMessageBox.information(self.messageParent, "Prism", "The latest version of Prism is already installed. (%s)" % self.version)


	@err_decorator
	def updatePrism(self, filepath="", source=""):
		if platform.system() == "Windows":
			targetdir = os.path.join(os.environ["temp"], "PrismUpdate")
		else:
			targetdir = "/tmp/PrismUpdate"

		if os.path.exists(targetdir):
			try:
				shutil.rmtree(targetdir, ignore_errors=False, onerror=self.handleRemoveReadonly)
			except:
				QMessageBox.warning(self.messageParent, "Prism update", "Could not remove temp directory:\n%s" % targetdir)
				return
		
		if source == "github":
			waitmsg = QMessageBox(QMessageBox.NoIcon, "Prism update", "Downloading Prism - please wait..", QMessageBox.Cancel)
			self.parentWindow(waitmsg)
			for i in waitmsg.buttons():
				i.setVisible(False)
			waitmsg.show()
			QCoreApplication.processEvents()

			url = 'https://api.github.com/repos/RichardFrangenberg/Prism/zipball'

			try:
				import ssl
				if pVersion == 2:
					import urllib
					u = urllib.urlopen(url, context=ssl._create_unverified_context())
				else:
					import urllib.request
					u = urllib.request.urlopen(url, context=ssl._create_unverified_context())
			except Exception as e:
				if "waitmsg" in locals() and waitmsg.isVisible():
					waitmsg.close()

				QMessageBox.warning(self.messageParent, "Prism update", "Could not connect to github:\n%s" % str(e))
				return

			data = u.read()
			u.close()
			filepath = os.path.join(targetdir, "Prism_update.zip")
			if not os.path.exists(os.path.dirname(filepath)):
				os.makedirs(os.path.dirname(filepath))
				
			with open(filepath, "wb") as f :
				f.write(data)

			if "waitmsg" in locals() and waitmsg.isVisible():
				waitmsg.close()

		if not os.path.exists(filepath):
			return

		import zipfile

		waitmsg = QMessageBox(QMessageBox.NoIcon, "Prism update", "Extracting - please wait..", QMessageBox.Cancel)
		self.parentWindow(waitmsg)
		for i in waitmsg.buttons():
			i.setVisible(False)
		waitmsg.show()
		QCoreApplication.processEvents()

		with zipfile.ZipFile(filepath,"r") as zip_ref:
			zip_ref.extractall(targetdir)

		for i in os.walk(targetdir):
			dirs = i[1]
			break

		updateRoot = os.path.join(targetdir, dirs[0], "Prism")

		if "waitmsg" in locals() and waitmsg.isVisible():
			waitmsg.close()

		msgText = "Are you sure you want to continue?\n\nThis will overwrite existing files in your Prism installation folder."
		if psVersion == 1:
			flags = QMessageBox.StandardButton.Yes
			flags |= QMessageBox.StandardButton.No
			result = QMessageBox.question(self.messageParent, "Prism update", msgText, flags)
		else:
			result = QMessageBox.question(self.messageParent, "Prism update", msgText)

		if not str(result).endswith(".Yes"):
			return

		for i in os.walk(updateRoot):
			for k in i[2]:
				filepath = os.path.join(i[0], k)
				if not os.path.exists(i[0].replace(updateRoot, self.prismRoot)):
					os.makedirs(i[0].replace(updateRoot, self.prismRoot))

				shutil.copy2(filepath, filepath.replace(updateRoot, self.prismRoot) )
				if os.path.splitext(filepath)[1] in [".command", ".sh"]:
					os.chmod(filepath.replace(updateRoot, self.prismRoot), 0o777)

		if os.path.exists(targetdir):
			shutil.rmtree(targetdir, ignore_errors=False, onerror=self.handleRemoveReadonly)
			
		try:
			import psutil
		except:
			pass
		else:
			PROCNAMES = ['PrismTray.exe', "PrismProjectBrowser.exe", "PrismSettings.exe"]
			for proc in psutil.process_iter():
				try:
					if proc.name() in PROCNAMES:
						if proc.pid == os.getpid():
							continue

						p = psutil.Process(proc.pid)

						try:
							if not 'SYSTEM' in p.username():
								try:
									proc.kill()
								except:
									pass
						except:
							pass
				except:
					pass

		trayPath = os.path.join(self.prismRoot, "Tools", "PrismTray.lnk")
		if os.path.exists(trayPath):
			subprocess.Popen([trayPath], shell=True)

		msgStr = "Successfully updated Prism"
		if self.appPlugin.pluginName == "Standalone":
			msgStr += "\n\nPrism will now close. Please restart all your currently open DCC apps."
		else:
			msgStr += "\nPlease restart %s in order to reload Prism." % self.appPlugin.pluginName

		QMessageBox.information(self.messageParent, "Prism update", msgStr)

		if self.appPlugin.pluginName == "Standalone":
			sys.exit()


	@err_decorator
	def handleRemoveReadonly(self, func, path, exc):
		excvalue = exc[1]
		if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
			os.chmod(path, stat.S_IRWXU| stat.S_IRWXG| stat.S_IRWXO) # 0777
			func(path)
		else:
			raise


	@err_decorator
	def ffmpegError(self, title, text, result):
		msg = QMessageBox(QMessageBox.Warning, title, text, QMessageBox.Ok, parent=self.messageParent)
		if result:
			msg.addButton("Show ffmpeg output", QMessageBox.YesRole)
		action = msg.exec_()

		if result and action == 0:
			warnDlg = QDialog()

			warnDlg.setWindowTitle("FFMPEG output")
			warnString = "%s\n%s" % (result[0], result[1])
			l_warnings = QLabel(warnString)
			l_warnings.setAlignment(Qt.AlignTop)

			sa_warns = QScrollArea()

			lay_warns = QHBoxLayout()
			lay_warns.addWidget(l_warnings)
			lay_warns.setContentsMargins(10,10,10,10)
			lay_warns.addStretch()
			w_warns = QWidget()
			w_warns.setLayout(lay_warns)
			sa_warns.setWidget(w_warns)
			sa_warns.setWidgetResizable(True)
		
			bb_warn = QDialogButtonBox()

			bb_warn.addButton("OK", QDialogButtonBox.AcceptRole)

			bb_warn.accepted.connect(warnDlg.accept)

			bLayout = QVBoxLayout()
			bLayout.addWidget(sa_warns)
			bLayout.addWidget(bb_warn)
			warnDlg.setLayout(bLayout)
			warnDlg.setParent(self.messageParent, Qt.Window)
			warnDlg.resize(1000*self.uiScaleFactor,500*self.uiScaleFactor)

			action = warnDlg.exec_()


	@err_decorator
	def popup(self, text, title=None, severity="warning"):
		if title is None:
			if severity == "warning":
				title = "Warning"
			elif severity == "info":
				title = "Information"
			elif severity == "error":
				title == "Error"

		if self.uiAvailable:
			QMessageBox.warning(self.messageParent, title, text)
		else:
			print ("%s - %s" % (title, text))


	def writeErrorLog(self, text):
		try:
			raiseError = False

			ptext = "An unknown Prism error occured.\nThe error was logged.\nIf you want to help improve Prism, please send this error to the developer.\n\nYou can contact the pipeline administrator or the developer, if you have any questions on this.\n\nMake sure you use the latest Prism version by using the automatic update option in the Prism Settings.\n\n"
		#	print (text)

			text += "\n\n"


			if hasattr(self, "prismIni") and hasattr(self, "user"):
				prjErPath = os.path.join(os.path.dirname(self.prismIni), "ErrorLog_%s.txt" % self.user)
				try:
					open(prjErPath, 'a').close()
				except:
					pass

				if os.path.exists(prjErPath):
					with open(prjErPath, "a") as erLog:
						erLog.write(text)

			if hasattr(self, "userini"):
				userErPath = os.path.join(os.path.dirname(self.userini), "ErrorLog_%s.txt" % socket.gethostname())

				try:
					open(userErPath, 'a').close()
				except:
					pass

				if platform.system() in ["Linux", "Darwin"]:
					if os.path.exists(userErPath):
						try:
							os.chmod(userErPath, 0o777)
						except:
							pass

				if os.path.exists(userErPath):
					with open(userErPath, "a") as erLog:
						erLog.write(text)

			if hasattr(self, "messageParent") and self.uiAvailable:
				msg = QDialog()

				msg.setWindowTitle("Error")
				l_info = QLabel(ptext)

				b_show = QPushButton("Show error message")
				b_send = QPushButton("Send to developer (anonymously)...")
				b_ok = QPushButton("Close")

				w_versions = QWidget()
				lay_versions = QHBoxLayout()
				lay_versions.addWidget(b_show)
				lay_versions.addWidget(b_send)
				lay_versions.addWidget(b_ok)
				lay_versions.setContentsMargins(0,10,10,10)
				w_versions.setLayout(lay_versions)

				bLayout = QVBoxLayout()
				bLayout.addWidget(l_info)
				bLayout.addWidget(w_versions)
				bLayout.addStretch()
				msg.setLayout(bLayout)
				msg.setParent(self.messageParent, Qt.Window)
				msg.setFocus()

				b_show.clicked.connect(lambda: QMessageBox.warning(self.messageParent, "Warning", text))
				b_send.clicked.connect(lambda: self.sendError(text))
				b_send.clicked.connect(msg.accept)
				b_ok.clicked.connect(msg.accept)

				action = msg.exec_()

				if "UnicodeDecodeError" in text or "UnicodeEncodeError" in text:
					QMessageBox.information(self.messageParent, "Prism", "The previous error might be caused by the use of special characters (like ö or é). Prism doesn't support this at the moment. Make sure you remove these characters from your filepaths.".decode("utf8"))
			else:
				print (text)
				raiseError = True
			
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			print ("ERROR - writeErrorLog - %s - %s - %s\n\n" % (str(e), exc_type, exc_tb.tb_lineno))

		if raiseError:
			raise RuntimeError(text)


	def sendError(self, errorText):
		msg = QDialog()

		dtext = "The technical error description will be sent, but you can add additional information to this message if you like.\nFor example how to reproduce the problem or your e-mail for further discussions and to get notified when the problem is fixed.\n"
		ptext = "Additional information (optional):"

		msg.setWindowTitle("Send error")
		l_description = QLabel(dtext)
		l_info = QLabel(ptext)
		te_info = QTextEdit()

		b_send = QPushButton("Send to developer (anonymously)")
		b_ok = QPushButton("Close")

		w_versions = QWidget()
		lay_versions = QHBoxLayout()
		lay_versions.addWidget(b_send)
		lay_versions.addWidget(b_ok)
		lay_versions.setContentsMargins(0,10,10,10)
		w_versions.setLayout(lay_versions)

		bLayout = QVBoxLayout()
		bLayout.addWidget(l_description)
		bLayout.addWidget(l_info)
		bLayout.addWidget(te_info)
		bLayout.addWidget(w_versions)
		bLayout.addStretch()
		msg.setLayout(bLayout)
		msg.setParent(self.messageParent, Qt.Window)
		msg.setFocus()

		b_send.clicked.connect(lambda: self.sendEmail("%s\n\n\n%s" % (te_info.toPlainText(), errorText)))
		b_send.clicked.connect(msg.accept)
		b_ok.clicked.connect(msg.accept)

		action = msg.exec_()



if __name__ == "__main__":
	sys.path.append(os.path.join(prismRoot, "PythonLibs", "Python27"))
	qapp = QApplication(sys.argv)
	from UserInterfacesPrism import qdarkstyle
	qapp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))
	appIcon = QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "UserInterfacesPrism", "p_tray.png"))
	qapp.setWindowIcon(appIcon)

	pc = PrismCore(prismArgs=["loadProject"])

	qapp.exec_()