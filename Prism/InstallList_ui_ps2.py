# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'InstallList.ui'
#
# Created: Tue Aug 14 22:47:54 2018
#      by: pyside2-uic @pyside_tools_VERSION@ running on PySide2 2.0.0~alpha0
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_dlg_InstallList(object):
    def setupUi(self, dlg_InstallList):
        dlg_InstallList.setObjectName("dlg_InstallList")
        dlg_InstallList.resize(843, 635)
        self.verticalLayout = QtWidgets.QVBoxLayout(dlg_InstallList)
        self.verticalLayout.setContentsMargins(-1, 15, -1, -1)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(dlg_InstallList)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.label_3 = QtWidgets.QLabel(dlg_InstallList)
        self.label_3.setObjectName("label_3")
        self.verticalLayout.addWidget(self.label_3)
        spacerItem = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.verticalLayout.addItem(spacerItem)
        self.tw_components = QtWidgets.QTreeWidget(dlg_InstallList)
        self.tw_components.setMinimumSize(QtCore.QSize(0, 450))
        self.tw_components.setObjectName("tw_components")
        self.tw_components.header().setVisible(False)
        self.tw_components.header().setDefaultSectionSize(200)
        self.verticalLayout.addWidget(self.tw_components)
        self.widget = QtWidgets.QWidget(dlg_InstallList)
        self.widget.setObjectName("widget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget)
        self.horizontalLayout.setContentsMargins(0, -1, 0, -1)
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.label_2 = QtWidgets.QLabel(self.widget)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.cb_users = QtWidgets.QComboBox(self.widget)
        self.cb_users.setMinimumSize(QtCore.QSize(300, 0))
        self.cb_users.setMaximumSize(QtCore.QSize(300, 16777215))
        self.cb_users.setObjectName("cb_users")
        self.horizontalLayout.addWidget(self.cb_users)
        self.verticalLayout.addWidget(self.widget)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem2)
        self.buttonBox = QtWidgets.QDialogButtonBox(dlg_InstallList)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(dlg_InstallList)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), dlg_InstallList.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), dlg_InstallList.reject)
        QtCore.QMetaObject.connectSlotsByName(dlg_InstallList)

    def retranslateUi(self, dlg_InstallList):
        dlg_InstallList.setWindowTitle(QtWidgets.QApplication.translate("dlg_InstallList", "Select Programs", None, -1))
        self.label.setText(QtWidgets.QApplication.translate("dlg_InstallList", "Please select the components you want to install:", None, -1))
        self.label_3.setText(QtWidgets.QApplication.translate("dlg_InstallList", "(Integrations can also  be added and removed later in the Prism settings)", None, -1))
        self.tw_components.headerItem().setText(0, QtWidgets.QApplication.translate("dlg_InstallList", "programm", None, -1))
        self.tw_components.headerItem().setText(1, QtWidgets.QApplication.translate("dlg_InstallList", "paths", None, -1))
        self.label_2.setText(QtWidgets.QApplication.translate("dlg_InstallList", "Install for user:", None, -1))

