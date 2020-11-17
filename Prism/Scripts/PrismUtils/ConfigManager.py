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
import platform
import logging

from collections import OrderedDict

if sys.version[0] == "3":
    import collections.abc as collections
    from configparser import ConfigParser
    from io import StringIO
else:
    import collections
    from ConfigParser import ConfigParser
    from StringIO import StringIO

from PrismUtils.Decorators import err_catcher
from PrismUtils import Lockfile


logger = logging.getLogger(__name__)


class ConfigManager(object):
    def __init__(self, core):
        self.core = core
        self.cachedConfigs = {}
        self.preferredExtension = ".yml"

        dprConfig = os.path.splitext(self.core.userini)[0] + ".ini"
        if not os.path.exists(self.core.userini) and os.path.exists(dprConfig):
            self.convertDeprecatedConfig(dprConfig)

    @err_catcher(name=__name__)
    def getConfigPath(self, config, location=None):
        if config == "user":
            return self.core.userini
        elif config == "project":
            return self.core.prismIni
        elif config == "omit":
            if self.core.prismIni:
                return os.path.join(
                    os.path.dirname(self.core.prismIni), "Configs", "omits.yml"
                )
        elif config == "shotinfo":
            return os.path.join(
                os.path.dirname(self.core.prismIni), "Shotinfo", "shotInfo.yml"
            )
        elif config == "assetinfo":
            return os.path.join(
                os.path.dirname(self.core.prismIni), "Assetinfo", "assetInfo.yml"
            )
        else:
            return self.generateConfigPath(name=config, location=location)

    @err_catcher(name=__name__)
    def getProjectConfigPath(self, projectPath=None):
        projectPath = projectPath or self.core.prismIni
        configPath = os.path.join(projectPath, "00_Pipeline", "pipeline.yml")
        return configPath

    @err_catcher(name=__name__)
    def clearCache(self, path=None):
        if path:
            path = os.path.normpath(path)
            self.cachedConfigs.pop(path, None)
        else:
            self.cachedConfigs = {}

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
                self.core.popup("Failed to create preferences folder: \"%s\"" % cfgDir)
                return

        uconfig = OrderedDict([
            ("globals", OrderedDict([
                ("current project", ""),
                ("showonstartup", True),
                ("check_import_versions", True),
                ("checkframerange", True),
                ("username", ""),
                ("autosave", True),
                ("send_error_reports", True),
                ("rvpath", ""),
                ("djvpath", ""),
                ("prefer_djv", False),
                ("checkForUpdates", 7),
                ("highdpi", False),
                ("debug_mode", False),
                ("prefer_djv", False),
            ])),

            ("nuke", OrderedDict([
                ("usenukex", False),
            ])),

            ("blender", OrderedDict([
                ("autosaverender", False),
                ("autosaveperproject", False),
                ("autosavepath", ""),
            ])),

            ("browser", OrderedDict([
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
            ])),

            ("localfiles", OrderedDict([])),
            ("recent_projects", OrderedDict([])),
        ])

        self.setConfig(data=uconfig, configPath=self.core.userini)

        if platform.system() in ["Linux", "Darwin"]:
            if os.path.exists(self.core.userini):
                os.chmod(self.core.userini, 0o777)

    @err_catcher(name=__name__)
    def getConfig(self, cat=None, param=None, configPath=None, config=None, dft=None, location=None):
        if not configPath and config:
            configPath = self.getConfigPath(config, location=location)
        elif configPath is None:
            configPath = self.core.userini

        if not configPath:
            if dft is not None:
                self.setConfig(cat=cat, param=param, val=dft, configPath=configPath, config=config)
            return dft

        isUserConfig = configPath == self.core.userini
        configPath = os.path.normpath(configPath)

        if isUserConfig and not os.path.exists(configPath):
            self.createUserPrefs()

        if not os.path.exists(configPath) and not self.findDeprecatedConfig(configPath):
            if dft is not None:
                self.setConfig(cat=cat, param=param, val=dft, configPath=configPath, config=config)
            return dft

        if os.path.splitext(configPath)[1] == ".ini":
            configPath = self.convertDeprecatedConfig(configPath)

        if configPath in self.cachedConfigs:
            configData = self.cachedConfigs[configPath]
        else:
            configData = self.readYaml(configPath)
            if not configData and isUserConfig:
                warnStr = """The Prism preferences file seems to be corrupt.

It will be reset, which means all local Prism settings will fall back to their defaults.
You will need to set your last project again, but no project files (like scenefiles or renderings) are lost."""

                self.core.popup(warnStr)
                self.createUserPrefs()
                configData = self.readYaml(configPath)

            self.cachedConfigs[configPath] = configData

        if configData is None:
            configData = OrderedDict([])

        if param and not cat:
            cat = param
            param = None

        if not cat:
            return configData
        elif not param:
            if cat in configData:
                return configData[cat]

        if cat in configData and param in configData[cat]:
            return configData[cat][param]

        if dft is not None:
            self.setConfig(cat=cat, param=param, val=dft, configPath=configPath, config=config)
        return dft

    @err_catcher(name=__name__)
    def setConfig(
        self, cat=None, param=None, val=None, data=None, configPath=None, delete=False, config=None, location=None
    ):
        if not configPath and config:
            configPath = self.getConfigPath(config, location=location)
        elif configPath is None:
            configPath = self.core.userini

        if not configPath:
            return

        isUserConfig = configPath == self.core.userini

        configData = self.readYaml(configPath)
        if configData is None:
            configData = OrderedDict([])

        if isUserConfig and not data and not configData:
            self.createUserPrefs()
            configData = self.readYaml(configPath)
            if configData is None:
                return

        if data:
            self.updateNestedDicts(configData, data)
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
                self.writeYaml(path=configPath, data=configData)
        except Lockfile.LockfileException:
            pass
        else:
            self.cachedConfigs[os.path.normpath(configPath)] = configData

    @err_catcher(name=__name__)
    def updateNestedDicts(self, d, u):
        for k, v in u.items():
            if isinstance(v, collections.Mapping):
                d[k] = self.updateNestedDicts(d.get(k, OrderedDict([])), v)
            else:
                d[k] = v
        return d

    @err_catcher(name=__name__)
    def readYaml(self, path=None, data=None, stream=None):
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

            with open(path, "r") as config:
                try:
                    yamlData = yaml.load(config)
                except Exception:
                    self.core.popup("Failed to open file: %s" % path)
                    return yamlData
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
    def writeYaml(self, path=None, data=None, stream=None):
        logger.debug("write to config: %s" % path)
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
                    raise
        else:
            if not stream:
                stream = StringIO()

            yaml.dump(data, stream)
            return stream.getvalue()

    @err_catcher(name=__name__)
    def readJson(self, path=None, stream=None, data=None):
        logger.debug("read from config: %s" % path)
        import json

        jsonData = []
        if path:
            if not os.path.exists(path):
                return OrderedDict([])

            with open(path, "r") as f:
                jsonData = json.load(f)
        else:
            if not stream:
                if not data:
                    return
                stream = StringIO(data)

            try:
                jsonData = json.load(stream)
            except ValueError:
                return

        return jsonData

    @err_catcher(name=__name__)
    def writeJson(self, data, path=None, stream=None):
        logger.debug("write to config: %s" % path)
        import json

        if path:
            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))

            with open(path, "w") as config:
                json.dump(data, config, indent=4)
        else:
            if not stream:
                stream = StringIO()

            json.dump(data, stream, indent=4)
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

        newConfig = os.path.splitext(path)[0] + ".yml"
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
            if section in ["recent_projects"] or section.startswith("recent_files") or os.path.basename(path) == "omits.ini":
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
                    if bname == "omits.ini" or bname == "pipeline.ini" and item[0] == "project_name":
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

        self.writeYaml(path=newConfig, data=data)
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
    def getUserConfigDir(self):
        if platform.system() == "Windows":
            folder = os.path.join(os.environ["userprofile"], "Documents", "Prism")
        elif platform.system() == "Linux":
            folder = os.path.join(os.environ["HOME"], "Prism")
        elif platform.system() == "Darwin":
            folder = os.path.join(os.environ["HOME"], "Library", "Preferences", "Prism")

        return folder

    @err_catcher(name=__name__)
    def generateConfigPath(self, name, location=None):
        location = location or "user"
        if location == "user":
            base = self.getUserConfigDir()
        elif location == "project":
            base = os.path.join(os.path.dirname(self.core.prismIni), "Configs")

        path = os.path.join(base, name + ".yml")
        return path
