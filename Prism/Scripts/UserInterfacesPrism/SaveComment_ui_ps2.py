# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'SaveComment.ui',
# licensing of 'SaveComment.ui' applies.
#
# Created: Sat Apr 13 22:28:48 2019
#      by: pyside2-uic  running on PySide2 5.9.0a1.dev1528389443
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_dlg_SaveComment(object):
    def setupUi(self, dlg_SaveComment):
        dlg_SaveComment.setObjectName("dlg_SaveComment")
        dlg_SaveComment.resize(599, 611)
        self.verticalLayout = QtWidgets.QVBoxLayout(dlg_SaveComment)
        self.verticalLayout.setObjectName("verticalLayout")
        self.w_details = QtWidgets.QWidget(dlg_SaveComment)
        self.w_details.setObjectName("w_details")
        self.gridLayout = QtWidgets.QGridLayout(self.w_details)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.l_preview = QtWidgets.QLabel(self.w_details)
        self.l_preview.setMinimumSize(QtCore.QSize(500, 281))
        self.l_preview.setAlignment(QtCore.Qt.AlignCenter)
        self.l_preview.setObjectName("l_preview")
        self.gridLayout.addWidget(self.l_preview, 4, 1, 1, 1)
        self.label = QtWidgets.QLabel(self.w_details)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 4, 0, 1, 1)
        self.l_comment = QtWidgets.QLabel(self.w_details)
        self.l_comment.setObjectName("l_comment")
        self.gridLayout.addWidget(self.l_comment, 0, 0, 1, 1)
        self.e_comment = QtWidgets.QLineEdit(self.w_details)
        self.e_comment.setObjectName("e_comment")
        self.gridLayout.addWidget(self.e_comment, 0, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.w_details)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 2, 0, 1, 1)
        self.e_description = QtWidgets.QTextEdit(self.w_details)
        self.e_description.setObjectName("e_description")
        self.gridLayout.addWidget(self.e_description, 2, 1, 1, 1)
        self.verticalLayout.addWidget(self.w_details)
        self.b_changePreview = QtWidgets.QPushButton(dlg_SaveComment)
        self.b_changePreview.setObjectName("b_changePreview")
        self.verticalLayout.addWidget(self.b_changePreview)
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
        dlg_SaveComment.setTabOrder(self.e_comment, self.e_description)

    def retranslateUi(self, dlg_SaveComment):
        dlg_SaveComment.setWindowTitle(QtWidgets.QApplication.translate("dlg_SaveComment", "Save with Comment", None, -1))
        self.l_preview.setText(QtWidgets.QApplication.translate("dlg_SaveComment", "Preview", None, -1))
        self.label.setText(QtWidgets.QApplication.translate("dlg_SaveComment", "Preview:", None, -1))
        self.l_comment.setText(QtWidgets.QApplication.translate("dlg_SaveComment", "Comment:", None, -1))
        self.label_2.setText(QtWidgets.QApplication.translate("dlg_SaveComment", "Description:", None, -1))
        self.b_changePreview.setText(QtWidgets.QApplication.translate("dlg_SaveComment", "Change preview", None, -1))

