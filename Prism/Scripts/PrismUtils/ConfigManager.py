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
import platform
import logging
import time

from collections import OrderedDict

if sys.version[0] == "3":
    import collections.abc as collections
    from configparser import ConfigParser
    from io import StringIO
else:
    import collections
    from ConfigParser import ConfigParser
    from StringIO import StringIO

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher
from PrismUtils import Lockfile


logger = logging.getLogger(__name__)


class ConfigManager(object):
    def __init__(self, core):
        self.core = core
        self.cachedConfigs = {}
        self.preferredExtension = self.core.preferredExtension
        self.configItems = {}

        dprConfig = os.path.splitext(self.core.userini)[0] + ".ini"
        if not os.path.exists(self.core.userini) and os.path.exists(dprConfig):
            self.convertDeprecatedConfig(dprConfig)

    @err_catcher(name=__name__)
    def addConfigItem(self, key, path):
        if key in self.configItems:
            return False

        self.configItems[key] = path
        return True

    @err_catcher(name=__name__)
    def getProjectExtension(self):
        if self.core.prism1Compatibility:
            ext = ".yml"
        else:
            ext = self.preferredExtension

        return ext

    @err_catcher(name=__name__)
    def getConfigPath(self, config, location=None):
        if config == "user":
            return self.core.userini
        elif config == "project":
            return self.core.prismIni
        elif config == "omit":
            if self.core.prismIni:
                return os.path.join(
                    self.core.projects.getConfigFolder(),
                    "omits" + self.getProjectExtension(),
                )
        elif config == "shotinfo":
            return os.path.join(
                self.core.projects.getPipelineFolder(),
                "Shotinfo",
                "shotInfo" + self.getProjectExtension(),
            )
        elif config == "assetinfo":
            return os.path.join(
                self.core.projects.getPipelineFolder(),
                "Assetinfo",
                "assetInfo" + self.getProjectExtension(),
            )
        elif config in self.configItems:
            return self.configItems[config]
        else:
            return self.generateConfigPath(name=config, location=location)

    @err_catcher(name=__name__)
    def getProjectConfigName(self, projectPath=None):
        return os.getenv(
            "PRISM_PROJECT_CONFIG_NAME", "pipeline" + self.preferredExtension
        )

    @err_catcher(name=__name__)
    def getProjectConfigPath(self, projectPath=None, pipelineDir=None, useEnv=True):
        projectPath = projectPath or self.core.prismIni
        if (
            self.core.prism1Compatibility
            and getattr(self.core, "projectPath", "") and os.path.normpath(projectPath).startswith(os.path.normpath(self.core.projectPath))
            or self.core.useLocalFiles and os.path.normpath(projectPath).startswith(os.path.normpath(self.core.localProjectPath))
        ):

            configPath = os.path.join(projectPath, "00_Pipeline", "pipeline.yml")
        else:
            configName = self.getProjectConfigName()
            configRelPath = os.getenv("PRISM_PROJECT_CONFIG_PATH")
            if not configRelPath or not useEnv:
                if pipelineDir:
                    pipeDir = pipelineDir
                else:
                    pipeDir = self.core.projects.getDefaultPipelineFolder()
                configRelPath = os.path.join(pipeDir, configName)

            configPath = os.path.join(projectPath, configRelPath)
            if not os.path.exists(configPath):
                configPath2 = os.path.join(projectPath, configName)
                if os.path.exists(configPath2):
                    configPath = configPath2

        return configPath

    @err_catcher(name=__name__)
    def clearCache(self, path=None):
        if path:
            path = os.path.normpath(path)
            self.cachedConfigs.pop(path, None)
        else:
            self.cachedConfigs = {}

    @err_catcher(name=__name__)
    def getCacheTime(self, path):
        if path:
            path = os.path.normpath(path)

        if path not in self.cachedConfigs:
            return

        return self.cachedConfigs[path]["modtime"]

    @err_catcher(name=__name__)
    def createUserPrefs(self):
        if os.path.exists(self.core.userini):
            try:
                os.remove(self.core.userini)
            except:
                pass

        cfgDir = os.path.dirname(self.core.userini)
        if not os.path.exists(cfgDir):
            try:
                os.makedirs(cfgDir)
            except:
                self.core.popup('Failed to create preferences folder: "%s"' % cfgDir)
                return

        uconfig = OrderedDict(
            [
                (
                    "globals",
                    OrderedDict(
                        [
                            ("current project", ""),
                            ("showonstartup", True),
                            ("check_import_versions", True),
                            ("checkframerange", True),
                            ("username", ""),
                            ("autosave", True),
                            ("send_error_reports", True),
                            ("mediaPlayerPath", ""),
                            ("mediaPlayerName", ""),
                            ("checkForUpdates", 7),
                            ("highdpi", False),
                            ("debug_mode", False),
                        ]
                    ),
                ),
                (
                    "nuke",
                    OrderedDict(
                        [
                            ("usenukex", False),
                        ]
                    ),
                ),
                (
                    "blender",
                    OrderedDict(
                        [
                            ("autosaverender", False),
                            ("autosaveperproject", False),
                            ("autosavepath", ""),
                        ]
                    ),
                ),
                (
                    "browser",
                    OrderedDict(
                        [
                            ("closeafterload", True),
                            ("closeafterloadsa", False),
                            ("current", "Assets"),
                            ("assetsVisible", True),
                            ("shotsVisible", True),
                            ("filesVisible", False),
                            ("recentVisible", True),
                            ("rendervisible", True),
                            ("assetsOrder", 0),
                            ("shotsOrder", 1),
                            ("filesOrder", 2),
                            ("recentOrder", 3),
                            ("assetSorting", [1, 1]),
                            ("shotSorting", [1, 1]),
                            ("fileSorting", [1, 1]),
                            ("autoplaypreview", False),
                            ("showmaxassets", True),
                            ("showmayaassets", True),
                            ("showhouassets", True),
                            ("shownukeassets", True),
                            ("showblenderassets", True),
                            ("showmaxshots", True),
                            ("showmayashots", True),
                            ("showhoushots", True),
                            ("shownukeshots", True),
                            ("showblendershots", True),
                        ]
                    ),
                ),
                ("localfiles", OrderedDict([])),
                ("recent_projects", OrderedDict([])),
            ]
        )

        self.setConfig(data=uconfig, configPath=self.core.userini)

        if platform.system() in ["Linux", "Darwin"]:
            if os.path.exists(self.core.userini):
                os.chmod(self.core.userini, 0o777)

    @err_catcher(name=__name__)
    def getConfig(
        self,
        cat=None,
        param=None,
        configPath=None,
        config=None,
        dft=None,
        location=None,
    ):
        if not configPath and config:
            configPath = self.getConfigPath(config, location=location)
        elif configPath is None:
            configPath = self.core.userini

        if configPath:
            configPath = os.path.normpath(configPath)

        if configPath in self.cachedConfigs:
            configData = self.cachedConfigs[configPath]["data"]
            if isinstance(configData, collections.Mapping):
                configData = configData.copy()
        else:
            if not configPath:
                if dft is not None:
                    self.setConfig(
                        cat=cat,
                        param=param,
                        val=dft,
                        configPath=configPath,
                        config=config,
                    )
                return dft

            isUserConfig = configPath == self.core.userini

            if isUserConfig and not os.path.exists(configPath):
                self.createUserPrefs()

            if not os.path.exists(configPath) and not self.findDeprecatedConfig(
                configPath
            ):
                if dft is not None:
                    self.setConfig(
                        cat=cat,
                        param=param,
                        val=dft,
                        configPath=configPath,
                        config=config,
                    )
                return dft

            ext = os.path.splitext(configPath)[1]
            if ext == ".ini":
                configPath = self.convertDeprecatedConfig(configPath)

            configData = self.readConfig(configPath)
            if configData is None:
                return dft

            mdate = self.core.getFileModificationDate(configPath, asString=False)
            self.cachedConfigs[configPath] = {
                "modtime": mdate,
                "data": configData,
            }

            # logger.debug("adding cache: %s ---- %s" % (configPath, configData))

        if param and not cat:
            cat = param
            param = None

        if not cat:
            return configData
        elif not param:
            if cat in configData:
                return configData[cat]

        if cat in configData and configData[cat] and param in configData[cat]:
            return configData[cat][param]

        if dft is not None:
            self.setConfig(
                cat=cat, param=param, val=dft, configPath=configPath, config=config
            )
        return dft

    @err_catcher(name=__name__)
    def readConfig(self, configPath):
        ext = os.path.splitext(configPath)[1]
        if ext == ".yml":
            configData = self.readYaml(configPath)
        else:
            configData = self.readJson(configPath)

        return configData

    @err_catcher(name=__name__)
    def writeConfig(self, path, data):
        if self.core.prism1Compatibility:
            if (
                getattr(self.core, "projectPath", "") and os.path.normpath(path).startswith(os.path.normpath(self.core.projectPath))
                or self.core.useLocalFiles and os.path.normpath(path).startswith(os.path.normpath(self.core.localProjectPath))
            ):
                path = os.path.splitext(path)[0] + ".yml"

        ext = os.path.splitext(path)[1]
        if ext == ".json":
            configData = self.writeJson(data=data, path=path)
        elif ext == ".yml":
            configData = self.writeYaml(path=path, data=data)

        return configData

    @err_catcher(name=__name__)
    def setConfig(
        self,
        cat=None,
        param=None,
        val=None,
        data=None,
        configPath=None,
        delete=False,
        config=None,
        location=None,
        updateNestedData=True,
    ):
        if not configPath and config:
            configPath = self.getConfigPath(config, location=location)
        elif configPath is None:
            configPath = self.core.userini

        if not configPath:
            return

        isUserConfig = configPath == self.core.userini

        configData = self.readConfig(configPath)
        if configData is None:
            configData = OrderedDict([])

        if isUserConfig and not data and not configData:
            self.createUserPrefs()
            configData = self.readConfig(configPath)
            if configData is None:
                return

        if data is not None:
            if updateNestedData and isinstance(data, collections.Mapping):
                if isinstance(updateNestedData, collections.Mapping):
                    exclude = updateNestedData.get("exclude", [])
                else:
                    exclude = []

                self.updateNestedDicts(configData, data, exclude=exclude)
            else:
                configData = data
        else:
            if param and not cat:
                cat = param
                param = None

            if param is None and delete:
                if cat in configData:
                    del configData[cat]
            else:
                if cat and cat not in configData and param:
                    configData[cat] = OrderedDict([])

                if delete:
                    if cat:
                        if param in configData[cat]:
                            if isinstance(configData[cat], list):
                                configData[cat].remove(param)
                            else:
                                del configData[cat][param]
                else:
                    if param:
                        configData[cat][param] = val
                    elif cat:
                        configData[cat] = val
                    else:
                        configData = val

        if not os.path.exists(os.path.dirname(configPath)):
            os.makedirs(os.path.dirname(configPath))

        lf = Lockfile.Lockfile(self.core, configPath)
        try:
            with lf:
                self.writeConfig(path=configPath, data=configData)
        except Lockfile.LockfileException:
            pass
        else:
            mdate = self.core.getFileModificationDate(configPath, asString=False)
            self.cachedConfigs[os.path.normpath(configPath)] = {
                "modtime": mdate,
                "data": configData,
            }

    @err_catcher(name=__name__)
    def updateNestedDicts(self, d, u, exclude=None):
        exclude = exclude or []
        for k, v in u.items():
            if k not in exclude and isinstance(v, collections.Mapping) and isinstance(
                d.get(k, None), collections.Mapping
            ):
                d[k] = self.updateNestedDicts(d.get(k, OrderedDict([])), v, exclude=exclude)
            else:
                d[k] = v

        return d

    @err_catcher(name=__name__)
    def readYaml(self, path=None, data=None, stream=None, retry=True):
        logger.debug("read from config: %s" % path)

        try:
            from ruamel.yaml import YAML
        except:
            self.core.missingModule("ruamel.yaml")
            return

        yaml = YAML()
        yamlData = OrderedDict([])
        if path:
            if not os.path.exists(path):
                return yamlData

            lf = Lockfile.Lockfile(self.core, path)
            try:
                lf.waitUntilReady()
            except Lockfile.LockfileException:
                msg = (
                    "The following file is locked. It might be used by another process:\n\n%s\n\nReading from this file in a locked state can result in data loss."
                    % path
                )
                result = self.core.popupQuestion(
                    msg,
                    buttons=["Retry", "Continue", "Cancel"],
                    default="Cancel",
                    icon=QMessageBox.Warning,
                )
                if result == "Retry":
                    return self.readYaml(path=path, data=data, stream=stream)
                elif result == "Continue":
                    try:
                        lf.forceRelease()
                    except:
                        msg = (
                            "Prism can't unlock the file. Make sure no other processes are using this file. You can manually unlock it by deleting the lockfile:\n\n%s\n\nCanceling to read from the file."
                            % lf.lockPath
                        )
                        self.core.popup(msg)
                        return

                elif result == "Cancel":
                    return

            with open(path, "r") as config:
                try:
                    yamlData = yaml.load(config)
                except Exception as e:
                    if retry:
                        time.sleep(0.5)
                        return self.readYaml(
                            path=path, data=data, stream=stream, retry=False
                        )
                    else:
                        if os.path.exists(path):
                            msg = (
                                "Cannot read the content of this file:\n\n%s\n\nThe file exists, but the content is not in a valid yaml format."
                                % path
                            )
                        else:
                            msg = (
                                "Cannot read the content of this file because the file can't be accessed:\n\n%s"
                                % path
                            )

                        result = self.core.popupQuestion(
                            msg,
                            icon=QMessageBox.Warning,
                            buttons=["Retry", "Reset File", "Cancel"],
                            default="Cancel",
                        )
                        if result == "Retry":
                            return self.readYaml(
                                path=path, data=data, stream=stream, retry=False
                            )
                        elif result == "Reset File":
                            if path == self.core.userini:
                                self.createUserPrefs()
                            else:
                                open(path, "w").close()

                            yamlData = self.readYaml(path)
                        elif result == "Cancel":
                            return
                        else:
                            print(result)

            if lf.isLocked():
                yamlData = self.readYaml(path=path, data=data, stream=stream)

            if not yamlData:
                logger.warning("empty config: %s" % path)
        else:
            if not stream:
                if not data:
                    return
                stream = StringIO(data)

            try:
                yamlData = yaml.load(stream)
            except ValueError:
                return

        return yamlData

    @err_catcher(name=__name__)
    def writeYaml(self, path=None, data=None, stream=None, retry=True):
        logger.debug("write to yml config: %s" % path)
        if not data:
            return

        try:
            from ruamel.yaml import YAML
        except:
            self.core.missingModule("ruamel.yaml")
            return

        yaml = YAML()

        if path:
            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))

            try:
                with open(path, "w") as config:
                    yaml.dump(data, config)
            except Exception as e:
                if getattr(e, "errno", None) == 28:
                    self.core.popup("Not enough diskspace to save config:\n\n%s" % path)
                else:
                    if retry:
                        time.sleep(0.5)
                        self.writeYaml(path=path, data=data, stream=stream, retry=False)
                    else:
                        if getattr(e, "errno", None) == 13:
                            msg = "No write permissions for this file:\n%s" % path
                            result = self.core.popupQuestion(
                                msg,
                                icon=QMessageBox.Warning,
                                buttons=["Retry", "Skip"],
                                default="Skip",
                            )
                            if result == "Retry":
                                self.writeYaml(
                                    path=path, data=data, stream=stream, retry=False
                                )
        else:
            if not stream:
                stream = StringIO()

            yaml.dump(data, stream)
            return stream.getvalue()

    @err_catcher(name=__name__)
    def readJson(self, path=None, stream=None, data=None, ignoreErrors=False):
        logger.debug("read from config: %s" % path)
        import json

        jsonData = []
        if path:
            if not os.path.exists(path):
                return OrderedDict([])

            with open(path, "r") as f:
                try:
                    jsonData = json.load(f)
                except Exception as e:
                    if not ignoreErrors:
                        msg = "Failed to read json config:\n\n%s\n\n%s" % (path, str(e))
                        self.core.popup(msg)
                        return
        else:
            if not stream:
                if not data:
                    return
                stream = StringIO(data)

            try:
                jsonData = json.load(stream)
            except Exception as e:
                if not ignoreErrors:
                    msg = "Failed to read json config:\n\n%s\n\n%s" % (path, str(e))
                    self.core.popup(msg)
                    return

        return jsonData

    @err_catcher(name=__name__)
    def writeJson(self, data, path=None, stream=None, indent=4, quiet=False):
        logger.debug("write to json config: %s" % path)
        import json

        if path:
            if not os.path.exists(os.path.dirname(path)):
                try:
                    os.makedirs(os.path.dirname(path))
                except:
                    if quiet:
                        return
                    else:
                        raise

            try:
                with open(path, "w") as config:
                    json.dump(data, config, indent=indent)
            except Exception as e:
                if getattr(e, "errno", None) == 13:
                    msg = "Failed to write to config because of missing permissions:\n\n%s\n\n%s" % (path, e)
                    self.core.popup(msg)
                else:
                    raise

        else:
            if not stream:
                stream = StringIO()

            json.dump(data, stream, indent=indent)
            return stream.getvalue()

    @err_catcher(name=__name__)
    def findDeprecatedConfig(self, path):
        depConfig = os.path.splitext(path)[0] + ".ini"
        if os.path.exists(depConfig):
            newConfig = self.convertDeprecatedConfig(depConfig) or ""
            if os.path.exists(newConfig):
                return newConfig

    @err_catcher(name=__name__)
    def convertDeprecatedConfig(self, path):
        if not os.path.exists(path):
            logger.debug("Skipped config conversion. Config doesn't exist: %s " % path)
            return

        newConfig = os.path.splitext(path)[0] + self.preferredExtension
        if os.path.exists(newConfig):
            logger.debug("Skipped config conversion. Target exists: %s " % newConfig)
            return newConfig

        data = OrderedDict([])

        config = ConfigParser()
        try:
            if os.path.exists(path):
                config.read(path)
        except:
            pass

        for section in config.sections():
            if (
                section in ["recent_projects"]
                or section.startswith("recent_files")
                or os.path.basename(path) == "omits.ini"
            ):
                toList = True
                if os.path.basename(path) == "omits.ini":
                    data[section.lower()] = []
                else:
                    data[section] = []
            else:
                toList = False
                data[section] = OrderedDict([])

            items = config.items(section)
            for item in items:
                try:
                    bname = os.path.basename(path)
                    if (
                        bname == "omits.ini"
                        or bname == "pipeline.ini"
                        and item[0] == "project_name"
                    ):
                        val = item[1]
                    else:
                        val = eval(item[1])
                except:
                    val = item[1]

                if toList:
                    if os.path.basename(path) == "omits.ini":
                        data[section.lower()].append(val)
                    else:
                        data[section].append(val)
                else:
                    data[section][item[0]] = val

        self.writeConfig(path=newConfig, data=data)
        # os.remove(path)

        logger.debug("Converted config: %s to %s" % (path, newConfig))

        return newConfig

    @err_catcher(name=__name__)
    def readIni(self, path=None, data=None):
        logger.debug("read from config: %s" % path)
        config = ConfigParser()
        if path:
            try:
                if os.path.exists(path):
                    config.read(path)
            except:
                pass
        elif data:
            buf = StringIO(data)
            try:
                config.readfp(buf)
            except:
                pass

        return config

    @err_catcher(name=__name__)
    def generateConfigPath(self, name, location=None):
        location = location or "user"
        ext = self.preferredExtension
        if location == "user":
            base = self.core.getUserPrefDir()
        elif location == "project":
            base = os.path.join(self.core.projects.getPipelineFolder(), "Configs")
            ext = self.getProjectExtension()

        path = os.path.join(base, name + ext)
        return path
