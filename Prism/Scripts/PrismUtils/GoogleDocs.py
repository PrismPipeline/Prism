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
import sys

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1

gLibs = os.path.abspath(
    os.path.join(__file__, os.pardir, os.pardir, os.pardir, "PythonLibs", "GoogleDocs")
)
if gLibs not in sys.path:
    sys.path.append(gLibs)

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from PrismUtils.Decorators import err_catcher


class GoogleDocs(QDialog):
    def __init__(self, core, authorizationfile):
        super(GoogleDocs, self).__init__()
        self.core = core
        self.authorize(authorizationfile)

    @err_catcher(name=__name__)
    def authorize(self, authorizationfile):
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            authorizationfile, scope
        )
        self.client = gspread.authorize(creds)

    @err_catcher(name=__name__)
    def getRows(self, docName, sheetName, columns, fromRow=-1, toRow=-1):
        sheet = self.client.open(docName).worksheet(sheetName)
        colVals = []
        for col in columns:
            colVals.append(sheet.col_values(col))

        if not colVals:
            return

        entities = []
        rows = range(len(colVals[0]))
        if toRow != -1:
            rows = rows[:(toRow)]
        if fromRow != -1:
            rows = rows[(fromRow - 1):]
        for i in rows:
            entity = [x[i] if len(x) > i else "" for x in colVals]
            entities.append(entity)

        return entities

    @err_catcher(name=__name__)
    def getAllData(self, docName, sheetName, fromRow=-1, toRow=-1):
        sheet = self.client.open(docName).worksheet(sheetName)
        data = sheet.get_all_values()

        if toRow != -1:
            data = data[:toRow]
        if fromRow != -1:
            data = data[(fromRow-1):]

        return data


def readGDocs(core, authorizationfile, docName, sheetName, fromRow, toRow, columns=None):
    gd = GoogleDocs(core, authorizationfile)
    if columns:
        data = gd.getRows(docName, sheetName, columns, fromRow, toRow)
    else:
        data = gd.getAllData(docName, sheetName, fromRow, toRow)

    return data
