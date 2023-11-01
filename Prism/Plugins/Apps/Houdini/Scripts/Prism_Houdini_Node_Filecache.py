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
import logging

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher as err_catcher

import hou

logger = logging.getLogger(__name__)


class Prism_Houdini_Filecache(object):
    def __init__(self, plugin):
        self.plugin = plugin
        self.core = self.plugin.core
        self.initState = None
        self.executeBackground = False
        self.nodeExecuted = False
        self.stateType = "Export"
        self.listType = "Export"

    @err_catcher(name=__name__)
    def getTypeName(self):
        return "prism::Filecache"

    @err_catcher(name=__name__)
    def getFormats(self):
        blacklisted = [".hda", "ShotCam", "other", ".rs"]
        appFormats = self.core.appPlugin.outputFormats
        nodeFormats = [f for f in appFormats if f not in blacklisted]

        tokens = []
        for f in nodeFormats:
            tokens.append(f)
            tokens.append(f)

        return tokens

    @err_catcher(name=__name__)
    def getLocations(self, kwargs):
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
        versions = []
        versions.insert(0, "latest")

        tokens = []
        for v in versions:
            tokens.append(v)
            tokens.append(v)

        return tokens

    @err_catcher(name=__name__)
    def getSaveVersions(self, kwargs):
        versions = []
        versions.insert(0, "next")

        tokens = []
        for v in versions:
            tokens.append(v)
            tokens.append(v)

        return tokens

    @err_catcher(name=__name__)
    def onNodeCreated(self, kwargs):
        self.plugin.onNodeCreated(kwargs)
        kwargs["node"].setColor(hou.Color(0.95, 0.5, 0.05))
        self.fetchStageRange(kwargs)
        self.getStateFromNode(kwargs)

    @err_catcher(name=__name__)
    def fetchStageRange(self, kwargs):
        parent = kwargs["node"].parent()
        while parent and not isinstance(parent, hou.LopNode):
            parent = parent.parent()

        if isinstance(parent, hou.LopNode):
            parent3 = parent
        else:
            parent3 = None

        if parent3 and parent3.inputs():
            stage = parent3.inputs()[0].stage()
            if stage:
                frameRange = self.core.getPlugin("USD").api.getFrameRangeFromStage(stage)
                if frameRange["authored"]:
                    self.plugin.setNodeParm(kwargs["node"], "f1", frameRange["start"], clear=True)
                    self.plugin.setNodeParm(kwargs["node"], "f2", frameRange["end"], clear=True)

    @err_catcher(name=__name__)
    def nodeInit(self, node, state=None):
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
        self.plugin.onNodeDeleted(kwargs)

    @err_catcher(name=__name__)
    def getStateFromNode(self, kwargs):
        return self.plugin.getStateFromNode(kwargs)

    @err_catcher(name=__name__)
    def setTaskFromNode(self, kwargs):
        taskname = self.getProductName(kwargs["node"])
        state = self.getStateFromNode(kwargs)
        if not state:
            return

        state.ui.setTaskname(taskname)
        self.updateLatestVersion(kwargs["node"])

    @err_catcher(name=__name__)
    def setFormatFromNode(self, kwargs):
        state = self.getStateFromNode(kwargs)
        if not state:
            return

        state.ui.setOutputType(kwargs["script_value"])

    @err_catcher(name=__name__)
    def setUpdateMasterVersionFromNode(self, kwargs):
        master = kwargs["node"].parm("updateMasterVersion").eval()
        state = self.getStateFromNode(kwargs)
        state.ui.setUpdateMasterVersion(master)

    @err_catcher(name=__name__)
    def setUpdateMasterVersionOnNode(self, node, master):
        if master != node.parm("updateMasterVersion").eval():
            self.plugin.setNodeParm(node, "updateMasterVersion", master, clear=True)

    @err_catcher(name=__name__)
    def setLocationFromNode(self, kwargs):
        location = kwargs["node"].parm("location").evalAsString()
        state = self.getStateFromNode(kwargs)
        state.ui.setLocation(location)

    @err_catcher(name=__name__)
    def setLocationOnNode(self, node, location):
        if location != node.parm("location").evalAsString():
            if location in node.parm("location").menuItems():
                self.plugin.setNodeParm(node, "location", location, clear=True)

    @err_catcher(name=__name__)
    def showInStateManagerFromNode(self, kwargs):
        self.plugin.showInStateManagerFromNode(kwargs)

    @err_catcher(name=__name__)
    def openInExplorerFromNode(self, kwargs):
        state = self.getStateFromNode(kwargs)
        if not state:
            return

        folderpath = state.ui.l_pathLast.text()
        if not os.path.exists(os.path.dirname(folderpath)):
            impPath = self.getImportPath()
            if os.path.exists(os.path.dirname(impPath)):
                folderpath = impPath

        self.core.openFolder(folderpath)

    @err_catcher(name=__name__)
    def refreshNodeUi(self, node, state, forceCook=False):
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

        lopChild = bool(parent3 and node.parm("showLopFetch") and self.core.getPlugin("USD"))
        node.parm("showLopFetch").set(lopChild)

    @err_catcher(name=__name__)
    def setRangeOnNode(self, node, val):
        idx = node.parm("framerange").menuItems().index(val)
        self.plugin.setNodeParm(node, "framerange", idx, clear=True) 

    @err_catcher(name=__name__)
    def refreshContextFromEntity(self, node, entity, needsToCook=False):
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
        if node.parm("format").evalAsString() == ".abc":
            ropName = "write_alembic"
        else:
            ropName = "write_geo"

        rop = node.node(ropName)
        return rop

    @err_catcher(name=__name__)
    def executeNode(self, node):
        rop = self.getRenderNode(node)

        if self.executeBackground:
            parmName = "executebackground"
        else:
            parmName = "execute"

        rop.parm(parmName).pressButton()
        QCoreApplication.processEvents()
        self.updateLatestVersion(node)
        node.node("switch_abc").cook(force=True)
        if (
            not self.executeBackground
            and node.parm("showSuccessPopup").eval()
            and self.nodeExecuted
            and not rop.errors()
        ):
            self.core.popup(
                "Finished caching successfully.", severity="info", modal=False
            )

        if self.executeBackground:
            return "background"
        else:
            return True

    @err_catcher(name=__name__)
    def executePressed(self, kwargs, background=False):
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

        self.nodeExecuted = True
        self.executeBackground = background
        sm.publish(
            executeState=True,
            useVersion=version,
            states=[state],
            successPopup=False,
            saveScene=saveScene,
            incrementScene=incrementScene,
            sanityChecks=sanityChecks,
            versionWarning=False,
        )
        self.executeBackground = False
        self.nodeExecuted = False
        self.reload(kwargs)

    @err_catcher(name=__name__)
    def submitPressed(self, kwargs):
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
        self.updateLatestVersion(kwargs["node"])

    @err_catcher(name=__name__)
    def latestChanged(self, kwargs):
        self.updateLatestVersion(kwargs["node"])

    @err_catcher(name=__name__)
    def getReadVersionFromNode(self, node):
        if node.parm("latestVersionRead").eval():
            version = "latest"
        else:
            intVersion = node.parm("readVersion").eval()
            version = self.core.versionFormat % intVersion

        return version

    @err_catcher(name=__name__)
    def getWriteVersionFromNode(self, node):
        if node.parm("nextVersionWrite").eval():
            version = "next"
        else:
            intVersion = node.parm("writeVersion").eval()
            version = self.core.versionFormat % intVersion

        return version

    @err_catcher(name=__name__)
    def updateLatestVersion(self, node):
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

            node.parm("writeVersion").set(latestVersion + 1)

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
                node.parm("readVersion").set(latestVersion)

    @err_catcher(name=__name__)
    def getParentFolder(self, create=True, node=None):
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
                "stateenabled": "PySide2.QtCore.Qt.CheckState.Checked",
                "stateexpanded": True,
            }
            state = sm.createState("Folder", stateData=stateData)
            return state

    @err_catcher(name=__name__)
    def findExistingVersion(self, kwargs, mode):
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

        return version

    @err_catcher(name=__name__)
    def getContextSources(self, kwargs):
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
        state = self.getStateFromNode(kwargs)
        if not state:
            return

        self.refreshNodeUi(kwargs["node"], state.ui, forceCook=True)

    @err_catcher(name=__name__)
    def getContextStrFromEntity(self, entity):
        if not entity:
            return ""

        entityType = entity.get("type", "")
        if entityType == "asset":
            entityName = entity.get("asset_path").replace("\\", "/")
        elif entityType == "shot":
            entityName = self.core.entities.getShotName(entity)

        context = "%s - %s" % (entityType.capitalize(), entityName)
        return context

    @err_catcher(name=__name__)
    def selectContextClicked(self, kwargs):
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
        value = self.core.configs.writeJson(context)
        if value != kwargs["node"].parm("customContext").eval():
            self.core.appPlugin.setNodeParm(kwargs["node"], "customContext", value, clear=True)

        state = self.getStateFromNode(kwargs)
        if not state:
            return

        self.refreshNodeUi(kwargs["node"], state.ui)

    @err_catcher(name=__name__)
    def setContextSourceFromNode(self, kwargs):
        state = self.getStateFromNode(kwargs)
        if not state:
            return

        self.refreshNodeUi(kwargs["node"], state.ui)

    @err_catcher(name=__name__)
    def getProductName(self, node):
        return node.parm("task").unexpandedString()

    @err_catcher(name=__name__)
    def getImportPath(self):
        if hou.hipFile.isLoadingHipFile():
            return ""

        sm = self.core.getStateManager(create=True)
        if not sm or self.core.getCurrentFileName() != sm.scenename:
            return ""

        node = hou.pwd()
        state = self.getStateFromNode({"node": node})
        if not state:
            return

        entity = state.ui.getOutputEntity()
        product = hou.text.expandString(self.getProductName(node))
        version = self.getReadVersionFromNode(node)
        if node.parm("readWedgeNum"):
            wedge = node.parm("readWedgeNum").evalAsString() if node.parm("readWedge").eval() else None
        else:
            wedge = None

        if version == "latest":
            path = self.core.products.getLatestVersionpathFromProduct(product, entity=entity, wedge=wedge)
        else:
            path = self.core.products.getVersionpathFromProductVersion(product, version, entity=entity, wedge=wedge)

        if path:
            path = path.replace("\\", "/")
            path = self.core.appPlugin.detectCacheSequence(path)
            path = hou.text.expandString(path)
        else:
            path = ""

        return path

    @err_catcher(name=__name__)
    def getProductNames(self):
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
    def reload(self, kwargs):
        isAbc = kwargs["node"].parm("switch_abc/input").eval()
        if isAbc:
            kwargs["node"].parm("read_alembic/reload").pressButton()
        else:
            kwargs["node"].parm("read_geo/reload").pressButton()

    @err_catcher(name=__name__)
    def getFrameranges(self):
        ranges = ["Save Current Frame", "Save Frame Range", "From State Manager"]
        ranges = [r for r in ranges for _ in range(2)]
        return ranges

    @err_catcher(name=__name__)
    def getFrameRange(self, node):
        if node.parm("framerange").eval() == 0:
            startFrame = self.core.appPlugin.getCurrentFrame()
            endFrame = startFrame
        else:
            startFrame = node.parm("f1").eval()
            endFrame = node.parm("f2").eval()

        return startFrame, endFrame

    @err_catcher(name=__name__)
    def framerangeChanged(self, kwargs):
        state = self.getStateFromNode(kwargs)
        if not state:
            return

        state.ui.setRangeType("Node")
        state.ui.updateUi()

    @err_catcher(name=__name__)
    def getNodeDescription(self):
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
            if fnameData.get("type") in ["asset", "shot"]:
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
        rangeType = node.parm("framerange").evalAsString()
        isSingle = rangeType == "Save Current Frame"
        return isSingle


class Farm_Submitter(QDialog):
    def __init__(self, origin, state, kwargs):
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
    def setupUi(self):
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
    def closeEvent(self, event):
        curItem = self.core.sm.getCurrentItem(self.core.sm.activeList)
        if curItem and self.state and (id(self.state) == id(curItem)):
            self.core.sm.showState()

        if self.showSm:
            self.core.sm.setHidden(False)

        event.accept()

    @err_catcher(name=__name__)
    def submit(self):
        self.hide()
        self.state.ui.gb_submit.setCheckable(True)
        self.state.ui.gb_submit.setChecked(True)

        sanityChecks = bool(self.kwargs["node"].parm("sanityChecks").eval())
        version = self.origin.getWriteVersionFromNode(self.kwargs["node"])
        saveScene = bool(self.kwargs["node"].parm("saveScene").eval())
        incrementScene = saveScene and bool(
            self.kwargs["node"].parm("incrementScene").eval()
        )

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
        )
        if result:
            msg = "Job submitted successfully."
            self.core.popup(msg, severity="info")

        self.close()


class EntityDlg(QDialog):

    entitySelected = Signal(object)

    def __init__(self, origin, parent=None):
        super(EntityDlg, self).__init__()
        self.origin = origin
        self.parentDlg = parent
        self.plugin = self.origin.plugin
        self.core = self.plugin.core
        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self):
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
    def itemDoubleClicked(self, item, column):
        self.buttonClicked("select")

    @err_catcher(name=__name__)
    def buttonClicked(self, button):
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
    def sizeHint(self):
        return QSize(400, 400)
