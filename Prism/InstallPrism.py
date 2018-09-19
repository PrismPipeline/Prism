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



import os, shutil, sys, imp, subprocess, csv, platform
from ConfigParser import ConfigParser

if platform.system() == "Windows":
	import _winreg, win32com
	from win32com.shell import shellcon
	import win32com.shell.shell as shell
	import win32con, win32event, win32process
else:
	import pwd

sys.path.append(os.path.join(os.path.dirname(__file__), 'PrismFiles/Scripts'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'PrismFiles/PythonLibs/Python27'))

try:
	from PySide2.QtCore import *
	from PySide2.QtGui import *
	from PySide2.QtWidgets import *
	psVersion = 2
except:
	from PySide.QtCore import *
	from PySide.QtGui import *
	psVersion = 1

import InstallList
from UserInterfacesPrism import qdarkstyle

class PrismInstaller():
	def __init__(self, user):
		try:
			self.exUser = user

			pluginPath = os.path.abspath(os.path.join(__file__, os.pardir, "PrismFiles", "Plugins"))
			sys.path.append(pluginPath)

			self.prismPlugins = {}
			for i in os.listdir(pluginPath):
				initmodule = "Prism_%s_init_unloaded" % i
				initPath = os.path.join(pluginPath, i, "Scripts", initmodule + ".py")
				if not os.path.exists(initPath):
					continue

				sys.path.append(os.path.dirname(initPath))
				core = self
				core.messageParent = QWidget()
			#	try:
				pPlug = getattr(__import__("Prism_%s_init_unloaded" % (i)), "Prism_%s_unloaded" % i)(core)
				if hasattr(pPlug, "updateInstallerUI") and platform.system() in pPlug.platforms:
					self.prismPlugins[pPlug.appName] = pPlug
			#	except:
			#		pass
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			QMessageBox.warning(QWidget(), "Prism Integration", "Errors occurred during the installation.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno))


	def copyfiles(self, prismPath, patch):
		try:
			data = ""
			locFile = os.path.join(prismPath, "installLocations.ini")

			if patch:
				sys.path.append(os.path.join(prismPath, "PythonLibs", "Python27"))
			else:
				sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "PrismFiles", "PythonLibs", "Python27"))

			try:
				import psutil
			except:
				pass
			else:
				PROCNAMES = ['PrismTray.exe', "PrismProjectBrowser.exe", "PrismSettings.exe"]
				for proc in psutil.process_iter():
					if proc.name() in PROCNAMES:
						p = psutil.Process(proc.pid)

						try:
							if not 'SYSTEM' in p.username():
								try:
									proc.kill()
									print "closed Prism process"
								except:
									pass
						except:
							pass

			if os.path.exists(prismPath):
				if not patch:

					print "remove old files.."
					if os.path.exists(locFile):
						with open(locFile, 'r') as installfile:
							data = installfile.read()

					if platform.system() == "Darwin":
						remPath = os.path.dirname(prismPath)
					else:
						remPath = prismPath

					while True:
						try:
							if os.path.exists(remPath):
								shutil.rmtree(remPath)
							break
						except:
							msg = QMessageBox(QMessageBox.Warning, "Remove old files", "Could not remove old files.\n\nMake sure all dependent programms like 3dsMax, Maya, Houdini, Blender, Nuke and eventually the windows explorer are closed.", QMessageBox.Cancel)
							msg.addButton("Retry", QMessageBox.YesRole)
							msg.setFocus()
							action = msg.exec_()

							if action != 0:
								msg = QMessageBox(QMessageBox.Warning, "Prism Installation", "Could not install new Prism files.", QMessageBox.Ok)
								msg.setFocus()
								msg.exec_()
								return False

			elif patch:
				msg = QMessageBox(QMessageBox.Warning, "Prism Installation", "Prism is not installed. Please install Prism before you install this patch.", QMessageBox.Ok)
				msg.setFocus()
				msg.exec_()
				return False


			print "copy new files.."

			if patch:
				while True:
					try:
						if os.path.exists(os.path.join(prismPath, "Plugins")):
							shutil.rmtree(os.path.join(prismPath, "Plugins"))
						if os.path.exists(os.path.join(prismPath, "ProjectFiles")):
							shutil.rmtree(os.path.join(prismPath, "ProjectFiles"))
						if os.path.exists(os.path.join(prismPath, "Scripts")):
							shutil.rmtree(os.path.join(prismPath, "Scripts"))
						break
					except WindowsError:
						msg = QMessageBox(QMessageBox.Warning, "Remove old files", "Could not remove old files.\n\nMake sure all dependent programms like 3dsMax, Maya, Houdini, Blender, Nuke and eventually the windows explorer are closed.", QMessageBox.Cancel)
						msg.addButton("Retry", QMessageBox.YesRole)
						msg.setFocus()
						action = msg.exec_()

						if action != 0:
							msg = QMessageBox(QMessageBox.Warning, "Prism Installation", "Could not install new Prism files.", QMessageBox.Ok)
							msg.setFocus()
							msg.exec_()
							return False

				shutil.copytree(os.path.dirname(os.path.abspath(__file__)) + "\\PrismFiles\\Plugins", prismPath + "\\Plugins")
				shutil.copytree(os.path.dirname(os.path.abspath(__file__)) + "\\PrismFiles\\ProjectFiles", prismPath + "\\ProjectFiles")
				shutil.copytree(os.path.dirname(os.path.abspath(__file__)) + "\\PrismFiles\\Scripts", prismPath + "\\Scripts")
			else:
				while True:
					try:
						shutil.copytree(os.path.join(os.path.dirname(os.path.abspath(__file__)), "PrismFiles"), prismPath)
						break
					except Exception as e:
						exc_type, exc_obj, exc_tb = sys.exc_info()
						msg = QMessageBox(QMessageBox.Warning, "Prism Installation", "Could not copy new files.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno), QMessageBox.Cancel)
						msg.addButton("Retry", QMessageBox.YesRole)
						msg.setFocus()
						action = msg.exec_()

						if action != 0:
							msg = QMessageBox(QMessageBox.Warning, "Prism Installation", "Could not install new Prism files.", QMessageBox.Ok)
							msg.setFocus()
							msg.exec_()
							return False

				if platform.system() in ["Linux", "Darwin"]:
					if platform.system() in ["Darwin"]:
						os.chmod(os.path.dirname(prismPath), 0o777)
					os.chmod(prismPath, 0o777)
					for root, dirs, files in os.walk(prismPath):
						for d in dirs:
							os.chmod(os.path.join(root, d), 0o777)

						for f in files:
							os.chmod(os.path.join(root, f), 0o777)


			if data != "":
				open(locFile, 'a').close()
				with open(locFile, 'w') as lfile:
					lfile.write(data)

			return True

		except Exception,e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			msg = QMessageBox(QMessageBox.Warning, "Prism Installation", "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno), QMessageBox.Ok)
			msg.setFocus()
			msg.exec_()

			return False


	def openBrowse(self, item, column):
		if item.parent().text(0) != "DCC integrations" and item.text(0) not in ["Custom"] or item.childCount() > 0:
			return

		path = QFileDialog.getExistingDirectory(QWidget(), "Select destination folder", item.text(column))
		if path != "":
			item.setText(1, path)
			item.setToolTip(1, path)


	def CompItemClicked(self, item, column):
		if item.text(0) == "Prism files":
			if item.checkState(0) == Qt.Checked:
				settingsPath = item.child(0).text(1)
				if os.path.exists(settingsPath):
					item.child(0).setFlags(item.child(0).flags() | Qt.ItemIsEnabled)
			else:
				item.child(0).setFlags(~Qt.ItemIsEnabled)
		else:
			if item.text(0) in ["DCC integrations"] or item.childCount == 0:
				return

			isEnabled =  item.checkState(0) == Qt.Checked
			for i in range(item.childCount()):
				if isEnabled:
					if item.child(i).text(0) == "Custom" or item.child(i).text(1) != "":
						item.child(i).setFlags(item.child(i).flags() | Qt.ItemIsEnabled)
				else:
					item.child(i).setFlags(~Qt.ItemIsEnabled)


	def refreshUI(self, pList, username, documents):
		try:
			if platform.system() == "Windows":
				lappdata = os.path.join(os.path.dirname(os.environ["Userprofile"]), username, "AppData", "Local")
				appdata = os.path.join(os.path.dirname(os.environ["Userprofile"]), username, "AppData", "Roaming")
				uProfile = os.path.join(os.path.dirname(os.environ["Userprofile"]), username)
				if self.exUser == username:
					docs = documents
				else:
					docs = os.path.join(uProfile, "Documents")
				userFolders = {"LocalAppdata": lappdata, "AppData": appdata, "UserProfile": uProfile, "Documents":docs }
			else:
				userFolders = {}

			pList.tw_components.clear()

			prismFilesItem = QTreeWidgetItem(["Prism files"])
			pList.tw_components.addTopLevelItem(prismFilesItem)
			prismFilesItem.setCheckState(0, Qt.Checked)

			keepSettingsItem = QTreeWidgetItem(["Keep old settings"])
			prismFilesItem.addChild(keepSettingsItem)
			prismFilesItem.setExpanded(True)

			pList.tw_components.itemClicked.connect(self.CompItemClicked)

			if platform.system() == "Windows":
				settingsPath = userFolders["LocalAppdata"] + "\\Prism\\Prism.ini"
				settingsPathOld = userFolders["LocalAppdata"] + "\\Prism\\PrismOLD.ini"
			elif platform.system() == "Linux":
				settingsPath = "/usr/local/Prism/Prism.ini"
				settingsPathOld = "/usr/local/Prism/PrismOLD.ini"
			elif platform.system() == "Darwin":
				settingsPath = "/Applications/Prism/Prism/Prism.ini"
				settingsPathOld = "/Applications/Prism/Prism/PrismOLD.ini"

			if os.path.exists(settingsPath):
				keepSettingsItem.setCheckState(0, Qt.Checked)
				keepSettingsItem.setText(1, settingsPath)
			elif os.path.exists(settingsPathOld):
				keepSettingsItem.setCheckState(0, Qt.Checked)
				keepSettingsItem.setText(1, settingsPathOld)
			else:
				keepSettingsItem.setCheckState(0, Qt.Unchecked)
				keepSettingsItem.setFlags(~Qt.ItemIsEnabled)

			if len(self.prismPlugins) > 0:
				integrationsItem = QTreeWidgetItem(["DCC integrations"])
				pList.tw_components.addTopLevelItem(integrationsItem)

				for i in sorted(self.prismPlugins):
					self.prismPlugins[i].updateInstallerUI(userFolders, integrationsItem)

				integrationsItem.setExpanded(True)

		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			msg = QMessageBox.warning(QWidget(), "Prism Installation", "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno))
			return False


	def install(self, patch=False, documents=""):
		try:
			pList = InstallList.InstallList()
			pList.setModal(True)

			pList.tw_components.header().resizeSection(0,200)
			pList.tw_components.itemDoubleClicked.connect(self.openBrowse)

			self.refreshUI(pList, self.exUser, documents=documents)

			if platform.system() == "Windows":
				userDir = os.path.dirname(os.environ["Userprofile"])
				pList.cb_users.addItems([x for x in os.listdir(userDir) if x not in ["All Users", "Default", "Default User"] and os.path.isdir(os.path.join(userDir,x))])
				pList.cb_users.setCurrentIndex(pList.cb_users.findText(self.exUser))
				pList.cb_users.currentIndexChanged[str].connect(lambda x:self.refreshUI(pList, x, documents=documents))
			else:
				pList.widget.setVisible(False)

			pList.buttonBox.button(QDialogButtonBox.Ok).setText("Install")
			pList.buttonBox.button(QDialogButtonBox.Cancel).setFocusPolicy(Qt.NoFocus)

			pList.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))
			pList.setFocus()

			result = pList.exec_()

			if result == 0:
				print "Installation canceled"
				return False

			print "\n\nInstalling - please wait.."

			waitmsg = QMessageBox(QMessageBox.NoIcon, "Prism Installation", "Installing - please wait..", QMessageBox.Cancel)
			waitmsg.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))
			waitmsg.setWindowIcon(wIcon)
			waitmsg.buttons()[0].setHidden(True)
			waitmsg.show()
			QCoreApplication.processEvents()

			if platform.system() == "Windows":
				lappdata = os.path.join(os.path.dirname(os.environ["Userprofile"]), pList.cb_users.currentText(), "AppData", "Local")
				appdata = os.path.join(os.path.dirname(os.environ["Userprofile"]), pList.cb_users.currentText(), "AppData", "Roaming")
				userFolders = {"LocalAppdata": lappdata, "AppData": appdata, "Documents": documents }
				settingsPath = userFolders["LocalAppdata"] + "\\Prism\\Prism.ini"
				settingsPathOld = userFolders["LocalAppdata"] + "\\Prism\\PrismOLD.ini"
				prismPath = userFolders["LocalAppdata"] + "\\Prism\\"
			elif platform.system() == "Linux":
				userFolders = {}
				settingsPath = "/usr/local/Prism/Prism.ini"
				settingsPathOld = "/usr/local/Prism/PrismOLD.ini"
				prismPath = "/usr/local/Prism"
			elif platform.system() == "Darwin":
				userFolders = {}
				settingsPath = "/Applications/Prism/Prism/Prism.ini"
				settingsPathOld = "/Applications/Prism/Prism/PrismOLD.ini"
				prismPath = "/Applications/Prism/Prism"

			prismFilesItem = pList.tw_components.findItems("Prism files", Qt.MatchExactly)[0]
			keepSettingsItem = prismFilesItem.child(0)
			dccItems = pList.tw_components.findItems("DCC integrations", Qt.MatchExactly | Qt.MatchRecursive)
			if len(dccItems) > 0:
				dccItem = dccItems[0]
			else:
				dccItem = None

			result = {}

			
			if prismFilesItem.checkState(0) == Qt.Checked:
				if keepSettingsItem.checkState(0) == Qt.Checked:
					if os.path.exists(settingsPath):
						sPath = settingsPath
					elif os.path.exists(settingsPathOld):
						sPath = settingsPathOld

					pconfig = ConfigParser()
					try:
						pconfig.read(sPath)
					except:
						os.remove(sPath)

				result["Prism Files"] = self.copyfiles(prismPath, patch)

				if not result["Prism Files"]:
					return result

				if keepSettingsItem.checkState(0) == Qt.Checked and "pconfig" in locals():
					writeIni = True
					if not os.path.exists(os.path.dirname(settingsPathOld)):
						try:
							os.makedirs(os.path.dirname(settingsPathOld))
						except:
							writeIni = False

					if writeIni:
						open(settingsPathOld, 'a').close()
						with open(settingsPathOld, 'w') as inifile:
							pconfig.write(inifile)

						if platform.system() in ["Linux", "Darwin"]:
							os.chmod(settingsPathOld, 0o777)

			installLocs = {}

			if dccItem is not None:
				for i in range(dccItem.childCount()):
					childItem = dccItem.child(i)
					if not childItem.text(0) in self.prismPlugins:
						continue

					installLocs[childItem.text(0)] = self.prismPlugins[childItem.text(0)].installerExecute(childItem, result)

			locFile = os.path.join(prismPath, "installLocations.ini")
			if len(installLocs) > 0:
				
				locConfig = ConfigParser()

				if os.path.exists(locFile):
					try:
						locConfig.read(locFile)
					except:
						pass

				for i in installLocs:
					existingItems = []
					if locConfig.has_section(i):
						existingItems = locConfig.items(i)
					else:
						locConfig.add_section(i)

					paths = installLocs[i]
					if type(paths) != list:
						continue

					for path in paths:
						if path not in [x[1] for x in existingItems]:
							locConfig.set(i, "%02d" % (len(existingItems)+1), path)

				with open(locFile, 'w') as inifile:
					locConfig.write(inifile)


			if platform.system() == "Windows":
				# setting regestry keys for wand module (EXR preview in Blender and Nuke)
				curkey = _winreg.CreateKey(_winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\ImageMagick\Current")
				_winreg.SetValueEx(curkey, "Version", 0, _winreg.REG_SZ, "6.9.9")
				key = _winreg.CreateKey(_winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\ImageMagick\6.9.9\Q:16")
				_winreg.SetValueEx(key, "LibPath", 0, _winreg.REG_SZ, os.path.join(userFolders["LocalAppdata"], "Prism", "Tools", "ImageMagick-6.9.9-Q16"))
				_winreg.SetValueEx(key, "CoderModulesPath", 0, _winreg.REG_SZ, os.path.join(userFolders["LocalAppdata"], "Prism", "Tools", "ImageMagick-6.9.9-Q16", "modules", "coders"))
				_winreg.SetValueEx(key, "FilterModulesPath", 0, _winreg.REG_SZ, os.path.join(userFolders["LocalAppdata"], "Prism", "Tools", "ImageMagick-6.9.9-Q16", "modules", "filters"))
				key.Close()
				curkey.Close()

				trayStartup = userFolders["AppData"] + "\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\PrismTray.lnk"
				trayStartMenu = userFolders["AppData"] + "\\Microsoft\\Windows\\Start Menu\\Programs\\Prism\\PrismTray.lnk"
				pbStartMenu = userFolders["AppData"] + "\\Microsoft\\Windows\\Start Menu\\Programs\\Prism\\PrismProjectBrowser.lnk"
				settingsStartMenu = userFolders["AppData"] + "\\Microsoft\\Windows\\Start Menu\\Programs\\Prism\\PrismSettings.lnk"

				trayLnk = os.path.join(userFolders["LocalAppdata"], "Prism", "Tools", "PrismTray.lnk")
				pbLnk = os.path.join(userFolders["LocalAppdata"], "Prism", "Tools", "PrismProjectBrowser.lnk")
				settingsLnk = os.path.join(userFolders["LocalAppdata"], "Prism", "Tools", "PrismSettings.lnk")

				cbPath = trayStartup

			elif platform.system() == "Linux":
				if os.path.exists(locFile):
					os.chmod(locFile, 0o777)
					
				trayStartup = "/etc/xdg/autostart/PrismTray.desktop"
				trayStartMenu = "/usr/share/applications/PrismTray.desktop"
				pbStartMenu = "/usr/share/applications/PrismProjectBrowser.desktop"
				settingsStartMenu = "/usr/share/applications/PrismSettings.desktop"

				trayLnk = "/usr/local/Prism/Tools/PrismTray.desktop"
				pbLnk = "/usr/local/Prism/Tools/PrismProjectBrowser.desktop"
				settingsLnk = "/usr/local/Prism/Tools/PrismSettings.desktop"

				cbPath = "/usr/local/Prism/Tools/PrismTray.sh"

				pMenuSource = "/usr/local/Prism/Tools/Prism.menu"
				pMenuTarget = "/etc/xdg/menus/applications-merged/Prism.menu"

				if not os.path.exists(os.path.dirname(pMenuTarget)):
					try:
						os.makedirs(os.path.dirname(pMenuTarget))
					except:
						pass

				if os.path.exists(pMenuTarget):
					os.remove(pMenuTarget)

				if os.path.exists(pMenuSource) and os.path.exists(os.path.dirname(pMenuTarget)):
					shutil.copy2(pMenuSource, pMenuTarget)
				else:
					print "could not create Prism startmenu entry"

				if os.path.exists(pbLnk):
					userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
					desktopPath = "/home/%s/Desktop/%s" % (userName, os.path.basename(pbLnk))
					if os.path.exists(desktopPath):
						try:
							os.remove(desktopPath)
						except:
							pass

					if os.path.exists(os.path.dirname(desktopPath)):
						shutil.copy2(pbLnk, desktopPath)
						uid = pwd.getpwnam(userName).pw_uid
						os.chown(desktopPath, uid, -1)

				#subprocess.Popen(['bash', "/usr/local/Prism/Tools/PrismTray.sh"])

			elif platform.system() == "Darwin":
				if os.path.exists(locFile):
					os.chmod(locFile, 0o777)
				
				userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
				trayStartup = "/Users/%s/Library/LaunchAgents/com.user.PrismTray.plist" % userName
				trayStartMenu = "/Applications/Prism/Prism Tray.app"
				pbStartMenu = "/Applications/Prism/Prism Project Browser.app"
				settingsStartMenu = "/Applications/Prism/Prism Settings.app"

				trayStartupSrc = "/Applications/Prism/Prism/Tools/com.user.PrismTray.plist"
				trayLnk = "/Applications/Prism/Prism/Tools/Prism Tray.app"
				pbLnk = "/Applications/Prism/Prism/Tools/Prism Project Browser.app"
				settingsLnk = "/Applications/Prism/Prism/Tools/Prism Settings.app"

				cbPath = "/Applications/Prism/Prism/Tools/PrismTray.sh"


				if os.path.exists(pbLnk):
					desktopPath = "/Users/%s/Desktop/%s" % (userName, os.path.splitext(os.path.basename(pbLnk))[0])
					if os.path.exists(desktopPath):
						try:
							os.remove(desktopPath)
						except:
							pass
					os.symlink(pbLnk, desktopPath)

				#subprocess.Popen(['bash', "/usr/local/Prism/Tools/PrismTray.sh"])


			if trayStartMenu != "" and not os.path.exists(os.path.dirname(trayStartMenu)):
				try:
					os.makedirs(os.path.dirname(trayStartMenu))
				except:
					pass

			if not os.path.exists(os.path.dirname(trayStartup)):
				try:
					os.makedirs(os.path.dirname(trayStartup))
					if platform.system() in ["Linux", "Darwin"]:
						os.chmod(os.path.dirname(trayStartup), 0o777)
				except:
					pass

			if os.path.exists(trayStartup):
				os.remove(trayStartup)

			if os.path.exists(trayLnk):
				if os.path.exists(os.path.dirname(trayStartup)):
					if platform.system() == "Darwin":
						if os.path.exists(trayStartupSrc):
							shutil.copy2(trayStartupSrc, trayStartup)
							os.chmod(trayStartup, 0o644)
							uid = pwd.getpwnam(userName).pw_uid
							os.chown(os.path.dirname(trayStartup), uid, -1)
							os.chown(trayStartup, uid, -1)
						#	os.system("launchctl load /Users/%s/Library/LaunchAgents/com.PrismTray.plist" % userName)
					else:
						shutil.copy2(trayLnk, trayStartup)
				else:
					print "could not create PrismTray autostart entry"

				if trayStartMenu != "":
					if os.path.exists(os.path.dirname(trayStartMenu)):
						if os.path.isdir(trayLnk):
							if os.path.exists(trayStartMenu):
								shutil.rmtree(trayStartMenu)
							shutil.copytree(trayLnk, trayStartMenu)
						else:
							shutil.copy2(trayLnk, trayStartMenu)
					else:
						print "could not create PrismTray startmenu entry"

			if pbStartMenu != "":
				if os.path.exists(pbLnk) and os.path.exists(os.path.dirname(pbStartMenu)):
					if os.path.isdir(pbLnk):
						if os.path.exists(pbStartMenu):
							shutil.rmtree(pbStartMenu)
						shutil.copytree(pbLnk, pbStartMenu)
					else:
						shutil.copy2(pbLnk, pbStartMenu)
				else:
					print "could not create PrismProjectBrowser startmenu entry"

			if settingsStartMenu != "":
				if os.path.exists(settingsLnk) and os.path.exists(os.path.dirname(settingsStartMenu)):
					if os.path.isdir(settingsLnk):
						if os.path.exists(settingsStartMenu):
							shutil.rmtree(settingsStartMenu)
						shutil.copytree(settingsLnk, settingsStartMenu)
					else:
						shutil.copy2(settingsLnk, settingsStartMenu)
				else:
					print "could not create PrismSettings startmenu entry"

			cb = qApp.clipboard()
			cb.setText(trayLnk)

			if "waitmsg" in locals() and waitmsg.isVisible():
				waitmsg.close()

			print "Finished"

			return result

		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			msg = QMessageBox(QMessageBox.Warning, "Prism Installation", "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno), QMessageBox.Ok)
			msg.setFocus()
			msg.exec_()
			return False


	def uninstall(self):
		import UninstallPrism

		return UninstallPrism.uninstallPrism(self, user=self.exUser)


def openInstallerDialog(prismPath, username, docFolder):
	isPatch = False #not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "PrismFiles", "Python27"))

	actionType = "install"

	if os.path.exists(prismPath):
		msg = QMessageBox(QMessageBox.Question, "Prism Pipeline", "An existing Prism installation was found.\nWhat do you want to do?\n\n(You don't need to uninstall Prism before you install a new version)", QMessageBox.Cancel)
		msg.addButton("Install", QMessageBox.YesRole)
		msg.addButton("Uninstall", QMessageBox.YesRole)
		msg.setFocus()
		action = msg.exec_()

		if action == 0:
			actionType = "install"
		elif action == 1:
			actionType = "uninstall"
		else:
			actionType = "cancel"

	pInstaller = PrismInstaller(user=username)

	if actionType == "install":
		result = pInstaller.install(patch=isPatch, documents=docFolder)
	elif actionType == "uninstall":
		result = pInstaller.uninstall()
	else:
		result = False
	
	if result == False:
		msg = QMessageBox(QMessageBox.Warning, "Prism Installation", "Installation was canceled", QMessageBox.Ok)
		msg.setFocus()
		msg.exec_()
	elif not False in result.values():
		if actionType == "install":
			msg = QMessageBox(QMessageBox.Information, "Prism Installation", "Prism was installed successfully.", QMessageBox.Ok)
			msg.setFocus()
			msg.exec_()
		elif actionType == "uninstall":
			msgStr = "Prism was uninstalled successfully."
			if platform.system() == "Windows":
				msgStr += "\n(You can ignore the \"Run Prism\" checkbox, which you will see on the installer after you press OK)"
			msg = QMessageBox(QMessageBox.Information, "Prism Uninstallation", msgStr, QMessageBox.Ok)
			msg.setFocus()
			msg.exec_()
	else:
		msgString = "Some parts failed to %s:\n\n" % actionType
		for i in result:
			msgString += "%s:\t\t%s\t\t\n\n" % (i, result[i])

		msgString = msgString.replace("True", "Success").replace("False", "Error").replace("Prism Files:", "Prism Files:\t")

		msg = QMessageBox(QMessageBox.Warning, "Prism Installation", msgString, QMessageBox.Ok)
		msg.setFocus()
		msg.exec_()


def force_elevated(user, documents):
	try:
		if sys.argv[-1] != 'asadmin':
			script = os.path.abspath(sys.argv[0])
			params = ' '.join(["\"%s\"" % script] + sys.argv[1:] + ["\"%s\"" % (user), "\"%s\"" % (documents), 'asadmin'])
			procInfo = shell.ShellExecuteEx(nShow=win32con.SW_SHOWNORMAL,
								 fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
								 lpVerb='runas',
								 lpFile=sys.executable,
								 lpParameters=params)

			procHandle = procInfo['hProcess']    
			obj = win32event.WaitForSingleObject(procHandle, win32event.INFINITE)
			rc = win32process.GetExitCodeProcess(procHandle)

	except Exception as ex:
		print ex


def startInstaller_Windows():
	from win32com.shell import shell, shellcon
	documents = shell.SHGetFolderPath(0, shellcon.CSIDL_PERSONAL, None, 0)

	if sys.argv[-1] != 'asadmin':
		force_elevated(user=os.environ["username"], documents=documents)
	else:
		try:
			username = sys.argv[-3]
			docFolder = sys.argv[-2]
			prismPath = os.path.join(os.path.dirname(os.environ["Userprofile"]), username, "AppData", "Local", "Prism")

			openInstallerDialog(prismPath, username, docFolder)

		except Exception,e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			QMessageBox.warning(QWidget(), "Prism Installation", "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno))


def startInstaller_Linux():
	try:
		if os.getuid() != 0:
			QMessageBox.warning(QWidget(), "Prism Installation", "Please run this installer as root to continue.")
			return

		prismPath = os.path.join("/usr", "local", "Prism")
		username = ""
		docFolder = ""

		openInstallerDialog(prismPath, username, docFolder)

	except Exception,e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		QMessageBox.warning(QWidget(), "Prism Installation", "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno))


def startInstaller_Mac():
	try:
		if os.getuid() != 0:
			QMessageBox.warning(QWidget(), "Prism Installation", "Please run this installer as root to continue.")
			return

		prismPath = "/Applications/Prism/Prism"
		username = ""
		docFolder = ""

		openInstallerDialog(prismPath, username, docFolder)

	except Exception,e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		QMessageBox.warning(QWidget(), "Prism Installation", "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno))




if __name__ == "__main__":
	qapp = QApplication(sys.argv)
	try:
		wIcon = QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "PrismFiles", "Scripts", "UserInterfacesPrism", "p_tray.png"))
		qapp.setWindowIcon(wIcon)
		qapp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))

		if platform.system() == "Windows":
			startInstaller_Windows()
		elif platform.system() == "Linux":
			startInstaller_Linux()
		elif platform.system() == "Darwin":
			startInstaller_Mac()

	except Exception,e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		QMessageBox.warning(QWidget(), "Prism Installation", "Errors occurred.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno))


	sys.exit()
	qapp.exec_()