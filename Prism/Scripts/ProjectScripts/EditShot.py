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

if psVersion == 1:
	import EditShot_ui
else:
	import EditShot_ui_ps2 as EditShot_ui

import sys, os, traceback, time, platform
from functools import wraps


if sys.version[0] == "3":
	from configparser import ConfigParser
	pVersion = 3
else:
	from ConfigParser import ConfigParser
	pVersion = 2


class EditShot(QDialog, EditShot_ui.Ui_dlg_EditShot):
	def __init__(self, core, shotName, sequences):
		QDialog.__init__(self)
		self.setupUi(self)

		self.core = core
		self.shotName = shotName
		self.sequences = sequences

		if len(self.sequences) == 0:
			self.b_showSeq.setVisible(False)

		self.b_deleteShot.setVisible(False)

		self.oiioLoaded = False
		self.wandLoaded = False

		self.core.appPlugin.editShot_startup(self)
		getattr(self.core.appPlugin, "editShot_loadLibs", lambda x: self.loadLibs())(self)

		self.imgPath = ""

		self.loadData()
		self.connectEvents()


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - EditShot %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def connectEvents(self):
		self.b_showSeq.clicked.connect(self.showSequences)
		self.b_changePreview.clicked.connect(self.browse)
		self.buttonBox.clicked.connect(self.buttonboxClicked)
		self.buttonBox.accepted.connect(self.saveInfo)
		self.e_shotName.textEdited.connect(lambda x: self.validate(x, self.e_shotName))
		self.e_sequence.textEdited.connect(lambda x: self.validate(x, self.e_sequence))
		self.b_deleteShot.clicked.connect(self.deleteShot)


	@err_decorator
	def loadOiio(self):
		try:
			global oiio
			if platform.system() == "Windows":
				from oiio1618 import OpenImageIO as oiio
			elif platform.system() in ["Linux", "Darwin"]:
				import OpenImageIO as oiio

			self.oiioLoaded = True
		except:
			pass


	@err_decorator
	def loadLibs(self):
		if not self.oiioLoaded:
			global numpy, wand
			try:
				import numpy
				import wand, wand.image
				self.wandLoaded = True
			except:
				pass


	@err_decorator
	def showSequences(self):
		smenu = QMenu()

		for i in self.sequences:
			sAct = QAction(i, self)
			sAct.triggered.connect(lambda x=None, t=i: self.seqClicked(t))
			smenu.addAction(sAct)

		self.core.appPlugin.setRCStyle(self, smenu)

		smenu.exec_(QCursor.pos())


	@err_decorator
	def seqClicked(self, seq):
		self.e_sequence.setText(seq)


	@err_decorator
	def browse(self):
		formats = "Image File (*.jpg *.png *.exr)"

		imgPath = QFileDialog.getOpenFileName(self, "Select preview-image", self.imgPath, formats)[0]

		if imgPath != "":
			if os.path.splitext(imgPath)[1] == ".exr":
				qimg = QImage(self.core.pb.shotPrvXres, self.core.pb.shotPrvYres, QImage.Format_RGB16)

				if self.oiioLoaded:
					imgSrc = oiio.ImageBuf(str(imgPath))
					rgbImgSrc = oiio.ImageBuf()
					oiio.ImageBufAlgo.channels(rgbImgSrc, imgSrc, (0,1,2))
					imgWidth = rgbImgSrc.spec().full_width
					imgHeight = rgbImgSrc.spec().full_height
					xOffset = 0
					yOffset = 0
					if (imgWidth/float(imgHeight)) > 1.7778:
						newImgWidth = self.core.pb.shotPrvXres
						newImgHeight = self.core.pb.shotPrvXres/float(imgWidth)*imgHeight
					else:
						newImgHeight = self.core.pb.shotPrvYres
						newImgWidth = self.core.pb.shotPrvYres/float(imgHeight)*imgWidth
					imgDst = oiio.ImageBuf(oiio.ImageSpec(int(newImgWidth),int(newImgHeight),3, oiio.UINT8))
					oiio.ImageBufAlgo.resample(imgDst, rgbImgSrc)
					sRGBimg = oiio.ImageBuf()
					oiio.ImageBufAlgo.pow(sRGBimg, imgDst, (1.0/2.2, 1.0/2.2, 1.0/2.2))
					bckImg = oiio.ImageBuf(oiio.ImageSpec(int(newImgWidth), int(newImgHeight), 3, oiio.UINT8))
					oiio.ImageBufAlgo.fill (bckImg, (0.5,0.5,0.5))
					oiio.ImageBufAlgo.paste(bckImg, xOffset,yOffset,0,0, sRGBimg)
					qimg = QImage(int(newImgWidth), int(newImgHeight), QImage.Format_RGB16)
					for i in range(int(newImgWidth)):
						for k in range(int(newImgHeight)):
							rgb = qRgb(bckImg.getpixel(i,k)[0]*255, bckImg.getpixel(i,k)[1]*255, bckImg.getpixel(i,k)[2]*255)
							qimg.setPixel(i,k,rgb)					

					pmsmall = QPixmap.fromImage(qimg)
				elif self.wandLoaded:
					with wand.image.Image(filename=imgPath) as img :
						imgWidth, imgHeight = [img.width, img.height]
						img.depth = 8
						imgArr = numpy.fromstring(img.make_blob('RGB'), dtype='uint{}'.format(img.depth)).reshape(imgHeight, imgWidth, 3)

					qimg = QImage(imgArr,imgWidth, imgHeight, QImage.Format_RGB888)
					pm = QPixmap.fromImage(qimg)
					if (pm.width()/float(pm.height())) > 1.7778:
						pmsmall = pm.scaledToWidth(self.core.pb.shotPrvXres)
					else:
						pmsmall = pm.scaledToHeight(self.core.pb.shotPrvYres)
				else:
					QMessageBox.critical(self.core.messageParent, "Error", "No image loader available. Unable to read the file.")
					return
			else:
				pm = self.core.pb.getImgPMap(imgPath)
				if pm.width() == 0:
					warnStr = "Cannot read image: %s" % imgPath
					msg = QMessageBox(QMessageBox.Warning, "Warning", warnStr, QMessageBox.Ok, parent=self.core.messageParent)
					msg.setFocus()
					msg.exec_()
					return

				if (pm.width()/float(pm.height())) > 1.7778:
					pmsmall = pm.scaledToWidth(self.core.pb.shotPrvXres)
				else:
					pmsmall = pm.scaledToHeight(self.core.pb.shotPrvYres)

			self.pmap = pmsmall

			self.l_shotPreview.setMinimumSize(self.pmap.width(), self.pmap.height())
			self.l_shotPreview.setPixmap(self.pmap)


	@err_decorator
	def validate(self, origText, editField):
		text = self.core.validateStr(origText)

		if editField == self.e_sequence:
			text = text.replace("-","")

		if len(text) != len(origText):
			cpos = editField.cursorPosition()
			editField.setText(text)
			editField.setCursorPosition(cpos-1)


	@err_decorator
	def deleteShot(self):
		msgText = "Are you sure you want to delete shot \"%s\"?\n\nThis will delete all scenefiles and renderings, which exist in this shot." % (self.shotName)
		if psVersion == 1:
			flags = QMessageBox.StandardButton.Yes
			flags |= QMessageBox.StandardButton.No
			result = QMessageBox.question(self.core.messageParent, "Warning", msgText, flags)
		else:
			result = QMessageBox.question(self.core.messageParent, "Warning", msgText)

		if str(result).endswith(".Yes"):
			self.core.createCmd(["deleteShot", self.shotName])
			self.accept()


	@err_decorator
	def buttonboxClicked(self, button):
		if button.text() == "Create":
			result = self.saveInfo()
			if result:
				self.core.pb.createShot(self.shotName)
			self.shotName = None
		elif button.text() == "Create and close":
			result = self.saveInfo()
			if result:
				self.core.pb.createShot(self.shotName)
				self.accept()


	@err_decorator
	def saveInfo(self):
		if self.e_shotName.text() == "":
			warnStr = "Invalid shotname"
			msg = QMessageBox(QMessageBox.Warning, "Warning", warnStr, QMessageBox.Ok, parent=self.core.messageParent)
			msg.setFocus()
			msg.exec_()
			return False

		shotFile = os.path.join(os.path.dirname(self.core.prismIni), "Shotinfo", "shotInfo.ini")

		if not os.path.exists(os.path.dirname(shotFile)):
			os.makedirs(os.path.dirname(shotFile))

		if not os.path.exists(shotFile):
			open(shotFile, 'a').close()

		if self.e_sequence.text() == "":
			newSName = self.e_shotName.text()
		else:
			newSName = "%s-%s" %(self.e_sequence.text(), self.e_shotName.text())

		if self.shotName is not None and newSName != self.shotName:
			msgText = "Are you sure you want to rename this shot from \"%s\" to \"%s\"?\n\nThis will rename all files in the subfolders of the shot, which may cause errors, if these files are referenced somewhere else." % (self.shotName, newSName)
			if psVersion == 1:
				flags = QMessageBox.StandardButton.Yes
				flags |= QMessageBox.StandardButton.No
				result = QMessageBox.question(self.core.messageParent, "Warning", msgText, flags)
			else:
				result = QMessageBox.question(self.core.messageParent, "Warning", msgText)

			if str(result).endswith(".Yes"):
				self.core.createCmd(["renameShot", self.shotName, newSName])
				self.core.checkCommands()

		self.shotName = newSName

		saveRange = True
		sconfig = ConfigParser()
		while True:
			try:
				sconfig.read(shotFile)
				break
			except:
				warnStr = "Could not read the configuration file for the frameranges:\n%s\n\nYou can try to fix this problem manually and then press retry.\nYou can also overwrite this file, which means that the frameranges for all existing shots will be lost.\nYou can also continue without saving the framerange for the current shot." % shotFile
				msg = QMessageBox(QMessageBox.Warning, "Warning", warnStr, QMessageBox.NoButton, parent=self.core.messageParent)
				msg.addButton("Retry", QMessageBox.YesRole)
				msg.addButton("Overwrite", QMessageBox.YesRole)
				msg.addButton("Continue", QMessageBox.YesRole)
				msg.setFocus()
				action = msg.exec_()

				if action == 0:
					pass
				elif action == 1:
					break
				elif action == 2:
					saveRange = False
					break

		if saveRange:
			if not sconfig.has_section("shotRanges"):
				sconfig.add_section("shotRanges")

			sconfig.set("shotRanges", self.shotName, str([self.sp_startFrame.value(), self.sp_endFrame.value()]))

			with open(shotFile, 'w') as inifile:
				sconfig.write(inifile)

		if hasattr(self, "pmap"):
			prvPath = os.path.join(os.path.dirname(self.core.prismIni), "Shotinfo", "%s_preview.jpg" % self.shotName)
			self.core.pb.savePMap(self.pmap, prvPath)

		for i in self.core.prjManagers.values():
			i.editShot_closed(self, self.shotName)

		return True


	@err_decorator
	def loadData(self):
		if self.shotName is not None:
			if "-" in self.shotName:
				sname = self.shotName.split("-",1)
				self.e_sequence.setText(sname[0])
				self.e_shotName.setText(sname[1])
			else:
				self.e_shotName.setText(self.shotName)

			shotFile = os.path.join(os.path.dirname(self.core.prismIni), "Shotinfo", "shotInfo.ini")

			if os.path.exists(shotFile):
				sconfig = ConfigParser()
				sconfig.read(shotFile)

				if sconfig.has_option("shotRanges", self.shotName):
					shotRange = eval(sconfig.get("shotRanges", self.shotName))
					if type(shotRange) == list and len(shotRange) == 2:
						self.sp_startFrame.setValue(shotRange[0])
						self.sp_endFrame.setValue(shotRange[1])


			imgPath = os.path.join(os.path.dirname(self.core.prismIni), "Shotinfo", "%s_preview.jpg" % self.shotName)
		else:
			self.b_deleteShot.setVisible(False)
			self.buttonBox.removeButton(self.buttonBox.buttons()[0])
			self.buttonBox.addButton("Create and close", QDialogButtonBox.AcceptRole)
			self.buttonBox.addButton("Create", QDialogButtonBox.ApplyRole)
			self.buttonBox.setStyleSheet("* { button-layout: 2}")

		if self.shotName is not None and os.path.exists(imgPath):
			pm = self.core.pb.getImgPMap(imgPath)
			if (pm.width()/float(pm.height())) > 1.7778:
				pmap = pm.scaledToWidth(self.core.pb.shotPrvXres)
			else:
				pmap = pm.scaledToHeight(self.core.pb.shotPrvYres)
		else:
			imgFile = os.path.join(self.core.projectPath, "00_Pipeline", "Fallbacks", "noFileSmall.jpg")
			pmap = self.core.pb.getImgPMap(imgFile)

		self.l_shotPreview.setMinimumSize(pmap.width(), pmap.height())
		self.l_shotPreview.setPixmap(pmap)

		for i in self.core.prjManagers.values():
			i.editShot_open(self, self.shotName)