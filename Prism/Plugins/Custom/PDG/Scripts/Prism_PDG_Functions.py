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
import subprocess
import threading
import glob

from functools import wraps

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *


try:
    import hou
    import pdg
except:
    pass


class Prism_PDG_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

    # this function catches any errors in this script and can be ignored
    def err_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            exc_info = sys.exc_info()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                erStr = (
                    "%s ERROR - Prism_Plugin_PDG - Core: %s - Plugin: %s:\n%s\n\n%s"
                    % (
                        time.strftime("%d/%m/%y %X"),
                        args[0].core.version,
                        args[0].plugin.version,
                        "".join(traceback.format_stack()),
                        traceback.format_exc(),
                    )
                )
                args[0].core.writeErrorLog(erStr)

        return func_wrapper

    # if returns true, the plugin will be loaded by Prism
    @err_decorator
    def isActive(self):
        return "hou" in globals()

    @err_decorator
    def getPythonExamples(self):
        exampleMenu = []
        snippetPath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Examples", "python_snippets")
        exampleFiles = glob.glob(snippetPath + "/*.py")
        for e in exampleFiles:
            with open(e, "r") as f:
                example = f.read()

            exampleName = example.split("\n")[0][2:]
            example = "\n".join(example.split("\n")[1:])
            exampleMenu.append(example)
            exampleMenu.append(exampleName)

        return exampleMenu

    @err_decorator
    def cookNode(self, **kwargs):

        if not hasattr(threading, "__mylock"):
            threading.__mylock = threading.Lock()

        with threading.__mylock:
            result = None
            self.core.uiAvailable = False

            if kwargs["nodeType"] == "google_docs":
                self.readGoogleDocs(
                    pdgCallback=kwargs["pdgCallback"],
                    itemHolder=kwargs["itemHolder"],
                    upstreamItems=kwargs["upstreamItems"],
                )
            elif kwargs["nodeType"] == "createEntity":
                self.createEntity(
                    pdgCallback=kwargs["pdgCallback"],
                    itemHolder=kwargs["itemHolder"],
                    upstreamItems=kwargs["upstreamItems"],
                )
            elif kwargs["nodeType"] == "writeEntity":
                result = self.writeEntity(workItem=kwargs["workItem"])
            elif kwargs["nodeType"] == "combineStates":
                self.combineStates(
                    pdgCallback=kwargs["pdgCallback"],
                    itemHolder=kwargs["itemHolder"],
                    upstreamItems=kwargs["upstreamItems"],
                )
            elif kwargs["nodeType"] == "createState":
                self.createState(
                    pdgCallback=kwargs["pdgCallback"],
                    itemHolder=kwargs["itemHolder"],
                    upstreamItems=kwargs["upstreamItems"],
                )
            elif kwargs["nodeType"] == "writeStates":
                result = self.writeStates(
                    pdgCallback=kwargs["pdgCallback"],
                    itemHolder=kwargs["itemHolder"],
                    upstreamItems=kwargs["upstreamItems"],
                )
            elif kwargs["nodeType"] == "createDependencies":
                self.createDependencies(
                    pdgCallback=kwargs["pdgCallback"], itemHolder=kwargs["itemHolder"]
                )
            elif kwargs["nodeType"] == "setProject":
                self.setProject(workItem=kwargs["workItem"])
            elif kwargs["nodeType"] == "scenePython":
                result = self.scenePython(
                    pdgCallback=kwargs["pdgCallback"],
                    itemHolder=kwargs["itemHolder"],
                    upstreamItems=kwargs["upstreamItems"],
                )
            else:
                self.core.popup("Unknown nodetype: %s" % kwargs["nodeType"])

            self.core.uiAvailable = True
            return result

    @err_decorator
    def createWorkItems(self, itemHolder, upstreamItems, entityType, entityData):
        if entityType == "assets":
            for entity in entityData:
                item = itemHolder.addWorkItem()
                item.setStringAttrib("entity", "asset")
                item.setStringAttrib("hierarchy", entity["hierarchy"])
                item.setStringAttrib("name", entity["asset"])
        if entityType == "shots":
            for entity in entityData:
                item = itemHolder.addWorkItem()
                item.setStringAttrib("entity", "shot")
                item.setStringAttrib("sequence", entity["sequence"])
                item.setStringAttrib("name", entity["shot"])
                item.setStringAttrib("framerange", entity["startframe"])
                item.setStringAttrib("framerange", entity["endframe"], 1)

    @err_decorator
    def setupNode(self, entityType, node):
        if entityType == "fromFile":
            cNode = node.createOutputNode("prism::create_entity")
            cNode.parm("entity").set("file")
        elif entityType == "project":
            cNode = node.createOutputNode("prism::create_entity")
            cNode.parm("entity").set("project")
        elif entityType == "asset":
            cNode = node.createOutputNode("prism::create_entity")
            cNode.parm("entity").set("asset")
        elif entityType == "shot":
            cNode = node.createOutputNode("prism::create_entity")
            cNode.parm("entity").set("shot")
        elif entityType == "step":
            cNode = node.createOutputNode("prism::create_entity")
            cNode.parm("entity").set("step")
        elif entityType == "category":
            cNode = node.createOutputNode("prism::create_entity")
            cNode.parm("entity").set("category")
        elif entityType == "scenefile":
            cNode = node.createOutputNode("prism::create_entity")
            cNode.parm("entity").set("scenefile")
        elif entityType == "write":
            cNode = node.createOutputNode("prism::write_entity")
        elif entityType == "setProject":
            cNode = node.createOutputNode("prism::set_project")
        elif entityType == "create_state":
            cNode = node.createOutputNode("prism::create_state")
        elif entityType == "write_states":
            cNode = node.createOutputNode("prism::write_states")
        else:
            self.core.popup("Invalid type: %s" % entityType)
            return

        if QApplication.keyboardModifiers() != Qt.ShiftModifier:
            cNode.setCurrent(True, clear_all_selected=True)

        return cNode

    @err_decorator
    def readGoogleDocs(self, pdgCallback, itemHolder, upstreamItems):
        node = hou.nodeBySessionId(pdgCallback.customId)
        parentNode = node.parent()
        if upstreamItems:
            with upstreamItems[0].makeActive():
                auth = parentNode.parm("authorization").eval()
                docName = parentNode.parm("document").eval()
                sheetName = parentNode.parm("sheet").eval()
                entityType = parentNode.parm("entity").evalAsString()
                fromRow = parentNode.parm("fromRow").eval()
                useToRow = parentNode.parm("useToRow").eval()
                toRow = parentNode.parm("toRow").eval()
                sequenceCol = ord(parentNode.parm("sequence").eval().lower()) - 96
                shotCol = ord(parentNode.parm("shot").eval().lower()) - 96
                startframeCol = ord(parentNode.parm("startframe").eval().lower()) - 96
                endframeCol = ord(parentNode.parm("endframe").eval().lower()) - 96
                hierarchyCol = ord(parentNode.parm("hierarchy").eval().lower()) - 96
                assetCol = ord(parentNode.parm("asset").eval().lower()) - 96
        else:
            auth = parentNode.parm("authorization").eval()
            docName = parentNode.parm("document").eval()
            sheetName = parentNode.parm("sheet").eval()
            entityType = parentNode.parm("entity").evalAsString()
            fromRow = parentNode.parm("fromRow").eval()
            useToRow = parentNode.parm("useToRow").eval()
            toRow = parentNode.parm("toRow").eval()
            sequenceCol = ord(parentNode.parm("sequence").eval().lower()) - 96
            shotCol = ord(parentNode.parm("shot").eval().lower()) - 96
            startframeCol = ord(parentNode.parm("startframe").eval().lower()) - 96
            endframeCol = ord(parentNode.parm("endframe").eval().lower()) - 96
            hierarchyCol = ord(parentNode.parm("hierarchy").eval().lower()) - 96
            assetCol = ord(parentNode.parm("asset").eval().lower()) - 96

        if not useToRow:
            toRow = -1

        if entityType == "assets":
            columns = {"hierarchy": hierarchyCol, "asset": assetCol}
        else:
            columns = {
                "sequence": sequenceCol,
                "shot": shotCol,
                "startframe": startframeCol,
                "endframe": endframeCol,
            }
        from PrismUtils import GoogleDocs

        entityData = GoogleDocs.readGDocs(
            self.core,
            auth,
            docName,
            sheetName,
            sorted(columns.values()),
            fromRow,
            toRow,
        )
        colNames = sorted(columns.keys(), key=lambda x: columns[x])
        dataDicts = []
        for i in entityData:
            entityDict = {}
            for name in colNames:
                entityDict[name] = i[colNames.index(name)]
            dataDicts.append(entityDict)

        self.createWorkItems(itemHolder, upstreamItems, entityType, dataDicts)

    @err_decorator
    def createEntity(self, pdgCallback, itemHolder, upstreamItems):
        parentNode = hou.nodeBySessionId(pdgCallback.customId).parent()
        if upstreamItems:
            with upstreamItems[0].makeActive():
                entity = parentNode.parm("entity").eval()
        else:
            entity = parentNode.parm("entity").eval()

        if entity == 0:
            if upstreamItems:
                with upstreamItems[0].makeActive():
                    filepath = parentNode.parm("definitionfile").eval()
            else:
                filepath = parentNode.parm("definitionfile").eval()

            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    defData = json.load(f)

                if "ASSETS" in defData:
                    for assetCat in defData["ASSETS"]:
                        for asset in defData["ASSETS"][assetCat]:
                            item = itemHolder.addWorkItem()
                            item.setStringAttrib("entity", "asset")
                            item.setStringAttrib("hierarchy", assetCat)
                            item.setStringAttrib("name", asset)

                if "SHOTS" in defData:
                    for seq in defData["SHOTS"]:
                        for shot in defData["SHOTS"][seq]:
                            item = itemHolder.addWorkItem()
                            item.setStringAttrib("entity", "shot")
                            item.setStringAttrib("sequence", seq)
                            item.setStringAttrib("name", shot)

        elif entity == 1:
            if upstreamItems:
                for upstreamItem in upstreamItems:
                    with upstreamItem.makeActive():
                        item = itemHolder.addWorkItem(
                            cloneResultData=True, preserveType=True, parent=upstreamItem
                        )
                        item.setStringAttrib("entity", "project")
                        path = (
                            parentNode.parm("projectPath").eval()
                            or upstreamItem.stringAttribValue("path")
                            or ""
                        )
                        name = (
                            parentNode.parm("projectName").eval()
                            or upstreamItem.stringAttribValue("name")
                            or ""
                        )
                        item.setStringAttrib("path", path)
                        item.setStringAttrib("name", name)
            else:
                item = itemHolder.addWorkItem()
                item.setStringAttrib("entity", "project")
                item.setStringAttrib("path", parentNode.parm("projectPath").eval())
                item.setStringAttrib("name", parentNode.parm("projectName").eval())

        elif entity == 2:
            if upstreamItems:
                for upstreamItem in upstreamItems:
                    with upstreamItem.makeActive():
                        item = itemHolder.addWorkItem(
                            cloneResultData=True, preserveType=True, parent=upstreamItem
                        )
                        item.setStringAttrib("entity", "asset")
                        if upstreamItem.stringAttribValue("hierarchy"):
                            path = "%s/%s" % (
                                upstreamItem.stringAttribValue("hierarchy"),
                                parentNode.parm("assetHierarchy").eval(),
                            )
                        else:
                            path = parentNode.parm("assetHierarchy").eval()
                        name = (
                            parentNode.parm("entityName").eval()
                            or upstreamItem.stringAttribValue("name")
                            or ""
                        )
                        item.setStringAttrib("hierarchy", path)
                        item.setStringAttrib("name", name)
            else:
                item = itemHolder.addWorkItem()
                item.setStringAttrib("entity", "asset")
                item.setStringAttrib(
                    "hierarchy", parentNode.parm("assetHierarchy").eval()
                )
                item.setStringAttrib("name", parentNode.parm("entityName").eval())

        elif entity == 3:
            if upstreamItems:
                for upstreamItem in upstreamItems:
                    with upstreamItem.makeActive():
                        item = itemHolder.addWorkItem(
                            cloneResultData=True, preserveType=True, parent=upstreamItem
                        )
                        item.setStringAttrib("entity", "shot")
                        path = (
                            parentNode.parm("sequence").eval()
                            or upstreamItem.stringAttribValue("sequence")
                            or ""
                        )
                        name = (
                            parentNode.parm("entityName").eval()
                            or upstreamItem.stringAttribValue("name")
                            or ""
                        )
                        if parentNode.parm("useRange").eval():
                            rangeStart = str(
                                parentNode.parm("shotrangex").evalAsString()
                            )
                            rangeEnd = str(parentNode.parm("shotrangey").evalAsString())
                            item.setStringAttrib("framerange", rangeStart)
                            item.setStringAttrib("framerange", rangeEnd, 1)
                        item.setStringAttrib("sequence", path)
                        item.setStringAttrib("name", name)
            else:
                item = itemHolder.addWorkItem()
                item.setStringAttrib("entity", "shot")
                item.setStringAttrib("sequence", parentNode.parm("sequence").eval())
                item.setStringAttrib("name", parentNode.parm("entityName").eval())
                if parentNode.parm("useRange").eval():
                    item.setStringAttrib(
                        "framerange", parentNode.parm("shotrangex").evalAsString()
                    )
                    item.setStringAttrib(
                        "framerange", parentNode.parm("shotrangey").evalAsString(), 1
                    )

        elif entity == 4:
            for upstreamItem in upstreamItems:
                with upstreamItem.makeActive():
                    curType = upstreamItem.stringAttribValue("entity")
                    if curType in ["asset", "shot"]:
                        item = itemHolder.addWorkItem(
                            cloneResultData=True, preserveType=True, parent=upstreamItem
                        )
                        item.setStringAttrib("entity", "step")
                        item.setStringAttrib(
                            "%sName" % curType,
                            upstreamItem.stringAttribValue("name"),
                            0,
                        )
                        item.setStringAttrib(
                            "name", parentNode.parm("stepName").eval()
                        )

        elif entity == 5:
            for upstreamItem in upstreamItems:
                with upstreamItem.makeActive():
                    curType = upstreamItem.stringAttribValue("entity")
                    if curType in ["step"]:
                        if parentNode.parm("defaultCategory").eval():
                            import ast

                            try:
                                steps = ast.literal_eval(
                                    self.core.getConfig(
                                        "globals",
                                        "pipeline_steps",
                                        configPath=self.core.prismIni,
                                    )
                                )
                            except:
                                continue

                            if type(steps) != dict:
                                steps = {}

                            steps = {
                                validSteps: steps[validSteps] for validSteps in steps
                            }
                            stepName = upstreamItem.stringAttribValue("name")
                            if stepName not in steps:
                                continue

                            catName = steps[stepName]
                        else:
                            catName = parentNode.parm("categoryName").eval()

                        item = itemHolder.addWorkItem(
                            cloneResultData=True, preserveType=True, parent=upstreamItem
                        )
                        item.setStringAttrib("entity", "category")
                        item.setStringAttrib(
                            "step", upstreamItem.stringAttribValue("name")
                        )
                        item.setStringAttrib("name", catName)

        elif entity == 6:
            for upstreamItem in upstreamItems:
                with upstreamItem.makeActive():
                    curType = upstreamItem.stringAttribValue("entity")
                    if curType in ["category"]:
                        item = itemHolder.addWorkItem(
                            cloneResultData=True, preserveType=True, parent=upstreamItem
                        )
                        item.setStringAttrib("entity", "scenefile")
                        if self.core.useLocalFiles:
                            item.setStringAttrib("location", "global")

                        item.setStringAttrib(
                            "category", upstreamItem.stringAttribValue("name")
                        )
                        item.setStringAttrib(
                            "source", parentNode.parm("scenefileSource").eval()
                        )
                        item.setStringAttrib(
                            "comment", parentNode.parm("scenefileComment").eval()
                        )
                        item.setStringAttrib(
                            "existingBehavior", parentNode.parm("existingSceneBehavior").evalAsString()
                        )

    @err_decorator
    def writeEntity(self, workItem):
        data = workItem.data.allDataMap
        if "entity" not in data:
            return "Error - invalid workitem"

        result = self.core.createEntity(entity=data)

        if result and workItem.stringAttribValue("entity") == "scenefile":
            # workItem.addResultData(result, "scenePath", 0)
            workItem.setStringAttrib("scenePath", result.replace("\\", "/"))

        return result

    @err_decorator
    def combineStates(self, pdgCallback, itemHolder, upstreamItems):
        parentNode = hou.nodeBySessionId(pdgCallback.customId).parent()
        entities = []

        up_items = upstreamItems
        for item in up_items:
            with upstreamItem.makeActive():
                unique = parentNode.parm("uniqueEntities").eval()
                combineStates = parentNode.parm("combineStates").eval()
                if not unique:
                    data = item.data.allDataMap
                    states = data.get("states", [])
                    entities.append({"item": item, "states": states})
                    continue

                for e in entities:
                    itemData = item.data.allDataMap
                    eData = e["item"].data.allDataMap

                    iStates = itemData.pop("states", None) or []
                    eStates = eData.pop("states", None) or []
                    if itemData == eData:
                        if combineStates:
                            e["states"] += iStates
                        break
                else:
                    data = item.data.allDataMap
                    states = data.get("states", [])
                    entities.append({"item": item, "states": states})

        for e in entities:
            item = itemHolder.addWorkItem(
                cloneResultData=True, preserveType=True, parent=e["item"]
            )
            if "states" in e:
                item.setStringAttrib("states", e["states"])

    @err_decorator
    def showStateUI(self, node):
        stateType = node.parm("stateType").evalAsString()

        import StateManager

        settings = node.parm("stateSettings").eval()
        try:
            settings = eval("{%s}" % settings.replace("=", ":"))
        except Exception as e:
            settings = {}

        settings = StateManager.openStateSettings(self.core, stateType, settings=settings)
        if settings:
            # connectedNodes is not used in Maya
            if node.parm("dcc").evalAsString() == "maya" and stateType == "default_Export":
                settings.pop("connectednodes")

            sLines = ['"%s" = "%s",' % (key, value) for (key, value) in sorted(settings.items(), key=lambda x: x[0])]
            settingsStr = '\n'.join(sLines)
            node.parm("stateSettings").set(settingsStr)

    @err_decorator
    def getAvailableStateDCCs(self):
        dccs = [
            "houdini", "Houdini",
            "maya", "Maya",
        ]

        return dccs

    @err_decorator
    def getAvailableStateTypes(self, node):
        dcc = node.parm("dcc").evalAsString()

        if dcc == "houdini":
            options = [
                "Folder", "Folder",
                "hou_ImportFile", "Import",
                "hou_Export", "Export",
                "hou_Playblast", "Playblast",
                "hou_ImageRender", "ImageRender",
                "hou_Dependency", "Dependency"
            ]
        elif dcc == "maya":
            options = [
                "Folder", "Folder",
                "default_ImportFile", "Import",
                "default_Export", "Export",
                "default_Playblast", "Playblast",
                "default_ImageRender", "ImageRender",
            ]
        else:
            options = []

        return options

    @err_decorator
    def createState(self, pdgCallback, itemHolder, upstreamItems):
        parentNode = hou.nodeBySessionId(pdgCallback.customId).parent()
        imports = []

        for upstreamItem in upstreamItems:
            with upstreamItem.makeActive():
                className = parentNode.parm("stateType").evalAsString()
                execute = parentNode.parm("execState").eval()
                usePreScript = parentNode.parm("usePreScript").eval()
                preScript = parentNode.parm("preScript").eval()
                usePostScript = parentNode.parm("usePostScript").eval()
                postScript = parentNode.parm("postScript").eval()
                settings = parentNode.parm("stateSettings").eval().replace("\n", "")

                if (
                    className in ["default_ImportFile", "hou_ImportFile"]
                    and parentNode.parm("importFromInput").eval()
                ):
                    if upstreamItem.intAttribValue("second_input"):
                        states = upstreamItem.stringAttribArray("states")
                        if not parentNode.parm("ignoreInputEntity").eval():
                            assetName = upstreamItem.stringAttribValue("entityName")
                            shotName = upstreamItem.stringAttribValue("entityName")
                        if states:
                            for state in states:
                                stateData = eval(state)
                                if "settings" in stateData:
                                    stateDict = eval(
                                        "{%s}" % stateData["settings"].replace("=", ":")
                                    )
                                    if parentNode.parm("ignoreInputEntity").eval():
                                        if (
                                            "taskname" in stateDict
                                            and stateDict["taskname"] not in imports
                                        ):
                                            imports.append(stateDict["taskname"])
                                    else:
                                        if assetName:
                                            entity = "asset"
                                            entityName = assetName
                                        elif shotName:
                                            entity = "shot"
                                            entityName = shotName
                                        elif "imports" in stateData:
                                            imports += stateData["imports"]
                                        else:
                                            continue

                                        if "taskname" in stateDict:
                                            imports.append(
                                                "%s|%s|%s"
                                                % (
                                                    entity,
                                                    entityName,
                                                    stateDict["taskname"],
                                                )
                                            )

        for upstreamItem in upstreamItems:
            with upstreamItem.makeActive():
                className = parentNode.parm("stateType").evalAsString()
                execute = parentNode.parm("execState").eval()
                usePreScript = parentNode.parm("usePreScript").eval()
                preScript = parentNode.parm("preScript").eval()
                usePostScript = parentNode.parm("usePostScript").eval()
                postScript = parentNode.parm("postScript").eval()
                settings = parentNode.parm("stateSettings").eval().replace("\n", "")

                if upstreamItem.intAttribValue("second_input"):
                    continue

                item = itemHolder.addWorkItem(
                    cloneResultData=True, preserveType=True, parent=upstreamItem
                )

                overrideSettings = ""
                for orId in range(parentNode.parm("overrideSettings").eval()):
                    orSetting = parentNode.parm("orSetting%s" % (orId + 1)).eval()
                    orVal = parentNode.parm("orValue%s" % (orId + 1)).eval()
                    overrideSettings += '"%s" = "%s",' % (orSetting, orVal)

                curStates = item.attribArray("states") or []
                stateData = {
                    "stateType": className,
                    "execute": execute,
                    "settings": settings,
                    "overrideSettings": overrideSettings,
                }

                if execute:
                    if usePreScript:
                        stateData["preScript"] = preScript.replace("\n", "\\n")
                    if usePostScript:
                        stateData["postScript"] = postScript.replace("\n", "\\n")

                if className == "default_Export":
                    stateData["stateObjects"] = []
                    for orId in range(parentNode.parm("stateObjects").eval()):
                        objName = parentNode.parm("stateObject%s" % (orId + 1)).eval()
                        stateData["stateObjects"].append(objName)

                if imports:
                    if parentNode.parm("ignoreInputEntity").eval():
                        assetName = upstreamItem.stringAttribValue("entityName")
                        shotName = upstreamItem.stringAttribValue("entityName")

                        if assetName:
                            entity = "asset"
                            entityName = assetName
                        elif shotName:
                            entity = "shot"
                            entityName = shotName
                        else:
                            continue

                        lImports = ["%s|%s|%s" % (entity, entityName, x) for x in imports]
                    else:
                        lImports = imports

                    stateData["imports"] = lImports

                curStates.append(str(stateData))
                item.setStringAttrib("states", curStates)

    @err_decorator
    def createDependencies(self, pdgCallback, itemHolder):
        parentNode = hou.nodeBySessionId(pdgCallback.customId).parent()
        className = "hou_ImportFile"
        execute = 1
        settings = ""
        dependencyStr = parentNode.parm("dependencies").eval()
        dependencies = dependencyStr.split("\n")
        imports = []

        for dep in dependencies:
            if len(dep) == 0:
                continue

            if dep[0] == "#":
                continue

            imports.append(dep)

        item = itemHolder.addWorkItem(cloneResultData=True, preserveType=True)

        stateData = {"stateType": className, "execute": execute, "settings": settings}
        if imports:
            stateData["imports"] = imports

        item.setStringAttrib("states", [str(stateData)])

    @err_decorator
    def setProject(self, workItem):
        typeStr = workItem.stringAttribValue("entity")
        if typeStr != "project":
            return

        prjPath = workItem.stringAttribValue("path")
        self.core.changeProject(prjPath)

    @err_decorator
    def scenePython(self, pdgCallback, itemHolder, upstreamItems):
        parentNode = hou.nodeBySessionId(pdgCallback.customId).parent()
        mayaTasks = []
        houTasks = []
        procs = []

        for upstreamItem in upstreamItems:
            path = upstreamItem.stringAttribValue("scenePath")
            if not path:
                self.core.popup(
                    "Unable to read scene. Workitem doesn't contain a scenepath."
                )
                continue

            mayaFormats = self.core.getPluginData("Maya", "sceneFormats")
            houdiniFormats = self.core.getPluginData("Houdini", "sceneFormats")
            with upstreamItem.makeActive():
                cmd = parentNode.parm("script").eval()
                if parentNode.parm("saveScene").eval():
                    cmd += "\npcore.saveScene(comment=\"python executed (PDG)\", versionUp=True)\n"
                doExecute = parentNode.parm("executeOnCook").eval()

            item = itemHolder.addWorkItem(
                cloneResultData=True, preserveType=True, parent=upstreamItem
            )

            if doExecute:
                if os.path.splitext(path)[1] in mayaFormats:
                    mayaTasks.append({"path": path, "command": cmd})
                elif os.path.splitext(path)[1] in houdiniFormats:
                    houTasks.append({"path": path, "command": cmd})
            else:
                item.setStringAttrib("scenePythonScript", cmd)

        if mayaTasks:
            mayaPath = upstreamItems[0].envLookup("PDG_MAYAPY")
            if not mayaPath or not os.path.exists(mayaPath):
                print ("The PDG_MAYAPY environment variable doesn't exist or doesn't contain a Maya executable.")
                return False

            mayaCmd = self.getMayaCmd([x["path"] for x in mayaTasks], pythonSnippet=cmd)
            procs.append({"executable": mayaPath, "command": mayaCmd})

        if houTasks:
            hython = os.path.join(os.environ["HB"], "hython.exe")
            if not hython or not os.path.exists(hython):
                print ("Couldn't find the hython executable.")
                return False

            houCmd = self.getHoudiniCmd([x["path"] for x in houTasks], pythonSnippet=cmd)
            procs.append({"executable": hython, "command": houCmd})

        if not procs:
            return True

        stdout = self.openScenefiles(procs)

        if "Scene was processed successfully" not in stdout:
            return False
        else:
            print("Completed scene python execution.")

        return True

    @err_decorator
    def writeStates(self, pdgCallback, itemHolder, upstreamItems):
        mayaPaths = []
        houPaths = []
        sceneStates = []
        for workItem in upstreamItems:
            # path = workItem.resultDataForTag("scenePath")
            path = [[workItem.stringAttribValue("scenePath")]]
            if not path:
                self.core.popup(
                    "Unable to write states. Workitem doesn't contain a scenepath."
                )
                continue

            states = workItem.stringAttribArray("states")
            if not states:
                self.core.popup(
                    "Unable to write states. Workitem doesn't contain states."
                )
                continue

            if os.path.splitext(path[0][0])[1] in self.core.getPluginData(
                "Maya", "sceneFormats"
            ):
                mayaPaths.append(path[0][0])
                sceneStates = map(lambda x: eval(x), states)
            elif os.path.splitext(path[0][0])[1] in self.core.getPluginData(
                "Houdini", "sceneFormats"
            ):
                houPaths.append(path[0][0])
                sceneStates = map(lambda x: eval(x.replace("\\", "\\\\\\")), states)

    #    for sc in sceneStates:
    #        if "preScript" in sc:
    #            sc["preScript"] = sc["preScript"].replace("\\n", "\n")
    #        if "postScript" in sc:
    #            sc["postScript"] = sc["postScript"].replace("\\n", "\n")
    #        if "pythonSnippet" in sc:
    #            sc["pythonSnippet"] = sc["pythonSnippet"].replace("\\n", "\n")

        procs = []
        if mayaPaths:
            mayaPath = upstreamItems[0].envLookup("PDG_MAYAPY")
            if not mayaPath or not os.path.exists(mayaPath):
                print ("The PDG_MAYAPY environment variable doesn't exist or doesn't contain a Maya executable.")
                return False

            mayaCmd = self.getMayaCmd(mayaPaths, sceneStates=sceneStates)
            procs.append({"executable": mayaPath, "command": mayaCmd})

        if houPaths:
            hython = os.path.join(os.environ["HB"], "hython.exe")
            if not hython or not os.path.exists(hython):
                print ("Couldn't find the hython executable.")
                return False

            houCmd = self.getHoudiniCmd(houPaths, sceneStates=sceneStates)
            procs.append({"executable": hython, "command": houCmd})

        stdout = self.openScenefiles(procs)

        for upstreamItem in upstreamItems:
            item = itemHolder.addWorkItem(
                cloneResultData=True, preserveType=True, parent=upstreamItem
            )
            item.eraseAttrib("states")

        if "Scene was processed successfully" not in stdout:
            return False
        else:
            print("Completed state creations.")

        return True

    @err_decorator
    def openScenefiles(self, tasks):
        stdout = ""
        for i in tasks:
            if True:  # if `@debug`:
                print("starting %s" % os.path.basename(i["executable"]))
                proc = subprocess.Popen(
                    [i["executable"], "-c", i["command"]], stdout=subprocess.PIPE
                )
                for line in proc.stdout:
                    line = "[stdout] %s" % line.replace("\n", "")
                    sys.stdout.write(line)
                    stdout += line

                proc.wait()
            else:
                proc = subprocess.Popen([i["executable"], "-c", i["command"]])
                stdout, stderr = proc.communicate()

        return stdout

    @err_decorator
    def getMayaCmd(self, mayaPaths, sceneStates="", pythonSnippet=""):
        cmd = """
import sys
from PySide2.QtCore import *
from PySide2.QtWidgets import *
QApplication(sys.argv)

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds

import PrismInit
pcore = PrismInit.prismInit(prismArgs=["noUI"])

scenePathsStr = "%s"
scenePaths = eval(scenePathsStr) if scenePathsStr else ""
pythonSnippet = \"\"\"%s\"\"\"

print ("processing scenes: %%s" %% scenePaths)
for scenePath in scenePaths:
    try:
        cmds.file( scenePath, o=True, force=True, ignoreVersion=True )
    except:
        if pcore.getCurrentFileName() == "":
            print ("Couldn't load file. Loading all plugins and trying again.")
            cmds.loadPlugin( allPlugins=True )
            cmds.file( scenePath, o=True, force=True, ignoreVersion=True )

    if pcore.getCurrentFileName() == "":
        print ("failed to load file: %%s" %% scenePath)
    else:
        print ("loaded file: %%s" %% scenePath)

        if pythonSnippet:
            exec(pythonSnippet)

        stateStr = \"\"\"%s\"\"\"
        states = eval(stateStr) if stateStr else ""
        if states:
            stateManager = pcore.stateManager()
            for idx, state in enumerate(states):
                settings = state["settings"]
                try:
                    settings = eval("{%%s}" %% settings.replace("=", ":"))
                except Exception as e:
                    settings = {}

                if "overrideSettings" in state:
                    orSettings = state["overrideSettings"]
                    try:
                        orSettings = eval("{%%s}" %% orSettings.replace("=", ":"))
                    except Exception as e:
                        orSettings = {}

                    settings.update(orSettings)

                if "imports" in state and state["imports"]:
                    settings["filepath"] = pcore.resolve(state["imports"][0])

                if "preScript" in state:
                    print (state["preScript"])
                    pcore.appPlugin.executeScript(pcore, state["preScript"], execute=True)

                stateNameBase = state["stateType"].replace(state["stateType"].split("_", 1)[0] + "_", "")
                stateItem = stateManager.createState(stateNameBase, stateData=settings)
                if state["execute"]:
                    if stateItem.ui.listType == "Import":
                        getattr(stateItem.ui, "importObject", lambda: None)()
                    elif stateItem.ui.listType == "Export":
                        stateManager.publish(executeState=True, states=[stateItem])
                    print ("executed state %%s: %%s" %% (idx, stateNameBase))

                if "postScript" in state:
                    pcore.appPlugin.executeScript(pcore, state["postScript"], execute=True)

            pcore.saveScene(comment=\"state added (PDG)\", versionUp=True)

    print ("Scene was processed successfully")

        """ % (
            mayaPaths,
            pythonSnippet,
            sceneStates,
        )
        return cmd

    @err_decorator
    def getHoudiniCmd(self, houPaths, sceneStates="", pythonSnippet=""):
        cmd = """
import os, sys
import hou

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

QApplication.addLibraryPath(os.path.join(hou.expandString("$HFS"), "bin", "Qt_plugins"))
qApp = QApplication.instance()
if qApp is None:
    qApp = QApplication(sys.argv)

import PrismInit
pcore = PrismInit.prismInit(prismArgs=["noUI"])

scenePathsStr = "%s"
scenePaths = eval(scenePathsStr) if scenePathsStr else ""
pythonSnippet = \"\"\"%s\"\"\"

print ("processing scenes: %%s" %% scenePaths)
for scenePath in scenePaths:
    hou.hipFile.load(file_name=scenePath, ignore_load_warnings=True)

    if pcore.getCurrentFileName() == "":
        print ("failed to load file: %%s" %% scenePath)
    else:
        print ("loaded file: %%s" %% scenePath)

        if pythonSnippet:
            print ("exec python snippet: %%s" %% pythonSnippet)
            exec(pythonSnippet)

        stateStr = \"\"\"%s\"\"\"
        states = eval(stateStr) if stateStr else ""
        if states:
            for idx, state in enumerate(states):
                settings = state["settings"]
                try:
                    settings = eval("{%%s}" %% settings.replace("=", ":"))
                except Exception as e:
                    settings = {}

                if "overrideSettings" in state:
                    orSettings = state["overrideSettings"]
                    try:
                        orSettings = eval("{%%s}" %% orSettings.replace("=", ":"))
                    except Exception as e:
                        orSettings = {}

                    settings.update(orSettings)

                if "imports" in state and state["imports"]:
                    settings["filepath"] = pcore.resolve(state["imports"][0])

                if "preScript" in state:
                    pScript = state["preScript"].replace("\\\\", "")
                    pScript = "import PrismInit;pcore = PrismInit.pcore\\n" + pScript
                    print("Pre-creation script: " + pScript)
                    pcore.appPlugin.executeScript(pcore, pScript, execute=True)

                stateNameBase = state["stateType"].replace(state["stateType"].split("_", 1)[0] + "_", "")
                stateManager = pcore.stateManager()
                stateItem = stateManager.createState(stateNameBase, stateData=settings)

                if "stateObjects" in state:
                    stateItem.ui.addObjects(state["stateObjects"])

                if "postScript" in state:
                    pScript = state["postScript"].replace("\\\\", "")
                    pScript = "import PrismInit;pcore = PrismInit.pcore\\n" + pScript
                    pcore.appPlugin.executeScript(pcore, pScript, execute=True)

                if state["execute"]:
                    if stateItem.ui.listType == "Import":
                        getattr(stateItem.ui, "importObject", lambda: None)()
                    elif stateItem.ui.listType == "Export":
                        stateManager.publish(executeState=True, states=[stateItem])
                    print ("executed state %%s: %%s" %% (idx, stateNameBase))

            pcore.saveScene(comment=\"state added (PDG)\", versionUp=True)

    print ("Scene was processed successfully")

        """ % (
            houPaths,
            pythonSnippet,
            sceneStates,
        )
        return cmd
