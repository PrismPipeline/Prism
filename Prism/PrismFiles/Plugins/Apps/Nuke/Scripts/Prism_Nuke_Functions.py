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



import nuke
import os, sys
import traceback, time, platform, random
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



class Prism_Nuke_Functions(object):
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
				erStr = ("%s ERROR - Prism_Plugin_Nuke %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].plugin.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def startup(self, origin):
		origin.timer.stop()

		for obj in qApp.topLevelWidgets():
			if (obj.inherits('QMainWindow') and obj.metaObject().className() == 'Foundry::UI::DockMainWindow'):
				nukeQtParent = obj
				break
		else:
			nukeQtParent = QWidget()

		origin.messageParent = QWidget()
		origin.messageParent.setParent(nukeQtParent, Qt.Window)
		origin.messageParent.setWindowFlags(origin.messageParent.windowFlags() ^ Qt.WindowStaysOnTopHint)

		nuke.menu('Nuke').addCommand( 'Prism/Save Version', origin.saveScene)
		nuke.menu('Nuke').addCommand( 'Prism/Save Comment', origin.saveWithComment)
		nuke.menu('Nuke').addCommand( 'Prism/Project Browser', origin.projectBrowser)
		nuke.menu('Nuke').addCommand( 'Prism/Update selected read nodes', self.updateNukeNodes)
		nuke.menu('Nuke').addCommand( 'Prism/Settings', origin.prismSettings)

		toolbar = nuke.toolbar("Nodes")
		iconPath = os.path.join(origin.prismRoot, "Scripts", "UserInterfacesPrism", "p_tray.png")
		toolbar.addMenu( 'Prism', icon=iconPath )
		toolbar.addCommand( "Prism/WritePrism", lambda: nuke.createNode('WritePrism'))

		nuke.addOnScriptLoad(origin.sceneOpen)

		self.isRendering = [False,""]
		self.useLastVersion = False


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
			currentFileName = nuke.root().name()
		except:
			currentFileName = ""

		if currentFileName == "Root":
			currentFileName = ""

		return currentFileName


	@err_decorator
	def getSceneExtension(self, origin):
		return ".nk"


	@err_decorator
	def saveScene(self, origin, filepath):
		try:
			return nuke.scriptSaveAs(filename=filepath)
		except:
			return ""


	@err_decorator
	def getImportPaths(self, origin):
		return False


	@err_decorator
	def getFrameRange(self, origin):
		startframe = nuke.knob("root.first_frame")
		endframe = nuke.knob("root.last_frame")

		return [startframe, endframe]


	@err_decorator
	def setFrameRange(self, origin, startFrame, endFrame):
		nuke.root().knob("first_frame").setValue(startFrame)
		nuke.root().knob("last_frame").setValue(endFrame)


	@err_decorator
	def getFPS(self, origin):
		return nuke.knob("root.fps")


	@err_decorator
	def updateNukeNodes(self):
		updatedNodes = []

		for i in nuke.selectedNodes():
			if i.Class() != "Read":
				continue

			curPath = i.knob("file").value()

			newPath = self.core.getLatestCompositingVersion(curPath)

			if os.path.exists(os.path.dirname(newPath)) and not curPath.startswith(os.path.dirname(newPath)):
				i.knob("file").setValue(newPath)
				updatedNodes.append(i)

		if len(updatedNodes) == 0:
			QMessageBox.information(self.core.messageParent, "Information", "No nodes were updated")
		else:
			mStr = "%s nodes were updated:\n\n" % len(updatedNodes)
			for i in updatedNodes:
				mStr += i.name() + "\n"

			QMessageBox.information(self.core.messageParent, "Information", mStr)


	@err_decorator
	def getOutputPath(self, node, group, render=False):
		try:
			taskName = group.knob("task").evaluate()
			comment = group.knob("comment").value()
			fileType = group.knob("file_type").value()
			localOut = group.knob("localOutput").value()
		except:
			return ""

		outputName = self.core.getCompositingOut(taskName, fileType, self.useLastVersion, render, localOut, comment)

		if not self.isRendering[0]:
			group.knob("fileName").setValue(outputName)
			#group.knob("fileName").clearFlag(0x10000000) # makes knob read-only, but leads to double property Uis

		return outputName


	@err_decorator
	def startRender(self, node, group, useLastVersion=False):
		taskName = group.knob("task").evaluate()

		if taskName is None or taskName == "":
			QMessageBox.warning(self.core.messageParent, "Warning", "Please choose a taskname")
			return

		fileName = self.getOutputPath(node, group)

		if fileName == "FileNotInPipeline":
			QMessageBox.warning(self.core.messageParent, "Warning", "The current file is not inside the Pipeline.\nUse the Project Browser to create a file in the Pipeline.")
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

		self.core.saveScene(versionUp=False)

		node.knob("Render").execute()

		self.useLastVersion = False


	@err_decorator
	def getAppVersion(self, origin):
		return nuke.NUKE_VERSION_STRING
		

	@err_decorator
	def onProjectBrowserStartup(self, origin):
		origin.loadOiio()
		origin.actionStateManager.setEnabled(False)


	@err_decorator
	def projectBrowserLoadLayout(self, origin):
		pass


	@err_decorator
	def setRCStyle(self, origin, rcmenu):
		pass


	@err_decorator
	def openScene(self, origin, filepath):
		if not filepath.endswith(".nk"):
			return False

		cleared = nuke.scriptSaveAndClear()
		if cleared:
			try:
				nuke.scriptOpen(filepath)
			except:
				pass

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
		msg = QMessageBox(QMessageBox.NoIcon, "Nuke Import", fString, QMessageBox.Cancel)
		msg.addButton("Current pass", QMessageBox.YesRole)
		msg.addButton("All passes", QMessageBox.YesRole)
		msg.addButton("Layout all passes", QMessageBox.YesRole)
		self.core.parentWindow(msg)
		action = msg.exec_()

		if action == 0:
			self.nukeImportSource(origin)
		elif action == 1:
			self.nukeImportPasses(origin)
		elif action == 2:
			self.nukeLayout(origin)
		else:
			return


	@err_decorator
	def nukeImportSource(self, origin):
		sourceData = origin.compGetImportSource()

		for i in sourceData:
			filePath = i[0]
			firstFrame = i[1]
			lastFrame = i[2]

			nuke.createNode("Read",'file %s first %s last %s' % (filePath, firstFrame, lastFrame), False)


	@err_decorator
	def nukeImportPasses(self, origin):
		sourceData = origin.compGetImportPasses()

		for i in sourceData:
			filePath = i[0]
			firstFrame = i[1]
			lastFrame = i[2]

			nuke.createNode("Read",'file %s first %s last %s' % (filePath, firstFrame, lastFrame), False)


	@err_decorator
	def nukeLayout(self, origin):
		allExistingNodes = nuke.allNodes()
		try:
			allBBx = max([node.xpos() for node in allExistingNodes])
		except:
			allBBx = 0


		self.nukeYPos = 0
		xOffset = 200
		nukeXPos = allBBx+xOffset
		nukeSetupWidth = 950
		nukeSetupHeight = 400
		nukeYDistance = 700
		nukeBeautyYDistance = 500
		nukeBackDropFontSize = 100
		self.nukeIdxNode = None

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

		passes = [ x for x in os.listdir(passFolder) if x[-5:] not in ["(mp4)", "(jpg)", "(png)"] and os.path.isdir(os.path.join(passFolder, x)) and len(os.listdir(os.path.join(passFolder, x))) > 0]

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
				self.createBeautyPass(origin, filePath,firstFrame,lastFrame,curPass, nukeXPos, nukeSetupWidth, nukeBeautyYDistance, nukeBackDropFontSize)

			#components
			elif curPass in passesComponents:
				self.createComponentPass(origin, filePath,firstFrame,lastFrame,curPass, nukeXPos, nukeSetupWidth, nukeSetupHeight, nukeBackDropFontSize, nukeYDistance)

			#masks
			elif curPass in passesMasks:
				maskNum += 1
				self.createMaskPass(origin, filePath,firstFrame,lastFrame, nukeXPos, nukeSetupWidth, maskNum)

			#utility
			elif curPass in passesUtilities:
				utilsNum += 1
				self.createUtilityPass(origin, filePath,firstFrame,lastFrame, nukeXPos, nukeSetupWidth, utilsNum)

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
			backDrop = nuke.nodes.BackdropNode(xpos = bdX,bdwidth = bdW,ypos = bdY, bdheight = bdH,tile_color = maskBackdropColor, note_font_size=nukeBackDropFontSize, label = "<center><b>"+"Masks"+"</b><c/enter>")

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
			backDrop = nuke.nodes.BackdropNode(xpos = bdX,bdwidth = bdW,ypos = bdY, bdheight = bdH,tile_color = maskBackdropColor, note_font_size=nukeBackDropFontSize, label = "<center><b>"+"Utilities"+"</b><c/enter>")


	@err_decorator
	def createBeautyPass(self, origin, filePath,firstFrame,lastFrame,curPass, nukeXPos, nukeSetupWidth, nukeBeautyYDistance, nukeBackDropFontSize):
	 
		curReadNode = nuke.createNode("Read",'file "%s" first %s last %s origfirst %s origlast %s' % (filePath,firstFrame,lastFrame,firstFrame,lastFrame),False)
	 
		nodeArray = [curReadNode]
	 
		#backdropcolor
		r = (float(random.randint( 30+((self.nukeYPos/3)%3), 80)))/100
		g = (float(random.randint( 20+((self.nukeYPos/3)%3), 80)))/100
		b = (float(random.randint( 15+((self.nukeYPos/3)%3), 80)))/100
		hexColour = int('%02x%02x%02x%02x' % (r*255,g*255,b*255,1),16)
	 
		#positions
		curReadNodeWidth = int(curReadNode.screenWidth()*0.5-6)
		curReadNodeHeight = int(curReadNode.screenHeight()*0.5-3)
	 
		curReadNode.setYpos(self.nukeYPos+curReadNodeHeight)
		curReadNode.setXpos(nukeXPos+nukeSetupWidth)
	 
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
		backDrop = nuke.nodes.BackdropNode(xpos = bdX,bdwidth = bdW,ypos = bdY, bdheight = bdH,tile_color = hexColour, note_font_size=nukeBackDropFontSize, label = "<center><b>"+curPass+"</b><c/enter>")
	 
		#increment position
		self.nukeYPos += nukeBeautyYDistance
	 
		#current nukeIdxNode
		self.nukeIdxNode = curReadNode


	@err_decorator
	def createComponentPass(self, origin, filePath,firstFrame,lastFrame,curPass, nukeXPos, nukeSetupWidth, nukeSetupHeight, nukeBackDropFontSize, nukeYDistance):

		curReadNode = nuke.createNode("Read",'file "%s" first %s last %s origfirst %s origlast %s' % (filePath,firstFrame,lastFrame,firstFrame,lastFrame),False)
		mergeNode1 = nuke.createNode("Merge",'operation difference',False)
		dotNode = nuke.createNode("Dot","",False)
		dotNodeCorner = nuke.createNode("Dot","",False)
		mergeNode2 = nuke.createNode("Merge",'operation plus',False)

		nodeArray = [curReadNode,dotNode,mergeNode1,mergeNode2,dotNodeCorner]
	 
		#positions
		curReadNode.setYpos(self.nukeYPos)
		curReadNode.setXpos(nukeXPos)
	 
		curReadNodeWidth = int(curReadNode.screenWidth()*0.5-6)
		curReadNodeHeight = int(curReadNode.screenHeight()*0.5-3)
	 
		mergeNode1.setYpos(self.nukeYPos+curReadNodeHeight)
		mergeNode1.setXpos(nukeXPos+nukeSetupWidth)
	 
		dotNode.setYpos(self.nukeYPos+curReadNodeHeight+int(curReadNode.screenWidth()*0.7))
		dotNode.setXpos(nukeXPos+curReadNodeWidth)
	 
		dotNodeCorner.setYpos(self.nukeYPos+nukeSetupHeight)
		dotNodeCorner.setXpos(nukeXPos+curReadNodeWidth)
	 
		mergeNode2.setYpos(self.nukeYPos+nukeSetupHeight-4)
		mergeNode2.setXpos(nukeXPos+nukeSetupWidth)
	 
	 
		# #inputs
		mergeNode1.setInput(1,curReadNode)
		dotNode.setInput(0,curReadNode)
		dotNodeCorner.setInput(0,dotNode)
		mergeNode2.setInput(1,dotNodeCorner)
		mergeNode2.setInput(0,mergeNode1)
	 
		if(self.nukeIdxNode!=None):
			mergeNode1.setInput(0,self.nukeIdxNode)
	 
		#backdrop boundry offsets
		left, top, right, bottom = (-10, -125, 100, 50)
		   
		#backdropcolor
		r = (float(random.randint( 30+((self.nukeYPos/3)%3), 80)))/100
		g = (float(random.randint( 20+((self.nukeYPos/3)%3), 80)))/100
		b = (float(random.randint( 15+((self.nukeYPos/3)%3), 80)))/100
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
		backDrop = nuke.nodes.BackdropNode(xpos = bdX,bdwidth = bdW,ypos = bdY, bdheight = bdH,tile_color = hexColour, note_font_size=nukeBackDropFontSize, label = "<b>"+curPass+"</b>")
	 
		#increment position
		self.nukeYPos += nukeYDistance

		#current nukeIdxNode
		self.nukeIdxNode = mergeNode2


	@err_decorator
	def createMaskPass(self, origin, filePath,firstFrame,lastFrame, nukeXPos, nukeSetupWidth, idx):
		
		curReadNode = nuke.createNode("Read",'file "%s" first %s last %s origfirst %s origlast %s' % (filePath,firstFrame,lastFrame,firstFrame,lastFrame),False)
		curReadNode.setYpos(0)
		curReadNode.setXpos(nukeXPos+nukeSetupWidth+500+idx*350)

		val = 0.5
		r = int('%02x%02x%02x%02x' % (val*255,0,0,1),16) 
		g = int('%02x%02x%02x%02x' % (0,val*255,0,1),16) 
		b = int('%02x%02x%02x%02x' % (0,0,val*255,1),16) 

		redShuffle = nuke.createNode("Shuffle", 'red red blue red green red alpha red',inpanel = False,)
		greenShuffle = nuke.createNode("Shuffle", 'red green blue green green green alpha green',inpanel = False)
		blueShuffle = nuke.createNode("Shuffle", 'red blue blue blue green blue alpha blue',inpanel = False)

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


	@err_decorator
	def createUtilityPass(self, origin, filePath,firstFrame,lastFrame, nukeXPos, nukeSetupWidth, idx):
		
		curReadNode = nuke.createNode("Read",'file "%s" first %s last %s origfirst %s origlast %s' % (filePath,firstFrame,lastFrame,firstFrame,lastFrame),False)
		curReadNode.setYpos(0)
		curReadNode.setXpos(nukeXPos+nukeSetupWidth+500+idx*100)
		try:
			curReadNode.setXpos(curReadNode.xpos()+self.maskNodes[-1].xpos()-nukeXPos-nukeSetupWidth)
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
	def shotgunPublish_startup(self, origin):
		pass