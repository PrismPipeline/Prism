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

from PrismUtils.Decorators import err_catcher


class PathManager(object):
    def __init__(self, core):
        super(PathManager, self).__init__()
        self.core = core

    @err_catcher(name=__name__)
    def getCompositingOut(
        self,
        taskName,
        fileType,
        useLastVersion,
        render,
        localOutput=False,
        comment="",
        ignoreEmpty=True,
    ):
        fileName = self.core.getCurrentFileName()
        fnameData = self.core.getScenefileData(fileName)

        if taskName is None:
            taskName = ""

        if not self.core.separateOutputVersionStack:
            version = fnameData.get("version")
        else:
            version = None

        if fnameData.get("entity") == "asset":
            assetBase = fnameData.get("basePath").rsplit("Scenefiles", 1)[0]
            fullEntityName = self.core.entities.getAssetRelPathFromPath(assetBase)
        else:
            fullEntityName = fnameData.get("entityName")

        outputName, version = self.getOutputPath(
            outputType="2dRender",
            entity=fnameData.get("entity"),
            entityName=fullEntityName,
            step=fnameData.get("step"),
            category=fnameData.get("category"),
            task=taskName,
            version=version,
            fileType=fileType,
            useLastVersion=useLastVersion,
            ignoreEmpty=ignoreEmpty,
            comment=comment,
            localOutput=localOutput,
        )

        if render and outputName != "FileNotInPipeline":
            if not os.path.exists(os.path.dirname(outputName)):
                try:
                    os.makedirs(os.path.dirname(outputName))
                except:
                    self.core.popup("Could not create output folder")

            data = {
                "outputType": "2dRender",
                "entity": fnameData.get("entity"),
                "entityName": fullEntityName,
                "step": fnameData.get("step"),
                "category": fnameData.get("category"),
                "task": taskName,
                "version": version,
                "fileType": fileType,
                "comment": comment,
            }

            self.core.saveVersionInfo(
                location=os.path.dirname(outputName),
                version=version,
                data=data,
                origin=self.core.getCurrentFileName(),
            )
            self.core.appPlugin.isRendering = [True, outputName]
        else:
            if self.core.appPlugin.isRendering[0]:
                return self.core.appPlugin.isRendering[1]

        return outputName

    @err_catcher(name=__name__)
    def getOutputPath(
        self,
        outputType,
        entity,
        entityName,
        step,
        category,
        task,
        version=None,
        fileType=None,
        useLastVersion=False,
        ignoreEmpty=True,
        comment="",
        localOutput=False,
    ):
        fileType = fileType or "exr"
        singleFileFormats = ["avi", "mp4", "mov"]
        padding = "." if fileType in singleFileFormats else ".####."

        if entity == "asset":
            outputPath = os.path.join(
                self.core.assetPath,
                entityName,
                "Rendering",
                "2dRender",
                task,
            )
            if not version:
                version = self.core.getHighestTaskVersion(
                    outputPath, getExisting=useLastVersion, ignoreEmpty=ignoreEmpty
                )

            outputFile = (
                os.path.basename(entityName)
                + self.core.filenameSeparator
                + task
                + self.core.filenameSeparator
                + version
                + padding
                + fileType
            )
        elif entity == "shot":
            outputPath = os.path.join(
                self.core.shotPath,
                entityName,
                "Rendering",
                "2dRender",
                task,
            )
            if not version:
                version = self.core.getHighestTaskVersion(
                    outputPath, getExisting=useLastVersion, ignoreEmpty=ignoreEmpty
                )
            outputFile = (
                "shot"
                + self.core.filenameSeparator
                + entityName
                + self.core.filenameSeparator
                + task
                + self.core.filenameSeparator
                + version
                + padding
                + fileType
            )
        else:
            outputName = "FileNotInPipeline"
            outputFile = ""

        if outputFile != "":
            outputPath = os.path.join(outputPath, version)
            if comment != "":
                outputPath += self.core.filenameSeparator + comment
            outputName = os.path.join(outputPath, outputFile)

        if localOutput:
            outputName = self.core.convertPath(outputName, target="local")
        else:
            outputName = self.core.convertPath(outputName, target="global")

        outputName = outputName.replace("\\", "/")

        return outputName, version

    @err_catcher(name=__name__)
    def getMediaConversionOutputPath(self, task, inputpath, extension):
        if (
            task.endswith(" (external)")
            or task.endswith(" (2d)")
            or task.endswith(" (playblast)")
        ):
            outputpath = os.path.join(
                os.path.dirname(inputpath) + "(%s)" % extension[1:],
                os.path.basename(inputpath),
            )
        else:
            outputpath = os.path.join(
                os.path.dirname(os.path.dirname(inputpath)) + "(%s)" % extension[1:],
                os.path.basename(os.path.dirname(inputpath)),
                os.path.basename(inputpath),
            )

        vf = self.core.mediaProducts.videoFormats
        inputExt = os.path.splitext(inputpath)[1]
        videoInput = inputExt in vf

        if extension in vf and inputExt not in vf:
            outputpath = os.path.splitext(outputpath)[0][:-5] + extension
        elif videoInput and extension not in vf:
            outputpath = "%s.%%04d%s".replace("4", str(self.core.framePadding)) % (os.path.splitext(outputpath)[0], extension)
        else:
            outputpath = os.path.splitext(outputpath)[0] + extension

        return outputpath

    @err_catcher(name=__name__)
    def getEntityBasePath(self, filepath):
        basePath = ""

        if self.core.useLocalFiles and filepath.startswith(self.core.localProjectPath):
            location = "local"
        else:
            location = "global"

        if filepath.startswith(self.core.getAssetPath(location=location)):
            prjVersion = getattr(self.core, "projectVersion", None)
            if prjVersion and self.core.compareVersions(prjVersion, "v1.2.1.6") == "lower":
                basePath = os.path.join(filepath, os.pardir, os.pardir, os.pardir)
            else:
                basePath = os.path.join(
                    filepath, os.pardir, os.pardir, os.pardir, os.pardir
                )

        elif filepath.startswith(self.core.getShotPath(location=location)):
            basePath = os.path.join(
                filepath, os.pardir, os.pardir, os.pardir, os.pardir
            )

        return os.path.abspath(basePath)

    @err_catcher(name=__name__)
    def getEntityBasePathFromProductPath(self, filepath):
        basePath = os.path.join(
            filepath, os.pardir, os.pardir, os.pardir, os.pardir, os.pardir
        )

        return os.path.abspath(basePath)

    @err_catcher(name=__name__)
    def getEntityPath(self, entity=None, asset=None, sequence=None, shot=None, step=None, category=None):
        if asset:
            if os.path.isabs(asset):
                asset = self.core.entities.getAssetRelPathFromPath(asset)
            base = self.core.getAssetPath()
            path = os.path.join(base, asset)
        elif shot:
            base = self.core.getShotPath()
            if sequence:
                shot = self.core.entities.getShotname(sequence, shot)
            path = os.path.join(base, shot)
        else:
            return ""

        if entity == "step" and not step:
            path = os.path.join(path, "Scenefiles")

        if step:
            path = os.path.join(path, "Scenefiles", step)

            odlPrj = self.core.compareVersions(self.core.projectVersion, "v1.2.1.6") == "lower"
            if (not asset or not odlPrj) and category:
                path = os.path.join(path, category)

        return path.replace("\\", "/")

    @err_catcher(name=__name__)
    def generateScenePath(
        self,
        entity,
        entityName,
        step,
        assetPath="",
        category="",
        extension="",
        basePath="",
        version="",
        comment="",
        user="",
    ):
        if entity == "asset":
            # example filename: Body_mod_v0002_details-added_rfr_.max
            assetPath = assetPath or basePath

            if (
                os.path.basename(os.path.dirname(assetPath)) == "Scenefiles"
                or os.path.basename(os.path.dirname(os.path.dirname(assetPath)))
                == "Scenefiles"
            ):
                dstname = assetPath
            else:
                dstname = self.getEntityPath(asset=assetPath, step=step, category=category)

            if self.core.compareVersions(self.core.projectVersion, "v1.2.1.6") == "lower":
                category = ""
            else:
                category = (category or "") + self.core.filenameSeparator

            version = version or self.core.entities.getHighestVersion(dstname, "asset")
            user = user or self.core.user

            fileName = (
                entityName
                + self.core.filenameSeparator
                + step
                + self.core.filenameSeparator
                + category
                + version
                + self.core.filenameSeparator
                + comment
                + self.core.filenameSeparator
                + user
            )
        elif entity == "shot":
            # example filename: shot_a-0010_mod_main_v0002_details-added_rfr_.max
            basePath = basePath or self.core.shotPath
            if (
                os.path.basename(os.path.dirname(os.path.dirname(basePath)))
                == "Scenefiles"
            ):
                dstname = basePath
            else:
                dstname = self.getEntityPath(shot=entityName, step=step, category=category)

            version = version or self.core.entities.getHighestVersion(dstname, "shot")
            user = user or self.core.user

            fileName = (
                "shot"
                + self.core.filenameSeparator
                + entityName
                + self.core.filenameSeparator
                + step
                + self.core.filenameSeparator
                + category
            )
            fileName += (
                self.core.filenameSeparator
                + version
                + self.core.filenameSeparator
                + comment
                + self.core.filenameSeparator
                + user
            )
        else:
            return ""

        if extension:
            fileName += self.core.filenameSeparator + extension

        scenePath = os.path.join(dstname, fileName)

        return scenePath

    @err_catcher(name=__name__)
    def getCachePathData(self, cachePath):
        cachePath = os.path.normpath(cachePath)
        if os.path.splitext(cachePath)[1]:
            cacheDir = os.path.dirname(cachePath)
        else:
            cacheDir = cachePath

        cacheConfig = os.path.join(cacheDir, "versioninfo.yml")
        if not os.path.exists(cacheConfig):
            cacheConfig = os.path.join(os.path.dirname(cacheDir), "versioninfo.yml")
        cacheData = self.core.getConfig(configPath=cacheConfig) or {}

        taskPath = os.path.dirname(os.path.dirname(cacheDir))
        cacheData["task"] = os.path.basename(taskPath)

        entityPath = os.path.dirname(os.path.dirname(taskPath))

        relAssetPath = self.core.assetPath.replace(self.core.projectPath, "")
        relShotPath = self.core.shotPath.replace(self.core.projectPath, "")
        if relAssetPath in entityPath:
            cacheData["entityType"] = "asset"
            cacheData["assetHierarchy"] = self.core.entities.getAssetRelPathFromPath(entityPath)
            cacheData["assetName"] = os.path.basename(cacheData["assetHierarchy"])
            cacheData["entity"] = cacheData["assetName"]
        elif relShotPath in entityPath:
            cacheData["entityType"] = "shot"
            shot, seq = self.core.entities.splitShotname(os.path.basename(entityPath))
            cacheData["sequence"] = seq
            cacheData["shot"] = shot
            cacheData["entity"] = cacheData["shot"]
        else:
            cacheData["entityType"] = ""

        cacheData["extension"] = os.path.splitext(cachePath)[1]
        cacheData["version"] = cacheData.get("information", {}).get("Version", "")
        if not cacheData["version"]:
            cacheData["version"] = cacheData.get("information", {}).get("version", "")

        return cacheData
