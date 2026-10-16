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
####################################################
#
#
#   XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX                               #   TODO
#
#
####################################################


import os
import subprocess
import logging
from collections import OrderedDict
from functools import partial
from html import escape
from typing import Any, Optional, TYPE_CHECKING


import numpy as np

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


from ProjectScripts.PreviewPlayer_GL_Display import GLVideoDisplay
import ProjectScripts.PreviewPlayer_GL_Utils as Utils
from ProjectScripts.PreviewPlayer_GL_Modules import (PlayerControls,
                                                     PreviewMediaData,
                                                     FrameCacheManager,
                                                     FrameCacheRescanWorker,
                                                     OcioPresetsEditor,
                                                     PresetsCollection,
                                                     PlayerConfigPopup,
                                                     PlaySettingsMenu,
                                                     FxControlsDialog,
                                                     FxControlsData)


from PrismUtils.Decorators import err_catcher
logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from PrismCore import PrismCore, Worker
    from ProjectScripts.ProjectBrowser import ProjectBrowser
    from ProjectScripts.MediaBrowser import MediaBrowser, MediaVersionPlayer



class PreviewPlayer_GL(QWidget):
    '''A GL based Preview Player to display many types of Media Files. This is a replacement for the original MediaPlayer in Prism2.

    - OpenColorIO (OCIO) for color management.
    - Automatic media decode and caching of frames for faster playback.
    - Simple FX image adjustments (exposure, contrast, saturation, etc.).
    - Multiple playback modes and speeds

    Signals:
    ------
    - frameReady (Signal): Signal emitted when a new frame is ready for display.
        
    Args:
    ------
    - mediaVersionPlayer (MediaVersionPlayer): The Prism MediaVersionPlayer instance that this preview player is associated with.

    API:
    ------
    - updatePreview(): Updates the preview display with the latest frame.
    - compare(): Compares the selected media versions.
    '''

    frameReady = Signal(int, np.ndarray)

    def __init__(self, mediaVersionPlayer: 'MediaVersionPlayer'):
        super(PreviewPlayer_GL, self).__init__()

        self.initialized = False

        self.mediaVersionPlayer = mediaVersionPlayer
        self.mediaBrowser:MediaBrowser = mediaVersionPlayer.origin
        self.origin:MediaBrowser = mediaVersionPlayer.origin  # Needed for RCL Menu callback
        self.projectBrowser:ProjectBrowser = self.mediaBrowser.projectBrowser
        self.core:PrismCore = mediaVersionPlayer.core

        self.MediaData = PreviewMediaData()
        self.PreviewCache = FrameCacheManager(self.core, self, pWidth=400)
        self.FxData = FxControlsData()

        self.iconDir = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism")
        
        self.global_useOCIO = True  # Turns on OCIO usage (off disables OCIO globally)
        self.ocioEnabled = False    # Controls if OCIO is Enabled in the Display Window
        self.OcioModule = None

        self.externalMediaPlayers = None

        self.playerEnabled = True
        self.timeline = None

        self.defaultRezX = 300
        self.defaultRezY = 169

        self.playback_mode = "loop"
        self.playback_fps = 24
        self.playback_fps_mode = "auto"
        self.playback_fps_custom = 24
        self.playback_missingFrameMode = "last"
        self._playInterval = 1000.0 / float(self.playback_fps)

        self.fpsFrameCount = 0
        self.lastFPSUpdate = 0
        self.currentFrameNumber = 0
        self.currentFrameIdx = 0
        self.frameDisplay_mode = "frames"

        self.wasPlaying = False
        self.playingWasChecked = False

        self.cacheRescanEnabled = True
        self.uiRefreshIntervalMs = 200
        self.pendingCacheUpdateFrame = None
        self.uiRefreshCallbacks = OrderedDict()

        self._resumeAfterDrag = False
        self._previewDragActive = False

        self.previewLoadToken = 0
        self.previewLoadWorker = None
        self.pendingPreviewUpdate = False

        self.projectBrowserEventsConnected = False

        self.systemRam = Utils.getTotalRAM()

        self.updateExternalMediaPlayers()
        self.checkSystemOCIO()

        self.setupIcons()
        self.setupUi()
        self.connectEvents()
        self.setupTimers()

        if self.global_useOCIO:
            self.loadOcioPresets()

        self.loadPlayerSettings()

        if self.global_useOCIO:
            self.loadOcioCombo()

        self.resetImage()
        self.enableControls(False)

        self.core.registerCallback("onProjectBrowserShow", self.onProjectBrowserShow, plugin=self.mediaBrowser)
        self.core.registerCallback("onProjectBrowserClose", self.onProjectBrowserClose, plugin=self.mediaBrowser)
        self.core.registerCallback("onProjectBrowserRefreshUiTriggered", self.onProjectBrowserRefreshUiTriggered, plugin=self.mediaBrowser)
        self.core.registerCallback("onProjectChanged", self.onProjectChanged, plugin=self.mediaBrowser)
        self.core.registerCallback("onMediaBrowserOpen", self.onMediaBrowserOpen, plugin=self.mediaBrowser)


    @property
    def seq(self):
        '''(list) For backwards compatibility with Prism'''
        return self.MediaData.mediaFiles


    ###############################
    ########   CALLBACKS   ########

    @err_catcher(name=__name__)
    def updateExternalMediaPlayers(self):
        '''Updates the list of external media players based on the Prism version.'''

        #   For Prism 2.0.18+
        if hasattr(self.core.media, "getExternalMediaPlayers"):
            self.externalMediaPlayers = self.core.media.getExternalMediaPlayers()

        #   For Before Prism 2.0.18
        else:
            player = self.core.media.getExternalMediaPlayer()
            self.externalMediaPlayers = [player]

        logger.debug("Updated external Media Players")


    @err_catcher(name=__name__)
    def onProjectBrowserShow(self, projectBrowser: 'ProjectBrowser'):
        '''From Prism's Project Browser show event.
        
        Args:
            projectBrowser: The Project Browser instance that is being shown.
        '''

        #   Restart Cache as Needed
        if self.cacheEnabled and self.checkMediaTabActive():
            self.setCachePaused(False)

        #   Connect to Tab Changed Event if Not Already Connected
        if self.projectBrowser and not self.projectBrowserEventsConnected:
            self.projectBrowser.tbw_project.currentChanged.connect(self.onTabChanged)
            self.projectBrowserEventsConnected = True


    @err_catcher(name=__name__)
    def onProjectBrowserClose(self, projectBrowser: 'ProjectBrowser'):
        '''From Prism's Project Browser close event.

        - Stops any running cache worker.
        - Pauses playback.
        - Closes the FX window if it is open.
        - Saves the current player settings.
        
        Args:
            projectBrowser: The Project Browser instance that is closing.
        '''

        self.previewLoadToken += 1
        self.cancelPreviewLoadWorker()
        self.pendingPreviewUpdate = False

        #   Stop Running Cache Worker Threads
        if getattr(self, "PreviewCache", None):
            self.PreviewCache.stop()
            self.PreviewCache.threadpool.waitForDone(1000)

        #   Pause Timeline if Playing
        self.setTimelinePaused(True)

        #   Close FX Window if Open
        if getattr(self, "FxWindow", None):
            self.FxWindow.close()

        #   Save Current Player Settings
        self.savePlayerSettings()


    @err_catcher(name=__name__)
    def onProjectBrowserRefreshUiTriggered(self, projectBrowser: 'ProjectBrowser'):
        '''From Prism's Project Browser Refresh Button.

        Args:
            projectBrowser: The Project Browser instance that triggered the UI refresh.
        '''

        self.resetImage()


    @err_catcher(name=__name__)
    def onProjectChanged(self, projectBrowser: 'ProjectBrowser'):
        '''From Prism's Project Browser Project Changed event.

        Args:
            projectBrowser: The Project Browser instance that detected a project change.
        '''

        self.resetImage()


    @err_catcher(name=__name__)
    def onMediaBrowserOpen(self, mediaBrowser: 'MediaBrowser'):
        '''From Prism's Media Browser open event.

        Args:
            mediaBrowser: The Media Browser instance that was opened.
        '''

        self.initialized = True

        if self.pendingPreviewUpdate and self.checkMediaTabActive():
            self.pendingPreviewUpdate = False
            QTimer.singleShot(0, self.updatePreview)
            return

        if self.cacheEnabled and self.MediaData.mediaFiles:
            self.PreviewCache.start()
            self.PlayControls.updateCacheSlider()


    @err_catcher(name=__name__)
    def onTabChanged(self, index: int):
        '''Handles when the ProjectBrowser tab changes.

        Args:
            index: The index of the newly selected tab.
        '''

        self.setTimelinePaused(True)

        if self.checkMediaTabActive():
            self.setCachePaused(False)
            if self.initialized and self.pendingPreviewUpdate:
                self.pendingPreviewUpdate = False
                QTimer.singleShot(0, self.updatePreview)
        else:
            if self.previewLoadWorker and self.previewLoadWorker.isRunning():
                self.previewLoadToken += 1
                self.cancelPreviewLoadWorker()
                self.pendingPreviewUpdate = True
            self.setCachePaused(True)


    ##########################
    ########    UI    ########

    @err_catcher(name=__name__)
    def setupIcons(self):
        '''Loads the icons for the Preview Player.'''

        self.toolbarIcon_on = Utils.getIconFromPath(os.path.join(self.iconDir, "tool_on.png"), 0.75)
        self.toolbarIcon_off = Utils.getIconFromPath(os.path.join(self.iconDir, "tool_off.png"), 0.75)

        self.playerIcon_on = Utils.getIconFromPath(os.path.join(self.iconDir, "screen_on.png"), 0.75)
        self.playerIcon_off = Utils.getIconFromPath(os.path.join(self.iconDir, "screen_off.png"), 0.75)

        self.cacheIcon_on = Utils.getIconFromPath(os.path.join(self.iconDir, "cache_on.png"), 0.75)
        self.cacheIcon_off = Utils.getIconFromPath(os.path.join(self.iconDir, "cache_off.png"), 0.75)
        self.cacheIcon_green = Utils.getIconFromPath(os.path.join(self.iconDir, "cache_on.png"), 0.75, tint=(0, 255, 0))
        self.cacheIcon_orange = Utils.getIconFromPath(os.path.join(self.iconDir, "cache_on.png"), 0.75, tint=(255, 165, 0))

        self.fxIcon_on = Utils.getIconFromPath(os.path.join(self.iconDir, "swatches_on.png"), 0.75)
        self.fxIcon_off = Utils.getIconFromPath(os.path.join(self.iconDir, "swatches_off.png"), 0.75)

        self.soundIcon_on = Utils.getIconFromPath(os.path.join(self.iconDir, "sound_on.png"), 0.75)
        self.soundIcon_off = Utils.getIconFromPath(os.path.join(self.iconDir, "sound_off.png"), 0.75)

        self.ocioIcon = Utils.getIconFromPath(os.path.join(self.iconDir, "ocio.png"), 0.75)


    @err_catcher(name=__name__)
    def setupUi(self):
        '''Sets up the UI for the Preview Player.'''

        ##  Main Layout
        self.lo_preview_main = QVBoxLayout(self)
        self.lo_preview_main.setContentsMargins(0, 0, 0, 0)
        self.lo_preview_main.setSpacing(0)

        ####  Top Separator
        line_top = QGroupBox()
        self.lo_preview_main.addWidget(line_top)

        ####   Top Information Bar
        self.topBarWidget = QWidget()
        self.lo_topBar = QHBoxLayout(self.topBarWidget)
        self.lo_topBar.setContentsMargins(0, 0, 0, 0)
        self.lo_topBar.setSpacing(4)

        self.l_info = QLabel("")
        self.l_info.setObjectName("l_info")
        self.lo_topBar.addWidget(self.l_info)

        self.lo_topBar.addStretch()

        self.b_toolbar = QPushButton()
        self.b_toolbar.setCheckable(True)
        self.b_toolbar.setChecked(True)
        self.b_toolbar.setFixedSize(32, 32)
        self.b_toolbar.setIconSize(QSize(28, 28))
        self.b_toolbar.setIcon(self.toolbarIcon_on)

        self.lo_topBar.addWidget(self.b_toolbar)

        self.lo_preview_main.addWidget(self.topBarWidget)

        ####  Player Group
        self.playerGroup = QWidget()
        self.lo_playerGroup = QVBoxLayout(self.playerGroup)
        self.lo_playerGroup.setContentsMargins(0, 0, 0, 0)
        self.lo_playerGroup.setSpacing(0)
        self.lo_preview_main.addWidget(self.playerGroup)

        ####  Player Toolbar
        self.toolbarWidget = QWidget()
        self.lo_playerToolbar = QHBoxLayout(self.toolbarWidget)
        self.lo_playerToolbar.setContentsMargins(6, 6, 6, 0)
        self.lo_playerToolbar.setSpacing(4)
        self.lo_playerToolbar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.lo_playerGroup.addWidget(self.toolbarWidget)

        #   Player Enable Button
        self.b_enablePlayer = QPushButton()
        self.b_enablePlayer.setIcon(self.playerIcon_on)
        self.b_enablePlayer.setCheckable(True)
        self.b_enablePlayer.setChecked(True)
        self.b_enablePlayer.setIconSize(QSize(18, 18))

        self.lo_playerToolbar.addWidget(self.b_enablePlayer)

        self.toolButtonsWidget = QWidget()
        self.lo_toolButtons = QHBoxLayout(self.toolButtonsWidget)
        self.lo_toolButtons.setContentsMargins(0, 0, 0, 0)
        self.lo_toolButtons.setSpacing(4)

        self.lo_playerToolbar.addWidget(self.toolButtonsWidget)

        #   Cache Enable Button
        self.b_cacheEnabled = QPushButton()
        self.b_cacheEnabled.setCheckable(True)
        self.b_cacheEnabled.setIcon(self.cacheIcon_on)
        self.b_cacheEnabled.setIconSize(QSize(18, 18))

        self.lo_toolButtons.addWidget(self.b_cacheEnabled)

        #   FX Enable Button
        self.b_fxEnabled = QPushButton()
        self.b_fxEnabled.setCheckable(True)
        self.b_fxEnabled.setIcon(self.fxIcon_on)
        self.b_fxEnabled.setIconSize(QSize(18, 18))
        self.b_fxEnabled.setContextMenuPolicy(Qt.CustomContextMenu)

        self.lo_toolButtons.addWidget(self.b_fxEnabled)

        #   Sound On Button
        self.b_soundEnabled = QPushButton()
        self.b_soundEnabled.setCheckable(True)
        self.b_soundEnabled.setIcon(self.soundIcon_on)
        self.b_soundEnabled.setIconSize(QSize(18, 18))

        self.lo_toolButtons.addWidget(self.b_soundEnabled)

        #   OCIO Enable Button
        self.b_ocioEnabled = QPushButton()
        self.b_ocioEnabled.setCheckable(True)
        self.b_ocioEnabled.setIcon(self.ocioIcon)
        self.b_ocioEnabled.setIconSize(QSize(18, 18))
        self.b_ocioEnabled.setVisible(self.global_useOCIO)

        self.lo_toolButtons.addWidget(self.b_ocioEnabled)

        self.lo_toolButtons.addStretch()

        #  OCIO Presets ComboBox
        self.cb_ocioPresets = QComboBox()
        self.cb_ocioPresets.setMinimumWidth(300)
        self.cb_ocioPresets.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.cb_ocioPresets.setVisible(self.global_useOCIO)

        self.ocioContainer = QWidget()
        self.ocioContainer.setFixedHeight(24)
        lo_ocioCont = QHBoxLayout(self.ocioContainer)
        lo_ocioCont.setContentsMargins(0, 0, 0, 0)
        lo_ocioCont.addWidget(self.cb_ocioPresets)

        self.lo_toolButtons.addWidget(self.ocioContainer)

        ####  Player Widget
        self.playerWidget = QWidget()
        self.playerWidget.setAttribute(Qt.WA_TranslucentBackground, True)
        self.playerWidget.setAutoFillBackground(False)

        self.lo_playerWidget = QVBoxLayout(self.playerWidget)
        self.lo_playerWidget.setContentsMargins(0, 6, 0, 0)
        self.lo_playerWidget.setSpacing(0)

        self.lo_playerGroup.addWidget(self.playerWidget)

        ##   OpenGL Display
        self.DisplayWindow = GLVideoDisplay(self, self.core, self.FxData, self.OcioModule)
        self.DisplayWindow.setObjectName("displayWindow")
        self.DisplayWindow.setMinimumWidth(self.defaultRezX)
        self.DisplayWindow.setMinimumHeight(self.defaultRezY)
        self.DisplayWindow.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.DisplayWindow.setAcceptDrops(True)
        self.DisplayWindow.dragEnterEvent = partial(self.onDragEnterEvent)
        self.DisplayWindow.dragMoveEvent = partial(self.onDragMoveEvent)
        self.DisplayWindow.dragLeaveEvent = partial(self.onDragLeaveEvent)
        self.DisplayWindow.dropEvent = partial(self.onDropEvent)

        self.lo_playerWidget.addWidget(self.DisplayWindow)

        #   Drag Overlay
        self.dragOverlay = QWidget(self.DisplayWindow)
        self.dragOverlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.dragOverlay.setStyleSheet(
            "background-color: rgba(0,0,0,0);"
            "border: 2px dashed rgb(100,200,100);"
        )
        self.dragOverlay.hide()
        self.dragOverlay.setGeometry(self.DisplayWindow.rect())

        ##  Player Controls
        self.PlayControls = PlayerControls(self, self)
        self.lo_playerWidget.addWidget(self.PlayControls)

        ####  Bottom Separator
        line_btm = QGroupBox()
        self.lo_preview_main.addWidget(line_btm)

        #   Make Stylesheet Overrides
        self.styleOverrides()

        logger.debug("Setup UI")


    @err_catcher(name=__name__)
    def styleOverrides(self):
        '''Applies stylesheet overrides.'''

        smallButtonStyleOvr = """
            QPushButton {
                padding: 0px;
                margin: 0px;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
                border: 1px solid rgb(90, 90, 90);
                border-style: inset;
                border-width: 1px;
                border-color: rgb(30, 30, 30);
            }
            """

        smallButtons = [
            self.b_enablePlayer,
            self.b_cacheEnabled,
            self.b_fxEnabled,
            self.b_soundEnabled,
            self.b_ocioEnabled
        ]

        for btn in smallButtons:
            btn.setStyleSheet(smallButtonStyleOvr)


    def connectEvents(self):
        '''Connects the UI signals.'''

        self.DisplayWindow.origMousePressEvent = self.DisplayWindow.mousePressEvent
        self.DisplayWindow.mousePressEvent = self.previewMousePress
        self.DisplayWindow.clickEvent = self.DisplayWindow.mouseReleaseEvent
        self.DisplayWindow.mouseReleaseEvent = self.previewClk
        self.DisplayWindow.mmEvent = self.DisplayWindow.mouseMoveEvent
        self.DisplayWindow.mouseMoveEvent = lambda x: self.mouseDrag(x, self.DisplayWindow)

        if not hasattr(self.DisplayWindow, "resizeEventOrig"):
            self.DisplayWindow.resizeEventOrig = self.DisplayWindow.resizeEvent
        self.DisplayWindow.resizeEvent = self.displayResizeEvent

        self.b_toolbar.toggled.connect(self.toggleToolBar)
        self.b_enablePlayer.toggled.connect(self.togglePreviewPlayer)
        self.b_cacheEnabled.toggled.connect(self.toggleCacheEnable)
        self.b_fxEnabled.toggled.connect(self.toggleFX)
        self.b_soundEnabled.toggled.connect(self.toggleSound)
        self.b_ocioEnabled.toggled.connect(self.toggleOcioEnable)
        self.cb_ocioPresets.currentIndexChanged.connect(self.onOcioChanged)

        self.b_fxEnabled.customContextMenuRequested.connect(self.openFxTools)
        self.FxData.changed.connect(self.DisplayWindow.update)

        self.PreviewCache.cacheUpdated.connect(self.onCacheUpdated)
        self.PreviewCache.cacheComplete.connect(self.onCacheComplete)
        self.frameReady.connect(self.DisplayWindow.displayFrame)
        self.PreviewCache.firstFrameComplete.connect(self.onFirstFrameReady)


    @err_catcher(name=__name__)
    def setupTimers(self):
        '''Sets up the various timers:
        
        - UI refresh throttle timer
        - Cache Rescan timer
        - Playback Refresh timer
        - Playback FPS Timing timer
        '''

        #   Global UI Refresh Timer (throttles coalesced non-playback UI updates)
        self.timer_UiRefresh = QTimer(self)
        self.timer_UiRefresh.setSingleShot(True)
        self.timer_UiRefresh.timeout.connect(self.onUiRefreshTimerTimeout)

        #   Cache Rescan Timer
        self.timer_cacheRescan = QTimer(self)
        self.timer_cacheRescan.setSingleShot(True)
        self.timer_cacheRescan.timeout.connect(self.checkRescan)

        #   Playback Timer (effective refresh rate for display)
        self.timer_playback = QTimer(self)
        self.timer_playback.setInterval(10)
        self.timer_playback.timeout.connect(self._playNextFrame)

        #   Playback FPS Timing Timer
        self.timer_FPS = QElapsedTimer()
        self.timer_FPS.start()


    @err_catcher(name=__name__)
    def toggleToolBar(self, checked: bool):
        '''Show/Hide the player toolbar.
        
        Args:
            checked (bool): Whether the top bar should be visible.
        '''

        if checked:
            self.b_toolbar.setIcon(self.toolbarIcon_on)
            self.b_toolbar.setToolTip("Hide Player Toolbar")
        else:
            self.b_toolbar.setIcon(self.toolbarIcon_off)
            self.b_toolbar.setToolTip("Show Player Toolbar")

        self.b_toolbar.setChecked(checked)
        self.toolbarWidget.setVisible(checked)
        logger.debug(f"Toolbar visibility set to: {checked}")


    @err_catcher(name=__name__)
    def togglePreviewPlayer(self, checked: bool):
        '''Show/Hide the preview display and player controls.

        Args:
            checked (bool): Whether the preview player should be visible.
        '''

        try:
            self.playerEnabled = checked
            self.toolButtonsWidget.setVisible(checked)
            self.playerWidget.setVisible(checked)

            if checked:
                self.b_enablePlayer.setIcon(self.playerIcon_on)
                self.b_enablePlayer.setToolTip("Media Player: ENABLED")

                #   Resume Cache if Enabled
                if hasattr(self, "cacheEnabled"):
                    self.toggleCacheEnable(self.b_cacheEnabled.isChecked())

                #   Display OCIO if Available and Enabled
                if self.global_useOCIO:
                    self.toggleOcioEnable(self.ocioEnabled)

            else:
                self.b_enablePlayer.setIcon(self.playerIcon_off)
                self.b_enablePlayer.setToolTip("Media Player: DISABLED")

                #   Pause Playback and Stop Cache
                self.setTimelinePaused(True)
                if hasattr(self, "PreviewCache"):
                    self.PreviewCache.stop()
                if hasattr(self, "timer_cacheRescan"):
                    self.timer_cacheRescan.stop()

            logger.debug(f"Preview Player visibility set to: {checked}")

        except Exception as e:
            logger.warning(f"Error toggling Preview Player visibility: {e}")


    @err_catcher(name=__name__)
    def toggleCacheEnable(self, enabled: bool):
        '''Enables or disables automatic caching for the preview player.
        
        Args:
            enabled (bool): Whether automatic caching should be enabled.
        '''

        try:
            self.b_cacheEnabled.setChecked(enabled)
            self.cacheEnabled = enabled

            if hasattr(self, "PreviewCache"):
                if not enabled:
                    self.PreviewCache.stop()
                    self.timer_cacheRescan.stop()
                    self.b_cacheEnabled.setIcon(self.cacheIcon_off)
                    self.b_cacheEnabled.setToolTip("Automatic Caching:  DISABLED")

                else:
                    self.b_cacheEnabled.setIcon(self.cacheIcon_on)
                    self.b_cacheEnabled.setToolTip("Automatic Caching:  ENABLED")
                    if self.initialized:
                        self.PreviewCache.start()

                    if self.cacheRescanEnabled:
                        self.checkRescan()


            self.PlayControls.updateCacheSlider()
            logger.debug(f"Automatic Caching set to: {enabled}")

        except Exception as e:
            logger.warning(f"Error toggling Automatic Caching: {e}")


    @err_catcher(name=__name__)
    def toggleFX(self, enabled: bool):
        '''Enables or disables FX for the preview player.

        Args:
            enabled (bool): Whether FX should be enabled.
        '''

        tipAppend = "\n\nRight-Click for FX Controls"

        try:
            self.b_fxEnabled.setChecked(enabled)
            self.FxData.setFxEnabled(enabled)

            if enabled:
                self.b_fxEnabled.setIcon(self.fxIcon_on)
                self.b_fxEnabled.setToolTip(f"FX: ENABLED{tipAppend}")

            else:
                self.b_fxEnabled.setIcon(self.fxIcon_off)
                self.b_fxEnabled.setToolTip(f"FX: DISABLED{tipAppend}")

            logger.debug(f"FX enabled set to: {enabled}")

        except Exception as e:
            logger.warning(f"Error toggling FX Enabled: {e}")


    @err_catcher(name=__name__)
    def openFxTools(self, point: QPoint):
        '''Opens the FX Controls dialog for adjusting image effects.

        Args:
            point (QPoint): The position where the dialog should appear.
        '''

        if not hasattr(self, "FxWindow"):
            self.FxWindow = FxControlsDialog(self.core, self.FxData, self)

        self.FxWindow.show()
        self.FxWindow.raise_()
        self.FxWindow.activateWindow()


    @err_catcher(name=__name__)
    def toggleSound(self, enabled: bool):                        ####   NOT YET IMPLEMENTED
        '''Enables or disables sound for the preview player.

        Args:
            enabled (bool): Whether sound should be enabled.
        '''

        if enabled:
            self.b_soundEnabled.setIcon(self.soundIcon_on)
            self.b_soundEnabled.setToolTip("Audio: ENABLED")
        else:
            self.b_soundEnabled.setIcon(self.soundIcon_off)
            self.b_soundEnabled.setToolTip("Audio: DISABLED")

        logger.debug(f"Audio enabled set to: {enabled}")


    @err_catcher(name=__name__)
    def toggleOcioEnable(self, enabled: bool):
        '''Enables or disables OCIO for the preview player.

        Args:
            enabled (bool): Whether OCIO should be enabled.
        '''

        try:
            if not self.global_useOCIO:
                self.ocioEnabled = False
                return

            self.b_ocioEnabled.setChecked(enabled)
            self.cb_ocioPresets.setVisible(enabled)
            self.ocioEnabled = enabled

            if enabled:
                self.b_ocioEnabled.setToolTip("OCIO:  ENABLED")

            else:
                self.b_ocioEnabled.setToolTip("OCIO:  DISABLED")

            if hasattr(self, "DisplayWindow"):
                self.DisplayWindow.update()

            logger.debug(f"OCIO Enabled set to: {enabled}")

        except Exception as e:
            logger.warning(f"Error toggling OCIO Enabled: {e}")


    @err_catcher(name=__name__)
    def enableControls(self, enable: bool):
        '''Enables or disables the player controls.
        
        Args:
            enable (bool): Whether to enable or disable the controls.
        '''

        self.PlayControls.setEnabled(enable)


    @err_catcher(name=__name__)
    def setOcioStatus(self, status: bool | str):
        '''Display OCIO Errors in UI if Needed.

        Args:
            status (bool | str): True when OCIO is valid, otherwise a user-facing error message.
        '''

        try:
            #   If No Errors, Set No Border and Normal Tooltip
            if status is True:
                self.cb_ocioPresets.setStyleSheet("")
                tip = self.OcioPresets.getTooltip()
                self.cb_ocioPresets.setToolTip(tip)  

            #   If Errors, Set Border Red and Errors in Tooltip
            else:
                stylesheet = """
                    QComboBox {
                        border: 1px solid #cc6666;
                        border-radius: 4px;
                        padding: 1px 18px 1px 3px; /* leave space for the arrow */
                    }
                    QComboBox::drop-down {
                        border-right: 1px solid #cc6666;
                        width: 18px;
                    }
                    QComboBox::drop-down {
                        border-top: 1px solid #cc6666;
                        width: 18px;
                    }
                    QComboBox::drop-down {
                        border-bottom: 1px solid #cc6666;
                        width: 18px;
                    }
                """
                self.cb_ocioPresets.setStyleSheet(stylesheet)
                if status is False:
                    status = "OCIO is disabled or invalid."
                self.cb_ocioPresets.setToolTip(str(status))

        except Exception as e:
            logger.warning(f"ERROR: Failed to Set OCIO Status: {e}")


    @err_catcher(name=__name__)
    def setCacheButtonStyle(self, status: str = "IDLE"):
        '''Sets the color of the cache button based on the current cache status.

        Args:
            status (str, optional): The status of the cache. Defaults to "IDLE".
            ('MAX CACHE', 'ACTIVE', 'IDLE', 'COMPLETE', 'DISABLED')
        '''

        try:
            if self.cacheEnabled:
                match status:
                    case "MAX CACHE":
                        self.b_cacheEnabled.setToolTip("Automatic Caching:  MAX CACHE")
                        icon = self.cacheIcon_orange
                    case "ACTIVE":
                        self.b_cacheEnabled.setToolTip("Automatic Caching:  ACTIVE")
                        icon = self.cacheIcon_green
                    case "IDLE":
                        self.b_cacheEnabled.setToolTip("Automatic Caching:  IDLE")
                        icon = self.cacheIcon_on
                    case "COMPLETE":
                        self.b_cacheEnabled.setToolTip("Automatic Caching:  COMPLETE")
                        icon = self.cacheIcon_on
                    case "DISABLED":
                        self.b_cacheEnabled.setToolTip("Automatic Caching:  DISABLED")
                        icon = self.cacheIcon_off
                    case _:
                        icon = None
            else:
                icon = self.cacheIcon_off

            if icon:
                self.b_cacheEnabled.setIcon(icon)

        except Exception as e:
            logger.warning(f"ERROR: Failed to Set Cache Button Style: {e}")


    @err_catcher(name=__name__)
    def updatePrvInfo(self):
        '''Update the preview metadata label.'''

        infoFiles = self.MediaData.requestedMediaFiles if self.MediaData.useFallback else self.MediaData.mediaFiles
        if not infoFiles:
            return

        #   Abort if No Files
        infoFile = infoFiles[0]
        if not infoFile:
            self.l_info.setText("\nNo image found\n")
            self.l_info.setToolTip("")
            self.DisplayWindow.setToolTip("")
            return

        #   Determine Display Filename
        if self.MediaData.isSeq and len(infoFiles) > 1:
            fileName = Utils.getBasename(Utils.getBaseFile(infoFiles))
        else:
            fileName = Utils.getBasename(infoFile)

        #   Determine File Modification Date
        pdate = (
            self.core.getFileModificationDate(infoFile)
            if os.path.exists(infoFile)
            else "UNKNOWN"
        )

        #   Retrieve Preview Metadata
        infoMetadata = self.MediaData.metadata or self.MediaData.requestedMetadata or {}

        #   Retrieve Width, Height, and Duration from Metadata
        widthMeta = Utils.getInfoMetric(infoMetadata, ["width", "mediaWidth", "resolutionWidth"])
        heightMeta = Utils.getInfoMetric(infoMetadata, ["height", "mediaHeight", "resolutionHeight"])
        durationMeta = Utils.getInfoMetric(infoMetadata, ["durationFrames", "frames", "duration"], fallback=1,)

        #   Determine Final Width, Height, and Duration
        if self.MediaData.useFallback:
            width = widthMeta
            height = heightMeta
            duration = durationMeta

        else:
            width = self.MediaData.pwidth or widthMeta
            height = self.MediaData.pheight or heightMeta
            duration = len(self.MediaData.mediaFiles) if self.MediaData.isSeq else (self.MediaData.pduration or durationMeta)

        #   Get File Size if Enabled
        if self.core.getConfig("globals", "showFileSizes"):
            size = sum(
                Utils.getFileSize(path)
                for path in infoFiles
                if os.path.exists(path)
            )
        else:
            size = None

        iData = {
            "fileName": fileName,
            "width": width,
            "height": height,
            "duration": duration,
            "pdate": pdate,
            "fileSize": size
        }

        #   Update Info Text and Tooltip
        self.setInfoText(iData)
        self.setInfoTooltip(iData)


    @err_catcher(name=__name__)
    def setInfoText(self, iData: dict | str):
        '''Set the Info Text Label with Elided Text to Fit Display Window Width
        
        Args:
            iData (dict | str): The preview info dict or a string to set directly.
        '''

        #   Set Text Directly if Passed as String
        if type(iData) is str:
            self.l_info.setText(iData)
            return

        #   Make Info String
        infoStr = (
            f"{iData['fileName']}\n"
            f"{iData['width']} x {iData['height']}   -   "
            f"{iData['duration']} {'frame' if iData['duration'] == 1 else 'frames'}   -   "
            f"{iData['pdate']}"
        )

        #   Append File Size if Configured
        if iData["fileSize"] is not None:
            infoStr += f"   -   {Utils.getFileSizeStr(iData['fileSize'])}"

        #   Set Elided Text to Fit Display Window Width
        try:
            metrics = QFontMetrics(self.l_info.font())
            lines = []
            for line in infoStr.split("\n"):
                elidedText = metrics.elidedText(line, Qt.ElideRight, self.DisplayWindow.width()-20)
                lines.append(elidedText)

            self.l_info.setText("\n".join(lines))

        except Exception as e:
            logger.warning(f"ERROR: Failed to Set Info Text: {e}")
            self.l_info.setText(infoStr)


    @err_catcher(name=__name__)
    def setInfoTooltip(self, iData: dict):
        '''Set the media information tooltip.
        
        Args:
            iData (dict): The preview info dict.
        '''

        #   Build Tooltip Rows
        rows = [
            ("File", iData["fileName"]),
            ("Resolution", f'{iData["width"]} x {iData["height"]}'),
            ("Duration", f"{iData['duration']} {'frame' if iData['duration'] == 1 else 'frames'}"),
            ("Modified", f"{iData['pdate']}")
        ]

        #   Append File Size if Configured
        if iData["fileSize"] is not None:
            rows.append(("File Size", Utils.getFileSizeStr(iData["fileSize"])))

        #   Add Image Sequence Info
        if self.MediaData.isSeq:
            rows.extend([
                ("Start Frame", self.MediaData.pstart),
                ("End Frame", self.MediaData.pend),
                ("Layer", self.MediaData.selectedLayer),
            ])

        #   Add Video Info
        elif self.MediaData.isVideo:
            rows.extend([
                ("Start Frame", self.MediaData.pstart),
                ("End Frame", self.MediaData.pend),
                ("Timecode Start", self.MediaData.timecodeStart),
                ("Timecode Mode", self.MediaData.timecodeMode),
                ("FPS", round(self.MediaData.fps, 2)),
                ("Codec", self.MediaData.codec),
            ])

        #   Create HTML Table
        rowsHtml = "".join(
            f"""
            <tr>
                <td style="
                    padding-right: 24px;
                    min-width: 110px;
                    white-space: nowrap;
                ">
                    <b>{escape(str(label))}:</b>
                </td>
                <td style="white-space: nowrap;">
                    {escape(str(value))}
                </td>
            </tr>
            """
            for label, value in rows
        )

        tip = f"""
        <table cellspacing="0" cellpadding="2">
            {rowsHtml}
        </table>
        """

        self.l_info.setToolTip(tip)



    ################################
    ########    SETTINGS    ########

    @err_catcher(name=__name__)
    def loadPlayerSettings(self, pData: dict = None):
        '''Loads settings from the Prism User config and Project Config.

        Args:
            pData (dict, optional): The player settings data. If not provided, it will be loaded from the user config.
        '''

        #   Gets Saved User Config if not Passed
        if not pData:
            pData = self.core.getConfig("browser", "mediaPlayerSettings")

            #   Create and Save New Default Data if it Does Not Exist
            if not pData:
                pData = {
                    "toolbarEnabled": True,
                    "playerEnabled": True,
                    "cacheEnabled": True,
                    "ocioEnabled": False,
                    "fxEnabled": False,
                    "playbackFPS": 24,
                    "playbackMode": "loop",
                    "missingFrameMode": "last",
                    "frameDisplay_mode": "frames",
                    "cacheThreads": Utils.getDefaultCacheThreads(),
                    "maxCacheMemPercent": 50,
                    "maxSafetyRamFactor": 0.9,
                    "cacheRescanEnabled": True,
                    "cacheRescanSecs": 10,
                    "check_size": 20,
                    "check_color1": (0.0, 0.0, 0.0),
                    "check_color2": (0.1, 0.1, 0.1),
                    "uiRefreshIntervalMs": 200,
                    }
                self.core.setConfig("browser", "mediaPlayerSettings", pData)

        #   UI Toggles
        if "toolbarEnabled" in pData:
            self.toggleToolBar(pData.get("toolbarEnabled", True))

        if "playerEnabled" in pData:
            self.togglePreviewPlayer(pData.get("playerEnabled", True))

        if "cacheEnabled" in pData:
            self.toggleCacheEnable(pData.get("cacheEnabled", True))

        if "fxEnabled" in pData:
            self.toggleFX(pData.get("fxEnabled", False))

        uiRefreshIntervalMs = pData.get("uiRefreshIntervalMs", self.uiRefreshIntervalMs)
        self.setUiRefreshIntervalMs(uiRefreshIntervalMs)

        #   Start Frame Mode
        self.frameDisplay_mode = pData.get("frameDisplay_mode", self.frameDisplay_mode)

        #   Playback
        self.playback_fps = pData.get("playbackFPS", self.playback_fps)
        self.playback_fps_mode = pData.get("playback_fps_mode", self.playback_fps_mode)
        self.playback_fps_custom = pData.get("playbackFPS_Custom", self.playback_fps_custom)
        self.playback_mode = pData.get("playbackMode", self.playback_mode)
        self.playback_missingFrameMode = pData.get("missingFrameMode", self.playback_missingFrameMode)

        #   Player
        if "cacheThreads" in pData:
            self.PreviewCache.setThreadpool(pData.get("cacheThreads", 4))

        if "maxCacheMemPercent" in pData:
            self.PreviewCache.maxCacheMemPercent = pData.get("maxCacheMemPercent", 50)

        if "maxSafetyRamFactor" in pData:
            self.PreviewCache.Cache.maxSafetyRamFactor = pData.get("maxSafetyRamFactor", 0.9)

        if "cacheRescanEnabled" in pData:
            self.cacheRescanEnabled = pData.get("cacheRescanEnabled", True)

        if "cacheRescanSecs" in pData:
            self.rescanIntervalMs = (pData.get("cacheRescanSecs", 10)) * 1000

        if "check_size" in pData:
            self.DisplayWindow.setBackground(
                                            pData.get("check_size", 20),
                                            pData.get("check_color1", (0.0, 0.0, 0.0)),
                                            pData.get("check_color2", (0.1, 0.1, 0.1))
                                            )
            
        #   OCIO
        if self.global_useOCIO:
            if "ocioEnabled" in pData:
                self.toggleOcioEnable(pData.get("ocioEnabled", False))

            oData = self.core.getConfig(cat="ocio", param="ocioSettings", config="project") or {}
            self.OcioPresets.currentPreset = (oData.get("currOcioPreset", ""))
            self.OcioPresets.presetOrder = (oData.get("ocioPresetOrder", []))
        

    @err_catcher(name=__name__)
    def savePlayerSettings(self):
        '''Saves the current player settings:
        
        - Main settings will be saved to the User's Prism config
        - OCIO settings will be saved to the project config
        '''
        
        #   Save to Prism User Config
        try:
            pData = {
                "toolbarEnabled": self.b_toolbar.isChecked(),
                "playerEnabled": self.b_enablePlayer.isChecked(),
                "cacheEnabled": self.b_cacheEnabled.isChecked(),
                "fxEnabled": self.b_fxEnabled.isChecked(),
                "ocioEnabled": self.b_ocioEnabled.isChecked(),
                "playbackFPS": self.playback_fps,
                "playback_fps_mode": self.playback_fps_mode,
                "playbackFPS_Custom": self.playback_fps_custom,
                "playbackMode": self.playback_mode,
                "missingFrameMode": self.playback_missingFrameMode,
                "frameDisplay_mode": self.frameDisplay_mode,
                "cacheThreads": self.PreviewCache.cacheThreads,
                "maxCacheMemPercent": self.PreviewCache.maxCacheMemPercent,
                "maxSafetyRamFactor": self.PreviewCache.Cache.maxSafetyRamFactor,
                "cacheRescanEnabled": self.cacheRescanEnabled,
                "cacheRescanSecs": self.rescanIntervalMs / 1000,
                "check_size": self.DisplayWindow.check_size,
                "check_color1": self.DisplayWindow.check_color1,
                "check_color2": self.DisplayWindow.check_color2,
                "uiRefreshIntervalMs": int(self.uiRefreshIntervalMs)
                }

            self.core.setConfig("browser", "mediaPlayerSettings", pData)
            logger.debug("Saved Player Settings to Prism Config")

        except Exception as e:
            logger.warning(f"ERROR: Failed to Save Player Settings to Prism Config: {e}")

        #   Save to Project Config
        if self.global_useOCIO:
            try:
                oData = {"currOcioPreset": self.OcioPresets.getCurrPreset(),
                         "ocioPresetOrder": self.OcioPresets.getOrderedPresetNames()}

                self.core.setConfig(cat="ocio", param="ocioSettings", val=oData, config="project")

                logger.debug("Saved OCIO Settings to Project Config")
            except Exception as e:
                logger.warning(f"ERROR: Failed to Save OCIO Settings to Project Config: {e}")


    @err_catcher(name=__name__)
    def loadOcioPresets(self):
        '''Loads the OCIO presets from the project preset directory.'''

        if not self.global_useOCIO:
            return

        try:
            self.OcioPresets = PresetsCollection("ocio")
            presetDir = Utils.getProjectPresetDir(self.core, "ocio")
            Utils.loadPresets(presetDir, self.OcioPresets, ".o_preset")

            logger.debug("Loaded OCIO Presets")
        
        except Exception as e:
            logger.warning(f"ERROR: Failed to Load OCIO Presets: {e}")


    @err_catcher(name=__name__)
    def loadOcioCombo(self):
        '''Populates the OCIO combo box with the available presets.'''

        if not self.global_useOCIO:
            return

        with Utils.blockSignals(self.cb_ocioPresets):
            try:
                self.cb_ocioPresets.clear()

                self.cb_ocioPresets.addItems(self.OcioPresets.getOrderedPresetNames())
                idx = self.cb_ocioPresets.findText(self.OcioPresets.currentPreset)
                if idx != -1:
                    self.cb_ocioPresets.setCurrentIndex(idx)
            
                #   Update Tooltip
                tip = self.OcioPresets.getTooltip()
                self.cb_ocioPresets.setToolTip(tip)

                logger.debug("Populated OCIO Combo with Presets")
            
            except Exception as e:
                logger.warning(f"ERROR: Failed to Populate OCIO Combo: {e}")


    @err_catcher(name=__name__)
    def onPlaybackSettingsChanged(self, settings: dict[str, Any]):
        '''Handle changes to the playback settings.

        Args:
            settings (dict[str, Any]): The new playback settings.
        '''

        self.playback_fps_mode = settings.get("fpsMode", "auto")
        self.playback_fps_custom = settings.get("customFPS", 24)
        self.playback_mode = settings.get("playbackMode", "loop")
        self.playback_missingFrameMode = settings.get("holdingFrameMode", "last")

        #   Reset the Holding Frame
        delattr(self, "holdingFrame") if hasattr(self, "holdingFrame") else None

        self.savePlayerSettings()
        self.setPlaybackFPS()


    @err_catcher(name=__name__)
    def onFrameDisplayChanged(self, settings: dict[str, Any]):
        '''Handle changes to the frame display settings.

        Args:
            settings (dict[str, Any]): The new frame display settings.
        '''

        self.frameDisplay_mode = settings.get("frameDisplay_mode", "frames")

        if hasattr(self, "PlayControls"):
            self.PlayControls.refreshFrameDisplay()

        self.savePlayerSettings()



    ############################
    ########    DATA    ########

    @err_catcher(name=__name__)
    def getSelectedContexts(self) -> list[dict[str, Any]]:   
        '''Return the current Prism selection contexts.

        Returns:
            list[dict[str, Any]]: The list of selected contexts.
        '''

        if hasattr(self.mediaBrowser, "origin") and hasattr(self.mediaBrowser.origin, "getSelectedContexts"):
            return self.mediaBrowser.origin.getSelectedContexts()

        if hasattr(self.mediaBrowser, "getSelectedContexts"):
            return self.mediaBrowser.getSelectedContexts()

        return []


    @err_catcher(name=__name__)
    def getMediaFilesFromContext(self, context: dict[str, Any]) -> list[str]:
        '''Return the media files for a Prism context.

        Args:
            context (dict[str, Any]): The Prism context.

        Returns:
            list[str]: The list of media file paths.
        '''

        return self.core.mediaProducts.getFilesFromContext(context)


    @err_catcher(name=__name__)
    def getFilesFromContext(self, context: dict[str, Any]) -> list[str]:
        '''Return the media files for a Prism context.

        Args:
            context (dict[str, Any]): The Prism context.

        Returns:
            list[str]: The list of media file paths.
        '''

        return self.core.mediaProducts.getFilesFromContext(context)


    @err_catcher(name=__name__)
    def getCurRenders(self) -> list[dict[str, Any]]:
        '''Return the current render contexts from Prism.

        Returns:
            list[dict[str, Any]]: The list of current render contexts.
        '''

        if self.mediaBrowser and hasattr(self.mediaBrowser, "getCurRenders"):
            return self.mediaBrowser.getCurRenders()

        return []


    @err_catcher(name=__name__)
    def getCurrentFilepath(self, curFrame: Optional[int] = None) -> Optional[str]:      
        '''Return the current file path for the preview frame number.
        
        Args:
            curFrame (Optional[int]): The current frame number. If None, it will be determined automatically.

        Returns:
            Optional[str]: The current file path for the preview frame, or None if not available.
        '''

        if not self.MediaData.mediaFiles:
            return None

        if curFrame is None:
            curFrame = self.getCurrentFrame()

        if len(self.MediaData.mediaFiles) == 1:
            return self.MediaData.mediaFiles[0]

        if getattr(self, "prvIsSequence", False) and hasattr(self, "PreviewCache"):
            seqFiles = getattr(self.PreviewCache, "mediaFiles", None)
            if seqFiles:
                framePos = self.frameNumberToPos(curFrame, clamp=True)
                if framePos is None:
                    framePos = 0

                seqPath = seqFiles[framePos] if framePos < len(seqFiles) else None
                if seqPath:
                    return seqPath

        framePos = self.frameNumberToPos(curFrame, clamp=True)
        if framePos is None:
            framePos = 0

        if framePos >= len(self.MediaData.mediaFiles):
            framePos = len(self.MediaData.mediaFiles) - 1

        return self.MediaData.mediaFiles[framePos]



    # @err_catcher(name=__name__)                                               #   IS THIS USED IN PRISM?
    # def getSeqFiles(self, seqFiles: list[str]) -> list[str]:
    #     '''Return sequence files in the order provided by Prism.
        
    #     Args:
    #         seqFiles (list[str]): The list of sequence file paths.

    #     Returns:
    #         list[str]: The list of sequence file paths in the order provided by Prism.
    #     '''

    #     return seqFiles


    @err_catcher(name=__name__)
    def frameNumberToPos(self, frameNumber: int, clamp: bool = True) -> int | None:
        '''Convert a frame number to zero-based playback position.
        
        Args:
            frameNumber (int): The frame number to convert.
            clamp (bool, optional): Whether to clamp the position within valid range. Defaults to True.

        Returns:
            int | None: The zero-based playback position, or None if invalid.
        '''

        if hasattr(self, "PreviewCache"):
            return self.PreviewCache.frameToIdx(frameNumber, clamp=clamp)

        try:
            pos = int(frameNumber) - int(self.MediaData.pstart)
        except Exception:
            return None

        totalFrames = max(1, int(getattr(self.PreviewCache.Cache, "totalFrames", 1))) if hasattr(self, "PreviewCache") else 1
        if clamp:
            return max(0, min(pos, totalFrames - 1))

        if pos < 0 or pos >= totalFrames:
            return None

        return pos


    @err_catcher(name=__name__)
    def posToFrameNumber(self, framePos: int, clamp: bool = True) -> int | None:
        '''Convert a zero-based playback position to frame number.
        
        Args:
            framePos (int): The zero-based playback position to convert.
            clamp (bool, optional): Whether to clamp the frame number within valid range. Defaults to True.

        Returns:
            int | None: The corresponding frame number, or None if invalid.
        '''

        if hasattr(self, "PreviewCache"):
            return self.PreviewCache.idxToFrame(framePos, clamp=clamp)

        try:
            pos = int(framePos)
        except Exception:
            return None

        totalFrames = max(1, int(getattr(self.PreviewCache.Cache, "totalFrames", 1))) if hasattr(self, "PreviewCache") else 1
        if clamp:
            pos = max(0, min(pos, totalFrames - 1))
        elif pos < 0 or pos >= totalFrames:
            return None

        return int(self.MediaData.pstart) + pos


    @err_catcher(name=__name__)
    def getAutoFPS(self) -> float:
        '''Return the auto FPS for the current context:\n
        - Media (if video)\n
        - Shot (if available)\n
        - Project (as fallback)

        Returns:
            float: The determined frames per second (FPS) value.
        '''

        fps_media = self.getMediaFPS()
        if fps_media is not None:
            return fps_media
        
        fps_shot = self.getShotFPS()
        if fps_shot is not None:
            return fps_shot

        fps_project = self.getProjectFPS()
        if fps_project is not None:
            return fps_project

        #   Fallback
        return 24.0


    @err_catcher(name=__name__)
    def getMediaFPS(self) -> float | None:
        '''Return the FPS for the current media.\n
        Video only or None for non-video media.

        Returns:
            float | None: The frames per second (FPS) of the media, or None.
        '''

        return self.MediaData.fps


    @err_catcher(name=__name__)
    def getShotFPS(self) -> float:
        '''Return the frames per second for the current shot.
        
        Returns:
            float: The frames per second (FPS) of the shot, or None if not available
        '''

        try:
            curEntity = self.mediaBrowser.getCurrentData()
            if curEntity:
                metadata = self.core.entities.getMetaData(curEntity)

            return float(metadata.get("fps", {}).get("value"))
        
        except:
            logger.warning(f"Unable to Get Shot FPS Metadata.")
            return None


    @err_catcher(name=__name__)
    def getProjectFPS(self) -> float:
        '''Return the project's frames per second.
        
        Returns:
            float: The frames per second (FPS) of the project.
        '''

        return self.core.projects.getFps()


    @err_catcher(name=__name__)
    def setPlaybackFPS(self):
        '''Sets the playback FPS Based on the Mode.'''

        try:
            playMode = self.playback_fps_mode
            match playMode.lower():

                case "auto":
                    fps = self.getAutoFPS()

                case "media":
                    fps_media = self.getMediaFPS()
                    if fps_media is not None:
                        fps = fps_media

                    else:
                        fps_shot = self.getShotFPS()
                        if fps_shot is not None:
                            fps = fps_shot

                        else:
                            fps = self.getProjectFPS() or 24.0

                case "shot":
                    fps_shot = self.getShotFPS()
                    if fps_shot is not None:
                        fps = fps_shot

                    else:
                        fps = self.getProjectFPS() or 24.0

                case "project":
                    fps = self.getProjectFPS() or 24.0

                case "custom":
                    fps = self.playback_fps_custom

                case _:
                    fps = self.getProjectFPS() or 24.0
                
        except Exception as e:
            logger.error(f"Error setting playback FPS: {e}")
            self.playback_fps = self.getProjectFPS() or 24.0
        
        finally:
            logger.debug(f"Playback FPS set to: {playMode} ({fps} fps)")
            self.playback_fps = fps
            self._playInterval = 1000.0 / max(float(fps), 0.01)

            if hasattr(self, "PlayControls") and self.isPlaying():
                self.PlayControls.updateFpsDisplay(self.playback_fps, self.playback_fps, 1)



    ########################################
    ########    SIGNALS / EVENTS    ########

    @err_catcher(name=__name__)
    def checkMediaTabActive(self) -> bool:
        '''Checks if the "Media" tab is currently active in the Project Browser.

        Returns:
            bool: True if the "Media" tab is active, False otherwise.
        '''

        try:
            if self.projectBrowser:
                tabsBar: QTabBar = self.projectBrowser.tbw_project
                return (tabsBar.tabText(tabsBar.currentIndex()) == "Media")

            return False
        
        except Exception as e:
            logger.warning(f"Error checking if Media tab is active: {e}")
            return False


    @err_catcher(name=__name__)
    def setUiRefreshIntervalMs(self, intervalMs: int):
        '''Sets the global UI refresh interval for throttled UI work.

        Args:
            intervalMs (int): The minimum interval in milliseconds between queued UI refresh flushes.
        '''

        self.uiRefreshIntervalMs = max(0, int(intervalMs))

        #   Keep Sender-side Cache Progress Throttling in Sync with Global UI Refresh Cadence.
        if hasattr(self, "PreviewCache"):
            self.PreviewCache.setSignalIntervalMs(self.uiRefreshIntervalMs)

        if self.uiRefreshIntervalMs <= 0:
            if self.timer_UiRefresh.isActive():
                self.timer_UiRefresh.stop()
            self.flushUiRefreshQueue()


    @err_catcher(name=__name__)
    def queueUiRefresh(self, key: str, callback: callable, immediate: bool = False):
        '''Queues a UI refresh callback under a stable key and flushes on the global heartbeat.

        Args:
            key (str): Unique key for this refresh task. New calls with same key replace older pending work.
            callback (callable): Callback executed on the next global UI refresh flush.
            immediate (bool, optional): If True, execute immediately by flushing the queue. Defaults to False.
        '''

        if not callable(callback):
            return

        self.uiRefreshCallbacks[key] = callback

        if immediate or self.uiRefreshIntervalMs <= 0:
            self.flushUiRefreshQueue()
            return

        if not self.timer_UiRefresh.isActive():
            self.timer_UiRefresh.start(self.uiRefreshIntervalMs)


    @err_catcher(name=__name__)
    def onUiRefreshTimerTimeout(self):
        '''Callback for the global UI refresh timer timeout.'''

        #   Flush all pending UI refresh callbacks
        self.flushUiRefreshQueue()

        #   Check if Cache is Full
        if hasattr(self, "PreviewCache"):
            self.PreviewCache.Cache.checkCacheFull()


    @err_catcher(name=__name__)
    def flushUiRefreshQueue(self):
        '''Flushes all pending throttled UI refresh callbacks.'''

        if not self.uiRefreshCallbacks:
            return

        callbacks = list(self.uiRefreshCallbacks.values())
        self.uiRefreshCallbacks.clear()

        for callback in callbacks:
            callback()


    @err_catcher(name=__name__)
    def displayResizeEvent(self, event: QResizeEvent):
        '''Handles the resize event for the display window and adjusting the aspect ratio.

        Args:
            event (QResizeEvent): The resize event.
        '''

        try:
            #   Update Drag Overlay Geo   
            self.dragOverlay.setGeometry(self.DisplayWindow.rect())

            #   Adjust Preview Aspect Ratio
            self.adjustPreviewAspect()

            #   Call Original Resize Event
            if hasattr(self.DisplayWindow, "resizeEventOrig"):
                self.DisplayWindow.resizeEventOrig(event)

        except Exception as e:
            logger.warning(f"ERROR: Failed to Handle Display Resize Event: {e}")


    @err_catcher(name=__name__)
    def adjustPreviewAspect(self):
        '''Keep the Display at 16:9 and fit media inside while preserving source aspect ratio.'''

        try:
            #   Use Available Width and Calc Height to be 16:9
            window_width = max(1, self.playerWidget.width())
            target_height = max(1, int(window_width * (9.0 / 16.0)))

            self.DisplayWindow.setMinimumHeight(target_height)
            self.DisplayWindow.setMaximumHeight(target_height)

            #   Fit media into the 16:9 Display while Preserving Image's Original Aspect Ratio
            if (
                self.MediaData.pwidth > 0 and
                self.MediaData.pheight > 0 and
                hasattr(self.DisplayWindow, "scale_w") and
                hasattr(self.DisplayWindow, "scale_h")
            ):
                img_aspect = float(self.MediaData.pwidth) / float(self.MediaData.pheight)
                display_aspect = float(window_width) / float(target_height)

                #   Wider than 16:9: fit width
                if img_aspect >= display_aspect:
                    self.DisplayWindow.scale_w = 1.0
                    self.DisplayWindow.scale_h = display_aspect / img_aspect

                #   Taller than 16:9: fit height
                else:
                    self.DisplayWindow.scale_w = img_aspect / display_aspect
                    self.DisplayWindow.scale_h = 1.0

            #   Fallback to Default Scale
            else:
                self.DisplayWindow.scale_w = 1.0
                self.DisplayWindow.scale_h = 1.0

            self.DisplayWindow.update()

            self.setInfoText(self.l_info.text())

        except Exception as e:
            logger.warning(f"ERROR: Failed to Adjust Preview Aspect: {e}")



    ###########################################
    ###########    MOUSE ACTIONS   ############

    @err_catcher(name=__name__)
    def onDragEnterEvent(self, e: QDragEnterEvent):
        '''Handle Drag Enter Event for File Paths
        
        Args:
            e (QDragEnterEvent): The drag enter event.
        '''

        if e.mimeData().hasUrls():
            dragPath = os.path.normpath(e.mimeData().urls()[0].toLocalFile()) if e.mimeData().urls() else ""
            seqFiles = self.MediaData.mediaFiles
            path = os.path.dirname(seqFiles[0]) if seqFiles else ""

            if not dragPath or os.path.dirname(dragPath.strip("/\\")) == path.strip("/\\"):
                e.ignore()
            else:
                e.acceptProposedAction()
                self.dragOverlay.show()
        else:
            e.ignore()


    @err_catcher(name=__name__)
    def onDragMoveEvent(self, e: QDragMoveEvent):
        '''Handle Drag Move Event for File Paths
        
        Args:
            e (QDragMoveEvent): The drag move event.
        '''

        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            e.ignore()


    @err_catcher(name=__name__)
    def onDragLeaveEvent(self, e: QDragLeaveEvent):
        '''Hides Overlay when Leaving

        Args:
            e (QDragLeaveEvent): The drag leave event.
        '''

        self.dragOverlay.hide()


    @err_catcher(name=__name__)
    def onDropEvent(self, e: QDropEvent):
        '''Handle Drop Event for File Paths

        Args:
            e (QDropEvent): The drop event.
        '''

        self.dragOverlay.hide()

        if e.mimeData().hasUrls() and self.mediaBrowser and hasattr(self.mediaBrowser, "ingestMediaToSelection"):
            e.setDropAction(Qt.LinkAction)
            e.accept()

            files = [os.path.normpath(str(url.toLocalFile())) for url in e.mimeData().urls()]
            entity = self.mediaBrowser.getCurrentEntity() if hasattr(self.mediaBrowser, "getCurrentEntity") else None

            if entity:
                self.mediaBrowser.ingestMediaToSelection(entity, files)
        else:
            e.ignore()


    @err_catcher(name=__name__)
    def mouseDrag(self, event: Any, element: Any):
        '''Initiate a Prism drag operation from the preview widget.
        
        Args:
            event (Any): The mouse event triggering the drag.
            element (Any): The UI element being interacted with.
        '''

        if not event or not hasattr(event, "buttons"):
            return

        if event.buttons() != Qt.LeftButton or (event.modifiers() & Qt.ShiftModifier):
            if hasattr(element, "mmEvent"):
                element.mmEvent(event)
            return

        if hasattr(event, "pos") and getattr(self, "_dragStartPos", None) is not None:
            try:
                if (event.pos() - self._dragStartPos).manhattanLength() < QApplication.startDragDistance():
                    if hasattr(element, "mmEvent"):
                        element.mmEvent(event)
                    return
            except Exception:
                pass

        contexts = self.getSelectedContexts()
        if not contexts:
            return

        mods = QApplication.keyboardModifiers()
        pathList = []
        for context in contexts:
            if not context:
                continue

            if mods == Qt.ControlModifier:
                path = context.get("path")
                if path:
                    pathList.append(os.path.normpath(path))
            else:
                mediaFiles = self.core.media.filterValidMediaFiles(self.getMediaFilesFromContext(context))
                for filePath in mediaFiles:
                    pathList.append(os.path.normpath(filePath))

        if not pathList:
            return

        drag = QDrag(self)
        mimeData = QMimeData()
        self.core.callback(name="onPreMediaPlayerDragged", args=[self, pathList])
        urlList = [QUrl.fromLocalFile(p) for p in pathList]
        mimeData.setUrls(urlList)
        drag.setMimeData(mimeData)
        self._previewDragActive = True
        drag.exec_(Qt.CopyAction | Qt.MoveAction)


    @err_catcher(name=__name__)
    def previewClk(self, event):
        '''Handle the event when the preview area is clicked, managing drag state and playback toggling.

        Args:
            event (QMouseEvent): The mouse click event.
        '''

        if self._previewDragActive:
            self._previewDragActive = False
            self.DisplayWindow.clickEvent(event)
            return

        if event.button() == Qt.LeftButton:
            self.onPlayClicked()

        self.DisplayWindow.clickEvent(event)


    @err_catcher(name=__name__)
    def previewMousePress(self, event: QMouseEvent):
        '''Handle the event when the mouse is pressed on the preview area, initializing drag state.

        Args:
            event (QMouseEvent): The mouse press event.
        '''

        self._dragStartPos = event.pos() if hasattr(event, "pos") else None
        self._previewDragActive = False
        self.DisplayWindow.origMousePressEvent(event)



    ###################################
    ###########    OCIO    ############

    @err_catcher(name=__name__)
    def checkSystemOCIO(self):
        '''Checks if OCIO is installed and a config is available.'''

        self.OcioModule = None

        #   Try to Import OCIO Module from Prism's Python Environment
        try:
            import ocio.PyOpenColorIO as ocio
            logger.debug("Imported 'ocio.PyOpenColorIO'.")

        except ImportError:
            try:
                import PyOpenColorIO as ocio
                logger.debug("Imported 'PyOpenColorIO'.")

            except ImportError:
                self.global_useOCIO = False
                self.OcioModule = None
                logger.warning("PyOpenColorIO is not installed. OCIO features will be disabled.")
                return

        self.OcioModule = ocio

        #   Check if OCIO Config is Available
        try:
            self.global_useOCIO = bool(os.environ.get("OCIO"))

        except Exception as e:
            self.global_useOCIO = False
            self.OcioModule = None
            logger.debug(f"Failed to get OCIO config: {e}")

        if self.global_useOCIO:
            logger.debug("System OCIO is available.")
        else:
            logger.warning("System OCIO config is not available. OCIO features will be disabled.")


    @err_catcher(name=__name__)
    def onOcioChanged(self, idx: int, ocioName: str = None  ):
        '''Handles changes to the OCIO preset selection

        Args:
            idx (int): The index of the selected OCIO preset.
            ocioName (str, optional): The name of the selected OCIO preset to set.
        '''

        try:
            #   Set Combo Index if Provided
            if idx:
                self.cb_ocioPresets.setCurrentIndex(idx)

            #   Set Combo Index if Name Provided
            if ocioName:
                name_idx = self.cb_ocioPresets.findText(ocioName)
                if name_idx != -1:
                    self.cb_ocioPresets.setCurrentIndex(name_idx)
            
            #   Update Current Preset and Configure OCIO
            presetName = self.cb_ocioPresets.currentText()
            self.OcioPresets.currentPreset = presetName
            self.configureOCIO()

            if self.MediaData.useFallback and getattr(self.DisplayWindow, "errorData", None):
                self.DisplayWindow.displayError(
                    title=self.DisplayWindow.errorData.get("title", "Unsupported Media"),
                    msg=self.DisplayWindow.errorData.get("msg", self.DisplayWindow.errorData.get("message", "")),
                    error=self.DisplayWindow.errorData.get("error"),
                    details=self.DisplayWindow.errorData.get("details", ""),
                )
                return

            self.reloadCurrentFrame()
            
        except Exception as e:
            logger.warning(f"ERROR: Failed to handle OCIO preset change: {e}")


    @err_catcher(name=__name__)
    def configureOCIO(self) -> bool:
        '''Configures the OCIO color transforms based on the current preset
        
        Returns:
            bool: True if the configuration was successful, False otherwise.
        '''

        try:
            if not self.global_useOCIO:
                if hasattr(self, "DisplayWindow"):
                    self.DisplayWindow.clearOcioTransforms()
                return True

            #   Get Current Preset Data
            pName = self.OcioPresets.currentPreset
            oData = self.OcioPresets.getPresetData(pName)

            if not pName or not oData:
                if hasattr(self, "DisplayWindow"):
                    self.DisplayWindow.clearOcioTransforms()
                self.setOcioStatus("No OCIO preset is currently selected.")
                return False
            
            input_space = oData.get("Color_Space", "")
            display = oData.get("Display", "")
            view = oData.get("View", "")
            look = oData.get("Look", "")
            lut_value = oData.get("LUT", "").strip()
            luts = [lut_value] if lut_value else []

            missingFields = []
            if not input_space:
                missingFields.append("Color Space")
            if not display:
                missingFields.append("Display")
            if not view:
                missingFields.append("View")

            if missingFields:
                if hasattr(self, "DisplayWindow"):
                    self.DisplayWindow.clearOcioTransforms()
                missingText = ", ".join(missingFields)
                self.setOcioStatus(f"OCIO preset '{pName}' is incomplete. Missing: {missingText}.")
                return False
            
            #   Set OCIO Transforms in Display Window
            result = self.DisplayWindow.setOcioTransforms(
                                            inputSpace=input_space,
                                            display=display,
                                            view=view,
                                            look=look,
                                            luts=luts,
                                        )
            
            #   Color OCIO Presets Combo if Any Errors
            self.setOcioStatus(result if result is not True else True)

            return True
        
        except Exception as e:
            logger.warning(f"ERROR: Failed to configure OCIO: {e}")
            self.setOcioStatus(f"Failed to configure OCIO: {e}")
            return False



    ####################################
    ###########    CACHE    ############

    @err_catcher(name=__name__)
    def setCachePaused(self, paused: bool):
        '''Sets the cache paused state.

        Args:
            paused (bool): True to pause the cache, False to resume.
        '''
        if paused:
            self.PreviewCache.stop()
        else:
            if self.cacheEnabled:
                self.PreviewCache.start()


    @err_catcher(name=__name__)
    def onCacheUpdated(self, frameNumber: int):
        '''Handle the signal from the Cache workers.

        Args:
            frameNumber (int): The frame number that has been updated in the cache.
        '''

        try:
            #   Mark the Pending Cache Update Frame
            self.pendingCacheUpdateFrame = frameNumber

            #   Keep Playback and Display unrestricted
            if frameNumber == self.currentFrameNumber:
                frame = self.PreviewCache.getFrame(frameNumber)
                if frame is not None:
                    self.frameReady.emit(frameNumber, frame)

            #   Queue Throttled UI Work on the Global Refresh Timer
            self.queueUiRefresh("cacheUpdate", self.flushCacheUiUpdate)

        except Exception as e:
            logger.warning(f"ERROR: Failed to handle cache update signal: {e}")


    @err_catcher(name=__name__)
    def checkRescan(self):
        '''Checks if the cache needs to be rescanned for available frames.'''

        if not self.cacheRescanEnabled or not self.playerEnabled:
            logger.debug("Cache rescan skipped: not enabled.")
            return

        if not self.MediaData.isSeq:
            logger.debug("Cache rescan skipped: media is not a image sequence.")
            return

        if self.PreviewCache.Cache.cacheFull:
            logger.debug("Cache rescan skipped: cache is full.")
            return

        if self.PreviewCache.isRunning:
            logger.debug("Cache rescan skipped: cache is currently running.")
            if not self.timer_cacheRescan.isActive():
                self.timer_cacheRescan.start(self.rescanIntervalMs)
            return

        self.rescanCache()


    @err_catcher(name=__name__)
    def rescanCache(self):
        '''Launches threaded worker to scan cache for new frames.'''

        self.setCacheButtonStyle("ACTIVE")

        logger.debug(f"Rescanning cache for new frames...")

        try:
            rescanWorker = FrameCacheRescanWorker(self, self.PreviewCache)
            rescanWorker.signals.cachedRescanned.connect(self.onCacheRescanned)
            self.PreviewCache.threadpool.start(rescanWorker)

        except Exception as e:
            logger.warning(f"ERROR: Failed to start cache rescan worker: {e}")
            self.setCacheButtonStyle("IDLE")


    @err_catcher(name=__name__)
    def onCacheRescanned(self, changed: bool = False):
        '''Called from Cache Rescanned Signal.
        
        Args:
            changed (bool): Indicates whether the cache content has changed.
        '''

        if not changed:
            if not self.timer_cacheRescan.isActive():
                self.timer_cacheRescan.start(self.rescanIntervalMs)

            self.setCacheButtonStyle("IDLE")
            return

        try:
            #   Get the current frame number before updating the cache range
            oldFrameNumber = int(getattr(self, "currentFrameNumber", self.MediaData.pstart))

            #   Update the cache range from the PreviewCache
            self.MediaData.pstart = int(getattr(self.PreviewCache, "pstart", self.MediaData.pstart))
            self.MediaData.pend = int(getattr(self.PreviewCache, "pend", self.MediaData.pend))
            self.MediaData.pduration = int(getattr(self.PreviewCache, "pduration", self.MediaData.pduration))

            #   Update Player Controls UI
            self.PlayControls.setRange(int(self.MediaData.pstart), int(self.MediaData.pend))

            #   Clamp the current frame number to the new range and update the playhead
            targetFrameNumber = max(int(self.MediaData.pstart), min(int(oldFrameNumber), int(self.MediaData.pend)))
            self.setCurrentFrame(targetFrameNumber, manual=True, reset=False, generateOnMiss=False)

            self.MediaData.update(
                mediaFiles=list(self.MediaData.mediaFiles),
                metadata=dict(self.MediaData.metadata),
                selectedLayer=getattr(self.PreviewCache, "selectedLayer", self.MediaData.selectedLayer),
                isSeq=bool(self.MediaData.isSeq),
                isVideo=bool(getattr(self.PreviewCache, "isVideo", self.MediaData.isVideo)),
                pstart=int(self.MediaData.pstart),
                pend=int(self.MediaData.pend),
                pduration=int(self.MediaData.pduration),
                pwidth=int(self.MediaData.pwidth),
                pheight=int(self.MediaData.pheight),
                fallbackDuration=int(self.MediaData.pduration),
                state="ready",
                useFallback=False,
                error="",
            )

            #   Update the Preview Info Str
            self.updatePrvInfo()

            #   Queue a UI refresh for the cache update
            self.pendingCacheUpdateFrame = targetFrameNumber
            self.queueUiRefresh("cacheUpdate", self.flushCacheUiUpdate)

            #   Restart the cache rescan timer if it's not already active
            if not self.timer_cacheRescan.isActive():
                self.timer_cacheRescan.start(self.rescanIntervalMs)

        except Exception as e:
            logger.warning(f"ERROR: Failed to handle cache rescan update: {e}")

        finally:
            self.setCacheButtonStyle("IDLE")


    @err_catcher(name=__name__)
    def flushCacheUiUpdate(self):
        '''Flushes pending cache UI updates on the global UI refresh cadence.'''

        frameIdx = self.pendingCacheUpdateFrame
        if frameIdx is None:
            return

        self.pendingCacheUpdateFrame = None
        self.PlayControls.updateCacheSlider(frameIdx)


    @err_catcher(name=__name__)
    def onCacheComplete(self):
        '''Handles cacheComplete Signal.'''

        #   Ensure final cache state uses the shared UI-throttle path.
        self.pendingCacheUpdateFrame = self.currentFrameNumber
        self.queueUiRefresh("cacheUpdate", self.flushCacheUiUpdate)



    ###############################################
    ###########    PLAYBACK CONTROLS   ############

    @err_catcher(name=__name__)
    def setTimelinePaused(self, paused: bool):
        '''Sets the timeline paused state and updates the UI accordingly
        
        Args:
            paused (bool): True to pause the timeline, False to resume.
        '''

        self.PlayControls.setPaused(paused)

        self.lastFPSUpdate = 0
        self.fpsFrameCount = 0
            
        if paused:
            try:
                if self.isPlaying():
                    self.timer_playback.stop()
                    self._pausedOffset += self.timer_FPS.elapsed()

            except Exception as e:
                logger.warning(f"ERROR: Failed to pause timeline: {e}")
                return
            
        else:
            try:
                self.timer_FPS.restart()
                self.timer_playback.start()

            except Exception as e:
                logger.warning(f"ERROR: Failed to resume timeline: {e}")
                return

        self.tlPaused = paused


    @err_catcher(name=__name__)
    def isPlaying(self) -> bool:
        '''Returns True if the timeline is currently playing, False otherwise.
        
        Returns:
            bool: True if playing, False if paused.
        '''

        return hasattr(self, "timer_playback") and self.timer_playback.isActive()


    @err_catcher(name=__name__)
    def setCurrentFrame(self, frameNumber:int, manual:bool = False, reset:bool = False, generateOnMiss: bool = True, priorityOnMiss: bool = False):
        '''Move the playhead to a specific frame number and update the UI.
        
        Args:
            frameNumber (int): The frame number to set as current.
            manual (bool, optional): If True, manually set the playhead without affecting playback. Defaults to False.
            reset (bool, optional): If True, reset the playhead and playback offsets. Defaults to False.
            generateOnMiss (bool, optional): If True, generate the frame in the cache if it is missing. Defaults to True.
            priorityOnMiss (bool, optional): If True, prioritize generating this frame over others when missing. Defaults to False.
        '''
        
        #   Clamp to Available Frame-number Range and Derive Internal Playback Position
        try:
            frameNumber = max(int(self.MediaData.pstart), min(int(frameNumber), int(self.MediaData.pend)))
            framePos = self.frameNumberToPos(frameNumber, clamp=True)
            if framePos is None:
                return

            self.currentFrameNumber = int(frameNumber)
            self.currentFrameIdx = int(framePos)
            self._playFramePos = int(framePos)
            self._playFrameIndex = int(framePos)

        except Exception as e:
            logger.warning(f"ERROR: Failed to set current frame: {e}")
            return

        #   Reset Playhead if Needed
        if reset:
            try:
                self._playBaseOffset = framePos * getattr(self, "_playInterval", 1000/24)
                self._pausedOffset = 0
                self.timer_FPS.restart()

            except Exception as e:
                logger.warning(f"ERROR: Failed to reset playhead: {e}")
                return

        #   Manual Playhead Adjustment
        elif manual:
            try:
                if hasattr(self, "_playInterval"):
                    self._playBaseOffset = framePos * self._playInterval
                self.timer_FPS.restart()
            except Exception as e:
                logger.warning(f"ERROR: Failed to manually set playhead: {e}")
                return

        #   UI Sync with the Slider and Spinbox
        self.PlayControls.setFrame(frameNumber, blockSignals=True)

        #   Get the Frame from Cache
        frame = self.PreviewCache.getFrame(frameNumber)

        #   If it Exists Signal to Display
        if frame is not None:
            self.frameReady.emit(frameNumber, frame)

        #   Or Display Holding Frame and Generate the Cache
        else:
            #   Last Frame Mode
            if self.playback_missingFrameMode == "last":
                holdingFrame = self.PreviewCache.getPreviousCachedFrame(frameNumber)

            #   Black Frame Mode
            elif self.playback_missingFrameMode == "black":
                if hasattr(self, "holdingFrame"):
                    holdingFrame = self.holdingFrame
                else:
                    holdingFrame = self.holdingFrame = Utils.holdingFrame(self, "black")

            #   Red X Frame Mode
            elif self.playback_missingFrameMode == "redX":
                if hasattr(self, "holdingFrame"):
                    holdingFrame = self.holdingFrame
                else:
                    holdingFrame = self.holdingFrame = Utils.holdingFrame(self, "redX")

            #   Emit the Holding Frame for Display
            self.frameReady.emit(frameNumber, holdingFrame)

            #   Generate the Frame in the Cache if Missing
            if generateOnMiss:
                self.PreviewCache.generateFrame(frameNumber, priority=priorityOnMiss)


    @err_catcher(name=__name__)
    def reloadCurrentFrame(self):
        '''Reload the current frame by setting the playhead to the current frame index manually.'''

        try:
            self.setCurrentFrame(self.currentFrameNumber, manual=True)

        except Exception as e:
            logger.warning(f"ERROR: Failed to reload current frame: {e}")


    @err_catcher(name=__name__)
    def getCurrentFrame(self) -> int:
        '''Return the current frame number.

        Returns:
            int: The current frame number.
        '''

        return int(getattr(self, "currentFrameNumber", self.MediaData.pstart))


    @err_catcher(name=__name__)
    def onFirstFrameReady(self, frameNumber: int):
        '''Receive the first cached frame and sync the preview state.

        Args:
            frameNumber (int): The number of the first cached frame.
        '''

        try:
            self.currentFrameNumber = int(frameNumber)
            self.PlayControls.setFrame(frameNumber, blockSignals=False)
            self.setCurrentFrame(frameNumber, manual=True, reset=False)

        except Exception as e:
            logger.warning(f"ERROR: Failed to handle first frame ready: {e}")

        try:
            if self.wasPlaying:
                self.setPlaybackFPS()
                QTimer.singleShot(500, lambda: self.setTimelinePaused(False))

        except Exception as e:
            logger.warning(f"ERROR: Failed to resume playback after first frame ready: {e}")


    @err_catcher(name=__name__)
    def onFirstClicked(self):
        '''Handle "First" button by setting the playhead to the first frame.'''
        
        self.setCurrentFrame(self.MediaData.pstart, manual=True, reset=True)


    @err_catcher(name=__name__)
    def onPrevClicked(self):
        '''Handle "Previous" button by setting the playhead to the previous frame.'''

        self.setCurrentFrame(self.currentFrameNumber - 1, manual=True, reset=True)


    @err_catcher(name=__name__)
    def onPlayClicked(self):
        '''Handle "Play" button by toggling playback state.'''

        try:
            if self.isPlaying():
                self.setTimelinePaused(True)
            else:
                self._playInterval = 1000.0 / float(self.playback_fps)
                self.setTimelinePaused(False)

        except Exception as e:
            logger.warning(f"ERROR: Failed to handle play button click: {e}")


    @err_catcher(name=__name__)
    def _playNextFrame(self):
        '''Play the next frame based on the elapsed time and playback interval.'''

        #   Ensure playback interval and start time are set
        try:
            total_frames = self.PreviewCache.Cache.totalFrames
            if total_frames <= 0:
                return
            
        except Exception as e:
            logger.warning(f"ERROR: Failed to play next frame: {e}")
            return

        try:
            #   Calculate the elapsed time since playback started, including any offsets
            elapsed = self.timer_FPS.elapsed()
            elapsed_ms = (elapsed + self._playBaseOffset + self._pausedOffset)

            #   Calculate the target frame based on elapsed time and playback interval
            target_frame = int(elapsed_ms / self._playInterval)      

        except Exception as e:
            logger.warning(f"ERROR: Failed to calculate target frame: {e}")
            return

        #   Determine Next Frame Based on Playback Mode
        match self.playback_mode:
            case "loop":
                direction = 1
                target_frame %= total_frames

            case "once":
                direction = 1
                if target_frame >= total_frames:
                    target_frame = total_frames - 1

                    if self.isPlaying():
                        self.setTimelinePaused(True)

            case "pingpong":
                cycle = total_frames * 2 - 2
                pingpong_phase = None

                if cycle > 0:
                    pingpong_phase = int(elapsed_ms / self._playInterval) % cycle

                    direction = 1 if pingpong_phase < total_frames - 1 else -1

                    target_frame %= cycle

                    if target_frame >= total_frames:
                        target_frame = cycle - target_frame
                else:
                    target_frame = 0

            case "reverse":
                direction = -1
                target_frame %= total_frames
                target_frame = (total_frames - 1) - target_frame

            case _:
                target_frame %= total_frames

        #   Update the Current Frame if it has Changed
        if target_frame != self._playFramePos:
            targetFrameNumber = self.posToFrameNumber(target_frame, clamp=True)
            if targetFrameNumber is None:
                return

            self.setCurrentFrame(targetFrameNumber, manual=False)

            #   Get Selected FPS
            selFPS = self.playback_fps
            self.fpsFrameCount += 1

            #   Update FPS Display if Enough Time Has Passed
            if elapsed - self.lastFPSUpdate >= 500:
                actFPS = self.fpsFrameCount * 1000.0 / (elapsed - self.lastFPSUpdate)

                self.PlayControls.updateFpsDisplay(selFPS, actFPS, direction)

                self.fpsFrameCount = 0
                self.lastFPSUpdate = elapsed


    @err_catcher(name=__name__)
    def onNextClicked(self):
        '''Handle "Next" button by setting the playhead to the next frame.'''

        self.setCurrentFrame(self.currentFrameNumber + 1, manual=True, reset=True)


    @err_catcher(name=__name__)
    def onLastClicked(self):
        '''Handle "Last" button by setting the playhead to the last frame.'''

        self.setCurrentFrame(self.MediaData.pend, manual=True, reset=True)


    @err_catcher(name=__name__)
    def sliderChanged(self, frameNumber: int):
        '''Handle slider value changes by updating the current frame and managing playback state.
        
        Args:
            frameNumber (int): The frame number corresponding to the slider value.
        '''

        try:
            was_playing = self.isPlaying()
            if was_playing:
                self.timer_playback.stop()

            self.setCurrentFrame(frameNumber, manual=True, reset=True, generateOnMiss=True, priorityOnMiss=False)

            if was_playing:
                self.timer_FPS.restart()
                self.timer_playback.start()

        except Exception as e:
            logger.warning(f"ERROR: Failed to handle slider change: {e}")


    @err_catcher(name=__name__)
    def onSliderPressed(self):
        '''Handle the event when the slider is pressed by stopping playback if it was active.'''

        try:
            self._resumeAfterDrag = self.isPlaying()
            if self._resumeAfterDrag:
                self.timer_playback.stop()

        except Exception as e:
            logger.warning(f"ERROR: Failed to handle slider press: {e}")


    @err_catcher(name=__name__)
    def onSliderReleased(self):
        '''Handle the event when the slider is released by updating the current frame and resuming playback if necessary.'''

        try:
            frameNumber = self.PlayControls.getFrame()
            self.setCurrentFrame(frameNumber, manual=True, reset=True, generateOnMiss=True, priorityOnMiss=True)

        except Exception as e:
            logger.warning(f"ERROR: Failed to finalize slider release frame: {e}")

        if self._resumeAfterDrag:
            self.timer_FPS.restart()
            self.timer_playback.start()
        self._resumeAfterDrag = False


    @err_catcher(name=__name__)
    def sliderMousePress(self, event: QMouseEvent):
        '''Handle when the mouse is pressed on the slider, updating the slider value if clicked outside the handle.
        
        Args:
            event (QMouseEvent): The mouse press event.
        '''

        try:
            if event.button() == Qt.LeftButton:
                #   Initialize the style option for the slider to determine the groove and handle positions
                opt = QStyleOptionSlider()
                self.PlayControls.sl_previewImage.initStyleOption(opt)

                groove_rect = self.PlayControls.sl_previewImage.style().subControlRect(
                    QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self.PlayControls.sl_previewImage
                )

                handle_rect = self.PlayControls.sl_previewImage.style().subControlRect(
                    QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, self.PlayControls.sl_previewImage
                )

                #   Check if the click occurred within the groove but outside the handle to update the slider value accordingly
                if groove_rect.contains(event.pos()) and not handle_rect.contains(event.pos()):
                    new_val = QStyle.sliderValueFromPosition(
                        self.PlayControls.sl_previewImage.minimum(),
                        self.PlayControls.sl_previewImage.maximum(),
                        event.pos().x() - groove_rect.x(),
                        groove_rect.width()
                    )
                    self.PlayControls.sl_previewImage.setValue(new_val)
                    event.accept()
                    return

            self.PlayControls.sl_previewImage.origMousePressEvent(event)

        except Exception as e:
            logger.warning(f"ERROR: Failed to handle slider mouse press: {e}")



    ###################################
    ###########    MEDIA   ############

    @err_catcher(name=__name__)
    def resetImage(self, clearCache:bool = True):
        '''Reset the displayed image to checkerboard-only and optionally clear the cache.
        
        Args:
            clearCache (bool): If True, clear the preview cache. Defaults to True.
            '''

        self.playingWasChecked = False

        self.previewLoadToken += 1
        self.cancelPreviewLoadWorker()
        self.pendingPreviewUpdate = False

        self.PreviewCache.stop()
        self.PreviewCache.threadpool.waitForDone(1000)

        if clearCache:
            self.PreviewCache.clear()

        self.MediaData.mediaFiles = []
        self.MediaData.metadata = {}
        self.MediaData.pwidth = self.defaultRezX
        self.MediaData.pheight = self.defaultRezY
        self.MediaData.requestedMediaFiles = []
        self.MediaData.requestedMetadata = {}
        self.MediaData.useFallback = False
        self.l_info.setText("")
        self.l_info.setToolTip("")
        self.DisplayWindow.setToolTip("")

        self.DisplayWindow.clearError()

        try:
            self.DisplayWindow.clearFrame()
            self.adjustPreviewAspect()

        except Exception as e:
            logger.warning(f"ERROR: Failed to reset to blank frame: {e}")

        try:
            self.currentFrameNumber = int(self.MediaData.pstart)
            self.currentFrameIdx = 0
            self._playFramePos = 0
            self._playFrameIndex = 0
            self._playBaseOffset = 0
            self._pausedOffset = 0
            self.lastFPSUpdate = 0
            self.fpsFrameCount = 0

            self.PlayControls.setRange(self.MediaData.pstart, self.MediaData.pstart)
            self.PlayControls.setFrame(self.MediaData.pstart, blockSignals=False)
            self.PlayControls.updateCacheSlider(reset=True)

        except Exception as e:
            logger.warning(f"ERROR: Failed to reset preview cache and UI elements: {e}")


    @err_catcher(name=__name__)
    def updatePreview(self):
        '''Called from Prism MediaVersionPlayer to Display Selected Media'''

        #   Abort if the Preview Player is not Initialized or the Media Tab is not Active
        if not self.initialized or not self.checkMediaTabActive():
            self.pendingPreviewUpdate = True
            return False

        #   Show Loading
        self.l_info.setText("Loading ...\n")
        self.DisplayWindow.displayLoading(True)

        #   Pause the Timeline and Display Loading Message
        if not self.playingWasChecked:
            self.playingWasChecked = True
            self.wasPlaying = self.isPlaying()
            self.setTimelinePaused(True)

        #   Increment the Preview Load Token and Cancel Any Existing Worker
        self.previewLoadToken += 1
        self.cancelPreviewLoadWorker()

        #   Populate MediaData with Selected Media Files and Metadata
        result = self.getSelectedMediaFiles(self.previewLoadToken)
        if not result:
            self.resetImage()
            return False

        #   Validate the Selected Media Files and Metadata
        result = self.validateMedia()
        if not result:
            self.resetImage()
            return False

        #   Display Fallback Error if Media is Unsupported
        if self.MediaData.useFallback:
            self.onPreviewLoadData({
                "token": self.previewLoadToken,
                "state": "fallback",
                "useFallback": self.MediaData.useFallback,
                "metadata": dict(self.MediaData.metadata or self.MediaData.requestedMetadata or {}),
                "requestedMediaFiles": list(self.MediaData.requestedMediaFiles),
            })
            return False

        #   Get the Initial Preview Data for the Worker
        initPrevData = self.MediaData.getData()

        #   Launch BG Thread for Preview Data Prep
        prevWorker: Worker = self.core.worker(self.core)
        prevWorker.function = lambda: self.createMediaDataWorker(prevWorker, initPrevData)
        prevWorker.errored.connect(lambda err: logger.warning(f"ERROR: Preview load worker failed: {err}"))
        prevWorker.dataSent.connect(self.onPreviewLoadData)
        prevWorker.finished.connect(self._onPreviewLoadWorkerFinished)

        self.previewLoadWorker = prevWorker
        prevWorker.start()

        return True


    @err_catcher(name=__name__)
    def getSelectedMediaFiles(self, token:int) -> bool:
        '''Get the selected Prism version and update MediaData
        
        Args:
            token (int): The unique token for this preview load operation.

        Returns:
            bool: True if the selected media was retrieved and MediaData was updated, False otherwise.
        '''

        try:
            contexts = self.getSelectedContexts()

            #   Abort if Multiple Selection
            if len(contexts) > 1:
                self.setInfoText("\nMultiple items selected\n")
                self.l_info.setToolTip("")
                self.DisplayWindow.setToolTip("")
                self.enableControls(False)
                return False

            #   Abort if Nothing Selected
            if not contexts:
                self.setInfoText("\nNo item selected\n")
                self.l_info.setToolTip("")
                self.DisplayWindow.setToolTip("")
                self.enableControls(False)
                return False

            #   Get the Media Files from the Selected Context
            mediaFiles = self.getMediaFilesFromContext(contexts[0])

            #   Filter Out JSON Files to Avoid Empty Prism Dirs Being Treated as Media
            mediaFiles = [
                path for path in mediaFiles
                if Utils.getFileExtension(filePath=path) != ".json"
            ]

            if not mediaFiles:
                return False
            
            metadata = contexts[0]

            #   Get the Selected Layer from the Media Browser if Available
            selectedLayer = None
            selectedFileLayer = self.mediaBrowser.getCurrentFilelayer() if hasattr(self.mediaBrowser, "getCurrentFilelayer") else None
            if selectedFileLayer:
                selectedLayer = selectedFileLayer.get("channel")

            #   Update MediaData with the Selected Media Files, Metadata, and Layer
            self.MediaData.update(
                token=token,
                requestedMediaFiles=mediaFiles,
                requestedMetadata=metadata,
                selectedLayer=selectedLayer,
                state="ready",
                mediaFiles=[],
                metadata={},
                useFallback=False,
                isSeq=False,
                isVideo=False,
                error="",
            )
            return True

        except Exception as e:
            logger.warning(f"ERROR: Failed to get selected media files: {e}")
            return False


    @err_catcher(name=__name__)
    def validateMedia(self) -> bool:
        '''Validate the selected media files and metadata.
        
        Returns:
            bool: True if the media is valid, False otherwise.
        '''

        isVideo = False
        resolvedCodec = None

        try:
            #   Filter to Supported Media File Types
            mediaFiles = self.core.media.filterValidMediaFiles(self.MediaData.requestedMediaFiles)

            #   If Nothing Remains After Filter, Capture Orig for Fallback
            if not mediaFiles:
                mediaFiles = self.MediaData.requestedMediaFiles

            metadata = Utils.normalizeMetadata(self.MediaData.requestedMetadata)

            ext = self.MediaData.requestedExtension
            codec = str(metadata.get("codec_name", "") or "")
            useFallback = False

            #   Fallback for Unsupported File Types
            if ext not in self.core.media.supportedFormats:
                logger.warning(f"Filetype is not supported in the Preview Player: '{ext}'")

                useFallback = Utils.getInvalidMediaInfo(
                    mediaFiles,
                    metadata,
                    reason="File Type Not Supported",
                    codec=codec,
                )

            #   Video Validation
            elif ext in self.core.media.videoFormats:
                vData = Utils.probeVideoInfo(mediaFiles[0], fast=True)

                isVideo = vData.get("hasVideo", False)

                probedCodec = (vData.get("codec") or "").strip().lower()
                metadataCodec = codec.strip().lower()
                resolvedCodec = probedCodec or metadataCodec

                #   Fallback for Unsupported Video
                if not vData.get("hasVideo") or resolvedCodec in {"", "none"}:
                    logger.warning(f"Unsupported media stream ({resolvedCodec or 'unknown'}).")

                    useFallback = Utils.getInvalidMediaInfo(
                        mediaFiles,
                        metadata,
                        reason="No Supported Video Stream",
                        codec=resolvedCodec,
                    )

                #   Fallback for Unsupported Video Codec
                elif not Utils.isCodecSupported(resolvedCodec):
                    logger.warning(f"Unsupported codec ({resolvedCodec}).")

                    useFallback = Utils.getInvalidMediaInfo(
                        mediaFiles,
                        metadata,
                        reason="Unsupported Codec",
                        codec=resolvedCodec,
                    )

            #   Update MediaData with Validated Media Files, Metadata, and Fallback State
            self.MediaData.update(
                mediaFiles = mediaFiles,
                metadata = metadata,
                isVideo = isVideo,
                useFallback = useFallback,
                codec = resolvedCodec,
                state = "fallback" if useFallback else "ready",
            )

            return True

        except Exception as e:
            logger.warning(f"ERROR: Failed to validate media: {e}")
            return False


    @err_catcher(name=__name__)
    def createMediaDataWorker(self, thread: 'Worker', initPrevData: dict):
        '''Worker for Preview Media Data Probe and Parsing.

        Args:
            thread (Worker): The worker thread instance.
            initPrevData (dict): The initial preview data dict from MediaData.
        '''

        #   Compare Token to Ensure This Worker is Still Relevant
        token = initPrevData.get("token")
        if token != self.previewLoadToken:
            return

        try:
            #   Abort if Cancelled
            if getattr(thread, "canceled", False):
                return

            #   Extract Media Files, Metadata, and Other Info from Initial Data
            validMedia = list(initPrevData.get("mediaFiles") or [])
            metadata = dict(initPrevData.get("metadata") or {})
            selectedLayer = initPrevData.get("selectedLayer")
            requestedMediaFiles = list(initPrevData.get("requestedMediaFiles") or [])
            useFallback = initPrevData.get("useFallback", False)
            isVideo = bool(initPrevData.get("isVideo", False))
            codec = str(initPrevData.get("codec", "") or "")

            #   Abort if No Valid Media Files Found
            if not validMedia:
                thread.dataSent.emit({"token": token, "state": "empty"})
                return

            #   Return Fallback Info if Media is Unsupported
            if useFallback:
                thread.dataSent.emit({
                    "token": token,
                    "state": "fallback",
                    "mediaFiles": list(validMedia),
                    "metadata": dict(metadata),
                    "selectedLayer": selectedLayer,
                    "useFallback": useFallback,
                    "isVideo": isVideo,
                    "requestedMediaFiles": list(requestedMediaFiles),
                })
                return
            
            #   Initial Values
            baseFile = validMedia[0]
            prvIsSequence = False
            fps = None
            pstart = 1
            pend = 1
            timecodeStart = None
            timecodeMode = None
            pduration = 1
            seq = list(validMedia)
            pwidth = None
            pheight = None

            ##   Image Sequence
            if len(validMedia) > 1 and not isVideo:
                seqFiles = self.core.media.detectSequence(validMedia, baseFile=baseFile)
                if len(seqFiles) > 1:
                    prvIsSequence = True
                    seq = list(seqFiles)
                    pstart, pend = self.core.media.getFrameRangeFromSequence(seq, baseFile=baseFile)
                    pduration = max(int(pend) - int(pstart) + 1, 1)

            ##   Video
            elif isVideo:
                vData = Utils.probeVideoInfo(baseFile)

                pstart = int(vData.get("frame_start") or 1)
                pduration = int(vData.get("durationFrames") or 1)
                pend = int(pstart + pduration - 1)
                timecodeStart = vData.get("timecodeStart", None)
                timecodeMode = vData.get("timecodeMode", None)
                fps = vData.get("fps") or 24.0
                pwidth = vData.get("width")
                pheight = vData.get("height")

            ##   Still Image
            if not isVideo:
                resolution = self.core.media.getMediaResolution(baseFile)
                pwidth = resolution.get("width")
                pheight = resolution.get("height")

            ##   Fallback
            if not pwidth or not pheight:
                try:
                    resolution = self.core.media.getMediaResolution(baseFile)
                    pwidth = resolution.get("width") or self.defaultRezX
                    pheight = resolution.get("height") or self.defaultRezY
                except Exception:
                    pwidth = self.defaultRezX
                    pheight = self.defaultRezY

            result = {
                "token": token,
                "state": "ready",
                "mediaFiles": list(validMedia),
                "metadata": dict(metadata),
                "selectedLayer": selectedLayer,
                "useFallback": useFallback,
                "isVideo": isVideo,
                "requestedMediaFiles": list(requestedMediaFiles),
                "isSeq": prvIsSequence,
                "fps": fps,
                "codec": codec,
                "pstart": int(pstart),
                "pend": int(pend),
                "timecodeStart": timecodeStart,
                "timecodeMode": timecodeMode,
                "pduration": int(pduration),
                "pwidth": int(pwidth),
                "pheight": int(pheight),
            }

            if getattr(thread, "canceled", False):
                return

            thread.dataSent.emit(result)

        except Exception as e:
            thread.dataSent.emit({
                "token": token,
                "state": "error",
                "error": str(e),
            })


    @err_catcher(name=__name__)
    def cancelPreviewLoadWorker(self):
        '''Cancel the active preview-load worker, if any.'''

        worker = getattr(self, "previewLoadWorker", None)
        if worker and worker.isRunning():
            worker.cancel()


    @err_catcher(name=__name__)
    def onPreviewLoadData(self, resolvedData: dict[str, Any]):
        '''Loads the Preview resolvedData from the Worker.
        
        Args:
            resolvedData (dict[str, Any]): The dictionary sent from the worker.
        '''

        #   Aborts
        if not isinstance(resolvedData, dict):
            return

        if resolvedData.get("token") != self.previewLoadToken:
            return

        if not self.initialized or not self.checkMediaTabActive():
            self.pendingPreviewUpdate = True
            return

        #   Update the shared MediaData
        self.MediaData.update(resolvedData)

        #   Abort if the Worker Result was Empty or an Error Occurred
        if self.MediaData.state in ("empty", "error"):
            if self.MediaData.state == "error":
                logger.warning(f"ERROR: Failed to prepare preview selection: {self.MediaData.error}")

            self.resetImage()
            return

        #   Fallback Media
        if self.MediaData.state == "fallback" and self.MediaData.useFallback:
            self.MediaData.update(
                mediaFiles=self.MediaData.requestedMediaFiles,
                metadata=self.MediaData.requestedMetadata,
                pwidth=self.defaultRezX,
                pheight=self.defaultRezY,
            )

            self.resetImage()
            self.enableControls(False)
            self.updatePrvInfo()
            self.adjustPreviewAspect()

            fallbackData = resolvedData["useFallback"]

            self.DisplayWindow.displayError(
                title=fallbackData.get("title", "Unsupported Media"),
                msg=fallbackData.get("message", "The selected media cannot be previewed."),
                error=fallbackData.get("error"),
                details=fallbackData.get("details", ""),
            )
            return

        if self.MediaData.state != "ready":
            return

        if not self.MediaData.hasMedia:
            self.resetImage()
            return

        self.displayPreview()


    @err_catcher(name=__name__)
    def _onPreviewLoadWorkerFinished(self):
        '''Clear completed preview-load worker references.'''

        worker = self.sender()
        if worker is self.previewLoadWorker:
            self.previewLoadWorker = None


    @err_catcher(name=__name__)
    def displayPreview(self):
        '''Display the preview media in the player.'''

        #   Adjust the preview aspect ratio based on the determined resolution
        self.adjustPreviewAspect()

        #   Enable Playback Controls Except for Single Image
        useControls = self.MediaData.pduration > 1 or self.MediaData.isSeq
        self.enableControls(useControls)

        prevData = {
            "start": self.MediaData.pstart,
            "end": self.MediaData.pend,
            "duration": self.MediaData.pduration,
            "fps": self.MediaData.fps,
            "codec": self.MediaData.codec,
            "width": self.MediaData.pwidth,
            "height": self.MediaData.pheight,
            "selectedLayer": self.MediaData.selectedLayer,
            "isVideo": self.MediaData.isVideo,
        }

        #   Initialize Media in the Cache
        windowWidth = self.DisplayWindow.width() or self.defaultRezX
        self.PreviewCache.setMedia(self.MediaData.mediaFiles, windowWidth, self.MediaData.isSeq, prevData)

        #   Update Player Controls
        self.PlayControls.setRange(self.MediaData.pstart, self.MediaData.pend)
        self.PlayControls.setFrame(self.MediaData.pstart, blockSignals=False)

        self.currentFrameNumber = int(self.MediaData.pstart)
        self.currentFrameIdx = 0
        self._playFramePos = 0
        self._playFrameIndex = 0
        self._playBaseOffset = 0
        self._pausedOffset = 0

        #   Set the Playback FPS
        self.setPlaybackFPS()
        self.playingWasChecked = False

        #   Update the Preview Info String
        self.updatePrvInfo()

        #   Start the Cache
        if self.playerEnabled and self.cacheEnabled and self.checkMediaTabActive():
            self.PreviewCache.start()

        #   Check if Player is Enabled and Ready
        canRequestFrames = bool(self.initialized and self.checkMediaTabActive() and self.playerEnabled)

        #   Set to Start Frame and Request Frame if Necessary
        self.setCurrentFrame(
            self.MediaData.pstart,
            manual=True,
            reset=False,
            generateOnMiss=canRequestFrames,
            priorityOnMiss=canRequestFrames,
        )

        #   Configure OCIO if it is being used
        if self.global_useOCIO:
            self.configureOCIO()

        #   Start Cache Rescanner if Enabled
        if self.cacheRescanEnabled:
            self.timer_cacheRescan.start(self.rescanIntervalMs)



    #######################################
    ###########    RCL MENU    ############

    @err_catcher(name=__name__)
    def rclPreview(self, pos: QPoint):
        '''Show the right-click context menu for the preview widget.

        Args:
            pos (QPoint): The position where the context menu should appear.
        '''

        menu = self.getMediaPreviewMenu()
        self.core.callback(
            name="mediaPlayerContextMenuRequested",
            args=[self, menu],
        )

        if not menu or menu.isEmpty():
            return

        menu.exec_(QCursor.pos())


    @err_catcher(name=__name__)
    def getMediaPreviewMenu(self) -> QMenu | None:
        '''Return the right-click context menu for the preview widget.

        Returns:
            QMenu: The context menu for the preview widget, or None if not applicable.
        '''

        contexts = self.getCurRenders()
        if not contexts or not contexts[0].get("version"):
            return

        path = contexts[0].get("path") or self.getCurrentFilepath() or (self.MediaData.mediaFiles[0] if self.MediaData.mediaFiles else None)
        if not path:
            return
        
        rcmenu = QMenu(self)

        #   Dummy Separator
        def _separator():
            gb = QGroupBox()
            gb.setFlat(False)
            gb.setFixedHeight(15)
            action = QWidgetAction(self)
            action.setDefaultWidget(gb)
            return action

        seqFiles = self.MediaData.mediaFiles

        if seqFiles and self.mediaBrowser and hasattr(self.mediaBrowser, "getCurrentEntity"):
            entity = self.mediaBrowser.getCurrentEntity()
            if entity and entity.get("type") in ["asset", "shot"] and hasattr(self.mediaBrowser, "setPreview"):
                previewText = "Set as assetpreview" if entity.get("type") == "asset" else "Set as shotpreview"
                setPreviewAct = QAction(previewText, self)
                setPreviewAct.triggered.connect(self.mediaBrowser.setPreview)
                rcmenu.addAction(setPreviewAct)

        if len(seqFiles) == 1 or self.MediaData.isSeq:
            #   Convert Options
            cvtMenu = QMenu("Convert", self)
            qtAct = QAction("jpg", self)
            qtAct.triggered.connect(lambda: self.convertImgs(".jpg"))
            cvtMenu.addAction(qtAct)
            qtAct = QAction("png", self)
            qtAct.triggered.connect(lambda: self.convertImgs(".png"))
            cvtMenu.addAction(qtAct)
            qtAct = QAction("mp4", self)
            qtAct.triggered.connect(lambda: self.convertImgs(".mp4"))
            cvtMenu.addAction(qtAct)

            #   ProRes 422 Conversion
            settings = OrderedDict()
            settings["-c"] = "prores_ks"
            settings["-profile:v"] = 2
            settings["-pix_fmt"] = "yuv422p10le"
            settings["-vf"] = "scale=in_color_matrix=auto:out_color_matrix=bt709"
            settings["-color_primaries"] = "bt709"
            settings["-color_trc"] = "bt709"
            settings["-colorspace"] = "bt709"
            movAct = QAction("mov (prores 422)", self)
            movAct.triggered.connect(lambda x=None, s=settings: self.convertImgs(".mov", settings=s))
            cvtMenu.addAction(movAct)

            #   ProRes 4444 Conversion
            settings = OrderedDict()
            settings["-c"] = "prores_ks"
            settings["-profile:v"] = 4
            settings["-pix_fmt"] = "yuva444p10le"
            settings["-vf"] = "scale=in_color_matrix=auto:out_color_matrix=bt709"
            settings["-color_primaries"] = "bt709"
            settings["-color_trc"] = "bt709"
            settings["-colorspace"] = "bt709"
            movAct = QAction("mov (prores 4444)", self)
            movAct.triggered.connect(lambda x=None, s=settings: self.convertImgs(".mov", settings=s))
            cvtMenu.addAction(movAct)

            rcmenu.addMenu(cvtMenu)

        rcmenu.addAction(_separator())

        #   Reload Cache
        iconPath = os.path.join(self.iconDir, "refresh.png")
        icon = self.core.media.getColoredIcon(iconPath)
        Utils.createMenuAction("Reload Cache", rcmenu, self, self.reloadCache, icon=icon)

        #   Player Settings
        iconPath = os.path.join(self.iconDir, "configure.png")
        icon = self.core.media.getColoredIcon(iconPath)
        Utils.createMenuAction("Player Settings", rcmenu, self, self.editPlayerSettings, icon=icon)

        #   OCIO Presets (if OCIO Available)
        if self.global_useOCIO:
            iconPath = os.path.join(self.iconDir, "ocio.png")
            icon = self.core.media.getColoredIcon(iconPath)
            Utils.createMenuAction("Edit OCIO Presets", rcmenu, self, self.editOcioPresets, icon=icon)

        rcmenu.addAction(_separator())

        #   External Player Options
        playMenu = QMenu("Play in", self)
        iconPath = os.path.join(self.iconDir, "play.png")
        icon = self.core.media.getColoredIcon(iconPath)
        playMenu.setIcon(icon)

        if self.externalMediaPlayers is not None:
            for player in self.externalMediaPlayers:
                playerName = player.get("name", "")

                def _comparePlayer(name=playerName):
                    self.compare(name)

                Utils.createMenuAction(playerName, playMenu, self, _comparePlayer)

        rcmenu.addMenu(playMenu)

        Utils.createMenuAction("Default", playMenu, self, lambda: self.compare(prog="default"))
       
        rcmenu.addAction(_separator())

        #   Open in Explorer
        iconPath = os.path.join(self.iconDir, "folder.png")
        icon = self.core.media.getColoredIcon(iconPath)
        Utils.createMenuAction("Open in Explorer", rcmenu, self, lambda: self.core.openFolder(path), icon=icon)

        #   Copy File Path to Clipboard
        copAct = self.core.getCopyAction(path, parent=self)
        rcmenu.addAction(copAct)

        return rcmenu


    @err_catcher(name=__name__)
    def reloadCache(self):
        '''Reload the preview cache and update the preview display.'''

        self.resetImage()
        self.configureOCIO()
        self.updatePreview()


    @err_catcher(name=__name__)
    def convertImgs(self, extension: str, checkRes: bool = True, settings: Optional[dict[str, Any]] = None):
        '''Convert the current media files to a specified format using FFmpeg.

        Args:
            extension (str): The target file extension (e.g., ".mp4").
            checkRes (bool, optional): Whether to check the resolution before conversion. Defaults to True.
            settings (dict, optional): Additional settings for the conversion. Defaults to None.
        '''

        contexts = self.getCurRenders()
        if not contexts:
            return

        files = self.getFilesFromContext(contexts[0])
        if not files:
            return

        inputpath = self.getCurrentFilepath() or files[0]
        if not inputpath:
            return

        if len(files) > 1:
            seqPath = self.core.media.getSequenceFromFilename(inputpath)
            inputpath = seqPath or inputpath

        if checkRes and extension == ".mp4":
            if not self.core.media.checkOddResolution(files[0], popup=True):
                return

        outputpath = os.path.splitext(inputpath)[0] + extension

        startNum = None
        if self.MediaData.isSeq:
            startNum = self.MediaData.pstart

        result = self.core.media.convertMedia(
            inputpath=inputpath,
            startNum=startNum,
            outputpath=outputpath,
            settings=settings,
        )

        if result and result[0] == "" and result[1] == "":
            self.core.copyToClipboard(outputpath, file=True)
            self.core.popup("The images were converted successfully. (path is in clipboard)")
        else:
            self.core.popup("The images could not be converted.")


    @err_catcher(name=__name__)
    def editPlayerSettings(self):
        '''Open the player settings dialog for the user to edit and save settings.'''

        #   Get Settings from User Config (Prism.json)
        pData = self.core.getConfig("browser", "mediaPlayerSettings")

        #   Create and Load UI Window
        playerConfigWindow = PlayerConfigPopup(self, self.core, self)
        playerConfigWindow.loadSettings(pData)

        #   Center in Current Monitor
        pos = Utils.getPopupPosition(playerConfigWindow, self)
        playerConfigWindow.move(pos)

        result = playerConfigWindow.exec()

        #   Save to Prism User Settings
        if result == QDialog.Accepted:
            pData = playerConfigWindow.getSettings()
            self.loadPlayerSettings(pData)
            self.savePlayerSettings()


    @err_catcher(name=__name__)
    def editOcioPresets(self):
        '''Open the OCIO Presets Editor dialog for the user to edit and save presets.'''

        currPreset = self.cb_ocioPresets.currentText()
        self.OcioPresets.currentPreset = currPreset
        
        editWindow = OcioPresetsEditor(self.core, self)

        #   Center in Current Monitor
        pos = Utils.getPopupPosition(editWindow, self)
        editWindow.move(pos)

        logger.debug("Opening OCIO Presets Editor")
        editWindow.exec_()
        
        if editWindow.result() == "Save":
            try:
                presetData, presetOrder = editWindow.getPresets()
                existingNames = set(self.OcioPresets.getPresetNames())
                originalDataMap = {
                    name: Utils.normalizeData(self.OcioPresets.getPresetData(name))
                    for name in existingNames
                }
                self.OcioPresets.clear()

                for name in presetOrder:
                    data = presetData.get(name, {})
                    self.OcioPresets.addPreset(name, data)
                    normalizedData = Utils.normalizeData(data)
                    originalData = originalDataMap.get(name)

                    if name not in existingNames or normalizedData != originalData:
                        pData = {"name": name, "data": data}
                        Utils.savePreset(self.core, "ocio", name, pData, project=True, checkExists=False)

                        logger.debug(f"Saved preset '{name}' to project")

                self.OcioPresets.presetOrder = presetOrder
                self.savePlayerSettings()
                self.loadOcioCombo()

                logger.debug("Saved OCIO Presets")

            except Exception as e:
                logger.warning(f"ERROR: Failed to Save OCIO Presets:\n{e}")


    @err_catcher(name=__name__)
    def compare(self, prog="", paths: Optional[list[str]] = None):
        '''Launch the selected media files in an external media player.

        Args:
            prog (str, optional): The name of the external media player to use. Defaults to "".
            paths (list[str], optional): The list of media file paths to open. Defaults to None.
        '''

        filePath = self.getCurrentFilepath() or (self.MediaData.mediaFiles[0] if self.MediaData.mediaFiles else None)
        if not filePath:
            return

        if self.timeline and self.timeline.state() == QTimeLine.Running:
            self.setTimelinePaused(True)

        if prog == "default":
            progPath = ""
        else:
            mediaPlayer = None
            if prog and self.externalMediaPlayers:
                matchingPlayers = [player for player in self.externalMediaPlayers if player.get("name") == prog]
                if matchingPlayers:
                    mediaPlayer = matchingPlayers[0]
                else:
                    self.core.popup("Can't find media player: %s" % prog)
                    return

            if not mediaPlayer:
                mediaPlayer = self.externalMediaPlayers[0] if self.externalMediaPlayers else None

            progPath = (mediaPlayer.get("path") or "") if mediaPlayer else ""

        comd = []
        if paths:
            if not progPath:
                filePath = paths[0]
            else:
                comd = [progPath]

                for path in paths:
                    comd.append(path)

                if len(paths) > 1 and "rv" in os.path.basename(progPath).lower():
                    comd += ["-view", "defaultLayout"]

        if not comd:
            if not progPath:
                if os.name == "nt":
                    os.startfile(filePath)
                    return

                comd = ["open", filePath]
            else:
                comd = [progPath, filePath]

        if comd:
            mpEnv = os.environ.copy()
            with open(os.devnull, "w") as f:
                logger.debug("launching: %s" % comd)
                try:
                    subprocess.Popen(comd, stdin=subprocess.PIPE, stdout=f, stderr=f, env=mpEnv)
                except Exception:
                    comd = "%s %s" % (comd[0], comd[1])
                    try:
                        subprocess.Popen(
                            comd, stdin=subprocess.PIPE, stdout=f, stderr=f, shell=True, env=mpEnv
                        )
                    except Exception as e:
                        raise RuntimeError("%s - %s" % (comd, e))


    @err_catcher(name=__name__)
    def triggerAutoplay(self, checked: bool = False):
        '''Mirror the MediaBrowser autoplay contract.

        Args:
            checked (bool, optional): Whether autoplay is enabled. Defaults to False.
        '''

        if self.timeline:
            if checked and self.timeline.state() == QTimeLine.Paused:
                self.setTimelinePaused(False)
            elif not checked and self.timeline.state() == QTimeLine.Running:
                self.setTimelinePaused(True)
        else:
            self.tlPaused = not checked

