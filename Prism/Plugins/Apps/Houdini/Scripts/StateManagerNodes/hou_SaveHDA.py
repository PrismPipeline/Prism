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

"""Houdini Save HDA state for Prism State Manager.

Exports Houdini nodes as versioned HDA (Houdini Digital Asset) files to the
Prism product library. Supports black box compilation, external references,
project HDAs, and automatic version management.
"""

import os
import time
import platform
from typing import Any, Optional, Dict, List, Tuple, Union

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

import hou
import hou_Export

from PrismUtils.Decorators import err_catcher as err_catcher


class SaveHDAClass(hou_Export.ExportClass):
    """State for exporting Houdini nodes as versioned HDAs.
    
    Extends ExportClass to save nodes as HDA files with versioning,
    optional black box compilation, and project HDA support.
    
    Attributes:
        className (str): State type identifier.
        listType (str): State list category.
        stateCategories (Dict): State category definitions.
        node: Connected Houdini node to export.
        nodePath (str): Path to connected node.
    """
    
    className = "Save HDA"
    listType = "Export"
    stateCategories = {"Export": [{"label": className, "stateType": className}]}

    @err_catcher(name=__name__)
    def setup(self, state: Any, core: Any, stateManager: Any, node: Optional[Any] = None, stateData: Optional[Dict] = None) -> None:
        """Initialize Save HDA state.
        
        Sets up UI, connects node if provided, and loads saved state data.
        
        Args:
            state: State Manager tree item.
            core: PrismCore instance.
            stateManager: State Manager instance.
            node: Optional node to connect.
            stateData: Optional saved state data to load.
        """
        self.state = state
        self.core = core
        self.stateManager = stateManager
        self.canSetVersion = True
        self.customEntity = None

        self.node = None
        self.nodes = []
        self.nodePath = ""

        self.e_name.setText(self.className + " - {product} ({node})")
        self.l_name.setVisible(False)
        self.e_name.setVisible(False)
        self.core.callback("onStateStartup", self)

        self.export_paths = self.core.paths.getExportProductBasePaths()
        self.cb_outPath.addItems(list(self.export_paths.keys()))
        if len(self.export_paths) < 2:
            self.w_outPath.setVisible(False)

        if node is None and not self.stateManager.standalone:
            if stateData is None:
                self.connectNodes()
        else:
            if isinstance(node, list):
                self.chb_recipe.setChecked(True)
                self.connectNodes(node)
            else:
                self.connectNodes([node])

        self.nameChanged(self.e_name.text())
        self.connectEvents()

        self.b_changeTask.setStyleSheet(
            "QPushButton { background-color: rgb(150,0,0); border: none;}"
        )

        if stateData is not None:
            self.loadData(stateData)
        else:
            entity = self.getOutputEntity()
            if entity.get("task"):
                self.l_taskName.setText(entity.get("task"))
                self.b_changeTask.setStyleSheet("")

    @err_catcher(name=__name__)
    def loadData(self, data: Dict) -> None:
        """Load state data from dictionary.
        
        Restores product name, connected node, output path, HDA options,
        and last export path.
        
        Args:
            data: Dictionary containing saved state data.
        """
        self.updateUi()

        if "stateName" in data:
            self.e_name.setText(data["stateName"])
        elif "statename" in data:
            self.e_name.setText(data["statename"] + " - {product} ({node})")
        if "taskname" in data:
            self.setProductname(data["taskname"])
        if "productname" in data:
            self.setProductname(data["productname"])
        if "connectednode" in data:
            node = hou.node(data["connectednode"])
            if node is None:
                node = self.findNode(data["connectednode"])
            self.connectNodes([node])
        if "connectednodes" in data and data["connectednodes"]:
            nodes = []
            for nodePath in data["connectednodes"]:
                node = hou.node(nodePath)
                if node is None:
                    node = self.findNode(nodePath)
                if node is not None:
                    nodes.append(node)
            self.connectNodes(nodes)
        if "curoutputpath" in data:
            idx = self.cb_outPath.findText(data["curoutputpath"])
            if idx != -1:
                self.cb_outPath.setCurrentIndex(idx)
        if "projecthda" in data:
            self.chb_projectHDA.setChecked(data["projecthda"])
        if "externalReferences" in data:
            self.chb_externalReferences.setChecked(data["externalReferences"])
        if "blackboxhda" in data:
            self.chb_blackboxHDA.setChecked(data["blackboxhda"])
        if "recipe" in data:
            self.chb_recipe.setChecked(data["recipe"])
        if "lastexportpath" in data:
            lePath = self.core.fixPath(data["lastexportpath"])

            self.l_pathLast.setText(lePath)
            self.l_pathLast.setToolTip(lePath)
        if "stateenabled" in data:
            if type(data["stateenabled"]) == int:
                self.state.setCheckState(
                    0, Qt.CheckState(data["stateenabled"]),
                )

        self.nameChanged(self.e_name.text())
        self.core.callback("onStateSettingsLoaded", self, data)

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect UI widget signals to handlers.
        
        Links buttons, text fields, checkboxes to their respective
        handlers and state save operations.
        """
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.b_changeTask.clicked.connect(self.changeTask)
        self.cb_outPath.activated.connect(self.stateManager.saveStatesToScene)
        self.chb_projectHDA.stateChanged.connect(
            lambda x: self.w_outPath.setEnabled(not x)
        )
        self.chb_projectHDA.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_externalReferences.stateChanged.connect(
            self.stateManager.saveStatesToScene
        )
        self.chb_blackboxHDA.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_recipe.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.b_pathLast.clicked.connect(lambda: self.stateManager.showLastPathMenu(self))

        if not self.stateManager.standalone:
            self.b_goTo.clicked.connect(self.goToNode)
            self.b_connect.clicked.connect(self.connectNodes)

    @err_catcher(name=__name__)
    def getLastPathOptions(self) -> Optional[List[Dict]]:
        """Get context menu options for last export path.
        
        Returns:
            List of menu option dicts with 'label' and 'callback' keys,
            or None if no path exists.
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
    def openInProductBrowser(self, path: str) -> None:
        """Open Product Browser to exported HDA location.
        
        Args:
            path: File path to navigate to.
        """
        self.core.projectBrowser()
        self.core.pb.showTab("Products")
        data = self.core.paths.getCachePathData(path)
        self.core.pb.productBrowser.navigateToVersion(version=data["version"], product=data["product"], entity=data)

    @err_catcher(name=__name__)
    def goToNode(self) -> Optional[bool]:
        """Navigate to and select connected node in network editor.
        
        Returns:
            False if node is invalid, None otherwise.
        """
        try:
            self.nodes[0].name()
        except:
            self.updateUi()
            return False

        self.nodes[0].setCurrent(True, clear_all_selected=True)
        for node in self.nodes[1:]:
            node.setSelected(True)

        paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        if paneTab is not None:
            paneTab.setCurrentNode(self.nodes[0])
            paneTab.homeToSelection()

    @err_catcher(name=__name__)
    def nameChanged(self, text: str) -> None:
        """Handle state name change.
        
        Updates state name with product and node name substitution.
        Ensures unique names by appending numbers if needed.
        
        Args:
            text: New name text (may contain {product}, {node}, {#} placeholders).
        """
        if self.isNodeValid():
            nodeName = self.nodes[0].name()
        else:
            nodeName = "None"

        text = self.e_name.text()
        context = {}
        context["product"] = self.getProductname(expanded=True)
        context["node"] = nodeName

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
    def getOutputType(self) -> str:
        """Get output file extension.
        
        Returns:
            ".hda" extension string.
        """
        return ".hda"

    @err_catcher(name=__name__)
    def isNodeValid(self) -> bool:
        """Check if connected node is valid.
        
        Attempts to reconnect if node path is saved but node reference is lost.
        
        Returns:
            True if node exists and is valid.
        """
        try:
            validTST = self.nodes[0].name()
        except:
            node = self.findNode(self.nodePath)
            if node:
                self.connectNodes([node])
            else:
                self.node = None
                self.nodes = []
                self.nodePath = ""

        return self.node is not None

    @err_catcher(name=__name__)
    def updateUi(self) -> None:
        """Update UI to reflect current node connection status.
        
        Updates status label, enables/disables options based on node validity
        and HDA capabilities.
        """
        if self.isNodeValid():
            if len(self.nodes) > 1:
                statusText = "%s nodes" % (len(self.nodes))
                toolTip = "\n".join([node.path() for node in self.nodes])
            else:
                statusText = self.nodes[0].name()
                toolTip = self.nodes[0].path()

            self.l_status.setText(statusText)
            self.l_status.setToolTip(toolTip)
            self.l_status.setStyleSheet("QLabel { background-color : rgb(0,150,0); }")
        else:
            self.l_status.setText("Not connected")
            self.l_status.setToolTip("")
            self.l_status.setStyleSheet("QLabel { background-color : rgb(150,0,0); }")

        self.w_blackboxHDA.setEnabled(
            (not self.isNodeValid() or (isinstance(self.nodes[0], hou.Node) and self.nodes[0].type().areContentsViewable())) and not self.chb_recipe.isChecked()
        )

        self.w_externalReferences.setEnabled(
            bool(self.nodes and isinstance(self.nodes[0], hou.Node) and self.nodes[0].canCreateDigitalAsset())
        )

        self.nameChanged(self.e_name.text())
        self.w_comment.setHidden(not self.stateManager.useStateComments())

    @classmethod
    @err_catcher(name=__name__)
    def getSelectedNodes(cls) -> Optional[Any]:
        """Get first selected node in Houdini.
        
        Returns:
            First selected node or None.
        """
        if len(hou.selectedNodes()) == 0:
            return

        nodes = hou.selectedNodes()
        return nodes

    @classmethod
    @err_catcher(name=__name__)
    def getSelectedItems(cls) -> Optional[Any]:
        """Get first selected node in Houdini.
        
        Returns:
            First selected node or None.
        """
        if len(hou.selectedItems()) == 0:
            return

        items = hou.selectedItems()
        return items

    @classmethod
    @err_catcher(name=__name__)
    def canConnectNode(cls, node: Optional[Any] = None) -> bool:
        """Check if node can be connected to this state.
        
        Args:
            node: Node to check (uses selected node if None).
            
        Returns:
            True if node is connectable.
        """
        if node is None:
            nodes = cls.getSelectedNodes()
            if not nodes:
                return False

            node = nodes[0]

        return cls.isConnectableNode(node)

    @staticmethod
    def isConnectableNode(node: Any, recipe: bool = False) -> bool:
        """Check if node can create or has an HDA definition.
        
        Args:
            node: Node to check.
            recipe: Whether to consider recipe state.
            
        Returns:
            True if node can be exported as HDA.
        """
        if recipe:
            return True

        if node and isinstance(node, hou.Node) and (node.canCreateDigitalAsset() or node.type().definition()):
            return True

        return False

    @err_catcher(name=__name__)
    def connectNodes(self, nodes: Optional[Any] = None) -> bool:
        """Connect node to this state.
        
        Args:
            nodes: Nodes to connect (uses selected node if None).
            
        Returns:
            True if connection successful.
        """
        if nodes is None:
            nodes = self.getSelectedItems()
            if not nodes:
                return False
            
        if self.isConnectableNode(node=nodes[0], recipe=self.chb_recipe.isChecked()):
            self.node = nodes[0]
            self.nodes = nodes
            self.nodePath = self.node.path()
            if isinstance(self.node, hou.Node):
                self.node.setUserData("PrismPath", self.nodePath)

            self.nameChanged(self.e_name.text())
            self.updateUi()
            self.stateManager.saveStatesToScene()
            return True

        return False

    @err_catcher(name=__name__)
    def preDelete(self, item: Any, silent: bool = False) -> None:
        """Handle pre-delete event.
        
        Args:
            item: Tree item being deleted.
            silent: Whether to skip confirmation dialogs.
        """
        pass

    @err_catcher(name=__name__)
    def preExecuteState(self) -> List[Any]:
        """Check for warnings before state execution.
        
        Validates product name, node validity, and output path length.
        
        Returns:
            List containing state name and list of warning messages.
        """
        warnings = []

        if not self.getProductname(expanded=True):
            warnings.append(["No productname is given.", "", 3])

        if not self.isNodeValid():
            warnings.append(["Node is invalid.", "", 3])
        else:
            result = self.getOutputName()
            if result:
                outputName, outputPath, hVersion = result
                outLength = len(outputName)
                if platform.system() == "Windows" and os.getenv("PRISM_IGNORE_PATH_LENGTH") != "1" and outLength > 255:
                    msg = (
                        "The outputpath is longer than 255 characters (%s), which is not supported on Windows."
                        % outLength
                    )
                    description = "Please shorten the outputpath by changing the comment, productname or projectpath."
                    warnings.append([msg, description, 3])

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def runSanityChecks(self) -> Dict[str, Any]:
        """Run pre-execution validation checks.
        
        Returns:
            Dict with 'checks' list and 'passed' boolean.
        """
        result = {}
        result["checks"] = self.preExecuteState()[1]
        result["passed"] = (
            len([check for check in result["checks"] if check[2] == 3]) == 0
        )
        return result

    @err_catcher(name=__name__)
    def generateExecutionResult(self, sanityResult: Dict) -> List[str]:
        """Generate execution result messages from sanity check results.
        
        Args:
            sanityResult: Dict from runSanityChecks().
            
        Returns:
            List of error message strings.
        """
        result = []
        for check in sanityResult["checks"]:
            if check[2] == 3:
                msg = (
                    self.state.text(0)
                    + ": error - %s Skipped the activation of this state." % check[0]
                )
                result.append(msg)

        return result

    @err_catcher(name=__name__)
    def getOutputName(self, useVersion: str = "next") -> Optional[Tuple[str, str, str]]:
        """Generate output file path for HDA export.
        
        Args:
            useVersion: Version string or "next" for auto-increment.
            
        Returns:
            Tuple (outputPath, outputFolder, version) or None if generation failed.
        """
        version = useVersion if useVersion != "next" else None
        user = None
        comment = self.getComment()

        result = self.core.appPlugin.getHDAOutputpath(
            node=self.node,
            task=self.getProductname(),
            comment=comment,
            user=user,
            version=version,
            location=self.cb_outPath.currentText(),
            projectHDA=self.chb_projectHDA.isChecked(),
            entity=self.getOutputEntity(),
        )

        if not result:
            return

        return result["outputPath"], result["outputFolder"], result["version"]

    @err_catcher(name=__name__)
    def executeState(self, parent: Any, useVersion: str = "next") -> List[str]:
        """Execute HDA export.
        
        Runs sanity checks, generates output path, executes callbacks,
        saves version info, and exports HDA file.
        
        Args:
            parent: Parent state or submission object.
            useVersion: Version string or "next" for auto-increment.
            
        Returns:
            List with status message.
        """
        sanityResult = self.runSanityChecks()
        if not sanityResult["passed"]:
            return self.generateExecutionResult(sanityResult)

        ropNodes = self.nodes
        fileName = self.core.getCurrentFileName()
        entity = self.getOutputEntity()
        result = self.getOutputName(useVersion=useVersion)
        if not result:
            return

        outputName, outputPath, hVersion = result

        kwargs = {
            "state": self,
            "scenefile": fileName,
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

        details = entity.copy()
        if "filename" in details:
            del details["filename"]

        if "extension" in details:
            del details["extension"]

        details["version"] = hVersion
        details["sourceScene"] = fileName
        details["product"] = self.getProductname()
        details["comment"] = self.getComment()

        self.core.saveVersionInfo(
            filepath=os.path.dirname(outputName),
            details=details,
        )

        self.l_pathLast.setText(outputName)
        self.l_pathLast.setToolTip(outputName)

        self.stateManager.saveStatesToScene()
        if self.stateManager.actionSaveDuringPub.isChecked():
            hou.hipFile.save()

        version = int(hVersion[1:]) if hVersion else None
        result = self.exportHDA(ropNodes, outputName, version)

        kwargs = {
            "state": self,
            "scenefile": fileName,
            "result": result,
            "outputpath": outputName,
        }
        self.core.callback("postExport", **kwargs)

        if result is True:
            if len(os.listdir(os.path.dirname(outputName))) > 0:
                result = True
            else:
                result = "unknown error (file doesn't exist)"

        if result is True:
            return [self.state.text(0) + " - success"]
        else:
            erStr = "%s ERROR - hou_SaveHDA %s:\n%s" % (
                time.strftime("%d/%m/%y %X"),
                self.core.version,
                result,
            )
            if result == "unknown error (files do not exist)":
                msg = "No files were created during the rendering. If you think this is a Prism bug please report it in the forum:\nwww.prism-pipeline.com/forum/\nor write a mail to contact@prism-pipeline.com"
                self.core.popup(msg)
            elif not result.startswith("Execute Canceled"):
                self.core.writeErrorLog(erStr)

            return [self.state.text(0) + " - error - " + str(result)]

    @err_catcher(name=__name__)
    def exportHDA(self, nodes: Any, outputPath: str, version: str) -> Union[bool, str]:
        """Export nodes as Houdini Digital Assets.
        
        Creates HDAs with proper naming, versioning, and optional black box compilation.
        Handles both project HDAs and regular versioned HDAs.
        
        Args:
            nodes: Houdini nodes to export as HDAs.
            outputPath: Target HDA file path.
            version: Version string or number.
            
        Returns:
            True on success, "Execute Canceled" on user cancellation, or False on error.
        """
        entity = self.getOutputEntity()
        if entity.get("type") == "asset":
            name = os.path.basename(entity["asset_path"])
        elif entity.get("type") == "shot":
            name = self.core.entities.getShotName(entity)
        productName = self.getProductname()
        typeName = "%s_%s" % (name, productName)

        label = typeName
        createBlackBox = self.chb_blackboxHDA.isChecked()
        allowExtRef = self.chb_externalReferences.isChecked()
        projectHDA = self.chb_projectHDA.isChecked()
        recipe = self.chb_recipe.isChecked()
        node = nodes[0]

        if isinstance(node, hou.Node) and node.canCreateDigitalAsset():
            convertNode = not createBlackBox
        else:
            convertNode = True

        if projectHDA:
            typeName = productName
            outputPath = None
            label = self.getProductname()
            version = "increment"

        # hou.HDADefinition.copyToHDAFile converts "-" to "_"
        typeName = typeName.replace("-", "_")
        label = label.replace("-", "_")

        result = self.core.appPlugin.createHDA(
            nodes,
            outputPath=outputPath,
            typeName=typeName,
            label=label,
            version=version,
            blackBox=createBlackBox,
            allowExternalReferences=allowExtRef,
            projectHDA=projectHDA,
            convertNode=convertNode,
            recipe=recipe,
        )
        if result and not isinstance(result, bool):
            self.connectNodes([result])

        self.updateUi()

        if result:
            return True
        else:
            return "Execute Canceled"

    @err_catcher(name=__name__)
    def getStateProps(self) -> Dict[str, Any]:
        """Get state properties for serialization.
        
        Returns:
            Dictionary containing all state settings for saving to scene.
        """
        try:
            curNode = self.node.path()
            if isinstance(self.node, hou.Node):
                self.node.setUserData("PrismPath", curNode)

            curNodes = [node.path() for node in self.nodes]
        except:
            curNode = None
            curNodes = []

        stateProps = {
            "stateName": self.e_name.text(),
            "productname": self.getProductname(),
            "curoutputpath": self.cb_outPath.currentText(),
            "connectednode": curNode,
            "connectednodes": curNodes,
            "projecthda": self.chb_projectHDA.isChecked(),
            "externalReferences": self.chb_externalReferences.isChecked(),
            "blackboxhda": self.chb_blackboxHDA.isChecked(),
            "recipe": self.chb_recipe.isChecked(),
            "lastexportpath": self.l_pathLast.text(),
            "stateenabled": self.core.getCheckStateValue(self.state.checkState(0)),
        }

        return stateProps
