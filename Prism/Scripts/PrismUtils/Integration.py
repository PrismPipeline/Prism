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
import platform

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

from PrismUtils.Decorators import err_catcher


class Ingegration(object):
    def __init__(self, core):
        self.core = core

        if platform.system() == "Windows":
            self.installLocPath = os.path.join(
                os.environ["userprofile"],
                "Documents",
                "Prism",
                "InstallLocations.yml",
            )
        elif platform.system() == "Linux":
            self.installLocPath = os.path.join(
                os.environ["HOME"], "Prism", "InstallLocations.yml"
            )
        elif platform.system() == "Darwin":
            self.installLocPath = os.path.join(
                os.environ["HOME"],
                "Library",
                "Preferences",
                "Prism",
                "InstallLocations.yml",
            )

        self.convertDeprecatedConfig()

    @err_catcher(name=__name__)
    def removeIntegrationData(self, content=None, filepath=None, deleteEmpty=True):
        if isinstance(filepath, list):
            for f in filepath:
                result = self._removeIntegrationData(content=content, filepath=f, deleteEmpty=deleteEmpty)
            return result
        else:
            return self._removeIntegrationData(content=content, filepath=filepath, deleteEmpty=deleteEmpty)

    @err_catcher(name=__name__)
    def _removeIntegrationData(self, content=None, filepath=None, deleteEmpty=True):
        if not content:
            if not os.path.exists(filepath):
                return True

            with open(filepath, "r") as f:
                content = f.read()

        while True:
            if "# >>>PrismStart" in content and "# <<<PrismEnd" in content:
                content = (
                    content[:content.find("# >>>PrismStart")]
                    + content[content.find("# <<<PrismEnd", content.find("# >>>PrismStart")) + len("# <<<PrismEnd"):]
                )
            elif "#>>>PrismStart" in content and "#<<<PrismEnd" in content:
                content = (
                    content[:content.find("#>>>PrismStart")]
                    + content[content.find("#<<<PrismEnd", content.find("#>>>PrismStart")) + len("#<<<PrismEnd"):]
                )
            else:
                break

        if filepath:
            with open(filepath, "w") as f:
                f.write(content)

            if deleteEmpty:
                otherChars = [x for x in content if x not in [" ", "\n"]]
                if not otherChars:
                    os.remove(filepath)

        return content

    @err_catcher(name=__name__)
    def getIntegrations(self):
        integrations = self.core.readYaml(path=self.installLocPath) or {}
        return integrations

    @err_catcher(name=__name__)
    def convertDeprecatedConfig(self):
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

        self.core.writeYaml(path=self.installLocPath, data=integrations)

        try:
            os.remove(installConfigPath)
        except:
            pass

    @err_catcher(name=__name__)
    def refreshAllIntegrations(self):
        intr = self.getIntegrations()
        self.removeIntegrations(intr)
        self.addIntegrations(intr)

    @err_catcher(name=__name__)
    def addIntegrations(self, integrations, quiet=True):
        for app in integrations:
            for path in integrations[app]:
                self.addIntegration(app, path, quiet=quiet)

    @err_catcher(name=__name__)
    def addIntegration(self, app, path=None, quiet=False):
        if not path:
            path = self.requestIntegrationPath(app)

            if not path:
                return

        plugin = self.core.getPlugin(app)
        if not plugin:
            return

        result = plugin.addIntegration(path)

        if result:
            path = self.core.fixPath(path)
            data = self.core.readYaml(path=self.installLocPath)
            if app not in data:
                data[app] = []

            if path not in data[app]:
                data[app].append(path)
                self.core.writeYaml(path=self.installLocPath, data=data)

            if not quiet:
                self.core.popup("Prism integration was added successfully", title="Prism Ingegration", severity="info")

            return path

    @err_catcher(name=__name__)
    def requestIntegrationPath(self, app):
        path = ""
        if self.core.uiAvailable:
            path = QFileDialog.getExistingDirectory(
                self.core.messageParent,
                "Select %s folder" % app,
                os.path.dirname(self.core.getPluginData(app, "examplePath")),
            )

        return path

    @err_catcher(name=__name__)
    def removeAllIntegrations(self):
        intr = self.getIntegrations()
        return self.removeIntegrations(intr)

    @err_catcher(name=__name__)
    def removeIntegrations(self, integrations, quiet=True):
        result = {}
        for app in integrations:
            for path in integrations[app]:
                result["%s (%s)" % (app, path)] = self.removeIntegration(app, path, quiet=quiet)

        return result

    @err_catcher(name=__name__)
    def removeIntegration(self, app, path, quiet=False):
        plugin = self.core.getPlugin(app)
        if not plugin:
            return

        result = plugin.removeIntegration(path)

        if result:
            path = self.core.fixPath(path)
            data = self.core.readYaml(path=self.installLocPath)

            if app in data:
                if path in data[app]:
                    data[app].remove(path)
                    self.core.writeYaml(path=self.installLocPath, data=data)

            if not quiet:
                self.core.popup("Prism integration was removed successfully", title="Prism Ingegration", severity="info")

        return result
