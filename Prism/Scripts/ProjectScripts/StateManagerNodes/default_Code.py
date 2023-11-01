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

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


from PrismUtils import PrismWidgets
from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class CodeClass(object):
    className = "Code"
    listType = "Export"

    def setup(self, state, core, stateManager, stateData=None):
        self.core = core
        self.state = state
        self.stateManager = stateManager
        self.canSetVersion = True
        self.e_name.setText(state.text(0))
        self.l_name.setVisible(False)
        self.e_name.setVisible(False)

        self.connectEvents()

        if stateData is not None:
            self.loadData(stateData)

    @err_catcher(name=__name__)
    def loadData(self, data):
        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "code" in data:
            self.te_code.setPlainText(data["code"])
        if "stateenabled" in data and self.listType == "Export":
            self.state.setCheckState(
                0,
                eval(
                    data["stateenabled"]
                    .replace("PySide.QtCore.", "")
                    .replace("PySide2.QtCore.", "")
                ),
            )

        self.core.callback("onStateSettingsLoaded", self, data)

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        self.te_code.textChanged.connect(self.stateManager.saveStatesToScene)
        self.b_presets.clicked.connect(self.showPresets)
        self.b_execute.clicked.connect(self.executePressed)

    @err_catcher(name=__name__)
    def nameChanged(self, text):
        self.state.setText(0, text)

    @err_catcher(name=__name__)
    def updateUi(self):
        return True

    @err_catcher(name=__name__)
    def showPresets(self):
        menu = QMenu(self)

        presets = self.core.projects.getCodePresets()
        for preset in presets:
            act_open = QAction(preset["name"], self)
            act_open.triggered.connect(lambda x=None, p=preset: self.setCode(p["code"]))
            menu.addAction(act_open)

        act_open = QAction("Manage presets...", self)
        act_open.triggered.connect(self.managePresets)
        menu.addAction(act_open)

        menu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def getPresets(self):
        return self.core.projects.getPresets()

    @err_catcher(name=__name__)
    def managePresets(self):
        if not hasattr(self, "dlg_manage"):
            self.dlg_manage = ManagePresetsDlg(self)

        self.dlg_manage.show()

    @err_catcher(name=__name__)
    def getCode(self):
        return self.te_code.toPlainText()

    @err_catcher(name=__name__)
    def setCode(self, code):
        return self.te_code.setPlainText(code)

    @err_catcher(name=__name__)
    def executePressed(self):
        result = self.executeCode()
        if result["result"] == "success":
            msg = "Code executed successfully."
            if result["val"] is not None:
                msg += "\n\n%s" % result["val"]

            self.core.popup(msg, severity="info")
        else:
            msg = "Failed to execute the code:\n\n%s" % result["error"]
            self.core.popup(msg)

    @err_catcher(name=__name__)
    def executeCode(self):
        if sys.version[0] == "3":
            from io import StringIO
        else:
            from cStringIO import StringIO

        code = self.getCode()
        old_stdout = sys.stdout
        redirected_output = sys.stdout = StringIO()

        try:
            exec(code, {"pcore": self.core, "state": self})
        except Exception as e:
            sys.stdout = old_stdout
            return {"result": "error", "error": e, "val": redirected_output.getvalue()}

        sys.stdout = old_stdout

        return {"result": "success", "val": redirected_output.getvalue()}

    @err_catcher(name=__name__)
    def preExecuteState(self):
        warnings = []

        if not self.getCode():
            warnings.append(["No code is specified.", "", 2])

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def executeState(self, parent, useVersion="next"):
        result = self.executeCode()
        if result["result"] == "success":
            return [self.state.text(0) + " - success"]
        else:
            return [
                self.state.text(0)
                + " - error - %s" % result["error"]
            ]

    @err_catcher(name=__name__)
    def getStateProps(self):
        stateProps = {}
        stateProps.update(
            {
                "statename": self.e_name.text(),
                "code": self.te_code.toPlainText(),
                "stateenabled": str(self.state.checkState(0)),
            }
        )
        return stateProps


class ManagePresetsDlg(QDialog):
    def __init__(self, origin):
        super(ManagePresetsDlg, self).__init__()
        self.origin = origin
        self.core = self.origin.core
        self.core.parentWindow(self, parent=origin)
        self.setupUI()
        self.refreshUI()

    @err_catcher(name=__name__)
    def sizeHint(self):
        return QSize(550, 350)

    @err_catcher(name=__name__)
    def setupUI(self):
        self.setWindowTitle("Manage Presets")
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.w_content = QSplitter()

        self.w_presets = QWidget()
        self.lo_presets = QVBoxLayout()
        self.lo_presets.setContentsMargins(0, 0, 0, 0)
        self.w_presets.setLayout(self.lo_presets)
        
        self.w_header = QWidget()
        self.lo_header = QHBoxLayout()
        self.lo_header.setContentsMargins(0, 0, 0, 0)
        self.w_header.setLayout(self.lo_header)
        self.l_preset = QLabel("Presets:")
        self.b_add = QToolButton()
        self.b_remove = QToolButton()
        self.b_add.setFocusPolicy(Qt.NoFocus)
        self.b_remove.setFocusPolicy(Qt.NoFocus)
        self.lo_header.addWidget(self.l_preset)
        self.lo_header.addStretch()
        self.lo_header.addWidget(self.b_add)
        self.lo_header.addWidget(self.b_remove)
        self.lw_presets = QListWidget()
        self.lw_presets.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lw_presets.customContextMenuRequested.connect(self.rclPreset)
        self.lw_presets.itemSelectionChanged.connect(self.refreshCode)
        self.lw_presets.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.lo_presets.addWidget(self.w_header)
        self.lo_presets.addWidget(self.lw_presets)

        self.b_add.setToolTip("Add Preset")
        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_add.setIcon(icon)
        self.b_add.clicked.connect(self.createPresetDlg)

        self.b_remove.setToolTip("Remove Preset")
        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "remove.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_remove.setIcon(icon)
        self.b_remove.clicked.connect(self.removePreset)

        self.w_code = QWidget()
        self.lo_code = QVBoxLayout()
        self.lo_code.setContentsMargins(0, 0, 0, 0)
        self.w_code.setLayout(self.lo_code)
        self.l_code = QLabel("Code:")
        self.te_code = QPlainTextEdit()
        self.te_code.textChanged.connect(self.presetChanged)
        self.lo_code.addWidget(self.l_code)
        self.lo_code.addWidget(self.te_code)

        self.w_content.addWidget(self.w_presets)
        self.w_content.addWidget(self.w_code)
        self.w_content.setSizes([150, 300])

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Save", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Cancel", QDialogButtonBox.RejectRole)
        self.bb_main.accepted.connect(self.dialogAccepted)
        self.bb_main.rejected.connect(self.reject)

        self.lo_main.addWidget(self.w_content)
        self.lo_main.addWidget(self.bb_main)

    @err_catcher(name=__name__)
    def refreshUI(self):
        names = [item.text() for item in self.lw_presets.selectedItems()]
        self.lw_presets.clear()
        presets = self.core.projects.getCodePresets()
        for apreset in presets:
            item = QListWidgetItem(apreset["name"])
            item.setData(Qt.UserRole, apreset)
            self.lw_presets.addItem(item)
            if apreset in names:
                item.setSelected(True)

    @err_catcher(name=__name__)
    def rclPreset(self, pos):
        rcmenu = QMenu(self)

        exp = QAction("Add Preset", self)
        exp.triggered.connect(self.createPresetDlg)
        rcmenu.addAction(exp)

        item = self.lw_presets.itemFromIndex(self.lw_presets.indexAt(pos))
        if item:
            exp = QAction("Remove", self)
            exp.triggered.connect(self.removePreset)
            rcmenu.addAction(exp)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def refreshCode(self):
        self.te_code.blockSignals(True)
        self.te_code.clear()

        presetItems = self.lw_presets.selectedItems()
        if len(presetItems) != 1:
            return

        presetData = presetItems[0].data(Qt.UserRole)
        code = presetData.get("code", "")
        self.te_code.setPlainText(code)
        self.te_code.blockSignals(False)

    @err_catcher(name=__name__)
    def presetChanged(self):
        items = self.lw_presets.selectedItems()
        if len(items) != 1:
            return

        code = self.te_code.toPlainText()
        data = items[0].data(Qt.UserRole)
        data["code"] = code
        items[0].setData(Qt.UserRole, data)

    @err_catcher(name=__name__)
    def selectPresets(self, names):
        self.lw_presets.clearSelection()
        for idx in range(self.lw_presets.count()):
            item = self.lw_presets.item(idx)
            if item.text() in names:
                item.setSelected(True)

    @err_catcher(name=__name__)
    def showEvent(self, event):
        self.l_code.setMinimumHeight(self.w_header.height())

    @err_catcher(name=__name__)
    def dialogAccepted(self):
        presets = []
        for idx in range(self.lw_presets.count()):
            item = self.lw_presets.item(idx)
            data = item.data(Qt.UserRole)
            presets.append(data)

        self.core.projects.setCodePresets(presets)
        self.accept()

    @err_catcher(name=__name__)
    def createPresetDlg(self):
        if hasattr(self, "newItem") and self.newItem.isVisible():
            self.newItem.close()

        self.newItem = PrismWidgets.CreateItem(
            core=self.core, showType=False, validate=False
        )
        self.core.parentWindow(self.newItem, parent=self)
        self.newItem.e_item.setFocus()
        self.newItem.setWindowTitle("Create Preset")
        self.newItem.l_item.setText("Preset:")
        self.newItem.accepted.connect(self.createPreset)
        self.newItem.show()

    @err_catcher(name=__name__)
    def createPreset(self):
        name = self.newItem.e_item.text()
        presets = self.core.projects.getCodePresets()
        presetNames = [f["name"] for f in presets]
        if name in presetNames:
            msg = "A preset with name \"%s\" does already exist." % name
            self.core.popup(msg, parent=self)
            return

        self.core.projects.addCodePreset(name)
        self.refreshUI()
        self.selectPresets([name])

    @err_catcher(name=__name__)
    def removePreset(self):
        names = [item.text() for item in self.lw_presets.selectedItems()]
        for name in names:
            self.core.projects.removeCodePreset(name)

        self.refreshUI()
