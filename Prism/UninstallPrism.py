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



import os, sys, shutil, platform
from ConfigParser import ConfigParser

if platform.system() == "Windows":
	from win32com.shell import shellcon
	import win32com.shell.shell as shell
	import win32con, win32event, win32process

try:
	from PySide2.QtCore import *
	from PySide2.QtGui import *
	from PySide2.QtWidgets import *
	psVersion = 2
except:
	from PySide.QtCore import *
	from PySide.QtGui import *
	psVersion = 1


def removePrismFiles(origin, prismPath):
	try:
		try:
			import psutil
		except:
			pass
		else:
			PROCNAME = 'PrismTray.exe'
			for proc in psutil.process_iter():
				if proc.name() == PROCNAME:
					p = psutil.Process(proc.pid)

					try:
						if not 'SYSTEM' in p.username():
							try:
								proc.kill()
								print "closed Prism tray"
							except:
								pass
					except:
						pass


		if platform.system() == "Windows":
			smTray = os.path.join(os.environ["appdata"], "Microsoft", "Windows", "Start Menu", "Programs", "Prism", "PrismTray.lnk")
			smBrowser = os.path.join(os.environ["appdata"], "Microsoft", "Windows", "Start Menu", "Programs", "Prism", "PrismProjectBrowser.lnk")
			smSettings = os.path.join(os.environ["appdata"], "Microsoft", "Windows", "Start Menu", "Programs", "Prism", "PrismSettings.lnk")
			suTray = os.path.join(os.environ["appdata"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup", "PrismTray.lnk")

			pFiles = [smTray, smBrowser, smSettings, suTray]
		elif platform.system() == "Linux":
			trayStartup = "/etc/xdg/autostart/PrismTray.desktop"
			trayStartMenu = "/usr/share/applications/PrismTray.desktop"
			pbStartMenu = "/usr/share/applications/PrismProjectBrowser.desktop"
			settingsStartMenu = "/usr/share/applications/PrismSettings.desktop"
			pMenuTarget = "/etc/xdg/menus/applications-merged/Prism.menu"
			userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
			desktopPath = "/home/%s/Desktop/PrismProjectBrowser.desktop" % userName
		
			pFiles = [trayStartup, trayStartMenu, pbStartMenu, settingsStartMenu, pMenuTarget, desktopPath]

		elif platform.system() == "Darwin":
			userName = os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']
			trayStartup = "/Users/%s/Library/LaunchAgents/com.PrismTray.plist" % userName
			desktopPath = "/Users/%s/Desktop/Prism Project Browser" % userName
			pFiles = [trayStartup, desktopPath]

		for i in pFiles:
			if os.path.exists(i):
				try:
					os.remove(i)
				except:
					pass

		if platform.system() == "Windows":
			smFolder = os.path.dirname(smTray)
			try:
				shutil.rmtree(smFolder)
			except:
				pass

		if os.path.exists(prismPath):
			print "remove old files.."
			
			while True:
				try:
					shutil.rmtree(prismPath)
					break
				except WindowsError:
					msg = QMessageBox(QMessageBox.Warning, "Remove old files", "Could not remove Prism files.\n\nMake sure all dependent programms like Max, Maya, Houdini, Blender, Nuke, TrayIcon and eventually the windows explorer are closed.", QMessageBox.Cancel)
					msg.addButton("Retry", QMessageBox.YesRole)
					action = msg.exec_()

					if action != 0:
						print "Canceled Prism files removal"
						return False

		return True

	except Exception as e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		QMessageBox.warning(QWidget(), "Prism Installation", "Error occurred during Prism files removal:\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno))
		return False


def uninstallPrism(origin, user=""):
	msg = QMessageBox(QMessageBox.Question, "Prism Pipeline", "Are you sure you want to uninstall Prism?\n\nThis will delete all Prism files and Prism integrations from your PC. Your projects will remain unaffected.", QMessageBox.Cancel)
	msg.addButton("Continue", QMessageBox.YesRole)
	msg.setFocus()
	action = msg.exec_()

	if action != 0:
		return False

	if platform.system() == "Windows":
		prismPath = os.path.join(os.path.dirname(os.environ["Userprofile"]), user, "AppData", "Local", "Prism")
	elif platform.system() == "Linux":
		prismPath = os.path.join("/usr", "local", "Prism")
	elif platform.system() == "Darwin":
		prismPath = "/Applications/Prism"

	locFile = os.path.join(prismPath, "installLocations.ini")

	print "uninstalling..."

	result = {}

	if os.path.exists(locFile):
		locConfig = ConfigParser()

		try:
			locConfig.read(locFile)
		except:
			pass

		pApps = locConfig.sections()

		for i in pApps:
			if not i in origin.prismPlugins:
				continue

			appPaths = locConfig.items(i)

			for k in appPaths:
				result["%s integration" % i] = origin.prismPlugins[i].removeIntegration(k[1])

	result["Prism Files"] = removePrismFiles(origin, prismPath)

	return result