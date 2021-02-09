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
import platform
import subprocess

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

if platform.system() == "Windows":
    import win32com.client

from PrismUtils.Decorators import err_catcher as err_catcher


class Prism_Photoshop_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        self.win = platform.system() == "Windows"

    @err_catcher(name=__name__)
    def startup(self, origin):
        origin.timer.stop()

        with (
            open(
                os.path.join(
                    self.core.prismRoot,
                    "Plugins",
                    "Apps",
                    "Photoshop",
                    "UserInterfaces",
                    "PhotoshopStyleSheet",
                    "Photoshop.qss",
                ),
                "r",
            )
        ) as ssFile:
            ssheet = ssFile.read()

        ssheet = ssheet.replace(
            "qss:",
            os.path.join(
                self.core.prismRoot,
                "Plugins",
                "Apps",
                "Photoshop",
                "UserInterfaces",
                "PhotoshopStyleSheet",
            ).replace("\\", "/")
            + "/",
        )
        # ssheet = ssheet.replace("#c8c8c8", "rgb(40, 40, 40)").replace("#727272", "rgb(83, 83, 83)").replace("#5e90fa", "rgb(89, 102, 120)").replace("#505050", "rgb(70, 70, 70)")
        # ssheet = ssheet.replace("#a6a6a6", "rgb(145, 145, 145)").replace("#8a8a8a", "rgb(95, 95, 95)").replace("#b5b5b5", "rgb(155, 155, 155)").replace("#999999", "rgb(105, 105, 105)")
        # ssheet = ssheet.replace("#9f9f9f", "rgb(58, 58, 58)").replace("#b2b2b2", "rgb(58, 58, 58)").replace("#aeaeae", "rgb(65, 65, 65)").replace("#c1c1c1", "rgb(65, 65, 65)")

        qApp.setStyleSheet(ssheet)
        appIcon = QIcon(
            os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "p_tray.png"
            )
        )
        qApp.setWindowIcon(appIcon)

        if self.win:
            try:
                # CS6: .60, CC2015: .90
                self.psApp = win32com.client.Dispatch("Photoshop.Application")
            except Exception as e:
                QMessageBox.warning(
                    self.core.messageParent,
                    "Warning",
                    "Could not connect to Photoshop:\n\n%s" % str(e),
                )
                return False
        else:
            self.psAppName = "Adobe Photoshop CC 2019"
            for foldercont in os.walk("/Applications"):
                for folder in reversed(sorted(foldercont[1])):
                    if folder.startswith("Adobe Photoshop"):
                        self.psAppName = folder
                        break
                break

            scpt = (
                """
            tell application "%s"
                activate
            end tell
            """
                % self.psAppName
            )
            self.executeAppleScript(scpt)

        return False

    @err_catcher(name=__name__)
    def onProjectChanged(self, origin):
        pass

    @err_catcher(name=__name__)
    def sceneOpen(self, origin):
        pass

    @err_catcher(name=__name__)
    def executeScript(self, origin, code, preventError=False):
        if preventError:
            try:
                return eval(code)
            except Exception as e:
                msg = "\npython code:\n%s" % code
                exec("raise type(e), type(e)(e.message + msg), sys.exc_info()[2]")
        else:
            return eval(code)

    @err_catcher(name=__name__)
    def executeAppleScript(self, script):
        p = subprocess.Popen(
            ["osascript"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = p.communicate(script)
        if p.returncode != 0:
            return None

        return stdout

    @err_catcher(name=__name__)
    def getCurrentFileName(self, origin, path=True):
        try:
            if self.win:
                doc = self.psApp.Application.ActiveDocument
                currentFileName = doc.FullName
            else:
                scpt = (
                    """
                tell application "%s"
                    set fpath to file path of current document
                    POSIX path of fpath
                end tell
                """
                    % self.psAppName
                )
                currentFileName = self.executeAppleScript(scpt)

                if currentFileName is None:
                    raise

                if currentFileName.endswith("\n"):
                    currentFileName = currentFileName[:-1]

        except:
            currentFileName = ""

        if not path and currentFileName != "":
            currentFileName = os.path.basename(currentFileName)

        return currentFileName

    @err_catcher(name=__name__)
    def getSceneExtension(self, origin):
        doc = self.core.getCurrentFileName()
        if doc != "":
            return os.path.splitext(doc)[1]

        return self.sceneFormats[0]

    @err_catcher(name=__name__)
    def onSaveExtendedOpen(self, origin):
        origin.l_format = QLabel("Save as:")
        origin.cb_format = QComboBox()
        origin.cb_format.addItems(self.sceneFormats)
        curFilename = self.core.getCurrentFileName()
        if curFilename:
            ext = os.path.splitext(curFilename)[1]
            idx = self.sceneFormats.index(ext)
            if idx != -1:
                origin.cb_format.setCurrentIndex(idx)
        rowIdx = origin.w_details.layout().rowCount()
        origin.w_details.layout().addWidget(origin.l_format, rowIdx, 0)
        origin.w_details.layout().addWidget(origin.cb_format, rowIdx, 1)

    @err_catcher(name=__name__)
    def onGetSaveExtendedDetails(self, origin, details):
        details["fileFormat"] = origin.cb_format.currentText()

    @err_catcher(name=__name__)
    def getCharID(self, s):
        return self.psApp.CharIDToTypeID(s)

    @err_catcher(name=__name__)
    def getStringID(self, s):
        return self.psApp.StringIDToTypeID(s)

    @err_catcher(name=__name__)
    def saveScene(self, origin, filepath, details={}):
        try:
            if self.win:
                doc = self.psApp.ActiveDocument
            else:
                scpt = (
                    """
                tell application "%s"
                    set fpath to name of current document
                    POSIX path of fpath
                end tell
                """
                    % self.psAppName
                )
                name = self.executeAppleScript(scpt)
                if name is None:
                    raise
        except:
            self.core.popup("There is no active document in Photoshop.")
            return False

        if "fileFormat" in details:
            filepath = os.path.splitext(filepath)[0] + details["fileFormat"]

        try:
            if self.win:
                if os.path.splitext(filepath)[1] == ".psb":
                    desc1 = win32com.client.Dispatch("Photoshop.ActionDescriptor")
                    desc2 = win32com.client.Dispatch("Photoshop.ActionDescriptor")
                    desc2.PutBoolean(self.getStringID("maximizeCompatibility"), True)
                    desc1.PutObject(
                        self.getCharID("As  "), self.getCharID("Pht8"), desc2
                    )
                    desc1.PutPath(self.getCharID("In  "), filepath)
                    desc1.PutBoolean(self.getCharID("LwCs"), True)
                    self.psApp.ExecuteAction(self.getCharID("save"), desc1)
                else:
                    doc.SaveAs(filepath)
            else:
                if os.path.splitext(filepath)[1] == ".psb":
                    scpt = """
                    tell application "%s"
                        do javascript "
                            var idsave = charIDToTypeID( 'save' );
                            var desc12 = new ActionDescriptor();
                            var idAs = charIDToTypeID( 'As  ' );
                            var desc13 = new ActionDescriptor();
                            var idmaximizeCompatibility = stringIDToTypeID( 'maximizeCompatibility' );
                            desc13.putBoolean( idmaximizeCompatibility, true );
                            var idPhteight = charIDToTypeID( 'Pht8' );
                            desc12.putObject( idAs, idPhteight, desc13 );
                            var idIn = charIDToTypeID( 'In  ' );
                            desc12.putPath( idIn, new File( '%s' ) );
                            var idsaveStage = stringIDToTypeID( 'saveStage' );
                            var idsaveStageType = stringIDToTypeID( 'saveStageType' );
                            var idsaveSucceeded = stringIDToTypeID( 'saveSucceeded' );
                            desc12.putEnumerated( idsaveStage, idsaveStageType, idsaveSucceeded );
                            executeAction( idsave, desc12, DialogModes.NO );
                        " show debugger on runtime error
                    end tell
                    """ % (
                        self.psAppName,
                        filepath,
                    )
                    doc = self.executeAppleScript(scpt)
                else:
                    scpt = """
                    tell application "%s"
                        save current document in file "%s"
                    end tell
                    """ % (
                        self.psAppName,
                        filepath,
                    )
                    doc = self.executeAppleScript(scpt)

                if doc is None:
                    raise
        except:
            return ""

    @err_catcher(name=__name__)
    def getImportPaths(self, origin):
        return False

    @err_catcher(name=__name__)
    def getFrameRange(self, origin):
        pass

    @err_catcher(name=__name__)
    def setFrameRange(self, origin, startFrame, endFrame):
        pass

    @err_catcher(name=__name__)
    def getFPS(self, origin):
        pass

    @err_catcher(name=__name__)
    def getAppVersion(self, origin):
        if self.win:
            version = self.psApp.Version
        else:
            scpt = (
                """
                tell application "%s"
                    application version
                end tell
            """
                % self.psAppName
            )
            version = self.executeAppleScript(scpt)

        return version

    @err_catcher(name=__name__)
    def onProjectBrowserStartup(self, origin):
        origin.actionStateManager.setEnabled(False)
        psMenu = QMenu("Photoshop", origin)
        psAction = QAction("Open tools", origin)
        psAction.triggered.connect(self.openPhotoshopTools)
        psMenu.addAction(psAction)
        origin.menuTools.addSeparator()
        origin.menuTools.addMenu(psMenu)

    @err_catcher(name=__name__)
    def openScene(self, origin, filepath, force=False):
        if not force and os.path.splitext(filepath)[1] not in self.sceneFormats:
            return False

        if self.win:
            self.psApp.Open(filepath)
        else:
            scpt = """
                tell application "%s"
                    open file "%s"
                end tell
            """ % (
                self.psAppName,
                filepath,
            )
            self.executeAppleScript(scpt)

        return True

    @err_catcher(name=__name__)
    def correctExt(self, origin, lfilepath):
        return lfilepath

    @err_catcher(name=__name__)
    def setSaveColor(self, origin, btn):
        btn.setPalette(origin.savedPalette)

    @err_catcher(name=__name__)
    def clearSaveColor(self, origin, btn):
        btn.setPalette(origin.oldPalette)

    @err_catcher(name=__name__)
    def importImages(self, origin):
        fString = "Please select an import option:"
        msg = QMessageBox(
            QMessageBox.NoIcon, "Photoshop Import", fString, QMessageBox.Cancel
        )
        msg.addButton("Current pass", QMessageBox.YesRole)
        #   msg.addButton("All passes", QMessageBox.YesRole)
        #   msg.addButton("Layout all passes", QMessageBox.YesRole)
        self.core.parentWindow(msg)
        action = msg.exec_()

        if action == 0:
            self.photoshopImportSource(origin)
        #   elif action == 1:
        #       self.photoshopImportPasses(origin)
        #   elif action == 2:
        #       self.photoshopLayout(origin)
        else:
            return

    @err_catcher(name=__name__)
    def photoshopImportSource(self, origin):
        mpb = origin.mediaPlaybacks["shots"]
        sourceFolder = os.path.dirname(
            os.path.join(mpb["basePath"], mpb["seq"][0])
        ).replace("\\", "/")
        sources = origin.getImgSources(sourceFolder)
        for curSourcePath in sources:

            if "@@@@" in curSourcePath:
                if (
                    "pstart" not in mpb
                    or "pend" not in mpb
                    or mpb["pstart"] == "?"
                    or mpb["pend"] == "?"
                ):
                    firstFrame = 0
                    lastFrame = 0
                else:
                    firstFrame = mpb["pstart"]
                    lastFrame = mpb["pend"]

                filePath = curSourcePath.replace("@"*self.core.framePadding, "%04d".replace("4", str(self.core.framePadding)) % firstFrame).replace(
                    "\\", "/"
                )
            else:
                filePath = curSourcePath.replace("\\", "/")
                firstFrame = 0
                lastFrame = 0

            self.openScene(origin, filePath, force=True)

            # curReadNode = photoshop.createNode("Read",'file %s first %s last %s' % (filePath,firstFrame,lastFrame),False)

    @err_catcher(name=__name__)
    def photoshopImportPasses(self, origin):
        sourceFolder = os.path.dirname(
            os.path.dirname(os.path.join(origin.basepath, origin.seq[0]))
        ).replace("\\", "/")
        passes = [
            x
            for x in os.listdir(sourceFolder)
            if x[-5:] not in ["(mp4)", "(jpg)", "(png)"]
            and os.path.isdir(os.path.join(sourceFolder, x))
        ]

        for curPass in passes:
            curPassPath = os.path.join(sourceFolder, curPass)

            imgs = os.listdir(curPassPath)
            if len(imgs) == 0:
                continue

            if len(imgs) > 1:
                if (
                    not hasattr(origin, "pstart")
                    or not hasattr(origin, "pend")
                    or origin.pstart == "?"
                    or origin.pend == "?"
                ):
                    return

                firstFrame = origin.pstart
                lastFrame = origin.pend

                curPassName = imgs[0].split(".")[0]
                increment = "####"
                curPassFormat = imgs[0].split(".")[-1]

                filePath = os.path.join(
                    sourceFolder,
                    curPass,
                    ".".join([curPassName, increment, curPassFormat]),
                ).replace("\\", "/")
            else:
                filePath = os.path.join(curPassPath, imgs[0]).replace("\\", "/")
                firstFrame = 0
                lastFrame = 0

            curReadNode = photoshop.createNode(
                "Read",
                "file %s first %s last %s" % (filePath, firstFrame, lastFrame),
                False,
            )

    @err_catcher(name=__name__)
    def setProject_loading(self, origin):
        pass

    @err_catcher(name=__name__)
    def onPrismSettingsOpen(self, origin):
        pass

    @err_catcher(name=__name__)
    def createProject_startup(self, origin):
        pass

    @err_catcher(name=__name__)
    def editShot_startup(self, origin):
        pass

    @err_catcher(name=__name__)
    def shotgunPublish_startup(self, origin):
        pass

    @err_catcher(name=__name__)
    def openPhotoshopTools(self):
        self.dlg_tools = QDialog()

        lo_tools = QVBoxLayout()
        self.dlg_tools.setLayout(lo_tools)

        b_saveVersion = QPushButton("Save Version")
        b_saveComment = QPushButton("Save Extended")
        b_export = QPushButton("Export")
        b_projectBrowser = QPushButton("Project Browser")
        b_settings = QPushButton("Settings")

        b_saveVersion.clicked.connect(self.core.saveScene)
        b_saveComment.clicked.connect(self.core.saveWithComment)
        b_export.clicked.connect(self.exportImage)
        b_projectBrowser.clicked.connect(self.core.projectBrowser)
        b_settings.clicked.connect(self.core.prismSettings)

        lo_tools.addWidget(b_saveVersion)
        lo_tools.addWidget(b_saveComment)
        lo_tools.addWidget(b_export)
        lo_tools.addWidget(b_projectBrowser)
        lo_tools.addWidget(b_settings)

        self.core.parentWindow(self.dlg_tools)
        self.dlg_tools.setWindowTitle("Prism")

        self.dlg_tools.show()

        return True

    @err_catcher(name=__name__)
    def exportImage(self):
        if not self.core.projects.ensureProject():
            return False

        if not self.core.users.ensureUser():
            return False

        curfile = self.core.getCurrentFileName()
        fname = self.core.getScenefileData(curfile)

        if fname["entity"] == "invalid":
            entityType = "context"
        else:
            entityType = fname["entity"]

        self.dlg_export = QDialog()
        self.core.parentWindow(self.dlg_export)
        self.dlg_export.setWindowTitle("Prism - Export image")

        lo_export = QVBoxLayout()
        self.dlg_export.setLayout(lo_export)

        self.rb_task = QRadioButton("Export into current %s" % entityType)
        self.w_task = QWidget()
        lo_prismExport = QVBoxLayout()
        lo_task = QHBoxLayout()
        self.w_comment = QWidget()
        lo_comment = QHBoxLayout()
        self.w_comment.setLayout(lo_comment)
        lo_comment.setContentsMargins(0, 0, 0, 0)
        lo_version = QHBoxLayout()
        lo_extension = QHBoxLayout()
        lo_localOut = QHBoxLayout()
        l_task = QLabel("Task:")
        l_task.setMinimumWidth(110)
        self.le_task = QLineEdit()
        self.b_task = QPushButton(u"▼")
        self.b_task.setMinimumSize(35, 0)
        self.b_task.setMaximumSize(35, 500)
        l_comment = QLabel("Comment (optional):")
        l_comment.setMinimumWidth(110)
        self.le_comment = QLineEdit()
        self.chb_useNextVersion = QCheckBox("Use next version")
        self.chb_useNextVersion.setChecked(True)
        self.chb_useNextVersion.setMinimumWidth(110)
        self.cb_versions = QComboBox()
        self.cb_versions.setEnabled(False)
        l_ext = QLabel("Format:")
        l_ext.setMinimumWidth(110)
        self.cb_formats = QComboBox()
        self.cb_formats.addItems([".jpg", ".png", ".tif", ".exr"])
        self.chb_localOutput = QCheckBox("Local output")
        lo_task.addWidget(l_task)
        lo_task.addWidget(self.le_task)
        lo_task.addWidget(self.b_task)
        lo_comment.addWidget(l_comment)
        lo_comment.addWidget(self.le_comment)
        lo_version.addWidget(self.chb_useNextVersion)
        lo_version.addWidget(self.cb_versions)
        lo_version.addStretch()
        lo_extension.addWidget(l_ext)
        lo_extension.addWidget(self.cb_formats)
        lo_extension.addStretch()
        lo_localOut.addWidget(self.chb_localOutput)
        lo_prismExport.addLayout(lo_task)
        lo_prismExport.addWidget(self.w_comment)
        lo_prismExport.addLayout(lo_version)
        lo_prismExport.addLayout(lo_extension)
        lo_prismExport.addLayout(lo_localOut)
        self.w_task.setLayout(lo_prismExport)
        lo_version.setContentsMargins(0, 0, 0, 0)

        rb_custom = QRadioButton("Export to custom location")

        self.b_export = QPushButton("Export")

        lo_export.addWidget(self.rb_task)
        lo_export.addWidget(self.w_task)
        lo_export.addWidget(rb_custom)
        lo_export.addStretch()
        lo_export.addWidget(self.b_export)

        self.rb_task.setChecked(True)
        self.dlg_export.resize(400, 300)

        self.rb_task.toggled.connect(self.exportToggle)
        self.b_task.clicked.connect(self.exportShowTasks)
        self.le_comment.textChanged.connect(self.validateComment)
        self.chb_useNextVersion.toggled.connect(self.exportVersionToggled)
        self.le_task.editingFinished.connect(self.exportGetVersions)
        self.b_export.clicked.connect(self.saveExport)

        if not self.core.useLocalFiles:
            self.chb_localOutput.setVisible(False)

        self.exportGetTasks()
        self.core.callback(
            name="photoshop_onExportOpen",
            types=[],
            args=[self],
        )

        self.dlg_export.show()

        self.cb_versions.setMinimumWidth(300)
        self.cb_formats.setMinimumWidth(300)

        return True

    @err_catcher(name=__name__)
    def exportToggle(self, checked):
        self.w_task.setEnabled(checked)

    @err_catcher(name=__name__)
    def exportGetTasks(self):
        self.taskList = self.core.getTaskNames("2d")

        if len(self.taskList) == 0:
            self.b_task.setHidden(True)
        else:
            if "_ShotCam" in self.taskList:
                self.taskList.remove("_ShotCam")

    @err_catcher(name=__name__)
    def exportShowTasks(self):
        tmenu = QMenu(self.dlg_export)

        for i in self.taskList:
            tAct = QAction(i, self.dlg_export)
            tAct.triggered.connect(lambda x=None, t=i: self.le_task.setText(t))
            tAct.triggered.connect(self.exportGetVersions)
            tmenu.addAction(tAct)

        tmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def exportGetVersions(self):
        existingVersions = []
        outData = self.exportGetOutputName()
        if outData is not None:
            versionDir = os.path.dirname(outData[1])

            if os.path.exists(versionDir):
                for i in reversed(sorted(os.listdir(versionDir))):
                    if len(i) < 5 or not i.startswith("v"):
                        continue

                    if sys.version[0] == "2":
                        if not unicode(i[1:5]).isnumeric():
                            continue
                    else:
                        if not i[1:5].isnumeric():
                            continue

                    existingVersions.append(i)

        self.cb_versions.clear()
        self.cb_versions.addItems(existingVersions)

    @err_catcher(name=__name__)
    def exportGetOutputName(self, useVersion="next"):
        if self.le_task.text() == "":
            return

        extension = self.cb_formats.currentText()
        fileName = self.core.getCurrentFileName()

        if self.core.useLocalFiles:
            if self.chb_localOutput.isChecked():
                fileName = self.core.convertPath(fileName, target="local")
            else:
                fileName = self.core.convertPath(fileName, target="global")

        hVersion = ""
        pComment = self.le_comment.text()
        if useVersion != "next":
            hVersion = useVersion.split(self.core.filenameSeparator)[0]
            pComment = useVersion.split(self.core.filenameSeparator)[1]

        fnameData = self.core.getScenefileData(fileName)
        if fnameData["entity"] == "shot":
            outputPath = os.path.abspath(
                os.path.join(
                    fileName,
                    os.pardir,
                    os.pardir,
                    os.pardir,
                    os.pardir,
                    "Rendering",
                    "2dRender",
                    self.le_task.text(),
                )
            )
            if hVersion == "":
                hVersion = self.core.getHighestTaskVersion(outputPath)

            outputFile = os.path.join(
                "shot"
                + "_"
                + fnameData["entityName"]
                + "_"
                + self.le_task.text()
                + "_"
                + hVersion
                + extension
            )
        elif fnameData["entity"] == "asset":
            base = self.core.getEntityBasePath(fileName)
            outputPath = os.path.abspath(
                os.path.join(
                    base,
                    "Rendering",
                    "2dRender",
                    self.le_task.text(),
                )
            )
            if hVersion == "":
                hVersion = self.core.getHighestTaskVersion(outputPath)

            outputFile = os.path.join(
                fnameData["entityName"]
                + "_"
                + self.le_task.text()
                + "_"
                + hVersion
                + extension
            )
        else:
            return

        outputPath = os.path.join(outputPath, hVersion)
        if pComment != "":
            outputPath += "_" + pComment

        outputName = os.path.join(outputPath, outputFile)

        return outputName, outputPath, hVersion

    @err_catcher(name=__name__)
    def exportVersionToggled(self, checked):
        self.cb_versions.setEnabled(not checked)
        self.w_comment.setEnabled(checked)

    @err_catcher(name=__name__)
    def validateComment(self, text):
        self.core.validateLineEdit(self.le_comment)

    @err_catcher(name=__name__)
    def saveExport(self):
        if self.rb_task.isChecked():
            taskName = self.le_task.text()
            if taskName is None or taskName == "":
                QMessageBox.warning(
                    self.core.messageParent, "Warning", "Please choose a taskname"
                )
                return

            if not self.core.fileInPipeline():
                QMessageBox.warning(
                    self.core.messageParent,
                    "Warning",
                    "The current file is not inside the Pipeline.\nUse the Project Browser to create a file in the Pipeline.",
                )
                return False

            oversion = "next"
            if not self.chb_useNextVersion.isChecked():
                oversion = self.cb_versions.currentText()

            if oversion is None or oversion == "":
                QMessageBox.warning(
                    self.core.messageParent, "Warning", "Invalid version"
                )
                return

            outputPath, outputDir, hVersion = self.exportGetOutputName(oversion)

            outLength = len(outputPath)
            if platform.system() == "Windows" and outLength > 255:
                msg = "The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, taskname or projectpath." % outLength
                self.core.popup(msg)
                return

            if not os.path.exists(outputDir):
                os.makedirs(outputDir)

            self.core.saveVersionInfo(
                location=os.path.dirname(outputPath),
                version=hVersion,
                origin=self.core.getCurrentFileName(),
            )
        else:
            startLocation = os.path.join(
                self.core.projectPath,
                self.core.getConfig("paths", "assets", configPath=self.core.prismIni),
                "Textures",
            )
            outputPath = QFileDialog.getSaveFileName(
                self.dlg_export,
                "Enter output filename",
                startLocation,
                "JPEG (*.jpg *.jpeg);;PNG (*.png);;TIFF (*.tif *.tiff);;OpenEXR (*.exr)",
            )[0]

            if outputPath == "":
                return

        ext = os.path.splitext(outputPath)[1].lower()

        if self.win:
            bdepth = self.psApp.Application.ActiveDocument.bitsPerChannel
            if ext in [".exr"]:
                if bdepth != 32:
                    QMessageBox.warning(
                        self.core.messageParent,
                        "Export",
                        "To export in this format you need to set the bit depth of your current document to 32.",
                    )
                    return

                descr = win32com.client.dynamic.Dispatch("Photoshop.ActionDescriptor")
                descr.PutString(self.getCharID("As  "), "OpenEXR")
                descr.PutPath(self.getCharID("In  "), outputPath)
                descr.PutBoolean(self.getCharID("LwCs"), True)
                descr.PutBoolean(self.getCharID("Cpy "), True)
                descr.PutEnumerated(
                    self.getStringID("saveStage"),
                    self.getStringID("saveStageType"),
                    self.getStringID("saveSucceeded"),
                )
                self.psApp.ExecuteAction(self.getCharID("save"), descr, 3)
            else:
                if bdepth == 32:
                    QMessageBox.warning(
                        self.core.messageParent,
                        "Export",
                        "To export in this format you need to lower the bit depth of your current document.",
                    )
                    return

                if ext in [".jpg", ".jpeg"]:
                    options = win32com.client.dynamic.Dispatch(
                        "Photoshop.JPEGSaveOptions"
                    )
                elif ext in [".png"]:
                    options = win32com.client.dynamic.Dispatch(
                        "Photoshop.PNGSaveOptions"
                    )
                elif ext in [".tif", ".tiff"]:
                    options = win32com.client.dynamic.Dispatch(
                        "Photoshop.TiffSaveOptions"
                    )

                self.psApp.Application.ActiveDocument.SaveAs(outputPath, options, True)
        else:
            bdScpt = """
                    tell application "%s"
                        bits per channel of current document
                    end tell
                """ % (
                self.psAppName
            )

            bdepth = self.executeAppleScript(bdScpt)

            if ext in [".exr"]:
                if bdepth != "thirty two\n":
                    QMessageBox.warning(
                        self.core.messageParent,
                        "Export",
                        "To export in this format you need to set the bit depth of your current document to 32.",
                    )
                    return

                scpt = """
                    tell application "%s"
                        do javascript "
                            var idsave = charIDToTypeID( 'save' );
                                var desc26 = new ActionDescriptor();
                                var idAs = charIDToTypeID( 'As  ' );
                                    var desc27 = new ActionDescriptor();
                                    var idBtDp = charIDToTypeID( 'BtDp' );
                                    desc27.putInteger( idBtDp, 16 );
                                    var idCmpr = charIDToTypeID( 'Cmpr' );
                                    desc27.putInteger( idCmpr, 4 );
                                    var idAChn = charIDToTypeID( 'AChn' );
                                    desc27.putInteger( idAChn, 0 );
                                var idEXRf = charIDToTypeID( 'EXRf' );
                                desc26.putObject( idAs, idEXRf, desc27 );
                                var idIn = charIDToTypeID( 'In  ' );
                                desc26.putPath( idIn, new File( '%s' ) );
                                var idCpy = charIDToTypeID( 'Cpy ' );
                                desc26.putBoolean( idCpy, true );
                                var idsaveStage = stringIDToTypeID( 'saveStage' );
                                var idsaveStageType = stringIDToTypeID( 'saveStageType' );
                                var idsaveSucceeded = stringIDToTypeID( 'saveSucceeded' );
                                desc26.putEnumerated( idsaveStage, idsaveStageType, idsaveSucceeded );
                            executeAction( idsave, desc26, DialogModes.NO );
                        " show debugger on runtime error
                    end tell
                """ % (
                    self.psAppName,
                    outputPath,
                )
            else:
                if bdepth == "thirty two\n":
                    QMessageBox.warning(
                        self.core.messageParent,
                        "Export",
                        "To export in this format you need to lower the bit depth of your current document.",
                    )
                    return

                if ext in [".jpg", ".jpeg"]:
                    formatName = "JPEG"
                elif ext in [".png"]:
                    formatName = "PNG"
                elif ext in [".tif", ".tiff"]:
                    formatName = "TIFF"

                scpt = """
                    tell application "%s"
                        save current document in file "%s" as %s with copying
                    end tell
                """ % (
                    self.psAppName,
                    outputPath,
                    formatName,
                )
            self.executeAppleScript(scpt)

        self.dlg_export.accept()
        self.core.copyToClipboard(outputPath)
        self.core.callback(name="photoshop_onImageExported", types=[], args=[self, outputPath])

        try:
            self.core.pb.refreshRender()
        except:
            pass

        if os.path.exists(outputPath):
            QMessageBox.information(
                self.core.messageParent,
                "Export",
                "Successfully exported the image.\n(Path is in the clipboard)",
            )
        else:
            QMessageBox.warning(
                self.core.messageParent,
                "Export",
                "Unknown error. Image file doesn't exist:\n\n%s" % outputPath,
            )
