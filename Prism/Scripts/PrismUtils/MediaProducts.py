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
    def getMediaProductLocations(self, basepath, entityType, entityName, step=None, category=None):
        basepath = basepath or self.getMediaProductBase(entityType, entityName, step=step, category=category)
        if not basepath:
            return

        basePaths = []
        renderPaths = self.core.paths.getRenderProductBasePaths()
        for renderPath in renderPaths:
            convertedBasepath = self.core.paths.convertGlobalRenderPath(basepath, renderPath)
            basePaths.append({"path": convertedBasepath, "type": renderPath})

        mediaPaths = []
        for basepathDict in basePaths:
            basepathType = basepathDict["type"]
            basepath = basepathDict["path"]
            path3d = os.path.join(basepath, "Rendering", "3dRender")
            path2d = os.path.join(basepath, "Rendering", "2dRender")
            pathExternal = os.path.join(basepath, "Rendering", "external")
            pathPlayblast = os.path.join(basepath, "Playblasts")

            suffix3d = ""
            if basepathType == "local":
                suffix3d = " (local)"

            mediaPaths += [
                {"type": "3d", "path": path3d, "suffix": suffix3d},
                {"type": "2d", "path": path2d, "suffix": " (2d)"},
                {"type": "external", "path": pathExternal, "suffix": " (external)"},
                {"type": "playblast", "path": pathPlayblast, "suffix": " (playblast)"},
            ]

        return mediaPaths

    @err_catcher(name=__name__)
    def getMediaProductNames(self, basepath=None, entityType=None, entityName=None, step=None, category=None):
        mediaTasks = {"3d": [], "2d": [], "playblast": [], "external": []}
        mediaPaths = self.getMediaProductLocations(basepath, entityType, entityName, step=step, category=category)

        if not mediaPaths:
            return mediaTasks

        for mediaPath in mediaPaths:
            for root, folders, fildes in os.walk(mediaPath["path"]):
                for folder in sorted(folders):
                    displayName = folder + mediaPath["suffix"]
                    taskNames = [x[0] for x in mediaTasks[mediaPath["type"]]]
                    if displayName in taskNames:
                        continue

                    if mediaPath["type"] == "3d" and folder in taskNames:
                        continue

                    taskPath = os.path.join(root, folder)
                    taskData = [displayName, mediaPath["type"], taskPath]
                    mediaTasks[mediaPath["type"]].append(taskData)
                break

        return mediaTasks

    @err_catcher(name=__name__)
    def getMediaVersionLocations(self, basepath=None, entityType=None, entityName=None, product="", step=None, category=None):
        basepath = basepath or self.getMediaProductBase(entityType, entityName, step=step, category=category)

        if basepath is None:
            return

        basePaths = []
        renderPaths = self.core.paths.getRenderProductBasePaths()
        for renderPath in renderPaths:
            convertedBasepath = self.core.paths.convertGlobalRenderPath(basepath, renderPath)
            basePaths.append({"path": convertedBasepath, "type": renderPath})

        versionPaths = []
        for basepathDict in basePaths:
            basepathType = basepathDict["type"]
            basepath = basepathDict["path"]
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

            suffix = ""
            if basepathType == "local":
                suffix = " (local)"

            data = {"type": basepathType, "path": taskPath, "suffix": suffix}
            versionPaths.append(data)

        return versionPaths

    @err_catcher(name=__name__)
    def getMediaVersions(self, basepath=None, entityType=None, entityName=None, product="", step=None, category=None):
        versions = []
        basepaths = self.getMediaVersionLocations(basepath, entityType, entityName, product, step, category)

        if not basepaths:
            return versions

        for basepathData in basepaths:
            for root, folders, files in os.walk(basepathData["path"]):
                for folder in folders:
                    versionPath = os.path.join(root, folder)
                    versionData = {"label": folder + basepathData["suffix"], "path": versionPath, "location": basepathData["type"]}
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
            foldercont = self.getRenderLayersFromPath(rPath)

        return foldercont

    @err_catcher(name=__name__)
    def getRenderLayersFromPath(self, path):
        for i in os.walk(path):
            foldercont = i[1]
            break

        return foldercont

    @err_catcher(name=__name__)
    def getMediaProductPath(self, basepath, product, version=None, layer=None, location=None):
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
            if location:
                basePath = self.core.paths.getRenderProductBasePaths()[location]
                prjPath = os.path.normpath(self.core.projectPath)
                basePath = os.path.normpath(basePath)
                path = os.path.normpath(path).replace(prjPath, basePath)
            else:
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
            entityPath = self.core.getEntityPath(asset=entityName)
        elif entity == "shot":
            entityPath = self.core.getEntityPath(shot=entityName)

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
    def generateMediaProductPath(self, entity, entityName, task, extension, framePadding=".", comment=None, version=None, location="global"):
        hVersion = ""
        if version is not None:
            hVersion, pComment = version.split(self.core.filenameSeparator)

        outputPath = self.getMediaProductPathFromEntity(entity, entityName, task)

        if hVersion == "":
            hVersion = self.core.getHighestTaskVersion(outputPath)
            pComment = comment or ""

        filename = self.generateMediaProductFilename(entity, entityName, task, hVersion, framePadding, extension)

        versionFoldername = (
            hVersion
            + self.core.filenameSeparator
            + pComment
        )

        outputName = os.path.join(outputPath, versionFoldername, "beauty", filename)
        outputName = getattr(self.core.appPlugin, "sm_render_fixOutputPath", lambda x, y, singleFrame: y)(self, outputName, singleFrame=not framePadding)

        basePath = self.core.paths.getRenderProductBasePaths()[location]
        prjPath = os.path.normpath(self.core.projectPath)
        basePath = os.path.normpath(basePath)
        outputName = os.path.normpath(outputName).replace(prjPath, basePath)

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
    def getPlayblastPathFromEntity(self, entity, entityName, task):
        if entity == "asset":
            entityPath = self.core.getEntityPath(asset=entityName)
        elif entity == "shot":
            entityPath = self.core.getEntityPath(shot=entityName)

        productPath = os.path.join(
            entityPath,
            "Playblasts",
            task,
        )

        return productPath

    @err_catcher(name=__name__)
    def generatePlayblastPath(self, entity, entityName, task, extension, framePadding=".", comment=None, version=None, location="global"):
        hVersion = ""
        if version is not None:
            hVersion, pComment = version.split(self.core.filenameSeparator)

        outputPath = self.getPlayblastPathFromEntity(entity, entityName, task)

        if hVersion == "":
            hVersion = self.core.getHighestTaskVersion(outputPath)
            pComment = comment or ""

        filename = self.generatePlayblastFilename(entity, entityName, task, hVersion, framePadding, extension)

        versionFoldername = (
            hVersion
            + self.core.filenameSeparator
            + pComment
        )

        outputName = os.path.join(outputPath, versionFoldername, filename)
        return outputName

    @err_catcher(name=__name__)
    def generatePlayblastFilename(self, entity, entityName, task, version, framePadding, extension):
        if entity == "asset":
            outputName = (
                os.path.basename(entityName)
                + self.core.filenameSeparator
                + task
                + self.core.filenameSeparator
                + version
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

    @err_catcher(name=__name__)
    def getLocationFromPath(self, path):
        locDict = self.core.paths.getRenderProductBasePaths()
        nPath = os.path.normpath(path)
        for location in locDict:
            if nPath.startswith(locDict[location]):
                return location
