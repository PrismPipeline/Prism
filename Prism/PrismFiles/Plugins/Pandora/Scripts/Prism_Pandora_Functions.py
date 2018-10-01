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



import os, sys, traceback, time, subprocess, platform, random, string, shutil, socket
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

if sys.version[0] == "3":
	from configparser import ConfigParser
else:
	from ConfigParser import ConfigParser


class Prism_Pandora_Functions(object):
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
				erStr = ("%s ERROR - Prism_Plugin_Pandora %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].plugin.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def isActive(self):
		return os.path.exists(self.getPandoraPath())


	@err_decorator
	def getPandoraPath(self):
		pandoraPath = os.path.join(os.getenv("localappdata"), "Pandora")

		return pandoraPath


	@err_decorator
	def getPandoraConfig(self, cat, param, ptype="string"):
		pandoraConfig = os.path.join(self.getPandoraPath(), "Config", "Pandora.ini")
		panConfig = ConfigParser()
		try:
			panConfig.read(pandoraConfig)
		except:
			return None

		if panConfig.has_option(cat, param):
			if ptype == "string":
				return panConfig.get(cat, param)
			elif ptype == "bool":
				return panConfig.getboolean(cat, param)
		else:
			return None


	@err_decorator
	def sm_dep_startup(self, origin):
		origin.lw_osStates.itemClicked.connect(lambda x: self.sm_updatePandoraDeps(origin, x))
		origin.b_goTo.clicked.connect(lambda: self.sm_pandoraGoToNode(origin))


	@err_decorator
	def sm_updatePandoraDeps(self, origin, item):
		if item.checkState() == Qt.Checked:
			if item.toolTip().startswith("Node:"):
				origin.dependencies["Pandora"] = [[item.text(), "Node"]]
			elif item.toolTip().startswith("Job:"):
				origin.dependencies["Pandora"] = [[item.text(), "Job"]]
			origin.updateUi()
			origin.stateManager.saveStatesToScene()
		elif item.checkState() == Qt.Unchecked:
			if len(origin.dependencies["Pandora"]) > 0 and item.text() == origin.dependencies["Pandora"][0][0]:
				origin.dependencies["Pandora"] = []
				origin.updateUi()
				origin.stateManager.saveStatesToScene()


	@err_decorator
	def sm_pandoraGoToNode(self, origin):
		try:
			origin.node.name()
		except:
			return False

		origin.node.setCurrent(True, clear_all_selected=True)

		paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
		if paneTab is not None:
			paneTab.frameSelection()


	@err_decorator
	def sm_dep_updateUI(self, origin):
		origin.gb_osDependency.setVisible(True)
		origin.gb_dlDependency.setVisible(False)
		try:
			origin.node.name()
			origin.l_status.setText(origin.node.name())
			origin.l_status.setStyleSheet("QLabel { background-color : rgb(0,150,0); }")
		except:
			origin.l_status.setText("Not connected")
			origin.l_status.setStyleSheet("QLabel { background-color : rgb(150,0,0); }")

		origin.lw_osStates.clear()
		newDepStates = []

		curNum = -1
		for idx, i in enumerate(origin.stateManager.states):
			if i.ui == origin:
				curNum = idx

			if curNum != -1:
				continue

			if i.ui.className in ["Export", "ImageRender"] and i.ui.node is not None and origin.isNodeValid(i.ui.node):
				item = QListWidgetItem(i.text(0))
				item.setToolTip("Node: " + i.text(0))

				if len(origin.dependencies["Pandora"]) > 0 and str(i.text(0)) == origin.dependencies["Pandora"][0][0]:
					cState = Qt.Checked
					newDepStates.append([str(i.text(0)), "Node"])
				else:
					cState = Qt.Unchecked

				item.setCheckState(cState)
				if psVersion == 2:
					item.setFlags(item.flags() & ~Qt.ItemIsAutoTristate)
				origin.lw_osStates.addItem(item)

		lmode = self.getPandoraConfig("globals", "localmode")

		if lmode == "True":
			osf = self.getPandoraConfig("globals", "rootpath")
			if osf is not None:
				osf = os.path.join(osf, "PandoraFarm", "Workstations", "WS_" + socket.gethostname(), "")
		else:
			osf = self.getPandoraConfig('submissions', "submissionpath")

		osFolder = ""
		if osf is not None:
			osFolder = osf

		if osFolder is not None and os.path.exists(osFolder):
			jobDir = os.path.join(os.path.dirname(os.path.dirname(osFolder)), "Logs", "Jobs")
			if os.path.exists(jobDir):
				self.pandoraJobs = []
				for x in sorted(os.listdir(jobDir)):
					jobName = os.path.splitext(x)[0]

					jcode = origin.core.getConfig(cat="information", param="jobcode", configPath=os.path.join(jobDir, x))

					if jcode is not None:
						jobCode = jcode
					else:
						continue

					self.pandoraJobs.append([jobName, jobCode])

				for x in self.pandoraJobs:
					jobName = x[0]

					item = QListWidgetItem(jobName)
					item.setToolTip("Job: %s" % (jobName))

					if len(origin.dependencies["Pandora"]) > 0 and jobName == origin.dependencies["Pandora"][0][0]:
						cState = Qt.Checked
						newDepStates.append([jobName, "Job"])
					else:
						cState = Qt.Unchecked

					item.setCheckState(cState)
					if psVersion == 2:
						item.setFlags(item.flags() & ~Qt.ItemIsAutoTristate)
					origin.lw_osStates.addItem(item)


		origin.dependencies["Pandora"] = newDepStates


	@err_decorator
	def sm_dep_preExecute(self, origin):
		warnings = []

		if origin.node is None or not origin.isNodeValid(origin.node):
			warnings.append(["Node is invalid.", "", 3])

		return warnings


	@err_decorator
	def sm_dep_execute(self, origin, parent):
		if len(origin.dependencies["Pandora"]) > 0 and origin.node is not None and origin.isNodeValid(origin.node):
			if origin.dependencies["Pandora"][0][1] == "Node" and origin.dependencies["Pandora"][0][0] in parent.osSubmittedJobs:
				parent.osDependencies.append([parent.osSubmittedJobs[origin.dependencies["Pandora"][0][0]], origin.node.path()])
			elif origin.dependencies["Pandora"][0][1] == "Job":
				jobCodes = [x[1] for x in self.pandoraJobs if origin.dependencies["Pandora"][0][0] == x[0]]
				if len(jobCodes) > 0:
					parent.osDependencies.append([jobCodes[0], origin.node.path()])


	@err_decorator
	def sm_houExport_startup(self, origin):
		pass


	@err_decorator
	def sm_houExport_activated(self, origin):
		origin.f_osDependencies.setVisible(True)
		origin.f_osUpload.setVisible(True)
		origin.f_osPAssets.setVisible(True)
		origin.gb_osSlaves.setVisible(True)
		origin.f_dlGroup.setVisible(False)


	@err_decorator
	def sm_houExport_preExecute(self, origin):
		warnings = []

		pandoraIni = os.path.join(self.getPandoraPath(), "Config", "Pandora.ini")

		lmode = self.getPandoraConfig("globals", "localmode")

		if lmode == "True":
			submPath = self.getPandoraConfig("globals", "rootpath")
		else:
			submPath = self.getPandoraConfig("submissions", "submissionpath")
	
		if submPath in [None, ""]:
			warnings.append(["No Pandora submission folder is configured.", "", 3])

		extFiles, extFilesSource = self.core.plugin.sm_getExternalFiles(origin)

		if origin.chb_osDependencies.isChecked():
			lockedAssets = []
			for idx, i in enumerate(extFiles):
				i = self.core.fixPath(i)

				if (not os.path.exists(i) and not i.startswith("op:")) or i == self.core.getCurrentFileName():
					continue

				if not extFilesSource[idx].node().isEditable():
					lockedAssets.append(i)

			if len(lockedAssets) > 0:
				depTitle = "The current scene contains locked dependencies.\nWhen submitting Pandora jobs, this dependencies cannot be relinked and will not be found by the renderslave:\n\n"
				depwarn = ""
				for i in lockedAssets:
					parmStr = ("In parameter: %s" % extFilesSource[extFiles.index(i.replace("\\", "/"))].path())
					depwarn += "\t%s\n\t%s\n\n" % (parmStr, i)

				warnings.append([depTitle, depwarn, 2])

		return warnings


	@err_decorator
	def sm_houExport_submitJob(self, origin, jobOutputFile, parent):
		pandoraIni = os.path.join(self.getPandoraPath(), "Config", "Pandora.ini")

		uconfig = ConfigParser()
		uconfig.read(pandoraIni)

		lmode = self.getPandoraConfig("globals", "localmode")

		if lmode is None:
			return "Execute Canceled: The Pandora config misses the mode setting."

		if lmode == "True":
			rootPath = self.getPandoraConfig("globals", "rootpath")
			if rootPath in [None, ""]:
				return "Execute Canceled: No Pandora root folder is configured."
			osFolder = os.path.join(rootPath, "PandoraFarm", "Workstations", "WS_" + socket.gethostname(), "")
		else:
			if not uconfig.has_option('submissions', "submissionpath"):
				return "Execute Canceled: No Pandora submission folder is configured."

			osFolder = uconfig.get('submissions', "submissionpath")
			if osFolder == "":
				return "Execute Canceled: No Pandora submission folder is configured."

		if not os.path.exists(osFolder):
			try:
				os.makedirs(osFolder)
			except:
				return "Execute Canceled: Pandora submission folder could not be created."

		fileName = self.core.getCurrentFileName()
		assignPath = os.path.join(osFolder, "JobSubmissions")
		jobName = os.path.splitext(os.path.basename(fileName))[0] + "---%s" % origin.l_taskName2.text()
		jobCode = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
		jobPath = os.path.join(assignPath, jobCode , "JobFiles")
		while os.path.exists(jobPath):
			jobCode = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
			jobPath = os.path.join(assignPath, jobCode , "JobFiles")

		jobIni = os.path.join(os.path.dirname(jobPath), "PandoraJob.ini")
		if origin.chb_osPAssets.isChecked():
			assetPath = os.path.join(assignPath, "ProjectAssets", self.core.projectName)
			if not os.path.exists(assetPath):
				os.makedirs(assetPath)
		else:
			assetPath = jobPath

		if os.path.exists(jobPath):
			return "Execute Canceled: Job already exists"

		os.makedirs(jobPath)
		jobFiles = [[os.path.basename(fileName), os.path.getmtime(fileName), fileName]]
		while True:
			try:
				shutil.copy(fileName, jobPath)
				break
			except:
				msg = QMessageBox(QMessageBox.Warning, "Pandora submission", "An error occurred while copying the scene file.", QMessageBox.Cancel)
				msg.addButton("Retry", QMessageBox.YesRole)
				self.core.parentWindow(msg)
				action = msg.exec_()

				if action != 0:
					return "Execute Canceled: Could not copy the files"

		if origin.chb_osDependencies.isChecked():
			houdeps = hou.fileReferences()
			extFiles = []
			for i in houdeps:
				if not os.path.exists(hou.expandString(i[1])):
					continue

				if i[1] in extFiles:
					continue

				if os.path.splitext(hou.expandString(i[1]))[1] == "":
					continue

				if "/Redshift/Plugins/Houdini/" in i[1]:
					continue

				if i[0] is not None and i[0].name() in ["RS_outputFileNamePrefix", "vm_picture"]:
					continue

				if i[0] is not None and i[0].name() in ["filename", "dopoutput", "copoutput", "sopoutput"] and i[0].node().type().name() in ["rop_alembic", "rop_dop", "rop_comp", "rop_geometry"]:
					continue
			
				extFiles.append(i[1])

			tFilesState = "None"

			while True:
				erFiles = []
				while True:
					tFiles = []
					for i in extFiles:
						exI = hou.expandString(i)
						frameVar = i.find("$F")
						fileSeq = []
						if frameVar != -1:
							for k in os.listdir(os.path.dirname(exI)):
								if k.startswith(os.path.basename(i)[:os.path.basename(i).find("$F")]) and k.endswith(os.path.basename(i)[os.path.basename(i).find("$F")+3:]):
									fileSeq.append(os.path.join(os.path.dirname(exI), k))
						else:
							fileSeq.append(exI)

						for k in fileSeq:
							if not os.path.exists(k):
								continue
							tPath = os.path.join(assetPath, os.path.basename(k))
							if os.path.exists(tPath):
								if tFilesState != "Overwrite":
									if tFilesState == "Skip":
										continue
									if tFilesState == "Keep newest":
										if int(os.path.getmtime(k)) <= int(os.path.getmtime(tPath)):
											continue
									else:
										if int(os.path.getmtime(k)) != int(os.path.getmtime(tPath)):
											for x in jobFiles:
												if os.path.basename(k) == x[0]:
													fString = "A file with the same name and a different modification date was already submitted with this Job. Only the first version of this file will be submitted:\n\n%s\n%s" % (x[2], k)
													msg = QMessageBox(QMessageBox.Warning, "Collecting assets", fString, QMessageBox.Cancel)
													msg.addButton("Continue", QMessageBox.YesRole)
													self.core.parentWindow(msg)
													action = msg.exec_()

													if action != 0:
														try:
															shutil.rmtree(os.path.dirname(jobPath))
														except:
															pass
														return "Execute Canceled"

													break
											else:
												tFiles.append(k)

										if os.path.basename(k) not in [x[0] for x in jobFiles]:
											jobFiles.append([os.path.basename(k), os.path.getmtime(k), k])
										continue

							try:
								shutil.copy2(k, assetPath)
								if os.path.basename(k) not in [x[0] for x in jobFiles]:
									jobFiles.append([os.path.basename(k), os.path.getmtime(k), k])
							except:
								erFiles.append(k)

					if len(tFiles) > 0:
						fString = "Some assets already exist in the ProjectAsset folder and have a different modification date:\n\n"
						for i in tFiles:
							fString += "%s\n" % i
						msg = QMessageBox(QMessageBox.Warning, "Pandora submission", fString, QMessageBox.Cancel)
						msg.addButton("Keep newest", QMessageBox.YesRole)
						msg.addButton("Overwrite", QMessageBox.YesRole)
						msg.addButton("Skip", QMessageBox.YesRole)
						self.core.parentWindow(msg)
						action = msg.exec_()

						if action == 1:
							extFiles = tFiles
							tFilesState = "Overwrite"
						elif action == 2:
							tFilesState = "Skip"
							break
						elif action != 0:
							if os.path.exists(jobPath):
								try:
									os.remove(jobPath)
								except:
									pass
							return "Execute Canceled: Canceled by user"
						else:
							extFiles = tFiles
							tFilesState = "Keep newest"
							
					else:
						tFilesState = "Skip"
						break

						
				if len(erFiles) > 0:
					fString = "An error occurred while copying external files:\n\n"
					for i in erFiles:
						fString += "%s\n" % i
					msg = QMessageBox(QMessageBox.Warning, "Pandora submission", fString, QMessageBox.Cancel)
					msg.addButton("Retry", QMessageBox.YesRole)
					msg.addButton("Continue", QMessageBox.YesRole)
					self.core.parentWindow(msg)
					action = msg.exec_()


					if action == 1:
						break
					elif action != 0:
						if os.path.exists(jobPath):
							try:
								os.remove(jobPath)
							except:
								pass
						return "Execute Canceled: Canceled by user"
					else:
						extFiles = erFiles
				else:
					break

		if not origin.chb_osPAssets.isChecked() and len(jobFiles) != os.listdir(jobPath):
			return "Execute Canceled: The filecount in the jobsubmission folder is not correct. %s of %s" % (os.listdir(jobPath), len(jobFiles))

		if not os.path.exists(jobIni):
			open(jobIni, 'a').close()

		listSlaves = origin.e_osSlaves.text()

		if origin.chb_globalRange.isChecked():
			jobFrames = [origin.stateManager.sp_rangeStart.value(), origin.stateManager.sp_rangeEnd.value()]
		else:
			jobFrames = [origin.sp_rangeStart.value(), origin.sp_rangeEnd.value()]

		config = ConfigParser()
		config.read(jobIni)

		config.add_section('jobglobals')
		config.set('jobglobals', 'priority', str(origin.sp_rjPrio.value()))
		config.set('jobglobals', 'uploadOutput', str(origin.chb_osUpload.isChecked()))
		config.set('jobglobals', 'listslaves', listSlaves)
		config.set('jobglobals', 'rendernode', origin.node.path())
		config.set('jobglobals', 'taskTimeout', str(origin.sp_rjTimeout.value()))
		if len(parent.osDependencies) > 0:
			config.set('jobglobals', 'jobdependecies', str(parent.osDependencies))
		config.add_section('information')
		config.set('information', 'jobname', jobName)
		config.set('information', 'scenename', os.path.basename(fileName))
		config.set('information', 'projectname', self.core.projectName)
		config.set('information', 'username', self.core.getConfig("globals", "UserName"))
		config.set('information', 'submitdate', time.strftime("%d.%m.%y, %X", time.localtime()))
		config.set('information', 'framerange', "%s-%s" % (jobFrames[0], jobFrames[1]))
		config.set('information', 'outputpath', jobOutputFile)
		config.set('information', 'filecount', str(len(jobFiles)))
		config.set('information', 'savedbasepath', self.core.projectPath)
		config.set('information', 'outputbase', os.path.dirname(os.path.dirname(jobOutputFile)))
		config.set('information', 'program', self.core.plugin.appName)
		config.set('information', 'programversion', hou.applicationVersionString())

		if origin.chb_osPAssets.isChecked():
			config.set('information', 'projectassets', [[x[0],x[1]] for x in jobFiles])

		config.add_section('jobtasks')

		curFrame=jobFrames[0]
		tasksNum = 0
		if origin.chb_rjSuspended.isChecked():
			initState = "disabled"
		else:
			initState = "ready"

		fpt = origin.sp_rjFramesPerTask.value()
		while curFrame <= jobFrames[1]:
			startFrame = curFrame
			endFrame = curFrame+fpt-1
			if endFrame > jobFrames[1]:
				endFrame = jobFrames[1]
			config.set('jobtasks', 'task'+ str(tasksNum), [startFrame, endFrame, initState, "unassigned", "", "", ""])
			curFrame+=fpt
			tasksNum += 1
		with open(jobIni, 'w') as inifile:
			config.write(inifile)

		parent.osSubmittedJobs[origin.state.text(0)] = jobCode

		return "Result=Success"


	@err_decorator
	def sm_houRender_updateUI(self, origin):
		origin.w_dlGPUpt.setVisible(False)
		origin.w_dlGPUdevices.setVisible(False)


	@err_decorator
	def sm_houRender_managerChanged(self, origin):
		origin.f_osDependencies.setVisible(True)

		showUpload = False
		lmode = self.getPandoraConfig("globals", "localmode")
		if lmode != "True":
			showUpload = True

		origin.f_osUpload.setVisible(showUpload)

		origin.f_osPAssets.setVisible(True)
		origin.gb_osSlaves.setVisible(True)
		origin.f_dlGroup.setVisible(False)

		origin.w_dlConcurrentTasks.setVisible(False)

		origin.w_dlGPUpt.setVisible(False)
		origin.w_dlGPUdevices.setVisible(False)


	@err_decorator
	def sm_houRender_preExecute(self, origin):
		warnings = []

		pandoraIni = os.path.join(self.getPandoraPath(), "Config", "Pandora.ini")

		lmode = self.getPandoraConfig("globals", "localmode")

		if lmode == "True":
			submPath = self.getPandoraConfig("globals", "rootpath")
		else:
			submPath = self.getPandoraConfig("submissions", "submissionpath")
	
		if submPath in [None, ""]:
			warnings.append(["No Pandora submission folder is configured.", "", 3])

		extFiles, extFilesSource = self.core.plugin.sm_getExternalFiles(origin)

		if origin.chb_osDependencies.isChecked():
			lockedAssets = []
			for idx, i in enumerate(extFiles):
				i = self.core.fixPath(i)
				
				if (not os.path.exists(i) and not i.startswith("op:")) or i == self.core.getCurrentFileName():
					continue

				if not extFilesSource[idx].node().isEditable():
					lockedAssets.append(i)

			if len(lockedAssets) > 0:
				depTitle = "The current scene contains locked dependencies.\nWhen submitting Pandora jobs, this dependencies cannot be relinked and will not be found by the renderslave:\n\n"
				depwarn = ""
				for i in lockedAssets:
					parmStr = ("In parameter: %s" % extFilesSource[extFiles.index(i.replace("\\", "/"))].path())
					depwarn += "\t%s\n\t%s\n\n" % (parmStr, i)

				warnings.append([depTitle, depwarn, 2])

		return warnings


	@err_decorator
	def sm_houRender_submitJob(self, origin, jobOutputFile, parent):
		pandoraIni = os.path.join(self.getPandoraPath(), "Config", "Pandora.ini")

		uconfig = ConfigParser()
		uconfig.read(pandoraIni)

		lmode = self.getPandoraConfig("globals", "localmode")

		if lmode is None:
			return "Execute Canceled: The Pandora config misses the mode setting."

		if lmode == "True":
			rootPath = self.getPandoraConfig("globals", "rootpath")
			if rootPath in [None, ""]:
				return "Execute Canceled: No Pandora root folder is configured."
			osFolder = os.path.join(rootPath, "PandoraFarm", "Workstations", "WS_" + socket.gethostname(), "")
		else:
			if not uconfig.has_option('submissions', "submissionpath"):
				return "Execute Canceled: No Pandora submission folder is configured."

			osFolder = uconfig.get('submissions', "submissionpath")
			if osFolder == "":
				return "Execute Canceled: No Pandora submission folder is configured."

		if not os.path.exists(osFolder):
			try:
				os.makedirs(osFolder)
			except:
				return "Execute Canceled: Pandora submission folder could not be created."

		fileName = self.core.getCurrentFileName()
		assignPath = os.path.join(osFolder, "JobSubmissions")
		jobName = os.path.splitext(os.path.basename(fileName))[0] + "---%s" % origin.l_taskName.text()
		jobCode = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
		jobPath = os.path.join(assignPath, jobCode , "JobFiles")
		while os.path.exists(jobPath):
			jobCode = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
			jobPath = os.path.join(assignPath, jobCode , "JobFiles")

		jobIni = os.path.join(os.path.dirname(jobPath), "PandoraJob.ini")
		if origin.chb_osPAssets.isChecked():
			assetPath = os.path.join(assignPath, "ProjectAssets", self.core.projectName)
			if not os.path.exists(assetPath):
				os.makedirs(assetPath)
		else:
			assetPath = jobPath

		if os.path.exists(jobPath):
			return "Execute Canceled: Job already exists"

		os.makedirs(jobPath)
		jobFiles = [[os.path.basename(fileName), os.path.getmtime(fileName), fileName]]
		while True:
			try:
				shutil.copy(fileName, jobPath)
				break
			except Exception as e:
				msg = QMessageBox(QMessageBox.Warning, "Pandora submission", "An error occurred while copying the scene file:\n\n%s" % e, QMessageBox.Cancel)
				msg.addButton("Retry", QMessageBox.YesRole)
				self.core.parentWindow(msg)
				action = msg.exec_()

				if action != 0:
					if os.path.exists(jobPath):
						try:
							os.remove(jobPath)
						except:
							pass
					return "Execute Canceled: Could not copy the files"

		if origin.chb_osDependencies.isChecked():
			houdeps = hou.fileReferences()
			extFiles = []
			for i in houdeps:
				if not os.path.exists(hou.expandString(i[1])):
					continue

				if i[1] in extFiles:
					continue

				if os.path.splitext(hou.expandString(i[1]))[1] == "":
					continue

				if "/Redshift/Plugins/Houdini/" in i[1]:
					continue

				if i[0] is not None and i[0].name() in ["RS_outputFileNamePrefix", "vm_picture"]:
					continue

				if i[0] is not None and i[0].name() in ["filename", "dopoutput", "copoutput", "sopoutput"] and i[0].node().type().name() in ["rop_alembic", "rop_dop", "rop_comp", "rop_geometry"]:
					continue
			
				extFiles.append(i[1])

			tFilesState = "None"

			while True:
				erFiles = []
				while True:
					tFiles = []
					for i in extFiles:
						exI = hou.expandString(i)
						frameVar = i.find("$F")
						exprVar = i.find("`")
						fileSeq = []
						if exprVar != -1:
							for k in os.listdir(os.path.dirname(exI)):
								if exprVar != -1 and k.startswith(os.path.basename(i)[:os.path.basename(i).find("`")]) and k.endswith(os.path.basename(i).split("`")[-1]):
									fileSeq.append(os.path.join(os.path.dirname(exI), k))
						elif frameVar != -1:
							for k in os.listdir(os.path.dirname(exI)):
								if k.startswith(os.path.basename(i)[:os.path.basename(i).find("$F")]) and k.endswith(os.path.basename(i)[os.path.basename(i).find("$F")+3:]):
									fileSeq.append(os.path.join(os.path.dirname(exI), k))
						else:
							fileSeq.append(exI)

						for k in fileSeq:
							if not os.path.exists(k):
								continue
							tPath = os.path.join(assetPath, os.path.basename(k))
							if os.path.exists(tPath):
								if tFilesState != "Overwrite":
									if tFilesState == "Skip":
										continue
									if tFilesState == "Keep newest":
										if int(os.path.getmtime(k)) <= int(os.path.getmtime(tPath)):
											continue
									else:
										if int(os.path.getmtime(k)) != int(os.path.getmtime(tPath)):
											for x in jobFiles:
												if os.path.basename(k) == x[0]:
													fString = "A file with the same name and a different modification date was already submitted with this Job. Only the first version of this file will be submitted:\n\n%s\n%s" % (x[2], k)
													msg = QMessageBox(QMessageBox.Warning, "Collecting assets", fString, QMessageBox.Cancel)
													msg.addButton("Continue", QMessageBox.YesRole)
													self.core.parentWindow(msg)
													action = msg.exec_()

													if action != 0:
														try:
															shutil.rmtree(os.path.dirname(jobPath))
														except:
															pass
														return "Execute Canceled"

													break
											else:
												tFiles.append(k)
										if os.path.basename(k) not in [x[0] for x in jobFiles]:
											jobFiles.append([os.path.basename(k), os.path.getmtime(k), k])
										continue

							try:
								shutil.copy2(k, assetPath)
								if os.path.basename(k) not in [x[0] for x in jobFiles]:
									jobFiles.append([os.path.basename(k), os.path.getmtime(k), k])
							except:
								erFiles.append(k)

					if len(tFiles) > 0:
						fString = "Some assets already exist in the ProjectAsset folder and have a different modification date:\n\n"
						for i in tFiles:
							fString += "%s\n" % i
						msg = QMessageBox(QMessageBox.Warning, "Pandora submission", fString, QMessageBox.Cancel)
						msg.addButton("Keep newest", QMessageBox.YesRole)
						msg.addButton("Overwrite", QMessageBox.YesRole)
						msg.addButton("Skip", QMessageBox.YesRole)
						self.core.parentWindow(msg)
						action = msg.exec_()

						if action == 1:
							extFiles = tFiles
							tFilesState = "Overwrite"
						elif action == 2:
							tFilesState = "Skip"
							break
						elif action != 0:
							if os.path.exists(jobPath):
								try:
									os.remove(jobPath)
								except:
									pass
							return "Execute Canceled: Canceled by user"
						else:
							extFiles = tFiles
							tFilesState = "Keep newest"
							
					else:
						tFilesState = "Skip"
						break

						
				if len(erFiles) > 0:
					fString = "An error occurred while copying external files:\n\n"
					for i in erFiles:
						fString += "%s\n" % i
					msg = QMessageBox(QMessageBox.Warning, "Pandora submission", fString, QMessageBox.Cancel)
					msg.addButton("Retry", QMessageBox.YesRole)
					msg.addButton("Continue", QMessageBox.YesRole)
					self.core.parentWindow(msg)
					action = msg.exec_()


					if action == 1:
						break
					elif action != 0:
						if os.path.exists(jobPath):
							try:
								os.remove(jobPath)
							except:
								pass
						return "Execute Canceled: Canceled by user"
					else:
						extFiles = erFiles
				else:
					break

		if not origin.chb_osPAssets.isChecked() and len(jobFiles) != len(os.listdir(jobPath)):
			return "Execute Canceled: The filecount in the jobsubmission folder is not correct. %s of %s" % (len(os.listdir(jobPath)), len(jobFiles))

		if not os.path.exists(jobIni):
			open(jobIni, 'a').close()

		listSlaves = origin.e_osSlaves.text()

		if origin.chb_globalRange.isChecked():
			jobFrames = [origin.stateManager.sp_rangeStart.value(), origin.stateManager.sp_rangeEnd.value()]
		else:
			jobFrames = [origin.sp_rangeStart.value(), origin.sp_rangeEnd.value()]

		config = ConfigParser()
		config.read(jobIni)

		config.add_section('jobglobals')
		config.set('jobglobals', 'priority', str(origin.sp_rjPrio.value()))
		config.set('jobglobals', 'uploadOutput', str(origin.chb_osUpload.isChecked()))
		config.set('jobglobals', 'listslaves', listSlaves)
		config.set('jobglobals', 'rendernode', origin.node.path())
		config.set('jobglobals', 'taskTimeout', str(origin.sp_rjTimeout.value()))
		if len(parent.osDependencies) > 0:
			config.set('jobglobals', 'jobdependecies', str(parent.osDependencies))
		config.add_section('information')
		config.set('information', 'jobname', jobName)
		config.set('information', 'scenename', os.path.basename(fileName))
		config.set('information', 'projectname', self.core.projectName)
		config.set('information', 'username', self.core.getConfig("globals", "UserName"))
		config.set('information', 'submitdate', time.strftime("%d.%m.%y, %X", time.localtime()))
		config.set('information', 'framerange', "%s-%s" % (jobFrames[0], jobFrames[1]))
		config.set('information', 'outputpath', jobOutputFile)
		config.set('information', 'filecount', str(len(jobFiles)))
		config.set('information', 'savedbasepath', self.core.projectPath)
		config.set('information', 'outputbase', os.path.dirname(os.path.dirname(jobOutputFile)))
		config.set('information', 'program', self.core.plugin.appName)
		config.set('information', 'programversion', hou.applicationVersionString())

		if origin.chb_osPAssets.isChecked():
			config.set('information', 'projectassets', [[x[0],x[1]] for x in jobFiles])

		if origin.chb_resOverride.isChecked():
			config.set('jobglobals', "width", origin.sp_resWidth.value())
			config.set('jobglobals', "height", origin.sp_resHeight.value())

		config.add_section('jobtasks')

		curFrame=jobFrames[0]
		tasksNum = 0
		if origin.chb_rjSuspended.isChecked():
			initState = "disabled"
		else:
			initState = "ready"

		fpt = origin.sp_rjFramesPerTask.value()
		while curFrame <= jobFrames[1]:
			startFrame = curFrame
			endFrame = curFrame+fpt-1
			if endFrame > jobFrames[1]:
				endFrame = jobFrames[1]
			config.set('jobtasks', 'task'+ str(tasksNum), [startFrame, endFrame, initState, "unassigned", "", "", ""])
			curFrame+=fpt
			tasksNum += 1
		with open(jobIni, 'w') as inifile:
			config.write(inifile)

		parent.osSubmittedJobs[origin.state.text(0)] = jobCode

		return "Result=Success"
		

	@err_decorator
	def sm_render_updateUI(self, origin):
		origin.w_dlGPUpt.setVisible(False)
		origin.w_dlGPUdevices.setVisible(False)


	@err_decorator
	def sm_render_managerChanged(self, origin):
		origin.f_osDependencies.setVisible(True)
		origin.gb_osSlaves.setVisible(True)

		showUpload = False
		lmode = self.getPandoraConfig("globals", "localmode")
		if lmode != "True":
			showUpload = True

		origin.f_osUpload.setVisible(showUpload)

		origin.f_dlGroup.setVisible(False)
		origin.w_dlConcurrentTasks.setVisible(False)

		origin.w_dlGPUpt.setVisible(False)
		origin.w_dlGPUdevices.setVisible(False)

		getattr(self.core.plugin, "sm_render_managerChanged", lambda x,y: None)(origin, True)


	@err_decorator
	def sm_render_preExecute(self, origin):
		warnings = []

		pandoraIni = os.path.join(self.getPandoraPath(), "Config", "Pandora.ini")

		lmode = self.getPandoraConfig("globals", "localmode")

		if lmode == "True":
			submPath = self.getPandoraConfig("globals", "rootpath")
		else:
			submPath = self.getPandoraConfig("submissions", "submissionpath")
	
		if submPath in [None, ""]:
			warnings.append(["No Pandora submission folder is configured.", "", 3])

		return warnings


	@err_decorator
	def sm_render_submitJob(self, origin, jobOutputFile, parent):
		pandoraIni = os.path.join(self.getPandoraPath(), "Config", "Pandora.ini")

		uconfig = ConfigParser()
		uconfig.read(pandoraIni)

		lmode = self.getPandoraConfig("globals", "localmode")

		if lmode is None:
			return "Execute Canceled: The Pandora config misses the mode setting."

		if lmode == "True":
			rootPath = self.getPandoraConfig("globals", "rootpath")
			if rootPath in [None, ""]:
				return "Execute Canceled: No Pandora root folder is configured."
			osFolder = os.path.join(rootPath, "PandoraFarm", "Workstations", "WS_" + socket.gethostname(), "")
		else:
			if not uconfig.has_option('submissions', "submissionpath"):
				return "Execute Canceled: No Pandora submission folder is configured."

			osFolder = uconfig.get('submissions', "submissionpath")
			if osFolder == "":
				return "Execute Canceled: No Pandora submission folder is configured."

		if not os.path.exists(osFolder):
			try:
				os.makedirs(osFolder)
			except:
				return "Execute Canceled: Pandora submission folder could not be created."

		fileName = str(self.core.getCurrentFileName())
		assignPath = os.path.join(osFolder, "JobSubmissions")

		lmode = self.getPandoraConfig("globals", "localmode")
		if lmode != "True":
			outputBasePath = self.core.projectPath
		else:
			outputBasePath = os.path.dirname(os.path.dirname(jobOutputFile))
			
		jobName = os.path.splitext(os.path.basename(fileName))[0] + "---%s" % origin.l_taskName.text()
		jobCode = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
		jobPath = os.path.join(assignPath, jobCode , "JobFiles")
		while os.path.exists(jobPath):
			jobCode = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
			jobPath = os.path.join(assignPath, jobCode , "JobFiles")

		jobIni = os.path.join(os.path.dirname(jobPath), "PandoraJob.ini")
		if origin.chb_osPAssets.isChecked():
			assetPath = os.path.join(assignPath, "ProjectAssets", self.core.projectName)
			if not os.path.exists(assetPath):
				os.makedirs(assetPath)
		else:
			assetPath = jobPath

		if os.path.exists(jobPath):
			return "Execute Canceled: Job already exists"

		os.makedirs(jobPath)
		jobFiles = [[os.path.basename(fileName), os.path.getmtime(fileName)]]

		if origin.chb_osDependencies.isChecked():
			extFiles = self.core.plugin.getExternalFiles(origin)

			tFilesState = "None"

			while True:
				erFiles = []
				while True:
					tFiles = []
					for i in extFiles:
						if not os.path.exists(i):
							continue

						if i == fileName:
							continue
							
						tPath = os.path.join(assetPath, os.path.basename(i))
						if os.path.exists(tPath):
							if tFilesState != "Overwrite":
								if tFilesState == "Skip":
									continue
								if tFilesState == "Keep newest":
									if int(os.path.getmtime(i)) <= int(os.path.getmtime(tPath)):
										continue
								else:
									if int(os.path.getmtime(i)) != int(os.path.getmtime(tPath)):
										tFiles.append(i)
									if os.path.basename(i) not in [x[0] for x in jobFiles]:
										jobFiles.append([os.path.basename(i), os.path.getmtime(i)])
									continue

						try:
							shutil.copy2(i, assetPath)
							if os.path.basename(i) not in [x[0] for x in jobFiles]:
								jobFiles.append([os.path.basename(i), os.path.getmtime(i)])
						except:
							erFiles.append(i)

					if len(tFiles) > 0:
						fString = "Some assets already exist in the ProjectAsset folder and have a different modification date:\n\n"
						for i in tFiles:
							fString += "%s\n" % i
						msg = QMessageBox(QMessageBox.Warning, "Pandora submission", fString, QMessageBox.Cancel)
						msg.addButton("Keep newest", QMessageBox.YesRole)
						msg.addButton("Overwrite", QMessageBox.YesRole)
						msg.addButton("Skip", QMessageBox.YesRole)
						self.core.parentWindow(msg)
						action = msg.exec_()

						if action == 1:
							extFiles = tFiles
							tFilesState = "Overwrite"
						elif action == 2:
							tFilesState = "Skip"
							break
						elif action != 0:
							if os.path.exists(jobPath):
								try:
									os.remove(jobPath)
								except:
									pass
							return "Execute Canceled: Canceled by user"
						else:
							extFiles = tFiles
							tFilesState = "Keep newest"
							
					else:
						tFilesState = "Skip"
						break

						
				if len(erFiles) > 0:
					fString = "An error occurred while copying external files:\n\n"
					for i in erFiles:
						fString += "%s\n" % i
					msg = QMessageBox(QMessageBox.Warning, "Pandora submission", fString, QMessageBox.Cancel)
					msg.addButton("Retry", QMessageBox.YesRole)
					msg.addButton("Continue", QMessageBox.YesRole)
					self.core.parentWindow(msg)
					action = msg.exec_()


					if action == 1:
						break
					elif action != 0:
						if os.path.exists(jobPath):
							try:
								os.remove(jobPath)
							except:
								pass
						return "Execute Canceled: Canceled by user"
					else:
						extFiles = erFiles
				else:
					break

		while True:
			try:
				if hasattr(self.core.plugin, "sm_render_submitScene") and origin.chb_osDependencies.isChecked():
					self.core.plugin.sm_render_submitScene(origin, jobPath)
				else:
					shutil.copy(fileName, jobPath)
				break
			except:
				msg = QMessageBox(QMessageBox.Warning, "Pandora submission", "An error occurred while copying the file.", QMessageBox.Cancel)
				msg.addButton("Retry", QMessageBox.YesRole)
				msg.addButton("Skip", QMessageBox.YesRole)
				self.core.parentWindow(msg)
				action = msg.exec_()

				if action == 1:
					break
				elif action != 0:
					return "Execute Canceled: Could not copy the files"

		if not origin.chb_osPAssets.isChecked() and len(jobFiles) != len(os.listdir(jobPath)):
			return "Execute Canceled: The filecount in the jobsubmission folder is not correct. %s of %s" % (len(os.listdir(jobPath)), len(jobFiles))

		if not os.path.exists(jobIni):
			open(jobIni, 'a').close()

		if origin.chb_globalRange.isChecked():
			jobFrames = [origin.stateManager.sp_rangeStart.value(), origin.stateManager.sp_rangeEnd.value()]
		else:
			jobFrames = [origin.sp_rangeStart.value(), origin.sp_rangeEnd.value()]

		listSlaves = origin.e_osSlaves.text()

		config = ConfigParser()
		config.read(jobIni)

		config.add_section('jobglobals')
		config.set('jobglobals', 'priority', str(origin.sp_rjPrio.value()))
		config.set('jobglobals', 'uploadOutput', str(origin.chb_osUpload.isChecked()))
		config.set('jobglobals', 'listslaves', listSlaves)
		config.set('jobglobals', 'taskTimeout', str(origin.sp_rjTimeout.value()))
		config.add_section('information')
		config.set('information', 'jobname', jobName)
		config.set('information', 'scenename', os.path.basename(fileName))
		config.set('information', 'projectname', self.core.projectName)
		config.set('information', 'username', self.core.getConfig("globals", "UserName"))
		config.set('information', 'submitdate', time.strftime("%d.%m.%y, %X", time.localtime()))
		config.set('information', 'framerange', "%s-%s" % (jobFrames[0], jobFrames[1]))
		config.set('information', 'outputpath', jobOutputFile)
		config.set('information', 'filecount', str(len(jobFiles)))
		config.set('information', 'savedbasepath', outputBasePath)
		config.set('information', 'outputbase', os.path.dirname(os.path.dirname(jobOutputFile)))
		config.set('information', 'program', self.core.plugin.appName)
		config.set('information', 'prismsubmission', "True")
		
		progVersion = getattr(self.core.plugin, "getProgramVersion", lambda x: "")(origin)
		if progVersion != "":
			config.set('information', 'programversion', progVersion)
	
		if origin.curCam != "Current View":
			config.set('information', 'camera', self.core.plugin.getCamName(origin, origin.curCam))
		if origin.chb_osPAssets.isChecked():
			config.set('information', 'projectassets', str(jobFiles))

		if origin.chb_resOverride.isChecked():
			config.set('jobglobals', "width", str(origin.sp_resWidth.value()))
			config.set('jobglobals', "height", str(origin.sp_resHeight.value()))

		config.add_section('jobtasks')

		curFrame=jobFrames[0]
		tasksNum = 0
		if origin.chb_rjSuspended.isChecked():
			initState = "disabled"
		else:
			initState = "ready"

		fpt = origin.sp_rjFramesPerTask.value()
		while curFrame <= jobFrames[1]:
			startFrame = curFrame
			endFrame = curFrame+fpt-1
			if endFrame > jobFrames[1]:
				endFrame = jobFrames[1]
			config.set('jobtasks', 'task'+ str(tasksNum), str([startFrame, endFrame, initState, "unassigned", "", "", ""]))
			curFrame+=fpt
			tasksNum += 1
		with open(jobIni, 'w') as inifile:
			config.write(inifile)
		
		return "Result=Success"
