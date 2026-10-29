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
import shutil
import platform
import subprocess
import logging
from typing import Any, Optional, List, Dict, Tuple

prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
scriptPath = os.path.join(prismRoot, "Scripts")
if scriptPath not in sys.path:
    sys.path.append(scriptPath)

if __name__ == "__main__":
    import PrismCore

if platform.system() == "Windows":
    if sys.version[0] == "3":
        import winreg as _winreg
    else:
        import _winreg

else:
    import pwd

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher
from UserInterfacesPrism import PrismInstaller_ui


logger = logging.getLogger(__name__)

_WIN32_SHELL_MODULES = None
_WIN32_SHELL_IMPORT_ERROR = None


def getWin32ShellModules() -> Tuple[Optional[Any], Optional[Any], Optional[Any], Optional[Any], Optional[Any]]:
    """Get pywin32 shell modules lazily to avoid import-time crashes."""
    global _WIN32_SHELL_MODULES, _WIN32_SHELL_IMPORT_ERROR

    if _WIN32_SHELL_MODULES is not None:
        return _WIN32_SHELL_MODULES

    if platform.system() != "Windows":
        _WIN32_SHELL_MODULES = (None, None, None, None, None)
        return _WIN32_SHELL_MODULES

    try:
        from win32comext.shell import shellcon
        import win32comext.shell.shell as shell
        import win32con
        import win32event
        import win32process
    except Exception as e:
        _WIN32_SHELL_IMPORT_ERROR = e
        _WIN32_SHELL_MODULES = (None, None, None, None, None)
    else:
        _WIN32_SHELL_MODULES = (shellcon, shell, win32con, win32event, win32process)

    return _WIN32_SHELL_MODULES


class PrismSetup(QDialog):
    """Setup wizard dialog for Prism installation.
    
    Provides multi-page guided setup for installing startmenu entries,
    DCC integrations, and uninstaller.
    """

    signalShowing = Signal()

    def __init__(self, core: Any) -> None:
        """Initialize setup wizard.
        
        Args:
            core (Any): PrismCore instance.
        """
        QDialog.__init__(self)
        self.core = core
        self.silent = False
        self.loadLayout()
        self.connectEvents()
        self.setFocus()

    def loadLayout(self) -> None:
        """Load and configure wizard page layout."""
        self.setWindowTitle("Prism Setup")
        self.lo_main = QVBoxLayout()
        self.lo_main.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.lo_main)
        self.sw_main = QStackedWidget()
        self.lo_main.addWidget(self.sw_main)

        self.w_pageStart = Page_Start(self)
        self.w_pageStartmenu = Page_Startmenu(self)
        self.w_pageIntegrations = Page_Integrations(self)
        self.w_pageFinished = Page_Finished(self)

        self.sw_main.addWidget(self.w_pageStart)
        self.sw_main.addWidget(self.w_pageStartmenu)
        self.sw_main.addWidget(self.w_pageIntegrations)
        self.sw_main.addWidget(self.w_pageFinished)

        self.resize(800, 450)

    def connectEvents(self) -> None:
        """Connect page signals to navigation slots."""
        self.w_pageStart.signalNext.connect(self.nextClicked)
        self.w_pageStartmenu.signalNext.connect(self.nextClicked)
        self.w_pageIntegrations.signalNext.connect(self.nextClicked)
        self.w_pageFinished.signalBack.connect(self.backClicked)
        self.sw_main.currentChanged.connect(self.pageChanged)

    def backClicked(self) -> None:
        """Navigate to previous wizard page."""
        curIdx = self.sw_main.currentIndex()
        if curIdx == 0:
            return

        self.sw_main.setCurrentIndex(curIdx-1)

    def nextClicked(self) -> None:
        """Navigate to next wizard page."""
        curIdx = self.sw_main.currentIndex()
        if curIdx == (self.sw_main.count() - 1):
            return

        self.sw_main.setCurrentIndex(curIdx+1)

    def showEvent(self, event: Any) -> None:
        """Handle dialog show event.
        
        Args:
            event (Any): Show event.
        """
        self.signalShowing.emit()
        self.activateWindow()
        self.raise_()

    def pageChanged(self, idx: int) -> None:
        """Trigger entered callback when page changes.
        
        Args:
            idx (int): New page index.
        """
        self.sw_main.widget(idx).entered()

    def run(self, silent: bool = False) -> None:
        """Start the setup wizard.
        
        Args:
            silent (bool, optional): Run without user interaction. Defaults to False.
        """
        self.silent = silent
        self.nextClicked()


class Page_Start(QWidget):
    """Initial setup page for component selection.
    
    Allows user to select which components to install (startmenu, integrations, uninstaller).
    """

    signalNext = Signal()

    def __init__(self, parent: Any) -> None:
        """Initialize start page.
        
        Args:
            parent (Any): Parent widget.
        """
        super(Page_Start, self).__init__()
        self.setupUi()

    def setupUi(self) -> None:
        """Set up the start page UI components.
        
        Creates layout with checkboxes for component selection (startmenu, integrations, uninstaller).
        """
        self.lo_main = QVBoxLayout()
        self.lo_main.setContentsMargins(20, 20, 20, 20)
        self.setLayout(self.lo_main)

        self.w_center = QWidget()
        self.lo_center = QHBoxLayout()
        self.w_center.setLayout(self.lo_center)
        self.lo_main.addStretch()
        self.lo_main.addWidget(self.w_center)
        self.lo_main.addStretch()

        self.w_options = QWidget()
        self.lo_options = QVBoxLayout()
        self.w_options.setLayout(self.lo_options)

        self.lo_center.addStretch()
        self.lo_center.addWidget(self.w_options)
        self.lo_center.addStretch()

        self.l_header = QLabel("Please select the components you want to install:\n\n")
        self.lo_options.addWidget(self.l_header)

        self.chb_startmenu = QCheckBox("Startmenu entries")
        self.chb_startmenu.setChecked(True)
        self.chb_integrations = QCheckBox("DCC integrations")
        self.chb_integrations.setChecked(True)
        self.chb_uninstaller = QCheckBox("Create Uninstaller")
        self.chb_uninstaller.setChecked(False)
        self.lo_options.addWidget(self.chb_startmenu)
        self.lo_options.addWidget(self.chb_integrations)
        if platform.system() == "Windows":
            self.lo_options.addWidget(self.chb_uninstaller)

        self.w_footer = QWidget()
        self.lo_footer = QHBoxLayout()
        self.w_footer.setLayout(self.lo_footer)
        self.b_setup = QPushButton("Install")
        self.b_setup.setFocusPolicy(Qt.NoFocus)
        self.lo_footer.addStretch()
        self.lo_footer.addWidget(self.b_setup)
        self.lo_footer.addStretch()
        self.lo_main.addWidget(self.w_footer)

        self.b_setup.clicked.connect(self.signalNext.emit)


class Page_Startmenu(QWidget):
    """Setup page for creating startmenu entries and uninstaller.
    
    Automatically executes setup tasks when page is entered.
    """

    signalNext = Signal()

    def __init__(self, parent: Any) -> None:
        """Initialize startmenu page.
        
        Args:
            parent (Any): Parent widget.
        """
        super(Page_Startmenu, self).__init__()
        self.parent = parent
        self.setupUi()

    def setupUi(self) -> None:
        """Set up the user interface for startmenu setup page."""
        self.lo_main = QVBoxLayout()
        self.lo_main.setContentsMargins(20, 50, 20, 20)
        self.l_header = QLabel("Creating startmenu. Please wait...")
        self.l_header.setAlignment(Qt.AlignHCenter)

        self.lo_main.addStretch()
        self.lo_main.addWidget(self.l_header)
        self.lo_main.addStretch()
        self.setLayout(self.lo_main)

    def entered(self) -> None:
        """Execute setup tasks when page is entered.
        
        Creates startmenu entries and uninstaller if selected.
        """
        QApplication.processEvents()
        if self.parent.w_pageStart.chb_startmenu.isChecked():
            self.parent.core.setupStartMenu(quiet=True)

        if self.parent.w_pageStart.chb_uninstaller.isChecked():
            self.l_header.setText("Creating uninstaller. Please wait...")
            QApplication.processEvents()
            self.parent.core.setupUninstaller(quiet=True)

        QApplication.processEvents()
        self.signalNext.emit()


class Page_Integrations(QWidget):
    """Setup page for DCC integration installation.
    
    Displays PrismInstaller widget for selecting and installing integrations.
    """

    signalNext = Signal()

    def __init__(self, parent: Any) -> None:
        """Initialize integrations page.
        
        Args:
            parent (Any): Parent widget.
        """
        super(Page_Integrations, self).__init__()
        self.parent = parent
        self.setupUi()

    def setupUi(self) -> None:
        """Set up the user interface for integrations page."""
        self.lo_main = QVBoxLayout()
        self.lo_main.setContentsMargins(20, 20, 20, 20)
        self.setLayout(self.lo_main)

        self.w_footer = QWidget()
        self.lo_footer = QHBoxLayout()
        self.w_footer.setLayout(self.lo_footer)
        self.b_skip = QPushButton("Skip")
        self.b_install = QPushButton("Install")
        self.b_skip.setFocusPolicy(Qt.NoFocus)
        self.b_install.setFocusPolicy(Qt.NoFocus)
        self.lo_footer.addStretch()
        self.lo_footer.addWidget(self.b_skip)
        self.lo_footer.addWidget(self.b_install)
        self.lo_footer.addStretch()
        self.lo_main.addWidget(self.w_footer)

        self.b_skip.clicked.connect(self.skipClicked)
        self.b_install.clicked.connect(self.installClicked)

    def skipClicked(self) -> None:
        """Skip integration installation and proceed to next page."""
        self.signalNext.emit()

    def installClicked(self) -> None:
        """Install selected DCC integrations."""
        core = self.parent.core
        core.uiAvailable = True
        self.w_integrations.install(successPopup=False)
        core.uiAvailable = False
        self.signalNext.emit()

    def entered(self) -> None:
        """Load integration installer when page is entered."""
        if not self.parent.w_pageStart.chb_integrations.isChecked():
            self.signalNext.emit()
            return

        core = self.parent.core
        try:
            for idx in reversed(range(self.lo_main.count()-1)):
                item = self.lo_main.takeAt(idx)
                w = item.widget()
                if w:
                    w.setParent(None)
                    w.deleteLater()

            self.w_integrations = PrismInstaller(core=core)
            if not self.w_integrations.plugins:
                self.skipClicked()
                return

            self.w_integrations.buttonBox.setVisible(False)
            self.lo_main.insertWidget(0, self.w_integrations)
            if self.parent.silent:
                self.installClicked()

        except Exception as e:
            self.l_error = QLabel("Failed to load Prism:\n\n%s\n\nPlease contact the support" % e)
            self.sp_main = QSpacerItem(0, 0, QSizePolicy.Fixed, QSizePolicy.Expanding)
            self.lo_main.insertWidget(0, self.l_error)
            self.lo_main.insertItem(1, self.sp_main)
            self.b_close = QPushButton("Close")
            self.b_close.setFocusPolicy(Qt.NoFocus)
            self.lo_footer.insertWidget(1, self.b_close)
            self.b_skip.setVisible(False)
            self.b_install.setVisible(False)
            self.b_close.clicked.connect(self.parent.close)
            return


class Page_Finished(QWidget):
    """Final setup page displaying completion status.
    
    Allows user to launch Prism after installation.
    """

    signalBack = Signal()
    signalNext = Signal()

    def __init__(self, parent: Any) -> None:
        """Initialize finished page.
        
        Args:
            parent (Any): Parent widget.
        """
        super(Page_Finished, self).__init__()
        self.parent = parent
        self.setupUi()

    def setupUi(self) -> None:
        """Set up the user interface for completion page."""
        self.l_success = QLabel("")
        self.l_success.setAlignment(Qt.AlignHCenter)
        self.chb_launchPrism = QCheckBox("Launch Prism")
        self.chb_launchPrism.setChecked(True)

        self.w_actions = QWidget()
        self.lo_actions = QHBoxLayout()
        self.w_actions.setLayout(self.lo_actions)
        self.lo_actions.addStretch()
        self.lo_actions.addWidget(self.chb_launchPrism)
        self.lo_actions.addStretch()

        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.addStretch()
        self.lo_main.addWidget(self.l_success)
        self.lo_main.addWidget(self.w_actions)
        self.lo_main.addStretch()

        self.w_footer = QWidget()
        self.lo_footer = QHBoxLayout()
        self.w_footer.setLayout(self.lo_footer)
        self.b_back = QPushButton("Back")
        self.b_finish = QPushButton("Finish")
        self.b_back.setFocusPolicy(Qt.NoFocus)
        self.b_finish.setFocusPolicy(Qt.NoFocus)
        self.lo_footer.addStretch()
        self.lo_footer.addWidget(self.b_back)
        self.lo_footer.addWidget(self.b_finish)
        self.lo_footer.addStretch()
        self.lo_main.addWidget(self.w_footer)

        self.b_back.clicked.connect(self.backClicked)
        self.b_finish.clicked.connect(self.finish)

    def backClicked(self) -> None:
        """Navigate back to previous page."""
        self.signalBack.emit()

    def finish(self) -> None:
        """Complete setup wizard.
        
        Launches Prism if checkbox is selected, then closes dialog.
        """
        if not self.chb_launchPrism.isHidden() and self.chb_launchPrism.isChecked():
            self.launchPrism()

        QDialog.accept(self.parent)

    def launchPrism(self) -> None:
        """Launch Prism Project Browser."""
        target = self.parent.core.prismRoot
        exe = os.path.join(target, self.parent.core.pythonVersion, "Prism.exe")
        script = os.path.join(target, "Scripts", "PrismTray.py")
        subprocess.Popen([exe, script, "projectBrowser"])

    def entered(self) -> None:
        """Update UI when page is entered."""
        if not self.parent.w_pageStart.chb_integrations.isChecked():
            self.b_back.setVisible(False)

        msg = "Prism %s was installed successfully!" % self.parent.core.version
        self.l_success.setText(msg)
        logger.info(msg)


class PrismInstaller(QDialog, PrismInstaller_ui.Ui_dlg_installer):
    """Dialog for installing DCC plugin integrations.
    
    Displays available plugins and allows user to select integration paths.
    """
    
    def __init__(self, core: Any, plugins: Optional[List[str]] = None, parent: Optional[Any] = None) -> None:
        """Initialize installer dialog.
        
        Args:
            core (Any): PrismCore instance.
            plugins (Optional[List[str]]): List of plugin names. Defaults to all plugins.
            parent (Optional[Any]): Parent widget.
        """
        QDialog.__init__(self)
        self.core = core
        self.core.parentWindow(self, parent=parent)
        if not plugins:
            plugins = self.core.getPluginNames()

        self.plugins = {name: self.core.getPlugin(name) for name in plugins if name != "Standalone"}
        self.installShortcuts = True
        self.setupUi(self)
        try:
            if platform.system() == "Windows":
                shellconMod, shellMod, _, _, _ = getWin32ShellModules()
                if shellconMod and shellMod:
                    self.documents = shellMod.SHGetFolderPath(
                        0, shellconMod.CSIDL_PERSONAL, None, 0
                    )
                else:
                    self.documents = os.path.join(os.path.expanduser("~"), "Documents")
                    if _WIN32_SHELL_IMPORT_ERROR:
                        logger.warning(
                            "Failed to load pywin32 shell modules, using fallback documents path: %s"
                            % _WIN32_SHELL_IMPORT_ERROR
                        )

            self.tw_components.header().resizeSection(0, 200)
            self.tw_components.itemDoubleClicked.connect(self.openBrowse)
            self.tw_components.itemClicked.connect(self.CompItemClicked)
            self.tw_components.setContextMenuPolicy(Qt.CustomContextMenu)
            self.tw_components.customContextMenuRequested.connect(self.contextMenuIntegrations)

            self.refreshUI()
            self.resize(1000, self.height())

            self.setWindowTitle("Add Prism integrations")
            self.label.setText("Please select the integrations you want to add:")
            iconDir = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism")
            self.buttonBox.button(QDialogButtonBox.Ok).setText("Add")
            self.buttonBox.button(QDialogButtonBox.Ok).setIcon(
                self.core.media.getColoredIcon(os.path.join(iconDir, "add.png"))
            )
            self.buttonBox.button(QDialogButtonBox.Cancel).setIcon(
                self.core.media.getColoredIcon(os.path.join(iconDir, "delete.png"))
            )
            self.buttonBox.accepted.connect(self.install)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = "Errors occurred during the installation.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno)
            self.core.popup(msg, parent=self)

    def requestIntegrationPath(self, plugin: str, detectedPath: str) -> str:
        """Choose a destination for a single-folder integration."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add %s Integration" % plugin)
        layout = QVBoxLayout(dialog)
        pathLayout = QHBoxLayout()
        pathEdit = QLineEdit()
        if os.path.isdir(detectedPath):
            pathEdit.setText(detectedPath)
        else:
            pathEdit.setText(self.core.getPluginData(plugin, "examplePath") or "")

        iconDir = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism")
        browseButton = QPushButton()
        browseButton.setIcon(self.core.media.getColoredIcon(os.path.join(iconDir, "browse.png")))
        browseButton.setToolTip("Browse for integration folder")
        browseButton.setContextMenuPolicy(Qt.CustomContextMenu)
        browseButton.customContextMenuRequested.connect(
            lambda position: self.core.openFolder(pathEdit.text().strip())
        )
        browseButton.setAutoDefault(False)
        pathLayout.addWidget(QLabel("Integration folder:"))
        pathLayout.addWidget(pathEdit)
        pathLayout.addWidget(browseButton)
        layout.addLayout(pathLayout)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Add")
        buttons.button(QDialogButtonBox.Ok).setIcon(
            self.core.media.getColoredIcon(os.path.join(iconDir, "add.png"))
        )
        buttons.button(QDialogButtonBox.Cancel).setIcon(
            self.core.media.getColoredIcon(os.path.join(iconDir, "delete.png"))
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        def browsePath() -> None:
            path = self.core.paths.requestPath(
                title="Select %s folder" % plugin,
                startPath=pathEdit.text(),
                parent=dialog,
            )
            if path:
                pathEdit.setText(os.path.normpath(path))

        browseButton.clicked.connect(browsePath)
        dialog.resize(680, dialog.sizeHint().height())
        while dialog.exec_() == QDialog.Accepted:
            path = pathEdit.text().strip()
            if path and os.path.isdir(path):
                return os.path.normpath(path)

            self.core.popup("Please select an existing integration folder.", parent=dialog)

        return ""

    def openBrowse(self, item: Any, column: int) -> None:
        """Open folder browser for custom integration paths.
        
        Args:
            item (Any): Tree widget item.
            column (int): Column index.
        """
        if (
            item.parent() is not None
            and item.text(0) not in ["Custom"]
            or item.childCount() > 0
        ):
            return

        startPath = item.text(1)
        if not os.path.exists(startPath):
            ttPath = item.toolTip(1).replace("e.g. ", "").strip("\"")
            if os.path.exists(ttPath):
                startPath = ttPath

        path = self.core.paths.requestPath(
            title="Select destination folder", startPath=startPath, parent=self
        )
        if path:
            path = os.path.normpath(path)
            item.setText(1, path)
            item.setToolTip(1, path)
            item.setCheckState(0, Qt.Checked)
            self.refreshIntegrationStatuses()

    def refreshIntegrationStatuses(self) -> None:
        """Refresh path statuses supplied by optional plugin hooks."""
        statusColors = {
            "added": QColor(100, 200, 100),
            "not added": QColor(220, 80, 80),
            "update needed": QColor(230, 160, 60),
        }
        for index in range(self.tw_components.topLevelItemCount()):
            rootItem = self.tw_components.topLevelItem(index)
            plugin = self.plugins.get(rootItem.text(0))
            getStatus = getattr(plugin, "getIntegrationStatus", None)
            items = [rootItem.child(childIndex) for childIndex in range(rootItem.childCount())]
            rootItem.setText(2, "")
            rootItem.setData(2, Qt.ForegroundRole, None)
            for item in items or [rootItem]:
                item.setText(2, "")
                item.setData(2, Qt.ForegroundRole, None)
                if callable(getStatus) and os.path.isdir(item.text(1)):
                    try:
                        status = getStatus(item.text(1))
                        if isinstance(status, str):
                            item.setText(2, status)
                            color = statusColors.get(status.strip().lower())
                            if color is not None:
                                item.setForeground(2, QBrush(color))
                    except Exception:
                        logger.exception("Failed to check integration status for %s", rootItem.text(0))

    def CompItemClicked(self, item: Any, column: int) -> None:
        """Handle tree item click to enable/disable child items.
        
        Args:
            item (Any): Tree widget item clicked.
            column (int): Column index.
        """
        if item.childCount() == 0:
            return

        isEnabled = item.checkState(0) == Qt.Checked
        for i in range(item.childCount()):
            if isEnabled:
                if item.child(i).text(0) == "Custom" or item.child(i).text(1) != "":
                    item.child(i).setFlags(item.child(i).flags() | Qt.ItemIsEnabled)
            else:
                item.child(i).setFlags(item.child(i).flags() & ~Qt.ItemIsEnabled)

    def contextMenuIntegrations(self, position: QPoint) -> None:
        """Show path actions for the clicked item and tree-wide integration actions."""
        menu = QMenu(self)
        item = self.tw_components.itemAt(position)
        path = item.text(1).strip() if item else ""
        if path and os.path.isabs(path):
            menu.addAction("Copy Path", lambda: self.core.copyToClipboard(path))
            menu.addAction("Open in Explorer", lambda: self.core.openFolder(path))
            menu.addSeparator()
        menu.addAction("Refresh", self.refreshUI)
        menu.addSeparator()
        menu.addAction("Expand All", self.tw_components.expandAll)
        menu.addAction("Collapse All", self.tw_components.collapseAll)
        menu.addSeparator()
        menu.addAction("Check All", lambda: self.setIntegrationsChecked(True))
        menu.addAction("Uncheck All", lambda: self.setIntegrationsChecked(False))
        menu.exec_(self.tw_components.viewport().mapToGlobal(position))

    def setIntegrationsChecked(self, checked: bool) -> None:
        """Set integration checkboxes and update child availability."""
        state = Qt.Checked if checked else Qt.Unchecked
        for index in range(self.tw_components.topLevelItemCount()):
            item = self.tw_components.topLevelItem(index)
            if checked and not item.flags() & Qt.ItemIsEnabled:
                continue

            item.setCheckState(0, state)
            self.CompItemClicked(item, 0)
            for childIndex in range(item.childCount()):
                child = item.child(childIndex)
                if not checked or child.flags() & Qt.ItemIsEnabled:
                    child.setCheckState(0, state)

    def refreshUI(self) -> None:
        """Refresh UI with available plugins and integration paths."""
        try:
            self.tw_components.setColumnCount(3)
            self.tw_components.setHeaderLabels(["DCC", "Path", "Status"])
            self.tw_components.header().setVisible(True)
            self.tw_components.header().setStretchLastSection(False)
            self.tw_components.header().setSectionResizeMode(1, QHeaderView.Stretch)
            self.tw_components.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
            if platform.system() == "Windows":
                userFolders = {
                    "LocalAppdata": os.environ["localappdata"],
                    "AppData": os.environ["appdata"],
                    "UserProfile": os.environ["Userprofile"],
                    "Documents": self.documents,
                }
            else:
                userFolders = {}

            self.tw_components.clear()

            if len(self.plugins) > 0:
                integrationsItem = QTreeWidgetItem()

                for i in sorted(self.plugins):
                    if hasattr(self.plugins[i], "updateInstallerUI"):
                        self.plugins[i].updateInstallerUI(userFolders, integrationsItem)

                dccItems = integrationsItem.takeChildren()
                self.tw_components.addTopLevelItems(dccItems)
                for item in dccItems:
                    if item.childCount() == 1 and item.child(0).text(0) == "Custom":
                        customItem = item.takeChild(0)
                        item.setText(1, customItem.text(1))
                        item.setToolTip(0, customItem.toolTip(0))
                        item.setToolTip(1, customItem.toolTip(1))
                        item.setCheckState(0, customItem.checkState(0))
                        item.setData(0, Qt.UserRole, "customOnly")

                    item.setExpanded(True)
                    plugin = self.plugins.get(item.text(0))
                    iconPath = getattr(plugin, "appIcon", None)
                    if iconPath:
                        item.setIcon(0, QIcon(iconPath))

            self.refreshIntegrationStatuses()

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno)
            self.core.popup(msg, parent=self)
            return False

    def getEnteredIntegrations(self) -> Dict[str, List[str]]:
        """Get integration paths entered by user.
        
        Returns:
            Dict[str, List[str]]: Dictionary mapping plugin names to lists of install paths.
        """
        result = {}

        for index in range(self.tw_components.topLevelItemCount()):
            childItem = self.tw_components.topLevelItem(index)
            if childItem.text(0) not in self.plugins:
                continue

            if childItem.checkState(0) != Qt.Checked:
                continue

            paths = []
            if childItem.childCount():
                for childIndex in range(childItem.childCount()):
                    cchildItem = childItem.child(childIndex)
                    if cchildItem.checkState(0) == Qt.Checked and os.path.exists(cchildItem.text(1)):
                        paths.append(cchildItem.text(1))
            else:
                if os.path.exists(childItem.text(1)):
                    paths.append(childItem.text(1))

            result[childItem.text(0)] = paths

        return result

    def install(self, patch: bool = False, documents: str = "", successPopup: bool = True) -> Any:
        """Install selected DCC integrations.
        
        Args:
            patch (bool, optional): Unused parameter. Defaults to False.
            documents (str, optional): Unused parameter. Defaults to "".
            successPopup (bool, optional): Show success message. Defaults to True.
            
        Returns:
            Any: False on error, None on success.
        """
        try:
            # print "\n\nInstalling - please wait.."

            with self.core.waitPopup(self.core, "Adding Integrations - please wait.."):
                result = {}

                for index in range(self.tw_components.topLevelItemCount()):
                    childItem = self.tw_components.topLevelItem(index)
                    if childItem.text(0) not in self.plugins:
                        continue

                    installItem = childItem
                    if childItem.data(0, Qt.UserRole) == "customOnly":
                        installItem = childItem.clone()
                        customItem = QTreeWidgetItem(installItem, ["Custom", childItem.text(1)])
                        customItem.setCheckState(0, childItem.checkState(0))

                    self.plugins[childItem.text(0)].installerExecute(installItem, result)

                self.refreshIntegrationStatuses()

            if self.installShortcuts and not os.environ.get("prism_skip_root_install"):
                self.core.setupStartMenu(quiet=True)

            if False not in result.values():
                if self.installShortcuts and successPopup:
                    self.core.popup("Prism was installed successfully.", severity="info", parent=self)
            else:
                msgString = "Some parts failed to install:\n\n"
                for i in result:
                    msgString += "%s:\t\t%s\t\t\n\n" % (i, result[i])

                msgString = msgString.replace("True", "Success").replace(
                    "False", "Error"
                )

                self.core.popup(msgString, title="Prism Installation", parent=self)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno)
            self.core.popup(msg, parent=self)
            return False

    def closeEvent(self, event: Any) -> None:
        """Handle dialog close event.
        
        Args:
            event (Any): Close event.
        """
        event.accept()


class Uninstaller(QDialog):
    """Dialog for uninstalling Prism and its components.
    
    Handles removal of DCC integrations, plugins, preferences, and core files.
    """
    
    def __init__(self) -> None:
        """Initialize uninstaller dialog."""
        super(Uninstaller, self).__init__()
        self.conn = None
        self.listener = None
        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self) -> None:
        """Set up the user interface for uninstaller dialog."""
        self.setWindowTitle("Prism Uninstaller")
        msg = "Please select the components, which you want to uninstall:"
        lo_uninstall = QVBoxLayout()
        l_header = QLabel(msg)
        self.chb_prism = QCheckBox("Prism Files")
        self.chb_prism.setChecked(True)
        self.chb_plugins = QCheckBox("Local Prism Plugins")
        self.chb_plugins.setChecked(True)
        self.chb_integrations = QCheckBox("DCC Integrations")
        self.chb_integrations.setChecked(True)
        self.chb_prefs = QCheckBox("User Preferences")
        lo_uninstall.addWidget(l_header)
        lo_uninstall.addWidget(self.chb_prism)
        lo_uninstall.addWidget(self.chb_plugins)
        lo_uninstall.addWidget(self.chb_integrations)
        lo_uninstall.addWidget(self.chb_prefs)
        sp_uninstall = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Fixed)
        l_feedback = QLabel("Please let us know why you are uninstalling Prism.\nThis will help us to improve Prism in the future.")
        self.le_feedback = QTextEdit()
        self.le_feedback.setPlaceholderText("I'm uninstalling Prism because...")
        lo_uninstall.addItem(sp_uninstall)
        lo_uninstall.addWidget(l_feedback)
        lo_uninstall.addWidget(self.le_feedback)

        bb_uninstall = QDialogButtonBox()

        bb_uninstall.addButton("Uninstall", QDialogButtonBox.AcceptRole)
        bb_uninstall.addButton("Cancel", QDialogButtonBox.RejectRole)

        bb_uninstall.accepted.connect(self.onUninstallClicked)
        bb_uninstall.rejected.connect(self.reject)

        lo_uninstall.addWidget(bb_uninstall)
        self.setLayout(lo_uninstall)
        self.resize(650, 400)

    @err_catcher(name=__name__)
    def onUninstallClicked(self) -> None:
        """Handle uninstall button click."""
        self.run()

    @err_catcher(name=__name__)
    def run(self, silent: bool = False) -> None:
        """Execute uninstallation process.
        
        Args:
            silent (bool, optional): Run without UI feedback. Defaults to False.
        """
        waitPopup = self.waitPopup(self, "Uninstalling. Please wait...", parent=self, hidden=silent)
        with waitPopup:
            feedback = self.le_feedback.toPlainText()
            if feedback:
                if not silent:
                    text = "Sending feedback. Please wait..."
                    waitPopup.msg.setText(text)
                    QCoreApplication.processEvents()

                self.sendFeedback()

            postDeletePaths = []

            result = {}
            if self.chb_integrations.isChecked():
                if not silent:
                    text = "Removing integrations. Please wait..."
                    waitPopup.msg.setText(text)
                    QCoreApplication.processEvents()

                result.update(self.removeIntegrations())

            if self.chb_prefs.isChecked():
                self.sendData({"name": "getUserPrefDir"})
                self.userPrefPath = self.getAnswer()

            if self.chb_prefs.isChecked() or self.chb_plugins.isChecked():
                self.sendData({"name": "getDefaultPluginPath"})
                self.userPluginPath = self.getAnswer()

            self.shutDownConnection()
            self.closePrismProcesses()

            if self.chb_plugins.isChecked():
                if not silent:
                    text = "Removing plugins. Please wait..."
                    waitPopup.msg.setText(text)
                    QCoreApplication.processEvents()

                result["Local Plugins"] = self.removeLocalPlugins()

            if self.chb_prefs.isChecked():
                if not silent:
                    text = "Removing preferences. Please wait..."
                    waitPopup.msg.setText(text)
                    QCoreApplication.processEvents()

                result["Prism Preferences"] = self.removePrismPreferences()

            if self.chb_prism.isChecked():
                if not silent:
                    text = "Removing Prism. Please wait..."
                    waitPopup.msg.setText(text)
                    QCoreApplication.processEvents()

                result["Prism Files"] = self.removePrismFiles(postDeletePaths)

        if False not in result.values():
            msgStr = "Prism was uninstalled successfully."
            logger.info(msgStr)
            if not silent:
                if postDeletePaths:
                    msgStr += "\nThe last remaining files will be removed after closing this window."

                QMessageBox.information(self, "Prism Uninstallation", msgStr)

            self.finalize(postDeletePaths)
        else:
            msgString = "Some parts failed to uninstall:\n\n"
            for i in result:
                msgString += "%s:\t\t%s\t\t\n\n" % (i, result[i])

            msgString = (
                msgString.replace("True", "Success")
                .replace("False", "Error")
                .replace("Prism Files:", "Prism Files:\t")
                .replace("Local Plugins:", "Local Plugins:\t")
            )
            logger.warning(msgStr)

            if not silent:
                QMessageBox.warning(
                    self, "Prism Installation", msgString
                )
                sys.exit(0)

    @err_catcher(name=__name__)
    def closeEvent(self, event: Any) -> None:
        """Handle dialog close event.
        
        Args:
            event (Any): Close event.
        """
        self.shutDownConnection()

    @err_catcher(name=__name__)
    def getPrismConnection(self) -> Any:
        """Get or create connection to running Prism instance.
        
        Returns:
            Any: Connection object.
        """
        if not self.conn:
            address = ("localhost", 6551)
            from multiprocessing.connection import Listener
            self.listener = Listener(address, authkey=b'gfjdbfs')

            cmd = "import sys;sys.path.append('%s');import PrismCore;core = PrismCore.create();core.startCommunication(port=6550, key=b'gfjdbfs')" % os.path.dirname(__file__).replace("\\", "\\\\")
            subprocess.Popen([sys.executable, "-c", cmd])

            self.sconn = self.listener.accept()

            address = ('localhost', 6550)
            from multiprocessing.connection import Client
            self.conn = Client(address, authkey=b'gfjdbfs')

        return self.conn

    @err_catcher(name=__name__)
    def getAnswer(self) -> Any:
        """Receive answer from Prism instance.
        
        Returns:
            Any: Answer data from Prism instance.
        """
        try:
            answer = self.sconn.recv()
        except Exception:
            print("connecting to Prism failed")
            return

        if isinstance(answer, dict) and not answer.get("success"):
            if answer.get("error"):
                msg = answer.get("error")
                self.popup(msg)
                return

        return answer.get("data")

    @err_catcher(name=__name__)
    def shutDownConnection(self) -> None:
        """Close connection to Prism instance."""
        if self.listener:
            self.listener.close()

        if self.conn:
            try:
                self.conn.send({"name": "close"})
            except Exception:
                pass

            self.conn.close()

    @err_catcher(name=__name__)
    def sendData(self, data: Dict[str, Any]) -> None:
        """Send data to Prism instance.
        
        Args:
            data (Dict[str, Any]): Data to send.
        """
        conn = self.getPrismConnection()
        conn.send(data)

    @err_catcher(name=__name__)
    def finalize(self, postDeletePaths: List[str]) -> None:
        """Finalize uninstallation and schedule file deletion.
        
        Args:
            postDeletePaths (List[str]): Paths to delete after exit.
        """
        if postDeletePaths:
            cmd = "timeout /t 5 /nobreak > nul"
            for path in postDeletePaths:
                cmd += " & rmdir /S /Q \"%s\"" % path.replace("\\", "\\\\")
            
            import subprocess
            subprocess.Popen(cmd, shell=True)

        sys.exit(0)

    @err_catcher(name=__name__)
    def sendFeedback(self) -> None:
        """Send user feedback about uninstallation reason."""
        feedback = self.le_feedback.toPlainText()
        feedback = "I'm uninstalling Prism because...\n\n" + feedback
        self.sendData({"name": "sendFeedback", "data": feedback})
        self.getAnswer()

    @err_catcher(name=__name__)
    def removeIntegrations(self) -> Dict[str, bool]:
        """Remove all DCC integrations.
        
        Returns:
            Dict[str, bool]: Result of integration removal.
        """
        self.sendData({"name": "removeAllIntegrations"})
        answer = self.getAnswer()
        if not answer and answer != {}:
            answer = {"DCC Integrations": False}

        return answer

    @err_catcher(name=__name__)
    def removeLocalPlugins(self) -> bool:
        """Remove local user plugins.
        
        Returns:
            bool: True if successful.
        """
        if not self.userPluginPath:
            return False

        while os.path.exists(self.userPluginPath):
            try:
                shutil.rmtree(self.userPluginPath)
            except Exception as e:
                msg = "Failed to remove folder. Make sure all Prism instances are closed and no process is accessing this folder:\n\n%s\n\nError: %s" % (self.userPluginPath, e)
                result = self.popupQuestion(msg, buttons=["Retry", "Skip plugin removal"])
                if result != "Retry":
                    break

        result = not os.path.exists(self.userPluginPath)
        return result

    @err_catcher(name=__name__)
    def removePrismPreferences(self) -> bool:
        """Remove Prism user preferences.
        
        Returns:
            bool: True if successful.
        """
        if not self.userPrefPath:
            return False

        if not self.userPluginPath:
            return False

        result = True
        if os.path.exists(self.userPrefPath):
            for root, folders, files in os.walk(self.userPrefPath):
                if root == os.path.dirname(self.userPluginPath):
                    folders[:] = [f for f in folders if f != os.path.basename(self.userPluginPath)]

                for folder in folders:
                    path = os.path.join(root, folder)
                    
                    while os.path.exists(path):
                        try:
                            shutil.rmtree(path)
                        except Exception as e:
                            msg = "Failed to remove folder. Make sure all Prism instances are closed and no process is accessing this folder:\n\n%s\n\nError: %s" % (path, e)
                            result = self.popupQuestion(msg, buttons=["Retry", "Skip preferences removal"])
                            if result != "Retry":
                                return False

                for file in files:
                    path = os.path.join(root, file)
                    while os.path.exists(path):
                        try:
                            os.remove(path)
                        except Exception as e:
                            msg = "Failed to remove file. Make sure all Prism instances are closed and no process is accessing this file:\n\n%s\n\nError: %s" % (path, e)
                            result = self.popupQuestion(msg, buttons=["Retry", "Skip preferences removal"])
                            if result != "Retry":
                                return False

            if not os.listdir(self.userPrefPath):
                try:
                    shutil.rmtree(self.userPrefPath)
                except:
                    pass

        return result

    @err_catcher(name=__name__)
    def closePrismProcesses(self) -> None:
        """Close all running Prism processes."""
        try:
            import psutil
        except:
            pass
        else:
            PROCNAMES = ["Prism.exe"]
            for proc in psutil.process_iter():
                if proc.name() in PROCNAMES:
                    p = psutil.Process(proc.pid)
                    if proc.pid == os.getpid():
                        continue

                    try:
                        if "SYSTEM" not in p.username():
                            try:
                                proc.kill()
                            except:
                                pass
                    except:
                        pass

    @err_catcher(name=__name__)
    def removePrismFiles(self, postDeletePaths: List[str]) -> bool:
        """Remove Prism core files.
        
        Args:
            postDeletePaths (List[str]): List to append paths requiring delayed deletion.
            
        Returns:
            bool: True if successful.
        """
        try:
            if platform.system() == "Windows":
                result = self.removeWindowsSpecificData()

            elif platform.system() == "Linux":
                result = self.removeLinuxSpecificData()

            elif platform.system() == "Darwin":
                result = self.removeMacSpecificData()

            if not result:
                return result

            postDeletePaths.append(prismRoot)
            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = "Error occurred during Prism files removal:\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno)
            self.popup(msg, parent=self)
            return False

    @err_catcher(name=__name__)
    def removeWindowsSpecificData(self) -> bool:
        """Remove Windows-specific Prism data (startmenu, shortcuts, registry).
        
        Returns:
            bool: True if successful.
        """
        basepath = os.path.join(
            os.environ["appdata"],
            "Microsoft",
            "Windows",
            "Start Menu",
            "Programs",
        )

        smTray = os.path.join(basepath, "Prism", "Prism.lnk")
        suTray = os.path.join(basepath, "Startup", "Prism.lnk")
        pFiles = [smTray, suTray]

        for file in pFiles:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass

        smFolder = os.path.dirname(smTray)
        try:
            shutil.rmtree(smFolder)
        except:
            pass

        desktopIcon = os.path.join(os.environ["USERPROFILE"], "Desktop", "Prism.lnk")
        if os.path.exists(desktopIcon):
            try:
                os.remove(desktopIcon)
            except:
                pass

        result = self.removeUninstallerFromWindowsRegistry()
        return result

    @err_catcher(name=__name__)
    def removeUninstallerFromWindowsRegistry(self) -> bool:
        """Remove uninstaller entry from Windows registry.
        
        Returns:
            bool: True if successful.
        """
        try:
            _winreg.DeleteKey(
                _winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Prism Pipeline 2.0",
            )
        except Exception as e:
            print("failed to remove uninstall key from windows registry: %s" % e)
            return False

        return True

    @err_catcher(name=__name__)
    def removeLinuxSpecificData(self) -> bool:
        """Remove Linux-specific Prism data (desktop files, menu entries).
        
        Returns:
            bool: True if successful.
        """
        trayStartup = "/etc/xdg/autostart/PrismTray.desktop"
        trayStartMenu = "/usr/share/applications/PrismTray.desktop"
        pbStartMenu = "/usr/share/applications/PrismProjectBrowser.desktop"
        settingsStartMenu = "/usr/share/applications/PrismSettings.desktop"
        pMenuTarget = "/etc/xdg/menus/applications-merged/Prism.menu"
        userName = (
            os.environ["SUDO_USER"]
            if "SUDO_USER" in os.environ
            else os.environ["USER"]
        )
        desktopPath = "/home/%s/Desktop/PrismProjectBrowser.desktop" % userName

        pFiles = [
            trayStartMenu,
            pbStartMenu,
            settingsStartMenu,
            desktopPath,
        ]
        from PrismCore import getLinuxTrayPaths

        trayPaths = getLinuxTrayPaths(prismRoot)
        for key in ("autostart", "applications"):
            path = trayPaths[key]
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError as e:
                    logger.warning("Failed to remove Linux tray shortcut %s: %s", path, e)
                    return False

        if not os.environ.get("prism_skip_root_install"):
            pFiles += [
                trayStartup,
                pMenuTarget,
            ]

        for file in pFiles:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass

        return True

    @err_catcher(name=__name__)
    def removeMacSpecificData(self) -> bool:
        """Remove macOS-specific Prism data (LaunchAgents, desktop shortcuts).
        
        Returns:
            bool: True if successful.
        """
        userName = (
            os.environ["SUDO_USER"]
            if "SUDO_USER" in os.environ
            else os.environ["USER"]
        )
        trayStartup = (
            "/Users/%s/Library/LaunchAgents/com.PrismTray.plist" % userName
        )
        desktopPath = "/Users/%s/Desktop/Prism Project Browser" % userName
        pFiles = [trayStartup, desktopPath]

        for file in pFiles:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass

        return True

    @err_catcher(name=__name__)
    def popup(
        self,
        text: str,
        title: Optional[str] = None,
        severity: str = "warning",
        notShowAgain: bool = False,
        parent: Optional[Any] = None,
        modal: bool = True,
        widget: Optional[Any] = None,
        show: bool = True,
    ) -> Optional[Dict[str, bool]]:
        """Display popup message dialog.
        
        Args:
            text (str): Message text.
            title (Optional[str]): Dialog title.
            severity (str): Severity level ("warning", "info", "error").
            notShowAgain (bool): Show "Don't show again" checkbox.
            parent (Optional[Any]): Parent widget.
            modal (bool): Modal dialog.
            widget (Optional[Any]): Additional widget to display.
            show (bool): Show dialog immediately.
            
        Returns:
            Optional[Dict[str, bool]]: Dictionary with notShowAgain checkbox state if applicable.
        """
        if title is None:
            if severity == "warning":
                title = "Prism - Warning"
            elif severity == "info":
                title = "Prism - Information"
            elif severity == "error":
                title = "Prism - Error"

        if sys.version[0] == "3":
            if not isinstance(text, str):
                text = str(text)
            if not isinstance(title, str):
                title = str(title)
        else:
            if not isinstance(text, basestring):
                text = unicode(text)
            if not isinstance(title, basestring):
                title = unicode(title)

        parent = parent or self
        msg = QMessageBox(parent)
        msg.setText(text)
        msg.setWindowTitle(title)
        msg.setModal(modal)

        if severity == "warning":
            msg.setIcon(QMessageBox.Icon.Warning)
        elif severity == "info":
            msg.setIcon(QMessageBox.Icon.Information)
        else:
            msg.setIcon(QMessageBox.Icon.Critical)
        msg.addButton(QMessageBox.Ok)
        if notShowAgain:
            msg.chb = QCheckBox("Don't show again")
            msg.setCheckBox(msg.chb)
            msg.setText(text + "\n")

        if widget:
            msg.layout().addWidget(widget, 1, 2)

        if show:
            if modal:
                msg.exec_()
            else:
                msg.show()

        if notShowAgain:
            return {"notShowAgain": msg.chb.isChecked()}

        return msg

    @err_catcher(name=__name__)
    def popupQuestion(
        self,
        text: str,
        title: Optional[str] = None,
        buttons: Optional[List[str]] = None,
        default: Optional[str] = None,
        icon: Optional[Any] = None,
        widget: Optional[Any] = None,
        parent: Optional[Any] = None,
        escapeButton: Optional[str] = None,
    ) -> str:
        """Display question dialog with custom buttons.
        
        Args:
            text (str): Question text.
            title (Optional[str]): Dialog title.
            buttons (Optional[List[str]]): Button labels.
            default (Optional[str]): Default button label.
            icon (Optional[Any]): Dialog icon.
            widget (Optional[Any]): Additional widget.
            parent (Optional[Any]): Parent widget.
            escapeButton (Optional[str]): Escape button label.
            
        Returns:
            str: Clicked button text.
        """
        text = str(text)
        title = str(title or "Prism")
        buttons = buttons or ["Yes", "No"]
        icon = QMessageBox.Question if icon is None else icon
        parent = parent or self

        msg = QMessageBox(
            icon,
            title,
            text,
            parent=parent,
        )
        for button in buttons:
            if button in ["Close", "Cancel", "Ignore"]:
                role = QMessageBox.RejectRole
            else:
                role = QMessageBox.YesRole
            b = msg.addButton(button, role)
            if default == button:
                msg.setDefaultButton(b)

            if escapeButton == button:
                msg.setEscapeButton(b)

        if widget:
            msg.layout().addWidget(widget, 1, 2)

        msg.exec_()
        result = msg.clickedButton().text()

        return result

    @err_catcher(name=__name__)
    def popupNoButton(
        self,
        text: str,
        title: Optional[str] = None,
        buttons: Optional[List[str]] = None,
        default: Optional[str] = None,
        icon: Optional[Any] = None,
        parent: Optional[Any] = None,
        show: bool = True,
    ) -> Any:
        """Display message dialog without standard buttons.
        
        Args:
            text (str): Message text.
            title (Optional[str]): Dialog title.
            buttons (Optional[List[str]]): Unused parameter.
            default (Optional[str]): Unused parameter.
            icon (Optional[Any]): Dialog icon.
            parent (Optional[Any]): Parent widget.
            show (bool): Show dialog immediately.
            
        Returns:
            Any: Message box widget.
        """
        text = str(text)
        title = str(title or "Prism")
        parent = parent or self

        msg = QMessageBox(
            QMessageBox.NoIcon,
            title,
            text,
            QMessageBox.Cancel,
            parent=parent
        )

        for i in msg.buttons():
            i.setVisible(False)
        msg.setModal(False)
        if show:
            msg.show()
            QCoreApplication.processEvents()

        return msg

    class waitPopup(QObject):
        """Context manager for displaying wait/progress popups during uninstallation.
        
        Usage:
            with self.waitPopup(self, "Uninstalling..."):
                # long running operation
        """

        canceled = Signal()

        def __init__(
            self,
            core: Any,
            text: str,
            title: Optional[str] = None,
            buttons: Optional[List[str]] = None,
            default: Optional[str] = None,
            icon: Optional[Any] = None,
            hidden: bool = False,
            parent: Optional[Any] = None,
            allowCancel: bool = False,
            activate: bool = True,
        ) -> None:
            """Initialize wait popup.
            
            Args:
                core (Any): Core instance.
                text (str): Message text.
                title (Optional[str]): Dialog title.
                buttons (Optional[List[str]]): Button labels.
                default (Optional[str]): Default button.
                icon (Optional[Any]): Dialog icon.
                hidden (bool): Don't show popup.
                parent (Optional[Any]): Parent widget.
                allowCancel (bool): Allow cancellation.
                activate (bool): Activate window when shown.
            """
            self.core = core
            super(self.core.waitPopup, self).__init__()
            self.parent = parent
            self.text = text
            self.title = title
            self.buttons = buttons
            self.default = default
            self.icon = icon
            self.hidden = hidden
            self.allowCancel = allowCancel
            self.activate = activate
            self.msg = None

        def __enter__(self) -> 'waitPopup':
            """Enter context manager.
            
            Returns:
                waitPopup: Self.
            """
            if not self.hidden:
                self.show()
            
            return self

        def __exit__(self, type: Any, value: Any, traceback: Any) -> None:
            """Exit context manager.
            
            Args:
                type (Any): Exception type.
                value (Any): Exception value.
                traceback (Any): Traceback object.
            """
            self.close()

        def createPopup(self) -> None:
            """Create popup widget."""
            self.msg = self.core.popupNoButton(
                self.text,
                title=self.title,
                buttons=self.buttons,
                default=self.default,
                icon=self.icon,
                parent=self.parent,
                show=False,
            )
            if not self.activate:
                self.msg.setAttribute(Qt.WA_ShowWithoutActivating)

        def show(self) -> None:
            """Show popup dialog."""
            self.createPopup()
            self.msg.show()
            QCoreApplication.processEvents()

        def exec_(self) -> None:
            """Execute popup modally."""
            self.createPopup()
            for button in self.msg.buttons():
                button.setVisible(self.allowCancel)

            #    if self.allowCancel:
            #        self.msg.canceled.connect(self.canceled)

            result = self.msg.exec_()
            if result:
                self.cancel()

        def close(self) -> None:
            """Close popup dialog."""
            if self.msg and self.msg.isVisible():
                self.msg.close()

        def cancel(self) -> None:
            """Cancel operation and emit signal."""
            self.canceled.emit()


def force_elevated() -> None:
    """Force script to run with elevated privileges on Windows.
    
    Relaunches script with admin rights if not already elevated.
    """
    if platform.system() != "Windows":
        return

    shellconMod, shellMod, win32conMod, win32eventMod, win32processMod = getWin32ShellModules()
    if not all([shellconMod, shellMod, win32conMod, win32eventMod, win32processMod]):
        if _WIN32_SHELL_IMPORT_ERROR:
            print(_WIN32_SHELL_IMPORT_ERROR)
        return

    try:
        if sys.argv[-1] != "asadmin":
            script = os.path.abspath(sys.argv[0])
            params = " ".join(['"%s"' % script] + sys.argv[1:] + ["asadmin"])
            procInfo = shellMod.ShellExecuteEx(
                nShow=win32conMod.SW_SHOWNORMAL,
                fMask=shellconMod.SEE_MASK_NOCLOSEPROCESS,
                lpVerb="runas",
                lpFile=sys.executable,
                lpParameters=params,
            )

            procHandle = procInfo["hProcess"]
            win32eventMod.WaitForSingleObject(procHandle, win32eventMod.INFINITE)
            win32processMod.GetExitCodeProcess(procHandle)
    except Exception as ex:
        print(ex)


def startInstaller_Windows(silent: bool = False, setupShortcuts: bool = True, dccIntegrations: bool = True, createUninstaller: bool = False) -> None:
    """Start Prism installer on Windows.
    
    Args:
        silent (bool, optional): Run without UI. Defaults to False.
        setupShortcuts (bool, optional): Create startmenu shortcuts. Defaults to True.
        dccIntegrations (bool, optional): Install DCC integrations. Defaults to True.
        createUninstaller (bool, optional): Create uninstaller. Defaults to False.
    """
    import PrismCore
    pc = PrismCore.create()
    dlg = pc.openSetup(silent=silent)
    dlg.w_pageStart.chb_startmenu.setChecked(setupShortcuts)
    dlg.w_pageStart.chb_startmenu.setChecked(dccIntegrations)
    dlg.w_pageStart.chb_startmenu.setChecked(createUninstaller)
    if silent:
        dlg.run(silent=True)


def startUninstaller_Windows(silent: bool = False, removeCore: bool = True, removePlugins: bool = True, removeDccIntegrations: bool = True, removePreferences: bool = False) -> None:
    """Start Prism uninstaller on Windows.
    
    Args:
        silent (bool, optional): Run without UI. Defaults to False.
        removeCore (bool, optional): Remove core files. Defaults to True.
        removePlugins (bool, optional): Remove local plugins. Defaults to True.
        removeDccIntegrations (bool, optional): Remove DCC integrations. Defaults to True.
        removePreferences (bool, optional): Remove user preferences. Defaults to False.
    """
    qApp = QApplication.instance()
    wIcon = QIcon(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "UserInterfacesPrism",
            "p_tray.png",
        )
    )
    qApp.setWindowIcon(wIcon)

    from UserInterfacesPrism.stylesheets import blue_moon
    qApp.setStyleSheet(blue_moon.load_stylesheet(pyside=True))

    dlg = Uninstaller()
    dlg.chb_prism.setChecked(removeCore)
    dlg.chb_plugins.setChecked(removePlugins)
    dlg.chb_integrations.setChecked(removeDccIntegrations)
    dlg.chb_prefs.setChecked(removePreferences)
    if silent:
        dlg.run(silent=True)
    else:
        dlg.exec_()
        sys.exit()


def startInstaller_Linux() -> None:
    """Start Prism installer on Linux."""
    try:
        if not checkRootUser():
            return

        import PrismCore

        pc = PrismCore.PrismCore()
        if sys.argv[-1] == "uninstall":
            dlg = Uninstaller()
            dlg.exec_()
        else:
            pc.openSetup()

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        QMessageBox.warning(
            QWidget(),
            "Prism Installation",
            "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s"
            % (str(e), exc_type, exc_tb.tb_lineno),
        )


def startUninstaller_Linux() -> None:
    """Start Prism uninstaller on Linux."""
    try:
        if not checkRootUser():
            return

        dlg = Uninstaller()
        dlg.exec_()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        QMessageBox.warning(
            QWidget(),
            "Prism Installation",
            "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s"
            % (str(e), exc_type, exc_tb.tb_lineno),
        )


def startInstaller_Mac() -> None:
    """Start Prism installer on macOS."""
    try:
        if not checkRootUser():
            return

        import PrismCore

        pc = PrismCore.PrismCore()
        if sys.argv[-1] == "uninstall":
            dlg = Uninstaller()
            dlg.exec_()
        else:
            pc.openSetup()

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        QMessageBox.warning(
            QWidget(),
            "Prism Installation",
            "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s"
            % (str(e), exc_type, exc_tb.tb_lineno),
        )


def startUninstaller_Mac() -> None:
    """Start Prism uninstaller on macOS."""
    try:
        if not checkRootUser():
            return

        dlg = Uninstaller()
        dlg.exec_()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        QMessageBox.warning(
            QWidget(),
            "Prism Installation",
            "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s"
            % (str(e), exc_type, exc_tb.tb_lineno),
        )


def checkRootUser() -> bool:
    """Check if running as root user on Linux/Mac and show warning if appropriate.
    
    Returns:
        bool: True if root or user chooses to continue, False otherwise.
    """
    if os.getuid() != 0:
        warnStr = """The installer was not started as root user.

The additional permissions are required to:
- add Prism to the system autostart
- add Prism to the system startmenu
- add Prism integration for some DCCs

If you continue Prism will skip these features.
"""
        msg = QMessageBox(
            QMessageBox.Warning,
            "Prism Installation",
            warnStr,
            QMessageBox.NoButton,
        )
        msg.addButton("Continue", QMessageBox.YesRole)
        msg.addButton("Cancel", QMessageBox.YesRole)
        action = msg.exec_()

        if action == 0:
            os.environ["prism_skip_root_install"] = "1"
            return True
        elif action == 1:
            sys.exit()
            return

    return True


def install(silent: bool = False, setupShortcuts: bool = True, dccIntegrations: bool = True, createUninstaller: bool = False) -> None:
    """Platform-independent installer entry point.
    
    Args:
        silent (bool, optional): Run without UI. Defaults to False.
        setupShortcuts (bool, optional): Create shortcuts. Defaults to True.
        dccIntegrations (bool, optional): Install DCC integrations. Defaults to True.
        createUninstaller (bool, optional): Create uninstaller. Defaults to False.
    """
    if platform.system() == "Windows":
        startInstaller_Windows(
            silent=silent,
            setupShortcuts=setupShortcuts,
            dccIntegrations=dccIntegrations,
            createUninstaller=createUninstaller
        )
    elif platform.system() == "Linux":
        startInstaller_Linux()
    elif platform.system() == "Darwin":
        startInstaller_Mac()


def uninstall(silent: bool = False, removeCore: bool = True, removePlugins: bool = True, removeDccIntegrations: bool = True, removePreferences: bool = False) -> None:
    """Platform-independent uninstaller entry point.
    
    Args:
        silent (bool, optional): Run without UI. Defaults to False.
        removeCore (bool, optional): Remove core files. Defaults to True.
        removePlugins (bool, optional): Remove local plugins. Defaults to True.
        removeDccIntegrations (bool, optional): Remove DCC integrations. Defaults to True.
        removePreferences (bool, optional): Remove user preferences. Defaults to False.
    """
    if platform.system() == "Windows":
        startUninstaller_Windows(
            silent=silent,
            removeCore=removeCore,
            removePlugins=removePlugins,
            removeDccIntegrations=removeDccIntegrations,
            removePreferences=removePreferences
        )
    elif platform.system() == "Linux":
        startUninstaller_Linux()
    elif platform.system() == "Darwin":
        startUninstaller_Mac()


if __name__ == "__main__":
    qApp = QApplication(sys.argv)
    try:
        if len(sys.argv) >= 2 and "uninstall" in sys.argv:
            uninstall()
        else:
            install()

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        QMessageBox.warning(
            QWidget(),
            "Prism Installation",
            "Errors occurred.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno),
        )
    else:
        sys.exit(qApp.exec_())
