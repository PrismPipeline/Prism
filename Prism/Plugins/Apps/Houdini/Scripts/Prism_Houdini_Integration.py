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
if platform.system() == "Windows":
	if sys.version[0] == "3":
		import winreg as _winreg
	else:
		import _winreg

if sys.version[0] == "3":
	from configparser import ConfigParser
else:
	from ConfigParser import ConfigParser

from functools import wraps


class Prism_Houdini_Integration(object):
	def __init__(self, core, plugin):
		self.core = core
		self.plugin = plugin

		if platform.system() == "Windows":
			self.examplePath = os.environ["userprofile"] + "\\Documents\\houdini17.5"
		elif platform.system() == "Linux":
			userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
			self.examplePath = os.path.join("/home", userName, "houdini17.5")
		elif platform.system() == "Darwin":
			userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
			self.examplePath = "/Users/%s/Library/Preferences/houdini/17.5" % userName

		if not os.path.exists(self.examplePath):
			for i in ["17.5", "17.0", "16.5", "16.0"]:
				path = self.examplePath[:-4] + i
				if os.path.exists(path):
					self.examplePath = path
					break


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			exc_info = sys.exc_info()
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - Prism_Plugin_Houdini_Integration %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].plugin.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				if hasattr(args[0].core, "writeErrorLog"):
					args[0].core.writeErrorLog(erStr)
				else:
					QMessageBox.warning(args[0].core.messageParent, "Prism Integration", erStr)

		return func_wrapper


	@err_decorator
	def getExecutable(self):
		execPath = ""
		if platform.system() == "Windows":
			defaultpath = os.path.join(self.getHoudiniPath(), "bin", "houdini.exe")
			if os.path.exists(defaultpath):
				execPath = defaultpath

		return execPath

	@err_decorator
	def getHoudiniPath(self):
		try:
			key = _winreg.OpenKey(
				_winreg.HKEY_LOCAL_MACHINE,
				"SOFTWARE\\Side Effects Software",
				0,
				_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
			)
			validVersion = (_winreg.QueryValueEx(key, "ActiveVersion"))[0]

			key = _winreg.OpenKey(
				_winreg.HKEY_LOCAL_MACHINE,
				"SOFTWARE\\Side Effects Software\\Houdini " + validVersion,
				0,
				_winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
			)

			return (_winreg.QueryValueEx(key, "InstallPath"))[0]

		except:
			return ""


	@err_decorator
	def integrationAdd(self, origin):
		path = QFileDialog.getExistingDirectory(self.core.messageParent, "Select Houdini folder", self.examplePath)

		if path == "":
			return False

		result = self.writeHoudiniFiles(path)

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


	def writeHoudiniFiles(self, houdiniPath):
		try:

			# python rc
			pyrc = os.path.join(houdiniPath, "python2.7libs", "pythonrc.py")

			if not os.path.exists(houdiniPath):
				msg = QMessageBox(QMessageBox.Warning, "Prism Installation", "Invalid Houdini path: %s.\n\nThe path has to be the Houdini preferences folder, which usually looks like this: (with your Houdini version):\n\n%s" % (houdiniPath, self.examplePath), QMessageBox.Ok)
				msg.setFocus()
				msg.exec_()
				return False

			integrationBase = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Integration")
			addedFiles = []

			origRCFile = os.path.join(integrationBase, "pythonrc.py")
			with open(origRCFile, 'r') as mFile:
				initString = mFile.read()

			if os.path.exists(pyrc):
				with open(pyrc, 'r') as rcfile:
					content = rcfile.read()
				if not initString in content:
					if "#>>>PrismStart" in content and "#<<<PrismEnd" in content:
						content = content[:content.find("#>>>PrismStart")] + content[content.find("#<<<PrismEnd")+12:] + initString
						with open(pyrc, 'w') as rcfile:
							rcfile.write(content)
					else:
						with open(pyrc, 'a') as rcfile:
							rcfile.write(initString)
			else:
				if not os.path.exists(os.path.dirname(pyrc)):
					os.makedirs(os.path.dirname(pyrc))

				with open(pyrc, 'w') as rcfile:
					rcfile.write(initString)

			addedFiles.append(pyrc)


			# prismInit
			initpath = os.path.join(os.path.dirname(pyrc), "PrismInit.py")

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


			# openScene callback
			openPath = os.path.join(houdiniPath, "scripts", "456.py")

			origOpenFile = os.path.join(integrationBase, "456.py")
			with open(origOpenFile, 'r') as mFile:
				openString = mFile.read()

			if os.path.exists(openPath):
				with open(openPath, 'r') as openFile:
					content = openFile.read()

				if not openString in content:
					if "#>>>PrismStart" in content and "#<<<PrismEnd" in content:
						content = content[:content.find("#>>>PrismStart")] + content[content.find("#<<<PrismEnd")+12:] + openString
						with open(openPath, 'w') as rcfile:
							rcfile.write(content)
					else:
						with open(openPath, 'a') as openFile:
							openFile.write( "\n" + openString)
			else:
				if not os.path.exists(os.path.dirname(openPath)):
					os.makedirs(os.path.dirname(openPath))

				open(openPath, 'a').close()
				with open(openPath, 'w') as openFile:
					openFile.write(openString)

			addedFiles.append(openPath)


			# saveScene callback
			savePath = os.path.join(houdiniPath, "scripts", "afterscenesave.py")

			origSaveFile = os.path.join(integrationBase, "afterscenesave.py")
			with open(origSaveFile, 'r') as mFile:
				saveString = mFile.read()

			if os.path.exists(savePath):
				with open(savePath, 'r') as saveFile:
					content = saveFile.read()

				if not saveString in content:
					if "#>>>PrismStart" in content and "#<<<PrismEnd" in content:
						content = content[:content.find("#>>>PrismStart")] + content[content.find("#<<<PrismEnd")+12:] + saveString
						with open(savePath, 'w') as rcfile:
							rcfile.write(content)
					else:
						with open(savePath, 'a') as saveFile:
							saveFile.write( "\n" + saveString)
			else:
				with open(savePath, 'w') as saveFile:
					saveFile.write(saveString)

			addedFiles.append(savePath)


			if platform.system() in ["Linux", "Darwin"]:
				for i in addedFiles:
					os.chmod(i, 0o777)

			return True

		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			msgStr = "Errors occurred during the installation of the Houdini integration.\nThe installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno)
			msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

			QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
			return False


	def removeIntegration(self, installPath):
		try:
			if os.path.exists(os.path.join(installPath, "houdini", "python2.7libs")):
				installBase = os.path.join(installPath, "houdini")
			else:
				installBase = installPath
			initPy = os.path.join(installBase, "python2.7libs", "PrismInit.py")
			initPyc = initPy + "c"

			for i in [initPy, initPyc]:
				if os.path.exists(i):
					os.remove(i)

			prc = os.path.join(installBase, "python2.7libs", "pythonrc.py")
			sceneOpen = os.path.join(installBase, "scripts", "456.py")
			sceneSave = os.path.join(installBase, "scripts", "afterscenesave.py")

			for i in [prc, sceneOpen, sceneSave]:
				if os.path.exists(i):
					with open(i, "r") as usFile:
						text = usFile.read()

					if "#>>>PrismStart" in text and "#<<<PrismEnd" in text:
						text = text[:text.find("#>>>PrismStart")] + text[text.find("#<<<PrismEnd")+len("#<<<PrismEnd"):]

						otherChars = [x for x in text if x != " "]
						if len(otherChars) == 0:
							os.remove(i)
						else:
							with open(i, "w") as usFile:
								usFile.write(text)

			return True

		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()

			msgStr = "Errors occurred during the removal of the Houdini integration.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno)
			msgStr += "\n\nRunning this application as administrator could solve this problem eventually."

			QMessageBox.warning(self.core.messageParent, "Prism Integration", msgStr)
			return False


	def updateInstallerUI(self, userFolders, pItem):
		try:
			houItem = QTreeWidgetItem(["Houdini"])
			pItem.addChild(houItem)

			houdiniPath = self.examplePath

			if houdiniPath != None and os.path.exists(houdiniPath):
				houItem.setCheckState(0, Qt.Checked)
				houItem.setText(1, houdiniPath)
				houItem.setToolTip(0, houdiniPath)
			else:
				houItem.setCheckState(0, Qt.Unchecked)
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			msg = QMessageBox.warning(self.core.messageParent, "Prism Installation", "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s" % (__file__, str(e), exc_type, exc_tb.tb_lineno))
			return False


	def installerExecute(self, houItem, result, locFile):
		try:
			locConfig = ConfigParser()
			if os.path.exists(locFile):
				try:
					locConfig.read(locFile)
				except:
					pass

			if locConfig.has_section("Houdini"):
				existingPaths = []
				removedInt = False
				opt = locConfig.options("Houdini")
				for i in opt:
					removeInt = False
					path = locConfig.get("Houdini", i)
					if platform.system() == "Windows" and "Side Effects Software" in path:
						removeInt = True
					elif platform.system() == "Linux" and "/opt/hfs" in path:
						removeInt = True
					elif platform.system() == "Darwin" and "/Applications/Houdini/" in path:
						removeInt = True

					if removeInt:
						self.removeIntegration(path)
						removedInt = True
					else:
						existingPaths.append(path)

					locConfig.remove_option("Houdini", i)

				if removedInt:
					for idx, i in enumerate(existingPaths):
						locConfig.set("Houdini", "%02d" % idx, i)

					with open(locFile, 'w') as inifile:
						locConfig.write(inifile)

			installLocs = []

			if houItem.checkState(0) == Qt.Checked and os.path.exists(houItem.text(1)):
				result["Houdini integration"] = self.writeHoudiniFiles(houItem.text(1))
				if result["Houdini integration"]:
					installLocs.append(houItem.text(1))

			return installLocs
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			msg = QMessageBox.warning(self.core.messageParent, "Prism Installation", "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s\n%s" % (__file__, str(e), exc_type, exc_tb.tb_lineno))
			return False