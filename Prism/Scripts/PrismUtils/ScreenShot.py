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

import sys, traceback, time
from functools import wraps


class ScreenShot(QDialog):
	def __init__(self, core):
		super(ScreenShot, self).__init__()
		self.core = core
		self.core.parentWindow(self)

		self.imgmap = None
		self.origin = None

		desktop = QApplication.desktop()
		uRect = QRect()
		for i in range(desktop.screenCount()):
			uRect = uRect.united(desktop.screenGeometry(i))

		width, height = uRect.width(), uRect.height()
		self.setAttribute(Qt.WA_TranslucentBackground)
		self.setCursor(Qt.CrossCursor)
		self.setGeometry(0, 0, width, height)

		self.setWindowFlags(
				  Qt.FramelessWindowHint # hides the window controls
				| Qt.WindowStaysOnTopHint # forces window to top... maybe
				| Qt.SplashScreen # this one hides it from the task bar!
				)

		self.rubberband = QRubberBand(QRubberBand.Rectangle, self)
		self.rubberband.setWindowOpacity(0)

		self.setMouseTracking(True)


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			exc_info = sys.exc_info()
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - Screenshot %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def mousePressEvent(self, event):
		self.origin = event.pos()
		self.rubberband.setGeometry(QRect(self.origin, QSize()))
		QWidget.mousePressEvent(self, event)


	@err_decorator
	def mouseMoveEvent(self, event):
		if self.origin is not None:
			rect = QRect(self.origin, event.pos()).normalized()
			self.rubberband.setGeometry(rect)

		self.repaint()
		QWidget.mouseMoveEvent(self, event)


	@err_decorator
	def paintEvent(self, event):
		painter = QPainter(self)

		painter.setBrush(QColor(0, 0, 0, 100))
		painter.setPen(Qt.NoPen)
		painter.drawRect(event.rect())

		if self.origin is not None:
			rect = QRect(self.origin, QCursor.pos())
			painter.setCompositionMode(QPainter.CompositionMode_Clear)
			painter.drawRect(rect)
			painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

			pen = QPen(QColor(200, 150, 0, 255), 1)
			painter.setPen(pen)
			painter.drawLine(rect.left(), rect.top(), rect.right(), rect.top())
			painter.drawLine(rect.left(), rect.top(), rect.left(), rect.bottom())
			painter.drawLine(rect.right(), rect.top(), rect.right(), rect.bottom())
			painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())

		QWidget.paintEvent(self, event)


	@err_decorator
	def mouseReleaseEvent(self, event):
		if self.origin is not None:
			self.rubberband.hide()
			self.hide()
			rect = self.rubberband.geometry()
			desktop = QApplication.desktop()
			if hasattr(QApplication, "primaryScreen"):
				screen = QApplication.primaryScreen()
			else:
				screen = QPixmap

			winID = desktop.winId()
			if sys.version[0] == "2":
				try:
					winID = long(winID)
				except:
					pass

			self.imgmap = screen.grabWindow(winID, rect.x(), rect.y(), rect.width(), rect.height())
			self.close()
		QWidget.mouseReleaseEvent(self, event)


def grabScreenArea(core):
	ss = ScreenShot(core)
	ss.exec_()
	return ss.imgmap