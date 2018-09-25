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
from functools import wraps


class Prism_Natron_Integration(object):
	def __init__(self, core, plugin):
		self.core = core
		self.plugin = plugin

		if platform.system() == "Windows":
			self.examplePath = os.path.join(os.environ["userprofile"], ".Natron")
		elif platform.system() == "Linux":
			userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
			self.examplePath = os.path.join("/home", userName, ".Natron")
		elif platform.system() == "Darwin":
			userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
			self.examplePath = "/Users/%s/.Natron" % userName


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			exc_info = sys.exc_info()
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - Prism_Plugin_Natron_Integration %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].plugin.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				if hasattr(args[0].core, "writeErrorLog"):
					args[0].core.writeErrorLog(erStr)
				else:
					QMessageBox.warning(args[0].core.messageParent, "Prism Integration", erStr)

		return func_wrapper


	@err_decorator
	def getExecutable(self):
		execPath = ""
		if platform.system() == "Windows":
			execPath = "C:\\Program Files\\INRIA\\Natron-2.3.14\\bin\\Natron.exe"

		return execPath


	@err_decorator
	def integrationAdd(self, origin):
		path = QFileDialog.getExistingDirectory(self.core.messageParent, "Select Natron folder", self.examplePath)

		if path == "":
			return False

		result = self.writeNatronFiles(path)

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


	def writeNatronFiles(self, natronpath):
		try:
			if not os.path.exists(natronpath):
				QMessageBox.warning(self.core.messageParent, "Prism Integration", "Invalid Natron path: %s.\nThe path doesn't exist." % natronpath, QMessageBox.Ok)
				return False

			integrationBase = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Integration")
			addedFiles = []

			origMenuFile = os.path.join(integrationBase, "initGui.py")
			with open(origMenuFile, 'r') as mFile:
				initString = mFile.read()

			initFile = os.path.join(natronpath, "initGui.py")

			writeInit = True
			if os.path.exists(initFile):
				with open(initFile, 'r') as mFile:
					fileContent = mFile.read()
				if initString in fileContent:
					writeInit = False
				elif "#>>>PrismStart" in fileContent and "#<<<PrismEnd" in fileContent:
					fileContent = fileContent[:fileContent.find("#>>>PrismStart")] + fileContent[fileContent.find("#<<<PrismEnd")+12:]
					with open(initFile, 'w') as mFile:
						mFile.write(fileContent)

			if writeInit:
				with open(initFile, 'a') as initfile:
					initfile.write(initString)

			addedFiles.append(initFile)

			wPrismFile = os.path.join(integrationBase, "WritePrism.py")
			wPrismtFile = os.path.join(natronpath, "WritePrism.py")

			if os.path.exists(wPrismtFile):
				os.remove(wPrismtFile)

			shutil.copy2(wPrismFile, wPrismtFile)
			addedFiles.append(wPrismtFile)

			wPrismIcon = os.path.join(integrationBase, "WritePrism.png")
			wPrismtIcon = os.path.join(natronpath, "WritePrism.png")

			if os.path.exists(wPrismtIcon):
				os.remove(wPrismtIcon)

			shutil.copy2(wPrismIcon, wPrismtIcon)
			addedFiles.append(wPrismtIcon)

			if platform.system() in ["Linux", "Darwin"]:
				for i in addedFiles:
					os.chmod(i, 0o777)

			return True

		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()

			msgStr = "Errors occurred during the installation of the Natron integration.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno)
			msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

			QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
			return False


	def removeIntegration(self, installPath):
		try:
			gizmo = os.path.join(installPath, "WritePrism.py")
			gizmoIcon = os.path.join(installPath, "WritePrism.png")

			for i in [gizmo, gizmoIcon]:
				if os.path.exists(i):
					os.remove(i)

			initFile = os.path.join(installPath, "initGui.py")

			for i in [initFile]:
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

			msgStr = "Errors occurred during the removal of the Natron integration.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno)
			msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

			QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
			return False


	def updateInstallerUI(self, userFolders, pItem):
		try:
			natronItem = QTreeWidgetItem(["Natron"])
			pItem.addChild(natronItem)

			natronPath = self.examplePath
			if os.path.exists(natronPath):
				natronItem.setCheckState(0, Qt.Checked)
				natronItem.setText(1, natronPath)
				natronItem.setToolTip(0, natronPath)
			else:
				natronItem.setCheckState(0, Qt.Unchecked)
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			msg = QMessageBox.warning(self.core.messageParent, "Prism Installation", "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s" % (__file__, str(e), exc_type, exc_tb.tb_lineno))
			return False


	def installerExecute(self, natronItem, result):
		try:
			installLocs = []

			if natronItem.checkState(0) == Qt.Checked and os.path.exists(natronItem.text(1)):
				result["Natron integration"] = self.writeNatronFiles(natronItem.text(1))
				if result["Natron integration"]:
					installLocs.append(natronItem.text(1))

			return installLocs
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			msg = QMessageBox.warning(self.core.messageParent, "Prism Installation", "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s" % (__file__, str(e), exc_type, exc_tb.tb_lineno))
			return False