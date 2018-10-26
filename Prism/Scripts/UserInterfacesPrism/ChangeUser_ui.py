# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ChangeUser.ui'
#
# Created: Tue Apr 11 21:44:42 2017
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_dlg_ChangeUser(object):
    def setupUi(self, dlg_ChangeUser):
        dlg_ChangeUser.setObjectName("dlg_ChangeUser")
        dlg_ChangeUser.resize(308, 101)
        self.verticalLayout = QtGui.QVBoxLayout(dlg_ChangeUser)
        self.verticalLayout.setObjectName("verticalLayout")
        self.gridLayout = QtGui.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.l_fname = QtGui.QLabel(dlg_ChangeUser)
        self.l_fname.setObjectName("l_fname")
        self.gridLayout.addWidget(self.l_fname, 0, 0, 1, 1)
        self.e_fname = QtGui.QLineEdit(dlg_ChangeUser)
        self.e_fname.setObjectName("e_fname")
        self.gridLayout.addWidget(self.e_fname, 0, 1, 1, 1)
        self.l_lname = QtGui.QLabel(dlg_ChangeUser)
        self.l_lname.setObjectName("l_lname")
        self.gridLayout.addWidget(self.l_lname, 1, 0, 1, 1)
        self.e_lname = QtGui.QLineEdit(dlg_ChangeUser)
        self.e_lname.setObjectName("e_lname")
        self.gridLayout.addWidget(self.e_lname, 1, 1, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.buttonBox = QtGui.QDialogButtonBox(dlg_ChangeUser)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(dlg_ChangeUser)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), dlg_ChangeUser.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), dlg_ChangeUser.reject)
        QtCore.QMetaObject.connectSlotsByName(dlg_ChangeUser)

    def retranslateUi(self, dlg_ChangeUser):
        dlg_ChangeUser.setWindowTitle(QtGui.QApplication.translate("dlg_ChangeUser", "Change User", None, QtGui.QApplication.UnicodeUTF8))
        self.l_fname.setText(QtGui.QApplication.translate("dlg_ChangeUser", "First Name:", None, QtGui.QApplication.UnicodeUTF8))
        self.l_lname.setText(QtGui.QApplication.translate("dlg_ChangeUser", "Last Name:", None, QtGui.QApplication.UnicodeUTF8))

