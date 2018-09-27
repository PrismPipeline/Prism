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

import sys, os

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
		self.e_comment.textEdited.connect(self.validate)


	def enterEvent(self, event):
		QApplication.restoreOverrideCursor()


	def validate(self, origText):
		text = self.core.validateStr(origText)

		if len(text) != len(origText):
			cpos = self.e_comment.cursorPosition()
			self.e_comment.setText(text)
			self.e_comment.setCursorPosition(cpos-1)