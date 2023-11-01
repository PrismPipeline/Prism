# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Folder.ui'
#
# Created: Mon Sep  4 22:29:18 2023
#      by: qtpy-uic 2.0.5
#
# WARNING! All changes made in this file will be lost!

from qtpy import QtCore, QtGui, QtWidgets

class Ui_wg_Folder(object):
    def setupUi(self, wg_Folder):
        wg_Folder.setObjectName("wg_Folder")
        wg_Folder.resize(340, 20)
        self.verticalLayout = QtWidgets.QVBoxLayout(wg_Folder)
        self.verticalLayout.setSpacing(6)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget = QtWidgets.QWidget(wg_Folder)
        self.widget.setObjectName("widget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget)
        self.horizontalLayout.setContentsMargins(-1, 0, 18, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.l_name = QtWidgets.QLabel(self.widget)
        self.l_name.setObjectName("l_name")
        self.horizontalLayout.addWidget(self.l_name)
        self.e_name = QtWidgets.QLineEdit(self.widget)
        self.e_name.setObjectName("e_name")
        self.horizontalLayout.addWidget(self.e_name)
        self.l_class = QtWidgets.QLabel(self.widget)
        font = QtGui.QFont()
        font.setWeight(75)
        font.setBold(True)
        self.l_class.setFont(font)
        self.l_class.setObjectName("l_class")
        self.horizontalLayout.addWidget(self.l_class)
        self.verticalLayout.addWidget(self.widget)

        self.retranslateUi(wg_Folder)
        QtCore.QMetaObject.connectSlotsByName(wg_Folder)

    def retranslateUi(self, wg_Folder):
        wg_Folder.setWindowTitle(QtWidgets.QApplication.translate("", "Folder", None, -1))
        self.l_name.setText(QtWidgets.QApplication.translate("", "Name:", None, -1))
        self.l_class.setText(QtWidgets.QApplication.translate("", "Folder", None, -1))

