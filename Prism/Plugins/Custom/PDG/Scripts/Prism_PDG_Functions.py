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



import os, sys, traceback, time, subprocess
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


	# the following function are called by Prism at specific events, which are indicated by the function names
	# you can add your own code to any of these functions.
	@err_decorator
	def onProjectCreated(self, origin, projectPath, projectName):
		pass


	@err_decorator
	def onProjectChanged(self, origin):
		pass


	@err_decorator
	def projectBrowser_loadUI(self, origin):
		pass


	@err_decorator
	def onProjectBrowserStartup(self, origin):
		pass


	@err_decorator
	def onProjectBrowserClose(self, origin):
		pass


	@err_decorator
	def onPrismSettingsOpen(self, origin):
		pass


	@err_decorator
	def onPrismSettingsSave(self, origin):
		pass


	@err_decorator
	def onStateManagerOpen(self, origin):
		pass


	@err_decorator
	def onStateManagerClose(self, origin):
		pass


	@err_decorator
	def onSelectTaskOpen(self, origin):
		pass


	@err_decorator
	def onStateCreated(self, origin):
		pass


	@err_decorator
	def onStateDeleted(self, origin):
		pass


	@err_decorator
	def onPublish(self, origin):
		pass


	@err_decorator
	def postPublish(self, origin, publishType):
		'''
		origin: 		StateManager instance
		publishType: 	The type (string) of the publish. 
						Can be "stateExecution" (state was executed from the context menu) or "publish" (publish button was pressed)
		'''


	@err_decorator
	def onAboutToSaveFile(self, origin, filepath, versionUp, comment, isPublish):
		'''
		origin: 	PrismCore instance
		filepath: 	The filepath of the scenefile, which will be saved
		versionUp: 	(bool) True if this save increments the version of that scenefile
		comment: 	The string, which is used as the comment for the scenefile. Empty string if no comment was given.
		isPublish: 	(bool) True if this save was triggered by a publish
		'''


	@err_decorator
	def onSaveFile(self, origin, filepath, versionUp, comment, isPublish):
		'''
		origin: 	PrismCore instance
		filepath: 	The filepath of the scenefile, which was saved
		versionUp: 	(bool) True if this save increments the version of that scenefile
		comment: 	The string, which is used as the comment for the scenefile. Empty string if no comment was given.
		isPublish: 	(bool) True if this save was triggered by a publish
		'''


	@err_decorator
	def onSceneOpen(self, origin, filepath):
		# called when a scenefile gets opened from the Project Browser. Gets NOT called when a scenefile is loaded manually from the file menu in a DCC app.
		pass


	@err_decorator
	def onAssetDlgOpen(self, origin, assetDialog):
		pass


	@err_decorator
	def onAssetCreated(self, origin, assetName, assetPath, assetDialog=None):
		pass


	@err_decorator
	def onStepDlgOpen(self, origin, dialog):
		pass


	@err_decorator
	def onStepCreated(self, origin, entity, stepname, path, settings):
		# entity: "asset" or "shot"
		# settings: dictionary containing "createDefaultCategory", which holds a boolean (settings["createDefaultCategory"])
		pass


	@err_decorator
	def onCategroyDlgOpen(self, origin, catDialog):
		pass


	@err_decorator
	def onCategoryCreated(self, origin, catname, path):
		pass


	@err_decorator
	def onShotDlgOpen(self, origin, shotDialog, shotName=None):
		# gets called just before the "Create Shot"/"Edit Shot" dialog opens. Check if "shotName" is None to check if a new shot will be created or if an existing shot will be edited.
		pass


	@err_decorator
	def onShotCreated(self, origin, sequenceName, shotName):
		pass

		
	@err_decorator
	def openPBFileContextMenu(self, origin, rcmenu, index):
		# gets called before "rcmenu" get displayed. Can be used to modify the context menu when the user right clicks in the scenefile lists of assets or shots in the Project Browser.
		pass


	@err_decorator
	def openPBListContextMenu(self, origin, rcmenu, listWidget, item, path):
		# gets called before "rcmenu" get displayed for the "Tasks" and "Versions" list in the Project Browser.
		pass


	@err_decorator
	def openPBAssetContextMenu(self, origin, rcmenu, index):
		'''
		origin: Project Browser instance
		rcmenu: QMenu object, which can be modified before it gets displayed
		index: QModelIndex object of the item on which the user clicked. Use index.data() to get the text of the index.
		'''
		pass


	@err_decorator
	def openPBAssetStepContextMenu(self, origin, rcmenu, index):
		pass


	@err_decorator
	def openPBAssetCategoryContextMenu(self, origin, rcmenu, index):
		pass


	@err_decorator
	def openPBShotContextMenu(self, origin, rcmenu, index):
		pass


	@err_decorator
	def openPBShotStepContextMenu(self, origin, rcmenu, index):
		pass


	@err_decorator
	def openPBShotCategoryContextMenu(self, origin, rcmenu, index):
		pass


	@err_decorator
	def openTrayContextMenu(self, origin, rcmenu):
		pass


	@err_decorator
	def preLoadEmptyScene(self, origin, filepath):
		pass


	@err_decorator
	def postLoadEmptyScene(self, origin, filepath):
		pass


	@err_decorator
	def preImport(self, *args, **kwargs):
		pass


	@err_decorator
	def postImport(self, *args, **kwargs):
		pass


	@err_decorator
	def preExport(self, *args, **kwargs):
		pass


	@err_decorator
	def postExport(self, *args, **kwargs):
		pass


	@err_decorator
	def prePlayblast(self, *args, **kwargs):
		pass


	@err_decorator
	def postPlayblast(self, *args, **kwargs):
		pass


	@err_decorator
	def preRender(self, *args, **kwargs):
		pass


	@err_decorator
	def postRender(self, *args, **kwargs):
		pass


	@err_decorator
	def maya_export_abc(self, origin, params):
		'''
		origin: reference to the Maya Plugin class
		params: dict containing the mel command (params["export_cmd"])

		Gets called immediately before Prism exports an alembic file from Maya
		This function can modify the mel command, which Prism will execute to export the file.

		Example:
		print params["export_cmd"]
		>>AbcExport -j "-frameRange 1000 1000 -root |pCube1  -worldSpace -uvWrite -writeVisibility  -file \"D:\\\\Projects\\\\Project\\\\03_Workflow\\\\Shots\\\\maya-001\\\\Export\\\\Box\\\\v0001_comment_rfr\\\\centimeter\\\\shot_maya-001_Box_v0001.abc\"" 
		
		Use python string formatting to modify the command:
		params["export_cmd"] = params["export_cmd"][:-1] + " -attr material" + params["export_cmd"][-1]
		'''

	@err_decorator
	def preSubmit_Deadline(self, origin, jobInfos, pluginInfos, arguments):
		'''
		origin: reference to the Deadline plugin class
		jobInfos: List containing the data that will be written to the JobInfo file. Can be modified.
		pluginInfos: List containing the data that will be written to the PluginInfo file. Can be modified.
		arguments: List of arguments that will be send to the Deadline submitter. This contains filepaths to all submitted files (note that they are eventually not created at this point).
		
		Gets called before a render or simulation job gets submitted to the Deadline renderfarmmanager.
		This function can modify the submission parameters.

		Example:
		jobInfos["PostJobScript"] = "D:/Scripts/Deadline/myPostJobTasks.py"

		You can find more available job parameters here:
		https://docs.thinkboxsoftware.com/products/deadline/10.0/1_User%20Manual/manual/manual-submission.html
		'''


	@err_decorator
	def postSubmit_Deadline(self, origin, result):
		'''
		origin: reference to the Deadline plugin class
		result: the return value from the Deadline submission.
		'''


	@err_decorator
	def cookNode(self, pdgCallback, itemHolder, upstreamItems=None):
		node = hou.nodeBySessionId(pdgCallback.customId)
		parentNode = node.parent()
		if parentNode.type().name() == "prism_google_docs":
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
		else:
			return

		if QApplication.keyboardModifiers() != Qt.ShiftModifier:
			cNode.setCurrent(True, clear_all_selected=True)

		return cNode
