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

import sys, os, datetime, traceback, time
from functools import wraps

if sys.version[0] == "3":
	from configparser import ConfigParser
	pVersion = 3
else:
	from ConfigParser import ConfigParser
	pVersion = 2

if psVersion == 1:
	import TaskSelection_ui
else:
	import TaskSelection_ui_ps2 as TaskSelection_ui


class TaskSelection(QDialog, TaskSelection_ui.Ui_dlg_TaskSelection):
	def __init__(self, core, importState):
		QDialog.__init__(self)
		self.setupUi(self)

		self.core = core
		self.importState = importState
		self.curEntity = None
		self.curTask = None

		self.adclick = False

		self.preferredUnit = self.importState.preferredUnit

		self.connectEvents()

		self.updateAssets()
		self.updateShots()

		if not self.navigateToFile(os.path.split(importState.e_file.text())[0]):
			self.navigateToFile(self.core.getCurrentFileName())

		self.core.callback(name="onSelectTaskOpen", types=["curApp", "custom"], args=[self])


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - TaskSelection %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def connectEvents(self):
		self.tbw_entity.currentChanged.connect(lambda x: self.entityClicked())
		self.tw_assets.itemExpanded.connect(self.aItemCollapsed)
		self.tw_assets.itemCollapsed.connect(self.aItemCollapsed)
		self.tw_assets.itemSelectionChanged.connect(lambda: self.entityClicked("Assets"))
		self.tw_assets.mousePrEvent = self.tw_assets.mousePressEvent
		self.tw_assets.mousePressEvent = lambda x: self.mouseClickEvent(x,"a")
		self.tw_assets.mouseClickEvent = self.tw_assets.mouseReleaseEvent
		self.tw_assets.mouseReleaseEvent = lambda x: self.mouseClickEvent(x,"a")
	#	self.tw_assets.mouseDClick = self.tw_assets.mouseDoubleClickEvent
	#	self.tw_assets.mouseDoubleClickEvent = lambda x: self.mousedb(x,"a", self.tw_assets)

		self.tw_shots.itemExpanded.connect(self.sItemCollapsed)
		self.tw_shots.itemCollapsed.connect(self.sItemCollapsed)
		self.tw_shots.itemSelectionChanged.connect(lambda: self.entityClicked("Shots"))
		self.tw_shots.mousePrEvent = self.tw_shots.mousePressEvent
		self.tw_shots.mousePressEvent = lambda x: self.mouseClickEvent(x,"s")
		self.tw_shots.mouseClickEvent = self.tw_shots.mouseReleaseEvent
		self.tw_shots.mouseReleaseEvent = lambda x: self.mouseClickEvent(x,"s")
	#	self.tw_shots.mouseDClick = self.tw_shots.mouseDoubleClickEvent
	#	self.tw_shots.mouseDoubleClickEvent = lambda x: self.mousedb(x,"s", self.tw_shots)

		self.lw_tasks.mousePrEvent = self.lw_tasks.mousePressEvent
		self.lw_tasks.mousePressEvent = lambda x: self.mouseClickEvent(x,"t")
		self.lw_tasks.mouseClickEvent = self.lw_tasks.mouseReleaseEvent
		self.lw_tasks.mouseReleaseEvent = lambda x: self.mouseClickEvent(x,"t")
		self.lw_tasks.itemSelectionChanged.connect(self.taskClicked)
		self.lw_tasks.doubleClicked.connect(lambda: self.loadVersion(None, currentVersion=True))
		self.tw_versions.doubleClicked.connect(self.loadVersion)
		self.b_custom.clicked.connect(self.openCustom)

		self.tw_assets.customContextMenuRequested.connect(lambda pos: self.rclicked(pos, "assets"))
		self.tw_shots.customContextMenuRequested.connect(lambda pos: self.rclicked(pos, "shots"))
		self.lw_tasks.customContextMenuRequested.connect(lambda pos: self.rclicked(pos, "tasks"))
		self.tw_versions.customContextMenuRequested.connect(lambda pos: self.rclicked(pos, "versions"))



	@err_decorator
	def mouseClickEvent(self, event, uielement):
		if QEvent != None:
			if event.type() == QEvent.MouseButtonRelease:
				if event.button() == Qt.LeftButton:
					if uielement == "a":
						index = self.tw_assets.indexAt(event.pos())
						if index.data() == None:
							self.tw_assets.setCurrentIndex(self.tw_assets.model().createIndex(-1,0))
						self.tw_assets.mouseClickEvent(event)
					elif uielement == "s":
						index = self.tw_shots.indexAt(event.pos())
						if index.data() == None:
							self.tw_shots.setCurrentIndex(self.tw_shots.model().createIndex(-1,0))
						self.tw_shots.mouseClickEvent(event)
					elif uielement == "t":
						index = self.lw_tasks.indexAt(event.pos())
						if index.data() == None:
							self.lw_tasks.setCurrentIndex(self.lw_tasks.model().createIndex(-1,0))
						self.lw_tasks.mouseClickEvent(event)
			elif event.type() == QEvent.MouseButtonPress:
				if uielement == "a":
					self.adclick = True
					self.tw_assets.mousePrEvent(event)
				elif uielement == "s":
					self.sdclick = True
					self.tw_shots.mousePrEvent(event)
				elif uielement == "t":
					self.lw_tasks.mousePrEvent(event)


	@err_decorator
	def mousedb(self, event, tab, uielement):
		if tab == "a" and not self.adclick:
			pos = self.tw_assets.mapFromGlobal(QCursor.pos())
			item = self.tw_assets.itemAt(pos.x(), pos.y())
			if item is not None:
				item.setExpanded(not item.isExpanded())

		elif tab == "s":
			pos = self.tw_shots.mapFromGlobal(QCursor.pos())
			item = self.tw_shots.itemAt(pos.x(), pos.y())
			if item is not None:
				item.setExpanded(not item.isExpanded())

	#		mIndex = uielement.indexAt(event.pos())
	#		if mIndex.data() is not None and mIndex.parent().column() == -1:
	#			uielement.setExpanded(mIndex, not uielement.isExpanded(mIndex))
	#			uielement.mouseDClick(event)


	@err_decorator
	def openCustom(self):
		startPath = self.getCurSelection()
		customFile = QFileDialog.getOpenFileName(self, "Select File to import", startPath, "All files (*.*)")[0]
		customFile = self.core.fixPath(customFile)

		splitName = getattr(self.core.appPlugin, "splitExtension", lambda x, y: os.path.splitext(y))(self, customFile)

		fileName = customFile
		impPath = getattr(self.core.appPlugin, "fixImportPath", lambda x, y:y)(self, splitName[0])
		fileName = impPath + splitName[1]

		if fileName != "":
			self.importState.importPath = [os.path.basename(os.path.dirname(fileName)).replace(" ", "_"), fileName]
			self.close()
		

	@err_decorator
	def loadVersion(self, index, currentVersion=False):
		if currentVersion:
			self.tw_versions.sortByColumn(0, Qt.DescendingOrder)
			pathC = self.tw_versions.model().columnCount()-1
			versionPath = self.tw_versions.model().index(0, pathC).data()
			if versionPath is None:
				return
		else:
			pathC = index.model().columnCount()-1
			versionPath = index.model().index(index.row(), pathC).data()
		incompatible = []
		for i in self.core.unloadedAppPlugins.values():
			incompatible += getattr(i, "appSpecificFormats", [])
		if os.path.splitext(versionPath)[1] in incompatible:
			QMessageBox.warning(self.core.messageParent,"Warning", "This filetype is incompatible. Can't import the selected file.")
		else:		
			self.importState.importPath = [self.lw_tasks.currentItem().text(), versionPath]
			self.close()


	@err_decorator
	def rclicked(self, pos, listType):
		showInfo = False
		if listType == "assets":
			viewUi = self.tw_assets
			item = self.tw_assets.itemAt(pos)
			if item is None:
				self.tw_assets.setCurrentIndex(self.tw_assets.model().createIndex(-1,0))
				self.updateTasks()
				path = os.path.join(self.core.projectPath, self.core.getConfig('paths', "scenes", configPath=self.core.prismIni), "Assets")
			else:
				path = item.text(1)

		elif listType == "shots":
			viewUi = self.tw_shots
			item = self.tw_shots.itemAt(pos)
			if item is None:
				self.tw_shots.setCurrentIndex(self.tw_shots.model().createIndex(-1,0))
				self.updateTasks()
				path = os.path.join(self.core.projectPath, self.core.getConfig('paths', "scenes", configPath=self.core.prismIni), "Shots")
			else:
				path = item.text(1)

		elif listType == "tasks":
			viewUi = self.lw_tasks
			item = self.lw_tasks.itemAt(pos)
			if self.tbw_entity.tabText(self.tbw_entity.currentIndex()) == "Assets":
				entityItem = self.tw_assets.currentItem()
			else:
				entityItem = self.tw_shots.currentItem()

			if entityItem is None:
				return

			if item is None:
				self.lw_tasks.setCurrentRow(-1)
				path = os.path.join(entityItem.text(1), "Export")
				if not os.path.exists(path):
					return
			else:
				path = os.path.join(entityItem.text(1), "Export", self.lw_tasks.currentItem().text().replace("ShotCam", "_ShotCam"))

		elif listType == "versions":
			viewUi = self.tw_versions
			row = self.tw_versions.rowAt(pos.y())

			if row == -1:
				if self.tbw_entity.tabText(self.tbw_entity.currentIndex()) == "Assets":
					entityItem = self.tw_assets.currentItem()
				else:
					entityItem = self.tw_shots.currentItem()

				self.tw_versions.setCurrentIndex(self.tw_versions.model().createIndex(-1,0))
				if self.lw_tasks.currentItem() is None:
					return

				path = os.path.join(entityItem.text(1), "Export", self.lw_tasks.currentItem().text().replace("ShotCam", "_ShotCam"))
			else:
				pathC = self.tw_versions.model().columnCount()-1
				path = os.path.dirname(self.tw_versions.model().index(row, pathC).data())
				showInfo = True

		if self.core.useLocalFiles and not os.path.exists(path) and os.path.exists(path.replace(self.core.projectPath, self.core.localProjectPath)):
			path = path.replace(self.core.projectPath, self.core.localProjectPath)

		rcmenu = QMenu()
		openex = QAction("Open in Explorer", self)
		openex.triggered.connect(lambda: self.core.openFolder(path))
		rcmenu.addAction(openex)

		if showInfo:
			infoAct = QAction("Show version info", self)
			infoAct.triggered.connect(lambda: self.showVersionInfo(os.path.dirname(path)))
			rcmenu.addAction(infoAct)

			infoPath = os.path.join(os.path.dirname(path), "versioninfo.ini")

			depAct = QAction("Show dependencies", self)
			depAct.triggered.connect(lambda: self.core.dependencyViewer(infoPath, modal=True))
			rcmenu.addAction(depAct)

		self.core.appPlugin.setRCStyle(self, rcmenu)

		rcmenu.exec_((viewUi.viewport()).mapToGlobal(pos))


	@err_decorator
	def showVersionInfo(self, path):
		vInfo = "No information is saved with this version."

		infoPath = os.path.join(path, "versioninfo.ini")

		if os.path.exists(infoPath):
			vConfig = ConfigParser()
			vConfig.read(infoPath)

			vInfo = ""
			for i in vConfig.options("information"):
				i = i[0].upper() + i[1:]
				if i == "Version":
					vInfo += "%s:\t\t\t%s\n" % (i, vConfig.get("information", i))
				else:
					vInfo += "%s:\t\t%s\n" % (i, vConfig.get("information", i))

		QMessageBox.information(self.core.messageParent, "Versioninfo", vInfo)


	@err_decorator
	def entityClicked(self, entityType=None):
		if entityType is None:
			if self.tbw_entity.tabText(self.tbw_entity.currentIndex()) == "Assets":
				entityType = "Assets"
			else:
				entityType = "Shots"

		if entityType == "Assets":
			uielement = self.tw_assets
		else:
			uielement = self.tw_shots

		sItems = uielement.selectedItems()

		if len(sItems) == 1:
			self.curEntity = [entityType, sItems[0].text(0)]
		else:
			self.curEntity = None
		
		self.updateTasks()


	@err_decorator
	def taskClicked(self):
		sItems = self.lw_tasks.selectedItems()
		if len(sItems) == 1 and sItems[0].text() != self.curTask:
			self.curTask = sItems[0].text()
		else:
			self.curTask = ""
		
		self.updateVersions()


	@err_decorator
	def updateAssets(self, load=False):
		self.tw_assets.clear()

		aBasePath = os.path.join(self.core.projectPath, self.core.getConfig('paths', "scenes", configPath=self.core.prismIni), "Assets")

		omittedAssets = []

		omitPath = os.path.join(os.path.dirname(self.core.prismIni), "Configs", "omits.ini")
		if os.path.exists(omitPath):
			oconfig = ConfigParser()
			oconfig.read(omitPath)

			if oconfig.has_section("Asset"):
				omittedAssets = [x[1] for x in oconfig.items("Asset")]

		if self.core.useLocalFiles:
			lBasePath = aBasePath.replace(self.core.projectPath, self.core.localProjectPath)

		assetPaths = self.core.getAssetPaths()

		for i in assetPaths:
			if i != aBasePath and i.replace(aBasePath + os.sep, "") in omittedAssets:
				continue

			taskPath = os.path.join(i, "Export")
			tasks = []
			for k in os.walk(taskPath):
				tasks += k[1]
				break

			if self.core.useLocalFiles:
				ltaskPath = taskPath.replace(self.core.projectPath, self.core.localProjectPath)
				for k in os.walk(ltaskPath):
					tasks += k[1]
					break

			if len(tasks) == 0:
				continue

			relPath = i

			if aBasePath in relPath:
				relPath = relPath.replace(aBasePath, "")
			elif self.core.useLocalFiles and lBasePath in relPath:
				relPath = relPath.replace(lBasePath, "")

			pathData = relPath.split(os.sep)[1:]

			lastItem = None
			for idx, val in enumerate(pathData):
				if lastItem is None:
					for k in range(self.tw_assets.topLevelItemCount()):
						curItem = self.tw_assets.topLevelItem(k)
						if curItem.text(0) == val:
							lastItem = curItem

					if lastItem is None:
						curPath = i.replace(relPath, "")
						for k in range(idx+1):
							curPath = os.path.join(curPath, pathData[k])
						lastItem = QTreeWidgetItem([val, curPath])
						self.tw_assets.addTopLevelItem(lastItem)
				else:
					newItem = None
					for k in range(lastItem.childCount()):
						curItem = lastItem.child(k)
						if curItem.text(0) == val:
							newItem = curItem

					if newItem is None:
						curPath = i.replace(relPath, "")
						for k in range(idx+1):
							curPath = os.path.join(curPath, pathData[k])
						newItem = QTreeWidgetItem([val, curPath])
						lastItem.addChild(newItem)

					lastItem = newItem

				if idx == (len(pathData)-1):
					lastItem.setText(2, "Asset")
					iFont = lastItem.font(0)
					iFont.setBold(True)
					lastItem.setFont(0, iFont)
				else:
					lastItem.setText(2, "Folder")

		if self.tw_assets.topLevelItemCount() > 0:
			self.tw_assets.setCurrentItem(self.tw_assets.topLevelItem(0))

		self.updateTasks()


	@err_decorator
	def aItemCollapsed(self, item):
		self.adclick = False


	@err_decorator
	def sItemCollapsed(self, item):
		self.sdclick = False


	@err_decorator
	def updateShots(self):
		self.tw_shots.clear()

		relsPath = os.path.join(self.core.getConfig('paths', "scenes", configPath=self.core.prismIni), "Shots")
		shotPath = os.path.join(self.core.projectPath, relsPath)

		omittedShots = []

		omitPath = os.path.join(os.path.dirname(self.core.prismIni), "Configs", "omits.ini")
		if os.path.exists(omitPath):
			oconfig = ConfigParser()
			oconfig.read(omitPath)

			if oconfig.has_section("Shot"):
				omittedShots = [x[1] for x in oconfig.items("Shot")]

		dirs = []
		if os.path.exists(shotPath):
			for i in os.walk(shotPath):
				dirs += [os.path.join(shotPath, k) for k in i[1]]
				break

		if self.core.useLocalFiles:
			lshotPath = os.path.join(self.core.localProjectPath, relsPath)
			if os.path.exists(lshotPath):
				for i in os.walk(lshotPath):
					for k in i[1]:
						ldir = os.path.join(i[0], k)
						if ldir.replace(self.core.localProjectPath, self.core.projectPath) not in dirs:
							dirs.append(ldir)
					break

		sequences = []
		shots = []
		for path in dirs:
			val = os.path.basename(path)
			if val.startswith("_") or val in omittedShots:
				continue

			taskPath = os.path.join(path, "Export")

			if self.core.useLocalFiles:
				taskPath = taskPath.replace(self.core.localProjectPath, self.core.projectPath)
				ltaskPath = taskPath.replace(self.core.projectPath, self.core.localProjectPath)

			tasks = []
			for k in os.walk(taskPath):
				tasks = k[1]
				break

			if self.core.useLocalFiles:
				for i in os.walk(ltaskPath):
					tasks += i[1]
					break

			if len(tasks) == 0:
				continue

			if "-" in val:
				sname = val.split("-",1)
				seqName = sname[0]
				shotName = sname[1]
			else:
				seqName = "no sequence"
				shotName = val

			shots.append([seqName, shotName, path])
			if seqName not in sequences:
				sequences.append(seqName)

		if "no sequence" in sequences:
			sequences.insert(len(sequences), sequences.pop(sequences.index("no sequence")))

		for seqName in sequences:
			seqItem = QTreeWidgetItem([seqName])
			self.tw_shots.addTopLevelItem(seqItem)

		for i in shots:
			for k in range(self.tw_shots.topLevelItemCount()):
				tlItem = self.tw_shots.topLevelItem(k)
				if tlItem.text(0) == i[0]:
					seqItem = tlItem

			sItem = QTreeWidgetItem([i[1], i[2]])
			seqItem.addChild(sItem)

		if self.tw_shots.topLevelItemCount() > 0:
			self.tw_shots.setCurrentItem(self.tw_shots.topLevelItem(0))

		self.updateTasks()


	@err_decorator
	def updateTasks(self, item=None):
		self.lw_tasks.clear()

		if self.tbw_entity.tabText(self.tbw_entity.currentIndex()) == "Assets":
			entityItem = self.tw_assets.currentItem()
		else:
			entityItem = self.tw_shots.currentItem()

		if entityItem is not None:
			taskPath = os.path.join(entityItem.text(1), "Export")
			if self.core.useLocalFiles:
				taskPath = taskPath.replace(self.core.localProjectPath, self.core.projectPath)
				ltaskPath = taskPath.replace(self.core.projectPath, self.core.localProjectPath)

			tasks = []
			for i in os.walk(taskPath):
				tasks += i[1]
				break

			if self.core.useLocalFiles:
				for i in os.walk(ltaskPath):
					tasks += i[1]
					break

			tasks = sorted(tasks, key=lambda s: s.lower())

			uniqueTasks = []
			for k in tasks:
				if k not in uniqueTasks:
					uniqueTasks.append(k)
					self.lw_tasks.addItem(k.replace("_ShotCam", "ShotCam"))

		if self.lw_tasks.count() > 0:
			self.lw_tasks.setCurrentRow(0)

		self.updateVersions()


	@err_decorator
	def updateVersions(self):
		model = QStandardItemModel()

		versionLabels = ["Version", "Comment", "Type", "Units", "User", "Date", "Path"]

		if self.core.useLocalFiles:
			versionLabels.insert(4, "Location")

		model.setHorizontalHeaderLabels(versionLabels)

		twSorting = [self.tw_versions.horizontalHeader().sortIndicatorSection(), self.tw_versions.horizontalHeader().sortIndicatorOrder()]

		# currentItem() leads to crashes in blender

		if self.curEntity is not None and self.curTask is not None:
			if self.tbw_entity.tabText(self.tbw_entity.currentIndex()) == "Assets":
				entityItem = self.tw_assets.currentItem()
			else:
				entityItem = self.tw_shots.currentItem()

			versionPath = os.path.join(entityItem.text(1), "Export", self.curTask.replace("ShotCam", "_ShotCam"))
			if self.core.useLocalFiles:
				versionPath = versionPath.replace(self.core.localProjectPath, self.core.projectPath)
				lversionPath = versionPath.replace(self.core.projectPath, self.core.localProjectPath)

			versions = []
			for i in os.walk(versionPath):
				for k in i[1]:
					versions += [[k, versionPath]]
				break

			if self.core.useLocalFiles:
				for i in os.walk(lversionPath):
					for k in i[1]:
						versions += [[k, lversionPath]]
					break

			for k in versions:
				nameData = k[0].split(self.core.filenameSeperator)
				
				if not (len(nameData) == 3 and k[0][0] == "v" and len(nameData[0]) == 5):
					continue

				fileName = [None, None, None]
				for n, unit in enumerate(["centimeter", "meter", ""]):
					for m in os.walk(os.path.join(k[1], k[0], unit)):
						if len(m[2]) > 0:
							for i in m[2]:
								if os.path.splitext(i)[1] not in [".txt", ".ini"]:
									fileName[n] = os.path.join(k[1], k[0], unit, i)
									if getattr(self.core.appPlugin, "shotcamFormat", ".abc") == ".fbx" and self.curTask == "ShotCam" and fileName[n].endswith(".abc") and os.path.exists(fileName[n][:-3] + "fbx"):
										fileName[n] = fileName[n][:-3] + "fbx"
									if fileName[n].endswith(".mtl") and os.path.exists(fileName[n][:-3] + "obj"):
										fileName[n] = fileName[n][:-3] + "obj"
									break
						break

				if fileName[0] is None and fileName[1] is None and fileName[2] is None:
					continue

				if fileName[2] is not None:
					uv = 2
				else:
					if self.preferredUnit == "centimeter":
						if fileName[0] is not None:
							uv = 0
						else:
							uv = 1
					elif self.preferredUnit == "meter":
						if fileName[1] is not None:
							uv = 1
						else:
							uv = 0

				depPath, depExt = getattr(self.core.appPlugin, "splitExtension", lambda x, y: os.path.splitext(y))(self, fileName[uv])

				row = []

				item = QStandardItem(nameData[0])
				item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
				row.append(item)

				if nameData[1] == "nocomment":
					comment = ""
				else:
					comment = nameData[1]

				item = QStandardItem(comment)
				item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
				row.append(item)

				item = QStandardItem(depExt)
				item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
				row.append(item)

				if fileName[0] is not None and fileName[1] is not None:
					uStr = "cm, m"
				elif fileName[0] is not None:
					uStr = "cm"
				elif fileName[1] is not None:
					uStr = "m"
				else:
					uStr = ""

				item = QStandardItem(uStr)
				item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
				row.append(item)

				if self.core.useLocalFiles:
					if self.core.localProjectPath in depPath:
						location = "local"
					else:
						location = "global"

					item = QStandardItem(location)
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)

				item = QStandardItem(nameData[2])
				item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
				row.append(item)

				cdate = datetime.datetime.fromtimestamp(os.path.getmtime(fileName[uv]))
				cdate = cdate.replace(microsecond = 0)
				cdate = cdate.strftime("%d.%m.%y,  %X")
				item = QStandardItem()
				item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
				item.setData(QDateTime.fromString( cdate, "dd.MM.yy,  hh:mm:ss").addYears(100), 0)
				item.setToolTip(cdate)
				row.append(item)

				impPath = getattr(self.core.appPlugin, "fixImportPath", lambda x, y:y)(self, depPath)
				row.append(QStandardItem(impPath + depExt))

				model.appendRow(row)

		self.tw_versions.setModel(model)
		self.tw_versions.setColumnHidden(len(versionLabels)-1, True)
		if psVersion == 1:
			self.tw_versions.horizontalHeader().setResizeMode(1, QHeaderView.Stretch)
		else:
			self.tw_versions.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

		self.tw_versions.resizeColumnsToContents()
		self.tw_versions.setColumnWidth(0,90*self.core.uiScaleFactor)
		self.tw_versions.setColumnWidth(2,70*self.core.uiScaleFactor)
		self.tw_versions.setColumnWidth(3,50*self.core.uiScaleFactor)
		self.tw_versions.setColumnWidth(len(versionLabels)-3,70*self.core.uiScaleFactor)
		self.tw_versions.setColumnWidth(len(versionLabels)-2,150*self.core.uiScaleFactor)
		self.tw_versions.sortByColumn(twSorting[0], twSorting[1])

		if self.tw_versions.model().rowCount() > 0:
			self.tw_versions.selectRow(0)


	@err_decorator
	def getCurSelection(self):
		curPath = os.path.join(self.core.projectPath, self.core.getConfig('paths', "scenes", configPath=self.core.prismIni))

		if self.tbw_entity.tabText(self.tbw_entity.currentIndex()) == "Assets":
			entityItem = self.tw_assets.currentItem()
		else:
			entityItem = self.tw_shots.currentItem()

		if entityItem is None:
			return curPath

		curPath = os.path.join(entityItem.text(1), "Export")
	
		if self.lw_tasks.currentItem() is None:
			return curPath

		curPath = os.path.join(curPath, self.lw_tasks.currentItem().text().replace("ShotCam", "_ShotCam"))

		if self.tw_versions.selectionModel().currentIndex().row() == -1:
			return curPath

		pathC = self.tw_versions.model().columnCount()-1
		row = self.tw_versions.selectionModel().currentIndex().row()
		return os.path.dirname(self.tw_versions.model().index(row, pathC).data())


	@err_decorator
	def navigateToFile(self, fileName):
		sceneDir = self.core.getConfig('paths', "scenes", configPath=self.core.prismIni)
		if os.path.exists(fileName) and (os.path.join(self.core.projectPath, sceneDir) in fileName or ( self.core.useLocalFiles and os.path.join(self.core.localProjectPath, sceneDir) in fileName)):
			relFileName = fileName.replace(os.path.join(self.core.projectPath, sceneDir), "")
			if self.core.useLocalFiles:
				relFileName = relFileName.replace(os.path.join(self.core.localProjectPath, sceneDir), "")
			fileNameData = relFileName.split(os.sep)

			if (os.path.join(self.core.projectPath, sceneDir, "Assets") in fileName or ( self.core.useLocalFiles and os.path.join(self.core.localProjectPath, sceneDir, "Assets") in fileName)):
				entityType = "Asset"
			else:
				entityType = "Shot"

			taskName = self.importState.taskName
			versionName = self.importState.l_curVersion.text()

			if versionName != "-":
				versionName = versionName[:5]

			foundEntity = False

			if entityType == "Asset":
				uielement = self.tw_assets
				entityName = fileNameData[-4]
				self.tbw_entity.setCurrentIndex(0)

				itemPath = fileName.replace(self.core.projectPath, "")
				if self.core.useLocalFiles:
					itemPath = itemPath.replace(self.core.localProjectPath, "")
				if not itemPath.startswith(os.sep):
					itemPath = os.sep + itemPath
				itemPath = itemPath.replace(os.sep + os.path.join( sceneDir, "Assets", "Scenefiles", ""), "")
				itemPath = itemPath.replace(os.sep + os.path.join( sceneDir, "Assets", ""), "")
				hierarchy = itemPath.split(os.sep)
				hItem = self.tw_assets.findItems(hierarchy[0], Qt.MatchExactly, 0)
				if len(hItem) == 0:
					return False

				hItem = hItem[-1]
				hItem.setExpanded(True)

				endIdx = None
				if len(hierarchy) > 1:
					for idx, i in enumerate((hierarchy[1:])):
						for k in range(hItem.childCount()-1,-1,-1):
							if hItem.child(k).text(0) == i:
								hItem = hItem.child(k)
								if len(hierarchy) > (idx+2):
									hItem.setExpanded(True)
								break
						else:
							endIdx = idx+1
							break

				self.tw_assets.setCurrentItem(hItem)
				foundEntity = True

			else:
				uielement = self.tw_shots
				entityName = fileNameData[2]
				self.tbw_entity.setCurrentIndex(1)
				if "-" in entityName:
					sname = entityName.split("-",1)
					seqName = sname[0]
					shotName = sname[1]
				else:
					seqName = "no sequence"
					shotName = entityName

				for i in range(self.tw_shots.topLevelItemCount()):
					sItem = self.tw_shots.topLevelItem(i)
					if sItem.text(0) == seqName:
						sItem.setExpanded(True)
						for k in range(sItem.childCount()):
							shotItem = sItem.child(k)
							if shotItem.text(0) == shotName:
								self.tw_shots.setCurrentItem(shotItem)
								foundEntity = True
								break

						if foundEntity:
							break
				else:
					if entityType == "Shot" and self.tw_shots.topLevelItemCount() > 0:
						seqItem = self.tw_shots.topLevelItem(0)
						seqItem.setExpanded(True)
						self.tw_shots.setCurrentItem(seqItem.child(0))
						foundEntity = True

			if foundEntity:
				self.updateTasks()

				if self.lw_tasks.findItems(taskName, Qt.MatchExactly) != []:
					self.lw_tasks.setCurrentItem(self.lw_tasks.findItems(taskName, Qt.MatchExactly)[0])

					self.updateVersions()

					for i in range(self.tw_versions.model().rowCount()):
						if self.tw_versions.model().index(i,0).data() == versionName:
							self.tw_versions.selectRow(i)
							return True

		return False