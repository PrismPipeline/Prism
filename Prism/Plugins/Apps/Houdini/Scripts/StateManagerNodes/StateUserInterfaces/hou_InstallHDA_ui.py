# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'hou_InstallHDA.ui'
#
# Created: Tue Mar  7 11:17:50 2023
#      by: qtpy-uic 2.0.5
#
# WARNING! All changes made in this file will be lost!

from qtpy import QtCore, QtGui, QtWidgets

class Ui_wg_InstallHDA(object):
    def setupUi(self, wg_InstallHDA):
        wg_InstallHDA.setObjectName("wg_InstallHDA")
        wg_InstallHDA.resize(340, 241)
        self.verticalLayout = QtWidgets.QVBoxLayout(wg_InstallHDA)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget_4 = QtWidgets.QWidget(wg_InstallHDA)
        self.widget_4.setObjectName("widget_4")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.widget_4)
        self.horizontalLayout_2.setContentsMargins(-1, 0, 18, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.l_name = QtWidgets.QLabel(self.widget_4)
        self.l_name.setObjectName("l_name")
        self.horizontalLayout_2.addWidget(self.l_name)
        self.e_name = QtWidgets.QLineEdit(self.widget_4)
        self.e_name.setMinimumSize(QtCore.QSize(0, 0))
        self.e_name.setMaximumSize(QtCore.QSize(9999, 16777215))
        self.e_name.setObjectName("e_name")
        self.horizontalLayout_2.addWidget(self.e_name)
        self.l_class = QtWidgets.QLabel(self.widget_4)
        font = QtGui.QFont()
        font.setWeight(75)
        font.setBold(True)
        self.l_class.setFont(font)
        self.l_class.setObjectName("l_class")
        self.horizontalLayout_2.addWidget(self.l_class)
        self.verticalLayout.addWidget(self.widget_4)
        self.gb_import = QtWidgets.QGroupBox(wg_InstallHDA)
        self.gb_import.setObjectName("gb_import")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.gb_import)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.groupBox = QtWidgets.QGroupBox(self.gb_import)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.groupBox)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.w_currentVersion = QtWidgets.QWidget(self.groupBox)
        self.w_currentVersion.setObjectName("w_currentVersion")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.w_currentVersion)
        self.horizontalLayout_5.setContentsMargins(-1, 0, -1, 0)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.label_3 = QtWidgets.QLabel(self.w_currentVersion)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_5.addWidget(self.label_3)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem)
        self.l_curVersion = QtWidgets.QLabel(self.w_currentVersion)
        self.l_curVersion.setObjectName("l_curVersion")
        self.horizontalLayout_5.addWidget(self.l_curVersion)
        self.verticalLayout_3.addWidget(self.w_currentVersion)
        self.w_latestVersion = QtWidgets.QWidget(self.groupBox)
        self.w_latestVersion.setObjectName("w_latestVersion")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout(self.w_latestVersion)
        self.horizontalLayout_6.setContentsMargins(-1, 0, -1, 0)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.label_6 = QtWidgets.QLabel(self.w_latestVersion)
        self.label_6.setObjectName("label_6")
        self.horizontalLayout_6.addWidget(self.label_6)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_6.addItem(spacerItem1)
        self.l_latestVersion = QtWidgets.QLabel(self.w_latestVersion)
        self.l_latestVersion.setObjectName("l_latestVersion")
        self.horizontalLayout_6.addWidget(self.l_latestVersion)
        self.verticalLayout_3.addWidget(self.w_latestVersion)
        self.w_autoUpdate = QtWidgets.QWidget(self.groupBox)
        self.w_autoUpdate.setObjectName("w_autoUpdate")
        self.horizontalLayout_14 = QtWidgets.QHBoxLayout(self.w_autoUpdate)
        self.horizontalLayout_14.setContentsMargins(9, 0, 9, 0)
        self.horizontalLayout_14.setObjectName("horizontalLayout_14")
        self.l_autoUpdate = QtWidgets.QLabel(self.w_autoUpdate)
        self.l_autoUpdate.setObjectName("l_autoUpdate")
        self.horizontalLayout_14.addWidget(self.l_autoUpdate)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_14.addItem(spacerItem2)
        self.chb_autoUpdate = QtWidgets.QCheckBox(self.w_autoUpdate)
        self.chb_autoUpdate.setText("")
        self.chb_autoUpdate.setChecked(False)
        self.chb_autoUpdate.setObjectName("chb_autoUpdate")
        self.horizontalLayout_14.addWidget(self.chb_autoUpdate)
        self.verticalLayout_3.addWidget(self.w_autoUpdate)
        self.w_importLatest = QtWidgets.QWidget(self.groupBox)
        self.w_importLatest.setObjectName("w_importLatest")
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout(self.w_importLatest)
        self.horizontalLayout_7.setContentsMargins(-1, 0, -1, 0)
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.b_browse = QtWidgets.QPushButton(self.w_importLatest)
        self.b_browse.setFocusPolicy(QtCore.Qt.NoFocus)
        self.b_browse.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.b_browse.setObjectName("b_browse")
        self.horizontalLayout_7.addWidget(self.b_browse)
        self.b_importLatest = QtWidgets.QPushButton(self.w_importLatest)
        self.b_importLatest.setMinimumSize(QtCore.QSize(0, 0))
        self.b_importLatest.setMaximumSize(QtCore.QSize(99999, 16777215))
        self.b_importLatest.setFocusPolicy(QtCore.Qt.NoFocus)
        self.b_importLatest.setObjectName("b_importLatest")
        self.horizontalLayout_7.addWidget(self.b_importLatest)
        self.verticalLayout_3.addWidget(self.w_importLatest)
        self.verticalLayout_2.addWidget(self.groupBox)
        self.widget_3 = QtWidgets.QWidget(self.gb_import)
        self.widget_3.setObjectName("widget_3")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.widget_3)
        self.horizontalLayout_4.setContentsMargins(-1, 0, -1, 0)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.label = QtWidgets.QLabel(self.widget_3)
        self.label.setMinimumSize(QtCore.QSize(40, 0))
        self.label.setMaximumSize(QtCore.QSize(40, 16777215))
        self.label.setObjectName("label")
        self.horizontalLayout_4.addWidget(self.label)
        self.l_status = QtWidgets.QLabel(self.widget_3)
        self.l_status.setAlignment(QtCore.Qt.AlignCenter)
        self.l_status.setObjectName("l_status")
        self.horizontalLayout_4.addWidget(self.l_status)
        self.verticalLayout_2.addWidget(self.widget_3)
        self.widget_2 = QtWidgets.QWidget(self.gb_import)
        self.widget_2.setObjectName("widget_2")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.widget_2)
        self.horizontalLayout_3.setContentsMargins(-1, 0, -1, 0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.b_import = QtWidgets.QPushButton(self.widget_2)
        self.b_import.setFocusPolicy(QtCore.Qt.NoFocus)
        self.b_import.setObjectName("b_import")
        self.horizontalLayout_3.addWidget(self.b_import)
        self.b_createNode = QtWidgets.QPushButton(self.widget_2)
        self.b_createNode.setFocusPolicy(QtCore.Qt.NoFocus)
        self.b_createNode.setObjectName("b_createNode")
        self.horizontalLayout_3.addWidget(self.b_createNode)
        self.verticalLayout_2.addWidget(self.widget_2)
        self.verticalLayout.addWidget(self.gb_import)

        self.retranslateUi(wg_InstallHDA)
        QtCore.QMetaObject.connectSlotsByName(wg_InstallHDA)

    def retranslateUi(self, wg_InstallHDA):
        wg_InstallHDA.setWindowTitle(QtWidgets.QApplication.translate("", "ImportFile", None, -1))
        self.l_name.setText(QtWidgets.QApplication.translate("", "Name:", None, -1))
        self.l_class.setText(QtWidgets.QApplication.translate("", "Install HDA", None, -1))
        self.gb_import.setTitle(QtWidgets.QApplication.translate("", "Import", None, -1))
        self.groupBox.setTitle(QtWidgets.QApplication.translate("", "Version", None, -1))
        self.label_3.setText(QtWidgets.QApplication.translate("", "Current Version:", None, -1))
        self.l_curVersion.setText(QtWidgets.QApplication.translate("", "-", None, -1))
        self.label_6.setText(QtWidgets.QApplication.translate("", "Latest Version:", None, -1))
        self.l_latestVersion.setText(QtWidgets.QApplication.translate("", "-", None, -1))
        self.l_autoUpdate.setText(QtWidgets.QApplication.translate("", "Auto load latest version:", None, -1))
        self.b_browse.setText(QtWidgets.QApplication.translate("", "Browse", None, -1))
        self.b_importLatest.setText(QtWidgets.QApplication.translate("", "Install latest Version", None, -1))
        self.label.setText(QtWidgets.QApplication.translate("", "Status:", None, -1))
        self.l_status.setText(QtWidgets.QApplication.translate("", "Not found in scene", None, -1))
        self.b_import.setText(QtWidgets.QApplication.translate("", "Re-Install", None, -1))
        self.b_createNode.setText(QtWidgets.QApplication.translate("", "Create Node", None, -1))

