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



import NatronEngine, NatronGui
import os, sys, platform
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
	if sys.version[0] == "3":
		import winreg as _winreg
	else:
		import _winreg


class Prism_Natron_Functions(object):
	def __init__(self, core, plugin):
		self.core = core
		self.plugin = plugin


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			exc_info = sys.exc_info()
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - Prism_Plugin_Natron - Core: %s - Plugin: %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, args[0].plugin.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def instantStartup(self, origin):
		NatronGui.natron.addMenuCommand("Prism/Save Version", "pcore.saveScene")
		NatronGui.natron.addMenuCommand("Prism/Save Comment", "pcore.saveWithComment")
		NatronGui.natron.addMenuCommand("Prism/Project Browser", "pcore.projectBrowser")
		NatronGui.natron.addMenuCommand("Prism/Update selected read nodes", "pcore.appPlugin.updateNatronNodes")
		NatronGui.natron.addMenuCommand("Prism/Settings", "pcore.prismSettings")


	@err_decorator
	def startup(self, origin):
		for obj in qApp.topLevelWidgets():
			if (obj.inherits('QMainWindow') and obj.metaObject().className() == 'Gui' and "Natron" in obj.windowTitle()):
				natronQtParent = obj
				break
		else:
			return False

		origin.messageParent = QWidget()
		origin.messageParent.setParent(natronQtParent, Qt.Window)
		origin.timer.stop()

		if platform.system() == "Darwin":
			if self.core.useOnTop:
				origin.messageParent.setWindowFlags(origin.messageParent.windowFlags() ^ Qt.WindowStaysOnTopHint)

		#else:
		#	origin.messageParent = QWidget()

	#	with open("D:/tst.txt", "a") as l:
	#		l.write("\nn2")


	#	toolbar = natron.toolbar("Nodes")
	#	iconPath = os.path.join(origin.prismRoot, "Scripts", "UserInterfacesPrism", "p_tray.png")
	#	toolbar.addMenu( 'Prism', icon=iconPath )
	#	toolbar.addCommand( "Prism/WritePrism", lambda: natron.createNode('WritePrism'))

	#	natron.addOnScriptLoad(origin.sceneOpen)

		ss = QApplication.instance().styleSheet()
		ss += QApplication.instance().styleSheet().replace("QTreeWidget", "QListWidget")
		ss += QApplication.instance().styleSheet().replace("QTreeWidget", "QTreeView")
		ss += QApplication.instance().styleSheet().replace("QTreeWidget", "QTableView")
		ss += QApplication.instance().styleSheet().replace("QTreeWidget", "QListView")
		ss += QApplication.instance().styleSheet().replace("QTreeView,", "QTreeView, QTableView,")
		origin.messageParent.setStyleSheet(ss)

		self.isRendering = [False,""]
		self.useLastVersion = False
		self.natronApp = NatronEngine.natron.getInstance(0)


	@err_decorator
	def onProjectChanged(self, origin):
		pass


	@err_decorator
	def sceneOpen(self, origin):
		if hasattr(origin, "asThread") and origin.asThread.isRunning():
			origin.startasThread()


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
	def getCurrentFileName(self, origin, path=True):
		try:
			pPath = NatronEngine.App.getProjectParam(self.natronApp, "projectPath").get()
			pName =  NatronEngine.App.getProjectParam(self.natronApp, "projectName").get()

			currentFileName = pPath + pName
		except:
			currentFileName = ""

		return currentFileName


	@err_decorator
	def getSceneExtension(self, origin):
		return self.sceneFormats[0]


	@err_decorator
	def saveScene(self, origin, filepath, details={}):
		try:
			return NatronEngine.App.saveProjectAs(self.natronApp, filepath)
		except:
			return ""


	@err_decorator
	def getImportPaths(self, origin):
		return False


	@err_decorator
	def getFrameRange(self, origin):
		startframe = NatronEngine.App.getProjectParam(self.natronApp, "frameRange").get().x
		endframe = NatronEngine.App.getProjectParam(self.natronApp, "frameRange").get().y

		return [startframe, endframe]


	@err_decorator
	def setFrameRange(self, origin, startFrame, endFrame):
		NatronEngine.App.getProjectParam(self.natronApp, "frameRange").set(startFrame, endFrame)


	@err_decorator
	def getFPS(self, origin):
		return NatronEngine.App.getProjectParam(self.natronApp, "frameRate").get()


	@err_decorator
	def setFPS(self, origin, fps):
		return NatronEngine.App.getProjectParam(self.natronApp, "frameRate").set(fps)


	@err_decorator
	def updateNatronNodes(self):
		updatedNodes = []

		selNodes = NatronGui.natron.getGuiInstance(self.natronApp.getAppID()).getSelectedNodes()
		for i in selNodes :
			if str(i.getPluginID()) != "fr.inria.built-in.Read":
				continue

			curPath = i.getParam("filename").get()

			newPath = self.core.getLatestCompositingVersion(curPath)

			if os.path.exists(os.path.dirname(newPath)) and not curPath.startswith(os.path.dirname(newPath)):
				i.getParam("filename").set(newPath)
				updatedNodes.append(i)

		if len(updatedNodes) == 0:
			QMessageBox.information(self.core.messageParent, "Information", "No nodes were updated")
		else:
			mStr = "%s nodes were updated:\n\n" % len(updatedNodes)
			for i in updatedNodes:
				mStr += i.getScriptName() + "\n"

			QMessageBox.information(self.core.messageParent, "Information", mStr)


	@err_decorator
	def getAppVersion(self, origin):
		return NatronEngine.natron.getNatronVersionString()


	@err_decorator
	def onProjectBrowserStartup(self, origin):
		origin.actionStateManager.setEnabled(False)


	@err_decorator
	def projectBrowserLoadLayout(self, origin):
		pass


	@err_decorator
	def projectBrower_loadLibs(self, origin):
		pass


	@err_decorator
	def setRCStyle(self, origin, rcmenu):
		pass


	@err_decorator
	def openScene(self, origin, filepath):
		if os.path.splitext(filepath)[1] not in self.sceneFormats:
			return False

		if NatronEngine.App.resetProject(self.natronApp):
			NatronEngine.App.loadProject(self.natronApp, filepath)

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
		msg = QMessageBox(QMessageBox.NoIcon, "Natron Import", fString, QMessageBox.Cancel)
		msg.addButton("Current pass", QMessageBox.YesRole)
		msg.addButton("All passes", QMessageBox.YesRole)
	#	msg.addButton("Layout all passes", QMessageBox.YesRole)
		self.core.parentWindow(msg)
		action = msg.exec_()

		if action == 0:
			self.natronImportSource(origin)
		elif action == 1:
			self.natronImportPasses(origin)
	#	elif action == 2:
	#		self.natronLayout(origin)
		else:
			return


	@err_decorator
	def natronImportSource(self, origin):
		sourceData = origin.compGetImportSource()

		for i in sourceData:
			self.natronApp.createReader(i[0])


	@err_decorator
	def natronImportPasses(self, origin):
		sourceData = origin.compGetImportPasses()

		for i in sourceData:
			self.natronApp.createReader(i[0])


	# not implemented yet
	@err_decorator
	def natronLayout(self, origin):
		allExistingNodes = natron.allNodes()
		try:
			allBBx = max([node.xpos() for node in allExistingNodes])
		except:
			allBBx = 0


		self.natronYPos = 0
		xOffset = 200
		natronXPos = allBBx+xOffset
		natronSetupWidth = 950
		natronSetupHeight = 400
		natronYDistance = 700
		natronBeautyYDistance = 500
		natronBackDropFontSize = 100
		self.natronIdxNode = None

		passFolder = os.path.dirname(os.path.dirname(os.path.join(origin.basepath, origin.seq[0]))).replace("\\", "/")

		if not os.path.exists(passFolder):
			return
		 
		beautyTriggers = ["beauty","rgb", "rgba"]
		componentsTriggers = ["ls","select","gi","spec","refr","refl","light","lighting","highlight","diff","diffuse","emission","sss","vol"]
		masksTriggers = ["mm","mask","puzzleMatte","matte","puzzle"]
		 
		beautyPass = []
		componentPasses = []
		maskPasses = []
		utilityPasses = []

		self.maskNodes = []
		self.utilityNodes = []

		passes = [ x for x in os.listdir(passFolder) if x[-5:] not in ["(mp4)", "(jpg)", "(png)"] and os.path.isdir(os.path.join(passFolder, x))]

		passesBeauty = []
		passesComponents = []
		passesMasks = []
		passesUtilities = []

		for curPass in passes:
			assigned = False

			for trigger in beautyTriggers:
				if trigger in curPass.lower():
					passesBeauty.append(curPass)
					assigned = True
					break

			if assigned:
				continue

			for trigger in componentsTriggers:
				if trigger in curPass.lower():
					passesComponents.append(curPass)
					assigned = True
					break

			if assigned:
				continue

			for trigger in masksTriggers:
				if trigger in curPass.lower():
					passesMasks.append(curPass)
					assigned = True
					break

			if assigned:
				continue

			passesUtilities.append(curPass)

		passes = passesBeauty + passesComponents + passesMasks + passesUtilities

		maskNum = 0
		utilsNum = 0

		for curPass in passes:
			curPassPath = os.path.join(passFolder,curPass)
			curPassName = os.listdir(curPassPath)[0].split(".")[0]

			if len(os.listdir(curPassPath)) > 1:
				if not hasattr(origin, "pstart") or not hasattr(origin, "pend") or origin.pstart == "?" or origin.pend == "?":
					return

				firstFrame = origin.pstart
				lastFrame = origin.pend

				increment = "####"
				curPassFormat = os.listdir(curPassPath)[0].split(".")[-1]

				filePath =  os.path.join(passFolder,curPass,".".join([curPassName,increment,curPassFormat])).replace("\\","/")
			else:
				filePath =  os.path.join(curPassPath, os.listdir(curPassPath)[0]).replace("\\","/")
				firstFrame = 0
				lastFrame = 0



			#createPasses
			#beauty
			if curPass in passesBeauty:
				self.createBeautyPass(origin, filePath,firstFrame,lastFrame,curPass, natronXPos, natronSetupWidth, natronBeautyYDistance, natronBackDropFontSize)

			#components
			elif curPass in passesComponents:
				self.createComponentPass(origin, filePath,firstFrame,lastFrame,curPass, natronXPos, natronSetupWidth, natronSetupHeight, natronBackDropFontSize, natronYDistance)

			#masks
			elif curPass in passesMasks:
				maskNum += 1
				self.createMaskPass(origin, filePath,firstFrame,lastFrame, natronXPos, natronSetupWidth, maskNum)

			#utility
			elif curPass in passesUtilities:
				utilsNum += 1
				self.createUtilityPass(origin, filePath,firstFrame,lastFrame, natronXPos, natronSetupWidth, utilsNum)

		#maskbackdrop
		if(len(self.maskNodes)>0):
			bdX = min([node.xpos() for node in self.maskNodes])
			bdY = min([node.ypos() for node in self.maskNodes])
			bdW = max([node.xpos() + node.screenWidth() for node in self.maskNodes]) - bdX
			bdH = max([node.ypos() + node.screenHeight() for node in self.maskNodes]) - bdY
		 
			#backdrop boundry offsets
			left, top, right, bottom = (-160, -135, 160, 80)
		 
			#boundry offsets
			bdX += left
			bdY += top
			bdW += (right - left)
			bdH += (bottom - top)

			#createbackdrop
			maskBackdropColor = int('%02x%02x%02x%02x' % (255,125,125,1),16)
			backDrop = natron.nodes.BackdropNode(xpos = bdX,bdwidth = bdW,ypos = bdY, bdheight = bdH,tile_color = maskBackdropColor, note_font_size=natronBackDropFontSize, label = "<center><b>"+"Masks"+"</b><c/enter>")

		#utilitybackdrop
		if(len(self.utilityNodes)>0):
			bdX = min([node.xpos() for node in self.utilityNodes])
			bdY = min([node.ypos() for node in self.utilityNodes])
			bdW = max([node.xpos() + node.screenWidth() for node in self.utilityNodes]) - bdX
			bdH = max([node.ypos() + node.screenHeight() for node in self.utilityNodes]) - bdY
		 
			#backdrop boundry offsets
			left, top, right, bottom = (-160, -135, 160, 80)
		 
			#boundry offsets
			bdX += left
			bdY += top
			bdW += (right - left)
			bdH += (bottom - top)

			#createbackdrop
			maskBackdropColor = int('%02x%02x%02x%02x' % (125,255,125,1),16)
			backDrop = natron.nodes.BackdropNode(xpos = bdX,bdwidth = bdW,ypos = bdY, bdheight = bdH,tile_color = maskBackdropColor, note_font_size=natronBackDropFontSize, label = "<center><b>"+"Utilities"+"</b><c/enter>")


	# not implemented yet
	@err_decorator
	def createBeautyPass(self, origin, filePath,firstFrame,lastFrame,curPass, natronXPos, natronSetupWidth, natronBeautyYDistance, natronBackDropFontSize):
	 
		curReadNode = natron.createNode("Read",'file "%s" first %s last %s origfirst %s origlast %s' % (filePath,firstFrame,lastFrame,firstFrame,lastFrame),False)
	 
		nodeArray = [curReadNode]
	 
		#backdropcolor
		r = (float(random.randint( 30+((self.natronYPos/3)%3), 80)))/100
		g = (float(random.randint( 20+((self.natronYPos/3)%3), 80)))/100
		b = (float(random.randint( 15+((self.natronYPos/3)%3), 80)))/100
		hexColour = int('%02x%02x%02x%02x' % (r*255,g*255,b*255,1),16)
	 
		#positions
		curReadNodeWidth = int(curReadNode.screenWidth()*0.5-6)
		curReadNodeHeight = int(curReadNode.screenHeight()*0.5-3)
	 
		curReadNode.setYpos(self.natronYPos+curReadNodeHeight)
		curReadNode.setXpos(natronXPos+natronSetupWidth)
	 
		#backdrop boundries
		bdX = min([node.xpos() for node in nodeArray])
		bdY = min([node.ypos() for node in nodeArray])
		bdW = max([node.xpos() + node.screenWidth() for node in nodeArray]) - bdX
		bdH = max([node.ypos() + node.screenHeight() for node in nodeArray]) - bdY
	 
		#backdrop boundry offsets
		left, top, right, bottom = (-160, -135, 160, 80)
	 
		#boundry offsets
		bdX += left
		bdY += top
		bdW += (right - left)
		bdH += (bottom - top)
	 
		#createbackdrop
		backDrop = natron.nodes.BackdropNode(xpos = bdX,bdwidth = bdW,ypos = bdY, bdheight = bdH,tile_color = hexColour, note_font_size=natronBackDropFontSize, label = "<center><b>"+curPass+"</b><c/enter>")
	 
		#increment position
		self.natronYPos += natronBeautyYDistance
	 
		#current natronIdxNode
		self.natronIdxNode = curReadNode


	# not implemented yet
	@err_decorator
	def createComponentPass(self, origin, filePath,firstFrame,lastFrame,curPass, natronXPos, natronSetupWidth, natronSetupHeight, natronBackDropFontSize, natronYDistance):

		curReadNode = natron.createNode("Read",'file "%s" first %s last %s origfirst %s origlast %s' % (filePath,firstFrame,lastFrame,firstFrame,lastFrame),False)
		mergeNode1 = natron.createNode("Merge",'operation difference',False)
		dotNode = natron.createNode("Dot","",False)
		dotNodeCorner = natron.createNode("Dot","",False)
		mergeNode2 = natron.createNode("Merge",'operation plus',False)

		nodeArray = [curReadNode,dotNode,mergeNode1,mergeNode2,dotNodeCorner]
	 
		#positions
		curReadNode.setYpos(self.natronYPos)
		curReadNode.setXpos(natronXPos)
	 
		curReadNodeWidth = int(curReadNode.screenWidth()*0.5-6)
		curReadNodeHeight = int(curReadNode.screenHeight()*0.5-3)
	 
		mergeNode1.setYpos(self.natronYPos+curReadNodeHeight)
		mergeNode1.setXpos(natronXPos+natronSetupWidth)
	 
		dotNode.setYpos(self.natronYPos+curReadNodeHeight+int(curReadNode.screenWidth()*0.7))
		dotNode.setXpos(natronXPos+curReadNodeWidth)
	 
		dotNodeCorner.setYpos(self.natronYPos+natronSetupHeight)
		dotNodeCorner.setXpos(natronXPos+curReadNodeWidth)
	 
		mergeNode2.setYpos(self.natronYPos+natronSetupHeight-4)
		mergeNode2.setXpos(natronXPos+natronSetupWidth)
	 
	 
		# #inputs
		mergeNode1.setInput(1,curReadNode)
		dotNode.setInput(0,curReadNode)
		dotNodeCorner.setInput(0,dotNode)
		mergeNode2.setInput(1,dotNodeCorner)
		mergeNode2.setInput(0,mergeNode1)
	 
		if(self.natronIdxNode!=None):
			mergeNode1.setInput(0,self.natronIdxNode)
	 
		#backdrop boundry offsets
		left, top, right, bottom = (-10, -125, 100, 50)
		   
		#backdropcolor
		r = (float(random.randint( 30+((self.natronYPos/3)%3), 80)))/100
		g = (float(random.randint( 20+((self.natronYPos/3)%3), 80)))/100
		b = (float(random.randint( 15+((self.natronYPos/3)%3), 80)))/100
		hexColour = int('%02x%02x%02x%02x' % (r*255,g*255,b*255,1),16)
	 
	 
		#backdrop boundries
		bdX = min([node.xpos() for node in nodeArray])
		bdY = min([node.ypos() for node in nodeArray])
		bdW = max([node.xpos() + node.screenWidth() for node in nodeArray]) - bdX
		bdH = max([node.ypos() + node.screenHeight() for node in nodeArray]) - bdY
	 
	 
		#boundry offsets
		bdX += left
		bdY += top
		bdW += (right - left)
		bdH += (bottom - top)
	 
		#createbackdrop
		backDrop = natron.nodes.BackdropNode(xpos = bdX,bdwidth = bdW,ypos = bdY, bdheight = bdH,tile_color = hexColour, note_font_size=natronBackDropFontSize, label = "<b>"+curPass+"</b>")
	 
		#increment position
		self.natronYPos += natronYDistance

		#current natronIdxNode
		self.natronIdxNode = mergeNode2


	# not implemented yet
	@err_decorator
	def createMaskPass(self, origin, filePath,firstFrame,lastFrame, natronXPos, natronSetupWidth, idx):
		
		curReadNode = natron.createNode("Read",'file "%s" first %s last %s origfirst %s origlast %s' % (filePath,firstFrame,lastFrame,firstFrame,lastFrame),False)
		curReadNode.setYpos(0)
		curReadNode.setXpos(natronXPos+natronSetupWidth+500+idx*350)

		val = 0.5
		r = int('%02x%02x%02x%02x' % (val*255,0,0,1),16) 
		g = int('%02x%02x%02x%02x' % (0,val*255,0,1),16) 
		b = int('%02x%02x%02x%02x' % (0,0,val*255,1),16) 

		redShuffle = natron.createNode("Shuffle", 'red red blue red green red alpha red',inpanel = False,)
		greenShuffle = natron.createNode("Shuffle", 'red green blue green green green alpha green',inpanel = False)
		blueShuffle = natron.createNode("Shuffle", 'red blue blue blue green blue alpha blue',inpanel = False)

		redShuffle['tile_color'].setValue(r)
		greenShuffle['tile_color'].setValue(g)
		blueShuffle['tile_color'].setValue(b)

		redShuffle.setInput(0,curReadNode)
		greenShuffle.setInput(0,curReadNode)
		blueShuffle.setInput(0,curReadNode)

		redShuffle.setXpos(redShuffle.xpos()-110)
	#	greenShuffle.setXpos(greenShuffle.xpos()-110)
		blueShuffle.setXpos(blueShuffle.xpos()+110)

		self.maskNodes.append(curReadNode)
		self.maskNodes.append(redShuffle)
		self.maskNodes.append(greenShuffle)
		self.maskNodes.append(blueShuffle)


	# not implemented yet
	@err_decorator
	def createUtilityPass(self, origin, filePath,firstFrame,lastFrame, natronXPos, natronSetupWidth, idx):
		
		curReadNode = natron.createNode("Read",'file "%s" first %s last %s origfirst %s origlast %s' % (filePath,firstFrame,lastFrame,firstFrame,lastFrame),False)
		curReadNode.setYpos(0)
		curReadNode.setXpos(natronXPos+natronSetupWidth+500+idx*100)
		try:
			curReadNode.setXpos(curReadNode.xpos()+self.maskNodes[-1].xpos()-natronXPos-natronSetupWidth)
		except:
			pass

		self.utilityNodes.append(curReadNode)


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
		pass


	@err_decorator
	def editShot_loadLibs(self, origin):
		pass


	@err_decorator
	def projectBrower_loadLibs(self, origin):
		pass


	@err_decorator
	def shotgunPublish_startup(self, origin):
		pass


	def wpParamChanged(self, thisParam=None, thisNode=None, thisGroup=None, app=None, userEdited=None):
		if not hasattr(thisNode, "refresh"):
			return

		if app is not None:
			self.natronApp = app

		if thisParam == thisNode.refresh:
			self.getOutputPath(thisNode.getNode("WritePrismBase"), thisNode)
		elif thisParam == thisNode.createDir:
			self.core.createFolder(os.path.dirname(thisNode.getParam("fileName").get()), showMessage=True)
		elif thisParam == thisNode.openDir:
			self.core.openFolder(os.path.dirname(thisNode.getParam("fileName").get()))
		elif thisParam == thisNode.b_startRender:
			self.startRender(thisNode.getNode("WritePrismBase"), thisNode)
		elif thisParam == thisNode.b_startRenderLastVersion:
			self.startRender(thisNode.getNode("WritePrismBase"), thisNode, useLastVersion=True)
		elif thisParam == thisNode.WritePrismBaseframeRange:
			self.wpRangeChanged(thisNode.getNode("WritePrismBase"), thisNode)


	@err_decorator
	def getOutputPath(self, node, group=None, app=None, render=False):
		if app is not None:
			self.natronApp = app

		self.isRendering = [False, ""]

		try:
			taskName = group.getParam("prismTask").get()
			fileType = group.getParam("outputFormat").getOption(group.getParam("outputFormat").get())
			localOut = group.getParam("localOutput").get()
		except:
			return ""

		outputName = self.core.getCompositingOut(taskName, fileType, self.useLastVersion, render, localOut)

		group.getParam("fileName").set(outputName)
		node.getParam("filename").set(outputName)

		return outputName


	@err_decorator
	def startRender(self, node, group, useLastVersion=False):
		taskName = group.getParam("prismTask").get()

		if taskName is None or taskName == "":
			QMessageBox.warning(self.core.messageParent, "Warning", "Please choose a taskname")
			return

		if useLastVersion:
			msg = QMessageBox(QMessageBox.Information, "Render", "Are you sure you want to execute this state as the previous version?\nThis may overwrite existing files.", QMessageBox.Cancel)
			msg.addButton("Continue", QMessageBox.YesRole)
			self.core.parentWindow(msg)
			action = msg.exec_()

			if action != 0:
				return

			self.useLastVersion = True
		else:
			self.useLastVersion = False

		fileName = self.getOutputPath(node, group, render=True)

		if fileName == "FileNotInPipeline":
			QMessageBox.warning(self.core.messageParent, "Warning", "The current file is not inside the Pipeline.\nUse the Project Browser to create a file in the Pipeline.")
			return

		self.core.saveScene(versionUp=False)
		node.getParam("startRender").trigger()

		self.useLastVersion = False


	@err_decorator
	def wpRangeChanged(self, node, group):
		fVisible = group.getParam("WritePrismBaseframeRange").get() == 2

		group.getParam("WritePrismBasefirstFrame").setVisible(fVisible)
		group.getParam("WritePrismBaselastFrame").setVisible(fVisible)