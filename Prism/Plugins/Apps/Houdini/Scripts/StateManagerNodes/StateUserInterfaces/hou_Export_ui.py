# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'hou_Export.ui'
##
## Created by: Qt User Interface Compiler version 6.8.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from qtpy.QtCore import *  # type: ignore
from qtpy.QtGui import *  # type: ignore
from qtpy.QtWidgets import *  # type: ignore

class Ui_wg_Export(object):
    def setupUi(self, wg_Export):
        if not wg_Export.objectName():
            wg_Export.setObjectName(u"wg_Export")
        wg_Export.resize(340, 853)
        self.verticalLayout = QVBoxLayout(wg_Export)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.w_name = QWidget(wg_Export)
        self.w_name.setObjectName(u"w_name")
        self.horizontalLayout_2 = QHBoxLayout(self.w_name)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(-1, 0, 18, 0)
        self.l_name = QLabel(self.w_name)
        self.l_name.setObjectName(u"l_name")

        self.horizontalLayout_2.addWidget(self.l_name)

        self.e_name = QLineEdit(self.w_name)
        self.e_name.setObjectName(u"e_name")
        self.e_name.setMinimumSize(QSize(0, 0))
        self.e_name.setMaximumSize(QSize(9999, 16777215))

        self.horizontalLayout_2.addWidget(self.e_name)

        self.l_class = QLabel(self.w_name)
        self.l_class.setObjectName(u"l_class")
        font = QFont()
        font.setBold(True)
        self.l_class.setFont(font)

        self.horizontalLayout_2.addWidget(self.l_class)


        self.verticalLayout.addWidget(self.w_name)

        self.gb_general = QGroupBox(wg_Export)
        self.gb_general.setObjectName(u"gb_general")
        self.verticalLayout_3 = QVBoxLayout(self.gb_general)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.w_comment = QWidget(self.gb_general)
        self.w_comment.setObjectName(u"w_comment")
        self.horizontalLayout_29 = QHBoxLayout(self.w_comment)
        self.horizontalLayout_29.setSpacing(0)
        self.horizontalLayout_29.setObjectName(u"horizontalLayout_29")
        self.horizontalLayout_29.setContentsMargins(9, 0, 9, 0)
        self.l_comment = QLabel(self.w_comment)
        self.l_comment.setObjectName(u"l_comment")
        self.l_comment.setMinimumSize(QSize(40, 0))
        self.l_comment.setMaximumSize(QSize(95, 16777215))

        self.horizontalLayout_29.addWidget(self.l_comment)

        self.horizontalSpacer_8 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_29.addItem(self.horizontalSpacer_8)

        self.e_comment = QLineEdit(self.w_comment)
        self.e_comment.setObjectName(u"e_comment")

        self.horizontalLayout_29.addWidget(self.e_comment)


        self.verticalLayout_3.addWidget(self.w_comment)

        self.f_taskName = QWidget(self.gb_general)
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

        self.f_frameRange = QWidget(self.gb_general)
        self.f_frameRange.setObjectName(u"f_frameRange")
        self.horizontalLayout = QHBoxLayout(self.f_frameRange)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(-1, 0, -1, 0)
        self.label_3 = QLabel(self.f_frameRange)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout.addWidget(self.label_3)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.cb_rangeType = QComboBox(self.f_frameRange)
        self.cb_rangeType.setObjectName(u"cb_rangeType")

        self.horizontalLayout.addWidget(self.cb_rangeType)


        self.verticalLayout_3.addWidget(self.f_frameRange)

        self.w_frameRangeValues = QWidget(self.gb_general)
        self.w_frameRangeValues.setObjectName(u"w_frameRangeValues")
        self.gridLayout = QGridLayout(self.w_frameRangeValues)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(-1, 0, -1, 0)
        self.l_rangeEnd = QLabel(self.w_frameRangeValues)
        self.l_rangeEnd.setObjectName(u"l_rangeEnd")
        self.l_rangeEnd.setMinimumSize(QSize(30, 0))
        self.l_rangeEnd.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.l_rangeEnd, 1, 5, 1, 1)

        self.sp_rangeEnd = QSpinBox(self.w_frameRangeValues)
        self.sp_rangeEnd.setObjectName(u"sp_rangeEnd")
        self.sp_rangeEnd.setMaximum(99999)
        self.sp_rangeEnd.setValue(1100)

        self.gridLayout.addWidget(self.sp_rangeEnd, 1, 6, 1, 1)

        self.sp_rangeStart = QSpinBox(self.w_frameRangeValues)
        self.sp_rangeStart.setObjectName(u"sp_rangeStart")
        self.sp_rangeStart.setMaximum(99999)
        self.sp_rangeStart.setValue(1001)

        self.gridLayout.addWidget(self.sp_rangeStart, 0, 6, 1, 1)

        self.l_rangeStart = QLabel(self.w_frameRangeValues)
        self.l_rangeStart.setObjectName(u"l_rangeStart")
        self.l_rangeStart.setMinimumSize(QSize(30, 0))
        self.l_rangeStart.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.l_rangeStart, 0, 5, 1, 1)

        self.l_rangeStartInfo = QLabel(self.w_frameRangeValues)
        self.l_rangeStartInfo.setObjectName(u"l_rangeStartInfo")

        self.gridLayout.addWidget(self.l_rangeStartInfo, 0, 0, 1, 1)

        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer_7, 0, 4, 1, 1)

        self.l_rangeEndInfo = QLabel(self.w_frameRangeValues)
        self.l_rangeEndInfo.setObjectName(u"l_rangeEndInfo")

        self.gridLayout.addWidget(self.l_rangeEndInfo, 1, 0, 1, 1)


        self.verticalLayout_3.addWidget(self.w_frameRangeValues)

        self.w_master = QWidget(self.gb_general)
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

        self.chb_master = QCheckBox(self.w_master)
        self.chb_master.setObjectName(u"chb_master")
        self.chb_master.setChecked(True)

        self.horizontalLayout_20.addWidget(self.chb_master)


        self.verticalLayout_3.addWidget(self.w_master)

        self.w_outPath = QWidget(self.gb_general)
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

        self.widget_6 = QWidget(self.gb_general)
        self.widget_6.setObjectName(u"widget_6")
        self.horizontalLayout_5 = QHBoxLayout(self.widget_6)
        self.horizontalLayout_5.setSpacing(0)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(-1, 0, -1, 0)
        self.label_5 = QLabel(self.widget_6)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout_5.addWidget(self.label_5)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_3)

        self.cb_outType = QComboBox(self.widget_6)
        self.cb_outType.setObjectName(u"cb_outType")
        self.cb_outType.setMinimumSize(QSize(124, 0))

        self.horizontalLayout_5.addWidget(self.cb_outType)


        self.verticalLayout_3.addWidget(self.widget_6)

        self.w_takes = QWidget(self.gb_general)
        self.w_takes.setObjectName(u"w_takes")
        self.horizontalLayout_9 = QHBoxLayout(self.w_takes)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.horizontalLayout_9.setContentsMargins(-1, 0, -1, 0)
        self.label_6 = QLabel(self.w_takes)
        self.label_6.setObjectName(u"label_6")

        self.horizontalLayout_9.addWidget(self.label_6)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_9.addItem(self.horizontalSpacer_4)

        self.chb_useTake = QCheckBox(self.w_takes)
        self.chb_useTake.setObjectName(u"chb_useTake")

        self.horizontalLayout_9.addWidget(self.chb_useTake)

        self.cb_take = QComboBox(self.w_takes)
        self.cb_take.setObjectName(u"cb_take")
        self.cb_take.setEnabled(False)
        self.cb_take.setMinimumSize(QSize(124, 0))

        self.horizontalLayout_9.addWidget(self.cb_take)


        self.verticalLayout_3.addWidget(self.w_takes)

        self.f_cam = QWidget(self.gb_general)
        self.f_cam.setObjectName(u"f_cam")
        self.horizontalLayout_6 = QHBoxLayout(self.f_cam)
        self.horizontalLayout_6.setSpacing(0)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(-1, 0, -1, 0)
        self.l_cam = QLabel(self.f_cam)
        self.l_cam.setObjectName(u"l_cam")
        self.l_cam.setMinimumSize(QSize(40, 0))
        self.l_cam.setMaximumSize(QSize(95, 16777215))

        self.horizontalLayout_6.addWidget(self.l_cam)

        self.cb_cam = QComboBox(self.f_cam)
        self.cb_cam.setObjectName(u"cb_cam")

        self.horizontalLayout_6.addWidget(self.cb_cam)


        self.verticalLayout_3.addWidget(self.f_cam)

        self.w_sCamShot = QWidget(self.gb_general)
        self.w_sCamShot.setObjectName(u"w_sCamShot")
        self.horizontalLayout_8 = QHBoxLayout(self.w_sCamShot)
        self.horizontalLayout_8.setSpacing(0)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(-1, 0, -1, 0)
        self.l_sCamShot = QLabel(self.w_sCamShot)
        self.l_sCamShot.setObjectName(u"l_sCamShot")
        self.l_sCamShot.setMinimumSize(QSize(40, 0))
        self.l_sCamShot.setMaximumSize(QSize(95, 16777215))

        self.horizontalLayout_8.addWidget(self.l_sCamShot)

        self.cb_sCamShot = QComboBox(self.w_sCamShot)
        self.cb_sCamShot.setObjectName(u"cb_sCamShot")

        self.horizontalLayout_8.addWidget(self.cb_sCamShot)


        self.verticalLayout_3.addWidget(self.w_sCamShot)

        self.f_status = QWidget(self.gb_general)
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

        self.f_connect = QWidget(self.gb_general)
        self.f_connect.setObjectName(u"f_connect")
        self.horizontalLayout_3 = QHBoxLayout(self.f_connect)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(-1, 0, -1, 0)
        self.b_connect = QPushButton(self.f_connect)
        self.b_connect.setObjectName(u"b_connect")
        self.b_connect.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.horizontalLayout_3.addWidget(self.b_connect)


        self.verticalLayout_3.addWidget(self.f_connect)


        self.verticalLayout.addWidget(self.gb_general)

        self.gb_submit = QGroupBox(wg_Export)
        self.gb_submit.setObjectName(u"gb_submit")
        self.gb_submit.setCheckable(True)
        self.gb_submit.setChecked(True)
        self.verticalLayout_7 = QVBoxLayout(self.gb_submit)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(-1, 15, -1, -1)
        self.f_manager = QWidget(self.gb_submit)
        self.f_manager.setObjectName(u"f_manager")
        self.horizontalLayout_17 = QHBoxLayout(self.f_manager)
        self.horizontalLayout_17.setObjectName(u"horizontalLayout_17")
        self.horizontalLayout_17.setContentsMargins(-1, 0, -1, 0)
        self.l_manager = QLabel(self.f_manager)
        self.l_manager.setObjectName(u"l_manager")

        self.horizontalLayout_17.addWidget(self.l_manager)

        self.horizontalSpacer_19 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_17.addItem(self.horizontalSpacer_19)

        self.cb_manager = QComboBox(self.f_manager)
        self.cb_manager.setObjectName(u"cb_manager")
        self.cb_manager.setMinimumSize(QSize(150, 0))

        self.horizontalLayout_17.addWidget(self.cb_manager)


        self.verticalLayout_7.addWidget(self.f_manager)

        self.f_rjPrio = QWidget(self.gb_submit)
        self.f_rjPrio.setObjectName(u"f_rjPrio")
        self.horizontalLayout_21 = QHBoxLayout(self.f_rjPrio)
        self.horizontalLayout_21.setObjectName(u"horizontalLayout_21")
        self.horizontalLayout_21.setContentsMargins(-1, 0, -1, 0)
        self.l_rjPrio = QLabel(self.f_rjPrio)
        self.l_rjPrio.setObjectName(u"l_rjPrio")

        self.horizontalLayout_21.addWidget(self.l_rjPrio)

        self.horizontalSpacer_15 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_21.addItem(self.horizontalSpacer_15)

        self.sp_rjPrio = QSpinBox(self.f_rjPrio)
        self.sp_rjPrio.setObjectName(u"sp_rjPrio")
        self.sp_rjPrio.setMaximum(100)
        self.sp_rjPrio.setValue(50)

        self.horizontalLayout_21.addWidget(self.sp_rjPrio)


        self.verticalLayout_7.addWidget(self.f_rjPrio)

        self.f_rjWidgetsPerTask = QWidget(self.gb_submit)
        self.f_rjWidgetsPerTask.setObjectName(u"f_rjWidgetsPerTask")
        self.horizontalLayout_22 = QHBoxLayout(self.f_rjWidgetsPerTask)
        self.horizontalLayout_22.setObjectName(u"horizontalLayout_22")
        self.horizontalLayout_22.setContentsMargins(-1, 0, -1, 0)
        self.label_15 = QLabel(self.f_rjWidgetsPerTask)
        self.label_15.setObjectName(u"label_15")

        self.horizontalLayout_22.addWidget(self.label_15)

        self.horizontalSpacer_16 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_22.addItem(self.horizontalSpacer_16)

        self.sp_rjFramesPerTask = QSpinBox(self.f_rjWidgetsPerTask)
        self.sp_rjFramesPerTask.setObjectName(u"sp_rjFramesPerTask")
        self.sp_rjFramesPerTask.setMinimum(1)
        self.sp_rjFramesPerTask.setMaximum(9999)
        self.sp_rjFramesPerTask.setValue(999)

        self.horizontalLayout_22.addWidget(self.sp_rjFramesPerTask)


        self.verticalLayout_7.addWidget(self.f_rjWidgetsPerTask)

        self.f_rjTimeout = QWidget(self.gb_submit)
        self.f_rjTimeout.setObjectName(u"f_rjTimeout")
        self.horizontalLayout_28 = QHBoxLayout(self.f_rjTimeout)
        self.horizontalLayout_28.setObjectName(u"horizontalLayout_28")
        self.horizontalLayout_28.setContentsMargins(-1, 0, -1, 0)
        self.l_rjTimeout = QLabel(self.f_rjTimeout)
        self.l_rjTimeout.setObjectName(u"l_rjTimeout")

        self.horizontalLayout_28.addWidget(self.l_rjTimeout)

        self.horizontalSpacer_22 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_28.addItem(self.horizontalSpacer_22)

        self.sp_rjTimeout = QSpinBox(self.f_rjTimeout)
        self.sp_rjTimeout.setObjectName(u"sp_rjTimeout")
        self.sp_rjTimeout.setMinimum(0)
        self.sp_rjTimeout.setMaximum(9999)
        self.sp_rjTimeout.setValue(360)

        self.horizontalLayout_28.addWidget(self.sp_rjTimeout)


        self.verticalLayout_7.addWidget(self.f_rjTimeout)

        self.f_rjSuspended = QWidget(self.gb_submit)
        self.f_rjSuspended.setObjectName(u"f_rjSuspended")
        self.horizontalLayout_26 = QHBoxLayout(self.f_rjSuspended)
        self.horizontalLayout_26.setObjectName(u"horizontalLayout_26")
        self.horizontalLayout_26.setContentsMargins(-1, 0, -1, 0)
        self.label_18 = QLabel(self.f_rjSuspended)
        self.label_18.setObjectName(u"label_18")

        self.horizontalLayout_26.addWidget(self.label_18)

        self.horizontalSpacer_20 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_26.addItem(self.horizontalSpacer_20)

        self.chb_rjSuspended = QCheckBox(self.f_rjSuspended)
        self.chb_rjSuspended.setObjectName(u"chb_rjSuspended")
        self.chb_rjSuspended.setChecked(False)

        self.horizontalLayout_26.addWidget(self.chb_rjSuspended)


        self.verticalLayout_7.addWidget(self.f_rjSuspended)

        self.f_osDependencies = QWidget(self.gb_submit)
        self.f_osDependencies.setObjectName(u"f_osDependencies")
        self.horizontalLayout_27 = QHBoxLayout(self.f_osDependencies)
        self.horizontalLayout_27.setObjectName(u"horizontalLayout_27")
        self.horizontalLayout_27.setContentsMargins(-1, 0, -1, 0)
        self.label_19 = QLabel(self.f_osDependencies)
        self.label_19.setObjectName(u"label_19")

        self.horizontalLayout_27.addWidget(self.label_19)

        self.horizontalSpacer_21 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_27.addItem(self.horizontalSpacer_21)

        self.chb_osDependencies = QCheckBox(self.f_osDependencies)
        self.chb_osDependencies.setObjectName(u"chb_osDependencies")
        self.chb_osDependencies.setChecked(True)

        self.horizontalLayout_27.addWidget(self.chb_osDependencies)


        self.verticalLayout_7.addWidget(self.f_osDependencies)

        self.f_osUpload = QWidget(self.gb_submit)
        self.f_osUpload.setObjectName(u"f_osUpload")
        self.horizontalLayout_23 = QHBoxLayout(self.f_osUpload)
        self.horizontalLayout_23.setObjectName(u"horizontalLayout_23")
        self.horizontalLayout_23.setContentsMargins(-1, 0, -1, 0)
        self.label_16 = QLabel(self.f_osUpload)
        self.label_16.setObjectName(u"label_16")

        self.horizontalLayout_23.addWidget(self.label_16)

        self.horizontalSpacer_17 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_23.addItem(self.horizontalSpacer_17)

        self.chb_osUpload = QCheckBox(self.f_osUpload)
        self.chb_osUpload.setObjectName(u"chb_osUpload")
        self.chb_osUpload.setChecked(True)

        self.horizontalLayout_23.addWidget(self.chb_osUpload)


        self.verticalLayout_7.addWidget(self.f_osUpload)

        self.f_osPAssets = QWidget(self.gb_submit)
        self.f_osPAssets.setObjectName(u"f_osPAssets")
        self.horizontalLayout_24 = QHBoxLayout(self.f_osPAssets)
        self.horizontalLayout_24.setObjectName(u"horizontalLayout_24")
        self.horizontalLayout_24.setContentsMargins(-1, 0, -1, 0)
        self.label_17 = QLabel(self.f_osPAssets)
        self.label_17.setObjectName(u"label_17")

        self.horizontalLayout_24.addWidget(self.label_17)

        self.horizontalSpacer_18 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_24.addItem(self.horizontalSpacer_18)

        self.chb_osPAssets = QCheckBox(self.f_osPAssets)
        self.chb_osPAssets.setObjectName(u"chb_osPAssets")
        self.chb_osPAssets.setChecked(True)

        self.horizontalLayout_24.addWidget(self.chb_osPAssets)


        self.verticalLayout_7.addWidget(self.f_osPAssets)

        self.gb_osSlaves = QGroupBox(self.gb_submit)
        self.gb_osSlaves.setObjectName(u"gb_osSlaves")
        self.horizontalLayout_25 = QHBoxLayout(self.gb_osSlaves)
        self.horizontalLayout_25.setObjectName(u"horizontalLayout_25")
        self.horizontalLayout_25.setContentsMargins(9, 3, 9, 3)
        self.e_osSlaves = QLineEdit(self.gb_osSlaves)
        self.e_osSlaves.setObjectName(u"e_osSlaves")

        self.horizontalLayout_25.addWidget(self.e_osSlaves)

        self.b_osSlaves = QPushButton(self.gb_osSlaves)
        self.b_osSlaves.setObjectName(u"b_osSlaves")
        self.b_osSlaves.setMaximumSize(QSize(25, 16777215))
        self.b_osSlaves.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.horizontalLayout_25.addWidget(self.b_osSlaves)


        self.verticalLayout_7.addWidget(self.gb_osSlaves)


        self.verticalLayout.addWidget(self.gb_submit)

        self.gb_previous = QGroupBox(wg_Export)
        self.gb_previous.setObjectName(u"gb_previous")
        self.gb_previous.setCheckable(False)
        self.gb_previous.setChecked(False)
        self.horizontalLayout_10 = QHBoxLayout(self.gb_previous)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.scrollArea = QScrollArea(self.gb_previous)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 289, 54))
        self.verticalLayout_2 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.l_pathLast = QLabel(self.scrollAreaWidgetContents)
        self.l_pathLast.setObjectName(u"l_pathLast")

        self.verticalLayout_2.addWidget(self.l_pathLast)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.horizontalLayout_10.addWidget(self.scrollArea)

        self.b_pathLast = QToolButton(self.gb_previous)
        self.b_pathLast.setObjectName(u"b_pathLast")
        self.b_pathLast.setEnabled(True)
        self.b_pathLast.setArrowType(Qt.ArrowType.DownArrow)

        self.horizontalLayout_10.addWidget(self.b_pathLast)


        self.verticalLayout.addWidget(self.gb_previous)

        QWidget.setTabOrder(self.e_name, self.cb_rangeType)
        QWidget.setTabOrder(self.cb_rangeType, self.sp_rangeStart)
        QWidget.setTabOrder(self.sp_rangeStart, self.sp_rangeEnd)
        QWidget.setTabOrder(self.sp_rangeEnd, self.chb_master)
        QWidget.setTabOrder(self.chb_master, self.cb_outPath)
        QWidget.setTabOrder(self.cb_outPath, self.cb_outType)
        QWidget.setTabOrder(self.cb_outType, self.chb_useTake)
        QWidget.setTabOrder(self.chb_useTake, self.cb_take)
        QWidget.setTabOrder(self.cb_take, self.cb_cam)
        QWidget.setTabOrder(self.cb_cam, self.cb_sCamShot)
        QWidget.setTabOrder(self.cb_sCamShot, self.gb_submit)
        QWidget.setTabOrder(self.gb_submit, self.cb_manager)
        QWidget.setTabOrder(self.cb_manager, self.sp_rjPrio)
        QWidget.setTabOrder(self.sp_rjPrio, self.sp_rjFramesPerTask)
        QWidget.setTabOrder(self.sp_rjFramesPerTask, self.sp_rjTimeout)
        QWidget.setTabOrder(self.sp_rjTimeout, self.chb_rjSuspended)
        QWidget.setTabOrder(self.chb_rjSuspended, self.chb_osDependencies)
        QWidget.setTabOrder(self.chb_osDependencies, self.chb_osUpload)
        QWidget.setTabOrder(self.chb_osUpload, self.chb_osPAssets)
        QWidget.setTabOrder(self.chb_osPAssets, self.e_osSlaves)
        QWidget.setTabOrder(self.e_osSlaves, self.scrollArea)
        QWidget.setTabOrder(self.scrollArea, self.b_pathLast)

        self.retranslateUi(wg_Export)

        QMetaObject.connectSlotsByName(wg_Export)
    # setupUi

    def retranslateUi(self, wg_Export):
        wg_Export.setWindowTitle(QCoreApplication.translate("wg_Export", u"Export", None))
        self.l_name.setText(QCoreApplication.translate("wg_Export", u"Name:", None))
        self.l_class.setText(QCoreApplication.translate("wg_Export", u"Export", None))
        self.gb_general.setTitle(QCoreApplication.translate("wg_Export", u"General", None))
        self.l_comment.setText(QCoreApplication.translate("wg_Export", u"Comment:", None))
        self.l_tasklabel.setText(QCoreApplication.translate("wg_Export", u"Productname:", None))
        self.l_taskName.setText("")
        self.b_changeTask.setText(QCoreApplication.translate("wg_Export", u"change", None))
        self.label_3.setText(QCoreApplication.translate("wg_Export", u"Framerange:", None))
        self.l_rangeEnd.setText(QCoreApplication.translate("wg_Export", u"1100", None))
        self.l_rangeStart.setText(QCoreApplication.translate("wg_Export", u"1001", None))
        self.l_rangeStartInfo.setText(QCoreApplication.translate("wg_Export", u"Start:", None))
        self.l_rangeEndInfo.setText(QCoreApplication.translate("wg_Export", u"End:", None))
        self.l_master.setText(QCoreApplication.translate("wg_Export", u"Update Master Version:", None))
        self.chb_master.setText("")
        self.l_outPath.setText(QCoreApplication.translate("wg_Export", u"Location:", None))
        self.label_5.setText(QCoreApplication.translate("wg_Export", u"Outputtype:", None))
        self.label_6.setText(QCoreApplication.translate("wg_Export", u"Override take:", None))
        self.chb_useTake.setText("")
        self.l_cam.setText(QCoreApplication.translate("wg_Export", u"Camera:", None))
        self.l_sCamShot.setText(QCoreApplication.translate("wg_Export", u"Shot:", None))
        self.label.setText(QCoreApplication.translate("wg_Export", u"Status:", None))
        self.l_status.setText(QCoreApplication.translate("wg_Export", u"Not connected", None))
        self.b_goTo.setText(QCoreApplication.translate("wg_Export", u"Go to Node", None))
        self.b_connect.setText(QCoreApplication.translate("wg_Export", u"Connect with selected ROP Node", None))
        self.gb_submit.setTitle(QCoreApplication.translate("wg_Export", u"Submit Job", None))
        self.l_manager.setText(QCoreApplication.translate("wg_Export", u"Manager:", None))
        self.l_rjPrio.setText(QCoreApplication.translate("wg_Export", u"Priority:", None))
        self.label_15.setText(QCoreApplication.translate("wg_Export", u"Frames per Task:", None))
        self.l_rjTimeout.setText(QCoreApplication.translate("wg_Export", u"Task Timeout (min)", None))
        self.label_18.setText(QCoreApplication.translate("wg_Export", u"Submit suspended:", None))
        self.chb_rjSuspended.setText("")
        self.label_19.setText(QCoreApplication.translate("wg_Export", u"Submit dependent files:", None))
        self.chb_osDependencies.setText("")
        self.label_16.setText(QCoreApplication.translate("wg_Export", u"Upload output:", None))
        self.chb_osUpload.setText("")
        self.label_17.setText(QCoreApplication.translate("wg_Export", u"Use Project Assets", None))
        self.chb_osPAssets.setText("")
        self.gb_osSlaves.setTitle(QCoreApplication.translate("wg_Export", u"Assign to slaves:", None))
        self.b_osSlaves.setText(QCoreApplication.translate("wg_Export", u"...", None))
        self.gb_previous.setTitle(QCoreApplication.translate("wg_Export", u"Last export", None))
        self.l_pathLast.setText(QCoreApplication.translate("wg_Export", u"None", None))
        self.b_pathLast.setText(QCoreApplication.translate("wg_Export", u"...", None))
    # retranslateUi

