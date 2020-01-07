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


import os, sys, traceback, time, subprocess
from functools import wraps

try:
    import hou
except:
    pass

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
    from configparser import ConfigParser

    pVersion = 3
else:
    from ConfigParser import ConfigParser

    pVersion = 2


class Prism_PluginEmpty_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            exc_info = sys.exc_info()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = (
                    "%s ERROR - Prism_Plugin_PluginEmpty - Core: %s - Plugin: %s:\n%s\n\n%s"
                    % (
                        time.strftime("%d/%m/%y %X"),
                        args[0].core.version,
                        args[0].plugin.version,
                        "".join(traceback.format_stack()),
                        traceback.format_exc(),
                    )
                )
                args[0].core.writeErrorLog(erStr)

        return func_wrapper

    @err_decorator
    def isActive(self):
        if pVersion == 2:
            return True

        return False

    @err_decorator
    def onProjectChanged(self, origin):
        pass

    @err_decorator
    def prismSettings_loadUI(self, origin):
        origin.gb_prjmanPrjIntegration = QGroupBox("PluginEmpty integration")
        origin.w_PluginEmpty = QWidget()
        lo_prjmanI = QHBoxLayout()
        lo_prjmanI.addWidget(origin.w_PluginEmpty)
        origin.gb_prjmanPrjIntegration.setLayout(lo_prjmanI)
        origin.gb_prjmanPrjIntegration.setCheckable(True)
        origin.gb_prjmanPrjIntegration.setChecked(False)

        lo_prjman = QGridLayout()
        origin.w_PluginEmpty.setLayout(lo_prjman)

        origin.l_prjmanSite = QLabel("PluginEmpty site:")
        origin.l_prjmanPrjName = QLabel("Project Name:")
        origin.l_prjmanScriptName = QLabel("Script Name:")
        origin.l_prjmanApiKey = QLabel("Script API key:")
        origin.e_prjmanSite = QLineEdit()
        origin.e_prjmanPrjName = QLineEdit()
        origin.e_prjmanScriptName = QLineEdit()
        origin.e_prjmanApiKey = QLineEdit()

        lo_prjman.addWidget(origin.l_prjmanSite)
        lo_prjman.addWidget(origin.l_prjmanPrjName)
        lo_prjman.addWidget(origin.l_prjmanScriptName)
        lo_prjman.addWidget(origin.l_prjmanApiKey)
        lo_prjman.addWidget(origin.e_prjmanSite, 0, 1)
        lo_prjman.addWidget(origin.e_prjmanPrjName, 1, 1)
        lo_prjman.addWidget(origin.e_prjmanScriptName, 2, 1)
        lo_prjman.addWidget(origin.e_prjmanApiKey, 3, 1)

        origin.w_prjSettings.layout().insertWidget(5, origin.gb_prjmanPrjIntegration)
        origin.groupboxes.append(origin.gb_prjmanPrjIntegration)

        origin.gb_prjmanPrjIntegration.toggled.connect(
            lambda x: self.prismSettings_prjmanToggled(origin, x)
        )

    @err_decorator
    def prismSettings_loadSettings(self, origin):
        loadData = {}
        loadFunctions = {}

        return loadData, loadFunctions

    @err_decorator
    def prismSettings_loadPrjSettings(self, origin):
        loadData = {}
        loadFunctions = {}

        loadData["prjmanActive"] = ["PluginEmpty", "active", "bool"]
        loadFunctions[
            "prjmanActive"
        ] = lambda x: origin.gb_prjmanPrjIntegration.setChecked(x)

        loadData["prjmanSite"] = ["PluginEmpty", "site"]
        loadFunctions["prjmanSite"] = lambda x: origin.e_prjmanSite.setText(x)

        loadData["prjmanPrjName"] = ["PluginEmpty", "projectname"]
        loadFunctions["prjmanPrjName"] = lambda x: origin.e_prjmanPrjName.setText(x)

        loadData["prjmanScriptName"] = ["PluginEmpty", "scriptname"]
        loadFunctions["prjmanScriptName"] = lambda x: origin.e_prjmanScriptName.setText(
            x
        )

        loadData["prjmanApiKey"] = ["PluginEmpty", "apikey"]
        loadFunctions["prjmanApiKey"] = lambda x: origin.e_prjmanApiKey.setText(x)

        return loadData, loadFunctions

    @err_decorator
    def prismSettings_postLoadSettings(self, origin):
        self.prismSettings_prjmanToggled(
            origin, origin.gb_prjmanPrjIntegration.isChecked()
        )

    @err_decorator
    def prismSettings_saveSettings(self, origin):
        saveData = []

        return saveData

    @err_decorator
    def prismSettings_savePrjSettings(self, origin):
        saveData = []

        saveData.append(
            ["PluginEmpty", "active", str(origin.gb_prjmanPrjIntegration.isChecked())]
        )
        saveData.append(["PluginEmpty", "site", str(origin.e_prjmanSite.text())])
        saveData.append(
            ["PluginEmpty", "projectname", str(origin.e_prjmanPrjName.text())]
        )
        saveData.append(
            ["PluginEmpty", "scriptname", str(origin.e_prjmanScriptName.text())]
        )
        saveData.append(["PluginEmpty", "apikey", str(origin.e_prjmanApiKey.text())])

        return saveData

    @err_decorator
    def prismSettings_prjmanToggled(self, origin, checked):
        origin.w_PluginEmpty.setVisible(checked)

    @err_decorator
    def pbBrowser_getMenu(self, origin):
        prjman = self.core.getConfig(
            "PluginEmpty", "active", configPath=self.core.prismIni
        )
        if prjman is not None and eval(prjman) and pVersion == 2:
            prjmanMenu = QMenu("PluginEmpty")

            actprjman = QAction("Open PluginEmpty", origin)
            actprjman.triggered.connect(self.openprjman)
            prjmanMenu.addAction(actprjman)

            prjmanMenu.addSeparator()

            actSSL = QAction("PluginEmpty assets to local", origin)
            actSSL.triggered.connect(lambda: self.prjmanAssetsToLocal(origin))
            prjmanMenu.addAction(actSSL)

            actSSL = QAction("Local assets to PluginEmpty", origin)
            actSSL.triggered.connect(lambda: self.prjmanAssetsToprjman(origin))
            prjmanMenu.addAction(actSSL)

            prjmanMenu.addSeparator()

            actSSL = QAction("PluginEmpty shots to local", origin)
            actSSL.triggered.connect(lambda: self.prjmanShotsToLocal(origin))
            prjmanMenu.addAction(actSSL)

            actLSS = QAction("Local shots to PluginEmpty", origin)
            actLSS.triggered.connect(lambda: self.prjmanShotsToprjman(origin))
            prjmanMenu.addAction(actLSS)

            return prjmanMenu

    @err_decorator
    def pbBrowser_getAssetMenu(self, origin, assetname, assetPath):
        prjman = self.core.getConfig(
            "PluginEmpty", "active", configPath=self.core.prismIni
        )
        if prjman is not None and eval(prjman) and pVersion == 2:
            prjmanAct = QAction("Open in PluginEmpty", origin)
            prjmanAct.triggered.connect(
                lambda: self.openprjman(assetname, eType="Asset", assetPath=assetPath)
            )
            return prjmanAct

    @err_decorator
    def pbBrowser_getShotMenu(self, origin, shotname):
        prjman = self.core.getConfig(
            "PluginEmpty", "active", configPath=self.core.prismIni
        )
        if prjman is not None and eval(prjman) and pVersion == 2:
            prjmanAct = QAction("Open in PluginEmpty", origin)
            prjmanAct.triggered.connect(lambda: self.openprjman(shotname))
            return prjmanAct

    @err_decorator
    def createAsset_open(self, origin):
        prjman = self.core.getConfig(
            "PluginEmpty", "active", configPath=self.core.prismIni
        )
        if prjman is None or not eval(prjman) or pVersion != 2:
            return

        origin.chb_createInPluginEmpty = QCheckBox("Create asset in PluginEmpty")
        origin.w_options.layout().insertWidget(0, origin.chb_createInPluginEmpty)
        origin.chb_createInPluginEmpty.setChecked(True)

    @err_decorator
    def createAsset_typeChanged(self, origin, state):
        if hasattr(origin, "chb_createInPluginEmpty"):
            origin.chb_createInPluginEmpty.setEnabled(state)

    @err_decorator
    def assetCreated(self, origin, itemDlg, assetPath):
        if (
            hasattr(itemDlg, "chb_createInPluginEmpty")
            and itemDlg.chb_createInPluginEmpty.isChecked()
        ):
            self.createprjmanAssets([assetPath])

    @err_decorator
    def editShot_open(self, origin, shotName):
        if shotName is None:
            prjman = self.core.getConfig(
                "PluginEmpty", "active", configPath=self.core.prismIni
            )
            if prjman is None or not eval(prjman) or pVersion != 2:
                return

            origin.chb_createInPluginEmpty = QCheckBox("Create shot in PluginEmpty")
            origin.widget.layout().insertWidget(0, origin.chb_createInPluginEmpty)
            origin.chb_createInPluginEmpty.setChecked(True)

    @err_decorator
    def editShot_closed(self, origin, shotName):
        if (
            hasattr(origin, "chb_createInPluginEmpty")
            and origin.chb_createInPluginEmpty.isChecked()
        ):
            self.createprjmanShots([shotName])

    @err_decorator
    def pbBrowser_getPublishMenu(self, origin):
        prjman = self.core.getConfig(
            "PluginEmpty", "active", configPath=self.core.prismIni
        )
        if (
            prjman is not None
            and eval(prjman)
            and len(origin.seq) > 0
            and pVersion == 2
        ):
            prjmanAct = QAction("Publish to PluginEmpty", origin)
            prjmanAct.triggered.connect(lambda: self.prjmanPublish(origin))
            return prjmanAct

    @err_decorator
    def connectToPluginEmpty(self, user=True):
        pass

    @err_decorator
    def createprjmanAssets(self, assets=[]):
        pass

    @err_decorator
    def createprjmanShots(self, shots=[]):
        pass

    @err_decorator
    def prjmanPublish(self, origin):
        if origin.tbw_browser.currentWidget().property("tabType") == "Assets":
            pType = "Asset"
        else:
            pType = "Shot"

        shotName = os.path.basename(origin.renderBasePath)

        taskName = (
            origin.curRTask.replace(" (playblast)", "")
            .replace(" (2d)", "")
            .replace(" (external)", "")
        )
        versionName = origin.curRVersion.replace(" (local)", "")
        mpb = origin.mediaPlaybacks["shots"]

        imgPaths = []
        if mpb["prvIsSequence"] or len(mpb["seq"]) == 1:
            if os.path.splitext(mpb["seq"][0])[1] in [".mp4", ".mov"]:
                imgPaths.append(
                    [os.path.join(mpb["basePath"], mpb["seq"][0]), mpb["curImg"]]
                )
            else:
                imgPaths.append(
                    [os.path.join(mpb["basePath"], mpb["seq"][mpb["curImg"]]), 0]
                )
        else:
            for i in mpb["seq"]:
                imgPaths.append([os.path.join(mpb["basePath"], i), 0])

        if "pstart" in mpb:
            sf = mpb["pstart"]
        else:
            sf = 0

        # do publish here

    def openprjman(self, shotName=None, eType="Shot", assetPath=""):
        prjmanSite = "https://prism-pipeline.com"

        import webbrowser

        webbrowser.open(prjmanSite)

    @err_decorator
    def prjmanAssetsToLocal(self, origin):
        # add code here

        createdAssets = []
        if len(createdAssets) > 0:
            msgString = "The following assets were created:\n\n"

            createdAssets.sort()

            for i in createdAssets:
                msgString += i + "\n"
        else:
            msgString = "No assets were created."

        QMessageBox.information(self.core.messageParent, "PluginEmpty Sync", msgString)

        origin.refreshAHierarchy()

    @err_decorator
    def prjmanAssetsToprjman(self, origin):
        # add code here

        msgString = "No assets were created or updated."

        QMessageBox.information(self.core.messageParent, "PluginEmpty Sync", msgString)

    @err_decorator
    def prjmanShotsToLocal(self, origin):
        # add code here

        origin.refreshShots()

    @err_decorator
    def prjmanShotsToprjman(self, origin):
        # add code here

        msgString = "No shots were created or updated."

        QMessageBox.information(self.core.messageParent, "PluginEmpty Sync", msgString)
