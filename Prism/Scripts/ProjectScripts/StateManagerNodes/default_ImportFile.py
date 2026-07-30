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
import logging
import copy

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class ImportFileClass(object):
    """State Manager node for importing external files/caches.
    
    Provides functionality to import files (ABC, FBX, USD, etc.) from the project
    or external sources. Supports automatic updates, object tracking, namespace
    management, and version checking.
    
    Attributes:
        className (str): Node type identifier ("ImportFile")
        listType (str): State list type ("Import")
        core (Any): Reference to PrismCore instance
        state (Any): Reference to QTreeWidgetItem representing this state
        stateManager (Any): Reference to StateManager instance
        stateMode (str): Current import mode ("ImportFile" or "ApplyCache")
        taskName (str): Task name from imported file
        setName (str): Set name for tracking
        importPath (str): Path to the imported file
        nodes (List): List of imported scene nodes
        nodeNames (List[str]): Names of imported nodes
        statusColor (QColor): Color indicating import status
    """
    className = "ImportFile"
    listType = "Import"

    @err_catcher(name=__name__)
    def setup(
        self,
        state: Any,
        core: Any,
        stateManager: Any,
        node: Optional[Any] = None,
        importPath: Optional[str] = None,
        stateData: Optional[Dict[str, Any]] = None,
        openProductsBrowser: bool = True,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Optional[bool]:
        """Initialize the ImportFile state.
        
        Args:
            state: QTreeWidgetItem representing this state
            core: PrismCore instance
            stateManager: StateManager instance
            node: Optional node reference (unused)
            importPath: Optional path to import
            stateData: Optional saved state data to load
            openProductsBrowser: Whether to show product browser if no path given
            settings: Optional import settings
            
        Returns:
            False if import was cancelled, None otherwise
        """
        self.state = state
        self.stateMode = "ImportFile"

        self.core = core
        self.stateManager = stateManager
        self.taskName = ""
        self.setName = ""

        stateNameTemplate = "{entity}_{product}_{version}{#}"
        self.stateNameTemplate = self.core.getConfig(
            "globals",
            "defaultImportStateName",
            configPath=self.core.prismIni,
        ) or stateNameTemplate
        self.e_name.setText(self.stateNameTemplate)
        self.l_name.setVisible(False)
        self.e_name.setVisible(False)

        self.nodes = []
        self.nodeNames = []

        self.f_abcPath.setVisible(False)
        self.f_keepRefEdits.setVisible(False)

        self.oldPalette = self.b_importLatest.palette()
        self.updatePalette = QPalette()
        self.updatePalette.setColor(QPalette.Button, QColor(200, 100, 0))
        self.updatePalette.setColor(QPalette.ButtonText, QColor(255, 255, 255))

        createEmptyState = (
            QApplication.keyboardModifiers() == Qt.ControlModifier
            or not self.core.uiAvailable
        ) or not openProductsBrowser

        if (
            importPath is None
            and stateData is None
            and not createEmptyState
            and not self.stateManager.standalone
        ):
            importPaths = self.requestImportPaths()
            if importPaths:
                importPath = importPaths[-1]
                if len(importPaths) > 1:
                    for impPath in importPaths[:-1]:
                        stateManager.importFile(impPath)

        if importPath:
            self.setImportPath(importPath)
            result = self.importObject(settings=settings)

            if not result:
                return False
        elif (
            stateData is None
            and not createEmptyState
            and not self.stateManager.standalone
        ):
            return False

        getattr(self.core.appPlugin, "sm_import_startup", lambda x: None)(self)
        self.connectEvents()
        if settings:
            stateData = copy.deepcopy(stateData or {})
            stateData.update(settings)

        if stateData is not None:
            self.loadData(stateData)

        self.nameChanged()
        self.updateUi()

    @err_catcher(name=__name__)
    def setStateMode(self, stateMode: str) -> None:
        """Set the import state mode.
        
        Args:
            stateMode: Mode to set ("ImportFile" or "ApplyCache")
        """
        self.stateMode = stateMode
        self.l_class.setText(stateMode)

    @err_catcher(name=__name__)
    def requestImportPaths(self) -> List[str]:
        """Request import paths from user via callback or browser.
        
        Returns:
            List of import file paths
        """
        result = self.core.callback("requestImportPath", self)
        for res in result:
            if isinstance(res, dict) and res.get("importPaths") is not None:
                return res["importPaths"]

        import ProductBrowser
        ts = ProductBrowser.ProductBrowser(core=self.core, importState=self)
        self.core.parentWindow(ts)
        ts.exec_()
        importPath = [ts.productPath]
        return importPath

    @err_catcher(name=__name__)
    def loadData(self, data: Dict[str, Any]) -> None:
        """Load state data from saved configuration.
        
        Restores import settings including file path, namespace settings,
        object tracking, and connected nodes.
        
        Args:
            data: Dictionary containing saved state configuration
        """
        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "statemode" in data:
            self.setStateMode(data["statemode"])
        if "filepath" in data:
            data["filepath"] = getattr(
                self.core.appPlugin, "sm_import_fixImportPath", lambda x: x
            )(data["filepath"])
            self.setImportPath(data["filepath"])
        if "keepedits" in data:
            self.chb_keepRefEdits.setChecked(eval(data["keepedits"]))
        if "autonamespaces" in data:
            self.chb_autoNameSpaces.setChecked(eval(data["autonamespaces"]))
        if "updateabc" in data:
            self.chb_abcPath.setChecked(eval(data["updateabc"]))
        if "trackobjects" in data:
            self.chb_trackObjects.setChecked(eval(data["trackobjects"]))
        if "connectednodes" in data:
            if self.core.isStr(data["connectednodes"]):
                data["connectednodes"] = eval(data["connectednodes"])
            self.nodes = [
                x[1]
                for x in data["connectednodes"]
                if self.core.appPlugin.isNodeValid(self, x[1])
            ]
        if "taskname" in data:
            self.taskName = data["taskname"]
        if "nodenames" in data:
            self.nodeNames = eval(data["nodenames"])
        if "setname" in data:
            self.setName = data["setname"]
        if "autoUpdate" in data:
            self.chb_autoUpdate.setChecked(eval(data["autoUpdate"]))
        if "ignoreMaster" in data:
            self.chb_ignoreMaster.setChecked(data["ignoreMaster"])

        self.core.callback("onStateSettingsLoaded", self, data)

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect Qt signals to their respective slot methods.
        
        Establishes connections for import path browsing, object selection,
        auto-update, and namespace management.
        """
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.b_browse.clicked.connect(self.browse)
        self.b_browse.customContextMenuRequested.connect(self.openFolder)
        self.b_import.clicked.connect(self.importObject)
        self.b_importLatest.clicked.connect(self.importLatest)
        self.chb_autoUpdate.stateChanged.connect(self.autoUpdateChanged)
        self.chb_ignoreMaster.stateChanged.connect(self.ignoreMasterChanged)
        self.chb_keepRefEdits.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_autoNameSpaces.stateChanged.connect(self.autoNameSpaceChanged)
        self.chb_abcPath.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_trackObjects.toggled.connect(self.updateTrackObjects)
        self.b_selectAll.clicked.connect(self.lw_objects.selectAll)
        if not self.stateManager.standalone:
            self.b_nameSpaces.clicked.connect(
                lambda: self.core.appPlugin.sm_import_removeNameSpaces(self)
            )
            self.lw_objects.itemSelectionChanged.connect(
                lambda: self.core.appPlugin.selectNodes(self)
            )

    @err_catcher(name=__name__)
    def nameChanged(self, text: Optional[str] = None) -> None:
        """Handle changes to the state name.
        
        Formats name with cache data context variables.
        
        Args:
            text: New name text (unused, reads from widget)
        """
        text = self.e_name.text()
        cacheData = self.core.paths.getCachePathData(self.getImportPath())
        if cacheData.get("type") == "asset":
            cacheData["entity"] = os.path.basename(cacheData.get("asset_path", ""))
        elif cacheData.get("type") == "shot":
            shotName = self.core.entities.getShotName(cacheData)
            if shotName:
                cacheData["entity"] = shotName

        num = 0
        self.core.callback("onGenerateStateNameContext", self, cacheData)
        try:
            if "{#}" in text:
                while True:
                    cacheData["#"] = num or ""
                    name = text.format(**cacheData)
                    for state in self.stateManager.states:
                        if state.ui.listType != "Import":
                            continue

                        if state is self.state:
                            continue

                        if state.text(0) == name:
                            num += 1
                            break
                    else:
                        break
            else:
                name = text.format(**cacheData)

        except Exception as e:
            name = text

        self.state.setText(0, name)

    @err_catcher(name=__name__)
    def getSortKey(self) -> str:
        """Get the sorting key for this state.
        
        Returns:
            Product name from cache data, used for sorting
        """
        cacheData = self.core.paths.getCachePathData(self.getImportPath())
        return cacheData.get("product")

    @err_catcher(name=__name__)
    def browse(self) -> None:
        """Open product browser to select import file.
        
        Shows product browser and imports selected file.
        """
        import ProductBrowser

        ts = ProductBrowser.ProductBrowser(core=self.core, importState=self)
        self.core.parentWindow(ts)
        ts.exec_()
        importPath = ts.productPath

        if importPath:
            result = self.importObject(update=True, path=importPath)
            if result:
                self.setImportPath(importPath)
            self.updateUi()

    @err_catcher(name=__name__)
    def openFolder(self, pos: QPoint) -> None:
        """Open file explorer at import file location.
        
        Args:
            pos: Position of context menu request (unused)
        """
        path = self.getImportPath()
        if os.path.isfile(path):
            path = os.path.dirname(path)

        self.core.openFolder(path)

    @err_catcher(name=__name__)
    def getImportPath(self) -> str:
        """Get the current import file path.
        
        Returns:
            Normalized import path string
        """
        path = getattr(self, "importPath", "")
        if path:
            path = os.path.normpath(path)

        return path

    @err_catcher(name=__name__)
    def setImportPath(self, path: str) -> None:
        """Set the import file path.
        
        Args:
            path: File path to set as import source
        """
        self.importPath = path
        self.w_currentVersion.setToolTip(path)
        self.stateManager.saveImports()
        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def isShotCam(self, path: Optional[str] = None) -> bool:
        """Check if import is a shot camera.
        
        Args:
            path: Optional path to check (uses current import path if None)
            
        Returns:
            True if path is a shot camera ABC file
        """
        if not path:
            path = self.getImportPath()
        return path.endswith(".abc") and "/_ShotCam/" in path

    @err_catcher(name=__name__)
    def autoUpdateChanged(self, checked: bool) -> None:
        """Handle auto-update checkbox state change.
        
        Args:
            checked: Whether auto-update is enabled
        """
        self.w_latestVersion.setVisible(not checked)
        self.w_importLatest.setVisible(not checked)

        if checked:
            curVersion, latestVersion = self.checkLatestVersion()
            if self.chb_autoUpdate.isChecked():
                if curVersion.get("version") and latestVersion.get("version") and curVersion["version"] != latestVersion["version"]:
                    self.importLatest()

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def ignoreMasterChanged(self, checked: bool) -> None:
        """Handle ignore master checkbox state change.
        
        Args:
            checked: Whether ignore master is enabled
        """
        self.updateUi()
        self.stateManager.saveImports()

    @err_catcher(name=__name__)
    def autoNameSpaceChanged(self, checked: bool) -> None:
        """Handle auto-namespace checkbox state change.
        
        Args:
            checked: Whether auto-namespace cleanup is enabled
        """
        self.b_nameSpaces.setEnabled(not checked)
        if not self.stateManager.standalone and checked:
            self.core.appPlugin.sm_import_removeNameSpaces(self)
            self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def runSanityChecks(self, cachePath: str, settings: Optional[Dict[str, Any]] = None) -> bool:
        """Run validation checks before import.
        
        Args:
            cachePath: Path to cache file to validate
            settings: Optional import settings
            
        Returns:
            True if checks passed, False otherwise
        """
        result = True

        if getattr(self.core.appPlugin, "hasFrameRange", True):
            result = self.checkFrameRange(cachePath, settings=settings)

        if not result:
            return False

        return True

    @err_catcher(name=__name__)
    def checkFrameRange(self, cachePath: str, settings: Optional[Dict[str, Any]] = None) -> bool:
        """Check if import FPS matches scene FPS.
        
        Args:
            cachePath: Path to cache file to check
            settings: Optional settings including 'quiet' mode
            
        Returns:
            True to proceed, False to cancel
        """
        versionInfoPath = self.core.getVersioninfoPath(
            self.core.products.getVersionInfoPathFromProductFilepath(cachePath)
        )

        impFPS = self.core.getConfig("fps", configPath=versionInfoPath)
        curFPS = self.core.getFPS()
        if not impFPS or not curFPS or impFPS == curFPS:
            return True

        vInfo = [["FPS of current scene:", str(curFPS)], ["Import FPS:", str(impFPS)]]
        lay_info = QGridLayout()

        msgString = "The FPS of the import doesn't match the FPS of the current scene:"

        for idx, val in enumerate(vInfo):
            l_infoName = QLabel(val[0] + ":\t")
            l_info = QLabel(val[1])
            lay_info.addWidget(l_infoName, idx, 0)
            lay_info.addWidget(l_info, idx, 1)

        lay_info.addItem(
            QSpacerItem(10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )
        lay_info.addItem(
            QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum), 0, 2
        )

        lay_info.setContentsMargins(0, 10, 0, 10)
        w_info = QWidget()
        w_info.setLayout(lay_info)

        if not settings or not settings.get("quiet", False):
            result = self.core.popupQuestion(
                msgString,
                title="FPS mismatch",
                buttons=["Continue", "Cancel"],
                icon=QMessageBox.Warning,
                widget=w_info,
                escapeButton="Continue",
                default="Continue",
            )
        else:
            logger.warning(msgString)
            result = "Continue"

        if result == "Cancel":
            return False

        return True

    @err_catcher(name=__name__)
    def importObject(self, update: bool = False, path: Optional[str] = None, settings: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Import file into the scene.
        
        Args:
            update: Whether this is an update of existing import
            path: Optional path to import (uses current if None)
            settings: Optional import settings
            
        Returns:
            Import result from app plugin, or None on failure
        """
        result = True
        if self.stateManager.standalone:
            return result

        fileName = self.core.getCurrentFileName()
        impFileName = path or self.getImportPath()
        impFileName = os.path.normpath(impFileName)

        kwargs = {
            "state": self,
            "scenefile": fileName,
            "importfile": impFileName,
        }
        result = self.core.callback("preImport", **kwargs)
        for res in result:
            if isinstance(res, dict) and res.get("cancel", False):
                return

            if res and "importfile" in res:
                impFileName = res["importfile"]
                if not impFileName:
                    return

        if not impFileName:
            self.core.popup("Invalid importpath:\n\n%s" % impFileName)
            return

        if not hasattr(self.core.appPlugin, "sm_import_importToApp"):
            self.core.popup("Import into %s is not supported." % self.core.appPlugin.pluginName)
            return

        result = self.runSanityChecks(impFileName, settings=settings)
        if not result:
            return

        cacheData = self.core.paths.getCachePathData(impFileName)
        self.taskName = cacheData.get("task")
        doImport = True

        if self.chb_trackObjects.isChecked():
            getattr(self.core.appPlugin, "sm_import_updateObjects", lambda x: None)(
                self
            )

        # temporary workaround until all plugin handle the settings argument
        if self.core.appPlugin.pluginName == "Maya":
            importResult = self.core.appPlugin.sm_import_importToApp(
                self, doImport=doImport, update=update, impFileName=impFileName, settings=settings
            )
        else:
            importResult = self.core.appPlugin.sm_import_importToApp(
                self, doImport=doImport, update=update, impFileName=impFileName
            )

        if not importResult:
            result = None
            doImport = False
        else:
            result = importResult["result"]
            doImport = importResult["doImport"]
            if result and "mode" in importResult:
                self.setStateMode(importResult["mode"])

        if doImport:
            if result == "canceled":
                return

            self.nodeNames = [
                self.core.appPlugin.getNodeName(self, x) for x in self.nodes
            ]
            illegalNodes = self.core.checkIllegalCharacters(self.nodeNames)
            if len(illegalNodes) > 0:
                msgStr = "Objects with non-ascii characters were imported. Prism supports only the first 128 characters in the ascii table. Please rename the following objects as they will cause errors with Prism:\n\n"
                for i in illegalNodes:
                    msgStr += i + "\n"
                self.core.popup(msgStr)

            if self.chb_autoNameSpaces.isChecked():
                self.core.appPlugin.sm_import_removeNameSpaces(self)

            if not result:
                msgStr = "Import failed: %s" % impFileName
                self.core.popup(msgStr, title="ImportFile")

        kwargs = {
            "state": self,
            "scenefile": fileName,
            "importfile": impFileName,
            "importedObjects": self.nodeNames,
        }
        self.core.callback("postImport", **kwargs)
        self.setImportPath(impFileName)
        self.stateManager.saveImports()
        self.updateUi()
        self.stateManager.saveStatesToScene()

        return result

    @err_catcher(name=__name__)
    def importLatest(self, refreshUi: bool = True, selectedStates: bool = True) -> None:
        """Import the latest version of the file.
        
        Args:
            refreshUi: Whether to refresh UI before importing
            selectedStates: Whether to apply to selected states
        """
        if refreshUi:
            self.updateUi()

        includeMaster = not self.chb_ignoreMaster.isChecked()
        latestVersion = self.core.products.getLatestVersionFromPath(
            self.getImportPath(), includeMaster=includeMaster
        )
        filepath = self.core.products.getPreferredFileFromVersion(latestVersion)
        if not filepath:
            if not self.chb_autoUpdate.isChecked():
                self.core.popup("Couldn't get latest version.")
            return

        prevState = self.stateManager.applyChangesToSelection
        self.stateManager.applyChangesToSelection = False
        self.setImportPath(filepath)
        self.importObject(update=True)
        if selectedStates:
            selStates = self.stateManager.getSelectedStates()
            for state in selStates:
                if state.__hash__() == self.state.__hash__():
                    continue

                if hasattr(state.ui, "importLatest"):
                    state.ui.importLatest(refreshUi=refreshUi, selectedStates=False)

        self.stateManager.applyChangesToSelection = prevState

    @err_catcher(name=__name__)
    def checkLatestVersion(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Check current vs latest available version.
        
        Returns:
            Tuple of (current_version_data, latest_version_data) dictionaries
        """
        path = self.getImportPath()
        curVersionName = self.core.products.getVersionFromFilepath(path) or ""
        curVersionData = {"version": curVersionName, "path": path}
        includeMaster = not self.chb_ignoreMaster.isChecked()
        latestVersion = self.core.products.getLatestVersionFromPath(path, includeMaster=includeMaster)
        if latestVersion:
            latestVersionData = {"version": latestVersion["version"], "path": latestVersion["path"]}
        else:
            latestVersionData = {}

        return curVersionData, latestVersionData

    @err_catcher(name=__name__)
    def setStateColor(self, status: str) -> None:
        """Set visual status color for the state.
        
        Args:
            status: Status string ("ok", "warning", "error")
        """
        if status == "ok":
            statusColor = QColor(0, 130, 0)
        elif status == "warning":
            statusColor = QColor(200, 100, 0)
        elif status == "error":
            statusColor = QColor(130, 0, 0)
        else:
            statusColor = QColor(0, 0, 0, 0)

        self.statusColor = statusColor
        self.stateManager.tw_import.repaint()

    @err_catcher(name=__name__)
    def updateUi(self) -> None:
        """Update the user interface with current state.
        
        Refreshes version info, object list, and status indicators.
        """
        versions = self.checkLatestVersion()
        if versions:
            curVersion, latestVersion = versions
        else:
            curVersion = latestVersion = ""

        if curVersion.get("version") == "master":
            filepath = self.getImportPath()
            curVersionName = self.core.products.getMasterVersionLabel(filepath)
        else:
            curVersionName = curVersion.get("version")

        if latestVersion.get("version") == "master":
            filepath = latestVersion["path"]
            latestVersionName = self.core.products.getMasterVersionLabel(filepath)
        else:
            latestVersionName = latestVersion.get("version")

        self.l_curVersion.setText(curVersionName or "-")
        self.l_latestVersion.setText(latestVersionName or "-")

        status = "error"
        if self.chb_autoUpdate.isChecked():
            if curVersionName and latestVersionName and curVersionName != latestVersionName:
                self.importLatest(refreshUi=False)

            if latestVersionName:
                status = "ok"
        else:
            useSS = getattr(self.core.appPlugin, "colorButtonWithStyleSheet", False)
            if (
                curVersionName
                and latestVersionName
                and curVersionName != latestVersionName
                and not curVersionName.startswith("master")
            ):
                status = "warning"
                if useSS:
                    self.b_importLatest.setStyleSheet(
                        "QPushButton { background-color: rgb(200,100,0); }"
                    )
                else:
                    self.b_importLatest.setPalette(self.updatePalette)
            else:
                if curVersionName and latestVersionName:
                    status = "ok"
                elif self.nodes:
                    status = "ok"

                if useSS:
                    self.b_importLatest.setStyleSheet("")
                else:
                    self.b_importLatest.setPalette(self.oldPalette)

        isCache = self.stateMode == "ApplyCache"
        self.f_nameSpaces.setVisible(not isCache)

        self.lw_objects.clear()

        if self.chb_trackObjects.isChecked():
            self.gb_objects.setVisible(True)
            getattr(self.core.appPlugin, "sm_import_updateObjects", lambda x: None)(
                self
            )

            for i in self.nodes:
                item = QListWidgetItem(self.core.appPlugin.getNodeName(self, i))
                getattr(
                    self.core.appPlugin,
                    "sm_import_updateListItem",
                    lambda x, y, z: None,
                )(self, item, i)

                self.lw_objects.addItem(item)
        else:
            self.gb_objects.setVisible(False)

        self.nameChanged()
        self.setStateColor(status)
        getattr(self.core.appPlugin, "sm_import_updateUi", lambda x: None)(self)

    @err_catcher(name=__name__)
    def updateTrackObjects(self, state: bool) -> None:
        """Handle object tracking checkbox state change.
        
        Args:
            state: Whether object tracking is enabled
        """
        if not state:
            if len(self.nodes) > 0:
                msg = QMessageBox(
                    QMessageBox.Question,
                    "Track objects",
                    "When you disable object tracking Prism won't be able to delete or replace the imported objects at a later point in time. You cannot undo this action. Are you sure you want to disable object tracking?",
                    QMessageBox.Cancel,
                )
                msg.addButton("Continue", QMessageBox.YesRole)
                msg.setParent(self.core.messageParent, Qt.Window)
                action = msg.exec_()

                if action != 0:
                    self.chb_trackObjects.setChecked(True)
                    return

            self.nodes = []
            getattr(
                self.core.appPlugin, "sm_import_disableObjectTracking", lambda x: None
            )(self)

        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def preDelete(
        self,
        item: Optional[Any] = None,
        baseText: str = "Do you also want to delete the connected objects?\n\n",
    ) -> None:
        """Cleanup before state deletion.
        
        Optionally deletes imported objects from scene.
        
        Args:
            item: State item being deleted
            baseText: Base message text for confirmation dialog
        """
        if len(self.nodes) > 0 and self.stateMode != "ApplyCache":
            message = baseText
            validNodes = [
                x for x in self.nodes if self.core.appPlugin.isNodeValid(self, x)
            ]
            if len(validNodes) > 0:
                for idx, val in enumerate(validNodes):
                    if idx > 5:
                        message += "..."
                        break
                    else:
                        message += self.core.appPlugin.getNodeName(self, val) + "\n"

                if not self.core.uiAvailable:
                    action = "Yes"
                    print("delete objects:\n\n%s" % message)
                else:
                    action = self.core.popupQuestion(message, title="Delete State", parent=self.stateManager)

                if action == "Yes":
                    self.core.appPlugin.deleteNodes(self, validNodes)

        getattr(self.core.appPlugin, "sm_import_preDelete", lambda x: None)(self)

    @err_catcher(name=__name__)
    def getStateProps(self) -> Dict[str, Any]:
        """Get all state properties for saving.
        
        Returns:
            Dictionary containing all state settings and values
        """
        connectedNodes = []
        if self.chb_trackObjects.isChecked():
            for i in range(self.lw_objects.count()):
                connectedNodes.append([self.lw_objects.item(i).text(), self.nodes[i]])

        return {
            "statename": self.e_name.text(),
            "statemode": self.stateMode,
            "filepath": self.getImportPath(),
            "autoUpdate": str(self.chb_autoUpdate.isChecked()),
            "ignoreMaster": self.chb_ignoreMaster.isChecked(),
            "keepedits": str(self.chb_keepRefEdits.isChecked()),
            "autonamespaces": str(self.chb_autoNameSpaces.isChecked()),
            "updateabc": str(self.chb_abcPath.isChecked()),
            "trackobjects": str(self.chb_trackObjects.isChecked()),
            "connectednodes": connectedNodes,
            "taskname": self.taskName,
            "nodenames": str(self.nodeNames),
            "setname": self.setName,
        }
