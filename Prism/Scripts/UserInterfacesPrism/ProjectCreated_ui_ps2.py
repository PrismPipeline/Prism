# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ProjectCreated.ui'
#
# Created: Sun Jul 08 21:20:17 2018
#      by: pyside2-uic @pyside_tools_VERSION@ running on PySide2 2.0.0~alpha0
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_dlg_projectCreated(object):
    def setupUi(self, dlg_projectCreated):
        dlg_projectCreated.setObjectName("dlg_projectCreated")
        dlg_projectCreated.resize(297, 219)
        self.verticalLayout = QtWidgets.QVBoxLayout(dlg_projectCreated)
        self.verticalLayout.setObjectName("verticalLayout")
        self.l_success = QtWidgets.QLabel(dlg_projectCreated)
        self.l_success.setText("")
        self.l_success.setAlignment(QtCore.Qt.AlignCenter)
        self.l_success.setObjectName("l_success")
        self.verticalLayout.addWidget(self.l_success)
        self.b_browser = QtWidgets.QPushButton(dlg_projectCreated)
        self.b_browser.setObjectName("b_browser")
        self.verticalLayout.addWidget(self.b_browser)
        self.b_settings = QtWidgets.QPushButton(dlg_projectCreated)
        self.b_settings.setObjectName("b_settings")
        self.verticalLayout.addWidget(self.b_settings)
        self.b_explorer = QtWidgets.QPushButton(dlg_projectCreated)
        self.b_explorer.setObjectName("b_explorer")
        self.verticalLayout.addWidget(self.b_explorer)
        self.b_close = QtWidgets.QPushButton(dlg_projectCreated)
        self.b_close.setObjectName("b_close")
        self.verticalLayout.addWidget(self.b_close)

        self.retranslateUi(dlg_projectCreated)
        QtCore.QMetaObject.connectSlotsByName(dlg_projectCreated)

    def retranslateUi(self, dlg_projectCreated):
        dlg_projectCreated.setWindowTitle(QtWidgets.QApplication.translate("dlg_projectCreated", "Project created", None, -1))
        self.b_browser.setText(QtWidgets.QApplication.translate("dlg_projectCreated", "Project Browser", None, -1))
        self.b_settings.setText(QtWidgets.QApplication.translate("dlg_projectCreated", "Project Settings", None, -1))
        self.b_explorer.setText(QtWidgets.QApplication.translate("dlg_projectCreated", "Open in Explorer", None, -1))
        self.b_close.setText(QtWidgets.QApplication.translate("dlg_projectCreated", "Close", None, -1))

