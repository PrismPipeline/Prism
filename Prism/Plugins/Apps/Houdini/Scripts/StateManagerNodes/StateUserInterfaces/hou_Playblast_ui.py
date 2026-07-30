# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'hou_Playblast.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from qtpy.QtCore import *  # type: ignore
from qtpy.QtGui import *  # type: ignore
from qtpy.QtWidgets import *  # type: ignore

class Ui_wg_Playblast(object):
    def setupUi(self, wg_Playblast):
        if not wg_Playblast.objectName():
            wg_Playblast.setObjectName(u"wg_Playblast")
        wg_Playblast.resize(389, 482)
        self.verticalLayout = QVBoxLayout(wg_Playblast)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.w_name = QWidget(wg_Playblast)
        self.w_name.setObjectName(u"w_name")
        self.horizontalLayout_4 = QHBoxLayout(self.w_name)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(-1, 0, 18, 0)
        self.l_name = QLabel(self.w_name)
        self.l_name.setObjectName(u"l_name")

        self.horizontalLayout_4.addWidget(self.l_name)

        self.e_name = QLineEdit(self.w_name)
        self.e_name.setObjectName(u"e_name")

        self.horizontalLayout_4.addWidget(self.e_name)

        self.l_class = QLabel(self.w_name)
        self.l_class.setObjectName(u"l_class")
        font = QFont()
        font.setBold(True)
        self.l_class.setFont(font)

        self.horizontalLayout_4.addWidget(self.l_class)


        self.verticalLayout.addWidget(self.w_name)

        self.gb_playblast = QGroupBox(wg_Playblast)
        self.gb_playblast.setObjectName(u"gb_playblast")
        self.verticalLayout_2 = QVBoxLayout(self.gb_playblast)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.w_comment = QWidget(self.gb_playblast)
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


        self.verticalLayout_2.addWidget(self.w_comment)

        self.widget_10 = QWidget(self.gb_playblast)
        self.widget_10.setObjectName(u"widget_10")
        self.horizontalLayout_10 = QHBoxLayout(self.widget_10)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.horizontalLayout_10.setContentsMargins(-1, 0, -1, 0)
        self.label_2 = QLabel(self.widget_10)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_10.addWidget(self.label_2)

        self.l_taskName = QLabel(self.widget_10)
        self.l_taskName.setObjectName(u"l_taskName")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.l_taskName.sizePolicy().hasHeightForWidth())
        self.l_taskName.setSizePolicy(sizePolicy)
        self.l_taskName.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout_10.addWidget(self.l_taskName)

        self.b_changeTask = QPushButton(self.widget_10)
        self.b_changeTask.setObjectName(u"b_changeTask")
        self.b_changeTask.setEnabled(True)
        self.b_changeTask.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.horizontalLayout_10.addWidget(self.b_changeTask)


        self.verticalLayout_2.addWidget(self.widget_10)

        self.widget_2 = QWidget(self.gb_playblast)
        self.widget_2.setObjectName(u"widget_2")
        self.horizontalLayout = QHBoxLayout(self.widget_2)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(9, 0, 9, 0)
        self.label_3 = QLabel(self.widget_2)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout.addWidget(self.label_3)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.cb_rangeType = QComboBox(self.widget_2)
        self.cb_rangeType.setObjectName(u"cb_rangeType")

        self.horizontalLayout.addWidget(self.cb_rangeType)


        self.verticalLayout_2.addWidget(self.widget_2)

        self.f_frameRange_2 = QWidget(self.gb_playblast)
        self.f_frameRange_2.setObjectName(u"f_frameRange_2")
        self.gridLayout = QGridLayout(self.f_frameRange_2)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(-1, 0, -1, 0)
        self.l_rangeEnd = QLabel(self.f_frameRange_2)
        self.l_rangeEnd.setObjectName(u"l_rangeEnd")
        self.l_rangeEnd.setMinimumSize(QSize(30, 0))
        self.l_rangeEnd.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.l_rangeEnd, 1, 5, 1, 1)

        self.sp_rangeEnd = QSpinBox(self.f_frameRange_2)
        self.sp_rangeEnd.setObjectName(u"sp_rangeEnd")
        self.sp_rangeEnd.setMaximum(99999)
        self.sp_rangeEnd.setValue(1100)

        self.gridLayout.addWidget(self.sp_rangeEnd, 1, 6, 1, 1)

        self.sp_rangeStart = QSpinBox(self.f_frameRange_2)
        self.sp_rangeStart.setObjectName(u"sp_rangeStart")
        self.sp_rangeStart.setMaximum(99999)
        self.sp_rangeStart.setValue(1001)

        self.gridLayout.addWidget(self.sp_rangeStart, 0, 6, 1, 1)

        self.l_rangeStart = QLabel(self.f_frameRange_2)
        self.l_rangeStart.setObjectName(u"l_rangeStart")
        self.l_rangeStart.setMinimumSize(QSize(30, 0))
        self.l_rangeStart.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.l_rangeStart, 0, 5, 1, 1)

        self.l_rangeStartInfo = QLabel(self.f_frameRange_2)
        self.l_rangeStartInfo.setObjectName(u"l_rangeStartInfo")

        self.gridLayout.addWidget(self.l_rangeStartInfo, 0, 0, 1, 1)

        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer_7, 0, 4, 1, 1)

        self.l_rangeEndInfo = QLabel(self.f_frameRange_2)
        self.l_rangeEndInfo.setObjectName(u"l_rangeEndInfo")

        self.gridLayout.addWidget(self.l_rangeEndInfo, 1, 0, 1, 1)


        self.verticalLayout_2.addWidget(self.f_frameRange_2)

        self.widget = QWidget(self.gb_playblast)
        self.widget.setObjectName(u"widget")
        self.horizontalLayout_2 = QHBoxLayout(self.widget)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(9, 0, 9, 0)
        self.label = QLabel(self.widget)
        self.label.setObjectName(u"label")

        self.horizontalLayout_2.addWidget(self.label)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.cb_cams = QComboBox(self.widget)
        self.cb_cams.setObjectName(u"cb_cams")
        self.cb_cams.setMinimumSize(QSize(150, 0))

        self.horizontalLayout_2.addWidget(self.cb_cams)


        self.verticalLayout_2.addWidget(self.widget)

        self.f_resolution = QWidget(self.gb_playblast)
        self.f_resolution.setObjectName(u"f_resolution")
        self.horizontalLayout_9 = QHBoxLayout(self.f_resolution)
        self.horizontalLayout_9.setSpacing(6)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.horizontalLayout_9.setContentsMargins(9, 0, 9, 0)
        self.label_6 = QLabel(self.f_resolution)
        self.label_6.setObjectName(u"label_6")

        self.horizontalLayout_9.addWidget(self.label_6)

        self.horizontalSpacer_13 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_9.addItem(self.horizontalSpacer_13)

        self.chb_resOverride = QCheckBox(self.f_resolution)
        self.chb_resOverride.setObjectName(u"chb_resOverride")
        self.chb_resOverride.setChecked(True)

        self.horizontalLayout_9.addWidget(self.chb_resOverride)

        self.sp_resWidth = QSpinBox(self.f_resolution)
        self.sp_resWidth.setObjectName(u"sp_resWidth")
        self.sp_resWidth.setEnabled(True)
        self.sp_resWidth.setMinimum(1)
        self.sp_resWidth.setMaximum(99999)
        self.sp_resWidth.setValue(1280)

        self.horizontalLayout_9.addWidget(self.sp_resWidth)

        self.sp_resHeight = QSpinBox(self.f_resolution)
        self.sp_resHeight.setObjectName(u"sp_resHeight")
        self.sp_resHeight.setEnabled(True)
        self.sp_resHeight.setMinimum(1)
        self.sp_resHeight.setMaximum(99999)
        self.sp_resHeight.setValue(720)

        self.horizontalLayout_9.addWidget(self.sp_resHeight)

        self.b_resPresets = QPushButton(self.f_resolution)
        self.b_resPresets.setObjectName(u"b_resPresets")
        self.b_resPresets.setEnabled(True)
        self.b_resPresets.setMinimumSize(QSize(23, 23))
        self.b_resPresets.setMaximumSize(QSize(23, 23))

        self.horizontalLayout_9.addWidget(self.b_resPresets)


        self.verticalLayout_2.addWidget(self.f_resolution)

        self.f_displayMode = QWidget(self.gb_playblast)
        self.f_displayMode.setObjectName(u"f_displayMode")
        self.horizontalLayout_11 = QHBoxLayout(self.f_displayMode)
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.horizontalLayout_11.setContentsMargins(9, 0, 9, 0)
        self.label_7 = QLabel(self.f_displayMode)
        self.label_7.setObjectName(u"label_7")

        self.horizontalLayout_11.addWidget(self.label_7)

        self.horizontalSpacer_14 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_11.addItem(self.horizontalSpacer_14)

        self.cb_displayMode = QComboBox(self.f_displayMode)
        self.cb_displayMode.setObjectName(u"cb_displayMode")
        self.cb_displayMode.setMinimumSize(QSize(150, 0))

        self.horizontalLayout_11.addWidget(self.cb_displayMode)


        self.verticalLayout_2.addWidget(self.f_displayMode)

        self.w_master = QWidget(self.gb_playblast)
        self.w_master.setObjectName(u"w_master")
        self.horizontalLayout_20 = QHBoxLayout(self.w_master)
        self.horizontalLayout_20.setSpacing(0)
        self.horizontalLayout_20.setObjectName(u"horizontalLayout_20")
        self.horizontalLayout_20.setContentsMargins(9, 0, 9, 0)
        self.l_master = QLabel(self.w_master)
        self.l_master.setObjectName(u"l_master")

        self.horizontalLayout_20.addWidget(self.l_master)

        self.horizontalSpacer_29 = QSpacerItem(113, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_20.addItem(self.horizontalSpacer_29)

        self.cb_master = QComboBox(self.w_master)
        self.cb_master.setObjectName(u"cb_master")
        self.cb_master.setMinimumSize(QSize(150, 0))

        self.horizontalLayout_20.addWidget(self.cb_master)


        self.verticalLayout_2.addWidget(self.w_master)

        self.w_location = QWidget(self.gb_playblast)
        self.w_location.setObjectName(u"w_location")
        self.horizontalLayout_18 = QHBoxLayout(self.w_location)
        self.horizontalLayout_18.setSpacing(0)
        self.horizontalLayout_18.setObjectName(u"horizontalLayout_18")
        self.horizontalLayout_18.setContentsMargins(9, 0, 9, 0)
        self.l_location = QLabel(self.w_location)
        self.l_location.setObjectName(u"l_location")

        self.horizontalLayout_18.addWidget(self.l_location)

        self.horizontalSpacer_9 = QSpacerItem(113, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_18.addItem(self.horizontalSpacer_9)

        self.cb_location = QComboBox(self.w_location)
        self.cb_location.setObjectName(u"cb_location")
        self.cb_location.setMinimumSize(QSize(150, 0))

        self.horizontalLayout_18.addWidget(self.cb_location)


        self.verticalLayout_2.addWidget(self.w_location)

        self.widget_5 = QWidget(self.gb_playblast)
        self.widget_5.setObjectName(u"widget_5")
        self.horizontalLayout_5 = QHBoxLayout(self.widget_5)
        self.horizontalLayout_5.setSpacing(0)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(9, 0, 9, 0)
        self.label_5 = QLabel(self.widget_5)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout_5.addWidget(self.label_5)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_4)

        self.cb_formats = QComboBox(self.widget_5)
        self.cb_formats.setObjectName(u"cb_formats")
        self.cb_formats.setMinimumSize(QSize(150, 0))

        self.horizontalLayout_5.addWidget(self.cb_formats)


        self.verticalLayout_2.addWidget(self.widget_5)


        self.verticalLayout.addWidget(self.gb_playblast)

        self.gb_previous = QGroupBox(wg_Playblast)
        self.gb_previous.setObjectName(u"gb_previous")
        self.gb_previous.setCheckable(False)
        self.gb_previous.setChecked(False)
        self.horizontalLayout_3 = QHBoxLayout(self.gb_previous)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(18, -1, 18, -1)
        self.scrollArea = QScrollArea(self.gb_previous)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 320, 69))
        self.horizontalLayout_6 = QHBoxLayout(self.scrollAreaWidgetContents)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.l_pathLast = QLabel(self.scrollAreaWidgetContents)
        self.l_pathLast.setObjectName(u"l_pathLast")

        self.horizontalLayout_6.addWidget(self.l_pathLast)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.horizontalLayout_3.addWidget(self.scrollArea)

        self.b_pathLast = QToolButton(self.gb_previous)
        self.b_pathLast.setObjectName(u"b_pathLast")
        self.b_pathLast.setEnabled(True)
        self.b_pathLast.setArrowType(Qt.ArrowType.DownArrow)

        self.horizontalLayout_3.addWidget(self.b_pathLast)


        self.verticalLayout.addWidget(self.gb_previous)

        QWidget.setTabOrder(self.e_name, self.cb_rangeType)
        QWidget.setTabOrder(self.cb_rangeType, self.sp_rangeStart)
        QWidget.setTabOrder(self.sp_rangeStart, self.sp_rangeEnd)
        QWidget.setTabOrder(self.sp_rangeEnd, self.cb_cams)
        QWidget.setTabOrder(self.cb_cams, self.chb_resOverride)
        QWidget.setTabOrder(self.chb_resOverride, self.sp_resWidth)
        QWidget.setTabOrder(self.sp_resWidth, self.sp_resHeight)
        QWidget.setTabOrder(self.sp_resHeight, self.b_resPresets)
        QWidget.setTabOrder(self.b_resPresets, self.cb_displayMode)
        QWidget.setTabOrder(self.cb_displayMode, self.cb_master)
        QWidget.setTabOrder(self.cb_master, self.cb_location)
        QWidget.setTabOrder(self.cb_location, self.cb_formats)
        QWidget.setTabOrder(self.cb_formats, self.scrollArea)
        QWidget.setTabOrder(self.scrollArea, self.b_pathLast)

        self.retranslateUi(wg_Playblast)

        QMetaObject.connectSlotsByName(wg_Playblast)
    # setupUi

    def retranslateUi(self, wg_Playblast):
        wg_Playblast.setWindowTitle(QCoreApplication.translate("wg_Playblast", u"Playblast", None))
        self.l_name.setText(QCoreApplication.translate("wg_Playblast", u"Name:", None))
        self.l_class.setText(QCoreApplication.translate("wg_Playblast", u"Playblast", None))
        self.gb_playblast.setTitle(QCoreApplication.translate("wg_Playblast", u"General", None))
        self.l_comment.setText(QCoreApplication.translate("wg_Playblast", u"Comment:", None))
        self.label_2.setText(QCoreApplication.translate("wg_Playblast", u"Identifier:", None))
        self.l_taskName.setText("")
        self.b_changeTask.setText(QCoreApplication.translate("wg_Playblast", u"change", None))
        self.label_3.setText(QCoreApplication.translate("wg_Playblast", u"Framerange:", None))
        self.l_rangeEnd.setText(QCoreApplication.translate("wg_Playblast", u"1100", None))
        self.l_rangeStart.setText(QCoreApplication.translate("wg_Playblast", u"1001", None))
        self.l_rangeStartInfo.setText(QCoreApplication.translate("wg_Playblast", u"Start:", None))
        self.l_rangeEndInfo.setText(QCoreApplication.translate("wg_Playblast", u"End:", None))
        self.label.setText(QCoreApplication.translate("wg_Playblast", u"Camera:", None))
        self.label_6.setText(QCoreApplication.translate("wg_Playblast", u"Resolution override:", None))
        self.chb_resOverride.setText("")
        self.b_resPresets.setText(QCoreApplication.translate("wg_Playblast", u"\u25bc", None))
        self.label_7.setText(QCoreApplication.translate("wg_Playblast", u"Display mode:", None))
        self.l_master.setText(QCoreApplication.translate("wg_Playblast", u"Master Version:", None))
        self.l_location.setText(QCoreApplication.translate("wg_Playblast", u"Location:", None))
        self.label_5.setText(QCoreApplication.translate("wg_Playblast", u"Format:", None))
        self.gb_previous.setTitle(QCoreApplication.translate("wg_Playblast", u"Last playblast", None))
        self.l_pathLast.setText(QCoreApplication.translate("wg_Playblast", u"None", None))
        self.b_pathLast.setText(QCoreApplication.translate("wg_Playblast", u"...", None))
    # retranslateUi

