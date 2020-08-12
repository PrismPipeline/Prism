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
import platform
import shutil

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_Houdini_externalAccess_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

    @err_catcher(name=__name__)
    def getAutobackPath(self, origin, tab):
        autobackpath = ""
        if platform.system() == "Windows":
            autobackpath = os.path.join(
                os.getenv("LocalAppdata"), "Temp", "houdini_temp"
            )

            if not os.path.exists(autobackpath):
                autobackpath = os.path.dirname(autobackpath)

        fileStr = "Houdini Scene File ("
        for i in self.sceneFormats:
            fileStr += "*%s " % i

        fileStr += ")"

        return autobackpath, fileStr

    @err_catcher(name=__name__)
    def onProjectCreated(self, origin, projectPath, projectName):
        hdaDir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "HDAs")

        pHdaPath = os.path.join(projectPath, "00_Pipeline", "HDAs")

        if not os.path.exists(pHdaPath):
            os.makedirs(pHdaPath)

        for i in os.listdir(hdaDir):
            if os.path.splitext(i)[1] not in [".hda", ".otl"]:
                continue

            origPath = os.path.join(hdaDir, i)
            targetPath = os.path.join(pHdaPath, i)

            shutil.copy2(origPath, targetPath)
