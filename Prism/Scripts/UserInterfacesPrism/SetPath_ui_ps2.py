# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'SetPath.ui'
#
# Created: Sun Aug 13 23:17:34 2017
#      by: pyside2-uic @pyside_tools_VERSION@ running on PySide2 2.0.0~alpha0
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_dlg_SetPath(object):
    def setupUi(self, dlg_SetPath):
        dlg_SetPath.setObjectName("dlg_SetPath")
        dlg_SetPath.resize(676, 110)
        self.verticalLayout = QtWidgets.QVBoxLayout(dlg_SetPath)
        self.verticalLayout.setObjectName("verticalLayout")
        self.l_description = QtWidgets.QLabel(dlg_SetPath)
        self.l_description.setObjectName("l_description")
        self.verticalLayout.addWidget(self.l_description)
        self.w_path = QtWidgets.QWidget(dlg_SetPath)
        self.w_path.setObjectName("w_path")
        self.gridLayout = QtWidgets.QGridLayout(self.w_path)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.e_path = QtWidgets.QLineEdit(self.w_path)
        self.e_path.setObjectName("e_path")
        self.gridLayout.addWidget(self.e_path, 0, 1, 1, 1)
        self.l_path = QtWidgets.QLabel(self.w_path)
        self.l_path.setObjectName("l_path")
        self.gridLayout.addWidget(self.l_path, 0, 0, 1, 1)
        self.b_browse = QtWidgets.QPushButton(self.w_path)
        self.b_browse.setMaximumSize(QtCore.QSize(50, 16777215))
        self.b_browse.setObjectName("b_browse")
        self.gridLayout.addWidget(self.b_browse, 0, 2, 1, 1)
        self.verticalLayout.addWidget(self.w_path)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.buttonBox = QtWidgets.QDialogButtonBox(dlg_SetPath)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(dlg_SetPath)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), dlg_SetPath.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), dlg_SetPath.reject)
        QtCore.QMetaObject.connectSlotsByName(dlg_SetPath)

    def retranslateUi(self, dlg_SetPath):
        dlg_SetPath.setWindowTitle(QtWidgets.QApplication.translate("dlg_SetPath", "Set local projectpath", None, -1))
        self.l_description.setText(QtWidgets.QApplication.translate("dlg_SetPath", "All your local scenefiles are saved in this folder.\n"
"This folder should be on your local hard drive and should not be synrchonized to any server.", None, -1))
        self.l_path.setText(QtWidgets.QApplication.translate("dlg_SetPath", "Local projectpath:", None, -1))
        self.b_browse.setText(QtWidgets.QApplication.translate("dlg_SetPath", "...", None, -1))

