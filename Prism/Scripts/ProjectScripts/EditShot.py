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

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

import MetaDataWidget
from PrismUtils.Decorators import err_catcher
from UserInterfaces import EditShot_ui


class EditShot(QDialog, EditShot_ui.Ui_dlg_EditShot):
    shotCreated = Signal(object)
    shotSaved = Signal()
    nextClicked = Signal()

    def __init__(self, core, shotData, sequences, editSequence=False, parent=None):
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.shotData = shotData or {}
        self.sequences = sequences
        self.editSequence = editSequence
        self.core.parentWindow(self, parent=parent)
        self.shotPrvXres = 250
        self.shotPrvYres = 141

        self.loadLayout()

        self.imgPath = ""
        self.btext = "Next"

        self.core.callback(
            name="onShotDlgOpen", args=[self, shotData]
        )

        self.loadData()
        self.connectEvents()

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.b_showSeq.clicked.connect(self.showSequences)
        self.buttonBox.clicked.connect(self.buttonboxClicked)
        self.e_shotName.textEdited.connect(lambda x: self.validate(self.e_shotName))
        self.e_sequence.textEdited.connect(lambda x: self.validate(self.e_sequence))
        self.l_shotPreview.mouseReleaseEvent = self.previewMouseReleaseEvent
        self.l_shotPreview.customContextMenuRequested.connect(self.rclShotPreview)
        self.b_deleteShot.clicked.connect(self.deleteShot)

    @err_catcher(name=__name__)
    def loadLayout(self):
        if len(self.sequences) == 0:
            self.b_showSeq.setVisible(False)

        self.b_deleteShot.setVisible(False)
        self.metaWidget = MetaDataWidget.MetaDataWidget(self.core, self.shotData)
        self.layout().insertWidget(self.layout().count() - 2, self.metaWidget)

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
    def previewMouseReleaseEvent(self, event):
        if event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                self.rclShotPreview()

    @err_catcher(name=__name__)
    def rclShotPreview(self, pos=None):
        rcmenu = QMenu(self)

        copAct = QAction("Capture thumbnail", self)
        copAct.triggered.connect(self.capturePreview)
        rcmenu.addAction(copAct)

        copAct = QAction("Browse thumbnail...", self)
        copAct.triggered.connect(self.browsePreview)
        rcmenu.addAction(copAct)

        clipAct = QAction("Paste thumbnail from clipboard", self)
        clipAct.triggered.connect(self.pastePreviewFromClipboard)
        rcmenu.addAction(clipAct)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def capturePreview(self):
        from PrismUtils import ScreenShot

        previewImg = ScreenShot.grabScreenArea(self.core)

        if previewImg:
            previewImg = self.core.media.scalePixmap(
                previewImg,
                self.shotPrvXres,
                self.shotPrvYres,
            )
            self.setPixmap(previewImg)

    @err_catcher(name=__name__)
    def pastePreviewFromClipboard(self):
        pmap = self.core.media.getPixmapFromClipboard()
        if not pmap:
            self.core.popup("No image in clipboard.", parent=self)
            return

        pmap = self.core.media.scalePixmap(
            pmap,
            self.shotPrvXres,
            self.shotPrvYres,
        )
        self.setPixmap(pmap)

    @err_catcher(name=__name__)
    def browsePreview(self):
        formats = "Image File (*.jpg *.png *.exr)"

        imgPath = QFileDialog.getOpenFileName(
            self, "Select thumbnail-image", self.imgPath, formats
        )[0]

        if not imgPath:
            return

        if os.path.splitext(imgPath)[1] == ".exr":
            pmsmall = self.core.media.getPixmapFromExrPath(
                imgPath,
                width=self.shotPrvXres,
                height=self.shotPrvYres,
            )
        else:
            pm = self.core.media.getPixmapFromPath(imgPath)
            if pm.width() == 0:
                warnStr = "Cannot read image: %s" % imgPath
                self.core.popup(warnStr, parent=self)
                return

            pmsmall = self.core.media.scalePixmap(
                pm,
                self.shotPrvXres,
                self.shotPrvYres,
            )

        self.setPixmap(pmsmall)

    @err_catcher(name=__name__)
    def setPixmap(self, pmsmall):
        self.pmap = pmsmall
        self.l_shotPreview.setMinimumSize(self.pmap.width(), self.pmap.height())
        self.l_shotPreview.setPixmap(self.pmap)

    @err_catcher(name=__name__)
    def validate(self, editField):
        self.core.validateLineEdit(editField)

    @err_catcher(name=__name__)
    def deleteShot(self):
        shotName = self.core.entities.getShotName(self.shotData)
        msgText = (
            'Are you sure you want to delete shot "%s"?\n\nThis will delete all scenefiles and renderings, which exist in this shot.'
            % (shotName)
        )

        result = self.core.popupQuestion(msgText, parent=self)
        if result == "Yes":
            self.core.createCmd(["deleteShot", shotName])
            self.accept(True)

    @err_catcher(name=__name__)
    def createEntities(self):
        result = None
        seqName = self.shotData["sequence"].replace(os.pathsep, ",")
        shotName = self.shotData["shot"].replace(os.pathsep, ",")
        seqs = [seq.strip() for seq in seqName.split(",") if seq.strip()]
        for seq in seqs:
            shots = [shot.strip() for shot in shotName.split(",") if shot.strip()]
            for shot in shots:
                shotData = self.shotData.copy()
                shotData["sequence"] = seq
                shotData["shot"] = shot

                result = self.core.entities.createEntity(shotData)
                self.shotCreated.emit(shotData)

        return result

    @err_catcher(name=__name__)
    def buttonboxClicked(self, button):
        if button.text() == "Add":
            result = self.saveInfo()
            if result:
                self.createEntities()
            self.shotData = {}
            self.onShotIncrementClicked()
        elif button.text() == "Create":
            result = self.saveInfo()
            if result:
                self.createEntities()
                self.accept(True)
        elif button.text() == "Save":
            result = self.saveInfo()
            if result:
                self.shotSaved.emit()
                self.accept(True)
        elif button.text() == self.btext:
            result = self.saveInfo()
            if result:
                result = self.createEntities()
                if result and not result.get("existed", True):
                    self.accept(True)
                    self.nextClicked.emit()
                else:
                    self.shotData = {}

        elif button.text() == "Cancel":
            self.reject()

    @err_catcher(name=__name__)
    def accept(self, force=False):
        if force:
            QDialog.accept(self)

        return

    @err_catcher(name=__name__)
    def getShotData(self):
        data = {
            "type": "shot",
            "sequence": self.e_sequence.text(),
            "shot": self.e_shotName.text(),
        }
        return data

    @err_catcher(name=__name__)
    def saveInfo(self):
        newShotData = self.getShotData()

        if not self.editSequence and not newShotData["shot"] or (newShotData["shot"].startswith("_") and newShotData["shot"] != "_sequence"):
            self.core.popup("Invalid shotname", parent=self)
            return False

        if not newShotData["sequence"] or newShotData["sequence"].startswith("_"):
            self.core.popup("Invalid sequencename", parent=self)
            return False

        if self.shotData.get("sequence") and newShotData["sequence"] != self.shotData["sequence"]:
            msgText = (
                'Are you sure you want to rename this sequence from "%s" to "%s"?\n\nThis will rename all files in the subfolders of the sequence, which may cause errors, if these files are referenced somewhere else.'
                % (self.shotData["sequence"], newShotData["sequence"])
            )

            result = self.core.popupQuestion(msgText, parent=self)
            if result == "No":
                return False

            self.core.entities.renameSequence(self.shotData["sequence"], newShotData["sequence"])
            if self.core.useLocalFiles:
                self.core.createCmd(["renameLocalSequence", self.shotData["sequence"], newShotData["sequence"]])
            self.shotData = newShotData
            if self.core.pb:
                self.core.pb.refreshUI()
                curw = self.core.pb.tbw_project.currentWidget()
                if hasattr(curw, "w_entities"):
                    curw.w_entities.navigate(newShotData)

        elif self.shotData.get("shot") and newShotData["shot"] != self.shotData["shot"]:
            msgText = (
                'Are you sure you want to rename this shot from "%s" to "%s"?\n\nThis will rename all files in the subfolders of the shot, which may cause errors, if these files are referenced somewhere else.'
                % (self.shotData["shot"], newShotData["shot"])
            )

            result = self.core.popupQuestion(msgText, parent=self)
            if result == "No":
                return False

            self.core.entities.renameShot(self.shotData, newShotData)
            if self.core.useLocalFiles:
                self.core.createCmd(["renameLocalShot", self.shotData, newShotData])
            self.shotData = newShotData
            if self.core.pb:
                self.core.pb.refreshUI()
                curw = self.core.pb.tbw_project.currentWidget()
                if hasattr(curw, "w_entities"):
                    curw.w_entities.navigate(newShotData)
        else:
            self.shotData = newShotData

        if not self.editSequence:
            self.core.entities.setShotRange(
                self.shotData, self.sp_startFrame.value(), self.sp_endFrame.value()
            )

        if hasattr(self, "pmap"):
            self.core.entities.setEntityPreview(self.shotData, self.pmap)

        self.metaWidget.save(self.shotData)
        self.core.callback(name="onEditShotDlgSaved", args=[self])
        return True

    @err_catcher(name=__name__)
    def loadData(self):
        shotName = self.shotData.get("shot")
        seqName = self.shotData.get("sequence")
        if seqName:
            self.e_sequence.setText(self.shotData["sequence"])

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "sequence.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.l_seqIcon.setPixmap(icon.pixmap(15, 15))

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "shot.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.l_shotIcon.setPixmap(icon.pixmap(15, 15))
        self.w_shotName.layout().addWidget(self.e_shotName, 1, 2, 1, 2)

        pmap = None
        if shotName:
            b_save = self.buttonBox.addButton("Save", QDialogButtonBox.AcceptRole)
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "check.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            b_save.setIcon(icon)
            b_cancel = self.buttonBox.addButton("Cancel", QDialogButtonBox.AcceptRole)
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "delete.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            b_cancel.setIcon(icon)
            self.e_shotName.setText(shotName)

            shotRange = self.core.entities.getShotRange(self.shotData)
            if shotRange:
                self.sp_startFrame.setValue(shotRange[0])
                self.sp_endFrame.setValue(shotRange[1])

            width = self.shotPrvXres
            height = self.shotPrvYres
            pmap = self.core.entities.getEntityPreview(self.shotData, width, height)
        else:
            self.setWindowTitle("Create Shot")
            self.b_deleteShot.setVisible(False)
            b_create = self.buttonBox.addButton("Create", QDialogButtonBox.AcceptRole)
            b_create.setToolTip("Create shot and close dialog")
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "create.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            b_create.setIcon(icon)
            b_add = self.buttonBox.addButton("Add", QDialogButtonBox.AcceptRole)
            b_add.setToolTip("Create shot and keep dialog open")
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            b_add.setIcon(icon)
            b_next = self.buttonBox.addButton(self.btext, QDialogButtonBox.AcceptRole)
            b_next.setToolTip("Create shot and open department dialog")
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "arrow_right.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            b_next.setIcon(icon)
            b_cancel = self.buttonBox.addButton("Cancel", QDialogButtonBox.AcceptRole)
            b_cancel.setToolTip("Close dialog without creating shot")
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "delete.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            b_cancel.setIcon(icon)
            if self.e_sequence.text():
                self.e_shotName.setFocus()

            self.buttonBox.setStyleSheet("* { button-layout: 2}")

            self.b_incrementSeq = QToolButton()
            self.b_incrementSeq.setToolTip("Increment sequence name.\nHold CTRL to append incremented name.")
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            self.b_incrementSeq.setIcon(icon)
            self.b_incrementSeq.clicked.connect(self.onSeqIncrementClicked)

            self.b_incrementShot = QToolButton()
            self.b_incrementShot.setToolTip("Increment shot name.\nHold CTRL to append incremented name.")
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            self.b_incrementShot.setIcon(icon)
            self.b_incrementShot.clicked.connect(self.onShotIncrementClicked)

            self.w_shotName.layout().addWidget(self.b_incrementSeq, 0, 4)
            self.w_shotName.layout().addWidget(self.b_incrementShot, 1, 4)

            self.l_seq.setText("Sequence(s):")
            self.e_sequence.setToolTip("Sequence name or comma separated list of sequence names")
            self.l_shot.setText("Shot(s):")
            self.e_shotName.setToolTip("Shot name or comma separated list of shot names")

        if not pmap:
            imgFile = os.path.join(
                self.core.projects.getFallbackFolder(), "noFileSmall.jpg"
            )
            pmap = self.core.media.getPixmapFromPath(imgFile)

        self.l_shotPreview.setMinimumSize(pmap.width(), pmap.height())
        self.l_shotPreview.setPixmap(pmap)
        self.core.callback(name="onEditShotDlgLoaded", args=[self])

    @err_catcher(name=__name__)
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            self.buttonboxClicked(self.buttonBox.buttons()[-1])
        elif event.key() == Qt.Key_Escape:
            self.reject()

    @err_catcher(name=__name__)
    def onSeqIncrementClicked(self):
        origName = self.e_sequence.text()
        name = origName.replace(os.pathsep, ",").split(",")[-1]
        num = self.getNumFromStr(name)
        inc = int(os.getenv("PRISM_SHOT_INCREMENT", "10"))
        if num:
            intnum = int(num) + inc
            newNum = str(intnum).zfill(len(num))
            newName = name[:-len(num)] + newNum
        else:
            strNum = str(inc).zfill(3)
            if name:
                newName = name + "_" + strNum
            else:
                newName = "sq_" + strNum

        mods = QApplication.keyboardModifiers()
        if mods == Qt.ControlModifier:
            newName = origName + "," + newName

        self.e_sequence.setText(newName.strip(","))

    @err_catcher(name=__name__)
    def onShotIncrementClicked(self):
        origName = self.e_shotName.text()
        name = origName.replace(os.pathsep, ",").split(",")[-1]
        num = self.getNumFromStr(name)
        inc = int(os.getenv("PRISM_SHOT_INCREMENT", "10"))
        if num:
            intnum = int(num) + inc
            newNum = str(intnum).zfill(len(num))
            newName = name[:-len(num)] + newNum
        else:
            strNum = str(inc).zfill(3)
            if name:
                newName = name + "_" + strNum
            else:
                newName = "sh_" + strNum

        mods = QApplication.keyboardModifiers()
        if mods == Qt.ControlModifier:
            newName = origName + "," + newName

        self.e_shotName.setText(newName.strip(","))

    @err_catcher(name=__name__)
    def getNumFromStr(self, val):
        numVal = ""
        for c in reversed(val):
            if c.isnumeric():
                numVal = c + numVal
            else:
                break

        return numVal
