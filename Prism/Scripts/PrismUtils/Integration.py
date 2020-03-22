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


def removeIntegrations(filepaths, deleteEmpty=False):
    for f in filepaths:
        removeIntegration(filepath=f, deleteEmpty=deleteEmpty)


def removeIntegration(content=None, filepath=None, deleteEmpty=True):
    if not content:
        if not os.path.exists(filepath):
            return

        with open(filepath, "r") as f:
            content = f.read()

    while True:
        if "# >>>PrismStart" in content and "# <<<PrismEnd" in content:
            content = (
                content[:content.find("# >>>PrismStart")]
                + content[content.find("# <<<PrismEnd") + len("# <<<PrismEnd"):]
            )
        elif "#>>>PrismStart" in content and "#<<<PrismEnd" in content:
            content = (
                content[:content.find("#>>>PrismStart")]
                + content[content.find("#<<<PrismEnd") + len("#<<<PrismEnd"):]
            )
        else:
            break

    if filepath:
        with open(filepath, "w") as f:
            f.write(content)

        if deleteEmpty:
            otherChars = [x for x in content if x not in [" ", "\n"]]
            if not otherChars:
                os.remove(filepath)

    return content
