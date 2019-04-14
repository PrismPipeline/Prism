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

import sys, os, traceback, platform, time
from functools import wraps

if psVersion == 1:
	from UserInterfacesPrism import SaveComment_ui
else:
	from UserInterfacesPrism import SaveComment_ui_ps2 as SaveComment_ui


class SaveComment(QDialog, SaveComment_ui.Ui_dlg_SaveComment):
	def __init__(self, core):
		QDialog.__init__(self)
		self.setupUi(self)

		self.core = core
		self.core.parentWindow(self)
		self.previewDefined = False
		self.e_comment.textEdited.connect(self.validate)
		self.b_changePreview.clicked.connect(self.grabArea)
		self.setEmptyPreview()
		self.core.callback(name="onSaveExtendedOpen", types=["curApp", "custom"], args=[self])
		self.resize(0,self.geometry().size().height())


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			exc_info = sys.exc_info()
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - ProjectBrowser %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	def enterEvent(self, event):
		QApplication.restoreOverrideCursor()


	@err_decorator
	def validate(self, origText):
		text = self.core.validateStr(origText)

		if len(text) != len(origText):
			cpos = self.e_comment.cursorPosition()
			self.e_comment.setText(text)
			self.e_comment.setCursorPosition(cpos-1)


	@err_decorator
	def setEmptyPreview(self):
		imgFile = os.path.join(self.core.projectPath, "00_Pipeline", "Fallbacks", "noFileBig.jpg")
		pmap = self.getImgPMap(imgFile)
		pmap = pmap.scaled(QSize(500, 281))
		self.l_preview.setPixmap(pmap)


	@err_decorator
	def getImgPMap(self, path):
		if platform.system() == "Windows":
			return QPixmap(path)
		else:
			try:
				im = Image.open(path)
				im = im.convert("RGBA")
				r,g,b,a = im.split()
				im = Image.merge("RGBA", (b,g,r,a))
				data = im.tobytes("raw", "RGBA")

				qimg = QImage(data, im.size[0], im.size[1], QImage.Format_ARGB32)

				return QPixmap(qimg)
			except:
				return QPixmap(path)


	@err_decorator
	def grabArea(self):
		self.setWindowOpacity(0)
		from PrismUtils import ScreenShot
		previewImg = ScreenShot.grabScreenArea(self.core)
		self.setWindowOpacity(1)

		if previewImg is not None:
			self.l_preview.setPixmap(previewImg.scaled(self.l_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
			self.previewDefined = True


	@err_decorator
	def getDetails(self):
		details = {"description":self.e_description.toPlainText(), "username":self.core.getConfig("globals", "UserName")}
		self.core.callback(name="onGetSaveExtendedDetails", types=["curApp", "custom"], args=[self, details])
		return details