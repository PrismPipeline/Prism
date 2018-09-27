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

import sys, os, traceback, time
from functools import wraps

sys.path.append(os.path.join(os.path.dirname(__file__), "UserInterfaces"))

if psVersion == 1:
	import CreateItem_ui
else:
	import CreateItem_ui_ps2 as CreateItem_ui

if sys.version[0] == "3":
	from configparser import ConfigParser
	pVersion = 3
else:
	from ConfigParser import ConfigParser
	pVersion = 2


class CreateItem(QDialog, CreateItem_ui.Ui_dlg_CreateItem):
	def __init__(self, startText = "", showTasks=False, taskType="", core=None, getStep=False, showType=False ):
		QDialog.__init__(self)
		self.setupUi(self)
		self.core = core
		self.getStep = getStep
		self.taskType = taskType

		self.e_item.setText(startText)

		if startText == "":
			self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

		self.isTaskName = showTasks

		if not showTasks:
			self.b_showTasks.setHidden(True)
		else:
			self.b_showTasks.setMinimumWidth(30)
			self.b_showTasks.setMinimumHeight(0)
			self.b_showTasks.setMaximumHeight(500)
			self.getTasks()

		if getStep:
			self.setWindowTitle("Create Step")
			self.l_item.setText("Abbreviation:")
			self.l_stepName = QLabel("Step Name:")
			self.e_stepName = QLineEdit()
			self.w_item.layout().addWidget(self.l_stepName)
			self.w_item.layout().addWidget(self.e_stepName)
			self.e_item.setMaximumWidth(100)
			self.resize(500*self.core.uiScaleFactor, self.height())
			self.setTabOrder(self.e_item, self.e_stepName)

		if showType:
			for i in self.core.prjManagers.values():
				i.createAsset_open(self)
		else:
			self.w_type.setVisible(False)
			self.w_prjManager.setVisible(False)
	
		self.resize(self.width(), 10)

		self.connectEvents()


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - CreateItem %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def connectEvents(self):
		self.buttonBox.accepted.connect(self.returnName)
		self.b_showTasks.clicked.connect(self.showTasks)
		if self.getStep:
			self.e_item.textEdited.connect(lambda x: self.enableOkStep(x, self.e_item))
			self.e_stepName.textEdited.connect(lambda x: self.enableOkStep(x, self.e_stepName))
		else:
			self.e_item.textEdited.connect(self.enableOk)
		self.rb_asset.toggled.connect(self.typeChanged)


	@err_decorator
	def getTasks(self):
		self.taskList = self.core.getTaskNames(self.taskType)

		if len(self.taskList) == 0:
			self.b_showTasks.setHidden(True)
		else:
			if "_ShotCam" in self.taskList:
				self.taskList.remove("_ShotCam")


	@err_decorator
	def showTasks(self):
		tmenu = QMenu()

		for i in self.taskList:
			tAct = QAction(i, self)
			tAct.triggered.connect(lambda x=None, t=i: self.taskClicked(t))
			tmenu.addAction(tAct)

		self.core.plugin.setRCStyle(self, tmenu)

		tmenu.exec_(QCursor.pos())


	@err_decorator
	def taskClicked(self, task):
		self.e_item.setText(task)
		self.enableOk(task)


	@err_decorator
	def typeChanged(self, state):
		for i in self.core.prjManagers.values():
			i.createAsset_typeChanged(self, state)


	@err_decorator
	def enableOk(self, origText):
		if self.isTaskName:
			if self.taskType == "Export":
				text = self.core.validateStr(origText,allowChars=["_"], denyChars=["-"])
			else:
				text = self.core.validateStr(origText,allowChars=["_"])
		else:
			text = self.core.validateStr(origText)

		if len(text) != len(origText):
			cpos = self.e_item.cursorPosition()
			self.e_item.setText(text)
			self.e_item.setCursorPosition(cpos-1)

		if text != "":
			self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
		else:
			self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)


	@err_decorator
	def enableOkStep(self, origText, uiField):
		text = self.core.validateStr(origText)

		if len(text) != len(origText):
			cpos = uiField.cursorPosition()
			uiField.setText(text)
			uiField.setCursorPosition(cpos-1)

		if self.e_item.text() != "" and self.e_stepName.text() != "":
			self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
		else:
			self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)


	@err_decorator
	def returnName(self):
		self.itemName = self.e_item.text()