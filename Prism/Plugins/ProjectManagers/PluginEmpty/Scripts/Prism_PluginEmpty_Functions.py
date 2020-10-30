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
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_PluginEmpty_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

    @err_catcher(name=__name__)
    def isActive(self):
        return True

    @err_catcher(name=__name__)
    def onProjectChanged(self, origin):
        pass

    @err_catcher(name=__name__)
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

    @err_catcher(name=__name__)
    def prismSettings_prjmanToggled(self, origin, checked):
        origin.w_PluginEmpty.setVisible(checked)

    @err_catcher(name=__name__)
    def pbBrowser_getMenu(self, origin):
        prjman = self.core.getConfig(
            "PluginEmpty", "active", configPath=self.core.prismIni
        )
        if prjman:
            prjmanMenu = QMenu("PluginEmpty", origin)

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

    @err_catcher(name=__name__)
    def createAsset_open(self, origin):
        prjman = self.core.getConfig(
            "PluginEmpty", "active", configPath=self.core.prismIni
        )
        if not prjman:
            return

        origin.chb_createInPluginEmpty = QCheckBox("Create asset in PluginEmpty")
        origin.w_options.layout().insertWidget(0, origin.chb_createInPluginEmpty)
        origin.chb_createInPluginEmpty.setChecked(True)

    @err_catcher(name=__name__)
    def createAsset_typeChanged(self, origin, state):
        if hasattr(origin, "chb_createInPluginEmpty"):
            origin.chb_createInPluginEmpty.setEnabled(state)

    @err_catcher(name=__name__)
    def assetCreated(self, origin, itemDlg, assetPath):
        if (
            hasattr(itemDlg, "chb_createInPluginEmpty")
            and itemDlg.chb_createInPluginEmpty.isChecked()
        ):
            self.createprjmanAssets([assetPath])

    @err_catcher(name=__name__)
    def editShot_open(self, origin, shotName):
        if shotName is None:
            prjman = self.core.getConfig(
                "PluginEmpty", "active", configPath=self.core.prismIni
            )
            if not prjman:
                return

            origin.chb_createInPluginEmpty = QCheckBox("Create shot in PluginEmpty")
            origin.widget.layout().insertWidget(0, origin.chb_createInPluginEmpty)
            origin.chb_createInPluginEmpty.setChecked(True)

    @err_catcher(name=__name__)
    def editShot_closed(self, origin, shotName):
        if (
            hasattr(origin, "chb_createInPluginEmpty")
            and origin.chb_createInPluginEmpty.isChecked()
        ):
            self.createprjmanShots([shotName])

    @err_catcher(name=__name__)
    def pbBrowser_getPublishMenu(self, origin):
        prjman = self.core.getConfig(
            "PluginEmpty", "active", configPath=self.core.prismIni
        )
        if (
            prjman
            and origin.seq
        ):
            prjmanAct = QAction("Publish to PluginEmpty", origin)
            prjmanAct.triggered.connect(lambda: self.prjmanPublish(origin))
            return prjmanAct

    @err_catcher(name=__name__)
    def connectToPluginEmpty(self, user=True):
        pass

    @err_catcher(name=__name__)
    def createprjmanAssets(self, assets=[]):
        pass

    @err_catcher(name=__name__)
    def createprjmanShots(self, shots=[]):
        pass

    @err_catcher(name=__name__)
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

    @err_catcher(name=__name__)
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

    @err_catcher(name=__name__)
    def prjmanAssetsToprjman(self, origin):
        # add code here

        msgString = "No assets were created or updated."

        QMessageBox.information(self.core.messageParent, "PluginEmpty Sync", msgString)

    @err_catcher(name=__name__)
    def prjmanShotsToLocal(self, origin):
        # add code here

        origin.refreshShots()

    @err_catcher(name=__name__)
    def prjmanShotsToprjman(self, origin):
        # add code here

        msgString = "No shots were created or updated."

        QMessageBox.information(self.core.messageParent, "PluginEmpty Sync", msgString)

    @err_catcher(name=__name__)
    def onProjectBrowserClose(self, origin):
        pass

    @err_catcher(name=__name__)
    def onSetProjectStartup(self, origin):
        pass
