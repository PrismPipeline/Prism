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

from PrismUtils.Decorators import err_catcher


class ImportFileClass(object):
    @err_catcher(name=__name__)
    def setup(
        self, state, core, stateManager, node=None, importPath=None, stateData=None
    ):
        self.state = state
        self.e_name.setText(state.text(0))

        self.className = "ImportFile"
        self.listType = "Import"
        self.stateMode = "ImportFile"

        # self.l_name.setVisible(False)
        # self.e_name.setVisible(False)

        self.core = core
        self.stateManager = stateManager
        self.importPath = None
        self.taskName = ""
        self.setName = ""
        self.importPath = importPath

        self.nodes = []
        self.nodeNames = []

        self.f_abcPath.setVisible(False)
        self.f_keepRefEdits.setVisible(False)
        self.updatePrefUnits()

        self.oldPalette = self.b_importLatest.palette()
        self.updatePalette = QPalette()
        self.updatePalette.setColor(QPalette.Button, QColor(200, 100, 0))
        self.updatePalette.setColor(QPalette.ButtonText, QColor(255, 255, 255))

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

            core.parentWindow(ts)
            ts.exec_()

        if self.importPath is not None:
            self.e_file.setText(self.importPath[1])
            result = self.importObject(taskName=self.importPath[0])
            self.importPath = None

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

        if stateData is not None:
            self.loadData(stateData)

        self.nameChanged(state.text(0))

    @err_catcher(name=__name__)
    def setStateMode(self, stateMode):
        self.stateMode = stateMode
        self.l_class.setText(stateMode)
        self.e_name.setText(stateMode)

    @err_catcher(name=__name__)
    def loadData(self, data):
        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "statemode" in data:
            self.setStateMode(data["statemode"])
        if "filepath" in data:
            data["filepath"] = getattr(
                self.core.appPlugin, "sm_import_fixImportPath", lambda x, y: y
            )(self, data["filepath"])
            self.e_file.setText(data["filepath"])
        if "keepedits" in data:
            self.chb_keepRefEdits.setChecked(eval(data["keepedits"]))
        if "autonamespaces" in data:
            self.chb_autoNameSpaces.setChecked(eval(data["autonamespaces"]))
        if "updateabc" in data:
            self.chb_abcPath.setChecked(eval(data["updateabc"]))
        if "trackobjects" in data:
            self.chb_trackObjects.setChecked(eval(data["trackobjects"]))
        if "preferunit" in data:
            self.chb_preferUnit.setChecked(eval(data["preferunit"]))
            self.updatePrefUnits()
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

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.e_file.editingFinished.connect(self.pathChanged)
        self.b_browse.clicked.connect(self.browse)
        self.b_browse.customContextMenuRequested.connect(self.openFolder)
        self.b_import.clicked.connect(self.importObject)
        self.b_importLatest.clicked.connect(self.importLatest)
        self.chb_autoUpdate.stateChanged.connect(self.autoUpdateChanged)
        self.chb_keepRefEdits.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_autoNameSpaces.stateChanged.connect(self.autoNameSpaceChanged)
        self.chb_abcPath.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.chb_trackObjects.toggled.connect(self.updateTrackObjects)
        self.chb_preferUnit.stateChanged.connect(lambda x: self.updatePrefUnits())
        self.chb_preferUnit.stateChanged.connect(self.stateManager.saveStatesToScene)
        self.b_selectAll.clicked.connect(self.lw_objects.selectAll)
        if not self.stateManager.standalone:
            self.b_nameSpaces.clicked.connect(
                lambda: self.core.appPlugin.sm_import_removeNameSpaces(self)
            )
            self.b_unitConversion.clicked.connect(
                lambda: self.core.appPlugin.sm_import_unitConvert(self)
            )
            self.lw_objects.itemSelectionChanged.connect(
                lambda: self.core.appPlugin.selectNodes(self)
            )

    @err_catcher(name=__name__)
    def nameChanged(self, text):
        getattr(self.core.appPlugin, "sm_import_nameChanged", lambda x: None)(self)

        if self.taskName != "":
            self.state.setText(0, text + " (" + self.taskName + ")")
        else:
            self.state.setText(0, text)

    @err_catcher(name=__name__)
    def browse(self):
        import TaskSelection

        ts = TaskSelection.TaskSelection(core=self.core, importState=self)

        self.core.parentWindow(ts)
        ts.exec_()

        if self.importPath is not None:
            self.e_file.setText(self.importPath[1])
            self.importObject(taskName=self.importPath[0], update=True)
            self.updateUi()
            self.importPath = None

    @err_catcher(name=__name__)
    def openFolder(self, pos):
        path = self.e_file.text()
        if os.path.isfile(path):
            path = os.path.dirname(path)

        self.core.openFolder(path)

    @err_catcher(name=__name__)
    def pathChanged(self):
        self.stateManager.saveImports()
        self.updateUi()
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def autoUpdateChanged(self, checked):
        self.w_latestVersion.setVisible(not checked)
        self.w_importLatest.setVisible(not checked)

        if checked:
            curVersion, latestVersion = self.checkLatestVersion()
            if self.chb_autoUpdate.isChecked():
                if curVersion and latestVersion and curVersion != latestVersion:
                    self.importLatest()

        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def autoNameSpaceChanged(self, checked):
        self.b_nameSpaces.setEnabled(not checked)
        if not self.stateManager.standalone:
            self.core.appPlugin.sm_import_removeNameSpaces(self)
            self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def getImportPath(self):
        return self.e_file.text().replace("\\", "/")

    @err_catcher(name=__name__)
    def importObject(self, taskName=None, update=False):
        result = True
        if self.stateManager.standalone:
            return result

        impFileName = self.getImportPath()

        if impFileName != "":
            versionInfoPath = os.path.join(
                os.path.dirname(os.path.dirname(impFileName)), "versioninfo.yml"
            )

            impFPS = self.core.getConfig("information", "fps", configPath=versionInfoPath)
            curFPS = self.core.getFPS()
            if impFPS and impFPS != curFPS:
                fString = (
                    "The FPS of the import doesn't match the FPS of the current scene:\n\nCurrent scene FPS:    %s\nImport FPS:                %s"
                    % (curFPS, impFPS)
                )
                msg = QMessageBox(
                    QMessageBox.Warning,
                    "FPS mismatch",
                    fString,
                    QMessageBox.Cancel,
                )
                msg.addButton("Continue", QMessageBox.YesRole)
                self.core.parentWindow(msg)
                action = msg.exec_()

                if action != 0:
                    return False

            if taskName is None:
                vPath = os.path.dirname(impFileName)
                if os.path.basename(vPath) in ["centimeter", "meter"]:
                    vName = os.path.basename(os.path.dirname(vPath))
                    vPath = os.path.dirname(vPath)
                else:
                    vName = os.path.basename(vPath)

                self.taskName = ""
                if len(vName.split(self.core.filenameSeparator)) == 3 and (
                    self.core.getScenePath() in impFileName
                    or (
                        self.core.useLocalFiles
                        and self.core.getScenePath(location="local")
                        in impFileName
                    )
                ):
                    self.taskName = os.path.basename(os.path.dirname(vPath))
                    if self.taskName == "_ShotCam":
                        self.taskName = "ShotCam"
                else:
                    self.taskName = vName
            else:
                self.taskName = taskName

            doImport = True

            parDirName = os.path.basename(os.path.dirname(impFileName))
            if parDirName in ["centimeter", "meter"]:
                prefFile = os.path.join(
                    os.path.dirname(os.path.dirname(impFileName)),
                    self.preferredUnit,
                    os.path.basename(impFileName),
                )
                if parDirName == self.unpreferredUnit and os.path.exists(prefFile):
                    impFileName = prefFile
                    self.e_file.setText(impFileName)

            if self.chb_trackObjects.isChecked():
                getattr(self.core.appPlugin, "sm_import_updateObjects", lambda x: None)(
                    self
                )

            fileName = self.core.getCurrentFileName()

            self.core.callHook(
                "preImport",
                args={
                    "prismCore": self.core,
                    "scenefile": fileName,
                    "importfile": impFileName,
                },
            )

            importResult = self.core.appPlugin.sm_import_importToApp(
                self, doImport=doImport, update=update, impFileName=impFileName
            )

            if importResult is None:
                result = None
                doImport = False
            else:
                result = importResult["result"]
                doImport = importResult["doImport"]
                if result and "mode" in importResult:
                    self.setStateMode(importResult["mode"])

            if doImport:
                self.nodeNames = [
                    self.core.appPlugin.getNodeName(self, x) for x in self.nodes
                ]
                illegalNodes = self.core.checkIllegalCharacters(self.nodeNames)
                if len(illegalNodes) > 0:
                    msgStr = "Objects with non-ascii characters were imported. Prism supports only the first 128 characters in the ascii table. Please rename the following objects as they will cause errors with Prism:\n\n"
                    for i in illegalNodes:
                        msgStr += i + "\n"
                    QMessageBox.warning(self.core.messageParent, "Warning", msgStr)

                if self.chb_autoNameSpaces.isChecked():
                    self.core.appPlugin.sm_import_removeNameSpaces(self)

                if not result:
                    msgStr = "Import failed: %s" % impFileName
                    if self.core.uiAvailable:
                        QMessageBox.warning(
                            self.core.messageParent, "ImportFile", msgStr
                        )
                    else:
                        print(msgStr)

            self.core.callHook(
                "postImport",
                args={
                    "prismCore": self.core,
                    "scenefile": fileName,
                    "importfile": impFileName,
                    "importedObjects": self.nodeNames,
                },
            )

        self.stateManager.saveImports()
        self.updateUi()
        self.stateManager.saveStatesToScene()

        return result

    @err_catcher(name=__name__)
    def importLatest(self, refreshUi=True):
        if refreshUi:
            self.updateUi()
        vPath = os.path.dirname(self.getImportPath())
        if os.path.basename(vPath) in ["centimeter", "meter"]:
            vPath = os.path.dirname(vPath)

        versionPath = os.path.join(os.path.dirname(vPath), self.l_latestVersion.text())
        if os.path.exists(versionPath):
            pPath = os.path.join(versionPath, self.preferredUnit)
            upPath = os.path.join(versionPath, self.unpreferredUnit)
            if os.path.exists(pPath) and len(os.listdir(pPath)) > 0:
                versionPath = pPath
            elif os.path.exists(upPath) and len(os.listdir(upPath)) > 0:
                versionPath = upPath

            for i in os.walk(versionPath):
                if len(i[2]) > 0:
                    for m in i[2]:
                        if (
                            os.path.splitext(m)[1] not in [".txt", ".ini", ".yml", ".xgen"]
                            and m[0] != "."
                        ):
                            fileName = os.path.join(i[0], m)

                            if (
                                getattr(self.core.appPlugin, "shotcamFormat", ".abc")
                                == ".fbx"
                                and self.taskName == "ShotCam"
                                and fileName.endswith(".abc")
                                and os.path.exists(fileName[:-3] + "fbx")
                            ):
                                fileName = fileName[:-3] + "fbx"
                            if fileName.endswith(".mtl") and os.path.exists(
                                fileName[:-3] + "obj"
                            ):
                                fileName = fileName[:-3] + "obj"

                            self.e_file.setText(fileName)
                            self.importObject(update=True)
                            break
                break

    @err_catcher(name=__name__)
    def checkLatestVersion(self):
        curVersion = latestVersion = ""

        if os.path.exists(self.e_file.text()):
            parDir = os.path.dirname(self.e_file.text())
            if os.path.basename(parDir) in ["centimeter", "meter"]:
                versionData = os.path.basename(os.path.dirname(parDir)).split(
                    self.core.filenameSeparator
                )
            else:
                versionData = os.path.basename(parDir).split(
                    self.core.filenameSeparator
                )

            fversionData = os.path.basename(self.e_file.text()).split(
                self.core.filenameSeparator
            )
            fversion = None
            for i in fversionData:
                try:
                    num = int(i[1:])
                except:
                    num = None
                if len(i) == 5 and i[0] == "v" and num is not None:
                    try:
                        x = int(i[1:])
                        fversion = i
                        break
                    except:
                        pass

            if (
                len(versionData) == 3
                and self.core.getScenePath().replace(self.core.projectPath, "")
                in self.e_file.text()
            ):
                curVersion = (
                    versionData[0]
                    + self.core.filenameSeparator
                    + versionData[1]
                    + self.core.filenameSeparator
                    + versionData[2]
                )
                vPath = os.path.dirname(self.e_file.text())
                if os.path.basename(vPath) in ["centimeter", "meter"]:
                    vPath = os.path.dirname(vPath)

                taskPath = os.path.dirname(vPath)
                for i in os.walk(taskPath):
                    folders = i[1]
                    folders.sort()
                    for k in reversed(folders):
                        meterDir = os.path.join(i[0], k, "meter")
                        cmeterDir = os.path.join(i[0], k, "centimeter")
                        if (
                            len(k.split(self.core.filenameSeparator)) == 3
                            and k[0] == "v"
                            and len(k.split(self.core.filenameSeparator)[0]) == 5
                            and (
                                (
                                    os.path.exists(meterDir)
                                    and len(os.listdir(meterDir)) > 0
                                )
                                or (
                                    os.path.exists(cmeterDir)
                                    and len(os.listdir(cmeterDir)) > 0
                                )
                            )
                        ):
                            latestVersion = k
                            break
                    break

        return curVersion, latestVersion

    @err_catcher(name=__name__)
    def updateUi(self):
        curVersion, latestVersion = self.checkLatestVersion()

        self.l_curVersion.setText(curVersion or "-")
        self.l_latestVersion.setText(latestVersion or "-")

        if self.chb_autoUpdate.isChecked():
            if curVersion and latestVersion and curVersion != latestVersion:
                self.importLatest(refreshUi=False)
        else:
            useSS = getattr(self.core.appPlugin, "colorButtonWithStyleSheet", False)
            if curVersion and latestVersion and curVersion != latestVersion:
                if useSS:
                    self.b_importLatest.setStyleSheet(
                        "QPushButton { background-color: rgb(200,100,0); }"
                    )
                else:
                    self.b_importLatest.setPalette(self.updatePalette)
            else:
                if useSS:
                    self.b_importLatest.setStyleSheet("")
                else:
                    self.b_importLatest.setPalette(self.oldPalette)

        isCache = self.stateMode == "ApplyCache"
        self.f_nameSpaces.setVisible(not isCache)
        self.f_unitConversion.setVisible(not isCache)
        self.w_preferUnit.setVisible(not isCache)

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

        self.nameChanged(self.e_name.text())

    @err_catcher(name=__name__)
    def updatePrefUnits(self):
        pref = self.core.appPlugin.preferredUnit
        if self.chb_preferUnit.isChecked():
            if pref == "centimeter":
                pref = "meter"
            else:
                pref = "centimeter"

        if pref == "centimeter":
            self.preferredUnit = "centimeter"
            self.unpreferredUnit = "meter"
        else:
            self.preferredUnit = "meter"
            self.unpreferredUnit = "centimeter"

    @err_catcher(name=__name__)
    def updateTrackObjects(self, state):
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
        item=None,
        baseText="Do you also want to delete the connected objects?\n\n",
    ):
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
                    action = 0
                    print("delete objects:\n\n%s" % message)
                else:
                    msg = QMessageBox(
                        QMessageBox.Question, "Delete state", message, QMessageBox.No
                    )
                    msg.addButton("Yes", QMessageBox.YesRole)
                    msg.setParent(self.core.messageParent, Qt.Window)
                    action = msg.exec_()

                if action == 0:
                    self.core.appPlugin.deleteNodes(self, validNodes)

    @err_catcher(name=__name__)
    def getStateProps(self):
        connectedNodes = []
        if self.chb_trackObjects.isChecked():
            for i in range(self.lw_objects.count()):
                connectedNodes.append(
                    [self.lw_objects.item(i).text(), self.nodes[i]]
                )

        return {
            "statename": self.e_name.text(),
            "statemode": self.stateMode,
            "filepath": self.e_file.text(),
            "autoUpdate": str(self.chb_autoUpdate.isChecked()),
            "keepedits": str(self.chb_keepRefEdits.isChecked()),
            "autonamespaces": str(self.chb_autoNameSpaces.isChecked()),
            "updateabc": str(self.chb_abcPath.isChecked()),
            "trackobjects": str(self.chb_trackObjects.isChecked()),
            "preferunit": str(self.chb_preferUnit.isChecked()),
            "connectednodes": connectedNodes,
            "taskname": self.taskName,
            "nodenames": str(self.nodeNames),
            "setname": self.setName,
        }
