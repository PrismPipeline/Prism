# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'PrismInstaller.ui'
#
# Created: Mon Sep 21 20:34:16 2020
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_dlg_installer(object):
    def setupUi(self, dlg_installer):
        dlg_installer.setObjectName("dlg_installer")
        dlg_installer.resize(680, 720)
        self.verticalLayout = QtGui.QVBoxLayout(dlg_installer)
        self.verticalLayout.setContentsMargins(-1, 15, -1, -1)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtGui.QLabel(dlg_installer)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.tw_components = QtGui.QTreeWidget(dlg_installer)
        self.tw_components.setMinimumSize(QtCore.QSize(0, 100))
        self.tw_components.setObjectName("tw_components")
        self.tw_components.header().setVisible(False)
        self.tw_components.header().setDefaultSectionSize(200)
        self.verticalLayout.addWidget(self.tw_components)
        spacerItem = QtGui.QSpacerItem(20, 10, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        self.verticalLayout.addItem(spacerItem)
        self.buttonBox = QtGui.QDialogButtonBox(dlg_installer)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(dlg_installer)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), dlg_installer.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), dlg_installer.reject)
        QtCore.QMetaObject.connectSlotsByName(dlg_installer)

    def retranslateUi(self, dlg_installer):
        dlg_installer.setWindowTitle(QtGui.QApplication.translate("dlg_installer", "Setup Prism integrations", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("dlg_installer", "Please select the integrations you want to install:", None, QtGui.QApplication.UnicodeUTF8))
        self.tw_components.headerItem().setText(0, QtGui.QApplication.translate("dlg_installer", "programm", None, QtGui.QApplication.UnicodeUTF8))
        self.tw_components.headerItem().setText(1, QtGui.QApplication.translate("dlg_installer", "paths", None, QtGui.QApplication.UnicodeUTF8))

