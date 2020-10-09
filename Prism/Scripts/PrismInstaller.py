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
# Copyright (C) 2016-2020 Richard Frangenberg
#
# Licensed under GNU GPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


import os
import sys
import shutil
import platform
import logging

if sys.version[0] == "3":
    pVersion = 3
    pyLibs = "Python37"
else:
    pVersion = 2
    pyLibs = "Python27"

prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
prismLibs = os.getenv("PRISM_LIBS")
if not prismLibs:
    prismLibs = prismRoot

scriptPath = os.path.join(prismRoot, "Scripts")
if scriptPath not in sys.path:
    sys.path.append(scriptPath)

sys.path.insert(0, os.path.join(prismLibs, "PythonLibs", pyLibs))
sys.path.insert(0, os.path.join(prismLibs, "PythonLibs", pyLibs, "win32"))
sys.path.insert(0, os.path.join(prismLibs, "PythonLibs", pyLibs, "win32", "lib"))
sys.path.insert(0, os.path.join(prismLibs, "PythonLibs", pyLibs, "PySide"))
sys.path.insert(0, os.path.join(scriptPath, "UserInterfacesPrism"))
os.environ['PATH'] = os.path.join(prismLibs, "PythonLibs", pyLibs, "pywin32_system32") + os.pathsep + os.environ['PATH']

if platform.system() == "Windows":
    from win32com.shell import shellcon
    import win32com.shell.shell as shell
    import win32con, win32event, win32process
else:
    import pwd

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1

if psVersion == 1:
    import PrismInstaller_ui
else:
    import PrismInstaller_ui_ps2 as PrismInstaller_ui

from UserInterfacesPrism import qdarkstyle

logger = logging.getLogger(__name__)
logging.basicConfig()
logging.root.setLevel("INFO")


class PrismInstaller(QDialog, PrismInstaller_ui.Ui_dlg_installer):
    def __init__(self, core, uninstall=False):
        QDialog.__init__(self)
        self.core = core
        pnames = self.core.getPluginNames()
        self.plugins = {x: self.core.getPlugin(x) for x in pnames if x != "Standalone"}

        if uninstall:
            self.uninstall()
        else:
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
                QMessageBox.warning(
                    QWidget(),
                    "Prism Integration",
                    "Errors occurred during the installation.\n\n%s\n%s\n%s"
                    % (str(e), exc_type, exc_tb.tb_lineno),
                )

        self.updatePrefPermissions()

    def openBrowse(self, item, column):
        if (
            item.parent() is not None
            and item.parent().text(0) != "DCC integrations"
            and item.text(0) not in ["Custom"]
            or item.childCount() > 0
        ):
            return

        path = QFileDialog.getExistingDirectory(
            QWidget(), "Select destination folder", item.text(column)
        )
        if path != "":
            item.setText(1, path)
            item.setToolTip(1, path)

    def CompItemClicked(self, item, column):
        if item.text(0) in ["DCC integrations"] or item.childCount == 0:
            return

        isEnabled = item.checkState(0) == Qt.Checked
        for i in range(item.childCount()):
            if isEnabled:
                if item.child(i).text(0) == "Custom" or item.child(i).text(1) != "":
                    item.child(i).setFlags(item.child(i).flags() | Qt.ItemIsEnabled)
            else:
                item.child(i).setFlags(~Qt.ItemIsEnabled)

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
                    self.plugins[i].updateInstallerUI(userFolders, integrationsItem)

                integrationsItem.setExpanded(True)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = QMessageBox.warning(
                QWidget(),
                "Prism Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno),
            )
            return False

    def install(self, patch=False, documents=""):
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

                    self.plugins[childItem.text(0)].installerExecute(
                        childItem, result
                    )

            if not os.environ.get("prism_skip_root_install"):
                self.core.setupStartMenu(quiet=True)

            if platform.system() != "Windows":
                self.updatePrefPermissions()

            # print "Finished"

            if not False in result.values():
                QMessageBox.information(
                    self.core.messageParent,
                    "Prism Installation",
                    "Prism was installed successfully.",
                )
            else:
                msgString = "Some parts failed to install:\n\n"
                for i in result:
                    msgString += "%s:\t\t%s\t\t\n\n" % (i, result[i])

                msgString = msgString.replace("True", "Success").replace(
                    "False", "Error"
                )

                QMessageBox.warning(
                    self.core.messageParent, "Prism Installation", msgString
                )

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = QMessageBox(
                QMessageBox.Warning,
                "Prism Installation",
                "Errors occurred during the installation.\n The installation is possibly incomplete.\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno),
                QMessageBox.Ok,
            )
            msg.setFocus()
            msg.exec_()
            return False

    def updatePrefPermissions(self):
        if platform.system() == "Windows":
            return

        userName = (
            os.environ["SUDO_USER"]
            if "SUDO_USER" in os.environ
            else os.environ["USER"]
        )
        uid = pwd.getpwnam(userName).pw_uid
        prefPath = os.path.dirname(self.core.integration.installLocPath)
        if os.path.exists(prefPath):
            os.chown(prefPath, uid, -1)
            for root, dirs, files in os.walk(prefPath):
                for d in (dirs+files):
                    path = os.path.join(root, d)
                    os.chown(path, uid, -1)

    def closeEvent(self, event):
        self.updatePrefPermissions()
        event.accept()

    def uninstall(self):
        msg = QMessageBox(
            QMessageBox.Question,
            "Prism Pipeline",
            "Are you sure you want to uninstall Prism?\n\nThis will delete all Prism integrations from your PC. Your projects will remain unaffected.",
            QMessageBox.Cancel,
            parent=self.core.messageParent,
        )
        msg.addButton("Continue", QMessageBox.YesRole)
        action = msg.exec_()

        if action != 0:
            return False

        # print "uninstalling..."

        result = self.core.integration.removeAllIntegrations()
        result["Prism Files"] = self.removePrismFiles()

        if not False in result.values():
            msgStr = (
                "All Prism integrations were removed successfully. To finish the uninstallation delete the Prism folder:\n\n%s"
                % self.core.prismRoot
            )
            QMessageBox.information(
                self.core.messageParent, "Prism Uninstallation", msgStr
            )
        else:
            msgString = "Some parts failed to uninstall:\n\n"
            for i in result:
                msgString += "%s:\t\t%s\t\t\n\n" % (i, result[i])

            msgString = (
                msgString.replace("True", "Success")
                .replace("False", "Error")
                .replace("Prism Files:", "Prism Files:\t")
            )

            QMessageBox.warning(
                self.core.messageParent, "Prism Installation", msgString
            )
            sys.exit()

    def removePrismFiles(self):
        try:
            try:
                import psutil
            except:
                pass
            else:
                PROCNAMES = [
                    "Prism Tray.exe",
                    "Prism Project Browser.exe",
                    "Prism Settings.exe",
                ]
                for proc in psutil.process_iter():
                    if proc.name() in PROCNAMES:
                        p = psutil.Process(proc.pid)

                        try:
                            if not "SYSTEM" in p.username():
                                try:
                                    proc.kill()
                                    # print "closed Prism process"
                                except:
                                    pass
                        except:
                            pass

            if platform.system() == "Windows":
                smTray = os.path.join(
                    os.environ["appdata"],
                    "Microsoft",
                    "Windows",
                    "Start Menu",
                    "Programs",
                    "Prism",
                    "Prism Tray.lnk",
                )
                smBrowser = os.path.join(
                    os.environ["appdata"],
                    "Microsoft",
                    "Windows",
                    "Start Menu",
                    "Programs",
                    "Prism",
                    "Prism Project Browser.lnk",
                )
                smSettings = os.path.join(
                    os.environ["appdata"],
                    "Microsoft",
                    "Windows",
                    "Start Menu",
                    "Programs",
                    "Prism",
                    "Prism Settings.lnk",
                )
                suTray = os.path.join(
                    os.environ["appdata"],
                    "Microsoft",
                    "Windows",
                    "Start Menu",
                    "Programs",
                    "Startup",
                    "Prism Tray.lnk",
                )

                pFiles = [smTray, smBrowser, smSettings, suTray]
            elif platform.system() == "Linux":
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

            elif platform.system() == "Darwin":
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

            for i in pFiles:
                if os.path.exists(i):
                    try:
                        os.remove(i)
                    except:
                        pass

            if platform.system() == "Windows":
                smFolder = os.path.dirname(smTray)
                try:
                    shutil.rmtree(smFolder)
                except:
                    pass

            return True

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            QMessageBox.warning(
                QWidget(),
                "Prism Installation",
                "Error occurred during Prism files removal:\n\n%s\n%s\n%s"
                % (str(e), exc_type, exc_tb.tb_lineno),
            )
            return False


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
    if sys.argv[-1] != "asadmin":
        force_elevated()
        sys.exit()
    else:
        import PrismCore

        pc = PrismCore.PrismCore()
        if sys.argv[-2] == "uninstall":
            pc.openInstaller(uninstall=True)
        else:
            pc.openInstaller()


def startInstaller_Linux():
    try:
        if not checkRootUser():
            return

        import PrismCore

        pc = PrismCore.PrismCore()
        if sys.argv[-1] == "uninstall":
            pc.openInstaller(uninstall=True)
        else:
            pc.openInstaller()

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
            pc.openInstaller(uninstall=True)
        else:
            pc.openInstaller()

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
        wIcon = QIcon(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "UserInterfacesPrism",
                "p_tray.png",
            )
        )
        qApp.setWindowIcon(wIcon)
        qApp.setStyleSheet(qdarkstyle.load_stylesheet(pyside=True))

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
