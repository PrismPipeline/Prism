# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'hou_SaveHDA.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from qtpy.QtCore import *  # type: ignore
from qtpy.QtGui import *  # type: ignore
from qtpy.QtWidgets import *  # type: ignore

class Ui_wg_SaveHDA(object):
    def setupUi(self, wg_SaveHDA):
        if not wg_SaveHDA.objectName():
            wg_SaveHDA.setObjectName(u"wg_SaveHDA")
        wg_SaveHDA.resize(340, 421)
        self.verticalLayout = QVBoxLayout(wg_SaveHDA)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.widget_4 = QWidget(wg_SaveHDA)
        self.widget_4.setObjectName(u"widget_4")
        self.horizontalLayout_2 = QHBoxLayout(self.widget_4)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(-1, 0, 18, 0)
        self.l_name = QLabel(self.widget_4)
        self.l_name.setObjectName(u"l_name")

        self.horizontalLayout_2.addWidget(self.l_name)

        self.e_name = QLineEdit(self.widget_4)
        self.e_name.setObjectName(u"e_name")
        self.e_name.setMinimumSize(QSize(0, 0))
        self.e_name.setMaximumSize(QSize(9999, 16777215))

        self.horizontalLayout_2.addWidget(self.e_name)

        self.l_class = QLabel(self.widget_4)
        self.l_class.setObjectName(u"l_class")
        font = QFont()
        font.setBold(True)
        self.l_class.setFont(font)

        self.horizontalLayout_2.addWidget(self.l_class)


        self.verticalLayout.addWidget(self.widget_4)

        self.groupBox_2 = QGroupBox(wg_SaveHDA)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.verticalLayout_3 = QVBoxLayout(self.groupBox_2)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.w_comment = QWidget(self.groupBox_2)
        self.w_comment.setObjectName(u"w_comment")
        self.horizontalLayout_25 = QHBoxLayout(self.w_comment)
        self.horizontalLayout_25.setSpacing(0)
        self.horizontalLayout_25.setObjectName(u"horizontalLayout_25")
        self.horizontalLayout_25.setContentsMargins(9, 0, 9, 0)
        self.l_comment = QLabel(self.w_comment)
        self.l_comment.setObjectName(u"l_comment")
        self.l_comment.setMinimumSize(QSize(40, 0))
        self.l_comment.setMaximumSize(QSize(95, 16777215))

        self.horizontalLayout_25.addWidget(self.l_comment)

        self.horizontalSpacer_8 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_25.addItem(self.horizontalSpacer_8)

        self.e_comment = QLineEdit(self.w_comment)
        self.e_comment.setObjectName(u"e_comment")

        self.horizontalLayout_25.addWidget(self.e_comment)


        self.verticalLayout_3.addWidget(self.w_comment)

        self.f_taskName = QWidget(self.groupBox_2)
        self.f_taskName.setObjectName(u"f_taskName")
        self.horizontalLayout_11 = QHBoxLayout(self.f_taskName)
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.horizontalLayout_11.setContentsMargins(-1, 0, -1, 0)
        self.l_tasklabel = QLabel(self.f_taskName)
        self.l_tasklabel.setObjectName(u"l_tasklabel")

        self.horizontalLayout_11.addWidget(self.l_tasklabel)

        self.l_taskName = QLabel(self.f_taskName)
        self.l_taskName.setObjectName(u"l_taskName")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.l_taskName.sizePolicy().hasHeightForWidth())
        self.l_taskName.setSizePolicy(sizePolicy)
        self.l_taskName.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout_11.addWidget(self.l_taskName)

        self.b_changeTask = QPushButton(self.f_taskName)
        self.b_changeTask.setObjectName(u"b_changeTask")
        self.b_changeTask.setEnabled(True)
        self.b_changeTask.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.horizontalLayout_11.addWidget(self.b_changeTask)


        self.verticalLayout_3.addWidget(self.f_taskName)

        self.w_outPath = QWidget(self.groupBox_2)
        self.w_outPath.setObjectName(u"w_outPath")
        self.horizontalLayout_12 = QHBoxLayout(self.w_outPath)
        self.horizontalLayout_12.setSpacing(0)
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.horizontalLayout_12.setContentsMargins(9, 0, 9, 0)
        self.l_outPath = QLabel(self.w_outPath)
        self.l_outPath.setObjectName(u"l_outPath")

        self.horizontalLayout_12.addWidget(self.l_outPath)

        self.horizontalSpacer_6 = QSpacerItem(113, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_12.addItem(self.horizontalSpacer_6)

        self.cb_outPath = QComboBox(self.w_outPath)
        self.cb_outPath.setObjectName(u"cb_outPath")
        self.cb_outPath.setMinimumSize(QSize(124, 0))

        self.horizontalLayout_12.addWidget(self.cb_outPath)


        self.verticalLayout_3.addWidget(self.w_outPath)

        self.w_projectHDA = QWidget(self.groupBox_2)
        self.w_projectHDA.setObjectName(u"w_projectHDA")
        self.horizontalLayout_19 = QHBoxLayout(self.w_projectHDA)
        self.horizontalLayout_19.setObjectName(u"horizontalLayout_19")
        self.horizontalLayout_19.setContentsMargins(-1, 0, -1, 0)
        self.l_projectHDA = QLabel(self.w_projectHDA)
        self.l_projectHDA.setObjectName(u"l_projectHDA")

        self.horizontalLayout_19.addWidget(self.l_projectHDA)

        self.horizontalSpacer_14 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_19.addItem(self.horizontalSpacer_14)

        self.chb_projectHDA = QCheckBox(self.w_projectHDA)
        self.chb_projectHDA.setObjectName(u"chb_projectHDA")

        self.horizontalLayout_19.addWidget(self.chb_projectHDA)


        self.verticalLayout_3.addWidget(self.w_projectHDA)

        self.w_externalReferences = QWidget(self.groupBox_2)
        self.w_externalReferences.setObjectName(u"w_externalReferences")
        self.horizontalLayout_20 = QHBoxLayout(self.w_externalReferences)
        self.horizontalLayout_20.setObjectName(u"horizontalLayout_20")
        self.horizontalLayout_20.setContentsMargins(-1, 0, -1, 0)
        self.l_externalReferences = QLabel(self.w_externalReferences)
        self.l_externalReferences.setObjectName(u"l_externalReferences")

        self.horizontalLayout_20.addWidget(self.l_externalReferences)

        self.horizontalSpacer_23 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_20.addItem(self.horizontalSpacer_23)

        self.chb_externalReferences = QCheckBox(self.w_externalReferences)
        self.chb_externalReferences.setObjectName(u"chb_externalReferences")

        self.horizontalLayout_20.addWidget(self.chb_externalReferences)


        self.verticalLayout_3.addWidget(self.w_externalReferences)

        self.w_blackboxHDA = QWidget(self.groupBox_2)
        self.w_blackboxHDA.setObjectName(u"w_blackboxHDA")
        self.horizontalLayout_18 = QHBoxLayout(self.w_blackboxHDA)
        self.horizontalLayout_18.setObjectName(u"horizontalLayout_18")
        self.horizontalLayout_18.setContentsMargins(-1, 0, -1, 0)
        self.l_blackboxHDA = QLabel(self.w_blackboxHDA)
        self.l_blackboxHDA.setObjectName(u"l_blackboxHDA")

        self.horizontalLayout_18.addWidget(self.l_blackboxHDA)

        self.horizontalSpacer_12 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_18.addItem(self.horizontalSpacer_12)

        self.chb_blackboxHDA = QCheckBox(self.w_blackboxHDA)
        self.chb_blackboxHDA.setObjectName(u"chb_blackboxHDA")

        self.horizontalLayout_18.addWidget(self.chb_blackboxHDA)


        self.verticalLayout_3.addWidget(self.w_blackboxHDA)

        self.w_recipe = QWidget(self.groupBox_2)
        self.w_recipe.setObjectName(u"w_recipe")
        self.horizontalLayout_21 = QHBoxLayout(self.w_recipe)
        self.horizontalLayout_21.setObjectName(u"horizontalLayout_21")
        self.horizontalLayout_21.setContentsMargins(-1, 0, -1, 0)
        self.l_recipe = QLabel(self.w_recipe)
        self.l_recipe.setObjectName(u"l_recipe")

        self.horizontalLayout_21.addWidget(self.l_recipe)

        self.horizontalSpacer_13 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_21.addItem(self.horizontalSpacer_13)

        self.chb_recipe = QCheckBox(self.w_recipe)
        self.chb_recipe.setObjectName(u"chb_recipe")

        self.horizontalLayout_21.addWidget(self.chb_recipe)


        self.verticalLayout_3.addWidget(self.w_recipe)

        self.f_status = QWidget(self.groupBox_2)
        self.f_status.setObjectName(u"f_status")
        self.horizontalLayout_4 = QHBoxLayout(self.f_status)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(-1, 0, -1, 0)
        self.label = QLabel(self.f_status)
        self.label.setObjectName(u"label")
        self.label.setMinimumSize(QSize(40, 0))
        self.label.setMaximumSize(QSize(40, 16777215))

        self.horizontalLayout_4.addWidget(self.label)

        self.l_status = QLabel(self.f_status)
        self.l_status.setObjectName(u"l_status")
        self.l_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout_4.addWidget(self.l_status)

        self.b_goTo = QPushButton(self.f_status)
        self.b_goTo.setObjectName(u"b_goTo")
        self.b_goTo.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.horizontalLayout_4.addWidget(self.b_goTo)


        self.verticalLayout_3.addWidget(self.f_status)

        self.f_connect = QWidget(self.groupBox_2)
        self.f_connect.setObjectName(u"f_connect")
        self.horizontalLayout_3 = QHBoxLayout(self.f_connect)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(-1, 0, -1, 0)
        self.b_connect = QPushButton(self.f_connect)
        self.b_connect.setObjectName(u"b_connect")
        self.b_connect.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.horizontalLayout_3.addWidget(self.b_connect)


        self.verticalLayout_3.addWidget(self.f_connect)


        self.verticalLayout.addWidget(self.groupBox_2)

        self.gb_previous = QGroupBox(wg_SaveHDA)
        self.gb_previous.setObjectName(u"gb_previous")
        self.gb_previous.setCheckable(False)
        self.gb_previous.setChecked(False)
        self.horizontalLayout = QHBoxLayout(self.gb_previous)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(18, -1, 18, -1)
        self.scrollArea = QScrollArea(self.gb_previous)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 271, 69))
        self.horizontalLayout_5 = QHBoxLayout(self.scrollAreaWidgetContents)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.l_pathLast = QLabel(self.scrollAreaWidgetContents)
        self.l_pathLast.setObjectName(u"l_pathLast")

        self.horizontalLayout_5.addWidget(self.l_pathLast)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.horizontalLayout.addWidget(self.scrollArea)

        self.b_pathLast = QToolButton(self.gb_previous)
        self.b_pathLast.setObjectName(u"b_pathLast")
        self.b_pathLast.setEnabled(True)
        self.b_pathLast.setArrowType(Qt.ArrowType.DownArrow)

        self.horizontalLayout.addWidget(self.b_pathLast)


        self.verticalLayout.addWidget(self.gb_previous)

        QWidget.setTabOrder(self.e_name, self.cb_outPath)
        QWidget.setTabOrder(self.cb_outPath, self.chb_projectHDA)
        QWidget.setTabOrder(self.chb_projectHDA, self.chb_externalReferences)
        QWidget.setTabOrder(self.chb_externalReferences, self.chb_blackboxHDA)
        QWidget.setTabOrder(self.chb_blackboxHDA, self.scrollArea)
        QWidget.setTabOrder(self.scrollArea, self.b_pathLast)

        self.retranslateUi(wg_SaveHDA)

        QMetaObject.connectSlotsByName(wg_SaveHDA)
    # setupUi

    def retranslateUi(self, wg_SaveHDA):
        wg_SaveHDA.setWindowTitle(QCoreApplication.translate("wg_SaveHDA", u"Export", None))
        self.l_name.setText(QCoreApplication.translate("wg_SaveHDA", u"Name:", None))
        self.l_class.setText(QCoreApplication.translate("wg_SaveHDA", u"Save HDA", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("wg_SaveHDA", u"General", None))
        self.l_comment.setText(QCoreApplication.translate("wg_SaveHDA", u"Comment:", None))
        self.l_tasklabel.setText(QCoreApplication.translate("wg_SaveHDA", u"Productname:", None))
        self.l_taskName.setText("")
        self.b_changeTask.setText(QCoreApplication.translate("wg_SaveHDA", u"change", None))
        self.l_outPath.setText(QCoreApplication.translate("wg_SaveHDA", u"Outputpath:", None))
        self.l_projectHDA.setText(QCoreApplication.translate("wg_SaveHDA", u"Save as project HDA:", None))
        self.chb_projectHDA.setText("")
        self.l_externalReferences.setText(QCoreApplication.translate("wg_SaveHDA", u"Allow external references", None))
        self.chb_externalReferences.setText("")
        self.l_blackboxHDA.setText(QCoreApplication.translate("wg_SaveHDA", u"Create Blackbox:", None))
        self.chb_blackboxHDA.setText("")
        self.l_recipe.setText(QCoreApplication.translate("wg_SaveHDA", u"Save as Tool Recipe:", None))
        self.chb_recipe.setText("")
        self.label.setText(QCoreApplication.translate("wg_SaveHDA", u"Status:", None))
        self.l_status.setText(QCoreApplication.translate("wg_SaveHDA", u"Not connected", None))
        self.b_goTo.setText(QCoreApplication.translate("wg_SaveHDA", u"Go to Node", None))
        self.b_connect.setText(QCoreApplication.translate("wg_SaveHDA", u"Connect with selected Node", None))
        self.gb_previous.setTitle(QCoreApplication.translate("wg_SaveHDA", u"Last export", None))
        self.l_pathLast.setText(QCoreApplication.translate("wg_SaveHDA", u"None", None))
        self.b_pathLast.setText(QCoreApplication.translate("wg_SaveHDA", u"...", None))
    # retranslateUi

