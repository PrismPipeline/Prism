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

        self.projectsUi = SetProjectImp()
        self.projectsUi.setup(self.core, self, openUi)

        grid = QGridLayout()
        grid.addWidget(self.projectsUi)

        self.setLayout(grid)
        self.resize(self.width(), self.minimumSizeHint().height())
        self.setFocus()


class SetProjectClass(object):
    def setup(self, core, pdialog, openUi=""):
        self.core = core
        self.pdialog = pdialog
        self.openUi = openUi

        self.refreshUi()
        self.connectEvents()

        self.core.appPlugin.setProject_loading(self)
        self.resize(self.width(), self.minimumSizeHint().height())

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.b_open.clicked.connect(self.core.openProject)
        self.b_create.clicked.connect(self.preCreate)
        self.chb_startup.stateChanged.connect(self.startupChanged)

    @err_catcher(name=__name__)
    def enterEvent(self, event):
        QApplication.restoreOverrideCursor()

    @err_catcher(name=__name__)
    def preCreate(self):
        self.core.createProject()
        self.pdialog.close()
        if hasattr(self.core, "pb") and self.core.pb.isVisible():
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

        rprojects = self.core.getConfig(cat="recent_projects", getOptions=True)
        if rprojects is None:
            rprojects = []

        cData = {}
        for i in rprojects:
            cData[i] = ["recent_projects", i]

        rPrjPaths = self.core.getConfig(data=cData)

        for prj in rPrjPaths:
            if rPrjPaths[prj] == "" or rPrjPaths[prj] == self.core.prismIni:
                continue

            rpName = self.core.getConfig(
                cat="globals", param="project_name", configPath=rPrjPaths[prj]
            )

            if rpName is None:
                continue

            prjPath = os.path.abspath(
                os.path.join(rPrjPaths[prj], os.pardir, os.pardir)
            )
            if not prjPath.endswith(os.sep):
                prjPath += os.sep

            pWidget = QWidget()
            wLayout = QHBoxLayout()
            wLayout.setContentsMargins(0, 0, 0, 0)
            l_recentName = QLabel(rpName)
            l_recentName.setMaximumWidth(100)
            l_recentPath = QLabel(prjPath)
            b_setActive = QPushButton("Set active")
            b_setActive.setMaximumWidth(100)
            b_setActive.setContextMenuPolicy(Qt.CustomContextMenu)
            wLayout.addWidget(l_recentName)
            wLayout.addWidget(l_recentPath)
            wLayout.addWidget(b_setActive)
            pWidget.setLayout(wLayout)

            self.scl_recent.addWidget(pWidget)

            b_setActive.clicked.connect(
                lambda y=None, x=rPrjPaths[prj]: self.core.changeProject(x, self.openUi)
            )
            b_setActive.customContextMenuRequested.connect(
                lambda x, y=l_recentPath: self.rclRecent(y)
            )

        if self.scl_recent.count() == 0:
            self.gb_recent.setVisible(False)
        else:
            spacer = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
            self.scl_recent.addSpacerItem(spacer)

        ssu = self.core.getConfig("globals", "ShowOnStartup", ptype="bool")
        if ssu is None:
            ssu = True

        self.chb_startup.setChecked(ssu)

    @err_catcher(name=__name__)
    def rclRecent(self, rProject):
        rcmenu = QMenu()

        delAct = QAction("Delete from recent", self)
        delAct.triggered.connect(lambda: self.deleteRecent(rProject))
        rcmenu.addAction(delAct)

        self.core.appPlugin.setRCStyle(self, rcmenu)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def deleteRecent(self, rProject):
        self.core.setRecentPrj(
            os.path.join(rProject.text(), "00_Pipeline", "pipeline.ini"),
            action="remove",
        )
        rProject.parent().setVisible(False)

        if self.scl_recent.count() == 0:
            self.gb_recent.setVisible(False)

        self.resize(self.width(), self.minimumSizeHint().height())

    @err_catcher(name=__name__)
    def startupChanged(self, state):
        if state == 0:
            self.core.setConfig("globals", "ShowOnStartup", str(False))
        elif state == 2:
            self.core.setConfig("globals", "ShowOnStartup", str(True))


class SetProjectImp(QDialog, SetProject_ui.Ui_dlg_setProject, SetProjectClass):
    def __init__(self):
        QDialog.__init__(self)
        self.setupUi(self)
