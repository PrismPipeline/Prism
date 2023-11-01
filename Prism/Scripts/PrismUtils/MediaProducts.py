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
import logging
import platform
import shutil
import glob
import errno
import time

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class MediaProducts(object):
    def __init__(self, core):
        self.core = core

    @err_catcher(name=__name__)
    def createExternalMedia(self, filepath, entity, identifier, version, action="copy"):
        if entity["type"] == "asset":
            key = "renderFilesAssets"
        elif entity["type"] == "shot":
            key = "renderFilesShots"
        else:
            self.core.popup("Invalid entity is selected. Select an asset or a shot and try again.")
            return

        context = entity.copy()
        context["mediaType"] = "externalMedia"
        context["identifier"] = identifier
        context["version"] = version
        context["aov"] = "rgb"
        if "comment" not in context:
            context["comment"] = ""

        path = self.core.projects.getResolvedProjectStructurePath(key, context=context)
        folderpath = os.path.dirname(path)

        if not os.path.exists(folderpath):
            os.makedirs(folderpath)

        files = filepath.split(os.pathsep)
        for file in files:
            try:
                if action == "copy":
                    if os.path.isdir(file):
                        os.rmdir(folderpath)
                        shutil.copytree(file, folderpath)
                    else:
                        shutil.copy2(file, folderpath)
                elif action == "move":
                    shutil.move(file, folderpath)
                elif action == "link":
                    redirectFile = os.path.join(folderpath, "REDIRECT.txt")
                    with open(redirectFile, "w") as rfile:
                        rfile.write(file)

            except Exception as e:
                msg = "Failed to add external media:\n\n%s" % e
                self.core.popup(msg)
                continue

        return folderpath

    @err_catcher(name=__name__)
    def getExternalPathFromVersion(self, version):
        if version["type"] == "asset":
            key = "renderFilesAssets"
        elif version["type"] == "shot":
            key = "renderFilesShots"

        context = version.copy()
        context["mediaType"] = "externalMedia"
        context["aov"] = "rgb"

        filepath = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )
        folderpath = os.path.dirname(filepath)

        redirectFile = os.path.join(folderpath, "REDIRECT.txt")
        curLoc = ""
        if os.path.exists(redirectFile):
            with open(redirectFile, "r") as rdFile:
                curLoc = rdFile.read()

        return curLoc

    @err_catcher(name=__name__)
    def getIdentifiersByType(self, entity, locations=None):
        locationData = self.core.paths.getRenderProductBasePaths()
        searchLocations = []
        for locData in locationData:
            if not locations or locData in locations or "all" in locations:
                searchLocations.append(locData)

        mediaTypes = {"3d": [], "2d": [], "playblast": [], "external": []}
        for loc in searchLocations:
            for mtype in mediaTypes:
                context = entity.copy()
                context["project_path"] = locationData[loc]
                if mtype == "3d":
                    key = "3drenders"
                    context["mediaType"] = key
                elif mtype == "2d":
                    key = "2drenders"
                    context["mediaType"] = key
                elif mtype == "playblast":
                    key = "playblasts"
                    context["mediaType"] = key
                elif mtype == "external":
                    key = "externalMedia"
                    context["mediaType"] = key

                template = self.core.projects.getResolvedProjectStructurePath(
                    key, context=context
                )
                productData = self.core.projects.getMatchingPaths(template)
                validData = []
                for data in productData:
                    if "." in data["identifier"]:
                        if os.path.isfile(data["path"]):
                            continue

                    data["displayName"] = data["identifier"]
                    data.update(context)
                    if mtype != "3d":
                        data["displayName"] += " (%s)" % mtype

                    validData.append(data)

                mediaTypes[mtype] += validData

        return mediaTypes

    @err_catcher(name=__name__)
    def getIdentifierPathFromEntity(self, entity):
        key = "3drenders"
        context = entity.copy()
        template = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )
        path = os.path.dirname(template)
        return path

    @err_catcher(name=__name__)
    def getVersionPathFromIdentifier(self, entity):
        key = "renderVersions"
        context = entity.copy()
        template = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )
        path = os.path.dirname(template)
        return path

    @err_catcher(name=__name__)
    def getVersionsFromIdentifier(self, identifier, locations=None):
        locationData = self.core.paths.getRenderProductBasePaths()
        searchLocations = []
        for locData in locationData:
            if not locations or locData in locations or "all" in locations:
                searchLocations.append(locData)

        versions = []
        for loc in searchLocations:
            context = identifier.copy()
            if "version" in context:
                del context["version"]

            if "paths" in context:
                del context["paths"]

            context["project_path"] = locationData[loc]
            locVersions = self.getVersionsFromContext(context)
            for locVersion in locVersions:
                locVersion["paths"] = [locVersion.get("path")]
                for version in versions:
                    if version.get("version") == locVersion.get("version"):
                        version["paths"].append(locVersion.get("path"))
                        break
                else:
                    versions.append(locVersion)
                    continue

                break

        return versions

    @err_catcher(name=__name__)
    def getVersionStackContextFromPath(self, filepath, mediaType=None):
        context = self.core.paths.getRenderProductData(filepath)

        if mediaType:
            context["mediaType"] = mediaType

        if "asset" in context:
            context["asset"] = os.path.basename(context["asset_path"])

        if "version" in context:
            del context["version"]
        if "comment" in context:
            del context["comment"]
        if "user" in context:
            del context["user"]

        return context

    @err_catcher(name=__name__)
    def getVersionsFromSameVersionStack(self, path, mediaType=None):
        context = self.getVersionStackContextFromPath(path, mediaType=mediaType)
        if not context:
            return []

        versionData = self.getVersionsFromContext(context)
        return versionData

    @err_catcher(name=__name__)
    def getVersionsFromContext(self, context, keys=None):
        if context.get("mediaType") == "playblasts":
            key = "playblastVersions"
        else:
            key = "renderVersions"

        template = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )
        versionData = self.core.projects.getMatchingPaths(template)
        versions = []
        for data in versionData:
            d = context.copy()
            d.update(data)
            versions.append(d)
        return versions

    @err_catcher(name=__name__)
    def getAovPathFromVersion(self, version):
        key = "aovs"
        context = version.copy()
        template = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )
        path = os.path.dirname(template)
        return path

    @err_catcher(name=__name__)
    def getAOVsFromVersion(self, version):
        if version.get("mediaType") == "playblasts":
            return []

        key = "aovs"
        template = self.core.projects.getResolvedProjectStructurePath(
            key, context=version
        )
        aovData = self.core.projects.getMatchingPaths(template)
        aovs = []
        for data in aovData:
            if not os.path.isdir(data["path"]):
                continue

            if "aov" not in data:
                continue

            d = version.copy()
            d.update(data)
            aovs.append(d)
        return aovs

    @err_catcher(name=__name__)
    def getFilesFromContext(self, context):
        if context.get("mediaType") == "playblasts":
            if context["type"] == "asset":
                key = "playblastFilesAssets"
            elif context["type"] == "shot":
                key = "playblastFilesShots"
        else:
            if context.get("mediaType") == "3drenders" and "aov" not in context:
                return []

            if context.get("type", None) == "asset":
                key = "renderFilesAssets"
            elif context.get("type", None) == "shot":
                key = "renderFilesShots"
            else:
                return []

        template = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )
        folder = os.path.dirname(template)
        if not os.path.isdir(folder):
            logger.warning("folder doesn't exist: %s" % folder)
            return []

        files = []
        if context.get("source"):
            globPath = os.path.join(folder, context["source"].replace("#", "?"))
            files = glob.glob(globPath)

        else:
            for root, folders, files in os.walk(folder):
                break

        filepaths = []
        for file in files:
            filepaths.append(os.path.join(folder, file))

        return filepaths

    @err_catcher(name=__name__)
    def getFilePatternFromVersion(self, version):
        if version.get("mediaType") == "playblasts":
            if version["type"] == "asset":
                key = "playblastFilesAssets"
            elif version["type"] == "shot":
                key = "playblastFilesShots"
        else:
            if version["type"] == "asset":
                key = "renderFilesAssets"
            elif version["type"] == "shot":
                key = "renderFilesShots"

        context = version.copy()
        files = self.getFilesFromContext(version)
        if files:
            template = self.core.projects.getResolvedProjectStructurePath(key)
            data = self.core.projects.extractKeysFromPath(files[0], template, context=context)
            data["extension"] = os.path.splitext(files[0])[1]
            context.update(data)

        context["frame"] = "#" * self.core.framePadding
        pattern = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )
        return pattern

    @err_catcher(name=__name__)
    def getMediaVersionInfoPathFromFilepath(self, path, mediaType=None):
        if mediaType == "playblasts":
            return self.getPlayblastVersionInfoPathFromFilepath(path)
        elif mediaType == "2drenders":
            return self.get2dVersionInfoPathFromFilepath(path)

        infoPath = os.path.join(
            os.path.dirname(os.path.dirname(path)),
            "versioninfo" + self.core.configs.getProjectExtension(),
        )
        return infoPath

    @err_catcher(name=__name__)
    def getPlayblastVersionInfoPathFromFilepath(self, path):
        infoPath = os.path.join(
            os.path.dirname(path), "versioninfo" + self.core.configs.getProjectExtension()
        )
        return infoPath

    @err_catcher(name=__name__)
    def get2dVersionInfoPathFromFilepath(self, path):
        infoPath = os.path.join(
            os.path.dirname(path), "versioninfo" + self.core.configs.getProjectExtension()
        )
        return infoPath

    @err_catcher(name=__name__)
    def getVersionInfoPathFromContext(self, context):
        if context.get("mediaType") == "playblasts":
            if context["type"] == "asset":
                key = "playblastFilesAssets"
            elif context["type"] == "shot":
                key = "playblastFilesShots"
        else:
            if context["type"] == "asset":
                key = "renderFilesAssets"
            elif context["type"] == "shot":
                key = "renderFilesShots"

        filepath = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )

        if context.get("mediaType") in ["playblasts", "2drenders"]:
            infopath = self.getPlayblastVersionInfoPathFromFilepath(filepath)
        else:
            infopath = self.getMediaVersionInfoPathFromFilepath(filepath)

        return infopath

    @err_catcher(name=__name__)
    def setComment(self, versionPath, comment):
        infoPath = self.getMediaVersionInfoPathFromFilepath(versionPath)
        infoPath = os.path.join(versionPath, os.path.basename(infoPath))
        mediaInfo = {}
        if os.path.exists(infoPath):
            mediaInfo = self.core.getConfig(configPath=infoPath) or {}

        mediaInfo["comment"] = comment
        self.core.setConfig(data=mediaInfo, configPath=infoPath)

    @err_catcher(name=__name__)
    def getLatestVersionFromVersions(self, versions, includeMaster=True):
        if not versions:
            return

        if not self.getUseMaster():
            includeMaster = False

        latestVersion = None
        sortedVersions = sorted(
            versions,
            key=lambda x: x["version"] if x["version"] != "master" else "zzz",
            reverse=True,
        )
        if not includeMaster:
            sortedVersions = [v for v in sortedVersions if v["version"] != "master"]

        if not sortedVersions:
            return

        latestVersion = sortedVersions[0]
        return latestVersion

    @err_catcher(name=__name__)
    def getLatestVersionFromIdentifier(self, identifier, includeMaster=True):
        versions = self.getVersionsFromIdentifier(identifier)
        if not versions:
            return

        version = self.getLatestVersionFromVersions(
            versions, includeMaster=includeMaster
        )
        if not version:
            return

        return version

    @err_catcher(name=__name__)
    def getLatestVersionFromFilepath(self, filepath, includeMaster=True):
        data = self.getDataFromFilepath(filepath)
        if not data:
            return

        versions = self.getVersionsFromIdentifier(data)
        version = self.getLatestVersionFromVersions(
            versions, includeMaster=includeMaster
        )
        if not version:
            return

        return version

    @err_catcher(name=__name__)
    def generateMediaProductPath(
        self,
        entity,
        task,
        extension,
        framePadding="",
        comment=None,
        version=None,
        location="global",
        aov="beauty",
        returnDetails=False,
        mediaType=None,
        singleFrame=False,
        ignoreEmpty=False,
        ignoreFolder=False,
        user=None,
        additionalContext=None
    ):
        framePadding = framePadding or ""
        comment = comment or ""

        versionUser = user or self.core.user
        basePath = self.core.paths.getRenderProductBasePaths()[location]
        context = entity.copy()
        if "version" in context:
            del context["version"]

        context.update(
            {
                "project_path": basePath,
                "identifier": task,
                "comment": comment,
                "user": versionUser,
                "extension": extension,
                "aov": aov,
                "frame": framePadding,
            }
        )
        if additionalContext:
            context.update(additionalContext)

        if mediaType:
            context["mediaType"] = mediaType

        version = version or self.getHighestMediaVersion(
            context, ignoreEmpty=ignoreEmpty, ignoreFolder=ignoreFolder
        )
        context["version"] = version
        if entity.get("type") == "asset":
            key = "renderFilesAssets"
        elif entity.get("type") == "shot":
            key = "renderFilesShots"
        else:
            return

        outputPath = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )
        outputPath = getattr(
            self.core.appPlugin, "sm_render_fixOutputPath", lambda x, y, singleFrame: y
        )(self, outputPath, singleFrame=singleFrame)
        if returnDetails:
            context["path"] = outputPath
            return context
        else:
            return outputPath

    @err_catcher(name=__name__)
    def generatePlayblastPath(
        self,
        entity,
        task,
        extension,
        framePadding="",
        comment=None,
        version=None,
        location="global",
        returnDetails=False,
        user=None,
    ):
        versionUser = user or self.core.user
        basePath = self.core.paths.getRenderProductBasePaths()[location]
        context = entity.copy()
        context.update(
            {
                "project_path": basePath,
                "identifier": task,
                "extension": extension,
                "frame": framePadding,
                "mediaType": "playblasts",
            }
        )

        version = version or self.getHighestMediaVersion(context)
        context["version"] = version
        context["comment"] = comment or ""
        context["user"] = versionUser

        if entity["type"] == "asset":
            key = "playblastFilesAssets"
        elif entity["type"] == "shot":
            key = "playblastFilesShots"

        outputPath = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )
        if returnDetails:
            context["path"] = outputPath
            return context
        else:
            return outputPath

    @err_catcher(name=__name__)
    def getHighestMediaVersion(self, context, getExisting=False, ignoreEmpty=False, ignoreFolder=False):
        if not getExisting and not self.core.separateOutputVersionStack:
            fileName = self.core.getCurrentFileName()
            fnameData = self.core.getScenefileData(fileName)
            if fnameData.get("type") in ["asset", "shot"]:
                hVersion = fnameData["version"]
            else:
                hVersion = self.core.versionFormat % self.core.lowestVersion

            return hVersion

        if context.get("mediaType") == "playblasts":
            key = "playblastVersions"
        else:
            key = "renderVersions"

        locations = self.core.paths.getRenderProductBasePaths()
        validData = []
        for loc in locations:
            ctx = context.copy()
            ctx["project_path"] = locations[loc]
            template = self.core.projects.getResolvedProjectStructurePath(
                key, context=ctx
            )

            productData = self.core.projects.getMatchingPaths(template)
            for data in productData:
                if ignoreEmpty:
                    if ignoreFolder:
                        files = None
                        for root, folders, files in os.walk(data["path"]):
                            break
                        
                        if not files:
                            continue

                    else:
                        if not os.path.isdir(data["path"]):
                            continue

                    if ctx.get("mediaType") == "2drenders":
                        exFiles = os.listdir(data["path"])
                        if len(exFiles) > 1 or (
                            len(exFiles) == 1 and not exFiles[0].startswith("versioninfo")
                        ):
                            validData.append(data)
                    else:
                        for folder in os.listdir(data["path"]):
                            path = os.path.join(data["path"], folder)
                            if not os.path.isdir(path):
                                continue

                            exFiles = os.listdir(path)
                            if len(exFiles) > 1 or (
                                len(exFiles) == 1 and not exFiles[0].startswith("versioninfo")
                            ):
                                validData.append(data)
                else:
                    validData.append(data)

        highversion = None
        for data in validData:
            try:
                version = int(data.get("version")[1: (1 + self.core.versionPadding)])
            except:
                continue

            if highversion is None or version > highversion:
                highversion = version

        if getExisting and highversion is not None:
            return self.core.versionFormat % (highversion)
        else:
            if highversion is None:
                return self.core.versionFormat % (self.core.lowestVersion)
            else:
                return self.core.versionFormat % (highversion + 1)

    @err_catcher(name=__name__)
    def getVersionFromFilepath(self, path):
        data = self.getDataFromFilepath(path)

        if "version" not in data:
            return

        version = data["version"]
        return version

    @err_catcher(name=__name__)
    def getDataFromFilepath(self, path):
        path = os.path.normpath(path)
        entityType = self.core.paths.getEntityTypeFromPath(path)

        if entityType == "asset":
            key = "renderFilesAssets"
        elif entityType == "shot":
            key = "renderFilesShots"
        else:
            return {}

        template = self.core.projects.getResolvedProjectStructurePath(key)
        data = self.core.projects.extractKeysFromPath(path, template, context={"entityType": entityType})
        data["type"] = entityType
        if "asset_path" in data:
            data["asset"] = os.path.basename(data["asset_path"])

        return data

    @err_catcher(name=__name__)
    def getVersionFromPlayblastFilepath(self, path):
        entityType = self.core.paths.getEntityTypeFromPath(path)

        if entityType == "asset":
            key = "playblastFilesAssets"
        elif entityType == "shot":
            key = "playblastFilesShots"

        template = self.core.projects.getResolvedProjectStructurePath(key)
        data = self.core.projects.extractKeysFromPath(path, template, context={"entityType": entityType})

        if "version" not in data:
            return

        version = data["version"]
        return version

    @err_catcher(name=__name__)
    def getVersionFromVersionFolder(self, versionFolder, context=None):
        path = os.path.normpath(versionFolder)
        key = "renderVersions"

        location = self.getLocationFromPath(versionFolder)
        context["project_path"] = self.core.paths.getRenderProductBasePaths()[location]

        if "type" in context and "entityType" not in context:
            context["entityType"] = context["type"]

        if context and "version" in context:
            del context["version"]

        template = self.core.projects.getResolvedProjectStructurePath(key, context=context)
        data = self.core.projects.extractKeysFromPath(path, template, context=context)

        if not data:
            key = "playblastVersions"
            template = self.core.projects.getResolvedProjectStructurePath(key, context=context)
            data = self.core.projects.extractKeysFromPath(path, template, context=context)

        if not data and "mediaType" not in context:
            key = "renderVersions"
            context["mediaType"] = "2drenders"
            template = self.core.projects.getResolvedProjectStructurePath(key, context=context)
            data = self.core.projects.extractKeysFromPath(path, template, context=context)

        if "version" not in data:
            return

        version = data["version"]
        return version

    @err_catcher(name=__name__)
    def getRenderProductDataFromFilepath(self, filepath, mediaType="3drenders"):
        entityType = self.core.paths.getEntityTypeFromPath(filepath)
        if entityType == "asset":
            key = "renderFilesAssets"
        elif entityType == "shot":
            key = "renderFilesShots"
        else:
            return {}

        context = {"type": entityType}
        context["mediaType"] = mediaType
        location = self.getLocationFromPath(filepath)
        if location:
            context["project_path"] = self.core.paths.getRenderProductBasePaths()[location]

        template = self.core.projects.getResolvedProjectStructurePath(key, context=context)
        context = {"entityType": entityType, "project_path": context["project_path"]}
        data = self.core.projects.extractKeysFromPath(filepath, template, context=context)

        if not data:
            if entityType == "asset":
                key = "playblastFilesAssets"
            elif entityType == "shot":
                key = "playblastFilesShots"

            context = {"entityType": entityType, "project_path": context["project_path"]}
            template = self.core.projects.getResolvedProjectStructurePath(key, context=context)
            context = {"entityType": entityType, "project_path": context["project_path"]}
            data = self.core.projects.extractKeysFromPath(filepath, template, context=context)

        data["type"] = entityType
        if "asset_path" in data:
            data["asset"] = os.path.basename(data["asset_path"])

        return data

    @err_catcher(name=__name__)
    def getLocationFromPath(self, path):
        locDict = self.core.paths.getRenderProductBasePaths()
        nPath = os.path.normpath(path)
        for location in locDict:
            if nPath.startswith(locDict[location]):
                return location

    @err_catcher(name=__name__)
    def getVersionPathFromMediaFilePath(self, path, mediaType):
        entityType = self.core.paths.getEntityTypeFromPath(path)

        context = {"mediaType": mediaType}
        if mediaType == "playblasts":
            versionKey = "playblastVersions"
            if entityType == "asset":
                key = "playblastFilesAssets"
            elif entityType == "shot":
                key = "playblastFilesShots"
        else:
            versionKey = "renderVersions"
            if entityType == "asset":
                key = "renderFilesAssets"
            elif entityType == "shot":
                key = "renderFilesShots"

        location = self.getLocationFromPath(path)
        context["project_path"] = self.core.paths.getRenderProductBasePaths()[location]
        template = self.core.projects.getResolvedProjectStructurePath(key, context=context)
        data = self.core.projects.extractKeysFromPath(path, template, context={"entityType": entityType})
        data.update(context)

        versionPath = self.core.projects.getResolvedProjectStructurePath(
            versionKey, context=data
        )

        return versionPath

    @err_catcher(name=__name__)
    def updateMasterVersion(self, path=None, context=None, isFilepath=True, add=False, mediaType=None):
        if context:
            path = context["path"]
            files = self.core.getFilesFromFolder(path)
            if files:
                ext = os.path.splitext(files[0])[1]
            else:
                ext = ".exr"

            context["extension"] = ext
            isFilepath = False
        else:
            if mediaType == "playblasts":
                context = self.core.paths.getPlayblastProductData(path, isFilepath=isFilepath)
            elif mediaType == "2drenders":
                context = self.core.paths.getRenderProductData(path, isFilepath=isFilepath, mediaType=mediaType)
            else:
                context = self.core.paths.getRenderProductData(path, isFilepath=isFilepath)

        forcedLoc = os.getenv("PRISM_MEDIA_MASTER_LOC")
        if forcedLoc:
            location = forcedLoc
        else:
            location = self.getLocationFromPath(path)

        if "mediaType" not in context:
            context["mediaType"] = mediaType or self.getMediaTypeFromContext(context)

        if context.get("mediaType") == "playblasts":
            masterPath = self.generatePlayblastPath(
                entity=context,
                task=context["identifier"],
                extension=context["extension"],
                version="master",
                location=location,
                framePadding="",
            )
        else:
            masterPath = self.generateMediaProductPath(
                entity=context,
                task=context["identifier"],
                extension=context.get("extension"),
                version="master",
                location=location,
                framePadding=None,
                mediaType=context.get("mediaType")
            )

        logger.debug("updating master render version: %s from %s" % (masterPath, path))
        if not add:
            result = self.deleteMasterVersion(masterPath, isFilepath=True, mediaType=context.get("mediaType"))
            if not result:
                return

            masterVersions = []
        else:
            masterVersions = self.getVersionPathsFromMaster(masterPath, isFilepath=True)

        masterDrive = os.path.splitdrive(masterPath)[0]
        drive = os.path.splitdrive(path)[0]

        masterBase = self.getVersionPathFromMediaFilePath(masterPath, mediaType=context.get("mediaType"))
        if isFilepath:
            originBase = self.getVersionPathFromMediaFilePath(path, mediaType=context.get("mediaType"))
        else:
            originBase = path

        files = self.core.getFilesFromFolder(originBase, recursive=True)
        for file in files:
            frameStr = os.path.splitext(file)[0][-self.core.framePadding :]
            if sys.version[0] == "2":
                frameStr = unicode(frameStr)

            masterFilename = self.core.paths.replaceVersionInStr(
                os.path.basename(file), "master"
            )
            masterFile = file.replace(originBase, masterBase)
            masterFile = os.path.join(os.path.dirname(masterFile), masterFilename)

            if not os.path.exists(os.path.dirname(masterFile)):
                try:
                    os.makedirs(os.path.dirname(masterFile))
                except Exception as e:
                    if e.errno != errno.EEXIST:
                        raise

            useHL = os.getenv("PRISM_USE_HARDLINK_MASTER", None)
            if platform.system() == "Windows" and drive == masterDrive and useHL:
                self.core.createSymlink(masterFile, file)
            else:
                shutil.copy2(file, masterFile)

        masterVersions.append(originBase)
        ext = self.core.configs.getProjectExtension()
        masterInfoPath = os.path.join(masterBase, "versioninfo" + ext)
        self.core.setConfig(
            "versionpaths", val=masterVersions, configPath=masterInfoPath
        )
        self.core.media.invalidateOiioCache()
        return masterPath

    @err_catcher(name=__name__)
    def getMasterVersionNumber(self, masterPath):
        versionData = self.core.paths.getRenderProductData(masterPath, validateModTime=True)
        if "versionpaths" in versionData:
            context = versionData.copy()
            for path in versionData["versionpaths"]:
                vName = self.core.mediaProducts.getVersionFromVersionFolder(
                    path, context=context
                )
                if vName:
                    return vName

    @err_catcher(name=__name__)
    def getMasterVersionLabel(self, path):
        versionName = "master"
        versionData = self.core.paths.getRenderProductData(path, validateModTime=True)
        if "versionpaths" in versionData:
            versions = []
            context = versionData.copy()
            for path in versionData["versionpaths"]:
                vName = self.core.mediaProducts.getVersionFromVersionFolder(
                    path, context=context
                )
                if vName:
                    versions.append(vName)

            versionStr = ", ".join(versions)
            versionName = "master"
            if versionStr:
                versionName += " (%s)" % versionStr

        return versionName

    @err_catcher(name=__name__)
    def getMediaTypeFromContext(self, context):
        mtype = "3drenders"
        if "displayName" in context:
            ndata = context["displayName"].rsplit(" (", 1)
            if len(ndata) == 2 and ndata[1][-1] == ")":
                mtype = ndata[1][:-1]

                if mtype == "2d":
                    mtype = "2drenders"
                elif mtype == "playblast":
                    mtype = "playblasts"
                elif mtype == "external":
                    mtype = "externalMedia"

        return mtype

    @err_catcher(name=__name__)
    def getMediaTypeFromPath(self, path):
        base, ext = os.path.splitext(path)
        if ext:
            dirpath = os.path.basename(path)
        else:
            dirpath = path

        infoPath = os.path.join(dirpath, "versioninfo" + self.core.configs.getProjectExtension())
        if not os.path.exists(infoPath):
            infoPath = os.path.join(os.path.dirname(dirpath), "versioninfo" + self.core.configs.getProjectExtension())

        data = self.core.getConfig(configPath=infoPath)
        if data and "mediaType" in data:
            return data["mediaType"]

        entityType = self.core.paths.getEntityTypeFromPath(path)
        if entityType == "asset":
            key = "renderFilesAssets"
        elif entityType == "shot":
            key = "renderFilesShots"
        else:
            return

        mediaType = None
        context = {"type": entityType}
        context["mediaType"] = "3drenders"
        location = self.getLocationFromPath(path)
        if location:
            context["project_path"] = self.core.paths.getRenderProductBasePaths()[location]

        template = self.core.projects.getResolvedProjectStructurePath(key, context=context)
        context = {"entityType": entityType, "project_path": context["project_path"]}
        data = self.core.projects.extractKeysFromPath(path, template, context=context)
        if data:
            mediaType = "3drenders"
        else:
            if entityType == "asset":
                key = "playblastFilesAssets"
            elif entityType == "shot":
                key = "playblastFilesShots"

            context = {"entityType": entityType, "project_path": context["project_path"]}
            template = self.core.projects.getResolvedProjectStructurePath(key, context=context)
            context = {"entityType": entityType, "project_path": context["project_path"]}
            data = self.core.projects.extractKeysFromPath(path, template, context=context)
            if data:
                mediaType = "playblasts"
            else:
                key = "renderVersions"
                context["mediaType"] = "2drenders"
                template = self.core.projects.getResolvedProjectStructurePath(key, context=context)
                data = self.core.projects.extractKeysFromPath(path, template, context=context)
                if data:
                    mediaType = "2drenders"

        return mediaType

    @err_catcher(name=__name__)
    def deleteMasterVersion(self, path, isFilepath=False, mediaType=None, allowClear=True, allowRename=True):
        if isFilepath:
            vpath = self.getVersionPathFromMediaFilePath(path, mediaType=mediaType)
        else:
            vpath = path

        logger.debug("removing master render version: %s" % vpath)
        if os.path.exists(vpath):
            try:
                shutil.rmtree(vpath)
            except Exception as e:
                if self.core.pb and allowClear:
                    self.core.pb.mediaBrowser.lw_version.clearSelection()
                    return self.deleteMasterVersion(path, isFilepath=isFilepath, mediaType=mediaType, allowClear=False, allowRename=allowRename)

                if allowRename:
                    renamed = self.core.products.renameMaster(vpath)
                    if renamed:
                        return True

                logger.warning(e)
                msg = "Couldn't remove the existing master version:\n\n%s" % (str(e))
                result = self.core.popupQuestion(
                    msg,
                    buttons=["Retry", "Don't delete master version"],
                    icon=QMessageBox.Warning,
                )
                if result == "Retry":
                    return self.deleteMasterVersion(path, isFilepath=isFilepath, mediaType=mediaType, allowClear=allowClear, allowRename=allowRename)
                else:
                    return False

        return True

    @err_catcher(name=__name__)
    def addToMasterVersion(self, path=None, context=None, isFilepath=True, mediaType=None):
        self.updateMasterVersion(
            path=path, context=context, isFilepath=isFilepath, add=True, mediaType=mediaType
        )

    @err_catcher(name=__name__)
    def getVersionPathsFromMaster(self, path, isFilepath=True):
        infoPath = self.getMediaVersionInfoPathFromFilepath(path)
        paths = self.core.getConfig("versionpaths", configPath=infoPath) or []
        return paths

    @err_catcher(name=__name__)
    def getUseMaster(self):
        return self.core.getConfig(
            "globals", "useMasterRenderVersion", dft=False, config="project"
        )

    @err_catcher(name=__name__)
    def createIdentifier(self, entity, identifier, identifierType="3drenders"):
        context = entity.copy()
        context["identifier"] = identifier
        if "task" not in context:
            context["task"] = "none"

        if "user" not in context:
            context["user"] = self.core.user

        path = self.core.projects.getResolvedProjectStructurePath(identifierType, context)

        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except:
                self.core.popup("The directory %s could not be created" % path)
                return
            else:
                self.core.callback(
                    name="onIdentifierCreated",
                    args=[self, path, context],
                )

            logger.debug("identifier created %s" % path)
        else:
            logger.debug("identifier already exists: %s" % path)

        return path

    @err_catcher(name=__name__)
    def createVersion(self, entity, identifier, version, identifierType="3drenders"):
        context = entity.copy()
        context["identifier"] = identifier
        context["mediaType"] = identifierType
        context["version"] = version
        if "task" not in context:
            context["task"] = "none"

        if "user" not in context:
            context["user"] = self.core.user

        if context.get("mediaType") == "playblasts":
            key = "playblastVersions"
        else:
            key = "renderVersions"

        path = self.core.projects.getResolvedProjectStructurePath(key, context)
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except:
                self.core.popup("The directory %s could not be created" % path)
                return
            else:
                self.core.callback(
                    name="onVersionCreated",
                    args=[self, path, context],
                )

            logger.debug("version created %s" % path)
        else:
            logger.debug("version already exists: %s" % path)

        return path

    @err_catcher(name=__name__)
    def createAov(self, entity, identifier, version, aov, identifierType="3drenders"):
        context = entity.copy()
        context["identifier"] = identifier
        context["mediaType"] = identifierType
        context["version"] = version
        context["aov"] = aov
        if "task" not in context:
            context["task"] = "none"
        
        if "user" not in context:
            context["user"] = self.core.user

        path = self.core.projects.getResolvedProjectStructurePath("aovs", context)

        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except:
                self.core.popup("The directory %s could not be created" % path)
                return
            else:
                self.core.callback(
                    name="onAovCreated",
                    args=[self, path, context],
                )

            logger.debug("aov created %s" % path)
        else:
            logger.debug("aov already exists: %s" % path)

        return path

    @err_catcher(name=__name__)
    def ingestMedia(self, files, entity, identifier, version, aov, mediaType="3drenders"):
        if not files:
            return

        kwargs = {
            "entity": entity,
            "task": identifier,
            "version": version,
            "aov": aov,
            "user": self.core.user,
            "mediaType": mediaType
        }

        baseTxt = "Copying file - please wait..\n\n"
        updatedText = baseTxt + "%s/%s" % (0, len(files))
        self.copyMsg = self.core.waitPopup(self.core, updatedText, hidden=True)

        self.ingestedFiles = []
        self.ingestCanceled = False
        self.ingestThreads = []
        with self.copyMsg as copyMsg:
            for idx, file in enumerate(files):
                if self.ingestCanceled:
                    return

                kwargs["extension"] = os.path.splitext(file)[1]
                if len(files) > 1:
                    kwargs["framePadding"] = ("%%0%sd" % self.core.framePadding) % (idx + 1)

                if kwargs.get("mediaType") == "playblasts":
                    pbkwargs = kwargs.copy()
                    del pbkwargs["aov"]
                    del pbkwargs["mediaType"]
                    targetPath = self.generatePlayblastPath(**pbkwargs)
                else:
                    targetPath = self.generateMediaProductPath(**kwargs)

                if idx == 0:
                    if not os.path.exists(os.path.dirname(targetPath)):
                        try:
                            os.makedirs(os.path.dirname(targetPath))
                        except:
                            msg = "The directory could not be created"
                            self.core.popup(msg)
                            return {"result": msg}

                    elif os.listdir(os.path.dirname(targetPath)):
                        msg = "The targetfolder contains files already.\nContinuing may overwrite existing files."
                        result = self.core.popupQuestion(msg, buttons=["Continue", "Add new version", "Cancel"], icon=QMessageBox.Warning)
                        if result == "Cancel":
                            return {"result": "canceled"}
                        elif result == "Add new version":
                            context = kwargs["entity"].copy()
                            context["identifier"] = identifier
                            context["mediaType"] = mediaType
                            version = self.getHighestMediaVersion(context)
                            self.createVersion(
                                entity=kwargs["entity"],
                                identifier=kwargs["task"],
                                identifierType=kwargs["mediaType"],
                                version=version
                            )

                            if kwargs["mediaType"] == "3drenders":
                                self.createAov(entity=kwargs["entity"], identifier=kwargs["task"], version=version, aov="rgb")

                            result = self.ingestMedia(files, entity, identifier, version, aov, mediaType) or {}
                            return {"result": result.get("result"), "versionAdded": True}

                    self.copyMsg.show()
                    if copyMsg.msg:
                        b_cnl = copyMsg.msg.buttons()[0]
                        b_cnl.setVisible(True)
                        b_cnl.clicked.connect(self.onIngestCanceled)

                    QApplication.processEvents()

                targetPath = targetPath.replace("\\", "/")
                copyThread = self.core.copyWithProgress(file, targetPath, popup=False, start=False)
                self.ingestThreads.append(copyThread)
                copyThread.finished.connect(lambda t=copyThread, tp=targetPath: self.onMediaFileIngested(t, tp, len(files)))
                copyThread.start()

            details = entity.copy()
            details["identifier"] = identifier
            details["user"] = kwargs["user"]
            details["version"] = kwargs["version"]
            details["comment"] = kwargs.get("comment", "")
            details["extension"] = kwargs["extension"]

            infoPath = self.getMediaVersionInfoPathFromFilepath(targetPath, mediaType=mediaType)
            self.core.saveVersionInfo(filepath=os.path.dirname(infoPath), details=details)
            while (len(self.ingestedFiles) != len(files)) and not self.ingestCanceled:
                time.sleep(0.1)
                QApplication.processEvents()

        return {"result": self.ingestedFiles, "versionAdded": False}

    @err_catcher(name=__name__)
    def onMediaFileIngested(self, thread, targetPath, numFiles):
        self.ingestedFiles.append(targetPath)
        logger.debug("ingested media: %s" % targetPath)
        baseTxt = "Copying file - please wait..\n\n"
        updatedText = baseTxt + "%s/%s" % (len(self.ingestedFiles), numFiles)
        self.copyMsg.text = updatedText
        if self.copyMsg.msg:
            self.copyMsg.msg.setText(updatedText)
            QApplication.processEvents()

        if len(self.ingestedFiles) == numFiles:
            self.copyMsg.close()

    @err_catcher(name=__name__)
    def onIngestCanceled(self):
        self.ingestCanceled = True
        for thread in self.ingestThreads:
            if thread.isRunning():
                thread.cancel()

    @err_catcher(name=__name__)
    def checkMasterVersions(self, entities, parent=None):
        self.dlg_masterManager = self.core.paths.masterManager(self.core, entities, "media", parent=parent)
        self.dlg_masterManager.refreshData()
        if not self.dlg_masterManager.outdatedVersions:
            msg = "All master versions of the selected entities are up to date."
            self.core.popup(msg, severity="info")
            return

        self.dlg_masterManager.show()

    @err_catcher(name=__name__)
    def getOutdatedMasterVersions(self, entities):
        outdatedVersions = []
        for entity in entities:
            idfs = self.getIdentifiersByType(entity)
            for cat in idfs:
                for idf in idfs[cat]:
                    versions = self.getVersionsFromContext(idf)
                    latestVersion = self.getLatestVersionFromVersions(versions)
                    if not latestVersion:
                        continue

                    if latestVersion["version"] == "master":
                        versionNumber = self.getMasterVersionNumber(latestVersion["path"])
                        masterLoc = self.getLocationFromPath(latestVersion["path"])
                        locVersions = [v for v in versions if self.getLocationFromPath(v["path"]) == masterLoc]
                        latestNumberVersion = self.getLatestVersionFromVersions(locVersions, includeMaster=False)
                        if latestNumberVersion and latestNumberVersion["version"] != versionNumber:
                            outdatedVersions.append({"master": latestVersion, "latest": latestNumberVersion})
                    else:
                        outdatedVersions.append({"master": None, "latest": latestVersion})

        return outdatedVersions
