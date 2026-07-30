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
import copy
import datetime
import fnmatch
from typing import Any, Optional, List, Dict, Tuple, Union

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class MediaProducts(object):
    """Manages media product creation and import in the Prism pipeline.
    
    Attributes:
        core: Reference to the Prism core instance.
    """
    
    def __init__(self, core: Any) -> None:
        """Initialize the MediaProducts manager.
        
        Args:
            core: Reference to the Prism core instance.
        """
        self.core = core

    @err_catcher(name=__name__)
    def createExternalMedia(self, filepath: str, entity: Dict, identifier: str, version: str, action: str = "copy", location: str = "global") -> Optional[str]:
        """Create external media product from external files.
        
        Imports external media files into the project structure. Can copy, move, or
        create redirect links to the original files.
        
        Args:
            filepath: Path(s) to external file(s). Multiple paths separated by os.pathsep.
            entity: Entity dict containing type ('asset' or 'shot') and other entity data.
            identifier: Product identifier name.
            version: Version string for the media.
            action: Import action - 'copy', 'move', or 'link'. Defaults to 'copy'.
            location: Storage location - 'global' or custom location. Defaults to 'global'.
            
        Returns:
            Optional[str]: Path to created media folder, or None if creation fails.
        """
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

        basePath = self.core.paths.getRenderProductBasePaths()[location]
        context["project_path"] = basePath

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
    def getExternalPathFromVersion(self, version: Dict) -> str:
        """Get the original external path from a media version.
        
        Reads the REDIRECT.txt file if present to find the original external media location.
        
        Args:
            version: Version dict containing type, identifier, and other version data.
            
        Returns:
            str: Original external file path, or empty string if not found.
        """
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
    def getDisplayNameForIdentifier(self, identifier: str, mediaType: str) -> str:
        """Generate display name for an identifier based on media type.
        
        Args:
            identifier: Base identifier name.
            mediaType: Type of media ('2drenders', 'playblasts', 'externalMedia', etc.).
            
        Returns:
            str: Display name with type suffix in parentheses.
        """
        display = identifier
        if mediaType == "2drenders":
            display += " (2d)"
        elif mediaType == "playblasts":
            display += " (playblast)"
        elif mediaType == "externalMedia":
            display += " (external)"

        return display

    @err_catcher(name=__name__)
    def getIdentifiersByType(self, entity: Dict, locations: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
        """Get all media identifiers for an entity, grouped by type.
        
        Args:
            entity: Entity dict containing type and other entity data.
            locations: Optional list of storage locations to search. Searches all if None.
            
        Returns:
            Dict[str, List[Dict]]: Dict with keys '3d', '2d', 'playblast', 'external', 
                each containing a list of identifier dicts.
        """
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
                    if "identifier" not in data:
                        continue

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
    def getIdentifierNames(self, entity: Dict) -> List[str]:
        """Get list of all identifier display names for an entity.
        
        Args:
            entity: Entity dict containing type and other entity data.
            
        Returns:
            List[str]: List of display names for all identifiers.
        """
        names = []
        idfs = self.getIdentifiersByType(entity)
        for mtype in idfs:
            for idf in idfs[mtype]:
                names.append(idf["displayName"])

        return names

    @err_catcher(name=__name__)
    def getIdentifiersFromEntity(self, entity: Dict) -> List[Dict]:
        """Get all media identifiers from an entity.
        
        Args:
            entity: Entity dict containing type and other entity data.
            
        Returns:
            List[Dict]: List of all identifier dicts across all media types.
        """
        entityIdfs = []
        idfs = self.getIdentifiersByType(entity)
        for mtype in idfs:
            for idf in idfs[mtype]:
                entityIdfs.append(idf)

        return entityIdfs

    @err_catcher(name=__name__)
    def getIdentifierPathFromEntity(self, entity: Dict) -> str:
        """Get the base path for identifiers from an entity.
        
        Args:
            entity: Entity dict containing type and other entity data.
            
        Returns:
            str: Path to the identifier directory.
        """
        key = "3drenders"
        context = entity.copy()
        template = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )
        path = os.path.dirname(template)
        return path

    @err_catcher(name=__name__)
    def getVersionPathFromIdentifier(self, entity: Dict) -> str:
        """Get the base path for versions from an identifier entity.
        
        Args:
            entity: Entity dict with identifier data.
            
        Returns:
            str: Path to the version directory.
        """
        key = "renderVersions"
        context = entity.copy()
        template = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )
        path = os.path.dirname(template)
        return path

    @err_catcher(name=__name__)
    def getVersionsFromIdentifier(self, identifier: Dict[str, Any], locations: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get all versions matching the given identifier.
        
        Searches render product locations for versions matching the identifier context.
        
        Args:
            identifier: Context dict with entity, department, task, etc.
            locations: List of location keys to search (default: search all)
            
        Returns:
            List of version dicts with path and metadata
        """
        if not identifier:
            return

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

        return versions

    @err_catcher(name=__name__)
    def getVersionStackContextFromPath(self, filepath: str, mediaType: Optional[str] = None) -> Dict:
        """Get context dict for a version stack from a file path.
        
        Extracts entity and identifier information from path, removing version-specific fields.
        
        Args:
            filepath: Path to a media file or folder.
            mediaType: Optional media type hint.
            
        Returns:
            Dict: Context dict suitable for finding other versions in the same stack.
        """
        context = self.core.paths.getRenderProductData(filepath, mediaType=mediaType)

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
    def getVersionsFromSameVersionStack(self, path: str, mediaType: Optional[str] = None) -> List[Dict]:
        """Get all versions that belong to the same version stack as the given path.
        
        Args:
            path: Path to a media file or folder.
            mediaType: Optional media type hint.
            
        Returns:
            List[Dict]: List of version dicts from the same version stack.
        """
        context = self.getVersionStackContextFromPath(path, mediaType=mediaType)
        if not context:
            return []

        versionData = self.getVersionsFromContext(context)
        return versionData

    @err_catcher(name=__name__)
    def getVersion(self, entity: Dict, identifier: str, mediaType: Optional[str] = None, 
                   version: Optional[str] = None) -> Optional[Dict]:
        """Get a specific version from an entity and identifier.
        
        Args:
            entity: Entity dict containing type and other entity data.
            identifier: Product identifier name.
            mediaType: Type of media ('3drenders', '2drenders', 'playblasts'). Defaults to '3drenders'.
            version: Version string, or 'latest' for newest version. Defaults to 'latest'.
            
        Returns:
            Optional[Dict]: Version dict, or None if not found.
        """
        mediaType = mediaType or "3drenders"
        version = version or "latest"
        idf = entity.copy()
        idf["identifier"] = identifier
        idf["mediaType"] = mediaType
        if version == "latest":
            versionData = self.getLatestVersionFromIdentifier(idf)
        else:
            versions = self.getVersionsFromIdentifier(idf)
            versionData = None
            for ver in versions:
                if ver["version"] == version:
                    versionData = ver

        return versionData

    @err_catcher(name=__name__)
    def getFileFromVersion(self, version: Dict, aov: Optional[str] = None, 
                           findExisting: bool = False) -> Optional[str]:
        """Get the file path or pattern from a version dict.
        
        Args:
            version: Version dict containing path and metadata.
            aov: Optional AOV name. If not provided, uses first available AOV for 3D renders.
            findExisting: Whether to find actual existing files instead of pattern.
            
        Returns:
            Optional[str]: File path pattern, or None if version invalid.
        """
        if not version:
            return

        if aov:
            version["aov"] = aov
        else:
            if not version.get("mediaType") or version.get("mediaType") == "3drenders" and "aov" not in version:
                aovs = self.getAOVsFromVersion(version)
                if aovs:
                    version["aov"] = aovs[0]["aov"]

        file = self.getFilePatternFromVersion(version)
        if version.get("locations"):
            file = self.core.convertPath(file, list(version["locations"].keys())[0])

        if findExisting:
            filepaths = self.core.media.getFilesFromSequence(file)
            if not filepaths:
                sources = self.core.media.getImgSources(os.path.dirname(file))
                if sources:
                    if sources[0].endswith("preview.jpg") and len(sources) > 1:
                        file = sources[1]
                    else:
                        file = sources[0]
                else:
                    return

        return file

    @err_catcher(name=__name__)
    def getVersionsFromContext(self, context: Dict[str, Any], keys: Optional[List[str]] = None, locations: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get all versions matching the given context.
        
        Searches structured project paths for versions based on context (entity, task, etc.).
        Can search render or playblast versions depending on mediaType in context.
        
        Args:
            context: Context dict with entity, department, task, mediaType, etc.
            keys: Project structure keys to use (default: renderVersions or playblastVersions)
            locations: List of location keys to search (default: search all)
            
        Returns:
            List of version dicts with path and metadata
        """
        locationData = self.core.paths.getRenderProductBasePaths()
        searchLocations = []
        for locData in locationData:
            if not locations or locData in locations or "all" in locations:
                searchLocations.append(locData)

        if context.get("mediaType") == "playblasts":
            key = "playblastVersions"
        else:
            key = "renderVersions"

        versions = []
        for loc in searchLocations:
            ctx = context.copy()
            ctx["project_path"] = locationData[loc]
            templates = self.core.projects.getResolvedProjectStructurePaths(
                key, context=ctx
            )
            versionData = []
            for template in templates:
                versionData += self.core.projects.getMatchingPaths(template)

            for data in versionData:
                c = self.getDeepCopy(context)
                c.update(data)
                if self.core.products.getIntVersionFromVersionName(c["version"]) is None and c["version"] != "master" and os.getenv("PRISM_SHOW_INVALID_VERSION_NAMES", "0") == "0":
                    continue

                c["paths"] = [data.get("path")]
                c["locations"] = {loc: data.get("path", "")}

                for version in versions:
                    if version.get("version") == c.get("version"):
                        version["paths"].append(c.get("path"))
                        version["locations"].update(c.get("locations"))
                        break
                else:
                    versions.append(c)
                    continue

        return versions

    @err_catcher(name=__name__)
    def isPicklable(self, value: Any) -> bool:
        """Check if a value can be pickled.
        
        Args:
            value: Value to test.
            
        Returns:
            bool: True if the value can be pickled, False otherwise.
        """
        import pickle
        try:
            pickle.dumps(value)
            return True
        except (pickle.PicklingError, TypeError):
            return False

    @err_catcher(name=__name__)
    def getDeepCopy(self, context: Any) -> Any:
        """Create a deep copy of a context dict, skipping unpicklable values.
        
        Args:
            context: Context dict or other value to copy.
            
        Returns:
            Any: Deep copy of the value, with unpicklable items excluded.
        """
        if not isinstance(context, dict):
            return context

        try:
            newDict = copy.deepcopy(context)
        except:
            newDict = {}
            for key, value in context.items():
                if self.isPicklable(value):
                    newDict[key] = self.getDeepCopy(value)
                else:
                    print(f"Warning: Ignoring unpicklable value for key '{key}'")

        return newDict

    @err_catcher(name=__name__)
    def getAovPathFromVersion(self, version: Dict) -> str:
        """Get the directory path for AOVs from a version dict.
        
        Args:
            version: Version dict containing path information.
            
        Returns:
            str: Path to the AOV directory.
        """
        key = "aovs"
        context = version.copy()
        template = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )
        path = os.path.dirname(template)
        return path

    @err_catcher(name=__name__)
    def getAOVsFromVersion(self, version: Dict) -> List[Dict]:
        """Get all AOVs (Arbitrary Output Variables) from a version.
        
        Scans the version directory for available render layers/passes.
        Does not apply to playblasts.
        
        Args:
            version: Version dict containing type, identifier, and version data.
            
        Returns:
            List[Dict]: List of AOV dicts, each containing aov name and path.
        """
        if version.get("mediaType") == "playblasts":
            return []

        key = "aovs"
        ctx = version.copy()
        if "aov" in ctx:
            del ctx["aov"]

        aovData = []
        if version.get("locations"):
            locations = self.core.paths.getRenderProductBasePaths()
            for loc in version["locations"]:
                if loc not in locations:
                    continue

                ctx["project_path"] = locations[loc]
                template = self.core.projects.getResolvedProjectStructurePath(
                    key, context=ctx
                )
                aovData += self.core.projects.getMatchingPaths(template)

        else:
            template = self.core.projects.getResolvedProjectStructurePath(
                key, context=ctx
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
    def getFilesFromContext(self, context: Dict) -> List[str]:
        """Get all media files from a version context.
        
        Resolves file paths from the context, handling redirects and sequences.  
        Supports both local and redirect-based external media.
        
        Args:
            context: Context dict containing version, identifier, and other metadata.
            
        Returns:
            List[str]: List of absolute file paths.
        """
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

        folders = []
        if context.get("locations"):
            locations = self.core.paths.getRenderProductBasePaths()
            for loc in context["locations"]:
                if loc not in locations:
                    continue

                ctx = context.copy()
                ctx["project_path"] = locations[loc]
                template = self.core.projects.getResolvedProjectStructurePath(
                    key, context=ctx
                )
                folders.append(os.path.dirname(template))

        else:
            template = self.core.projects.getResolvedProjectStructurePath(
                key, context=context
            )
            folders = [os.path.dirname(template)]

        filepaths = []
        for folder in folders:
            if not os.path.isdir(folder):
                logger.warning("folder doesn't exist: %s" % folder)
                continue

            if context.get("redirect"):
                base, ext = os.path.splitext(context["redirect"])
                if ext:
                    globPath = context["redirect"].replace("#", "?")
                    files = glob.glob(globPath)
                else:
                    if context.get("source"):
                        globPath = os.path.join(context["redirect"], context["source"].replace("#", "?"))
                        files = glob.glob(globPath)
                    else:
                        for rdroot, rdfolders, rdfiles in os.walk(context["redirect"]):
                            break

                        files = [os.path.join(rdroot, rdf) for rdf in rdfiles]

            elif context.get("source"):
                globPath = os.path.join(glob.escape(folder), context["source"].replace("#", "?"))
                files = glob.glob(globPath)
            else:
                files = []
                for root, folders, files in os.walk(folder):
                    break

            for file in files:
                filepath = os.path.join(folder, file)
                if file == "REDIRECT.txt":
                    with open(filepath, "r") as rfile:
                        rpath = rfile.read()
                        base, ext = os.path.splitext(rpath)
                        if ext:
                            filepaths.append(rpath)
                        else:
                            rdfiles = []
                            for rdroot, rdfolders, rdfiles in os.walk(rpath):
                                break

                            filepaths += [os.path.join(rdroot, rdf) for rdf in rdfiles]

                    context["redirect"] = rpath
                else:
                    filepaths.append(filepath)

        return filepaths

    @err_catcher(name=__name__)
    def getFilePatternFromVersion(self, version: Dict) -> str:
        """Get the filename pattern from a version dict.
        
        Generates a pattern with frame padding (#) for sequences.
        
        Args:
            version: Version dict containing identifier, version, and type data.
            
        Returns:
            str: File path pattern with frame padding.
            
        Raises:
            Exception: If version dict is invalid.
        """
        key = None
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

        if not key:
            raise Exception("Invalid version: %s" % version)

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
    def getMediaVersionInfoPathFromFilepath(self, path: str, mediaType: Optional[str] = None) -> str:
        """Get the version info file path from a media filepath.
        
        Args:
            path: Path to a media file.
            mediaType: Optional media type to determine info file location.
            
        Returns:
            str: Path to the versioninfo config file.
        """
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
    def getPlayblastVersionInfoPathFromFilepath(self, path: str) -> str:
        """Get the version info file path from a playblast filepath.
        
        Args:
            path: Path to a playblast file.
            
        Returns:
            str: Path to the versioninfo config file.
        """
        infoPath = os.path.join(
            os.path.dirname(path), "versioninfo" + self.core.configs.getProjectExtension()
        )
        return infoPath

    @err_catcher(name=__name__)
    def get2dVersionInfoPathFromFilepath(self, path: str) -> str:
        """Get the version info file path from a 2D render filepath.
        
        Args:
            path: Path to a 2D render file.
            
        Returns:
            str: Path to the versioninfo config file.
        """
        infoPath = os.path.join(
            os.path.dirname(path), "versioninfo" + self.core.configs.getProjectExtension()
        )
        return infoPath

    @err_catcher(name=__name__)
    def getVersionInfoPathFromContext(self, context: Dict) -> str:
        """Get the version info file path from a context dict.
        
        Args:
            context: Context dict containing version metadata.
            
        Returns:
            str: Path to the versioninfo config file.
        """
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
    def setComment(self, versionPath: str, comment: str) -> None:
        """Set the comment for a version.
        
        Args:
            versionPath: Path to the version directory.
            comment: Comment text to save.
        """
        infoPath = self.getMediaVersionInfoPathFromFilepath(versionPath)
        infoPath = os.path.join(versionPath, os.path.basename(infoPath))
        mediaInfo = {}
        if os.path.exists(infoPath):
            mediaInfo = self.core.getConfig(configPath=infoPath) or {}

        mediaInfo["comment"] = comment
        self.core.setConfig(data=mediaInfo, configPath=infoPath)

    @err_catcher(name=__name__)
    def getLatestVersionFromVersions(self, versions: List[Dict], includeMaster: bool = True) -> Optional[Dict]:
        """Get the latest version from a list of versions.
        
        Sorts versions by version string. Master versions are treated as newest if included.
        
        Args:
            versions: List of version dicts.
            includeMaster: Whether to include 'master' versions. Defaults to True.
            
        Returns:
            Optional[Dict]: Latest version dict, or None if list is empty.
        """
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
    def getLatestVersionFromIdentifier(self, identifier: Dict, includeMaster: bool = True) -> Optional[Dict]:
        """Get the latest version from an identifier.
        
        Args:
            identifier: Identifier dict containing identifier name and entity data.
            includeMaster: Whether to include 'master' versions. Defaults to True.
            
        Returns:
            Optional[Dict]: Latest version dict, or None if no versions exist.
        """
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
    def getLatestVersionFromFilepath(self, filepath: str, includeMaster: bool = True) -> Optional[Dict]:
        """Get the latest version from the same version stack as a filepath.
        
        Args:
            filepath: Path to a media file.
            includeMaster: Whether to include 'master' versions. Defaults to True.
            
        Returns:
            Optional[Dict]: Latest version dict, or None if filepath invalid.
        """
        data = self.getDataFromFilepath(filepath)
        if not data or len(data.keys()) <= 1:
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
        entity: Dict[str, Any],
        task: str,
        extension: str,
        framePadding: str = "",
        comment: Optional[str] = None,
        version: Optional[str] = None,
        location: str = "global",
        aov: str = "beauty",
        returnDetails: bool = False,
        mediaType: Optional[str] = None,
        singleFrame: bool = False,
        ignoreEmpty: bool = False,
        ignoreFolder: bool = False,
        user: Optional[str] = None,
        additionalContext: Optional[Dict[str, Any]] = None,
        state: Optional[Any] = None,
        filenameTemplate: Optional[str] = None,
    ) -> Union[str, Dict[str, Any]]:
        """Generate output path for a media product (render).
        
        Creates a versioned output path following the project structure template.
        Can generate paths for different AOVs, locations, and media types.
        
        Args:
            entity: Entity dict with type, asset_path/sequence/shot, etc.
            task: Task name (e.g., 'Lighting', 'Compositing')
            extension: File extension (e.g., '.exr', '.jpg')
            framePadding: Frame padding pattern (e.g., '####')
            comment: Optional version comment
            version: Specific version string (default: auto-increment)
            location: Storage location key (default: 'global')
            aov: AOV name (default: 'beauty')
            returnDetails: If True, return context dict instead of string
            mediaType: Media type key (default: auto-detect from extension)
            singleFrame: If True, no frame padding in path
            ignoreEmpty: Skip empty folder checks when determining version
            ignoreFolder: Skip folder existence checks when determining version
            user: Username for version (default: current user)
            additionalContext: Extra context keys to merge
            state: State manager state object
            filenameTemplate: Custom filename template
            
        Returns:
            Output file path string, or context dict if returnDetails=True
        """
        framePadding = framePadding or ""
        comment = comment or ""
        location = location or "global"

        versionUser = user or self.core.user
        basePaths = self.core.paths.getRenderProductBasePaths()
        if location not in basePaths:
            return

        basePath = basePaths[location]
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
        if "layer" not in context:
            context["layer"] = ""

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
            self.core.appPlugin, "sm_render_fixOutputPath", lambda x, y, singleFrame, state: y
        )(self, outputPath, singleFrame=singleFrame, state=state)
        if returnDetails:
            context["path"] = outputPath
            return context
        else:
            return outputPath

    @err_catcher(name=__name__)
    def generatePlayblastPath(
        self,
        entity: Dict[str, Any],
        task: str,
        extension: str,
        framePadding: str = "",
        comment: Optional[str] = None,
        version: Optional[str] = None,
        location: str = "global",
        returnDetails: bool = False,
        user: Optional[str] = None,
        filenameTemplate: Optional[str] = None,
    ) -> Union[str, Dict[str, Any]]:
        """Generate output path for a playblast.
        
        Creates a versioned playblast output path following project structure.
        
        Args:
            entity: Entity dict with type, asset_path/sequence/shot, etc.
            task: Task name
            extension: File extension (e.g., '.mp4', '.mov')
            framePadding: Frame padding pattern (e.g., '####')
            comment: Optional version comment
            version: Specific version string (default: auto-increment)
            location: Storage location key (default: 'global')
            returnDetails: If True, return context dict instead of string
            user: Username for version (default: current user)
            filenameTemplate: Custom filename template
            
        Returns:
            Output file path string, or context dict if returnDetails=True
        """
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
            if "asset" not in context and "asset_path" in context:
                context["asset"] = os.path.dirname(context["asset_path"])

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
    def getHighestMediaVersion(self, context: Dict[str, Any], getExisting: bool = False, ignoreEmpty: bool = False, ignoreFolder: bool = False) -> str:
        """Get highest version number for media product.
        
        Determines the next or highest existing version number based on context.
        Can use scene version or search existing versions on disk.
        
        Args:
            context: Context dict with entity, task, mediaType, etc.
            getExisting: If True, search disk for existing versions
            ignoreEmpty: Skip empty folder checks
            ignoreFolder: Skip folder existence checks
            
        Returns:
            Version string (e.g., 'v0001')
        """
        if not getExisting and not self.core.separateOutputVersionStack and not self.core.appPlugin.pluginName == "Standalone":
            fileName = self.core.getCurrentFileName()
            fnameData = self.core.getScenefileData(fileName)
            if fnameData.get("type") in ["asset", "shot"] and "version" in fnameData:
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
        if "version" in context:
            del context["version"]

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
    def getVersionFromFilepath(self, path: str) -> Optional[str]:
        """Extract version string from a media filepath.
        
        Args:
            path: Path to media file or folder.
            
        Returns:
            Optional[str]: Version string (e.g., 'v0001'), or None if not found.
        """
        data = self.getDataFromFilepath(path)

        if "version" not in data:
            return

        version = data["version"]
        return version

    # @err_catcher(name=__name__)
    # def getDataFromFilepath(self, path):
    #     path = os.path.normpath(path)
    #     entityType = self.core.paths.getEntityTypeFromPath(path)

    #     if entityType == "asset":
    #         key = "renderFilesAssets"
    #     elif entityType == "shot":
    #         key = "renderFilesShots"
    #     else:
    #         return {}

    #     template = self.core.projects.getResolvedProjectStructurePath(key)
    #     data = self.core.projects.extractKeysFromPath(path, template, context={"entityType": entityType})
    #     if not data:
    #         if entityType == "asset":
    #             key = "playblastFilesAssets"
    #         elif entityType == "shot":
    #             key = "playblastFilesShots"

    #         template = self.core.projects.getResolvedProjectStructurePath(key)
    #         data = self.core.projects.extractKeysFromPath(path, template, context={"entityType": entityType})
    #         if data:
    #             data["mediaType"] = "playblasts"

    #     data["type"] = entityType
    #     if "asset_path" in data:
    #         data["asset"] = os.path.basename(data["asset_path"])

    #     return data

    @err_catcher(name=__name__)
    def getDataFromFilepath(self, path: str, isVersionFolder: bool = False) -> Optional[Dict]:
        """Extract all metadata from a media filepath.
        
        Args:
            path: Path to media file or folder.
            isVersionFolder: Whether path points to a version folder.
            
        Returns:
            Optional[Dict]: Dict containing extracted entity, identifier, version, and other data.
        """
        if not path:
            return {}

        path = os.path.normpath(path)
        entityType = self.core.paths.getEntityTypeFromPath(path)
        entity = self.core.paths.getRenderProductData(path) or {}
        isValid = (entity.get("type") == "asset" and entity.get("asset_path")) or (entity.get("type") == "shot" and entity.get("shot"))
        if not isValid:
            entity = self.core.paths.getRenderProductData(path, mediaType="2drenders")
            isValid = (entity.get("type") == "asset" and entity.get("asset_path")) or (entity.get("type") == "shot" and entity.get("shot"))
            if not isValid:
                entity = self.core.paths.getPlayblastProductData(path)
                isValid = (entity.get("type") == "asset" and entity.get("asset_path")) or (entity.get("type") == "shot" and entity.get("shot"))
                if not isValid:
                    entity = self.core.paths.getRenderProductData(path, mediaType="externalMedia")
                    isValid = (entity.get("type") == "asset" and entity.get("asset_path")) or (entity.get("type") == "shot" and entity.get("shot"))
                    if not isValid:
                        if isVersionFolder:
                            entity = {}
                        else:
                            entity = self.getDataFromFilepath(os.path.dirname(path), isVersionFolder=True)
                            isValid = (entity.get("type") == "asset" and entity.get("asset_path")) or (entity.get("type") == "shot" and entity.get("shot"))
                            if not isValid:
                                entity = {}

        if entityType:
            entity["type"] = entityType

        if "asset_path" in entity:
            entity["asset"] = os.path.basename(entity["asset_path"])

        return entity

    @err_catcher(name=__name__)
    def getVersionFromPlayblastFilepath(self, path: str) -> Optional[str]:
        """Extract version string from a playblast filepath.
        
        Args:
            path: Path to playblast file.
            
        Returns:
            Optional[str]: Version string, or None if not found.
        """
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
    def getVersionFromVersionFolder(self, versionFolder: str, context: Optional[Dict] = None) -> Optional[str]:
        """Extract version string from a version folder path.
        
        Args:
            versionFolder: Path to version folder.
            context: Optional context dict with entity information.
            
        Returns:
            Optional[str]: Version string, or None if not found.
        """
        path = os.path.normpath(versionFolder)
        key = "renderVersions"
        context = context or {}

        location = self.getLocationFromPath(versionFolder)
        if location:
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
    def getRenderProductDataFromFilepath(self, filepath: str, mediaType: str = "3drenders") -> Dict:
        """Extract metadata from a render product filepath.
        
        Args:
            filepath: Path to render file.
            mediaType: Type of media. Defaults to '3drenders'.
            
        Returns:
            Dict: Metadata dict with entity, version, identifier, etc.
        """
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
            if data:
                data["mediaType"] = "playblasts"

        data["type"] = entityType
        if "asset_path" in data:
            data["asset"] = os.path.basename(data["asset_path"])

        return data

    @err_catcher(name=__name__)
    def getMediaDataFromVersionFolder(self, path: str, mediaType: str = "3drenders") -> Dict:
        """Extract metadata from a version folder path.
        
        Args:
            path: Path to version folder.
            mediaType: Type of media. Defaults to '3drenders'.
            
        Returns:
            Dict: Metadata dict with entity, version, identifier, etc.
        """
        entityType = self.core.paths.getEntityTypeFromPath(path)
        key = "renderVersions"
        context = {"type": entityType, "entityType": entityType}
        context["mediaType"] = mediaType
        location = self.getLocationFromPath(path)
        if location:
            context["project_path"] = self.core.paths.getRenderProductBasePaths()[location]

        template = self.core.projects.getResolvedProjectStructurePath(key, context=context)
        context = {"entityType": entityType, "project_path": context["project_path"]}
        data = self.core.projects.extractKeysFromPath(path, template, context=context)
        data["type"] = entityType
        if "asset_path" in data:
            data["asset"] = os.path.basename(data["asset_path"])

        return data

    @err_catcher(name=__name__)
    def getLocationFromPath(self, path: str) -> Optional[str]:
        """Get the storage location name from a media path.
        
        Args:
            path: Path to check.
            
        Returns:
            Optional[str]: Location name ('global', 'local', or custom), or None if not found.
        """
        locDict = self.core.paths.getRenderProductBasePaths()
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
    def getVersionPathFromMediaFilePath(self, path: str, mediaType: str, entityType: Optional[str] = None) -> Optional[str]:
        """Get the version folder path from a media file path.
        
        Args:
            path: Path to media file.
            mediaType: Type of media.
            entityType: Optional entity type hint.
            
        Returns:
            Optional[str]: Path to version folder, or None if not found.
        """
        if not entityType:
            entityType = self.core.paths.getEntityTypeFromPath(path)
            if not entityType:
                context = self.core.paths.getMediaProductData(path, mediaType=mediaType)
                entityType = context.get("type")

        key = None
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

        if not key:
            return

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
    def updateMasterVersion(self, path: Optional[str] = None, context: Optional[Dict] = None, isFilepath: bool = True, add: bool = False, mediaType: Optional[str] = None) -> Optional[str]:
        """Update the master version to point to a specific version.
        
        Copies files from the source version to the master version folder.
        
        Args:
            path: Path to source version or file.
            context: Optional context dict with version metadata.
            isFilepath: Whether path is a filepath (vs version folder).
            add: If True, adds to existing master instead of replacing.
            mediaType: Optional media type hint.
            
        Returns:
            Optional[str]: Path to master version folder, or None if update failed.
        """
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

            if not context.get("extension"):
                context["extension"] = os.path.splitext(path)[1]

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

        masterBase = self.getVersionPathFromMediaFilePath(masterPath, mediaType=context.get("mediaType"), entityType=context.get("type"))
        if isFilepath:
            originBase = self.getVersionPathFromMediaFilePath(path, mediaType=context.get("mediaType"), entityType=context.get("type"))
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
                while True:
                    try:
                        os.makedirs(os.path.dirname(masterFile), exist_ok=True)
                    except Exception as e:
                        if e.errno == errno.EEXIST:
                            break

                        logger.warning(e)
                        msg = "Couldn't create master version folder:\n\n%s\n\n%s" % (str(e), os.path.dirname(masterFile))
                        result = self.core.popupQuestion(
                            msg,
                            buttons=["Retry", "Skip"],
                            escapeButton="Skip",
                            default="Skip",
                        )
                        if result == "Retry":
                            continue

                        break

                    break

            useHL = os.getenv("PRISM_USE_HARDLINK_MASTER", None)
            if platform.system() == "Windows" and drive == masterDrive and useHL:
                self.core.createSymlink(masterFile, file)
            else:
                while True:
                    try:
                        shutil.copy2(file, masterFile)
                    except Exception as e:
                        logger.warning(e)
                        msg = "Couldn't copy file to master version:\n\n%s\n\n%s" % (str(e), file)
                        result = self.core.popupQuestion(
                            msg,
                            buttons=["Retry", "Skip file"],
                            escapeButton="Skip file",
                            default="Skip file",
                        )
                        if result == "Retry":
                            continue

                    break

        masterVersions.append(originBase)
        ext = self.core.configs.getProjectExtension()
        masterInfoPath = os.path.join(masterBase, "versioninfo" + ext)
        self.core.setConfig(
            "versionpaths", val=masterVersions, configPath=masterInfoPath
        )
        self.core.media.invalidateOiioCache()
        return masterPath

    @err_catcher(name=__name__)
    def getMasterVersionNumber(self, masterPath: str, allowCache: bool = True) -> Optional[str]:
        """Get the version number that a master version points to.
        
        Args:
            masterPath: Path to master version folder.
            allowCache: Whether to use cached config data.
            
        Returns:
            Optional[str]: Version string, or None if not found.
        """
        versionData = self.core.paths.getRenderProductData(masterPath, validateModTime=True, allowCache=allowCache)
        if "versionpaths" in versionData:
            context = versionData.copy()
            for path in versionData["versionpaths"]:
                vName = self.core.mediaProducts.getVersionFromVersionFolder(
                    path, context=context
                )
                if vName:
                    return vName
        else:
            if "sourceVersion" in versionData:
                return versionData["sourceVersion"]

            if "version" in versionData:
                return versionData["version"]

    @err_catcher(name=__name__)
    def getMasterVersionLabel(self, path: str) -> str:
        """Get a display label for a master version showing source versions.
        
        Args:
            path: Path to master version folder.
            
        Returns:
            str: Display label (e.g., 'master' or 'master (v0003, v0005)').
        """
        versionName = "master"
        versionData = self.core.paths.getRenderProductData(path, validateModTime=True, isVersionFolder=True)
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
    def getMediaTypeFromContext(self, context: Dict) -> str:
        """Determine media type from a context dict.
        
        Args:
            context: Context dict with metadata.
            
        Returns:
            str: Media type string ('3drenders', '2drenders', 'playblasts', or 'externalMedia').
        """
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
    def getMediaTypeFromPath(self, path: str) -> Optional[str]:
        """Determine media type from a file or folder path.
        
        Args:
            path: Path to analyze.
            
        Returns:
            Optional[str]: Media type string, or None if cannot be determined.
        """
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

        key = None
        entityType = self.core.paths.getEntityTypeFromPath(path)
        if entityType == "asset":
            key = "renderFilesAssets"
        elif entityType == "shot":
            key = "renderFilesShots"

        mediaType = None
        if key:
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
                    data = self.core.projects.extractKeysFromPath(os.path.dirname(path), template, context=context)
                    if data:
                        mediaType = "2drenders"
                    else:
                        key = "renderVersions"
                        context["mediaType"] = "externalMedia"
                        template = self.core.projects.getResolvedProjectStructurePath(key, context=context)
                        data = self.core.projects.extractKeysFromPath(os.path.dirname(os.path.dirname(path)), template, context=context)
                        if data:
                            mediaType = "externalMedia"

        if not mediaType:
            pathData = self.getDataFromFilepath(path)
            if pathData and pathData.get("mediaType"):
                mediaType = pathData["mediaType"]

        return mediaType

    @err_catcher(name=__name__)
    def deleteMasterVersion(self, path: str, isFilepath: bool = False, mediaType: Optional[str] = None,
                            allowClear: bool = True, allowRename: bool = True) -> bool:
        """Delete a master version folder.
        
        Attempts to remove the master version, with retry logic and fallback to renaming.
        
        Args:
            path: Path to media file or version folder.
            isFilepath: Whether path is a filepath (vs version folder path).
            mediaType: Optional media type hint.
            allowClear: Whether to clear UI selection on retry.
            allowRename: Whether to rename instead of delete if removal fails.
            
        Returns:
            bool: True if deletion succeeded, False otherwise.
        """
        if isFilepath:
            vpath = self.getVersionPathFromMediaFilePath(path, mediaType=mediaType)
        else:
            vpath = path

        logger.debug("removing master render version: %s" % vpath)
        if vpath and os.path.exists(vpath):
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
    def addToMasterVersion(self, path: Optional[str] = None, context: Optional[Dict] = None,
                           isFilepath: bool = True, mediaType: Optional[str] = None) -> None:
        """Add a version to the master version.
        
        Convenience wrapper for updateMasterVersion with add=True.
        
        Args:
            path: Path to media file or folder.
            context: Optional context dict.
            isFilepath: Whether path is a filepath.
            mediaType: Optional media type hint.
        """
        self.updateMasterVersion(
            path=path, context=context, isFilepath=isFilepath, add=True, mediaType=mediaType
        )

    @err_catcher(name=__name__)
    def getVersionPathsFromMaster(self, path: str, isFilepath: bool = True) -> List[str]:
        """Get list of version folder paths referenced by a master version.
        
        Args:
            path: Path to master version file or folder.
            isFilepath: Whether path is a filepath.
            
        Returns:
            List[str]: List of version folder paths.
        """
        infoPath = self.getMediaVersionInfoPathFromFilepath(path)
        paths = self.core.getConfig("versionpaths", configPath=infoPath) or []
        return paths

    @err_catcher(name=__name__)
    def getUseMaster(self) -> bool:
        """Check if master versions are enabled in project settings.
        
        Returns:
            bool: True if master versions enabled, False otherwise.
        """
        return self.core.getConfig(
            "globals", "useMasterRenderVersion", dft=False, config="project"
        )

    @err_catcher(name=__name__)
    def getLinkedToTasks(self) -> bool:
        """Check if products are linked to tasks in project settings.
        
        Returns:
            bool: True if products linked to tasks, False otherwise.
        """
        return self.core.getConfig("globals", "productTasks", config="project")

    @err_catcher(name=__name__)
    def createIdentifier(self, entity: Dict, identifier: str, identifierType: str = "3drenders",
                         location: str = "global") -> Optional[str]:
        """Create a new media product identifier folder.
        
        Args:
            entity: Entity dict containing type and other entity data.
            identifier: Identifier/product name.
            identifierType: Type of media product. Defaults to '3drenders'.
            location: Storage location. Defaults to 'global'.
            
        Returns:
            Optional[str]: Path to created identifier folder, or None if creation failed.
        """
        context = entity.copy()
        context["identifier"] = identifier
        if "task" not in context:
            context["task"] = "none"

        if "user" not in context:
            context["user"] = self.core.user

        basePath = self.core.paths.getRenderProductBasePaths()[location]
        context["project_path"] = basePath
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
    def createVersion(self, entity: Dict, identifier: str, version: str, identifierType: str = "3drenders",
                      location: str = "global") -> Optional[str]:
        """Create a new version folder for a media product.
        
        Args:
            entity: Entity dict containing type and other entity data.
            identifier: Identifier/product name.
            version: Version string (e.g., 'v0001').
            identifierType: Type of media product. Defaults to '3drenders'.
            location: Storage location. Defaults to 'global'.
            
        Returns:
            Optional[str]: Path to created version folder, or None if creation failed.
        """
        context = entity.copy()
        context["identifier"] = identifier
        context["mediaType"] = identifierType
        context["version"] = version
        if "task" not in context:
            context["task"] = "none"

        if "user" not in context:
            context["user"] = self.core.user

        basePath = self.core.paths.getRenderProductBasePaths()[location]
        context["project_path"] = basePath
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
    def createAov(self, entity: Dict, identifier: str, version: str, aov: str,
                  identifierType: str = "3drenders") -> Optional[str]:
        """Create a new AOV folder for a render version.
        
        Args:
            entity: Entity dict containing type and other entity data.
            identifier: Identifier/product name.
            version: Version string.
            aov: AOV/render layer name.
            identifierType: Type of media product. Defaults to '3drenders'.
            
        Returns:
            Optional[str]: Path to created AOV folder, or None if creation failed.
        """
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
    def ingestMedia(self, files: List[str], entity: Dict, identifier: str, version: Optional[str] = None, aov: Optional[str] = None, mediaType: str = "3drenders", filenameTemplate: Optional[str] = None, location: str = "global", rename: bool = True) -> Dict:
        """Ingest external media files into the project structure.
        
        Copies files into proper version folders with progress tracking.

        Args:
            files: List of file paths to ingest.
            entity: Entity dict containing type and other entity data.
            identifier: Product identifier name.
            version: Optional version string. Auto-generates if None.
            aov: Optional AOV name for 3D renders.
            mediaType: Type of media. Defaults to '3drenders'.
            filenameTemplate: Optional template for renaming files.
            location: Storage location. Defaults to 'global'.
            rename: When True (default), files are renamed to match the project naming
                convention (frame-padded sequence). When False, original filenames are kept.
            
        Returns:
            Dict: Result dict with 'result' (list of ingested paths), 'versionAdded' (bool), 'versionPath' (str).
        """
        if not files:
            return

        kwargs = {
            "entity": entity,
            "task": identifier,
            "version": version,
            "aov": aov,
            "user": self.core.user,
            "mediaType": mediaType,
            "filenameTemplate": filenameTemplate,
            "location": location,
        }

        baseTxt = "Copying file - please wait..\n\n"
        updatedText = baseTxt + "%s/%s" % (0, len(files))
        self.copyMsg = self.core.waitPopup(self.core, updatedText, hidden=True)

        self.ingestedFiles = []
        self.ingestCanceled = False
        self.ingestThreads = []
        startFrame = 1
        if entity.get("type") == "shot":
            shotRange = self.core.entities.getShotRange(entity)
            if shotRange:
                startFrame = shotRange[0]
                if startFrame is None:
                    startFrame = 1001

        with self.copyMsg as copyMsg:
            # Pre-compute all (source, destination) path pairs up front so we can
            # choose the most efficient copy strategy before touching the filesystem.
            pairs = []
            for idx, file in enumerate(files):
                kw = kwargs.copy()
                kw["extension"] = os.path.splitext(file)[1]
                if rename and len(files) > 1:
                    kw["framePadding"] = ("%%0%sd" % self.core.framePadding) % (idx + startFrame)
                if kw.get("mediaType") == "playblasts":
                    pbkw = kw.copy()
                    del pbkw["aov"]
                    del pbkw["mediaType"]
                    tp = self.generatePlayblastPath(**pbkw)
                else:
                    tp = self.generateMediaProductPath(**kw)
                if not rename:
                    # Keep the original filename; only use the generated path for its directory.
                    tp = os.path.join(os.path.dirname(tp), os.path.basename(file))
                pairs.append((file, tp.replace("\\", "/")))

            # Preserve final-file kwargs so saveVersionInfo below is correct.
            kwargs["extension"] = os.path.splitext(files[-1])[1]
            if len(files) > 1:
                kwargs["framePadding"] = ("%%0%sd" % self.core.framePadding) % (len(files) - 1 + startFrame)

            if self.ingestCanceled:
                return

            targetPath = pairs[-1][1]
            dst_dir = os.path.dirname(pairs[0][1])

            if not os.path.exists(dst_dir):
                try:
                    os.makedirs(dst_dir)
                except:
                    msg = "The directory could not be created"
                    self.core.popup(msg)
                    return {"result": msg}

            elif os.listdir(dst_dir):
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

            # --- Copy strategy selection ---
            # Batch robocopy: one subprocess for all files when all sources share
            # the same directory. robocopy's /MT gives parallel I/O within that
            # single process, so this is both faster and avoids the OS thread/handle
            # exhaustion that occurred when spawning one subprocess per file.
            src_dirs = set(os.path.dirname(src) for src, _ in pairs)
            use_batch = (
                platform.system() == "Windows"
                and os.getenv("PRISM_USE_ROBOCOPY", "1") == "1"
                and len(src_dirs) == 1
                and len(pairs) > 1
            )

            if use_batch:
                src_dir_rb = next(iter(src_dirs))
                filenames = [os.path.basename(src) for src, _ in pairs]
                cmd = (
                    ["robocopy", src_dir_rb, dst_dir]
                    + filenames
                    + ["/COPY:DAT", "/R:3", "/W:5", "/MT:8", "/NP", "/NDL"]
                )
                logger.debug("Batch robocopy: %s" % " ".join(cmd))
                try:
                    import subprocess as _sp
                    proc = _sp.Popen(
                        cmd,
                        stdout=_sp.PIPE,
                        stderr=_sp.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=_sp.CREATE_NO_WINDOW,
                    )
                    stdout_lines = []
                    while proc.poll() is None:
                        # Drain stdout to prevent the pipe buffer from filling up and
                        # blocking robocopy. With 200+ files the buffer fills quickly.
                        line = proc.stdout.readline()
                        if line:
                            line = line.rstrip()
                            stdout_lines.append(line)
                            logger.debug("robocopy: %s" % line)
                        QApplication.processEvents()
                        if self.ingestCanceled:
                            proc.terminate()
                            return

                    # Drain any remaining output after process exits
                    for line in proc.stdout:
                        line = line.rstrip()
                        stdout_lines.append(line)
                        logger.debug("robocopy: %s" % line)

                    logger.debug("Batch robocopy finished with return code %s" % proc.returncode)
                    files_in_dst = os.listdir(dst_dir) if os.path.exists(dst_dir) else []
                    logger.debug("Files in dst_dir after copy (%s): %s" % (len(files_in_dst), dst_dir))

                    if proc.returncode not in (0, 1, 2, 3):
                        logger.warning(
                            "Batch robocopy failed (rc=%s), falling back to sequential copy.\nOutput:\n%s"
                            % (proc.returncode, "\n".join(stdout_lines))
                        )
                        use_batch = False

                except Exception as e:
                    logger.warning("Batch robocopy error: %s — falling back to sequential copy." % e)
                    use_batch = False

                if use_batch:
                    # Rename files whose destination name differs from the source name
                    # (frame-padded targets). Files that already have the right name
                    # in the destination are left as-is.
                    logger.debug("%s phase for %s pairs" % ("Rename" if rename else "Progress-tracking", len(pairs)))
                    for src, dst in pairs:
                        src_name = os.path.basename(src)
                        dst_name = os.path.basename(dst)
                        if src_name != dst_name:
                            src_in_dst = os.path.join(dst_dir, src_name)
                            if os.path.exists(src_in_dst):
                                try:
                                    os.rename(src_in_dst, dst)
                                    logger.debug("Renamed %s → %s" % (src_name, dst_name))
                                except Exception as e:
                                    logger.warning("Failed to rename %s → %s: %s" % (src_in_dst, dst, e))
                            else:
                                logger.warning("Expected file not found after copy: %s" % src_in_dst)

                        self.ingestedFiles.append(dst)
                        updatedText = "Copying file - please wait..\n\n%s/%s" % (len(self.ingestedFiles), len(pairs))
                        self.copyMsg.text = updatedText
                        if copyMsg.msg:
                            copyMsg.msg.setText(updatedText)
                            QApplication.processEvents()

                    logger.debug("Rename phase complete. Ingested: %s" % len(self.ingestedFiles))
                    self.copyMsg.close()

            if not use_batch:
                # Sequential copy: one thread at a time to avoid spawning hundreds of
                # robocopy subprocesses simultaneously.
                for src, dst in pairs:
                    if self.ingestCanceled:
                        break
                    copyThread = self.core.copyWithProgress(src, dst, popup=False, start=False)
                    self.ingestThreads.append(copyThread)
                    copyThread.finished.connect(lambda t=copyThread, tp=dst: self.onMediaFileIngested(t, tp, len(pairs)))
                    copyThread.start()
                    while copyThread.isRunning():
                        time.sleep(0.05)
                        QApplication.processEvents()
                        if self.ingestCanceled:
                            break

            details = entity.copy()
            details["identifier"] = identifier
            details["user"] = kwargs["user"]
            details["version"] = kwargs["version"]
            details["comment"] = kwargs.get("comment", "")
            details["extension"] = kwargs["extension"]
            details["mediaType"] = kwargs["mediaType"]
            details["date"] = int(datetime.datetime.now().timestamp())

            infoPath = self.getMediaVersionInfoPathFromFilepath(targetPath, mediaType=mediaType)
            self.core.saveVersionInfo(filepath=os.path.dirname(infoPath), details=details)

        return {"result": self.ingestedFiles, "versionAdded": False, "versionPath": targetPath}

    @err_catcher(name=__name__)
    def onMediaFileIngested(self, thread: Any, targetPath: str, numFiles: int) -> None:
        """Callback when a media file finishes being copied during ingest.
        
        Updates progress UI and closes popup when all files complete.
        
        Args:
            thread: The copy thread that finished.
            targetPath: Destination path of the ingested file.
            numFiles: Total number of files being ingested.
        """
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
    def onIngestCanceled(self) -> None:
        """Cancel all running ingest operations."""
        self.ingestCanceled = True
        for thread in self.ingestThreads:
            if thread.isRunning():
                thread.cancel()

    @err_catcher(name=__name__)
    def checkMasterVersions(self, entities: List[Dict], parent: Optional[QWidget] = None) -> None:
        """Check and display outdated master versions for entities.
        
        Opens a dialog showing which master versions need updating.
        
        Args:
            entities: List of entity dicts to check.
            parent: Optional parent widget for the dialog.
        """
        self.dlg_masterManager = self.core.paths.masterManager(self.core, entities, "media", parent=parent)
        self.dlg_masterManager.refreshData()
        if not self.dlg_masterManager.outdatedVersions:
            msg = "All master versions of the selected entities are up to date."
            self.core.popup(msg, severity="info")
            return

        self.dlg_masterManager.show()

    @err_catcher(name=__name__)
    def getOutdatedMasterVersions(self, entities: List[Dict]) -> List[Dict]:
        """Find all outdated master versions for a list of entities.
        
        Args:
            entities: List of entity dicts to check.
            
        Returns:
            List[Dict]: List of dicts with 'master' and 'latest' version info.
        """
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

    @err_catcher(name=__name__)
    def getGroupFromIdentifier(self, identifier: Dict) -> Optional[str]:
        """Get the group name assigned to an identifier.
        
        Args:
            identifier: Identifier dict.
            
        Returns:
            Optional[str]: Group name, or None if not set.
        """
        identifierPath = self.getIdentifierPathFromEntity(identifier)
        cfgPath = os.path.join(identifierPath, "identifiers" + self.core.configs.getProjectExtension())
        group = self.core.getConfig(identifier.get("displayName"), "group", configPath=cfgPath)
        if not group:
            groups = self.core.getConfig("media_identifiers", "groups", config="project") or {}
            for identifierName, groupName in groups.items():
                if identifier.get("displayName") == identifierName or fnmatch.fnmatch(identifier.get("displayName"), identifierName):
                    group = groupName
                    break

        return group

    @err_catcher(name=__name__)
    def setIdentifiersGroup(self, identifiers: List[Dict], group: str, projectWide: bool = False) -> None:
        """Set the group for multiple identifiers.
        
        Args:
            identifiers: List of identifier dicts.
            group: Group name to assign.
            projectWide: Whether to apply project-wide (not currently implemented).
        """
        identifierPath = self.getIdentifierPathFromEntity(identifiers[0])
        cfgPath = os.path.join(identifierPath, "identifiers" + self.core.configs.getProjectExtension())
        data = self.core.getConfig(configPath=cfgPath) or {}
        for identifier in identifiers:
            if identifier.get("displayName") not in data:
                data[identifier.get("displayName")] = {}

            data[identifier.get("displayName")]["group"] = group

        self.core.setConfig(data=data, configPath=cfgPath)
        return True
