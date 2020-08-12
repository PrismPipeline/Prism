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

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_TextureFolderExample_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        # This example adds a checkbox to the dialog, which will be used to create assets
        # If checked a new folder in the texture folder will be created for the new asset
        # The texture folder is \04_Assets\Textures by default in your Prism project folder
        # See the "onAssetDlgOpen" and "onAssetCreated" functions in this script for the details
        # Uncomment the following line to enable the texture folder creation. Then you need to save the file and reload the plugin by restarting your Prism application or calling the "reloadCustomPlugins" function of the PrismCore object.

        # self.textureFolders = True

    # if returns true, the plugin will be loaded by Prism
    @err_catcher(name=__name__)
    def isActive(self):
        return True

    # the following function are called by Prism at specific events, which are indicated by the function names
    # you can add your own code to any of these functions.
    @err_catcher(name=__name__)
    def onAssetDlgOpen(self, origin, assetDialog):
        if hasattr(self, "textureFolders"):
            # create a new checkbox
            chb = QCheckBox("Create texture folder")

            # set the default to checked
            chb.setChecked(True)

            # add the checkbox to the dialog
            assetDialog.w_options.layout().addWidget(chb)
            assetDialog.chb_textureFolder = chb

            # disable the checkbox if "folder" entity is selected in the asset dialog
            assetDialog.rb_asset.toggled.connect(
                lambda x: assetDialog.chb_textureFolder.setEnabled(x)
            )

    @err_catcher(name=__name__)
    def onAssetCreated(self, origin, assetName, assetPath, assetDialog=None):
        if hasattr(self, "textureFolders"):
            # check if the texture folder should be created
            if (
                assetDialog is not None
                and hasattr(assetDialog, "chb_textureFolder")
                and assetDialog.chb_textureFolder.isChecked()
            ):

                # get the asset hierarchy
                relPath = assetPath.replace(self.core.getAssetPath(), "")[1:]

                # get the asset-texture-path
                folderPath = os.path.join(
                    self.core.getTexturePath(), relPath
                )

                # create the folder. Show a message when the folder could not be created (for example through missing permissions)
                if not os.path.exists(folderPath):
                    try:
                        os.makedirs(folderPath)
                    except:
                        QMessageBox.warning(
                            self.core.messageParent,
                            "Prism",
                            "Could not create the texture folder for asset %s"
                            % assetName,
                        )
