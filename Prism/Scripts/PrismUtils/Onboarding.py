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
import re
import tempfile
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import ClassVar

from qtpy.QtCore import (
    QObject,
    Property,
    QCoreApplication,
    QEventLoop,
    QThread,
    QStandardPaths,
    QTimer,
    QUrl,
    Signal,
    Slot,
    Qt,
)
from qtpy.QtWidgets import QDialog, QFileDialog, QVBoxLayout


logger = logging.getLogger(__name__)


class OnboardingBridge(QObject):
    stepChanged = Signal()
    statusChanged = Signal()
    pluginInstallChanged = Signal()
    pluginInstallFinished = Signal()
    manualPluginsChanged = Signal()
    pluginIconsChanged = Signal()
    demoProjectsChanged = Signal()
    demoProjectProgressChanged = Signal()

    def __init__(self, controller):
        super(OnboardingBridge, self).__init__()
        self.controller = controller
        self._step = 0
        self._installingPlugins = False
        self._pluginInstallStatus = ""
        self._pluginInstallTotal = 0
        self._pluginInstallCompleted = 0

    def getStep(self):
        return self._step

    def setStep(self, step):
        step = max(0, min(int(step), 4))
        if self._step == step:
            return

        self._step = step
        self.stepChanged.emit()

    step = Property(int, getStep, setStep, notify=stepChanged)

    def getLoggedIn(self):
        loggedIn = False
        internals = self.controller.getInternals()
        if internals:
            status = internals.getLoginStatus()
            if status.get("loggedin"):
                license = status.get("licenseType")
                if not license:
                    internals.acquireLicenseDeferred()
                    self.refreshStatus()
                
                if bool(license):
                    loggedIn = True

        return loggedIn

    loggedIn = Property(bool, getLoggedIn, notify=statusChanged)

    def getAcquiringLicense(self):
        internals = self.controller.getInternals()
        return bool(internals and getattr(internals, "acquiringLicense", False))

    acquiringLicense = Property(
        bool, getAcquiringLicense, notify=statusChanged
    )

    def getAccountName(self):
        internals = self.controller.getInternals()
        if not internals:
            return ""

        status = internals.getLoginStatus() or {}
        return str(status.get("username", "")) if status.get("loggedin") else ""

    accountName = Property(str, getAccountName, notify=statusChanged)

    def getLicenseType(self):
        internals = self.controller.getInternals()
        if not internals:
            return ""

        status = internals.getLoginStatus() or {}
        return str(status.get("licenseType", "")) if status.get("loggedin") else ""

    licenseType = Property(str, getLicenseType, notify=statusChanged)

    def getDefaultPluginBundleTitle(self):
        return "Free" if self.getLicenseType().strip().lower() == "free" else "Advanced"

    defaultPluginBundleTitle = Property(
        str, getDefaultPluginBundleTitle, notify=statusChanged
    )

    def getAccountAvailable(self):
        return self.controller.getInternals() is not None

    accountAvailable = Property(bool, getAccountAvailable, notify=statusChanged)

    def getHubAvailable(self):
        return self.controller.core.getPlugin("Hub") is not None

    hubAvailable = Property(bool, getHubAvailable, notify=statusChanged)

    def getHelpUrl(self):
        return self.controller.getHelpUrl()

    helpUrl = Property(str, getHelpUrl, constant=True)

    def getProjectName(self):
        return getattr(self.controller.core, "projectName", "")

    projectName = Property(str, getProjectName, notify=statusChanged)

    def getProjectPath(self):
        return getattr(self.controller.core, "projectPath", "")

    projectPath = Property(str, getProjectPath, notify=statusChanged)

    def getProjectImageUrl(self):
        projectPath = self.getProjectPath()
        projects = getattr(self.controller.core, "projects", None)
        getProjectImage = getattr(projects, "getProjectImage", None)
        if not projectPath or not callable(getProjectImage):
            return QUrl()

        imagePath = getProjectImage(projectPath=projectPath)
        return QUrl.fromLocalFile(imagePath) if imagePath else QUrl()

    projectImageUrl = Property(QUrl, getProjectImageUrl, notify=statusChanged)

    def getPluginBundles(self):
        return self.controller.pluginBundles

    pluginBundles = Property(
        "QVariantList", getPluginBundles, notify=manualPluginsChanged
    )

    def getProjectManagerBundles(self):
        return self.controller.projectManagerBundles

    projectManagerBundles = Property(
        "QVariantList", getProjectManagerBundles, notify=manualPluginsChanged
    )

    def getDemoProjects(self):
        return self.controller.demoProjects

    demoProjects = Property(
        "QVariantList", getDemoProjects, notify=demoProjectsChanged
    )

    def getLoadingDemoProjects(self):
        return self.controller.loadingDemoProjects

    loadingDemoProjects = Property(
        bool, getLoadingDemoProjects, notify=demoProjectsChanged
    )

    def getDemoProjectsError(self):
        return self.controller.demoProjectsError

    demoProjectsError = Property(str, getDemoProjectsError, notify=demoProjectsChanged)

    def getCreatingDemoProject(self):
        return self.controller.creatingDemoProject

    creatingDemoProject = Property(
        bool, getCreatingDemoProject, notify=demoProjectProgressChanged
    )

    def getDemoProjectProgress(self):
        return self.controller.demoProjectProgress

    demoProjectProgress = Property(
        int, getDemoProjectProgress, notify=demoProjectProgressChanged
    )

    def getDemoProjectDownloadedSize(self):
        return self.controller.demoProjectDownloadedSize

    demoProjectDownloadedSize = Property(
        str, getDemoProjectDownloadedSize, notify=demoProjectProgressChanged
    )

    def getDemoProjectTotalSize(self):
        return self.controller.demoProjectTotalSize

    demoProjectTotalSize = Property(
        str, getDemoProjectTotalSize, notify=demoProjectProgressChanged
    )

    def getDemoProjectStatus(self):
        return self.controller.demoProjectStatus

    demoProjectStatus = Property(
        str, getDemoProjectStatus, notify=demoProjectProgressChanged
    )

    def getDemoProjectError(self):
        return self.controller.demoProjectError

    demoProjectError = Property(
        str, getDemoProjectError, notify=demoProjectProgressChanged
    )

    def getManualPluginNames(self):
        return self.controller.manualPluginNames

    manualPluginNames = Property(
        "QVariantList", getManualPluginNames, notify=manualPluginsChanged
    )

    def getUsingManualPluginSelection(self):
        return self.controller.usingManualPluginSelection

    usingManualPluginSelection = Property(
        bool, getUsingManualPluginSelection, notify=manualPluginsChanged
    )

    def getAvailablePlugins(self):
        return self.controller.availablePluginRecords

    availablePlugins = Property(
        "QVariantList", getAvailablePlugins, notify=manualPluginsChanged
    )

    def getLoadingAvailablePlugins(self):
        return self.controller.loadingAvailablePlugins

    loadingAvailablePlugins = Property(
        bool, getLoadingAvailablePlugins, notify=manualPluginsChanged
    )

    def getAvailablePluginsError(self):
        return self.controller.availablePluginsError

    availablePluginsError = Property(
        str, getAvailablePluginsError, notify=manualPluginsChanged
    )

    def getPluginIcons(self):
        return self.controller.pluginIcons

    pluginIcons = Property(
        "QVariantMap", getPluginIcons, notify=pluginIconsChanged
    )

    def getInstallingPlugins(self):
        return self._installingPlugins

    installingPlugins = Property(
        bool, getInstallingPlugins, notify=pluginInstallChanged
    )

    def getPluginInstallStatus(self):
        return self._pluginInstallStatus

    pluginInstallStatus = Property(
        str, getPluginInstallStatus, notify=pluginInstallChanged
    )

    def getPluginInstallTotal(self):
        return self._pluginInstallTotal

    pluginInstallTotal = Property(
        int, getPluginInstallTotal, notify=pluginInstallChanged
    )

    def getPluginInstallCompleted(self):
        return self._pluginInstallCompleted

    pluginInstallCompleted = Property(
        int, getPluginInstallCompleted, notify=pluginInstallChanged
    )

    def setPluginInstallState(
        self, installing, status="", total=None, completed=None
    ):
        self._installingPlugins = installing
        self._pluginInstallStatus = status
        if total is not None:
            self._pluginInstallTotal = total
        if completed is not None:
            self._pluginInstallCompleted = completed
        self.pluginInstallChanged.emit()

    @Slot()
    def refreshStatus(self):
        self.statusChanged.emit()

    @Slot()
    def next(self):
        self.setStep(self._step + 1)

    @Slot()
    def back(self):
        self.setStep(self._step - 1)

    @Slot(int)
    def goToStep(self, step):
        self.setStep(step)

    @Slot()
    def skip(self):
        self.controller.skip()
        self.controller.close()

    @Slot()
    def finish(self):
        self.controller.finish()
        self.controller.close()

    @Slot()
    def openLogin(self):
        self.controller.openLogin()

    @Slot()
    def switchUser(self):
        self.controller.switchUser()

    @Slot()
    def openHub(self):
        self.controller.openHub()

    @Slot()
    def installHubDependencies(self):
        self.controller.installHubDependencies()

    @Slot(result=bool)
    def loadAvailablePlugins(self):
        return self.controller.loadAvailablePlugins()

    @Slot(object)
    def handleAvailablePluginDataLoaded(self, serverData):
        self.controller._onAvailablePluginDataLoaded(serverData)

    @Slot(str, str)
    def handleAvailablePluginIconLoaded(self, pluginName, iconPath):
        self.controller._onAvailablePluginIconLoaded(pluginName, iconPath)

    @Slot(str)
    def handleAvailablePluginsFailed(self, message):
        self.controller._onAvailablePluginsFailed(message)

    @Slot()
    def handleAvailablePluginsFinished(self):
        self.controller._onAvailablePluginsFinished()

    @Slot("QVariantList")
    def applyManualPluginSelection(self, pluginNames):
        self.controller.applyManualPluginSelection(pluginNames)

    @Slot()
    def clearManualPluginSelection(self):
        self.controller.clearManualPluginSelection()

    @Slot("QVariantList")
    def installPlugins(self, pluginNames):
        self.controller.installPlugins(pluginNames)

    @Slot(str, result=bool)
    def isPluginInstalled(self, pluginName):
        return self.controller.isPluginInstalled(pluginName)

    @Slot()
    def createProject(self):
        self.controller.createProject()

    @Slot()
    def loadDemoProjects(self):
        self.controller.loadDemoProjects()

    @Slot(str, result=str)
    def defaultDemoProjectPath(self, projectName):
        return self.controller.getDefaultDemoProjectPath(projectName)

    @Slot(str, result=str)
    def browseDemoProjectPath(self, currentPath):
        return self.controller.browseDemoProjectPath(currentPath)

    @Slot(str, str, str, result=bool)
    def createDemoProject(self, demoProjectId, projectName, projectPath):
        return self.controller.createDemoProject(
            demoProjectId, projectName, projectPath
        )

    @Slot(int, str)
    def handleDemoProjectProgress(self, progress, status):
        self.controller._onDemoProjectProgressChanged(progress, status)

    @Slot(object, object)
    def handleDemoProjectDownloadProgress(self, downloaded, total):
        self.controller._onDemoProjectDownloadProgressChanged(downloaded, total)

    @Slot(str)
    def handleDemoProjectCreated(self, result):
        self.controller._onDemoProjectCreated(result)

    @Slot(str)
    def handleDemoProjectFailed(self, message):
        self.controller._onDemoProjectFailed(message)

    @Slot()
    def handleDemoProjectCanceled(self):
        self.controller._onDemoProjectCanceled()

    @Slot()
    def cancelDemoProject(self):
        self.controller.cancelDemoProject()

    @Slot("QVariantList")
    def handleDemoProjectsLoaded(self, projects):
        self.controller._onDemoProjectsLoaded(projects)

    @Slot(str, str)
    def handleDemoProjectThumbnailLoaded(self, projectId, thumbnailPath):
        self.controller._onDemoProjectThumbnailLoaded(projectId, thumbnailPath)

    @Slot()
    def handleDemoProjectsFinished(self):
        self.controller._onDemoProjectsFinished()

    @Slot(str)
    def handleDemoProjectsFailed(self, message):
        self.controller._onDemoProjectsFailed(message)

    @Slot()
    def openProject(self):
        self.controller.openProject()

    @Slot()
    def openHelp(self):
        self.controller.openHelp()

    @Slot(str)
    def openUrl(self, url):
        self.controller.openUrl(url)


class OnboardingController(object):
    SCHEMA_VERSION = 1
    CONFIG_SECTION = "onboarding"
    HELP_URL = "https://prism-pipeline.com/docs/latest"

    def __init__(self, core):
        self.core = core
        self.dialog = None
        self.bridge = None
        self._onClosed = None
        self._closing = False
        self._closePending = False
        self._openProjectBrowserOnClose = False
        self._callbackIds = []
        self._hub = None
        self._pluginInstallQueue = []
        self._pluginInstallFailures = []
        self.pluginBundles = []
        self.projectManagerBundles = []
        self.demoProjects = []
        self.availablePluginRecords = []
        self.pluginIcons = {}
        self.loadingAvailablePlugins = False
        self.availablePluginsError = ""
        self.availablePluginsThread = None
        self.availablePluginsWorker = None
        self.manualPluginNames = []
        self.usingManualPluginSelection = False
        self.creatingDemoProject = False
        self.demoProjectProgress = 0
        self.demoProjectDownloadedSize = ""
        self.demoProjectTotalSize = ""
        self.demoProjectStatus = ""
        self.demoProjectError = ""
        self.demoProjectName = ""
        self.loadingDemoProjects = False
        self.demoProjectsError = ""
        self.demoProjectsThread = None
        self.demoProjectsWorker = None
        self.demoProjectThread = None
        self.demoProjectWorker = None

    def loadDemoProjects(self):
        if self.loadingDemoProjects:
            return

        if not self.getInternals():
            self.demoProjects = []
            self.loadingDemoProjects = False
            self.demoProjectsError = (
                "Demo projects are unavailable because the PrismInternals plugin "
                "is not loaded."
            )
            if self.bridge:
                self.bridge.demoProjectsChanged.emit()
            return

        self.demoProjects = []
        self.loadingDemoProjects = True
        self.demoProjectsError = ""
        self.bridge.demoProjectsChanged.emit()

        self.demoProjectsThread = QThread()
        self.demoProjectsWorker = DemoProjectsWorker(self)
        self.demoProjectsWorker.moveToThread(self.demoProjectsThread)
        self.demoProjectsThread.started.connect(self.demoProjectsWorker.run)
        self.demoProjectsWorker.projectsLoaded.connect(
            self.bridge.handleDemoProjectsLoaded
        )
        self.demoProjectsWorker.thumbnailLoaded.connect(
            self.bridge.handleDemoProjectThumbnailLoaded
        )
        self.demoProjectsWorker.finished.connect(
            self.bridge.handleDemoProjectsFinished
        )
        self.demoProjectsWorker.failed.connect(self.bridge.handleDemoProjectsFailed)
        self.demoProjectsWorker.finished.connect(self.demoProjectsWorker.deleteLater)
        self.demoProjectsWorker.finished.connect(self.demoProjectsThread.quit)
        self.demoProjectsThread.finished.connect(self.demoProjectsThread.deleteLater)
        self.demoProjectsThread.finished.connect(self._clearDemoProjectsThread)
        self.demoProjectsThread.start()

    def _onDemoProjectsLoaded(self, projects):
        if projects:
            self.demoProjects = [dict(project) for project in projects]
            self.loadingDemoProjects = False
            self.demoProjectsError = ""
            if self.bridge:
                self.bridge.demoProjectsChanged.emit()

    def _onDemoProjectThumbnailLoaded(self, projectId, thumbnailPath):
        projects = [dict(project) for project in self.demoProjects]
        for project in projects:
            if project["id"] == projectId:
                project["thumbnail"] = QUrl.fromLocalFile(thumbnailPath).toString()
                project["thumbnailReady"] = True
                self.demoProjects = projects
                if self.bridge:
                    self.bridge.demoProjectsChanged.emit()
                return

    def _onDemoProjectsFinished(self):
        self.loadingDemoProjects = False
        if self.bridge:
            self.bridge.demoProjectsChanged.emit()

    def _onDemoProjectsFailed(self, message):
        logger.warning("Failed to load demo projects: %s", message)
        self.loadingDemoProjects = False
        self.demoProjectsError = (
            "Demo projects could not be loaded. Check your connection and try again.\n\n"
            "Error details: {}".format(message.strip("\n ").split("\n")[-1])
        )
        if self.bridge:
            self.bridge.demoProjectsChanged.emit()

    def _clearDemoProjectsThread(self):
        self.loadingDemoProjects = False
        self.demoProjectsWorker = None
        self.demoProjectsThread = None

    def getPluginBundles(self):
        internals = self.getInternals()
        bundles = internals.getPluginBundles() if internals else None
        return bundles

    @staticmethod
    def arePluginBundlesValid(bundles):
        return all(
            isinstance(bundle, dict)
            and isinstance(bundle.get("title"), str)
            and isinstance(bundle.get("plugins"), list)
            and all(isinstance(plugin, str) for plugin in bundle["plugins"])
            for bundle in bundles
        )

    def setPluginBundles(self, bundles):
        featureBundles = []
        projectManagerBundles = []
        if isinstance(bundles, dict):
            featureBundles = bundles.get("pluginBundles", [])
            projectManagerBundles = bundles.get("projectManagers", [])

        self.pluginBundles = featureBundles
        self.projectManagerBundles = projectManagerBundles

    def getState(self):
        return self.core.getConfig(
            self.CONFIG_SECTION,
            config="user",
            dft={},
        ) or {}

    def isCompleted(self):
        state = self.getState()
        return (
            state.get("completed") is True
            and state.get("schemaVersion") == self.SCHEMA_VERSION
        )

    def shouldShow(self, force=False):
        appPlugin = getattr(self.core, "appPlugin", None)
        if (
            not self.core.uiAvailable
            or not appPlugin
            or appPlugin.pluginName != "Standalone"
        ):
            return False

        if force:
            return True

        if os.getenv("PRISM_ONBOARDING") == "1":
            return True

        if [name for name in self.core.getPluginNames() if name not in ["PrismInternals", "Hub", "Standalone"]] or self.core.plugins._delayedPluginPaths:
            return False

        if "silent" in self.core.prismArgs:
            return False

        if os.getenv("PRISM_NO_ONBOARDING") == "1":
            return False

        if self.isCompleted():
            return False

        return True

    def setCompleted(self, status):
        self.core.setConfig(
            self.CONFIG_SECTION,
            val={
                "completed": True,
                "status": status,
                "schemaVersion": self.SCHEMA_VERSION,
            },
            config="user",
        )

    def finish(self):
        self.setCompleted("completed")
        self._openProjectBrowserOnClose = True

    def skip(self):
        self.setCompleted("skipped")

    def show(self, force=False, onClosed=None):
        if not self.prepare(force=force, onClosed=onClosed):
            return False

        return self.showPrepared()

    def prepare(self, force=False, onClosed=None, ignoreInternalsAndHub=False):
        if not self.shouldShow(force=force):
            return

        with self.core.waitPopup(self.core, "Preparing Onboarding. Please wait..."):
            os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
            try:
                from qtpy.QtQuickWidgets import QQuickWidget
            except ImportError:
                return

            if self.dialog:
                if onClosed is not None:
                    self._onClosed = onClosed
                return True

            self.setPluginBundles(self.getPluginBundles())

            qmlPath = os.path.join(
                self.core.prismRoot,
                "Scripts",
                "UserInterfacesPrism",
                "Onboarding",
                "Onboarding.qml",
            )
            if not os.path.exists(qmlPath):
                return

            self._onClosed = onClosed
            self._closing = False
            self._closePending = False
            self._openProjectBrowserOnClose = False
            self.bridge = OnboardingBridge(self)
            self.dialog = QDialog()
            self.dialog.setWindowTitle("Welcome to Prism")
            self.dialog.setMinimumSize(920, 620)
            self.dialog.resize(1040, 680)
            self.dialog.setAttribute(Qt.WA_DeleteOnClose, True)
            self.core.parentWindow(self.dialog)
            splashScreen = getattr(self.core, "splashScreen", None)
            if splashScreen and splashScreen.isVisible():
                splashScreen.setHidden(True)

            layout = QVBoxLayout(self.dialog)
            layout.setContentsMargins(0, 0, 0, 0)
            quickWidget = QQuickWidget(self.dialog)
            quickWidget.setResizeMode(QQuickWidget.SizeRootObjectToView)
            quickWidget.rootContext().setContextProperty("onboarding", self.bridge)
            quickWidget.rootContext().setContextProperty(
                "prismLogoUrl",
                QUrl.fromLocalFile(
                    os.path.join(
                        self.core.prismRoot,
                        "Scripts",
                        "UserInterfacesPrism",
                        "prism-pipeline-logo-white.png",
                    )
                ),
            )
            hubPlugin = self.core.getPlugin("Hub")
            hubIconPath = (
                os.path.join(hubPlugin.pluginDirectory, "UserInterfaces", "hub.png")
                if hubPlugin
                else ""
            )
            quickWidget.rootContext().setContextProperty(
                "hubIconUrl", QUrl.fromLocalFile(hubIconPath) if hubIconPath else QUrl()
            )
            quickWidget.setSource(QUrl.fromLocalFile(qmlPath))
            if quickWidget.status() == QQuickWidget.Error:
                self.dialog.deleteLater()
                self.dialog = None
                self.bridge = None
                return

            self.quickWidget = quickWidget
            layout.addWidget(quickWidget)
            self._registerCallbacks()
            self.dialog.finished.connect(self._onDialogClosed)
            self.dialog.destroyed.connect(self._onDialogDestroyed)
            return True

    def showPrepared(self):
        if not self.dialog:
            return False

        self.dialog.show()
        self.dialog.activateWindow()
        self.dialog.raise_()
        return True

    def close(self):
        if not self.dialog or self._closePending:
            return

        self._closePending = True
        QTimer.singleShot(0, self._closeDialog)

    def _closeDialog(self):
        if self.dialog:
            self.quickWidget.setSource(QUrl())
            self.dialog.close()

    def _onDialogClosed(self, result):
        if self._closing:
            return

        self._closing = True
        if self.quickWidget.source() != QUrl():
            self.quickWidget.setSource(QUrl())

        self._closePending = False
        for callbackId in self._callbackIds:
            self.core.unregisterCallback(callbackId)

        self._callbackIds = []
        if self._hub:
            try:
                self._hub.signalDownloaded.disconnect(self.refreshStatus)
            except (RuntimeError, TypeError):
                pass

        self._hub = None
        callback = self._onClosed
        openProjectBrowser = self._openProjectBrowserOnClose
        self.dialog = None
        self._onClosed = None
        self._openProjectBrowserOnClose = False
        if callback:
            callback()

        projectBrowser = getattr(self.core, "pb", None)
        if openProjectBrowser and not (
            projectBrowser and projectBrowser.isVisible()
        ):
            self.core.projectBrowser()

    def _onDialogDestroyed(self, *args):
        self.quickWidget = None
        self.bridge = None

    def _registerCallbacks(self):
        for callbackName in [
            "prismAccount_loggedIn",
            "prismAccount_loggedOut",
            "prismAccount_licenseChanged",
            "onProjectCreated",
            "onProjectChanged",
        ]:
            callback = self.core.registerCallback(callbackName, self.refreshStatus)
            self._callbackIds.append(callback["id"])

    def refreshStatus(self, *args, **kwargs):
        if self.bridge:
            self.bridge.refreshStatus()

    def getInternals(self):
        plugin = self.core.getPlugin("PrismInternals")
        return getattr(plugin, "internals", None) if plugin else None

    def installHubDependencies(self):
        self.core.plugins.installHub()
        bundles = self.getPluginBundles()
        self.setPluginBundles(bundles)
        self.availablePluginRecords = []
        self.pluginIcons = {}
        self.refreshStatus()
        if self.bridge:
            self.bridge.manualPluginsChanged.emit()
            self.bridge.pluginIconsChanged.emit()
            self.loadAvailablePlugins()

    def openLogin(self):
        internals = self.getInternals()
        if not internals:
            self.core.popup("Prism account login is currently unavailable.")
            return

        loginDialog = internals.getLoginDlg(parent=self.dialog, allowSkip=True)
        loginDialog.finished.connect(self.refreshStatus)
        loginDialog.show()
        self.loginDialog = loginDialog

    def switchUser(self):
        internals = self.getInternals()
        if not internals:
            self.core.popup("Prism account login is currently unavailable.")
            return

        if not internals.isLoggedIn() or internals.logout():
            self.refreshStatus()
            self.openLogin()

    def openHub(self):
        plugin = self.core.getPlugin("Hub")
        if not plugin:
            self.core.popup("The Prism Hub plugin is currently unavailable.")
            return

        if not self.getInternals() or not self.getInternals().isLoggedIn():
            self.openLogin()
            return

        self._hub = plugin.getHub()
        try:
            self._hub.signalDownloaded.disconnect(self.refreshStatus)
        except (RuntimeError, TypeError):
            pass

        self._hub.signalDownloaded.connect(self.refreshStatus)
        plugin.launch()

    def getAvailablePluginRecords(self, force=False, serverData=None):
        if self.availablePluginRecords and not force:
            return self.availablePluginRecords

        if serverData is None:
            internals = self.getInternals()
            serverData = internals.getHubData() if internals else None
        if not isinstance(serverData, dict):
            return []

        categories = serverData.get("categories", [])
        pluginItems = []
        for category in categories:
            if str(category.get("name", "")).strip().lower() == "plugins":
                pluginItems = category.get("items", [])
                break

        records = []
        for item in pluginItems:
            if not isinstance(item, dict):
                continue

            itemType = str(item.get("type", "")).lower()
            if itemType and "plugin" not in itemType:
                continue

            itemKey = self._getFirstPluginValue(
                item, ["itemKey", "item_key", "key", "id"]
            )
            name = self._getFirstPluginValue(item, ["name"])
            pluginName = self._getFirstPluginValue(item, ["pluginName"])
            if not itemKey or not name or not pluginName:
                continue

            records.append(
                {
                    "name": name,
                    "pluginName": pluginName,
                    "itemKey": itemKey,
                    "installed": self.isPluginInstalled(pluginName),
                    "thumbnailColor": self._getPluginThumbnailColor(item),
                }
            )

        records.sort(key=lambda record: record["name"].lower())
        self.availablePluginRecords = records
        return records

    @staticmethod
    def _getFirstPluginValue(data, keys):
        for key in keys:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        return ""

    @classmethod
    def _getPluginThumbnailColor(cls, item):
        stylesheet = cls._getFirstPluginValue(
            item, ["stylesheet", "styleSheet", "css"]
        )
        if not stylesheet:
            return ""

        candidateTokens = set()
        for key in ["itemKey", "pluginName", "name"]:
            value = cls._getFirstPluginValue(item, [key])
            token = cls._normalizePluginSelectorToken(f"{value}_list")
            if token:
                candidateTokens.add(token)

        for selector, declarations in re.findall(
            r"([^{}]+)\{([^{}]*)\}", stylesheet
        ):
            selectorTokens = {
                cls._normalizePluginSelectorToken(token)
                for token in re.findall(r"#([A-Za-z0-9_-]+)", selector)
            }
            if not candidateTokens.intersection(selectorTokens):
                continue

            for declaration in declarations.split(";"):
                if ":" not in declaration:
                    continue

                propertyName, value = declaration.split(":", 1)
                if propertyName.strip().lower() not in [
                    "background",
                    "background-color",
                ]:
                    continue

                match = re.search(
                    r"#[0-9a-fA-F]{8}|#[0-9a-fA-F]{6}|#[0-9a-fA-F]{4}|#[0-9a-fA-F]{3}",
                    value,
                )
                if match:
                    return match.group(0)

        return ""

    @staticmethod
    def _normalizePluginSelectorToken(value):
        return "".join(character.lower() for character in value if character.isalnum())

    def loadAvailablePlugins(self):
        if self.loadingAvailablePlugins:
            return False

        if self.availablePluginRecords:
            self.bridge.manualPluginsChanged.emit()
            return True

        internals = self.getInternals()
        if not internals:
            self.availablePluginsError = "Available plugins could not be loaded."
            self.bridge.manualPluginsChanged.emit()
            return False

        self.loadingAvailablePlugins = True
        self.availablePluginsError = ""
        self.bridge.manualPluginsChanged.emit()

        self.availablePluginsThread = QThread()
        self.availablePluginsWorker = AvailablePluginsWorker(internals)
        self.availablePluginsWorker.moveToThread(self.availablePluginsThread)
        self.availablePluginsThread.started.connect(self.availablePluginsWorker.run)
        self.availablePluginsWorker.loaded.connect(
            self.bridge.handleAvailablePluginDataLoaded
        )
        self.availablePluginsWorker.iconLoaded.connect(
            self.bridge.handleAvailablePluginIconLoaded
        )
        self.availablePluginsWorker.failed.connect(
            self.bridge.handleAvailablePluginsFailed
        )
        self.availablePluginsWorker.finished.connect(
            self.bridge.handleAvailablePluginsFinished
        )
        self.availablePluginsWorker.finished.connect(
            self.availablePluginsWorker.deleteLater
        )
        self.availablePluginsWorker.finished.connect(self.availablePluginsThread.quit)
        self.availablePluginsThread.finished.connect(
            self.availablePluginsThread.deleteLater
        )
        self.availablePluginsThread.finished.connect(
            self._clearAvailablePluginsThread
        )
        self.availablePluginsThread.start()
        return True

    def _onAvailablePluginDataLoaded(self, serverData):
        records = self.getAvailablePluginRecords(force=True, serverData=serverData)
        self.loadingAvailablePlugins = False
        self.availablePluginsError = (
            "" if records else "No available plugins could be loaded."
        )
        if self.bridge:
            self.bridge.manualPluginsChanged.emit()

    def _onAvailablePluginIconLoaded(self, pluginName, iconPath):
        icons = dict(self.pluginIcons)
        icons[pluginName] = QUrl.fromLocalFile(iconPath).toString()
        self.pluginIcons = icons
        if self.bridge:
            self.bridge.pluginIconsChanged.emit()

    def _onAvailablePluginsFailed(self, message):
        self.loadingAvailablePlugins = False
        self.availablePluginsError = "Available plugins could not be loaded."
        if self.bridge:
            self.bridge.manualPluginsChanged.emit()

    def _onAvailablePluginsFinished(self):
        self.loadingAvailablePlugins = False
        if self.bridge:
            self.bridge.manualPluginsChanged.emit()

    def _clearAvailablePluginsThread(self):
        self.availablePluginsWorker = None
        self.availablePluginsThread = None

    def applyManualPluginSelection(self, pluginNames):
        installedNames = {
            record["pluginName"]
            for record in self.availablePluginRecords
            if record["installed"]
        }
        self.manualPluginNames = list(
            dict.fromkeys(
                str(name) for name in pluginNames if str(name) not in installedNames
            )
        )
        self.usingManualPluginSelection = True
        self.bridge.manualPluginsChanged.emit()

    def clearManualPluginSelection(self):
        if not self.usingManualPluginSelection and not self.manualPluginNames:
            return

        self.manualPluginNames = []
        self.usingManualPluginSelection = False
        self.bridge.manualPluginsChanged.emit()

    def isPluginInstalled(self, pluginName):
        if self.core.getPlugin(pluginName):
            return True

        getUnloadedPlugin = getattr(self.core.plugins, "getUnloadedPlugin", None)
        return bool(getUnloadedPlugin and getUnloadedPlugin(pluginName))

    def installPlugins(self, pluginNames):
        uniqueNames = list(dict.fromkeys(str(name) for name in pluginNames))
        itemKeys = {
            record["pluginName"]: record["itemKey"]
            for record in self.availablePluginRecords
        }
        self._pluginInstallQueue = [
            {"name": name, "itemKey": itemKeys.get(name, name)}
            for name in uniqueNames
            if not self.isPluginInstalled(name)
        ]
        self._pluginInstallFailures = []
        if not self._pluginInstallQueue:
            self.bridge.pluginInstallFinished.emit()
            return

        internals = self.getInternals()
        if not internals or not internals.isLoggedIn():
            self.openLogin()
            return

        self.bridge.setPluginInstallState(
            True,
            "Preparing plugin installation...",
            total=len(self._pluginInstallQueue),
            completed=0,
        )
        QTimer.singleShot(0, self._installNextPlugin)

    def _installNextPlugin(self):
        if not self.dialog or not self.bridge:
            self._pluginInstallQueue = []
            return

        if not self._pluginInstallQueue:
            self.bridge.setPluginInstallState(False)
            self.refreshStatus()
            if self._pluginInstallFailures:
                self.core.popup(
                    "Some plugins could not be installed:\n\n{}".format(
                        "\n".join(self._pluginInstallFailures)
                    ),
                    parent=self.dialog,
                )

            self.bridge.pluginInstallFinished.emit()
            return

        plugin = self._pluginInstallQueue.pop(0)
        pluginName = plugin["name"]
        self.bridge.setPluginInstallState(
            True, "Installing {}...".format(pluginName)
        )
        QCoreApplication.processEvents(QEventLoop.ExcludeUserInputEvents)
        if not self.dialog or not self.bridge:
            self._pluginInstallQueue = []
            return

        internals = self.getInternals()
        result = internals.installPlugin(plugin["itemKey"], parent=self.dialog, popup=False)
        if result:
            self.bridge.setPluginInstallState(
                True,
                "Installed {}.".format(pluginName),
                completed=self.bridge.getPluginInstallCompleted() + 1,
            )
        else:
            self._pluginInstallFailures.append(pluginName)

        QTimer.singleShot(0, self._installNextPlugin)

    def createProject(self):
        self.projectDialog = self.core.projects.createProjectDialog()

    def getDefaultDemoProjectPath(self, projectName):
        documentsPath = QStandardPaths.writableLocation(
            QStandardPaths.DocumentsLocation
        )
        return os.path.normpath(
            os.path.join(documentsPath, "Prism2", "projects", projectName)
        )

    def browseDemoProjectPath(self, currentPath):
        return QFileDialog.getExistingDirectory(
            self.dialog,
            "Select demo project folder",
            currentPath or QStandardPaths.writableLocation(
                QStandardPaths.DocumentsLocation
            ),
        )

    def createDemoProject(self, demoProjectId, projectName, projectPath):
        projectName = projectName.strip()
        projectPath = projectPath.strip()
        if not projectName or not projectPath:
            self.core.popup(
                "Enter a project name and project path.", parent=self.dialog
            )
            return

        demoProjectIds = {project["id"] for project in self.demoProjects}
        if demoProjectId not in demoProjectIds:
            self.core.popup("Select a demo project.", parent=self.dialog)
            return False

        if self.creatingDemoProject:
            return False

        project = next(
            project for project in self.demoProjects if project["id"] == demoProjectId
        )
        if project.get("enabled", True) is False:
            self.core.popup(
                "This demo project is not available yet.", parent=self.dialog
            )
            return False

        self.creatingDemoProject = True
        self.demoProjectProgress = 0
        self.demoProjectDownloadedSize = "0 B"
        self.demoProjectTotalSize = str(project.get("size") or "")
        self.demoProjectStatus = "Preparing download..."
        self.demoProjectError = ""
        self.demoProjectName = projectName
        self.bridge.demoProjectProgressChanged.emit()

        self.demoProjectThread = QThread()
        self.demoProjectWorker = self.core.getPlugin("PrismInternals").internals.getDemoProjectWorker(
            project["downloadUrl"], projectPath
        )
        self.demoProjectWorker.moveToThread(self.demoProjectThread)
        self.demoProjectThread.started.connect(self.demoProjectWorker.run)
        self.demoProjectWorker.progressChanged.connect(
            self.bridge.handleDemoProjectProgress
        )
        self.demoProjectWorker.downloadProgressChanged.connect(
            self.bridge.handleDemoProjectDownloadProgress
        )
        self.demoProjectWorker.finished.connect(self.bridge.handleDemoProjectCreated)
        self.demoProjectWorker.failed.connect(self.bridge.handleDemoProjectFailed)
        self.demoProjectWorker.canceled.connect(self.bridge.handleDemoProjectCanceled)
        self.demoProjectWorker.finished.connect(self.demoProjectWorker.deleteLater)
        self.demoProjectWorker.failed.connect(self.demoProjectWorker.deleteLater)
        self.demoProjectWorker.canceled.connect(self.demoProjectWorker.deleteLater)
        self.demoProjectWorker.finished.connect(self.demoProjectThread.quit)
        self.demoProjectWorker.failed.connect(self.demoProjectThread.quit)
        self.demoProjectWorker.canceled.connect(self.demoProjectThread.quit)
        self.demoProjectThread.finished.connect(self.demoProjectThread.deleteLater)
        self.demoProjectThread.finished.connect(self._clearDemoProjectThread)
        self.demoProjectThread.start()
        return True

    def _clearDemoProjectThread(self):
        self.demoProjectWorker = None
        self.demoProjectThread = None

    def _onDemoProjectProgressChanged(self, progress, status):
        self.demoProjectProgress = progress
        self.demoProjectStatus = status
        if self.bridge:
            self.bridge.demoProjectProgressChanged.emit()

    @staticmethod
    def _formatDownloadSize(size):
        for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
            if size < 1024 or unit == "TiB":
                if unit == "B":
                    return f"{int(size)} B"
                return f"{size:.1f} {unit}"
            size /= 1024.0

    def _onDemoProjectDownloadProgressChanged(self, downloaded, total):
        self.demoProjectDownloadedSize = self._formatDownloadSize(downloaded)
        if total > 0:
            self.demoProjectTotalSize = self._formatDownloadSize(total)
        if self.bridge:
            self.bridge.demoProjectProgressChanged.emit()

    def _onDemoProjectCreated(self, result):
        configPath = self.core.configs.getProjectConfigPath(result)
        self.core.setConfig(
            "globals",
            "project_name",
            self.demoProjectName,
            configPath=configPath,
        )
        result = configPath
        result = self.core.changeProject(result)
        if not result:
            self._onDemoProjectFailed("The downloaded project could not be activated.")
            return

        self.creatingDemoProject = False
        self.demoProjectProgress = 100
        self.demoProjectStatus = "Demo project ready"
        self.demoProjectError = ""
        self.refreshStatus()
        if self.bridge:
            self.bridge.demoProjectProgressChanged.emit()

    def _onDemoProjectFailed(self, message):
        self.creatingDemoProject = False
        self.demoProjectStatus = "Demo project creation failed"
        self.demoProjectError = str(message)
        if self.bridge:
            self.bridge.demoProjectProgressChanged.emit()

    def _onDemoProjectCanceled(self):
        self.creatingDemoProject = False
        self.demoProjectStatus = "Demo project download canceled"
        self.demoProjectError = ""
        self.demoProjectDownloadedSize = ""
        self.demoProjectTotalSize = ""
        if self.bridge:
            self.bridge.demoProjectProgressChanged.emit()

    def cancelDemoProject(self):
        if not self.creatingDemoProject or not self.demoProjectWorker:
            return

        cancel = getattr(self.demoProjectWorker, "cancel", None)
        if callable(cancel):
            cancel()
            self.demoProjectStatus = "Canceling demo project download..."
            if self.bridge:
                self.bridge.demoProjectProgressChanged.emit()

    def openProject(self):
        self.core.projects.openProject(parent=self.dialog)
        self.refreshStatus()

    def getHelpUrl(self):
        return self.HELP_URL

    def openHelp(self):
        self.core.openWebsite("documentation")

    def openUrl(self, url):
        self.core.openWebsite(url)


class AvailablePluginsWorker(QObject):
    loaded = Signal(object)
    iconLoaded = Signal(str, str)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, internals):
        super(AvailablePluginsWorker, self).__init__()
        self.internals = internals

    @Slot()
    def run(self):
        try:
            serverData = self.internals.getHubData()
            self.loaded.emit(serverData)
            self._downloadIcons(serverData)
        except Exception as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()

    def _downloadIcons(self, serverData):
        if not isinstance(serverData, dict):
            return

        pluginItems = []
        for category in serverData.get("categories", []):
            if str(category.get("name", "")).strip().lower() == "plugins":
                pluginItems = category.get("items", [])
                break

        cacheDir = os.path.join(tempfile.gettempdir(), "Prism", "plugin-icons")
        os.makedirs(cacheDir, exist_ok=True)
        iconItems = []
        for item in pluginItems:
            if not isinstance(item, dict):
                continue

            pluginName = OnboardingController._getFirstPluginValue(
                item, ["pluginName"]
            )
            if pluginName:
                iconItems.append((pluginName, cacheDir))

        if not iconItems:
            return

        workerCount = min(8, len(iconItems))
        with ThreadPoolExecutor(max_workers=workerCount) as executor:
            futures = [
                executor.submit(self._downloadIcon, pluginName, cacheDir)
                for pluginName, cacheDir in iconItems
            ]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    self.iconLoaded.emit(*result)

    def _downloadIcon(self, pluginName, cacheDir):
        return self.internals.downloadPluginIcon(pluginName, cacheDir)


class DemoProjectsWorker(QObject):
    projectsLoaded = Signal(list)
    thumbnailLoaded = Signal(str, str)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, origin):
        self.core = origin.core
        super(DemoProjectsWorker, self).__init__()

    @Slot()
    def run(self):
        try:
            intPlug = self.core.getPlugin("PrismInternals")
            internals = intPlug.internals
            projects = internals.getDemoProjects()
            if not projects:
                raise RuntimeError("The demo project catalog response is invalid.")

            self.projectsLoaded.emit(projects)
            for project in projects:
                thumbnailUrl = project.get("thumbnailUrl")
                if not thumbnailUrl:
                    continue

                try:
                    thumbnailPath = internals.downloadDemoProjectThumbnail(
                        project["id"], thumbnailUrl
                    )
                except Exception:
                    continue

                self.thumbnailLoaded.emit(project["id"], thumbnailPath)
        except Exception as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()
