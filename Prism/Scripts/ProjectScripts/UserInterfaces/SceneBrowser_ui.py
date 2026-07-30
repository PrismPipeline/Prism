# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'SceneBrowser.ui'
##
## Created by: Qt User Interface Compiler version 6.8.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from qtpy.QtCore import *  # type: ignore
from qtpy.QtGui import *  # type: ignore
from qtpy.QtWidgets import *  # type: ignore

class Ui_w_sceneBrowser(object):
    def setupUi(self, w_sceneBrowser):
        if not w_sceneBrowser.objectName():
            w_sceneBrowser.setObjectName(u"w_sceneBrowser")
        w_sceneBrowser.resize(801, 499)
        self.horizontalLayout = QHBoxLayout(w_sceneBrowser)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.splitter1 = QSplitter(w_sceneBrowser)
        self.splitter1.setObjectName(u"splitter1")
        self.splitter1.setOrientation(Qt.Orientation.Horizontal)
        self.verticalWidget_3 = QWidget(self.splitter1)
        self.verticalWidget_3.setObjectName(u"verticalWidget_3")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(10)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.verticalWidget_3.sizePolicy().hasHeightForWidth())
        self.verticalWidget_3.setSizePolicy(sizePolicy)
        self.verticalLayout_2 = QVBoxLayout(self.verticalWidget_3)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.splitter2 = QSplitter(self.verticalWidget_3)
        self.splitter2.setObjectName(u"splitter2")
        self.splitter2.setOrientation(Qt.Orientation.Vertical)
        self.horizontalWidget_2 = QWidget(self.splitter2)
        self.horizontalWidget_2.setObjectName(u"horizontalWidget_2")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(10)
        sizePolicy1.setHeightForWidth(self.horizontalWidget_2.sizePolicy().hasHeightForWidth())
        self.horizontalWidget_2.setSizePolicy(sizePolicy1)
        self.horizontalLayout_13 = QHBoxLayout(self.horizontalWidget_2)
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.horizontalLayout_13.setContentsMargins(0, 0, 0, 0)
        self.splitter3 = QSplitter(self.horizontalWidget_2)
        self.splitter3.setObjectName(u"splitter3")
        self.splitter3.setOrientation(Qt.Orientation.Horizontal)
        self.widget_23 = QWidget(self.splitter3)
        self.widget_23.setObjectName(u"widget_23")
        sizePolicy.setHeightForWidth(self.widget_23.sizePolicy().hasHeightForWidth())
        self.widget_23.setSizePolicy(sizePolicy)
        self.verticalLayout_22 = QVBoxLayout(self.widget_23)
        self.verticalLayout_22.setObjectName(u"verticalLayout_22")
        self.verticalLayout_22.setContentsMargins(0, 0, 0, 0)
        self.w_departmentsHeader = QWidget(self.widget_23)
        self.w_departmentsHeader.setObjectName(u"w_departmentsHeader")
        self.verticalLayout_3 = QVBoxLayout(self.w_departmentsHeader)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.l_departments = QLabel(self.w_departmentsHeader)
        self.l_departments.setObjectName(u"l_departments")

        self.verticalLayout_3.addWidget(self.l_departments)


        self.verticalLayout_22.addWidget(self.w_departmentsHeader)

        self.lw_departments = QListWidget(self.widget_23)
        self.lw_departments.setObjectName(u"lw_departments")
        self.lw_departments.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lw_departments.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.lw_departments.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        self.verticalLayout_22.addWidget(self.lw_departments)

        self.splitter3.addWidget(self.widget_23)
        self.w_tasks = QWidget(self.splitter3)
        self.w_tasks.setObjectName(u"w_tasks")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(15)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.w_tasks.sizePolicy().hasHeightForWidth())
        self.w_tasks.setSizePolicy(sizePolicy2)
        self.verticalLayout_23 = QVBoxLayout(self.w_tasks)
        self.verticalLayout_23.setObjectName(u"verticalLayout_23")
        self.verticalLayout_23.setContentsMargins(0, 0, 0, 0)
        self.w_tasksHeader = QWidget(self.w_tasks)
        self.w_tasksHeader.setObjectName(u"w_tasksHeader")
        self.verticalLayout_5 = QVBoxLayout(self.w_tasksHeader)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.l_tasks = QLabel(self.w_tasksHeader)
        self.l_tasks.setObjectName(u"l_tasks")

        self.verticalLayout_5.addWidget(self.l_tasks)


        self.verticalLayout_23.addWidget(self.w_tasksHeader)

        self.lw_tasks = QListWidget(self.w_tasks)
        self.lw_tasks.setObjectName(u"lw_tasks")
        self.lw_tasks.setMaximumSize(QSize(10000, 16777215))
        self.lw_tasks.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lw_tasks.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.lw_tasks.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        self.verticalLayout_23.addWidget(self.lw_tasks)

        self.splitter3.addWidget(self.w_tasks)

        self.horizontalLayout_13.addWidget(self.splitter3)

        self.splitter2.addWidget(self.horizontalWidget_2)
        self.gb_entityInfo = QGroupBox(self.splitter2)
        self.gb_entityInfo.setObjectName(u"gb_entityInfo")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(1)
        sizePolicy3.setHeightForWidth(self.gb_entityInfo.sizePolicy().hasHeightForWidth())
        self.gb_entityInfo.setSizePolicy(sizePolicy3)
        self.gb_entityInfo.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lo_entityDetails = QVBoxLayout(self.gb_entityInfo)
        self.lo_entityDetails.setSpacing(15)
        self.lo_entityDetails.setObjectName(u"lo_entityDetails")
        self.lo_entityDetails.setContentsMargins(9, 18, 9, 0)
        self.w_entityInfo = QWidget(self.gb_entityInfo)
        self.w_entityInfo.setObjectName(u"w_entityInfo")
        self.lo_entityInfo = QGridLayout(self.w_entityInfo)
        self.lo_entityInfo.setObjectName(u"lo_entityInfo")

        self.lo_entityDetails.addWidget(self.w_entityInfo)

        self.verticalSpacer_5 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.lo_entityDetails.addItem(self.verticalSpacer_5)

        self.widget_8 = QWidget(self.gb_entityInfo)
        self.widget_8.setObjectName(u"widget_8")
        self.horizontalLayout_14 = QHBoxLayout(self.widget_8)
        self.horizontalLayout_14.setSpacing(0)
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.horizontalLayout_14.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_14.addItem(self.horizontalSpacer_6)

        self.l_entityPreview = QLabel(self.widget_8)
        self.l_entityPreview.setObjectName(u"l_entityPreview")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.l_entityPreview.sizePolicy().hasHeightForWidth())
        self.l_entityPreview.setSizePolicy(sizePolicy4)
        self.l_entityPreview.setMinimumSize(QSize(100, 100))
        self.l_entityPreview.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.l_entityPreview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout_14.addWidget(self.l_entityPreview)

        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_14.addItem(self.horizontalSpacer_7)


        self.lo_entityDetails.addWidget(self.widget_8)

        self.splitter2.addWidget(self.gb_entityInfo)

        self.verticalLayout_2.addWidget(self.splitter2)

        self.splitter1.addWidget(self.verticalWidget_3)
        self.w_scenefiles = QWidget(self.splitter1)
        self.w_scenefiles.setObjectName(u"w_scenefiles")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy5.setHorizontalStretch(50)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.w_scenefiles.sizePolicy().hasHeightForWidth())
        self.w_scenefiles.setSizePolicy(sizePolicy5)
        self.verticalLayout_4 = QVBoxLayout(self.w_scenefiles)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.w_scenefileHeader = QWidget(self.w_scenefiles)
        self.w_scenefileHeader.setObjectName(u"w_scenefileHeader")
        self.horizontalLayout_12 = QHBoxLayout(self.w_scenefileHeader)
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.horizontalLayout_12.setContentsMargins(0, 0, 0, 0)
        self.l_scenefiles = QLabel(self.w_scenefileHeader)
        self.l_scenefiles.setObjectName(u"l_scenefiles")
        sizePolicy6 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy6.setHorizontalStretch(0)
        sizePolicy6.setVerticalStretch(0)
        sizePolicy6.setHeightForWidth(self.l_scenefiles.sizePolicy().hasHeightForWidth())
        self.l_scenefiles.setSizePolicy(sizePolicy6)

        self.horizontalLayout_12.addWidget(self.l_scenefiles)

        self.widget = QWidget(self.w_scenefileHeader)
        self.widget.setObjectName(u"widget")
        sizePolicy7 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy7.setHorizontalStretch(0)
        sizePolicy7.setVerticalStretch(0)
        sizePolicy7.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy7)
        self.horizontalLayout_2 = QHBoxLayout(self.widget)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.b_sceneLayoutItems = QToolButton(self.widget)
        self.b_sceneLayoutItems.setObjectName(u"b_sceneLayoutItems")
        self.b_sceneLayoutItems.setCheckable(True)

        self.horizontalLayout_2.addWidget(self.b_sceneLayoutItems)

        self.b_sceneLayoutList = QToolButton(self.widget)
        self.b_sceneLayoutList.setObjectName(u"b_sceneLayoutList")
        self.b_sceneLayoutList.setCheckable(True)
        self.b_sceneLayoutList.setChecked(False)

        self.horizontalLayout_2.addWidget(self.b_sceneLayoutList)


        self.horizontalLayout_12.addWidget(self.widget)

        self.b_scenefilter = QToolButton(self.w_scenefileHeader)
        self.b_scenefilter.setObjectName(u"b_scenefilter")
        self.b_scenefilter.setArrowType(Qt.ArrowType.DownArrow)

        self.horizontalLayout_12.addWidget(self.b_scenefilter)


        self.verticalLayout_4.addWidget(self.w_scenefileHeader)

        self.sw_scenefiles = QStackedWidget(self.w_scenefiles)
        self.sw_scenefiles.setObjectName(u"sw_scenefiles")
        self.w_scenePage1 = QWidget()
        self.w_scenePage1.setObjectName(u"w_scenePage1")
        self.horizontalLayout_3 = QHBoxLayout(self.w_scenePage1)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.tw_scenefiles = QTableView(self.w_scenePage1)
        self.tw_scenefiles.setObjectName(u"tw_scenefiles")
        self.tw_scenefiles.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tw_scenefiles.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tw_scenefiles.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tw_scenefiles.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tw_scenefiles.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.tw_scenefiles.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tw_scenefiles.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tw_scenefiles.setSortingEnabled(True)
        self.tw_scenefiles.horizontalHeader().setCascadingSectionResizes(False)
        self.tw_scenefiles.horizontalHeader().setHighlightSections(False)
        self.tw_scenefiles.horizontalHeader().setProperty(u"showSortIndicator", True)
        self.tw_scenefiles.horizontalHeader().setStretchLastSection(False)
        self.tw_scenefiles.verticalHeader().setVisible(False)
        self.tw_scenefiles.verticalHeader().setStretchLastSection(False)

        self.horizontalLayout_3.addWidget(self.tw_scenefiles)

        self.sw_scenefiles.addWidget(self.w_scenePage1)
        self.w_scenePage2 = QWidget()
        self.w_scenePage2.setObjectName(u"w_scenePage2")
        self.verticalLayout = QVBoxLayout(self.w_scenePage2)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.sa_scenefileItems = QScrollArea(self.w_scenePage2)
        self.sa_scenefileItems.setObjectName(u"sa_scenefileItems")
        self.sa_scenefileItems.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sa_scenefileItems.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 552, 447))
        self.sa_scenefileItems.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout.addWidget(self.sa_scenefileItems)

        self.sw_scenefiles.addWidget(self.w_scenePage2)

        self.verticalLayout_4.addWidget(self.sw_scenefiles)

        self.splitter1.addWidget(self.w_scenefiles)

        self.horizontalLayout.addWidget(self.splitter1)


        self.retranslateUi(w_sceneBrowser)

        self.sw_scenefiles.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(w_sceneBrowser)
    # setupUi

    def retranslateUi(self, w_sceneBrowser):
        w_sceneBrowser.setWindowTitle(QCoreApplication.translate("w_sceneBrowser", u"Scene Browser", None))
        self.l_departments.setText(QCoreApplication.translate("w_sceneBrowser", u"Departments:", None))
        self.l_tasks.setText(QCoreApplication.translate("w_sceneBrowser", u"Tasks:", None))
        self.gb_entityInfo.setTitle(QCoreApplication.translate("w_sceneBrowser", u"Entityinfo", None))
        self.l_entityPreview.setText("")
        self.l_scenefiles.setText(QCoreApplication.translate("w_sceneBrowser", u"Files:", None))
        self.b_sceneLayoutItems.setText(QCoreApplication.translate("w_sceneBrowser", u"...", None))
        self.b_sceneLayoutList.setText(QCoreApplication.translate("w_sceneBrowser", u"...", None))
        self.b_scenefilter.setText(QCoreApplication.translate("w_sceneBrowser", u"...", None))
    # retranslateUi

