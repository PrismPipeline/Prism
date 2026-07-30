# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'default_Export.ui'
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
        wg_Export.resize(400, 1259)
        self.verticalLayout = QVBoxLayout(wg_Export)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.w_name = QWidget(wg_Export)
        self.w_name.setObjectName(u"w_name")
        self.horizontalLayout_5 = QHBoxLayout(self.w_name)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(9, 0, 18, 0)
        self.l_name = QLabel(self.w_name)
        self.l_name.setObjectName(u"l_name")

        self.horizontalLayout_5.addWidget(self.l_name)

        self.e_name = QLineEdit(self.w_name)
        self.e_name.setObjectName(u"e_name")
        self.e_name.setMinimumSize(QSize(0, 0))
        self.e_name.setMaximumSize(QSize(9999, 16777215))

        self.horizontalLayout_5.addWidget(self.e_name)

        self.l_class = QLabel(self.w_name)
        self.l_class.setObjectName(u"l_class")
        font = QFont()
        font.setBold(True)
        self.l_class.setFont(font)

        self.horizontalLayout_5.addWidget(self.l_class)


        self.verticalLayout.addWidget(self.w_name)

        self.gb_export = QGroupBox(wg_Export)
        self.gb_export.setObjectName(u"gb_export")
        self.lo_export = QVBoxLayout(self.gb_export)
        self.lo_export.setObjectName(u"lo_export")
        self.w_comment = QWidget(self.gb_export)
        self.w_comment.setObjectName(u"w_comment")
        self.horizontalLayout_16 = QHBoxLayout(self.w_comment)
        self.horizontalLayout_16.setSpacing(0)
        self.horizontalLayout_16.setObjectName(u"horizontalLayout_16")
        self.horizontalLayout_16.setContentsMargins(9, 0, 9, 0)
        self.l_comment = QLabel(self.w_comment)
        self.l_comment.setObjectName(u"l_comment")
        self.l_comment.setMinimumSize(QSize(40, 0))
        self.l_comment.setMaximumSize(QSize(95, 16777215))

        self.horizontalLayout_16.addWidget(self.l_comment)

        self.horizontalSpacer_8 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_16.addItem(self.horizontalSpacer_8)

        self.e_comment = QLineEdit(self.w_comment)
        self.e_comment.setObjectName(u"e_comment")

        self.horizontalLayout_16.addWidget(self.e_comment)


        self.lo_export.addWidget(self.w_comment)

        self.w_context = QWidget(self.gb_export)
        self.w_context.setObjectName(u"w_context")
        self.horizontalLayout_10 = QHBoxLayout(self.w_context)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.horizontalLayout_10.setContentsMargins(9, 0, 9, 0)
        self.label_4 = QLabel(self.w_context)
        self.label_4.setObjectName(u"label_4")

        self.horizontalLayout_10.addWidget(self.label_4)

        self.horizontalSpacer_5 = QSpacerItem(37, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_10.addItem(self.horizontalSpacer_5)

        self.l_context = QLabel(self.w_context)
        self.l_context.setObjectName(u"l_context")

        self.horizontalLayout_10.addWidget(self.l_context)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_10.addItem(self.horizontalSpacer)

        self.b_context = QPushButton(self.w_context)
        self.b_context.setObjectName(u"b_context")

        self.horizontalLayout_10.addWidget(self.b_context)

        self.cb_context = QComboBox(self.w_context)
        self.cb_context.setObjectName(u"cb_context")

        self.horizontalLayout_10.addWidget(self.cb_context)


        self.lo_export.addWidget(self.w_context)

        self.w_taskname = QWidget(self.gb_export)
        self.w_taskname.setObjectName(u"w_taskname")
        self.horizontalLayout_4 = QHBoxLayout(self.w_taskname)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(9, 0, 9, 0)
        self.l_tasklabel = QLabel(self.w_taskname)
        self.l_tasklabel.setObjectName(u"l_tasklabel")

        self.horizontalLayout_4.addWidget(self.l_tasklabel)

        self.l_taskName = QLabel(self.w_taskname)
        self.l_taskName.setObjectName(u"l_taskName")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.l_taskName.sizePolicy().hasHeightForWidth())
        self.l_taskName.setSizePolicy(sizePolicy)
        self.l_taskName.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout_4.addWidget(self.l_taskName)

        self.b_changeTask = QPushButton(self.w_taskname)
        self.b_changeTask.setObjectName(u"b_changeTask")
        self.b_changeTask.setEnabled(True)
        self.b_changeTask.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.horizontalLayout_4.addWidget(self.b_changeTask)


        self.lo_export.addWidget(self.w_taskname)

        self.w_range = QWidget(self.gb_export)
        self.w_range.setObjectName(u"w_range")
        self.horizontalLayout_6 = QHBoxLayout(self.w_range)
        self.horizontalLayout_6.setSpacing(0)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(9, 0, 9, 0)
        self.label_3 = QLabel(self.w_range)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout_6.addWidget(self.label_3)

        self.horizontalSpacer_2 = QSpacerItem(37, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer_2)

        self.cb_rangeType = QComboBox(self.w_range)
        self.cb_rangeType.setObjectName(u"cb_rangeType")

        self.horizontalLayout_6.addWidget(self.cb_rangeType)


        self.lo_export.addWidget(self.w_range)

        self.w_rangeFrames = QWidget(self.gb_export)
        self.w_rangeFrames.setObjectName(u"w_rangeFrames")
        self.gridLayout = QGridLayout(self.w_rangeFrames)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(9, 0, 9, 0)
        self.l_rangeEnd = QLabel(self.w_rangeFrames)
        self.l_rangeEnd.setObjectName(u"l_rangeEnd")
        self.l_rangeEnd.setMinimumSize(QSize(30, 0))
        self.l_rangeEnd.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.l_rangeEnd, 1, 5, 1, 1)

        self.sp_rangeEnd = QSpinBox(self.w_rangeFrames)
        self.sp_rangeEnd.setObjectName(u"sp_rangeEnd")
        self.sp_rangeEnd.setMaximum(99999)
        self.sp_rangeEnd.setValue(1100)

        self.gridLayout.addWidget(self.sp_rangeEnd, 1, 6, 1, 1)

        self.sp_rangeStart = QSpinBox(self.w_rangeFrames)
        self.sp_rangeStart.setObjectName(u"sp_rangeStart")
        self.sp_rangeStart.setMaximum(99999)
        self.sp_rangeStart.setValue(1001)

        self.gridLayout.addWidget(self.sp_rangeStart, 0, 6, 1, 1)

        self.l_rangeStart = QLabel(self.w_rangeFrames)
        self.l_rangeStart.setObjectName(u"l_rangeStart")
        self.l_rangeStart.setMinimumSize(QSize(30, 0))
        self.l_rangeStart.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.l_rangeStart, 0, 5, 1, 1)

        self.l_rangeStartInfo = QLabel(self.w_rangeFrames)
        self.l_rangeStartInfo.setObjectName(u"l_rangeStartInfo")

        self.gridLayout.addWidget(self.l_rangeStartInfo, 0, 0, 1, 1)

        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer_7, 0, 4, 1, 1)

        self.l_rangeEndInfo = QLabel(self.w_rangeFrames)
        self.l_rangeEndInfo.setObjectName(u"l_rangeEndInfo")

        self.gridLayout.addWidget(self.l_rangeEndInfo, 1, 0, 1, 1)


        self.lo_export.addWidget(self.w_rangeFrames)

        self.w_master = QWidget(self.gb_export)
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


        self.lo_export.addWidget(self.w_master)

        self.w_outPath = QWidget(self.gb_export)
        self.w_outPath.setObjectName(u"w_outPath")
        self.horizontalLayout_11 = QHBoxLayout(self.w_outPath)
        self.horizontalLayout_11.setSpacing(0)
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.horizontalLayout_11.setContentsMargins(9, 0, 9, 0)
        self.l_outPath = QLabel(self.w_outPath)
        self.l_outPath.setObjectName(u"l_outPath")

        self.horizontalLayout_11.addWidget(self.l_outPath)

        self.horizontalSpacer_6 = QSpacerItem(113, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_11.addItem(self.horizontalSpacer_6)

        self.cb_outPath = QComboBox(self.w_outPath)
        self.cb_outPath.setObjectName(u"cb_outPath")
        self.cb_outPath.setMinimumSize(QSize(124, 0))

        self.horizontalLayout_11.addWidget(self.cb_outPath)


        self.lo_export.addWidget(self.w_outPath)

        self.w_outType = QWidget(self.gb_export)
        self.w_outType.setObjectName(u"w_outType")
        self.horizontalLayout_9 = QHBoxLayout(self.w_outType)
        self.horizontalLayout_9.setSpacing(0)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.horizontalLayout_9.setContentsMargins(9, 0, 9, 0)
        self.l_outType = QLabel(self.w_outType)
        self.l_outType.setObjectName(u"l_outType")

        self.horizontalLayout_9.addWidget(self.l_outType)

        self.horizontalSpacer_3 = QSpacerItem(113, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_9.addItem(self.horizontalSpacer_3)

        self.cb_outType = QComboBox(self.w_outType)
        self.cb_outType.setObjectName(u"cb_outType")
        self.cb_outType.setMinimumSize(QSize(124, 0))

        self.horizontalLayout_9.addWidget(self.cb_outType)


        self.lo_export.addWidget(self.w_outType)

        self.w_cam = QWidget(self.gb_export)
        self.w_cam.setObjectName(u"w_cam")
        self.horizontalLayout_3 = QHBoxLayout(self.w_cam)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(9, 0, 9, 0)
        self.l_cam = QLabel(self.w_cam)
        self.l_cam.setObjectName(u"l_cam")
        self.l_cam.setMinimumSize(QSize(40, 0))
        self.l_cam.setMaximumSize(QSize(95, 16777215))

        self.horizontalLayout_3.addWidget(self.l_cam)

        self.cb_cam = QComboBox(self.w_cam)
        self.cb_cam.setObjectName(u"cb_cam")

        self.horizontalLayout_3.addWidget(self.cb_cam)


        self.lo_export.addWidget(self.w_cam)

        self.w_sCamShot = QWidget(self.gb_export)
        self.w_sCamShot.setObjectName(u"w_sCamShot")
        self.horizontalLayout_7 = QHBoxLayout(self.w_sCamShot)
        self.horizontalLayout_7.setSpacing(0)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(9, 0, 9, 0)
        self.l_sCamShot = QLabel(self.w_sCamShot)
        self.l_sCamShot.setObjectName(u"l_sCamShot")
        self.l_sCamShot.setMinimumSize(QSize(40, 0))
        self.l_sCamShot.setMaximumSize(QSize(95, 16777215))

        self.horizontalLayout_7.addWidget(self.l_sCamShot)

        self.cb_sCamShot = QComboBox(self.w_sCamShot)
        self.cb_sCamShot.setObjectName(u"cb_sCamShot")

        self.horizontalLayout_7.addWidget(self.cb_sCamShot)


        self.lo_export.addWidget(self.w_sCamShot)

        self.w_selectCam = QWidget(self.gb_export)
        self.w_selectCam.setObjectName(u"w_selectCam")
        self.horizontalLayout_2 = QHBoxLayout(self.w_selectCam)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(9, 0, 9, 0)
        self.b_selectCam = QPushButton(self.w_selectCam)
        self.b_selectCam.setObjectName(u"b_selectCam")
        self.b_selectCam.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.horizontalLayout_2.addWidget(self.b_selectCam)


        self.lo_export.addWidget(self.w_selectCam)

        self.w_additionalOptions = QWidget(self.gb_export)
        self.w_additionalOptions.setObjectName(u"w_additionalOptions")
        self.horizontalLayout_15 = QHBoxLayout(self.w_additionalOptions)
        self.horizontalLayout_15.setObjectName(u"horizontalLayout_15")
        self.horizontalLayout_15.setContentsMargins(9, 0, 9, 0)
        self.l_additionalOptions = QLabel(self.w_additionalOptions)
        self.l_additionalOptions.setObjectName(u"l_additionalOptions")

        self.horizontalLayout_15.addWidget(self.l_additionalOptions)

        self.horizontalSpacer_11 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_15.addItem(self.horizontalSpacer_11)

        self.chb_additionalOptions = QCheckBox(self.w_additionalOptions)
        self.chb_additionalOptions.setObjectName(u"chb_additionalOptions")
        self.chb_additionalOptions.setChecked(False)

        self.horizontalLayout_15.addWidget(self.chb_additionalOptions)


        self.lo_export.addWidget(self.w_additionalOptions)

        self.w_wholeScene = QWidget(self.gb_export)
        self.w_wholeScene.setObjectName(u"w_wholeScene")
        self.horizontalLayout = QHBoxLayout(self.w_wholeScene)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(9, 0, 9, 0)
        self.l_wholeScene = QLabel(self.w_wholeScene)
        self.l_wholeScene.setObjectName(u"l_wholeScene")

        self.horizontalLayout.addWidget(self.l_wholeScene)

        self.horizontalSpacer_4 = QSpacerItem(185, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_4)

        self.chb_wholeScene = QCheckBox(self.w_wholeScene)
        self.chb_wholeScene.setObjectName(u"chb_wholeScene")
        self.chb_wholeScene.setChecked(False)

        self.horizontalLayout.addWidget(self.chb_wholeScene)


        self.lo_export.addWidget(self.w_wholeScene)

        self.gb_objects = QGroupBox(self.gb_export)
        self.gb_objects.setObjectName(u"gb_objects")
        self.gb_objects.setEnabled(True)
        self.verticalLayout_3 = QVBoxLayout(self.gb_objects)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(9, 9, 9, 9)
        self.f_objectList = QFrame(self.gb_objects)
        self.f_objectList.setObjectName(u"f_objectList")
        self.horizontalLayout_8 = QHBoxLayout(self.f_objectList)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.lw_objects = QListWidget(self.f_objectList)
        self.lw_objects.setObjectName(u"lw_objects")
        self.lw_objects.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lw_objects.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.lw_objects.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.lw_objects.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        self.horizontalLayout_8.addWidget(self.lw_objects)


        self.verticalLayout_3.addWidget(self.f_objectList)

        self.b_add = QPushButton(self.gb_objects)
        self.b_add.setObjectName(u"b_add")
        self.b_add.setMinimumSize(QSize(0, 0))
        self.b_add.setMaximumSize(QSize(99999, 16777215))
        self.b_add.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.verticalLayout_3.addWidget(self.b_add)


        self.lo_export.addWidget(self.gb_objects)

        self.gb_submit = QGroupBox(self.gb_export)
        self.gb_submit.setObjectName(u"gb_submit")
        self.gb_submit.setCheckable(True)
        self.gb_submit.setChecked(True)
        self.verticalLayout_8 = QVBoxLayout(self.gb_submit)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(-1, 15, -1, -1)
        self.f_manager = QWidget(self.gb_submit)
        self.f_manager.setObjectName(u"f_manager")
        self.horizontalLayout_14 = QHBoxLayout(self.f_manager)
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.horizontalLayout_14.setContentsMargins(-1, 0, -1, 0)
        self.l_manager = QLabel(self.f_manager)
        self.l_manager.setObjectName(u"l_manager")

        self.horizontalLayout_14.addWidget(self.l_manager)

        self.horizontalSpacer_19 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_14.addItem(self.horizontalSpacer_19)

        self.cb_manager = QComboBox(self.f_manager)
        self.cb_manager.setObjectName(u"cb_manager")
        self.cb_manager.setMinimumSize(QSize(150, 0))

        self.horizontalLayout_14.addWidget(self.cb_manager)


        self.verticalLayout_8.addWidget(self.f_manager)

        self.f_rjPrio = QWidget(self.gb_submit)
        self.f_rjPrio.setObjectName(u"f_rjPrio")
        self.horizontalLayout_21 = QHBoxLayout(self.f_rjPrio)
        self.horizontalLayout_21.setObjectName(u"horizontalLayout_21")
        self.horizontalLayout_21.setContentsMargins(-1, 0, -1, 0)
        self.l_rjPrio = QLabel(self.f_rjPrio)
        self.l_rjPrio.setObjectName(u"l_rjPrio")

        self.horizontalLayout_21.addWidget(self.l_rjPrio)

        self.horizontalSpacer_16 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_21.addItem(self.horizontalSpacer_16)

        self.sp_rjPrio = QSpinBox(self.f_rjPrio)
        self.sp_rjPrio.setObjectName(u"sp_rjPrio")
        self.sp_rjPrio.setMaximum(100)
        self.sp_rjPrio.setValue(50)

        self.horizontalLayout_21.addWidget(self.sp_rjPrio)


        self.verticalLayout_8.addWidget(self.f_rjPrio)

        self.f_rjWidgetsPerTask = QWidget(self.gb_submit)
        self.f_rjWidgetsPerTask.setObjectName(u"f_rjWidgetsPerTask")
        self.horizontalLayout_22 = QHBoxLayout(self.f_rjWidgetsPerTask)
        self.horizontalLayout_22.setObjectName(u"horizontalLayout_22")
        self.horizontalLayout_22.setContentsMargins(-1, 0, -1, 0)
        self.label_15 = QLabel(self.f_rjWidgetsPerTask)
        self.label_15.setObjectName(u"label_15")

        self.horizontalLayout_22.addWidget(self.label_15)

        self.horizontalSpacer_17 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_22.addItem(self.horizontalSpacer_17)

        self.sp_rjFramesPerTask = QSpinBox(self.f_rjWidgetsPerTask)
        self.sp_rjFramesPerTask.setObjectName(u"sp_rjFramesPerTask")
        self.sp_rjFramesPerTask.setMinimum(1)
        self.sp_rjFramesPerTask.setMaximum(9999)
        self.sp_rjFramesPerTask.setValue(9999)

        self.horizontalLayout_22.addWidget(self.sp_rjFramesPerTask)


        self.verticalLayout_8.addWidget(self.f_rjWidgetsPerTask)

        self.f_rjTimeout = QWidget(self.gb_submit)
        self.f_rjTimeout.setObjectName(u"f_rjTimeout")
        self.horizontalLayout_28 = QHBoxLayout(self.f_rjTimeout)
        self.horizontalLayout_28.setObjectName(u"horizontalLayout_28")
        self.horizontalLayout_28.setContentsMargins(-1, 0, -1, 0)
        self.l_rjTimeout = QLabel(self.f_rjTimeout)
        self.l_rjTimeout.setObjectName(u"l_rjTimeout")

        self.horizontalLayout_28.addWidget(self.l_rjTimeout)

        self.horizontalSpacer_23 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_28.addItem(self.horizontalSpacer_23)

        self.sp_rjTimeout = QSpinBox(self.f_rjTimeout)
        self.sp_rjTimeout.setObjectName(u"sp_rjTimeout")
        self.sp_rjTimeout.setMinimum(0)
        self.sp_rjTimeout.setMaximum(9999)
        self.sp_rjTimeout.setValue(180)

        self.horizontalLayout_28.addWidget(self.sp_rjTimeout)


        self.verticalLayout_8.addWidget(self.f_rjTimeout)

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


        self.verticalLayout_8.addWidget(self.f_rjSuspended)

        self.w_dlConcurrentTasks = QWidget(self.gb_submit)
        self.w_dlConcurrentTasks.setObjectName(u"w_dlConcurrentTasks")
        self.horizontalLayout_29 = QHBoxLayout(self.w_dlConcurrentTasks)
        self.horizontalLayout_29.setObjectName(u"horizontalLayout_29")
        self.horizontalLayout_29.setContentsMargins(-1, 0, -1, 0)
        self.l_dlConcurrentTasks = QLabel(self.w_dlConcurrentTasks)
        self.l_dlConcurrentTasks.setObjectName(u"l_dlConcurrentTasks")

        self.horizontalLayout_29.addWidget(self.l_dlConcurrentTasks)

        self.horizontalSpacer_24 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_29.addItem(self.horizontalSpacer_24)

        self.sp_dlConcurrentTasks = QSpinBox(self.w_dlConcurrentTasks)
        self.sp_dlConcurrentTasks.setObjectName(u"sp_dlConcurrentTasks")
        self.sp_dlConcurrentTasks.setMinimum(1)
        self.sp_dlConcurrentTasks.setMaximum(99)
        self.sp_dlConcurrentTasks.setValue(1)

        self.horizontalLayout_29.addWidget(self.sp_dlConcurrentTasks)


        self.verticalLayout_8.addWidget(self.w_dlConcurrentTasks)


        self.lo_export.addWidget(self.gb_submit)

        self.gb_previous = QGroupBox(self.gb_export)
        self.gb_previous.setObjectName(u"gb_previous")
        self.horizontalLayout_13 = QHBoxLayout(self.gb_previous)
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.horizontalLayout_13.setContentsMargins(9, 9, 9, 9)
        self.scrollArea = QScrollArea(self.gb_previous)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 329, 248))
        self.horizontalLayout_12 = QHBoxLayout(self.scrollAreaWidgetContents)
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.l_pathLast = QLabel(self.scrollAreaWidgetContents)
        self.l_pathLast.setObjectName(u"l_pathLast")

        self.horizontalLayout_12.addWidget(self.l_pathLast)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.horizontalLayout_13.addWidget(self.scrollArea)

        self.b_pathLast = QToolButton(self.gb_previous)
        self.b_pathLast.setObjectName(u"b_pathLast")
        self.b_pathLast.setEnabled(True)
        self.b_pathLast.setArrowType(Qt.ArrowType.DownArrow)

        self.horizontalLayout_13.addWidget(self.b_pathLast)


        self.lo_export.addWidget(self.gb_previous)


        self.verticalLayout.addWidget(self.gb_export)

        QWidget.setTabOrder(self.e_name, self.b_context)
        QWidget.setTabOrder(self.b_context, self.cb_context)
        QWidget.setTabOrder(self.cb_context, self.cb_rangeType)
        QWidget.setTabOrder(self.cb_rangeType, self.sp_rangeStart)
        QWidget.setTabOrder(self.sp_rangeStart, self.sp_rangeEnd)
        QWidget.setTabOrder(self.sp_rangeEnd, self.chb_master)
        QWidget.setTabOrder(self.chb_master, self.cb_outPath)
        QWidget.setTabOrder(self.cb_outPath, self.cb_outType)
        QWidget.setTabOrder(self.cb_outType, self.cb_cam)
        QWidget.setTabOrder(self.cb_cam, self.cb_sCamShot)
        QWidget.setTabOrder(self.cb_sCamShot, self.chb_additionalOptions)
        QWidget.setTabOrder(self.chb_additionalOptions, self.chb_wholeScene)
        QWidget.setTabOrder(self.chb_wholeScene, self.lw_objects)
        QWidget.setTabOrder(self.lw_objects, self.gb_submit)
        QWidget.setTabOrder(self.gb_submit, self.cb_manager)
        QWidget.setTabOrder(self.cb_manager, self.sp_rjPrio)
        QWidget.setTabOrder(self.sp_rjPrio, self.sp_rjFramesPerTask)
        QWidget.setTabOrder(self.sp_rjFramesPerTask, self.sp_rjTimeout)
        QWidget.setTabOrder(self.sp_rjTimeout, self.chb_rjSuspended)
        QWidget.setTabOrder(self.chb_rjSuspended, self.sp_dlConcurrentTasks)
        QWidget.setTabOrder(self.sp_dlConcurrentTasks, self.scrollArea)
        QWidget.setTabOrder(self.scrollArea, self.b_pathLast)

        self.retranslateUi(wg_Export)

        QMetaObject.connectSlotsByName(wg_Export)
    # setupUi

    def retranslateUi(self, wg_Export):
        wg_Export.setWindowTitle(QCoreApplication.translate("wg_Export", u"Export", None))
        self.l_name.setText(QCoreApplication.translate("wg_Export", u"Name:", None))
        self.l_class.setText(QCoreApplication.translate("wg_Export", u"Export", None))
        self.gb_export.setTitle(QCoreApplication.translate("wg_Export", u"General", None))
        self.l_comment.setText(QCoreApplication.translate("wg_Export", u"Comment:", None))
        self.label_4.setText(QCoreApplication.translate("wg_Export", u"Context:", None))
        self.l_context.setText("")
        self.b_context.setText(QCoreApplication.translate("wg_Export", u"Select", None))
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
        self.l_outType.setText(QCoreApplication.translate("wg_Export", u"Outputtype:", None))
        self.l_cam.setText(QCoreApplication.translate("wg_Export", u"Camera:", None))
        self.l_sCamShot.setText(QCoreApplication.translate("wg_Export", u"Shot:", None))
        self.b_selectCam.setText(QCoreApplication.translate("wg_Export", u"Select", None))
        self.l_additionalOptions.setText(QCoreApplication.translate("wg_Export", u"Show additional options on publish:", None))
        self.chb_additionalOptions.setText("")
        self.l_wholeScene.setText(QCoreApplication.translate("wg_Export", u"Export whole Scene:", None))
        self.chb_wholeScene.setText("")
        self.gb_objects.setTitle(QCoreApplication.translate("wg_Export", u"Objects", None))
        self.b_add.setText(QCoreApplication.translate("wg_Export", u"Add selected", None))
        self.gb_submit.setTitle(QCoreApplication.translate("wg_Export", u"Submit Render Job", None))
        self.l_manager.setText(QCoreApplication.translate("wg_Export", u"Manager:", None))
        self.l_rjPrio.setText(QCoreApplication.translate("wg_Export", u"Priority:", None))
        self.label_15.setText(QCoreApplication.translate("wg_Export", u"Frames per Task:", None))
        self.l_rjTimeout.setText(QCoreApplication.translate("wg_Export", u"Task Timeout (min)", None))
        self.label_18.setText(QCoreApplication.translate("wg_Export", u"Submit suspended:", None))
        self.chb_rjSuspended.setText("")
        self.l_dlConcurrentTasks.setText(QCoreApplication.translate("wg_Export", u"Concurrent Tasks:", None))
        self.gb_previous.setTitle(QCoreApplication.translate("wg_Export", u"Last export", None))
        self.l_pathLast.setText(QCoreApplication.translate("wg_Export", u"None", None))
        self.b_pathLast.setText(QCoreApplication.translate("wg_Export", u"...", None))
    # retranslateUi

