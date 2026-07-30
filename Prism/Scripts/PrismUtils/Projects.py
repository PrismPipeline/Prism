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
import sys
import logging
import shutil
import platform
import time
import fnmatch
import glob
import re
from collections import OrderedDict
from typing import Optional, Dict, List, Any, Union, Tuple

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class Projects(object):
    """Manages project operations including creation, loading, and configuration.
    
    This class handles all project-related functionality in Prism, including
    project creation, loading, switching, structure management, and configuration.
    It maintains project state, environment variables, and provides interfaces
    for project browser and settings.
    
    Attributes:
        core: Reference to PrismCore instance
        dlg_settings: Project settings dialog instance
        extraStructureItems (OrderedDict): Additional folder structure items
        environmentVariables (List[Dict]): Project environment variables
        validVariables (Dict): Valid project variables and their allowed values
        invalidVariables (Dict): Invalid project variables and their values
        previewWidth (int): Width for project preview images
        previewHeight (int): Height for project preview images
        
    Example:
        ```python
        projects = Projects(core)
        projects.createProject(name="MyProject", path="/path/to/project")
        projects.changeProject("/path/to/project/00_Pipeline/pipeline.yml")
        ```
    """

    def __init__(self, core: Any) -> None:
        """Initialize the Projects manager.
        
        Args:
            core: PrismCore instance providing core functionality
        """
        super(Projects, self).__init__()
        self.core = core
        self.dlg_settings = None
        self.extraStructureItems = OrderedDict([])
        self.environmentVariables = []
        self.validVariables = {}
        self.invalidVariables = {}
        self.previewWidth = 1280
        self.previewHeight = 720
        self.core.registerProtocolHandler("projects", self.protocolHandler)

    @err_catcher(name=__name__)
    def protocolHandler(self, path: str, qs: Dict[str, List[str]]) -> None:
        """Handle project protocol URLs for opening projects.
        
        Args:
            path: Protocol path (e.g., "/open")
            qs: Query string parameters dictionary
            
        Example:
            prism://projects/open?path=D%3A%5Cprojects%5Canim
        """
        if path == "/open":
            # urllib.parse.quote("D:\\projects\\anim")
            # prism://projects/open?path=D%3A%5Cprojects%5Canim
            if "path" not in qs:
                logger.warning("no path provided")
                return

            path = qs["path"][0]
            self.changeProject(path)
            self.core.projectBrowser()
            if not bool(QEventLoop().isRunning()):
                qapp = QApplication.instance()
                qapp.exec_()

    @err_catcher(name=__name__)
    def setProject(self, startup: Optional[bool] = None, openUi: str = "") -> None:
        """Open the project selection dialog.
        
        Args:
            startup: Whether this is called during startup. Defaults to None.
            openUi: UI to open after project selection. Defaults to empty string.
        """
        if eval(os.getenv("PRISM_DEBUG", "False")):
            try:
                del sys.modules["ProjectWidgets"]
            except:
                pass

        try:
            self.dlg_setProject.close()
        except:
            pass

        from PrismUtils import ProjectWidgets

        if startup is None:
            startup = self.core.status == "starting"

        self.dlg_setProject = ProjectWidgets.SetProject(core=self.core, openUi=openUi)
        if not startup:
            self.dlg_setProject.projectsUi.chb_startup.setVisible(False)

        if self.core.splashScreen and self.core.splashScreen.isVisible():
            self.core.splashScreen.hide()

        self.dlg_setProject.show()
        self.dlg_setProject.activateWindow()
        self.dlg_setProject.raise_()

    @err_catcher(name=__name__)
    def setPrism1Compatibility(self, state: bool) -> None:
        """Enable or disable Prism 1.x compatibility mode.
        
        Args:
            state: True to enable Prism 1.x compatibility, False to disable
        """
        if state:
            self.core.prism1Compatibility = True
            logger.debug("activating Prism 1 compatibility")
        else:
            self.core.prism1Compatibility = False
            logger.debug("deactivating Prism 1 compatibility")

    @err_catcher(name=__name__)
    def isPrism1Project(self, path: str) -> bool:
        """Check if a project path is a Prism 1.x project.
        
        Args:
            path: Path to project folder or config file
            
        Returns:
            True if this is a Prism 1.x project, False otherwise
        """
        if os.path.splitext(path)[1]:
            path = os.path.dirname(path)

        if os.path.basename(path) == "00_Pipeline":
            path = os.path.dirname(path)

        cfg = os.path.join(path, "00_Pipeline", "pipeline.yml")
        if os.path.exists(cfg):
            version = self.core.getConfig("globals", "prism_version", configPath=cfg)
            if self.core.compareVersions(version, "1.9") != "higher":
                return True

        cfg = os.path.join(path, "00_Pipeline", "pipeline.ini")
        if os.path.exists(cfg):
            return True

        return False

    @err_catcher(name=__name__)
    def openProject(self, parent: Optional[QWidget] = None) -> None:
        """Open a file dialog to browse and select an existing project.
        
        Args:
            parent: Parent widget for the dialog. Defaults to None.
        """
        parent = parent or self.core.messageParent
        if self.core.prismIni == "":
            path = QFileDialog.getExistingDirectory(
                parent, "Select existing project folder"
            )
        else:
            path = QFileDialog.getExistingDirectory(
                parent,
                "Select existing project folder",
                os.path.abspath(os.path.join(self.core.prismIni, os.pardir, os.pardir)),
            )

        if not path:
            return

        if self.isPrism1Project(path):
            self.setPrism1Compatibility(True)
            if os.path.basename(path) == "00_Pipeline":
                path = os.path.dirname(path)

            configPath = os.path.join(path, "00_Pipeline", "pipeline.yml")            
            self.core.configs.findDeprecatedConfig(configPath)
        else:
            if os.path.basename(path) == self.getDefaultPipelineFolder():
                path = os.path.dirname(path)

            self.setPrism1Compatibility(False)
            configPath = self.core.configs.getProjectConfigPath(path)

        if os.path.exists(configPath):
            try:
                self.dlg_setProject.close()
            except:
                pass
            self.changeProject(configPath, openUi="projectBrowser")
        else:
            configName = os.path.basename(configPath)
            msg = "Invalid project folder. If you changed the default pipeline folder name for this project please select the folder, which contains the \"%s\" file or set the \"PRISM_PROJECT_CONFIG_PATH\" environment variable." % configName
            self.core.popup(msg, parent=parent)

    @err_catcher(name=__name__)
    def changeProject(
        self,
        configPath: Optional[str] = None,
        openUi: str = "",
        settingsTab: Optional[Union[int, str]] = None,
        settingsType: Optional[str] = None,
        unset: bool = False,
        writeToConfig: Optional[bool] = None
    ) -> Optional[str]:
        """Change the active project.
        
        Args:
            configPath: Path to project config file. Defaults to None.
            openUi: UI to open after loading. Can be "projectBrowser", "stateManager", or "prismSettings". Defaults to empty string.
            settingsTab: Settings tab to open (if openUi="prismSettings"). Defaults to None.
            settingsType: Settings type to open. Defaults to None.
            unset: If True, unload the current project without loading a new one. Defaults to False.
            writeToConfig: Whether to write to config. Defaults to None.
            
        Returns:
            Project path if successful, None otherwise
        """
        if not unset:
            if configPath is None:
                return

            if not self.core.isStr(configPath):
                return

            if self.isPrism1Project(configPath):
                if not self.core.prism1Compatibility:
                    self.setPrism1Compatibility(True)
            else:
                if self.core.prism1Compatibility:
                    self.setPrism1Compatibility(False)

            if os.path.isdir(configPath):
                if os.path.basename(configPath) == self.getDefaultPipelineFolder():
                    configPath = os.path.dirname(configPath)

                configPath = self.core.configs.getProjectConfigPath(configPath)

            configPath = (
                self.core.configs.findDeprecatedConfig(configPath) or configPath
            )

            if not os.path.exists(configPath):
                self.core.popup(
                    "Cannot set project. File doesn't exist:\n\n%s" % configPath
                )
                return

            configPath = self.core.fixPath(configPath)
            configData = self.core.getConfig(configPath=configPath)
            if configData is None:
                logger.debug("unable to read project config: %s" % configPath)
                return

            projectPath = self.getProjectFolderFromConfigPath(configPath)
            projectName = self.core.getConfig(
                "globals", "project_name", configPath=configPath
            )
            projectVersion = (
                self.core.getConfig("globals", "prism_version", configPath=configPath)
                or ""
            )

            if not projectName:
                self.core.popup(
                    'The project config doesn\'t contain the "project_name" setting.\n\nCannot open project.'
                )
                return

            reqPlugins = (
                self.core.getConfig("globals", "required_plugins", configPath=configPath)
                or []
            )

            missing = []
            for reqPlugin in reqPlugins:
                if not reqPlugin:
                    continue

                if not self.core.getPlugin(reqPlugin):
                    unloadedPlugin = self.core.plugins.getUnloadedPlugin(reqPlugin)
                    if unloadedPlugin:
                        msg = "The plugin \"%s\" has to be loaded to open project \"%s\".\n\nDo you want to load plugin \"%s\" now?" % (reqPlugin, projectName, reqPlugin)
                        result = self.core.popupQuestion(msg)
                        if result == "Yes":
                            loadedPlugin = self.core.plugins.loadPlugin(unloadedPlugin.pluginPath)
                            if loadedPlugin:
                                continue

                    missing.append(reqPlugin)

            if missing:
                msg = "Cannot open project \"%s\".\n\nThe following plugins are required to open this project:\n\n" % projectName
                msg += "\n".join(missing)
                self.core.popup(msg)
                return

            disabledPlugins = self.core.getConfig("globals", "disabled_plugins", configPath=configPath) or []
            for disabledPlugin in disabledPlugins:
                if not disabledPlugin:
                    continue

                plug = self.core.getPlugin(disabledPlugin)
                if plug:
                    logger.debug("disabling plugin %s because it's disabled in this project" % disabledPlugin)
                    self.core.plugins.unloadPlugin(plugin=plug)

            expPrismVersions = self.core.getConfig(
                "globals",
                "expectedPrismVersions",
                dft="",
                configPath=configPath,
            )
            expPrismVersionMode = self.core.getConfig(
                "globals",
                "expectedPrismVersionMode",
                dft="Warn",
                configPath=configPath,
            )
            if expPrismVersions:
                allowedVersions = [v.strip() for v in expPrismVersions.split(",") if v.strip()]
                currentVersion = self.core.version
                if allowedVersions and currentVersion not in allowedVersions:
                    msg = "The project \"%s\" requires Prism version %s to be opened.\n\nThe currently running Prism version is %s." % (projectName, ", ".join(allowedVersions), currentVersion)
                    if self.core.appPlugin.pluginName != "Standalone":
                        msg += "\n\nPlease restart your DCC and open it with the correct Prism version."

                    if expPrismVersionMode == "Enforce":
                        self.core.popup(msg + "\n\nThe project cannot be opened.")
                        return
                    else:
                        self.core.popup(msg + "\n\nContinuing can have unexpected consequences.")

        delModules = []

        pipefolder = self.getPipelineFolder()
        for path in sys.path:
            if pipefolder and pipefolder in path:
                delModules.append(path)

        for modulePath in delModules:
            sys.path.remove(modulePath)

        if hasattr(self.core, "projectPath"):
            modulePath = os.path.join(
                self.getPipelineFolder(), "CustomModules", "Python"
            )
            if modulePath in sys.path:
                sys.path.remove(modulePath)

            curModules = list(sys.modules.keys())
            for i in curModules:
                if (
                    hasattr(sys.modules[i], "__file__")
                    and sys.modules[i].__file__ is not None
                    and modulePath in sys.modules[i].__file__
                ):
                    del sys.modules[i]

        self.core.unloadProjectPlugins()

        openPb = False
        openSm = False
        openPs = False

        quitOnLastWindowClosed = QApplication.quitOnLastWindowClosed()
        QApplication.setQuitOnLastWindowClosed(False)

        try:
            if getattr(self.core, "pb", None) and self.core.pb.isVisible():
                self.core.pb.close()
                openPb = True
        except:
            pass

        sm = self.core.getStateManager(create=False)
        if sm:
            if sm.isVisible():
                openSm = True

            self.core.closeSM()

        try:
            if hasattr(self, "dlg_setProject") and self.dlg_setProject.isVisible():
                self.dlg_setProject.close()
        except:
            pass

        try:
            if getattr(self.core, "ps", None) and self.core.ps.isVisible():
                if settingsTab is None:
                    settingsTab = self.core.ps.getCurrentCategory()

                if settingsType is None:
                    settingsType = self.core.ps.getCurrentSettingsType()

                self.core.ps.close()
                openPs = True
        except:
            pass

        try:
            if getattr(self, "dlg_settings", None) and self.dlg_settings.isVisible():
                self.dlg_settings.close()
        except:
            pass

        self.core.pb = None
        self.core.sm = None
        self.core.ps = None
        self.core.dv = None
        self.dlg_settings = None

        self.core.entities.removeEntityAction("masterVersionCheckProducts")
        self.core.entities.removeEntityAction("masterVersionCheckMedia")

        if unset:
            self.core.prismIni = ""
            self.core.setConfig("globals", "current project", "")
            if hasattr(self.core, "projectName"):
                del self.core.projectName
            if hasattr(self.core, "projectPath"):
                del self.core.projectPath
            if hasattr(self.core, "projectVersion"):
                del self.core.projectVersion
            self.core.useLocalFiles = False
            QApplication.setQuitOnLastWindowClosed(quitOnLastWindowClosed)
            return

        self.core.prismIni = configPath
        self.core.projectPath = projectPath
        self.core.projectName = projectName
        self.core.projectVersion = projectVersion

        self.core.configs.clearCache()
        result = self.refreshLocalFiles()
        if not result:
            QApplication.setQuitOnLastWindowClosed(quitOnLastWindowClosed)
            return

        if configPath != self.core.getConfig("globals", "current project") and (self.core.uiAvailable or writeToConfig):
            self.core.setConfig("globals", "current project", configPath)

        self.core.versionPadding = self.core.getConfig(
            "globals",
            "versionPadding",
            dft=self.core.versionPadding,
            configPath=configPath,
        )
        self.core.framePadding = self.core.getConfig(
            "globals", "framePadding", dft=self.core.framePadding, configPath=configPath
        )
        self.core.versionFormatVan = self.core.getConfig(
            "globals",
            "versionFormat",
            dft=self.core.versionFormatVan,
            configPath=configPath,
        )
        self.core.versionFormat = self.core.versionFormatVan.replace(
            "#", "%0{}d".format(self.core.versionPadding)
        )
        self.core.separateOutputVersionStack = not self.core.getConfig(
            "globals",
            "matchScenefileVersions",
            dft=False,
            configPath=configPath,
        )
        self.refreshUseEpisode(configPath=configPath)

        expPath = self.core.getConfig(
            "globals",
            "expectedPrjPath",
            dft="",
            configPath=configPath,
        )

        if expPath and expPath.strip("\\") != self.core.projectPath.strip("\\") and os.getenv("PRISM_SKIP_PROJECT_PATH_WARNING", "0") != "1":
            msg = "This project should be loaded from the following path:\n\n%s\n\nCurrently it is loaded from this path:\n\n%s\n\nContinuing can have unexpected consequences." % (expPath, self.core.projectPath)
            self.core.popup(msg)

        self.core._scenePath = None
        self.core._shotPath = None
        self.core._sequencePath = None
        self.core._episodePath = None
        self.core._assetPath = None
        self.core._texturePath = None

        self.core.callbacks.registerProjectHooks()
        self.unloadProjectEnvironment(beforeRefresh=True)
        self.refreshProjectEnvironment()
        if self.core.products.getUseMaster():
            self.core.entities.addEntityAction(
                key="masterVersionCheckProducts",
                types=["asset", "shot"],
                function=self.core.products.checkMasterVersions,
                label="Check Product Master Versions..."
            )
        else:
            self.core.entities.removeEntityAction("masterVersionCheckProducts")

        if self.core.mediaProducts.getUseMaster():
            self.core.entities.addEntityAction(
                key="masterVersionCheckMedia",
                types=["asset", "shot"],
                function=self.core.mediaProducts.checkMasterVersions,
                label="Check Media Master Versions..."
            )
        else:
            self.core.entities.removeEntityAction("masterVersionCheckMedia")

        logger.debug("Loaded project " + self.core.projectPath)

        modulePath = os.path.join(self.getPipelineFolder(), "CustomModules", "Python")
        if not os.path.exists(modulePath):
            try:
                os.makedirs(modulePath)
            except Exception as e:
                pass

        if os.path.exists(modulePath) and modulePath not in sys.path:
            sys.path.append(modulePath)

        pluginPath = self.getPluginFolder()
        if os.path.exists(pluginPath):
            if os.getenv("PRISM_LOAD_PRJ_PLUGINS_RECURSIVE", "0") == "1":
                self.core.plugins.loadPlugins(directories=[pluginPath], recursive=True)
            else:
                self.core.plugins.loadPlugins(directories=[pluginPath], recursive=False, singleFilePlugins=True)

        self.setRecentPrj(configPath)
        self.core.updateProjectEnvironment()
        if self.getCommandsEnabled():
            self.core.checkCommands()

        self.core.callback(
            name="onProjectChanged",
            args=[self.core],
        )

        if self.core.uiAvailable:
            if openPb or openUi == "projectBrowser":
                self.core.projectBrowser()

            if openSm or openUi == "stateManager":
                self.core.stateManager()

            if openPs or openUi == "prismSettings":
                self.core.prismSettings(tab=settingsTab, settingsType=settingsType, reload_module=False)

        structure = self.getProjectStructure()
        if os.getenv("PRISM_ENFORCE_FOLDER_STRUCTURE_RULES", "1") == "1":
            result = self.validateFolderStructure(structure)
            if result is not True:
                msg = "The project structure is invalid. Please update the project settings."
                r = self.core.popupQuestion(msg, buttons=["Open Project Settings...", "Close"], default="Open Project Settings...", escapeButton="Close", icon=QMessageBox.Warning)
                if r == "Open Project Settings...":
                    self.core.prismSettings(tab="Folder Structure", settingsType="Project")

        QApplication.setQuitOnLastWindowClosed(quitOnLastWindowClosed)
        return self.core.projectPath

    @err_catcher(name=__name__)
    def getCommandsEnabled(self):
        return os.getenv("PRISM_ENABLE_COMMANDS", "1") == "1"

    @err_catcher(name=__name__)
    def getUseEpisodes(self) -> bool:
        """Get whether episodes are enabled for this project.
        
        Returns:
            True if episodes are enabled, False otherwise
        """
        useEpisodes = self.core.getConfig(
            "globals",
            "useEpisodes",
            config="project",
        ) or False
        return useEpisodes

    @err_catcher(name=__name__)
    def refreshUseEpisode(self, configPath: Optional[str] = None) -> None:
        """Refresh the episodes project structure based on project config.
        
        Args:
            configPath: Path to config file. Uses current project if None. Defaults to None.
        """
        if configPath:
            config = None
        else:
            config = "project"

        useEpisodes = self.core.getConfig(
            "globals",
            "useEpisodes",
            dft=False,
            configPath=configPath,
            config=config
        )
        if useEpisodes:
            data = {
                "label": "Episodes",
                "key": "@episode_path@",
                "value": "@project_path@/03_Production/Shots/@episode@",
                "requires": ["project_path"],
                "idx": 2,
            }
            self.core.projects.addProjectStructureItem("episodes", data)
        else:
            self.core.projects.removeProjectStructureItem("episodes")

    @err_catcher(name=__name__)
    def refreshLocalFiles(self) -> bool:
        """Refresh local files settings and paths.
        
        Returns:
            True if successful, False if operation was cancelled
        """
        self.core.useLocalFiles = self.getUseLocalFiles()
        if self.core.useLocalFiles:
            if self.core.getConfig("localfiles", self.core.projectName) is not None:
                self.core.localProjectPath = self.core.getConfig(
                    "localfiles", self.core.projectName
                )
            else:
                result = self.core.getLocalPath()
                if not result:
                    self.core.changeProject(unset=True)
                    return False

            self.core.localProjectPath = self.core.fixPath(self.core.localProjectPath)
            if not self.core.localProjectPath.endswith(os.sep):
                self.core.localProjectPath += os.sep

        return True

    @err_catcher(name=__name__)
    def unloadProjectEnvironment(self, beforeRefresh: bool = False) -> None:
        """Unload project environment variables.
        
        Args:
            beforeRefresh: Whether this is called before refreshing environment. Defaults to False.
        """
        for item in self.environmentVariables:
            if item["orig"] is None:
                if item["key"] in os.environ:
                    del os.environ[item["key"]]
            else:
                os.environ[item["key"]] = item["orig"]

        self.core.callback(name="updatedEnvironmentVars", args=["unloadProject", self.environmentVariables, beforeRefresh])

    @err_catcher(name=__name__)
    def getProjectEnvironment(self, appPluginName: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get project environment variables.
        
        Args:
            appPluginName: Name of application plugin. Uses current app if None. Defaults to None.
            
        Returns:
            List of environment variable dictionaries with keys: 'key', 'value', 'orig'
        """
        variables = self.core.getConfig(
            "environmentVariables", config="project", dft={}
        )
        envVars = []
        if not appPluginName:
            if getattr(self.core, "appPlugin", None):
                appPluginName = self.core.appPlugin.pluginName
            else:
                appPluginName = ""

        for key in variables:
            val = os.path.expandvars(str(variables[key]))
            res = self.core.callback(name="expandEnvVar", args=[val])
            for r in res:
                if r:
                    val = r

            if key.lower().startswith("ocio") and appPluginName.lower() == key.split("_")[-1]:
                key = "OCIO"

            item = {
                "key": str(key),
                "value": val,
                "orig": os.getenv(key),
            }
            envVars.append(item)

        return envVars

    @err_catcher(name=__name__)
    def refreshProjectEnvironment(self) -> None:
        """Refresh and apply project environment variables."""
        self.environmentVariables = []
        envVars = self.getProjectEnvironment()
        for envVar in envVars:
            self.environmentVariables.append(envVar)
            os.environ[envVar["key"]] = envVar["value"]

        self.core.callback(name="updatedEnvironmentVars", args=["refreshProject", self.environmentVariables])

    @err_catcher(name=__name__)
    def getUseLocalFiles(self, projectConfig: Optional[str] = None) -> bool:
        """Get whether local files are enabled for this project.
        
        Args:
            projectConfig: Path to project config. Uses current project if None. Defaults to None.
            
        Returns:
            True if local files are enabled, False otherwise
        """
        if not projectConfig:
            projectConfig = self.core.prismIni

        prjUseLocal = self.core.getConfig(
            "globals", "uselocalfiles", dft=False, configPath=projectConfig
        )
        userUseLocal = self.core.getConfig(
            "useLocalFiles", self.core.projectName, dft="inherit"
        )
        if userUseLocal == "inherit":
            useLocal = prjUseLocal
        elif userUseLocal == "on":
            useLocal = True
        else:
            useLocal = False

        return useLocal

    @err_catcher(name=__name__)
    def getDefaultLocalPath(self, projectName: Optional[str] = None) -> str:
        """Get the default local files path for a project.
        
        Args:
            projectName: Project name. Uses current project if None. Defaults to None.
            
        Returns:
            Default local path string
        """
        if not projectName:
            if hasattr(self.core, "projectName"):
                projectName = self.core.projectName
            else:
                projectName = ""

        if platform.system() == "Windows":
            base = os.path.join(
                self.core.getWindowsDocumentsPath(), "LocalProjects"
            )
        elif platform.system() == "Linux":
            base = os.path.join(
                os.path.expanduser("~"), "Documents", "LocalProjects"
            )
        elif platform.system() == "Darwin":
            base = os.path.join(
                os.path.expanduser("~"), "Documents", "LocalProjects"
            )

        envDft = os.getenv("PRISM_DFT_LOCAL_PATH")
        if envDft:
            base = envDft

        defaultLocalPath = os.path.normpath(os.path.join(base, projectName))
        return defaultLocalPath

    @err_catcher(name=__name__)
    def setFaroriteProject(self, path: str, favorite: bool = True) -> None:
        """Mark a project as favorite or unfavorite.
        
        Args:
            path: Path to project config file
            favorite: True to mark as favorite, False to unmark. Defaults to True.
        """
        path = self.core.fixPath(path)
        changed = False
        projects = self.core.getConfig("recent_projects", config="user", dft=[])
        for project in projects:
            if project["configPath"] == path and project.get("favorite", False) != favorite:
                project["favorite"] = favorite
                changed = True

        if changed:
            self.core.setConfig(
                param="recent_projects", val=projects, config="user"
            )

    @err_catcher(name=__name__)
    def setRecentPrj(self, path: str, action: str = "add") -> None:
        """Add or remove a project from recent projects list.
        
        Args:
            path: Path to project config file
            action: "add" to add to recent, "remove" to remove. Defaults to "add".
        """
        path = self.core.fixPath(path)

        recentProjects = self.getRecentProjects(includeCurrent=True)
        if (
            recentProjects
            and path == recentProjects[0]["configPath"]
            and action == "add"
        ):
            return

        newRecenetProjects = []

        for prj in recentProjects:
            if prj["configPath"] != path:
                newRecenetProjects.append(prj)

        if action == "add":
            prjData = {"configPath": path}
            prjData["name"] = self.core.getConfig(
                "globals", "project_name", configPath=path
            )
            prjData["date"] = time.time()
            newRecenetProjects = [prjData] + newRecenetProjects
        elif action == "remove":
            prjName = self.core.getConfig(
                "globals", "project_name", configPath=path
            )
            if prjName:
                rSection = "recent_files_" + prjName
                self.core.setConfig(cat=rSection, delete=True, config="user")
                param = "expandedSequences_" + prjName
                self.core.setConfig(cat="browser", param=param, delete=True, config="user")
                param = "expandedAssets_" + prjName
                self.core.setConfig(cat="browser", param=param, delete=True, config="user")
                self.core.setConfig(cat="useLocalFiles", param=prjName, delete=True, config="user")

        self.core.setConfig(param="recent_projects", val=newRecenetProjects)

    @err_catcher(name=__name__)
    def getRecentProjects(self, includeCurrent: bool = False) -> List[Dict[str, Any]]:
        """Get list of recent projects.
        
        Args:
            includeCurrent: Whether to include currently active project. Defaults to False.
            
        Returns:
            List of project dictionaries with keys: 'configPath', 'name', 'date', 'favorite'
        """
        favProjects = []
        validProjects = []
        deprecated = False
        projects = self.core.getConfig("recent_projects", config="user", dft=[])

        for project in projects:
            if self.core.isStr(project):
                if not project or not self.core.isStr(project):
                    continue

                if not includeCurrent and project == self.core.prismIni:
                    continue

                configPath = (
                    os.path.splitext(self.core.fixPath(project))[0]
                    + self.core.configs.preferredExtension
                )
                prjData = {"configPath": configPath}
                prjData["name"] = self.core.getConfig(
                    "globals", "project_name", configPath=configPath
                )
                validProjects.append(prjData)
                deprecated = True
            else:
                if not project or not project["configPath"]:
                    continue

                if not self.core.isStr(project["configPath"]):
                    continue

                if not includeCurrent and project["configPath"] == self.core.prismIni:
                    continue

                if project.get("favorite", False):
                    favProjects.append(project)
                else:
                    validProjects.append(project)

        validProjects = favProjects + validProjects
        if deprecated:
            self.core.setConfig(
                param="recent_projects", val=validProjects, config="user"
            )

        return validProjects

    @err_catcher(name=__name__)
    def getAvailableProjects(self, includeCurrent: bool = False) -> List[Dict[str, Any]]:
        """Get list of available projects.
        
        Args:
            includeCurrent: Whether to include currently active project. Defaults to False.
            
        Returns:
            List of project dictionaries
        """
        projects = self.getRecentProjects(includeCurrent=includeCurrent)
        for project in projects:
            project["source"] = "recent"

        return projects

    @err_catcher(name=__name__)
    def createProjectDialog(
        self,
        name: Optional[str] = None,
        path: Optional[str] = None,
        settings: Optional[Dict] = None,
        enforcedSettings: Optional[Dict] = None
    ) -> Any:
        """Open the create project dialog or create project directly.
        
        Args:
            name: Project name. Defaults to None.
            path: Project path. Defaults to None.
            settings: Project settings. Defaults to None.
            enforcedSettings: Settings that cannot be changed. Defaults to None.
            
        Returns:
            CreateProject dialog instance
        """
        settings = settings or {}
        if eval(os.getenv("PRISM_DEBUG", "False")):
            try:
                del sys.modules["ProjectWidgets"]
            except:
                pass

        try:
            self.cp.close()
        except:
            pass

        from PrismUtils import ProjectWidgets

        if name is not None and path is not None:
            return ProjectWidgets.CreateProject(
                core=self.core, name=name, path=path, settings=settings, enforcedSettings=enforcedSettings
            )
        else:
            self.cp = ProjectWidgets.CreateProject(core=self.core)
            self.cp.show()

        return self.cp

    @err_catcher(name=__name__)
    def getDefaultProjectSettings(self) -> OrderedDict:
        """Get default project settings with standard structure and configuration.
        
        Returns:
            OrderedDict containing default project settings
        """
        dftDepsAsset = [
            {"name": "Concept", "abbreviation": "cpt", "defaultTasks": ["Concept"]},
            {"name": "Modeling", "abbreviation": "mod", "defaultTasks": ["Modeling"]},
            {"name": "Surfacing", "abbreviation": "surf", "defaultTasks": ["Surfacing"]},
            {"name": "Rigging", "abbreviation": "rig", "defaultTasks": ["Rigging"]},
        ]

        dftDepsShot = [
            {"name": "Layout", "abbreviation": "lay", "defaultTasks": ["Layout"]},
            {"name": "Animation", "abbreviation": "anm", "defaultTasks": ["Animation"]},
            {"name": "CharFX", "abbreviation": "cfx", "defaultTasks": ["CharacterEffects"]},
            {"name": "FX", "abbreviation": "fx", "defaultTasks": ["Effects"]},
            {"name": "Lighting", "abbreviation": "lgt", "defaultTasks": ["Lighting"]},
            {"name": "Compositing", "abbreviation": "cmp", "defaultTasks": ["Compositing"]},
        ]
        dftTaskPresetsAsset = self.getDftAssetTaskPresets()
        dftTaskPresetsShot = self.getDftShotTaskPresets()
        dftProductTags = self.core.products.getDefaultProjectProductTags()

        structure = self.getStructureValues(self.getDefaultProjectStructure())
        settings = OrderedDict(
            [
                (
                    "globals",
                    OrderedDict(
                        [
                            ("project_name", ""),
                            ("prism_version", self.core.version),
                            ("departments_asset", dftDepsAsset),
                            ("departments_shot", dftDepsShot),
                            ("taskpresets_asset", dftTaskPresetsAsset),
                            ("taskpresets_shot", dftTaskPresetsShot),
                            ("uselocalfiles", False),
                            ("track_dependencies", "publish"),
                            ("checkframerange", True),
                            ("forcefps", False),
                            ("fps", 25),
                            ("forceversions", False),
                            ("forceResolution", False),
                            ("resolution", [1920, 1080]),
                            (
                                "resolutionPresets",
                                [
                                    "3840x2160",
                                    "1920x1080",
                                    "1280x720",
                                    "960x540",
                                    "640x360",
                                ],
                            ),
                            ("requirePublishComment", True),
                            ("publishCommentLength", 3),
                            ("versionPadding", 4),
                            ("defaultImportStateName", "{entity}_{product}_{version}{#}"),
                            ("useStrictAssetDetection", False),
                        ]
                    ),
                ),
                ("folder_structure", structure),
                (
                    "defaultpasses",
                    OrderedDict([]),
                ),
                (
                    "products",
                    OrderedDict(
                        [
                            ("tags", dftProductTags)
                        ]
                    ),
                ),
            ]
        )

        for pluginName in self.core.getPluginNames():
            passes = self.core.getPluginData(pluginName, "renderPasses")
            if type(passes) == dict:
                settings["defaultpasses"].update(passes)

        return settings

    @err_catcher(name=__name__)
    def createProject(
        self,
        name: str,
        path: str,
        settings: Optional[Dict] = None,
        preset: str = "Default",
        image: Optional[QPixmap] = None,
        structure: Optional[Dict] = None,
        parent: Optional[QWidget] = None
    ) -> Optional[str]:
        """Create a new Prism project.
        
        Args:
            name: Project name
            path: Path where project will be created
            settings: Project settings dictionary. Defaults to None.
            preset: Preset name to use. Defaults to "Default".
            image: Preview image for project. Defaults to None.
            structure: Folder structure. Defaults to None.
            parent: Parent widget for dialogs. Defaults to None.
            
        Returns:
            Path to created config file if successful, None otherwise
        """
        prjName = name
        prjPath = path.strip(" ")
        settings = settings or {}

        if preset:
            preset = self.getPreset(name=preset)
            projectSettings = preset["settings"]
        else:
            projectSettings = {}

        self.core.configs.updateNestedDicts(projectSettings, settings)
        projectSettings["globals"]["project_name"] = prjName
        projectSettings["globals"]["prism_version"] = self.core.version

        for locType in ["export_paths", "render_paths"]:
            for loc in list(projectSettings.get(locType, {})):
                if "@project_name@" in projectSettings[locType][loc]:
                    newLocPath = projectSettings[locType][loc].replace("@project_name@", prjName)
                    projectSettings[locType][loc] = newLocPath

                if "@project_name@" in loc:
                    newLoc = loc.replace("@project_name@", prjName)
                    projectSettings[locType][newLoc] = projectSettings[locType][loc]
                    del projectSettings[locType][loc]

        # check valid project name
        if not prjName:
            self.core.popup("The project name is invalid.")
            return

        # create project folder
        if not os.path.isabs(prjPath):
            self.core.popup("The project path is invalid.")
            return

        if not os.path.exists(prjPath):
            try:
                os.makedirs(prjPath)
            except Exception as e:
                self.core.popup("The project folder could not be created.\n\n(%s)" % str(e), parent=parent)
                return

        else:
            try:
                content = os.listdir(prjPath)
            except Exception as e:
                self.core.popup("The project folder could not be accessed.\n\n(%s)" % str(e), parent=parent)
                return

            if content:
                msg = "The project folder is not empty:\n\n%s\n\nHow do you want to continue?" % prjPath
                result = self.core.popupQuestion(
                    msg,
                    icon=QMessageBox.Warning,
                    buttons=[
                        "Create project in existing folder",
                        "Clear folder before creating the project",
                        "Cancel",
                    ],
                    parent=parent
                )
                if result == "Cancel":
                    return
                elif result == "Clear folder before creating the project":
                    while self.core.countFilesInFolder(prjPath, maximum=1000) >= 1000:
                        msg = "There are more than 1000 files in the project folder.\n\n%s\n\nAs a security measurement Prism cannot delete this folder.\nDelete the folder manually in your file explorer to continue." % prjPath
                        result = self.core.popupQuestion(
                            msg,
                            icon=QMessageBox.Warning,
                            buttons=["Continue", "Cancel"],
                            parent=parent
                        )
                        if result == "Continue":
                            continue
                        elif result == "Cancel":
                            return

                    while (self.core.getFolderSize(prjPath)["size"] / 1024.0 / 1024.0) >= 1:
                        msg = "The project folder size is more than 1 GB.\n\n%s\n\nAs a security measurement Prism cannot delete this folder.\nDelete the folder manually in your file explorer to continue." % prjPath
                        result = self.core.popupQuestion(
                            msg,
                            icon=QMessageBox.Warning,
                            buttons=["Continue", "Cancel"],
                            parent=parent
                        )
                        if result == "Continue":
                            continue
                        elif result == "Cancel":
                            return

                    while os.path.exists(prjPath):
                        msg = "Are you really sure you want to delete this folder?\n\n%s\n\nThis will PERMANENTLY REMOVE the folder and it's content.\nThis cannot be undone!" % prjPath
                        result = self.core.popupQuestion(
                            msg,
                            icon=QMessageBox.Warning,
                            buttons=["Yes", "No"],
                            parent=parent
                        )
                        if result != "Yes":
                            return False

                        try:
                            shutil.rmtree(prjPath)
                        except Exception as e:
                            logger.debug(str(e))
                            msg = "Failed to remove folder:\n\n%s" % prjPath
                            result = self.core.popupQuestion(
                                msg,
                                buttons=["Retry", "Cancel"],
                                escapeButton="Cancel",
                                icon=QMessageBox.Warning,
                            )
                            if result == "Cancel":
                                return False

        if structure:
            result = self.createProjectStructure(prjPath, structure)
            if not result:
                return
        else:
            try:
                self.core.copyFolder(preset["path"], prjPath)
            except Exception as e:
                logger.debug(e)
                self.core.popup(
                    "Could not copy folders to %s.\n\n%s" % (prjPath, str(e))
                )
                return

        # create config
        structure = self.getProjectStructure(projectStructure=projectSettings["folder_structure"])
        context = {"project_path": prjPath}
        pipelineDir = self.getResolvedProjectStructurePath("pipeline", context=context, structure=structure)
        configPath = self.core.configs.getProjectConfigPath(prjPath, pipelineDir=pipelineDir, useEnv=False)

        self.core.setConfig(data=projectSettings, configPath=configPath, updateNestedData=False)
        if image:
            imagePath = self.getProjectImage(prjPath, validate=False, structure=structure)
            self.core.media.savePixmap(image, imagePath)

        logger.debug("project created: %s - %s" % (prjName, prjPath))

        self.core.callback(
            name="onProjectCreated",
            args=[self, prjPath, prjName],
        )
        return configPath

    @err_catcher(name=__name__)
    def getFolderStructureFromPath(self, projectPath: str, simple: bool = False) -> Dict[str, Any]:
        """Build a folder structure dictionary from an existing project path.
        
        Args:
            projectPath: Path to project root
            simple: If True, include only essential folders. Defaults to False.
            
        Returns:
            Dictionary representing folder structure with 'name' and 'children' keys
        """
        rootEntity = {
            "name": "root",
            "children": [],
        }
        entities = {projectPath: rootEntity}

        if os.path.exists(projectPath):
            for root, folders, files in os.walk(projectPath):
                if root not in entities:
                    continue

                parent = entities[root]
                for folder in folders:
                    path = os.path.join(root, folder)
                    entity = {
                        "name": folder,
                        "children": [],
                    }
                    parent["children"].append(entity)
                    entities[path] = entity

                if simple:
                    if root == projectPath:
                        folders[:] = [f for f in folders if f == "00_Pipeline"]

                    if root == os.path.join(projectPath, "00_Pipeline"):
                        folders[:] = [f for f in folders if f not in ["Assetinfo", "Attachments", "Commands", "Shotinfo"]]
                        files[:] = [f for f in files if not f.startswith("ErrorLog_")]

                for file in files:
                    path = os.path.join(root, file)
                    entity = {
                        "name": file,
                        "path": path,
                    }
                    parent["children"].append(entity)
                    entities[path] = entity

        return rootEntity

    @err_catcher(name=__name__)
    def createProjectStructure(self, path: str, entity: Dict[str, Any]) -> bool:
        """Recursively create project folder structure.
        
        Args:
            path: Base path for structure
            entity: Entity dictionary with 'name' and 'children' keys
            
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except FileExistsError:
                pass
            except Exception as e:
                msg = "Failed to create folder:\n\n%s\n\nError: %s" % (path, e)
                self.core.popup(msg)
                return False

        for childEntity in entity["children"]:
            if "children" in childEntity:
                folderPath = os.path.join(path, childEntity["name"])
                self.createProjectStructure(folderPath, childEntity)
            else:
                try:
                    shutil.copy2(childEntity["path"], path)
                except PermissionError:
                    shutil.copy(childEntity["path"], path)

        return True

    @err_catcher(name=__name__)
    def ensureProject(self, openUi: str = "") -> bool:
        """Ensure a project is loaded, prompting user if needed.
        
        Args:
            openUi: UI to open after loading project. Defaults to empty string.
            
        Returns:
            True if project is loaded, False otherwise
        """
        if getattr(self.core, "projectPath", None) and os.path.exists(
            self.core.prismIni
        ):
            return True

        if "prism_project" in os.environ and os.path.exists(
            os.environ["prism_project"]
        ):
            curPrj = os.environ["prism_project"]
        else:
            curPrj = self.core.getConfig("globals", "current project")

        if curPrj:
            if self.changeProject(curPrj):
                return True

        self.setProject(openUi=openUi)
        hasPrj = getattr(self.core, "projectPath", None) and os.path.exists(
            self.core.prismIni
        )
        return hasPrj

    @err_catcher(name=__name__)
    def hasActiveProject(self) -> bool:
        """Check if a project is currently active.
        
        Returns:
            True if a project is active, False otherwise
        """
        return hasattr(self.core, "projectPath")

    @err_catcher(name=__name__)
    def getProjectResolution(self) -> Optional[List[int]]:
        """Get project resolution if forced resolution is enabled.
        
        Returns:
            List of [width, height] if forced, None otherwise
        """
        forceRes = self.core.getConfig(
            "globals", "forceResolution", configPath=self.core.prismIni
        )
        if not forceRes:
            return

        pRes = self.core.getConfig(
            "globals", "resolution", configPath=self.core.prismIni
        )
        return pRes

    @err_catcher(name=__name__)
    def getResolutionPresets(self) -> List[str]:
        """Get available resolution presets for the project.
        
        Returns:
            List of resolution preset strings (e.g., "1920x1080")
        """
        dftResPresets = [
            "3840x2160",
            "1920x1080",
            "1280x720",
            "960x540",
            "640x360",
        ]

        presets = list(self.core.getConfig(
            "globals",
            "resolutionPresets",
            configPath=self.core.prismIni,
            dft=dftResPresets,
        ))

        prjRes = self.getProjectResolution()
        if prjRes:
            presets.insert(0, "Project (%sx%s)" % (prjRes[0], prjRes[1]))

        return presets

    @err_catcher(name=__name__)
    def openProjectSettings(
        self,
        tab: Union[int, str] = 0,
        restart: bool = False,
        reload_module: bool = False,
        config: Optional[str] = None,
        projectData: Optional[Dict] = None
    ) -> Any:
        """Open the project settings dialog.
        
        Args:
            tab: Tab to open (index or name). Defaults to 0.
            restart: Force restart of dialog. Defaults to False.
            reload_module: Reload the settings module. Defaults to False.
            config: Path to config file. Defaults to None.
            projectData: Project data dictionary. Defaults to None.
            
        Returns:
            ProjectSettings dialog instance
        """
        if not projectData:
            config = config or self.core.prismIni

        if self.dlg_settings and self.dlg_settings.isVisible():
            self.dlg_settings.close()

        if not self.dlg_settings or self.core.debugMode or restart or reload_module:
            if self.core.debugMode or reload_module:
                try:
                    del sys.modules["ProjectSettings"]
                except:
                    pass

            import ProjectSettings

            self.dlg_settings = ProjectSettings.ProjectSettings(
                core=self.core, projectConfig=config, projectData=projectData
            )

        self.dlg_settings.show()
        if isinstance(tab, int):
            self.dlg_settings.tw_settings.setCurrentIndex(tab)
        else:
            for idx in range(self.dlg_settings.tw_settings.count()):
                if self.dlg_settings.tw_settings.tabText(idx) == tab:
                    self.dlg_settings.tw_settings.setCurrentIndex(idx)

        return self.dlg_settings

    @err_catcher(name=__name__)
    def getDefaultPipelineFolder(self) -> str:
        """Get the default pipeline folder name.
        
        Returns:
            Pipeline folder name ("00_Pipeline" for Prism 1.x or from environment)
        """
        if self.core.prism1Compatibility:
            return "00_Pipeline"

        return os.getenv("PRISM_PROJECT_PIPELINE_FOLDER", "00_Pipeline")

    @err_catcher(name=__name__)
    def getPipelineFolder(self, projectPath: Optional[str] = None, structure: Optional[Dict] = None) -> str:
        """Get the full path to the pipeline folder.
        
        Args:
            projectPath: Project path. Uses current project if None. Defaults to None.
            structure: Project structure. Defaults to None.
            
        Returns:
            Full path to pipeline folder
        """
        if not projectPath:
            if not hasattr(self.core, "projectPath"):
                return ""

            projectPath = self.core.projectPath

            if not structure:
                structure = self.getProjectStructure()

        folder = self.getResolvedProjectStructurePath(
            "pipeline", context={"project_path": projectPath}, structure=structure
        )
        if not folder:
            folder = self.getDefaultPipelineFolder()

        folderpath = os.path.join(projectPath, folder)
        return folderpath

    @err_catcher(name=__name__)
    def getProjectFolderFromConfigPath(self, configPath: str, norm: bool = False) -> str:
        """Extract project folder path from config file path.
        
        Args:
            configPath: Path to config file
            norm: Whether to normalize the path. Defaults to False.
            
        Returns:
            Project folder path
        """
        projectPath = None
        projectStructure = self.core.getConfig(
            "folder_structure", configPath=configPath
        )
        if projectStructure:
            pipelineTemplate = projectStructure["pipeline"]["value"]
            data = self.extractKeysFromPath(os.path.dirname(configPath), pipelineTemplate)
            if data and data.get("project_path"):
                projectPath = data["project_path"]
        
        if not projectPath:
            projectPath = str(os.path.abspath(
                os.path.join(configPath, os.pardir, os.pardir)
            ))

        if not projectPath.endswith(os.sep):
            projectPath += os.sep

        if norm:
            projectPath = os.path.normpath(projectPath)

        return projectPath

    @err_catcher(name=__name__)
    def getPluginFolder(self) -> str:
        """Get the project plugins folder path.
        
        Returns:
            Path to project plugins folder, empty string if no project loaded
        """
        if not getattr(self.core, "projectPath", None):
            pluginPath = ""
        else:
            pluginPath = os.path.join(self.getPipelineFolder(), "Plugins")

        return pluginPath

    @err_catcher(name=__name__)
    def getHookFolder(self) -> str:
        """Get the project hooks folder path.
        
        Returns:
            Path to hooks folder
        """
        return os.path.join(self.getPipelineFolder(), "Hooks")

    @err_catcher(name=__name__)
    def getFallbackFolder(self) -> str:
        """Get the project fallbacks folder path.
        
        Returns:
            Path to fallbacks folder
        """
        return os.path.join(self.getPipelineFolder(), "Fallbacks")

    @err_catcher(name=__name__)
    def getConfigFolder(self) -> str:
        """Get the project configs folder path.
        
        Returns:
            Path to configs folder
        """
        return os.path.join(self.getPipelineFolder(), "Configs")

    @err_catcher(name=__name__)
    def getPresetFolder(self) -> str:
        """Get the project presets folder path.
        
        Returns:
            Path to presets folder
        """
        return os.path.join(self.getPipelineFolder(), "Presets")

    @err_catcher(name=__name__)
    def getDefaultProjectStructure(self) -> OrderedDict:
        """Get the default project folder structure template.
        
        Returns:
            OrderedDict containing default folder structure definitions
        """
        structure = OrderedDict([])
        structure["pipeline"] = {
            "label": "Pipeline",
            "key": "@pipeline_path@",
            "value": "@project_path@/00_Pipeline",
            "requires": ["project_path"],
        }
        structure["assets"] = {
            "label": "Assets",
            "key": "@entity_path@",
            "value": "@project_path@/03_Production/Assets/@asset_path@",
            "requires": ["project_path", "asset_path"],
        }
        structure["sequences"] = {
            "label": "Sequences",
            "key": "@sequence_path@",
            "value": "@project_path@/03_Production/Shots/@sequence@",
            "requires": ["sequence"],
        }
        structure["shots"] = {
            "label": "Shots",
            "key": "@entity_path@",
            "value": "@sequence_path@/@shot@",
            "requires": [["sequence_path", "sequence"], "shot"],
        }
        structure["textures"] = {
            "label": "Textures",
            "key": "@entity_path@",
            "value": "@project_path@/04_Resources/Textures",
            "requires": ["project_path"],
        }
        structure["departments"] = {
            "label": "Departments",
            "key": "@department_path@",
            "value": "@entity_path@/Scenefiles/@department@",
            "requires": ["entity_path", "department"],
        }
        structure["tasks"] = {
            "label": "Tasks",
            "key": "@task_path@",
            "value": "@department_path@/@task@",
            "requires": ["department_path", "task"],
        }
        structure["assetScenefiles"] = {
            "label": "Asset Scenefiles",
            "key": "@scenefile_path@",
            "value": "@task_path@/@asset@_@task@_@version@@extension@",
            "requires": ["task_path", "version"],
        }
        structure["shotScenefiles"] = {
            "label": "Shot Scenefiles",
            "key": "@scenefile_path@",
            "value": "@task_path@/@sequence@-@shot@_@task@_@version@@extension@",
            "requires": ["task_path", "version"],
        }
        structure["products"] = {
            "label": "Products",
            "key": "@product_path@",
            "value": "@entity_path@/Export/@product@",
            "requires": ["entity_path", "product"],
        }
        structure["productVersions"] = {
            "label": "Productversions",
            "key": "@productversion_path@",
            "value": "@product_path@/@version@@_(wedge)@",
            "requires": ["product_path", "version"],
        }
        structure["productFilesAssets"] = {
            "label": "Asset Productfiles",
            "key": "@productfile_path@",
            "value": "@productversion_path@/@asset@_@product@_@version@@.(frame)@@extension@",
            "requires": ["productversion_path"],
        }
        structure["productFilesShots"] = {
            "label": "Shot Productfiles",
            "key": "@productfile_path@",
            "value": "@productversion_path@/@sequence@-@shot@_@product@_@version@@.(frame)@@extension@",
            "requires": ["productversion_path"],
        }
        structure["3drenders"] = {
            "label": "3D Renders",
            "key": "@render_path@",
            "value": "@entity_path@/Renders/3dRender/@identifier@",
            "requires": ["entity_path", "identifier"],
        }
        structure["2drenders"] = {
            "label": "2D Renders",
            "key": "@render_path@",
            "value": "@entity_path@/Renders/2dRender/@identifier@",
            "requires": ["entity_path", "identifier"],
        }
        structure["externalMedia"] = {
            "label": "External Media",
            "key": "@render_path@",
            "value": "@entity_path@/Renders/external/@identifier@",
            "requires": ["entity_path", "identifier"],
        }
        structure["renderVersions"] = {
            "label": "Renderversions",
            "key": "@renderversion_path@",
            "value": "@render_path@/@version@",
            "requires": ["render_path", "version"],
        }
        structure["aovs"] = {
            "label": "AOVs",
            "key": "@aov_path@",
            "value": "[expression,#  available variables:\n#  \"core\" - PrismCore\n#  \"context\" - dict\n\nif context.get(\"mediaType\") == \"2drenders\":\n\ttemplate = \"@renderversion_path@\"\nelse:\n\ttemplate = \"@renderversion_path@/@aov@\"]",
            "requires": ["renderversion_path", "aov"],
        }
        structure["renderFilesAssets"] = {
            "label": "Asset Renderfiles",
            "key": "@renderfile_path@",
            "value": "[expression,#  available variables:\n#  \"core\" - PrismCore\n#  \"context\" - dict\n\nif context.get(\"mediaType\") == \"2drenders\":\n\ttemplate = \"@aov_path@/@asset@_@identifier@_@version@@.(frame)@@extension@\"\nelse:\n\ttemplate = \"@aov_path@/@asset@_@identifier@_@version@@._(layer)@_@aov@@.(frame)@@extension@\"]",
            "requires": ["aov_path"],
        }
        structure["renderFilesShots"] = {
            "label": "Shot Renderfiles",
            "key": "@renderfile_path@",
            "value": "[expression,#  available variables:\n#  \"core\" - PrismCore\n#  \"context\" - dict\n\nif context.get(\"mediaType\") == \"2drenders\":\n\ttemplate = \"@aov_path@/@sequence@-@shot@_@identifier@_@version@@.(frame)@@extension@\"\nelse:\n\ttemplate = \"@aov_path@/@sequence@-@shot@_@identifier@_@version@@_(layer)@_@aov@@.(frame)@@extension@\"]",
            "requires": ["aov_path"],
        }
        structure["playblasts"] = {
            "label": "Playblasts",
            "key": "@playblast_path@",
            "value": "@entity_path@/Playblasts/@identifier@",
            "requires": ["entity_path", "identifier"],
        }
        structure["playblastVersions"] = {
            "label": "Playblastsversions",
            "key": "@playblastversion_path@",
            "value": "@playblast_path@/@version@",
            "requires": ["playblast_path", "version"],
        }
        structure["playblastFilesAssets"] = {
            "label": "Asset Playblastsfiles",
            "key": "@playblastfile_path@",
            "value": "@playblastversion_path@/@asset@_@identifier@_@version@@.(frame)@@extension@",
            "requires": ["playblastversion_path"],
        }
        structure["playblastFilesShots"] = {
            "label": "Shot Playblastsfiles",
            "key": "@playblastfile_path@",
            "value": "@playblastversion_path@/@sequence@-@shot@_@identifier@_@version@@.(frame)@@extension@",
            "requires": ["playblastversion_path"],
        }
        for key in self.extraStructureItems:
            data = self.extraStructureItems[key].copy()
            if "idx" in data:
                structure[key] = data
                structure.move_to_end(key, last=False)
                revstruct = reversed(structure)
                start = -(data["idx"]+1)
                for idx, skey in enumerate(list(revstruct)[start:]):
                    if idx >= data["idx"]:
                        break

                    structure.move_to_end(skey, last=False)
            else:
                structure[key] = data

        return structure

    @err_catcher(name=__name__)
    def getPrism1ProjectStructure(self) -> Dict[str, Dict[str, str]]:
        """Get the Prism 1.x project folder structure.
        
        Returns:
            Dictionary containing Prism 1.x folder structure definitions
        """
        folderStructure = {
            "pipeline": {
                "value": "@project_path@/00_Pipeline"
            }, 
            "assets": {
                "value": "@project_path@/03_Workflow/Assets/@asset_path@"
            },
            "sequences": {
                "value": "@project_path@/03_Workflow/Shots/@sequence@-@shot@"
            }, 
            "shots": {
                "value": "@project_path@/03_Workflow/Shots/@sequence@-@shot@"
            },
            "textures": {
                "value": "@project_path@/04_Assets/Textures"
            }, 
            "departments": {
                "value": "@entity_path@/Scenefiles/@department@"
            }, 
            "tasks": {
                "value": "@department_path@/@task@"
            }, 
            "assetScenefiles": {
                "value": "@task_path@/@asset@_@department@_@task@_@version@_@comment@_@user@_@extension@"
            }, 
            "shotScenefiles": {
                "value": "@task_path@/shot_@sequence@-@shot@_@department@_@task@_@version@_@comment@_@user@_@extension@"
            }, 
            "products": {
                "value": "@entity_path@/Export/@product@"
            }, 
            "productVersions": {
                "value": "@product_path@/@version@_@comment@_@user@"
            }, 
            "productFilesAssets": {
                "value": "@productversion_path@/@unit@/@asset@_@product@_@version@@.(frame)@@extension@"
            }, 
            "productFilesShots": {
                "value": "@productversion_path@/@unit@/shot_@sequence@-@shot@_@product@_@version@@.(frame)@@extension@"
            }, 
            "3drenders": {
                "value": "@entity_path@/Rendering/3dRender/@identifier@"
            }, 
            "2drenders": {
                "value": "@entity_path@/Rendering/2dRender/@identifier@"
            }, 
            "externalMedia": {
                "value": "@entity_path@/Rendering/external/@identifier@"
            },
            "renderVersions": {
                "value": "[expression,if context.get(\"mediaType\") == \"2drenders\":\n    template=\"@render_path@/@version@\"\nelse:\n    template=\"@render_path@/@version@_@comment@\"]"
            }, 
            "aovs": {
                "value": "[expression,if context.get(\"mediaType\") == \"2drenders\":\n    template=\"@renderversion_path@\"\nelse:\n    template=\"@renderversion_path@/@aov@\"]"
            }, 
            "renderFilesAssets": {
                "value": "@aov_path@/@asset@_@identifier@_@version@_@aov@@.(frame)@@extension@"
            }, 
            "renderFilesShots": {
                "value": "@aov_path@/shot_@sequence@-@shot@_@identifier@_@version@_@aov@@.(frame)@@extension@"
            }, 
            "playblasts": {
                "value": "@entity_path@/Playblasts/@identifier@"
            }, 
            "playblastVersions": {
                "value": "@playblast_path@/@version@_@comment@"
            }, 
            "playblastFilesAssets": {
                "value": "@playblastversion_path@/@asset@_@identifier@_@version@@.(frame)@@extension@"
            }, 
            "playblastFilesShots": {
                "value": "@playblastversion_path@/shot_@sequence@-@shot@_@identifier@_@version@@.(frame)@@extension@"
            }, 
            "houdini_HDAs": {
                "value": "@project_path@/04_Assets/HDAs"
            }, 
            "textureVersions": {
                "value": "@entity_path@/Textures/@identifier@/@version@"
            }, 
        }

        return folderStructure

    @err_catcher(name=__name__)
    def addProjectStructureItem(self, key: str, value: Dict[str, Any]) -> bool:
        """Add a custom item to the project structure.
        
        Args:
            key: Unique key for the structure item
            value: Structure item dictionary with label, key, value, and requires fields
            
        Returns:
            True on success
        """
        self.extraStructureItems[key] = value
        return True

    @err_catcher(name=__name__)
    def removeProjectStructureItem(self, key: str) -> bool:
        """Remove a custom item from the project structure.
        
        Args:
            key: Key of the structure item to remove
            
        Returns:
            True if item was removed, False if not found
        """
        if key in self.extraStructureItems:
            self.extraStructureItems.pop(key)
            return True
        else:
            return False

    @err_catcher(name=__name__)
    def getProjectStructure(
        self,
        projectPath: Optional[str] = None,
        projectStructure: Optional[Dict] = None
    ) -> OrderedDict:
        """Get the project folder structure with custom overrides.
        
        Args:
            projectPath: Project path. Uses current project if None. Defaults to None.
            projectStructure: Custom structure to merge. Defaults to None.
            
        Returns:
            OrderedDict containing complete project structure
        """
        structure = self.getDefaultProjectStructure()
        if not projectStructure:
            if self.core.prism1Compatibility:
                projectStructure = self.getPrism1ProjectStructure()
            else:
                if projectPath:
                    configPath = self.core.configs.getProjectConfigPath(projectPath)
                    projectStructure = self.core.getConfig(
                        "folder_structure", configPath=configPath
                    )
                else:
                    projectStructure = self.core.getConfig("folder_structure", config="project")

        if projectStructure:
            for key in projectStructure:
                if key in structure:
                    structure[key]["value"] = projectStructure[key]["value"]

        return structure

    @err_catcher(name=__name__)
    def getStructureValues(self, structure: OrderedDict) -> Dict[str, Dict[str, str]]:
        """Extract just the values from a structure definition.
        
        Args:
            structure: Full structure OrderedDict
            
        Returns:
            Dictionary containing only 'value' fields
        """
        struct = {}
        for key in structure:
            struct[key] = {"value": structure[key]["value"]}

        return struct

    @err_catcher(name=__name__)
    def validateFolderStructure(self, structure: OrderedDict) -> Union[bool, Dict[str, List[str]]]:
        """Validate project folder structure for errors.
        
        Args:
            structure: Structure OrderedDict to validate
            
        Returns:
            True if valid, dictionary of errors by key otherwise
        """
        errors = {}
        for skey in structure:
            item = structure[skey]
            path = item["value"]

            errors[skey] = []
            r = self.validateFolderKey(path, item)
            if r is not True:
                errors[skey] = r

        for skey in errors:
            if errors[skey]:
                return errors
        else:
            return True

    @err_catcher(name=__name__)
    def validateFolderKey(self, path: str, item: Dict[str, Any]) -> Union[bool, str]:
        """Validate a single folder structure key.
        
        Args:
            path: Template path string
            item: Structure item dictionary
            
        Returns:
            True if valid, error message string otherwise
        """
        missing = []
        reqKeys = item.get("requires", [])

        if path.count("@") % 2:
            msg = 'The path contains an uneven number of "@" characters.'

            return msg

        for key in reqKeys:
            if self.core.isStr(key):
                if "@%s@" % key not in path:
                    missing.append("@%s@" % key)
            else:
                for okey in key:
                    if "@%s@" % okey in path:
                        break
                else:
                    missing.append(" or ".join(["@%s@" % o for o in key]))

        if missing:
            msg = "The following required keys are missing:\n\n"
            msg += "\n".join(missing)
            return msg

        prevIdx = 0
        for key in reqKeys:
            if self.core.isStr(key):
                idx = path.find("@%s@" % key)
            else:
                for okey in key:
                    oekey = "@%s@" % okey
                    if oekey in path:
                        idx = path.find(oekey)

            if idx < prevIdx:
                msg = "The required keys are not in the correct order:\n\n"
                msg += "\n".join(["@%s@" % key for key in reqKeys])
                return msg

            prevIdx = idx

        return True

    @err_catcher(name=__name__)
    def validateExpression(self, expression: str) -> Dict[str, Any]:
        """Validate a Python expression used in folder structure.
        
        Args:
            expression: Python code string to validate
            
        Returns:
            Dictionary with 'valid' boolean and optional 'error' message
        """
        context = {}
        core = self.core
        lcls = locals().copy()
        try:
            exec(expression, lcls, None)
        except Exception as e:
            result = {"valid": False, "error": str(e)}
            return result
        else:
            if "template" in lcls:
                result = {"valid": True}
                return result

        result = {"valid": False, "error": "Make sure \"template\" is defined."}
        return result

    @err_catcher(name=__name__)
    def getTemplatesFromExpression(self, expression: str, context: Optional[Dict] = None) -> Optional[List[str]]:
        """Execute expression and extract template paths.
        
        Args:
            expression: Python expression string
            context: Context variables for expression. Defaults to None.
            
        Returns:
            List of template strings if successful, None on error
        """
        context = context or {}
        core = self.core

        if expression.startswith("[expression,"):
            expression = expression[len("[expression,"):]
            if expression.endswith("]"):
                expression = expression[:-1]

        lcls = locals().copy()
        try:
            exec(expression, lcls, None)
        except Exception as e:
            logger.warning("Error while evaluating expression:\n\n%s\n\nExpression: %s\n\nContext: %s" % (str(e), expression, context))
            return
        else:
            if "template" in lcls:
                t = lcls["template"]
                if self.core.isStr(t):
                    t = [t]

                return t

            logger.warning("expression doesn't define any template: %s - context: %s" % (expression, context))

    @err_catcher(name=__name__)
    def getTemplatePath(self, key: str, default: bool = False) -> Optional[str]:
        """Get template path for a structure key.
        
        Args:
            key: Structure key name
            default: If True, use default structure, else use project structure. Defaults to False.
            
        Returns:
            Template path string, None if key not found
        """
        if default:
            structure = self.getDefaultProjectStructure()
        else:
            structure = self.getProjectStructure()

        item = structure.get(key)
        if not item:
            return

        return item["value"]

    @err_catcher(name=__name__)
    def setTemplatePath(self, key: str, value: str) -> Optional[bool]:
        """Set template path for a structure key.
        
        Args:
            key: Structure key name
            value: New template path
            
        Returns:
            True on success, None if key invalid
        """
        structure = self.getProjectStructure()
        item = structure.get(key)
        if not item:
            self.core.popup("Invalid key: %s" % key)
            return

        item["value"] = value
        self.core.setConfig("folder_structure", val=structure, config="project")
        return True

    @err_catcher(name=__name__)
    def getResolvedProjectStructurePath(
        self,
        key: str,
        context: Optional[Dict] = None,
        structure: Optional[OrderedDict] = None,
        fallback: Optional[str] = None
    ) -> str:
        """Get a single resolved path from project structure.
        
        Args:
            key: Structure key to resolve
            context: Context variables for resolution. Defaults to None.
            structure: Structure definition. Defaults to None.
            fallback: Fallback value if resolution fails. Defaults to None.
            
        Returns:
            Resolved path string, or False/fallback if key not found
        """
        resolvedPaths = self.getResolvedProjectStructurePaths(key, context, structure, fallback)
        if not resolvedPaths:
            return ""

        resolvedPath = resolvedPaths[0]
        return resolvedPath

    @err_catcher(name=__name__)
    def getResolvedProjectStructurePaths(
        self,
        key: str,
        context: Optional[Dict] = None,
        structure: Optional[OrderedDict] = None,
        fallback: Optional[str] = None
    ) -> List[str]:
        """Get all resolved paths for a structure key.
        
        Args:
            key: Structure key to resolve
            context: Context variables. Defaults to None.
            structure: Structure definition. Defaults to None.
            fallback: Fallback value. Defaults to None.
            
        Returns:
            List of resolved paths, or False if key not found
        """
        context = context or {}
        if context.get("project_path"):
            prjPath = self.core.convertPath(context["project_path"], "global")
        else:
            if hasattr(self.core, "projectPath"):
                context["project_path"] = os.path.normpath(self.core.projectPath)
            else:
                context["project_path"] = ""

            prjPath = context["project_path"]

        if structure is None:
            structure = self.getProjectStructure(prjPath)

        item = structure.get(key)
        if not item:
            return []

        if key in [
            "assetScenefiles",
            "productFilesAssets",
            "renderFilesAssets",
            "playblastFilesAssets",
        ]:
            context["entityType"] = "asset"
        elif key in [
            "shotScenefiles",
            "productFilesShots",
            "renderFilesShots",
            "playblastFilesShots",
        ]:
            context["entityType"] = "shot"

        resolvedPaths = self.resolveStructurePath(item["value"], context=context, structure=structure, fallback=fallback)
        resolvedPaths = [os.path.normpath(resolvedPath) for resolvedPath in resolvedPaths]
        return resolvedPaths

    @err_catcher(name=__name__)
    def resolveStructurePath(
        self,
        path: str,
        context: Optional[Dict] = None,
        structure: Optional[OrderedDict] = None,
        addProjectPath: bool = True,
        fillContextKeys: bool = True,
        fallback: Optional[str] = None
    ) -> List[str]:
        """Resolve a template path string with context variables.
        
        Args:
            path: Template path with @key@ placeholders
            context: Context variables for resolution. Defaults to None.
            structure: Structure definition. Defaults to None.
            addProjectPath: Whether to add project_path to context. Defaults to True.
            fillContextKeys: Whether to fill keys from context. Defaults to True.
            fallback: Fallback for unresolved keys. Defaults to None.
            
        Returns:
            List of resolved path strings
        """
        context = context or {}
        prjPath = None
        if "project_path" in context:
            if structure is None:
                prjPath = self.core.convertPath(context["project_path"], "global")
        elif getattr(self.core, "projectPath", None):
            if addProjectPath:
                context["project_path"] = os.path.normpath(self.core.projectPath)
                prjPath = context["project_path"]
            else:
                if structure is None:
                    prjPath = os.path.normpath(self.core.projectPath)

        if "project_path" in context and "project_name" not in context:
            glbPrjPath = self.core.convertPath(context["project_path"], "global")
            if hasattr(self.core, "projectPath") and glbPrjPath == self.core.projectPath:
                context["project_name"] = self.core.projectName
            else:
                cfgPath = self.core.configs.getProjectConfigPath(glbPrjPath)
                context["project_name"] = self.core.getConfig("globals", "project_name", configPath=cfgPath) or ""

        if structure is None:
            structure = self.getProjectStructure(prjPath)

        if path.startswith("[expression,"):
            paths = self.getTemplatesFromExpression(path, context=context) or ""
        else:
            paths = [path]

        newPaths = []
        for path in paths:
            resolvedPaths = [""]
            pieces = path.split("@")
            for idx, piece in enumerate(pieces):
                if not piece:
                    continue

                if idx % 2:
                    resolvedPieces = self.resolveStructurePiece(piece, structure, context, fillContextKeys=fillContextKeys, fallback=fallback)
                    if resolvedPieces is None:
                        logger.debug(piece)
                        logger.debug(context)

                    newResolvedPaths = []
                    for resolvedPiece in resolvedPieces:
                        for resolvedPath in resolvedPaths:
                            if resolvedPiece is None:
                                logger.warning("couldn't resolve. piece: %s context: %s" % (piece, context))
                            try:
                                newPath = resolvedPath + resolvedPiece
                            except:
                                logger.warning("couldn't resolve. piece: %s context: %s resolvedPath: %s resolvedPiece %s" % (piece, context, resolvedPath, resolvedPiece))
                                continue

                            newResolvedPaths.append(newPath)

                    resolvedPaths = newResolvedPaths

                else:
                    newResolvedPaths = []
                    for resolvedPath in resolvedPaths:
                        newPath = resolvedPath + piece
                        newResolvedPaths.append(newPath)

                    resolvedPaths = newResolvedPaths

            newPaths += resolvedPaths

        return newPaths

    @err_catcher(name=__name__)
    def resolveStructurePiece(
        self,
        key: str,
        structure: OrderedDict,
        context: Dict,
        fillContextKeys: bool = True,
        fallback: Optional[str] = None
    ) -> List[str]:
        """Resolve a single key piece from structure.
        
        Args:
            key: Key to resolve
            structure: Structure definition
            context: Context variables
            fillContextKeys: Whether to fill from context. Defaults to True.
            fallback: Fallback value. Defaults to None.
            
        Returns:
            List of resolved values for the key
        """
        if "(" in key and ")" in key:
            cleanKey = key[key.find("(")+1:key.find(")")]
        else:
            cleanKey = key

        if fillContextKeys:
            if cleanKey in context:
                val = context[cleanKey]
                if cleanKey != key and val:
                    val = key.replace("(%s)" % cleanKey, val)

                return [val]

        for structureKey in structure:
            if ("@%s@" % key) != structure[structureKey]["key"]:
                continue

            if (
                key == "entity_path"
                and ("asset" in context or context.get("entityType") == "asset")
                and structureKey != "assets"
            ):
                continue

            if (
                key == "entity_path"
                and ("shot" in context or context.get("entityType") == "shot")
                and structureKey != "shots"
            ):
                continue

            if (
                key == "render_path"
                and "mediaType" in context
                and structureKey != context["mediaType"]
            ):
                continue

            paths = self.resolveStructurePath(
                structure[structureKey]["value"], context=context, structure=structure, fillContextKeys=fillContextKeys
            )
            return paths

        if fallback is None:
            paths = ["@%s@" % key]
        else:
            paths = [fallback]

        return paths

    @err_catcher(name=__name__)
    def getTemplateKeys(self, template: str) -> List[str]:
        """Extract all keys from a template path.
        
        Args:
            template: Template path string with @key@ placeholders
            
        Returns:
            List of key names (without @ symbols)
        """
        return template.split("@")[1::2]

    @err_catcher(name=__name__)
    def extractKeysFromPath(self, path: str, template: str, context: Optional[Dict] = None) -> Dict[str, str]:
        """Extract key values from a path based on a template.
        
        Args:
            path: Actual path string
            template: Template path with @key@ placeholders
            context: Context for template resolution. Defaults to None.
            
        Returns:
            Dictionary mapping keys to their extracted values
        """
        template = self.resolveStructurePath(template, context=context, addProjectPath=False, fillContextKeys=False)[0]
        template = os.path.normpath(template)
        path = os.path.normpath(path)
        keys = self.getTemplateKeys(template)
        extKey = "@extension@"
        if template.endswith(extKey) and template[:-len(extKey)][-1] != ".":
            template = template[:-len(extKey)]
            path, extension = self.core.paths.splitext(path)
        else:
            extension = ""

        rePath = template
        rePath = re.escape(rePath)

        usedKeys = []
        for key in keys:
            if key in usedKeys:
                reKey = "__temp__%s_%s" % (key, usedKeys.count(key))
            else:
                if "(" in key and ")" in key:
                    cleanKey = key[key.find("(")+1:key.find(")")]
                    reKey = cleanKey
                else:
                    reKey = key

            reval = "(?P<%s>.*)" % reKey
            rePath = rePath.replace(re.escape("@%s@" % key), reval, 1)
            usedKeys.append(key)

        try:
            rmatch = re.match(rePath, path, re.IGNORECASE)
        except re.error as e:
            duplicates = [k for k in set(keys) if keys.count(k) > 1]
            logger.warning(
                "Failed to build regex for path template. "
                "Duplicate template keys: %s. Template: %s. Path: %s. Error: %s" % (duplicates, template, path, e)
            )
            return {}

        if not rmatch:
            return {}

        data = rmatch.groupdict()
        data["path"] = path
        if extension:
            data["extension"] = extension

        for key in data.copy():
            if key.startswith("__temp__"):
                del data[key]

        return data

    @err_catcher(name=__name__)
    def espaceBrackets(self, path: str) -> str:
        """Escape square brackets in a path for glob matching.
        
        Args:
            path: Path string that may contain square brackets
            
        Returns:
            Path with escaped brackets
        """
        escapedPath = ""
        for char in path:
            if char == "[":
                escapedPath += "[[]"
            elif char == "]":
                escapedPath += "[]]"
            else:
                escapedPath += char

        return escapedPath

    @err_catcher(name=__name__)
    def getMatchingPaths(self, template: str) -> List[Dict[str, str]]:
        """Find all filesystem paths matching a template.
        
        Args:
            template: Template path with @key@ placeholders
            
        Returns:
            List of dictionaries containing extracted key values and 'path'
        """
        template = os.path.normpath(template)
        keys = self.getTemplateKeys(template)
        globPath = template
        for key in keys:
            globPath = globPath.replace("@%s@" % key, "*")

        globPath = self.espaceBrackets(globPath)
        matches = glob.glob(globPath)

        extKey = "@extension@"
        if template.endswith(extKey) and template[:-len(extKey)][-1] != ".":
            template = template[:-len(extKey)]
            hasext = True
        else:
            hasext = False

        rePath = re.escape(template)
        usedKeys = []
        for key in keys:
            if key in usedKeys:
                reKey = "__temp__%s_%s" % (key, keys.index(key))
            else:
                if "(" in key and ")" in key:
                    cleanKey = key[key.find("(")+1:key.find(")")]
                    reKey = cleanKey
                else:
                    reKey = key

            reval = "(?P<%s>.*)" % reKey

            rePath = rePath.replace(re.escape("@%s@" % key), reval, 1)
            usedKeys.append(key)

        if self.core.prism1Compatibility:
            if "(?P<sequence>.*)-(?P<shot>.*)" in rePath:
                rePath = rePath.replace("(?P<sequence>.*)-(?P<shot>.*)", "(?P<sequence>[^-]+)-(?P<shot>.*)")

        pathData = []
        for match in matches:
            origMatch = match
            if hasext:
                match, extension = self.core.paths.splitext(match)

            rmatch = re.match(rePath, match, re.IGNORECASE)
            if not rmatch:
                continue

            data = rmatch.groupdict()
            data["path"] = origMatch
            if hasext:
                data["extension"] = extension

            if self.validateMatchedData(data):
                pathData.append(data)

        return pathData

    @err_catcher(name=__name__)
    def validateMatchedData(self, data: Dict[str, str]) -> bool:
        """Validate extracted data from a matched path.
        
        Args:
            data: Dictionary of extracted key values
            
        Returns:
            True if data is valid, False otherwise
        """
        for validVar in self.validVariables:
            if validVar in data:
                val = data[validVar]
                validVarValues = self.validVariables[validVar]
                if not any(fnmatch.fnmatch(val, pattern) for pattern in validVarValues):
                    logger.debug("skipping path with invalid value. variable: %s value: %s" % (validVar, val))
                    return False
                
        for invalidVar in self.invalidVariables:
            if invalidVar in data:
                val = data[invalidVar]
                invalidVarValues = self.invalidVariables[invalidVar]
                if any(fnmatch.fnmatch(val, pattern) for pattern in invalidVarValues):
                    logger.debug("skipping path with invalid value. variable: %s value: %s" % (invalidVar, val))
                    return False

        return True

    @err_catcher(name=__name__)
    def addValidVariables(self, variable: str, value: Union[str, List[str]]) -> None:
        """Add valid variable patterns for path validation.
        
        Args:
            variable: Variable name to validate
            value: Pattern or list of patterns that variable value must match to be considered valid
        """
        if variable not in self.validVariables:
            self.validVariables[variable] = []

        if isinstance(value, list):
            self.validVariables[variable].extend(value)
        else:
            self.validVariables[variable].append(value)

    @err_catcher(name=__name__)
    def addInvalidVariables(self, variable: str, value: Union[str, List[str]]) -> None:
        """Add invalid variable patterns for path validation.
        
        Args:
            variable: Variable name to validate
            value: Pattern or list of patterns that variable value must match to be considered invalid
        """
        if variable not in self.invalidVariables:
            self.invalidVariables[variable] = []

        if isinstance(value, list):
            self.invalidVariables[variable].extend(value)
        else:
            self.invalidVariables[variable].append(value)

    @err_catcher(name=__name__)
    def getProjectImagePath(
        self,
        projectPath: Optional[str] = None,
        projectConfig: Optional[str] = None,
        structure: Optional[OrderedDict] = None
    ) -> str:
        """Get the path where project image is stored.
        
        Args:
            projectPath: Project root path. Defaults to None.
            projectConfig: Project config path. Defaults to None.
            structure: Project structure. Defaults to None.
            
        Returns:
            Path to project.jpg file
        """
        if not projectPath and projectConfig:
            projectPath = self.getProjectFolderFromConfigPath(projectConfig)

        pipeDir = self.getPipelineFolder(projectPath=projectPath, structure=structure)
        path = os.path.join(pipeDir, "project.jpg")
        return path

    @err_catcher(name=__name__)
    def getProjectImage(
        self,
        projectPath: Optional[str] = None,
        projectConfig: Optional[str] = None,
        validate: bool = True,
        structure: Optional[OrderedDict] = None
    ) -> Optional[str]:
        """Get project image path if it exists.
        
        Args:
            projectPath: Project root path. Defaults to None.
            projectConfig: Project config path. Defaults to None.
            validate: Check if file exists. Defaults to True.
            structure: Project structure. Defaults to None.
            
        Returns:
            Path to image file if exists (and validate=True), None otherwise
        """
        path = self.getProjectImagePath(projectPath, projectConfig, structure)
        if not validate or os.path.exists(path):
            return path
        else:
            return

    @err_catcher(name=__name__)
    def saveProjectImage(
        self,
        projectPath: Optional[str] = None,
        projectConfig: Optional[str] = None,
        image: Optional[QPixmap] = None
    ) -> str:
        """Save project preview image.
        
        Args:
            projectPath: Project root path. Defaults to None.
            projectConfig: Project config path. Defaults to None.
            image: Image pixmap to save. Defaults to None.
            
        Returns:
            Path where image was saved
        """
        if not projectPath and projectConfig:
            projectPath = self.getProjectFolderFromConfigPath(projectConfig)

        imagePath = self.getProjectImagePath(projectPath)
        self.core.media.savePixmap(image, imagePath)
        return imagePath

    @err_catcher(name=__name__)
    def getRootPresetPath(self) -> str:
        """Get path to Prism root preset folder.
        
        Returns:
            Path to root presets directory
        """
        path = os.path.join(self.core.prismRoot, "Presets", "Projects")
        return path

    @err_catcher(name=__name__)
    def getUserPresetPath(self) -> str:
        """Get path to user preset folder.
        
        Returns:
            Path to user presets directory
        """
        dft = os.path.join(os.path.dirname(self.core.userini), "Presets", "Projects")
        path = os.getenv("PRISM_PROJECT_PRESETS_PATH", dft)
        return path

    @err_catcher(name=__name__)
    def getPresetPaths(self) -> List[str]:
        """Get all preset directory paths.
        
        Returns:
            List of preset directory paths
        """
        paths = []
        paths.append(self.getRootPresetPath())
        paths.append(self.getUserPresetPath())
        self.core.callback("getProjectPresetPaths", args=[paths])
        return paths

    @err_catcher(name=__name__)
    def getPresets(self) -> List[Dict[str, Any]]:
        """Get all available project presets.
        
        Returns:
            List of preset dictionaries with 'name', 'path', and 'settings' keys
        """
        presets = []
        presetPaths = self.getPresetPaths()
        for presetPath in presetPaths:
            if not os.path.exists(presetPath):
                continue

            for folder in os.listdir(presetPath):
                path = os.path.join(presetPath, folder)
                data = self.getPreset(name=folder, path=path)
                if data:
                    presets.append(data)

        return presets

    @err_catcher(name=__name__)
    def getPreset(self, name: Optional[str] = None, path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a specific project preset by name or path.
        
        Args:
            name: Preset name. Defaults to None.
            path: Preset path. Defaults to None.
            
        Returns:
            Preset dictionary or None if not found
        """
        if not path:
            presetPaths = self.getPresetPaths()
            for presetPath in presetPaths:
                path = os.path.join(presetPath, name)
                if os.path.exists(path):
                    break
            else:
                return

        if name == "Default":
            settings = self.getDefaultProjectSettings()
        else:
            configPath = self.core.configs.getProjectConfigPath(path)
            if not os.path.exists(configPath):
                logger.warning("couldn't find config of preset \"%s\". skipping preset. please set the \"PRISM_PROJECT_CONFIG_PATH\" environment variable." % path)
                return

            settings = self.core.getConfig(configPath=configPath)
        data = {"name": name, "path": path, "settings": settings}
        return data

    @err_catcher(name=__name__)
    def deletePreset(self, name: Optional[str] = None, path: Optional[str] = None) -> bool:
        """Delete a project preset.
        
        Args:
            name: Preset name. Defaults to None.
            path: Preset path. Defaults to None.
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not path:
            path = os.path.join(self.getUserPresetPath(), name)
            if not os.path.exists(path):
                return False

        while os.path.exists(path):
            try:
                shutil.rmtree(path)
            except Exception as e:
                logger.debug(str(e))
                msg = "Failed to delete preset:\n\n%s" % path
                result = self.core.popupQuestion(
                    msg,
                    buttons=["Retry", "Cancel"],
                    escapeButton="Cancel",
                    icon=QMessageBox.Warning,
                )
                if result == "Cancel":
                    return False

        return True

    @err_catcher(name=__name__)
    def createPresetFromFolder(self, name: str, path: str) -> bool:
        """Create a preset by copying an existing project folder.
        
        Args:
            name: New preset name
            path: Path to source project folder
            
        Returns:
            True on success, False on failure
        """
        presetsPath = self.getUserPresetPath()
        presetPath = os.path.join(presetsPath, name)
        if os.path.exists(presetPath):
            msg = 'Failed to create preset.\n\nThe preset "%s" already exists.' % name
            self.core.popup(msg)
            return False

        try:
            shutil.copytree(path, presetPath)
        except Exception as e:
            msg = "Failed to copy the folder to the preset directory:\n\n%s" % str(e)
            self.core.popup(msg)
            return False

        config = self.core.configs.getProjectConfigPath(presetPath)
        self.core.setConfig("globals", "project_name", "", configPath=config)
        return True

    @err_catcher(name=__name__)
    def createPresetFromSettings(
        self,
        name: str,
        settings: Dict,
        structure: Dict,
        dft: Optional[str] = None
    ) -> Optional[bool]:
        """Create a preset from settings dictionary.
        
        Args:
            name: Preset name
            settings: Project settings dictionary
            structure: Project structure
            dft: Default button for validation dialog. Defaults to None.
            
        Returns:
            True on success, False on failure, None if preset exists
        """
        presetsPath = self.getUserPresetPath()
        presetPath = os.path.join(presetsPath, name)
        if os.path.exists(presetPath):
            msg = 'Failed to create preset.\n\nThe preset "%s" already exists.' % name
            self.core.popup(msg)
            return False

        result = self.createProject(
            name=name,
            path=presetPath,
            settings=settings,
            preset=None,
            structure=structure,
        )
        if result:
            res = self.validateProjectPresetConfig(presetPath, result, dft=dft)
            if not res:
                return res

            self.core.setConfig("globals", "project_name", "", configPath=result)
            return True

    @err_catcher(name=__name__)
    def validateProjectPresetConfig(self, presetPath: str, configPath: str, dft: Optional[str] = None) -> bool:
        """Validate that preset config location matches expected location.
        
        Args:
            presetPath: Path to preset folder
            configPath: Path to config file
            dft: Default button choice. Defaults to None.
            
        Returns:
            True if valid, False if user cancels
        """
        dftConfig = self.core.configs.getProjectConfigPath(presetPath, useEnv=False)
        if dftConfig != configPath:
            cfgRelPath = os.path.normpath(configPath).replace(os.path.normpath(presetPath), "")
            cfgRelPath = cfgRelPath.strip("\\/")
            if "PRISM_PROJECT_CONFIG_PATH" in os.environ:
                if os.environ["PRISM_PROJECT_CONFIG_PATH"] == cfgRelPath:
                    return True

            msg = "The project config location for this preset differs from the default location. In order to save this preset the \"PRISM_PROJECT_CONFIG_PATH\" environment variable needs to be set to \"%s\". As long as this variable is set, presets with a different project config location cannot be loaded anymore." % cfgRelPath
            dft = dft or "Don't create preset"
            result = self.core.popupQuestion(msg, buttons=["Continue", "Don't create preset"], default=dft)
            if result == "Don't create preset":
                self.deletePreset(path=presetPath)
                return False

            self.core.users.setUserEnvironmentVariable(key="PRISM_PROJECT_CONFIG_PATH", value=cfgRelPath)

        return True

    @err_catcher(name=__name__)
    def getProjectDepartments(self) -> Dict:
        """Get legacy pipeline steps (deprecated).
        
        Returns:
            Dictionary of pipeline steps
        """
        steps = self.core.getConfig(
            "globals", "pipeline_steps", configPath=self.core.prismIni
        )

        try:
            dict(steps)
        except:
            steps = {}

        return steps

    @err_catcher(name=__name__)
    def getAssetDepartments(self, configData: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get asset departments configuration.
        
        Args:
            configData: Config dictionary. Uses project config if None. Defaults to None.
            
        Returns:
            List of department dictionaries
        """
        if configData:
            deps = configData.get("globals", {}).get("departments_asset")
        else:
            deps = self.core.getConfig(
                "globals", "departments_asset", configPath=self.core.prismIni
            )

        try:
            deps = list(deps)
        except:
            deps = []

        if not deps:
            deps = self.getProjectDepartments()
            if deps:
                deps = [{"name": d[1], "abbreviation": d[0], "defaultTasks": [d[1]]} for d in list(deps.items())]
                self.setDepartments("asset", deps, configData)

        return deps

    @err_catcher(name=__name__)
    def getShotDepartments(self, configData: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get shot departments configuration.
        
        Args:
            configData: Config dictionary. Uses project config if None. Defaults to None.
            
        Returns:
            List of department dictionaries
        """
        if configData:
            deps = configData.get("globals", {}).get("departments_shot")
        else:
            deps = self.core.getConfig(
                "globals", "departments_shot", configPath=self.core.prismIni
            )

        try:
            deps = list(deps)
        except:
            deps = []

        if not deps:
            deps = self.getProjectDepartments()
            if deps:
                deps = [{"name": d[1], "abbreviation": d[0], "defaultTasks": [d[1]]} for d in list(deps.items())]
                self.setDepartments("shot", deps, configData)

        return deps

    @err_catcher(name=__name__)
    def addDepartment(
        self,
        entity: str,
        name: str,
        abbreviation: str,
        defaultTasks: Optional[List[str]] = None,
        configData: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Add or update a department.
        
        Args:
            entity: "asset" or "shot"
            name: Department name
            abbreviation: Short abbreviation
            defaultTasks: List of default task names. Defaults to None.
            configData: Config dictionary. Defaults to None.
            
        Returns:
            Department dictionary
        """
        if entity == "asset":
            key = "departments_asset"
        elif entity in ["shot", "sequence"]:
            key = "departments_shot"

        if configData:
            deps = configData.get("globals", {}).get(key, [])
        else:
            deps = self.core.getConfig(
                "globals", key, configPath=self.core.prismIni, dft=[]
            )

        validDeps = []
        for dep in deps:
            if dep["abbreviation"] != abbreviation:
                validDeps.append(dep)

        defaultTasks = defaultTasks or []
        dep = {"name": name, "abbreviation": abbreviation, "defaultTasks": defaultTasks}
        validDeps.append(dep)

        self.setDepartments(entity, validDeps, configData)
        return dep

    @err_catcher(name=__name__)
    def setDepartments(self, entity: str, departments: List[Dict], configData: Optional[Dict] = None) -> None:
        """Set all departments for entity type.
        
        Args:
            entity: "asset" or "shot"
            departments: List of department dictionaries
            configData: Config dictionary. Defaults to None.
        """
        if entity == "asset":
            key = "departments_asset"
        elif entity in ["shot", "sequence"]:
            key = "departments_shot"

        if configData:
            configData["globals"][key] = departments
        else:
            self.core.setConfig(
                "globals", key, departments, configPath=self.core.prismIni
            )

    @err_catcher(name=__name__)
    def getAssetTaskPresets(self, configData: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get asset task presets.
        
        Args:
            configData: Config dictionary. Defaults to None.
            
        Returns:
            List of task preset dictionaries
        """
        if configData:
            presets = configData.get("globals", {}).get("taskpresets_asset")
        else:
            presets = self.core.getConfig(
                "globals", "taskpresets_asset", configPath=self.core.prismIni
            )

        if presets is None:
            presets = self.getDftAssetTaskPresets()
            self.setTaskPresets("asset", presets, configData)

        try:
            presets = list(presets)
        except:
            presets = []

        return presets

    @err_catcher(name=__name__)
    def getDftAssetTaskPresets(self) -> List[Dict[str, Any]]:
        """Get default asset task presets.
        
        Returns:
            List of default task preset dictionaries
        """
        presets = [
            {
                "name": "All",
                "departments": [
                    {
                        "name": "Concept",
                        "tasks": ["Concept"]
                    },
                    {
                        "name": "Modeling",
                        "tasks": ["Modeling"]
                    },
                    {
                        "name": "Surfacing",
                        "tasks": ["Surfacing"]
                    },
                    {
                        "name": "Rigging",
                        "tasks": ["Rigging"]
                    }
                ]
            },
            {
                "name": "Character",
                "departments": [
                    {
                        "name": "Modeling",
                        "tasks": ["Modeling"]
                    },
                    {
                        "name": "Surfacing",
                        "tasks": ["Surfacing"]
                    },
                    {
                        "name": "Rigging",
                        "tasks": ["Rigging"]
                    }
                ]
            },
            {
                "name": "Prop",
                "departments": [
                    {
                        "name": "Modeling",
                        "tasks": ["Modeling"]
                    },
                    {
                        "name": "Surfacing",
                        "tasks": ["Surfacing"]
                    }
                ]
            },
            {
                "name": "Environment",
                "departments": [
                    {
                        "name": "Modeling",
                        "tasks": ["Layout"]
                    }
                ]
            }
        ]
        return presets

    @err_catcher(name=__name__)
    def getShotTaskPresets(self, configData: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get shot task presets.
        
        Args:
            configData: Config dictionary. Defaults to None.
            
        Returns:
            List of task preset dictionaries
        """
        if configData:
            presets = configData.get("globals", {}).get("taskpresets_shot")
        else:
            presets = self.core.getConfig(
                "globals", "taskpresets_shot", configPath=self.core.prismIni
            )

        if presets is None:
            presets = self.getDftShotTaskPresets()
            self.setTaskPresets("shot", presets, configData)

        try:
            presets = list(presets)
        except:
            presets = []

        return presets

    @err_catcher(name=__name__)
    def getDftShotTaskPresets(self) -> List[Dict[str, Any]]:
        """Get default shot task presets.
        
        Returns:
            List of default task preset dictionaries
        """
        presets = [
            {
                "name": "All",
                "departments": [
                    {
                        "name": "Layout",
                        "tasks": ["Layout"]
                    },
                    {
                        "name": "Animation",
                        "tasks": ["Animation"]
                    },
                    {
                        "name": "CharFX",
                        "tasks": ["CharacterEffects"]
                    },
                    {
                        "name": "FX",
                        "tasks": ["Effects"]
                    },
                    {
                        "name": "Lighting",
                        "tasks": ["Lighting"]
                    },
                    {
                        "name": "Compositing",
                        "tasks": ["Compositing"]
                    }
                ]
            },
            {
                "name": "Default",
                "departments": [
                    {
                        "name": "Layout",
                        "tasks": ["Layout"]
                    },
                    {
                        "name": "Animation",
                        "tasks": ["Animation"]
                    },
                    {
                        "name": "Lighting",
                        "tasks": ["Lighting"]
                    },
                    {
                        "name": "Compositing",
                        "tasks": ["Compositing"]
                    }
                ]
            },
            {
                "name": "Simple",
                "departments": [
                    {
                        "name": "Animation",
                        "tasks": ["Animation"]
                    },
                    {
                        "name": "Lighting",
                        "tasks": ["Lighting"]
                    },
                    {
                        "name": "Compositing",
                        "tasks": ["Compositing"]
                    }
                ]
            },
            {
                "name": "Minimal",
                "departments": [
                    {
                        "name": "Lighting",
                        "tasks": ["Lighting"]
                    }
                ]
            }
        ]
        return presets

    @err_catcher(name=__name__)
    def addTaskPreset(
        self,
        entity: str,
        name: str,
        departments: Optional[List[Dict]] = None,
        configData: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Add or update a task preset.
        
        Args:
            entity: "asset" or "shot"
            name: Preset name
            departments: List of department dictionaries. Defaults to None.
            configData: Config dictionary. Defaults to None.
            
        Returns:
            Preset dictionary
        """
        departments = departments or []
        if entity == "asset":
            key = "taskpresets_asset"
        elif entity in ["shot", "sequence"]:
            key = "taskpresets_shot"

        if configData:
            presets = configData.get("globals", {}).get(key, [])
        else:
            presets = self.core.getConfig(
                "globals", key, configPath=self.core.prismIni, dft=[]
            )

        validPresets = []
        for preset in presets:
            if preset["name"] != name:
                validPresets.append(preset)

        preset = {"name": name, "departments": departments}
        validPresets.append(preset)

        self.setTaskPresets(entity, validPresets, configData)
        return preset

    @err_catcher(name=__name__)
    def setTaskPresets(self, entity: str, presets: List[Dict], configData: Optional[Dict] = None) -> None:
        """Set all task presets for entity type.
        
        Args:
            entity: "asset" or "shot"
            presets: List of preset dictionaries
            configData: Config dictionary. Defaults to None.
        """
        if entity == "asset":
            key = "taskpresets_asset"
        elif entity in ["shot", "sequence"]:
            key = "taskpresets_shot"

        if configData:
            if "globals" not in configData:
                configData["globals"] = {}

            configData["globals"][key] = presets
        else:
            self.core.setConfig(
                "globals", key, presets, configPath=self.core.prismIni
            )

    @err_catcher(name=__name__)
    def getDefaultCodePresets(self) -> List[Dict[str, str]]:
        """Get default code presets.
        
        Returns:
            List of code preset dictionaries with 'name' and 'code' keys
        """
        presets = [
            {
                "name": "Show Message",
                "code": "pcore.popup(\"Hello World\")"
            },
            {
                "name": "Stop Publish",
                "code": "#run some checks\npassed = False\nif not passed:\n    pcore.popup(\"Publish checks not passed.\")\n    STOP_PUBLISH = True"
            }
        ]
        return presets

    @err_catcher(name=__name__)
    def getCodePresets(self) -> List[Dict[str, str]]:
        """Get all code presets.
        
        Returns:
            List of code preset dictionaries
        """
        dft = self.getDefaultCodePresets()
        data = self.core.getConfig(config="codePresets", location="project", dft=dft)
        return data

    @err_catcher(name=__name__)
    def setCodePresets(self, presets: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Save code presets.
        
        Args:
            presets: List of code preset dictionaries
            
        Returns:
            The saved presets list
        """
        self.core.setConfig(data=presets, config="codePresets", location="project")
        return presets

    @err_catcher(name=__name__)
    def addCodePreset(self, name: str, code: str = "") -> List[Dict[str, str]]:
        """Add or update a code preset.
        
        Args:
            name: Preset name
            code: Python code string. Defaults to empty string.
            
        Returns:
            Updated list of presets
        """
        presets = self.getCodePresets()
        presets = [p for p in presets if p.get("name", "") != name]
        newPreset = {"name": name, "code": code}
        presets.append(newPreset)
        self.setCodePresets(presets)
        return presets

    @err_catcher(name=__name__)
    def removeCodePreset(self, name: str) -> List[Dict[str, str]]:
        """Remove a code preset.
        
        Args:
            name: Preset name to remove
            
        Returns:
            Updated list of presets
        """
        presets = self.getCodePresets()
        presets = [p for p in presets if p.get("name", "") != name]
        self.setCodePresets(presets)
        return presets

    @err_catcher(name=__name__)
    def getFps(self) -> Optional[float]:
        """Get project frames per second if forced FPS is enabled.
        
        Returns:
            FPS value if forced, None otherwise
        """
        forceFPS = self.core.getConfig(
            "globals", "forcefps", config="project"
        )
        if not forceFPS:
            return

        pFps = self.core.getConfig("globals", "fps", config="project")
        return pFps

    class ProjectListWidget(QDialog):
        """Dialog widget for displaying and selecting from available projects.
        
        This widget shows a grid of project cards that users can browse,
        search, and select from. It provides options to create new projects
        or open existing ones.
        
        Attributes:
            signalShowing (Signal): Emitted when widget is shown
            origin: Parent widget
            core: PrismCore instance
            projectWidgets (List): List of ProjectWidget instances
            allowClose (bool): Whether widget can be closed
            allowDeselect (bool): Whether items can be deselected
            allowMultiSelection (bool): Whether multiple items can be selected
            dirty (bool): Whether widget needs refresh
        """

        signalShowing = Signal()

        def __init__(self, origin: Any) -> None:
            """Initialize ProjectListWidget.
            
            Args:
                origin: Parent widget
            """
            super(Projects.ProjectListWidget, self).__init__()
            self.origin = origin
            self.core = origin.core
            self.projectWidgets = []
            self.allowClose = True
            self.allowDeselect = True
            self.allowMultiSelection = True
            self.dirty = False
            self.core.parentWindow(self, parent=origin)
            self.setupUi()
            self.refreshUi()
            self.core.callback(name="onProjectListStartup", args=[self])

        @err_catcher(name=__name__)
        def focusInEvent(self, event: Any) -> None:
            """Handle focus in event by activating window.
            
            Args:
                event: Focus event
            """
            self.activateWindow()

        @err_catcher(name=__name__)
        def focusOutEvent(self, event: Any) -> None:
            """Handle focus out event, close if focus moved outside widget.
            
            Args:
                event: Focus event
            """
            new_focus = QApplication.focusWidget()
            if new_focus and self.isAncestorOf(new_focus):
                # Focus moved to a child → do NOT close
                event.ignore()
            else:
                if self.allowClose:
                    self.close()

        @err_catcher(name=__name__)
        def eventFilter(self, watched: Any, event: Any) -> bool:
            """Filter events for child widgets, close on focus out.
            
            Args:
                watched: Widget being watched
                event: Event to filter
                
            Returns:
                Whether event was handled
            """
            if event.type() == QEvent.FocusOut:
                new_focus = QApplication.focusWidget()
                if not (new_focus and self.isAncestorOf(new_focus)):
                    self.close()

            return super().eventFilter(watched, event)

        @err_catcher(name=__name__)
        def showWidget(self) -> None:
            """Configure widget display style and select current project.
            
            Sets frameless window, stays on top, applies border style,
            and pre-selects current project widget.
            """
            self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.setStyleSheet("QDialog { border: 1px solid rgb(70, 90, 120); }")

            for widget in self.projectWidgets:
                if widget.data.get("configPath", None) == self.core.prismIni:
                    widget.select()

            if self.dirty:
                self.refreshUi()
                self.dirty = False

            self.show()
            QApplication.processEvents()
            self.e_search.setFocus()
            self.resize(self.w_projects.width() + self.lo_projects.contentsMargins().left() * 2, self.height())        

        @err_catcher(name=__name__)
        def setupUi(self) -> None:
            """Set up project list UI with search, create/open buttons, and scrollable grid.
            
            Creates header with search bar and action buttons, grid layout for project
            widgets, and scroll area for navigation.
            """
            self.setFocusPolicy(Qt.StrongFocus)

            self.w_header = QWidget()
            self.lo_header = QHBoxLayout(self.w_header)
            self.e_search = QLineEdit()
            self.e_search.setPlaceholderText("Search Projects...")
            self.e_search.setClearButtonEnabled(True)
            self.e_search.installEventFilter(self)
            self.e_search.textChanged.connect(lambda text: self.refreshUi())
            self.b_create = QPushButton()
            path = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "create.png")
            icon = self.core.media.getColoredIcon(path)
            self.b_create.setIcon(icon)
            self.b_create.setText(" Create")
            self.b_create.setToolTip("Create New Project...")
            self.b_create.setFocusPolicy(Qt.NoFocus)
            self.b_create.clicked.connect(self.preCreate)

            self.b_open = QPushButton()
            path = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "browse.png")
            icon = self.core.media.getColoredIcon(path)
            self.b_open.setIcon(icon)
            self.b_open.setText(" Open")
            self.b_open.setToolTip("Browse and Open an existing Project...")
            self.b_open.setFocusPolicy(Qt.NoFocus)
            self.b_open.clicked.connect(self.close)
            self.b_open.clicked.connect(lambda: self.core.projects.openProject(parent=self.origin))

            self.lo_header.addWidget(self.e_search)
            self.lo_header.addWidget(self.b_create)
            self.lo_header.addWidget(self.b_open)
            self.lo_header.setContentsMargins(9, 5, 9, 0)

            self.w_projects = QWidget()
            self.w_projects.setFocusProxy(self)
            self.lo_projects = QGridLayout()
            self.lo_projects.setSpacing(10)
            self.lo_projects.setContentsMargins(0, 9, 20, 9)
            self.w_projects.setLayout(self.lo_projects)
            self.lo_main = QVBoxLayout()
            self.lo_main.setContentsMargins(0, 0, 0, 0)
            self.setLayout(self.lo_main)

            self.w_scrollParent = QWidget()
            self.w_scrollParent.setFocusProxy(self)
            self.lo_scrollParent = QHBoxLayout()
            self.lo_scrollParent.setContentsMargins(0, 0, 0, 0)
            self.sa_projects = QScrollArea()
            self.sa_projects.setFocusProxy(self)
            self.sa_projects.setWidgetResizable(True)
            self.sa_projects.setWidget(self.w_projects)
            self.sa_projects.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.w_scrollParent.setLayout(self.lo_scrollParent)
            self.lo_scrollParent.addWidget(self.sa_projects)
            self.lo_main.addWidget(self.w_header)
            self.lo_main.addWidget(self.w_scrollParent)

        @err_catcher(name=__name__)
        def refreshUi(self) -> None:
            """Refresh project list UI with current projects and search filter.
            
            Clears existing widgets, loads available projects, applies search filter,
            creates project widgets in grid layout, and triggers callback.
            """
            self.projectWidgets = []
            for idx in reversed(range(self.lo_projects.count())):
                item = self.lo_projects.takeAt(idx)
                w = item.widget()
                if w:
                    w.setParent(None)
                    w.deleteLater()

            self.projects = self.core.projects.getAvailableProjects(includeCurrent=True)
            searchFilter = self.e_search.text().lower()
            if searchFilter:
                self.projects = [p for p in self.projects if searchFilter in (p.get("name") or "").lower()]

            for project in self.projects:
                w_prj = Projects.ProjectWidget(self, project.copy(), minHeight=1, previewScale=0.5)
                w_prj.setFocusProxy(self)
                w_prj.signalDoubleClicked.connect(self.openProject)
                w_prj.signalRemoved.connect(self.refreshUi)
                w_prj.signalSelect.connect(self.itemSelected)
                self.projectWidgets.append(w_prj)
                self.lo_projects.addWidget(
                    w_prj,
                    int(self.lo_projects.count() / 3),
                    (self.lo_projects.count() % 3) + 1,
                )

            self.core.callback(name="onProjectListRefreshed", args=[self])
            self.sp_projectsR = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.sp_projectsB = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.lo_projects.addItem(self.sp_projectsR, 0, 4)
            self.w_spacer = QWidget()
            sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            sizePolicy.setVerticalStretch(100)
            self.w_spacer.setSizePolicy(sizePolicy)
            self.lo_projects.addWidget(self.w_spacer, self.lo_projects.rowCount(), 0)

        @err_catcher(name=__name__)
        def preCreate(self) -> None:
            """Open project creation dialog and close project browser if visible."""
            self.core.projects.createProjectDialog()
            if getattr(self.core, "pb", None) and self.core.pb.isVisible():
                self.core.pb.close()

        @err_catcher(name=__name__)
        def itemSelected(self, item: Any, event: Optional[Any] = None) -> None:
            """Handle item selection with multi-selection and modifier key support.
            
            Args:
                item: Project widget being selected
                event: Mouse event (optional)
            """
            if not self.allowDeselect:
                return

            if self.allowMultiSelection:
                mods = QApplication.keyboardModifiers()
                if item.isSelected():
                    if mods == Qt.ControlModifier and (not event or event.button() == Qt.LeftButton):
                        item.deselect()
                else:
                    if mods != Qt.ControlModifier:
                        self.deselectItems(ignore=[item])
            else:
                if not item.isSelected():
                    self.deselectItems(ignore=[item])

        @err_catcher(name=__name__)
        def deselectItems(self, ignore: Optional[List[Any]] = None) -> None:
            """Deselect all project widgets except ignored ones.
            
            Args:
                ignore: List of widgets to skip deselecting
            """
            for item in self.projectWidgets:
                if ignore and item in ignore:
                    continue

                item.deselect()

        @err_catcher(name=__name__)
        def getSelectedProject(self) -> Optional[Any]:
            """Get first selected project widget.
            
            Returns:
                First selected ProjectWidget or None if none selected
            """
            selectedProjects = [x for x in self.projectWidgets if x.isSelected()]
            if not selectedProjects:
                return

            prj = selectedProjects[0]
            return prj

        @err_catcher(name=__name__)
        def getSelectedItems(self) -> List[Any]:
            """ Get list of selected project widgets.
            
            Returns:
                List of selected ProjectWidget instances
            """
            items = []
            for item in self.projectWidgets:
                if item.isSelected():
                    items.append(item)

            return items

        @err_catcher(name=__name__)
        def showEvent(self, event: Any) -> None:
            """Handle show event by emitting signalShowing.
            
            Args:
                event: Show event
            """
            self.signalShowing.emit()

        @err_catcher(name=__name__)
        def openProject(self, widget: Any) -> None:
            """Open selected project, close dialog and switch to new project.
            
            Args:
                widget: Project widget to open
            """
            path = widget.data["configPath"]
            if path == self.core.prismIni:
                msg = "This project is already active."
                self.core.popup(msg, parent=self)
                return

            self.close()
            self.core.changeProject(path)

    class ProjectWidget(QWidget):
        """Widget representing a single project in the project browser.
        
        Displays project preview image, name, and provides context menu
        for project operations like opening, favoriting, or removing.
        
        Attributes:
            signalSelect (Signal): Emitted when widget is selected
            signalReleased (Signal): Emitted when mouse released
            signalDoubleClicked (Signal): Emitted on double click
            signalRemoved (Signal): Emitted when project removed
            core: PrismCore instance
            data (Dict): Project data dictionary
            status (str): Selection status ("selected" or "deselected")
        """

        signalSelect = Signal(object, object)
        signalReleased = Signal(object)
        signalDoubleClicked = Signal(object)
        signalRemoved = Signal()
        signalPreviewImageLoaded = Signal(object)

        def __init__(
            self,
            parent: "Projects.ProjectListWidget",
            data: Dict[str, Any],
            minHeight: int = 200,
            allowRemove: bool = True,
            previewScale: float = 1,
            useWidgetWidth: bool = False
        ) -> None:
            """Initialize ProjectWidget.
            
            Args:
                parent: Parent ProjectListWidget
                data: Project data dictionary
                minHeight: Minimum widget height. Defaults to 200.
                allowRemove: Whether project can be removed. Defaults to True.
                previewScale: Scale factor for preview. Defaults to 1.
                useWidgetWidth: Use widget width for scaling. Defaults to False.
            """
            super(Projects.ProjectWidget, self).__init__()
            self.core = parent.core
            self._parent = parent
            self.data = data
            self.status = "deselected"
            self.minHeight = minHeight
            self.allowRemove = allowRemove
            self.previewScale = previewScale
            self.useWidgetWidth = useWidgetWidth
            self.previewWidth = int(200 * previewScale)
            self.previewHeight = int((200 * previewScale) / (16/9.0))
            self.signalPreviewImageLoaded.connect(self.onPreviewImageLoaded)
            self.setupUi()
            self.refreshUi()

        @err_catcher(name=__name__)
        def sizeHint(self) -> QSize:
            """Return size hint for project widget.
            
            Returns:
                QSize with minHeight
            """
            return QSize(1, self.minHeight)

        @err_catcher(name=__name__)
        def resizeEvent(self, event: Any) -> None:
            """Handle resize event by updating preview without reloading.
            
            Args:
                event: Resize event
            """
            self.updatePreview(load=False)

        @err_catcher(name=__name__)
        def setupUi(self) -> None:
            """Set up project widget UI with preview, icon, name, and info labels.
            
            Creates rounded preview label, project name, favorite star, info icon,
            and context menu. Configures layout and styling.
            """
            self.setObjectName("texture")
            self.applyStyle()
            self.setAttribute(Qt.WA_StyledBackground, True)
            self.lo_main = QVBoxLayout()
            self.setLayout(self.lo_main)
            self.lo_main.setSpacing(0)
            self.lo_main.setContentsMargins(0, 0, 0, 0)

            self.l_preview = Projects.RoundedLabel()
            self.l_preview.setMinimumWidth(self.previewWidth)
            self.l_preview.setMinimumHeight(self.previewHeight)
            self.l_icon = QLabel()
            self.l_icon.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
            self.l_name = QLabel()
            font = self.l_name.font()
            font.setBold(True)
            font.setPointSizeF(10)
            self.l_name.setFont(font)
            self.l_name.setAlignment(Qt.AlignHCenter)
            self.l_fav = QLabel()
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "favorite.png"
            )
            icon = self.core.media.getColoredIcon(iconPath, r=240, g=240, b=0)
            self.l_fav.setPixmap(icon.pixmap(15, 15))
            self.l_fav.setToolTip("Favorite")

            self.l_info = Projects.HelpLabel()
            self.l_info.setMouseTracking(True)
            self.lo_info = QVBoxLayout()

            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "info.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            self.l_info.setPixmap(icon.pixmap(15, 15))
            self.l_info.setMouseTracking(True)

            self.lo_footer = QHBoxLayout()
            self.lo_footer.addStretch()
            self.lo_footer.addWidget(self.l_name)
            if "info" not in self.data:
                self.data["info"] = ""

            if "configPath" in self.data:
                self.data["info"] += self.data["configPath"]

            if "date" in self.data:
                if self.data["info"]:
                    self.data["info"] += "\n"

                self.data["info"] += "Last opened:    " + self.core.getFormattedDate(
                    self.data["date"]
                )

            self.lo_footer.setContentsMargins(10, 10, 10, 10)
            self.lo_footer.setSpacing(10)
            self.lo_info.addLayout(self.lo_footer)
            if "icon" in self.data:
                self.lo_main.addWidget(self.l_icon)
            else:
                self.lo_main.addWidget(self.l_preview)

            self.lo_main.addLayout(self.lo_info)

            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self.rightClicked)

            if self.data["info"]:
                self.l_info.setToolTip(self.data["info"])
                self.l_info.adjustSize()
                # self.l_info.move(self.previewWidth - int(30 * self.previewScale), 10)
                self.lo_footer.addStretch()
                self.lo_footer.addWidget(self.l_fav)
                self.lo_footer.addWidget(self.l_info)
                self.l_info.setParent(self)
                self.sp_left = QSpacerItem(self.l_info.width(), 0, QSizePolicy.Fixed, QSizePolicy.Fixed)
                self.lo_footer.insertItem(0, self.sp_left)
            else:
                self.lo_footer.addStretch()
                self.lo_footer.addWidget(self.l_fav)

        @err_catcher(name=__name__)
        def updatePreview_threaded(self) -> None:
            """Start background thread to update preview image."""
            import threading

            self.thread = threading.Thread(target=self.loadPreviewImage)
            self.thread.start()

        @err_catcher(name=__name__)
        def loadPreviewImage(self) -> None:
            """Load preview QImage in a worker thread and emit it to GUI thread."""
            imagePath = None
            if "configPath" in self.data:
                imagePath = self.core.projects.getProjectImage(
                    projectConfig=self.data["configPath"]
                )

                if not imagePath:
                    imagePath = os.path.join(
                        self.core.prismRoot,
                        "Presets/Projects/Default/00_Pipeline/Fallbacks/noFileBig.jpg",
                    )

            if not imagePath:
                return

            qimg = self.core.media.getQImageFromPath(imagePath)
            self.signalPreviewImageLoaded.emit(qimg)

        @err_catcher(name=__name__)
        def onPreviewImageLoaded(self, qimg: Optional[QImage]) -> None:
            """Convert loaded QImage to preview pixmap on the GUI thread."""
            if not qimg or qimg.isNull():
                return

            pixmap = QPixmap.fromImage(qimg)
            self.validPreview = pixmap
            ppixmap = self.core.media.scalePixmap(
                pixmap,
                self.l_preview.width(),
                self.previewHeight,
                keepRatio=True,
                fitIntoBounds=False,
                crop=True,
            )
            if ppixmap and ppixmap != "loading":
                self.l_preview.setPixmap(ppixmap)

        @err_catcher(name=__name__)
        def refreshUi(self) -> None:
            """Refresh widget display with icon/preview, name, and favorite star.
            
            Loads icon or preview image (threaded if parent visible),
            updates display name, and shows/hides favorite indicator.
            """
            icon = self.getIcon()
            if icon:
                self.l_icon.setPixmap(icon)
            else:
                self.setLoadingPreview()
                if self._parent.isVisible():
                    self.updatePreview_threaded()
                else:
                    self._parent.signalShowing.connect(self.updatePreview_threaded)

            name = self.getDisplayName()
            self.l_name.setText(name)
            self.l_fav.setVisible(self.data.get("favorite", False))

        @err_catcher(name=__name__)
        def updatePreview(self, load: bool = True) -> None:
            """Update preview image with optional loading from disk.
            
            Args:
                load: Whether to load image from disk. Defaults to True.
            """
            if hasattr(self, "loadingGif"):
                self.loadingGif.setScaledSize(QSize(self.l_preview.width(), int(self.l_preview.width() / (300/169.0))))

            ppixmap = self.getPreviewImage(load=load)
            if not ppixmap or ppixmap == "loading":
                return

            self.l_preview.setPixmap(ppixmap)

        @err_catcher(name=__name__)
        def setLoadingPreview(self) -> None:
            """Display animated loading indicator in preview label."""
            if hasattr(self, "loadingGif"):
                return

            path = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "loading.gif"
            )
            self.loadingGif = QMovie(path, QByteArray(), self) 
            self.loadingGif.setCacheMode(QMovie.CacheAll) 
            self.loadingGif.setSpeed(100) 
            self.loadingGif.setScaledSize(QSize(self.l_preview.width(), int(self.l_preview.width() / (300/169.0))))
            self.l_preview.setMovie(self.loadingGif)
            self.loadingGif.start()

        @err_catcher(name=__name__)
        def getPreviewImage(self, load: bool = True) -> Union[QPixmap, str, None]:
            """Get preview image pixmap, loading from disk if needed.
            
            Args:
                load: Whether to load image from disk if not cached. Defaults to True.
                
            Returns:
                QPixmap, 'loading' string, or None
            """
            if getattr(self, "validPreview", None):
                pixmap = self.core.media.scalePixmap(self.validPreview, self.l_preview.width(), self.previewHeight, keepRatio=True, fitIntoBounds=False, crop=True)
                return pixmap

            image = None
            if load:
                if "configPath" in self.data:
                    image = self.core.projects.getProjectImage(
                        projectConfig=self.data["configPath"]
                    )
                    if not image:
                        imgFile = os.path.join(
                            self.core.prismRoot,
                            "Presets/Projects/Default/00_Pipeline/Fallbacks/noFileBig.jpg",
                        )
                        pixmap = self.core.media.getPixmapFromPath(imgFile)
                        pixmap = self.core.media.scalePixmap(pixmap, self.l_preview.width(), self.previewHeight, keepRatio=True, fitIntoBounds=False, crop=True)
                        return pixmap

            if load and image:
                pixmap = QPixmap(image)
                self.validPreview = pixmap
                pixmap = self.core.media.scalePixmap(pixmap, self.l_preview.width(), self.previewHeight, keepRatio=True, fitIntoBounds=False, crop=True)
            else:
                pixmap = "loading"

            return pixmap

        @err_catcher(name=__name__)
        def getIcon(self) -> Optional[QPixmap]:
            """Get project icon pixmap if available.
            
            Returns:
                QPixmap icon or None
            """
            if "icon" not in self.data:
                return

            if self.core.isStr(self.data["icon"]):
                icon = self.core.media.getColoredIcon(self.data["icon"], force=True)
            else:
                icon = self.data["icon"]

            pixmap = icon.pixmap(30, 30)
            return pixmap

        @err_catcher(name=__name__)
        def getDisplayName(self) -> str:
            """Get project display name from data.
            
            Returns:
                Project name string
            """
            name = self.data["name"]
            return name

        @err_catcher(name=__name__)
        def applyStyle(self, styleType: str = "deselected") -> None:
            """Apply visual style based on selection and hover state.
            
            Args:
                styleType: Style type - 'deselected', 'selected', 'hoverSelected', or 'hover'
            """
            ssheet = """
                QWidget#texture {
                    border: 1px solid rgb(70, 90, 120);
                    border-radius: 10px;
                    background-color: rgba(255, 255, 255, 10);
                }
            """
            if styleType == "deselected":
                pass
            elif styleType == "selected":
                ssheet = """
                    QWidget#texture {
                        border: 1px solid rgb(120, 130, 150);
                        background-color: rgba(255, 255, 255, 40);
                        border-radius: 10px;
                    }
                    QWidget {
                        background-color: rgba(255, 255, 255, 0);
                    }

                """
            elif styleType == "hoverSelected":
                ssheet = """
                    QWidget#texture {
                        border: 1px solid rgb(120, 130, 150);
                        background-color: rgba(255, 255, 255, 50);
                        border-radius: 10px;
                    }
                    QWidget {
                        background-color: rgba(255, 255, 255, 0);
                    }

                """
            elif styleType == "hover":
                ssheet += """
                    QWidget {
                        background-color: rgba(255, 255, 255, 0);
                    }
                    QWidget#texture {
                        background-color: rgba(255, 255, 255, 20);
                    }
                """

            self.setStyleSheet(ssheet)

        @err_catcher(name=__name__)
        def mousePressEvent(self, event: Any) -> None:
            """Handle mouse press by selecting widget.
            
            Args:
                event: Mouse event
            """
            self.select(event)

        @err_catcher(name=__name__)
        def mouseReleaseEvent(self, event: Any) -> None:
            """Handle mouse release by emitting signalReleased.
            
            Args:
                event: Mouse event
            """
            self.signalReleased.emit(self)

        @err_catcher(name=__name__)
        def enterEvent(self, event: Any) -> None:
            """Handle mouse enter by applying hover style.
            
            Args:
                event: Enter event
            """
            if self.isSelected():
                self.applyStyle("hoverSelected")
            else:
                self.applyStyle("hover")

        @err_catcher(name=__name__)
        def leaveEvent(self, event: Any) -> None:
            """Handle mouse leave by restoring current style.
            
            Args:
                event: Leave event
            """
            self.applyStyle(self.status)

        @err_catcher(name=__name__)
        def deselect(self) -> None:
            """Deselect widget and apply deselected style."""
            self.status = "deselected"
            self.applyStyle(self.status)

        @err_catcher(name=__name__)
        def select(self, event: Optional[Any] = None) -> None:
            """Select widget, emit signal, and apply selected style.
            
            Args:
                event: Mouse event (optional)
            """
            wasSelected = self.isSelected()
            self.signalSelect.emit(self, event)
            if not wasSelected:
                self.status = "selected"
                self.applyStyle(self.status)
                self.setFocus()

        @err_catcher(name=__name__)
        def isSelected(self) -> bool:
            """Check if widget is currently selected.
            
            Returns:
                True if selected, False otherwise
            """
            return self.status == "selected"

        def mouseDoubleClickEvent(self, event: Any) -> None:
            """Handle double click to open project.
            
            Args:
                event: Mouse event
            """
            super(Projects.ProjectWidget, self).mouseDoubleClickEvent(event)
            if event.button() == Qt.LeftButton:
                self.signalDoubleClicked.emit(self)

            event.accept()

        @err_catcher(name=__name__)
        def getContextMenu(self) -> QMenu:
            """Create context menu with project operations.
            
            Returns:
                QMenu with capture/browse/paste preview, favorite, explorer, copy path actions
            """
            menu = QMenu(self._parent)

            selectedProjects = self._parent.getSelectedItems()

            copAct = QAction("Capture project image", self)
            copAct.triggered.connect(self.captureProjectPreview)
            menu.addAction(copAct)
            if len(selectedProjects) > 1:
                copAct.setEnabled(False)

            copAct = QAction("Browse project image...", self)
            copAct.triggered.connect(self.browseProjectPreview)
            menu.addAction(copAct)
            if len(selectedProjects) > 1:
                copAct.setEnabled(False)

            clipAct = QAction("Paste project image from clipboard", self)
            clipAct.triggered.connect(self.pasteProjectPreviewFromClipboard)
            menu.addAction(clipAct)
            if len(selectedProjects) > 1:
                clipAct.setEnabled(False)

            if "source" in self.data and self.data["source"] == "recent" and self.allowRemove:
                expAct = QAction("Delete from recent", self._parent)
                expAct.triggered.connect(self.deleteRecent)
                menu.addAction(expAct)

            favAct = QAction("Favorite", self._parent)
            favAct.setCheckable(True)
            favAct.setChecked(self.data.get("favorite", False))
            favAct.toggled.connect(self.onFavoriteToggled)
            menu.addAction(favAct)

            expAct = QAction("Open in Explorer", self._parent)
            expAct.triggered.connect(self.onOpenExplorerClicked)
            menu.addAction(expAct)

            copAct = QAction("Copy path", self._parent)
            copAct.triggered.connect(self.onCopyPathClicked)
            menu.addAction(copAct)

            self.core.callback(
                name="projectWidgetGetContextMenu",
                args=[self, menu],
            )
            return menu

        @err_catcher(name=__name__)
        def onFavoriteToggled(self, state: bool) -> None:
            """Handle favorite toggle for selected project(s).
            
            Args:
                state: New favorite state
            """
            items = self._parent.getSelectedItems()
            for item in items:
                item.data["favorite"] = state
                item.core.projects.setFaroriteProject(item.data["configPath"], state)
                item.refreshUi()

            self._parent.dirty = True

        @err_catcher(name=__name__)
        def onOpenExplorerClicked(self) -> None:
            """Open Explorer/Finder at project config path for selected projects."""
            items = self._parent.getSelectedItems()
            for item in items:
                self.core.openFolder(item.data["configPath"])

        @err_catcher(name=__name__)
        def onCopyPathClicked(self) -> None:
            """Copy project config paths of selected projects to clipboard.
            
            Multiple paths separated by OS path separator.
            """
            items = self._parent.getSelectedItems()
            text = os.pathsep.join(item.data["configPath"] for item in items)
            self.core.copyToClipboard(text)

        @err_catcher(name=__name__)
        def rightClicked(self, pos: Any) -> None:
            """Show context menu at cursor position.
            
            Args:
                pos: Click position
            """
            if not self.data.get("configPath"):
                return

            menu = self.getContextMenu()
            if not menu or menu.isEmpty():
                return

            if hasattr(self._parent, "allowClose"):
                self._parent.allowClose = False

            menu.exec_(QCursor.pos())

            if hasattr(self._parent, "allowClose"):
                self._parent.allowClose = True

        @err_catcher(name=__name__)
        def browseProjectPreview(self) -> None:
            """Browse for project preview image file (jpg/png/exr) and set as preview.
            
            Scales image to standard preview size and saves to project.
            """
            formats = "Image File (*.jpg *.png *.exr)"

            imgPath = QFileDialog.getOpenFileName(
                self, "Select preview-image", os.path.dirname(self.data["configPath"]), formats
            )[0]

            if not imgPath:
                return

            if os.path.splitext(imgPath)[1] == ".exr":
                previewImg = self.core.media.getPixmapFromExrPath(
                    imgPath, width=self.core.projects.previewWidth, height=self.core.projects.previewHeight
                )
            else:
                previewImg = self.core.media.getPixmapFromPath(imgPath)
                if previewImg.width() == 0:
                    warnStr = "Cannot read image: %s" % imgPath
                    self.core.popup(warnStr)
                    return

            previewImg = self.core.media.scalePixmap(previewImg, width=self.core.projects.previewWidth, height=self.core.projects.previewHeight, fitIntoBounds=False)
            rect = QRect(0, 0, self.core.projects.previewWidth, self.core.projects.previewHeight)
            cropped = previewImg.copy(rect)
            self.core.projects.saveProjectImage(projectConfig=self.data["configPath"], image=cropped)
            self.validPreview = None
            self.updatePreview()

        @err_catcher(name=__name__)
        def captureProjectPreview(self) -> None:
            """Capture screen area as project preview image.
            
            Hides window temporarily, captures screen area, scales to standard size,
            and saves as project preview.
            """
            from PrismUtils import ScreenShot
            self.window().setWindowOpacity(0)

            previewImg = ScreenShot.grabScreenArea(self.core)
            self.window().setWindowOpacity(1)

            if previewImg:
                previewImg = self.core.media.scalePixmap(previewImg, width=self.core.projects.previewWidth, height=self.core.projects.previewHeight, fitIntoBounds=False)
                rect = QRect(0, 0, self.core.projects.previewWidth, self.core.projects.previewHeight)
                cropped = previewImg.copy(rect)
                self.core.projects.saveProjectImage(projectConfig=self.data["configPath"], image=cropped)
                self.validPreview = None
                self.updatePreview()

        @err_catcher(name=__name__)
        def pasteProjectPreviewFromClipboard(self) -> None:
            """Paste image from clipboard as project preview.
            
            Scales to standard preview size and saves to project.
            """
            pmap = self.core.media.getPixmapFromClipboard()
            if not pmap:
                self.core.popup("No image in clipboard.", parent=self._parent)
                return

            pmap = self.core.media.scalePixmap(pmap, width=self.core.projects.previewWidth, height=self.core.projects.previewHeight, fitIntoBounds=False)
            rect = QRect(0, 0, self.core.projects.previewWidth, self.core.projects.previewHeight)
            cropped = pmap.copy(rect)
            self.core.projects.saveProjectImage(projectConfig=self.data["configPath"], image=cropped)
            self.validPreview = None
            self.updatePreview()

        @err_catcher(name=__name__)
        def deleteRecent(self) -> None:
            """Remove selected projects from recent projects list."""
            items = self._parent.getSelectedItems()
            for item in items:
                self.core.projects.setRecentPrj(item.data["configPath"], action="remove")
            
            self.signalRemoved.emit()

    class RoundedLabel(QLabel):
        """QLabel with rounded bottom corners for project previews."""

        def paintEvent(self, event: Any) -> None:
            """Paint event with rounded corners.
            
            Args:
                event: Paint event
            """
            pm = self.pixmap()
            if pm:
                painter = QPainter(self)
                painter.setRenderHint(QPainter.Antialiasing, True)
                painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
                brush = QBrush(self.pixmap())
                painter.setBrush(brush)
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(1, 1, self.width()-2, self.height(), 10, 10)
                painter.drawRect(1, int(self.height() / 2), self.width()-2, self.height())
            else:
                super(Projects.RoundedLabel, self).paintEvent(event)

    class HelpLabel(QLabel):
        """QLabel that shows tooltip on mouse move."""

        def mouseMoveEvent(self, event: Any) -> None:
            """Show tooltip on mouse move.
            
            Args:
                event: Mouse event
            """
            QToolTip.showText(QCursor.pos(), self.toolTip())
