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
from collections import OrderedDict

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


class PathManager(object):
    def __init__(self, core):
        super(PathManager, self).__init__()
        self.core = core
        self.masterManager = MasterManager

    @err_catcher(name=__name__)
    def getCompositingOut(
        self,
        taskName,
        fileType,
        useVersion,
        render,
        location="global",
        comment="",
        ignoreEmpty=True,
        node=None,
    ):
        fileName = self.core.getCurrentFileName()
        if self.core.fileInPipeline(filepath=fileName):
            fnameData = self.core.getScenefileData(fileName)
            if taskName is None:
                taskName = ""

            if not self.core.separateOutputVersionStack:
                version = fnameData.get("version")
            else:
                version = useVersion

            extension = "." + fileType
            framePadding = "#" * self.core.framePadding if extension not in self.core.media.videoFormats else ""
            outputData = self.core.mediaProducts.generateMediaProductPath(
                entity=fnameData,
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
                outputPath = "FileNotInPipeline"
        else:
            outputPath = "FileNotInPipeline"

        if render and outputPath != "FileNotInPipeline":
            if not os.path.exists(os.path.dirname(outputPath)):
                try:
                    os.makedirs(os.path.dirname(outputPath))
                except:
                    self.core.popup("Could not create output folder")

            details = outputData.copy()
            details["sourceScene"] = self.core.getCurrentFileName()
            filepath = os.path.dirname(outputPath)
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
    def getMediaConversionOutputPath(self, context, inputpath, extension, addFramePadding=True):
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

        context["version"] = context["version"] + " (%s)" % extension[1:]
        context["extension"] = extension
        if extension in videoFormats or not addFramePadding:
            context["frame"] = ""
        else:
            context["frame"] = "%%0%sd" % self.core.framePadding
        outputPath = self.core.projects.getResolvedProjectStructurePath(
            key, context=context
        )
        return outputPath

    @err_catcher(name=__name__)
    def getEntityPath(
        self, entity=None, step=None, category=None, reqEntity=None, location="global"
    ):
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
        entity,
        department,
        task="",
        extension="",
        version="",
        comment="",
        user="",
        location=None,
    ):
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
            scenePath = self.core.projects.getResolvedProjectStructurePath(
                "assetScenefiles", context=context
            )

        elif entity["type"] == "shot":
            context["sequence"] = entity["sequence"]
            context["shot"] = entity["shot"]
            scenePath = self.core.projects.getResolvedProjectStructurePath(
                "shotScenefiles", context=context
            )

        else:
            return ""

        scenePath = self.core.convertPath(scenePath, location)
        return scenePath

    @err_catcher(name=__name__)
    def getCachePathData(self, cachePath, addPathData=True, validateModTime=False):
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

        cacheData = self.core.getConfig(configPath=cacheConfig) or {}
        cacheData = cacheData.copy()
        if addPathData:
            if os.path.splitext(cachePath)[1]:
                pathData = self.core.products.getProductDataFromFilepath(cachePath)
            else:
                pathData = self.core.products.getProductDataFromVersionFolder(cachePath)

            cacheData.update(pathData)

        if "_" in cacheData.get("version", "") and len(cacheData["version"].split("_")) == 2:
            cacheData["version"], cacheData["wedge"] = cacheData["version"].split("_")

        return cacheData

    @err_catcher(name=__name__)
    def getMediaProductData(self, productPath, isFilepath=True, addPathData=True, mediaType="3drenders", validateModTime=False):
        if mediaType == "playblasts":
            return self.getPlayblastProductData(productPath, isFilepath=isFilepath, addPathData=addPathData, validateModTime=validateModTime)
        else:
            return self.getRenderProductData(productPath, isFilepath=isFilepath, addPathData=addPathData, mediaType=mediaType, validateModTime=validateModTime)

    @err_catcher(name=__name__)
    def getRenderProductData(self, productPath, isFilepath=True, addPathData=True, mediaType="3drenders", validateModTime=False):
        productPath = os.path.normpath(productPath)
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

        productData = self.core.getConfig(configPath=productConfig) or {}
        if addPathData:
            pathData = self.core.mediaProducts.getRenderProductDataFromFilepath(productPath, mediaType=mediaType)
            productData.update(pathData)

        productData["locations"] = []
        loc = self.core.paths.getLocationFromPath(os.path.normpath(productPath))
        if len(self.core.paths.getRenderProductBasePaths()) > 1:
            globalPath = self.core.convertPath(os.path.normpath(productPath), "global")
            if os.path.exists(os.path.normpath(globalPath)):
                productData["locations"].append("global")

        if self.core.useLocalFiles:
            localPath = self.core.convertPath(os.path.normpath(productPath), "local")
            if os.path.exists(localPath):
                productData["locations"].append("local")

        if loc not in ["global", "local"]:
            productData["locations"].append(loc)

        productData["path"] = productPath
        return productData

    @err_catcher(name=__name__)
    def getPlayblastProductData(self, productPath, isFilepath=True, addPathData=True, validateModTime=False):
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
            pathData = self.core.mediaProducts.getRenderProductDataFromFilepath(productPath)
            productData.update(pathData)

        return productData

    @err_catcher(name=__name__)
    def requestPath(self, title="Select folder", startPath="", parent=None):
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
        title="Select File",
        startPath="",
        parent=None,
        fileFilter="All files (*.*)",
        saveDialog=True
    ):
        path = ""
        parent = parent or self.core.messageParent
        if self.core.uiAvailable:
            if saveDialog:
                path = QFileDialog.getSaveFileName(parent, title, startPath, fileFilter)[0]
            else:
                path = QFileDialog.getOpenFileName(parent, title, startPath, fileFilter)[0]

        return path

    @err_catcher(name=__name__)
    def convertExportPath(self, path, fromLocation, toLocation):
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
    def addExportProductBasePath(self, location, path, configData=None):
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
    def addRenderProductBasePath(self, location, path, configData=None):
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
    def removeExportProductBasePath(self, location, configData=None):
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
    def removeRenderProductBasePath(self, location, configData=None):
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
    def getExportProductBasePaths(self, default=True, configPath=None, configData=None):
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
    def getRenderProductBasePaths(self, default=True, configPath=None, configData=None):
        render_paths = OrderedDict([])
        if not self.core.projects.hasActiveProject():
            return render_paths

        if default:
            render_paths["global"] = self.core.projectPath

            if self.core.useLocalFiles:
                render_paths["local"] = self.core.localProjectPath

        if configData:
            customPaths = configData.get("render_paths", [])
        else:
            if not configPath:
                configPath = self.core.prismIni

            customPaths = self.core.getConfig(
                "render_paths", configPath=configPath, dft=[]
            )

        for cp in customPaths:
            render_paths[cp] = customPaths[cp]

        for path in render_paths:
            render_paths[path] = os.path.normpath(render_paths[path])

        return render_paths

    @err_catcher(name=__name__)
    def convertGlobalRenderPath(self, path, target="global"):
        path = os.path.normpath(path)
        basepaths = self.getRenderProductBasePaths()
        prjPath = os.path.normpath(self.core.projectPath)
        convertedPath = os.path.normpath(path).replace(prjPath, basepaths[target])
        return convertedPath

    @err_catcher(name=__name__)
    def replaceVersionInStr(self, inputStr, replacement):
        versions = re.findall("v[0-9]{%s}" % self.core.versionPadding, inputStr)
        replacedStr = inputStr
        for version in versions:
            replacedStr = replacedStr.replace(version, replacement)

        return replacedStr

    @err_catcher(name=__name__)
    def getFrameFromFilename(self, filename):
        filename = os.path.basename(filename)
        base, ext = os.path.splitext(filename)
        match = re.search("[0-9]{%s}$" % self.core.framePadding, base)
        if not match:
            return

        frame = match.group(0)
        return frame

    @err_catcher(name=__name__)
    def getLocationFromPath(self, path):
        if path.startswith(getattr(self.core, "projectPath", "")):
            return "global"
        elif self.core.useLocalFiles and path.startswith(self.core.localProjectPath):
            return "local"
        else:
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
    def getLocationPath(self, locationName):
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
    def splitext(self, path):
        if path.endswith(".bgeo.sc"):
            return [path[: -len(".bgeo.sc")], ".bgeo.sc"]
        else:
            return os.path.splitext(path)

    @err_catcher(name=__name__)
    def getEntityTypeFromPath(self, path):
        globalPath = self.core.convertPath(path, "global")
        globalPath = os.path.normpath(globalPath)
        globalPath = os.path.splitdrive(globalPath)[1]
        assetPath = os.path.splitdrive(self.core.assetPath)[1]
        sequencePath = os.path.splitdrive(self.core.sequencePath)[1]
        if globalPath.startswith(assetPath):
            return "asset"
        elif globalPath.startswith(sequencePath):
            return "shot"


class MasterManager(QDialog):
    def __init__(self, core, entities, mode, parent=None):
        super(MasterManager, self).__init__()
        self.core = core
        self.core.parentWindow(self, parent=parent)
        self.mode = mode
        self.entities = entities
        self.outdatedVersions = []
        self.setupUi()

    @err_catcher(name=__name__)
    def showEvent(self, event):
        self.refreshTable()

    @err_catcher(name=__name__)
    def sizeHint(self):
        return QSize(700, 500)

    @err_catcher(name=__name__)
    def setupUi(self):
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
    def refreshTable(self):
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
    def onItemDoubleClicked(self, item):
        data = self.tw_versions.item(item.row(), 0).data(Qt.UserRole)
        self.openInProjectBrowser(data["latest"]["path"])

    @err_catcher(name=__name__)
    def showContextMenu(self, pos):
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
    def updateSelected(self):
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
    def openInProjectBrowser(self, path):
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
    def refreshData(self):
        text = "Getting version data. Please wait..."
        with self.core.waitPopup(self.core, text):
            if self.mode == "products":
                result = self.core.products.getOutdatedMasterVersions(self.entities)
            else:
                result = self.core.mediaProducts.getOutdatedMasterVersions(self.entities)
    
        self.outdatedVersions = result

    @err_catcher(name=__name__)
    def onUpdateMasterClicked(self, versionData):
        text = "Updating version. Please wait..."
        with self.core.waitPopup(self.core, text):
            self.updateMaster(versionData)

    @err_catcher(name=__name__)
    def updateMaster(self, versionData):
        if self.mode == "products":
            filepath = self.core.products.getPreferredFileFromVersion(versionData["latest"])
            self.core.products.updateMasterVersion(filepath)
        else:
            self.core.mediaProducts.updateMasterVersion(context=versionData["latest"])

    @err_catcher(name=__name__)
    def refreshProjectBrowserVersions(self):
        if self.core.pb:
            if self.mode == "products":
                self.core.pb.productBrowser.updateVersions(restoreSelection=True)
            else:
                self.core.pb.mediaBrowser.updateVersions(restoreSelection=True)

    @err_catcher(name=__name__)
    def onAcceptClicked(self):
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
