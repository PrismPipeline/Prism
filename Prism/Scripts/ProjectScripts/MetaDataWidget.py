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
import logging

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher

logger = logging.getLogger(__name__)


class MetaDataWidget(QGroupBox):
    def __init__(self, core, entityData=None):
        QGroupBox.__init__(self)

        self.core = core
        self.core.parentWindow(self)
        self.entityData = entityData

        self.loadLayout()
        self.connectEvents()
        self.loadMetaData(entityData)

    @err_catcher(name=__name__)
    def loadLayout(self):
        self.w_add = QWidget()
        self.b_add = QToolButton()
        self.lo_add = QHBoxLayout()
        self.w_add.setLayout(self.lo_add)
        self.lo_add.addStretch()
        self.lo_add.addWidget(self.b_add)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_add.setIcon(icon)
        self.b_add.setIconSize(QSize(20, 20))
        self.b_add.setToolTip("Add Item")
        if self.core.appPlugin.pluginName != "Standalone":
            self.b_add.setStyleSheet(
                "QWidget{padding: 0; border-width: 0px;background-color: transparent} QWidget:hover{border-width: 1px; }"
            )

        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.addWidget(self.w_add)
        self.setTitle("Meta Data")

    @err_catcher(name=__name__)
    def connectEvents(self):
        self.b_add.clicked.connect(self.addItem)

    @err_catcher(name=__name__)
    def loadMetaData(self, entityData):
        metaData = self.core.entities.getMetaData(entityData)

        for key in sorted(metaData):
            self.addItem(key, metaData[key]["value"], metaData[key]["show"])

    @err_catcher(name=__name__)
    def addItem(self, key=None, value=None, show=False):
        item = MetaDataItem(self.core)
        item.removed.connect(self.removeItem)
        if key:
            item.setKey(key)

        if value:
            item.setValue(value)

        item.setShow(show)

        self.lo_main.insertWidget(self.lo_main.count() - 1, item)
        return item

    @err_catcher(name=__name__)
    def removeItem(self, item):
        idx = self.lo_main.indexOf(item)
        if idx != -1:
            w = self.lo_main.takeAt(idx)
            if w.widget():
                w.widget().deleteLater()

    @err_catcher(name=__name__)
    def save(self, entityData):
        if not entityData:
            entityData = self.entityData

        data = {}
        for idx in reversed(range(self.lo_main.count())):
            w = self.lo_main.itemAt(idx)
            widget = w.widget()
            if widget:
                if isinstance(widget, MetaDataItem):
                    if not widget.key():
                        continue

                    data[widget.key()] = {
                        "value": widget.value(),
                        "show": widget.show(),
                    }

        self.core.entities.setMetaData(entityData, data)


class MetaDataItem(QWidget):

    removed = Signal(object)

    def __init__(self, core):
        super(MetaDataItem, self).__init__()
        self.core = core
        self.loadLayout()

    @err_catcher(name=__name__)
    def loadLayout(self):
        self.e_key = QLineEdit()
        self.e_key.setPlaceholderText("Key")
        self.e_value = QLineEdit()
        self.e_value.setPlaceholderText("Value")
        self.chb_show = QCheckBox("show")
        self.chb_show.setToolTip("Show item in preview")
        self.b_remove = QToolButton()
        self.b_remove.clicked.connect(lambda: self.removed.emit(self))

        self.lo_main = QHBoxLayout()
        self.lo_main.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.lo_main)
        self.lo_main.addWidget(self.e_key)
        self.lo_main.addWidget(self.e_value)
        self.lo_main.addWidget(self.chb_show)
        self.lo_main.addWidget(self.b_remove)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "delete.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_remove.setIcon(icon)
        self.b_remove.setIconSize(QSize(20, 20))
        self.b_remove.setToolTip("Delete")
        if self.core.appPlugin.pluginName != "Standalone":
            self.b_remove.setStyleSheet(
                "QWidget{padding: 0; border-width: 0px;background-color: transparent} QWidget:hover{border-width: 1px; }"
            )

    @err_catcher(name=__name__)
    def key(self):
        return self.e_key.text()

    @err_catcher(name=__name__)
    def value(self):
        return self.e_value.text()

    @err_catcher(name=__name__)
    def show(self):
        return self.chb_show.isChecked()

    @err_catcher(name=__name__)
    def setKey(self, key):
        return self.e_key.setText(key)

    @err_catcher(name=__name__)
    def setValue(self, value):
        return self.e_value.setText(str(value))

    @err_catcher(name=__name__)
    def setShow(self, show):
        return self.chb_show.setChecked(show)
