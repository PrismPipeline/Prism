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
    import EditShot_ui
else:
    import EditShot_ui_ps2 as EditShot_ui

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2

from PrismUtils.Decorators import err_catcher


class EditShot(QDialog, EditShot_ui.Ui_dlg_EditShot):
    def __init__(self, core, shotName, sequences, editSequence=False):
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.shotName = shotName
        self.sequences = sequences
        self.editSequence = editSequence
        self.core.parentWindow(self)

        if len(self.sequences) == 0:
            self.b_showSeq.setVisible(False)

        self.b_deleteShot.setVisible(False)

        self.core.appPlugin.editShot_startup(self)
        getattr(self.core.appPlugin, "editShot_loadLibs", lambda x: self.loadLibs())(
            self
        )
        self.oiio = self.core.media.getOIIO()

        self.imgPath = ""
        self.btext = "Next"

        self.loadData()
        self.connectEvents()

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.b_showSeq.clicked.connect(self.showSequences)
        self.b_changePreview.clicked.connect(self.browse)
        self.buttonBox.clicked.connect(self.buttonboxClicked)
        self.e_shotName.textEdited.connect(lambda x: self.validate(self.e_shotName))
        self.e_sequence.textEdited.connect(lambda x: self.validate(self.e_sequence))
        self.b_deleteShot.clicked.connect(self.deleteShot)

    @err_catcher(name=__name__)
    def loadLibs(self):
        pass

    @err_catcher(name=__name__)
    def showSequences(self):
        smenu = QMenu(self)

        for i in self.sequences:
            sAct = QAction(i, self)
            sAct.triggered.connect(lambda x=None, t=i: self.seqClicked(t))
            smenu.addAction(sAct)

        smenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def seqClicked(self, seq):
        self.e_sequence.setText(seq)

    @err_catcher(name=__name__)
    def browse(self):
        formats = "Image File (*.jpg *.png *.exr)"

        imgPath = QFileDialog.getOpenFileName(
            self, "Select preview-image", self.imgPath, formats
        )[0]

        if imgPath != "":
            if os.path.splitext(imgPath)[1] == ".exr":
                qimg = QImage(
                    self.core.pb.shotPrvXres,
                    self.core.pb.shotPrvYres,
                    QImage.Format_RGB16,
                )

                if self.oiio:
                    imgSrc = self.oiio.ImageBuf(str(imgPath))
                    rgbImgSrc = self.oiio.ImageBuf()
                    self.oiio.ImageBufAlgo.channels(rgbImgSrc, imgSrc, (0, 1, 2))
                    imgWidth = rgbImgSrc.spec().full_width
                    imgHeight = rgbImgSrc.spec().full_height
                    xOffset = 0
                    yOffset = 0
                    if (imgWidth / float(imgHeight)) > 1.7778:
                        newImgWidth = self.core.pb.shotPrvXres
                        newImgHeight = (
                            self.core.pb.shotPrvXres / float(imgWidth) * imgHeight
                        )
                    else:
                        newImgHeight = self.core.pb.shotPrvYres
                        newImgWidth = (
                            self.core.pb.shotPrvYres / float(imgHeight) * imgWidth
                        )
                    imgDst = self.oiio.ImageBuf(
                        self.oiio.ImageSpec(
                            int(newImgWidth), int(newImgHeight), 3, self.oiio.UINT8
                        )
                    )
                    self.oiio.ImageBufAlgo.resample(imgDst, rgbImgSrc)
                    sRGBimg = self.oiio.ImageBuf()
                    self.oiio.ImageBufAlgo.pow(
                        sRGBimg, imgDst, (1.0 / 2.2, 1.0 / 2.2, 1.0 / 2.2)
                    )
                    bckImg = self.oiio.ImageBuf(
                        self.oiio.ImageSpec(
                            int(newImgWidth), int(newImgHeight), 3, self.oiio.UINT8
                        )
                    )
                    self.oiio.ImageBufAlgo.fill(bckImg, (0.5, 0.5, 0.5))
                    self.oiio.ImageBufAlgo.paste(bckImg, xOffset, yOffset, 0, 0, sRGBimg)
                    qimg = QImage(
                        int(newImgWidth), int(newImgHeight), QImage.Format_RGB16
                    )
                    for i in range(int(newImgWidth)):
                        for k in range(int(newImgHeight)):
                            rgb = qRgb(
                                bckImg.getpixel(i, k)[0] * 255,
                                bckImg.getpixel(i, k)[1] * 255,
                                bckImg.getpixel(i, k)[2] * 255,
                            )
                            qimg.setPixel(i, k, rgb)

                    pmsmall = QPixmap.fromImage(qimg)
                else:
                    QMessageBox.critical(
                        self.core.messageParent,
                        "Error",
                        "No image loader available. Unable to read the file.",
                    )
                    return
            else:
                pm = self.core.media.getPixmapFromPath(imgPath)
                if pm.width() == 0:
                    warnStr = "Cannot read image: %s" % imgPath
                    msg = QMessageBox(
                        QMessageBox.Warning,
                        "Warning",
                        warnStr,
                        QMessageBox.Ok,
                        parent=self.core.messageParent,
                    )
                    msg.setFocus()
                    msg.exec_()
                    return

                if (pm.width() / float(pm.height())) > 1.7778:
                    pmsmall = pm.scaledToWidth(self.core.pb.shotPrvXres)
                else:
                    pmsmall = pm.scaledToHeight(self.core.pb.shotPrvYres)

            self.pmap = pmsmall

            self.l_shotPreview.setMinimumSize(self.pmap.width(), self.pmap.height())
            self.l_shotPreview.setPixmap(self.pmap)

    @err_catcher(name=__name__)
    def validate(self, editField):
        denyChars = [self.core.sequenceSeparator] if editField == self.e_sequence else None

        self.core.validateLineEdit(editField, denyChars=denyChars)

    @err_catcher(name=__name__)
    def deleteShot(self):
        msgText = (
            'Are you sure you want to delete shot "%s"?\n\nThis will delete all scenefiles and renderings, which exist in this shot.'
            % (self.shotName)
        )
        if psVersion == 1:
            flags = QMessageBox.StandardButton.Yes
            flags |= QMessageBox.StandardButton.No
            result = QMessageBox.question(
                self.core.messageParent, "Warning", msgText, flags
            )
        else:
            result = QMessageBox.question(self.core.messageParent, "Warning", msgText)

        if str(result).endswith(".Yes"):
            self.core.createCmd(["deleteShot", self.shotName])
            self.accept()

    @err_catcher(name=__name__)
    def buttonboxClicked(self, button):
        if button.text() == "Create":
            result = self.saveInfo()
            if result:
                self.core.pb.createShot(self.shotName)
            self.shotName = None
        elif button.text() == "Create and close":
            result = self.saveInfo()
            if result:
                self.core.pb.createShot(self.shotName)
                self.accept()
        elif button.text() == "Save":
            result = self.saveInfo()
            if result:
                self.core.pb.refreshShotinfo()
                self.accept()
        elif button.text() == self.btext:
            result = self.saveInfo()
            if result:
                result = self.core.pb.createShot(self.shotName)
                if result and not result.get("existed", True):
                    self.accept()
                    self.core.pb.createStepWindow("s")

    @err_catcher(name=__name__)
    def getShotName(self):
        newSName = self.core.entities.getShotname(
            self.e_sequence.text(),
            self.e_shotName.text(),
        )
        return newSName

    @err_catcher(name=__name__)
    def saveInfo(self):
        newSName = self.getShotName()
        shotName, seqName = self.core.entities.splitShotname(newSName)
        shotNameOrig, seqNameOrig = self.core.entities.splitShotname(self.shotName)

        if not self.editSequence and not shotName:
            self.core.popup("Invalid shotname")
            return False

        if self.editSequence and not seqName:
            self.core.popup("Invalid sequencename")
            return False

        if shotNameOrig and newSName != self.shotName:
            msgText = (
                'Are you sure you want to rename this shot from "%s" to "%s"?\n\nThis will rename all files in the subfolders of the shot, which may cause errors, if these files are referenced somewhere else.'
                % (self.shotName, newSName)
            )
            if psVersion == 1:
                flags = QMessageBox.StandardButton.Yes
                flags |= QMessageBox.StandardButton.No
                result = QMessageBox.question(
                    self.core.messageParent, "Warning", msgText, flags
                )
            else:
                result = QMessageBox.question(
                    self.core.messageParent, "Warning", msgText
                )

            if str(result).endswith(".Yes"):
                self.core.createCmd(["renameShot", self.shotName, newSName])
                self.core.checkCommands()
                self.shotName = newSName
        else:
            self.shotName = newSName

        if not self.editSequence:
            self.core.entities.setShotRange(
                self.shotName, self.sp_startFrame.value(), self.sp_endFrame.value()
            )

        if hasattr(self, "pmap"):
            prvPath = os.path.join(
                os.path.dirname(self.core.prismIni),
                "Shotinfo",
                "%s_preview.jpg" % self.shotName,
            )
            self.core.media.savePixmap(self.pmap, prvPath)

        for i in self.core.prjManagers.values():
            i.editShot_closed(self, self.shotName)

        return True

    @err_catcher(name=__name__)
    def loadData(self):
        shotName, seqName = self.core.entities.splitShotname(self.shotName)
        if seqName and seqName != "no sequence":
            self.e_sequence.setText(seqName)

        if shotName:
            self.e_shotName.setText(shotName)

            shotRange = self.core.entities.getShotRange(self.shotName)
            if shotRange:
                self.sp_startFrame.setValue(shotRange[0])
                self.sp_endFrame.setValue(shotRange[1])

            imgPath = os.path.join(
                os.path.dirname(self.core.prismIni),
                "Shotinfo",
                "%s_preview.jpg" % self.shotName,
            )
        else:
            self.setWindowTitle("Create Shot")
            self.b_deleteShot.setVisible(False)
            self.buttonBox.removeButton(self.buttonBox.buttons()[0])
            self.buttonBox.addButton("Create and close", QDialogButtonBox.AcceptRole)
            self.buttonBox.addButton("Create", QDialogButtonBox.ApplyRole)
            b = self.buttonBox.addButton(self.btext, QDialogButtonBox.ApplyRole)
            b.setToolTip("Create shot and open step dialog")
            self.buttonBox.setStyleSheet("* { button-layout: 2}")
            if self.e_sequence.text():
                self.e_shotName.setFocus()

        if shotName and os.path.exists(imgPath):
            pm = self.core.media.getPixmapFromPath(imgPath)
            if (pm.width() / float(pm.height())) > 1.7778:
                pmap = pm.scaledToWidth(self.core.pb.shotPrvXres)
            else:
                pmap = pm.scaledToHeight(self.core.pb.shotPrvYres)
        else:
            imgFile = os.path.join(
                self.core.projectPath, "00_Pipeline", "Fallbacks", "noFileSmall.jpg"
            )
            pmap = self.core.media.getPixmapFromPath(imgFile)

        self.l_shotPreview.setMinimumSize(pmap.width(), pmap.height())
        self.l_shotPreview.setPixmap(pmap)

        for i in self.core.prjManagers.values():
            i.editShot_open(self, self.shotName)

    @err_catcher(name=__name__)
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            self.buttonboxClicked(self.buttonBox.buttons()[-1])
        elif event.key() == Qt.Key_Escape:
            self.reject()