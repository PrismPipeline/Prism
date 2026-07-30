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
import errno
import textwrap
from typing import Any, Optional, List, Dict, Tuple, Union

from collections import OrderedDict

import collections.abc as collections
try:
    from configparser import ConfigParser
except:
    pass

from io import StringIO

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher
from PrismUtils import Lockfile


logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration files and settings for the Prism pipeline.
    
    This class provides centralized management for reading, writing, and caching
    configuration files in various formats (YAML, JSON, INI). It handles user
    preferences, project settings, and supports automatic format conversion and
    caching for performance optimization.
    
    Attributes:
        core: The Prism core instance
        cachedConfigs: Dictionary of cached configuration data with modification times
        preferredExtension: The preferred file extension for new config files
        configItems: Dictionary mapping config keys to file paths
    """
    
    def __init__(self, core: Any) -> None:
        """Initialize the ConfigManager.
        
        Args:
            core: The Prism core instance
        """
        self.core = core
        self.cachedConfigs = {}
        self.preferredExtension = self.core.preferredExtension
        self.configItems = {}

        dprConfig = os.path.splitext(self.core.userini)[0] + ".ini"
        if not os.path.exists(self.core.userini) and os.path.exists(dprConfig):
            self.convertDeprecatedConfig(dprConfig)

    @err_catcher(name=__name__)
    def formatPathForPopup(self, path: Any, width: int = 150) -> str:
        """Format long paths for popup dialogs to avoid clipping."""
        path = str(path or "")
        if len(path) <= width:
            return path

        return "\n".join(
            textwrap.wrap(
                path,
                width=width,
                break_long_words=True,
                break_on_hyphens=False,
            )
        )

    @err_catcher(name=__name__)
    def addConfigItem(self, key: str, path: str) -> bool:
        """Add a custom configuration item path mapping.
        
        Register a custom config key with its associated file path for later retrieval.
        
        Args:
            key: The configuration key identifier
            path: The file path associated with this config key
            
        Returns:
            True if the item was added successfully, False if the key already exists
        """
        if key in self.configItems:
            return False

        self.configItems[key] = path
        return True

    @err_catcher(name=__name__)
    def getProjectExtension(self) -> str:
        """Get the file extension to use for project configuration files.
        
        Returns .yml for Prism 1 compatibility mode, otherwise returns the
        preferred extension.
        
        Returns:
            The file extension to use (e.g., '.yml' or '.json')
        """
        if self.core.prism1Compatibility:
            ext = ".yml"
        else:
            ext = self.preferredExtension

        return ext

    @err_catcher(name=__name__)
    def getConfigPath(self, config: str, location: Optional[str] = None) -> Optional[str]:
        """Get the file path for a specific configuration.
        
        Resolves configuration keys like 'user', 'project', 'omit', 'shotinfo',
        'assetinfo' to their full file paths. For custom config items, returns
        the registered path or generates a new path.
        
        Args:
            config: The configuration identifier (e.g., 'user', 'project', 'omit')
            location: Optional location context for path generation
            
        Returns:
            The full file path to the configuration file, or None if not found
        """
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
    def getProjectConfigName(self, projectPath: Optional[str] = None) -> str:
        """Get the name of the project configuration file.
        
        Checks the PRISM_PROJECT_CONFIG_NAME environment variable, or returns
        the default 'pipeline' with preferred extension.
        
        Args:
            projectPath: Optional project path (currently unused)
            
        Returns:
            The project configuration filename (e.g., 'pipeline.json')
        """
        return os.getenv(
            "PRISM_PROJECT_CONFIG_NAME", "pipeline" + self.preferredExtension
        )

    @err_catcher(name=__name__)
    def getProjectConfigPath(
        self,
        projectPath: Optional[str] = None,
        pipelineDir: Optional[str] = None,
        useEnv: bool = True
    ) -> str:
        """Get the full path to the project configuration file.
        
        Resolves the project config path based on project settings, environment
        variables, and Prism 1 compatibility mode. Supports custom pipeline
        directories and falls back to default locations.
        
        Args:
            projectPath: Optional project root path (defaults to current project)
            pipelineDir: Optional custom pipeline directory name
            useEnv: Whether to check PRISM_PROJECT_CONFIG_PATH environment variable
            
        Returns:
            The full path to the project configuration file
        """
        projectPath = projectPath or self.core.prismIni
        if (
            self.core.prism1Compatibility
            and getattr(self.core, "projectPath", "") and os.path.normpath(projectPath).startswith(os.path.normpath(self.core.projectPath))
            or self.core.useLocalFiles and os.path.normpath(projectPath).startswith(os.path.normpath(self.core.localProjectPath))
        ):

            configPath = os.path.join(projectPath, "00_Pipeline", "pipeline.yml")
        else:
            if getattr(self.core, "projectPath", "") and os.path.normpath(projectPath) == os.path.normpath(self.core.projectPath):
                configPath = self.core.prismIni
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
    def clearCache(self, path: Optional[str] = None) -> None:
        """Clear cached configuration data.
        
        Removes configuration data from the cache. If a path is provided, only
        that specific config is cleared; otherwise, the entire cache is cleared.
        Triggers a postClearConfigCache callback.
        
        Args:
            path: Optional path to specific config to clear (clears all if None)
        """
        if path:
            path = os.path.normpath(path)
            self.cachedConfigs.pop(path, None)
        else:
            self.cachedConfigs = {}

        self.core.callback("postClearConfigCache", args=[path])

    @err_catcher(name=__name__)
    def getCacheTime(self, path: str) -> Optional[Any]:
        """Get the modification time of a cached configuration.
        
        Retrieves the timestamp when a cached config was last loaded from disk.
        
        Args:
            path: Path to the configuration file
            
        Returns:
            The modification time of the cached config, or None if not cached
        """
        if path:
            path = os.path.normpath(path)

        if path not in self.cachedConfigs:
            return

        return self.cachedConfigs[path]["modtime"]

    @err_catcher(name=__name__)
    def createUserPrefs(self) -> None:
        """Create the default user preferences configuration file.
        
        Generates a new user preferences file with default settings for the Prism
        pipeline, including globals, DCC app settings, browser preferences, local
        files, and recent projects. Deletes any existing user preferences first.
        Sets appropriate file permissions on Linux/macOS.
        """
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

        self.setConfig(data=uconfig, configPath=self.core.userini, updateNestedData=False)

        if platform.system() in ["Linux", "Darwin"]:
            if os.path.exists(self.core.userini):
                os.chmod(self.core.userini, 0o777)

    @err_catcher(name=__name__)
    def getConfig(
        self,
        cat: Optional[str] = None,
        param: Optional[str] = None,
        configPath: Optional[str] = None,
        config: Optional[str] = None,
        dft: Optional[Any] = None,
        location: Optional[str] = None,
        allowCache: bool = True,
    ) -> Any:
        """Get a configuration value from a config file.
        
        Reads configuration data from YAML or JSON files with automatic caching,
        format conversion, and default value handling. Supports hierarchical
        access to nested configuration values.
        
        Args:
            cat: Category/section name in the config file
            param: Parameter name within the category. If param is None and cat
                  is provided, treats cat as the parameter name
            configPath: Full path to config file (overrides config parameter)
            config: Config identifier like 'user', 'project' to resolve path
            dft: Default value to return and save if config value doesn't exist
            location: Location context for path resolution
            allowCache: Whether to use cached config data for performance
            
        Returns:
            The requested configuration value, the default value if not found,
            or the entire config data if no cat/param specified
        """
        if not configPath and config:
            configPath = self.getConfigPath(config, location=location)
        elif configPath is None:
            configPath = self.core.userini

        if configPath:
            configPath = os.path.normpath(configPath)

        if configPath in self.cachedConfigs and allowCache:
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

            if allowCache:
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
    def readConfig(self, configPath: str) -> Optional[Any]:
        """Read configuration data from a file.
        
        Automatically determines the file format based on extension and reads
        the configuration using the appropriate parser (YAML or JSON).
        
        Args:
            configPath: Full path to the configuration file
            
        Returns:
            The parsed configuration data, or None if reading failed
        """
        ext = os.path.splitext(configPath)[1]
        if ext == ".yml":
            configData = self.readYaml(configPath)
        else:
            configData = self.readJson(configPath)

        return configData

    @err_catcher(name=__name__)
    def writeConfig(self, path: str, data: Any) -> Optional[Any]:
        """Write configuration data to a file.
        
        Automatically determines the output format based on file extension and
        writes the data using the appropriate formatter. Handles Prism 1
        compatibility mode by converting paths to .yml format when needed.
        
        Args:
            path: Full path to the configuration file
            data: Configuration data to write
            
        Returns:
            The written configuration data, or None if writing failed
        """
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
        cat: Optional[str] = None,
        param: Optional[str] = None,
        val: Optional[Any] = None,
        data: Optional[Any] = None,
        configPath: Optional[str] = None,
        delete: bool = False,
        config: Optional[str] = None,
        location: Optional[str] = None,
        updateNestedData: Union[bool, Dict[str, Any]] = True,
    ) -> None:
        """Set a configuration value in a config file.
        
        Writes a value to a configuration file with support for hierarchical
        updates, deletion, and automatic file locking. Can update nested
        dictionaries or replace entire config sections.
        
        Args:
            cat: Category/section name in the config file
            param: Parameter name within the category. If param is None and cat
                  is provided, treats cat as the parameter name
            val: Value to set for the parameter
            data: Complete config data to write (overrides cat/param/val)
            configPath: Full path to config file (overrides config parameter)
            delete: If True, delete the specified category or parameter
            config: Config identifier like 'user', 'project' to resolve path
            location: Location context for path resolution
            updateNestedData: If True/dict, merge nested dicts. If dict, can
                            specify 'exclude' list of keys not to merge
        """
        if not configPath and config:
            configPath = self.getConfigPath(config, location=location)
        elif configPath is None:
            configPath = self.core.userini

        if not configPath:
            return

        isUserConfig = configPath == self.core.userini

        if data is None or updateNestedData:
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

        dirname = os.path.dirname(configPath)
        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except Exception as e:
                if e.errno != errno.EEXIST:
                    self.core.popup("Failed to create folder:\n\n%s\n\nError:\n%s" % (dirname, e))
                    return

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
    def updateNestedDicts(
        self,
        d: Dict[str, Any],
        u: Dict[str, Any],
        exclude: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Recursively update nested dictionaries.
        
        Merges dictionary u into dictionary d, recursively updating nested
        dictionaries while preserving structure. Can exclude specific keys
        from merging.
        
        Args:
            d: Target dictionary to update (modified in place)
            u: Source dictionary with updates to apply
            exclude: Optional list of keys to skip during merge
            
        Returns:
            The updated target dictionary d
        """
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
    def readYaml(
        self,
        path: Optional[str] = None,
        data: Optional[str] = None,
        stream: Optional[Any] = None,
        retry: bool = True
    ) -> Optional[OrderedDict]:
        """Read YAML configuration data.
        
        Reads and parses YAML data from a file, string, or stream with file
        locking, error handling, and retry logic. Handles locked files with
        user prompts and can reset corrupted files.
        
        Args:
            path: Path to YAML file to read
            data: YAML data as string to parse
            stream: Stream object containing YAML data
            retry: Whether to retry once if reading fails
            
        Returns:
            OrderedDict containing parsed YAML data, or empty OrderedDict if
            file doesn't exist, or None if user cancels on error
        """
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
                displayPath = self.formatPathForPopup(path)
                msg = (
                    "The following file is locked. It might be used by another process:\n\n%s\n\nReading from this file in a locked state can result in data loss."
                    % displayPath
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
                        lockPath = self.formatPathForPopup(lf.lockPath)
                        msg = (
                            "Prism can't unlock the file. Make sure no other processes are using this file. You can manually unlock it by deleting the lockfile:\n\n%s\n\nCanceling to read from the file."
                            % lockPath
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
                        displayPath = self.formatPathForPopup(path)
                        if os.path.exists(path):
                            msg = (
                                "Cannot read the content of this file:\n\n%s\n\nThe file exists, but the content is not in a valid yaml format."
                                % displayPath
                            )
                        else:
                            msg = (
                                "Cannot read the content of this file because the file can't be accessed:\n\n%s"
                                % displayPath
                            )

                        logger.warning(msg)
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
    def writeYaml(
        self,
        path: Optional[str] = None,
        data: Optional[Any] = None,
        stream: Optional[Any] = None,
        retry: bool = True
    ) -> Optional[str]:
        """Write YAML configuration data.
        
        Writes configuration data to a YAML file or stream with automatic
        directory creation, error handling, and retry logic. Handles disk
        space and permission errors.
        
        Args:
            path: Path to YAML file to write
            data: Configuration data to serialize as YAML
            stream: Stream object to write YAML data to
            retry: Whether to retry once if writing fails
            
        Returns:
            The YAML string if writing to stream, otherwise None
        """
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
    def readJson(
        self,
        path: Optional[str] = None,
        stream: Optional[Any] = None,
        data: Optional[str] = None,
        ignoreErrors: bool = False,
        retry: bool = True
    ) -> Optional[Any]:
        """Read JSON configuration data.
        
        Reads and parses JSON data from a file, string, or stream with file
        locking, error handling, and retry logic. Handles locked files with
        user prompts and can reset corrupted files.
        
        Args:
            path: Path to JSON file to read
            stream: Stream object containing JSON data
            data: JSON data as string to parse
            ignoreErrors: If True, suppress error popups and return silently
            retry: Whether to retry once if reading fails
            
        Returns:
            Parsed JSON data (dict/list), empty OrderedDict if file doesn't
            exist, or None if reading failed or user canceled
        """
        logger.debug("read from config: %s" % path)
        import json

        jsonData = []
        if path:
            if not os.path.exists(path):
                return OrderedDict([])

            lf = Lockfile.Lockfile(self.core, path)
            try:
                lf.waitUntilReady()
            except Lockfile.LockfileException:
                displayPath = self.formatPathForPopup(path)
                msg = (
                    "The following file is locked. It might be used by another process:\n\n%s\n\nReading from this file in a locked state can result in data loss."
                    % displayPath
                )
                result = self.core.popupQuestion(
                    msg,
                    buttons=["Retry", "Continue", "Cancel"],
                    default="Cancel",
                    icon=QMessageBox.Warning,
                )
                if result == "Retry":
                    return self.readJson(path=path, stream=stream, data=data, ignoreErrors=ignoreErrors)
                elif result == "Continue":
                    try:
                        lf.forceRelease()
                    except:
                        lockPath = self.formatPathForPopup(lf.lockPath)
                        msg = (
                            "Prism can't unlock the file. Make sure no other processes are using this file. You can manually unlock it by deleting the lockfile:\n\n%s\n\nCanceling to read from the file."
                            % lockPath
                        )
                        self.core.popup(msg)
                        return

                elif result == "Cancel":
                    return

            try:
                f_handle = open(path, "r")
            except OSError as e:
                if retry:
                    time.sleep(0.5)
                    return self.readJson(
                        path=path, stream=stream, data=data, ignoreErrors=ignoreErrors, retry=False
                    )
                else:
                    if not ignoreErrors:
                        displayPath = self.formatPathForPopup(path)
                        msg = (
                            "Cannot open the following file:\n\n%s\n\nThe file may be unavailable due to a network or sync issue (e.g. Dropbox Smart Sync / cloud-only placeholder)."
                            % displayPath
                        )
                        msg += "\n\n%s" % str(e)
                        result = self.core.popupQuestion(
                            msg,
                            icon=QMessageBox.Warning,
                            buttons=["Retry", "Cancel"],
                            default="Cancel",
                        )
                        if result == "Retry":
                            return self.readJson(
                                path=path, stream=stream, data=data, ignoreErrors=ignoreErrors, retry=True
                            )
                    return

            with f_handle as f:
                try:
                    jsonData = json.load(f)
                except Exception as e:
                    if retry:
                        time.sleep(0.5)
                        return self.readJson(
                            path=path, stream=stream, data=data, ignoreErrors=ignoreErrors, retry=False
                        )
                    else:
                        if not ignoreErrors:
                            displayPath = self.formatPathForPopup(path)
                            if os.path.exists(path):
                                msg = (
                                    "Cannot read the content of this file:\n\n%s\n\nThe file exists, but the content is not in a valid json format."
                                    % displayPath
                                )
                            else:
                                msg = (
                                    "Cannot read the content of this file because the file can't be accessed:\n\n%s"
                                    % displayPath
                                )

                            msg += "\n\n%s" % str(e)
                            logger.warning(msg)
                            result = self.core.popupQuestion(
                                msg,
                                icon=QMessageBox.Warning,
                                buttons=["Retry", "Reset File", "Cancel"],
                                default="Cancel",
                            )
                            if result == "Retry":
                                return self.readJson(
                                    path=path, stream=stream, data=data, ignoreErrors=ignoreErrors, retry=False
                                )
                            elif result == "Reset File":
                                if path == self.core.userini:
                                    self.createUserPrefs()
                                else:
                                    with open(path, "w") as f:
                                        f.write("{}")

                                jsonData = self.readJson(path)
                            elif result == "Cancel":
                                return

            if lf.isLocked():
                jsonData = self.readJson(path=path, stream=stream, data=data, ignoreErrors=ignoreErrors)

            if not jsonData:
                logger.warning("empty config: %s" % path)

        else:
            if not stream:
                if not data:
                    return
                stream = StringIO(data)

            try:
                jsonData = json.load(stream)
            except Exception as e:
                if not ignoreErrors:
                    msg = "Failed to read json config from string:\n\n%s" % str(e)
                    self.core.popup(msg)
                    return

        return jsonData

    @err_catcher(name=__name__)
    def writeJson(
        self,
        data: Any,
        path: Optional[str] = None,
        stream: Optional[Any] = None,
        indent: int = 4,
        quiet: bool = False
    ) -> Optional[str]:
        """Write JSON configuration data.
        
        Writes configuration data to a JSON file or stream with automatic
        directory creation, formatting, and error handling. Can suppress
        error popups in quiet mode.
        
        Args:
            data: Configuration data to serialize as JSON
            path: Path to JSON file to write
            stream: Stream object to write JSON data to
            indent: Number of spaces for JSON indentation (default 4)
            quiet: If True, suppress error popups and return/raise silently
            
        Returns:
            The JSON string if writing to stream, otherwise None
        """
        logger.debug("write to json config: %s" % path)
        import json

        if path:
            if not os.path.exists(os.path.dirname(path)):
                try:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                except:
                    if quiet:
                        return
                    else:
                        raise

            while True:
                try:
                    with open(path, "w") as config:
                        json.dump(data, config, indent=indent, default=lambda o: "")

                    break
                except Exception as e:
                    logger.warning("Failed to write config: %s\n%s" % (path, str(e)))
                    if getattr(e, "errno", None) == 13:
                        msg = "Failed to write to config because of missing permissions:\n\n%s\n\n%s" % (path, e)
                    else:
                        msg = "Failed to write config:\n\n%s\n\n%s" % (path, e)

                    if os.getenv("PRISM_CONFIG_WRITE_WARNING", "1") == "1":
                        result = self.core.popupQuestion(
                            msg, buttons=["Retry", "Cancel"], default="Cancel", icon=QMessageBox.Warning, escapeButton="Cancel"
                        )
                    else:
                        result = "Cancel"

                    if result == "Retry":
                        continue
                    else:
                        break

        else:
            if not stream:
                stream = StringIO()

            json.dump(data, stream, indent=indent, default=lambda o: "")
            return stream.getvalue()

    @err_catcher(name=__name__)
    def findDeprecatedConfig(self, path: str) -> Optional[str]:
        """Find and convert a deprecated .ini config to the preferred format.
        
        Searches for a .ini version of the config file and converts it to
        the preferred format (YAML or JSON) if found.
        
        Args:
            path: Path to the config file (with preferred extension)
            
        Returns:
            Path to the converted config file if found and converted,
            otherwise None
        """
        depConfig = os.path.splitext(path)[0] + ".ini"
        if os.path.exists(depConfig):
            newConfig = self.convertDeprecatedConfig(depConfig) or ""
            if os.path.exists(newConfig):
                return newConfig

    @err_catcher(name=__name__)
    def convertDeprecatedConfig(self, path: str) -> Optional[str]:
        """Convert a deprecated .ini config file to the preferred format.
        
        Reads an old .ini format configuration file and converts it to the
        preferred format (YAML or JSON). Handles special cases for recent
        projects, recent files, and omits. Creates sections as lists or
        ordered dictionaries as appropriate.
        
        Args:
            path: Path to the .ini config file to convert
            
        Returns:
            Path to the newly created config file in preferred format,
            or None if conversion was skipped
        """
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
    def readIni(
        self,
        path: Optional[str] = None,
        data: Optional[str] = None
    ) -> ConfigParser:
        """Read an INI format configuration file.
        
        Reads legacy .ini format configuration files using ConfigParser.
        Used for backward compatibility with older Prism versions.
        
        Args:
            path: Path to the .ini file to read
            data: INI data as string to parse
            
        Returns:
            ConfigParser object containing the parsed INI data
        """
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
    def generateConfigPath(
        self,
        name: str,
        location: Optional[str] = None
    ) -> str:
        """Generate a full path for a new configuration file.
        
        Creates a configuration file path based on the name and location context.
        Uses appropriate base directories and file extensions based on whether
        it's a user or project config.
        
        Args:
            name: Base name for the config file (without extension)
            location: Either 'user' or 'project' to determine base directory
                     (defaults to 'user')
            
        Returns:
            Full path to the configuration file with appropriate extension
        """
        location = location or "user"
        ext = self.preferredExtension
        if location == "user":
            base = self.core.getUserPrefDir()
        elif location == "project":
            base = os.path.join(self.core.projects.getPipelineFolder(), "Configs")
            ext = self.getProjectExtension()

        path = os.path.join(base, name + ext)
        return path
