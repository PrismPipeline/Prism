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
import sys
import logging
import shutil

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

import CreateItem


logger = logging.getLogger(__name__)


class ProjectEntities(object):
    def __init__(self, core):
        self.core = core
        self.refreshOmittedEntities()

        eDirs = [
                "Scenefiles",
                "Export",
                "Playblasts",
                "Rendering/3dRender",
                "Rendering/2dRender",
            ]
        self.entityFolders = {"asset": eDirs, "shot": eDirs}

    @err_catcher(name=__name__)
    def refreshOmittedEntities(self):
        self.omittedEntities = {"asset": [], "shot": []}
        omits = self.core.getConfig(config="omit") or {}

        oShots = omits.get("shot") or []
        oAssets = omits.get("asset") or []

        self.omittedEntities["shot"] = oShots
        self.omittedEntities["asset"] = oAssets
        self.omittedEntities["assetFolder"] = oAssets

    @err_catcher(name=__name__)
    def splitShotname(self, shotName):
        if shotName and self.core.sequenceSeparator in shotName:
            sname = shotName.split(self.core.sequenceSeparator, 1)
            seqName = sname[0]
            shotName = sname[1]
        else:
            seqName = "no sequence"
            shotName = shotName

        return shotName, seqName

    @err_catcher(name=__name__)
    def getShotname(self, sequence, shot):
        shotname = sequence + self.core.sequenceSeparator + shot
        return shotname

    @err_catcher(name=__name__)
    def setShotRange(self, shotName, start, end):
        self.core.setConfig("shotRanges", shotName, [start, end], config="shotinfo")

    @err_catcher(name=__name__)
    def getShotRange(self, shotName):
        return self.core.getConfig("shotRanges", shotName, config="shotinfo")

    @err_catcher(name=__name__)
    def getShots(self, searchFilter="", locations=None):
        export_paths = self.core.paths.getExportProductBasePaths()
        relShotPath = self.core.shotPath.replace(os.path.normpath(self.core.projectPath), "")
        seqDirs = []
        for location in export_paths:
            if locations is not None and location not in locations:
                continue
            seqDir = {"location": location, "path": export_paths[location] + relShotPath}
            seqDirs.append(seqDir)

        sequences = []
        shots = []

        shotDirs = []
        for seqDir in seqDirs:
            for root, folders, files in os.walk(seqDir["path"]):
                for f in folders:
                    if f.startswith("_"):
                        continue

                    sPath = os.path.join(root, f)
                    data = {"location": seqDir["location"], "path": sPath}
                    shotDirs.append(data)
                break

        for shotDir in sorted(shotDirs, key=lambda x: x["path"]):
            path = shotDir["path"]
            val = os.path.basename(path)

            if val in self.omittedEntities["shot"]:
                continue

            shotName, seqName = self.core.entities.splitShotname(val)
            if searchFilter not in seqName and searchFilter not in shotName:
                continue

            if shotName:
                for shot in shots:
                    if seqName == shot[0] and shotName == shot[1]:
                        shot[3].append(shotDir)
                        break
                else:
                    shotData = [seqName, shotName, val, [shotDir]]
                    shots.append(shotData)

            if seqName not in sequences:
                sequences.append(seqName)

        sequences = sorted(sequences)
        shots = sorted(shots, key=lambda x: self.core.naturalKeys(x[1]))

        if "no sequence" in sequences:
            sequences.insert(
                len(sequences), sequences.pop(sequences.index("no sequence"))
            )

        return sequences, shots

    @err_catcher(name=__name__)
    def getSteps(self, asset=None, shot=None):
        steps = []

        if asset:
            path = self.core.getEntityPath(entity="step", asset=asset)
        elif shot:
            path = self.core.getEntityPath(entity="step", shot=shot)

        stepDirs = [path]

        if self.core.useLocalFiles:
            path = self.core.convertPath(path, target="global")
            lpath = self.core.convertPath(path, target="local")
            stepDirs = [path, lpath]

        dirContent = []

        for sDir in stepDirs:
            if os.path.exists(sDir):
                dirContent += [os.path.join(sDir, x) for x in os.listdir(sDir)]

        for i in sorted(dirContent, key=lambda x: os.path.basename(x)):
            stepName = os.path.basename(i)
            if stepName.startswith("_"):
                continue

            if os.path.isdir(i) and stepName not in steps:
                steps.append(stepName)

        return steps

    @err_catcher(name=__name__)
    def getCategories(self, asset=None, shot=None, step=None):
        cats = []

        if asset:
            path = self.core.getEntityPath(asset=asset, step=step)
        elif shot:
            path = self.core.getEntityPath(shot=shot, step=step)

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

        return cats

    @err_catcher(name=__name__)
    def getScenefiles(self, asset=None, shot=None, step=None, category=None, extensions=None):
        extensions = extensions or "*"
        scenefiles = []

        if asset:
            if (
                self.core.compareVersions(self.core.projectVersion, "v1.2.1.6")
                == "lower"
            ):
                path = self.core.getEntityPath(asset=asset, step=step)
            else:
                path = self.core.getEntityPath(asset=asset, step=step, category=category)
        elif shot:
            path = self.core.getEntityPath(
                shot=shot,
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

                    if self.isValidScenefilename(f, extensions=extensions):
                        sfiles[f] = os.path.join(root, f)
                break

        scenefiles = sfiles.values()

        return scenefiles

    @err_catcher(name=__name__)
    def isValidScenefilename(self, filename, extensions=None):
        extensions = extensions or "*"
        sData = self.core.getScenefileData(filename)

        if sData["entity"] not in ["asset", "shot"]:
            return False

        try:
            int(sData["extension"][-5:])  # ignore maya temp files
            return False
        except Exception:
            pass

        if "extension" not in sData:
            return False

        if sData["extension"].endswith("~"):  # ignore nuke autosave files
            return False

        if filename.endswith(".painter_lock"):  # ignore substance painter lock files
            return False

        if filename.endswith("autosave"):
            return False

        uScene = (
            sData["extension"] not in self.core.getPluginSceneFormats()
            and "info" not in sData["extension"]
            and "preview" not in sData["extension"]
        )

        if (
            sData["extension"] not in extensions
            and not ("*" in extensions and uScene)
        ):
            return False

        return True

    @err_catcher(name=__name__)
    def getDependencies(self, path):
        info = self.core.getVersioninfoPath(path)
        deps = []
        source = self.core.getConfig("information", "source scene", configPath=info)
        if source:
            deps.append(source)

        depPaths = self.core.getConfig("information", "Dependencies", configPath=info) or []
        deps += depPaths
        extFiles = self.core.getConfig("information", "External files", configPath=info) or []
        deps += extFiles

        return deps

    @err_catcher(name=__name__)
    def getCurrentDependencies(self):
        deps = getattr(self.core.appPlugin, "getImportPaths", lambda x: None)(self.core) or []

        if type(deps) == str:
            deps = eval(deps.replace("\\", "/").replace("//", "/"))
        deps = [str(x[0]) for x in deps]

        extFiles = getattr(
            self.core.appPlugin, "sm_getExternalFiles", lambda x: [[], []]
        )(self.core)[0]
        extFiles = list(set(extFiles))

        return {"dependencies": deps, "externalFiles": extFiles}

    @err_catcher(name=__name__)
    def createEntity(self, entityType, entityName, dialog=None, frameRange=None):
        if entityType == "asset":
            result = self.createAsset(entityName, dialog=dialog)
        elif entityType == "assetFolder":
            result = self.createAssetFolder(entityName, dialog=dialog)
        elif entityType == "shot":
            result = self.createShot(entityName, frameRange=frameRange)
        else:
            return {}

        if result.get("existed"):
            eName = self.getAssetRelPathFromPath(entityName)
            if eName in self.omittedEntities[entityType] and self.core.uiAvailable:
                msgText = (
                    "The %s %s already exists, but is marked as omitted.\n\nDo you want to restore it?"
                    % (entityType, eName)
                )
                resultq = self.core.popupQuestion(msgText)

                if resultq == "Yes":
                    self.omitEntity(entityType, eName, omit=False)
            else:
                self.core.popup("The %s already exists:\n\n%s" % (entityType, eName))

        if result.get("error"):
            self.core.popup(result["error"])

        return result

    @err_catcher(name=__name__)
    def createAssetFolder(self, folderPath, dialog=None):
        if not os.path.isabs(folderPath):
            folderPath = os.path.join(self.core.assetPath, folderPath)

        existed = os.path.exists(folderPath)
        if not os.path.exists(folderPath):
            os.makedirs(folderPath)

        relpath = self.getAssetRelPathFromPath(folderPath)

        if not existed:
            self.core.callback(
                name="onAssetFolderCreated",
                args=[self, relpath, folderPath, dialog],
            )

        result = {
            "entity": "assetfolder",
            "entityName": relpath,
            "entityPath": folderPath,
            "existed": existed,
        }
        logger.debug("assetFolder created: %s" % result)
        return result

    @err_catcher(name=__name__)
    def createAsset(self, assetPath, dialog=None):
        if not os.path.isabs(assetPath):
            assetPath = os.path.join(self.core.assetPath, assetPath)

        assetName = self.getAssetNameFromPath(assetPath)
        if not self.isValidAssetName(assetName):
            return {"error": "Invalid assetname"}

        existed = os.path.exists(assetPath)

        for f in self.entityFolders["asset"]:
            aFolder = os.path.join(assetPath, f)
            if not os.path.exists(aFolder):
                os.makedirs(aFolder)

        if not existed:
            self.core.callback(
                name="onAssetCreated",
                types=["custom"],
                args=[self, assetName, assetPath, dialog],
            )
            for i in self.core.prjManagers.values():
                i.assetCreated(self, dialog, assetPath)

        result = {
            "entity": "asset",
            "entityName": assetName,
            "entityPath": assetPath,
            "existed": existed,
        }
        logger.debug("asset created: %s" % result)
        return result

    @err_catcher(name=__name__)
    def createShot(self, shotName, frameRange=None):
        sBase = self.core.getEntityPath(shot=shotName)

        existed = os.path.exists(sBase)

        for f in self.entityFolders["shot"]:
            sFolder = os.path.join(sBase, f)
            if not os.path.exists(sFolder):
                try:
                    os.makedirs(sFolder)
                except Exception as e:
                    if e.errno == 13:
                        self.core.popup("Missing permissions to create folder:\n\n%s" % sFolder)
                        return {}
                    else:
                        raise

        if frameRange:
            self.core.setConfig("shotRanges", shotName, frameRange, config="shotinfo")

        if not existed:
            shotName, seqName = self.core.entities.splitShotname(shotName)

            self.core.callback(
                name="onShotCreated", types=["custom"], args=[self, seqName, shotName]
            )

        result = {
            "entity": "shot",
            "entityName": shotName,
            "entityPath": sBase,
            "existed": existed,
        }
        logger.debug("shot created: %s" % result)
        return result

    @err_catcher(name=__name__)
    def createStep(
        self, stepName, entity="shot", entityName="", stepPath="", createCat=True
    ):
        if not stepPath:
            if entity == "asset":
                entityName = self.getAssetPathFromAssetName(entityName)
                if not entityName:
                    msg = "Asset '%s' doesn't exist. Could not create step." % entityName
                    self.core.popup(msg)
                    return

                stepPath = self.core.getEntityPath(asset=entityName, step=stepName)

            elif entity == "shot":
                stepPath = self.core.getEntityPath(shot=entityName, step=stepName)

        if not os.path.exists(stepPath):
            existed = False
            try:
                os.makedirs(stepPath)
            except:
                self.core.popup("The directory %s could not be created" % stepName)
                return False
        else:
            existed = True
            logger.debug("step already exists: %s" % stepPath)

        settings = {
            "createDefaultCategory": (
                entity == "shot"
                or self.core.compareVersions(self.core.projectVersion, "v1.2.1.6")
                != "lower"
            )
            and createCat
        }

        self.core.callback(
            name="onStepCreated",
            types=["custom"],
            args=[self, entity, stepName, stepPath, settings],
        )

        if not existed:
            logger.debug("step created %s" % stepPath)

        if settings["createDefaultCategory"]:
            paths = self.createDefaultCat(entity, entityName, stepName)
            return paths

        return stepPath

    @err_catcher(name=__name__)
    def createDefaultCat(self, entity, entityName, step):
        existingSteps = self.core.getConfig(
                            "globals", "pipeline_steps", configPath=self.core.prismIni
                        )
        if step not in existingSteps:
            msgStr = "Step '%s' doesn't exist in the project config. Couldn't create default category." % step
            self.core.popup(msgStr)
            return

        categories = existingSteps[step]
        if not isinstance(categories, list):
            categories = [categories]

        paths = []
        for category in categories:
            paths.append(self.createCategory(entity, entityName, step, category))

        return paths

    @err_catcher(name=__name__)
    def createCategory(self, entity, entityName, step, category):
        if entity == "asset":
            catPath = self.core.getEntityPath(asset=entityName, step=step, category=category)
        elif entity == "shot":
            catPath = self.core.getEntityPath(shot=entityName, step=step, category=category)

        if not os.path.exists(catPath):
            try:
                os.makedirs(catPath)
            except:
                self.core.popup("The directory %s could not be created" % catPath)
                return
            else:
                self.core.callback(
                    name="onCategoryCreated",
                    types=["custom"],
                    args=[self, category, catPath],
                )

            logger.debug("category created %s" % catPath)
        else:
            logger.debug("category already exists: %s" % catPath)

        return catPath

    @err_catcher(name=__name__)
    def omitEntity(self, entityType, entityName, omit=True):
        if entityType == "assetFolder":
            entityType = "asset"

        if omit:
            omits = self.core.getConfig(entityType, config="omit") or []

            if entityName not in omits:
                omits.append(entityName)

            self.core.setConfig(entityType, val=omits, config="omit")
            logger.debug("omitted %s %s" % (entityType, entityName))
        else:
            self.core.setConfig(entityType, entityName, config="omit", delete=True)
            logger.debug("restored %s %s" % (entityType, entityName))

        self.refreshOmittedEntities()

    @err_catcher(name=__name__)
    def setComment(self, filepath, comment):
        newPath = ""
        data = self.core.getScenefileData(filepath)

        if self.core.useLocalFiles:
            localPath = filepath.replace(self.core.projectPath, self.core.localProjectPath)
            if os.path.exists(localPath):
                localData = self.core.getScenefileData(localPath)
                del localData["filename"]
                del localData["fullEntityName"]
                localData["comment"] = comment
                newPath = self.core.generateScenePath(**localData)
                self.core.copySceneFile(localPath, newPath, mode="move")

        if os.path.exists(filepath):
            data["comment"] = comment
            del data["filename"]
            del data["fullEntityName"]
            newPath = self.core.generateScenePath(**data)
            self.core.copySceneFile(filepath, newPath, mode="move")

        return newPath

    @err_catcher(name=__name__)
    def deleteShot(self, shotName):
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
                msg = QMessageBox(
                    QMessageBox.Warning,
                    "Warning",
                    'Permission denied.\nAnother programm uses files in the shotfolder.\n\nThe shot "%s" could not be deleted completly.\n\n%s'
                    % (shotName, str(e)),
                    QMessageBox.Cancel,
                )
                msg.addButton("Retry", QMessageBox.YesRole)
                self.core.parentWindow(msg)
                action = msg.exec_()

                if action != 0:
                    self.core.popup("Deleting shot canceled.")
                    break

    @err_catcher(name=__name__)
    def renameShot(self, curShotName, newShotName):
        shotFolder = self.core.getEntityPath(shot=curShotName)
        newShotFolder = self.core.getEntityPath(shot=newShotName)
        shotFolders = {shotFolder: newShotFolder}
        if self.core.useLocalFiles:
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
                            if curShotName in k:
                                os.rename(k, k.replace(curShotName, newShotName))
                        for k in i[2]:
                            if curShotName in k:
                                os.rename(k, k.replace(curShotName, newShotName))
                    os.chdir(cwd)

                prvPath = os.path.join(
                    os.path.dirname(self.core.prismIni),
                    "Shotinfo",
                    "%s_preview.jpg" % curShotName,
                )
                if os.path.exists(prvPath):
                    os.chdir(os.path.dirname(prvPath))
                    os.rename(curShotName + "_preview.jpg", newShotName + "_preview.jpg")

                break

            except Exception as e:
                msg = QMessageBox(
                    QMessageBox.Warning,
                    "Warning",
                    'Permission denied.\nAnother programm uses files in the shotfolder.\n\nThe shot "%s" could not be renamed to "%s" completly.\n\n%s'
                    % (curShotName, newShotName, str(e)),
                    QMessageBox.Cancel,
                )
                msg.addButton("Retry", QMessageBox.YesRole)
                self.core.parentWindow(msg)
                action = msg.exec_()

                if action != 0:
                    self.core.popup("Renaming shot canceled.")
                    return

        curRange = self.core.getConfig("shotRanges", curShotName, config="shotinfo")
        if curRange:
            self.core.setConfig("shotRanges", newShotName, curRange, config="shotinfo")
        self.core.setConfig("shotRanges", curShotName, delete=True, config="shotinfo")

    @err_catcher(name=__name__)
    def getTypeFromPath(self, path):
        if not os.path.exists(path):
            return

        dirContent = os.listdir(path)

        if self.core.getConfig("globals", "useStrictAssetDetection", dft=False, config="project"):
            isAsset = (
                "Export" in dirContent
                and "Playblasts" in dirContent
                and "Rendering" in dirContent
                and "Scenefiles" in dirContent
            )
        else:
            isAsset = (
                "Export" in dirContent
                or "Playblasts" in dirContent
                or "Rendering" in dirContent
                or "Scenefiles" in dirContent
            )

        if isAsset:
            return "asset"
        else:
            return "folder"

    @err_catcher(name=__name__)
    def getAssetPaths(self, path=None, returnFolders=False, depth=0):
        aBasePath = path or self.core.getAssetPath()
        assets = []
        assetFolders = []

        for root, folders, files in os.walk(aBasePath):
            for folder in folders:
                folderPath = os.path.join(root, folder)
                if self.getTypeFromPath(folderPath) == "asset":
                    assets.append(folderPath)
                else:
                    if depth == 1:
                        assetFolders.append(folderPath)
                    else:
                        nextDepth = 0 if depth == 0 else (depth-1)
                        childAssets, childFolders = self.getAssetPaths(path=folderPath, returnFolders=True, depth=nextDepth)
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
    def getEmptyAssetFolders(self):
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
    def getAssetPathFromAssetName(self, assetName):
        if os.path.isabs(assetName):
            assetPath = assetName
        else:
            assetPaths = self.getAssetPaths()
            path = os.path.join(self.core.assetPath, assetName)
            if path in assetPaths:
                assetPath = path
            else:
                for i in assetPaths:
                    if os.path.basename(i) == assetName:
                        assetPath = i
                        break
                else:
                    return

        return assetPath

    @err_catcher(name=__name__)
    def getAssetFoldersFromPath(self, path, pathType="asset"):
        relPath = self.getAssetRelPathFromPath(path)
        folders = os.path.normpath(relPath).split(os.sep)
        if pathType == "asset":
            folders = folders[:-1]
        return folders

    @err_catcher(name=__name__)
    def filterAssets(self, assets, filterStr):
        filteredPaths = []
        for absAssetPath in assets:
            assetPath = absAssetPath.replace(self.core.assetPath, "")
            if self.core.useLocalFiles:
                localAssetPath = self.core.getAssetPath(location="local")
                assetPath = assetPath.replace(localAssetPath, "")
            assetPath = assetPath[1:]

            if filterStr.lower() in assetPath.lower():
                filteredPaths.append(absAssetPath)
        return filteredPaths

    @err_catcher(name=__name__)
    def filterOmittedAssets(self, assets):
        filteredPaths = []
        for absAssetPath in assets:
            assetName = self.getAssetRelPathFromPath(absAssetPath)
            if assetName not in self.omittedEntities["asset"]:
                filteredPaths.append(absAssetPath)

        return filteredPaths

    @err_catcher(name=__name__)
    def getExportProductNamesFromAsset(self, assetPath):
        productPath = self.core.products.getProductPathFromEntityPath(assetPath)
        pnames = []
        for root, folders, files in os.walk(productPath):
            pnames += folders
            break

        return pnames

    @err_catcher(name=__name__)
    def isAssetPathOmitted(self, assetPath):
        isOmitted = not bool(self.filterOmittedAssets([assetPath]))
        return isOmitted

    @err_catcher(name=__name__)
    def isValidAssetName(self, assetName):
        if self.core.getConfig("globals", "useStrictAssetDetection"):
            return True
        else:
            return assetName not in ["Export", "Playblasts", "Rendering", "Scenefiles"]

    @err_catcher(name=__name__)
    def getAssetNameFromPath(self, path):
        return os.path.basename(path)

    @err_catcher(name=__name__)
    def getAssetRelPathFromPath(self, path):
        path = self.core.convertPath(path, "global")
        return path.replace(self.core.assetPath, "").strip("\\").strip("/")

    @err_catcher(name=__name__)
    def getScenefileData(self, fileName):
        fname = os.path.basename(fileName).split(self.core.filenameSeparator)
        data = {}
        try:
            data["basePath"] = os.path.dirname(fileName)
        except:
            pass

        data["filename"] = fileName

        if len(fname) == 6:
            basepath = self.core.paths.getEntityBasePath(fileName)
            relpath = self.getAssetRelPathFromPath(basepath)
            data.update({
                "entity": "asset",
                "entityName": fname[0],
                "fullEntityName": relpath,
                "step": fname[1],
                "category": "",
                "version": fname[2],
                "comment": fname[3],
                "user": fname[4],
                "extension": fname[5],
            })

        elif len(fname) == 7:
            basepath = self.core.paths.getEntityBasePath(fileName)
            relpath = self.getAssetRelPathFromPath(basepath)
            data.update({
                "entity": "asset",
                "entityName": fname[0],
                "fullEntityName": relpath,
                "step": fname[1],
                "category": fname[2],
                "version": fname[3],
                "comment": fname[4],
                "user": fname[5],
                "extension": fname[6],
            })

        elif len(fname) == 8:
            data.update({
                "entity": "shot",
                "entityName": fname[1],
                "fullEntityName": fname[1],
                "step": fname[2],
                "category": fname[3],
                "version": fname[4],
                "comment": fname[5],
                "user": fname[6],
                "extension": fname[7],
            })

        else:
            data.update({"entity": "invalid"})

        return data

    @err_catcher(name=__name__)
    def getHighestVersion(
        self,
        dstname,
        scenetype=None,
        getExistingPath=False,
        fileTypes="*",
        localVersions=True,
        getExistingVersion=False,
    ):
        if not scenetype:
            glbDstname = dstname
            assetPath = self.core.getAssetPath()
            shotPath = self.core.getShotPath()

            if self.core.useLocalFiles:
                glbDstname = self.core.convertPath(dstname, "global")

            if glbDstname.startswith(assetPath):
                scenetype = "asset"
            elif glbDstname.startswith(shotPath):
                scenetype = "shot"
            else:
                return

        files = []
        if self.core.useLocalFiles and localVersions:
            dstname = self.core.convertPath(dstname, "global")

        for i in os.walk(dstname):
            files += [os.path.join(i[0], x) for x in i[2]]
            break

        if self.core.useLocalFiles and localVersions:
            for i in os.walk(self.core.convertPath(dstname, "local")):
                files += [os.path.join(i[0], x) for x in i[2]]
                break

        highversion = [0, ""]
        for i in files:
            if fileTypes != "*" and os.path.splitext(i)[1] not in fileTypes:
                continue

            fname = self.core.getScenefileData(i)

            if fname["entity"] != scenetype.lower():
                continue

            try:
                version = int(fname["version"][-self.core.versionPadding:])
            except:
                continue

            if version > highversion[0]:
                highversion = [version, i]

        if getExistingVersion:
            return highversion
        elif getExistingPath:
            return highversion[1]
        else:
            return self.core.versionFormat % (highversion[0] + 1)

    @err_catcher(name=__name__)
    def getHighestTaskVersion(self, dstname, getExisting=False, ignoreEmpty=False):
        taskDirs = []
        dstname = os.path.normpath(dstname)
        if os.path.normpath("Rendering/3dRender") in dstname or os.path.normpath("Rendering/2dRender") in dstname:
            outPaths = self.core.paths.getRenderProductBasePaths().values()
        else:
            outPaths = self.core.paths.getExportProductBasePaths().values()

        for path in outPaths:
            dstname = dstname.replace(path, self.core.projectPath)

        for path in outPaths:
            opath = dstname.replace(self.core.projectPath, path)
            for i in os.walk(opath):
                if ignoreEmpty:
                    for k in i[1]:
                        exFiles = os.listdir(os.path.join(i[0], k))
                        if len(exFiles) > 1 or (
                            len(exFiles) == 1 and not exFiles[0].startswith("versioninfo")
                        ):
                            taskDirs.append(k)
                else:
                    taskDirs += i[1]
                break

        highversion = 0
        for i in taskDirs:
            fname = i.split(self.core.filenameSeparator)

            if len(fname) in [1, 2, 3]:
                try:
                    version = int(fname[0][1:(1+self.core.versionPadding)])
                except:
                    continue

                if version > highversion:
                    highversion = version

        if not getExisting and not self.core.separateOutputVersionStack:
            fileName = self.core.getCurrentFileName()
            fnameData = self.core.getScenefileData(fileName)
            if fnameData["entity"] != "invalid":
                hVersion = fnameData["version"]
            else:
                hVersion = self.core.versionFormat % 1

            return hVersion

        if getExisting and highversion != 0:
            return self.core.versionFormat % (highversion)
        else:
            return self.core.versionFormat % (highversion + 1)

    @err_catcher(name=__name__)
    def getLatestCompositingVersion(self, curPath):
        curFile = os.path.basename(curPath)
        passName = os.path.basename(os.path.dirname(curPath))

        verNum = passName[1:5]
        if sys.version[0] == "2":
            verNum = unicode(verNum)

        if passName.startswith("v") and verNum.isnumeric():
            curVersion = passName[:5]
            passName = ""
            taskPath = os.path.dirname(os.path.dirname(curPath))
        else:
            curVersion = os.path.basename(os.path.dirname(os.path.dirname(curPath)))[:5]
            taskPath = os.path.dirname(os.path.dirname(os.path.dirname(curPath)))

        latestVersion = self.core.getHighestTaskVersion(
            taskPath, getExisting=True, ignoreEmpty=True
        )

        newPath = ""
        for k in os.listdir(taskPath):
            if k.startswith(latestVersion):
                newPath = os.path.join(taskPath, k, passName)
                break

        newPath = os.path.join(
            newPath, curFile.replace(curVersion, latestVersion)
        ).replace("\\", "/")

        return newPath

    @err_catcher(name=__name__)
    def getTaskNames(self, taskType, basePath=""):
        taskList = []

        if basePath is None:
            basePath = ""

        if basePath == "":
            fname = self.core.getCurrentFileName()
            assetPath = self.core.paths.getEntityBasePath(fname)
            shotPath = self.core.getShotPath()

            if self.core.useLocalFiles:
                assetPath = assetPath.replace(self.core.localProjectPath, self.core.projectPath)
                lassetPath = assetPath.replace(self.core.projectPath, self.core.localProjectPath)
                lshotPath = shotPath.replace(self.core.projectPath, self.core.localProjectPath)

            fnameData = self.core.getScenefileData(fname)

            if fnameData["entity"] == "asset" and (
                assetPath in fname or (self.core.useLocalFiles and lassetPath in fname)
            ):
                basePath = assetPath

            elif fnameData["entity"] == "shot" and (
                shotPath in fname or (self.core.useLocalFiles and lshotPath in fname)
            ):
                basePath = os.path.join(shotPath, fnameData["entityName"])
            else:
                return taskList

            catPath = os.path.join(basePath, "Scenefiles", fnameData["step"])

        if self.core.useLocalFiles:
            lbasePath = basePath.replace(self.core.projectPath, self.core.localProjectPath)

        taskPath = ""

        if basePath != "":
            if taskType == "export":
                taskPath = os.path.join(basePath, "Export")
                if "lbasePath" in locals():
                    ltaskPath = os.path.join(lbasePath, "Export")
            elif taskType == "render":
                taskPath = os.path.join(basePath, "Rendering", "3dRender")
                if "lbasePath" in locals():
                    ltaskPath = os.path.join(lbasePath, "Rendering", "3dRender")
            elif taskType == "2d":
                taskPath = os.path.join(basePath, "Rendering", "2dRender")
                if "lbasePath" in locals():
                    ltaskPath = os.path.join(lbasePath, "Rendering", "2dRender")
            elif taskType == "playblast":
                taskPath = os.path.join(basePath, "Playblasts")
                if "lbasePath" in locals():
                    ltaskPath = os.path.join(lbasePath, "Playblasts")
            elif taskType == "external":
                taskPath = os.path.join(basePath, "Rendering", "external")
                if "lbasePath" in locals():
                    ltaskPath = os.path.join(lbasePath, "Rendering", "external")

        taskList = []
        if os.path.exists(taskPath):
            taskList = [
                x
                for x in os.listdir(taskPath)
                if os.path.isdir(os.path.join(taskPath, x))
            ]

        if self.core.useLocalFiles and "ltaskPath" in locals() and os.path.exists(ltaskPath):
            taskList += [
                x
                for x in os.listdir(ltaskPath)
                if x not in taskList and os.path.isdir(os.path.join(ltaskPath, x))
            ]

        if "catPath" in locals() and os.path.exists(catPath):
            taskList += [
                x
                for x in os.listdir(catPath)
                if x not in taskList and os.path.isdir(os.path.join(catPath, x))
            ]

        return taskList

    @err_catcher(name=__name__)
    def getEntityPreviewPath(self, entityType, entityName):
        if entityType == "asset":
            folderName = "Assetinfo"
        elif entityType in ["shot", "sequence"]:
            folderName = "Shotinfo"

        if entityType == "sequence":
            imgName = "seq_%s_preview.jpg" % entityName
        else:
            imgName = "%s_preview.jpg" % entityName

        imgPath = os.path.join(os.path.dirname(self.core.prismIni), folderName, imgName)
        return imgPath

    @err_catcher(name=__name__)
    def setEntityPreview(self, entityType, entityName, pixmap, width=250, height=141):
        if not pixmap:
            logger.debug("invalid pixmap")
            return

        if (pixmap.width() / float(pixmap.height())) > 1.7778:
            pmsmall = pixmap.scaledToWidth(width)
        else:
            pmsmall = pixmap.scaledToHeight(height)

        prvPath = self.getEntityPreviewPath(entityType, entityName)
        self.core.media.savePixmap(pmsmall, prvPath)

    @err_catcher(name=__name__)
    def getPresetScenes(self):
        presetScenes = []
        emptyDir = os.path.join(os.path.dirname(self.core.prismIni), "EmptyScenes")
        if os.path.exists(emptyDir):
            for filename in sorted(os.listdir(emptyDir)):
                if filename == "readme.txt":
                    continue

                presetScenes.append(filename)

        return presetScenes

    @err_catcher(name=__name__)
    def createEmptyScene(
        self,
        entity,
        fileName,
        entityName=None,
        assetPath=None,
        step=None,
        category=None,
        comment=None,
        version=None,
        location="local",
    ):
        ext = os.path.splitext(fileName)[1]
        comment = comment or ""

        if entity == "asset":
            entityPath = ""
            if assetPath:
                entityPath = os.path.join(self.core.getAssetPath(), assetPath)
            else:
                self.core.popup("Invalid asset:\n\n%s" % (entityPath or entityName))
                return

            filePath = self.core.generateScenePath(
                "asset",
                entityName,
                step,
                assetPath=assetPath,
                category=category,
                extension=ext,
                comment=comment,
                version=version,
            )
        elif entity == "shot":
            filePath = self.core.generateScenePath(
                "shot",
                entityName,
                step,
                category=category,
                extension=ext,
                comment=comment,
                version=version,
            )
        else:
            self.core.popup("Invalid entity:\n\n%s" % entity)
            return

        if os.path.isabs(fileName):
            scene = fileName
        else:
            scene = os.path.join(
                os.path.dirname(self.core.prismIni), "EmptyScenes", fileName
            )

        if location == "local" and self.core.useLocalFiles:
            filePath = self.core.convertPath(filePath, "local")

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
        self.core.saveSceneInfo(filePath)

        self.core.callback(
            name="onEmptySceneCreated",
            types=["custom"],
            args=[self, filePath],
        )

        logger.debug("Created empty scene: %s" % filePath)
        return filePath

    @err_catcher(name=__name__)
    def createPresetScene(self):
        emptyDir = os.path.join(os.path.dirname(self.core.prismIni), "EmptyScenes")

        newItem = CreateItem.CreateItem(
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

        filepath = os.path.join(emptyDir, pName)
        filepath = filepath.replace("\\", "/")
        filepath += self.core.appPlugin.getSceneExtension(self)

        self.core.saveScene(filepath=filepath, prismReq=False)
        return filepath
