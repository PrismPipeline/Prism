# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'UserSettings.ui'
#
# Created: Tue Aug  8 18:14:53 2023
#      by: qtpy-uic 2.0.5
#
# WARNING! All changes made in this file will be lost!

from qtpy import QtCore, QtGui, QtWidgets

class Ui_dlg_UserSettings(object):
    def setupUi(self, dlg_UserSettings):
        dlg_UserSettings.setObjectName("dlg_UserSettings")
        dlg_UserSettings.resize(949, 802)
        self.verticalLayout = QtWidgets.QVBoxLayout(dlg_UserSettings)
        self.verticalLayout.setSpacing(20)
        self.verticalLayout.setObjectName("verticalLayout")
        self.splitter = QtWidgets.QSplitter(dlg_UserSettings)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.lw_categories = QtWidgets.QListWidget(self.splitter)
        self.lw_categories.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.lw_categories.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.lw_categories.setObjectName("lw_categories")
        self.scrollArea = QtWidgets.QScrollArea(self.splitter)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 597, 739))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.horizontalLayout_9 = QtWidgets.QHBoxLayout(self.scrollAreaWidgetContents)
        self.horizontalLayout_9.setSpacing(20)
        self.horizontalLayout_9.setContentsMargins(15, 15, 15, 15)
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        self.tw_settings = QtWidgets.QTabWidget(self.scrollAreaWidgetContents)
        self.tw_settings.setObjectName("tw_settings")
        self.tabWidgetPage4 = QtWidgets.QWidget()
        self.tabWidgetPage4.setObjectName("tabWidgetPage4")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.tabWidgetPage4)
        self.verticalLayout_3.setContentsMargins(15, 15, 15, 15)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.gb_about = QtWidgets.QGroupBox(self.tabWidgetPage4)
        self.gb_about.setObjectName("gb_about")
        self.horizontalLayout_11 = QtWidgets.QHBoxLayout(self.gb_about)
        self.horizontalLayout_11.setObjectName("horizontalLayout_11")
        self.l_about = QtWidgets.QLabel(self.gb_about)
        self.l_about.setText("")
        self.l_about.setOpenExternalLinks(True)
        self.l_about.setObjectName("l_about")
        self.horizontalLayout_11.addWidget(self.l_about)
        self.verticalLayout_3.addWidget(self.gb_about)
        self.groupBox_3 = QtWidgets.QGroupBox(self.tabWidgetPage4)
        self.groupBox_3.setObjectName("groupBox_3")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.groupBox_3)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.w_username = QtWidgets.QWidget(self.groupBox_3)
        self.w_username.setObjectName("w_username")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.w_username)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.l_abbreviation = QtWidgets.QLabel(self.w_username)
        self.l_abbreviation.setObjectName("l_abbreviation")
        self.gridLayout_2.addWidget(self.l_abbreviation, 1, 0, 1, 1)
        self.l_username = QtWidgets.QLabel(self.w_username)
        self.l_username.setObjectName("l_username")
        self.gridLayout_2.addWidget(self.l_username, 0, 0, 1, 1)
        self.e_username = QtWidgets.QLineEdit(self.w_username)
        self.e_username.setObjectName("e_username")
        self.gridLayout_2.addWidget(self.e_username, 0, 2, 1, 1)
        self.e_abbreviation = QtWidgets.QLineEdit(self.w_username)
        self.e_abbreviation.setObjectName("e_abbreviation")
        self.gridLayout_2.addWidget(self.e_abbreviation, 1, 2, 1, 1)
        self.verticalLayout_4.addWidget(self.w_username)
        self.verticalLayout_3.addWidget(self.groupBox_3)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_3.addItem(spacerItem)
        self.tw_settings.addTab(self.tabWidgetPage4, "")
        self.tabWidgetPage2 = QtWidgets.QWidget()
        self.tabWidgetPage2.setObjectName("tabWidgetPage2")
        self.verticalLayout_8 = QtWidgets.QVBoxLayout(self.tabWidgetPage2)
        self.verticalLayout_8.setContentsMargins(15, 15, 15, 15)
        self.verticalLayout_8.setObjectName("verticalLayout_8")
        self.w_curPrj = QtWidgets.QGroupBox(self.tabWidgetPage2)
        self.w_curPrj.setObjectName("w_curPrj")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.w_curPrj)
        self.verticalLayout_6.setContentsMargins(-1, 18, -1, -1)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.widget_5 = QtWidgets.QWidget(self.w_curPrj)
        self.widget_5.setObjectName("widget_5")
        self.gridLayout = QtWidgets.QGridLayout(self.widget_5)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.l_projectName = QtWidgets.QLabel(self.widget_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.l_projectName.sizePolicy().hasHeightForWidth())
        self.l_projectName.setSizePolicy(sizePolicy)
        self.l_projectName.setText("")
        self.l_projectName.setObjectName("l_projectName")
        self.gridLayout.addWidget(self.l_projectName, 0, 1, 1, 1)
        self.l_projectPath = QtWidgets.QLabel(self.widget_5)
        self.l_projectPath.setText("")
        self.l_projectPath.setObjectName("l_projectPath")
        self.gridLayout.addWidget(self.l_projectPath, 1, 1, 1, 1)
        self.label_4 = QtWidgets.QLabel(self.widget_5)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 1, 0, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.widget_5)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)
        self.verticalLayout_6.addWidget(self.widget_5)
        spacerItem1 = QtWidgets.QSpacerItem(20, 15, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.verticalLayout_6.addItem(spacerItem1)
        self.l_localPath = QtWidgets.QLabel(self.w_curPrj)
        self.l_localPath.setObjectName("l_localPath")
        self.verticalLayout_6.addWidget(self.l_localPath)
        self.widget_3 = QtWidgets.QWidget(self.w_curPrj)
        self.widget_3.setObjectName("widget_3")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget_3)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.e_localPath = QtWidgets.QLineEdit(self.widget_3)
        self.e_localPath.setObjectName("e_localPath")
        self.horizontalLayout.addWidget(self.e_localPath)
        self.b_browseLocal = QtWidgets.QPushButton(self.widget_3)
        self.b_browseLocal.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.b_browseLocal.setObjectName("b_browseLocal")
        self.horizontalLayout.addWidget(self.b_browseLocal)
        self.verticalLayout_6.addWidget(self.widget_3)
        self.w_userUseLocal = QtWidgets.QWidget(self.w_curPrj)
        self.w_userUseLocal.setObjectName("w_userUseLocal")
        self.horizontalLayout_15 = QtWidgets.QHBoxLayout(self.w_userUseLocal)
        self.horizontalLayout_15.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_15.setObjectName("horizontalLayout_15")
        self.label_5 = QtWidgets.QLabel(self.w_userUseLocal)
        self.label_5.setObjectName("label_5")
        self.horizontalLayout_15.addWidget(self.label_5)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_15.addItem(spacerItem2)
        self.cb_userUseLocal = QtWidgets.QComboBox(self.w_userUseLocal)
        self.cb_userUseLocal.setObjectName("cb_userUseLocal")
        self.cb_userUseLocal.addItem("")
        self.cb_userUseLocal.addItem("")
        self.cb_userUseLocal.addItem("")
        self.horizontalLayout_15.addWidget(self.cb_userUseLocal)
        self.verticalLayout_6.addWidget(self.w_userUseLocal)
        self.w_resetPrjScripts = QtWidgets.QWidget(self.w_curPrj)
        self.w_resetPrjScripts.setObjectName("w_resetPrjScripts")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.w_resetPrjScripts)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.verticalLayout_6.addWidget(self.w_resetPrjScripts)
        self.verticalLayout_8.addWidget(self.w_curPrj)
        spacerItem3 = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.verticalLayout_8.addItem(spacerItem3)
        self.widget_6 = QtWidgets.QWidget(self.tabWidgetPage2)
        self.widget_6.setObjectName("widget_6")
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout(self.widget_6)
        self.horizontalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_10.addItem(spacerItem4)
        self.b_manageProjects = QtWidgets.QPushButton(self.widget_6)
        self.b_manageProjects.setFocusPolicy(QtCore.Qt.NoFocus)
        self.b_manageProjects.setObjectName("b_manageProjects")
        self.horizontalLayout_10.addWidget(self.b_manageProjects)
        spacerItem5 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_10.addItem(spacerItem5)
        self.verticalLayout_8.addWidget(self.widget_6)
        self.w_projects = QtWidgets.QWidget(self.tabWidgetPage2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(10)
        sizePolicy.setHeightForWidth(self.w_projects.sizePolicy().hasHeightForWidth())
        self.w_projects.setSizePolicy(sizePolicy)
        self.w_projects.setObjectName("w_projects")
        self.lo_projects = QtWidgets.QVBoxLayout(self.w_projects)
        self.lo_projects.setContentsMargins(0, 0, 0, 0)
        self.lo_projects.setObjectName("lo_projects")
        spacerItem6 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.lo_projects.addItem(spacerItem6)
        self.verticalLayout_8.addWidget(self.w_projects)
        spacerItem7 = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_8.addItem(spacerItem7)
        self.tw_settings.addTab(self.tabWidgetPage2, "")
        self.tab_dccApps = QtWidgets.QWidget()
        self.tab_dccApps.setObjectName("tab_dccApps")
        self.verticalLayout_24 = QtWidgets.QVBoxLayout(self.tab_dccApps)
        self.verticalLayout_24.setObjectName("verticalLayout_24")
        self.widget_23 = QtWidgets.QWidget(self.tab_dccApps)
        self.widget_23.setObjectName("widget_23")
        self.verticalLayout_26 = QtWidgets.QVBoxLayout(self.widget_23)
        self.verticalLayout_26.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_26.setObjectName("verticalLayout_26")
        self.verticalLayout_24.addWidget(self.widget_23)
        self.tw_settings.addTab(self.tab_dccApps, "")
        self.tab_Plugins = QtWidgets.QWidget()
        self.tab_Plugins.setObjectName("tab_Plugins")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.tab_Plugins)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.widget = QtWidgets.QWidget(self.tab_Plugins)
        self.widget.setObjectName("widget")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.widget)
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.label_3 = QtWidgets.QLabel(self.widget)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_5.addWidget(self.label_3)
        self.b_createPlugin = QtWidgets.QToolButton(self.widget)
        self.b_createPlugin.setObjectName("b_createPlugin")
        self.horizontalLayout_5.addWidget(self.b_createPlugin)
        self.b_loadPlugin = QtWidgets.QToolButton(self.widget)
        self.b_loadPlugin.setObjectName("b_loadPlugin")
        self.horizontalLayout_5.addWidget(self.b_loadPlugin)
        self.b_reloadPlugins = QtWidgets.QToolButton(self.widget)
        self.b_reloadPlugins.setObjectName("b_reloadPlugins")
        self.horizontalLayout_5.addWidget(self.b_reloadPlugins)
        self.b_managePlugins = QtWidgets.QToolButton(self.widget)
        self.b_managePlugins.setObjectName("b_managePlugins")
        self.horizontalLayout_5.addWidget(self.b_managePlugins)
        self.verticalLayout_2.addWidget(self.widget)
        self.tw_plugins = QtWidgets.QTableWidget(self.tab_Plugins)
        self.tw_plugins.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_plugins.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tw_plugins.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tw_plugins.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tw_plugins.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tw_plugins.setObjectName("tw_plugins")
        self.tw_plugins.setColumnCount(0)
        self.tw_plugins.setRowCount(0)
        self.tw_plugins.horizontalHeader().setHighlightSections(False)
        self.tw_plugins.verticalHeader().setVisible(False)
        self.verticalLayout_2.addWidget(self.tw_plugins)
        self.tw_settings.addTab(self.tab_Plugins, "")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.verticalLayout_9 = QtWidgets.QVBoxLayout(self.tab)
        self.verticalLayout_9.setObjectName("verticalLayout_9")
        self.label_6 = QtWidgets.QLabel(self.tab)
        self.label_6.setObjectName("label_6")
        self.verticalLayout_9.addWidget(self.label_6)
        self.tw_environment = QtWidgets.QTableWidget(self.tab)
        self.tw_environment.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_environment.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tw_environment.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tw_environment.setObjectName("tw_environment")
        self.tw_environment.setColumnCount(2)
        self.tw_environment.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tw_environment.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tw_environment.setHorizontalHeaderItem(1, item)
        self.tw_environment.horizontalHeader().setStretchLastSection(True)
        self.tw_environment.verticalHeader().setVisible(False)
        self.verticalLayout_9.addWidget(self.tw_environment)
        self.widget_2 = QtWidgets.QWidget(self.tab)
        self.widget_2.setObjectName("widget_2")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.widget_2)
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        spacerItem8 = QtWidgets.QSpacerItem(374, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem8)
        self.b_showEnvironment = QtWidgets.QPushButton(self.widget_2)
        self.b_showEnvironment.setObjectName("b_showEnvironment")
        self.horizontalLayout_4.addWidget(self.b_showEnvironment)
        self.verticalLayout_9.addWidget(self.widget_2)
        self.tw_settings.addTab(self.tab, "")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.verticalLayout_14 = QtWidgets.QVBoxLayout(self.tab_2)
        self.verticalLayout_14.setObjectName("verticalLayout_14")
        self.gb_miscellaneous = QtWidgets.QGroupBox(self.tab_2)
        self.gb_miscellaneous.setObjectName("gb_miscellaneous")
        self.lo_miscellaneous = QtWidgets.QVBoxLayout(self.gb_miscellaneous)
        self.lo_miscellaneous.setObjectName("lo_miscellaneous")
        self.chb_autosave = QtWidgets.QCheckBox(self.gb_miscellaneous)
        self.chb_autosave.setChecked(True)
        self.chb_autosave.setObjectName("chb_autosave")
        self.lo_miscellaneous.addWidget(self.chb_autosave)
        self.chb_captureViewport = QtWidgets.QCheckBox(self.gb_miscellaneous)
        self.chb_captureViewport.setChecked(True)
        self.chb_captureViewport.setObjectName("chb_captureViewport")
        self.lo_miscellaneous.addWidget(self.chb_captureViewport)
        self.chb_browserStartup = QtWidgets.QCheckBox(self.gb_miscellaneous)
        self.chb_browserStartup.setChecked(True)
        self.chb_browserStartup.setObjectName("chb_browserStartup")
        self.lo_miscellaneous.addWidget(self.chb_browserStartup)
        self.chb_mediaThumbnails = QtWidgets.QCheckBox(self.gb_miscellaneous)
        self.chb_mediaThumbnails.setChecked(True)
        self.chb_mediaThumbnails.setObjectName("chb_mediaThumbnails")
        self.lo_miscellaneous.addWidget(self.chb_mediaThumbnails)
        self.chb_trayStartup = QtWidgets.QCheckBox(self.gb_miscellaneous)
        self.chb_trayStartup.setChecked(True)
        self.chb_trayStartup.setObjectName("chb_trayStartup")
        self.lo_miscellaneous.addWidget(self.chb_trayStartup)
        self.w_startTray = QtWidgets.QWidget(self.gb_miscellaneous)
        self.w_startTray.setObjectName("w_startTray")
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout(self.w_startTray)
        self.horizontalLayout_7.setContentsMargins(17, 0, 0, 0)
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.b_startTray = QtWidgets.QPushButton(self.w_startTray)
        self.b_startTray.setMinimumSize(QtCore.QSize(150, 0))
        self.b_startTray.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.b_startTray.setObjectName("b_startTray")
        self.horizontalLayout_7.addWidget(self.b_startTray)
        spacerItem9 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_7.addItem(spacerItem9)
        self.lo_miscellaneous.addWidget(self.w_startTray)
        self.chb_highDPI = QtWidgets.QCheckBox(self.gb_miscellaneous)
        self.chb_highDPI.setObjectName("chb_highDPI")
        self.lo_miscellaneous.addWidget(self.chb_highDPI)
        self.chb_errorReports = QtWidgets.QCheckBox(self.gb_miscellaneous)
        self.chb_errorReports.setChecked(True)
        self.chb_errorReports.setObjectName("chb_errorReports")
        self.lo_miscellaneous.addWidget(self.chb_errorReports)
        self.chb_debug = QtWidgets.QCheckBox(self.gb_miscellaneous)
        self.chb_debug.setObjectName("chb_debug")
        self.lo_miscellaneous.addWidget(self.chb_debug)
        self.w_styleSheet = QtWidgets.QWidget(self.gb_miscellaneous)
        self.w_styleSheet.setObjectName("w_styleSheet")
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout(self.w_styleSheet)
        self.horizontalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.l_styleSheet = QtWidgets.QLabel(self.w_styleSheet)
        self.l_styleSheet.setObjectName("l_styleSheet")
        self.horizontalLayout_8.addWidget(self.l_styleSheet)
        self.cb_styleSheet = QtWidgets.QComboBox(self.w_styleSheet)
        self.cb_styleSheet.setObjectName("cb_styleSheet")
        self.horizontalLayout_8.addWidget(self.cb_styleSheet)
        spacerItem10 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_8.addItem(spacerItem10)
        self.lo_miscellaneous.addWidget(self.w_styleSheet)
        self.widget_4 = QtWidgets.QWidget(self.gb_miscellaneous)
        self.widget_4.setObjectName("widget_4")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout(self.widget_4)
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.b_importSettings = QtWidgets.QToolButton(self.widget_4)
        self.b_importSettings.setObjectName("b_importSettings")
        self.horizontalLayout_6.addWidget(self.b_importSettings)
        self.b_exportSettings = QtWidgets.QToolButton(self.widget_4)
        self.b_exportSettings.setObjectName("b_exportSettings")
        self.horizontalLayout_6.addWidget(self.b_exportSettings)
        spacerItem11 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_6.addItem(spacerItem11)
        self.lo_miscellaneous.addWidget(self.widget_4)
        self.verticalLayout_14.addWidget(self.gb_miscellaneous)
        self.gb_mediaPlayer = QtWidgets.QGroupBox(self.tab_2)
        self.gb_mediaPlayer.setObjectName("gb_mediaPlayer")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.gb_mediaPlayer)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.widget_8 = QtWidgets.QWidget(self.gb_mediaPlayer)
        self.widget_8.setObjectName("widget_8")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.widget_8)
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.e_mediaPlayerName = QtWidgets.QLineEdit(self.widget_8)
        self.e_mediaPlayerName.setObjectName("e_mediaPlayerName")
        self.gridLayout_3.addWidget(self.e_mediaPlayerName, 0, 1, 1, 1)
        self.label_7 = QtWidgets.QLabel(self.widget_8)
        self.label_7.setObjectName("label_7")
        self.gridLayout_3.addWidget(self.label_7, 0, 0, 1, 1)
        self.label_12 = QtWidgets.QLabel(self.widget_8)
        font = QtGui.QFont()
        font.setWeight(50)
        font.setBold(False)
        self.label_12.setFont(font)
        self.label_12.setObjectName("label_12")
        self.gridLayout_3.addWidget(self.label_12, 1, 0, 1, 1)
        self.e_mediaPlayerPath = QtWidgets.QLineEdit(self.widget_8)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(10)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.e_mediaPlayerPath.sizePolicy().hasHeightForWidth())
        self.e_mediaPlayerPath.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setWeight(50)
        font.setBold(False)
        self.e_mediaPlayerPath.setFont(font)
        self.e_mediaPlayerPath.setObjectName("e_mediaPlayerPath")
        self.gridLayout_3.addWidget(self.e_mediaPlayerPath, 1, 1, 1, 1)
        self.b_browseMediaPlayer = QtWidgets.QPushButton(self.widget_8)
        font = QtGui.QFont()
        font.setWeight(50)
        font.setBold(False)
        self.b_browseMediaPlayer.setFont(font)
        self.b_browseMediaPlayer.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.b_browseMediaPlayer.setObjectName("b_browseMediaPlayer")
        self.gridLayout_3.addWidget(self.b_browseMediaPlayer, 1, 2, 1, 1)
        self.verticalLayout_5.addWidget(self.widget_8)
        self.widget_7 = QtWidgets.QWidget(self.gb_mediaPlayer)
        self.widget_7.setObjectName("widget_7")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.widget_7)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.chb_mediaPlayerPattern = QtWidgets.QCheckBox(self.widget_7)
        self.chb_mediaPlayerPattern.setObjectName("chb_mediaPlayerPattern")
        self.horizontalLayout_3.addWidget(self.chb_mediaPlayerPattern)
        self.verticalLayout_5.addWidget(self.widget_7)
        self.verticalLayout_14.addWidget(self.gb_mediaPlayer)
        spacerItem12 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_14.addItem(spacerItem12)
        self.tw_settings.addTab(self.tab_2, "")
        self.horizontalLayout_9.addWidget(self.tw_settings)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout.addWidget(self.splitter)
        self.buttonBox = QtWidgets.QDialogButtonBox(dlg_UserSettings)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Apply|QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Save)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(dlg_UserSettings)
        self.tw_settings.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(dlg_UserSettings)
        dlg_UserSettings.setTabOrder(self.tw_settings, self.e_localPath)
        dlg_UserSettings.setTabOrder(self.e_localPath, self.b_browseLocal)

    def retranslateUi(self, dlg_UserSettings):
        dlg_UserSettings.setWindowTitle(QtWidgets.QApplication.translate("", "User Settings", None, -1))
        self.gb_about.setTitle(QtWidgets.QApplication.translate("", "About", None, -1))
        self.groupBox_3.setTitle(QtWidgets.QApplication.translate("", "User", None, -1))
        self.l_abbreviation.setText(QtWidgets.QApplication.translate("", "Abbreviation:    ", None, -1))
        self.l_username.setText(QtWidgets.QApplication.translate("", "Local Username:", None, -1))
        self.tw_settings.setTabText(self.tw_settings.indexOf(self.tabWidgetPage4), QtWidgets.QApplication.translate("", "General", None, -1))
        self.w_curPrj.setTitle(QtWidgets.QApplication.translate("", "Current Project", None, -1))
        self.l_projectName.setToolTip(QtWidgets.QApplication.translate("", "current project", None, -1))
        self.l_projectPath.setToolTip(QtWidgets.QApplication.translate("", "current project path", None, -1))
        self.label_4.setText(QtWidgets.QApplication.translate("", "Path:          ", None, -1))
        self.label_2.setText(QtWidgets.QApplication.translate("", "Name:", None, -1))
        self.l_localPath.setText(QtWidgets.QApplication.translate("", "Local path:", None, -1))
        self.b_browseLocal.setText(QtWidgets.QApplication.translate("", "...", None, -1))
        self.label_5.setText(QtWidgets.QApplication.translate("", "Use additional local project folder:", None, -1))
        self.cb_userUseLocal.setItemText(0, QtWidgets.QApplication.translate("", "Inherit from project", None, -1))
        self.cb_userUseLocal.setItemText(1, QtWidgets.QApplication.translate("", "On", None, -1))
        self.cb_userUseLocal.setItemText(2, QtWidgets.QApplication.translate("", "Off", None, -1))
        self.b_manageProjects.setText(QtWidgets.QApplication.translate("", "Manage Projects...", None, -1))
        self.tw_settings.setTabText(self.tw_settings.indexOf(self.tabWidgetPage2), QtWidgets.QApplication.translate("", "Projects", None, -1))
        self.tw_settings.setTabText(self.tw_settings.indexOf(self.tab_dccApps), QtWidgets.QApplication.translate("", "DCC apps", None, -1))
        self.label_3.setText(QtWidgets.QApplication.translate("", "Loaded Plugins:", None, -1))
        self.b_createPlugin.setToolTip(QtWidgets.QApplication.translate("", "Create new plugin...", None, -1))
        self.b_createPlugin.setText(QtWidgets.QApplication.translate("", "...", None, -1))
        self.b_loadPlugin.setToolTip(QtWidgets.QApplication.translate("", "Add existing plugin...", None, -1))
        self.b_loadPlugin.setText(QtWidgets.QApplication.translate("", "...", None, -1))
        self.b_reloadPlugins.setToolTip(QtWidgets.QApplication.translate("", "Reload all plugins", None, -1))
        self.b_reloadPlugins.setText(QtWidgets.QApplication.translate("", "...", None, -1))
        self.b_managePlugins.setToolTip(QtWidgets.QApplication.translate("", "Manage Plugin Paths...", None, -1))
        self.b_managePlugins.setText(QtWidgets.QApplication.translate("", "...", None, -1))
        self.tw_settings.setTabText(self.tw_settings.indexOf(self.tab_Plugins), QtWidgets.QApplication.translate("", "Plugins", None, -1))
        self.label_6.setText(QtWidgets.QApplication.translate("", "User specific environment variables:", None, -1))
        self.tw_environment.horizontalHeaderItem(0).setText(QtWidgets.QApplication.translate("", "Variable", None, -1))
        self.tw_environment.horizontalHeaderItem(1).setText(QtWidgets.QApplication.translate("", "Value", None, -1))
        self.b_showEnvironment.setText(QtWidgets.QApplication.translate("", "Show current environment", None, -1))
        self.tw_settings.setTabText(self.tw_settings.indexOf(self.tab), QtWidgets.QApplication.translate("", "Environment", None, -1))
        self.gb_miscellaneous.setTitle(QtWidgets.QApplication.translate("", "Miscellaneous", None, -1))
        self.chb_autosave.setText(QtWidgets.QApplication.translate("", "Autosave popup", None, -1))
        self.chb_captureViewport.setText(QtWidgets.QApplication.translate("", "Capture viewport preview on scene save", None, -1))
        self.chb_browserStartup.setText(QtWidgets.QApplication.translate("", "Open Project Browser on application startup", None, -1))
        self.chb_mediaThumbnails.setText(QtWidgets.QApplication.translate("", "Automatically generate thumbnails for media", None, -1))
        self.chb_trayStartup.setText(QtWidgets.QApplication.translate("", "Show Prism tray icon on system startup", None, -1))
        self.b_startTray.setText(QtWidgets.QApplication.translate("", "Start Prism tray now", None, -1))
        self.chb_highDPI.setText(QtWidgets.QApplication.translate("", "HighDPI support (requires complete application restart) (experimental)", None, -1))
        self.chb_errorReports.setText(QtWidgets.QApplication.translate("", "Send anonymous error reports", None, -1))
        self.chb_debug.setText(QtWidgets.QApplication.translate("", "Debug mode", None, -1))
        self.l_styleSheet.setText(QtWidgets.QApplication.translate("", "Standalone Style Sheet:", None, -1))
        self.b_importSettings.setToolTip(QtWidgets.QApplication.translate("", "Import User Settings...", None, -1))
        self.b_importSettings.setText(QtWidgets.QApplication.translate("", "...", None, -1))
        self.b_exportSettings.setToolTip(QtWidgets.QApplication.translate("", "Export User Settings...", None, -1))
        self.b_exportSettings.setText(QtWidgets.QApplication.translate("", "...", None, -1))
        self.gb_mediaPlayer.setTitle(QtWidgets.QApplication.translate("", "Media Player", None, -1))
        self.label_7.setText(QtWidgets.QApplication.translate("", "Name:", None, -1))
        self.label_12.setText(QtWidgets.QApplication.translate("", "Executable Path:", None, -1))
        self.b_browseMediaPlayer.setText(QtWidgets.QApplication.translate("", "...", None, -1))
        self.chb_mediaPlayerPattern.setText(QtWidgets.QApplication.translate("", "Understands Framepatterns", None, -1))
        self.tw_settings.setTabText(self.tw_settings.indexOf(self.tab_2), QtWidgets.QApplication.translate("", "Miscellaneous", None, -1))
