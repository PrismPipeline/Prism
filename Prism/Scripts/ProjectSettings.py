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
import logging
import subprocess
from collections import OrderedDict

scriptPath = os.path.abspath(os.path.dirname(__file__))
if scriptPath not in sys.path:
    sys.path.append(scriptPath)

if __name__ == "__main__":
    import PrismCore

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils import PrismWidgets
from PrismUtils.Decorators import err_catcher
from UserInterfacesPrism import ProjectSettings_ui


logger = logging.getLogger(__name__)


class ProjectSettings(QDialog, ProjectSettings_ui.Ui_dlg_ProjectSettings):

    signalSaved = Signal(object)

    def __init__(self, core, projectConfig=None, projectData=None):
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.core.parentWindow(self)
        self.projectConfig = projectConfig
        self.projectData = projectData
        self.previewMap = None

        self.dependencyStates = {
            "always": "Always",
            "publish": "On Publish",
            "never": "Never",
        }

        self.loadUI()
        self.loadSettings()

        self.core.callback(name="onProjectSettingsOpen", args=[self])

        self.connectEvents()
        self.setFocus()

        screen = self.core.getQScreenGeo()
        if screen:
            screenH = screen.height()
            space = 100
            if screenH < (self.height() + space):
                self.resize(self.width(), screenH - space)

    @err_catcher(name=__name__)
    def loadUI(self):
        tabBar = self.tw_settings.findChild(QTabBar)
        tabBar.hide()
        self.tw_settings.currentChanged.connect(self.tabChanged)
        for idx in range(self.tw_settings.count()):
            self.tw_settings.widget(idx).layout().setContentsMargins(0, 0, 0, 0)

        imgFile = os.path.join(
            self.core.prismRoot,
            "Presets/Projects/Default/00_Pipeline/Fallbacks/noFileBig.jpg",
        )
        pmap = self.core.media.getPixmapFromPath(imgFile)
        self.l_preview.setMinimumSize(pmap.width(), pmap.height())
        self.l_preview.setPixmap(pmap)

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "help.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        pixmap = icon.pixmap(20, 20)
        self.l_helpExportLocations = HelpLabel(self)
        self.l_helpExportLocations.setPixmap(pixmap)
        self.l_helpExportLocations.setMouseTracking(True)
        msg = (
            "Export locations are project paths outside of the main project folder.\n"
            "They can be used to export files to different folders and harddrives.\n"
            "In the export settings artists can choose to which location they want to export their objects.\n"
            'The filepath of an exported file consists of the locationpath plus the relative projectpath, which is defined in the "Folder Structure" tab of the project settings.'
        )
        self.l_helpExportLocations.msg = msg
        self.lo_exportLocationsHeader.addWidget(self.l_helpExportLocations)
        self.l_helpRenderLocations = HelpLabel(self)
        self.l_helpRenderLocations.setPixmap(pixmap)
        self.l_helpRenderLocations.setMouseTracking(True)
        msg = (
            "Render locations are project paths outside of the main project folder.\n"
            "They can be used to render files to different folders and harddrives.\n"
            "In the render settings artists can choose to which location they want to render their images.\n"
            'The filepath of a rendered file consists of the locationpath plus the relative projectpath, which is defined in the "Folder Structure" tab of the project settings.'
        )
        self.l_helpRenderLocations.msg = msg
        self.lo_renderLocationsHeader.addWidget(self.l_helpRenderLocations)

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "reset.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.b_resetStructure.setIcon(icon)
        self.b_resetStructure.setToolTip("Reset all fields to their default")

        if self.projectData:
            items = self.projectData.get("folder_structure", "")
            if items:
                items = self.core.projects.getProjectStructure(projectStructure=items)
            else:
                items = self.core.projects.getDefaultProjectStructure()
        else:
            items = self.core.projects.getProjectStructure()

        self.folderStructureWidgets = []
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "help.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.helpPixmap = icon.pixmap(20, 20)
        self.invalidHelpPixmap = self.core.media.getColoredIcon(
            iconPath, r=200, g=10, b=10
        ).pixmap(20, 20)
        for idx, key in enumerate(items):
            l_item = QLabel(items[key]["label"] + ":  ")
            l_item.setToolTip(items[key]["key"])
            e_item = QLineEdit(items[key]["value"])
            l_help = HelpLabel(self)
            e_item.textChanged.connect(lambda x, w=e_item: self.validateFolderWidget(w))
            e_item.helpWidget = l_help
            e_item.setContextMenuPolicy(Qt.CustomContextMenu)
            e_item.customContextMenuRequested.connect(
                lambda x, w=e_item: self.rclStructureKey(w)
            )
            l_help.editWidget = e_item
            l_help.key = key
            l_help.item = items[key]
            l_help.msg = ""
            l_help.setPixmap(self.helpPixmap)
            l_help.setMouseTracking(True)
            l_help.signalEntered.connect(self.structureItemEntered)
            self.validateFolderWidget(e_item)

            self.lo_structure.addWidget(l_item, idx, 0)
            self.lo_structure.addWidget(e_item, idx, 1)
            self.lo_structure.addWidget(l_help, idx, 2)

            data = {"key": key, "item": items[key], "widget": e_item}
            self.folderStructureWidgets.append(data)

        sp_structure = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.lo_structure.addItem(sp_structure, idx + 1, 1)

        self.origKeyPressEvent = self.keyPressEvent
        self.keyPressEvent = lambda x: self.keyPressedDialog(x)

        self.tw_exportPaths.customContextMenuRequested.connect(self.rclExportPaths)
        self.tw_renderPaths.customContextMenuRequested.connect(self.rclRenderPaths)

        self.tw_environment.setHorizontalHeaderLabels(["Variable", "Value"])
        self.tw_environment.customContextMenuRequested.connect(self.rclEnvironment)
        self.addEnvironmentRow()
        self.tw_environment.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )

        if self.core.prism1Compatibility:
            self.tw_settings.removeTab(self.tw_settings.indexOf(self.tab_folderStructure))

        self.b_assetDepAdd = QToolButton()
        self.b_assetDepAdd.setToolTip("Add asset department...")
        self.b_assetDepAdd.setFocusPolicy(Qt.NoFocus)
        self.w_assetDepartmentHeader.layout().addWidget(self.b_assetDepAdd)
        self.b_assetDepRemove = QToolButton()
        self.b_assetDepRemove.setToolTip("Remove selected asset departments")
        self.b_assetDepRemove.setFocusPolicy(Qt.NoFocus)
        self.w_assetDepartmentHeader.layout().addWidget(self.b_assetDepRemove)
        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_assetDepAdd.setIcon(icon)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "remove.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_assetDepRemove.setIcon(icon)
        self.b_assetDepAdd.clicked.connect(self.addAssetDepartmentClicked)
        self.b_assetDepRemove.clicked.connect(self.removeAssetDepartmentClicked)
        self.tw_assetDepartments.verticalHeader().setSectionsMovable(True)
        self.tw_assetDepartments.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.tw_assetDepartments.customContextMenuRequested.connect(self.assetDepsRightClicked)
        self.tw_assetDepartments.verticalHeader().sectionMoved.connect(self.assetDepartmentRowMoved)
        self.tw_assetDepartments.itemDoubleClicked.connect(self.assetDepartmentDoubleClicked)
        self.tw_assetDepartments.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)

        self.b_shotDepAdd = QToolButton()
        self.b_shotDepAdd.setToolTip("Add shot department...")
        self.b_shotDepAdd.setFocusPolicy(Qt.NoFocus)
        self.w_shotDepartmentHeader.layout().addWidget(self.b_shotDepAdd)
        self.b_shotDepRemove = QToolButton()
        self.b_shotDepRemove.setToolTip("Remove selected shot departments")
        self.b_shotDepRemove.setFocusPolicy(Qt.NoFocus)
        self.w_shotDepartmentHeader.layout().addWidget(self.b_shotDepRemove)
        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_shotDepAdd.setIcon(icon)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "remove.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_shotDepRemove.setIcon(icon)
        self.b_shotDepAdd.clicked.connect(self.addShotDepartmentClicked)
        self.b_shotDepRemove.clicked.connect(self.removeShotDepartmentClicked)
        self.tw_shotDepartments.verticalHeader().setSectionsMovable(True)
        self.tw_shotDepartments.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.tw_shotDepartments.customContextMenuRequested.connect(self.shotDepsRightClicked)
        self.tw_shotDepartments.verticalHeader().sectionMoved.connect(self.shotDepartmentRowMoved)
        self.tw_shotDepartments.itemDoubleClicked.connect(self.shotDepartmentDoubleClicked)
        self.tw_shotDepartments.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "import.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_importSettings.setIcon(icon)
        self.b_importSettings.setIconSize(QSize(22, 22))

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "export.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_exportSettings.setIcon(icon)
        self.b_exportSettings.setIconSize(QSize(22, 22))

        self.refreshCategories()
        policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        policy.setHorizontalStretch(58)
        self.lw_categories.setSizePolicy(policy)
        policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        policy.setHorizontalStretch(100)
        self.tw_settings.setSizePolicy(policy)
        self.lw_categories.currentItemChanged.connect(self.onCategoryChanged)
        self.selectCategory("General")
        self.core.callback(name="projectSettings_loadUI", args=[self])

    @err_catcher(name=__name__)
    def addTab(self, widget, name):
        self.tw_settings.addTab(widget, name)
        self.refreshCategories()

    @err_catcher(name=__name__)
    def tabChanged(self, tab):
        self.lw_categories.blockSignals(True)
        self.selectCategory(self.tw_settings.tabText(tab))
        self.lw_categories.blockSignals(False)

    @err_catcher(name=__name__)
    def refreshCategories(self):
        self.lw_categories.blockSignals(True)
        curCat = self.getCurrentCategory()
        self.lw_categories.clear()
        cats = []
        for idx in range(self.tw_settings.count()):
            text = self.tw_settings.tabText(idx)
            cats.append(text)
        
        self.lw_categories.addItems(sorted(cats))
        if curCat:
            self.selectCategory(curCat)
        else:
            self.lw_categories.setCurrentRow(0)

        self.lw_categories.blockSignals(False)
        self.onCategoryChanged(self.lw_categories.currentItem())

    @err_catcher(name=__name__)
    def onCategoryChanged(self, current, prev=None):
        text = current.text()
        for idx in range(self.tw_settings.count()):
            tabtext = self.tw_settings.tabText(idx)
            if text == tabtext:
                self.tw_settings.setCurrentIndex(idx)
                break

    @err_catcher(name=__name__)
    def selectCategory(self, name):
        for idx in range(self.lw_categories.count()):
            cat = self.lw_categories.item(idx).text()
            if cat == name:
                self.lw_categories.setCurrentRow(idx)
                break

    @err_catcher(name=__name__)
    def getCurrentCategory(self):
        item = self.lw_categories.currentItem()
        if not item:
            return

        return item.text()

    @err_catcher(name=__name__)
    def keyPressedDialog(self, event):
        if event.key() == Qt.Key_Return:
            self.setFocus()
        else:
            self.origKeyPressEvent(event)

        event.accept()

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.l_preview.mouseDoubleClickEvent = lambda x: self.browsePreview()
        self.l_preview.customContextMenuRequested.connect(self.rclPreview)
        self.e_curPname.textEdited.connect(self.curPnameEdited)
        self.chb_curPuseFps.toggled.connect(self.pfpsToggled)
        self.chb_prjResolution.toggled.connect(self.prjResolutionToggled)
        self.chb_curPRequirePublishComment.toggled.connect(self.requirePublishCommentToggled)
        self.b_addExportPath.clicked.connect(self.addExportPathClicked)
        self.b_removeExportPath.clicked.connect(self.removeExportPathClicked)
        self.b_addRenderPath.clicked.connect(self.addRenderPathClicked)
        self.b_removeRenderPath.clicked.connect(self.removeRenderPathClicked)
        self.b_resetStructure.clicked.connect(self.resetProjectStructure)
        self.b_showEnvironment.clicked.connect(self.showEnvironment)
        self.b_importSettings.clicked.connect(self.onImportSettingsClicked)
        self.b_exportSettings.clicked.connect(self.onExportSettingsClicked)
        self.b_reqPlugins.clicked.connect(self.onRequiredPluginsClicked)
        self.buttonBox.accepted.connect(self.saveSettings)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(
            lambda: self.saveSettings(changeProject=False)
        )

    @err_catcher(name=__name__)
    def rclPreview(self, pos):
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
    def rclStructureKey(self, widget):
        rcmenu = QMenu(self)

        exp = QAction("Restore saved value", self)
        exp.triggered.connect(lambda: self.restoreStructurePath(widget))
        rcmenu.addAction(exp)

        exp = QAction("Restore factory default", self)
        exp.triggered.connect(lambda: self.restoreStructurePath(widget, default=True))
        rcmenu.addAction(exp)

        exp = QAction("Edit Expression...", self)
        exp.triggered.connect(lambda: self.editExpression(widget))
        rcmenu.addAction(exp)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def editExpression(self, widget):
        self.dlg_expression = ExpressionWindow(self)
        text = widget.text()
        if text.startswith("[expression,"):
            text = text[len("[expression,"):]
            if text.endswith("]"):
                text = text[:-1]
        else:
            text = "#  available variables:\n#  \"core\" - PrismCore\n#  \"context\" - dict\n\ntemplate = \"%s\"" % text

        self.dlg_expression.te_expression.setPlainText(text)
        newCursor = QTextCursor(self.dlg_expression.te_expression.document())
        newCursor.movePosition(QTextCursor.End)
        self.dlg_expression.te_expression.setTextCursor(newCursor)
        result = self.dlg_expression.exec_()

        if result == 1:
            text = self.dlg_expression.te_expression.toPlainText()
            text = "[expression,%s]" % text
            widget.setText(text)

    @err_catcher(name=__name__)
    def rclExportPaths(self, pos):
        rcmenu = QMenu(self)

        exp = QAction("Add location", self)
        exp.triggered.connect(self.addExportLocation)
        rcmenu.addAction(exp)

        item = self.tw_exportPaths.itemFromIndex(self.tw_exportPaths.indexAt(pos))
        if item:
            if item.column() == 1:
                exp = QAction("Browse...", self)
                exp.triggered.connect(lambda: self.browse(item, "export"))
                rcmenu.addAction(exp)

            exp = QAction("Remove", self)
            exp.triggered.connect(lambda: self.removeExportLocation(item.row()))
            rcmenu.addAction(exp)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def browse(self, item, location):
        windowTitle = "Select %s location" % location
        selectedPath = QFileDialog.getExistingDirectory(
            self, windowTitle, item.text()
        )

        if selectedPath:
            item.setText(self.core.fixPath(selectedPath))

    @err_catcher(name=__name__)
    def addExportLocation(self):
        count = self.tw_exportPaths.rowCount()
        self.tw_exportPaths.insertRow(count)
        item = QTableWidgetItem("< doubleclick to edit >")
        self.tw_exportPaths.setItem(count, 0, item)
        item = QTableWidgetItem("< doubleclick to edit >")
        self.tw_exportPaths.setItem(count, 1, item)
        self.tw_exportPaths.resizeColumnsToContents()

    @err_catcher(name=__name__)
    def removeExportLocation(self, idx):
        self.tw_exportPaths.removeRow(idx)

    @err_catcher(name=__name__)
    def rclRenderPaths(self, pos):
        rcmenu = QMenu(self)

        exp = QAction("Add location", self)
        exp.triggered.connect(self.addRenderLocation)
        rcmenu.addAction(exp)

        item = self.tw_renderPaths.itemFromIndex(self.tw_renderPaths.indexAt(pos))
        if item:
            if item.column() == 1:
                exp = QAction("Browse...", self)
                exp.triggered.connect(lambda: self.browse(item, "render"))
                rcmenu.addAction(exp)

            exp = QAction("Remove", self)
            exp.triggered.connect(lambda: self.removeRenderLocation(item.row()))
            rcmenu.addAction(exp)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def addRenderLocation(self):
        count = self.tw_renderPaths.rowCount()
        self.tw_renderPaths.insertRow(count)
        item = QTableWidgetItem("< doubleclick to edit >")
        self.tw_renderPaths.setItem(count, 0, item)
        item = QTableWidgetItem("< doubleclick to edit >")
        self.tw_renderPaths.setItem(count, 1, item)
        self.tw_renderPaths.resizeColumnsToContents()

    @err_catcher(name=__name__)
    def removeRenderLocation(self, idx):
        self.tw_renderPaths.removeRow(idx)

    @err_catcher(name=__name__)
    def rclEnvironment(self, pos):
        rcmenu = QMenu(self)

        exp = QAction("Add row", self)
        exp.triggered.connect(self.addEnvironmentRow)
        rcmenu.addAction(exp)

        item = self.tw_environment.itemFromIndex(self.tw_environment.indexAt(pos))
        if item:
            exp = QAction("Make Persistent", self)
            exp.triggered.connect(lambda: self.makePersistent(item.row()))
            rcmenu.addAction(exp)

            exp = QAction("Remove", self)
            exp.triggered.connect(lambda: self.removeEnvironmentRow(item.row()))
            rcmenu.addAction(exp)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def addEnvironmentRow(self):
        count = self.tw_environment.rowCount()
        self.tw_environment.insertRow(count)
        item = QTableWidgetItem("< doubleclick to edit >")
        self.tw_environment.setItem(count, 0, item)
        item = QTableWidgetItem("< doubleclick to edit >")
        self.tw_environment.setItem(count, 1, item)
        self.tw_environment.resizeColumnsToContents()

    @err_catcher(name=__name__)
    def removeEnvironmentRow(self, idx):
        self.tw_environment.removeRow(idx)

    @err_catcher(name=__name__)
    def makePersistent(self, idx):
        dft = "< doubleclick to edit >"
        key = self.tw_environment.item(idx, 0).text()
        if not key or key == dft:
            self.core.popup("Invalid key.")
            return

        value = self.tw_environment.item(idx, 1).text()
        if value == dft:
            self.core.popup("Invalid value.")
            return

        with self.core.waitPopup(self.core, "Making env var persistent. Please wait..."):
            proc = subprocess.Popen("setx %s %s" % (key, value), stdout=subprocess.PIPE)
            stdout, _ = proc.communicate()
        
        if sys.version[0] == "3":
            stdout = stdout.decode("utf-8", "ignore")

        if "success" in stdout.lower():
            self.core.popup("Successfully set environment variable persistently.", severity="info")
        else:
            self.core.popup("Unknown result. The env var might not be set persistently. Result is:\n\n%s" % stdout)

    @err_catcher(name=__name__)
    def showEnvironment(self):
        self.w_env = EnvironmentWidget(self)
        self.w_env.show()

    @err_catcher(name=__name__)
    def onImportSettingsClicked(self):
        path = self.core.paths.requestFilepath(
            title="Load project settings",
            startPath=self.core.prismIni,
            parent=self,
            fileFilter="Config files (*.json *.yml)",
            saveDialog=False
        )

        if not path:
            return

        self.loadSettings(configPath=path)

    @err_catcher(name=__name__)
    def onExportSettingsClicked(self):
        path = self.core.paths.requestFilepath(
            title="Save project settings",
            startPath=self.core.prismIni,
            parent=self,
            fileFilter="Config files (*.json *.yml)",
            saveDialog=True
        )

        if not path:
            return

        self.saveSettings(configPath=path, export=True)

    @err_catcher(name=__name__)
    def onRequiredPluginsClicked(self):
        pos = QCursor.pos()
        rcmenu = QMenu(self)

        plugins = self.core.plugins.getPlugins()
        pluginNames = []
        for pluginCat in plugins:
            if pluginCat == "inactive":
                continue

            pluginNames += plugins[pluginCat]

        for plugin in sorted(pluginNames):
            exp = QAction(plugin, self)
            exp.triggered.connect(lambda x=None, p=plugin: self.toggleRequiredPlugin(p))
            rcmenu.addAction(exp)

        rcmenu.exec_(pos)

    @err_catcher(name=__name__)
    def toggleRequiredPlugin(self, plugin):
        plugins = [p.strip() for p in self.e_reqPlugins.text().split(",") if p]
        if plugin in plugins:
            plugins.remove(plugin)
        else:
            plugins.append(plugin)

        self.e_reqPlugins.setText(", ".join(plugins))

    @err_catcher(name=__name__)
    def restoreStructurePath(self, widget, default=False):
        key = widget.helpWidget.key
        path = self.core.projects.getTemplatePath(key, default=default)
        widget.setText(path)

    @err_catcher(name=__name__)
    def capturePreview(self):
        from PrismUtils import ScreenShot

        previewImg = ScreenShot.grabScreenArea(self.core)

        if previewImg:
            previewImg = self.core.media.scalePixmap(
                previewImg,
                self.core.projects.previewWidth,
                self.core.projects.previewHeight,
            )
            self.previewMap = previewImg
            previewImg = self.core.media.scalePixmap(
                previewImg,
                self.l_preview.geometry().width(),
                self.l_preview.geometry().height(),
            )
            self.l_preview.setPixmap(previewImg)

    @err_catcher(name=__name__)
    def pastePreviewFromClipboard(self):
        pmap = self.core.media.getPixmapFromClipboard()
        if not pmap:
            self.core.popup("No image in clipboard.")
            return

        pmap = self.core.media.scalePixmap(
            pmap, self.core.projects.previewWidth, self.core.projects.previewHeight
        )
        self.previewMap = pmap
        pmap = self.core.media.scalePixmap(
            pmap, self.l_preview.geometry().width(), self.l_preview.geometry().height()
        )
        self.l_preview.setPixmap(pmap)

    @err_catcher(name=__name__)
    def browsePreview(self):
        formats = "Image File (*.jpg *.png *.exr)"

        imgPath = QFileDialog.getOpenFileName(
            self, "Select Project Image", "", formats
        )[0]

        if not imgPath:
            return

        if os.path.splitext(imgPath)[1] == ".exr":
            pmsmall = self.core.media.getPixmapFromExrPath(
                imgPath, width=self.core.projects.previewWidth, height=self.core.projects.previewHeight
            )
        else:
            pm = self.core.media.getPixmapFromPath(imgPath)
            if pm.width() == 0:
                warnStr = "Cannot read image: %s" % imgPath
                self.core.popup(warnStr)
                return

            pmsmall = self.core.media.scalePixmap(pm, self.core.projects.previewWidth, self.core.projects.previewHeight)

        self.previewMap = pmsmall
        pmsmall = self.core.media.scalePixmap(
            pmsmall, self.l_preview.geometry().width(), self.l_preview.geometry().height()
        )
        self.l_preview.setPixmap(pmsmall)

    @err_catcher(name=__name__)
    def validate(self, uiWidget, origText=None):
        self.core.validateLineEdit(uiWidget)

    @err_catcher(name=__name__)
    def pfpsToggled(self, checked):
        self.sp_curPfps.setEnabled(checked)

    @err_catcher(name=__name__)
    def prjResolutionToggled(self, checked):
        self.sp_prjResolutionWidth.setEnabled(checked)
        self.l_prjResolutionX.setEnabled(checked)
        self.sp_prjResolutionHeight.setEnabled(checked)

    @err_catcher(name=__name__)
    def requirePublishCommentToggled(self, checked):
        self.sp_publishComment.setEnabled(checked)
        self.l_publishCommentChars.setEnabled(checked)

    @err_catcher(name=__name__)
    def saveSettings(self, changeProject=True, configPath=None, export=False):
        logger.debug("save project settings")

        if configPath is None:
            configPath = self.projectConfig

        cData = {"globals": {}}

        cData["globals"]["project_name"] = self.e_curPname.text()
        cData["globals"]["uselocalfiles"] = self.chb_curPuseLocal.isChecked()
        cData["globals"]["track_dependencies"] = [
            x
            for x in self.dependencyStates
            if self.dependencyStates[x] == self.cb_dependencies.currentText()
        ][0]
        cData["globals"]["forcefps"] = self.chb_curPuseFps.isChecked()
        cData["globals"]["fps"] = self.sp_curPfps.value()
        cData["globals"]["forceResolution"] = self.chb_prjResolution.isChecked()
        cData["globals"]["resolution"] = [
            self.sp_prjResolutionWidth.value(),
            self.sp_prjResolutionHeight.value(),
        ]
        cData["globals"]["useMasterVersion"] = self.chb_curPuseMaster.isChecked()
        cData["globals"][
            "useMasterRenderVersion"
        ] = self.chb_curPuseMasterRender.isChecked()
        cData["globals"][
            "backupScenesOnPublish"
        ] = self.chb_curPbackupPublishes.isChecked()
        cData["globals"][
            "scenefileLocking"
        ] = self.chb_curPscenefileLocking.isChecked()
        cData["globals"][
            "matchScenefileVersions"
        ] = self.chb_matchScenefileVersions.isChecked()
        cData["globals"][
            "requirePublishComment"
        ] = self.chb_curPRequirePublishComment.isChecked()
        cData["globals"]["publishCommentLength"] = self.sp_publishComment.value()
        cData["globals"]["required_plugins"] = [x.strip() for x in self.e_reqPlugins.text().split(",") if x]
        cData["changeProject"] = changeProject
        structure = self.getFolderStructure()
        if self.isValidStructure(structure):
            valStruct = self.core.projects.getStructureValues(structure)
            cData["folder_structure"] = valStruct
        else:
            msg = "The project folderstructure is invalid and cannot be saved"
            self.core.popup(msg)
        cData["globals"]["allowAdditionalTasks"] = self.chb_allowAdditionalTasks.isChecked()
        cData["environmentVariables"] = self.getEnvironmentVariables()
        cData["globals"]["departments_asset"] = self.getAssetDepartments()
        cData["globals"]["departments_shot"] = self.getShotDepartments()
        cData["export_paths"] = self.getExportLocations()
        cData["render_paths"] = self.getRenderLocations()

        self.tmp_configPath = configPath
        self.tmp_export = export
        self.core.callback(name="preProjectSettingsSave", args=[self, cData])
        self.tmp_configPath = None
        self.tmp_export = None
        changeProject = cData["changeProject"]
        cData.pop("changeProject")

        if configPath:
            image = self.previewMap
            if image:
                imagePath = self.core.projects.getProjectImage(
                    projectConfig=configPath, validate=False
                )
                self.core.media.savePixmap(image, imagePath)

            self.core.setConfig(data=cData, configPath=configPath, updateNestedData={"exclude": ["environmentVariables", "folder_structure"]})

            if configPath == self.core.prismIni and not export:
                self.core.projects.refreshLocalFiles()
                if changeProject:
                    self.core.changeProject(
                        self.core.prismIni, settingsTab=self.tw_settings.currentIndex(), settingsType="Project",
                    )

        self.core.callback(name="postProjectSettingsSave", args=[self, cData])
        self.signalSaved.emit(cData)

    @err_catcher(name=__name__)
    def getFolderStructure(self):
        data = OrderedDict([])
        for widgetData in self.folderStructureWidgets:
            data[widgetData["key"]] = widgetData["item"]
            data[widgetData["key"]]["value"] = widgetData["widget"].text()

        return data

    @err_catcher(name=__name__)
    def isValidStructure(self, structure):
        for key in structure:
            if (
                self.core.projects.validateFolderKey(structure[key]["value"], structure[key])
                is not True
            ):
                logger.debug("invalid key: %s" % key)
                return False

        return True

    @err_catcher(name=__name__)
    def getExportLocations(self):
        locations = {}
        dft = "< doubleclick to edit >"
        for idx in range(self.tw_exportPaths.rowCount()):
            key = self.tw_exportPaths.item(idx, 0).text()
            if not key or key == dft:
                continue

            value = self.tw_exportPaths.item(idx, 1).text()
            if value == dft:
                continue

            locations[key] = value

        return locations

    @err_catcher(name=__name__)
    def getRenderLocations(self):
        locations = {}
        dft = "< doubleclick to edit >"
        for idx in range(self.tw_renderPaths.rowCount()):
            key = self.tw_renderPaths.item(idx, 0).text()
            if not key or key == dft:
                continue

            value = self.tw_renderPaths.item(idx, 1).text()
            if value == dft:
                continue

            locations[key] = value

        return locations

    @err_catcher(name=__name__)
    def getEnvironmentVariables(self):
        variables = {}
        dft = "< doubleclick to edit >"
        for idx in range(self.tw_environment.rowCount()):
            key = self.tw_environment.item(idx, 0).text()
            if not key or key == dft:
                continue

            value = self.tw_environment.item(idx, 1).text()
            if value == dft:
                continue

            variables[key] = value

        return variables

    @err_catcher(name=__name__)
    def loadEnvironmant(self, variables):
        self.tw_environment.setRowCount(0)
        for idx, key in enumerate(sorted(variables)):
            self.tw_environment.insertRow(idx)
            item = QTableWidgetItem(key)
            self.tw_environment.setItem(idx, 0, item)
            item = QTableWidgetItem(variables[key])
            self.tw_environment.setItem(idx, 1, item)

    @err_catcher(name=__name__)
    def loadSettings(self, configPath=None):
        if configPath is not None:
            configData = self.core.getConfig(configPath=configPath)
        else:
            configData = self.projectData
        
        prjPath = None
        if self.projectConfig:
            configPath = self.projectConfig
            prjPath = self.core.projects.getProjectFolderFromConfigPath(configPath) if configPath else None

        self.previewMap = None
        if not configData and os.path.exists(self.projectConfig):
            configData = self.core.getConfig(configPath=self.projectConfig)
            image = self.core.projects.getProjectImage(projectConfig=self.projectConfig)
            if image:
                self.previewMap = QPixmap(image)
                geo = self.l_preview.geometry()
                smallPixmap = self.core.media.scalePixmap(
                    self.previewMap, geo.width(), geo.height(), keepRatio=False
                )
                self.l_preview.setPixmap(smallPixmap)

        self.core.callback(name="preProjectSettingsLoad", args=[self, configData])
        gblData = configData.get("globals", {}) if configData else {}

        if prjPath:
            self.l_curPpath.setText(prjPath)

        if "project_name" in gblData:
            self.e_curPname.setText(gblData["project_name"])
        if "uselocalfiles" in gblData:
            self.chb_curPuseLocal.setChecked(gblData["uselocalfiles"])
        if "track_dependencies" in gblData:
            if not self.core.isStr(gblData["track_dependencies"]):
                gblData["track_dependencies"] = "publish"
            idx = self.cb_dependencies.findText(
                self.dependencyStates[gblData["track_dependencies"]]
            )
            if idx != -1:
                self.cb_dependencies.setCurrentIndex(idx)
        if "forcefps" in gblData:
            self.chb_curPuseFps.setChecked(gblData["forcefps"])
        if "fps" in gblData:
            self.sp_curPfps.setValue(gblData["fps"])
        if "forceResolution" in gblData:
            self.chb_prjResolution.setChecked(gblData["forceResolution"])
        if "resolution" in gblData:
            self.sp_prjResolutionWidth.setValue(gblData["resolution"][0])
            self.sp_prjResolutionHeight.setValue(gblData["resolution"][1])
        if "useMasterVersion" in gblData:
            self.chb_curPuseMaster.setChecked(gblData["useMasterVersion"])
        if "useMasterRenderVersion" in gblData:
            self.chb_curPuseMasterRender.setChecked(gblData["useMasterRenderVersion"])
        if "backupScenesOnPublish" in gblData:
            self.chb_curPbackupPublishes.setChecked(
                gblData["backupScenesOnPublish"]
            )
        if "scenefileLocking" in gblData:
            self.chb_curPscenefileLocking.setChecked(
                gblData["scenefileLocking"]
            )
        if "matchScenefileVersions" in gblData:
            self.chb_matchScenefileVersions.setChecked(
                gblData["matchScenefileVersions"]
            )
        if "requirePublishComment" in gblData:
            self.chb_curPRequirePublishComment.setChecked(
                gblData["requirePublishComment"]
            )
        if "publishCommentLength" in gblData:
            self.sp_publishComment.setValue(gblData["publishCommentLength"])
        if "required_plugins" in gblData:
            self.e_reqPlugins.setText(", ".join(gblData["required_plugins"]))
        if "allowAdditionalTasks" in gblData:
            self.chb_allowAdditionalTasks.setChecked(gblData["allowAdditionalTasks"])
        if configData and "environmentVariables" in configData and configData["environmentVariables"]:
            self.loadEnvironmant(configData["environmentVariables"])

        self.refreshAssetDepartments(configData=configData)
        self.refreshShotDepartments(configData=configData)
        self.refreshExportPaths(configData=configData)
        self.refreshRenderPaths(configData=configData)

        self.pfpsToggled(self.chb_curPuseFps.isChecked())
        self.w_curPfps.setToolTip(
            "When this option is enabled, Prism checks the fps of scenefiles when they are opened and shows a warning, if they don't match the project fps."
        )

        self.prjResolutionToggled(self.chb_prjResolution.isChecked())
        self.w_prjResolution.setToolTip(
            "When this option is enabled, Prism checks the resolution of Nuke scripts when they are opened and shows a warning, if they don't match the project resolution."
        )
        self.requirePublishCommentToggled(self.chb_curPRequirePublishComment.isChecked())

        self.core.callback(name="postProjectSettingsLoad", args=[self, configData])

    @err_catcher(name=__name__)
    def refreshAssetDepartments(self, departments=None, configData=None):
        if departments is None:
            if configData is None:
                configData = self.projectData

            departments = self.core.projects.getAssetDepartments(configData=configData)

        self.tw_assetDepartments.setRowCount(0)
        for dep in departments:
            name = "%s (%s)" % (dep.get("name"), dep.get("abbreviation"))
            nameItem = QTableWidgetItem(name)
            nameItem.setData(Qt.UserRole, dep)
            taskItem = QTableWidgetItem("\n".join(dep.get("defaultTasks")))

            rc = self.tw_assetDepartments.rowCount()
            self.tw_assetDepartments.insertRow(rc)

            self.tw_assetDepartments.setItem(rc, 0, nameItem)
            self.tw_assetDepartments.setItem(rc, 1, taskItem)

        self.tw_assetDepartments.resizeRowsToContents()
        self.tw_assetDepartments.resizeColumnsToContents()
        self.tw_assetDepartments.setColumnWidth(0, self.tw_assetDepartments.columnWidth(0) + 20)

    @err_catcher(name=__name__)
    def refreshShotDepartments(self, departments=None, configData=None):
        if departments is None:
            if configData is None:
                configData = self.projectData

            departments = self.core.projects.getShotDepartments(configData=configData)

        self.tw_shotDepartments.setRowCount(0)
        for dep in departments:
            name = "%s (%s)" % (dep.get("name"), dep.get("abbreviation"))
            nameItem = QTableWidgetItem(name)
            nameItem.setData(Qt.UserRole, dep)
            taskItem = QTableWidgetItem("\n".join(dep.get("defaultTasks")))

            rc = self.tw_shotDepartments.rowCount()
            self.tw_shotDepartments.insertRow(rc)

            self.tw_shotDepartments.setItem(rc, 0, nameItem)
            self.tw_shotDepartments.setItem(rc, 1, taskItem)

        self.tw_shotDepartments.resizeRowsToContents()
        self.tw_shotDepartments.resizeColumnsToContents()
        self.tw_shotDepartments.setColumnWidth(0, self.tw_shotDepartments.columnWidth(0) + 20)

    @err_catcher(name=__name__)
    def assetDepartmentRowMoved(self, logicalIdx, oldVisualIdx, newVisualIdx):
        departments = self.getAssetDepartments()
        self.refreshAssetDepartments(departments=departments)
        self.tw_assetDepartments.selectRow(newVisualIdx)

    @err_catcher(name=__name__)
    def shotDepartmentRowMoved(self, logicalIdx, oldVisualIdx, newVisualIdx):
        departments = self.getShotDepartments()
        self.refreshShotDepartments(departments=departments)
        self.tw_shotDepartments.selectRow(newVisualIdx)

    @err_catcher(name=__name__)
    def addAssetDepartmentClicked(self):
        self.saveAssetDepartments()
        self.dlg_department = PrismWidgets.CreateDepartmentDlg(core=self.core, entity="asset", configData=self.projectData, parent=self)
        self.dlg_department.departmentCreated.connect(lambda x: self.onDepartmentCreated("asset"))
        self.dlg_department.exec_()

    @err_catcher(name=__name__)
    def saveAssetDepartments(self):
        deps = self.getAssetDepartments()
        self.core.projects.setDepartments("asset", deps, configData=self.projectData)

    @err_catcher(name=__name__)
    def onDepartmentCreated(self, entity):
        if entity == "asset":
            self.refreshAssetDepartments()
        elif entity == "shot":
            self.refreshShotDepartments()

    @err_catcher(name=__name__)
    def removeAssetDepartmentClicked(self):
        items = self.tw_assetDepartments.selectedItems()
        rows = []
        for item in items:
            if item.column() == 0:
                rows.append(item.row())

        for idx in sorted(rows, reverse=True):
            self.tw_assetDepartments.removeRow(idx)

    @err_catcher(name=__name__)
    def addShotDepartmentClicked(self):
        self.saveShotDepartments()
        self.dlg_department = PrismWidgets.CreateDepartmentDlg(core=self.core, entity="shot", configData=self.projectData, parent=self)
        self.dlg_department.departmentCreated.connect(lambda x: self.onDepartmentCreated("shot"))
        self.dlg_department.exec_()

    @err_catcher(name=__name__)
    def saveShotDepartments(self):
        deps = self.getShotDepartments()
        self.core.projects.setDepartments("shot", deps, configData=self.projectData)

    @err_catcher(name=__name__)
    def removeShotDepartmentClicked(self):
        items = self.tw_shotDepartments.selectedItems()
        rows = []
        for item in items:
            if item.column() == 0:
                rows.append(item.row())

        for idx in sorted(rows, reverse=True):
            self.tw_shotDepartments.removeRow(idx)

    @err_catcher(name=__name__)
    def assetDepsRightClicked(self, pos):
        rcmenu = QMenu(self)

        exp = QAction("Add...", self)
        exp.triggered.connect(self.addAssetDepartmentClicked)
        rcmenu.addAction(exp)

        clipAct = QAction("Edit...", self)
        clipAct.triggered.connect(lambda: self.editAssetDepartment(self.tw_assetDepartments.selectedItems()[0]))
        rcmenu.addAction(clipAct)
        if not len(self.tw_assetDepartments.selectedItems()) == 2:
            clipAct.setEnabled(False)

        copAct = QAction("Remove", self)
        copAct.triggered.connect(self.removeAssetDepartmentClicked)
        rcmenu.addAction(copAct)
        if not self.tw_assetDepartments.selectedItems():
            copAct.setEnabled(False)

        clipAct = QAction("Move up", self)
        clipAct.triggered.connect(self.moveUpAssetDepartment)
        rcmenu.addAction(clipAct)
        if 0 in [i.row() for i in self.tw_assetDepartments.selectedItems()] or not self.tw_assetDepartments.selectedItems():
            clipAct.setEnabled(False)

        clipAct = QAction("Move down", self)
        clipAct.triggered.connect(self.moveDownAssetDepartment)
        rcmenu.addAction(clipAct)
        if (self.tw_assetDepartments.rowCount()-1) in [i.row() for i in self.tw_assetDepartments.selectedItems()] or not self.tw_assetDepartments.selectedItems():
            clipAct.setEnabled(False)

        clipAct = QAction("Restore defaults", self)
        clipAct.triggered.connect(self.restoreAssetDepsTriggered)
        rcmenu.addAction(clipAct)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def shotDepsRightClicked(self, pos):
        rcmenu = QMenu(self)

        exp = QAction("Add...", self)
        exp.triggered.connect(self.addShotDepartmentClicked)
        rcmenu.addAction(exp)

        clipAct = QAction("Edit...", self)
        clipAct.triggered.connect(lambda: self.editShotDepartment(self.tw_shotDepartments.selectedItems()[0]))
        rcmenu.addAction(clipAct)
        if not len(self.tw_shotDepartments.selectedItems()) == 2:
            clipAct.setEnabled(False)

        copAct = QAction("Remove", self)
        copAct.triggered.connect(self.removeShotDepartmentClicked)
        rcmenu.addAction(copAct)
        if not self.tw_shotDepartments.selectedItems():
            copAct.setEnabled(False)

        clipAct = QAction("Move up", self)
        clipAct.triggered.connect(self.moveUpShotDepartment)
        rcmenu.addAction(clipAct)
        if 0 in [i.row() for i in self.tw_shotDepartments.selectedItems()] or not self.tw_shotDepartments.selectedItems():
            clipAct.setEnabled(False)

        clipAct = QAction("Move down", self)
        clipAct.triggered.connect(self.moveDownShotDepartment)
        rcmenu.addAction(clipAct)
        if (self.tw_shotDepartments.rowCount()-1) in [i.row() for i in self.tw_shotDepartments.selectedItems()] or not self.tw_shotDepartments.selectedItems():
            clipAct.setEnabled(False)

        clipAct = QAction("Restore defaults", self)
        clipAct.triggered.connect(self.restoreShotDepsTriggered)
        rcmenu.addAction(clipAct)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def moveUpAssetDepartment(self):
        items = self.tw_assetDepartments.selectedItems()
        rows = []
        for item in items:
            if item.column() == 0:
                rows.append(item.row())

        deps = self.getAssetDepartments()
        for idx in sorted(rows):
            row = deps.pop(idx)
            deps.insert(idx-1, row)

        self.refreshAssetDepartments(departments=deps)
        self.tw_assetDepartments.setSelectionMode(QAbstractItemView.MultiSelection)
        for idx in sorted(rows):
            self.tw_assetDepartments.selectRow(idx-1)

        self.tw_assetDepartments.setSelectionMode(QAbstractItemView.ExtendedSelection)

    @err_catcher(name=__name__)
    def moveDownAssetDepartment(self):
        items = self.tw_assetDepartments.selectedItems()
        rows = []
        for item in items:
            if item.column() == 0:
                rows.append(item.row())

        deps = self.getAssetDepartments()
        for idx in sorted(rows):
            row = deps.pop(idx)
            deps.insert(idx+1, row)

        self.refreshAssetDepartments(departments=deps)
        self.tw_assetDepartments.setSelectionMode(QAbstractItemView.MultiSelection)
        for idx in sorted(rows):
            self.tw_assetDepartments.selectRow(idx+1)

        self.tw_assetDepartments.setSelectionMode(QAbstractItemView.ExtendedSelection)

    @err_catcher(name=__name__)
    def moveUpShotDepartment(self):
        items = self.tw_shotDepartments.selectedItems()
        rows = []
        for item in items:
            if item.column() == 0:
                rows.append(item.row())

        deps = self.getShotDepartments()
        for idx in sorted(rows):
            row = deps.pop(idx)
            deps.insert(idx-1, row)

        self.refreshShotDepartments(departments=deps)
        self.tw_shotDepartments.setSelectionMode(QAbstractItemView.MultiSelection)
        for idx in sorted(rows):
            self.tw_shotDepartments.selectRow(idx-1)

        self.tw_shotDepartments.setSelectionMode(QAbstractItemView.ExtendedSelection)

    @err_catcher(name=__name__)
    def moveDownShotDepartment(self):
        items = self.tw_shotDepartments.selectedItems()
        rows = []
        for item in items:
            if item.column() == 0:
                rows.append(item.row())

        deps = self.getShotDepartments()
        for idx in sorted(rows):
            row = deps.pop(idx)
            deps.insert(idx+1, row)

        self.refreshShotDepartments(departments=deps)
        self.tw_shotDepartments.setSelectionMode(QAbstractItemView.MultiSelection)
        for idx in sorted(rows):
            self.tw_shotDepartments.selectRow(idx+1)

        self.tw_shotDepartments.setSelectionMode(QAbstractItemView.ExtendedSelection)

    @err_catcher(name=__name__)
    def restoreAssetDepsTriggered(self):
        configData = self.core.projects.getDefaultProjectSettings()
        self.refreshAssetDepartments(configData=configData)

    @err_catcher(name=__name__)
    def restoreShotDepsTriggered(self):
        configData = self.core.projects.getDefaultProjectSettings()
        self.refreshShotDepartments(configData=configData)

    @err_catcher(name=__name__)
    def assetDepartmentDoubleClicked(self, item):
        self.editAssetDepartment(item)

    @err_catcher(name=__name__)
    def editAssetDepartment(self, item):
        self.saveAssetDepartments()
        dep = self.tw_assetDepartments.item(item.row(), 0).data(Qt.UserRole)
        self.dlg_department = PrismWidgets.CreateDepartmentDlg(core=self.core, entity="asset", configData=self.projectData, department=dep, parent=self)
        result = self.dlg_department.exec_()
        if not result:
            return

        department = self.dlg_department.getDepartment()
        name = "%s (%s)" % (department["name"], department["abbreviation"])
        self.tw_assetDepartments.item(item.row(), 0).setText(name)
        self.tw_assetDepartments.item(item.row(), 0).setData(Qt.UserRole, department)
        self.tw_assetDepartments.item(item.row(), 1).setText("\n".join(department["defaultTasks"]))
        self.tw_assetDepartments.resizeRowsToContents()
        self.tw_assetDepartments.resizeColumnsToContents()
        self.tw_assetDepartments.setColumnWidth(0, self.tw_assetDepartments.columnWidth(0) + 20)

    @err_catcher(name=__name__)
    def shotDepartmentDoubleClicked(self, item):
        self.editShotDepartment(item)

    @err_catcher(name=__name__)
    def editShotDepartment(self, item):
        self.saveShotDepartments()
        dep = self.tw_shotDepartments.item(item.row(), 0).data(Qt.UserRole)
        self.dlg_department = PrismWidgets.CreateDepartmentDlg(core=self.core, entity="shot", configData=self.projectData, department=dep, parent=self)
        result = self.dlg_department.exec_()
        if not result:
            return

        department = self.dlg_department.getDepartment()
        name = "%s (%s)" % (department["name"], department["abbreviation"])
        self.tw_shotDepartments.item(item.row(), 0).setText(name)
        self.tw_shotDepartments.item(item.row(), 0).setData(Qt.UserRole, department)
        self.tw_shotDepartments.item(item.row(), 1).setText("\n".join(department["defaultTasks"]))
        self.tw_shotDepartments.resizeRowsToContents()
        self.tw_shotDepartments.resizeColumnsToContents()
        self.tw_shotDepartments.setColumnWidth(0, self.tw_shotDepartments.columnWidth(0) + 20)

    @err_catcher(name=__name__)
    def getAssetDepartments(self):
        deps = []
        rowDict = {}
        for idx in range(self.tw_assetDepartments.rowCount()):
            rowDict[str(self.tw_assetDepartments.visualRow(idx))] = idx

        for idx in range(self.tw_assetDepartments.rowCount()):
            deps.append(self.tw_assetDepartments.item(rowDict[str(idx)], 0).data(Qt.UserRole))

        return deps

    @err_catcher(name=__name__)
    def getShotDepartments(self):
        deps = []
        rowDict = {}
        for idx in range(self.tw_shotDepartments.rowCount()):
            rowDict[str(self.tw_shotDepartments.visualRow(idx))] = idx

        for idx in range(self.tw_shotDepartments.rowCount()):
            deps.append(self.tw_shotDepartments.item(rowDict[str(idx)], 0).data(Qt.UserRole))

        return deps

    @err_catcher(name=__name__)
    def validateFolderWidget(self, widget):
        path = widget.text()
        item = widget.helpWidget.item
        result = self.core.projects.validateFolderKey(path, item)
        invalidStyle = "border: 2px solid rgb(200, 10, 10)"

        if result is True:
            widget.setStyleSheet("border: 2px solid transparent")
            widget.helpWidget.setPixmap(self.helpPixmap)
        else:
            widget.setStyleSheet(invalidStyle)
            widget.helpWidget.setPixmap(self.invalidHelpPixmap)

        return result

    @err_catcher(name=__name__)
    def structureItemEntered(self, widget):
        result = self.validateFolderWidget(widget.editWidget)
        if result is not True:
            widget.msg = result
            return

        entityType = (
            "shot"
            if widget.key
            in [
                "shots",
                "sequences",
                "shotScenefiles",
                "productFilesShots",
                "renderFilesShots",
                "playblastFilesShots",
            ]
            else "asset"
        )
        if widget.key in ["productFilesAssets", "productFilesShots"]:
            fileType = "product"
        elif widget.key in ["renderFilesShots", "playblastFilesShots"]:
            fileType = "media"
        else:
            fileType = "scene"

        widget.msg = self.getResolvedPath(
            widget.editWidget.text(), entityType=entityType, fileType=fileType
        )

        reqKeys = widget.item.get("requires", [])
        if reqKeys:
            msg = "\n\nThe following keys are required:"
            for key in reqKeys:
                if self.core.isStr(key):
                    msg += "\n@%s@" % key
                else:
                    msg += "\n" + " or ".join(["@%s@" % o for o in key])

            widget.msg += msg

    @err_catcher(name=__name__)
    def getResolvedPath(self, path, entityType="asset", fileType="scene"):
        if self.projectData:
            projectPath = self.projectData["globals"]["project_path"]
        else:
            projectPath = os.path.normpath(self.core.projectPath)

        context = {
            "project_path": projectPath,
            "project_name": "myProject",
            "department": "modeling",
            "task": "body",
            "comment": "my-comment",
            "version": "v0001",
            "user": "mmu",
            "product": "charGEO",
            "frame": "1001",
            "aov": "beauty",
            "identifier": "main",
        }

        if entityType == "asset":
            context["asset"] = "alien"
            context["asset_path"] = "character/alien"
        elif entityType == "shot":
            context["sequence"] = "seq01"
            context["shot"] = "0010"

        if fileType == "scene":
            context["extension"] = ".hip"
        elif fileType == "product":
            context["extension"] = ".abc"
        elif fileType == "media":
            context["extension"] = ".exr"

        paths = self.core.projects.resolveStructurePath(path, context)
        if paths:
            return paths[0]
        else:
            return ""

    @err_catcher(name=__name__)
    def resetProjectStructure(self):
        for item in self.folderStructureWidgets:
            widget = item["widget"]
            key = item["key"]
            dftStructure = self.core.projects.getDefaultProjectStructure()
            dft = dftStructure[key]["value"]
            widget.setText(dft)

    @err_catcher(name=__name__)
    def refreshExportPaths(self, configData=None):
        if configData is None:
            configData = self.projectData

        exportPaths = self.core.paths.getExportProductBasePaths(
            default=False, configData=configData
        )
        self.tw_exportPaths.setRowCount(0)
        for location in exportPaths:
            locationItem = QTableWidgetItem(location)
            pathItem = QTableWidgetItem(exportPaths[location])

            rc = self.tw_exportPaths.rowCount()
            self.tw_exportPaths.insertRow(rc)

            self.tw_exportPaths.setItem(rc, 0, locationItem)
            self.tw_exportPaths.setItem(rc, 1, pathItem)
            self.tw_exportPaths.setRowHeight(rc, 15)

        self.tw_exportPaths.resizeColumnsToContents()

    @err_catcher(name=__name__)
    def refreshRenderPaths(self, configData=None):
        if configData is None:
            configData = self.projectData
        
        renderPaths = self.core.paths.getRenderProductBasePaths(
            default=False, configData=configData
        )
        self.tw_renderPaths.setRowCount(0)
        for location in renderPaths:
            locationItem = QTableWidgetItem(location)
            pathItem = QTableWidgetItem(renderPaths[location])

            rc = self.tw_renderPaths.rowCount()
            self.tw_renderPaths.insertRow(rc)

            self.tw_renderPaths.setItem(rc, 0, locationItem)
            self.tw_renderPaths.setItem(rc, 1, pathItem)
            self.tw_renderPaths.setRowHeight(rc, 15)

        self.tw_renderPaths.resizeColumnsToContents()

    @err_catcher(name=__name__)
    def addExportPathClicked(self):
        self.dlg_addExportPath = AddProductPathDialog(self.core, "export", self)
        self.dlg_addExportPath.pathAdded.connect(self.refreshExportPaths)
        self.dlg_addExportPath.show()

    @err_catcher(name=__name__)
    def removeExportPathClicked(self):
        selection = self.tw_exportPaths.selectedItems()
        if selection:
            for item in selection:
                if item.column() == 0:
                    self.core.paths.removeExportProductBasePath(
                        item.text(), configData=self.projectData
                    )
            self.refreshExportPaths()
        else:
            self.core.popup("No path selected")

    @err_catcher(name=__name__)
    def addRenderPathClicked(self):
        self.dlg_addRenderPath = AddProductPathDialog(self.core, "render", self)
        self.dlg_addRenderPath.pathAdded.connect(self.refreshRenderPaths)
        self.dlg_addRenderPath.show()

    @err_catcher(name=__name__)
    def removeRenderPathClicked(self):
        selection = self.tw_renderPaths.selectedItems()
        if selection:
            for item in selection:
                if item.column() == 0:
                    self.core.paths.removeRenderProductBasePath(
                        item.text(), configData=self.projectData
                    )
            self.refreshRenderPaths()
        else:
            self.core.popup("No path selected")

    @err_catcher(name=__name__)
    def reload(self):
        idx = self.tw_settings.currentIndex()
        self.core.prismSettings(restart=True)
        self.core.ps.tw_settings.setCurrentIndex(idx)

    @err_catcher(name=__name__)
    def curPnameEdited(self, text):
        self.validate(self.e_curPname)

    @err_catcher(name=__name__)
    def enterEvent(self, event):
        try:
            QApplication.restoreOverrideCursor()
        except:
            pass


class AddProductPathDialog(QDialog):

    pathAdded = Signal()

    def __init__(self, core, pathType, parent=None):
        QDialog.__init__(self)
        self.core = core
        self.pathType = pathType
        self.parent = parent
        self.setupUi(parent=parent)
        self.connectEvents()

    @err_catcher(name=__name__)
    def setupUi(self, parent=None):
        self.core.parentWindow(self, parent)
        self.setWindowTitle("Add additional %s location" % self.pathType)
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.lo_name = QGridLayout()
        self.l_name = QLabel("Location Name:")
        self.e_name = QLineEdit()
        self.lo_name.addWidget(self.l_name, 0, 0)
        self.lo_name.addWidget(self.e_name, 0, 1, 1, 2)
        self.lo_main.addLayout(self.lo_name)

        self.l_pathInfo = QLabel("Path:")
        self.l_path = QLabel("")
        self.l_path.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.e_path = QLineEdit()
        self.b_browse = QPushButton("...")
        self.lo_name.addWidget(self.l_pathInfo, 1, 0)
        self.lo_name.addWidget(self.e_path, 1, 1)
        self.lo_name.addWidget(self.b_browse, 1, 2)
        self.b_browse.setContextMenuPolicy(Qt.CustomContextMenu)

        self.lo_main.addStretch()

        self.bb_main = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.bb_main.buttons()[0].setText("Add")
        self.bb_main.accepted.connect(self.addPath)
        self.bb_main.rejected.connect(self.reject)

        self.lo_main.addWidget(self.bb_main)

        self.resize(500 * self.core.uiScaleFactor, 150 * self.core.uiScaleFactor)

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.e_name.textChanged.connect(lambda x: self.validate(self.e_name, x))
        self.e_path.textChanged.connect(lambda x: self.validate(self.e_path, x))
        self.b_browse.clicked.connect(self.browse)
        self.b_browse.customContextMenuRequested.connect(
            lambda: self.core.openFolder(self.e_path.text())
        )

    @err_catcher(name=__name__)
    def browse(self):
        windowTitle = "Select %s location" % self.pathType
        selectedPath = QFileDialog.getExistingDirectory(
            self, windowTitle, self.e_path.text()
        )

        if selectedPath:
            self.e_path.setText(self.core.fixPath(selectedPath))

    @err_catcher(name=__name__)
    def validate(self, uiWidget, origText=None):
        if uiWidget == self.e_name:
            allowChars = ["_", " "]
        else:
            allowChars = ["/", "\\", "_", " ", ":"]

        self.core.validateLineEdit(uiWidget, allowChars=allowChars)

    @err_catcher(name=__name__)
    def addPath(self):
        location = self.e_name.text()
        path = self.e_path.text()

        if not location:
            self.core.popup("No location specified")
            return

        if not path:
            self.core.popup("No path specified")
            return

        if self.pathType == "export":
            self.core.paths.addExportProductBasePath(
                location, path, configData=self.parent.projectData
            )
        else:
            self.core.paths.addRenderProductBasePath(
                location, path, configData=self.parent.projectData
            )

        self.pathAdded.emit()
        self.close()


class HelpLabel(QLabel):

    signalEntered = Signal(object)

    def __init__(self, parent):
        super(HelpLabel, self).__init__()
        self.parent = parent

    def enterEvent(self, event):
        self.signalEntered.emit(self)

    def mouseMoveEvent(self, event):
        QToolTip.showText(QCursor.pos(), self.msg)


class EnvironmentWidget(QDialog):
    def __init__(self, parent):
        super(EnvironmentWidget, self).__init__()
        self.parent = parent
        self.core = self.parent.core
        self.core.parentWindow(self, parent=self.parent)
        self.setupUi()
        self.refreshEnvironment()

    def sizeHint(self):
        return QSize(1000, 700)

    def setupUi(self):
        self.setWindowTitle("Current Environment")
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.tw_environment = QTableWidget()
        self.tw_environment.setColumnCount(2)
        self.tw_environment.setHorizontalHeaderLabels(["Variable", "Value"])
        self.tw_environment.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tw_environment.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tw_environment.horizontalHeader().setStretchLastSection(True)
        self.tw_environment.verticalHeader().setVisible(False)
        self.tw_environment.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.lo_main.addWidget(self.tw_environment)

    def refreshEnvironment(self):
        self.tw_environment.setRowCount(0)
        for idx, key in enumerate(sorted(os.environ)):
            self.tw_environment.insertRow(idx)
            item = QTableWidgetItem(key)
            self.tw_environment.setItem(idx, 0, item)
            item = QTableWidgetItem(os.environ[key])
            self.tw_environment.setItem(idx, 1, item)

        self.tw_environment.resizeColumnsToContents()


class ExpressionWindow(QDialog):
    def __init__(self, parent):
        super(ExpressionWindow, self).__init__()
        self.parent = parent
        self.core = self.parent.core
        self.core.parentWindow(self, parent=self.parent)
        self.setupUi()

    def sizeHint(self):
        return QSize(800, 500)

    def setupUi(self):
        self.setWindowTitle("Edit Expression")
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.te_expression = QTextEdit()
        tabStop = 4
        metrics = QFontMetrics(self.te_expression.font())
        self.te_expression.setTabStopWidth(tabStop * metrics.width(' '))

        self.bb_main = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.bb_main.accepted.connect(self.onAcceptClicked)
        self.bb_main.rejected.connect(self.reject)

        self.lo_main.addWidget(self.te_expression)
        self.lo_main.addWidget(self.bb_main)

    def onAcceptClicked(self):
        result = self.core.projects.validateExpression(self.te_expression.toPlainText())
        if result and result["valid"]:
            self.accept()
        else:
            msg = "Invalid expression."
            if result and result.get("error"):
                msg += "\n\n%s" % result["error"]

            self.core.popup(msg)


if __name__ == "__main__":
    qapp = QApplication(sys.argv)
    from UserInterfacesPrism import qdarkstyle

    qapp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))
    appIcon = QIcon(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "UserInterfacesPrism",
            "p_tray.png",
        )
    )
    qapp.setWindowIcon(appIcon)

    pc = PrismCore.PrismCore(prismArgs=["loadProject", "noProjectBrowser"])

    pc.prismSettings()
    qapp.exec_()
