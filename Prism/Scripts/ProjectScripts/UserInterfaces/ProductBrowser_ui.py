# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ProductBrowser.ui'
#
# Created: Wed Aug  9 14:06:09 2023
#      by: qtpy-uic 2.0.5
#
# WARNING! All changes made in this file will be lost!

from qtpy import QtCore, QtGui, QtWidgets

class Ui_dlg_ProductBrowser(object):
    def setupUi(self, dlg_ProductBrowser):
        dlg_ProductBrowser.setObjectName("dlg_ProductBrowser")
        dlg_ProductBrowser.resize(1294, 696)
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(dlg_ProductBrowser)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.splitter = QtWidgets.QSplitter(dlg_ProductBrowser)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.w_tasks = QtWidgets.QWidget(self.splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(10)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.w_tasks.sizePolicy().hasHeightForWidth())
        self.w_tasks.setSizePolicy(sizePolicy)
        self.w_tasks.setObjectName("w_tasks")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.w_tasks)
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.l_identifier = QtWidgets.QLabel(self.w_tasks)
        self.l_identifier.setObjectName("l_identifier")
        self.verticalLayout_3.addWidget(self.l_identifier)
        self.tw_identifier = QtWidgets.QTreeWidget(self.w_tasks)
        self.tw_identifier.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_identifier.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tw_identifier.setIndentation(10)
        self.tw_identifier.setObjectName("tw_identifier")
        self.tw_identifier.headerItem().setText(0, "1")
        self.tw_identifier.header().setVisible(False)
        self.verticalLayout_3.addWidget(self.tw_identifier)
        self.w_versions = QtWidgets.QWidget(self.splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(30)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.w_versions.sizePolicy().hasHeightForWidth())
        self.w_versions.setSizePolicy(sizePolicy)
        self.w_versions.setObjectName("w_versions")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.w_versions)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.w_version = QtWidgets.QWidget(self.w_versions)
        self.w_version.setObjectName("w_version")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.w_version)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.l_version = QtWidgets.QLabel(self.w_version)
        self.l_version.setObjectName("l_version")
        self.horizontalLayout.addWidget(self.l_version)
        self.l_versionRight = QtWidgets.QLabel(self.w_version)
        self.l_versionRight.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.l_versionRight.setText("")
        self.l_versionRight.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.l_versionRight.setObjectName("l_versionRight")
        self.horizontalLayout.addWidget(self.l_versionRight)
        self.verticalLayout_2.addWidget(self.w_version)
        self.tw_versions = QtWidgets.QTableWidget(self.w_versions)
        self.tw_versions.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_versions.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tw_versions.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tw_versions.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tw_versions.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tw_versions.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tw_versions.setShowGrid(False)
        self.tw_versions.setObjectName("tw_versions")
        self.tw_versions.setColumnCount(0)
        self.tw_versions.setRowCount(0)
        self.tw_versions.horizontalHeader().setCascadingSectionResizes(False)
        self.tw_versions.horizontalHeader().setHighlightSections(False)
        self.tw_versions.horizontalHeader().setMinimumSectionSize(0)
        self.tw_versions.verticalHeader().setVisible(False)
        self.verticalLayout_2.addWidget(self.tw_versions)
        self.verticalLayout_4.addWidget(self.splitter)

        self.retranslateUi(dlg_ProductBrowser)
        QtCore.QMetaObject.connectSlotsByName(dlg_ProductBrowser)

    def retranslateUi(self, dlg_ProductBrowser):
        dlg_ProductBrowser.setWindowTitle(QtWidgets.QApplication.translate("", "Product Browser", None, -1))
        self.l_identifier.setText(QtWidgets.QApplication.translate("", "Products:", None, -1))
        self.l_version.setText(QtWidgets.QApplication.translate("", "Versions:", None, -1))
        self.tw_versions.setSortingEnabled(True)

