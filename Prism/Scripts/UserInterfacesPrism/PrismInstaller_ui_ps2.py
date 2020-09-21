# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'PrismInstaller.ui',
# licensing of 'PrismInstaller.ui' applies.
#
# Created: Mon Sep 21 20:34:16 2020
#      by: pyside2-uic  running on PySide2 5.9.0a1.dev1528389443
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_dlg_installer(object):
    def setupUi(self, dlg_installer):
        dlg_installer.setObjectName("dlg_installer")
        dlg_installer.resize(680, 720)
        self.verticalLayout = QtWidgets.QVBoxLayout(dlg_installer)
        self.verticalLayout.setContentsMargins(-1, 15, -1, -1)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(dlg_installer)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.tw_components = QtWidgets.QTreeWidget(dlg_installer)
        self.tw_components.setMinimumSize(QtCore.QSize(0, 100))
        self.tw_components.setObjectName("tw_components")
        self.tw_components.header().setVisible(False)
        self.tw_components.header().setDefaultSectionSize(200)
        self.verticalLayout.addWidget(self.tw_components)
        spacerItem = QtWidgets.QSpacerItem(20, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.verticalLayout.addItem(spacerItem)
        self.buttonBox = QtWidgets.QDialogButtonBox(dlg_installer)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(dlg_installer)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), dlg_installer.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), dlg_installer.reject)
        QtCore.QMetaObject.connectSlotsByName(dlg_installer)

    def retranslateUi(self, dlg_installer):
        dlg_installer.setWindowTitle(QtWidgets.QApplication.translate("dlg_installer", "Setup Prism integrations", None, -1))
        self.label.setText(QtWidgets.QApplication.translate("dlg_installer", "Please select the integrations you want to install:", None, -1))
        self.tw_components.headerItem().setText(0, QtWidgets.QApplication.translate("dlg_installer", "programm", None, -1))
        self.tw_components.headerItem().setText(1, QtWidgets.QApplication.translate("dlg_installer", "paths", None, -1))

