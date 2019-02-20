# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'CombineMedia.ui'
#
# Created: Sun Feb 17 23:21:47 2019
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_dlg_CombineMedia(object):
    def setupUi(self, dlg_CombineMedia):
        dlg_CombineMedia.setObjectName("dlg_CombineMedia")
        dlg_CombineMedia.resize(653, 117)
        self.verticalLayout = QtGui.QVBoxLayout(dlg_CombineMedia)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget = QtGui.QWidget(dlg_CombineMedia)
        self.widget.setObjectName("widget")
        self.gridLayout = QtGui.QGridLayout(self.widget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.b_tasks = QtGui.QPushButton(self.widget)
        self.b_tasks.setObjectName("b_tasks")
        self.gridLayout.addWidget(self.b_tasks, 1, 3, 1, 1)
        self.e_output = QtGui.QLineEdit(self.widget)
        self.e_output.setObjectName("e_output")
        self.gridLayout.addWidget(self.e_output, 0, 2, 1, 1)
        self.b_browse = QtGui.QPushButton(self.widget)
        self.b_browse.setObjectName("b_browse")
        self.gridLayout.addWidget(self.b_browse, 0, 3, 1, 1)
        self.label = QtGui.QLabel(self.widget)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.e_task = QtGui.QLineEdit(self.widget)
        self.e_task.setObjectName("e_task")
        self.gridLayout.addWidget(self.e_task, 1, 2, 1, 1)
        self.l_task = QtGui.QLabel(self.widget)
        self.l_task.setObjectName("l_task")
        self.gridLayout.addWidget(self.l_task, 1, 0, 1, 1)
        self.chb_task = QtGui.QCheckBox(self.widget)
        self.chb_task.setText("")
        self.chb_task.setChecked(True)
        self.chb_task.setObjectName("chb_task")
        self.gridLayout.addWidget(self.chb_task, 1, 1, 1, 1)
        self.verticalLayout.addWidget(self.widget)
        self.bb_combine = QtGui.QDialogButtonBox(dlg_CombineMedia)
        self.bb_combine.setOrientation(QtCore.Qt.Horizontal)
        self.bb_combine.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.bb_combine.setObjectName("bb_combine")
        self.verticalLayout.addWidget(self.bb_combine)

        self.retranslateUi(dlg_CombineMedia)
        QtCore.QObject.connect(self.bb_combine, QtCore.SIGNAL("accepted()"), dlg_CombineMedia.accept)
        QtCore.QObject.connect(self.bb_combine, QtCore.SIGNAL("rejected()"), dlg_CombineMedia.reject)
        QtCore.QMetaObject.connectSlotsByName(dlg_CombineMedia)

    def retranslateUi(self, dlg_CombineMedia):
        dlg_CombineMedia.setWindowTitle(QtGui.QApplication.translate("dlg_CombineMedia", "Combine media", None, QtGui.QApplication.UnicodeUTF8))
        self.b_tasks.setText(QtGui.QApplication.translate("dlg_CombineMedia", "▼", None, QtGui.QApplication.UnicodeUTF8))
        self.b_browse.setText(QtGui.QApplication.translate("dlg_CombineMedia", "...", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("dlg_CombineMedia", "Outputfile:", None, QtGui.QApplication.UnicodeUTF8))
        self.l_task.setText(QtGui.QApplication.translate("dlg_CombineMedia", "Create external task:", None, QtGui.QApplication.UnicodeUTF8))

