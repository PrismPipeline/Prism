# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'UserSettings.ui'
##
## Created by: Qt User Interface Compiler version 6.8.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from qtpy.QtCore import *  # type: ignore
from qtpy.QtGui import *  # type: ignore
from qtpy.QtWidgets import *  # type: ignore

class Ui_dlg_UserSettings(object):
    def setupUi(self, dlg_UserSettings):
        if not dlg_UserSettings.objectName():
            dlg_UserSettings.setObjectName(u"dlg_UserSettings")
        dlg_UserSettings.resize(949, 802)
        self.verticalLayout = QVBoxLayout(dlg_UserSettings)
        self.verticalLayout.setSpacing(20)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.splitter = QSplitter(dlg_UserSettings)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.lw_categories = QListWidget(self.splitter)
        self.lw_categories.setObjectName(u"lw_categories")
        self.lw_categories.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.lw_categories.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.splitter.addWidget(self.lw_categories)
        self.scrollArea = QScrollArea(self.splitter)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 637, 734))
        self.horizontalLayout_9 = QHBoxLayout(self.scrollAreaWidgetContents)
        self.horizontalLayout_9.setSpacing(20)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.horizontalLayout_9.setContentsMargins(15, 15, 15, 15)
        self.tw_settings = QTabWidget(self.scrollAreaWidgetContents)
        self.tw_settings.setObjectName(u"tw_settings")
        self.tabWidgetPage4 = QWidget()
        self.tabWidgetPage4.setObjectName(u"tabWidgetPage4")
        self.verticalLayout_3 = QVBoxLayout(self.tabWidgetPage4)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(15, 15, 15, 15)
        self.gb_about = QGroupBox(self.tabWidgetPage4)
        self.gb_about.setObjectName(u"gb_about")
        self.horizontalLayout_11 = QHBoxLayout(self.gb_about)
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.l_about = QLabel(self.gb_about)
        self.l_about.setObjectName(u"l_about")
        self.l_about.setOpenExternalLinks(True)

        self.horizontalLayout_11.addWidget(self.l_about)


        self.verticalLayout_3.addWidget(self.gb_about)

        self.groupBox_3 = QGroupBox(self.tabWidgetPage4)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.verticalLayout_4 = QVBoxLayout(self.groupBox_3)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.w_username = QWidget(self.groupBox_3)
        self.w_username.setObjectName(u"w_username")
        self.gridLayout_2 = QGridLayout(self.w_username)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.l_abbreviation = QLabel(self.w_username)
        self.l_abbreviation.setObjectName(u"l_abbreviation")

        self.gridLayout_2.addWidget(self.l_abbreviation, 1, 0, 1, 1)

        self.l_username = QLabel(self.w_username)
        self.l_username.setObjectName(u"l_username")

        self.gridLayout_2.addWidget(self.l_username, 0, 0, 1, 1)

        self.e_username = QLineEdit(self.w_username)
        self.e_username.setObjectName(u"e_username")

        self.gridLayout_2.addWidget(self.e_username, 0, 2, 1, 1)

        self.e_abbreviation = QLineEdit(self.w_username)
        self.e_abbreviation.setObjectName(u"e_abbreviation")

        self.gridLayout_2.addWidget(self.e_abbreviation, 1, 2, 1, 1)


        self.verticalLayout_4.addWidget(self.w_username)


        self.verticalLayout_3.addWidget(self.groupBox_3)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer_3)

        self.tw_settings.addTab(self.tabWidgetPage4, "")
        self.tabWidgetPage2 = QWidget()
        self.tabWidgetPage2.setObjectName(u"tabWidgetPage2")
        self.verticalLayout_8 = QVBoxLayout(self.tabWidgetPage2)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(15, 15, 15, 15)
        self.w_curPrj = QGroupBox(self.tabWidgetPage2)
        self.w_curPrj.setObjectName(u"w_curPrj")
        self.verticalLayout_6 = QVBoxLayout(self.w_curPrj)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(-1, 18, -1, -1)
        self.widget_5 = QWidget(self.w_curPrj)
        self.widget_5.setObjectName(u"widget_5")
        self.gridLayout = QGridLayout(self.widget_5)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.l_projectName = QLabel(self.widget_5)
        self.l_projectName.setObjectName(u"l_projectName")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.l_projectName.sizePolicy().hasHeightForWidth())
        self.l_projectName.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.l_projectName, 0, 1, 1, 1)

        self.l_projectPath = QLabel(self.widget_5)
        self.l_projectPath.setObjectName(u"l_projectPath")

        self.gridLayout.addWidget(self.l_projectPath, 1, 1, 1, 1)

        self.label_4 = QLabel(self.widget_5)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout.addWidget(self.label_4, 1, 0, 1, 1)

        self.label_2 = QLabel(self.widget_5)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)


        self.verticalLayout_6.addWidget(self.widget_5)

        self.verticalSpacer_9 = QSpacerItem(20, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout_6.addItem(self.verticalSpacer_9)

        self.l_localPath = QLabel(self.w_curPrj)
        self.l_localPath.setObjectName(u"l_localPath")

        self.verticalLayout_6.addWidget(self.l_localPath)

        self.widget_3 = QWidget(self.w_curPrj)
        self.widget_3.setObjectName(u"widget_3")
        self.horizontalLayout = QHBoxLayout(self.widget_3)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.e_localPath = QLineEdit(self.widget_3)
        self.e_localPath.setObjectName(u"e_localPath")

        self.horizontalLayout.addWidget(self.e_localPath)

        self.b_browseLocal = QPushButton(self.widget_3)
        self.b_browseLocal.setObjectName(u"b_browseLocal")
        self.b_browseLocal.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.horizontalLayout.addWidget(self.b_browseLocal)


        self.verticalLayout_6.addWidget(self.widget_3)

        self.w_userUseLocal = QWidget(self.w_curPrj)
        self.w_userUseLocal.setObjectName(u"w_userUseLocal")
        self.horizontalLayout_15 = QHBoxLayout(self.w_userUseLocal)
        self.horizontalLayout_15.setObjectName(u"horizontalLayout_15")
        self.horizontalLayout_15.setContentsMargins(0, 0, 0, 0)
        self.label_5 = QLabel(self.w_userUseLocal)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout_15.addWidget(self.label_5)

        self.horizontalSpacer_10 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_15.addItem(self.horizontalSpacer_10)

        self.cb_userUseLocal = QComboBox(self.w_userUseLocal)
        self.cb_userUseLocal.addItem("")
        self.cb_userUseLocal.addItem("")
        self.cb_userUseLocal.addItem("")
        self.cb_userUseLocal.setObjectName(u"cb_userUseLocal")

        self.horizontalLayout_15.addWidget(self.cb_userUseLocal)


        self.verticalLayout_6.addWidget(self.w_userUseLocal)

        self.w_resetPrjScripts = QWidget(self.w_curPrj)
        self.w_resetPrjScripts.setObjectName(u"w_resetPrjScripts")
        self.horizontalLayout_2 = QHBoxLayout(self.w_resetPrjScripts)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_6.addWidget(self.w_resetPrjScripts)


        self.verticalLayout_8.addWidget(self.w_curPrj)

        self.verticalSpacer_8 = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout_8.addItem(self.verticalSpacer_8)

        self.widget_6 = QWidget(self.tabWidgetPage2)
        self.widget_6.setObjectName(u"widget_6")
        self.horizontalLayout_10 = QHBoxLayout(self.widget_6)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.horizontalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_10.addItem(self.horizontalSpacer_5)

        self.b_manageProjects = QPushButton(self.widget_6)
        self.b_manageProjects.setObjectName(u"b_manageProjects")
        self.b_manageProjects.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.horizontalLayout_10.addWidget(self.b_manageProjects)

        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_10.addItem(self.horizontalSpacer_6)


        self.verticalLayout_8.addWidget(self.widget_6)

        self.w_projects = QWidget(self.tabWidgetPage2)
        self.w_projects.setObjectName(u"w_projects")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(10)
        sizePolicy1.setHeightForWidth(self.w_projects.sizePolicy().hasHeightForWidth())
        self.w_projects.setSizePolicy(sizePolicy1)
        self.lo_projects = QVBoxLayout(self.w_projects)
        self.lo_projects.setObjectName(u"lo_projects")
        self.lo_projects.setContentsMargins(0, 0, 0, 0)
        self.verticalSpacer_4 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.lo_projects.addItem(self.verticalSpacer_4)


        self.verticalLayout_8.addWidget(self.w_projects)

        self.verticalSpacer_10 = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_8.addItem(self.verticalSpacer_10)

        self.tw_settings.addTab(self.tabWidgetPage2, "")
        self.tab_dccApps = QWidget()
        self.tab_dccApps.setObjectName(u"tab_dccApps")
        self.verticalLayout_24 = QVBoxLayout(self.tab_dccApps)
        self.verticalLayout_24.setObjectName(u"verticalLayout_24")
        self.widget_23 = QWidget(self.tab_dccApps)
        self.widget_23.setObjectName(u"widget_23")
        self.verticalLayout_26 = QVBoxLayout(self.widget_23)
        self.verticalLayout_26.setObjectName(u"verticalLayout_26")

        self.verticalLayout_24.addWidget(self.widget_23)

        self.tw_settings.addTab(self.tab_dccApps, "")
        self.tab_Plugins = QWidget()
        self.tab_Plugins.setObjectName(u"tab_Plugins")
        self.verticalLayout_2 = QVBoxLayout(self.tab_Plugins)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.widget = QWidget(self.tab_Plugins)
        self.widget.setObjectName(u"widget")
        self.horizontalLayout_5 = QHBoxLayout(self.widget)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.label_3 = QLabel(self.widget)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout_5.addWidget(self.label_3)

        self.b_createPlugin = QToolButton(self.widget)
        self.b_createPlugin.setObjectName(u"b_createPlugin")

        self.horizontalLayout_5.addWidget(self.b_createPlugin)

        self.b_loadPlugin = QToolButton(self.widget)
        self.b_loadPlugin.setObjectName(u"b_loadPlugin")

        self.horizontalLayout_5.addWidget(self.b_loadPlugin)

        self.b_reloadPlugins = QToolButton(self.widget)
        self.b_reloadPlugins.setObjectName(u"b_reloadPlugins")

        self.horizontalLayout_5.addWidget(self.b_reloadPlugins)

        self.b_managePlugins = QToolButton(self.widget)
        self.b_managePlugins.setObjectName(u"b_managePlugins")

        self.horizontalLayout_5.addWidget(self.b_managePlugins)


        self.verticalLayout_2.addWidget(self.widget)

        self.tw_plugins = QTableWidget(self.tab_Plugins)
        self.tw_plugins.setObjectName(u"tw_plugins")
        self.tw_plugins.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tw_plugins.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tw_plugins.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tw_plugins.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tw_plugins.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tw_plugins.horizontalHeader().setHighlightSections(False)
        self.tw_plugins.verticalHeader().setVisible(False)

        self.verticalLayout_2.addWidget(self.tw_plugins)

        self.tw_settings.addTab(self.tab_Plugins, "")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.verticalLayout_9 = QVBoxLayout(self.tab)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.label_6 = QLabel(self.tab)
        self.label_6.setObjectName(u"label_6")

        self.verticalLayout_9.addWidget(self.label_6)

        self.tw_environment = QTableWidget(self.tab)
        if (self.tw_environment.columnCount() < 2):
            self.tw_environment.setColumnCount(2)
        __qtablewidgetitem = QTableWidgetItem()
        self.tw_environment.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tw_environment.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        self.tw_environment.setObjectName(u"tw_environment")
        self.tw_environment.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tw_environment.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tw_environment.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tw_environment.horizontalHeader().setStretchLastSection(True)
        self.tw_environment.verticalHeader().setVisible(False)

        self.verticalLayout_9.addWidget(self.tw_environment)

        self.widget_2 = QWidget(self.tab)
        self.widget_2.setObjectName(u"widget_2")
        self.horizontalLayout_4 = QHBoxLayout(self.widget_2)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_2 = QSpacerItem(374, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_2)

        self.b_showEnvironment = QPushButton(self.widget_2)
        self.b_showEnvironment.setObjectName(u"b_showEnvironment")

        self.horizontalLayout_4.addWidget(self.b_showEnvironment)


        self.verticalLayout_9.addWidget(self.widget_2)

        self.tw_settings.addTab(self.tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.lo_miscellaneousTab = QVBoxLayout(self.tab_2)
        self.lo_miscellaneousTab.setObjectName(u"lo_miscellaneousTab")
        self.gb_miscellaneous = QGroupBox(self.tab_2)
        self.gb_miscellaneous.setObjectName(u"gb_miscellaneous")
        self.lo_miscellaneous = QVBoxLayout(self.gb_miscellaneous)
        self.lo_miscellaneous.setObjectName(u"lo_miscellaneous")
        self.chb_autosave = QCheckBox(self.gb_miscellaneous)
        self.chb_autosave.setObjectName(u"chb_autosave")
        self.chb_autosave.setChecked(True)

        self.lo_miscellaneous.addWidget(self.chb_autosave)

        self.chb_captureViewport = QCheckBox(self.gb_miscellaneous)
        self.chb_captureViewport.setObjectName(u"chb_captureViewport")
        self.chb_captureViewport.setChecked(True)

        self.lo_miscellaneous.addWidget(self.chb_captureViewport)

        self.chb_captureViewportProduct = QCheckBox(self.gb_miscellaneous)
        self.chb_captureViewportProduct.setObjectName(u"chb_captureViewportProduct")

        self.lo_miscellaneous.addWidget(self.chb_captureViewportProduct)

        self.chb_browserStartup = QCheckBox(self.gb_miscellaneous)
        self.chb_browserStartup.setObjectName(u"chb_browserStartup")
        self.chb_browserStartup.setChecked(True)

        self.lo_miscellaneous.addWidget(self.chb_browserStartup)

        self.chb_mediaThumbnails = QCheckBox(self.gb_miscellaneous)
        self.chb_mediaThumbnails.setObjectName(u"chb_mediaThumbnails")
        self.chb_mediaThumbnails.setChecked(True)

        self.lo_miscellaneous.addWidget(self.chb_mediaThumbnails)

        self.chb_trayStartup = QCheckBox(self.gb_miscellaneous)
        self.chb_trayStartup.setObjectName(u"chb_trayStartup")
        self.chb_trayStartup.setChecked(True)

        self.lo_miscellaneous.addWidget(self.chb_trayStartup)

        self.w_startTray = QWidget(self.gb_miscellaneous)
        self.w_startTray.setObjectName(u"w_startTray")
        self.horizontalLayout_7 = QHBoxLayout(self.w_startTray)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(17, 0, 0, 0)
        self.b_startTray = QPushButton(self.w_startTray)
        self.b_startTray.setObjectName(u"b_startTray")
        self.b_startTray.setMinimumSize(QSize(150, 0))
        self.b_startTray.setMaximumSize(QSize(16777215, 16777215))

        self.horizontalLayout_7.addWidget(self.b_startTray)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_7.addItem(self.horizontalSpacer)


        self.lo_miscellaneous.addWidget(self.w_startTray)

        self.chb_errorReports = QCheckBox(self.gb_miscellaneous)
        self.chb_errorReports.setObjectName(u"chb_errorReports")
        self.chb_errorReports.setChecked(True)

        self.lo_miscellaneous.addWidget(self.chb_errorReports)

        self.chb_debug = QCheckBox(self.gb_miscellaneous)
        self.chb_debug.setObjectName(u"chb_debug")

        self.lo_miscellaneous.addWidget(self.chb_debug)

        self.w_deferredPlugins = QWidget(self.gb_miscellaneous)
        self.w_deferredPlugins.setObjectName(u"w_deferredPlugins")
        self.horizontalLayout_3 = QHBoxLayout(self.w_deferredPlugins)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.l_deferredPlugins = QLabel(self.w_deferredPlugins)
        self.l_deferredPlugins.setObjectName(u"l_deferredPlugins")

        self.horizontalLayout_3.addWidget(self.l_deferredPlugins)

        self.e_deferredPlugins = QLineEdit(self.w_deferredPlugins)
        self.e_deferredPlugins.setObjectName(u"e_deferredPlugins")

        self.horizontalLayout_3.addWidget(self.e_deferredPlugins)


        self.lo_miscellaneous.addWidget(self.w_deferredPlugins)

        self.w_protocolHandler = QWidget(self.gb_miscellaneous)
        self.w_protocolHandler.setObjectName(u"w_protocolHandler")
        self.layout_16 = QHBoxLayout(self.w_protocolHandler)
        self.layout_16.setObjectName(u"layout_16")
        self.layout_16.setContentsMargins(0, 0, 0, 0)
        self.b_protocolHandler = QPushButton(self.w_protocolHandler)
        self.b_protocolHandler.setObjectName(u"b_protocolHandler")

        self.layout_16.addWidget(self.b_protocolHandler)

        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.layout_16.addItem(self.horizontalSpacer_7)


        self.lo_miscellaneous.addWidget(self.w_protocolHandler)

        self.w_styleSheet = QWidget(self.gb_miscellaneous)
        self.w_styleSheet.setObjectName(u"w_styleSheet")
        self.horizontalLayout_8 = QHBoxLayout(self.w_styleSheet)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.l_styleSheet = QLabel(self.w_styleSheet)
        self.l_styleSheet.setObjectName(u"l_styleSheet")

        self.horizontalLayout_8.addWidget(self.l_styleSheet)

        self.cb_styleSheet = QComboBox(self.w_styleSheet)
        self.cb_styleSheet.setObjectName(u"cb_styleSheet")

        self.horizontalLayout_8.addWidget(self.cb_styleSheet)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_8.addItem(self.horizontalSpacer_4)


        self.lo_miscellaneous.addWidget(self.w_styleSheet)

        self.widget_4 = QWidget(self.gb_miscellaneous)
        self.widget_4.setObjectName(u"widget_4")
        self.horizontalLayout_6 = QHBoxLayout(self.widget_4)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.b_importSettings = QToolButton(self.widget_4)
        self.b_importSettings.setObjectName(u"b_importSettings")

        self.horizontalLayout_6.addWidget(self.b_importSettings)

        self.b_exportSettings = QToolButton(self.widget_4)
        self.b_exportSettings.setObjectName(u"b_exportSettings")

        self.horizontalLayout_6.addWidget(self.b_exportSettings)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer_3)


        self.lo_miscellaneous.addWidget(self.widget_4)


        self.lo_miscellaneousTab.addWidget(self.gb_miscellaneous)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.lo_miscellaneousTab.addItem(self.verticalSpacer_2)

        self.tw_settings.addTab(self.tab_2, "")

        self.horizontalLayout_9.addWidget(self.tw_settings)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.splitter.addWidget(self.scrollArea)

        self.verticalLayout.addWidget(self.splitter)

        self.buttonBox = QDialogButtonBox(dlg_UserSettings)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Apply|QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Save)
        self.buttonBox.setCenterButtons(False)

        self.verticalLayout.addWidget(self.buttonBox)

        QWidget.setTabOrder(self.tw_settings, self.e_localPath)
        QWidget.setTabOrder(self.e_localPath, self.b_browseLocal)

        self.retranslateUi(dlg_UserSettings)

        self.tw_settings.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(dlg_UserSettings)
    # setupUi

    def retranslateUi(self, dlg_UserSettings):
        dlg_UserSettings.setWindowTitle(QCoreApplication.translate("dlg_UserSettings", u"User Settings", None))
        self.gb_about.setTitle(QCoreApplication.translate("dlg_UserSettings", u"About", None))
        self.l_about.setText("")
        self.groupBox_3.setTitle(QCoreApplication.translate("dlg_UserSettings", u"User", None))
        self.l_abbreviation.setText(QCoreApplication.translate("dlg_UserSettings", u"Abbreviation:    ", None))
        self.l_username.setText(QCoreApplication.translate("dlg_UserSettings", u"Local Username:", None))
        self.tw_settings.setTabText(self.tw_settings.indexOf(self.tabWidgetPage4), QCoreApplication.translate("dlg_UserSettings", u"General", None))
        self.w_curPrj.setTitle(QCoreApplication.translate("dlg_UserSettings", u"Current Project", None))
#if QT_CONFIG(tooltip)
        self.l_projectName.setToolTip(QCoreApplication.translate("dlg_UserSettings", u"current project", None))
#endif // QT_CONFIG(tooltip)
        self.l_projectName.setText("")
#if QT_CONFIG(tooltip)
        self.l_projectPath.setToolTip(QCoreApplication.translate("dlg_UserSettings", u"current project path", None))
#endif // QT_CONFIG(tooltip)
        self.l_projectPath.setText("")
        self.label_4.setText(QCoreApplication.translate("dlg_UserSettings", u"Path:          ", None))
        self.label_2.setText(QCoreApplication.translate("dlg_UserSettings", u"Name:", None))
        self.l_localPath.setText(QCoreApplication.translate("dlg_UserSettings", u"Local path:", None))
        self.b_browseLocal.setText(QCoreApplication.translate("dlg_UserSettings", u"...", None))
        self.label_5.setText(QCoreApplication.translate("dlg_UserSettings", u"Use additional local project folder:", None))
        self.cb_userUseLocal.setItemText(0, QCoreApplication.translate("dlg_UserSettings", u"Inherit from project", None))
        self.cb_userUseLocal.setItemText(1, QCoreApplication.translate("dlg_UserSettings", u"On", None))
        self.cb_userUseLocal.setItemText(2, QCoreApplication.translate("dlg_UserSettings", u"Off", None))

        self.b_manageProjects.setText(QCoreApplication.translate("dlg_UserSettings", u"Manage Projects...", None))
        self.tw_settings.setTabText(self.tw_settings.indexOf(self.tabWidgetPage2), QCoreApplication.translate("dlg_UserSettings", u"Projects", None))
        self.tw_settings.setTabText(self.tw_settings.indexOf(self.tab_dccApps), QCoreApplication.translate("dlg_UserSettings", u"DCC apps", None))
        self.label_3.setText(QCoreApplication.translate("dlg_UserSettings", u"Loaded Plugins:", None))
#if QT_CONFIG(tooltip)
        self.b_createPlugin.setToolTip(QCoreApplication.translate("dlg_UserSettings", u"Create new plugin...", None))
#endif // QT_CONFIG(tooltip)
        self.b_createPlugin.setText(QCoreApplication.translate("dlg_UserSettings", u"...", None))
#if QT_CONFIG(tooltip)
        self.b_loadPlugin.setToolTip(QCoreApplication.translate("dlg_UserSettings", u"Add existing plugin...", None))
#endif // QT_CONFIG(tooltip)
        self.b_loadPlugin.setText(QCoreApplication.translate("dlg_UserSettings", u"...", None))
#if QT_CONFIG(tooltip)
        self.b_reloadPlugins.setToolTip(QCoreApplication.translate("dlg_UserSettings", u"Reload all plugins", None))
#endif // QT_CONFIG(tooltip)
        self.b_reloadPlugins.setText(QCoreApplication.translate("dlg_UserSettings", u"...", None))
#if QT_CONFIG(tooltip)
        self.b_managePlugins.setToolTip(QCoreApplication.translate("dlg_UserSettings", u"Manage Plugin Paths...", None))
#endif // QT_CONFIG(tooltip)
        self.b_managePlugins.setText(QCoreApplication.translate("dlg_UserSettings", u"...", None))
        self.tw_settings.setTabText(self.tw_settings.indexOf(self.tab_Plugins), QCoreApplication.translate("dlg_UserSettings", u"Plugins", None))
        self.label_6.setText(QCoreApplication.translate("dlg_UserSettings", u"User specific environment variables:", None))
        ___qtablewidgetitem = self.tw_environment.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("dlg_UserSettings", u"Variable", None));
        ___qtablewidgetitem1 = self.tw_environment.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("dlg_UserSettings", u"Value", None));
        self.b_showEnvironment.setText(QCoreApplication.translate("dlg_UserSettings", u"Show current environment", None))
        self.tw_settings.setTabText(self.tw_settings.indexOf(self.tab), QCoreApplication.translate("dlg_UserSettings", u"Environment", None))
        self.gb_miscellaneous.setTitle(QCoreApplication.translate("dlg_UserSettings", u"Miscellaneous", None))
        self.chb_autosave.setText(QCoreApplication.translate("dlg_UserSettings", u"Autosave popup", None))
        self.chb_captureViewport.setText(QCoreApplication.translate("dlg_UserSettings", u"Capture viewport preview on scene save", None))
        self.chb_captureViewportProduct.setText(QCoreApplication.translate("dlg_UserSettings", u"Capture viewport preview for products", None))
        self.chb_browserStartup.setText(QCoreApplication.translate("dlg_UserSettings", u"Open Project Browser on application startup", None))
        self.chb_mediaThumbnails.setText(QCoreApplication.translate("dlg_UserSettings", u"Automatically generate thumbnails for media", None))
        self.chb_trayStartup.setText(QCoreApplication.translate("dlg_UserSettings", u"Show Prism tray icon on system startup", None))
        self.b_startTray.setText(QCoreApplication.translate("dlg_UserSettings", u"Start Prism tray now", None))
        self.chb_errorReports.setText(QCoreApplication.translate("dlg_UserSettings", u"Send anonymous error reports", None))
        self.chb_debug.setText(QCoreApplication.translate("dlg_UserSettings", u"Debug mode", None))
        self.l_deferredPlugins.setText(QCoreApplication.translate("dlg_UserSettings", u"Deferred loaded Plugins:", None))
        self.b_protocolHandler.setText(QCoreApplication.translate("dlg_UserSettings", u"Install Prism Url Protocol Handler", None))
        self.l_styleSheet.setText(QCoreApplication.translate("dlg_UserSettings", u"Standalone Style Sheet:", None))
#if QT_CONFIG(tooltip)
        self.b_importSettings.setToolTip(QCoreApplication.translate("dlg_UserSettings", u"Import User Settings...", None))
#endif // QT_CONFIG(tooltip)
        self.b_importSettings.setText(QCoreApplication.translate("dlg_UserSettings", u"...", None))
#if QT_CONFIG(tooltip)
        self.b_exportSettings.setToolTip(QCoreApplication.translate("dlg_UserSettings", u"Export User Settings...", None))
#endif // QT_CONFIG(tooltip)
        self.b_exportSettings.setText(QCoreApplication.translate("dlg_UserSettings", u"...", None))
        self.tw_settings.setTabText(self.tw_settings.indexOf(self.tab_2), QCoreApplication.translate("dlg_UserSettings", u"Miscellaneous", None))
    # retranslateUi

