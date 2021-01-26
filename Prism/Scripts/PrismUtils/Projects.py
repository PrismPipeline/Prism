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
import glob
import imp
import logging
import shutil
from collections import OrderedDict

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class Projects(object):
    def __init__(self, core):
        super(Projects, self).__init__()
        self.core = core

    @err_catcher(name=__name__)
    def setProject(self, startup=None, openUi=""):
        try:
            del sys.modules["SetProject"]
        except:
            pass

        try:
            import SetProject
        except:
            modPath = imp.find_module("SetProject")[1]
            if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
                os.remove(modPath)
            import SetProject

        if startup is None:
            startup = self.core.status == "starting"

        self.dlg_setProject = SetProject.SetProject(core=self.core, openUi=openUi)
        if not startup:
            self.dlg_setProject.projectsUi.chb_startup.setVisible(False)

        self.dlg_setProject.show()

    @err_catcher(name=__name__)
    def openProject(self):
        if self.core.prismIni == "":
            path = QFileDialog.getExistingDirectory(
                self.core.messageParent, "Select existing project folder"
            )
        else:
            path = QFileDialog.getExistingDirectory(
                self.core.messageParent,
                "Select existing project folder",
                os.path.abspath(os.path.join(self.core.prismIni, os.pardir, os.pardir)),
            )

        if not path:
            return

        if os.path.basename(path) == "00_Pipeline":
            path = os.path.join(path, "pipeline.yml")
        else:
            path = os.path.join(path, "00_Pipeline", "pipeline.yml")

        self.core.configs.findDeprecatedConfig(path)

        if os.path.exists(path):
            try:
                self.dlg_setProject.close()
            except:
                pass
            self.changeProject(path, openUi="projectBrowser")
        else:
            self.core.popup("Invalid project folder")

    @err_catcher(name=__name__)
    def changeProject(self, configPath=None, openUi="", settingsTab=2, unset=False):
        if not unset:
            if configPath is None:
                return

            if sys.version[0] == "3":
                if not isinstance(configPath, str):
                    return
            else:
                if not isinstance(configPath, basestring):
                    return

            if os.path.isdir(configPath):
                if os.path.basename(configPath) == "00_Pipeline":
                    configPath = os.path.join(configPath, "pipeline.yml")
                else:
                    configPath = os.path.join(configPath, "00_Pipeline", "pipeline.yml")

            configPath = self.core.configs.findDeprecatedConfig(configPath) or configPath

            if not os.path.exists(configPath):
                self.core.popup("Cannot set project. File doesn't exist:\n\n%s" % configPath)
                return

            configPath = self.core.fixPath(configPath)
            projectPath = os.path.abspath(
                os.path.join(configPath, os.pardir, os.pardir)
            )
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
                self.core.getConfig("globals", "prism_version", configPath=configPath) or ""
            )

            if not projectName:
                self.core.popup("The project config doesn't contain the \"project_name\" setting.\n\nCannot open project.")
                return

        delModules = []

        for i in sys.path:
            if self.core.prismIni != "" and os.path.dirname(self.core.prismIni) in i:
                delModules.append(i)

        for i in delModules:
            sys.path.remove(i)

        if hasattr(self.core, "projectPath"):
            modulePath = os.path.join(
                self.core.projectPath, "00_Pipeline", "CustomModules", "Python"
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

        try:
            if getattr(self.core, "pb", None) and self.core.pb.isVisible():
                self.core.pb.close()
                openPb = True
        except:
            pass

        if getattr(self.core, "sm", None):
            if self.core.sm.isVisible():
                openSm = True
            self.core.closeSM()

        try:
            if hasattr(self.core.projects, "dlg_setProject") and self.core.projects.dlg_setProject.isVisible():
                self.core.projects.dlg_setProject.close()
        except:
            pass

        try:
            if getattr(self.core, "ps", None) and self.core.ps.isVisible():
                self.core.ps.close()
                openPs = True
        except:
            pass

        self.core.pb = None
        self.core.sm = None
        self.core.ps = None
        self.core.dv = None

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
            return

        self.core.prismIni = configPath
        self.core.projectPath = projectPath
        self.core.projectName = projectName
        self.core.projectVersion = projectVersion

        self.core.configs.clearCache()

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
                    return

            self.core.localProjectPath = self.core.fixPath(self.core.localProjectPath)
            if not self.core.localProjectPath.endswith(os.sep):
                self.core.localProjectPath += os.sep

        if configPath != self.core.getConfig("globals", "current project"):
            self.core.setConfig("globals", "current project", configPath)

        self.core.versionPadding = self.core.getConfig("globals", "versionPadding", dft=self.core.versionPadding, configPath=configPath)
        self.core.framePadding = self.core.getConfig("globals", "framePadding", dft=self.core.framePadding, configPath=configPath)
        self.core.versionFormatVan = self.core.getConfig("globals", "versionFormat", dft=self.core.versionFormatVan, configPath=configPath)
        self.core.versionFormat = self.core.versionFormatVan.replace("#", "%0{}d".format(self.core.versionPadding))

        self.core._scenePath = None
        self.core._shotPath = None
        self.core._assetPath = None
        self.core._texturePath = None

        self.core.callbacks.registerProjectHooks()

        logger.debug("Loaded project " + self.core.projectPath)

        modulePath = os.path.join(
            self.core.projectPath, "00_Pipeline", "CustomModules", "Python"
        )
        if not os.path.exists(modulePath):
            os.makedirs(modulePath)

        sys.path.append(modulePath)

        pluginPath = os.path.join(self.core.projectPath, "00_Pipeline", "Plugins")
        if os.path.exists(pluginPath):
            self.core.plugins.loadPlugins(directories=[pluginPath], recursive=True)

        sep = self.core.getConfig("globals", "filenameseparator", configPath=self.core.prismIni)
        if not sep:
            sep = self.core.getConfig(
                "globals", "filenameseperator", configPath=self.core.prismIni
            )
        if sep:
            self.core.filenameSeparator = self.core.validateStr(
                sep, allowChars=[self.core.filenameSeparator]
            )

        ssep = self.core.getConfig("globals", "sequenceseparator", configPath=self.core.prismIni)
        if ssep:
            self.core.sequenceSeparator = self.core.validateStr(
                ssep, allowChars=[self.core.sequenceSeparator]
            )

            if ssep != self.core.sequenceSeparator and ssep == self.core.filenameSeparator:
                self.core.popup(
                    "The filenameSeparator and the sequenceSeparator are equal. Because this would cause problems the sequenceSeparator will be set to \"%s\"" % self.core.sequenceSeparator
                )

        self.setRecentPrj(configPath)
        self.core.sanities.checkAppVersion()
        self.core.checkCommands()
        self.core.updateProjectEnvironment()
        self.core.callback(
            name="onProjectChanged",
            types=["curApp", "custom", "prjManagers"],
            args=[self.core],
        )

        if self.core.uiAvailable:
            if openPb or openUi == "projectBrowser":
                self.core.projectBrowser()

            if openSm or openUi == "stateManager":
                self.core.stateManager()

            if openPs or openUi == "prismSettings":
                self.core.prismSettings()
                self.core.ps.tw_settings.setCurrentIndex(settingsTab)

        return self.core.projectPath

    @err_catcher(name=__name__)
    def getUseLocalFiles(self, projectConfig=None):
        if not projectConfig:
            projectConfig = self.core.prismIni

        prjUseLocal = self.core.getConfig("globals", "uselocalfiles", dft=False, configPath=projectConfig)
        userUseLocal = self.core.getConfig("useLocalFiles", self.core.projectName, dft="inherit")
        if userUseLocal == "inherit":
            useLocal = prjUseLocal
        elif userUseLocal == "on":
            useLocal = True
        else:
            useLocal = False

        return useLocal

    @err_catcher(name=__name__)
    def setRecentPrj(self, path, action="add"):
        path = self.core.fixPath(path)

        recentProjects = self.getRecentProjects(includeCurrent=True)
        if recentProjects and path == recentProjects[0]["configPath"] and action == "add":
            return

        newRecenetProjects = []

        for prj in recentProjects:
            if prj["configPath"] != path:
                newRecenetProjects.append(prj)

        if action == "add":
            prjData = {"configPath": path}
            prjData["name"] = self.core.getConfig("globals", "project_name", configPath=path)
            newRecenetProjects = [prjData] + newRecenetProjects

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

                configPath = os.path.splitext(self.core.fixPath(project))[0] + self.core.configs.preferredExtension
                prjData = {"configPath": configPath}
                prjData["name"] = self.core.getConfig("globals", "project_name", configPath=configPath)
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
            self.core.setConfig(param="recent_projects", val=validProjects, config="user")

        return validProjects

    @err_catcher(name=__name__)
    def createProjectDialog(self, name=None, path=None, settings={}):
        try:
            del sys.modules["CreateProject"]
        except:
            pass

        try:
            self.cp.close()
        except:
            pass

        try:
            import CreateProject
        except:
            modPath = imp.find_module("CreateProject")[1]
            if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
                os.remove(modPath)
            import CreateProject

        if name is not None and path is not None:
            return CreateProject.createProject(
                core=self.core, name=name, path=path, settings=settings
            )
        else:
            self.cp = CreateProject.CreateProject(core=self.core)
            self.cp.show()

        return self.cp

    @err_catcher(name=__name__)
    def createProject(self, name, path, settings=None):
        prjName = name
        prjPath = path
        settings = settings or {}

        dftSteps = OrderedDict([
            ("cpt", "Concept"),
            ("mod", "Modeling"),
            ("ldv", "Lookdev"),
            ("rig", "Rigging"),
            ("lay", "Layout"),
            ("anm", "Animation"),
            ("fx", "Effects"),
            ("cfx", "CharacterEffects"),
            ("lgt", "Lighting"),
            ("cmp", "Compositing"),
            ("edt", "Editing"),
            ("dev", "Development"),
        ])
        pipeline_steps = settings.get("pipeline_steps", dftSteps)

        uselocalfiles = settings.get("uselocalfiles", False)
        trackDependencies = settings.get("track_dependencies", "publish")
        checkframerange = settings.get("checkframerange", True)
        forcefps = settings.get("forcefps", False)
        fps = settings.get("fps", 24)
        forceversions = settings.get("forceversions", False)
        filenameseparator = settings.get("filenameseparator", "_")
        sequenceseparator = settings.get("sequenceseparator", "-")
        forceResolution = settings.get("forceResolution", False)
        resolution = settings.get("resolution", [1920, 1080])
        resolutionPresets = settings.get("resolutionPresets") or [
            "3840x2160",
            "1920x1080",
            "1280x720",
            "960x540",
            "640x360",
        ]
        projectFolders = settings.get("projectFolders", self.getDefaultProjectFolders())

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
                self.core.popup("The project folder could not be created")
                return
        else:
            if not os.listdir(prjPath) == []:
                if self.core.uiAvailable:
                    mStr = "The project folder is not empty.\nExisting files will be overwritten.\n"
                    msg = QMessageBox(
                        QMessageBox.Warning, "Project setup", mStr, QMessageBox.Cancel
                    )
                    msg.addButton("Continue", QMessageBox.YesRole)
                    self.core.parentWindow(msg)
                    action = msg.exec_()

                    if action != 0:
                        return
                else:
                    self.core.popup("Project directory already exists.")
                    if glob.glob(
                        os.path.join(prjPath, "00_Pipeline", "pipeline.*")
                    ):
                        return True
                    else:
                        return

        # check if all required folders are defined
        req = ["Scenes*", "Assets*"]

        for i in req:
            if i not in [x[1] for x in projectFolders]:
                self.core.popup("Not all required folders are defined")
                return

        # create folders

        pPath = os.path.join(prjPath, "00_Pipeline")

        if os.path.exists(pPath):
            try:
                if self.enableCleanup:
                    shutil.rmtree(pPath)
                else:
                    self.core.popup('Projects Exists "%s"' % pPath)
            except:
                self.core.popup('Could not remove folder "%s"' % pPath)
                return

        try:
            shutil.copytree(
                os.path.abspath(
                    os.path.join(self.core.prismRoot, "ProjectFiles")
                ),
                pPath,
            )
        except Exception as e:
            self.core.popup("Could not copy folders to %s.\n\n%s" % (pPath, str(e)))
            return

        for i in (
            pf
            for pf in projectFolders
            if not os.path.exists(os.path.join(prjPath, pf[0]))
        ):
            try:
                os.makedirs(os.path.join(prjPath, i[0]))
            except:
                self.core.popup('Could not create folder "%s"' % i[0])
                return

        # create config

        configPath = os.path.join(pPath, "pipeline.yml")
        for i in projectFolders:
            if i[1] == "Scenes*":
                scname = i[0]
            if i[1] == "Assets*":
                assetname = i[0]
            if i[1] == "Dailies":
                dailiesname = i[0]

        cfolders = [
            os.path.join(prjPath, scname, "Assets"),
            os.path.join(prjPath, scname, "Shots"),
            os.path.join(prjPath, assetname, "Textures"),
            os.path.join(prjPath, assetname, "HDAs"),
        ]

        for i in cfolders:
            if not os.path.exists(i):
                os.makedirs(i)

        cData = OrderedDict([
            ("globals", OrderedDict([
                ("project_name", prjName),
                ("prism_version", self.core.version),
                ("pipeline_steps", pipeline_steps),
                ("uselocalfiles", uselocalfiles),
                ("track_dependencies", trackDependencies),
                ("checkframerange", checkframerange),
                ("forcefps", forcefps),
                ("fps", fps),
                ("forceversions", forceversions),
                ("filenameseparator", filenameseparator),
                ("sequenceseparator", sequenceseparator),
                ("forceResolution", forceResolution),
                ("resolution", resolution),
                ("resolutionPresets", resolutionPresets),
            ])),
            ("paths", OrderedDict([
                ("pipeline", "00_Pipeline"),
                ("scenes", scname),
                ("assets", assetname),
            ])),
            ("defaultpasses", OrderedDict([]),)
        ])

        if "dailiesname" in locals():
            cData["paths"]["dailies"] = dailiesname

        for i in self.core.getPluginNames():
            passes = self.core.getPluginData(i, "renderPasses")
            if type(passes) == dict:
                cData["defaultpasses"].update(passes)

        self.core.setConfig(data=cData, configPath=configPath)
        self.core.callback(
            name="onProjectCreated",
            types=["curApp", "unloadedApps", "custom"],
            args=[self, prjPath, prjName],
        )
        return True

    @err_catcher(name=__name__)
    def getDefaultProjectFolders(self):
        folders = [
            ["01_Management", "Default"],
            ["02_Designs", "Default"],
            ["03_Workflow", "Scenes*"],
            ["04_Assets", "Assets*"],
            ["05_Dailies", "Dailies"],
        ]

        return folders

    @err_catcher(name=__name__)
    def ensureProject(self, openUi=""):
        if getattr(self.core, "projectPath", None) and os.path.exists(self.core.prismIni):
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
        hasPrj = getattr(self.core, "projectPath", None) and os.path.exists(self.core.prismIni)
        return hasPrj

    @err_catcher(name=__name__)
    def hasActiveProject(self):
        return hasattr(self.core, "projectPath")
