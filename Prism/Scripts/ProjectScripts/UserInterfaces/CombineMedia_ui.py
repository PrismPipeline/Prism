# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'CombineMedia.ui'
#
# Created: Wed Mar 22 14:21:50 2023
#      by: qtpy-uic 2.0.5
#
# WARNING! All changes made in this file will be lost!

from qtpy import QtCore, QtGui, QtWidgets

class Ui_dlg_CombineMedia(object):
    def setupUi(self, dlg_CombineMedia):
        dlg_CombineMedia.setObjectName("dlg_CombineMedia")
        dlg_CombineMedia.resize(653, 117)
        self.verticalLayout = QtWidgets.QVBoxLayout(dlg_CombineMedia)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget = QtWidgets.QWidget(dlg_CombineMedia)
        self.widget.setObjectName("widget")
        self.gridLayout = QtWidgets.QGridLayout(self.widget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.b_tasks = QtWidgets.QPushButton(self.widget)
        self.b_tasks.setObjectName("b_tasks")
        self.gridLayout.addWidget(self.b_tasks, 1, 3, 1, 1)
        self.e_output = QtWidgets.QLineEdit(self.widget)
        self.e_output.setObjectName("e_output")
        self.gridLayout.addWidget(self.e_output, 0, 2, 1, 1)
        self.b_browse = QtWidgets.QPushButton(self.widget)
        self.b_browse.setObjectName("b_browse")
        self.gridLayout.addWidget(self.b_browse, 0, 3, 1, 1)
        self.label = QtWidgets.QLabel(self.widget)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.e_task = QtWidgets.QLineEdit(self.widget)
        self.e_task.setObjectName("e_task")
        self.gridLayout.addWidget(self.e_task, 1, 2, 1, 1)
        self.l_task = QtWidgets.QLabel(self.widget)
        self.l_task.setObjectName("l_task")
        self.gridLayout.addWidget(self.l_task, 1, 0, 1, 1)
        self.chb_task = QtWidgets.QCheckBox(self.widget)
        self.chb_task.setText("")
        self.chb_task.setChecked(True)
        self.chb_task.setObjectName("chb_task")
        self.gridLayout.addWidget(self.chb_task, 1, 1, 1, 1)
        self.verticalLayout.addWidget(self.widget)
        self.bb_combine = QtWidgets.QDialogButtonBox(dlg_CombineMedia)
        self.bb_combine.setOrientation(QtCore.Qt.Horizontal)
        self.bb_combine.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.bb_combine.setObjectName("bb_combine")
        self.verticalLayout.addWidget(self.bb_combine)

        self.retranslateUi(dlg_CombineMedia)
        QtCore.QObject.connect(self.bb_combine, QtCore.SIGNAL("accepted()"), dlg_CombineMedia.accept)
        QtCore.QObject.connect(self.bb_combine, QtCore.SIGNAL("rejected()"), dlg_CombineMedia.reject)
        QtCore.QMetaObject.connectSlotsByName(dlg_CombineMedia)

    def retranslateUi(self, dlg_CombineMedia):
        dlg_CombineMedia.setWindowTitle(QtWidgets.QApplication.translate("", "Combine media", None, -1))
        self.b_tasks.setText(QtWidgets.QApplication.translate("", "▼", None, -1))
        self.b_browse.setText(QtWidgets.QApplication.translate("", "...", None, -1))
        self.label.setText(QtWidgets.QApplication.translate("", "Outputfile:", None, -1))
        self.l_task.setText(QtWidgets.QApplication.translate("", "Create external task:", None, -1))

