# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'SaveComment.ui'
#
# Created: Sat Apr 13 22:28:48 2019
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_dlg_SaveComment(object):
    def setupUi(self, dlg_SaveComment):
        dlg_SaveComment.setObjectName("dlg_SaveComment")
        dlg_SaveComment.resize(599, 611)
        self.verticalLayout = QtGui.QVBoxLayout(dlg_SaveComment)
        self.verticalLayout.setObjectName("verticalLayout")
        self.w_details = QtGui.QWidget(dlg_SaveComment)
        self.w_details.setObjectName("w_details")
        self.gridLayout = QtGui.QGridLayout(self.w_details)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.l_preview = QtGui.QLabel(self.w_details)
        self.l_preview.setMinimumSize(QtCore.QSize(500, 281))
        self.l_preview.setAlignment(QtCore.Qt.AlignCenter)
        self.l_preview.setObjectName("l_preview")
        self.gridLayout.addWidget(self.l_preview, 4, 1, 1, 1)
        self.label = QtGui.QLabel(self.w_details)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 4, 0, 1, 1)
        self.l_comment = QtGui.QLabel(self.w_details)
        self.l_comment.setObjectName("l_comment")
        self.gridLayout.addWidget(self.l_comment, 0, 0, 1, 1)
        self.e_comment = QtGui.QLineEdit(self.w_details)
        self.e_comment.setObjectName("e_comment")
        self.gridLayout.addWidget(self.e_comment, 0, 1, 1, 1)
        self.label_2 = QtGui.QLabel(self.w_details)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 2, 0, 1, 1)
        self.e_description = QtGui.QTextEdit(self.w_details)
        self.e_description.setObjectName("e_description")
        self.gridLayout.addWidget(self.e_description, 2, 1, 1, 1)
        self.verticalLayout.addWidget(self.w_details)
        self.b_changePreview = QtGui.QPushButton(dlg_SaveComment)
        self.b_changePreview.setObjectName("b_changePreview")
        self.verticalLayout.addWidget(self.b_changePreview)
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
        dlg_SaveComment.setTabOrder(self.e_comment, self.e_description)

    def retranslateUi(self, dlg_SaveComment):
        dlg_SaveComment.setWindowTitle(QtGui.QApplication.translate("dlg_SaveComment", "Save with Comment", None, QtGui.QApplication.UnicodeUTF8))
        self.l_preview.setText(QtGui.QApplication.translate("dlg_SaveComment", "Preview", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("dlg_SaveComment", "Preview:", None, QtGui.QApplication.UnicodeUTF8))
        self.l_comment.setText(QtGui.QApplication.translate("dlg_SaveComment", "Comment:", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("dlg_SaveComment", "Description:", None, QtGui.QApplication.UnicodeUTF8))
        self.b_changePreview.setText(QtGui.QApplication.translate("dlg_SaveComment", "Change preview", None, QtGui.QApplication.UnicodeUTF8))

