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



try:
	from PySide2.QtCore import *
	from PySide2.QtGui import *
	from PySide2.QtWidgets import *
	psVersion = 2
except:
	from PySide.QtCore import *
	from PySide.QtGui import *
	psVersion = 1

import sys, os, shutil, time, traceback, platform
from functools import wraps

if sys.version[0] == "3":
	from configparser import ConfigParser
	pVersion = 3
else:
	from ConfigParser import ConfigParser
	pVersion = 2



class ExportClass(object):
	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - sm_default_export %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def setup(self, state, core, stateManager, node=None, stateData=None):
		self.state = state
		self.core = core
		self.stateManager = stateManager

		self.e_name.setText(state.text(0))

		self.className = "Export"
		self.listType = "Export"

		self.l_name.setVisible(False)
		self.e_name.setVisible(False)

		self.curCam = None

		self.oldPalette = self.b_changeTask.palette()
		self.warnPalette = QPalette()
		self.warnPalette.setColor(QPalette.Button, QColor(200, 0, 0))
		self.warnPalette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
		self.b_changeTask.setPalette(self.warnPalette)

		self.w_cam.setVisible(False)
		self.w_sCamShot.setVisible(False)
		self.w_selectCam.setVisible(False)
		self.w_localOutput.setVisible(self.core.useLocalFiles)

		self.nodes = []

		self.preDelete = lambda item: self.core.appPlugin.sm_export_preDelete(self)

		self.cb_outType.addItems(self.core.appPlugin.outputFormats)
		getattr(self.core.appPlugin, "sm_export_startup", lambda x: None)(self)
		self.nameChanged(state.text(0))
		self.connectEvents()

		if not self.stateManager.loading:
			getattr(self.core.appPlugin, "sm_export_addObjects", lambda x: None)(self)

		if stateData is not None:
			self.loadData(stateData)
		else:
			startFrame = self.core.appPlugin.getFrameRange(self)[0]
			self.sp_rangeStart.setValue(startFrame)
			self.sp_rangeEnd.setValue(startFrame)
			fileName = self.core.getCurrentFileName()
			fnameData = self.core.getScenefileData(fileName)
			sceneDir = self.core.getConfig('paths', "scenes", configPath=self.core.prismIni)
			if os.path.exists(fileName) and fnameData["type"] == "shot" and (os.path.join(self.core.projectPath, sceneDir) in fileName or (self.core.useLocalFiles and os.path.join(self.core.localProjectPath, sceneDir) in fileName)):
				idx = self.cb_sCamShot.findText(fnameData["shotName"])
				if idx != -1:
					self.cb_sCamShot.setCurrentIndex(idx)

		self.typeChanged(self.cb_outType.currentText())


	@err_decorator
	def loadData(self, data):
		if "taskname" in data:
			self.l_taskName.setText(data["taskname"])
			if data["taskname"] != "":
				self.b_changeTask.setPalette(self.oldPalette)
		if "connectednodes" in data:
			self.nodes = eval(data["connectednodes"])

		self.updateUi()

		if "statename" in data:
			self.e_name.setText(data["statename"])
		if "globalrange" in data:
			self.chb_globalRange.setChecked(eval(data["globalrange"]))
		if "startframe" in data:
			self.sp_rangeStart.setValue(int(data["startframe"]))
		if "endframe" in data:
			self.sp_rangeEnd.setValue(int(data["endframe"]))
		if "curoutputtype" in data:
			idx = self.cb_outType.findText(data["curoutputtype"])
			if idx != -1:
				self.cb_outType.setCurrentIndex(idx)
		if "wholescene" in data:
			self.chb_wholeScene.setChecked(eval(data["wholescene"]))
		if "localoutput" in data:
			self.chb_localOutput.setChecked(eval(data["localoutput"]))
		if "unitconvert" in data:
			self.chb_convertExport.setChecked(eval(data["unitconvert"]))
		if "additionaloptions" in data:
			self.chb_additionalOptions.setChecked(eval(data["additionaloptions"]))
		if "currentcam" in data:
			camName = getattr(self.core.appPlugin, "getCamName", lambda x, y:"")(self, data["currentcam"])
			idx = self.cb_cam.findText(camName)
			if idx != -1:
				self.curCam = self.camlist[idx]
				self.cb_cam.setCurrentIndex(idx)
				self.nameChanged(self.e_name.text())
		if "currentscamshot" in data:
			idx = self.cb_sCamShot.findText(data["currentscamshot"])
			if idx != -1:
				self.cb_sCamShot.setCurrentIndex(idx)
		if "lastexportpath" in data:
			lePath = self.core.fixPath(data["lastexportpath"])
			self.l_pathLast.setText(lePath)
			self.l_pathLast.setToolTip(lePath)
			pathIsNone = self.l_pathLast.text() == "None"
			self.b_openLast.setEnabled(not pathIsNone)
			self.b_copyLast.setEnabled(not pathIsNone)

		if "stateenabled" in data:
			self.state.setCheckState(0, eval(data["stateenabled"].replace("PySide.QtCore.", "").replace("PySide2.QtCore.", "")))

		getattr(self.core.appPlugin, "sm_export_loadData", lambda x, y: None)(self, data)


	@err_decorator
	def connectEvents(self):
		self.e_name.textChanged.connect(self.nameChanged)
		self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.b_changeTask.clicked.connect(self.changeTask)
		self.chb_globalRange.stateChanged.connect(self.rangeTypeChanged)
		self.sp_rangeStart.editingFinished.connect(self.startChanged)
		self.sp_rangeEnd.editingFinished.connect(self.endChanged)
		self.cb_outType.activated[str].connect(self.typeChanged)
		self.chb_wholeScene.stateChanged.connect(self.wholeSceneChanged)
		self.chb_localOutput.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.chb_convertExport.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.chb_additionalOptions.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.lw_objects.itemSelectionChanged.connect(lambda: self.core.appPlugin.selectNodes(self))
		self.lw_objects.customContextMenuRequested.connect(self.rcObjects)
		self.cb_cam.activated.connect(self.setCam)
		self.cb_sCamShot.activated.connect(self.stateManager.saveStatesToScene)
		self.b_selectCam.clicked.connect(lambda: self.core.appPlugin.selectCam(self))
		self.b_openLast.clicked.connect(lambda: self.core.openFolder(os.path.dirname(self.l_pathLast.text())))
		self.b_copyLast.clicked.connect(lambda: self.core.copyToClipboard(self.l_pathLast.text()))
		if not self.stateManager.standalone:
			self.b_add.clicked.connect(lambda: self.core.appPlugin.sm_export_addObjects(self))


	@err_decorator
	def rangeTypeChanged(self, state):
		checked = state == Qt.Checked
		self.l_rangeStart.setEnabled(not checked)
		self.l_rangeEnd.setEnabled(not checked)
		self.sp_rangeStart.setEnabled(not checked)
		self.sp_rangeEnd.setEnabled(not checked)
		self.stateManager.saveStatesToScene()


	@err_decorator
	def wholeSceneChanged(self, state):
		self.gb_objects.setEnabled(not state == Qt.Checked)
		self.updateUi()
		self.stateManager.saveStatesToScene()


	@err_decorator
	def nameChanged(self, text):
		if self.cb_outType.currentText() == "ShotCam":
			sText = text + " (ShotCam - %s)" % self.cb_cam.currentText()
		else:
			taskname = self.l_taskName.text()
			if taskname == "":
				taskname = "None"

			sText = text + " (%s)" % taskname
			
		if self.state.text(0).endswith(" - disabled"):
			sText += " - disabled"
			
		self.state.setText(0, sText)


	@err_decorator
	def setTaskname(self, taskname):
		prevTaskName = self.l_taskName.text()
		self.core.appPlugin.sm_export_setTaskText(self, prevTaskName, taskname)
		self.updateUi()


	@err_decorator
	def changeTask(self):
		import CreateItem
		self.nameWin = CreateItem.CreateItem(startText=self.l_taskName.text(), showTasks=True, taskType="export", core=self.core)
		self.core.parentWindow(self.nameWin)
		self.nameWin.setWindowTitle("Change Taskname")
		self.nameWin.l_item.setText("Taskname:")
		self.nameWin.e_item.selectAll()
		prevTaskName = self.l_taskName.text()
		result = self.nameWin.exec_()
		
		if result == 1:
			default_func = lambda x1, x2, newTaskName: self.l_taskName.setText(newTaskName)
			getattr(self.core.appPlugin, "sm_export_setTaskText", default_func)(self, prevTaskName, self.nameWin.e_item.text())
			self.b_changeTask.setPalette(self.oldPalette)
			self.nameChanged(self.e_name.text())
			self.stateManager.saveStatesToScene()


	@err_decorator
	def rcObjects(self, pos):
		item = self.lw_objects.itemAt(pos)

		if item is None:
			self.lw_objects.setCurrentRow(-1)

		createMenu = QMenu()

		if not item is None:
			actRemove = QAction("Remove", self)
			actRemove.triggered.connect(lambda: self.removeItem(item))
			createMenu.addAction(actRemove)
		else:
			self.lw_objects.setCurrentRow(-1)

		actClear = QAction("Clear", self)
		actClear.triggered.connect(self.clearItems)
		createMenu.addAction(actClear)

		self.updateUi()		
		createMenu.exec_(self.lw_objects.mapToGlobal(pos))


	@err_decorator
	def removeItem(self, item):
		items = self.lw_objects.selectedItems()
		for i in reversed(self.lw_objects.selectedItems()):
			rowNum = self.lw_objects.row(i)
			self.core.appPlugin.sm_export_removeSetItem(self, self.nodes[rowNum])
			del self.nodes[rowNum]
			self.lw_objects.takeItem(rowNum)

		self.updateUi()
		self.stateManager.saveStatesToScene()


	@err_decorator
	def clearItems(self):
		self.lw_objects.clear()
		self.nodes = []
		self.core.appPlugin.sm_export_clearSet(self)

		self.updateUi()
		self.stateManager.saveStatesToScene()


	@err_decorator
	def updateUi(self):
		self.cb_cam.clear()
		self.camlist = camNames = []
		if not self.stateManager.standalone:
			self.camlist = self.core.appPlugin.getCamNodes(self)
			camNames = [self.core.appPlugin.getCamName(self, i) for i in self.camlist]

		self.cb_cam.addItems(camNames)
		if self.curCam in self.camlist:
			self.cb_cam.setCurrentIndex(self.camlist.index(self.curCam))
		else:
			self.cb_cam.setCurrentIndex(0)
			if len(self.camlist) > 0:
				self.curCam = self.camlist[0]
			else:
				self.curCam = None
			self.stateManager.saveStatesToScene()

		curShot = self.cb_sCamShot.currentText()
		self.cb_sCamShot.clear()
		shotPath = os.path.join(self.core.projectPath, self.core.getConfig('paths', "scenes", configPath=self.core.prismIni), "Shots")
		shotNames = []
		omittedShots = []

		omitPath = os.path.join(os.path.dirname(self.core.prismIni), "Configs", "omits.ini")
		if os.path.exists(omitPath):
			oconfig = ConfigParser()
			oconfig.read(omitPath)

			if oconfig.has_section("Shot"):
				omittedShots = [x[1] for x in oconfig.items("Shot")]

		if os.path.exists(shotPath):
			shotNames += [x for x in os.listdir(shotPath) if not x.startswith("_") and x not in omittedShots]
		self.cb_sCamShot.addItems(shotNames)
		if curShot in shotNames:
			self.cb_sCamShot.setCurrentIndex(shotNames.index(curShot))
		else:
			self.cb_sCamShot.setCurrentIndex(0)
			self.stateManager.saveStatesToScene()

		selObjects = [x.text() for x in self.lw_objects.selectedItems()]
		self.lw_objects.clear()

		newObjList = []

		getattr(self.core.appPlugin, "sm_export_updateObjects", lambda x: None)(self)

		for node in self.nodes:
			if self.core.appPlugin.isNodeValid(self, node):
				item = QListWidgetItem(self.core.appPlugin.getNodeName(self, node))
				self.lw_objects.addItem(item)
				newObjList.append(node)

		if self.l_taskName.text() != "":
			self.b_changeTask.setPalette(self.oldPalette)

		if self.lw_objects.count() == 0 and not self.chb_wholeScene.isChecked():
			getattr(self.core.appPlugin, "sm_export_colorObjList", lambda x: self.lw_objects.setStyleSheet("QListWidget { border: 3px solid rgb(200,0,0); }") )(self)
		else:
			getattr(self.core.appPlugin, "sm_export_unColorObjList", lambda x: self.lw_objects.setStyleSheet("QListWidget { border: 3px solid rgb(114,114,114); }") )(self)

		for i in range(self.lw_objects.count()):
			if self.lw_objects.item(i).text() in selObjects:
				self.lw_objects.setCurrentItem(self.lw_objects.item(i))

		self.nodes = newObjList

		self.nameChanged(self.e_name.text())


	@err_decorator
	def typeChanged(self, idx):
		isSCam = idx == "ShotCam"
		self.w_cam.setVisible(isSCam)
		self.w_sCamShot.setVisible(isSCam)
		self.w_selectCam.setVisible(isSCam)
		self.w_taskname.setVisible(not isSCam)
		getattr(self.core.appPlugin, "sm_export_typeChanged", lambda x, y: None)(self, idx)
		self.w_wholeScene.setVisible(not isSCam)
		self.gb_objects.setVisible(not isSCam)

		self.updateUi()
		self.stateManager.saveStatesToScene()


	@err_decorator
	def setCam(self, index):
		self.curCam = self.camlist[index]
		self.updateUi()
		self.stateManager.saveStatesToScene()


	@err_decorator
	def startChanged(self):
		if self.sp_rangeStart.value() > self.sp_rangeEnd.value():
			self.sp_rangeEnd.setValue(self.sp_rangeStart.value())
		self.stateManager.saveStatesToScene()


	@err_decorator
	def endChanged(self):
		if self.sp_rangeEnd.value() < self.sp_rangeStart.value():
			self.sp_rangeStart.setValue(self.sp_rangeEnd.value())
		self.stateManager.saveStatesToScene()


	@err_decorator
	def preExecuteState(self):
		warnings = []

		if self.chb_globalRange.isChecked():
			startFrame = self.stateManager.sp_rangeStart.value()
			endFrame = self.stateManager.sp_rangeEnd.value()
		else:
			startFrame = self.sp_rangeStart.value()
			endFrame = self.sp_rangeEnd.value()

		if self.cb_outType.currentText() == "ShotCam":
			if self.curCam is None:
				warnings.append(["No camera specified.", "", 3])
		else:
			if self.l_taskName.text() == "":
				warnings.append(["No taskname is given.", "", 3])

			if not self.chb_wholeScene.isChecked() and len(self.nodes) == 0:
				warnings.append(["No objects are selected for export.", "", 3])

		warnings += self.core.appPlugin.sm_export_preExecute(self, startFrame, endFrame)

		return [self.state.text(0), warnings]


	@err_decorator
	def getOutputName(self, useVersion="next", startFrame=0, endFrame=0):
		prefUnit = self.core.appPlugin.preferredUnit

		fileName = self.core.getCurrentFileName()
		sceneDir = self.core.getConfig('paths', "scenes", configPath=self.core.prismIni)

		if self.cb_outType.currentText() == "ShotCam":
			outputBase = os.path.join(self.core.projectPath, sceneDir, "Shots", self.cb_sCamShot.currentText())

			if self.core.useLocalFiles and self.chb_localOutput.isChecked():
				outputBase = os.path.join(self.core.localProjectPath, sceneDir, "Shots", self.cb_sCamShot.currentText())

			fnameData = self.core.getScenefileData(fileName)

			comment = fnameData["comment"]
			versionUser = self.core.user

			outputPath = os.path.abspath(os.path.join(outputBase, "Export", "_ShotCam"))

			if useVersion != "next":
				versionData = useVersion.split(self.core.filenameSeperator)
				if len(versionData) == 3:
					hVersion, comment, versionUser = versionData
				else:
					useVersion == "next"

			if useVersion == "next":
				hVersion = self.core.getHighestTaskVersion(outputPath)
				
			outputPath = os.path.join(outputPath, hVersion + self.core.filenameSeperator + comment + self.core.filenameSeperator + versionUser, prefUnit)
			outputName = os.path.join(outputPath, "shot" + self.core.filenameSeperator + self.cb_sCamShot.currentText() + self.core.filenameSeperator + "ShotCam" + self.core.filenameSeperator + hVersion)

		else:
			if self.l_taskName.text() == "":
				return

			if startFrame == endFrame or self.cb_outType.currentText() != ".obj":
				fileNum = ""
			else:
				fileNum = ".####"

			basePath = self.core.projectPath
			if self.core.useLocalFiles:
				if self.chb_localOutput.isChecked():
					basePath = self.core.localProjectPath
					if fileName.startswith(os.path.join(self.core.projectPath, sceneDir)):
						fileName = fileName.replace(self.core.projectPath, self.core.localProjectPath)
				elif fileName.startswith(os.path.join(self.core.localProjectPath, sceneDir)):
					fileName = fileName.replace(self.core.localProjectPath, self.core.projectPath)

			versionUser = self.core.user
			hVersion = ""
			if useVersion != "next":
				versionData = useVersion.split(self.core.filenameSeperator)
				if len(versionData) == 3:
					hVersion, pComment, versionUser = versionData

			fnameData = self.core.getScenefileData(fileName)

			if fnameData["type"] == "shot":
				outputPath = os.path.join(self.core.getEntityBasePath(fileName), "Export", self.l_taskName.text())
				if hVersion == "":
					hVersion = self.core.getHighestTaskVersion(outputPath)
					pComment = fnameData["comment"]

				outputPath = os.path.join(outputPath, hVersion + self.core.filenameSeperator + pComment + self.core.filenameSeperator + versionUser, prefUnit)
				outputName = os.path.join(outputPath, "shot" + self.core.filenameSeperator + fnameData["shotName"] + self.core.filenameSeperator + self.l_taskName.text() + self.core.filenameSeperator + hVersion + fileNum + self.cb_outType.currentText())
			elif fnameData["type"] == "asset":
				if os.path.join(sceneDir, "Assets", "Scenefiles") in fileName:
					outputPath = os.path.join(self.core.fixPath(basePath), sceneDir, "Assets", "Export", self.l_taskName.text())
				else:
					outputPath = os.path.join(self.core.getEntityBasePath(fileName), "Export", self.l_taskName.text())
				if hVersion == "":
					hVersion = self.core.getHighestTaskVersion(outputPath)
					pComment = fnameData["comment"]

				outputPath = os.path.join(outputPath, hVersion + self.core.filenameSeperator + pComment + self.core.filenameSeperator + versionUser, prefUnit)
				outputName = os.path.join(outputPath, fnameData["assetName"] + self.core.filenameSeperator + self.l_taskName.text() + self.core.filenameSeperator + hVersion + fileNum + self.cb_outType.currentText())
			else:
				return

		return outputName, outputPath, hVersion


	@err_decorator
	def executeState(self, parent, useVersion="next"):
		if self.chb_globalRange.isChecked():
			startFrame = self.stateManager.sp_rangeStart.value()
			endFrame = self.stateManager.sp_rangeEnd.value()
		else:
			startFrame = self.sp_rangeStart.value()
			endFrame = self.sp_rangeEnd.value()

		if self.cb_outType.currentText() == "ShotCam":
			if self.curCam is None:
				return [self.state.text(0) + ": error - No camera specified. Skipped the activation of this state."]

			if self.cb_sCamShot.currentText() == "":
				return [self.state.text(0) + ": error - No Shot specified. Skipped the activation of this state."]

			fileName = self.core.getCurrentFileName()

			outputName, outputPath, hVersion = self.getOutputName(useVersion=useVersion)

			outLength = len(outputName)
			if platform.system() == "Windows" and outLength > 255:
				return [self.state.text(0) + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, taskname or projectpath." % outLength]

			if not os.path.exists(outputPath):
				os.makedirs(outputPath)

			self.core.callHook("preExport", args={"prismCore":self.core, "scenefile":fileName, "startFrame":startFrame, "endFrame":endFrame, "outputName":outputName})

			self.core.saveVersionInfo(location=os.path.dirname(outputPath), version=hVersion, origin=fileName, fps=startFrame!=endFrame)

			self.core.appPlugin.sm_export_exportShotcam(self, startFrame=startFrame, endFrame=endFrame, outputName=outputName)

			self.l_pathLast.setText(outputName)
			self.l_pathLast.setToolTip(outputName)
			self.b_openLast.setEnabled(True)
			self.b_copyLast.setEnabled(True)

			self.core.callHook("postExport", args={"prismCore":self.core, "scenefile":fileName, "startFrame":startFrame, "endFrame":endFrame, "outputName":outputName})

			self.stateManager.saveStatesToScene()

			if os.path.exists(outputName + ".abc"): # and os.path.exists(outputName + ".fbx"):
				return [self.state.text(0) + " - success"]
			else:
				return [self.state.text(0) + " - unknown error"]
		else:

			if self.l_taskName.text() == "":
				return [self.state.text(0) + ": error - No taskname is given. Skipped the activation of this state."]

			if not self.chb_wholeScene.isChecked() and len([x for x in self.nodes if self.core.appPlugin.isNodeValid(self, x)]) == 0:
				return [self.state.text(0) + ": error - No objects chosen. Skipped the activation of this state."]


			fileName = self.core.getCurrentFileName()

			outputName, outputPath, hVersion = self.getOutputName(useVersion=useVersion)

			outLength = len(outputName)
			if platform.system() == "Windows" and outLength > 255:
				return [self.state.text(0) + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, taskname or projectpath." % outLength]

			if not os.path.exists(outputPath):
				os.makedirs(outputPath)

			self.core.callHook("preExport", args={"prismCore":self.core, "scenefile":fileName, "startFrame":startFrame, "endFrame":endFrame, "outputName":outputName})

			self.core.saveVersionInfo(location=os.path.dirname(outputPath), version=hVersion, origin=fileName, fps=startFrame!=endFrame)

			try:
				outputName = self.core.appPlugin.sm_export_exportAppObjects(self, startFrame=startFrame, endFrame=endFrame, outputName=outputName)

				if outputName == False:
					return [self.state.text(0) + " - error"]

				if outputName.startswith("Canceled"):
					return [self.state.text(0) + " - error: %s" % outputName]

				self.l_pathLast.setText(outputName)
				self.l_pathLast.setToolTip(outputName)
				self.b_openLast.setEnabled(True)
				self.b_copyLast.setEnabled(True)

				self.stateManager.saveStatesToScene()

			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - sm_default_export %s:\n%s" % (time.strftime("%d/%m/%y %X"), self.core.version, traceback.format_exc()))
				self.core.writeErrorLog(erStr)
				return [self.state.text(0) + " - unknown error (view console for more information)"]

			self.core.callHook("postExport", args={"prismCore":self.core, "scenefile":fileName, "startFrame":startFrame, "endFrame":endFrame, "outputName":outputName})

			if os.path.exists(outputName):
				return [self.state.text(0) + " - success"]
			else:
				return [self.state.text(0) + " - unknown error (files do not exist)"]


	@err_decorator
	def getStateProps(self):
		stateProps = {}
		stateProps.update(getattr(self.core.appPlugin, "sm_export_getStateProps", lambda x: {})(self))
		stateProps.update({"statename":self.e_name.text(), "taskname":self.l_taskName.text(), "globalrange":str(self.chb_globalRange.isChecked()), "startframe":self.sp_rangeStart.value(), "endframe":self.sp_rangeEnd.value(), "unitconvert": str(self.chb_convertExport.isChecked()), "additionaloptions": str(self.chb_additionalOptions.isChecked())})
		stateProps.update({"curoutputtype": self.cb_outType.currentText(), "wholescene":str(self.chb_wholeScene.isChecked()), "localoutput": str(self.chb_localOutput.isChecked()), "connectednodes": str(self.nodes), "currentcam": str(self.curCam), "currentscamshot": self.cb_sCamShot.currentText(), "lastexportpath": self.l_pathLast.text().replace("\\", "/"), "stateenabled":str(self.state.checkState(0))})
		return stateProps