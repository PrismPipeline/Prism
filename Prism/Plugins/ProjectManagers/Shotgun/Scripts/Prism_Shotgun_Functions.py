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

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


modulePath = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), "external_modules")
sys.path.append(modulePath)


class Prism_Shotgun_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        self.callbacks = []
        self.registerCallbacks()

    @err_catcher(name=__name__)
    def isActive(self):
        return True

    @err_catcher(name=__name__)
    def registerCallbacks(self):
        self.callbacks.append(self.core.registerCallback("projectBrowser_getAssetMenu", self.projectBrowser_getAssetMenu))
        self.callbacks.append(self.core.registerCallback("projectBrowser_getShotMenu", self.projectBrowser_getShotMenu))

    @err_catcher(name=__name__)
    def unregister(self):
        self.unregisterCallbacks()

    @err_catcher(name=__name__)
    def unregisterCallbacks(self):
        for cb in self.callbacks:
            self.core.unregisterCallback(cb["id"])

    @err_catcher(name=__name__)
    def onProjectChanged(self, origin):
        if hasattr(self, "sg"):
            del self.sg

    @err_catcher(name=__name__)
    def prismSettings_loadUI(self, origin):
        origin.gb_sgAccount = QGroupBox("Publish Shotgun versions with Shotgun account")
        lo_sg = QGridLayout()
        origin.gb_sgAccount.setLayout(lo_sg)
        origin.gb_sgAccount.setCheckable(True)
        origin.gb_sgAccount.setChecked(False)

        origin.l_sgUserName = QLabel("Username:       ")
        origin.l_sgUserPassword = QLabel("Password:")
        origin.e_sgUserName = QLineEdit()
        origin.e_sgUserPassword = QLineEdit()

        lo_sg.addWidget(origin.l_sgUserName)
        lo_sg.addWidget(origin.l_sgUserPassword)
        lo_sg.addWidget(origin.e_sgUserName, 0, 1)
        lo_sg.addWidget(origin.e_sgUserPassword, 1, 1)

        origin.tabWidgetPage1.layout().insertWidget(1, origin.gb_sgAccount)
        origin.groupboxes.append(origin.gb_sgAccount)

        origin.gb_sgPrjIntegration = QGroupBox("Shotgun integration")
        origin.w_shotgun = QWidget()
        lo_sgI = QHBoxLayout()
        lo_sgI.addWidget(origin.w_shotgun)
        origin.gb_sgPrjIntegration.setLayout(lo_sgI)
        origin.gb_sgPrjIntegration.setCheckable(True)
        origin.gb_sgPrjIntegration.setChecked(False)

        lo_sg = QGridLayout()
        origin.w_shotgun.setLayout(lo_sg)

        origin.l_sgSite = QLabel("Shotgun site:")
        origin.l_sgPrjName = QLabel("Project Name:")
        origin.l_sgScriptName = QLabel("Script Name:")
        origin.l_sgApiKey = QLabel("Script API key:")
        origin.e_sgSite = QLineEdit()
        origin.e_sgPrjName = QLineEdit()
        origin.e_sgScriptName = QLineEdit()
        origin.e_sgApiKey = QLineEdit()

        lo_sg.addWidget(origin.l_sgSite)
        lo_sg.addWidget(origin.l_sgPrjName)
        lo_sg.addWidget(origin.l_sgScriptName)
        lo_sg.addWidget(origin.l_sgApiKey)
        lo_sg.addWidget(origin.e_sgSite, 0, 1)
        lo_sg.addWidget(origin.e_sgPrjName, 1, 1)
        lo_sg.addWidget(origin.e_sgScriptName, 2, 1)
        lo_sg.addWidget(origin.e_sgApiKey, 3, 1)

        num = origin.w_prjSettings.layout().count() - 1
        origin.w_prjSettings.layout().insertWidget(num, origin.gb_sgPrjIntegration)
        origin.groupboxes.append(origin.gb_sgPrjIntegration)

        origin.gb_sgPrjIntegration.toggled.connect(
            lambda x: self.prismSettings_sgToggled(origin, x)
        )

    @err_catcher(name=__name__)
    def prismSettings_loadSettings(self, origin, settings):
        if "shotgun" in settings:
            if "sguseaccount" in settings["shotgun"]:
                origin.gb_sgAccount.setChecked(settings["shotgun"]["sguseaccount"])

            if "sgusername" in settings["shotgun"]:
                origin.e_sgUserName.setText(settings["shotgun"]["sgusername"])

            if "sguserpassword" in settings["shotgun"]:
                origin.e_sgUserPassword.setText(settings["shotgun"]["sguserpassword"])

    @err_catcher(name=__name__)
    def prismSettings_loadPrjSettings(self, origin, settings):
        if "shotgun" in settings:
            if "active" in settings["shotgun"]:
                origin.gb_sgPrjIntegration.setChecked(settings["shotgun"]["active"])

            if "site" in settings["shotgun"]:
                origin.e_sgSite.setText(settings["shotgun"]["site"])

            if "projectname" in settings["shotgun"]:
                origin.e_sgPrjName.setText(settings["shotgun"]["projectname"])

            if "scriptname" in settings["shotgun"]:
                origin.e_sgScriptName.setText(settings["shotgun"]["scriptname"])

            if "apikey" in settings["shotgun"]:
                origin.e_sgApiKey.setText(settings["shotgun"]["apikey"])

        self.prismSettings_sgToggled(origin, origin.gb_sgPrjIntegration.isChecked())

    @err_catcher(name=__name__)
    def prismSettings_saveSettings(self, origin, settings):
        if "shotgun" not in settings:
            settings["shotgun"] = {}

        settings["shotgun"]["sguseaccount"] = origin.gb_sgAccount.isChecked()
        settings["shotgun"]["sgusername"] = origin.e_sgUserName.text()
        settings["shotgun"]["sguserpassword"] = origin.e_sgUserPassword.text()

    @err_catcher(name=__name__)
    def prismSettings_savePrjSettings(self, origin, settings):
        if "shotgun" not in settings:
            settings["shotgun"] = {}

        settings["shotgun"]["active"] = origin.gb_sgPrjIntegration.isChecked()
        settings["shotgun"]["site"] = origin.e_sgSite.text()
        settings["shotgun"]["projectname"] = origin.e_sgPrjName.text()
        settings["shotgun"]["scriptname"] = origin.e_sgScriptName.text()
        settings["shotgun"]["apikey"] = origin.e_sgApiKey.text()

    @err_catcher(name=__name__)
    def prismSettings_sgToggled(self, origin, checked):
        origin.w_shotgun.setVisible(checked)
        origin.gb_sgAccount.setVisible(checked)

    @err_catcher(name=__name__)
    def pbBrowser_getMenu(self, origin):
        sg = self.core.getConfig("shotgun", "active", configPath=self.core.prismIni)
        if sg:
            sgMenu = QMenu("Shotgun", origin)

            actSg = QAction("Open Shotgun", origin)
            actSg.triggered.connect(self.openSg)
            sgMenu.addAction(actSg)

            sgMenu.addSeparator()

            actSSL = QAction("Shotgun assets to local", origin)
            actSSL.triggered.connect(lambda: self.sgAssetsToLocal(origin))
            sgMenu.addAction(actSSL)

            actSSL = QAction("Local assets to Shotgun", origin)
            actSSL.triggered.connect(lambda: self.sgAssetsToSG(origin))
            sgMenu.addAction(actSSL)

            sgMenu.addSeparator()

            actSSL = QAction("Shotgun shots to local", origin)
            actSSL.triggered.connect(lambda: self.sgShotsToLocal(origin))
            sgMenu.addAction(actSSL)

            actLSS = QAction("Local shots to Shotgun", origin)
            actLSS.triggered.connect(lambda: self.sgShotsToSG(origin))
            sgMenu.addAction(actLSS)

            return sgMenu

    @err_catcher(name=__name__)
    def projectBrowser_getAssetMenu(self, origin, assetname, assetPath, entityType):
        if entityType != "asset":
            return

        sg = self.core.getConfig("shotgun", "active", configPath=self.core.prismIni)
        if sg:
            sgAct = QAction("Open in Shotgun", origin)
            sgAct.triggered.connect(
                lambda: self.openSg(assetname, eType="Asset", assetPath=assetPath)
            )
            return sgAct

    @err_catcher(name=__name__)
    def projectBrowser_getShotMenu(self, origin, shotname):
        sg = self.core.getConfig("shotgun", "active", configPath=self.core.prismIni)
        if sg:
            sgAct = QAction("Open in Shotgun", origin)
            sgAct.triggered.connect(lambda: self.openSg(shotname))
            return sgAct

    @err_catcher(name=__name__)
    def createAsset_open(self, origin):
        sg = self.core.getConfig("shotgun", "active", configPath=self.core.prismIni)
        if not sg:
            return

        origin.chb_createInShotgun = QCheckBox("Create asset in Shotgun")
        origin.w_options.layout().insertWidget(0, origin.chb_createInShotgun)
        origin.chb_createInShotgun.setChecked(True)

    @err_catcher(name=__name__)
    def createAsset_typeChanged(self, origin, state):
        if hasattr(origin, "chb_createInShotgun"):
            origin.chb_createInShotgun.setEnabled(state)

    @err_catcher(name=__name__)
    def assetCreated(self, origin, itemDlg, assetPath):
        if (
            hasattr(itemDlg, "chb_createInShotgun")
            and itemDlg.chb_createInShotgun.isChecked()
        ):
            self.createSgAssets([assetPath])

    @err_catcher(name=__name__)
    def editShot_open(self, origin, shotName):
        shotName, seqName = self.core.entities.splitShotname(shotName)
        if not shotName:
            sg = self.core.getConfig("shotgun", "active", configPath=self.core.prismIni)
            if not sg:
                return

            origin.chb_createInShotgun = QCheckBox("Create shot in Shotgun")
            origin.widget.layout().insertWidget(0, origin.chb_createInShotgun)
            origin.chb_createInShotgun.setChecked(True)

    @err_catcher(name=__name__)
    def editShot_closed(self, origin, shotName):
        if (
            hasattr(origin, "chb_createInShotgun")
            and origin.chb_createInShotgun.isChecked()
        ):
            self.createSgShots([shotName])

    @err_catcher(name=__name__)
    def pbBrowser_getPublishMenu(self, origin):
        sg = self.core.getConfig("shotgun", "active", configPath=self.core.prismIni)
        if sg and origin.mediaPlaybacks["shots"]["seq"]:
            sgAct = QAction("Publish to Shotgun", origin)
            sgAct.triggered.connect(lambda: self.sgPublish(origin))
            return sgAct

    @err_catcher(name=__name__)
    def connectToShotgun(self, user=True):
        if (
            not hasattr(self, "sg")
            or not hasattr(self, "sgPrjId")
            or (user and not hasattr(self, "sgUserId"))
        ):
            import shotgun_api3

            sgSite = self.core.getConfig(
                "shotgun", "site", configPath=self.core.prismIni
            )
            sgProjectName = self.core.getConfig(
                "shotgun", "projectname", configPath=self.core.prismIni
            )
            sgScriptName = self.core.getConfig(
                "shotgun", "scriptname", configPath=self.core.prismIni
            )
            sgApiKey = self.core.getConfig(
                "shotgun", "apikey", configPath=self.core.prismIni
            )

            if (
                not sgSite
                or not sgProjectName
                or not sgScriptName
                or not sgApiKey
            ):
                QMessageBox.warning(
                    self.core.messageParent,
                    "Shotgun",
                    "Not all required information for the authentification are configured.",
                )
                return [None, None, None]

            authentificated = False
            if user:
                useUserAccount = self.core.getConfig("shotgun", "sguseaccount")
                sgUsername = self.core.getConfig("shotgun", "sgusername")
                sgPw = self.core.getConfig("shotgun", "sguserpassword")

                if (
                    useUserAccount
                    and sgUsername
                    and sgPw
                ):
                    try:
                        self.sg = shotgun_api3.Shotgun(
                            sgSite, login=sgUsername, password=sgPw
                        )
                        authentificated = True
                    except:
                        pass

            if not authentificated:
                try:
                    self.sg = shotgun_api3.Shotgun(
                        sgSite, script_name=sgScriptName, api_key=sgApiKey
                    )
                except Exception as e:
                    QMessageBox.warning(
                        self.core.messageParent,
                        "Shotgun",
                        "Could not connect to Shotgun:\n\n%s" % e,
                    )
                    return [None, None, None]

            # get project id
            try:
                sgPrj = self.sg.find("Project", [["name", "is", sgProjectName]])
            except Exception as e:
                QMessageBox.warning(
                    self.core.messageParent,
                    "Shotgun",
                    "Could not request Shotgun data:\n\n%s" % e,
                )
                return [None, None, None]

            if len(sgPrj) == 0:
                QMessageBox.warning(
                    self.core.messageParent,
                    "Shotgun",
                    'Could not find project "%s" in Shotgun.' % sgProjectName,
                )
                return [self.sg, None, None]

            self.sgPrjId = sgPrj[0]["id"]

            # get user id
            if not user:
                return [self.sg, self.sgPrjId, None]

            if useUserAccount is True:
                userName = sgUsername
                filterStr = "login"
            else:
                userName = self.core.getConfig("globals", "username")
                filterStr = "name"

            filters = [
                ["projects", "is", {"type": "Project", "id": self.sgPrjId}],
                [filterStr, "is", userName],
            ]

            sgUser = self.sg.find("HumanUser", filters)

            if len(sgUser) == 0:
                # 	QMessageBox.warning(self.core.messageParent, "Shotgun", "No user \"%s\" is assigned to the project." % userName)
                return [self.sg, self.sgPrjId, None]

            self.sgUserId = sgUser[0]["id"]

        if user:
            return [self.sg, self.sgPrjId, self.sgUserId]
        else:
            return [self.sg, self.sgPrjId, None]

    @err_catcher(name=__name__)
    def createSgAssets(self, assets=[]):
        sg, sgPrjId, sgUserId = self.connectToShotgun(user=False)

        if sg is None or sgPrjId is None or sgUserId:
            return

        if "sg_localhierarchy" not in sg.schema_field_read("Asset"):
            try:
                sg.schema_field_create("Asset", "text", "localHierarchy", "")
            except Exception as e:
                QMessageBox.critical(
                    self.core.messageParent,
                    "Create field",
                    'Could not create field "sg_localhierarchy":\n\n%s' % e,
                )
                return

        fields = ["id", "code", "tasks"]
        filters = [["project", "is", {"type": "Project", "id": sgPrjId}]]
        sgAssets = {}
        for x in sg.find("Asset", filters, fields):
            assetName = x["code"]
            sgAssets[assetName] = x

        fields = ["code", "short_name", "entity_type"]
        sgSteps = {
            x["code"]: x
            for x in sg.find("Step", [], fields)
            if x["entity_type"] == "Asset"
        }

        aBasePath = self.core.getAssetPath()
        assets = [[os.path.basename(x), x.replace(aBasePath, "")[1:]] for x in assets]

        createdAssets = []
        updatedAssets = []
        for asset in assets:
            if asset[0] not in sgAssets.keys():
                data = {
                    "project": {"type": "Project", "id": sgPrjId},
                    "code": asset[0],
                    "sg_status_list": "ip",
                    "sg_localhierarchy": asset[1],
                }

                result = sg.create("Asset", data)
                createdAssets.append(result)

    @err_catcher(name=__name__)
    def createSgShots(self, shots=[]):
        sg, sgPrjId, sgUserId = self.connectToShotgun(user=False)

        if sg is None or sgPrjId is None or sgUserId:
            return

        fields = [
            "id",
            "code",
            "tasks",
            "image",
            "sg_cut_in",
            "sg_cut_out",
            "sg_sequence",
        ]
        filters = [["project", "is", {"type": "Project", "id": sgPrjId}]]
        sgShots = {}
        for x in sg.find("Shot", filters, fields):
            if x["sg_sequence"] is None:
                shotName = x["code"]
            else:
                shotName = "%s%s%s" % (
                    x["sg_sequence"]["name"],
                    self.core.sequenceSeparator,
                    x["code"],
                )
            sgShots[shotName] = x

        fields = ["code", "short_name", "entity_type"]
        sgSteps = {
            x["code"]: x
            for x in sg.find("Step", [], fields)
            if x["entity_type"] == "Shot"
        }

        fields = ["id", "code"]
        filters = [["project", "is", {"type": "Project", "id": sgPrjId}]]
        sgSequences = {x["code"]: x for x in sg.find("Sequence", filters, fields)}

        createdShots = []
        updatedShots = []
        for shot in shots:
            shotName, seqName = self.core.entities.splitShotname(shot)
            if seqName == "no sequence":
                seqName = ""

            shotImgPath = os.path.join(
                os.path.dirname(self.core.prismIni), "Shotinfo", "%s_preview.jpg" % shot
            )
            if os.path.exists(shotImgPath):
                shotImg = shotImgPath
            else:
                shotImg = ""

            shotRange = self.core.getConfig("shotRanges", shot, config="shotinfo")

            if type(shotRange) == list and len(shotRange) == 2:
                startFrame = shotRange[0]
                endFrame = shotRange[1]
            else:
                startFrame = ""
                endFrame = ""

            shotSeq = {"code": ""}
            if seqName != "" and shot not in sgShots.keys():
                if seqName in sgSequences.keys():
                    shotSeq = sgSequences[seqName]
                else:
                    data = {
                        "project": {"type": "Project", "id": sgPrjId},
                        "code": seqName,
                        "sg_status_list": "ip",
                    }

                    shotSeq = sg.create("Sequence", data)
                    sgSequences[shotSeq["code"]] = shotSeq

            if shot not in sgShots.keys():
                data = {
                    "project": {"type": "Project", "id": sgPrjId},
                    "code": shotName,
                    "sg_status_list": "ip",
                    "image": shotImg,
                }

                if shotSeq["code"] != "":
                    data["sg_sequence"] = shotSeq

                try:
                    int(startFrame)
                    data["sg_cut_in"] = int(startFrame)
                except:
                    pass

                try:
                    int(startFrame)
                    data["sg_cut_out"] = int(endFrame)
                except:
                    pass

                result = sg.create("Shot", data)
                result["sg_sequence"] = shotSeq["code"]
                createdShots.append(result)
            else:
                data = {"image": shotImg}

                try:
                    if sgShots[shot]["sg_cut_in"] != int(startFrame):
                        data["sg_cut_in"] = int(startFrame)
                except:
                    pass

                try:
                    if sgShots[shot]["sg_cut_out"] != int(endFrame):
                        data["sg_cut_out"] = int(endFrame)
                except:
                    pass

                if len(data.keys()) > 1 or shotImg != "":
                    result = sg.update("Shot", sgShots[shot]["id"], data)
                    if (
                        [seqName, shotName]
                        not in [[x["code"], x["sg_sequence"]] for x in createdShots]
                        and shot not in updatedShots
                        and (len(data.keys()) > 1 or sgShots[shot]["image"] is None)
                    ):
                        updatedShots.append(shot)

    @err_catcher(name=__name__)
    def sgPublish(self, origin):
        try:
            del sys.modules["ShotgunPublish"]
        except:
            pass

        import ShotgunPublish

        if origin.tbw_browser.currentWidget().property("tabType") == "Assets":
            pType = "Asset"
        else:
            pType = "Shot"

        shotName = os.path.basename(origin.renderBasePath)

        taskName = (
            origin.curRTask.replace(" (playblast)", "")
            .replace(" (2d)", "")
            .replace(" (external)", "")
        )
        versionName = origin.curRVersion.replace(" (local)", "")

        imgPaths = []
        if (
            origin.mediaPlaybacks["shots"]["prvIsSequence"]
            or len(origin.mediaPlaybacks["shots"]["seq"]) == 1
        ):
            if os.path.splitext(origin.mediaPlaybacks["shots"]["seq"][0])[1] in [
                ".mp4",
                ".mov",
            ]:
                imgPaths.append(
                    [
                        os.path.join(
                            origin.mediaPlaybacks["shots"]["basePath"],
                            origin.mediaPlaybacks["shots"]["seq"][0],
                        ),
                        origin.mediaPlaybacks["shots"]["curImg"],
                    ]
                )
            else:
                imgPaths.append(
                    [
                        os.path.join(
                            origin.mediaPlaybacks["shots"]["basePath"],
                            origin.mediaPlaybacks["shots"]["seq"][
                                origin.mediaPlaybacks["shots"]["curImg"]
                            ],
                        ),
                        0,
                    ]
                )
        else:
            for i in origin.seq:
                imgPaths.append(
                    [os.path.join(origin.mediaPlaybacks["shots"]["basePath"], i), 0]
                )

        if "pstart" in origin.mediaPlaybacks["shots"]:
            sf = origin.mediaPlaybacks["shots"]["pstart"]
        else:
            sf = 0

        sgp = ShotgunPublish.sgPublish(
            core=self.core,
            origin=self,
            ptype=pType,
            shotName=shotName,
            task=taskName,
            version=versionName,
            sources=imgPaths,
            startFrame=sf,
        )
        if not hasattr(sgp, "sgPrjId") or not hasattr(sgp, "sgUserId"):
            return

        self.core.parentWindow(sgp)
        sgp.exec_()

        curTab = origin.tbw_browser.currentWidget().property("tabType")
        curData = [
            curTab,
            origin.cursShots,
            origin.curRTask,
            origin.curRVersion,
            origin.curRLayer,
        ]
        origin.showRender(curData[0], curData[1], curData[2], curData[3], curData[4])

    def openSg(self, shotName=None, eType="Shot", assetPath=""):
        sg, sgPrjId, sgUserId = self.connectToShotgun(user=False)

        if sg is None or sgPrjId is None:
            return

        sgSite = self.core.getConfig("shotgun", "site", configPath=self.core.prismIni)

        if shotName is None:
            sgSite += "/detail/Project/" + str(sgPrjId)

        else:
            filters = [
                ["project", "is", {"type": "Project", "id": sgPrjId}],
                ["code", "is", shotName],
            ]

            if eType == "Asset":
                filters += [["sg_localhierarchy", "is", assetPath]]
            elif eType == "Shot":
                shotName, seqName = self.core.entities.splitShotname(shotName)
                if seqName and seqName != "no sequence":
                    seqFilters = [
                        ["project", "is", {"type": "Project", "id": sgPrjId}],
                        ["code", "is", seqName],
                    ]

                    seq = sg.find_one("Sequence", seqFilters)
                    if seq is not None:
                        filters = [
                            ["project", "is", {"type": "Project", "id": sgPrjId}],
                            ["code", "is", shotName],
                            ["sg_sequence", "is", seq],
                        ]

            shot = sg.find_one(eType, filters)
            if shot is None:
                QMessageBox.warning(
                    self.core.messageParent,
                    "Shotgun",
                    "Could not find %s %s in Shotgun" % (eType, shotName),
                )
                return

            shotID = shot["id"]
            sgSite += "/detail/%s/" % eType + str(shotID)

        import webbrowser

        webbrowser.open(sgSite)

    @err_catcher(name=__name__)
    def sgAssetsToLocal(self, origin):
        sg, sgPrjId, sgUserId = self.connectToShotgun(user=False)

        if sg is None or sgPrjId is None:
            return

        hasLocalField = "sg_localhierarchy" in sg.schema_field_read("Asset")

        fields = ["id", "code", "tasks", "sg_asset_type"]
        if hasLocalField:
            fields.append("sg_localhierarchy")
        filters = [["project", "is", {"type": "Project", "id": sgPrjId}]]
        sgAssets = sg.find("Asset", filters, fields)

        createdAssets = []
        for i in sgAssets:
            if hasLocalField and i["sg_localhierarchy"] is not None:
                assetPath = os.path.join(origin.aBasePath, i["sg_localhierarchy"])
                assetName = os.path.basename(assetPath)
            else:
                if not "sg_asset_type" in i or i["sg_asset_type"] is None:
                    i["sg_asset_type"] = ""
                    assetName = i["code"]
                else:
                    assetName = "%s/%s" % (i["sg_asset_type"], i["code"])

                assetPath = os.path.join(
                    origin.aBasePath, i["sg_asset_type"], i["code"]
                )

            if not os.path.exists(assetPath):
                self.core.entities.createEntity("asset", assetPath)
                createdAssets.append(assetName)

        if len(createdAssets) > 0:
            msgString = "The following assets were created:\n\n"

            createdAssets.sort()

            for i in createdAssets:
                msgString += i + "\n"
        else:
            msgString = "No assets were created."

        QMessageBox.information(self.core.messageParent, "Shotgun Sync", msgString)

        origin.refreshAHierarchy()

    @err_catcher(name=__name__)
    def sgAssetsToSG(self, origin):
        sg, sgPrjId, sgUserId = self.connectToShotgun(user=False)

        if sg is None or sgPrjId is None or sgUserId:
            return

        if "sg_localhierarchy" not in sg.schema_field_read("Asset"):
            try:
                sg.schema_field_create("Asset", "text", "localHierarchy", "")
            except Exception as e:
                QMessageBox.critical(
                    self.core.messageParent,
                    "Create field",
                    'Could not create field "sg_localhierarchy":\n\n%s' % e,
                )
                return

        fields = ["id", "code", "tasks"]
        filters = [["project", "is", {"type": "Project", "id": sgPrjId}]]
        sgAssets = {}
        for x in sg.find("Asset", filters, fields):
            assetName = x["code"]
            sgAssets[assetName] = x

        fields = ["code", "short_name", "entity_type"]
        sgSteps = {
            x["code"]: x
            for x in sg.find("Step", [], fields)
            if x["entity_type"] == "Asset"
        }

        assets = self.core.entities.getAssetPaths()
        localAssets = [
            [os.path.basename(x), x.replace(origin.aBasePath, "")[1:]]
            for x in assets
            if x.replace(os.path.join(self.core.fixPath(origin.aBasePath), ""), "")
            not in self.core.entities.omittedEntities["asset"]
        ]

        createdAssets = []
        updatedAssets = []
        for asset in localAssets:
            if asset[0] not in sgAssets.keys():
                data = {
                    "project": {"type": "Project", "id": sgPrjId},
                    "code": asset[0],
                    "sg_status_list": "ip",
                    "sg_localhierarchy": asset[1],
                }

                result = sg.create("Asset", data)
                createdAssets.append(result)

        if len(createdAssets) > 0 or len(updatedAssets) > 0:
            msgString = ""

            createdAssetNames = []
            for i in createdAssets:
                createdAssetNames.append(i["code"])

            createdAssetNames.sort()
            updatedAssets.sort()

            if len(createdAssetNames) > 0:
                msgString += "The following assets were created:\n\n"

                for i in createdAssetNames:
                    msgString += i + "\n"

            if len(createdAssetNames) > 0 and len(updatedAssets) > 0:
                msgString += "\n\n"

            if len(updatedAssets) > 0:
                msgString += "The following assets were updated:\n\n"

                for i in updatedAssets:
                    msgString += i + "\n"
        else:
            msgString = "No assets were created or updated."

        QMessageBox.information(self.core.messageParent, "Shotgun Sync", msgString)

    @err_catcher(name=__name__)
    def sgShotsToLocal(self, origin):
        sg, sgPrjId, sgUserId = self.connectToShotgun(user=False)

        if sg is None or sgPrjId is None:
            return

        fields = [
            "id",
            "code",
            "image",
            "sg_cut_in",
            "sg_cut_out",
            "tasks",
            "sg_sequence",
        ]
        filters = [["project", "is", {"type": "Project", "id": sgPrjId}]]
        sgShots = {}
        for x in sg.find("Shot", filters, fields):
            if self.core.filenameSeparator not in x["code"]:
                if x["sg_sequence"] is None:
                    shotName = x["code"]
                else:
                    shotName = "%s%s%s" % (
                        x["sg_sequence"]["name"],
                        self.core.sequenceSeparator,
                        x["code"],
                    )
                sgShots[shotName] = x

        fields = ["code", "short_name", "entity_type"]
        sgSteps = {
            x["code"]: x["short_name"]
            for x in sg.find("Step", [], fields)
            if x["entity_type"] is not None
        }

        createdShots = []
        updatedShots = []
        for shotName, shotData in sgShots.items():
            if not os.path.exists(os.path.join(origin.sBasePath, shotName)):
                self.core.entities.createEntity("shot", shotName)

                createdShots.append(shotName)

            startFrame = shotData["sg_cut_in"]
            endFrame = shotData["sg_cut_out"]

            if startFrame is not None and endFrame is not None:
                shotRange = self.core.getConfig("shotRanges", shotName, config="shotinfo")

                if type(shotRange) == list and len(shotRange) == 2:
                    prvStartFrame = shotRange[0]
                    prvEndFrame = shotRange[1]
                else:
                    prvStartFrame = ""
                    prvEndFrame = ""

                self.core.setConfig("shotRanges", shotName, [startFrame, endFrame], config="shotinfo")

                if (
                    shotName not in createdShots
                    and shotName not in updatedShots
                    and (startFrame != prvStartFrame or endFrame != prvEndFrame)
                ):
                    updatedShots.append(shotName)

            if shotData["image"] is not None:
                import urllib2

                shotImgPath = os.path.join(
                    os.path.dirname(self.core.prismIni),
                    "Shotinfo",
                    "%s_preview.jpg" % shotName,
                )

                if not os.path.exists(os.path.dirname(shotImgPath)):
                    os.makedirs(os.path.dirname(shotImgPath))

                prvExist = os.path.exists(shotImgPath)

                response = urllib2.urlopen(shotData["image"])

                with open(shotImgPath, "wb") as prvImg:
                    prvImg.write(response.read())

                if (
                    shotName not in createdShots
                    and shotName not in updatedShots
                    and not prvExist
                ):
                    updatedShots.append(shotName)

        if len(createdShots) > 0 or len(updatedShots) > 0:
            msgString = ""
            createdShots.sort()
            updatedShots.sort()

            if len(createdShots) > 0:
                msgString += "The following shots were created:\n\n"

                for i in createdShots:
                    msgString += i + "\n"

            if len(createdShots) > 0 and len(updatedShots) > 0:
                msgString += "\n\n"

            if len(updatedShots) > 0:
                msgString += "The following shots were updated:\n\n"

                for i in updatedShots:
                    msgString += i + "\n"
        else:
            msgString = "No shots were created or updated."

        msgString += (
            '\n\nNote that shots with "%s" in their name are getting ignored by Prism.'
            % self.core.filenameSeparator
        )

        QMessageBox.information(self.core.messageParent, "Shotgun Sync", msgString)

        for i in os.walk(origin.sBasePath):
            foldercont = i
            break

        shotnames = [x for x in foldercont[1] if not x.startswith("_")]
        localShots = []
        for i in shotnames:
            if i not in sgShots.keys():
                localShots.append(i)

        if len(localShots) > 0:
            msg = QMessageBox(
                QMessageBox.Question,
                "Shotgun Sync",
                "Some local shots don't exist in Shotgun.\n\nDo you want to hide the local shots?",
                parent=self.core.messageParent,
            )
            msg.addButton("Yes", QMessageBox.YesRole)
            msg.addButton("No", QMessageBox.YesRole)
            action = msg.exec_()

            if action == 0:
                noAccess = []
                for i in localShots:
                    dstname = os.path.join(origin.sBasePath, "_" + i)
                    if not os.path.exists(dstname):
                        try:
                            os.rename(os.path.join(origin.sBasePath, i), dstname)
                        except:
                            noAccess.append(i)

                if len(noAccess) > 0:
                    msgString = "Acces denied for:\n\n"

                    for i in noAccess:
                        msgString += i + "\n"

                    QMessageBox.warning(
                        self.core.messageParent, "Hide Shots", msgString
                    )

        origin.refreshShots()

    @err_catcher(name=__name__)
    def sgShotsToSG(self, origin):
        sg, sgPrjId, sgUserId = self.connectToShotgun(user=False)

        if sg is None or sgPrjId is None or sgUserId:
            return

        fields = [
            "id",
            "code",
            "tasks",
            "image",
            "sg_cut_in",
            "sg_cut_out",
            "sg_sequence",
        ]
        filters = [["project", "is", {"type": "Project", "id": sgPrjId}]]
        sgShots = {}
        for x in sg.find("Shot", filters, fields):
            if x["sg_sequence"] is None:
                shotName = x["code"]
            else:
                shotName = "%s%s%s" % (
                    x["sg_sequence"]["name"],
                    self.core.sequenceSeparator,
                    x["code"],
                )
            sgShots[shotName] = x

        fields = ["code", "short_name", "entity_type"]
        sgSteps = {
            x["code"]: x
            for x in sg.find("Step", [], fields)
            if x["entity_type"] == "Shot"
        }

        fields = ["id", "code"]
        filters = [["project", "is", {"type": "Project", "id": sgPrjId}]]
        sgSequences = {x["code"]: x for x in sg.find("Sequence", filters, fields)}

        for i in os.walk(origin.sBasePath):
            foldercont = i
            break

        self.core.entities.refreshOmittedEntities()

        localShots = []
        for x in foldercont[1]:
            if not x.startswith("_") and x not in self.core.entities.omittedEntities["shot"]:
                shotName, seqName = self.core.entities.splitShotname(x)
                if seqName == "no sequence":
                    seqName = ""

                localShots.append([x, seqName, shotName])

        createdShots = []
        updatedShots = []
        for shot in localShots:
            shotImgPath = os.path.join(
                os.path.dirname(self.core.prismIni),
                "Shotinfo",
                "%s_preview.jpg" % shot[0],
            )
            if os.path.exists(shotImgPath):
                shotImg = shotImgPath
            else:
                shotImg = ""

            shotRange = self.core.getConfig("shotRanges", shot[0], config="shotinfo")

            if type(shotRange) == list and len(shotRange) == 2:
                startFrame = shotRange[0]
                endFrame = shotRange[1]
            else:
                startFrame = ""
                endFrame = ""

            shotSeq = {"code": ""}
            if shot[1] != "" and shot[0] not in sgShots.keys():
                if shot[1] in sgSequences.keys():
                    shotSeq = sgSequences[shot[1]]
                else:
                    data = {
                        "project": {"type": "Project", "id": sgPrjId},
                        "code": shot[1],
                        "sg_status_list": "ip",
                    }

                    shotSeq = sg.create("Sequence", data)
                    sgSequences[shotSeq["code"]] = shotSeq

            if shot[0] not in sgShots.keys():
                data = {
                    "project": {"type": "Project", "id": sgPrjId},
                    "code": shot[2],
                    "sg_status_list": "ip",
                    "image": shotImg,
                }

                if shotSeq["code"] != "":
                    data["sg_sequence"] = shotSeq

                try:
                    int(startFrame)
                    data["sg_cut_in"] = int(startFrame)
                except:
                    pass

                try:
                    int(startFrame)
                    data["sg_cut_out"] = int(endFrame)
                except:
                    pass

                result = sg.create("Shot", data)
                result["sg_sequence"] = shotSeq["code"]
                createdShots.append(result)
            else:
                data = {"image": shotImg}

                try:
                    if sgShots[shot[0]]["sg_cut_in"] != int(startFrame):
                        data["sg_cut_in"] = int(startFrame)
                except:
                    pass

                try:
                    if sgShots[shot[0]]["sg_cut_out"] != int(endFrame):
                        data["sg_cut_out"] = int(endFrame)
                except:
                    pass

                if len(data.keys()) > 1 or shotImg != "":
                    result = sg.update("Shot", sgShots[shot[0]]["id"], data)
                    if (
                        [shot[1], shot[2]]
                        not in [[x["code"], x["sg_sequence"]] for x in createdShots]
                        and shot[0] not in updatedShots
                        and (len(data.keys()) > 1 or sgShots[shot[0]]["image"] is None)
                    ):
                        updatedShots.append(shot[0])

            shotSteps = []
            stepsPath = self.core.getEntityPath(entity="step", shot=shot[0])
            for k in os.walk(stepsPath):
                shotSteps = k[1]
                break

            shotTasks = {}
            for k in shotSteps:
                stepPath = self.core.getEntityPath(shot=shot[0], step=k)
                for m in os.walk(stepPath):
                    shotTasks[k] = m[1]
                    break

        if len(createdShots) > 0 or len(updatedShots) > 0:
            msgString = ""

            createdShotNames = []
            for i in createdShots:
                if i["sg_sequence"] == "":
                    createdShotNames.append(i["code"])
                else:
                    createdShotNames.append(
                        "%s%s%s"
                        % (i["sg_sequence"], self.core.sequenceSeparator, i["code"])
                    )

            createdShotNames.sort()
            updatedShots.sort()

            if len(createdShotNames) > 0:
                msgString += "The following shots were created:\n\n"

                for i in createdShotNames:
                    msgString += i + "\n"

            if len(createdShotNames) > 0 and len(updatedShots) > 0:
                msgString += "\n\n"

            if len(updatedShots) > 0:
                msgString += "The following shots were updated:\n\n"

                for i in updatedShots:
                    msgString += i + "\n"
        else:
            msgString = "No shots were created or updated."

        QMessageBox.information(self.core.messageParent, "Shotgun Sync", msgString)
