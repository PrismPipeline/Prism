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


import hou
import os, sys
import traceback, time, platform, glob
from functools import wraps

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1


class Prism_Houdini_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            exc_info = sys.exc_info()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = (
                    "%s ERROR - Prism_Plugin_Houdini - Core: %s - Plugin: %s:\n%s\n\n%s"
                    % (
                        time.strftime("%d/%m/%y %X"),
                        args[0].core.version,
                        args[0].plugin.version,
                        "".join(traceback.format_stack()),
                        traceback.format_exc(),
                    )
                )
                args[0].core.writeErrorLog(erStr)

        return func_wrapper

    @err_decorator
    def startup(self, origin):
        if self.core.uiAvailable:
            if not hou.isUIAvailable():
                return False

            if hou.ui.mainQtWindow() is None:
                return False

            if platform.system() == "Darwin":
                origin.messageParent = QWidget()
                origin.messageParent.setParent(hou.ui.mainQtWindow(), Qt.Window)
                if self.core.useOnTop:
                    origin.messageParent.setWindowFlags(
                        origin.messageParent.windowFlags() ^ Qt.WindowStaysOnTopHint
                    )
            else:
                origin.messageParent = hou.ui.mainQtWindow()

            origin.startasThread()
            origin.timer.stop()
        else:
            QApplication.addLibraryPath(
                os.path.join(hou.expandString("$HFS"), "bin", "Qt_plugins")
            )
            qApp = QApplication.instance()
            if qApp is None:
                qApp = QApplication(sys.argv)
            origin.messageParent = QWidget()

    @err_decorator
    def autosaveEnabled(self, origin):
        return hou.hscript("autosave")[0] == "autosave on\n"

    @err_decorator
    def onProjectChanged(self, origin):
        self.loadPrjHDAs(origin)
        job = self.core.projectPath.replace("\\", "/")
        if job.endswith("/"):
            job = job[:-1]
        hou.hscript("set PRISMJOB=" + job)

        if self.core.useLocalFiles:
            ljob = self.core.localProjectPath.replace("\\", "/")
            if ljob.endswith("/"):
                ljob = ljob[:-1]
            hou.hscript("set PRISMJOBLOCAL=" + ljob)

    @err_decorator
    def sceneOpen(self, origin):
        origin.sceneUnload()

    @err_decorator
    def loadPrjHDAs(self, origin):
        if not hasattr(origin, "projectPath") or not os.path.exists(origin.projectPath):
            return

        if not origin.validateUser():
            origin.changeUser()

        for i in origin.prjHDAs:
            if not os.path.exists(i):
                continue

            defs = hou.hda.definitionsInFile(i)
            if len(defs) > 0 and defs[0].isInstalled():
                hou.hda.uninstallFile(i)

        hdaFolders = [os.path.join(origin.projectPath, "00_Pipeline", "HDAs")]

        prjHDAs = os.path.join(
            origin.projectPath,
            origin.getConfig("paths", "assets", configPath=origin.prismIni),
            "HDAs",
        )
        if hasattr(self.core, "user"):
            hdaUFolder = os.path.join(prjHDAs, origin.user)
            hdaFolders += [prjHDAs, hdaUFolder]

        origin.prjHDAs = []

        for k in hdaFolders:
            if os.path.exists(k):
                for i in os.walk(k):
                    if os.path.basename(i[0]) == "backup":
                        continue

                    for m in i[2]:
                        if os.path.splitext(m)[1] in [
                            ".hda",
                            ".hdanc",
                            ".hdalc",
                            ".otl",
                            ".otlnc",
                            ".otllc",
                        ]:
                            origin.prjHDAs.append(
                                os.path.join(i[0], m).replace("\\", "/")
                            )

        oplib = os.path.join(prjHDAs, "ProjectHDAs.oplib").replace("\\", "/")
        for i in origin.prjHDAs:
            hou.hda.installFile(i, oplib)

    @err_decorator
    def executeScript(self, origin, code, execute=False):
        try:
            if not execute:
                return eval(code)
            else:
                exec(code)
        except Exception as e:
            msg = "\npython code:\n%s" % code
            exec("raise type(e), type(e)(e.message + msg), sys.exc_info()[2]")

    @err_decorator
    def getCurrentFileName(self, origin, path=True):
        if path:
            return hou.hipFile.path()
        else:
            return hou.hipFile.basename()

    @err_decorator
    def getCurrentSceneFiles(self, origin):
        return [self.core.getCurrentFileName()]

    @err_decorator
    def getSceneExtension(self, origin):
        if str(hou.licenseCategory()) == "licenseCategoryType.Commercial":
            return ".hip"
        elif str(hou.licenseCategory()) == "licenseCategoryType.Indie":
            return ".hiplc"
        else:
            return ".hipnc"

    @err_decorator
    def saveScene(self, origin, filepath, details={}):
        filepath = filepath.replace("\\", "/")
        return hou.hipFile.save(file_name=filepath, save_to_recent_files=True)

    @err_decorator
    def getImportPaths(self, origin):
        val = hou.node("/obj").userData("PrismImports")

        if val is None:
            return False

        return val

    @err_decorator
    def getFrameRange(self, origin):
        startframe = hou.playbar.playbackRange()[0]
        endframe = hou.playbar.playbackRange()[1]

        return [startframe, endframe]

    @err_decorator
    def setFrameRange(self, origin, startFrame, endFrame):
        setGobalFrangeExpr = "tset `(%d-1)/$FPS` `%d/$FPS`" % (startFrame, endFrame)
        hou.hscript(setGobalFrangeExpr)
        hou.playbar.setPlaybackRange(startFrame, endFrame)
        hou.setFrame(startFrame)

    @err_decorator
    def getFPS(self, origin):
        return hou.fps()

    @err_decorator
    def setFPS(self, origin, fps):
        frange = self.getFrameRange(origin)
        hou.setFps(fps)
        self.setFrameRange(origin, frange[0], frange[1])

    @err_decorator
    def cacheHouTmp(self, ropNode):
        if not os.path.exists(self.core.prismIni):
            curPrj = self.core.getConfig("globals", "current project")
            if curPrj != "" and curPrj is not None:
                QMessageBox.warning(
                    self.core.messageParent,
                    "Warning (cacheHouTmp)",
                    "Could not find project:\n%s"
                    % os.path.dirname(os.path.dirname(curPrj)),
                )

            self.core.setProject(openUi="stateManager")
            return False

        if not self.core.validateUser():
            self.core.changeUser()

        if not hasattr(self.core, "user"):
            return False

        if not self.core.fileInPipeline():
            QMessageBox.warning(
                self.core.messageParent,
                "Could not write the cache",
                "The current file is not inside the Pipeline.\nUse the Project Browser to create a file in the Pipeline.",
            )
            return False

        if self.core.useLocalFiles:
            basePath = self.core.localProjectPath
        else:
            basePath = self.core.projectPath

        exportNode = hou.node(ropNode.path() + "/ropnet1/RENDER")

        sceneBase = os.path.splitext(os.path.basename(self.core.getCurrentFileName()))[
            0
        ]
        outputPath = os.path.join(
            basePath,
            self.core.getConfig("paths", "scenes", configPath=self.core.prismIni),
            "Caches",
            sceneBase,
            ropNode.name(),
        )
        if not os.path.exists(outputPath):
            os.makedirs(outputPath)

        outputFile = "%s_%s.$F4.bgeo" % (sceneBase, ropNode.name())

        outputStr = os.path.join(outputPath, outputFile)
        if not self.setNodeParm(ropNode, "outputpath", outputStr):
            return False

        exportNode.parm("execute").pressButton()

    @err_decorator
    def getAppVersion(self, origin):
        return hou.applicationVersion()[1:-1]

    @err_decorator
    def onProjectBrowserStartup(self, origin):
        if platform.system() == "Darwin":
            origin.menubar.setNativeMenuBar(False)
        origin.loadOiio()
        origin.checkColor = "rgb(185, 134, 32)"

    @err_decorator
    def projectBrowserLoadLayout(self, origin):
        origin.scrollArea.setStyleSheet(
            hou.qt.styleSheet().replace("QLabel", "QScrollArea")
        )

    @err_decorator
    def preLoadEmptyScene(self, origin, filepath):
        self.curDesktop = hou.ui.curDesktop()

    @err_decorator
    def postLoadEmptyScene(self, origin, filepath):
        if hasattr(self, "curDesktop"):
            self.curDesktop.setAsCurrent()

    @err_decorator
    def setRCStyle(self, origin, rcmenu):
        if not self.core.uiAvailable:
            return

        if platform.system() == "Darwin":
            rcmenu.setStyleSheet(hou.ui.mainQtWindow().styleSheet())
        else:
            rcmenu.setStyleSheet(origin.parent().styleSheet())

    @err_decorator
    def openScene(self, origin, filepath, force=False):
        if (
            not filepath.endswith(".hip")
            and not filepath.endswith(".hipnc")
            and not filepath.endswith(".hiplc")
        ):
            return False

        hou.hipFile.load(file_name=filepath)

        return True

    @err_decorator
    def correctExt(self, origin, lfilepath):
        if str(hou.licenseCategory()) == "licenseCategoryType.Commercial":
            return os.path.splitext(lfilepath)[0] + ".hip"
        elif str(hou.licenseCategory()) == "licenseCategoryType.Indie":
            return os.path.splitext(lfilepath)[0] + ".hiplc"
        else:
            return os.path.splitext(lfilepath)[0] + ".hipnc"

    @err_decorator
    def setSaveColor(self, origin, btn):
        btn.setStyleSheet("background-color: " + origin.checkColor)

    @err_decorator
    def clearSaveColor(self, origin, btn):
        btn.setStyleSheet("")

    @err_decorator
    def setProject_loading(self, origin):
        origin.sa_recent.setStyleSheet(
            hou.qt.styleSheet().replace("QLabel", "QScrollArea")
            + "QScrollArea { border: 0px;}"
        )

    @err_decorator
    def onPrismSettingsOpen(self, origin):
        origin.w_startTray.setVisible(False)
        origin.scrollArea.setStyleSheet(
            hou.qt.styleSheet().replace("QLabel", "QScrollArea")
        )

        for i in origin.groupboxes:
            self.fixStyleSheet(i)

        origin.sp_curPfps.setStyleSheet(
            hou.qt.styleSheet().replace("QSpinBox", "QDoubleSpinBox")
        )

    @err_decorator
    def createProject_startup(self, origin):
        origin.scrollArea.setStyleSheet(
            hou.qt.styleSheet().replace("QLabel", "QScrollArea")
        )

    @err_decorator
    def editShot_startup(self, origin):
        origin.loadOiio()

    @err_decorator
    def shotgunPublish_startup(self, origin):
        origin.te_description.setStyleSheet(
            hou.qt.styleSheet().replace("QTextEdit", "QPlainTextEdit")
        )

    @err_decorator
    def fixImportPath(self, origin, depPath):
        if len(depPath) > 4 and depPath[-5] != "v":
            try:
                num = int(depPath[-4:])
                return depPath[:-4] + "$F4"
            except:
                return depPath

        return depPath

    @err_decorator
    def splitExtension(self, origin, path):
        if path.endswith(".bgeo.sc"):
            return [path[: -len(".bgeo.sc")], ".bgeo.sc"]
        else:
            return os.path.splitext(path)

    @err_decorator
    def setNodeParm(self, node, parm, val=None, clear=False):
        try:
            if clear:
                node.parm(parm).deleteAllKeyframes()
            else:
                node.parm(parm).set(val)
        except:
            if not node.parm(parm):
                return False

            curTake = hou.takes.currentTake()
            if (
                curTake.hasParmTuple(node.parm(parm).tuple())
                or curTake.parent() is None
            ):
                msgString = (
                    "Cannot set this parameter. Probably because it is locked:\n\n%s"
                    % node.parm(parm).path()
                )
                msg = QMessageBox(
                    QMessageBox.Warning,
                    "Cannot set Parameter",
                    msgString,
                    QMessageBox.Cancel,
                )
                msg.addButton("Ignore", QMessageBox.YesRole)
                self.core.parentWindow(msg)
                action = msg.exec_()

                if action == 0:
                    return True
                else:
                    return False
            else:
                msgString = (
                    "The parameter is not included in the current take.\nTo continue the parameter should be added to the current take.\n\n%s"
                    % node.parm(parm).path()
                )
                msg = QMessageBox(
                    QMessageBox.Warning,
                    "Locked Parameter",
                    msgString,
                    QMessageBox.Cancel,
                )
                msg.addButton("Add to current take", QMessageBox.YesRole)
                msg.addButton("Ignore", QMessageBox.YesRole)
                self.core.parentWindow(msg)
                action = msg.exec_()

                if action == 0:
                    curTake.addParmTuple(node.parm(parm).tuple())
                    self.setNodeParm(node, parm, val, clear)
                elif action == 1:
                    return True
                else:
                    return False

        return True

    @err_decorator
    def sm_preDelete(self, origin, item, silent=False):
        if not hasattr(item.ui, "node") or silent:
            return

        try:
            item.ui.node.name()
            nodeExists = True
        except:
            nodeExists = False

        if nodeExists:
            msg = QMessageBox(
                QMessageBox.Question,
                "Delete state",
                (
                    "Do you also want to delete the connected node?\n\n%s"
                    % (item.ui.node.path())
                ),
                QMessageBox.No,
            )
            msg.addButton("Yes", QMessageBox.YesRole)
            msg.setParent(self.core.messageParent, Qt.Window)
            action = msg.exec_()

            if action == 0:
                try:
                    if item.ui.className == "ImportFile":
                        nwBox = hou.node("/obj").findNetworkBox("Import")
                        if nwBox is not None:
                            if (
                                len(nwBox.nodes()) == 1
                                and nwBox.nodes()[0] == item.ui.node
                            ):
                                nwBox.destroy()
                    item.ui.node.destroy()
                    if hasattr(item.ui, "node2"):
                        item.ui.node2.destroy()
                except:
                    pass

        if (
            item.ui.className == "ImportFile"
            and os.path.splitext(item.ui.e_file.text())[1] == ".hda"
        ):
            fpath = item.ui.e_file.text().replace("\\", "/")
            defs = hou.hda.definitionsInFile(fpath)
            if len(defs) > 0 and defs[0].isInstalled():
                hou.hda.uninstallFile(fpath)

    @err_decorator
    def sm_preSaveToScene(self, origin):
        if origin.scenename == self.core.getCurrentFileName():
            return

        origin.saveEnabled = False

        msg = QMessageBox(
            QMessageBox.NoIcon,
            "State Manager",
            "Houdini still has no decent callback system, so you need to tell me what to do:",
        )
        msg.addButton("Save current states to scene", QMessageBox.YesRole)
        msg.addButton("Reload states from scene", QMessageBox.NoRole)
        msg.addButton("Close", QMessageBox.NoRole)

        msg.setParent(self.core.messageParent, Qt.Window)

        action = msg.exec_()

        origin.scenename = self.core.getCurrentFileName()

        if action == 1:
            self.core.closeSM(restart=True)
            return False
        elif action == 2:
            self.core.closeSM()
            return False

        origin.saveEnabled = True

    def fixStyleSheet(self, widget):
        root = self.core.prismRoot.replace("\\", "/")
        ssheet = ""
        ssheet += (
            "QGroupBox::indicator::checked\n{\n    image: url(%s/Plugins/Apps/Houdini/UserInterfaces/checkbox_on.svg);\n}"
            % root
        )
        ssheet += (
            "QGroupBox::indicator::unchecked\n{\n    image: url(%s/Plugins/Apps/Houdini/UserInterfaces/checkbox_off.svg);\n}"
            % root
        )
        ssheet += "QGroupBox::indicator { width: 16px; height: 16px;}"
        widget.setStyleSheet(ssheet)

    @err_decorator
    def getFrameStyleSheet(self, origin):
        return hou.qt.styleSheet().replace("QWidget", "QFrame")

    @err_decorator
    def onStateManagerOpen(self, origin):
        if platform.system() == "Darwin":
            origin.menubar.setNativeMenuBar(False)

        if self.core.uiAvailable:
            origin.enabledCol = QBrush(QColor(204, 204, 204))

        if self.core.uiAvailable:
            origin.scrollArea.setStyleSheet(
                hou.qt.styleSheet().replace("QLabel", "QScrollArea")
            )

        origin.f_import.setStyleSheet("QFrame { border: 0px; }")
        origin.f_export.setStyleSheet("QFrame { border: 0px; }")

        root = self.core.prismRoot.replace("\\", "/")
        ssheet = ""
        ssheet += (
            "QTreeWidget::indicator::checked\n{\n    image: url(%s/Plugins/Apps/Houdini/UserInterfaces/checkbox_on.svg);\n}"
            % root
        )
        ssheet += (
            "QTreeWidget::indicator::unchecked\n{\n    image: url(%s/Plugins/Apps/Houdini/UserInterfaces/checkbox_off.svg);\n}"
            % root
        )
        ssheet += "QTreeWidget::indicator { width: 16px; height: 16px;}"

        origin.tw_export.setStyleSheet(ssheet)

        origin.b_stateFromNode.setVisible(True)
        # 	origin.b_createDependency.setVisible(True)
        origin.layout().setContentsMargins(0, 0, 0, 0)

        origin.b_createExport.setText("Exp")
        origin.b_createRender.setText("Rnd")
        origin.b_createPlayblast.setText("Pb")

        origin.b_createImport.setMinimumWidth(80 * self.core.uiScaleFactor)
        origin.b_createImport.setMaximumWidth(80 * self.core.uiScaleFactor)
        origin.b_createExport.setMinimumWidth(55 * self.core.uiScaleFactor)
        origin.b_createExport.setMaximumWidth(55 * self.core.uiScaleFactor)
        origin.b_createRender.setMinimumWidth(55 * self.core.uiScaleFactor)
        origin.b_createRender.setMaximumWidth(55 * self.core.uiScaleFactor)
        origin.b_createPlayblast.setMinimumWidth(50 * self.core.uiScaleFactor)
        origin.b_createPlayblast.setMaximumWidth(50 * self.core.uiScaleFactor)
        origin.b_createDependency.setMinimumWidth(50 * self.core.uiScaleFactor)
        origin.b_createDependency.setMaximumWidth(50 * self.core.uiScaleFactor)
        origin.b_stateFromNode.setMinimumWidth(130 * self.core.uiScaleFactor)
        origin.b_stateFromNode.setMaximumWidth(130 * self.core.uiScaleFactor)
        origin.b_getRange.setMaximumWidth(200 * self.core.uiScaleFactor)
        origin.b_setRange.setMaximumWidth(200 * self.core.uiScaleFactor)

        startframe = hou.playbar.playbackRange()[0]
        endframe = hou.playbar.playbackRange()[1]
        origin.sp_rangeStart.setValue(startframe)
        origin.sp_rangeEnd.setValue(endframe)

        usdType = hou.nodeType(hou.sopNodeTypeCategory(), "pixar::usdrop")
        if usdType is not None and ".usd" not in self.plugin.outputFormats:
            self.plugin.outputFormats.insert(-2, ".usd")
        elif usdType is None and ".usd" in self.plugin.outputFormats:
            self.plugin.outputFormats.pop(self.plugin.outputFormats.index(".usd"))

        rsType = hou.nodeType(hou.sopNodeTypeCategory(), "Redshift_Proxy_Output")
        if rsType is not None and ".rs" not in self.plugin.outputFormats:
            self.plugin.outputFormats.insert(-2, ".rs")
        elif rsType is None and ".rs" in self.plugin.outputFormats:
            self.plugin.outputFormats.pop(self.plugin.outputFormats.index(".rs"))

    @err_decorator
    def sm_saveStates(self, origin, buf):
        hou.node("/obj").setUserData("PrismStates", buf)

    @err_decorator
    def sm_saveImports(self, origin, importPaths):
        hou.node("/obj").setUserData("PrismImports", importPaths)

    @err_decorator
    def sm_readStates(self, origin):
        stateData = hou.node("/obj").userData("PrismStates")
        if stateData is not None:
            return stateData

    @err_decorator
    def sm_deleteStates(self, origin):
        if hou.node("/obj").userData("PrismStates") is not None:
            hou.node("/obj").destroyUserData("PrismStates")

    @err_decorator
    def sm_getExternalFiles(self, origin):
        # 	hou.setFrame(hou.playbar.playbackRange()[0])
        whitelist = [
            "$HIP/$OS-bounce.rat",
            "$HIP/$OS-fill.rat",
            "$HIP/$OS-key.rat",
            "$HIP/$OS-rim.rat",
        ]
        expNodes = [
            x.ui.node
            for x in self.core.sm.states
            if x.ui.className in ["Export", "ImageRender"]
            and x.ui.node is not None
            and self.isNodeValid(origin, x.ui.node)
        ]
        houdeps = hou.fileReferences()
        extFiles = []
        extFilesSource = []
        for x in houdeps:
            if "/Redshift/Plugins/Houdini/" in x[1]:
                continue

            if x[0] is None:
                continue

            if x[0].node() in expNodes:
                continue

            if x[0].node().parent() in expNodes and x[0].node().type().name() == "file":
                continue

            if x[1] in whitelist:
                continue

            if not os.path.isabs(hou.expandString(x[1])):
                continue

            if os.path.splitext(hou.expandString(x[1]))[1] == "":
                continue

            if x[0] is not None and x[0].name() in [
                "RS_outputFileNamePrefix",
                "vm_picture",
            ]:
                continue

            if (
                x[0] is not None
                and x[0].name() in ["filename", "dopoutput", "copoutput", "sopoutput"]
                and x[0].node().type().name()
                in ["rop_alembic", "rop_dop", "rop_comp", "rop_geometry"]
            ):
                continue

            if (
                x[0] is not None
                and x[0].name() in ["filename", "sopoutput"]
                and x[0].node().type().category().name() == "Driver"
                and x[0].node().type().name() in ["geometry", "alembic"]
            ):
                continue

            extFiles.append(hou.expandString(x[1]).replace("\\", "/"))
            extFilesSource.append(x[0])

        return [extFiles, extFilesSource]

    @err_decorator
    def isNodeValid(self, origin, node):
        try:
            node.name()
            return True
        except:
            return False

    @err_decorator
    def sm_createRenderPressed(self, origin):
        renderers = self.getRendererPlugins()
        if len(hou.selectedNodes()) > 0:
            for i in renderers:
                if hou.selectedNodes()[0].type().name() in i.ropNames:
                    origin.createPressed("Render")
                    return

        if len(renderers) == 1:
            origin.createPressed("Render", renderer=renderers[0].label)
        else:
            rndMenu = QMenu()
            for i in renderers:
                mAct = QAction(i.label, origin)
                mAct.triggered.connect(
                    lambda x=None, y=i.label: origin.createPressed("Render", renderer=y)
                )
                rndMenu.addAction(mAct)

            if rndMenu.isEmpty():
                origin.createPressed("Render")
                return False

            self.setRCStyle(origin, rndMenu)

            rndMenu.exec_(QCursor.pos())

    @err_decorator
    def getRendererPlugins(self):
        gpath = os.path.dirname(os.path.abspath(__file__)) + "/Prism_Houdini_Renderer_*"
        files = glob.glob(gpath)

        rplugs = []
        for f in files:
            if f.endswith(".pyc"):
                continue

            rname = os.path.splitext(os.path.basename(f))[0]

            try:
                del sys.modules[rname]
            except:
                pass

            rplug = __import__(rname)
            if hasattr(rplug, "isActive") and rplug.isActive():
                rplugs.append(rplug)

        return rplugs

    @err_decorator
    def sm_existExternalAsset(self, origin, asset):
        if asset.startswith("op:") and hou.node(asset.replace("\\", "/")) is not None:
            return True

        return False

    @err_decorator
    def sm_fixWarning(self, origin, asset, extFiles, extFilesSource):
        parm = extFilesSource[extFiles.index(asset.replace("\\", "/"))]
        if parm is None:
            parmStr = ""
        else:
            parmStr = "In parameter: %s" % parm.path()

        return parmStr

    @err_decorator
    def sm_openStateFromNode(self, origin):
        nodeMenu = QMenu()

        renderMenu = QMenu("ImageRender")

        renderNodes = []
        for node in hou.node("/").allSubChildren():
            if node.type().name() in ["ifd", "Redshift_ROP"]:
                renderNodes.append(node)

        for i in origin.states:
            if (
                i.ui.className == "ImageRender"
                and i.ui.node is not None
                and i.ui.node in renderNodes
            ):
                renderNodes.remove(i.ui.node)

        for i in renderNodes:
            actRender = QAction(i.path(), origin)
            actRender.triggered.connect(
                lambda y=None, x=i: origin.createState(
                    "ImageRender", node=x, setActive=True
                )
            )
            renderMenu.addAction(actRender)

        nodeMenu.addMenu(renderMenu)

        ropMenu = QMenu("Export")

        ropNodes = []
        for node in hou.node("/").allSubChildren():
            if node.type().name() in [
                "rop_dop",
                "rop_comp",
                "rop_geometry",
                "rop_alembic",
                "filecache",
                "pixar::usdrop",
                "Redshift_Proxy_Output",
            ]:
                ropNodes.append(node)

            if node.type().category().name() == "Driver" and node.type().name() in [
                "geometry",
                "alembic",
            ]:
                ropNodes.append(node)

        for i in origin.states:
            if (
                i.ui.className == "Export"
                and i.ui.node is not None
                and i.ui.node in ropNodes
            ):
                ropNodes.remove(i.ui.node)

        for i in ropNodes:
            actExport = QAction(i.path(), origin)
            actExport.triggered.connect(
                lambda y=None, x=i: origin.createState("Export", node=x, setActive=True)
            )
            ropMenu.addAction(actExport)

        nodeMenu.addMenu(ropMenu)

        self.setRCStyle(origin, nodeMenu)
        self.setRCStyle(origin, renderMenu)
        self.setRCStyle(origin, ropMenu)

        nodeMenu.exec_(QCursor.pos())

    @err_decorator
    def sm_render_getDeadlineParams(self, origin, dlParams, homeDir):
        dlParams["pluginInfoFile"] = os.path.join(
            homeDir, "temp", "houdini_plugin_info.job"
        )
        dlParams["jobInfoFile"] = os.path.join(
            homeDir, "temp", "houdini_submit_info.job"
        )

        dlParams["jobInfos"]["Plugin"] = "Houdini"
        dlParams["jobInfos"]["Comment"] = (
            "Prism-Submission-Houdini_%s" % origin.className
        )

        dlParams["pluginInfos"]["OutputDriver"] = origin.node.path()
        dlParams["pluginInfos"]["IgnoreInputs"] = "True"

        if (
            int(
                self.core.rfManagers["Deadline"]
                .deadlineCommand(["-version"])
                .split(".")[0][1:]
            )
            > 9
        ):
            dlParams["pluginInfos"]["Version"] = "%s.%s" % (
                hou.applicationVersion()[0],
                hou.applicationVersion()[1],
            )
        else:
            dlParams["pluginInfos"]["Version"] = hou.applicationVersion()[0]

        if hasattr(origin, "chb_resOverride") and origin.chb_resOverride.isChecked():
            dlParams["pluginInfos"]["Width"] = origin.sp_resWidth.value()
            dlParams["pluginInfos"]["Height"] = origin.sp_resHeight.value()

    @err_decorator
    def sm_renderSettings_getCurrentSettings(self, origin, node=None):
        settings = []
        if not node:
            node = hou.node(origin.e_node.text())

        if not node:
            return ""

        for parm in sorted(node.parms(), key=lambda x: x.name().lower()):
            setting = {}
            if len(parm.keyframes()) == 1:
                setting[parm.name()] = parm.expression() + " [expression]"
            elif parm.parmTemplate().dataType() == hou.parmData.String:
                setting[parm.name()] = parm.unexpandedString()
            else:
                setting[parm.name()] = parm.eval()
            settings.append(setting)

        settingsStr = self.core.writeYaml(data=settings)
        return settingsStr

    @err_decorator
    def sm_renderSettings_setCurrentSettings(
        self, origin, preset, state=None, node=None
    ):
        if not node:
            if state:
                node = hou.node(state.e_node.text())
        if not node:
            return

        for setting in preset:
            parm = node.parm(setting.keys()[0])
            if not parm:
                continue

            value = setting.values()[0]
            if type(value) in [str, unicode] and value.endswith(" [expression]"):
                value = value[: -len(" [expression")]
                parm.setExpression(value)
            else:
                parm.deleteAllKeyframes()
                try:
                    parm.set(value)
                except:
                    pass

    @err_decorator
    def sm_renderSettings_applyDefaultSettings(self, origin):
        node = hou.node(origin.e_node.text())
        if not node:
            return

        for parm in node.parms():
            parm.revertToDefaults()

    @err_decorator
    def sm_renderSettings_startup(self, origin):
        origin.w_node = QWidget()
        origin.lo_node = QHBoxLayout()
        origin.w_node.setLayout(origin.lo_node)
        origin.l_node = QLabel("Node:")
        origin.e_node = QLineEdit()
        origin.e_node.setContextMenuPolicy(Qt.CustomContextMenu)
        origin.e_node.customContextMenuRequested.connect(
            lambda x: self.showNodeContext(origin)
        )
        origin.e_node.editingFinished.connect(origin.stateManager.saveStatesToScene)
        if self.core.uiAvailable:
            origin.b_node = hou.qt.NodeChooserButton()
            origin.b_node.nodeSelected.connect(lambda x: origin.e_node.setText(x.path()))
            origin.b_node.nodeSelected.connect(origin.stateManager.saveStatesToScene)
            origin.lo_node.addWidget(origin.b_node)

        origin.lo_node.addWidget(origin.l_node)
        origin.lo_node.addWidget(origin.e_node)
        origin.gb_general.layout().insertWidget(0, origin.w_node)

    @err_decorator
    def sm_renderSettings_loadData(self, origin, data):
        if "node" in data:
            origin.e_node.setText(data["node"])

    @err_decorator
    def sm_renderSettings_getStateProps(self, origin):
        stateProps = {"node": origin.e_node.text()}

        return stateProps

    @err_decorator
    def sm_renderSettings_addSelected(self, origin):
        if len(hou.selectedNodes()) == 0:
            return False

        origin.e_node.setText(hou.selectedNodes()[0].path())

    @err_decorator
    def sm_renderSettings_preExecute(self, origin):
        warnings = []

        if not hou.node(origin.e_node.text()):
            warnings.append(["Invalid node specified.", "", 2])

        return warnings

    @err_decorator
    def showNodeContext(self, origin):
        rcMenu = QMenu()
        mAct = QAction("Add selected", origin)
        mAct.triggered.connect(lambda: self.sm_renderSettings_addSelected(origin))
        rcMenu.addAction(mAct)

        self.setRCStyle(origin.stateManager, rcMenu)
        rcMenu.exec_(QCursor.pos())
