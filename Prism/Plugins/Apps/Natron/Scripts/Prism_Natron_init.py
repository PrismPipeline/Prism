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


from Prism_Natron_Variables import Prism_Natron_Variables
from Prism_Natron_externalAccess_Functions import Prism_Natron_externalAccess_Functions
from Prism_Natron_Functions import Prism_Natron_Functions
from Prism_Natron_Integration import Prism_Natron_Integration


class Prism_Plugin_Natron(
    Prism_Natron_Variables,
    Prism_Natron_externalAccess_Functions,
    Prism_Natron_Functions,
    Prism_Natron_Integration,
):
    def __init__(self, core):
        Prism_Natron_Variables.__init__(self, core, self)
        Prism_Natron_externalAccess_Functions.__init__(self, core, self)
        Prism_Natron_Functions.__init__(self, core, self)
        Prism_Natron_Integration.__init__(self, core, self)
