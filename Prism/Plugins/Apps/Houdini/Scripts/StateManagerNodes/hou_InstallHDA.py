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

"""Houdini Install HDA state for Prism State Manager.

Provides functionality to install Houdini Digital Assets (HDAs) from the
Prism product library. Tracks HDA versions, supports auto-update, and can
automatically create node instances after installation.
"""

import os
from typing import Any, Optional, Dict, Union

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

import hou
import hou_ImportFile

from PrismUtils.Decorators import err_catcher as err_catcher


class InstallHDAClass(hou_ImportFile.ImportFileClass):
    """State for installing HDAs into Houdini session.
    
    Extends ImportFileClass to provide HDA-specific installation,
    version tracking, and node creation capabilities.
    
    Attributes:
        className (str): State type identifier.
        listType (str): State list category.
        supportedFormats (List[str]): Supported HDA file extensions.
    """
    
    className = "Install HDA"
    listType = "Import"

    @err_catcher(name=__name__)
    def setup(
        self, 
        state: Any,
        core: Any, 
        stateManager: Any,
        node: Optional[Any] = None,
        importPath: Optional[str] = None,
        stateData: Optional[Dict] = None,
        openProductsBrowser: bool = True,
        settings: Optional[Dict] = None,
    ) -> Optional[bool]:
        """Initialize Install HDA state.
        
        Sets up UI, opens Product Browser if needed, installs HDA if path provided,
        and loads saved state data.
        
        Args:
            state: State Manager tree item.
            core: PrismCore instance.
            stateManager: State Manager instance.
            node: Unused (compatibility with parent class).
            importPath: Optional HDA file path to install.
            stateData: Optional saved state data to load.
            openProductsBrowser: Whether to open Product Browser (unused).
            settings: Optional settings dict with 'createNodeAfterImport' key.
            
        Returns:
            False if setup failed or was cancelled, None otherwise.
        """
        self.state = state
        self.core = core
        self.stateManager = stateManager
        self.taskName = None
        self.supportedFormats = self.core.appPlugin.assetFormats

        stateNameTemplate = "{entity}_{task}_{version}"
        self.stateNameTemplate = self.core.getConfig(
            "globals",
            "defaultImportStateName",
            dft=stateNameTemplate,
            configPath=self.core.prismIni,
        )
        self.e_name.setText("HDA - " + self.stateNameTemplate)
        self.l_name.setVisible(False)
        self.e_name.setVisible(False)

        self.core.callback("onStateStartup", self)

        createEmptyState = (
            QApplication.keyboardModifiers() == Qt.ControlModifier
            or not self.core.uiAvailable
        )

        if (
            importPath is None
            and stateData is None
            and not createEmptyState
            and not self.stateManager.standalone
        ):
            import ProductBrowser

            ts = ProductBrowser.ProductBrowser(core=core, importState=self)
            self.core.parentWindow(ts)
            if self.core.uiScaleFactor != 1:
                self.core.scaleUI(self.state, sFactor=0.5)
            ts.exec_()
            importPath = ts.productPath

        if importPath:
            self.setImportPath(importPath)
            settings = settings or {}
            result = self.importObject(createNode=settings.get("createNodeAfterImport"))

            if not result:
                return False
        elif (
            stateData is None
            and not createEmptyState
            and not self.stateManager.standalone
        ):
            return False

        self.nameChanged()
        self.connectEvents()

        if stateData is not None:
            self.loadData(stateData)

        self.updateUi()

    @err_catcher(name=__name__)
    def loadData(self, data: Dict) -> None:
        """Load state data from dictionary.
        
        Restores state name, file path, and auto-update setting.
        
        Args:
            data: Dictionary containing saved state data.
        """
        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "filepath" in data:
            self.setImportPath(data["filepath"])
        if "autoUpdate" in data:
            self.chb_autoUpdate.setChecked(eval(data["autoUpdate"]))

        self.core.callback("onStateSettingsLoaded", self, data)

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect UI widget signals to handlers.
        
        Links buttons, text fields, and checkboxes to their respective
        change handlers and state save operations.
        """
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.b_browse.clicked.connect(self.browse)
        self.b_browse.customContextMenuRequested.connect(self.openFolder)
        self.b_importLatest.clicked.connect(self.importLatest)
        self.chb_autoUpdate.stateChanged.connect(self.autoUpdateChanged)
        if not self.stateManager.standalone:
            self.b_import.clicked.connect(self.importObject)
            self.b_createNode.clicked.connect(self.createNode)

    @err_catcher(name=__name__)
    def importObject(self, taskName: Optional[str] = None, createNode: Optional[bool] = None) -> bool:
        """Install HDA file into Houdini session.
        
        Validates path, executes pre-import callbacks, installs HDA,
        updates all instances to latest version, and optionally creates
        a new node instance.
        
        Args:
            taskName: Unused (compatibility with parent class).
            createNode: Whether to create node after install (prompts if None).
            
        Returns:
            True if installation succeeded, False otherwise.
        """
        if self.stateManager.standalone:
            return False

        impFileName = self.getImportPath()
        result = self.validateFilepath(impFileName)
        if result is not True:
            self.core.popup(result)
            return

        kwargs = {
            "state": self,
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
            self.core.popup("Invalid importpath")
            return

        hou.hda.installFile(impFileName, force_use_assets=True)
        defs = hou.hda.definitionsInFile(impFileName)
        for definition in defs:
            self.changeAssetDefinitionVersions(definition)

        self.stateManager.saveImports()
        self.updateUi()
        self.stateManager.saveStatesToScene()

        if createNode is not None:
            result = "Yes" if createNode else "No"
        else:
            create = os.getenv("PRISM_HOUDINI_CREATE_NODE_AFTER_HDA_INSTALL", "1")
            if create == "1":
                result = "Yes"
            elif create == "0":
                result = "No"
            else:
                msg = "The HDA was installed successfully.\n\nDo you want to create a new node from it?"
                result = self.core.popupQuestion(msg)

        if result == "Yes":
            self.createNode()

        kwargs = {
            "state": self,
            "importfile": impFileName,
        }
        self.core.callback("postImport", **kwargs)
        return True

    @err_catcher(name=__name__)
    def changeAssetDefinitionVersions(self, definition: Any) -> None:
        """Update all node instances to use new HDA definition.
        
        Iterates through all instances of older versions in the namespace
        and changes them to the newly installed definition.
        
        Args:
            definition: HDA definition object from hou.hda.
        """
        namespaceOrder = definition.nodeType().namespaceOrder()
        for namespace in namespaceOrder:
            if namespace == definition.nodeTypeName():
                continue

            nodeType = hou.nodeType(definition.nodeTypeCategory(), namespace)
            for instance in nodeType.instances():
                instance.changeNodeType(definition.nodeType().name())

    @err_catcher(name=__name__)
    def validateFilepath(self, path: str) -> Union[str, bool]:
        """Validate HDA file path.
        
        Checks that path exists, is not empty, and has supported extension.
        
        Args:
            path: File path to validate.
            
        Returns:
            True if valid, error message string if invalid.
        """
        if not path:
            return "Invalid importpath"

        extension = os.path.splitext(path)[1]
        if extension not in self.supportedFormats:
            return 'Format "%s" is not supported by this statetype.' % extension

        if not os.path.exists(path):
            return "File doesn't exist:\n%s" % path

        return True

    @err_catcher(name=__name__)
    def createNode(self, parentNode: Optional[Any] = None) -> Optional[Any]:
        """Create node instance from installed HDA.
        
        Creates a node from the first definition in the HDA file,
        positions it in the network editor, and sets display/render flags.
        
        Args:
            parentNode: Parent context node (uses current network editor if None).
            
        Returns:
            Created node or None if creation failed.
        """
        if not self.core.uiAvailable:
            return

        paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        if parentNode is None:
            if paneTab is None:
                return

            parentNode = paneTab.pwd()

        if parentNode.isInsideLockedHDA():
            return

        mNode = None
        if os.path.exists(self.getImportPath()):
            defs = hou.hda.definitionsInFile(self.getImportPath())
            if len(defs) > 0:
                if parentNode.childTypeCategory() == hou.objNodeTypeCategory() and defs[0].nodeType().category() == hou.sopNodeTypeCategory():
                    typeNameData = defs[0].nodeTypeName().split("::")
                    if len(typeNameData) > 2:
                        name = typeNameData[-2] + "_container"
                    else:
                        name = typeNameData[-1] + "_container"

                    parentNode = parentNode.createNode("geo", name)
                elif parentNode.childTypeCategory() == hou.lopNodeTypeCategory() and defs[0].nodeType().category() == hou.sopNodeTypeCategory():
                    typeNameData = defs[0].nodeTypeName().split("::")
                    if len(typeNameData) > 2:
                        name = typeNameData[-2] + "_sopcreate"
                    else:
                        name = typeNameData[-1] + "_sopcreate"

                    sopcreate = parentNode.createNode("sopcreate", name)
                    parentNode = sopcreate.node("sopnet/create")

                tname = defs[0].nodeTypeName()
                isToolRecipe = self.isToolRecipe(tname)
                if isToolRecipe:
                    hou.data.applyTabToolRecipe(
                        name=tname,
                        parent=parentNode,
                        click_to_place=True,
                        skip_notes=False
                    )
                else:
                    try:
                        mNode = parentNode.createNode(tname)
                        mNode.moveToGoodPosition()
                    except:
                        return

        if mNode is None:
            return

        if hasattr(mNode, "setDisplayFlag"):
            mNode.setDisplayFlag(True)
        if hasattr(mNode, "setRenderFlag"):
            mNode.setRenderFlag(True)

        if paneTab:
            mNode.setPosition(paneTab.visibleBounds().center())

        mNode.setCurrent(True, clear_all_selected=True)
        return mNode
    
    @err_catcher(name=__name__)
    def isToolRecipe(self, typeName: str) -> bool:
        """Check if HDA type is a tool recipe.
        
        Determines if the given HDA type name corresponds to a tool recipe
        by checking for the "prism_tool_recipe" substring.
        
        Args:
            typeName: HDA type name to check.
            
        Returns:
            True if it's a tool recipe, False otherwise.
        """
        try:
            import recipeutils as ru
        except Exception as e:
            return False

        isToolRecipe = bool(ru.recipeNames(ru.RecipeCategory.tool, name_pattern=typeName))
        return isToolRecipe

    @err_catcher(name=__name__)
    def updateUi(self) -> None:
        """Update UI to reflect current HDA installation status.
        
        Updates status label, version indicators, and import button styling.
        Auto-imports latest version if auto-update is enabled and version differs.
        """
        self.l_status.setText("not installed")
        self.l_status.setStyleSheet("QLabel { background-color : rgb(130,0,0); }")
        status = "error"
        if os.path.exists(self.getImportPath()):
            defs = hou.hda.definitionsInFile(self.getImportPath())
            if len(defs) > 0:
                if defs[0].isInstalled():
                    self.l_status.setText("installed")
                    self.l_status.setStyleSheet(
                        "QLabel { background-color : rgb(0,130,0); }"
                    )
                    status = "ok"

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

        if self.chb_autoUpdate.isChecked():
            if curVersionName and latestVersionName and curVersionName != latestVersionName:
                self.importLatest(refreshUi=False)
        else:
            if curVersionName and latestVersionName and curVersionName != latestVersionName:
                self.b_importLatest.setStyleSheet(
                    "QPushButton { background-color : rgb(150,80,0); border: none;}"
                )
                status = "warning"
            else:
                self.b_importLatest.setStyleSheet("")

        self.nameChanged()
        self.setStateColor(status)

    @err_catcher(name=__name__)
    def getStateProps(self) -> Dict[str, str]:
        """Get state properties for saving.
        
        Returns:
            Dictionary of state data for serialization.
        """
        return {
            "statename": self.e_name.text(),
            "filepath": self.getImportPath(),
            "autoUpdate": str(self.chb_autoUpdate.isChecked()),
        }
