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
import time
import platform
import subprocess

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1

if psVersion == 1:
    import CombineMedia_ui
else:
    import CombineMedia_ui_ps2 as CombineMedia_ui

from PrismUtils.Decorators import err_catcher


class CombineMedia(QDialog, CombineMedia_ui.Ui_dlg_CombineMedia):
    def __init__(self, core, ctype):
        QDialog.__init__(self)
        self.setupUi(self)
        self.core = core
        self.core.parentWindow(self)
        self.ctype = ctype

        dailiesName = self.core.getConfig(
            "paths", "dailies", configPath=self.core.prismIni
        )
        if dailiesName is not None:
            curDate = time.strftime("%Y_%m_%d", time.localtime())
            outputpreset = os.path.join(
                self.core.projectPath,
                dailiesName,
                curDate,
                self.core.getConfig("globals", "username"),
                "combined_video.mp4",
            )
            self.e_output.setText(outputpreset)

        self.e_task.setText("Combined-Video")
        self.taskList = self.core.getTaskNames(
            "external", basePath=self.core.pb.renderBasePath
        )

        if len(self.taskList) == 0:
            self.b_tasks.setHidden(True)

        if self.core.pb.renderBasePath is None:
            self.l_task.setEnabled(False)
            self.chb_task.setChecked(False)
            self.chb_task.setEnabled(False)
            self.e_task.setEnabled(False)

        self.connectEvents()
        self.e_output.setFocus()

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.b_browse.clicked.connect(self.browseCombineOutputFile)
        self.b_browse.customContextMenuRequested.connect(
            lambda: self.core.openFolder(self.e_output.text())
        )

        self.chb_task.toggled.connect(lambda x: self.e_task.setEnabled(x))
        self.chb_task.toggled.connect(lambda x: self.b_tasks.setEnabled(x))
        self.b_tasks.clicked.connect(self.showTasks)
        self.accepted.connect(self.combine)

    @err_catcher(name=__name__)
    def showTasks(self):
        tmenu = QMenu(self)

        for i in self.taskList:
            tAct = QAction(i, self)
            tAct.triggered.connect(lambda x=None, t=i: self.e_task.setText(t))
            tmenu.addAction(tAct)

        tmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def combine(self):
        output = self.e_output.text()

        if not os.path.exists(os.path.dirname(output)):
            try:
                os.makedirs(os.path.dirname(output))
            except:
                QMessageBox.warning(
                    self.core.messageParent,
                    "Video combine",
                    "Could not create outputfolder %s" % os.path.dirname(output),
                )
                return

        ffmpegIsInstalled = False
        if platform.system() == "Windows":
            ffmpegPath = os.path.join(
                self.core.prismLibs, "Tools", "FFmpeg", "bin", "ffmpeg.exe"
            )
            if os.path.exists(ffmpegPath):
                ffmpegIsInstalled = True
        elif platform.system() == "Linux":
            ffmpegPath = "ffmpeg"
            try:
                subprocess.Popen([ffmpegPath])
                ffmpegIsInstalled = True
            except:
                pass
        elif platform.system() == "Darwin":
            ffmpegPath = os.path.join(self.core.prismLibs, "Tools", "ffmpeg")
            if os.path.exists(ffmpegPath):
                ffmpegIsInstalled = True

        if not ffmpegIsInstalled:
            QMessageBox.critical(
                self.core.messageParent,
                "Video combine",
                "Could not find %s" % ffmpegPath,
            )
            return

        if len(self.core.pb.compareStates) > 0:
            cStates = self.core.pb.compareStates
        else:
            cStates = self.core.pb.getCurRenders()[0]

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
                inputpath = self.core.pb.getImgSources(i, getFirstFile=True)
                if len(inputpath) == 0:
                    continue

                inputpath = inputpath[0]

            iw, ih = self.core.pb.getMediaResolution(inputpath)
            if iw == "?" or ih == "?":
                continue

            if iw > tw:
                tw = iw
            if ih > th:
                th = ih

            inputExt = os.path.splitext(inputpath)[1]

            isSequence = not inputExt in [".mp4", ".mov"]

            if isSequence:
                outputpath = os.path.splitext(inputpath)[0][:-(self.core.framePadding+1)] + ".mp4"
                if not os.path.exists(os.path.dirname(outputpath)):
                    os.makedirs(os.path.dirname(outputpath))

                startNum = os.path.splitext(inputpath)[0][-self.core.framePadding:]
                inputpath = os.path.splitext(inputpath)[0][:-self.core.framePadding] + "%04d".replace("4", str(self.core.framePadding)) + inputExt
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

            sources.append([inputpath, iw, ih])

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
            versionBase = os.path.join(
                self.core.pb.renderBasePath, "Rendering", "external", self.e_task.text()
            )
            newVersion = self.core.getHighestTaskVersion(versionBase)
            self.core.pb.createExternalTask(
                data={
                    "taskName": self.e_task.text(),
                    "versionName": newVersion,
                    "targetPath": output,
                }
            )

        for k in tmpFiles:
            try:
                os.remove(k)
            except:
                pass

        if os.path.exists(output):
            self.core.copyToClipboard(output)
            QMessageBox.information(
                self.core.messageParent,
                "Media combine",
                "The video was created successfully. (path is in clipboard)",
            )
        else:
            self.core.ffmpegError(
                "Media combine", "The video could not be created.", [stdout, stderr]
            )

    @err_catcher(name=__name__)
    def browseCombineOutputFile(self):
        path = QFileDialog.getSaveFileName(
            self, "Select Outputfile", self.e_output.text(), "Video (*.mp4)"
        )[0]
        if path != "":
            self.e_output.setText(path)

    @err_catcher(name=__name__)
    def getTasks(self):
        taskList = self.core.getTaskNames(self.taskType)

        if len(self.taskList) == 0:
            self.b_showTasks.setHidden(True)
        else:
            if "_ShotCam" in self.taskList:
                self.taskList.remove("_ShotCam")
