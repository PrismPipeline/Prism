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
import logging
import platform
import subprocess
import datetime
import shutil
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

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class Updater(object):
    def __init__(self, core):
        super(Updater, self).__init__()
        self.core = core
        self.showChangelogWarnOnError = True
        self.autoUpdateCheckEnabled = True

    @err_catcher(name=__name__)
    def startup(self):
        if not self.autoUpdateCheckEnabled:
            return

        prevVersion = self.core.getConfig("globals", "prism_version")
        if prevVersion != self.core.version:
            self.core.setConfig("globals", "prism_version", self.core.version)
            if prevVersion:
                self.showChangelog()

        self.autoUpdateCheck()

    @err_catcher(name=__name__)
    def updateFromZip(self):
        pZip = QFileDialog.getOpenFileName(
            QWidget(), "Select Prism Zip", self.core.prismRoot, "ZIP (*.zip)"
        )[0]

        if pZip != "":
            self.updatePrism(filepath=pZip)

    @err_catcher(name=__name__)
    def autoUpdateCheck(self):
        updateInterval = self.core.getConfig(cat="globals", param="checkForUpdates", dft=7)
        if updateInterval is False or updateInterval == -1:
            return

        if updateInterval is True or updateInterval is None:
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

    @err_catcher(name=__name__)
    def checkForUpdates(self, silent=False):
        logger.debug("checking for updates")
        url = "https://raw.githubusercontent.com/RichardFrangenberg/Prism/development/Prism/Scripts/PrismCore.py"
        result = self.getPrismVersionFromGithub(url)

        if not result:
            if not silent:
                msg = "Unable to read https://raw.githubusercontent.com/RichardFrangenberg/Prism/development/Prism/Scripts/PrismCore.py. Could not check for updates."
                self.core.popup(msg)
            self.core.setConfig(
                cat="globals",
                param="update_status",
                val="unknown status",
            )
            return

        updateStatus = "latest version installed"

        latestVersion = result[0]
        libVersion = result[1]

        curVersion = self.core.version
        curLibVersion = "v1.3.0.0"
        libConfig = os.path.join(self.core.prismLibs, "PythonLibs", "libraries.yml")
        if os.path.exists(libConfig):
            libInfo = self.core.readYaml(libConfig)
            if "version" in libInfo:
                curLibVersion = libInfo["version"]

        versionComp = self.core.compareVersions(curVersion, latestVersion)
        updatePossible = True
        if versionComp == "lower":
            if curLibVersion != libVersion:
                self.core.popup("The version of the currently installed Prism libraries (%s) doesn't match the required version of the latest Prism version (%s). Please download the latest installer from the Prism website to update the Prism libraries." % (curLibVersion, libVersion))
                updateStatus = "update available: %s" % latestVersion
                updatePossible = False
        else:
            if silent:
                updatePossible = False

        if updatePossible:
            dlg_update = self.getUpdateDialog(installedVersion=curVersion, latestVersion=latestVersion)
            action = dlg_update.exec_()

            if action:
                self.updatePrism(source="github")
            elif versionComp == "lower":
                updateStatus = "update available: %s" % latestVersion

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

    @err_catcher(name=__name__)
    def getUpdateDialog(self, installedVersion="", latestVersion=""):
        versionComp = self.core.compareVersions(installedVersion, latestVersion)
        if versionComp == "lower":
            title = "A newer version of Prism is available:\n"
        elif versionComp == "higher":
            title = "The installed Prism version in newer than the latest available version:\n"
        elif versionComp == "equal":
            title = "The latest version of Prism is already installed:\n"

        msg = QDialog()
        msg.setWindowTitle("Prism")
        msg.setLayout(QVBoxLayout())
        msg.l_title = QLabel(title)
        msg.layout().addWidget(msg.l_title)
        self.core.parentWindow(msg)

        bb_update = QDialogButtonBox()
        bb_update.addButton("Close", QDialogButtonBox.RejectRole)
        bb_update.addButton("Update Prism", QDialogButtonBox.AcceptRole)
        bb_update.accepted.connect(msg.accept)
        bb_update.rejected.connect(msg.reject)

        lo_version = QGridLayout()
        l_curVersion = QLabel(installedVersion)
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
        return msg

    @err_catcher(name=__name__)
    def updatePrism(self, filepath="", source="", url=None, token=None):
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
                msg = "Could not remove temp directory:\n%s" % targetdir
                self.core.popup(msg)
                return

        if source == "github":
            filepath = os.path.join(targetdir, "Prism_update.zip")
            self.downloadZipFromGithub(filepath, url=url, token=token)

        if not os.path.exists(filepath):
            return

        self.extractZip(filepath, targetdir)

        for i in os.walk(targetdir):
            dirs = i[1]
            break

        if not dirs:
            self.core.popup("Failed to extract Prism update archive")
            return

        updateRoot = os.path.join(targetdir, dirs[0], "Prism")

        msgText = "Are you sure you want to continue?\n\nThis will overwrite existing files in your Prism installation folder."
        result = self.core.popupQuestion(msgText, default="Yes")

        if result != "Yes":
            return

        self.updatePrismFromFolder(updateRoot)

        if os.path.exists(targetdir):
            shutil.rmtree(
                targetdir, ignore_errors=False, onerror=self.core.handleRemoveReadonly
            )

        self.restartPrism()

    @err_catcher(name=__name__)
    def getDataFromGithub(self, url, token=None):
        result = {
            "success": False,
            "data": None,
            "msg": "",
        }

        try:
            import ssl

            if pVersion == 2:
                from urllib2 import Request, urlopen
            else:
                from urllib.request import Request, urlopen

            if token:
                request = Request(url)
                request.add_header('Authorization', 'token %s' % token)
            else:
                request = url

            try:
                u = urlopen(request, context=ssl._create_unverified_context())
            except:
                u = urlopen(request)

        except Exception as e:
            msg = "Could not connect to github:\n%s" % str(e)
            result["msg"] = msg
            return result

        data = u.read()
        u.close()

        result["success"] = True
        result["data"] = data
        return result

    @err_catcher(name=__name__)
    def getPrismVersionFromGithub(self, url, token=""):
        pStr = """
try:
    import os
    import sys
    import traceback

    pyLibs = os.path.join('%s', 'PythonLibs', 'Python37')
    if pyLibs not in sys.path:
        sys.path.insert(0, pyLibs)

    pyLibs = os.path.join('%s', 'PythonLibs', 'CrossPlatform')
    if pyLibs not in sys.path:
        sys.path.insert(0, pyLibs)

    import ssl
    if sys.version[0] == "3":
        from urllib.request import Request, urlopen
    else:
        from urllib2 import Request, urlopen

    url = "%s"
    token = "%s"

    if token:
        request = Request(url)
        request.add_header('Authorization', 'token ' + token)
    else:
        request = url

    try:
        u = urlopen(request, context=ssl._create_unverified_context())
    except:
        u = urlopen(request)

    data = u.read().decode("utf-8")
    u.close()

    lines = data.split('\\n')
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
    sys.stdout.write('failed %%s' %% traceback.format_exc())
""" % (
            self.core.prismLibs,
            self.core.prismLibs,
            url,
            token,
        )
        pythonPath = self.core.getPythonPath()

        result = subprocess.Popen(
            [pythonPath, "-c", pStr],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdOutData, stderrdata = result.communicate()

        if "failed" in str(stdOutData) or len(str(stdOutData).split("__")) < 2:
            logger.warning("failed to get Prism version: %s" % stdOutData)
            return

        if pVersion == 3:
            stdOutData = stdOutData.decode("utf-8")

        latestVersion = stdOutData.split("__")[0]
        libVersion = stdOutData.split("__")[1] or "v1.3.0.0"
        return latestVersion, libVersion

    @err_catcher(name=__name__)
    def getGithubApiUrl(self, url, branch=""):
        if url[-1] in ["/", "\\"]:
            url = url[:-1]

        user = os.path.basename(os.path.dirname(url))
        repo = os.path.basename(url)
        apiUrl = 'https://api.github.com/repos/{user}/{repo}/zipball/{branch}'.format(user=user, repo=repo, branch=branch)
        return apiUrl

    @err_catcher(name=__name__)
    def downloadZipFromGithub(self, filepath, url=None, token=None):
        title = "Prism update"
        text = "Downloading Prism - please wait.."
        waitmsg = self.core.popupNoButton(text, title)

        url = url or "https://api.github.com/repos/RichardFrangenberg/Prism/zipball"
        result = self.getDataFromGithub(url, token=token)

        if not result["success"]:
            if waitmsg and waitmsg.isVisible():
                waitmsg.close()
            self.core.popup(result["msg"])
            return

        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))

        with open(filepath, "wb") as f:
            f.write(result["data"])

        if waitmsg and waitmsg.isVisible():
            waitmsg.close()

    @err_catcher(name=__name__)
    def extractZip(self, zippath, targetdir):
        import zipfile

        title = "Prism update"
        text = "Extracting - please wait.."
        waitmsg = self.core.popupNoButton(text, title)

        with zipfile.ZipFile(zippath, "r") as zip_ref:
            zip_ref.extractall(targetdir)

        if waitmsg and waitmsg.isVisible():
            waitmsg.close()

    @err_catcher(name=__name__)
    def updatePrismFromFolder(self, path):
        updateRoot = path
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

    @err_catcher(name=__name__)
    def restartPrism(self):
        try:
            import psutil
        except:
            logger.warning("couldn't load psutil")
        else:
            PROCNAMES = [
                "Prism Tray.exe",
                "Prism Project Browser.exe",
                "Prism Settings.exe",
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
                                    logger.warning("couldn't kill process %s" % proc.name())
                        except:
                            pass
                except:
                    pass

        corePath = os.path.join(self.core.prismRoot, "Scripts", "PrismCore.py")
        pythonPath = self.core.getPythonPath()

        result = subprocess.Popen(
            [pythonPath, corePath, "silent", "refreshIntegrations"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdOutData, stderrdata = result.communicate()

        self.core.restartRequired = True
        msgStr = "Successfully updated Prism"
        if self.core.appPlugin.pluginName == "Standalone":
            msgStr += "\n\nPrism will now close. Please restart all your currently open DCC apps."
        else:
            msgStr += (
                "\nPlease restart %s in order to reload Prism."
                % self.core.appPlugin.pluginName
            )

        self.core.popup(msgStr, severity="info")

        trayPath = os.path.join(self.core.prismLibs, "Tools", "Prism Tray.lnk")
        if os.path.exists(trayPath):
            subprocess.Popen([trayPath], shell=True)

        if self.core.appPlugin.pluginName == "Standalone":
            sys.exit()

    @err_catcher(name=__name__)
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

    @err_catcher(name=__name__)
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

    @err_catcher(name=__name__)
    def getChangelog(self, silent=False):
        pStr = """
try:
    import os, sys

    pyLibs = os.path.join('%s', 'PythonLibs', 'Python37')
    if pyLibs not in sys.path:
        sys.path.insert(0, pyLibs)

    pyLibs = os.path.join('%s', 'PythonLibs', 'CrossPlatform')
    if pyLibs not in sys.path:
        sys.path.insert(0, pyLibs)

    import requests
    page = requests.get('https://raw.githubusercontent.com/RichardFrangenberg/Prism/development/changelog.txt', verify=False)

    sys.stdout.write(page.content.decode("utf-8"))

except Exception as e:
    sys.stdout.write('failed %%s' %% e)
""" % (
            self.core.prismLibs,
            self.core.prismLibs,
        )

        pythonPath = self.core.getPythonPath()

        result = subprocess.Popen(
            [pythonPath, "-c", pStr],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdOutData, stderrdata = result.communicate()

        if pVersion == 3:
            stdOutData = stdOutData.decode("utf-8")

        if str(stdOutData).startswith("failed"):
            if not silent and self.showChangelogWarnOnError:
                msg = "Unable to read https://raw.githubusercontent.com/RichardFrangenberg/Prism/development/changelog.txt. Could not get changelog.\n\n(%s)" % stdOutData
                self.core.popup(msg)
            return

        return stdOutData
