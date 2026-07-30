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
import re
import logging
from typing import Any, Optional, List, Dict, Tuple
from collections import OrderedDict

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class PathManager(object):
    """Manages file path generation and manipulation for the Prism pipeline.
    
    Handles scene file paths, render output paths, cache paths, and product paths.
    Manages path conversions between different storage locations (global/local/custom).
    Provides utilities for path parsing, version extraction, and entity type detection.
    
    Attributes:
        core: Reference to the Prism core instance.
        masterManager: Reference to MasterManager class for version management.
    """
    
    def __init__(self, core: Any) -> None:
        """Initialize the PathManager.
        
        Args:
            core: Reference to the Prism core instance.
        """
        super(PathManager, self).__init__()
        self.core = core
        self.masterManager = MasterManager

    @err_catcher(name=__name__)
    def getCompositingOut(
        self,
        taskName: Optional[str],
        fileType: Optional[str],
        useVersion: Optional[str],
        render: bool,
        location: str = "global",
        comment: str = "",
        ignoreEmpty: bool = False,
        node: Any = None,
        entity: Optional[Any] = None
    ) -> str:
        """Generate output path for compositing renders.
        
        Creates output paths for 2D compositing renders based on current scene context.
        Handles version management, creates directories, and tracks render state.
        
        Args:
            taskName: Name of the compositing task/identifier.
            fileType: Output file format extension.
            useVersion: Version string to use (if separate version stack enabled).
            render: If True, creates folders and starts render tracking.
            location: Storage location ('global' or custom). Defaults to 'global'.
            comment: Optional version comment.
            ignoreEmpty: If True, allows reusing existing versions with files.
            node: Optional node reference for render tracking.
            entity: Optional entity to use for path calculation.
            
        Returns:
            str: Output file path pattern, or 'FileNotInPipeline' if scene not in pipeline.
        """
        if not entity:
            fileName = self.core.getCurrentFileName()
            if self.core.fileInPipeline(filepath=fileName, validateFilename=False):
                entity = self.core.getScenefileData(fileName)

            else:
                # logger.debug("not in pipeline: %s" % fileName)
                outputPath = "FileNotInPipeline"

        if entity:
            if taskName is None:
                taskName = ""

            if not self.core.separateOutputVersionStack:
                version = entity.get("version")
            else:
                version = useVersion

            fileType = fileType or ""
            extension = "." + fileType
            framePadding = "#" * self.core.framePadding if extension not in self.core.media.videoFormats else ""
            outputData = self.core.mediaProducts.generateMediaProductPath(
                entity=entity,
                task=taskName,
                version=version,
                extension=extension,
                ignoreEmpty=ignoreEmpty,
                framePadding=framePadding,
                mediaType="2drenders",
                comment=comment,
                location=location,
                returnDetails=True,
            )

            if outputData:
                outputPath = outputData["path"].replace("\\", "/")
            else:
                # logger.debug("no output data: %s - %s - %s - %s" % (entity, taskName, version, extension))
                outputPath = "FileNotInPipeline"

        if render and outputPath != "FileNotInPipeline":
            expandedOutputpath = os.path.expandvars(outputPath)
            expandedOutputpath = expandedOutputpath.replace("%PRISM_JOB", os.getenv("PRISM_JOB"))
            if not os.path.exists(os.path.dirname(expandedOutputpath)):
                try:
                    os.makedirs(os.path.dirname(expandedOutputpath))
                except:
                    self.core.popup("Could not create output folder")

            details = outputData.copy()
            details["sourceScene"] = self.core.getCurrentFileName()
            filepath = os.path.dirname(expandedOutputpath)
            self.core.saveVersionInfo(
                filepath=filepath,
                details=details,
            )
            if self.core.getConfig("globals", "backupScenesOnPublish", config="project"):
                self.core.entities.backupScenefile(filepath)

            if node:
                self.core.appPlugin.startedRendering(node, outputPath)
            else:
                self.core.appPlugin.isRendering = [True, outputPath]
        else:
            if node:
                if self.core.appPlugin.isNodeRendering(node):
                    return self.core.appPlugin.getPathFromRenderingNode(node)
            else:
                if self.core.appPlugin.isRendering[0]:
                    return self.core.appPlugin.isRendering[1]

        return outputPath

    @err_catcher(name=__name__)
    def getMediaConversionOutputPath(
        self,
        context: Dict,
        inputpath: str,
        extension: str,
        addFramePadding: bool = True
    ) -> str:
        """Generate output path for media format conversions.
        
        Args:
            context: Context dict with entity, version, and media type information.
            inputpath: Path to input media file.
            extension: Target file extension for conversion.
            addFramePadding: If True, adds frame padding for image sequences.
            
        Returns:
            str: Output path for converted media.
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

        videoFormats = self.core.media.videoFormats

        context = context.copy()
        if "asset_path" in context:
            context["asset"] = os.path.basename(context["asset_path"])

        context["extension"] = extension
        if extension in videoFormats or not addFramePadding:
            context["frame"] = ""
        else:
            context["frame"] = "%%0%sd" % self.core.framePadding

        context["layer"] = ""
        mode = os.getenv("PRISM_MEDIA_CONVERSION_OUTPUT_MODE", "same_folder")
        if mode == "version_suffix":
            context["version"] = context["version"] + " (%s)" % extension[1:]
        elif mode == "same_folder":
            pass
        elif mode == "next_version":
            context["version"] = self.core.mediaProducts.getHighestMediaVersion(context)

        outputPath = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )
        return outputPath

    @err_catcher(name=__name__)
    def getEntityPath(
        self,
        entity: Optional[Dict] = None,
        step: Optional[str] = None,
        category: Optional[str] = None,
        reqEntity: Optional[str] = None,
        location: str = "global"
    ) -> str:
        """Get file system path for an entity or department.
        
        Args:
            entity: Entity dict containing type ('asset', 'shot', etc.) and entity data.
            step: Optional department/step name.
            category: Optional category within the department.
            reqEntity: If 'step', returns parent department folder path.
            location: Storage location. Defaults to 'global'.
            
        Returns:
            str: File system path for the entity or empty string if invalid.
        """
        if entity.get("type") not in ["asset", "assetFolder", "shot", "sequence"]:
            return ""

        context = entity.copy()
        if step:
            context["department"] = step
            path = self.core.projects.getResolvedProjectStructurePath(
                "departments", context
            )

            odlPrj = (
                self.core.compareVersions(self.core.projectVersion, "v1.2.1.6")
                == "lower"
            )
            if (entity["type"] != "asset" or not odlPrj) and category:
                path = os.path.join(path, category)
        elif reqEntity == "step":
            path = self.core.projects.getResolvedProjectStructurePath(
                "departments", context
            )
            path = os.path.dirname(path)
        else:
            if entity["type"] in ["asset", "assetFolder"]:
                path = self.core.projects.getResolvedProjectStructurePath(
                    "assets", entity
                )
            elif entity["type"] == "shot":
                if context.get("sequence") == "_episode":
                    path = self.core.projects.getResolvedProjectStructurePath(
                        "episodes", context
                    )
                elif context.get("shot") == "_sequence":
                    path = self.core.projects.getResolvedProjectStructurePath(
                        "sequences", context
                    )
                else:
                    path = self.core.projects.getResolvedProjectStructurePath(
                        "shots", context
                    )
            elif entity["type"] == "sequence":
                path = self.core.projects.getResolvedProjectStructurePath(
                    "sequences", context
                )

        path = self.core.convertPath(path, location)
        return path.replace("\\", "/")

    @err_catcher(name=__name__)
    def generateScenePath(
        self,
        entity: Dict,
        department: str,
        task: str = "",
        extension: str = "",
        version: str = "",
        comment: str = "",
        user: str = "",
        location: Optional[str] = None,
    ) -> str:
        """Generate a scene file path based on entity and task information.
        
        Creates properly formatted scene file paths following project structure templates.
        Automatically determines next version if not specified.
        
        Args:
            entity: Entity dict with asset or shot information.
            department: Department/step name (e.g., 'modeling', 'animation').
            task: Task name within the department. Defaults to empty.
            extension: File extension. Defaults to empty.
            version: Version string. Auto-generates if empty.
            comment: Optional version comment. Defaults to empty.
            user: User name. Uses current user if empty.
            location: Storage location. Uses 'global' if None.
            
        Returns:
            str: Complete scene file path, or empty string if invalid entity.
        """
        user = user or self.core.user
        location = location or "global"
        context = entity.copy()
        context.update({
            "project_path": self.core.projectPath,
            "project_name": self.core.projectName,
            "department": department,
            "task": task,
            "version": version,
            "comment": comment,
            "user": user,
            "extension": extension,
        })

        if not context["version"]:
            dstentity = entity.copy()
            if "project_path" in dstentity:
                del dstentity["project_path"]

            context["version"] = self.core.entities.getHighestVersion(
                dstentity, department, task
            )
        if entity["type"] == "asset":
            if (
                self.core.compareVersions(self.core.projectVersion, "v1.2.1.6")
                == "lower"
            ):
                context["task"] = ""

            context["asset"] = os.path.basename(entity["asset_path"])
            context["asset_path"] = entity["asset_path"]
            if "sequence" in context:
                del context["sequence"]

            if "shot" in context:
                del context["shot"]

            scenePath = self.core.projects.getResolvedProjectStructurePath(
                "assetScenefiles", context=context
            )
        elif entity["type"] == "shot":
            context["sequence"] = entity["sequence"]
            context["shot"] = entity["shot"]
            if "asset" in context:
                del context["asset"]

            if "asset_path" in context:
                del context["asset_path"]

            scenePath = self.core.projects.getResolvedProjectStructurePath(
                "shotScenefiles", context=context
            )
        else:
            return ""

        scenePath = self.core.convertPath(scenePath, location)
        return scenePath

    @err_catcher(name=__name__)
    def getCachePathData(
        self,
        cachePath: str,
        addPathData: bool = True,
        validateModTime: bool = False,
        allowCache: bool = True
    ) -> Dict:
        """Get metadata and path information for a cache file or folder.
        
        Reads cache version info and extracts path-based metadata.
        
        Args:
            cachePath: Path to cache file or folder.
            addPathData: If True, extracts additional data from path structure.
            validateModTime: If True, clears cache if modification time changed.
            allowCache: If True, allows using cached config data.
            
        Returns:
            Dict: Cache metadata including version, entity, user, locations, etc.
        """
        if not cachePath:
            return {}

        cachePath = os.path.normpath(cachePath)
        if os.path.splitext(cachePath)[1]:
            cacheDir = os.path.dirname(cachePath)
        else:
            cacheDir = cachePath

        cacheConfig = self.core.getVersioninfoPath(cacheDir)
        if validateModTime:
            mdate = self.core.getFileModificationDate(cacheConfig, asString=False)
            cacheDate = self.core.configs.getCacheTime(cacheConfig)
            if cacheDate and cacheDate != mdate:
                self.core.configs.clearCache(path=cacheConfig)

        cacheData = self.core.getConfig(configPath=cacheConfig, allowCache=allowCache) or {}
        cacheData = cacheData.copy()
        if addPathData:
            if os.path.splitext(cachePath)[1]:
                pathData = self.core.products.getProductDataFromFilepath(cachePath)
            else:
                pathData = self.core.products.getProductDataFromVersionFolder(cachePath)

            cacheData.update(pathData)

        if "_" in (cacheData.get("version") or "") and len(cacheData["version"].split("_")) == 2:
            cacheData["version"], cacheData["wedge"] = cacheData["version"].split("_")

        cacheData["locations"] = {}
        loc = self.core.paths.getLocationFromPath(os.path.normpath(cachePath))
        if len(self.core.paths.getExportProductBasePaths()) > 1:
            globalPath = self.core.convertPath(os.path.normpath(cacheDir), "global")
            if os.path.exists(os.path.normpath(globalPath)):
                cacheData["locations"]["global"] = globalPath

        if self.core.useLocalFiles:
            localPath = self.core.convertPath(os.path.normpath(cacheDir), "local")
            if os.path.exists(localPath):
                cacheData["locations"]["local"] = localPath

        if loc and loc not in ["global", "local"]:
            cacheData["locations"][loc] = cachePath

        return cacheData

    @err_catcher(name=__name__)
    def getMediaProductData(self, productPath: str, isFilepath: bool = True, addPathData: bool = True, mediaType: Optional[str] = None, validateModTime: bool = False, isVersionFolder: bool = False) -> Dict[str, Any]:
        """Get metadata for media product (render or playblast).
        
        Routes to getRenderProductData or getPlayblastProductData based on mediaType.
        
        Args:
            productPath: Path to product file or version folder
            isFilepath: If True, path is to a file; if False, to a folder
            addPathData: If True, extract and add path metadata
            mediaType: Media type ('3drenders', '2drenders', 'playblasts', etc.)
            validateModTime: If True, invalidate cache if file modified
            isVersionFolder: If True, path is to version folder not file
            
        Returns:
            Dict with product metadata (version, user, comment, paths, locations, etc.)
        """
        mediaType = mediaType or "3drenders"
        if mediaType == "playblasts":
            return self.getPlayblastProductData(productPath, isFilepath=isFilepath, addPathData=addPathData, validateModTime=validateModTime, isVersionFolder=isVersionFolder)
        else:
            return self.getRenderProductData(productPath, isFilepath=isFilepath, addPathData=addPathData, mediaType=mediaType, validateModTime=validateModTime, isVersionFolder=isVersionFolder)

    @err_catcher(name=__name__)
    def getRenderProductData(self, productPath: str, isFilepath: bool = True, addPathData: bool = True, mediaType: Optional[str] = None, validateModTime: bool = False, isVersionFolder: bool = False, allowCache: bool = True) -> Dict[str, Any]:
        """Get metadata for render product.
        
        Reads versioninfo config and extracts metadata from product path.
        Handles multiple locations (global, local, custom).
        
        Args:
            productPath: Path to render file or version folder
            isFilepath: If True, path is to a file; if False, to a folder
            addPathData: If True, extract and add path-derived metadata
            mediaType: Media type ('3drenders', '2drenders', etc.)
            validateModTime: If True, clear cache if file modified
            isVersionFolder: If True, path is to version folder
            allowCache: If True, use cached config data
            
        Returns:
            Dict with render product metadata including locations, entity info, version, etc.
        """
        productPath = os.path.normpath(productPath)
        mediaType = mediaType or "3drenders"
        if os.path.splitext(productPath)[1]:
            productConfig = self.core.mediaProducts.getMediaVersionInfoPathFromFilepath(productPath, mediaType=mediaType)
        else:
            productConfig = os.path.join(
                productPath, "versioninfo" + self.core.configs.getProjectExtension()
            )

        if validateModTime:
            mdate = self.core.getFileModificationDate(productConfig, asString=False)
            cacheDate = self.core.configs.getCacheTime(productConfig)
            if cacheDate and cacheDate != mdate:
                self.core.configs.clearCache(path=productConfig)

        productData = self.core.getConfig(configPath=productConfig, allowCache=allowCache) or {}
        if addPathData:
            if isVersionFolder:
                pathData = self.core.mediaProducts.getMediaDataFromVersionFolder(productPath, mediaType=mediaType)
            else:
                pathData = self.core.mediaProducts.getRenderProductDataFromFilepath(productPath, mediaType=mediaType)
                if not pathData or (pathData.get("type") == "asset" and "asset_path" not in pathData) or (pathData.get("type") == "shot" and "shot" not in pathData):
                    if mediaType == "2drenders":
                        productVersionPath = os.path.dirname(productPath)
                    else:
                        productVersionPath = os.path.dirname(os.path.dirname(productPath))

                    newPathData = self.getRenderProductData(
                        productVersionPath,
                        isFilepath=False,
                        addPathData=addPathData,
                        mediaType=mediaType,
                        validateModTime=validateModTime,
                        isVersionFolder=True,
                        allowCache=allowCache
                    )
                    if newPathData:
                        pathData = newPathData

            productData.update(pathData)

        productData["locations"] = {}
        productData["mediaType"] = mediaType
        loc = self.core.paths.getLocationFromPath(os.path.normpath(productPath))
        if len(self.core.paths.getRenderProductBasePaths()) > 1:
            globalPath = self.core.convertPath(os.path.normpath(productPath), "global")
            if os.path.exists(os.path.normpath(globalPath)):
                productData["locations"]["global"] = globalPath

        if self.core.useLocalFiles:
            localPath = self.core.convertPath(os.path.normpath(productPath), "local")
            if os.path.exists(localPath):
                productData["locations"]["local"] = localPath

        if loc and loc not in ["global", "local"]:
            productData["locations"][loc] = productPath

        productData["path"] = productPath
        return productData

    @err_catcher(name=__name__)
    def getPlayblastProductData(self, productPath: str, isFilepath: bool = True, addPathData: bool = True, validateModTime: bool = False, isVersionFolder: bool = False) -> Dict[str, Any]:
        """Get metadata for playblast product.
        
        Reads playblast versioninfo config and extracts metadata from path.
        
        Args:
            productPath: Path to playblast file or version folder
            isFilepath: If True, path is to a file; if False, to a folder
            addPathData: If True, extract and add path-derived metadata
            validateModTime: If True, clear cache if file modified
            isVersionFolder: If True, path is to version folder
            
        Returns:
            Dict with playblast metadata including locations, entity info, version, etc.
        """
        productPath = os.path.normpath(productPath)
        if os.path.splitext(productPath)[1]:
            productConfig = self.core.mediaProducts.getPlayblastVersionInfoPathFromFilepath(productPath)
        else:
            productConfig = os.path.join(
                productPath, "versioninfo" + self.core.configs.getProjectExtension()
            )

        if validateModTime:
            mdate = self.core.getFileModificationDate(productConfig, asString=False)
            cacheDate = self.core.configs.getCacheTime(productConfig)
            if cacheDate and cacheDate != mdate:
                self.core.configs.clearCache(path=productConfig)

        productData = self.core.getConfig(configPath=productConfig) or {}
        productData["mediaType"] = "playblasts"
        if addPathData:
            if isVersionFolder:
                pathData = self.core.mediaProducts.getMediaDataFromVersionFolder(productPath, mediaType="playblasts")
            else:
                pathData = self.core.mediaProducts.getRenderProductDataFromFilepath(productPath, mediaType="playblasts")

            productData.update(pathData)

        return productData

    @err_catcher(name=__name__)
    def requestPath(
        self,
        title: str = "Select folder",
        startPath: str = "",
        parent: Optional[QWidget] = None
    ) -> str:
        """Show a folder selection dialog.
        
        Args:
            title: Dialog title. Defaults to 'Select folder'.
            startPath: Initial directory path. Defaults to empty.
            parent: Optional parent widget. Uses core messageParent if None.
            
        Returns:
            str: Selected folder path, or empty string if canceled.
        """
        path = ""
        parent = parent or self.core.messageParent
        if self.core.uiAvailable:
            path = QFileDialog.getExistingDirectory(
                parent,
                title,
                startPath,
            )

        return path

    @err_catcher(name=__name__)
    def requestFilepath(
        self,
        title: str = "Select File",
        startPath: str = "",
        parent: Optional[QWidget] = None,
        fileFilter: str = "All files (*.*)",
        saveDialog: bool = True
    ) -> str:
        """Show a file selection dialog.
        
        Args:
            title: Dialog title. Defaults to 'Select File'.
            startPath: Initial directory path. Defaults to empty.
            parent: Optional parent widget. Uses core messageParent if None.
            fileFilter: File filter string. Defaults to 'All files (*.*)'.
            saveDialog: If True, shows save dialog. If False, shows open dialog.
            
        Returns:
            str: Selected file path, or empty string if canceled.
        """
        path = ""
        parent = parent or self.core.messageParent
        if self.core.uiAvailable:
            if saveDialog:
                path = QFileDialog.getSaveFileName(parent, title, startPath, fileFilter)[0]
            else:
                path = QFileDialog.getOpenFileName(parent, title, startPath, fileFilter)[0]

        return path

    @err_catcher(name=__name__)
    def convertExportPath(self, path: str, fromLocation: str, toLocation: str) -> str:
        """Convert an export product path from one location to another.
        
        Args:
            path: Path to convert.
            fromLocation: Source location name.
            toLocation: Target location name.
            
        Returns:
            str: Converted path with new base location.
        """
        bases = self.getExportProductBasePaths()
        baseFrom = bases[fromLocation]
        baseTo = bases[toLocation]

        if not baseFrom.endswith(os.sep):
            baseFrom += os.sep

        if not baseTo.endswith(os.sep):
            baseTo += os.sep

        cPath = path.replace(baseFrom, baseTo)
        return cPath

    @err_catcher(name=__name__)
    def addExportProductBasePath(self, location: str, path: str, configData: Optional[Dict] = None) -> Optional[bool]:
        """Add or update a custom export product base path.
        
        Args:
            location: Location name (e.g., 'custom1').
            path: Filesystem path for this location.
            configData: Optional config dict to update instead of saving to project.
            
        Returns:
            Optional[bool]: True if path already exists, None otherwise. If configData provided, returns updated dict.
        """
        exportPaths = self.getExportProductBasePaths(
            default=False, configData=configData
        )
        if location in exportPaths and path == exportPaths[location]:
            return True

        exportPaths[location] = path
        if configData:
            configData["export_paths"] = exportPaths
            return configData
        else:
            self.core.setConfig("export_paths", val=exportPaths, config="project")

    @err_catcher(name=__name__)
    def addRenderProductBasePath(self, location: str, path: str, configData: Optional[Dict] = None) -> Optional[bool]:
        """Add or update a custom render product base path.
        
        Args:
            location: Location name (e.g., 'custom1').
            path: Filesystem path for this location.
            configData: Optional config dict to update instead of saving to project.
            
        Returns:
            Optional[bool]: True if path already exists, None otherwise. If configData provided, returns updated dict.
        """
        renderPaths = self.getRenderProductBasePaths(
            default=False, configData=configData
        )
        if location in renderPaths and path == renderPaths[location]:
            return True

        renderPaths[location] = path
        if configData:
            configData["render_paths"] = renderPaths
            return configData
        else:
            self.core.setConfig("render_paths", val=renderPaths, config="project")

    @err_catcher(name=__name__)
    def removeExportProductBasePath(self, location: str, configData: Optional[Dict] = None) -> Optional[Dict]:
        """Remove a custom export product base path.
        
        Args:
            location: Location name to remove.
            configData: Optional config dict to update instead of saving to project.
            
        Returns:
            Optional[Dict]: Updated config dict if configData was provided, None otherwise.
        """
        exportPaths = self.getExportProductBasePaths(
            default=False, configData=configData
        )
        if location in exportPaths:
            del exportPaths[location]

            if configData:
                configData["export_paths"] = exportPaths
                return configData
            else:
                self.core.setConfig("export_paths", val=exportPaths, config="project")

    @err_catcher(name=__name__)
    def removeRenderProductBasePath(self, location: str, configData: Optional[Dict] = None) -> Optional[Dict]:
        """Remove a custom render product base path.
        
        Args:
            location: Location name to remove.
            configData: Optional config dict to update instead of saving to project.
            
        Returns:
            Optional[Dict]: Updated config dict if configData was provided, None otherwise.
        """
        renderPaths = self.getRenderProductBasePaths(
            default=False, configData=configData
        )
        if location in renderPaths:
            del renderPaths[location]

            if configData:
                configData["render_paths"] = renderPaths
                return configData
            else:
                self.core.setConfig("render_paths", val=renderPaths, config="project")

    @err_catcher(name=__name__)
    def getExportProductBasePaths(self, default: bool = True, configPath: Optional[str] = None, configData: Optional[Dict] = None) -> OrderedDict:
        """Get all configured export product base paths.
        
        Args:
            default: Whether to include default paths (global, local). Defaults to True.
            configPath: Optional path to config file. Uses project config if None.
            configData: Optional config dict to read from instead of file.
            
        Returns:
            OrderedDict: Mapping of location names to filesystem paths.
        """
        export_paths = OrderedDict([])
        if default:
            if hasattr(self.core, "projectPath"):
                export_paths["global"] = self.core.projectPath

            if self.core.useLocalFiles:
                export_paths["local"] = self.core.localProjectPath

        if configData:
            customPaths = configData.get("export_paths", [])
        else:
            if not configPath:
                configPath = self.core.prismIni

            customPaths = self.core.getConfig(
                "export_paths", configPath=configPath, dft=[]
            )

        for cp in customPaths:
            export_paths[cp] = customPaths[cp]

        for path in export_paths:
            export_paths[path] = os.path.normpath(export_paths[path])

        return export_paths

    @err_catcher(name=__name__)
    def getRenderProductBasePaths(self, default: bool = True, configPath: Optional[str] = None, configData: Optional[Dict] = None) -> OrderedDict:
        """Get all configured render product base paths.
        
        Args:
            default: Whether to include default paths (global, local). Defaults to True.
            configPath: Optional path to config file. Uses project config if None.
            configData: Optional config dict to read from instead of file.
            
        Returns:
            OrderedDict: Mapping of location names to filesystem paths.
        """
        render_paths = OrderedDict([])
        if not self.core.projects.hasActiveProject():
            return render_paths

        if default:
            render_paths["global"] = self.core.projectPath

            if self.core.useLocalFiles:
                render_paths["local"] = self.core.localProjectPath

        if configData:
            customPaths = configData.get("render_paths", [])
            prjName = configData.get("project_name", "")
        else:
            if configPath:
                prjName = self.core.getConfig(
                    "project_name", configPath=configPath, dft=[]
                )
            else:
                configPath = self.core.prismIni
                prjName = self.core.projectName

            customPaths = self.core.getConfig(
                "render_paths", configPath=configPath, dft=[]
            )

        for cp in customPaths:
            render_paths[cp] = customPaths[cp]

        for path in render_paths:
            render_paths[path] = os.path.normpath(render_paths[path].replace("@project_name@", prjName))

        return render_paths

    @err_catcher(name=__name__)
    def convertGlobalRenderPath(self, path: str, target: str = "global") -> str:
        """Convert a render path from global location to another location.
        
        Args:
            path: Path to convert.
            target: Target location name. Defaults to 'global'.
            
        Returns:
            str: Converted path.
        """
        path = os.path.normpath(path)
        basepaths = self.getRenderProductBasePaths()
        prjPath = os.path.normpath(self.core.projectPath)
        convertedPath = os.path.normpath(path).replace(prjPath, basepaths[target])
        return convertedPath

    @err_catcher(name=__name__)
    def replaceVersionInStr(self, inputStr: str, replacement: str) -> str:
        """Replace all version strings in a string with a new value.
        
        Args:
            inputStr: String containing version patterns (e.g., 'v0001').
            replacement: Replacement version string.
            
        Returns:
            str: String with versions replaced.
        """
        versions = re.findall("v[0-9]{%s}" % self.core.versionPadding, inputStr)
        replacedStr = inputStr
        for version in versions:
            replacedStr = replacedStr.replace(version, replacement)

        return replacedStr

    @err_catcher(name=__name__)
    def getFrameFromFilename(self, filename: str) -> Optional[str]:
        """Extract frame number from a filename.
        
        Args:
            filename: Filename to parse.
            
        Returns:
            Optional[str]: Frame number string, or None if not found.
        """
        filename = os.path.basename(filename)
        base, ext = os.path.splitext(filename)
        match = re.search("[0-9]{%s}$" % self.core.framePadding, base)
        if not match:
            return

        frame = match.group(0)
        return frame

    @err_catcher(name=__name__)
    def getLocationFromPath(self, path: str) -> Optional[str]:
        """Determine the storage location name from a path.
        
        Checks both export and render product paths.
        
        Args:
            path: Path to check.
            
        Returns:
            Optional[str]: Location name ('global', 'local', or custom), or None if not found.
        """
        locations = []
        productPaths = self.getExportProductBasePaths()
        for ppath in productPaths:
            if path.startswith(productPaths[ppath]):
                locations.append(ppath)

        if locations:
            return sorted(locations, key=lambda x: len(productPaths[x]), reverse=True)[0]

        locations = []
        renderPaths = self.getRenderProductBasePaths()
        for rpath in renderPaths:
            if path.startswith(renderPaths[rpath]):
                locations.append(rpath)

        if locations:
            return sorted(locations, key=lambda x: len(renderPaths[x]), reverse=True)[0]

    @err_catcher(name=__name__)
    def getLocationPath(self, locationName: str) -> Optional[str]:
        """Get the filesystem path for a storage location name.
        
        Args:
            locationName: Location name to look up.
            
        Returns:
            Optional[str]: Filesystem path, or None if location not found.
        """
        if locationName == "global":
            return self.core.projectPath
        elif self.core.useLocalFiles and locationName == "local":
            return self.core.localProjectPath
        else:
            productPaths = self.getExportProductBasePaths()
            if locationName in productPaths:
                return productPaths[locationName]

            renderPaths = self.getRenderProductBasePaths()
            if locationName in renderPaths:
                return renderPaths[locationName]

    @err_catcher(name=__name__)
    def splitext(self, path: str) -> List[str]:
        """Split path into root and extension, with special handling for compound extensions.
        
        Handles special cases like '.bgeo.sc'.
        
        Args:
            path: File path to split.
            
        Returns:
            List[str]: [root, extension] pair.
        """
        if path.endswith(".bgeo.sc"):
            return [path[: -len(".bgeo.sc")], ".bgeo.sc"]
        else:
            return os.path.splitext(path)

    @err_catcher(name=__name__)
    def getEntityTypeFromPath(self, path: str, projectPath: Optional[str] = None) -> Optional[str]:
        """Determine entity type from a project path.
        
        Args:
            path: Path to analyze.
            projectPath: Optional project path for path resolution.
            
        Returns:
            Optional[str]: 'asset' or 'shot', or None if cannot be determined.
        """
        globalPath = self.core.convertPath(path, "global")
        globalPath = os.path.normpath(globalPath)
        globalPath = os.path.splitdrive(globalPath)[1]
        assetPath = self.core.assetPath
        if projectPath:
            assetPath = assetPath.replace(os.path.normpath(self.core.projectPath), projectPath)

        assetPath = os.path.splitdrive(assetPath)[1]

        useEpisodes = self.core.getConfig(
            "globals",
            "useEpisodes",
            config="project",
        ) or False

        if useEpisodes:
            sequencePath = self.core.episodePath
        else:
            sequencePath = self.core.sequencePath

        if projectPath:
            sequencePath = sequencePath.replace(os.path.normpath(self.core.projectPath), projectPath)

        sequencePath = os.path.splitdrive(sequencePath)[1]
        if globalPath.startswith(assetPath):
            return "asset"
        elif globalPath.startswith(sequencePath):
            return "shot"


class MasterManager(QDialog):
    """Dialog for managing master version updates across multiple entities.
    
    Displays outdated master versions and provides batch update functionality.
    Can manage both cache products and media renders.
    
    Attributes:
        core: Reference to Prism core instance.
        mode: Operating mode - 'products' or 'media'.
        entities: List of entity dicts to check for updates.
        outdatedVersions (List[Dict]): List of versions needing master updates.
    """
    
    def __init__(self, core: Any, entities: List[Dict], mode: str, parent: Any = None) -> None:
        """Initialize MasterManager dialog.
        
        Args:
            core: PrismCore instance
            entities: List of entity dictionaries to check
            mode: 'products' or 'mediaProducts'
            parent: Parent widget. Defaults to None.
        """
        super(MasterManager, self).__init__()
        self.core = core
        self.core.parentWindow(self, parent=parent)
        self.mode = mode
        self.entities = entities
        self.outdatedVersions = []
        self.setupUi()

    @err_catcher(name=__name__)
    def showEvent(self, event: Any) -> None:
        """Handle dialog show event.
        
        Refreshes the versions table when dialog is shown.
        
        Args:
            event: Qt show event
        """
        self.refreshTable()

    @err_catcher(name=__name__)
    def sizeHint(self) -> QSize:
        """Get recommended dialog size.
        
        Returns:
            QSize(700, 500)
        """
        return QSize(700, 500)

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Set up the master manager dialog UI.
        
        Creates table showing outdated versions with update buttons.
        """
        self.setWindowTitle("Master Version Manager")
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.tw_versions = QTableWidget()
        self.tw_versions.setColumnCount(5)
        self.tw_versions.setSortingEnabled(True)
        self.tw_versions.setHorizontalHeaderLabels(
            ["Entity", "Identifier", "Master", "Latest", ""]
        )
        self.tw_versions.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        self.tw_versions.verticalHeader().setDefaultSectionSize(25)
        self.tw_versions.horizontalHeader().setStretchLastSection(True)
        self.tw_versions.verticalHeader().hide()
        self.tw_versions.horizontalHeader().setHighlightSections(False)
        self.tw_versions.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tw_versions.setShowGrid(False)
        self.tw_versions.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tw_versions.customContextMenuRequested.connect(self.showContextMenu)
        self.tw_versions.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tw_versions.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tw_versions.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tw_versions.itemDoubleClicked.connect(self.onItemDoubleClicked)

        self.bb_main = QDialogButtonBox()
        self.bb_main.addButton("Update all", QDialogButtonBox.AcceptRole)
        self.bb_main.addButton("Cancel", QDialogButtonBox.RejectRole)

        self.bb_main.accepted.connect(self.onAcceptClicked)
        self.bb_main.rejected.connect(self.reject)

        self.lo_main.addWidget(self.tw_versions)
        self.lo_main.addWidget(self.bb_main)

    @err_catcher(name=__name__)
    def refreshTable(self) -> None:
        """Populate table with outdated version data.
        
        Creates table rows for each outdated version showing entity, department,
        task, identifier, current version, latest version, and path.
        """
        twSorting = [
            self.tw_versions.horizontalHeader().sortIndicatorSection(),
            self.tw_versions.horizontalHeader().sortIndicatorOrder(),
        ]
        self.tw_versions.setSortingEnabled(False)

        self.tw_versions.setRowCount(0)
        for versionData in self.outdatedVersions:
            master = versionData["master"]
            latest = versionData["latest"]
            if latest.get("type") == "asset":
                entityName = latest["asset_path"]
            elif latest.get("type") == "shot":
                entityName = self.core.entities.getShotName(latest)

            entityItem = QTableWidgetItem(entityName)
            entityItem.setData(Qt.UserRole, versionData)

            if "product" in latest:
                identifier = latest["product"]
            elif "identifier" in latest:
                identifier = latest["identifier"]

            idItem = QTableWidgetItem(identifier)
            
            if master:
                if self.mode == "products":
                    masterVersion = self.core.products.getMasterVersionNumber(master["path"])
                else:
                    masterVersion = self.core.mediaProducts.getMasterVersionNumber(master["path"])
            else:
                masterVersion = "-"

            masterItem = QTableWidgetItem(masterVersion)
            if master:
                masterItem.setToolTip(master["path"])

            latestItem = QTableWidgetItem(latest["version"])
            latestItem.setToolTip(latest["path"])

            rc = self.tw_versions.rowCount()
            self.tw_versions.insertRow(rc)

            self.tw_versions.setItem(rc, 0, entityItem)
            self.tw_versions.setItem(rc, 1, idItem)
            self.tw_versions.setItem(rc, 2, masterItem)
            self.tw_versions.setItem(rc, 3, latestItem)
            b_update = QPushButton("Update")
            b_update.setStyleSheet("background-color: rgba(250, 250, 250, 20);")
            b_update.clicked.connect(lambda x=None, vd=versionData: self.onUpdateMasterClicked(vd))
            b_update.clicked.connect(self.refreshData)
            b_update.clicked.connect(self.refreshTable)
            b_update.clicked.connect(self.refreshProjectBrowserVersions)
            self.tw_versions.setCellWidget(rc, 4, b_update)

        self.tw_versions.resizeRowsToContents()
        self.tw_versions.resizeColumnsToContents()
        self.tw_versions.setColumnWidth(0, self.tw_versions.columnWidth(0) + 20)
        self.tw_versions.setColumnWidth(1, self.tw_versions.columnWidth(1) + 20)
        self.tw_versions.setColumnWidth(2, self.tw_versions.columnWidth(2) + 20)
        self.tw_versions.setColumnWidth(3, self.tw_versions.columnWidth(3) + 20)
        self.tw_versions.sortByColumn(twSorting[0], twSorting[1])
        self.tw_versions.setSortingEnabled(True)

    @err_catcher(name=__name__)
    def onItemDoubleClicked(self, item: Any) -> None:
        """Handle double-click on table item.
        
        Opens the version in Project Browser.
        
        Args:
            item: Table widget item that was double-clicked
        """
        data = self.tw_versions.item(item.row(), 0).data(Qt.UserRole)
        self.openInProjectBrowser(data["latest"]["path"])

    @err_catcher(name=__name__)
    def showContextMenu(self, pos: Any) -> None:
        """Show right-click context menu.
        
        Provides options to update selected versions, show in Project Browser, or refresh.
        
        Args:
            pos: Mouse position for menu
        """
        rcmenu = QMenu(self)

        if self.tw_versions.selectedItems():
            exp = QAction("Update Selected", self)
            exp.triggered.connect(self.updateSelected)
            rcmenu.addAction(exp)

        item = self.tw_versions.itemAt(pos)
        if item:
            exp = QAction("Show in Project Browser", self)
            exp.triggered.connect(lambda x=None, i=item: self.onItemDoubleClicked(i))
            rcmenu.addAction(exp)

        exp = QAction("Refresh", self)
        exp.triggered.connect(self.refreshData)
        exp.triggered.connect(self.refreshTable)
        rcmenu.addAction(exp)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def updateSelected(self) -> None:
        """Update master versions for all selected table rows.
        
        Shows wait popup while updating, then refreshes data and UI.
        """
        text = "Updating versions. Please wait..."
        with self.core.waitPopup(self.core, text):
            for item in self.tw_versions.selectedItems():
                if item.column() != 0:
                    continue

                versionData = item.data(Qt.UserRole)
                self.updateMaster(versionData)

        self.refreshData()
        self.refreshTable()
        self.refreshProjectBrowserVersions()

    @err_catcher(name=__name__)
    def openInProjectBrowser(self, path: str) -> None:
        """Open the Project Browser and navigate to the given path.
        
        Shows and focuses Project Browser, then navigates to the version.
        
        Args:
            path: Version path to navigate to
        """
        if self.core.pb:
            self.core.pb.show()
            self.core.pb.activateWindow()
            self.core.pb.raise_()
            self.core.pb.checkVisibleTabs()
            if self.core.pb.isMinimized():
                self.core.pb.showNormal()
        else:
            self.core.projectBrowser()

        if self.mode == "products":
            self.core.pb.showTab("Products")
            data = self.core.paths.getCachePathData(path)
            self.core.pb.productBrowser.navigateToProduct(data["product"], entity=data)
        else:
            self.core.pb.showTab("Media")
            data = self.core.paths.getRenderProductData(path)
            self.core.pb.mediaBrowser.showRender(identifier=data.get("identifier"), entity=data, version=data.get("version"))

    @err_catcher(name=__name__)
    def refreshData(self) -> None:
        """Get outdated master versions for entities.
        
        Shows wait popup while fetching version data.
        """
        text = "Getting version data. Please wait..."
        with self.core.waitPopup(self.core, text):
            if self.mode == "products":
                result = self.core.products.getOutdatedMasterVersions(self.entities)
            else:
                result = self.core.mediaProducts.getOutdatedMasterVersions(self.entities)
    
        self.outdatedVersions = result

    @err_catcher(name=__name__)
    def onUpdateMasterClicked(self, versionData: Dict[str, Any]) -> None:
        """Handle update master button click for single version.
        
        Args:
            versionData: Version data dictionary
        """
        text = "Updating version. Please wait..."
        with self.core.waitPopup(self.core, text):
            self.updateMaster(versionData)

    @err_catcher(name=__name__)
    def updateMaster(self, versionData: Dict[str, Any]) -> None:
        """Update master version to latest for single version.
        
        Args:
            versionData: Version data dict with 'latest' and 'master' keys
        """
        if self.mode == "products":
            filepath = self.core.products.getPreferredFileFromVersion(versionData["latest"])
            self.core.products.updateMasterVersion(filepath)
        else:
            self.core.mediaProducts.updateMasterVersion(context=versionData["latest"])

    @err_catcher(name=__name__)
    def refreshProjectBrowserVersions(self) -> None:
        """Refresh version displays in Project Browser after updating."""
        if self.core.pb:
            if self.mode == "products":
                self.core.pb.productBrowser.updateVersions(restoreSelection=True)
            else:
                self.core.pb.mediaBrowser.updateVersions(restoreSelection=True)

    @err_catcher(name=__name__)
    def onAcceptClicked(self) -> None:
        """Handle accept button click - update all outdated master versions."""
        text = "Updating versions. Please wait..."
        with self.core.waitPopup(self.core, text):
            for versionData in self.outdatedVersions:
                self.updateMaster(versionData)

        self.refreshData()
        self.refreshTable()
        self.refreshProjectBrowserVersions()
        if self.outdatedVersions:
            return
        
        msg = "All versions updated successfully."
        self.core.popup(msg, severity="info")
        self.accept()
