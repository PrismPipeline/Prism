# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'SaveComment.ui'
#
# Created: Thu Feb 23 13:32:33 2017
#      by: pyside2-uic @pyside_tools_VERSION@ running on PySide2 2.0.0~alpha0
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_dlg_SaveComment(object):
    def setupUi(self, dlg_SaveComment):
        dlg_SaveComment.setObjectName("dlg_SaveComment")
        dlg_SaveComment.resize(260, 75)
        self.verticalLayout = QtWidgets.QVBoxLayout(dlg_SaveComment)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.l_comment = QtWidgets.QLabel(dlg_SaveComment)
        self.l_comment.setObjectName("l_comment")
        self.horizontalLayout.addWidget(self.l_comment)
        self.e_comment = QtWidgets.QLineEdit(dlg_SaveComment)
        self.e_comment.setObjectName("e_comment")
        self.horizontalLayout.addWidget(self.e_comment)
        self.verticalLayout.addLayout(self.horizontalLayout)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.buttonBox = QtWidgets.QDialogButtonBox(dlg_SaveComment)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(dlg_SaveComment)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), dlg_SaveComment.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), dlg_SaveComment.reject)
        QtCore.QMetaObject.connectSlotsByName(dlg_SaveComment)

    def retranslateUi(self, dlg_SaveComment):
        dlg_SaveComment.setWindowTitle(QtWidgets.QApplication.translate("dlg_SaveComment", "Save with Comment", None, -1))
        self.l_comment.setText(QtWidgets.QApplication.translate("dlg_SaveComment", "Comment:", None, -1))

