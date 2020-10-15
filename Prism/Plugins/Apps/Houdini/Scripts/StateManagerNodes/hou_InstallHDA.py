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
# Copyright (C) 2016-2020 Richard Frangenberg
#
# Licensed under GNU GPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


import os

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

import hou
import hou_ImportFile

from PrismUtils.Decorators import err_catcher as err_catcher


class InstallHDAClass(hou_ImportFile.ImportFileClass):
    className = "Install HDA"
    listType = "Import"
    preferredUnit = "meter"
    unpreferredUnit = "centimeter"

    @err_catcher(name=__name__)
    def setup(
        self, state, core, stateManager, node=None, importPath=None, stateData=None
    ):
        self.state = state
        self.core = core
        self.stateManager = stateManager
        self.taskName = None
        self.supportedFormats = self.core.appPlugin.assetFormats

        stateNameTemplate = "{entity}_{task}_{version}"
        self.stateNameTemplate = self.core.getConfig("globals", "defaultImportStateName", dft=stateNameTemplate, configPath=self.core.prismIni)
        self.e_name.setText("HDA - " + self.stateNameTemplate)

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
            import TaskSelection

            ts = TaskSelection.TaskSelection(core=core, importState=self)
            self.core.parentWindow(ts)
            if self.core.uiScaleFactor != 1:
                self.core.scaleUI(self.state, sFactor=0.5)
            ts.exec_()
            importPath = ts.productPath

        if importPath:
            self.e_file.setText(importPath)
            result = self.importObject()

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
    def loadData(self, data):
        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "filepath" in data:
            self.e_file.setText(data["filepath"])
        if "autoUpdate" in data:
            self.chb_autoUpdate.setChecked(eval(data["autoUpdate"]))

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.e_file.editingFinished.connect(self.pathChanged)
        self.b_browse.clicked.connect(self.browse)
        self.b_browse.customContextMenuRequested.connect(self.openFolder)
        self.b_importLatest.clicked.connect(self.importLatest)
        self.chb_autoUpdate.stateChanged.connect(self.autoUpdateChanged)
        if not self.stateManager.standalone:
            self.b_import.clicked.connect(self.importObject)
            self.b_createNode.clicked.connect(self.createNode)

    @err_catcher(name=__name__)
    def importObject(self, taskName=None):
        if self.stateManager.standalone:
            return False

        impFileName = self.getImportPath()
        result = self.validateFilepath(impFileName)
        if result is not True:
            self.core.popup(result)
            return

        hou.hda.installFile(impFileName, force_use_assets=True)
        defs = hou.hda.definitionsInFile(impFileName)
        for definition in defs:
            self.changeAssetDefinitionVersions(definition)

        self.stateManager.saveImports()
        self.updateUi()
        self.stateManager.saveStatesToScene()

        return True

    @err_catcher(name=__name__)
    def changeAssetDefinitionVersions(self, definition):
        namespaceOrder = definition.nodeType().namespaceOrder()
        for namespace in namespaceOrder:
            if namespace == definition.nodeTypeName():
                continue

            nodeType = hou.nodeType(definition.nodeTypeCategory(), namespace)
            for instance in nodeType.instances():
                instance.changeNodeType(definition.nodeType().name())

    @err_catcher(name=__name__)
    def validateFilepath(self, path):
        if not path:
            return "Invalid importpath"

        extension = os.path.splitext(path)[1]
        if extension not in self.supportedFormats:
            return "Format \"%s\" is not supported by this statetype." % extension

        if not os.path.exists(path):
            return "File doesn't exist:\n%s" % path

        return True

    @err_catcher(name=__name__)
    def createNode(self):
        if not self.core.uiAvailable:
            return

        paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        if paneTab is None:
            return

        nodePath = paneTab.pwd()

        if nodePath.isInsideLockedHDA():
            return

        if os.path.exists(self.e_file.text()):
            defs = hou.hda.definitionsInFile(self.e_file.text().replace("\\", "/"))
            if len(defs) > 0:
                tname = defs[0].nodeTypeName()
                mNode = None
                try:
                    mNode = nodePath.createNode(tname)
                    mNode.moveToGoodPosition()
                except:
                    return
        if mNode is None:
            return

        mNode.setDisplayFlag(True)
        if hasattr(mNode, "setRenderFlag"):
            mNode.setRenderFlag(True)
        mNode.setPosition(paneTab.visibleBounds().center())
        mNode.setCurrent(True, clear_all_selected=True)

    @err_catcher(name=__name__)
    def updateUi(self):
        self.l_status.setText("not installed")
        self.l_status.setStyleSheet("QLabel { background-color : rgb(130,0,0); }")
        status = "error"
        if os.path.exists(self.e_file.text()):
            defs = hou.hda.definitionsInFile(self.e_file.text().replace("\\", "/"))
            if len(defs) > 0:
                if defs[0].isInstalled():
                    self.l_status.setText("installed")
                    self.l_status.setStyleSheet(
                        "QLabel { background-color : rgb(0,130,0); }"
                    )
                    status = "ok"

        curVersion, latestVersion = self.checkLatestVersion()

        self.l_curVersion.setText(curVersion or "-")
        self.l_latestVersion.setText(latestVersion or "-")

        if self.chb_autoUpdate.isChecked():
            if curVersion and latestVersion and curVersion != latestVersion:
                self.importLatest(refreshUi=False)
        else:
            if curVersion and latestVersion and curVersion != latestVersion:
                self.b_importLatest.setStyleSheet(
                    "QPushButton { background-color : rgb(150,80,0); border: none;}"
                )
                status = "warning"
            else:
                self.b_importLatest.setStyleSheet("")

        self.nameChanged()
        self.setStateColor(status)

    @err_catcher(name=__name__)
    def getStateProps(self):
        return {
            "statename": self.e_name.text(),
            "filepath": self.e_file.text(),
            "autoUpdate": str(self.chb_autoUpdate.isChecked()),
        }
