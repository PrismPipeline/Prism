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



import sys, os, subprocess, time, traceback, shutil, platform, copy
from functools import wraps

if platform.system() == "Windows":
	prismRoot = os.path.join(os.getenv('LocalAppdata'), "Prism")
elif platform.system() == "Linux":
	prismRoot = "/usr/local/Prism"
elif platform.system() == "Darwin":
	prismRoot = "/Applications/Prism/Prism"

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

for i in ["PrismSettings_ui", "PrismSettings_ui_ps2", "SetProject", "SetProject_ui", "SetProject_ui_ps2"]:
	try:
		del sys.modules[i]
	except:
		pass

sys.path.append(os.path.join(os.path.dirname(__file__), "UserInterfacesPrism"))

import SetProject

if psVersion == 1:
	import PrismSettings_ui
	import SetProject_ui
else:
	import PrismSettings_ui_ps2 as PrismSettings_ui
	import SetProject_ui_ps2 as SetProject_ui

if sys.version[0] == "3":
	pVersion = 3
else:
	pVersion = 2

from UserInterfacesPrism import qdarkstyle

class SetProjectImp(QDialog, SetProject_ui.Ui_dlg_setProject, SetProject.SetProjectClass):
	def __init__(self):
		QDialog.__init__(self)
		self.setupUi(self)


class PrismSettings(QDialog, PrismSettings_ui.Ui_dlg_PrismSettings):
	def __init__(self, core):
		QDialog.__init__(self)
		self.setupUi(self)

		self.core = core
		self.core.parentWindow(self)

		projectsUi = SetProjectImp()
		projectsUi.setup(self.core, self)
		projectsUi.l_project.setVisible(False)
		projectsUi.w_startup.setVisible(False)

		self.lo_projects.addWidget(projectsUi)

		self.groupboxes = [self.gb_curPversions]

		self.loadUI()
		self.core.plugin.prismSettings_loading(self)
		self.loadSettings()

		ss = QApplication.instance().styleSheet()
		for i in self.groupboxes:
			i.setStyleSheet(ss.replace("QCheckBox::indicator", "QGroupBox::indicator"))
		
		self.forceVersionsToggled(self.gb_curPversions.isChecked())
		for i in self.core.prjManagers.values():
			i.prismSettings_postLoadSettings(self)

		self.connectEvents()
		self.setFocus()

		screenH = QApplication.desktop().screenGeometry().height()
		space = 100 
		if screenH < (self.height()+space):
			self.resize(self.width(), screenH-space)


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - PrismSettings %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def connectEvents(self):
		self.e_fname.textChanged.connect(lambda x: self.validate(self.e_fname, x))
		self.e_lname.textChanged.connect(lambda x: self.validate(self.e_lname, x))
		self.b_browseLocal.clicked.connect(lambda: self.browse("local"))
		self.b_browseLocal.customContextMenuRequested.connect(lambda: self.core.openFolder(self.e_localPath.text()))
		self.e_curPname.textEdited.connect(self.curPnameEdited)
		self.chb_curPuseFps.toggled.connect(self.pfpsToggled)
		self.gb_curPversions.toggled.connect(self.forceVersionsToggled)
		for i in self.forceVersionPlugins:
			self.forceVersionPlugins[i]["b"].clicked.connect(lambda y=None, x=i: self.curPshowList(x))
		for i in self.exOverridePlugins:
			self.exOverridePlugins[i]["chb"].stateChanged.connect(lambda x, y=i: self.orToggled(y, x))
			self.exOverridePlugins[i]["b"].clicked.connect(lambda y=None, x=(i+"OR"): self.browse(x, getFile=True))
			self.exOverridePlugins[i]["b"].customContextMenuRequested.connect(lambda x, y=i: self.core.openFolder(self.exOverridePlugins[y]["le"].text()))
		for i in self.integrationPlugins:
			self.integrationPlugins[i]["badd"].clicked.connect(lambda y=None, x=i: self.integrationAdd(x))
			self.integrationPlugins[i]["bremove"].clicked.connect(lambda y=None, x=i: self.integrationRemove(x))
		self.b_about.clicked.connect(self.core.showAbout)
		self.b_startTray.clicked.connect(self.startTray)
		self.b_browseRV.clicked.connect(lambda: self.browse("rv"))
		self.b_browseRV.customContextMenuRequested.connect(lambda: self.core.openFolder(self.e_rvPath.text()))
		self.b_browseDJV.clicked.connect(lambda: self.browse("djv"))
		self.b_browseDJV.customContextMenuRequested.connect(lambda: self.core.openFolder(self.e_djvPath.text()))
		self.buttonBox.accepted.connect(self.saveSettings)


	@err_decorator
	def validate(self, uiWidget, origText=None):
		if origText is None:
			origText = uiWidget.text()
		text = self.core.validateStr(origText)

		if len(text) != len(origText):
			cpos = uiWidget.cursorPosition()
			uiWidget.setText(text)
			uiWidget.setCursorPosition(cpos-1)

		if len(self.e_fname.text()) > 0 and len(self.e_lname.text()) > 1:
			self.l_abbreviation.setText((self.e_fname.text()[0] + self.e_lname.text()[:2]).lower())
		else:
			self.l_abbreviation.setText("invalid")


	@err_decorator
	def pfpsToggled(self, checked):
		self.sp_curPfps.setEnabled(checked)


	@err_decorator
	def forceVersionsToggled(self, checked):
		self.w_versions.setVisible(checked)


	@err_decorator
	def browse(self, bType="", getFile=False, windowTitle=None, uiEdit=None):
		if bType == "local":
			windowTitle = "Select local project path"
			uiEdit = self.e_localPath
		elif bType == "rv":
			windowTitle = "Select RV path"
			uiEdit = self.e_rvPath
		elif bType == "djv":
			windowTitle = "Select DJV path"
			uiEdit = self.e_djvPath
		elif bType.endswith("OR"):
			pName = bType[:-2]
			windowTitle = "Select %s executable" % pName
			uiEdit = self.exOverridePlugins[pName]["le"]
		elif windowTitle is None or uiEdit is None:
			return

		if getFile:
			if platform.system() == "Windows":
				fStr = "Executable (*.exe)"
			else:
				fStr = "All files (*)"
				
			selectedPath = QFileDialog.getOpenFileName(self, windowTitle, uiEdit.text(), fStr)[0]
		else:
			selectedPath = QFileDialog.getExistingDirectory(self, windowTitle, uiEdit.text())

		if selectedPath != "":
			uiEdit.setText(self.core.fixPath(selectedPath))


	@err_decorator
	def orToggled(self, prog, state):
		self.exOverridePlugins[prog]["le"].setEnabled(state)
		self.exOverridePlugins[prog]["b"].setEnabled(state)


	@err_decorator
	def integrationAdd(self, prog):
		if prog == self.core.plugin.appName:
			result = self.core.plugin.integrationAdd(self)
		else:
			for i in self.core.unloadedPlugins:
				if i.appName == prog:
					result = i.integrationAdd(self)

		if result:
			result = self.core.fixPath(result)
			installConfigPath = os.path.join(os.path.dirname(self.core.userini), "installLocations.ini")
			existingPaths = []
			for i in range(self.integrationPlugins[prog]["lw"].count()):
				existingPaths.append(self.integrationPlugins[prog]["lw"].item(i).text())

			if result not in existingPaths:
				self.core.setConfig(configPath=installConfigPath, cat=prog, param="%02d" % (len(existingPaths)+1), val=result)
		
			self.refreshIntegrations()


	@err_decorator
	def integrationRemove(self, prog):
		items = self.integrationPlugins[prog]["lw"].selectedItems()
		if len(items) == 0:
			return

		installPath = items[0].text()

		if prog == self.core.plugin.appName:
			result = self.core.plugin.integrationRemove(self, installPath)
		else:
			for i in self.core.unloadedPlugins:
				if i.appName == prog:
					result = i.integrationRemove(self, installPath)

		if result:
			existingPaths = []
			for i in range(self.integrationPlugins[prog]["lw"].count()):
				existingPaths.append(self.integrationPlugins[prog]["lw"].item(i).text())

			installConfigPath = os.path.join(os.path.dirname(self.core.userini), "installLocations.ini")
			options = self.core.getConfig(cat=prog, configPath=installConfigPath, getOptions=True)
			cData = []
			for i in options:
				cData.append([prog, i, ""])

			self.core.setConfig(configPath=installConfigPath, data=cData, delete=True)

			existingPaths.pop(self.integrationPlugins[prog]["lw"].currentRow())
			cData = []
			for idx, i in enumerate(existingPaths):
				cData.append([prog, "%02d" % idx, i])

			self.core.setConfig(configPath=installConfigPath, data=cData)
			self.refreshIntegrations()


	@err_decorator
	def changeProject(self):
		self.core.setProject()
		self.close()


	@err_decorator
	def saveSettings(self):
		cData = []

		if len(self.e_fname.text()) > 0 and len(self.e_lname.text()) > 1:
			cData.append(['globals', "username", (self.e_fname.text() + " " + self.e_lname.text())])
			self.core.user = (self.e_fname.text()[0] + self.e_lname.text()[:2]).lower()

		if hasattr(self.core, "projectName") and self.e_localPath.isEnabled():
			lpath = self.core.fixPath(self.e_localPath.text())
			if not lpath.endswith(os.sep):
				lpath += os.sep

			cData.append(['localfiles', self.core.projectName, lpath])

		if self.e_localPath.text() != "disabled":
			self.core.localProjectPath = lpath

		rvPath = self.core.fixPath(self.e_rvPath.text())
		if rvPath != "" and not rvPath.endswith(os.sep):
			rvPath += os.sep
		cData.append(['globals', "rvpath", rvPath])

		djvPath = self.core.fixPath(self.e_djvPath.text())
		if djvPath != "" and not djvPath.endswith(os.sep):
			djvPath += os.sep
		cData.append(['globals', "djvpath", djvPath])

		cData.append(["globals", "prefer_djv", str(self.chb_preferDJV.isChecked())])
		cData.append(["globals", "showonstartup", str(self.chb_browserStartup.isChecked())])
		cData.append(["globals", "autosave", str(self.chb_autosave.isChecked())])
		cData.append(["globals", "highdpi", str(self.chb_highDPI.isChecked())])

		for i in self.exOverridePlugins:
			res = self.core.getPlugin(i).prismSettings_saveSettings(self)
			if type(res) == list:
				cData += res

		for i in self.exOverridePlugins:
			cData.append(['dccoverrides', "%s_override" % i, str(self.exOverridePlugins[i]["chb"].isChecked())])
			cData.append(['dccoverrides', "%s_path" % i, str(self.exOverridePlugins[i]["le"].text())])

		for i in self.core.prjManagers.values():
			res = i.prismSettings_saveSettings(self)
			if type(res) == list:
				cData += res

		if self.core.plugin.appType == "3d":
			if self.chb_autosave.isChecked():
				if not hasattr(self.core,  "asThread") or not self.core.asThread.isRunning():
					self.core.startasThread()
			else:
				self.core.startasThread(quit=True)

		self.core.setConfig(data=cData)

		if os.path.exists(self.core.prismIni):
			cData = []

			cData.append(['globals', 'project_name', (self.e_curPname.text())])
			cData.append(['globals', 'uselocalfiles', str(self.chb_curPuseLocal.isChecked())])
			cData.append(['globals', 'forcefps', str(self.chb_curPuseFps.isChecked())])
			cData.append(['globals', 'fps', str(self.sp_curPfps.value())])
			cData.append(['globals', 'forceversions', str(self.gb_curPversions.isChecked())])

			for i in self.core.prjManagers.values():
				res = i.prismSettings_savePrjSettings(self)
				if type(res) == list:
					cData += res

			for i in self.forceVersionPlugins:
				cData.append(['globals', "%s_version" % i, str(self.forceVersionPlugins[i]["le"].text())])

			self.core.setConfig(data=cData, configPath=self.core.prismIni)

			self.core.useLocalFiles = self.chb_curPuseLocal.isChecked()

			self.core.changeProject(self.core.prismIni)

		if platform.system() == "Windows":
			trayStartup = os.path.join(os.getenv('APPDATA'), "Microsoft", "Windows", "Start Menu", "Programs", "Startup", "PrismTray.lnk")
			trayLnk = os.path.join(os.getenv('LocalAppdata'), "Prism", "Tools", "PrismTray.lnk")

			if os.path.exists(trayStartup):
				os.remove(trayStartup)

			if self.chb_trayStartup.isChecked():
				if not os.path.exists(trayStartup):
					shutil.copy2(trayLnk, trayStartup)

		elif platform.system() == "Linux":
			trayStartup = "/etc/xdg/autostart/PrismTray.desktop"
			trayLnk = "/usr/local/Prism/Tools/PrismTray.desktop"
			if os.path.exists(trayStartup):
				os.remove(trayStartup)

			if self.chb_trayStartup.isChecked():
				if not os.path.exists(trayStartup):
					shutil.copy2(trayLnk, trayStartup)

		elif platform.system() == "Darwin":
			userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
			trayStartup = "/Users/%s/Library/LaunchAgents/com.user.PrismTray.plist" % userName
			trayLnk = "/Applications/Prism/Prism/Tools/com.user.PrismTray.plist"

			if os.path.exists(trayStartup):
				os.remove(trayStartup)

			if self.chb_trayStartup.isChecked():
				if not os.path.exists(trayStartup):
					shutil.copy2(trayLnk, trayStartup)
					os.chmod(trayStartup, 0o644)
					import pwd
					uid = pwd.getpwnam(userName).pw_uid
					os.chown(os.path.dirname(trayStartup), uid, -1)
					os.chown(trayStartup, uid, -1)
					os.system("launchctl load /Users/%s/Library/LaunchAgents/com.user.PrismTray.plist" % userName)


	@err_decorator
	def loadSettings(self):
		if not os.path.exists(self.core.userini):
			QMessageBox.warning(self,"loadSettings", "Prism config does not exist.")
			return

		if hasattr(self.core, "projectName"):
			self.l_projectName.setText(self.core.projectName)
		else:
			self.l_projectName.setText("No current project")

		if hasattr(self.core, "projectPath"):
			self.l_projectPath.setText(self.core.projectPath)
		else:
			self.l_projectPath.setText("")

		if hasattr(self.core, "useLocalFiles") and self.core.useLocalFiles and self.l_projectPath.text() != "":
			self.e_localPath.setText(self.core.localProjectPath)
		else:
			self.e_localPath.setText("disabled")
			self.e_localPath.setEnabled(False)
			self.b_browseLocal.setEnabled(False)

		if platform.system() == "Windows":
			trayStartupPath = os.path.join(os.getenv('APPDATA'), "Microsoft", "Windows", "Start Menu", "Programs", "Startup", "PrismTray.lnk")
		elif platform.system() == "Linux":
			trayStartupPath = "/etc/xdg/autostart/PrismTray.desktop"
		elif platform.system() == "Darwin":
			userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
			trayStartupPath = "/Users/%s/Library/LaunchAgents/com.user.PrismTray.plist" % userName

		self.chb_trayStartup.setChecked(os.path.exists(trayStartupPath))

		ucData = {}

		for i in self.exOverridePlugins:
			ucData["%s_override" % i] = ["dccoverrides", "%s_override" % i, "bool"]
			ucData["%s_path" % i] = ["dccoverrides", "%s_path" % i]

		ucData["username"] = ['globals', "username"]
		ucData["showonstartup"] = ['globals', "showonstartup", "bool"]
		ucData["autosave"] = ['globals', "autosave", "bool"]
		ucData["highdpi"] = ['globals', "highdpi", "bool"]
		ucData["rvpath"] = ['globals', "rvpath"]
		ucData["djvpath"] = ['globals', "djvpath"]
		ucData["prefer_djv"] = ['globals', "prefer_djv", "bool"]

		loadFunctions = {}
		for i in self.exOverridePlugins:
			res = self.core.getPlugin(i).prismSettings_loadSettings(self)
			if type(res) == tuple:
				loadData, pLoadFunctions = res
				ucData.update(loadData)
				loadFunctions.update(pLoadFunctions)

		for i in self.core.prjManagers.values():
			res = i.prismSettings_loadSettings(self)
			if type(res) == tuple:
				loadData, pLoadFunctions = res
				ucData.update(loadData)
				loadFunctions.update(pLoadFunctions)

		ucData = self.core.getConfig(data=ucData)

		if ucData["username"] is not None:
			uname = ucData["username"].split()
			
			if len(uname) == 2:	
				self.e_fname.setText(uname[0])
				self.e_lname.setText(uname[1])

				self.validate(uiWidget=self.e_fname)
				self.validate(uiWidget =self.e_lname)

		if ucData["showonstartup"] is not None:
			self.chb_browserStartup.setChecked(ucData["showonstartup"])

		for i in sorted(loadFunctions):
			if ucData[i] is not None:
				loadFunctions[i](ucData[i])

		if ucData["autosave"] is not None:
			self.chb_autosave.setChecked(ucData["autosave"])

		if ucData["highdpi"] is not None:
			self.chb_highDPI.setChecked(ucData["highdpi"])

		if ucData["rvpath"] is not None:
			self.e_rvPath.setText(ucData["rvpath"])

		if ucData["djvpath"] is not None:
			self.e_djvPath.setText(ucData["djvpath"])

		if ucData["prefer_djv"] is not None:
			self.chb_preferDJV.setChecked(ucData["prefer_djv"])		

		for i in self.exOverridePlugins:
			if ucData["%s_override" % i] is not None:
				self.exOverridePlugins[i]["chb"].setChecked(ucData["%s_override" % i])

			if ucData["%s_path" % i] is not None:	
				self.exOverridePlugins[i]["le"].setText(ucData["%s_path" % i])

			if not self.exOverridePlugins[i]["chb"].isChecked() and self.exOverridePlugins[i]["le"].text() == "":
				execFunc = self.core.getPluginData(i, "getExecutable")
				if execFunc is not None:
					examplePath = execFunc()
					if examplePath is not None:
						if not os.path.exists(examplePath) and os.path.exists(os.path.dirname(examplePath)):
							examplePath = os.path.dirname(examplePath)

						self.exOverridePlugins[i]["le"].setText(examplePath)

			self.exOverridePlugins[i]["le"].setEnabled(self.exOverridePlugins[i]["chb"].isChecked())
			self.exOverridePlugins[i]["b"].setEnabled(self.exOverridePlugins[i]["chb"].isChecked())

		if os.path.exists(self.core.prismIni):
			pcData = {}

			for i in self.forceVersionPlugins:
				pcData["%s_version" % i] = ["globals", "%s_version" % i]

			pcData["pName"] = ["globals", "project_name"]
			pcData["lFiles"] = ["globals", "uselocalfiles"]
			pcData["fpfps"] = ["globals", "forcefps"]
			pcData["pfps"] = ["globals", "fps"]
			pcData["fVersion"] = ["globals", "forceversions"]

			loadFunctions = {}

			for i in self.core.prjManagers.values():
				res = i.prismSettings_loadPrjSettings(self)
				if type(res) == tuple:
					loadData, pLoadFunctions = res
					pcData.update(loadData)
					loadFunctions.update(pLoadFunctions)

			pcData = self.core.getConfig(data=pcData, configPath=self.core.prismIni)

			if pcData["pName"] is not None:
				self.e_curPname.setText(pcData["pName"])
			if pcData["lFiles"] is not None:
				self.chb_curPuseLocal.setChecked(eval(pcData["lFiles"]))
			if pcData["fpfps"] is not None:
				self.chb_curPuseFps.setChecked(eval(pcData["fpfps"]))
			if pcData["pfps"] is not None:
				self.sp_curPfps.setValue(float(pcData["pfps"]))
			if pcData["fVersion"] is not None:
				self.gb_curPversions.setChecked(eval(pcData["fVersion"]))

			for i in sorted(loadFunctions):
				if pcData[i] is not None:
					loadFunctions[i](pcData[i])

			for i in self.forceVersionPlugins:
				if pcData["%s_version" % i] is not None:
					self.forceVersionPlugins[i]["le"].setText(pcData["%s_version" % i])

		else:
			self.l_localPath.setEnabled(False)
			self.w_prjSettings.setEnabled(False)

		self.pfpsToggled(self.chb_curPuseFps.isChecked())
		self.w_curPfps.setToolTip("When this option is enabled, Prism checks the fps of scenefiles when they are opened and shows a warning, if they don't match the project fps.")


	@err_decorator
	def loadUI(self):
		self.forceVersionPlugins = {}
		self.exOverridePlugins = {}
		self.integrationPlugins = {}
		self.dccTabs = QTabWidget()

		pluginNames = self.core.getPluginNames()
		for i in pluginNames:
			pVPresets = self.core.getPluginData(i, "appVersionPresets")
			if pVPresets is not None:

				w_pVersion = QWidget()
				lo_pVersion = QHBoxLayout()

				l_pName = QLabel(i)
				le_pVersion = QLineEdit(pVPresets[0])
				le_pVersion.setMinimumSize(100,0)
				le_pVersion.setMaximumSize(100,100)

				if pVersion == 2:
					bStr = unicode("▼", "utf-8")
				else:
					bStr = "▼"

				b_pShowVersions = QPushButton(bStr)
				b_pShowVersions.setMaximumSize(25,100)

				lo_pVersion.addWidget(l_pName)
				lo_pVersion.addStretch()
				lo_pVersion.addWidget(le_pVersion)
				lo_pVersion.addWidget(b_pShowVersions)

				lo_pVersion.setContentsMargins(9,0,9,0)
				w_pVersion.setLayout(lo_pVersion)

				self.w_versions.layout().addWidget(w_pVersion)
				#x = copy.deepcopy(b_pShowVersions)
				self.forceVersionPlugins[i] = {"le": le_pVersion, "b": b_pShowVersions, "presets": pVPresets}

			pAppType = self.core.getPluginData(i, "appType")
			if pAppType != "standalone":
				tab = QWidget()
				w_ovr = QWidget()
				lo_tab = QVBoxLayout()
				lo_ovr = QHBoxLayout()
				tab.setLayout(lo_tab)
				w_ovr.setLayout(lo_ovr)
				lo_tab.setContentsMargins(15,15,15,15)
				lo_ovr.setContentsMargins(0,9,0,9)
			#	w_ovr.setMinimumSize(0,39)

				if self.core.getPluginData(i, "canOverrideExecuteable") != False:
					l_ovr = QLabel("By default Prism uses the default application configured in Windows to open scenefiles.\nThe following setting let you override this behaviour by defining explicit applications for opening scenefiles.")
					chb_ovr = QCheckBox("Executable override")
					le_ovr = QLineEdit()
					b_ovr = QPushButton("...")
					b_ovr.setMinimumWidth(40)
					b_ovr.setMaximumWidth(40)
					b_ovr.setContextMenuPolicy(Qt.CustomContextMenu)

					lo_ovr.addWidget(chb_ovr)
					lo_ovr.addWidget(le_ovr)
					lo_ovr.addWidget(b_ovr)

					lo_tab.addWidget(l_ovr)
					lo_tab.addWidget(w_ovr)

					self.exOverridePlugins[i] = {"chb":chb_ovr, "le": le_ovr, "b": b_ovr}

				gb_integ = QGroupBox("Prism integrations")
				lo_integ = QVBoxLayout()
				gb_integ.setLayout(lo_integ)
				lw_integ = QListWidget()
				w_integ = QWidget()
				lo_integButtons = QHBoxLayout()
				b_addInteg = QPushButton("Add")
				b_removeInteg = QPushButton("Remove")

				w_integ.setLayout(lo_integButtons)
				lo_integButtons.addStretch()
				lo_integButtons.addWidget(b_addInteg)
				lo_integButtons.addWidget(b_removeInteg)

				lo_integ.addWidget(lw_integ)
				lo_integ.addWidget(w_integ)
				lo_tab.addWidget(gb_integ)

				lw_integ.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed))

				self.integrationPlugins[i] = {"lw":lw_integ, "badd": b_addInteg, "bremove": b_removeInteg}

				self.core.getPlugin(i).prismSettings_loadUI(self, tab)

				lo_tab.addStretch()

				self.dccTabs.addTab(tab, i)

		if self.dccTabs.count() > 0:
			self.tab_dccApps.layout().addWidget(self.dccTabs)

		self.refreshIntegrations()

		self.tab_dccApps.layout().addStretch()

		for i in self.core.prjManagers.values():
			i.prismSettings_loadUI(self)


	@err_decorator
	def refreshIntegrations(self):
		installConfigPath = os.path.join(os.path.dirname(self.core.userini), "installLocations.ini")
		installConfig = None
		if  os.path.exists(installConfigPath):
			installConfig = self.core.getConfig(configPath=installConfigPath, getConf=True)

		for i in self.integrationPlugins:
			installPaths = []
			if installConfig is not None and installConfig.has_section(i):
				opt = installConfig.options(i)
				for k in opt:
					installPaths.append(installConfig.get(i, k))

			self.integrationPlugins[i]["lw"].clear()

			for k in installPaths:
				item = QListWidgetItem(k)
				self.integrationPlugins[i]["lw"].addItem(item)

			if len(installPaths) > 0:
				self.integrationPlugins[i]["lw"].setCurrentRow(0)
				self.integrationPlugins[i]["bremove"].setEnabled(True)
			else:
				self.integrationPlugins[i]["bremove"].setEnabled(False)



	@err_decorator
	def curPnameEdited(self, text):
		self.validate(self.e_curPname)


	@err_decorator
	def curPshowList(self, prog):
		versionList = self.forceVersionPlugins[prog]["presets"]

		vmenu = QMenu()

		for i in versionList:
			tAct = QAction(i, self)
			tAct.triggered.connect(lambda x=None, t=i: self.forceVersionPlugins[prog]["le"].setText(t))
			vmenu.addAction(tAct)

		self.core.plugin.setRCStyle(self, vmenu)

		vmenu.exec_(QCursor.pos())


	@err_decorator
	def startTray(self):
		if platform.system() == "Windows":
			command = '\"%s\\Prism\\Python27\\PrismTray.exe\" \"%s\\Prism\\Scripts\\PrismTray.py\"' % (os.getenv('LocalAppdata'), os.getenv('LocalAppdata'))
		elif platform.system() == "Linux":
			command = 'bash /usr/local/Prism/Tools/PrismTray.sh'
		elif platform.system() == "Darwin":
			command = 'bash /Applications/Prism/Prism/Tools/PrismTray.sh'

		subprocess.Popen(command, shell=True)


	@err_decorator
	def enterEvent(self, event):
		QApplication.restoreOverrideCursor()



if __name__ == "__main__":
	qapp = QApplication(sys.argv)
	qapp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))
	appIcon = QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "UserInterfacesPrism", "p_tray.png"))
	qapp.setWindowIcon(appIcon)
	import PrismCore
	pc = PrismCore.PrismCore()
	pPath = pc.getConfig("globals", "current project")
	if pPath is not None and pPath != "":
		pc.changeProject(pc.getConfig("globals", "current project"))
	pc.prismSettings()
	qapp.exec_()