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

prismRoot = sys.argv[1]

sys.path.insert(0, os.path.join(prismRoot, "Scripts"))
import PrismCore

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

qapp = QApplication.instance()
if qapp is None:
    qapp = QApplication(sys.argv)

pcore = PrismCore.create(app="Photoshop", prismArgs=["splash", "noProjectBrowser"])

if hasattr(pcore.appPlugin, "psApp") or platform.system() == "Darwin":
    curPrj = pcore.getConfig("globals", "current project")

    result = False
    if sys.argv[2] == "Tools":
        result = pcore.appPlugin.openPhotoshopTools()
    elif sys.argv[2] == "SaveVersion":
        pcore.saveScene()
    elif sys.argv[2] == "SaveComment":
        result = pcore.saveWithComment()
    elif sys.argv[2] == "Export":
        result = pcore.appPlugin.exportImage()
    elif sys.argv[2] == "ProjectBrowser":
        result = pcore.projectBrowser()
    elif sys.argv[2] == "Settings":
        result = pcore.prismSettings()

    if len(sys.argv) > 3:
        pcore.appPlugin.openScene(origin=pcore, filepath=sys.argv[3])

    if result:
        qapp.exec_()
