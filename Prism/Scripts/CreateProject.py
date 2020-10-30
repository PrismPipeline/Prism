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
import sys
import imp

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *
    psVersion = 1

for i in ["CreateProject_ui", "CreateProject_ui_ps2"]:
    try:
        del sys.modules[i]
    except:
        pass

if psVersion == 1:
    import CreateProject_ui
else:
    import CreateProject_ui_ps2 as CreateProject_ui

try:
    import ProjectCreated
except:
    modPath = imp.find_module("ProjectCreated")[1]
    if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
        os.remove(modPath)
    import ProjectCreated

from PrismUtils.Decorators import err_catcher


class CreateProject(QDialog, CreateProject_ui.Ui_dlg_createProject):
    def __init__(self, core):
        QDialog.__init__(self)
        self.core = core
        if self.core.uiAvailable:
            self.setupUi(self)
            self.core.parentWindow(self)
            getattr(self.core.appPlugin, "createProject_startup", lambda x: None)(self)

            nameTT = "The name of the new project.\nThe project name will be visible at different locations in the Prism user interface."
            self.l_name.setToolTip(nameTT)
            self.e_name.setToolTip(nameTT)
            pathTT = "This is the directory, where the project will be saved.\nThis folder should be empty or should not exist.\nThe project name will NOT be appended automatically to this path."
            self.l_path.setToolTip(pathTT)
            self.e_path.setToolTip(pathTT)
            self.b_browse.setToolTip("Select a folder on the current PC")
            self.gb_folderStructure.setToolTip(
                'This list defines the top-level folder structure of the project.\nDouble-Click a name or a type to edit an existing folder.\nFoldertypes marked with an "*" have to be defined before the project can be created.\nAdditional folders can be created manually later on.'
            )

            self.connectEvents()

            self.e_name.setFocus()

        self.prjFolders = self.core.projects.getDefaultProjectFolders()
        self.enableCleanup = True

        self.setupFolders()
        self.core.callback(
            name="onCreateProjectOpen",
            types=["custom"],
            args=[self],
        )

    @err_catcher(name=__name__)
    def enterEvent(self, event):
        QApplication.restoreOverrideCursor()

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.b_browse.clicked.connect(self.browse)
        self.e_name.textEdited.connect(lambda x: self.validateText(x, self.e_name))
        self.e_path.textEdited.connect(lambda x: self.validateText(x, self.e_path))

        self.tw_dirStruct.mousePrEvent = self.tw_dirStruct.mousePressEvent
        self.tw_dirStruct.mousePressEvent = lambda x: self.mouseClickEvent(x)
        self.tw_dirStruct.mouseClickEvent = self.tw_dirStruct.mouseReleaseEvent
        self.tw_dirStruct.mouseReleaseEvent = lambda x: self.mouseClickEvent(x)
        self.tw_dirStruct.doubleClicked.connect(self.dClickItem)

        self.b_addDir.clicked.connect(self.addDir)
        self.b_delDir.clicked.connect(self.delDir)
        self.b_upDir.clicked.connect(self.upDir)
        self.b_downDir.clicked.connect(self.downDir)

        self.b_create.clicked.connect(self.createClicked)

    @err_catcher(name=__name__)
    def mouseClickEvent(self, event):
        if QEvent != None:
            if event.type() == QEvent.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    index = self.tw_dirStruct.indexAt(event.pos())
                    if index.data() == None:
                        self.tw_dirStruct.setCurrentIndex(
                            self.tw_dirStruct.model().createIndex(-1, 0)
                        )
                    self.tw_dirStruct.mouseClickEvent(event)

            else:
                self.tw_dirStruct.mousePrEvent(event)

    @err_catcher(name=__name__)
    def validateText(self, origText, pathUi):
        if pathUi == self.e_name:
            allowChars = ["_"]
        else:
            allowChars = ["/", "\\", "_", " ", ":"]

        self.core.validateLineEdit(pathUi, allowChars=allowChars)

    @err_catcher(name=__name__)
    def browse(self):
        path = QFileDialog.getExistingDirectory(
            self.core.messageParent, "Select project folder", self.e_path.text()
        )
        if path != "":
            self.e_path.setText(path)
            self.validateText(path, self.e_path)

    @err_catcher(name=__name__)
    def setupFolders(self):
        if self.core.uiAvailable:
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["Prefix", "Name", "Type"])
            self.tw_dirStruct.setModel(model)
            self.tw_dirStruct.setColumnWidth(1, 300)

            for i in self.prjFolders:
                self.addDir(i[0].split("_", 1)[1], i[1])

    @err_catcher(name=__name__)
    def dClickItem(self, index):
        if index.column() == 1:
            self.tw_dirStruct.edit(index)
        elif index.column() == 2:
            model = self.tw_dirStruct.model()
            existingTypes = []
            for i in range(model.rowCount()):
                rType = model.index(i, 2).data()
                existingTypes.append(rType)

            typeMenu = QMenu(self)

            for i in ["Scenes*", "Assets*", "Dailies"]:
                if i not in existingTypes:
                    cAct = QAction(i, self)
                    cAct.triggered.connect(lambda y=None, x=i: model.setData(index, x))
                    typeMenu.addAction(cAct)

            cAct = QAction("Default", self)
            cAct.triggered.connect(lambda: model.setData(index, "Default"))
            typeMenu.addAction(cAct)

            typeMenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def addDir(self, name="", dirType="Default"):
        model = self.tw_dirStruct.model()
        row = []
        row.append(QStandardItem("%02d_" % (model.rowCount() + 1)))
        row.append(QStandardItem(name))
        row.append(QStandardItem(dirType))

        model.appendRow(row)

    @err_catcher(name=__name__)
    def delDir(self):
        selIdx = self.tw_dirStruct.selectedIndexes()
        if len(selIdx) > 0:
            model = self.tw_dirStruct.model()
            model.removeRow(selIdx[0].row())
            self.refreshPrefix()

    @err_catcher(name=__name__)
    def upDir(self):
        selIdx = self.tw_dirStruct.selectedIndexes()
        if len(selIdx) > 0 and selIdx[0].row() > 0:
            model = self.tw_dirStruct.model()
            row = []
            row.append(QStandardItem(""))
            row.append(QStandardItem(model.index(selIdx[0].row(), 1).data()))
            row.append(QStandardItem(model.index(selIdx[0].row(), 2).data()))
            model.insertRow(selIdx[0].row() - 1, row)
            self.tw_dirStruct.setCurrentIndex(model.index(selIdx[0].row() - 1, 0))
            model.removeRow(selIdx[0].row() + 1)
            self.refreshPrefix()

    @err_catcher(name=__name__)
    def downDir(self):
        selIdx = self.tw_dirStruct.selectedIndexes()
        model = self.tw_dirStruct.model()
        if len(selIdx) > 0 and (selIdx[0].row() + 1) < model.rowCount():
            row = []
            row.append(QStandardItem(""))
            row.append(QStandardItem(model.index(selIdx[0].row(), 1).data()))
            row.append(QStandardItem(model.index(selIdx[0].row(), 2).data()))
            model.insertRow(selIdx[0].row() + 2, row)
            self.tw_dirStruct.setCurrentIndex(model.index(selIdx[0].row() + 2, 0))
            model.removeRow(selIdx[0].row())

            self.refreshPrefix()

    @err_catcher(name=__name__)
    def refreshPrefix(self):
        model = self.tw_dirStruct.model()
        for i in range(model.rowCount()):
            model.setData(model.index(i, 0), "%02d_" % (i + 1))

    @err_catcher(name=__name__)
    def createClicked(self):
        prjName = self.e_name.text()
        prjPath = self.e_path.text()

        if self.core.uiAvailable:
            self.prjFolders = []
            model = self.tw_dirStruct.model()

            # adding numbers to the foldernames
            for i in range(model.rowCount()):
                fName = model.index(i, 1).data()
                if fName != "":
                    self.prjFolders.append(
                        [model.index(i, 0).data() + fName, model.index(i, 2).data()]
                    )

        settings = {"projectFolders": self.prjFolders}
        result = self.core.projects.createProject(name=prjName, path=prjPath, settings=settings)

        if result:
            self.core.changeProject(prjPath)
            self.pc = ProjectCreated.ProjectCreated(
                prjName, core=self.core, basepath=prjPath
            )
            self.pc.exec_()

            self.close()

    @err_catcher(name=__name__)
    def closeEvent(self, event):
        self.setParent(None)
