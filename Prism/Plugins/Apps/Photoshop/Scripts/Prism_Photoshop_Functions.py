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
import platform
import subprocess
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

if platform.system() == "Windows":
    import win32com.client
    if sys.version[0] == "3":
        import winreg as _winreg
    else:
        import _winreg

from PrismUtils.Decorators import err_catcher as err_catcher


logger = logging.getLogger(__name__)


class Prism_Photoshop_Functions(object):
    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize Photoshop functions module.
        
        Registers callbacks for save dialogs and Project Browser.
        
        Args:
            core: Prism core instance
            plugin: Plugin instance (self)
        """
        self.core = core
        self.plugin = plugin
        self.win = platform.system() == "Windows"
        self.core.registerCallback("postInitialize", self.postInitialize, plugin=self.plugin)

    @err_catcher(name=__name__)
    def postInitialize(self):
        """Post-initialization callback to set up UI and connections."""
        if self.core.pb:
            self.onProjectBrowserStartup(self.core.pb)

        self.core.registerCallback(
            "onSaveExtendedOpen", self.onSaveExtendedOpen, plugin=self.plugin
        )
        self.core.registerCallback(
            "onGetSaveExtendedDetails", self.onGetSaveExtendedDetails, plugin=self.plugin
        )
        self.core.registerCallback(
            "onProjectBrowserStartup", self.onProjectBrowserStartup, plugin=self.plugin
        )

    @err_catcher(name=__name__)
    def startup(self, origin: Any) -> Optional[bool]:
        """Initialize Photoshop connection and UI.
        
        Connects to running Photoshop instance via COM (Windows) or AppleScript (macOS).
        Configures app icon and style sheet.
        
        Args:
            origin: Origin instance with timer attribute
            
        Returns:
            None on success, implicitly False on connection failure
        """
        origin.timer.stop()
        self.core.setActiveStyleSheet("Photoshop")
        appIcon = QIcon(
            os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "p_tray.png"
            )
        )
        QApplication.instance().setWindowIcon(appIcon)

        if self.win:
            excludes = []
            while True:
                dname = self.getPhotoshopDispatchName(excludes=excludes)
                self.psApp = None
                if dname:
                    try:
                        self.psApp = win32com.client.Dispatch(dname)
                        
                    except:
                        self.psApp = None
                        excludes.append(dname)
                        continue
                    else:
                        try:
                            self.psApp.ActiveDocument
                        except AttributeError:
                            self.psApp = None
                            excludes.append(dname)
                            continue
                        except:
                            pass

                if not self.psApp:
                    msg = "Could not connect to Photoshop."
                    self.core.popup(msg)
                    return

                self.dispatchSuffix = dname.replace("Photoshop.Application", "")
                logger.debug("using %s" % dname)
                break
        else:
            self.psAppName = "Adobe Photoshop CC 2025"
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
            self.executeAppleScript(scpt, getResponse=False)

    @err_catcher(name=__name__)
    def getPhotoshopDispatchName(self, excludes: Optional[List[str]] = None) -> Optional[str]:
        """Get Photoshop COM dispatch name from Windows registry.
        
        Searches for Photoshop.Application or versioned variants like Photoshop.Application.140.
        Uses PRISM_PHOTOSHOP_KEY environment variable if set.
        
        Args:
            excludes: List of dispatch names to skip
            
        Returns:
            COM dispatch name string, or None if not found
        """
        envkey = os.getenv("PRISM_PHOTOSHOP_KEY")
        if envkey:
            return envkey

        name = "Photoshop.Application"
        classBase = "SOFTWARE\\Classes\\"
        try:
            if excludes and name in excludes:
                raise Exception()

            _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                classBase + name,
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )
        except:
            classKey = _winreg.OpenKey(
                _winreg.HKEY_LOCAL_MACHINE,
                classBase,
                0,
                _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY,
            )
            try:
                i = 0
                keyName = None
                while True:
                    classNameKey = _winreg.EnumKey(classKey, i)
                    if sys.version[0] == "2":
                        classNameKey = unicode(classNameKey)

                    if excludes and classNameKey in excludes:
                        i += 1
                        continue

                    if classNameKey.startswith("Photoshop.Application."):
                        if keyName:
                            try:
                                if float(classNameKey.replace("Photoshop.Application.", "")) > float(keyName.replace("Photoshop.Application.", "")):
                                    keyName = classNameKey
                            except:
                                pass
                        else:
                            keyName = classNameKey

                    elif keyName:
                        return keyName

                    i += 1
            except WindowsError:
                pass

        else:
            return name

    @err_catcher(name=__name__)
    def sceneOpen(self, origin: Any) -> None:
        """Callback when scene is opened (no-op for Photoshop).
        
        Args:
            origin: Event origin instance
        """
        pass

    @err_catcher(name=__name__)
    def executeAppleScript(self, script: str, getResponse: bool = True) -> Optional[str]:
        """Execute AppleScript on macOS.
        
        Args:
            script: AppleScript code to execute
            getResponse: If True, wait for and return script output
            
        Returns:
            Script stdout if getResponse=True, None if error or getResponse=False
        """
        logger.debug("running applescript: %s" % script)
        if getResponse:
            p = subprocess.Popen(
                ["osascript"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = p.communicate(script)
            if p.returncode != 0:
                return None

            return stdout
        else:
            subprocess.Popen(["osascript", "-e", script])

    @err_catcher(name=__name__)
    def getCurrentFileName(self, origin: Any, path: bool = True) -> str:
        """Get current Photoshop document filename.
        
        Uses COM (Windows) or AppleScript (macOS) to query active document.
        
        Args:
            origin: Calling instance (unused)
            path: If True, return full path; if False, return basename only
            
        Returns:
            Document file path, or empty string if no document open
        """
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
    def getSceneExtension(self, origin: Any) -> str:
        """Get file extension of current document.
        
        Args:
            origin: Calling instance (unused)
            
        Returns:
            File extension (e.g. '.psd'), or first scene format if no document open
        """
        doc = self.core.getCurrentFileName()
        if doc != "":
            return os.path.splitext(doc)[1]

        return self.sceneFormats[0]

    @err_catcher(name=__name__)
    def onSaveExtendedOpen(self, origin: Any) -> None:
        """Add format selector to Save Extended dialog.
        
        Adds combo box for choosing .psd or .psb format.
        
        Args:
            origin: Save Extended dialog instance
        """
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
    def onGetSaveExtendedDetails(self, origin: Any, details: Dict[str, Any]) -> None:
        """Get file format from Save Extended dialog.
        
        Args:
            origin: Save Extended dialog instance
            details: Dictionary to add 'fileFormat' key to
        """
        details["fileFormat"] = origin.cb_format.currentText()

    @err_catcher(name=__name__)
    def getCharID(self, s: str) -> Any:
        """Convert 4-character string to Photoshop type ID.
        
        Args:
            s: 4-character string (e.g. 'save')
            
        Returns:
            Photoshop type ID
        """
        return self.psApp.CharIDToTypeID(s)

    @err_catcher(name=__name__)
    def getStringID(self, s: str) -> Any:
        """Convert string to Photoshop type ID.
        
        Args:
            s: String identifier (e.g. 'maximizeCompatibility')
            
        Returns:
            Photoshop type ID
        """
        return self.psApp.StringIDToTypeID(s)

    @err_catcher(name=__name__)
    def saveScene(self, origin: Optional[Any], filepath: str, details: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Save current Photoshop document.
        
        Uses COM (Windows) or AppleScript (macOS) to save document.
        Supports .psd and .psb formats with maximize compatibility option.
        
        Args:
            origin: Calling instance (unused)
            filepath: Target file path
            details: Optional dict with 'fileFormat' key to override extension
            
        Returns:
            Empty string on failure, None on success, or False if no active document
        """
        if details is None:
            details = {}
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
        except Exception as e:
            self.core.popup("There is no active document in Photoshop.\n\nError: %s" % str(e))
            return False

        if "fileFormat" in details:
            filepath = os.path.splitext(filepath)[0] + details["fileFormat"]

        try:
            if self.win:
                if os.path.splitext(filepath)[1] == ".psb":
                    desc1 = win32com.client.Dispatch("Photoshop.ActionDescriptor" + self.dispatchSuffix)
                    desc2 = win32com.client.Dispatch("Photoshop.ActionDescriptor" + self.dispatchSuffix)
                    desc2.PutBoolean(self.getStringID("maximizeCompatibility"), True)
                    desc1.PutObject(
                        self.getCharID("As  "), self.getCharID("Pht8"), desc2
                    )
                    desc1.PutPath(self.getCharID("In  "), filepath)
                    desc1.PutBoolean(self.getCharID("LwCs"), True)
                    self.psApp.ExecuteAction(self.getCharID("save"), desc1)
                else:
                    filepath = os.path.normpath(filepath)
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
    def getImportPaths(self, origin: Any) -> bool:
        """Get import paths (not supported in Photoshop).
        
        Args:
            origin: Calling instance
            
        Returns:
            Always False
        """
        return False

    @err_catcher(name=__name__)
    def getFrameRange(self, origin: Any) -> None:
        """Get frame range (not applicable for Photoshop).
        
        Args:
            origin: Calling instance
        """
        pass

    @err_catcher(name=__name__)
    def setFrameRange(self, origin: Any, startFrame: int, endFrame: int) -> None:
        """Set frame range (not applicable for Photoshop).
        
        Args:
            origin: Calling instance
            startFrame: Start frame number
            endFrame: End frame number
        """
        pass

    @err_catcher(name=__name__)
    def getFPS(self, origin: Any) -> None:
        """Get FPS (not applicable for Photoshop).
        
        Args:
            origin: Calling instance
        """
        pass

    @err_catcher(name=__name__)
    def getAppVersion(self, origin: Any) -> Optional[str]:
        """Get Photoshop application version.
        
        Uses COM (Windows) or AppleScript (macOS) to query version.
        
        Args:
            origin: Calling instance (unused)
            
        Returns:
            Version string (e.g. '25.0'), or None on error
        """
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
    def onProjectBrowserStartup(self, origin: Any) -> None:
        """Customize Project Browser on startup.
        
        Disables State Manager and adds Photoshop tools menu.
        
        Args:
            origin: Project Browser instance
        """
        origin.actionStateManager.setEnabled(False)
        psMenu = QMenu("Photoshop", origin)
        psAction = QAction("Open tools", origin)
        psAction.triggered.connect(self.openPhotoshopTools)
        psMenu.addAction(psAction)
        origin.menuTools.addSeparator()
        origin.menuTools.addMenu(psMenu)

    @err_catcher(name=__name__)
    def openScene(self, origin: Any, filepath: str, force: bool = False) -> bool:
        """Open a file in Photoshop.
        
        Uses COM (Windows) or AppleScript (macOS) to open document.
        
        Args:
            origin: Calling instance (unused)
            filepath: Path to file to open
            force: If True, open file regardless of extension
            
        Returns:
            True on success, False if extension not supported and force=False
        """
        if not force and os.path.splitext(filepath)[1] not in self.sceneFormats:
            return False

        if self.win:
            while True:
                try:
                    self.psApp.Open(filepath)
                except Exception as e:
                    msg = "Failed to open file in Photoshop:\n\n%s\n\nError: %s" % (filepath, str(e))
                    result = self.core.popupQuestion(msg, buttons=["Retry", "Cancel"], escapeButton="Cancel", icon=QMessageBox.Warning)
                    if result == "Cancel":
                        return False

                else:
                    break

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
    def importImages(self, filepath: Optional[str] = None, mediaBrowser: Optional[Any] = None, parent: Optional[Any] = None) -> None:
        """Import images into Photoshop.
        
        Opens image file or media from Media Browser.
        
        Args:
            filepath: Path to image file to open
            mediaBrowser: Media Browser instance with selected media
            parent: Parent widget (unused)
        """
        if mediaBrowser:
            self.photoshopImportSource(mediaBrowser)
        elif filepath:
            self.openScene(None, filepath, force=True)

    @err_catcher(name=__name__)
    def photoshopImportSource(self, origin: Any) -> None:
        """Import selected media source from Media Browser.
        
        Args:
            origin: Media Browser instance with seq attribute
        """
        filepath = origin.seq[origin.getCurrentFrame()].replace("\\", "/")
        self.openScene(origin, filepath, force=True)

    @err_catcher(name=__name__)
    def photoshopImportPasses(self, origin: Any) -> None:
        """Import render passes from Media Browser (not implemented).
        
        Args:
            origin: Media Browser instance
        """
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
    def openPhotoshopTools(self) -> bool:
        """Open Prism tools dialog with common actions.
        
        Creates dialog with buttons for Save Version, Save with Comment, Export,
        Project Browser, and Settings.
        
        Returns:
            Always True
        """
        self.dlg_tools = QDialog()

        lo_tools = QVBoxLayout()
        self.dlg_tools.setLayout(lo_tools)

        b_saveVersion = QPushButton("Save Version")
        b_saveComment = QPushButton("Save with Comment")
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
        self.dlg_tools.resize(self.dlg_tools.width()*1.5, self.dlg_tools.height())

        return True

    @err_catcher(name=__name__)
    def exportImage(self) -> Union[bool, None]:
        """Open export dialog for current Photoshop document.
        
        Creates dialog for exporting to Prism project or custom location.
        Supports task-based export with versioning and master version management.
        
        Returns:
            False if preconditions fail (no project/user/document), True/None otherwise
        """
        if not self.core.projects.ensureProject():
            return False

        if not self.core.users.ensureUser():
            return False

        curfile = self.core.getCurrentFileName()
        filepath = curfile.replace("\\", "/")
        if not filepath:
            self.core.showFileNotInProjectWarning()
            return False

        curfile = self.core.getCurrentFileName()
        fname = self.core.getScenefileData(curfile)

        if "type" in fname:
            entityType = fname["type"]
        else:
            entityType = "context"

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
        l_task = QLabel("Identifier:")
        l_task.setMinimumWidth(110)
        self.le_task = QLineEdit()
        self.le_task.setText(fname.get("task", ""))
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
        self.cb_formats.addItems([".jpg", ".png", ".tif", ".exr", ".psd"])
        self.w_location = QWidget()
        self.lo_location = QHBoxLayout()
        self.lo_location.setContentsMargins(0, 0, 0, 0)
        self.w_location.setLayout(self.lo_location)
        self.l_location = QLabel("Location:")
        self.l_location.setMinimumWidth(140)
        self.cb_location = QComboBox()
        self.export_paths = self.core.paths.getRenderProductBasePaths()
        self.cb_location.addItems(list(self.export_paths.keys()))
        self.lo_location.addWidget(self.l_location)
        self.lo_location.addWidget(self.cb_location)
        if len(self.export_paths) < 2:
            self.w_location.setVisible(False)

        self.w_master = QWidget()
        self.lo_master = QHBoxLayout()
        self.lo_master.setContentsMargins(0, 0, 0, 0)
        self.w_master.setLayout(self.lo_master)
        self.l_master = QLabel("Master Version:")
        self.l_master.setMinimumWidth(140)
        self.cb_master = QComboBox()
        self.export_paths = self.core.paths.getRenderProductBasePaths()
        self.lo_master.addWidget(self.l_master)
        self.lo_master.addWidget(self.cb_master)

        masterItems = ["Set as master", "Add to master", "Don't update master"]
        self.cb_master.addItems(masterItems)

        if not self.core.mediaProducts.getUseMaster():
            self.w_master.setVisible(False)

        lo_task.addWidget(l_task)
        lo_task.addWidget(self.le_task)
        lo_task.addWidget(self.b_task)
        lo_comment.addWidget(l_comment)
        lo_comment.addWidget(self.le_comment)
        lo_version.addWidget(self.chb_useNextVersion)
        lo_version.addWidget(self.cb_versions)
        lo_extension.addWidget(l_ext)
        lo_extension.addWidget(self.cb_formats)
        lo_localOut.addWidget(self.w_location)
        lo_prismExport.addLayout(lo_task)
        lo_prismExport.addWidget(self.w_comment)
        lo_prismExport.addLayout(lo_version)
        lo_prismExport.addLayout(lo_extension)
        lo_prismExport.addWidget(self.w_master)
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

        self.exportGetTasks()
        self.core.callback(
            name="photoshop_onExportOpen",
            args=[self],
        )

        self.dlg_export.show()

        self.cb_versions.setMinimumWidth(300)
        self.cb_formats.setMinimumWidth(300)

        return True

    @err_catcher(name=__name__)
    def exportToggle(self, checked: bool) -> None:
        """Toggle task export UI enabled state.
        
        Args:
            checked: Whether task export radio button is checked
        """
        self.w_task.setEnabled(checked)

    @err_catcher(name=__name__)
    def exportGetTasks(self) -> None:
        """Populate task list from project configuration.
        
        Gets 2d task names and hides task button if no tasks available.
        """
        self.taskList = self.core.getTaskNames("2d")

        if len(self.taskList) == 0:
            self.b_task.setHidden(True)
        else:
            if "_ShotCam" in self.taskList:
                self.taskList.remove("_ShotCam")

    @err_catcher(name=__name__)
    def exportShowTasks(self) -> None:
        """Show task selection menu.
        
        Displays context menu with available 2d tasks.
        """
        tmenu = QMenu(self.dlg_export)

        for i in sorted(self.taskList, key=lambda x: x.lower()):
            tAct = QAction(i, self.dlg_export)
            tAct.triggered.connect(lambda x=None, t=i: self.le_task.setText(t))
            tAct.triggered.connect(self.exportGetVersions)
            tmenu.addAction(tAct)

        tmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def exportGetVersions(self) -> None:
        """Populate version combo box with existing versions for current task.
        
        Scans output directory for existing version folders (vXXXX).
        """
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
    def exportGetOutputName(self, useVersion: str = "next") -> Optional[Tuple[str, str, str]]:
        """Generate output path for export.
        
        Creates versioned output path based on current scene, task, and format.
        
        Args:
            useVersion: Version to use ('next' for auto-increment, or specific version string)
            
        Returns:
            Tuple of (output_path, output_folder, version_string), or None if invalid
        """
        if self.le_task.text() == "":
            return

        task = self.le_task.text()
        extension = self.cb_formats.currentText()
        fileName = self.core.getCurrentFileName()
        fnameData = self.core.getScenefileData(fileName)

        if "type" not in fnameData:
            return

        location = self.cb_location.currentText()
        outputPathData = self.core.mediaProducts.generateMediaProductPath(
            entity=fnameData,
            task=task,
            extension=extension,
            comment=fnameData.get("comment", ""),
            framePadding="",
            version=useVersion if useVersion != "next" else None,
            location=location,
            returnDetails=True,
            mediaType="2drenders",
        )

        outputFolder = os.path.dirname(outputPathData["path"])
        hVersion = outputPathData["version"]

        return outputPathData["path"], outputFolder, hVersion

    @err_catcher(name=__name__)
    def exportVersionToggled(self, checked: bool) -> None:
        """Handle version checkbox toggle.
        
        Args:
            checked: Whether 'Use next version' is checked
        """
        self.cb_versions.setEnabled(not checked)
        self.w_comment.setEnabled(checked)

    @err_catcher(name=__name__)
    def validateComment(self, text: str) -> None:
        """Validate comment text field.
        
        Args:
            text: Comment text to validate
        """
        self.core.validateLineEdit(self.le_comment)

    @err_catcher(name=__name__)
    def saveExport(self) -> Optional[bool]:
        """Save/export current document to selected location.
        
        Handles both task-based export (into project structure) and custom location export.
        Creates version info file and updates master version if enabled.
        
        Returns:
            False if validation fails, None otherwise
        """
        if self.rb_task.isChecked():
            taskName = self.le_task.text()
            if taskName is None or taskName == "":
                QMessageBox.warning(
                    self.core.messageParent, "Warning", "Please choose an identifier"
                )
                return

            if not self.core.fileInPipeline():
                self.core.showFileNotInProjectWarning(title="Warning")
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
            if platform.system() == "Windows" and os.getenv("PRISM_IGNORE_PATH_LENGTH") != "1" and outLength > 255:
                msg = (
                    "The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, identifier or projectpath."
                    % outLength
                )
                self.core.popup(msg)
                return

            if not os.path.exists(outputDir):
                os.makedirs(outputDir)

            fileName = self.core.getCurrentFileName()
            context = self.core.getScenefileData(fileName)

            details = context.copy()
            if "filename" in details:
                del details["filename"]

            if "extension" in details:
                del details["extension"]

            details["version"] = hVersion
            details["sourceScene"] = fileName
            details["identifier"] = self.le_task.text()

            self.core.saveVersionInfo(
                filepath=os.path.dirname(outputPath),
                details=details,
            )
        else:
            startLocation = self.core.projects.getResolvedProjectStructurePath("textures")
            outputPath = QFileDialog.getSaveFileName(
                self.dlg_export,
                "Enter output filename",
                startLocation,
                "JPEG (*.jpg *.jpeg);;PNG (*.png);;TIFF (*.tif *.tiff);;OpenEXR (*.exr);;Photoshop (*.psd)",
            )[0]

            if outputPath == "":
                return

        self.exportImageToPath(outputPath)
        self.handleMasterVersion(outputPath)
        self.dlg_export.accept()
        if os.getenv("PRISM_COPY_FILE_CONTENT", "0") == "1":
            self.core.copyToClipboard(outputPath, file=True)
        else:
            self.core.copyToClipboard(outputPath, file=False)

        self.core.callback(name="photoshop_onImageExported", args=[self, outputPath])

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

    @err_catcher(name=__name__)
    def _isRpcUnavailableError(self, err: Exception) -> bool:
        """Return True when COM error indicates lost Photoshop RPC connection."""
        if not self.win:
            return False

        msg = str(err).lower()
        return (
            "rpc server is unavailable" in msg
            or "-2147023174" in msg
            or "application is busy" in msg
            or "-2147417846" in msg
        )

    @err_catcher(name=__name__)
    def _reconnectPhotoshop(self) -> bool:
        """Try to reconnect to Photoshop COM and refresh dispatch metadata."""
        if not self.win:
            return False

        dname = self.getPhotoshopDispatchName()
        if not dname:
            self.psApp = None
            return False

        self.psApp = win32com.client.Dispatch(dname)
        self.dispatchSuffix = dname.replace("Photoshop.Application", "")
        return True

    @err_catcher(name=__name__)
    def getBitsPerChannel(self) -> Any:
        """Get bit depth of current Photoshop document.
        
        Uses COM (Windows) or AppleScript (macOS) to query bit depth.
        
        Returns:
            Bit depth value (8, 16, 32 on Windows; string on macOS)
        """
        if self.win:
            try:
                bdepth = self.psApp.Application.ActiveDocument.bitsPerChannel
            except Exception as e:
                if not self._isRpcUnavailableError(e):
                    raise

                isBusy = "application is busy" in str(e).lower() or "-2147417846" in str(e)
                logger.warning("Photoshop COM connection lost while querying bit depth. Trying reconnect...")
                self.psApp = None
                try:
                    if self._reconnectPhotoshop():
                        bdepth = self.psApp.Application.ActiveDocument.bitsPerChannel
                    else:
                        bdepth = None
                except Exception:
                    bdepth = None

                if bdepth is None:
                    if isBusy:
                        msg = "Photoshop is busy. Please wait until Photoshop has finished its current operation and try again."
                    else:
                        msg = "Lost connection to Photoshop. Please make sure Photoshop is running and a document is open, then retry."

                    self.core.popup(msg, title="Prism")
                    return
        else:
            scpt = (
                """
            tell application "%s"
                bits per channel of current document
            end tell
            """
                % self.psAppName
            )
            bdepth = self.executeAppleScript(scpt)

        return bdepth

    @err_catcher(name=__name__)
    def exportImageToPath(self, outputPath: str) -> Optional[bool]:
        """Export current Photoshop document to specified path.
        
        Handles format-specific export operations:
        - .exr: OpenEXR format (requires 32-bit depth)
        - .psd: Copy current file
        - .jpg/.png/.tif: Standard image formats via SaveAs or AppleScript
        
        Uses COM (Windows) or AppleScript (macOS) for export operations.
        
        Args:
            outputPath: Target file path with extension
            
        Returns:
            None on success, False/None on error
        """
        ext = os.path.splitext(outputPath)[1].lower()
        bdepth = self.getBitsPerChannel()
        if self.win:
            if ext in [".exr"]:
                if bdepth != 32:
                    msg = "To export in this format you need to set the bit depth of your current document to 32."
                    self.core.popup(msg, title="Prism Export")
                    return

                descr = win32com.client.dynamic.Dispatch("Photoshop.ActionDescriptor" + self.dispatchSuffix)
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
            elif ext in [".psd"]:
                curFileName = self.core.getCurrentFileName()
                self.core.copySceneFile(curFileName, outputPath)
            else:
                if bdepth == 32:
                    msg = "To export in this format you need to lower the bit depth of your current document."
                    result = self.core.popupQuestion(msg, buttons=["Lower bit depth and continue", "Cancel"], icon=QMessageBox.Warning)
                    if result != "Lower bit depth and continue":
                        return

                    self.psApp.Application.ActiveDocument.bitsPerChannel = 16

                if ext in [".jpg", ".jpeg"]:
                    options = win32com.client.Dispatch(
                        "Photoshop.JPEGSaveOptions" + self.dispatchSuffix
                    )
                    options.quality = 10
                elif ext in [".png"]:
                    options = win32com.client.Dispatch(
                        "Photoshop.PNGSaveOptions" + self.dispatchSuffix
                    )
                elif ext in [".tif", ".tiff"]:
                    options = win32com.client.Dispatch(
                        "Photoshop.TiffSaveOptions" + self.dispatchSuffix
                    )

                self.psApp.Application.ActiveDocument.SaveAs(outputPath, options, True)

        else:
            if ext in [".exr"]:
                if bdepth != "thirty two\n":
                    msg = "To export in this format you need to set the bit depth of your current document to 32."
                    self.core.popup(msg, title="Prism Export")
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
            elif ext in [".psd"]:
                curFileName = self.core.getCurrentFileName()
                self.core.copySceneFile(curFileName, outputPath)
            else:
                if bdepth == "thirty two\n":
                    msg = "To export in this format you need to lower the bit depth of your current document."
                    self.core.popup(msg, title="Prism Export")
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

    @err_catcher(name=__name__)
    def isUsingMasterVersion(self) -> bool:
        """Check if master version should be updated.
        
        Returns:
            True if master versioning is enabled and action is not 'Don't update master'
        """
        useMaster = self.core.mediaProducts.getUseMaster()
        if not useMaster:
            return False

        masterAction = self.cb_master.currentText()
        if masterAction == "Don't update master":
            return False

        return True

    @err_catcher(name=__name__)
    def handleMasterVersion(self, outputName: str) -> None:
        """Update master version based on selected action.
        
        Args:
            outputName: Path to exported file
        """
        if not self.isUsingMasterVersion():
            return

        masterAction = self.cb_master.currentText()
        if masterAction == "Set as master":
            self.core.mediaProducts.updateMasterVersion(outputName, mediaType="2drenders")
        elif masterAction == "Add to master":
            self.core.mediaProducts.addToMasterVersion(outputName, mediaType="2drenders")

    @err_catcher(name=__name__)
    def captureViewportThumbnail(self) -> Optional[Any]:
        """Capture thumbnail of current Photoshop document.
        
        Exports document to temporary JPG and loads as QPixmap.
        
        Returns:
            QPixmap of document, or None on error
        """
        import tempfile
        path = tempfile.NamedTemporaryFile(suffix=".jpg").name
        self.exportImageToPath(path.replace("\\", "/"))
        pm = self.core.media.getPixmapFromPath(path)
        try:
            os.remove(path)
        except:
            pass

        return pm
