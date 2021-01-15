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
import logging

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *
    psVersion = 1

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

        return (not self.core.restartRequired)

    @err_catcher(name=__name__)
    def checkImportVersions(self):
        checkImpVersions = self.core.getConfig("globals", "check_import_versions")
        if checkImpVersions is None:
            self.core.setConfig("globals", "check_import_versions", True)
            checkImpVersions = True

        if not checkImpVersions:
            return

        if not getattr(self.core, "projectPath", None) or not os.path.exists(self.core.prismIni):
            return

        paths = self.core.appPlugin.getImportPaths(self.core)

        if not paths:
            return

        paths = eval(paths.replace("\\", "/"))
        paths = [[self.core.fixPath(str(x[0])), self.core.fixPath(str(x[1]))] for x in paths]

        if len(paths) == 0:
            return

        msgString = "For the following imports there is a newer version available:\n\n"
        updates = 0

        for i in paths:
            if not os.path.exists(os.path.dirname(i[0])):
                continue

            versionData = (
                os.path.dirname(os.path.dirname(i[0]))
                .rsplit(os.sep, 1)[1]
                .split(self.core.filenameSeparator)
            )

            if (
                len(versionData) != 3
                or not self.core.core.getScenePath().replace(self.core.projectPath, "")
                in i[0]
            ):
                continue

            curVersion = (
                versionData[0]
                + self.core.filenameSeparator
                + versionData[1]
                + self.core.filenameSeparator
                + versionData[2]
            )
            latestVersion = None
            for m in os.walk(os.path.dirname(os.path.dirname(os.path.dirname(i[0])))):
                folders = m[1]
                folders.sort()
                for k in reversed(folders):
                    if (
                        len(k.split(self.core.filenameSeparator)) == 3
                        and k[0] == "v"
                        and len(k.split(self.core.filenameSeparator)[0]) == 5
                        and len(os.listdir(os.path.join(m[0], k))) > 0
                    ):
                        latestVersion = k
                        break
                break

            if latestVersion is None or curVersion == latestVersion:
                continue

            msgString += "%s\n    current: %s\n    latest: %s\n\n" % (
                i[1],
                curVersion,
                latestVersion,
            )
            updates += 1

        msgString += "Please update the imports in the State Manager."

        if updates > 0:
            if self.core.uiAvailable:
                QMessageBox.information(self.core.messageParent, "State updates", msgString)

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

        fileName = self.core.getCurrentFileName()

        fnameData = self.core.getScenefileData(fileName)
        if fnameData["entity"] != "shot":
            return

        shotName = fnameData["entityName"]
        shotRange = self.core.getConfig("shotRanges", shotName, config="shotinfo")

        if (
            self.core.core.getScenePath() not in fileName
            and (
                self.core.useLocalFiles
                and self.core.core.getScenePath(location="local") not in fileName
            )
        ):
            return

        if not isinstance(shotRange, list) or len(shotRange) != 2:
            return

        curRange = self.core.appPlugin.getFrameRange(self.core)

        if int(curRange[0]) == shotRange[0] and int(curRange[1]) == shotRange[1]:
            return

        msgString = (
            "The framerange of the current scene doesn't match the framerange of the shot:\n\nFramerange of current scene:\n%s - %s\n\nFramerange of shot %s:\n%s - %s"
            % (int(curRange[0]), int(curRange[1]), shotName, shotRange[0], shotRange[1])
        )

        if self.core.forceFramerange:
            self.core.setFrameRange(shotRange[0], shotRange[1])
        else:
            result = self.core.popupQuestion(msgString, title="Framerange mismatch", buttons=["Set shotrange in scene", "Skip"], escapeButton="Skip")
            if result == "Set shotrange in scene":
                self.core.setFrameRange(shotRange[0], shotRange[1])

    @err_catcher(name=__name__)
    def checkFPS(self):
        forceFPS = self.core.getConfig("globals", "forcefps", configPath=self.core.prismIni)
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

        if pFps == curFps:
            return

        vInfo = [["FPS of current scene:", str(curFps)], ["FPS of project", str(pFps)]]
        lay_info = QGridLayout()

        msgString = (
            "The FPS of the current scene doesn't match the FPS of the project:"
        )

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

        result = self.core.popupQuestion(msgString, title="FPS mismatch", buttons=["Set project FPS in current scene", "Skip"], widget=w_info)

        if result == "Set project FPS in current scene":
            self.core.appPlugin.setFPS(self.core, float(pFps))

    @err_catcher(name=__name__)
    def checkResolution(self):
        forceRes = self.core.getConfig("globals", "forceResolution", configPath=self.core.prismIni)
        if not forceRes:
            return

        if not self.core.fileInPipeline():
            return

        pRes = self.core.getConfig("globals", "resolution", configPath=self.core.prismIni)

        if not pRes:
            return

        curRes = self.core.getResolution()
        if not curRes:
            return

        if list(pRes) == curRes:
            return

        vInfo = [["Resolution of current scene:", "%s x %s" % (curRes[0], curRes[1])], ["Resolution of project", "%s x %s" % (pRes[0], pRes[1])]]
        lay_info = QGridLayout()
        msgString = (
            "The resolution of the current scene doesn't match the resolution of the project:"
        )

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

        result = self.core.popupQuestion(msgString, title="Resolution mismatch", buttons=["Set project resolution in current scene", "Skip"], widget=w_info)

        if result == "Set project resolution in current scene":
            self.core.appPlugin.setResolution(*pRes)

    @err_catcher(name=__name__)
    def checkAppVersion(self):
        fversion = self.core.getConfig("globals", "forceversions", configPath=self.core.prismIni)
        if (
            not fversion
            or self.core.appPlugin.appType == "standalone"
        ):
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
            msgStr = "You use a different %s version, than configured in your \
current project.\n\nYour current version: %s\nVersion configured in project: %s\n\nPlease use the required %s version to avoid incompatibility problems." % (
                self.core.appPlugin.pluginName,
                curVersion,
                rversion,
                self.core.appPlugin.pluginName,
            ),
            self.core.popup(msgStr)
