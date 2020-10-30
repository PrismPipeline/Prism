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
    from UserInterfacesPrism import SetProject_ui
else:
    from UserInterfacesPrism import SetProject_ui_ps2 as SetProject_ui

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2

from PrismUtils.Decorators import err_catcher


class SetProject(QDialog):
    def __init__(self, core, openUi=""):
        QDialog.__init__(self)
        self.core = core
        self.core.parentWindow(self)
        self.setWindowTitle("Set Project")

        self.openUi = openUi

        self.projectsUi = SetProjectClass(self.core, self, openUi)

        grid = QGridLayout()
        grid.addWidget(self.projectsUi)

        self.setLayout(grid)
        self.resize(self.projectsUi.width(), self.projectsUi.height())
        self.setFocus()

    @err_catcher(name=__name__)
    def showEvent(self, event):
        super(SetProject, self).showEvent(event)
        if self.projectsUi.gb_recent.isVisible():
            recentEmptySpace = self.projectsUi.spacer_recent.geometry().height()
            if recentEmptySpace > 0:
                height = self.height() - recentEmptySpace
                self.resize(self.width(), height)
                self.move(self.pos().x(), self.pos().y() + recentEmptySpace/2)
        else:
            newHeight = self.minimumSizeHint().height()
            difference = self.height() - newHeight
            self.resize(self.width(), newHeight)
            self.move(self.pos().x(), self.pos().y() + difference/2)


class SetProjectClass(QDialog, SetProject_ui.Ui_dlg_setProject):
    def __init__(self, core, pdialog, openUi=""):
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.pdialog = pdialog
        self.openUi = openUi

        self.refreshUi()
        self.connectEvents()

        getattr(self.core.appPlugin, "setProject_loading", lambda x: None)(self)
        self.core.callback(
            name="onSetProjectStartup", types=["prjManagers", "custom"], args=[self]
        )

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.b_open.clicked.connect(self.core.projects.openProject)
        self.b_create.clicked.connect(self.preCreate)
        self.chb_startup.stateChanged.connect(self.startupChanged)

    @err_catcher(name=__name__)
    def enterEvent(self, event):
        try:
            QApplication.restoreOverrideCursor()
        except:
            pass

    @err_catcher(name=__name__)
    def preCreate(self):
        self.core.projects.createProjectDialog()
        self.pdialog.close()
        if getattr(self.core, "pb", None) and self.core.pb.isVisible():
            self.core.pb.close()

    @err_catcher(name=__name__)
    def refreshUi(self):
        if hasattr(self.core, "projectName") and self.core.projectName is not None:
            self.l_project.setText(
                "Current Project:\n\n"
                + (self.core.projectName + "          " + self.core.projectPath)
            )
        else:
            self.l_project.setText("No current project")

        self.gb_recent.setStyleSheet("""
            QWidget#project {
                background-color: rgba(255, 255, 255, 20);
            }
            QWidget#pchild {
                background-color: rgba(0, 0, 0, 0);
            }
            QScrollArea {
                border: 0px;
            }
        """)

        rPrjPaths = self.core.getConfig(cat="recent_projects") or []
        for prjPath in rPrjPaths:
            if not prjPath or not self.core.isStr(prjPath) or prjPath == self.core.prismIni:
                continue

            rpName = self.core.getConfig(
                cat="globals", param="project_name", configPath=prjPath
            )

            if rpName is None:
                continue

            prjPath = os.path.abspath(
                os.path.join(prjPath, os.pardir, os.pardir)
            )
            if not prjPath.endswith(os.sep):
                prjPath += os.sep

            pWidget = QWidget()
            pWidget.setAttribute(Qt.WA_StyledBackground, True)
            wLayout = QHBoxLayout()
            wLayout.setContentsMargins(9, 4, 9, 4)
            l_recentName = QLabel(rpName)
            l_recentName.setMinimumWidth(200 * self.core.uiScaleFactor)
            l_recentName.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))
            l_recentName.setStyleSheet("padding: 0 30 0 30;")
            l_recentPath = QLabel(prjPath)
            l_recentPath.setWordWrap(True)
            l_recentPath.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred))
            l_recentPath.setToolTip(prjPath)
            b_setActive = QPushButton("Set active")
            b_setActive.setMinimumWidth(100 * self.core.uiScaleFactor)
            b_setActive.setMaximumWidth(100 * self.core.uiScaleFactor)
            b_setActive.setContextMenuPolicy(Qt.CustomContextMenu)
            wLayout.addWidget(b_setActive)
            wLayout.addWidget(l_recentName)
            wLayout.addWidget(l_recentPath)
        #    wLayout.addStretch()
            pWidget.setLayout(wLayout)
            l_recentName.setObjectName("pchild")
            l_recentPath.setObjectName("pchild")
            pWidget.setObjectName("project")

            self.scl_recent.addWidget(pWidget)

            b_setActive.clicked.connect(
                lambda y=None, x=prjPath: self.core.changeProject(x, self.openUi)
            )
            b_setActive.customContextMenuRequested.connect(
                lambda x, y=l_recentPath: self.rclRecent(y)
            )

        if self.scl_recent.count() == 0:
            self.gb_recent.setVisible(False)
        else:
            self.spacer_recent = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
            self.scl_recent.addSpacerItem(self.spacer_recent)

        ssu = self.core.getConfig("globals", "showonstartup")
        if ssu is None:
            ssu = True

        self.chb_startup.setChecked(ssu)

    @err_catcher(name=__name__)
    def rclRecent(self, rProject):
        rcmenu = QMenu(self)

        delAct = QAction("Delete from recent", self)
        delAct.triggered.connect(lambda: self.deleteRecent(rProject))
        rcmenu.addAction(delAct)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def deleteRecent(self, rProject):
        self.core.projects.setRecentPrj(
            os.path.join(rProject.text(), "00_Pipeline", "pipeline.yml"),
            action="remove",
        )
        rProject.parent().setVisible(False)

        if self.scl_recent.count() == 0:
            self.gb_recent.setVisible(False)

    @err_catcher(name=__name__)
    def startupChanged(self, state):
        if state == 0:
            self.core.setConfig("globals", "showonstartup", False)
        elif state == 2:
            self.core.setConfig("globals", "showonstartup", True)
