# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ChangeUser.ui'
#
# Created: Tue Mar  7 09:52:58 2023
#      by: qtpy-uic 2.0.5
#
# WARNING! All changes made in this file will be lost!

from qtpy import QtCore, QtGui, QtWidgets

class Ui_dlg_ChangeUser(object):
    def setupUi(self, dlg_ChangeUser):
        dlg_ChangeUser.setObjectName("dlg_ChangeUser")
        dlg_ChangeUser.resize(368, 73)
        self.verticalLayout = QtWidgets.QVBoxLayout(dlg_ChangeUser)
        self.verticalLayout.setObjectName("verticalLayout")
        self.w_username = QtWidgets.QWidget(dlg_ChangeUser)
        self.w_username.setObjectName("w_username")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.w_username)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.l_username = QtWidgets.QLabel(self.w_username)
        self.l_username.setObjectName("l_username")
        self.horizontalLayout.addWidget(self.l_username)
        self.e_username = QtWidgets.QLineEdit(self.w_username)
        self.e_username.setObjectName("e_username")
        self.horizontalLayout.addWidget(self.e_username)
        self.verticalLayout.addWidget(self.w_username)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.buttonBox = QtWidgets.QDialogButtonBox(dlg_ChangeUser)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(dlg_ChangeUser)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), dlg_ChangeUser.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), dlg_ChangeUser.reject)
        QtCore.QMetaObject.connectSlotsByName(dlg_ChangeUser)

    def retranslateUi(self, dlg_ChangeUser):
        dlg_ChangeUser.setWindowTitle(QtWidgets.QApplication.translate("", "Change User", None, -1))
        self.l_username.setText(QtWidgets.QApplication.translate("", "Local Username:", None, -1))

