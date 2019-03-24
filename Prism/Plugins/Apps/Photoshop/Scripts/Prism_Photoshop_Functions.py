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



import os, sys, platform, subprocess
import traceback, time
from functools import wraps

try:
	from PySide2.QtCore import *
	from PySide2.QtGui import *
	from PySide2.QtWidgets import *
	psVersion = 2
except:
	from PySide.QtCore import *
	from PySide.QtGui import *
	psVersion = 1

if platform.system() == "Windows":
	import win32com.client


class Prism_Photoshop_Functions(object):
	def __init__(self, core, plugin):
		self.core = core
		self.plugin = plugin
		self.win = platform.system() == "Windows"


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			exc_info = sys.exc_info()
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - Prism_Plugin_Photoshop %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].plugin.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def startup(self, origin):
		origin.timer.stop()

		with (open(os.path.join(self.core.prismRoot, "Plugins", "Apps", "Photoshop", "UserInterfaces", "PhotoshopStyleSheet", "Photoshop.qss"), "r")) as ssFile:
		    ssheet = ssFile.read()

		ssheet = ssheet.replace("qss:", os.path.join(self.core.prismRoot, "Plugins", "Apps", "Photoshop", "UserInterfaces", "PhotoshopStyleSheet").replace("\\", "/") + "/")
		#ssheet = ssheet.replace("#c8c8c8", "rgb(40, 40, 40)").replace("#727272", "rgb(83, 83, 83)").replace("#5e90fa", "rgb(89, 102, 120)").replace("#505050", "rgb(70, 70, 70)")
		#ssheet = ssheet.replace("#a6a6a6", "rgb(145, 145, 145)").replace("#8a8a8a", "rgb(95, 95, 95)").replace("#b5b5b5", "rgb(155, 155, 155)").replace("#999999", "rgb(105, 105, 105)")
		#ssheet = ssheet.replace("#9f9f9f", "rgb(58, 58, 58)").replace("#b2b2b2", "rgb(58, 58, 58)").replace("#aeaeae", "rgb(65, 65, 65)").replace("#c1c1c1", "rgb(65, 65, 65)")

		qApp.setStyleSheet(ssheet)
		appIcon = QIcon(os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "p_tray.png"))
		qApp.setWindowIcon(appIcon)

		if self.win:
			# CS6: .60, CC2015: .90
			self.psApp = win32com.client.Dispatch("Photoshop.Application")
		else:
			self.psAppName = "Adobe Photoshop CC 2019"
			for foldercont in os.walk("/Applications"):
				for folder in reversed(sorted(foldercont[1])):
					if folder.startswith("Adobe Photoshop"):
						self.psAppName = folder
						break
				break

			scpt = '''
			tell application "%s"
				activate
			end tell
			''' % self.psAppName
			self.executeAppleScript(scpt)

		return False


	@err_decorator
	def onProjectChanged(self, origin):
		pass


	@err_decorator
	def sceneOpen(self, origin):
		pass


	@err_decorator
	def executeScript(self, origin, code, preventError=False):
		if preventError:
			try:
				return eval(code)
			except Exception as e:
				msg = '\npython code:\n%s' % code
				exec("raise type(e), type(e)(e.message + msg), sys.exc_info()[2]")
		else:
			return eval(code)


	@err_decorator
	def executeAppleScript(self, script):
		p = subprocess.Popen(['osascript'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = p.communicate(script)
		if p.returncode != 0:
			return None

		return stdout


	@err_decorator
	def getCurrentFileName(self, origin, path=True):
		try:
			if self.win:
				doc = self.psApp.Application.ActiveDocument
				currentFileName = doc.FullName
			else:
				scpt = '''
				tell application "%s"
					set fpath to file path of current document
					POSIX path of fpath
				end tell
				''' % self.psAppName
				currentFileName = self.executeAppleScript(scpt)

				if currentFileName is None:
					raise
		except:
			currentFileName = ""

		if not path and currentFileName != "":
			currentFileName = os.path.basename(currentFileName)

		return currentFileName


	@err_decorator
	def getSceneExtension(self, origin):
		return self.sceneFormats[0]


	@err_decorator
	def saveScene(self, origin, filepath):
		try:
			if self.win:
				doc = self.psApp.ActiveDocument
			else:
				doc = self.core.getCurrentFileName()
				if doc == "":
					raise
		except:
			QMessageBox.warning(self.core.messageParent, "Warning", "There is no active document in Photoshop.")
			return

		try:
			if self.win:
				doc.SaveAs(filepath) 
			else:
				scpt = '''
				tell application "%s"
					save current document in file "%s"
				end tell
				''' % (self.psAppName, filepath)
				doc = self.executeAppleScript(scpt)

				if doc is None:
					raise
		except:
			return ""


	@err_decorator
	def getImportPaths(self, origin):
		return False


	@err_decorator
	def getFrameRange(self, origin):
		pass


	@err_decorator
	def setFrameRange(self, origin, startFrame, endFrame):
		pass


	@err_decorator
	def getFPS(self, origin):
		pass


	@err_decorator
	def getAppVersion(self, origin):
		if self.win:
			version = self.psApp.Version
		else:
			scpt = '''
				tell application "%s"
					application version
				end tell
			''' % self.psAppName
			version = self.executeAppleScript(scpt)

		return version
		

	@err_decorator
	def onProjectBrowserStartup(self, origin):
		origin.loadOiio()
		origin.actionStateManager.setEnabled(False)
		psMenu = QMenu("Photoshop")
		psAction = QAction("Open tools", origin)
		psAction.triggered.connect(self.openPhotoshopTools)
		psMenu.addAction(psAction)
		origin.menuTools.addSeparator()
		origin.menuTools.addMenu(psMenu)


	@err_decorator
	def projectBrowserLoadLayout(self, origin):
		pass


	@err_decorator
	def setRCStyle(self, origin, rcmenu):
		pass


	@err_decorator
	def openScene(self, origin, filepath, force=False):
		if not force and os.path.splitext(filepath)[1] not in self.sceneFormats:
			return False

		if self.win:
			self.psApp.Open(filepath)
		else:
			scpt = '''
				tell application "%s"
					open file "%s"
				end tell
			''' % (self.psAppName, filepath)
			self.executeAppleScript(scpt)

		return True


	@err_decorator
	def correctExt(self, origin, lfilepath):
		return lfilepath


	@err_decorator
	def setSaveColor(self, origin, btn):
		btn.setPalette(origin.savedPalette)


	@err_decorator
	def clearSaveColor(self, origin, btn):
		btn.setPalette(origin.oldPalette)


	@err_decorator
	def importImages(self, origin): 
		fString = "Please select an import option:"
		msg = QMessageBox(QMessageBox.NoIcon, "Photoshop Import", fString, QMessageBox.Cancel)
		msg.addButton("Current pass", QMessageBox.YesRole)
	#	msg.addButton("All passes", QMessageBox.YesRole)
	#	msg.addButton("Layout all passes", QMessageBox.YesRole)
		self.core.parentWindow(msg)
		action = msg.exec_()

		if action == 0:
			self.photoshopImportSource(origin)
	#	elif action == 1:
	#		self.photoshopImportPasses(origin)
	#	elif action == 2:
	#		self.photoshopLayout(origin)
		else:
			return


	@err_decorator
	def photoshopImportSource(self, origin):
		sourceFolder = os.path.dirname(os.path.join(origin.basepath, origin.seq[0])).replace("\\", "/")
		sources = origin.getImgSources(sourceFolder)
		for curSourcePath in sources:

			if "@@@@" in curSourcePath:
				if not hasattr(origin, "pstart") or not hasattr(origin, "pend") or origin.pstart == "?" or origin.pend == "?":
					firstFrame = 0
					lastFrame = 0
				else:
					firstFrame = origin.pstart
					lastFrame = origin.pend

				filePath = curSourcePath.replace("@@@@", "%04d" % firstFrame).replace("\\","/")
			else:
				filePath =  curSourcePath.replace("\\","/")
				firstFrame = 0
				lastFrame = 0

			self.openScene(origin, filePath, force=True)

			#curReadNode = photoshop.createNode("Read",'file %s first %s last %s' % (filePath,firstFrame,lastFrame),False)


	@err_decorator
	def photoshopImportPasses(self, origin):
		sourceFolder = os.path.dirname(os.path.dirname(os.path.join(origin.basepath, origin.seq[0]))).replace("\\", "/")
		passes = [ x for x in os.listdir(sourceFolder) if x[-5:] not in ["(mp4)", "(jpg)", "(png)"] and os.path.isdir(os.path.join(sourceFolder, x))]

		for curPass in passes:
			curPassPath = os.path.join(sourceFolder,curPass)

			imgs = os.listdir(curPassPath)
			if len(imgs) == 0:
				continue

			if len(imgs) > 1:
				if not hasattr(origin, "pstart") or not hasattr(origin, "pend") or origin.pstart == "?" or origin.pend == "?":
					return

				firstFrame = origin.pstart
				lastFrame = origin.pend

				curPassName = imgs[0].split(".")[0]
				increment = "####"
				curPassFormat = imgs[0].split(".")[-1]
	 
				filePath =  os.path.join(sourceFolder,curPass,".".join([curPassName,increment,curPassFormat])).replace("\\","/")
			else:
				filePath =  os.path.join(curPassPath, imgs[0]).replace("\\","/")
				firstFrame = 0
				lastFrame = 0

			curReadNode = photoshop.createNode("Read",'file %s first %s last %s' % (filePath,firstFrame,lastFrame),False)


	@err_decorator
	def setProject_loading(self, origin):
		pass


	@err_decorator
	def onPrismSettingsOpen(self, origin):
		pass


	@err_decorator
	def createProject_startup(self, origin):
		pass


	@err_decorator
	def editShot_startup(self, origin):
		origin.loadOiio()


	@err_decorator
	def shotgunPublish_startup(self, origin):
		pass


	@err_decorator
	def openPhotoshopTools(self):
		self.dlg_tools = QDialog()

		lo_tools = QVBoxLayout()
		self.dlg_tools.setLayout(lo_tools)

		b_saveVersion = QPushButton("Save Version")
		b_saveComment = QPushButton("Save Comment")
		b_export = QPushButton("Export")
		b_projectBrowser = QPushButton("Project Browser")
		b_settings = QPushButton("Settings")

		b_saveVersion.clicked.connect(self.core.saveScene)
		b_saveComment.clicked.connect(self.core.saveWithComment)
		b_export.clicked.connect(self.exportImage)
		b_projectBrowser.clicked.connect(self.core.projectBrowser)
		b_settings.clicked.connect(self.core.prismSettings)

		lo_tools.addWidget(b_saveVersion)
		lo_tools.addWidget(b_saveComment)
		lo_tools.addWidget(b_export)
		lo_tools.addWidget(b_projectBrowser)
		lo_tools.addWidget(b_settings)

		self.core.parentWindow(self.dlg_tools)
		self.dlg_tools.setWindowTitle("Prism - Photoshop tools")

		self.dlg_tools.show()

		return True


	@err_decorator
	def exportImage(self):
		self.dlg_export = QDialog()
		self.core.parentWindow(self.dlg_export)
		self.dlg_export.setWindowTitle("Prism - Export image")

		lo_export = QVBoxLayout()
		self.dlg_export.setLayout(lo_export)


		curfile = self.core.getCurrentFileName()
		fname = os.path.basename(curfile).split("_")

		if len(fname) == 6:
			fType = "asset"
		else:
			fType = "shot"

		self.rb_task = QRadioButton("Export into current %s" % fType)
		self.w_task = QWidget()
		lo_prismExport = QVBoxLayout()
		lo_task = QHBoxLayout()
		self.w_comment = QWidget()
		lo_comment = QHBoxLayout()
		self.w_comment.setLayout(lo_comment)
		lo_comment.setContentsMargins(0,0,0,0)
		lo_version = QHBoxLayout()
		lo_extension = QHBoxLayout()
		lo_localOut = QHBoxLayout()
		l_task = QLabel("Task:")
		l_task.setMinimumWidth(110)
		self.le_task = QLineEdit()
		self.b_task = QPushButton(u"▼")
		self.b_task.setMinimumSize(35,0)
		self.b_task.setMaximumSize(35,500)
		l_comment = QLabel("Comment (optional):")
		l_comment.setMinimumWidth(110)
		self.le_comment = QLineEdit()
		self.chb_useNextVersion = QCheckBox("Use next version")
		self.chb_useNextVersion.setChecked(True)
		self.chb_useNextVersion.setMinimumWidth(110)
		self.cb_versions = QComboBox()
		self.cb_versions.setEnabled(False)
		l_ext = QLabel("Format:")
		l_ext.setMinimumWidth(110)
		self.cb_formats = QComboBox()
		self.cb_formats.addItems([".jpg", ".png", ".tif"])
		self.chb_localOutput = QCheckBox("Local output")
		lo_task.addWidget(l_task)
		lo_task.addWidget(self.le_task)
		lo_task.addWidget(self.b_task)
		lo_comment.addWidget(l_comment)
		lo_comment.addWidget(self.le_comment)
		lo_version.addWidget(self.chb_useNextVersion)
		lo_version.addWidget(self.cb_versions)
		lo_version.addStretch()
		lo_extension.addWidget(l_ext)
		lo_extension.addWidget(self.cb_formats)
		lo_extension.addStretch()
		lo_localOut.addWidget(self.chb_localOutput)
		lo_prismExport.addLayout(lo_task)
		lo_prismExport.addWidget(self.w_comment)
		lo_prismExport.addLayout(lo_version)
		lo_prismExport.addLayout(lo_extension)
		lo_prismExport.addLayout(lo_localOut)
		self.w_task.setLayout(lo_prismExport)
		lo_version.setContentsMargins(0,0,0,0)

		rb_custom = QRadioButton("Export to custom location")

		b_export = QPushButton("Export")

		lo_export.addWidget(self.rb_task)
		lo_export.addWidget(self.w_task)
		lo_export.addWidget(rb_custom)
		lo_export.addStretch()
		lo_export.addWidget(b_export)

		self.rb_task.setChecked(True)
		self.dlg_export.resize(400,300)

		self.rb_task.toggled.connect(self.exportToggle)
		self.b_task.clicked.connect(self.exportShowTasks)
		self.le_comment.textChanged.connect(self.validateComment)
		self.chb_useNextVersion.toggled.connect(self.exportVersionToggled)
		self.le_task.editingFinished.connect(self.exportGetVersions)
		b_export.clicked.connect(self.saveExport)

		if not self.core.useLocalFiles:
			self.chb_localOutput.setVisible(False)

		self.exportGetTasks()

		self.dlg_export.show()

		self.cb_versions.setMinimumWidth(300)
		self.cb_formats.setMinimumWidth(300)

		return True


	@err_decorator
	def exportToggle(self, checked):
		self.w_task.setEnabled(checked)


	@err_decorator
	def exportGetTasks(self):
		self.taskList = self.core.getTaskNames("2d")

		if len(self.taskList) == 0:
			self.b_task.setHidden(True)
		else:
			if "_ShotCam" in self.taskList:
				self.taskList.remove("_ShotCam")


	@err_decorator
	def exportShowTasks(self):
		tmenu = QMenu()

		for i in self.taskList:
			tAct = QAction(i, self.dlg_export)
			tAct.triggered.connect(lambda x=None, t=i: self.le_task.setText(t))
			tAct.triggered.connect(self.exportGetVersions)
			tmenu.addAction(tAct)

		self.core.appPlugin.setRCStyle(self, tmenu)

		tmenu.exec_(QCursor.pos())


	@err_decorator
	def exportGetVersions(self):
		existingVersions = []
		outData = self.exportGetOutputName()
		if outData is not None:
			versionDir = os.path.dirname(outData[1])

			if os.path.exists(versionDir):
				for i in reversed(sorted(os.listdir(versionDir))):
					if len(i) < 5 or not i.startswith("v"):
						continue

					if sys.version[0] == "2":
						if not unicode(i[1:5]).isnumeric():
							continue
					else:
						if not i[1:5].isnumeric():
							continue

					existingVersions.append(i)

		self.cb_versions.clear()
		self.cb_versions.addItems(existingVersions)


	@err_decorator
	def exportGetOutputName(self, useVersion="next"):
		if self.le_task.text() == "":
			return

		extension = self.cb_formats.currentText()

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
		pComment = self.le_comment.text()
		if useVersion != "next":
			hVersion = useVersion.split("_")[0]
			pComment = useVersion.split("_")[1]

		fnameData = os.path.basename(fileName).split("_")
		if len(fnameData) == 8:
			outputPath = os.path.abspath(os.path.join(fileName, os.pardir, os.pardir, os.pardir, os.pardir, "Rendering", "2dRender", self.le_task.text()))
			if hVersion == "":
				hVersion = self.core.getHighestTaskVersion(outputPath)

			outputFile = os.path.join( fnameData[0] + "_" + fnameData[1] + "_" + self.le_task.text() + "_" + hVersion + extension)
		elif len(fnameData) == 6:
			if os.path.join(sceneDir, "Assets", "Scenefiles") in fileName:
				outputPath = os.path.join(self.core.fixPath(basePath), sceneDir, "Assets", "Rendering", "2dRender", self.le_task.text())
			else:
				outputPath = os.path.abspath(os.path.join(fileName, os.pardir, os.pardir, os.pardir, "Rendering", "2dRender", self.le_task.text()))
			if hVersion == "":
				hVersion = self.core.getHighestTaskVersion(outputPath)

			
			outputFile = os.path.join( fnameData[0]  + "_" + self.le_task.text() + "_" + hVersion + extension)
		else:
			return

		outputPath = os.path.join(outputPath, hVersion)
		if pComment != "":
			outputPath += "_" + pComment

		outputName = os.path.join(outputPath, outputFile)

		return outputName, outputPath, hVersion


	@err_decorator
	def exportVersionToggled(self, checked):
		self.cb_versions.setEnabled(not checked)
		self.w_comment.setEnabled(checked)


	@err_decorator
	def validateComment(self, text):
		origComment = self.le_comment.text()
		validText = self.core.validateStr(origComment)
		startpos = self.le_comment.cursorPosition()
		
		if len(origComment) != len(validText):
			self.le_comment.setText(validText)
			self.le_comment.setCursorPosition(startpos-1)


	@err_decorator
	def saveExport(self):
		if self.rb_task.isChecked():
			taskName = self.le_task.text()
			if taskName is None or taskName == "":
				QMessageBox.warning(self.core.messageParent, "Warning", "Please choose a taskname")
				return

			if not self.core.fileInPipeline():
				QMessageBox.warning(self.core.messageParent,"Warning", "The current file is not inside the Pipeline.\nUse the Project Browser to create a file in the Pipeline.")
				return False

			oversion = "next"
			if not self.chb_useNextVersion.isChecked():
				oversion = self.cb_versions.currentText()

			if oversion is None or oversion == "":
				QMessageBox.warning(self.core.messageParent, "Warning", "Invalid version")
				return

			outputPath, outputDir, hVersion = self.exportGetOutputName(oversion)

			outLength = len(outputPath)
			if platform.system() == "Windows" and outLength > 255:
				return [self.state.text(0) + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, taskname or projectpath." % outLength]

			if not os.path.exists(outputDir):
				os.makedirs(outputDir)

			self.core.saveVersionInfo(location=os.path.dirname(outputPath), version=hVersion, origin=self.core.getCurrentFileName())
		else:
			startLocation = os.path.join(self.core.projectPath, self.core.getConfig('paths', "assets", configPath=self.core.prismIni), "Textures")
			outputPath = QFileDialog.getSaveFileName(self.dlg_export, "Enter output filename", startLocation, "JPEG (*.jpg *.jpeg);;PNG (*.png);;TIFF (*.tif *.tiff)")[0]

			if outputPath == "":
				return

		ext = os.path.splitext(outputPath)[1].lower()

		if self.win:
			if ext in [".jpg", ".jpeg"]:
				options = win32com.client.dynamic.Dispatch('Photoshop.JPEGSaveOptions')
			elif ext in [".png"]:
				options = win32com.client.dynamic.Dispatch('Photoshop.PNGSaveOptions')
			elif ext in [".tif", ".tiff"]:
				options = win32com.client.dynamic.Dispatch('Photoshop.TiffSaveOptions')

			self.psApp.Application.ActiveDocument.SaveAs(outputPath, options, True)
		else:
			if ext in [".jpg", ".jpeg"]:
				formatName = "JPEG"
			elif ext in [".png"]:
				formatName = "PNG"
			elif ext in [".tif", ".tiff"]:
				formatName = "TIFF"

			scpt = '''
				tell application "%s"
					save current document in file "%s" as %s with copying
				end tell
			''' % (self.psAppName, outputPath, formatName)
			self.executeAppleScript(scpt)

		self.dlg_export.accept()
		self.core.copyToClipboard(outputPath)

		try:
			self.core.pb.refreshRender()
		except:
			pass

		if os.path.exists(outputPath):
			QMessageBox.information(self.core.messageParent, "Export", "Successfully exported the image.\n(Path is in the clipboard)")
		else:
			QMessageBox.warning(self.core.messageParent, "Export", "Unknown error. Image file doesn't exist:\n\n%s" % outputPath)