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
from typing import Any, Optional, List, Dict, Union

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class Ingegration(object):
    """Manages DCC (Digital Content Creation) application integrations.
    
    This class handles the installation, removal, and management of Prism integrations
    with various DCC applications like Maya, Houdini, Nuke, Blender, etc. It maintains
    a registry of installed integration locations and provides methods to add or remove
    integration scripts from application startup paths.
    
    Note: Class name contains a typo 'Ingegration' instead of 'Integration' for
    backward compatibility.
    
    Attributes:
        core: The Prism core instance
        installLocPath: Path to the file storing integration installation locations
    """
    
    def __init__(self, core: Any) -> None:
        """Initialize the Integration manager.
        
        Args:
            core: The Prism core instance
        """
        self.core = core
        prefDir = self.core.getUserPrefDir()
        self.installLocPath = os.path.join(prefDir, "InstallLocations" + self.core.configs.preferredExtension)
        self.convertDeprecatedConfig()

    @err_catcher(name=__name__)
    def removeIntegrationData(
        self,
        content: Optional[str] = None,
        filepath: Optional[Union[str, List[str]]] = None,
        deleteEmpty: bool = True,
        searchStrings: Optional[List[List[str]]] = None
    ) -> Union[str, bool]:
        """Remove Prism integration code blocks from file(s).
        
        Public method that handles both single files and lists of files.
        Delegates to _removeIntegrationData for actual processing.
        
        Args:
            content: Optional file content string (if not reading from filepath)
            filepath: Single file path or list of file paths to process
            deleteEmpty: Whether to delete the file if it becomes empty after removal
            searchStrings: Custom marker pairs to search for. Defaults to
                          [['# >>>PrismStart', '# <<<PrismEnd'],
                           ['#>>>PrismStart', '#<<<PrismEnd']]
            
        Returns:
            The modified content string or boolean success status
        """
        if isinstance(filepath, list):
            for f in filepath:
                result = self._removeIntegrationData(content=content, filepath=f, deleteEmpty=deleteEmpty, searchStrings=searchStrings)
            return result
        else:
            return self._removeIntegrationData(content=content, filepath=filepath, deleteEmpty=deleteEmpty, searchStrings=searchStrings)

    @err_catcher(name=__name__)
    def _removeIntegrationData(
        self,
        content: Optional[str] = None,
        filepath: Optional[str] = None,
        deleteEmpty: bool = True,
        searchStrings: Optional[List[List[str]]] = None
    ) -> Union[str, bool]:
        """Remove Prism integration code blocks from a single file.
        
        Searches for and removes code blocks delimited by Prism markers from
        the file content. Can optionally delete the file if it becomes empty.
        
        Args:
            content: Optional file content string (if not reading from filepath)
            filepath: Path to the file to process
            deleteEmpty: Whether to delete the file if it becomes empty after removal
            searchStrings: Custom marker pairs to search for. Defaults to
                          [['# >>>PrismStart', '# <<<PrismEnd'],
                           ['#>>>PrismStart', '#<<<PrismEnd']]
            
        Returns:
            The modified content string if successful, False if file reading failed
        """
        if content is None:
            if not os.path.exists(filepath):
                return True

            try:
                with open(filepath, "r") as f:
                    content = f.read()
            except Exception as e:
                logger.warning(e)
                return False

        if not searchStrings:
            searchStrings = [
                ["# >>>PrismStart", "# <<<PrismEnd"],
                ["#>>>PrismStart", "#<<<PrismEnd"],
            ]

        while True:
            for sstr in searchStrings:
                if sstr[0] in content and sstr[1] in content:
                    content = (
                        content[:content.find(sstr[0])]
                        + content[content.find(sstr[1], content.find(sstr[0])) + len(sstr[1]):]
                    )
                    break
            else:
                break

        if filepath:
            while True:
                try:
                    with open(filepath, "w") as f:
                        f.write(content)
                    break
                except Exception as e:
                    result = self.core.popupQuestion(
                        "Failed to write file:\n\n%s" % e,
                        buttons=["Retry", "Skip"],
                        escapeButton="Skip",
                        default="Skip",
                        icon=QMessageBox.Warning,
                    )
                    if result == "Retry":
                        continue

                    break

            if deleteEmpty:
                otherChars = [x for x in content if x not in [" ", "\n"]]
                if not otherChars:
                    try:
                        os.remove(filepath)
                    except Exception as e:
                        logger.warning("Failed to delete empty file: %s - %s" % (filepath, e))

        return content

    @err_catcher(name=__name__)
    def getIntegrations(self) -> Dict[str, List[str]]:
        """Get all registered DCC application integrations.
        
        Reads the integration registry file and returns a dictionary mapping
        application names to lists of installation paths.
        
        Returns:
            Dictionary with app names as keys and lists of installation paths
            as values. Returns empty dict if registry doesn't exist.
        """
        integrations = self.core.configs.readJson(path=self.installLocPath, ignoreErrors=True) or {}
        if not integrations:
            ymlIntegrations = self.core.readYaml(path=self.installLocPath) or {}
            if ymlIntegrations:
                self.core.configs.writeJson(path=self.installLocPath, data=ymlIntegrations)
                integrations = ymlIntegrations

        return integrations

    @err_catcher(name=__name__)
    def convertDeprecatedConfig(self) -> None:
        """Convert legacy .ini integration config to JSON format.
        
        Reads the old .ini format integration configuration and converts it
        to JSON format, preserving all integration paths. Deletes the .ini
        file after successful conversion.
        """
        installConfigPath = os.path.splitext(self.installLocPath)[0] + ".ini"

        if not os.path.exists(installConfigPath):
            return

        installConfig = self.core.configs.readIni(path=installConfigPath)
        integrations = self.getIntegrations()
        for section in installConfig.sections():
            if section not in integrations:
                integrations[section] = []

            opt = installConfig.options(section)
            for k in opt:
                path = installConfig.get(section, k)
                if path not in integrations[section]:
                    integrations[section].append(path)

        self.core.setConfig(configPath=self.installLocPath, data=integrations)

        try:
            os.remove(installConfigPath)
        except:
            pass

    @err_catcher(name=__name__)
    def refreshAllIntegrations(self) -> None:
        """Refresh all registered integrations.
        
        Removes and re-adds all registered integrations to ensure they're
        up-to-date with the current Prism version. Useful after updates.
        """
        intr = self.getIntegrations()
        self.removeIntegrations(intr)
        self.addIntegrations(intr)

    @err_catcher(name=__name__)
    def addAllIntegrations(self) -> None:
        """Add integrations for all available DCC applications.
        
        Runs the Prism installer to add integrations for all detected DCC
        applications without creating desktop shortcuts. Does not show success
        popup."""
        installer = self.core.getInstaller()
        installer.installShortcuts = False 
        installer.install(successPopup=False)

    @err_catcher(name=__name__)
    def addIntegrations(
        self,
        integrations: Dict[str, List[str]],
        quiet: bool = True
    ) -> None:
        """Add multiple DCC integrations.
        
        Iterates through a dictionary of applications and their installation
        paths, adding integration for each one.
        
        Args:
            integrations: Dictionary mapping app names to lists of install paths
            quiet: If True, suppress success popups for each integration
        """
        for app in integrations:
            for path in integrations[app]:
                self.addIntegration(app, path, quiet=quiet)

    @err_catcher(name=__name__)
    def addIntegration(
        self,
        app: str,
        path: Optional[str] = None,
        quiet: bool = False
    ) -> Optional[str]:
        """Add Prism integration to a DCC application.
        
        Installs Prism integration scripts into the specified DCC application.
        If the application requires an installation path but none is provided,
        prompts the user to select one. Updates the integration registry on success.
        
        Args:
            app: Name of the DCC application (e.g., 'Maya', 'Houdini')
            path: Installation path for the integration. If None and required,
                 user will be prompted to select one
            quiet: If True, suppress success popup
            
        Returns:
            The installation path if successful, None if failed or canceled
        """
        plugin = self.core.getPlugin(app)
        if not plugin:
            return

        hasIntegrationPath = self.core.getPluginData(app, "hasIntegrationPath")
        if hasIntegrationPath is None:
            hasIntegrationPath = True

        if not path and hasIntegrationPath:
            path = self.requestIntegrationPath(app)
            if not path:
                return

        result = plugin.addIntegration(path)
        if result:
            if not hasIntegrationPath:
                path = result

            self.core.callback("postIntegrationAdded", args=(app, path))
            if path:
                path = self.core.fixPath(path)
                data = self.core.configs.readJson(path=self.installLocPath, ignoreErrors=True) or {}
                if not data:
                    ymlData = self.core.readYaml(path=self.installLocPath) or {}
                    if ymlData:
                        self.core.configs.writeJson(path=self.installLocPath, data=ymlData)
                        data = ymlData

                if app not in data:
                    data[app] = []

                if path not in data[app]:
                    data[app].append(path)
                    self.core.setConfig(configPath=self.installLocPath, data=data)

            if not quiet:
                self.core.popup("Prism integration was added successfully", title="Prism Ingegration", severity="info")

            return path

    @err_catcher(name=__name__)
    def requestIntegrationPath(self, app: str) -> str:
        """Prompt user to select an integration installation path.
        
        Opens a folder selection dialog for the user to choose where to
        install the Prism integration for a specific DCC application.
        
        Args:
            app: Name of the DCC application
            
        Returns:
            Selected folder path, or empty string if canceled or UI unavailable
        """
        path = ""
        if self.core.uiAvailable:
            path = QFileDialog.getExistingDirectory(
                self.core.messageParent,
                "Select %s folder" % app,
                self.core.getPluginData(app, "examplePath"),
            )

        return path

    @err_catcher(name=__name__)
    def removeAllIntegrations(self) -> Dict[str, bool]:
        """Remove all registered Prism integrations.
        
        Removes Prism integration from all DCC applications that have
        registered integration paths.
        
        Returns:
            Dictionary mapping 'app (path)' strings to boolean success status
        """
        intr = self.getIntegrations()
        return self.removeIntegrations(intr)

    @err_catcher(name=__name__)
    def removeIntegrations(
        self,
        integrations: Dict[str, List[str]],
        quiet: bool = True
    ) -> Dict[str, bool]:
        """Remove multiple DCC integrations.
        
        Iterates through a dictionary of applications and their installation
        paths, removing integration for each one.
        
        Args:
            integrations: Dictionary mapping app names to lists of install paths
            quiet: If True, suppress success popups for each removal
            
        Returns:
            Dictionary mapping 'app (path)' strings to boolean success status
        """
        result = {}
        for app in integrations:
            for path in integrations[app]:
                result["%s (%s)" % (app, path)] = self.removeIntegration(app, path, quiet=quiet)

        return result

    @err_catcher(name=__name__)
    def removeIntegration(
        self,
        app: str,
        path: str,
        quiet: bool = False
    ) -> bool:
        """Remove Prism integration from a DCC application.
        
        Uninstalls Prism integration scripts from the specified DCC application
        at the given path. Updates the integration registry on success.
        
        Args:
            app: Name of the DCC application (e.g., 'Maya', 'Houdini')
            path: Installation path where integration was installed
            quiet: If True, suppress success popup
            
        Returns:
            True if removal was successful, False otherwise
        """
        plugin = self.core.getPlugin(app)
        if not plugin:
            return

        result = plugin.removeIntegration(path)

        if result:
            path = self.core.fixPath(path)
            data = self.core.configs.readJson(path=self.installLocPath, ignoreErrors=True) or {}
            if not data:
                ymlData = self.core.readYaml(path=self.installLocPath) or {}
                if ymlData:
                    self.core.configs.writeJson(path=self.installLocPath, data=ymlData)
                    data = ymlData

            if app in data:
                if path in data[app]:
                    data[app].remove(path)
                    self.core.setConfig(configPath=self.installLocPath, data=data)

            if not quiet:
                self.core.popup("Prism integration was removed successfully", title="Prism Ingegration", severity="info")

        return result
