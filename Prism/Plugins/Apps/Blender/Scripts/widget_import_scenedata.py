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


import bpy
import os
import sys
import threading
import platform
import traceback
import time
import shutil
from functools import wraps

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1


class Import_SceneData(QDialog):
    def __init__(self, core, plugin):
        super(Import_SceneData, self).__init__()
        self.core = core
        self.plugin = plugin

    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            exc_info = sys.exc_info()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = (
                    "%s ERROR - Prism_Plugin_Blender - Core: %s - Plugin: %s:\n%s\n\n%s"
                    % (
                        time.strftime("%d/%m/%y %X"),
                        args[0].core.version,
                        args[0].plugin.version,
                        "".join(traceback.format_stack()),
                        traceback.format_exc(),
                    )
                )
                args[0].core.writeErrorLog(erStr)

        return func_wrapper

    @err_decorator
    def importScene(self, scenepath, update, state):
        self.scenepath = scenepath
        self.state = state
        self.updated = False

        validNodes = [x for x in self.state.nodes if self.plugin.isNodeValid(self.state, x)]
        print (self.state.nodes)
        print (validNodes)
        if update and validNodes:
            self.updated = self.updateData(validNodes)
            if self.updated:
                return

        self.setupUI()
        self.connectEvents()
        self.refreshTree()
        action = self.exec_()
        return action

    @err_decorator
    def setupUI(self):
        self.core.parentWindow(self)
        self.setWindowTitle(os.path.basename(self.scenepath))
        self.lo_main = QVBoxLayout()
        self.tw_scenedata = QTreeWidget()
        self.tw_scenedata.header().setVisible(False)

        self.tw_scenedata.setColumnCount(1)
        self.tw_scenedata.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tw_scenedata.setSortingEnabled(False)
        self.tw_scenedata.setHorizontalScrollMode(
            QAbstractItemView.ScrollPerPixel
        )
        self.tw_scenedata.setVerticalScrollMode(
            QAbstractItemView.ScrollPerPixel
        )
        self.tw_scenedata.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tw_scenedata.itemClicked.connect(self.selectionChanged)

        self.bb_main = QDialogButtonBox(QDialogButtonBox.Cancel)

        b_link = self.bb_main.addButton("Link", QDialogButtonBox.AcceptRole)
        b_append = self.bb_main.addButton("Append", QDialogButtonBox.AcceptRole)
        b_link.clicked.connect(lambda: self.importData(link=True))
        b_append.clicked.connect(lambda: self.importData(link=False))
        self.bb_main.accepted.connect(self.accept)
        self.bb_main.rejected.connect(self.reject)

        self.lo_main.addWidget(self.tw_scenedata)
        self.lo_main.addWidget(self.bb_main)
        self.setLayout(self.lo_main)

        self.resize(800 * self.core.uiScaleFactor, 600 * self.core.uiScaleFactor)

    @err_decorator
    def connectEvents(self):
        self.tw_scenedata.doubleClicked.connect(self.accept)
        self.tw_scenedata.doubleClicked.connect(lambda: self.importData(link=False))

    @err_decorator
    def selectionChanged(self, item, column):
        for cIdx in range(item.childCount()):
            item.child(cIdx).setSelected(item.isSelected())

    @err_decorator
    def refreshTree(self):
        with bpy.data.libraries.load(self.scenepath, link=False) as (data_from, data_to):
            pass

        self.tw_scenedata.clear()

        cats = ["Collections", "Objects"]

        for cat in cats:
            parentItem = QTreeWidgetItem([cat])
            self.tw_scenedata.addTopLevelItem(parentItem)
            parentItem.setExpanded(True)

            for obj in getattr(data_from, cat.lower()):
                item = QTreeWidgetItem([obj])
                parentItem.addChild(item)

    @err_decorator
    def getSelectedData(self):
        data = {}
        for iIdx in range(self.tw_scenedata.topLevelItemCount()):
            tItem = self.tw_scenedata.topLevelItem(iIdx)
            data[tItem.text(0).lower()] = []

        for sItem in self.tw_scenedata.selectedItems():
            if not sItem.parent():
                continue

            data[sItem.parent().text(0).lower()].append(sItem.text(0))

        return data

    @err_decorator
    def updateData(self, validNodes):
        if validNodes and validNodes[0]["library"]:
            for i in validNodes:
                oldLib = self.plugin.getObject(i).library.filepath
                self.plugin.getObject(i).library.filepath = self.scenepath
                for node in self.state.nodes:
                    if node["library"] == oldLib:
                        node["library"] = self.scenepath

            self.plugin.getObject(i).library.reload()
            return True

    @err_decorator
    def importData(self, link=False):
        self.state.preDelete(
            baseText="Do you want to delete the currently connected objects?\n\n"
        )

        if bpy.app.version >= (2, 80, 0):
            self.existingNodes = list(bpy.data.objects)
        else:
            self.existingNodes = list(bpy.context.scene.objects)

        data = self.getSelectedData()

        with bpy.data.libraries.load(self.scenepath, link=link) as (data_from, data_to):
            data_to.collections = data["collections"]
            data_to.objects = data["objects"]

        for collection in data_to.collections:
            if collection in list(bpy.context.scene.collection.children):
                self.core.popup("Collection already exists: %s" % collection.name)
                continue

            bpy.context.scene.collection.children.link(collection)

        for obj in data_to.objects:
            if obj:
                if bpy.app.version >= (2, 80, 0):
                    if obj in list(bpy.context.scene.collection.objects):
                        self.core.popup("Object already exists: %s" % obj.name)
                        continue

                    bpy.context.scene.collection.objects.link(obj)
                else:
                    if obj in list(bpy.context.scene.objects):
                        self.core.popup("Object already exists: %s" % obj.name)
                        continue

                    bpy.context.scene.objects.link(obj)
