# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'default_Code.ui'
#
# Created: Mon Mar  6 23:25:44 2023
#      by: qtpy-uic 2.0.5
#
# WARNING! All changes made in this file will be lost!

from qtpy import QtCore, QtGui, QtWidgets

class Ui_wg_Code(object):
    def setupUi(self, wg_Code):
        wg_Code.setObjectName("wg_Code")
        wg_Code.resize(340, 384)
        self.verticalLayout = QtWidgets.QVBoxLayout(wg_Code)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.w_name = QtWidgets.QWidget(wg_Code)
        self.w_name.setObjectName("w_name")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.w_name)
        self.horizontalLayout_5.setContentsMargins(9, 0, 18, 0)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.l_name = QtWidgets.QLabel(self.w_name)
        self.l_name.setObjectName("l_name")
        self.horizontalLayout_5.addWidget(self.l_name)
        self.e_name = QtWidgets.QLineEdit(self.w_name)
        self.e_name.setMinimumSize(QtCore.QSize(0, 0))
        self.e_name.setMaximumSize(QtCore.QSize(9999, 16777215))
        self.e_name.setObjectName("e_name")
        self.horizontalLayout_5.addWidget(self.e_name)
        self.l_class = QtWidgets.QLabel(self.w_name)
        font = QtGui.QFont()
        font.setWeight(75)
        font.setBold(True)
        self.l_class.setFont(font)
        self.l_class.setObjectName("l_class")
        self.horizontalLayout_5.addWidget(self.l_class)
        self.verticalLayout.addWidget(self.w_name)
        self.gb_code = QtWidgets.QGroupBox(wg_Code)
        self.gb_code.setObjectName("gb_code")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.gb_code)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.w_presets = QtWidgets.QWidget(self.gb_code)
        self.w_presets.setObjectName("w_presets")
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout(self.w_presets)
        self.horizontalLayout_7.setSpacing(0)
        self.horizontalLayout_7.setContentsMargins(9, 0, 9, 0)
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.l_code = QtWidgets.QLabel(self.w_presets)
        self.l_code.setObjectName("l_code")
        self.horizontalLayout_7.addWidget(self.l_code)
        self.b_presets = QtWidgets.QToolButton(self.w_presets)
        self.b_presets.setArrowType(QtCore.Qt.DownArrow)
        self.b_presets.setObjectName("b_presets")
        self.horizontalLayout_7.addWidget(self.b_presets)
        self.verticalLayout_2.addWidget(self.w_presets)
        self.widget = QtWidgets.QWidget(self.gb_code)
        self.widget.setObjectName("widget")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.widget)
        self.verticalLayout_3.setContentsMargins(-1, 0, -1, 0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.te_code = QtWidgets.QPlainTextEdit(self.widget)
        self.te_code.setObjectName("te_code")
        self.verticalLayout_3.addWidget(self.te_code)
        self.verticalLayout_2.addWidget(self.widget)
        self.w_execute = QtWidgets.QWidget(self.gb_code)
        self.w_execute.setObjectName("w_execute")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.w_execute)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setContentsMargins(9, 0, 9, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.b_execute = QtWidgets.QPushButton(self.w_execute)
        self.b_execute.setFocusPolicy(QtCore.Qt.NoFocus)
        self.b_execute.setObjectName("b_execute")
        self.horizontalLayout_2.addWidget(self.b_execute)
        self.verticalLayout_2.addWidget(self.w_execute)
        self.verticalLayout.addWidget(self.gb_code)

        self.retranslateUi(wg_Code)
        QtCore.QMetaObject.connectSlotsByName(wg_Code)

    def retranslateUi(self, wg_Code):
        wg_Code.setWindowTitle(QtWidgets.QApplication.translate("", "Code", None, -1))
        self.l_name.setText(QtWidgets.QApplication.translate("", "Name:", None, -1))
        self.l_class.setText(QtWidgets.QApplication.translate("", "Code", None, -1))
        self.gb_code.setTitle(QtWidgets.QApplication.translate("", "General", None, -1))
        self.l_code.setText(QtWidgets.QApplication.translate("", "Code:", None, -1))
        self.b_presets.setText(QtWidgets.QApplication.translate("", "...", None, -1))
        self.b_execute.setText(QtWidgets.QApplication.translate("", "Execute now", None, -1))
