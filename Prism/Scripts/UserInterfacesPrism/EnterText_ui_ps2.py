# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'EnterText.ui'
#
# Created: Sun Nov 05 11:21:33 2017
#      by: pyside2-uic @pyside_tools_VERSION@ running on PySide2 2.0.0~alpha0
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_dlg_EnterText(object):
    def setupUi(self, dlg_EnterText):
        dlg_EnterText.setObjectName("dlg_EnterText")
        dlg_EnterText.resize(367, 228)
        self.verticalLayout = QtWidgets.QVBoxLayout(dlg_EnterText)
        self.verticalLayout.setObjectName("verticalLayout")
        self.l_info = QtWidgets.QLabel(dlg_EnterText)
        self.l_info.setObjectName("l_info")
        self.verticalLayout.addWidget(self.l_info)
        self.te_text = QtWidgets.QTextEdit(dlg_EnterText)
        self.te_text.setObjectName("te_text")
        self.verticalLayout.addWidget(self.te_text)
        self.buttonBox = QtWidgets.QDialogButtonBox(dlg_EnterText)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(dlg_EnterText)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), dlg_EnterText.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), dlg_EnterText.reject)
        QtCore.QMetaObject.connectSlotsByName(dlg_EnterText)

    def retranslateUi(self, dlg_EnterText):
        dlg_EnterText.setWindowTitle(QtWidgets.QApplication.translate("dlg_EnterText", "Enter Text", None, -1))
        self.l_info.setText(QtWidgets.QApplication.translate("dlg_EnterText", "Enter text:", None, -1))

