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
import traceback
import time
import platform
import subprocess
import datetime
import shutil
from functools import wraps
from collections import OrderedDict

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

    psVersion = 2
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

    psVersion = 1


class Updater(object):
    def __init__(self, core):
        super(Updater, self).__init__()
        self.core = core

    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            exc_info = sys.exc_info()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = "%s ERROR - Screenshot %s:\n%s\n\n%s" % (
                    time.strftime("%d/%m/%y %X"),
                    args[0].core.version,
                    "".join(traceback.format_stack()),
                    traceback.format_exc(),
                )
                args[0].core.writeErrorLog(erStr)

        return func_wrapper

    @err_decorator
    def startup(self):
        prevVersion = self.core.getConfig("globals", "prism_version")
        if prevVersion != self.core.version:
            self.core.setConfig("globals", "prism_version", self.core.version)
            if prevVersion:
                self.showChangelog()

        self.autoUpdateCheck()

    @err_decorator
    def updateFromZip(self):
        pZip = QFileDialog.getOpenFileName(
            QWidget(), "Select Prism Zip", self.core.prismRoot, "ZIP (*.zip)"
        )[0]

        if pZip != "":
            self.updatePrism(filepath=pZip)

    @err_decorator
    def autoUpdateCheck(self):
        updateInterval = self.core.getConfig(cat="globals", param="checkForUpdates")
        if updateInterval == "False" or updateInterval == -1:
            return

        if updateInterval == "True" or updateInterval is None:
            updateInterval = 7
        else:
            updateInterval = int(updateInterval)

        if updateInterval > 0:
            lastUpdateCheck = self.core.getConfig(cat="globals", param="lastUpdateCheck")
            if lastUpdateCheck:
                lastCheckSecs = (datetime.datetime.now() - datetime.datetime.strptime(lastUpdateCheck, "%Y-%m-%d %H:%M:%S.%f")).total_seconds()
                if lastCheckSecs < (60 * 60 * 24 * updateInterval):
                    return

        self.checkForUpdates(silent=True)

    @err_decorator
    def checkForUpdates(self, silent=False):
        pStr = """
try:
    import os, sys

    pyLibs = os.path.join('%s', 'PythonLibs', 'Python27')
    if pyLibs not in sys.path:
        sys.path.insert(0, pyLibs)

    pyLibs = os.path.join('%s', 'PythonLibs', 'CrossPlatform')
    if pyLibs not in sys.path:
        sys.path.insert(0, pyLibs)

    import requests
    page = requests.get('https://raw.githubusercontent.com/RichardFrangenberg/Prism/development/Prism/Scripts/PrismCore.py', verify=False)

    cStr = page.content
    lines = cStr.split('\\n')
    latestVersionStr = libVersionStr = ''
    for line in lines:
        if not latestVersionStr and 'self.version =' in line:
            latestVersionStr = line[line.find('\\"')+2:-1]

        if not libVersionStr and 'self.requiredLibraries =' in line:
            libVersionStr = line[line.find('\\"')+1:-1]

        if latestVersionStr and libVersionStr:
            break

    sys.stdout.write(latestVersionStr + '__' + libVersionStr)

except Exception as e:
    sys.stdout.write('failed %%s' %% e)
""" % (
            self.core.prismRoot,
            self.core.prismRoot,
        )

        if platform.system() == "Windows":
            pythonPath = os.path.join(self.core.prismRoot, "Python27", "pythonw.exe")
        else:
            pythonPath = "python"

        result = subprocess.Popen(
            [pythonPath, "-c", pStr],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdOutData, stderrdata = result.communicate()

        if "failed" in str(stdOutData) or len(str(stdOutData).split("__")) < 2:
            if not silent:
                QMessageBox.information(
                    self.core.messageParent,
                    "Prism",
                    "Unable to read https://raw.githubusercontent.com/RichardFrangenberg/Prism/development/Prism/Scripts/PrismCore.py. Could not check for updates.\n\n(%s)"
                    % stdOutData,
                )
            return

        if pVersion == 3:
            stdOutData = stdOutData.decode("utf-8")

        updateStatus = "latest version installed"

        latestVersion = stdOutData.split("__")[0]
        libVersion = stdOutData.split("__")[1] or "v1.2.0.0"

        curLibVersion = "v1.2.0.0"
        libConfig = os.path.join(self.core.prismRoot, "PythonLibs", "libraries.yml")
        if os.path.exists(libConfig):
            libInfo = self.core.readYaml(libConfig)
            if "version" in libInfo:
                curLibVersion = libInfo["version"]

        if curLibVersion != libVersion:
            self.core.popup("The version of the currently installed Prism libraries (%s) doesn't match the required version of the latest Prism version (%s). Please download the latest installer from the Prism website to update the Prism libraries." % (curLibVersion, libVersion))
            updateStatus = "update available: %s" % latestVersion
        else:
            if self.core.compareVersions(self.core.version, latestVersion) == "lower":
                msg = QDialog()
                msg.setWindowTitle("Prism")
                msg.setLayout(QVBoxLayout())
                msg.layout().addWidget(QLabel("A newer version of Prism is available:\n"))
                self.core.parentWindow(msg)

                bb_update = QDialogButtonBox()
                bb_update.addButton("Ignore", QDialogButtonBox.RejectRole)
                bb_update.addButton("Update Prism", QDialogButtonBox.AcceptRole)
                bb_update.accepted.connect(msg.accept)
                bb_update.rejected.connect(msg.reject)

                lo_version = QGridLayout()
                l_curVersion = QLabel(self.core.version)
                l_latestVersion = QLabel("v" + latestVersion)
                l_curVersion.setAlignment(Qt.AlignRight)
                l_latestVersion.setAlignment(Qt.AlignRight)

                lo_version.addWidget(QLabel("Installed version:"), 0, 0)
                lo_version.addWidget(l_curVersion, 0, 1)

                lo_version.addWidget(QLabel("Latest version:\n"), 1, 0)
                lo_version.addWidget(l_latestVersion, 1, 1)

                msg.layout().addLayout(lo_version)

                msg.layout().addWidget(bb_update)
                msg.resize(300 * self.core.uiScaleFactor, 10)
                action = msg.exec_()

                if action:
                    self.updatePrism(source="github")
                else:
                    updateStatus = "update available: %s" % latestVersion

            else:
                if not silent:
                    QMessageBox.information(
                        self.core.messageParent,
                        "Prism",
                        "The latest version of Prism is already installed. (%s)"
                        % self.core.version,
                    )

        self.core.setConfig(
            cat="globals",
            param="update_status",
            val=updateStatus,
        )

        self.core.setConfig(
            cat="globals",
            param="lastUpdateCheck",
            val=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        )

    @err_decorator
    def updatePrism(self, filepath="", source=""):
        if platform.system() == "Windows":
            targetdir = os.path.join(os.environ["temp"], "PrismUpdate")
        else:
            targetdir = "/tmp/PrismUpdate"

        if os.path.exists(targetdir):
            try:
                shutil.rmtree(
                    targetdir, ignore_errors=False, onerror=self.core.handleRemoveReadonly
                )
            except:
                QMessageBox.warning(
                    self.core.messageParent,
                    "Prism update",
                    "Could not remove temp directory:\n%s" % targetdir,
                )
                return

        if source == "github":
            waitmsg = QMessageBox(
                QMessageBox.NoIcon,
                "Prism update",
                "Downloading Prism - please wait..",
                QMessageBox.Cancel,
            )
            self.core.parentWindow(waitmsg)
            for i in waitmsg.buttons():
                i.setVisible(False)
            waitmsg.show()
            QCoreApplication.processEvents()

            url = "https://api.github.com/repos/RichardFrangenberg/Prism/zipball"

            try:
                import ssl

                if pVersion == 2:
                    import urllib

                    u = urllib.urlopen(url, context=ssl._create_unverified_context())
                else:
                    import urllib.request

                    u = urllib.request.urlopen(
                        url, context=ssl._create_unverified_context()
                    )
            except Exception as e:
                if "waitmsg" in locals() and waitmsg.isVisible():
                    waitmsg.close()

                QMessageBox.warning(
                    self.core.messageParent,
                    "Prism update",
                    "Could not connect to github:\n%s" % str(e),
                )
                return

            data = u.read()
            u.close()
            filepath = os.path.join(targetdir, "Prism_update.zip")
            if not os.path.exists(os.path.dirname(filepath)):
                os.makedirs(os.path.dirname(filepath))

            with open(filepath, "wb") as f:
                f.write(data)

            if "waitmsg" in locals() and waitmsg.isVisible():
                waitmsg.close()

        if not os.path.exists(filepath):
            return

        import zipfile

        waitmsg = QMessageBox(
            QMessageBox.NoIcon,
            "Prism update",
            "Extracting - please wait..",
            QMessageBox.Cancel,
        )
        self.core.parentWindow(waitmsg)
        for i in waitmsg.buttons():
            i.setVisible(False)
        waitmsg.show()
        QCoreApplication.processEvents()

        with zipfile.ZipFile(filepath, "r") as zip_ref:
            zip_ref.extractall(targetdir)

        for i in os.walk(targetdir):
            dirs = i[1]
            break

        updateRoot = os.path.join(targetdir, dirs[0], "Prism")

        if "waitmsg" in locals() and waitmsg.isVisible():
            waitmsg.close()

        msgText = "Are you sure you want to continue?\n\nThis will overwrite existing files in your Prism installation folder."
        if psVersion == 1:
            flags = QMessageBox.StandardButton.Yes
            flags |= QMessageBox.StandardButton.No
            result = QMessageBox.question(
                self.core.messageParent, "Prism update", msgText, flags
            )
        else:
            result = QMessageBox.question(self.core.messageParent, "Prism update", msgText)

        if not str(result).endswith(".Yes"):
            return

        for i in os.walk(updateRoot):
            for k in i[2]:
                filepath = os.path.join(i[0], k)
                if not os.path.exists(i[0].replace(updateRoot, self.core.prismRoot)):
                    os.makedirs(i[0].replace(updateRoot, self.core.prismRoot))

                target = filepath.replace(updateRoot, self.core.prismRoot)
                try:
                    shutil.copy2(filepath, target)
                except IOError:
                    self.core.popup("Unable to copy file to:\n\n%s\n\nMake sure you have write access to this location. \
If admin privileges are required for this location launch Prism as admin before you start the update process \
or move Prism to a location where no admin privileges are required." % target)
                    return
                if os.path.splitext(filepath)[1] in [".command", ".sh"]:
                    os.chmod(filepath.replace(updateRoot, self.core.prismRoot), 0o777)

        if os.path.exists(targetdir):
            shutil.rmtree(
                targetdir, ignore_errors=False, onerror=self.core.handleRemoveReadonly
            )

        try:
            import psutil
        except:
            pass
        else:
            PROCNAMES = [
                "PrismTray.exe",
                "PrismProjectBrowser.exe",
                "PrismSettings.exe",
            ]
            for proc in psutil.process_iter():
                try:
                    if proc.name() in PROCNAMES:
                        if proc.pid == os.getpid():
                            continue

                        p = psutil.Process(proc.pid)

                        try:
                            if not "SYSTEM" in p.username():
                                try:
                                    proc.kill()
                                except:
                                    pass
                        except:
                            pass
                except:
                    pass

        msgStr = "Successfully updated Prism"
        if self.core.appPlugin.pluginName == "Standalone":
            msgStr += "\n\nPrism will now close. Please restart all your currently open DCC apps."
        else:
            msgStr += (
                "\nPlease restart %s in order to reload Prism."
                % self.core.appPlugin.pluginName
            )

        QMessageBox.information(self.core.messageParent, "Prism update", msgStr)

        trayPath = os.path.join(self.core.prismRoot, "Tools", "PrismTray.lnk")
        if os.path.exists(trayPath):
            subprocess.Popen([trayPath], shell=True)

        if self.core.appPlugin.pluginName == "Standalone":
            sys.exit()

    @err_decorator
    def showChangelog(self):
        self.changelogStr = self.getChangelog()
        if not self.changelogStr:
            return

        self.dlg_changelog = QDialog()
        self.dlg_changelog.setWindowTitle("Prism changelog")

        l_changelog = QLabel(self.changelogStr)
        l_changelog.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lo_changelog = QVBoxLayout()
        lo_scrollArea = QVBoxLayout()

        self.dlg_changelog.setLayout(lo_changelog)

        sa_changelog = QScrollArea()
        w_scrollArea = QWidget()
        e_search = QLineEdit()

        w_scrollArea.setLayout(lo_scrollArea)
        lo_scrollArea.addWidget(e_search)
        lo_scrollArea.addWidget(l_changelog)
        lo_scrollArea.addStretch()
        sa_changelog.setWidget(w_scrollArea)
        lo_changelog.addWidget(sa_changelog)

        if psVersion == 2:
            e_search.setClearButtonEnabled(True)

        e_search.setPlaceholderText("Search...")
        e_search.textChanged.connect(lambda x: self.refreshChangelog(l_changelog, e_search.text()))
        e_search.setFocus()
        sa_changelog.setWidgetResizable(True)

        self.core.parentWindow(self.dlg_changelog)
        self.dlg_changelog.resize(1000 * self.core.uiScaleFactor, 800 * self.core.uiScaleFactor)
        self.dlg_changelog.exec_()

    @err_decorator
    def refreshChangelog(self, l_changelog, filterStr):
        text = self.changelogStr
        if filterStr:
            lines = text.split("\n")
            filteredLines = OrderedDict()
            versionLine = ""
            for line in lines:
                if not line or line == "\r":
                    continue

                if line[0] == "v" and line[-2] == ":":
                    versionLine = line
                    filteredLines[versionLine] = []
                    continue

                if filterStr.lower() in line.lower():
                    filteredLines[versionLine].append(line)

            text = ""
            for version in filteredLines:
                if not filteredLines[version]:
                    continue

                text += version + "\n".join(filteredLines[version]) + "\n\n"

        l_changelog.setText(text)

    @err_decorator
    def getChangelog(self, silent=False):
        pStr = """
try:
    import os, sys

    pyLibs = os.path.join('%s', 'PythonLibs', 'Python27')
    if pyLibs not in sys.path:
        sys.path.insert(0, pyLibs)

    pyLibs = os.path.join('%s', 'PythonLibs', 'CrossPlatform')
    if pyLibs not in sys.path:
        sys.path.insert(0, pyLibs)

    import requests
    page = requests.get('https://raw.githubusercontent.com/RichardFrangenberg/Prism/development/changelog.txt', verify=False)

    sys.stdout.write(page.content)

except Exception as e:
    sys.stdout.write('failed %%s' %% e)
""" % (
            self.core.prismRoot,
            self.core.prismRoot,
        )

        if platform.system() == "Windows":
            pythonPath = os.path.join(self.core.prismRoot, "Python27", "pythonw.exe")
        else:
            pythonPath = "python"

        result = subprocess.Popen(
            [pythonPath, "-c", pStr],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdOutData, stderrdata = result.communicate()

        if "failed" in str(stdOutData) or len(str(stdOutData).split(".")) < 4:
            if not silent:
                QMessageBox.information(
                    self.core.messageParent,
                    "Prism",
                    "Unable to read https://raw.githubusercontent.com/RichardFrangenberg/Prism/development/changelog.txt. Could not get changelog.\n\n(%s)"
                    % stdOutData,
                )
            return

        if pVersion == 3:
            stdOutData = stdOutData.decode("utf-8")

        return stdOutData
