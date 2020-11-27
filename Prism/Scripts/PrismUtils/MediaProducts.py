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

        if not basepath:
            return mediaTasks

        path3d = os.path.join(basepath, "Rendering", "3dRender")
        path2d = os.path.join(basepath, "Rendering", "2dRender")
        pathExternal = os.path.join(basepath, "Rendering", "external")
        pathPlayblast = os.path.join(basepath, "Playblasts")

        mediaPaths = [
            {"type": "3d", "path": path3d, "suffix": ""},
            {"type": "2d", "path": path2d, "suffix": " (2d)"},
            {"type": "external", "path": pathExternal, "suffix": " (external)"},
            {"type": "playblast", "path": pathPlayblast, "suffix": " (playblast)"},
        ]

        for mediaPath in mediaPaths:
            for root, folders, fildes in os.walk(mediaPath["path"]):
                for folder in sorted(folders):
                    displayName = folder + mediaPath["suffix"]
                    taskPath = os.path.join(root, folder)
                    taskData = [displayName, mediaPath["type"], taskPath]
                    mediaTasks[mediaPath["type"]].append(taskData)
                break

            if self.core.useLocalFiles:
                localPath = self.core.convertPath(mediaPath["path"], "local")
                if mediaPath["type"] == "3d":
                    suffix = " (local)"
                else:
                    suffix = mediaPath["suffix"]

                for root, folders, fildes in os.walk(localPath):
                    for folder in sorted(folders):
                        tname = folder + suffix
                        taskNames = [x[0] for x in mediaTasks[mediaPath["type"]]]
                        if tname not in taskNames:
                            if mediaPath["type"] == "3d" and folder in taskNames:
                                continue

                            taskPath = os.path.join(root, folder)
                            taskData = [tname, mediaPath["type"], taskPath]
                            mediaTasks[mediaPath["type"]].append(taskData)
                    break

        return mediaTasks

    @err_catcher(name=__name__)
    def getMediaVersions(self, basepath=None, entityType=None, entityName=None, product="", step=None, category=None):
        versions = []
        basepath = basepath or self.getMediaProductBase(entityType, entityName, step=step, category=category)

        if basepath is None:
            return versions

        if product.endswith(" (playblast)"):
            productName = product.replace(" (playblast)", "")
            taskPath = os.path.join(basepath, "Playblasts", productName)
        elif product.endswith(" (2d)"):
            productName = product.replace(" (2d)", "")
            taskPath = os.path.join(basepath, "Rendering", "2dRender", productName)
        elif product.endswith(" (external)"):
            productName = product.replace(" (external)", "")
            taskPath = os.path.join(basepath, "Rendering", "external", productName)
        else:
            productName = product.replace(" (local)", "")
            taskPath = os.path.join(basepath, "Rendering", "3dRender", productName)

        for root, folders, files in os.walk(taskPath):
            for folder in folders:
                versionPath = os.path.join(root, folder)
                versionData = {"label": folder, "path": versionPath}
                versions.append(versionData)
            break

        if self.core.useLocalFiles:
            localTaskPath = self.core.convertPath(taskPath, "local")
            for root, folders, files in os.walk(localTaskPath):
                for folder in folders:
                    versionPath = os.path.join(root, folder)
                    versionData = {"label": folder + " (local)", "path": versionPath}
                    versions.append(versionData)
                break

        return versions

    @err_catcher(name=__name__)
    def getRenderLayerPath(self, basepath, product, version):
        if version.endswith(" (local)"):
            localBase = self.core.convertPath(basepath, "local")
            productName = product.replace(" (local)", "")
            versionName = version.replace(" (local)", "")
            rPath = os.path.join(
                localBase, "Rendering", "3dRender", productName, versionName
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
                base = self.core.convertPath(basepath, "local")
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
                base = self.core.convertPath(basepath, "local")
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

    @err_catcher(name=__name__)
    def getMediaPathType(self, path):
        if "Playblasts" in path:
            return "playblast"
        elif "2dRender" in path:
            return "2d"
        elif "3dRender" in path:
            return "3d"
        else:
            return "unknown"

    @err_catcher(name=__name__)
    def getMediaProductPathFromEntity(self, entity, entityName, task, productType="3d"):
        if entity == "asset":
            entityPath = os.path.join(self.core.assetPath, entityName)
        elif entity == "shot":
            entityPath = os.path.join(self.core.shotPath, entityName)

        if productType == "3d":
            typeFolder = "3dRender"
        if productType == "2d":
            typeFolder = "2dRender"

        productPath = os.path.join(
            entityPath,
            "Rendering",
            typeFolder,
            task,
        )

        return productPath

    @err_catcher(name=__name__)
    def generateMediaProductPath(self, entity, entityName, task, extension, framePadding=True, comment=None, version=None, location="global"):
        hVersion = ""
        if version is not None:
            hVersion, pComment = version.split(self.core.filenameSeparator)

        framePadding = "." if framePadding else ""
        outputPath = self.getMediaProductPathFromEntity(entity, entityName, task)

        if hVersion == "":
            hVersion = self.core.getHighestTaskVersion(outputPath)
            pComment = comment or ""

        filename = self.generateMediaProductFilename(entity, entityName, task, hVersion, framePadding, extension)

        versionFoldername = (
            hVersion
            + self.core.filenameSeparator
            + pComment
            + self.core.filenameSeparator
        )

        outputName = os.path.join(outputPath, versionFoldername, "beauty", filename)
        outputName = getattr(self.core.appPlugin, "sm_render_fixOutputPath", lambda x, y, z: y)(self, outputName, singleFrame=not framePadding)
        result = self.core.callback(name="sm_render_fixOutputPath", types=["custom"], args=[self, outputName])
        for res in result:
            if res:
                outputName = res

        return outputName

    @err_catcher(name=__name__)
    def generateMediaProductFilename(self, entity, entityName, task, version, framePadding, extension):
        if entity == "asset":
            outputName = (
                os.path.basename(entityName)
                + self.core.filenameSeparator
                + task
                + self.core.filenameSeparator
                + version
                + self.core.filenameSeparator
                + "beauty"
                + framePadding
                + extension
            )
        elif entity == "shot":
            outputName = (
                "shot"
                + self.core.filenameSeparator
                + entityName
                + self.core.filenameSeparator
                + task
                + self.core.filenameSeparator
                + version
                + self.core.filenameSeparator
                + "beauty"
                + framePadding
                + extension
            )

        return outputName

    @err_catcher(name=__name__)
    def getVersionFromFilepath(self, path):
        versionFoldername = os.path.basename(os.path.dirname(os.path.dirname(path)))
        fileData = versionFoldername.split(self.core.filenameSeparator)

        fileversion = None
        for data in fileData:
            try:
                num = int(data[1:])
            except:
                num = None

            if len(data) == (self.core.versionPadding+1) and data[0] == "v" and num:
                try:
                    fileversion = data
                    break
                except:
                    pass

        return fileversion
