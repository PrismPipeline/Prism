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


from __future__ import annotations

import os
import logging
from typing import Optional, Dict, List, Any, Union, Callable

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class SanityChecks(object):
    """Performs sanity checks and validations for project and scene states.
    
    This class runs various checks when opening projects or scenes to ensure
    consistency with project settings. Checks include framerate, resolution,
    framerange, import versions, and restart requirements.
    
    Attributes:
        core: PrismCore instance
        checksToRun (Dict): Dictionary of check categories and their checks
    
    Example:
        ```python
        checks = SanityChecks(core)
        result = checks.runChecks("onSceneOpen")
        if not result["passed"]:
            print("Some checks failed")
        ```
    """

    def __init__(self, core: Any) -> None:
        """Initialize SanityChecks manager.
        
        Args:
            core: PrismCore instance
        """
        self.core = core
        self._notificationQueue = None
        self.dlg_sanityNotifications = None
        self.checksToRun = {
            "onOpenProjectBrowser": {
                "enabled": True,
                "checks": [
                    {"name": "restartRequired", "function": self.checkRestartRequired}
                ],
            },
            "onOpenStateManager": {
                "enabled": True,
                "checks": [
                    {"name": "restartRequired", "function": self.checkRestartRequired}
                ],
            },
            "onSceneOpen": {
                "enabled": True,
                "checks": [
                    {"name": "checkImportVersions", "function": self.checkImportVersions},
                    {"name": "checkFramerange", "function": self.checkFramerange},
                    {"name": "checkFPS", "function": self.checkFPS},
                    {"name": "checkResolution", "function": self.checkResolution},
                    {
                        "name": "checkSceneBuildingUpdates",
                        "function": self.checkSceneBuildingUpdates,
                    },
                ]
            }
        }

    @err_catcher(name=__name__)
    def runChecks(self, category: str, settings: Optional[Dict] = None) -> Dict[str, Any]:
        """Run all checks for a given category.
        
        Args:
            category: Check category (e.g., "onSceneOpen", "onOpenProjectBrowser")
            settings: Optional settings dictionary. Defaults to None.
            
        Returns:
            Dictionary with 'passed' boolean and list of 'checks' results
        """
        settings = settings or {}
        result = {"passed": True, "checks": []}
        if category not in self.checksToRun:
            return result

        if not self.checksToRun[category].get("enabled", True):
            return result

        if category == "onSceneOpen" and not settings.get("accept", False):
            self._notificationQueue = []

        for check in self.checksToRun[category]["checks"]:
            checkResult = check["function"](settings=settings)
            if not checkResult:
                result["passed"] = False

            checkData = {"name": check["name"], "passed": checkResult}
            result["checks"].append(checkData)

        if category == "onSceneOpen":
            self.showQueuedNotifications()

        return result

    @err_catcher(name=__name__)
    def queueOrShowNotification(
        self,
        text: str,
        title: str,
        buttons: List[str],
        default: Optional[str] = None,
        escapeButton: Optional[str] = None,
        widget: Optional[QWidget] = None,
        callback: Optional[Callable[[Any], None]] = None,
    ) -> Optional[Any]:
        """Queue a notification for stacked display or show it immediately.

        Args:
            title: Dialog title.
            text: Message text.
            buttons: Action button labels.
            default: Optional default button label.
            escapeButton: Optional escape button label.
            widget: Optional extra widget to display in the notification.
            callback: Optional callback for clicked button.

        Returns:
            QMessageBox-like dialog when shown immediately, otherwise None.
        """
        notification = {
            "text": text,
            "title": title,
            "buttons": buttons,
            "default": default,
            "escapeButton": escapeButton,
            "widget": widget,
            "callback": callback,
        }

        if self._notificationQueue is not None:
            self._notificationQueue.append(notification)
            return None

        return self.showImmediateNotification(notification)

    @err_catcher(name=__name__)
    def showImmediateNotification(self, notification: Dict[str, Any]) -> Optional[Any]:
        """Show a single notification popup directly.

        Args:
            notification: Notification descriptor.

        Returns:
            Dialog object when shown, otherwise None.
        """
        msg = self.core.popupQuestion(
            notification.get("text", ""),
            title=notification.get("title", "Prism"),
            buttons=notification.get("buttons") or ["Ok"],
            escapeButton=notification.get("escapeButton"),
            default=notification.get("default"),
            widget=notification.get("widget"),
            doExec=False,
        )
        if self.core.isStr(msg):
            return None

        callback = notification.get("callback")
        if callback:
            msg.buttonClicked.connect(callback)

        msg.show()
        return msg

    @err_catcher(name=__name__)
    def showQueuedNotifications(self) -> None:
        """Show queued scene-open sanity notifications as one stacked dialog."""
        notifications = self._notificationQueue or []
        self._notificationQueue = None
        if not notifications:
            return

        qapp = QApplication.instance()
        isGuiThread = qapp and qapp.thread() == QThread.currentThread()
        if "silent" in self.core.prismArgs or not self.core.uiAvailable or not isGuiThread:
            return

        from PrismUtils import ProjectWidgets

        if (
            getattr(self, "dlg_sanityNotifications", None)
            and self.core.isObjectValid(self.dlg_sanityNotifications)
            and self.dlg_sanityNotifications.isVisible()
        ):
            self.dlg_sanityNotifications.close()

        self.dlg_sanityNotifications = ProjectWidgets.SanityNotificationsDialog(
            self.core,
            notifications=notifications,
            parent=getattr(self.core, "messageParent", None),
        )
        self.dlg_sanityNotifications.setModal(False)
        self.dlg_sanityNotifications.show()

    @err_catcher(name=__name__)
    def checkRestartRequired(self, settings: Optional[Dict] = None) -> bool:
        """Check if Prism restart is required.
        
        Args:
            settings: Optional settings with 'quiet' key. Defaults to None.
            
        Returns:
            True if check passed or restart not required, False otherwise
        """
        quiet = (settings or {}).get("quiet", False)
        if self.core.restartRequired and not quiet:
            appName = self.core.appPlugin.pluginName
            if appName == "Standalone":
                appName = "Prism"
            self.core.popup("Please restart %s to use this feature." % appName)

        return not self.core.restartRequired

    @err_catcher(name=__name__)
    def checkImportVersions(self, settings: Optional[Dict[str, Any]] = None) -> None:
        """Check if imported products have newer versions available.
        
        Shows popup if updates are available for State Manager imports.
        
        Args:
            settings: Optional dict with 'accept' and 'value' keys for automation
        """
        settings = settings or {}
        checkImpVersions = self.core.getConfig("globals", "check_import_versions")
        if checkImpVersions is None:
            self.core.setConfig("globals", "check_import_versions", True)
            checkImpVersions = True

        if not checkImpVersions and not settings.get("showSuccess", False):
            return

        if not getattr(self.core, "projectPath", None) or not os.path.exists(
            self.core.prismIni
        ):
            return

        paths = getattr(self.core.appPlugin, "getImportPaths", lambda x: None)(
            self.core
        ) or []
        if not paths and not settings.get("showSuccess", False):
            return

        if isinstance(paths, str):
            paths = eval(paths.replace("\\", "/"))

        paths = [
            [self.core.fixPath(str(x[0])), self.core.fixPath(str(x[1])), x[2] if len(x) > 2 else False] for x in paths
        ]
        if len(paths) == 0 and not settings.get("showSuccess", False):
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

            curVersionName = self.core.products.getVersionFromFilepath(path) or ""
            if not curVersionName:
                curVersionName = self.core.paths.getCachePathData(path).get("version")
                if curVersionName and os.path.basename(os.path.dirname(path)) == "master":
                    curVersionName = "master"

            ignoreMaster = pathData[2] if len(pathData) > 2 else False
            includeMaster = self.core.products.getUseMaster() and not ignoreMaster
            latestVersion = self.core.products.getLatestVersionFromPath(path, includeMaster=includeMaster)
            if not latestVersion or curVersionName == latestVersion["version"]:
                continue

            latestVersionName = latestVersion["version"]
            if curVersionName == "master":
                curVersionName = self.core.products.getMasterVersionLabel(path)

            if latestVersionName == "master":
                latestVersionName = self.core.products.getMasterVersionLabel(path)

            msgString += "%s\n    current: %s\n    latest: %s\n\n" % (
                pathData[1],
                curVersionName,
                latestVersionName,
            )
            updates += 1

        msgString += "Please update the imports in the State Manager."

        if updates > 0:
            if settings.get("accept", False):
                self.onImportVersionsClicked(settings.get("value", "Update all"))
            else:
                self.queueOrShowNotification(
                    msgString,
                    title="New versions available",
                    buttons=["Update all", "Open State Manager", "Skip"],
                    escapeButton="Skip",
                    default="Skip",
                    callback=self.onImportVersionsClicked,
                )
        elif settings.get("showSuccess", False):
            self.core.popup("All imports are up to date.", title="No updates available", severity="info")

    @err_catcher(name=__name__)
    def onImportVersionsClicked(self, button: Union[str, Any]) -> None:
        """Handle import version check dialog button click.
        
        Args:
            button: Button text string or button object clicked
        """
        if self.core.isStr(button):
            result = button
        else:
            result = button.text()

        if result == "Update all":
            sm = self.core.getStateManager()
            sm.updateAllImportStates()

        elif result == "Open State Manager":
            sm = self.core.stateManager()
            sm.gb_import.setChecked(True)

    @err_catcher(name=__name__)
    def checkSceneBuildingUpdates(
        self, settings: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check whether the opened scene has actionable scene-building updates."""
        if not self.core.getConfig(
            "sceneBuilding", "checkForUpdatesOnSceneOpen", config="project"
        ):
            return True

        fileName = self.core.getCurrentFileName()
        if not fileName or not self.core.fileInPipeline(fileName):
            return True

        entity = self.core.getScenefileData(fileName)
        department = entity.get("department")
        task = entity.get("task")
        if entity.get("type") not in ["asset", "shot"] or not department or not task:
            return True

        steps, stepContext = self.core.entities.getSceneBuildingStepsWithUpdateData(
            entity, department, task
        )
        updateSteps = [
            step
            for step in steps
            if (step.get("update_data", {}).get("action") or "").lower()
            != "no change"
        ]
        if not updateSteps:
            return True

        self.queueOrShowNotification(
            "%s scene-building step(s) can be updated."
            % len(updateSteps),
            title="Scene-building updates available",
            buttons=["Update Scene...", "Skip"],
            escapeButton="Skip",
            default="Skip",
            callback=lambda button: self.onSceneBuildingUpdatesClicked(
                button, steps, stepContext
            ),
        )
        return False

    @err_catcher(name=__name__)
    def onSceneBuildingUpdatesClicked(
        self,
        button: Union[str, Any],
        steps: List[Dict[str, Any]],
        stepContext: Dict[str, Any],
    ) -> None:
        """Open the rebuild dialog for the scene-open update results."""
        result = button if self.core.isStr(button) else button.text()
        if result != "Update Scene...":
            return

        from ProjectScripts.SceneBrowser import SceneReBuildStepRunDlg

        self.dlg_sceneBuildingUpdates = SceneReBuildStepRunDlg(
            self.core,
            steps,
            stepContext=stepContext,
            parent=getattr(self.core, "messageParent", None),
        )
        self.dlg_sceneBuildingUpdates.setModal(False)
        self.dlg_sceneBuildingUpdates.show()
        self.dlg_sceneBuildingUpdates.raise_()
        self.dlg_sceneBuildingUpdates.activateWindow()

    @err_catcher(name=__name__)
    def checkFramerange(self, settings: Optional[Dict[str, Any]] = None) -> None:
        """Check if scene frame range matches shot/asset frame range.
        
        Shows popup if mismatch detected, offers to update scene.
        
        Args:
            settings: Optional dict with 'accept' and 'value' keys for automation
        """
        settings = settings or {}
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
        if curRange[0] is None or curRange[1] is None or (int(curRange[0]) == int(shotRange[0]) and int(curRange[1]) == int(shotRange[1])):
            return

        handleRange = self.core.entities.getShotRange(fnameData, handles=True)
        hasHandles = handleRange != shotRange
        if hasHandles and int(curRange[0]) == int(handleRange[0]) and int(curRange[1]) == int(handleRange[1]):
            return

        handlePolicy = os.getenv("PRISM_FRAMERANGE_CHECK_HANDLES")
        if handlePolicy == "enforce":
            shotRange = handleRange
        elif handlePolicy == "ignore":
            hasHandles = False

        shotName = self.core.entities.getShotName(fnameData)
        msgString = (
            "The framerange of the current scene doesn't match the framerange of the shot:\n\nFramerange of current scene:\n%s - %s\n\nFramerange of shot %s:\n%s - %s"
            % (int(curRange[0]), int(curRange[1]), shotName, shotRange[0], shotRange[1])
        )
        if not handlePolicy and hasHandles:
            msgString += " (%s - %s)" % (handleRange[0], handleRange[1])

        if self.core.forceFramerange:
            self.core.setFrameRange(int(shotRange[0]), int(shotRange[1]))
        else:
            if settings.get("accept", False):
                self.onCheckFramerangeClicked(settings.get("value", "Set shotrange in scene"), shotRange, handleRange)
            else:
                buttons = ["Set shotrange in scene", "Skip"]
                if not handlePolicy and hasHandles:
                    buttons.insert(1, "Set shotrange in scene (with handles)")

                self.queueOrShowNotification(
                    msgString,
                    title="Framerange mismatch",
                    buttons=buttons,
                    escapeButton="Skip",
                    default="Skip",
                    callback=lambda x: self.onCheckFramerangeClicked(x, shotRange, handleRange),
                )

    @err_catcher(name=__name__)
    def onCheckFramerangeClicked(self, button: Union[str, Any], shotRange: Tuple[int, int], handleRange: Optional[Tuple[int, int]] = None) -> None:
        """Handle frame range check dialog button click.
        
        Args:
            button: Button object or result string
            shotRange: Shot frame range (start, end)
            handleRange: Range with handles (start, end). Defaults to None.
        """
        if self.core.isStr(button):
            result = button
        else:
            result = button.text()

        if result == "Set shotrange in scene":
            self.core.setFrameRange(int(shotRange[0]), int(shotRange[1]))
        elif result == "Set shotrange in scene (with handles)":
            self.core.setFrameRange(int(handleRange[0]), int(handleRange[1]))

    @err_catcher(name=__name__)
    def checkFPS(self, settings: Optional[Dict[str, Any]] = None) -> None:
        """Check if scene FPS matches project/entity FPS.
        
        Shows popup if mismatch detected, offers to update scene FPS.
        
        Args:
            settings: Optional dict with 'accept' and 'value' keys for automation
        """
        settings = settings or {}
        forceFPS = self.core.getConfig(
            "globals", "forcefps", configPath=self.core.prismIni
        )
        if not forceFPS and not settings.get("force", False):
            return

        if not getattr(self.core.appPlugin, "hasFrameRange", True):
            return

        if not self.core.fileInPipeline():
            return

        pFps = self.core.getConfig("globals", "fps", configPath=self.core.prismIni)

        fileName = self.core.getCurrentFileName()
        entity = self.core.getScenefileData(fileName)
        metaData = self.core.entities.getMetaData(entity)
        fpsDef = "project"

        if "fps" in metaData:
            fpsDef = "entity"
            pFps = metaData["fps"]["value"]

        if pFps is None:
            return

        pFps = float(pFps)
        curFps = self.core.getFPS()
        if pFps == curFps or curFps is None:
            return

        vInfo = [["FPS of current scene:", str(curFps)], ["FPS of %s" % fpsDef, str(pFps)]]
        lay_info = QGridLayout()

        msgString = "The FPS of the current scene doesn't match the FPS of the %s:" % pFps

        for idx, val in enumerate(vInfo):
            l_infoName = QLabel(val[0] + ":\t")
            l_info = QLabel(val[1])
            lay_info.addWidget(l_infoName, idx, 0)
            lay_info.addWidget(l_info, idx, 1)

        lay_info.addItem(
            QSpacerItem(10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )
        lay_info.addItem(
            QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum), 0, 2
        )

        lay_info.setContentsMargins(0, 10, 0, 10)
        w_info = QWidget()
        w_info.setLayout(lay_info)

        if settings.get("accept", False):
            self.onCheckFpsClicked(settings.get("value", "Set %s FPS in current scene" % fpsDef), pFps)
        else:
            self.queueOrShowNotification(
                msgString,
                title="FPS mismatch",
                buttons=["Set %s FPS in current scene" % fpsDef, "Skip"],
                widget=w_info,
                escapeButton="Skip",
                default="Skip",
                callback=lambda x: self.onCheckFpsClicked(x, pFps),
            )

    @err_catcher(name=__name__)
    def onCheckFpsClicked(self, button: Union[str, Any], projectFps: float) -> None:
        """Handle FPS check dialog button click.
        
        Args:
            button: Button text string or button object clicked
            projectFps: Target FPS to set
        """
        if self.core.isStr(button):
            result = button
        else:
            result = button.text()

        if result == "Set project FPS in current scene" or result == "Set entity FPS in current scene":
            self.core.appPlugin.setFPS(self.core, float(projectFps))

    @err_catcher(name=__name__)
    def checkResolution(self, settings: Optional[Dict[str, Any]] = None) -> None:
        """Check if scene resolution matches project/entity resolution.
        
        Shows popup if mismatch detected, offers to update scene resolution.
        
        Args:
            settings: Optional dict with 'accept' and 'value' keys for automation
        """
        settings = settings or {}
        forceRes = self.core.getConfig(
            "globals", "forceResolution", configPath=self.core.prismIni
        )
        if not forceRes and not settings.get("force", False):
            return

        if not self.core.fileInPipeline():
            return

        fileName = self.core.getCurrentFileName()
        entity = self.core.getScenefileData(fileName)
        metaData = self.core.entities.getMetaData(entity)
        resDef = "project"
        pRes = self.core.getConfig(
            "globals", "resolution", configPath=self.core.prismIni
        )

        resX = None
        resY = None
        if pRes:
            resX = pRes[0]
            resY = pRes[1]

        if "resolution_x" in metaData:
            resDef = "entity"
            try:
                resX = int(metaData["resolution_x"]["value"])
            except:
                pass

        if "resolution_y" in metaData:
            resDef = "entity"
            try:
                resY = int(metaData["resolution_y"]["value"])
            except:
                pass

        if not resX or not resY:
            return

        curRes = self.core.getResolution()
        if not curRes:
            return

        if [resX, resY] == curRes:
            return

        vInfo = [
            ["Resolution of current scene:", "%s x %s" % (curRes[0], curRes[1])],
            ["Resolution of %s" % resDef, "%s x %s" % (resX, resY)],
        ]
        lay_info = QGridLayout()
        msgString = "The resolution of the current scene doesn't match the resolution of the %s:" % resDef

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

        lay_info.setContentsMargins(0, 10, 0, 10)
        w_info = QWidget()
        w_info.setLayout(lay_info)

        if hasattr(self, "dlg_res") and self.core.isObjectValid(self.dlg_res) and self.dlg_res.isVisible():
            self.dlg_res.close()

        if settings.get("accept", False):
            self.onCheckResolutionClicked(settings.get("value", "Set %s resolution in current scene" % resDef), [resX, resY])
        else:
            self.dlg_res = self.queueOrShowNotification(
                msgString,
                title="Resolution mismatch",
                buttons=["Set %s resolution in current scene" % resDef, "Skip"],
                widget=w_info,
                escapeButton="Skip",
                default="Skip",
                callback=lambda x: self.onCheckResolutionClicked(x, [resX, resY]),
            )

    @err_catcher(name=__name__)
    def onCheckResolutionClicked(self, button: Union[str, Any], projectResolution: Tuple[int, int]) -> None:
        """Handle resolution check dialog button click.
        
        Args:
            button: Button object or result string
            projectResolution: Resolution tuple (width, height)
        """
        if self.core.isStr(button):
            result = button
        else:
            result = button.text()

        if result == "Set project resolution in current scene" or result == "Set entity resolution in current scene":
            self.core.appPlugin.setResolution(*projectResolution)

    @err_catcher(name=__name__)
    def checkAppVersion(self) -> None:
        """Check if application version is compatible with Prism."""
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
