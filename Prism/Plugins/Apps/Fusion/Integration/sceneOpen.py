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

prismRoot = os.getenv("PRISM_ROOT")
if not prismRoot:
    prismRoot = PRISMROOT
	
sys.path.append(os.path.join(prismRoot, "Scripts"))
sys.path.append(os.path.join(prismRoot, "PythonLibs", "Python27", "PySide"))
sys.path.append(os.path.join(prismRoot, "PythonLibs", "Python37", "PySide"))

try:
	from PySide2.QtCore import *
	from PySide2.QtGui import *
	from PySide2.QtWidgets import *
except:
	from PySide.QtCore import *
	from PySide.QtGui import *

qapp = QApplication.instance()

if qapp == None:
	qapp = QApplication(sys.argv)

import PrismCore

pcore = PrismCore.PrismCore(app="Fusion")
pcore.appPlugin.fusion = fusion

curPrj = pcore.getConfig("globals", "current project")
if curPrj is not None and curPrj != "":
	pcore.changeProject(curPrj, openUi="") # projectBrowser
else:
	pcore.projects.setProject(openUi="projectBrowser")

pcore.sceneOpen()

qapp.exec_()