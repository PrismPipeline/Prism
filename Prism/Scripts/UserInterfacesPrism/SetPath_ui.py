# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'SetPath.ui'
#
# Created: Sun Aug 13 23:17:34 2017
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_dlg_SetPath(object):
    def setupUi(self, dlg_SetPath):
        dlg_SetPath.setObjectName("dlg_SetPath")
        dlg_SetPath.resize(676, 110)
        self.verticalLayout = QtGui.QVBoxLayout(dlg_SetPath)
        self.verticalLayout.setObjectName("verticalLayout")
        self.l_description = QtGui.QLabel(dlg_SetPath)
        self.l_description.setObjectName("l_description")
        self.verticalLayout.addWidget(self.l_description)
        self.w_path = QtGui.QWidget(dlg_SetPath)
        self.w_path.setObjectName("w_path")
        self.gridLayout = QtGui.QGridLayout(self.w_path)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.e_path = QtGui.QLineEdit(self.w_path)
        self.e_path.setObjectName("e_path")
        self.gridLayout.addWidget(self.e_path, 0, 1, 1, 1)
        self.l_path = QtGui.QLabel(self.w_path)
        self.l_path.setObjectName("l_path")
        self.gridLayout.addWidget(self.l_path, 0, 0, 1, 1)
        self.b_browse = QtGui.QPushButton(self.w_path)
        self.b_browse.setMaximumSize(QtCore.QSize(50, 16777215))
        self.b_browse.setObjectName("b_browse")
        self.gridLayout.addWidget(self.b_browse, 0, 2, 1, 1)
        self.verticalLayout.addWidget(self.w_path)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.buttonBox = QtGui.QDialogButtonBox(dlg_SetPath)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(dlg_SetPath)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), dlg_SetPath.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), dlg_SetPath.reject)
        QtCore.QMetaObject.connectSlotsByName(dlg_SetPath)

    def retranslateUi(self, dlg_SetPath):
        dlg_SetPath.setWindowTitle(QtGui.QApplication.translate("dlg_SetPath", "Set local projectpath", None, QtGui.QApplication.UnicodeUTF8))
        self.l_description.setText(QtGui.QApplication.translate("dlg_SetPath", "All your local scenefiles are saved in this folder.\n"
"This folder should be on your local hard drive and should not be synrchonized to any server.", None, QtGui.QApplication.UnicodeUTF8))
        self.l_path.setText(QtGui.QApplication.translate("dlg_SetPath", "Local projectpath:", None, QtGui.QApplication.UnicodeUTF8))
        self.b_browse.setText(QtGui.QApplication.translate("dlg_SetPath", "...", None, QtGui.QApplication.UnicodeUTF8))

