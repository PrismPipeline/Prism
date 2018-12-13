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



try:
	from PySide2.QtCore import *
	from PySide2.QtGui import *
	from PySide2.QtWidgets import *
	psVersion = 2
except:
	from PySide.QtCore import *
	from PySide.QtGui import *
	psVersion = 1

import os, sys
import traceback, time, platform, shutil, socket

if platform.system() in ["Linux", "Darwin"]:
	import pwd

from functools import wraps


class Prism_Nuke_Integration(object):
	def __init__(self, core, plugin):
		self.core = core
		self.plugin = plugin
		if platform.system() == "Windows":
			self.examplePath = os.path.join(os.environ["userprofile"], ".nuke")
		elif platform.system() == "Linux":
			userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
			self.examplePath = os.path.join("/home", userName, ".nuke")
		elif platform.system() == "Darwin":
			userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
			self.examplePath = "/Users/%s/.nuke" % userName


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			exc_info = sys.exc_info()
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - Prism_Plugin_Nuke_Integration %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].plugin.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				if hasattr(args[0].core, "writeErrorLog"):
					args[0].core.writeErrorLog(erStr)
				else:
					QMessageBox.warning(args[0].core.messageParent, "Prism Integration", erStr)

		return func_wrapper


	@err_decorator
	def getExecutable(self):
		execPath = ""
		if platform.system() == "Windows":
			execPath = "C:\\Program Files\\Nuke11.2v2\\Nuke11.2.exe"

		return execPath


	@err_decorator
	def integrationAdd(self, origin):
		path = QFileDialog.getExistingDirectory(self.core.messageParent, "Select Nuke folder", self.examplePath)

		if path == "":
			return False

		result = self.writeNukeFiles(path)

		if result:
			QMessageBox.information(self.core.messageParent, "Prism Integration", "Prism integration was added successfully")
			return path

		return result


	@err_decorator
	def integrationRemove(self, origin, installPath):
		result = self.removeIntegration(installPath)

		if result:
			QMessageBox.information(self.core.messageParent, "Prism Integration", "Prism integration was removed successfully")

		return result


	def writeNukeFiles(self, nukepath):
		try:
			if not os.path.exists(nukepath):
				QMessageBox.warning(self.core.messageParent, "Prism Integration", "Invalid Nuke path: %s.\nThe path doesn't exist." % nukepath, QMessageBox.Ok)
				return False

			integrationBase = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Integration")
			addedFiles = []

			origMenuFile = os.path.join(integrationBase, "menu.py")
			with open(origMenuFile, 'r') as mFile:
				initString = mFile.read()

			menuFile = os.path.join(nukepath, "menu.py")

			writeInit = True
			if os.path.exists(menuFile):
				with open(menuFile, 'r') as mFile:
					fileContent = mFile.read()
				if initString in fileContent:
					writeInit = False
				elif "#>>>PrismStart" in fileContent and "#<<<PrismEnd" in fileContent:
					fileContent = fileContent[:fileContent.find("#>>>PrismStart")] + fileContent[fileContent.find("#<<<PrismEnd")+12:]
					with open(menuFile, 'w') as mFile:
						mFile.write(fileContent)

			if writeInit:
				with open(menuFile, 'a') as initfile:
					initfile.write(initString)

			with open(menuFile, "r") as init:
				initStr = init.read()

			with open(menuFile, "w") as init:
				initStr = initStr.replace("PRISMROOT", "\"%s\"" % self.core.prismRoot.replace("\\", "/"))
				init.write(initStr)

			addedFiles.append(menuFile)

			wPrismFile = os.path.join(integrationBase, "WritePrism.gizmo")
			wpPath = os.path.join(nukepath, "WritePrism.gizmo")

			if os.path.exists(wpPath):
				os.remove(wpPath)

			shutil.copy2(wPrismFile, wpPath)
			addedFiles.append(wpPath)

			if platform.system() in ["Linux", "Darwin"]:
				for i in addedFiles:
					os.chmod(i, 0o777)

			return True

		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()

			msgStr = "Errors occurred during the installation of the Nuke integration.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno)
			msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

			QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
			return False


	def removeIntegration(self, installPath):
		try:
			gizmo = os.path.join(installPath, "WritePrism.gizmo")

			for i in [gizmo]:
				if os.path.exists(i):
					os.remove(i)

			menu = os.path.join(installPath, "menu.py")

			for i in [menu]:
				if os.path.exists(i):
					with open(i, "r") as usFile:
						text = usFile.read()

					if "#>>>PrismStart" in text and "#<<<PrismEnd" in text:
						text = text[:text.find("#>>>PrismStart")] + text[text.find("#<<<PrismEnd")+len("#<<<PrismEnd"):]
						with open(i, "w") as usFile:
							usFile.write(text)

			return True

		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()

			msgStr = "Errors occurred during the removal of the Nuke integration.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno)
			msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

			QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
			return False


	def updateInstallerUI(self, userFolders, pItem):
		try:
			nukeItem = QTreeWidgetItem(["Nuke"])
			pItem.addChild(nukeItem)

			if platform.system() == "Windows":
				nukePath = os.path.join(userFolders["UserProfile"], ".nuke")
			elif platform.system() == "Linux":
				userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
				nukePath = os.path.join("/home", userName, ".nuke")
			elif platform.system() == "Darwin":
				userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
				nukePath = "/Users/%s/.nuke" % userName

			if os.path.exists(nukePath):
				nukeItem.setCheckState(0, Qt.Checked)
				nukeItem.setText(1, nukePath)
				nukeItem.setToolTip(0, nukePath)
			else:
				nukeItem.setCheckState(0, Qt.Unchecked)
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			msg = QMessageBox.warning(self.core.messageParent, "Prism Installation", "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s" % (__file__, str(e), exc_type, exc_tb.tb_lineno))
			return False


	def installerExecute(self, nukeItem, result, locFile):
		try:
			installLocs = []

			if nukeItem.checkState(0) == Qt.Checked and os.path.exists(nukeItem.text(1)):
				result["Nuke integration"] = self.writeNukeFiles(nukeItem.text(1))
				if result["Nuke integration"]:
					installLocs.append(nukeItem.text(1))

			return installLocs
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			msg = QMessageBox.warning(self.core.messageParent, "Prism Installation", "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s" % (__file__, str(e), exc_type, exc_tb.tb_lineno))
			return False