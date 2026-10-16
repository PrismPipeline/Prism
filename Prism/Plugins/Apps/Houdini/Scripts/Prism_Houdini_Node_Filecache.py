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


"""Houdini Filecache node implementation for Prism.

Provides Prism::Filecache HDA functionality for caching and exporting
geometry/volumes with version management, context switching, and farm submission.
"""

import os
import logging
from typing import Any, Optional, List, Dict, Tuple

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher as err_catcher

import hou

logger = logging.getLogger(__name__)


class Prism_Houdini_Filecache(object):
    """Prism Filecache HDA node manager.
    
    Manages Prism::Filecache nodes for exporting/caching geometry with
    automatic versioning, context management, and render farm integration.
    
    Attributes:
        plugin: Houdini plugin instance.
        core: PrismCore instance.
        initState: Initialization state.
        executeBackground: Background execution flag.
        stateType: State type identifier.
        listType: List type for state manager.
    """
    
    def __init__(self, plugin: Any) -> None:
        """Initialize Filecache node manager.
        
        Args:
            plugin: Houdini plugin instance.
        """
        self.plugin = plugin
        self.core = self.plugin.core
        self.initState = None
        self.executeBackground = False
        self.stateType = "Export"
        self.listType = "Export"

    @err_catcher(name=__name__)
    def getTypeName(self) -> str:
        """Get node type name.
        
        Returns:
            Node type name string.
        """
        return "prism::Filecache"

    @err_catcher(name=__name__)
    def getFormats(self, kwargs=None):
        """Get available output formats for the node.
        
        Args:
            kwargs: Optional node context.
            
        Returns:
            List of supported format strings."""
        blacklisted = [".hda", "ShotCam", "other", ".rs"]
        appFormats = self.core.appPlugin.outputFormats
        nodeFormats = [f for f in appFormats if f not in blacklisted]
        if kwargs and kwargs["node"].parm("showUsdSettings").eval():
            nodeFormats = [n for n in nodeFormats if "usd" in n]

        tokens = []
        for f in nodeFormats:
            tokens.append(f)
            tokens.append(f)

        return tokens

    @err_catcher(name=__name__)
    def getLocations(self, kwargs):
        """Get available export locations.
        
        Args:
            kwargs: Node context.
            
        Returns:
            List of location name strings."""
        if hou.hipFile.isLoadingHipFile():
            return []

        # if function gets called before scene is fully loaded
        sm = self.core.getStateManager(create=True)
        if not sm or self.core.getCurrentFileName() != sm.scenename:
            return []

        if self.initState:
            state = self.initState
        else:
            state = self.getStateFromNode(kwargs)

        if not state:
            return []

        cb = state.ui.cb_outPath
        locations = [cb.itemText(idx) for idx in range(cb.count())]

        tokens = []
        for loc in locations:
            tokens.append(loc)
            tokens.append(loc)

        return tokens

    @err_catcher(name=__name__)
    def getReadVersions(self, kwargs):
        """Get available versions for reading/loading.
        
        Args:
            kwargs: Node context.
            
        Returns:
            List of version strings."""
        versions = []
        versions.insert(0, "latest")

        tokens = []
        for v in versions:
            tokens.append(v)
            tokens.append(v)

        return tokens

    @err_catcher(name=__name__)
    def getSaveVersions(self, kwargs):
        """Get available versions for saving/exporting.
        
        Args:
            kwargs: Node context.
            
        Returns:
            List of version strings."""
        versions = []
        versions.insert(0, "next")

        tokens = []
        for v in versions:
            tokens.append(v)
            tokens.append(v)

        return tokens

    @err_catcher(name=__name__)
    def onNodeCreated(self, kwargs):
        """Handle node creation callback.
        
        Args:
            kwargs: Node creation context."""
        self.plugin.onNodeCreated(kwargs)
        kwargs["node"].setColor(hou.Color(0.95, 0.5, 0.05))
        self.fetchStageRange(kwargs)
        self.getStateFromNode(kwargs)

    @err_catcher(name=__name__)
    def fetchStageRange(self, kwargs):
        """Fetch frame range from current stage/context.
        
        Args:
            kwargs: Node context."""
        parent = kwargs["node"].parent()
        while parent and not isinstance(parent, hou.LopNode):
            parent = parent.parent()

        if isinstance(parent, hou.LopNode):
            parent3 = parent
        else:
            parent3 = None

        if parent3 and parent3.inputs() and parent3.inputs()[0]:
            stage = parent3.inputs()[0].stage()
            usdPlug = self.core.getPlugin("USD")
            if stage and usdPlug:
                frameRange = usdPlug.api.getFrameRangeFromStage(stage)
                if frameRange["authored"]:
                    self.plugin.setNodeParm(kwargs["node"], "f1", frameRange["start"], clear=True)
                    self.plugin.setNodeParm(kwargs["node"], "f2", frameRange["end"], clear=True)

    @err_catcher(name=__name__)
    def nodeInit(self, node, state=None):
        """Initialize node with Prism state.
        
        Args:
            node: Houdini node to initialize.
            state: Optional State Manager state to link."""
        if not state:
            state = self.getStateFromNode({"node": node})

        self.initState = state
        trange = node.parm("framerange").evalAsString()
        task = self.getProductName(node)
        outformat = node.parm("format").evalAsString()
        location = node.parm("location").evalAsString()
        updateMaster = node.parm("updateMasterVersion").eval()
        if trange != "From State Manager":
            state.ui.setRangeType("Node")

        state.ui.setTaskname(task)
        state.ui.setOutputType(outformat)
        state.ui.setLocation(location)
        state.ui.setUpdateMasterVersion(updateMaster)
        self.updateLatestVersion(node)
        self.initState = None

    @err_catcher(name=__name__)
    def onNodeDeleted(self, kwargs):
        """Handle node deletion callback.
        
        Args:
            kwargs: Deletion context."""
        self.plugin.onNodeDeleted(kwargs)

    @err_catcher(name=__name__)
    def getStateFromNode(self, kwargs):
        """Get State Manager state linked to node.
        
        Args:
            kwargs: Node context.
            
        Returns:
            Linked state or None."""
        return self.plugin.getStateFromNode(kwargs)

    @err_catcher(name=__name__)
    def setTaskFromNode(self, kwargs):
        """Set task/product name from node parameter.
        
        Args:
            kwargs: Node context."""
        taskname = self.getProductName(kwargs["node"])
        state = self.getStateFromNode(kwargs)
        if not state:
            return

        state.ui.setTaskname(taskname)
        self.updateLatestVersion(kwargs["node"])

    @err_catcher(name=__name__)
    def setFormatFromNode(self, kwargs):
        """Set output format from node parameter.
        
        Args:
            kwargs: Node context."""
        state = self.getStateFromNode(kwargs)
        if not state:
            return

        state.ui.setOutputType(kwargs["script_value"])

    @err_catcher(name=__name__)
    def setUpdateMasterVersionFromNode(self, kwargs):
        """Set master version update mode from node.
        
        Args:
            kwargs: Node context."""
        master = kwargs["node"].parm("updateMasterVersion").eval()
        state = self.getStateFromNode(kwargs)
        state.ui.setUpdateMasterVersion(master)

    @err_catcher(name=__name__)
    def setUpdateMasterVersionOnNode(self, node, master):
        """Set master version update parameter on node.
        
        Args:
            node: Target node.
            master: Master version mode string."""
        if master != node.parm("updateMasterVersion").eval():
            self.plugin.setNodeParm(node, "updateMasterVersion", master, clear=True)

    @err_catcher(name=__name__)
    def setLocationFromNode(self, kwargs):
        """Set export location from node parameter.
        
        Args:
            kwargs: Node context."""
        location = kwargs["node"].parm("location").evalAsString()
        state = self.getStateFromNode(kwargs)
        state.ui.setLocation(location)

    @err_catcher(name=__name__)
    def setLocationOnNode(self, node, location):
        """Set location parameter on node.
        
        Args:
            node: Target node.
            location: Location name string."""
        if location != node.parm("location").evalAsString():
            if location in node.parm("location").menuItems():
                self.plugin.setNodeParm(node, "location", location, clear=True)

    @err_catcher(name=__name__)
    def showInStateManagerFromNode(self, kwargs):
        """Show linked state in State Manager.
        
        Args:
            kwargs: Node context."""
        self.plugin.showInStateManagerFromNode(kwargs)

    @err_catcher(name=__name__)
    def openInFromNode(self, kwargs):
        """Open exported cache in external application.
        
        Args:
            kwargs: Node context."""
        state = self.getStateFromNode(kwargs)
        if not state:
            return

        folderpath = state.ui.l_pathLast.text()

        parent = self.core.messageParent
        menu = QMenu(parent)

        act_open = QAction("Open in Product Browser", parent)
        act_open.triggered.connect(lambda: self.openInProductBrowser(folderpath))
        menu.addAction(act_open)

        act_open = QAction("Open in explorer", parent)
        act_open.triggered.connect(lambda: self.core.openFolder(folderpath))
        menu.addAction(act_open)

        act_open = QAction("Load in LOPs", parent)
        act_open.triggered.connect(lambda: self.openInLOPs(kwargs, folderpath))
        menu.addAction(act_open)

        act_copy = self.core.getCopyAction(folderpath, parent=parent)
        menu.addAction(act_copy)

        menu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def openInProductBrowser(self, path):
        """Open path in Product Browser.
        
        Args:
            path: File/folder path to open."""
        self.core.projectBrowser()
        self.core.pb.showTab("Products")
        data = self.core.paths.getCachePathData(path)
        self.core.pb.productBrowser.navigateToProduct(data.get("product", ""), entity=data)

    @err_catcher(name=__name__)
    def openInLOPs(self, kwargs, path):
        """Open USD cache in LOPs context.
        
        Args:
            kwargs: Node context.
            path: USD file path."""
        parent = kwargs["node"].parent()
        while parent and (not isinstance(parent, hou.LopNode) or parent.isInsideLockedHDA() or parent.isLockedHDA()):
            parent = parent.parent()

        if isinstance(parent, hou.LopNode):
            parent3 = parent
        else:
            parent3 = hou.node("/stage")

        if hou.nodeType(hou.lopNodeTypeCategory(), "prism::LOP_Import::1.0"):
            lopnode = parent3.createNode("prism::LOP_Import::1.0")
            lopnode.parm("filepath").set(path)
            lopnode.parm("importAs").set(1)
            lopnode.hdaModule().setPath({"node": lopnode, "script_value": path})
        else:
            lopnode = parent3.createNode("sublayer")
            lopnode.parm("filepath1").set(path)

        lopnode.setDisplayFlag(True)
        self.core.appPlugin.goToNode(lopnode)

    @err_catcher(name=__name__)
    def refreshNodeUi(self, node, state, forceCook=False):
        """Refresh node UI with current state.
        
        Args:
            node: Target node.
            state: Linked State Manager state.
            forceCook: Force geometry cook before refresh."""
        taskname = state.getTaskname()
        if taskname != self.getProductName(node):
            self.plugin.setNodeParm(node, "task", taskname, clear=True)

        rangeType = state.getRangeType()
        if rangeType != "Node":
            startFrame, endFrame = state.getFrameRange(rangeType)
            if endFrame is None:
                endFrame = startFrame

            if startFrame != node.parm("f1").eval():
                self.plugin.setNodeParm(node, "f1", startFrame, clear=True)

            if endFrame != node.parm("f2").eval():
                self.plugin.setNodeParm(node, "f2", endFrame, clear=True)

            idx = node.parm("framerange").menuItems().index("From State Manager")
            self.plugin.setNodeParm(node, "framerange", idx, clear=True)

        outType = state.getOutputType()
        if outType != node.parm("format").evalAsString():
            self.plugin.setNodeParm(node, "format", outType, clear=True)

        master = state.getUpdateMasterVersion()
        self.setUpdateMasterVersionOnNode(node, master)

        location = state.getLocation()
        self.setLocationOnNode(node, location)

        entity = state.getOutputEntity(forceCook=forceCook)
        needsToCook = not state.isContextSourceCooked()
        self.refreshContextFromEntity(node, entity, needsToCook=needsToCook)

        parent = node.parent()
        while parent and not isinstance(parent, hou.LopNode):
            parent = parent.parent()

        if isinstance(parent, hou.LopNode):
            parent3 = parent
        else:
            parent3 = None

        usdPlug = self.core.getPlugin("USD")
        lopChild = bool(parent3 and node.parm("showLopFetch") and usdPlug)
        self.plugin.setNodeParm(node, "showLopFetch", lopChild, clear=True) 

    @err_catcher(name=__name__)
    def setRangeOnNode(self, node, val):
        """Set frame range parameter on node.
        
        Args:
            node: Target node.
            val: Range type string."""
        idx = node.parm("framerange").menuItems().index(val)
        self.plugin.setNodeParm(node, "framerange", idx, clear=True) 

    @err_catcher(name=__name__)
    def refreshContextFromEntity(self, node, entity, needsToCook=False):
        """Refresh context display from entity data.
        
        Args:
            node: Target node.
            entity: Entity data dictionary.
            needsToCook: Whether cook is required."""
        if not entity and needsToCook:
            context = "< node not cooked >"
        else:
            context = self.getContextStrFromEntity(entity)
            if needsToCook:
                context += " (not cooked)"

        if context != node.parm("context").eval():
            self.core.appPlugin.setNodeParm(node, "context", context, clear=True)

    @err_catcher(name=__name__)
    def getRenderNode(self, node):
        """Get render/export node inside filecache.
        
        Args:
            node: Filecache node.
            
        Returns:
            Internal render node."""
        if node.parm("format").evalAsString() == ".abc":
            ropName = "write_alembic"
        elif node.parm("format").evalAsString() == ".fbx":
            ropName = "write_fbx"
        elif node.parm("format").evalAsString() in [".usda", ".usdc"]:
            ropName = "write_usd/lopnet_EXPORT/USD_OUT"
        else:
            ropName = "write_geo"

        rop = node.node(ropName)
        return rop

    @err_catcher(name=__name__)
    def executeNode(self, node):
        """Execute cache export on node.
        
        Args:
            node: Filecache node to execute."""
        rop = self.getRenderNode(node)
        self.updateLatestVersion(node)
        if node.parm("useWedging").eval():
            if node.parm("nextVersionWrite").eval():
                node.parm("nextVersionWrite").set(False)
                enableNext = True
            else:
                enableNext = False

            import nodegraphtopui
            topnet = node.node("wedging")
            node.parm("useWedging").set(0)
            node.wedgeInProgress = True
            nodegraphtopui.dirtyAll(topnet, False)
            topnet.cookOutputWorkItems(block=True)
            node.parm("useWedging").set(1)
            node.wedgeInProgress = False
            node.nodeExecuted = True
            if enableNext:
                node.parm("nextVersionWrite").set(True)

        else:
            if self.executeBackground:
                if hou.hipFile.hasUnsavedChanges():
                    hou.hipFile.save()

                parmName = "executebackground"
            else:
                parmName = "execute"

            rop.parm(parmName).pressButton()
            QCoreApplication.processEvents()

        try:
            node.node("switch_format").cook(force=True)
        except:
            pass

        if (
            not self.executeBackground
            and node.parm("showSuccessPopup").eval()
            and getattr(node, "nodeExecuted", False)
            and not rop.errors()
            and not getattr(node, "wedgeInProgress", False)
        ):
            self.core.popup(
                "Finished caching successfully.", severity="info", modal=False
            )

        if not getattr(node, "wedgeInProgress", False):
            self.updateLatestVersion(node)

        if self.executeBackground:
            return "background"
        else:
            if node.parm("useWedging").eval():
                return "wedges"
            else:
                return True

    @err_catcher(name=__name__)
    def executePressed(self, kwargs, background=False):
        """Handle execute button press.
        
        Args:
            kwargs: Button press context.
            background: Execute in background flag."""
        if not kwargs["node"].inputs():
            self.core.popup("No inputs connected")
            return

        sm = self.core.getStateManager()
        if not sm:
            return

        state = self.getStateFromNode(kwargs)
        sanityChecks = bool(kwargs["node"].parm("sanityChecks").eval())
        version = self.getWriteVersionFromNode(kwargs["node"])
        saveScene = bool(kwargs["node"].parm("saveScene").eval())
        incrementScene = saveScene and bool(
            kwargs["node"].parm("incrementScene").eval()
        )
        state.ui.gb_submit.setChecked(False)

        if getattr(state.ui.node, "wedgeInProgress", False):
            saveScene = False
            sanityChecks = False

        state.ui.node.nodeExecuted = True
        self.executeBackground = background
        comment = kwargs["node"].parm("comment").eval()
        sm.publish(
            executeState=True,
            useVersion=version,
            states=[state],
            successPopup=False,
            saveScene=saveScene,
            incrementScene=incrementScene,
            sanityChecks=sanityChecks,
            versionWarning=False,
            comment=comment,
        )
        self.executeBackground = False
        state.ui.node.nodeExecuted = False
        if not kwargs["node"].parm("autorefresh").eval() and kwargs["node"].parm("latestVersionRead").eval():
            self.refreshImportPath(kwargs)

        self.reload(kwargs)

    @err_catcher(name=__name__)
    def submitPressed(self, kwargs):
        """Handle farm submission button press.
        
        Args:
            kwargs: Button press context."""
        if not kwargs["node"].inputs():
            self.core.popup("No inputs connected")
            return

        sm = self.core.getStateManager()
        if not sm:
            return

        state = self.getStateFromNode(kwargs)
        if not state.ui.cb_manager.count():
            msg = "No farm submitter is installed."
            self.core.popup(msg)
            return

        self.submitter = Farm_Submitter(self, state, kwargs)
        self.submitter.show()

    @err_catcher(name=__name__)
    def nextChanged(self, kwargs):
        """Handle 'next version' toggle change.
        
        Args:
            kwargs: Change context."""
        self.updateLatestVersion(kwargs["node"])

    @err_catcher(name=__name__)
    def latestChanged(self, kwargs):
        """Handle 'use latest' toggle change.
        
        Args:
            kwargs: Change context."""
        self.updateLatestVersion(kwargs["node"])
        if not kwargs["node"].parm("autorefresh").eval():
            self.refreshImportPath(kwargs)

    @err_catcher(name=__name__)
    def masterChanged(self, kwargs):
        """Handle 'use master' toggle change.
        
        Args:
            kwargs: Change context."""
        self.updateLatestVersion(kwargs["node"])
        if not kwargs["node"].parm("autorefresh").eval():
            self.refreshImportPath(kwargs)

    @err_catcher(name=__name__)
    def readVersionChanged(self, kwargs):
        """Handle read version selection change.
        
        Args:
            kwargs: Change context."""
        if not kwargs["node"].parm("autorefresh").eval():
            self.refreshImportPath(kwargs)

    @err_catcher(name=__name__)
    def useWedgeChanged(self, kwargs):
        """Handle wedge usage toggle change.
        
        Args:
            kwargs: Change context."""
        if not kwargs["node"].parm("autorefresh").eval():
            self.refreshImportPath(kwargs)

    @err_catcher(name=__name__)
    def wedgeChanged(self, kwargs):
        """Handle wedge selection change.
        
        Args:
            kwargs: Change context."""
        if not kwargs["node"].parm("autorefresh").eval():
            self.refreshImportPath(kwargs)

    @err_catcher(name=__name__)
    def getReadVersionFromNode(self, node):
        """Get read version string from node.
        
        Args:
            node: Source node.
            
        Returns:
            Version string."""
        if node.parm("latestVersionRead").eval():
            version = "latest"
        else:
            intVersion = node.parm("readVersion").eval()
            version = self.core.versionFormat % intVersion

        return version

    @err_catcher(name=__name__)
    def getWriteVersionFromNode(self, node):
        """Get write version string from node.
        
        Args:
            node: Source node.
            
        Returns:
            Version string."""
        if node.parm("nextVersionWrite").eval():
            version = "next"
        else:
            intVersion = node.parm("writeVersion").eval()
            version = self.core.versionFormat % intVersion

        return version

    @err_catcher(name=__name__)
    def updateLatestVersion(self, node):
        """Update latest version parameter on node.
        
        Args:
            node: Target node."""
        latestVersion = None
        state = self.getStateFromNode({"node": node})
        if not state:
            return

        entity = state.ui.getOutputEntity()

        if node.parm("nextVersionWrite").eval():
            task = hou.text.expandString(self.getProductName(node))
            versionpath = self.core.products.getLatestVersionpathFromProduct(
                task, includeMaster=False, entity=entity,
            )
            if not versionpath:
                latestVersion = 0
            else:
                latestVersion = self.core.products.getVersionFromFilepath(
                    versionpath, num=True
                ) or 0

            self.core.appPlugin.setNodeParm(node, "writeVersion", latestVersion + 1, clear=True)

        if node.parm("latestVersionRead").eval():
            if latestVersion is None:
                task = hou.text.expandString(self.getProductName(node))
                versionpath = self.core.products.getLatestVersionpathFromProduct(task, entity=entity)
                if not versionpath:
                    latestVersion = 0
                else:
                    latestVersion = self.core.products.getVersionFromFilepath(
                        versionpath, num=True
                    )

            if latestVersion is not None:
                self.core.appPlugin.setNodeParm(node, "readVersion", latestVersion, clear=True)

    @err_catcher(name=__name__)
    def getParentFolder(self, create=True, node=None):
        """Get parent folder path for exports.
        
        Args:
            create: Create folder if missing.
            node: Source node.
            
        Returns:
            Folder path string."""
        sm = self.core.getStateManager()
        if not sm:
            return

        for state in sm.states:
            if state.ui.listType != "Export" or state.ui.className != "Folder":
                continue

            if state.ui.e_name.text() != "Filecaches":
                continue

            return state

        if create:
            stateData = {
                "statename": "Filecaches",
                "listtype": "Export",
                "stateenabled": 2,
                "stateexpanded": True,
            }
            state = sm.createState("Folder", stateData=stateData)
            return state

    @err_catcher(name=__name__)
    def findExistingVersion(self, kwargs, mode):
        """Find existing version for read/write.
        
        Args:
            kwargs: Node context.
            mode: 'read' or 'write' mode."""
        if not getattr(self.core, "projectPath", None):
            return

        import ProductBrowser

        ts = ProductBrowser.ProductBrowser(core=self.core)

        product = hou.text.expandString(self.getProductName(kwargs["node"]))
        state = self.getStateFromNode(kwargs)
        if not state:
            return

        entity = state.ui.getOutputEntity()
        result = ts.navigateToProduct(product, entity=entity)
        widget = ts.tw_versions
        if not result or not widget.rowCount():
            self.core.popup("No versions exist in the current context.")
            return

        if mode == "write":
            usevparm = kwargs["node"].parm("nextVersionWrite")
            vparm = kwargs["node"].parm("writeVersion")
            if kwargs["node"].parm("wedge") and kwargs["node"].parm("wedge").eval():
                wedge = kwargs["node"].parm("wedgeNum").evalAsString()
            else:
                wedge = None
        elif mode == "read":
            usevparm = kwargs["node"].parm("latestVersionRead")
            vparm = kwargs["node"].parm("readVersion")
            if kwargs["node"].parm("readWedgeNum"):
                wedge = kwargs["node"].parm("readWedgeNum").evalAsString() if kwargs["node"].parm("readWedge").eval() else None

        if not usevparm.eval():
            versionName = self.core.versionFormat % vparm.eval()
            if wedge is not None:
                versionName += " (%s)" % wedge

            ts.navigateToVersion(versionName)

        self.core.parentWindow(widget)
        widget.setWindowTitle("Select Version")
        widget.resize(1000, 600)

        ts.productPathSet.connect(
            lambda x, m=mode, k=kwargs: self.versionSelected(x, m, k)
        )
        ts.productPathSet.connect(widget.close)

        widget.show()

    @err_catcher(name=__name__)
    def versionSelected(self, path, mode, kwargs):
        """Handle version selection from browser.
        
        Args:
            path: Selected version path.
            mode: 'read' or 'write' mode.
            kwargs: Selection context."""
        if not path:
            return

        data = self.core.products.getProductDataFromFilepath(path)
        if "version" not in data:
            return

        version = data["version"]
        versionNumber = self.core.products.getIntVersionFromVersionName(version)

        if mode == "write":
            if version == "master":
                kwargs["node"].parm("nextVersionWrite").set(1)
            else:
                kwargs["node"].parm("nextVersionWrite").set(0)
                kwargs["node"].parm("writeVersion").set(versionNumber)

            if kwargs["node"].parm("wedge"):
                if data.get("wedge") is None or data.get("wedge") == "":
                    self.plugin.setNodeParm(kwargs["node"], "wedge", False, clear=True)
                else:
                    self.plugin.setNodeParm(kwargs["node"], "wedge", True, clear=True)
                    self.plugin.setNodeParm(kwargs["node"], "wedgeNum", int(data["wedge"]), clear=True)

        elif mode == "read":
            if version == "master":
                kwargs["node"].parm("latestVersionRead").set(1)
                if kwargs["node"].parm("includeMaster"):
                    kwargs["node"].parm("includeMaster").set(1)
            else:
                kwargs["node"].parm("latestVersionRead").set(0)
                kwargs["node"].parm("readVersion").set(versionNumber)
        
            if kwargs["node"].parm("readWedge"):
                if data.get("wedge") is None or data.get("wedge") == "":
                    self.plugin.setNodeParm(kwargs["node"], "readWedge", False, clear=True)
                else:
                    self.plugin.setNodeParm(kwargs["node"], "readWedge", True, clear=True)
                    self.plugin.setNodeParm(kwargs["node"], "readWedgeNum", int(data["wedge"]), clear=True)

            if not kwargs["node"].parm("autorefresh").eval():
                self.refreshImportPath(kwargs)

        return version

    @err_catcher(name=__name__)
    def getContextSources(self, kwargs):
        """Get available context source options.
        
        Args:
            kwargs: Node context.
            
        Returns:
            List of context source strings."""
        parent = kwargs["node"].parent()
        while parent and not isinstance(parent, hou.LopNode):
            parent = parent.parent()

        if isinstance(parent, hou.LopNode):
            parent3 = parent
        else:
            parent3 = None

        if parent3 and self.core.getPlugin("USD"):
            sources = ["From USD stage meta data", "From scenefile", "Custom"]
        else:
            sources = ["From scenefile", "Custom"]

        tokens = []
        for source in sources:
            tokens.append(source)
            tokens.append(source)

        return tokens

    @err_catcher(name=__name__)
    def refreshPressed(self, kwargs):
        """Handle context refresh button press.
        
        Args:
            kwargs: Button press context."""
        state = self.getStateFromNode(kwargs)
        if not state:
            return

        self.refreshNodeUi(kwargs["node"], state.ui, forceCook=True)

    @err_catcher(name=__name__)
    def getContextStrFromEntity(self, entity):
        """Get context display string from entity.
        
        Args:
            entity: Entity data dictionary.
            
        Returns:
            Context display string."""
        if not entity:
            return ""

        entityType = entity.get("type", "")
        if entityType == "asset":
            entityName = entity.get("asset_path", "").replace("\\", "/")
        elif entityType == "shot":
            entityName = self.core.entities.getShotName(entity)

        context = "%s - %s" % (entityType.capitalize(), entityName)
        return context

    @err_catcher(name=__name__)
    def selectContextClicked(self, kwargs):
        """Handle context selection button click.
        
        Args:
            kwargs: Click context."""
        dlg = EntityDlg(self)
        data = self.core.configs.readJson(data=kwargs["node"].parm("customContext").eval().replace("\\", "/"), ignoreErrors=False)
        if not data:
            state = self.getStateFromNode(kwargs)
            if not state:
                return

            data = state.ui.getOutputEntity()

        dlg.w_entities.navigate(data)
        dlg.entitySelected.connect(lambda x: self.setCustomContext(kwargs, x))
        dlg.show()

    @err_catcher(name=__name__)
    def setCustomContext(self, kwargs, context):
        """Set custom output context.
        
        Args:
            kwargs: Node context.
            context: Custom context dictionary."""
        value = self.core.configs.writeJson(context)
        if value != kwargs["node"].parm("customContext").eval():
            self.core.appPlugin.setNodeParm(kwargs["node"], "customContext", value, clear=True)

        state = self.getStateFromNode(kwargs)
        if not state:
            return

        self.refreshNodeUi(kwargs["node"], state.ui)

    @err_catcher(name=__name__)
    def setContextSourceFromNode(self, kwargs):
        """Set context source from node parameter.
        
        Args:
            kwargs: Node context."""
        state = self.getStateFromNode(kwargs)
        if not state:
            return

        self.refreshNodeUi(kwargs["node"], state.ui)

    @err_catcher(name=__name__)
    def getProductName(self, node):
        """Get product/task name from node.
        
        Args:
            node: Source node.
            
        Returns:
            Product name string."""
        parm = node.parm("task")
        if parm.keyframes():
            val = parm.eval()
        else:
            val = parm.unexpandedString()

        return val

    @err_catcher(name=__name__)
    def isPrismFilecacheNode(self, node):
        """Check if node is a Prism Filecache.
        
        Args:
            node: Node to check.
            
        Returns:
            True if Prism Filecache node."""
        if not self.core.appPlugin.isNodeValid(self, node):
            return False

        if node.type().name().startswith("prism::Filecache"):
            return True

        return False

    @err_catcher(name=__name__)
    def getImportPath(self, expand=True, node=None):
        """Get import/read cache path from node.
        
        Args:
            expand: Expand variables in path.
            node: Source node.
            
        Returns:
            Import path string."""
        if hou.hipFile.isLoadingHipFile():
            return ""

        sm = self.core.getStateManager(create=True)
        if not sm or self.core.getCurrentFileName() != sm.scenename:
            return ""

        node = node or hou.pwd()
        state = self.getStateFromNode({"node": node})
        if not state:
            return

        if self.isPrismFilecacheNode(node) and node.parm("showUsdSettings").eval():
            usdPlug = self.core.getPlugin("USD")
            if not usdPlug:
                self.core.popup("USD plugin is not loaded.")
                return

            return usdPlug.api.usdExport.getImportPath(expand=expand, node=node)

        entity = state.ui.getOutputEntity()
        product = hou.text.expandString(self.getProductName(node))
        version = self.getReadVersionFromNode(node)
        if node.parm("readWedgeNum"):
            wedge = node.parm("readWedgeNum").evalAsString() if node.parm("readWedge").eval() else None
        else:
            wedge = None

        if version == "latest":
            includeMaster = node.parm("includeMaster").eval()
            path = self.core.products.getLatestVersionpathFromProduct(product, includeMaster=includeMaster, entity=entity, wedge=wedge)
        else:
            path = self.core.products.getVersionpathFromProductVersion(product, version, entity=entity, wedge=wedge)

        if path:
            path = path.replace("\\", "/")
            incr = node.parm("f3").eval() / node.parm("substeps").eval()
            if incr < 1:
                subframeStr = f"`pythonexprs('\"%0{self.core.framePadding}d.%03d\" % (int(hou.timeToFrame(hou.time())), round(int(hou.timeToFrame(hou.time()) * (1 / {incr})) / (1 / {incr}) % 1, 3) * 1000)')`"
            else:
                subframeStr = None

            path = self.core.appPlugin.detectCacheSequence(path, subframeStr=subframeStr)
            path = self.core.appPlugin.getPathRelativeToProject(path) if self.core.appPlugin.getUseRelativePath() else path
            if expand:
                path = hou.text.expandString(path)
        else:
            path = ""

        if path != node.parm("importPathFallback").eval():
            self.core.appPlugin.setNodeParm(node, "importPathFallback", path, clear=True)

        return path

    @err_catcher(name=__name__)
    def getProductNames(self):
        """Get available product names from project.
        
        Returns:
            List of product name strings."""
        names = []
        node = hou.pwd()
        state = self.getStateFromNode({"node": node})
        if not state:
            return

        data = state.ui.getOutputEntity()
        if not data or "type" not in data:
            return names

        names = self.core.products.getProductNamesFromEntity(data)
        names = sorted(names)
        names = [name for name in names for _ in range(2)]
        return names

    @err_catcher(name=__name__)
    def autoRefreshToggled(self, kwargs):
        """Handle auto-refresh toggle change.
        
        Args:
            kwargs: Toggle context."""
        auto = kwargs["node"].parm("autorefresh").eval()
        if auto:
            kwargs["node"].parm("importPath").setExpression("hou.phm().getImportPath()", language=hou.exprLanguage.Python)
        else:
            self.refreshImportPath(kwargs)

    @err_catcher(name=__name__)
    def refreshImportPath(self, kwargs):
        """Refresh import path from current settings.
        
        Args:
            kwargs: Node context."""
        path = self.getImportPath(expand=False)
        self.plugin.setNodeParm(kwargs["node"], "importPath", path, clear=True)

    @err_catcher(name=__name__)
    def reload(self, kwargs):
        """Reload cache from disk.
        
        Args:
            kwargs: Reload context."""
        isAbc = kwargs["node"].parm("switch_format/input").eval() == 1
        isUsd = kwargs["node"].parm("switch_format/input").eval() == 2
        if isAbc:
            kwargs["node"].parm("read_alembic/reload").pressButton()
        elif isUsd:
            kwargs["node"].parm("read_usd/reload").pressButton()
        else:
            kwargs["node"].parm("read_geo/reload").pressButton()

    @err_catcher(name=__name__)
    def getFrameranges(self):
        """Get available frame range types.
        
        Returns:
            List of range type strings."""
        ranges = ["Save Current Frame", "Save Frame Range", "From State Manager"]
        ranges = [r for r in ranges for _ in range(2)]
        return ranges

    @err_catcher(name=__name__)
    def getFrameRange(self, node):
        """Get frame range from node.
        
        Args:
            node: Source node.
            
        Returns:
            Tuple of (startFrame, endFrame)."""
        if node.parm("framerange").eval() == 0:
            startFrame = self.core.appPlugin.getCurrentFrame()
            endFrame = startFrame
        else:
            startFrame = node.parm("f1").eval()
            endFrame = node.parm("f2").eval()

        return startFrame, endFrame

    @err_catcher(name=__name__)
    def framerangeChanged(self, kwargs):
        """Handle frame range type change.
        
        Args:
            kwargs: Change context."""
        state = self.getStateFromNode(kwargs)
        if not state:
            return

        state.ui.setRangeType("Node")
        state.ui.updateUi()

    @err_catcher(name=__name__)
    def getNodeDescription(self):
        """Get node description/help text.
        
        Returns:
            Description string."""
        node = hou.pwd()
        if self.core.separateOutputVersionStack:
            version = self.getWriteVersionFromNode(node)
            if version == "next":
                version += " (%s)" % (
                    self.core.versionFormat % node.parm("writeVersion").eval()
                )
        else:
            fileName = self.core.getCurrentFileName()
            fnameData = self.core.getScenefileData(fileName)
            if fnameData.get("type") in ["asset", "shot"] and "version" in fnameData:
                version = fnameData["version"]
            else:
                version = self.core.versionFormat % self.core.lowestVersion

        descr = hou.text.expandString(self.getProductName(node)) + "\n" + version

        if not node.parm("latestVersionRead").eval():
            readv = self.core.versionFormat % node.parm("readVersion").eval()
            descr += "\nRead: " + readv

        return descr

    @err_catcher(name=__name__)
    def isSingleFrame(self, node):
        """Check if node exports single frame.
        
        Args:
            node: Node to check.
            
        Returns:
            True if single frame mode."""
        rangeType = node.parm("framerange").evalAsString()
        isSingle = rangeType == "Save Current Frame"
        return isSingle


class Farm_Submitter(QDialog):
    """Dialog for submitting Filecache jobs to render farm.
    
    Provides UI for configuring farm submission parameters and executing
    the submission through the configured render manager.
    """
    
    def __init__(self, origin: Any, state: Any, kwargs: Dict[str, Any]) -> None:
        """Initialize farm submission dialog.
        
        Args:
            origin: Filecache node manager instance.
            state: State Manager state.
            kwargs: Node context dictionary.
        """
        super(Farm_Submitter, self).__init__()
        self.origin = origin
        self.plugin = self.origin.plugin
        self.core = self.plugin.core
        self.core.parentWindow(self)
        self.state = state
        self.kwargs = kwargs
        self.showSm = False
        if self.core.sm.isVisible():
            self.core.sm.setHidden(True)
            self.showSm = True

        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Set up the farm submission dialog UI elements and layout."""
        self.setWindowTitle("Prism Farm Submitter - %s" % self.state.ui.node.path())
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.addWidget(self.state.ui)
        self.state.ui.w_name.setVisible(False)
        self.state.ui.gb_general.setVisible(False)
        self.state.ui.gb_previous.setHidden(True)
        self.state.ui.gb_submit.setCheckable(False)

        if self.state.ui.cb_manager.count() == 1:
            self.state.ui.f_manager.setVisible(False)
            self.state.ui.gb_submit.setTitle(self.state.ui.cb_manager.currentText())

        self.b_submit = QPushButton("Submit")
        self.lo_main.addWidget(self.b_submit)
        self.b_submit.clicked.connect(self.submit)

    @err_catcher(name=__name__)
    def closeEvent(self, event: Any) -> None:
        """Handle dialog close event.
        
        Args:
            event: Qt close event.
        """
        curItem = self.core.sm.getCurrentItem(self.core.sm.activeList)
        if curItem and self.state and (id(self.state) == id(curItem)):
            self.core.sm.showState()

        if self.showSm:
            self.core.sm.setHidden(False)

        event.accept()

    @err_catcher(name=__name__)
    def submit(self) -> None:
        """Submit the filecache job to the render farm."""
        self.hide()
        self.state.ui.gb_submit.setCheckable(True)
        self.state.ui.gb_submit.setChecked(True)

        sanityChecks = bool(self.kwargs["node"].parm("sanityChecks").eval())
        version = self.origin.getWriteVersionFromNode(self.kwargs["node"])
        saveScene = bool(self.kwargs["node"].parm("saveScene").eval())
        incrementScene = saveScene and bool(
            self.kwargs["node"].parm("incrementScene").eval()
        )
        comment = self.kwargs["node"].parm("comment").eval()

        sm = self.core.getStateManager()
        result = sm.publish(
            successPopup=False,
            executeState=True,
            states=[self.state],
            useVersion=version,
            saveScene=saveScene,
            incrementScene=incrementScene,
            sanityChecks=sanityChecks,
            versionWarning=False,
            comment=comment,
        )
        if result:
            msg = "Job submitted successfully."
            self.core.popup(msg, severity="info")

        self.close()


class EntityDlg(QDialog):
    """Dialog for selecting output entity (asset/shot) context.
    
    Provides tree widget navigation for selecting target asset or shot
    for cache export context.
    """

    entitySelected = Signal(object)

    def __init__(self, origin: Any, parent: Optional[Any] = None) -> None:
        """Initialize entity selection dialog.
        
        Args:
            origin: Filecache node manager instance.
            parent: Optional parent widget.
        """
        super(EntityDlg, self).__init__()
        self.origin = origin
        self.parentDlg = parent
        self.plugin = self.origin.plugin
        self.core = self.plugin.core
        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Set up the entity dialog UI with entity tree widget and buttons."""
        title = "Select entity"

        self.setWindowTitle(title)
        self.core.parentWindow(self, parent=self.parentDlg)

        import EntityWidget
        self.w_entities = EntityWidget.EntityWidget(core=self.core, refresh=True)
        self.w_entities.editEntitiesOnDclick = False
        self.w_entities.getPage("Assets").tw_tree.itemDoubleClicked.connect(self.itemDoubleClicked)
        self.w_entities.getPage("Shots").tw_tree.itemDoubleClicked.connect(self.itemDoubleClicked)
        self.w_entities.getPage("Assets").setSearchVisible(False)
        self.w_entities.getPage("Shots").setSearchVisible(False)

        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Select", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Close", QDialogButtonBox.RejectRole)

        self.bb_main.clicked.connect(self.buttonClicked)

        self.lo_main.addWidget(self.w_entities)
        self.lo_main.addWidget(self.bb_main)

    @err_catcher(name=__name__)
    def itemDoubleClicked(self, item: Any, column: int) -> None:
        """Handle tree item double-click.
        
        Args:
            item: Clicked tree widget item.
            column: Column index.
        """
        self.buttonClicked("select")

    @err_catcher(name=__name__)
    def buttonClicked(self, button: Any) -> None:
        """Handle dialog button click.
        
        Emits entitySelected signal with selected entity data on OK.
        
        Args:
            button: Clicked button widget.
        """
        if button == "select" or button.text() == "Select":
            entities = self.w_entities.getCurrentData()
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

            self.entitySelected.emit(validEntities[0])

        self.close()

    @err_catcher(name=__name__)
    def sizeHint(self) -> Any:
        """Get preferred dialog size.
        
        Returns:
            QSize for dialog dimensions.
        """
        return QSize(400, 400)
