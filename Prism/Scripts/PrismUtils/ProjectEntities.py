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
import shutil
import time
import re
import datetime
import copy
from typing import Any, Optional, List, Dict, Tuple, Union

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher

from PrismUtils import PrismWidgets


logger = logging.getLogger(__name__)


class ProjectEntities(object):
    """Manages all entity-related operations for Prism projects.
    
    Handles creation, retrieval, modification, and querying of project entities
    including assets, shots, sequences, episodes, departments, and tasks. Provides
    methods for managing entity metadata, ranges, dependencies, and file operations.
    
    Attributes:
        core: PrismCore instance.
        entityFolders (Dict[str, List[str]]): Predefined subfolders for entity types.
        entityActions (Dict): Registered entity context menu actions.
        depIcons (Dict): Department icon cache.
        entityDlg: Dialog class for entity operations.
        omittedEntities (Dict[str, List]): Entities marked as omitted/hidden.
    """

    def __init__(self, core: Any) -> None:
        """Initialize the ProjectEntities manager.
        
        Args:
            core: PrismCore instance.
        """
        self.core = core
        self.entityFolders = {"asset": ["Textures"], "shot": []}
        self.entityActions = {}
        self.depIcons = {}
        self.entityDlg = EntityDlg
        self.refreshOmittedEntities()
        self.addEntityAction(
            key="importConnectedAssets",
            types=["shot"],
            function=lambda entities=None, parent=None: self.core.products.importConnectedAssetsForEntities(entities),
            label="Import Connected Assets..."
        )

    @err_catcher(name=__name__)
    def refreshOmittedEntities(self) -> None:
        """Refresh the list of omitted entities from project configuration."""
        self.omittedEntities = {"asset": [], "shot": []}
        omits = self.core.getConfig(config="omit") or {}

        oShots = omits.get("shot") or []
        oAssets = omits.get("asset") or []

        self.omittedEntities["shot"] = oShots
        self.omittedEntities["asset"] = oAssets
        self.omittedEntities["assetFolder"] = oAssets

    @err_catcher(name=__name__)
    def isEntityOmitted(self, entity: Dict[str, Any]) -> bool:
        """Check if an entity is marked as omitted.
        
        Args:
            entity: Entity dict with a 'type' key.
            
        Returns:
            bool: True if entity is omitted.
        """
        if entity["type"] in ["asset", "assetFolder"]:
            return self.isAssetOmitted(entity)
        elif entity["type"] == "shot":
            return self.isShotOmitted(entity)

    @err_catcher(name=__name__)
    def isAssetOmitted(self, entity: Dict[str, Any]) -> bool:
        """Check if an asset entity is omitted.
        
        Args:
            entity: Asset entity dict with 'asset_path' key.
            
        Returns:
            bool: True if asset is omitted.
        """
        omitted = entity["asset_path"].replace("\\", "/") in [a.replace("\\", "/") for a in self.omittedEntities["asset"]]
        return omitted

    @err_catcher(name=__name__)
    def isEpisodeOmitted(self, entity: Dict[str, Any]) -> bool:
        """Check if an episode entity is omitted.
        
        Args:
            entity: Episode entity dict.
            
        Returns:
            bool: Currently always returns False.
        """
        return False

    @err_catcher(name=__name__)
    def isSequenceOmitted(self, entity: Dict[str, Any]) -> bool:
        """Check if a sequence entity is omitted.
        
        Args:
            entity: Sequence entity dict.
            
        Returns:
            bool: Currently always returns False.
        """
        return False

    @err_catcher(name=__name__)
    def isShotOmitted(self, entity: Dict[str, Any]) -> bool:
        """Check if a shot entity is omitted.
        
        Args:
            entity: Shot entity dict with 'sequence' and 'shot' keys.
            
        Returns:
            bool: True if shot is omitted.
        """
        if entity["sequence"] in self.omittedEntities["shot"]:
            if entity["shot"] in self.omittedEntities["shot"][entity["sequence"]]:
                return True

        return False

    @err_catcher(name=__name__)
    def getShotSubFolders(self) -> List[str]:
        """Get the list of expected subfolders for shot entities.
        
        Returns:
            List[str]: List of subfolder names (e.g., ['Scenefiles', 'Export']).
        """
        subfolders = []

        template = self.core.projects.getTemplatePath("departments")
        template = template.replace("\\", "/")
        sceneFolder = template.split("/")[1]
        if sceneFolder:
            subfolders.append(sceneFolder)

        template = self.core.projects.getTemplatePath("products")
        template = template.replace("\\", "/")
        productFolder = template.split("/")[1]
        if productFolder:
            subfolders.append(productFolder)

        template = self.core.projects.getTemplatePath("3drenders")
        template = template.replace("\\", "/")
        renderFolder = template.split("/")[1]
        if renderFolder:
            subfolders.append(renderFolder)

        template = self.core.projects.getTemplatePath("playblasts")
        template = template.replace("\\", "/")
        playblastFolder = template.split("/")[1]
        if playblastFolder:
            subfolders.append(playblastFolder)

        return subfolders

    @err_catcher(name=__name__)
    def getTypeFromShotPath(self, path: str, content: Optional[List[str]] = None) -> Optional[str]:
        """Determine if a path represents a shot or folder based on its contents.
        
        Args:
            path: Path to check.
            content: Optional list of folder contents (if already known).
            
        Returns:
            Optional[str]: 'shot' if path is a shot, 'folder' otherwise, or None if path doesn't exist.
        """
        if not os.path.exists(path):
            return

        if content is None:
            content = os.listdir(path)

        subfolders = self.getShotSubFolders()

        if self.core.getConfig(
            "globals", "useStrictShotDetection", dft=False, config="project"
        ):
            isShot = True
            for folder in subfolders:
                if folder not in content:
                    isShot = False

        else:
            isShot = False
            for folder in subfolders:
                if folder in content:
                    isShot = True

        if isShot:
            return "shot"
        else:
            return "folder"

    @err_catcher(name=__name__)
    def getShotName(self, entity: Dict[str, Any]) -> Optional[str]:
        """Get the formatted name for a shot entity.
        
        Args:
            entity: Shot entity dict with 'sequence', 'shot', and optionally 'episode' keys.
            
        Returns:
            Optional[str]: Formatted shot name, or None if no sequence in entity.
        """
        if "sequence" not in entity:
            return

        shotnameTemplate = os.getenv("PRISM_SHOT_NAME_TEMPLATE")
        if shotnameTemplate:
            shotname = self.core.projects.resolveStructurePath(shotnameTemplate, context=entity)[0]
        else:
            if "shot" in entity:
                shotname = (entity["sequence"] or "") + "-" + (entity["shot"] or "")
            else:
                shotname = entity["sequence"] or ""

            if "episode" in entity:
                shotname = "%s-%s" % (entity["episode"], shotname)

        return shotname

    @err_catcher(name=__name__)
    def setShotRange(self, entity: Dict[str, Any], start: int, end: int) -> None:
        """Set the frame range for a shot entity.
        
        Args:
            entity: Shot entity dict with 'episode', 'sequence', and 'shot' keys.
            start: Start frame number.
            end: End frame number.
        """
        if self.core.projects.getUseEpisodes() and self.core.compareVersions(self.core.projectVersion, "v2.1.1") != "lower":
            epRanges = self.core.getConfig(
                "shotRanges", entity["episode"], config="shotinfo", allowCache=False
            )
            if not epRanges:
                epRanges = {}

            if not epRanges.get(entity["sequence"]):
                epRanges[entity["sequence"]] = {}

            epRanges[entity["sequence"]][entity["shot"]] = [start, end]
            self.core.setConfig(
                "shotRanges", entity["episode"], epRanges, config="shotinfo"
            )
        else:
            seqRanges = self.core.getConfig(
                "shotRanges", entity["sequence"], config="shotinfo", allowCache=False
            )
            if not seqRanges:
                seqRanges = {}

            seqRanges[entity["shot"]] = [start, end]
            self.core.setConfig(
                "shotRanges", entity["sequence"], seqRanges, config="shotinfo"
            )

    @err_catcher(name=__name__)
    def getShotRange(self, entity: Dict[str, Any], handles: bool = False) -> Optional[List[int]]:
        """Get the frame range for a shot entity.
        
        Args:
            entity: Shot entity dict with 'sequence', 'shot', and optionally 'episode' keys.
            handles: If True, include handle frames in the range.
            
        Returns:
            Optional[List[int]]: Two-element list [start, end] or None if no range defined.
        """
        shotRange = None
        ranges = self.core.getConfig("shotRanges", config="shotinfo") or {}
        if self.core.projects.getUseEpisodes() and self.core.compareVersions(self.core.projectVersion, "v2.1.1") != "lower":
            if entity.get("episode") in ranges:
                if entity.get("sequence") in ranges[entity["episode"]]:
                    if entity.get("shot") in ranges[entity["episode"]][entity["sequence"]]:
                        shotRange = ranges[entity["episode"]][entity["sequence"]][entity["shot"]].copy()

        else:
            if entity.get("sequence") in ranges:
                if entity.get("shot") in ranges[entity["sequence"]]:
                    shotRange = ranges[entity["sequence"]][entity["shot"]].copy()

        if not shotRange:
            return

        if handles:
            metaData = self.getMetaData(entity)
            if "handles_in" in metaData:
                try:
                    shotRange[0] = shotRange[0] - int(metaData["handles_in"]["value"])
                except:
                    pass

            if "handles_out" in metaData:
                try:
                    shotRange[1] = shotRange[1] + int(metaData["handles_out"]["value"])
                except:
                    pass

            if "handles" in metaData:
                try:
                    handleNum = int(metaData["handles"]["value"])
                except:
                    pass
                else:
                    if "handles_in" not in metaData:
                        shotRange[0] = shotRange[0] - handleNum

                    if "handles_out" not in metaData:
                        shotRange[1] = shotRange[1] + handleNum

        return shotRange

    @err_catcher(name=__name__)
    def getEpisodes(self, searchFilter: str = "", locations: Optional[List] = None, includeOmitted: bool = False) -> List[Dict[str, Any]]:
        """Get all episodes matching the search filter.
        
        Args:
            searchFilter: Optional filter string to match episode names or descriptions.
            locations: Optional list of specific locations to search.
            includeOmitted: If True, include episodes marked as omitted.
            
        Returns:
            List[Dict[str, Any]]: List of episode dicts with paths and metadata.
        """
        epDirs = self.getLocations(locations)
        epDicts = []
        for epDir in epDirs:
            context = {"project_path": epDir["path"]}
            template = self.core.projects.getResolvedProjectStructurePath(
                "episodes", context=context
            )
            epData = self.core.projects.getMatchingPaths(template)
            for data in epData:
                if "." in os.path.basename(data["path"]) and os.path.isfile(data["path"]):
                    continue

                if data["episode"].startswith("_"):
                    continue

                if self.isEpisodeOmitted(data) and not includeOmitted:
                    continue

                if (
                    searchFilter.lower() not in data["episode"].lower()
                ):
                    metaData = self.getMetaData(data)
                    if not metaData or searchFilter.lower() not in metaData.get("Description", {}).get("value", "").lower():
                        continue

                data["location"] = epDir["location"]
                data["type"] = "shot"
                epDicts.append(data)

        episodes = []
        for epDict in sorted(epDicts, key=lambda x: x["path"]):
            for episode in episodes:
                if (
                    epDict["episode"] == episode["episode"]
                ):
                    data = {"location": epDict["location"], "path": epDict["path"]}
                    episode["paths"].append(data)
                    break
            else:
                epDict["paths"] = [
                    {"location": epDict["location"], "path": epDict["path"]}
                ]
                episodes.append(epDict)

        episodes = sorted(episodes, key=lambda x: self.core.naturalKeys(x["episode"]))
        return episodes

    @err_catcher(name=__name__)
    def getSequences(self, searchFilter: str = "", locations: Optional[List] = None, episode: Optional[str] = None, includeOmitted: bool = False) -> List[Dict[str, Any]]:
        """Get all sequences matching the search filter.
        
        Args:
            searchFilter: Optional filter string to match sequence names or descriptions.
            locations: Optional list of specific locations to search.
            episode: Optional episode name to filter sequences.
            includeOmitted: If True, include sequences marked as omitted.
            
        Returns:
            List[Dict[str, Any]]: List of sequence dicts with paths and metadata.
        """
        seqDirs = self.getLocations(locations)
        seqDicts = []
        for seqDir in seqDirs:
            context = {"project_path": seqDir["path"]}
            if episode:
                context["episode"] = episode

            template = self.core.projects.getResolvedProjectStructurePath(
                "sequences", context=context
            )
            seqData = self.core.projects.getMatchingPaths(template)
            for data in seqData:
                if "." in os.path.basename(data["path"]) and os.path.isfile(data["path"]):
                    continue

                if data["sequence"].startswith("_"):
                    continue

                if self.isSequenceOmitted(data) and not includeOmitted:
                    continue

                if searchFilter:
                    if (
                        searchFilter.lower() not in data["sequence"].lower()
                    ):
                        metaData = self.getMetaData(data)
                        if not metaData or searchFilter.lower() not in metaData.get("Description", {}).get("value", "").lower():
                            if not self.getShots(sequence=data["sequence"], searchFilter=searchFilter, locations=locations, episode=episode):
                                continue

                data["location"] = seqDir["location"]
                data["type"] = "shot"
                if episode:
                    data["episode"] = episode

                seqDicts.append(data)

        sequences = []
        for seqDict in sorted(seqDicts, key=lambda x: x["path"]):
            for sequence in sequences:
                if (
                    seqDict["sequence"] == sequence["sequence"]
                ):
                    data = {"location": seqDict["location"], "path": seqDict["path"]}
                    sequence["paths"].append(data)
                    break
            else:
                seqDict["paths"] = [
                    {"location": seqDict["location"], "path": seqDict["path"]}
                ]
                sequences.append(seqDict)

        sequences = sorted(sequences, key=lambda x: self.core.naturalKeys(x["sequence"]))
        return sequences

    @err_catcher(name=__name__)
    def getLocations(self, locations: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """Get project locations (paths) to search for entities.
        
        Args:
            locations: Optional list of location names/paths to filter.
            
        Returns:
            List[Dict[str, str]]: List of location dicts with 'path' and 'location' keys.
        """
        locationDicts = []
        location_paths = self.core.paths.getExportProductBasePaths()
        location_paths.update(self.core.paths.getRenderProductBasePaths())
        for location in location_paths:
            if locations is not None and location not in locations:
                continue
            locDir = {"location": location, "path": location_paths[location]}
            locationDicts.append(locDir)

        return locationDicts

    @err_catcher(name=__name__)
    def filterValidShots(self, shotData: List[Dict[str, Any]], searchFilter: str = "", includeOmitted: bool = False) -> List[Dict[str, Any]]:
        """Filter shot data to only valid shots matching the search filter.
        
        Args:
            shotData: List of shot dicts to filter.
            searchFilter: Optional filter string to match shot names or descriptions.
            includeOmitted: If True, include shots marked as omitted.
            
        Returns:
            List[Dict[str, Any]]: Filtered list of shot dicts.
        """
        searchFilters = [x.strip() for x in searchFilter.lower().split(",") if x.strip()] if searchFilter else []
        validShots = []
        for data in shotData:
            if "." in os.path.basename(data["path"]) and os.path.isfile(data["path"]):
                continue

            if data.get("episode", "").startswith("_"):
                continue

            if data["sequence"].startswith("_"):
                continue

            if data["shot"].startswith("_"):
                continue

            if self.isShotOmitted(data) and not includeOmitted:
                continue

            if searchFilters:
                valid = False
                for searchFilter in searchFilters:
                    if (
                        ("episode" in data and searchFilter in data["episode"].lower())
                        or searchFilter in data["sequence"].lower()
                        or searchFilter in data["shot"].lower()
                    ):
                        valid = True
                        break

                    metaData = self.getMetaData(data)
                    if metaData and searchFilter in metaData.get("Description", {}).get("value", "").lower():
                        valid = True
                        break

                    if searchFilter in self.getEntityName(data):
                        valid = True
                        break

                if not valid:
                    continue

            validShots.append(data)

        return validShots

    @err_catcher(name=__name__)
    def combineShotsFromLocations(self, shotData: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Combine shot data from multiple locations into unique shots.
        
        Args:
            shotData: List of shot dicts from different locations.
            
        Returns:
            List[Dict[str, Any]]: Combined list with unique shots having multiple paths.
        """
        shots = []
        for shotDict in sorted(shotData, key=lambda x: x["path"]):
            for shot in shots:
                if (
                    shotDict["sequence"] == shot["sequence"]
                    and shotDict["shot"] == shot["shot"]
                    and ("episode" not in shotDict or shotDict.get("episode") == shot.get("episode"))
                ):
                    data = {"location": shotDict["location"], "path": shotDict["path"]}
                    shot["paths"].append(data)
                    break
            else:
                shotDict["paths"] = [
                    {"location": shotDict["location"], "path": shotDict["path"]}
                ]
                shots.append(shotDict)

        return shots

    @err_catcher(name=__name__)
    def getShot(self, sequence: str, shot: str, episode: Optional[str] = None, projectPath: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a specific shot entity by name.
        
        Args:
            sequence: Sequence name.
            shot: Shot name.
            episode: Optional episode name.
            projectPath: Optional specific project path to search.
            
        Returns:
            Optional[Dict[str, Any]]: Shot entity dict or None if not found.
        """
        if not sequence or not shot:
            return

        shot = {"type": "shot", "sequence": sequence, "shot": shot}
        if episode:
            shot["episode"] = episode

        shotpath = self.core.projects.getResolvedProjectStructurePath(
            "shots", context=shot
        )
        existed = os.path.exists(shotpath)
        if existed:
            return shot
        else:
            return

    @err_catcher(name=__name__)
    def getShots(self, searchFilter: str = "", locations: Optional[List] = None, episode: Optional[str] = None, sequence: Optional[str] = None, includeOmitted: bool = False) -> List[Dict[str, Any]]:
        """Get all shots matching the filter criteria.
        
        Args:
            searchFilter: Optional filter string to match shot names or descriptions.
            locations: Optional list of specific locations to search.
            episode: Optional episode name to filter shots.
            sequence: Optional sequence name to filter shots.
            includeOmitted: Whether to include shots marked as omitted.
            
        Returns:
            List[Dict[str, Any]]: List of shot dicts with paths and metadata.
        """
        seqDirs = self.getLocations(locations)
        shotDicts = []
        for seqDir in seqDirs:
            context = {"project_path": seqDir["path"]}
            if episode:
                context["episode"] = episode

            if sequence:
                context["sequence"] = sequence

            template = self.core.projects.getResolvedProjectStructurePath(
                "shots", context=context
            )
            shotData = self.core.projects.getMatchingPaths(template)
            for data in shotData:
                if episode:
                    data["episode"] = episode

                if sequence:
                    data["sequence"] = sequence

                data["location"] = seqDir["location"]
                data["type"] = "shot"

            shotDicts += self.filterValidShots(shotData, searchFilter=searchFilter, includeOmitted=includeOmitted)

        shots = self.combineShotsFromLocations(shotDicts)
        shots = sorted(shots, key=lambda x: self.core.naturalKeys(x["shot"]))
        return shots

    @err_catcher(name=__name__)
    def getShotsFromSequence(self, sequence: str) -> List[Dict[str, Any]]:
        """Get all shots for a specific sequence.
        
        Args:
            sequence: Sequence name.
            
        Returns:
            List[Dict[str, Any]]: List of shot dicts.
        """
        shots = self.core.entities.getShots(sequence=sequence)
        return shots

    @err_catcher(name=__name__)
    def getSteps(self, entity: Dict[str, Any]) -> List[str]:
        """Get all departments/steps for an entity.
        
        Args:
            entity: Entity dict with 'type' key.
            
        Returns:
            List[str]: List of department names.
        """
        departments = []
        path = self.core.getEntityPath(entity=entity, reqEntity="step")
        stepDirs = []

        templates = self.core.projects.getResolvedProjectStructurePaths(
            "departments", context=entity
        )

        if self.core.useLocalFiles:
            for template in templates:
                path = self.core.convertPath(template, target="global")
                lpath = self.core.convertPath(template, target="local")
                if path not in stepDirs:
                    stepDirs.append(path)

                if lpath not in stepDirs:
                    stepDirs.append(lpath)
        else:
            stepDirs = templates

        dirContent = []
        for sDir in stepDirs:
            dirContent += self.core.projects.getMatchingPaths(sDir)

        for content in sorted(dirContent, key=lambda x: x.get("department")):
            dep = content.get("department", "")
            if dep.startswith("_"):
                continue

            if os.path.isdir(content["path"]) and dep not in departments:
                departments.append(dep)

        departments = self.orderDepartments(entity, departments)
        return departments

    @err_catcher(name=__name__)
    def getCategories(self, entity: Dict[str, Any], step: Optional[str] = None) -> List[str]:
        """Get all categories (tasks) for an entity and optional department.
        
        Args:
            entity: Entity dict.
            step: Optional department name to filter categories.
            
        Returns:
            List[str]: List of category/task names.
        """
        cats = []
        path = self.core.getEntityPath(entity=entity, step=step)
        catDirs = [path]

        if self.core.useLocalFiles:
            path = self.core.convertPath(path, target="global")
            lpath = self.core.convertPath(path, target="local")
            catDirs = [path, lpath]

        dirContent = []

        for cDir in catDirs:
            if os.path.exists(cDir):
                dirContent += [os.path.join(cDir, x) for x in os.listdir(cDir)]

        for i in sorted(dirContent, key=lambda x: os.path.basename(x)):
            catName = os.path.basename(i)
            if catName.startswith("_"):
                continue

            if os.path.isdir(i) and catName not in cats:
                cats.append(catName)

        cats = self.orderTasks(entity, step, cats)
        return cats

    @err_catcher(name=__name__)
    def getScenefiles(self, entity: Optional[Dict[str, Any]] = None, step: Optional[str] = None, category: Optional[str] = None, extensions: Optional[List[str]] = None, path: Optional[str] = None) -> List[str]:
        """Get all scenefile paths matching the criteria.
        
        Args:
            entity: Optional entity dict to filter by.
            step: Optional department name.
            category: Optional task name.
            extensions: Optional list of file extensions to filter.
            path: Optional specific path to search.
            
        Returns:
            List[str]: List of scenefile paths.
        """
        scenefiles = []

        if not path:
            if entity["type"] == "asset":
                if (
                    self.core.compareVersions(self.core.projectVersion, "v1.2.1.6")
                    == "lower"
                ):
                    path = self.core.getEntityPath(entity=entity, step=step)
                else:
                    path = self.core.getEntityPath(
                        entity=entity, step=step, category=category
                    )
            elif entity["type"] == "shot":
                path = self.core.getEntityPath(
                    entity=entity,
                    step=step,
                    category=category,
                )

        sceneDirs = [path]

        if self.core.useLocalFiles:
            path = self.core.convertPath(path, target="global")
            lpath = self.core.convertPath(path, target="local")
            sceneDirs = [path, lpath]

        sfiles = {}
        for sDir in sceneDirs:
            for root, dirs, files in os.walk(sDir):
                for f in files:
                    if f in sfiles:
                        continue

                    scenePath = os.path.join(root, f).replace("\\", "/")
                    if self.isValidScenefilename(scenePath, extensions=extensions):
                        sfiles[f] = scenePath
                break

        scenefiles = list(sfiles.values())
        return scenefiles

    @err_catcher(name=__name__)
    def getScenefile(self, entity: Dict[str, Any], department: str, task: str, version: Union[str, int]) -> Optional[str]:
        """Get a specific scenefile path by version.
        
        Args:
            entity: Entity dict.
            department: Department name.
            task: Task name.
            version: Version number (int), version string, or 'latest'.
            
        Returns:
            Optional[str]: Scenefile path or None if not found.
        """
        scenefiles = self.getScenefiles(entity, department, task)
        highversion = [None, None]
        for scenefile in scenefiles:
            ext = os.path.splitext(scenefile)[1]
            if not self.isValidScenefilename(scenefile):
                continue

            fname = self.core.getScenefileData(scenefile)
            if fname.get("type") != entity.get("type"):
                continue

            try:
                sversion = int(fname["version"][-self.core.versionPadding:])
            except:
                continue

            if (
                ext.lower() in self.core.media.supportedFormats
                and self.core.versionFormat.startswith("v")
                and fname["version"][-(self.core.versionPadding+1)] != "v"
            ):
                continue

            if version == "latest":
                if highversion[0] is None or sversion > highversion[0]:
                    highversion = [sversion, scenefile]
            else:
                if isinstance(version, int):
                    if version == sversion:
                        return scenefile
                else:
                    if version == fname["version"]:
                        return scenefile

        if version == "latest":
            return highversion[1]

    @err_catcher(name=__name__)
    def isValidScenefilename(self, filename: str, extensions: Optional[List[str]] = None) -> bool:
        """Check if a filename is a valid scenefile.
        
        Filters out temp files, autosaves, and blacklisted extensions.
        
        Args:
            filename: Filename or path to check.
            extensions: Optional list of allowed extensions.
            
        Returns:
            bool: True if filename is a valid scenefile.
        """
        ext = os.path.splitext(filename)[1]
        if ext in [
            ".jpg",
            # ".json",
            ".yml",
            ".ini",
            ".lock",
            ".old",
            ".db",
            ".usda"
        ]:
            return False

        if ext in self.getBlacklistedExtensions():
            return False

        sData = self.core.getScenefileData(filename)

        try:
            int(sData["extension"][-5:])  # ignore maya temp files
            logger.debug("maya temp file")
            return False
        except Exception:
            pass

        if "extension" not in sData:
            logger.debug("no extension")
            return False

        if filename.endswith("info.json"):
            return False

        if sData["extension"].endswith("~"):  # ignore nuke autosave files
            logger.debug("nuke autosave file")
            return False

        if filename.endswith(".painter_lock"):  # ignore substance painter lock files
            logger.debug("substance lockfile")
            return False

        if sData["extension"] == ".spp" and "autosave_" in filename:  # ignore substance painter autosave files
            logger.debug("substance lockfile")
            return False

        if filename.endswith("autosave"):
            logger.debug("autosave file")
            return False

        if sData["extension"].startswith(".blend") and sData["extension"] != ".blend":  # ignore Blender autosave files
            logger.debug("Blender autosave file")
            return False

        if extensions:
            unknownScene = sData["extension"] not in self.core.getPluginSceneFormats()
            if unknownScene:
                if "*" not in extensions:
                    logger.debug("invalid extension: %s" % sData["extension"])
                    return False
            else:
                if sData["extension"] not in extensions:
                    logger.debug("invalid extension: %s" % sData["extension"])
                    return False

        return True

    @err_catcher(name=__name__)
    def orderDepartments(self, entity: Dict[str, Any], departments: List[str]) -> List[str]:
        """Order departments according to project settings.
        
        Args:
            entity: Entity dict with type
            departments: List of department names to order
            
        Returns:
            Ordered list of department names
        """
        if entity.get("type") == "asset":
            pdeps = self.core.projects.getAssetDepartments()
        elif entity.get("type") == "shot":
            pdeps = self.core.projects.getShotDepartments()
        else:
            return departments

        abbrs = [d["abbreviation"] for d in pdeps]
        deps = sorted(departments, key=lambda x: self.indexOf(x, abbrs))
        return deps

    @err_catcher(name=__name__)
    def orderTasks(self, entity: Dict[str, Any], department: str, tasks: List[str]) -> List[str]:
        """Order tasks according to department's default task order.
        
        Args:
            entity: Entity dict with type
            department: Department abbreviation
            tasks: List of task names to order
            
        Returns:
            Ordered list of task names
        """
        if entity.get("type") == "asset":
            pdeps = self.core.projects.getAssetDepartments()
        elif entity.get("type") == "shot":
            pdeps = self.core.projects.getShotDepartments()
        else:
            return tasks

        for dep in pdeps:
            if dep["abbreviation"] == department:
                tasks = sorted(tasks, key=lambda x: self.indexOf(x, dep["defaultTasks"]) if x in dep["defaultTasks"] else 999)
                break

        return tasks

    @err_catcher(name=__name__)
    def indexOf(self, val: Any, listData: List) -> int:
        """Get the index of a value in a list, or -1 if not found.
        
        Args:
            val: Value to find.
            listData: List to search.
            
        Returns:
            int: Index of value or -1 if not found.
        """
        try:
            idx = listData.index(val)
        except ValueError:
            idx = -1

        return idx

    @err_catcher(name=__name__)
    def getDependencies(self, path: str) -> List[str]:
        """Get dependencies for a version file.
        
        Args:
            path: Path to version file.
            
        Returns:
            List[str]: List of dependency paths.
        """
        info = self.core.getVersioninfoPath(path)
        deps = []
        source = self.core.getConfig("source scene", configPath=info)
        if source:
            deps.append(source)

        depPaths = (
            self.core.getConfig("dependencies", configPath=info) or []
        )
        deps += depPaths
        extFiles = (
            self.core.getConfig("externalFiles", configPath=info) or []
        )
        deps += extFiles

        return deps

    @err_catcher(name=__name__)
    def getCurrentDependencies(self) -> Dict[str, List[str]]:
        """Get dependencies from the currently open scene.
        
        Returns:
            Dict[str, List[str]]: Dict with 'dependencies' and 'externalFiles' keys.
        """
        deps = (
            getattr(self.core.appPlugin, "getImportPaths", lambda x: None)(self.core)
            or []
        )

        if type(deps) == str:
            deps = eval(deps.replace("\\", "/").replace("//", "/"))
        deps = [str(x[0]) for x in deps]

        extFiles = getattr(
            self.core.appPlugin, "sm_getExternalFiles", lambda x: [[], []]
        )(self.core)[0]
        extFiles = list(set(extFiles))

        return {"dependencies": deps, "externalFiles": extFiles}

    @err_catcher(name=__name__)
    def createEntity(self, entity: Dict[str, Any], dialog: Optional[Any] = None, frameRange: Optional[List[int]] = None, silent: bool = False, description: Optional[str] = None, preview: Optional[QPixmap] = None, metaData: Optional[Dict] = None) -> Dict[str, Any]:
        """Create an entity (asset, assetFolder, or shot).
        
        Args:
            entity: Entity dict with 'type' key.
            dialog: Optional dialog widget.
            frameRange: Optional frame range for shots.
            silent: If True, suppress UI dialogs.
            description: Optional description text.
            preview: Optional preview pixmap.
            metaData: Optional metadata dict.
            
        Returns:
            Dict[str, Any]: Result dict with entity and status info.
        """
        if entity["type"] == "asset":
            result = self.createAsset(entity, description=description, preview=preview, metaData=metaData, dialog=dialog)
        elif entity["type"] == "assetFolder":
            result = self.createAssetFolder(entity, dialog=dialog)
        elif entity["type"] == "shot":
            result = self.createShot(entity, frameRange=frameRange, preview=preview, metaData=metaData)
        else:
            return {}

        if not result:
            return {}

        if result.get("existed"):
            if entity["type"] in ["asset", "assetFolder"]:
                name = entity["asset_path"]
            elif entity["type"] == "shot":
                name = self.getShotName(entity)

            if self.isEntityOmitted(entity) and self.core.uiAvailable:
                msgText = (
                    "The %s %s already exists, but is marked as omitted.\n\nDo you want to restore it?"
                    % (entity["type"], name)
                )
                resultq = self.core.popupQuestion(msgText)

                if resultq == "Yes":
                    self.omitEntity(entity, omit=False)
            else:
                if not silent:
                    self.core.popup("The %s already exists:\n\n%s" % (entity["type"], name))

        if result.get("error"):
            self.core.popup(result["error"])

        return result

    @err_catcher(name=__name__)
    def createAssetFolder(self, entity: Dict[str, Any], dialog: Optional[Any] = None) -> Dict[str, Any]:
        """Create an asset folder entity.
        
        Args:
            entity: Asset folder entity dict with 'asset_path' key.
            dialog: Optional dialog widget.
            
        Returns:
            Dict[str, Any]: Result dict with entity and 'existed' flag.
        """
        fullAssetPath = os.path.join(self.core.assetPath, entity["asset_path"])

        existed = os.path.exists(fullAssetPath)
        if not os.path.exists(fullAssetPath):
            os.makedirs(fullAssetPath)

        if not existed:
            self.core.callback(
                name="onAssetFolderCreated",
                args=[self, entity, dialog],
            )

        result = {
            "entity": entity,
            "existed": existed,
        }
        logger.debug("assetFolder created: %s" % result)
        return result

    @err_catcher(name=__name__)
    def createAsset(self, entity: Dict[str, Any], description: Optional[str] = None, preview: Optional[QPixmap] = None, metaData: Optional[Dict] = None, dialog: Optional[Any] = None) -> Dict[str, Any]:
        """Create an asset entity with all necessary folders.
        
        Args:
            entity: Asset entity dict with 'asset_path' key.
            description: Optional asset description.
            preview: Optional preview pixmap.
            metaData: Optional metadata dict.
            dialog: Optional dialog widget.
            
        Returns:
            Dict[str, Any]: Result dict with entity, 'existed' flag, and optional 'error'.
        """
        fullAssetPath = os.path.join(self.core.assetPath, entity["asset_path"])

        assetName = self.getAssetNameFromPath(fullAssetPath)
        if not self.isValidAssetName(assetName):
            return {"error": "Invalid assetname."}

        existed = os.path.exists(fullAssetPath)
        if existed and self.getTypeFromAssetPath(fullAssetPath) == "folder":
            return {"error": "A folder with this name exists already."}

        for f in self.entityFolders["asset"]:
            aFolder = os.path.join(fullAssetPath, f)
            if not os.path.exists(aFolder):
                try:
                    os.makedirs(aFolder, exist_ok=True)
                except Exception as e:
                    return {"error": "Failed to create folder:\n\n%s\n\nError: %s" % (aFolder, str(e))}

        assetDep = self.core.projects.getResolvedProjectStructurePath(
            "departments", context=entity
        )
        assetProducts = self.core.projects.getResolvedProjectStructurePath(
            "products", context=entity
        )
        asset3dRenders = self.core.projects.getResolvedProjectStructurePath(
            "3drenders", context=entity
        )
        asset2dRenders = self.core.projects.getResolvedProjectStructurePath(
            "2drenders", context=entity
        )
        assetPlayblasts = self.core.projects.getResolvedProjectStructurePath(
            "playblasts", context=entity
        )
        assetFolders = [
            os.path.dirname(assetDep),
            os.path.dirname(assetProducts),
            os.path.dirname(asset3dRenders),
            os.path.dirname(asset2dRenders),
            os.path.dirname(assetPlayblasts),
        ]

        for assetFolder in assetFolders:
            if not os.path.exists(assetFolder):
                try:
                    os.makedirs(assetFolder, exist_ok=True)
                except Exception as e:
                    return {"error": "Failed to create folder:\n\n%s\n\nError: %s" % (assetFolder, str(e))}

        if description:
            self.core.entities.setAssetDescription(assetName, description)

        if preview:
            self.core.entities.setEntityPreview(entity, preview)

        if metaData:
            self.core.entities.setMetaData(entity, metaData)

        if not existed:
            self.core.callback(
                name="onAssetCreated",
                args=[self, entity, dialog],
            )

        result = {
            "entity": entity,
            "existed": existed,
        }
        logger.debug("asset created: %s" % result)
        return result

    @err_catcher(name=__name__)
    def createShot(self, entity: Dict[str, Any], frameRange: Optional[List[int]] = None, preview: Optional[QPixmap] = None, metaData: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a shot entity with all necessary folders.
        
        Args:
            entity: Shot entity dict with shot info.
            frameRange: Optional two-element list [start, end] frame range.
            preview: Optional preview pixmap.
            metaData: Optional metadata dict.
            
        Returns:
            Dict[str, Any]: Result dict with entity and 'existed' flag.
        """
        sBase = self.core.getEntityPath(entity=entity)
        existed = os.path.exists(sBase)

        for f in self.entityFolders["shot"]:
            sFolder = os.path.join(sBase, f)
            while True:
                try:
                    if not os.path.exists(sFolder):
                        os.makedirs(sFolder)
                except Exception as e:
                    msg = "Failed to create folder:\n\n%s\n\nError: %s" % (sFolder, str(e))
                    result = self.core.popupQuestion(msg, buttons=["Retry", "Cancel"], escapeButton="Cancel", icon=QMessageBox.Warning)
                    if result == "Retry":
                        continue

                break

        shotDep = self.core.projects.getResolvedProjectStructurePath(
            "departments", context=entity
        )
        shotProducts = self.core.projects.getResolvedProjectStructurePath(
            "products", context=entity
        )
        shot3dRenders = self.core.projects.getResolvedProjectStructurePath(
            "3drenders", context=entity
        )
        shot2dRenders = self.core.projects.getResolvedProjectStructurePath(
            "2drenders", context=entity
        )
        shotPlayblasts = self.core.projects.getResolvedProjectStructurePath(
            "playblasts", context=entity
        )
        shotFolders = [
            os.path.dirname(shotDep),
            os.path.dirname(shotProducts),
            os.path.dirname(shot3dRenders),
            os.path.dirname(shot2dRenders),
            os.path.dirname(shotPlayblasts),
        ]

        for shotFolder in shotFolders:
            while "@" in os.path.basename(shotFolder):
                shotFolder = os.path.dirname(shotFolder)

            if not os.path.exists(shotFolder):
                while not os.path.exists(shotFolder):
                    try:
                        os.makedirs(shotFolder)
                    except Exception as e:
                        msg = "Failed to create folder:\n\n%s\n\nError: %s" % (shotFolder, str(e))
                        result = self.core.popupQuestion(msg, buttons=["Retry", "Cancel"], escapeButton="Cancel", icon=QMessageBox.Warning)
                        if result == "Retry":
                            continue
                        else:
                            return {"error": msg}

        if frameRange:
            self.setShotRange(entity, frameRange[0], frameRange[1])

        if preview:
            self.core.entities.setEntityPreview(entity, preview)

        if metaData:
            self.core.entities.setMetaData(entity, metaData)

        if not existed:
            self.core.callback(name="onShotCreated", args=[self, entity])

        result = {
            "entity": entity,
            "entityPath": sBase,
            "existed": existed,
        }
        logger.debug("shot created: %s" % result)
        return result

    @err_catcher(name=__name__)
    def createDepartment(self, department: str, entity: Dict[str, Any], stepPath: str = "", createCat: bool = True) -> str:
        """Create a department folder for an entity.
        
        Args:
            department: Department name.
            entity: Entity dict.
            stepPath: Optional base path for department. If empty, uses entity path.
            createCat: If True, create a default category/task in the department.
            
        Returns:
            str: Path to the created department folder.
        """
        if not stepPath:
            stepPath = self.core.getEntityPath(entity=entity, step=department)

        if not os.path.exists(stepPath):
            existed = False
            try:
                os.makedirs(stepPath)
            except:
                self.core.popup("The department %s could not be created.\n\n%s" % (department, stepPath))
                return False
        else:
            existed = True
            logger.debug("step already exists: %s" % stepPath)

        settings = {
            "createDefaultCategory": (
                entity["type"] == "shot"
                or self.core.compareVersions(self.core.projectVersion, "v1.2.1.6")
                != "lower"
            )
            and createCat
        }

        self.core.callback(
            name="onDepartmentCreated",
            args=[self, entity, department, stepPath, settings],
        )

        if not existed:
            logger.debug("department created %s" % stepPath)

        if settings["createDefaultCategory"]:
            paths = self.createDefaultCat(entity, department)
            return paths

        return stepPath

    @err_catcher(name=__name__)
    def getLongDepartmentName(self, entity: str, abbreviation: str) -> Optional[str]:
        """Get the full name of a department from its abbreviation.
        
        Args:
            entity: Entity type ('asset', 'shot', or 'sequence').
            abbreviation: Department abbreviation.
            
        Returns:
            Optional[str]: Full department name or None if not found.
        """
        if entity == "asset":
            deps = self.core.projects.getAssetDepartments()
        elif entity in ["shot", "sequence"]:
            deps = self.core.projects.getShotDepartments()
        else:
            return

        fullNames = [dep["name"] for dep in deps if dep["abbreviation"] == abbreviation]
        if fullNames:
            return fullNames[0]

    @err_catcher(name=__name__)
    def getDepartmentAbbreviation(self, entity: str, department: str) -> Optional[str]:
        """Get the abbreviation of a department from its full name.
        
        Args:
            entity: Entity type ('asset', 'shot', or 'sequence').
            department: Full department name.
            
        Returns:
            Optional[str]: Department abbreviation or None if not found.
        """
        if entity == "asset":
            deps = self.core.projects.getAssetDepartments()
        elif entity in ["shot", "sequence"]:
            deps = self.core.projects.getShotDepartments()

        abbrvs = [dep["abbreviation"] for dep in deps if dep["name"] == department]
        if abbrvs:
            return abbrvs[0]

    @err_catcher(name=__name__)
    def getPrismDepartmentFromCustomName(self, name: str) -> Optional[str]:
        """Convert custom department names to standard Prism department names.
        
        Maps various common abbreviations and names to standard Prism departments
        (Concept, Modeling, Surfacing, Rigging, Layout, Animation, FX, Lighting, Compositing).
        Checks environment variables for custom names.
        
        Args:
            name: Department name or abbreviation (case-insensitive).
            
        Returns:
            Optional[str]: Standard Prism department name or original name if no match.
        """
        name = name.lower()

        cptNames = ["cpt", "concept"]
        if os.getenv("PRISM_CONCEPT_NAME"):
            cptNames.append(os.getenv("PRISM_CONCEPT_NAME").lower())

        if name in cptNames:
            return "Concept"

        modNames = ["mod", "modeling"]
        if os.getenv("PRISM_MODELING_NAME"):
            modNames.append(os.getenv("PRISM_MODELING_NAME").lower())

        if name in modNames:
            return "Modeling"

        surfNames = ["surf", "surfacing"]
        if os.getenv("PRISM_SURFACING_NAME"):
            surfNames.append(os.getenv("PRISM_SURFACING_NAME").lower())

        if name in surfNames:
            return "Surfacing"

        rigNames = ["rig", "rigging"]
        if os.getenv("PRISM_RIGGING_NAME"):
            rigNames.append(os.getenv("PRISM_RIGGING_NAME").lower())

        if name in rigNames:
            return "Rigging"

        layNames = ["lay", "layout"]
        if os.getenv("PRISM_LAYOUT_NAME"):
            layNames.append(os.getenv("PRISM_LAYOUT_NAME").lower())

        if name in layNames:
            return "Layout"

        anmNames = ["anm", "animation", "anim"]
        if os.getenv("PRISM_ANIMATION_NAME"):
            anmNames.append(os.getenv("PRISM_ANIMATION_NAME").lower())

        if name in anmNames:
            return "Animation"

        cfxNames = ["cfx", "charfx", "characterfx", "creaturefx"]
        if os.getenv("PRISM_CHARFX_NAME"):
            cfxNames.append(os.getenv("PRISM_CHARFX_NAME").lower())

        if name in cfxNames:
            return "CharFX"

        fxNames = ["fx", "effects"]
        if os.getenv("PRISM_FX_NAME"):
            anmNames.append(os.getenv("PRISM_FX_NAME").lower())

        if name in fxNames:
            return "FX"

        lgtNames = ["lgt", "lighting"]
        if os.getenv("PRISM_LIGHTING_NAME"):
            lgtNames.append(os.getenv("PRISM_LIGHTING_NAME").lower())

        if name in lgtNames:
            return "Lighting"

        cmpNames = ["cmp", "comp", "compositing"]
        if os.getenv("PRISM_COMPOSITING_NAME"):
            cmpNames.append(os.getenv("PRISM_COMPOSITING_NAME").lower())

        if name in cmpNames:
            return "Compositing"

        newName = self.getLongDepartmentName("asset", name) or self.getLongDepartmentName("shot", name)
        if newName and newName != name:
            name = self.getPrismDepartmentFromCustomName(newName)

        return name

    @err_catcher(name=__name__)
    def getDepartmentIcon(self, department: str) -> QIcon:
        """Get the icon for a department.
        
        Args:
            department: Department name.
            
        Returns:
            QIcon: Icon for the department.
        """
        if department in self.depIcons:
            return self.depIcons[department]

        path = os.path.join(self.core.projects.getPipelineFolder(), "Icons", department + ".png")
        icon = QIcon(path)
        self.depIcons[department] = icon
        return icon

    @err_catcher(name=__name__)
    def getDefaultTasksForDepartment(self, entity: str, department: str) -> Optional[List[str]]:
        """Get the default tasks for a department.
        
        Args:
            entity: Entity type string ('asset' or 'shot').
            department: Department name/abbreviation.
            
        Returns:
            Optional[List[str]]: List of default task names or None if department doesn't exist.
        """
        if entity == "asset":
            existingDeps = self.core.projects.getAssetDepartments()
        elif entity in ["shot", "sequence"]:
            existingDeps = self.core.projects.getShotDepartments()

        if department not in [d["abbreviation"] for d in existingDeps]:
            msgStr = (
                "Department '%s' doesn't exist in the project config. Couldn't get default task."
                % department
            )
            logger.debug(msgStr)
            return

        tasks = [d for d in existingDeps if d["abbreviation"] == department][0]["defaultTasks"]
        if not isinstance(tasks, list):
            tasks = [tasks]

        return tasks

    @err_catcher(name=__name__)
    def createDefaultCat(self, entity: Dict[str, Any], step: str) -> Optional[List[str]]:
        """Create default categories/tasks for a department.
        
        Args:
            entity: Entity dict with 'type' key.
            step: Department name.
            
        Returns:
            Optional[List[str]]: List of created category paths or None if no tasks defined.
        """
        tasks = self.getDefaultTasksForDepartment(entity["type"], step)
        if not tasks:
            return

        paths = []
        for category in tasks:
            paths.append(self.createCategory(entity, step, category))

        return paths

    @err_catcher(name=__name__)
    def createCategory(self, entity: Dict[str, Any], step: str, category: str) -> Optional[str]:
        """Create a category/task folder for an entity and department.
        
        Args:
            entity: Entity dict.
            step: Department name.
            category: Task/category name.
            
        Returns:
            Optional[str]: Path to created category or None if creation failed.
        """
        catPath = self.core.getEntityPath(entity=entity, step=step, category=category)
        if not os.path.exists(catPath):
            try:
                os.makedirs(catPath)
            except:
                self.core.popup("The directory %s could not be created" % catPath)
                return
            else:
                self.core.callback(
                    name="onTaskCreated",
                    args=[self, entity, step, category, catPath],
                )

                ctx = entity.copy()
                ctx["department"] = step
                presetPath = self.getDefaultPresetSceneForContext(ctx)
                if presetPath:
                    self.createSceneFromPreset(
                        entity,
                        presetPath,
                        step=step,
                        category=category,
                        comment=os.path.basename(os.path.splitext(presetPath)[0])
                    )

            logger.debug("task created %s" % catPath)
        else:
            logger.debug("task already exists: %s" % catPath)

        return catPath

    @err_catcher(name=__name__)
    def getDefaultPresetSceneForContext(self, context: Dict[str, Any]) -> Optional[str]:
        """Get the default preset scene file for a given context.
        
        Checks callbacks and default preset scene settings to find a matching
        preset scene for the context (entity, department, task).
        
        Args:
            context: Context dict with entity and task information.
            
        Returns:
            Optional[str]: Path to preset scene file or None if not found.
        """
        kwargs = {
            "context": context,
        }
        result = self.core.callback("getDefaultPresetSceneForContext", **kwargs)
        filename = ""
        for res in result:
            if res and "filename" in res:
                filename = res["filename"]

        if filename:
            presetPath = self.getScenePresetPathFromName(filename)
            return presetPath

        defaults = self.getDefaultPresetScenes()
        preset = self.getItemMatchingContext(defaults, context)
        if not preset:
            return

        presetName = preset["name"]
        presetPath = self.getScenePresetPathFromName(presetName)
        if presetPath:
            return presetPath

    @err_catcher(name=__name__)
    def getDefaultPresetScenes(self) -> List[Dict]:
        """Get list of default preset scenes from project configuration.
        
        Returns:
            List[Dict]: List of preset scene definitions with 'name' key.
        """
        presets = self.core.getConfig("globals", "presetScenes", config="project") or []
        presets = [p for p in presets if p.get("name")]
        return presets

    @err_catcher(name=__name__)
    def doesContextMatchTaskFilters(self, taskFilters: Dict, context: Dict[str, Any]) -> bool:
        """Check if a context matches the specified task filters.
        
        Evaluates whether the context (entity type, name, department) matches
        the filter patterns defined in taskFilters.
        
        Args:
            taskFilters: Filter dict with 'entities' and 'departments' keys.
            context: Context dict with entity and task information.
            
        Returns:
            bool: True if context matches filters.
        """
        for entity in taskFilters.get("entities", []):
            if entity != "*":
                entityData = entity.split(":")
                if entityData[0] != "*" and context.get("type") != entityData[0]:
                    continue

                entityName = re.escape(entityData[1]).replace("\\*", ".*")
                if context["type"] == "asset":
                    if not re.match("^%s$" % entityName, context.get("asset_path", "")):
                        continue

                elif context["type"] == "shot":
                    if not re.match("^%s$" % entityName, self.getShotName(context)):
                        continue

            for department in taskFilters["departments"]:
                if department != "*":
                    departmentName = re.escape(department).replace("\\*", ".*")
                    ctxDep = context.get("department", "")
                    if not ctxDep or not re.match("^%s$" % departmentName, ctxDep):
                        continue

                for task in taskFilters["tasks"]:
                    if task != "*":
                        taskName = re.escape(task).replace("\\*", ".*")
                        ctxTask = context.get("task", "")
                        if not ctxTask or not re.match("^%s$" % taskName, ctxTask):
                            continue

                    if taskFilters.get("useExpression"):
                        result = self.validateExpression(taskFilters.get("expression"))
                        if not result or not result["valid"] or not result["result"]:
                            continue

                    return True

        return False

    @err_catcher(name=__name__)
    def getItemMatchingContext(self, items: List[Dict], context: Dict[str, Any]) -> Optional[Dict]:
        """Find the first item in a list that matches the given context.
        
        Args:
            items: List of items with 'taskFilter' expressions.
            context: Context dict with entity and task information.
            
        Returns:
            Optional[Dict]: First matching item or None if no match found.
        """
        """Get the first item that matches the given context.
        
        Args:
            items: List of items with 'dftTasks' keys.
            context: Context dict to match against.
            
        Returns:
            Optional[Dict]: Matching item or None.
        """
        for item in items:
            taskFilters = item.get("dftTasks", {})
            if self.doesContextMatchTaskFilters(taskFilters, context):
                return item

    @err_catcher(name=__name__)
    def validateExpression(self, expression: str) -> Dict[str, Any]:
        """Validate a task filter expression.
        
        Parses and validates filter expressions used to match tasks against contexts.
        Expression format: "entity:name|department:dep_name".
        
        Args:
            expression: Filter expression string.
            
        Returns:
            Dict[str, Any]: Parsed filter dict with 'entities' and 'departments' lists.
        """
        """Validate a Python expression for task filtering.
        
        Args:
            expression: Python code string to validate.
            
        Returns:
            Dict[str, Any]: Dict with 'valid' bool and either 'result' or 'error'.
        """
        context = {}
        core = self.core
        lcls = locals().copy()
        try:
            exec(expression, lcls, None)
        except Exception as e:
            print(e)
            result = {"valid": False, "error": str(e)}
            return result
        else:
            if "result" in lcls:
                exvar = bool(lcls["result"])
                result = {"valid": True, "result": exvar}
                return result

        result = {"valid": False, "error": "Make sure \"result\" is defined."}
        return result

    @err_catcher(name=__name__)
    def createTasksFromPreset(self, entity: Dict[str, Any], preset: Optional[Dict] = None, presetName: Optional[str] = None) -> Optional[List[str]]:
        """Create tasks for an entity from a task preset.
        
        Args:
            entity: Entity dict.
            preset: Optional preset dict with 'tasks' list.
            presetName: Optional preset name to load if preset not provided.
            
        Returns:
            Optional[List[str]]: List of created task paths or None if no preset found.
        """
        """Create tasks from a preset configuration.
        
        Args:
            entity: Entity dict.
            preset: Optional preset dict with 'departments' key.
            presetName: Optional preset name to load if preset not provided.
            
        Returns:
            Optional[List[str]]: List of created task paths or None if invalid preset.
        """
        if not preset and presetName:
            if entity.get("type") == "asset":
                presets = self.core.projects.getAssetTaskPresets()
            else:
                presets = self.core.projects.getShotTaskPresets()

            for p in presets:
                if p.get("name") == presetName:
                    preset = p
                    break
            else:
                self.core.popup("Invalid preset name: %s" % presetName)
                return

        logger.debug("creating tasks from preset - entity: %s - preset: %s" % (entity, preset))
        paths = []
        for dep in preset.get("departments", []):
            abbrv = self.getDepartmentAbbreviation(entity.get("type"), dep["name"])
            if not abbrv:
                continue

            self.createDepartment(abbrv, entity, createCat=False)
            for task in dep.get("tasks", []):
                paths.append(self.createCategory(entity, abbrv, task))

        return paths

    @err_catcher(name=__name__)
    def getTaskDataPath(self, entity: Dict[str, Any], department: str, task: str) -> str:
        """Get the path to the task data file.
        
        Args:
            entity: Entity dict.
            department: Department name.
            task: Task name.
            
        Returns:
            str: Path to task data config file.
        """
        """Get the path to the task info configuration file.
        
        Args:
            entity: Entity dict.
            department: Department name.
            task: Task name.
            
        Returns:
            str: Path to task info file.
        """
        taskPath = self.core.getEntityPath(entity=entity, step=department, category=task)
        filename = "info" + self.core.configs.getProjectExtension()
        infoPath = os.path.join(taskPath, filename)
        return infoPath

    @err_catcher(name=__name__)
    def getTaskData(self, entity: Dict[str, Any], department: str, task: str) -> Dict:
        """Get the stored data for a task.
        
        Args:
            entity: Entity dict.
            department: Department name.
            task: Task name.
            
        Returns:
            Dict: Task data dict (empty if file doesn't exist).
        """
        """Get task configuration data.
        
        Args:
            entity: Entity dict.
            department: Department name.
            task: Task name.
            
        Returns:
            Dict: Task configuration data.
        """
        infoPath = self.getTaskDataPath(entity, department, task)
        data = self.core.getConfig(configPath=infoPath)
        return data

    @err_catcher(name=__name__)
    def setTaskData(self, entity: Dict[str, Any], department: str, task: str, key: str, val: Any) -> bool:
        """Set a specific data value for a task.
        
        Args:
            entity: Entity dict.
            department: Department name.
            task: Task name.
            key: Data key to set.
            val: Value to set.
            
        Returns:
            bool: True if successful.
        """
        """Set task configuration data.
        
        Args:
            entity: Entity dict.
            department: Department name.
            task: Task name.
            key: Configuration key.
            val: Configuration value.
            
        Returns:
            bool: Always True.
        """
        infoPath = self.getTaskDataPath(entity, department, task)
        self.core.setConfig(key, val=val, configPath=infoPath)
        return True

    @err_catcher(name=__name__)
    def omitEntity(self, entity: Dict[str, Any], omit: bool = True) -> None:
        """Mark an entity as omitted (hidden) or restore it.
        
        Omitted entities are hidden from entity lists and browsers.
        
        Args:
            entity: Entity dict with 'type' and entity identifiers.
            omit: If True, omit the entity. If False, restore it.
        """
        """Mark an entity as omitted/hidden or restore it.
        
        Args:
            entity: Entity dict with 'type' key.
            omit: If True, omit the entity; if False, restore it.
        """
        if entity["type"] == "assetFolder":
            entityType = "asset"
        else:
            entityType = entity["type"]

        if entityType == "asset":
            entityName = entity["asset_path"]
        elif entityType == "shot":
            entityName = self.core.entities.getShotName(entity)

        omits = self.core.getConfig(entityType, config="omit")
        if omit:
            if entityType == "asset":
                if not omits:
                    omits = []

                if entityName not in omits:
                    omits.append(entityName)
            elif entityType == "shot":
                if not omits:
                    omits = {}

                if not entity["sequence"] in omits:
                    omits[entity["sequence"]] = []

                if entity["shot"] not in omits[entity["sequence"]]:
                    omits[entity["sequence"]].append(entity["shot"])

            self.core.setConfig(entityType, val=omits, config="omit")
            logger.debug("omitted %s %s" % (entityType, entityName))
        else:
            if not omits:
                return False

            if entityType == "asset":
                if entityName.replace("\\", "/") in omits:
                    omits.remove(entityName.replace("\\", "/"))
                elif entityName.replace("/", "\\") in omits:
                    omits.remove(entityName.replace("/", "\\"))
                else:
                    return False

            elif entityType == "shot":
                if entity["sequence"] not in omits:
                    return False

                if entity["shot"] not in omits[entity["sequence"]]:
                    return False

                omits[entity["sequence"]].remove(entity["shot"])

            self.core.setConfig(entityType, val=omits, config="omit")
            logger.debug("restored %s %s" % (entityType, entityName))

        self.refreshOmittedEntities()
        return True

    @err_catcher(name=__name__)
    def setComment(self, filepath: str, comment: str) -> str:
        """Set a comment for a scenefile.
        
        Args:
            filepath: Path to scenefile.
            comment: Comment text.
            
        Returns:
            str: The comment that was set.
        """
        """Set or update the comment for a scenefile.
        
        Args:
            filepath: Path to scenefile.
            comment: Comment text to set.
            
        Returns:
            str: Path to the renamed file with comment.
        """
        newPath = ""
        data = self.core.getScenefileData(filepath)

        if self.core.useLocalFiles:
            localPath = filepath.replace(
                self.core.projectPath, self.core.localProjectPath
            )
            if os.path.exists(localPath):
                localData = self.core.getScenefileData(localPath)
                scenedata = {"entity": localData}
                if "department" in localData:
                    scenedata["department"] = localData["department"]

                if "task" in localData:
                    scenedata["task"] = localData["task"]

                if "extension" in localData:
                    scenedata["extension"] = localData["extension"]

                if "version" in localData:
                    scenedata["version"] = localData["version"]

                if "user" in localData:
                    scenedata["user"] = localData["user"]

                scenedata["comment"] = comment
                if "department" in localData:
                    newPath = self.core.generateScenePath(**scenedata)
                    self.core.copySceneFile(localPath, newPath, mode="move")
                else:
                    newPath = localPath

                self.setScenefileInfo(newPath, "comment", comment)

        if os.path.exists(filepath):
            scenedata = {"entity": data}
            if "department" in data:
                scenedata["department"] = data["department"]

            if "task" in data:
                scenedata["task"] = data["task"]

            if "extension" in data:
                scenedata["extension"] = data["extension"]

            if "version" in data:
                scenedata["version"] = data["version"]

            if "user" in data:
                scenedata["user"] = data["user"]

            scenedata["comment"] = comment
            if "department" in data:
                newPath = self.core.generateScenePath(**scenedata)
                self.core.copySceneFile(filepath, newPath, mode="move")
            else:
                newPath = filepath

            self.setScenefileInfo(newPath, "comment", comment)

        return newPath

    @err_catcher(name=__name__)
    def setDescription(self, filepath: str, description: str) -> None:
        """Set a description for a scenefile.
        
        Args:
            filepath: Path to scenefile.
            description: Description text.
        """
        """Set the description for a scenefile.
        
        Args:
            filepath: Path to scenefile.
            description: Description text to set.
        """
        self.setScenefileInfo(filepath, "description", description)

    @err_catcher(name=__name__)
    def getAssetDescription(self, assetName: str, projectPath: Optional[str] = None) -> str:
        """Get the description for an asset.
        
        Args:
            assetName: Asset name.
            projectPath: Optional specific project path.
            
        Returns:
            str: Asset description or empty string if not found.
        """
        pipeFolder = self.core.projects.getPipelineFolder()
        if projectPath:
            pipeFolder = pipeFolder.replace(os.path.normpath(self.core.projectPath), projectPath)

        assetFile = os.path.join(
            pipeFolder,
            "Assetinfo",
            "assetInfo" + self.core.configs.getProjectExtension(),
        )

        description = ""

        assetInfos = self.core.getConfig(configPath=assetFile)
        if not assetInfos:
            assetInfos = {}

        if assetName in assetInfos and "description" in assetInfos[assetName]:
            description = assetInfos[assetName]["description"]

        return description

    @err_catcher(name=__name__)
    def setAssetDescription(self, assetName: str, description: str) -> None:
        """Set the description for an asset.
        
        Args:
            assetName: Asset name.
            description: Description text.
        """
        assetFile = os.path.join(
            self.core.projects.getPipelineFolder(),
            "Assetinfo",
            "assetInfo" + self.core.configs.getProjectExtension(),
        )
        assetInfos = self.core.getConfig(configPath=assetFile)
        if not assetInfos:
            assetInfos = {}

        if assetName not in assetInfos:
            assetInfos[assetName] = {}

        assetInfos[assetName]["description"] = description

        self.core.setConfig(data=assetInfos, configPath=assetFile)

    @err_catcher(name=__name__)
    def getMetaData(self, entity: Dict[str, Any], projectPath: Optional[str] = None) -> Dict:
        """Get the metadata for an entity.
        
        Args:
            entity: Entity dict with 'type' and entity identifiers.
            projectPath: Optional specific project path.
            
        Returns:
            Dict: Metadata dict (empty if not found).
        """
        metadata = {}
        if not entity:
            return metadata

        if entity.get("type") == "asset":
            if projectPath:
                pipeFolder = self.core.projects.getPipelineFolder()
                pipeFolder = pipeFolder.replace(os.path.normpath(self.core.projectPath), projectPath)
                assetFile = os.path.join(
                    pipeFolder,
                    "Assetinfo",
                    "assetInfo" + self.core.configs.getProjectExtension(),
                )
                data = self.core.getConfig(configPath=assetFile) or {}
            else:
                data = self.core.getConfig(config="assetinfo") or {}

            if "assets" not in data:
                return metadata

            if "asset_path" not in entity:
                return metadata

            entityName = self.core.entities.getAssetNameFromPath(entity["asset_path"])
            if entityName not in data["assets"]:
                return metadata

            metadata = data["assets"][entityName].get("metadata", {})

        elif entity.get("type") == "shot":
            data = self.core.getConfig(config="shotinfo") or {}
            if "shots" not in data:
                return metadata

            if entity.get("sequence", "") not in data["shots"]:
                return metadata

            if entity["shot"] not in data["shots"][entity["sequence"]]:
                return metadata

            metadata = data["shots"][entity["sequence"]][entity["shot"]].get("metadata", {})

        return metadata

    @err_catcher(name=__name__)
    def setMetaData(self, entity: Optional[Dict[str, Any]] = None, metaData: Optional[Dict] = None, entities: Optional[List[Dict[str, Any]]] = None, metaDatas: Optional[List[Dict]] = None) -> None:
        """Set metadata for one or more entities.
        
        Args:
            entity: Single entity dict (use with metaData).
            metaData: Metadata dict for single entity.
            entities: List of entity dicts (use with metaDatas).
            metaDatas: List of metadata dicts corresponding to entities.
        """
        if entity and not entities:
            entities = [entity]
            metaDatas = [metaData]

        assetConfig = None
        shotConfig = None
        for idx, entity in enumerate(entities):
            metaData = metaDatas[idx]
            if entity["type"] == "asset":
                if assetConfig is None:
                    assetConfig = self.core.getConfig(config="assetinfo", allowCache=False) or {}

                if "assets" not in assetConfig:
                    assetConfig["assets"] = {}

                entityName = self.core.entities.getAssetNameFromPath(entity["asset_path"])
                if entityName not in assetConfig["assets"]:
                    assetConfig["assets"][entityName] = {}

                assetConfig["assets"][entityName]["metadata"] = metaData
            elif entity["type"] == "shot":
                if shotConfig is None:
                    shotConfig = self.core.getConfig(config="shotinfo", allowCache=False) or {}

                if "shots" not in shotConfig:
                    shotConfig["shots"] = {}

                if entity["sequence"] not in shotConfig["shots"]:
                    shotConfig["shots"][entity["sequence"]] = {}

                if entity["shot"] not in shotConfig["shots"][entity["sequence"]]:
                    shotConfig["shots"][entity["sequence"]][entity["shot"]] = {}

                shotConfig["shots"][entity["sequence"]][entity["shot"]]["metadata"] = metaData
        
        if assetConfig is not None:
            self.core.setConfig(data=assetConfig, config="assetinfo", updateNestedData=False)

        if shotConfig is not None:
            self.core.setConfig(data=shotConfig, config="shotinfo", updateNestedData=False)

    @err_catcher(name=__name__)
    def deleteShot(self, shotName: str) -> None:
        """Delete a shot and all its files.
        
        Attempts to remove the shot folder from both global and local locations.
        Prompts user to retry if files are locked by another program.
        
        Args:
            shotName: Name of the shot to delete.
        """
        shotPath = self.core.getEntityPath(shot=shotName)
        while True:
            try:
                if os.path.exists(shotPath):
                    shutil.rmtree(shotPath)
                if self.core.useLocalFiles:
                    lShotPath = shotPath.replace(
                        self.core.projectPath, self.core.localProjectPath
                    )
                    if os.path.exists(lShotPath):
                        shutil.rmtree(lShotPath)
                break
            except Exception as e:
                msg = (
                    'Permission denied.\nAnother programm uses files in the shotfolder.\n\nThe shot "%s" could not be deleted completly.\n\n%s'
                    % (shotName, str(e)),
                )
                result = self.core.popupQuestion(msg, buttons=["Retry", "Cancel"])
                if result == "Cancel":
                    self.core.popup("Deleting shot canceled.")
                    break

    @err_catcher(name=__name__)
    def renameEpisode(self, curEpName: str, newEpName: str, locations: Optional[List[str]] = None) -> None:
        """Rename an episode and update all related paths and configs.
        
        Updates episode folder names, nested folder references, and config files.
        Handles both global and local locations.
        
        Args:
            curEpName: Current episode name.
            newEpName: New episode name.
            locations: Optional list of locations to rename ('global', 'local'). If None, uses all.
        """
        epFolder = os.path.normpath(self.core.getEntityPath(entity={"type": "episode", "episode": curEpName}))
        newEpFolder = os.path.normpath(self.core.getEntityPath(entity={"type": "episode", "episode": newEpName}))
        epFolders = {}
        if not locations or "global" in locations:
            epFolders[epFolder] = newEpFolder

        if self.core.useLocalFiles:
            if not locations or "local" in locations:
                lEpFolder = epFolder.replace(
                    self.core.projectPath, self.core.localProjectPath
                )
                newLEpFolder = newEpFolder.replace(
                    self.core.projectPath, self.core.localProjectPath
                )
                epFolders[lEpFolder] = newLEpFolder

        curShots = self.getShotsFromEpisode(curEpName)

        while True:
            try:
                for k in epFolders:
                    if os.path.exists(k):
                        os.rename(k, epFolders[k])

                    cwd = os.getcwd()
                    for i in os.walk(epFolders[k]):
                        os.chdir(i[0])
                        for k in i[1]:
                            if curEpName in k:
                                os.rename(k, k.replace(curEpName, newEpName))
                        for k in i[2]:
                            if os.path.splitext(k)[1] == self.core.configs.preferredExtension:
                                filepath = os.path.join(i[0], k)
                                fepName = self.core.getConfig("episode", configPath=filepath)
                                if fepName == curEpName:
                                    self.core.setConfig("episode", val=newEpName, configPath=filepath)

                            if curEpName in k:
                                os.rename(k, k.replace(curEpName, newEpName))
                    os.chdir(cwd)

                break

            except Exception as e:
                logger.debug(e)
                msg = QMessageBox(
                    QMessageBox.Warning,
                    "Warning",
                    'Permission denied.\nAnother programm uses files in the epsidoefolder.\n\nThe episode "%s" could not be renamed to "%s" completly.\n\n%s'
                    % (curEpName, curEpName, str(e)),
                    QMessageBox.Cancel,
                )
                msg.addButton("Retry", QMessageBox.YesRole)
                self.core.parentWindow(msg)
                action = msg.exec_()

                if action != 0:
                    self.core.popup("Renaming episode canceled.")
                    return

        for curShot in curShots:
            oldPrvPath = self.getEntityPreviewPath(curShot)
            newShot = curShot.copy()
            newShot["episode"] = newEpName
            newPrvPath = self.getEntityPreviewPath(newShot)
            if os.path.exists(oldPrvPath):
                os.rename(oldPrvPath, newPrvPath)

        curRange = self.core.getConfig("shotRanges", config="shotinfo")
        if curRange and curEpName in curRange:
            cursRange = curRange[curEpName]
            del curRange[curEpName]
            curRange[newEpName] = cursRange
            self.core.setConfig("shotRanges", val=curRange, config="shotinfo")

        curRange = self.core.getConfig("shots", config="shotinfo")
        if curRange and curEpName in curRange:
            cursRange = curRange[curEpName]
            del curRange[curEpName]
            curRange[newEpName] = cursRange
            self.core.setConfig("shots", val=curRange, config="shotinfo")

    @err_catcher(name=__name__)
    def renameSequence(self, curSeqName: str, newSeqName: str, locations: Optional[List[str]] = None) -> None:
        """Rename a sequence and update all related paths and configs.
        
        Updates sequence folder names, nested folder references, and config files.
        Handles both global and local locations.
        
        Args:
            curSeqName: Current sequence name.
            newSeqName: New sequence name.
            locations: Optional list of locations to rename ('global', 'local'). If None, uses all.
        """
        seqFolder = os.path.normpath(self.core.getEntityPath(entity={"type": "sequence", "sequence": curSeqName}))
        newSeqFolder = os.path.normpath(self.core.getEntityPath(entity={"type": "sequence", "sequence": newSeqName}))
        seqFolders = {}
        if not locations or "global" in locations:
            seqFolders[seqFolder] = newSeqFolder

        if self.core.useLocalFiles:
            if not locations or "local" in locations:
                lSeqFolder = seqFolder.replace(
                    self.core.projectPath, self.core.localProjectPath
                )
                newLSeqFolder = newSeqFolder.replace(
                    self.core.projectPath, self.core.localProjectPath
                )
                seqFolders[lSeqFolder] = newLSeqFolder

        curShots = self.getShots(sequence=curSeqName)
        while True:
            try:
                for k in seqFolders:
                    if os.path.exists(k):
                        os.rename(k, seqFolders[k])

                    cwd = os.getcwd()
                    for i in os.walk(seqFolders[k]):
                        os.chdir(i[0])
                        for k in i[1]:
                            if curSeqName in k:
                                os.rename(k, k.replace(curSeqName, newSeqName))
                        for k in i[2]:
                            if os.path.splitext(k)[1] == self.core.configs.preferredExtension:
                                filepath = os.path.join(i[0], k)
                                fseqName = self.core.getConfig("sequence", configPath=filepath)
                                if fseqName == curSeqName:
                                    self.core.setConfig("sequence", val=newSeqName, configPath=filepath)

                            if curSeqName in k:
                                os.rename(k, k.replace(curSeqName, newSeqName))
                    os.chdir(cwd)

                break

            except Exception as e:
                logger.debug(e)
                msg = QMessageBox(
                    QMessageBox.Warning,
                    "Warning",
                    'Permission denied.\nAnother programm uses files in the sequencefolder.\n\nThe sequence "%s" could not be renamed to "%s" completly.\n\n%s'
                    % (curSeqName, curSeqName, str(e)),
                    QMessageBox.Cancel,
                )
                msg.addButton("Retry", QMessageBox.YesRole)
                self.core.parentWindow(msg)
                action = msg.exec_()

                if action != 0:
                    self.core.popup("Renaming sequence canceled.")
                    return

        for curShot in curShots:
            oldPrvPath = self.getEntityPreviewPath(curShot)
            newShot = curShot.copy()
            newShot["sequence"] = newSeqName
            newPrvPath = self.getEntityPreviewPath(newShot)
            if os.path.exists(oldPrvPath):
                os.rename(oldPrvPath, newPrvPath)

        curRange = self.core.getConfig("shotRanges", config="shotinfo")
        if curRange and curSeqName in curRange:
            cursRange = curRange[curSeqName]
            del curRange[curSeqName]
            curRange[newSeqName] = cursRange
            self.core.setConfig("shotRanges", val=curRange, config="shotinfo")

        curRange = self.core.getConfig("shots", config="shotinfo")
        if curRange and curSeqName in curRange:
            cursRange = curRange[curSeqName]
            del curRange[curSeqName]
            curRange[newSeqName] = cursRange
            self.core.setConfig("shots", val=curRange, config="shotinfo")

    @err_catcher(name=__name__)
    def renameShot(self, curShotData: Dict[str, str], newShotData: Dict[str, str], locations: Optional[List[str]] = None) -> None:
        """Rename a shot and update all related paths and configs.
        
        Updates shot folder names, nested folder references, and config files.
        Handles both global and local locations.
        
        Args:
            curShotData: Dict with current 'sequence' and 'shot' keys.
            newShotData: Dict with new 'sequence' and 'shot' keys.
            locations: Optional list of locations to rename ('global', 'local'). If None, uses all.
        """
        shotFolder = os.path.normpath(self.core.getEntityPath(entity=curShotData))
        newShotFolder = os.path.normpath(self.core.getEntityPath(entity=newShotData))
        shotFolders = {}
        if not locations or "global" in locations:
            shotFolders[shotFolder] = newShotFolder

        if self.core.useLocalFiles:
            if not locations or "local" in locations:
                lShotFolder = shotFolder.replace(
                    self.core.projectPath, self.core.localProjectPath
                )
                newLShotFolder = newShotFolder.replace(
                    self.core.projectPath, self.core.localProjectPath
                )
                shotFolders[lShotFolder] = newLShotFolder

        while True:
            try:
                for k in shotFolders:
                    if os.path.exists(k):
                        os.rename(k, shotFolders[k])

                    cwd = os.getcwd()
                    for i in os.walk(shotFolders[k]):
                        os.chdir(i[0])
                        for k in i[1]:
                            if curShotData["shot"] in k:
                                os.rename(k, k.replace(curShotData["shot"], newShotData["shot"]))
                        for k in i[2]:
                            if os.path.splitext(k)[1] == self.core.configs.preferredExtension:
                                filepath = os.path.join(i[0], k)
                                shotName = self.core.getConfig("shot", configPath=filepath)
                                if shotName == curShotData["shot"]:
                                    self.core.setConfig("shot", val=newShotData["shot"], configPath=filepath)

                            if curShotData["shot"] in k:
                                os.rename(k, k.replace(curShotData["shot"], newShotData["shot"]))

                    os.chdir(cwd)

                oldPrvPath = self.getEntityPreviewPath(curShotData)
                newPrvPath = self.getEntityPreviewPath(newShotData)
                if os.path.exists(oldPrvPath):
                    os.rename(oldPrvPath, newPrvPath)

                break

            except Exception as e:
                logger.debug(e)
                msg = 'Permission denied.\nAnother programm uses files in the shotfolder.\n\nThe shot "%s" could not be renamed to "%s" completly.\n\n%s' % (self.getShotName(curShotData), self.getShotName(newShotData), str(e))
                result = self.core.popupQuestion(msg, buttons=["Retry", "Cancel"], icon=QMessageBox.Warning)
                if result != "Retry":
                    self.core.popup("Renaming shot canceled.")
                    return

        curRange = self.core.getConfig("shotRanges", curShotData["sequence"], config="shotinfo")
        if curRange and curShotData["shot"] in curRange:
            cursRange = curRange[curShotData["shot"]]
            del curRange[curShotData["shot"]]
            curRange[newShotData["shot"]] = cursRange
            self.core.setConfig("shotRanges", curShotData["sequence"], curRange, config="shotinfo")

        curRange = self.core.getConfig("shots", curShotData["sequence"], config="shotinfo")
        if curRange and curShotData["shot"] in curRange:
            cursRange = curRange[curShotData["shot"]]
            del curRange[curShotData["shot"]]
            curRange[newShotData["shot"]] = cursRange
            self.core.setConfig("shots", curShotData["sequence"], curRange, config="shotinfo")

    @err_catcher(name=__name__)
    def getAssetSubFolders(self) -> List[str]:
        """Get the list of subfolders that identify an asset folder.
        
        Determines required subfolders based on project structure templates
        (departments, products, renders, playblasts).
        
        Returns:
            List[str]: List of subfolder names that should exist in asset folders.
        """
        subfolders = []

        template = self.core.projects.getTemplatePath("departments")
        template = template.replace("\\", "/")
        sceneFolder = template.split("/")[1]
        if sceneFolder:
            subfolders.append(sceneFolder)

        template = self.core.projects.getTemplatePath("products")
        template = template.replace("\\", "/")
        productFolder = template.split("/")[1]
        if productFolder:
            subfolders.append(productFolder)

        template = self.core.projects.getTemplatePath("3drenders")
        template = template.replace("\\", "/")
        renderFolder = template.split("/")[1]
        if renderFolder:
            subfolders.append(renderFolder)

        template = self.core.projects.getTemplatePath("playblasts")
        template = template.replace("\\", "/")
        playblastFolder = template.split("/")[1]
        if playblastFolder:
            subfolders.append(playblastFolder)

        return subfolders

    @err_catcher(name=__name__)
    def getTypeFromAssetPath(self, path: str, content: Optional[List[str]] = None) -> Optional[str]:
        """Determine if a path is an asset folder or a regular folder.
        
        Checks for the presence of asset-identifying subfolders.
        Uses strict or loose detection based on project settings.
        
        Args:
            path: Folder path to check.
            content: Optional list of folder contents. If None, reads from disk.
            
        Returns:
            Optional[str]: 'asset' if it's an asset folder, 'folder' if regular folder, None if path doesn't exist.
        """
        if not os.path.exists(path):
            return

        if content is None:
            try:
                content = os.listdir(path)
            except Exception as e:
                logger.warning("Error reading directory content for asset detection: %s" % str(e))
                return

        subfolders = self.getAssetSubFolders()

        if self.core.getConfig(
            "globals", "useStrictAssetDetection", dft=False, config="project"
        ):
            isAsset = True
            for folder in subfolders:
                if folder not in content:
                    isAsset = False

        else:
            isAsset = False
            for folder in subfolders:
                if folder in content:
                    isAsset = True

        if isAsset:
            return "asset"
        else:
            return "folder"

    @err_catcher(name=__name__)
    def getAsset(self, assetName: str, projectPath: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get an asset entity dict by name.
        
        Args:
            assetName: Asset name or relative path.
            projectPath: Optional specific project path.
            
        Returns:
            Optional[Dict[str, Any]]: Asset entity dict with 'type' and 'asset_path' keys, or None if not found.
        """
        base = self.core.assetPath
        if projectPath:
            base = base.replace(os.path.normpath(self.core.projectPath), projectPath)

        fullAssetPath = os.path.join(base, assetName)
        existed = os.path.exists(fullAssetPath)
        if existed:
            return {"type": "asset", "asset_path": assetName}
        else:
            return

    @err_catcher(name=__name__)
    def getAssets(self, path: Optional[str] = None, depth: int = 0, includeOmitted: bool = False) -> List[Dict[str, Any]]:
        """Get all assets in a path.
        
        Args:
            path: Optional base path to search. Defaults to project asset path.
            depth: Search depth. 0 = unlimited, 1 = immediate children only, etc.
            includeOmitted: If True, include paths that are marked as omitted.
            
        Returns:
            List[Dict[str, Any]]: List of asset entity dicts.
        """
        assets = []
        paths = self.getAssetPaths(path=path, depth=depth, includeOmitted=includeOmitted)
        assets = [{"type": "asset", "asset_path": self.getAssetRelPathFromPath(p)} for p in paths]
        return assets

    @err_catcher(name=__name__)
    def getAssetPaths(self, path: Optional[str] = None, returnFolders: bool = False, depth: int = 0, includeOmitted: bool = False) -> Union[List[str], Tuple[List[str], List[str]]]:
        """Get all asset folder paths in a directory tree.
        
        Recursively searches for asset folders based on asset-identifying subfolders.
        
        Args:
            path: Optional base path to search. Defaults to project asset path.
            returnFolders: If True, also return non-asset folder paths.
            depth: Search depth. 0 = unlimited, 1 = immediate children only, etc.
            includeOmitted: If True, include paths that are marked as omitted.
            
        Returns:
            Union[List[str], Tuple[List[str], List[str]]]: List of asset paths, or tuple of (asset_paths, folder_paths) if returnFolders is True.
        """
        aBasePath = path or self.core.assetPath
        assets = []
        assetFolders = []

        for root, folders, files in os.walk(aBasePath):
            for folder in folders:
                folderPath = os.path.join(root, folder)
                if not includeOmitted and self.isAssetPathOmitted(folderPath):
                    continue
    
                if self.getTypeFromAssetPath(folderPath) == "asset":
                    assets.append(folderPath)
                else:
                    if depth == 1:
                        assetFolders.append(folderPath)
                    else:
                        nextDepth = 0 if depth == 0 else (depth - 1)
                        childAssets, childFolders = self.getAssetPaths(
                            path=folderPath, returnFolders=True, depth=nextDepth
                        )
                        if childAssets or childFolders:
                            assets += childAssets
                            assetFolders += childFolders
                        else:
                            assetFolders.append(folderPath)
            break

        if returnFolders:
            return assets, assetFolders
        else:
            return assets

    @err_catcher(name=__name__)
    def getEmptyAssetFolders(self) -> List[str]:
        """Get all empty asset folders in the project.
        
        Returns:
            List[str]: List of paths to empty asset folders.
        """
        assets, folders = self.getAssetPaths(returnFolders=True)
        emptyFolders = []
        for folder in folders:
            for asset in assets:
                if folder in asset:
                    break
            else:
                for folder2 in folders:
                    if folder in folder2 and len(folder) < len(folder2):
                        break
                else:
                    emptyFolders.append(folder)

        return emptyFolders

    @err_catcher(name=__name__)
    def getAssetPathFromAssetName(self, assetName: str) -> Optional[str]:
        """Get the full path to an asset folder from its name.
        
        Args:
            assetName: Asset name or relative path.
            
        Returns:
            Optional[str]: Full path to asset folder or None if not found.
        """
        if os.path.isabs(assetName):
            assetPath = assetName
        else:
            assetPaths = self.getAssetPaths()
            path = os.path.join(self.core.assetPath, assetName)
            if path in assetPaths:
                assetPath = path
            else:
                for assetPath in assetPaths:
                    if os.path.basename(assetPath) == assetName:
                        assetPath = assetPath
                        break
                else:
                    return

        return assetPath

    @err_catcher(name=__name__)
    def getAssetFoldersFromPath(self, path: str, pathType: str = "asset") -> List[str]:
        """Get the asset folder hierarchy from a path.
        
        Args:
            path: Full path to an asset or within an asset.
            pathType: Type of path ('asset').
            
        Returns:
            List[str]: List of folder names in the asset hierarchy.
        """
        relPath = self.getAssetRelPathFromPath(path)
        folders = os.path.normpath(relPath).split(os.sep)
        if pathType == "asset":
            folders = folders[:-1]
        return folders

    @err_catcher(name=__name__)
    def filterAssets(self, assets: List[Dict[str, Any]], filterStr: str, projectPath: Optional[str] = None) -> List[Dict[str, Any]]:
        """Filter assets by a search string.
        
        Filters assets whose names or paths contain the filter string.
        Also filters out omitted assets and checks descriptions.
        
        Args:
            assets: List of asset entity dicts.
            filterStr: Search string (case-insensitive).
            projectPath: Optional specific project path.
            
        Returns:
            List[Dict[str, Any]]: Filtered list of asset entity dicts.
        """
        searchFilters = [x.strip() for x in filterStr.lower().split(",") if x.strip()] if filterStr else []
        filteredPaths = []
        for absAssetPath in assets:
            base = self.core.assetPath
            if projectPath:
                base = base.replace(os.path.normpath(self.core.projectPath), projectPath)

            assetPath = absAssetPath.replace(base, "")
            if self.core.useLocalFiles:
                localAssetPath = self.core.getAssetPath(location="local")
                assetPath = assetPath.replace(localAssetPath, "")
            assetPath = assetPath[1:]

            valid = False
            for searchFilter in searchFilters:
                if searchFilter in assetPath.lower():
                    valid = True
                    break

                description = self.getAssetDescription(self.getAssetNameFromPath(assetPath), projectPath=projectPath) or ""
                if searchFilter in description.lower():
                    valid = True
                    break

                entity = self.getAsset(assetPath, projectPath=projectPath)
                metaData = self.getMetaData(entity, projectPath=projectPath)
                if metaData and "tags" in metaData:
                    tags = [x.strip() for x in metaData["tags"]["value"].split(",")]
                    if searchFilter in tags:
                        valid = True
                        break

            if valid:
                filteredPaths.append(absAssetPath)

        return filteredPaths

    @err_catcher(name=__name__)
    def filterOmittedAssets(self, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove omitted assets from a list.
        
        Args:
            assets: List of asset entity dicts.
            
        Returns:
            List[Dict[str, Any]]: Filtered list without omitted assets.
        """
        filteredPaths = []
        for absAssetPath in assets:
            assetName = self.getAssetRelPathFromPath(absAssetPath)
            if assetName not in self.omittedEntities["asset"]:
                filteredPaths.append(absAssetPath)

        return filteredPaths

    @err_catcher(name=__name__)
    def isAssetPathOmitted(self, assetPath: str) -> bool:
        """Check if an asset path is marked as omitted.
        
        Args:
            assetPath: Asset path to check.
            
        Returns:
            bool: True if asset is omitted.
        """
        isOmitted = not bool(self.filterOmittedAssets([assetPath]))
        return isOmitted

    @err_catcher(name=__name__)
    def isValidAssetName(self, assetName: str) -> bool:
        """Check if an asset name contains only valid characters.
        
        Args:
            assetName: Asset name to validate.
            
        Returns:
            bool: True if name is valid.
        """
        if self.core.getConfig("globals", "useStrictAssetDetection"):
            return True
        else:
            return assetName not in self.getAssetSubFolders()

    @err_catcher(name=__name__)
    def getAssetNameFromPath(self, path: str) -> str:
        """Extract the asset name from a full path.
        
        Args:
            path: Full path to asset folder or file within asset.
            
        Returns:
            str: Asset name (last component before asset base path).
        """
        return os.path.basename(path)

    @err_catcher(name=__name__)
    def getAssetRelPathFromPath(self, path: str, projectPath: Optional[str] = None) -> str:
        """Get the relative asset path from a full path.
        
        Args:
            path: Full path to asset folder.
            projectPath: Optional specific project path.
            
        Returns:
            str: Relative path from asset base directory.
        """
        path = self.core.convertPath(path, "global")
        base = self.core.assetPath
        if projectPath:
            base = base.replace(os.path.normpath(self.core.projectPath), projectPath)

        return path.replace(base, "").strip("\\").strip("/")

    @err_catcher(name=__name__)
    def getScenefileData(self, fileName: str, preview: bool = False, getEntityFromPath: bool = False) -> Dict[str, Any]:
        """Extract metadata from a scenefile name and path.
        
        Parses entity, department, task, version, user, comment from filename.
        
        Args:
            fileName: Full path to scenefile.
            preview: If True, also load preview image.
            getEntityFromPath: If True, extract entity data from path.
            
        Returns:
            Dict[str, Any]: Scenefile data with keys like 'entity', 'department', 'task', 'version', 'user', 'comment', 'extension', etc.
        """
        data = self.core.getConfig(configPath=self.getScenefileInfoPath(fileName)) or {}
        data = dict(data)
        if fileName and (not data or getEntityFromPath):
            entityType = self.core.paths.getEntityTypeFromPath(fileName)
            key = None
            if entityType == "asset":
                key = "assetScenefiles"
            elif entityType == "shot":
                key = "shotScenefiles"

            if key:
                template = self.core.projects.getTemplatePath(key)
                hasData = bool(data)
                data["type"] = entityType
                data["entityType"] = entityType
                pathData = self.core.projects.extractKeysFromPath(fileName, template, context=data)
                if pathData.get("asset_path"):
                    pathData["asset"] = os.path.basename(pathData["asset_path"])

                if not hasData:
                    data = pathData
                elif getEntityFromPath:
                    if entityType == "asset":
                        if "asset" in pathData:
                            data["asset"] = pathData["asset"]

                        if "asset_path" in pathData:
                            data["asset_path"] = pathData["asset_path"]
                    if entityType == "shot":
                        if "shot" in pathData:
                            data["shot"] = pathData["shot"]

                        if "sequence" in pathData:
                            data["sequence"] = pathData["sequence"]

                        if "episode" in pathData:
                            data["episode"] = pathData["episode"]

        if fileName:
            data["filename"] = fileName
            data["extension"] = os.path.splitext(fileName)[1]

        if "type" not in data:
            etype = self.core.paths.getEntityTypeFromPath(fileName)
            if etype:
                data["type"] = etype

        data["locations"] = {}
        glbPath = self.core.convertPath(fileName, "global")
        if os.path.exists(glbPath):
            data["locations"]["global"] = glbPath

        if (
            self.core.useLocalFiles
            and os.path.exists(self.core.convertPath(fileName, "local"))
        ):
            data["locations"]["local"] = self.core.convertPath(fileName, "local")

        if preview:
            prvPath = os.path.splitext(fileName)[0] + "preview.jpg"
            if os.path.exists(prvPath):
                data["preview"] = prvPath

        return data

    @err_catcher(name=__name__)
    def getCurrentScenefileData(self) -> Dict[str, Any]:
        """Get scenefile data for the currently open scene.
        
        Returns:
            Dict[str, Any]: Scenefile data dict for current scene.
        """
        fn = self.core.getCurrentFileName()
        return self.getScenefileData(fn)

    @err_catcher(name=__name__)
    def getScenePreviewPath(self, scenepath: str) -> str:
        """Get the path to a scenefile's preview image.
        
        Args:
            scenepath: Path to scenefile.
            
        Returns:
            str: Path to preview image file.
        """
        return os.path.splitext(scenepath)[0] + "preview.jpg"

    @err_catcher(name=__name__)
    def setScenePreview(self, scenepath: str, preview: QPixmap) -> None:
        """Save a preview image for a scenefile.
        
        Args:
            scenepath: Path to scenefile.
            preview: Preview pixmap to save.
        """
        prvPath = self.getScenePreviewPath(scenepath)
        self.core.media.savePixmap(preview, prvPath)

    @err_catcher(name=__name__)
    def getScenefileInfoPath(self, scenePath: str) -> str:
        """Get the path to a scenefile's version info file.
        
        Args:
            scenePath: Path to scenefile.
            
        Returns:
            str: Path to version info config file.
        """
        return (
            os.path.splitext(scenePath)[0]
            + "versioninfo"
            + self.core.configs.getProjectExtension()
        )

    @err_catcher(name=__name__)
    def setScenefileInfo(self, scenePath: str, key: str, value: Any) -> None:
        """Set a specific info value for a scenefile.
        
        Args:
            scenePath: Path to scenefile.
            key: Info key to set.
            value: Value to set.
        """
        infoPath = self.getScenefileInfoPath(scenePath)

        sceneInfo = {}
        if os.path.exists(infoPath):
            sceneInfo = self.core.getConfig(configPath=infoPath) or {}

        sceneInfo[key] = value
        self.core.setConfig(data=sceneInfo, configPath=infoPath)

    @err_catcher(name=__name__)
    def getHighestVersion(
        self,
        entity: Dict[str, Any],
        department: str,
        task: str,
        getExistingPath: bool = False,
        fileTypes: Union[str, List[str]] = "*",
        localVersions: bool = True,
        getExistingVersion: bool = False,
    ) -> Union[str, List, Tuple[Optional[int], str]]:
        """Get the next version number or highest existing version for a task.
        
        Args:
            entity: Entity dict.
            department: Department name.
            task: Task name.
            getExistingPath: If True, return path to highest version instead of next version number.
            fileTypes: File extension filter ('*' for all, or list of extensions).
            localVersions: Include local versions in search.
            getExistingVersion: If True, return [version_int, path] tuple.
            
        Returns:
            Union[str, List, Tuple]: Next version string (e.g. 'v0001'), or path, or [version, path] tuple based on flags.
        """
        scenefiles = self.getScenefiles(entity=entity, step=department, category=task)
        highversion = [None, ""]
        for scenefile in scenefiles:
            ext = os.path.splitext(scenefile)[1]
            if fileTypes != "*" and ext not in fileTypes:
                continue

            if not self.isValidScenefilename(scenefile):
                continue

            fname = self.core.getScenefileData(scenefile)
            if fname.get("type") != entity.get("type"):
                continue

            try:
                version = int(fname["version"][-self.core.versionPadding:])
            except:
                continue

            if (
                ext.lower() in self.core.media.supportedFormats
                and self.core.versionFormat.startswith("v")
                and fname["version"][-(self.core.versionPadding+1)] != "v"
            ):
                continue

            if highversion[0] is None or version > highversion[0]:
                highversion = [version, scenefile]

        if getExistingVersion:
            return highversion
        elif getExistingPath:
            return highversion[1]
        else:
            if highversion[0] is None:
                return self.core.versionFormat % (self.core.lowestVersion)
            else:
                return self.core.versionFormat % (highversion[0] + 1)

    @err_catcher(name=__name__)
    def getTaskNames(self, taskType: Optional[str] = None, locations: Optional[List] = None, context: Optional[Dict] = None, key: Optional[str] = None, taskname: Optional[str] = None, addDepartments: bool = True) -> List[str]:
        """Get all task/product/identifier names for a given type.
        
        Scans project structure to find all existing tasks, products, or identifiers.
        
        Args:
            taskType: Type of tasks to get ('export', '3d', '2d', 'playblast', 'external', 'textures').
            locations: Optional list of location paths to search.
            context: Optional context dict to filter results.
            key: Optional structure key override (auto-determined from taskType if None).
            taskname: Optional task name key override.
            addDepartments: If True, include department names in results.
            
        Returns:
            List[str]: List of unique task/product/identifier names.
        """
        if key is None:
            if taskType == "export":
                key = "products"
            elif taskType == "3d":
                key = "3drenders"
            elif taskType == "2d":
                key = "2drenders"
            elif taskType == "playblast":
                key = "playblasts"
            elif taskType == "external":
                key = "externalMedia"
            elif taskType == "textures":
                key = "textures"
            else:
                raise Exception("Invalid taskType: %s" % taskType)

        context = context or {}
        fname = self.core.getCurrentFileName()
        fnameData = self.core.getScenefileData(fname)
        context.update(fnameData)
        if "version" in context:
            del context["version"]

        if "type" in context:
            departmentNames = self.getCategories(
                context, step=context.get("department")
            )
        else:
            departmentNames = []

        if key == "products":
            locations = self.core.paths.getExportProductBasePaths()
        else:
            locations = self.core.paths.getRenderProductBasePaths()

        productDirs = []
        for location in locations:
            if locations is not None and location not in locations:
                continue

            productDir = {"location": location, "path": locations[location]}
            productDirs.append(productDir)

        productDicts = []
        for productDir in productDirs:
            context["project_path"] = productDir["path"]
            template = self.core.projects.getResolvedProjectStructurePath(
                key, context=context
            )
            productData = self.core.projects.getMatchingPaths(template)
            productDicts += productData

        taskList = []
        for data in productDicts:
            if taskname is None:
                if key == "products":
                    taskname = "product"
                else:
                    taskname = "identifier"

            taskList.append(data[taskname])

        if addDepartments:
            taskList += departmentNames

        taskList = sorted(list(set(taskList)), key=lambda x: x.lower())
        return taskList

    @err_catcher(name=__name__)
    def getEntityPreviewPath(self, entity: Dict[str, Any]) -> str:
        """Get the path to an entity's preview/thumbnail image.
        
        Args:
            entity: Entity dict with 'type' and entity identifiers.
            
        Returns:
            str: Path to preview image file.
        """
        if entity["type"] == "asset":
            folderName = "Assetinfo"
            entityName = self.getAssetNameFromPath(entity.get("asset_path", ""))
        elif entity["type"] in ["shot", "sequence", "episode"]:
            folderName = "Shotinfo"
            if entity["type"] == "episode":
                entityName = "ep_%s" % entity["episode"]
            elif entity["type"] == "sequence":
                entityName = "seq_%s" % entity["sequence"]
            elif entity["type"] == "shot":
                entityName = self.getShotName(entity)

        ext = os.getenv("PRISM_ENTITY_THUMBNAIL_EXT", ".jpg")
        imgName = "%s_preview%s" % (entityName, ext)
        pipeFolder = self.core.projects.getPipelineFolder()
        if entity.get("project_path"):
            pipeFolder = pipeFolder.replace(os.path.normpath(self.core.projectPath), entity["project_path"])

        imgPath = os.path.join(
            pipeFolder, folderName, imgName
        )
        return imgPath

    @err_catcher(name=__name__)
    def getEntityPreview(self, entity: Dict[str, Any], width: Optional[int] = None, height: Optional[int] = None) -> Optional[QPixmap]:
        """Get the preview image for an entity.
        
        Args:
            entity: Entity dict with 'type' and entity identifiers.
            width: Optional width to scale to.
            height: Optional height to scale to.
            
        Returns:
            Optional[QPixmap]: Preview pixmap or None if not found.
        """
        pm = None
        imgPath = self.getEntityPreviewPath(entity)
        if os.path.exists(imgPath):
            pm = self.core.media.getPixmapFromPath(imgPath)
            if width and height:
                pm = self.core.media.scalePixmap(pm, width, height)

        return pm

    @err_catcher(name=__name__)
    def setEntityPreview(self, entity: Dict[str, Any], pixmap: QPixmap, width: int = 250, height: int = 141) -> Optional[QPixmap]:
        """Save a preview image for an entity.
        
        Args:
            entity: Entity dict with 'type' and entity identifiers.
            pixmap: Preview pixmap to save.
            width: Target width for saved image.
            height: Target height for saved image.
            
        Returns:
            Optional[QPixmap]: Scaled and saved pixmap or None if invalid.
        """
        if not pixmap:
            logger.debug("invalid pixmap")
            return

        if (pixmap.width() / float(pixmap.height())) > 1.7778:
            pmsmall = pixmap.scaledToWidth(width)
        else:
            pmsmall = pixmap.scaledToHeight(height)

        prvPath = self.getEntityPreviewPath(entity)
        logger.debug("setting entity preview for: %s" % entity)
        self.core.media.savePixmap(pmsmall, prvPath)
        return pmsmall

    @err_catcher(name=__name__)
    def getPresetScene(self, name: str) -> Optional[Dict[str, str]]:
        """Get a preset scene by name.
        
        Args:
            name: Preset scene name or filename.
            
        Returns:
            Optional[Dict[str, str]]: Preset dict with 'label' and 'path' keys, or None if not found.
        """
        presets = self.getPresetScenes()
        for preset in presets:
            if preset["label"] == name or os.path.basename(preset["path"]) == name:
                return preset

    @err_catcher(name=__name__)
    def getPresetScenes(self, context: Optional[Dict] = None) -> List[Dict[str, str]]:
        """Get all available preset scenes.
        
        Searches project PresetScenes folder and custom paths from environment variable.
        
        Args:
            context: Optional context dict to filter presets.
            
        Returns:
            List[Dict[str, str]]: List of preset dicts with 'label' and 'path' keys.
        """
        presetDir = os.path.join(self.core.projects.getPipelineFolder(), "PresetScenes")
        folders = [presetDir]
        folders += [x.strip() for x in os.getenv("PRISM_SCENEFILE_PRESET_PATHS", "").split(os.pathsep) if x]
        presetScenes = []
        for folder in folders:
            presetScenes += self.getPresetScenesFromFolder(folder)

        self.core.callback("getPresetScenes", args=[presetScenes])
        return presetScenes

    @err_catcher(name=__name__)
    def getBlacklistedExtensions(self) -> List[str]:
        """Get list of file extensions to exclude from preset scene search.
        
        Reads from PRISM_BLACKLISTED_EXTENSIONS environment variable.
        
        Returns:
            List[str]: List of blacklisted file extensions.
        """
        extsStr = os.getenv("PRISM_BLACKLISTED_EXTENSIONS", "")
        exts = [ext.strip() for ext in extsStr.split(",")]
        return exts

    @err_catcher(name=__name__)
    def getPresetScenesFromFolder(self, folder: str) -> List[Dict[str, str]]:
        """Get all preset scene files from a folder.
        
        Recursively searches folder for scene files, excluding blacklisted extensions
        and files starting with '.', '_', or ending with '~'.
        
        Args:
            folder: Folder path to search.
            
        Returns:
            List[Dict[str, str]]: List of preset dicts with 'label' and 'path' keys.
        """
        presetScenes = []
        if os.path.exists(folder):
            blacklisted = self.getBlacklistedExtensions()
            for root, folders, files in os.walk(folder):
                for filename in sorted(files):
                    if filename == "readme.txt":
                        continue

                    if filename.startswith(".") or filename.startswith("_") or filename.endswith("~"):
                        continue

                    if blacklisted:
                        _, ext = os.path.splitext(filename)
                        if ext in blacklisted:
                            continue

                    relPresetDir = root.replace(folder, "")
                    if relPresetDir:
                        presetName = (
                            relPresetDir[1:].replace("\\", "/") + "/" + filename
                        )
                    else:
                        presetName = filename

                    presetName = os.path.splitext(presetName)[0]
                    path = os.path.join(root, filename)
                    presetScenes.append({"label": presetName, "path": path})

        return presetScenes

    @err_catcher(name=__name__)
    def getScenePresetPathFromName(self, name: str) -> Optional[str]:
        """Get the full path to a preset scene by name.
        
        Args:
            name: Preset scene name.
            
        Returns:
            Optional[str]: Full path to preset scene or None if not found.
        """
        scenes = self.getPresetScenes()
        for scene in scenes:
            if scene["label"] == name:
                return scene["path"]

    @err_catcher(name=__name__)
    def ingestScenefiles(self, files: List[str], entity: Dict[str, Any], department: str, task: str, finishCallback: Optional[callable] = None, data: Optional[Dict] = None, rename: bool = True) -> List[str]:
        """Import external scenefiles into the project structure.
        
        Copies files to the appropriate project location with proper naming.
        
        Args:
            files: List of file paths to ingest.
            entity: Target entity dict.
            department: Target department name.
            task: Target task name.
            finishCallback: Optional callback when copy completes.
            data: Optional additional data to merge into version info.
            rename: If True, rename files to project naming convention. If False, keep original names.
            
        Returns:
            List[str]: List of created file paths.
        """
        kwargs = {
            "entity": entity,
            "department": department,
            "task": task,
            "comment": "",
            "user": self.core.user,
        }
        version = self.core.entities.getHighestVersion(entity, department, task)
        kwargs["version"] = version
        if data:
            kwargs.update(data)

        createdFiles = []
        for idx, file in enumerate(files):
            kwargs["extension"] = os.path.splitext(file)[1]
            targetPath = self.core.paths.generateScenePath(**kwargs)
            if self.core.useLocalFiles:
                targetPath = self.core.convertPath(targetPath, target="local")

            if not rename:
                targetPath = os.path.join(os.path.dirname(targetPath), os.path.basename(file))

            if not os.path.exists(os.path.dirname(targetPath)):
                try:
                    os.makedirs(os.path.dirname(targetPath))
                except:
                    self.core.popup("The directory could not be created")
                    return

            targetPath = targetPath.replace("\\", "/")

            thread = self.core.copyWithProgress(file, targetPath, finishCallback=finishCallback)
            thread.wait(999999999)
            details = entity.copy()
            details["department"] = department
            details["task"] = task
            details["user"] = kwargs["user"]
            details["version"] = kwargs["version"]
            details["comment"] = kwargs["comment"]
            details["extension"] = kwargs["extension"]
            details["date"] = int(datetime.datetime.now().timestamp())
            self.core.saveSceneInfo(targetPath, details=details)
            createdFiles.append(targetPath)
            logger.debug("ingested scenefile: %s" % targetPath)

        return createdFiles

    @err_catcher(name=__name__)
    def createSceneFromPreset(
        self,
        entity: Dict[str, Any],
        fileName: str,
        step: Optional[str] = None,
        category: Optional[str] = None,
        comment: Optional[str] = None,
        version: Optional[str] = None,
        location: str = "local",
    ) -> Optional[str]:
        """Create a new scene version from a preset scene file.
        
        Copies a preset scene to the proper project location with full version info.
        
        Args:
            entity: Entity dict.
            fileName: Preset scene name or full path to preset file.
            step: Optional department name.
            category: Optional task/category name.
            comment: Optional version comment.
            version: Optional version string. If None, uses next available version.
            location: Target location ('local' or 'global').
            
        Returns:
            Optional[str]: Path to created scene file or None if failed.
        """
        comment = comment or ""
        user = self.core.user

        if entity["type"] not in ["asset", "shot"]:
            self.core.popup("Invalid entity:\n\n%s" % entity["type"])
            return

        if not version:
            version = self.core.entities.getHighestVersion(entity, step, category)

        if os.path.isabs(fileName):
            scene = fileName
        else:
            preset = self.getPresetScene(fileName)
            if preset:
                scene = preset["path"]
            else:
                scene = fileName

        if not os.path.exists(scene):
            self.core.popup(
                "The preset scenefile doesn't exist:\n\n%s"
                % scene
            )
            return

        ext = os.path.splitext(scene)[1]
        filePath = self.core.generateScenePath(
            entity,
            step,
            task=category,
            extension=ext,
            comment=comment,
            version=version,
            user=user,
        )

        if location == "local" and self.core.useLocalFiles:
            filePath = self.core.convertPath(filePath, "local")

        if os.path.exists(filePath):
            msg = (
                "Skipped creating a new version from preset.\nThe filepath exists already:\n\n%s"
                % filePath
            )
            self.core.popup(msg)
            return

        if not os.path.exists(os.path.dirname(filePath)):
            try:
                os.makedirs(os.path.dirname(filePath))
            except:
                self.core.popup(
                    "The directory could not be created:\n\n%s"
                    % os.path.dirname(filePath)
                )
                return

        filePath = filePath.replace("\\", "/")

        shutil.copyfile(scene, filePath)
        details = entity.copy()
        details["department"] = step
        details["task"] = category
        details["user"] = user
        details["version"] = version
        details["comment"] = comment
        details["extension"] = ext
        self.core.saveSceneInfo(filePath, details=details)

        self.core.callback(
            name="onSceneFromPresetCreated",
            args=[self, filePath],
        )

        logger.debug("Created scene from preset: %s" % filePath)
        return filePath

    @err_catcher(name=__name__)
    def createPresetScene(self) -> Optional[str]:
        """Create a new preset scene from the current scene.
        
        Prompts user for preset name and saves current scene to PresetScenes folder.
        
        Returns:
            Optional[str]: Path to created preset scene or None if cancelled.
        """
        presetDir = os.path.join(self.core.projects.getPipelineFolder(), "PresetScenes")

        newItem = PrismWidgets.CreateItem(
            core=self.core,
            startText=self.core.appPlugin.pluginName.replace(" ", ""),
        )

        self.core.parentWindow(newItem)
        newItem.e_item.setFocus()
        newItem.setWindowTitle("Create preset scene")
        newItem.l_item.setText("Preset name:")
        result = newItem.exec_()

        if result != 1:
            return

        pName = newItem.e_item.text()

        filepath = os.path.join(presetDir, pName)
        filepath = filepath.replace("\\", "/")
        filepath += self.core.appPlugin.getSceneExtension(self)

        self.core.saveScene(filepath=filepath, prismReq=False)
        return filepath

    @err_catcher(name=__name__)
    def getAutobackPath(self, prog: str, entity: Optional[Dict[str, Any]] = None, department: Optional[str] = None, task: Optional[str] = None) -> Optional[Tuple[str, str]]:
        """Get the autobackup path for a specific program and context.
        
        Args:
            prog: Program/plugin name.
            entity: Optional entity dict.
            department: Optional department name.
            task: Optional task name.
            
        Returns:
            Optional[Tuple[str, str]]: Tuple of (autoback_path, file_filter_string) or None if not available.
        """
        if prog == self.core.appPlugin.pluginName:
            if not hasattr(self.core.appPlugin, "getAutobackPath"):
                return

            autobackpath, fileStr = self.core.appPlugin.getAutobackPath(self)
        else:
            for i in self.core.unloadedAppPlugins.values():
                if i.pluginName == prog:
                    if not hasattr(i, "getAutobackPath"):
                        return

                    autobackpath, fileStr = i.getAutobackPath(self)

        if not autobackpath and entity:
            if entity["type"] == "asset":
                cVersion = self.core.compareVersions(
                    self.core.projectVersion, "v1.2.1.6"
                )
                if cVersion == "lower":
                    autobackpath = self.core.getEntityPath(entity=entity, step=department)
                else:
                    autobackpath = self.core.getEntityPath(
                        entity=entity, step=department, category=task
                    )

            elif entity["type"] == "shot":
                autobackpath = self.core.getEntityPath(
                    entity=entity, step=department, category=task
                )

        return autobackpath, fileStr

    @err_catcher(name=__name__)
    def createVersionFromAutoBackupDlg(
        self, prog: str, entity: Dict[str, Any], department: str, task: str, parent: Optional[QWidget] = None
    ) -> Optional[str]:
        """Show file dialog to select an autobackup file and create a version from it.
        
        Args:
            prog: Program/plugin name.
            entity: Entity dict.
            department: Department name.
            task: Task name.
            parent: Optional parent widget for dialog.
            
        Returns:
            Optional[str]: Path to created version or None if cancelled.
        """
        parent = parent or self.core.messageParent
        result = self.getAutobackPath(prog, entity, department, task)
        if not result:
            return

        autobackpath, fileStr = result
        autobfile = QFileDialog.getOpenFileName(
            parent, "Select Autoback File", autobackpath, fileStr
        )[0]

        if not autobfile:
            return

        return self.createVersionFromAutoBackup(autobfile, entity, department, task)

    @err_catcher(name=__name__)
    def createVersionFromAutoBackup(self, filepath: str, entity: Dict[str, Any], department: str, task: str) -> Optional[str]:
        """Create a new version from an autobackup file.
        
        Args:
            filepath: Path to autobackup file.
            entity: Entity dict.
            department: Department name.
            task: Task name.
            
        Returns:
            Optional[str]: Path to created version or None if failed.
        """
        version = self.core.entities.getHighestVersion(entity, department, task)
        targetpath = self.core.generateScenePath(
            entity=entity,
            department=department,
            task=task,
            extension=os.path.splitext(filepath)[1],
            version=version
        )

        if self.core.useLocalFiles:
            targetpath = self.core.convertPath(targetpath, "local")

        if os.path.exists(targetpath):
            msg = (
                "Skipped creating a new version from autoback.\nThe filepath exists already:\n\n%s"
                % targetpath
            )
            self.core.popup(msg)
            return

        if not os.path.exists(os.path.dirname(targetpath)):
            try:
                os.makedirs(os.path.dirname(targetpath))
            except:
                self.core.popup("The directory could not be created")
                return

        targetpath = targetpath.replace("\\", "/")
        self.core.copySceneFile(filepath, targetpath)

        details = entity.copy()
        details["department"] = department
        details["task"] = task
        details["extension"] = os.path.splitext(filepath)[1]
        details["comment"] = ""
        details["version"] = version
        self.core.saveSceneInfo(targetpath, details=details)
        logger.debug("Created scene from autoback: %s" % targetpath)
        return targetpath

    @err_catcher(name=__name__)
    def copySceneFile(self, filepath: str, entity: Dict[str, Any], department: str, task: str, location: Optional[str] = None) -> Optional[str]:
        """Copy a scene file to create a new version in the project.
        
        Args:
            filepath: Source file path to copy.
            entity: Entity dict.
            department: Department name.
            task: Task name.
            location: Optional target location ('local' or 'global'). If None, uses project setting.
            
        Returns:
            Optional[str]: Path to created version or None if failed.
        """
        version = self.core.entities.getHighestVersion(entity, department, task)
        targetpath = self.core.generateScenePath(
            entity=entity,
            department=department,
            task=task,
            extension=os.path.splitext(filepath)[1],
            version=version,
            location=location
        )

        if location is None:
            if self.core.useLocalFiles:
                targetpath = self.core.convertPath(targetpath, "local")

        if not os.path.exists(os.path.dirname(targetpath)):
            try:
                os.makedirs(os.path.dirname(targetpath))
            except:
                self.core.popup("The directory could not be created")
                return

        targetpath = targetpath.replace("\\", "/")
        self.core.copySceneFile(filepath, targetpath)

        details = entity.copy()
        details["department"] = department
        details["task"] = task
        details["extension"] = os.path.splitext(filepath)[1]
        details["version"] = version
        self.core.saveSceneInfo(targetpath, details=details, replace=True)
        logger.debug("Copied scene: %s" % targetpath)
        return targetpath
    
    @err_catcher(name=__name__)
    def getDefaultSceneBuildingSteps(self) -> List[Dict[str, Any]]:
        """Get the list of default scene building steps.
        
        Defines the order of operations to apply during scene building.
        
        Returns:
            List[Dict[str, Any]]: List of step dictionaries with their details.
        """
        steps = [
            {
                "name": "setFramerange",
                "label": "Set Framerange",
                "function": "self.core.entities.buildSceneSetFramerange",
                "settings": [
                    {
                        "type": "combobox",
                        "label": "Framerange to apply",
                        "items": ["Shotrange", "Shotrange + Handles"],
                        "value": "Shotrange"
                    }
                ]
            },
            {
                "name": "setFps",
                "label": "Set FPS",
                "function": "self.core.entities.buildSceneSetFPS",
            },
            {
                "name": "setResolution",
                "label": "Set Resolution",
                "function": "self.core.entities.buildSceneSetResolution",
            },
            {
                "name": "importProducts",
                "label": "Import Products",
                "function": "self.core.entities.buildSceneImportProducts",
                "settings": [
                    {
                        "type": "checkbox",
                        "label": "Ignore Master Versions",
                        "value": False,
                    }
                ]
            },
            {
                "name": "importShotcam",
                "label": "Import Shot Cameras",
                "function": "self.core.entities.buildSceneImportShotcam",
            },
            {
                "name": "runCode",
                "label": "Run Code",
                "function": "self.core.entities.buildSceneRunCode",
                "description": "Run custom Python code during scene building.",
                "settings": [
                    {
                        "type": "code",
                        "label": "Code",
                        "value": "# Available variables: core, self, context, step\n",
                    }
                ]
            }
        ]
        return steps

    @err_catcher(name=__name__)
    def getAvailableSceneBuildingSteps(self, app: str) -> List[dict]:
        """Get the list of available scene building steps.

        Args:
            app: Application name.
            
        Returns:
            List[dict]: List of step dictionaries that can be applied during scene building.
        """

        steps = self.core.callback("getAvailableSceneBuildingSteps", args=[app]) or []
        return steps
    
    @err_catcher(name=__name__)
    def buildSceneSetFramerange(self, step: Dict[str, Any], context: Dict[str, Any]) -> None:
        """
        Scene building step function to set framerange for an entity.
        
        Args:
            step: Step settings dict.
            context: Current scene building context dict with entity, department, task info.
        """
        if step["settings"][0]["value"] == "Shotrange":
            value = "Set shotrange in scene"
        else:
            value = "Set shotrange in scene (with handles)"

        settings = {
            "accept": True,
            "value": value
        }
        self.core.sanities.checkFramerange(settings)

    @err_catcher(name=__name__)
    def buildSceneSetFPS(self, step: Dict[str, Any], context: Dict[str, Any]) -> None:
        """
        Scene building step function to set FPS for an entity.
        
        Args:
            step: Step settings dict.
            context: Current scene building context dict with entity, department, task info.
        """
        settings = {
            "accept": True
        }
        self.core.sanities.checkFPS(settings)

    @err_catcher(name=__name__)
    def buildSceneSetResolution(self, step: Dict[str, Any], context: Dict[str, Any]) -> None:
        """
        Scene building step function to set resolution for an entity.
        
        Args:
            step: Step settings dict.
            context: Current scene building context dict with entity, department, task info.
        """
        settings = {
            "accept": True
        }
        self.core.sanities.checkResolution(settings)

    @err_catcher(name=__name__)
    def buildSceneImportProducts(self, step: Dict[str, Any], context: Dict[str, Any]) -> None:
        """
        Scene building step function to import products for an entity.
        
        Args:
            step: Step settings dict.
            context: Current scene building context dict with entity, department, task info.
        """
        entityData = context.copy()
        entityData["department"] = context.get("department")
        entityData["task"] = context.get("task")
        includeMaster = not step.get("settings", [{}])[0].get("value", True)
        self.core.products.importProductsForTask(context, context.get("department"), context.get("task"), quietCheck=True, includeMaster=includeMaster)
        if context.get("type") in ["shot"]:
            self.core.products.importConnectedAssets(entityData, quietCheck=True, includeMaster=includeMaster)
    
    @err_catcher(name=__name__)
    def buildSceneImportShotcam(self, step: Dict[str, Any], context: Dict[str, Any]) -> None:
        """
        Scene building step function to import shot cameras for a shot entity.
        
        Args:
            step: Step settings dict.
            context: Current scene building context dict with entity, department, task info.
        """
        entityData = context.copy()
        sm = self.core.getStateManager()
        if not sm:
            return

        sm.importShotCam(shot=entityData, quiet=True)

    @err_catcher(name=__name__)
    def buildSceneRunCode(self, step: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Scene building step to run custom Python code.

        Available variables in the code scope:
            core: Prism core instance
            self: ProjectEntities instance
            context: Current scene building context dict
            step: Current step dict
        """
        code = ""
        for setting in step.get("settings") or []:
            label = (setting.get("label") or setting.get("name") or "").lower()
            if label in ["code", "python", "python code"]:
                code = setting.get("value") or ""
                break

        if not code.strip():
            return

        scope = {
            "core": self.core,
            "self": self,
            "context": context,
            "step": step,
        }
        exec(code, scope, scope)

    @err_catcher(name=__name__)
    def getActiveSceneBuildingSteps(
        self,
        entity: Dict[str, Any],
        department: str,
        task: str,
        sbSettings: Dict,
        skipBuildSteps: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Return the ordered list of enabled scene building steps that match the given context.

        Steps are loaded from the project config for the current app plugin (under
        ``sceneBuilding.<appName>.steps``).  When no app-specific steps are configured
        the built-in defaults from :meth:`getDefaultSceneBuildingSteps` are used.

        Each step is included only when:

        * ``enabled`` is ``True`` (or absent).
        * Its ``name`` is not in *skipBuildSteps*.
        * Its ``dftTasks`` filter (if present) matches *entity*/*department*/*task*.
        * For built-in steps without a ``dftTasks`` key the corresponding entry in
          *sbSettings* is used as a fallback filter.

        Args:
            entity: Entity dict.
            department: Department name.
            task: Task name.
            sbSettings: Scene building settings dict (merged defaults + project overrides).
            skipBuildSteps: Optional list of step names to skip.

        Returns:
            List of active step dicts in execution order.
        """
        skipBuildSteps = skipBuildSteps or []
        appName = self.core.appPlugin.pluginName

        configuredSteps = self.core.getConfig("sceneBuilding", appName[0].lower() + appName[1:] + "_steps", config="project") or []
        logger.debug("configured scene building steps for %s: %s" % (appName, [x.get("name") for x in configuredSteps]))
        context = entity.copy()
        context["department"] = department
        context["task"] = task

        activeSteps = []
        for step in configuredSteps:
            if not step.get("enabled", True):
                continue

            if step.get("name") in skipBuildSteps:
                continue

            dftTasks = {
                "entities": ["*"],
                "departments": ["*"],
                "tasks": ["*"],
            }
            dftTasks = step.get("dftTasks", dftTasks)
            if not self.doesContextMatchTaskFilters(dftTasks, context):
                continue

            activeSteps.append(step)

        return activeSteps

    @err_catcher(name=__name__)
    def buildScene(
        self,
        entity: Dict[str, Any],
        department: str,
        task: str,
        stepOverrides: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[str]:
        """Automatically build a new scene with project settings applied.
        
        Creates a new scene with proper framerange, fps, resolution, imported products,
        and shot cameras based on scene building settings.
        
        Args:
            entity: Entity dict.
            department: Department name.
            task: Task name.
            stepOverrides: Optional per-run list of step dicts. If provided,
                these steps are executed instead of resolving active steps from
                project configuration.
            
        Returns:
            Optional[str]: Path to created scene or None if failed/cancelled.
        """
        kwargs = {
            "entity": entity,
            "department": department,
            "task": task,
        }
        skipBuildSteps = []
        result = self.core.callback("preBuildScene", **kwargs)
        for res in result:
            if isinstance(res, dict) and res.get("cancel", False):
                return

        if hasattr(self.core.appPlugin, "newScene"):
            result = self.core.appPlugin.newScene()
            if not result:
                return

        result = self.core.callback("buildScene", **kwargs)
        for res in result:
            if isinstance(res, dict):
                if res.get("cancel", False):
                    return

                if res.get("skipBuildSteps"):
                    skipBuildSteps += res["skipBuildSteps"]

        version = self.core.entities.getHighestVersion(entity, department, task)
        filepath = self.core.generateScenePath(
            entity=entity,
            department=department,
            task=task,
            extension=self.core.appPlugin.getSceneExtension(self),
            version=version
        )

        if self.core.useLocalFiles:
            filepath = self.core.convertPath(filepath, "local")

        if not os.path.exists(os.path.dirname(filepath)):
            try:
                os.makedirs(os.path.dirname(filepath))
            except:
                self.core.popup("The directory could not be created")
                return

        filepath = filepath.replace("\\", "/")
        self.core.startAutosaveTimer(quit=True)

        details = entity.copy()
        details["department"] = department
        details["task"] = task
        details["extension"] = os.path.splitext(filepath)[1]
        details["comment"] = "Scene Building"
        details["version"] = version

        # Get scene building steps and split them into before/after save groups
        sbSettings = self.core.getConfig("sceneBuilding", config="project") or {}
        if stepOverrides is not None:
            steps = stepOverrides
        else:
            steps = self.getActiveSceneBuildingSteps(
                entity,
                department,
                task,
                sbSettings,
                skipBuildSteps=skipBuildSteps,
            )
        logger.debug("active scene building steps: %s" % [x["name"] for x in steps])

        # Split steps into before and after save scene
        stepsBeforeSave = [s for s in steps if s.get("runBeforeSaveScene", False)]
        stepsAfterSave = [s for s in steps if not s.get("runBeforeSaveScene", False)]

        context = entity.copy()
        context["department"] = department
        context["task"] = task

        # Run steps that should execute before saving the scene
        for step in stepsBeforeSave:
            preparedStep = dict(step)
            func = step.get("function")
            logger.debug("running scene building step (before save) '%s' with function '%s'" % (step.get("name", ""), func))
            if callable(func):
                func(preparedStep, context)
            elif isinstance(func, str):
                try:
                    fn = eval(func, {"self": self})
                    fn(preparedStep, context)
                except Exception as e:
                    logger.warning("Failed to execute scene building step '%s': %s" % (step.get("name", ""), e))

        # Now save the scene or create from preset
        self.core.sanities.checksToRun["onSceneOpen"]["enabled"] = False
        presetScene = self.getDefaultPresetSceneForContext(details)
        if presetScene and os.path.splitext(presetScene)[1] in self.core.appPlugin.sceneFormats:
            filePath = self.createSceneFromPreset(
                entity,
                presetScene,
                step=department,
                category=task,
                comment="build scene",
                location="local",
            )
            self.core.callback(
                name="preLoadPresetScene",
                args=[self, filePath],
            )
            self.openScenefile(filepath)
            try:
                self.core.pb.sceneBrowser.refreshScenefilesThreaded()
            except:
                pass

            self.core.callback(
                name="postLoadPresetScene",
                args=[self, filePath],
            )
        else:
            filepath = self.core.saveScene(filepath=filepath, details=details)
            self.core.sceneOpen()

        self.core.sanities.checksToRun["onSceneOpen"]["enabled"] = True

        # Run remaining steps after the scene has been saved
        for step in stepsAfterSave:
            preparedStep = dict(step)
            func = step.get("function")
            logger.debug("running scene building step '%s' with function '%s'" % (step.get("name", ""), func))
            if callable(func):
                func(preparedStep, context)
            elif isinstance(func, str):
                try:
                    fn = eval(func, {"self": self})
                    fn(preparedStep, context)
                except Exception as e:
                    logger.warning("Failed to execute scene building step '%s': %s" % (step.get("name", ""), e))

        if self.core.shouldAutosaveTimerRun():
            self.core.startAutosaveTimer()

        kwargs = {
            "entity": entity,
            "department": department,
            "task": task,
            "filepath": filepath,
        }
        self.core.callback("postBuildScene", **kwargs)
        logger.debug("build scene: %s" % filepath)
        return filepath

    @err_catcher(name=__name__)
    def openScenefile(self, filepath: str) -> bool:
        """Open a scenefile in the current application.
        
        Handles lockfile checking, local file syncing, state manager, and callbacks.
        
        Args:
            filepath: Path to scenefile to open.
            
        Returns:
            bool: True if successfully opened, False otherwise.
        """
        if self.core.getLockScenefilesEnabled():
            from PrismUtils import Lockfile
            lf = Lockfile.Lockfile(self.core, filepath)
            if lf.isLocked():
                showPopup = True

                modTime = self.core.getFileModificationDate(lf.lockPath, asString=False, asDatetime=True)
                age = datetime.datetime.now() - modTime
                if age < datetime.timedelta(minutes=11):
                    lfData = self.core.configs.readJson(path=lf.lockPath, ignoreErrors=True) or {}
                    if lfData.get("username"):
                        if lfData.get("username") == self.core.username:
                            showPopup = False
                        else:
                            msg = self.core.tr("This scenefile is currently being used by") + " \"%s\"." % lfData.get("username")
                    else:
                        msg = self.core.tr("This scenefile is currently being used.")

                    if showPopup:
                        result = self.core.popupQuestion(msg, buttons=["Continue", "Cancel"], icon=QMessageBox.Warning)
                        if result != "Continue":
                            return

        wasSmOpen = self.core.isStateManagerOpen()
        if wasSmOpen:
            self.core.sm.close()

        if self.core.useLocalFiles and self.core.fileInPipeline(filepath):
            lfilepath = self.core.convertPath(filepath, "local")

            if not os.path.exists(lfilepath):
                if not os.path.exists(os.path.dirname(lfilepath)):
                    try:
                        os.makedirs(os.path.dirname(lfilepath))
                    except:
                        self.core.popup(self.core.tr("The directory could not be created"))
                        return

                self.core.copySceneFile(filepath, lfilepath)

            filepath = lfilepath

        if self.core.appPlugin.pluginName == "Standalone":
            self.core.openFile(filepath)
        else:
            filepath = filepath.replace("\\", "/")
            logger.debug("Opening scene " + filepath)
            self.core.appPlugin.openScene(self, filepath)

        self.core.addToRecent(filepath)
        if wasSmOpen:
            self.core.stateManager()

        return True

    @err_catcher(name=__name__)
    def createVersionFromCurrentScene(self, entity: Dict[str, Any], department: str, task: str) -> Optional[str]:
        """Create a new version by saving the current scene.
        
        Args:
            entity: Entity dict.
            department: Department name.
            task: Task name.
            
        Returns:
            Optional[str]: Path to saved version or None if failed.
        """
        version = self.core.entities.getHighestVersion(entity, department, task)
        filepath = self.core.generateScenePath(
            entity=entity,
            department=department,
            task=task,
            extension=self.core.appPlugin.getSceneExtension(self),
            version=version
        )

        if self.core.useLocalFiles:
            filepath = self.core.convertPath(filepath, "local")

        if not os.path.exists(os.path.dirname(filepath)):
            try:
                os.makedirs(os.path.dirname(filepath))
            except:
                self.core.popup("The directory could not be created")
                return

        filepath = filepath.replace("\\", "/")
        self.core.startAutosaveTimer(quit=True)

        details = entity.copy()
        details["department"] = department
        details["task"] = task
        details["extension"] = os.path.splitext(filepath)[1]
        details["comment"] = ""
        details["version"] = version
        filepath = self.core.saveScene(filepath=filepath, details=details)
        self.core.sceneOpen()
        if self.core.shouldAutosaveTimerRun():
            self.core.startAutosaveTimer()

        logger.debug("Created scene from current: %s" % filepath)
        return filepath

    @err_catcher(name=__name__)
    def backupScenefile(self, targetFolder: str, bufferMinutes: int = 5) -> bool:
        """Create a backup of the current scene if enough time has passed.
        
        Args:
            targetFolder: Folder to save backup to.
            bufferMinutes: Minimum minutes since last backup before creating new one.
            
        Returns:
            bool: True if backup was created or skipped due to buffer, False if failed.
        """
        filename = self.core.getCurrentFileName()
        if not filename:
            return

        target = os.path.join(targetFolder, "scenefile", os.path.basename(filename))
        if os.path.exists(target):
            mtime = os.path.getmtime(target)
            if time.time() - mtime < (60 * bufferMinutes):
                return

            base, ext = os.path.splitext(os.path.basename(target))
            backupNum = 1
            while True:
                backup = os.path.join(os.path.dirname(target), "_backup", base + "_" + str(backupNum) + ext)
                if not os.path.exists(backup):
                    break
                else:
                    mtime = os.path.getmtime(backup)
                    if time.time() - mtime < (60 * bufferMinutes):
                        return
                    backupNum += 1
            self.core.copySceneFile(target, backup)

        self.core.copySceneFile(filename, target)
        logger.debug("backed up scenefile: %s" % target)

    @err_catcher(name=__name__)
    def addEntityAction(self, key: str, types: List[str], function: callable, label: str) -> None:
        """Register a custom context menu action for entities.
        
        Args:
            key: Unique identifier for the action.
            types: List of entity types this action applies to ('asset', 'shot', etc).
            function: Callable to execute when action is triggered.
            label: Display label for the context menu item.
        """
        self.entityActions[key] = {"types": types, "function": function, "label": label}

    @err_catcher(name=__name__)
    def removeEntityAction(self, key: str) -> None:
        """Remove a registered entity action.
        
        Args:
            key: Unique identifier of the action to remove.
        """
        if key in self.entityActions:
            del self.entityActions[key]
            return True

    @err_catcher(name=__name__)
    def getAssetActions(self) -> Dict[str, Dict]:
        """Get all registered context menu actions for asset entities.
        
        Returns:
            Dict[str, Dict]: Dict of action key -> action data.
        """
        actions = {act: self.entityActions[act] for act in self.entityActions if "asset" in self.entityActions[act]["types"]}
        return actions

    @err_catcher(name=__name__)
    def getShotActions(self) -> Dict[str, Dict]:
        """Get all registered context menu actions for shot entities.
        
        Returns:
            Dict[str, Dict]: Dict of action key -> action data.
        """
        actions = {act: self.entityActions[act] for act in self.entityActions if "shot" in self.entityActions[act]["types"]}
        return actions

    @err_catcher(name=__name__)
    def connectEntityDlg(self, entities: Optional[List[Dict[str, Any]]] = None, parent: Optional[QWidget] = None) -> Optional[List[Dict[str, Any]]]:
        """Show dialog to connect entities to other entities.
        
        Args:
            entities: Optional list of entities to connect.
            parent: Optional parent widget for dialog.
            
        Returns:
            Optional[List[Dict[str, Any]]]: List of connected entities or None if cancelled.
        """
        self.dlg_connectEntities = ConnectEntitiesDlg(self.core, parent)
        self.dlg_connectEntities.navigate(entities)
        self.dlg_connectEntities.show()

    @err_catcher(name=__name__)
    def getConnectedEntities(self, entity: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get all entities connected to the given entity.
        
        Args:
            entity: Entity dict.
            
        Returns:
            List[Dict[str, Any]]: List of connected entity dicts.
        """
        centities = {}
        if not entity:
            return centities

        if entity.get("type") == "asset":
            data = self.core.getConfig(config="assetinfo") or {}
            if "assets" not in data:
                return centities

            if "asset_path" not in entity:
                return centities

            entityName = self.core.entities.getAssetNameFromPath(entity["asset_path"])
            if entityName not in data["assets"]:
                return centities

            centities = copy.deepcopy(data["assets"][entityName].get("connectedEntities", {}))

        elif entity.get("type") == "shot" and "sequence" in entity:
            data = self.core.getConfig(config="shotinfo") or {}
            if "shots" not in data:
                return centities

            if entity["sequence"] not in data["shots"]:
                return centities

            if entity["shot"] not in data["shots"][entity["sequence"]]:
                return centities

            centities = copy.deepcopy(data["shots"][entity["sequence"]][entity["shot"]].get("connectedEntities", {}))

        return centities

    @err_catcher(name=__name__)
    def setConnectedEntities(self, entities: List[Dict[str, Any]], connectedEntities: List[Dict[str, Any]], add: bool = False, remove: bool = False, setReverse: bool = True) -> None:
        """Set or update entity connections.
        
        Args:
            entities: List of entities to set connections for.
            connectedEntities: List of entities to connect to.
            add: If True, add to existing connections instead of replacing.
            remove: If True, remove from existing connections.
            setReverse: If True, also create reverse connections.
        """
        assetInfo = None
        shotInfo = None
        for entity in entities:
            if entity["type"] == "asset" and "asset_path" in entity:
                if assetInfo is None:
                    assetInfo = self.core.getConfig(config="assetinfo", allowCache=False) or {}

                if "assets" not in assetInfo:
                    assetInfo["assets"] = {}

                entityName = self.core.entities.getAssetNameFromPath(entity["asset_path"])
                if entityName not in assetInfo["assets"]:
                    assetInfo["assets"][entityName] = {}

                entityInfo = assetInfo["assets"][entityName]

            elif entity["type"] == "shot":
                if shotInfo is None:
                    shotInfo = self.core.getConfig(config="shotinfo", allowCache=False) or {}

                if "shots" not in shotInfo:
                    shotInfo["shots"] = {}

                if entity["sequence"] not in shotInfo["shots"]:
                    shotInfo["shots"][entity["sequence"]] = {}

                if entity["shot"] not in shotInfo["shots"][entity["sequence"]]:
                    shotInfo["shots"][entity["sequence"]][entity["shot"]] = {}

                entityInfo = shotInfo["shots"][entity["sequence"]][entity["shot"]]

            curEntities = entityInfo.get("connectedEntities", [])
            centities = []
            if add or remove:
                centities = list(curEntities)

            if remove:
                newEntities = []
                toRemoveNames = [self.getEntityName(e) for e in connectedEntities]
                for centity in centities:
                    if self.getEntityName(centity) not in toRemoveNames:
                        newEntities.append(centity)

                centities = [self.getCleanEntity(e) for e in newEntities]
            else:
                to_add = [self.getCleanEntity(e) for e in connectedEntities]
                centities += to_add

            if not remove:
                centityNames = [self.getEntityName(e) for e in centities]
                removed = []
                for curEntity in curEntities:
                    name = self.getEntityName(curEntity)
                    if name not in centityNames:
                        removed.append(curEntity)

                if removed:
                    self.setConnectedEntities(removed, [entity], remove=True, setReverse=False)

            entityInfo["connectedEntities"] = centities

        if setReverse:
            # Build a map of unique connected entities and their occurrence counts,
            # then do a remove-then-add to set the exact count in the reverse direction.
            # This avoids accumulation on repeated Apply clicks while preserving count.
            count_map = {}
            for e in connectedEntities:
                name = self.getEntityName(e)
                if name not in count_map:
                    count_map[name] = [e, 0]
                count_map[name][1] += 1

            for entity_name, (connected_entity, count) in count_map.items():
                # Remove existing reverse connections for `entities`, then add
                # back exactly `count` copies to match the forward count.
                self.setConnectedEntities([connected_entity], entities, remove=True, setReverse=False)
                reverse_entities = []
                for fwd_entity in entities:
                    reverse_entities.extend([fwd_entity] * count)
                self.setConnectedEntities([connected_entity], reverse_entities, add=True, setReverse=False)
        
        if assetInfo:
            self.core.setConfig(data=assetInfo, config="assetinfo", updateNestedData=False)

        if shotInfo:
            self.core.setConfig(data=shotInfo, config="shotinfo", updateNestedData=False)

        return True

    @err_catcher(name=__name__)
    def getCleanEntity(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Create a cleaned copy of entity dict with only essential keys.
        
        Args:
            entity: Entity dict to clean.
            
        Returns:
            Dict[str, Any]: Cleaned entity dict.
        """
        data = {}
        data["type"] = entity.get("type")
        if entity.get("type") == "asset":
            data["asset_path"] = entity.get("asset_path")
        elif entity.get("type") == "shot":
            data["shot"] = entity.get("shot")
            data["sequence"] = entity.get("sequence")

        return data

    @err_catcher(name=__name__)
    def getUniqueEntities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate entities from a list.
        
        Args:
            entities: List of entity dicts.
            
        Returns:
            List[Dict[str, Any]]: List of unique entities.
        """
        data = {}
        for entity in entities:
            uid = self.getEntityName(entity)
            if uid not in data:
                data[uid] = entity

        uentities = list(data.values())
        return uentities

    @err_catcher(name=__name__)
    def getEntityName(self, entity: Dict[str, Any]) -> str:
        """Get the display name for an entity.
        
        Args:
            entity: Entity dict.
            
        Returns:
            str: Entity name for display.
        """
        if not entity:
            return

        name = None
        if entity.get("type") == "asset":
            name = entity.get("asset_path", "").replace("\\", "/")
        elif entity.get("type") == "shot":
            name = self.getShotName(entity)

        return name


class EntityDlg(QDialog):

    entitySelected = Signal(object)

    def __init__(self, origin: Any, parent: Optional[QWidget] = None) -> None:
        """Initialize EntityDlg dialog.
        
        Args:
            origin: Parent widget with core attribute
            parent: Qt parent widget. Defaults to None.
        """
        super(EntityDlg, self).__init__()
        self.origin = origin
        self.parentDlg = parent
        self.core = self.origin.core
        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Set up the entity selection dialog UI.
        
        Creates entity widget with asset/shot tabs and selection buttons.
        """
        title = "Select entity"

        self.setWindowTitle(title)
        self.core.parentWindow(self, parent=self.parentDlg)

        import EntityWidget
        self.w_entities = EntityWidget.EntityWidget(core=self.core, refresh=True)
        self.w_entities.getPage("Assets").tw_tree.itemDoubleClicked.connect(self.itemDoubleClicked)
        self.w_entities.getPage("Shots").tw_tree.itemDoubleClicked.connect(self.itemDoubleClicked)
        self.w_entities.getPage("Assets").setSearchVisible(False)
        self.w_entities.getPage("Shots").setSearchVisible(False)

        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Select", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Close", QDialogButtonBox.RejectRole)

        self.bb_main.clicked.connect(self.buttonClicked)

        self.lo_main.addWidget(self.w_entities)
        self.lo_main.addWidget(self.bb_main)

    @err_catcher(name=__name__)
    def itemDoubleClicked(self, item: Any, column: int) -> None:
        """Handle double-click on entity item.
        
        Args:
            item: Tree widget item
            column: Column index
        """
        self.buttonClicked("select")

    @err_catcher(name=__name__)
    def buttonClicked(self, button: Union[str, Any]) -> None:
        """Handle dialog button clicks.
        
        Args:
            button: Button text or button object
        """
        if button == "select" or button.text() == "Select":
            entities = self.w_entities.getCurrentData()
            if isinstance(entities, dict):
                entities = [entities]

            validEntities = []
            for entity in entities:
                if entity.get("type", "") not in ["asset", "shot"]:
                    continue

                validEntities.append(entity)

            if not validEntities:
                msg = "Invalid entity selected."
                self.core.popup(msg, parent=self)
                return

            self.entitySelected.emit(validEntities[0])

        self.close()

    @err_catcher(name=__name__)
    def sizeHint(self) -> QSize:
        """Get recommended dialog size.
        
        Returns:
            QSize(600, 700)
        """
        return QSize(600, 700)


class ConnectedListWidget(QTreeWidget):
    """A QTreeWidget for displaying connected entities with preview images, similar to EntityWidget."""

    def __init__(self, dlg):
        super(ConnectedListWidget, self).__init__()
        self.dlg = dlg
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.CopyAction)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.dlg.showConnectedListContextMenu)
        
        # Configure tree widget appearance
        self.setColumnCount(1)
        self.setHeaderHidden(True)
        self.setUniformRowHeights(False)
        self.itemDoubleClicked.connect(self._onItemDoubleClicked)
        
        # Preview dimensions (matching EntityWidget)
        self.entityPreviewWidth = 107
        self.entityPreviewHeight = 60

    def _onItemDoubleClicked(self, item, column):
        """Handle double-click to remove item."""
        self.dlg.removeSelectedFromConnected(item)
    
    def setItemPreview(self, item: QTreeWidgetItem, entity: Dict, name: str, count: int) -> None:
        """Set the preview image and text for a tree item.
        
        Creates a custom widget with preview image and label text, matching EntityWidget style.
        """
        w_entity = QWidget()
        w_entity.setStyleSheet("background-color: transparent;")
        lo_entity = QHBoxLayout()
        lo_entity.setContentsMargins(0, 0, 0, 0)
        w_entity.setLayout(lo_entity)
        
        # Preview image label
        l_preview = QLabel()
        # Display name with count suffix
        l_label = QLabel(self._formatDisplayName(name, count))
        
        lo_entity.addWidget(l_preview)
        lo_entity.addWidget(l_label)
        lo_entity.addStretch()
        
        # Load and scale preview
        pm = self.dlg.core.entities.getEntityPreview(entity)
        if not pm:
            pm = self.dlg.core.media.emptyPrvPixmap
        
        if pm:
            pmap = self.dlg.core.media.scalePixmap(pm, self.entityPreviewWidth, self.entityPreviewHeight, fitIntoBounds=False, crop=True)
            l_preview.setPixmap(pmap)
        
        # Set the custom widget as the item display
        self.setItemWidget(item, 0, w_entity)
        item.setText(0, "")  # Clear text since we're using custom widget
    
    def _formatDisplayName(self, name: str, count: int) -> str:
        """Format entity name with count suffix if count > 1."""
        if count > 1:
            return "%s x%s" % (name, count)
        return name

    def dragEnterEvent(self, event):
        if isinstance(event.source(), QTreeWidget) or event.source() is self:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if isinstance(event.source(), QTreeWidget) or event.source() is self:
            if event.source() is self:
                event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.source() is self:
            event.setDropAction(Qt.MoveAction)
            super(ConnectedListWidget, self).dropEvent(event)
        elif isinstance(event.source(), QTreeWidget):
            self.dlg.addSelectedEntitiesToConnected()
            event.accept()
        else:
            event.ignore()


class ConnectEntitiesDlg(QDialog):
    """Dialog for connecting entities to each other.
    
    Allows selecting two entities and creating connections between them.
    
    Attributes:
        core: PrismCore instance
        parentDlg: Parent dialog
    """
    
    def __init__(self, core: Any, parent: Optional[QWidget] = None) -> None:
        """Initialize ConnectEntitiesDlg.
        
        Args:
            core: PrismCore instance
            parent: Parent widget. Defaults to None.
        """
        super(ConnectEntitiesDlg, self).__init__()
        self.parentDlg = parent
        self.core = core
        self._hasPendingChanges = False
        self._connectedSourceEntities = []

        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Set up the connect entities dialog UI.
        
        Creates three panels: left entity selector, middle connected list, right available entities.
        """
        title = "Connect Entities"
        self.setWindowTitle(title)
        self.core.parentWindow(self, parent=self.parentDlg)

        self.w_entitiesParent = QSplitter(Qt.Horizontal)

        # Left panel — entity to connect from
        self.w_selEntities = QWidget()
        self.w_selEntities.setObjectName("w_selEntities")

        # Middle panel — connected entities list
        self.gb_connectedEntities = QGroupBox("Connected Entities")
        self.gb_connectedEntities.setObjectName("gb_connectedEntities")

        # Right panel — available entities to connect to
        self.gb_availableEntities = QGroupBox()
        self.gb_availableEntities.setObjectName("gb_availableEntities")

        self.w_entitiesParent.addWidget(self.w_selEntities)
        self.w_entitiesParent.addWidget(self.gb_connectedEntities)
        self.w_entitiesParent.addWidget(self.gb_availableEntities)
        self.w_entitiesParent.setStretchFactor(0, 1)
        self.w_entitiesParent.setStretchFactor(1, 1)
        self.w_entitiesParent.setStretchFactor(2, 1)

        import EntityWidget

        # Left entity widget
        self.w_entities = EntityWidget.EntityWidget(core=self.core, refresh=True)
        self.w_entities.tabChanged.connect(self.tabChanged)
        self.w_entities.getPage("Assets").itemChanged.connect(self.onSelectedEntityChanged)
        self.w_entities.getPage("Shots").itemChanged.connect(self.onSelectedEntityChanged)
        self.w_entities.getPage("Assets").setSearchVisible(False)
        self.w_entities.getPage("Shots").setSearchVisible(False)

        self.l_info = QLabel()

        self.lo_selEntities = QVBoxLayout()
        self.w_selEntities.setLayout(self.lo_selEntities)
        self.lo_selEntities.addWidget(self.w_entities)
        self.lo_selEntities.addWidget(self.l_info)

        # Middle connected list
        self.lw_connected = ConnectedListWidget(self)

        self.l_connectedInfo = QLabel()

        self.lo_connectedBtns = QHBoxLayout()
        self.b_removeConnected = QPushButton("Disconnect Selected")
        self.lo_connectedBtns.addWidget(self.b_removeConnected)

        self.b_removeConnected.clicked.connect(self.removeSelectedFromConnected)

        self.lo_connected = QVBoxLayout()
        self.gb_connectedEntities.setLayout(self.lo_connected)
        self.lo_connected.addWidget(self.lw_connected)
        self.lo_connected.addWidget(self.l_connectedInfo)
        self.lo_connected.addLayout(self.lo_connectedBtns)

        # Right available entity widget (opposite type, tab hidden)
        self.w_availableEntities = EntityWidget.EntityWidget(core=self.core, refresh=False)
        self.w_availableEntities.getPage("Assets").useCounter = True
        self.w_availableEntities.refreshEntities()
        self.w_availableEntities.tb_entities.setVisible(False)
        self.w_availableEntities.getPage("Assets").setSearchVisible(False)
        self.w_availableEntities.getPage("Shots").setSearchVisible(False)

        for pageName in ("Assets", "Shots"):
            page = self.w_availableEntities.getPage(pageName)
            page.tw_tree.setDragEnabled(True)
            page.tw_tree.itemDoubleClicked.connect(self.addSelectedEntitiesToConnected)
            page.tw_tree.setContextMenuPolicy(Qt.CustomContextMenu)
            page.tw_tree.customContextMenuRequested.connect(self.showAvailableEntityContextMenu)

        self.lo_availableBtns = QHBoxLayout()
        self.b_addConnected = QPushButton("Connect Selected")
        self.b_addConnected.clicked.connect(self.addSelectedEntitiesToConnected)
        self.lo_availableBtns.addWidget(self.b_addConnected)

        self.lo_available = QVBoxLayout()
        self.gb_availableEntities.setLayout(self.lo_available)
        self.lo_available.addWidget(self.w_availableEntities)
        self.lo_available.addLayout(self.lo_availableBtns)

        self.refreshEntityInfo()
        self.refreshConnectedEntityInfo()

        self.tabChanged()

        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Apply", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Close", QDialogButtonBox.RejectRole)

        self.bb_main.accepted.connect(self.onAccepted)
        self.bb_main.rejected.connect(self.reject)

        self.lo_main.addWidget(self.w_entitiesParent)
        self.lo_main.addWidget(self.bb_main)

    @err_catcher(name=__name__)
    def sizeHint(self) -> QSize:
        """Get recommended dialog size.
        
        Returns:
            QSize(1400, 700)
        """
        return QSize(1400, 700)

    @err_catcher(name=__name__)
    def _getEntityKey(self, entity: Dict) -> str:
        """Get a unique key for an entity based on its type and path."""
        entity_type = entity.get("type")
        if entity_type == "asset":
            return ("asset", entity.get("asset_path"))
        elif entity_type == "shot":
            return ("shot", entity.get("sequence"), entity.get("shot"))
        return None

    @err_catcher(name=__name__)
    def _formatEntityDisplayName(self, name: str, count: int) -> str:
        """Format entity name with count suffix if count > 1."""
        if count > 1:
            return "%s x%s" % (name, count)
        return name

    @err_catcher(name=__name__)
    def _findConnectedListItem(self, entity: Dict) -> Optional[QTreeWidgetItem]:
        """Find an item in lw_connected with the same entity key."""
        key = self._getEntityKey(entity)
        for i in range(self.lw_connected.topLevelItemCount()):
            item = self.lw_connected.topLevelItem(i)
            stored_entity = item.data(0, Qt.UserRole)
            if self._getEntityKey(stored_entity) == key:
                return item
        return None

    @err_catcher(name=__name__)
    def _getValidEntities(self, entities: List[Dict]) -> List[Dict]:
        """Filter and return valid asset/shot entities."""
        return [
            e
            for e in entities
            if e.get("type") in ["asset", "shot"] and ("asset_path" in e or "shot" in e)
        ]

    @err_catcher(name=__name__)
    def _promptPendingChanges(self, actionLabel: str) -> bool:
        """Prompt to apply or ignore unsaved connection changes."""
        if not self._hasPendingChanges:
            return True

        msg = (
            "You have unsaved connection changes.\n\n"
            "Apply them before %s?\n\n"
            "Choose \"Ignore\" to discard these pending changes."
        ) % actionLabel
        action = self.core.popupQuestion(
            msg,
            buttons=["Apply", "Ignore"],
            icon=QMessageBox.Warning,
            parent=self,
            escapeButton="Ignore",
        )

        if action == "Apply":
            source_entities = list(self._connectedSourceEntities)
            if not self._applyConnections(sourceEntities=source_entities, showConfirmation=False):
                return False
        else:
            self._hasPendingChanges = False

        return True

    @err_catcher(name=__name__)
    def _handlePendingChangesBeforeContextSwitch(self) -> bool:
        """Prompt to apply or ignore unsaved connection changes before switching context."""
        return self._promptPendingChanges("switching the selection")

    @err_catcher(name=__name__)
    def _handlePendingChangesBeforeClose(self) -> bool:
        """Prompt to apply or ignore unsaved connection changes before closing."""
        return self._promptPendingChanges("closing this window")

    @err_catcher(name=__name__)
    def _applyConnections(self, sourceEntities: Optional[List[Dict]] = None, showConfirmation: bool = True) -> bool:
        """Apply the current connected-list state to the selected source entities."""
        if sourceEntities is None:
            sourceEntities = self.w_entities.getCurrentData(returnOne=False)

        entities = self._getValidEntities(sourceEntities or [])
        if not entities:
            msg = "No valid entity selected."
            self.core.popup(msg)
            return False

        connectedEntities = []
        connectedNames = []
        for i in range(self.lw_connected.topLevelItemCount()):
            item = self.lw_connected.topLevelItem(i)
            entity = item.data(0, Qt.UserRole)
            count = item.data(0, Qt.UserRole + 1) or 1
            if entity and entity.get("type") in ["asset", "shot"] and (entity.get("asset_path") or entity.get("shot")):
                for _ in range(count):
                    connectedEntities.append(entity)

                name = self.core.entities.getEntityName(entity)
                if count > 1:
                    name = "%s x%s" % (name, count)
                connectedNames.append(name)

        result = self.core.entities.setConnectedEntities(entities, connectedEntities)
        if not result:
            return False

        self._hasPendingChanges = False

        if showConfirmation:
            entityNames = [self.core.entities.getEntityName(e) for e in entities]
            connectedNames = connectedNames or ["-"]

            sourceList = "\n  • ".join(entityNames) if entityNames else "-"
            targetList = "\n  • ".join(connectedNames)
            msg = "Entity Connections were set successfully:\n\n\nSource:\n  • %s\n\n\nConnected to:\n  • %s" % (sourceList, targetList)
            self.core.popup(msg, severity="info", parent=self)

        return True

    @err_catcher(name=__name__)
    def addSelectedEntitiesToConnected(self, item=None, column=None) -> None:
        """Add the currently selected available entities to the connected list.
        
        Groups duplicates with count suffix (e.g., "AssetName x3").
        Uses the useCounter value to add multiple copies when the counter is > 1.
        """
        page = self.w_availableEntities.getCurrentPage()
        items = page.tw_tree.selectedItems()
        changed = False
        for treeItem in items:
            entity = page.getDataFromItem(treeItem)
            if not entity or entity.get("type") not in ["asset", "shot"]:
                continue
            if not (entity.get("asset_path") or entity.get("shot")):
                continue
            count = page.getCount(treeItem) if page.useCounter else 1
            if count < 1:
                continue
            
            # Find if this entity already exists in the list
            existing = self._findConnectedListItem(entity)
            if existing is not None:
                # Increment count on existing item
                existing_count = existing.data(0, Qt.UserRole + 1) or 1
                new_count = existing_count + count
                existing.setData(0, Qt.UserRole + 1, new_count)
                name = self.core.entities.getEntityName(entity)
                # Update the preview widget with new count
                self.lw_connected.setItemPreview(existing, entity, name, new_count)
                changed = True
            else:
                # Add new item with count and preview
                name = self.core.entities.getEntityName(entity)
                lwItem = QTreeWidgetItem()
                lwItem.setData(0, Qt.UserRole, entity)
                lwItem.setData(0, Qt.UserRole + 1, count)
                self.lw_connected.addTopLevelItem(lwItem)
                # Set the preview widget
                self.lw_connected.setItemPreview(lwItem, entity, name, count)
                changed = True
            
            if page.useCounter:
                page.setCount(treeItem, 0)

        if changed:
            self._hasPendingChanges = True
        self.refreshConnectedEntityInfo()

    @err_catcher(name=__name__)
    def removeSelectedFromConnected(self, item=None) -> None:
        """Remove items from the connected list.
        
        If item is provided (from itemDoubleClicked), removes that item or decrements its count.
        Otherwise removes all currently selected items.
        """
        if item is not None:
            items = [item]
        else:
            items = self.lw_connected.selectedItems()

        changed = False
        
        for lwItem in items:
            current_count = lwItem.data(0, Qt.UserRole + 1) or 1
            if current_count > 1:
                # Decrement count
                new_count = current_count - 1
                lwItem.setData(0, Qt.UserRole + 1, new_count)
                entity = lwItem.data(0, Qt.UserRole)
                name = self.core.entities.getEntityName(entity)
                # Update the preview widget with decremented count
                self.lw_connected.setItemPreview(lwItem, entity, name, new_count)
                changed = True
            else:
                # Remove completely
                index = self.lw_connected.indexOfTopLevelItem(lwItem)
                self.lw_connected.takeTopLevelItem(index)
                changed = True

        if changed:
            self._hasPendingChanges = True
        self.refreshConnectedEntityInfo()

    @err_catcher(name=__name__)
    def clearConnected(self) -> None:
        """Clear all items from the connected entities list."""
        if self.lw_connected.topLevelItemCount() > 0:
            self._hasPendingChanges = True
        self.lw_connected.clear()
        self.refreshConnectedEntityInfo()

    @err_catcher(name=__name__)
    def showConnectedListContextMenu(self, pos) -> None:
        """Show context menu for the connected entities list."""
        menu = QMenu(self)
        menu.addAction("Add Selected Available", self.addSelectedEntitiesToConnected)
        menu.addSeparator()
        menu.addAction("Remove Selected", self.removeSelectedFromConnected)
        menu.addAction("Clear All", self.clearConnected)
        menu.exec_(self.lw_connected.mapToGlobal(pos))

    @err_catcher(name=__name__)
    def showAvailableEntityContextMenu(self, pos) -> None:
        """Show context menu for the available entities tree."""
        sender = self.sender()
        menu = QMenu(self)
        menu.addAction("Add to Connected", self.addSelectedEntitiesToConnected)
        menu.exec_(sender.mapToGlobal(pos))

    @err_catcher(name=__name__)
    def onAccepted(self) -> None:
        """Handle Apply button click.
        
        Sets the entity connections and shows confirmation message.
        """
        self._applyConnections(showConfirmation=True)

    @err_catcher(name=__name__)
    def reject(self) -> None:
        """Handle dialog close requests and guard against losing unsaved changes."""
        if not self._handlePendingChangesBeforeClose():
            return

        super(ConnectEntitiesDlg, self).reject()

    @err_catcher(name=__name__)
    def tabChanged(self) -> None:
        """Handle tab change between Assets and Shots.
        
        Updates the available entities widget to show the opposite type.
        """
        if not self._handlePendingChangesBeforeContextSwitch():
            return

        self.w_availableEntities.tb_entities.setCurrentIndex(not bool(self.w_entities.tb_entities.currentIndex()))
        self.gb_availableEntities.setTitle("Available %s" % self.w_availableEntities.getCurrentPageName())
        self.selectConnectedEntities()
        self.refreshEntityInfo()
        self.refreshConnectedEntityInfo()

    @err_catcher(name=__name__)
    def onSelectedEntityChanged(self, items: Optional[Any] = None) -> None:
        """Handle selection change in entity widget.
        
        Args:
            items: Selected items
        """
        self.refreshEntityInfo(items)
        if not self._handlePendingChangesBeforeContextSwitch():
            return

        self.selectConnectedEntities()

    @err_catcher(name=__name__)
    def selectConnectedEntities(self) -> None:
        """Populate the connected list with entities connected to the current selection."""
        all_entities = self.w_entities.getCurrentData(returnOne=False)
        self._connectedSourceEntities = self._getValidEntities(all_entities or [])

        entities = list(self._connectedSourceEntities)
        # Only use the first selected entity to avoid duplicate counts
        entities = entities[:1] if entities else []
        connected = []
        for entity in entities:
            connected += self.core.entities.getConnectedEntities(entity)

        self.lw_connected.clear()
        
        # Group entities by key and count occurrences
        entity_map = {}
        for entity in connected:
            key = self._getEntityKey(entity)
            if key not in entity_map:
                entity_map[key] = (entity, 0)
            entity_obj, count = entity_map[key]
            entity_map[key] = (entity_obj, count + 1)

        # Add to list with counts and preview images
        for (entity_obj, count) in entity_map.values():
            name = self.core.entities.getEntityName(entity_obj)
            if not name:
                continue
            lwItem = QTreeWidgetItem()
            lwItem.setData(0, Qt.UserRole, entity_obj)
            lwItem.setData(0, Qt.UserRole + 1, count)
            self.lw_connected.addTopLevelItem(lwItem)
            # Set the preview widget
            self.lw_connected.setItemPreview(lwItem, entity_obj, name, count)

        self._hasPendingChanges = False
        self.refreshConnectedEntityInfo()

    @err_catcher(name=__name__)
    def refreshEntities(self) -> None:
        """Refresh both entity widgets."""
        self.w_entities.refreshEntities()
        self.w_availableEntities.refreshEntities()

    @err_catcher(name=__name__)
    def refreshEntityInfo(self, items: Optional[Any] = None) -> None:
        """Update the entity selection info label.
        
        Args:
            items: Items to show info for (defaults to selected items)
        """
        page = self.w_entities.getCurrentPage()
        if items is None:
            items = page.tw_tree.selectedItems()
        elif not isinstance(items, list):
            items = [items]

        if page.useCounter:
            entities = []
            for item in items:
                entity = page.getDataFromItem(item)
                if entity["type"] in ["asset", "shot"]:
                    for idx in range(page.getCount(item)):
                        entities.append(entity)

        else:
            entities = [page.getDataFromItem(item) for item in items]
            entities = [entity for entity in entities if entity["type"] in ["asset", "shot"]]

        if page.entityType == "asset":
            if len(entities) == 1:
                text = "%s Asset selected" % len(entities)
            else:
                text = "%s Assets selected" % len(entities)
        else:
            if len(entities) == 1:
                text = "%s Shot selected" % len(entities)
            else:
                text = "%s Shots selected" % len(entities)

        self.l_info.setText(text)

    @err_catcher(name=__name__)
    def refreshConnectedEntityInfo(self, items: Optional[Any] = None) -> None:
        """Update the connected entities count label."""
        count = self.lw_connected.topLevelItemCount()
        if count == 1:
            text = "1 Entity connected"
        else:
            text = "%s Entities connected" % count
        self.l_connectedInfo.setText(text)

    @err_catcher(name=__name__)
    def navigate(self, entities: List[Dict]) -> None:
        """Navigate entity widget to show specific entities.
        
        Args:
            entities: List of entity dictionaries to navigate to
        """
        self.w_entities.navigate(entities)
