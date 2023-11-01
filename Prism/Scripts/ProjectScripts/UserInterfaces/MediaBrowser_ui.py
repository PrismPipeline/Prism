# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'MediaBrowser.ui'
#
# Created: Fri Mar 17 11:44:15 2023
#      by: qtpy-uic 2.0.5
#
# WARNING! All changes made in this file will be lost!

from qtpy import QtCore, QtGui, QtWidgets

class Ui_w_mediaBrowser(object):
    def setupUi(self, w_mediaBrowser):
        w_mediaBrowser.setObjectName("w_mediaBrowser")
        w_mediaBrowser.resize(714, 393)
        self.horizontalLayout = QtWidgets.QHBoxLayout(w_mediaBrowser)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.splitter = QtWidgets.QSplitter(w_mediaBrowser)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.w_identifier = QtWidgets.QWidget(self.splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(8)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.w_identifier.sizePolicy().hasHeightForWidth())
        self.w_identifier.setSizePolicy(sizePolicy)
        self.w_identifier.setObjectName("w_identifier")
        self.verticalLayout_8 = QtWidgets.QVBoxLayout(self.w_identifier)
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_8.setObjectName("verticalLayout_8")
        self.l_identifier = QtWidgets.QLabel(self.w_identifier)
        self.l_identifier.setObjectName("l_identifier")
        self.verticalLayout_8.addWidget(self.l_identifier)
        self.lw_task = QtWidgets.QListWidget(self.w_identifier)
        self.lw_task.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.lw_task.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.lw_task.setObjectName("lw_task")
        self.verticalLayout_8.addWidget(self.lw_task)
        self.w_autoUpdate = QtWidgets.QWidget(self.w_identifier)
        self.w_autoUpdate.setObjectName("w_autoUpdate")
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout(self.w_autoUpdate)
        self.horizontalLayout_10.setSpacing(15)
        self.horizontalLayout_10.setContentsMargins(0, 5, 0, 0)
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        self.chb_autoUpdate = QtWidgets.QCheckBox(self.w_autoUpdate)
        self.chb_autoUpdate.setChecked(True)
        self.chb_autoUpdate.setObjectName("chb_autoUpdate")
        self.horizontalLayout_10.addWidget(self.chb_autoUpdate)
        self.b_refresh = QtWidgets.QPushButton(self.w_autoUpdate)
        self.b_refresh.setEnabled(False)
        self.b_refresh.setFocusPolicy(QtCore.Qt.NoFocus)
        self.b_refresh.setObjectName("b_refresh")
        self.horizontalLayout_10.addWidget(self.b_refresh)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_10.addItem(spacerItem)
        self.verticalLayout_8.addWidget(self.w_autoUpdate)
        self.w_version = QtWidgets.QWidget(self.splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(9)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.w_version.sizePolicy().hasHeightForWidth())
        self.w_version.setSizePolicy(sizePolicy)
        self.w_version.setObjectName("w_version")
        self.verticalLayout_11 = QtWidgets.QVBoxLayout(self.w_version)
        self.verticalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_11.setObjectName("verticalLayout_11")
        self.l_version = QtWidgets.QLabel(self.w_version)
        self.l_version.setObjectName("l_version")
        self.verticalLayout_11.addWidget(self.l_version)
        self.lw_version = QtWidgets.QListWidget(self.w_version)
        self.lw_version.setMaximumSize(QtCore.QSize(16777215, 9999))
        self.lw_version.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.lw_version.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.lw_version.setObjectName("lw_version")
        self.verticalLayout_11.addWidget(self.lw_version)
        self.horizontalLayout.addWidget(self.splitter)

        self.retranslateUi(w_mediaBrowser)
        QtCore.QMetaObject.connectSlotsByName(w_mediaBrowser)

    def retranslateUi(self, w_mediaBrowser):
        w_mediaBrowser.setWindowTitle(QtWidgets.QApplication.translate("", "Media Browser", None, -1))
        self.l_identifier.setText(QtWidgets.QApplication.translate("", "Identifiers:", None, -1))
        self.chb_autoUpdate.setText(QtWidgets.QApplication.translate("", "Auto update", None, -1))
        self.b_refresh.setText(QtWidgets.QApplication.translate("", "Refresh Tasks", None, -1))
        self.l_version.setText(QtWidgets.QApplication.translate("", "Versions:", None, -1))

