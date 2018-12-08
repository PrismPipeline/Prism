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



import sys, os, datetime, shutil, ast, time, traceback, random, platform

prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

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
		sys.path.append(os.path.join(prismRoot, "PythonLibs", "Python27"))
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

if sys.version[0] == "3":
	from configparser import ConfigParser
	pVersion = 3
else:
	from ConfigParser import ConfigParser
	pVersion = 2

if platform.system() == "Windows":
	if pVersion == 3:
		import winreg as _winreg
	elif pVersion == 2:
		import _winreg
		
elif platform.system() in ["Linux", "Darwin"]:
	if pVersion == 3:
		from io import BytesIO as StringIO
	elif pVersion == 2:
		pyLibs = os.path.join(prismRoot, "PythonLibs", "Python27")
		if pyLibs not in sys.path:
			sys.path.append(pyLibs)
		try:
			from PIL import Image
			from cStringIO import StringIO
		except:
			pass

import subprocess
from functools import wraps
sys.path.append(os.path.join(prismRoot, "Scripts"))
sys.path.append(os.path.join(os.path.dirname(__file__), "UserInterfaces"))

for i in ["ProjectBrowser_ui", "ProjectBrowser_ui_ps2", "CreateItem", "CreateItem_ui", "CreateItem_ui_ps2"]:
	try:
		del sys.modules[i]
	except:
		pass

if psVersion == 1:
	import ProjectBrowser_ui
else:
	import ProjectBrowser_ui_ps2 as ProjectBrowser_ui

try:
	import CreateItem
except:
	modPath = imp.find_module("CreateItem")[1]
	if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
		os.remove(modPath)
	import CreateItem


class ProjectBrowser(QMainWindow, ProjectBrowser_ui.Ui_mw_ProjectBrowser):
	def __init__(self, core):
		QMainWindow.__init__(self)
		self.setupUi(self)
		self.core = core
		self.version = "v1.1.1.0"

		#self.core.reloadPlugins()

		self.core.parentWindow(self)

		self.setWindowTitle("Prism - Project Browser - " + self.core.projectName)
		self.scenes = self.core.getConfig('paths', "scenes", configPath=self.core.prismIni)
		self.aBasePath = os.path.join(self.core.projectPath, self.scenes, "Assets")
		self.sBasePath = os.path.join(self.core.projectPath, self.scenes, "Shots")

		self.aExpanded = []
		self.sExpanded = []
		self.fhierarchy =["Files"]
		self.fbottom = False
		self.fclickedon = ""

		self.copiedFile = None
		self.copiedsFile = None
		self.copiedfFile = None

		self.dclick = False
		self.adclick = False
		self.sdclick = False

		self.shotPrvXres = 250
		self.shotPrvYres = 141

		self.cursShots = None
		self.cursStep = None
		self.cursCat = None

		self.tw_aHierarchy.setHeaderLabels(["Assets"])

		self.fhbuttons = [self.b_fH01, self.b_fH02, self.b_fH03, self.b_fH04, self.b_fH05, self.b_fH06, self.b_fH07, self.b_fH08, self.b_fH09, self.b_fH10]

		self.curRTask = ""
		self.curRVersion = ""
		self.curRLayer = ""

		self.b_refresh.setEnabled(True)

		self.saveRender1 = []
		self.saveRender2 = []
		self.saveRender3 = []
		self.w_saveButtons.setVisible(False)

		self.b_compareRV.setEnabled(False)
		self.b_combineVersions.setEnabled(False)
		self.b_clearRV.setEnabled(False)

		self.chb_autoUpdate.setToolTip("Automatically refresh tasks, versions and renderings, when the current asset/shot changes.")
		self.b_refresh.setToolTip("Refresh tasks, versions and renderings.")
		self.b_compareRV.setToolTip("Click to compare media files in layout view in RV.\nRight-Click for additional compare modes.")
		self.b_combineVersions.setToolTip("Click to combine media files to one video file.\nRight-Click for additional combine modes.")

		self.renderResX = 300
		self.renderResY = 169

		self.renderRefreshEnabled = True
		self.openRV = False
		self.prevCurImg = 0
		self.compareStates = []

		self.oiioLoaded = False
		self.wandLoaded = False

		self.oldPalette = self.b_saveRender1.palette()
		self.savedPalette = QPalette()
		self.savedPalette.setColor(QPalette.Button, QColor(200, 100, 0))
		self.savedPalette.setColor(QPalette.ButtonText, QColor(255, 255, 255))

		self.publicColor = QColor(150,200,220)
		self.closeParm = "closeafterload"
		getattr(self.core.appPlugin, "projectBrower_loadLibs", lambda x: self.loadLibs())(self)
		self.emptypmap = self.createPMap(self.renderResX, self.renderResY)
		self.emptypmapPrv = self.createPMap(self.shotPrvXres, self.shotPrvYres)
		self.refreshFCat()
		self.setRecent()
		self.loadLayout()
		self.getRVpath()
		self.getDJVpath()
		self.getVLCpath()
		self.connectEvents()
		self.core.callback(name="onProjectBrowserStartup", types=["curApp", "custom"], args=[self])
		self.refreshAHierarchy(load=True)
		self.refreshShots()
		self.navigateToCurrent()
		self.updateTasks()

		self.l_preview.setAcceptDrops(True)


	#	self.tw_sFiles.setStyleSheet("QTableView,QListView,QHeaderView {color: rgb(199,199,199);background-color: rgb(71,71,71);selection-color: rgb(0,0,0);selection-background-color: rgb(242,138,0);}")


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			exc_info = sys.exc_info()
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - ProjectBrowser %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def connectEvents(self):
		self.tw_aHierarchy.mousePrEvent = self.tw_aHierarchy.mousePressEvent
		self.tw_aHierarchy.mousePressEvent = lambda x: self.mouseClickEvent(x,"ah")
		self.tw_aHierarchy.mouseClickEvent = self.tw_aHierarchy.mouseReleaseEvent
		self.tw_aHierarchy.mouseReleaseEvent = lambda x: self.mouseClickEvent(x,"ah")
		self.tw_aHierarchy.mouseDClick = self.tw_aHierarchy.mouseDoubleClickEvent
		self.tw_aHierarchy.mouseDoubleClickEvent = lambda x: self.mousedb(x,"ah", self.tw_aHierarchy)
		self.lw_aPipeline.mouseClickEvent = self.lw_aPipeline.mouseReleaseEvent
		self.lw_aPipeline.mouseReleaseEvent = lambda x: self.mouseClickEvent(x,"ap")
		self.lw_aPipeline.mouseDClick = self.lw_aPipeline.mouseDoubleClickEvent
		self.lw_aPipeline.mouseDoubleClickEvent = lambda x: self.mousedb(x,"ap", self.lw_aPipeline)
		self.tw_aFiles.mouseClickEvent = self.tw_aFiles.mouseReleaseEvent
		self.tw_aFiles.mouseReleaseEvent = lambda x: self.mouseClickEvent(x,"af")

		self.tw_sShot.mousePrEvent = self.tw_sShot.mousePressEvent
		self.tw_sShot.mousePressEvent = lambda x: self.mouseClickEvent(x,"ss")
		self.tw_sShot.mouseClickEvent = self.tw_sShot.mouseReleaseEvent
		self.tw_sShot.mouseReleaseEvent = lambda x: self.mouseClickEvent(x,"ss")
		self.tw_sShot.mouseDClick = self.tw_sShot.mouseDoubleClickEvent
		self.tw_sShot.mouseDoubleClickEvent = lambda x: self.mousedb(x,"ss", self.tw_sShot)
		self.lw_sPipeline.mouseClickEvent = self.lw_sPipeline.mouseReleaseEvent
		self.lw_sPipeline.mouseReleaseEvent = lambda x: self.mouseClickEvent(x,"sp")
		self.lw_sPipeline.mouseDClick = self.lw_sPipeline.mouseDoubleClickEvent
		self.lw_sPipeline.mouseDoubleClickEvent = lambda x: self.mousedb(x,"sp", self.lw_sPipeline)
		self.lw_sCategory.mouseClickEvent = self.lw_sCategory.mouseReleaseEvent
		self.lw_sCategory.mouseReleaseEvent = lambda x: self.mouseClickEvent(x,"sc")
		self.lw_sCategory.mouseDClick = self.lw_sCategory.mouseDoubleClickEvent
		self.lw_sCategory.mouseDoubleClickEvent = lambda x: self.mousedb(x,"sc", self.lw_sCategory)
		self.tw_sFiles.mouseClickEvent = self.tw_sFiles.mouseReleaseEvent
		self.tw_sFiles.mouseReleaseEvent = lambda x: self.mouseClickEvent(x,"sf")

		self.lw_fCategory.mousePrEvent = self.lw_fCategory.mousePressEvent
		self.lw_fCategory.mousePressEvent = lambda x: self.mouseClickEvent(x,"f")
		self.lw_fCategory.mouseClickEvent = self.lw_fCategory.mouseReleaseEvent
		self.lw_fCategory.mouseReleaseEvent = lambda x: self.mouseClickEvent(x,"fc")
		self.lw_fCategory.mouseDClick = self.lw_fCategory.mouseDoubleClickEvent
		self.lw_fCategory.mouseDoubleClickEvent = lambda x: self.mousedb(x,"f", self.lw_fCategory)
		self.tw_fFiles.mouseClickEvent = self.tw_fFiles.mouseReleaseEvent
		self.tw_fFiles.mouseReleaseEvent = lambda x: self.mouseClickEvent(x,"ff")
		self.tw_recent.mouseClickEvent = self.tw_recent.mouseReleaseEvent
		self.tw_recent.mouseReleaseEvent = lambda x: self.mouseClickEvent(x,"r")

		self.tw_aHierarchy.currentItemChanged.connect(lambda x, y: self.Assetclicked(x))
		self.tw_aHierarchy.itemExpanded.connect(self.refreshAItem)
		self.tw_aHierarchy.itemCollapsed.connect(self.hItemCollapsed)
		self.tw_aHierarchy.customContextMenuRequested.connect(lambda x: self.rclCat("ah",x))
		self.lw_aPipeline.currentItemChanged.connect(self.refreshAFile)
		self.lw_aPipeline.customContextMenuRequested.connect(lambda x: self.rclCat("ap",x))
		self.tw_aFiles.customContextMenuRequested.connect(lambda x: self.rclFile("a",x))
		self.tw_aFiles.doubleClicked.connect(self.exeFile)

		self.tw_sShot.currentItemChanged.connect(lambda x, y: self.sShotclicked(x))
		self.tw_sShot.itemExpanded.connect(self.sItemCollapsed)
		self.tw_sShot.itemCollapsed.connect(self.sItemCollapsed)
		self.tw_sShot.customContextMenuRequested.connect(lambda x: self.rclCat("ss",x))
		self.lw_sPipeline.customContextMenuRequested.connect(lambda x: self.rclCat("sp",x))
		self.lw_sCategory.customContextMenuRequested.connect(lambda x: self.rclCat("sc",x))
		self.tw_sFiles.customContextMenuRequested.connect(lambda x: self.rclFile("sf",x))
		self.tw_sFiles.doubleClicked.connect(self.exeFile)

		self.l_shotPreview.mouseDoubleClickEvent = lambda x: self.editShot(self.cursShots)

		self.lw_fCategory.customContextMenuRequested.connect(lambda x: self.rclCat("f",x))
		self.tw_fFiles.customContextMenuRequested.connect(self.rclfFile)
		self.tw_fFiles.doubleClicked.connect(self.exeFile)

		self.actionPrismSettings.triggered.connect(self.core.prismSettings)
		self.actionStateManager.triggered.connect(self.core.stateManager)
		self.actionOpenOnStart.toggled.connect(self.triggerOpen)
		self.actionCheckForUpdates.toggled.connect(self.triggerUpdates)
		self.actionCheckForShotFrameRange.toggled.connect(self.triggerFrameranges)
		self.actionCloseAfterLoad.toggled.connect(self.triggerCloseLoad)
		self.actionAutoplay.toggled.connect(self.triggerAutoplay)
		self.actionAssets.toggled.connect(self.triggerAssets)
		self.actionShots.toggled.connect(self.triggerShots)
		self.actionFiles.toggled.connect(self.triggerFiles)
		self.actionRecent.toggled.connect(self.triggerRecent)
		self.actionRenderings.toggled.connect(self.triggerRenderings)
		self.tbw_browser.currentChanged.connect(self.tabChanged)
		self.tw_recent.customContextMenuRequested.connect(lambda x: self.rclFile("r",x))
		self.tw_recent.doubleClicked.connect(self.exeFile)

		for i in self.appFilters:
			self.appFilters[i]["assetChb"].stateChanged.connect(self.refreshAFile)
			self.appFilters[i]["shotChb"].stateChanged.connect(self.refreshSFile)

		self.b_fH01.clicked.connect(lambda: self.filehiera(1))
		self.b_fH02.clicked.connect(lambda: self.filehiera(2))
		self.b_fH03.clicked.connect(lambda: self.filehiera(3))
		self.b_fH04.clicked.connect(lambda: self.filehiera(4))
		self.b_fH05.clicked.connect(lambda: self.filehiera(5))
		self.b_fH06.clicked.connect(lambda: self.filehiera(6))
		self.b_fH07.clicked.connect(lambda: self.filehiera(7))
		self.b_fH08.clicked.connect(lambda: self.filehiera(8))
		self.b_fH09.clicked.connect(lambda: self.filehiera(9))
		self.b_fH10.clicked.connect(lambda: self.filehiera(10))

		self.chb_autoUpdate.stateChanged.connect(self.updateChanged)
		self.b_refresh.clicked.connect(self.refreshRender)

		self.l_preview.clickEvent = self.l_preview.mouseReleaseEvent
		self.l_preview.mouseReleaseEvent = self.previewClk
		self.l_preview.dclickEvent = self.l_preview.mouseDoubleClickEvent
		self.l_preview.mouseDoubleClickEvent = self.previewDclk
		self.l_preview.customContextMenuRequested.connect(self.rclPreview)
		self.l_preview.mouseMoveEvent = lambda x: self.mouseDrag(x, self.l_preview)

		self.lw_task.itemSelectionChanged.connect(self.taskClicked)
		self.lw_task.mmEvent = self.lw_task.mouseMoveEvent
		self.lw_task.mouseMoveEvent = lambda x: self.mouseDrag(x, self.lw_task)
		self.lw_version.itemSelectionChanged.connect(self.versionClicked)
		self.lw_version.mmEvent = self.lw_version.mouseMoveEvent
		self.lw_version.mouseMoveEvent = lambda x: self.mouseDrag(x, self.lw_version)
		self.lw_version.itemDoubleClicked.connect(self.showVersionInfo)
		self.cb_layer.currentIndexChanged.connect(self.layerChanged)
		self.cb_layer.mmEvent = self.cb_layer.mouseMoveEvent
		self.cb_layer.mouseMoveEvent = lambda x: self.mouseDrag(x, self.cb_layer)
		self.b_addRV.clicked.connect(self.addCompare)
		self.b_compareRV.clicked.connect(self.compare)
		self.b_compareRV.customContextMenuRequested.connect(self.compareOptions)
		self.b_combineVersions.clicked.connect(self.combineVersions)
		self.b_combineVersions.customContextMenuRequested.connect(self.combineOptions)
		self.b_clearRV.clicked.connect(self.clearCompare)
		self.b_saveRender1.clicked.connect(lambda: self.saveClicked(1))
		self.b_saveRender2.clicked.connect(lambda: self.saveClicked(2))
		self.b_saveRender3.clicked.connect(lambda: self.saveClicked(3))
		self.b_saveRender1.customContextMenuRequested.connect(lambda: self.saverClicked(1))
		self.b_saveRender2.customContextMenuRequested.connect(lambda: self.saverClicked(2))
		self.b_saveRender3.customContextMenuRequested.connect(lambda: self.saverClicked(3))
		self.sl_preview.valueChanged.connect(self.sliderChanged)
		self.sl_preview.sliderPressed.connect(self.sliderClk)
		self.sl_preview.sliderReleased.connect(self.sliderRls)
		self.sl_preview.origMousePressEvent = self.sl_preview.mousePressEvent
		self.sl_preview.mousePressEvent = self.sliderDrag
		self.lw_task.customContextMenuRequested.connect(lambda x: self.rclList(x, self.lw_task))
		self.lw_version.customContextMenuRequested.connect(lambda x: self.rclList(x, self.lw_version))
		self.lw_compare.customContextMenuRequested.connect(self.rclCompare)


	def enterEvent(self, event):
		QApplication.restoreOverrideCursor()


	@err_decorator
	def loadLayout(self):
		self.actionRefresh = QAction("Refresh", self)
		self.actionRefresh.triggered.connect(self.refreshUI)
		self.menubar.addAction(self.actionRefresh)

		helpMenu = QMenu("Help")

		self.actionWebsite = QAction("Visit website", self)
		self.actionWebsite.triggered.connect(lambda: self.core.openWebsite("home"))
		helpMenu.addAction(self.actionWebsite)

		self.actionWebsite = QAction("Tutorials", self)
		self.actionWebsite.triggered.connect(lambda:self.core.openWebsite("tutorials"))
		helpMenu.addAction(self.actionWebsite)

		self.actionWebsite = QAction("Documentation", self)
		self.actionWebsite.triggered.connect(lambda: self.core.openWebsite("documentation"))
		helpMenu.addAction(self.actionWebsite)

		self.actionSendFeedback = QAction("Send feedback/feature requests...", self)
		self.actionSendFeedback.triggered.connect(self.core.sendFeedback)
		helpMenu.addAction(self.actionSendFeedback)

		self.actionCheckVersion = QAction("Check for Prism updates", self)
		self.actionCheckVersion.triggered.connect(self.core.checkPrismVersion)
		helpMenu.addAction(self.actionCheckVersion)

		self.actionAbout = QAction("About...", self)
		self.actionAbout.triggered.connect(lambda: self.core.showAbout("Project: %s" % self.version))
		helpMenu.addAction(self.actionAbout)
	
		self.menubar.addMenu(helpMenu)

		self.core.appPlugin.setRCStyle(self, helpMenu)

		self.appFilters = {}
		for i in self.core.getPluginNames():
			if len(self.core.getPluginData(i, "sceneFormats")) == 0:
				continue

			chb_aApp = QCheckBox(i)
			chb_sApp = QCheckBox(i)
			chb_aApp.setChecked(True)
			chb_sApp.setChecked(True)
			self.w_aShowFormats.layout().addWidget(chb_aApp)
			self.w_sShowFormats.layout().addWidget(chb_sApp)
			setattr(self, "chb_aShow%s" % self.core.getPluginData(i, "appShortName"), chb_aApp)
			setattr(self, "chb_sShow%s" % self.core.getPluginData(i, "appShortName"), chb_sApp)
			self.appFilters[i] = {"assetChb": chb_aApp, "shotChb": chb_sApp, "shortName": self.core.getPluginData(i, "appShortName"), "formats": self.core.getPluginData(i, "sceneFormats")}
	
		cData = {}

		for i in self.appFilters:
			sa = self.appFilters[i]["shortName"]
			cData["show%sAssets" % sa] = ["browser", "show%sAssets" % sa, "bool"]
			cData["show%sShots" % sa] = ["browser", "show%sShots" % sa, "bool"]

		cData["showonstartup"] = ["globals", "showonstartup", "bool"]
		cData["checkversions"] = ["globals", "checkversions", "bool"]
		cData["checkframeranges"] = ["globals", "checkframeranges", "bool"]
		cData[self.closeParm] = ["browser", self.closeParm, "bool"]
		cData["autoplaypreview"] = ["browser", "autoplaypreview", "bool"]
		cData["assetsOrder"] = ["browser", "assetsOrder", "int"]
		cData["shotsOrder"] = ["browser", "shotsOrder", "int"]
		cData["filesOrder"] = ["browser", "filesOrder", "int"]
		cData["recentOrder"] = ["browser", "recentOrder", "int"]
		cData["assetsVisible"] = ["browser", "assetsVisible", "bool"]
		cData["shotsVisible"] = ["browser", "shotsVisible", "bool"]
		cData["recentVisible"] = ["browser", "recentVisible", "bool"]
		cData["renderVisible"] = ["browser", "renderVisible", "bool"]
		cData["assetSorting"] = ["browser", "assetSorting"]
		cData["shotSorting"] = ["browser", "shotSorting"]
		cData["fileSorting"] = ["browser", "fileSorting"]
		cData["current"] = ["browser", "current"]
		cData["autoUpdateRenders"] = ["browser", "autoUpdateRenders", "bool"]
		cData["windowSize"] = ["browser", "windowSize"]
		cData["expandedAssets" + self.core.projectName] = ["browser", "expandedAssets" + self.core.projectName]
		cData["expandedSequences" + self.core.projectName] = ["browser", "expandedSequences" + self.core.projectName]

		cData = self.core.getConfig(data=cData)

		if cData["showonstartup"] is not None:
			self.actionOpenOnStart.setChecked(cData["showonstartup"])

		if cData["checkversions"] is not None:
			self.actionCheckForUpdates.setChecked(cData["checkversions"])

		if cData["checkframeranges"] is not None:
			self.actionCheckForShotFrameRange.setChecked(cData["checkframeranges"])

		if cData[self.closeParm] is not None:
			self.actionCloseAfterLoad.setChecked(cData[self.closeParm])

		if cData["autoplaypreview"] is not None:
			state = cData["autoplaypreview"]
			self.actionAutoplay.setChecked(state)

		rprojects = self.core.getConfig(cat="recent_projects", getOptions=True)
		if rprojects is None:
			rprojects = []

		rcData = {}
		for i in rprojects:
			rcData[i] = ["recent_projects", i]

		rPrjPaths = self.core.getConfig(data=rcData)

		for prjName in rPrjPaths:
			prj = rPrjPaths[prjName]
			if prj == "" or prj == self.core.prismIni:
				continue

			rpconfig = ConfigParser()
			try:
				rpconfig.read(prj)
			except:
				continue
				
			if not rpconfig.has_option("globals", "project_name"):
				continue

			rpName = rpconfig.get("globals", "project_name")

			rpAct = QAction(rpName, self)
			rpAct.setToolTip(prj)

			rpAct.triggered.connect(lambda y=None, x=prj: self.core.changeProject(x))
			self.menuRecentProjects.addAction(rpAct)

		if self.menuRecentProjects.isEmpty():
			self.menuRecentProjects.setEnabled(False)

		for i in self.core.prjManagers.values():
			prjMngMenu = i.pbBrowser_getMenu(self)
			if prjMngMenu is not None:
				self.menuTools.addSeparator()
				self.menuTools.addMenu(prjMngMenu)
				self.core.appPlugin.setRCStyle(self, prjMngMenu)

		self.tabOrder = ["Assets","Shots","Files","Recent"]
		if cData["assetsOrder"] is not None and cData["shotsOrder"] is not None and cData["filesOrder"] is not None and cData["recentOrder"] is not None:
			self.tabOrder[cData["assetsOrder"]] = "Assets"
			self.tabOrder[cData["shotsOrder"]] = "Shots"
			self.tabOrder[cData["filesOrder"]] = "Files"
			self.tabOrder[cData["recentOrder"]] = "Recent"

		self.tbw_browser.insertTab(self.tabOrder.index("Assets"), self.t_assets, "Assets")
		self.tbw_browser.insertTab(self.tabOrder.index("Shots"), self.t_shots, "Shots")
		self.tbw_browser.insertTab(self.tabOrder.index("Files"), self.t_files, "Files")
		self.tbw_browser.insertTab(self.tabOrder.index("Recent"), self.t_recent, "Recent")

		if not cData["assetsVisible"]:
			self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_assets))
			self.actionAssets.setChecked(False)

		if not cData["shotsVisible"]:
			self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_shots))
			self.actionShots.setChecked(False)

		self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_files))
		self.actionFiles.setChecked(False)
		self.actionFiles.setVisible(False)

		if not cData["recentVisible"]:
			self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_recent))
			self.actionRecent.setChecked(False)

		if cData["renderVisible"] is not None:
			state = cData["renderVisible"]
			self.actionRenderings.setChecked(state)
			if not state:
				self.gb_renderings.setVisible(state)

		for i in self.appFilters:
			sa = self.appFilters[i]["shortName"]
			if cData["show%sAssets" % sa] is not None:
				eval("self.chb_aShow%s.setChecked(%s)" % (sa, cData["show%sAssets" % sa]))

			if cData["show%sShots" % sa] is not None:
				eval("self.chb_sShow%s.setChecked(%s)" % (sa, cData["show%sShots" % sa]))

		if cData["assetSorting"] is not None:
			assetSort = eval(cData["assetSorting"].replace("PySide.QtCore.", "").replace("PySide2.QtCore.", ""))
			self.tw_aFiles.sortByColumn(assetSort[0], assetSort[1])
		if cData["shotSorting"] is not None:
			shotSort = eval(cData["shotSorting"].replace("PySide.QtCore.", "").replace("PySide2.QtCore.", ""))
			self.tw_sFiles.sortByColumn(shotSort[0], shotSort[1])
		if cData["fileSorting"] is not None:
			fileSort = eval(cData["fileSorting"].replace("PySide.QtCore.", "").replace("PySide2.QtCore.", ""))
			self.tw_fFiles.sortByColumn(fileSort[0], fileSort[1])

		if cData["current"] is not None and cData["current"] != "":
			self.tbw_browser.setCurrentIndex(self.tabOrder.index(cData["current"]))
			self.updateChanged(False)

		if self.tbw_browser.count() == 0:
			self.tbw_browser.setVisible(False)

		if cData["autoUpdateRenders"] is not None:
			self.chb_autoUpdate.setChecked(cData["autoUpdateRenders"])

		self.core.appPlugin.projectBrowserLoadLayout(self)
		self.core.callback(name="projectBrowser_loadUI", types=["unloadedApps"], args=[self])

		if cData["windowSize"] is not None:
			wsize = eval(cData["windowSize"])
			self.resize(wsize[0], wsize[1])
		else:
			screenW = QApplication.desktop().screenGeometry().width()
			screenH = QApplication.desktop().screenGeometry().height()
			space = 200
			if screenH < (self.height()+space):
				self.resize(self.width(), screenH-space)

			if screenW < (self.width()+space):
				self.resize(screenW-space, self.height())

		if cData["expandedAssets" + self.core.projectName] is not None:
			self.aExpanded = eval(cData["expandedAssets" + self.core.projectName])

		if cData["expandedSequences" + self.core.projectName] is not None:
			self.sExpanded = eval(cData["expandedSequences" + self.core.projectName])
		

	@err_decorator
	def closeEvent(self, event):
		tabOrder = []
		for i in range(self.tbw_browser.count()):
			tabOrder.append(self.tbw_browser.tabText(i))

		if not "Assets" in tabOrder:
			tabOrder.append("Assets")

		if not "Shots" in tabOrder:
			tabOrder.append("Shots")

		if not "Files" in tabOrder:
			tabOrder.append("Files")

		if not "Recent" in tabOrder:
			tabOrder.append("Recent")

		visible = []
		for i in range(self.tbw_browser.count()):
			visible.append(self.tbw_browser.tabText(i))

		cData = []

		cData.append(['browser', "current", self.tbw_browser.tabText(self.tbw_browser.currentIndex())])
		cData.append(['browser', "assetsOrder", str(tabOrder.index("Assets"))])
		cData.append(['browser', "shotsOrder", str(tabOrder.index("Shots"))])
		cData.append(['browser', "filesOrder", str(tabOrder.index("Files"))])
		cData.append(['browser', "recentOrder", str(tabOrder.index("Recent"))])

		cData.append(['browser', "assetsVisible", str("Assets" in visible )])
		cData.append(['browser', "shotsVisible", str("Shots" in visible )])
		cData.append(['browser', "filesVisible", str("Files" in visible )])
		cData.append(['browser', "recentVisible", str("Recent" in visible )])

		cData.append(['browser', "renderVisible", str(self.actionRenderings.isChecked())])

		for i in self.appFilters:
			sa = self.appFilters[i]["shortName"]
			cData.append(['browser', "show%sAssets" % sa, str(eval("self.chb_aShow%s.isChecked()" % sa))])
			cData.append(['browser', "show%sShots" % sa, str(eval("self.chb_sShow%s.isChecked()" % sa))])

		cData.append(['browser', "assetSorting", str([self.tw_aFiles.horizontalHeader().sortIndicatorSection(), self.tw_aFiles.horizontalHeader().sortIndicatorOrder()])])
		cData.append(['browser', "shotSorting", str([self.tw_sFiles.horizontalHeader().sortIndicatorSection(), self.tw_sFiles.horizontalHeader().sortIndicatorOrder()])])
		cData.append(['browser', "fileSorting", str([self.tw_fFiles.horizontalHeader().sortIndicatorSection(), self.tw_fFiles.horizontalHeader().sortIndicatorOrder()])])
		cData.append(['browser', "windowSize", str([self.width(), self.height()])])
		cData.append(['browser', "expandedAssets" + self.core.projectName, str(self.getExpandedAssets())])
		cData.append(['browser', "expandedSequences" + self.core.projectName, str(self.getExpandedSequences())])

		cData.append(['browser', "autoUpdateRenders", str(self.chb_autoUpdate.isChecked())])

		self.core.setConfig(data=cData)

		if hasattr(self, "tl") and self.tl.state() != QTimeLine.NotRunning:
			self.tl.setPaused(True)

		QPixmapCache.clear()

		self.core.callback(name="onProjectBrowserClose", types=["curApp", "custom"], args=[self])

		event.accept()


	@err_decorator
	def loadLibs(self):
		global imageio
		try:
			import imageio
		except:
			pass

		if not self.oiioLoaded:
			global numpy, wand
			try:
				import numpy
				import wand, wand.image
				self.wandLoaded = True
			except:
				pass


	@err_decorator
	def getExpandedAssets(self):
		expandedAssets = []
		for i in range(self.tw_aHierarchy.topLevelItemCount()):
			item = self.tw_aHierarchy.topLevelItem(i)
			expandedAssets += self.getExpandedChildren(item)

		return expandedAssets


	@err_decorator
	def getExpandedChildren(self, item):
		expandedAssets = []
		if item.isExpanded():
			expandedAssets.append(item.text(1))
			
		for i in range(item.childCount()):
			expandedAssets += self.getExpandedChildren(item.child(i))

		return expandedAssets


	@err_decorator
	def getExpandedSequences(self):
		expandedSeqs = []
		for i in range(self.tw_sShot.topLevelItemCount()):
			item = self.tw_sShot.topLevelItem(i)
			if item.isExpanded():
				expandedSeqs.append(item.text(0))

		return expandedSeqs


	@err_decorator
	def tabChanged(self, tab):
		if self.tbw_browser.tabText(tab) == "Assets":
			self.refreshAFile()
		elif self.tbw_browser.tabText(tab) == "Shots":
			self.refreshSFile()
		elif self.tbw_browser.tabText(tab) == "Files":
			self.refreshFCat()
		elif self.tbw_browser.tabText(tab) == "Recent":
			self.setRecent()

		if self.gb_renderings.isVisible() and self.chb_autoUpdate.isChecked():
			self.updateTasks()


	@err_decorator
	def refreshUI(self):
		tab = self.tbw_browser.currentIndex()

		curTab = self.tbw_browser.tabText(self.tbw_browser.currentIndex())
		curData = [curTab, self.cursShots, self.curRTask, self.curRVersion, self.curRLayer]

		if self.tbw_browser.tabText(tab) == "Assets":
			curAssetItem = self.tw_aHierarchy.currentItem()
			if curAssetItem is None:
				dstname = self.aBasePath
			else:
				basePath = curAssetItem.text(1)
				curStepItem = self.lw_aPipeline.currentItem()
				if curStepItem is None:
					curStep = ""
				else:
					curStep = os.path.join("Scenefiles", curStepItem.text())
					if not os.path.exists(os.path.join(basePath, curStep)):
						curStep = os.path.join("Scenefiles", curStepItem.text())
				dstname = os.path.join(basePath, curStep)

			self.refreshAHierarchy()
		elif self.tbw_browser.tabText(tab) == "Shots":
			if self.cursShots is None:
				shot = ""
			else:
				shot = self.cursShots

			if self.cursStep is None:
				step = ""
			else:
				step = os.path.join("Scenefiles", self.cursStep)

			if self.cursCat is None:
				cat = ""
			else:
				cat = self.cursCat

			dstname = os.path.join(self.sBasePath, shot, step, cat)

			self.refreshShots()
		elif self.tbw_browser.tabText(tab) == "Recent":
			self.setRecent()
			return
		else:
			return

		self.navigateToCurrent(path=dstname)

		self.showRender(curData[0], curData[1], curData[2], curData[3], curData[4])


	@err_decorator
	def mousedb(self, event, tab, uielement):
		if tab == "ah":
			cItem = uielement.itemFromIndex(uielement.indexAt(event.pos()))
			if cItem is not None and cItem.text(2) == "Asset":
				return
			name = "Entity"
		elif tab == "ap":
			if self.tw_aHierarchy.currentItem() is not None and self.lw_aPipeline.indexAt(event.pos()).data() == None and (self.tw_aHierarchy.currentItem().text(2) == "Asset"):
				self.createStep("a")
		elif tab == "ss":
			mIndex = uielement.indexAt(event.pos())
			if mIndex.data() == None:
				self.editShot()
			else:
				if mIndex.parent().column() == -1 and uielement.mapFromGlobal(QCursor.pos()).x()>10:
					uielement.setExpanded(mIndex, not uielement.isExpanded(mIndex))
					uielement.mouseDClick(event)
		elif tab == "sp":
			if self.cursShots is not None and not (len(self.cursShots.split("-")) == 2 and self.cursShots[-1] == "-") and self.lw_sPipeline.indexAt(event.pos()).data() == None:
				self.createStep("s")
		elif tab == "sc":
			if self.cursStep is not None and self.lw_sCategory.indexAt(event.pos()).data() == None:
				name = "Category"
		elif tab == "f":
			if self.lw_fCategory.indexAt(event.pos()).data() == None:
				name = "Category"
			else:
				name = "Sub-Category"

		if (tab != "f" and tab != "ah" and tab != "ss") or self.dclick or self.adclick or self.sdclick:
			if "name" in locals():
				self.createCatWin(tab, name)

			uielement.mouseDClick(event)

		if tab == "ah" and not self.adclick:
			pos = self.tw_aHierarchy.mapFromGlobal(QCursor.pos())
			item = self.tw_aHierarchy.itemAt(pos.x(), pos.y()-23)
			if item is not None:
				item.setExpanded(not item.isExpanded())
		elif tab == "ss" and not self.sdclick:
			pos = self.tw_sShot.mapFromGlobal(QCursor.pos())
			item = self.tw_sShot.itemAt(pos.x(), pos.y())
			if item is not None:
				item.setExpanded(not item.isExpanded())


	@err_decorator
	def mouseClickEvent(self, event, uielement):
		if QEvent != None:
			if event.type() == QEvent.MouseButtonRelease:
				if event.button() == Qt.LeftButton:
					if uielement == "ah":
						index = self.tw_aHierarchy.indexAt(event.pos())
						if index.data() == None:
							self.tw_aHierarchy.setCurrentIndex(self.tw_aHierarchy.model().createIndex(-1,0))
						self.tw_aHierarchy.mouseClickEvent(event)
					elif uielement == "ap":
						index = self.lw_aPipeline.indexAt(event.pos())
						if index.data() == None:
							self.lw_aPipeline.setCurrentIndex(self.lw_aPipeline.model().createIndex(-1,0))
						self.lw_aPipeline.mouseClickEvent(event)
					elif uielement == "af":
						index = self.tw_aFiles.indexAt(event.pos())
						if index.data() == None:
							self.tw_aFiles.setCurrentIndex(self.tw_aFiles.model().createIndex(-1,0))
						self.tw_aFiles.mouseClickEvent(event)
					elif uielement == "ss":
						index = self.tw_sShot.indexAt(event.pos())
						if index.data() == None:
							self.tw_sShot.setCurrentIndex(self.tw_sShot.model().createIndex(-1,0))
						self.tw_sShot.mouseClickEvent(event)
					elif uielement == "sp":
						index = self.lw_sPipeline.indexAt(event.pos())
						if index.data() == None:
							self.lw_sPipeline.setCurrentIndex(self.lw_sPipeline.model().createIndex(-1,0))
						self.lw_sPipeline.mouseClickEvent(event)
					elif uielement == "sc":
						index = self.lw_sCategory.indexAt(event.pos())
						if index.data() == None:
							self.lw_sCategory.setCurrentIndex(self.lw_sCategory.model().createIndex(-1,0))
						self.lw_sCategory.mouseClickEvent(event)
					elif uielement == "sf":
						index = self.tw_sFiles.indexAt(event.pos())
						if index.data() == None:
							self.tw_sFiles.setCurrentIndex(self.tw_sFiles.model().createIndex(-1,0))
						self.tw_sFiles.mouseClickEvent(event)
					elif uielement == "fc":
						self.fbottom = False
						index = self.lw_fCategory.indexAt(event.pos())
						self.FCatclicked(index)
						self.lw_fCategory.mouseClickEvent(event)
					elif uielement == "ff":
						index = self.tw_fFiles.indexAt(event.pos())
						if index.data() == None:
							self.tw_fFiles.setCurrentIndex(self.tw_fFiles.model().createIndex(-1,0))
						self.tw_fFiles.mouseClickEvent(event)
					elif uielement == "r":
						index = self.tw_recent.indexAt(event.pos())
						if index.data() == None:
							self.tw_recent.setCurrentIndex(self.tw_recent.model().createIndex(-1,0))
						self.tw_recent.mouseClickEvent(event)
			elif event.type() == QEvent.MouseButtonPress:
				if uielement == "f":
					self.dclick = True
					self.lw_fCategory.mousePrEvent(event)
				elif uielement == "ah":
					self.adclick = True
					self.tw_aHierarchy.mousePrEvent(event)
				elif uielement == "ss":
					self.sdclick = True
					self.tw_sShot.mousePrEvent(event)


	@err_decorator
	def rclCat(self, tab, pos):
		rcmenu = QMenu()
		typename = "Category"

		if tab == "ah":
			lw = self.tw_aHierarchy
			cItem = lw.itemFromIndex(lw.indexAt(pos))
			if cItem is None:
				path = self.aBasePath
			else:
				path = os.path.dirname(cItem.text(1))
			typename = "Entity"
		elif tab == "ap":
			lw = self.lw_aPipeline
			curItem = self.tw_aHierarchy.currentItem()
			if curItem is None:
				return

			if curItem.text(2) != "Asset":
				return

			path = os.path.join(curItem.text(1), "Scenefiles")

			typename = "Step"

		elif tab == "ss":
			lw = self.tw_sShot
			path = self.sBasePath
			typename = "Shot"

		elif tab == "sp":
			lw = self.lw_sPipeline
			if self.cursShots is not None:
				path = os.path.join(self.sBasePath, self.cursShots, "Scenefiles")
			else:
				return False
			typename = "Step"

		elif tab == "sc":
			lw = self.lw_sCategory
			if self.cursStep is not None:
				path = os.path.join(self.sBasePath, self.cursShots, "Scenefiles", self.cursStep)
			else:
				return False

		elif tab == "f":
			lw = self.lw_fCategory
			path = self.fpath
			fname = lw.indexAt(pos).data()
			if fname != None:
				fpath = os.path.join(self.fpath, fname)
			copyact = QAction("Copy", self)
			copyact.triggered.connect(lambda: self.copyfile(fpath, "Copy"))
			if fname == None:
				copyact.setEnabled(False)
			rcmenu.addAction(copyact)
			cutact = QAction("Cut", self)
			cutact.triggered.connect(lambda: self.copyfile(fpath, "Cut"))
			if fname == None:
				cutact.setEnabled(False)
			rcmenu.addAction(cutact)
			pasteact = QAction("Paste", self)
			pasteact.triggered.connect(lambda: self.pastefile(tab))
			if self.copiedfFile == None or type(self.copiedfFile) == list:
				pasteact.setEnabled(False)
			rcmenu.addAction(pasteact)

		if tab in ["ap", "ss", "sp", "sc"]:
			createAct = QAction("Create " + typename, self)
			if tab == "ap":
				createAct.triggered.connect(lambda: self.createStep("a"))
			elif tab == "sp":
				createAct.triggered.connect(lambda: self.createStep("s"))
			elif tab == "ss":
				createAct.triggered.connect(self.editShot)
			else:
				createAct.triggered.connect(lambda: self.createCatWin(tab, typename))
			rcmenu.addAction(createAct)

		iname = (lw.indexAt(pos)).data()

		if iname != None and (tab != "ss" or lw.itemAt(pos).childCount() == 0):
			prjMngMenus = []
			addOmit = False
			if tab == "ah" or tab == "f":
				if cItem is not None and cItem.text(2) != "Asset":
					subcat = QAction("Create entity", self)
					typename = "Entity"
					subcat.triggered.connect(lambda: self.createCatWin(tab, typename))
					rcmenu.addAction(subcat)
				elif cItem.text(2) == "Asset":
					for i in self.core.prjManagers.values():
						prjMngMenu = i.pbBrowser_getAssetMenu(self, iname, cItem.text(1).replace(self.aBasePath, "")[1:])
						if prjMngMenu is not None:
							prjMngMenus.append(prjMngMenu)

				oAct = QAction("Omit Asset", self)
				oAct.triggered.connect(lambda: self.omitEntity("Asset", cItem.text(1).replace(self.aBasePath, "")[1:]))
				addOmit = True

				if tab == "f":
					self.fclickedon = iname
			elif tab == "ss":
				iname = self.cursShots
				editAct = QAction("Edit shot settings", self)
				editAct.triggered.connect(lambda: self.editShot(iname))
				rcmenu.addAction(editAct)
				for i in self.core.prjManagers.values():
					prjMngMenu = i.pbBrowser_getShotMenu(self, iname)
					if prjMngMenu is not None:
						prjMngMenus.append(prjMngMenu)

				oAct = QAction("Omit Shot", self)
				oAct.triggered.connect(lambda: self.omitEntity("Shot", self.cursShots))
				addOmit = True
			dirPath = os.path.join(path, iname)
			if not os.path.exists(dirPath) and self.core.useLocalFiles and os.path.exists(dirPath.replace(self.core.projectPath, self.core.localProjectPath)):
				dirPath = dirPath.replace(self.core.projectPath, self.core.localProjectPath)
			openex = QAction("Open in Explorer", self)
			openex.triggered.connect(lambda: self.core.openFolder(dirPath))
			rcmenu.addAction(openex)
			copAct = QAction("Copy path", self)
			copAct.triggered.connect(lambda: self.core.copyToClipboard(dirPath))
			rcmenu.addAction(copAct)
			for i in prjMngMenus:
				rcmenu.addAction(i)
			if addOmit:
				rcmenu.addAction(oAct)
		elif "path" in locals():
			lw.setCurrentIndex(lw.model().createIndex(-1,0))
			if tab not in ["ap", "ss", "sp", "sc"]:
				cat = QAction("Create " + typename, self)
				cat.triggered.connect(lambda: self.createCatWin(tab, typename))
				rcmenu.addAction(cat)
			openex = QAction("Open in Explorer", self)
			openex.triggered.connect(lambda: self.core.openFolder(path))
			rcmenu.addAction(openex)
			copAct = QAction("Copy path", self)
			copAct.triggered.connect(lambda: self.core.copyToClipboard(path))
			rcmenu.addAction(copAct)

		self.core.appPlugin.setRCStyle(self, rcmenu)

		rcmenu.exec_(QCursor.pos())

	@err_decorator
	def rclFile(self, tab, pos):
		if tab == "a":
			if self.lw_aPipeline.currentItem() is None:
				return

			tw = self.tw_aFiles
			filepathrow = 5
			filepath = os.path.join(self.tw_aHierarchy.currentItem().text(1), "Scenefiles", self.lw_aPipeline.currentItem().text())
		elif tab == "sf":
			if self.cursStep is None or self.cursCat is None:
				return

			tw = self.tw_sFiles
			filepathrow = 5
			filepath = os.path.join(self.sBasePath, self.cursShots, "Scenefiles", self.cursStep, self.cursCat)
		elif tab == "r":
			tw = self.tw_recent
			filepathrow = 7

		rcmenu = QMenu()

		if tw.selectedIndexes() != []:
			irow = tw.selectedIndexes()[0].row()
		else:
			irow = -1
		cop = QAction("Copy", self)
		if irow == -1 :
			if tab == "r":
				return False
			cop.setEnabled(False)
			if not os.path.exists(filepath) and self.core.useLocalFiles and os.path.exists(filepath.replace(self.core.projectPath, self.core.localProjectPath)):
				filepath = filepath.replace(self.core.projectPath, self.core.localProjectPath)
		else:
			filepath = self.core.fixPath(tw.model().index(irow, filepathrow).data())
			cop.triggered.connect(lambda: self.copyfile(filepath))
			tw.setCurrentIndex(tw.model().createIndex(irow,0))
		if tab != "r":
			rcmenu.addAction(cop)
			past = QAction("Paste as new version", self)
			past.triggered.connect(lambda: self.pastefile(tab))
			if not (tab == "a" and self.copiedFile != None) and not (tab == "sf" and self.copiedsFile != None):
				past.setEnabled(False)
			rcmenu.addAction(past)
			current = QAction("Create new version from current", self)
			current.triggered.connect(lambda: self.createFromCurrent())
			if self.core.appPlugin.pluginName == "Standalone":
				current.setEnabled(False)
			rcmenu.addAction(current)
			emp = QMenu("Create empty file")
			emptyDir = os.path.join(os.path.dirname(self.core.prismIni), "EmptyScenes")
			if os.path.exists(emptyDir):
				for i in sorted(os.listdir(emptyDir)):
					if i.startswith("EmptyScene_") and os.path.splitext(i)[1] in self.core.getPluginSceneFormats():
						fName = os.path.splitext(i)[0][11:].replace("_", ".")
						empAct = QAction(fName, self)
						empAct.triggered.connect(lambda y=None, x=tab, fname=i: self.createEmpty(x,fname))
						emp.addAction(empAct)

			newPreset = QAction("< Create new preset from current >", self)
			newPreset.triggered.connect(lambda y=None, x=tab: self.createEmpty(x,"createnew"))
			emp.addAction(newPreset)
			if self.core.appPlugin.pluginName == "Standalone":
				newPreset.setEnabled(False)

			self.core.appPlugin.setRCStyle(self, emp)
			rcmenu.addMenu(emp)
			autob = QMenu("Create new version from autoback")
			for i in self.core.getPluginNames():
				if self.core.getPluginData(i, "appType") == "standalone":
					continue

				autobAct = QAction(i, self)
				autobAct.triggered.connect(lambda y=None, x=i: self.autoback(tab, x))
				autob.addAction(autobAct)

			self.core.appPlugin.setRCStyle(self, autob)
			rcmenu.addMenu(autob)

		if irow != -1:
			if tab != "r":
				globalAct = QAction("Copy to global", self)
				if self.core.useLocalFiles and filepath.startswith(self.core.localProjectPath):
					globalAct.triggered.connect(lambda: self.copyToGlobal(filepath))
				else:
					globalAct.setEnabled(False)
				rcmenu.addAction(globalAct)

			desc = QAction("Show description", self)
			sceneName = os.path.splitext(os.path.basename(filepath))[0]
			descPath = os.path.join(os.path.dirname(self.core.prismIni), "SceneDescriptions", sceneName + ".txt")
			if os.path.exists(descPath):
				with open(descPath, 'r') as descFile:
					fileDescription = descFile.read()
				desc.triggered.connect(lambda: QMessageBox.information(self.core.messageParent, "Scene description", fileDescription))
			else:
				desc.setEnabled(False)
			rcmenu.addAction(desc)

			actDeps = QAction("Show dependencies", self)
			infoPath = os.path.splitext(filepath)[0] + "versioninfo.ini"
			if os.path.exists(infoPath):
				with open(infoPath, 'r') as descFile:
					fileDescription = descFile.read()
				actDeps.triggered.connect(lambda: self.core.dependencyViewer(infoPath))
			else:
				actDeps.setEnabled(False)
			rcmenu.addAction(actDeps)

		openex = QAction("Open in Explorer", self)
		openex.triggered.connect(lambda: self.core.openFolder(filepath))
		rcmenu.addAction(openex)

		copAct = QAction("Copy path", self)
		copAct.triggered.connect(lambda: self.core.copyToClipboard(filepath))
		rcmenu.addAction(copAct)

		self.core.appPlugin.setRCStyle(self, rcmenu)
		rcmenu.exec_((tw.viewport()).mapToGlobal(pos))


	@err_decorator
	def rclfFile(self, pos):
		tw = self.tw_fFiles
		rcmenu = QMenu()

		fpath = []
		for i in tw.selectedIndexes():
			path = i.model().index(i.row(),2).data()
			if path not in fpath:
				fpath.append(path)

		cop = QAction("Copy", self)
		cop.triggered.connect(lambda: self.copyfile(fpath, "Copy"))
		if tw.selectedIndexes() == []:
			cop.setEnabled(False)
		rcmenu.addAction(cop)
		cut = QAction("Cut", self)
		cut.triggered.connect(lambda: self.copyfile(fpath, "Cut"))
		if tw.selectedIndexes() == []:
			cut.setEnabled(False)
		rcmenu.addAction(cut)
		past = QAction("Paste", self)
		past.triggered.connect(lambda: self.pastefile("f"))
		if self.copiedfFile == None or type(self.copiedfFile) == str:
			past.setEnabled(False)
		rcmenu.addAction(past)
		openex = QAction("Open in Explorer", self)
		openex.triggered.connect(self.openFFile)
		rcmenu.addAction(openex)
		self.core.appPlugin.setRCStyle(self, rcmenu)
		rcmenu.exec_((tw.viewport()).mapToGlobal(pos))


	@err_decorator
	def exeFile(self, index=None, filepath=""):
		openSm = hasattr(self.core, "sm") and not self.core.sm.isHidden()
		if hasattr(self.core, "sm"):
			self.core.sm.close()

		if self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Assets":
			column = 5
			refresh = self.refreshAFile
		elif self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Shots":
			column = 5
			refresh = self.refreshSFile
		elif self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Files":
			column = 2
			refresh = self.refreshFCat
		elif self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Recent":
			column = 7
			refresh = self.setRecent

		if filepath == "":
			filepath = index.model().index(index.row(), column).data()

		if self.core.useLocalFiles and os.path.join(self.core.projectPath, self.scenes) in filepath:
			lfilepath = filepath.replace(self.core.projectPath, self.core.localProjectPath)

			if not os.path.exists(lfilepath):
				if not os.path.exists(os.path.dirname(lfilepath)):
					try:
						os.makedirs(os.path.dirname(lfilepath))
					except:
						QMessageBox.warning(self.core.messageParent,"Warning", "The directory could not be created")
						return

				self.core.copySceneFile(filepath, lfilepath)
			
			filepath = lfilepath

		filepath = filepath.replace("\\","/")

		isOpen = self.core.appPlugin.openScene(self, filepath)

		if not isOpen and self.core.appPlugin.pluginName == "Standalone":
			fileStarted = False
			ext = os.path.splitext(filepath)[1]
			appPath = ""

			for i in self.core.unloadedAppPlugins.values():
				if ext in i.sceneFormats:
					orApp = self.core.getConfig("dccoverrides", "%s_override" % i.pluginName.lower(), ptype="bool")
					if orApp is not None and orApp:
						appOrPath = self.core.getConfig("dccoverrides", "%s_path" % i.pluginName.lower())
						if appOrPath is not None and os.path.exists(appOrPath) and os.path.splitext(appOrPath)[1] == ".exe":
							appPath = appOrPath

					fileStarted = getattr(i, "customizeExecutable", lambda x1,x2,x3: False)(self, appPath, filepath)

			if appPath != "" and not fileStarted:
				subprocess.Popen([appPath, self.core.fixPath(filepath)])
				fileStarted = True

			if not fileStarted:
				try:
					if platform.system() == "Windows":
						os.startfile(filepath)
					elif platform.system() == "Linux":
						subprocess.Popen(["xdg-open", filepath])
					elif platform.system() == "Darwin":
						subprocess.Popen(["open", filepath])
				except:
					ext = os.path.splitext(filepath)[1]
					warnStr = "Could not open the scenefile.\n\nPossibly there is no application connected to \"%s\" files on your computer.\nUse the overrides in the \"DCC apps\" tab of the Prism Settings to specify an application for this filetype." % ext
					msg = QMessageBox(QMessageBox.Warning, "Warning", warnStr, QMessageBox.Ok, parent=self.core.messageParent)
					msg.exec_()

		if self.tbw_browser.tabText(self.tbw_browser.currentIndex()) != "Files":
			self.core.addToRecent(filepath)
			self.setRecent()

		if openSm:
			self.core.stateManager()

		refresh()
		if self.core.getCurrentFileName().replace("\\","/") == filepath and self.actionCloseAfterLoad.isChecked():
			self.close()


	@err_decorator
	def createFromCurrent(self):

		fname = self.core.getCurrentFileName()
		if self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Assets":
			dstname = self.tw_aHierarchy.currentItem().text(1)
			refresh = self.refreshAFile

			prefix = self.tw_aHierarchy.currentItem().text(0)
			step = self.lw_aPipeline.currentItem().text()
			dstname = os.path.join(dstname, "Scenefiles", step)
			newfname = prefix + self.core.filenameSeperator + step + self.core.filenameSeperator + self.core.getHighestVersion(dstname, "Asset") + self.core.filenameSeperator + "nocomment" + self.core.filenameSeperator + self.core.user

		elif self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Shots":
			dstname = os.path.join(self.sBasePath, self.cursShots, "Scenefiles", self.cursStep, self.cursCat)
			refresh = self.refreshSFile

			subcat = self.core.filenameSeperator + self.cursCat
			newfname = "shot" + self.core.filenameSeperator + self.cursShots + self.core.filenameSeperator + self.cursStep + subcat + self.core.filenameSeperator + self.core.getHighestVersion(dstname, "Shot") + self.core.filenameSeperator + "nocomment" + self.core.filenameSeperator + self.core.user

		if "newfname" in locals():
			filepath = os.path.join(dstname, newfname)

			if self.core.useLocalFiles:
				filepath = filepath.replace(self.core.projectPath, self.core.localProjectPath)

			if not os.path.exists(os.path.dirname(filepath)):
				try:
					os.makedirs(os.path.dirname(filepath))
				except:
					QMessageBox.warning(self.core.messageParent,"Warning", "The directory could not be created")
					return None

			filepath = filepath.replace("\\","/")
			filepath += self.core.filenameSeperator + self.core.appPlugin.getSceneExtension(self)

			filepath = self.core.saveScene(prismReq=False, filepath=filepath)
			self.core.sceneOpen()

			self.core.addToRecent(filepath)
			self.setRecent()
		refresh()


	@err_decorator
	def autoback(self, tab, prog):
		if prog == self.core.appPlugin.pluginName:
			autobackpath, fileStr = self.core.appPlugin.getAutobackPath(self, tab)
		else:
			for i in self.core.unloadedAppPlugins.values():
				if i.pluginName == prog:
					autobackpath, fileStr = i.getAutobackPath(self, tab)

		autobfile = QFileDialog.getOpenFileName(self, "Select Autoback File", autobackpath, fileStr)[0]

		if autobfile != "":
			if tab == "a":
				dstname = self.tw_aHierarchy.currentItem().text(1)
				refresh = self.refreshAFile

				prefix = self.tw_aHierarchy.currentItem().text(0)
				step = self.lw_aPipeline.currentItem().text()
				dstname = os.path.join(dstname, "Scenefiles", step)
				newfname = prefix + self.core.filenameSeperator + step + self.core.filenameSeperator + self.core.getHighestVersion(dstname, "Asset") + self.core.filenameSeperator + "nocomment" + self.core.filenameSeperator + self.core.user + self.core.filenameSeperator + os.path.splitext(autobfile)[1]

			elif tab == "sf":
				dstname = os.path.join(self.sBasePath, self.cursShots, "Scenefiles", self.cursStep, self.cursCat)
				refresh = self.refreshSFile

				subcat = self.core.filenameSeperator + self.cursCat
				newfname = "shot" + self.core.filenameSeperator + self.cursShots + self.core.filenameSeperator + self.cursStep + subcat
				if len(os.path.basename(autobfile).split(self.core.filenameSeperator)) == 8:
					newfname += self.core.filenameSeperator + self.core.getHighestVersion(dstname, "Shot") + self.core.filenameSeperator + os.path.basename(autobfile).split(self.core.filenameSeperator)[5] + self.core.filenameSeperator + self.core.user + self.core.filenameSeperator + os.path.splitext(autobfile)[1]
				else:
					newfname += self.core.filenameSeperator + self.core.getHighestVersion(dstname, "Shot") + self.core.filenameSeperator + "nocomment" + self.core.filenameSeperator + self.core.user + self.core.filenameSeperator + os.path.splitext(autobfile)[1]

			if "newfname" in locals():
				filepath = os.path.join(dstname, newfname)

				if self.core.useLocalFiles:
					filepath = filepath.replace(self.core.projectPath, self.core.localProjectPath)

				if not os.path.exists(os.path.dirname(filepath)):
					try:
						os.makedirs(os.path.dirname(filepath))
					except:
						QMessageBox.warning(self.core.messageParent,"Warning", "The directory could not be created")
						return None

				filepath = filepath.replace("\\","/")

				self.core.copySceneFile(autobfile, filepath)
				if prog == self.core.appPlugin.pluginName:
					self.exeFile(filepath=filepath)
				else:
					self.core.addToRecent(filepath)
					self.setRecent()
					refresh()


	@err_decorator
	def createEmpty(self, tab, fname):
		if fname == "createnew":
			emptyDir = os.path.join(os.path.dirname(self.core.prismIni), "EmptyScenes")

			newItem = CreateItem.CreateItem(core=self.core, startText=self.core.appPlugin.pluginName.replace(" ", ""))

			self.core.parentWindow(newItem)
			newItem.e_item.setFocus()
			newItem.setWindowTitle("Create empty scene")
			newItem.l_item.setText("Preset name:")
			result = newItem.exec_()

			if result == 1:
				pName = newItem.e_item.text()

				filepath = os.path.join(emptyDir, "EmptyScene_%s" % pName)
				filepath = filepath.replace("\\","/")
				filepath += self.core.appPlugin.getSceneExtension(self)

				self.core.saveScene(prismReq=False, filepath=filepath)
			return


		if tab == "a":
			dstname = self.tw_aHierarchy.currentItem().text(1)
			refresh = self.refreshAFile

			prefix = self.tw_aHierarchy.currentItem().text(0)
			step = self.lw_aPipeline.currentItem().text()
			dstname = os.path.join(dstname, "Scenefiles", step)
			newfname = prefix + self.core.filenameSeperator + step + self.core.filenameSeperator + self.core.getHighestVersion(dstname, "Asset") + self.core.filenameSeperator + "nocomment" + self.core.filenameSeperator + self.core.user

			#example filename: Body_mod_v0002_details-added_rfr_.max
		elif tab == "sf":
			refresh = self.refreshSFile
			dstname = os.path.join(self.sBasePath, self.cursShots, "Scenefiles", self.cursStep, self.cursCat)
			#example filename: shot_0010_mod_main_v0002_details-added_rfr_.max
			subcat = self.core.filenameSeperator + self.cursCat
			newfname = "shot" + self.core.filenameSeperator + self.cursShots + self.core.filenameSeperator + self.cursStep + subcat
			newfname += self.core.filenameSeperator + self.core.getHighestVersion(dstname, "Shot") + self.core.filenameSeperator + "nocomment" + self.core.filenameSeperator + self.core.user

		if "newfname" in locals():
			ext = os.path.splitext(fname)[1]
			scene = os.path.join(os.path.dirname(self.core.prismIni), "EmptyScenes", fname)

			newfname += self.core.filenameSeperator + ext

			filepath = os.path.join(dstname, newfname)

			if self.core.useLocalFiles:
				filepath = filepath.replace(self.core.projectPath, self.core.localProjectPath)

			if not os.path.exists(os.path.dirname(filepath)):
				try:
					os.makedirs(os.path.dirname(filepath))
				except:
					QMessageBox.warning(self.core.messageParent,"Warning", "The directory could not be created")
					return None

			filepath = filepath.replace("\\","/")

			shutil.copyfile(scene, filepath)
			if ext in self.core.appPlugin.sceneFormats:
				self.core.callback(name="preLoadEmptyScene", types=["curApp", "custom"], args=[self, filepath])
				self.exeFile(filepath=filepath)
				self.core.callback(name="postLoadEmptyScene", types=["curApp", "custom"], args=[self, filepath])
			else:
				self.core.addToRecent(filepath)
				self.setRecent()
				refresh()


	@err_decorator
	def copyfile(self, path, mode = None):
		if self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Assets":
			self.copiedFile = path
		elif self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Shots":
			self.copiedsFile = path 
		elif self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Files":
			self.fcopymode = mode
			self.copiedfFile = path


	@err_decorator
	def pastefile(self, tab):
		if tab == "a":
			dstname = self.tw_aHierarchy.currentItem().text(1)
			refresh = self.refreshAFile

			prefix = self.tw_aHierarchy.currentItem().text(0)
			step = self.lw_aPipeline.currentItem().text()
			dstname = os.path.join(dstname, "Scenefiles", step)
			oldfname = os.path.basename(self.copiedFile).split(self.core.filenameSeperator)
			newfname = prefix + self.core.filenameSeperator + step + self.core.filenameSeperator + self.core.getHighestVersion(dstname, "Asset") + self.core.filenameSeperator + "nocomment" + self.core.filenameSeperator + self.core.user + self.core.filenameSeperator + oldfname[5]
			dstname = os.path.join(dstname, newfname)

			if self.core.useLocalFiles:
				dstname = dstname.replace(self.core.projectPath, self.core.localProjectPath)

			if not os.path.exists(os.path.dirname(dstname)):
				try:
					os.makedirs(os.path.dirname(dstname))
				except:
					QMessageBox.warning(self.core.messageParent,"Warning", "The directory could not be created")
					return None
		
			dstname = dstname.replace("\\","/")

			self.core.copySceneFile(self.copiedFile, dstname)

			if os.path.splitext(dstname)[1] in self.core.appPlugin.sceneFormats:
				self.exeFile(filepath=dstname)
			else:
				self.core.addToRecent(dstname)
				self.setRecent()

			self.refreshAFile()

		elif tab == "sf":
			dstname = os.path.join(self.sBasePath, self.cursShots, "Scenefiles", self.cursStep, self.cursCat)

			oldfname = os.path.basename(self.copiedsFile)

			fname = oldfname.split(self.core.filenameSeperator)
			fname[1] = self.cursShots
			fname[2] = self.cursStep
			subcat = self.cursCat
			fname[3] = subcat
			fname[4] = self.core.getHighestVersion(dstname, "Shot")
			fname[5] = "nocomment"
			fname[6] = self.core.user
			newfname = ""
			for i in fname:
				newfname += i + self.core.filenameSeperator
			newfname = newfname[:-1]
			dstname = os.path.join(dstname, newfname)

			if self.core.useLocalFiles:
				dstname = dstname.replace(self.core.projectPath, self.core.localProjectPath)

			if not os.path.exists(os.path.dirname(dstname)):
				try:
					os.makedirs(os.path.dirname(dstname))
				except:
					QMessageBox.warning(self.core.messageParent,"Warning", "The directory could not be created")
					return None

			dstname = dstname.replace("\\","/")

			self.core.copySceneFile(self.copiedsFile, dstname)

			if os.path.splitext(dstname)[1] in self.core.appPlugin.sceneFormats:
				self.exeFile(filepath=dstname)
			else:
				self.core.addToRecent(dstname)
				self.setRecent()
		
			self.refreshSFile()

		elif tab == "f":
			if type(self.copiedfFile) == list:
				if self.fbottom:
					dstname = self.fpath + self.fclickedon
				else:
					dstname = self.fpath
				for i in self.copiedfFile:
					fname = os.path.basename(i)
					dstfname = os.path.join(dstname, fname)
					if i != dstfname:
						if self.fcopymode == "Copy":
							self.core.copySceneFile(i, dstfname)
						elif self.fcopymode == "Cut":
							shutil.move(i, dstfname)
					else:
						QMessageBox.warning(self.core.messageParent,"Warning", "Could not paste %s, because the root an the target are the same" % dstname)
			elif type(self.copiedfFile) == str:
				if self.lw_fCategory.selectedIndexes() == []:
					dstname = self.fpath
				else:
					dstname = os.path.join(self.fpath, self.lw_fCategory.selectedIndexes()[0].data())
				dstname = os.path.join(dstname, self.copiedfFile.split(os.sep)[len(self.copiedfFile.split(os.sep))-1])
				if self.copiedfFile != dstname :
					if self.fcopymode == "Copy":
						shutil.copytree(self.copiedfFile, dstname)
					elif self.fcopymode == "Cut":
						shutil.move(self.copiedfFile, dstname)
				else:
					QMessageBox.warning(self.core.messageParent,"Warning", "Could not paste %s\nbecause the root an the target are the same." % dstname.replace("\\", "/"))

			self.refreshFCat()


	@err_decorator
	def getStep(self, steps, tab):
		try:
			del sys.modules["ItemList"]
		except:
			pass

		if tab == "a":
			entity = "asset"
		elif tab == "s":
			entity = "shot"

		import ItemList
		self.ss = ItemList.ItemList(core = self.core, entity=entity)
		self.core.parentWindow(self.ss)
		self.ss.tw_steps.doubleClicked.connect(self.ss.accept)

		abrSteps = list(steps.keys())
		abrSteps.sort()
		for i in abrSteps:
			rc = self.ss.tw_steps.rowCount()
			self.ss.tw_steps.insertRow(rc)
			abrItem = QTableWidgetItem(i)
			self.ss.tw_steps.setItem(rc, 0, abrItem)
			stepItem = QTableWidgetItem(steps[i])
			self.ss.tw_steps.setItem(rc, 1, stepItem)

		result = self.ss.exec_()

		if result == 1:
			steps = []
			for i in self.ss.tw_steps.selectedItems():
				if i.column() == 0:
					steps.append(i.text())

			if len(steps) > 0:
				return [steps, self.ss.chb_category.isChecked()]
			else:
				return False
		else:
			return False


	@err_decorator
	def refreshAHierarchy(self, load=False):
		self.tw_aHierarchy.clear()

		if self.core.useLocalFiles:
			lBasePath = self.aBasePath.replace(self.core.projectPath, self.core.localProjectPath)

		dirs = []

		for i in os.walk(self.aBasePath):
			for k in i[1]:
				if k in ["Export", "Playblasts", "Rendering", "Scenefiles"]:
					continue
				dirs.append(os.path.join(i[0], k))
			break

		if self.core.useLocalFiles:
			for i in os.walk(lBasePath):
				for k in i[1]:
					if k in ["Export", "Playblasts", "Rendering", "Scenefiles"]:
						continue

					ldir = os.path.join(i[0], k)
					if ldir.replace(self.core.localProjectPath, self.core.projectPath) not in dirs:
						dirs.append(ldir)
				break

		self.refreshOmittedEntities()

		for path in dirs:
			val = os.path.basename(path)
			if val not in self.omittedEntities["Asset"]:
				item = QTreeWidgetItem([val, path])
				self.tw_aHierarchy.addTopLevelItem(item)
				self.refreshAItem(item, expanded=False)

		if self.tw_aHierarchy.topLevelItemCount() > 0:
			self.tw_aHierarchy.setCurrentItem(self.tw_aHierarchy.topLevelItem(0))
		else:
			self.refreshAStep()


	@err_decorator
	def refreshAItem(self, item, expanded=True):
		item.takeChildren()

		path = item.text(1)

		if expanded:
			self.adclick = False
			if item.text(1) not in self.aExpanded:
				self.aExpanded.append(item.text(1))

		if self.core.useLocalFiles:
			path = path.replace(self.core.localProjectPath, self.core.projectPath)

			lpath = path.replace(self.core.projectPath, self.core.localProjectPath)

		dirContent = []
		dirContentPaths = []

		if os.path.exists(path):
			dirContent += os.listdir(path)
			dirContentPaths += [os.path.join(path,x) for x in os.listdir(path)]

		if self.core.useLocalFiles and os.path.exists(lpath):
			dirContent += os.listdir(lpath)
			dirContentPaths += [os.path.join(lpath,x) for x in os.listdir(lpath)]

		isAsset = False
		if "Export" in dirContent and "Playblasts" in dirContent and "Rendering" in dirContent and "Scenefiles" in dirContent:
			isAsset = True
			item.setText(2, "Asset")
		else:
			item.setText(2, "Folder")
			childs = []
			for i in dirContentPaths:
				if os.path.isdir(i):
						if os.path.basename(i) not in childs and i.replace(self.aBasePath, "")[1:] not in self.omittedEntities["Asset"]:
							child = QTreeWidgetItem([os.path.basename(i), i])
							item.addChild(child)
							childs.append(os.path.basename(i))
							if expanded:
								self.refreshAItem(child, expanded=False)

		if isAsset:
			iFont = item.font(0)
			iFont.setBold(True)
			item.setFont(0, iFont)

		if path in self.aExpanded and not expanded:
			item.setExpanded(True)


	@err_decorator
	def hItemCollapsed(self, item):
		self.adclick = False
		if item.text(1) in self.aExpanded:
			self.aExpanded.remove(item.text(1))


	@err_decorator
	def refreshAStep(self, cur=None, prev=None):
		self.lw_aPipeline.clear()

		if self.tw_aHierarchy.currentItem() is None:
			self.refreshAFile()
			return

		path = os.path.join(self.tw_aHierarchy.currentItem().text(1), "Scenefiles")

		if self.core.useLocalFiles:
			path = path.replace(self.core.localProjectPath, self.core.projectPath)
			lpath = path.replace(self.core.projectPath, self.core.localProjectPath)

		dirContent = []

		if os.path.exists(path):
			dirContent += [os.path.join(path,x) for x in os.listdir(path)]

		if self.core.useLocalFiles and os.path.exists(lpath):
			dirContent += [os.path.join(lpath,x) for x in os.listdir(lpath)]

		addedSteps = []
		for i in sorted(dirContent):
			stepName = os.path.basename(i)
			if os.path.isdir(i) and stepName not in addedSteps:
				sItem = QListWidgetItem(stepName)
				self.lw_aPipeline.addItem(sItem)
				addedSteps.append(stepName)

		if self.lw_aPipeline.count() > 0:
			self.lw_aPipeline.setCurrentRow(0)
		else:
			self.refreshAFile()


	@err_decorator
	def refreshAFile(self, cur=None, prev=None):
		scenefiles = []

		if self.tw_aHierarchy.currentItem() is not None and self.lw_aPipeline.currentItem() is not None:
			path = os.path.join(self.tw_aHierarchy.currentItem().text(1), "Scenefiles", self.lw_aPipeline.currentItem().text())

			if self.core.useLocalFiles:
				path = path.replace(self.core.localProjectPath, self.core.projectPath)
				lpath = path.replace(self.core.projectPath, self.core.localProjectPath)

			dirContent = []

			if os.path.exists(path):
				for k in os.walk(path):
					dirContent += [os.path.join(path,x) for x in k[2]]
					break

			if self.core.useLocalFiles and os.path.exists(lpath):
				for k in os.walk(lpath):
					dirContent += [os.path.join(lpath,x) for x in k[2]]
					break

			for k in dirContent:
				if self.core.useLocalFiles and k.replace(self.core.localProjectPath, self.core.projectPath) in scenefiles:
					continue
				scenefiles.append(k)

		twSorting = [self.tw_aFiles.horizontalHeader().sortIndicatorSection(), self.tw_aFiles.horizontalHeader().sortIndicatorOrder()]

		model = QStandardItemModel()
		model.setHorizontalHeaderLabels(["", "Version", "Comment", "Date", "User"])

		appfilter = []

		for i in self.appFilters:
			if eval("self.chb_aShow%s.isChecked()" % self.appFilters[i]["shortName"]):
				appfilter += self.appFilters[i]["formats"]
		
		#example filename: Body_mod_v0002_details-added_rfr_.max
		for i in scenefiles:
			row = []
			fname = os.path.basename(i).split(self.core.filenameSeperator)

			if len(fname) == 6 and fname[5] in appfilter:
				publicFile = self.core.useLocalFiles and i.startswith(os.path.join(self.core.projectPath, self.scenes, "Assets"))

				if pVersion == 2:
					item = QStandardItem(unicode("█", "utf-8"))
				else:
					item = QStandardItem("█")
				item.setFont(QFont('SansSerif', 100))
				item.setFlags(~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)

				ext = fname[5]

				colorVals = [128,128,128]
				if ext in self.core.appPlugin.sceneFormats:
					colorVals = self.core.appPlugin.appColor
				else:
					for k in self.core.unloadedAppPlugins.values():
						if ext in k.sceneFormats:
							colorVals = k.appColor

				item.setForeground(QColor(colorVals[0], colorVals[1], colorVals[2]))

				row.append(item)
				item = QStandardItem(fname[2])
				item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
				row.append(item)
				if fname[3] == "nocomment":
					item = QStandardItem("")
				else:
					item = QStandardItem(fname[3])
				item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
				row.append(QStandardItem(item))
				filepath = i
				cdate = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
				cdate = cdate.replace(microsecond = 0)
				cdate = cdate.strftime("%d.%m.%y,  %X")
				item = QStandardItem(str(cdate))
				item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
				item.setData(QDateTime.fromString( cdate, "dd.MM.yy,  hh:mm:ss").addYears(100), 0)
			#	item.setToolTip(cdate)
				row.append(item)
				item = QStandardItem(fname[4])
				item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
				row.append(item)
				item = QStandardItem(i)
				row.append(item)

				if publicFile:
					for k in row[1:]:
						iFont = k.font()
						iFont.setBold(True)
						k.setFont(iFont)
						k.setForeground(self.publicColor)

				model.appendRow(row)

		
		self.tw_aFiles.setModel(model)
		self.tw_aFiles.setColumnHidden(5, True)
		if psVersion == 1:
			self.tw_aFiles.horizontalHeader().setResizeMode(0,QHeaderView.Fixed)
			self.tw_aFiles.horizontalHeader().setResizeMode(2, QHeaderView.Stretch)
		else:
			self.tw_aFiles.horizontalHeader().setSectionResizeMode(0,QHeaderView.Fixed)
			self.tw_aFiles.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

		self.tw_aFiles.resizeColumnsToContents()
		self.tw_aFiles.setColumnWidth(0,10*self.core.uiScaleFactor)
		self.tw_aFiles.setColumnWidth(1,80*self.core.uiScaleFactor)
		self.tw_aFiles.setColumnWidth(3,200*self.core.uiScaleFactor)
		self.tw_aFiles.setColumnWidth(4,100*self.core.uiScaleFactor)
		
		self.tw_aFiles.sortByColumn(twSorting[0], twSorting[1])


	@err_decorator
	def Assetclicked(self, item):
		if item is not None and item.childCount() == 0 and item.text(0) != None:
			self.curAsset = item.text(1)
		else:
			self.curAsset = None

		self.refreshAStep()

		if self.gb_renderings.isVisible() and self.chb_autoUpdate.isChecked():
			self.updateTasks()


	@err_decorator
	def refreshShots(self):
		self.tw_sShot.clear()

		if self.core.useLocalFiles:
			lBasePath = self.sBasePath.replace(self.core.projectPath, self.core.localProjectPath)

		self.refreshOmittedEntities()

		dirs = []
		for i in os.walk(self.sBasePath):
			for k in i[1]:
				dirs.append(os.path.join(i[0], k))
			break

		if self.core.useLocalFiles:
			for i in os.walk(lBasePath):
				for k in i[1]:
					ldir = os.path.join(i[0], k)
					if ldir.replace(self.core.localProjectPath, self.core.projectPath) not in dirs:
						dirs.append(ldir)
				break

		sequences = []
		shots = []
		for path in sorted(dirs):
			val = os.path.basename(path)
			if not val.startswith("_") and val not in self.omittedEntities["Shot"]:
				if "-" in val:
					sname = val.split("-",1)
					seqName = sname[0]
					shotName = sname[1]
				else:
					seqName = "no sequence"
					shotName = val

				if shotName != "":
					shots.append([seqName, shotName, val])

				if seqName not in sequences:
					sequences.append(seqName)

		if "no sequence" in sequences:
			sequences.insert(len(sequences), sequences.pop(sequences.index("no sequence")))

		blockoutSeqs = [x for x in sequences if x.startswith("BLK")]

		for i in blockoutSeqs:
			sequences.insert(len(sequences), sequences.pop(sequences.index(i)))

		for seqName in sequences:
			seqItem = QTreeWidgetItem([seqName, seqName + "-"])
			self.tw_sShot.addTopLevelItem(seqItem)
			if seqName in self.sExpanded:
				seqItem.setExpanded(True)

		for i in shots:
			for k in range(self.tw_sShot.topLevelItemCount()):
				tlItem = self.tw_sShot.topLevelItem(k)
				if tlItem.text(0) == i[0]:
					seqItem = tlItem

			sItem = QTreeWidgetItem([i[1], i[2]])
			seqItem.addChild(sItem)

		if self.tw_sShot.topLevelItemCount() > 0:
			if self.tw_sShot.topLevelItem(0).isExpanded():
				self.tw_sShot.setCurrentItem(self.tw_sShot.topLevelItem(0).child(0))
			else:
				self.tw_sShot.setCurrentItem(self.tw_sShot.topLevelItem(0))
		else:
			self.cursShots = None
			self.refreshsStep()
			self.refreshShotinfo()


	@err_decorator
	def sItemCollapsed(self, item):
		self.sdclick = False
		exp = item.isExpanded()

		if exp:
			if item.text(0) not in self.sExpanded:
				self.sExpanded.append(item.text(0))
		else:
			if item.text(0) in self.sExpanded:
				self.sExpanded.remove(item.text(0))


	@err_decorator
	def refreshsStep(self, cur=None, prev=None):
		model = QStandardItemModel()

		if self.cursShots is not None:
			foldercont = ["","",""]
			for i in os.walk(os.path.join(self.sBasePath, self.cursShots, "Scenefiles")):
				foldercont = i
				break
			for i in sorted(foldercont[1]):
				item = QStandardItem(i)
				model.appendRow(item)

		self.lw_sPipeline.setModel(model)

		selModel = self.lw_sPipeline.selectionModel()
		selModel.currentRowChanged.connect(lambda x, y: self.sPipelineclicked(x))

		if self.lw_sPipeline.model().rowCount() > 0:
			idx = self.lw_sPipeline.model().index(0,0)
			self.lw_sPipeline.selectionModel().setCurrentIndex(idx, QItemSelectionModel.ClearAndSelect)
		else:
			self.cursStep = None
			self.refreshsCat()


	@err_decorator
	def refreshsCat(self):
		model = QStandardItemModel()

		if self.cursStep is not None:
			foldercont = ["","",""]
			for i in os.walk(os.path.join(self.sBasePath, self.cursShots, "Scenefiles", self.cursStep)):
				foldercont = i
				break
			for i in sorted(foldercont[1]):
				item = QStandardItem(i)
				model.appendRow(item)

		self.lw_sCategory.setModel(model)

		selModel = self.lw_sCategory.selectionModel()
		selModel.currentRowChanged.connect(lambda x, y: self.sCatclicked(x))

		if self.lw_sCategory.model().rowCount() > 0:
			idxList = self.lw_sCategory.model().findItems("main")
			if len(idxList) > 0:
				idx = self.lw_sCategory.model().indexFromItem(idxList[0])
			else:
				idxList = self.lw_sCategory.model().findItems("_main")
				if len(idxList) > 0:
					idx = self.lw_sCategory.model().indexFromItem(idxList[0])
				else:
					idx = self.lw_sCategory.model().index(0,0)

			self.lw_sCategory.selectionModel().setCurrentIndex(idx, QItemSelectionModel.ClearAndSelect)
		else:
			self.cursCat = None
			self.refreshSFile()


	@err_decorator
	def refreshSFile(self, parm=None):
		twSorting = [self.tw_sFiles.horizontalHeader().sortIndicatorSection(), self.tw_sFiles.horizontalHeader().sortIndicatorOrder()]

		model = QStandardItemModel()

		model.setHorizontalHeaderLabels(["","Version", "Comment", "Date", "User"])
		#example filename: shot_0010_mod_main_v0002_details-added_rfr_.max

		if self.cursCat is not None:
			foldercont = ["","",""]
			scenefiles = []
			sscenepath = os.path.join(self.sBasePath, self.cursShots, "Scenefiles", self.cursStep, self.cursCat)
			for i in os.walk(sscenepath):
				for k in i[2]:
					scenefiles.append(os.path.join(i[0], k))
				break
			if self.core.useLocalFiles:
				for i in os.walk(sscenepath.replace(self.core.projectPath, self.core.localProjectPath)):
					for k in i[2]:
						fpath = os.path.join(i[0], k)
						if not fpath.replace(self.core.localProjectPath, self.core.projectPath) in scenefiles:
							scenefiles.append(fpath)
					break

			appfilter = []

			for i in self.appFilters:
				if eval("self.chb_sShow%s.isChecked()" % self.appFilters[i]["shortName"]):
					appfilter += self.appFilters[i]["formats"]

			for i in scenefiles:
				row = []
				fname = os.path.basename(i).split(self.core.filenameSeperator)
				tmpScene = False
				try:
					x = int(fname[7][-5:])
					tmpScene = True
				except:
					pass
				if len(fname) == 8 and fname[7] in appfilter and not tmpScene:
					publicFile = self.core.useLocalFiles and i.startswith(os.path.join(self.core.projectPath, self.scenes, "Shots"))

					if pVersion == 2:
						item = QStandardItem(unicode("█", "utf-8"))
					else:
						item = QStandardItem("█")
					item.setFont(QFont('SansSerif', 100))
					item.setFlags(~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)

					ext = fname[7]

					colorVals = [128,128,128]
					if ext in self.core.appPlugin.sceneFormats:
						colorVals = self.core.appPlugin.appColor
					else:
						for k in self.core.unloadedAppPlugins.values():
							if ext in k.sceneFormats:
								colorVals = k.appColor

					item.setForeground(QColor(colorVals[0], colorVals[1], colorVals[2]))

					row.append(item)
					item = QStandardItem(fname[4])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
					if fname[5] == "nocomment":
						item = QStandardItem("")
					else:
						item = QStandardItem(fname[5])
				#	self.tw_sFiles.setItemDelegate(ColorDelegate(self.tw_sFiles))
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
					cdate = datetime.datetime.fromtimestamp(os.path.getmtime(i))
					cdate = cdate.replace(microsecond = 0)
					cdate = cdate.strftime("%d.%m.%y,  %X")
					item = QStandardItem(str(cdate))
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					item.setData(QDateTime.fromString( cdate, "dd.MM.yy,  hh:mm:ss").addYears(100), 0)
				#	item.setToolTip(cdate)
					row.append(item)
					item = QStandardItem(fname[6])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
					item = QStandardItem(i)
					row.append(item)

					if publicFile:
						for k in row[1:]:
							iFont = k.font()
							iFont.setBold(True)
							k.setFont(iFont)
							k.setForeground(self.publicColor)

					model.appendRow(row)

		self.tw_sFiles.setModel(model)
		self.tw_sFiles.setColumnHidden(5, True)
		if psVersion == 1:
			self.tw_sFiles.horizontalHeader().setResizeMode(0,QHeaderView.Fixed)
			self.tw_sFiles.horizontalHeader().setResizeMode(2, QHeaderView.Stretch)
		else:
			self.tw_sFiles.horizontalHeader().setSectionResizeMode(0,QHeaderView.Fixed)
			self.tw_sFiles.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

		self.tw_sFiles.resizeColumnsToContents()
		self.tw_sFiles.setColumnWidth(0,10*self.core.uiScaleFactor)
		self.tw_sFiles.setColumnWidth(1,80*self.core.uiScaleFactor)
		self.tw_sFiles.setColumnWidth(3,200*self.core.uiScaleFactor)
		self.tw_sFiles.setColumnWidth(4,100*self.core.uiScaleFactor)
		self.tw_sFiles.sortByColumn(twSorting[0], twSorting[1])


	@err_decorator
	def sShotclicked(self, item):
		if item is not None and item.text(0) != None and item.text(0) != "no sequence":
			self.cursShots = item.text(1)
		else:
			self.cursShots = None

		self.refreshShotinfo()
		self.refreshsStep()

		if self.gb_renderings.isVisible() and self.chb_autoUpdate.isChecked():
			self.updateTasks()


	@err_decorator
	def sPipelineclicked(self, index):
		if index.data() != None:
			self.cursStep = index.data()
		else:
			self.cursStep = None

		self.refreshsCat()


	@err_decorator
	def sCatclicked(self, index):
		if index.data() != None:
			self.cursCat = index.data()
		else:
			self.cursCat = None

		self.refreshSFile()


	@err_decorator
	def refreshShotinfo(self):
		pmap = None

		if self.cursShots is not None:
			shotFile = os.path.join(os.path.dirname(self.core.prismIni), "Shotinfo", "shotInfo.ini")

			startFrame = "?"
			endFrame = "?"

			if os.path.exists(shotFile):
				sconfig = ConfigParser()
				try:
					sconfig.read(shotFile)
				except:
					warnStr = "Could not read the configuration file for the frameranges:\n%s\n\nYou can try to fix this problem manually.\nYou can also reset this file, which means that the frameranges for all existing shots will be lost." % shotFile
					msg = QMessageBox(QMessageBox.Warning, "Warning", warnStr, QMessageBox.Ok, parent=self.core.messageParent)
					msg.addButton("Reset", QMessageBox.YesRole)
					msg.setFocus()
					action = msg.exec_()

					if action == 0:
						if not sconfig.has_section("shotRanges"):
							sconfig.add_section("shotRanges")

						with open(shotFile, 'w') as inifile:
							sconfig.write(inifile)

				if sconfig.has_option("shotRanges", self.cursShots):
					shotRange = eval(sconfig.get("shotRanges", self.cursShots))
					if type(shotRange) == list and len(shotRange) == 2:
						startFrame = shotRange[0]
						endFrame = shotRange[1]

			if len(self.cursShots.split("-")) == 2 and self.cursShots.endswith("-"):
				rangeText = "Sequence selected"
			else:
				rangeText = "Framerange:	%s - %s" % (startFrame, endFrame)


			imgPath = os.path.join(os.path.dirname(self.core.prismIni), "Shotinfo", "%s_preview.jpg" % self.cursShots)

			if os.path.exists(imgPath):
				pm = self.getImgPMap(imgPath)
				if pm.width() > 0 and pm.height() > 0:
					if (pm.width()/float(pm.height())) > 1.7778:
						pmap = pm.scaledToWidth(self.shotPrvXres)
					else:
						pmap = pm.scaledToHeight(self.shotPrvYres)
		else:
			rangeText = "No shot selected"

		if pmap is None:
			pmap = self.emptypmapPrv

		self.l_framerange.setText(rangeText)
		self.l_shotPreview.setMinimumSize(pmap.width(), pmap.height())
		self.l_shotPreview.setPixmap(pmap)


	@err_decorator
	def editShot(self, shotName=None):
		sequs = []
		for i in range(self.tw_sShot.topLevelItemCount()):
			sName = self.tw_sShot.topLevelItem(i).text(0)
			if sName != "no sequence":
				sequs.append(sName)

		try:
			del sys.modules["EditShot"]
		except:
			pass

		import EditShot
		self.es = EditShot.EditShot(core = self.core, shotName= shotName, sequences=sequs)
		self.core.parentWindow(self.es)
		if shotName is None:
			self.es.setWindowTitle("Create Shot")

		result = self.es.exec_()

		if result != 1 or self.es.shotName is None:
			return

		if shotName is None:
			return

		self.refreshShots()

		if "-" in self.es.shotName:
			sname = self.es.shotName.split("-",1)
			seqName = sname[0]
			shotName = sname[1]
		else:
			seqName = "no sequence"
			shotName = self.es.shotName

		for i in range(self.tw_sShot.topLevelItemCount()):
			sItem = self.tw_sShot.topLevelItem(i)
			if sItem.text(0) == seqName:
				sItem.setExpanded(True)
				for k in range(sItem.childCount()):
					shotItem = sItem.child(k)
					if shotItem.text(0) == shotName:
						self.tw_sShot.setCurrentItem(shotItem)


	@err_decorator
	def createShot(self, shotName):
		self.createShotFolders(shotName, "Shot")

		self.refreshShots()

		if "-" in self.es.shotName:
			sname = self.es.shotName.split("-",1)
			seqName = sname[0]
			shotName = sname[1]
		else:
			seqName = "no sequence"
			shotName = self.es.shotName

		self.core.callback(name="onShotCreated", types=["custom"], args=[self, seqName, shotName])

		for i in range(self.tw_sShot.topLevelItemCount()):
			sItem = self.tw_sShot.topLevelItem(i)
			if sItem.text(0) == seqName:
				sItem.setExpanded(True)
				for k in range(sItem.childCount()):
					shotItem = sItem.child(k)
					if shotItem.text(0) == shotName:
						self.tw_sShot.setCurrentItem(shotItem)


	@err_decorator
	def refreshFCat(self):

		model = QStandardItemModel()
		hpath = ""
		for i in self.fhierarchy:
			hpath += i + os.sep

		hpath = hpath[6:]

		self.fpath = os.path.join(self.core.projectPath, self.core.getConfig('paths', "assets", configPath=self.core.prismIni), hpath)

		foldercont = ["","",""]
		for i in os.walk(self.fpath):
			foldercont = i
			break
		dirs = foldercont[1]

		for idx, val in enumerate(dirs):
			item = QStandardItem(val)
			if self.fbottom and val == self.fclickedon:
				current = idx
			model.appendRow(item)

		self.lw_fCategory.setModel(model)

		if self.fbottom:
			index = model.createIndex(current,0)
			self.lw_fCategory.setCurrentIndex(index)
			for i in os.walk(os.path.join(self.fpath, self.fclickedon)):
				foldercont = i
				break

		twSorting = [self.tw_fFiles.horizontalHeader().sortIndicatorSection(), self.tw_fFiles.horizontalHeader().sortIndicatorOrder()]
		model = QStandardItemModel()

		model.setHorizontalHeaderLabels(["Filename", "Date"])

		for i in foldercont[2]:
			row = []
			item = QStandardItem(i)
			row.append(item)
			filepath = os.path.join(foldercont[0], i)
			cdate = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
			cdate = cdate.replace(microsecond = 0)
			cdate = cdate.strftime("%d.%m.%y,  %X")
			item = QStandardItem()
			item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
			item.setData(QDateTime.fromString( cdate, "dd.MM.yy,  hh:mm:ss").addYears(100), 0)
		#	item.setToolTip(cdate)
			row.append(item)
			item = QStandardItem(os.path.join(foldercont[0], i))
			row.append(item)

			model.appendRow(row)

		self.tw_fFiles.setModel(model)
		self.tw_fFiles.setColumnHidden(2, True)
		self.tw_fFiles.resizeColumnsToContents()
		self.tw_fFiles.setColumnWidth(0,self.tw_fFiles.columnWidth(0)+1)
		self.tw_fFiles.sortByColumn(twSorting[0], twSorting[1])


		for i in range(len(self.fhierarchy)):
			self.fhbuttons[i].setHidden(False)
			self.fhbuttons[i].setText(self.fhierarchy[i])

		for i in range(10, len(self.fhierarchy), -1):
			self.fhbuttons[i-1].setHidden(True)


	@err_decorator
	def setRecent(self):
		model = QStandardItemModel()

		model.setHorizontalHeaderLabels(["","Name", "Step", "Version", "Comment", "Date", "User", "Filepath"])
		#example filename: Body_mod_v0002_details-added_rfr_.max
		#example filename: shot_0010_mod_main_v0002_details-added_rfr_.max
		rSection = "recent_files_" + self.core.projectName

		rcData = {}

		rcData["recent01"] = [rSection, "recent01"]
		rcData["recent02"] = [rSection, "recent02"]
		rcData["recent03"] = [rSection, "recent03"]
		rcData["recent04"] = [rSection, "recent04"]
		rcData["recent05"] = [rSection, "recent05"]
		rcData["recent06"] = [rSection, "recent06"]
		rcData["recent07"] = [rSection, "recent07"]
		rcData["recent08"] = [rSection, "recent08"]
		rcData["recent09"] = [rSection, "recent09"]
		rcData["recent10"] = [rSection, "recent10"]

		rcData = self.core.getConfig(data=rcData)
		recentfiles = [rcData[x] for x in sorted(rcData)]

		for i in recentfiles:
			if i is None:
				continue

			row = []
			fname = os.path.basename(i).split(self.core.filenameSeperator)
			if os.path.exists(i):
				if pVersion == 2:
					item = QStandardItem(unicode("█", "utf-8"))
				else:
					item = QStandardItem("█")
				item.setFont(QFont('SansSerif', 100))
				item.setFlags(~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)

				ext = fname[-1]

				colorVals = [128,128,128]
				if ext in self.core.appPlugin.sceneFormats:
					colorVals = self.core.appPlugin.appColor
				else:
					for k in self.core.unloadedAppPlugins.values():
						if ext in k.sceneFormats:
							colorVals = k.appColor

				item.setForeground(QColor(colorVals[0], colorVals[1], colorVals[2]))

				row.append(item)
				if len(fname) == 6:
					item = QStandardItem(fname[0])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
					item = QStandardItem(fname[1])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
					item = QStandardItem(fname[2])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
					if fname[3] == "nocomment":
						item = QStandardItem("")
					else:
						item = QStandardItem(fname[3])
					row.append(item)
					cdate = datetime.datetime.fromtimestamp(os.path.getmtime(i))
					cdate = cdate.replace(microsecond = 0)
					cdate = cdate.strftime("%d.%m.%y,  %X")
					item = QStandardItem(str(cdate))
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					item.setData(QDateTime.fromString( cdate, "dd.MM.yy,  hh:mm:ss").addYears(100), 0)
				#	item.setToolTip(cdate)
					row.append(item)
					item = QStandardItem(fname[4])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
				elif len(fname) == 8:
					item = QStandardItem(fname[1])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
					item = QStandardItem(fname[2])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
					item = QStandardItem(fname[4])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
					if fname[5] == "nocomment":
						item = QStandardItem("")
					else:
						item = QStandardItem(fname[5])
					row.append(item)
					cdate = datetime.datetime.fromtimestamp(os.path.getmtime(i))
					cdate = cdate.replace(microsecond = 0)
					cdate = cdate.strftime("%d.%m.%y,  %X")
					item = QStandardItem(str(cdate))
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					item.setData(QDateTime.fromString( cdate, "dd.MM.yy,  hh:mm:ss").addYears(100), 0)
				#	item.setToolTip(cdate)
					row.append(item)
					item = QStandardItem(fname[6])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
				else:
					continue

				item = QStandardItem(i)
				item.setToolTip(i)
				row.append(item)

				model.appendRow(row)

		self.tw_recent.setModel(model)
		self.tw_recent.resizeColumnsToContents()
		self.tw_recent.setColumnWidth(0,10*self.core.uiScaleFactor)
		self.tw_recent.setColumnWidth(2,40*self.core.uiScaleFactor)
		self.tw_recent.setColumnWidth(3,60*self.core.uiScaleFactor)
		self.tw_recent.setColumnWidth(6,50*self.core.uiScaleFactor)

		if psVersion == 1:
			self.tw_recent.horizontalHeader().setResizeMode(0,QHeaderView.Fixed)
		else:
			self.tw_recent.horizontalHeader().setSectionResizeMode(0,QHeaderView.Fixed)


	@err_decorator
	def refreshCurrent(self):
		if self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Assets":
			self.refreshAFile()
		elif self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Shots":
			self.refreshSFile()
		elif self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Files":
			self.refreshFCat()
		elif self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Recent":
			self.setRecent()


	@err_decorator
	def FCatclicked(self, index):
		if index.row() != -1:
			for i in os.walk(self.fpath + index.data()):
				foldercont = i
				break
			if len(foldercont[1]) != 0 and len(self.fhierarchy) < 10:
				self.dclick = False
				self.fhierarchy.append(index.data())
				self.fbottom = False
			else:
				self.fbottom = True
			self.fclickedon = index.data()
		self.refreshFCat()


	@err_decorator
	def filehiera(self, hieranum):
		self.fhierarchy = self.fhierarchy[:hieranum]
		self.fbottom = False
		self.refreshFCat()


	@err_decorator
	def triggerOpen(self, checked=False):
		self.core.setConfig("globals", "showonstartup", str(checked))


	@err_decorator
	def triggerUpdates(self, checked=False):
		self.core.setConfig("globals", "checkversions", str(checked))


	@err_decorator
	def triggerFrameranges(self, checked=False):
		self.core.setConfig("globals", "checkframeranges", str(checked))


	@err_decorator
	def triggerCloseLoad(self, checked=False):
		self.core.setConfig('browser', self.closeParm, str(checked))


	@err_decorator
	def triggerAutoplay(self, checked=False):
		self.core.setConfig('browser', "autoplaypreview", str(checked))

		if hasattr(self, "tl"):
			if checked and self.tl.state() == QTimeLine.Paused:
				self.tl.setPaused(False)
			elif not checked and self.tl.state() == QTimeLine.Running:
				self.tl.setPaused(True)
		else:
			self.tlPaused = not checked


	@err_decorator
	def triggerAssets(self, checked=False):
		if checked:
			self.tbw_browser.insertTab(self.tabOrder.index("Assets"), self.t_assets, "Assets")
			if self.tbw_browser.count() == 1:
				self.tbw_browser.setVisible(True)
		else:
			self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_assets))
			if self.tbw_browser.count() == 0:
				self.tbw_browser.setVisible(False)


	@err_decorator
	def triggerShots(self, checked=False):
		if checked:
			self.tbw_browser.insertTab(self.tabOrder.index("Shots"), self.t_shots, "Shots")
			if self.tbw_browser.count() == 1:
				self.tbw_browser.setVisible(True)
		else:
			self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_shots))
			if self.tbw_browser.count() == 0:
				self.tbw_browser.setVisible(False)


	@err_decorator
	def triggerFiles(self, checked=False):
		if checked:
			self.tbw_browser.insertTab(self.tabOrder.index("Files"), self.t_files, "Files")
			if self.tbw_browser.count() == 1:
				self.tbw_browser.setVisible(True)
		else:
			self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_files))
			if self.tbw_browser.count() == 0:
				self.tbw_browser.setVisible(False)



	@err_decorator
	def triggerRecent(self, checked=False):
		if checked:
			self.tbw_browser.insertTab(self.tabOrder.index("Recent"), self.t_recent, "Recent")
			if self.tbw_browser.count() == 1:
				self.tbw_browser.setVisible(True)
		else:
			self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_recent))
			if self.tbw_browser.count() == 0:
				self.tbw_browser.setVisible(False)


	@err_decorator
	def triggerRenderings(self, checked=False):
		self.gb_renderings.setVisible(checked)


	@err_decorator
	def createCatWin(self, tab, name):
		self.newItem = CreateItem.CreateItem(core=self.core, showType=tab=="ah")

		self.newItem.setModal(True)
		self.core.parentWindow(self.newItem)
		self.newItem.e_item.setFocus()
		self.newItem.setWindowTitle("Create " + name)
		self.newItem.l_item.setText(name + " Name:")
		self.newItem.show()
		self.newItem.buttonBox.accepted.connect(lambda: self.createCat(tab))
		if tab == "ah":
			self.core.callback(name="onAssetDlgOpen", types=["custom"], args=[self, self.newItem])


	@err_decorator
	def createCat(self, tab):
		self.activateWindow()
		self.itemName = self.newItem.e_item.text()

		if tab == "ah":
			curItem = self.tw_aHierarchy.currentItem()
			if curItem is None:
				path = self.aBasePath
			else:
				path = self.tw_aHierarchy.currentItem().text(1)
			refresh = self.refreshAHierarchy
			uielement = self.tw_aHierarchy
		elif tab == "ss":
			path = self.sBasePath
			refresh = self.refreshShots
			uielement = self.tw_sShot
			self.cursShots = self.itemName
		elif tab == "sc":
			path = os.path.join(self.sBasePath, self.cursShots, "Scenefiles", self.cursStep)
			refresh = self.refreshsCat
			uielement = self.lw_sCategory
			self.cursCat = self.itemName
		elif tab == "f":
			path = self.fpath
			hiera = self.fhierarchy
			clickedon = self.fclickedon
			refresh = self.refreshFCat
			uielement = self.lw_fCategory
			self.fbottom = True

		if tab == "f" and self.newItem.windowTitle() == "Create Sub-Category":
			if len(hiera) < 10:
				try:
					os.makedirs(os.path.join(path, clickedon, self.itemName))
				except:
					QMessageBox.warning(self.core.messageParent,"Warning", "The directory could not be created")
					return None

				self.fhierarchy.append(self.fclickedon)
		elif tab == "ah" and self.newItem.rb_asset.isChecked():
			assetPath = os.path.join(path, self.itemName)
			self.createShotFolders(assetPath, "Asset")
			self.core.callback(name="onAssetCreated", types=["custom"], args=[self, self.itemName, path, self.newItem])
			for i in self.core.prjManagers.values():
				i.assetCreated(self, self.newItem, assetPath)
		else:
			dirName = os.path.join(path, self.itemName)
			if not os.path.exists(dirName):
				try:
					os.makedirs(dirName)
				except:
					QMessageBox.warning(self.core.messageParent,"Warning", "The directory could not be created")
					return None
			else:
				QMessageBox.warning(self.core.messageParent,"Warning", "The directory already exists")

		if tab == "f":
			self.fclickedon = self.itemName

		refresh()
		if tab == "ah":
			self.navigateToCurrent(path=os.path.join(path, self.itemName))
		else:
			for i in range(uielement.model().rowCount()):
				if uielement.model().index(i,0).data() == self.itemName:
					uielement.selectionModel().setCurrentIndex(uielement.model().index(i,0), QItemSelectionModel.ClearAndSelect)


	@err_decorator
	def createShotFolders(self, fname, ftype):
		if ftype == "Asset":
			basePath = ""
		else:
			basePath = self.sBasePath

		sFolders = []
		sFolders.append(os.path.join(basePath, fname, "Scenefiles"))
		sFolders.append(os.path.join(basePath, fname, "Export"))
		sFolders.append(os.path.join(basePath, fname, "Playblasts"))
		sFolders.append(os.path.join(basePath, fname, "Rendering", "3dRender"))
		sFolders.append(os.path.join(basePath, fname, "Rendering", "2dRender"))

		if os.path.exists(os.path.dirname(sFolders[0])):
			QMessageBox.warning(self.core.messageParent,"Warning", "The %s %s already exists" % (ftype, fname))
			return

		for i in sFolders:
			if not os.path.exists(i):
				os.makedirs(i)


	@err_decorator
	def createStep(self, tab):
		if tab == "a":
			basePath = os.path.join(self.tw_aHierarchy.currentItem().text(1), "Scenefiles")
		elif tab == "s":
			basePath = os.path.join(self.sBasePath, self.cursShots, "Scenefiles")
		else:
			return

		steps = ast.literal_eval(self.core.getConfig('globals', "pipeline_steps", configPath=self.core.prismIni))
		if type(steps) != dict:
			steps = {}

		steps = {validSteps : steps[validSteps] for validSteps in steps if not os.path.exists(os.path.join(basePath, validSteps))}
		steps = self.getStep(steps, tab)
		if steps != False:
			createdDirs = []
			for i in steps[0]:
				if tab == "a":
					dstname = os.path.join(basePath, i)
				elif tab == "s":
					existingSteps = ast.literal_eval(self.core.getConfig('globals', "pipeline_steps", configPath=self.core.prismIni))
					if steps[1]:
						catName = existingSteps[i]
					else:
						catName = ""

					dstname = os.path.join(basePath, i, catName)
				if not os.path.exists(dstname):
					try:
						os.makedirs(dstname)
						createdDirs.append(i)
					except:
						QMessageBox.warning(self.core.messageParent,"Warning", ("The directory %s could not be created" % i))
			if len(createdDirs) != 0:
				if tab == "a":
					self.refreshAHierarchy()
					self.navigateToCurrent(path=dstname)
				elif tab == "s":
					self.cursStep = createdDirs[0]
					self.refreshsStep()
					for i in range(self.lw_sPipeline.model().rowCount()):
						if self.lw_sPipeline.model().index(i,0).data() == createdDirs[0]:
							self.lw_sPipeline.selectionModel().setCurrentIndex( self.lw_sPipeline.model().index(i,0) , QItemSelectionModel.ClearAndSelect)


	@err_decorator
	def openFFile(self):
		if self.fbottom:
			self.core.openFolder(self.fpath + self.fclickedon)
		else:
			self.core.openFolder(self.fpath)


	@err_decorator
	def copyToGlobal(self, localPath):
		dstPath = localPath.replace(self.core.localProjectPath, self.core.projectPath)

		if os.path.isdir(localPath):
			if os.path.exists(dstPath):
				for i in os.walk(dstPath):
					if i[2] != []:
						QMessageBox.information(self.core.messageParent, "Copy to global", "Found existing files in the global directory. Copy to global was canceled.")
						return

				shutil.rmtree(dstPath)

			shutil.copytree(localPath, dstPath)
			
			if hasattr(self, "vidPrw") and not self.vidPrw.closed:
				for i in range(6):
					self.vidPrw.close()
					time.sleep(0.5)
					if self.vidPrw.closed:
						break

			try:
				shutil.rmtree(localPath)
			except:
				QMessageBox.warning(self.core.messageParent, "Copy to global", "Could not delete the local file. Probably it is used by another process.")

			curTab = self.tbw_browser.tabText(self.tbw_browser.currentIndex())
			curData = [curTab, self.cursShots, self.curRTask, self.curRVersion, self.curRLayer]
			self.updateTasks()
			self.showRender(curData[0], curData[1], curData[2], curData[3].replace(" (local)", ""), curData[4])
		else:
			if not os.path.exists(os.path.dirname(dstPath)):
				os.makedirs(os.path.dirname(dstPath))

			self.core.copySceneFile(localPath, dstPath)

			if self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Assets":
				self.refreshAFile()
			elif self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Shots":
				self.refreshSFile()


	@err_decorator
	def omitEntity(self, eType, ePath):
		msgText = "Are you sure you want to omit %s \"%s\"?\n\nThis will make the %s be ignored by Prism, but all scenefiles and renderings remain on the hard drive." % (eType.lower(), ePath, eType.lower())
		if psVersion == 1:
			flags = QMessageBox.StandardButton.Yes
			flags |= QMessageBox.StandardButton.No
			result = QMessageBox.question(self.core.messageParent, "Warning", msgText, flags)
		else:
			result = QMessageBox.question(self.core.messageParent, "Warning", msgText)

		if str(result).endswith(".Yes"):
			omitConfig = os.path.join(os.path.dirname(self.core.prismIni), "Configs", "omits.ini")

			if not os.path.exists(os.path.dirname(omitConfig)):
				os.makedirs(os.path.dirname(omitConfig))

			if not os.path.exists(omitConfig):
				open(omitConfig, "w").close()

			oconfig = ConfigParser()
			oconfig.read(omitConfig)

			if not oconfig.has_section(eType):
				oconfig.add_section(eType)

			num = len(oconfig.options(eType))
			oconfig.set(eType, str(num), ePath)

			with open(omitConfig, 'w') as inifile:
				oconfig.write(inifile)

			if eType == "Asset":
				self.refreshAHierarchy()
			elif eType == "Shot":
				self.refreshShots()


	@err_decorator
	def refreshOmittedEntities(self):
		self.omittedEntities = {"Asset":[], "Shot":[]}
		omitPath = os.path.join(os.path.dirname(self.core.prismIni), "Configs", "omits.ini")
		if os.path.exists(omitPath):
			oconfig = ConfigParser()
			oconfig.read(omitPath)

			if oconfig.has_section("Shot"):
				self.omittedEntities["Shot"] = [x[1] for x in oconfig.items("Shot")]

			if oconfig.has_section("Asset"):
				self.omittedEntities["Asset"] = [x[1] for x in oconfig.items("Asset")]


	@err_decorator
	def navigateToCurrent(self, path=None):
		if path is None:
			fileName = self.core.getCurrentFileName()
			fileNameData = os.path.basename(fileName).split(self.core.filenameSeperator)
		else:
			fileName = path
			fileNameData = []

		if os.path.join(self.core.projectPath, self.scenes) in fileName or (self.core.useLocalFiles and os.path.join(self.core.localProjectPath, self.scenes) in fileName):
			if len(fileNameData) == 6 or self.aBasePath in fileName or (self.core.useLocalFiles and (self.aBasePath.replace(self.core.projectPath, self.core.localProjectPath) in fileName)):
				itemPath = fileName.replace(self.core.projectPath, "")
				if self.core.useLocalFiles:
					itemPath = itemPath.replace(self.core.localProjectPath, "")
				if not itemPath.startswith(os.sep):
					itemPath = os.sep + itemPath
				itemPath = itemPath.replace(os.sep + os.path.join( self.scenes, os.path.join("Assets", "")), "")
				hierarchy = itemPath.split(os.sep)
				hierarchy = [x for x in hierarchy if x != ""]
				hItem = self.tw_aHierarchy.findItems(hierarchy[0], Qt.MatchExactly, 0)
				if len(hItem) == 0:
					return
				hItem = hItem[-1]

				endIdx = None
				if len(hierarchy) > 1:
					hItem.setExpanded(True)
					if hItem.text(1) not in self.aExpanded:
						self.aExpanded.append(hItem.text(1))

					for idx, i in enumerate((hierarchy[1:])):
						for k in range(hItem.childCount()-1,-1,-1):
							if hItem.child(k).text(0) == i:
								hItem = hItem.child(k)
								if len(hierarchy) > (idx+2):
									hItem.setExpanded(True)
									if hItem.text(1) not in self.aExpanded:
										self.aExpanded.append(hItem.text(1))
								break
						else:
							endIdx = idx+1
							break

				self.tw_aHierarchy.setCurrentItem(hItem)

				if endIdx is not None and hierarchy[endIdx] == "Scenefiles":
					endIdx += 1

				if endIdx is not None and endIdx+2 == len(hierarchy):
					stepName = hierarchy[endIdx]
					fItems = self.lw_aPipeline.findItems(stepName, Qt.MatchExactly)
					if len(fItems) > 0:
						self.lw_aPipeline.setCurrentItem(fItems[0])
						if len(hierarchy) > (endIdx + 1):
							for i in range(self.tw_aFiles.model().rowCount()):
								if fileName == self.tw_aFiles.model().index(i,5).data():
									idx = self.tw_aFiles.model().index(i,0)
									self.tw_aFiles.selectRow(idx.row())
									break

			elif (len(fileNameData) == 8 or self.sBasePath in fileName or (self.core.useLocalFiles and self.sBasePath.replace(self.core.projectPath, self.core.localProjectPath) in fileName)) and self.tw_sShot.topLevelItemCount() > 0:
				fnamePath = fileName.replace(self.sBasePath, "")
				if self.core.useLocalFiles:
					lbase = self.sBasePath.replace(self.core.projectPath, self.core.localProjectPath)
					fnamePath = fnamePath.replace(lbase, "")

				fnameData = fnamePath.replace(self.sBasePath, "").split(os.sep)
				fnameData = [x for x in fnameData if x != ""]

				shotName = stepName = catName = ""
				if len(fnameData) > 0:
					shotName = fnameData[0]
				if len(fnameData) > 2:
					stepName = fnameData[2]
				if len(fnameData) > 3:
					catName = fnameData[3]

				if "-" in shotName:
					sname = shotName.split("-",1)
					seqName = sname[0]
					shotName = sname[1]
				else:
					seqName = "no sequence"
					shotName = shotName

				for i in range(self.tw_sShot.topLevelItemCount()):
					sItem = self.tw_sShot.topLevelItem(i)
					if sItem.text(0) == seqName:
						if shotName == "":
							self.tw_sShot.setCurrentItem(sItem)
						else:
							sItem.setExpanded(True)
							for k in range(sItem.childCount()):
								shotItem = sItem.child(k)
								if shotItem.text(0) == shotName:
									self.tw_sShot.setCurrentItem(shotItem)
									break

				if stepName != "":
					for i in range(self.lw_sPipeline.model().rowCount()):
						if stepName == self.lw_sPipeline.model().index(i,0).data():
							idx = self.lw_sPipeline.model().index(i,0)
							self.lw_sPipeline.selectionModel().setCurrentIndex(idx, QItemSelectionModel.ClearAndSelect)
							break
					if catName != "":
						for i in range(self.lw_sCategory.model().rowCount()):
							if catName == self.lw_sCategory.model().index(i,0).data():
								idx = self.lw_sCategory.model().index(i,0)
								self.lw_sCategory.selectionModel().setCurrentIndex(idx, QItemSelectionModel.ClearAndSelect)
								break

						for i in range(self.tw_sFiles.model().rowCount()):
							if fileName == self.tw_sFiles.model().index(i,5).data():
								idx = self.tw_sFiles.model().index(i,0)
								self.tw_sFiles.selectRow(idx.row())
								break


	@err_decorator
	def updateChanged(self, state):
		if state:
			self.updateTasks()


	@err_decorator
	def refreshRender(self):
		curTab = self.tbw_browser.tabText(self.tbw_browser.currentIndex())
		curData = [curTab, self.cursShots, self.curRTask, self.curRVersion, self.curRLayer]
		self.updateTasks()
		self.showRender(curData[0], curData[1], curData[2], curData[3], curData[4])


	@err_decorator
	def updateTasks(self):
		self.renderRefreshEnabled = False

		self.curRTask = ""
		self.lw_task.clear()

		foldercont = []
		self.renderBasePath = None


		if self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Assets":
			if self.tw_aHierarchy.currentItem() is not None and self.tw_aHierarchy.currentItem().text(2) == "Asset":
				self.renderBasePath = self.tw_aHierarchy.currentItem().text(1)
		elif self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Shots" and self.cursShots is not None:
			self.renderBasePath = os.path.join(self.core.projectPath, self.scenes, "Shots", self.cursShots)

		if self.renderBasePath is not None:
			for i in os.walk(os.path.join(self.renderBasePath, "Rendering", "3dRender")):
				foldercont += i[1]
				break

			for i in os.walk(os.path.join(self.renderBasePath, "Rendering", "2dRender")):
				for k in sorted(i[1]):
					foldercont.append(k +" (2d)")
				break

			for i in os.walk(os.path.join(self.renderBasePath, "Rendering", "external")):
				for k in sorted(i[1]):
					foldercont.append(k +" (external)")
				break

			for i in os.walk(os.path.join(self.renderBasePath, "Playblasts")):
				for k in sorted(i[1]):
					foldercont.append(k +" (playblast)")
				break

			if self.core.useLocalFiles:
				for i in os.walk(os.path.join(self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath), "Rendering", "3dRender")):
					for k in sorted(i[1]):
						tname = k + " (local)"
						if tname not in foldercont and k not in foldercont:
							foldercont.append(tname)
					break

				for i in os.walk(os.path.join(self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath), "Rendering", "2dRender")):
					for k in sorted(i[1]):
						tname = k + " (2d)"
						if tname not in foldercont:
							foldercont.append(tname)
					break

				for i in os.walk(os.path.join(self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath), "Playblasts")):
					for k in sorted(i[1]):
						tname = k + " (playblast)"
						if tname not in foldercont:
							foldercont.append(tname)
					break

			for i in foldercont:
				self.lw_task.addItem(i)

		mIdx = self.lw_task.findItems("main", (Qt.MatchExactly & Qt.MatchCaseSensitive))
		if len(mIdx) > 0:
			self.lw_task.setCurrentItem(mIdx[0])
			self.curRTask = "main"
		elif self.lw_task.count() > 0:
			self.lw_task.setCurrentRow(0)

		self.renderRefreshEnabled = True


		self.updateVersions()


	@err_decorator
	def updateVersions(self):
		if not self.renderRefreshEnabled:
			return

		self.curRVersion = ""
		self.lw_version.clear()

		if len(self.lw_task.selectedItems()) == 1:
			foldercont = self.getRenderVersions(self.curRTask)
			foldercont.sort()
			for i in reversed(foldercont):
				item = QListWidgetItem(i)
				if self.curRTask.endswith(" (playblast)"):
					versionInfoPath = os.path.join(self.renderBasePath, "Playblasts", self.curRTask.replace(" (playblast)", ""), i, "versioninfo.ini")
				elif self.curRTask.endswith(" (2d)"):
					versionInfoPath = os.path.join(self.renderBasePath, "Rendering", "2dRender", self.curRTask.replace(" (2d)", ""), i, "versioninfo.ini")
				elif self.curRTask.endswith(" (external)"):
					versionInfoPath = os.path.join(self.renderBasePath, "Rendering", "external", self.curRTask.replace(" (external)", ""), i, "versioninfo.ini")
				else:
					versionInfoPath = os.path.join(self.renderBasePath, "Rendering", "3dRender", self.curRTask, i, "versioninfo.ini")

				if self.core.useLocalFiles and i.endswith(" (local)"):
					versionInfoPath = versionInfoPath.replace(self.core.projectPath, self.core.localProjectPath)

				if os.path.exists(versionInfoPath):
					vConfig = ConfigParser()
					vConfig.read(versionInfoPath)

					prjMngNames = [[x, x.lower() + "-url"] for x in self.core.prjManagers]
					for i in prjMngNames:
						if vConfig.has_option("information", i[1]):
							f = item.font()
							f.setBold(True)
							item.setFont(f)
							break

				self.lw_version.addItem(item)

		self.renderRefreshEnabled = False
		self.lw_version.setCurrentRow(0)
		self.renderRefreshEnabled = True

		if self.lw_version.currentItem() is not None:
			self.curRVersion = self.lw_version.currentItem().text()

		self.updateLayers()


	@err_decorator
	def updateLayers(self):
		if not self.renderRefreshEnabled:
			return

		self.curRLayer = ""
		self.cb_layer.clear()

		if len(self.lw_version.selectedItems()) == 1:
			foldercont = self.getRenderLayers(self.curRTask, self.curRVersion)
			for i in foldercont:
				self.cb_layer.addItem(i)

		bIdx = self.cb_layer.findText("beauty")
		if bIdx != -1:
			self.cb_layer.setCurrentIndex(bIdx)
		else:
			bIdx = self.cb_layer.findText("rgba")
			if bIdx != -1:
				self.cb_layer.setCurrentIndex(bIdx)
			else:
				self.cb_layer.setCurrentIndex(0)

		if self.cb_layer.currentIndex() != -1:
			self.curRLayer = self.cb_layer.currentText()
		else:
			self.updatePreview()


	@err_decorator
	def getRenderVersions(self, task):
		foldercont = []
		if self.renderBasePath is None:
			return foldercont

		if task.endswith(" (playblast)"):
			for i in os.walk(os.path.join(self.renderBasePath, "Playblasts", task.replace(" (playblast)", ""))):
				foldercont = i[1]
				break

			if self.core.useLocalFiles:
				for i in os.walk(os.path.join(self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath), "Playblasts", task.replace(" (playblast)", ""))):
					for k in i[1]:
						foldercont.append(k +" (local)")
					break

		elif task.endswith(" (2d)"):
			for i in os.walk(os.path.join(self.renderBasePath, "Rendering", "2dRender", task.replace(" (2d)", ""))):
				foldercont = i[1]
				break

			if self.core.useLocalFiles:
				for i in os.walk(os.path.join(self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath), "Rendering", "2dRender", task.replace(" (2d)", ""))):
					for k in i[1]:
						foldercont.append(k +" (local)")
					break
		elif task.endswith(" (external)"):
			for i in os.walk(os.path.join(self.renderBasePath, "Rendering", "external", task.replace(" (external)", ""))):
				foldercont = i[1]
				break
		else:
			if self.core.useLocalFiles:
				for i in os.walk(os.path.join(self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath), "Rendering", "3dRender", task.replace(" (local)", ""))):
					for k in i[1]:
						foldercont.append(k +" (local)")
					break

			for i in os.walk(os.path.join(self.renderBasePath, "Rendering", "3dRender", task)):
				foldercont += i[1]
				break

		return foldercont


	@err_decorator
	def getRenderLayers(self, task, version):
		foldercont = []
		if self.renderBasePath is None:
			return foldercont

		if " (playblast)" not in task and " (2d)" not in task and " (external)" not in task:
			if version.endswith(" (local)"):
				rPath = os.path.join(self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath), "Rendering", "3dRender", task.replace(" (local)", ""), version.replace(" (local)", ""))
			else:
				rPath = os.path.join(self.renderBasePath, "Rendering", "3dRender", task, version)

			for i in os.walk(rPath):
				foldercont = i[1]
				break

		return foldercont


	@err_decorator
	def updatePreview(self):
		if hasattr(self, "tl"):
			if self.tl.state() != QTimeLine.NotRunning:
				if self.tl.state() == QTimeLine.Running:
					self.tlPaused = False
				elif self.tl.state() == QTimeLine.Paused:
					self.tlPaused = True
				self.tl.stop()
		else:
			self.tlPaused = not self.actionAutoplay.isChecked()

		self.sl_preview.setValue(0)
		self.prevCurImg = 0
		self.curImg = 0
		self.seq = []
		self.prvIsSequence = False
		self.b_addRV.setEnabled(False)
		if len(self.compareStates) == 0:
			self.b_compareRV.setEnabled(False)
			self.b_combineVersions.setEnabled(False)

		QPixmapCache.clear()

		if self.curRLayer != "":
			if self.curRVersion.endswith(" (local)"):
				rPath = os.path.join(self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath), "Rendering", "3dRender", self.curRTask.replace(" (local)", ""), self.curRVersion.replace(" (local)", ""), self.curRLayer)
			else:
				rPath = os.path.join(self.renderBasePath, "Rendering", "3dRender", self.curRTask, self.curRVersion, self.curRLayer)

			for i in os.walk(rPath):
				foldercont = i
				break
		elif self.curRTask.endswith(" (2d)"):
			if self.curRVersion.endswith(" (local)"):
				base = self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath)
			else:
				base = self.renderBasePath
			for i in os.walk(os.path.join(base, "Rendering", "2dRender", self.curRTask.replace(" (2d)", ""), self.curRVersion.replace(" (local)", ""))):
				foldercont = i
				break
		elif self.curRTask.endswith(" (playblast)"):
			if self.curRVersion.endswith(" (local)"):
				base = self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath)
			else:
				base = self.renderBasePath
			for i in os.walk(os.path.join(base, "Playblasts", self.curRTask.replace(" (playblast)", ""), self.curRVersion.replace(" (local)", ""))):
				foldercont = i
				break
		elif self.curRTask.endswith(" (external)"):
			redirectFile = os.path.join(self.renderBasePath, "Rendering", "external", self.curRTask.replace(" (external)", ""), self.curRVersion, "REDIRECT.txt")
			
			if os.path.exists(redirectFile):
				with open(redirectFile, "r") as rfile:
					rpath = rfile.read()

				if os.path.splitext(rpath)[1] == "":
					for i in os.walk(rpath):
						foldercont = i
						break
				else:
					files = []
					if os.path.exists(rpath):
						files = [os.path.basename(rpath)]
					foldercont = [os.path.dirname(rpath), [], files]

		if len(self.lw_task.selectedItems()) > 1 or len(self.lw_version.selectedItems()) > 1:
			self.l_info.setText("Multiple items selected")
			self.l_info.setToolTip("")
			self.l_date.setText("")
			self.b_addRV.setEnabled(True)
			self.b_compareRV.setEnabled(True)
			self.b_combineVersions.setEnabled(True)
		elif "foldercont" in locals():
			self.basepath = foldercont[0]
			base = None
			for i in sorted(foldercont[2]):
				if os.path.splitext(i)[1] in [".jpg", ".jpeg", ".JPG", ".png", ".tif", ".tiff", ".exr", ".dpx", ".mp4", ".mov"]:
					base = i
					break

			if base is not None:
				baseName, extension = os.path.splitext(base)
				for i in sorted(foldercont[2]):
					if i.startswith(baseName[:-4]) and (i.endswith(extension)):
						self.seq.append(i)

				if len(self.seq) > 1 and extension not in [".mp4", ".mov"]:
					self.prvIsSequence = True
					try:
						self.pstart = int(baseName[-4:])
					except:
						self.pstart = "?"

					try:
						self.pend = int(os.path.splitext(self.seq[len(self.seq)-1])[0][-4:])
					except:
						self.pend = "?"

				else:
					self.prvIsSequence = False
					self.seq = []
					for i in foldercont[2]:
						if os.path.splitext(i)[1] in [".jpg", ".jpeg", ".JPG", ".png", ".tif", ".tiff", ".exr", ".dpx", ".mp4", ".mov"]:
							self.seq.append(i)

				if not (self.curRTask == "" or self.curRVersion == "" or len(self.seq) == 0):
					self.b_addRV.setEnabled(True)

				self.pduration = len(self.seq)
				imgPath = str(os.path.join(foldercont[0], base))
				if os.path.exists(imgPath) and self.pduration == 1 and os.path.splitext(imgPath)[1] in [".mp4", ".mov"]:
					if os.stat(imgPath).st_size == 0:
						self.vidPrw = "Error"
					else:
						try:
							self.vidPrw = imageio.get_reader(imgPath,  'ffmpeg')
						except:
							self.vidPrw = "Error"

					self.updatePrvInfo(imgPath, vidReader=self.vidPrw)
				else:
					self.updatePrvInfo(imgPath)

				if os.path.exists(imgPath):
					self.tl = QTimeLine(self.pduration*40, self)
					self.tl.setFrameRange(0, self.pduration-1)
					self.tl.setEasingCurve(QEasingCurve.Linear)
					self.tl.setLoopCount(0)
					self.tl.frameChanged.connect(self.changeImg)
					QPixmapCache.setCacheLimit(2097151)
					self.curImg = 0
					self.tl.start()


					if self.tlPaused:
						self.tl.setPaused(True)
						self.changeImg()
					elif self.pduration < 3:
						self.changeImg()

					return True
			else:
				self.updatePrvInfo()
		else:
			self.updatePrvInfo()

		self.l_preview.setPixmap(self.emptypmap)
		self.sl_preview.setEnabled(False)


	@err_decorator
	def updatePrvInfo(self, prvFile="", vidReader=None):
		if not os.path.exists(prvFile):
			self.l_info.setText("No image found")
			self.l_info.setToolTip("")
			self.l_date.setText("")
			self.l_preview.setToolTip("")
			return

		self.pwidth, self.pheight = self.getMediaResolution(prvFile, vidReader=vidReader, setDuration=True)

		self.pformat = "*" + os.path.splitext(prvFile)[1]

		cdate = datetime.datetime.fromtimestamp(os.path.getmtime(prvFile))
		cdate = cdate.replace(microsecond = 0)
		pdate = cdate.strftime("%d.%m.%y,  %X")

		self.sl_preview.setEnabled(True)

		if self.pduration == 1:
			frStr = "frame"
		else:
			frStr = "frames"

		if self.prvIsSequence:
			infoStr = "%sx%s   %s   %s-%s (%s %s)" % (self.pwidth, self.pheight, self.pformat, self.pstart, self.pend, self.pduration, frStr)
		elif len(self.seq) > 1:
			infoStr = "%s files %sx%s   %s   %s" % (self.pduration, self.pwidth, self.pheight, self.pformat, os.path.basename(prvFile))
		elif os.path.splitext(self.seq[0])[1] in [".mp4", ".mov"]:
			if self.pwidth == "?":
				duration = "?"
				frStr = "frames"
			else:
				duration = self.pduration

			infoStr = "%sx%s   %s   %s %s" % (self.pwidth, self.pheight, self.seq[0], duration, frStr)
		else:
			infoStr = "%sx%s   %s" % (self.pwidth, self.pheight, os.path.basename(prvFile))
			self.sl_preview.setEnabled(False)

		self.l_info.setText(infoStr)
		self.l_info.setToolTip(infoStr)
		self.l_date.setText(pdate)
		self.l_preview.setToolTip("Drag to drop the media to RV\nCtrl+Drag to drop the media to Nuke")


	@err_decorator
	def getMediaResolution(self, prvFile, vidReader=None, setDuration=False):
		pwidth = 0
		pheight = 0

		if os.path.splitext(prvFile)[1] in [".jpg", ".jpeg", ".JPG", ".png", ".tif", ".tiff"]:
			size = self.getImgPMap(prvFile).size()
			pwidth = size.width()
			pheight = size.height()
		elif os.path.splitext(prvFile)[1] in [".exr", ".dpx"]:
			pwidth = pheight = "?"
			if self.oiioLoaded:
				imgSpecs = oiio.ImageBuf(str(prvFile)).spec()
				pwidth = imgSpecs.full_width
				pheight = imgSpecs.full_height

			elif self.wandLoaded:
				try:
					with wand.image.Image(filename=prvFile) as img:
						pwidth = img.width
						pheight = img.height
				except:
					pass

		elif os.path.splitext(prvFile)[1] in [".mp4", ".mov"]:
			if vidReader is None:
				if os.stat(prvFile).st_size == 0:
					vidReader = "Error"
				else:
					try:
						vidReader = imageio.get_reader(prvFile,  'ffmpeg')
					except:
						vidReader = "Error"

			if vidReader == "Error":
				pwidth = pheight = "?"
				if setDuration:
					self.pduration = 1
			else:
				pwidth = vidReader._meta["size"][0]
				pheight = vidReader._meta["size"][1]
				if len(self.seq) == 1 and setDuration:
					self.pduration = vidReader._meta["nframes"]

		if pwidth == 0 and pheight == 0:
			pwidth = pheight = "?"

		return pwidth, pheight

	@err_decorator
	def createPMap(self, resx, resy):
		if resx == 300:
			imgFile = os.path.join(self.core.projectPath, "00_Pipeline", "Fallbacks", "noFileBig.jpg")
		else:
			imgFile = os.path.join(self.core.projectPath, "00_Pipeline", "Fallbacks", "noFileSmall.jpg")


		return self.getImgPMap(imgFile)


	@err_decorator
	def getImgPMap(self, path):
		if platform.system() == "Windows":
			return QPixmap(path)
		else:
			try:
				im = Image.open(path)
				im = im.convert("RGBA")
				r,g,b,a = im.split()
				im = Image.merge("RGBA", (b,g,r,a))
				data = im.tobytes("raw", "RGBA")

				qimg = QImage(data, im.size[0], im.size[1], QImage.Format_ARGB32)

				return QPixmap(qimg)
			except:
				return QPixmap(path)


	@err_decorator
	def savePMap(self, pmap, path):
		if platform.system() == "Windows":
			pmap.save(path, "JPG")
		else:
			try:
				img = pmap.toImage()
				buf = QBuffer()
				buf.open(QIODevice.ReadWrite)
				img.save(buf, "PNG")

				strio = StringIO()
				strio.write(buf.data())
				buf.close()
				strio.seek(0)
				pimg = Image.open(strio)
				pimg.save(path)
			except:
				pmap.save(path, "JPG")


	@err_decorator
	def changeImg(self, frame = 0):
		pmsmall = QPixmap()
		if not QPixmapCache.find(("Frame" + str(self.curImg)), pmsmall):
			if len(self.seq) == 1 and os.path.splitext(self.seq[0])[1] in [".mp4", ".mov"]:
				curFile = self.seq[0]
			else:
				curFile = self.seq[self.curImg]
			fileName = os.path.join(self.basepath, curFile)

			if os.path.splitext(curFile)[1] in [".jpg", ".jpeg", ".JPG", ".png", ".tif", ".tiff"]:
				pm = self.getImgPMap(fileName)

				if pm.width() == 0 or pm.height() == 0:
					pmsmall = self.getImgPMap(os.path.join(self.core.projectPath, "00_Pipeline", "Fallbacks", "%s.jpg" % os.path.splitext(curFile)[1][1:].lower()))
				elif (pm.width()/float(pm.height())) > 1.7778:
					pmsmall = pm.scaledToWidth(self.renderResX)
				else:
					pmsmall = pm.scaledToHeight(self.renderResY)
			elif os.path.splitext(curFile)[1] in [".exr", ".dpx"]:
				try:
					qimg = QImage(self.renderResX, self.renderResY, QImage.Format_RGB16)

					if self.oiioLoaded:
						imgSrc = oiio.ImageBuf(str(fileName))
						rgbImgSrc = oiio.ImageBuf()
						oiio.ImageBufAlgo.channels(rgbImgSrc, imgSrc, (0,1,2))
						imgWidth = rgbImgSrc.spec().full_width
						imgHeight = rgbImgSrc.spec().full_height
						xOffset = 0
						yOffset = 0
						if (imgWidth/float(imgHeight)) > 1.7778:
							newImgWidth = self.renderResX
							newImgHeight = self.renderResX/float(imgWidth)*imgHeight
						else:
							newImgHeight = self.renderResY
							newImgWidth = self.renderResY/float(imgHeight)*imgWidth
						imgDst = oiio.ImageBuf(oiio.ImageSpec(int(newImgWidth),int(newImgHeight),3, oiio.UINT8))
						oiio.ImageBufAlgo.resample(imgDst, rgbImgSrc)
						sRGBimg = oiio.ImageBuf()
						oiio.ImageBufAlgo.pow(sRGBimg, imgDst, (1.0/2.2, 1.0/2.2, 1.0/2.2))
						bckImg = oiio.ImageBuf(oiio.ImageSpec(int(newImgWidth), int(newImgHeight), 3, oiio.UINT8))
						oiio.ImageBufAlgo.fill (bckImg, (0.5,0.5,0.5))
						oiio.ImageBufAlgo.paste(bckImg, xOffset,yOffset,0,0, sRGBimg)
						qimg = QImage(int(newImgWidth), int(newImgHeight), QImage.Format_RGB16)
						for i in range(int(newImgWidth)):
							for k in range(int(newImgHeight)):
								rgb = qRgb(bckImg.getpixel(i,k)[0]*255, bckImg.getpixel(i,k)[1]*255, bckImg.getpixel(i,k)[2]*255)
								qimg.setPixel(i,k,rgb)
						pmsmall = QPixmap.fromImage(qimg)

					elif self.wandLoaded:
						with wand.image.Image(filename=fileName) as img :
							imgWidth, imgHeight = [img.width, img.height]
							img.depth = 8
							imgArr = numpy.fromstring(img.make_blob('RGB'), dtype='uint{}'.format(img.depth)).reshape(imgHeight, imgWidth, 3)

						qimg = QImage(imgArr,imgWidth, imgHeight, QImage.Format_RGB888)
						pm = QPixmap.fromImage(qimg)
						if (pm.width()/float(pm.height())) > 1.7778:
							pmsmall = pm.scaledToWidth(self.renderResX)
						else:
							pmsmall = pm.scaledToHeight(self.renderResY)

					else:
						raise RuntimeError ("no image loader available")
				except:
					pmsmall = self.getImgPMap(os.path.join(self.core.projectPath, "00_Pipeline", "Fallbacks", "%s.jpg" % os.path.splitext(curFile)[1][1:].lower()))
			elif os.path.splitext(curFile)[1] in [".mp4", ".mov"]:
				try:
					if len(self.seq) > 1:
						imgNum = 0
						vidFile = imageio.get_reader(fileName,  'ffmpeg')
					else:
						imgNum = self.curImg
						vidFile = self.vidPrw

					image = vidFile.get_data(imgNum)
					qimg = QImage(image, vidFile._meta["size"][0], vidFile._meta["size"][1], QImage.Format_RGB888)
					pm = QPixmap.fromImage(qimg)
					if (pm.width()/float(pm.height())) > 1.7778:
						pmsmall = pm.scaledToWidth(self.renderResX)
					else:
						pmsmall = pm.scaledToHeight(self.renderResY)
				except:
					pmsmall = self.getImgPMap(os.path.join(self.core.projectPath, "00_Pipeline", "Fallbacks", "%s.jpg" % os.path.splitext(curFile)[1][1:].lower()))
			else:
				return False

			QPixmapCache.insert(("Frame" + str(self.curImg)), pmsmall)

		if not self.prvIsSequence and len(self.seq) > 1:
			curFile = self.seq[self.curImg]
			fileName = os.path.join(self.basepath, curFile)
			self.updatePrvInfo(fileName)

		self.l_preview.setPixmap(pmsmall)
		if self.tl.state() == QTimeLine.Running:
			self.sl_preview.setValue(int(100 * (self.curImg/float(self.pduration))))
		self.curImg += 1
		if self.curImg == self.pduration:
			self.curImg = 0


	@err_decorator
	def taskClicked(self):
		sItems = self.lw_task.selectedItems()
		if len(sItems) == 1 and sItems[0].text() != self.curRTask:
			self.curRTask = sItems[0].text()
		else:
			self.curRTask = ""
		
		self.updateVersions()


	@err_decorator
	def versionClicked(self):
		sItems = self.lw_version.selectedItems()
		if len(sItems) == 1 and sItems[0].text() != self.curRVersion:
			self.curRVersion = sItems[0].text()
		else:
			self.curRVersion = ""

		self.updateLayers()


	@err_decorator
	def layerChanged(self, layer):
		layertext = self.cb_layer.itemText(layer)
		if layertext != "" and layer != self.curRLayer:
			self.curRLayer = layertext
			self.updatePreview()


	@err_decorator
	def sliderChanged(self, val):
		if self.seq != []:
			if val != (self.prevCurImg+1) or self.tl.state() != QTimeLine.Running:
				self.prevCurImg = val
				self.curImg = int(val/99.0*(self.pduration-1))

				if self.tl.state() != QTimeLine.Running:
					self.changeImg()
			else:
				self.prevCurImg = val


	@err_decorator
	def saveClicked(self, num):
		curTab = self.tbw_browser.tabText(self.tbw_browser.currentIndex())
		if curTab not in ["Assets", "Shots"]:
			return False

		btn = eval("self.b_saveRender" + str(num))
		dataVar = eval("self.saveRender" + str(num))

		if dataVar == []:
			dataVar = [curTab, self.cursShots, self.curRTask, self.curRVersion, self.curRLayer]
			self.core.appPlugin.setSaveColor(self, btn)

			if curTab == "Assets":
				btnText = self.curRTask
			else:
				btnText = self.cursShots

			btn.setText(btnText)
		else:
			self.showRender(dataVar[0], dataVar[1], dataVar[2], dataVar[3], dataVar[4])

		exec("self.saveRender%s = dataVar" % num)


	@err_decorator
	def saverClicked(self, num):
		btn = eval("self.b_saveRender" + str(num))
		dataVar = eval("self.saveRender" + str(num))

		btn.setText("--free--")
		self.core.appPlugin.clearSaveColor(self, btn)
		exec("self.saveRender%s = []" % num)


	@err_decorator
	def getVersionInfoPath(self):
		if self.curRVersion.endswith(" (local)"):
			base = self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath)
		else:
			base = self.renderBasePath

		if self.curRTask.endswith(" (playblast)"):
			path = os.path.join(base, "Playblasts", self.curRTask.replace(" (playblast)", ""), self.curRVersion.replace(" (local)", ""), "versioninfo.ini")
		elif self.curRTask.endswith(" (2d)"):
			path = os.path.join(base, "Rendering", "2dRender", self.curRTask.replace(" (2d)", ""), self.curRVersion.replace(" (local)", ""), "versioninfo.ini")
		elif self.curRTask.endswith(" (external)"):
			path = ""
		else:
			path = os.path.join(base, "Rendering", "3dRender", self.curRTask.replace(" (local)", ""), self.curRVersion.replace(" (local)", ""), "versioninfo.ini")

		return path


	@err_decorator
	def showVersionInfo(self, item=None):
		vInfo = "No information is saved with this version."

		path = self.getVersionInfoPath()

		if os.path.exists(path):
			vConfig = ConfigParser()
			vConfig.read(path)

			vInfo = []
			for i in vConfig.options("information"):
				i = i[0].upper() + i[1:]
				vInfo.append([i, vConfig.get("information", i)])


		if type(vInfo) == str or len(vInfo) == 0:
			QMessageBox.information(self.core.messageParent, "Versioninfo", vInfo)
			return

		infoDlg = QDialog()
		lay_info = QGridLayout()

		infoDlg.setWindowTitle("Versioninfo %s %s:" % (self.curRTask, self.curRVersion))
		for idx, val in enumerate(vInfo):
			l_infoName = QLabel(val[0] + ":\t")
			l_info = QLabel(val[1])
			lay_info.addWidget(l_infoName)
			lay_info.addWidget(l_info, idx, 1)

		lay_info.addItem(QSpacerItem(10,10, QSizePolicy.Minimum, QSizePolicy.Expanding))
		lay_info.addItem(QSpacerItem(10,10, QSizePolicy.Expanding, QSizePolicy.Minimum), 0,2)

		sa_info = QScrollArea()

		lay_info.setContentsMargins(10,10,10,10)
		w_info = QWidget()
		w_info.setLayout(lay_info)
		sa_info.setWidget(w_info)
		sa_info.setWidgetResizable(True)
	
		bb_info = QDialogButtonBox()

		bb_info.addButton("Ok", QDialogButtonBox.AcceptRole)

		bb_info.accepted.connect(infoDlg.accept)

		bLayout = QVBoxLayout()
		bLayout.addWidget(sa_info)
		bLayout.addWidget(bb_info)
		infoDlg.setLayout(bLayout)
		infoDlg.setParent(self.core.messageParent, Qt.Window)
		infoDlg.resize(900*self.core.uiScaleFactor,200*self.core.uiScaleFactor)

		action = infoDlg.exec_()


	@err_decorator
	def showDependencies(self):
		path = self.getVersionInfoPath()

		if not os.path.exists(path):
			QMessageBox.warning(self.core.messageParent, "Warning", "No dependency information was saved with this version.")
			return

		self.core.dependencyViewer(path)


	@err_decorator
	def showRender(self, tab, shot, task, version, layer):
		if tab != self.tbw_browser.tabText(self.tbw_browser.currentIndex()):
			for i in range(self.tbw_browser.count()):
				if self.tbw_browser.tabText(i) == tab:
					idx = i
					break
			else:
				return False

			self.tbw_browser.setCurrentIndex(idx)

		if tab == "Shots" and self.tw_sShot.currentIndex().data() != shot:
			for i in range(self.tw_sShot.model().rowCount()):
				if self.tw_sShot.model().index(i,0).data() == shot:
					self.tw_sShot.selectionModel().setCurrentIndex( self.tw_sShot.model().index(i,0) , QItemSelectionModel.ClearAndSelect)
					break

		self.updateTasks()
		if len(self.lw_task.findItems(task, (Qt.MatchExactly & Qt.MatchCaseSensitive))) != 0:
			self.lw_task.setCurrentItem(self.lw_task.findItems(task, (Qt.MatchExactly & Qt.MatchCaseSensitive))[0])
			if len(self.lw_version.findItems(version, (Qt.MatchExactly & Qt.MatchCaseSensitive))) != 0:
				self.lw_version.setCurrentItem(self.lw_version.findItems(version, (Qt.MatchExactly & Qt.MatchCaseSensitive))[0])
				if self.cb_layer.findText(layer) != -1:
					self.cb_layer.setCurrentIndex(self.cb_layer.findText(layer))
					self.updatePreview()


	@err_decorator
	def previewClk(self, event):
		if self.seq != [] and event.button() == Qt.LeftButton:
			if self.tl.state() == QTimeLine.Paused and not self.openRV:
				self.tl.setPaused(False)
			else:
				if self.tl.state() == QTimeLine.Running:
					self.tl.setPaused(True)
				self.openRV = False
		self.l_preview.clickEvent(event)


	@err_decorator
	def previewDclk(self, event):
		if self.seq != [] and event.button() == Qt.LeftButton:
			self.openRV = True
			self.compare(current=True)
		self.l_preview.dclickEvent(event)


	@err_decorator
	def rclPreview(self, pos):
		if self.curRVersion == "" or ( self.curRLayer == "" and not (self.curRTask.endswith(" (playblast)") or self.curRTask.endswith(" (2d)") or self.curRTask.endswith(" (external)")) ):
			return False

		rcmenu = QMenu()

		if self.curRVersion.endswith(" (local)"):
			base = self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath)
		else:
			base = self.renderBasePath

		if self.curRTask.endswith(" (playblast)"):
			path = os.path.join(base, "Playblasts", self.curRTask.replace(" (playblast)", ""), self.curRVersion.replace(" (local)", ""), self.curRLayer)
		elif self.curRTask.endswith(" (2d)"):
			path = os.path.join(base, "Rendering", "2dRender", self.curRTask.replace(" (2d)", ""), self.curRVersion.replace(" (local)", ""), self.curRLayer)
		elif self.curRTask.endswith(" (external)"):
			redirectFile = os.path.join(self.renderBasePath, "Rendering", "external", self.curRTask.replace(" (external)", ""), self.curRVersion, "REDIRECT.txt")
			path = ""
			if os.path.exists(redirectFile):
				with open(redirectFile, "r") as rfile:
					path = rfile.read()

				if os.path.isfile(path):
					path = os.path.dirname(path)
		else:
			path = os.path.join(base, "Rendering", "3dRender", self.curRTask.replace(" (local)", ""), self.curRVersion.replace(" (local)", ""), self.curRLayer)


		if len(self.seq) > 0:
			playMenu = QMenu("Play in")

			if self.rv is not None:
				pAct = QAction("RV", self)
				pAct.triggered.connect(lambda: self.compare(current=True, prog="RV"))
				playMenu.addAction(pAct)

			if self.djv is not None:
				pAct = QAction("DJV", self)
				pAct.triggered.connect(lambda: self.compare(current=True, prog="DJV"))
				playMenu.addAction(pAct)

			if self.vlc is not None:
				pAct = QAction("VLC", self)
				pAct.triggered.connect(lambda: self.compare(current=True, prog="VLC"))
				playMenu.addAction(pAct)

				if self.pformat == "*.exr":
					pAct.setEnabled(False)

			pAct = QAction("Default", self)
			pAct.triggered.connect(lambda: self.compare(current=True, prog="default"))
			playMenu.addAction(pAct)
			
			self.core.appPlugin.setRCStyle(self, playMenu)

			rcmenu.addMenu(playMenu)

		for i in self.core.prjManagers.values():
			pubAct = i.pbBrowser_getPublishMenu(self)
			if pubAct is not None:
				rcmenu.addAction(pubAct)

		exp = QAction("Open in Explorer", self)
		exp.triggered.connect(lambda: self.core.openFolder(path))
		rcmenu.addAction(exp)

		copAct = QAction("Copy path", self)
		copAct.triggered.connect(lambda: self.core.copyToClipboard(path))
		rcmenu.addAction(copAct)

		if len(self.seq) == 1 or self.prvIsSequence:
			cvtMenu = QMenu("Convert")
			qtAct = QAction("jpg", self)
			qtAct.triggered.connect(lambda: self.convertImgs(".jpg"))
			cvtMenu.addAction(qtAct)
			qtAct = QAction("png", self)
			qtAct.triggered.connect(lambda: self.convertImgs(".png"))
			cvtMenu.addAction(qtAct)
			qtAct = QAction("mp4", self)
			qtAct.triggered.connect(lambda: self.convertImgs(".mp4"))
			cvtMenu.addAction(qtAct)
			rcmenu.addMenu(cvtMenu)
			self.core.appPlugin.setRCStyle(self, cvtMenu)

		if self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Shots" and len(self.seq) > 0:
			prvAct = QAction("Set as shotpreview", self)
			prvAct.triggered.connect(self.setPreview)
			rcmenu.addAction(prvAct)

		if len(self.seq) > 0 and not self.curRVersion.endswith(" (local)") and self.core.getConfig('paths', "dailies", configPath=self.core.prismIni) is not None:
			dliAct = QAction("Send to dailies", self)
			dliAct.triggered.connect(self.sendToDailies)
			rcmenu.addAction(dliAct)

		if self.core.appPlugin.appType == "2d" and len(self.seq) > 0:
			impAct = QAction("Import images...", self)
			impAct.triggered.connect(lambda: self.core.appPlugin.importImages(self))
			rcmenu.addAction(impAct)

		self.core.appPlugin.setRCStyle(self, rcmenu)
		rcmenu.exec_(self.l_preview.mapToGlobal(pos))




	@err_decorator
	def setPreview(self):
		prvPath = os.path.join(os.path.dirname(self.core.prismIni), "Shotinfo", "%s_preview.jpg" % self.cursShots)

		if not os.path.exists(os.path.dirname(prvPath)):
			os.makedirs(os.path.dirname(prvPath))

		pm = self.l_preview.pixmap()
		if (pm.width()/float(pm.height())) > 1.7778:
			pmap = pm.scaledToWidth(self.shotPrvXres)
		else:
			pmap = pm.scaledToHeight(self.shotPrvYres)

		self.savePMap(pmap, prvPath)

		self.refreshShotinfo()


	@err_decorator
	def sendToDailies(self):
		dailiesName = self.core.getConfig('paths', "dailies", configPath=self.core.prismIni)

		curDate = time.strftime("%Y_%m_%d", time.localtime())

		dailiesFolder = os.path.join(self.core.projectPath, dailiesName, curDate, self.core.getConfig("globals", "UserName"))
		if not os.path.exists(dailiesFolder):
			os.makedirs(dailiesFolder)

		prvData = self.seq[0].split(self.core.filenameSeperator)

		refName = ""

		if self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Assets":
			refName += prvData[0] + self.core.filenameSeperator
		elif self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Shots":
			refName += prvData[0] + self.core.filenameSeperator + prvData[1] + self.core.filenameSeperator

		refName += self.curRTask + self.core.filenameSeperator + self.curRVersion
		if self.curRLayer != "":
			refName += self.core.filenameSeperator + self.curRLayer

		sourcePath = os.path.join(self.basepath, self.seq[0])

		if platform.system() == "Windows":
			folderLinkName = refName + self.core.filenameSeperator + "Folder.lnk"
			refName += ".lnk"

			seqLnk = os.path.join(dailiesFolder, refName)
			folderLnk = os.path.join(dailiesFolder, folderLinkName)

			self.core.createShortcut(seqLnk, vTarget=sourcePath, args='', vWorkingDir='', vIcon='')
			self.core.createShortcut(folderLnk, vTarget=self.basepath, args='', vWorkingDir='', vIcon='')
		else:
			slinkPath = os.path.join(dailiesFolder, refName + "_Folder")
			if os.path.exists(slinkPath):
				try:
					os.remove(slinkPath)
				except:
					QMessageBox.warning(self.core.messageParent, "Dailies", "An existing reference in the dailies folder couldn't be replaced.")
					return

			os.symlink(self.basepath, slinkPath)

		self.core.copyToClipboard(dailiesFolder)

		QMessageBox.information(self.core.messageParent, "Dailies", "The version was sent to the current dailies folder. (path in clipboard)")


	@err_decorator
	def sliderDrag(self, event):
		custEvent = QMouseEvent(QEvent.MouseButtonPress, event.pos(), Qt.MidButton, Qt.MidButton, Qt.NoModifier)
		self.sl_preview.origMousePressEvent(custEvent)


	@err_decorator
	def sliderClk(self):
		if hasattr(self, "tl") and self.tl.state() == QTimeLine.Running:
			self.slStop = True
			self.tl.setPaused(True)
		else:
			self.slStop = False


	@err_decorator
	def sliderRls(self):
		if self.slStop:
			self.tl.setPaused(False)


	@err_decorator
	def rclList(self, pos, lw):
		if lw.itemAt(pos) is not None:
			itemName = lw.itemAt(pos).text()
		else:
			itemName = ""

		if self.renderBasePath is None:
			return False

		if lw == self.lw_task:
			if itemName.endswith(" (local)"):
				path = os.path.join(self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath), "Rendering", "3dRender", itemName.replace(" (local)", ""))
			elif itemName.endswith(" (2d)"):
				path = os.path.join(self.renderBasePath, "Rendering", "2dRender", itemName.replace(" (2d)", ""))
				if not os.path.exists(path) and self.core.useLocalFiles:
					path = os.path.join(self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath), "Rendering", "2dRender", itemName.replace(" (2d)", ""))
			elif itemName.endswith(" (playblast)"):
				path = os.path.join(self.renderBasePath, "Playblasts", itemName.replace(" (playblast)", ""))
				if not os.path.exists(path) and self.core.useLocalFiles:
					path = os.path.join(self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath), "Playblasts", itemName.replace(" (playblast)", ""))
			elif itemName.endswith(" (external)"):
				path = os.path.join(self.renderBasePath, "Rendering", "external", itemName.replace(" (external)", ""))
			else:
				path = os.path.join(self.renderBasePath, "Rendering", "3dRender", itemName)
		elif lw == self.lw_version:
			if itemName.endswith(" (local)"):
				base = self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath)
			else:
				base = self.renderBasePath
			path = os.path.join(base, "Rendering", "3dRender", self.curRTask.replace(" (playblast)", "").replace(" (2d)", "").replace(" (local)", ""), itemName.replace(" (local)", ""))

			if self.curRTask.endswith(" (playblast)"):
				path = path.replace(os.path.join("Rendering", "3dRender"), "Playblasts")
			elif self.curRTask.endswith(" (2d)"):
				path = path.replace(os.path.join("Rendering", "3dRender"), os.path.join("Rendering", "2dRender"))
			elif self.curRTask.endswith(" (external)"):
				redirectFile = os.path.join(self.renderBasePath, "Rendering", "external", self.curRTask.replace(" (external)", ""), self.curRVersion, "REDIRECT.txt")
				path = ""
				if os.path.exists(redirectFile):
					with open(redirectFile, "r") as rfile:
						path = rfile.read()

					if os.path.isfile(path):
						path = os.path.dirname(path)

		rcmenu = QMenu()

		add = QAction("Add current to compare", self)
		add.triggered.connect(self.addCompare)
		if self.rv is not None and ((self.curRTask != "" and self.curRVersion != "" and len(self.seq) > 0) or len(self.lw_task.selectedItems()) > 1 or len(self.lw_version.selectedItems()) > 1):
			rcmenu.addAction(add)

		if lw == self.lw_task and self.renderBasePath != self.aBasePath:
			exAct = QAction("Create external task", self)
			exAct.triggered.connect(self.createExternalTask)
			rcmenu.addAction(exAct)

		if lw == self.lw_version:
			infAct = QAction("Show version info", self)
			infAct.triggered.connect(self.showVersionInfo)
			rcmenu.addAction(infAct)

			depAct = QAction("Show dependencies", self)
			depAct.triggered.connect(self.showDependencies)
			rcmenu.addAction(depAct)
			
			if self.curRTask.endswith(" (external)"):
				nvAct = QAction("Create new version", self)
				nvAct.triggered.connect(self.newExVersion)
				rcmenu.addAction(nvAct)

		if os.path.exists(path):
			opAct = QAction("Open in Explorer", self)
			opAct.triggered.connect(lambda: self.core.openFolder(path))
			rcmenu.addAction(opAct)

			copAct = QAction("Copy path", self)
			copAct.triggered.connect(lambda: self.core.copyToClipboard(path))
			rcmenu.addAction(copAct)

		if lw == self.lw_version and itemName.endswith(" (local)"):
			glbAct = QAction("Move to global", self)
			glbAct.triggered.connect(lambda: self.copyToGlobal(path))
			rcmenu.addAction(glbAct)

		if rcmenu.isEmpty():
			return False

		self.core.appPlugin.setRCStyle(self, rcmenu)
		rcmenu.exec_((lw.viewport()).mapToGlobal(pos))


	@err_decorator
	def createExternalTask(self, data={}):
		if data == {}:
			try:
				del sys.modules["ExternalTask"]
			except:
				pass

			import ExternalTask
			self.ep = ExternalTask.ExternalTask(core = self.core)
			result = self.ep.exec_()

			if result == 1:
				taskName = self.ep.e_taskName.text()
				versionName = self.ep.e_versionName.text()
				targetPath = self.ep.e_taskPath.text()
			else:
				return

		else:
			taskName = data["taskName"]
			versionName = data["versionName"]
			targetPath = data["targetPath"]

		tPath = os.path.join(self.renderBasePath, "Rendering", "external", taskName, versionName)
		if not os.path.exists(tPath):
			os.makedirs(tPath)

		redirectFile = os.path.join(tPath, "REDIRECT.txt")
		with open(redirectFile, "w") as rfile:
			rfile.write(targetPath)

		curTab = self.tbw_browser.tabText(self.tbw_browser.currentIndex())
		curData = [curTab, self.cursShots, taskName + " (external)", versionName, ""]
		self.showRender(curData[0], curData[1], curData[2], curData[3], curData[4])


	@err_decorator
	def newExVersion(self):
		vPath = os.path.join(self.renderBasePath, "Rendering", "external", self.curRTask.replace(" (external)", ""))
		for i in os.walk(vPath):
			dirs = i[1]
			break
			
		highversion = 0
		cHighVersion = ""
		for i in dirs:
			fname = i.split(self.core.filenameSeperator)

			try:
				version = int(i[1:])
			except:
				continue

			if version > highversion:
				highversion = version
				cHighVersion = i
					
		newVersion = "v" + format(highversion + 1, '04')

		curLoc = ""
		rdPath = os.path.join(vPath, cHighVersion, "REDIRECT.txt")
		if os.path.exists(rdPath):
			with open(rdPath, "r") as rdFile:
				curLoc = rdFile.read()

		try:
			del sys.modules["ExternalTask"]
		except:
			pass

		import ExternalTask
		self.ep = ExternalTask.ExternalTask(core = self.core)
		self.ep.e_taskName.setText(self.curRTask.replace(" (external)", ""))
		self.ep.w_taskName.setEnabled(False)
		self.ep.e_taskPath.setText(curLoc)
		self.ep.e_versionName.setText(newVersion)
		self.ep.enableOk(curLoc, self.ep.e_taskPath)
		self.ep.setWindowTitle("Create new version")


		result = self.ep.exec_()

		if result == 1:
			vPath = os.path.join(self.renderBasePath, "Rendering", "external", self.curRTask.replace(" (external)", ""), self.ep.e_versionName.text())
			if not os.path.exists(vPath):
				os.makedirs(vPath)

			redirectFile = os.path.join(vPath, "REDIRECT.txt")
			with open(redirectFile, "w") as rfile:
				rfile.write(self.ep.e_taskPath.text())

			curTab = self.tbw_browser.tabText(self.tbw_browser.currentIndex())
			curData = [curTab, self.cursShots, self.curRTask, self.ep.e_versionName.text(), ""]
			self.showRender(curData[0], curData[1], curData[2], curData[3], curData[4])


	@err_decorator
	def rclCompare(self, pos):
		rcmenu = QMenu()

		add = QAction("Add current", self)
		add.triggered.connect(self.addCompare)
		if self.rv is not None and ((self.curRTask != "" and self.curRVersion != "" and len(self.seq) > 0) or len(self.lw_task.selectedItems()) > 1 or len(self.lw_version.selectedItems()) > 1):
			rcmenu.addAction(add)
		com = QAction("Compare", self)
		com.triggered.connect(self.compare)
		if self.lw_compare.count() > 0:
			rcmenu.addAction(com)
		delc = QAction("Remove", self)
		delc.triggered.connect(self.removeCompare)
		if len(self.lw_compare.selectedItems()) > 0:
			rcmenu.addAction(delc)
		clear = QAction("Clear", self)
		clear.triggered.connect(self.clearCompare)
		if self.lw_compare.count() > 0:
			rcmenu.addAction(clear)

		self.core.appPlugin.setRCStyle(self, rcmenu)

		if not rcmenu.isEmpty():
			rcmenu.exec_((self.lw_compare.viewport()).mapToGlobal(pos))


	@err_decorator
	def getCurRenders(self):
		renders = []
		sTasks = self.lw_task.selectedItems()
		sVersions = self.lw_version.selectedItems()

		if len(sTasks) > 1:
			for i in sTasks:
				render = {"task":i.text(), "version":"", "layer":""}
				versions = self.getRenderVersions(i.text())

				if len(versions) > 0:
					versions.sort()
					versions = versions[::-1]

					render["version"] = versions[0]
					layers = self.getRenderLayers(i.text(), versions[0])

					if len(layers) > 0:
						if "beauty" in layers:
							render["layer"] = "beauty"
						elif "rgba" in layers:
							render["layer"] = "rgba"
						else:
							render["layer"] = layers[0]

				renders.append(render)

		elif len(sVersions) > 1:
			for i in sVersions:
				render = {"task":self.curRTask, "version":i.text(), "layer":""}
				layers = self.getRenderLayers(self.curRTask, i.text())

				if len(layers) > 0:
					if "beauty" in layers:
						render["layer"] = "beauty"
					elif "rgba" in layers:
						render["layer"] = "rgba"
					else:
						render["layer"] = layers[0]

				renders.append(render)

		else:
			renders.append({"task":self.curRTask, "version":self.curRVersion, "layer":self.curRLayer})

		paths = []

		for i in renders:
			if i["layer"] != "":
				if i["version"].endswith(" (local)"):
					paths.append(os.path.join(self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath), "Rendering", "3dRender", i["task"].replace(" (local)", ""), i["version"].replace(" (local)", ""), i["layer"]))
				else:
					paths.append(os.path.join(self.renderBasePath, "Rendering", "3dRender", i["task"], i["version"], i["layer"]))
			elif i["task"].endswith(" (2d)"):
				if i["version"].endswith(" (local)"):
					base = self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath)
				else:
					base = self.renderBasePath
				paths.append(os.path.join(base, "Rendering", "2dRender", i["task"].replace(" (2d)", ""), i["version"].replace(" (local)", "")))
			elif i["task"].endswith(" (external)"):
				redirectFile = os.path.join(self.renderBasePath, "Rendering", "external", i["task"].replace(" (external)", ""), i["version"], "REDIRECT.txt")
				if os.path.exists(redirectFile):
					with open(redirectFile, "r") as rfile:
						paths.append(rfile.read())
			elif i["task"].endswith(" (playblast)"):
				if i["version"].endswith(" (local)"):
					base = self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath)
				else:
					base = self.renderBasePath
				paths.append(os.path.join(base, "Playblasts", i["task"].replace(" (playblast)", ""), i["version"].replace(" (local)", "")))
			else:
				continue

		return [paths, renders]


	@err_decorator
	def addCompare(self):
		if self.tbw_browser.tabText(self.tbw_browser.currentIndex()) == "Assets":
			shotName = "Asset"
		else:
			shotName = self.cursShots

		curRnd = self.getCurRenders()

		for idx, path in enumerate(curRnd[0]):
			cFiles = []

			if os.path.isfile(path):
				cFiles = [path]
			else:
				for k in os.walk(path):
					cFiles = k[2]
					break

			if len(cFiles) > 0 and path not in self.compareStates:
				self.compareStates.insert(0, path)
				self.lw_compare.insertItem(0, str(self.lw_compare.count() + 1) + ": " + shotName + " - " + curRnd[1][idx]["task"] + " - " + curRnd[1][idx]["version"] + " - " + curRnd[1][idx]["layer"])
			

		if len(self.compareStates) > 0:
			self.b_compareRV.setEnabled(True)
			self.b_combineVersions.setEnabled(True)
			self.b_clearRV.setEnabled(True)


	@err_decorator
	def removeCompare(self):
		for i in self.lw_compare.selectedItems():
			del self.compareStates[self.lw_compare.row(i)]
			self.lw_compare.takeItem(self.lw_compare.row(i))

		for i in range(self.lw_compare.count()):
			item = self.lw_compare.item(i)
			item.setText(str(len(self.compareStates)-(self.lw_compare.row(item))) + ": " + item.text().split(": ", 1)[1])

		if len(self.compareStates) == 0:
			if len(self.lw_task.selectedItems()) < 2 and len(self.lw_version.selectedItems()) < 2:
				self.b_compareRV.setEnabled(False)
				self.b_combineVersions.setEnabled(False)
			self.b_clearRV.setEnabled(False)


	@err_decorator
	def clearCompare(self):
		self.compareStates = []
		self.lw_compare.clear()

		if len(self.lw_task.selectedItems()) < 2 and len(self.lw_version.selectedItems()) < 2:
			self.b_compareRV.setEnabled(False)
			self.b_combineVersions.setEnabled(False)
		self.b_clearRV.setEnabled(False)


	@err_decorator
	def compare(self, current=False, ctype="layout", prog=""):
		if hasattr(self, "tl") and self.tl.state() == QTimeLine.Running:
			self.tl.setPaused(True)

		if prog in ["DJV", "VLC", "default"] or (prog == "" and ((self.rv is None) or (self.djv is not None and self.core.getConfig("globals", "prefer_djv", ptype="bool")))):
			if prog in ["DJV", ""] and self.djv is not None:
				progPath = self.djv
			elif prog == "VLC":
				progPath = self.vlc
			elif prog in ["default", ""]:
				progPath = ""

			comd = []
			filePath = ""
			curRenders = self.getCurRenders()[0]

			if len(curRenders) > 0:
				if os.path.isfile(curRenders[0]):
					filePath = curRenders[0]
				else:
					for i in os.walk(curRenders[0]):
						for m in i[2]:
							filePath = os.path.join(i[0], m)
							break

						break

				if filePath != "":
					baseName, extension = os.path.splitext(filePath)
					if extension in [".jpg", ".jpeg", ".JPG", ".png", ".tif", ".tiff", ".exr", ".dpx", ".mp4", ".mov"]:
						if progPath == "":
							if platform.system() == "Windows":
								cmd = ['start', '', '%s' % self.core.fixPath(filePath)]
								subprocess.call(cmd, shell=True)
							elif platform.system() == "Linux":
								subprocess.call(["xdg-open", self.core.fixPath(filePath)])
							elif platform.system() == "Darwin":
								subprocess.call(["open", self.core.fixPath(filePath)])

							return
						else:
							comd = [progPath, filePath]

		elif prog in ["RV", ""]:
			comd = [self.rv]

			if current:
				if len(self.seq) == 1:
					cStates = [os.path.join(self.basepath, self.seq[0])]
				else:
					cStates = [self.basepath]
			elif len(self.compareStates) > 0:
				cStates = self.compareStates
			else:
				cStates = self.getCurRenders()[0]

			if ctype in ["layout", "sequence"]:
				cStates = reversed(cStates)

			for i in cStates:
				if os.path.isfile(i):
					comd.append(i)
				else:
					comd += self.getImgSources(i)

			if ctype == "layout":
				comd += ["-view", "defaultLayout"]
			elif ctype == "sequence":
				comd += ["-view", "defaultSequence"]
			elif ctype == "stack":
				comd += ["-over"]
			elif ctype == "stackDif":
				comd += ["-diff"]

		if comd != []:
			with open(os.devnull, "w") as f:
				try:
					subprocess.Popen(comd, stdin=subprocess.PIPE, stdout=f, stderr=f)
				except:
					try:
						subprocess.Popen(comd, stdin=subprocess.PIPE, stdout=f, stderr=f, shell=True)
					except Exception as e:
						raise RuntimeError("%s - %s" % (comd, e))


	@err_decorator
	def combineVersions(self, ctype="sequence"):
		if hasattr(self, "tl") and self.tl.state() == QTimeLine.Running:
			self.tl.setPaused(True)

		try:
			del sys.modules["CombineMedia"]
		except:
			pass

		import CombineMedia
		self.cm = CombineMedia.CombineMedia(core=self.core, ctype=ctype)

		result = self.cm.exec_()


	@err_decorator
	def compareOptions(self, event):
		cmenu = QMenu()

		sAct = QAction("Sequence", self)
		sAct.triggered.connect(lambda: self.compare(ctype="sequence"))
		cmenu.addAction(sAct)

		lAct = QAction("Layout", self)
		lAct.triggered.connect(lambda: self.compare(ctype="layout"))
		cmenu.addAction(lAct)

		lAct = QAction("Stack (over)", self)
		lAct.triggered.connect(lambda: self.compare(ctype="stack"))
		cmenu.addAction(lAct)

		lAct = QAction("Stack (difference)", self)
		lAct.triggered.connect(lambda: self.compare(ctype="stackDif"))
		cmenu.addAction(lAct)

		self.core.appPlugin.setRCStyle(self, cmenu)

		cmenu.exec_(QCursor.pos())


	@err_decorator
	def combineOptions(self, event):
		cmenu = QMenu()

		sAct = QAction("Sequence", self)
		sAct.triggered.connect(lambda: self.combineVersions(ctype="sequence"))
		cmenu.addAction(sAct)

		#lAct = QAction("Layout", self)
		#lAct.triggered.connect(lambda: self.combineVersions(ctype="layout"))
		#cmenu.addAction(lAct)

		#lAct = QAction("Stack (over)", self)
		#lAct.triggered.connect(lambda: self.combineVersions(ctype="stack"))
		#cmenu.addAction(lAct)

		#lAct = QAction("Stack (difference)", self)
		#lAct.triggered.connect(lambda: self.combineVersions(ctype="stackDif"))
		#cmenu.addAction(lAct)

		self.core.appPlugin.setRCStyle(self, cmenu)

		cmenu.exec_(QCursor.pos())


	@err_decorator
	def mouseDrag(self, event, element):
		if (element == self.l_preview) and event.buttons() != Qt.LeftButton:
			return
		elif (event.buttons() != Qt.LeftButton and element != self.cb_layer) or (event.buttons() == Qt.LeftButton and (event.modifiers() & Qt.ShiftModifier)):
			element.mmEvent(event)
			return
		elif element == self.cb_layer and event.buttons() != Qt.MiddleButton:
			element.mmEvent(event)
			return

		curRnd = self.getCurRenders()
		urlList = []
		mods = QApplication.keyboardModifiers()
		for i in curRnd[0]:
			if element == self.cb_layer:
				for k in os.walk(os.path.dirname(i)):
					for m in k[1]:
						urlList.append(QUrl("file:///%s" % os.path.join(k[0], m)))
					break
			else:
				if os.path.isfile(i):
					imgSrc = [i]
				else:
					imgSrc = self.getImgSources(i)

				for k in imgSrc:
					if mods == Qt.ControlModifier:
						url = "file:///%s" % os.path.dirname(k)
					else:
						url = "file:///%s" % k

					urlList.append(QUrl(url))

		if len(urlList) == 0:
			return

		drag = QDrag(self.l_preview)
		mData = QMimeData()
		
		mData.setUrls(urlList)
		drag.setMimeData(mData)

		drag.exec_()


	@err_decorator
	def getImgSources(self, path, getFirstFile=False):
		foundSrc = []
		for k in os.walk(path):
			sources = []
			psources = []
			for m in k[2]:
				baseName, extension = os.path.splitext(m)
				if extension in [".jpg", ".jpeg", ".JPG", ".png", ".tif", ".tiff", ".exr", ".mp4", ".mov", ".dpx"]:
					src = [baseName, extension]
					if len(baseName) > 3:
						endStr = baseName[-4:]
						if pVersion == 2:
							endStr = unicode(endStr)
						if endStr.isnumeric():
							src = [baseName[:-4], extension]

					psources.append(src)

			for m in sorted(k[2]):
				baseName, extension = os.path.splitext(m)
				if extension in [".jpg", ".jpeg", ".JPG", ".png", ".tif", ".tiff", ".exr", ".mp4", ".mov", ".dpx"]:
					fname = m
					if getFirstFile:
						return [os.path.join(path, m)]

					if len(baseName) > 3:
						endStr = baseName[-4:]
						if pVersion == 2:
							endStr = unicode(endStr)
						if endStr.isnumeric() and len(psources) == psources.count(psources[0]) and extension not in [".mp4", ".mov"]:
							fname = "%s@@@@%s" % (baseName[:-4], extension)							

					if fname in sources:
						if len(sources) == 1:
							break				# sequence detected
					else:
						foundSrc.append(os.path.join(path, fname))
						sources.append(fname)
			break

		return foundSrc


	@err_decorator
	def loadOiio(self):
		try:
			global oiio
			if platform.system() == "Windows":
				from oiio1618 import OpenImageIO as oiio
			elif platform.system() in ["Linux", "Darwin"]:
				import OpenImageIO as oiio

			self.oiioLoaded = True
		except:
			pass


	@err_decorator
	def getRVpath(self):
		try:
			if platform.system() == "Windows":
				cRVPath = self.core.getConfig("globals", "rvpath")
				if cRVPath is not None and os.path.exists(os.path.join(cRVPath, "bin", "rv.exe")):
					self.rv = os.path.join(cRVPath, "bin", "rv.exe")
				else:
					key = _winreg.OpenKey(
						_winreg.HKEY_LOCAL_MACHINE,
						"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\rv.exe",
						0,
						_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
					)

					self.rv = (_winreg.QueryValue(key, None))
			else:
				self.rv = "/usr/local/rv-Linux-x86-64-7.2.5/bin/rv"
				
			if not os.path.exists(self.rv):
				self.rv = None
		except:
			self.rv = None


	@err_decorator
	def getRVdLUT(self):
		dlut = None

		assets = self.core.getConfig('paths', "assets", configPath=self.core.prismIni)

		if assets is not None:
			lutPath = os.path.join(self.core.projectPath, assets, "LUTs", "RV_dLUT")
			if os.path.exists(lutPath) and len(os.listdir(lutPath)) > 0:
				dlut = os.path.join(lutPath, os.listdir(lutPath)[0])

		return dlut


	@err_decorator
	def getDJVpath(self):
		try:
			cDJVPath = self.core.getConfig("globals", "djvpath")

			if platform.system() == "Windows":
				if cDJVPath is not None and os.path.exists(os.path.join(cDJVPath, "bin", "djv_view.exe")):
					self.djv = os.path.join(cDJVPath, "bin", "djv_view.exe")
				else:
					key = _winreg.OpenKey(
						_winreg.HKEY_LOCAL_MACHINE,
						"SOFTWARE\\Classes\\djv_view\\shell\\open\\command",
						0,
						_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
					)

					self.djv = (_winreg.QueryValue(key, None)).split(" \"%1\"")[0]
			else:
				if cDJVPath is not None and os.path.exists(os.path.join(cDJVPath, "bin", "djv_view.sh")):
					self.djv = os.path.join(cDJVPath, "bin", "djv_view.sh")
				else:
					self.djv = "/usr/local/djv-1.1.0-Linux-64/bin/djv_view.sh"

			if not os.path.exists(self.djv):
				self.djv = None
		except:
			self.djv = None


	@err_decorator
	def getVLCpath(self):
		if platform.system() == "Windows":
			try:
				key = _winreg.OpenKey(
					_winreg.HKEY_LOCAL_MACHINE,
					"SOFTWARE\\VideoLAN\\VLC",
					0,
					_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
				)

				self.vlc = (_winreg.QueryValue(key, None))

				if not os.path.exists(self.vlc):
					self.vlc = None

			except:
				try:
					key = _winreg.OpenKey(
						_winreg.HKEY_LOCAL_MACHINE,
						"SOFTWARE\\WOW6432Node\\VideoLAN\\VLC",
						0,
						_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
					)

					self.vlc = (_winreg.QueryValue(key, None))
					if not os.path.exists(self.vlc):
						self.vlc = None

				except:
					self.vlc = None

		else:
			self.vlc = "/usr/bin/vlc"
			if not os.path.exists(self.vlc):
				self.vlc = None


	@err_decorator
	def convertImgs(self, extension):
		inputpath = os.path.join(self.basepath, self.seq[0]).replace("\\", "/")
		inputExt = os.path.splitext(inputpath)[1]
		videoInput = inputExt in [".mp4", ".mov"]

		if hasattr(self, "pwidth") and self.pwidth == "?":
			QMessageBox.warning(self.core.messageParent,"Media conversion", "Cannot read media file.")
			return

		if extension == ".mp4" and hasattr(self, "pwidth") and hasattr(self, "pheight") and (int(self.pwidth)%2 == 1 or int(self.pheight)%2 == 1):
			QMessageBox.warning(self.core.messageParent,"Media conversion", "Media with odd resolution can't be converted to mp4.")
			return

		if self.prvIsSequence:
			inputpath = os.path.splitext(inputpath)[0][:-4] + "%04d" + inputExt
		
		if self.curRTask.endswith(" (external)") or self.curRTask.endswith(" (2d)") or self.curRTask.endswith(" (playblast)"):
			outputpath = os.path.join(os.path.dirname(inputpath) + "(%s)" % extension[1:], os.path.basename(inputpath))
		else:
			outputpath = os.path.join(os.path.dirname(os.path.dirname(inputpath)) + "(%s)" % extension[1:], os.path.basename(os.path.dirname(inputpath)), os.path.basename(inputpath))

		if extension == ".mp4" and self.prvIsSequence:
			outputpath = os.path.splitext(outputpath)[0][:-5] + extension
		elif videoInput and extension != ".mp4":
			outputpath = "%s.%%04d%s" % (os.path.splitext(outputpath)[0], extension)
		else:
			outputpath = os.path.splitext(outputpath)[0] + extension

		if self.curRTask.endswith(" (external)"):
			curPath = os.path.join(self.renderBasePath, "Rendering", "external", self.curRTask.replace(" (external)", ""), self.curRVersion)
			rpath = os.path.join(curPath + "(%s)" % extension[1:], "REDIRECT.txt")

			if not os.path.exists(os.path.dirname(rpath)):
				os.makedirs(os.path.dirname(rpath))

			with open(rpath, "w") as rfile:
				rfile.write(os.path.dirname(outputpath))

		if self.prvIsSequence:
			startNum = self.pstart
		else:
			startNum = 0

		result = self.core.convertMedia(inputpath, startNum, outputpath)

		if self.prvIsSequence or videoInput:
			outputpath = outputpath.replace("%04d", "%04d" % int(startNum))

		curTab = self.tbw_browser.tabText(self.tbw_browser.currentIndex())
		curData = [curTab, self.cursShots, self.curRTask, self.curRVersion, self.curRLayer]
		self.showRender(curData[0], curData[1], curData[2], curData[3], curData[4])

		if os.path.exists(outputpath) and os.stat(outputpath).st_size > 0:
			self.core.copyToClipboard(outputpath)
			QMessageBox.information(self.core.messageParent,"Image conversion", "The images were converted successfully. (path is in clipboard)")
		else:
			self.core.ffmpegError("Image conversion", "The images could not be converted.", result)


	@err_decorator
	def compGetImportSource(self):
		sourceFolder = os.path.dirname(os.path.join(self.basepath, self.seq[0])).replace("\\", "/")
		sources = self.getImgSources(sourceFolder)
		sourceData = []

		for curSourcePath in sources:

			if "@@@@" in curSourcePath:
				if not hasattr(self, "pstart") or not hasattr(self, "pend") or self.pstart == "?" or self.pend == "?":
					firstFrame = 0
					lastFrame = 0
				else:
					firstFrame = self.pstart
					lastFrame = self.pend

				filePath = curSourcePath.replace("@@@@", "####").replace("\\","/")
			else:
				filePath =  curSourcePath.replace("\\","/")
				firstFrame = 0
				lastFrame = 0

			sourceData.append([filePath, firstFrame, lastFrame])

		return sourceData


	@err_decorator
	def compGetImportPasses(self):
		sourceFolder = os.path.dirname(os.path.dirname(os.path.join(self.basepath, self.seq[0]))).replace("\\", "/")
		passes = [ x for x in os.listdir(sourceFolder) if x[-5:] not in ["(mp4)", "(jpg)", "(png)"] and os.path.isdir(os.path.join(sourceFolder, x))]
		sourceData = []

		for curPass in passes:
			curPassPath = os.path.join(sourceFolder,curPass)

			imgs = os.listdir(curPassPath)
			if len(imgs) == 0:
				continue

			if len(imgs) > 1 and hasattr(self, "pstart") and hasattr(self, "pend") and self.pstart != "?" and self.pend != "?":
				firstFrame = self.pstart
				lastFrame = self.pend

				curPassName = imgs[0].split(".")[0]
				increment = "####"
				curPassFormat = imgs[0].split(".")[-1]
	 
				filePath =  os.path.join(sourceFolder,curPass,".".join([curPassName,increment,curPassFormat])).replace("\\","/")
			else:
				filePath =  os.path.join(curPassPath, imgs[0]).replace("\\","/")
				firstFrame = 0
				lastFrame = 0

			sourceData.append([filePath, firstFrame, lastFrame])

		return sourceData



if __name__ == "__main__":
	qapp = QApplication(sys.argv)

	from UserInterfacesPrism import qdarkstyle
	qapp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))

	appIcon = QIcon(os.path.join(prismRoot, "Scripts", "UserInterfacesPrism", "p_tray.ico"))

	qapp.setWindowIcon(appIcon)
	sys.path.append(os.path.join(prismRoot, "Scripts"))
	import PrismCore
	pc = PrismCore.PrismCore(prismArgs=["loadProject"])

	sys.exit(qapp.exec_())