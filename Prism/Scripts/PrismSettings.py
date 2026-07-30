# -*- coding: utf-8 -*-
#
####################################################
#
# PRISM - Pipeline for animation and VFX projects
#
# www.prism-pipeline.com
#
# contact: contact@prism-pipeline.com
#
####################################################
#
#
# Copyright (C) 2016-2023 Richard Frangenberg
# Copyright (C) 2023 Prism Software GmbH
#
# Licensed under GNU LGPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


import os
import sys
import subprocess
import platform
import logging
from typing import Any, Optional, List, Dict, Tuple

scriptPath = os.path.abspath(os.path.dirname(__file__))
if scriptPath not in sys.path:
    sys.path.append(scriptPath)

if __name__ == "__main__":
    import PrismCore

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher
from UserInterfacesPrism import UserSettings_ui
from PrismUtils import PrismWidgets


logger = logging.getLogger(__name__)


class PrismSettings(QDialog):
    """Main settings dialog for Prism pipeline configuration.
    
    This dialog provides access to user settings and project settings tabs,
    allowing users to configure Prism preferences, plugins, integrations,
    and project-specific options.
    
    Attributes:
        core: Reference to the Prism core instance
        tabs (List[QWidget]): List of all setting tabs
        activeTabs (List[QWidget]): List of recently accessed tabs
    """
    
    def __init__(self, core: Any) -> None:
        """Initialize the Prism Settings dialog.
        
        Args:
            core: The Prism core instance providing access to framework functionality
        """
        QDialog.__init__(self)
        self.core = core
        self.core.parentWindow(self)
        self.tabs = []
        self.activeTabs = []

        self.loadUI()

        self.core.callback(name="onPrismSettingsOpen", args=[self])
        self.setFocus()
        screen = self.core.getQScreenGeo()
        if screen:
            screenH = screen.height()
            space = 100
            if screenH < (self.height() + space):
                self.resize(self.width(), screenH - space)

    @err_catcher(name=__name__)
    def loadUI(self) -> None:
        """Load and initialize the settings dialog UI.
        
        Creates tab widgets for user and project settings, sets up the main layout,
        and configures dialog buttons (Save, Cancel, Apply).
        """
        self.setWindowTitle("Prism Settings")
        self.tbw_settings = QTabWidget()
        self.tbw_settings.currentChanged.connect(self.tabChanged)
        self.lo_main = QVBoxLayout(self)
        self.lo_main.addWidget(self.tbw_settings)

        self.w_user = UserSettings(self.core)
        self.w_user.buttonBox.setVisible(False)
        path = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "user.png")
        icon = self.core.media.getColoredIcon(path)
        self.addTab("User", self.w_user, icon=icon)

        if self.core.prismIni:
            import ProjectSettings
            self.w_project = ProjectSettings.ProjectSettings(self.core, projectConfig=self.core.prismIni)
            self.w_project.buttonBox.setVisible(False)
            self.w_project.layout().setContentsMargins(0, 0, 0, 0)
            path = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "project.png")
            icon = self.core.media.getColoredIcon(path)
            self.addTab("Project", self.w_project, icon=icon)

        self.bb_main = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply)
        self.bb_main.button(QDialogButtonBox.Ok).setText("Save")
        self.bb_main.button(QDialogButtonBox.Apply).clicked.connect(self.applySettings)
        self.bb_main.accepted.connect(self.accept)
        self.bb_main.accepted.connect(self.saveSettings)
        self.bb_main.rejected.connect(self.reject)

        self.lo_main.addWidget(self.bb_main)
        self.tabChanged()

    @err_catcher(name=__name__)
    def saveSettings(self) -> None:
        """Save the current settings from all tabs.
        
        Delegates to the currently active tab's saveSettings method.
        """
        self.tbw_settings.currentWidget().saveSettings()

    @err_catcher(name=__name__)
    def applySettings(self) -> None:
        """Apply settings without changing the project.
        
        Saves the current settings without triggering a project change.
        """
        self.tbw_settings.currentWidget().saveSettings(changeProject=False)

    @err_catcher(name=__name__)
    def addTab(self, name: str, widget: QWidget, position: int = -1, icon: Optional[QIcon] = None) -> None:
        """Add a new tab to the settings dialog.
        
        Args:
            name: Tab name/title to display
            widget: The widget to display in the tab
            position: Insert position (default -1 for append)
            icon: Optional icon to display on the tab
        """
        widget.setProperty("tabType", name)
        idx = self.tbw_settings.insertTab(position, widget, name)
        if icon:
            self.tbw_settings.setTabIcon(idx, icon)

        self.tabs.append(widget)

    @err_catcher(name=__name__)
    def getCurrentSettingsType(self) -> str:
        """Get the name of the currently active settings tab.
        
        Returns:
            The text/name of the currently visible tab
        """
        return self.tbw_settings.tabText(self.tbw_settings.currentIndex())

    @err_catcher(name=__name__)
    def getCurrentCategory(self) -> Optional[str]:
        """Get the currently selected category from the active tab.
        
        Returns:
            The name of the selected category, or None if not applicable
        """
        return self.tbw_settings.currentWidget().getCurrentCategory()

    def sizeHint(self) -> QSize:
        """Provide the suggested default size for the settings dialog.
        
        Returns:
            A QSize object with width=1000 and height=700
        """
        return QSize(1000, 700)
    
    @err_catcher(name=__name__)
    def getTabByName(self, tab: str) -> Optional[QWidget]:
        """Retrieve a settings tab by its name.
        
        Args:
            tab: The name of the tab to retrieve
            
        Returns:
            The tab widget, or None if not found
        """
        for idx in range(self.tbw_settings.count()):
            name = self.tbw_settings.tabText(idx)
            if name == tab:
                return self.tbw_settings.widget(idx)

    @err_catcher(name=__name__)
    def navigate(self, data: Dict[str, Any]) -> None:
        """Navigate to a specific settings location.
        
        Args:
            data: Dictionary containing navigation parameters:
                - 'settingsType' (str): Tab name to navigate to
                - 'tab' (str): Category/section within the tab
        """
        if data.get("settingsType"):
            for idx in range(self.tbw_settings.count()):
                if self.tbw_settings.tabText(idx) == data["settingsType"]:
                    self.tbw_settings.setCurrentIndex(idx)
                    break

        if "tab" in data:
            tab = data["tab"]
            widget = self.tbw_settings.currentWidget()
            widget.selectCategory(tab)

    @err_catcher(name=__name__)
    def tabChanged(self, idx: Optional[int] = None) -> None:
        """Handle tab change events.
        
        Tracks which tabs have been activated/viewed.
        
        Args:
            idx: The new tab index (optional, can be None)
        """
        curTab = self.tbw_settings.currentWidget()
        if curTab not in self.activeTabs:
            self.activeTabs.append(curTab)


class UserSettings(QDialog, UserSettings_ui.Ui_dlg_UserSettings):
    def __init__(self, core: Any) -> None:
        """Initialize the User Settings dialog.
        
        Sets up the User Settings UI window with plugin configurations, integration
        settings, user preferences, and stylesheet options. Initializes dependency
        and local use state enumerations, loads UI elements, and connects event handlers.
        
        Args:
            core: The Prism core instance providing access to system functions,
                plugins, and configuration management.
        """
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.core.parentWindow(self)

        self.dependencyStates = {
            "always": "Always",
            "publish": "On Publish",
            "never": "Never",
        }

        self.useLocalStates = {
            "inherit": "Inherit from project",
            "on": "On",
            "off": "Off",
        }
        self.trayChanged = False

        self.loadUI()
        self.loadSettings()
        self.refreshPlugins()

        self.core.callback(name="onUserSettingsOpen", args=[self])

        self.connectEvents()
        self.setFocus()

        screen = self.core.getQScreenGeo()
        if screen:
            screenH = screen.height()
            space = 100
            if screenH < (self.height() + space):
                self.resize(self.width(), screenH - space)

    @err_catcher(name=__name__)
    def loadUI(self) -> None:
        """Initialize and configure all User Settings UI elements.
        
        Sets up the settings dialog with plugin tabs (DCC applications), integration
        configurations, executable overrides, user preferences (username, abbreviation),
        appearance settings (themes, stylesheet), and various checkboxes for user options.
        Hides the tab bar and populates DCC-specific tabs from plugin data. This is a
        comprehensive UI initialization method (approximately 187 lines).
        """
        tabBar = self.tw_settings.findChild(QTabBar)
        tabBar.hide()
        self.tw_settings.currentChanged.connect(self.tabChanged)

        self.scrollAreaWidgetContents.layout().setContentsMargins(0, 0, 0, 0)
        for idx in range(self.tw_settings.count()):
            self.tw_settings.widget(idx).layout().setContentsMargins(0, 0, 0, 0)

        self.layout().setContentsMargins(0, 0, 0, 0)
        self.gb_about.layout().setContentsMargins(15, 15, 15, 15)
        self.l_about.setText(self.core.getAboutString())

        readOnly = self.core.users.isUserReadOnly()
        abbrReadOnly = self.core.users.isAbbreviationReadOnly()
        self.e_username.setReadOnly(readOnly)
        self.e_abbreviation.setReadOnly(readOnly or abbrReadOnly)
        self.b_manageProjects.setMinimumHeight(40)

        self.exOverridePlugins = {}
        self.integrationPlugins = {}
        self.dccTabs = QTabWidget()

        pluginNames = self.core.getPluginNames()
        for i in pluginNames:
            pAppType = self.core.getPluginData(i, "appType")
            if pAppType != "standalone":
                tab = QWidget()
                w_ovr = QWidget()
                lo_tab = QVBoxLayout()
                lo_ovr = QHBoxLayout()
                tab.setLayout(lo_tab)
                w_ovr.setLayout(lo_ovr)
                lo_tab.setContentsMargins(15, 15, 15, 15)
                lo_ovr.setContentsMargins(0, 9, 0, 9)
                #   w_ovr.setMinimumSize(0,39)

                if self.core.getPluginData(i, "canOverrideExecuteable") is not False:
                    l_ovr = QLabel(
                        "By default Prism uses the default application configured in the OS settings to open scenefiles.\nThe following setting let you override this behaviour by defining explicit applications for opening scenefiles."
                    )
                    chb_ovr = QCheckBox("Executable override")
                    le_ovr = QLineEdit()
                    b_ovr = QPushButton("...")
                    b_ovr.setContextMenuPolicy(Qt.CustomContextMenu)

                    lo_ovr.addWidget(chb_ovr)
                    lo_ovr.addWidget(le_ovr)
                    lo_ovr.addWidget(b_ovr)

                    lo_tab.addWidget(l_ovr)
                    lo_tab.addWidget(w_ovr)

                    self.exOverridePlugins[i] = {
                        "chb": chb_ovr,
                        "le": le_ovr,
                        "b": b_ovr,
                    }

                if self.core.getPluginData(i, "hasIntegration") is not False:
                    hasIntegrationPath = self.core.getPluginData(i, "hasIntegrationPath")
                    if hasIntegrationPath is None:
                        hasIntegrationPath = True

                    gb_integ = QGroupBox("Prism integrations")
                    lo_integ = QVBoxLayout()
                    gb_integ.setLayout(lo_integ)
                    lw_integ = QListWidget()
                    w_integ = QWidget()
                    lo_integButtons = QHBoxLayout()
                    b_addInteg = QPushButton("Add")
                    b_removeInteg = QPushButton("Remove")
                    if hasIntegrationPath:
                        examplePath = self.core.getPluginData(i, "examplePath") or ""
                        l_examplePath = QLabel("Examplepath:\n\n" + examplePath)

                    w_integ.setLayout(lo_integButtons)
                    lo_integButtons.addStretch()
                    lo_integButtons.addWidget(b_addInteg)
                    lo_integButtons.addWidget(b_removeInteg)

                    lo_integ.addWidget(lw_integ)
                    if hasIntegrationPath:
                        lo_integ.addWidget(l_examplePath)

                    lo_integ.addWidget(w_integ)
                    lo_tab.addWidget(gb_integ)

                    lw_integ.setSizePolicy(
                        QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    )
                    lw_integ.setContextMenuPolicy(Qt.CustomContextMenu)
                    lw_integ.customContextMenuRequested.connect(
                        lambda x, y=lw_integ: self.contextMenuIntegration(x, y)
                    )

                    self.integrationPlugins[i] = {
                        "lw": lw_integ,
                        "badd": b_addInteg,
                        "bremove": b_removeInteg,
                        "tab": tab,
                    }
                    if hasIntegrationPath:
                        self.integrationPlugins[i]["lexample"] = l_examplePath

                getattr(
                    self.core.getPlugin(i), "userSettings_loadUI", lambda x, y: None
                )(self, tab)

                lo_tab.addStretch()
                self.dccTabs.addTab(tab, i)

        if self.dccTabs.count() > 0:
            self.tab_dccApps.layout().addWidget(self.dccTabs)

        self.refreshIntegrations()

        self.tab_dccApps.layout().addStretch()

        headerLabels = ["Loaded", "Auto Load", "Name", "Type", "Version", "Location"]
        self.tw_plugins.setColumnCount(len(headerLabels))
        self.tw_plugins.setHorizontalHeaderLabels(headerLabels)
        self.tw_plugins.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        self.tw_plugins.verticalHeader().setDefaultSectionSize(25)
        self.tw_plugins.horizontalHeader().setStretchLastSection(True)
        self.tw_plugins.setAcceptDrops(True)
        self.tw_plugins.dragEnterEvent = self.pluginDragEnterEvent
        self.tw_plugins.dragMoveEvent = self.pluginDragMoveEvent
        self.tw_plugins.dragLeaveEvent = self.pluginDragLeaveEvent
        self.tw_plugins.dropEvent = self.pluginDropEvent

        self.tw_environment.setHorizontalHeaderLabels(["Variable", "Value"])
        self.tw_environment.customContextMenuRequested.connect(self.rclEnvironment)
        self.addEnvironmentRow()
        self.tw_environment.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )

        self.origKeyPressEvent = self.keyPressEvent
        self.keyPressEvent = lambda x: self.keyPressedDialog(x)

        self.l_helpUser = HelpLabel(self)
        self.l_helpUser.setMouseTracking(True)
        msg = (
            "This username is used to identify, which scenefiles and renders you create in a project with other people.\n"
            "Typically this would be: \"Firstname Lastname\""
        )
        self.l_helpUser.msg = msg
        self.w_username.layout().addWidget(self.l_helpUser, 0, 3)

        if platform.system() in ["Linux", "Darwin"]:
            self.chb_trayStartup.setText(
                self.chb_trayStartup.text() + " (change requires root permissions)"
            )

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        if not self.core.getPlugin("Hub", allowUnloaded=True) and os.getenv("PRISM_ALLOW_HUB_INSTALL") != "0":
            self.gb_installHub = QGroupBox("Hub")
            self.lo_installHub = QHBoxLayout(self.gb_installHub)
            self.b_installHub = QPushButton("Install Hub")
            self.b_installHub.clicked.connect(self.core.plugins.installHub)
            self.l_installHub = QLabel("Allows you to install plugins and update your Prism version.")
            self.lo_installHub.addWidget(self.b_installHub)
            self.lo_installHub.addWidget(self.l_installHub)
            self.lo_installHub.addStretch()
            self.getTabByName("General").layout().insertWidget(1, self.gb_installHub)

        self.gb_mediaPlayers = PrismWidgets.MediaPlayersWidget(self)
        self.lo_miscellaneousTab.insertWidget(self.lo_miscellaneousTab.count() - 1, self.gb_mediaPlayers)

        self.refreshIcons()
        self.refreshCategories()
        policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        policy.setHorizontalStretch(40)
        self.lw_categories.setSizePolicy(policy)
        policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        policy.setHorizontalStretch(100)
        self.scrollArea.setSizePolicy(policy)
        self.lw_categories.currentItemChanged.connect(self.onCategoryChanged)
        self.selectCategory("General")
        self.updateTabSize(self.tw_settings.currentIndex())
        self.core.callback(name="userSettings_loadUI", args=[self])

    @err_catcher(name=__name__)
    def pluginDragEnterEvent(self, e: Any) -> None:
        """Handle drag enter event for plugin files.
        
        Accepts drag events when Python files are dragged over the plugin table.
        
        Args:
            e: Qt drag enter event
        """
        if e.mimeData().hasUrls() and e.mimeData().urls():
            files = [
                os.path.normpath(str(url.toLocalFile())) for url in e.mimeData().urls()
            ]
            files = [file for file in files if file.endswith(".py")]

            if files:
                e.accept()
                return

        e.ignore()

    @err_catcher(name=__name__)
    def pluginDragMoveEvent(self, e: Any) -> None:
        """Handle drag move event over plugin table.
        
        Provides visual feedback by highlighting the plugin table with a green dashed border
        when Python files are dragged over it.
        
        Args:
            e: Qt drag move event
        """
        if e.mimeData().hasUrls():
            files = [
                os.path.normpath(str(url.toLocalFile())) for url in e.mimeData().urls()
            ]
            files = [file for file in files if file.endswith(".py")]
            if files:
                e.accept()
                self.tw_plugins.setStyleSheet(
                    "QTableView { border-style: dashed; border-color: rgb(100, 200, 100);  border-width: 2px; }"
                )
                return
        
        e.ignore()

    @err_catcher(name=__name__)
    def pluginDragLeaveEvent(self, e: Any) -> None:
        """Handle drag leave event from plugin table.
        
        Removes visual highlighting when dragged files leave the plugin table area.
        
        Args:
            e: Qt drag leave event
        """
        self.tw_plugins.setStyleSheet("")

    @err_catcher(name=__name__)
    def pluginDropEvent(self, e: Any) -> None:
        """Handle drop event for plugin files into the plugin table.
        
        Loads dropped Python plugin files and adds them to the plugin configuration.
        
        Args:
            e: Qt drop event
        """
        if e.mimeData().hasUrls():
            self.tw_plugins.setStyleSheet("")
            e.setDropAction(Qt.LinkAction)
            e.accept()

            files = [
                os.path.normpath(str(url.toLocalFile())) for url in e.mimeData().urls()
            ]
            files = [file for file in files if file.endswith(".py")]

            if files:
                self.core.plugins.loadPlugins(files)
                for file in files:
                    self.core.plugins.addToPluginConfig(file)

                self.refreshPlugins()
                return
        
        e.ignore()

    @err_catcher(name=__name__)
    def addTab(self, widget: QWidget, name: str) -> None:
        """Add a new tab to the settings tabs widget.
        
        Args:
            widget: The widget to display in the new tab
            name: The name/label for the tab
        """
        self.tw_settings.addTab(widget, name)
        self.refreshCategories()

    @err_catcher(name=__name__)
    def removeTab(self, name: str) -> None:
        """Remove a tab from the settings tabs widget.
        
        Args:
            name: The name of the tab to remove
        """
        for idx in range(self.tw_settings.count()):
            if self.tw_settings.tabText(idx) == name:
                self.tw_settings.removeTab(idx)
                break

        self.refreshCategories()

    @err_catcher(name=__name__)
    def tabChanged(self, tab: int) -> None:
        """Handle tab change event.
        
        Updates tab size policy and syncs category list selection when active tab changes.
        
        Args:
            tab: Index of the newly selected tab
        """
        self.updateTabSize(tab)
        self.lw_categories.blockSignals(True)
        self.selectCategory(self.tw_settings.tabText(tab))
        self.lw_categories.blockSignals(False)

    @err_catcher(name=__name__)
    def updateTabSize(self, tab: int) -> None:
        """Update size policies for all tabs based on active tab.
        
        Sets non-active tabs to Ignored size policy and active tab to Preferred policy
        to manage UI layout efficiency.
        
        Args:
            tab: Index of the tab that should be active
        """
        for idx in range(self.tw_settings.count()):
            if idx != tab:
                self.tw_settings.widget(idx).setSizePolicy(
                    QSizePolicy.Ignored, QSizePolicy.Ignored
                )

        curWidget = self.tw_settings.widget(tab)
        if not curWidget:
            return

        curWidget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

    @err_catcher(name=__name__)
    def refreshCategories(self) -> None:
        """Refresh the category list with sorted tab names.
        
        Rebuilds the categories list widget from current tabs, maintaining current selection
        if present or falling back to the first category.
        """
        cur = self.getCurrentCategory()
        self.lw_categories.blockSignals(True)
        self.lw_categories.clear()
        cats = []
        for idx in range(self.tw_settings.count()):
            text = self.tw_settings.tabText(idx)
            cats.append(text)
        
        self.lw_categories.addItems(sorted(cats))
        self.lw_categories.setCurrentRow(0)
        self.selectCategory(cur)
        self.lw_categories.blockSignals(False)
        self.onCategoryChanged(self.lw_categories.currentItem())

    @err_catcher(name=__name__)
    def onCategoryChanged(self, current: Optional[QListWidgetItem], prev: Optional[QListWidgetItem] = None) -> None:
        """Handle category selection change in the category list.
        
        Updates the active tab to match the selected category and calls the widget's
        'entered' callback if it exists.
        
        Args:
            current: The newly selected category item
            prev: The previously selected category item (optional)
        """
        text = current.text()
        for idx in range(self.tw_settings.count()):
            tabtext = self.tw_settings.tabText(idx)
            if text == tabtext:
                self.tw_settings.setCurrentIndex(idx)
                widget = self.tw_settings.widget(idx)
                if hasattr(widget, "entered"):
                    widget.entered(self, widget)

                break

    @err_catcher(name=__name__)
    def selectCategory(self, name: Optional[str]) -> None:
        """Select a category by name in the category list.
        
        Args:
            name: The name of the category to select
        """
        for idx in range(self.lw_categories.count()):
            cat = self.lw_categories.item(idx).text()
            if cat == name:
                self.lw_categories.setCurrentRow(idx)
                break

    @err_catcher(name=__name__)
    def getCurrentCategory(self) -> Optional[str]:
        """Get the name of the currently selected category.
        
        Returns:
            The text of the currently selected category item, or None if no item is selected
        """
        item = self.lw_categories.currentItem()
        if not item:
            return

        return item.text()

    @err_catcher(name=__name__)
    def getTabByName(self, tab: str) -> Optional[QWidget]:
        """Retrieve a settings tab widget by its name.
        
        Args:
            tab: The name of the tab to retrieve
            
        Returns:
            The tab widget if found, None otherwise
        """
        for idx in range(self.tw_settings.count()):
            name = self.tw_settings.tabText(idx)
            if name == tab:
                return self.tw_settings.widget(idx)

    @err_catcher(name=__name__)
    def refreshIcons(self) -> None:
        """Load and apply icons to all UI buttons and labels.
        
        Updates icons for help labels, plugin management buttons, import/export buttons,
        and other UI elements from the Prism icon resources.
        """
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "help.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        pixmap = icon.pixmap(20, 20)
        self.l_helpUser.setPixmap(pixmap)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "create.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_createPlugin.setIcon(icon)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_loadPlugin.setIcon(icon)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "refresh.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_reloadPlugins.setIcon(icon)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "configure.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_managePlugins.setIcon(icon)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "import.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_importSettings.setIcon(icon)
        self.b_importSettings.setIconSize(QSize(22, 22))

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "export.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_exportSettings.setIcon(icon)
        self.b_exportSettings.setIconSize(QSize(22, 22))

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect all UI signals to their corresponding slot methods.
        
        Establishes connections for buttons, checkboxes, text edits, and context menus
        to enable user interactions throughout the settings dialog.
        """
        self.e_username.textChanged.connect(lambda x: self.validate(self.e_username, x))
        self.e_abbreviation.textChanged.connect(
            lambda x: self.validate(self.e_abbreviation, x)
        )
        self.b_browseLocal.clicked.connect(lambda: self.browse("local"))
        self.b_browseLocal.customContextMenuRequested.connect(
            lambda: self.core.openFolder(self.e_localPath.text())
        )
        for i in self.exOverridePlugins:
            self.exOverridePlugins[i]["chb"].stateChanged.connect(
                lambda x, y=i: self.orToggled(y, x)
            )
            self.exOverridePlugins[i]["b"].clicked.connect(
                lambda y=None, x=(i + "OR"): self.browse(x, getFile=True)
            )
            self.exOverridePlugins[i]["b"].customContextMenuRequested.connect(
                lambda x, y=i: self.core.openFolder(
                    self.exOverridePlugins[y]["le"].text()
                )
            )
        for i in self.integrationPlugins:
            self.integrationPlugins[i]["badd"].clicked.connect(
                lambda y=None, x=i: self.integrationAdd(x)
            )
            self.integrationPlugins[i]["bremove"].clicked.connect(
                lambda y=None, x=i: self.integrationRemove(x)
            )

        self.b_manageProjects.clicked.connect(self.core.projects.setProject)

        self.b_startTray.clicked.connect(self.startTray)
        self.chb_trayStartup.toggled.connect(self.onTrayChanged)
        self.b_protocolHandler.clicked.connect(self.onProtocolHandlerClicked)
        self.tw_plugins.customContextMenuRequested.connect(self.rclPluginList)
        self.b_managePlugins.clicked.connect(self.managePluginsDlg)
        self.b_loadPlugin.clicked.connect(self.loadExternalPlugin)
        self.b_loadPlugin.setContextMenuPolicy(Qt.CustomContextMenu)
        self.b_loadPlugin.customContextMenuRequested.connect(self.rclLoadPlugin)
        self.b_reloadPlugins.clicked.connect(self.reloadPlugins)
        self.b_createPlugin.clicked.connect(self.createPluginWindow)
        self.b_showEnvironment.clicked.connect(self.showEnvironment)
        self.cb_styleSheet.currentIndexChanged.connect(self.onStyleSheetChanged)
        self.b_importSettings.clicked.connect(self.onImportSettingsClicked)
        self.b_exportSettings.clicked.connect(self.onExportSettingsClicked)
        self.buttonBox.accepted.connect(self.saveSettings)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(
            lambda: self.saveSettings(changeProject=False)
        )

    @err_catcher(name=__name__)
    def validate(self, uiWidget: QLineEdit, origText: Optional[str] = None) -> None:
        """Validate line edit widget input and auto-update abbreviation if needed.
        
        Args:
            uiWidget: The line edit widget to validate
            origText: The original text (optional, used by signal connections)
        """
        self.core.validateLineEdit(uiWidget, allowChars=[" "])

        if uiWidget != self.e_abbreviation:
            abbrev = self.core.users.getUserAbbreviation(
                self.e_username.text(), fromConfig=False
            )
            self.e_abbreviation.setText(abbrev)

    @err_catcher(name=__name__)
    def browse(self, bType: str = "", getFile: bool = False, windowTitle: Optional[str] = None, uiEdit: Optional[QLineEdit] = None) -> None:
        """Open a file/folder browser dialog and populate the target line edit.
        
        Args:
            bType: Type of browse operation ("local", "mediaPlayer", or appName + "OR" for executable override)
            getFile: If True, opens file dialog; if False, opens directory dialog
            windowTitle: Custom window title for the dialog
            uiEdit: The line edit widget to populate with selected path
        """
        if bType == "local":
            windowTitle = "Select local project path"
            uiEdit = self.e_localPath
        elif bType == "mediaPlayer":
            windowTitle = "Select Media Player executable"
            uiEdit = self.e_mediaPlayerPath
        elif bType.endswith("OR"):
            pName = bType[:-2]
            windowTitle = "Select %s executable" % pName
            uiEdit = self.exOverridePlugins[pName]["le"]
        elif windowTitle is None or uiEdit is None:
            return

        if getFile:
            if platform.system() == "Windows":
                fStr = "Executable (*.exe);;All files (*)"
            else:
                fStr = "All files (*)"

            selectedPath = QFileDialog.getOpenFileName(
                self, windowTitle, uiEdit.text(), fStr
            )[0]
        else:
            selectedPath = QFileDialog.getExistingDirectory(
                self, windowTitle, uiEdit.text()
            )

        if selectedPath != "":
            uiEdit.setText(self.core.fixPath(selectedPath))

    @err_catcher(name=__name__)
    def orToggled(self, prog: str, state: int) -> None:
        """Enable or disable executable override path widgets based on checkbox state.
        
        Args:
            prog: The application/plugin name associated with the override
            state: The checkbox state (checked/unchecked)
        """
        self.exOverridePlugins[prog]["le"].setEnabled(state)
        self.exOverridePlugins[prog]["b"].setEnabled(state)

    @err_catcher(name=__name__)
    def rclPluginList(self, pos: Optional[QPoint] = None) -> None:
        """Handle right-click context menu on plugin list.
        
        Displays options to reload, load, unload, set auto-load, or open plugin folder.
        
        Args:
            pos: The cursor position where right-click occurred
        """
        selPlugs = []
        for i in self.tw_plugins.selectedItems():
            if i.row() not in selPlugs:
                selPlugs.append(i.row())

        rcmenu = QMenu(self)

        act_reload = rcmenu.addAction(
            "Reload", lambda: self.reloadPlugins(selected=True)
        )
        act_load = rcmenu.addAction("Load", lambda: self.loadPlugins(selected=True))
        act_unload = rcmenu.addAction(
            "Unload", lambda: self.loadPlugins(selected=True, unload=True)
        )
        act_autoload = rcmenu.addAction("Auto Load")
        act_autoload.setCheckable(True)
        act_open = rcmenu.addAction("Open in explorer", self.openPluginFolder)

        if len(selPlugs) == 0:
            return
        elif len(selPlugs) == 1:
            if self.tw_plugins.cellWidget(selPlugs[0], 0).isChecked():
                act_load.setEnabled(False)
            else:
                act_reload.setEnabled(False)
                act_unload.setEnabled(False)

            if self.tw_plugins.cellWidget(selPlugs[0], 1).isChecked():
                act_autoload.setChecked(True)
            else:
                act_autoload.setChecked(False)

        elif len(selPlugs) > 1:
            act_open.setEnabled(False)

            isAutoLoad = False
            for selPlug in selPlugs:
                if self.tw_plugins.cellWidget(selPlug, 1).isChecked():
                    isAutoLoad = True
                    break

            act_autoload.setChecked(isAutoLoad)

        act_autoload.toggled.connect(lambda x: self.setAutoLoadPlugins(selected=True, state=x))
        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def rclLoadPlugin(self, pos: Optional[QPoint] = None) -> None:
        """Handle right-click context menu on load plugin button.
        
        Shows option to add a plugin search path.
        
        Args:
            pos: The cursor position where right-click occurred
        """
        menu = QMenu(self)
        act_addPath = menu.addAction(
            "Add plugin searchpath...", self.addPluginSearchpath
        )
        menu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def integrationAdd(self, prog: str) -> None:
        """Add an integration for a plugin/application.
        
        Args:
            prog: The plugin/application name to add integration for
        """
        result = self.core.integration.addIntegration(prog)
        if result:
            self.refreshIntegrations()

    @err_catcher(name=__name__)
    def integrationRemove(self, prog: str) -> None:
        """Remove a selected integration for a plugin/application.
        
        Args:
            prog: The plugin/application name to remove integration from
        """
        items = self.integrationPlugins[prog]["lw"].selectedItems()
        if len(items) == 0:
            return

        installPath = items[0].text()
        result = self.core.integration.removeIntegration(prog, installPath)

        if result:
            self.refreshIntegrations()

    @err_catcher(name=__name__)
    def rclEnvironment(self, pos: QPoint) -> None:
        """Handle right-click context menu on environment variables table.
        
        Shows options to add, edit, make persistent, or remove environment variables.
        
        Args:
            pos: The cursor position where right-click occurred
        """
        rcmenu = QMenu(self)

        exp = QAction("Add row", self)
        exp.triggered.connect(self.addEnvironmentRow)
        rcmenu.addAction(exp)

        item = self.tw_environment.itemFromIndex(self.tw_environment.indexAt(pos))
        if item:
            exp = QAction("Make Persistent", self)
            exp.triggered.connect(lambda: self.makePersistent(item.row()))
            rcmenu.addAction(exp)

            exp = QAction("Remove", self)
            exp.triggered.connect(lambda: self.removeEnvironmentRow(item.row()))
            rcmenu.addAction(exp)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def addEnvironmentRow(self) -> None:
        """Add a new empty row to the environment variables table.
        
        Creates placeholder text items for key and value columns that can be edited.
        """
        count = self.tw_environment.rowCount()
        self.tw_environment.insertRow(count)
        item = QTableWidgetItem("< doubleclick to edit >")
        self.tw_environment.setItem(count, 0, item)
        item = QTableWidgetItem("< doubleclick to edit >")
        self.tw_environment.setItem(count, 1, item)

    @err_catcher(name=__name__)
    def removeEnvironmentRow(self, idx: int) -> None:
        """Remove an environment variable row by index.
        
        Args:
            idx: The row index to remove
        """
        self.tw_environment.removeRow(idx)

    @err_catcher(name=__name__)
    def makePersistent(self, idx: int) -> None:
        """Make an environment variable persistent at the system level.
        
        Uses Windows setx command to set the variable permanently in the registry.
        Only works on Windows systems.
        
        Args:
            idx: The row index of the environment variable to make persistent
        """
        dft = "< doubleclick to edit >"
        key = self.tw_environment.item(idx, 0).text()
        if not key or key == dft:
            self.core.popup("Invalid key.")
            return

        value = self.tw_environment.item(idx, 1).text()
        if value == dft:
            self.core.popup("Invalid value.")
            return

        with self.core.waitPopup(self.core, "Making env var persistent. Please wait..."):
            proc = subprocess.Popen("setx %s %s" % (key, value), stdout=subprocess.PIPE)
            stdout, _ = proc.communicate()

        if sys.version[0] == "3":
            stdout = stdout.decode("utf-8", "ignore")

        if "success" in stdout.lower():
            self.core.popup("Successfully set environment variable persistently.", severity="info")
        else:
            self.core.popup("Unknown result. The env var might not be set persistently. Result is:\n\n%s" % stdout)

    @err_catcher(name=__name__)
    def showEnvironment(self) -> None:
        """Open a dialog showing all current environment variables.
        
        Displays a read-only table with all system environment variables.
        """
        self.w_env = EnvironmentWidget(self)
        self.w_env.show()

    @err_catcher(name=__name__)
    def changeProject(self) -> None:
        """Open project selection dialog and close the settings window.
        
        Calls the core project selection and closes this settings dialog.
        """
        self.core.projects.setProject()
        self.close()

    @err_catcher(name=__name__)
    def saveSettings(self, changeProject: bool = True, configPath: Optional[str] = None, export: bool = False) -> None:
        """Save the current user settings to the configuration file.
        
        Collects all user preferences from UI elements, including username, local paths,
        media players, autosave settings, and DCC overrides. Saves to the config file and
        updates core settings. Triggers environment refresh and autosave timer adjustments.
        
        Args:
            changeProject: If True, changes the project after saving (default True)
            configPath: Path to config file to save to (default uses core.userini)
            export: If True, skips user/environment updates (default False)
        """
        if configPath is None:
            configPath = self.core.userini

        logger.debug("save prism settings")
        cData = {
            "globals": {},
            "localfiles": {},
            "useLocalFiles": {},
            "dccoverrides": {},
        }

        if len(self.e_username.text()) > 2:
            cData["globals"]["username"] = self.e_username.text()
            cData["globals"]["username_abbreviation"] = self.e_abbreviation.text()
            if not export:
                self.core.users.setUser(cData["globals"]["username"], abbreviation=cData["globals"]["username_abbreviation"])

        if hasattr(self.core, "projectName") and self.e_localPath.isEnabled():
            lpath = self.core.fixPath(self.e_localPath.text())
            if not lpath.endswith(os.sep):
                lpath += os.sep

            cData["localfiles"][self.core.projectName] = lpath
            if self.e_localPath.text() != "disabled" and not export:
                self.core.localProjectPath = lpath

        if hasattr(self.core, "projectName"):
            useLocal = [
                x
                for x in self.useLocalStates
                if self.useLocalStates[x] == self.cb_userUseLocal.currentText()
            ][0]
            cData["useLocalFiles"][self.core.projectName] = useLocal

        cData["globals"]["mediaPlayers"] = self.gb_mediaPlayers.getPlayerData()
        cData["globals"]["showonstartup"] = self.chb_browserStartup.isChecked()
        cData["globals"]["useMediaThumbnails"] = self.chb_mediaThumbnails.isChecked()
        cData["globals"]["autosave"] = self.chb_autosave.isChecked()
        cData["globals"]["capture_viewport"] = self.chb_captureViewport.isChecked()
        cData["globals"]["capture_viewport_products"] = self.chb_captureViewportProduct.isChecked()
        cData["globals"]["send_error_reports"] = self.chb_errorReports.isChecked()
        cData["globals"]["debug_mode"] = self.chb_debug.isChecked()
        if not os.getenv("PRISM_DELAYED_LOAD_PLUGINS"):
            cData["globals"]["deferred_plugins"] = self.e_deferredPlugins.text()
        cData["globals"]["standalone_stylesheet"] = self.cb_styleSheet.currentData().get("name", "")
        cData["environmentVariables"] = self.getEnvironmentVariables()

        for i in self.exOverridePlugins:
            c = self.exOverridePlugins[i]["chb"].isChecked()
            ct = self.exOverridePlugins[i]["le"].text()
            cData["dccoverrides"]["%s_override" % i] = c
            cData["dccoverrides"]["%s_path" % i] = ct

        self.core.callback(name="userSettings_saveSettings", args=[self, cData])

        if self.core.appPlugin.appType == "3d" and not export:
            if self.chb_autosave.isChecked():
                if not self.core.isAutosaveTimerActive():
                    self.core.startAutosaveTimer()
            else:
                self.core.startAutosaveTimer(quit=True)

        self.core.setConfig(data=cData, updateNestedData={"exclude": "environmentVariables"}, configPath=configPath)
        if not export:
            self.core.setDebugMode(self.chb_debug.isChecked())
            if self.trayChanged:
                self.core.setTrayStartup(self.chb_trayStartup.isChecked())
                self.trayChanged = False

            self.core.users.refreshEnvironment()

        self.core.callback(name="onUserSettingsSave", args=[self])

    @err_catcher(name=__name__)
    def onTrayChanged(self, state: int) -> None:
        """Handle tray startup checkbox state change.
        
        Sets flag indicating tray startup setting has been modified.
        
        Args:
            state: Qt checkbox state value (Qt.Checked or Qt.Unchecked)
        """
        self.trayChanged = True

    @err_catcher(name=__name__)
    def loadSettings(self, configPath: Optional[str] = None) -> None:
        """Load user settings from the configuration file into UI elements.
        
        Populates all user preference UI controls from the config file, including
        username, local project path, media players, startup options, and environment
        variables. Also configures tray startup options based on platform.
        
        Args:
            configPath: Path to config file to load from (default uses core.userini)
        """
        if configPath is None:
            configPath = self.core.userini

        if not os.path.exists(configPath):
            self.core.popup("Prism config does not exist.", title="Load Settings")
            return

        if hasattr(self.core, "projectName"):
            self.l_projectName.setText(self.core.projectName)
        else:
            self.l_projectName.setText("No current project")

        if hasattr(self.core, "projectPath"):
            self.l_projectPath.setText(self.core.projectPath)
        else:
            self.l_projectPath.setText("")

        if (
            hasattr(self.core, "useLocalFiles")
            and self.core.useLocalFiles
            and self.l_projectPath.text() != ""
        ):
            self.e_localPath.setText(self.core.localProjectPath)
        else:
            self.e_localPath.setText("disabled")
            self.e_localPath.setEnabled(False)
            self.b_browseLocal.setEnabled(False)

        if platform.system() == "Windows":
            trayStartupPath = os.path.join(
                os.getenv("PROGRAMDATA"),
                "Microsoft",
                "Windows",
                "Start Menu",
                "Programs",
                "Startup",
                "Prism.lnk",
            )
            if not os.path.exists(trayStartupPath):
                trayStartupPath = os.path.join(
                    os.getenv("APPDATA"),
                    "Microsoft",
                    "Windows",
                    "Start Menu",
                    "Programs",
                    "Startup",
                    "Prism.lnk",
                )
        elif platform.system() == "Linux":
            trayStartupPath = "/etc/xdg/autostart/PrismTray.desktop"
        elif platform.system() == "Darwin":
            userName = (
                os.environ["SUDO_USER"]
                if "SUDO_USER" in os.environ
                else os.environ["USER"]
            )
            trayStartupPath = (
                "/Users/%s/Library/LaunchAgents/com.user.PrismTray.plist" % userName
            )

        self.chb_trayStartup.setChecked(os.path.exists(trayStartupPath))

        configData = self.core.getConfig(configPath=configPath)
        self.core.callback(name="userSettings_loadSettings", args=[self, configData])

        if not configData:
            self.core.popup("Loading Prism Settings failed.")
        else:
            gblData = configData.get("globals", {})
            if "username" in gblData:
                self.e_username.setText(self.core.username)
                self.validate(uiWidget=self.e_username)

            if "username_abbreviation" in gblData:
                self.e_abbreviation.setText(self.core.user)
                self.validate(uiWidget=self.e_abbreviation)

            if "showonstartup" in gblData:
                self.chb_browserStartup.setChecked(gblData["showonstartup"])

            if "useMediaThumbnails" in gblData:
                self.chb_mediaThumbnails.setChecked(gblData["useMediaThumbnails"])

            if "useLocalFiles" in configData:
                if (
                    hasattr(self.core, "projectName")
                    and self.core.projectName in configData["useLocalFiles"]
                ):
                    idx = self.cb_userUseLocal.findText(
                        self.useLocalStates[
                            configData["useLocalFiles"][self.core.projectName]
                        ]
                    )
                    if idx != -1:
                        self.cb_userUseLocal.setCurrentIndex(idx)

            if "autosave" in gblData:
                self.chb_autosave.setChecked(gblData["autosave"])

            if "capture_viewport" in gblData:
                self.chb_captureViewport.setChecked(gblData["capture_viewport"])

            if "capture_viewport_products" in gblData:
                self.chb_captureViewportProduct.setChecked(gblData["capture_viewport_products"])

            if "send_error_reports" in gblData:
                self.chb_errorReports.setChecked(gblData["send_error_reports"])

            if "debug_mode" in gblData:
                self.chb_debug.setChecked(gblData["debug_mode"])

            if "mediaPlayers" in gblData:
                val = gblData["mediaPlayers"]
                if val:
                    self.gb_mediaPlayers.loadPlayerData(val)
            else:
                name = None
                path = None
                understandsFramepattern = None
                if "mediaPlayerName" in gblData:
                    name = gblData["mediaPlayerName"]

                if "rvpath" in gblData:
                    path = gblData["rvpath"]

                if "djvpath" in gblData:
                    path = gblData["djvpath"]

                if "mediaPlayerPath" in gblData:
                    path = gblData["mediaPlayerPath"]

                if "mediaPlayerFramePattern" in gblData:
                    understandsFramepattern = gblData["mediaPlayerFramePattern"]

                if name is not None and path is not None and understandsFramepattern is not None:
                    data = [{"name": name, "path": path, "understandsFramepattern": understandsFramepattern}]
                    self.gb_mediaPlayers.loadPlayerData(data)

            dccData = configData.get("dccoverrides", {})
            for i in self.exOverridePlugins:
                if "%s_override" % i in dccData:
                    self.exOverridePlugins[i]["chb"].setChecked(
                        dccData["%s_override" % i]
                    )

                dccPath = None
                if "%s_path" % i in dccData:
                    dccPath = dccData["%s_path" % i]

                if not dccPath and not self.exOverridePlugins[i]["chb"].isChecked():
                    execFunc = self.core.getPluginData(i, "getExecutable")
                    if execFunc is not None:
                        dccPath = execFunc()
                        if dccPath:
                            if not os.path.exists(dccPath) and os.path.exists(
                                os.path.dirname(dccPath)
                            ):
                                dccPath = os.path.dirname(dccPath)

                            self.core.setConfig("dccoverrides", "%s_path" % i, val=dccPath, configPath=configPath)

                if dccPath:
                    self.exOverridePlugins[i]["le"].setText(dccPath)

                self.exOverridePlugins[i]["le"].setEnabled(
                    self.exOverridePlugins[i]["chb"].isChecked()
                )
                self.exOverridePlugins[i]["b"].setEnabled(
                    self.exOverridePlugins[i]["chb"].isChecked()
                )

            if "environmentVariables" in configData and configData["environmentVariables"]:
                self.loadEnvironmant(configData["environmentVariables"])

            envOverride = os.getenv("PRISM_DELAYED_LOAD_PLUGINS")
            if envOverride:
                self.e_deferredPlugins.setText(envOverride)
                self.e_deferredPlugins.setEnabled(False)
                self.e_deferredPlugins.setToolTip("Controlled by PRISM_DELAYED_LOAD_PLUGINS environment variable")
            else:
                deferredPlugins = gblData.get("deferred_plugins", "")
                self.e_deferredPlugins.setText(deferredPlugins)
                self.e_deferredPlugins.setEnabled(True)
                self.e_deferredPlugins.setToolTip("")

        if not os.path.exists(self.core.prismIni):
            self.l_localPath.setEnabled(False)

        self.w_userUseLocal.setToolTip(
            'This setting overrides the "Use additional local project folder" option in the project settings for the current user. It doesn\'t affect any other users.'
        )
        self.refreshStyleSheets()

        ssheetName = None
        if self.core.appPlugin.pluginName == "Standalone":
            curSheet = self.core.getActiveStyleSheet()
            if curSheet:
                ssheetName = curSheet.get("label", "")
        elif "standalone_stylesheet" in gblData:
            ssheetName = gblData["standalone_stylesheet"]

        if ssheetName:        
            idx = self.cb_styleSheet.findText(ssheetName)
            if idx != -1:
                self.cb_styleSheet.setCurrentIndex(idx)

    @err_catcher(name=__name__)
    def keyPressedDialog(self, event: Any) -> None:
        """Handle key press events in the dialog.
        
        Intercepts Return key to prevent default behavior; passes other keys to original handler.
        
        Args:
            event: Qt key event
        """
        if event.key() == Qt.Key_Return:
            self.setFocus()
        else:
            self.origKeyPressEvent(event)

        event.accept()

    @err_catcher(name=__name__)
    def getEnvironmentVariables(self) -> Dict[str, str]:
        """Extract all environment variables from the table widget.
        
        Returns:
            Dictionary mapping environment variable names to values
        """
        variables = {}
        dft = "< doubleclick to edit >"
        for idx in range(self.tw_environment.rowCount()):
            key = self.tw_environment.item(idx, 0).text()
            if not key or key == dft:
                continue

            value = self.tw_environment.item(idx, 1).text()
            if value == dft:
                continue

            variables[key] = value

        return variables

    @err_catcher(name=__name__)
    def loadEnvironmant(self, variables: Dict[str, str]) -> None:
        """Load environment variables into the table widget.
        
        Note: Method name has typo ('Environmant' instead of 'Environment').
        
        Args:
            variables: Dictionary of environment variables to load
        """
        self.tw_environment.setRowCount(0)
        for idx, key in enumerate(sorted(variables)):
            self.tw_environment.insertRow(idx)
            item = QTableWidgetItem(key)
            self.tw_environment.setItem(idx, 0, item)
            item = QTableWidgetItem(variables[key])
            self.tw_environment.setItem(idx, 1, item)

        self.tw_environment.resizeColumnsToContents()

    @err_catcher(name=__name__)
    def contextMenuIntegration(self, pos: QPoint, listwidget: QListWidget) -> None:
        """Handle right-click context menu on integration list.
        
        Shows options to open integration path in explorer or copy it to clipboard.
        
        Args:
            pos: The cursor position where right-click occurred
            listwidget: The list widget where right-click occurred
        """
        item = listwidget.itemFromIndex(listwidget.indexAt(pos))
        if not item:
            return

        path = item.text()

        rcmenu = QMenu(self)
        openex = QAction("Open in Explorer", self)
        openex.triggered.connect(lambda: self.core.openFolder(path))
        rcmenu.addAction(openex)

        copAct = QAction("Copy path", self)
        copAct.triggered.connect(lambda: self.core.copyToClipboard(path))
        rcmenu.addAction(copAct)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def refreshIntegrations(self) -> None:
        """Refresh the integration lists for all plugins.
        
        Clears and rebuilds the integration lists showing available integration paths.
        """
        integrations = self.core.integration.getIntegrations()

        for app in self.integrationPlugins:
            try:
                self.integrationPlugins[app]["lw"].clear()
            except:
                continue

            if app in integrations:
                for path in integrations[app]:
                    item = QListWidgetItem(path)
                    self.integrationPlugins[app]["lw"].addItem(item)

                self.integrationPlugins[app]["lw"].setCurrentRow(0)
                self.integrationPlugins[app]["bremove"].setEnabled(True)
            else:
                self.integrationPlugins[app]["bremove"].setEnabled(False)

    @err_catcher(name=__name__)
    def refreshPlugins(self) -> None:
        """Refresh the plugin list table with current plugin information.
        
        Rebuilds the plugin table showing loaded/inactive plugins with version and location info.
        """
        self.tw_plugins.setRowCount(0)
        self.tw_plugins.setSortingEnabled(False)
        plugins = self.core.plugins.getPlugins()

        for pType in plugins:
            for pluginName in plugins[pType]:
                activeCheckBox = QCheckBox("")
                chb_autoload = QCheckBox("")
                chb_autoload.setChecked(self.core.plugins.getAutoLoadPlugin(pluginName))
                pluginPath = plugins[pType][pluginName].pluginPath
                if pType == "inactive":
                    version = ""
                    location = ""
                else:
                    activeCheckBox.setChecked(True)
                    version = getattr(plugins[pType][pluginName], "version", "")
                    location = (
                        plugins[pType][pluginName]
                        .location.replace("prismRoot", "Root")
                        .replace("prismProject", "Project")
                    )
                pluginData = {"path": pluginPath, "name": pluginName}
                activeCheckBox.toggled.connect(
                    lambda x, y=pluginData: self.loadPlugins([y], unload=not x)
                )
                chb_autoload.toggled.connect(
                    lambda x, y=pluginName: self.core.plugins.setAutoLoadPlugin(y, x)
                )
                activeItem = QTableWidgetItem()
                autoLoadItem = QTableWidgetItem()
                nameItem = QTableWidgetItem(pluginName)
                nameItem.setToolTip(pluginPath)
                typeItem = QTableWidgetItem(pType)
                versionItem = QTableWidgetItem(version)
                locItem = QTableWidgetItem(location)

                activeItem.setData(Qt.UserRole, pluginPath)

                rc = self.tw_plugins.rowCount()
                self.tw_plugins.insertRow(rc)

                self.tw_plugins.setItem(rc, 0, activeItem)
                self.tw_plugins.setItem(rc, 1, autoLoadItem)
                self.tw_plugins.setItem(rc, 2, nameItem)
                self.tw_plugins.setItem(rc, 3, typeItem)
                self.tw_plugins.setItem(rc, 4, versionItem)
                self.tw_plugins.setItem(rc, 5, locItem)

                self.tw_plugins.setCellWidget(rc, 0, activeCheckBox)
                self.tw_plugins.setCellWidget(rc, 1, chb_autoload)

        self.tw_plugins.resizeColumnsToContents()
        self.tw_plugins.setColumnWidth(2, 300)
        self.tw_plugins.setColumnWidth(3, 120)
        self.tw_plugins.setSortingEnabled(True)
        self.tw_plugins.sortByColumn(2, Qt.AscendingOrder)

    @err_catcher(name=__name__)
    def loadPlugins(self, plugins: Optional[List[Dict[str, str]]] = None, selected: bool = False, unload: bool = False) -> None:
        """Load or unload specified plugins and refresh the plugin display.
        
        Args:
            plugins: List of plugin dicts with 'path' and 'name' keys
            selected: If True, uses selected items from plugin table
            unload: If True, unloads plugins instead of loading them
        """
        if plugins is None and selected:
            plugins = []
            for i in self.tw_plugins.selectedItems():
                if i.column() != 0:
                    continue

                pluginPath = i.data(Qt.UserRole)
                if pluginPath:
                    name = self.tw_plugins.item(i.row(), 2).text()
                    plugins.append({"path": pluginPath, "name": name})

        if not plugins:
            return

        for pluginData in plugins:
            if unload:
                if pluginData["name"] == self.core.appPlugin.pluginName:
                    self.core.popup("Cannot unload the currently active app plugin.")
                    if len(plugins) == 1:
                        self.refreshPlugins()
                        return
                    else:
                        continue

                self.core.plugins.deactivatePlugin(pluginData["name"])
            else:
                result = self.core.plugins.activatePlugin(pluginData["path"])
                if not result:
                    self.refreshPlugins()
                    return

        ps = self.core.ps  # keep the Settings Window in memory to avoid crash
        if os.path.exists(self.core.prismIni):
            self.core.changeProject(self.core.prismIni)
        else:
            self.core.prismSettings(reload_module=False)

        QApplication.processEvents()
        if self.core.ps:
            self.core.ps.navigate({"tab": "Plugins", "settingsType": "User"})
            self.core.ps.activateWindow()
            self.core.ps.raise_()

    @err_catcher(name=__name__)
    def setAutoLoadPlugins(self, plugins: Optional[List[Dict[str, Any]]] = None, selected: bool = False, state: bool = False) -> None:
        """Set auto-load state for plugins.
        
        Args:
            plugins: List of plugin dicts with 'name' and 'row' keys
            selected: If True, uses selected items from plugin table
            state: If True, enables auto-load; if False, disables it
        """
        if plugins is None and selected:
            plugins = []
            for i in self.tw_plugins.selectedItems():
                if i.column() != 0:
                    continue

                pluginPath = i.data(Qt.UserRole)
                if pluginPath:
                    name = self.tw_plugins.item(i.row(), 2).text()
                    plugins.append({"path": pluginPath, "name": name, "row": i.row()})

        if not plugins:
            return

        for plugin in plugins:
            self.tw_plugins.cellWidget(plugin["row"], 1).setChecked(state)
            self.core.plugins.setAutoLoadPlugin(plugin["name"], state)

    @err_catcher(name=__name__)
    def managePluginsDlg(self, state: Optional[bool] = None) -> None:
        """Open the plugin path management dialog.
        
        Args:
            state: Optional state parameter (from signal connection)
        """
        self.dlg_managePluginPaths = ManagePluginPaths(self)
        self.dlg_managePluginPaths.show()        

    @err_catcher(name=__name__)
    def loadExternalPlugin(self, state: Optional[bool] = None) -> None:
        """Load a plugin from an external folder.
        
        Opens a folder selection dialog, loads the plugin, and adds it to config.
        
        Args:
            state: Optional state parameter (from signal connection)
        """
        startPath = getattr(
            self, "externalPluginStartPath", None
        ) or self.core.plugins.getPluginPath(location="root")
        selectedPath = QFileDialog.getExistingDirectory(
            self, "Select plugin folder", startPath
        )

        if not selectedPath:
            return

        result = self.core.plugins.loadPlugin(selectedPath, activate=True, showWarnings=True)
        selectedParent = os.path.dirname(selectedPath)
        if not result:
            self.externalPluginStartPath = selectedParent
            return

        self.core.plugins.addToPluginConfig(selectedPath)
        ps = self.core.ps  # keep the Settings Window in memory to avoid crash
        if os.path.exists(self.core.prismIni):
            self.core.changeProject(self.core.prismIni)
        else:
            self.core.prismSettings(restart=True, reload_module=False)

        QApplication.processEvents()
        self.core.ps.externalPluginStartPath = selectedParent
        self.core.ps.navigate({"tab": "Plugins", "settingsType": "User"})
        self.core.ps.activateWindow()
        self.core.ps.raise_()

    @err_catcher(name=__name__)
    def reloadPlugins(self, plugins: Optional[List[str]] = None, selected: bool = False) -> None:
        """Reload specified plugins or reload script.
        
        Args:
            plugins: List of plugin names to reload
            selected: If True, reloads selected items from plugin table
        """
        if plugins is None and selected:
            plugins = []
            for i in self.tw_plugins.selectedItems():
                if i.column() != 0:
                    continue

                pluginPath = i.data(Qt.UserRole)
                if pluginPath:
                    pluginName = self.core.plugins.getPluginNameFromPath(pluginPath)
                    plugins.append(pluginName)

            if not plugins:
                return

        self.core.reloadPlugins(plugins)
        ps = self.core.ps  # keep the Settings Window in memory to avoid crash
        if os.path.exists(self.core.prismIni):
            self.core.changeProject(self.core.prismIni)

        if not self.core.ps:
            self.core.prismSettings(reload_module=False)

        QApplication.processEvents()
        self.core.ps.navigate({"tab": "Plugins", "settingsType": "User"})
        self.core.ps.activateWindow()
        self.core.ps.raise_()

    @err_catcher(name=__name__)
    def reload(self) -> None:
        """Reload the entire Prism settings dialog.
        
        Restarts the Prism settings window while preserving the current category/tab.
        Temporarily disables quit-on-last-window-closed to prevent application exit,
        then launches a fresh settings instance with the previous tab restored.
        """
        tab = self.getCurrentCategory()
        prevVal = QApplication.instance().quitOnLastWindowClosed()
        QApplication.instance().setQuitOnLastWindowClosed(False)
        self.core.prismSettings(restart=True, reload_module=False)
        self.core.ps.navigate({"tab": tab, "settingsType": "User"})
        if prevVal:
            QApplication.instance().setQuitOnLastWindowClosed(prevVal)

    @err_catcher(name=__name__)
    def createPluginWindow(self) -> None:
        """Open the create plugin dialog.
        
        Allows users to create a new plugin with specified type and location.
        """
        dlg_plugin = CreatePluginDialog(self.core)
        action = dlg_plugin.exec_()

        if action == 0:
            return

        pluginName = dlg_plugin.e_name.text()
        pluginType = dlg_plugin.cb_type.currentText()
        pluginLocation = dlg_plugin.cb_location.currentText().lower()
        if pluginLocation == "custom":
            path = dlg_plugin.e_path.text()
        else:
            path = ""

        self.createPlugin(pluginName, pluginType, pluginLocation, path=path)

    @err_catcher(name=__name__)
    def createPlugin(self, pluginName: str, pluginType: str, location: str, path: str = "") -> None:
        """Create a new plugin with specified parameters.
        
        Args:
            pluginName: The name of the plugin to create
            pluginType: The type of plugin ("App", "Custom", "Single File")
            location: The location ("Computer", "User", "Project", "Custom")
            path: Custom path if location is "Custom"
        """
        pluginPath = self.core.createPlugin(
            pluginName, pluginType, location=location, path=path
        )

        if not pluginPath:
            return

        self.core.plugins.loadPlugin(pluginPath)
        if pluginType in ["Custom", "Single File"]:
            self.core.plugins.addToPluginConfig(pluginPath)

        ps = self.core.ps  # keep the Settings Window in memory to avoid crash
        if os.path.exists(self.core.prismIni):
            self.core.changeProject(self.core.prismIni)

        QApplication.processEvents()
        self.core.ps.navigate({"tab": "Plugins", "settingsType": "User"})
        self.core.ps.activateWindow()
        self.core.ps.raise_()

    @err_catcher(name=__name__)
    def addPluginSearchpath(self) -> None:
        """Add a new plugin search path from user selection.
        
        Opens a folder selection dialog, adds the selected path to plugin config,
        loads plugins from that directory, and updates the settings.
        """
        startPath = getattr(
            self, "externalPluginStartPath", None
        ) or self.core.plugins.getPluginPath(location="root")
        selectedPath = QFileDialog.getExistingDirectory(
            self, "Select plugin searchpath", startPath
        )

        if not selectedPath:
            return

        self.core.plugins.addToPluginConfig(searchPath=selectedPath)
        result = self.core.plugins.loadPlugins(directory=selectedPath)
        selectedParent = os.path.dirname(selectedPath)
        if not result:
            self.externalPluginStartPath = selectedParent
            self.core.popup("No plugins found in searchpath.")
            return

        ps = self.core.ps  # keep the Settings Window in memory to avoid crash
        if os.path.exists(self.core.prismIni):
            self.core.changeProject(self.core.prismIni)

        QApplication.processEvents()
        self.core.ps.externalPluginStartPath = selectedParent
        self.core.ps.navigate({"tab": "Plugins", "settingsType": "User"})
        self.core.ps.activateWindow()
        self.core.ps.raise_()

    @err_catcher(name=__name__)
    def openPluginFolder(self) -> None:
        """Open the selected plugin folder in the file explorer.
        
        Uses the currently selected plugin item in the table.
        """
        for i in self.tw_plugins.selectedItems():
            if i.column() != 0:
                continue

            pluginPath = i.data(Qt.UserRole)
            self.core.openFolder(pluginPath)

    @err_catcher(name=__name__)
    def refreshStyleSheets(self) -> None:
        """Refresh the stylesheet combo box with available stylesheets.
        
        Populates the dropdown with all registered stylesheets from the core.
        """
        self.cb_styleSheet.blockSignals(True)
        self.cb_styleSheet.clear()
        sheets = self.core.getRegisteredStyleSheets()
        for sheet in sheets:
            self.cb_styleSheet.addItem(sheet.get("label", ""), sheet)

        self.cb_styleSheet.blockSignals(False)

    @err_catcher(name=__name__)
    def onStyleSheetChanged(self, idx: int) -> None:
        """Handle stylesheet selection change.
        
        Updates the active stylesheet when user selects a different theme. Only
        applies to Standalone app plugin. Refreshes icons after stylesheet change
        to reflect new color scheme.
        
        Args:
            idx: Index of the selected stylesheet in the combobox.
        """
        if self.core.appPlugin.pluginName == "Standalone":
            sheet = self.cb_styleSheet.currentData()
            self.core.setActiveStyleSheet(sheet["name"])
            self.refreshIcons()

    @err_catcher(name=__name__)
    def startTray(self) -> None:
        """Start the Prism tray application.
        
        Launches the PrismTray.py script using appropriate shell command for the
        current platform (Windows, Linux, or macOS).
        """
        if platform.system() == "Windows":
            slavePath = os.path.join(self.core.prismRoot, "Scripts", "PrismTray.py")
            pythonPath = os.path.join(self.core.prismLibs, self.core.pythonVersion, "Prism.exe")
            for i in [slavePath, pythonPath]:
                if not os.path.exists(i):
                    msg = "%s does not exist." % os.path.basename(i)
                    self.core.popup(msg, title="Script missing")
                    return None

            command = ["%s" % pythonPath, "%s" % slavePath]
        elif platform.system() == "Linux":
            command = "bash %s/Tools/PrismTray.sh" % self.core.prismLibs
        elif platform.system() == "Darwin":
            command = "bash %s/Tools/PrismTray.sh" % self.core.prismLibs

        subprocess.Popen(command, shell=True)

    @err_catcher(name=__name__)
    def onProtocolHandlerClicked(self) -> None:
        """Register Prism protocol handler with the operating system.
        
        Attempts to register the Prism protocol handler to allow opening Prism
        resources via 'prism://' URLs. Shows success or failure message to user.
        Platform-specific implementation handled by core method.
        """
        result = self.core.registerPrismProtocolHandler()
        if result:
            self.core.popup("Installed Protocol Handler successfully.", severity="info")
        else:
            self.core.popup("Failed to install Protocol Handler.")

    @err_catcher(name=__name__)
    def onImportSettingsClicked(self) -> None:
        """Handle import user settings button click.
        
        Opens a file dialog to select a user settings file (JSON or YAML),
        then loads the settings from that file into the dialog. Used to import
        previously exported user settings configurations.
        """
        path = self.core.paths.requestFilepath(
            title="Load user settings",
            startPath=self.core.userini,
            parent=self,
            fileFilter="Config files (*.json *.yml)",
            saveDialog=False
        )

        if not path:
            return

        self.loadSettings(configPath=path)

    @err_catcher(name=__name__)
    def onExportSettingsClicked(self) -> None:
        """Handle export user settings button click.
        
        Opens a file dialog to select a destination for exporting current user
        settings. Saves all user configuration to a JSON or YAML file that can
        be later imported into another Prism installation.
        """
        path = self.core.paths.requestFilepath(
            title="Save user settings",
            startPath=self.core.userini,
            parent=self,
            fileFilter="Config files (*.json *.yml)",
            saveDialog=True
        )

        if not path:
            return

        self.saveSettings(configPath=path, export=True)

    @err_catcher(name=__name__)
    def enterEvent(self, event: QEvent) -> None:
        """Handle mouse enter event for the dialog.
        
        Restores the cursor when mouse enters the dialog area. Silently ignores
        any exceptions that may occur during cursor restoration.
        
        Args:
            event: The QEvent object generated when mouse enters the widget.
        """
        try:
            QApplication.restoreOverrideCursor()
        except:
            pass


class CreatePluginDialog(QDialog):
    """Dialog for creating new plugins with specified type and location.
    
    Allows users to define plugin name, type (App/Custom/Single File), and location
    (Computer/User/Project/Custom) before plugin creation.
    
    Attributes:
        core: Reference to the Prism core instance
        pluginName: Name of the plugin being created
    """
    def __init__(self, core: Any) -> None:
        """Initialize the create plugin dialog.
        
        Args:
            core: The Prism core instance
        """
        QDialog.__init__(self)
        self.core = core

        self.setupUi()
        self.connectEvents()
        self.pluginName = ""
        self.refreshPath()

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Create and configure all UI elements for the dialog.
        
        Creates input fields for plugin name, type selector, location selector,
        path display, and browse button.
        """
        self.core.parentWindow(self)
        self.setWindowTitle("Create Plugin")
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.lo_name = QHBoxLayout()
        self.l_name = QLabel("Plugin Name:")
        self.e_name = QLineEdit()
        self.lo_name.addWidget(self.l_name)
        self.lo_name.addWidget(self.e_name)
        self.lo_main.addLayout(self.lo_name)

        self.lo_type = QHBoxLayout()
        self.l_type = QLabel("Type:")
        self.cb_type = QComboBox()
        self.cb_type.addItems(["App", "Custom", "Single File"])
        self.cb_type.setCurrentIndex(1)
        self.lo_type.addWidget(self.l_type)
        self.lo_type.addWidget(self.cb_type)
        self.lo_main.addLayout(self.lo_type)

        self.lo_location = QHBoxLayout()
        self.l_location = QLabel("Location:")
        self.cb_location = QComboBox()
        self.cb_location.addItems(["Computer", "User", "Project", "Custom"])
        self.lo_location.addWidget(self.l_location)
        self.lo_location.addWidget(self.cb_location)
        self.lo_main.addLayout(self.lo_location)

        self.lo_path = QHBoxLayout()
        self.l_pathInfo = QLabel("Path:")
        self.l_path = QLabel("")
        self.l_path.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pluginPath = self.core.plugins.getComputerPluginPath()
        self.e_path = QLineEdit(pluginPath)
        self.b_browse = QPushButton("...")
        self.lo_path.addWidget(self.l_pathInfo)
        self.lo_path.addWidget(self.l_path)
        self.lo_path.addWidget(self.e_path)
        self.lo_path.addWidget(self.b_browse)
        self.lo_main.addLayout(self.lo_path)
        self.e_path.setVisible(False)
        self.b_browse.setVisible(False)
        self.b_browse.setContextMenuPolicy(Qt.CustomContextMenu)

        self.lo_main.addStretch()

        self.bb_main = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.bb_main.accepted.connect(self.accept)
        self.bb_main.rejected.connect(self.reject)

        self.lo_main.addWidget(self.bb_main)

        self.resize(500 * self.core.uiScaleFactor, 200 * self.core.uiScaleFactor)

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect all UI signals to their slot methods.
        
        Connects validation, path refresh, and browse functionality.
        """
        self.e_name.textChanged.connect(lambda x: self.validate(self.e_name, x))
        self.e_path.textChanged.connect(lambda x: self.validate(self.e_path, x))
        self.cb_type.activated.connect(lambda x: self.refreshPath())
        self.cb_location.activated.connect(lambda x: self.refreshPath())
        self.cb_location.activated.connect(
            lambda x: self.l_path.setVisible(self.cb_location.currentText() != "Custom")
        )
        self.cb_location.activated.connect(
            lambda x: self.e_path.setVisible(self.cb_location.currentText() == "Custom")
        )
        self.cb_location.activated.connect(
            lambda x: self.b_browse.setVisible(self.cb_location.currentText() == "Custom")
        )
        self.b_browse.clicked.connect(self.browse)
        self.b_browse.customContextMenuRequested.connect(
            lambda: self.core.openFolder(self.e_path.text())
        )

    @err_catcher(name=__name__)
    def browse(self) -> None:
        """Open a folder browser dialog for custom plugin location selection.
        
        Updates the path field with the selected folder path.
        """
        windowTitle = "Select plugin location"
        selectedPath = QFileDialog.getExistingDirectory(
            self, windowTitle, self.e_path.text()
        )

        if selectedPath:
            self.e_path.setText(self.core.fixPath(selectedPath))

    @err_catcher(name=__name__)
    def validate(self, uiWidget: QLineEdit, origText: Optional[str] = None) -> None:
        """Validate the plugin name or path input.
        
        Args:
            uiWidget: The line edit widget to validate
            origText: The original text (used by signal connections)
        """
        if uiWidget == self.e_name:
            allowChars = ["_"]
        else:
            allowChars = ["/", "\\", "_", " ", ":"]

        self.core.validateLineEdit(uiWidget, allowChars=allowChars)

        if uiWidget == self.e_name:
            self.refreshPath()
            self.pluginName = self.e_name.text()

    @err_catcher(name=__name__)
    def refreshPath(self) -> None:
        """Refresh the plugin path display based on current selections.
        
        Computes the full path where the plugin will be created based on type,
        location, and plugin name selections.
        """
        pluginType = self.cb_type.currentText()
        if self.cb_location.currentText() == "Computer":
            path = self.core.plugins.getComputerPluginPath()
        if self.cb_location.currentText() == "User":
            path = self.core.plugins.getUserPluginPath()
        elif self.cb_location.currentText() == "Project":
            path = self.core.plugins.getPluginPath(
                location="project", pluginType=pluginType
            )
        elif self.cb_location.currentText() == "Custom":
            path = self.e_path.text()
            if os.path.basename(path) == self.pluginName:
                path = os.path.dirname(path)

        name = self.e_name.text()
        fullPath = os.path.join(path, name)
        fullPath = os.path.normpath(fullPath).replace("\\", "/")
        self.l_path.setText(fullPath)


class AddProductPathDialog(QDialog):
    """Dialog for adding new export or render location paths to project.
    
    Allows users to specify a name and path for an additional product location.
    Emits pathAdded signal when path is successfully added.
    
    Signals:
        pathAdded: Emitted when a path has been successfully added
    
    Attributes:
        pathType: Type of location being added ('export' or 'render')
        core: Reference to the Prism core instance
    """

    pathAdded = Signal()

    def __init__(self, core: Any, pathType: str, parent: Optional[QWidget] = None) -> None:
        """Initialize the add product path dialog.
        
        Args:
            core: The Prism core instance
            pathType: Type of path being added ('export' or 'render')
            parent: Optional parent widget
        """
        QDialog.__init__(self)
        self.core = core
        self.pathType = pathType

        self.setupUi(parent=parent)
        self.connectEvents()

    @err_catcher(name=__name__)
    def setupUi(self, parent: Optional[QWidget] = None) -> None:
        """Set up the add product path dialog UI.
        
        Creates form with location name field, path field, and browse button.
        
        Args:
            parent: Optional parent widget for window parenting
        """
        self.core.parentWindow(self, parent)
        self.setWindowTitle("Add additional %s location" % self.pathType)
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.lo_name = QGridLayout()
        self.l_name = QLabel("Location Name:")
        self.e_name = QLineEdit()
        self.lo_name.addWidget(self.l_name, 0, 0)
        self.lo_name.addWidget(self.e_name, 0, 1, 1, 2)
        self.lo_main.addLayout(self.lo_name)

        self.l_pathInfo = QLabel("Path:")
        self.l_path = QLabel("")
        self.l_path.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.e_path = QLineEdit()
        self.b_browse = QPushButton("...")
        self.lo_name.addWidget(self.l_pathInfo, 1, 0)
        self.lo_name.addWidget(self.e_path, 1, 1)
        self.lo_name.addWidget(self.b_browse, 1, 2)
        self.b_browse.setContextMenuPolicy(Qt.CustomContextMenu)

        self.lo_main.addStretch()

        self.bb_main = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.bb_main.buttons()[0].setText("Add")
        self.bb_main.accepted.connect(self.addPath)
        self.bb_main.rejected.connect(self.reject)

        self.lo_main.addWidget(self.bb_main)

        self.resize(500 * self.core.uiScaleFactor, 150 * self.core.uiScaleFactor)

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect UI widget signals to slot methods.
        
        Connects text change signals for validation, browse button, and context menu.
        """
        self.e_name.textChanged.connect(lambda x: self.validate(self.e_name, x))
        self.e_path.textChanged.connect(lambda x: self.validate(self.e_path, x))
        self.b_browse.clicked.connect(self.browse)
        self.b_browse.customContextMenuRequested.connect(
            lambda: self.core.openFolder(self.e_path.text())
        )

    @err_catcher(name=__name__)
    def browse(self) -> None:
        """Open a folder selection dialog and set the selected path.
        
        Allows user to browse and select a folder path through a file dialog.
        """
        windowTitle = "Select %s location" % self.pathType
        selectedPath = QFileDialog.getExistingDirectory(
            self, windowTitle, self.e_path.text()
        )

        if selectedPath:
            self.e_path.setText(self.core.fixPath(selectedPath))

    @err_catcher(name=__name__)
    def validate(self, uiWidget: QLineEdit, origText: Optional[str] = None) -> None:
        """Validate line edit content based on widget type.
        
        Validation rules:
        - Location name: allows underscore and space
        - Path: allows forward/back slashes, underscore, space, and colon
        
        Args:
            uiWidget: The line edit widget to validate
            origText: Original text value (optional)
        """
        if uiWidget == self.e_name:
            allowChars = ["_", " "]
        else:
            allowChars = ["/", "\\", "_", " ", ":"]

        self.core.validateLineEdit(uiWidget, allowChars=allowChars)

    @err_catcher(name=__name__)
    def addPath(self) -> None:
        """Add the configured path to the project and emit pathAdded signal.
        
        Validates location name and path are not empty, then adds the path
        to either export or render product base paths based on pathType.
        Shows popup dialogs and returns early if validation fails. Closes
        the dialog after successfully adding the path.
        """
        location = self.e_name.text()
        path = self.e_path.text()

        if not location:
            self.core.popup("No location specified")
            return

        if not path:
            self.core.popup("No path specified")
            return

        if self.pathType == "export":
            self.core.paths.addExportProductBasePath(location, path)
        else:
            self.core.paths.addRenderProductBasePath(location, path)

        self.pathAdded.emit()
        self.close()


class EnvironmentWidget(QDialog):
    """Dialog displaying all current environment variables in a read-only table.
    
    Attributes:
        parent: Parent widget reference
        core: Reference to the Prism core instance
    """
    def __init__(self, parent: QWidget) -> None:
        """Initialize the environment widget.
        
        Args:
            parent: Parent widget
        """
        super(EnvironmentWidget, self).__init__()
        self.parent = parent
        self.core = self.parent.core
        self.core.parentWindow(self, parent=self.parent)
        self.setupUi()
        self.refreshEnvironment()

    def sizeHint(self) -> QSize:
        """Return recommended size for the dialog.
        
        Returns:
            QSize with dimensions 1000x700
        """
        return QSize(1000, 700)

    def setupUi(self) -> None:
        """Create and configure the environment variables table.
        
        Creates a read-only table widget with two columns (Variable, Value).
        """
        self.setWindowTitle("Current Environment")
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.tw_environment = QTableWidget()
        self.tw_environment.setColumnCount(2)
        self.tw_environment.setHorizontalHeaderLabels(["Variable", "Value"])
        self.tw_environment.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tw_environment.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tw_environment.horizontalHeader().setStretchLastSection(True)
        self.tw_environment.verticalHeader().setVisible(False)
        self.tw_environment.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.lo_main.addWidget(self.tw_environment)

    def refreshEnvironment(self) -> None:
        """Populate the table with all current environment variables.
        
        Reads from os.environ and populates the table with sorted variable names.
        """
        self.tw_environment.setRowCount(0)
        for idx, key in enumerate(sorted(os.environ)):
            self.tw_environment.insertRow(idx)
            item = QTableWidgetItem(key)
            self.tw_environment.setItem(idx, 0, item)
            item = QTableWidgetItem(os.environ[key])
            self.tw_environment.setItem(idx, 1, item)

        self.tw_environment.resizeColumnsToContents()


class HelpLabel(QLabel):
    """Custom label widget that displays a help message tooltip on hover.
    
    Signal:
        signalEntered: Emitted when the mouse enters the label area
    """

    signalEntered = Signal(object)

    def __init__(self, parent: QWidget) -> None:
        """Initialize the help label.
        
        Args:
            parent: Parent widget
        """
        super(HelpLabel, self).__init__()
        self.parent = parent

    def enterEvent(self, event: Any) -> None:
        """Handle mouse enter event.
        
        Emits the signalEntered signal when mouse enters the label.
        
        Args:
            event: Qt enter event
        """
        self.signalEntered.emit(self)

    def mouseMoveEvent(self, event: Any) -> None:
        """Handle mouse move event.
        
        Displays tooltip with help message at cursor position.
        
        Args:
            event: Qt mouse move event
        """
        QToolTip.showText(QCursor.pos(), self.msg)


class ManagePluginPaths(QDialog):
    """Dialog for managing plugin paths and search paths.
    
    Displays and manages both plugin installation paths and plugin search paths.
    Allows enabling/disabling, adding, and removing paths. Provides context menus
    for additional operations.
    
    Attributes:
        parent: Parent settings window
        core: Reference to the Prism core instance
    """
    
    def __init__(self, parent: QWidget) -> None:
        """Initialize the manage plugin paths dialog.
        
        Args:
            parent: Parent widget (UserSettings)
        """
        super(ManagePluginPaths, self).__init__()
        self.parent = parent
        self.core = self.parent.core
        self.core.parentWindow(self, parent=self.parent)
        self.setupUi()
        self.refresh()

    def sizeHint(self) -> QSize:
        """Return recommended size for the dialog.
        
        Returns:
            QSize with dimensions 1000x1000
        """
        return QSize(1000, 1000)

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Set up the ManagePluginPaths dialog UI components.
        
        Initializes the dialog with a header showing plugin search paths, buttons
        to add/remove paths, a scrollable list widget for browsing paths, and status
        information. Creates the layout structure and applies icons to buttons.
        """
        self.setWindowTitle("Manage Plugin Paths")
        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)

        self.w_paths = QWidget()
        self.lo_paths = QVBoxLayout()
        self.w_paths.setLayout(self.lo_paths)
        self.w_pathsHeader = QWidget()
        self.lo_pathsHeader = QHBoxLayout()
        self.lo_pathsHeader.setContentsMargins(9, 0, 0, 0)
        self.w_pathsHeader.setLayout(self.lo_pathsHeader)
        self.l_paths = QLabel("Plugin Paths:")
        self.lo_pathsHeader.addWidget(self.l_paths)
        self.lo_pathsHeader.addStretch()
        self.b_addPath = QToolButton()
        self.b_addPath.setToolTip("Add Path...")
        self.b_addPath.setFocusPolicy(Qt.NoFocus)
        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_addPath.setIcon(icon)
        self.lo_pathsHeader.addWidget(self.b_addPath)
        self.b_removePath = QToolButton()
        self.b_removePath.setToolTip("Remove selected paths")
        self.b_removePath.setFocusPolicy(Qt.NoFocus)
        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "remove.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_removePath.setIcon(icon)
        self.lo_pathsHeader.addWidget(self.b_removePath)
        self.tw_paths = QTableWidget()
        self.tw_paths.setColumnCount(2)
        self.tw_paths.setHorizontalHeaderLabels(["Enabled", "Path"])
        self.tw_paths.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tw_paths.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tw_paths.horizontalHeader().setStretchLastSection(True)
        self.tw_paths.horizontalHeader().setHighlightSections(False)
        self.tw_paths.verticalHeader().setDefaultSectionSize(20)
        self.tw_paths.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tw_paths.verticalHeader().setVisible(False)
        self.tw_paths.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tw_paths.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tw_paths.customContextMenuRequested.connect(self.contextMenuPaths)
        self.lo_paths.addWidget(self.w_pathsHeader)
        self.lo_paths.addWidget(self.tw_paths)

        self.w_searchPaths = QWidget()
        self.lo_searchPaths = QVBoxLayout()
        self.w_searchPaths.setLayout(self.lo_searchPaths)
        self.w_searchPathsHeader = QWidget()
        self.lo_searchPathsHeader = QHBoxLayout()
        self.lo_searchPathsHeader.setContentsMargins(9, 0, 0, 0)
        self.w_searchPathsHeader.setLayout(self.lo_searchPathsHeader)
        self.l_searchPaths = QLabel("Plugin Search Paths:")
        self.lo_searchPathsHeader.addWidget(self.l_searchPaths)
        self.lo_searchPathsHeader.addStretch()
        self.b_addSearchPath = QToolButton()
        self.b_addSearchPath.setToolTip("Add Searchpath...")
        self.b_addSearchPath.setFocusPolicy(Qt.NoFocus)
        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_addSearchPath.setIcon(icon)
        self.lo_searchPathsHeader.addWidget(self.b_addSearchPath)
        self.b_removeSearchPath = QToolButton()
        self.b_removeSearchPath.setToolTip("Remove selected searchpaths")
        self.b_removeSearchPath.setFocusPolicy(Qt.NoFocus)
        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "remove.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_removeSearchPath.setIcon(icon)
        self.lo_searchPathsHeader.addWidget(self.b_removeSearchPath)
        self.tw_searchPaths = QTableWidget()
        self.tw_searchPaths.setColumnCount(2)
        self.tw_searchPaths.setHorizontalHeaderLabels(["Enabled", "Path"])
        self.tw_searchPaths.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tw_searchPaths.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tw_searchPaths.horizontalHeader().setStretchLastSection(True)
        self.tw_searchPaths.horizontalHeader().setHighlightSections(False)        
        self.tw_searchPaths.verticalHeader().setDefaultSectionSize(20)
        self.tw_searchPaths.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tw_searchPaths.verticalHeader().setVisible(False)
        self.tw_searchPaths.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tw_searchPaths.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tw_searchPaths.customContextMenuRequested.connect(self.contextMenuSearchpaths)
        self.lo_searchPaths.addWidget(self.w_searchPathsHeader)
        self.lo_searchPaths.addWidget(self.tw_searchPaths)

        self.spl_main = QSplitter(Qt.Vertical)
        self.spl_main.addWidget(self.w_paths)
        self.spl_main.addWidget(self.w_searchPaths)
        self.lo_main.addWidget(self.spl_main)
        self.spl_main.setSizes([200, 100])

        self.bb_main = QDialogButtonBox(QDialogButtonBox.Ok)
        self.bb_main.buttons()[0].setText("OK (changes require Prism restart)")
        self.bb_main.accepted.connect(self.accept)

        self.b_addPath.clicked.connect(self.addPluginPath)
        self.b_removePath.clicked.connect(self.removePluginPaths)
        self.b_addSearchPath.clicked.connect(self.addPluginSearchpath)
        self.b_removeSearchPath.clicked.connect(self.removePluginSearchpaths)

        self.lo_main.addWidget(self.bb_main)

    @err_catcher(name=__name__)
    def refresh(self) -> None:
        """Refresh both plugin paths and search paths tables.
        
        Clears and repopulates both tables with current plugin paths and search paths,
        including enable/disable checkboxes and path information.
        """
        self.tw_paths.setRowCount(0)
        paths = self.getPluginPaths()
        for idx, path in enumerate(paths):
            self.tw_paths.insertRow(idx)
            chb_enabled = QCheckBox("")
            chb_enabled.setChecked(path["enabled"])
            chb_enabled.toggled.connect(lambda x, p=path["path"]: self.core.plugins.setPluginPathEnabled(p, x))
            self.tw_paths.setCellWidget(idx, 0, chb_enabled)
            item = QTableWidgetItem(path["path"])
            self.tw_paths.setItem(idx, 1, item)
            if not path["editable"]:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                chb_enabled.setEnabled(False)

        self.tw_paths.resizeColumnsToContents()

        self.tw_searchPaths.setRowCount(0)
        searchPaths = self.getPluginSearchPaths()
        for idx, path in enumerate(searchPaths):
            self.tw_searchPaths.insertRow(idx)
            chb_enabled = QCheckBox("")
            chb_enabled.setChecked(path["enabled"])
            chb_enabled.toggled.connect(lambda x, p=path["path"]: self.core.plugins.setPluginSearchPathEnabled(p, x))
            self.tw_searchPaths.setCellWidget(idx, 0, chb_enabled)
            item = QTableWidgetItem(path["path"])
            self.tw_searchPaths.setItem(idx, 1, item)
            if not path["editable"]:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                chb_enabled.setEnabled(False)

        self.tw_searchPaths.resizeColumnsToContents()

    @err_catcher(name=__name__)
    def getPluginPaths(self) -> List[Dict[str, Any]]:
        """Get list of configured plugin paths with metadata.
        
        Returns:
            List of dicts with keys: 'enabled', 'path', 'editable'
        """
        pluginPaths = []
        paths = self.core.plugins.getPluginDirs(includeEnv=True, includeDefaults=False, includeConfig=False, enabledOnly=False)["pluginPaths"]
        pluginPaths += [{"enabled": True, "path": p, "editable": False} for p in paths]
        paths = self.core.plugins.getPluginDirs(includeEnv=False, enabledOnly=False)["pluginPaths"]
        pluginPaths += [{"enabled": p.get("enabled", True), "path": p["path"], "editable": True} for p in paths]
        return pluginPaths

    @err_catcher(name=__name__)
    def getPluginSearchPaths(self) -> List[Dict[str, Any]]:
        """Get list of configured plugin search paths with metadata.
        
        Returns:
            List of dicts with keys: 'enabled', 'path', 'editable'
        """
        searchPaths = []
        paths = self.core.plugins.getPluginDirs(includeEnv=False, includeConfig=False)["searchPaths"]
        searchPaths += [{"enabled": True, "path": p, "editable": False} for p in paths]
        paths = self.core.plugins.getPluginDirs(includeEnv=True, includeDefaults=False, includeConfig=False, enabledOnly=False)["searchPaths"]
        searchPaths += [{"enabled": True, "path": p, "editable": False} for p in paths]
        paths = self.core.plugins.getPluginDirs(includeEnv=False, includeDefaults=False, enabledOnly=False)["searchPaths"]
        searchPaths += [{"enabled": p.get("enabled", True), "path": p["path"], "editable": True} for p in paths]
        return searchPaths

    @err_catcher(name=__name__)
    def addPluginPath(self) -> None:
        """Add a new plugin path through a folder selection dialog.
        
        Opens file dialog, loads plugin from selected folder, adds to config,
        and restarts Prism settings window to apply changes.
        """
        startPath = getattr(
            self, "externalPluginStartPath", None
        ) or self.core.plugins.getPluginPath(location="root")
        selectedPath = QFileDialog.getExistingDirectory(
            self, "Select plugin folder", startPath
        )

        if not selectedPath:
            return

        result = self.core.plugins.loadPlugin(selectedPath, activate=True)
        selectedParent = os.path.dirname(selectedPath)
        if not result:
            self.externalPluginStartPath = selectedParent
            self.core.popup("Couldn't load plugin")
            return

        self.core.plugins.addToPluginConfig(selectedPath)
        ps = self.core.ps  # keep the Settings Window in memory to avoid crash
        if os.path.exists(self.core.prismIni):
            self.core.changeProject(self.core.prismIni)
        else:
            self.core.prismSettings(restart=True, reload_module=False)

        QApplication.processEvents()
        if self.core.ps:
            self.core.ps.externalPluginStartPath = selectedParent
            self.core.ps.navigate({"tab": "Plugins", "settingsType": "User"})
            self.core.ps.activateWindow()
            self.core.ps.raise_()
            self.core.ps.w_user.managePluginsDlg()
            self.close()

    @err_catcher(name=__name__)
    def removePluginPaths(self) -> None:
        """Remove selected plugin paths from configuration.
        
        Removes selected plugin paths and refreshes the table.
        Shows popup confirmation if removal was successful.
        """
        toRemove = []
        for item in self.tw_paths.selectedItems():
            if item.column() != 1:
                continue

            path = item.text()
            toRemove.append(path)

        if not toRemove:
            msg = "No pluginpath is selected."
            self.core.popup(msg)
            return

        result = self.core.plugins.removeFromPluginConfig(pluginPaths=toRemove)
        self.refresh()
        if result:
            msg = "Pluginpaths removed successfully. Please restart Prism to let the changes take effect."
            self.core.popup(msg, severity="info")
        else:
            msg = "Failed to remove pluginpaths."
            self.core.popup(msg)

    @err_catcher(name=__name__)
    def addPluginSearchpath(self) -> None:
        """Add a new plugin search path and load plugins from it.
        
        Opens a directory browser dialog to allow user selection of a new plugin
        search path. Adds the path to plugin configuration, loads plugins from
        that directory, and triggers project change if needed. Updates the UI
        to reflect newly loaded plugins.
        """
        startPath = getattr(
            self, "externalPluginStartPath", None
        ) or self.core.plugins.getPluginPath(location="root")
        selectedPath = QFileDialog.getExistingDirectory(
            self, "Select plugin searchpath", startPath
        )

        if not selectedPath:
            return

        self.core.plugins.addToPluginConfig(searchPath=selectedPath)
        result = self.core.plugins.loadPlugins(directory=selectedPath)
        selectedParent = os.path.dirname(selectedPath)
        if not result:
            self.externalPluginStartPath = selectedParent
            self.core.popup("No plugins found in searchpath.")
            return

        ps = self.core.ps  # keep the Settings Window in memory to avoid crash
        if os.path.exists(self.core.prismIni):
            self.core.changeProject(self.core.prismIni)

        QApplication.processEvents()
        self.core.ps.externalPluginStartPath = selectedParent
        self.core.ps.navigate({"tab": "Plugins", "settingsType": "User"})
        self.core.ps.activateWindow()
        self.core.ps.raise_()
        self.core.ps.w_user.managePluginsDlg()
        if self.core.isObjectValid(self):
            self.close()

    @err_catcher(name=__name__)
    def removePluginSearchpaths(self) -> None:
        """Remove selected plugin search paths from configuration.
        
        Removes selected search paths and refreshes the table.
        Shows popup confirmation if removal was successful.
        """
        toRemove = []
        for item in self.tw_searchPaths.selectedItems():
            if item.column() != 1:
                continue

            path = item.text()
            toRemove.append(path)

        if not toRemove:
            msg = "No searchpath is selected."
            self.core.popup(msg)
            return

        result = self.core.plugins.removeFromPluginConfig(searchPaths=toRemove)
        self.refresh()
        if result:
            msg = "Searchpaths removed successfully. Please restart Prism to let the changes take effect."
            self.core.popup(msg, severity="info")
        else:
            msg = "Failed to remove searchpaths."
            self.core.popup(msg)

    @err_catcher(name=__name__)
    def setSelectedPathsEnabled(self, enabled: bool) -> None:
        """Set enabled state for all selected plugin paths.
        
        Args:
            enabled: Whether to enable (True) or disable (False) selected paths
        """
        for item in self.tw_paths.selectedItems():
            if item.column() != 1:
                continue

            widget = self.tw_paths.cellWidget(item.row(), 0)
            widget.setChecked(enabled)

    @err_catcher(name=__name__)
    def setSelectedSearchpathsEnabled(self, enabled: bool) -> None:
        """Set enabled state for all selected plugin search paths.
        
        Args:
            enabled: Whether to enable (True) or disable (False) selected search paths
        """
        for item in self.tw_searchPaths.selectedItems():
            if item.column() != 1:
                continue

            widget = self.tw_searchPaths.cellWidget(item.row(), 0)
            widget.setChecked(enabled)  

    @err_catcher(name=__name__)
    def contextMenuPaths(self, pos: QPoint) -> None:
        """Display context menu for plugin paths table.
        
        Provides actions to enable, disable, add, remove, open in explorer,
        and copy path for selected rows.
        
        Args:
            pos: Position where context menu was requested
        """
        items = self.tw_paths.selectedItems()
        items = [item for item in items if item.column() == 1]
        if not items:
            return

        rcmenu = QMenu(self)
        openex = QAction("Enable", self)
        openex.triggered.connect(lambda: self.setSelectedPathsEnabled(True))
        rcmenu.addAction(openex)

        openex = QAction("Disable", self)
        openex.triggered.connect(lambda: self.setSelectedPathsEnabled(False))
        rcmenu.addAction(openex)

        openex = QAction("Add path...", self)
        openex.triggered.connect(self.addPluginPath)
        rcmenu.addAction(openex)

        openex = QAction("Remove", self)
        openex.triggered.connect(self.removePluginPaths)
        rcmenu.addAction(openex)

        if len(items) == 1:
            path = items[0].text()
        else:
            path = ""

        openex = QAction("Open in Explorer", self)
        openex.triggered.connect(lambda: self.core.openFolder(path))
        rcmenu.addAction(openex)

        copAct = QAction("Copy path", self)
        copAct.triggered.connect(lambda: self.core.copyToClipboard(path))
        rcmenu.addAction(copAct)

        if len(items) != 1:
            openex.setEnabled(False)
            copAct.setEnabled(False)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def contextMenuSearchpaths(self, pos: QPoint) -> None:
        """Display context menu for plugin search paths table.
        
        Provides actions to enable, disable, add, remove, open in explorer,
        and copy path for selected rows.
        
        Args:
            pos: Position where context menu was requested
        """
        items = self.tw_searchPaths.selectedItems()
        items = [item for item in items if item.column() == 1]
        if not items:
            return

        rcmenu = QMenu(self)
        openex = QAction("Enable", self)
        openex.triggered.connect(lambda: self.setSelectedSearchpathsEnabled(True))
        rcmenu.addAction(openex)

        openex = QAction("Disable", self)
        openex.triggered.connect(lambda: self.setSelectedSearchpathsEnabled(False))
        rcmenu.addAction(openex)

        openex = QAction("Add path...", self)
        openex.triggered.connect(self.addPluginSearchpath)
        rcmenu.addAction(openex)

        openex = QAction("Remove", self)
        openex.triggered.connect(self.removePluginSearchpaths)
        rcmenu.addAction(openex)

        if len(items) == 1:
            path = items[0].text()
        else:
            path = ""

        openex = QAction("Open in Explorer", self)
        openex.triggered.connect(lambda: self.core.openFolder(path))
        rcmenu.addAction(openex)

        copAct = QAction("Copy path", self)
        copAct.triggered.connect(lambda: self.core.copyToClipboard(path))
        rcmenu.addAction(copAct)

        if len(items) != 1:
            openex.setEnabled(False)
            copAct.setEnabled(False)

        rcmenu.exec_(QCursor.pos())
