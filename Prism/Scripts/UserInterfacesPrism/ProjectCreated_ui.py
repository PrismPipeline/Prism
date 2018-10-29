# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ProjectCreated.ui'
#
# Created: Sun Jul 08 21:20:17 2018
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_dlg_projectCreated(object):
    def setupUi(self, dlg_projectCreated):
        dlg_projectCreated.setObjectName("dlg_projectCreated")
        dlg_projectCreated.resize(297, 219)
        self.verticalLayout = QtGui.QVBoxLayout(dlg_projectCreated)
        self.verticalLayout.setObjectName("verticalLayout")
        self.l_success = QtGui.QLabel(dlg_projectCreated)
        self.l_success.setText("")
        self.l_success.setAlignment(QtCore.Qt.AlignCenter)
        self.l_success.setObjectName("l_success")
        self.verticalLayout.addWidget(self.l_success)
        self.b_browser = QtGui.QPushButton(dlg_projectCreated)
        self.b_browser.setObjectName("b_browser")
        self.verticalLayout.addWidget(self.b_browser)
        self.b_settings = QtGui.QPushButton(dlg_projectCreated)
        self.b_settings.setObjectName("b_settings")
        self.verticalLayout.addWidget(self.b_settings)
        self.b_explorer = QtGui.QPushButton(dlg_projectCreated)
        self.b_explorer.setObjectName("b_explorer")
        self.verticalLayout.addWidget(self.b_explorer)
        self.b_close = QtGui.QPushButton(dlg_projectCreated)
        self.b_close.setObjectName("b_close")
        self.verticalLayout.addWidget(self.b_close)

        self.retranslateUi(dlg_projectCreated)
        QtCore.QMetaObject.connectSlotsByName(dlg_projectCreated)

    def retranslateUi(self, dlg_projectCreated):
        dlg_projectCreated.setWindowTitle(QtGui.QApplication.translate("dlg_projectCreated", "Project created", None, QtGui.QApplication.UnicodeUTF8))
        self.b_browser.setText(QtGui.QApplication.translate("dlg_projectCreated", "Project Browser", None, QtGui.QApplication.UnicodeUTF8))
        self.b_settings.setText(QtGui.QApplication.translate("dlg_projectCreated", "Project Settings", None, QtGui.QApplication.UnicodeUTF8))
        self.b_explorer.setText(QtGui.QApplication.translate("dlg_projectCreated", "Open in Explorer", None, QtGui.QApplication.UnicodeUTF8))
        self.b_close.setText(QtGui.QApplication.translate("dlg_projectCreated", "Close", None, QtGui.QApplication.UnicodeUTF8))

