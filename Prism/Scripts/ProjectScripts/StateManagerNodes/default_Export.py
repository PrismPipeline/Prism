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

from typing import Any, Optional, Dict, List, Tuple

import os
import sys
import time
import traceback
import platform
import logging

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class ExportClass(object):
    """State Manager node for exporting scene objects/geometry.
    
    Provides functionality to export selected objects or entire scenes to various
    file formats (FBX, OBJ, ABC, etc.). Supports context-based naming, version control,
    frame range selection, and render farm submission.
    
    Attributes:
        className (str): Node type identifier ("Export")
        listType (str): State list type ("Export")
        stateCategories (Dict): Category configuration for state manager
        core (Any): Reference to PrismCore instance
        state (Any): Reference to QTreeWidgetItem representing this state
        stateManager (Any): Reference to StateManager instance
        canSetVersion (bool): Whether this state supports version control
        customContext (Optional[Dict]): Custom entity context if set
        allowCustomContext (bool): Whether custom context is allowed
        shotCamsInitialized (bool): Whether shot camera list has been initialized
        curCam (Any): Currently selected camera
        nodes (List): List of scene nodes to export
        additionalSettings (List[Dict]): List of additional plugin-specific settings
    """
    className = "Export"
    listType = "Export"
    stateCategories = {"Export": [{"label": className, "stateType": className}]}

    @err_catcher(name=__name__)
    def setup(self, state: Any, core: Any, stateManager: Any, node: Optional[Any] = None, stateData: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the Export state.
        
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
        self.shotCamsInitialized = False

        self.e_name.setText(state.text(0) + " ({product})")

        self.l_name.setVisible(False)
        self.e_name.setVisible(False)
        self.gb_submit.setChecked(False)

        self.cb_context.addItems(["From scenefile", "Custom"])
        self.curCam = None
        self.chb_master.setChecked(os.getenv("PRISM_ENABLE_MASTER_DFT", "1") == "1")

        self.oldPalette = self.b_changeTask.palette()
        self.warnPalette = QPalette()
        self.warnPalette.setColor(QPalette.Button, QColor(200, 0, 0))
        self.warnPalette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        self.b_changeTask.setPalette(self.warnPalette)

        self.w_cam.setVisible(False)
        self.w_sCamShot.setVisible(False)
        self.w_selectCam.setVisible(False)
        self.additionalSettings = []
        self.b_additionalSettings = QPushButton("Additional Settings...")
        self.b_additionalSettings.clicked.connect(self.showAdditionalSettings)
        self.lo_export.insertWidget(self.lo_export.indexOf(self.gb_objects), self.b_additionalSettings)

        self.nodes = []

        self.rangeTypes = ["Scene", "Shot", "Shot + 1", "Single Frame", "Custom"]
        self.cb_rangeType.addItems(self.rangeTypes)
        for idx, rtype in enumerate(self.rangeTypes):
            self.cb_rangeType.setItemData(
                idx, self.stateManager.getFrameRangeTypeToolTip(rtype), Qt.ToolTipRole
            )

        if self.stateManager.standalone:
            outputFormats = []
            if self.core.appPlugin.pluginName != "Houdini" and hasattr(self.core.appPlugin, "outputFormats"):
                outputFormats += list(self.core.appPlugin.outputFormats)

            for i in self.core.unloadedAppPlugins.values():
                if i.pluginName != "Houdini":
                    outputFormats += getattr(i, "outputFormats", [])
            outputFormats = sorted(set(outputFormats))
        else:
            outputFormats = getattr(self.core.appPlugin, "outputFormats", [])

        self.cb_outType.addItems(outputFormats)
        self.export_paths = self.core.paths.getExportProductBasePaths()
        self.cb_outPath.addItems(list(self.export_paths.keys()))
        if len(self.export_paths) < 2:
            self.w_outPath.setVisible(False)

        if hasattr(self, "gb_submit"):
            self.gb_submit.setVisible(False)
            self.cb_manager.addItems([p.pluginName for p in self.core.plugins.getRenderfarmPlugins()])
            self.cb_manager.wheelEvent = lambda event: None

        self.cb_context.wheelEvent = lambda event: None
        self.cb_rangeType.wheelEvent = lambda event: None
        self.cb_cam.wheelEvent = lambda event: None
        self.cb_sCamShot.wheelEvent = lambda event: None
        self.cb_outPath.wheelEvent = lambda event: None
        self.cb_outType.wheelEvent = lambda event: None
        getattr(self.core.appPlugin, "sm_export_startup", lambda x: None)(self)
        self.nameChanged(state.text(0))
        self.connectEvents()

        self.core.callback("onStateStartup", self)
        self.f_rjWidgetsPerTask.setVisible(False)
        self.managerChanged(True)

        if stateData is not None:
            self.loadData(stateData)
        else:
            self.initializeContextBasedSettings()

        self.typeChanged(self.getOutputType())

    @err_catcher(name=__name__)
    def loadData(self, data: Dict[str, Any]) -> None:
        """Load state data from saved configuration.
        
        Restores all state settings including context, product name, objects,
        frame range, output format, and render farm settings.
        
        Args:
            data: Dictionary containing saved state configuration
        """
        if "contextType" in data:
            self.setContextType(data["contextType"])
        if "customContext" in data:
            self.customContext = data["customContext"]
        if "taskname" in data:
            self.setProductname(data["taskname"])
        if "productname" in data:
            self.setProductname(data["productname"])
        if "connectednodes" in data:
            self.nodes = eval(data["connectednodes"])

        self.updateUi()

        if "stateName" in data:
            self.e_name.setText(data["stateName"])
        elif "statename" in data:
            self.e_name.setText(data["statename"] + " ({product})")
        if "rangeType" in data:
            idx = self.cb_rangeType.findText(data["rangeType"])
            if idx != -1:
                self.cb_rangeType.setCurrentIndex(idx)
                self.updateRange()
        if "startframe" in data:
            self.sp_rangeStart.setValue(int(data["startframe"]))
        if "endframe" in data:
            self.sp_rangeEnd.setValue(int(data["endframe"]))
        if "updateMasterVersion" in data:
            self.chb_master.setChecked(data["updateMasterVersion"])
        if "curoutputpath" in data:
            idx = self.cb_outPath.findText(data["curoutputpath"])
            if idx != -1:
                self.cb_outPath.setCurrentIndex(idx)
        if "curoutputtype" in data:
            idx = self.cb_outType.findText(data["curoutputtype"])
            if idx != -1:
                self.cb_outType.setCurrentIndex(idx)
        if "wholescene" in data:
            self.chb_wholeScene.setChecked(eval(data["wholescene"]))
        if "additionaloptions" in data:
            self.chb_additionalOptions.setChecked(eval(data["additionaloptions"]))
        if "currentcam" in data:
            if not self.shotCamsInitialized:
                self.refreshShotCameras()

            camName = getattr(self.core.appPlugin, "getCamName", lambda x, y: "")(
                self, data["currentcam"]
            )
            idx = self.cb_cam.findText(camName)
            if idx != -1:
                self.curCam = self.camlist[idx]
                self.cb_cam.setCurrentIndex(idx)
                self.nameChanged(self.e_name.text())
        if "currentscamshot" in data:
            idx = self.cb_sCamShot.findText(data["currentscamshot"])
            if idx != -1:
                self.cb_sCamShot.setCurrentIndex(idx)
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
        if "dlconcurrent" in data:
            self.sp_dlConcurrentTasks.setValue(int(data["dlconcurrent"]))
        if "lastexportpath" in data:
            lePath = self.core.fixPath(data["lastexportpath"])
            self.setLastPath(lePath)
        if "stateenabled" in data:
            if type(data["stateenabled"]) == int:
                self.state.setCheckState(
                    0, Qt.CheckState(data["stateenabled"]),
                )
        if "additionalSettings" in data:
            for setting in data["additionalSettings"]:
                for asetting in self.additionalSettings:
                    if asetting["name"] == setting:
                        asetting["value"] = data["additionalSettings"][setting]

        getattr(self.core.appPlugin, "sm_export_loadData", lambda x, y: None)(
            self, data
        )
        self.core.callback("onStateSettingsLoaded", self, data)

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect Qt signals to their respective slot methods.
        
        Establishes connections between UI widgets and handler methods,
        including context selection, object management, frame range controls,
        and render farm submission options.
        """
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.cb_context.activated.connect(self.onContextTypeChanged)
        self.b_context.clicked.connect(self.selectContextClicked)
        self.b_changeTask.clicked.connect(self.changeTask)
        self.cb_rangeType.activated.connect(self.rangeTypeChanged)
        self.sp_rangeStart.editingFinished.connect(self.startChanged)
        self.sp_rangeEnd.editingFinished.connect(self.endChanged)
        self.chb_master.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.cb_outPath.activated.connect(self.stateManager.saveStatesToScene)
        self.cb_outType.currentIndexChanged.connect(lambda x: self.typeChanged(self.getOutputType()))
        self.chb_wholeScene.stateChanged.connect(self.wholeSceneChanged)
        self.chb_additionalOptions.stateChanged.connect(
            self.stateManager.saveStatesToScene
        )
        self.lw_objects.itemSelectionChanged.connect(
            lambda: self.core.appPlugin.selectNodes(self)
        )
        self.lw_objects.customContextMenuRequested.connect(self.rcObjects)
        self.cb_cam.activated.connect(self.setCam)
        self.cb_sCamShot.activated.connect(self.stateManager.saveStatesToScene)
        self.b_selectCam.clicked.connect(lambda: self.core.appPlugin.selectCam(self))
        self.gb_submit.toggled.connect(self.rjToggled)
        self.cb_manager.activated.connect(self.managerChanged)
        self.sp_rjPrio.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.sp_rjFramesPerTask.editingFinished.connect(
            self.stateManager.saveStatesToScene
        )
        self.sp_rjTimeout.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.chb_rjSuspended.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.sp_dlConcurrentTasks.editingFinished.connect(
            self.stateManager.saveStatesToScene
        )
        if not self.stateManager.standalone:
            self.b_add.clicked.connect(self.addObjects)
        self.b_pathLast.clicked.connect(lambda: self.stateManager.showLastPathMenu(self))

    @err_catcher(name=__name__)
    def initializeContextBasedSettings(self) -> None:
        """Initialize state settings based on current context.
        
        Sets default frame range, product name, and adds objects based on
        whether the scene is an asset, shot, or scene-based context.
        """
        context = self.getCurrentContext()
        startFrame, endFrame = self.getFrameRange("Scene")
        if startFrame is not None:
            self.sp_rangeStart.setValue(startFrame)

        if endFrame is not None:
            self.sp_rangeEnd.setValue(endFrame)

        if context.get("type") == "asset":
            self.setRangeType("Single Frame")
            self.sp_rangeEnd.setValue(startFrame)
        elif context.get("type") == "shot":
            self.setRangeType("Shot")
        elif self.stateManager.standalone:
            self.setRangeType("Custom")
        else:
            self.setRangeType("Scene")

        if context.get("task"):
            self.setProductname(context.get("task"))

        getattr(self.core.appPlugin, "sm_export_updateObjects", lambda x: None)(
            self
        )

        if not self.stateManager.standalone:
            self.addObjects()

    @err_catcher(name=__name__)
    def getLastPathOptions(self) -> Optional[List[Dict[str, Any]]]:
        """Get context menu options for the last export path.
        
        Returns:
            List of menu options with labels and callbacks, or None if no path exists
        """
        path = self.l_pathLast.text()
        if path == "None":
            return

        options = [
            {
                "label": "Open in Product Browser...",
                "callback": lambda: self.openInProductBrowser(path)
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
    def showAdditionalSettings(self) -> None:
        """Show additional settings dialog.
        
        Displays a dialog with plugin-specific additional export settings.
        """
        self.dlg_additionalSettings = AdditionalSettingsDialog(self)
        self.dlg_additionalSettings.show()

    @err_catcher(name=__name__)
    def openInProductBrowser(self, path: str) -> None:
        """Open the specified export in the Product Browser.
        
        Args:
            path: File path to the exported product
        """
        self.core.projectBrowser()
        self.core.pb.showTab("Products")
        data = self.core.paths.getCachePathData(path)
        self.core.pb.productBrowser.navigateToVersion(version=data["version"], product=data["product"], entity=data)

    @err_catcher(name=__name__)
    def selectContextClicked(self) -> None:
        """Open entity selector dialog for custom context.
        
        Allows user to select a custom entity (asset/shot) for export context.
        """
        self.dlg_entity = self.stateManager.entityDlg(self)
        data = self.getCurrentContext()
        self.dlg_entity.w_entities.navigate(data)
        self.dlg_entity.entitySelected.connect(lambda x: self.setCustomContext(x))
        self.dlg_entity.show()

    @err_catcher(name=__name__)
    def setCustomContext(self, context: Dict[str, Any]) -> None:
        """Set a custom export context.
        
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
        self.updateRange()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def wholeSceneChanged(self, state: int) -> None:
        """Handle whole scene checkbox state change.
        
        Args:
            state: Qt checkbox state
        """
        if self.w_wholeScene.isHidden():
            enabled = True
        else:
            enabled = not state == Qt.Checked

        self.gb_objects.setEnabled(enabled)
        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def nameChanged(self, text: str) -> None:
        """Handle changes to the state name.
        
        Formats name with product context and ensures uniqueness among states.
        
        Args:
            text: New name text
        """
        text = self.e_name.text()
        context = {}
        if self.getOutputType() == "ShotCam":
            context["product"] = "ShotCam - %s" % self.cb_cam.currentText()
        else:
            context["product"] = self.getProductname() or "None"

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
    def getUpdateMasterVersion(self) -> bool:
        """Get whether master version will be updated.
        
        Returns:
            True if master version updating is enabled
        """
        return self.chb_master.isChecked()

    @err_catcher(name=__name__)
    def setUpdateMasterVersion(self, master: bool) -> None:
        """Set whether master version will be updated.
        
        Args:
            master: Whether to update master version
        """
        self.chb_master.setChecked(master)

    @err_catcher(name=__name__)
    def getOutputType(self) -> str:
        """Get the current export output type/format.
        
        Returns:
            Current output type string (e.g., ".fbx", ".obj", "ShotCam")
        """
        return self.cb_outType.currentText()

    @err_catcher(name=__name__)
    def setOutputType(self, outType: str) -> None:
        """Set the export output type/format.
        
        Args:
            outType: Output type to set
        """
        idx = self.cb_outType.findText(outType)
        if idx != -1:
            self.cb_outType.setCurrentIndex(idx)

    @err_catcher(name=__name__)
    def getContextType(self) -> str:
        """Get the current context type.
        
        Returns:
            Context type string ("From scenefile" or "Custom")
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
    def getProductname(self) -> str:
        """Get the current product name.
        
        Returns:
            Product name string
        """
        if self.getOutputType() == "ShotCam":
            productName = "_ShotCam"
        else:
            productName = self.l_taskName.text().strip()

        return productName

    @err_catcher(name=__name__)
    def getTaskname(self) -> str:
        """Get the task name (alias for getProductname).
        
        Returns:
            Product/task name string
        """
        return self.getProductname()

    @err_catcher(name=__name__)
    def setProductname(self, productname: str) -> str:
        """Set the product name.
        
        Args:
            productname: Product name to set
            
        Returns:
            The final product name after any plugin modifications
        """
        newProductName = productname.strip()
        prevProductName = self.getProductname()
        default_func = lambda x1, x2, newTaskName: newProductName
        productname = getattr(self.core.appPlugin, "sm_export_setTaskText", default_func)(
            self, prevProductName, newProductName
        )
        self.l_taskName.setText(productname)
        if not self.stateManager.loading:
            self.updateUi()

        return productname

    @err_catcher(name=__name__)
    def setTaskname(self, taskname: str) -> str:
        """Set the task name (alias for setProductname).
        
        Args:
            taskname: Task name to set
            
        Returns:
            The final product name after setting
        """
        return self.setProductname(taskname)

    @err_catcher(name=__name__)
    def getSortKey(self) -> str:
        """Get the sorting key for this state.
        
        Returns:
            Product name used for sorting states
        """
        return self.getProductname()

    @err_catcher(name=__name__)
    def changeTask(self) -> None:
        """Open dialog to change the product name with tag support.
        
        Shows a dialog with task suggestions and tag management for the product.
        """
        from PrismUtils import PrismWidgets
        self.nameWin = PrismWidgets.CreateItem(
            startText=self.getProductname(),
            showTasks=True,
            taskType="export",
            core=self.core,
        )
        self.core.parentWindow(self.nameWin)
        self.nameWin.setWindowTitle("Change Productname")
        self.nameWin.l_item.setText("Productname:")
        self.nameWin.buttonBox.buttons()[0].setText("Ok")
        if not self.stateManager.standalone:
            self.nameWin.w_tags = QWidget()
            self.nameWin.lo_tags = QHBoxLayout(self.nameWin.w_tags)
            self.nameWin.lo_tags.setContentsMargins(9, 0, 9, 0)
            self.nameWin.l_tagLabel = QLabel("Tags:               ")
            self.nameWin.e_tags = QLineEdit()
            self.nameWin.b_editTags = QPushButton(u"\u25bc")
            self.nameWin.b_editTags.setToolTip("Recommended Tags")
            self.nameWin.b_editTags.setMaximumSize(QSize(30, 16777215))
            self.nameWin.lo_tags.addWidget(self.nameWin.l_tagLabel)
            self.nameWin.lo_tags.addWidget(self.nameWin.e_tags)
            self.nameWin.lo_tags.addWidget(self.nameWin.b_editTags)
            self.nameWin.layout().insertWidget(2, self.nameWin.w_tags)
            self.nameWin.b_editTags.clicked.connect(self.showRecommendedTags)

        self.nameWin.e_item.textChanged.connect(self.onProductNameChanged)        
        self.onProductNameChanged()
        self.nameWin.e_item.selectAll()
        result = self.nameWin.exec_()

        if result == 1:
            product = self.nameWin.e_item.text()
            self.setProductname(product)
            if not self.stateManager.standalone:
                tags = [t.strip() for t in self.nameWin.e_tags.text().split(",")]
                ctx = self.getCurrentContext().copy()
                if ctx and ctx.get("type"):
                    ctx["product"] = product
                    self.core.products.setProductTags(ctx, tags)

            self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def onProductNameChanged(self, text: Optional[str] = None) -> None:
        """Handle product name changes in the dialog.
        
        Updates tag display based on the new product name.
        
        Args:
            text: New product name text (unused)
        """
        product = self.nameWin.e_item.text()
        ctx = self.getCurrentContext().copy()
        ctx["product"] = product
        if not self.stateManager.standalone:
            tags = self.core.products.getTagsFromProduct(ctx)
            self.nameWin.e_tags.setText(", ".join(tags))

    @err_catcher(name=__name__)
    def showRecommendedTags(self) -> None:
        """Show menu with recommended product tags.
        
        Displays context menu with tags appropriate for the current context.
        """
        tmenu = QMenu(self)

        tags = self.core.products.getRecommendedTags(self.getCurrentContext())
        for tag in tags:
            tAct = QAction(tag, self)
            tAct.triggered.connect(lambda x=None, t=tag: self.toggleTag(t))
            tmenu.addAction(tAct)

        tmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def toggleTag(self, tag: str) -> None:
        """Toggle a tag in the tag list.
        
        Args:
            tag: Tag string to add or remove
        """
        tags = [t.strip() for t in self.nameWin.e_tags.text().split(",")]
        if tag in tags:
            tags = [t for t in tags if t != tag]
        else:
            tags.append(tag)

        tags = [t for t in tags if t]
        self.nameWin.e_tags.setText(", ".join(tags))

    @err_catcher(name=__name__)
    def preDelete(self, item: Any) -> None:
        """Cleanup before state deletion.
        
        Args:
            item: State item being deleted
        """
        getattr(self.core.appPlugin, "sm_export_preDelete", lambda x: None)(self)

    @err_catcher(name=__name__)
    def rcObjects(self, pos: QPoint) -> None:
        """Show context menu for objects list.
        
        Args:
            pos: Position where context menu was requested
        """
        item = self.lw_objects.itemAt(pos)

        if item is None:
            self.lw_objects.setCurrentRow(-1)

        createMenu = QMenu()

        if item is not None:
            actRemove = QAction("Remove", self)
            actRemove.triggered.connect(lambda: self.removeItem(item))
            createMenu.addAction(actRemove)
        else:
            self.lw_objects.setCurrentRow(-1)

        actClear = QAction("Clear", self)
        actClear.triggered.connect(self.clearItems)
        createMenu.addAction(actClear)

        self.updateUi()
        createMenu.exec_(self.lw_objects.mapToGlobal(pos))

    @err_catcher(name=__name__)
    def addObjects(self, objects: Optional[List[Any]] = None) -> None:
        """Add objects to the export list.
        
        Args:
            objects: Optional list of objects to add (uses selection if None)
        """
        self.core.appPlugin.sm_export_addObjects(self, objects)
        self.updateObjectList()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def removeItem(self, item: QListWidgetItem) -> None:
        """Remove selected items from export list.
        
        Args:
            item: List widget item to remove
        """
        items = self.lw_objects.selectedItems()
        for item in reversed(items):
            rowNum = self.lw_objects.row(item)
            getattr(self.core.appPlugin, "sm_export_removeSetItem", lambda x, y: None)(self, self.nodes[rowNum])
            del self.nodes[rowNum]
            self.lw_objects.takeItem(rowNum)

        self.updateObjectList()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def clearItems(self) -> None:
        """Clear all items from the export list.
        """
        self.lw_objects.clear()
        self.nodes = []
        if not self.stateManager.standalone:
            getattr(self.core.appPlugin, "sm_export_clearSet", lambda x: None)(self)

        self.updateObjectList()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def refreshShotCameras(self) -> None:
        """Refresh the list of available shot cameras.
        
        Updates the shot camera combo box with current project shots.
        """
        curShot = self.cb_sCamShot.currentText()
        self.cb_sCamShot.clear()
        shots = self.core.entities.getShots()
        for shot in sorted(shots, key=lambda s: self.core.entities.getShotName(s).lower()):
            shotData = {"type": "shot", "sequence": shot["sequence"], "shot": shot["shot"]}
            if "episode" in shot:
                shotData["episode"] = shot["episode"]

            shotName = self.core.entities.getShotName(shot)
            self.cb_sCamShot.addItem(shotName, shotData)

        idx = self.cb_sCamShot.findText(curShot)
        if idx != -1:
            self.cb_sCamShot.setCurrentIndex(idx)
        else:
            self.cb_sCamShot.setCurrentIndex(0)
            self.stateManager.saveStatesToScene()

        if not self.shotCamsInitialized:
            context = self.getCurrentContext()
            if (
                context.get("type") == "shot"
                and "sequence" in context
            ):
                shotName = self.core.entities.getShotName(context)
                idx = self.cb_sCamShot.findText(shotName)
                if idx != -1:
                    self.cb_sCamShot.setCurrentIndex(idx)
                    self.stateManager.saveStatesToScene()

            self.shotCamsInitialized = True

    @err_catcher(name=__name__)
    def updateUi(self) -> None:
        """Update the user interface with current state.
        
        Refreshes cameras, context, object list, and other UI elements.
        """
        self.cb_cam.clear()
        self.camlist = camNames = []
        if not self.stateManager.standalone and hasattr(self.core.appPlugin, "getCamNodes"):
            self.camlist = self.core.appPlugin.getCamNodes(self)
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

        if not self.core.products.getUseMaster():
            self.w_master.setVisible(False)

        self.w_context.setHidden(not self.allowCustomContext)
        self.w_comment.setHidden(not self.stateManager.useStateComments())
        self.refreshContext()
        self.updateRange()
        if self.getOutputType() == "ShotCam":
            self.refreshShotCameras()

        self.updateObjectList()

        if self.getProductname():
            self.b_changeTask.setPalette(self.oldPalette)

        self.refreshSubmitUi()
        showSettings = any([setting.get("visible", lambda dlg, state: True)(None, self) for setting in self.additionalSettings])
        self.b_additionalSettings.setHidden(not showSettings)
        self.nameChanged(self.e_name.text())
        self.core.callback("sm_export_updateUi", self)

    @err_catcher(name=__name__)
    def updateObjectList(self) -> None:
        """Update the export objects list display.
        
        Refreshes the list widget with current valid nodes.
        """
        selObjects = [x.text() for x in self.lw_objects.selectedItems()]
        self.lw_objects.clear()

        newObjList = []
        result = getattr(self.core.appPlugin, "sm_export_updateObjects", lambda x: None)(self)
        if result is False:
            return

        if not self.stateManager.standalone:
            for node in self.nodes:
                if self.core.appPlugin.isNodeValid(self, node):
                    item = QListWidgetItem(self.core.appPlugin.getNodeName(self, node))
                    self.lw_objects.addItem(item)
                    newObjList.append(node)

        self.updateObjectListStyle()
        for i in range(self.lw_objects.count()):
            if self.lw_objects.item(i).text() in selObjects:
                self.lw_objects.item(i).setSelected(True)

        self.nodes = newObjList

    @err_catcher(name=__name__)
    def refreshContext(self) -> None:
        """Refresh the context display.
        
        Updates the context label with current entity information.
        """
        context = self.getCurrentContext()
        contextStr = self.getContextStrFromEntity(context)
        self.l_context.setText(contextStr)
        if contextStr:
            self.b_context.setPalette(self.oldPalette)
        else:
            self.b_context.setPalette(self.warnPalette)

    @err_catcher(name=__name__)
    def getCurrentContext(self) -> Dict[str, Any]:
        """Get the current export context.
        
        Returns:
            Dictionary containing entity context (type, asset, shot, etc.)
        """
        context = {}
        if self.allowCustomContext:
            ctype = self.getContextType()
            if ctype == "Custom":
                context = self.customContext

        if not context:
            if self.getOutputType() == "ShotCam":
                if self.shotCamsInitialized:
                    context = self.cb_sCamShot.currentData()
                else:
                    fileName = self.core.getCurrentFileName()
                    context = self.core.getScenefileData(fileName)

                if context and self.core.getConfig("globals", "productTasks", config="project"):
                    context["department"] = os.getenv("PRISM_SHOTCAM_DEPARTMENT", "Layout")
                    context["task"] = os.getenv("PRISM_SHOTCAM_TASK", "Cameras")

            else:
                fileName = self.core.getCurrentFileName()
                context = self.core.getScenefileData(fileName)

        if context and "username" in context:
            del context["username"]

        if context and "user" in context:
            del context["user"]

        return context or {}

    @err_catcher(name=__name__)
    def updateObjectListStyle(self, warn: bool = True) -> None:
        """Update object list visual styling based on validation.
        
        Args:
            warn: Whether to show warning style
        """
        if self.lw_objects.count() == 0 and not self.chb_wholeScene.isChecked() and self.lw_objects.isEnabled():
            self.setObjectListStyle(warn=True)
        else:
            self.setObjectListStyle(warn=False)

    @err_catcher(name=__name__)
    def setObjectListStyle(self, warn: bool = True) -> None:
        """Set object list visual styling.
        
        Args:
            warn: Whether to apply warning styling
        """
        if warn:
            getattr(
                self.core.appPlugin,
                "sm_export_colorObjList",
                lambda x: self.lw_objects.setStyleSheet(
                    "QListWidget { border: 3px solid rgb(200,0,0); }"
                ),
            )(self)
        else:
            getattr(
                self.core.appPlugin,
                "sm_export_unColorObjList",
                lambda x: self.lw_objects.setStyleSheet(
                    "QListWidget { border: 3px solid rgba(114,114,114,0); }"
                ),
            )(self)

    @err_catcher(name=__name__)
    def refreshSubmitUi(self) -> None:
        """Refresh the render farm submission UI elements.
        
        Updates visibility and state of renderfarm-related controls.
        """
        if not self.gb_submit.isHidden():
            if not self.gb_submit.isCheckable():
                return

            submitChecked = self.gb_submit.isChecked()
            for idx in reversed(range(self.gb_submit.layout().count())):
                self.gb_submit.layout().itemAt(idx).widget().setHidden(not submitChecked)

            if submitChecked:
                plug = self.core.plugins.getRenderfarmPlugin(self.cb_manager.currentText())
                if plug:
                    plug.sm_render_updateUI(self)

    @err_catcher(name=__name__)
    def updateRange(self) -> None:
        """Update the frame range display based on current range type.
        
        Shows/hides appropriate controls and updates range values.
        """
        rangeType = self.cb_rangeType.currentText()
        isCustom = rangeType == "Custom"
        self.l_rangeStart.setVisible(not isCustom)
        self.l_rangeEnd.setVisible(not isCustom)
        self.sp_rangeStart.setVisible(isCustom)
        self.sp_rangeEnd.setVisible(isCustom)

        if not isCustom:
            frange = self.getFrameRange(rangeType=rangeType)
            start = str(int(frange[0])) if frange[0] is not None else "-"
            end = str(int(frange[1])) if frange[1] is not None else "-"
            self.l_rangeStart.setText(start)
            self.l_rangeEnd.setText(end)

    @err_catcher(name=__name__)
    def getFrameRange(self, rangeType: str) -> Tuple[Optional[int], Optional[int]]:
        """Get the frame range for the specified range type.
        
        Args:
            rangeType: Type of range ("Scene", "Shot", "Shot + 1", "Single Frame", "Custom")
            
        Returns:
            Tuple of (start_frame, end_frame)
        """
        startFrame = None
        endFrame = None
        if rangeType == "Scene":
            if hasattr(self.core.appPlugin, "getFrameRange"):
                startFrame, endFrame = self.core.appPlugin.getFrameRange(self)
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
                startFrame = self.core.appPlugin.getCurrentFrame()
            else:
                startFrame = 1001
        elif rangeType == "Custom":
            startFrame = self.sp_rangeStart.value()
            endFrame = self.sp_rangeEnd.value()

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
    def typeChanged(self, idx: str) -> None:
        """Handle export type/format selection change.
        
        Args:
            idx: New export type string
        """
        isSCam = idx == "ShotCam"
        isOtio = idx == ".otio"
        self.w_cam.setVisible(isSCam)
        self.w_sCamShot.setVisible(isSCam)
        self.w_selectCam.setVisible(isSCam)
        self.w_taskname.setVisible(not isSCam)
        getattr(self.core.appPlugin, "sm_export_typeChanged", lambda x, y: None)(
            self, idx
        )
        self.w_wholeScene.setVisible(not isSCam and not isOtio)
        self.gb_objects.setVisible(not isSCam and not isOtio)

        if not self.stateManager.loading:
            self.updateUi()
            self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def setCam(self, index: int) -> None:
        """Set the active camera for shot cam export.
        
        Args:
            index: Camera index in the camera list
        """
        self.curCam = self.camlist[index]
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
            plugin.sm_export_managerChanged(self)

        self.cb_manager.prevManager = plugin
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def setLastPath(self, path: str) -> None:
        """Update the last export path display.
        
        Args:
            path: Path to display as last export
        """
        self.l_pathLast.setText(path)
        self.l_pathLast.setToolTip(path)
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

        rangeType = self.cb_rangeType.currentText()
        startFrame, endFrame = self.getFrameRange(rangeType)

        if self.getOutputType() == "ShotCam":
            if self.curCam is None:
                warnings.append(["No camera specified.", "", 3])
        else:
            if not self.getProductname():
                warnings.append(["No productname is given.", "", 3])

            if not self.chb_wholeScene.isChecked() and len(self.nodes) == 0 and self.getOutputType() not in [".otio"]:
                warnings.append(["No objects are selected for export.", "", 3])

        if startFrame is None:
            warnings.append(["Framerange is invalid.", "", 3])

        warnings += self.core.appPlugin.sm_export_preExecute(self, startFrame, endFrame)

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def getOutputName(self, useVersion: str = "next") -> Optional[Tuple[str, str, str]]:
        """Generate the output filename and path for the export.
        
        Args:
            useVersion: Version to use ("next" for auto-increment, or specific version)
            
        Returns:
            Tuple of (output_path, output_folder, version) or None if invalid
        """
        context = self.getCurrentContext()
        location = self.cb_outPath.currentText()
        version = useVersion if useVersion != "next" else None
        if "type" not in context:
            return

        product = self.getProductname()
        if not product:
            return

        if self.getOutputType() == "ShotCam":
            context["entityType"] = "shot"
            context["type"] = "shot"
            if "asset_path" in context:
                del context["asset_path"]

            if "asset" in context:
                del context["asset"]

            extension = ""
            framePadding = None
        else:
            rangeType = self.cb_rangeType.currentText()
            extension = self.getOutputType()

            if rangeType == "Single Frame" or extension != ".obj":
                framePadding = ""
            else:
                framePadding = "#" * self.core.framePadding

        outputPathData = self.core.products.generateProductPath(
            entity=context,
            task=product,
            extension=extension,
            framePadding=framePadding,
            comment=self.getComment(),
            version=version,
            location=location,
            returnDetails=True,
        )

        outputFolder = os.path.dirname(outputPathData["path"])
        hVersion = outputPathData["version"]

        return outputPathData["path"], outputFolder, hVersion

    @err_catcher(name=__name__)
    def isUsingMasterVersion(self) -> bool:
        """Check if master version updating is enabled.
        
        Returns:
            True if master version will be updated
        """
        useMaster = self.core.products.getUseMaster()
        if not useMaster:
            return False

        return useMaster and self.getUpdateMasterVersion()

    @err_catcher(name=__name__)
    def handleMasterVersion(self, outputName: str) -> None:
        """Update master version if enabled.
        
        Args:
            outputName: Path to the exported output
        """
        if not self.isUsingMasterVersion():
            return

        self.core.products.updateMasterVersion(outputName)

    @err_catcher(name=__name__)
    def getComment(self) -> str:
        """Get the current comment for the export.
        
        Returns:
            Comment string (from state or state manager)
        """
        if self.stateManager.useStateComments():
            comment = self.e_comment.text() or self.stateManager.publishComment
        else:
            comment = self.stateManager.publishComment

        return comment

    @err_catcher(name=__name__)
    def executeState(self, parent: Any, useVersion: str = "next") -> List[str]:
        """Execute the export operation.
        
        Exports selected objects/scene to file, handles shot cameras specially,
        submits to render farm if enabled, and manages master version.
        
        Args:
            parent: Parent widget for dialogs
            useVersion: Version to use for output
            
        Returns:
            List containing result message string
        """
        rangeType = self.cb_rangeType.currentText()
        startFrame, endFrame = self.getFrameRange(rangeType)
        if startFrame is None:
            return [self.state.text(0) + ": error - Framerange is invalid"]

        if rangeType == "Single Frame":
            endFrame = startFrame

        if self.getOutputType() == "ShotCam":
            if self.curCam is None:
                return [
                    self.state.text(0)
                    + ": error - No camera specified. Skipped the activation of this state."
                ]

            if self.cb_sCamShot.currentText() == "":
                return [
                    self.state.text(0)
                    + ": error - No Shot specified. Skipped the activation of this state."
                ]

            fileName = self.core.getCurrentFileName()
            context = self.getCurrentContext()
            outputName, outputPath, hVersion = self.getOutputName(useVersion=useVersion)

            outLength = len(outputName)
            if platform.system() == "Windows" and os.getenv("PRISM_IGNORE_PATH_LENGTH") != "1" and outLength > 255:
                return [
                    self.state.text(0)
                    + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, taskname or projectpath."
                    % outLength
                ]

            kwargs = {
                "state": self,
                "scenefile": fileName,
                "startframe": startFrame,
                "endframe": endFrame,
                "outputpath": outputName,
                "version": hVersion,
            }

            result = self.core.callback("preExport", **kwargs)
            for res in result:
                if isinstance(res, dict) and res.get("cancel", False):
                    return [
                        self.state.text(0)
                        + " - error - %s" % res.get("details", "preExport hook returned False")
                    ]

                if res and "outputName" in res:
                    outputName = res["outputName"]

                if res and "version" in res:
                    hVersion = res["version"]

            outputPath = os.path.dirname(outputName)
            if not os.path.exists(outputPath):
                os.makedirs(outputPath)

            details = context.copy()
            if "filename" in details:
                del details["filename"]

            if "extension" in details:
                del details["extension"]

            details["version"] = hVersion
            details["sourceScene"] = fileName
            details["product"] = self.getProductname()
            details["resolution"] = self.core.appPlugin.getResolution()
            details["comment"] = self.getComment()

            details.update(self.cb_sCamShot.currentData())
            details["entityType"] = "shot"
            details["type"] = "shot"
            if "asset_path" in details:
                del details["asset_path"]

            if startFrame != endFrame:
                details["fps"] = self.core.getFPS()

            infoPath = self.core.products.getVersionInfoPathFromProductFilepath(
                outputName
            )
            self.core.saveVersionInfo(filepath=infoPath, details=details)

            self.core.appPlugin.sm_export_exportShotcam(
                self, startFrame=startFrame, endFrame=endFrame, outputName=outputName
            )

            outputName += ".abc"
            self.setLastPath(outputName)

            useMaster = self.core.products.getUseMaster()
            if useMaster and self.getUpdateMasterVersion():
                self.core.products.updateMasterVersion(outputName)

            kwargs = {
                "state": self,
                "scenefile": fileName,
                "startframe": startFrame,
                "endframe": endFrame,
                "outputpath": outputName,
            }

            result = self.core.callback("postExport", **kwargs)
            validateOutput = True
            for res in result:
                if isinstance(res, dict) and res.get("cancel", False):
                    return [
                        self.state.text(0)
                        + " - error - %s" % res.get("details", "postExport hook returned False")
                    ]

                if res and "outputName" in res:
                    outputName = res["outputName"]

                if res and "validateOutput" in res:
                    validateOutput = res["validateOutput"]

            self.stateManager.saveStatesToScene()

            if not validateOutput or os.path.exists(outputName):
                return [self.state.text(0) + " - success"]
            else:
                return [self.state.text(0) + " - unknown error"]
        else:

            if not self.getProductname():
                return [
                    self.state.text(0)
                    + ": error - No productname is given. Skipped the activation of this state."
                ]

            if (
                not self.chb_wholeScene.isChecked()
                and len(
                    [x for x in self.nodes if self.core.appPlugin.isNodeValid(self, x)]
                )
                == 0
                and self.getOutputType() not in [".otio"]
            ):
                return [
                    self.state.text(0)
                    + ": error - No objects chosen. Skipped the activation of this state."
                ]

            fileName = self.core.getCurrentFileName()
            context = self.getCurrentContext()
            outputName, outputPath, hVersion = self.getOutputName(useVersion=useVersion)

            outLength = len(outputName)
            if platform.system() == "Windows" and os.getenv("PRISM_IGNORE_PATH_LENGTH") != "1" and outLength > 255:
                return [
                    self.state.text(0)
                    + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, taskname or projectpath."
                    % outLength
                ]

            kwargs = {
                "state": self,
                "scenefile": fileName,
                "startframe": startFrame,
                "endframe": endFrame,
                "outputpath": outputName,
            }
            extraVersionInfo = {}
            result = self.core.callback("preExport", **kwargs)
            for res in result:
                if isinstance(res, dict) and res.get("cancel", False):
                    return [
                        self.state.text(0)
                        + " - error - %s" % res.get("details", "preExport hook returned False")
                    ]
                
                if res and "outputName" in res:
                    outputName = res["outputName"]

                if res and "extraVersionInfo" in res:
                    extraVersionInfo.update(res["extraVersionInfo"])

            outputPath = os.path.dirname(outputName)
            if not os.path.exists(outputPath):
                os.makedirs(outputPath)

            details = context.copy()
            if "filename" in details:
                del details["filename"]

            if "extension" in details:
                del details["extension"]

            details["version"] = hVersion
            details["sourceScene"] = fileName
            details["product"] = self.getProductname()
            details["comment"] = self.getComment()

            if startFrame != endFrame:
                details["fps"] = self.core.getFPS()

            details.update(extraVersionInfo)
            infoPath = self.core.products.getVersionInfoPathFromProductFilepath(
                outputName
            )
            self.core.saveVersionInfo(filepath=infoPath, details=details)
            if self.core.products.getUseProductPreviews():
                preview = self.core.products.generateProductPreview()
                if preview:
                    self.core.products.setProductPreview(os.path.dirname(outputName), preview)

            updateMaster = True
            try:
                submitResult = None
                if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
                    handleMaster = "product" if self.isUsingMasterVersion() else False
                    plugin = self.core.plugins.getRenderfarmPlugin(self.cb_manager.currentText())
                    submitResult = plugin.sm_render_submitJob(self, outputName, parent, handleMaster=handleMaster, details=details)
                    updateMaster = False
                else:
                    outputName = self.core.appPlugin.sm_export_exportAppObjects(
                        self,
                        startFrame=startFrame,
                        endFrame=endFrame,
                        outputName=outputName,
                    )

                    if not outputName:
                        return [self.state.text(0) + " - error"]

                    if outputName.startswith("Canceled"):
                        return [self.state.text(0) + " - error: %s" % outputName]

                logger.debug("exported to: %s" % outputName)
                self.setLastPath(outputName)
                self.stateManager.saveStatesToScene()

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "%s ERROR - sm_default_export %s:\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    self.core.version,
                    traceback.format_exc(),
                )
                self.core.writeErrorLog(erStr)
                return [
                    self.state.text(0)
                    + " - unknown error (view console for more information)"
                ]

            if updateMaster:
                self.handleMasterVersion(outputName)

            kwargs = {
                "state": self,
                "scenefile": fileName,
                "startframe": startFrame,
                "endframe": endFrame,
                "outputpath": outputName,
                "result": submitResult,
            }

            result = self.core.callback("postExport", **kwargs)
            validateOutput = True
            for res in result:
                if res:
                    if res and "outputName" in res:
                        outputName = res["outputName"]

                    if res and "validateOutput" in res:
                        validateOutput = res["validateOutput"]

            if not self.gb_submit.isHidden() and self.gb_submit.isChecked() and "Result=Success" in submitResult:
                return [self.state.text(0) + " - success"]
            elif os.path.exists(outputName) or self.core.media.getFilesFromSequence(outputName) or not validateOutput:
                return [self.state.text(0) + " - success"]
            else:
                return [self.state.text(0) + " - unknown error (files do not exist)"]

    @err_catcher(name=__name__)
    def getStateProps(self) -> Dict[str, Any]:
        """Get all state properties for saving.
        
        Returns:
            Dictionary containing all state settings and values
        """
        stateProps = {}

        nodes = []
        if not self.stateManager.standalone:
            for node in self.nodes:
                if self.core.appPlugin.isNodeValid(self, node):
                    nodes.append(node)

        stateProps.update(
            {
                "stateName": self.e_name.text(),
                "contextType": self.getContextType(),
                "customContext": self.customContext,
                "productname": self.getProductname(),
                "rangeType": str(self.cb_rangeType.currentText()),
                "startframe": self.sp_rangeStart.value(),
                "endframe": self.sp_rangeEnd.value(),
                "additionaloptions": str(self.chb_additionalOptions.isChecked()),
                "updateMasterVersion": self.chb_master.isChecked(),
                "curoutputpath": self.cb_outPath.currentText(),
                "curoutputtype": self.getOutputType(),
                "wholescene": str(self.chb_wholeScene.isChecked()),
                "connectednodes": str(nodes),
                "currentcam": str(self.curCam),
                "currentscamshot": self.cb_sCamShot.currentText(),
                "submitrender": str(self.gb_submit.isChecked()),
                "rjmanager": str(self.cb_manager.currentText()),
                "rjprio": self.sp_rjPrio.value(),
                "rjframespertask": self.sp_rjFramesPerTask.value(),
                "rjtimeout": self.sp_rjTimeout.value(),
                "rjsuspended": str(self.chb_rjSuspended.isChecked()),
                "dlconcurrent": self.sp_dlConcurrentTasks.value(),
                "lastexportpath": self.l_pathLast.text().replace("\\", "/"),
                "stateenabled": self.core.getCheckStateValue(self.state.checkState(0)),
                "additionalSettings": {s["name"]: s["value"] for s in self.additionalSettings}
            }
        )
        getattr(self.core.appPlugin, "sm_export_getStateProps", lambda x, y: None)(
            self, stateProps
        )
        self.core.callback("onStateGetSettings", self, stateProps)
        return stateProps


class AdditionalSettingsDialog(QDialog):
    """Dialog for managing additional export settings.
    
    Provides a UI for plugin-specific additional settings that may be
    conditionally visible based on other state settings.
    
    Attributes:
        state (ExportClass): Parent export state
        core (Any): PrismCore instance
        widgets (List[Dict]): List of widget configuration dictionaries
    """
    def __init__(self, state: Any) -> None:
        """Initialize the additional settings dialog.
        
        Args:
            state: Parent export state instance
        """
        super(AdditionalSettingsDialog, self).__init__()
        self.state = state
        self.core = self.state.core
        self.core.parentWindow(self, parent=self.state)
        self.widgets = []
        self.loadLayout()

    @err_catcher(name=__name__)
    def loadLayout(self) -> None:
        """Load and build the dialog layout.
        
        Creates widgets for all additional settings defined in the state.
        """
        self.setWindowTitle("Additional Settings")
        self.lo_main = QVBoxLayout(self)

        for setting in self.state.additionalSettings:
            widgets = {}
            w = QWidget()
            lo = QHBoxLayout(w)
            lo.setContentsMargins(9, 0, 9, 0)
            l = QLabel(setting["label"] + ":")
            lo.addWidget(l)
            lo.addStretch()
            setattr(self, "l_" + setting["name"], l)
            setattr(self, "w_" + setting["name"], w)
            setattr(self, "lo_" + setting["name"], lo)
            self.lo_main.addWidget(w)
            widgets = {"widget": w, "label": l, "type": setting["type"]}

            if setting["type"] == "checkbox":
                chb = QCheckBox()
                lo.addWidget(chb)
                setattr(self, "chb_" + setting["name"], chb)
                widgets["checkbox"] = chb
                chb.setChecked(setting["value"])
                chb.toggled.connect(lambda x: self.refreshVisibility())
            elif setting["type"] == "combobox":
                cb = QComboBox()
                lo.addWidget(cb)
                setattr(self, "cb_" + setting["name"], cb)
                widgets["combobox"] = cb
                cb.addItems(setting["items"])
                cb.setCurrentText(setting["value"])
                cb.currentIndexChanged.connect(lambda x: self.refreshVisibility())
            elif setting["type"] == "float":
                sp = QDoubleSpinBox()
                lo.addWidget(sp)
                setattr(self, "sp_" + setting["name"], sp)
                widgets["spinbox"] = sp
                sp.setValue(setting["value"])

            if not setting.get("visible", lambda dlg, state: True)(self, self.state):
                w.setHidden(True)

            self.widgets.append(widgets)

        self.lo_main.addStretch()
        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Accept", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Cancel", QDialogButtonBox.RejectRole)
        self.bb_main.accepted.connect(self.onAccept)
        self.bb_main.rejected.connect(self.reject)
        self.lo_main.addWidget(self.bb_main)

    @err_catcher(name=__name__)
    def refreshVisibility(self) -> None:
        """Refresh visibility of settings based on current state.
        
        Updates widget visibility based on visibility callbacks.
        """
        for idx, setting in enumerate(self.state.additionalSettings):
            self.widgets[idx]["widget"].setHidden(not setting.get("visible", lambda dlg, state: True)(self, self.state))

    @err_catcher(name=__name__)
    def onAccept(self) -> None:
        """Handle dialog acceptance.
        
        Saves all settings values back to the state and closes dialog.
        """
        for idx, setting in enumerate(self.state.additionalSettings):
            val = self.getValueFromWidget(self.widgets[idx])
            setting["value"] = val

        self.state.stateManager.saveStatesToScene()
        self.accept()

    @err_catcher(name=__name__)
    def getValueFromWidget(self, widget: Dict[str, Any]) -> Any:
        """Extract current value from a widget configuration.
        
        Args:
            widget: Widget configuration dictionary
            
        Returns:
            Current widget value (type depends on widget type)
        """
        if widget["type"] == "checkbox":
            return widget["checkbox"].isChecked()
        elif widget["type"] == "combobox":
            return widget["combobox"].currentText()
        elif widget["type"] == "float":
            return widget["spinbox"].value()
