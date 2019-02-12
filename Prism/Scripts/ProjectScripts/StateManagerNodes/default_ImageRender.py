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

import sys, os, shutil, time, traceback, threading, platform
from functools import wraps

if sys.version[0] == "3":
	from configparser import ConfigParser
	pVersion = 3
else:
	from ConfigParser import ConfigParser
	pVersion = 2



class ImageRenderClass(object):
	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - sm_default_imageRender %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def setup(self, state, core, stateManager, node=None, stateData=None):
		self.state = state
		self.core = core
		self.stateManager = stateManager

		self.curCam = None
		self.className = "ImageRender"
		self.listType = "Export"

		self.renderingStarted = False

		self.e_name.setText(state.text(0))

		self.l_name.setVisible(False)
		self.e_name.setVisible(False)
		self.gb_submit.setChecked(False)
		self.f_renderLayer.setVisible(False)

		self.core.appPlugin.sm_render_startup(self)

		if not self.core.appPlugin.sm_render_isVray(self):
			self.gb_Vray.setVisible(False)

		self.resolutionPresets = ["1920x1080", "1280x720", "640x360", "4000x2000", "2000x1000"]
		self.f_localOutput.setVisible(self.core.useLocalFiles)
		self.e_osSlaves.setText("All")

		self.connectEvents()

		self.oldPalette = self.b_changeTask.palette()
		self.warnPalette = QPalette()
		self.warnPalette.setColor(QPalette.Button, QColor(200, 0, 0))
		self.warnPalette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
		
		self.core.appPlugin.sm_render_setTaskWarn(self, True)

		self.nameChanged(state.text(0))

		for i in self.core.rfManagers.values():
			self.cb_manager.addItem(i.pluginName)
			i.sm_houExport_startup(self)

		if self.cb_manager.count() == 0:
			self.gb_submit.setVisible(False)

		self.managerChanged(True)

		if stateData is not None:
			self.loadData(stateData)


	@err_decorator
	def loadData(self, data):
		if "taskname" in data:
			self.l_taskName.setText(data["taskname"])
			if data["taskname"] != "":
				self.core.appPlugin.sm_render_setTaskWarn(self, False)
		
		self.updateUi()

		if "statename" in data:
			self.e_name.setText(data["statename"])
		if "globalrange" in data:
			self.chb_globalRange.setChecked(eval(data["globalrange"]))
		if "startframe" in data:
			self.sp_rangeStart.setValue(int(data["startframe"]))
		if "endframe" in data:
			self.sp_rangeEnd.setValue(int(data["endframe"]))
		if "currentcam" in data:
			idx = self.cb_cam.findText(self.core.appPlugin.getCamName(self, data["currentcam"]))
			if idx != -1:
				self.curCam = self.camlist[idx]
				self.cb_cam.setCurrentIndex(idx)
				self.stateManager.saveStatesToScene()
		if "resoverride" in data:
			res = eval(data["resoverride"])
			self.chb_resOverride.setChecked(res[0])
			self.sp_resWidth.setValue(res[1])
			self.sp_resHeight.setValue(res[2])
		if "localoutput" in data:
			self.chb_localOutput.setChecked(eval(data["localoutput"]))
		if "renderlayer" in data:
			idx = self.cb_renderLayer.findText(data["renderlayer"])
			if idx != -1:
				self.cb_renderLayer.setCurrentIndex(idx)
				self.stateManager.saveStatesToScene()
		if "vrayoverride" in data:
			self.chb_override.setChecked(eval(data["vrayoverride"]))
		if "vrayminsubdivs" in data:
			self.sp_minSubdivs.setValue(int(data["vrayminsubdivs"]))
		if "vraymaxsubdivs" in data:
			self.sp_maxSubdivs.setValue(int(data["vraymaxsubdivs"]))
		if "vraycthreshold" in data:
			self.sp_cThres.setValue(float(data["vraycthreshold"]))
		if "vraynthreshold" in data:
			self.sp_nThres.setValue(float(data["vraynthreshold"]))
		if "submitrender" in data:
			self.gb_submit.setChecked(eval(data["submitrender"]))
		if "rjmanager" in data:
			idx = self.cb_manager.findText(data["rjmanager"])
			if idx != -1:
				self.cb_manager.setCurrentIndex(idx)
			self.managerChanged(True)
		if "rjprio" in data:
			self.sp_rjPrio.setValue(int(data["rjprio"]))
		if "rjframespertask" in data:
			self.sp_rjFramesPerTask.setValue(int(data["rjframespertask"]))
		if "rjtimeout" in data:
			self.sp_rjTimeout.setValue(int(data["rjtimeout"]))
		if "rjsuspended" in data:
			self.chb_rjSuspended.setChecked(eval(data["rjsuspended"]))
		if "osdependencies" in data:
			self.chb_osDependencies.setChecked(eval(data["osdependencies"]))
		if "osupload" in data:
			self.chb_osUpload.setChecked(eval(data["osupload"]))
		if "ospassets" in data:
			self.chb_osPAssets.setChecked(eval(data["ospassets"]))
		if "osslaves" in data:
			self.e_osSlaves.setText(data["osslaves"])
		if "curdlgroup" in data:
			idx = self.cb_dlGroup.findText(data["curdlgroup"])
			if idx != -1:
				self.cb_dlGroup.setCurrentIndex(idx)
		if "dlconcurrent" in data:
			self.sp_dlConcurrentTasks.setValue(int(data["dlconcurrent"]))
		if "dlgpupt" in data:
			self.sp_dlGPUpt.setValue(int(data["dlgpupt"]))
			self.gpuPtChanged()
		if "dlgpudevices" in data:
			self.le_dlGPUdevices.setText(data["dlgpudevices"])
			self.gpuDevicesChanged()
		if "enablepasses" in data:
			self.gb_passes.setChecked(eval(data["enablepasses"]))
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
		self.cb_cam.activated.connect(self.setCam)
		self.chb_resOverride.stateChanged.connect(self.resOverrideChanged)
		self.sp_resWidth.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.sp_resHeight.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.b_resPresets.clicked.connect(self.showResPresets)
		self.chb_localOutput.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.cb_renderLayer.activated.connect(self.stateManager.saveStatesToScene)
		self.chb_override.stateChanged.connect(self.overrideChanged)
		self.sp_minSubdivs.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.sp_maxSubdivs.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.sp_cThres.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.sp_nThres.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.gb_submit.toggled.connect(self.rjToggled)
		self.cb_manager.activated.connect(self.managerChanged)
		self.sp_rjPrio.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.sp_rjFramesPerTask.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.sp_rjTimeout.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.chb_rjSuspended.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.chb_osDependencies.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.chb_osUpload.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.chb_osPAssets.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.e_osSlaves.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.b_osSlaves.clicked.connect(self.openSlaves)
		self.cb_dlGroup.activated.connect(self.stateManager.saveStatesToScene)
		self.sp_dlConcurrentTasks.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.sp_dlGPUpt.editingFinished.connect(self.gpuPtChanged)
		self.le_dlGPUdevices.editingFinished.connect(self.gpuDevicesChanged)
		self.gb_passes.toggled.connect(self.stateManager.saveStatesToScene)
		self.b_addPasses.clicked.connect(self.showPasses)
		self.lw_passes.customContextMenuRequested.connect(self.rclickPasses)
		self.b_openLast.clicked.connect(lambda: self.core.openFolder(os.path.dirname(self.l_pathLast.text())))
		self.b_copyLast.clicked.connect(lambda: self.core.copyToClipboard(self.l_pathLast.text()))
		self.lw_passes.itemDoubleClicked.connect(lambda x: self.core.appPlugin.sm_render_openPasses(self))


	@err_decorator
	def rangeTypeChanged(self, state):
		if state == Qt.Checked:
			self.l_rangeStart.setEnabled(False)
			self.l_rangeEnd.setEnabled(False)
			self.sp_rangeStart.setEnabled(False)
			self.sp_rangeEnd.setEnabled(False)
		else:
			self.l_rangeStart.setEnabled(True)
			self.l_rangeEnd.setEnabled(True)
			self.sp_rangeStart.setEnabled(True)
			self.sp_rangeEnd.setEnabled(True)

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
		self.curCam = self.camlist[index]
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
	def changeTask(self):
		import CreateItem
		self.nameWin = CreateItem.CreateItem(startText=self.l_taskName.text(), showTasks=True, taskType="render", core=self.core)
		self.core.parentWindow(self.nameWin)
		self.nameWin.setWindowTitle("Change Taskname")
		self.nameWin.l_item.setText("Taskname:")
		self.nameWin.e_item.selectAll()
		prevTaskName = self.l_taskName.text()
		result = self.nameWin.exec_()
		
		if result == 1:
			self.l_taskName.setText(self.nameWin.e_item.text())
			self.core.appPlugin.sm_render_setTaskWarn(self, False)
			self.nameChanged(self.e_name.text())
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

		pmenu.exec_(QCursor.pos())


	@err_decorator
	def overrideChanged(self, checked):
		if self.chb_override.isChecked():
			self.l_subdivs.setEnabled(True)
			self.sp_minSubdivs.setEnabled(True)
			self.sp_maxSubdivs.setEnabled(True)
			self.l_cThres.setEnabled(True)
			self.sp_cThres.setEnabled(True)
			self.l_nThres.setEnabled(True)
			self.sp_nThres.setEnabled(True)
		else:
			self.l_subdivs.setEnabled(False)
			self.sp_minSubdivs.setEnabled(False)
			self.sp_maxSubdivs.setEnabled(False)
			self.l_cThres.setEnabled(False)
			self.sp_cThres.setEnabled(False)
			self.l_nThres.setEnabled(False)
			self.sp_nThres.setEnabled(False)

		self.stateManager.saveStatesToScene()


	@err_decorator
	def updateUi(self):

		#update Cams
		self.cb_cam.clear()
		
		self.camlist = self.core.appPlugin.getCamNodes(self, cur=True)

		self.cb_cam.addItems([self.core.appPlugin.getCamName(self, i) for i in self.camlist])

		if self.curCam in self.camlist:
			self.cb_cam.setCurrentIndex(self.camlist.index(self.curCam))
		else:
			self.cb_cam.setCurrentIndex(0)
			if len(self.camlist) > 0:
				self.curCam = self.camlist[0]
			else:
				self.curCam = None

			self.stateManager.saveStatesToScene()

		#update Render Layer
		curLayer = self.cb_renderLayer.currentText()
		self.cb_renderLayer.clear()
		
		layerList = getattr(self.core.appPlugin, "sm_render_getRenderLayer", lambda x: [])(self)

		self.cb_renderLayer.addItems(layerList)

		if curLayer in layerList:
			self.cb_renderLayer.setCurrentIndex(layerList.index(curLayer))
		else:
			self.cb_renderLayer.setCurrentIndex(0)
			self.stateManager.saveStatesToScene()


		if self.l_taskName.text() != "":
			self.core.appPlugin.sm_render_setTaskWarn(self, False)

		if not self.gb_submit.isHidden():
			self.core.rfManagers[self.cb_manager.currentText()].sm_render_updateUI(self)

		self.core.appPlugin.sm_render_refreshPasses(self)

		self.nameChanged(self.e_name.text())

		return True


	@err_decorator
	def openSlaves(self):
		try:
			del sys.modules["SlaveAssignment"]
		except:
			pass

		import SlaveAssignment
		self.sa = SlaveAssignment.SlaveAssignment(core = self.core, curSlaves = self.e_osSlaves.text())
		result = self.sa.exec_()

		if result == 1:
			selSlaves = ""
			if self.sa.rb_exclude.isChecked():
				selSlaves = "exclude "
			if self.sa.rb_all.isChecked():
				selSlaves += "All"
			elif self.sa.rb_group.isChecked():
				selSlaves += "groups: "
				for i in self.sa.activeGroups:
					selSlaves += i + ", "

				if selSlaves.endswith(", "):
					selSlaves = selSlaves[:-2]

			elif self.sa.rb_custom.isChecked():
				slavesList = [x.text() for x in self.sa.lw_slaves.selectedItems()]
				for i in slavesList:
					selSlaves += i + ", "

				if selSlaves.endswith(", "):
					selSlaves = selSlaves[:-2]

			self.e_osSlaves.setText(selSlaves)
			self.stateManager.saveStatesToScene()


	@err_decorator
	def gpuPtChanged(self):
		self.w_dlGPUdevices.setEnabled(self.sp_dlGPUpt.value() == 0)
		self.stateManager.saveStatesToScene()


	@err_decorator
	def gpuDevicesChanged(self):
		self.w_dlGPUpt.setEnabled(self.le_dlGPUdevices.text() == "")
		self.stateManager.saveStatesToScene()


	@err_decorator
	def showPasses(self):
		steps = self.core.appPlugin.sm_render_getRenderPasses(self)
		
		if steps is None or len(steps) == 0:
			return False

		steps = eval(steps)

		try:
			del sys.modules["ItemList"]
		except:
			pass

		import ItemList
		self.il = ItemList.ItemList(core = self.core)
		self.il.setWindowTitle("Select Passes")
		self.core.parentWindow(self.il)
		self.il.b_addStep.setVisible(False)
		self.il.tw_steps.doubleClicked.connect(self.il.accept)
		self.il.tw_steps.horizontalHeaderItem(0).setText("Name")
		self.il.tw_steps.setColumnHidden(1, True)
		for i in sorted(steps, key=lambda s: s.lower()):
			rc = self.il.tw_steps.rowCount()
			self.il.tw_steps.insertRow(rc)
			item1 = QTableWidgetItem(i)
			self.il.tw_steps.setItem(rc, 0, item1)

		result = self.il.exec_()

		if result != 1:
			return False

		for i in self.il.tw_steps.selectedItems():
			if i.column() == 0:
				self.core.appPlugin.sm_render_addRenderPass(self, passName=i.text(), steps=steps)

		self.updateUi()
		self.stateManager.saveStatesToScene()


	@err_decorator
	def rclickPasses(self, pos):
		if self.lw_passes.currentItem() is None or not getattr(self.core.appPlugin, "canDeleteRenderPasses", True):
			return

		item = self.lw_passes.currentItem()

		rcmenu = QMenu()

		delAct = QAction("Delete", self)
		delAct.triggered.connect(lambda: self.core.appPlugin.sm_render_deletePass(self, item))
		rcmenu.addAction(delAct)

		rcmenu.exec_(QCursor.pos())


	@err_decorator
	def rjToggled(self,checked):
		self.f_localOutput.setEnabled(self.gb_submit.isHidden() or not checked or (checked and self.core.rfManagers[self.cb_manager.currentText()].canOutputLocal))

		self.stateManager.saveStatesToScene()


	@err_decorator
	def managerChanged(self, text=None):
		self.f_localOutput.setEnabled(self.gb_submit.isHidden() or not self.gb_submit.isChecked() or (self.gb_submit.isChecked() and self.core.rfManagers[self.cb_manager.currentText()].canOutputLocal))

		if self.cb_manager.currentText() in self.core.rfManagers:
			self.core.rfManagers[self.cb_manager.currentText()].sm_render_managerChanged(self)

		self.stateManager.saveStatesToScene()


	@err_decorator
	def preExecuteState(self):
		warnings = []

		if self.l_taskName.text() == "":
			warnings.append(["No taskname is given.", "", 3])

		if self.curCam is None or (self.curCam != "Current View" and not self.core.appPlugin.isNodeValid(self, self.curCam)):
			warnings.append(["No camera is selected.", "", 3])
		elif self.curCam == "Current View":
			warnings.append(["No camera is selected.", "", 2])

		if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
			warnings += self.core.rfManagers[self.cb_manager.currentText()].sm_render_preExecute(self)

		warnings += self.core.appPlugin.sm_render_preExecute(self)

		return [self.state.text(0), warnings]


	@err_decorator
	def getOutputName(self, useVersion="next"):
		if self.l_taskName.text() == "":
			return

		fileName = self.core.getCurrentFileName()
		sceneDir = self.core.getConfig('paths', "scenes", configPath=self.core.prismIni)

		basePath = self.core.projectPath
		if self.core.useLocalFiles:
			if self.chb_localOutput.isChecked() and (self.gb_submit.isHidden() or not self.gb_submit.isChecked() or (self.gb_submit.isChecked() and self.core.rfManagers[self.cb_manager.currentText()].canOutputLocal)):
				basePath = self.core.localProjectPath
				if fileName.startswith(os.path.join(self.core.projectPath, sceneDir)):
					fileName = fileName.replace(self.core.projectPath, self.core.localProjectPath)
			elif fileName.startswith(os.path.join(self.core.localProjectPath, sceneDir)):
				fileName = fileName.replace(self.core.localProjectPath, self.core.projectPath)

		outputPath = ""
		outputFile = ""
		hVersion = ""
		if useVersion != "next":
			hVersion = useVersion.split(self.core.filenameSeperator)[0]
			pComment = useVersion.split(self.core.filenameSeperator)[1]

		fnameData = os.path.basename(fileName).split(self.core.filenameSeperator)
		if len(fnameData) == 8:
			outputPath = os.path.abspath(os.path.join(fileName, os.pardir, os.pardir, os.pardir, os.pardir, "Rendering", "3dRender", self.l_taskName.text()))
			if hVersion == "":
				hVersion = self.core.getHighestTaskVersion(outputPath)
				pComment = fnameData[5]

			outputPath = os.path.join(outputPath, hVersion + self.core.filenameSeperator + pComment, "beauty")
			outputFile = fnameData[0] + self.core.filenameSeperator + fnameData[1] + self.core.filenameSeperator + self.l_taskName.text() + self.core.filenameSeperator + hVersion + self.core.filenameSeperator + "beauty..exr" 
		elif len(fnameData) == 6:
			if os.path.join(sceneDir, "Assets", "Scenefiles") in fileName:
				outputPath = os.path.join(self.core.fixPath(basePath), sceneDir, "Assets", "Rendering", "3dRender", self.l_taskName.text())
			else:
				outputPath = os.path.abspath(os.path.join(fileName, os.pardir, os.pardir, os.pardir, "Rendering", "3dRender", self.l_taskName.text()))
			if hVersion == "":
				hVersion = self.core.getHighestTaskVersion(outputPath)
				pComment = fnameData[3]

			outputPath = os.path.join(outputPath, hVersion + self.core.filenameSeperator + pComment, "beauty")
			outputFile = fnameData[0] + self.core.filenameSeperator + self.l_taskName.text() + self.core.filenameSeperator + hVersion + self.core.filenameSeperator + "beauty..exr"
		
		outputName = os.path.join(outputPath, outputFile)
		outputName = self.core.appPlugin.sm_render_fixOutputPath(self, outputName)
		outputPath = os.path.dirname(outputName)

		return outputName, outputPath, hVersion


	@err_decorator
	def executeState(self, parent, useVersion="next"):
		if self.chb_globalRange.isChecked():
			jobFrames = [self.stateManager.sp_rangeStart.value(), self.stateManager.sp_rangeEnd.value()]
		else:
			jobFrames = [self.sp_rangeStart.value(), self.sp_rangeEnd.value()]

		fileName = self.core.getCurrentFileName()
		if not self.renderingStarted:	
			if self.l_taskName.text() == "":
				return [self.state.text(0) + ": error - no taskname is given. Skipped the activation of this state."]

			if self.curCam is None or (self.curCam != "Current View" and not self.core.appPlugin.isNodeValid(self, self.curCam)):
				return [self.state.text(0) + ": error - no camera is selected. Skipping activation of this state."]

			if self.chb_override.isChecked():
				self.core.appPlugin.sm_render_setVraySettings(self)

			outputName, outputPath, hVersion = self.getOutputName(useVersion=useVersion)

			outLength = len(outputName)
			if platform.system() == "Windows" and outLength > 255:
				return [self.state.text(0) + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, taskname or projectpath." % outLength]

			if not os.path.exists(outputPath):
				os.makedirs(outputPath)

			self.core.saveVersionInfo(location=os.path.dirname(outputPath), version=hVersion, origin=fileName)

			self.l_pathLast.setText(outputName)
			self.l_pathLast.setToolTip(outputName)
			self.b_openLast.setEnabled(True)
			self.b_copyLast.setEnabled(True)

			self.stateManager.saveStatesToScene()

			rSettings = {"outputName": outputName}

			self.core.appPlugin.sm_render_preSubmit(self, rSettings)
			self.core.callHook("preRender", args={"prismCore":self.core, "scenefile":fileName, "startFrame":jobFrames[0], "endFrame":jobFrames[1], "outputName":outputName})

			self.core.saveScene(versionUp=False, prismReq=False)

			if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
				result = self.core.rfManagers[self.cb_manager.currentText()].sm_render_submitJob(self, outputName, parent)
			else:
				result = self.core.appPlugin.sm_render_startLocalRender(self, rSettings["outputName"], rSettings)
		else:
			rSettings = self.LastRSettings
			result = self.core.appPlugin.sm_render_startLocalRender(self, rSettings["outputName"], rSettings)
			outputName = rSettings["outputName"]

		if not self.renderingStarted:
			self.core.appPlugin.sm_render_undoRenderSettings(self, rSettings)

		if result == "publish paused":
			return [self.state.text(0) + " - publish paused"]
		else:
			self.core.callHook("postRender", args={"prismCore":self.core, "scenefile":fileName, "startFrame":jobFrames[0], "endFrame":jobFrames[1], "outputName":outputName})

			if "Result=Success" in result:
				return [self.state.text(0) + " - success"]
			else:
				erStr = ("%s ERROR - sm_default_imageRenderPublish %s:\n%s" % (time.strftime("%d/%m/%y %X"), self.core.version, result))
				if not result.startswith("Execute Canceled: "):
					if result == "unknown error (files do not exist)":
						QMessageBox.warning(self.core.messageParent, "Warning", "No files were created during the rendering. If you think this is a Prism bug please report it in the forum:\nwww.prism-pipeline.com/forum/\nor write a mail to contact@prism-pipeline.com")
					else:
						self.core.writeErrorLog(erStr)
				return [self.state.text(0) + " - error - " + result]


	@err_decorator
	def getStateProps(self):
		stateProps = {"statename":self.e_name.text(), "taskname":self.l_taskName.text(), "globalrange":str(self.chb_globalRange.isChecked()), "startframe":self.sp_rangeStart.value(), "endframe":self.sp_rangeEnd.value(), "currentcam": str(self.curCam), "resoverride": str([self.chb_resOverride.isChecked(), self.sp_resWidth.value(), self.sp_resHeight.value()]), "localoutput": str(self.chb_localOutput.isChecked()), "renderlayer": str(self.cb_renderLayer.currentText()), "vrayoverride":str(self.chb_override.isChecked())}
		stateProps.update({"vrayminsubdivs":self.sp_minSubdivs.value(), "vraymaxsubdivs":self.sp_maxSubdivs.value(), "vraycthreshold":self.sp_cThres.value(), "vraynthreshold":self.sp_nThres.value(), "submitrender": str(self.gb_submit.isChecked()), "rjmanager":str(self.cb_manager.currentText()), "rjprio":self.sp_rjPrio.value(), "rjframespertask":self.sp_rjFramesPerTask.value(), "rjtimeout":self.sp_rjTimeout.value(), "rjsuspended": str(self.chb_rjSuspended.isChecked()), "osdependencies": str(self.chb_osDependencies.isChecked()), "osupload": str(self.chb_osUpload.isChecked()), "ospassets": str(self.chb_osPAssets.isChecked()), "osslaves": self.e_osSlaves.text(), "curdlgroup":self.cb_dlGroup.currentText(), "dlconcurrent":self.sp_dlConcurrentTasks.value(), "dlgpupt":self.sp_dlGPUpt.value(), "dlgpudevices":self.le_dlGPUdevices.text(), "lastexportpath": self.l_pathLast.text().replace("\\", "/"), "enablepasses": str(self.gb_passes.isChecked()), "stateenabled":str(self.state.checkState(0))})
		return stateProps