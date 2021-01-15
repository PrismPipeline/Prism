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
import time
import platform

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

import hou
import hou_Export

from PrismUtils.Decorators import err_catcher as err_catcher


class SaveHDAClass(hou_Export.ExportClass):
    className = "Save HDA"
    listType = "Export"

    @err_catcher(name=__name__)
    def setup(self, state, core, stateManager, node=None, stateData=None):
        self.state = state
        self.core = core
        self.stateManager = stateManager

        self.node = None
        self.nodePath = ""

        self.e_name.setText(self.className)
        self.l_name.setVisible(False)
        self.e_name.setVisible(False)

        self.export_paths = self.core.paths.getExportProductBasePaths()
        self.cb_outPath.addItems(list(self.export_paths.keys()))
        if len(self.export_paths) < 2:
            self.w_outPath.setVisible(False)

        if node is None and not self.stateManager.standalone:
            if stateData is None:
                self.connectNode()
        else:
            self.connectNode(node)

        self.nameChanged(self.e_name.text())
        self.connectEvents()

        self.b_changeTask.setStyleSheet(
            "QPushButton { background-color: rgb(150,0,0); border: none;}"
        )

        if stateData is not None:
            self.loadData(stateData)
        else:
            fileName = self.core.getCurrentFileName()
            fnameData = self.core.getScenefileData(fileName)

            if fnameData.get("category"):
                self.l_taskName.setText(fnameData.get("category"))
                self.b_changeTask.setStyleSheet("")

    @err_catcher(name=__name__)
    def loadData(self, data):
        self.updateUi()

        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "taskname" in data:
            self.l_taskName.setText(data["taskname"])
            if data["taskname"] != "":
                self.b_changeTask.setStyleSheet("")
        if "connectednode" in data:
            node = hou.node(data["connectednode"])
            if node is None:
                node = self.findNode(data["connectednode"])
            self.connectNode(node)
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
        if "lastexportpath" in data:
            lePath = self.core.fixPath(data["lastexportpath"])

            self.l_pathLast.setText(lePath)
            self.l_pathLast.setToolTip(lePath)
            pathIsNone = self.l_pathLast.text() == "None"
            self.b_openLast.setEnabled(not pathIsNone)
            self.b_copyLast.setEnabled(not pathIsNone)
        if "stateenabled" in data:
            self.state.setCheckState(0, Qt.CheckState(data["stateenabled"]))

        self.nameChanged(self.e_name.text())

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.b_changeTask.clicked.connect(self.changeTask)
        self.cb_outPath.activated[str].connect(self.stateManager.saveStatesToScene)
        self.chb_projectHDA.stateChanged.connect(
            lambda x: self.w_outPath.setEnabled(not x)
        )
        self.chb_projectHDA.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_externalReferences.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_blackboxHDA.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.b_openLast.clicked.connect(
            lambda: self.core.openFolder(os.path.dirname(self.l_pathLast.text()))
        )
        self.b_copyLast.clicked.connect(
            lambda: self.core.copyToClipboard(self.l_pathLast.text())
        )
        if not self.stateManager.standalone:
            self.b_goTo.clicked.connect(self.goToNode)
            self.b_connect.clicked.connect(self.connectNode)

    @err_catcher(name=__name__)
    def nameChanged(self, text):
        if self.isNodeValid():
            nodeName = self.node.name()
        else:
            nodeName = "None"

        sText = text + " - %s (%s)" % (self.l_taskName.text(), nodeName)

        if self.state.text(0).endswith(" - disabled"):
            sText += " - disabled"

        self.state.setText(0, sText)

    @err_catcher(name=__name__)
    def isNodeValid(self):
        try:
            validTST = self.node.name()
        except:
            node = self.findNode(self.nodePath)
            if node:
                self.connectNode(node)
            else:
                self.node = None
                self.nodePath = ""

        return self.node is not None

    @err_catcher(name=__name__)
    def updateUi(self):
        if self.isNodeValid():
            self.l_status.setText(self.node.name())
            self.l_status.setToolTip(self.node.path())
            self.l_status.setStyleSheet("QLabel { background-color : rgb(0,150,0); }")
        else:
            self.l_status.setText("Not connected")
            self.l_status.setToolTip("")
            self.l_status.setStyleSheet("QLabel { background-color : rgb(150,0,0); }")

        self.w_blackboxHDA.setEnabled(
            not self.isNodeValid() or self.node.type().areContentsViewable()
        )

        self.w_externalReferences.setEnabled(bool(
            self.node and
            self.node.canCreateDigitalAsset())
        )

        self.nameChanged(self.e_name.text())

    @classmethod
    @err_catcher(name=__name__)
    def getSelectedNode(self):
        if len(hou.selectedNodes()) == 0:
            return

        node = hou.selectedNodes()[0]
        return node

    @classmethod
    @err_catcher(name=__name__)
    def canConnectNode(self, node=None):
        if node is None:
            node = self.getSelectedNode()
            if not node:
                return False

        if node.canCreateDigitalAsset() or node.type().definition():
            return True

        return False

    @err_catcher(name=__name__)
    def connectNode(self, node=None):
        if node is None:
            node = self.getSelectedNode()

        if self.canConnectNode(node=node):
            self.node = node
            self.nodePath = self.node.path()
            self.node.setUserData("PrismPath", self.nodePath)
            self.nameChanged(self.e_name.text())
            self.updateUi()
            self.stateManager.saveStatesToScene()
            return True

        return False

    @err_catcher(name=__name__)
    def preDelete(self, item, silent=False):
        pass

    @err_catcher(name=__name__)
    def preExecuteState(self):
        warnings = []

        if self.l_taskName.text() == "":
            warnings.append(["No taskname is given.", "", 3])

        if not self.isNodeValid():
            warnings.append(["Node is invalid.", "", 3])
        else:
            result = self.getOutputName()
            if result:
                outputName, outputPath, hVersion = result
                outLength = len(outputName)
                if platform.system() == "Windows" and outLength > 255:
                    msg = (
                        "The outputpath is longer than 255 characters (%s), which is not supported on Windows."
                        % outLength
                    )
                    description = "Please shorten the outputpath by changing the comment, taskname or projectpath."
                    warnings.append([msg, description, 3])

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def runSanityChecks(self):
        result = {}
        result["checks"] = self.preExecuteState()[1]
        result["passed"] = len([check for check in result["checks"] if check[2] == 3]) == 0
        return result

    @err_catcher(name=__name__)
    def generateExecutionResult(self, sanityResult):
        result = []
        for check in sanityResult["checks"]:
            if check[2] == 3:
                msg = self.state.text(0) + ": error - %s. Skipped the activation of this state." % check[0]
                result.append(msg)

        return result

    @err_catcher(name=__name__)
    def getOutputName(self, useVersion="next"):
        version = useVersion
        comment = None
        user = None
        if version != "next":
            versionData = version.split(self.core.filenameSeparator)
            if len(versionData) == 3:
                version, comment, user = versionData

        fileName = self.core.getCurrentFileName()
        fnameData = self.core.getScenefileData(fileName)
        if comment is None and fnameData.get("entity") != "invalid":
            comment = fnameData["comment"]

        result = self.core.appPlugin.getHDAOutputpath(
            node=self.node,
            task=self.l_taskName.text(),
            comment=comment,
            user=user,
            version=version,
            location=self.cb_outPath.currentText(),
            projectHDA=self.chb_projectHDA.isChecked(),
        )

        if not result:
            return

        return result["outputPath"], result["outputFolder"], result["version"]

    @err_catcher(name=__name__)
    def executeState(self, parent, useVersion="next"):
        sanityResult = self.runSanityChecks()
        if not sanityResult["passed"]:
            return self.generateExecutionResult(sanityResult)

        ropNode = self.node
        fileName = self.core.getCurrentFileName()
        result = self.getOutputName(useVersion=useVersion)
        if not result:
            return

        outputName, outputPath, hVersion = result

        self.core.saveVersionInfo(
            location=os.path.dirname(outputName),
            version=hVersion,
            origin=fileName,
        )

        self.l_pathLast.setText(outputName)
        self.l_pathLast.setToolTip(outputName)
        self.b_openLast.setEnabled(True)
        self.b_copyLast.setEnabled(True)

        self.stateManager.saveStatesToScene()
        hou.hipFile.save()

        version = int(hVersion[1:]) if hVersion else None
        result = self.exportHDA(ropNode, outputName, version)
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
    def exportHDA(self, node, outputPath, version):
        fileName = self.core.getCurrentFileName()
        data = self.core.getScenefileData(fileName)
        entityName = data.get("entityName", "")
        taskName = self.l_taskName.text()
        typeName = "%s_%s" % (entityName, taskName)

        label = typeName
        createBlackBox = self.chb_blackboxHDA.isChecked()
        allowExtRef = self.chb_externalReferences.isChecked()
        projectHDA = self.chb_projectHDA.isChecked()

        if node.canCreateDigitalAsset():
            convertNode = not createBlackBox
        else:
            convertNode = True

        if projectHDA:
            typeName = taskName
            outputPath = None
            label = self.l_taskName.text()
            version = "increment"

        # hou.HDADefinition.copyToHDAFile converts "-" to "_"
        typeName = typeName.replace("-", "_")
        label = label.replace("-", "_")

        result = self.core.appPlugin.createHDA(
            node,
            outputPath=outputPath,
            typeName=typeName,
            label=label,
            version=version,
            blackBox=createBlackBox,
            allowExternalReferences=allowExtRef,
            projectHDA=projectHDA,
            convertNode=convertNode,
        )
        if result and not isinstance(result, bool):
            self.connectNode(result)

        self.updateUi()

        if result:
            return True
        else:
            return "Execute Canceled"

    @err_catcher(name=__name__)
    def getStateProps(self):
        try:
            curNode = self.node.path()
            self.node.setUserData("PrismPath", curNode)
        except:
            curNode = None

        stateProps = {
            "statename": self.e_name.text(),
            "taskname": self.l_taskName.text(),
            "curoutputpath": self.cb_outPath.currentText(),
            "connectednode": curNode,
            "projecthda": self.chb_projectHDA.isChecked(),
            "externalReferences": self.chb_externalReferences.isChecked(),
            "blackboxhda": self.chb_blackboxHDA.isChecked(),
            "lastexportpath": self.l_pathLast.text(),
            "stateenabled": int(self.state.checkState(0)),
        }

        return stateProps
