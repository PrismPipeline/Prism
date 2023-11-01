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
# Copyright (C) 2016-2021 Richard Frangenberg
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


def load_stylesheet(pyside=True):
    sFile = os.path.dirname(__file__) + "/style.qss"
    if not os.path.exists(sFile):
        return ""

    if sys.version[0] == "2":
        with open(sFile, "r") as f:
            stylesheet = f.read()
    else:
        with open(sFile, "r", errors="ignore") as f:
            stylesheet = f.read()

    ssheetDir = os.path.dirname(sFile)
    ssheetDir = ssheetDir.replace("\\", "/") + "/"

    repl = {
        "qss:": ssheetDir,
        "@mainBackground1": "rgb(50, 53, 55)",
        "@borders": "rgb(70, 90, 120)",
        "@tableHeader": "rgb(35, 35, 35)",
        "@selectionBackgroundColor": "rgb(70, 90, 120)",
        "@selectionBackgroundHoverColor": "rgb(60, 80, 110)",
        "@selectionHoverColor": "rgba(70, 90, 120, 80)",
        "@selectionColor": "rgb(150, 210, 240)",
        "@menuhoverbackground": "rgba(70, 90, 120, 80)",
        "@buttonBackgroundDefault": "rgb(35, 35, 35)",
        "@buttonBackgroundDisabled": "rgb(32, 32, 32)",
        "@buttonBackgroundHover": "rgb(42, 42, 42)",
        "@buttonBackgroundBright1": "rgb(60, 67, 70)",
        "@buttonBackgroundBright2": "rgb(50, 56, 59)",
        "@white": "rgb(200, 220, 235)",
        "@tableBackground": "rgb(35, 35, 35)",
        "@test": "rgb(200, 49, 49)",
        "@lightgrey": "rgb(190, 190, 190)",
        "@disabledText": "rgb(120, 130, 145)",
        "@tableBorders": "rgb(70, 90, 120)",
    }

    for key in repl:
        stylesheet = stylesheet.replace(key, repl[key])

    return stylesheet
