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



try:
	from PySide2.QtCore import *
	from PySide2.QtGui import *
	from PySide2.QtWidgets import *
	psVersion = 2
except:
	from PySide.QtCore import *
	from PySide.QtGui import *
	psVersion = 1

import sys, os, time, traceback
from functools import wraps

if sys.version[0] == "3":
	from configparser import ConfigParser
	pVersion = 3
else:
	from ConfigParser import ConfigParser
	pVersion = 2



class ImportFileClass(object):
	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - sm_default_importFile %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].stateManager.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def setup(self, state, core, stateManager, node=None, importPath=None, stateData=None):
		self.state = state
		self.e_name.setText(state.text(0))

		self.className = "ImportFile"
		self.listType = "Import"

		self.l_name.setVisible(False)
		self.e_name.setVisible(False)

		self.core = core
		self.stateManager = stateManager
		self.importPath = None
		self.taskName = ""
		self.setName = ""
		self.importPath = importPath

		self.nodes = []
		self.nodeNames = []

		self.f_abcPath.setVisible(False)
		self.f_keepRefEdits.setVisible(False)
		self.updatePrefUnits()

		self.oldPalette = self.b_importLatest.palette()
		self.updatePalette = QPalette()
		self.updatePalette.setColor(QPalette.Button, QColor(200, 100, 0))
		self.updatePalette.setColor(QPalette.ButtonText, QColor(255, 255, 255))

		if importPath is None and stateData is None:
			import TaskSelection
			ts = TaskSelection.TaskSelection(core = core, importState = self)

			core.parentWindow(ts)
			ts.exec_()

		if self.importPath is not None:
			self.e_file.setText(self.importPath[1])
			result = self.importObject(taskName=self.importPath[0])
			self.importPath = None

			if not result:
				return False
		elif stateData is None:
			return False

		self.core.appPlugin.sm_import_startup(self)
		self.connectEvents()

		if stateData is not None:
			self.loadData(stateData)

		self.nameChanged(state.text(0))


	@err_decorator
	def loadData(self, data):
		if "statename" in data:
			self.e_name.setText(data["statename"])
		if "filepath" in data:
			data["filepath"] = getattr(self.core.appPlugin, "sm_import_fixImportPath", lambda x,y:y)(self, data["filepath"])
			self.e_file.setText(data["filepath"])
		if "keepedits" in data:
			self.chb_keepRefEdits.setChecked(eval(data["keepedits"]))
		if "autonamespaces" in data:
			self.chb_autoNameSpaces.setChecked(eval(data["autonamespaces"]))
		if "updateabc" in data:
			self.chb_abcPath.setChecked(eval(data["updateabc"]))
		if "preferunit" in data:
			self.chb_preferUnit.setChecked(eval(data["preferunit"]))
			self.updatePrefUnits()
		if "connectednodes" in data:
			self.nodes = [x[1] for x in eval(data["connectednodes"]) if self.core.appPlugin.isNodeValid(self, x[1])]
		if "taskname" in data:
			self.taskName = data["taskname"]
		if "nodenames" in data:
			self.nodeNames = eval(data["nodenames"])
		if "setname" in data:
			self.setName = data["setname"]


	@err_decorator
	def connectEvents(self):
		self.e_name.textChanged.connect(self.nameChanged)
		self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.e_file.editingFinished.connect(self.pathChanged)
		self.b_browse.clicked.connect(self.browse)
		self.b_browse.customContextMenuRequested.connect(self.openFolder)
		self.b_import.clicked.connect(self.importObject)
		self.b_importLatest.clicked.connect(self.importLatest)
		self.b_nameSpaces.clicked.connect(lambda: self.core.appPlugin.sm_import_removeNameSpaces(self))
		self.b_unitConversion.clicked.connect(lambda: self.core.appPlugin.sm_import_unitConvert(self))
		self.chb_keepRefEdits.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.chb_autoNameSpaces.stateChanged.connect(self.autoNameSpaceChanged)
		self.chb_abcPath.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.chb_preferUnit.stateChanged.connect(lambda x: self.updatePrefUnits())
		self.chb_preferUnit.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.lw_objects.itemSelectionChanged.connect(lambda: self.core.appPlugin.selectNodes(self))


	@err_decorator
	def nameChanged(self, text):
		getattr(self.core.appPlugin, "sm_import_nameChanged", lambda x:None)(self)

		if self.taskName != "":
			self.state.setText(0, text + " (" + self.taskName + ")")
		else:
			self.state.setText(0, text)


	@err_decorator
	def browse(self):		
		import TaskSelection

		ts = TaskSelection.TaskSelection(core = self.core, importState = self)

		self.core.parentWindow(ts)
		ts.exec_()

		if self.importPath is not None:
			self.e_file.setText(self.importPath[1])
			self.importObject(taskName=self.importPath[0])
			self.updateUi()
			self.importPath = None


	@err_decorator
	def openFolder(self, pos):
		path = self.e_file.text()
		if os.path.isfile(path):
			path = os.path.dirname(path)

		self.core.openFolder(path)


	@err_decorator
	def pathChanged(self):
		self.stateManager.saveImports()
		self.updateUi()
		self.stateManager.saveStatesToScene()


	@err_decorator
	def autoNameSpaceChanged(self, checked):
		self.b_nameSpaces.setEnabled(not checked)
		self.core.appPlugin.sm_import_removeNameSpaces(self)
		self.stateManager.saveStatesToScene()


	@err_decorator
	def importObject(self, taskName=None, update=False):
		if self.e_file.text() != "":
			versionInfoPath = os.path.join(os.path.dirname(os.path.dirname(self.e_file.text())), "versioninfo.ini")
			if os.path.exists(versionInfoPath):
				vConfig = ConfigParser()
				vConfig.read(versionInfoPath)
				if vConfig.has_option("information", "fps"):
					impFPS = float(vConfig.get("information", "fps"))
					curFPS = self.core.getFPS()
					if impFPS != curFPS:
						fString = "The FPS of the import doesn't match the FPS of the current scene:\n\nCurrent scene FPS:    %s\nImport FPS:                %s" % (curFPS, impFPS)
						msg = QMessageBox(QMessageBox.Warning, "FPS mismatch", fString, QMessageBox.Cancel)
						msg.addButton("Continue", QMessageBox.YesRole)
						self.core.parentWindow(msg)
						action = msg.exec_()

						if action != 0:
							return False

			if taskName is None:
				vPath = os.path.dirname(self.e_file.text())
				if os.path.basename(vPath) in ["centimeter", "meter"]:
					vName = os.path.basename(os.path.dirname(vPath))
					vPath = os.path.dirname(vPath)
				else:
					vName = os.path.basename(vPath)

				self.taskName = ""
				sceneDir = self.core.getConfig('paths', "scenes", configPath=self.core.prismIni)
				if len(vName.split(self.core.filenameSeperator)) == 3 and (os.path.join(self.core.projectPath, sceneDir) in self.e_file.text() or (self.core.useLocalFiles and os.path.join(self.core.localProjectPath, sceneDir) in self.e_file.text())):
					self.taskName = os.path.basename(os.path.dirname(vPath))
					if self.taskName == "_ShotCam":
						self.taskName = "ShotCam"
				else:
					self.taskName = vName
			else:
				self.taskName = taskName

			doImport = True

			impFileName = self.e_file.text()
			parDirName = os.path.basename(os.path.dirname(impFileName))
			if parDirName in ["centimeter", "meter"]:
				prefFile = os.path.join(os.path.dirname(os.path.dirname(impFileName)), self.preferredUnit, os.path.basename(impFileName))
				if parDirName == self.unpreferredUnit and os.path.exists(prefFile):
					impFileName = prefFile
					self.e_file.setText(impFileName)

			self.core.appPlugin.sm_import_updateObjects(self)

			fileName = self.core.getCurrentFileName()

			self.core.callHook("preImport", args={"prismCore":self.core, "scenefile":fileName, "importfile":impFileName})

			result, doImport = self.core.appPlugin.sm_import_importToApp(self, doImport=doImport, update=update, impFileName=impFileName)

			if doImport:
				self.nodeNames = [self.core.appPlugin.getNodeName(self, x) for x in self.nodes]

				if self.chb_autoNameSpaces.isChecked():
					self.core.appPlugin.sm_import_removeNameSpaces(self)

				if not result:
					QMessageBox.warning(self.core.messageParent, "ImportFile", "Import failed.")

			self.core.callHook("postImport", args={"prismCore":self.core, "scenefile":fileName, "importfile":impFileName, "importedObjects":self.nodeNames})

		self.stateManager.saveImports()
		self.updateUi()
		self.stateManager.saveStatesToScene()

		return True


	@err_decorator
	def importLatest(self):
		self.updateUi()
		vPath = os.path.dirname(self.e_file.text())
		if os.path.basename(vPath) in ["centimeter", "meter"]:
			vPath = os.path.dirname(vPath)

		versionPath = os.path.join(os.path.dirname(vPath), self.l_latestVersion.text())
		if os.path.exists(versionPath):
			pPath = os.path.join(versionPath, self.preferredUnit)
			upPath = os.path.join(versionPath, self.unpreferredUnit)
			if os.path.exists(pPath) and len(os.listdir(pPath)) > 0:
				versionPath = pPath
			elif os.path.exists(upPath) and len(os.listdir(upPath)) > 0:
				versionPath = upPath

			for i in os.walk(versionPath):
				if len(i[2]) > 0:
					fileName = os.path.join(i[0], i[2][0])

					if getattr(self.core.appPlugin, "shotcamFormat", ".abc") == ".fbx"  and self.taskName == "ShotCam" and fileName.endswith(".abc") and os.path.exists(fileName[:-3] + "fbx"):
						fileName = fileName[:-3] + "fbx"
					if fileName.endswith(".mtl") and os.path.exists(fileName[:-3] + "obj"):
						fileName = fileName[:-3] + "obj"

					self.e_file.setText(fileName)
					self.importObject(update=True)
				break


	@err_decorator
	def updateUi(self):
		if os.path.exists(self.e_file.text()):
			parDir = os.path.dirname(self.e_file.text())
			if os.path.basename(parDir) in ["centimeter", "meter"]:
				versionData = os.path.basename(os.path.dirname(parDir)).split(self.core.filenameSeperator)
			else:
				versionData = os.path.basename(parDir).split(self.core.filenameSeperator)

			fversionData = os.path.basename(self.e_file.text()).split(self.core.filenameSeperator)
			fversion = None
			for i in fversionData:
				try:
					num = int(i[1:])
				except:
					num = None
				if len(i) == 5 and i[0] == "v" and num is not None:
					try:
						x = int(i[1:])
						fversion = i
						break
					except:
						pass
						
			if len(versionData) == 3 and self.core.getConfig('paths', "scenes", configPath=self.core.prismIni) in self.e_file.text():
				self.l_curVersion.setText(versionData[0] + self.core.filenameSeperator + versionData[1] + self.core.filenameSeperator + versionData[2])
				self.l_latestVersion.setText("-")
				vPath = os.path.dirname(self.e_file.text())
				if os.path.basename(vPath) in ["centimeter", "meter"]:
					vPath = os.path.dirname(vPath)

				taskPath = os.path.dirname(vPath)
				for i in os.walk(taskPath):
					folders = i[1]
					folders.sort()
					for k in reversed(folders):
						meterDir = os.path.join(i[0], k, "meter")
						cmeterDir = os.path.join(i[0], k, "centimeter")
						if len(k.split(self.core.filenameSeperator)) == 3 and k[0] == "v" and len(k.split(self.core.filenameSeperator)[0]) == 5 and ((os.path.exists(meterDir) and len(os.listdir(meterDir)) > 0) or (os.path.exists(cmeterDir) and len(os.listdir(cmeterDir)) > 0)):
							self.l_latestVersion.setText(k)
							break
					break

			else:
				self.l_curVersion.setText("-")
				self.l_latestVersion.setText("-")

			useSS = getattr(self.core.appPlugin, "colorButtonWithStyleSheet", False)
			if self.l_curVersion.text() != self.l_latestVersion.text() and self.l_curVersion.text() != "-" and self.l_latestVersion.text() != "-":
				if useSS:
					self.b_importLatest.setStyleSheet("QPushButton { background-color: rgb(200,100,0); }")
				else:
					self.b_importLatest.setPalette(self.updatePalette)
			else:
				if useSS:
					self.b_importLatest.setStyleSheet("")
				else:
					self.b_importLatest.setPalette(self.oldPalette)
		else:
			self.l_curVersion.setText("-")
			self.l_latestVersion.setText("-")

		self.lw_objects.clear()

		self.core.appPlugin.sm_import_updateObjects(self)

		for i in self.nodes:
			item = QListWidgetItem(self.core.appPlugin.getNodeName(self, i))
			getattr(self.core.appPlugin, "sm_import_updateListItem", lambda x,y, z:None)(self, item, i)

			self.lw_objects.addItem(item)

		self.nameChanged(self.e_name.text())


	@err_decorator
	def updatePrefUnits(self):
		pref = self.core.appPlugin.preferredUnit
		if self.chb_preferUnit.isChecked():
			if pref == "centimeter":
				pref = "meter"
			else:
				pref = "centimeter"

		if pref == "centimeter":
			self.preferredUnit = "centimeter"
			self.unpreferredUnit = "meter"
		else:
			self.preferredUnit = "meter"
			self.unpreferredUnit = "centimeter"
		

	@err_decorator
	def preDelete(self, item=None, baseText="Do you also want to delete the connected objects?\n\n"):
		if len(self.nodes) > 0:
			message = baseText
			validNodes = [ x for x in self.nodes if self.core.appPlugin.isNodeValid(self, x)]
			if len(validNodes) > 0:
				for idx, val in enumerate(validNodes):
					if idx > 5:
						message += "..."
						break
					else:
						message += self.core.appPlugin.getNodeName(self, val) + "\n"

				msg = QMessageBox(QMessageBox.Question, "Delete state", message, QMessageBox.No)
				msg.addButton("Yes", QMessageBox.YesRole)
				msg.setParent(self.core.messageParent, Qt.Window)
				action = msg.exec_()

				if action == 0:
					self.core.appPlugin.deleteNodes(self, validNodes)


	@err_decorator
	def getStateProps(self):
		connectedNodes = []
		for i in range(self.lw_objects.count()):
			connectedNodes.append([str(self.lw_objects.item(i).text()), self.nodes[i]])

		return {"statename":self.e_name.text(), "filepath": self.e_file.text().replace("\\","\\\\"), "keepedits": str(self.chb_keepRefEdits.isChecked()), "autonamespaces": str(self.chb_autoNameSpaces.isChecked()), "updateabc": str(self.chb_abcPath.isChecked()), "preferunit": str(self.chb_preferUnit.isChecked()), "connectednodes": str(connectedNodes), "taskname":self.taskName, "nodenames":str(self.nodeNames), "setname":self.setName}