# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Folder.ui'
#
# Created: Sat May 13 19:27:44 2017
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_wg_Folder(object):
    def setupUi(self, wg_Folder):
        wg_Folder.setObjectName("wg_Folder")
        wg_Folder.resize(340, 20)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(wg_Folder.sizePolicy().hasHeightForWidth())
        wg_Folder.setSizePolicy(sizePolicy)
        wg_Folder.setMinimumSize(QtCore.QSize(340, 0))
        wg_Folder.setMaximumSize(QtCore.QSize(340, 16777215))
        self.verticalLayout = QtGui.QVBoxLayout(wg_Folder)
        self.verticalLayout.setSpacing(6)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget = QtGui.QWidget(wg_Folder)
        self.widget.setObjectName("widget")
        self.horizontalLayout = QtGui.QHBoxLayout(self.widget)
        self.horizontalLayout.setContentsMargins(-1, 0, 18, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_5 = QtGui.QLabel(self.widget)
        self.label_5.setObjectName("label_5")
        self.horizontalLayout.addWidget(self.label_5)
        self.e_name = QtGui.QLineEdit(self.widget)
        self.e_name.setObjectName("e_name")
        self.horizontalLayout.addWidget(self.e_name)
        self.l_class = QtGui.QLabel(self.widget)
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
        wg_Folder.setWindowTitle(QtGui.QApplication.translate("wg_Folder", "Folder", None, QtGui.QApplication.UnicodeUTF8))
        self.label_5.setText(QtGui.QApplication.translate("wg_Folder", "Name:", None, QtGui.QApplication.UnicodeUTF8))
        self.l_class.setText(QtGui.QApplication.translate("wg_Folder", "Folder", None, QtGui.QApplication.UnicodeUTF8))

