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
# Copyright (C) 2016-2023 Richard Frangenberg
# Copyright (C) 2023 Prism Software GmbH
#
# Licensed under GNU LGPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


import sys

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


class ScreenShot(QDialog):
    def __init__(self, core):
        super(ScreenShot, self).__init__()
        self.core = core

        self.imgmap = None
        self.origin = None

        uRect = QRect()
        for i in range(len(QApplication.screens())):
            uRect = uRect.united(QApplication.screens()[i].geometry())

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.setGeometry(uRect)

        self.setWindowFlags(
            Qt.FramelessWindowHint  # hides the window controls
            | Qt.WindowStaysOnTopHint  # forces window to top... maybe
            | Qt.SplashScreen  # this one hides it from the task bar!
        )

        self.rubberband = QRubberBand(QRubberBand.Rectangle, self)
        self.rubberband.setWindowOpacity(0)

        self.setMouseTracking(True)

    @err_catcher(name=__name__)
    def mousePressEvent(self, event):
        self.origin = event.pos()
        self.rubberband.setGeometry(QRect(self.origin, QSize()))
        QWidget.mousePressEvent(self, event)

    @err_catcher(name=__name__)
    def mouseMoveEvent(self, event):
        if self.origin is not None:
            rect = QRect(self.origin, event.pos()).normalized()
            self.rubberband.setGeometry(rect)

        self.repaint()
        QWidget.mouseMoveEvent(self, event)

    @err_catcher(name=__name__)
    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setBrush(QColor(0, 0, 0, 100))
        painter.setPen(Qt.NoPen)
        painter.drawRect(event.rect())

        if self.origin is not None:
            rect = QRect(self.origin, self.mapFromGlobal(QCursor.pos()))
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

    @err_catcher(name=__name__)
    def mouseReleaseEvent(self, event):
        if self.origin is not None:
            self.rubberband.hide()
            self.hide()
            rect = self.rubberband.geometry()
            if hasattr(QApplication, "primaryScreen"):
                screen = QApplication.primaryScreen()
            else:
                screen = QPixmap

            desktop = QApplication.desktop()
            winID = desktop.winId()
            if sys.version[0] == "2":
                try:
                    winID = long(winID)
                except:
                    pass

            pos = self.mapToGlobal(rect.topLeft())
            try:
                self.imgmap = screen.grabWindow(
                    winID, pos.x(), pos.y(), rect.width(), rect.height()
                )
            except:
                self.imgmap = screen.grabWindow(
                    int(winID), pos.x(), pos.y(), rect.width(), rect.height()
                )
            self.close()

        QWidget.mouseReleaseEvent(self, event)


def grabScreenArea(core):
    ss = ScreenShot(core)
    ss.exec_()
    return ss.imgmap
