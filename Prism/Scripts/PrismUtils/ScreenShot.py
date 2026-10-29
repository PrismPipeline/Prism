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


from __future__ import annotations

import os
import sys
import logging
from typing import Optional, Any

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class ScreenShotOverlay(QWidget):
    """A transparent selection overlay constrained to one physical screen."""

    def __init__(self, screenshot: "ScreenShot", screen: QScreen) -> None:
        super(ScreenShotOverlay, self).__init__()
        self.screenshot = screenshot
        self.screen = screen

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.setGeometry(screen.geometry())
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen
        )
        self.setMouseTracking(True)

    def mousePressEvent(self, event: Any) -> None:
        self.screenshot.beginSelection(self.mapToGlobal(event.pos()))

    def mouseMoveEvent(self, event: Any) -> None:
        if self.screenshot.origin is not None:
            self.screenshot.updateSelection(self.mapToGlobal(event.pos()))

    def mouseReleaseEvent(self, event: Any) -> None:
        if self.screenshot.origin is not None:
            self.screenshot.captureSelection(self.mapToGlobal(event.pos()))

    def keyPressEvent(self, event: Any) -> None:
        if event.key() == Qt.Key_Escape:
            self.screenshot.close()
        else:
            QWidget.keyPressEvent(self, event)

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setBrush(QColor(0, 0, 0, 100))
        painter.setPen(Qt.NoPen)
        painter.drawRect(event.rect())

        if self.screenshot.selection is not None:
            rect = QRect(
                self.mapFromGlobal(self.screenshot.selection.topLeft()),
                self.mapFromGlobal(self.screenshot.selection.bottomRight()),
            ).normalized()
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.drawRect(rect)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor(200, 150, 0, 255), 1))
            painter.drawRect(rect)


class ScreenShot(QDialog):
    """Provides screen capture functionality for Prism.
    
    This class creates one transparent overlay window per screen, allowing
    users to select a rectangular area without mixed-DPI geometry errors.
    Used for capturing project previews, asset thumbnails, and screenshots.
    
    Attributes:
        core: PrismCore instance
        imgmap: Captured image pixmap
        origin (QPoint): Global start point of the selection rectangle
        selection (QRect): Global selection rectangle
        overlays (list[ScreenShotOverlay]): Per-screen overlay windows
    """

    def __init__(self, core: Any) -> None:
        """Initialize ScreenShot capture dialog.
        
        Args:
            core: PrismCore instance
        """
        super(ScreenShot, self).__init__()
        self.core = core

        self.imgmap = None
        self.origin = None

        self.selection = None
        self.eventLoop = None
        self.overlays = [
            ScreenShotOverlay(self, screen) for screen in QApplication.screens()
        ]

    @err_catcher(name=__name__)
    def beginSelection(self, position: QPoint) -> None:
        self.origin = position
        self.selection = QRect(position, QSize())

    @err_catcher(name=__name__)
    def updateSelection(self, position: QPoint) -> None:
        self.selection = QRect(self.origin, position).normalized()
        for overlay in self.overlays:
            overlay.update()

    @err_catcher(name=__name__)
    def captureSelection(self, position: QPoint) -> None:
        """Capture the selection, rejecting failed or partial screen captures."""
        self.updateSelection(position)
        if self.selection is not None:
            for overlay in self.overlays:
                overlay.hide()

            selection = self.selection
            self.imgmap = QPixmap(selection.size())
            self.imgmap.fill(Qt.transparent)

            painter = QPainter()
            captureSucceeded = False
            try:
                if not self.imgmap.isNull() and painter.begin(self.imgmap):
                    capturedScreen = False
                    for screen in QApplication.screens():
                        screen_rect = screen.geometry()
                        capture_rect = selection.intersected(screen_rect)
                        if capture_rect.isEmpty():
                            continue

                        pixmap = screen.grabWindow(
                            0,
                            capture_rect.x() - screen_rect.x(),
                            capture_rect.y() - screen_rect.y(),
                            capture_rect.width(),
                            capture_rect.height(),
                        )
                        if pixmap.isNull():
                            break

                        painter.drawPixmap(capture_rect.topLeft() - selection.topLeft(), pixmap)
                        capturedScreen = True
                    else:
                        captureSucceeded = capturedScreen
            finally:
                if painter.isActive():
                    painter.end()
                if not captureSucceeded:
                    self.imgmap = None
                self.close()

            if not captureSucceeded:
                msg = "Unable to capture the selected screen area."
                if sys.platform.startswith("linux"):
                    msg += (
                        "\n\nWayland or XWayland may restrict desktop capture."
                        "\nUse your desktop's screenshot tool, then import or paste "
                        "the image into Prism."
                        "\nIf available, you can also try Prism in an X11/Xorg session."
                    )
                if os.getenv("PRISM_SHOW_SCREENSHOT_WARNING", "1") == "1":
                    self.core.popup(msg, title="Screen capture failed")
                else:
                    logger.debug(msg)

    def exec_(self) -> int:
        self.eventLoop = QEventLoop()
        for overlay in self.overlays:
            overlay.show()
        return self.eventLoop.exec_()

    def close(self) -> bool:
        for overlay in self.overlays:
            overlay.close()
        if self.eventLoop is not None:
            self.eventLoop.quit()
        return super(ScreenShot, self).close()


def grabScreenArea(core: Any) -> Optional[QPixmap]:
    """Show screenshot tool to capture screen area.
    
    Args:
        core: Prism core instance
        
    Returns:
        Captured screen area as QPixmap or None if canceled or capture failed
    """
    ss = ScreenShot(core)
    ss.exec_()
    return ss.imgmap
