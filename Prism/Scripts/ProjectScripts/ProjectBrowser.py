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



import sys, os, datetime, shutil, ast, time, traceback, random, platform, imp

prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

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
		sys.path.insert(0, os.path.join(prismRoot, "PythonLibs", "Python27"))
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

try:
	import EnterText
except:
	modPath = imp.find_module("EnterText")[1]
	if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
		os.remove(modPath)
	import EnterText



class ProjectBrowser(QMainWindow, ProjectBrowser_ui.Ui_mw_ProjectBrowser):
	def __init__(self, core):
		QMainWindow.__init__(self)
		self.setupUi(self)
		self.core = core

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

		self.curAsset = None
		self.curaStep = None
		self.curaCat = None

		self.cursShots = None
		self.cursStep = None
		self.cursCat = None

		self.tabLabels = {"Assets": "Assets", "Shots": "Shots", "Files": "Files", "Recent": "Recent"}
		self.tableColumnLabels = {"Version": "Version", "Comment": "Comment", "Date": "Date", "User": "User", "Name": "Name", "Step": "Step"}
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
		self.compareStates = []
		self.mediaPlaybacks = {"shots": {"name": "shots", "sl_preview": self.sl_preview, "prevCurImg": 0, "l_info": self.l_info, "l_date": self.l_date, "l_preview": self.l_preview, "openRV": False, "getMediaBase": self.getShotMediaPath, "getMediaBaseFolder": self.getShotMediaFolder}}

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
	#	self.refreshFCat()
		self.loadLayout()
		self.setRecent()
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
				erStr = ("%s ERROR - ProjectBrowser %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
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
		self.tw_aHierarchy.keyPressEvent = lambda x: self.keyPressed(x, "assets")
		self.e_assetSearch.origKeyPressEvent = self.e_assetSearch.keyPressEvent
		self.e_assetSearch.keyPressEvent = lambda x: self.keyPressed(x, "assetSearch")
		self.lw_aPipeline.mouseClickEvent = self.lw_aPipeline.mouseReleaseEvent
		self.lw_aPipeline.mouseReleaseEvent = lambda x: self.mouseClickEvent(x,"ap")
		self.lw_aPipeline.mouseDClick = self.lw_aPipeline.mouseDoubleClickEvent
		self.lw_aPipeline.mouseDoubleClickEvent = lambda x: self.mousedb(x,"ap", self.lw_aPipeline)
		self.lw_aCategory.mouseClickEvent = self.lw_aCategory.mouseReleaseEvent
		self.lw_aCategory.mouseReleaseEvent = lambda x: self.mouseClickEvent(x,"ac")
		self.lw_aCategory.mouseDClick = self.lw_aCategory.mouseDoubleClickEvent
		self.lw_aCategory.mouseDoubleClickEvent = lambda x: self.mousedb(x,"ac", self.lw_aCategory)
		self.tw_aFiles.mouseClickEvent = self.tw_aFiles.mouseReleaseEvent
		self.tw_aFiles.mouseReleaseEvent = lambda x: self.mouseClickEvent(x,"af")

		self.tw_sShot.mousePrEvent = self.tw_sShot.mousePressEvent
		self.tw_sShot.mousePressEvent = lambda x: self.mouseClickEvent(x,"ss")
		self.tw_sShot.mouseClickEvent = self.tw_sShot.mouseReleaseEvent
		self.tw_sShot.mouseReleaseEvent = lambda x: self.mouseClickEvent(x,"ss")
		self.tw_sShot.mouseDClick = self.tw_sShot.mouseDoubleClickEvent
		self.tw_sShot.mouseDoubleClickEvent = lambda x: self.mousedb(x,"ss", self.tw_sShot)
		self.tw_sShot.keyPressEvent = lambda x: self.keyPressed(x, "shots")
		self.e_shotSearch.origKeyPressEvent = self.e_shotSearch.keyPressEvent
		self.e_shotSearch.keyPressEvent = lambda x: self.keyPressed(x, "shotSearch")
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
		self.e_assetSearch.textChanged.connect(lambda x: self.refreshAHierarchy())
		self.lw_aPipeline.currentItemChanged.connect(self.aPipelineclicked)
		self.lw_aPipeline.customContextMenuRequested.connect(lambda x: self.rclCat("ap",x))
		self.lw_aCategory.currentItemChanged.connect(self.aCatclicked)
		self.lw_aCategory.customContextMenuRequested.connect(lambda x: self.rclCat("ac",x))
		self.tw_aFiles.customContextMenuRequested.connect(lambda x: self.rclFile("a",x))
		self.tw_aFiles.doubleClicked.connect(self.exeFile)
		self.tw_aFiles.setMouseTracking(True)
		self.tw_aFiles.mouseMoveEvent = lambda x: self.tableMoveEvent(x, "af")
		self.tw_aFiles.leaveEvent = lambda x: self.tableLeaveEvent(x, "af")
		self.tw_aFiles.focusOutEvent = lambda x: self.tableFocusOutEvent(x, "af")

		self.l_assetPreview.mouseDoubleClickEvent = lambda x: self.editAsset(self.curAsset)
		self.l_assetPreview.customContextMenuRequested.connect(lambda x: self.rclEntityPreview(x, "asset"))

		self.tw_sShot.currentItemChanged.connect(lambda x, y: self.sShotclicked(x))
		self.tw_sShot.itemExpanded.connect(self.sItemCollapsed)
		self.tw_sShot.itemCollapsed.connect(self.sItemCollapsed)
		self.tw_sShot.customContextMenuRequested.connect(lambda x: self.rclCat("ss",x))
		self.e_shotSearch.textChanged.connect(lambda x: self.refreshShots())
		self.lw_sPipeline.customContextMenuRequested.connect(lambda x: self.rclCat("sp",x))
		self.lw_sPipeline.currentItemChanged.connect(self.sPipelineclicked)
		self.lw_sCategory.currentItemChanged.connect(self.sCatclicked)		
		self.lw_sCategory.customContextMenuRequested.connect(lambda x: self.rclCat("sc",x))
		self.tw_sFiles.customContextMenuRequested.connect(lambda x: self.rclFile("sf",x))
		self.tw_sFiles.doubleClicked.connect(self.exeFile)
		self.tw_sFiles.setMouseTracking(True)
		self.tw_sFiles.mouseMoveEvent = lambda x: self.tableMoveEvent(x, "sf")
		self.tw_sFiles.leaveEvent = lambda x: self.tableLeaveEvent(x, "sf")
		self.tw_sFiles.focusOutEvent = lambda x: self.tableFocusOutEvent(x, "sf")

		self.l_shotPreview.mouseDoubleClickEvent = lambda x: self.editShot(self.cursShots)
		self.l_shotPreview.customContextMenuRequested.connect(lambda x: self.rclEntityPreview(x, "shot"))

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
		self.tw_recent.setMouseTracking(True)
		self.tw_recent.mouseMoveEvent = lambda x: self.tableMoveEvent(x, "r")
		self.tw_recent.leaveEvent = lambda x: self.tableLeaveEvent(x, "r")
		self.tw_recent.focusOutEvent = lambda x: self.tableFocusOutEvent(x, "r")

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

		self.helpMenu = QMenu("Help")

		self.actionWebsite = QAction("Visit website", self)
		self.actionWebsite.triggered.connect(lambda: self.core.openWebsite("home"))
		self.helpMenu.addAction(self.actionWebsite)

		self.actionWebsite = QAction("Tutorials", self)
		self.actionWebsite.triggered.connect(lambda:self.core.openWebsite("tutorials"))
		self.helpMenu.addAction(self.actionWebsite)

		self.actionWebsite = QAction("Documentation", self)
		self.actionWebsite.triggered.connect(lambda: self.core.openWebsite("documentation"))
		self.helpMenu.addAction(self.actionWebsite)

		self.actionSendFeedback = QAction("Send feedback/feature requests...", self)
		self.actionSendFeedback.triggered.connect(self.core.sendFeedback)
		self.helpMenu.addAction(self.actionSendFeedback)

		self.actionCheckVersion = QAction("Check for Prism updates", self)
		self.actionCheckVersion.triggered.connect(self.core.checkForUpdates)
		self.helpMenu.addAction(self.actionCheckVersion)

		self.actionAbout = QAction("About...", self)
		self.actionAbout.triggered.connect(self.core.showAbout)
		self.helpMenu.addAction(self.actionAbout)
	
		self.menubar.addMenu(self.helpMenu)

		self.core.appPlugin.setRCStyle(self, self.helpMenu)

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

		self.tabOrder = {
					"Assets":{"order":0, "showRenderings":True}, 
					"Shots":{"order":1, "showRenderings":True},
					"Files":{"order":2, "showRenderings":False},
					"Recent":{"order":3, "showRenderings":False}
					}
		if cData["assetsOrder"] is not None and cData["shotsOrder"] is not None and cData["filesOrder"] is not None and cData["recentOrder"] is not None:
			for i in ["assetsOrder", "shotsOrder", "filesOrder", "recentOrder"]:
				if cData[i] >= len(self.tabOrder):
					cData[i] = -1
			self.tabOrder["Assets"]["order"] = cData["assetsOrder"]
			self.tabOrder["Shots"]["order"] = cData["shotsOrder"]
			self.tabOrder["Files"]["order"] = cData["filesOrder"]
			self.tabOrder["Recent"]["order"] = cData["recentOrder"]

		self.tbw_browser.insertTab(self.tabOrder["Assets"]["order"], self.t_assets, self.tabLabels["Assets"])
		self.tbw_browser.insertTab(self.tabOrder["Shots"]["order"], self.t_shots, self.tabLabels["Shots"])
		self.tbw_browser.insertTab(self.tabOrder["Files"]["order"], self.t_files, self.tabLabels["Files"])
		self.tbw_browser.insertTab(self.tabOrder["Recent"]["order"], self.t_recent, self.tabLabels["Recent"])

		self.t_assets.setProperty("tabType", "Assets")
		self.t_shots.setProperty("tabType", "Shots")
		self.t_files.setProperty("tabType", "Files")
		self.t_recent.setProperty("tabType", "Recent")

		if not cData["assetsVisible"]:
			self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_assets))
			self.actionAssets.setChecked(False)

		if not cData["shotsVisible"]:
			self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_shots))
			self.actionShots.setChecked(False)

		self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_files))
		self.actionFiles.setChecked(False)
		self.actionFiles.setVisible(False)
		self.tabOrder.pop("Files")

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

		self.core.appPlugin.projectBrowserLoadLayout(self)
		self.core.callback(name="projectBrowser_loadUI", types=["custom" ,"unloadedApps"], args=[self])
		if cData["current"] is not None and cData["current"] != "" and cData["current"] in self.tabOrder:
			for i in range(self.tbw_browser.count()):
				if self.tbw_browser.widget(i).property("tabType") == cData["current"]:
					self.tbw_browser.setCurrentIndex(i)
					break
			self.updateChanged(False)

		if self.tbw_browser.count() == 0:
			self.tbw_browser.setVisible(False)
			self.gb_renderings.setVisible(False)
		else:
			if self.actionRenderings.isChecked():
				self.gb_renderings.setVisible(self.tabOrder[self.tbw_browser.currentWidget().property("tabType")]["showRenderings"])

		if cData["autoUpdateRenders"] is not None:
			self.chb_autoUpdate.setChecked(cData["autoUpdateRenders"])

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

		self.e_assetSearch.setVisible(False)
		self.e_shotSearch.setVisible(False)

		if psVersion == 2:
			self.e_assetSearch.setClearButtonEnabled(True)
			self.e_shotSearch.setClearButtonEnabled(True)

		if self.core.compareVersions(self.core.projectVersion, "v1.2.1.6") == "lower":
			self.w_aCategory.setVisible(False)
		

	@err_decorator
	def closeEvent(self, event):
		tabOrder = []
		for i in range(self.tbw_browser.count()):
			tabOrder.append(self.tbw_browser.widget(i).property("tabType"))

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
			visible.append(self.tbw_browser.widget(i).property("tabType"))

		cData = []

		curW = self.tbw_browser.widget(self.tbw_browser.currentIndex())
		if curW:
			currentType = curW.property("tabType")
		else:
			currentType = ""

		cData.append(['browser', "current", currentType])
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

		for i in self.mediaPlaybacks:
			if "timeline" in i and i["timeline"].state() != QTimeLine.NotRunning:
				i["timeline"].setPaused(True)

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
		if not self.tbw_browser.widget(tab):
			tabType = ""
			self.gb_renderings.setVisible(False)
		else:
			tabType = self.tbw_browser.widget(tab).property("tabType")

			if tabType == "Assets":
				self.refreshAFile()
			elif tabType == "Shots":
				self.refreshSFile()
			elif tabType == "Files":
				self.refreshFCat()
			elif tabType == "Recent":
				self.setRecent()

			if self.actionRenderings.isChecked():
				self.gb_renderings.setVisible(self.tabOrder[tabType]["showRenderings"])

		if self.gb_renderings.isVisible() and self.chb_autoUpdate.isChecked():
			self.updateTasks()


	@err_decorator
	def refreshUI(self):
		curTab = self.tbw_browser.currentWidget().property("tabType")
		curData = [curTab, self.cursShots, self.curRTask, self.curRVersion, self.curRLayer]

		if curTab == "Assets":
			curAssetItem = self.tw_aHierarchy.currentItem()
			if curAssetItem is None:
				dstname = self.aBasePath
			else:
				basePath = self.tw_aHierarchy.currentItem().text(1)
				if self.curaStep is None:
					step = ""
				else:
					step = os.path.join("Scenefiles", self.curaStep)

				if self.curaCat is None:
					cat = ""
				else:
					cat = self.curaCat

				dstname = os.path.join(basePath, step, cat)

			self.refreshAHierarchy()
		elif curTab == "Shots":
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
		elif curTab == "Recent":
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
			if cItem is not None and cItem.text(2) == "asset":
				return
			name = "Entity"
		elif tab == "ap":
			if self.curAsset:
				self.createStepWindow("a")
		elif tab == "ac":
			if self.curaStep is not None and self.lw_aCategory.indexAt(event.pos()).data() == None:
				name = "Category"
		elif tab == "ss":
			mIndex = uielement.indexAt(event.pos())
			if mIndex.data() == None:
				self.editShot()
			else:
				if mIndex.parent().column() == -1 and uielement.mapFromGlobal(QCursor.pos()).x()>10:
					uielement.setExpanded(mIndex, not uielement.isExpanded(mIndex))
					uielement.mouseDClick(event)
		elif tab == "sp":
			shotName = self.splitShotname(self.cursShots)
			if shotName and len(shotName) == 2 and shotName[1] and self.lw_sPipeline.indexAt(event.pos()).data() == None:
				self.createStepWindow("s")
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
					elif uielement == "ac":
						index = self.lw_aCategory.indexAt(event.pos())
						if index.data() == None:
							self.lw_aCategory.setCurrentIndex(self.lw_aCategory.model().createIndex(-1,0))
						self.lw_aCategory.mouseClickEvent(event)
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
	def keyPressed(self, event, entity):
		if entity in ["assets", "assetSearch"]:
			etext = self.e_assetSearch
		elif entity in ["shots", "shotSearch"]:
			etext = self.e_shotSearch

		if entity in ["assets", "shots"]:
			if event.key() == Qt.Key_Escape:
				etext.setVisible(False)
				etext.setText("")
				etext.textChanged.emit("")
			else:
				etext.setVisible(True)
				etext.setFocus()
				etext.keyPressEvent(event)
		elif entity in ["assetSearch", "shotSearch"]:
			if event.key() == Qt.Key_Escape:
				etext.setVisible(False)
				etext.setText("")
				etext.textChanged.emit("")
			else:
				etext.origKeyPressEvent(event)

		event.accept()


	@err_decorator
	def tableMoveEvent(self, event, table):
		self.showDetailWin(event, table)
		if hasattr(self, "detailWin") and self.detailWin.isVisible():
			self.detailWin.move(QCursor.pos().x()+20, QCursor.pos().y())


	@err_decorator
	def showDetailWin(self, event, table):
		if table == "af":
			table = self.tw_aFiles
		elif table == "sf":
			table = self.tw_sFiles
		elif table == "r":
			table = self.tw_recent

		index = table.indexAt(event.pos())
		if index.data() is None:
			if hasattr(self, "detailWin") and self.detailWin.isVisible():
				self.detailWin.close()
			return

		scenePath = table.model().index(index.row(),0).data(Qt.UserRole)
		if scenePath is None:
			if hasattr(self, "detailWin") and self.detailWin.isVisible():
				self.detailWin.close()
			return

		infoPath = os.path.splitext(scenePath)[0] + "info.yml"
		prvPath = os.path.splitext(scenePath)[0] + "preview.jpg"

		if not os.path.exists(infoPath) and not os.path.exists(prvPath):
			if hasattr(self, "detailWin") and self.detailWin.isVisible():
				self.detailWin.close()
			return
	
		if not hasattr(self, "detailWin") or not self.detailWin.isVisible() or self.detailWin.scenePath != scenePath:
			if hasattr(self, "detailWin"):
				self.detailWin.close()

			self.detailWin = QFrame()

			ss = getattr(self.core.appPlugin, "getFrameStyleSheet", lambda x: "")(self)
			self.detailWin.setStyleSheet(ss +""" .QFrame{ border: 2px solid rgb(100,100,100);} """)

			self.detailWin.scenePath = scenePath
			self.core.parentWindow(self.detailWin)
			winwidth = 320
			winheight = 10
			VBox = QVBoxLayout()
			if os.path.exists(prvPath):
				imgmap = self.getImgPMap(prvPath)
				l_prv = QLabel()
				l_prv.setPixmap(imgmap)
				l_prv.setStyleSheet( """
					border: 1px solid rgb(100,100,100);
				""")
				VBox.addWidget(l_prv)
			w_info = QWidget()
			GridL = QGridLayout()
			GridL.setColumnStretch(1,1)
			rc = 0
			sPathL = QLabel("Scene:\t")
			sPath = QLabel(os.path.basename(scenePath))
			GridL.addWidget(sPathL, rc, 0, Qt.AlignLeft)
			GridL.addWidget(sPath, rc, 1, Qt.AlignLeft)
			rc += 1
			if os.path.exists(infoPath):
				sceneInfo = self.core.readYaml(infoPath)
				if sceneInfo is None:
					sceneInfo = {}
				if "username" in sceneInfo:
					unameL = QLabel("User:\t")
					uname = QLabel(sceneInfo["username"])
					GridL.addWidget(unameL, rc, 0, Qt.AlignLeft)
					GridL.addWidget(uname, rc, 1, Qt.AlignLeft)
					GridL.addWidget(uname, rc, 1, Qt.AlignLeft)
					rc += 1
				if "description" in sceneInfo and sceneInfo["description"] != "":
					descriptionL = QLabel("Description:\t")
					description = QLabel(sceneInfo["description"])
					GridL.addWidget(descriptionL, rc, 0, Qt.AlignLeft | Qt.AlignTop)
					GridL.addWidget(description, rc, 1, Qt.AlignLeft)

			w_info.setLayout(GridL)
			GridL.setContentsMargins(0,0,0,0)
			VBox.addWidget(w_info)
			self.detailWin.setLayout(VBox)
			self.detailWin.setWindowFlags(
					  Qt.FramelessWindowHint # hides the window controls
					| Qt.WindowStaysOnTopHint # forces window to top... maybe
					| Qt.SplashScreen # this one hides it from the task bar!
					)
			self.detailWin.setAttribute(Qt.WA_ShowWithoutActivating)
			self.detailWin.setGeometry(0, 0, winwidth, winheight)
			self.detailWin.move(QCursor.pos().x()+20, QCursor.pos().y())
			self.detailWin.show()


	@err_decorator
	def tableLeaveEvent(self, event, table):
		if hasattr(self, "detailWin") and self.detailWin.isVisible():
			self.detailWin.close()


	@err_decorator
	def tableFocusOutEvent(self, event, table):
		if hasattr(self, "detailWin") and self.detailWin.isVisible():
			self.detailWin.close()


	@err_decorator
	def rclCat(self, tab, pos):
		rcmenu = QMenu()
		typename = "Category"
		callbackName = ""

		if tab == "ah":
			lw = self.tw_aHierarchy
			cItem = lw.itemFromIndex(lw.indexAt(pos))
			if cItem is None:
				path = self.aBasePath
			else:
				path = os.path.dirname(cItem.text(1))
			typename = "Entity"
			callbackName = "openPBAssetContextMenu"
		elif tab == "ap":
			lw = self.lw_aPipeline

			if not self.curAsset:
				return

			path = os.path.join(self.curAsset, "Scenefiles")
			typename = "Step"
			callbackName = "openPBAssetStepContextMenu"

		elif tab == "ac":
			lw = self.lw_aCategory
			if self.curaStep is not None:
				path = os.path.join( self.curAsset, "Scenefiles", self.curaStep)
			else:
				return False

			callbackName = "openPBAssetCategoryContextMenu"

		elif tab == "ss":
			lw = self.tw_sShot
			path = self.sBasePath
			typename = "Shot"
			callbackName = "openPBShotContextMenu"

		elif tab == "sp":
			lw = self.lw_sPipeline
			if self.cursShots is not None:
				path = os.path.join(self.sBasePath, self.cursShots, "Scenefiles")
			else:
				return False
			typename = "Step"
			callbackName = "openPBShotStepContextMenu"

		elif tab == "sc":
			lw = self.lw_sCategory
			if self.cursStep is not None:
				path = os.path.join(self.sBasePath, self.cursShots, "Scenefiles", self.cursStep)
			else:
				return False

			callbackName = "openPBShotCategoryContextMenu"

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
				createAct.triggered.connect(lambda: self.createStepWindow("a"))
			elif tab == "sp":
				createAct.triggered.connect(lambda: self.createStepWindow("s"))
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
				if cItem is not None and cItem.text(2) != "asset":
					subcat = QAction("Create entity", self)
					typename = "Entity"
					subcat.triggered.connect(lambda: self.createCatWin(tab, typename))
					rcmenu.addAction(subcat)
				elif cItem.text(2) == "asset":
					for i in self.core.prjManagers.values():
						prjMngMenu = i.pbBrowser_getAssetMenu(self, iname, cItem.text(1).replace(self.aBasePath, "")[1:])
						if prjMngMenu is not None:
							prjMngMenus.append(prjMngMenu)

				oAct = QAction("Omit Asset", self)
				oAct.triggered.connect(lambda: self.omitEntity("asset", cItem.text(1).replace(self.aBasePath, "")[1:]))
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
				oAct.triggered.connect(lambda: self.omitEntity("shot", self.cursShots))
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
			if iname is None:
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

		if callbackName:
			self.core.callback(name=callbackName, types=["custom"], args=[self, rcmenu, lw.indexAt(pos)])

		rcmenu.exec_(QCursor.pos())


	@err_decorator
	def rclFile(self, tab, pos):
		if tab == "a":
			if self.curaStep is None or self.curaCat is None:
				return

			tw = self.tw_aFiles
			filepath = os.path.join(self.curAsset, "Scenefiles", self.curaStep, self.curaCat)
			tabName = "asset"
		elif tab == "sf":
			if self.cursStep is None or self.cursCat is None:
				return

			tw = self.tw_sFiles
			filepath = os.path.join(self.sBasePath, self.cursShots, "Scenefiles", self.cursStep, self.cursCat)
			tabName = "shot"
		elif tab == "r":
			tw = self.tw_recent

		rcmenu = QMenu()

		if tw.selectedIndexes() != []:
			idx = tw.selectedIndexes()[0]
			irow = idx.row()
		else:
			idx = None
			irow = -1
		cop = QAction("Copy", self)
		if irow == -1 :
			if tab == "r":
				return False
			cop.setEnabled(False)
			if not os.path.exists(filepath) and self.core.useLocalFiles and os.path.exists(filepath.replace(self.core.projectPath, self.core.localProjectPath)):
				filepath = filepath.replace(self.core.projectPath, self.core.localProjectPath)
		else:
			filepath = self.core.fixPath(tw.model().index(irow, 0).data(Qt.UserRole))
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
						empAct.triggered.connect(lambda y=None, x=tabName, fname=i: self.createEmptyScene(x, fname))
						emp.addAction(empAct)

			newPreset = QAction("< Create new preset from current >", self)
			newPreset.triggered.connect(lambda y=None, x=tabName: self.createEmptyScene(x, "createnew"))
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
		self.core.callback(name="openPBFileContextMenu", types=["custom"], args=[self, rcmenu, idx])

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

		if self.tbw_browser.currentWidget().property("tabType") == "Assets":
			refresh = self.refreshAFile
		elif self.tbw_browser.currentWidget().property("tabType") == "Shots":
			refresh = self.refreshSFile
		elif self.tbw_browser.currentWidget().property("tabType") == "Files":
			refresh = self.refreshFCat
		elif self.tbw_browser.currentWidget().property("tabType") == "Recent":
			refresh = self.setRecent

		if filepath == "":
			filepath = index.model().index(index.row(), 0).data(Qt.UserRole)

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
				try:
					subprocess.Popen([appPath, self.core.fixPath(filepath)])
				except Exception as e:
					QMessageBox.warning(self.core.messageParent,"Warning", "Could not execute file:\n\n%s" % str(e))
				fileStarted = True

			if not fileStarted:
				try:
					if platform.system() == "Windows":
						os.startfile(self.core.fixPath(filepath))
					elif platform.system() == "Linux":
						subprocess.Popen(["xdg-open", filepath])
					elif platform.system() == "Darwin":
						subprocess.Popen(["open", filepath])
				except:
					ext = os.path.splitext(filepath)[1]
					warnStr = "Could not open the scenefile.\n\nPossibly there is no application connected to \"%s\" files on your computer.\nUse the overrides in the \"DCC apps\" tab of the Prism Settings to specify an application for this filetype." % ext
					msg = QMessageBox(QMessageBox.Warning, "Warning", warnStr, QMessageBox.Ok, parent=self.core.messageParent)
					msg.exec_()

		if self.tbw_browser.currentWidget().property("tabType") != "Files":
			self.core.addToRecent(filepath)
			self.setRecent()

		self.core.callback(name="onSceneOpen", types=["custom"], args=[self, filepath])

		if openSm:
			self.core.stateManager()

		refresh()
		if self.core.getCurrentFileName().replace("\\","/") == filepath and self.actionCloseAfterLoad.isChecked():
			self.close()


	@err_decorator
	def createFromCurrent(self):
		if self.tbw_browser.currentWidget().property("tabType") == "Assets":
			dstname = self.curAsset
			refresh = self.refreshAFile

			prefix = os.path.basename(self.curAsset)
			filepath = self.core.generateScenePath(entity="asset", entityName=prefix, step=self.curaStep, category=self.curaCat, basePath=dstname, extension=self.core.appPlugin.getSceneExtension(self))

		elif self.tbw_browser.currentWidget().property("tabType") == "Shots":
			refresh = self.refreshSFile
			filepath = self.core.generateScenePath(entity="shot", entityName=self.cursShots, step=self.cursStep, category=self.cursCat, extension=self.core.appPlugin.getSceneExtension(self))
		else:
			return

		if self.core.useLocalFiles:
			filepath = filepath.replace(self.core.projectPath, self.core.localProjectPath)

		if not os.path.exists(os.path.dirname(filepath)):
			try:
				os.makedirs(os.path.dirname(filepath))
			except:
				QMessageBox.warning(self.core.messageParent, "Warning", "The directory could not be created")
				return None

		filepath = filepath.replace("\\","/")

		asRunning = hasattr(self.core,  "asThread") and self.core.asThread.isRunning()
		self.core.startasThread(quit=True)
	
		filepath = self.core.saveScene(prismReq=False, filepath=filepath)
		self.core.sceneOpen()
		if asRunning:
			self.core.startasThread()

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

		if not autobfile:
			return

		if tab == "a":
			dstname = self.curAsset
			refresh = self.refreshAFile

			prefix = os.path.basename(self.curAsset)
			filepath = self.core.generateScenePath(entity="asset", entityName=prefix, step=self.curaStep, extension=os.path.splitext(autobfile)[1], category=self.curaCat, basePath=dstname)
		elif tab == "sf":
			refresh = self.refreshSFile

			sceneData = self.core.getScenefileData(autobfile)
			if sceneData["type"] == "shot":
				comment = sceneData["comment"]
			else:
				comment = ""

			filepath = self.core.generateScenePath(entity="shot", entityName=self.cursShots, step=self.cursStep, category=self.cursCat, extension=os.path.splitext(autobfile)[1])
		else:
			return

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
	def createEmptyScene(self, entity, fileName, entityName=None, step=None, category=None, comment=None, openFile=True):
		if fileName == "createnew":
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

		ext = os.path.splitext(fileName)[1]
		comment = comment or ""

		if entity == "asset":
			refresh = self.refreshAFile
			if entityName:
				for i in self.core.getAssetPaths():
					if os.path.basename(i) == entityName:
						dstname = i
						break
				else:
					return
			else:
				dstname = self.curAsset

			assetName = entityName or os.path.basename(self.curAsset)
			step = step or self.curaStep
			category = category or self.curaCat
			filePath = self.core.generateScenePath("asset", assetName, step, assetPath=dstname, category=category, extension=ext, comment=comment)
		elif entity == "shot":
			refresh    = self.refreshSFile
			entityName = entityName or self.cursShots
			step       = step or self.cursStep
			category = category or self.cursCat
			filePath = self.core.generateScenePath("shot", entityName, step, category=category, extension=ext, comment=comment)
		else:
			return

		if os.path.isabs(fileName):
			scene = fileName
		else:
			scene = os.path.join(os.path.dirname(self.core.prismIni), "EmptyScenes", fileName)

		if self.core.useLocalFiles:
			filePath = filePath.replace(self.core.projectPath, self.core.localProjectPath)

		if not os.path.exists(os.path.dirname(filePath)):
			try:
				os.makedirs(os.path.dirname(filePath))
			except:
				self.core.popup("The directory could not be created:\n\n%s" % os.path.dirname(filePath))
				return

		filePath = filePath.replace("\\","/")

		shutil.copyfile(scene, filePath)

		if self.core.uiAvailable:
			if ext in self.core.appPlugin.sceneFormats and openFile:
				self.core.callback(name="preLoadEmptyScene", types=["curApp", "custom"], args=[self, filePath])
				self.exeFile(filepath=filePath)
				self.core.callback(name="postLoadEmptyScene", types=["curApp", "custom"], args=[self, filePath])
			else:
				self.core.addToRecent(filePath)
				self.setRecent()
				refresh()

		return filePath


	@err_decorator
	def copyfile(self, path, mode = None):
		if self.tbw_browser.currentWidget().property("tabType") == "Assets":
			self.copiedFile = path
		elif self.tbw_browser.currentWidget().property("tabType") == "Shots":
			self.copiedsFile = path 
		elif self.tbw_browser.currentWidget().property("tabType") == "Files":
			self.fcopymode = mode
			self.copiedfFile = path


	@err_decorator
	def pastefile(self, tab):
		if tab == "a":
			dstname = self.curAsset

			prefix = os.path.basename(self.curAsset)
			dstname = self.core.generateScenePath(entity="asset", entityName=prefix, step=self.curaStep, category=self.curaCat, extension=os.path.splitext(self.copiedFile)[1], basePath=dstname)

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
			oldfname = os.path.basename(self.copiedsFile)
			dstname = self.core.generateScenePath(entity="shot", entityName=self.cursShots, step=self.cursStep, category=self.cursCat, extension=os.path.splitext(oldfname)[1])

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

		self.core.callback(name="onStepDlgOpen", types=["custom"], args=[self, self.ss])

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

		self.filteredAssetPaths = self.core.getAssetPaths()
		if self.e_assetSearch.isVisible():
			filteredPaths = []
			for assetPath in self.filteredAssetPaths:
				assetPath = assetPath.replace(self.aBasePath, "")
			
				if self.core.useLocalFiles:
					assetPath = assetPath.replace(self.aBasePath.replace(self.core.projectPath, self.core.localProjectPath), "")
				assetPath = assetPath[1:]

				if self.e_assetSearch.text() in assetPath:
					filteredPaths.append(assetPath)

			self.filteredAssetPaths = filteredPaths

		for path in dirs:
			val = os.path.basename(path)
			if val not in self.omittedEntities["asset"]:
				if self.e_assetSearch.isVisible():
					aPath = path.replace(self.aBasePath, "")
			
					if self.core.useLocalFiles:
						aPath = aPath.replace(self.aBasePath.replace(self.core.projectPath, self.core.localProjectPath), "")
					aPath = aPath[1:]

					if len([x for x in self.filteredAssetPaths if aPath in x]) == 0:
						continue

				item = QTreeWidgetItem([val, path])
				self.tw_aHierarchy.addTopLevelItem(item)
				self.refreshAItem(item, expanded=False)

		if self.tw_aHierarchy.topLevelItemCount() > 0:
			self.tw_aHierarchy.setCurrentItem(self.tw_aHierarchy.topLevelItem(0))
		else:
			self.curAsset = None
			self.refreshAStep()
			self.refreshAssetinfo()


	@err_decorator
	def refreshAItem(self, item, expanded=True):
		item.takeChildren()

		path = item.text(1)

		if expanded:
			self.adclick = False
			if item.text(1) not in self.aExpanded and not self.e_assetSearch.isVisible():
				self.aExpanded.append(item.text(1))

		if self.core.useLocalFiles:
			path = path.replace(self.core.localProjectPath, self.core.projectPath)
			lpath = path.replace(self.core.projectPath, self.core.localProjectPath)

		dirContent = []
		dirContentPaths = []

		if os.path.exists(path):
			gContent = os.listdir(path)
			dirContent += gContent
			dirContentPaths += [os.path.join(path,x) for x in gContent]

		if self.core.useLocalFiles and os.path.exists(lpath):
			lContent = os.listdir(lpath)
			dirContent += lContent
			dirContentPaths += [os.path.join(lpath,x) for x in lContent]

		isAsset = False
		if "Export" in dirContent and "Playblasts" in dirContent and "Rendering" in dirContent and "Scenefiles" in dirContent:
			isAsset = True
			item.setText(2, "asset")
		else:
			item.setText(2, "folder")
			childs = []
			for i in dirContentPaths:
				if os.path.isdir(i):
					aName = i.replace(self.aBasePath, "")
					if self.core.useLocalFiles:
						aName = aName.replace(self.aBasePath.replace(self.core.projectPath, self.core.localProjectPath), "")
					aName = aName[1:]

					if self.e_assetSearch.isVisible():
						if len([x for x in self.filteredAssetPaths if aName in x]) == 0:
							continue

					if os.path.basename(i) not in childs and aName not in self.omittedEntities["asset"]:
						child = QTreeWidgetItem([os.path.basename(i), i])
						item.addChild(child)
						childs.append(os.path.basename(i))
						if expanded:
							self.refreshAItem(child, expanded=False)

		if isAsset:
			iFont = item.font(0)
			iFont.setBold(True)
			item.setFont(0, iFont)

		if path in self.aExpanded and not expanded or self.e_assetSearch.isVisible():
			item.setExpanded(True)


	@err_decorator
	def hItemCollapsed(self, item):
		self.adclick = False
		if item.text(1) in self.aExpanded:
			self.aExpanded.remove(item.text(1))


	@err_decorator
	def refreshAStep(self, cur=None, prev=None):
		self.lw_aPipeline.clear()

		if not self.curAsset:
			self.refreshaCat()
			return

		path = os.path.join(self.curAsset, "Scenefiles")

		if self.core.useLocalFiles:
			path = path.replace(self.core.localProjectPath, self.core.projectPath)
			lpath = path.replace(self.core.projectPath, self.core.localProjectPath)

		dirContent = []

		if os.path.exists(path):
			dirContent += [os.path.join(path,x) for x in os.listdir(path)]

		if self.core.useLocalFiles and os.path.exists(lpath):
			dirContent += [os.path.join(lpath,x) for x in os.listdir(lpath)]

		addedSteps = []
		for i in sorted(dirContent, key=lambda x: os.path.basename(x)):
			stepName = os.path.basename(i)
			if os.path.isdir(i) and stepName not in addedSteps:
				sItem = QListWidgetItem(stepName)
				self.lw_aPipeline.addItem(sItem)
				addedSteps.append(stepName)

		if self.lw_aPipeline.count() > 0:
			self.lw_aPipeline.setCurrentRow(0)
		else:
			self.curaStep = None
			self.refreshaCat()


	@err_decorator
	def refreshaCat(self):
		self.lw_aCategory.clear()

		if not self.curAsset or not self.curaStep:
			self.refreshAFile()
			return

		path = os.path.join(self.curAsset, "Scenefiles", self.curaStep)

		if self.core.useLocalFiles:
			path = path.replace(self.core.localProjectPath, self.core.projectPath)
			lpath = path.replace(self.core.projectPath, self.core.localProjectPath)

		dirContent = []

		if os.path.exists(path):
			dirContent += [os.path.join(path,x) for x in os.listdir(path)]

		if self.core.useLocalFiles and os.path.exists(lpath):
			dirContent += [os.path.join(lpath,x) for x in os.listdir(lpath)]

		addedCats = []
		for i in sorted(dirContent, key=lambda x: os.path.basename(x)):
			catName = os.path.basename(i)
			if os.path.isdir(i) and catName not in addedCats:
				sItem = QListWidgetItem(catName)
				self.lw_aCategory.addItem(sItem)
				addedCats.append(catName)

		if self.lw_aCategory.count() > 0:
			self.lw_aCategory.setCurrentRow(0)
		else:
			if self.core.compareVersions(self.core.projectVersion, "v1.2.1.6") == "lower":
				self.curaCat = "category"
			else:
				self.curaCat = None
			
			self.refreshAFile()


	@err_decorator
	def refreshAFile(self, cur=None, prev=None):
		scenefiles = []

		if self.curAsset and self.curaStep and self.curaCat:
			if self.core.compareVersions(self.core.projectVersion, "v1.2.1.6") == "lower":
				path = os.path.join(self.curAsset, "Scenefiles", self.curaStep)
			else:
				path = os.path.join(self.curAsset, "Scenefiles", self.curaStep, self.curaCat)

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
		model.setHorizontalHeaderLabels(["", self.tableColumnLabels["Version"], self.tableColumnLabels["Comment"], self.tableColumnLabels["Date"], self.tableColumnLabels["User"]])

		appfilter = []

		for i in self.appFilters:
			if eval("self.chb_aShow%s.isChecked()" % self.appFilters[i]["shortName"]):
				appfilter += self.appFilters[i]["formats"]
		
		#example filename: Body_mod_v0002_details-added_rfr_.max
		for i in scenefiles:
			row = []
			fname = self.core.getScenefileData(i)

			if fname["type"] == "asset" and fname["extension"] in appfilter:
				publicFile = self.core.useLocalFiles and i.startswith(os.path.join(self.core.projectPath, self.scenes, "Assets"))

				if pVersion == 2:
					item = QStandardItem(unicode("█", "utf-8"))
				else:
					item = QStandardItem("█")
				item.setFont(QFont('SansSerif', 100))
				item.setFlags(~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
				item.setData(i, Qt.UserRole)

				colorVals = [128,128,128]
				if fname["extension"] in self.core.appPlugin.sceneFormats:
					colorVals = self.core.appPlugin.appColor
				else:
					for k in self.core.unloadedAppPlugins.values():
						if fname["extension"] in k.sceneFormats:
							colorVals = k.appColor

				item.setForeground(QColor(colorVals[0], colorVals[1], colorVals[2]))

				row.append(item)
				item = QStandardItem(fname["version"])
				item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
				row.append(item)
				if fname["comment"] == "nocomment":
					item = QStandardItem("")
				else:
					item = QStandardItem(fname["comment"])
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
				item = QStandardItem(fname["user"])
				item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
				row.append(item)

				if publicFile:
					for k in row[1:]:
						iFont = k.font()
						iFont.setBold(True)
						k.setFont(iFont)
						k.setForeground(self.publicColor)

				model.appendRow(row)

		
		self.tw_aFiles.setModel(model)
		if psVersion == 1:
			self.tw_aFiles.horizontalHeader().setResizeMode(0,QHeaderView.Fixed)
			self.tw_aFiles.horizontalHeader().setResizeMode(2, QHeaderView.Stretch)
		else:
			self.tw_aFiles.horizontalHeader().setSectionResizeMode(0,QHeaderView.Fixed)
			self.tw_aFiles.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

		self.tw_aFiles.resizeColumnsToContents()
		self.tw_aFiles.horizontalHeader().setMinimumSectionSize(10)
		self.tw_aFiles.setColumnWidth(0,10*self.core.uiScaleFactor)
		self.tw_aFiles.setColumnWidth(1,100*self.core.uiScaleFactor)
		self.tw_aFiles.setColumnWidth(3,200*self.core.uiScaleFactor)
		self.tw_aFiles.setColumnWidth(4,100*self.core.uiScaleFactor)
		
		self.tw_aFiles.sortByColumn(twSorting[0], twSorting[1])


	@err_decorator
	def Assetclicked(self, item):
		if item is not None and item.childCount() == 0 and item.text(0) != None and item.text(2) == "asset":
			self.curAsset = item.text(1)
		else:
			self.curAsset = None

		self.refreshAssetinfo()
		self.refreshAStep()

		if self.gb_renderings.isVisible() and self.chb_autoUpdate.isChecked():
			self.updateTasks()


	@err_decorator
	def aPipelineclicked(self, current, prev):
		if current:
			self.curaStep = current.text()
		else:
			self.curaStep = None

		self.refreshaCat()


	@err_decorator
	def aCatclicked(self, current, prev):
		if self.core.compareVersions(self.core.projectVersion, "v1.2.1.6") == "lower":
			self.curaCat = "category"

		elif current:
			self.curaCat = current.text()

		else:
			self.curaCat = None

		self.refreshAFile()


	@err_decorator
	def refreshAssetinfo(self):
		pmap = None

		if self.curAsset:
			assetName = os.path.basename(self.curAsset)
			assetFile = os.path.join(os.path.dirname(self.core.prismIni), "Assetinfo", "assetInfo.yml")

			description = ""

			assetInfos = self.core.readYaml(assetFile)
			if not assetInfos:
				assetInfos = {}

			if assetName in assetInfos and "description" in assetInfos[assetName]:
				description = assetInfos[assetName]["description"]

			imgPath = os.path.join(os.path.dirname(self.core.prismIni), "Assetinfo", "%s_preview.jpg" % assetName)

			if os.path.exists(imgPath):
				pm = self.getImgPMap(imgPath)
				if pm.width() > 0 and pm.height() > 0:
					if (pm.width()/float(pm.height())) > 1.7778:
						pmap = pm.scaledToWidth(self.shotPrvXres)
					else:
						pmap = pm.scaledToHeight(self.shotPrvYres)
		else:
			curItem = self.tw_aHierarchy.currentItem()
			if not curItem:
				description = "No asset selected"
			else:
				description = "Folder selected"

		if pmap is None:
			pmap = self.emptypmapPrv

		self.l_aDescription.setText(description)
		self.l_assetPreview.setMinimumSize(pmap.width(), pmap.height())
		self.l_assetPreview.setPixmap(pmap)


	@err_decorator
	def getShots(self):
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

		searchFilter = ""
		if self.e_shotSearch.isVisible():
			searchFilter = self.e_shotSearch.text()

		for path in sorted(dirs):
			val = os.path.basename(path)
			if not val.startswith("_") and val not in self.omittedEntities["shot"]:
				shotName, seqName = self.splitShotname(val)

				if searchFilter not in seqName and searchFilter not in shotName:
					continue

				if shotName != "":
					shots.append([seqName, shotName, val])

				if seqName not in sequences:
					sequences.append(seqName)

		sequences = sorted(sequences)
		shots = sorted(shots, key=lambda x: self.core.naturalKeys(x[1]))

		if "no sequence" in sequences:
			sequences.insert(len(sequences), sequences.pop(sequences.index("no sequence")))

		return sequences, shots


	@err_decorator
	def splitShotname(self, shotName):
		if shotName and "-" in shotName:
			sname = shotName.split("-",1)
			seqName = sname[0]
			shotName = sname[1]
		else:
			seqName = "no sequence"
			shotName = shotName

		return shotName, seqName


	@err_decorator
	def refreshShots(self):
		self.tw_sShot.clear()

		sequences, shots = self.getShots()

		for seqName in sequences:
			seqItem = QTreeWidgetItem([seqName, seqName + "-"])
			self.tw_sShot.addTopLevelItem(seqItem)
			if seqName in self.sExpanded or self.e_shotSearch.isVisible():
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
		if self.e_shotSearch.isVisible():
			return

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
		self.lw_sPipeline.clear()

		if not self.cursShots:
			self.refreshsCat()
			return

		path = os.path.join(self.sBasePath, self.cursShots, "Scenefiles")

		if self.core.useLocalFiles:
			path = path.replace(self.core.localProjectPath, self.core.projectPath)
			lpath = path.replace(self.core.projectPath, self.core.localProjectPath)

		dirContent = []

		if os.path.exists(path):
			dirContent += [os.path.join(path,x) for x in os.listdir(path)]

		if self.core.useLocalFiles and os.path.exists(lpath):
			dirContent += [os.path.join(lpath,x) for x in os.listdir(lpath)]

		addedSteps = []
		for i in sorted(dirContent, key=lambda x: os.path.basename(x)):
			stepName = os.path.basename(i)
			if os.path.isdir(i) and stepName not in addedSteps:
				sItem = QListWidgetItem(stepName)
				self.lw_sPipeline.addItem(sItem)
				addedSteps.append(stepName)

		if self.lw_sPipeline.count() > 0:
			self.lw_sPipeline.setCurrentRow(0)
		else:
			self.cursCat = None
			self.refreshsCat()


	@err_decorator
	def refreshsCat(self):
		self.lw_sCategory.clear()

		if not self.cursStep:
			self.refreshSFile()
			return

		path = os.path.join(self.sBasePath, self.cursShots, "Scenefiles", self.cursStep)

		if self.core.useLocalFiles:
			path = path.replace(self.core.localProjectPath, self.core.projectPath)
			lpath = path.replace(self.core.projectPath, self.core.localProjectPath)

		dirContent = []

		if os.path.exists(path):
			dirContent += [os.path.join(path,x) for x in os.listdir(path)]

		if self.core.useLocalFiles and os.path.exists(lpath):
			dirContent += [os.path.join(lpath,x) for x in os.listdir(lpath)]

		addedCats = []
		for i in sorted(dirContent, key=lambda x: os.path.basename(x)):
			catName = os.path.basename(i)
			if os.path.isdir(i) and catName not in addedCats:
				sItem = QListWidgetItem(catName)
				self.lw_sCategory.addItem(sItem)
				addedCats.append(catName)

		if self.lw_sCategory.count() > 0:
			self.lw_sCategory.setCurrentRow(0)
		else:
			self.cursCat = None
			self.refreshSFile()


	@err_decorator
	def refreshSFile(self, parm=None):
		twSorting = [self.tw_sFiles.horizontalHeader().sortIndicatorSection(), self.tw_sFiles.horizontalHeader().sortIndicatorOrder()]

		model = QStandardItemModel()

		model.setHorizontalHeaderLabels(["", self.tableColumnLabels["Version"], self.tableColumnLabels["Comment"], self.tableColumnLabels["Date"], self.tableColumnLabels["User"]])
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
				fname = self.core.getScenefileData(i)
				tmpScene = False
				try:
					x = int(fname["extension"][-5:])
					tmpScene = True
				except:
					pass
				if fname["type"] == "shot" and fname["extension"] in appfilter and not tmpScene:
					publicFile = self.core.useLocalFiles and i.startswith(os.path.join(self.core.projectPath, self.scenes, "Shots"))

					if pVersion == 2:
						item = QStandardItem(unicode("█", "utf-8"))
					else:
						item = QStandardItem("█")
					item.setFont(QFont('SansSerif', 100))
					item.setFlags(~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
					item.setData(i, Qt.UserRole)

					colorVals = [128,128,128]
					if fname["extension"] in self.core.appPlugin.sceneFormats:
						colorVals = self.core.appPlugin.appColor
					else:
						for k in self.core.unloadedAppPlugins.values():
							if fname["extension"] in k.sceneFormats:
								colorVals = k.appColor

					item.setForeground(QColor(colorVals[0], colorVals[1], colorVals[2]))

					row.append(item)
					item = QStandardItem(fname["version"])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
					if fname["comment"] == "nocomment":
						item = QStandardItem("")
					else:
						item = QStandardItem(fname["comment"])
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
					item = QStandardItem(fname["user"])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)

					if publicFile:
						for k in row[1:]:
							iFont = k.font()
							iFont.setBold(True)
							k.setFont(iFont)
							k.setForeground(self.publicColor)

					model.appendRow(row)

		self.tw_sFiles.setModel(model)
		if psVersion == 1:
			self.tw_sFiles.horizontalHeader().setResizeMode(0,QHeaderView.Fixed)
			self.tw_sFiles.horizontalHeader().setResizeMode(2, QHeaderView.Stretch)
		else:
			self.tw_sFiles.horizontalHeader().setSectionResizeMode(0,QHeaderView.Fixed)
			self.tw_sFiles.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

		self.tw_sFiles.resizeColumnsToContents()
		self.tw_sFiles.horizontalHeader().setMinimumSectionSize(10)
		self.tw_sFiles.setColumnWidth(0,10*self.core.uiScaleFactor)
		self.tw_sFiles.setColumnWidth(1,100*self.core.uiScaleFactor)
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
	def sPipelineclicked(self, current, prev):
		if current:
			self.cursStep = current.text()
		else:
			self.cursStep = None

		self.refreshsCat()


	@err_decorator
	def sCatclicked(self, current, prev):
		if current:
			self.cursCat = current.text()
		else:
			self.cursCat = None

		self.refreshSFile()


	@err_decorator
	def refreshShotinfo(self):
		pmap = None

		if self.cursShots is not None:
			startFrame = "?"
			endFrame = "?"

			shotRange = self.core.getShotRange(self.cursShots)
			if shotRange:
				startFrame, endFrame = shotRange

			shotName, seqName = self.splitShotname(self.cursShots)
			if not shotName and seqName:
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
	def rclEntityPreview(self, pos, entity):
		rcmenu = QMenu()

		if entity == "asset":
			if not self.curAsset:
				return

			exp = QAction("Edit asset description", self)
			exp.triggered.connect(lambda: self.editAsset(self.curAsset))
			rcmenu.addAction(exp)

			copAct = QAction("Capture assetpreview", self)
			copAct.triggered.connect(lambda: self.captureEntityPreview("asset", self.curAsset))
			rcmenu.addAction(copAct)
		else:
			shotName, seqName = self.splitShotname(self.cursShots)
			if not shotName:
				return

			exp = QAction("Edit shotinfo", self)
			exp.triggered.connect(lambda: self.editShot(self.cursShots))
			rcmenu.addAction(exp)

			copAct = QAction("Capture shotpreview", self)
			copAct.triggered.connect(lambda: self.captureEntityPreview("shot", self.cursShots))
			rcmenu.addAction(copAct)

		self.core.appPlugin.setRCStyle(self, rcmenu)
		rcmenu.exec_(QCursor.pos())


	@err_decorator
	def captureEntityPreview(self, entity, entityname):
		if entity == "asset":
			folderName = "Assetinfo"
			entityname = os.path.basename(entityname)
			refresh = self.refreshAssetinfo
		else:
			folderName = "Shotinfo"
			refresh = self.refreshShotinfo

		from PrismUtils import ScreenShot
		previewImg = ScreenShot.grabScreenArea(self.core)

		if previewImg:
			if (previewImg.width()/float(previewImg.height())) > 1.7778:
				pmsmall = previewImg.scaledToWidth(self.shotPrvXres)
			else:
				pmsmall = previewImg.scaledToHeight(self.shotPrvYres)

			prvPath = os.path.join(os.path.dirname(self.core.prismIni), folderName, "%s_preview.jpg" % entityname)
			self.savePMap(pmsmall, prvPath)

			refresh()


	@err_decorator
	def editAsset(self, assetName=None):
		if not assetName:
			return

		assetName = os.path.basename(assetName)

		descriptionDlg = EnterText.EnterText()
		self.core.parentWindow(descriptionDlg)
		descriptionDlg.setWindowTitle("Enter description")
		descriptionDlg.l_info.setText("Description:")
		descriptionDlg.te_text.setPlainText(self.l_aDescription.text())

		c = descriptionDlg.te_text.textCursor()
		c.setPosition(0);
		c.setPosition(len(self.l_aDescription.text()), QTextCursor.KeepAnchor)
		descriptionDlg.te_text.setTextCursor(c)

		result = descriptionDlg.exec_()

		if result:
			description = descriptionDlg.te_text.toPlainText()
			self.l_aDescription.setText(description)

			assetFile = os.path.join(os.path.dirname(self.core.prismIni), "Assetinfo", "assetInfo.yml")
			assetInfos = self.core.readYaml(assetFile)
			if not assetInfos:
				assetInfos = {}

			if assetName not in assetInfos:
				assetInfos[assetName] = {}

			assetInfos[assetName]["description"] = description

			self.core.writeYaml(assetFile, assetInfos)


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
		sName, seqName = self.splitShotname(shotName)
		if not sName:
			self.es.setWindowTitle("Create Shot")

			if self.cursShots is not None:
				sName, seqName = self.splitShotname(self.cursShots)
				if seqName != "no sequence":
					self.es.e_sequence.setText(seqName)
				self.es.e_shotName.setFocus()

		self.core.callback(name="onShotDlgOpen", types=["custom"], args=[self, self.es, shotName])

		result = self.es.exec_()

		if result != 1 or self.es.shotName is None:
			return

		if shotName is None:
			return

		self.refreshShots()

		shotName, seqName = self.splitShotname(self.es.shotName)

		for i in range(self.tw_sShot.topLevelItemCount()):
			sItem = self.tw_sShot.topLevelItem(i)
			if sItem.text(0) == seqName:
				sItem.setExpanded(True)
				for k in range(sItem.childCount()):
					shotItem = sItem.child(k)
					if shotItem.text(0) == shotName:
						self.tw_sShot.setCurrentItem(shotItem)


	@err_decorator
	def createShot(self, shotName, frameRange=None):
		result = self.createShotFolders(shotName, "shot")

		if result == True or not result:
			return result

		if frameRange:
			shotFile = os.path.join(os.path.dirname(self.core.prismIni), "Shotinfo", "shotInfo.ini")

			if not os.path.exists(os.path.dirname(shotFile)):
				os.makedirs(os.path.dirname(shotFile))

			if not os.path.exists(shotFile):
				open(shotFile, 'a').close()

			sconfig = ConfigParser()
			try:
				sconfig.read(shotFile)
			except:
				pass
			else:
				if not sconfig.has_section("shotRanges"):
					sconfig.add_section("shotRanges")

				sconfig.set("shotRanges", shotName, str(frameRange))

				with open(shotFile, 'w') as inifile:
					sconfig.write(inifile)

		if self.core.uiAvailable:
			self.refreshShots()

		shotName, seqName = self.splitShotname(shotName)

		self.core.callback(name="onShotCreated", types=["custom"], args=[self, seqName, shotName])

		if self.core.uiAvailable:
			for i in range(self.tw_sShot.topLevelItemCount()):
				sItem = self.tw_sShot.topLevelItem(i)
				if sItem.text(0) == seqName:
					sItem.setExpanded(True)
					for k in range(sItem.childCount()):
						shotItem = sItem.child(k)
						if shotItem.text(0) == shotName:
							self.tw_sShot.setCurrentItem(shotItem)

		return result


	@err_decorator
	def showShotSearch(self):
		self.l_shotSearch.setVisible(True)


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

		model.setHorizontalHeaderLabels(["", self.tableColumnLabels["Name"], self.tableColumnLabels["Step"], self.tableColumnLabels["Version"], self.tableColumnLabels["Comment"], self.tableColumnLabels["Date"], self.tableColumnLabels["User"], "Filepath"])
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
			fname = self.core.getScenefileData(i)
			if os.path.exists(i):
				if pVersion == 2:
					item = QStandardItem(unicode("█", "utf-8"))
				else:
					item = QStandardItem("█")
				item.setFont(QFont('SansSerif', 100))
				item.setFlags(~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
				item.setData(i, Qt.UserRole)

				colorVals = [128,128,128]
				if fname["extension"] in self.core.appPlugin.sceneFormats:
					colorVals = self.core.appPlugin.appColor
				else:
					for k in self.core.unloadedAppPlugins.values():
						if fname["extension"] in k.sceneFormats:
							colorVals = k.appColor

				item.setForeground(QColor(colorVals[0], colorVals[1], colorVals[2]))

				row.append(item)
				if fname["type"] == "asset":
					item = QStandardItem(fname["assetName"])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
					item = QStandardItem(fname["step"])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
					item = QStandardItem(fname["version"])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
					if fname["comment"] == "nocomment":
						item = QStandardItem("")
					else:
						item = QStandardItem(fname["comment"])
					row.append(item)
					cdate = datetime.datetime.fromtimestamp(os.path.getmtime(i))
					cdate = cdate.replace(microsecond = 0)
					cdate = cdate.strftime("%d.%m.%y,  %X")
					item = QStandardItem(str(cdate))
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					item.setData(QDateTime.fromString( cdate, "dd.MM.yy,  hh:mm:ss").addYears(100), 0)
				#	item.setToolTip(cdate)
					row.append(item)
					item = QStandardItem(fname["user"])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
				elif fname["type"] == "shot":
					item = QStandardItem(fname["shotName"])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
					item = QStandardItem(fname["step"])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
					item = QStandardItem(fname["version"])
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					row.append(item)
					if fname["comment"] == "nocomment":
						item = QStandardItem("")
					else:
						item = QStandardItem(fname["comment"])
					row.append(item)
					cdate = datetime.datetime.fromtimestamp(os.path.getmtime(i))
					cdate = cdate.replace(microsecond = 0)
					cdate = cdate.strftime("%d.%m.%y,  %X")
					item = QStandardItem(str(cdate))
					item.setTextAlignment(Qt.Alignment(Qt.AlignCenter))
					item.setData(QDateTime.fromString( cdate, "dd.MM.yy,  hh:mm:ss").addYears(100), 0)
				#	item.setToolTip(cdate)
					row.append(item)
					item = QStandardItem(fname["user"])
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
		self.tw_recent.horizontalHeader().setMinimumSectionSize(10)
		self.tw_recent.setColumnWidth(0,10*self.core.uiScaleFactor)
	#	self.tw_recent.setColumnWidth(2,40*self.core.uiScaleFactor)
	#	self.tw_recent.setColumnWidth(3,60*self.core.uiScaleFactor)
	#	self.tw_recent.setColumnWidth(6,50*self.core.uiScaleFactor)

		if psVersion == 1:
			self.tw_recent.horizontalHeader().setResizeMode(0,QHeaderView.Fixed)
		else:
			self.tw_recent.horizontalHeader().setSectionResizeMode(0,QHeaderView.Fixed)


	@err_decorator
	def refreshCurrent(self):
		if self.tbw_browser.currentWidget().property("tabType") == "Assets":
			self.refreshAFile()
		elif self.tbw_browser.currentWidget().property("tabType") == "Shots":
			self.refreshSFile()
		elif self.tbw_browser.currentWidget().property("tabType") == "Files":
			self.refreshFCat()
		elif self.tbw_browser.currentWidget().property("tabType") == "Recent":
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
	def triggerAutoplay(self, checked=False, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		self.core.setConfig('browser', "autoplaypreview", str(checked))

		if "timeline" in mediaPlayback:
			if checked and mediaPlayback["timeline"].state() == QTimeLine.Paused:
				mediaPlayback["timeline"].setPaused(False)
			elif not checked and mediaPlayback["timeline"].state() == QTimeLine.Running:
				mediaPlayback["timeline"].setPaused(True)
		else:
			mediaPlayback["tlPaused"] = not checked


	@err_decorator
	def triggerAssets(self, checked=False):
		if checked:
			self.tbw_browser.insertTab(self.tabOrder["Assets"]["order"], self.t_assets, self.tabLabels["Assets"])
			if self.tbw_browser.count() == 1:
				self.tbw_browser.setVisible(True)
		else:
			self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_assets))
			if self.tbw_browser.count() == 0:
				self.tbw_browser.setVisible(False)


	@err_decorator
	def triggerShots(self, checked=False):
		if checked:
			self.tbw_browser.insertTab(self.tabOrder["Shots"]["order"], self.t_shots, self.tabLabels["Shots"])
			if self.tbw_browser.count() == 1:
				self.tbw_browser.setVisible(True)
		else:
			self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_shots))
			if self.tbw_browser.count() == 0:
				self.tbw_browser.setVisible(False)


	@err_decorator
	def triggerFiles(self, checked=False):
		if checked:
			self.tbw_browser.insertTab(self.tabOrder["Files"]["order"], self.t_files, self.tabLabels["Files"])
			if self.tbw_browser.count() == 1:
				self.tbw_browser.setVisible(True)
		else:
			self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_files))
			if self.tbw_browser.count() == 0:
				self.tbw_browser.setVisible(False)



	@err_decorator
	def triggerRecent(self, checked=False):
		if checked:
			self.tbw_browser.insertTab(self.tabOrder["Recent"]["order"], self.t_recent, self.tabLabels["Recent"])
			if self.tbw_browser.count() == 1:
				self.tbw_browser.setVisible(True)
		else:
			self.tbw_browser.removeTab(self.tbw_browser.indexOf(self.t_recent))
			if self.tbw_browser.count() == 0:
				self.tbw_browser.setVisible(False)


	@err_decorator
	def triggerRenderings(self, checked=False):
		if self.tbw_browser.currentWidget() and self.tabOrder[self.tbw_browser.currentWidget().property("tabType")]["showRenderings"]:
			self.gb_renderings.setVisible(checked)


	@err_decorator
	def createCatWin(self, tab, name):
		self.newItem = CreateItem.CreateItem(core=self.core, showType=tab=="ah")

		self.newItem.setModal(True)
		self.core.parentWindow(self.newItem)
		self.newItem.e_item.setFocus()
		self.newItem.setWindowTitle("Create " + name)
		nameLabel = "Name:" if name == "Entity" else name + " Name:"
		self.newItem.l_item.setText(nameLabel)
		self.newItem.buttonBox.accepted.connect(lambda: self.createCat(tab))

		if tab == "ah":
			self.core.callback(name="onAssetDlgOpen", types=["custom"], args=[self, self.newItem])
		elif tab == "sc":
			self.core.callback(name="onCategroyDlgOpen", types=["custom"], args=[self, self.newItem])

		self.newItem.show()


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
		elif tab == "ac":
			path = os.path.join(self.curAsset, "Scenefiles", self.curaStep)
			refresh = self.refreshaCat
			uielement = self.lw_aCategory
			self.curaCat = self.itemName
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
			self.createShotFolders(assetPath, "asset")
			self.core.callback(name="onAssetCreated", types=["custom"], args=[self, self.itemName, path, self.newItem])
			for i in self.core.prjManagers.values():
				i.assetCreated(self, self.newItem, assetPath)
		elif tab == "sc":
			catPath = os.path.join(path, self.itemName)
			self.createCategory(self.itemName, catPath)
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
		if ftype == "asset":
			basePath = self.aBasePath
			fname = fname.replace(self.aBasePath, "")
			if fname[0] in ["/", "\\"]:
				fname = fname[1:]
		else:
			basePath = self.sBasePath

		sBase = os.path.join(basePath, fname)
		sFolders = []
		sFolders.append(os.path.join(sBase, "Scenefiles"))
		sFolders.append(os.path.join(sBase, "Export"))
		sFolders.append(os.path.join(sBase, "Playblasts"))
		sFolders.append(os.path.join(sBase, "Rendering", "3dRender"))
		sFolders.append(os.path.join(sBase, "Rendering", "2dRender"))

		if os.path.exists(sBase):
			if fname in self.omittedEntities[ftype] and self.core.uiAvailable:
				msgText = "The %s %s already exists, but is marked as omitted.\n\nDo you want to restore it?" % (ftype, fname)
				if psVersion == 1:
					flags = QMessageBox.StandardButton.Yes
					flags |= QMessageBox.StandardButton.No
					result = QMessageBox.question(self.core.messageParent, "Warning", msgText, flags)
				else:
					result = QMessageBox.question(self.core.messageParent, "Warning", msgText)

				if str(result).endswith(".Yes"):
					omitPath = os.path.join(os.path.dirname(self.core.prismIni), "Configs", "omits.ini")
					items = self.core.getConfig(ftype, configPath=omitPath, getItems=True)
					eItem = [ x[0] for x in items if x[1] == fname]
					if len(eItem) > 0:
						self.core.setConfig(ftype, eItem[0], configPath=omitPath, delete=True)
				else:
					return
			else:
				self.core.popup("The %s %s already exists" % (ftype, fname))
				return True

		for i in sFolders:
			if not os.path.exists(i):
				os.makedirs(i)

		return sBase


	@err_decorator
	def createStepWindow(self, tab):
		if tab == "a":
			basePath = os.path.join(self.curAsset, "Scenefiles")
		elif tab == "s":
			basePath = os.path.join(self.sBasePath, self.cursShots, "Scenefiles")
		else:
			return

		try:
			steps = ast.literal_eval(self.core.getConfig('globals', "pipeline_steps", configPath=self.core.prismIni))
		except:
			QMessageBox.warning(self.core.messageParent, "Warning", "Could not read steps from configuration file.\nCheck this file for errors:\n\n%s" % self.core.prismIni)
			return

		if type(steps) != dict:
			steps = {}

		steps = {validSteps : steps[validSteps] for validSteps in steps if not os.path.exists(os.path.join(basePath, validSteps))}
		steps = self.getStep(steps, tab)
		if steps != False:
			createdDirs = []

			if tab == "s":
				entity = "shot"
			else:
				entity = "asset"

			for i in steps[0]:
				dstname = os.path.join(basePath, i)
				result = self.createStep(i, entity, stepPath=dstname, createCat=steps[1])
				if result:
					createdDirs.append(i)
				
			if len(createdDirs) != 0:
				if tab == "a":
					self.curaStep = createdDirs[0]
					self.refreshAHierarchy()
					self.navigateToCurrent(path=dstname)
				elif tab == "s":
					self.cursStep = createdDirs[0]
					self.refreshsStep()
					for i in range(self.lw_sPipeline.model().rowCount()):
						if self.lw_sPipeline.model().index(i,0).data() == createdDirs[0]:
							self.lw_sPipeline.selectionModel().setCurrentIndex( self.lw_sPipeline.model().index(i,0) , QItemSelectionModel.ClearAndSelect)


	@err_decorator
	def createStep(self, stepName, entity="shot", entityName="", stepPath="", createCat=True):
		if not stepPath:
			if entity == "asset":
				for i in self.core.getAssetPaths():
					if os.path.basename(i) == entityName:
						stepPath = os.path.join(i, "Scenefiles", stepName)
						break
				else:
					self.core.popup("Asset '%s' doesn't exist. Could not create step." % entityName)
					return

			elif entity == "shot":
				stepPath = os.path.join(self.sBasePath, entityName, "Scenefiles", stepName)

		if not os.path.exists(stepPath):
			try:
				os.makedirs(stepPath)
			except:
				self.core.popup("The directory %s could not be created" % stepName)
				return False

		settings = {"createDefaultCategory": (entity == "shot" or self.core.compareVersions(self.core.projectVersion, "v1.2.1.6") != "lower") and createCat}

		self.core.callback(name="onStepCreated", types=["custom"], args=[self, entity, stepName, stepPath, settings])

		if settings["createDefaultCategory"]:
			path = self.createDefaultCat(stepName, stepPath)
			return path

		return stepPath


	@err_decorator
	def createDefaultCat(self, step, path):
		existingSteps = ast.literal_eval(self.core.getConfig('globals', "pipeline_steps", configPath=self.core.prismIni))
		if step not in existingSteps:
			QMessageBox.warning(self.core.messageParent, "Warning", "Step '%s' doesn't exist in the project config. Couldn't create default category." % step)
			return

		catName = existingSteps[step]
		dstname = os.path.join(path, catName)
		path  = self.createCategory(catName, dstname)
		return path


	@err_decorator
	def createCategory(self, catName, path):
		if os.path.basename(path) != catName:
			path = os.path.join(path, catName)

		if not os.path.exists(path):
			try:
				os.makedirs(path)
			except:
				QMessageBox.warning(self.core.messageParent,"Warning", ("The directory %s could not be created" % path))
				return
			else:
				self.core.callback(name="onCategoryCreated", types=["custom"], args=[self, catName, path])
		
		return path


	@err_decorator
	def openFFile(self):
		if self.fbottom:
			self.core.openFolder(self.fpath + self.fclickedon)
		else:
			self.core.openFolder(self.fpath)


	@err_decorator
	def copyToGlobal(self, localPath, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		dstPath = localPath.replace(self.core.localProjectPath, self.core.projectPath)

		if os.path.isdir(localPath):
			if os.path.exists(dstPath):
				for i in os.walk(dstPath):
					if i[2] != []:
						QMessageBox.information(self.core.messageParent, "Copy to global", "Found existing files in the global directory. Copy to global was canceled.")
						return

				shutil.rmtree(dstPath)

			shutil.copytree(localPath, dstPath)
			
			if "vidPrw" in mediaPlayback and not mediaPlayback["vidPrw"].closed:
				for i in range(6):
					mediaPlayback["vidPrw"].close()
					time.sleep(0.5)
					if mediaPlayback["vidPrw"].closed:
						break

			try:
				shutil.rmtree(localPath)
			except:
				QMessageBox.warning(self.core.messageParent, "Copy to global", "Could not delete the local file. Probably it is used by another process.")

			curTab = self.tbw_browser.currentWidget().property("tabType")
			curData = [curTab, self.cursShots, self.curRTask, self.curRVersion, self.curRLayer]
			self.updateTasks()
			self.showRender(curData[0], curData[1], curData[2], curData[3].replace(" (local)", ""), curData[4])
		else:
			if not os.path.exists(os.path.dirname(dstPath)):
				os.makedirs(os.path.dirname(dstPath))

			self.core.copySceneFile(localPath, dstPath)

			if self.tbw_browser.currentWidget().property("tabType") == "Assets":
				self.refreshAFile()
			elif self.tbw_browser.currentWidget().property("tabType") == "Shots":
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

			if eType == "asset":
				self.refreshAHierarchy()
			elif eType == "shot":
				self.refreshShots()


	@err_decorator
	def refreshOmittedEntities(self):
		self.omittedEntities = {"asset":[], "shot":[]}
		omitPath = os.path.join(os.path.dirname(self.core.prismIni), "Configs", "omits.ini")
		if os.path.exists(omitPath):
			oconfig = ConfigParser()
			oconfig.read(omitPath)

			if oconfig.has_section("Shot"):
				self.omittedEntities["shot"] = [x[1] for x in oconfig.items("Shot")]

			if oconfig.has_section("Asset"):
				self.omittedEntities["asset"] = [x[1] for x in oconfig.items("Asset")]


	@err_decorator
	def navigateToCurrent(self, path=None):
		if path is None:
			fileName = self.core.getCurrentFileName()
			fileNameData = self.core.getScenefileData(fileName)
		else:
			fileName = path
			fileNameData = {"type":"invalid"}

		if os.path.join(self.core.projectPath, self.scenes) in fileName or (self.core.useLocalFiles and os.path.join(self.core.localProjectPath, self.scenes) in fileName):
			if fileNameData["type"] == "asset" or self.aBasePath in fileName or (self.core.useLocalFiles and (self.aBasePath.replace(self.core.projectPath, self.core.localProjectPath) in fileName)):
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

				if endIdx is not None and endIdx < len(hierarchy):
					stepName = hierarchy[endIdx]
					fItems = self.lw_aPipeline.findItems(stepName, Qt.MatchExactly)
					if len(fItems) > 0:
						self.lw_aPipeline.setCurrentItem(fItems[0])
						if len(hierarchy) > (endIdx + 1):
							for i in range(self.tw_aFiles.model().rowCount()):
								if fileName == self.tw_aFiles.model().index(i,0).data(Qt.UserRole):
									idx = self.tw_aFiles.model().index(i,0)
									self.tw_aFiles.selectRow(idx.row())
									break

			elif (fileNameData["type"] == "shot" or self.sBasePath in fileName or (self.core.useLocalFiles and self.sBasePath.replace(self.core.projectPath, self.core.localProjectPath) in fileName)) and self.tw_sShot.topLevelItemCount() > 0:
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

				shotName, seqName = self.splitShotname(shotName)

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
							if fileName == self.tw_sFiles.model().index(i,0).data(Qt.UserRole):
								idx = self.tw_sFiles.model().index(i,0)
								self.tw_sFiles.selectRow(idx.row())
								break


	@err_decorator
	def updateChanged(self, state):
		if state:
			self.updateTasks()


	@err_decorator
	def refreshRender(self):
		curTab = self.tbw_browser.currentWidget().property("tabType")
		curData = [curTab, self.cursShots, self.curRTask, self.curRVersion, self.curRLayer]
		self.updateTasks()
		self.showRender(curData[0], curData[1], curData[2], curData[3], curData[4])


	@err_decorator
	def getMediaTasks(self, entityName=None, entityType=None):
		mediaTasks = {"3d":[], "2d":[], "playblast":[], "external":[]}

		if entityType is None:
			if not self.tbw_browser.currentWidget():
				return mediaTasks

			entityType = self.tbw_browser.currentWidget().property("tabType")

		foldercont = []
		self.renderBasePath = None

		if entityName is None:
			if entityType == "Assets":
				if self.curAsset:
					self.renderBasePath = self.curAsset
			elif entityType == "Shots" and self.cursShots is not None:
				self.renderBasePath = os.path.join(self.core.projectPath, self.scenes, "Shots", self.cursShots)
		else:
			if entityType == "Assets":
				pass
			elif entityType == "Shots":
				self.renderBasePath = os.path.join(self.core.projectPath, self.scenes, "Shots", entityName)

		if self.renderBasePath is not None:
			for i in os.walk(os.path.join(self.renderBasePath, "Rendering", "3dRender")):
				for k in sorted(i[1]):
					mediaTasks["3d"].append([k, "3d", os.path.join(i[0], k)])
				break

			for i in os.walk(os.path.join(self.renderBasePath, "Rendering", "2dRender")):
				for k in sorted(i[1]):
					mediaTasks["2d"].append([k +" (2d)", "2d", os.path.join(i[0], k)])
				break

			for i in os.walk(os.path.join(self.renderBasePath, "Rendering", "external")):
				for k in sorted(i[1]):
					mediaTasks["external"].append([k +" (external)", "external", os.path.join(i[0], k)])
				break

			for i in os.walk(os.path.join(self.renderBasePath, "Playblasts")):
				for k in sorted(i[1]):
					mediaTasks["playblast"].append([k +" (playblast)", "playblast", os.path.join(i[0], k)])
				break

			if self.core.useLocalFiles:
				for i in os.walk(os.path.join(self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath), "Rendering", "3dRender")):
					for k in sorted(i[1]):
						tname = k + " (local)"
						taskNames = [x[0] for x in mediaTasks["3d"]]
						if tname not in taskNames and k not in taskNames:
							mediaTasks["3d"].append([tname, "3d", os.path.join(i[0], k)])
					break

				for i in os.walk(os.path.join(self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath), "Rendering", "2dRender")):
					for k in sorted(i[1]):
						tname = k + " (2d)"
						taskNames = [x[0] for x in mediaTasks["2d"]]
						if tname not in mediaTasks["2d"]:
							mediaTasks["2d"].append([tname, "2d", os.path.join(i[0], k)])
					break

				for i in os.walk(os.path.join(self.renderBasePath.replace(self.core.projectPath, self.core.localProjectPath), "Playblasts")):
					for k in sorted(i[1]):
						tname = k + " (playblast)"
						taskNames = [x[0] for x in mediaTasks["playblast"]]
						if tname not in mediaTasks["playblast"]:
							mediaTasks["playblast"].append([tname, "playblast", os.path.join(i[0], k)])
					break

		return mediaTasks


	@err_decorator
	def updateTasks(self):
		self.renderRefreshEnabled = False

		self.curRTask = ""
		self.lw_task.clear()

		mediaTasks = self.getMediaTasks()
		taskNames = []
		for i in ["3d", "2d", "playblast", "external"]:
			taskNames += sorted(list({x[0] for x in mediaTasks[i]}))
		
		self.lw_task.addItems(taskNames)

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
			foldercont = self.getRenderVersions(task=self.curRTask)
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
	def getRenderVersions(self, task="", taskPath=None):
		foldercont = []

		if taskPath is None:
			if self.renderBasePath is None:
				return foldercont

			if task.endswith(" (playblast)"):
				taskPath = os.path.join(self.renderBasePath, "Playblasts", task.replace(" (playblast)", ""))
			elif task.endswith(" (2d)"):
				taskPath = os.path.join(self.renderBasePath, "Rendering", "2dRender", task.replace(" (2d)", ""))
			elif task.endswith(" (external)"):
				taskPath = os.path.join(self.renderBasePath, "Rendering", "external", task.replace(" (external)", ""))
			else:
				taskPath = os.path.join(self.renderBasePath, "Rendering", "3dRender", task.replace(" (local)", ""))

		for i in os.walk(taskPath):
			foldercont = i[1]
			break

		if self.core.useLocalFiles:
			for i in os.walk(taskPath.replace(self.core.projectPath, self.core.localProjectPath)):
				for k in i[1]:
					foldercont.append(k +" (local)")
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
	def getShotMediaPath(self):
		foldercont = [None, None, None]
		if len(self.lw_task.selectedItems()) > 1 or len(self.lw_version.selectedItems()) > 1:
			mediaPlayback = self.mediaPlaybacks["shots"]

			mediaPlayback["l_info"].setText("Multiple items selected")
			mediaPlayback["l_info"].setToolTip("")
			mediaPlayback["l_date"].setText("")
			self.b_addRV.setEnabled(True)
			self.b_compareRV.setEnabled(True)
			self.b_combineVersions.setEnabled(True)
			return ["multiple", None, None]
		else:
			self.b_addRV.setEnabled(False)
			if len(self.compareStates) == 0:
				self.b_compareRV.setEnabled(False)
				self.b_combineVersions.setEnabled(False)

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

		return foldercont


	@err_decorator
	def updatePreview(self, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		if "timeline" in mediaPlayback:
			if mediaPlayback["timeline"].state() != QTimeLine.NotRunning:
				if mediaPlayback["timeline"].state() == QTimeLine.Running:
					mediaPlayback["tlPaused"] = False
				elif mediaPlayback["timeline"].state() == QTimeLine.Paused:
					mediaPlayback["tlPaused"] = True
				mediaPlayback["timeline"].stop()
		else:
			mediaPlayback["tlPaused"] = not self.actionAutoplay.isChecked()

		mediaPlayback["sl_preview"].setValue(0)
		mediaPlayback["prevCurImg"] = 0
		mediaPlayback["curImg"] = 0
		mediaPlayback["seq"] = []
		mediaPlayback["prvIsSequence"] = False

		QPixmapCache.clear()

		mediaBase, mediaFolders, mediaFiles = mediaPlayback["getMediaBase"]()

		if mediaBase != "multiple":
			if mediaBase is not None:
				mediaPlayback["basePath"] = mediaBase
				base = None
				for i in sorted(mediaFiles):
					if os.path.splitext(i)[1] in [".jpg", ".jpeg", ".JPG", ".png", ".tif", ".tiff", ".exr", ".dpx", ".mp4", ".mov"]:
						base = i
						break

				if base is not None:
					baseName, extension = os.path.splitext(base)
					for i in sorted(mediaFiles):
						if i.startswith(baseName[:-4]) and (i.endswith(extension)):
							mediaPlayback["seq"].append(i)

					if len(mediaPlayback["seq"]) > 1 and extension not in [".mp4", ".mov"]:
						mediaPlayback["prvIsSequence"] = True
						try:
							mediaPlayback["pstart"] = int(baseName[-4:])
						except:
							mediaPlayback["pstart"] = "?"

						try:
							mediaPlayback["pend"] = int(os.path.splitext(mediaPlayback["seq"][len(mediaPlayback["seq"])-1])[0][-4:])
						except:
							mediaPlayback["pend"] = "?"

					else:
						mediaPlayback["prvIsSequence"] = False
						mediaPlayback["seq"] = []
						for i in mediaFiles:
							if os.path.splitext(i)[1] in [".jpg", ".jpeg", ".JPG", ".png", ".tif", ".tiff", ".exr", ".dpx", ".mp4", ".mov"]:
								mediaPlayback["seq"].append(i)

					if not (self.curRTask == "" or self.curRVersion == "" or len(mediaPlayback["seq"]) == 0):
						self.b_addRV.setEnabled(True)

					mediaPlayback["pduration"] = len(mediaPlayback["seq"])
					imgPath = str(os.path.join(mediaBase, base))
					if os.path.exists(imgPath) and mediaPlayback["pduration"] == 1 and os.path.splitext(imgPath)[1] in [".mp4", ".mov"]:
						if os.stat(imgPath).st_size == 0:
							mediaPlayback["vidPrw"] = "Error"
						else:
							try:
								mediaPlayback["vidPrw"] = imageio.get_reader(imgPath,  'ffmpeg')
							except:
								mediaPlayback["vidPrw"] = "Error"

						self.updatePrvInfo(imgPath, vidReader=mediaPlayback["vidPrw"], mediaPlayback=mediaPlayback)
					else:
						self.updatePrvInfo(imgPath, mediaPlayback=mediaPlayback)

					if os.path.exists(imgPath):
						mediaPlayback["timeline"] = QTimeLine(mediaPlayback["pduration"]*40, self)
						mediaPlayback["timeline"].setFrameRange(0, mediaPlayback["pduration"]-1)
						mediaPlayback["timeline"].setEasingCurve(QEasingCurve.Linear)
						mediaPlayback["timeline"].setLoopCount(0)
						mediaPlayback["timeline"].frameChanged.connect(lambda x: self.changeImg(x, mediaPlayback=mediaPlayback))
						QPixmapCache.setCacheLimit(2097151)
						mediaPlayback["curImg"] = 0
						mediaPlayback["timeline"].start()


						if mediaPlayback["tlPaused"]:
							mediaPlayback["timeline"].setPaused(True)
							self.changeImg(mediaPlayback=mediaPlayback)
						elif mediaPlayback["pduration"] < 3:
							self.changeImg(mediaPlayback=mediaPlayback)

						return True
				else:
					self.updatePrvInfo(mediaPlayback=mediaPlayback)
			else:
				self.updatePrvInfo(mediaPlayback=mediaPlayback)

		mediaPlayback["l_preview"].setPixmap(self.emptypmap)
		mediaPlayback["sl_preview"].setEnabled(False)


	@err_decorator
	def updatePrvInfo(self, prvFile="", vidReader=None, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		if not os.path.exists(prvFile):
			mediaPlayback["l_info"].setText("No image found")
			mediaPlayback["l_info"].setToolTip("")
			mediaPlayback["l_date"].setText("")
			mediaPlayback["l_preview"].setToolTip("")
			return

		mediaPlayback["pwidth"], mediaPlayback["pheight"] = self.getMediaResolution(prvFile, vidReader=vidReader, setDuration=True, mediaPlayback=mediaPlayback)

		mediaPlayback["pformat"] = "*" + os.path.splitext(prvFile)[1]

		cdate = datetime.datetime.fromtimestamp(os.path.getmtime(prvFile))
		cdate = cdate.replace(microsecond = 0)
		pdate = cdate.strftime("%d.%m.%y,  %X")

		mediaPlayback["sl_preview"].setEnabled(True)

		if mediaPlayback["pduration"] == 1:
			frStr = "frame"
		else:
			frStr = "frames"

		if mediaPlayback["prvIsSequence"]:
			infoStr = "%sx%s   %s   %s-%s (%s %s)" % (mediaPlayback["pwidth"], mediaPlayback["pheight"], mediaPlayback["pformat"], mediaPlayback["pstart"], mediaPlayback["pend"], mediaPlayback["pduration"], frStr)
		elif len(mediaPlayback["seq"]) > 1:
			infoStr = "%s files %sx%s   %s   %s" % (mediaPlayback["pduration"], mediaPlayback["pwidth"], mediaPlayback["pheight"], mediaPlayback["pformat"], os.path.basename(prvFile))
		elif os.path.splitext(mediaPlayback["seq"][0])[1] in [".mp4", ".mov"]:
			if mediaPlayback["pwidth"] == "?":
				duration = "?"
				frStr = "frames"
			else:
				duration = mediaPlayback["pduration"]

			infoStr = "%sx%s   %s   %s %s" % (mediaPlayback["pwidth"], mediaPlayback["pheight"], mediaPlayback["seq"][0], duration, frStr)
		else:
			infoStr = "%sx%s   %s" % (mediaPlayback["pwidth"], mediaPlayback["pheight"], os.path.basename(prvFile))
			mediaPlayback["sl_preview"].setEnabled(False)

		mediaPlayback["l_info"].setText(infoStr)
		mediaPlayback["l_info"].setToolTip(infoStr)
		mediaPlayback["l_date"].setText(pdate)
		mediaPlayback["l_preview"].setToolTip("Drag to drop the media to RV\nCtrl+Drag to drop the media to Nuke")


	@err_decorator
	def getMediaResolution(self, prvFile, vidReader=None, setDuration=False, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

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
					mediaPlayback["pduration"] = 1
			else:
				pwidth = vidReader._meta["size"][0]
				pheight = vidReader._meta["size"][1]
				if len(mediaPlayback["seq"]) == 1 and setDuration:
					mediaPlayback["pduration"] = vidReader._meta["nframes"]

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
		if not os.path.exists(os.path.dirname(path)):
			os.makedirs(os.path.dirname(path))

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
	def changeImg(self, frame=0, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		pmsmall = QPixmap()
		if not QPixmapCache.find(("Frame" + str(mediaPlayback["curImg"])), pmsmall):
			if len(mediaPlayback["seq"]) == 1 and os.path.splitext(mediaPlayback["seq"][0])[1] in [".mp4", ".mov"]:
				curFile = mediaPlayback["seq"][0]
			else:
				curFile = mediaPlayback["seq"][mediaPlayback["curImg"]]
			fileName = os.path.join(mediaPlayback["basePath"], curFile)

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
					if len(mediaPlayback["seq"]) > 1:
						imgNum = 0
						vidFile = imageio.get_reader(fileName,  'ffmpeg')
					else:
						imgNum = mediaPlayback["curImg"]
						vidFile = mediaPlayback["vidPrw"]

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

			QPixmapCache.insert(("Frame" + str(mediaPlayback["curImg"])), pmsmall)

		if not mediaPlayback["prvIsSequence"] and len(mediaPlayback["seq"]) > 1:
			curFile = mediaPlayback["seq"][mediaPlayback["curImg"]]
			fileName = os.path.join(mediaPlayback["basePath"], curFile)
			self.updatePrvInfo(fileName, mediaPlayback=mediaPlayback)

		mediaPlayback["l_preview"].setPixmap(pmsmall)
		if mediaPlayback["timeline"].state() == QTimeLine.Running:
			mediaPlayback["sl_preview"].setValue(int(100 * (mediaPlayback["curImg"]/float(mediaPlayback["pduration"]))))
		mediaPlayback["curImg"] += 1
		if mediaPlayback["curImg"] == mediaPlayback["pduration"]:
			mediaPlayback["curImg"] = 0


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
	def sliderChanged(self, val, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		if mediaPlayback["seq"] != []:
			if val != (mediaPlayback["prevCurImg"]+1) or mediaPlayback["timeline"].state() != QTimeLine.Running:
				mediaPlayback["prevCurImg"] = val
				mediaPlayback["curImg"] = int(val/99.0*(mediaPlayback["pduration"]-1))

				if mediaPlayback["timeline"].state() != QTimeLine.Running:
					self.changeImg(mediaPlayback=mediaPlayback)
			else:
				mediaPlayback["prevCurImg"] = val


	@err_decorator
	def saveClicked(self, num):
		curTab = self.tbw_browser.currentWidget().property("tabType")
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
		if tab != self.tbw_browser.currentWidget().property("tabType"):
			for i in range(self.tbw_browser.count()):
				if self.tbw_browser.widget(i).property("tabType") == tab:
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
	def previewClk(self, event, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		if mediaPlayback["seq"] != [] and event.button() == Qt.LeftButton:
			if mediaPlayback["timeline"].state() == QTimeLine.Paused and not mediaPlayback["openRV"]:
				mediaPlayback["timeline"].setPaused(False)
			else:
				if mediaPlayback["timeline"].state() == QTimeLine.Running:
					mediaPlayback["timeline"].setPaused(True)
				mediaPlayback["openRV"] = False
		mediaPlayback["l_preview"].clickEvent(event)


	@err_decorator
	def previewDclk(self, event, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		if mediaPlayback["seq"] != [] and event.button() == Qt.LeftButton:
			mediaPlayback["openRV"] = True
			self.compare(current=True, mediaPlayback=mediaPlayback)
		mediaPlayback["l_preview"].dclickEvent(event)


	@err_decorator
	def getShotMediaFolder(self):
		if self.curRVersion == "" or ( self.curRLayer == "" and not (self.curRTask.endswith(" (playblast)") or self.curRTask.endswith(" (2d)") or self.curRTask.endswith(" (external)")) ):
			return

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

		return path


	@err_decorator
	def rclPreview(self, pos, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		path = mediaPlayback["getMediaBaseFolder"]()

		if path is None:
			return

		rcmenu = QMenu()

		if len(mediaPlayback["seq"]) > 0:
			playMenu = QMenu("Play in")

			if self.rv is not None:
				pAct = QAction("RV", self)
				pAct.triggered.connect(lambda: self.compare(current=True, prog="RV", mediaPlayback=mediaPlayback))
				playMenu.addAction(pAct)

			if self.djv is not None:
				pAct = QAction("DJV", self)
				pAct.triggered.connect(lambda: self.compare(current=True, prog="DJV", mediaPlayback=mediaPlayback))
				playMenu.addAction(pAct)

			if self.vlc is not None:
				pAct = QAction("VLC", self)
				pAct.triggered.connect(lambda: self.compare(current=True, prog="VLC", mediaPlayback=mediaPlayback))
				playMenu.addAction(pAct)

				if mediaPlayback["pformat"] == "*.exr":
					pAct.setEnabled(False)

			pAct = QAction("Default", self)
			pAct.triggered.connect(lambda: self.compare(current=True, prog="default", mediaPlayback=mediaPlayback))
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

		if len(mediaPlayback["seq"]) == 1 or mediaPlayback["prvIsSequence"]:
			cvtMenu = QMenu("Convert")
			qtAct = QAction("jpg", self)
			qtAct.triggered.connect(lambda: self.convertImgs(".jpg", mediaPlayback=mediaPlayback))
			cvtMenu.addAction(qtAct)
			qtAct = QAction("png", self)
			qtAct.triggered.connect(lambda: self.convertImgs(".png", mediaPlayback=mediaPlayback))
			cvtMenu.addAction(qtAct)
			qtAct = QAction("mp4", self)
			qtAct.triggered.connect(lambda: self.convertImgs(".mp4", mediaPlayback=mediaPlayback))
			cvtMenu.addAction(qtAct)
			rcmenu.addMenu(cvtMenu)
			self.core.appPlugin.setRCStyle(self, cvtMenu)

		if len(mediaPlayback["seq"]) > 0:
			if self.tbw_browser.currentWidget().property("tabType") == "Assets":
				prvAct = QAction("Set as assetpreview", self)
				prvAct.triggered.connect(self.setPreview)
				rcmenu.addAction(prvAct)

			elif self.tbw_browser.currentWidget().property("tabType") == "Shots":
				prvAct = QAction("Set as shotpreview", self)
				prvAct.triggered.connect(self.setPreview)
				rcmenu.addAction(prvAct)

		if len(mediaPlayback["seq"]) > 0 and not self.curRVersion.endswith(" (local)") and self.core.getConfig('paths', "dailies", configPath=self.core.prismIni) is not None:
			dliAct = QAction("Send to dailies", self)
			dliAct.triggered.connect(lambda: self.sendToDailies(mediaPlayback=mediaPlayback))
			rcmenu.addAction(dliAct)

		if self.core.appPlugin.appType == "2d" and len(mediaPlayback["seq"]) > 0:
			impAct = QAction("Import images...", self)
			impAct.triggered.connect(lambda: self.core.appPlugin.importImages(self))
			rcmenu.addAction(impAct)

		self.core.appPlugin.setRCStyle(self, rcmenu)
		rcmenu.exec_(mediaPlayback["l_preview"].mapToGlobal(pos))


	@err_decorator
	def setPreview(self):
		if self.tbw_browser.currentWidget().property("tabType") == "Assets":
			folderName = "Assetinfo"
			entityName = self.curAsset
			refresh = self.refreshAssetinfo
		else:
			folderName = "Shotinfo"
			entityName = self.cursShots
			refresh = self.refreshShotinfo

		prvPath = os.path.join(os.path.dirname(self.core.prismIni), folderName, "%s_preview.jpg" % entityName)

		pm = self.l_preview.pixmap()
		if (pm.width()/float(pm.height())) > 1.7778:
			pmap = pm.scaledToWidth(self.shotPrvXres)
		else:
			pmap = pm.scaledToHeight(self.shotPrvYres)

		self.savePMap(pmap, prvPath)

		refresh()


	@err_decorator
	def sendToDailies(self, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		dailiesName = self.core.getConfig('paths', "dailies", configPath=self.core.prismIni)

		curDate = time.strftime("%Y_%m_%d", time.localtime())

		dailiesFolder = os.path.join(self.core.projectPath, dailiesName, curDate, self.core.getConfig("globals", "UserName"))
		if not os.path.exists(dailiesFolder):
			os.makedirs(dailiesFolder)

		prvData = mediaPlayback["seq"][0].split(self.core.filenameSeperator)

		refName = ""

		if self.tbw_browser.currentWidget().property("tabType") == "Assets":
			refName += prvData[0] + self.core.filenameSeperator
		elif self.tbw_browser.currentWidget().property("tabType") == "Shots":
			refName += prvData[0] + self.core.filenameSeperator + prvData[1] + self.core.filenameSeperator

		refName += self.curRTask + self.core.filenameSeperator + self.curRVersion
		if self.curRLayer != "":
			refName += self.core.filenameSeperator + self.curRLayer

		sourcePath = os.path.join(mediaPlayback["basePath"], mediaPlayback["seq"][0])

		if platform.system() == "Windows":
			folderLinkName = refName + self.core.filenameSeperator + "Folder.lnk"
			refName += ".lnk"

			seqLnk = os.path.join(dailiesFolder, refName)
			folderLnk = os.path.join(dailiesFolder, folderLinkName)

			self.core.createShortcut(seqLnk, vTarget=sourcePath, args='', vWorkingDir='', vIcon='')
			self.core.createShortcut(folderLnk, vTarget=mediaPlayback["basePath"], args='', vWorkingDir='', vIcon='')
		else:
			slinkPath = os.path.join(dailiesFolder, refName + "_Folder")
			if os.path.exists(slinkPath):
				try:
					os.remove(slinkPath)
				except:
					QMessageBox.warning(self.core.messageParent, "Dailies", "An existing reference in the dailies folder couldn't be replaced.")
					return

			os.symlink(mediaPlayback["basePath"], slinkPath)

		self.core.copyToClipboard(dailiesFolder)

		QMessageBox.information(self.core.messageParent, "Dailies", "The version was sent to the current dailies folder. (path in clipboard)")


	@err_decorator
	def sliderDrag(self, event, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		custEvent = QMouseEvent(QEvent.MouseButtonPress, event.pos(), Qt.MidButton, Qt.MidButton, Qt.NoModifier)
		mediaPlayback["sl_preview"].origMousePressEvent(custEvent)


	@err_decorator
	def sliderClk(self, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		if "timeline" in mediaPlayback and mediaPlayback["timeline"].state() == QTimeLine.Running:
			mediaPlayback["slStop"] = True
			mediaPlayback["timeline"].setPaused(True)
		else:
			mediaPlayback["slStop"] = False


	@err_decorator
	def sliderRls(self, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		if mediaPlayback["slStop"]:
			mediaPlayback["timeline"].setPaused(False)


	@err_decorator
	def rclList(self, pos, lw, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		item = lw.itemAt(pos)
		if item is not None:
			itemName = item.text()
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
		if self.rv is not None and ((self.curRTask != "" and self.curRVersion != "" and len(mediaPlayback["seq"]) > 0) or len(self.lw_task.selectedItems()) > 1 or len(self.lw_version.selectedItems()) > 1):
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

		self.core.callback(name="openPBListContextMenu", types=["custom"], args=[self, rcmenu, lw, item, path])

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

		curTab = self.tbw_browser.currentWidget().property("tabType")
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

			curTab = self.tbw_browser.currentWidget().property("tabType")
			curData = [curTab, self.cursShots, self.curRTask, self.ep.e_versionName.text(), ""]
			self.showRender(curData[0], curData[1], curData[2], curData[3], curData[4])


	@err_decorator
	def rclCompare(self, pos, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		rcmenu = QMenu()

		add = QAction("Add current", self)
		add.triggered.connect(self.addCompare)
		if self.rv is not None and ((self.curRTask != "" and self.curRVersion != "" and len(mediaPlayback["seq"]) > 0) or len(self.lw_task.selectedItems()) > 1 or len(self.lw_version.selectedItems()) > 1):
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
				versions = self.getRenderVersions(task=i.text())

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
		if self.tbw_browser.currentWidget().property("tabType") == "Assets":
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
	def compare(self, current=False, ctype="layout", prog="", mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		if "timeline" in mediaPlayback and mediaPlayback["timeline"].state() == QTimeLine.Running:
			mediaPlayback["timeline"].setPaused(True)

		if prog in ["DJV", "VLC", "default"] or (prog == "" and ((self.rv is None) or (self.djv is not None and self.core.getConfig("globals", "prefer_djv", ptype="bool")))):
			if prog in ["DJV", ""] and self.djv is not None:
				progPath = self.djv
			elif prog == "VLC":
				progPath = self.vlc
			elif prog in ["default", ""]:
				progPath = ""

			comd = []
			filePath = ""

			if mediaPlayback["name"] == "shots":
				curRenders = self.getCurRenders()[0]
			else:
				curRenders = [mediaPlayback["getMediaBaseFolder"]()]

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
				if len(mediaPlayback["seq"]) == 1:
					cStates = [os.path.join(mediaPlayback["basePath"], mediaPlayback["seq"][0])]
				else:
					cStates = [mediaPlayback["basePath"]]
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
	def combineVersions(self, ctype="sequence", mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		if "timeline" in mediaPlayback and mediaPlayback["timeline"].state() == QTimeLine.Running:
			mediaPlayback["timeline"].setPaused(True)

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
	def mouseDrag(self, event, element, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		if (element == mediaPlayback["l_preview"]) and event.buttons() != Qt.LeftButton:
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

		drag = QDrag(mediaPlayback["l_preview"])
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
				for i in ["djv_view.exe", "djv.exe"]:
					djvPath = os.path.join(cDJVPath, "bin", i)
					if cDJVPath is not None and os.path.exists(djvPath):
						self.djv = djvPath
						break
				else:
					key = _winreg.OpenKey(
						_winreg.HKEY_LOCAL_MACHINE,
						"SOFTWARE\\Classes\\djv_view\\shell\\open\\command",
						0,
						_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
					)

					self.djv = (_winreg.QueryValue(key, None)).split(" \"%1\"")[0]
			else:
				for i in ["djv_view.sh", "djv.sh"]:
					djvPath = os.path.join(cDJVPath, "bin", i)
					if cDJVPath is not None and os.path.exists(djvPath):
						self.djv = djvPath
						break
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
	def convertImgs(self, extension, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		inputpath = os.path.join(mediaPlayback["basePath"], mediaPlayback["seq"][0]).replace("\\", "/")
		inputExt = os.path.splitext(inputpath)[1]
		videoInput = inputExt in [".mp4", ".mov"]

		if "pwidth" in mediaPlayback and mediaPlayback["pwidth"] == "?":
			QMessageBox.warning(self.core.messageParent,"Media conversion", "Cannot read media file.")
			return

		if extension == ".mp4" and "pwidth" in mediaPlayback and "pheight" in mediaPlayback and (int(mediaPlayback["pwidth"])%2 == 1 or int(mediaPlayback["pheight"])%2 == 1):
			QMessageBox.warning(self.core.messageParent,"Media conversion", "Media with odd resolution can't be converted to mp4.")
			return

		if mediaPlayback["prvIsSequence"]:
			inputpath = os.path.splitext(inputpath)[0][:-4] + "%04d" + inputExt
		
		if self.curRTask.endswith(" (external)") or self.curRTask.endswith(" (2d)") or self.curRTask.endswith(" (playblast)"):
			outputpath = os.path.join(os.path.dirname(inputpath) + "(%s)" % extension[1:], os.path.basename(inputpath))
		else:
			outputpath = os.path.join(os.path.dirname(os.path.dirname(inputpath)) + "(%s)" % extension[1:], os.path.basename(os.path.dirname(inputpath)), os.path.basename(inputpath))

		if extension == ".mp4" and mediaPlayback["prvIsSequence"]:
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

		if mediaPlayback["prvIsSequence"]:
			startNum = mediaPlayback["pstart"]
		else:
			startNum = 0

		result = self.core.convertMedia(inputpath, startNum, outputpath)

		if mediaPlayback["prvIsSequence"] or videoInput:
			outputpath = outputpath.replace("%04d", "%04d" % int(startNum))

		curTab = self.tbw_browser.currentWidget().property("tabType")
		curData = [curTab, self.cursShots, self.curRTask, self.curRVersion, self.curRLayer]
		self.showRender(curData[0], curData[1], curData[2], curData[3], curData[4])

		if os.path.exists(outputpath) and os.stat(outputpath).st_size > 0:
			self.core.copyToClipboard(outputpath)
			QMessageBox.information(self.core.messageParent,"Image conversion", "The images were converted successfully. (path is in clipboard)")
		else:
			self.core.ffmpegError("Image conversion", "The images could not be converted.", result)


	@err_decorator
	def compGetImportSource(self, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		sourceFolder = os.path.dirname(os.path.join(mediaPlayback["basePath"], mediaPlayback["seq"][0])).replace("\\", "/")
		sources = self.getImgSources(sourceFolder)
		sourceData = []

		for curSourcePath in sources:

			if "@@@@" in curSourcePath:
				if not "pstart" in mediaPlayback or not "pend" in mediaPlayback or mediaPlayback["pstart"] == "?" or mediaPlayback["pend"] == "?":
					firstFrame = 0
					lastFrame = 0
				else:
					firstFrame = mediaPlayback["pstart"]
					lastFrame = mediaPlayback["pend"]

				filePath = curSourcePath.replace("@@@@", "####").replace("\\","/")
			else:
				filePath =  curSourcePath.replace("\\","/")
				firstFrame = 0
				lastFrame = 0

			sourceData.append([filePath, firstFrame, lastFrame])

		return sourceData


	@err_decorator
	def compGetImportPasses(self, mediaPlayback=None):
		if mediaPlayback is None:
			mediaPlayback = self.mediaPlaybacks["shots"]

		sourceFolder = os.path.dirname(os.path.dirname(os.path.join(mediaPlayback["basePath"], mediaPlayback["seq"][0]))).replace("\\", "/")
		passes = [ x for x in os.listdir(sourceFolder) if x[-5:] not in ["(mp4)", "(jpg)", "(png)"] and os.path.isdir(os.path.join(sourceFolder, x))]
		sourceData = []

		for curPass in passes:
			curPassPath = os.path.join(sourceFolder,curPass)

			imgs = os.listdir(curPassPath)
			if len(imgs) == 0:
				continue

			if len(imgs) > 1 and "pstart" in mediaPlayback and "pend" in mediaPlayback and mediaPlayback["pstart"] != "?" and mediaPlayback["pend"] != "?":
				firstFrame = mediaPlayback["pstart"]
				lastFrame = mediaPlayback["pend"]

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