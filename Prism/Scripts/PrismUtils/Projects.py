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
import shutil
import platform
import time
import glob
import re
from collections import OrderedDict
from distutils.dir_util import copy_tree

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class Projects(object):
    def __init__(self, core):
        super(Projects, self).__init__()
        self.core = core
        self.dlg_settings = None
        self.extraStructureItems = OrderedDict([])
        self.environmentVariables = []
        self.previewWidth = 640
        self.previewHeight = 360

    @err_catcher(name=__name__)
    def setProject(self, startup=None, openUi=""):
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
    def setPrism1Compatibility(self, state):
        if state:
            self.core.prism1Compatibility = True
            logger.debug("activating Prism 1 compatibility")
        else:
            self.core.prism1Compatibility = False
            logger.debug("deactivating Prism 1 compatibility")

    @err_catcher(name=__name__)
    def isPrism1Project(self, path):
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
    def openProject(self, parent=None):
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
    def changeProject(self, configPath=None, openUi="", settingsTab=None, settingsType=None, unset=False):
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
            projectPath = str(os.path.abspath(
                os.path.join(configPath, os.pardir, os.pardir)
            ))
            if not projectPath.endswith(os.sep):
                projectPath += os.sep

            configData = self.core.getConfig(configPath=configPath)
            if configData is None:
                logger.debug("unable to read project config: %s" % configPath)
                return

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

        if configPath != self.core.getConfig("globals", "current project") and self.core.uiAvailable:
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

        self.core._scenePath = None
        self.core._shotPath = None
        self.core._sequencePath = None
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

        if self.core.mediaProducts.getUseMaster():
            self.core.entities.addEntityAction(
                key="masterVersionCheckMedia",
                types=["asset", "shot"],
                function=self.core.mediaProducts.checkMasterVersions,
                label="Check Media Master Versions..."
            )

        logger.debug("Loaded project " + self.core.projectPath)

        modulePath = os.path.join(self.getPipelineFolder(), "CustomModules", "Python")
        if not os.path.exists(modulePath):
            try:
                os.makedirs(modulePath)
            except FileExistsError:
                pass

        sys.path.append(modulePath)

        pluginPath = self.getPluginFolder()
        if os.path.exists(pluginPath):
            self.core.plugins.loadPlugins(directories=[pluginPath], recursive=True)

        self.setRecentPrj(configPath)
        self.core.checkCommands()
        self.core.updateProjectEnvironment()
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
        result = self.validateFolderStructure(structure)
        if result is not True:
            msg = "The project structure is invalid. Please update the project settings."
            r = self.core.popupQuestion(msg, buttons=["Open Project Settings...", "Close"], default="Open Project Settings...", escapeButton="Close", icon=QMessageBox.Warning)
            if r == "Open Project Settings...":
                self.core.prismSettings(tab="Folder Structure", settingsType="Project")

        QApplication.setQuitOnLastWindowClosed(quitOnLastWindowClosed)
        return self.core.projectPath

    @err_catcher(name=__name__)
    def refreshLocalFiles(self):
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
    def unloadProjectEnvironment(self, beforeRefresh=False):
        for item in self.environmentVariables:
            if item["orig"] is None:
                if item["key"] in os.environ:
                    del os.environ[item["key"]]
            else:
                os.environ[item["key"]] = item["orig"]

        self.core.callback(name="updatedEnvironmentVars", args=["unloadProject", self.environmentVariables, beforeRefresh])

    @err_catcher(name=__name__)
    def refreshProjectEnvironment(self):
        variables = self.core.getConfig(
            "environmentVariables", config="project", dft={}
        )
        self.environmentVariables = []
        for key in variables:
            val = os.path.expandvars(str(variables[key]))
            res = self.core.callback(name="expandEnvVar", args=[val])
            for r in res:
                if r:
                    val = r

            if key.lower().startswith("ocio") and self.core.appPlugin and self.core.appPlugin.pluginName.lower() == key.split("_")[-1]:
                key = "OCIO"

            item = {
                "key": str(key),
                "value": val,
                "orig": os.getenv(key),
            }
            self.environmentVariables.append(item)
            os.environ[str(key)] = val

        self.core.callback(name="updatedEnvironmentVars", args=["refreshProject", self.environmentVariables])

    @err_catcher(name=__name__)
    def getUseLocalFiles(self, projectConfig=None):
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
    def getDefaultLocalPath(self, projectName=None):
        if not projectName:
            if hasattr(self.core, "projectName"):
                projectName = self.core.projectName
            else:
                projectName = ""

        if platform.system() == "Windows":
            defaultLocalPath = os.path.join(
                self.core.getWindowsDocumentsPath(), "LocalProjects", projectName
            )
        elif platform.system() == "Linux":
            defaultLocalPath = os.path.join(
                os.path.expanduser("~"), "Documents", "LocalProjects", projectName
            )
        elif platform.system() == "Darwin":
            defaultLocalPath = os.path.join(
                os.path.expanduser("~"), "Documents", "LocalProjects", projectName
            )

        return defaultLocalPath

    @err_catcher(name=__name__)
    def setRecentPrj(self, path, action="add"):
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
    def getRecentProjects(self, includeCurrent=False):
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

                validProjects.append(project)

        if deprecated:
            self.core.setConfig(
                param="recent_projects", val=validProjects, config="user"
            )

        return validProjects

    @err_catcher(name=__name__)
    def getAvailableProjects(self, includeCurrent=False):
        projects = self.getRecentProjects(includeCurrent=includeCurrent)
        for project in projects:
            project["source"] = "recent"

        return projects

    @err_catcher(name=__name__)
    def createProjectDialog(self, name=None, path=None, settings=None):
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
                core=self.core, name=name, path=path, settings=settings
            )
        else:
            self.cp = ProjectWidgets.CreateProject(core=self.core)
            self.cp.show()

        return self.cp

    @err_catcher(name=__name__)
    def getDefaultProjectSettings(self):
        dftDepsAsset = [
            {"name": "Concept", "abbreviation": "cpt", "defaultTasks": ["Concept"]},
            {"name": "Modeling", "abbreviation": "mod", "defaultTasks": ["Modeling"]},
            {"name": "Surfacing", "abbreviation": "surf", "defaultTasks": ["Surfacing"]},
            {"name": "Rigging", "abbreviation": "rig", "defaultTasks": ["Rigging"]},
        ]

        dftDepsShot = [
            {"name": "Layout", "abbreviation": "lay", "defaultTasks": ["Layout"]},
            {"name": "Animation", "abbreviation": "anm", "defaultTasks": ["Animation"]},
            {"name": "FX", "abbreviation": "fx", "defaultTasks": ["Effects"]},
            {"name": "CharFX", "abbreviation": "cfx", "defaultTasks": ["CharacterEffects"]},
            {"name": "Lighting", "abbreviation": "lgt", "defaultTasks": ["Lighting"]},
            {"name": "Compositing", "abbreviation": "cmp", "defaultTasks": ["Compositing"]},
        ]

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
                        ]
                    ),
                ),
                ("folder_structure", structure),
                (
                    "defaultpasses",
                    OrderedDict([]),
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
        self, name, path, settings=None, preset="Default", image=None, structure=None, parent=None
    ):
        prjName = name
        prjPath = path.strip(" ")
        settings = settings or {}

        if preset:
            preset = self.getPreset(name=preset)
            projectSettings = preset["settings"]
        else:
            projectSettings = {}

        projectSettings.update(settings)
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
            self.core.popup("The project name is invalid")
            return

        # create project folder
        if not os.path.isabs(prjPath):
            self.core.popup("The project path is invalid")
            return

        if not os.path.exists(prjPath):
            try:
                os.makedirs(prjPath)
            except:
                self.core.popup("The project folder could not be created", parent=parent)
                return
        elif os.listdir(prjPath):
            msg = "The project folder is not empty. How do you want to continue?"
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
                while os.path.exists(prjPath):
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
                copy_tree(preset["path"], prjPath)
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
    def getFolderStructureFromPath(self, projectPath, simple=False):
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
    def createProjectStructure(self, path, entity):
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
                shutil.copy2(childEntity["path"], path)

        return True

    @err_catcher(name=__name__)
    def ensureProject(self, openUi=""):
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
    def hasActiveProject(self):
        return hasattr(self.core, "projectPath")

    @err_catcher(name=__name__)
    def getProjectResolution(self):
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
    def getResolutionPresets(self):
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
        self, tab=0, restart=False, reload_module=False, config=None, projectData=None
    ):
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
    def getDefaultPipelineFolder(self):
        if self.core.prism1Compatibility:
            return "00_Pipeline"

        return os.getenv("PRISM_PROJECT_PIPELINE_FOLDER", "00_Pipeline")

    @err_catcher(name=__name__)
    def getPipelineFolder(self, projectPath=None, structure=None):
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
    def getProjectFolderFromConfigPath(self, configPath):
        folder = os.path.dirname(configPath)
        folder = folder.replace(self.getDefaultPipelineFolder(), "")
        return folder

    @err_catcher(name=__name__)
    def getPluginFolder(self):
        if not getattr(self.core, "projectPath", None):
            pluginPath = ""
        else:
            pluginPath = os.path.join(self.getPipelineFolder(), "Plugins")

        return pluginPath

    @err_catcher(name=__name__)
    def getHookFolder(self):
        return os.path.join(self.getPipelineFolder(), "Hooks")

    @err_catcher(name=__name__)
    def getFallbackFolder(self):
        return os.path.join(self.getPipelineFolder(), "Fallbacks")

    @err_catcher(name=__name__)
    def getConfigFolder(self):
        return os.path.join(self.getPipelineFolder(), "Configs")

    @err_catcher(name=__name__)
    def getPresetFolder(self):
        return os.path.join(self.getPipelineFolder(), "Presets")

    @err_catcher(name=__name__)
    def getDefaultProjectStructure(self):
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
            "requires": ["project_path", "sequence"],
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
            "value": "[expression,#  available variables:\n#  \"core\" - PrismCore\n#  \"context\" - dict\n\nif context.get(\"mediaType\") == \"2drenders\":\n\ttemplate = \"@aov_path@/@asset@_@identifier@_@version@@.(frame)@@extension@\"\nelse:\n\ttemplate = \"@aov_path@/@asset@_@identifier@_@version@_@aov@@.(frame)@@extension@\"]",
            "requires": ["aov_path"],
        }
        structure["renderFilesShots"] = {
            "label": "Shot Renderfiles",
            "key": "@renderfile_path@",
            "value": "[expression,#  available variables:\n#  \"core\" - PrismCore\n#  \"context\" - dict\n\nif context.get(\"mediaType\") == \"2drenders\":\n\ttemplate = \"@aov_path@/@sequence@-@shot@_@identifier@_@version@@.(frame)@@extension@\"\nelse:\n\ttemplate = \"@aov_path@/@sequence@-@shot@_@identifier@_@version@_@aov@@.(frame)@@extension@\"]",
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
            structure[key] = self.extraStructureItems[key].copy()

        return structure

    @err_catcher(name=__name__)
    def getPrism1ProjectStructure(self):
        folderStructure = {
            "pipeline": {
                "value": "@project_path@/00_Pipeline"
            }, 
            "assets": {
                "value": "@project_path@/03_Workflow/Assets/@asset_path@"
            },
            "sequences": {
                "value": "@project_path@/03_Workflow/Shots/@sequence@"
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
    def addProjectStructureItem(self, key, value):
        self.extraStructureItems[key] = value
        return True

    @err_catcher(name=__name__)
    def getProjectStructure(self, projectPath=None, projectStructure=None):
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
    def getStructureValues(self, structure):
        struct = {}
        for key in structure:
            struct[key] = {"value": structure[key]["value"]}

        return struct

    @err_catcher(name=__name__)
    def validateFolderStructure(self, structure):
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
    def validateFolderKey(self, path, item):
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
    def validateExpression(self, expression):
        context = {}
        core = self.core
        try:
            exec(expression, locals(), None)
        except Exception as e:
            result = {"valid": False, "error": str(e)}
            return result
        else:
            if "template" in locals():
                result = {"valid": True}
                return result

        result = {"valid": False, "error": "Make sure \"template\" is defined."}
        return result

    @err_catcher(name=__name__)
    def getTemplatesFromExpression(self, expression, context=None):
        context = context or {}
        core = self.core

        if expression.startswith("[expression,"):
            expression = expression[len("[expression,"):]
            if expression.endswith("]"):
                expression = expression[:-1]

        try:
            exec(expression, locals(), None)
        except Exception as e:
            logger.warning(e)
            return
        else:
            if "template" in locals():
                t = locals()["template"]
                if self.core.isStr(t):
                    t = [t]

                return t

    @err_catcher(name=__name__)
    def getTemplatePath(self, key, default=False):
        if default:
            structure = self.getDefaultProjectStructure()
        else:
            structure = self.getProjectStructure()

        item = structure.get(key)
        if not item:
            return

        return item["value"]

    @err_catcher(name=__name__)
    def setTemplatePath(self, key, value):
        structure = self.getProjectStructure()
        item = structure.get(key)
        if not item:
            self.core.popup("Invalid key: %s" % key)
            return

        item["value"] = value
        self.core.setConfig("folder_structure", val=structure, config="project")
        return True

    @err_catcher(name=__name__)
    def getResolvedProjectStructurePath(self, key, context=None, structure=None, fallback=None):
        resolvedPaths = self.getResolvedProjectStructurePaths(key, context, structure, fallback)
        if not resolvedPaths:
            return resolvedPaths

        resolvedPath = resolvedPaths[0]
        return resolvedPath

    @err_catcher(name=__name__)
    def getResolvedProjectStructurePaths(self, key, context=None, structure=None, fallback=None):
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
            return False

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
    def resolveStructurePath(self, path, context=None, structure=None, addProjectPath=True, fillContextKeys=True, fallback=None):
        context = context or {}
        if "project_path" in context:
            if structure is None:
                prjPath = self.core.convertPath(context["project_path"], "global")
        elif addProjectPath:
            context["project_path"] = os.path.normpath(self.core.projectPath)
            prjPath = context["project_path"]
        else:
            if structure is None:
                prjPath = os.path.normpath(self.core.projectPath)

        if "project_path" in context and "project_name" not in context:
            if hasattr(self.core, "projectPath") and context["project_path"] == self.core.projectPath:
                context["project_name"] = self.core.projectName
            else:
                cfgPath = self.core.configs.getProjectConfigPath(context["project_path"])
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
                                print(piece)
                                print(context)
                            try:
                                newPath = resolvedPath + resolvedPiece
                            except:
                                print(piece)
                                print(context)
                                print(resolvedPath)
                                print(resolvedPiece)
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
    def resolveStructurePiece(self, key, structure, context, fillContextKeys=True, fallback=None):
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
    def getTemplateKeys(self, template):
        return template.split("@")[1::2]

    @err_catcher(name=__name__)
    def extractKeysFromPath(self, path, template, context=None):
        template = self.resolveStructurePath(template, context=context, addProjectPath=False, fillContextKeys=False)[0]
        template = os.path.normpath(template)
        path = os.path.normpath(path)
        keys = self.getTemplateKeys(template)
        extKey = "@extension@"
        if template.endswith(extKey):
            template = template[:-len(extKey)]
            path, extension = self.core.paths.splitext(path)
        else:
            extension = ""

        rePath = template
        rePath = re.escape(rePath)

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

        rmatch = re.match(rePath, path, re.IGNORECASE)
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
    def getMatchingPaths(self, template):
        template = os.path.normpath(template)
        keys = self.getTemplateKeys(template)
        globPath = template
        for key in keys:
            globPath = globPath.replace("@%s@" % key, "*")

        matches = glob.glob(globPath)

        extKey = "@extension@"
        if template.endswith(extKey):
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

            pathData.append(data)

        return pathData

    @err_catcher(name=__name__)
    def getProjectImage(self, projectPath=None, projectConfig=None, validate=True, structure=None):
        if not projectPath and projectConfig:
            projectPath = self.getProjectFolderFromConfigPath(projectConfig)

        pipeDir = self.getPipelineFolder(projectPath=projectPath, structure=structure)
        path = os.path.join(pipeDir, "project.jpg")
        if not validate or os.path.exists(path):
            return path
        else:
            return

    @err_catcher(name=__name__)
    def saveProjectImage(self, projectPath=None, projectConfig=None, image=None):
        if not projectPath and projectConfig:
            projectPath = self.getProjectFolderFromConfigPath(projectConfig)

        imagePath = self.getProjectImage(projectPath, validate=False)
        self.core.media.savePixmap(image, imagePath)
        return imagePath

    @err_catcher(name=__name__)
    def getRootPresetPath(self):
        path = os.path.join(self.core.prismRoot, "Presets", "Projects")
        return path

    @err_catcher(name=__name__)
    def getUserPresetPath(self):
        dft = os.path.join(os.path.dirname(self.core.userini), "Presets", "Projects")
        path = os.getenv("PRISM_PROJECT_PRESETS_PATH", dft)
        return path

    @err_catcher(name=__name__)
    def getPresetPaths(self):
        paths = []
        paths.append(self.getRootPresetPath())
        paths.append(self.getUserPresetPath())
        return paths

    @err_catcher(name=__name__)
    def getPresets(self):
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
    def getPreset(self, name=None, path=None):
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
    def deletePreset(self, name=None, path=None):
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
    def createPresetFromFolder(self, name, path):
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
    def createPresetFromSettings(self, name, settings, structure, dft=None):
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
    def validateProjectPresetConfig(self, presetPath, configPath, dft=None):
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
    def getProjectDepartments(self):
        steps = self.core.getConfig(
            "globals", "pipeline_steps", configPath=self.core.prismIni
        )

        try:
            dict(steps)
        except:
            steps = {}

        return steps

    @err_catcher(name=__name__)
    def getAssetDepartments(self, configData=None):
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
            deps = [{"name": d[1], "abbreviation": d[0], "defaultTasks": [d[1]]} for d in list(deps.items())]
            self.setDepartments("asset", deps, configData)

        return deps

    @err_catcher(name=__name__)
    def getShotDepartments(self, configData=None):
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
            deps = [{"name": d[1], "abbreviation": d[0], "defaultTasks": [d[1]]} for d in list(deps.items())]
            self.setDepartments("shot", deps, configData)

        return deps

    @err_catcher(name=__name__)
    def addDepartment(self, entity, name, abbreviation, defaultTasks=None, configData=None):
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
    def setDepartments(self, entity, departments, configData=None):
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
    def getDefaultCodePresets(self):
        presets = [
            {
                "name": "Show Message",
                "code": "pcore.popup(\"Hello World\")"
            }
        ]
        return presets

    @err_catcher(name=__name__)
    def getCodePresets(self):
        dft = self.getDefaultCodePresets()
        data = self.core.getConfig(config="codePresets", location="project", dft=dft)
        return data

    @err_catcher(name=__name__)
    def setCodePresets(self, presets):
        self.core.setConfig(data=presets, config="codePresets", location="project")
        return presets

    @err_catcher(name=__name__)
    def addCodePreset(self, name, code=""):
        presets = self.getCodePresets()
        presets = [p for p in presets if p.get("name", "") != name]
        newPreset = {"name": name, "code": code}
        presets.append(newPreset)
        self.setCodePresets(presets)
        return presets

    @err_catcher(name=__name__)
    def removeCodePreset(self, name):
        presets = self.getCodePresets()
        presets = [p for p in presets if p.get("name", "") != name]
        self.setCodePresets(presets)
        return presets

    @err_catcher(name=__name__)
    def getFps(self):
        forceFPS = self.core.getConfig(
            "globals", "forcefps", config="project"
        )
        if not forceFPS:
            return

        pFps = self.core.getConfig("globals", "fps", config="project")
        return pFps

    class ProjectListWidget(QDialog):

        signalShowing = Signal()

        def __init__(self, origin):
            super(Projects.ProjectListWidget, self).__init__()
            self.origin = origin
            self.core = origin.core
            self.projectWidgets = []
            self.allowClose = True
            self.allowDeselect = True
            self.allowMultiSelection = True
            self.core.parentWindow(self, parent=origin)
            self.setupUi()
            self.refreshUi()
            self.core.callback(name="onProjectListStartup", args=[self])

        @err_catcher(name=__name__)
        def focusInEvent(self, event):
            self.activateWindow()

        @err_catcher(name=__name__)
        def focusOutEvent(self, event):
            if self.allowClose:
                self.close()

        @err_catcher(name=__name__)
        def showWidget(self):
            self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.setStyleSheet("QDialog { border: 1px solid rgb(70, 90, 120); }")

            for widget in self.projectWidgets:
                if widget.data.get("configPath", None) == self.core.prismIni:
                    widget.select()

            self.show()
            QApplication.processEvents()
            self.setFocus()
            self.resize(self.w_projects.width() + self.lo_projects.contentsMargins().left() * 2, self.height())        

        @err_catcher(name=__name__)
        def setupUi(self):
            self.setFocusPolicy(Qt.StrongFocus)

            self.w_projects = QWidget()
            self.w_projects.setFocusProxy(self)
            self.lo_projects = QGridLayout()
            self.lo_projects.setSpacing(10)
            self.lo_projects.setContentsMargins(15, 9, 15, 9)
            self.w_projects.setLayout(self.lo_projects)
            self.lo_main = QVBoxLayout()
            self.lo_main.setContentsMargins(0, 0, 0, 0)
            self.setLayout(self.lo_main)

            self.w_scrollParent = QWidget()
            self.w_scrollParent.setFocusProxy(self)
            self.lo_scrollParent = QHBoxLayout()
            self.sa_projects = QScrollArea()
            self.sa_projects.setFocusProxy(self)
            self.sa_projects.setWidgetResizable(True)
            self.sa_projects.setWidget(self.w_projects)
            self.sa_projects.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.w_scrollParent.setLayout(self.lo_scrollParent)
            self.lo_scrollParent.addWidget(self.sa_projects)
            self.lo_main.addWidget(self.w_scrollParent)

        @err_catcher(name=__name__)
        def refreshUi(self):
            self.projectWidgets = []
            for idx in reversed(range(self.lo_projects.count())):
                item = self.lo_projects.takeAt(idx)
                w = item.widget()
                if w:
                    w.setParent(None)
                    w.deleteLater()

            self.projects = self.core.projects.getAvailableProjects(includeCurrent=True)
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

            path = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
            )
            data = {"name": "Create New Project", "icon": path}
            self.w_new = Projects.ProjectWidget(self, data)
            self.w_new.lo_main.setContentsMargins(0, 10, 0, 0)
            self.w_new.setFocusProxy(self)
            self.w_new.signalDoubleClicked.connect(lambda x: self.preCreate())
            self.w_new.signalSelect.connect(self.itemSelected)
            self.projectWidgets.append(self.w_new)
            self.lo_projects.addWidget(
                self.w_new,
                int(self.lo_projects.count() / 3),
                (self.lo_projects.count() % 3) + 1,
            )
            sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            sizePolicy.setVerticalStretch(1)
            self.w_new.setSizePolicy(sizePolicy)

            path = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "browse.png"
            )
            data = {"name": "Browse Projects", "icon": path}
            self.w_open = Projects.ProjectWidget(self, data)
            self.w_open.lo_main.setContentsMargins(0, 10, 0, 0)
            self.w_open.setFocusProxy(self)
            self.w_open.signalDoubleClicked.connect(lambda x: self.close())
            self.w_open.signalDoubleClicked.connect(lambda x: self.core.projects.openProject(parent=self.origin))
            self.w_open.signalSelect.connect(self.itemSelected)
            self.projectWidgets.append(self.w_open)
            self.lo_projects.addWidget(
                self.w_open,
                int(self.lo_projects.count() / 3),
                (self.lo_projects.count() % 3) + 1,
            )
            sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            sizePolicy.setVerticalStretch(1)
            self.w_open.setSizePolicy(sizePolicy)

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
        def preCreate(self):
            self.core.projects.createProjectDialog()
            if getattr(self.core, "pb", None) and self.core.pb.isVisible():
                self.core.pb.close()

        @err_catcher(name=__name__)
        def itemSelected(self, item, event=None):
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
        def deselectItems(self, ignore=None):
            for item in self.projectWidgets:
                if ignore and item in ignore:
                    continue

                item.deselect()

        @err_catcher(name=__name__)
        def getSelectedProject(self):
            selectedProjects = [x for x in self.projectWidgets if x.isSelected()]
            if not selectedProjects:
                return

            prj = selectedProjects[0]
            return prj

        @err_catcher(name=__name__)
        def getSelectedItems(self):
            items = []
            for item in self.projectWidgets:
                if item.isSelected():
                    items.append(item)

            return items

        @err_catcher(name=__name__)
        def showEvent(self, event):
            self.signalShowing.emit()

        @err_catcher(name=__name__)
        def openProject(self, widget):
            path = widget.data["configPath"]
            if path == self.core.prismIni:
                msg = "This project is already active."
                self.core.popup(msg, parent=self)
                return

            self.close()
            self.core.changeProject(path)

    class ProjectWidget(QWidget):

        signalSelect = Signal(object, object)
        signalReleased = Signal(object)
        signalDoubleClicked = Signal(object)
        signalRemoved = Signal()

        def __init__(self, parent, data, minHeight=200, allowRemove=True, previewScale=1, useWidgetWidth=False):
            super(Projects.ProjectWidget, self).__init__()
            self.core = parent.core
            self.parent = parent
            self.data = data
            self.status = "deselected"
            self.minHeight = minHeight
            self.allowRemove = allowRemove
            self.previewScale = previewScale
            self.useWidgetWidth = useWidgetWidth
            self.previewWidth = int(200 * previewScale)
            self.previewHeight = int((200 * previewScale) / (16/9.0))
            self.setupUi()
            self.refreshUi()

        @err_catcher(name=__name__)
        def sizeHint(self):
            return QSize(1, self.minHeight)

        @err_catcher(name=__name__)
        def resizeEvent(self, event):
            self.updatePreview(load=False)

        @err_catcher(name=__name__)
        def setupUi(self):
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
                self.lo_footer.addWidget(self.l_info)
                self.l_info.setParent(self)
                self.sp_left = QSpacerItem(self.l_info.width(), 0, QSizePolicy.Fixed, QSizePolicy.Fixed)
                self.lo_footer.insertItem(0, self.sp_left)
            else:
                self.lo_footer.addStretch()

        @err_catcher(name=__name__)
        def updatePreview_threaded(self):
            import threading

            self.thread = threading.Thread(target=lambda: self.updatePreview(True))
            self.thread.start()

        @err_catcher(name=__name__)
        def refreshUi(self):
            icon = self.getIcon()
            if icon:
                self.l_icon.setPixmap(icon)
            else:
                self.setLoadingPreview()
                if self.parent.isVisible():
                    self.updatePreview_threaded()
                else:
                    self.parent.signalShowing.connect(self.updatePreview_threaded)

            name = self.getDisplayName()
            self.l_name.setText(name)

        @err_catcher(name=__name__)
        def updatePreview(self, load=True):
            if hasattr(self, "loadingGif"):
                self.loadingGif.setScaledSize(QSize(self.l_preview.width(), self.l_preview.width() / (300/169.0)))

            ppixmap = self.getPreviewImage(load=load)
            if not ppixmap or ppixmap == "loading":
                return

            self.l_preview.setPixmap(ppixmap)

        @err_catcher(name=__name__)
        def setLoadingPreview(self):
            if hasattr(self, "loadingGif"):
                return

            path = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "loading.gif"
            )
            self.loadingGif = QMovie(path, QByteArray(), self) 
            self.loadingGif.setCacheMode(QMovie.CacheAll) 
            self.loadingGif.setSpeed(100) 
            self.loadingGif.setScaledSize(QSize(self.l_preview.width(), self.l_preview.width() / (300/169.0)))
            self.l_preview.setMovie(self.loadingGif)
            self.loadingGif.start()

        @err_catcher(name=__name__)
        def getPreviewImage(self, load=True):
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
        def getIcon(self):
            if "icon" not in self.data:
                return

            icon = self.core.media.getColoredIcon(self.data["icon"], force=True)
            pixmap = icon.pixmap(30, 30)
            return pixmap

        @err_catcher(name=__name__)
        def getDisplayName(self):
            name = self.data["name"]
            return name

        @err_catcher(name=__name__)
        def applyStyle(self, styleType="deselected"):
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
        def mousePressEvent(self, event):
            self.select(event)

        @err_catcher(name=__name__)
        def mouseReleaseEvent(self, event):
            self.signalReleased.emit(self)

        @err_catcher(name=__name__)
        def enterEvent(self, event):
            if self.isSelected():
                self.applyStyle("hoverSelected")
            else:
                self.applyStyle("hover")

        @err_catcher(name=__name__)
        def leaveEvent(self, event):
            self.applyStyle(self.status)

        @err_catcher(name=__name__)
        def deselect(self):
            self.status = "deselected"
            self.applyStyle(self.status)

        @err_catcher(name=__name__)
        def select(self, event=None):
            wasSelected = self.isSelected()
            self.signalSelect.emit(self, event)
            if not wasSelected:
                self.status = "selected"
                self.applyStyle(self.status)
                self.setFocus()

        @err_catcher(name=__name__)
        def isSelected(self):
            return self.status == "selected"

        def mouseDoubleClickEvent(self, event):
            super(Projects.ProjectWidget, self).mouseDoubleClickEvent(event)
            if event.button() == Qt.LeftButton:
                self.signalDoubleClicked.emit(self)

            event.accept()

        @err_catcher(name=__name__)
        def getContextMenu(self):
            menu = QMenu(self.parent)

            selectedProjects = self.parent.getSelectedItems()

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
                expAct = QAction("Delete from recent", self.parent)
                expAct.triggered.connect(self.deleteRecent)
                menu.addAction(expAct)

            expAct = QAction("Open in Explorer", self.parent)
            expAct.triggered.connect(self.onOpenExplorerClicked)
            menu.addAction(expAct)

            copAct = QAction("Copy path", self.parent)
            copAct.triggered.connect(self.onCopyPathClicked)
            menu.addAction(copAct)
            return menu

        @err_catcher(name=__name__)
        def onOpenExplorerClicked(self):
            items = self.parent.getSelectedItems()
            for item in items:
                self.core.openFolder(item.data["configPath"])

        @err_catcher(name=__name__)
        def onCopyPathClicked(self):
            items = self.parent.getSelectedItems()
            text = os.pathsep.join(item.data["configPath"] for item in items)
            self.core.copyToClipboard(text)

        @err_catcher(name=__name__)
        def rightClicked(self, pos):
            if not self.data.get("configPath"):
                return

            menu = self.getContextMenu()
            if hasattr(self.parent, "allowClose"):
                self.parent.allowClose = False

            menu.exec_(QCursor.pos())

            if hasattr(self.parent, "allowClose"):
                self.parent.allowClose = True

        @err_catcher(name=__name__)
        def browseProjectPreview(self):
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
        def captureProjectPreview(self):
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
        def pasteProjectPreviewFromClipboard(self):
            pmap = self.core.media.getPixmapFromClipboard()
            if not pmap:
                self.core.popup("No image in clipboard.", parent=self.parent)
                return

            pmap = self.core.media.scalePixmap(pmap, width=self.core.projects.previewWidth, height=self.core.projects.previewHeight, fitIntoBounds=False)
            rect = QRect(0, 0, self.core.projects.previewWidth, self.core.projects.previewHeight)
            cropped = pmap.copy(rect)
            self.core.projects.saveProjectImage(projectConfig=self.data["configPath"], image=cropped)
            self.validPreview = None
            self.updatePreview()

        @err_catcher(name=__name__)
        def deleteRecent(self):
            items = self.parent.getSelectedItems()
            for item in items:
                self.core.projects.setRecentPrj(item.data["configPath"], action="remove")
            
            self.signalRemoved.emit()

    class RoundedLabel(QLabel):
        def paintEvent(self, event):
            pm = self.pixmap()
            if pm:
                painter = QPainter(self)
                painter.setRenderHint(QPainter.Antialiasing, True)
                brush = QBrush(self.pixmap())
                painter.setBrush(brush)
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(1, 1, self.width()-2, self.height(), 10, 10)
                painter.drawRect(1, self.height() / 2, self.width()-2, self.height())
            else:
                super(Projects.RoundedLabel, self).paintEvent(event)

    class HelpLabel(QLabel):
        def mouseMoveEvent(self, event):
            QToolTip.showText(QCursor.pos(), self.toolTip())
