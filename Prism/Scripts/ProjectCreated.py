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
    from UserInterfacesPrism import ProjectCreated_ui
else:
    from UserInterfacesPrism import ProjectCreated_ui_ps2 as ProjectCreated_ui


class ProjectCreated(QDialog, ProjectCreated_ui.Ui_dlg_projectCreated):
    def __init__(self, prjname, core, basepath):
        QDialog.__init__(self)
        self.setupUi(self)
        self.core = core
        self.basepath = basepath

        self.core.parentWindow(self)

        self.l_success.setText('The project "%s" was created successfully!' % prjname)

        self.setFocus()
        self.connectEvents()

    def connectEvents(self):
        self.b_browser.clicked.connect(self.core.projectBrowser)
        self.b_browser.clicked.connect(self.accept)
        self.b_settings.clicked.connect(lambda: self.core.prismSettings(tab=2))
        self.b_settings.clicked.connect(self.accept)
        self.b_explorer.clicked.connect(lambda: self.core.openFolder(self.basepath))
        self.b_explorer.clicked.connect(self.accept)
        self.b_close.clicked.connect(self.accept)
