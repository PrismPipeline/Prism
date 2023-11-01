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
import logging

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class SanityChecks(object):
    def __init__(self, core):
        self.core = core
        self.checksToRun = {
            "onOpenProjectBrowser": [
                {"name": "restartRequired", "function": self.checkRestartRequired}
            ],
            "onOpenStateManager": [
                {"name": "restartRequired", "function": self.checkRestartRequired}
            ],
        }

    @err_catcher(name=__name__)
    def runChecks(self, category, quiet=False):
        result = {"passed": True, "checks": []}
        if category not in self.checksToRun:
            return result

        for check in self.checksToRun[category]:
            checkResult = check["function"](quiet=quiet)
            if not checkResult:
                result["passed"] = False

            checkData = {"name": check["name"], "passed": checkResult}
            result["checks"].append(checkData)

        return result

    @err_catcher(name=__name__)
    def checkRestartRequired(self, quiet=False):
        if self.core.restartRequired and not quiet:
            appName = self.core.appPlugin.pluginName
            if appName == "Standalone":
                appName = "Prism"
            self.core.popup("Please restart %s to use this feature." % appName)

        return not self.core.restartRequired

    @err_catcher(name=__name__)
    def checkImportVersions(self):
        checkImpVersions = self.core.getConfig("globals", "check_import_versions")
        if checkImpVersions is None:
            self.core.setConfig("globals", "check_import_versions", True)
            checkImpVersions = True

        if not checkImpVersions:
            return

        if not getattr(self.core, "projectPath", None) or not os.path.exists(
            self.core.prismIni
        ):
            return

        paths = getattr(self.core.appPlugin, "getImportPaths", lambda x: None)(
            self.core
        )

        if not paths:
            return

        paths = eval(paths.replace("\\", "/"))
        paths = [
            [self.core.fixPath(str(x[0])), self.core.fixPath(str(x[1]))] for x in paths
        ]

        if len(paths) == 0:
            return

        msgString = "For the following imports there is a newer version available:\n\n"
        updates = 0
        for pathData in paths:
            path = pathData[0]
            if not os.path.exists(os.path.dirname(path)):
                continue

            entityType = self.core.paths.getEntityTypeFromPath(path)
            if not entityType:
                continue

            curVersion = self.core.products.getProductDataFromFilepath(path)
            if not curVersion or "version" not in curVersion:
                continue

            latestVersion = self.core.products.getLatestVersionFromPath(path, includeMaster=self.core.products.getUseMaster())

            if not latestVersion or curVersion["version"] == latestVersion["version"]:
                continue

            msgString += "%s\n    current: %s\n    latest: %s\n\n" % (
                pathData[1],
                curVersion["version"],
                latestVersion["version"],
            )
            updates += 1

        msgString += "Please update the imports in the State Manager."

        if updates > 0:
            msg = self.core.popupQuestion(
                msgString,
                title="New versions available",
                buttons=["Update all", "Open State Manager", "Skip"],
                escapeButton="Skip",
                default="Skip",
                doExec=False,
            )
            if not self.core.isStr(msg):
                msg.buttonClicked.connect(self.onImportVersionsClicked)
                msg.show()

    @err_catcher(name=__name__)
    def onImportVersionsClicked(self, button):
        result = button.text()
        if result == "Update all":
            sm = self.core.getStateManager()
            sm.updateAllImportStates()

        elif result == "Open State Manager":
            sm = self.core.stateManager()
            sm.gb_import.setChecked(True)

    @err_catcher(name=__name__)
    def checkFramerange(self):
        if not getattr(self.core.appPlugin, "hasFrameRange", True):
            return

        checkRange = self.core.getConfig("globals", "checkframeranges")
        if checkRange is None:
            self.core.setConfig("globals", "checkframeranges", True)
            checkRange = True

        if not checkRange:
            return

        if not hasattr(self.core, "projectPath"):
            return

        fileName = self.core.getCurrentFileName()

        fnameData = self.core.getScenefileData(fileName)
        if fnameData.get("type") != "shot":
            return

        if not self.core.fileInPipeline(fileName):
            return

        if "shot" not in fnameData or "sequence" not in fnameData:
            return

        if fnameData["shot"] == "_sequence":
            return

        shotRange = self.core.entities.getShotRange(fnameData)
        if not isinstance(shotRange, list) or len(shotRange) != 2 or shotRange[0] in [None, ""] or shotRange[1] in [None, ""]:
            return

        curRange = self.core.appPlugin.getFrameRange(self.core)
        if int(curRange[0]) == int(shotRange[0]) and int(curRange[1]) == int(shotRange[1]):
            return

        shotName = self.core.entities.getShotName(fnameData)
        msgString = (
            "The framerange of the current scene doesn't match the framerange of the shot:\n\nFramerange of current scene:\n%s - %s\n\nFramerange of shot %s:\n%s - %s"
            % (int(curRange[0]), int(curRange[1]), shotName, shotRange[0], shotRange[1])
        )

        if self.core.forceFramerange:
            self.core.setFrameRange(int(shotRange[0]), int(shotRange[1]))
        else:
            msg = self.core.popupQuestion(
                msgString,
                title="Framerange mismatch",
                buttons=["Set shotrange in scene", "Skip"],
                escapeButton="Skip",
                default="Skip",
                doExec=False,
            )
            if not self.core.isStr(msg):
                msg.buttonClicked.connect(lambda x: self.onCheckFramerangeClicked(x, shotRange))
                msg.show()

    @err_catcher(name=__name__)
    def onCheckFramerangeClicked(self, button, shotRange):
        result = button.text()
        if result == "Set shotrange in scene":
            self.core.setFrameRange(int(shotRange[0]), int(shotRange[1]))

    @err_catcher(name=__name__)
    def checkFPS(self):
        forceFPS = self.core.getConfig(
            "globals", "forcefps", configPath=self.core.prismIni
        )
        if not forceFPS:
            return

        if not getattr(self.core.appPlugin, "hasFrameRange", True):
            return

        if not self.core.fileInPipeline():
            return

        pFps = self.core.getConfig("globals", "fps", configPath=self.core.prismIni)

        if pFps is None:
            return

        pFps = float(pFps)

        curFps = self.core.getFPS()

        if pFps == curFps or curFps is None:
            return

        vInfo = [["FPS of current scene:", str(curFps)], ["FPS of project", str(pFps)]]
        lay_info = QGridLayout()

        msgString = "The FPS of the current scene doesn't match the FPS of the project:"

        for idx, val in enumerate(vInfo):
            l_infoName = QLabel(val[0] + ":\t")
            l_info = QLabel(val[1])
            lay_info.addWidget(l_infoName)
            lay_info.addWidget(l_info, idx, 1)

        lay_info.addItem(
            QSpacerItem(10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )
        lay_info.addItem(
            QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum), 0, 2
        )

        lay_info.setContentsMargins(10, 10, 10, 10)
        w_info = QWidget()
        w_info.setLayout(lay_info)

        msg = self.core.popupQuestion(
            msgString,
            title="FPS mismatch",
            buttons=["Set project FPS in current scene", "Skip"],
            widget=w_info,
            escapeButton="Skip",
            default="Skip",
            doExec=False,
        )
        if not self.core.isStr(msg):
            msg.buttonClicked.connect(lambda x: self.onCheckFpsClicked(x, pFps))
            msg.show()

    @err_catcher(name=__name__)
    def onCheckFpsClicked(self, button, projectFps):
        result = button.text()
        if result == "Set project FPS in current scene":
            self.core.appPlugin.setFPS(self.core, float(projectFps))

    @err_catcher(name=__name__)
    def checkResolution(self):
        forceRes = self.core.getConfig(
            "globals", "forceResolution", configPath=self.core.prismIni
        )
        if not forceRes:
            return

        if not self.core.fileInPipeline():
            return

        pRes = self.core.getConfig(
            "globals", "resolution", configPath=self.core.prismIni
        )

        if not pRes:
            return

        curRes = self.core.getResolution()
        if not curRes:
            return

        if list(pRes) == curRes:
            return

        vInfo = [
            ["Resolution of current scene:", "%s x %s" % (curRes[0], curRes[1])],
            ["Resolution of project", "%s x %s" % (pRes[0], pRes[1])],
        ]
        lay_info = QGridLayout()
        msgString = "The resolution of the current scene doesn't match the resolution of the project:"

        for idx, val in enumerate(vInfo):
            l_infoName = QLabel(val[0] + ":\t")
            l_info = QLabel(val[1])
            lay_info.addWidget(l_infoName)
            lay_info.addWidget(l_info, idx, 1)

        lay_info.addItem(
            QSpacerItem(10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )
        lay_info.addItem(
            QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum), 0, 2
        )

        lay_info.setContentsMargins(10, 10, 10, 10)
        w_info = QWidget()
        w_info.setLayout(lay_info)

        msg = self.core.popupQuestion(
            msgString,
            title="Resolution mismatch",
            buttons=["Set project resolution in current scene", "Skip"],
            widget=w_info,
            escapeButton="Skip",
            default="Skip",
            doExec=False,
        )
        if not self.core.isStr(msg):
            msg.buttonClicked.connect(lambda x: self.onCheckResolutionClicked(x, pRes))
            msg.show()

    @err_catcher(name=__name__)
    def onCheckResolutionClicked(self, button, projectResolution):
        result = button.text()
        if result == "Set project resolution in current scene":
            self.core.appPlugin.setResolution(*projectResolution)

    @err_catcher(name=__name__)
    def checkAppVersion(self):
        fversion = self.core.getConfig(
            "globals", "forceversions", configPath=self.core.prismIni
        )
        if not fversion or self.core.appPlugin.appType == "standalone":
            return

        rversion = self.core.getConfig(
            "globals",
            "%s_version" % self.core.appPlugin.pluginName,
            configPath=self.core.prismIni,
        )
        if rversion is None or rversion == "":
            return

        curVersion = self.core.appPlugin.getAppVersion(self.core)

        if curVersion != rversion:
            msgStr = (
                "You use a different %s version, than configured in your \
current project.\n\nYour current version: %s\nVersion configured in project: %s\n\nPlease use the required %s version to avoid incompatibility problems."
                % (
                    self.core.appPlugin.pluginName,
                    curVersion,
                    rversion,
                    self.core.appPlugin.pluginName,
                ),
            )
            self.core.popup(msgStr)
