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
if platform.system() == "Windows":
	if sys.version[0] == "3":
		import winreg as _winreg
	else:
		import _winreg

class Prism_Maya_Integration(object):
	def __init__(self, core, plugin):
		self.core = core
		self.plugin = plugin

		if platform.system() == "Windows":
			self.examplePath = os.environ["userprofile"] + "\\Documents\\maya\\2019"
		elif platform.system() == "Linux":
			userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
			self.examplePath = os.path.join("/home", userName, "maya", "2019")
		elif platform.system() == "Darwin":
			userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
			self.examplePath = "/Users/%s/Library/Preferences/Autodesk/maya/2019" % userName


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			exc_info = sys.exc_info()
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - Prism_Plugin_Maya_Integration %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].plugin.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				if hasattr(args[0].core, "writeErrorLog"):
					args[0].core.writeErrorLog(erStr)
				else:
					QMessageBox.warning(args[0].core.messageParent, "Prism Integration", erStr)

		return func_wrapper


	@err_decorator
	def getExecutable(self):
		execPath = ""
		if platform.system() == "Windows":
			defaultpath = os.path.join(self.getMayaPath(), "bin", "maya.exe")
			if os.path.exists(defaultpath):
				execPath = defaultpath

		return execPath


	@err_decorator
	def getMayaPath(self):
		try:
			key = _winreg.OpenKey(
					_winreg.HKEY_LOCAL_MACHINE,
					"SOFTWARE\\Autodesk\\Maya",
					0,
					_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
			)

			mayaVersions = []
			try:
				i = 0
				while True:
					mayaVers = _winreg.EnumKey(key, i)
					if unicode(mayaVers).isnumeric():
						mayaVersions.append(mayaVers)
					i += 1
			except WindowsError:
				pass

			validVersion = mayaVersions[-1]

			key = _winreg.OpenKey(
				_winreg.HKEY_LOCAL_MACHINE,
				"SOFTWARE\\Autodesk\\Maya\\%s\\Setup\\InstallPath" % validVersion,
				0,
				_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
			)

			installDir = (_winreg.QueryValueEx(key, "MAYA_INSTALL_LOCATION"))[0]

			return installDir

		except:
			return ""


	@err_decorator
	def integrationAdd(self, origin):
		path = QFileDialog.getExistingDirectory(self.core.messageParent, "Select Maya folder", os.path.dirname(self.examplePath))

		if path == "":
			return False

		result = self.writeMayaFiles(path)

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


	def writeMayaFiles(self, mayaPath):
		try:
			if not os.path.exists(os.path.join(mayaPath, "scripts")) or not os.path.exists(os.path.join(mayaPath, "prefs", "shelves")):
				QMessageBox.warning(self.core.messageParent, "Prism Installation", "Invalid Maya path: %s.\n\nThe path has to be the Maya preferences folder, which usually looks like this: (with your username and Maya version):\n\nC:\\Users\\Richard\\Documents\\maya\\2018" % mayaPath, QMessageBox.Ok)
				return False

			integrationBase = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Integration")
			addedFiles = []

			origSetupFile = os.path.join(integrationBase, "userSetup.py")
			with open(origSetupFile, 'r') as mFile:
				setupString = mFile.read()

			prismSetup = os.path.join(mayaPath, "scripts", "userSetup.py")

			if os.path.exists(prismSetup):
				with open(prismSetup, 'r') as setupfile:
					content = setupfile.read()

				if not setupString in content:
					if "#>>>PrismStart" in content and "#<<<PrismEnd" in content:
						content = setupString + content[:content.find("#>>>PrismStart")] + content[content.find("#<<<PrismEnd")+12:]
						with open(prismSetup, 'w') as rcfile:
							rcfile.write(content)
					else:
						with open(prismSetup, 'w') as setupfile:
							setupfile.write(setupString + content)
			else:
				open(prismSetup, 'a').close()
				with open(prismSetup, 'w') as setupfile:
					setupfile.write(setupString)

			addedFiles.append(prismSetup)

			initpath = os.path.join(mayaPath, "scripts", "PrismInit.py")

			if os.path.exists(initpath):
				os.remove(initpath)

			if os.path.exists(initpath + "c"):
				os.remove(initpath + "c")

			origInitFile = os.path.join(integrationBase, "PrismInit.py")
			shutil.copy2(origInitFile, initpath)
			addedFiles.append(initpath)

			with open(initpath, "r") as init:
				initStr = init.read()

			with open(initpath, "w") as init:
				initStr = initStr.replace("PRISMROOT", "\"%s\"" % self.core.prismRoot.replace("\\", "/"))
				init.write(initStr)

			shelfpath = os.path.join(mayaPath, "prefs", "shelves", "shelf_Prism.mel")

			if os.path.exists(shelfpath):
				os.remove(shelfpath)
		
			origShelfFile = os.path.join(integrationBase, "shelf_Prism.mel")
			shutil.copy2(origShelfFile, shelfpath)
			addedFiles.append(shelfpath)

			icons = ["prismSave.png", "prismSaveComment.png", "prismBrowser.png", "prismStates.png", "prismSettings.png"]

			for i in icons:
				iconPath = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", i)
				tPath = os.path.join(mayaPath, "prefs", "icons", i)

				if os.path.exists(tPath):
					os.remove(tPath)

				shutil.copy2(iconPath, tPath)
				addedFiles.append(tPath)

			if platform.system() in ["Linux", "Darwin"]:
				for i in addedFiles:
					os.chmod(i, 0o777)

			return True

		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()

			msgStr = "Errors occurred during the installation of the Maya integration.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno)
			msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

			QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
			return False


	def removeIntegration(self, installPath):
		try:
			initPy = os.path.join(installPath, "scripts", "PrismInit.py")
			initPyc = os.path.join(installPath, "scripts", "PrismInit.pyc")
			shelfpath = os.path.join(installPath, "prefs", "shelves", "shelf_Prism.mel")

			for i in [initPy, initPyc, shelfpath]:
				if os.path.exists(i):
					os.remove(i)

			userSetup = os.path.join(installPath, "scripts", "userSetup.py")

			if os.path.exists(userSetup):
				with open(userSetup, "r") as usFile:
					text = usFile.read()

				if "#>>>PrismStart" in text and "#<<<PrismEnd" in text:
					text = text[:text.find("#>>>PrismStart")] + text[text.find("#<<<PrismEnd")+len("#<<<PrismEnd"):]

					otherChars = [x for x in text if x != " "]
					if len(otherChars) == 0:
						os.remove(userSetup)
					else:
						with open(userSetup, "w") as usFile:
							usFile.write(text)

			return True

		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()

			msgStr = "Errors occurred during the removal of the Maya integration.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno)
			msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

			QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
			return False


	def updateInstallerUI(self, userFolders, pItem):
		try:
			if platform.system() == "Windows":
				mayaPath = [os.path.join(userFolders["Documents"], "maya", "2016"), os.path.join(userFolders["Documents"], "maya", "2017"), os.path.join(userFolders["Documents"], "maya", "2018"), os.path.join(userFolders["Documents"], "maya", "2019")]
			elif platform.system() == "Linux":
				userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
				mayaPath = [os.path.join("/home", userName, "maya", "2016"), os.path.join("/home", userName, "maya", "2017"), os.path.join("/home", userName, "maya", "2018"), os.path.join("/home", userName, "maya", "2019")]
			elif platform.system() == "Darwin":
				userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
				mayaPath = ["/Users/%s/Library/Preferences/Autodesk/maya/2016" % userName, "/Users/%s/Library/Preferences/Autodesk/maya/2017" % userName, "/Users/%s/Library/Preferences/Autodesk/maya/2018" % userName, "/Users/%s/Library/Preferences/Autodesk/maya/2019" % userName]

			mayaItem = QTreeWidgetItem(["Maya"])
			mayaItem.setCheckState(0, Qt.Checked)
			pItem.addChild(mayaItem)

			mayacItem = QTreeWidgetItem(["Custom"])
			mayacItem.setToolTip(0, "e.g. \"%s\"" % self.examplePath)
			mayacItem.setToolTip(1, "e.g. \"%s\"" % self.examplePath)
			mayacItem.setCheckState(0, Qt.Unchecked)
			mayaItem.addChild(mayacItem)
			#mayaItem.setExpanded(True)

			activeVersion = False
			for i in mayaPath:
				mayavItem = QTreeWidgetItem([i[-4:]])
				mayaItem.addChild(mayavItem)

				if os.path.exists(i):
					mayavItem.setCheckState(0, Qt.Checked)
					mayavItem.setText(1, i)
					mayavItem.setToolTip(0, i)
					mayacItem.setText(1, i)
					activeVersion = True
				else:
					mayavItem.setCheckState(0, Qt.Unchecked)
					mayavItem.setFlags(~Qt.ItemIsEnabled)

			if not activeVersion:
				mayaItem.setCheckState(0, Qt.Unchecked)
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			msg = QMessageBox.warning(self.core.messageParent, "Prism Installation", "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s" % (__file__, str(e), exc_type, exc_tb.tb_lineno))
			return False


	def installerExecute(self, mayaItem, result, locFile):
		try:
			mayaPaths = []
			installLocs = []

			if mayaItem.checkState(0) != Qt.Checked:
				return installLocs

			for i in range(mayaItem.childCount()):
				item = mayaItem.child(i)
				if item.checkState(0) == Qt.Checked and os.path.exists(item.text(1)):
					mayaPaths.append(item.text(1))

			for i in mayaPaths:
				result["Maya integration"] = self.writeMayaFiles(i)
				if result["Maya integration"]:
					installLocs.append(i)

			return installLocs
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			msg = QMessageBox.warning(self.core.messageParent, "Prism Installation", "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s" % (__file__, str(e), exc_type, exc_tb.tb_lineno))
			return False