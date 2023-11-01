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

prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
scriptPath = os.path.join(prismRoot, "Scripts")
if scriptPath not in sys.path:
    sys.path.append(scriptPath)

if __name__ == "__main__":
    import PrismCore

if platform.system() == "Windows":
    from win32comext.shell import shellcon
    import win32comext.shell.shell as shell
    import win32con, win32event, win32process
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


class PrismSetup(QDialog):

    signalShowing = Signal()

    def __init__(self, core):
        QDialog.__init__(self)
        self.core = core
        self.loadLayout()
        self.connectEvents()
        self.setFocus()

    def loadLayout(self):
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

    def connectEvents(self):
        self.w_pageStart.signalNext.connect(self.nextClicked)
        self.w_pageStartmenu.signalNext.connect(self.nextClicked)
        self.w_pageIntegrations.signalNext.connect(self.nextClicked)
        self.w_pageFinished.signalBack.connect(self.backClicked)
        self.sw_main.currentChanged.connect(self.pageChanged)

    def backClicked(self):
        curIdx = self.sw_main.currentIndex()
        if curIdx == 0:
            return

        self.sw_main.setCurrentIndex(curIdx-1)

    def nextClicked(self):
        curIdx = self.sw_main.currentIndex()
        if curIdx == (self.sw_main.count() - 1):
            return

        self.sw_main.setCurrentIndex(curIdx+1)

    def showEvent(self, event):
        self.signalShowing.emit()
        self.activateWindow()
        self.raise_()

    def pageChanged(self, idx):
        self.sw_main.widget(idx).entered()


class Page_Start(QWidget):

    signalNext = Signal()

    def __init__(self, parent):
        super(Page_Start, self).__init__()
        self.setupUi()

    def setupUi(self):
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
        self.lo_options.addWidget(self.chb_startmenu)
        self.lo_options.addWidget(self.chb_integrations)

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

    signalNext = Signal()

    def __init__(self, parent):
        super(Page_Startmenu, self).__init__()
        self.parent = parent
        self.setupUi()

    def setupUi(self):
        self.lo_main = QVBoxLayout()
        self.lo_main.setContentsMargins(20, 50, 20, 20)
        self.l_header = QLabel("Creating startmenu. Please wait...")
        self.l_header.setAlignment(Qt.AlignHCenter)

        self.lo_main.addStretch()
        self.lo_main.addWidget(self.l_header)
        self.lo_main.addStretch()
        self.setLayout(self.lo_main)

    def entered(self):
        QApplication.processEvents()
        if self.parent.w_pageStart.chb_startmenu.isChecked():
            self.parent.core.setupStartMenu(quiet=True)
            self.l_header.setText("Creating uninstaller. Please wait...")
            QApplication.processEvents()
            self.parent.core.setupUninstaller(quiet=True)

        QApplication.processEvents()
        self.signalNext.emit()


class Page_Integrations(QWidget):

    signalNext = Signal()

    def __init__(self, parent):
        super(Page_Integrations, self).__init__()
        self.parent = parent
        self.setupUi()

    def setupUi(self):
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

    def skipClicked(self):
        self.signalNext.emit()

    def installClicked(self):
        core = self.parent.core
        core.uiAvailable = True
        self.w_integrations.install(successPopup=False)
        core.uiAvailable = False
        self.signalNext.emit()

    def entered(self):
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

    signalBack = Signal()
    signalNext = Signal()

    def __init__(self, parent):
        super(Page_Finished, self).__init__()
        self.parent = parent
        self.setupUi()

    def setupUi(self):
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

    def backClicked(self):
        self.signalBack.emit()

    def finish(self):
        if not self.chb_launchPrism.isHidden() and self.chb_launchPrism.isChecked():
            self.launchPrism()

        QDialog.accept(self.parent)

    def launchPrism(self):
        target = self.parent.core.prismRoot
        exe = os.path.join(target, self.parent.core.pythonVersion, "Prism.exe")
        script = os.path.join(target, "Scripts", "PrismTray.py")
        subprocess.Popen([exe, script, "projectBrowser"])

    def entered(self):
        if not self.parent.w_pageStart.chb_integrations.isChecked():
            self.b_back.setVisible(False)

        msg = "Prism %s was installed successfully!" % self.parent.core.version
        self.l_success.setText(msg)


class PrismInstaller(QDialog, PrismInstaller_ui.Ui_dlg_installer):
    def __init__(self, core, plugins=None):
        QDialog.__init__(self)
        self.core = core
        if not plugins:
            plugins = self.core.getPluginNames()

        self.plugins = {name: self.core.getPlugin(name) for name in plugins if name != "Standalone"}
        self.installShortcuts = True
        self.setupUi(self)
        try:
            if platform.system() == "Windows":
                self.documents = shell.SHGetFolderPath(
                    0, shellcon.CSIDL_PERSONAL, None, 0
                )

            self.tw_components.header().resizeSection(0, 200)
            self.tw_components.itemDoubleClicked.connect(self.openBrowse)

            self.refreshUI()

            self.buttonBox.button(QDialogButtonBox.Ok).setText("Install")
            self.buttonBox.accepted.connect(self.install)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = "Errors occurred during the installation.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno)
            self.core.popup(msg, parent=self)

    def openBrowse(self, item, column):
        if (
            item.parent() is not None
            and item.parent().text(0) != "DCC integrations"
            and item.text(0) not in ["Custom"]
            or item.childCount() > 0
        ):
            return

        startPath = item.text(column)
        if not os.path.exists(startPath):
            ttPath = item.toolTip(column).replace("e.g. ", "").strip("\"")
            if os.path.exists(ttPath):
                startPath = ttPath

        path = QFileDialog.getExistingDirectory(
            self, "Select destination folder", startPath
        )
        if path != "":
            path = os.path.normpath(path)
            item.setText(1, path)
            item.setToolTip(1, path)
            item.setCheckState(0, Qt.Checked)

    def CompItemClicked(self, item, column):
        if item.text(0) in ["DCC integrations"] or item.childCount == 0:
            return

        isEnabled = item.checkState(0) == Qt.Checked
        for i in range(item.childCount()):
            if isEnabled:
                if item.child(i).text(0) == "Custom" or item.child(i).text(1) != "":
                    item.child(i).setFlags(item.child(i).flags() | Qt.ItemIsEnabled)
            else:
                item.child(i).setFlags(item.child(i).flags() & ~Qt.ItemIsEnabled)

    def refreshUI(self):
        try:
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
            self.tw_components.itemClicked.connect(self.CompItemClicked)

            if len(self.plugins) > 0:
                integrationsItem = QTreeWidgetItem(["DCC integrations"])
                self.tw_components.addTopLevelItem(integrationsItem)

                for i in sorted(self.plugins):
                    if hasattr(self.plugins[i], "updateInstallerUI"):
                        self.plugins[i].updateInstallerUI(userFolders, integrationsItem)

                integrationsItem.setExpanded(True)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno)
            self.core.popup(msg, parent=self)
            return False

    def getEnteredIntegrations(self):
        dccItems = self.tw_components.findItems(
            "DCC integrations", Qt.MatchExactly | Qt.MatchRecursive
        )
        if len(dccItems) > 0:
            dccItem = dccItems[0]
        else:
            dccItem = None

        result = {}

        if dccItem is not None:
            for i in range(dccItem.childCount()):
                childItem = dccItem.child(i)
                if not childItem.text(0) in self.plugins:
                    continue

                if childItem.checkState(0) != Qt.Checked:
                    continue

                paths = []
                if childItem.childCount():
                    for i in range(childItem.childCount()):
                        cchildItem = childItem.child(i)
                        if cchildItem.checkState(0) == Qt.Checked and os.path.exists(cchildItem.text(1)):
                            paths.append(cchildItem.text(1))
                else:
                    if os.path.exists(childItem.text(1)):
                        paths.append(childItem.text(1))

                result[childItem.text(0)] = paths

        return result

    def install(self, patch=False, documents="", successPopup=True):
        try:
            # print "\n\nInstalling - please wait.."

            dccItems = self.tw_components.findItems(
                "DCC integrations", Qt.MatchExactly | Qt.MatchRecursive
            )
            if len(dccItems) > 0:
                dccItem = dccItems[0]
            else:
                dccItem = None

            result = {}

            if dccItem is not None:
                for i in range(dccItem.childCount()):
                    childItem = dccItem.child(i)
                    if not childItem.text(0) in self.plugins:
                        continue

                    self.plugins[childItem.text(0)].installerExecute(childItem, result)

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

    def closeEvent(self, event):
        event.accept()


class Uninstaller(QDialog):
    def __init__(self):
        super(Uninstaller, self).__init__()
        self.conn = None
        self.listener = None
        self.setupUi()

    @err_catcher(name=__name__)
    def setupUi(self):
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
    def onUninstallClicked(self):
        waitPopup = self.waitPopup(self, "Uninstalling. Please wait...", parent=self)
        with waitPopup:
            feedback = self.le_feedback.toPlainText()
            if feedback:
                text = "Sending feedback. Please wait..."
                waitPopup.msg.setText(text)
                QCoreApplication.processEvents()
                self.sendFeedback()

            postDeletePaths = []

            result = {}
            if self.chb_integrations.isChecked():
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
                text = "Removing plugins. Please wait..."
                waitPopup.msg.setText(text)
                QCoreApplication.processEvents()
                result["Local Plugins"] = self.removeLocalPlugins()

            if self.chb_prefs.isChecked():
                text = "Removing preferences. Please wait..."
                waitPopup.msg.setText(text)
                QCoreApplication.processEvents()
                result["Prism Preferences"] = self.removePrismPreferences()

            if self.chb_prism.isChecked():
                text = "Removing Prism. Please wait..."
                waitPopup.msg.setText(text)
                QCoreApplication.processEvents()
                result["Prism Files"] = self.removePrismFiles(postDeletePaths)

        if False not in result.values():
            msgStr = "Prism was uninstalled successfully."
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

            QMessageBox.warning(
                self, "Prism Installation", msgString
            )
            sys.exit(0)

    @err_catcher(name=__name__)
    def closeEvent(self, event):
        self.shutDownConnection()

    @err_catcher(name=__name__)
    def getPrismConnection(self):
        if not self.conn:
            address = ("localhost", 6551)
            from multiprocessing.connection import Listener
            self.listener = Listener(address, authkey=b'gfjdbfs')

            cmd = "import sys;sys.path.append('%s');import PrismCore;core = PrismCore.create();core.startCommunication(port=6550, key=b'gfjdbfs')" % os.path.dirname(__file__)
            subprocess.Popen([sys.executable, "-c", cmd])

            self.sconn = self.listener.accept()

            address = ('localhost', 6550)
            from multiprocessing.connection import Client
            self.conn = Client(address, authkey=b'gfjdbfs')

        return self.conn

    @err_catcher(name=__name__)
    def getAnswer(self):
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
    def shutDownConnection(self):
        if self.listener:
            self.listener.close()

        if self.conn:
            try:
                self.conn.send({"name": "close"})
            except Exception:
                pass

            self.conn.close()

    @err_catcher(name=__name__)
    def sendData(self, data):
        conn = self.getPrismConnection()
        conn.send(data)

    @err_catcher(name=__name__)
    def finalize(self, postDeletePaths):
        if postDeletePaths:
            cmd = "timeout /t 5 /nobreak > nul"
            for path in postDeletePaths:
                cmd += " & rmdir /S /Q \"%s\"" % path.replace("\\", "\\\\")
            
            import subprocess
            subprocess.Popen(cmd, shell=True)

        sys.exit(0)

    @err_catcher(name=__name__)
    def sendFeedback(self):
        feedback = self.le_feedback.toPlainText()
        feedback = "I'm uninstalling Prism because...\n\n" + feedback
        self.sendData({"name": "sendFeedback", "data": feedback})
        self.getAnswer()

    @err_catcher(name=__name__)
    def removeIntegrations(self):
        self.sendData({"name": "removeAllIntegrations"})
        answer = self.getAnswer()
        if not answer and answer != {}:
            answer = {"DCC Integrations": False}

        return answer

    @err_catcher(name=__name__)
    def removeLocalPlugins(self):
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
    def removePrismPreferences(self):
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
    def closePrismProcesses(self):
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
    def removePrismFiles(self, postDeletePaths):
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
    def removeWindowsSpecificData(self):
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
    def removeUninstallerFromWindowsRegistry(self):
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
    def removeLinuxSpecificData(self):
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
    def removeMacSpecificData(self):
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
        text,
        title=None,
        severity="warning",
        notShowAgain=False,
        parent=None,
        modal=True,
        widget=None,
        show=True,
    ):
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
        text,
        title=None,
        buttons=None,
        default=None,
        icon=None,
        widget=None,
        parent=None,
        escapeButton=None,
    ):
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
        text,
        title=None,
        buttons=None,
        default=None,
        icon=None,
        parent=None,
        show=True,
    ):
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
        """
        with self.core.waitPopup(self.core, text):

        """

        canceled = Signal()

        def __init__(
            self,
            core,
            text,
            title=None,
            buttons=None,
            default=None,
            icon=None,
            hidden=False,
            parent=None,
            allowCancel=False,
            activate=True,
        ):
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

        def __enter__(self):
            if not self.hidden:
                self.show()

        def __exit__(self, type, value, traceback):
            self.close()

        def createPopup(self):
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

        def show(self):
            self.createPopup()
            self.msg.show()
            QCoreApplication.processEvents()

        def exec_(self):
            self.createPopup()
            for button in self.msg.buttons():
                button.setVisible(self.allowCancel)

            #    if self.allowCancel:
            #        self.msg.canceled.connect(self.canceled)

            result = self.msg.exec_()
            if result:
                self.cancel()

        def close(self):
            if self.msg and self.msg.isVisible():
                self.msg.close()

        def cancel(self):
            self.canceled.emit()


def force_elevated():
    try:
        if sys.argv[-1] != "asadmin":
            script = os.path.abspath(sys.argv[0])
            params = " ".join(['"%s"' % script] + sys.argv[1:] + ["asadmin"])
            procInfo = shell.ShellExecuteEx(
                nShow=win32con.SW_SHOWNORMAL,
                fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                lpVerb="runas",
                lpFile=sys.executable,
                lpParameters=params,
            )

            procHandle = procInfo["hProcess"]
            obj = win32event.WaitForSingleObject(procHandle, win32event.INFINITE)
            rc = win32process.GetExitCodeProcess(procHandle)

    except Exception as ex:
        print(ex)


def startInstaller_Windows():
    if len(sys.argv) >= 2 and "uninstall" in sys.argv:
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
        dlg.exec_()
        sys.exit()
    else:
        import PrismCore
        pc = PrismCore.create()
        pc.openSetup()


def startInstaller_Linux():
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


def startInstaller_Mac():
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


def checkRootUser():
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


if __name__ == "__main__":
    qApp = QApplication(sys.argv)
    try:
        if platform.system() == "Windows":
            startInstaller_Windows()
        elif platform.system() == "Linux":
            startInstaller_Linux()
        elif platform.system() == "Darwin":
            startInstaller_Mac()

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        QMessageBox.warning(
            QWidget(),
            "Prism Installation",
            "Errors occurred.\n\n%s\n%s\n%s" % (str(e), exc_type, exc_tb.tb_lineno),
        )
    else:
        sys.exit(qApp.exec_())
