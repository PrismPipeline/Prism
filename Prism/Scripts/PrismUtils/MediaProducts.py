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

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *
    psVersion = 1

from PrismUtils.Decorators import err_catcher


class MediaProducts(object):
    def __init__(self, core):
        self.core = core
        self.videoFormats = [".mp4", ".mov"]

    @err_catcher(name=__name__)
    def getMediaProductBase(self, entityType, entityName, step=None, category=None):
        if entityType == "asset":
            basepath = self.core.getEntityPath(asset=entityName)
        elif entityType == "shot":
            basepath = self.core.getEntityPath(shot=entityName)
        else:
            basepath = ""

        return basepath

    @err_catcher(name=__name__)
    def getMediaProductNames(self, basepath=None, entityType=None, entityName=None, step=None, category=None):
        mediaTasks = {"3d": [], "2d": [], "playblast": [], "external": []}
        basepath = basepath or self.getMediaProductBase(entityType, entityName, step=step, category=category)

        if basepath:
            for i in os.walk(
                os.path.join(basepath, "Rendering", "3dRender")
            ):
                for k in sorted(i[1]):
                    mediaTasks["3d"].append([k, "3d", os.path.join(i[0], k)])
                break

            for i in os.walk(
                os.path.join(basepath, "Rendering", "2dRender")
            ):
                for k in sorted(i[1]):
                    mediaTasks["2d"].append([k + " (2d)", "2d", os.path.join(i[0], k)])
                break

            for i in os.walk(
                os.path.join(basepath, "Rendering", "external")
            ):
                for k in sorted(i[1]):
                    mediaTasks["external"].append(
                        [k + " (external)", "external", os.path.join(i[0], k)]
                    )
                break

            for i in os.walk(os.path.join(basepath, "Playblasts")):
                for k in sorted(i[1]):
                    mediaTasks["playblast"].append(
                        [k + " (playblast)", "playblast", os.path.join(i[0], k)]
                    )
                break

            if self.core.useLocalFiles:
                for i in os.walk(
                    os.path.join(
                        basepath.replace(
                            self.core.projectPath, self.core.localProjectPath
                        ),
                        "Rendering",
                        "3dRender",
                    )
                ):
                    for k in sorted(i[1]):
                        tname = k + " (local)"
                        taskNames = [x[0] for x in mediaTasks["3d"]]
                        if tname not in taskNames and k not in taskNames:
                            mediaTasks["3d"].append(
                                [tname, "3d", os.path.join(i[0], k)]
                            )
                    break

                for i in os.walk(
                    os.path.join(
                        basepath.replace(
                            self.core.projectPath, self.core.localProjectPath
                        ),
                        "Rendering",
                        "2dRender",
                    )
                ):
                    for k in sorted(i[1]):
                        tname = k + " (2d)"
                        taskNames = [x[0] for x in mediaTasks["2d"]]
                        if tname not in mediaTasks["2d"]:
                            mediaTasks["2d"].append(
                                [tname, "2d", os.path.join(i[0], k)]
                            )
                    break

                for i in os.walk(
                    os.path.join(
                        basepath.replace(
                            self.core.projectPath, self.core.localProjectPath
                        ),
                        "Playblasts",
                    )
                ):
                    for k in sorted(i[1]):
                        tname = k + " (playblast)"
                        taskNames = [x[0] for x in mediaTasks["playblast"]]
                        if tname not in mediaTasks["playblast"]:
                            mediaTasks["playblast"].append(
                                [tname, "playblast", os.path.join(i[0], k)]
                            )
                    break

        return mediaTasks

    @err_catcher(name=__name__)
    def getMediaVersions(self, basepath=None, entityType=None, entityName=None, product="", step=None, category=None):
        foldercont = []
        basepath = basepath or self.getMediaProductBase(entityType, entityName, step=step, category=category)

        if basepath is None:
            return foldercont

        if product.endswith(" (playblast)"):
            taskPath = os.path.join(
                basepath, "Playblasts", product.replace(" (playblast)", "")
            )
        elif product.endswith(" (2d)"):
            taskPath = os.path.join(
                basepath,
                "Rendering",
                "2dRender",
                product.replace(" (2d)", ""),
            )
        elif product.endswith(" (external)"):
            taskPath = os.path.join(
                basepath,
                "Rendering",
                "external",
                product.replace(" (external)", ""),
            )
        else:
            taskPath = os.path.join(
                basepath,
                "Rendering",
                "3dRender",
                product.replace(" (local)", ""),
            )

        for i in os.walk(taskPath):
            foldercont = i[1]
            break

        if self.core.useLocalFiles:
            for i in os.walk(
                taskPath.replace(self.core.projectPath, self.core.localProjectPath)
            ):
                for k in i[1]:
                    foldercont.append(k + " (local)")
                break

        return foldercont

    @err_catcher(name=__name__)
    def getRenderLayerPath(self, basepath, product, version):
        if version.endswith(" (local)"):
            rPath = os.path.join(
                basepath.replace(
                    self.core.projectPath, self.core.localProjectPath
                ),
                "Rendering",
                "3dRender",
                product.replace(" (local)", ""),
                version.replace(" (local)", ""),
            )
        else:
            rPath = os.path.join(
                basepath, "Rendering", "3dRender", product, version
            )

        return rPath

    @err_catcher(name=__name__)
    def getRenderLayers(self, basepath, product, version):
        foldercont = []
        if basepath is None:
            return foldercont

        if (
            " (playblast)" not in product
            and " (2d)" not in product
            and " (external)" not in product
        ):
            rPath = self.getRenderLayerPath(basepath, product, version)

            for i in os.walk(rPath):
                foldercont = i[1]
                break

        return foldercont

    @err_catcher(name=__name__)
    def getMediaProductPath(self, basepath, product, version=None, layer=None):
        foldercont = ["", [], []]
        path = None
        version = version or ""

        if product.endswith(" (2d)"):
            if version and version.endswith(" (local)"):
                base = basepath.replace(
                    self.core.projectPath, self.core.localProjectPath
                )
            else:
                base = basepath

            path = os.path.join(
                    base,
                    "Rendering",
                    "2dRender",
                    product.replace(" (2d)", ""),
                    version.replace(" (local)", ""),
                )

        elif product.endswith(" (playblast)"):
            if version and version.endswith(" (local)"):
                base = basepath.replace(
                    self.core.projectPath, self.core.localProjectPath
                )
            else:
                base = basepath

            path = os.path.join(
                    base,
                    "Playblasts",
                    product.replace(" (playblast)", ""),
                    version.replace(" (local)", ""),
                )

        elif product.endswith(" (external)"):
            redirectFile = os.path.join(
                basepath,
                "Rendering",
                "external",
                product.replace(" (external)", ""),
            )

            if version:
                redirectFile = os.path.join(redirectFile, version, "REDIRECT.txt")

                if os.path.exists(redirectFile):
                    with open(redirectFile, "r") as rfile:
                        rpath = rfile.read()

                    if os.path.splitext(rpath)[1] == "":
                        path = rpath
                    else:
                        files = []
                        if os.path.exists(rpath):
                            files = [os.path.basename(rpath)]
                        foldercont = [os.path.dirname(rpath), [], files]
                else:
                    foldercont = [redirectFile, [], []]
        else:
            if layer:
                rPath = self.getRenderLayerPath(basepath, product, version)
                path = os.path.join(rPath, layer)
            else:
                path = os.path.join(
                        basepath,
                        "Rendering",
                        "3dRender",
                        product,
                        version,
                    )

        if path:
            if not os.path.exists(path) and self.core.useLocalFiles:
                path = self.core.convertPath(path, target="local")

            for foldercont in os.walk(path):
                break

        return foldercont

    @err_catcher(name=__name__)
    def getMediaVersionInfoPath(self, basepath, product, version):
        if version.endswith(" (local)"):
            basepath = self.core.convertPath(basepath, target="local")

        if product.endswith(" (playblast)"):
            path = os.path.join(
                basepath,
                "Playblasts",
                product.replace(" (playblast)", ""),
                version.replace(" (local)", ""),
                "versioninfo.yml",
            )
        elif product.endswith(" (2d)"):
            path = os.path.join(
                basepath,
                "Rendering",
                "2dRender",
                product.replace(" (2d)", ""),
                version.replace(" (local)", ""),
                "versioninfo.yml",
            )
        elif product.endswith(" (external)"):
            path = ""
        else:
            path = os.path.join(
                basepath,
                "Rendering",
                "3dRender",
                product.replace(" (local)", ""),
                version.replace(" (local)", ""),
                "versioninfo.yml",
            )

        self.core.configs.findDeprecatedConfig(path)
        return path
