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
from typing import Any


class Prism_PureRef_Variables(object):
    """Variables and configuration for PureRef plugin.
    
    Defines plugin metadata, supported formats, and basic configuration
    for PureRef integration with Prism.
    
    Attributes:
        version (str): Plugin version
        pluginName (str): Display name of the plugin
        pluginType (str): Type of plugin (App)
        appShortName (str): Short name for the application
        appType (str): Application type (2d)
        hasQtParent (bool): Whether app has Qt parent window
        sceneFormats (List[str]): Supported scene file formats
        appSpecificFormats (List[str]): App-specific file formats
        appColor (List[int]): RGB color for UI elements
        renderPasses (List): Available render passes
        platforms (List[str]): Supported operating systems
        pluginDirectory (str): Path to plugin directory
        hasIntegration (bool): Whether app has DCC integration
        appIcon (str): Path to application icon
    """

    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize PureRef plugin variables.
        
        Args:
            core: PrismCore instance.
            plugin: Plugin instance.
        """
        self.version = "v2.1.4.1"
        self.pluginName = "PureRef"
        self.pluginType = "App"
        self.appShortName = "PureRef"
        self.appType = "2d"
        self.hasQtParent = False
        self.sceneFormats = [".pur"]
        self.appSpecificFormats = self.sceneFormats
        self.appColor = [200, 200, 200]
        self.renderPasses = []
        self.platforms = ["Windows", "Linux", "Darwin"]
        self.pluginDirectory = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        self.hasIntegration = False
        self.appIcon = os.path.join(self.pluginDirectory, "Resources", "PureRef.ico")
