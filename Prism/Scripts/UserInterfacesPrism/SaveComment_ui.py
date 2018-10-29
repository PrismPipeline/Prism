# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'SaveComment.ui'
#
# Created: Tue Jun 07 21:01:40 2016
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_dlg_SaveComment(object):
    def setupUi(self, dlg_SaveComment):
        dlg_SaveComment.setObjectName("dlg_SaveComment")
        dlg_SaveComment.resize(260, 75)
        self.verticalLayout = QtGui.QVBoxLayout(dlg_SaveComment)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.l_comment = QtGui.QLabel(dlg_SaveComment)
        self.l_comment.setObjectName("l_comment")
        self.horizontalLayout.addWidget(self.l_comment)
        self.e_comment = QtGui.QLineEdit(dlg_SaveComment)
        self.e_comment.setObjectName("e_comment")
        self.horizontalLayout.addWidget(self.e_comment)
        self.verticalLayout.addLayout(self.horizontalLayout)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.buttonBox = QtGui.QDialogButtonBox(dlg_SaveComment)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(dlg_SaveComment)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), dlg_SaveComment.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), dlg_SaveComment.reject)
        QtCore.QMetaObject.connectSlotsByName(dlg_SaveComment)

    def retranslateUi(self, dlg_SaveComment):
        dlg_SaveComment.setWindowTitle(QtGui.QApplication.translate("dlg_SaveComment", "Save with Comment", None, QtGui.QApplication.UnicodeUTF8))
        self.l_comment.setText(QtGui.QApplication.translate("dlg_SaveComment", "Comment:", None, QtGui.QApplication.UnicodeUTF8))

