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
import subprocess
import shutil
import platform
import datetime
import logging
from collections import OrderedDict

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2

scriptPath = os.path.abspath(os.path.dirname(__file__))
if scriptPath not in sys.path:
    sys.path.append(scriptPath)

if __name__ == "__main__":
    import PrismCore

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *
    psVersion = 1


for i in [
    "PrismSettings_ui",
    "PrismSettings_ui_ps2",
    "SetProject",
]:
    try:
        del sys.modules[i]
    except:
        pass

import SetProject

if psVersion == 1:
    import PrismSettings_ui
else:
    import PrismSettings_ui_ps2 as PrismSettings_ui

from UserInterfacesPrism import qdarkstyle
from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class PrismSettings(QDialog, PrismSettings_ui.Ui_dlg_PrismSettings):
    def __init__(self, core):
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.core.parentWindow(self)

        projectsUi = SetProject.SetProjectClass(self.core, self)
        projectsUi.l_project.setVisible(False)
        projectsUi.w_startup.setVisible(False)

        self.lo_projects.addWidget(projectsUi)

        self.groupboxes = [self.gb_curPversions]
        self.updateIntervals = OrderedDict([
            ("On every launch", 0),
            ("Once per day", 1),
            ("Once per week", 7),
            ("Once per month", 30),
            ("Never", -1),
        ])

        self.dependencyStates = {
            "always": "Always",
            "publish": "On Publish",
            "never": "Never",
        }

        self.useLocalStates = {
            "inherit": "Inherit from project",
            "on": "On",
            "off": "Off",
        }

        self.l_about.setText(self.core.getAboutString())
        self.cb_checkForUpdates.addItems(list(self.updateIntervals.keys()))
        self.cb_checkForUpdates.setCurrentIndex(2)

        self.loadUI()
        self.loadSettings()
        self.refreshPlugins()

        self.forceVersionsToggled(self.gb_curPversions.isChecked())

        self.core.callback(
            name="onPrismSettingsOpen", types=["curApp", "custom"], args=[self]
        )

        self.connectEvents()
        self.setFocus()

        screenH = QApplication.desktop().screenGeometry().height()
        space = 100
        if screenH < (self.height() + space):
            self.resize(self.width(), screenH - space)

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.b_checkForUpdates.customContextMenuRequested.connect(self.cmenu_update)
        self.e_fname.textChanged.connect(lambda x: self.validate(self.e_fname, x))
        self.e_lname.textChanged.connect(lambda x: self.validate(self.e_lname, x))
        self.e_abbreviation.textChanged.connect(
            lambda x: self.validate(self.e_abbreviation, x)
        )
        self.b_browseLocal.clicked.connect(lambda: self.browse("local"))
        self.b_browseLocal.customContextMenuRequested.connect(
            lambda: self.core.openFolder(self.e_localPath.text())
        )
        self.e_curPname.textEdited.connect(self.curPnameEdited)
        self.chb_curPuseFps.toggled.connect(self.pfpsToggled)
        self.chb_prjResolution.toggled.connect(self.prjResolutionToggled)
        self.gb_curPversions.toggled.connect(self.forceVersionsToggled)
        for i in self.forceVersionPlugins:
            self.forceVersionPlugins[i]["b"].clicked.connect(
                lambda y=None, x=i: self.curPshowList(x)
            )
        for i in self.exOverridePlugins:
            self.exOverridePlugins[i]["chb"].stateChanged.connect(
                lambda x, y=i: self.orToggled(y, x)
            )
            self.exOverridePlugins[i]["b"].clicked.connect(
                lambda y=None, x=(i + "OR"): self.browse(x, getFile=True)
            )
            self.exOverridePlugins[i]["b"].customContextMenuRequested.connect(
                lambda x, y=i: self.core.openFolder(
                    self.exOverridePlugins[y]["le"].text()
                )
            )
        for i in self.integrationPlugins:
            self.integrationPlugins[i]["badd"].clicked.connect(
                lambda y=None, x=i: self.integrationAdd(x)
            )
            self.integrationPlugins[i]["bremove"].clicked.connect(
                lambda y=None, x=i: self.integrationRemove(x)
            )

        self.b_checkForUpdates.clicked.connect(self.checkForUpdates)
        self.b_changelog.clicked.connect(self.changelog)
        self.b_startTray.clicked.connect(self.startTray)
        self.b_browseRV.clicked.connect(lambda: self.browse("rv"))
        self.b_browseRV.customContextMenuRequested.connect(
            lambda: self.core.openFolder(self.e_rvPath.text())
        )
        self.b_browseDJV.clicked.connect(lambda: self.browse("djv"))
        self.b_browseDJV.customContextMenuRequested.connect(
            lambda: self.core.openFolder(self.e_djvPath.text())
        )
        self.tw_plugins.customContextMenuRequested.connect(self.rclPluginList)
        self.b_loadPlugin.clicked.connect(self.loadExternalPlugin)
        self.b_loadPlugin.customContextMenuRequested.connect(self.rclLoadPlugin)
        self.b_reloadPlugins.clicked.connect(self.reloadPlugins)
        self.b_createPlugin.clicked.connect(self.createPluginWindow)
        self.buttonBox.accepted.connect(self.saveSettings)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(lambda: self.saveSettings(changeProject=False))

    @err_catcher(name=__name__)
    def validate(self, uiWidget, origText=None):
        self.core.validateLineEdit(uiWidget)

        if uiWidget != self.e_abbreviation:
            abbrev = self.core.users.getUserAbbreviation(
                "%s %s" % (self.e_fname.text(), self.e_lname.text()), fromConfig=False
            )
            self.e_abbreviation.setText(abbrev)

    @err_catcher(name=__name__)
    def pfpsToggled(self, checked):
        self.sp_curPfps.setEnabled(checked)

    @err_catcher(name=__name__)
    def prjResolutionToggled(self, checked):
        self.sp_prjResolutionWidth.setEnabled(checked)
        self.l_prjResolutionX.setEnabled(checked)
        self.sp_prjResolutionHeight.setEnabled(checked)

    @err_catcher(name=__name__)
    def forceVersionsToggled(self, checked):
        self.w_versions.setVisible(checked)

    @err_catcher(name=__name__)
    def browse(self, bType="", getFile=False, windowTitle=None, uiEdit=None):
        if bType == "local":
            windowTitle = "Select local project path"
            uiEdit = self.e_localPath
        elif bType == "rv":
            windowTitle = "Select RV path"
            uiEdit = self.e_rvPath
        elif bType == "djv":
            windowTitle = "Select DJV path"
            uiEdit = self.e_djvPath
        elif bType.endswith("OR"):
            pName = bType[:-2]
            windowTitle = "Select %s executable" % pName
            uiEdit = self.exOverridePlugins[pName]["le"]
        elif windowTitle is None or uiEdit is None:
            return

        if getFile:
            if platform.system() == "Windows":
                fStr = "Executable (*.exe)"
            else:
                fStr = "All files (*)"

            selectedPath = QFileDialog.getOpenFileName(
                self, windowTitle, uiEdit.text(), fStr
            )[0]
        else:
            selectedPath = QFileDialog.getExistingDirectory(
                self, windowTitle, uiEdit.text()
            )

        if selectedPath != "":
            uiEdit.setText(self.core.fixPath(selectedPath))

    @err_catcher(name=__name__)
    def orToggled(self, prog, state):
        self.exOverridePlugins[prog]["le"].setEnabled(state)
        self.exOverridePlugins[prog]["b"].setEnabled(state)

    @err_catcher(name=__name__)
    def rclPluginList(self, pos=None):
        selPlugs = []
        for i in self.tw_plugins.selectedItems():
            if i.row() not in selPlugs:
                selPlugs.append(i.row())

        rcmenu = QMenu(self)

        act_reload = rcmenu.addAction("Reload", lambda: self.reloadPlugins(selected=True))
        act_load = rcmenu.addAction("Load", lambda: self.loadPlugins(selected=True))
        act_unload = rcmenu.addAction("Unload", lambda: self.loadPlugins(selected=True, unload=True))
        act_open = rcmenu.addAction("Open in explorer", self.openPluginFolder)

        if len(selPlugs) > 1:
            act_open.setEnabled(False)

        if len(selPlugs) == 1:
            if self.tw_plugins.cellWidget(selPlugs[0], 0).isChecked():
                act_load.setEnabled(False)
            else:
                act_reload.setEnabled(False)
                act_unload.setEnabled(False)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def rclLoadPlugin(self, pos=None):
        menu = QMenu(self)
        act_addPath = menu.addAction("Add plugin searchpath...", self.addPluginSearchpath)
        menu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def integrationAdd(self, prog):
        result = self.core.integration.addIntegration(prog)
        if result:
            self.refreshIntegrations()

    @err_catcher(name=__name__)
    def integrationRemove(self, prog):
        items = self.integrationPlugins[prog]["lw"].selectedItems()
        if len(items) == 0:
            return

        installPath = items[0].text()
        result = self.core.integration.removeIntegration(prog, installPath)

        if result:
            self.refreshIntegrations()

    @err_catcher(name=__name__)
    def changeProject(self):
        self.core.projects.setProject()
        self.close()

    @err_catcher(name=__name__)
    def saveSettings(self, changeProject=True):
        logger.debug("save prism settings")
        cData = {
            "globals": {},
            "localfiles": {},
            "useLocalFiles": {},
            "dccoverrides": {},
        }

        if len(self.e_fname.text()) > 0 and len(self.e_lname.text()) > 1:
            cData["globals"]["username"] = self.e_fname.text() + " " + self.e_lname.text()
            cData["globals"]["username_abbreviation"] = self.e_abbreviation.text()
            self.core.user = self.e_abbreviation.text()

        if hasattr(self.core, "projectName") and self.e_localPath.isEnabled():
            lpath = self.core.fixPath(self.e_localPath.text())
            if not lpath.endswith(os.sep):
                lpath += os.sep

            cData["localfiles"][self.core.projectName] = lpath

        if self.e_localPath.text() != "disabled":
            self.core.localProjectPath = lpath

        if hasattr(self.core, "projectName"):
            useLocal = [x for x in self.useLocalStates if self.useLocalStates[x] == self.cb_userUseLocal.currentText()][0]
            cData["useLocalFiles"][self.core.projectName] = useLocal

        rvPath = self.core.fixPath(self.e_rvPath.text())
        if rvPath != "" and not rvPath.endswith(os.sep):
            rvPath += os.sep
        cData["globals"]["rvpath"] = rvPath

        djvPath = self.core.fixPath(self.e_djvPath.text())
        if djvPath != "" and not djvPath.endswith(os.sep):
            djvPath += os.sep
        cData["globals"]["djvpath"] = djvPath

        cData["globals"]["prefer_djv"] = self.chb_preferDJV.isChecked()
        cData["globals"]["showonstartup"] = self.chb_browserStartup.isChecked()
        cData["globals"]["checkForUpdates"] = self.updateIntervals[self.cb_checkForUpdates.currentText()]
        cData["globals"]["autosave"] = self.chb_autosave.isChecked()
        cData["globals"]["highdpi"] = self.chb_highDPI.isChecked()
        cData["globals"]["send_error_reports"] = self.chb_errorReports.isChecked()
        cData["globals"]["debug_mode"] = self.chb_debug.isChecked()

        for i in self.exOverridePlugins:
            c = self.exOverridePlugins[i]["chb"].isChecked()
            ct = self.exOverridePlugins[i]["le"].text()
            cData["dccoverrides"]["%s_override" % i] = c
            cData["dccoverrides"]["%s_path" % i] = ct

        self.core.callback(name="prismSettings_saveSettings", types=["curApp", "unloadedApps", "custom", "prjManagers"], args=[self, cData])

        if self.core.appPlugin.appType == "3d":
            if self.chb_autosave.isChecked():
                if (
                    not hasattr(self.core, "asThread")
                    or not self.core.asThread.isRunning()
                ):
                    self.core.startasThread()
            else:
                self.core.startasThread(quit=True)

        self.core.setConfig(data=cData)

        self.core.setDebugMode(self.chb_debug.isChecked())

        if os.path.exists(self.core.prismIni):
            cData = {"globals": {}}

            cData["globals"]["debug_mode"] = self.chb_debug.isChecked()
            cData["globals"]["project_name"] = self.e_curPname.text()
            cData["globals"]["uselocalfiles"] = self.chb_curPuseLocal.isChecked()
            cData["globals"]["track_dependencies"] = [x for x in self.dependencyStates if self.dependencyStates[x] == self.cb_dependencies.currentText()][0]
            cData["globals"]["forcefps"] = self.chb_curPuseFps.isChecked()
            cData["globals"]["fps"] = self.sp_curPfps.value()
            cData["globals"]["forceResolution"] = self.chb_prjResolution.isChecked()
            cData["globals"]["resolution"] = [self.sp_prjResolutionWidth.value(), self.sp_prjResolutionHeight.value()]
            cData["globals"]["useMasterVersion"] = self.chb_curPuseMaster.isChecked()
            cData["globals"]["forceversions"] = self.gb_curPversions.isChecked()
            cData["changeProject"] = changeProject

            for i in self.forceVersionPlugins:
                cData["globals"]["%s_version" % i] = self.forceVersionPlugins[i]["le"].text()

            self.core.callback(name="prismSettings_savePrjSettings", types=["curApp", "unloadedApps", "custom", "prjManagers"], args=[self, cData])
            changeProject = cData["changeProject"]
            cData.pop("changeProject")

            self.core.setConfig(data=cData, configPath=self.core.prismIni)
            self.core.useLocalFiles = self.chb_curPuseLocal.isChecked()
            if changeProject:
                self.core.changeProject(self.core.prismIni, settingsTab=self.tw_settings.currentIndex())

        if platform.system() == "Windows":
            trayStartup = os.path.join(
                os.getenv("APPDATA"),
                "Microsoft",
                "Windows",
                "Start Menu",
                "Programs",
                "Startup",
                "Prism Tray.lnk",
            )
            trayLnk = self.core.fixPath(
                os.path.join(self.core.prismLibs, "Tools", "Prism Tray.lnk")
            )

            if self.chb_trayStartup.isChecked():
                if os.path.exists(trayLnk):
                    if os.path.exists(trayStartup):
                        try:
                            os.remove(trayStartup)
                        except WindowsError as e:
                            if e.winerror == 32:
                                QMessageBox.warning(
                                    self,
                                    "Remove link",
                                    "Unable to remove autostart link, because the file is used by another process:\n\n%s"
                                    % trayStartup,
                                )
                            else:
                                raise

                    if not os.path.exists(trayStartup) and os.path.exists(trayLnk):
                        shutil.copy2(trayLnk, trayStartup)
                else:
                    QMessageBox.warning(
                        self,
                        "Prism",
                        "Cannot add Prism to the autostart because this shortcut doesn't exist:\n\n%s\n\nExecute '%s\\Win_Setup_Startmenu.bat' to create the shortcut."
                        % (
                            trayLnk,
                            self.core.fixPath(self.core.prismLibs).replace("/", "\\"),
                        ),
                    )
            elif os.path.exists(trayStartup):
                try:
                    os.remove(trayStartup)
                except WindowsError as e:
                    if e.winerror == 32:
                        QMessageBox.warning(
                            self,
                            "Remove link",
                            "Unable to remove autostart link, because the file is used by another process:\n\n%s"
                            % trayStartup,
                        )
                    else:
                        raise

        elif platform.system() == "Linux":
            trayStartup = "/etc/xdg/autostart/PrismTray.desktop"
            trayLnk = self.core.fixPath(
                os.path.join(self.core.prismLibs, "Tools", "PrismTray.desktop")
            )

            if os.path.exists(trayStartup):
                try:
                    os.remove(trayStartup)
                except:
                    pass

            if self.chb_trayStartup.isChecked():
                if not os.path.exists(trayStartup) and os.path.exists(trayLnk):
                    try:
                        shutil.copy2(trayLnk, trayStartup)
                        os.chmod(trayStartup, 0o777)
                    except:
                        pass

        elif platform.system() == "Darwin":
            userName = (
                os.environ["SUDO_USER"]
                if "SUDO_USER" in os.environ
                else os.environ["USER"]
            )
            trayStartup = (
                "/Users/%s/Library/LaunchAgents/com.user.PrismTray.plist" % userName
            )
            trayLnk = self.core.fixPath(
                os.path.join(self.core.prismLibs, "Tools", "com.user.PrismTray.plist")
            )

            if os.path.exists(trayStartup):
                os.remove(trayStartup)

            if self.chb_trayStartup.isChecked():
                if not os.path.exists(trayStartup) and os.path.exists(trayLnk):
                    shutil.copy2(trayLnk, trayStartup)
                    os.chmod(trayStartup, 0o644)
                    import pwd

                    uid = pwd.getpwnam(userName).pw_uid
                    os.chown(os.path.dirname(trayStartup), uid, -1)
                    os.chown(trayStartup, uid, -1)
                    os.system(
                        "launchctl load /Users/%s/Library/LaunchAgents/com.user.PrismTray.plist"
                        % userName
                    )

        self.core.callback(name="onPrismSettingsSave", types=["custom"], args=[self])

    @err_catcher(name=__name__)
    def loadSettings(self):
        if not os.path.exists(self.core.userini):
            self.core.popup("Prism config does not exist.", title="Load Settings")
            return

        if hasattr(self.core, "projectName"):
            self.l_projectName.setText(self.core.projectName)
        else:
            self.l_projectName.setText("No current project")

        if hasattr(self.core, "projectPath"):
            self.l_projectPath.setText(self.core.projectPath)
        else:
            self.l_projectPath.setText("")

        if (
            hasattr(self.core, "useLocalFiles")
            and self.core.useLocalFiles
            and self.l_projectPath.text() != ""
        ):
            self.e_localPath.setText(self.core.localProjectPath)
        else:
            self.e_localPath.setText("disabled")
            self.e_localPath.setEnabled(False)
            self.b_browseLocal.setEnabled(False)

        if platform.system() == "Windows":
            trayStartupPath = os.path.join(
                os.getenv("APPDATA"),
                "Microsoft",
                "Windows",
                "Start Menu",
                "Programs",
                "Startup",
                "Prism Tray.lnk",
            )
        elif platform.system() == "Linux":
            trayStartupPath = "/etc/xdg/autostart/PrismTray.desktop"
        elif platform.system() == "Darwin":
            userName = (
                os.environ["SUDO_USER"]
                if "SUDO_USER" in os.environ
                else os.environ["USER"]
            )
            trayStartupPath = (
                "/Users/%s/Library/LaunchAgents/com.user.PrismTray.plist" % userName
            )

        self.chb_trayStartup.setChecked(os.path.exists(trayStartupPath))

        configData = self.core.getConfig()
        self.core.callback(name="prismSettings_loadSettings", types=["curApp", "unloadedApps", "custom", "prjManagers"], args=[self, configData])

        if not configData:
            self.core.popup("Loading Prism Settings failed.")
        else:
            gblData = configData.get("globals", {})
            if "username" in gblData:
                uname = gblData["username"].split()

                if len(uname) == 2:
                    self.e_fname.setText(uname[0])
                    self.e_lname.setText(uname[1])

                    self.validate(uiWidget=self.e_fname)
                    self.validate(uiWidget=self.e_lname)

            if "username_abbreviation" in gblData:
                self.e_abbreviation.setText(gblData["username_abbreviation"])
                self.validate(uiWidget=self.e_abbreviation)

            if "showonstartup" in gblData:
                self.chb_browserStartup.setChecked(gblData["showonstartup"])

            updateStatus = gblData.get("update_status", "")
            updateCheckTime = gblData.get("lastUpdateCheck", "")

            self.setUpdateStatus(status=updateStatus, checkTime=updateCheckTime)

            if "checkForUpdates" in gblData:
                if gblData["checkForUpdates"] is True:
                    gblData["checkForUpdates"] = 7
                elif gblData["checkForUpdates"] is False:
                    gblData["checkForUpdates"] = -1

                idx = 1
                for i in self.updateIntervals:
                    if self.updateIntervals[i] == gblData["checkForUpdates"]:
                        fidx = self.cb_checkForUpdates.findText(i)
                        if fidx != -1:
                            idx = fidx
                        break

                self.cb_checkForUpdates.setCurrentIndex(idx)

            if "useLocalFiles" in configData:
                if hasattr(self.core, "projectName") and self.core.projectName in configData["useLocalFiles"]:
                    idx = self.cb_userUseLocal.findText(self.useLocalStates[configData["useLocalFiles"][self.core.projectName]])
                    if idx != -1:
                        self.cb_userUseLocal.setCurrentIndex(idx)

            if "autosave" in gblData:
                self.chb_autosave.setChecked(gblData["autosave"])

            if "highdpi" in gblData:
                self.chb_highDPI.setChecked(gblData["highdpi"])

            if "send_error_reports" in gblData:
                self.chb_errorReports.setChecked(gblData["send_error_reports"])

            if "debug_mode" in gblData:
                self.chb_debug.setChecked(gblData["debug_mode"])

            if "rvpath" in gblData:
                self.e_rvPath.setText(gblData["rvpath"])

            if "djvpath" in gblData:
                self.e_djvPath.setText(gblData["djvpath"])

            if "prefer_djv" in gblData:
                self.chb_preferDJV.setChecked(gblData["prefer_djv"])

            dccData = configData.get("dccoverrides", {})
            for i in self.exOverridePlugins:
                if "%s_override" % i in dccData:
                    self.exOverridePlugins[i]["chb"].setChecked(dccData["%s_override" % i])

                if "%s_path" % i in dccData:
                    self.exOverridePlugins[i]["le"].setText(dccData["%s_path" % i])

                if (
                    not self.exOverridePlugins[i]["chb"].isChecked()
                    and self.exOverridePlugins[i]["le"].text() == ""
                ):
                    execFunc = self.core.getPluginData(i, "getExecutable")
                    if execFunc is not None:
                        examplePath = execFunc()
                        if examplePath is not None:
                            if not os.path.exists(examplePath) and os.path.exists(
                                os.path.dirname(examplePath)
                            ):
                                examplePath = os.path.dirname(examplePath)

                            self.exOverridePlugins[i]["le"].setText(examplePath)

                self.exOverridePlugins[i]["le"].setEnabled(
                    self.exOverridePlugins[i]["chb"].isChecked()
                )
                self.exOverridePlugins[i]["b"].setEnabled(
                    self.exOverridePlugins[i]["chb"].isChecked()
                )

        if os.path.exists(self.core.prismIni):
            configData = self.core.getConfig(configPath=self.core.prismIni)
            self.core.callback(name="prismSettings_loadPrjSettings", types=["curApp", "unloadedApps", "custom", "prjManagers"], args=[self, configData])
            gblData = configData.get("globals", {})

            if "project_name" in gblData:
                self.e_curPname.setText(gblData["project_name"])
            if "uselocalfiles" in gblData:
                self.chb_curPuseLocal.setChecked(gblData["uselocalfiles"])
            if "track_dependencies" in gblData:
                if not self.core.isStr(gblData["track_dependencies"]):
                    gblData["track_dependencies"] = "publish"
                idx = self.cb_dependencies.findText(self.dependencyStates[gblData["track_dependencies"]])
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
            if "forceversions" in gblData:
                self.gb_curPversions.setChecked(gblData["forceversions"])

            for i in self.forceVersionPlugins:
                if "%s_version" % i in gblData:
                    self.forceVersionPlugins[i]["le"].setText(gblData["%s_version" % i])

        else:
            self.l_localPath.setEnabled(False)
            self.w_prjSettings.setEnabled(False)
            self.w_resetPrjScripts.setEnabled(False)

        self.w_userUseLocal.setToolTip(
            "This setting overrides the \"Use additional local project folder\" option in the project settings for the current user. It doesn't affect any other users."
        )

        self.pfpsToggled(self.chb_curPuseFps.isChecked())
        self.w_curPfps.setToolTip(
            "When this option is enabled, Prism checks the fps of scenefiles when they are opened and shows a warning, if they don't match the project fps."
        )

        self.prjResolutionToggled(self.chb_prjResolution.isChecked())
        self.w_prjResolution.setToolTip(
            "When this option is enabled, Prism checks the resolution of Nuke scripts when they are opened and shows a warning, if they don't match the project resolution."
        )

    @err_catcher(name=__name__)
    def loadUI(self):
        self.forceVersionPlugins = {}
        self.exOverridePlugins = {}
        self.integrationPlugins = {}
        self.dccTabs = QTabWidget()

        pluginNames = self.core.getPluginNames()
        for i in pluginNames:
            pVPresets = self.core.getPluginData(i, "appVersionPresets")
            if pVPresets is not None:

                w_pVersion = QWidget()
                lo_pVersion = QHBoxLayout()

                l_pName = QLabel(i)
                le_pVersion = QLineEdit(pVPresets[0])
                le_pVersion.setMinimumSize(100, 0)
                le_pVersion.setMaximumSize(100, 100)

                if pVersion == 2:
                    bStr = unicode("▼", "utf-8")
                else:
                    bStr = "▼"

                b_pShowVersions = QPushButton(bStr)
                b_pShowVersions.setMaximumSize(25, 100)

                lo_pVersion.addWidget(l_pName)
                lo_pVersion.addStretch()
                lo_pVersion.addWidget(le_pVersion)
                lo_pVersion.addWidget(b_pShowVersions)

                lo_pVersion.setContentsMargins(9, 0, 9, 0)
                w_pVersion.setLayout(lo_pVersion)

                self.w_versions.layout().addWidget(w_pVersion)
                # x = copy.deepcopy(b_pShowVersions)
                self.forceVersionPlugins[i] = {
                    "le": le_pVersion,
                    "b": b_pShowVersions,
                    "presets": pVPresets,
                }

            pAppType = self.core.getPluginData(i, "appType")
            if pAppType != "standalone":
                tab = QWidget()
                w_ovr = QWidget()
                lo_tab = QVBoxLayout()
                lo_ovr = QHBoxLayout()
                tab.setLayout(lo_tab)
                w_ovr.setLayout(lo_ovr)
                lo_tab.setContentsMargins(15, 15, 15, 15)
                lo_ovr.setContentsMargins(0, 9, 0, 9)
                #   w_ovr.setMinimumSize(0,39)

                if self.core.getPluginData(i, "canOverrideExecuteable") != False:
                    l_ovr = QLabel(
                        "By default Prism uses the default application configured in Windows to open scenefiles.\nThe following setting let you override this behaviour by defining explicit applications for opening scenefiles."
                    )
                    chb_ovr = QCheckBox("Executable override")
                    le_ovr = QLineEdit()
                    b_ovr = QPushButton("...")
                    b_ovr.setMinimumWidth(40)
                    b_ovr.setMaximumWidth(40)
                    b_ovr.setContextMenuPolicy(Qt.CustomContextMenu)

                    lo_ovr.addWidget(chb_ovr)
                    lo_ovr.addWidget(le_ovr)
                    lo_ovr.addWidget(b_ovr)

                    lo_tab.addWidget(l_ovr)
                    lo_tab.addWidget(w_ovr)

                    self.exOverridePlugins[i] = {
                        "chb": chb_ovr,
                        "le": le_ovr,
                        "b": b_ovr,
                    }

                gb_integ = QGroupBox("Prism integrations")
                lo_integ = QVBoxLayout()
                gb_integ.setLayout(lo_integ)
                lw_integ = QListWidget()
                w_integ = QWidget()
                lo_integButtons = QHBoxLayout()
                b_addInteg = QPushButton("Add")
                b_removeInteg = QPushButton("Remove")
                examplePath = self.core.getPluginData(i, "examplePath")
                l_examplePath = QLabel("Examplepath:\n\n" + examplePath)

                w_integ.setLayout(lo_integButtons)
                lo_integButtons.addStretch()
                lo_integButtons.addWidget(b_addInteg)
                lo_integButtons.addWidget(b_removeInteg)

                lo_integ.addWidget(lw_integ)
                lo_integ.addWidget(l_examplePath)
                lo_integ.addWidget(w_integ)
                lo_tab.addWidget(gb_integ)

                lw_integ.setSizePolicy(
                    QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                )
                lw_integ.setContextMenuPolicy(Qt.CustomContextMenu)
                lw_integ.customContextMenuRequested.connect(lambda x, y=lw_integ: self.contextMenuIntegration(x, y))

                self.integrationPlugins[i] = {
                    "lw": lw_integ,
                    "badd": b_addInteg,
                    "bremove": b_removeInteg,
                    "lexample": l_examplePath,
                }

                getattr(self.core.getPlugin(i), "prismSettings_loadUI", lambda x, y: None)(self, tab)

                lo_tab.addStretch()
                self.dccTabs.addTab(tab, i)

        if self.dccTabs.count() > 0:
            self.tab_dccApps.layout().addWidget(self.dccTabs)

        self.refreshIntegrations()

        self.tab_dccApps.layout().addStretch()

        self.tw_plugins.setColumnCount(5)
        self.tw_plugins.setHorizontalHeaderLabels(
            ["Active", "Name", "Type", "Version", "Location"]
        )
        self.tw_plugins.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        self.tw_plugins.verticalHeader().setDefaultSectionSize(25)
        self.tw_plugins.horizontalHeader().setStretchLastSection(True)

        if platform.system() in ["Linux", "Darwin"]:
            self.chb_trayStartup.setText(self.chb_trayStartup.text() + " (change requires root permissions)")

        self.core.callback(name="prismSettings_loadUI", types=["custom", "prjManagers"], args=[self])

    @err_catcher(name=__name__)
    def contextMenuIntegration(self, pos, listwidget):
        item = listwidget.itemFromIndex(listwidget.indexAt(pos))
        if not item:
            return

        path = item.text()

        rcmenu = QMenu(self)
        openex = QAction("Open in Explorer", self)
        openex.triggered.connect(lambda: self.core.openFolder(path))
        rcmenu.addAction(openex)

        copAct = QAction("Copy path", self)
        copAct.triggered.connect(lambda: self.core.copyToClipboard(path))
        rcmenu.addAction(copAct)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def refreshIntegrations(self):
        integrations = self.core.integration.getIntegrations()

        for app in self.integrationPlugins:
            self.integrationPlugins[app]["lw"].clear()

            if app in integrations:
                for path in integrations[app]:
                    item = QListWidgetItem(path)
                    self.integrationPlugins[app]["lw"].addItem(item)

                self.integrationPlugins[app]["lw"].setCurrentRow(0)
                self.integrationPlugins[app]["bremove"].setEnabled(True)
            else:
                self.integrationPlugins[app]["bremove"].setEnabled(False)

    @err_catcher(name=__name__)
    def refreshPlugins(self):
        self.tw_plugins.setRowCount(0)
        self.tw_plugins.setSortingEnabled(False)

        plugins = self.core.getLoadedPlugins()
        plugins["inactive"] = self.core.inactivePlugins

        for pType in plugins:
            for pluginName in plugins[pType]:
                activeCheckBox = QCheckBox("")
                if pType == "inactive":
                    version = ""
                    location = ""
                    pluginPath = plugins[pType][pluginName]
                else:
                    activeCheckBox.setChecked(True)
                    version = plugins[pType][pluginName].version
                    location = (plugins[pType][pluginName]
                                .location.replace("prismRoot", "Root")
                                .replace("prismProject", "Project")
                                )
                    pluginPath = plugins[pType][pluginName].pluginPath
                activeCheckBox.toggled.connect(lambda x, y=pluginPath: self.loadPlugins([y], unload=not x))
                activeItem = QTableWidgetItem()
                nameItem = QTableWidgetItem(pluginName)
                typeItem = QTableWidgetItem(pType)
                versionItem = QTableWidgetItem(version)
                locItem = QTableWidgetItem(location)

                activeItem.setData(Qt.UserRole, pluginPath)

                rc = self.tw_plugins.rowCount()
                self.tw_plugins.insertRow(rc)

                self.tw_plugins.setItem(rc, 0, activeItem)
                self.tw_plugins.setItem(rc, 1, nameItem)
                self.tw_plugins.setItem(rc, 2, typeItem)
                self.tw_plugins.setItem(rc, 3, versionItem)
                self.tw_plugins.setItem(rc, 4, locItem)

                self.tw_plugins.setCellWidget(rc, 0, activeCheckBox)

        self.tw_plugins.resizeColumnsToContents()
        self.tw_plugins.setColumnWidth(1, 450)
        self.tw_plugins.setColumnWidth(2, 120)
        self.tw_plugins.setColumnWidth(3, 80)
        self.tw_plugins.setSortingEnabled(True)
        self.tw_plugins.sortByColumn(1, Qt.AscendingOrder)

    @err_catcher(name=__name__)
    def loadPlugins(self, plugins=None, selected=False, unload=False):
        if plugins is None and selected:
            plugins = []
            for i in self.tw_plugins.selectedItems():
                if i.column() != 0:
                    continue

                pluginPath = i.data(Qt.UserRole)
                if pluginPath:
                    plugins.append(pluginPath)

        if not plugins:
            return

        for pluginPath in plugins:
            pluginName = self.core.plugins.getPluginNameFromPath(pluginPath)
            if unload:
                if pluginName == self.core.appPlugin.pluginName:
                    self.core.popup("Cannot unload the currently active app plugin.")
                    if len(plugins) == 1:
                        return
                    else:
                        continue

                self.core.plugins.deactivatePlugin(pluginName)
            else:
                result = self.core.plugins.activatePlugin(pluginPath)
                if not result:
                    self.refreshPlugins()
                    return

        if os.path.exists(self.core.prismIni):
            self.core.changeProject(self.core.prismIni)
        else:
            self.core.prismSettings()

        self.core.ps.tw_settings.setCurrentIndex(5)

    @err_catcher(name=__name__)
    def loadExternalPlugin(self):
        startPath = (
            getattr(self, "externalPluginStartPath", None)
            or self.core.plugins.getPluginPath(location="root")
        )
        selectedPath = QFileDialog.getExistingDirectory(
            self, "Select plugin folder", startPath
        )

        if not selectedPath:
            return

        result = self.core.plugins.loadPlugin(selectedPath, activate=True)
        selectedParent = os.path.dirname(selectedPath)
        if not result:
            self.externalPluginStartPath = selectedParent
            self.core.popup("Couldn't load plugin")
            return

        self.core.plugins.addToPluginConfig(selectedPath)

        if os.path.exists(self.core.prismIni):
            self.core.changeProject(self.core.prismIni)

        self.core.ps.externalPluginStartPath = selectedParent
        self.core.ps.tw_settings.setCurrentIndex(5)

    @err_catcher(name=__name__)
    def reloadPlugins(self, plugins=None, selected=False):
        if plugins is None and selected:
            plugins = []
            for i in self.tw_plugins.selectedItems():
                if i.column() != 0:
                    continue

                pluginPath = i.data(Qt.UserRole)
                if pluginPath:
                    pluginName = self.core.plugins.getPluginNameFromPath(pluginPath)
                    plugins.append(pluginName)

        self.core.reloadPlugins(plugins)

        if os.path.exists(self.core.prismIni):
            self.core.changeProject(self.core.prismIni)
        else:
            self.core.prismSettings()

        self.core.ps.tw_settings.setCurrentIndex(5)

    @err_catcher(name=__name__)
    def createPluginWindow(self):
        dlg_plugin = CreatePluginDialog(self.core)
        action = dlg_plugin.exec_()

        if action == 0:
            return

        pluginName = dlg_plugin.e_name.text()
        pluginType = dlg_plugin.cb_type.currentText()
        pluginLocation = dlg_plugin.cb_location.currentText().lower()
        if pluginLocation == "custom":
            path = dlg_plugin.e_path.text()
        else:
            path = ""

        self.createPlugin(pluginName, pluginType, pluginLocation, path=path)

    @err_catcher(name=__name__)
    def createPlugin(self, pluginName, pluginType, location, path=""):
        pluginPath = self.core.createPlugin(pluginName, pluginType, location=location, path=path)
        self.core.plugins.loadPlugin(pluginPath)
        if pluginType == "Custom":
            self.core.plugins.addToPluginConfig(pluginPath)

        if os.path.exists(self.core.prismIni):
            self.core.changeProject(self.core.prismIni)

        self.core.ps.tw_settings.setCurrentIndex(5)

    @err_catcher(name=__name__)
    def addPluginSearchpath(self):
        startPath = (
            getattr(self, "externalPluginStartPath", None)
            or self.core.plugins.getPluginPath(location="root")
        )
        selectedPath = QFileDialog.getExistingDirectory(
            self, "Select plugin searchpath", startPath
        )

        if not selectedPath:
            return

        self.core.plugins.addToPluginConfig(searchPath=selectedPath)
        result = self.core.plugins.loadPlugins(directory=selectedPath)
        selectedParent = os.path.dirname(selectedPath)
        if not result:
            self.externalPluginStartPath = selectedParent
            self.core.popup("No plugins found in searchpath.")
            return

        if os.path.exists(self.core.prismIni):
            self.core.changeProject(self.core.prismIni)

        self.core.ps.externalPluginStartPath = selectedParent
        self.core.ps.tw_settings.setCurrentIndex(5)

    @err_catcher(name=__name__)
    def openPluginFolder(self):
        for i in self.tw_plugins.selectedItems():
            if i.column() != 0:
                continue

            pluginPath = i.data(Qt.UserRole)
            self.core.openFolder(pluginPath)

    @err_catcher(name=__name__)
    def cmenu_update(self, event):
        rcmenu = QMenu(self)

        act_zip = QAction("Update from .zip", self)
        act_zip.triggered.connect(self.core.updater.updateFromZip)
        rcmenu.addAction(act_zip)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def curPnameEdited(self, text):
        self.validate(self.e_curPname)

    @err_catcher(name=__name__)
    def curPshowList(self, prog):
        versionList = self.forceVersionPlugins[prog]["presets"]

        vmenu = QMenu(self)

        for i in versionList:
            tAct = QAction(i, self)
            tAct.triggered.connect(
                lambda x=None, t=i: self.forceVersionPlugins[prog]["le"].setText(t)
            )
            vmenu.addAction(tAct)

        vmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def checkForUpdates(self):
        self.core.updater.checkForUpdates()
        self.setUpdateStatus()

    @err_catcher(name=__name__)
    def setUpdateStatus(self, status=None, checkTime=None):
        if not status or not checkTime:
            result = self.core.getConfig()
            gblData = result.get("globals", {})

            status = gblData.get("update_status", "")
            checkTime = gblData.get("lastUpdateCheck", "")

        if checkTime:
            checkTime = datetime.datetime.strptime(checkTime, "%Y-%m-%d %H:%M:%S.%f").strftime("%H:%M:%S   %d.%m.%Y")

        if "update available" in status:
            self.l_updateInfo.setStyleSheet("QLabel { color: rgb(250,150,50); }")
            self.b_checkForUpdates.setText("Update")
            self.l_updateInfo.setText(status)
        elif status == "latest version installed":
            self.l_updateInfo.setStyleSheet("QLabel { color: rgb(100,200,100); }")
            self.b_checkForUpdates.setText("Check now")
            self.l_updateInfo.setText("%s - last check %s" % (status, checkTime))
        else:
            self.l_updateInfo.setStyleSheet("")
            self.b_checkForUpdates.setText("Check now")
            self.l_updateInfo.setText("%s - last check %s" % (status, checkTime))

    @err_catcher(name=__name__)
    def changelog(self):
        self.core.updater.showChangelog()

    @err_catcher(name=__name__)
    def startTray(self):
        if platform.system() == "Windows":
            slavePath = os.path.join(self.core.prismRoot, "Scripts", "PrismTray.py")
            pythonPath = os.path.join(self.core.prismLibs, "Python37", "Prism Tray.exe")
            for i in [slavePath, pythonPath]:
                if not os.path.exists(i):
                    msg = "%s does not exist." % os.path.basename(i)
                    self.core.popup(msg, title="Script missing")
                    return None

            command = ["%s" % pythonPath, "%s" % slavePath]
        elif platform.system() == "Linux":
            command = "bash %s/Tools/PrismTray.sh" % self.core.prismLibs
        elif platform.system() == "Darwin":
            command = "bash %s/Tools/PrismTray.sh" % self.core.prismLibs

        subprocess.Popen(command, shell=True)

    @err_catcher(name=__name__)
    def enterEvent(self, event):
        try:
            QApplication.restoreOverrideCursor()
        except:
            pass


class CreatePluginDialog(QDialog):
    def __init__(self, core):
        QDialog.__init__(self)
        self.core = core

        self.setupUi()
        self.connectEvents()
        self.pluginName = ""
        self.refreshPath()

    @err_catcher(name=__name__)
    def setupUi(self):
        self.core.parentWindow(self)
        self.setWindowTitle("Create Plugin")
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.lo_name = QHBoxLayout()
        self.l_name = QLabel("Plugin Name:")
        self.e_name = QLineEdit()
        self.lo_name.addWidget(self.l_name)
        self.lo_name.addWidget(self.e_name)
        self.lo_main.addLayout(self.lo_name)

        self.lo_type = QHBoxLayout()
        self.l_type = QLabel("Type:")
        self.cb_type = QComboBox()
        self.cb_type.addItems(["App", "Renderfarm", "Projectmanager", "Custom"])
        self.cb_type.setCurrentIndex(3)
        self.lo_type.addWidget(self.l_type)
        self.lo_type.addWidget(self.cb_type)
        self.lo_main.addLayout(self.lo_type)

        self.lo_location = QHBoxLayout()
        self.l_location = QLabel("Location:")
        self.cb_location = QComboBox()
        self.cb_location.addItems(["Root", "Project", "Custom"])
        self.lo_location.addWidget(self.l_location)
        self.lo_location.addWidget(self.cb_location)
        self.lo_main.addLayout(self.lo_location)

        self.lo_path = QHBoxLayout()
        self.l_pathInfo = QLabel("Path:")
        self.l_path = QLabel("")
        self.l_path.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        rootPath = self.core.plugins.getPluginPath(location="root", pluginType=self.cb_type.currentText())
        self.e_path = QLineEdit(rootPath)
        self.b_browse = QPushButton("...")
        self.lo_path.addWidget(self.l_pathInfo)
        self.lo_path.addWidget(self.l_path)
        self.lo_path.addWidget(self.e_path)
        self.lo_path.addWidget(self.b_browse)
        self.lo_main.addLayout(self.lo_path)
        self.e_path.setVisible(False)
        self.b_browse.setVisible(False)
        self.b_browse.setContextMenuPolicy(Qt.CustomContextMenu)

        self.lo_main.addStretch()

        self.bb_main = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.bb_main.accepted.connect(self.accept)
        self.bb_main.rejected.connect(self.reject)

        self.lo_main.addWidget(self.bb_main)

        self.resize(500*self.core.uiScaleFactor, 200*self.core.uiScaleFactor)

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.e_name.textChanged.connect(lambda x: self.validate(self.e_name, x))
        self.e_path.textChanged.connect(lambda x: self.validate(self.e_path, x))
        self.cb_type.activated.connect(lambda x: self.refreshPath())
        self.cb_location.activated.connect(lambda x: self.refreshPath())
        self.cb_location.activated[str].connect(lambda x: self.l_path.setVisible(x != "Custom"))
        self.cb_location.activated[str].connect(lambda x: self.e_path.setVisible(x == "Custom"))
        self.cb_location.activated[str].connect(lambda x: self.b_browse.setVisible(x == "Custom"))
        self.b_browse.clicked.connect(self.browse)
        self.b_browse.customContextMenuRequested.connect(
            lambda: self.core.openFolder(self.e_path.text())
        )

    @err_catcher(name=__name__)
    def browse(self):
        windowTitle = "Select plugin location"
        selectedPath = QFileDialog.getExistingDirectory(
            self, windowTitle, self.e_path.text()
        )

        if selectedPath:
            self.e_path.setText(self.core.fixPath(selectedPath))

    @err_catcher(name=__name__)
    def validate(self, uiWidget, origText=None):
        if uiWidget == self.e_name:
            allowChars = ["_"]
        else:
            allowChars = ["/", "\\", "_", " ", ":"]

        self.core.validateLineEdit(uiWidget, allowChars=allowChars)

        if uiWidget == self.e_name:
            self.refreshPath()
            self.pluginName = self.e_name.text()

    @err_catcher(name=__name__)
    def refreshPath(self):
        pluginType = self.cb_type.currentText()
        if self.cb_location.currentText() == "Root":
            path = self.core.plugins.getPluginPath(location="root", pluginType=pluginType)
        elif self.cb_location.currentText() == "Project":
            path = self.core.plugins.getPluginPath(location="project", pluginType=pluginType)
        elif self.cb_location.currentText() == "Custom":
            path = self.e_path.text()
            if os.path.basename(path) == self.pluginName:
                path = os.path.dirname(path)

        name = self.e_name.text()
        fullPath = os.path.join(path, name)
        fullPath = os.path.normpath(fullPath).replace("\\", "/")
        self.l_path.setText(fullPath)


if __name__ == "__main__":
    qapp = QApplication(sys.argv)
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
