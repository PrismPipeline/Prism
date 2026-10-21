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


import os
import tempfile
import subprocess
import logging
import platform
from typing import Any, List, Optional, Dict

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


logger = logging.getLogger(__name__)


class Prism_PureRef_externalAccess_Functions(object):
    """External access and callback functions for PureRef plugin.
    
    Handles file operations, context menus, media exports, and PureRef
    executable integration.
    
    Attributes:
        core: PrismCore instance
        plugin: Plugin instance
    """

    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize external access functions and register callbacks.
        
        Args:
            core: PrismCore instance.
            plugin: Plugin instance.
        """
        self.core = core
        self.plugin = plugin
        self.core.registerCallback("getIconPathForFileType", self.getIconPathForFileType, plugin=self.plugin)
        self.core.registerCallback("getPresetScenes", self.getPresetScenes, plugin=self.plugin)
        self.core.registerCallback("openPBFileContextMenu", self.openPBFileContextMenu, plugin=self.plugin)
        self.core.registerCallback("mediaPlayerContextMenuRequested", self.mediaPlayerContextMenuRequested, plugin=self.plugin)
        self.core.registerCallback("onSceneBrowserOpen", self.onSceneBrowserOpen, plugin=self.plugin)

        self.initializeFirstLaunch()
        self.initialize()

    @err_catcher(name=__name__)
    def initializeFirstLaunch(self) -> None:
        """Prompt user to configure PureRef executable on first launch.
        
        Shows file browser dialog to select PureRef executable if not already
        configured. Saves configuration to user settings.
        """
        if not self.core.uiAvailable:
            return

        if self.core.getConfig("pureref", "initialized", config="user"):
            return

        if self.core.getConfig("dccoverrides", "PureRef_path"):
            return

        if self.core.status == "starting":
            return

        msg = "Please specify the \"PureRef\" executable to use the \"PureRef\" plugin in Prism.\nYou can change the path to the executable later in the \"DCC Apps\" tab of the Prism User Settings."
        result = self.core.popupQuestion(msg, buttons=["Browse...", "Cancel"], icon=QMessageBox.Information)

        if result == "Browse...":
            if platform.system() == "Windows":
                fStr = "Executable (*.exe)"
            else:
                fStr = "All files (*)"

            windowTitle = "Select PureRef executable"
            selectedPath = QFileDialog.getOpenFileName(
                self.core.messageParent, windowTitle, self.core.prismRoot, fStr
            )[0]

            if not selectedPath:
                return

            cData = {
                "dccoverrides": {
                    "PureRef_override": True,
                    "PureRef_path": selectedPath
                }
            }

            self.core.setConfig(data=cData, config="user")

        self.core.setConfig("pureref", "initialized", True, config="user")

    @err_catcher(name=__name__)
    def initialize(self) -> None:
        """Initialize PureRef plugin integration.
        
        Registers PureRef file formats with the Project Browser's scene browser
        and refreshes the scene file list.
        """
        sceneBrowser = getattr(getattr(self.core, "pb", None), "sceneBrowser", None)
        if sceneBrowser is not None:
            self.onSceneBrowserOpen(sceneBrowser)
            sceneBrowser.refreshScenefilesThreaded()

    @err_catcher(name=__name__)
    def onSceneBrowserOpen(self, origin) -> None:
        origin.appFilters[self.pluginName] = {
            "formats": self.sceneFormats,
            "show": True,
        }

    @err_catcher(name=__name__)
    def preUninstall(self) -> None:
        """Clean up configuration before plugin uninstall.
        
        Removes PureRef-related configuration entries from user settings.
        """
        self.core.setConfig("pureref", "initialized", delete=True, config="user")
        self.core.setConfig("dccoverrides", "PureRef_override", delete=True, config="user")
        self.core.setConfig("dccoverrides", "PureRef_path", delete=True, config="user")

    @err_catcher(name=__name__)
    def getPresetScenes(self, presetScenes: List) -> None:
        """Add PureRef preset scenes to the preset scenes list.
        
        Args:
            presetScenes: List to append preset scenes to.
        """
        if os.getenv("PRISM_SHOW_DEFAULT_SCENEFILE_PRESETS", "1") != "1":
            return

        presetDir = os.path.join(self.pluginDirectory, "Presets")
        scenes = self.core.entities.getPresetScenesFromFolder(presetDir)
        presetScenes += scenes

    @err_catcher(name=__name__)
    def getIconPathForFileType(self, extension: str) -> Optional[str]:
        """Get icon path for PureRef file extension.
        
        Args:
            extension: File extension (e.g., ".pur").
        
        Returns:
            Path to icon file, or None if extension not supported.
        """
        if extension == ".pur":
            path = os.path.join(self.pluginDirectory, "Resources", "PureRef.ico")
            return path

    @err_catcher(name=__name__)
    def openPBFileContextMenu(self, origin: Any, menu: QMenu, filepath: str) -> None:
        """Add PureRef-specific actions to Project Browser file context menu.
        
        Args:
            origin: Originating widget.
            menu: Context menu to modify.
            filepath: Path to the file.
        """
        ext = os.path.splitext(filepath)[1]
        if ext == ".pur":
            pmenu = QMenu("PureRef", origin)
            
            data = self.core.entities.getScenefileData(filepath)
            entity = data.get("type")
            if entity:
                action = QAction("Set as %s preview" % entity, origin)
                action.triggered.connect(lambda: self.setAsPreview(origin, filepath))
                pmenu.addAction(action)

                action = QAction("Export...", origin)
                action.triggered.connect(lambda: self.exportDlg(filepath))
                pmenu.addAction(action)

            menu.insertMenu(menu.actions()[0], pmenu)

    @err_catcher(name=__name__)
    def mediaPlayerContextMenuRequested(self, origin: Any, menu: QMenu) -> None:
        """Add "Open in PureRef" action to media player context menu.
        
        Args:
            origin: Originating widget.
            menu: Context menu to modify.
        """
        if not type(origin.origin).__name__ == "MediaBrowser":
            return

        version = origin.origin.getCurrentVersion()
        if not version:
            return

        if not origin.seq:
            return

        filepath = origin.seq[0]
        if os.path.splitext(filepath)[1] in self.core.media.videoFormats:
            return

        action = QAction("Open in PureRef...", origin)
        action.triggered.connect(lambda: self.openMediaInPureRef(origin.seq))
        menu.insertAction(menu.actions()[-2], action)

    @err_catcher(name=__name__)
    def openMediaInPureRef(self, media: List[str]) -> None:
        """Open media files in PureRef application.
        
        Args:
            media: List of media file paths to open.
        """
        exe = None
        orApp = self.core.getConfig(
            "dccoverrides",
            "%s_override" % self.pluginName,
        )
        if not orApp:
            msg = "Invalid executable specified. Please update the executable setting in the DCC apps tab in the Prism User Settings."
            self.core.popup(msg)
            return

        appOrPath = self.core.getConfig(
            "dccoverrides", "%s_path" % self.pluginName
        )
        if appOrPath and os.path.exists(appOrPath):
            exe = appOrPath
        else:
            msg = "Invalid executable specified. Please update the executable setting in the DCC apps tab in the Prism User Settings."
            self.core.popup(msg)
            return

        args = [exe] + media
        subprocess.Popen(args)

    @err_catcher(name=__name__)
    def setAsPreview(self, origin: Any, path: str) -> None:
        """Set PureRef scene as entity preview image.
        
        Args:
            origin: Originating widget.
            path: Path to PureRef scene file.
        """
        with self.core.waitPopup(self.core, "Creating preview. Please wait..."):
            entity = self.core.entities.getScenefileData(path)
            previewImg = self.getImageFromScene(path)
            self.core.entities.setEntityPreview(entity, previewImg)
            origin.refreshEntityInfo()

    @err_catcher(name=__name__)
    def exportDlg(self, path: str) -> None:
        """Show export dialog for PureRef scene.
        
        Args:
            path: Path to PureRef scene file.
        """
        self.dlg_export = ExportDlg(self, path)
        self.dlg_export.show()

    @err_catcher(name=__name__)
    def exportSceneToProject(self, path: str, entity: Dict, identifier: str, comment: Optional[str] = None, location: str = "global") -> Optional[str]:
        """Export PureRef scene as image to project.
        
        Args:
            path: Path to PureRef scene file.
            entity: Entity dictionary (asset or shot).
            identifier: Task/identifier name.
            comment: Optional version comment. Defaults to None.
            location: Storage location. Defaults to "global".
        
        Returns:
            Path to exported image, or False if export failed.
        """
        if entity.get("type") not in ["asset", "shot"]:
            msg = "The scene is located in an invalid context."
            self.core.popup(msg)
            return False

        extension = ".png"
        imgPath = self.core.mediaProducts.generateMediaProductPath(
            entity=entity,
            task=identifier,
            extension=extension,
            comment=comment,
            location=location,
            mediaType="2drenders",
        )
        if not imgPath:
            msg = "Failed to generate outputpath."
            self.core.popup(msg)
            return False

        imgPath = imgPath.replace("\\", "/")
        result = self.exportImage(path, imgPath)
        if not result:
            if result is not False:
                msg = "Failed to export an image from the scene."
                self.core.popup(msg)
            return False

        return imgPath

    @err_catcher(name=__name__)
    def getImageFromScene(self, path: str) -> Optional[Any]:
        """Extract image from PureRef scene file.
        
        Args:
            path: Path to PureRef scene file.
        
        Returns:
            QPixmap of exported image, or None if export failed.
        """
        entity = self.core.entities.getScenefileData(path)
        if entity.get("type") not in ["asset", "shot"]:
            msg = "The scene is located in an invalid context."
            self.core.popup(msg)
            return

        imgPath = tempfile.NamedTemporaryFile(suffix=".png").name
        result = self.exportImage(path, imgPath)
        if not result:
            if result is not False:
                msg = "Failed to export an image from the scene."
                self.core.popup(msg)
            return

        previewImg = self.core.media.getPixmapFromPath(imgPath)
        if previewImg.width() == 0:
            warnStr = "Cannot read image: %s" % path
            self.core.popup(warnStr)
            return

        try:
            os.remove(imgPath)
        except:
            pass

        return previewImg

    @err_catcher(name=__name__)
    def exportImage(self, path: str, imgPath: str) -> bool:
        """Export image from PureRef scene to file.
        
        Args:
            path: Path to PureRef scene file.
            imgPath: Destination path for exported image.
        
        Returns:
            True if export successful, False otherwise.
        """
        exe = None
        orApp = self.core.getConfig(
            "dccoverrides",
            "%s_override" % self.pluginName,
        )
        if not orApp:
            msg = "Invalid executable specified. Please update the executable setting in the DCC apps tab in the Prism User Settings."
            self.core.popup(msg)
            return False

        appOrPath = self.core.getConfig(
            "dccoverrides", "%s_path" % self.pluginName
        )
        if appOrPath and os.path.exists(appOrPath):
            exe = appOrPath
        else:
            msg = "Invalid executable specified. Please update the executable setting in the DCC apps tab in the Prism User Settings."
            self.core.popup(msg)
            return False

        dirpath = os.path.dirname(imgPath)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        args = [exe, "-c", "load;%s" % path, "-c", "exportScene;%s;" % imgPath, "-c", "exit;"]
        logger.debug("writing image to %s" % imgPath)
        subprocess.call(args)

        result = os.path.exists(imgPath)
        if result:
            return result


class ExportDlg(QDialog):
    """Dialog for exporting PureRef scenes as images to project.
    
    Allows selecting entity, identifier, comment, and location for
    exporting PureRef board as rendered image.
    
    Attributes:
        plugin: Plugin instance
        core: PrismCore instance
        path (str): Path to PureRef scene file
        identifiers (List[str]): Available task identifiers
        entity (Dict): Target entity for export
    """

    def __init__(self, plugin: Any, path: str) -> None:
        """Initialize export dialog.
        
        Args:
            plugin: Plugin instance.
            path: Path to PureRef scene file.
        """
        super(ExportDlg, self).__init__()
        self.plugin = plugin
        self.core = self.plugin.core
        self.path = path
        self.identifiers = []
        self.entity = None
        self.setupUi()
        entity = self.core.entities.getScenefileData(path)
        self.setEntity(entity)

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Setup the dialog user interface."""
        self.setWindowTitle("Export Image")
        self.core.parentWindow(self)
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.lo_widgets = QGridLayout()

        self.lo_entity = QHBoxLayout()
        self.l_entity = QLabel("Entity:")
        self.l_entityName = QLabel("")
        self.b_entity = QPushButton("Choose...")
        self.b_entity.clicked.connect(self.chooseEntity)
        self.b_entity.setFocusPolicy(Qt.NoFocus)
        self.lo_widgets.addWidget(self.l_entity, 0, 0)
        self.lo_widgets.setColumnStretch(1, 1)
        self.lo_widgets.addWidget(self.l_entityName, 0, 1)
        self.lo_widgets.addWidget(self.b_entity, 0, 2, 1, 2)

        self.l_identifier = QLabel("Identifier:    ")
        self.e_identifier = QLineEdit("")
        self.b_identifier = QToolButton()
        self.b_identifier.setFocusPolicy(Qt.NoFocus)
        self.b_identifier.setArrowType(Qt.DownArrow)
        self.b_identifier.clicked.connect(self.showIdentifiers)
        self.b_identifier.setVisible(False)
        self.lo_widgets.addWidget(self.l_identifier, 1, 0)
        self.lo_widgets.addWidget(self.e_identifier, 1, 1, 1, 3)
        self.lo_widgets.addWidget(self.b_identifier, 1, 3)

        self.l_comment = QLabel("Comment:")
        self.e_comment = QLineEdit("")
        self.lo_widgets.addWidget(self.l_comment, 2, 0)
        self.lo_widgets.addWidget(self.e_comment, 2, 1, 1, 3)

        self.l_location = QLabel("Location:")
        self.cb_location = QComboBox()
        paths = self.core.paths.getRenderProductBasePaths()
        self.cb_location.addItems(list(paths.keys()))
        if len(paths) > 1:
            self.cb_location.setFocusPolicy(Qt.NoFocus)
            self.lo_widgets.addWidget(self.l_location, 3, 0)
            self.lo_widgets.addWidget(self.cb_location, 3, 1, 1, 3)

        self.lo_main.addLayout(self.lo_widgets)

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Export", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Cancel", QDialogButtonBox.RejectRole)

        self.bb_main.clicked.connect(self.buttonClicked)

        self.lo_main.addStretch()
        self.lo_main.addWidget(self.bb_main)

    @err_catcher(name=__name__)
    def sizeHint(self) -> QSize:
        """Get preferred dialog size.
        
        Returns:
            Preferred size for the dialog.
        """
        return QSize(400, 250)

    @err_catcher(name=__name__)
    def getIdentifier(self) -> str:
        """Get the selected identifier text.
        
        Returns:
            Identifier/task name.
        """
        return self.e_identifier.text()

    @err_catcher(name=__name__)
    def getComment(self) -> str:
        """Get the comment text.
        
        Returns:
            Version comment.
        """
        return self.e_comment.text()

    @err_catcher(name=__name__)
    def getLocation(self) -> str:
        """Get the selected location.
        
        Returns:
            Storage location name.
        """
        return self.cb_location.currentText()

    @err_catcher(name=__name__)
    def setEntity(self, entity: Any) -> None:
        """Set the target entity for export.
        
        Args:
            entity: Entity dictionary or list containing entity.
        """
        if isinstance(entity, list):
            entity = entity[0]

        self.entity = entity
        entityType = self.entity.get("type")
        if entityType == "asset":
            entityName = self.entity["asset_path"]
        elif entityType == "shot":
            entityName = self.core.entities.getShotName(self.entity)
        else:
            entityName = ""

        self.l_entityName.setText(entityName)
        self.identifiers = self.core.getTaskNames(taskType="2d", context=self.entity, addDepartments=False)
        self.b_identifier.setVisible(bool(self.identifiers))
        if self.identifiers:
            self.lo_widgets.addWidget(self.e_identifier, 1, 1, 1, 2)
        else:
            self.lo_widgets.addWidget(self.e_identifier, 1, 1, 1, 3)

    @err_catcher(name=__name__)
    def chooseEntity(self) -> None:
        """Show entity selection dialog."""
        dlg = EntityDlg(self)
        dlg.entitiesSelected.connect(self.setEntity)
        if self.entity:
            dlg.w_browser.w_entities.navigate(self.entity)

        dlg.exec_()

    @err_catcher(name=__name__)
    def showIdentifiers(self) -> None:
        """Show context menu with available identifiers."""
        pos = QCursor.pos()
        tmenu = QMenu(self)

        for identifier in self.identifiers:
            tAct = QAction(identifier, self)
            tAct.triggered.connect(lambda x=None, t=identifier: self.e_identifier.setText(t))
            tmenu.addAction(tAct)

        tmenu.exec_(pos)

    @err_catcher(name=__name__)
    def validate(self) -> bool:
        """Validate dialog inputs before export.
        
        Returns:
            True if inputs are valid, False otherwise.
        """
        if not self.entity:
            msg = "No entity is selected."
            self.core.popup(msg, parent=self)
            return False

        if not self.getIdentifier():
            msg = "No identifier is specified."
            self.core.popup(msg, parent=self)
            return False

        return True

    @err_catcher(name=__name__)
    def buttonClicked(self, button: Any) -> None:
        """Handle dialog button clicks.
        
        Args:
            button: Clicked button widget.
        """
        if button.text() == "Export":
            if not self.validate():
                return

            identifier = self.getIdentifier()
            comment = self.getComment()
            location = self.getLocation()
            outputpath = self.plugin.exportSceneToProject(self.path, entity=self.entity, identifier=identifier, comment=comment, location=location)
            if outputpath is not False:
                if outputpath and os.path.exists(outputpath):
                    msg = "Finished rendering successfully."
                    result = self.core.popupQuestion(msg, buttons=["Open in Project Browser", "Open in Explorer", "Close"], icon=QMessageBox.Information, parent=self)
                    if result == "Open in Project Browser":
                        if hasattr(self.core, "pb") and self.core.pb.isVisible():
                            pb = self.core.pb
                            pb.show()
                            pb.activateWindow()
                            pb.raise_()
                        else:
                            pb = self.core.projectBrowser()

                        pb.showTab("Media")
                        pb.mediaBrowser.showRender(self.entity, identifier + " (2d)")
                    elif result == "Open in Explorer":
                        self.core.openFolder(outputpath)
                else:
                    msg = "Export failed. The expected mediafile doesn't exist:\n\n%s" % outputpath
                    self.core.popup(msg, parent=self)

                self.close()
        else:
            self.close()


class EntityDlg(QDialog):
    """Dialog for selecting entities (assets/shots).
    
    Provides entity browser for selecting target entities for export.
    
    Attributes:
        parentDlg: Parent dialog
        plugin: Plugin instance
        core: PrismCore instance
        w_browser: MediaBrowser widget
        entitiesSelected (Signal): Signal emitted when entities are selected
    """

    entitiesSelected = Signal(object)

    def __init__(self, parent: Any) -> None:
        """Initialize entity selection dialog.
        
        Args:
            parent: Parent dialog.
        """
        super(EntityDlg, self).__init__()
        self.parentDlg = parent
        self.plugin = self.parentDlg.plugin
        self.core = self.plugin.core
        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Setup the entity dialog user interface."""
        title = "Choose Shots"

        self.setWindowTitle(title)
        self.core.parentWindow(self, parent=self.parentDlg)

        import MediaBrowser
        self.w_browser = MediaBrowser.MediaBrowser(core=self.core)
        self.w_browser.w_entities.getPage("Assets").tw_tree.itemDoubleClicked.connect(self.itemDoubleClicked)
        self.w_browser.w_entities.getPage("Shots").tw_tree.itemDoubleClicked.connect(self.itemDoubleClicked)
        self.setExpanded(False)

        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Select", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Cancel", QDialogButtonBox.RejectRole)
        self.b_expand = self.bb_main.addButton("▶", QDialogButtonBox.RejectRole)
        self.b_expand.setToolTip("Expand")

        self.bb_main.clicked.connect(self.buttonClicked)

        self.lo_main.addWidget(self.w_browser)
        self.lo_main.addWidget(self.bb_main)

    @err_catcher(name=__name__)
    def itemDoubleClicked(self, item: Any, column: int) -> None:
        """Handle double-click on entity item.
        
        Args:
            item: Clicked tree widget item.
            column: Column index.
        """
        self.buttonClicked("select")

    @err_catcher(name=__name__)
    def buttonClicked(self, button: Any) -> None:
        """Handle dialog button clicks.
        
        Args:
            button: Clicked button widget or string identifier.
        """
        if button == "select" or button.text() == "Select":
            entities = self.w_browser.w_entities.getCurrentData()
            if isinstance(entities, dict):
                entities = [entities]

            validEntities = []
            for entity in entities:
                if entity.get("type", "") not in ["asset", "shot"]:
                    continue

                validEntities.append(entity)

            if not validEntities:
                msg = "Invalid entity selected."
                self.core.popup(msg, parent=self)
                return

            self.entitiesSelected.emit(validEntities)
        elif button.text() == "▶":
            self.setExpanded(True)
            button.setVisible(False)
            return

        self.close()

    @err_catcher(name=__name__)
    def setExpanded(self, expand: bool) -> None:
        """Set expanded state of the browser.
        
        Args:
            expand: Whether to expand the browser view.
        """
        self.w_browser.w_identifier.setVisible(expand)
        self.w_browser.w_version.setVisible(expand)
        self.w_browser.w_preview.setVisible(expand)

        if expand:
            newwidth = 1200
            curwidth = self.geometry().width()
            self.resize(newwidth, self.geometry().height())
            self.move(self.pos().x()-((newwidth-curwidth)/2), self.pos().y())

    @err_catcher(name=__name__)
    def sizeHint(self) -> QSize:
        """Get preferred dialog size.
        
        Returns:
            Preferred size for the dialog.
        """
        return QSize(500, 500)
