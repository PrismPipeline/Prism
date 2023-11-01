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
import shutil
import platform
import errno

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class Products(object):
    def __init__(self, core):
        self.core = core

    @err_catcher(name=__name__)
    def getProductNamesFromEntity(self, entity, locations=None):
        data = self.getProductsFromEntity(entity, locations=locations)
        names = {}
        for product in data:
            idf = product["product"]
            if idf not in names:
                names[idf] = product
                names[idf]["locations"] = []

            names[idf]["locations"].append(product["path"])

        return names

    @err_catcher(name=__name__)
    def getProductPathFromEntity(self, entity, includeProduct=False):
        key = "products"
        context = entity.copy()
        path = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )
        if not includeProduct:
            path = os.path.dirname(path)

        return path

    @err_catcher(name=__name__)
    def getProductsFromEntity(self, entity, locations=None):
        locationData = self.core.paths.getExportProductBasePaths()
        searchLocations = []
        for locData in locationData:
            if not locations or locData in locations or "all" in locations:
                searchLocations.append(locData)

        key = "products"
        products = []
        for loc in searchLocations:
            context = entity.copy()
            context["project_path"] = locationData[loc]
            template = self.core.projects.getResolvedProjectStructurePath(
                key, context=context
            )
            productData = self.core.projects.getMatchingPaths(template)
            for data in productData:
                if data.get("path", "").endswith(".json"):
                    continue

                d = context.copy()
                d.update(data)
                products.append(d)

        return products

    @err_catcher(name=__name__)
    def getLocationPathFromLocation(self, location):
        locDict = self.core.paths.getExportProductBasePaths()
        if location in locDict:
            return locDict[location]

    @err_catcher(name=__name__)
    def getLocationFromFilepath(self, path):
        locDict = self.core.paths.getExportProductBasePaths()
        nPath = os.path.normpath(path)
        locations = []
        for location in locDict:
            if nPath.startswith(locDict[location]):
                locations.append(location)

        if locations:
            return sorted(locations, key=lambda x: len(locDict[x]), reverse=True)[0]

    @err_catcher(name=__name__)
    def getVersionStackContextFromPath(self, filepath):
        context = self.core.paths.getCachePathData(filepath)
        if "asset_path" in context:
            context["asset"] = os.path.basename(context["asset_path"])

        if "version" in context:
            del context["version"]
        if "comment" in context:
            del context["comment"]
        if "user" in context:
            del context["user"]

        return context

    @err_catcher(name=__name__)
    def getVersionsFromSameVersionStack(self, path):
        context = self.getVersionStackContextFromPath(path)
        if not context or "product" not in context:
            return []

        versionData = self.getVersionsFromContext(context)
        return versionData

    @err_catcher(name=__name__)
    def getVersionsFromProduct(self, entity, product, locations="all"):
        if locations == "all":
            locations = self.core.paths.getExportProductBasePaths()

        versions = []
        for loc in locations:
            context = entity.copy()
            if "version" in context:
                del context["version"]
            if "comment" in context:
                del context["comment"]
            if "user" in context:
                del context["user"]
            if "paths" in context:
                del context["paths"]

            context["product"] = product
            context["project_path"] = locations[loc]
            locVersions = self.getVersionsFromContext(context, locations={loc: locations[loc]})
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
    def getDataFromVersionContext(self, context):
        path = context.get("path", "")
        if not path:
            path = self.getPreferredFileFromVersion(context)

        data = self.core.paths.getCachePathData(path)
        return data

    @err_catcher(name=__name__)
    def getVersionsFromPath(self, path):
        entityType = self.core.paths.getEntityTypeFromPath(path)

        key = "products"
        context = {"entityType": entityType}
        template = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )
        context = self.core.projects.extractKeysFromPath(path, template, context=context)
        return self.getVersionsFromContext(context)

    @err_catcher(name=__name__)
    def getVersionsFromContext(self, context, locations=None):
        locationData = self.core.paths.getExportProductBasePaths()
        searchLocations = []
        for locData in locationData:
            if not locations or locData in locations or "all" in locations:
                searchLocations.append(locData)

        key = "productVersions"
        versions = []
        for loc in searchLocations:
            ctx = context.copy()
            ctx["project_path"] = locationData[loc]
            template = self.core.projects.getResolvedProjectStructurePath(
                key, context=ctx
            )

            versionData = self.core.projects.getMatchingPaths(template)
            for data in versionData:
                c = ctx.copy()
                c.update(data)
                if self.getIntVersionFromVersionName(c["version"]) is None and c["version"] != "master":
                    continue

                c["paths"] = [data.get("path")]
                if c["version"] and "_" in c["version"] and c["version"].count("_") == 1:
                    c["version"], c["wedge"] = c["version"].split("_")

                if "locations" in c:
                    c["locations"] = list(c["locations"])

                for version in versions:
                    if version.get("version") == c.get("version"):
                        version["paths"].append(c.get("path"))
                        break
                else:
                    versions.append(c)
                    continue

        return versions

    @err_catcher(name=__name__)
    def getVersionFromFilepath(self, path, num=False):
        data = self.getProductDataFromFilepath(path)
        if "version" not in data:
            return

        version = data["version"]
        if num:
            version = self.getIntVersionFromVersionName(version)

        return version

    @err_catcher(name=__name__)
    def getProductDataFromFilepath(self, filepath):
        if not filepath:
            return {}

        path = os.path.normpath(filepath)
        entityType = self.core.paths.getEntityTypeFromPath(path)

        if self.core.prism1Compatibility:
            data = {}
            data["extension"] = os.path.splitext(path)[1]
            data["unit"] = os.path.basename(os.path.dirname(path))
            versionName = os.path.basename(os.path.dirname(os.path.dirname(path)))
            version = versionName.split("_", 1)[0]
            data["version"] = version
            data["comment"] = versionName.split("_", 1)[1].rsplit("_", 1)[0]
            data["user"] = versionName.split("_", 1)[1].rsplit("_", 1)[-1]
        else:
            if entityType == "asset":
                key = "productFilesAssets"
            elif entityType == "shot":
                key = "productFilesShots"
            else:
                return {}

            context = {"entityType": entityType}
            context["project_path"] = self.getLocationPathFromLocation(self.getLocationFromFilepath(path))
            template = self.core.projects.getResolvedProjectStructurePath(key, context=context)
            context = {"entityType": entityType, "project_path": context["project_path"]}
            data = self.core.projects.extractKeysFromPath(path, template, context=context)
            data["project_path"] = context["project_path"]
            if "asset_path" in data:
                data["asset"] = os.path.basename(data["asset_path"])

        data["type"] = entityType
        if "_" in data.get("version", "") and data.get("version", "").count("_") == 1:
            data["version"], data["wedge"] = data["version"].split("_")

        return data

    @err_catcher(name=__name__)
    def getProductDataFromVersionFolder(self, path):
        if not path:
            return {}

        path = os.path.normpath(path)
        entityType = self.core.paths.getEntityTypeFromPath(path)

        if self.core.prism1Compatibility:
            data = {}
            data["unit"] = os.path.basename(path)
            versionName = os.path.basename(os.path.dirname(path))
            
            version = versionName.split("_", 1)[0]
            data["version"] = version
            if len(versionName.split("_", 1)) > 1:
                data["comment"] = versionName.split("_", 1)[1].rsplit("_", 1)[0]
            else:
                data["comment"] = ""

            if len(versionName.split("_", 1)) > 1:
                data["user"] = versionName.split("_", 1)[1].rsplit("_", 1)[-1]
            else:
                data["user"] = ""
        else:
            if entityType not in ["asset", "shot"]:
                return {}

            key = "productVersions"
            context = {"entityType": entityType}
            context["project_path"] = self.getLocationPathFromLocation(self.getLocationFromFilepath(path))
            template = self.core.projects.getResolvedProjectStructurePath(key, context=context)
            context = {"entityType": entityType, "project_path": context["project_path"]}
            data = self.core.projects.extractKeysFromPath(path, template, context=context)
            data["project_path"] = context["project_path"]
            if "asset_path" in data:
                data["asset"] = os.path.basename(data["asset_path"])

        data["type"] = entityType
        if "_" in data.get("version", "") and data.get("version", "").count("_") == 1:
            data["version"], data["wedge"] = data["version"].split("_")

        return data

    @err_catcher(name=__name__)
    def getIntVersionFromVersionName(self, versionName):
        if versionName.startswith("v"):
            versionName = versionName[1:]

        versionName = versionName.split("_")[0].split(" ")[0]

        try:
            version = int(versionName)
        except:
            return

        return version

    @err_catcher(name=__name__)
    def getLatestVersionFromVersions(self, versions, includeMaster=True, wedge=None):
        if not versions:
            return

        if not self.getUseMaster():
            includeMaster = False

        sortedVersions = sorted(
            versions,
            key=lambda x: x["version"] if x["version"] != "master" else "zzz",
            reverse=True,
        )

        highestVersion = None
        for version in sortedVersions:
            if not includeMaster and version["version"] == "master":
                continue

            if version["version"] is None:
                continue

            if not self.getPreferredFileFromVersion(version):
                continue

            if wedge is None:
                return version

            if wedge == version.get("wedge"):
                return version

            if highestVersion and highestVersion["version"] != version["version"]:
                return

            highestVersion = version

    @err_catcher(name=__name__)
    def getLatestVersionFromPath(self, path, includeMaster=True):
        if not path:
            return {}

        latestVersion = None
        path = os.path.normpath(path)
        versions = self.getVersionsFromSameVersionStack(path)
        latestVersion = self.getLatestVersionFromVersions(
            versions, includeMaster=includeMaster
        )
        return latestVersion

    @err_catcher(name=__name__)
    def getLatestVersionpathFromProduct(self, product, entity=None, includeMaster=True, wedge=None):
        if not entity:
            fname = self.core.getCurrentFileName()
            entity = self.core.getScenefileData(fname)
            if entity.get("type") not in ["asset", "shot"]:
                return

        versions = self.getVersionsFromProduct(entity, product)
        version = self.getLatestVersionFromVersions(
            versions, includeMaster=includeMaster, wedge=wedge
        )
        if not version:
            return

        filepath = self.getPreferredFileFromVersion(version)
        return filepath

    @err_catcher(name=__name__)
    def getVersionInfoFromVersion(self, version):
        if "path" not in version:
            return

        infopath = self.core.getVersioninfoPath(version["path"])
        data = self.core.getConfig(configPath=infopath) or {}
        return data

    @err_catcher(name=__name__)
    def getPreferredFileFromVersion(self, version, location=None):
        if not version:
            return ""

        info = self.getVersionInfoFromVersion(version)
        if info and "path" in version and "preferredFile" in info:
            prefFile = os.path.join(version["path"], info["preferredFile"])
            if os.path.exists(prefFile):
                return prefFile

        context = version.copy()
        if location:
            locationPath = self.getLocationPathFromLocation(location)
            context["project_path"] = locationPath

        if "type" in version:
            entityType = version["type"]
        else:
            entityType = self.core.paths.getEntityTypeFromPath(version["path"])

        if "extension" in context:
            del context["extension"]

        if self.core.prism1Compatibility:
            cmpath = os.path.join(version["path"], "centimeter")
            mpath = os.path.join(version["path"], "meter")
            fileDatas = []
            for upath in [cmpath, mpath]:
                if os.path.exists(upath):
                    fileDatas += [{"product": version["product"], "path": os.path.join(upath, f)} for f in os.listdir(upath)]
        else:
            if entityType == "asset":
                key = "productFilesAssets"
            elif entityType == "shot":
                key = "productFilesShots"

            if os.path.isfile(context.get("path", "")) and context.get("wedge") == os.path.basename(context.get("path", "")):
                del context["wedge"]
            
            template = self.core.projects.getResolvedProjectStructurePath(
                key, context=context
            )
            fileDatas = self.core.projects.getMatchingPaths(template)
            if not fileDatas:
                files = []
                for root, folders, files in os.walk(version["path"]):
                    break

                fileDatas = [{"path": os.path.join(version["path"], file)} for file in files]

        blacklistExtensions = [".txt", ".ini", ".yml", ".json", ".xgen"]
        filepath = None
        if "path" in context:
            del context["path"]

        for fileData in fileDatas:
            fileData.update(context)
            filepath = fileData["path"]

            ext = os.path.splitext(filepath)[1]
            if ext in blacklistExtensions or os.path.basename(filepath)[0] == ".":
                continue

            filepath = getattr(self.core.appPlugin, "overrideImportpath", lambda x: x)(
                filepath
            )
            shotCamFormat = getattr(self.core.appPlugin, "shotcamFormat", ".abc")
            if (
                shotCamFormat == ".fbx"
                and version["product"] == "_ShotCam"
                and filepath.endswith(".abc")
                and os.path.exists(filepath[:-3] + "fbx")
            ):
                filepath = filepath[:-3] + "fbx"

            objPath = filepath[:-3] + "obj"
            if (filepath.endswith(".mtl") or filepath.endswith(".bmp")) and os.path.exists(objPath):
                filepath = objPath
            break

        return filepath

    @err_catcher(name=__name__)
    def setPreferredFileForVersionDlg(self, version, callback=None):
        self.dlg_prefVersion = PreferredVersionDialog(self, version)
        self.dlg_prefVersion.signalSelected.connect(lambda x, y: self.setPreferredFileForVersion(x, y, callback))
        self.dlg_prefVersion.show()

    @err_catcher(name=__name__)
    def setPreferredFileForVersion(self, version, preferredFile, callback=None):
        if "path" not in version:
            return

        infoPath = self.core.getVersioninfoPath(version["path"])
        logger.debug("setting preferredFile: %s - %s" % (version["path"], preferredFile))
        self.core.setConfig("preferredFile", val=preferredFile, configPath=infoPath)
        if callback:
            callback()

    @err_catcher(name=__name__)
    def getVersionpathFromProductVersion(self, product, version, entity=None, wedge=None):
        if not entity:
            fname = self.core.getCurrentFileName()
            entity = self.core.getScenefileData(fname)
            if entity.get("type") not in ["asset", "shot"]:
                return

        versions = self.getVersionsFromProduct(entity, product)
        filepath = None
        for v in versions:
            if v["version"] == version:
                if wedge is None or wedge == v.get("wedge"):
                    filepath = self.getPreferredFileFromVersion(v)
                    break

        return filepath

    @err_catcher(name=__name__)
    def generateProductPath(
        self,
        entity,
        task,
        extension=None,
        startframe=None,
        endframe=None,
        comment=None,
        user=None,
        version=None,
        framePadding=None,
        location=None,
        returnDetails=False,
        wedge=None
    ):
        if framePadding is None:
            if startframe == endframe or extension != ".obj":
                framePadding = ""
            else:
                framePadding = "#" * self.core.framePadding

        comment = comment or ""
        versionUser = user or self.core.user
        extension = extension or ""
        location = location or "global"
        wedge = wedge or ""
        if not version:
            version = self.getNextAvailableVersion(entity, task)

        if wedge == "" and "/@wedge@" in self.core.projects.getTemplatePath("productVersions"):
            wedge = "0"

        basePath = self.core.paths.getExportProductBasePaths()[location]
        context = entity.copy()
        context.update(
            {
                "project_path": basePath,
                "product": task,
                "comment": comment,
                "version": version,
                "user": versionUser,
                "frame": framePadding,
                "extension": extension,
                "wedge": wedge,
            }
        )

        if self.core.prism1Compatibility:
            context["unit"] = "meter"

        if "asset_path" in context:
            context["asset"] = os.path.basename(context["asset_path"])

        if entity["type"] == "asset":
            key = "productFilesAssets"
        elif entity["type"] == "shot":
            key = "productFilesShots"
        else:
            return ""

        outputPath = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )

        if returnDetails:
            context["path"] = outputPath
            return context
        else:
            return outputPath

    @err_catcher(name=__name__)
    def getNextAvailableVersion(self, entity, product):
        if not self.core.separateOutputVersionStack:
            fileName = self.core.getCurrentFileName()
            fnameData = self.core.getScenefileData(fileName)
            if fnameData.get("type") in ["asset", "shot"]:
                hVersion = fnameData["version"]
            else:
                hVersion = self.core.versionFormat % self.core.lowestVersion

            return hVersion

        versions = self.getVersionsFromProduct(entity, product)
        latest = self.getLatestVersionFromVersions(versions, includeMaster=False)
        if latest:
            latestNum = self.getIntVersionFromVersionName(latest["version"])
            if latestNum is not None:
                num = latestNum + 1
                version = self.core.versionFormat % num
            else:
                version = self.core.versionFormat % self.core.lowestVersion
        else:
            version = self.core.versionFormat % self.core.lowestVersion

        return version

    @err_catcher(name=__name__)
    def getVersionInfoPathFromProductFilepath(self, filepath):
        return os.path.dirname(filepath)

    @err_catcher(name=__name__)
    def setComment(self, versionPath, comment):
        infoPath = self.core.getVersioninfoPath(versionPath)
        versionInfo = {}
        if os.path.exists(infoPath):
            versionInfo = self.core.getConfig(configPath=infoPath) or {}

        versionInfo["comment"] = comment
        self.core.setConfig(data=versionInfo, configPath=infoPath)

    @err_catcher(name=__name__)
    def updateMasterVersion(self, path):
        data = self.core.paths.getCachePathData(path)

        forcedLoc = os.getenv("PRISM_PRODUCT_MASTER_LOC")
        if forcedLoc:
            location = forcedLoc
        else:
            location = self.getLocationFromFilepath(path)

        origVersion = data.get("version")
        if not origVersion:
            msg = "Invalid product version. Make sure the version contains valid files."
            self.core.popup(msg)
            return

        data["type"] = self.core.paths.getEntityTypeFromPath(path)
        masterPath = self.generateProductPath(
            entity=data,
            task=data.get("product"),
            extension=data.get("extension", ""),
            version="master",
            location=location,
        )
        if masterPath:
            logger.debug("updating master version: %s from %s" % (masterPath, path))
        else:
            logger.warning("failed to generate masterpath: %s %s" % (data, location))
            msg = "Failed to generate masterpath. Please contact the support."
            self.core.popup(msg)
            return

        msg = "Failed to update master version. Couldn't remove old master version.\n\n%s"
        result = self.deleteMasterVersion(masterPath, msg)
        if not result:
            return

        if not os.path.exists(os.path.dirname(masterPath)):
            try:
                os.makedirs(os.path.dirname(masterPath))
            except Exception as e:
                if e.errno != errno.EEXIST:
                    raise

        masterDrive = os.path.splitdrive(masterPath)[0]
        drive = os.path.splitdrive(path)[0]

        seqFiles = self.core.detectFileSequence(path)
        if not seqFiles:
            return

        useHL = os.getenv("PRISM_USE_HARDLINK_MASTER", None)
        for seqFile in seqFiles:
            if len(seqFiles) > 1:
                extData = self.core.paths.splitext(seqFile)
                base = extData[0]
                frameStr = "." + base[-self.core.framePadding:]
                base, ext = self.core.paths.splitext(masterPath)
                masterPathPadded = base + frameStr + ext
            else:
                masterPathPadded = masterPath

            if (
                platform.system() == "Windows"
                and drive == masterDrive
                and useHL
                and not masterDrive.startswith("\\")
            ):
                self.core.createSymlink(masterPathPadded, seqFile)
            else:
                shutil.copy2(seqFile, masterPathPadded)

        folderPath = self.getVersionInfoPathFromProductFilepath(path)
        infoPath = self.core.getVersioninfoPath(folderPath)
        folderPath = self.getVersionInfoPathFromProductFilepath(masterPath)
        masterInfoPath = self.core.getVersioninfoPath(folderPath)
        if (
            platform.system() == "Windows"
            and drive == masterDrive
            and useHL
            and not masterDrive.startswith("\\")
        ):
            self.core.createSymlink(masterInfoPath, infoPath)
        else:
            if os.path.exists(infoPath):
                shutil.copy2(infoPath, masterInfoPath)

        infoData = self.core.getConfig(configPath=infoPath)
        if infoData and "preferredFile" in infoData:
            if infoData["preferredFile"] == os.path.basename(path):
                newPreferredFile = os.path.basename(masterPathPadded)
                if newPreferredFile != infoData["preferredFile"]:
                    self.core.setConfig("preferredFile", val=newPreferredFile, configPath=masterInfoPath)

        processedFiles = [os.path.basename(infoPath)] + [os.path.basename(b) for b in seqFiles]
        files = os.listdir(os.path.dirname(path))
        for file in files:
            if file in processedFiles:
                continue

            filepath = os.path.join(os.path.dirname(path), file)
            fileTargetName = os.path.basename(filepath)
            if data["product"] == "_ShotCam" and not os.path.isdir(filepath) and origVersion in fileTargetName:
                fileTargetName = fileTargetName.replace(origVersion, "master")

            fileTargetPath = os.path.join(os.path.dirname(masterPathPadded), fileTargetName)
            if not os.path.exists(os.path.dirname(fileTargetPath)):
                try:
                    os.makedirs(os.path.dirname(fileTargetPath))
                except:
                    self.core.popup("The directory could not be created: %s" % os.path.dirname(fileTargetPath))
                    return

            fileTargetPath = fileTargetPath.replace("\\", "/")
            if os.path.isdir(filepath):
                self.core.copyfolder(filepath, fileTargetPath)
            else:
                self.core.copyfile(filepath, fileTargetPath)

        self.core.configs.clearCache(path=masterInfoPath)
        self.core.callback(name="masterVersionUpdated", args=[masterPath])
        return masterPath

    @err_catcher(name=__name__)
    def renameMaster(self, masterFolder):
        delBasePath = os.path.join(os.path.dirname(masterFolder), ".delete")
        valid = True
        if os.path.exists(delBasePath):
            try:
                shutil.rmtree(delBasePath)
            except:
                pass

        if not os.path.exists(delBasePath):
            try:
                os.makedirs(delBasePath)
            except Exception:
                valid = False

        if valid:
            delPath = os.path.join(delBasePath, os.path.basename(masterFolder))
            while os.path.exists(delPath):
                num = delPath.rsplit("_", 1)[-1]
                try:
                    intnum = int(num)
                    base = delPath.rsplit("_", 1)[0]
                except:
                    intnum = 0
                    base = delPath

                delPath = base + "_" + str(intnum + 1)

            try:
                os.rename(masterFolder, delPath)
            except:
                pass
            else:
                return True

    @err_catcher(name=__name__)
    def deleteMasterVersion(self, path, errorMsg=None, allowClear=True, allowRename=True):
        context = self.getVersionStackContextFromPath(path)
        context["version"] = "master"
        key = "productVersions"
        masterFolder = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )

        if os.path.exists(masterFolder):
            try:
                shutil.rmtree(masterFolder)
            except Exception as e:
                if self.core.pb and allowClear:
                    self.core.pb.productBrowser.tw_versions.selectionModel().clearSelection()
                    return self.deleteMasterVersion(path, errorMsg=errorMsg, allowClear=False, allowRename=allowRename)

                if allowRename:
                    renamed = self.renameMaster(masterFolder)
                    if renamed:
                        return True

                logger.warning(e)
                msg = (errorMsg or "Couldn't remove the existing master version:\n\n%s") % (str(e))
                result = self.core.popupQuestion(
                    msg,
                    buttons=["Retry", "Don't delete master version"],
                    icon=QMessageBox.Warning,
                )
                if result == "Retry":
                    return self.deleteMasterVersion(path, errorMsg=errorMsg, allowClear=allowClear, allowRename=allowRename)
                else:
                    return False

        return True

    @err_catcher(name=__name__)
    def getMasterVersionNumber(self, masterPath):
        versionData = self.core.paths.getCachePathData(masterPath, addPathData=False, validateModTime=True)
        if "sourceVersion" in versionData:
            return versionData["sourceVersion"]

        if "version" in versionData:
            return versionData["version"]

    @err_catcher(name=__name__)
    def getMasterVersionLabel(self, path):
        versionName = "master"
        versionData = self.core.paths.getCachePathData(path, addPathData=False, validateModTime=True)
        if "sourceVersion" in versionData:
            versionName = "master (%s)" % versionData["sourceVersion"]
        elif "version" in versionData:
            versionName = "master (%s)" % versionData["version"]

        return versionName

    @err_catcher(name=__name__)
    def createProduct(self, entity, product):
        context = entity.copy()
        context["product"] = product
        path = self.core.projects.getResolvedProjectStructurePath("products", context)

        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except:
                self.core.popup("The directory %s could not be created" % path)
                return
            else:
                self.core.callback(
                    name="onProductCreated",
                    args=[self, path, context],
                )

            logger.debug("product created %s" % path)
        else:
            logger.debug("product already exists: %s" % path)

        return path

    @err_catcher(name=__name__)
    def getPreferredFileFromFiles(self, files, relative=False):
        for file in files:
            if os.path.isfile(file):
                if relative:
                    filepath = os.path.basename(file)
                else:
                    filepath = file

                return filepath

        for file in files:
            if os.path.isdir(file):
                for root, dirs, files in os.walk(file):
                    if files:
                        if relative:
                            filepath = os.path.join(root, files[0]).replace(os.path.dirname(file), "").strip("\\/")
                        else:
                            filepath = os.path.join(root, files[0])

                        return filepath

    @err_catcher(name=__name__)
    def ingestProductVersion(self, files, entity, product, comment=None):
        if comment is None:
            if len(files) > 1:
                comment = "ingested files"
            else:
                comment = "ingested file: %s" % os.path.basename(files[0])
    
        kwargs = {
            "entity": entity,
            "task": product,
            "comment": comment,
            "user": self.core.user,
        }

        version = self.getNextAvailableVersion(entity=entity, product=product)
        kwargs["version"] = version
        prefFile = self.getPreferredFileFromFiles(files, relative=True)
        if not prefFile:
            msg = "No file to ingest."
            self.core.popup(msg)
            return

        createdFiles = []
        targetPath = self.generateProductPath(**kwargs)
        for file in files:
            fileTargetPath = os.path.join(os.path.dirname(targetPath), os.path.basename(file))
            if not os.path.exists(os.path.dirname(fileTargetPath)):
                try:
                    os.makedirs(os.path.dirname(fileTargetPath))
                except:
                    self.core.popup("The directory could not be created")
                    return

            fileTargetPath = fileTargetPath.replace("\\", "/")
            self.copyThread = self.core.copyWithProgress(file, fileTargetPath, popup=False, start=False)

            isFolder = os.path.isdir(file)
            if isFolder:
                msg = "Copying folder - please wait..\n\n\n"
            else:
                msg = "Copying file - please wait..\n\n\n"

            self.copyMsg = self.core.waitPopup(self.core, msg)

            self.copyThread.updated.connect(lambda x: self.core.updateProgressPopup(x, self.copyMsg))
            self.copyThread.finished.connect(self.copyMsg.close)
            if self.copyMsg.msg:
                b_cnl = self.copyMsg.msg.buttons()[0]
                b_cnl.setVisible(True)
                b_cnl.clicked.connect(self.copyThread.cancel)

            self.copyThread.start()
            self.copyMsg.exec_()

            createdFiles.append(fileTargetPath)
            logger.debug("ingested product: %s" % fileTargetPath)

        details = entity.copy()
        details["product"] = product
        details["user"] = kwargs["user"]
        details["version"] = version
        details["comment"] = kwargs["comment"]
        details["extension"] = os.path.splitext(prefFile)[1]
        details["preferredFile"] = prefFile

        infoPath = self.getVersionInfoPathFromProductFilepath(targetPath)
        self.core.saveVersionInfo(filepath=infoPath, details=details)

        return createdFiles

    @err_catcher(name=__name__)
    def getUseMaster(self):
        return self.core.getConfig(
            "globals", "useMasterVersion", dft=True, config="project"
        )

    @err_catcher(name=__name__)
    def checkMasterVersions(self, entities, parent=None):
        self.dlg_masterManager = self.core.paths.masterManager(self.core, entities, "products", parent=parent)
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
            products = self.getProductsFromEntity(entity)
            for product in products:
                versions = self.getVersionsFromContext(product)
                latestVersion = self.getLatestVersionFromVersions(versions)
                if not latestVersion:
                    continue

                if latestVersion["version"] == "master":
                    versionNumber = self.getMasterVersionNumber(latestVersion["path"])
                    masterLoc = self.getLocationFromFilepath(latestVersion["path"])
                    locVersions = [v for v in versions if self.getLocationFromFilepath(v["path"]) == masterLoc]
                    latestNumberVersion = self.getLatestVersionFromVersions(locVersions, includeMaster=False)
                    if latestNumberVersion and latestNumberVersion["version"] != versionNumber:
                        outdatedVersions.append({"master": latestVersion, "latest": latestNumberVersion})
                else:
                    outdatedVersions.append({"master": None, "latest": latestVersion})

        return outdatedVersions

    @err_catcher(name=__name__)
    def getGroupFromProduct(self, product):
        productPath = self.getProductPathFromEntity(product, includeProduct=False)
        cfgPath = os.path.join(productPath, "products" + self.core.configs.getProjectExtension())
        group = self.core.getConfig(product.get("product"), "group", configPath=cfgPath)
        return group

    @err_catcher(name=__name__)
    def setProductsGroup(self, products, group, projectWide=False):
        productPath = self.getProductPathFromEntity(products[0], includeProduct=False)
        cfgPath = os.path.join(productPath, "products" + self.core.configs.getProjectExtension())
        data = self.core.getConfig(configPath=cfgPath) or {}
        for product in products:
            if product.get("product") not in data:
                data[product.get("product")] = {}

            data[product.get("product")]["group"] = group

        self.core.setConfig(data=data, configPath=cfgPath)

    @err_catcher(name=__name__)
    def getTagsFromProduct(self, product):
        productPath = self.getProductPathFromEntity(product, includeProduct=False)
        cfgPath = os.path.join(productPath, "products" + self.core.configs.getProjectExtension())
        tags = self.core.getConfig(product.get("product"), "tags", configPath=cfgPath) or []
        return tags

    @err_catcher(name=__name__)
    def setProductTags(self, product, tags):
        productPath = self.getProductPathFromEntity(product, includeProduct=False)
        cfgPath = os.path.join(productPath, "products" + self.core.configs.getProjectExtension())
        self.core.setConfig(product.get("product"), "tags", val=tags, configPath=cfgPath)

    @err_catcher(name=__name__)
    def getProductsByTags(self, entity, tags):
        products = self.getProductsFromEntity(entity)
        foundProducts = []
        for tag in tags:
            for product in products:
                if product in foundProducts:
                    continue

                ptags = self.getTagsFromProduct(product)
                if tag in ptags:
                    foundProducts.append(product)

        return foundProducts


class PreferredVersionDialog(QDialog):

    signalSelected = Signal(object, object)

    def __init__(self, origin, version):
        super(PreferredVersionDialog, self).__init__()
        self.origin = origin
        self.core = self.origin.core
        self.version = version
        self.setupUi()
        self.refreshTree()

    @err_catcher(name=__name__)
    def sizeHint(self):
        return QSize(350, 400)

    @err_catcher(name=__name__)
    def setupUi(self):
        self.setWindowTitle("Select Preferred File")
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.tw_files = QTreeWidget()
        self.tw_files.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tw_files.header().setVisible(False)

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Ok", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Cancel", QDialogButtonBox.RejectRole)

        self.bb_main.accepted.connect(self.onAcceptClicked)
        self.bb_main.rejected.connect(self.reject)

        self.lo_main.addWidget(self.tw_files)
        self.lo_main.addWidget(self.bb_main)

    @err_catcher(name=__name__)
    def refreshTree(self):
        self.projectStructure = self.core.projects.getFolderStructureFromPath(self.version["path"])
        self.projectStructure["name"] = os.path.basename(self.version["path"])
        self.tw_files.clear()
        self.addItemToTree(self.projectStructure)
        file = self.origin.getPreferredFileFromVersion(self.version)
        if file:
            file = file.replace(self.version["path"], "")
            self.navigate(file)

    @err_catcher(name=__name__)
    def addItemToTree(self, entity, parent=None):
        if entity["name"] == "versioninfo" + self.core.configs.getProjectExtension():
            return

        item = QTreeWidgetItem([entity["name"]])
        item.setData(0, Qt.UserRole, entity)
        if parent:
            parent.addChild(item)
        else:
            self.tw_files.addTopLevelItem(item)
            item.setExpanded(True)

        if "children" in entity:
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "folder.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            item.setIcon(0, icon)
            for child in entity["children"]:
                self.addItemToTree(child, parent=item)

        return item

    @err_catcher(name=__name__)
    def navigate(self, file):
        self.tw_files.selectionModel().clearSelection()
        hierarchy = file.replace("\\", "/").split("/")
        hierarchy = [x for x in hierarchy if x != ""]
        if not hierarchy:
            return

        hItem = self.tw_files.topLevelItem(0)
        for idx, i in enumerate((hierarchy)):
            for k in range(hItem.childCount() - 1, -1, -1):
                itemName = hItem.child(k).data(0, Qt.UserRole)["name"]
                if itemName == i:
                    hItem = hItem.child(k)
                    if len(hierarchy) > (idx + 1):
                        hItem.setExpanded(True)

                    break
            else:
                break

        hItem.setSelected(True)
        self.tw_files.setCurrentItem(hItem)

    @err_catcher(name=__name__)
    def onAcceptClicked(self):
        item = self.tw_files.currentItem()
        if not item:
            msg = "No file selected."
            self.core.popup(msg)
            return

        selectedData = item.data(0, Qt.UserRole)
        if "path" not in selectedData:
            msg = "No file selected."
            self.core.popup(msg)
            return

        selectedFile = selectedData["path"].replace(self.version["path"], "").strip("\\").strip("/")
        self.signalSelected.emit(self.version, selectedFile)
        self.accept()
