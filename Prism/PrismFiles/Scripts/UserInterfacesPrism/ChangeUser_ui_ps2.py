# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ChangeUser.ui'
#
# Created: Tue Apr 11 21:44:42 2017
#      by: pyside2-uic @pyside_tools_VERSION@ running on PySide2 2.0.0~alpha0
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_dlg_ChangeUser(object):
    def setupUi(self, dlg_ChangeUser):
        dlg_ChangeUser.setObjectName("dlg_ChangeUser")
        dlg_ChangeUser.resize(308, 101)
        self.verticalLayout = QtWidgets.QVBoxLayout(dlg_ChangeUser)
        self.verticalLayout.setObjectName("verticalLayout")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.l_fname = QtWidgets.QLabel(dlg_ChangeUser)
        self.l_fname.setObjectName("l_fname")
        self.gridLayout.addWidget(self.l_fname, 0, 0, 1, 1)
        self.e_fname = QtWidgets.QLineEdit(dlg_ChangeUser)
        self.e_fname.setObjectName("e_fname")
        self.gridLayout.addWidget(self.e_fname, 0, 1, 1, 1)
        self.l_lname = QtWidgets.QLabel(dlg_ChangeUser)
        self.l_lname.setObjectName("l_lname")
        self.gridLayout.addWidget(self.l_lname, 1, 0, 1, 1)
        self.e_lname = QtWidgets.QLineEdit(dlg_ChangeUser)
        self.e_lname.setObjectName("e_lname")
        self.gridLayout.addWidget(self.e_lname, 1, 1, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
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
        dlg_ChangeUser.setWindowTitle(QtWidgets.QApplication.translate("dlg_ChangeUser", "Change User", None, -1))
        self.l_fname.setText(QtWidgets.QApplication.translate("dlg_ChangeUser", "First Name:", None, -1))
        self.l_lname.setText(QtWidgets.QApplication.translate("dlg_ChangeUser", "Last Name:", None, -1))

