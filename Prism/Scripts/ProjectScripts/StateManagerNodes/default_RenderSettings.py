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

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2

from PrismUtils.Decorators import err_catcher


class RenderSettingsClass(object):
    className = "Render Settings"
    listType = "Export"

    @classmethod
    def isActive(cls, core):
        return core.appPlugin.pluginName in ["Houdini", "Maya"]

    @classmethod
    def getPresets(cls, core):
        presets = {}
        appName = core.appPlugin.pluginName
        presetPath = os.path.join(
            os.path.dirname(core.prismIni), "Presets", "RenderSettings", appName
        )
        if not os.path.exists(presetPath):
            return presets

        for pFile in os.listdir(presetPath):
            base, ext = os.path.splitext(pFile)
            if ext != ".yml":
                continue

            presets[base] = os.path.join(presetPath, pFile)

        return presets

    @classmethod
    def applyPreset(cls, core, presetPath, **kwargs):
        preset = core.readYaml(presetPath)
        if "renderSettings" not in preset:
            return

        preset = preset["renderSettings"]

        getattr(
            core.appPlugin, "sm_renderSettings_setCurrentSettings", lambda x, y: None
        )(core, preset, **kwargs)

    @err_catcher(name=__name__)
    def setup(self, state, core, stateManager, node=None, stateData=None):
        self.state = state
        self.core = core
        self.stateManager = stateManager

        self.cb_addSetting.lineEdit().setPlaceholderText("Select setting to add")

        getattr(self.core.appPlugin, "sm_renderSettings_startup", lambda x: None)(self)
        if state:
            self.e_name.setText("Render Settings")
            self.nameChanged("Render Settings")
        self.editChanged(self.chb_editSettings.isChecked())
        self.connectEvents()

        if stateData is not None:
            self.loadData(stateData)

    @err_catcher(name=__name__)
    def loadData(self, data):
        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "presetoption" in data:
            self.updateUi()
            idx = self.cb_presetOption.findText(data["presetoption"])
            if idx != -1:
                self.cb_presetOption.setCurrentIndex(idx)
        if "editsettings" in data:
            self.chb_editSettings.setChecked(
                eval(
                    data["editsettings"]
                    .replace("PySide.QtCore.", "")
                    .replace("PySide2.QtCore.", "")
                )
            )
        if "rendersettings" in data:
            settings = self.core.writeYaml(data=data["rendersettings"])
            self.te_settings.setPlainText(settings)
        if "stateenabled" in data:
            self.state.setCheckState(
                0,
                eval(
                    data["stateenabled"]
                    .replace("PySide.QtCore.", "")
                    .replace("PySide2.QtCore.", "")
                ),
            )

        getattr(self.core.appPlugin, "sm_renderSettings_loadData", lambda x, y: None)(
            self, data
        )

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.cb_presetOption.activated.connect(self.stateManager.saveStatesToScene)
        self.b_loadCurrent.clicked.connect(self.loadCurrent)
        self.b_resetSettings.clicked.connect(self.resetSettings)
        self.b_loadPreset.clicked.connect(self.showPresets)
        self.b_savePreset.clicked.connect(self.savePreset)
        self.chb_editSettings.stateChanged.connect(self.editChanged)
        self.cb_addSetting.activated.connect(self.settingActivated)
        self.cb_addSetting.lineEdit().editingFinished.connect(self.settingActivated)
        self.te_settings.origFocusOutEvent = self.te_settings.focusOutEvent
        self.te_settings.focusOutEvent = self.focusOut
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
        if not self.stateManager.standalone:
            self.b_applySettings.clicked.connect(self.applySettings)

    @err_catcher(name=__name__)
    def nameChanged(self, text):
        sText = text

        if self.state.text(0).endswith(" - disabled"):
            sText += " - disabled"

        self.state.setText(0, sText)

    @err_catcher(name=__name__)
    def editChanged(self, state):
        self.w_presetOption.setVisible(not state)
        self.w_loadCurrent.setVisible(state)
        self.w_addSetting.setVisible(state)
        self.gb_settings.setVisible(state)
        self.te_settings.setPlainText("")
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def updateUi(self):
        curPreset = self.cb_presetOption.currentText()
        self.cb_presetOption.clear()
        self.cb_presetOption.addItems(
            sorted(self.getPresets(self.core).keys(), key=lambda x: x.lower())
        )
        idx = self.cb_presetOption.findText(curPreset)
        if idx != -1:
            self.cb_presetOption.setCurrentIndex(idx)
        else:
            self.stateManager.saveStatesToScene()
        if self.state:
            self.nameChanged(self.e_name.text())

        if not self.cb_addSetting.isHidden():
            settings = getattr(
                self.core.appPlugin, "sm_renderSettings_getCurrentSettings", lambda x, y: {}
            )(self, asString=False)
            self.cb_addSetting.clear()
            settingNames = [x.keys()[0] for x in settings]
            settingNames.insert(0, "")
            self.cb_addSetting.addItems(settingNames)

    @err_catcher(name=__name__)
    def focusOut(self, event):
        self.stateManager.saveStatesToScene()
        self.te_settings.origFocusOutEvent(event)

    @err_catcher(name=__name__)
    def loadCurrent(self):
        settings = getattr(
            self.core.appPlugin, "sm_renderSettings_getCurrentSettings", lambda x: {}
        )(self)
        self.te_settings.setPlainText(settings)
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def resetSettings(self):
        getattr(
            self.core.appPlugin, "sm_renderSettings_applyDefaultSettings", lambda x: {}
        )(self)

    @err_catcher(name=__name__)
    def settingActivated(self, text=None):
        text = self.cb_addSetting.currentText()
        settings = getattr(
            self.core.appPlugin, "sm_renderSettings_getCurrentSettings", lambda x, y: {}
        )(self, asString=False)
        setting = [x for x in settings if x.keys()[0] == text]
        if setting:
            settingsStr = self.core.writeYaml(data=setting)
            curStr = self.te_settings.toPlainText()
            self.te_settings.setPlainText(curStr + settingsStr)
            self.cb_addSetting.setCurrentIndex(0)

    @err_catcher(name=__name__)
    def showPresets(self):
        presets = self.getPresets(self.core)
        if not presets:
            self.core.popup("No presets found.")
            return

        pmenu = QMenu(self.stateManager)

        for preset in sorted(presets):
            add = QAction(preset, self)
            add.triggered.connect(lambda x=None, p=preset: self.loadPreset(presets[p]))
            pmenu.addAction(add)

        pmenu.exec_(QCursor().pos())

    @err_catcher(name=__name__)
    def loadPreset(self, presetPath):
        preset = self.core.readYaml(presetPath)
        if "renderSettings" not in preset:
            return

        settings = self.core.writeYaml(data=preset["renderSettings"])
        self.te_settings.setPlainText(settings)
        self.stateManager.saveStatesToScene()

    @err_catcher(name=__name__)
    def savePreset(self):
        result = QInputDialog.getText(self, "Save preset", "Presetname:")
        if not result[1]:
            return

        appName = self.core.appPlugin.pluginName
        presetPath = os.path.join(
            os.path.dirname(self.core.prismIni),
            "Presets",
            "RenderSettings",
            appName,
            "%s.yml" % result[0],
        )

        if self.chb_editSettings.isChecked():
            presetStr = self.te_settings.toPlainText()
        else:
            presetStr = getattr(
                self.core.appPlugin,
                "sm_renderSettings_getCurrentSettings",
                lambda x: {},
            )(self)

        preset = self.core.readYaml(data=presetStr)
        if preset is None:
            self.core.popup("Invalid preset syntax.")
        else:
            self.core.writeYaml(presetPath, {"renderSettings": preset})

        self.updateUi()

    @err_catcher(name=__name__)
    def applySettings(self, settings=None):
        if self.chb_editSettings.isChecked():
            if not settings:
                settings = self.te_settings.toPlainText()
            preset = self.core.readYaml(data=settings)
            getattr(
                self.core.appPlugin,
                "sm_renderSettings_setCurrentSettings",
                lambda x, y: None,
            )(self, preset, state=self)
        else:
            presets = self.getPresets(self.core)
            selPreset = self.cb_presetOption.currentText()
            if selPreset not in presets:
                return

            self.applyPreset(self.core, presets[selPreset], state=self)

    @err_catcher(name=__name__)
    def preExecuteState(self):
        warnings = []

        if self.chb_editSettings.isChecked() and not self.te_settings.toPlainText():
            warnings.append(["No rendersettings are specified.", "", 2])

        warnings += getattr(
            self.core.appPlugin, "sm_renderSettings_preExecute", lambda x: []
        )(self)

        return [self.state.text(0), warnings]

    @err_catcher(name=__name__)
    def executeState(self, parent, useVersion="next"):
        self.applySettings()
        return [self.state.text(0) + " - success"]

    @err_catcher(name=__name__)
    def getStateProps(self):
        stateProps = {}
        stateProps.update(
            getattr(
                self.core.appPlugin, "sm_renderSettings_getStateProps", lambda x: {}
            )(self)
        )
        stateProps.update(
            {
                "statename": self.e_name.text(),
                "presetoption": self.cb_presetOption.currentText(),
                "editsettings": str(self.chb_editSettings.isChecked()),
                "rendersettings": self.core.readYaml(
                    data=self.te_settings.toPlainText()
                ),
                "stateenabled": str(self.state.checkState(0)),
            }
        )

        return stateProps
