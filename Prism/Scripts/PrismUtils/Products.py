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
import copy
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class Products(object):
    """Manages cache/export products including versioning and master versions.
    
    Handles creation, retrieval, and management of export products (caches, alembics, etc.)
    Provides version management, master version updates, and product metadata.
    
    Attributes:
        core: Reference to the Prism core instance.
    """
    
    def __init__(self, core: Any) -> None:
        """Initialize the Products manager.
        
        Args:
            core: Reference to the Prism core instance.
        """
        self.core = core

    @err_catcher(name=__name__)
    def getProductNamesFromEntity(self, entity: Dict, locations: Optional[List[str]] = None) -> Dict[str, Dict]:
        """Get all product names for an entity.
        
        Args:
            entity: Entity dict containing type and other entity data.
            locations: Optional list of storage locations to search.
            
        Returns:
            Dict[str, Dict]: Dict mapping product names to product data dicts.
        """
        data = self.getProductsFromEntity(entity, locations=locations)
        names = {}
        useTasks = self.core.products.getLinkedToTasks()
        for product in data:
            if useTasks:
                idf = "%s/%s/%s" % (product.get("department", "unknown"), product.get("task", "unknown"), product["product"])
            else:
                idf = product["product"]

            if idf not in names:
                names[idf] = copy.deepcopy(product)
                names[idf]["locations"] = {}

            names[idf]["locations"].update(product["locations"])

        return names

    @err_catcher(name=__name__)
    def getProductPathFromEntity(self, entity: Dict, includeProduct: bool = False) -> str:
        """Get the base directory path for products from an entity.
        
        Args:
            entity: Entity dict containing type and other entity data.
            includeProduct: If True, includes product name in path.
            
        Returns:
            str: Base path for products.
        """
        key = "products"
        context = entity.copy()
        path = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )
        if not includeProduct:
            path = os.path.dirname(path)

        return path

    @err_catcher(name=__name__)
    def getProductsFromEntity(self, entity: Dict, locations: Optional[List[str]] = None) -> List[Dict]:
        """Get all products for an entity across specified locations.
        
        Args:
            entity: Entity dict containing type and other entity data.
            locations: Optional list of storage locations to search. Searches all if None.
            
        Returns:
            List[Dict]: List of product dicts with metadata and paths.
        """
        if locations == "project_path":
            searchLocations = ["other"]
        else:
            locationData = self.core.paths.getExportProductBasePaths()
            searchLocations = []
            for locData in locationData:
                if not locations or locData in locations or "all" in locations:
                    searchLocations.append(locData)

        key = "products"
        products = []
        for loc in searchLocations:
            context = entity.copy()
            if "product" in context:
                del context["product"]

            if locations != "project_path":
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
                d["locations"] = {loc: data.get("path", "")}
                products.append(d)

        return products

    @err_catcher(name=__name__)
    def getLocationPathFromLocation(self, location: str) -> Optional[str]:
        """Get the file system path for a specific storage location.
        
        Args:
            location: Storage location identifier (e.g., 'global', 'local').
            
        Returns:
            Optional[str]: Filesystem path for the location, or None if not found.
        """
        locDict = self.core.paths.getExportProductBasePaths()
        if location in locDict:
            return locDict[location]

    @err_catcher(name=__name__)
    def getLocationFromFilepath(self, path: str) -> Optional[str]:
        """Determine which storage location contains the given file path.
        
        Args:
            path: File system path to check.
            
        Returns:
            Optional[str]: Location identifier that contains the path, or None if not found.
                         Returns the most specific location if multiple match.
        """
        if not path:
            return

        locDict = self.core.paths.getExportProductBasePaths()
        nPath = os.path.normpath(path)
        locations = []
        for location in locDict:
            if nPath.startswith(locDict[location]):
                locations.append(location)

        if locations:
            return sorted(locations, key=lambda x: len(locDict[x]), reverse=True)[0]

    @err_catcher(name=__name__)
    def getVersionStackContextFromPath(self, filepath: str) -> Dict[str, Any]:
        """Extract version stack context from a file path (excluding version-specific data).
        
        A version stack is all versions of the same product. This method extracts
        the common context (entity, product, etc.) while removing version-specific
        information (version number, comment, user).
        
        Args:
            filepath: Path to a product version file.
            
        Returns:
            Dict[str, Any]: Context dict with entity and product info, but no version details.
        """
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
    def getVersionsFromSameVersionStack(self, path: str) -> List[Dict[str, Any]]:
        """Get all versions in the same version stack as the given path.
        
        This retrieves all versions of the same product from the same entity,
        allowing comparison or selection of different versions.
        
        Args:
            path: Path to any version file in the stack.
            
        Returns:
            List[Dict[str, Any]]: List of version dicts in the same version stack.
        """
        context = self.getVersionStackContextFromPath(path)
        if not context or "product" not in context:
            return []

        versionData = self.getVersionsFromContext(context)
        return versionData

    @err_catcher(name=__name__)
    def getVersionsFromProduct(self, entity: Dict[str, Any], product: str, locations: Union[str, List[str]] = "all") -> List[Dict[str, Any]]:
        """Get all versions of a specific product for an entity across locations.
        
        Searches for all versions of a product and consolidates versions that exist
        in multiple locations, tracking all paths for each version.
        
        Args:
            entity: Entity dict with type and entity information.
            product: Product name to search for.
            locations: Storage locations to search ('all', 'project_path', or list of locations).
            
        Returns:
            List[Dict[str, Any]]: List of version dicts with 'paths' list for multi-location versions.
        """
        locations = locations or "all"
        if locations == "all":
            locPaths = self.core.paths.getExportProductBasePaths()
        elif locations == "project_path":
            locPaths = {"_other": entity["project_path"]}

        versions = []
        for loc in locPaths:
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
            context["project_path"] = locPaths[loc]
            locVersions = self.getVersionsFromContext(context, locations={loc: locPaths[loc]})
            for locVersion in locVersions:
                locVersion["paths"] = [locVersion.get("path")]
                for version in versions:
                    if version.get("version") == locVersion.get("version") and version.get("wedge") == locVersion.get("wedge"):
                        version["paths"].append(locVersion.get("path"))
                        break
                else:
                    versions.append(locVersion)
                    continue

        return versions

    @err_catcher(name=__name__)
    def getDataFromVersionContext(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract full data from a version context, resolving the path if needed.
        
        Args:
            context: Version context dict (may or may not include path).
            
        Returns:
            Dict[str, Any]: Complete data extracted from the version path.
        """
        path = context.get("path", "")
        if not path:
            path = self.getPreferredFileFromVersion(context)

        data = self.core.paths.getCachePathData(path)
        return data

    @err_catcher(name=__name__)
    def getVersionsFromPath(self, path: str) -> List[Dict[str, Any]]:
        """Get all versions for the product referenced by the given path.
        
        Args:
            path: Path to any file within a product version stack.
            
        Returns:
            List[Dict[str, Any]]: List of all versions in the product's version stack.
        """
        entityType = self.core.paths.getEntityTypeFromPath(path)

        key = "products"
        context = {"entityType": entityType}
        template = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )
        context = self.core.projects.extractKeysFromPath(path, template, context=context)
        return self.getVersionsFromContext(context)

    @err_catcher(name=__name__)
    def getVersionsFromContext(self, context: Dict[str, Any], locations: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Get all versions matching a context specification across locations.
        
        Args:
            context: Context dict specifying entity, product, etc.
            locations: Optional dict mapping location names to paths.
            
        Returns:
            List[Dict[str, Any]]: List of version dicts matching the context.
        """
        locationData = self.core.paths.getExportProductBasePaths()
        searchLocations = []
        if locations and "_other" in locations:
            searchLocations = locations
        else:
            for locData in locationData:
                if not locations or locData in locations or "all" in locations:
                    searchLocations.append(locData)

        key = "productVersions"
        versions = []
        for loc in searchLocations:
            ctx = context.copy()
            if loc != "_other":
                ctx["project_path"] = locationData[loc]

            templates = self.core.projects.getResolvedProjectStructurePaths(
                key, context=ctx
            )
            versionData = []
            for template in templates:
                versionData += self.core.projects.getMatchingPaths(template)

            for data in versionData:
                c = copy.deepcopy(ctx)
                c.update(data)
                if self.getIntVersionFromVersionName(c["version"]) is None and c["version"] != "master":
                    continue

                c["locations"] = {}
                c["paths"] = [data.get("path")]
                c["locations"][loc] = data.get("path", "")
                if c["version"] and "_" in c["version"] and c["version"].count("_") == 1:
                    c["version"], c["wedge"] = c["version"].split("_")

                for version in versions:
                    if version.get("version") == c.get("version") and version.get("wedge") == c.get("wedge"):
                        version["paths"].append(c.get("path"))
                        version["locations"].update(c.get("locations"))
                        break
                else:
                    versions.append(c)
                    continue

        return versions

    @err_catcher(name=__name__)
    def getVersionFromFilepath(self, path: str, num: bool = False) -> Optional[Union[str, int]]:
        """Extract version from a product file path.
        
        Args:
            path: Product file path.
            num: If True, returns version as int; if False, returns version string.
            
        Returns:
            Optional[Union[str, int]]: Version string (e.g., 'v0001') or int (1), or None if not found.
        """
        data = self.getProductDataFromFilepath(path)
        if "version" not in data:
            return

        version = data["version"]
        if num:
            version = self.getIntVersionFromVersionName(version)

        return version

    @err_catcher(name=__name__)
    def getProductDataFromFilepath(self, filepath: str) -> Dict[str, Any]:
        """Extract product metadata from a file path.
        
        Parses the filepath to extract entity, product, version, user, and other
        metadata based on the project structure template.
        
        Args:
            filepath: Path to a product file.
            
        Returns:
            Dict[str, Any]: Dict containing extracted metadata (product, version, user, etc.).
        """
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
    def getProductDataFromVersionFolder(self, path: str) -> Dict[str, Any]:
        """Extract product metadata from a version folder path.
        
        Similar to getProductDataFromFilepath but operates on version folder paths
        rather than individual files.
        
        Args:
            path: Path to a product version folder.
            
        Returns:
            Dict[str, Any]: Dict containing extracted metadata (product, version, etc.).
        """
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
    def getIntVersionFromVersionName(self, versionName: str) -> Optional[int]:
        """Convert a version name string to an integer.
        
        Handles formats like 'v0001', 'v1', or just '1'. Extracts the numeric
        portion and converts to int.
        
        Args:
            versionName: Version string (e.g., 'v0001', 'v1_wedge1').
            
        Returns:
            Optional[int]: Integer version number, or None if conversion fails.
        """
        if versionName.startswith("v"):
            versionName = versionName[1:]

        versionName = versionName.split("_")[0].split(" ")[0]

        try:
            version = int(versionName)
        except:
            return

        return version

    @err_catcher(name=__name__)
    def getLatestVersionFromVersions(self, versions: List[Dict[str, Any]], includeMaster: bool = True, wedge: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the latest version from a list of versions.
        
        Sorts versions by version number and optionally includes or excludes the master version.
        Validates that the version has an accessible preferred file.
        
        Args:
            versions: List of version dicts to search.
            includeMaster: Whether to consider the master version. Defaults to True.
            wedge: Optional wedge identifier to filter by.
            
        Returns:
            Optional[Dict[str, Any]]: Latest version dict, or None if no valid versions found.
        """
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
    def getLatestVersionFromPath(self, path: str, includeMaster: bool = True) -> Optional[Dict[str, Any]]:
        """Get the latest version from the same version stack as the given path.
        
        Args:
            path: Path to any file in a version stack.
            includeMaster: Whether to consider the master version. Defaults to True.
            
        Returns:
            Optional[Dict[str, Any]]: Latest version dict from the version stack.
        """
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
    def getLatestVersionFromProduct(self, product: str, entity: Optional[Dict[str, Any]] = None, includeMaster: bool = True, wedge: Optional[str] = None, locations: Optional[Union[str, List[str]]] = None) -> Optional[Dict[str, Any]]:
        """Get the latest version of a specific product.
        
        Args:
            product: Product name.
            entity: Optional entity dict. Uses current scenefile entity if None.
            includeMaster: Whether to include master version. Defaults to True.
            wedge: Optional wedge identifier to filter by.
            locations: Optional storage locations to search.
            
        Returns:
            Optional[Dict[str, Any]]: Latest version dict for the product.
        """
        if not entity:
            fname = self.core.getCurrentFileName()
            entity = self.core.getScenefileData(fname)
            if entity.get("type") not in ["asset", "shot"]:
                return

        versions = self.getVersionsFromProduct(entity, product, locations=locations)
        version = self.getLatestVersionFromVersions(
            versions, includeMaster=includeMaster, wedge=wedge
        )
        if not version:
            return

        return version

    @err_catcher(name=__name__)
    def getLatestVersionpathFromProduct(self, product: str, entity: Optional[Dict[str, Any]] = None, includeMaster: bool = True, wedge: Optional[str] = None, locations: Optional[Union[str, List[str]]] = None) -> Optional[str]:
        """Get the file path of the latest version of a specific product.
        
        Args:
            product: Product name.
            entity: Optional entity dict. Uses current scenefile entity if None.
            includeMaster: Whether to include master version. Defaults to True.
            wedge: Optional wedge identifier to filter by.
            locations: Optional storage locations to search.
            
        Returns:
            Optional[str]: File path to the preferred file of the latest version.
        """
        if not entity:
            fname = self.core.getCurrentFileName()
            entity = self.core.getScenefileData(fname)
            if entity.get("type") not in ["asset", "shot"]:
                return

        versions = self.getVersionsFromProduct(entity, product, locations=locations)
        version = self.getLatestVersionFromVersions(
            versions, includeMaster=includeMaster, wedge=wedge
        )
        if not version:
            return

        filepath = self.getPreferredFileFromVersion(version)
        return filepath

    @err_catcher(name=__name__)
    def getVersionInfoFromVersion(self, version: Dict[str, Any]) -> Dict[str, Any]:
        """Load version info metadata from a version dict.
        
        Reads the versioninfo config file for a version and returns its contents.
        
        Args:
            version: Version dict containing at least a 'path' key.
            
        Returns:
            Dict[str, Any]: Version info data (comment, user, preferredFile, etc.).
        """
        if "path" not in version:
            return

        infopath = self.core.getVersioninfoPath(version["path"])
        data = self.core.getConfig(configPath=infopath) or {}
        return data

    @err_catcher(name=__name__)
    def getUseProductPreviews(self) -> bool:
        """Check if product preview capturing is enabled.
        
        Returns:
            bool: True if product preview capture is enabled in user settings.
        """
        return self.core.getConfig("globals", "capture_viewport_products", config="user", dft=False)

    @err_catcher(name=__name__)
    def getProductPreviewPath(self, productPath: str) -> str:
        """Get the path where a product preview image should be stored.
        
        Args:
            productPath: Path to the product version folder.
            
        Returns:
            str: Path to the preview.jpg file.
        """
        return productPath + "/preview.jpg"

    @err_catcher(name=__name__)
    def generateProductPreview(self) -> Optional[QPixmap]:
        """Generate a preview image for the current product.
        
        Captures the current viewport or uses a recent scene preview,
        scaled to the standard preview dimensions.
        
        Returns:
            Optional[QPixmap]: Preview pixmap, or None if capture fails.
        """
        scenePreviewPath = self.core.entities.getScenePreviewPath(self.core.getCurrentFileName())
        previewTime = self.core.getFileModificationDate(scenePreviewPath, validate=True, asString=False)
        if previewTime and (time.time() - previewTime) < 5:
            return self.core.media.getPixmapFromPath(scenePreviewPath)

        appPreview = getattr(self.core.appPlugin, "captureViewportThumbnail", lambda: None)()
        if not appPreview:
            return

        preview = self.core.media.scalePixmap(appPreview, self.core.scenePreviewWidth, self.core.scenePreviewHeight, fitIntoBounds=False, crop=True)
        return preview

    @err_catcher(name=__name__)
    def setProductPreview(self, productPath: str, preview: QPixmap) -> None:
        """Save a preview image for a product.
        
        Args:
            productPath: Path to the product version folder.
            preview: Pixmap to save as preview.
        """
        prvPath = self.getProductPreviewPath(productPath)
        logger.debug("saving product preview: %s" % prvPath)
        self.core.media.savePixmap(preview, prvPath)

    @err_catcher(name=__name__)
    def getPreferredFileFromVersion(self, version: Dict[str, Any], location: Optional[str] = None) -> str:
        """Get the preferred file path from a version.
        
        The preferred file is the main file users should reference when importing
        the product. This can be explicitly set or automatically determined.
        
        Args:
            version: Version dict containing path and product info.
            location: Optional storage location to prefer.
            
        Returns:
            str: Path to the preferred file for this version.
        """
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
    def setPreferredFileForVersionDlg(self, version: Dict[str, Any], callback: Optional[callable] = None, parent: Optional[QWidget] = None) -> None:
        """Show a dialog to select the preferred file for a version.
        
        Args:
            version: Version dict to set preferred file for.
            callback: Optional callback function to execute after selection.
            parent: Optional parent widget for the dialog.
        """
        self.dlg_prefVersion = PreferredVersionDialog(self, version, parent=parent)
        self.dlg_prefVersion.signalSelected.connect(lambda x, y: self.setPreferredFileForVersion(x, y, callback))
        self.dlg_prefVersion.show()

    @err_catcher(name=__name__)
    def setPreferredFileForVersion(self, version: Dict[str, Any], preferredFile: str, callback: Optional[callable] = None) -> None:
        """Set the preferred file for a version.
        
        Args:
            version: Version dict to update.
            preferredFile: Relative path to the preferred file within the version folder.
            callback: Optional callback function to execute after setting.
        """
        if "path" not in version:
            return

        infoPath = self.core.getVersioninfoPath(version["path"])
        logger.debug("setting preferredFile: %s - %s" % (version["path"], preferredFile))
        self.core.setConfig("preferredFile", val=preferredFile, configPath=infoPath)
        if callback:
            callback()

    @err_catcher(name=__name__)
    def getLocationFromPath(self, path: str) -> Optional[str]:
        """Determine the storage location that contains a given path.
        
        Similar to getLocationFromFilepath. Returns the most specific matching location.
        
        Args:
            path: Filesystem path to check.
            
        Returns:
            Optional[str]: Storage location identifier, or None if not found.
        """
        locDict = self.core.paths.getExportProductBasePaths()
        nPath = os.path.normpath(path)
        validLocs = []
        for location in locDict:
            if nPath.startswith(locDict[location]):
                validLocs.append(location)

        if not validLocs:
            return

        validLocs = sorted(validLocs, key=lambda x: len(locDict[x]), reverse=True)
        return validLocs[0]

    @err_catcher(name=__name__)
    def getProductVersion(self, product: str, version: str, entity: Optional[Dict[str, Any]] = None, wedge: Optional[str] = None, locations: Optional[Union[str, List[str]]] = None, includeMaster: bool = True) -> Optional[Dict[str, Any]]:
        """Get a specific version of a product.
        
        Args:
            product: Product name.
            version: Version string ('v0001', 'latest', or 'master').
            entity: Optional entity dict. Uses current file's entity if None.
            wedge: Optional wedge identifier.
            locations: Optional storage locations to search.
            includeMaster: Whether to include master when version is 'latest'. Defaults to True.
            
        Returns:
            Optional[Dict[str, Any]]: Version dict for the specified version.
        """
        if not entity:
            fname = self.core.getCurrentFileName()
            entity = self.core.getScenefileData(fname)
            if entity.get("type") not in ["asset", "shot"]:
                return

        versionData = None
        versions = self.getVersionsFromProduct(entity, product, locations=locations)
        if version == "latest":
            versionData = self.getLatestVersionFromVersions(
                versions, includeMaster=includeMaster, wedge=wedge
            )
        else:
            for v in versions:
                if v["version"] == version:
                    if wedge is None or wedge == v.get("wedge"):
                        versionData = v
                        break

        return versionData

    @err_catcher(name=__name__)
    def getVersionpathFromProductVersion(self, product: str, version: str, entity: Optional[Dict[str, Any]] = None, wedge: Optional[str] = None, locations: Optional[Union[str, List[str]]] = None) -> Optional[str]:
        """Get the file path for a specific version of a product.
        
        Args:
            product: Product name.
            version: Version string ('v0001', 'latest', or 'master').
            entity: Optional entity dict. Uses current file's entity if None.
            wedge: Optional wedge identifier.
            locations: Optional storage locations to search.
            
        Returns:
            Optional[str]: File path to the preferred file of the specified version.
        """
        versionData = self.getProductVersion(product, version, entity=entity, wedge=wedge, locations=locations)
        if not versionData:
            return

        filepath = self.getPreferredFileFromVersion(versionData)
        return filepath

    @err_catcher(name=__name__)
    def generateProductPath(
        self,
        entity: Dict[str, Any],
        task: str,
        extension: Optional[str] = None,
        startframe: Optional[int] = None,
        endframe: Optional[int] = None,
        comment: Optional[str] = None,
        user: Optional[str] = None,
        version: Optional[str] = None,
        framePadding: Optional[str] = None,
        location: str = "global",
        returnDetails: bool = False,
        wedge: Optional[str] = None
    ) -> Union[str, Dict[str, Any]]:
        """Generate a product file path based on entity and version parameters.
        
        Constructs a complete file path for a product export based on the project
        structure template and provided parameters.
        
        Args:
            entity: Entity dict containing type and entity information.
            task: Product/task name.
            extension: File extension (e.g., '.abc', '.fbx'). Defaults to None.
            startframe: Start frame number. Defaults to None.
            endframe: End frame number. Defaults to None.
            comment: Version comment. Defaults to empty string.
            user: Username for the version. Defaults to current user.
            version: Version string. Auto-generates next available if None.
            framePadding: Frame padding string (e.g., '####'). Auto-determined if None.
            location: Storage location ('global', 'local', etc.). Defaults to 'global'.
            returnDetails: If True, returns full context dict; if False, returns path string.
            wedge: Optional wedge identifier. Defaults to None.
            
        Returns:
            Union[str, Dict[str, Any]]: Generated file path or context dict with path.
        """
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

        if entity.get("type") == "asset":
            key = "productFilesAssets"
        elif entity.get("type") == "shot":
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
    def getNextAvailableVersion(self, entity: Dict[str, Any], product: str) -> str:
        """Get the next available version number for a product.
        
        Determines the next version number based on existing versions or the current
        scene file version, depending on settings.
        
        Args:
            entity: Entity dict containing type and entity information.
            product: Product name.
            
        Returns:
            str: Next available version string (e.g., 'v0001').
        """
        if (not self.core.separateOutputVersionStack) and self.core.appPlugin.pluginName != "Standalone":
            fileName = self.core.getCurrentFileName()
            fnameData = self.core.getScenefileData(fileName)
            if fnameData.get("type") in ["asset", "shot"] and "version" in fnameData:
                hVersion = fnameData["version"]
            else:
                hVersion = self.core.versionFormat % self.core.lowestVersion

            return hVersion

        versions = self.getVersionsFromProduct(entity, product)
        latest = self.getLatestVersionFromVersions(versions, includeMaster=False)
        if latest:
            latestNum = self.getIntVersionFromVersionName(latest.get("version", ""))
            if latestNum is not None:
                num = latestNum + 1
                version = self.core.versionFormat % num
            else:
                version = self.core.versionFormat % self.core.lowestVersion
        else:
            version = self.core.versionFormat % self.core.lowestVersion

        return version

    @err_catcher(name=__name__)
    def getVersionInfoPathFromProductFilepath(self, filepath: str) -> str:
        """Get the directory path containing version info for a product file.
        
        Args:
            filepath: Path to a product file.
            
        Returns:
            str: Directory path containing the versioninfo file.
        """
        return os.path.dirname(filepath)

    @err_catcher(name=__name__)
    def setComment(self, versionPath: str, comment: str) -> None:
        """Set the comment for a product version.
        
        Args:
            versionPath: Path to the version folder.
            comment: Comment text to set.
        """
        infoPath = self.core.getVersioninfoPath(versionPath)
        versionInfo = {}
        if os.path.exists(infoPath):
            versionInfo = self.core.getConfig(configPath=infoPath) or {}

        versionInfo["comment"] = comment
        self.core.setConfig(data=versionInfo, configPath=infoPath)

    @err_catcher(name=__name__)
    def updateMasterVersion(self, path: str) -> Optional[str]:
        """Update the master version to point to a specific version.
        
        Copies or links files from a numbered version to the master version folder,
        making it the current master.
        
        Args:
            path: Path to the version that should become the new master.
            
        Returns:
            Optional[str]: Path to the updated master version, or None if update failed.
        """
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
            logger.debug("no files exists for sequence: %s" % path)
            return

        useHL = os.getenv("PRISM_USE_HARDLINK_MASTER", None)
        for seqFile in seqFiles:
            if len(seqFiles) > 1:
                extData = self.core.paths.splitext(seqFile)
                base = extData[0]
                if self.core.framePadding == 4 and len(base) > 8 and base[-4] == "." and base[-3:].isnumeric() and base[-8:-4].isnumeric() and base[-9] != "v":
                    frameStr = "." + base[-8:]
                else:
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
                while True:
                    try:
                        shutil.copy2(seqFile, masterPathPadded)
                    except Exception as e:
                        logger.warning(e)
                        msg = "Couldn't copy file to master version:\n\nError: %s\n\nSource Path: %s\n\nTarget Path: %s" % (str(e), seqFile, masterPathPadded)
                        result = self.core.popupQuestion(
                            msg,
                            buttons=["Retry", "Skip file"],
                            escapeButton="Skip file",
                            default="Skip file",
                        )
                        if result == "Retry":
                            continue

                    break

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
                masterInfoDir = os.path.dirname(masterInfoPath)
                if not os.path.exists(masterInfoDir):
                    try:
                        os.makedirs(masterInfoDir, exist_ok=True)
                    except Exception as e:
                        logger.warning("Failed to create master info directory: %s - %s" % (masterInfoDir, e))

                if os.path.exists(masterInfoDir):
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
    def renameMaster(self, masterFolder: str) -> Optional[bool]:
        """Rename a master folder to a .delete subfolder.
        
        Used when a master version needs to be archived before being replaced.
        
        Args:
            masterFolder: Path to the master version folder to rename.
            
        Returns:
            Optional[bool]: True if rename succeeded, None otherwise.
        """
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
    def deleteMasterVersion(self, path: str, errorMsg: Optional[str] = None, allowClear: bool = True, allowRename: bool = True) -> bool:
        """Delete a master version folder.
        
        Attempts to remove the master version folder, with fallback options to
        rename or clear selections if deletion fails.
        
        Args:
            path: Path to any file in the version stack.
            errorMsg: Optional custom error message template.
            allowClear: Whether to allow clearing UI selections on failure. Defaults to True.
            allowRename: Whether to allow renaming instead of deleting. Defaults to True.
            
        Returns:
            bool: True if deletion succeeded or user chose to skip deletion.
        """
        context = self.getVersionStackContextFromPath(path)
        context["version"] = "master"
        key = "productVersions"
        if "wedge" not in context:
            context["wedge"] = ""

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
    def getMasterVersionNumber(self, masterPath: str, allowCache: bool = True) -> Optional[str]:
        """Get the source version number that the master version points to.
        
        Args:
            masterPath: Path to the master version folder.
            allowCache: Whether to use cached data. Defaults to True.
            
        Returns:
            Optional[str]: Source version number (e.g., 'v0005'), or None if not found.
        """
        versionData = self.core.paths.getCachePathData(masterPath, addPathData=False, validateModTime=True, allowCache=allowCache)
        if "sourceVersion" in versionData:
            return versionData["sourceVersion"]

        if "version" in versionData:
            return versionData["version"]

    @err_catcher(name=__name__)
    def getMasterVersionLabel(self, path: str) -> str:
        """Get a display label for a master version showing its source version.
        
        Args:
            path: Path to the master version.
            
        Returns:
            str: Label like 'master (v0005)' or just 'master'.
        """
        versionName = "master"
        versionData = self.core.paths.getCachePathData(path, addPathData=False, validateModTime=True)
        if "sourceVersion" in versionData:
            versionName = "master (%s)" % versionData["sourceVersion"]
        elif "version" in versionData:
            versionName = "master (%s)" % versionData["version"]

        return versionName

    @err_catcher(name=__name__)
    def createProduct(self, entity: Dict[str, Any], product: str, location: str = "global") -> Optional[str]:
        """Create a new product folder for an entity.
        
        Args:
            entity: Entity dict containing type and entity information.
            product: Product name to create.
            location: Storage location where product should be created. Defaults to 'global'.
            
        Returns:
            Optional[str]: Path to the created product folder, or None if creation failed.
        """
        context = entity.copy()
        context["product"] = product
        basePath = self.core.paths.getExportProductBasePaths()[location]
        context["project_path"] = basePath

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
    def getPreferredFileFromFiles(self, files: List[str], relative: bool = False) -> Optional[str]:
        """Select a preferred file from a list of files.
        
        Prefers regular files over directories, and if only directories exist,
        finds the first file within them.
        
        Args:
            files: List of file/folder paths to choose from.
            relative: If True, returns relative path; if False, returns absolute. Defaults to False.
            
        Returns:
            Optional[str]: Path to the preferred file, or None if no files found.
        """
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
    def ingestProductVersion(self, files: List[str], entity: Dict[str, Any], product: str, comment: Optional[str] = None, version: Optional[str] = None, location: str = "global") -> Dict[str, Any]:
        """Ingest external files as a new product version.
        
        Copies files into the project structure as a new version of a product,
        creating version info and setting up the preferred file.
        
        Args:
            files: List of file/folder paths to ingest.
            entity: Entity dict to ingest product for.
            product: Product name.
            comment: Optional version comment. Auto-generated if None.
            version: Optional version number. Auto-generated if None.
            location: Storage location. Defaults to 'global'.
            
        Returns:
            Dict[str, Any]: Dict with 'createdFiles' list and 'versionPath' string.
        """
        if comment is None:
            if len(files) > 1:
                comment = "ingested files"
            elif files:
                comment = "ingested file: %s" % os.path.basename(files[0])
            else:
                comment = ""
    
        kwargs = {
            "entity": entity,
            "task": product,
            "comment": comment,
            "user": self.core.user,
        }
        basePath = self.core.paths.getExportProductBasePaths()[location]
        kwargs["entity"]["project_path"] = basePath
        if version is None:
            version = self.getNextAvailableVersion(entity=entity, product=product)

        kwargs["version"] = version
        prefFile = self.getPreferredFileFromFiles(files, relative=True)
        createdFiles = []
        targetPath = self.generateProductPath(**kwargs)
        versionPath = os.path.dirname(targetPath)
        for file in files:
            fileTargetPath = os.path.join(versionPath, os.path.basename(file))
            if not os.path.exists(versionPath):
                try:
                    os.makedirs(versionPath)
                except:
                    self.core.popup("The directory could not be created")
                    return

            fileTargetPath = fileTargetPath.replace("\\", "/")
            self.copyThread = self.core.copyWithProgress(file, fileTargetPath, popup=False, start=False)

            isFolder = os.path.isdir(file)
            if isFolder:
                msg = "Copying folder - please wait...    "
            else:
                msg = "Copying file - please wait...    "

            self.copyMsg = self.core.waitPopup(self.core, msg)
            self.copyMsg.baseTxt = msg

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
        if prefFile:
            details["extension"] = os.path.splitext(prefFile)[1]
            details["preferredFile"] = prefFile

        infoPath = self.getVersionInfoPathFromProductFilepath(targetPath)
        self.core.saveVersionInfo(filepath=infoPath, details=details)

        return {"createdFiles": createdFiles, "versionPath": versionPath}

    @err_catcher(name=__name__)
    def getUseMaster(self) -> bool:
        """Check if master version usage is enabled for the project.
        
        Returns:
            bool: True if master versions are enabled in project settings.
        """
        return self.core.getConfig(
            "globals", "useMasterVersion", dft=True, config="project"
        )

    @err_catcher(name=__name__)
    def getLinkedToTasks(self) -> Optional[bool]:
        """Check if products are organized by tasks/departments.
        
        Returns:
            Optional[bool]: True if products are linked to tasks, False/None otherwise.
        """
        return self.core.getConfig("globals", "productTasks", config="project")

    @err_catcher(name=__name__)
    def checkMasterVersions(self, entities: List[Dict[str, Any]], parent: Optional[QWidget] = None) -> None:
        """Check if master versions are outdated for given entities.
        
        Opens a dialog showing which master versions need updating.
        
        Args:
            entities: List of entity dicts to check.
            parent: Optional parent widget for the dialog.
        """
        self.dlg_masterManager = self.core.paths.masterManager(self.core, entities, "products", parent=parent)
        self.dlg_masterManager.refreshData()
        if not self.dlg_masterManager.outdatedVersions:
            msg = "All master versions of the selected entities are up to date."
            self.core.popup(msg, severity="info")
            return

        self.dlg_masterManager.show()

    @err_catcher(name=__name__)
    def getOutdatedMasterVersions(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find all outdated master versions for given entities.
        
        Compares master versions with the latest numbered versions to identify
        which masters need updating.
        
        Args:
            entities: List of entity dicts to check.
            
        Returns:
            List[Dict[str, Any]]: List of dicts with 'master' and 'latest' version info.
        """
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
    def getGroupFromProduct(self, product: Dict[str, Any]) -> Optional[str]:
        """Get the group assigned to a product.
        
        Args:
            product: Product dict.
            
        Returns:
            Optional[str]: Group name, or None if no group assigned.
        """
        productPath = self.getProductPathFromEntity(product, includeProduct=False)
        cfgPath = os.path.join(productPath, "products" + self.core.configs.getProjectExtension())
        group = self.core.getConfig(product.get("product"), "group", configPath=cfgPath)
        return group

    @err_catcher(name=__name__)
    def setProductsGroup(self, products: List[Dict[str, Any]], group: str, projectWide: bool = False) -> None:
        """Set the group for multiple products.
        
        Args:
            products: List of product dicts to update.
            group: Group name to assign.
            projectWide: Whether to apply project-wide. Currently unused.
        """
        productPath = self.getProductPathFromEntity(products[0], includeProduct=False)
        cfgPath = os.path.join(productPath, "products" + self.core.configs.getProjectExtension())
        data = self.core.getConfig(configPath=cfgPath) or {}
        for product in products:
            if product.get("product") not in data:
                data[product.get("product")] = {}

            data[product.get("product")]["group"] = group

        self.core.setConfig(data=data, configPath=cfgPath)

    @err_catcher(name=__name__)
    def getTagsFromProduct(self, product: Dict[str, Any]) -> List[str]:
        """Get tags assigned to a product.
        
        Falls back to project-wide tags if no entity-specific tags are set.
        
        Args:
            product: Product dict.
            
        Returns:
            List[str]: List of tag strings.
        """
        productPath = self.getProductPathFromEntity(product, includeProduct=False)
        cfgPath = os.path.join(productPath, "products" + self.core.configs.getProjectExtension())
        tags = self.core.getConfig(product.get("product"), "tags", configPath=cfgPath)
        if tags is None:
            tags = []
            prjTags = self.getProjectTagsFromProduct(product["product"])
            for prjTag in prjTags:
                if prjTag not in tags:
                    tags.append(prjTag)

        return tags

    @err_catcher(name=__name__)
    def getDefaultProjectProductTags(self) -> Dict[str, List[str]]:
        """Get the default product tags for different departments.
        
        Returns:
            Dict[str, List[str]]: Dict mapping department names to their default tag lists.
        """
        tags = {
            "Modeling": ["to_surf"],
            "Surfacing": ["to_rig, static"],
            "Rigging": ["to_anm"],
            "Animation": ["animated"],
        }
        return tags
    
    @err_catcher(name=__name__)
    def getProjectTagsFromProduct(self, product: str) -> List[str]:
        """Get project-wide tags for a specific product name.
        
        Args:
            product: Product name.
            
        Returns:
            List[str]: List of project tag strings for this product.
        """
        tagData = self.getProjectProductTags() or {}
        if product not in list(tagData.keys()):
            return []

        tags = tagData[product] or []
        return tags

    @err_catcher(name=__name__)
    def getProjectProductTags(self) -> Dict[str, List[str]]:
        """Get all project-wide product tags.
        
        Returns:
            Dict[str, List[str]]: Dict mapping product names to tag lists.
        """
        tagData = self.core.getConfig("products", "tags", config="project")
        if tagData is None:
            tagData = self.getDefaultProjectProductTags()

        return tagData

    @err_catcher(name=__name__)
    def setProjectProductTags(self, tags: Dict[str, List[str]]) -> None:
        """Set project-wide product tags.
        
        Args:
            tags: Dict mapping product names to tag lists.
        """
        self.core.setConfig("products", "tags", val=tags, config="project")

    @err_catcher(name=__name__)
    def setProductTags(self, product: Dict[str, Any], tags: List[str]) -> None:
        """Set tags for a specific product.
        
        Args:
            product: Product dict.
            tags: List of tag strings to assign.
        """
        productPath = self.getProductPathFromEntity(product, includeProduct=False)
        cfgPath = os.path.join(productPath, "products" + self.core.configs.getProjectExtension())
        self.core.setConfig(product.get("product"), "tags", val=tags, configPath=cfgPath)

    @err_catcher(name=__name__)
    def getProductsByTags(self, entity: Dict[str, Any], tags: List[str]) -> List[Dict[str, Any]]:
        """Find all products for an entity that have any of the specified tags.
        
        Args:
            entity: Entity dict to search products in.
            tags: List of tag strings to search for.
            
        Returns:
            List[Dict[str, Any]]: List of product dicts matching any of the tags.
        """
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

    @err_catcher(name=__name__)
    def getRecommendedTags(self, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Get a list of recommended product tags based on project setup.
        
        Generates tags from department abbreviations, task names, and common tags.
        
        Args:
            context: Context dict (currently unused but available for filtering).
            
        Returns:
            List[str]: List of recommended tag strings (deduplicated).
        """
        tags = []
        departments = self.core.projects.getAssetDepartments()
        departments += self.core.projects.getShotDepartments()
        for department in departments:
            depTag = "to_" + department.get("abbreviation", "").lower()
            tags.append(depTag)

            for defaultTask in department.get("defaultTasks", []):
                taskTag = "to_" + defaultTask.lower()
                tags.append(taskTag)

        tags += ["main", "static", "animated"]
        tags += getattr(self, "extraTags", [])
        newTags = []
        for tag in tags:
            if tag not in newTags:
                newTags.append(tag)

        return newTags

    @err_catcher(name=__name__)
    def importConnectedAssetsForEntities(self, entities: Optional[List[Dict[str, Any]]] = None, parent: Optional[QWidget] = None, includeMaster: bool = True) -> None:
        """Import connected assets for multiple entities.
        
        Args:
            entities: List of entity dicts to import assets for.
            parent: Optional parent widget.
            includeMaster: Whether to include master versions. Defaults to True.
        """
        for entity in entities:
            self.importConnectedAssets(entity, includeMaster=includeMaster)

    @err_catcher(name=__name__)
    def importConnectedAssets(self, entity: Optional[Dict[str, Any]] = None, quiet: bool = True, quietCheck: bool = False, includeMaster: bool = True, settings: Optional[Dict[str, Any]] = None) -> None:
        """Import products from assets connected to a shot.
        
        Automatically imports products tagged for the current department/task
        from all assets connected to the shot.
        
        Args:
            entity: Optional entity dict. Uses current scenefile entity if None.
            quiet: Whether to suppress import dialogs. Defaults to True.
            quietCheck: Whether to suppress "no products" messages. Defaults to False.
            includeMaster: Whether to include master versions. Defaults to True.
            settings: Optional import settings dict.
        """
        logger.debug("importing connected assets")
        sm = self.core.getStateManager()
        if not sm:
            return

        if not entity:
            filepath = self.core.getCurrentFileName()
            entity = self.core.getScenefileData(filepath)

        if not entity or entity.get("type") != "shot":
            msg = "Importing connected assets is possible in shot scenefiles only."
            logger.debug(msg)
            if not quietCheck:
                self.core.popup(msg)

            return

        productsToImport = []
        entities = self.core.entities.getConnectedEntities(entity)
        if not entities:
            msg = "No assets are connected to the current shot."
            logger.debug(msg)
            if not quietCheck:
                result = self.core.popupQuestion(msg, buttons=["Connect Assets...", "Close"], icon=QMessageBox.Information)
                if result == "Connect Assets...":
                    self.core.entities.connectEntityDlg(entities=[entity])

            return

        tags = [x.strip() for x in os.getenv("PRISM_AUTO_IMPORT_TAGS", "").split(",") if x]
        if not tags:
            tags = ["main"]

        curDep = entity.get("department")
        if curDep:
            tags.insert(0, "to_%s" % curDep.lower())

        task = entity.get("task")
        if task:
            tags.insert(0, "to_%s" % task.lower())

        newTags = []
        for tag in tags:
            if tag not in newTags:
                newTags.append(tag)

        tags = newTags

        for centity in entities:
            products = self.core.products.getProductsByTags(centity, tags)
            productsToImport += products

        if not productsToImport:
            msg = "No products to import.\n(checking for tags: \"%s\")" % "\", \"".join(tags)
            logger.debug(msg)
            if not quietCheck:
                self.core.popup(msg)

            return

        settings = settings or{}
        if quiet:
            settings["quiet"] = True

        importedProducts = []
        for product in productsToImport:
            if "asset_path" not in product:
                continue

            productPath = self.core.products.getLatestVersionpathFromProduct(product["product"], entity=product, includeMaster=includeMaster)
            if not productPath:
                continue

            sm.importFile(productPath, settings=settings)
            logger.debug("added product to shot: %s - %s" % (self.core.entities.getShotName(entity), productPath))
            importedProducts.append(productPath)

        if not importedProducts:
            logger.debug("no products to import (%s)" % productsToImport)

    @err_catcher(name=__name__)
    def importProductsForTask(self, entity: Optional[Dict[str, Any]] = None, department: Optional[str] = None, task: Optional[str] = None, quiet: bool = True, quietCheck: bool = False, settings: Optional[Dict[str, Any]] = None, includeMaster: bool = True) -> None:
        """Import products for a specific department and task.
        
        Imports products tagged for the specified department/task combination.
        
        Args:
            entity: Optional entity dict. Uses current scenefile entity if None.
            department: Department name to import for.
            task: Task name to import for.
            quiet: Whether to suppress import dialogs. Defaults to True.
            quietCheck: Whether to suppress "no products" messages. Defaults to False.
            settings: Optional import settings dict.
            includeMaster: Whether to include master versions. Defaults to True.
        """
        logger.debug("importing products for entity %s for department %s" % (entity, department))
        sm = self.core.getStateManager()
        if not sm:
            return

        if not entity:
            filepath = self.core.getCurrentFileName()
            entity = self.core.getScenefileData(filepath)

        productsToImport = []
        tags = [x.strip() for x in os.getenv("PRISM_AUTO_IMPORT_TAGS", "").split(",") if x]
        if not tags:
            tags = ["main"]

        tags.insert(0, "to_%s" % department.lower())
        tags.insert(0, "to_%s" % task.lower())

        newTags = []
        for tag in tags:
            if tag not in newTags:
                newTags.append(tag)

        tags = newTags

        productsToImport = self.core.products.getProductsByTags(entity, tags)
        if not productsToImport:
            msg = "No products to import.\n(checking for tags: \"%s\")" % "\", \"".join(tags)
            logger.debug(msg)
            if not quietCheck:
                self.core.popup(msg)

            return

        settings = settings or {}
        if quiet:
            settings["quiet"] = True

        if self.core.appPlugin.pluginName == "Maya":
            settings["useNamespace"] = bool(settings.get("namespace"))

        importedProducts = []
        for product in productsToImport:
            productPath = self.core.products.getLatestVersionpathFromProduct(product["product"], entity=product, includeMaster=includeMaster)
            if not productPath:
                continue

            sm.importFile(productPath, settings=settings)
            logger.debug("imported product: %s - %s" % (self.core.entities.getEntityName(entity), productPath))
            importedProducts.append(productPath)

        if not importedProducts:
            logger.debug("no products to import (%s)" % productsToImport)


class PreferredVersionDialog(QDialog):
    """Dialog for selecting the preferred file from a product version.
    
    Displays the file structure of a version folder and allows users to
    select which file should be the default for imports.
    
    Signals:
        signalSelected: Emitted when user selects a file. Args: (version dict, relative file path).
    
    Attributes:
        origin: Products instance that created this dialog.
        core: PrismCore instance.
        version: Version dict being edited.
        projectStructure: Folder structure dict of the version.
    """

    signalSelected = Signal(object, object)

    def __init__(self, origin: 'Products', version: Dict[str, Any], parent: Optional[QWidget] = None) -> None:
        """Initialize the PreferredVersionDialog.
        
        Args:
            origin: Products instance.
            version: Version dict to select preferred file for.
            parent: Optional parent widget for the dialog.
        """
        super(PreferredVersionDialog, self).__init__()
        self.origin = origin
        self.core = self.origin.core
        self.core.parentWindow(self, parent=parent)
        self.version = version
        self.setupUi()
        self.refreshTree()

    @err_catcher(name=__name__)
    def sizeHint(self) -> QSize:
        """Get the preferred size for the dialog.
        
        Returns:
            QSize: Preferred dialog size.
        """
        return QSize(350, 400)

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Set up the user interface for the dialog."""
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
    def refreshTree(self) -> None:
        """Refresh the file tree display and select the current preferred file."""
        self.projectStructure = self.core.projects.getFolderStructureFromPath(self.version["path"])
        self.projectStructure["name"] = os.path.basename(self.version["path"])
        self.tw_files.clear()
        self.addItemToTree(self.projectStructure)
        file = self.origin.getPreferredFileFromVersion(self.version)
        if file:
            file = file.replace(self.version["path"], "")
            self.navigate(file)

    @err_catcher(name=__name__)
    def addItemToTree(self, entity: Dict[str, Any], parent: Optional[QTreeWidgetItem] = None) -> QTreeWidgetItem:
        """Recursively add a file/folder to the tree widget.
        
        Args:
            entity: Dict representing a file or folder with 'name' and optional 'children'.
            parent: Optional parent tree item. Adds to root if None.
            
        Returns:
            QTreeWidgetItem: The created tree item.
        """
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
    def navigate(self, file: str) -> None:
        """Navigate to and select a file in the tree.
        
        Args:
            file: Relative path to the file within the version folder.
        """
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
    def onAcceptClicked(self) -> None:
        """Handle when user clicks OK button.
        
        Validates selection and emits the signalSelected signal.
        """
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
