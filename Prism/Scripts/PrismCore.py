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



import sys, os, threading, shutil, time, socket, traceback, imp, platform, random, errno, stat

#check if python 2 or python 3 is used
if sys.version[0] == "3":
	from configparser import ConfigParser
	pVersion = 3
else:
	from ConfigParser import ConfigParser
	pVersion = 2

prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

try:
	from PySide2.QtCore import *
	from PySide2.QtGui import *
	from PySide2.QtWidgets import *
	psVersion = 2
except:
	try:
		from PySide.QtCore import *
		from PySide.QtGui import *
		psVersion = 1
	except:
		sys.path.append(os.path.join(prismRoot, "PythonLibs", "Python27", "PySide"))
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
		#QWidget.__init__(self)
		self.prismIni = ""

		try:
			# set some general variables
			self.version = "v1.1.1.0"

			self.prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

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

			self.stateData = []
			self.prjHDAs = []
			self.uiScaleFactor = 1

			self.smCallbacksRegistered = False
			self.sceneOpenChecksEnabled = True
			self.parentWindows = True
			self.filenameSeperator = "_"

			# delete old paths from the path variable
			for val in sys.path:
				if "00_Pipeline" in val:
					sys.path.remove(val)

			# add the custom python libraries to the path variable, so they can be imported
			if pVersion == 2:
				pyLibs = os.path.join(self.prismRoot, "PythonLibs", "Python27")
			else:
				pyLibs = os.path.join(self.prismRoot, "PythonLibs", "Python35")
				QCoreApplication.addLibraryPath(os.path.join(self.prismRoot, "PythonLibs", "Python35", "PySide2", "plugins"))
				
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
	def updatePlugins(self, current):
		self.unloadedAppPlugins = []
		self.customPlugins = {}
		customPlugins = []
		self.rfManagers = {}
		rfManagers = []
		self.prjManagers = {}
		prjManagers = []

		sys.path.append(os.path.join(self.pluginPathApp, current, "Scripts"))
		self.appPlugin = getattr(__import__("Prism_%s_init" % current), "Prism_Plugin_%s" % current)(self)

		if not self.appPlugin:
			QMessageBox.critical(QWidget(), "Prism Error", "Prism could not initialize correctly and may not work correctly in this session.")
			return

		for k in self.pluginDirs:
			if not os.path.exists(k):
				continue

			for i in os.listdir(k):
				if i == "PluginEmpty":
					continue

				initmodule = "Prism_%s_init" % i
				initPath = os.path.join(k, i, "Scripts", initmodule + ".py")

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
					if pPlug.pluginType in ["App"]:
						self.unloadedAppPlugins.append(pPlug)
					elif pPlug.pluginType in ["Custom"]:
						customPlugins.append(pPlug)
					elif pPlug.pluginType in ["RenderfarmManager"]:
						rfManagers.append(pPlug)
					elif pPlug.pluginType in ["ProjectManager"]:
						prjManagers.append(pPlug)

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

		if not self.appPlugin.hasQtParent:
			self.messageParent = QWidget()
			self.parentWindows = False
			pyLibs = os.path.join(self.prismRoot, "PythonLibs", "Python27", "PySide")
			if pyLibs not in sys.path:
				sys.path.append(pyLibs)
			if self.appPlugin.pluginName != "Standalone":
				self.messageParent.setWindowFlags(self.messageParent.windowFlags() ^ Qt.WindowStaysOnTopHint)

		getattr(self.appPlugin, "instantStartup", lambda x:None)(self)

		if self.appPlugin.pluginName != "Standalone":
			self.maxwait = 20
			self.elapsed = 0
			self.timer = QTimer()
			result = self.startup()
			if result == False:
				self.timer.timeout.connect(self.startup)
				self.timer.start(1000)
		else:
			self.startup()


	@err_decorator
	def reloadPlugins(self):
		for i in [self.appPlugin.pluginName]: # self.getPluginNames():
			mods = ["Prism_%s_init" % i, "Prism_%s_externalAccess_Functions" % i, "Prism_%s_Functions" % i, "Prism_%s_Variables" % i]
			for k in mods:
				try:
					del sys.modules[k]
				#	del sys.modules["Prism_%s_init" % i]
				#	del sys.modules["Prism_%s_externalAccess_Functions" % i]
				#	del sys.modules[]
				#	del sys.modules[]
				except:
					pass

			self.appPlugin = getattr(__import__("Prism_%s_init" % i), "Prism_Plugin_%s" % i)(self)

			#	__import__(k)


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
	def callback(self, name="", types=["custom"], args=[], kwargs={}):
		if "curApp" in types:
			getattr(self.appPlugin, name, lambda *args, **kwargs: None)(*args, **kwargs)

		if "unloadedApps" in types:
			for i in self.unloadedAppPlugins:
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
			if self.elapsed > self.maxwait:
				self.timer.stop()

		result = self.appPlugin.startup(self)

		if result is not None:
			return result

		if not "silent" in self.prismArgs:
			curPrj = self.getConfig("globals", "current project")
			if curPrj == "" and self.getConfig("globals", "showonstartup", ptype="bool"):
				self.setProject(startup=True, openUi="projectBrowser")

		curPrj = self.getConfig("globals", "current project")

		if curPrj != "":
			self.changeProject(curPrj)
			if not "silent" in self.prismArgs and self.getConfig("globals", "showonstartup", ptype="bool"):
				self.projectBrowser()

		if self.getCurrentFileName() != "":
			self.sceneOpen()


	@err_decorator
	def startasThread(self, quit=False):
		if hasattr(self,  "asThread") and self.asThread.isRunning():
			self.asObject.active = False
			self.asThread.quit()

		if quit:
			return

		autoSave = self.getConfig("globals", "autosave")
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

		msg = QMessageBox()
		msg.setWindowTitle("Autosave")
		msg.setText("Autosave is disabled. Would you like to save now?")
		msg.addButton("Save", QMessageBox.YesRole)
		msg.addButton("Save new version", QMessageBox.YesRole)
		msg.addButton("No", QMessageBox.YesRole)
		msg.addButton("No, don't ask again in this session", QMessageBox.YesRole)

		self.parentWindow(msg)
		msg.finished.connect(self.autoSaveDone)
		msg.setModal(False)
		action = msg.show()


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
		with open(self.userini, 'w') as inifile:
			uconfig.write(inifile)

		if platform.system() in ["Linux", "Darwin"]:
			if os.path.exists(self.userini):
				os.chmod(self.userini, 0o777)


	@err_decorator
	def changeProject(self, inipath, openUi="", settingsTab=1):
		if inipath is None:
			return
			
		delModules = []

		for i in sys.path:
			if self.prismIni != "" and os.path.dirname(self.prismIni) in i:
				delModules.append(i)

		for i in delModules:
			sys.path.remove(i)

		if not os.path.exists(inipath):
			self.prismIni = ""
			self.setConfig("globals", "current project", "")
			if hasattr(self, "projectName"):
				del self.projectName
			if hasattr(self, "projectPath"):
				del self.projectPath
			if hasattr(self, "useLocalFiles"):
				del self.useLocalFiles
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

		rSection = "recent_files_" + self.projectName

		for i in range(10):
			if self.getConfig(rSection, "recent" + "%02d" % (i+1)) is None:
				self.setConfig(rSection, "recent" + "%02d" % (i+1), "")

		sep = self.getConfig("globals", "filenameseperator", configPath=self.prismIni)
		if sep is not None:
			self.filenameSeperator = self.validateStr(sep, allowChars=[self.filenameSeperator])

		self.setRecentPrj(inipath)
		self.checkAppVersion()
		self.checkCommands()
		self.callback(name="onProjectChanged", types=["curApp", "custom", "prjManagers"], args=[self])

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
			if self.appPlugin.pluginName != "Standalone":
				win.setWindowFlags(win.windowFlags() ^ Qt.WindowStaysOnTopHint)
	
		if not self.parentWindows:
			return
			
		win.setParent(self.messageParent, Qt.Window)

		if platform.system() == "Darwin":
			win.setWindowFlags(win.windowFlags() ^ Qt.WindowStaysOnTopHint)


	@err_decorator
	def createProject(self):
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

		self.cp = CreateProject.CreateProject(core = self)
		self.cp.show()


	@err_decorator
	def showAbout(self, dlgVersion=""):
		msg = QMessageBox(QMessageBox.Information, "About", "Prism: %s\n%s\n\nCopyright (C) 2016-2018 Richard Frangenberg\nLicense: GNU GPL-3.0-or-later\n\ncontact@prism-pipeline.com\n\nwww.prism-pipeline.com" % (self.version, dlgVersion), parent=self.messageParent)
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

			self.sm.show()
			self.sm.collapseFolders()
			self.sm.saveStatesToScene()

			if hasattr(self, "sm"):
				self.sm.activateWindow()
				self.sm.raise_()


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
	def projectBrowser(self):
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
			self.pb.show()

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
			self.appPlugin.createWinStartMenu(self)
			if not "silent" in self.prismArgs:
				QMessageBox.information(self.messageParent, "Prism", "Successfully added start menu entries.")


	@err_decorator
	def validateUser(self):		
		uname = self.getConfig("globals", "username")
		if uname is None:
			return False

		uname = uname.split()
		if len(uname) == 2:
			if len(uname[0]) > 0 and len(uname[1]) > 1:
				self.user = (uname[0][0] + uname[1][:2]).lower()
				self.username = "%s %s" % (uname[0], uname[1])
				return True


		return False


	@err_decorator
	def changeUser(self):
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
		if os.path.exists(os.path.join(path, "00_Pipeline", "pipeline.ini")):
			try:
				self.sp.close()
			except:
				pass
			self.changeProject(os.path.join(path, "00_Pipeline", "pipeline.ini"), openUi="projectBrowser")
		else:
			QMessageBox.warning(self.messageParent,"Warning", "Invalid project folder")


	@err_decorator
	def callHook(self, hookName, args={}):
		self.callback(name=hookName, types=["curApp", "custom"], kwargs=args)

		if not hasattr(self, "projectPath") or self.projectPath == None:
			return

		hookPath = os.path.join(self.projectPath, "00_Pipeline", "Hooks", hookName + ".py")
		if os.path.basename(hookPath) in os.listdir(os.path.dirname(hookPath)):
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
				if vtype == "string":
					returnData[i] = userConfig.get(cat, param)
				elif vtype == "bool":
					returnData[i] = userConfig.getboolean(cat, param)
				elif vtype == "int":
					returnData[i] = userConfig.getint(cat, param)
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

			userConfig.set(cat, param, str(val))

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
	def validateStr(self, text, allowChars=[], denyChars=[]):
		invalidChars = [" ", "\\", "/", ":", "*", "?", "\"", "<", ">", "|", "ä", "ö", "ü", "ß", self.filenameSeperator]
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

		if len(self.filenameSeperator) > 1:
			validText = validText.replace(self.filenameSeperator, "")

		return validText


	@err_decorator
	def getPluginNames(self):
		pluginNames = [x.pluginName for x in self.unloadedAppPlugins]
		pluginNames.append(self.appPlugin.pluginName)

		return sorted(pluginNames)


	@err_decorator
	def getPluginSceneFormats(self):
		pluginFormats = list(self.appPlugin.sceneFormats)

		for i in self.unloadedAppPlugins:
			pluginFormats += i.sceneFormats

		return pluginFormats


	@err_decorator
	def getPluginData(self, pluginName, data):
		if pluginName == self.appPlugin.pluginName:
			return getattr(self.appPlugin, data, None)
		else:
			for i in self.unloadedAppPlugins:
				if i.pluginName == pluginName:
					return getattr(i, data, None)

		return None


	@err_decorator
	def getPlugin(self, pluginName):
		if pluginName == self.appPlugin.pluginName:
			return self.appPlugin
		else:
			for i in self.unloadedAppPlugins:
				if i.pluginName == pluginName:
					return i

		return None


	@err_decorator
	def getCurrentFileName(self, path=True):
		currentFileName = self.appPlugin.getCurrentFileName(self, path)
		currentFileName = self.fixPath(currentFileName)

		return currentFileName


	@err_decorator
	def fileInPipeline(self):
		fileName = self.getCurrentFileName()

		fileNameData = os.path.basename(fileName).split(self.filenameSeperator)
		sceneDir = self.getConfig('paths', "scenes", configPath=self.prismIni)
		if (os.path.join(self.projectPath, sceneDir) in fileName or (self.useLocalFiles and os.path.join(self.localProjectPath, sceneDir) in fileName)) and (len(fileNameData) == 6 or len(fileNameData) == 8):
			return True
		else:
			return False


	@err_decorator
	def getHighestVersion(self, dstname, scenetype):
		if scenetype == "Asset":
			numvers = 2
		elif scenetype == "Shot":
			numvers = 4

		files = []
		if self.useLocalFiles:
			dstname = dstname.replace(self.localProjectPath, self.projectPath)

		for i in os.walk(dstname):
			files += i[2]
			break

		if self.useLocalFiles:
			for i in os.walk(dstname.replace(self.projectPath, self.localProjectPath)):
				files += i[2]
				break
			
		highversion = 0
		for i in files:
			fname = i.split(self.filenameSeperator)

			if (len(fname) == 8 or len(fname) == 6):
				try:
					version = int(fname[numvers][-4:])
				except:
					continue

				if version > highversion:
					highversion = version
			

		return "v" + format(highversion + 1, '04')


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
			fname = i.split(self.filenameSeperator)

			if len(fname) in [1,2,3]:
				try:
					version = int(fname[0][1:5])
				except:
					continue

				if version > highversion:
					highversion = version
			
		if getExisting and highversion != 0:
			return "v" + format(highversion, '04')
		else:		
			return "v" + format(highversion + 1, '04')


	@err_decorator
	def getTaskNames(self, taskType, basePath=""):
		taskList = []

		if basePath == "":
			fname = self.getCurrentFileName()
			sceneDir = self.getConfig('paths', "scenes", configPath=self.prismIni)
			assetPath = os.path.abspath(os.path.join(fname, os.pardir, os.pardir, os.pardir))
			shotPath = os.path.join(self.projectPath, sceneDir, "Shots")

			if self.useLocalFiles:
				assetPath = assetPath.replace(self.localProjectPath, self.projectPath)
				lassetPath = assetPath.replace(self.projectPath, self.localProjectPath)
				lshotPath = shotPath.replace(self.projectPath, self.localProjectPath)

			if len(os.path.basename(fname).split(self.filenameSeperator)) == 6 and (assetPath in fname or (self.useLocalFiles and lassetPath in fname)):
				basePath = assetPath

			elif len(os.path.basename(fname).split(self.filenameSeperator)) == 8 and (shotPath in fname or (self.useLocalFiles and lshotPath in fname)):
				basePath = os.path.join(shotPath, os.path.basename(fname).split(self.filenameSeperator)[1])
				catPath = os.path.join(basePath, "Scenefiles", os.path.basename(fname).split(self.filenameSeperator)[2])

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
			taskList = os.listdir(taskPath)

		if self.useLocalFiles and "ltaskPath" in locals() and os.path.exists(ltaskPath):
			taskList += [x for x in os.listdir(ltaskPath) if x not in taskList]

		if "catPath" in locals() and os.path.exists(catPath):
			taskList += [x for x in os.listdir(catPath) if x not in taskList]

		return taskList


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
		aBasePath = os.path.join(self.projectPath, self.getConfig('paths', "scenes", configPath=self.prismIni), "Assets")

		dirs = []

		for i in os.walk(aBasePath):
			for k in i[1]:
				if k in ["Export", "Playblasts", "Rendering", "Scenefiles"]:
					continue
				dirs.append(os.path.join(i[0], k))
			break

		if self.useLocalFiles:
			lBasePath = aBasePath.replace(self.projectPath, self.localProjectPath)

			for i in os.walk(lBasePath):
				for k in i[1]:
					if k in ["Export", "Playblasts", "Rendering", "Scenefiles"]:
						continue

					ldir = os.path.join(i[0], k)
					if ldir.replace(self.localProjectPath, self.projectPath) not in dirs:
						dirs.append(ldir)
				break


		assetPaths = []
		for path in dirs:
			val = os.path.basename(path)
			if path == aBasePath or (self.useLocalFiles and path == lBasePath):
				if aBasePath not in assetPaths:
					assetPaths.append(aBasePath)
			else:
				assetPaths += self.refreshAItem(path)

		return assetPaths


	@err_decorator
	def refreshAItem(self, path):
		self.adclick = False

		if self.useLocalFiles:
			path = path.replace(self.localProjectPath, self.projectPath)
			lpath = path.replace(self.projectPath, self.localProjectPath)

		dirContent = []
		dirContentPaths = []

		if os.path.exists(path):
			dirContent += os.listdir(path)
			dirContentPaths += [os.path.join(path,x) for x in os.listdir(path)]

		if self.useLocalFiles and os.path.exists(lpath):
			dirContent += os.listdir(lpath)
			dirContentPaths += [os.path.join(lpath,x) for x in os.listdir(lpath)]

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
	def saveScene(self, comment = "nocomment", publish=False, versionUp=True, prismReq=True, filepath=""):
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
				QMessageBox.warning(self.messageParent,"Could not save the file", "The current file is not inside the Pipeline.\nUse the Project Browser to create a file in the Pipeline.")
				return False
				
			if self.useLocalFiles:
				dstname = filepath.replace(self.projectPath, self.localProjectPath)
				if not os.path.exists(dstname):
					os.makedirs(dstname)

			if versionUp:
				fname = os.path.basename(curfile).split(self.filenameSeperator)
				dstname = os.path.dirname(curfile)

				if len(fname) == 6:
					fname[2] = self.getHighestVersion(dstname, "Asset")
					fname[3] = comment
					fname[4] = self.user
					fname[5] = self.appPlugin.getSceneExtension(self)

				elif len(fname) == 8:
					fname[4] = self.getHighestVersion(dstname, "Shot")
					fname[5] = comment
					fname[6] = self.user
					fname[7] = self.appPlugin.getSceneExtension(self)

				newfname = ""
				for i in fname:
					newfname += i + self.filenameSeperator
				newfname = newfname[:-1]
				filepath = os.path.join(dstname, newfname)
				filepath = filepath.replace("\\","/")

		outLength = len(filepath)
		if platform.system() == "Windows" and outLength > 255:
			QMessageBox.warning(self.messageParent, "Could not save the file", "The filepath is longer than 255 characters (%s), which is not supported on Windows." % outLength)
			return False

		result = self.appPlugin.saveScene(self, filepath)
		self.callback(name="onSaveFile", types=["custom"], args=[self, filepath])

		if result == False:
			return False			

		if not prismReq:
			return filepath

		if not os.path.exists(filepath):
			return False

		self.addToRecent(filepath)

		if publish and self.useLocalFiles:
			self.copySceneFile(filepath, self.fixPath(filepath).replace(self.localProjectPath, self.projectPath))

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
		fname = len(os.path.basename(self.getCurrentFileName()).split(self.filenameSeperator))
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

		self.savec = SaveComment.SaveComment(core = self)
		self.savec.buttonBox.accepted.connect(lambda: self.saveScene(self.savec.e_comment.text()))
		self.savec.exec_()


	@err_decorator
	def copySceneFile(self, origFile, targetFile):
		shutil.copy2(self.fixPath(origFile), self.fixPath(targetFile))
		ext = os.path.splitext(origFile)[1]
		if ext in self.appPlugin.sceneFormats:
			getattr(self.appPlugin, "copySceneFile", lambda x1, x2, x3: None)(self, origFile, targetFile)
		else:
			for i in self.unloadedAppPlugins:
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

		cb = qApp.clipboard()
		cb.setText(text)


	@err_decorator
	def createShortcut(self, vPath, vTarget='', args='', vWorkingDir='', vIcon=''):
		try:
			import win32com.client
		except:
			return
		shell = win32com.client.Dispatch('WScript.Shell')
		shortcut = shell.CreateShortCut(vPath)
		shortcut.Targetpath = vTarget
		shortcut.Arguments = args
		shortcut.WorkingDirectory = vWorkingDir
		if vIcon == '':
			pass
		else:
			shortcut.IconLocation = vIcon
		shortcut.save()


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
			
			versionData = os.path.dirname(os.path.dirname(i[0])).rsplit(os.sep, 1)[1].split(self.filenameSeperator)

			if len(versionData) != 3 or not self.getConfig('paths', "scenes", configPath=self.prismIni) in i[0]:
				continue

			curVersion = versionData[0] + self.filenameSeperator + versionData[1] + self.filenameSeperator + versionData[2]
			latestVersion = None
			for m in os.walk(os.path.dirname(os.path.dirname(os.path.dirname(i[0])))):
				folders = m[1]
				folders.sort()
				for k in reversed(folders):
					if len(k.split(self.filenameSeperator)) == 3 and k[0] == "v" and len(k.split(self.filenameSeperator)[0]) == 5 and len(os.listdir(os.path.join(m[0], k))) > 0:
						latestVersion = k
						break
				break

			if latestVersion is None or curVersion == latestVersion:
				continue

			msgString += "%s\n    current: %s\n    latest: %s\n\n" % (i[1], curVersion, latestVersion)
			updates += 1

		msgString += "Please update the imports in the State Manager."

		if updates > 0:
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

		fnameData = os.path.basename(fileName).split(self.filenameSeperator)
		if len(fnameData) != 8:
			return

		shotName = fnameData[1]

		shotFile = os.path.join(os.path.dirname(self.prismIni), "Shotinfo", "shotInfo.ini")
		if not os.path.exists(shotFile):
			return

		shotConfig = ConfigParser()
		shotConfig.read(shotFile)
		sceneDir = self.getConfig('paths', "scenes", configPath=self.prismIni)

		if (os.path.join(self.projectPath, sceneDir) not in fileName and (self.useLocalFiles and os.path.join(self.localProjectPath, sceneDir) not in fileName)) or len(fnameData) != 8 or not shotConfig.has_option("shotRanges", shotName):
			return

		shotRange = eval(shotConfig.get("shotRanges", shotName))
		if type(shotRange) != list or len(shotRange) != 2:
			return

		curRange = self.appPlugin.getFrameRange(self)

		if int(curRange[0]) == shotRange[0] and int(curRange[1]) == shotRange[1]:
			return			

		msgString = "The framerange of the current scene doesn't match the framerange of the shot:\n\nFramerange of current scene:\n%s - %s\n\nFramerange of shot %s:\n%s - %s" % (int(curRange[0]), int(curRange[1]), shotName, shotRange[0], shotRange[1])

		msg = QMessageBox(QMessageBox.Information, "Framerange mismatch", msgString, QMessageBox.Ok)
		msg.addButton("Set shotrange in scene", QMessageBox.YesRole)
		self.parentWindow(msg)
		action = msg.exec_()

		if action == 0:
			self.setFrameRange(shotRange[0], shotRange[1])


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

		fnameData = os.path.basename(fileName).split(self.filenameSeperator)
		if len(fnameData) == 8:
			outputPath = os.path.abspath(os.path.join(fileName, os.pardir, os.pardir, os.pardir, os.pardir, "Rendering", "2dRender", taskName))
			hVersion = self.getHighestTaskVersion(outputPath, getExisting=useLastVersion, ignoreEmpty=ignoreEmpty)
			outputFile = fnameData[0] + self.filenameSeperator + fnameData[1] + self.filenameSeperator + taskName + self.filenameSeperator + hVersion + ".####." + fileType
		elif len(fnameData) == 6:
			if os.path.join(self.getConfig('paths', "scenes", configPath=self.prismIni), "Assets", "Scenefiles").replace("\\", "/") in fileName:
				outputPath = os.path.join(self.projectPath, self.getConfig('paths', "scenes", configPath=self.prismIni), "Assets", "Rendering", "2dRender", taskName)
			else:
				outputPath = os.path.abspath(os.path.join(fileName, os.pardir, os.pardir, os.pardir, "Rendering", "2dRender", taskName))
			hVersion = self.getHighestTaskVersion(outputPath, getExisting=useLastVersion, ignoreEmpty=ignoreEmpty)
			
			outputFile = fnameData[0] + self.filenameSeperator + taskName + self.filenameSeperator + hVersion + ".####." + fileType
		else:
			outputName = "FileNotInPipeline"
			outputFile = ""

		if outputFile != "":
			outputPath = os.path.join(outputPath, hVersion)
			if comment != "":
				outputPath += self.filenameSeperator + comment
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
	def saveVersionInfo(self, location, version, origin, fps=None):
		infoFilePath = os.path.join(location, "versioninfo.ini")
		vConfig = ConfigParser()

		vConfig.add_section("information")
		vConfig.set("information", "Version", version)
		vConfig.set("information", "Created by", self.getConfig("globals", "UserName"))
		vConfig.set("information", "Creation date", time.strftime("%d.%m.%y %X"))
		vConfig.set("information", "Source scene", origin)

		if fps:
			vConfig.set("information", "FPS", str(self.getFPS()))

		with open(infoFilePath, "w") as infoFile:
			vConfig.write(infoFile)


	@err_decorator
	def sendEmail(self, text, subject="Prism Error"):
		waitmsg = QMessageBox(QMessageBox.NoIcon, "Sending message", "Sending - please wait..", QMessageBox.Cancel)
		self.parentWindow(waitmsg)
		waitmsg.buttons()[0].setHidden(True)
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
				try:
					import smtplib

					from email.mime.text import MIMEText

					msg = MIMEText(text)

					msg['Subject'] = subject
					msg['From'] = "vfxpipemail@gmail.com"
					msg['To'] = "contact@prism-pipeline.com"

					s = smtplib.SMTP('smtp.gmail.com:587')
					s.ehlo()
					s.starttls()
					s.login("vfxpipemail@gmail.com", "vfxpipeline")
					s.sendmail("vfxpipemail@gmail.com", "contact@prism-pipeline.com", msg.as_string())
					s.quit()
				except Exception as e:
					exc_type, exc_obj, exc_tb = sys.exc_info()
					messageStr = "%s\n\n%s - %s - %s - %s\n\n%s" % (stdOutData, str(e), exc_type, exc_tb.tb_lineno, traceback.format_exc(), text)
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
	def checkPrismVersion(self):
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
	page = requests.get('https://prism-pipeline.com/downloads/', verify=False)
	#page = requests.get('https://prism-pipeline.com/downloads/')

	cStr = page.content
	vCode = 'Latest version: ['
	latestVersionStr = cStr[cStr.find(vCode)+len(vCode): cStr.find(']', cStr.find('Latest version: ['))]

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

		if "failed" in str(stdOutData) or len(str(stdOutData).split(".")) < 3:
			msg = QMessageBox(QMessageBox.Information, "Prism", "Unable to connect to www.prism-pipeline.com. Could not check for updates.", QMessageBox.Ok, parent=self.messageParent)
			msg.setFocus()
			action = msg.exec_()
			return

		if pVersion == 3:
			stdOutData = stdOutData.decode("utf-8")

		latestVersion = str(stdOutData).split(".")
		latestVersion = [int(str(x)) for x in latestVersion]

		coreversion = self.version[1:].split(".")
		curVersion = [int(x) for x in coreversion]

		if curVersion[0] < latestVersion[0] or (curVersion[0] == latestVersion[0] and curVersion[1] < latestVersion[1]) or (curVersion[0] == latestVersion[0] and curVersion[1] == latestVersion[1] and curVersion[2] < latestVersion[2]):
			msg = QMessageBox(QMessageBox.Information, "Prism", "A newer version of Prism is available.\n\nInstalled version:\t%s\nLatest version:\t\tv%s" % (self.version, stdOutData), QMessageBox.Ok, parent=self.messageParent)
			msg.addButton("Go to downloads page", QMessageBox.YesRole)
			msg.setFocus()
			action = msg.exec_()

			if action == 0:
				self.openWebsite("downloads")

		else:
			msg = QMessageBox(QMessageBox.Information, "Prism", "The latest version of Prism is already installed. (%s)" % self.version, QMessageBox.Ok, parent=self.messageParent)
			msg.setFocus()
			action = msg.exec_()


	@err_decorator
	def updatePrism(self, filepath="", gitHub=False):
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

		if gitHub:
			try:
				from git import Repo
			except:
				QMessageBox.warning(self.messageParent, "Prism update", "Could not load git. In order to update Prism from GitHub you need git installed on your computer.")
				return

			waitmsg = QMessageBox(QMessageBox.NoIcon, "Prism update", "Downloading repository - please wait..", QMessageBox.Cancel)
			waitmsg.buttons()[0].setHidden(True)
			waitmsg.show()
			QCoreApplication.processEvents()

			Repo.clone_from("https://github.com/RichardFrangenberg/Prism", targetdir)

			updateRoot = os.path.join(os.environ["temp"], "PrismUpdate", "Prism")
		else:
			if not os.path.exists(filepath):
				return

			import zipfile

			waitmsg = QMessageBox(QMessageBox.NoIcon, "Prism update", "Extracting - please wait..", QMessageBox.Cancel)
			waitmsg.buttons()[0].setHidden(True)
			waitmsg.show()
			QCoreApplication.processEvents()

			with zipfile.ZipFile(filepath,"r") as zip_ref:
				zip_ref.extractall(targetdir)

			updateRoot = os.path.join(os.environ["temp"], "PrismUpdate", "Prism-development", "Prism")

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

		if os.path.exists(targetdir):
			shutil.rmtree(targetdir, ignore_errors=False, onerror=self.handleRemoveReadonly)
		try:
			import psutil
		except:
			pass
		else:
			PROCNAMES = ['PrismTray.exe', "PrismProjectBrowser.exe", "PrismSettings.exe"]
			for proc in psutil.process_iter():
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
		msg.addButton("Show ffmpeg output", QMessageBox.YesRole)
		action = msg.exec_()

		if action == 0:
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


	def writeErrorLog(self, text):
		try:

			ptext = "An unknown Prism error occured.\nThe error was logged.\nIf you want to help improve Prism, please send this error to the developer.\n\nYou can contact the pipeline administrator or the developer, if you have any questions on this.\n\n"
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

				if os.path.exists(userErPath):
					with open(userErPath, "a") as erLog:
						erLog.write(text)

			if hasattr(self, "messageParent"):
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
			else:
				print (text)
			
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			print ("ERROR - writeErrorLog - %s - %s - %s\n\n" % (str(e), exc_type, exc_tb.tb_lineno))


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