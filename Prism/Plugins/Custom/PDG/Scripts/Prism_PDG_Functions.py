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



import os, sys, traceback, time, subprocess, threading
from functools import wraps

try:
	from PySide2.QtCore import *
	from PySide2.QtGui import *
	from PySide2.QtWidgets import *
except:
	from PySide.QtCore import *
	from PySide.QtGui import *


try:
	import hou
	import pdg
except:
	pass


class Prism_PDG_Functions(object):
	def __init__(self, core, plugin):
		self.core = core
		self.plugin = plugin


	# this function catches any errors in this script and can be ignored
	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			exc_info = sys.exc_info()
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - Prism_Plugin_PDG - Core: %s - Plugin: %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, args[0].plugin.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	# if returns true, the plugin will be loaded by Prism
	@err_decorator
	def isActive(self):
		return "hou" in globals()


	@err_decorator
	def cookNode(self, **kwargs):

		if not hasattr(threading, "__mylock"):
			threading.__mylock = threading.Lock()

		with threading.__mylock:
			result = None
			self.core.uiAvailable = False

			if kwargs["nodeType"] == "google_docs":
				self.readGoogleDocs(pdgCallback=kwargs["pdgCallback"], itemHolder=kwargs["itemHolder"], upstreamItems=kwargs["upstreamItems"])
			elif kwargs["nodeType"] == "createEntity":
				self.createEntity(pdgCallback=kwargs["pdgCallback"], itemHolder=kwargs["itemHolder"], upstreamItems=kwargs["upstreamItems"])
			elif kwargs["nodeType"] == "writeEntity":
				result = self.writeEntity(workItem=kwargs["workItem"])
			elif kwargs["nodeType"] == "combineStates":
				self.combineStates(pdgCallback=kwargs["pdgCallback"], itemHolder=kwargs["itemHolder"], upstreamItems=kwargs["upstreamItems"])
			elif kwargs["nodeType"] == "createState":
				self.createState(pdgCallback=kwargs["pdgCallback"], itemHolder=kwargs["itemHolder"], upstreamItems=kwargs["upstreamItems"])
			elif kwargs["nodeType"] == "writeStates":
				result = self.writeStates(pdgCallback=kwargs["pdgCallback"], itemHolder=kwargs["itemHolder"], upstreamItems=kwargs["upstreamItems"])
			elif kwargs["nodeType"] == "createDependencies":
				self.createDependencies(pdgCallback=kwargs["pdgCallback"], itemHolder=kwargs["itemHolder"])
			elif kwargs["nodeType"] == "setProject":
				self.setProject(workItem=kwargs["workItem"])
			else:
				self.core.popup("Unknown nodetype: %s" % kwargs["nodeType"])

			self.core.uiAvailable = True
			return result


	@err_decorator
	def createWorkItems(self, itemHolder, upstreamItems, entityType, entityData):
		if entityType == "assets":
			for entity in entityData:
				item = itemHolder.addWorkItem()
				item.data.setString('type', "asset", 0)
				item.data.setString('hierarchy', entity["hierarchy"], 0)
				item.data.setString('name', entity["asset"], 0)
		if entityType == "shots":
			for entity in entityData:
				item = itemHolder.addWorkItem()
				item.data.setString('type', "shot", 0)
				item.data.setString('sequence', entity["sequence"], 0)
				item.data.setString('name', entity["shot"], 0)
				item.data.setString('framerange', entity["startframe"], 0)
				item.data.setString('framerange', entity["endframe"], 1)


	@err_decorator
	def setupNode(self, entityType, node):
		if entityType == "fromFile":
			cNode = node.createOutputNode("prism_create_entity")
			cNode.parm("entity").set("file")
		elif entityType == "project":
			cNode = node.createOutputNode("prism_create_entity")
			cNode.parm("entity").set("project")
		elif entityType == "asset":
			cNode = node.createOutputNode("prism_create_entity")
			cNode.parm("entity").set("asset")
		elif entityType == "shot":
			cNode = node.createOutputNode("prism_create_entity")
			cNode.parm("entity").set("shot")
		elif entityType == "step":
			cNode = node.createOutputNode("prism_create_entity")
			cNode.parm("entity").set("step")
		elif entityType == "category":
			cNode = node.createOutputNode("prism_create_entity")
			cNode.parm("entity").set("category")
		elif entityType == "scenefile":
			cNode = node.createOutputNode("prism_create_entity")
			cNode.parm("entity").set("scenefile")
		elif entityType == "write":
			cNode = node.createOutputNode("prism_write_entity")
		elif entityType == "setProject":
			cNode = node.createOutputNode("prism_set_project")
		elif entityType == "create_state":
			cNode = node.createOutputNode("prism_create_state")
		elif entityType == "write_states":
			cNode = node.createOutputNode("prism_write_states")
		else:
			self.core.popup("Invalid type: %s" % entityType)
			return

		if QApplication.keyboardModifiers() != Qt.ShiftModifier:
			cNode.setCurrent(True, clear_all_selected=True)

		return cNode


	@err_decorator
	def readGoogleDocs(self, pdgCallback, itemHolder, upstreamItems):
		node = hou.nodeBySessionId(pdgCallback.customId)
		parentNode = node.parent()
		auth = parentNode.parm("authorization").eval()
		docName = parentNode.parm("document").eval()
		sheetName = parentNode.parm("sheet").eval()
		entityType = parentNode.parm("entity").evalAsString()
		fromRow = parentNode.parm("fromRow").eval()
		useToRow = parentNode.parm("useToRow").eval()
		toRow = parentNode.parm("toRow").eval()
		sequenceCol = ord(parentNode.parm("sequence").eval().lower()) - 96
		shotCol = ord(parentNode.parm("shot").eval().lower()) - 96
		startframeCol = ord(parentNode.parm("startframe").eval().lower()) - 96
		endframeCol = ord(parentNode.parm("endframe").eval().lower()) - 96
		hierarchyCol = ord(parentNode.parm("hierarchy").eval().lower()) - 96
		assetCol = ord(parentNode.parm("asset").eval().lower()) - 96

		if not useToRow:
			toRow = -1

		if entityType == "assets":
			columns = {"hierarchy":hierarchyCol, "asset":assetCol}
		else:
			columns = {"sequence":sequenceCol, "shot":shotCol, "startframe":startframeCol, "endframe":endframeCol}
		from PrismUtils import GoogleDocs
		entityData = GoogleDocs.readGDocs(self.core, auth, docName, sheetName, sorted(columns.values()), fromRow, toRow)
		colNames = sorted(columns.keys(), key=lambda x: columns[x])
		dataDicts = []
		for i in entityData:
			entityDict = {}
			for name in colNames:
				entityDict[name] = i[colNames.index(name)]
			dataDicts.append(entityDict)

		self.createWorkItems(itemHolder, upstreamItems, entityType, dataDicts)


	@err_decorator
	def createEntity(self, pdgCallback, itemHolder, upstreamItems):
		parentNode = hou.nodeBySessionId(pdgCallback.customId).parent()
		entity = parentNode.parm("entity").eval()

		if entity == 0:
			filepath = parentNode.parm("definitionfile").eval()
			
			if os.path.exists(filepath):
				with open(filepath, 'r') as f:
					defData = json.load(f)
				
				if "ASSETS" in defData:
					for assetCat in defData["ASSETS"]:
						for asset in defData["ASSETS"][assetCat]:
							item = itemHolder.addWorkItem()
							item.data.setString('type', "asset", 0)
							item.data.setString('hierarchy', assetCat, 0)
							item.data.setString('name', asset, 0)
			
				if "SHOTS" in defData:
					for seq in defData["SHOTS"]:
						for shot in defData["SHOTS"][seq]:
							item = itemHolder.addWorkItem()
							item.data.setString('type', "shot", 0)
							item.data.setString('sequence', seq, 0)
							item.data.setString('name', shot, 0)

		elif entity == 1:
			if upstreamItems:
				for upstreamItem in upstreamItems:
					item = itemHolder.addWorkItem(cloneResultData=True, preserveType=True, parent=upstreamItem)
					item.data.setString('type', "project", 0)
					path = parentNode.parm("projectPath").eval() or upstreamItem.data.stringData("path", 0) or ""
					name = parentNode.parm("projectName").eval() or upstreamItem.data.stringData("name", 0) or ""
					item.data.setString('path', path, 0)
					item.data.setString('name', name, 0)
			else:
				item = itemHolder.addWorkItem()
				item.data.setString('type', "project", 0)
				item.data.setString('path', parentNode.parm("projectPath").eval(), 0)
				item.data.setString('name', parentNode.parm("projectName").eval(), 0)

		elif entity == 2:
			if upstreamItems:
				for upstreamItem in upstreamItems:
					item = itemHolder.addWorkItem(cloneResultData=True, preserveType=True, parent=upstreamItem)
					item.data.setString('type', "asset", 0)
					if upstreamItem.data.stringData("hierarchy", 0):
						path = "%s/%s" % (upstreamItem.data.stringData("hierarchy", 0), parentNode.parm("assetHierarchy").eval())
					else:
						path = parentNode.parm("assetHierarchy").eval()
					name = parentNode.parm("assetName").eval() or upstreamItem.data.stringData("name", 0) or ""
					item.data.setString('hierarchy', path, 0)
					item.data.setString('name', name, 0)
			else:
				item = itemHolder.addWorkItem()
				item.data.setString('type', "asset", 0)
				item.data.setString('hierarchy', parentNode.parm("assetHierarchy").eval(), 0)
				item.data.setString('name', parentNode.parm("assetName").eval(), 0)
			
		elif entity == 3:
			if upstreamItems:
				for upstreamItem in upstreamItems:
					item = itemHolder.addWorkItem(cloneResultData=True, preserveType=True, parent=upstreamItem)
					item.data.setString('type', "shot", 0)
					path = parentNode.parm("sequence").eval() or upstreamItem.data.stringData("sequence", 0) or ""
					name = parentNode.parm("shotName").eval() or upstreamItem.data.stringData("name", 0) or ""
					if parentNode.parm("useRange").eval():
						rangeStart = str(parentNode.parm("shotrangex").evalAsString())
						rangeEnd = str(parentNode.parm("shotrangey").evalAsString())
						item.data.setString('framerange', rangeStart, 0)
						item.data.setString('framerange', rangeEnd, 1)
					item.data.setString('sequence', path, 0)
					item.data.setString('name', name, 0)
			else:
				item = itemHolder.addWorkItem()
				item.data.setString('type', "shot", 0)
				item.data.setString('sequence', parentNode.parm("sequence").eval(), 0)
				item.data.setString('name', parentNode.parm("shotName").eval(), 0)
				if parentNode.parm("useRange").eval():
					item.data.setString('framerange', parentNode.parm("shotrangex").evalAsString(), 0)
					item.data.setString('framerange', parentNode.parm("shotrangey").evalAsString(), 1)
			
		elif entity == 4:
			for upstreamItem in upstreamItems:
				curType = upstreamItem.data.stringData("type", 0)
				if curType in ["asset", "shot"]:
					item = itemHolder.addWorkItem(cloneResultData=True, preserveType=True, parent=upstreamItem)
					item.data.setString('type', "step", 0)
					item.data.setString('%sName' % curType, upstreamItem.data.stringData("name", 0), 0)
					item.data.setString('name', parentNode.parm("stepName").eval(), 0)
					
		elif entity == 5:
			for upstreamItem in upstreamItems:
				curType = upstreamItem.data.stringData("type", 0)
				if curType in ["step"]:
					if parentNode.parm("defaultCategory").eval():
						import ast
						try:
							steps = ast.literal_eval(self.core.getConfig('globals', "pipeline_steps", configPath=self.core.prismIni))
						except:
							continue

						if type(steps) != dict:
							steps = {}
						
						steps = {validSteps: steps[validSteps] for validSteps in steps}
						stepName = upstreamItem.data.stringData("name", 0)
						if stepName not in steps:
							continue
				
						catName = steps[stepName]
					else:
						catName = parentNode.parm("categoryName").eval()
				
					item = itemHolder.addWorkItem(cloneResultData=True, preserveType=True, parent=upstreamItem)
					item.data.setString('type', "category", 0)
					item.data.setString('step', upstreamItem.data.stringData("name", 0), 0)
					item.data.setString('name', catName, 0)
					
		elif entity == 6:
			for upstreamItem in upstreamItems:
				curType = upstreamItem.data.stringData("type", 0)
				if curType in ["category"]:
					item = itemHolder.addWorkItem(cloneResultData=True, preserveType=True, parent=upstreamItem)
					item.data.setString('type', "scenefile", 0)
					item.data.setString('category', upstreamItem.data.stringData("name", 0), 0)
					item.data.setString('source', parentNode.parm("scenefileSource").eval(), 0)
					item.data.setString('comment', parentNode.parm("scenefileComment").eval(), 0)


	@err_decorator
	def writeEntity(self, workItem):
		data = workItem.data.allDataMap
		if "type" not in data:
			return "Error - invalid workitem"

		result = self.core.createEntity(entity=data)

		if workItem.attrib("type").value() == "scenefile":
			# workItem.addResultData(result, "scenePath", 0)
			workItem.setStringAttrib("scenePath", result, 0)

		return result


	@err_decorator
	def combineStates(self, pdgCallback, itemHolder, upstreamItems):
		parentNode = hou.nodeBySessionId(pdgCallback.customId).parent()
		unique = parentNode.parm("uniqueEntities").eval()
		combineStates = parentNode.parm("combineStates").eval()

		entities = []

		up_items = upstreamItems
		for item in up_items:
			if not unique:
				data = item.data.allDataMap
				states = data.get("states", [])
				entities.append({"item":item, "states":states})
				continue
				
			for e in entities:
				itemData = item.data.allDataMap
				eData = e["item"].data.allDataMap
				
				iStates = itemData.pop("states", None) or []
				eStates = eData.pop("states", None) or []
				if itemData == eData:
					if combineStates:
						e["states"] += iStates
					break
			else:
				data = item.data.allDataMap
				states = data.get("states", [])
				entities.append({"item":item, "states":states})
			
		for e in entities:
			item = itemHolder.addWorkItem(cloneResultData=True, preserveType=True,
					parent=e["item"])
			if "states" in e:
				item.data.setStringArray("states", e["states"])

	@err_decorator
	def createState(self, pdgCallback, itemHolder, upstreamItems):
		parentNode = hou.nodeBySessionId(pdgCallback.customId).parent()
		className = parentNode.parm("stateType").menuItems()[parentNode.parm("stateType").eval()]
		execute = parentNode.parm("execState").eval()
		usePreScript = parentNode.parm("usePreScript").eval()
		preScript = parentNode.parm("preScript").eval()
		usePostScript = parentNode.parm("usePostScript").eval()
		postScript = parentNode.parm("postScript").eval()
		settings = parentNode.parm("stateSettings").eval().replace("\n", "")
		imports = []

		if className in ["default_ImportFile", "hou_ImportFile"] and parentNode.parm("importFromInput").eval():
			for upstreamItem in upstreamItems:
				if upstreamItem.data.intData("second_input", 0):
					states = upstreamItem.data.stringDataArray("states")
					if not parentNode.parm("ignoreInputEntity").eval():
						assetName = upstreamItem.data.stringData("assetName", 0)
						shotName = upstreamItem.data.stringData("shotName", 0)
					if states:
						for state in states:
							stateData = eval(state)
							if "settings" in stateData:
								stateDict = eval("{%s}" % stateData["settings"].replace("=", ":"))
								if parentNode.parm("ignoreInputEntity").eval():
									if "taskname" in stateDict and stateDict["taskname"] not in imports:
										imports.append(stateDict["taskname"])
								else:
									if assetName:
										entity = "asset"
										entityName = assetName
									elif shotName:
										entity = "shot"
										entityName = shotName
									elif "imports" in stateData:
										imports += stateData["imports"]
									else:
										continue
										
									if "taskname" in stateDict:
										imports.append("%s|%s|%s" % (entity, entityName, stateDict["taskname"]))
					  
		for upstreamItem in upstreamItems:
			if upstreamItem.data.intData("second_input", 0):
				continue
				
			item = itemHolder.addWorkItem(cloneResultData=True, preserveType=True,
				parent=upstreamItem)

			overrideSettings = ""
			for orId in range(parentNode.parm("overrideSettings").eval()):
				with item.makeActive():
					orSetting = parentNode.parm("orSetting%s" % (orId+1)).eval()
					orVal = parentNode.parm("orValue%s" % (orId+1)).eval()

				overrideSettings += "\"%s\" = \"%s\"," % (orSetting, orVal)

			curStates = item.data.dataArray("states") or []
			stateData = {"stateType": className, "execute": execute, "settings": settings, "overrideSettings": overrideSettings}
			
			if execute:
				if usePreScript:
					stateData["preScript"] = preScript.replace("\n", ";")
				if usePostScript:
					stateData["postScript"] = postScript.replace("\n", ";")
					
			if imports:
				if parentNode.parm("ignoreInputEntity").eval():
					assetName = upstreamItem.data.stringData("assetName", 0)
					shotName = upstreamItem.data.stringData("shotName", 0)
					
					if assetName:
						entity = "asset"
						entityName = assetName
					elif shotName:
						entity = "shot"
						entityName = shotName
					else:
						continue
					
					lImports = [ "%s|%s|%s" % (entity, entityName, x) for x in imports]
				else:
					lImports = imports

				stateData["imports"] = lImports
				
			curStates.append(str(stateData))
			item.data.setStringArray("states", curStates)


	@err_decorator
	def createDependencies(self, pdgCallback, itemHolder):
		parentNode = hou.nodeBySessionId(pdgCallback.customId).parent()
		className = "hou_ImportFile"
		execute = 1
		settings = ""
		dependencyStr = parentNode.parm("dependencies").eval()
		dependencies = dependencyStr.split("\n")
		imports = []
					  
		for dep in dependencies:
			if len(dep) == 0:
				continue
				
			if dep[0] == "#":
				continue
				
			imports.append(dep)
			
		item = itemHolder.addWorkItem(cloneResultData=True, preserveType=True)

		stateData = {"stateType": className, "execute": execute, "settings": settings}
		if imports:
			stateData["imports"] = imports

		item.data.setStringArray("states", [str(stateData)])


	@err_decorator
	def setProject(self, workItem):
		typeStr = workItem.attrib("type").value()
		if typeStr != "project":
			return

		prjPath = workItem.attrib("path").value()
		self.core.changeProject(prjPath)


	@err_decorator
	def writeStates(self, pdgCallback, itemHolder, upstreamItems):
		mayaPath = upstreamItems[0].envLookup("PDG_MAYAPY")
		mpy = mayaPath or "C:/Program Files/Autodesk/Maya2018/bin/mayapy.exe"
		hython = os.path.join(os.environ["HB"], "hython.exe")
		mayaPaths = []
		houPaths = []
		sceneStates = []
		for workItem in upstreamItems:
			# path = workItem.resultDataForTag("scenePath")
			path = [[workItem.data.stringData("scenePath", 0)]]
			if not path:
				self.core.popup("Unable to write states. Workitem doesn't contain a scenepath.")
				continue

			states = workItem.data.stringDataArray("states")
			if not states:
				self.core.popup("Unable to write states. Workitem doesn't contain states.")
				continue

			if os.path.splitext(path[0][0])[1] in self.core.getPluginData("Maya", "sceneFormats"):
				mayaPaths.append(path[0][0])
				sceneStates = map(lambda x: eval(x.replace("\\", "\\\\\\\\\\")), states)
			elif os.path.splitext(path[0][0])[1] in self.core.getPluginData("Houdini", "sceneFormats"):
				houPaths.append(path[0][0])
				sceneStates = map(lambda x: eval(x.replace("\\", "\\\\\\")), states)

		procs = []
		if mayaPaths:
			mayaCmd = self.getMayaCmd(mayaPaths, sceneStates)
			procs.append({"executable": mpy, "command": mayaCmd})

		if houPaths:
			houCmd = self.getHoudiniCmd(houPaths, sceneStates)
			procs.append({"executable": hython, "command": houCmd})


		stdout = ""
		for i in procs:
			if True: #if `@debug`:
				print "starting %s" % os.path.basename(i["executable"])
				proc = subprocess.Popen([i["executable"], "-c", i["command"]], stdout=subprocess.PIPE)
				for line in proc.stdout:
					line = "[stdout] %s" % line.replace("\n", "")
					sys.stdout.write(line)
					stdout += line
					
				proc.wait()
			else:
				proc = subprocess.Popen([i["executable"], "-c", i["command"]])
				stdout, stderr = proc.communicate()

		for upstreamItem in upstreamItems:
			item = itemHolder.addWorkItem(cloneResultData=True, preserveType=True, parent=upstreamItem)
			item.eraseAttrib("states")
				
		if "Scene was processed successfully" not in stdout:
			return False
		else:
			print "Completed state creations."

		return True


	@err_decorator
	def getMayaCmd(self, mayaPaths, sceneStates):
		cmd = """
import sys
from PySide2.QtCore import *
from PySide2.QtWidgets import *
QApplication(sys.argv)

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds

import PrismInit
pcore = PrismInit.prismInit(prismArgs=["noUI"])
scenePaths = eval("%s")
print "processing scenes: %%s" %% scenePaths
for scenePath in scenePaths:
	try:
		cmds.file( scenePath, o=True, force=True, ignoreVersion=True )
	except:
		if pcore.getCurrentFileName() == "":
			print "Couldn't load file. Loading all plugins and trying again."
			cmds.loadPlugin( allPlugins=True )
			cmds.file( scenePath, o=True, force=True, ignoreVersion=True )

	if pcore.getCurrentFileName() == "":
		print ("failed to load file: %%s" %% scenePath)
	else:
		print ("loaded file: %%s" %% scenePath)
		
		stateManager = pcore.stateManager()
		states = eval(\"\"\"%s\"\"\")
		for idx, state in enumerate(states):
			settings = state["settings"]
			try:
				settings = eval("{%%s}" %% settings.replace("=", ":"))
			except Exception as e:
				settings = {}

			if "overrideSettings" in state:
				orSettings = state["overrideSettings"]
				try:
					orSettings = eval("{%%s}" %% orSettings.replace("=", ":"))
				except Exception as e:
					orSettings = {}

				settings.update(orSettings)
				
			if "imports" in state and state["imports"]:
				settings["filepath"] = pcore.resolve(state["imports"][0])
			
			if "preScript" in state:
				pcore.appPlugin.executeScript(pcore, state["preScript"], execute=True)
				
			stateNameBase = state["stateType"].replace(state["stateType"].split("_", 1)[0] + "_", "")
			stateItem = stateManager.createState(stateNameBase, stateData=settings)
			if state["execute"]:
				if stateItem.ui.listType == "Import":
					getattr(stateItem.ui, "importObject", lambda: None)()
				elif stateItem.ui.listType == "Export":
					stateManager.publish(executeState=True, states=[stateItem])
				print "executed state %%s: %%s" %% (idx, stateNameBase)
				
			if "postScript" in state:
				pcore.appPlugin.executeScript(pcore, state["postScript"], execute=True)
				
		pcore.saveScene(comment=\"state added (PDG)\", versionUp=True)
		
	print "Scene was processed successfully"

		""" % (mayaPaths, sceneStates)
		return cmd


	@err_decorator
	def getHoudiniCmd(self, houPaths, sceneStates):
		cmd = """
import os, sys
import hou
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
		
QApplication.addLibraryPath(os.path.join(hou.expandString("$HFS"), "bin", "Qt_plugins"))
qApp = QApplication.instance()
if qApp is None:
	qApp = QApplication(sys.argv)
	
import PrismInit
pcore = PrismInit.prismInit(prismArgs=["noUI"])

scenePaths = eval("%s")
print "processing scenes: %%s" %% scenePaths
for scenePath in scenePaths:
	hou.hipFile.load(file_name=scenePath, ignore_load_warnings=True)

	if pcore.getCurrentFileName() == "":
		print ("failed to load file: %%s" %% scenePath)
	else:
		print ("loaded file: %%s" %% scenePath)
		
		stateManager = pcore.stateManager()
		states = eval(\"\"\"%s\"\"\")
		for idx, state in enumerate(states):
			settings = state["settings"]
			try:
				settings = eval("{%%s}" %% settings.replace("=", ":"))
			except Exception as e:
				settings = {}

			if "overrideSettings" in state:
				orSettings = state["overrideSettings"]
				try:
					orSettings = eval("{%%s}" %% orSettings.replace("=", ":"))
				except Exception as e:
					orSettings = {}

				settings.update(orSettings)
				
			if "imports" in state and state["imports"]:
				settings["filepath"] = pcore.resolve(state["imports"][0])
			
			if "preScript" in state:
				print("Pre-creation script: " + state["preScript"])
				pcore.appPlugin.executeScript(pcore, state["preScript"], execute=True)
				
			stateNameBase = state["stateType"].replace(state["stateType"].split("_", 1)[0] + "_", "")
			stateItem = stateManager.createState(stateNameBase, stateData=settings)

			if "postScript" in state:
				pcore.appPlugin.executeScript(pcore, state["postScript"], execute=True)
				
			if state["execute"]:
				if stateItem.ui.listType == "Import":
					getattr(stateItem.ui, "importObject", lambda: None)()
				elif stateItem.ui.listType == "Export":
					stateManager.publish(executeState=True, states=[stateItem])
				print "executed state %%s: %%s" %% (idx, stateNameBase)
				
		pcore.saveScene(comment=\"state added (PDG)\", versionUp=True)
		
	print "Scene was processed successfully"

		""" % (houPaths, sceneStates)
		return cmd
