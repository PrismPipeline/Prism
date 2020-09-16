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
import traceback
import subprocess
import datetime
import platform
import imp

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1

sys.path.append(os.path.join(os.path.dirname(__file__), "UserInterfaces"))
if psVersion == 1:
    import ShotgunPublish_ui
else:
    import ShotgunPublish_ui_ps2 as ShotgunPublish_ui

try:
    import CreateItem
except:
    modPath = imp.find_module("CreateItem")[1]
    if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
        os.remove(modPath)
    import CreateItem

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class sgPublish(QDialog, ShotgunPublish_ui.Ui_dlg_sgPublish):
    def __init__(
        self, core, origin, ptype, shotName, task, version, sources, startFrame
    ):
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.core.parentWindow(self)
        self.ptype = ptype
        self.shotName = shotName
        self.taskVersion = version
        self.fileSources = sources
        self.startFrame = startFrame
        self.shotList = {}

        sgData = origin.connectToShotgun()

        if sgData[0] is None or sgData[1] is None:
            return

        self.sg, self.sgPrjId, self.sgUserId = sgData

        self.core.appPlugin.shotgunPublish_startup(self)

        for i in range(7):
            self.cb_playlist.addItem(
                "DAILIES_%s" % (datetime.date.today() + datetime.timedelta(days=i))
            )

        if ptype == "Asset":
            self.rb_asset.setChecked(True)
        else:
            self.rb_shot.setChecked(True)

        self.updateShots()
        self.navigateToCurrent(shotName, task)

        if self.core.appPlugin.pluginName == "Houdini" and hasattr(
            self.core.appPlugin, "fixStyleSheet"
        ):
            self.core.appPlugin.fixStyleSheet(self.gb_playlist)

        self.connectEvents()

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.rb_asset.pressed.connect(self.updateShots)
        self.rb_shot.pressed.connect(self.updateShots)
        # 	self.b_addTask.clicked.connect(self.createTask)
        self.b_addTask.setVisible(False)
        self.cb_shot.activated.connect(self.updateTasks)
        self.b_sgPublish.clicked.connect(self.publish)

    @err_catcher(name=__name__)
    def updateShots(self):
        fields = ["id", "code", "type", "sg_sequence", "sg_localhierarchy"]
        filters = [["project", "is", {"type": "Project", "id": self.sgPrjId}]]

        if self.rb_asset.isDown():
            self.ptype = "Asset"
        elif self.rb_shot.isDown():
            self.ptype = "Shot"

        self.sgShots = self.sg.find(self.ptype, filters, fields)

        self.cb_shot.clear()
        self.shotList = {}
        for x in self.sgShots:
            if "sg_sequence" in x and x["sg_sequence"] is not None:
                x["code"] = "%s%s%s" % (
                    x["sg_sequence"]["name"],
                    self.core.sequenceSeparator,
                    x["code"],
                )

            if "sg_localhierarchy" in x and x["sg_localhierarchy"] is not None:
                self.shotList[x["code"]] = x["sg_localhierarchy"]
            else:
                self.shotList[x["code"]] = x["code"]

        self.cb_shot.addItems(sorted(self.shotList.keys(), key=lambda s: s.lower()))
        self.updateTasks()

    @err_catcher(name=__name__)
    def updateTasks(self, idx=None):
        self.cb_task.clear()
        if self.cb_shot.currentText() == "":
            QMessageBox.warning(
                self.core.messageParent,
                "Shotgun Publish",
                "No %s exists in the Shotgun project." % self.ptype,
            )
            return

        fields = ["id", "content", "type"]

        if self.ptype == "Asset":
            filters = [
                ["project", "is", {"type": "Project", "id": self.sgPrjId}],
                ["entity.%s.code" % self.ptype, "is", self.cb_shot.currentText()],
            ]
        elif self.ptype == "Shot":
            shotName, seqName = self.core.entities.splitShotname(self.cb_shot.currentText())
            if seqName == "no sequence":
                seqName = ""

            filters = [
                ["project", "is", {"type": "Project", "id": self.sgPrjId}],
                ["code", "is", seqName],
            ]

            seq = self.sg.find_one("Sequence", filters)

            filters = [
                ["project", "is", {"type": "Project", "id": self.sgPrjId}],
                ["entity.%s.code" % self.ptype, "is", shotName],
                ["entity.%s.sg_sequence" % self.ptype, "is", seq],
            ]

        self.sgTasks = self.sg.find("Task", filters, fields)

        sgTaskNames = [x["content"] for x in self.sgTasks]
        sgTaskNames = list(set(sgTaskNames))

        taskPaths = [""]
        if self.ptype == "Asset":
            assetPath = self.core.getAssetPath()
            taskPaths.append(
                os.path.join(
                    assetPath,
                    self.shotList[self.cb_shot.currentText()],
                    "Rendering",
                    "3dRender",
                )
            )
            taskPaths.append(
                os.path.join(
                    assetPath,
                    self.shotList[self.cb_shot.currentText()],
                    "Rendering",
                    "2dRender",
                )
            )
            taskPaths.append(
                os.path.join(
                    assetPath,
                    self.shotList[self.cb_shot.currentText()],
                    "Rendering",
                    "external",
                )
            )
            taskPaths.append(
                os.path.join(
                    assetPath,
                    self.shotList[self.cb_shot.currentText()],
                    "Playblasts",
                )
            )
        elif self.ptype == "Shot":
            shotPath = self.core.getShotPath()
            taskPaths.append(
                os.path.join(
                    shotPath, self.cb_shot.currentText(), "Rendering", "3dRender"
                )
            )
            taskPaths.append(
                os.path.join(
                    shotPath, self.cb_shot.currentText(), "Rendering", "2dRender"
                )
            )
            taskPaths.append(
                os.path.join(
                    shotPath, self.cb_shot.currentText(), "Rendering", "external"
                )
            )
            taskPaths.append(
                os.path.join(shotPath, self.cb_shot.currentText(), "Playblasts")
            )

        taskNames = []
        for i in taskPaths:
            if os.path.exists(i):
                taskNames += os.listdir(i)

        taskNames = list(set(taskNames))
        # 	taskNames = [x for x in taskNames if x not in sgTaskNames]

        self.cb_task.addItems(sgTaskNames)
        if len(sgTaskNames) > 0 and len(taskNames) > 0:
            self.cb_task.insertSeparator(len(sgTaskNames))
        self.cb_task.addItems(taskNames)

    # 	@err_catcher(name=__name__)
    # 	def createTask(self):
    # 		self.newItem = CreateItem.CreateItem(core=self.core)
    #
    # 		self.newItem.setModal(True)
    # 		self.core.parentWindow(self.newItem)
    # 		self.newItem.e_item.setFocus()
    # 		self.newItem.setWindowTitle("Create " + self.ptype)
    # 		self.newItem.l_item.setText(self.ptype + " Name:")
    # 		res = self.newItem.exec_()
    #
    # 		if res == 1:
    # 			data = { 'project': {'type': 'Project','id': self.sgPrjId},
    # 				'content': self.newItem.e_item.text(),
    # 				'sg_status_list': 'ip',
    # 				'entity' : {'type': self.ptype, 'id': curShotId}
    # 			}
    # 			result = self.sg.create('Task', data)

    @err_catcher(name=__name__)
    def navigateToCurrent(self, shotName, task):
        idx = self.cb_shot.findText(shotName)
        if idx != -1:
            self.cb_shot.setCurrentIndex(idx)

        self.updateTasks()

        idx = self.cb_task.findText(task)
        if idx != -1:
            self.cb_task.setCurrentIndex(idx)

    @err_catcher(name=__name__)
    def enterEvent(self, event):
        QApplication.restoreOverrideCursor()

    @err_catcher(name=__name__)
    def publish(self):
        if self.cb_shot.currentText() == "":
            QMessageBox.warning(
                self.core.messageParent,
                "Shotgun Publish",
                "No %s exists in the Shotgun project. Publish canceled" % self.ptype,
            )
            return

        if self.cb_task.currentText() == "":
            QMessageBox.warning(
                self.core.messageParent,
                "Shotgun Publish",
                "No task is selected. Publish canceled.",
            )
            return

        curShotId = [
            x["id"] for x in self.sgShots if x["code"] == self.cb_shot.currentText()
        ][0]
        curTaskId = [
            x["id"] for x in self.sgTasks if x["content"] == self.cb_task.currentText()
        ]

        if len(curTaskId) > 0:
            curTaskId = curTaskId[0]
        else:
            fields = ["code", "short_name", "entity_type"]
            # 	sgSteps = { x['short_name'] : x for x in self.sg.find("Step", [], fields) if x['entity_type'] is not None}
            data = {
                "project": {"type": "Project", "id": self.sgPrjId},
                "content": self.cb_task.currentText(),
                "sg_status_list": "ip",
                "entity": {"type": self.ptype, "id": curShotId}
                # 	'step' : {'type': 'Step', 'id': sgSteps["ren"]['id'] }
            }
            try:
                result = self.sg.create("Task", data)
            except Exception as e:
                if "Entity of type Task cannot be created by this user." in str(e):
                    QMessageBox.warning(
                        self.core.messageParent,
                        "Warning",
                        "This shotgun account cannot create tasks.\n\nPublish canceled.",
                    )
                    return
                else:
                    raise e
            curTaskId = result["id"]

        pubVersions = []
        for source in self.fileSources:
            versionName = "%s_%s_%s" % (
                self.cb_shot.currentText(),
                self.cb_task.currentText(),
                self.taskVersion,
            )
            if len(self.fileSources) > 1:
                versionName += "_%s" % os.path.splitext(os.path.basename(source[0]))[0]
            baseName, extension = os.path.splitext(source[0])

            videoInput = extension in [".mp4", ".mov"]
            if videoInput:
                sequenceName = source[0]
            else:
                try:
                    int(baseName[-4:])
                    sequenceName = baseName[:-4] + "####" + extension
                except:
                    sequenceName = source[0]

            tmpFiles = []

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

            imgPath = source[0]
            if extension in [".exr", ".mp4", ".mov"]:
                inputpath = source[0].replace("\\", "/")
                outputpath = os.path.splitext(inputpath)[0] + ".jpg"
                if ffmpegIsInstalled:
                    if videoInput:
                        nProc = subprocess.Popen(
                            [
                                ffmpegPath,
                                "-apply_trc",
                                "iec61966_2_1",
                                "-i",
                                inputpath,
                                "-pix_fmt",
                                "yuv420p",
                                "-vf",
                                "select=gte(n\,%s)" % source[1],
                                "-frames",
                                "1",
                                outputpath,
                                "-y",
                            ]
                        )
                    else:
                        nProc = subprocess.Popen(
                            [
                                ffmpegPath,
                                "-apply_trc",
                                "iec61966_2_1",
                                "-i",
                                inputpath,
                                "-pix_fmt",
                                "yuv420p",
                                outputpath,
                                "-y",
                            ]
                        )

                    result = nProc.communicate()
                    imgPath = outputpath
                    tmpFiles.append(imgPath)

            data = {
                "project": {"type": "Project", "id": self.sgPrjId},
                "code": versionName,
                "description": self.te_description.toPlainText(),
                "sg_path_to_frames": sequenceName,
                "sg_status_list": "rev",
                "entity": {"type": self.ptype, "id": curShotId},
                "sg_task": {"type": "Task", "id": curTaskId},
            }

            if self.sgUserId is not None:
                data["user"] = {"type": "HumanUser", "id": self.sgUserId}

            if os.path.exists(imgPath):
                data["image"] = imgPath

            try:
                createdVersion = self.sg.create("Version", data)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "ERROR:\n%s" % traceback.format_exc()
                QMessageBox.warning(self.core.messageParent, "Shotgun Publish", erStr)
                return

            if self.chb_proxyVid.isChecked() and ffmpegIsInstalled:
                proxyPath = ""
                inputpath = source[0].replace("\\", "/")
                mp4File = (
                    os.path.join(
                        os.path.dirname(inputpath) + "(mp4)",
                        os.path.basename(inputpath),
                    )[:-9]
                    + ".mp4"
                )
                pwidth = 0
                pheight = 0
                if os.path.exists(mp4File):
                    proxyPath = mp4File
                else:
                    isSequence = False

                    if not videoInput:
                        try:
                            x = int(inputpath[-8:-4])
                            isSequence = True
                        except:
                            pass

                    if os.path.splitext(inputpath)[1] in [
                        ".jpg",
                        ".jpeg",
                        ".JPG",
                        ".png",
                        ".tif",
                        ".tiff",
                    ]:
                        size = QImage(inputpath).size()
                        pwidth = size.width()
                        pheight = size.height()
                    elif os.path.splitext(inputpath)[1] in [".exr"]:
                        oiio = self.core.media.getOIIO()

                        if oiio:
                            imgSpecs = oiio.ImageBuf(str(inputpath)).spec()
                            pwidth = imgSpecs.full_width
                            pheight = imgSpecs.full_height

                    elif os.path.splitext(inputpath)[1] in [".mp4", ".mov"]:
                        try:
                            import imageio
                        except:
                            pass
                        vidReader = imageio.get_reader(inputpath, "ffmpeg")

                        pwidth = vidReader._meta["size"][0]
                        pheight = vidReader._meta["size"][1]

                    if int(pwidth) % 2 == 1 or int(pheight) % 2 == 1:
                        QMessageBox.warning(
                            self.core.messageParent,
                            "Media conversion",
                            "Media with odd resolution can't be converted to mp4. No proxy video could be generated.",
                        )
                    else:
                        if isSequence or videoInput:
                            if isSequence:
                                inputpath = os.path.splitext(inputpath)[0][:-(self.core.framePadding)] + "%04d".replace("4", str(self.core.framePadding)) + os.path.splitext(inputpath)[1]
                                outputpath = os.path.splitext(inputpath)[0][:-(self.core.framePadding+1)] + ".mp4"
                                nProc = subprocess.Popen(
                                    [
                                        ffmpegPath,
                                        "-start_number",
                                        str(self.startFrame),
                                        "-framerate",
                                        "24",
                                        "-apply_trc",
                                        "iec61966_2_1",
                                        "-i",
                                        inputpath,
                                        "-pix_fmt",
                                        "yuv420p",
                                        "-start_number",
                                        str(self.startFrame),
                                        outputpath,
                                        "-y",
                                    ]
                                )
                            else:
                                outputpath = os.path.splitext(inputpath)[0][:-(self.core.framePadding+1)] + "(proxy).mp4"
                                nProc = subprocess.Popen(
                                    [
                                        ffmpegPath,
                                        "-apply_trc",
                                        "iec61966_2_1",
                                        "-i",
                                        inputpath,
                                        "-pix_fmt",
                                        "yuv420p",
                                        "-start_number",
                                        str(self.startFrame),
                                        outputpath,
                                        "-y",
                                    ]
                                )

                            mp4Result = nProc.communicate()
                            proxyPath = outputpath
                            tmpFiles.append(proxyPath)

                if (
                    proxyPath != ""
                    and os.path.exists(proxyPath)
                    and os.stat(proxyPath).st_size != 0
                ):
                    try:
                        self.sg.upload(
                            "Version",
                            createdVersion["id"],
                            proxyPath,
                            "sg_uploaded_movie",
                        )
                    except Exception as e:
                        QMessageBox.warning(
                            self.core.messageParent,
                            "Warning",
                            "Uploading proxy video failed:\n\n%s" % str(e),
                        )

            if self.gb_playlist.isChecked():
                fields = ["id", "versions"]
                filters = [
                    ["project", "is", {"type": "Project", "id": self.sgPrjId}],
                    ["code", "is", self.cb_playlist.currentText()],
                ]
                sgPlaylists = self.sg.find("Playlist", filters, fields)

                if len(sgPlaylists) > 0:
                    vers = sgPlaylists[0]["versions"]
                    vers.append(createdVersion)
                    data = {"versions": vers}
                    self.sg.update("Playlist", sgPlaylists[0]["id"], data)
                else:
                    data = {
                        "project": {"type": "Project", "id": self.sgPrjId},
                        "code": self.cb_playlist.currentText(),
                        "description": "dailies_01",
                        "sg_status": "opn",
                        "versions": [createdVersion],
                    }

                    try:
                        createdPlaylist = self.sg.create("Playlist", data)
                    except:
                        data.pop("sg_status")
                        createdPlaylist = self.sg.create("Playlist", data)

            for i in tmpFiles:
                try:
                    os.remove(i)
                except:
                    pass

            pubVersions.append(versionName)

            sgSite = self.core.getConfig(
                "shotgun", "site", configPath=self.core.prismIni
            )
            sgSite += "/detail/Version/" + str(createdVersion["id"])

            versionInfoPath = os.path.join(
                os.path.dirname(source[0]), "versionInfo.yml"
            )
            if not os.path.exists(versionInfoPath):
                versionInfoPath = os.path.join(
                    os.path.dirname(os.path.dirname(source[0])), "versionInfo.yml"
                )

            self.core.setConfig("information", "shotgun-url", sgSite, configPath=versionInfoPath)

        msgStr = "Successfully published:"
        for i in pubVersions:
            msgStr += "\n%s" % i

        msg = QMessageBox(
            QMessageBox.Information,
            "Shotgun Publish",
            msgStr,
            parent=self.core.messageParent,
        )
        msg.addButton("Open version in Shotgun", QMessageBox.YesRole)
        msg.addButton("Close", QMessageBox.YesRole)
        msg.setFocus()
        action = msg.exec_()

        if action == 0:
            import webbrowser

            webbrowser.open(sgSite)

        self.accept()
