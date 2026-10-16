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
import subprocess
from typing import Any, Optional, List, Dict, Tuple

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

import CombineMedia_ui

from PrismUtils.Decorators import err_catcher


class CombineMedia(QDialog, CombineMedia_ui.Ui_dlg_CombineMedia):
    """Dialog for combining multiple media files into a single video output.
    
    This class provides functionality to combine multiple renders or media sources
    into a single video file using FFmpeg. Supports different combination types
    including layout, sequence, stack, and stack difference modes.
    
    Attributes:
        core: The Prism core instance
        ctype: Combination type ("layout", "sequence", "stack", or "stackDif")
        taskList: List of available task names for the current context
    """
    
    def __init__(self, core: Any, ctype: str) -> None:
        """Initialize the CombineMedia dialog.
        
        Args:
            core: The Prism core instance providing access to pipeline functionality
            ctype: Type of media combination to perform ("layout", "sequence", "stack", "stackDif")
        """
        QDialog.__init__(self)
        self.setupUi(self)
        self.core = core
        self.core.parentWindow(self)
        self.ctype = ctype

        self.e_task.setText("Combined-Video")
        context = self.core.pb.mediaBrowser.getCurrentEntity()
        self.taskList = self.core.getTaskNames("external", context=context)

        if len(self.taskList) == 0:
            self.b_tasks.setHidden(True)

        if not context:
            self.l_task.setEnabled(False)
            self.chb_task.setChecked(False)
            self.chb_task.setEnabled(False)
            self.e_task.setEnabled(False)

        self.connectEvents()
        self.e_output.setFocus()

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect UI signals to their respective slot methods.
        
        Connects button clicks, checkbox states, and dialog acceptance to
        their corresponding handler methods.
        """
        self.b_browse.clicked.connect(self.browseCombineOutputFile)
        self.b_browse.customContextMenuRequested.connect(
            lambda: self.core.openFolder(self.e_output.text())
        )

        self.chb_task.toggled.connect(lambda x: self.e_task.setEnabled(x))
        self.chb_task.toggled.connect(lambda x: self.b_tasks.setEnabled(x))
        self.b_tasks.clicked.connect(self.showTasks)
        self.accepted.connect(self.combine)

    @err_catcher(name=__name__)
    def showTasks(self) -> None:
        """Display a context menu with available task names.
        
        Creates and shows a popup menu containing all tasks from the task list,
        allowing the user to select a task name for the combined output.
        """
        tmenu = QMenu(self)

        for i in self.taskList:
            tAct = QAction(i, self)
            tAct.triggered.connect(lambda x=None, t=i: self.e_task.setText(t))
            tmenu.addAction(tAct)

        tmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def combine(self) -> None:
        """Combine multiple media sources into a single output video.
        
        Processes all selected media renders/sources through FFmpeg to create
        a combined video output. Handles:
        - Image sequence to video conversion
        - Resolution normalization and padding
        - Video concatenation for sequence mode
        - Optional media product creation in project structure
        
        The method:
        1. Validates output path and FFmpeg availability
        2. Converts image sequences to video if needed
        3. Normalizes all inputs to same resolution with padding
        4. Combines videos based on combination type (sequence, layout, etc.)
        5. Optionally creates a new version in the project structure
        6. Cleans up temporary files
        """
        output = self.e_output.text()

        if not os.path.exists(os.path.dirname(output)):
            try:
                os.makedirs(os.path.dirname(output))
            except:
                msg = "Could not create outputfolder %s" % os.path.dirname(output)
                self.core.popup(msg)
                return

        ffmpegPath = self.core.media.getFFmpeg(validate=True)
        if not ffmpegPath:
            self.core.popup(
                "Could not find %s" % ffmpegPath,
            )
            return

        if self.core.pb.mediaBrowser.compareStates:
            cStates = self.core.pb.mediaBrowser.compareStates
        else:
            cStates = self.core.pb.mediaBrowser.getCurRenders()

        if self.ctype in ["layout", "sequence"]:
            cStates = reversed(cStates)

        tmpFiles = []
        sources = []
        combineInputs = []
        tw = th = 0
        stdout = ""
        stderr = ""

        for i in cStates:
            if os.path.isfile(i):
                inputpath = i
            else:
                inputpath = self.core.pb.mediaBrowser.getImgSources(
                    i, getFirstFile=True
                )
                if len(inputpath) == 0:
                    continue

                inputpath = inputpath[0]

            resolution = self.core.media.getMediaResolution(inputpath)
            inWidth = resolution["width"]
            inHeight = resolution["height"]
            if inWidth is None or inHeight is None:
                continue

            if inWidth > tw:
                tw = inWidth
            if inHeight > th:
                th = inHeight

            inputExt = os.path.splitext(inputpath)[1]

            isSequence = inputExt not in self.core.media.videoFormats

            if isSequence:
                outputpath = (
                    os.path.splitext(inputpath)[0][: -(self.core.framePadding + 1)]
                    + ".mp4"
                )
                if not os.path.exists(os.path.dirname(outputpath)):
                    os.makedirs(os.path.dirname(outputpath))

                startNum = os.path.splitext(inputpath)[0][-self.core.framePadding :]
                inputpath = (
                    os.path.splitext(inputpath)[0][: -self.core.framePadding]
                    + "%04d".replace("4", str(self.core.framePadding))
                    + inputExt
                )
                nProc = subprocess.Popen(
                    [
                        ffmpegPath,
                        "-start_number",
                        startNum,
                        "-framerate",
                        "24",
                        "-apply_trc",
                        "iec61966_2_1",
                        "-i",
                        inputpath,
                        "-pix_fmt",
                        "yuva420p",
                        "-start_number",
                        startNum,
                        outputpath,
                        "-y",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                result = nProc.communicate()
                stdout += str(result[0])
                stderr += str(result[1])
                if not os.path.exists(outputpath) or os.stat(outputpath).st_size == 0:
                    continue

                tmpFiles.append(outputpath)
                inputpath = outputpath

            sources.append([inputpath, inWidth, inHeight])

        for i in sources:
            inputpath = i[0]

            outputpath = os.path.splitext(inputpath)[0] + "_converted.mp4"
            outputpathts = os.path.splitext(inputpath)[0] + "_converted.ts"

            iw = i[1]
            ih = i[2]

            newW = iw * min(tw / iw, th / ih)
            newH = ih * min(tw / iw, th / ih)

            pad = "%s:%s:%s:%s" % (
                tw,
                th,
                (tw - iw * min(tw / iw, th / ih)) / 2,
                (th - ih * min(tw / iw, th / ih)) / 2,
            )

            nProc = subprocess.Popen(
                [
                    ffmpegPath,
                    "-i",
                    inputpath,
                    "-pix_fmt",
                    "yuv420p",
                    "-vf",
                    "scale=%s:%s, pad=%s" % (newW, newH, pad),
                    outputpath,
                    "-y",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            result = nProc.communicate()
            stdout += str(result[0])
            stderr += str(result[1])
            nProc = subprocess.Popen(
                [
                    ffmpegPath,
                    "-i",
                    outputpath,
                    "-pix_fmt",
                    "yuv420p",
                    "-c",
                    "copy",
                    "-bsf:v",
                    "h264_mp4toannexb",
                    outputpathts,
                    "-y",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            result = nProc.communicate()
            stdout += str(result[0])
            stderr += str(result[1])

            tmpFiles.append(outputpath)
            tmpFiles.append(outputpathts)

            if os.path.exists(outputpathts):
                combineInputs.append(outputpathts)

        if self.ctype == "sequence":
            args = [ffmpegPath]
            filterStr = ""
            for idx, i in enumerate(combineInputs):
                args += ["-i", i]
                filterStr += "[%s:0]" % idx
            args += ["-filter_complex"]
            filterStr += "concat=n=%s:v=1:a=0 [v]" % len(combineInputs)
            args += [filterStr, "-map", "[v]", "-pix_fmt", "yuv420p", output, "-y"]
            nProc = subprocess.call(args)
        # 	elif self.ctype == "layout":
        # 	elif self.ctype == "stack":
        # 	elif self.ctype == "stackDif":

        if self.chb_task.isChecked() and self.e_task.text() != "":
            context = self.core.pb.mediaBrowser.getCurrentEntity()
            context["identifier"] = self.e_task.text()
            version = self.core.mediaProducts.getLatestVersionFromIdentifier(context)
            if version:
                intVersion = self.core.products.getIntVersionFromVersionName(
                    version["version"]
                )
            else:
                intVersion = 1
            newVersion = self.core.versionFormat % (intVersion + 1)
            self.core.mediaProducts.createExternalMedia(
                output, context, context["identifier"], newVersion
            )

        for k in tmpFiles:
            try:
                os.remove(k)
            except:
                pass

        if os.path.exists(output):
            self.core.copyToClipboard(output, file=True)
            msg = "The video was created successfully. (path is in clipboard)"
            self.core.popup(msg, severity="info")
        else:
            self.core.ffmpegError(
                "Media combine", "The video could not be created.", [stdout, stderr]
            )

    @err_catcher(name=__name__)
    def browseCombineOutputFile(self) -> None:
        """Open file browser dialog to select the output file path.
        
        Displays a save file dialog for the user to select where the combined
        video should be saved. Updates the output path field with the selection.
        """
        path = QFileDialog.getSaveFileName(
            self, "Select Outputfile", self.e_output.text(), "Video (*.mp4)"
        )[0]
        if path != "":
            self.e_output.setText(path)

    @err_catcher(name=__name__)
    def getTasks(self) -> None:
        """Retrieve and filter the task list for the current context.
        
        Gets task names based on the task type and filters out special tasks
        like "_ShotCam". Hides the tasks button if no tasks are available.
        """
        taskList = self.core.getTaskNames(self.taskType)

        if len(self.taskList) == 0:
            self.b_showTasks.setHidden(True)
        else:
            camProduct = self.core.products.getShotcamProductName()
            if camProduct in self.taskList:
                self.taskList.remove(camProduct)
