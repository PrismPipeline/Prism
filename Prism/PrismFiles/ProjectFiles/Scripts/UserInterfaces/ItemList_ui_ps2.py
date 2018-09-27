# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ItemList.ui'
#
# Created: Sun Mar 04 12:24:16 2018
#      by: pyside2-uic @pyside_tools_VERSION@ running on PySide2 2.0.0~alpha0
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_dlg_ItemList(object):
    def setupUi(self, dlg_ItemList):
        dlg_ItemList.setObjectName("dlg_ItemList")
        dlg_ItemList.resize(276, 420)
        self.verticalLayout = QtWidgets.QVBoxLayout(dlg_ItemList)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tw_steps = QtWidgets.QTableWidget(dlg_ItemList)
        self.tw_steps.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tw_steps.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tw_steps.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tw_steps.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tw_steps.setObjectName("tw_steps")
        self.tw_steps.setColumnCount(0)
        self.tw_steps.setRowCount(0)
        self.tw_steps.horizontalHeader().setHighlightSections(False)
        self.tw_steps.horizontalHeader().setSortIndicatorShown(True)
        self.tw_steps.horizontalHeader().setStretchLastSection(True)
        self.tw_steps.verticalHeader().setVisible(False)
        self.tw_steps.verticalHeader().setHighlightSections(False)
        self.verticalLayout.addWidget(self.tw_steps)
        self.b_addStep = QtWidgets.QPushButton(dlg_ItemList)
        self.b_addStep.setObjectName("b_addStep")
        self.verticalLayout.addWidget(self.b_addStep)
        self.chb_category = QtWidgets.QCheckBox(dlg_ItemList)
        self.chb_category.setChecked(True)
        self.chb_category.setObjectName("chb_category")
        self.verticalLayout.addWidget(self.chb_category)
        spacerItem = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.verticalLayout.addItem(spacerItem)
        self.buttonBox = QtWidgets.QDialogButtonBox(dlg_ItemList)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(dlg_ItemList)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), dlg_ItemList.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), dlg_ItemList.reject)
        QtCore.QMetaObject.connectSlotsByName(dlg_ItemList)

    def retranslateUi(self, dlg_ItemList):
        dlg_ItemList.setWindowTitle(QtWidgets.QApplication.translate("dlg_ItemList", "Select Steps", None, -1))
        self.b_addStep.setText(QtWidgets.QApplication.translate("dlg_ItemList", "Add new", None, -1))
        self.chb_category.setText(QtWidgets.QApplication.translate("dlg_ItemList", "Create default category", None, -1))

