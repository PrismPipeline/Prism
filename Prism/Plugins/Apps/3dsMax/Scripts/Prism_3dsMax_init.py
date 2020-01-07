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


from Prism_3dsMax_Variables import Prism_3dsMax_Variables
from Prism_3dsMax_externalAccess_Functions import Prism_3dsMax_externalAccess_Functions
from Prism_3dsMax_Functions import Prism_3dsMax_Functions
from Prism_3dsMax_Integration import Prism_3dsMax_Integration


class Prism_Plugin_3dsMax(
    Prism_3dsMax_Variables,
    Prism_3dsMax_externalAccess_Functions,
    Prism_3dsMax_Functions,
    Prism_3dsMax_Integration,
):
    def __init__(self, core):
        Prism_3dsMax_Variables.__init__(self, core, self)
        Prism_3dsMax_externalAccess_Functions.__init__(self, core, self)
        Prism_3dsMax_Functions.__init__(self, core, self)
        Prism_3dsMax_Integration.__init__(self, core, self)
