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



import os, sys, traceback, time, subprocess
from functools import wraps

try:
	import hou
except:
	pass

try:
	from PySide2.QtCore import *
	from PySide2.QtGui import *
	from PySide2.QtWidgets import *
	psVersion = 2
except:
	from PySide.QtCore import *
	from PySide.QtGui import *
	psVersion = 1


class Prism_Deadline_Functions(object):
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
				erStr = ("%s ERROR - Prism_Plugin_Deadline %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].plugin.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def isActive(self):
		return len(self.getDeadlineGroups()) > 0


	@err_decorator
	def deadlineCommand(self, arguments, background=True, readStdout=True):
		deadlineBin = os.getenv('DEADLINE_PATH')
		if deadlineBin is None:
			return False
		deadlineCommand = os.path.join( deadlineBin, "deadlinecommand.exe" )

		startupinfo = None
		creationflags = 0
		if background:
			startupinfo = subprocess.STARTUPINFO()
			startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
		else:
			# still show top-level windows, but don't show a console window
			CREATE_NO_WINDOW = 0x08000000   #MSDN process creation flag
			creationflags = CREATE_NO_WINDOW

		arguments.insert( 0, deadlineCommand)
		
		stdoutPipe = None
		if readStdout:
			stdoutPipe=subprocess.PIPE
			
		# Specifying PIPE for all handles to workaround a Python bug on Windows. The unused handles are then closed immediatley afterwards.
		proc = subprocess.Popen(arguments, cwd=deadlineBin, stdin=subprocess.PIPE, stdout=stdoutPipe, stderr=subprocess.PIPE, startupinfo=startupinfo, creationflags=creationflags )
		proc.stdin.close()
		proc.stderr.close()

		output = ""
		if readStdout:
			output = proc.stdout.read()
		return output


	@err_decorator
	def blenderDeadlineCommand(self):
		deadlineBin = ""
		try:
			deadlineBin = os.environ['DEADLINE_PATH']
		except KeyError:
			pass

		if deadlineBin == "":
			return None

		deadlineCommand = os.path.join(deadlineBin, "deadlinecommand")
		
		return deadlineCommand


	@err_decorator
	def getDeadlineGroups(self, subdir=None):
		if not hasattr(self, "deadlineGroups"):
			if self.core.plugin.appName == "Blender":
				deadlineCommand = self.blenderDeadlineCommand()
				
				if deadlineCommand is None:
					return []

				startupinfo = None

				args = [deadlineCommand, "-groups"]   
				if subdir != None and subdir != "":
					args.append(subdir)
				
				# Specifying PIPE for all handles to workaround a Python bug on Windows. The unused handles are then closed immediatley afterwards.
				proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo)

				proc.stdin.close()
				proc.stderr.close()

				output = proc.stdout.read()

				output = output.decode("utf_8")

			else:
				output = self.deadlineCommand( ["-groups",] )

			if output != False and not "Error" in output:
				self.deadlineGroups = output.splitlines()
			else:
				self.deadlineGroups = []

		return self.deadlineGroups


	@err_decorator
	def sm_dep_startup(self, origin):
		origin.tw_caches.itemClicked.connect(lambda x,y: self.sm_updateDlDeps(origin, x, y))
		origin.tw_caches.itemDoubleClicked.connect(self.sm_dlGoToNode)


	@err_decorator
	def sm_updateDlDeps(self, origin, item, column):
		if len(item.toolTip(0).split("\n")) == 1:
			return

		if item.toolTip(0).split("\n")[1] in [x.split("\n")[1] for x in origin.dependencies["Deadline"]] and item.checkState(0) == Qt.Unchecked:
			origin.dependencies["Deadline"].remove(item.toolTip(0))
		elif (not item.toolTip(0).split("\n")[1] in [x.split("\n")[1] for x in origin.dependencies["Deadline"]]) and item.checkState(0) == Qt.Checked:
			origin.dependencies["Deadline"].append(item.toolTip(0))

		origin.nameChanged(origin.e_name.text())

		origin.stateManager.saveStatesToScene()


	@err_decorator
	def sm_dlGoToNode(self,item, column):
		if item.parent() is None:
			return

		node = hou.node(item.toolTip(0).split("\n")[1])

		if node is not None:
			node.setCurrent(True, clear_all_selected=True)
			paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
			if paneTab is not None:
				paneTab.frameSelection()


	@err_decorator
	def sm_dep_updateUI(self, origin):
		origin.gb_osDependency.setVisible(False)
		origin.gb_dlDependency.setVisible(True)

		origin.tw_caches.clear()
		QTreeWidgetItem(origin.tw_caches, ["Import"])
		QTreeWidgetItem(origin.tw_caches, ["Export"])

		fileNodeList = []
		copFileNodeList = []
		ropDopNodeList = []
		ropCopNodeList = []
		ropSopNodeList = []
		ropAbcNodeList = []
		filecacheNodeList = []

		for node in hou.node("/").allSubChildren():
			if node.type().name() == "file":
				if node.type().category().name() == "Sop" and len(node.parm("file").keyframes()) == 0:
					fileNodeList.append(node)
				elif node.type().category().name() == "Cop2" and len(node.parm("filename1").keyframes()) == 0:
					copFileNodeList.append(node)
			elif node.type().name() == "rop_dop" and len(node.parm("dopoutput").keyframes()) == 0:
				ropDopNodeList.append(node)
			elif node.type().name() == "rop_comp" and len(node.parm("copoutput").keyframes()) == 0:
				ropCopNodeList.append(node)
			elif node.type().name() == "rop_geometry" and len(node.parm("sopoutput").keyframes()) == 0:
				ropSopNodeList.append(node)
			elif node.type().name() == "rop_alembic" and len(node.parm("filename").keyframes()) == 0:
				ropAbcNodeList.append(node)
			elif node.type().name() == "filecache" and len(node.parm("file").keyframes()) == 0:
				filecacheNodeList.append(node)

		for i in fileNodeList:
			itemName = os.path.basename(i.path())
			item = QTreeWidgetItem(origin.tw_caches.topLevelItem(0), [itemName])
			item.setToolTip(0, i.parm("file").unexpandedString() + "\n" + i.path())

		for i in copFileNodeList:
			itemName = os.path.basename(i.path())
			item = QTreeWidgetItem(origin.tw_caches.topLevelItem(0), [itemName])
			item.setToolTip(0, i.parm("filename1").unexpandedString() + "\n" + i.path())

		for i in ropDopNodeList:
			itemName = os.path.basename(i.path())
			item = QTreeWidgetItem(origin.tw_caches.topLevelItem(1), [itemName])
			item.setToolTip(0, i.parm("dopoutput").unexpandedString() + "\n" + i.path())

		for i in ropCopNodeList:
			itemName = os.path.basename(i.path())
			item = QTreeWidgetItem(origin.tw_caches.topLevelItem(1), [itemName])
			item.setToolTip(0, i.parm("copoutput").unexpandedString() + "\n" + i.path())

		for i in ropSopNodeList:
			itemName = os.path.basename(i.path())
			item = QTreeWidgetItem(origin.tw_caches.topLevelItem(1), [itemName])
			item.setToolTip(0, i.parm("sopoutput").unexpandedString() + "\n" + i.path())

		for i in filecacheNodeList:
			itemName = os.path.basename(i.path())
			item = QTreeWidgetItem(origin.tw_caches.topLevelItem(1), [itemName])
			item.setToolTip(0, i.parm("file").unexpandedString() + "\n" + i.path())

		#alembic dependency disabled because no progress measureable
		for i in ropAbcNodeList:
			itemName = os.path.basename(i.parm("filename").unexpandedString())
			item = QTreeWidgetItem(origin.tw_caches.topLevelItem(1), [itemName])
			item.setToolTip(0, i.parm("filename").unexpandedString() + "\n" + i.path())

		items = []
		for i in range(origin.tw_caches.topLevelItemCount()):
			origin.tw_caches.topLevelItem(i).setExpanded(True)
			for k in range(origin.tw_caches.topLevelItem(i).childCount()):
				items.append(origin.tw_caches.topLevelItem(i).child(k))

		newActive = []
		for i in items:
			if i.toolTip(0).split("\n")[1] in [x.split("\n")[1] for x in origin.dependencies["Deadline"]]:
				i.setCheckState(0, Qt.Checked)
				newActive.append(i.toolTip(0))
			else:
				i.setCheckState(0, Qt.Unchecked)

		origin.dependencies["Deadline"] = newActive


	@err_decorator
	def sm_dep_preExecute(self, origin):
		warnings = []

		return warnings


	@err_decorator
	def sm_dep_execute(self, origin, parent):
		origin.dependencies["Deadline"] = [x if not x.split("\n")[0] in origin.stateManager.publishInfos["updatedExports"] else "%s\n%s" % (origin.stateManager.publishInfos["updatedExports"][x.split("\n")[0]], x.split("\n")[1]) for x in origin.dependencies["Deadline"]]
		
		parent.dependencies += [[origin.sp_offset.value(), hou.expandString(x.split("\n")[0])] for x in origin.dependencies["Deadline"]]


	@err_decorator
	def sm_houExport_startup(self, origin):
		origin.cb_dlGroup.addItems(self.getDeadlineGroups())


	@err_decorator
	def sm_houExport_activated(self, origin):
		origin.f_osDependencies.setVisible(False)
		origin.f_osUpload.setVisible(False)
		origin.f_osPAssets.setVisible(False)
		origin.gb_osSlaves.setVisible(False)
		origin.f_dlGroup.setVisible(True)


	@err_decorator
	def sm_houExport_preExecute(self, origin):
		warnings = []

		return warnings


	@err_decorator
	def sm_houExport_submitJob(self, origin, jobOutputFile, parent):
		jobOutputFile = jobOutputFile.replace("$F4", "####")

		homeDir = (self.deadlineCommand( ["-GetCurrentUserHomeDirectory",] ))

		if homeDir == False:
			return "Execute Canceled: Deadline is not installed"

		homeDir = homeDir.replace( "\r", "" ).replace( "\n", "" )

		dependencies = parent.dependencies

		jobName = os.path.splitext(hou.hipFile.basename())[0] + origin.l_taskName2.text()
		jobComment = "Prism-Submission-Export"
		jobGroup = origin.cb_dlGroup.currentText()
		jobPrio = origin.sp_rjPrio.value()
		jobTimeOut = str(origin.sp_rjTimeout.value())
		jobMachineLimit = "0"
		jobFamesPerTask = origin.sp_rjFramesPerTask.value()

		if origin.chb_globalRange.isChecked():
			jobFrames = str(origin.stateManager.sp_rangeStart.value()) + "-" + str(origin.stateManager.sp_rangeEnd.value())
		else:
			jobFrames = str(origin.sp_rangeStart.value()) + "-" + str(origin.sp_rangeEnd.value())


		# Create submission info file
		jobInfoFile = os.path.join(homeDir, "temp", "houdini_submit_info.job" )
		fileHandle = open( jobInfoFile, "w" )

		fileHandle.write( "Plugin=Houdini\n" )
		fileHandle.write( "Name=%s\n" % jobName )
		fileHandle.write( "Comment=%s\n" % jobComment )
		fileHandle.write( "Group=%s\n" % jobGroup )
		fileHandle.write( "Priority=%s\n" % jobPrio )
		fileHandle.write( "TaskTimeoutMinutes=%s\n" % jobTimeOut )
		fileHandle.write( "MachineLimit=%s\n" % jobMachineLimit )
		fileHandle.write( "Frames=%s\n" % jobFrames )
		fileHandle.write( "ChunkSize=%s\n" % jobFamesPerTask )
		fileHandle.write( "OutputFilename0=%s\n" % jobOutputFile )
		if origin.chb_rjSuspended.isChecked():
			fileHandle.write( "InitialStatus=Suspended\n" )

		if len(dependencies) > 0:
			fileHandle.write( "IsFrameDependent=true\n" )
			fileHandle.write( "ScriptDependencies=%s\n" % (os.path.join(self.core.projectPath, "00_Pipeline", "Scripts", "DeadlineDependency.py") ))
		
		fileHandle.close()


		nodeName = origin.node.path()
		ignoreInputs = "True"
		hBuild = "64bit"

		# Create plugin info file
		pluginInfoFile = os.path.join( homeDir, "temp", "houdini_plugin_info.job" )
		fileHandle = open( pluginInfoFile, "w" )

		fileHandle.write( "OutputDriver=%s\n" % nodeName )

		fileHandle.write( "IgnoreInputs=%s\n" % ignoreInputs )
		if int(self.deadlineCommand( ["-version",] ).split(".")[0][1:]) > 9:
			fileHandle.write( "Version=%s.%s\n" % (hou.applicationVersion()[0], hou.applicationVersion()[1]) )
		else:
			fileHandle.write( "Version=%s\n" % hou.applicationVersion()[0] )
		fileHandle.write( "Build=%s\n" % hBuild )
		
		fileHandle.close()

		if len(dependencies) > 0:
			dependencyFile = os.path.join( homeDir, "temp", "dependencies.txt" )
			fileHandle = open( dependencyFile, "w" )

			for i in dependencies:
				fileHandle.write(str(i[0]) + "\n")
				fileHandle.write(str(i[1]) + "\n")

			fileHandle.close()
		
		arguments = []
		arguments.append( jobInfoFile )
		arguments.append( pluginInfoFile )
		arguments.append( hou.hipFile.path() )
		if "dependencyFile" in locals():
			arguments.append( dependencyFile )
			
		jobResult = self.deadlineCommand( arguments )
	
		return jobResult


	@err_decorator
	def sm_houRender_updateUI(self, origin):
		showGPUsettings = origin.node is not None and origin.node.type().name() == "Redshift_ROP"
		origin.w_dlGPUpt.setVisible(showGPUsettings)
		origin.w_dlGPUdevices.setVisible(showGPUsettings)


	@err_decorator
	def sm_houRender_managerChanged(self, origin):
		origin.f_osDependencies.setVisible(False)
		origin.f_osUpload.setVisible(False)

		origin.f_osPAssets.setVisible(False)
		origin.gb_osSlaves.setVisible(False)
		origin.f_dlGroup.setVisible(True)

		origin.w_dlConcurrentTasks.setVisible(True)

		showGPUsettings = origin.node is not None and origin.node.type().name() == "Redshift_ROP"
		origin.w_dlGPUpt.setVisible(showGPUsettings)
		origin.w_dlGPUdevices.setVisible(showGPUsettings)


	@err_decorator
	def sm_houRender_preExecute(self, origin):
		warnings = []

		return warnings


	@err_decorator
	def sm_houRender_submitJob(self, origin, jobOutputFile, parent):
		jobOutputFile = jobOutputFile.replace("$F4", "####")

		homeDir = (self.deadlineCommand( ["-GetCurrentUserHomeDirectory",] ))

		if homeDir == False:
			return "Execute Canceled: Deadline is not installed"

		homeDir = homeDir.replace( "\r", "" ).replace( "\n", "" )

		dependencies = parent.dependencies

		jobName = os.path.splitext(hou.hipFile.basename())[0] + origin.l_taskName.text()
		jobComment = "Prism-Submission-ImageRender"
		jobGroup = origin.cb_dlGroup.currentText()
		jobPrio = origin.sp_rjPrio.value()
		jobTimeOut = str(origin.sp_rjTimeout.value())
		jobMachineLimit = "0"
		jobFamesPerTask = origin.sp_rjFramesPerTask.value()
		concurrentTasks = origin.sp_dlConcurrentTasks.value()

		if origin.chb_globalRange.isChecked():
			jobFrames = str(origin.stateManager.sp_rangeStart.value()) + "-" + str(origin.stateManager.sp_rangeEnd.value())
		else:
			jobFrames = str(origin.sp_rangeStart.value()) + "-" + str(origin.sp_rangeEnd.value())


		# Create submission info file
		jobInfoFile = os.path.join(homeDir, "temp", "houdini_submit_info.job" )
		fileHandle = open( jobInfoFile, "w" )

		fileHandle.write( "Plugin=Houdini\n" )
		fileHandle.write( "Name=%s\n" % jobName )
		fileHandle.write( "Comment=%s\n" % jobComment )
		fileHandle.write( "Group=%s\n" % jobGroup )
		fileHandle.write( "Priority=%s\n" % jobPrio )
		fileHandle.write( "TaskTimeoutMinutes=%s\n" % jobTimeOut )
		fileHandle.write( "MachineLimit=%s\n" % jobMachineLimit )
		fileHandle.write( "Frames=%s\n" % jobFrames )
		fileHandle.write( "ChunkSize=%s\n" % jobFamesPerTask )
		fileHandle.write( "OutputFilename0=%s\n" % jobOutputFile )
		if origin.chb_rjSuspended.isChecked():
			fileHandle.write( "InitialStatus=Suspended\n" )

		if not origin.w_dlConcurrentTasks.isHidden():
			fileHandle.write( "ConcurrentTasks=%s\n" % concurrentTasks )

		if len(dependencies) > 0:
			fileHandle.write( "IsFrameDependent=true\n" )
			fileHandle.write( "ScriptDependencies=%s\n" % (os.path.join(self.core.projectPath, "00_Pipeline", "Scripts", "DeadlineDependency.py") ))
		
		fileHandle.close()


		nodeName = origin.node.path()
		ignoreInputs = "True"
		hBuild = "64bit"

		# Create plugin info file
		pluginInfoFile = os.path.join( homeDir, "temp", "houdini_plugin_info.job" )
		fileHandle = open( pluginInfoFile, "w" )

		fileHandle.write( "OutputDriver=%s\n" % nodeName )

		fileHandle.write( "IgnoreInputs=%s\n" % ignoreInputs )
		if int(self.deadlineCommand( ["-version",] ).split(".")[0][1:]) > 9:
			fileHandle.write( "Version=%s.%s\n" % (hou.applicationVersion()[0], hou.applicationVersion()[1]) )
		else:
			fileHandle.write( "Version=%s\n" % hou.applicationVersion()[0] )
		fileHandle.write( "Build=%s\n" % hBuild )

		if origin.chb_resOverride.isChecked():
			fileHandle.write( "Width=%s\n" % origin.sp_resWidth.value())
			fileHandle.write( "Height=%s\n" % origin.sp_resHeight.value())

		if not origin.w_dlGPUpt.isHidden():
			fileHandle.write( "GPUsPerTask=%s\n" % origin.sp_dlGPUpt.value() )

		if not origin.w_dlGPUdevices.isHidden():
			fileHandle.write( "GPUsSelectDevices=%s\n" % origin.le_dlGPUdevices.text() )
		
		fileHandle.close()

		if len(dependencies) > 0:
			dependencyFile = os.path.join( homeDir, "temp", "dependencies.txt" )
			fileHandle = open( dependencyFile, "w" )

			for i in dependencies:
				fileHandle.write(str(i[0]) + "\n")
				fileHandle.write(str(i[1]) + "\n")

			fileHandle.close()
		
		arguments = []
		arguments.append( jobInfoFile )
		arguments.append( pluginInfoFile )
		arguments.append( hou.hipFile.path() )
		if "dependencyFile" in locals():
			arguments.append( dependencyFile )
			
		jobResult = self.deadlineCommand( arguments )
	
		return jobResult


	@err_decorator
	def sm_render_updateUI(self, origin):
		showGPUsettings = "redshift" in self.core.plugin.getCurrentRenderer(origin).lower()
		origin.w_dlGPUpt.setVisible(showGPUsettings)
		origin.w_dlGPUdevices.setVisible(showGPUsettings)


	@err_decorator
	def sm_render_managerChanged(self, origin):
		origin.f_osDependencies.setVisible(False)
		origin.gb_osSlaves.setVisible(False)
		origin.f_osUpload.setVisible(False)

		origin.f_dlGroup.setVisible(True)
		origin.w_dlConcurrentTasks.setVisible(True)

		showGPUsettings = "redshift" in self.core.plugin.getCurrentRenderer(origin).lower()
		origin.w_dlGPUpt.setVisible(showGPUsettings)
		origin.w_dlGPUdevices.setVisible(showGPUsettings)

		getattr(self.core.plugin, "sm_render_managerChanged", lambda x,y: None)(origin, False)


	@err_decorator
	def sm_render_preExecute(self, origin):
		warnings = []

		return warnings


	@err_decorator
	def sm_render_submitJob(self, origin, jobOutputFile, parent):
		homeDir = (self.deadlineCommand( ["-GetCurrentUserHomeDirectory",], background=False )).decode("utf-8")

		if homeDir == False:
			return "Execute Canceled: Deadline is not installed"

		homeDir = homeDir.replace( "\r", "" ).replace( "\n", "" )

		dependencies = parent.dependencies

		jobName = os.path.splitext(self.core.getCurrentFileName(path=False))[0] + origin.l_taskName.text()
		jobGroup = origin.cb_dlGroup.currentText()
		jobPrio = origin.sp_rjPrio.value()
		jobTimeOut = str(origin.sp_rjTimeout.value())
		jobMachineLimit = "0"
		jobFamesPerTask = origin.sp_rjFramesPerTask.value()
		concurrentTasks = origin.sp_dlConcurrentTasks.value()

		if origin.chb_globalRange.isChecked():
			jobFrames = str(origin.stateManager.sp_rangeStart.value()) + "-" + str(origin.stateManager.sp_rangeEnd.value())
		else:
			jobFrames = str(origin.sp_rangeStart.value()) + "-" + str(origin.sp_rangeEnd.value())

		dlParams = {"build": "64bit", "version": "", "camera": "", "resolution": "", "plugin": "", "pluginInfoFile": "", "jobInfoFile": "", "jobComment": "", "outputfile": jobOutputFile}
		self.core.plugin.sm_render_getDeadlineParams(origin, dlParams, homeDir)

		# Create submission info file
		
		fileHandle = open( dlParams["jobInfoFile"] , "w" )

		fileHandle.write( "Plugin=%s\n" % dlParams["plugin"] )
		fileHandle.write( "Name=%s\n" % jobName )
		fileHandle.write( "Comment=%s\n" % dlParams["jobComment"] )
		fileHandle.write( "Group=%s\n" % jobGroup )
		fileHandle.write( "Priority=%s\n" % jobPrio )
		fileHandle.write( "TaskTimeoutMinutes=%s\n" % jobTimeOut )
		fileHandle.write( "MachineLimit=%s\n" % jobMachineLimit )
		fileHandle.write( "Frames=%s\n" % jobFrames )
		fileHandle.write( "ChunkSize=%s\n" % jobFamesPerTask )
		fileHandle.write( "OutputFilename0=%s\n" % jobOutputFile )
		if origin.chb_rjSuspended.isChecked():
			fileHandle.write( "InitialStatus=Suspended\n" )

		if not origin.w_dlConcurrentTasks.isHidden():
			fileHandle.write( "ConcurrentTasks=%s\n" % concurrentTasks )

		if len(dependencies) > 0:
			fileHandle.write( "IsFrameDependent=true\n" )
			fileHandle.write( "ScriptDependencies=%s\n" % (os.path.join(self.core.projectPath, "00_Pipeline" ,"Scripts", "DeadlineDependency.py") ))
		
		fileHandle.close()

		# Create plugin info file
		
		fileHandle = open( dlParams["pluginInfoFile"] , "w" )
		if "filePrefix" in dlParams:
			fileHandle.write( "OutputFilePrefix=%s\n" % dlParams["filePrefix"] )
		if "version" in dlParams:
			fileHandle.write( "Version=%s\n" % dlParams["version"] )
		if "camera" in dlParams and origin.curCam != "Current View":
			fileHandle.write( "Camera=%s\n" % self.core.plugin.getCamName(origin, origin.curCam) )

		pParams = self.core.plugin.sm_render_getDeadlineSubmissionParams(origin, dlParams, jobOutputFile)

		for i in pParams:
			fileHandle.write( "%s=%s\n" % (i, pParams[i]))

		if not origin.w_dlGPUpt.isHidden():
			fileHandle.write( "GPUsPerTask=%s\n" % origin.sp_dlGPUpt.value() )

		if not origin.w_dlGPUdevices.isHidden():
			fileHandle.write( "GPUsSelectDevices=%s\n" % origin.le_dlGPUdevices.text() )
		
		fileHandle.close()

		if len(dependencies) > 0:
			dependencyFile = os.path.join( homeDir, "temp", "dependencies.txt" )
			fileHandle = open( dependencyFile, "w" )

			for i in dependencies:
				fileHandle.write(str(i[0]) + "\n")
				fileHandle.write(str(i[1]) + "\n")

			fileHandle.close()
		
		arguments = []
		arguments.append( dlParams["jobInfoFile"] )
		arguments.append( dlParams["pluginInfoFile"] )
		for i in self.core.plugin.getCurrentSceneFiles(origin):
			arguments.append(i)

		if "dependencyFile" in locals():
			arguments.append( dependencyFile )
			
		jobResult = self.deadlineCommand( arguments, background=False ).decode("utf-8") 
		   
		return jobResult