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

try:
	import hou
except:
	pass

class ImportFileClass(object):
	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - hou_ImportFile %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def setup(self, state, core, stateManager, node=None, importPath=None, stateData=None):
		self.state = state
		self.core = core
		self.stateManager = stateManager
		self.e_name.setText(state.text(0))

		self.className = "ImportFile"
		self.listType = "Import"
		self.taskName = None

		self.l_name.setVisible(False)
		self.e_name.setVisible(False)

		self.node = node
		self.fileNode = None
		self.importPath = importPath
		self.updatePrefUnits()

		createEmptyState = QApplication.keyboardModifiers() == Qt.ControlModifier

		if importPath is None and stateData is None and not createEmptyState:
			import TaskSelection
			ts = TaskSelection.TaskSelection(core = core, importState = self)

			core.parentWindow(ts)
			if self.core.uiScaleFactor != 1:
				self.core.scaleUI(self.state, sFactor=0.5)
			ts.exec_()
		
		if self.importPath is not None:
			self.e_file.setText(self.importPath[1])
			result = self.importObject(taskName=self.importPath[0])
			self.importPath = None

			if not result:
				return False
		elif stateData is None and not createEmptyState:
			return False

		self.nameChanged(state.text(0))
		self.connectEvents()

		if stateData is not None:
			self.loadData(stateData)


	@err_decorator
	def loadData(self, data):
		if "statename" in data:
			self.e_name.setText(data["statename"])
		if "filepath" in data:
			self.e_file.setText(data["filepath"])
		if "connectednode" in data:
			self.node = hou.node(data["connectednode"])
			if self.node is None:
				self.node = self.findNode(data["connectednode"])
		if "filenode" in data:
			self.fileNode = hou.node(data["filenode"])
			if self.fileNode is None:
				self.fileNode = self.findNode(data["filenode"])
		if "taskname" in data:
			self.taskName = data["taskname"]
			self.nameChanged(self.e_name.text())
		if "updatepath" in data:
			self.chb_updateOnly.setChecked(eval(data["updatepath"]))
		if "autonamespaces" in data:
			self.chb_autoNameSpaces.setChecked(eval(data["autonamespaces"]))
		if "preferunit" in data:
			self.chb_preferUnit.setChecked(eval(data["preferunit"]))
			self.updatePrefUnits()


	@err_decorator
	def findNode(self, path):
		for node in hou.node("/").allSubChildren():
			if node.userData("PrismPath") is not None and node.userData("PrismPath") == path:
				node.setUserData("PrismPath", node.path())
				return node

		return None


	@err_decorator
	def connectEvents(self):
		self.e_name.textChanged.connect(self.nameChanged)
		self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.e_file.editingFinished.connect(self.pathChanged)
		self.b_browse.clicked.connect(self.browse)
		self.b_browse.customContextMenuRequested.connect(self.openFolder)
		self.b_goTo.clicked.connect(self.goToNode)
		self.b_import.clicked.connect(self.importObject)
		self.b_objMerge.clicked.connect(self.objMerge)
		self.b_importLatest.clicked.connect(self.importLatest)
		self.b_nameSpaces.clicked.connect(self.removeNameSpaces)
		self.b_unitConversion.clicked.connect(self.unitConvert)
		self.chb_updateOnly.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.chb_autoNameSpaces.stateChanged.connect(self.autoNameSpaceChanged)
		self.chb_preferUnit.stateChanged.connect(lambda x: self.updatePrefUnits())


	@err_decorator
	def nameChanged(self, text):
		isShotCam = self.taskName == "ShotCam"
		self.f_nameSpaces.setVisible(not isShotCam)
		self.b_objMerge.setVisible(not isShotCam)

		try:
			self.state.setText(0, text + " (" + self.taskName + ")")
		except:
			self.state.setText(0, text + " (None)")


	@err_decorator
	def pathChanged(self):
		self.stateManager.saveImports()
		self.updateUi()
		self.stateManager.saveStatesToScene()


	@err_decorator
	def browse(self):
		import TaskSelection

		ts = TaskSelection.TaskSelection(core = self.core, importState = self)

		self.core.parentWindow(ts)
		if self.core.uiScaleFactor != 1:
			self.core.scaleUI(self.state, sFactor=0.5)
		ts.exec_()

		if self.importPath is not None:
			self.e_file.setText(self.importPath[1])
			self.importObject(taskName=self.importPath[0])
			self.updateUi()
			self.importPath = None


	@err_decorator
	def openFolder(self, pos):
		path = hou.expandString(self.e_file.text())
		if os.path.isfile(path):
			path = os.path.dirname(path)

		self.core.openFolder(path)


	@err_decorator
	def goToNode(self):
		try:
			self.node.name()
		except:
			self.updateUi()
			return False

		if self.node.type().name() == "alembicarchive":
			self.node.setCurrent(True, clear_all_selected=True)
		else:
			self.node.children()[0].setCurrent(True, clear_all_selected=True)

		paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
		if paneTab is not None:
			paneTab.frameSelection()


	@err_decorator
	def autoNameSpaceChanged(self, checked):
		self.b_nameSpaces.setEnabled(not checked)
		if checked:
			self.removeNameSpaces()
		self.stateManager.saveStatesToScene()


	@err_decorator
	def importObject(self, taskName = None, objMerge=True):
		fileName = self.core.getCurrentFileName()
		impFileName = self.e_file.text().replace("\\", "/")

		if self.e_file.text() != "":
			versionInfoPath = os.path.join(os.path.dirname(os.path.dirname(self.e_file.text())), "versioninfo.ini")
			if os.path.exists(versionInfoPath):
				vConfig = ConfigParser()
				vConfig.read(versionInfoPath)
				if vConfig.has_option("information", "fps"):
					impFPS = float(vConfig.get("information", "fps"))
					curFPS = self.core.getFPS()
					if impFPS != curFPS:
						fString = "The FPS of the import doesn't match the FPS of the current scene:\n\nCurrent scene FPS:\t%s\nImport FPS:\t\t%s" % (curFPS, impFPS)
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

				if len(vName.split(self.core.filenameSeperator)) == 3 and (os.path.join(self.core.projectPath, self.core.getConfig('paths', "scenes", configPath=self.core.prismIni)).replace("\\", "/") in self.e_file.text().replace("\\", "/") or (self.core.useLocalFiles and os.path.join(self.core.localProjectPath, self.core.getConfig('paths', "scenes", configPath=self.core.prismIni)).replace("\\", "/") in self.e_file.text().replace("\\", "/"))):
					taskName = os.path.basename(os.path.dirname(vPath))
					if taskName == "_ShotCam":
						taskName = "ShotCam"
				else:
					taskName = vName

			taskName = taskName.replace("$", "_")
			self.taskName = taskName

			parDirName = os.path.basename(os.path.dirname(impFileName))
			if parDirName in ["centimeter", "meter"]:
				prefFile = os.path.join(os.path.dirname(os.path.dirname(impFileName)), self.preferredUnit, os.path.basename(impFileName))
				if parDirName == self.unpreferredUnit and os.path.exists(prefFile):
					impFileName = prefFile
					self.e_file.setText(impFileName)

			self.core.callHook("preImport", args={"prismCore":self.core, "scenefile":fileName, "importfile":impFileName})

			try:
				self.node.path()
			except:
				self.node = None
				self.fileNode = None

			if os.path.splitext(impFileName)[1] == ".hda":
				try:
					self.node.destroy()
				except:
					pass

				if os.path.exists(impFileName):
					hou.hda.installFile(impFileName)
			elif self.node is None or self.fileNode is None or not self.chb_updateOnly.isChecked() or (self.fileNode is not None and (self.fileNode.type().name() == "alembic") == (os.path.splitext(impFileName)[1] != ".abc")) or self.node.type().name() == "subnet":
				if self.node is not None:
					try:
						self.node.destroy()
					except:
						pass

				nwBox = hou.node("/obj").findNetworkBox("Import")
				if nwBox is None:
					nwBox = hou.node("/obj").createNetworkBox("Import")
					nwBox.setComment("Imports")
					#nwBox.setMinimized(True)

				if os.path.splitext(impFileName)[1] == ".abc" and "_ShotCam_" in impFileName:
					self.fileNode = None
					self.node = hou.node("/obj").createNode("alembicarchive", "IMPORT_ShotCam")
					self.node.parm("fileName").set(impFileName)
					self.node.parm("buildHierarchy").pressButton()
					self.node.moveToGoodPosition()
				else:
					self.node = hou.node("/obj").createNode("geo", "IMPORT_" + taskName)
					self.node.moveToGoodPosition()

					if len(self.node.children()) > 0:
						self.node.children()[0].destroy()
					if os.path.splitext(impFileName)[1] == ".abc":
						self.fileNode = self.node.createNode("alembic")
						self.fileNode.moveToGoodPosition()
						self.fileNode.parm("fileName").set(impFileName)
						self.fileNode.parm("loadmode").set(1)
						self.fileNode.parm("groupnames").set(3)
					elif os.path.splitext(impFileName)[1] == ".fbx":
						self.node.destroy()

						tlSettings = [hou.frame()]
						tlSettings += hou.playbar.playbackRange()

						self.node = hou.hipFile.importFBX(impFileName)[0]

						setGobalFrangeExpr = "tset `(%d-1)/$FPS` `%d/$FPS`" % (tlSettings[1], tlSettings[2])
						hou.hscript(setGobalFrangeExpr)
						hou.playbar.setPlaybackRange(tlSettings[1], tlSettings[2])
						hou.setFrame(tlSettings[0])

						self.node.setName("IMPORT_" + taskName, unique_name=True)
						fbxObjs = [x for x in self.node.children() if x.type().name() == "geo"]
						mergeGeo = self.node.createNode("geo", "FBX_Objects")
						mergeGeo.moveToGoodPosition()
						if len(mergeGeo.children()) > 0:
							mergeGeo.children()[0].destroy()
						self.fileNode = mergeGeo.createNode("merge", "Merged_Objects")
						self.fileNode.moveToGoodPosition()
						for i in fbxObjs:
							i.setDisplayFlag(False)
							objmerge = mergeGeo.createNode("object_merge", i.name())
							objmerge.moveToGoodPosition()
							objmerge.parm("objpath1").set(i.path())
							objmerge.parm("xformtype").set(1)
							self.fileNode.setNextInput(objmerge)

						mergeGeo.layoutChildren()
						self.node.layoutChildren()
					elif os.path.splitext(impFileName)[1] == ".usd":
						self.fileNode = self.node.createNode("pixar::usdimport")
						self.fileNode.moveToGoodPosition()
						self.fileNode.parm("import_file").set(impFileName)
						self.fileNode.parm("import_primpath").set("/")
						self.fileNode.parm("import_time").setExpression("$F")
					elif os.path.splitext(impFileName)[1] == ".rs":
						if hou.nodeType(hou.sopNodeTypeCategory(), "Redshift_Proxy_Output") is None:
							QMessageBox.warning(self.core.messageParent, "ImportFile", "Format is not supported, because Redshift is not available in Houdini.")
							if nwBox is not None:
								if len(nwBox.nodes()) == 0:
									nwBox.destroy()
							try:
								self.node.destroy()
							except:
								pass
							self.fileNode = None
							return

						self.fileNode = self.node.createNode("redshift_proxySOP")
						self.fileNode.moveToGoodPosition()
						self.node.setCurrent(True, clear_all_selected=True)
						hou.hscript("Redshift_objectSpareParameters")
						self.node.parm("RS_objprop_proxy_enable").set(True)
						self.node.parm("RS_objprop_proxy_file").set(impFileName)
					else:
						self.fileNode = self.node.createNode("file")
						self.fileNode.moveToGoodPosition()
						self.fileNode.parm("file").set(impFileName)

					outNode = self.fileNode.createOutputNode("null", "OUT_" + taskName)
					outNode.setDisplayFlag(True)
					outNode.setRenderFlag(True)

				nwBox.addNode(self.node)
				self.node.moveToGoodPosition()
				nwBox.fitAroundContents()

				self.node.setDisplayFlag(False)
				self.node.setColor(hou.Color(0.451, 0.369, 0.796))

				if self.chb_autoNameSpaces.isChecked():
					self.removeNameSpaces()

				if objMerge and "outNode" in locals():
					self.objMerge()

			else:
				prevData = self.node.name().split("IMPORT_")
				if len(prevData) > 1:
					prevTaskName = prevData[1]
				else:
					prevTaskName = self.node.name()

				self.node.setName("IMPORT_" + taskName, unique_name=True)
				for i in self.node.children():
					if prevTaskName in i.name():
						i.setName(i.name().replace(prevTaskName, taskName), unique_name=True)
						
				if os.path.splitext(impFileName)[1] == ".abc" and "_ShotCam_" in impFileName:
					self.node.parm("fileName").set(impFileName)
					self.node.parm("buildHierarchy").pressButton()
				else:
					if os.path.splitext(impFileName)[1] == ".abc":
						self.fileNode.parm("fileName").set(impFileName)
					elif os.path.splitext(impFileName)[1] == ".usd":
						self.fileNode.parm("import_file").set(impFileName)
					else:
						self.fileNode.parm("file").set(impFileName)

		impNodes = []
		try:
			curNode = self.node.path()
			impNodes.append(curNode)
		except:
			pass

		try:
			fNode = self.fileNode.path()
			impNodes.append(fNode)
		except:
			pass

		self.core.callHook("postImport", args={"prismCore":self.core, "scenefile":fileName, "importfile":impFileName, "importedObjects":impNodes})

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
					for m in i[2]:
						if os.path.splitext(m)[1] not in [".txt", ".ini"]:
							splitFile = os.path.splitext(os.path.join(i[0], m))
							if splitFile[0][-5] != "v":
								try:
									num = int(splitFile[0][-4:])
									filename = splitFile[0][:-4] + "$F4" + splitFile[1]
								except:
									filename = os.path.join(i[0], m)
							else:
								filename = os.path.join(i[0], m)

							if filename.endswith(".mtl") and os.path.exists(filename[:-3] + "obj"):
								filename = filename[:-3] + "obj"
								
							self.e_file.setText(filename)
							self.importObject(objMerge=False)
							break
				break


	@err_decorator
	def objMerge(self):
		paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
		if paneTab is None:
			return

		nodePath = paneTab.pwd()

		if nodePath.isInsideLockedHDA():
			return

		if os.path.splitext(self.e_file.text())[1] == ".hda":
			if os.path.exists(self.e_file.text()):
				defs = hou.hda.definitionsInFile(self.e_file.text().replace("\\", "/"))
				if len(defs) > 0:
					tname = defs[0].nodeTypeName()
					mNode = None
					try:
						mNode = nodePath.createNode(tname)
						mNode.moveToGoodPosition()
					except:
						return
			if mNode is None:
				return
		else:
			try:
				x = self.node.path()
			except:
				return

			mNode = None
			try:
				mNode = nodePath.createNode("object_merge")
				mNode.moveToGoodPosition()
			except:
				return

			outNodePath = ""
			if self.node.type().name() == "subnet":
				for i in self.node.children():
					if getattr(i, "isDisplayFlagSet", lambda: None)():
						outNodePath = i.displayNode().path()
						break
			else:
				outNodePath = self.node.displayNode().path()

			mNode.parm("objpath1").set(outNodePath)

		mNode.setDisplayFlag(True)
		if hasattr(mNode, "setRenderFlag"):
			mNode.setRenderFlag(True)
		mNode.setPosition(paneTab.visibleBounds().center())
		mNode.setCurrent(True, clear_all_selected=True)


	@err_decorator
	def updateUi(self):
		if os.path.splitext(self.e_file.text())[1] == ".hda":
			self.gb_options.setVisible(False)
			self.b_goTo.setVisible(False)
			self.b_objMerge.setText("Create Node")
			self.l_status.setText("not installed")
			self.l_status.setStyleSheet("QLabel { background-color : rgb(150,0,0); }")
			if os.path.exists(self.e_file.text()):
				defs = hou.hda.definitionsInFile(self.e_file.text().replace("\\", "/"))
				if len(defs) > 0:
					if defs[0].isInstalled():
						self.l_status.setText("installed")
						self.l_status.setStyleSheet("QLabel { background-color : rgb(0,150,0); }")
		else:
			self.gb_options.setVisible(True)
			self.b_goTo.setVisible(True)
			self.b_objMerge.setText("Create Obj Merge")
			try:
				self.node.name()
				self.l_status.setText(self.node.name())
				self.l_status.setStyleSheet("QLabel { background-color : rgb(0,150,0); }")
				self.b_objMerge.setEnabled(True)
			except:
				self.nameChanged(self.e_name.text())
				self.l_status.setText("Not found in scene")
				self.l_status.setStyleSheet("QLabel { background-color : rgb(150,0,0); }")
				self.b_objMerge.setEnabled(False)

		parDir = os.path.dirname(self.e_file.text())
		if os.path.basename(parDir) in ["centimeter", "meter"]:
			versionData = os.path.basename(os.path.dirname(parDir)).split(self.core.filenameSeperator)
			taskPath = os.path.dirname(os.path.dirname(parDir))
		else:
			versionData = os.path.basename(parDir).split(self.core.filenameSeperator)
			taskPath = os.path.dirname(parDir)

		if len(versionData) == 3 and self.core.getConfig('paths', "scenes", configPath=self.core.prismIni) in self.e_file.text():
			self.l_curVersion.setText(versionData[0] + self.core.filenameSeperator + versionData[1] + self.core.filenameSeperator + versionData[2])
			self.l_latestVersion.setText("-")
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

		if self.l_curVersion.text() != self.l_latestVersion.text() and self.l_curVersion.text() != "-" and self.l_latestVersion.text() != "-":
			self.b_importLatest.setStyleSheet("QPushButton { background-color : rgb(180,90,0); }")
		else:
			self.b_importLatest.setStyleSheet("")

		self.nameChanged(self.e_name.text())


	@err_decorator
	def removeNameSpaces(self):
		outputCons = self.fileNode.outputConnections()

		for i in outputCons:
			if i.outputNode().type().name() == "grouprename" and i.outputNode().name() == "RemoveMayaNameSpaces":
				return

			if i.outputNode().type().name() == "xform" and i.outputNode().name() == "UnitConversion":
				outputConsUnit = i.outputNode().outputConnections()

				for k in outputConsUnit:
					if k.outputNode().type().name() == "grouprename" and k.outputNode().name() == "RemoveMayaNameSpaces":
						return

		renameNode = self.fileNode.createOutputNode("grouprename", "RemoveMayaNameSpaces")
		for i in outputCons:
			i.outputNode().setInput(i.inputIndex(), renameNode, 0)

		groups = renameNode.geometry().primGroups()
		renames = 0
		for idx, val in enumerate(groups):
			groupName = val.name()
			newName = groupName.rsplit("_", 1)[-1]
			if newName != groupName:
				renames += 1
				renameNode.parm("renames").set(renames)
				renameNode.parm("group" + str(renames)).set(groupName)
				renameNode.parm("newname" + str(renames)).set(newName + "_" + str(renames))

		self.fileNode.parent().layoutChildren()


	@err_decorator
	def unitConvert(self):
		if self.taskName == "ShotCam":
			xforms = [x for x in self.node.children() if x.type().name() == "alembicxform"]
			if len(xforms) == 0:
				return

			xNode = xforms[0]

			inputCons = xNode.inputConnections()
			unitNode = xNode.createInputNode(0, "null", "UnitConversion")

			for i in inputCons:
				if i.inputNode() is None:
					unitNode.setInput(0, i.subnetIndirectInput(), 0)
				else:
					unitNode.setInput(0, i.inputNode(), 0)

			unitNode.parm("scale").set(0.01)
			self.node.layoutChildren()
		else:
			outputCons = self.fileNode.outputConnections()

			unitNode = None
			for i in outputCons:
				if i.outputNode().type().name() == "xform" and i.outputNode().name() == "UnitConversion":
					unitNode = i.outputNode()

				if i.outputNode().type().name() == "grouprename" and i.outputNode().name() == "RemoveMayaNameSpaces":
					outputConsNS = i.outputNode().outputConnections()

					for k in outputConsNS:
						if k.outputNode().type().name() == "xform" and k.outputNode().name() == "UnitConversion":
							unitNode = k.outputNode()

			if unitNode is None:
				unitNode = self.fileNode.createOutputNode("xform", "UnitConversion")

				for i in outputCons:
					i.outputNode().setInput(i.inputIndex(), unitNode, 0)

			unitNode.parm("scale").set(0.01)
			self.fileNode.parent().layoutChildren()


	@err_decorator
	def updatePrefUnits(self):
		if self.chb_preferUnit.isChecked():
			self.preferredUnit = "centimeter"
			self.unpreferredUnit = "meter"
		else:
			self.preferredUnit = "meter"
			self.unpreferredUnit = "centimeter"


	@err_decorator
	def preDelete(self, item, silent=False):
		self.core.appPlugin.sm_preDelete(self, item, silent)


	@err_decorator
	def getStateProps(self):
		try:
			curNode = self.node.path()
			self.node.setUserData("PrismPath", curNode)
		except:
			curNode = None

		try:
			fNode = self.fileNode.path()
			self.fileNode.setUserData("PrismPath", fNode)
		except:
			fNode = None

		return {"statename":self.e_name.text(), "filepath": self.e_file.text(), "connectednode": curNode, "filenode": fNode, "taskname":self.taskName, "updatepath": str(self.chb_updateOnly.isChecked()), "autonamespaces": str(self.chb_autoNameSpaces.isChecked()), "preferunit": str(self.chb_preferUnit.isChecked())}