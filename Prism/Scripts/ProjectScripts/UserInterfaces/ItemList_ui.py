# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ItemList.ui'
#
# Created: Sun Mar 04 12:24:15 2018
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_dlg_ItemList(object):
    def setupUi(self, dlg_ItemList):
        dlg_ItemList.setObjectName("dlg_ItemList")
        dlg_ItemList.resize(276, 420)
        self.verticalLayout = QtGui.QVBoxLayout(dlg_ItemList)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tw_steps = QtGui.QTableWidget(dlg_ItemList)
        self.tw_steps.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.tw_steps.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tw_steps.setVerticalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.tw_steps.setHorizontalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.tw_steps.setObjectName("tw_steps")
        self.tw_steps.setColumnCount(0)
        self.tw_steps.setRowCount(0)
        self.tw_steps.horizontalHeader().setHighlightSections(False)
        self.tw_steps.horizontalHeader().setSortIndicatorShown(True)
        self.tw_steps.horizontalHeader().setStretchLastSection(True)
        self.tw_steps.verticalHeader().setVisible(False)
        self.tw_steps.verticalHeader().setHighlightSections(False)
        self.verticalLayout.addWidget(self.tw_steps)
        self.b_addStep = QtGui.QPushButton(dlg_ItemList)
        self.b_addStep.setObjectName("b_addStep")
        self.verticalLayout.addWidget(self.b_addStep)
        self.chb_category = QtGui.QCheckBox(dlg_ItemList)
        self.chb_category.setChecked(True)
        self.chb_category.setObjectName("chb_category")
        self.verticalLayout.addWidget(self.chb_category)
        spacerItem = QtGui.QSpacerItem(20, 20, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        self.verticalLayout.addItem(spacerItem)
        self.buttonBox = QtGui.QDialogButtonBox(dlg_ItemList)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(dlg_ItemList)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), dlg_ItemList.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), dlg_ItemList.reject)
        QtCore.QMetaObject.connectSlotsByName(dlg_ItemList)

    def retranslateUi(self, dlg_ItemList):
        dlg_ItemList.setWindowTitle(QtGui.QApplication.translate("dlg_ItemList", "Select Steps", None, QtGui.QApplication.UnicodeUTF8))
        self.b_addStep.setText(QtGui.QApplication.translate("dlg_ItemList", "Add new", None, QtGui.QApplication.UnicodeUTF8))
        self.chb_category.setText(QtGui.QApplication.translate("dlg_ItemList", "Create default category", None, QtGui.QApplication.UnicodeUTF8))

