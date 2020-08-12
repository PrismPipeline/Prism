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

from PrismUtils.Decorators import err_catcher


class Resolver(object):
    def __init__(self, core):
        super(Resolver, self).__init__()
        self.core = core

    @err_catcher(name=__name__)
    def resolveFields(self, uri, uriType="exportProduct"):
        fields = {}
        if uriType == "exportProduct":
            resolveData = uri.split("|")
            if resolveData[0] not in ["asset", "shot"]:
                resolveData.insert(0, "asset")

            fields = {"entity": resolveData[0]}
            if len(resolveData) >= 2:
                fields["entityName"] = resolveData[1]

            if len(resolveData) >= 3:
                fields["task"] = resolveData[2]

            if len(resolveData) >= 4:
                fields["version"] = resolveData[3]

        return fields

    @err_catcher(name=__name__)
    def resolvePath(self, uri, uriType="exportProduct", target="file"):
        fields = self.resolveFields(uri, uriType)

        path = ""
        for i in range(1):
            if not hasattr(self.core, "projectPath") or not self.core.projectPath:
                continue

            path = self.core.projectName

            if "entity" not in fields:
                continue

            if fields["entity"] == "asset":
                path = self.core.getAssetPath()
            elif fields["entity"] == "shot":
                path = self.core.getShotPath()

            if "entityName" not in fields:
                continue

            entityPath = os.path.join(path, fields["entityName"])
            if fields["entity"] == "asset":
                if not os.path.exists(entityPath) and not "/" in fields["entityName"]:
                    for i in self.core.entities.getAssetPaths():
                        if os.path.basename(i) == fields["entityName"]:
                            entityPath = i
                            break

            if not os.path.exists(entityPath):
                continue

            path = entityPath

            if "task" not in fields:
                if target not in ["task", "version", "file"]:
                    continue

                taskPath = os.path.join(path, "Export")
                if not os.path.exists(taskPath):
                    continue

                for i in os.walk(taskPath):
                    tasks = i[1]
                    break

                if not tasks:
                    continue

                fields["task"] = tasks[0]

            taskPath = os.path.join(path, "Export", fields["task"])
            if not os.path.exists(taskPath):
                continue

            path = taskPath

            if "version" not in fields:
                if target not in ["version", "file"]:
                    continue

                if not os.path.exists(path):
                    continue

                for i in os.walk(path):

                    versions = i[1]
                    break

                if not versions:
                    continue

                fields["version"] = versions[-1]

            versionPath = os.path.join(path, fields["version"])

            if not os.path.exists(versionPath):
                continue

            path = versionPath

            if target not in ["file"]:
                continue

            for fcont in os.walk(path):
                for folder in fcont[1]:
                    fpath = os.path.join(fcont[0], folder)

                    for f in os.listdir(fpath):
                        path = os.path.join(fpath, f)
                        continue

        return os.path.normpath(path)
