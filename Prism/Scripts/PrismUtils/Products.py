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
import logging
import shutil
import platform

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


logger = logging.getLogger(__name__)


class Products(object):
    def __init__(self, core):
        self.core = core
        self.videoFormats = [".mp4", ".mov"]

    @err_catcher(name=__name__)
    def getProductsFromPaths(self, paths):
        products = {}
        for path in paths:
            pathProducts = self.getProductsFromPath(path)
            for pathProduct in pathProducts:
                if pathProduct in products:
                    products[pathProduct]["locations"] += pathProducts[pathProduct]["locations"]
                else:
                    products[pathProduct] = pathProducts[pathProduct]

        return products

    @err_catcher(name=__name__)
    def getProductsFromPath(self, path):
        products = {}
        for root, folders, files in os.walk(path):
            for folder in folders:
                if folder not in products:
                    products[folder] = {"type": "product", "name": folder, "locations": []}

                fullPath = os.path.join(root, folder)
                products[folder]["locations"].append(fullPath)
            break

        return products

    @err_catcher(name=__name__)
    def getProductsFromEntityPath(self, path):
        productPath = self.getProductPathFromEntityPath(path)
        products = self.getProductsFromPath(productPath)
        return products

    @err_catcher(name=__name__)
    def getProductPathFromEntityPath(self, path):
        return os.path.join(path, "Export")

    @err_catcher(name=__name__)
    def getLocationPathFromLocation(self, location):
        locDict = self.core.getExportPaths()
        if location in locDict:
            return locDict[location]

    @err_catcher(name=__name__)
    def getLocationFromFilepath(self, path):
        locDict = self.core.getExportPaths()
        nPath = os.path.normpath(path)
        for location in locDict:
            if nPath.startswith(locDict[location]):
                return location

    @err_catcher(name=__name__)
    def getVersionsFromPaths(self, paths):
        versions = {}
        for path in paths:
            pathVersions = self.getVersionsFromPath(path)
            for pathVersion in pathVersions:
                if pathVersion in versions:
                    versions[pathVersion]["locations"].update(pathVersions[pathVersion]["locations"])
                else:
                    versions[pathVersion] = pathVersions[pathVersion]

        return versions

    @err_catcher(name=__name__)
    def getVersionFolderFromProductPath(self, path):
        versionFolder = ""
        versionDir = os.path.dirname(path)
        if os.path.basename(versionDir) in ["centimeter", "meter"]:
            versionDir = os.path.dirname(versionDir)

        versionName = self.getVersionNameFromFilepath(path)

        if versionName:
            versionFolder = os.path.dirname(versionDir)

        return versionFolder

    @err_catcher(name=__name__)
    def getVersionsFromPath(self, path):
        versions = {}
        versionPaths = []
        for root, folders, files in os.walk(path):
            for folder in folders:
                nameData = folder.split(self.core.filenameSeparator)
                isVersion = len(nameData) == 3 and folder[0] == "v"
                isMaster = folder == "master"
                if not isVersion and not isMaster:
                    continue

                versionPath = os.path.join(root, folder)
                versionPaths.append(versionPath)
            break

        units = ["centimeter", "meter", ""]
        blacklistExtensions = [".txt", ".ini", ".yml", ".xgen"]
        for versionPath in versionPaths:
            name = os.path.basename(versionPath)
            productName = os.path.basename(os.path.dirname(versionPath))
            version = {"type": "productVersion", "name": name, "locations": {versionPath: {}}}
            for unit in units:

                unitPath = os.path.join(versionPath, unit)
                filepath = None
                for root, folders, files in os.walk(unitPath):
                    if not files:
                        break

                    for file in files:
                        ext = os.path.splitext(file)[1]
                        if ext in blacklistExtensions or file[0] == ".":
                            continue

                        filepath = os.path.join(root, file)
                        filepath = getattr(self.core.appPlugin, "overrideImportpath", lambda x: x)(filepath)
                        shotCamFormat = getattr(self.core.appPlugin, "shotcamFormat", ".abc")
                        if (
                            shotCamFormat == ".fbx"
                            and productName == "_ShotCam"
                            and filepath.endswith(".abc")
                            and os.path.exists(filepath[:-3] + "fbx")
                        ):
                            filepath = filepath[:-3] + "fbx"

                        objPath = filepath[:-3] + "obj"
                        if filepath.endswith(".mtl") and os.path.exists(objPath):
                            filepath = objPath
                        break
                    break

                if not filepath:
                    continue

                version["locations"][versionPath][unit] = filepath

            if not version["locations"][versionPath]:
                continue

            versions[name] = version

        return versions

    @err_catcher(name=__name__)
    def getVersionFromFilepath(self, path):
        fileData = os.path.basename(path).split(
            self.core.filenameSeparator
        )
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
    def getVersionNameFromFilepath(self, path):
        versionDir = os.path.dirname(path)
        if os.path.basename(versionDir) in ["centimeter", "meter"]:
            versionDir = os.path.dirname(versionDir)

        versionName = os.path.basename(versionDir)
        versionData = versionName.split(self.core.filenameSeparator)
        relScenePath = self.core.scenePath.replace(self.core.projectPath, "")
        if (len(versionData) != 3 and versionName != "master") and relScenePath not in path:
            return None

        return versionName

    @err_catcher(name=__name__)
    def getLatestVersionFromPath(self, path):
        latestVersion = None

        versionDir = os.path.dirname(path)
        if os.path.basename(versionDir) in ["centimeter", "meter"]:
            versionDir = os.path.dirname(versionDir)

        versionName = self.getVersionNameFromFilepath(path)

        if versionName:
            taskPath = os.path.dirname(versionDir)
            versions = self.getVersionsFromPath(taskPath)
            if versions:
                latestVersionName = sorted(versions, reverse=True)[0]
                latestVersion = versions[latestVersionName]

        return latestVersion

    @err_catcher(name=__name__)
    def getPreferredFileFromVersion(self, version, preferredUnit=None, location=None):
        preferredUnit = preferredUnit or getattr(self.core.appPlugin, "preferredUnit", "centimeter")

        if location:
            locationPath = self.getLocationPathFromLocation(location)

        filepath = None
        filepathUnit = None
        for vlocation in version["locations"]:
            for unit in version["locations"][vlocation]:
                if location:
                    if vlocation.startswith(locationPath) or not filepath:
                        if unit == preferredUnit or filepathUnit != preferredUnit:
                            filepath = version["locations"][vlocation][unit]
                            filepathUnit = unit
                else:
                    if unit == preferredUnit or filepathUnit != preferredUnit:
                        filepath = version["locations"][vlocation][unit]
                        filepathUnit = unit

        return filepath

    @err_catcher(name=__name__)
    def getUnitsFromVersion(self, version, short=False, location=None):
        units = []

        if location:
            locationPath = self.getLocationPathFromLocation(location)

        for vlocation in version["locations"]:
            if location and not vlocation.startswith(locationPath):
                continue

            for unit in version["locations"][vlocation]:
                if short:
                    if unit == "centimeter":
                        unit = "cm"
                    elif unit == "meter":
                        unit = "m"

                if unit in units:
                    continue

                units.append(unit)

        return sorted(units)

    @err_catcher(name=__name__)
    def getProductPathFromEntity(self, entity, entityName, task):
        if entity == "asset":
            entityPath = os.path.join(self.core.assetPath, entityName)
        elif entity == "shot":
            entityPath = os.path.join(self.core.shotPath, entityName)

        productPath = os.path.join(entityPath, "Export", task)
        return productPath

    @err_catcher(name=__name__)
    def generateProductPath(self, entity, entityName, task, extension, startframe=None, endframe=None, comment=None, user=None, version=None, framePadding=None, unit=None, location="global"):
        prefUnit = unit or self.core.appPlugin.preferredUnit

        if framePadding is None:
            if startframe == endframe or extension != ".obj":
                framePadding = ""
            else:
                framePadding = "." + "#"*self.core.framePadding

        versionUser = user or self.core.user
        hVersion = ""
        if version is not None and version != "master":
            versionData = version.split(self.core.filenameSeparator)
            if len(versionData) == 3:
                hVersion, pComment, versionUser = versionData

        outputPath = self.getProductPathFromEntity(entity, entityName, task)

        if hVersion == "":
            hVersion = self.core.getHighestTaskVersion(outputPath)
            pComment = comment or ""

        if version == "master":
            versionFoldername = "master"
            hVersion = "master"
        else:
            versionFoldername = (
                hVersion
                + self.core.filenameSeparator
                + pComment
                + self.core.filenameSeparator
                + versionUser
            )

        outputPath = os.path.join(outputPath, versionFoldername, prefUnit)
        filename = self.generateProductFilename(entity, entityName, task, hVersion, framePadding, extension)
        outputName = os.path.join(outputPath, filename)

        basePath = self.core.getExportPaths()[location]
        prjPath = os.path.normpath(self.core.projectPath)
        basePath = os.path.normpath(basePath)
        outputName = outputName.replace(prjPath, basePath)
        return outputName

    @err_catcher(name=__name__)
    def generateProductFilename(self, entity, entityName, task, version, framePadding, extension):
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
            if task == "_ShotCam":
                task = "ShotCam"

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
    def updateMasterVersion(self, path):
        data = self.core.paths.getCachePathData(path)

        if data["entityType"] == "asset":
            assetPath = self.core.paths.getEntityBasePathFromProductPath(path)
            entityName = self.core.entities.getAssetRelPathFromPath(assetPath)
        else:
            entityName = self.core.entities.getShotname(data["sequence"], data["shot"])

        location = self.getLocationFromFilepath(path)

        masterPath = self.generateProductPath(
            entity=data["entityType"],
            entityName=entityName,
            task=data["task"],
            extension=data["extension"],
            version="master",
            unit=data["unit"],
            location=location,
        )
        logger.debug("updating master version: %s" % masterPath)

        self.deleteMasterVersion(masterPath)
        if not os.path.exists(os.path.dirname(masterPath)):
            os.makedirs(os.path.dirname(masterPath))

        masterDrive = os.path.splitdrive(masterPath)
        drive = os.path.splitdrive(path)

        seqFiles = self.core.detectFileSequence(path)
        for seqFile in seqFiles:
            if len(seqFiles) > 1:
                frameStr = "." + os.path.splitext(seqFile)[0][-self.core.framePadding:]
                base, ext = os.path.splitext(masterPath)
                masterPathPadded = base + frameStr + ext
            else:
                masterPathPadded = masterPath

            if platform.system() == "Windows" and drive == masterDrive:
                self.core.createSymlink(masterPathPadded, seqFile)
            else:
                shutil.copy2(seqFile, masterPathPadded)

        ext = self.core.configs.preferredExtension
        infoPath = os.path.join(os.path.dirname(os.path.dirname(path)), "versioninfo" + ext)
        masterInfoPath = os.path.join(os.path.dirname(os.path.dirname(masterPath)), "versioninfo" + ext)
        self.core.createSymlink(masterInfoPath, infoPath)
        self.core.setConfig("filename", val=path, configPath=masterInfoPath)
        return masterPath

    @err_catcher(name=__name__)
    def deleteMasterVersion(self, path):
        masterFolder = os.path.dirname(os.path.dirname(path))
        if os.path.exists(masterFolder):
            shutil.rmtree(masterFolder)
            return True
