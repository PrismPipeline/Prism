# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'default_Playblast.ui'
#
# Created: Fri Oct 27 15:51:53 2023
#      by: qtpy-uic 2.0.5
#
# WARNING! All changes made in this file will be lost!

from qtpy import QtCore, QtGui, QtWidgets

class Ui_wg_Playblast(object):
    def setupUi(self, wg_Playblast):
        wg_Playblast.setObjectName("wg_Playblast")
        wg_Playblast.resize(340, 598)
        self.verticalLayout = QtWidgets.QVBoxLayout(wg_Playblast)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget_4 = QtWidgets.QWidget(wg_Playblast)
        self.widget_4.setObjectName("widget_4")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.widget_4)
        self.horizontalLayout_4.setContentsMargins(9, 0, 18, 0)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.l_name = QtWidgets.QLabel(self.widget_4)
        self.l_name.setObjectName("l_name")
        self.horizontalLayout_4.addWidget(self.l_name)
        self.e_name = QtWidgets.QLineEdit(self.widget_4)
        self.e_name.setObjectName("e_name")
        self.horizontalLayout_4.addWidget(self.e_name)
        self.l_class = QtWidgets.QLabel(self.widget_4)
        font = QtGui.QFont()
        font.setWeight(75)
        font.setBold(True)
        self.l_class.setFont(font)
        self.l_class.setObjectName("l_class")
        self.horizontalLayout_4.addWidget(self.l_class)
        self.verticalLayout.addWidget(self.widget_4)
        self.gb_playblast = QtWidgets.QGroupBox(wg_Playblast)
        self.gb_playblast.setObjectName("gb_playblast")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.gb_playblast)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.widget_10 = QtWidgets.QWidget(self.gb_playblast)
        self.widget_10.setObjectName("widget_10")
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout(self.widget_10)
        self.horizontalLayout_10.setContentsMargins(9, 0, 9, 0)
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        self.label_2 = QtWidgets.QLabel(self.widget_10)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_10.addWidget(self.label_2)
        self.l_taskName = QtWidgets.QLabel(self.widget_10)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.l_taskName.sizePolicy().hasHeightForWidth())
        self.l_taskName.setSizePolicy(sizePolicy)
        self.l_taskName.setText("")
        self.l_taskName.setAlignment(QtCore.Qt.AlignCenter)
        self.l_taskName.setObjectName("l_taskName")
        self.horizontalLayout_10.addWidget(self.l_taskName)
        self.b_changeTask = QtWidgets.QPushButton(self.widget_10)
        self.b_changeTask.setEnabled(True)
        self.b_changeTask.setFocusPolicy(QtCore.Qt.NoFocus)
        self.b_changeTask.setObjectName("b_changeTask")
        self.horizontalLayout_10.addWidget(self.b_changeTask)
        self.verticalLayout_2.addWidget(self.widget_10)
        self.widget_2 = QtWidgets.QWidget(self.gb_playblast)
        self.widget_2.setObjectName("widget_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget_2)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setContentsMargins(9, 0, 9, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_3 = QtWidgets.QLabel(self.widget_2)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout.addWidget(self.label_3)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.cb_rangeType = QtWidgets.QComboBox(self.widget_2)
        self.cb_rangeType.setObjectName("cb_rangeType")
        self.horizontalLayout.addWidget(self.cb_rangeType)
        self.verticalLayout_2.addWidget(self.widget_2)
        self.f_frameRange_2 = QtWidgets.QWidget(self.gb_playblast)
        self.f_frameRange_2.setObjectName("f_frameRange_2")
        self.gridLayout = QtWidgets.QGridLayout(self.f_frameRange_2)
        self.gridLayout.setContentsMargins(9, 0, 9, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.l_rangeEnd = QtWidgets.QLabel(self.f_frameRange_2)
        self.l_rangeEnd.setMinimumSize(QtCore.QSize(30, 0))
        self.l_rangeEnd.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.l_rangeEnd.setObjectName("l_rangeEnd")
        self.gridLayout.addWidget(self.l_rangeEnd, 1, 5, 1, 1)
        self.sp_rangeEnd = QtWidgets.QSpinBox(self.f_frameRange_2)
        self.sp_rangeEnd.setMaximumSize(QtCore.QSize(55, 16777215))
        self.sp_rangeEnd.setMaximum(99999)
        self.sp_rangeEnd.setProperty("value", 1100)
        self.sp_rangeEnd.setObjectName("sp_rangeEnd")
        self.gridLayout.addWidget(self.sp_rangeEnd, 1, 6, 1, 1)
        self.sp_rangeStart = QtWidgets.QSpinBox(self.f_frameRange_2)
        self.sp_rangeStart.setMaximumSize(QtCore.QSize(55, 16777215))
        self.sp_rangeStart.setMaximum(99999)
        self.sp_rangeStart.setProperty("value", 1001)
        self.sp_rangeStart.setObjectName("sp_rangeStart")
        self.gridLayout.addWidget(self.sp_rangeStart, 0, 6, 1, 1)
        self.l_rangeStart = QtWidgets.QLabel(self.f_frameRange_2)
        self.l_rangeStart.setMinimumSize(QtCore.QSize(30, 0))
        self.l_rangeStart.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.l_rangeStart.setObjectName("l_rangeStart")
        self.gridLayout.addWidget(self.l_rangeStart, 0, 5, 1, 1)
        self.l_rangeStartInfo = QtWidgets.QLabel(self.f_frameRange_2)
        self.l_rangeStartInfo.setObjectName("l_rangeStartInfo")
        self.gridLayout.addWidget(self.l_rangeStartInfo, 0, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem1, 0, 4, 1, 1)
        self.l_rangeEndInfo = QtWidgets.QLabel(self.f_frameRange_2)
        self.l_rangeEndInfo.setObjectName("l_rangeEndInfo")
        self.gridLayout.addWidget(self.l_rangeEndInfo, 1, 0, 1, 1)
        self.verticalLayout_2.addWidget(self.f_frameRange_2)
        self.widget = QtWidgets.QWidget(self.gb_playblast)
        self.widget.setObjectName("widget")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.widget)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setContentsMargins(9, 0, 9, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label = QtWidgets.QLabel(self.widget)
        self.label.setObjectName("label")
        self.horizontalLayout_2.addWidget(self.label)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem2)
        self.cb_cams = QtWidgets.QComboBox(self.widget)
        self.cb_cams.setMinimumSize(QtCore.QSize(150, 0))
        self.cb_cams.setObjectName("cb_cams")
        self.horizontalLayout_2.addWidget(self.cb_cams)
        self.verticalLayout_2.addWidget(self.widget)
        self.f_resolution = QtWidgets.QWidget(self.gb_playblast)
        self.f_resolution.setObjectName("f_resolution")
        self.horizontalLayout_9 = QtWidgets.QHBoxLayout(self.f_resolution)
        self.horizontalLayout_9.setSpacing(6)
        self.horizontalLayout_9.setContentsMargins(9, 0, 9, 0)
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        self.label_6 = QtWidgets.QLabel(self.f_resolution)
        self.label_6.setEnabled(True)
        self.label_6.setObjectName("label_6")
        self.horizontalLayout_9.addWidget(self.label_6)
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_9.addItem(spacerItem3)
        self.chb_resOverride = QtWidgets.QCheckBox(self.f_resolution)
        self.chb_resOverride.setText("")
        self.chb_resOverride.setChecked(True)
        self.chb_resOverride.setObjectName("chb_resOverride")
        self.horizontalLayout_9.addWidget(self.chb_resOverride)
        self.sp_resWidth = QtWidgets.QSpinBox(self.f_resolution)
        self.sp_resWidth.setEnabled(True)
        self.sp_resWidth.setMinimum(1)
        self.sp_resWidth.setMaximum(99999)
        self.sp_resWidth.setProperty("value", 1280)
        self.sp_resWidth.setObjectName("sp_resWidth")
        self.horizontalLayout_9.addWidget(self.sp_resWidth)
        self.sp_resHeight = QtWidgets.QSpinBox(self.f_resolution)
        self.sp_resHeight.setEnabled(True)
        self.sp_resHeight.setMinimum(1)
        self.sp_resHeight.setMaximum(99999)
        self.sp_resHeight.setProperty("value", 720)
        self.sp_resHeight.setObjectName("sp_resHeight")
        self.horizontalLayout_9.addWidget(self.sp_resHeight)
        self.b_resPresets = QtWidgets.QPushButton(self.f_resolution)
        self.b_resPresets.setEnabled(True)
        self.b_resPresets.setMinimumSize(QtCore.QSize(23, 23))
        self.b_resPresets.setMaximumSize(QtCore.QSize(23, 23))
        self.b_resPresets.setObjectName("b_resPresets")
        self.horizontalLayout_9.addWidget(self.b_resPresets)
        self.verticalLayout_2.addWidget(self.f_resolution)
        self.w_master = QtWidgets.QWidget(self.gb_playblast)
        self.w_master.setObjectName("w_master")
        self.horizontalLayout_18 = QtWidgets.QHBoxLayout(self.w_master)
        self.horizontalLayout_18.setSpacing(0)
        self.horizontalLayout_18.setContentsMargins(9, 0, 9, 0)
        self.horizontalLayout_18.setObjectName("horizontalLayout_18")
        self.l_outPath_2 = QtWidgets.QLabel(self.w_master)
        self.l_outPath_2.setObjectName("l_outPath_2")
        self.horizontalLayout_18.addWidget(self.l_outPath_2)
        spacerItem4 = QtWidgets.QSpacerItem(113, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_18.addItem(spacerItem4)
        self.cb_master = QtWidgets.QComboBox(self.w_master)
        self.cb_master.setMinimumSize(QtCore.QSize(150, 0))
        self.cb_master.setObjectName("cb_master")
        self.horizontalLayout_18.addWidget(self.cb_master)
        self.verticalLayout_2.addWidget(self.w_master)
        self.w_location = QtWidgets.QWidget(self.gb_playblast)
        self.w_location.setObjectName("w_location")
        self.horizontalLayout_17 = QtWidgets.QHBoxLayout(self.w_location)
        self.horizontalLayout_17.setSpacing(0)
        self.horizontalLayout_17.setContentsMargins(9, 0, 9, 0)
        self.horizontalLayout_17.setObjectName("horizontalLayout_17")
        self.l_location = QtWidgets.QLabel(self.w_location)
        self.l_location.setObjectName("l_location")
        self.horizontalLayout_17.addWidget(self.l_location)
        spacerItem5 = QtWidgets.QSpacerItem(113, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_17.addItem(spacerItem5)
        self.cb_location = QtWidgets.QComboBox(self.w_location)
        self.cb_location.setMinimumSize(QtCore.QSize(150, 0))
        self.cb_location.setObjectName("cb_location")
        self.horizontalLayout_17.addWidget(self.cb_location)
        self.verticalLayout_2.addWidget(self.w_location)
        self.widget_5 = QtWidgets.QWidget(self.gb_playblast)
        self.widget_5.setObjectName("widget_5")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.widget_5)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setContentsMargins(9, 0, 9, 0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_4 = QtWidgets.QLabel(self.widget_5)
        self.label_4.setObjectName("label_4")
        self.horizontalLayout_3.addWidget(self.label_4)
        spacerItem6 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem6)
        self.cb_formats = QtWidgets.QComboBox(self.widget_5)
        self.cb_formats.setMinimumSize(QtCore.QSize(150, 0))
        self.cb_formats.setObjectName("cb_formats")
        self.horizontalLayout_3.addWidget(self.cb_formats)
        self.verticalLayout_2.addWidget(self.widget_5)
        self.gb_submit = QtWidgets.QGroupBox(self.gb_playblast)
        self.gb_submit.setCheckable(True)
        self.gb_submit.setChecked(True)
        self.gb_submit.setObjectName("gb_submit")
        self.verticalLayout_8 = QtWidgets.QVBoxLayout(self.gb_submit)
        self.verticalLayout_8.setContentsMargins(-1, 15, -1, -1)
        self.verticalLayout_8.setObjectName("verticalLayout_8")
        self.f_manager = QtWidgets.QWidget(self.gb_submit)
        self.f_manager.setObjectName("f_manager")
        self.horizontalLayout_13 = QtWidgets.QHBoxLayout(self.f_manager)
        self.horizontalLayout_13.setContentsMargins(-1, 0, -1, 0)
        self.horizontalLayout_13.setObjectName("horizontalLayout_13")
        self.l_manager = QtWidgets.QLabel(self.f_manager)
        self.l_manager.setObjectName("l_manager")
        self.horizontalLayout_13.addWidget(self.l_manager)
        spacerItem7 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_13.addItem(spacerItem7)
        self.cb_manager = QtWidgets.QComboBox(self.f_manager)
        self.cb_manager.setMinimumSize(QtCore.QSize(150, 0))
        self.cb_manager.setObjectName("cb_manager")
        self.horizontalLayout_13.addWidget(self.cb_manager)
        self.verticalLayout_8.addWidget(self.f_manager)
        self.f_rjPrio = QtWidgets.QWidget(self.gb_submit)
        self.f_rjPrio.setObjectName("f_rjPrio")
        self.horizontalLayout_21 = QtWidgets.QHBoxLayout(self.f_rjPrio)
        self.horizontalLayout_21.setContentsMargins(-1, 0, -1, 0)
        self.horizontalLayout_21.setObjectName("horizontalLayout_21")
        self.l_rjPrio = QtWidgets.QLabel(self.f_rjPrio)
        self.l_rjPrio.setObjectName("l_rjPrio")
        self.horizontalLayout_21.addWidget(self.l_rjPrio)
        spacerItem8 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_21.addItem(spacerItem8)
        self.sp_rjPrio = QtWidgets.QSpinBox(self.f_rjPrio)
        self.sp_rjPrio.setMaximum(100)
        self.sp_rjPrio.setProperty("value", 50)
        self.sp_rjPrio.setObjectName("sp_rjPrio")
        self.horizontalLayout_21.addWidget(self.sp_rjPrio)
        self.verticalLayout_8.addWidget(self.f_rjPrio)
        self.f_rjWidgetsPerTask = QtWidgets.QWidget(self.gb_submit)
        self.f_rjWidgetsPerTask.setObjectName("f_rjWidgetsPerTask")
        self.horizontalLayout_22 = QtWidgets.QHBoxLayout(self.f_rjWidgetsPerTask)
        self.horizontalLayout_22.setContentsMargins(-1, 0, -1, 0)
        self.horizontalLayout_22.setObjectName("horizontalLayout_22")
        self.label_15 = QtWidgets.QLabel(self.f_rjWidgetsPerTask)
        self.label_15.setObjectName("label_15")
        self.horizontalLayout_22.addWidget(self.label_15)
        spacerItem9 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_22.addItem(spacerItem9)
        self.sp_rjFramesPerTask = QtWidgets.QSpinBox(self.f_rjWidgetsPerTask)
        self.sp_rjFramesPerTask.setMaximum(9999)
        self.sp_rjFramesPerTask.setProperty("value", 9999)
        self.sp_rjFramesPerTask.setObjectName("sp_rjFramesPerTask")
        self.horizontalLayout_22.addWidget(self.sp_rjFramesPerTask)
        self.verticalLayout_8.addWidget(self.f_rjWidgetsPerTask)
        self.f_rjTimeout = QtWidgets.QWidget(self.gb_submit)
        self.f_rjTimeout.setObjectName("f_rjTimeout")
        self.horizontalLayout_28 = QtWidgets.QHBoxLayout(self.f_rjTimeout)
        self.horizontalLayout_28.setContentsMargins(-1, 0, -1, 0)
        self.horizontalLayout_28.setObjectName("horizontalLayout_28")
        self.l_rjTimeout = QtWidgets.QLabel(self.f_rjTimeout)
        self.l_rjTimeout.setObjectName("l_rjTimeout")
        self.horizontalLayout_28.addWidget(self.l_rjTimeout)
        spacerItem10 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_28.addItem(spacerItem10)
        self.sp_rjTimeout = QtWidgets.QSpinBox(self.f_rjTimeout)
        self.sp_rjTimeout.setMinimum(1)
        self.sp_rjTimeout.setMaximum(9999)
        self.sp_rjTimeout.setProperty("value", 180)
        self.sp_rjTimeout.setObjectName("sp_rjTimeout")
        self.horizontalLayout_28.addWidget(self.sp_rjTimeout)
        self.verticalLayout_8.addWidget(self.f_rjTimeout)
        self.f_rjSuspended = QtWidgets.QWidget(self.gb_submit)
        self.f_rjSuspended.setObjectName("f_rjSuspended")
        self.horizontalLayout_26 = QtWidgets.QHBoxLayout(self.f_rjSuspended)
        self.horizontalLayout_26.setContentsMargins(-1, 0, -1, 0)
        self.horizontalLayout_26.setObjectName("horizontalLayout_26")
        self.label_18 = QtWidgets.QLabel(self.f_rjSuspended)
        self.label_18.setObjectName("label_18")
        self.horizontalLayout_26.addWidget(self.label_18)
        spacerItem11 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_26.addItem(spacerItem11)
        self.chb_rjSuspended = QtWidgets.QCheckBox(self.f_rjSuspended)
        self.chb_rjSuspended.setText("")
        self.chb_rjSuspended.setChecked(False)
        self.chb_rjSuspended.setObjectName("chb_rjSuspended")
        self.horizontalLayout_26.addWidget(self.chb_rjSuspended)
        self.verticalLayout_8.addWidget(self.f_rjSuspended)
        self.w_dlConcurrentTasks = QtWidgets.QWidget(self.gb_submit)
        self.w_dlConcurrentTasks.setObjectName("w_dlConcurrentTasks")
        self.horizontalLayout_29 = QtWidgets.QHBoxLayout(self.w_dlConcurrentTasks)
        self.horizontalLayout_29.setContentsMargins(-1, 0, -1, 0)
        self.horizontalLayout_29.setObjectName("horizontalLayout_29")
        self.l_dlConcurrentTasks = QtWidgets.QLabel(self.w_dlConcurrentTasks)
        self.l_dlConcurrentTasks.setObjectName("l_dlConcurrentTasks")
        self.horizontalLayout_29.addWidget(self.l_dlConcurrentTasks)
        spacerItem12 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_29.addItem(spacerItem12)
        self.sp_dlConcurrentTasks = QtWidgets.QSpinBox(self.w_dlConcurrentTasks)
        self.sp_dlConcurrentTasks.setMinimum(1)
        self.sp_dlConcurrentTasks.setMaximum(99)
        self.sp_dlConcurrentTasks.setProperty("value", 1)
        self.sp_dlConcurrentTasks.setObjectName("sp_dlConcurrentTasks")
        self.horizontalLayout_29.addWidget(self.sp_dlConcurrentTasks)
        self.verticalLayout_8.addWidget(self.w_dlConcurrentTasks)
        self.verticalLayout_2.addWidget(self.gb_submit)
        self.verticalLayout.addWidget(self.gb_playblast)
        self.groupBox_3 = QtWidgets.QGroupBox(wg_Playblast)
        self.groupBox_3.setCheckable(False)
        self.groupBox_3.setChecked(False)
        self.groupBox_3.setObjectName("groupBox_3")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.groupBox_3)
        self.horizontalLayout_5.setContentsMargins(9, 9, 9, 9)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.scrollArea = QtWidgets.QScrollArea(self.groupBox_3)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 289, 69))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.l_pathLast = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.l_pathLast.setObjectName("l_pathLast")
        self.verticalLayout_3.addWidget(self.l_pathLast)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.horizontalLayout_5.addWidget(self.scrollArea)
        self.b_pathLast = QtWidgets.QToolButton(self.groupBox_3)
        self.b_pathLast.setEnabled(True)
        self.b_pathLast.setArrowType(QtCore.Qt.DownArrow)
        self.b_pathLast.setObjectName("b_pathLast")
        self.horizontalLayout_5.addWidget(self.b_pathLast)
        self.verticalLayout.addWidget(self.groupBox_3)

        self.retranslateUi(wg_Playblast)
        QtCore.QMetaObject.connectSlotsByName(wg_Playblast)
        wg_Playblast.setTabOrder(self.e_name, self.cb_rangeType)
        wg_Playblast.setTabOrder(self.cb_rangeType, self.sp_rangeStart)
        wg_Playblast.setTabOrder(self.sp_rangeStart, self.sp_rangeEnd)
        wg_Playblast.setTabOrder(self.sp_rangeEnd, self.cb_cams)
        wg_Playblast.setTabOrder(self.cb_cams, self.chb_resOverride)
        wg_Playblast.setTabOrder(self.chb_resOverride, self.sp_resWidth)
        wg_Playblast.setTabOrder(self.sp_resWidth, self.sp_resHeight)
        wg_Playblast.setTabOrder(self.sp_resHeight, self.b_resPresets)
        wg_Playblast.setTabOrder(self.b_resPresets, self.cb_formats)
        wg_Playblast.setTabOrder(self.cb_formats, self.gb_submit)
        wg_Playblast.setTabOrder(self.gb_submit, self.cb_manager)
        wg_Playblast.setTabOrder(self.cb_manager, self.sp_rjPrio)
        wg_Playblast.setTabOrder(self.sp_rjPrio, self.sp_rjFramesPerTask)
        wg_Playblast.setTabOrder(self.sp_rjFramesPerTask, self.sp_rjTimeout)
        wg_Playblast.setTabOrder(self.sp_rjTimeout, self.chb_rjSuspended)
        wg_Playblast.setTabOrder(self.chb_rjSuspended, self.sp_dlConcurrentTasks)
        wg_Playblast.setTabOrder(self.sp_dlConcurrentTasks, self.scrollArea)
        wg_Playblast.setTabOrder(self.scrollArea, self.b_pathLast)

    def retranslateUi(self, wg_Playblast):
        wg_Playblast.setWindowTitle(QtWidgets.QApplication.translate("", "Playblast", None, -1))
        self.l_name.setText(QtWidgets.QApplication.translate("", "Name:", None, -1))
        self.l_class.setText(QtWidgets.QApplication.translate("", "Playblast", None, -1))
        self.gb_playblast.setTitle(QtWidgets.QApplication.translate("", "General", None, -1))
        self.label_2.setText(QtWidgets.QApplication.translate("", "Identifier:", None, -1))
        self.b_changeTask.setText(QtWidgets.QApplication.translate("", "change", None, -1))
        self.label_3.setText(QtWidgets.QApplication.translate("", "Framerange:", None, -1))
        self.l_rangeEnd.setText(QtWidgets.QApplication.translate("", "1100", None, -1))
        self.l_rangeStart.setText(QtWidgets.QApplication.translate("", "1001", None, -1))
        self.l_rangeStartInfo.setText(QtWidgets.QApplication.translate("", "Start:", None, -1))
        self.l_rangeEndInfo.setText(QtWidgets.QApplication.translate("", "End:", None, -1))
        self.label.setText(QtWidgets.QApplication.translate("", "Camera:", None, -1))
        self.label_6.setText(QtWidgets.QApplication.translate("", "Resolution override:", None, -1))
        self.b_resPresets.setText(QtWidgets.QApplication.translate("", "▼", None, -1))
        self.l_outPath_2.setText(QtWidgets.QApplication.translate("", "Master Version:", None, -1))
        self.l_location.setText(QtWidgets.QApplication.translate("", "Location:", None, -1))
        self.label_4.setText(QtWidgets.QApplication.translate("", "Outputformat:", None, -1))
        self.gb_submit.setTitle(QtWidgets.QApplication.translate("", "Submit Render Job", None, -1))
        self.l_manager.setText(QtWidgets.QApplication.translate("", "Manager:", None, -1))
        self.l_rjPrio.setText(QtWidgets.QApplication.translate("", "Priority:", None, -1))
        self.label_15.setText(QtWidgets.QApplication.translate("", "Frames per Task:", None, -1))
        self.l_rjTimeout.setText(QtWidgets.QApplication.translate("", "Task Timeout (min)", None, -1))
        self.label_18.setText(QtWidgets.QApplication.translate("", "Submit suspended:", None, -1))
        self.l_dlConcurrentTasks.setText(QtWidgets.QApplication.translate("", "Concurrent Tasks:", None, -1))
        self.groupBox_3.setTitle(QtWidgets.QApplication.translate("", "Last playblast", None, -1))
        self.l_pathLast.setText(QtWidgets.QApplication.translate("", "None", None, -1))
        self.b_pathLast.setText(QtWidgets.QApplication.translate("", "...", None, -1))

