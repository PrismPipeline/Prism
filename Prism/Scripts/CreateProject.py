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



import sys, os, copy, shutil, imp, time, traceback, platform

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

if sys.version[0] == "3":
	pVersion = 3
else:
	pVersion = 2

for i in ["CreateProject_ui", "CreateProject_ui_ps2"]:
	try:
		del sys.modules[i]
	except:
		pass

sys.path.append(os.path.join(os.path.dirname(__file__), "UserInterfacesPrism"))

if psVersion == 1:
	import CreateProject_ui
else:
	import CreateProject_ui_ps2 as CreateProject_ui

from UserInterfacesPrism import qdarkstyle

try:
	import ProjectCreated
except:
	modPath = imp.find_module("ProjectCreated")[1]
	if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
		os.remove(modPath)
	import ProjectCreated


class CreateProject(QDialog, CreateProject_ui.Ui_dlg_createProject):
	def __init__(self, core):
		QDialog.__init__(self)
		self.setupUi(self)
		self.core = core
		self.core.parentWindow(self)
	
		self.core.appPlugin.createProject_startup(self)

		nameTT = "The name of the new project.\nThe project name will be visible at different locations in the Prism user interface."
		self.l_name.setToolTip(nameTT)
		self.e_name.setToolTip(nameTT)
		pathTT = "This is the directory, where the project will be saved.\nThis folder should be empty or should not exist.\nThe project name will NOT be appended automatically to this path."
		self.l_path.setToolTip(pathTT)
		self.e_path.setToolTip(pathTT)
		self.b_browse.setToolTip("Select a folder on the current PC")
		self.gb_folderStructure.setToolTip("This list defines the top-level folder structure of the project.\nDouble-Click a name or a type to edit an existing folder.\nFoldertypes marked with an \"*\" have to be defined before the project can be created.\nAdditional folders can be created manually later on.")

		self.fillDirStruct()
		self.connectEvents()

		self.e_name.setFocus()


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - CreateProject %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def enterEvent(self, event):
		QApplication.restoreOverrideCursor()


	@err_decorator
	def connectEvents(self):
		self.b_browse.clicked.connect(self.browse)
		self.e_name.textEdited.connect(lambda x: self.validateText(x, self.e_name))
		self.e_path.textEdited.connect(lambda x: self.validateText(x, self.e_path))
		
		self.tw_dirStruct.mousePrEvent = self.tw_dirStruct.mousePressEvent
		self.tw_dirStruct.mousePressEvent = lambda x: self.mouseClickEvent(x)
		self.tw_dirStruct.mouseClickEvent = self.tw_dirStruct.mouseReleaseEvent
		self.tw_dirStruct.mouseReleaseEvent = lambda x: self.mouseClickEvent(x)
		self.tw_dirStruct.doubleClicked.connect(self.dClickItem)

		self.b_addDir.clicked.connect(self.addDir)
		self.b_delDir.clicked.connect(self.delDir)
		self.b_upDir.clicked.connect(self.upDir)
		self.b_downDir.clicked.connect(self.downDir)

		self.b_create.clicked.connect(self.createClicked)


	@err_decorator
	def mouseClickEvent(self, event):
		if QEvent != None:
			if event.type() == QEvent.MouseButtonRelease:
				if event.button() == Qt.LeftButton:
					index = self.tw_dirStruct.indexAt(event.pos())
					if index.data() == None:
						self.tw_dirStruct.setCurrentIndex(self.tw_dirStruct.model().createIndex(-1,0))
					self.tw_dirStruct.mouseClickEvent(event)

			else:
				self.tw_dirStruct.mousePrEvent(event)


	@err_decorator
	def validateText(self, origText, pathUi):
		if pathUi == self.e_name:
			allowChars = ["_"]
		else:
			allowChars = ["/", "\\", "_", " ", ":"]

		validText = self.core.validateStr(origText, allowChars=allowChars)		

		if len(validText) != len(origText):
			cpos = pathUi.cursorPosition()
			pathUi.setText(validText)
			pathUi.setCursorPosition(cpos-1)


	@err_decorator
	def browse(self):
		path = QFileDialog.getExistingDirectory(self.core.messageParent, "Select project folder", self.e_path.text())
		if path != "":
			self.e_path.setText(path)
			self.validateText(path, self.e_path)


	@err_decorator
	def fillDirStruct(self):
		model = QStandardItemModel()
		model.setHorizontalHeaderLabels(["Prefix","Name", "Type"])
		self.tw_dirStruct.setModel(model)
		self.tw_dirStruct.setColumnWidth(1,300)

		self.addDir("Management", "Default")
		self.addDir("Designs", "Default")
		self.addDir("Workflow", "Scenes*")
		self.addDir("Assets", "Assets*")
		self.addDir("Dailies", "Dailies")


	@err_decorator
	def dClickItem(self, index):
		if index.column() == 1:
			self.tw_dirStruct.edit(index)
		elif index.column() == 2:
			model = self.tw_dirStruct.model()
			existingTypes = []
			for i in range(model.rowCount()):
				rType = model.index(i,2).data()
				existingTypes.append(rType)

			typeMenu = QMenu()
			pos = self.tw_dirStruct.mapFromGlobal(QCursor.pos())
			pos.setY(pos.y()-23)
			idx = self.tw_dirStruct.indexAt(pos)

			for i in ["Scenes*", "Assets*", "Dailies"]:
				if i not in existingTypes:
					cAct = QAction(i, self)
					cAct.triggered.connect(lambda y=None, x=i: model.setData(idx, x))
					typeMenu.addAction(cAct)

			cAct = QAction("Default", self)
			cAct.triggered.connect(lambda: model.setData(idx, "Default"))
			typeMenu.addAction(cAct)
			self.core.appPlugin.setRCStyle(self, typeMenu)

			typeMenu.exec_(QCursor.pos())


	@err_decorator
	def addDir(self, name="", dirType="Default"):
		model = self.tw_dirStruct.model()
		row = []
		row.append(QStandardItem("%02d_" % (model.rowCount()+1)))
		row.append(QStandardItem(name))
		row.append(QStandardItem(dirType))

		model.appendRow(row)


	@err_decorator
	def delDir(self):
		selIdx = self.tw_dirStruct.selectedIndexes()
		if len(selIdx) > 0:
			model = self.tw_dirStruct.model()
			model.removeRow(selIdx[0].row())
			self.refreshPrefix()


	@err_decorator
	def upDir(self):
		selIdx = self.tw_dirStruct.selectedIndexes()
		if len(selIdx) > 0 and selIdx[0].row() > 0:
			model = self.tw_dirStruct.model()
			row = []
			row.append(QStandardItem(""))
			row.append(QStandardItem(model.index(selIdx[0].row(), 1).data()))
			row.append(QStandardItem(model.index(selIdx[0].row(), 2).data()))
			model.insertRow(selIdx[0].row()-1, row)
			self.tw_dirStruct.setCurrentIndex(model.index(selIdx[0].row()-1, 0))
			model.removeRow(selIdx[0].row()+1)
			self.refreshPrefix()


	@err_decorator
	def downDir(self):
		selIdx = self.tw_dirStruct.selectedIndexes()
		model = self.tw_dirStruct.model()
		if len(selIdx) > 0 and (selIdx[0].row()+1) < model.rowCount():
			row = []
			row.append(QStandardItem(""))
			row.append(QStandardItem(model.index(selIdx[0].row(), 1).data()))
			row.append(QStandardItem(model.index(selIdx[0].row(), 2).data()))
			model.insertRow(selIdx[0].row()+2, row)
			self.tw_dirStruct.setCurrentIndex(model.index(selIdx[0].row()+2, 0))
			model.removeRow(selIdx[0].row())

			self.refreshPrefix()


	@err_decorator
	def refreshPrefix(self):
		model = self.tw_dirStruct.model()
		for i in range(model.rowCount()):
			model.setData(model.index(i,0), "%02d_" % (i+1))


	@err_decorator
	def create(self, name, path, settings={}):
		prjName = name
		prjPath = path

		pipeline_steps = settings.get("pipeline_steps", str({"mod": "Modeling",
									"shd": "Shading",
									"rig": "Rigging",
									"anm": "Animation",
									"ren": "Rendering",
									"rnd": "Research",
									"sim": "Simulation",
									"cmp": "Compositing"}))

		uselocalfiles = settings.get("uselocalfiles", "False")
		checkframerange = settings.get("checkframerange", "True")
		forcefps = settings.get("forcefps", "False")
		fps = settings.get("fps", "24")
		forceversions = settings.get("forceversions", "False")
		filenameseperator = settings.get("filenameseperator", "_")

		#check valid project name
		if not prjName:
			self.core.popup("The project name is invalid")
			return

		#create project folder
		if not os.path.isabs(prjPath):
			self.core.popup("The project path is invalid")
			return

		if not os.path.exists(prjPath):
			try:
				os.makedirs(prjPath)
			except:
				self.core.popup("The project folder could not be created")
				return
		else:
			if not os.listdir(prjPath) == []:
				if self.core.uiAvailable:
					mStr = "The project folder is not empty.\nExisting files will be overwritten.\n"
					msg = QMessageBox(QMessageBox.Warning, "Project setup", mStr, QMessageBox.Cancel)
					msg.addButton("Continue", QMessageBox.YesRole)
					self.core.parentWindow(msg)
					action = msg.exec_()

					if action != 0:
						return
				else:
					self.core.popup("Project directory already exists.")
					if os.path.exists(os.path.join(prjPath, "00_Pipeline", "pipeline.ini")):
						return True
					else:
						return

		model = self.tw_dirStruct.model()
		pfolders = []

		#adding numbers to the foldernames
		for i in range(model.rowCount()):
			fName = model.index(i,1).data()
			if fName != "":
				pfolders.append([model.index(i,0).data() + fName, model.index(i,2).data()])

		#check if all required folders are defined
		req = ["Scenes*", "Assets*"]

		for i in req:
			if i not in [x[1] for x in pfolders]:
				self.core.popup("Not all required folders are defined")
				return

		# create folders

		pPath = os.path.join(prjPath, "00_Pipeline")

		if os.path.exists(pPath):
			try:
				shutil.rmtree(pPath)
			except:
				self.core.popup("Could not remove folder \"%s\"" % pPath)
				return

		try:
			shutil.copytree(os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, "ProjectFiles")), pPath)
		except Exception as e:
			self.core.popup("Could not copy folders to %s.\n\n%s" % (pPath, str(e)))
			return

		for i in (pf for pf in pfolders if not os.path.exists(os.path.join(prjPath, pf[0]))):
			try:
				os.makedirs(os.path.join(prjPath, i[0]))
			except:
				self.core.popup("Could not create folder \"%s\"" % i[0])
				return

		#create ini file

		inipath = os.path.join(pPath, "pipeline.ini")
		for i in pfolders:
			if i[1] == "Scenes*":
				scname = i[0]
			if i[1] == "Assets*":
				assetname = i[0]
			if i[1] == "Dailies":
				dailiesname = i[0]

		cfolders = [os.path.join(prjPath, scname, "Assets"), os.path.join(prjPath, scname, "Shots"), os.path.join(prjPath, assetname, "Textures"), os.path.join(prjPath, assetname, "HDAs")]

		for i in cfolders:
			if not os.path.exists(i):
				os.makedirs(i)

		cData = []

		cData.append(['globals', 'project_name', prjName])
		cData.append(['globals', 'prism_version', self.core.version])
		cData.append(['globals', "pipeline_steps", pipeline_steps])
		cData.append(['globals', 'uselocalfiles', uselocalfiles])
		cData.append(['globals', 'checkframerange', checkframerange])
		cData.append(['globals', 'forcefps', forcefps])
		cData.append(['globals', 'fps', fps])
		cData.append(['globals', 'forceversions', forceversions])
		cData.append(['globals', 'filenameseperator', filenameseperator])
		cData.append(['paths', 'pipeline', "00_Pipeline"])
		cData.append(['paths', 'scenes', scname])
		cData.append(['paths', 'assets', assetname])
		if "dailiesname" in locals():
			cData.append(['paths', 'dailies', dailiesname])

		for i in self.core.getPluginNames():
			passes = self.core.getPluginData(i, "renderPasses")
			if type(passes) == list:
				cData += passes

		self.core.setConfig(data=cData, configPath=inipath)

		self.inipath = inipath

		self.core.callback(name="onProjectCreated", types=["curApp", "unloadedApps", "custom"], args=[self, prjPath, prjName])
		return True


	@err_decorator
	def createClicked(self):
		prjName = self.e_name.text()
		prjPath = self.e_path.text()
		result = self.create(name=prjName, path=prjPath)

		if result:
			self.core.changeProject(self.inipath)
			self.pc = ProjectCreated.ProjectCreated(prjName, core=self.core, basepath=prjPath)
			self.pc.exec_()

			self.close()


	@err_decorator
	def closeEvent(self, event):
		self.setParent(None)



def createProject(core, name, path, settings={}):
	cp = CreateProject(core=core)
	return cp.create(name, path, settings)


if __name__ == "__main__":
	qapp = QApplication(sys.argv)
	qapp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))
	appIcon = QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "UserInterfacesPrism", "p_tray.png"))
	qapp.setWindowIcon(appIcon)
	import PrismCore
	pc = PrismCore.PrismCore()
	try:
		pc.createProject()
	except Exception as e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		print ("ERROR -- %s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno))

	qapp.exec_()