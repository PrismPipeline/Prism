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
import sys

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils import PrismWidgets
from PrismUtils.Decorators import err_catcher

from UserInterfacesPrism import CreateProject_ui


class CreateProject(QDialog, CreateProject_ui.Ui_dlg_createProject):
    def __init__(self, core):
        QDialog.__init__(self)
        self.core = core
        self.prevName = ""
        if self.core.uiAvailable:
            self.loadLayout()

        self.enableCleanup = True
        self.core.callback(
            name="onCreateProjectOpen",
            args=[self],
        )
        path = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "background.png")
        self.background = QPixmap(path)

    def paintEvent(self, event):
        pixmap = self.core.media.scalePixmap(self.background, self.width(), self.height(), fitIntoBounds=False)
        painter = QPainter(self)
        painter.setOpacity(0.3)
        painter.drawPixmap(0, 0, pixmap)

    @err_catcher(name=__name__)
    def loadLayout(self):
        self.setupUi(self)
        self.core.parentWindow(self)
        self.sw_project.setStyleSheet("QStackedWidget { background-color: transparent;}")
        self.w_settings = QWidget()
        self.lo_settings = QHBoxLayout(self.w_settings)
        self.lo_settings.setContentsMargins(0, 0, 0, 0)

        self.l_settings = QLabel("Settings:")
        self.cb_settings = QComboBox()
        self.cb_settings.addItems(["Default", "From Preset", "From Project"])
        self.cb_settings.currentIndexChanged.connect(self.onSettingsSourceChanged)
        self.lo_settings.addStretch()
        self.lo_settings.addWidget(self.cb_settings)
        self.lo_settings.addWidget(self.b_reload)

        self.w_start.layout().addWidget(self.l_settings, 2, 0)
        self.w_start.layout().addWidget(self.w_settings, 2, 1)

        self.l_projectSettings = QLabel("Project Settings:")
        self.e_projectSettings = QLineEdit()
        self.e_projectSettings.setText(getattr(self.core, "projectPath", ""))
        self.b_projectSettings = QToolButton()
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "browse.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.b_projectSettings.setIcon(icon)

        self.w_start.layout().addWidget(self.l_projectSettings, 4, 0)
        self.w_start.layout().addWidget(self.e_projectSettings, 4, 1)
        self.w_start.layout().addWidget(self.b_projectSettings, 4, 2)

        getattr(self.core.appPlugin, "createProject_startup", lambda x: None)(self)

        nameTT = "The name of the new project.\nThe project name will be visible at different locations in the Prism user interface."
        self.l_name.setToolTip(nameTT)
        self.e_name.setToolTip(nameTT)
        pathTT = "This is the directory, where the project will be saved.\nThis folder should be empty or should not exist.\nThe project name will NOT be appended automatically to this path."
        self.l_path.setToolTip(pathTT)
        self.e_path.setToolTip(pathTT)
        self.b_browse.setToolTip("Select a folder on the current PC")
        self.tw_structure.setToolTip("Rightclick to add, remove or rename folders")

        self.connectEvents()
        self.e_name.setFocus()

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "browse.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.b_browse.setIcon(icon)

        imgFile = os.path.join(
            self.core.prismRoot,
            "Presets/Projects/Default/00_Pipeline/Fallbacks/noFileBig.jpg",
        )
        pmap = self.core.media.getPixmapFromPath(imgFile)
        self.l_preview.setMinimumSize(pmap.width(), pmap.height())
        self.l_preview.setPixmap(pmap)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "refresh.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_reload.setIcon(icon)
        self.b_reload.setToolTip("Restore Settings")

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_addPreset.setIcon(icon)
        self.b_addPreset.setToolTip("Create new preset from current settings")

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "configure.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_managePresets.setIcon(icon)
        self.b_managePresets.setToolTip("Manage Presets")

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "arrow_right.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_next.setIcon(icon)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "arrow_left.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_back.setIcon(icon)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "create.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_create.setIcon(icon)

        if self.sw_project.currentIndex() == 0:
            self.b_back.setVisible(False)

        presets = self.core.projects.getPresets()
        self.cb_preset.addItems([p["name"] for p in presets])
        self.reloadSettings()

        self.tw_structure.setHeaderLabel("Folder Structure")

        # self.lo_summary = QVBoxLayout()
        # self.w_summary.setLayout(self.lo_summary)

        self.w_complete = QWidget()
        self.lo_complete = QVBoxLayout(self.w_complete)
        self.l_complete = QLabel("Project <b>%s</b> was created successfully!")
        self.l_complete.setAlignment(Qt.AlignCenter)
        self.l_completeIcon = QLabel()
        headerPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "check.png"
        )
        icon = self.core.media.getColoredIcon(headerPath, r=29, g=191, b=106, force=True)
        self.l_completeIcon.setPixmap(icon.pixmap(60, 60))
        self.l_completeIcon.setAlignment(Qt.AlignCenter)
        self.w_completeButtons = QWidget()
        self.lo_completeButtons = QHBoxLayout(self.w_completeButtons)
        self.b_completeBrowser = QPushButton("Open Project Browser")
        self.b_completeBrowser.clicked.connect(self.core.projectBrowser)
        self.b_completeBrowser.clicked.connect(self.accept)
        self.b_completeExplorer = QPushButton("Open in Explorer")
        self.b_completeExplorer.clicked.connect(lambda: self.core.openFolder(self.core.projectPath))
        self.b_completeExplorer.clicked.connect(self.accept)
        self.lo_completeButtons.addStretch()
        self.lo_completeButtons.addWidget(self.b_completeBrowser)
        self.lo_completeButtons.addWidget(self.b_completeExplorer)
        self.lo_completeButtons.addStretch()
        self.lo_complete.addWidget(self.l_complete)
        self.lo_complete.addWidget(self.l_completeIcon)
        self.lo_complete.addWidget(self.w_completeButtons)
        self.scrollArea.widget().layout().addWidget(self.w_complete)
        self.w_complete.setHidden(True)
        self.onSettingsSourceChanged()

    @err_catcher(name=__name__)
    def enterEvent(self, event):
        QApplication.restoreOverrideCursor()

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.b_browse.clicked.connect(self.browse)
        self.e_name.textEdited.connect(self.nameChanged)
        self.e_path.textEdited.connect(lambda x: self.validateText(x, self.e_path))

        self.l_preview.mouseDoubleClickEvent = lambda x: self.browsePreview()
        self.l_preview.mousePressEvent = self.rclPreview
        self.l_preview.customContextMenuRequested.connect(self.rclPreview)

        self.tw_structure.mousePrEvent = self.tw_structure.mousePressEvent
        self.tw_structure.mousePressEvent = lambda x: self.mouseClickEvent(x)
        self.tw_structure.mouseClickEvent = self.tw_structure.mouseReleaseEvent
        self.tw_structure.mouseReleaseEvent = lambda x: self.mouseClickEvent(x)
        self.tw_structure.customContextMenuRequested.connect(self.rclTree)

        self.b_create.clicked.connect(self.createClicked)

        self.cb_settings.activated.connect(lambda x: self.reloadSettings())
        self.e_projectSettings.editingFinished.connect(self.reloadSettings)

        self.b_back.clicked.connect(self.backClicked)
        self.b_next.clicked.connect(self.nextClicked)
        self.cb_preset.activated.connect(lambda x: self.reloadSettings())
        self.b_settings.clicked.connect(self.customizeSettings)
        self.b_reload.clicked.connect(self.reloadSettings)
        self.b_addPreset.clicked.connect(self.createPresetDlg)
        self.b_managePresets.clicked.connect(self.managePresets)
        self.b_projectSettings.clicked.connect(self.browseProjectSettings)

    @err_catcher(name=__name__)
    def nameChanged(self, name):
        self.validateText(name, self.e_name)
        name = self.e_name.text()
        path = self.e_path.text()
        if path:
            if not name or not path.endswith(name):
                base = os.path.basename(path)
                if base == self.prevName:
                    path = os.path.dirname(path)

                path = os.path.join(path, name)
                self.e_path.setText(path)

        self.prevName = name

    @err_catcher(name=__name__)
    def mouseClickEvent(self, event):
        if event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                index = self.tw_structure.indexAt(event.pos())
                if not index.data():
                    self.tw_structure.setCurrentIndex(
                        self.tw_structure.model().createIndex(-1, 0)
                    )
                self.tw_structure.mouseClickEvent(event)

        else:
            self.tw_structure.mousePrEvent(event)

    @err_catcher(name=__name__)
    def rclPreview(self, pos=None):
        rcmenu = QMenu(self)

        exp = QAction("Browse...", self)
        exp.triggered.connect(self.browsePreview)
        rcmenu.addAction(exp)

        copAct = QAction("Capture image", self)
        copAct.triggered.connect(self.capturePreview)
        rcmenu.addAction(copAct)
        clipAct = QAction("Paste image from clipboard", self)
        clipAct.triggered.connect(self.pastePreviewFromClipboard)
        rcmenu.addAction(clipAct)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def capturePreview(self):
        from PrismUtils import ScreenShot

        previewImg = ScreenShot.grabScreenArea(self.core)

        if previewImg:
            previewImg = self.core.media.scalePixmap(
                previewImg,
                self.l_preview.geometry().width(),
                self.l_preview.geometry().height(),
            )
            self.previewMap = previewImg
            self.l_preview.setPixmap(self.previewMap)

    @err_catcher(name=__name__)
    def pastePreviewFromClipboard(self):
        pmap = self.core.media.getPixmapFromClipboard()
        if not pmap:
            self.core.popup("No image in clipboard.")
            return

        pmap = self.core.media.scalePixmap(
            pmap, self.l_preview.geometry().width(), self.l_preview.geometry().height()
        )
        self.previewMap = pmap
        self.l_preview.setPixmap(self.previewMap)

    @err_catcher(name=__name__)
    def browsePreview(self):
        formats = "Image File (*.jpg *.png *.exr)"

        imgPath = QFileDialog.getOpenFileName(
            self, "Select Project Image", self.core.prismRoot, formats
        )[0]

        if not imgPath:
            return

        curGeo = self.l_preview.geometry()
        if os.path.splitext(imgPath)[1] == ".exr":
            pmsmall = self.core.media.getPixmapFromExrPath(
                imgPath, width=curGeo.width(), height=curGeo.height()
            )
        else:
            pm = self.core.media.getPixmapFromPath(imgPath)
            if pm.width() == 0:
                warnStr = "Cannot read image: %s" % imgPath
                self.core.popup(warnStr)
                return

            pmsmall = self.core.media.scalePixmap(pm, curGeo.width(), curGeo.height())

        self.previewMap = pmsmall
        self.l_preview.setPixmap(self.previewMap)

    @err_catcher(name=__name__)
    def onSettingsSourceChanged(self, idx=None):
        source = self.cb_settings.currentText()
        self.l_preset.setHidden(source != "From Preset")
        self.w_preset.setHidden(source != "From Preset")
        self.l_placeholder.setHidden(True)
        self.l_projectSettings.setHidden(source != "From Project")
        self.e_projectSettings.setHidden(source != "From Project")
        self.b_projectSettings.setHidden(source != "From Project")

    @err_catcher(name=__name__)
    def reloadSettings(self):
        source = self.cb_settings.currentText()
        self.projectSettings = None
        if source == "From Preset":
            name = self.cb_preset.currentText()
            preset = self.core.projects.getPreset(name)
            self.projectSettings = self.core.projects.getDefaultProjectSettings()
            self.core.configs.updateNestedDicts(self.projectSettings, preset["settings"])
            self.projectStructure = self.core.projects.getFolderStructureFromPath(preset["path"])
        elif source == "From Project":
            path = self.e_projectSettings.text()
            if path and os.path.isdir(path):
                configPath = self.core.configs.getProjectConfigPath(path)
                if os.path.exists(configPath):
                    settings = self.core.getConfig(configPath=configPath)
                    self.projectSettings = self.core.projects.getDefaultProjectSettings()
                    self.core.configs.updateNestedDicts(self.projectSettings, settings)
                    self.projectStructure = self.core.projects.getFolderStructureFromPath(path, simple=True)

        if source == "Default" or not self.projectSettings:
            self.projectSettings = self.core.projects.getDefaultProjectSettings()
            preset = self.core.projects.getPreset("Default")
            self.projectStructure = self.core.projects.getFolderStructureFromPath(preset["path"])

        self.refreshStructureTree()
        self.core.callback(
            name="onProjectCreationSettingsReloaded",
            args=[self.projectSettings]
        )

    @err_catcher(name=__name__)
    def createPresetDlg(self):
        self.presetItem = PrismWidgets.CreateItem(
            core=self.core, allowChars=["_"], showType=False
        )
        self.core.parentWindow(self.presetItem, parent=self)
        self.presetItem.e_item.setFocus()
        self.presetItem.setWindowTitle("Create Preset")
        self.presetItem.l_item.setText("Preset Name:")
        self.presetItem.accepted.connect(self.createPresetFromCurrent)
        self.presetItem.show()

    @err_catcher(name=__name__)
    def createPresetFromCurrent(self):
        name = self.presetItem.e_item.text()
        settings = self.projectSettings
        structure = self.getStructureFromTree()
        text = "Creating preset. Please Wait..."
        with self.core.waitPopup(self.core, text):
            result = self.core.projects.createPresetFromSettings(
                name, settings, structure
            )

        if result:
            self.refreshPresets()
            msg = 'Created project preset "%s" successfully.' % name
            self.core.popup(msg, severity="info")

    @err_catcher(name=__name__)
    def rclTree(self, pos):
        rcmenu = QMenu(self)

        curItem = self.tw_structure.itemAt(pos)
        act_add = QAction("Add Folder...", self)
        act_add.triggered.connect(lambda: self.addFolderDlg(curItem))
        rcmenu.addAction(act_add)

        if curItem:
            act_rename = QAction("Rename...", self)
            act_rename.triggered.connect(lambda: self.renameItemDlg(curItem))
            rcmenu.addAction(act_rename)

            act_remove = QAction("Remove", self)
            act_remove.triggered.connect(lambda: self.removeItem(curItem))
            rcmenu.addAction(act_remove)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def addFolderDlg(self, parent):
        self.folderItem = PrismWidgets.CreateItem(
            core=self.core, allowChars=["_"], showType=False
        )
        self.core.parentWindow(self.folderItem, parent=self)
        self.folderItem.e_item.setFocus()
        self.folderItem.setWindowTitle("Add Folder")
        self.folderItem.l_item.setText("Folder Name:")
        self.folderItem.accepted.connect(lambda: self.addFolderToItem(parent))
        self.folderItem.show()

    @err_catcher(name=__name__)
    def addFolderToItem(self, parent):
        name = self.folderItem.e_item.text()
        entity = {"name": name, "children": []}
        item = self.addItemToTree(entity, parent)
        if parent:
            parent.setExpanded(True)

        self.tw_structure.setCurrentItem(item)

    @err_catcher(name=__name__)
    def renameItemDlg(self, parent):
        self.rnItem = PrismWidgets.CreateItem(
            core=self.core, allowChars=["_"], showType=False
        )
        self.core.parentWindow(self.rnItem, parent=self)
        self.rnItem.e_item.setFocus()
        self.rnItem.setWindowTitle("Rename")
        self.rnItem.l_item.setText("New Name:")
        self.rnItem.buttonBox.buttons()[0].setText("Rename")
        self.rnItem.e_item.setText(parent.text(0))
        self.rnItem.e_item.selectAll()
        self.rnItem.enableOk(self.rnItem.e_item)
        self.rnItem.accepted.connect(lambda: self.renameItem(parent))
        self.rnItem.show()

    @err_catcher(name=__name__)
    def renameItem(self, item):
        name = self.rnItem.e_item.text()
        item.setText(0, name)

    @err_catcher(name=__name__)
    def removeItem(self, item):
        if item.parent():
            idx = item.parent().indexOfChild(item)
            item.parent().takeChild(idx)
        else:
            idx = self.tw_structure.indexOfTopLevelItem(item)
            self.tw_structure.takeTopLevelItem(idx)

    @err_catcher(name=__name__)
    def getStructureFromTree(self):
        rootEntity = {
            "name": "root",
            "children": [],
        }

        for topIdx in range(self.tw_structure.topLevelItemCount()):
            item = self.tw_structure.topLevelItem(topIdx)
            data = self.getStructureFromTreeItem(item)
            rootEntity["children"].append(data)

        return rootEntity

    @err_catcher(name=__name__)
    def getStructureFromTreeItem(self, item):
        entity = item.data(0, Qt.UserRole)
        entity["name"] = item.text(0)
        if "children" in entity:
            entity["children"] = []
            for idx in range(item.childCount()):
                childItem = item.child(idx)
                data = self.getStructureFromTreeItem(childItem)
                entity["children"].append(data)

        return entity

    @err_catcher(name=__name__)
    def customizeSettings(self):
        self.projectSettings["globals"]["project_name"] = self.getProjectName()
        self.projectSettings["globals"]["project_path"] = self.getProjectPath()
        self.dlg_settings = self.core.projects.openProjectSettings(
            projectData=self.projectSettings
        )
        self.dlg_settings.signalSaved.connect(self.settingsApplied)

    @err_catcher(name=__name__)
    def settingsApplied(self, settings):
        self.projectSettings = settings

    @err_catcher(name=__name__)
    def getProjectName(self):
        return self.e_name.text()

    @err_catcher(name=__name__)
    def getProjectPath(self):
        return self.e_path.text()

    @err_catcher(name=__name__)
    def managePresets(self):
        self.dlg_managePresets = ManagePresets(self)
        self.core.parentWindow(self.dlg_managePresets, parent=self)
        self.dlg_managePresets.signalPresetsChanged.connect(self.refreshPresets)
        self.dlg_managePresets.show()

    @err_catcher(name=__name__)
    def refreshPresets(self):
        self.cb_preset.blockSignals(True)
        cur = self.cb_preset.currentText()

        self.cb_preset.clear()
        presets = self.core.projects.getPresets()
        self.cb_preset.addItems([p["name"] for p in presets])
        idx = self.cb_preset.findText(cur)
        if idx != -1:
            self.cb_preset.setCurrentIndex(idx)
        else:
            self.reloadSettings()

        self.cb_preset.blockSignals(False)

    @err_catcher(name=__name__)
    def refreshStructureTree(self):
        self.tw_structure.clear()
        for entity in self.projectStructure["children"]:
            self.addItemToTree(entity)

    @err_catcher(name=__name__)
    def addItemToTree(self, entity, parent=None):
        item = QTreeWidgetItem([entity["name"]])
        item.setData(0, Qt.UserRole, entity)
        if parent:
            parent.addChild(item)
        else:
            self.tw_structure.addTopLevelItem(item)

        if "children" in entity:
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "folder.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            item.setIcon(0, icon)
            for child in entity["children"]:
                self.addItemToTree(child, parent=item)

        return item

    @err_catcher(name=__name__)
    def validateText(self, origText, pathUi):
        if pathUi == self.e_name:
            allowChars = ["_", " "]
        else:
            allowChars = ["/", "\\", "_", " ", ":"]

        self.core.validateLineEdit(pathUi, allowChars=allowChars)

    @err_catcher(name=__name__)
    def browse(self):
        startpath = self.getProjectPath()
        if not startpath or not os.path.exists(startpath):
            startpath = self.core.prismRoot

        path = QFileDialog.getExistingDirectory(
            self.core.messageParent, "Select project folder", startpath
        )
        if path:
            path = os.path.normpath(path)
            name = self.e_name.text()
            if not path.endswith(name):
                path = os.path.join(path, name)

            self.e_path.setText(path)
            self.validateText(path, self.e_path)

    @err_catcher(name=__name__)
    def browseProjectSettings(self):
        startpath = getattr(self.core, "projectPath", "")
        if not startpath or not os.path.exists(startpath):
            startpath = self.getProjectPath()
            if not startpath or not os.path.exists(startpath):
                startpath = self.core.prismRoot

        path = QFileDialog.getExistingDirectory(
            self.core.messageParent, "Select existing project folder", startpath
        )
        if path:
            if os.path.basename(path) == "00_Pipeline":
                path = os.path.dirname(path)

            self.e_projectSettings.setText(path)
            self.validateText(path, self.e_projectSettings)

    @err_catcher(name=__name__)
    def createClicked(self):
        result = self.runSanityChecks()
        if result:
            msg = "\n".join(result)
            self.core.popup(msg)
            return

        prjName = self.getProjectName()
        prjPath = self.getProjectPath()

        self.projectSettings["globals"]["project_name"] = prjName
        if "project_path" in self.projectSettings["globals"]:
            del self.projectSettings["globals"]["project_path"]

        preset = self.cb_preset.currentText()
        pmap = self.l_preview.pixmap()
        structure = self.getStructureFromTree()
        result = self.core.projects.createProject(
            name=prjName,
            path=prjPath,
            settings=self.projectSettings,
            preset=preset,
            image=pmap,
            structure=structure,
        )

        if result:
            self.core.callback(
                name="onCreateProjectWindowCompleted",
                args=[self, result],
            )

            result = self.core.changeProject(result)
            if not result:
                return

            self.sw_project.setHidden(True)
            self.w_footer.setHidden(True)
            self.l_complete.setText("Project <b>%s</b> was created successfully!" % prjName)
            self.w_complete.setHidden(False)

            # self.pc = ProjectCreated(
            #     prjName, core=self.core, basepath=prjPath
            # )
            # self.pc.exec_()
            # self.close()

    @err_catcher(name=__name__)
    def backClicked(self):
        curIdx = self.sw_project.currentIndex()
        if curIdx == 0:
            return

        self.sw_project.setCurrentIndex(curIdx - 1)
        self.b_next.setVisible(True)
        self.horizontalLayout_3.itemAt(self.horizontalLayout_3.count() - 1).changeSize(
            0, 0
        )
        self.horizontalLayout_3.invalidate()
        if self.sw_project.currentIndex() == 0:
            self.b_back.setVisible(False)

    @err_catcher(name=__name__)
    def nextClicked(self):
        curIdx = self.sw_project.currentIndex()
        if curIdx == (self.sw_project.count() - 1):
            return

        self.sw_project.setCurrentIndex(curIdx + 1)
        self.b_back.setVisible(True)
        if self.sw_project.currentIndex() == (self.sw_project.count() - 1):
            self.b_next.setVisible(False)

    @err_catcher(name=__name__)
    def runSanityChecks(self):
        result = []
        prjName = self.getProjectName()
        if not prjName:
            result.append("The project name is invalid.")

        prjPath = self.getProjectPath()
        if not os.path.isabs(prjPath):
            result.append("The project path is invalid.")

        return result

    @err_catcher(name=__name__)
    def closeEvent(self, event):
        self.setParent(None)


class ManagePresets(QDialog):

    signalPresetsChanged = Signal()

    def __init__(self, parent):
        super(ManagePresets, self).__init__()
        self.core = parent.core
        self.core.parentWindow(self, parent=parent)
        self.loadLayout()
        self.refreshPresets()
        self.connectEvents()

    @err_catcher(name=__name__)
    def loadLayout(self):
        self.setWindowTitle("Manage Project Presets")
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.lw_presets = QListWidget()
        self.w_options = QWidget()
        self.lo_options = QHBoxLayout()
        self.w_options.setLayout(self.lo_options)
        self.b_addFolder = QToolButton()
        self.b_delete = QToolButton()
        self.bb_main = QDialogButtonBox()
        self.lo_options.addStretch()
        self.lo_options.addWidget(self.b_addFolder)
        self.lo_options.addWidget(self.b_delete)
        self.lo_main.addWidget(self.lw_presets)
        self.lo_main.addWidget(self.w_options)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_addFolder.setIcon(icon)
        self.b_addFolder.setToolTip("Create new preset from existing project")

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "remove.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_delete.setIcon(icon)
        self.b_delete.setToolTip("Delete")

        self.lw_presets.setContextMenuPolicy(Qt.CustomContextMenu)

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.b_addFolder.clicked.connect(self.addPresetFromFolder)
        self.b_delete.clicked.connect(self.deletePreset)
        self.lw_presets.customContextMenuRequested.connect(self.presetRightClicked)

    @err_catcher(name=__name__)
    def refreshPresets(self):
        self.lw_presets.clear()
        presets = self.core.projects.getPresets()
        for preset in presets:
            item = QListWidgetItem(preset["name"])
            item.setData(Qt.UserRole, preset)
            item.setToolTip(preset["path"])
            self.lw_presets.addItem(item)

    @err_catcher(name=__name__)
    def addPresetFromFolder(self):
        path = QFileDialog.getExistingDirectory(
            self.core.messageParent, "Select project folder"
        )
        if path:
            self.newItem = PrismWidgets.CreateItem(
                core=self.core, allowChars=["_"], showType=False
            )
            self.core.parentWindow(self.newItem)
            self.newItem.e_item.setFocus()
            self.newItem.setWindowTitle("Create Preset")
            self.newItem.l_item.setText("Preset Name:")
            self.newItem.accepted.connect(lambda: self.createPreset(path))
            self.newItem.show()

    @err_catcher(name=__name__)
    def createPreset(self, path):
        name = self.newItem.e_item.text()
        self.core.projects.createPresetFromFolder(name, path)
        self.signalPresetsChanged.emit()
        self.refreshPresets()

    @err_catcher(name=__name__)
    def deletePreset(self):
        items = self.lw_presets.selectedItems()
        if not items:
            return

        item = items[0]
        name = item.text()
        if name == "Default":
            self.core.popup("Cannot delete the default project preset.")
            return

        result = self.core.popupQuestion(
            'Are you sure you want to delete the preset "%s"?' % name
        )
        if result == "Yes":
            path = item.data(Qt.UserRole)["path"]
            self.core.projects.deletePreset(path=path)
            self.signalPresetsChanged.emit()
            self.refreshPresets()

    @err_catcher(name=__name__)
    def presetRightClicked(self, pos):
        item = self.lw_presets.itemAt(pos)
        if not item:
            return

        path = item.data(Qt.UserRole)["path"]

        rcmenu = QMenu(self)
        openex = QAction("Open in Explorer", self)
        openex.triggered.connect(lambda: self.core.openFolder(path))
        rcmenu.addAction(openex)

        copAct = QAction("Copy path", self)
        copAct.triggered.connect(lambda: self.core.copyToClipboard(path))
        rcmenu.addAction(copAct)

        rcmenu.exec_(QCursor.pos())


class ProjectCreated(QDialog):
    def __init__(self, prjname, core, basepath):
        QDialog.__init__(self)
        self.core = core
        self.basepath = basepath
        self.prjname = prjname
        self.loadLayout()
        self.connectEvents()

    @err_catcher(name=__name__)
    def loadLayout(self):
        self.setWindowTitle("Project Created")
        self.lo_main = QVBoxLayout()
        self.lo_main.setSpacing(50)
        self.setLayout(self.lo_main)
        msg = 'The project "%s" was created successfully!' % self.prjname
        self.l_success = QLabel(msg)
        self.l_icon = QLabel()
        headerPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "check.png"
        )
        pmap = self.core.media.getPixmapFromPath(headerPath)
        self.l_icon.setPixmap(pmap)
        self.l_icon.setAlignment(Qt.AlignHCenter)
        self.b_browser = QPushButton("Open Project Browser")
        self.lo_main.addWidget(self.l_success)
        self.lo_main.addWidget(self.l_icon)
        self.lo_main.addWidget(self.b_browser)
        self.core.parentWindow(self)
        self.setFocus()

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.b_browser.clicked.connect(self.core.projectBrowser)
        self.b_browser.clicked.connect(self.accept)


class SetProject(QDialog):
    def __init__(self, core, openUi=""):
        QDialog.__init__(self)
        self.core = core
        self.core.parentWindow(self)
        self.setWindowTitle("Set Project")

        self.openUi = openUi

        self.projectsUi = SetProjectClass(self.core, self, openUi)
        self.loadLayout()
        self.setFocus()

    @err_catcher(name=__name__)
    def loadLayout(self):
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self.projectsUi)

        self.setLayout(grid)

        self.w_header = DragWidget(self)
        self.w_header.setAttribute(Qt.WA_StyledBackground, True)
        self.w_header.setStyleSheet("DragWidget{ background-color: rgba(0, 0, 0, 30) }")
        self.w_header.setGeometry(0, 0, self.width(), 40)
        self.b_close = QToolButton(self)
        self.b_close.move((self.width() - self.b_close.geometry().width() - 10), 10)
        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "delete.png"
        )
        icon = self.core.media.getColoredIcon(path, force=True)
        self.b_close.setIcon(icon)
        self.b_close.clicked.connect(self.close)
        self.b_close.setIconSize(QSize(20, 20))
        self.b_close.setToolTip("Close")
        self.b_close.setMaximumWidth(20)
        self.b_close.setMaximumHeight(20)
        self.b_close.setStyleSheet(
            "QToolButton{padding: 0; margin: 0; border-width: 0px;background-color: transparent} QWidget:hover{border-width: 0px; background-color: rgba(255, 255, 255, 30)}"
        )

        #    self.resize(self.projectsUi.width(), self.projectsUi.height())
        if self.projectsUi.getProjects():
            self.resize(800, 900)
        else:
            self.resize(
                self.projectsUi.l_header.pixmap().width(),
                self.projectsUi.l_header.pixmap().height(),
            )

        self.setWindowFlags(
            self.windowFlags() ^ Qt.FramelessWindowHint
        )

    @err_catcher(name=__name__)
    def resizeEvent(self, event):
        self.b_close.move((self.width() - self.b_close.geometry().width() - 10), 10)
        self.w_header.setGeometry(0, 0, self.width(), 40)


class SetProjectClass(QDialog):

    signalShowing = Signal()

    def __init__(self, core, pdialog, openUi="", refresh=True):
        QDialog.__init__(self)
        self.core = core
        self.pdialog = pdialog
        self.openUi = openUi
        self.allowDeselect = True

        self.loadLayout()
        self.connectEvents()
        if refresh:
            self.refreshUi()

        self.core.callback(name="onSetProjectStartup", args=[self])

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.chb_startup.stateChanged.connect(self.startupChanged)

    @err_catcher(name=__name__)
    def enterEvent(self, event):
        try:
            QApplication.restoreOverrideCursor()
        except:
            pass

    @err_catcher(name=__name__)
    def preCreate(self):
        self.core.projects.createProjectDialog()
        self.pdialog.close()
        if getattr(self.core, "pb", None) and self.core.pb.isVisible():
            self.core.pb.close()

    @err_catcher(name=__name__)
    def openProject(self, widget):
        path = widget.data["configPath"]
        if path == self.core.prismIni:
            msg = "This project is already active."
            self.core.popup(msg, parent=self)
            return

        self.core.changeProject(path, self.openUi)

    @err_catcher(name=__name__)
    def getProjectWidgetClass(self):
        return self.core.projects.ProjectWidget

    @err_catcher(name=__name__)
    def loadLayout(self):
        self.l_header = QLabel()
        headerPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "prism_title.png"
        )
        pmap = self.core.media.getPixmapFromPath(headerPath)
        pmap = self.core.media.scalePixmap(pmap, 800, 500)
        self.l_header.setPixmap(pmap)
        self.l_header.setAlignment(Qt.AlignTop)

        self.w_newProject = QWidget()
        self.w_newProjectV = QWidget()
        self.lo_newProjectV = QVBoxLayout()
        self.w_newProjectV.setLayout(self.lo_newProjectV)
        self.lo_newProject = QHBoxLayout()
        self.lo_newProject.setSpacing(20)
        self.w_newProject.setLayout(self.lo_newProject)
        self.w_projects = QWidget()
        self.lo_projects = QGridLayout()
        self.lo_projects.setSpacing(30)
        self.w_projects.setLayout(self.lo_projects)
        self.w_bottomWidgets = QWidget()
        self.lo_bottomWidgets = QHBoxLayout(self.w_bottomWidgets)
        self.chb_startup = QCheckBox("Open on startup")
        ssheet = self.chb_startup.styleSheet() + ";QCheckBox::indicator{border-width: 1px}"
        self.chb_startup.setStyleSheet(ssheet)
        self.b_settings = QToolButton()
        self.b_settings.setToolTip("Open Prism Settings...")
        self.b_settings.setStyleSheet(
            "QToolButton{padding: 0; margin: 0; border-width: 0px;background-color: transparent} QWidget:hover{border-width: 0px; background-color: rgba(255, 255, 255, 30)}"
        )
        self.b_settings.clicked.connect(self.core.prismSettings)
        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "configure.png"
        )
        icon = self.core.media.getColoredIcon(path, force=True)
        self.b_settings.setIcon(icon)
        self.lo_bottomWidgets.addWidget(self.chb_startup)
        self.lo_bottomWidgets.addStretch()
        self.lo_bottomWidgets.addWidget(self.b_settings)
        self.lo_main = QVBoxLayout()
        self.lo_main.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.lo_main)

        self.w_scrollParent = QWidget()
        self.lo_scrollParent = QHBoxLayout()
        self.sa_projects = QScrollArea()
        self.sa_projects.setWidgetResizable(True)
        self.sa_projects.setWidget(self.w_projects)
        self.w_scrollParent.setLayout(self.lo_scrollParent)
        self.lo_scrollParent.addWidget(self.sa_projects)
        self.lo_main.addWidget(self.l_header)
        self.lo_main.addWidget(self.w_scrollParent)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
        )
        data = {"name": "Create New Project", "icon": path}
        self.w_new = self.getProjectWidgetClass()(self, data)
        self.w_new.setMaximumHeight(100)
        self.w_new.setMinimumWidth(200)
        self.w_new.signalReleased.connect(lambda x: self.preCreate())
        self.w_new.signalReleased.connect(lambda x: x.deselect())

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "browse.png"
        )
        data = {"name": "Browse Projects", "icon": path}
        self.w_open = self.getProjectWidgetClass()(self, data)
        self.w_open.setMaximumHeight(100)
        self.w_open.setMinimumWidth(200)
        self.w_open.signalReleased.connect(lambda x: self.core.projects.openProject(parent=self.pdialog))
        self.w_open.signalReleased.connect(lambda x: x.deselect())

        self.lo_newProject.addStretch()
        self.lo_newProject.addWidget(self.w_new)
        self.lo_newProject.addWidget(self.w_open)
        self.lo_newProject.addStretch()
        self.lo_newProjectV.addStretch()
        self.lo_newProjectV.addWidget(self.w_newProject)
        self.lo_newProjectV.addWidget(self.w_bottomWidgets)
        self.w_newProjectV.setParent(self)
        self.w_newProjectV.setGeometry(
            0, 0, self.l_header.width(), self.l_header.height()
        )

        ssu = self.core.getConfig("globals", "showonstartup")
        if ssu is None:
            ssu = True

        if self.core.appPlugin.pluginName == "Standalone":
            self.chb_startup.setVisible(False)

        self.chb_startup.setChecked(ssu)

    @err_catcher(name=__name__)
    def resizeEvent(self, event):
        self.w_newProjectV.setGeometry(
            0, 0, self.l_header.width(), self.l_header.height()
        )

    @err_catcher(name=__name__)
    def refreshUi(self):
        self._projects = None
        self.projectWidgets = []
        for idx in reversed(range(self.lo_projects.count())):
            item = self.lo_projects.takeAt(idx)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        projects = self.getProjects()
        for project in projects:
            w_prj = self.getProjectWidgetClass()(self, project.copy(), minHeight=1)
            w_prj.signalDoubleClicked.connect(self.openProject)
            w_prj.signalRemoved.connect(self.refreshUi)
            w_prj.signalSelect.connect(self.itemSelected)
            self.projectWidgets.append(w_prj)
            self.lo_projects.addWidget(
                w_prj,
                int(self.lo_projects.count() / 3),
                1 + (self.lo_projects.count() % 3) + (self.lo_projects.count() % 3),
            )

        sp_projectsR = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.lo_projects.setColumnStretch(0, 100)
        sp_projectsL = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Fixed)
        sp_projectsR2 = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Fixed)
        sp_projectsL2 = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Fixed)
        sp_projectsB = QSpacerItem(0, 0, QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.lo_projects.addItem(sp_projectsR, 0, 0)
        self.lo_projects.setColumnStretch(0, 100)
        self.lo_projects.addItem(sp_projectsL, 0, 2)
        self.lo_projects.setColumnStretch(2, 100)
        if len(projects) > 1:
            self.lo_projects.addItem(sp_projectsR2, 0, 4)
            self.lo_projects.setColumnStretch(4, 100)
            if len(projects) > 2:
                self.lo_projects.addItem(sp_projectsL2, 0, 6)
                self.lo_projects.setColumnStretch(6, 100)

        self.lo_projects.addItem(sp_projectsB, self.lo_projects.rowCount(), 0)
        self.w_scrollParent.setHidden(not bool(projects))
        for widget in self.projectWidgets:
            if widget.data.get("configPath", None) == self.core.prismIni:
                widget.select()

    @err_catcher(name=__name__)
    def itemSelected(self, item, event=None):
        if not self.allowDeselect:
            return

        mods = QApplication.keyboardModifiers()
        if item.isSelected():
            if mods == Qt.ControlModifier and (not event or event.button() == Qt.LeftButton):
                item.deselect()
        else:
            if mods != Qt.ControlModifier:
                self.deselectItems(ignore=[item])

    @err_catcher(name=__name__)
    def deselectItems(self, ignore=None):
        for item in self.projectWidgets:
            if ignore and item in ignore:
                continue

            item.deselect()

    @err_catcher(name=__name__)
    def startupChanged(self, state):
        if state == 0:
            self.core.setConfig("globals", "showonstartup", False)
        elif state == 2:
            self.core.setConfig("globals", "showonstartup", True)

    @err_catcher(name=__name__)
    def getProjects(self):
        if not hasattr(self, "_projects") or self._projects is None:
            self._projects = self.core.projects.getAvailableProjects(includeCurrent=True)

        return self._projects

    @err_catcher(name=__name__)
    def getSelectedItems(self):
        items = []
        for item in self.projectWidgets:
            if item.isSelected():
                items.append(item)

        return items

    @err_catcher(name=__name__)
    def showEvent(self, event):
        self.signalShowing.emit()


class DragWidget(QWidget):
    @err_catcher(name=__name__)
    def mousePressEvent(self, event):
        self.startPos = event.pos()

    @err_catcher(name=__name__)
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            diff = event.pos() - self.startPos
            newpos = self.parent().pos() + diff
            self.parent().move(newpos)


class CreateAssetDlg(PrismWidgets.CreateItem):
    def __init__(self, core, parent=None, startText=None):
        startText = startText or ""
        super(CreateAssetDlg, self).__init__(startText=startText.lstrip("/"), core=core, mode="assetHierarchy", allowChars=["/"])
        self.parentDlg = parent
        self.core = core
        self.thumbXres = 250
        self.thumbYres = 141
        self.imgPath = ""
        self.pmap = None
        self.setupUi_()

    @err_catcher(name=__name__)
    def setupUi_(self):
        self.setWindowTitle("Create Asset...")
        self.core.parentWindow(self, parent=self.parentDlg)

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "create.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.buttonBox.buttons()[0].setIcon(icon)

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "delete.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.buttonBox.buttons()[2].setIcon(icon)

        self.e_item.setFocus()
        self.e_item.setToolTip("Asset name or comma separated list of asset names.\nParent nFolders can be included using slashes.")
        self.l_item.setText("Asset(s):")
        # self.l_assetIcon = QLabel()
        # self.w_item.layout().insertWidget(0, self.l_assetIcon)
        # iconPath = os.path.join(
        #     self.core.prismRoot, "Scripts", "UserInterfacesPrism", "asset.png"
        # )
        # icon = self.core.media.getColoredIcon(iconPath)
        # self.l_assetIcon.setPixmap(icon.pixmap(15, 15))

        self.layout().setContentsMargins(20, 20, 20, 20)

        self.w_thumbnail = QWidget()
        self.lo_thumbnail = QHBoxLayout(self.w_thumbnail)
        self.lo_thumbnail.setContentsMargins(0, 0, 0, 0)
        self.l_thumbnailStr = QLabel("Thumbnail:")
        self.l_thumbnail = QLabel()
        self.lo_thumbnail.addWidget(self.l_thumbnailStr)
        self.lo_thumbnail.addWidget(self.l_thumbnail)
        self.layout().insertWidget(self.layout().indexOf(self.buttonBox)-2, self.w_thumbnail)

        self.l_info = QLabel("Description:")
        self.layout().insertWidget(self.layout().indexOf(self.buttonBox)-2, self.l_info)
        self.te_text = QTextEdit()
        self.layout().insertWidget(self.layout().indexOf(self.buttonBox)-2, self.te_text)

        import MetaDataWidget
        self.w_meta = MetaDataWidget.MetaDataWidget(self.core)
        self.layout().insertWidget(
            self.layout().indexOf(self.buttonBox)-2, self.w_meta
        )
        # self.spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.layout().insertItem(
        #     self.layout().indexOf(self.buttonBox), self.spacer
        # )

        imgFile = os.path.join(
            self.core.projects.getFallbackFolder(), "noFileSmall.jpg"
        )
        pmap = self.core.media.getPixmapFromPath(imgFile)
        self.l_thumbnail.setMinimumSize(pmap.width(), pmap.height())
        self.l_thumbnail.setPixmap(pmap)
        self.l_thumbnail.setContextMenuPolicy(Qt.CustomContextMenu)

        self.l_thumbnail.mouseReleaseEvent = self.previewMouseReleaseEvent
        self.l_thumbnail.customContextMenuRequested.connect(self.rclThumbnail)
        self.resize(450, 550)

    @err_catcher(name=__name__)
    def sizeHint(self):
        return QSize(450, 450)

    @err_catcher(name=__name__)
    def previewMouseReleaseEvent(self, event):
        if event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                self.rclThumbnail()

    @err_catcher(name=__name__)
    def rclThumbnail(self, pos=None):
        rcmenu = QMenu(self)

        copAct = QAction("Capture thumbnail", self)
        copAct.triggered.connect(self.capturePreview)
        rcmenu.addAction(copAct)

        copAct = QAction("Browse thumbnail...", self)
        copAct.triggered.connect(self.browsePreview)
        rcmenu.addAction(copAct)

        clipAct = QAction("Paste thumbnail from clipboard", self)
        clipAct.triggered.connect(self.pastePreviewFromClipboard)
        rcmenu.addAction(clipAct)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def capturePreview(self):
        from PrismUtils import ScreenShot

        previewImg = ScreenShot.grabScreenArea(self.core)

        if previewImg:
            previewImg = self.core.media.scalePixmap(
                previewImg,
                self.thumbXres,
                self.thumbYres,
            )
            self.setPixmap(previewImg)

    @err_catcher(name=__name__)
    def pastePreviewFromClipboard(self):
        pmap = self.core.media.getPixmapFromClipboard()
        if not pmap:
            self.core.popup("No image in clipboard.", parent=self)
            return

        pmap = self.core.media.scalePixmap(
            pmap,
            self.thumbXres,
            self.thumbYres,
        )
        self.setPixmap(pmap)

    @err_catcher(name=__name__)
    def browsePreview(self):
        formats = "Image File (*.jpg *.png *.exr)"

        imgPath = QFileDialog.getOpenFileName(
            self, "Select thumbnail-image", self.imgPath, formats
        )[0]

        if not imgPath:
            return

        if os.path.splitext(imgPath)[1] == ".exr":
            pmsmall = self.core.media.getPixmapFromExrPath(
                imgPath,
                width=self.thumbXres,
                height=self.thumbYres,
            )
        else:
            pm = self.core.media.getPixmapFromPath(imgPath)
            if pm.width() == 0:
                warnStr = "Cannot read image: %s" % imgPath
                self.core.popup(warnStr, parent=self)
                return

            pmsmall = self.core.media.scalePixmap(
                pm,
                self.thumbXres,
                self.thumbYres,
            )

        self.setPixmap(pmsmall)

    @err_catcher(name=__name__)
    def setPixmap(self, pmsmall):
        self.pmap = pmsmall
        self.l_thumbnail.setMinimumSize(self.pmap.width(), self.pmap.height())
        self.l_thumbnail.setPixmap(self.pmap)

    @err_catcher(name=__name__)
    def getDescription(self):
        return self.te_text.toPlainText()
    
    @err_catcher(name=__name__)
    def getThumbnail(self):
        return self.pmap


class CreateAssetFolderDlg(PrismWidgets.CreateItem):
    def __init__(self, core, parent=None, startText=None):
        startText = startText or ""
        super(CreateAssetFolderDlg, self).__init__(startText=startText.lstrip("/"), core=core, mode="assetHierarchy", allowChars=["/"])
        self.parentDlg = parent
        self.core = core
        self.setupUi_()

    @err_catcher(name=__name__)
    def setupUi_(self):
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "create.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.buttonBox.buttons()[0].setIcon(icon)

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "delete.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.buttonBox.buttons()[2].setIcon(icon)

        self.core.parentWindow(self, parent=self.parentDlg)
        self.e_item.setFocus()
        self.e_item.setToolTip("Folder name or comma separated list of folder names.\nParent folders can be included using slashes.")
        self.setWindowTitle("Create Folder...")
        self.l_item.setText("Folder(s):")
