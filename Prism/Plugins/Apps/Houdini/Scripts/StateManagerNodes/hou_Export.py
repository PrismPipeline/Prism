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
from ConfigParser import ConfigParser
from functools import wraps

try:
	import hou
except:
	pass


class ExportClass(object):
	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - hou_Export %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
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

		self.node = None
		self.curCam = None

		self.cb_outType.addItems(self.core.appPlugin.outputFormats)

		self.l_name.setVisible(False)
		self.e_name.setVisible(False)
		self.f_cam.setVisible(False)
		self.w_sCamShot.setVisible(False)
		self.w_saveToExistingHDA.setVisible(False)
		self.w_blackboxHDA.setVisible(False)
		self.w_projectHDA.setVisible(False)
		self.gb_submit.setChecked(False)
		self.f_localOutput.setVisible(self.core.useLocalFiles)

		for i in self.core.rfManagers.values():
			self.cb_manager.addItem(i.pluginName)
			i.sm_houExport_startup(self)

		if self.cb_manager.count() == 0:
			self.gb_submit.setVisible(False)

		if node is None:
			if stateData is None:
				if not self.connectNode():
					self.createNode()
		else:
			self.node = node

		if self.node is not None and self.node.parm("f1") is not None:
			self.sp_rangeStart.setValue(self.node.parm("f1").eval())
			self.sp_rangeEnd.setValue(self.node.parm("f2").eval())

			idx = -1
			if self.node.type().name() in ["rop_alembic", "alembic"]:
				idx = self.cb_outType.findText(".abc")
			elif self.node.type().name() in ["pixar::usdrop"]:
				idx = self.cb_outType.findText(".usd")
			elif self.node.type().name() in ["Redshift_Proxy_Output"]:
				idx = self.cb_outType.findText(".rs")
			
			if idx != -1:
				self.cb_outType.setCurrentIndex(idx)
				self.typeChanged(self.cb_outType.currentText())
		elif stateData is None:
			self.sp_rangeStart.setValue(hou.playbar.playbackRange()[0])
			self.sp_rangeEnd.setValue(hou.playbar.playbackRange()[1])

		self.nameChanged(state.text(0))

		self.managerChanged(True)

		self.connectEvents()

		self.b_changeTask.setStyleSheet("QPushButton { background-color: rgb(150,0,0); }")
		self.core.appPlugin.fixStyleSheet(self.gb_submit)

		self.e_osSlaves.setText("All")

		if stateData is not None:
			self.loadData(stateData)
		else:
			fileName = self.core.getCurrentFileName()
			fnameData = os.path.basename(fileName).split(self.core.filenameSeperator)
			if os.path.exists(fileName) and len(fnameData) == 8 and (os.path.join(self.core.projectPath, self.core.getConfig('paths', "scenes", configPath=self.core.prismIni)) in fileName or (self.core.useLocalFiles and os.path.join(self.core.localProjectPath, self.core.getConfig('paths', "scenes", configPath=self.core.prismIni)) in fileName)):
				idx = self.cb_sCamShot.findText(fnameData[1])
				if idx != -1:
					self.cb_sCamShot.setCurrentIndex(idx)


	@err_decorator
	def loadData(self, data):
		self.updateUi()

		if "statename" in data:
			self.e_name.setText(data["statename"])
		if "taskname" in data:
			self.l_taskName.setText(data["taskname"])
			if data["taskname"] != "":
				self.b_changeTask.setStyleSheet("")
		if "globalrange" in data:
			self.chb_globalRange.setChecked(eval(data["globalrange"]))
		if "startframe" in data:
			self.sp_rangeStart.setValue(int(data["startframe"]))
		if "endframe" in data:
			self.sp_rangeEnd.setValue(int(data["endframe"]))
		if "connectednode" in data:
			node = hou.node(data["connectednode"])
			if node is None:
				node = self.findNode(data["connectednode"])
			self.connectNode(node)
		if "outputtypes" in data:
			self.cb_outType.clear()
			self.cb_outType.addItems(eval(data["outputtypes"]))
		if "curoutputtype" in data:
			idx = self.cb_outType.findText(data["curoutputtype"])
			if idx != -1:
				self.cb_outType.setCurrentIndex(idx)
				self.typeChanged(self.cb_outType.currentText(), createMissing=False)
		if "localoutput" in data:
			self.chb_localOutput.setChecked(eval(data["localoutput"]))
		if "savetoexistinghda" in data:
			self.chb_saveToExistingHDA.setChecked(eval(data["savetoexistinghda"]))
		if "projecthda" in data:
			self.chb_projectHDA.setChecked(eval(data["projecthda"]))
		if "blackboxhda" in data:
			self.chb_blackboxHDA.setChecked(eval(data["blackboxhda"]))
		if "unitconvert" in data:
			self.chb_convertExport.setChecked(eval(data["unitconvert"]))
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
		if "currentcam" in data:
			idx = self.cb_cam.findText(data["currentcam"])
			if idx != -1:
				self.curCam = self.camlist[idx]
				if self.cb_outType.currentText() == "ShotCam":
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

		self.nameChanged(self.e_name.text())


	@err_decorator
	def findNode(self, path):
		for node in hou.node("/").allSubChildren():
			if node.userData("PrismPath") is not None and node.userData("PrismPath") == path:
				node.setUserData("PrismPath", node.path())
				return node

		return None


	@err_decorator
	def isNodeValid(self):
		try:
			validTST = self.node.name()
		except:
			self.node = None

		return (self.node is not None)


	@err_decorator
	def createNode(self):
		parentNode = None
		nodePath = None
		if not self.isNodeValid():
			if len(hou.selectedNodes()) > 0:
				curContext = hou.selectedNodes()[0].type().category().name()
				if len(hou.selectedNodes()[0].outputNames()) > 0:
					parentNode = hou.selectedNodes()[0]
			else:
				paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
				if paneTab is None:
					return

				curContext = paneTab.pwd().childTypeCategory().name()
				nodePath = paneTab.pwd()
		else:
			curContext = self.node.type().category().name()
			if len(self.node.inputs()) > 0:
				parentNode = self.node.inputs()[0]
			else:
				nodePath = self.node.parent()

			if self.node.type().name() in ["rop_geometry", "rop_alembic", "rop_dop", "rop_comp", "filecache", "geometry", "alembic", "pixar::usdrop", "Redshift_Proxy_Output"]:
				try:
					self.node.destroy()
				except:
					pass

			self.node = None

		ropType = ""
		if curContext == "Cop2":
			ropType = "rop_comp"
		elif curContext == "Dop":
			ropType = "rop_dop"
		elif curContext == "Sop":
			ropType = "rop_geometry"
		elif curContext == "Driver":
			ropType = "geometry"

		if self.cb_outType.currentText() == ".abc":
			if curContext == "Sop":
				ropType = "rop_alembic"
			else:
				ropType = "alembic"
		elif self.cb_outType.currentText() == ".hda":
			ropType = ""
		elif self.cb_outType.currentText() == ".usd":
			ropType = "pixar::usdrop"
		elif self.cb_outType.currentText() == ".rs":
			ropType = "Redshift_Proxy_Output"

		if ropType != "" and nodePath is not None and not nodePath.isInsideLockedHDA() and not nodePath.isLockedHDA():
			try:
				self.node = nodePath.createNode(ropType)
			except:
				pass
			else:
				paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
				if paneTab is not None:
					self.node.setPosition(paneTab.visibleBounds().center())
				self.node.moveToGoodPosition()
		elif ropType != "" and parentNode is not None and not (parentNode.parent().isInsideLockedHDA()):
			try:
				self.node = parentNode.createOutputNode(ropType)
			except:
				pass
			else:
				self.node.moveToGoodPosition()

		self.goToNode()
		self.updateUi()


	@err_decorator
	def connectEvents(self):
		self.e_name.textChanged.connect(self.nameChanged)
		self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.b_changeTask.clicked.connect(self.changeTask)
		self.chb_globalRange.stateChanged.connect(self.rangeTypeChanged)
		self.sp_rangeStart.editingFinished.connect(self.startChanged)
		self.sp_rangeEnd.editingFinished.connect(self.endChanged)
		self.cb_outType.activated[str].connect(self.typeChanged)
		self.b_goTo.clicked.connect(self.goToNode)
		self.b_connect.clicked.connect(self.connectNode)
		self.chb_saveToExistingHDA.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.chb_saveToExistingHDA.stateChanged.connect(lambda x: self.f_localOutput.setEnabled(not x))
		self.chb_saveToExistingHDA.stateChanged.connect(lambda x: self.w_projectHDA.setEnabled(not x or not self.w_saveToExistingHDA.isEnabled()))
		self.chb_projectHDA.stateChanged.connect(lambda x: self.f_localOutput.setEnabled(not x))
		self.chb_projectHDA.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.chb_blackboxHDA.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.chb_localOutput.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.chb_convertExport.stateChanged.connect(self.stateManager.saveStatesToScene)
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
		self.cb_cam.activated.connect(self.setCam)
		self.cb_sCamShot.activated.connect(self.stateManager.saveStatesToScene)
		self.b_openLast.clicked.connect(lambda: self.core.openFolder(os.path.dirname(self.l_pathLast.text())))
		self.b_copyLast.clicked.connect(lambda: self.core.copyToClipboard(self.l_pathLast.text()))


	@err_decorator
	def rangeTypeChanged(self, state):
		self.l_rangeStart.setEnabled(not state)
		self.l_rangeEnd.setEnabled(not state)
		self.sp_rangeStart.setEnabled(not state)
		self.sp_rangeEnd.setEnabled(not state)

		self.stateManager.saveStatesToScene()


	@err_decorator
	def nameChanged(self, text):
		if self.cb_outType.currentText() == "ShotCam":
			sText = text + " - Shotcam (%s)" % (self.curCam)
		else:
			try:
				sText = text + " - %s (%s)" % (self.l_taskName.text(), self.node)
			except:
				sText = text + " - %s (None)" % self.l_taskName.text()

		if self.state.text(0).endswith(" - disabled"):
			sText += " - disabled"
			
		self.state.setText(0, sText)


	@err_decorator
	def changeTask(self):
		import CreateItem
		self.nameWin = CreateItem.CreateItem(startText=self.l_taskName.text(), showTasks=True, taskType="export", core=self.core)
		self.core.parentWindow(self.nameWin)
		self.nameWin.setWindowTitle("Change Taskname")
		self.nameWin.l_item.setText("Taskname:")
		self.nameWin.e_item.selectAll()
		result = self.nameWin.exec_()
		
		if result == 1:
			self.l_taskName.setText(self.nameWin.e_item.text())
			self.nameChanged(self.e_name.text())

			self.b_changeTask.setStyleSheet("")

			self.stateManager.saveStatesToScene()


	@err_decorator
	def setCam(self, index):
		self.curCam = self.camlist[index]
		self.nameChanged(self.e_name.text())

		self.stateManager.saveStatesToScene()


	@err_decorator
	def updateUi(self):
		try:
			self.node.name()
			self.l_status.setText(self.node.name())
			self.l_status.setStyleSheet("QLabel { background-color : rgb(0,150,0); }")
		except:
			self.l_status.setText("Not connected")
			self.l_status.setStyleSheet("QLabel { background-color : rgb(150,0,0); }")

		self.camlist = []
		for node in hou.node("/").allSubChildren():

			if node.type().name() == "cam" and node.name() != "ipr_camera":
				self.camlist.append(node)

		self.cb_cam.clear()
		self.cb_cam.addItems([str(i) for i in self.camlist])

		try:
			self.curCam.name()
		except:
			self.curCam = None

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

		if self.cb_outType.currentText() == ".hda":
			if self.isNodeValid() and (self.node.canCreateDigitalAsset() or self.node.type().definition() is not None):
				self.w_saveToExistingHDA.setEnabled(self.node.type().definition() is not None)
			else:
				self.w_saveToExistingHDA.setEnabled(True)

			self.w_blackboxHDA.setEnabled(not self.isNodeValid() or self.node.type().areContentsViewable())

			self.w_projectHDA.setEnabled(not self.w_saveToExistingHDA.isEnabled() or not self.chb_saveToExistingHDA.isChecked())

		self.checkLocalOutput()

		self.nameChanged(self.e_name.text())


	@err_decorator
	def typeChanged(self, idx, createMissing=True):
		self.isNodeValid()

		if idx == ".abc":
			self.f_cam.setVisible(False)
			self.w_sCamShot.setVisible(False)
			self.w_saveToExistingHDA.setVisible(False)
			self.w_blackboxHDA.setVisible(False)
			self.w_projectHDA.setVisible(False)
			self.f_taskName.setVisible(True)
			self.f_status.setVisible(True)
			self.f_connect.setVisible(True)
			self.f_frameRange.setVisible(True)
			self.f_convertExport.setVisible(True)
			if self.cb_manager.count() > 0:
				self.gb_submit.setVisible(True)
			if (self.node is None or self.node.type().name() not in ["rop_alembic", "alembic"]) and createMissing:
				self.createNode()
		elif idx == ".hda":
			self.f_cam.setVisible(False)
			self.w_sCamShot.setVisible(False)
			self.w_saveToExistingHDA.setVisible(True)
			self.w_blackboxHDA.setVisible(True)
			self.w_projectHDA.setVisible(True)
			self.f_taskName.setVisible(True)
			self.f_status.setVisible(True)
			self.f_connect.setVisible(True)
			self.f_frameRange.setVisible(False)
			self.f_convertExport.setVisible(False)
			self.gb_submit.setVisible(False)
			if (self.node is None or (self.node is not None and not (self.node.canCreateDigitalAsset()) or self.node.type().definition() is not None)) and createMissing:
				self.createNode()
		elif idx == ".usd":
			self.f_cam.setVisible(False)
			self.w_sCamShot.setVisible(False)
			self.w_saveToExistingHDA.setVisible(False)
			self.w_blackboxHDA.setVisible(False)
			self.w_projectHDA.setVisible(False)
			self.f_taskName.setVisible(True)
			self.f_status.setVisible(True)
			self.f_connect.setVisible(True)
			self.f_frameRange.setVisible(True)
			self.f_convertExport.setVisible(True)
			if self.cb_manager.count() > 0:
				self.gb_submit.setVisible(True)
			if (self.node is None or self.node.type().name() not in ["pixar::usdrop"]) and createMissing:
				self.createNode()
		elif idx == ".rs":
			self.f_cam.setVisible(False)
			self.w_sCamShot.setVisible(False)
			self.w_saveToExistingHDA.setVisible(False)
			self.w_blackboxHDA.setVisible(False)
			self.w_projectHDA.setVisible(False)
			self.f_taskName.setVisible(True)
			self.f_status.setVisible(True)
			self.f_connect.setVisible(True)
			self.f_frameRange.setVisible(True)
			self.f_convertExport.setVisible(True)
			if self.cb_manager.count() > 0:
				self.gb_submit.setVisible(True)
			if (self.node is None or self.node.type().name() not in ["Redshift_Proxy_Output"]) and createMissing:
				self.createNode()
		elif idx == "ShotCam":
			self.f_cam.setVisible(True)
			self.w_sCamShot.setVisible(True)
			self.w_saveToExistingHDA.setVisible(False)
			self.w_blackboxHDA.setVisible(False)
			self.w_projectHDA.setVisible(False)
			self.f_taskName.setVisible(False)
			self.f_status.setVisible(False)
			self.f_connect.setVisible(False)
			self.f_frameRange.setVisible(True)
			self.f_convertExport.setVisible(True)
			self.gb_submit.setVisible(False)
		elif idx == "other":
			self.f_cam.setVisible(False)
			self.w_sCamShot.setVisible(False)
			self.w_saveToExistingHDA.setVisible(False)
			self.w_blackboxHDA.setVisible(False)
			self.w_projectHDA.setVisible(False)
			self.f_taskName.setVisible(True)
			self.f_status.setVisible(True)
			self.f_connect.setVisible(True)
			self.f_frameRange.setVisible(True)
			self.f_convertExport.setVisible(True)
			if self.cb_manager.count() > 0:
				self.gb_submit.setVisible(True)

			import CreateItem

			typeWin = CreateItem.CreateItem(core=self.core)
			typeWin.setModal(True)
			self.core.parentWindow(typeWin)
			typeWin.setWindowTitle("Outputtype")
			typeWin.l_item.setText("Outputtype:")
			typeWin.exec_()

			if hasattr(typeWin, "itemName"):
				if self.cb_outType.findText(typeWin.itemName) == -1:
					self.cb_outType.insertItem(self.cb_outType.count()-1, typeWin.itemName)

				if typeWin.itemName == "other":
					self.cb_outType.setCurrentIndex(0)
				else:
					self.cb_outType.setCurrentIndex(self.cb_outType.findText(typeWin.itemName))
					
			else:
				self.cb_outType.setCurrentIndex(0)

			if (self.node is None or self.node.type().name() in ["rop_alembic", "alembic", "pixar::usdrop", "Redshift_Proxy_Output"] or self.node.canCreateDigitalAsset() or self.node.type().definition() is not None) and createMissing:
				self.createNode()
			
		else:
			self.f_cam.setVisible(False)
			self.w_sCamShot.setVisible(False)
			self.w_saveToExistingHDA.setVisible(False)
			self.w_blackboxHDA.setVisible(False)
			self.w_projectHDA.setVisible(False)
			self.f_taskName.setVisible(True)
			self.f_status.setVisible(True)
			self.f_connect.setVisible(True)
			self.f_frameRange.setVisible(True)
			self.f_convertExport.setVisible(True)
			if self.cb_manager.count() > 0:
				self.gb_submit.setVisible(True)
			if (self.node is None or self.node.type().name() in ["rop_alembic", "alembic", "pixar::usdrop", "Redshift_Proxy_Output"] or self.node.canCreateDigitalAsset() or self.node.type().definition() is not None) and createMissing:
				self.createNode()


		self.rjToggled()
		self.updateUi()
		self.stateManager.saveStatesToScene()


	@err_decorator
	def goToNode(self):
		try:
			self.node.name()
		except:
			self.createNode()

		try:
			self.node.name()
		except:
			self.updateUi()
			return False

		self.node.setCurrent(True, clear_all_selected=True)
		paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
		if paneTab is not None:
			paneTab.frameSelection()


	@err_decorator
	def connectNode(self, node=None):
		if node is None:
			if len(hou.selectedNodes()) == 0:
				return False

			node = hou.selectedNodes()[0]

		if node.type().name() in ["rop_geometry", "rop_dop", "rop_comp", "rop_alembic", "filecache", 'pixar::usdrop', "Redshift_Proxy_Output"] or (node.type().category().name() == "Driver" and node.type().name() in ["geometry", "alembic"]) or node.canCreateDigitalAsset() or node.type().definition() is not None:
			self.node = node

			extension = ""
			if self.node.type().name() == "rop_dop":
				extension = os.path.splitext(self.node.parm("dopoutput").eval())[1]
			elif self.node.type().name() == "rop_comp":
				extension = os.path.splitext(self.node.parm("copoutput").eval())[1]
			elif self.node.type().name() == "rop_geometry":
				if self.node.parm("sopoutput").eval().endswith(".bgeo.sc"):
					extension = ".bgeo.sc"
				else:
					extension = os.path.splitext(self.node.parm("sopoutput").eval())[1]
			elif self.node.type().name() == "rop_alembic":
				extension = os.path.splitext(self.node.parm("filename").eval())[1]
			elif self.node.type().name() == "filecache":
				if self.node.parm("file").eval().endswith(".bgeo.sc"):
					extension = ".bgeo.sc"
				else:
					extension = os.path.splitext(self.node.parm("file").eval())[1]
			elif self.node.type().name() == "pixar::usdrop":
				extension = os.path.splitext(self.node.parm("usdfile").eval())[1]
			elif self.node.type().name() == "Redshift_Proxy_Output":
				extension = os.path.splitext(self.node.parm("RS_archive_file").eval())[1]
			elif self.node.type().name() == "geometry" and self.node.type().category().name() == "Driver":
				if self.node.parm("sopoutput").eval().endswith(".bgeo.sc"):
					extension = ".bgeo.sc"
				else:
					extension = os.path.splitext(self.node.parm("sopoutput").eval())[1]
			elif self.node.type().name() == "alembic" and self.node.type().category().name() == "Driver":
				extension = os.path.splitext(self.node.parm("filename").eval())[1]
			elif self.node.canCreateDigitalAsset() or self.node.type().definition() is not None:
				extension = ".hda"

			if self.cb_outType.findText(extension) != -1:
				self.cb_outType.setCurrentIndex(self.cb_outType.findText(extension))
				self.typeChanged(self.cb_outType.currentText(), createMissing=False)

			self.nameChanged(self.e_name.text())
			self.updateUi()
			self.stateManager.saveStatesToScene()
			return True

		return False			


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
	def rjToggled(self,checked=None):
		if checked is None:
			checked = self.gb_submit.isChecked()
		self.checkLocalOutput()
		self.stateManager.saveStatesToScene()


	@err_decorator
	def managerChanged(self, text=None):
		self.checkLocalOutput()
		if self.cb_manager.currentText() in self.core.rfManagers:
			self.core.rfManagers[self.cb_manager.currentText()].sm_houExport_activated(self)
		self.stateManager.saveStatesToScene()


	@err_decorator
	def checkLocalOutput(self):
		fstate = True
		if self.cb_outType.currentText() == ".hda":
			if (self.w_saveToExistingHDA.isEnabled() and self.chb_saveToExistingHDA.isChecked()) or self.chb_projectHDA.isChecked():
				fstate = False
		else:
			fstate = self.gb_submit.isHidden() or not self.gb_submit.isChecked() or (self.gb_submit.isChecked() and self.core.rfManagers[self.cb_manager.currentText()].canOutputLocal)
		self.f_localOutput.setEnabled(fstate)


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
	def preDelete(self, item, silent=False):
		self.core.appPlugin.sm_preDelete(self, item, silent)


	@err_decorator
	def preExecuteState(self):
		warnings = []

		if self.cb_outType.currentText() == "ShotCam":
			if self.curCam is None:
				warnings.append(["No camera specified.", "", 3])
		else:
			if self.l_taskName.text() == "":
				warnings.append(["No taskname is given.", "", 3])

			try:
				self.node.name()
			except:
				warnings.append(["Node is invalid.", "", 3])

		if not hou.simulationEnabled():
			warnings.append(["Houdini simulations are disabled.", "", 3])

		if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
			warnings += self.core.rfManagers[self.cb_manager.currentText()].sm_houExport_preExecute(self)
			
		return [self.state.text(0), warnings]


	@err_decorator
	def getOutputName(self, useVersion="next"):
		fileName = self.core.getCurrentFileName()
		prefUnit = "meter"
		sceneDir = self.core.getConfig('paths', "scenes", configPath=self.core.prismIni)

		if self.cb_outType.currentText() == "ShotCam":
			outputBase = os.path.join(self.core.projectPath, sceneDir, "Shots", self.cb_sCamShot.currentText())

			if self.core.useLocalFiles and self.chb_localOutput.isChecked():
				outputBase = os.path.join(self.core.localProjectPath, sceneDir, "Shots", self.cb_sCamShot.currentText())

			fnameData = os.path.basename(fileName).split(self.core.filenameSeperator)
			if len(fnameData) == 8:
				comment = fnameData[5]
			elif len(fnameData) == 6:
				comment = fnameData[3]

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

			outputPath = os.path.join( outputPath, hVersion + self.core.filenameSeperator + comment + self.core.filenameSeperator + versionUser, prefUnit)
			outputName = os.path.join(outputPath, "shot" + self.core.filenameSeperator + self.cb_sCamShot.currentText() + self.core.filenameSeperator + "ShotCam" + self.core.filenameSeperator + hVersion)

		elif self.cb_outType.currentText() == ".hda" and self.node is not None and self.node.type().definition() is not None and self.chb_saveToExistingHDA.isChecked():
			outputName = self.node.type().definition().libraryFilePath()
			outputPath = os.path.dirname(outputName)
			hVersion = ""

		elif self.cb_outType.currentText() == ".hda" and self.node is not None and self.node.type().definition() is not None and self.chb_projectHDA.isChecked():
			outputName = os.path.join(self.core.projectPath, self.core.getConfig('paths', "assets", configPath=self.core.prismIni), "HDAs", self.l_taskName.text() + ".hda")
			outputPath = os.path.dirname(outputName)
			hVersion = ""

		else:
			if self.l_taskName.text() == "":
				return

			basePath = self.core.projectPath
			if self.core.useLocalFiles:
				if self.chb_localOutput.isChecked() and (self.gb_submit.isHidden() or not self.gb_submit.isChecked() or (self.gb_submit.isChecked() and self.core.rfManagers[self.cb_manager.currentText()].canOutputLocal)):
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

			fnameData = os.path.basename(fileName).split(self.core.filenameSeperator)
			if len(fnameData) == 8:
				outputPath = os.path.abspath(os.path.join(fileName, os.pardir, os.pardir, os.pardir, os.pardir, "Export", self.l_taskName.text()))
				if hVersion == "":
					hVersion = self.core.getHighestTaskVersion(outputPath)
					pComment = fnameData[5]

				outputPath = os.path.join(outputPath, hVersion + self.core.filenameSeperator + pComment + self.core.filenameSeperator + versionUser, prefUnit)
				outputName = os.path.join(outputPath, fnameData[0] + self.core.filenameSeperator + fnameData[1] + self.core.filenameSeperator + self.l_taskName.text() + self.core.filenameSeperator + hVersion + ".$F4" + self.cb_outType.currentText())
			elif len(fnameData) == 6:
				if os.path.join(sceneDir, "Assets", "Scenefiles") in fileName:
					outputPath = os.path.join(self.core.fixPath(basePath), sceneDir, "Assets", "Export", self.l_taskName.text())
				else:
					outputPath = os.path.abspath(os.path.join(fileName, os.pardir, os.pardir, os.pardir, "Export", self.l_taskName.text()))
				if hVersion == "":
					hVersion = self.core.getHighestTaskVersion(outputPath)
					pComment = fnameData[3]

				outputPath = os.path.join( outputPath, hVersion + self.core.filenameSeperator + pComment + self.core.filenameSeperator + versionUser, prefUnit)
				outputName = os.path.join(outputPath, fnameData[0]  + self.core.filenameSeperator + self.l_taskName.text() + self.core.filenameSeperator + hVersion + ".$F4" + self.cb_outType.currentText())
			else:
				return

		return outputName.replace("\\", "/"), outputPath.replace("\\", "/"), hVersion


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

			if self.chb_convertExport.isChecked():
				inputCons = self.curCam.inputConnections()
				if len(inputCons) > 0 and inputCons[0].inputNode().type().name() == "null" and inputCons[0].inputNode().name() == "SCALEOVERRIDE":
					transformNode = inputCons[0].inputNode()
				else:
					transformNode = self.curCam.createInputNode(0, "null", "SCALEOVERRIDE")
					for i in inputCons:
						transformNode.setInput(0, i.inputNode(), i.inputIndex())

			abc_rop = hou.node('/out').createNode('alembic')

			abc_rop.parm('trange').set(1)
			abc_rop.parm('f1').set(startFrame)
			abc_rop.parm('f2').set(endFrame)
			abc_rop.parm('filename').set(outputName + ".abc")
			abc_rop.parm('root').set(self.curCam.parent().path())
			abc_rop.parm('objects').set(self.curCam.name())


			fbx_rop = hou.node('/out').createNode('filmboxfbx')
			fbx_rop.parm('sopoutput').set(outputName + ".fbx")
			fbx_rop.parm('startnode').set(self.curCam.path())

			abc_rop.render()
			fbx_rop.render(frame_range=(startFrame,endFrame))

			if self.chb_convertExport.isChecked():
				transformNode.parm("scale").set(100)

				outputName = os.path.join(os.path.dirname(os.path.dirname(outputName)), "centimeter", os.path.basename(outputName))
				if not os.path.exists(os.path.dirname(outputName)):
					os.makedirs(os.path.dirname(outputName))

				abc_rop.parm('filename').set(outputName + ".abc")
				abc_rop.render()
				fbx_rop.parm('sopoutput').set(outputName + ".fbx")
				fbx_rop.render(frame_range=(startFrame,endFrame))

				transformNode.destroy()

			abc_rop.destroy()
			fbx_rop.destroy()

			self.l_pathLast.setText(outputName)
			self.l_pathLast.setToolTip(outputName)
			self.b_openLast.setEnabled(True)
			self.b_copyLast.setEnabled(True)

			self.core.callHook("postExport", args={"prismCore":self.core, "scenefile":fileName, "startFrame":startFrame, "endFrame":endFrame, "outputName":outputName})

			self.stateManager.saveStatesToScene()

			if os.path.exists(outputName + ".abc") and os.path.exists(outputName + ".fbx"):
				return [self.state.text(0) + " - success"]
			else:
				return [self.state.text(0) + " - error"]

		else:
			if self.l_taskName.text() == "":
				return [self.state.text(0) + ": error - No taskname is given. Skipped the activation of this state."]

			try:
				self.node.name()
			except:
				return [self.state.text(0) + ": error - Node is invalid. Skipped the activation of this state."]

			if not self.node.isEditable() and self.cb_outType.currentText() != ".hda":
				return [self.state.text(0) + ": error - Node is locked. Skipped the activation of this state."]

			fileName = self.core.getCurrentFileName()

			outputName, outputPath, hVersion = self.getOutputName(useVersion=useVersion)

			outLength = len(outputName)
			if platform.system() == "Windows" and outLength > 255:
				return [self.state.text(0) + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, taskname or projectpath." % outLength]

			if self.cb_outType.currentText() == ".hda":
				if not self.node.canCreateDigitalAsset() and self.node.type().definition() is None:
					return [self.state.text(0) + ": error - Cannot create a digital asset from this node: %s" % self.node.path()]
			else:
				if not self.core.appPlugin.setNodeParm(self.node, "trange", val=1):
					return [self.state.text(0) + ": error - Publish canceled"]

				if not self.core.appPlugin.setNodeParm(self.node, "f1", clear=True):
					return [self.state.text(0) + ": error - Publish canceled"]

				if not self.core.appPlugin.setNodeParm(self.node, "f2", clear=True):
					return [self.state.text(0) + ": error - Publish canceled"]

				self.node.parm("f1").set(startFrame)
				self.node.parm("f2").set(endFrame)

				if self.cb_outType.currentText() in [".abc", ".usd"]:
					outputName = outputName.replace(".$F4", "")

				if self.node.type().name() in ["rop_geometry", "rop_alembic", "rop_dop", "geometry", "filecache", "alembic"]:
					if not self.core.appPlugin.setNodeParm(self.node, "initsim", val=True):
						return [self.state.text(0) + ": error - Publish canceled"]

			if not os.path.exists(outputPath):
				os.makedirs(outputPath)

			self.core.callHook("preExport", args={"prismCore":self.core, "scenefile":fileName, "startFrame":startFrame, "endFrame":endFrame, "outputName":outputName})

			self.core.saveVersionInfo(location=os.path.dirname(outputPath), version=hVersion, origin=fileName, fps=startFrame!=endFrame)

			outputNames = [outputName]
			if not self.chb_convertExport.isHidden() and self.chb_convertExport.isChecked():
				inputCons = self.node.inputConnections()
				if len(inputCons) > 0 and inputCons[0].inputNode().type().name() == "xform" and inputCons[0].inputNode().name() == "SCALEOVERRIDE":
					transformNode = inputCons[0].inputNode()
				else:
					transformNode = self.node.createInputNode(0, "xform", "SCALEOVERRIDE")
					for i in inputCons:
						transformNode.setInput(0, i.inputNode(), i.inputIndex())

				outputNames.append(os.path.join(os.path.dirname(os.path.dirname(outputName)), "centimeter", os.path.basename(outputName)))
				if not os.path.exists(os.path.dirname(outputNames[1])):
					os.makedirs(os.path.dirname(outputNames[1]))

			self.l_pathLast.setText(outputNames[0])
			self.l_pathLast.setToolTip(outputNames[0])
			self.b_openLast.setEnabled(True)
			self.b_copyLast.setEnabled(True)

			self.stateManager.saveStatesToScene()

			for idx, outputName in enumerate(outputNames):
				outputName = outputName.replace("\\", "/")
				parmName = False
				if self.node.type().name() == "rop_dop":
					parmName = "dopoutput"
				elif self.node.type().name() == "rop_comp":
					parmName = "copoutput"
				elif self.node.type().name() == "rop_geometry":
					parmName = "sopoutput"
				elif self.node.type().name() == "rop_alembic":
					parmName = "filename"
				elif self.node.type().name() == "filecache":
					parmName = "file"
				elif self.node.type().name() == "pixar::usdrop":
					parmName = "usdfile"
				elif self.node.type().name() == "Redshift_Proxy_Output":
					parmName = "RS_archive_file"
				elif self.node.type().name() == "geometry":
					parmName = "sopoutput"
				elif self.node.type().name() == "alembic":
					parmName = "filename"

				if parmName != False:
					self.stateManager.publishInfos["updatedExports"][self.node.parm(parmName).unexpandedString()] = outputName

					if not self.core.appPlugin.setNodeParm(self.node, parmName, val=outputName):
						return [self.state.text(0) + ": error - Publish canceled"]

				hou.hipFile.save()

				if idx == 1:
					transformNode.parm("scale").set(100)

				if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
					result = self.core.rfManagers[self.cb_manager.currentText()].sm_houExport_submitJob(self, outputName, parent)
				else:
					try:
						result = ""
						if self.cb_outType.currentText() == ".hda":
							HDAoutputName = outputName.replace(".$F4", "")
							bb = self.chb_blackboxHDA.isChecked()
							if self.node.canCreateDigitalAsset():
								typeName = "prism_" + self.l_taskName.text()
								hda = self.node.createDigitalAsset(typeName , hda_file_name=HDAoutputName, description=self.l_taskName.text(), change_node_type=(not bb))
								if bb:
									hou.hda.installFile(HDAoutputName, force_use_assets=True)
									aInst = self.node.parent().createNode(typeName)
									aInst.type().definition().save(file_name=HDAoutputName, template_node=aInst, create_backup=False, compile_contents=bb, black_box=bb)
									aInst.destroy()
								else:
									self.connectNode(hda)
							else:
								if self.chb_saveToExistingHDA.isChecked():
									defs = hou.hda.definitionsInFile(HDAoutputName)
									highestVersion = 0
									basename = self.node.type().name()
									basedescr = self.node.type().description()
									for i in defs:
										name = i.nodeTypeName()
										v = name.split("_")[-1]
										if sys.version[0] == "2":
											v = unicode(v)

										if v.isnumeric():
											if int(v) > highestVersion:
												highestVersion = int(v)
												basename = name.rsplit("_", 1)[0]
												basedescr = i.description().rsplit("_", 1)[0]

									aname = basename + "_" + str(highestVersion + 1)
									adescr = basedescr + "_" + str(highestVersion + 1)

									tmpPath = HDAoutputName + "tmp"
									self.node.type().definition().save(file_name=tmpPath, template_node=self.node, create_backup=False, compile_contents=bb, black_box=bb)
									defs = hou.hda.definitionsInFile(tmpPath)
									defs[0].copyToHDAFile(HDAoutputName, new_name=aname, new_menu_name=adescr)
									os.remove(tmpPath)
									node = self.node.changeNodeType(aname)
									self.connectNode(node)
								else:
									self.node.type().definition().save(file_name=HDAoutputName, template_node=self.node, create_backup=False, compile_contents=bb, black_box=bb)
								
									if self.chb_projectHDA.isChecked():
										oplib = os.path.join(os.path.dirname(HDAoutputName), "ProjectHDAs.oplib").replace("\\", "/")
										hou.hda.installFile(HDAoutputName, oplib, force_use_assets=True)
									else:
										hou.hda.installFile(HDAoutputName, force_use_assets=True)

							self.updateUi()
						else:
							self.node.parm("execute").pressButton()
							if self.node.errors() != () and self.node.errors() != "":
								erStr = ("%s ERROR - houExportnode %s:\n%s" % (time.strftime("%d/%m/%y %X"), self.core.version, self.node.errors()))
					#			self.core.writeErrorLog(erStr)
								result = "Execute failed: " + str(self.node.errors())

						if result == "":
							if len(os.listdir(outputPath)) > 0:
								result = "Result=Success"
							else:
								result = "unknown error (files do not exist)"

					except Exception as e:
						exc_type, exc_obj, exc_tb = sys.exc_info()
						erStr = ("%s ERROR - houExport %s:\n%s" % (time.strftime("%d/%m/%y %X"), self.core.version, traceback.format_exc()))
						self.core.writeErrorLog(erStr)

						return [self.state.text(0) + " - unknown error (view console for more information)"]

				if idx == 1:
					transformNode.parm("scale").set(1)

			self.core.callHook("postExport", args={"prismCore":self.core, "scenefile":fileName, "startFrame":startFrame, "endFrame":endFrame, "outputName":outputName})

			if "Result=Success" in result:
				return [self.state.text(0) + " - success"]
			else:
				erStr = ("%s ERROR - houExportPublish %s:\n%s" % (time.strftime("%d/%m/%y %X"), self.core.version, result))
				if result == "unknown error (files do not exist)":
					QMessageBox.warning(self.core.messageParent, "Warning", "No files were created during the rendering. If you think this is a Prism bug please report it in the forum:\nwww.prism-pipeline.com/forum/\nor write a mail to contact@prism-pipeline.com")
				elif not result.startswith("Execute Canceled") and not result.startswith("Execute failed"):
					self.core.writeErrorLog(erStr)
				return [self.state.text(0) + " - error - " + result]


	@err_decorator
	def getStateProps(self):
		outputTypes = []
		for i in range(self.cb_outType.count()):
			outputTypes.append(str(self.cb_outType.itemText(i)))

		try:
			curNode = self.node.path()
			self.node.setUserData("PrismPath", curNode)
		except:
			curNode = None

		self.curCam
		try:
			curCam = self.curCam.name()
		except:
			curCam = None


		stateProps = {
		"statename":self.e_name.text(),
		"taskname":self.l_taskName.text(),
		"globalrange":str(self.chb_globalRange.isChecked()),
		"startframe":self.sp_rangeStart.value(),
		"endframe":self.sp_rangeEnd.value(),
		"outputtypes":str(outputTypes),
		"curoutputtype": self.cb_outType.currentText(),
		"connectednode": curNode,
		"unitconvert": str(self.chb_convertExport.isChecked()),
		"localoutput":str(self.chb_localOutput.isChecked()),
		"savetoexistinghda":str(self.chb_saveToExistingHDA.isChecked()),
		"projecthda":str(self.chb_projectHDA.isChecked()),
		"blackboxhda":str(self.chb_blackboxHDA.isChecked()),
		"submitrender": str(self.gb_submit.isChecked()),
		"rjmanager":str(self.cb_manager.currentText()),
		"rjprio":self.sp_rjPrio.value(),
		"rjframespertask":self.sp_rjFramesPerTask.value(),
		"rjtimeout":self.sp_rjTimeout.value(),
		"rjsuspended": str(self.chb_rjSuspended.isChecked()),
		"osdependencies": str(self.chb_osDependencies.isChecked()),
		"osupload": str(self.chb_osUpload.isChecked()),
		"ospassets": str(self.chb_osPAssets.isChecked()),
		"osslaves": self.e_osSlaves.text(),
		"curdlgroup":self.cb_dlGroup.currentText(),
		"currentcam": str(curCam),
		"currentscamshot": self.cb_sCamShot.currentText(),
		"lastexportpath": self.l_pathLast.text().replace("\\", "/"),
		"stateenabled":str(self.state.checkState(0))}

		return stateProps