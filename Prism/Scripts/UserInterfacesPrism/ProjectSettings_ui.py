# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ProjectSettings.ui'
##
## Created by: Qt User Interface Compiler version 6.8.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from qtpy.QtCore import *  # type: ignore
from qtpy.QtGui import *  # type: ignore
from qtpy.QtWidgets import *  # type: ignore

class Ui_dlg_ProjectSettings(object):
    def setupUi(self, dlg_ProjectSettings):
        if not dlg_ProjectSettings.objectName():
            dlg_ProjectSettings.setObjectName(u"dlg_ProjectSettings")
        dlg_ProjectSettings.resize(891, 759)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(10)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(dlg_ProjectSettings.sizePolicy().hasHeightForWidth())
        dlg_ProjectSettings.setSizePolicy(sizePolicy)
        dlg_ProjectSettings.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.verticalLayout = QVBoxLayout(dlg_ProjectSettings)
        self.verticalLayout.setSpacing(20)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(dlg_ProjectSettings)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.lw_categories = QListWidget(self.splitter)
        self.lw_categories.setObjectName(u"lw_categories")
        self.lw_categories.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.lw_categories.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.splitter.addWidget(self.lw_categories)
        self.tw_settings = QTabWidget(self.splitter)
        self.tw_settings.setObjectName(u"tw_settings")
        self.tw_settings.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_general = QWidget()
        self.tab_general.setObjectName(u"tab_general")
        self.verticalLayout_2 = QVBoxLayout(self.tab_general)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.sa_general = QScrollArea(self.tab_general)
        self.sa_general.setObjectName(u"sa_general")
        self.sa_general.setWidgetResizable(True)
        self.w_saGeneralContent = QWidget()
        self.w_saGeneralContent.setObjectName(u"w_saGeneralContent")
        self.w_saGeneralContent.setGeometry(QRect(0, -183, 644, 879))
        self.verticalLayout_8 = QVBoxLayout(self.w_saGeneralContent)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.w_prjSettings = QWidget(self.w_saGeneralContent)
        self.w_prjSettings.setObjectName(u"w_prjSettings")
        self.w_prjSettings.setEnabled(True)
        self.verticalLayout_9 = QVBoxLayout(self.w_prjSettings)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.verticalSpacer_11 = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout_9.addItem(self.verticalSpacer_11)

        self.widget_5 = QWidget(self.w_prjSettings)
        self.widget_5.setObjectName(u"widget_5")
        self.gridLayout = QGridLayout(self.widget_5)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.e_curPname = QLineEdit(self.widget_5)
        self.e_curPname.setObjectName(u"e_curPname")
        self.e_curPname.setMinimumSize(QSize(300, 0))

        self.gridLayout.addWidget(self.e_curPname, 0, 2, 1, 1)

        self.l_curPname = QLabel(self.widget_5)
        self.l_curPname.setObjectName(u"l_curPname")

        self.gridLayout.addWidget(self.l_curPname, 0, 0, 1, 1)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer_2, 0, 1, 1, 1)


        self.verticalLayout_9.addWidget(self.widget_5)

        self.widget_19 = QWidget(self.w_prjSettings)
        self.widget_19.setObjectName(u"widget_19")
        self.gridLayout_3 = QGridLayout(self.widget_19)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.l_curPpath = QLabel(self.widget_19)
        self.l_curPpath.setObjectName(u"l_curPpath")

        self.gridLayout_3.addWidget(self.l_curPpath, 0, 2, 1, 1)

        self.horizontalSpacer_14 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_3.addItem(self.horizontalSpacer_14, 0, 1, 1, 1)

        self.l_curPname_2 = QLabel(self.widget_19)
        self.l_curPname_2.setObjectName(u"l_curPname_2")

        self.gridLayout_3.addWidget(self.l_curPname_2, 0, 0, 1, 1)


        self.verticalLayout_9.addWidget(self.widget_19)

        self.widget = QWidget(self.w_prjSettings)
        self.widget.setObjectName(u"widget")
        self.horizontalLayout = QHBoxLayout(self.widget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(self.widget)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.l_preview = QLabel(self.widget)
        self.l_preview.setObjectName(u"l_preview")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.l_preview.sizePolicy().hasHeightForWidth())
        self.l_preview.setSizePolicy(sizePolicy1)
        self.l_preview.setMinimumSize(QSize(300, 169))
        self.l_preview.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.l_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout.addWidget(self.l_preview)


        self.verticalLayout_9.addWidget(self.widget)

        self.widget_10 = QWidget(self.w_prjSettings)
        self.widget_10.setObjectName(u"widget_10")
        self.horizontalLayout_5 = QHBoxLayout(self.widget_10)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.label_2 = QLabel(self.widget_10)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_5.addWidget(self.label_2)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_4)

        self.chb_curPuseLocal = QCheckBox(self.widget_10)
        self.chb_curPuseLocal.setObjectName(u"chb_curPuseLocal")
        self.chb_curPuseLocal.setChecked(True)

        self.horizontalLayout_5.addWidget(self.chb_curPuseLocal)


        self.verticalLayout_9.addWidget(self.widget_10)

        self.widget_12 = QWidget(self.w_prjSettings)
        self.widget_12.setObjectName(u"widget_12")
        self.horizontalLayout_16 = QHBoxLayout(self.widget_12)
        self.horizontalLayout_16.setObjectName(u"horizontalLayout_16")
        self.horizontalLayout_16.setContentsMargins(0, 0, 0, 0)
        self.label_6 = QLabel(self.widget_12)
        self.label_6.setObjectName(u"label_6")

        self.horizontalLayout_16.addWidget(self.label_6)

        self.horizontalSpacer_11 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_16.addItem(self.horizontalSpacer_11)

        self.chb_curPuseMaster = QCheckBox(self.widget_12)
        self.chb_curPuseMaster.setObjectName(u"chb_curPuseMaster")
        self.chb_curPuseMaster.setChecked(True)

        self.horizontalLayout_16.addWidget(self.chb_curPuseMaster)


        self.verticalLayout_9.addWidget(self.widget_12)

        self.w_useMasterRender = QWidget(self.w_prjSettings)
        self.w_useMasterRender.setObjectName(u"w_useMasterRender")
        self.horizontalLayout_18 = QHBoxLayout(self.w_useMasterRender)
        self.horizontalLayout_18.setObjectName(u"horizontalLayout_18")
        self.horizontalLayout_18.setContentsMargins(0, 0, 0, 0)
        self.label_8 = QLabel(self.w_useMasterRender)
        self.label_8.setObjectName(u"label_8")

        self.horizontalLayout_18.addWidget(self.label_8)

        self.horizontalSpacer_13 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_18.addItem(self.horizontalSpacer_13)

        self.chb_curPuseMasterRender = QCheckBox(self.w_useMasterRender)
        self.chb_curPuseMasterRender.setObjectName(u"chb_curPuseMasterRender")
        self.chb_curPuseMasterRender.setChecked(False)

        self.horizontalLayout_18.addWidget(self.chb_curPuseMasterRender)


        self.verticalLayout_9.addWidget(self.w_useMasterRender)

        self.w_curPepisodes = QWidget(self.w_prjSettings)
        self.w_curPepisodes.setObjectName(u"w_curPepisodes")
        self.horizontalLayout_29 = QHBoxLayout(self.w_curPepisodes)
        self.horizontalLayout_29.setObjectName(u"horizontalLayout_29")
        self.horizontalLayout_29.setContentsMargins(0, 0, 0, 0)
        self.l_curPepisodes = QLabel(self.w_curPepisodes)
        self.l_curPepisodes.setObjectName(u"l_curPepisodes")

        self.horizontalLayout_29.addWidget(self.l_curPepisodes)

        self.horizontalSpacer_25 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_29.addItem(self.horizontalSpacer_25)

        self.chb_curPepisodes = QCheckBox(self.w_curPepisodes)
        self.chb_curPepisodes.setObjectName(u"chb_curPepisodes")

        self.horizontalLayout_29.addWidget(self.chb_curPepisodes)


        self.verticalLayout_9.addWidget(self.w_curPepisodes)

        self.widget_16 = QWidget(self.w_prjSettings)
        self.widget_16.setObjectName(u"widget_16")
        self.horizontalLayout_20 = QHBoxLayout(self.widget_16)
        self.horizontalLayout_20.setObjectName(u"horizontalLayout_20")
        self.horizontalLayout_20.setContentsMargins(0, 0, 0, 0)
        self.l_backupPublishes = QLabel(self.widget_16)
        self.l_backupPublishes.setObjectName(u"l_backupPublishes")

        self.horizontalLayout_20.addWidget(self.l_backupPublishes)

        self.horizontalSpacer_15 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_20.addItem(self.horizontalSpacer_15)

        self.chb_curPbackupPublishes = QCheckBox(self.widget_16)
        self.chb_curPbackupPublishes.setObjectName(u"chb_curPbackupPublishes")

        self.horizontalLayout_20.addWidget(self.chb_curPbackupPublishes)


        self.verticalLayout_9.addWidget(self.widget_16)

        self.widget_18 = QWidget(self.w_prjSettings)
        self.widget_18.setObjectName(u"widget_18")
        self.horizontalLayout_22 = QHBoxLayout(self.widget_18)
        self.horizontalLayout_22.setObjectName(u"horizontalLayout_22")
        self.horizontalLayout_22.setContentsMargins(0, 0, 0, 0)
        self.l_scenefileLocking = QLabel(self.widget_18)
        self.l_scenefileLocking.setObjectName(u"l_scenefileLocking")

        self.horizontalLayout_22.addWidget(self.l_scenefileLocking)

        self.horizontalSpacer_18 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_22.addItem(self.horizontalSpacer_18)

        self.chb_curPscenefileLocking = QCheckBox(self.widget_18)
        self.chb_curPscenefileLocking.setObjectName(u"chb_curPscenefileLocking")

        self.horizontalLayout_22.addWidget(self.chb_curPscenefileLocking)


        self.verticalLayout_9.addWidget(self.widget_18)

        self.widget_21 = QWidget(self.w_prjSettings)
        self.widget_21.setObjectName(u"widget_21")
        self.horizontalLayout_24 = QHBoxLayout(self.widget_21)
        self.horizontalLayout_24.setObjectName(u"horizontalLayout_24")
        self.horizontalLayout_24.setContentsMargins(0, 0, 0, 0)
        self.l_productTasks = QLabel(self.widget_21)
        self.l_productTasks.setObjectName(u"l_productTasks")

        self.horizontalLayout_24.addWidget(self.l_productTasks)

        self.horizontalSpacer_20 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_24.addItem(self.horizontalSpacer_20)

        self.chb_curPproductTasks = QCheckBox(self.widget_21)
        self.chb_curPproductTasks.setObjectName(u"chb_curPproductTasks")

        self.horizontalLayout_24.addWidget(self.chb_curPproductTasks)


        self.verticalLayout_9.addWidget(self.widget_21)

        self.widget_20 = QWidget(self.w_prjSettings)
        self.widget_20.setObjectName(u"widget_20")
        self.horizontalLayout_23 = QHBoxLayout(self.widget_20)
        self.horizontalLayout_23.setObjectName(u"horizontalLayout_23")
        self.horizontalLayout_23.setContentsMargins(0, 0, 0, 0)
        self.l_matchScenefileVersions = QLabel(self.widget_20)
        self.l_matchScenefileVersions.setObjectName(u"l_matchScenefileVersions")

        self.horizontalLayout_23.addWidget(self.l_matchScenefileVersions)

        self.horizontalSpacer_19 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_23.addItem(self.horizontalSpacer_19)

        self.chb_matchScenefileVersions = QCheckBox(self.widget_20)
        self.chb_matchScenefileVersions.setObjectName(u"chb_matchScenefileVersions")

        self.horizontalLayout_23.addWidget(self.chb_matchScenefileVersions)


        self.verticalLayout_9.addWidget(self.widget_20)

        self.widget_17 = QWidget(self.w_prjSettings)
        self.widget_17.setObjectName(u"widget_17")
        self.horizontalLayout_21 = QHBoxLayout(self.widget_17)
        self.horizontalLayout_21.setObjectName(u"horizontalLayout_21")
        self.horizontalLayout_21.setContentsMargins(0, 0, 0, 0)
        self.l_requirePublishComment = QLabel(self.widget_17)
        self.l_requirePublishComment.setObjectName(u"l_requirePublishComment")

        self.horizontalLayout_21.addWidget(self.l_requirePublishComment)

        self.horizontalSpacer_17 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_21.addItem(self.horizontalSpacer_17)

        self.chb_curPRequirePublishComment = QCheckBox(self.widget_17)
        self.chb_curPRequirePublishComment.setObjectName(u"chb_curPRequirePublishComment")
        self.chb_curPRequirePublishComment.setChecked(True)

        self.horizontalLayout_21.addWidget(self.chb_curPRequirePublishComment)

        self.sp_publishComment = QSpinBox(self.widget_17)
        self.sp_publishComment.setObjectName(u"sp_publishComment")
        self.sp_publishComment.setMinimum(1)
        self.sp_publishComment.setMaximum(999)
        self.sp_publishComment.setValue(3)

        self.horizontalLayout_21.addWidget(self.sp_publishComment)

        self.l_publishCommentChars = QLabel(self.widget_17)
        self.l_publishCommentChars.setObjectName(u"l_publishCommentChars")

        self.horizontalLayout_21.addWidget(self.l_publishCommentChars)


        self.verticalLayout_9.addWidget(self.widget_17)

        self.widget_11 = QWidget(self.w_prjSettings)
        self.widget_11.setObjectName(u"widget_11")
        self.horizontalLayout_14 = QHBoxLayout(self.widget_11)
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.horizontalLayout_14.setContentsMargins(0, 0, 0, 0)
        self.label_4 = QLabel(self.widget_11)
        self.label_4.setObjectName(u"label_4")

        self.horizontalLayout_14.addWidget(self.label_4)

        self.horizontalSpacer_9 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_14.addItem(self.horizontalSpacer_9)

        self.cb_dependencies = QComboBox(self.widget_11)
        self.cb_dependencies.addItem("")
        self.cb_dependencies.addItem("")
        self.cb_dependencies.addItem("")
        self.cb_dependencies.setObjectName(u"cb_dependencies")

        self.horizontalLayout_14.addWidget(self.cb_dependencies)


        self.verticalLayout_9.addWidget(self.widget_11)

        self.w_curPfps = QWidget(self.w_prjSettings)
        self.w_curPfps.setObjectName(u"w_curPfps")
        self.horizontalLayout_6 = QHBoxLayout(self.w_curPfps)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.label_7 = QLabel(self.w_curPfps)
        self.label_7.setObjectName(u"label_7")

        self.horizontalLayout_6.addWidget(self.label_7)

        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer_6)

        self.chb_curPuseFps = QCheckBox(self.w_curPfps)
        self.chb_curPuseFps.setObjectName(u"chb_curPuseFps")
        self.chb_curPuseFps.setChecked(False)

        self.horizontalLayout_6.addWidget(self.chb_curPuseFps)

        self.sp_curPfps = QDoubleSpinBox(self.w_curPfps)
        self.sp_curPfps.setObjectName(u"sp_curPfps")
        self.sp_curPfps.setMinimumSize(QSize(60, 0))
        self.sp_curPfps.setDecimals(3)
        self.sp_curPfps.setMinimum(1.000000000000000)
        self.sp_curPfps.setMaximum(9999.989999999999782)
        self.sp_curPfps.setValue(24.000000000000000)

        self.horizontalLayout_6.addWidget(self.sp_curPfps)


        self.verticalLayout_9.addWidget(self.w_curPfps)

        self.w_prjResolution = QWidget(self.w_prjSettings)
        self.w_prjResolution.setObjectName(u"w_prjResolution")
        self.horizontalLayout_13 = QHBoxLayout(self.w_prjResolution)
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.horizontalLayout_13.setContentsMargins(0, 0, 0, 0)
        self.l_prjResolution = QLabel(self.w_prjResolution)
        self.l_prjResolution.setObjectName(u"l_prjResolution")

        self.horizontalLayout_13.addWidget(self.l_prjResolution)

        self.horizontalSpacer_8 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_13.addItem(self.horizontalSpacer_8)

        self.chb_prjResolution = QCheckBox(self.w_prjResolution)
        self.chb_prjResolution.setObjectName(u"chb_prjResolution")
        self.chb_prjResolution.setChecked(False)

        self.horizontalLayout_13.addWidget(self.chb_prjResolution)

        self.sp_prjResolutionWidth = QSpinBox(self.w_prjResolution)
        self.sp_prjResolutionWidth.setObjectName(u"sp_prjResolutionWidth")
        self.sp_prjResolutionWidth.setMinimumSize(QSize(60, 0))
        self.sp_prjResolutionWidth.setMinimum(1)
        self.sp_prjResolutionWidth.setMaximum(100000)
        self.sp_prjResolutionWidth.setValue(1920)

        self.horizontalLayout_13.addWidget(self.sp_prjResolutionWidth)

        self.l_prjResolutionX = QLabel(self.w_prjResolution)
        self.l_prjResolutionX.setObjectName(u"l_prjResolutionX")

        self.horizontalLayout_13.addWidget(self.l_prjResolutionX)

        self.sp_prjResolutionHeight = QSpinBox(self.w_prjResolution)
        self.sp_prjResolutionHeight.setObjectName(u"sp_prjResolutionHeight")
        self.sp_prjResolutionHeight.setMinimumSize(QSize(60, 0))
        self.sp_prjResolutionHeight.setMinimum(1)
        self.sp_prjResolutionHeight.setMaximum(100000)
        self.sp_prjResolutionHeight.setValue(1080)

        self.horizontalLayout_13.addWidget(self.sp_prjResolutionHeight)


        self.verticalLayout_9.addWidget(self.w_prjResolution)

        self.w_curPversionPadding = QWidget(self.w_prjSettings)
        self.w_curPversionPadding.setObjectName(u"w_curPversionPadding")
        self.horizontalLayout_25 = QHBoxLayout(self.w_curPversionPadding)
        self.horizontalLayout_25.setObjectName(u"horizontalLayout_25")
        self.horizontalLayout_25.setContentsMargins(0, 0, 0, 0)
        self.label_14 = QLabel(self.w_curPversionPadding)
        self.label_14.setObjectName(u"label_14")

        self.horizontalLayout_25.addWidget(self.label_14)

        self.horizontalSpacer_26 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_25.addItem(self.horizontalSpacer_26)

        self.sp_curPversionPadding = QSpinBox(self.w_curPversionPadding)
        self.sp_curPversionPadding.setObjectName(u"sp_curPversionPadding")
        self.sp_curPversionPadding.setMinimumSize(QSize(60, 0))
        self.sp_curPversionPadding.setMinimum(1)
        self.sp_curPversionPadding.setValue(4)

        self.horizontalLayout_25.addWidget(self.sp_curPversionPadding)


        self.verticalLayout_9.addWidget(self.w_curPversionPadding)

        self.w_curPframePadding = QWidget(self.w_prjSettings)
        self.w_curPframePadding.setObjectName(u"w_curPframePadding")
        self.horizontalLayout_26 = QHBoxLayout(self.w_curPframePadding)
        self.horizontalLayout_26.setObjectName(u"horizontalLayout_26")
        self.horizontalLayout_26.setContentsMargins(0, 0, 0, 0)
        self.label_15 = QLabel(self.w_curPframePadding)
        self.label_15.setObjectName(u"label_15")

        self.horizontalLayout_26.addWidget(self.label_15)

        self.horizontalSpacer_27 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_26.addItem(self.horizontalSpacer_27)

        self.sp_curPframePadding = QSpinBox(self.w_curPframePadding)
        self.sp_curPframePadding.setObjectName(u"sp_curPframePadding")
        self.sp_curPframePadding.setMinimumSize(QSize(60, 0))
        self.sp_curPframePadding.setMinimum(1)
        self.sp_curPframePadding.setValue(4)

        self.horizontalLayout_26.addWidget(self.sp_curPframePadding)


        self.verticalLayout_9.addWidget(self.w_curPframePadding)

        self.w_expectedPrjPath_2 = QWidget(self.w_prjSettings)
        self.w_expectedPrjPath_2.setObjectName(u"w_expectedPrjPath_2")
        self.gridLayout_5 = QGridLayout(self.w_expectedPrjPath_2)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.gridLayout_5.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_24 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_5.addItem(self.horizontalSpacer_24, 0, 1, 1, 1)

        self.e_version = QLineEdit(self.w_expectedPrjPath_2)
        self.e_version.setObjectName(u"e_version")
        self.e_version.setMinimumSize(QSize(300, 0))

        self.gridLayout_5.addWidget(self.e_version, 0, 2, 1, 1)

        self.l_expectedPrjPath_2 = QLabel(self.w_expectedPrjPath_2)
        self.l_expectedPrjPath_2.setObjectName(u"l_expectedPrjPath_2")

        self.gridLayout_5.addWidget(self.l_expectedPrjPath_2, 0, 0, 1, 1)


        self.verticalLayout_9.addWidget(self.w_expectedPrjPath_2)

        self.w_reqPlugins = QWidget(self.w_prjSettings)
        self.w_reqPlugins.setObjectName(u"w_reqPlugins")
        self.gridLayout_2 = QGridLayout(self.w_reqPlugins)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_16 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_2.addItem(self.horizontalSpacer_16, 0, 1, 1, 1)

        self.e_reqPlugins = QLineEdit(self.w_reqPlugins)
        self.e_reqPlugins.setObjectName(u"e_reqPlugins")
        self.e_reqPlugins.setMinimumSize(QSize(300, 0))

        self.gridLayout_2.addWidget(self.e_reqPlugins, 0, 2, 1, 1)

        self.b_reqPlugins = QToolButton(self.w_reqPlugins)
        self.b_reqPlugins.setObjectName(u"b_reqPlugins")
        self.b_reqPlugins.setArrowType(Qt.ArrowType.DownArrow)

        self.gridLayout_2.addWidget(self.b_reqPlugins, 0, 3, 1, 1)

        self.l_reqPlugins = QLabel(self.w_reqPlugins)
        self.l_reqPlugins.setObjectName(u"l_reqPlugins")

        self.gridLayout_2.addWidget(self.l_reqPlugins, 0, 0, 1, 1)


        self.verticalLayout_9.addWidget(self.w_reqPlugins)

        self.w_disabledPlugins = QWidget(self.w_prjSettings)
        self.w_disabledPlugins.setObjectName(u"w_disabledPlugins")
        self.gridLayout_6 = QGridLayout(self.w_disabledPlugins)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.gridLayout_6.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_28 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_6.addItem(self.horizontalSpacer_28, 0, 1, 1, 1)

        self.e_disabledPlugins = QLineEdit(self.w_disabledPlugins)
        self.e_disabledPlugins.setObjectName(u"e_disabledPlugins")
        self.e_disabledPlugins.setMinimumSize(QSize(300, 0))

        self.gridLayout_6.addWidget(self.e_disabledPlugins, 0, 2, 1, 1)

        self.b_disabledPlugins = QToolButton(self.w_disabledPlugins)
        self.b_disabledPlugins.setObjectName(u"b_disabledPlugins")
        self.b_disabledPlugins.setArrowType(Qt.ArrowType.DownArrow)

        self.gridLayout_6.addWidget(self.b_disabledPlugins, 0, 3, 1, 1)

        self.l_disabledPlugins = QLabel(self.w_disabledPlugins)
        self.l_disabledPlugins.setObjectName(u"l_disabledPlugins")

        self.gridLayout_6.addWidget(self.l_disabledPlugins, 0, 0, 1, 1)


        self.verticalLayout_9.addWidget(self.w_disabledPlugins)

        self.w_expectedPrjPath = QWidget(self.w_prjSettings)
        self.w_expectedPrjPath.setObjectName(u"w_expectedPrjPath")
        self.gridLayout_4 = QGridLayout(self.w_expectedPrjPath)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_21 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_4.addItem(self.horizontalSpacer_21, 0, 1, 1, 1)

        self.e_expectedPrjPath = QLineEdit(self.w_expectedPrjPath)
        self.e_expectedPrjPath.setObjectName(u"e_expectedPrjPath")
        self.e_expectedPrjPath.setMinimumSize(QSize(300, 0))

        self.gridLayout_4.addWidget(self.e_expectedPrjPath, 0, 2, 1, 1)

        self.b_expectedPrjPath = QToolButton(self.w_expectedPrjPath)
        self.b_expectedPrjPath.setObjectName(u"b_expectedPrjPath")

        self.gridLayout_4.addWidget(self.b_expectedPrjPath, 0, 3, 1, 1)

        self.l_expectedPrjPath = QLabel(self.w_expectedPrjPath)
        self.l_expectedPrjPath.setObjectName(u"l_expectedPrjPath")

        self.gridLayout_4.addWidget(self.l_expectedPrjPath, 0, 0, 1, 1)


        self.verticalLayout_9.addWidget(self.w_expectedPrjPath)

        self.w_expectedPrismVersion = QWidget(self.w_prjSettings)
        self.w_expectedPrismVersion.setObjectName(u"w_expectedPrismVersion")
        self.gridLayout_7 = QGridLayout(self.w_expectedPrismVersion)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.gridLayout_7.setContentsMargins(0, 0, 0, 0)
        self.l_expectedPrismVersion = QLabel(self.w_expectedPrismVersion)
        self.l_expectedPrismVersion.setObjectName(u"l_expectedPrismVersion")

        self.gridLayout_7.addWidget(self.l_expectedPrismVersion, 0, 0, 1, 1)

        self.e_expectedPrismVersion = QLineEdit(self.w_expectedPrismVersion)
        self.e_expectedPrismVersion.setObjectName(u"e_expectedPrismVersion")
        self.e_expectedPrismVersion.setMinimumSize(QSize(300, 0))

        self.gridLayout_7.addWidget(self.e_expectedPrismVersion, 0, 2, 1, 1)

        self.cb_expectedPrismVersion = QComboBox(self.w_expectedPrismVersion)
        self.cb_expectedPrismVersion.setObjectName(u"cb_expectedPrismVersion")

        self.gridLayout_7.addWidget(self.cb_expectedPrismVersion, 0, 3, 1, 1)

        self.horizontalSpacer_29 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_7.addItem(self.horizontalSpacer_29, 0, 1, 1, 1)


        self.verticalLayout_9.addWidget(self.w_expectedPrismVersion)

        self.w_defaultImportStateName = QWidget(self.w_prjSettings)
        self.w_defaultImportStateName.setObjectName(u"w_defaultImportStateName")
        self.gridLayout_defaultImportStateName = QGridLayout(self.w_defaultImportStateName)
        self.gridLayout_defaultImportStateName.setObjectName(u"gridLayout_defaultImportStateName")
        self.gridLayout_defaultImportStateName.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_defaultImportStateName = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_defaultImportStateName.addItem(self.horizontalSpacer_defaultImportStateName, 0, 1, 1, 1)

        self.e_defaultImportStateName = QLineEdit(self.w_defaultImportStateName)
        self.e_defaultImportStateName.setObjectName(u"e_defaultImportStateName")
        self.e_defaultImportStateName.setMinimumSize(QSize(300, 0))

        self.gridLayout_defaultImportStateName.addWidget(self.e_defaultImportStateName, 0, 2, 1, 1)

        self.l_defaultImportStateName = QLabel(self.w_defaultImportStateName)
        self.l_defaultImportStateName.setObjectName(u"l_defaultImportStateName")

        self.gridLayout_defaultImportStateName.addWidget(self.l_defaultImportStateName, 0, 0, 1, 1)


        self.verticalLayout_9.addWidget(self.w_defaultImportStateName)

        self.w_manageProductTags = QWidget(self.w_prjSettings)
        self.w_manageProductTags.setObjectName(u"w_manageProductTags")
        self.horizontalLayout_manageProductTags = QHBoxLayout(self.w_manageProductTags)
        self.horizontalLayout_manageProductTags.setObjectName(u"horizontalLayout_manageProductTags")
        self.horizontalLayout_manageProductTags.setContentsMargins(0, 0, 0, 0)
        self.l_manageProductTags = QLabel(self.w_manageProductTags)
        self.l_manageProductTags.setObjectName(u"l_manageProductTags")

        self.horizontalLayout_manageProductTags.addWidget(self.l_manageProductTags)

        self.horizontalSpacer_manageProductTags = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_manageProductTags.addItem(self.horizontalSpacer_manageProductTags)

        self.b_manageProductTags = QPushButton(self.w_manageProductTags)
        self.b_manageProductTags.setObjectName(u"b_manageProductTags")

        self.horizontalLayout_manageProductTags.addWidget(self.b_manageProductTags)


        self.verticalLayout_9.addWidget(self.w_manageProductTags)

        self.widget_15 = QWidget(self.w_prjSettings)
        self.widget_15.setObjectName(u"widget_15")
        self.horizontalLayout_11 = QHBoxLayout(self.widget_15)
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.horizontalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_10 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_11.addItem(self.horizontalSpacer_10)

        self.b_importSettings = QToolButton(self.widget_15)
        self.b_importSettings.setObjectName(u"b_importSettings")

        self.horizontalLayout_11.addWidget(self.b_importSettings)

        self.b_exportSettings = QToolButton(self.widget_15)
        self.b_exportSettings.setObjectName(u"b_exportSettings")

        self.horizontalLayout_11.addWidget(self.b_exportSettings)


        self.verticalLayout_9.addWidget(self.widget_15)

        self.verticalSpacer_12 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_9.addItem(self.verticalSpacer_12)


        self.verticalLayout_8.addWidget(self.w_prjSettings)

        self.sa_general.setWidget(self.w_saGeneralContent)

        self.verticalLayout_2.addWidget(self.sa_general)

        self.tw_settings.addTab(self.tab_general, "")
        self.tab_departments = QWidget()
        self.tab_departments.setObjectName(u"tab_departments")
        self.verticalLayout_7 = QVBoxLayout(self.tab_departments)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.widget_9 = QWidget(self.tab_departments)
        self.widget_9.setObjectName(u"widget_9")
        self.horizontalLayout_10 = QHBoxLayout(self.widget_9)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.horizontalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.widget_4 = QWidget(self.widget_9)
        self.widget_4.setObjectName(u"widget_4")
        self.verticalLayout_5 = QVBoxLayout(self.widget_4)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.w_assetDepartmentHeader = QWidget(self.widget_4)
        self.w_assetDepartmentHeader.setObjectName(u"w_assetDepartmentHeader")
        self.horizontalLayout_8 = QHBoxLayout(self.w_assetDepartmentHeader)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.label_12 = QLabel(self.w_assetDepartmentHeader)
        self.label_12.setObjectName(u"label_12")

        self.horizontalLayout_8.addWidget(self.label_12)


        self.verticalLayout_5.addWidget(self.w_assetDepartmentHeader)

        self.tw_assetDepartments = QTableWidget(self.widget_4)
        if (self.tw_assetDepartments.columnCount() < 2):
            self.tw_assetDepartments.setColumnCount(2)
        __qtablewidgetitem = QTableWidgetItem()
        self.tw_assetDepartments.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tw_assetDepartments.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        self.tw_assetDepartments.setObjectName(u"tw_assetDepartments")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(10)
        sizePolicy2.setHeightForWidth(self.tw_assetDepartments.sizePolicy().hasHeightForWidth())
        self.tw_assetDepartments.setSizePolicy(sizePolicy2)
        self.tw_assetDepartments.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tw_assetDepartments.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tw_assetDepartments.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tw_assetDepartments.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tw_assetDepartments.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tw_assetDepartments.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tw_assetDepartments.setCornerButtonEnabled(False)
        self.tw_assetDepartments.setColumnCount(2)
        self.tw_assetDepartments.horizontalHeader().setHighlightSections(False)
        self.tw_assetDepartments.horizontalHeader().setStretchLastSection(True)
        self.tw_assetDepartments.verticalHeader().setHighlightSections(False)

        self.verticalLayout_5.addWidget(self.tw_assetDepartments)

        self.w_taskPresetsAsset = QWidget(self.widget_4)
        self.w_taskPresetsAsset.setObjectName(u"w_taskPresetsAsset")
        self.horizontalLayout_12 = QHBoxLayout(self.w_taskPresetsAsset)
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.horizontalLayout_12.setContentsMargins(0, -1, 0, 0)
        self.l_taskPresetsAsset = QLabel(self.w_taskPresetsAsset)
        self.l_taskPresetsAsset.setObjectName(u"l_taskPresetsAsset")

        self.horizontalLayout_12.addWidget(self.l_taskPresetsAsset)

        self.horizontalSpacer_22 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_12.addItem(self.horizontalSpacer_22)

        self.b_addTaskPresetsAsset = QToolButton(self.w_taskPresetsAsset)
        self.b_addTaskPresetsAsset.setObjectName(u"b_addTaskPresetsAsset")

        self.horizontalLayout_12.addWidget(self.b_addTaskPresetsAsset)

        self.b_removeTaskPresetsAsset = QToolButton(self.w_taskPresetsAsset)
        self.b_removeTaskPresetsAsset.setObjectName(u"b_removeTaskPresetsAsset")

        self.horizontalLayout_12.addWidget(self.b_removeTaskPresetsAsset)


        self.verticalLayout_5.addWidget(self.w_taskPresetsAsset)

        self.lw_taskPresetsAsset = QListWidget(self.widget_4)
        self.lw_taskPresetsAsset.setObjectName(u"lw_taskPresetsAsset")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(3)
        sizePolicy3.setHeightForWidth(self.lw_taskPresetsAsset.sizePolicy().hasHeightForWidth())
        self.lw_taskPresetsAsset.setSizePolicy(sizePolicy3)
        self.lw_taskPresetsAsset.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lw_taskPresetsAsset.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.lw_taskPresetsAsset.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.lw_taskPresetsAsset.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        self.verticalLayout_5.addWidget(self.lw_taskPresetsAsset)


        self.horizontalLayout_10.addWidget(self.widget_4)

        self.widget_7 = QWidget(self.widget_9)
        self.widget_7.setObjectName(u"widget_7")
        self.verticalLayout_6 = QVBoxLayout(self.widget_7)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.w_shotDepartmentHeader = QWidget(self.widget_7)
        self.w_shotDepartmentHeader.setObjectName(u"w_shotDepartmentHeader")
        self.horizontalLayout_9 = QHBoxLayout(self.w_shotDepartmentHeader)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.horizontalLayout_9.setContentsMargins(0, 0, 0, 0)
        self.label_13 = QLabel(self.w_shotDepartmentHeader)
        self.label_13.setObjectName(u"label_13")

        self.horizontalLayout_9.addWidget(self.label_13)


        self.verticalLayout_6.addWidget(self.w_shotDepartmentHeader)

        self.tw_shotDepartments = QTableWidget(self.widget_7)
        if (self.tw_shotDepartments.columnCount() < 2):
            self.tw_shotDepartments.setColumnCount(2)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tw_shotDepartments.setHorizontalHeaderItem(0, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.tw_shotDepartments.setHorizontalHeaderItem(1, __qtablewidgetitem3)
        self.tw_shotDepartments.setObjectName(u"tw_shotDepartments")
        sizePolicy2.setHeightForWidth(self.tw_shotDepartments.sizePolicy().hasHeightForWidth())
        self.tw_shotDepartments.setSizePolicy(sizePolicy2)
        self.tw_shotDepartments.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tw_shotDepartments.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tw_shotDepartments.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tw_shotDepartments.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tw_shotDepartments.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tw_shotDepartments.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tw_shotDepartments.setCornerButtonEnabled(False)
        self.tw_shotDepartments.setColumnCount(2)
        self.tw_shotDepartments.horizontalHeader().setHighlightSections(False)
        self.tw_shotDepartments.horizontalHeader().setStretchLastSection(True)
        self.tw_shotDepartments.verticalHeader().setHighlightSections(False)

        self.verticalLayout_6.addWidget(self.tw_shotDepartments)

        self.w_taskPresetsShot = QWidget(self.widget_7)
        self.w_taskPresetsShot.setObjectName(u"w_taskPresetsShot")
        self.horizontalLayout_15 = QHBoxLayout(self.w_taskPresetsShot)
        self.horizontalLayout_15.setObjectName(u"horizontalLayout_15")
        self.horizontalLayout_15.setContentsMargins(0, -1, 0, 0)
        self.l_taskPresetsShot = QLabel(self.w_taskPresetsShot)
        self.l_taskPresetsShot.setObjectName(u"l_taskPresetsShot")

        self.horizontalLayout_15.addWidget(self.l_taskPresetsShot)

        self.horizontalSpacer_23 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_15.addItem(self.horizontalSpacer_23)

        self.b_addTaskPresetsShot = QToolButton(self.w_taskPresetsShot)
        self.b_addTaskPresetsShot.setObjectName(u"b_addTaskPresetsShot")

        self.horizontalLayout_15.addWidget(self.b_addTaskPresetsShot)

        self.b_removeTaskPresetsShot = QToolButton(self.w_taskPresetsShot)
        self.b_removeTaskPresetsShot.setObjectName(u"b_removeTaskPresetsShot")

        self.horizontalLayout_15.addWidget(self.b_removeTaskPresetsShot)


        self.verticalLayout_6.addWidget(self.w_taskPresetsShot)

        self.lw_taskPresetsShot = QListWidget(self.widget_7)
        self.lw_taskPresetsShot.setObjectName(u"lw_taskPresetsShot")
        sizePolicy3.setHeightForWidth(self.lw_taskPresetsShot.sizePolicy().hasHeightForWidth())
        self.lw_taskPresetsShot.setSizePolicy(sizePolicy3)
        self.lw_taskPresetsShot.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lw_taskPresetsShot.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.lw_taskPresetsShot.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.lw_taskPresetsShot.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        self.verticalLayout_6.addWidget(self.lw_taskPresetsShot)


        self.horizontalLayout_10.addWidget(self.widget_7)


        self.verticalLayout_7.addWidget(self.widget_9)

        self.widget_14 = QWidget(self.tab_departments)
        self.widget_14.setObjectName(u"widget_14")
        self.horizontalLayout_7 = QHBoxLayout(self.widget_14)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(-1, 0, -1, 0)
        self.chb_allowAdditionalTasks = QCheckBox(self.widget_14)
        self.chb_allowAdditionalTasks.setObjectName(u"chb_allowAdditionalTasks")
        self.chb_allowAdditionalTasks.setChecked(True)

        self.horizontalLayout_7.addWidget(self.chb_allowAdditionalTasks)


        self.verticalLayout_7.addWidget(self.widget_14)

        self.tw_settings.addTab(self.tab_departments, "")
        self.tab_locations = QWidget()
        self.tab_locations.setObjectName(u"tab_locations")
        self.verticalLayout_3 = QVBoxLayout(self.tab_locations)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.w_exportLocationHeader = QWidget(self.tab_locations)
        self.w_exportLocationHeader.setObjectName(u"w_exportLocationHeader")
        self.lo_exportLocationsHeader = QHBoxLayout(self.w_exportLocationHeader)
        self.lo_exportLocationsHeader.setObjectName(u"lo_exportLocationsHeader")
        self.lo_exportLocationsHeader.setContentsMargins(0, 0, 0, 0)
        self.label_5 = QLabel(self.w_exportLocationHeader)
        self.label_5.setObjectName(u"label_5")

        self.lo_exportLocationsHeader.addWidget(self.label_5)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.lo_exportLocationsHeader.addItem(self.horizontalSpacer_5)


        self.verticalLayout_3.addWidget(self.w_exportLocationHeader)

        self.tw_exportPaths = QTableWidget(self.tab_locations)
        if (self.tw_exportPaths.columnCount() < 2):
            self.tw_exportPaths.setColumnCount(2)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.tw_exportPaths.setHorizontalHeaderItem(0, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.tw_exportPaths.setHorizontalHeaderItem(1, __qtablewidgetitem5)
        self.tw_exportPaths.setObjectName(u"tw_exportPaths")
        self.tw_exportPaths.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tw_exportPaths.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tw_exportPaths.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tw_exportPaths.setColumnCount(2)
        self.tw_exportPaths.horizontalHeader().setStretchLastSection(True)
        self.tw_exportPaths.verticalHeader().setVisible(False)

        self.verticalLayout_3.addWidget(self.tw_exportPaths)

        self.widget_6 = QWidget(self.tab_locations)
        self.widget_6.setObjectName(u"widget_6")
        self.horizontalLayout_4 = QHBoxLayout(self.widget_6)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_3)

        self.b_addExportPath = QPushButton(self.widget_6)
        self.b_addExportPath.setObjectName(u"b_addExportPath")

        self.horizontalLayout_4.addWidget(self.b_addExportPath)

        self.b_removeExportPath = QPushButton(self.widget_6)
        self.b_removeExportPath.setObjectName(u"b_removeExportPath")

        self.horizontalLayout_4.addWidget(self.b_removeExportPath)


        self.verticalLayout_3.addWidget(self.widget_6)

        self.verticalSpacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout_3.addItem(self.verticalSpacer)

        self.w_renderLocationHeader = QWidget(self.tab_locations)
        self.w_renderLocationHeader.setObjectName(u"w_renderLocationHeader")
        self.lo_renderLocationsHeader = QHBoxLayout(self.w_renderLocationHeader)
        self.lo_renderLocationsHeader.setObjectName(u"lo_renderLocationsHeader")
        self.lo_renderLocationsHeader.setContentsMargins(0, 0, 0, 0)
        self.label_11 = QLabel(self.w_renderLocationHeader)
        self.label_11.setObjectName(u"label_11")

        self.lo_renderLocationsHeader.addWidget(self.label_11)

        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.lo_renderLocationsHeader.addItem(self.horizontalSpacer_7)


        self.verticalLayout_3.addWidget(self.w_renderLocationHeader)

        self.tw_renderPaths = QTableWidget(self.tab_locations)
        if (self.tw_renderPaths.columnCount() < 2):
            self.tw_renderPaths.setColumnCount(2)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.tw_renderPaths.setHorizontalHeaderItem(0, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.tw_renderPaths.setHorizontalHeaderItem(1, __qtablewidgetitem7)
        self.tw_renderPaths.setObjectName(u"tw_renderPaths")
        self.tw_renderPaths.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tw_renderPaths.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.tw_renderPaths.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tw_renderPaths.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tw_renderPaths.setColumnCount(2)
        self.tw_renderPaths.horizontalHeader().setStretchLastSection(True)
        self.tw_renderPaths.verticalHeader().setVisible(False)

        self.verticalLayout_3.addWidget(self.tw_renderPaths)

        self.widget_8 = QWidget(self.tab_locations)
        self.widget_8.setObjectName(u"widget_8")
        self.horizontalLayout_17 = QHBoxLayout(self.widget_8)
        self.horizontalLayout_17.setObjectName(u"horizontalLayout_17")
        self.horizontalLayout_17.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_12 = QSpacerItem(672, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_17.addItem(self.horizontalSpacer_12)

        self.b_addRenderPath = QPushButton(self.widget_8)
        self.b_addRenderPath.setObjectName(u"b_addRenderPath")

        self.horizontalLayout_17.addWidget(self.b_addRenderPath)

        self.b_removeRenderPath = QPushButton(self.widget_8)
        self.b_removeRenderPath.setObjectName(u"b_removeRenderPath")

        self.horizontalLayout_17.addWidget(self.b_removeRenderPath)


        self.verticalLayout_3.addWidget(self.widget_8)

        self.tw_settings.addTab(self.tab_locations, "")
        self.tab_folderStructure = QWidget()
        self.tab_folderStructure.setObjectName(u"tab_folderStructure")
        self.lo_structureTab = QGridLayout(self.tab_folderStructure)
        self.lo_structureTab.setObjectName(u"lo_structureTab")
        self.widget_3 = QWidget(self.tab_folderStructure)
        self.widget_3.setObjectName(u"widget_3")
        self.horizontalLayout_3 = QHBoxLayout(self.widget_3)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.label_10 = QLabel(self.widget_3)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setWordWrap(True)

        self.horizontalLayout_3.addWidget(self.label_10)

        self.b_resetStructure = QToolButton(self.widget_3)
        self.b_resetStructure.setObjectName(u"b_resetStructure")
        self.b_resetStructure.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.horizontalLayout_3.addWidget(self.b_resetStructure)


        self.lo_structureTab.addWidget(self.widget_3, 1, 0, 1, 1)

        self.sa_structure = QScrollArea(self.tab_folderStructure)
        self.sa_structure.setObjectName(u"sa_structure")
        self.sa_structure.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 656, 628))
        self.lo_structure = QGridLayout(self.scrollAreaWidgetContents)
        self.lo_structure.setObjectName(u"lo_structure")
        self.sa_structure.setWidget(self.scrollAreaWidgetContents)

        self.lo_structureTab.addWidget(self.sa_structure, 0, 0, 1, 1)

        self.tw_settings.addTab(self.tab_folderStructure, "")
        self.tab_environment = QWidget()
        self.tab_environment.setObjectName(u"tab_environment")
        self.verticalLayout_4 = QVBoxLayout(self.tab_environment)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.label_3 = QLabel(self.tab_environment)
        self.label_3.setObjectName(u"label_3")

        self.verticalLayout_4.addWidget(self.label_3)

        self.tw_environment = QTableWidget(self.tab_environment)
        if (self.tw_environment.columnCount() < 2):
            self.tw_environment.setColumnCount(2)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.tw_environment.setHorizontalHeaderItem(0, __qtablewidgetitem8)
        __qtablewidgetitem9 = QTableWidgetItem()
        self.tw_environment.setHorizontalHeaderItem(1, __qtablewidgetitem9)
        self.tw_environment.setObjectName(u"tw_environment")
        self.tw_environment.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tw_environment.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tw_environment.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tw_environment.horizontalHeader().setStretchLastSection(True)
        self.tw_environment.verticalHeader().setVisible(False)

        self.verticalLayout_4.addWidget(self.tw_environment)

        self.widget_2 = QWidget(self.tab_environment)
        self.widget_2.setObjectName(u"widget_2")
        self.horizontalLayout_2 = QHBoxLayout(self.widget_2)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer = QSpacerItem(374, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.b_showEnvironment = QPushButton(self.widget_2)
        self.b_showEnvironment.setObjectName(u"b_showEnvironment")

        self.horizontalLayout_2.addWidget(self.b_showEnvironment)


        self.verticalLayout_4.addWidget(self.widget_2)

        self.tw_settings.addTab(self.tab_environment, "")
        self.tab_hooks = QWidget()
        self.tab_hooks.setObjectName(u"tab_hooks")
        self.horizontalLayout_19 = QHBoxLayout(self.tab_hooks)
        self.horizontalLayout_19.setObjectName(u"horizontalLayout_19")
        self.widget_13 = QWidget(self.tab_hooks)
        self.widget_13.setObjectName(u"widget_13")
        self.horizontalLayout_28 = QHBoxLayout(self.widget_13)
        self.horizontalLayout_28.setObjectName(u"horizontalLayout_28")
        self.splitter_2 = QSplitter(self.widget_13)
        self.splitter_2.setObjectName(u"splitter_2")
        self.splitter_2.setOrientation(Qt.Orientation.Horizontal)
        self.widget_23 = QWidget(self.splitter_2)
        self.widget_23.setObjectName(u"widget_23")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy4.setHorizontalStretch(4)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.widget_23.sizePolicy().hasHeightForWidth())
        self.widget_23.setSizePolicy(sizePolicy4)
        self.verticalLayout_10 = QVBoxLayout(self.widget_23)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.widget_22 = QWidget(self.widget_23)
        self.widget_22.setObjectName(u"widget_22")
        self.horizontalLayout_27 = QHBoxLayout(self.widget_22)
        self.horizontalLayout_27.setObjectName(u"horizontalLayout_27")
        self.horizontalLayout_27.setContentsMargins(0, 0, 0, 0)
        self.label_9 = QLabel(self.widget_22)
        self.label_9.setObjectName(u"label_9")

        self.horizontalLayout_27.addWidget(self.label_9)

        self.b_addHook = QToolButton(self.widget_22)
        self.b_addHook.setObjectName(u"b_addHook")

        self.horizontalLayout_27.addWidget(self.b_addHook)

        self.b_removeHook = QToolButton(self.widget_22)
        self.b_removeHook.setObjectName(u"b_removeHook")

        self.horizontalLayout_27.addWidget(self.b_removeHook)


        self.verticalLayout_10.addWidget(self.widget_22)

        self.lw_hooks = QListWidget(self.widget_23)
        self.lw_hooks.setObjectName(u"lw_hooks")
        self.lw_hooks.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lw_hooks.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.lw_hooks.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.lw_hooks.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.lw_hooks.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        self.verticalLayout_10.addWidget(self.lw_hooks)

        self.splitter_2.addWidget(self.widget_23)
        self.widget_24 = QWidget(self.splitter_2)
        self.widget_24.setObjectName(u"widget_24")
        sizePolicy.setHeightForWidth(self.widget_24.sizePolicy().hasHeightForWidth())
        self.widget_24.setSizePolicy(sizePolicy)
        self.verticalLayout_11 = QVBoxLayout(self.widget_24)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.te_hook = QTextEdit(self.widget_24)
        self.te_hook.setObjectName(u"te_hook")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy5.setHorizontalStretch(10)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.te_hook.sizePolicy().hasHeightForWidth())
        self.te_hook.setSizePolicy(sizePolicy5)
        self.te_hook.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.te_hook.setReadOnly(False)

        self.verticalLayout_11.addWidget(self.te_hook)

        self.b_saveHook = QPushButton(self.widget_24)
        self.b_saveHook.setObjectName(u"b_saveHook")
        self.b_saveHook.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.verticalLayout_11.addWidget(self.b_saveHook)

        self.splitter_2.addWidget(self.widget_24)

        self.horizontalLayout_28.addWidget(self.splitter_2)


        self.horizontalLayout_19.addWidget(self.widget_13)

        self.tw_settings.addTab(self.tab_hooks, "")
        self.splitter.addWidget(self.tw_settings)

        self.verticalLayout.addWidget(self.splitter)

        self.buttonBox = QDialogButtonBox(dlg_ProjectSettings)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Apply|QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Save)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(dlg_ProjectSettings)
        self.buttonBox.accepted.connect(dlg_ProjectSettings.accept)
        self.buttonBox.rejected.connect(dlg_ProjectSettings.reject)

        self.tw_settings.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(dlg_ProjectSettings)
    # setupUi

    def retranslateUi(self, dlg_ProjectSettings):
        dlg_ProjectSettings.setWindowTitle(QCoreApplication.translate("dlg_ProjectSettings", u"Project Settings", None))
        self.l_curPname.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Project Name:", None))
        self.l_curPpath.setText("")
        self.l_curPname_2.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Project Path:", None))
        self.label.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Image:", None))
        self.l_preview.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Preview image", None))
        self.label_2.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Use additional local project folder:", None))
        self.chb_curPuseLocal.setText("")
        self.label_6.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Use master product versions:", None))
        self.chb_curPuseMaster.setText("")
        self.label_8.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Use master media versions:", None))
        self.chb_curPuseMasterRender.setText("")
        self.l_curPepisodes.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Use Episodes:", None))
        self.chb_curPepisodes.setText("")
        self.l_backupPublishes.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Backup scenefiles on publish:", None))
        self.chb_curPbackupPublishes.setText("")
        self.l_scenefileLocking.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Enable scenefile locking:", None))
        self.chb_curPscenefileLocking.setText("")
        self.l_productTasks.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Link Products and Media to tasks:", None))
        self.chb_curPproductTasks.setText("")
        self.l_matchScenefileVersions.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Match product/media version to scenefile version number:", None))
        self.chb_matchScenefileVersions.setText("")
        self.l_requirePublishComment.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Require publish comment:", None))
        self.chb_curPRequirePublishComment.setText("")
        self.sp_publishComment.setSuffix("")
        self.l_publishCommentChars.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Characters", None))
        self.label_4.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Track dependencies:", None))
        self.cb_dependencies.setItemText(0, QCoreApplication.translate("dlg_ProjectSettings", u"Always", None))
        self.cb_dependencies.setItemText(1, QCoreApplication.translate("dlg_ProjectSettings", u"On Publish", None))
        self.cb_dependencies.setItemText(2, QCoreApplication.translate("dlg_ProjectSettings", u"Never", None))

        self.label_7.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Frames per second:", None))
        self.chb_curPuseFps.setText("")
        self.l_prjResolution.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Resolution:", None))
        self.chb_prjResolution.setText("")
        self.l_prjResolutionX.setText(QCoreApplication.translate("dlg_ProjectSettings", u"x", None))
        self.label_14.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Version Padding:", None))
        self.label_15.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Frame Padding:", None))
#if QT_CONFIG(tooltip)
        self.w_expectedPrjPath_2.setToolTip(QCoreApplication.translate("dlg_ProjectSettings", u"Specifies the version of the project. Prism can change the behavior of specific features to provide backwards compatibility with projects, which were created with older Prism versions.", None))
#endif // QT_CONFIG(tooltip)
        self.l_expectedPrjPath_2.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Project Version:", None))
        self.b_reqPlugins.setText(QCoreApplication.translate("dlg_ProjectSettings", u"...", None))
        self.l_reqPlugins.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Required Plugins:", None))
        self.b_disabledPlugins.setText(QCoreApplication.translate("dlg_ProjectSettings", u"...", None))
        self.l_disabledPlugins.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Disabled Plugins:", None))
        self.b_expectedPrjPath.setText(QCoreApplication.translate("dlg_ProjectSettings", u"...", None))
        self.l_expectedPrjPath.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Expected Project Path:", None))
        self.l_expectedPrismVersion.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Expected Prism Version(s):", None))
        self.l_defaultImportStateName.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Import State Name Template:", None))
        self.l_manageProductTags.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Product Tags:", None))
        self.b_manageProductTags.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Manage Product Tags", None))
#if QT_CONFIG(tooltip)
        self.b_importSettings.setToolTip(QCoreApplication.translate("dlg_ProjectSettings", u"Import Project Settings...", None))
#endif // QT_CONFIG(tooltip)
        self.b_importSettings.setText(QCoreApplication.translate("dlg_ProjectSettings", u"...", None))
#if QT_CONFIG(tooltip)
        self.b_exportSettings.setToolTip(QCoreApplication.translate("dlg_ProjectSettings", u"Export Project settings...", None))
#endif // QT_CONFIG(tooltip)
        self.b_exportSettings.setText(QCoreApplication.translate("dlg_ProjectSettings", u"...", None))
        self.tw_settings.setTabText(self.tw_settings.indexOf(self.tab_general), QCoreApplication.translate("dlg_ProjectSettings", u"General", None))
        self.label_12.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Asset Departments:", None))
        ___qtablewidgetitem = self.tw_assetDepartments.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Department", None));
        ___qtablewidgetitem1 = self.tw_assetDepartments.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Default Tasks", None));
        self.l_taskPresetsAsset.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Asset Task Presets:", None))
        self.b_addTaskPresetsAsset.setText(QCoreApplication.translate("dlg_ProjectSettings", u"...", None))
        self.b_removeTaskPresetsAsset.setText(QCoreApplication.translate("dlg_ProjectSettings", u"...", None))
        self.label_13.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Shot Departments:", None))
        ___qtablewidgetitem2 = self.tw_shotDepartments.horizontalHeaderItem(0)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Department", None));
        ___qtablewidgetitem3 = self.tw_shotDepartments.horizontalHeaderItem(1)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Default Tasks", None));
        self.l_taskPresetsShot.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Shot Task Presets:", None))
        self.b_addTaskPresetsShot.setText(QCoreApplication.translate("dlg_ProjectSettings", u"...", None))
        self.b_removeTaskPresetsShot.setText(QCoreApplication.translate("dlg_ProjectSettings", u"...", None))
        self.chb_allowAdditionalTasks.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Allow creation of additional tasks", None))
        self.tw_settings.setTabText(self.tw_settings.indexOf(self.tab_departments), QCoreApplication.translate("dlg_ProjectSettings", u"Departments", None))
        self.label_5.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Additional Export Locations:", None))
        ___qtablewidgetitem4 = self.tw_exportPaths.horizontalHeaderItem(0)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Name", None));
        ___qtablewidgetitem5 = self.tw_exportPaths.horizontalHeaderItem(1)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Path", None));
        self.b_addExportPath.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Add", None))
        self.b_removeExportPath.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Remove", None))
        self.label_11.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Additional Render Locations:", None))
        ___qtablewidgetitem6 = self.tw_renderPaths.horizontalHeaderItem(0)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Name", None));
        ___qtablewidgetitem7 = self.tw_renderPaths.horizontalHeaderItem(1)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Path", None));
        self.b_addRenderPath.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Add", None))
        self.b_removeRenderPath.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Remove", None))
        self.tw_settings.setTabText(self.tw_settings.indexOf(self.tab_locations), QCoreApplication.translate("dlg_ProjectSettings", u"Locations", None))
        self.label_10.setText(QCoreApplication.translate("dlg_ProjectSettings", u"WARNING: Changing the project structure after the project is created can have unexpected effects for existing data in your project.", None))
        self.b_resetStructure.setText(QCoreApplication.translate("dlg_ProjectSettings", u"...", None))
        self.tw_settings.setTabText(self.tw_settings.indexOf(self.tab_folderStructure), QCoreApplication.translate("dlg_ProjectSettings", u"Folder Structure", None))
        self.label_3.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Project specific environment variables:", None))
        ___qtablewidgetitem8 = self.tw_environment.horizontalHeaderItem(0)
        ___qtablewidgetitem8.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Variable", None));
        ___qtablewidgetitem9 = self.tw_environment.horizontalHeaderItem(1)
        ___qtablewidgetitem9.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Value", None));
        self.b_showEnvironment.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Show current environment", None))
        self.tw_settings.setTabText(self.tw_settings.indexOf(self.tab_environment), QCoreApplication.translate("dlg_ProjectSettings", u"Environment", None))
        self.label_9.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Hooks:", None))
        self.b_addHook.setText(QCoreApplication.translate("dlg_ProjectSettings", u"...", None))
        self.b_removeHook.setText(QCoreApplication.translate("dlg_ProjectSettings", u"...", None))
        self.b_saveHook.setText(QCoreApplication.translate("dlg_ProjectSettings", u"Save", None))
        self.tw_settings.setTabText(self.tw_settings.indexOf(self.tab_hooks), QCoreApplication.translate("dlg_ProjectSettings", u"Hooks", None))
    # retranslateUi

