# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'SetProject.ui',
# licensing of 'SetProject.ui' applies.
#
# Created: Wed Oct 14 11:26:38 2020
#      by: pyside2-uic  running on PySide2 5.9.0a1.dev1528389443
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_dlg_setProject(object):
    def setupUi(self, dlg_setProject):
        dlg_setProject.setObjectName("dlg_setProject")
        dlg_setProject.resize(993, 607)
        self.verticalLayout = QtWidgets.QVBoxLayout(dlg_setProject)
        self.verticalLayout.setSpacing(6)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.l_project = QtWidgets.QLabel(dlg_setProject)
        self.l_project.setMinimumSize(QtCore.QSize(0, 100))
        self.l_project.setText("")
        self.l_project.setAlignment(QtCore.Qt.AlignCenter)
        self.l_project.setObjectName("l_project")
        self.verticalLayout.addWidget(self.l_project)
        self.w_setProject = QtWidgets.QWidget(dlg_setProject)
        self.w_setProject.setObjectName("w_setProject")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.w_setProject)
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setContentsMargins(9, 15, 9, 15)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.b_open = QtWidgets.QPushButton(self.w_setProject)
        self.b_open.setMinimumSize(QtCore.QSize(0, 35))
        self.b_open.setFocusPolicy(QtCore.Qt.NoFocus)
        self.b_open.setObjectName("b_open")
        self.horizontalLayout.addWidget(self.b_open)
        self.b_create = QtWidgets.QPushButton(self.w_setProject)
        self.b_create.setMinimumSize(QtCore.QSize(0, 35))
        self.b_create.setFocusPolicy(QtCore.Qt.NoFocus)
        self.b_create.setObjectName("b_create")
        self.horizontalLayout.addWidget(self.b_create)
        self.verticalLayout.addWidget(self.w_setProject)
        self.gb_recent = QtWidgets.QGroupBox(dlg_setProject)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(10)
        sizePolicy.setHeightForWidth(self.gb_recent.sizePolicy().hasHeightForWidth())
        self.gb_recent.setSizePolicy(sizePolicy)
        self.gb_recent.setMinimumSize(QtCore.QSize(0, 190))
        self.gb_recent.setObjectName("gb_recent")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.gb_recent)
        self.verticalLayout_2.setSpacing(6)
        self.verticalLayout_2.setContentsMargins(9, 18, 9, 9)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.sa_recent = QtWidgets.QScrollArea(self.gb_recent)
        self.sa_recent.setWidgetResizable(True)
        self.sa_recent.setObjectName("sa_recent")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 971, 345))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.scl_recent = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents)
        self.scl_recent.setSpacing(6)
        self.scl_recent.setContentsMargins(0, 0, 0, 0)
        self.scl_recent.setObjectName("scl_recent")
        self.sa_recent.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout_2.addWidget(self.sa_recent)
        self.verticalLayout.addWidget(self.gb_recent)
        self.w_startup = QtWidgets.QWidget(dlg_setProject)
        self.w_startup.setObjectName("w_startup")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.w_startup)
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.chb_startup = QtWidgets.QCheckBox(self.w_startup)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.chb_startup.sizePolicy().hasHeightForWidth())
        self.chb_startup.setSizePolicy(sizePolicy)
        self.chb_startup.setObjectName("chb_startup")
        self.verticalLayout_3.addWidget(self.chb_startup)
        self.verticalLayout.addWidget(self.w_startup)

        self.retranslateUi(dlg_setProject)
        QtCore.QMetaObject.connectSlotsByName(dlg_setProject)

    def retranslateUi(self, dlg_setProject):
        dlg_setProject.setWindowTitle(QtWidgets.QApplication.translate("dlg_setProject", "Set Project", None, -1))
        self.b_open.setText(QtWidgets.QApplication.translate("dlg_setProject", "Open Existing Project", None, -1))
        self.b_create.setText(QtWidgets.QApplication.translate("dlg_setProject", "Create New Project", None, -1))
        self.gb_recent.setTitle(QtWidgets.QApplication.translate("dlg_setProject", "Recent projects:", None, -1))
        self.chb_startup.setText(QtWidgets.QApplication.translate("dlg_setProject", "Open on startup", None, -1))

