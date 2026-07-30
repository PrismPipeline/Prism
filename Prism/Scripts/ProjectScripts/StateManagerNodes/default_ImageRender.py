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


from typing import Any, Optional, Dict, List, Tuple, Union

import os
import sys
import time
import platform
import logging

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class ImageRenderClass(object):
    """State Manager node for creating image/sequence renders.
    
    Provides functionality to render 3D scenes with configurable cameras, frame ranges,
    resolutions, render layers, AOVs/passes, and output formats. Supports both local
    and render farm rendering.
    
    Attributes:
        className (str): Node type identifier ("ImageRender")
        listType (str): State list type ("Export")
        stateCategories (Dict): Category configuration for state manager
        core (Any): Reference to PrismCore instance
        state (Any): Reference to QTreeWidgetItem representing this state
        stateManager (Any): Reference to StateManager instance
        canSetVersion (bool): Whether this state supports version control
        customContext (Optional[Dict]): Custom entity context if set
        allowCustomContext (bool): Whether custom context is allowed
        curCam (Any): Currently selected camera
        renderingStarted (bool): Whether rendering has begun
        cleanOutputdir (bool): Whether to clean output directory before render
        mediaType (str): Type of media being produced ("3drenders")
        tasknameRequired (bool): Whether identifier/task name is required
        outputFormats (List[str]): Available output format extensions
        renderPresets (Dict): Available render settings presets
    """
    className = "ImageRender"
    listType = "Export"
    stateCategories = {"Render": [{"label": className, "stateType": className}]}

    @err_catcher(name=__name__)
    def setup(self, state: Any, core: Any, stateManager: Any, node: Optional[Any] = None, stateData: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the ImageRender state.
        
        Args:
            state: QTreeWidgetItem representing this state
            core: PrismCore instance
            stateManager: StateManager instance
            node: Optional node reference (unused)
            stateData: Optional saved state data to load
        """
        self.state = state
        self.core = core
        self.stateManager = stateManager
        self.canSetVersion = True
        self.customContext = None
        self.allowCustomContext = False
        self.cb_context.addItems(["From scenefile", "Custom"])

        self.curCam = None
        self.renderingStarted = False
        self.cleanOutputdir = True

        self.e_name.setText(state.text(0) + " - {identifier}")

        self.rangeTypes = [
            "Scene",
            "Shot",
            "Shot + 1",
            "Single Frame",
            "Custom",
            "Expression",
        ]
        self.cb_rangeType.addItems(self.rangeTypes)
        for idx, rtype in enumerate(self.rangeTypes):
            self.cb_rangeType.setItemData(
                idx, self.stateManager.getFrameRangeTypeToolTip(rtype), Qt.ToolTipRole
            )
        self.w_frameExpression.setToolTip(
            self.stateManager.getFrameRangeTypeToolTip("ExpressionField")
        )

        self.renderPresets = (
            self.stateManager.stateTypes["RenderSettings"].getPresets(self.core)
            if "RenderSettings" in self.stateManager.stateTypes
            else {}
        )
        if self.renderPresets:
            self.cb_renderPreset.addItems(self.renderPresets.keys())
        else:
            self.w_renderPreset.setVisible(False)

        self.l_name.setVisible(False)
        self.e_name.setVisible(False)
        self.gb_submit.setChecked(False)
        self.f_renderLayer.setVisible(False)

        getattr(self.core.appPlugin, "sm_render_startup", lambda x: None)(self)

        masterItems = ["Set as master", "Add to master", "Don't update master"]
        self.cb_master.addItems(masterItems)
        self.product_paths = self.core.paths.getRenderProductBasePaths()
        self.cb_outPath.addItems(list(self.product_paths.keys()))
        if len(self.product_paths) < 2:
            self.w_outPath.setVisible(False)

        self.mediaType = "3drenders"
        self.tasknameRequired = True
        self.outputFormats = [
            ".exr",
            ".png",
            ".jpg",
        ]

        self.cb_format.addItems(self.outputFormats)

        self.resolutionPresets = self.core.projects.getResolutionPresets()
        if "Get from rendersettings" not in self.resolutionPresets:
            self.resolutionPresets.append("Get from rendersettings")

        self.e_osSlaves.setText("All")

        self.connectEvents()

        self.oldPalette = self.b_changeTask.palette()
        self.warnPalette = QPalette()
        self.warnPalette.setColor(QPalette.Button, QColor(200, 0, 0))
        self.warnPalette.setColor(QPalette.ButtonText, QColor(255, 255, 255))

        self.cb_cam.showPopupOrig = self.cb_cam.showPopup
        self.cb_cam.showPopup = self.showCameraPopup

        self.setTaskWarn(True)
        self.nameChanged(state.text(0))

        self.cb_manager.addItems([p.pluginName for p in self.core.plugins.getRenderfarmPlugins()])
        self.core.callback("onStateStartup", self)
        if self.cb_manager.count() == 0:
            self.gb_submit.setVisible(False)

        self.managerChanged(True)
        self.onVersionOverrideChanged(self.chb_version.isChecked())

        self.cb_context.wheelEvent = lambda event: None
        self.cb_rangeType.wheelEvent = lambda event: None
        self.cb_cam.wheelEvent = lambda event: None
        self.cb_renderPreset.wheelEvent = lambda event: None
        self.cb_master.wheelEvent = lambda event: None
        self.cb_outPath.wheelEvent = lambda event: None
        self.cb_renderLayer.wheelEvent = lambda event: None
        self.cb_format.wheelEvent = lambda event: None
        self.cb_manager.wheelEvent = lambda event: None

        if stateData is not None:
            self.loadData(stateData)
        else:
            self.initializeContextBasedSettings()

    @err_catcher(name=__name__)
    def loadData(self, data: Dict[str, Any]) -> None:
        """Load state data from saved configuration.
        
        Restores all render settings including context, identifier, camera,
        resolution, render presets, AOVs, and render farm settings.
        
        Args:
            data: Dictionary containing saved state configuration
        """
        if "contextType" in data:
            self.setContextType(data["contextType"])
        if "customContext" in data:
            self.customContext = data["customContext"]
        if "taskname" in data:
            self.setIdentifier(data["taskname"])
        if "identifier" in data:
            self.setIdentifier(data["identifier"])

        self.updateUi()

        if "stateName" in data:
            self.e_name.setText(data["stateName"])
        elif "statename" in data:
            self.e_name.setText(data["statename"] + " - {identifier}")
        if "renderpresetoverride" in data:
            res = eval(data["renderpresetoverride"])
            self.chb_renderPreset.setChecked(res)
        if "currentrenderpreset" in data:
            idx = self.cb_renderPreset.findText(data["currentrenderpreset"])
            if idx != -1:
                self.cb_renderPreset.setCurrentIndex(idx)
                self.stateManager.saveStatesToScene()
        if "rangeType" in data:
            idx = self.cb_rangeType.findText(data["rangeType"])
            if idx != -1:
                self.cb_rangeType.setCurrentIndex(idx)
                self.updateRange()
        if "startframe" in data:
            self.sp_rangeStart.setValue(int(data["startframe"]))
        if "endframe" in data:
            self.sp_rangeEnd.setValue(int(data["endframe"]))
        if "frameExpression" in data:
            self.le_frameExpression.setText(data["frameExpression"])
        if "currentcam" in data:
            camName = getattr(self.core.appPlugin, "getCamName", lambda x, y: "")(
                self, data["currentcam"]
            )
            idx = self.cb_cam.findText(camName)
            if idx != -1:
                self.curCam = self.camlist[idx]
                self.cb_cam.setCurrentIndex(idx)
                self.stateManager.saveStatesToScene()
        if "resoverride" in data:
            res = eval(data["resoverride"])
            self.chb_resOverride.setChecked(res[0])
            self.sp_resWidth.setValue(res[1])
            self.sp_resHeight.setValue(res[2])
        if "masterVersion" in data:
            idx = self.cb_master.findText(data["masterVersion"])
            if idx != -1:
                self.cb_master.setCurrentIndex(idx)
        if "curoutputpath" in data:
            idx = self.cb_outPath.findText(data["curoutputpath"])
            if idx != -1:
                self.cb_outPath.setCurrentIndex(idx)
        if "renderlayer" in data:
            idx = self.cb_renderLayer.findText(data["renderlayer"])
            if idx != -1:
                self.cb_renderLayer.setCurrentIndex(idx)
                self.stateManager.saveStatesToScene()
        if "outputFormat" in data:
            idx = self.cb_format.findText(data["outputFormat"])
            if idx != -1:
                self.cb_format.setCurrentIndex(idx)
        if "useVersionOverride" in data:
            self.chb_version.setChecked(data["useVersionOverride"])
        if "versionOverride" in data:
            self.sp_version.setValue(data["versionOverride"])
        if "submitrender" in data:
            self.gb_submit.setChecked(eval(data["submitrender"]))
        if "rjmanager" in data:
            idx = self.cb_manager.findText(data["rjmanager"])
            if idx != -1:
                self.cb_manager.setCurrentIndex(idx)
            self.managerChanged(True)
        if "rjprio" in data:
            self.sp_rjPrio.setValue(int(data["rjprio"]))
        if "rjframespertask" in data:
            self.sp_rjFramesPerTask.setValue(int(data["rjframespertask"]))
        if "rjtimeout" in data:
            self.sp_rjTimeout.setValue(int(data["rjtimeout"]))
        if "rjsuspended" in data:
            self.chb_rjSuspended.setChecked(eval(data["rjsuspended"]))
        if "osdependencies" in data:
            self.chb_osDependencies.setChecked(eval(data["osdependencies"]))
        if "osupload" in data:
            self.chb_osUpload.setChecked(eval(data["osupload"]))
        if "ospassets" in data:
            self.chb_osPAssets.setChecked(eval(data["ospassets"]))
        if "osslaves" in data:
            self.e_osSlaves.setText(data["osslaves"])
        if "dlconcurrent" in data:
            self.sp_dlConcurrentTasks.setValue(int(data["dlconcurrent"]))
        if "dlgpupt" in data:
            self.sp_dlGPUpt.setValue(int(data["dlgpupt"]))
            self.gpuPtChanged()
        if "dlgpudevices" in data:
            self.le_dlGPUdevices.setText(data["dlgpudevices"])
            self.gpuDevicesChanged()
        if "enablepasses" in data:
            self.gb_passes.setChecked(eval(data["enablepasses"]))
        if "lastexportpath" in data:
            lePath = self.core.fixPath(data["lastexportpath"])
            self.l_pathLast.setText(lePath)
            self.l_pathLast.setToolTip(lePath)
        if "stateenabled" in data:
            if type(data["stateenabled"]) == int:
                self.state.setCheckState(
                    0, Qt.CheckState(data["stateenabled"]),
                )

        self.core.callback("onStateSettingsLoaded", self, data)

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect Qt signals to their respective slot methods.
        
        Establishes connections between UI widgets and handler methods for
        context, camera, frame range, resolution, AOVs, and render farm settings.
        """
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.cb_context.activated.connect(self.onContextTypeChanged)
        self.b_context.clicked.connect(self.selectContextClicked)
        self.b_changeTask.clicked.connect(self.changeTask)
        self.chb_renderPreset.stateChanged.connect(self.presetOverrideChanged)
        self.cb_renderPreset.activated.connect(self.stateManager.saveStatesToScene)
        self.cb_rangeType.activated.connect(self.rangeTypeChanged)
        self.sp_rangeStart.editingFinished.connect(self.startChanged)
        self.sp_rangeEnd.editingFinished.connect(self.endChanged)
        self.le_frameExpression.textChanged.connect(self.frameExpressionChanged)
        self.le_frameExpression.editingFinished.connect(
            self.stateManager.saveStatesToScene
        )
        self.le_frameExpression.setMouseTracking(True)
        self.le_frameExpression.origMoveEvent = self.le_frameExpression.mouseMoveEvent
        self.le_frameExpression.mouseMoveEvent = self.exprMoveEvent
        self.le_frameExpression.leaveEvent = self.exprLeaveEvent
        self.le_frameExpression.focusOutEvent = self.exprFocusOutEvent
        self.cb_cam.activated.connect(self.setCam)
        self.chb_resOverride.stateChanged.connect(self.resOverrideChanged)
        self.sp_resWidth.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.sp_resHeight.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.b_resPresets.clicked.connect(self.showResPresets)
        self.cb_master.activated.connect(self.stateManager.saveStatesToScene)
        self.cb_outPath.activated.connect(self.stateManager.saveStatesToScene)
        self.cb_renderLayer.activated.connect(self.onRenderLayerChanged)
        self.cb_format.activated.connect(self.stateManager.saveStatesToScene)
        self.chb_version.stateChanged.connect(self.onVersionOverrideChanged)
        self.sp_version.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.b_version.clicked.connect(self.onVersionOverrideClicked)
        self.gb_submit.toggled.connect(self.rjToggled)
        self.cb_manager.activated.connect(self.managerChanged)
        self.sp_rjPrio.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.sp_rjFramesPerTask.editingFinished.connect(
            self.stateManager.saveStatesToScene
        )
        self.sp_rjTimeout.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.chb_rjSuspended.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_osDependencies.stateChanged.connect(
            self.stateManager.saveStatesToScene
        )
        self.chb_osUpload.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_osPAssets.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.e_osSlaves.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.b_osSlaves.clicked.connect(self.openSlaves)
        self.sp_dlConcurrentTasks.editingFinished.connect(
            self.stateManager.saveStatesToScene
        )
        self.sp_dlGPUpt.editingFinished.connect(self.gpuPtChanged)
        self.le_dlGPUdevices.editingFinished.connect(self.gpuDevicesChanged)
        self.gb_passes.toggled.connect(self.stateManager.saveStatesToScene)
        self.b_addPasses.clicked.connect(self.showPasses)
        self.tw_passes.customContextMenuRequested.connect(self.rclickPasses)
        self.b_pathLast.clicked.connect(lambda: self.stateManager.showLastPathMenu(self))
        self.tw_passes.itemDoubleClicked.connect(
            lambda x: self.core.appPlugin.sm_render_openPasses(self)
        )

    @err_catcher(name=__name__)
    def initializeContextBasedSettings(self) -> None:
        """Initialize state settings based on current context.
        
        Sets appropriate defaults for frame range and identifier based on
        whether the scene is an asset, shot, or scene-based context.
        """
        context = self.getCurrentContext()
        if context.get("type") == "asset":
            self.setRangeType("Single Frame")
        elif context.get("type") == "shot":
            self.setRangeType("Shot")
        elif self.stateManager.standalone:
            self.setRangeType("Custom")
        else:
            self.setRangeType("Scene")

        start, end = self.getFrameRange("Scene")
        if start is not None:
            self.sp_rangeStart.setValue(start)

        if end is not None:
            self.sp_rangeEnd.setValue(end)

        if context.get("task"):
            self.setIdentifier(context.get("task"))

        self.updateUi()

    @err_catcher(name=__name__)
    def getLastPathOptions(self) -> Optional[List[Dict[str, Any]]]:
        """Get context menu options for the last render path.
        
        Returns:
            List of menu options with labels and callbacks, or None if no path exists
        """
        path = self.l_pathLast.text()
        if path == "None":
            return

        options = [
            {
                "label": "Play...",
                "callback": lambda: self.core.media.playMediaInExternalPlayer(path)
            },
            {
                "label": "Open in Media Browser...",
                "callback": lambda: self.openInMediaBrowser(path)
            },
            {
                "label": "Open in Explorer...",
                "callback": lambda: self.core.openFolder(path)
            },
        ]
        if os.getenv("PRISM_COPY_FILE_CONTENT", "0") == "1":
            options.append({
                "label": "Copy",
                "callback": lambda: self.core.copyToClipboard(path, file=True)
            })
        else:
            options.append({
                "label": "Copy Path",
                "callback": lambda: self.core.copyToClipboard(path, file=False)
            })

        return options

    @err_catcher(name=__name__)
    def openInMediaBrowser(self, path: str) -> None:
        """Open the specified render in the Media Browser.
        
        Args:
            path: File path to the rendered media
        """
        self.core.projectBrowser()
        self.core.pb.showTab("Media")
        data = self.core.paths.getRenderProductData(path)
        self.core.pb.mediaBrowser.showRender(entity=data, identifier=data.get("identifier"), version=data.get("version"))

    @err_catcher(name=__name__)
    def selectContextClicked(self, state: Optional[Any] = None) -> None:
        """Open entity selector dialog for custom context.
        
        Args:
            state: Optional state parameter (unused)
        """
        self.dlg_entity = self.stateManager.entityDlg(self)
        data = self.getCurrentContext()
        self.dlg_entity.w_entities.navigate(data)
        self.dlg_entity.entitySelected.connect(lambda x: self.setCustomContext(x))
        self.dlg_entity.show()

    @err_catcher(name=__name__)
    def setCustomContext(self, context: Dict[str, Any]) -> None:
        """Set a custom render context.
        
        Args:
            context: Entity context dictionary
        """
        self.customContext = context
        self.refreshContext()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def onContextTypeChanged(self, state: int) -> None:
        """Handle context type selection change.
        
        Args:
            state: New state index from combo box
        """
        self.refreshContext()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def rangeTypeChanged(self, state: int) -> None:
        """Handle frame range type selection change.
        
        Args:
            state: New state index from combo box
        """
        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def startChanged(self) -> None:
        """Handle start frame value change.
        
        Ensures start frame doesn't exceed end frame.
        """
        if self.sp_rangeStart.value() > self.sp_rangeEnd.value():
            self.sp_rangeEnd.setValue(self.sp_rangeStart.value())

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def endChanged(self) -> None:
        """Handle end frame value change.
        
        Ensures end frame is not less than start frame.
        """
        if self.sp_rangeEnd.value() < self.sp_rangeStart.value():
            self.sp_rangeStart.setValue(self.sp_rangeEnd.value())

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def frameExpressionChanged(self, text: Optional[str] = None) -> None:
        """Handle changes to the frame expression field.
        
        Updates the expression preview window with resolved frames.
        
        Args:
            text: New expression text (unused)
        """
        if not hasattr(self, "expressionWinLabel"):
            return

        frames = self.core.resolveFrameExpression(self.le_frameExpression.text())
        if len(frames) > 1000:
            frames = frames[:1000]
            frames.append("...")

        for idx in range(int(len(frames) / 30.0)):
            frames.insert((idx+1)*30, "\n")

        frameStr = ",".join([str(x) for x in frames]) or "invalid expression"
        self.expressionWinLabel.setText(frameStr)
        self.expressionWin.resize(1, 1)

    @err_catcher(name=__name__)
    def exprMoveEvent(self, event: Any) -> None:
        """Handle mouse move over expression field.
        
        Shows expression preview window near cursor.
        
        Args:
            event: Mouse move event
        """
        self.showExpressionWin(event)
        if hasattr(self, "expressionWin") and self.expressionWin.isVisible():
            self.expressionWin.move(
                QCursor.pos().x() + 20, QCursor.pos().y() - self.expressionWin.height()
            )
        self.le_frameExpression.origMoveEvent(event)

    @err_catcher(name=__name__)
    def showExpressionWin(self, event: Any) -> None:
        """Show the expression preview window.
        
        Creates and displays a popup showing resolved frame numbers.
        
        Args:
            event: Triggering event
        """
        if not hasattr(self, "expressionWin") or not self.expressionWin.isVisible():
            if hasattr(self, "expressionWin"):
                self.expressionWin.close()

            self.expressionWin = QFrame()
            ss = getattr(self.core.appPlugin, "getFrameStyleSheet", lambda x: "")(self)
            self.expressionWin.setStyleSheet(
                ss + """ .QFrame{ border: 2px solid rgb(100,100,100);} """
            )

            self.core.parentWindow(self.expressionWin)
            winwidth = 10
            winheight = 10
            VBox = QVBoxLayout()
            frames = self.core.resolveFrameExpression(self.le_frameExpression.text())
            if len(frames) > 1000:
                frames = frames[:1000]
                frames.append("...")

            for idx in range(int(len(frames) / 30.0)):
                frames.insert((idx+1)*30, "\n")

            frameStr = ",".join([str(x) for x in frames]) or "invalid expression"
            self.expressionWinLabel = QLabel(frameStr)
            VBox.addWidget(self.expressionWinLabel)
            self.expressionWin.setLayout(VBox)
            self.expressionWin.setWindowFlags(
                Qt.FramelessWindowHint  # hides the window controls
                | Qt.WindowStaysOnTopHint  # forces window to top... maybe
                | Qt.SplashScreen  # this one hides it from the task bar!
            )

            self.expressionWin.setGeometry(0, 0, winwidth, winheight)
            self.expressionWin.move(QCursor.pos().x() + 20, QCursor.pos().y())
            self.expressionWin.setAttribute(Qt.WA_ShowWithoutActivating)
            self.expressionWin.show()

    @err_catcher(name=__name__)
    def exprLeaveEvent(self, event: Any) -> None:
        """Handle mouse leaving expression field.
        
        Hides the expression preview window.
        
        Args:
            event: Leave event
        """
        if hasattr(self, "expressionWin") and self.expressionWin.isVisible():
            self.expressionWin.close()

    @err_catcher(name=__name__)
    def exprFocusOutEvent(self, event: Any) -> None:
        """Handle focus loss from expression field.
        
        Hides the expression preview window.
        
        Args:
            event: Focus out event
        """
        if hasattr(self, "expressionWin") and self.expressionWin.isVisible():
            self.expressionWin.close()

    @err_catcher(name=__name__)
    def setCam(self, index: int) -> None:
        """Set the active render camera.
        
        Args:
            index: Camera index in the camera list
        """
        self.curCam = self.camlist[index]
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def nameChanged(self, text: str = "") -> None:
        """Handle changes to the state name.
        
        Formats name with identifier context and ensures uniqueness.
        
        Args:
            text: New name text
        """
        text = self.e_name.text()
        context = {}
        context["identifier"] = self.getIdentifier() or "None"
        num = 0
        try:
            if "{#}" in text:
                while True:
                    context["#"] = num or ""
                    name = text.format(**context)
                    for state in self.stateManager.states:
                        if state.ui.listType != "Export":
                            continue

                        if state is self.state:
                            continue

                        if state.text(0) == name:
                            num += 1
                            break
                    else:
                        break
            else:
                name = text.format(**context)
        except Exception:
            name = text

        if self.state.text(0).endswith(" - disabled"):
            name += " - disabled"

        self.state.setText(0, name)

    @err_catcher(name=__name__)
    def getFormat(self) -> str:
        """Get the current output format.
        
        Returns:
            Current output format string
        """
        self.cb_format.currentText()

    @err_catcher(name=__name__)
    def setFormat(self, fmt: str) -> bool:
        """Set the output format.
        
        Args:
            fmt: Format string to set (e.g., ".exr", ".png")
            
        Returns:
            True if format was found and set, False otherwise
        """
        idx = self.cb_format.findText(fmt)
        if idx != -1:
            self.cb_format.setCurrentIndex(idx)
            self.stateManager.saveStatesToScene()
            return True

        return False

    @err_catcher(name=__name__)
    def getContextType(self) -> str:
        """Get the current context type.
        
        Returns:
            Context type string
        """
        contextType = self.cb_context.currentText()
        return contextType

    @err_catcher(name=__name__)
    def setContextType(self, contextType: str) -> bool:
        """Set the context type.
        
        Args:
            contextType: Context type to set
            
        Returns:
            True if context type was found and set, False otherwise
        """
        idx = self.cb_context.findText(contextType)
        if idx != -1:
            self.cb_context.setCurrentIndex(idx)
            self.refreshContext()
            return True

        return False

    @err_catcher(name=__name__)
    def getIdentifier(self) -> str:
        """Get the current identifier/task name.
        
        Returns:
            Current identifier string
        """
        identifier = self.l_taskName.text()
        return identifier

    @err_catcher(name=__name__)
    def getTaskname(self) -> str:
        """Get the task name (alias for getIdentifier).
        
        Returns:
            Current task name string
        """
        return self.getIdentifier()

    @err_catcher(name=__name__)
    def setIdentifier(self, identifier: str) -> None:
        """Set the identifier/task name.
        
        Args:
            identifier: New identifier string
        """
        self.l_taskName.setText(identifier)
        self.setTaskWarn(not bool(identifier))
        self.updateUi()

    @err_catcher(name=__name__)
    def setTaskname(self, taskname: str) -> None:
        """Set the task name (alias for setIdentifier).
        
        Args:
            taskname: New task name string
        """
        self.setIdentifier(taskname)

    @err_catcher(name=__name__)
    def getSortKey(self) -> str:
        """Get the sorting key for this state.
        
        Returns:
            Identifier used for sorting states
        """
        return self.getIdentifier()

    @err_catcher(name=__name__)
    def changeTask(self) -> None:
        """Open dialog to change the identifier/task name.
        
        Shows a dialog with task suggestions for 3D rendering.
        """
        from PrismUtils import PrismWidgets
        self.nameWin = PrismWidgets.CreateItem(
            startText=self.getIdentifier(),
            showTasks=True,
            taskType="3d",
            core=self.core,
        )
        self.core.parentWindow(self.nameWin)
        self.nameWin.setWindowTitle("Change Identifier")
        self.nameWin.l_item.setText("Identifier:")
        self.nameWin.buttonBox.buttons()[0].setText("Ok")
        self.nameWin.e_item.selectAll()
        result = self.nameWin.exec_()

        if result == 1:
            self.setIdentifier(self.nameWin.e_item.text())
            self.nameChanged(self.e_name.text())
            self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def presetOverrideChanged(self, checked: bool) -> None:
        """Handle render preset override checkbox change.
        
        Args:
            checked: Whether preset override is enabled
        """
        self.cb_renderPreset.setEnabled(checked)
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def resOverrideChanged(self, checked: bool) -> None:
        """Handle resolution override checkbox change.
        
        Args:
            checked: Whether resolution override is enabled
        """
        self.sp_resWidth.setEnabled(checked)
        self.sp_resHeight.setEnabled(checked)
        self.b_resPresets.setEnabled(checked)

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def showResPresets(self) -> None:
        """Show menu with available resolution presets.
        """
        pmenu = QMenu(self)

        for preset in self.resolutionPresets:
            pAct = QAction(preset, self)
            res = self.getResolution(preset)
            if not res:
                continue

            pwidth, pheight = res

            pAct.triggered.connect(
                lambda x=None, v=pwidth: self.sp_resWidth.setValue(v)
            )
            pAct.triggered.connect(
                lambda x=None, v=pheight: self.sp_resHeight.setValue(v)
            )
            pAct.triggered.connect(lambda: self.stateManager.saveStatesToScene())
            pmenu.addAction(pAct)

        pmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def onVersionOverrideChanged(self, checked: bool) -> None:
        """Handle version override checkbox change.
        
        Args:
            checked: Whether version override is enabled
        """
        self.sp_version.setEnabled(checked)
        self.sp_version.lineEdit().setHidden(not checked)
        self.b_version.setEnabled(checked)
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def onVersionOverrideClicked(self) -> None:
        """Show menu with existing versions for override selection.
        """
        pmenu = QMenu(self)

        outPath = self.getOutputName()
        if not outPath:
            return

        existingVersions = self.core.mediaProducts.getVersionsFromSameVersionStack(
            outPath[0]
        )
        for version in sorted(
            existingVersions, key=lambda x: x["version"], reverse=True
        ):
            name = version["version"]
            intVersion = self.core.products.getIntVersionFromVersionName(name)
            if intVersion is None:
                continue

            actV = QAction(name, self)
            actV.triggered.connect(
                lambda y=None, v=intVersion: self.sp_version.setValue(v)
            )
            actV.triggered.connect(lambda: self.stateManager.saveStatesToScene())
            pmenu.addAction(actV)

        if existingVersions:
            pmenu.exec_(QCursor.pos())
        else:
            self.core.popup("No versions exists in the current context.", severity="info")

    @err_catcher(name=__name__)
    def getRangeType(self) -> str:
        """Get the current frame range type.
        
        Returns:
            Current range type string
        """
        return self.cb_rangeType.currentText()

    @err_catcher(name=__name__)
    def setRangeType(self, rangeType: str) -> bool:
        """Set the frame range type.
        
        Args:
            rangeType: Range type to set
            
        Returns:
            True if range type was found and set, False otherwise
        """
        idx = self.cb_rangeType.findText(rangeType)
        if idx != -1:
            self.cb_rangeType.setCurrentIndex(idx)
            self.updateRange()
            return True

        return False

    @err_catcher(name=__name__)
    def getResolution(self, resolution: str) -> Optional[List[int]]:
        """Parse resolution preset string to width and height.
        
        Args:
            resolution: Resolution preset string
            
        Returns:
            List containing [width, height], or None if invalid
        """
        res = None
        if resolution == "Get from rendersettings":
            if hasattr(self.core.appPlugin, "getResolution"):
                res = self.core.appPlugin.getResolution()
            else:
                res = [1920, 1080]
        elif resolution.startswith("Project ("):
            res = resolution[9:-1].split("x")
            res = [int(r) for r in res]
        else:
            try:
                pwidth = int(resolution.split("x")[0])
                pheight = int(resolution.split("x")[1])
                res = [pwidth, pheight]
            except:
                res = getattr(
                    self.core.appPlugin, "evaluateResolution", lambda x: None
                )(resolution)

        return res

    @err_catcher(name=__name__)
    def onRenderLayerChanged(self, state: int) -> None:
        """Handle render layer selection change.
        
        Args:
            state: New state index
        """
        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def getMasterVersion(self) -> str:
        """Get the current master version action.
        
        Returns:
            Master version handling setting
        """
        return self.cb_master.currentText()

    @err_catcher(name=__name__)
    def setMasterVersion(self, master: str) -> bool:
        """Set the master version handling action.
        
        Args:
            master: Master version action to set
            
        Returns:
            True if action was found and set, False otherwise
        """
        idx = self.cb_master.findText(master)
        if idx != -1:
            self.cb_master.setCurrentIndex(idx)
            self.stateManager.saveStatesToScene()
            return True

        return False

    @err_catcher(name=__name__)
    def getLocation(self) -> str:
        """Get the current output location.
        
        Returns:
            Current output location name
        """
        return self.cb_outPath.currentText()

    @err_catcher(name=__name__)
    def setLocation(self, location: str) -> bool:
        """Set the output location.
        
        Args:
            location: Location name to set
            
        Returns:
            True if location was found and set, False otherwise
        """
        idx = self.cb_outPath.findText(location)
        if idx != -1:
            self.cb_outPath.setCurrentIndex(idx)
            self.stateManager.saveStatesToScene()
            return True

        return False

    @err_catcher(name=__name__)
    def showCameraPopup(self) -> None:
        """Refresh camera list and show camera selection popup.
        """
        self.refreshCameras()
        self.cb_cam.showPopupOrig()

    @err_catcher(name=__name__)
    def refreshCameras(self) -> None:
        """Refresh the list of available cameras from the scene.
        """
        # update Cams
        self.cb_cam.clear()
        self.camlist = camNames = []

        if not self.stateManager.standalone:
            self.camlist = self.core.appPlugin.getCamNodes(self, cur=True)
            camNames = [self.core.appPlugin.getCamName(self, i) for i in self.camlist]

        self.cb_cam.addItems(camNames)

        if self.curCam in self.camlist:
            self.cb_cam.setCurrentIndex(self.camlist.index(self.curCam))
        else:
            self.cb_cam.setCurrentIndex(0)
            if len(self.camlist) > 0:
                self.curCam = self.camlist[0]
            else:
                self.curCam = None

            self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def updateUi(self) -> bool:
        """Update the user interface with current state.
        
        Returns:
            True when update is complete
        """
        self.w_context.setHidden(not self.allowCustomContext)
        self.refreshContext()
        self.refreshCameras()
        self.updateRange()
        self.w_comment.setHidden(not self.stateManager.useStateComments())

        if not self.core.mediaProducts.getUseMaster():
            self.w_master.setVisible(False)

        # update Render Layer
        curLayer = self.cb_renderLayer.currentText()
        self.cb_renderLayer.clear()

        layerList = getattr(
            self.core.appPlugin, "sm_render_getRenderLayer", lambda x: []
        )(self)

        self.cb_renderLayer.addItems(layerList)

        if curLayer in layerList:
            self.cb_renderLayer.setCurrentIndex(layerList.index(curLayer))
        else:
            self.cb_renderLayer.setCurrentIndex(0)
            self.stateManager.saveStatesToScene()

        self.refreshSubmitUi()
        getattr(self.core.appPlugin, "sm_render_refreshPasses", lambda x: None)(self)

        self.nameChanged(self.e_name.text())
        getattr(self.core.appPlugin, "sm_render_updateUi", lambda x: None)(self)
        return True

    @err_catcher(name=__name__)
    def refreshContext(self) -> None:
        """Refresh the context display.
        """
        context = self.getCurrentContext()
        contextStr = self.getContextStrFromEntity(context)
        self.l_context.setText(contextStr)

    @err_catcher(name=__name__)
    def getCurrentContext(self) -> Dict[str, Any]:
        """Get the current render context.
        
        Returns:
            Dictionary containing entity context
        """
        context = None
        if self.allowCustomContext:
            ctype = self.getContextType()
            if ctype == "Custom":
                context = self.customContext

        if not context:
            fileName = self.core.getCurrentFileName()
            context = self.core.getScenefileData(fileName)
        
        if "username" in context:
            del context["username"]

        if "user" in context:
            del context["user"]

        return context

    @err_catcher(name=__name__)
    def refreshSubmitUi(self) -> None:
        """Refresh the render farm submission UI elements.
        """
        if not self.gb_submit.isHidden():
            if not self.gb_submit.isCheckable():
                return

            submitChecked = self.gb_submit.isChecked()
            for idx in reversed(range(self.gb_submit.layout().count())):
                self.gb_submit.layout().itemAt(idx).widget().setHidden(not submitChecked)

            if submitChecked:
                self.core.plugins.getRenderfarmPlugin(self.cb_manager.currentText()).sm_render_updateUI(self)

    @err_catcher(name=__name__)
    def updateRange(self) -> None:
        """Update the frame range display based on current range type.
        """
        rangeType = self.cb_rangeType.currentText()
        isCustom = rangeType == "Custom"
        isExp = rangeType == "Expression"
        self.l_rangeStart.setVisible(not isCustom and not isExp)
        self.l_rangeEnd.setVisible(not isCustom and not isExp)
        self.sp_rangeStart.setVisible(isCustom)
        self.sp_rangeEnd.setVisible(isCustom)
        self.w_frameRangeValues.setVisible(not isExp)
        self.w_frameExpression.setVisible(isExp)

        if not isCustom and not isExp:
            frange = self.getFrameRange(rangeType=rangeType)
            start = str(int(frange[0])) if frange[0] is not None else "-"
            end = str(int(frange[1])) if frange[1] is not None else "-"
            self.l_rangeStart.setText(start)
            self.l_rangeEnd.setText(end)

    @err_catcher(name=__name__)
    def getFrameRange(self, rangeType: str) -> Union[Tuple[Optional[int], Optional[int]], List[int]]:
        """Get the frame range for the specified range type.
        
        Args:
            rangeType: Type of range ("Scene", "Shot", "Single Frame", "Custom", "Expression")
            
        Returns:
            Tuple of (start_frame, end_frame) or list of frames for Expression type
        """
        startFrame = None
        endFrame = None
        if rangeType == "Scene":
            if hasattr(self.core.appPlugin, "getFrameRange"):
                startFrame, endFrame = self.core.appPlugin.getFrameRange(self)
                startFrame = int(startFrame)
                endFrame = int(endFrame)
            else:
                startFrame = 1001
                endFrame = 1100
        elif rangeType == "Shot":
            context = self.getCurrentContext()
            if context.get("type") == "shot" and "sequence" in context:
                frange = self.core.entities.getShotRange(context)
                if frange:
                    startFrame, endFrame = frange
        elif rangeType == "Shot + 1":
            context = self.getCurrentContext()
            if context.get("type") == "shot" and "sequence" in context:
                frange = self.core.entities.getShotRange(context)
                if frange and frange[0] is not None and frange[1] is not None:
                    startFrame, endFrame = frange
                    startFrame -= 1
                    endFrame += 1
        elif rangeType == "Single Frame":
            if hasattr(self.core.appPlugin, "getCurrentFrame"):
                startFrame = int(self.core.appPlugin.getCurrentFrame())
            else:
                startFrame = 1001
        elif rangeType == "Custom":
            startFrame = self.sp_rangeStart.value()
            endFrame = self.sp_rangeEnd.value()
        elif rangeType == "Expression":
            return self.core.resolveFrameExpression(self.le_frameExpression.text())

        if startFrame == "":
            startFrame = None

        if endFrame == "":
            endFrame = None

        if startFrame is not None:
            startFrame = int(startFrame)

        if endFrame is not None:
            endFrame = int(endFrame)

        return startFrame, endFrame

    @err_catcher(name=__name__)
    def openSlaves(self) -> None:
        """Open slave assignment dialog for distributed rendering.
        """
        if eval(os.getenv("PRISM_DEBUG", "False")):
            try:
                del sys.modules["SlaveAssignment"]
            except:
                pass

        import SlaveAssignment

        self.sa = SlaveAssignment.SlaveAssignment(
            core=self.core, curSlaves=self.e_osSlaves.text()
        )
        result = self.sa.exec_()

        if result == 1:
            selSlaves = ""
            if self.sa.rb_exclude.isChecked():
                selSlaves = "exclude "
            if self.sa.rb_all.isChecked():
                selSlaves += "All"
            elif self.sa.rb_group.isChecked():
                selSlaves += "groups: "
                for i in self.sa.activeGroups:
                    selSlaves += i + ", "

                if selSlaves.endswith(", "):
                    selSlaves = selSlaves[:-2]

            elif self.sa.rb_custom.isChecked():
                slavesList = [x.text() for x in self.sa.lw_slaves.selectedItems()]
                for i in slavesList:
                    selSlaves += i + ", "

                if selSlaves.endswith(", "):
                    selSlaves = selSlaves[:-2]

            self.e_osSlaves.setText(selSlaves)
            self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def gpuPtChanged(self) -> None:
        """Handle GPU per task setting change.
        """
        self.w_dlGPUdevices.setEnabled(self.sp_dlGPUpt.value() == 0)
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def gpuDevicesChanged(self) -> None:
        """Handle GPU devices list change.
        """
        self.w_dlGPUpt.setEnabled(self.le_dlGPUdevices.text() == "")
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def showPasses(self) -> bool:
        """Show dialog to add render passes/AOVs.
        
        Returns:
            False if no passes available, None otherwise
        """
        steps = getattr(
            self.core.appPlugin, "sm_render_getRenderPasses", lambda x: None
        )(self)

        if steps is None or len(steps) == 0:
            return False

        if self.core.isStr(steps):
            steps = eval(steps)

        if eval(os.getenv("PRISM_DEBUG", "False")):
            try:
                del sys.modules["ItemList"]
            except:
                pass

        import ItemList

        self.il = ItemList.ItemList(core=self.core)
        self.il.setWindowTitle("Select Passes")
        self.core.parentWindow(self.il)
        self.il.tw_steps.doubleClicked.connect(self.il.accept)
        self.il.tw_steps.horizontalHeaderItem(0).setText("Name")
        self.il.tw_steps.setColumnHidden(1, True)
        for i in sorted(steps, key=lambda s: s.lower()):
            rc = self.il.tw_steps.rowCount()
            self.il.tw_steps.insertRow(rc)
            item1 = QTableWidgetItem(i)
            self.il.tw_steps.setItem(rc, 0, item1)

        result = self.il.exec_()

        if result != 1:
            return False

        for i in self.il.tw_steps.selectedItems():
            if i.column() == 0:
                self.core.appPlugin.sm_render_addRenderPass(
                    self, passName=i.text(), steps=steps
                )

        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def rclickPasses(self, pos: QPoint) -> None:
        """Show context menu for passes list.
        
        Args:
            pos: Position where context menu was requested
        """
        rcmenu = QMenu()

        refreshAct = QAction("Refresh", self)
        refreshAct.triggered.connect(lambda: getattr(self.core.appPlugin, "sm_render_refreshPasses", lambda x: None)(self))
        rcmenu.addAction(refreshAct)

        if self.tw_passes.currentItem() and getattr(
            self.core.appPlugin, "canDeleteRenderPasses", True
        ):
            delAct = QAction("Delete", self)
            delAct.triggered.connect(self.deleteAOVs)
            rcmenu.addAction(delAct)

        if hasattr(self.core.appPlugin, "sm_render_rightclickPasses"):
            self.core.appPlugin.sm_render_rightclickPasses(self, rcmenu, pos)

        if rcmenu.isEmpty():
            return

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def deleteAOVs(self) -> None:
        """Delete selected AOVs/passes from the list.
        """
        items = self.tw_passes.selectedItems()
        for i in items:
            self.core.appPlugin.removeAOV(i.text(0))

        self.updateUi()

    @err_catcher(name=__name__)
    def rjToggled(self, checked: bool) -> None:
        """Handle render farm submission checkbox toggle.
        
        Args:
            checked: Whether submission is enabled
        """
        self.refreshSubmitUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def managerChanged(self, text: Optional[Any] = None) -> None:
        """Handle render farm manager selection change.
        
        Args:
            text: New manager text (unused)
        """
        if getattr(self.cb_manager, "prevManager", None):
            self.cb_manager.prevManager.unsetManager(self)

        plugin = self.core.plugins.getRenderfarmPlugin(self.cb_manager.currentText())
        if plugin:
            plugin.sm_render_managerChanged(self)

        self.cb_manager.prevManager = plugin
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def getContextStrFromEntity(self, entity: Dict[str, Any]) -> str:
        """Generate display string from entity context.
        
        Args:
            entity: Entity context dictionary
            
        Returns:
            Formatted context string for display
        """
        if not entity:
            return ""

        entityType = entity.get("type", "")
        if entityType == "asset":
            entityName = entity.get("asset_path", "").replace("\\", "/")
        elif entityType == "shot":
            entityName = self.core.entities.getShotName(entity)
        else:
            return ""

        context = "%s - %s" % (entityType.capitalize(), entityName)
        return context

    @err_catcher(name=__name__)
    def preExecuteState(self) -> List[Any]:
        """Validate state before execution.
        
        Checks for required settings and generates warnings.
        
        Returns:
            List containing [state_name, warnings_list]
        """
        warnings = []

        self.updateUi()

        if self.tasknameRequired and not self.getIdentifier():
            warnings.append(["No identifier is given.", "", 3])

        if self.curCam is None or (
            self.curCam != "Current View"
            and not self.core.appPlugin.isNodeValid(self, self.curCam)
        ):
            warnings.append(["No camera is selected.", "", 3])
        elif self.curCam == "Current View":
            warnings.append(["No camera is selected.", "", 2])

        rangeType = self.cb_rangeType.currentText()
        frames = self.getFrameRange(rangeType)
        if rangeType != "Expression":
            frames = frames[0]

        if frames is None or frames == []:
            warnings.append(["Framerange is invalid.", "", 3])

        if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
            plugin = self.core.plugins.getRenderfarmPlugin(self.cb_manager.currentText())
            warnings += plugin.sm_render_preExecute(self)

        warnings += self.core.appPlugin.sm_render_preExecute(self)

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def getOutputName(self, useVersion: str = "next", identifier: Optional[str] = None, layer: Optional[str] = None) -> Optional[Tuple[str, str, str]]:
        """Generate the output filename and path for the render.
        
        Args:
            useVersion: Version to use ("next" for auto-increment, or specific version)
            identifier: Optional identifier override
            layer: Optional layer name
            
        Returns:
            Tuple of (output_path, output_folder, version) or None if invalid
        """
        if identifier is None:
            identifier = self.getIdentifier()

        if self.tasknameRequired and not identifier:
            return

        extension = self.cb_format.currentText()
        context = self.getCurrentContext()
        framePadding = (
            "#" * self.core.framePadding if self.getRangeType() != "Single Frame" else ""
        )

        if "type" not in context:
            return

        singleFrame = self.cb_rangeType.currentText() == "Single Frame"
        location = self.cb_outPath.currentText()
        if self.chb_version.isChecked():
            version = self.core.versionFormat % self.sp_version.value()
        else:
            version = useVersion if useVersion != "next" else None

        additionalContext = getattr(
            self.core.appPlugin, "getAdditionalRenderContext", lambda x, x2, x3, x4: None
        )(self, context, identifier, layer)

        outputPathData = self.core.mediaProducts.generateMediaProductPath(
            entity=context,
            task=identifier,
            extension=extension,
            framePadding=framePadding,
            comment=self.getComment(),
            version=version,
            location=location,
            singleFrame=singleFrame,
            returnDetails=True,
            mediaType=self.mediaType,
            state=self,
            additionalContext=additionalContext,
        )

        outputFolder = os.path.dirname(outputPathData["path"])
        hVersion = outputPathData["version"]
        return outputPathData["path"], outputFolder, hVersion

    @err_catcher(name=__name__)
    def getComment(self) -> str:
        """Get the current comment for the render.
        
        Returns:
            Comment string
        """
        if self.stateManager.useStateComments():
            comment = self.e_comment.text() or self.stateManager.publishComment
        else:
            comment = self.stateManager.publishComment

        return comment

    @err_catcher(name=__name__)
    def executeState(self, parent: Any, useVersion: str = "next") -> List[str]:
        """Execute the render operation.
        
        Renders images/sequences with configured settings, handles multiple
        identifiers and layers, submits to render farm if enabled.
        
        Args:
            parent: Parent widget for dialogs
            useVersion: Version to use for output
            
        Returns:
            List containing result message string
        """
        rangeType = self.cb_rangeType.currentText()
        frames = self.getFrameRange(rangeType)
        if rangeType != "Expression":
            startFrame = frames[0]
            endFrame = frames[1]
        else:
            startFrame = None
            endFrame = None

        if frames is None or frames == [] or frames[0] is None:
            return [self.state.text(0) + ": error - Framerange is invalid"]

        if rangeType == "Single Frame":
            endFrame = startFrame

        updateMaster = True
        fileName = self.core.getCurrentFileName()
        context = self.getCurrentContext()
        if not self.renderingStarted:
            idfFunc = getattr(self.core.appPlugin, "sm_render_getIdentifiers", None)
            if idfFunc:
                idfs = idfFunc(self)
            else:
                idfs = None

            if idfs is None:
                idfs = [self.getIdentifier()]

            if not idfs:
                return [self.state.text(0) + ": error - no identifiers to render."]

            layerFunc = getattr(self.core.appPlugin, "sm_render_getLayers", None)
            if layerFunc:
                layers = layerFunc(self)
                if layers == []:
                    return [self.state.text(0) + ": error - no layers to render."]
            else:
                layers = None

            if layers is None:
                layers = [""]

            if useVersion == "next" and len(idfs) > 1 and os.getenv("PRISM_RENDER_LAYERS_ALIGN_VERSIONS", "1") == "1":
                for idf in idfs:
                    for layer in layers:
                        outputName, outputPath, hVersion = self.getOutputName(useVersion="next", identifier=idf, layer=layer)
                        useVersion = hVersion if useVersion == "next" or (self.core.compareVersions(hVersion, useVersion) == "higher") else useVersion

            for idf in idfs:
                for layer in layers:
                    result = self.executeIdentifier(
                        idf,
                        useVersion,
                        context,
                        fileName,
                        startFrame,
                        endFrame,
                        frames,
                        rangeType,
                        parent,
                        layer,
                    )
                    if not isinstance(result, dict):
                        return result

                    if not self.renderingStarted:
                        self.core.appPlugin.sm_render_undoRenderSettings(self, result["rSettings"])

            updateMaster = result["updateMaster"]
            rSettings = result["rSettings"]
            outputName = result["outputName"]
            result = result["result"]
        else:
            rSettings = self.LastRSettings
            result = self.core.appPlugin.sm_render_startLocalRender(
                self, rSettings["outputName"], rSettings
            )
            outputName = rSettings["outputName"]

        if result == "publish paused":
            return [self.state.text(0) + " - publish paused"]
        else:
            if updateMaster:
                self.handleMasterVersion(self.expandvars(outputName))

            kwargs = {
                "state": self,
                "scenefile": fileName,
                "settings": rSettings,
                "result": result,
            }

            self.core.callback("postRender", **kwargs)

            if result and "Result=Success" in result:
                return [self.state.text(0) + " - success"]
            else:
                erStr = "%s ERROR - sm_default_imageRenderPublish %s:\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    self.core.version,
                    result,
                )
                if not result or not result.startswith("Execute Canceled: "):
                    if result == "unknown error (files do not exist)":
                        msg = "No files were created during the rendering. If you think this is a Prism bug please report it on our Discord server:\nwww.prism-pipeline.com/discord\nor write a mail to contact@prism-pipeline.com"
                        self.core.popup(msg)
                    else:
                        if not result or (
                            "Could not connect to any of the specified Mongo DB servers defined in" not in result
                            and "ConcurrentTasks must be a value between 1 and 16 inclusive" not in result
                            and "does not exist or is not accessible from this computer" not in result
                            and "System.OutOfMemoryException" not in result
                        ):
                            self.core.writeErrorLog(erStr)

                return [self.state.text(0) + " - error - " + result]

    @err_catcher(name=__name__)
    def expandvars(self, path: str) -> str:
        """Expand environment variables in filepath.
        
        Args:
            path: Path potentially containing environment variables
            
        Returns:
            Expanded path string
        """
        if hasattr(self.core.appPlugin, "expandEnvVarsInFilepath"):
            expandedPath = self.core.appPlugin.expandEnvVarsInFilepath(path)
        else:
            expandedPath = os.path.expandvars(path)

        return expandedPath

    @err_catcher(name=__name__)
    def executeIdentifier(
        self,
        identifier: str,
        useVersion: str,
        context: Dict[str, Any],
        fileName: str,
        startFrame: Optional[int],
        endFrame: Optional[int],
        frames: Union[Tuple, List],
        rangeType: str,
        parent: Any,
        layer: Optional[str],
    ) -> Union[List[str], Dict[str, Any]]:
        """Execute rendering for a specific identifier and layer.
        
        Handles rendering setup, callbacks, and render execution for a single
        identifier/layer combination.
        
        Args:
            identifier: Task/identifier name
            useVersion: Version string to use
            context: Entity context dictionary
            fileName: Source scene filename
            startFrame: Start frame number
            endFrame: End frame number
            frames: Frame range or list
            rangeType: Type of frame range
            parent: Parent widget
            layer: Optional layer name
            
        Returns:
            Result dictionary with render settings and status, or error list
        """
        if self.tasknameRequired and not identifier:
            return [
                self.state.text(0)
                + ": error - no identifier is given. Skipped the activation of this state."
            ]

        if self.curCam is None or (
            self.curCam != "Current View"
            and not self.core.appPlugin.isNodeValid(self, self.curCam)
        ):
            return [
                self.state.text(0)
                + ": error - no camera is selected. Skipping activation of this state."
            ]

        outputName, outputPath, hVersion = self.getOutputName(useVersion=useVersion, identifier=identifier, layer=layer)
        expandedOutputPath = self.expandvars(outputPath)

        outLength = len(outputName)
        if platform.system() == "Windows" and os.getenv("PRISM_IGNORE_PATH_LENGTH") != "1" and outLength > 255:
            return [
                self.state.text(0)
                + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, identifier or projectpath."
                % outLength
            ]

        if not os.path.exists(os.path.dirname(expandedOutputPath)):
            os.makedirs(os.path.dirname(expandedOutputPath))

        details = context.copy()
        if "filename" in details:
            del details["filename"]

        if "extension" in details:
            del details["extension"]

        details["version"] = hVersion
        details["sourceScene"] = fileName
        details["identifier"] = identifier
        details["comment"] = self.getComment()
        details["startframe"] = startFrame
        details["endframe"] = endFrame
        if layer:
            details["layer"] = layer

        if self.mediaType == "3drenders":
            infopath = os.path.dirname(expandedOutputPath)
        else:
            infopath = expandedOutputPath

        self.core.saveVersionInfo(
            filepath=infopath, details=details
        )

        self.stateManager.saveStatesToScene()

        rSettings = {
            "outputName": outputName,
            "startFrame": startFrame,
            "endFrame": endFrame,
            "frames": frames,
            "rangeType": rangeType,
            "identifier": identifier,
        }
        if layer:
            rSettings["layer"] = layer

        if (
            self.chb_renderPreset.isChecked()
            and "RenderSettings" in self.stateManager.stateTypes
        ):
            rSettings["renderSettings"] = getattr(
                self.core.appPlugin,
                "sm_renderSettings_getCurrentSettings",
                lambda x: {},
            )(self)
            self.stateManager.stateTypes["RenderSettings"].applyPreset(
                self.core, self.renderPresets[self.cb_renderPreset.currentText()]
            )

        self.core.appPlugin.sm_render_preSubmit(self, rSettings)
        self.l_pathLast.setText(rSettings["outputName"])
        self.l_pathLast.setToolTip(rSettings["outputName"])

        kwargs = {
            "state": self,
            "scenefile": fileName,
            "settings": rSettings,
        }

        result = self.core.callback("preRender", **kwargs)
        for res in result:
            if isinstance(res, dict) and res.get("cancel", False):
                return [
                    self.state.text(0)
                    + " - error - %s" % res.get("details", "preRender hook returned False")
                ]

        if not os.path.exists(self.expandvars(os.path.dirname(rSettings["outputName"]))):
            try:
                os.makedirs(self.expandvars(os.path.dirname(rSettings["outputName"])))
            except:
                logger.debug("failed to create folder: " + self.expandvars(os.path.dirname(rSettings["outputName"])))

        if self.stateManager.actionSaveDuringPub.isChecked():
            self.core.saveScene(versionUp=False, prismReq=False)
        
        if self.core.getConfig("globals", "backupScenesOnPublish", config="project"):
            self.core.entities.backupScenefile(self.expandvars(os.path.dirname(rSettings["outputName"])), bufferMinutes=0)

        updateMaster = True
        if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
            handleMaster = "media" if self.isUsingMasterVersion() else False
            plugin = self.core.plugins.getRenderfarmPlugin(self.cb_manager.currentText())
            if hasattr(self, "chb_redshift") and self.chb_redshift.isChecked() and not self.w_redshift.isHidden():
                sceneDescription = "redshift"
            elif hasattr(self, "chb_vrscene") and self.chb_vrscene.isChecked() and not self.w_vrscene.isHidden():
                sceneDescription = "vray"
            else:
                sceneDescription = None

            submitExport = True
            if sceneDescription == "vray" and hasattr(self, "chb_exportSceneLocally") and self.chb_exportSceneLocally.isChecked():
                localResult = self.core.appPlugin.sm_render_startLocalRender(self, rSettings["outputName"], rSettings)
                vrsceneDir = os.path.join(os.path.dirname(rSettings["outputName"]), "_vrscene")
                vrsceneExported = os.path.exists(vrsceneDir) and bool(os.listdir(vrsceneDir))
                if localResult != "Result=Success" and not vrsceneExported:
                    resultData = {"result": localResult, "updateMaster": updateMaster, "rSettings": rSettings, "outputName": rSettings["outputName"], "details": details}
                    return resultData

                submitExport = False

            result = plugin.sm_render_submitJob(
                self,
                rSettings["outputName"],
                parent,
                handleMaster=handleMaster,
                details=details,
                sceneDescription=sceneDescription,
                skipSubmission=not submitExport,
            )
            updateMaster = False
        else:
            result = self.core.appPlugin.sm_render_startLocalRender(
                self, rSettings["outputName"], rSettings
            )

        resultData = {"result": result, "updateMaster": updateMaster, "rSettings": rSettings, "outputName": rSettings["outputName"], "details": details}
        return resultData

    @err_catcher(name=__name__)
    def isUsingMasterVersion(self) -> bool:
        """Check if master version updating is enabled.
        
        Returns:
            True if master version will be updated
        """
        useMaster = self.core.mediaProducts.getUseMaster()
        if not useMaster:
            return False

        masterAction = self.cb_master.currentText()
        if masterAction == "Don't update master":
            return False

        return True

    @err_catcher(name=__name__)
    def handleMasterVersion(self, outputName: str) -> None:
        """Update master version based on settings.
        
        Args:
            outputName: Path to the rendered output
        """
        if not self.isUsingMasterVersion():
            return

        masterAction = self.cb_master.currentText()
        if masterAction == "Set as master":
            self.core.mediaProducts.updateMasterVersion(outputName)
        elif masterAction == "Add to master":
            self.core.mediaProducts.addToMasterVersion(outputName)

    @err_catcher(name=__name__)
    def setTaskWarn(self, warn: bool) -> None:
        """Set visual warning state for task button.
        
        Args:
            warn: Whether to show warning styling
        """
        useSS = getattr(self.core.appPlugin, "colorButtonWithStyleSheet", False)
        if warn and self.f_taskname.isEnabled():
            if useSS:
                self.b_changeTask.setStyleSheet(
                    "QPushButton { background-color: rgb(200,0,0); }"
                )
            else:
                self.b_changeTask.setPalette(self.warnPalette)
        else:
            if useSS:
                self.b_changeTask.setStyleSheet("")
            else:
                self.b_changeTask.setPalette(self.oldPalette)

    @err_catcher(name=__name__)
    def getStateProps(self) -> Dict[str, Any]:
        """Get all state properties for saving.
        
        Returns:
            Dictionary containing all state settings and values
        """
        stateProps = {
            "stateName": self.e_name.text(),
            "contextType": self.getContextType(),
            "customContext": self.customContext,
            "identifier": self.getIdentifier(),
            "renderpresetoverride": str(self.chb_renderPreset.isChecked()),
            "currentrenderpreset": self.cb_renderPreset.currentText(),
            "rangeType": str(self.cb_rangeType.currentText()),
            "startframe": self.sp_rangeStart.value(),
            "endframe": self.sp_rangeEnd.value(),
            "frameExpression": self.le_frameExpression.text(),
            "currentcam": str(self.curCam),
            "resoverride": str(
                [
                    self.chb_resOverride.isChecked(),
                    self.sp_resWidth.value(),
                    self.sp_resHeight.value(),
                ]
            ),
            "masterVersion": self.cb_master.currentText(),
            "curoutputpath": self.cb_outPath.currentText(),
            "renderlayer": str(self.cb_renderLayer.currentText()),
            "outputFormat": str(self.cb_format.currentText()),
            "useVersionOverride": self.chb_version.isChecked(),
            "versionOverride": self.sp_version.value(),
            "submitrender": str(self.gb_submit.isChecked()),
            "rjmanager": str(self.cb_manager.currentText()),
            "rjprio": self.sp_rjPrio.value(),
            "rjframespertask": self.sp_rjFramesPerTask.value(),
            "rjtimeout": self.sp_rjTimeout.value(),
            "rjsuspended": str(self.chb_rjSuspended.isChecked()),
            "osdependencies": str(self.chb_osDependencies.isChecked()),
            "osupload": str(self.chb_osUpload.isChecked()),
            "ospassets": str(self.chb_osPAssets.isChecked()),
            "osslaves": self.e_osSlaves.text(),
            "dlconcurrent": self.sp_dlConcurrentTasks.value(),
            "dlgpupt": self.sp_dlGPUpt.value(),
            "dlgpudevices": self.le_dlGPUdevices.text(),
            "lastexportpath": self.l_pathLast.text().replace("\\", "/"),
            "enablepasses": str(self.gb_passes.isChecked()),
            "stateenabled": self.core.getCheckStateValue(self.state.checkState(0)),
        }
        self.core.callback("onStateGetSettings", self, stateProps)
        return stateProps
