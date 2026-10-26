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
# Copyright (C) 2023-2026 Prism Software GmbH
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


import ctypes
import ctypes.wintypes
import os
import platform


def get_user_pref_dir():
    override = os.getenv("PRISM_USER_PREFS")
    if override:
        return override

    home = os.path.expanduser("~")
    system = platform.system()
    if system == "Windows":
        documents = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        result = ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, documents)
        if result == 0 and documents.value:
            base = documents.value
        else:
            data_dir = os.getenv("PRISM_DATA_DIR") or os.path.join(
                os.environ["PROGRAMDATA"], "Prism Pipeline"
            )
            base = os.path.join(data_dir, "userprefs")
    elif system == "Darwin":
        base = os.path.join(home, "Library", "Preferences")
    else:
        base = home
    return os.path.join(base, "Prism2")


def get_comfy_config_path():
    override = os.getenv("PRISM_COMFYUI_CONFIG_PATH", "")
    if override:
        return os.path.normpath(os.path.expandvars(os.path.expanduser(override)))
    return os.path.join(get_user_pref_dir(), "comfy.json")