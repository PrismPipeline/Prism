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



class PlayblastClass(object):
	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - sm_default_playblast %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def setup(self, state, core, stateManager, stateData=None):
		self.state = state
		self.core = core
		self.stateManager = stateManager

		self.curCam = None
		self.className = "Playblast"
		self.listType = "Export"

		self.e_name.setText(state.text(0))

		self.l_name.setVisible(False)
		self.e_name.setVisible(False)

		self.camlist = []

		self.resolutionPresets = ["1920x1080", "1280x720", "640x360", "4000x2000", "2000x1000"]
		self.outputformats = ["jpg", "mp4"]

		self.cb_formats.addItems(self.outputformats)

		self.connectEvents()

		self.oldPalette = self.b_changeTask.palette()
		self.warnPalette = QPalette()
		self.warnPalette.setColor(QPalette.Button, QColor(200, 0, 0))
		self.warnPalette.setColor(QPalette.ButtonText, QColor(255, 255, 255))

		self.setTaskWarn(True)

		self.f_localOutput.setVisible(self.core.useLocalFiles)

		self.updateUi()
		if stateData is not None:
			self.loadData(stateData)
			

	@err_decorator
	def loadData(self, data):
		if "statename" in data:
			self.e_name.setText(data["statename"])
		if "taskname" in data:
			self.l_taskName.setText(data["taskname"])
			if data["taskname"] != "":
				self.setTaskWarn(False)
				self.nameChanged(self.e_name.text())
		if "globalrange" in data:
			self.chb_globalRange.setChecked(eval(data["globalrange"]))
		if "startframe" in data:
			self.sp_rangeStart.setValue(int(data["startframe"]))
		if "endframe" in data:
			self.sp_rangeEnd.setValue(int(data["endframe"]))
		if "currentcam" in data:
			camName = getattr(self.core.appPlugin, "getCamName", lambda x, y:"")(self, data["currentcam"])
			idx = self.cb_cams.findText(camName)
			if idx > 0:
				self.curCam = self.camlist[idx-1]
				self.cb_cams.setCurrentIndex(idx)
				self.stateManager.saveStatesToScene()
		if "resoverride" in data:
			res = eval(data["resoverride"])
			self.chb_resOverride.setChecked(res[0])
			self.sp_resWidth.setValue(res[1])
			self.sp_resHeight.setValue(res[2])
		if "localoutput" in data:
			self.chb_localOutput.setChecked(eval(data["localoutput"]))
		if "outputformat" in data:
			idx = self.cb_formats.findText(data["outputformat"])
			if idx > 0:
				self.cb_formats.setCurrentIndex(idx)
		if "lastexportpath" in data:
			lePath = self.core.fixPath(data["lastexportpath"])
			self.l_pathLast.setText(lePath)
			self.l_pathLast.setToolTip(lePath)
			pathIsNone = self.l_pathLast.text() == "None"
			self.b_openLast.setEnabled(not pathIsNone)
			self.b_copyLast.setEnabled(not pathIsNone)
		if "stateenabled" in data:
			self.state.setCheckState(0, eval(data["stateenabled"].replace("PySide.QtCore.", "").replace("PySide2.QtCore.", "")))


	@err_decorator
	def connectEvents(self):
		self.e_name.textChanged.connect(self.nameChanged)
		self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.b_changeTask.clicked.connect(self.changeTask)
		self.chb_globalRange.stateChanged.connect(self.rangeTypeChanged)
		self.sp_rangeStart.editingFinished.connect(self.startChanged)
		self.sp_rangeEnd.editingFinished.connect(self.endChanged)
		self.cb_cams.activated.connect(self.setCam)
		self.chb_resOverride.stateChanged.connect(self.resOverrideChanged)
		self.sp_resWidth.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.sp_resHeight.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.b_resPresets.clicked.connect(self.showResPresets)
		self.chb_localOutput.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.cb_formats.activated.connect(self.stateManager.saveStatesToScene)
		self.b_openLast.clicked.connect(lambda: self.core.openFolder(os.path.dirname(self.l_pathLast.text())))
		self.b_copyLast.clicked.connect(lambda: self.core.copyToClipboard(self.l_pathLast.text()))


	@err_decorator
	def rangeTypeChanged(self, state):
		self.l_rangeEnd.setEnabled(not state)
		self.sp_rangeStart.setEnabled(not state)
		self.sp_rangeEnd.setEnabled(not state)

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
	def setCam(self, index):
		if index == 0:
			self.curCam = None
		else:
			self.curCam = self.camlist[index-1]

		self.stateManager.saveStatesToScene()


	@err_decorator
	def nameChanged(self, text):
		taskname = self.l_taskName.text()
		if taskname == "":
			taskname = "None"

		sText = text + " (%s)" % taskname
		if self.state.text(0).endswith(" - disabled"):
			sText += " - disabled"
			
		self.state.setText(0, sText)


	@err_decorator
	def setTaskname(self, taskname):
		self.l_taskName.setText(taskname)
		self.updateUi()


	@err_decorator
	def changeTask(self):
		import CreateItem
		self.nameWin = CreateItem.CreateItem(startText=self.l_taskName.text(), showTasks=True, taskType="playblast", core=self.core)
		self.core.parentWindow(self.nameWin)
		self.nameWin.setWindowTitle("Change Taskname")
		self.nameWin.l_item.setText("Taskname:")
		self.nameWin.e_item.selectAll()
		result = self.nameWin.exec_()
		
		if result == 1:
			self.l_taskName.setText(self.nameWin.e_item.text())
			self.nameChanged(self.e_name.text())

			self.setTaskWarn(False)

			self.stateManager.saveStatesToScene()


	@err_decorator
	def resOverrideChanged(self, checked):
		self.sp_resWidth.setEnabled(checked)
		self.sp_resHeight.setEnabled(checked)
		self.b_resPresets.setEnabled(checked)

		self.stateManager.saveStatesToScene()


	@err_decorator
	def showResPresets(self):
		pmenu = QMenu()

		for i in self.resolutionPresets:
			pAct = QAction(i, self)
			pwidth = int(i.split("x")[0])
			pheight = int(i.split("x")[1])
			pAct.triggered.connect(lambda x=None, v=pwidth: self.sp_resWidth.setValue(v))
			pAct.triggered.connect(lambda x=None, v=pheight: self.sp_resHeight.setValue(v))
			pAct.triggered.connect(lambda: self.stateManager.saveStatesToScene())
			pmenu.addAction(pAct)

		self.core.appPlugin.setRCStyle(self.stateManager, pmenu)
		pmenu.exec_(QCursor.pos())


	@err_decorator
	def updateUi(self):
		#update Cams
		self.cb_cams.clear()
		self.cb_cams.addItem("Don't override")
		self.camlist = camNames = []

		if not self.stateManager.standalone:
			self.camlist = self.core.appPlugin.getCamNodes(self)
			camNames = [self.core.appPlugin.getCamName(self, i) for i in self.camlist]

		self.cb_cams.addItems(camNames)

		if self.curCam in self.camlist:
			self.cb_cams.setCurrentIndex(self.camlist.index(self.curCam)+1)
		else:
			self.cb_cams.setCurrentIndex(0)
			self.curCam = None

		if self.l_taskName.text() != "":
			self.setTaskWarn(False)

		self.nameChanged(self.e_name.text())

		return True


	@err_decorator
	def preExecuteState(self):
		warnings = []

		if self.l_taskName.text() == "":
			warnings.append(["No taskname is given.", "", 3])

		warnings += self.core.appPlugin.sm_playblast_preExecute(self)

		return [self.state.text(0), warnings]


	@err_decorator
	def getOutputName(self, useVersion="next"):
		if self.l_taskName.text() == "":
			return

		fileName = self.core.getCurrentFileName()
		sceneDir = self.core.getConfig('paths', "scenes", configPath=self.core.prismIni)

		basePath = self.core.projectPath
		if self.core.useLocalFiles:
			if self.chb_localOutput.isChecked():
				basePath = self.core.localProjectPath
				if fileName.startswith(os.path.join(self.core.projectPath, sceneDir)):
					fileName = fileName.replace(self.core.projectPath, self.core.localProjectPath)
			elif fileName.startswith(os.path.join(self.core.localProjectPath, sceneDir)):
				fileName = fileName.replace(self.core.localProjectPath, self.core.projectPath)

		hVersion = ""
		if useVersion != "next":
			hVersion = useVersion.split(self.core.filenameSeparator)[0]
			pComment = useVersion.split(self.core.filenameSeparator)[1]

		fnameData = self.core.getScenefileData(fileName)
		if fnameData["type"] == "shot":
			outputPath = os.path.join(self.core.getEntityBasePath(fileName), "Playblasts", self.l_taskName.text())
			if hVersion == "":
				hVersion = self.core.getHighestTaskVersion(outputPath)
				pComment = fnameData["comment"]

			outputPath = os.path.join(outputPath, hVersion + self.core.filenameSeparator + pComment)
			outputFile = os.path.join( "shot" + self.core.filenameSeparator + fnameData["shotName"] + self.core.filenameSeparator + self.l_taskName.text() + self.core.filenameSeparator + hVersion + "..jpg")
		elif fnameData["type"] == "asset":
			if os.path.join(sceneDir, "Assets", "Scenefiles") in fileName:
				outputPath = os.path.join(self.core.fixPath(basePath), sceneDir, "Assets", "Playblasts", self.l_taskName.text())
			else:
				outputPath = os.path.join(self.core.getEntityBasePath(fileName), "Playblasts", self.l_taskName.text())
				
			if hVersion == "":
				hVersion = self.core.getHighestTaskVersion(outputPath)
				pComment = fnameData["comment"]

			outputPath = os.path.join(outputPath, hVersion + self.core.filenameSeparator + pComment)
			outputFile = os.path.join( fnameData["assetName"]  + self.core.filenameSeparator + self.l_taskName.text() + self.core.filenameSeparator + hVersion + "..jpg")
		else:
			return

		outputName = os.path.join(outputPath, outputFile)

		return outputName, outputPath, hVersion


	@err_decorator
	def executeState(self, parent, useVersion="next"):
	#	if not self.core.uiAvailable:
	#		return [self.state.text(0) + ": error - Playblasts are not supported without UI."]

		if self.l_taskName.text() == "":
			return [self.state.text(0) + ": error - No taskname is given. Skipped the activation of this state."]

		fileName = self.core.getCurrentFileName()

		outputName, outputPath, hVersion = self.getOutputName(useVersion=useVersion)

		outLength = len(outputName)
		if platform.system() == "Windows" and outLength > 255:
			return [self.state.text(0) + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, taskname or projectpath." % outLength]

		if not os.path.exists(outputPath):
			os.makedirs(outputPath)

		self.core.saveVersionInfo(location=outputPath, version=hVersion, origin=fileName)

		self.l_pathLast.setText(outputName)
		self.l_pathLast.setToolTip(outputName)
		self.b_openLast.setEnabled(True)
		self.b_copyLast.setEnabled(True)

		self.stateManager.saveStatesToScene()

		self.core.saveScene(versionUp=False, prismReq=False)

		if self.chb_globalRange.isChecked():
			jobFrames = (self.stateManager.sp_rangeStart.value(), self.stateManager.sp_rangeEnd.value())
		else:
			jobFrames = (self.sp_rangeStart.value(), self.sp_rangeEnd.value())

		exCheck = self.core.appPlugin.sm_playblast_execute(self)
		if exCheck is not None:
			return exCheck

		if self.curCam is not None and not self.core.appPlugin.isNodeValid(self, self.curCam):
			return [self.state.text(0) + ": error - Camera is invalid (%s)." % self.curCam]

		self.core.callHook("prePlayblast", args={"prismCore":self.core, "scenefile":fileName, "startFrame":jobFrames[0], "endFrame":jobFrames[1], "outputName":outputName})

		try:
			self.core.appPlugin.sm_playblast_createPlayblast(self, jobFrames=jobFrames, outputName=outputName)

			getattr(self.core.appPlugin, "sm_playblast_postExecute", lambda x: None)(self)

			if self.cb_formats.currentText() == "mp4":
				mediaBaseName = os.path.splitext(outputName)[0]
				videoOutput = mediaBaseName + "mp4"
				inputpath = os.path.splitext(outputName)[0] + "%04d" + os.path.splitext(outputName)[1]
				result = self.core.convertMedia(inputpath, jobFrames[0], videoOutput)

				if not os.path.exists(videoOutput):
					return [self.state.text(0) + " - error occurred during conversion of jpg files to mp4"]

				delFiles = []
				for i in os.listdir(os.path.dirname(outputName)):
					if i.startswith(os.path.basename(mediaBaseName)) and i.endswith(".jpg"):
						delFiles.append(os.path.join(os.path.dirname(outputName), i))

				for i in delFiles:
					try:
						os.remove(i)
					except:
						pass

			self.core.callHook("postPlayblast", args={"prismCore":self.core, "scenefile":fileName, "startFrame":jobFrames[0], "endFrame":jobFrames[1], "outputName":outputName})

			if len(os.listdir(outputPath)) > 1:
				return [self.state.text(0) + " - success"]
			else:
				return [self.state.text(0) + " - unknown error (files do not exist)"]
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			erStr = ("%s ERROR - sm_default_playblast %s:\n%s" % (time.strftime("%d/%m/%y %X"), self.core.version, traceback.format_exc()))
			self.core.writeErrorLog(erStr)
			return [self.state.text(0) + " - unknown error (view console for more information)"]


	@err_decorator
	def setTaskWarn(self, warn):
		useSS = getattr(self.core.appPlugin, "colorButtonWithStyleSheet", False)
		if warn:
			if useSS:
				self.b_changeTask.setStyleSheet("QPushButton { background-color: rgb(200,0,0); }")
			else:
				self.b_changeTask.setPalette(self.warnPalette)
		else:
			if useSS:
				self.b_changeTask.setStyleSheet("")
			else:
				self.b_changeTask.setPalette(self.oldPalette)


	@err_decorator
	def getStateProps(self):
		stateProps = {"statename":self.e_name.text(), "taskname":self.l_taskName.text(), "globalrange": str(self.chb_globalRange.isChecked()), "startframe":self.sp_rangeStart.value(), "endframe":self.sp_rangeEnd.value(), "currentcam": str(self.curCam), "resoverride": str([self.chb_resOverride.isChecked(), self.sp_resWidth.value(), self.sp_resHeight.value()]), "localoutput": str(self.chb_localOutput.isChecked())}
		stateProps.update({"lastexportpath": self.l_pathLast.text().replace("\\", "/"), "stateenabled":str(self.state.checkState(0)), "outputformat": str(self.cb_formats.currentText())})
		return stateProps