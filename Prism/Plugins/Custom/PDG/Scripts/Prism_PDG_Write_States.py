import sys, os, subprocess, threading

def writeStates(pcore, work_items, mayaPath=None):
	mpy = mayaPath or "C:/Program Files/Autodesk/Maya2018/bin/mayapy.exe"
	hython = os.path.join(os.environ["HB"], "hython.exe")
	mayaPaths = []
	houPaths = []
	sceneStates = []
	for work_item in work_items:
		path = work_item.resultDataForTag("scenePath")
		states = work_item.data.stringDataArray("states")
		if not path or not states:
			continue

		if os.path.splitext(path[0][0])[1] in pcore.getPluginData("Maya", "sceneFormats"):
			mayaPaths.append(path[0][0])
			sceneStates = map(lambda x: eval(x.replace("\\", "\\\\\\\\\\")), states)
		elif os.path.splitext(path[0][0])[1] in pcore.getPluginData("Houdini", "sceneFormats"):
			houPaths.append(path[0][0])
			sceneStates = map(lambda x: eval(x.replace("\\", "\\\\\\")), states)

	procs = []
	if mayaPaths:
		mayaCmd = getMayaCmd(mayaPaths, sceneStates)
		procs.append({"executable":mpy, "command": mayaCmd})

	if houPaths:
		houCmd = getHoudiniCmd(houPaths, sceneStates)
		procs.append({"executable":hython, "command": houCmd})

	if not hasattr(threading, "__mylock"):
		threading.__mylock = threading.Lock()

	with threading.__mylock:
		stdout = ""
		for i in procs:
			if True: #if `@debug`:
				print "starting %s" % os.path.basename(i["executable"])
				proc = subprocess.Popen([i["executable"], "-c", i["command"]], stdout=subprocess.PIPE)
				for line in proc.stdout:
					line = "[stdout] %s" % line.replace("\n", "")
					sys.stdout.write(line)
					stdout += line
					
				proc.wait()
			else:
				proc = subprocess.Popen([i["executable"], "-c", i["command"]])
				stdout, stderr = proc.communicate()
			
	if "Scene was processed successfully" not in stdout:
		raise RuntimeError
	else:
		print "Completed state creations."


def getMayaCmd(mayaPaths, sceneStates):
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
scenePaths = eval("%s")
print "processing scenes: %%s" %% scenePaths
for scenePath in scenePaths:
	try:
		cmds.file( scenePath, o=True, force=True, ignoreVersion=True )
	except:
		if pcore.getCurrentFileName() == "":
			print "Couldn't load file. Loading all plugins and trying again."
			cmds.loadPlugin( allPlugins=True )
			cmds.file( scenePath, o=True, force=True, ignoreVersion=True )

	if pcore.getCurrentFileName() == "":
		print ("failed to load file: %%s" %% scenePath)
	else:
		print ("loaded file: %%s" %% scenePath)
		
		stateManager = pcore.stateManager()
		states = eval(\"\"\"%s\"\"\")
		for idx, state in enumerate(states):
			settings = state["settings"]
			try:
				settings = eval("{%%s}" %% settings.replace("=", ":"))
			except Exception as e:
				settings = {}
				
			if "imports" in state and state["imports"]:
				settings["filepath"] = pcore.resolve(state["imports"][0])
			
			if "preScript" in state:
				pcore.appPlugin.executeScript(pcore, state["preScript"], execute=True)
				
			stateNameBase = state["stateType"].replace(state["stateType"].split("_", 1)[0] + "_", "")
			stateItem = stateManager.createState(stateNameBase, stateData=settings)
			if state["execute"]:
				if stateItem.ui.listType == "Import":
					getattr(stateItem.ui, "importObject", lambda: None)()
				elif stateItem.ui.listType == "Export":
					stateManager.publish(executeState=True, states=[stateItem])
				print "executed state %%s: %%s" %% (idx, stateNameBase)
				
			if "postScript" in state:
				pcore.appPlugin.executeScript(pcore, state["postScript"], execute=True)
				
		pcore.saveScene(versionUp=False)
		
	print "Scene was processed successfully"

	""" % (mayaPaths, sceneStates)
	return cmd

def getHoudiniCmd(houPaths, sceneStates):
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

scenePaths = eval("%s")
print "processing scenes: %%s" %% scenePaths
for scenePath in scenePaths:
	hou.hipFile.load(file_name=scenePath, ignore_load_warnings=True)

	if pcore.getCurrentFileName() == "":
		print ("failed to load file: %%s" %% scenePath)
	else:
		print ("loaded file: %%s" %% scenePath)
		
		stateManager = pcore.stateManager()
		states = eval(\"\"\"%s\"\"\")
		for idx, state in enumerate(states):
			settings = state["settings"]
			try:
				settings = eval("{%%s}" %% settings.replace("=", ":"))
			except Exception as e:
				settings = {}
				
			if "imports" in state and state["imports"]:
				settings["filepath"] = pcore.resolve(state["imports"][0])
			
			if "preScript" in state:
				print state["preScript"]
				pcore.appPlugin.executeScript(pcore, state["preScript"], execute=True)
				
			stateNameBase = state["stateType"].replace(state["stateType"].split("_", 1)[0] + "_", "")
			stateItem = stateManager.createState(stateNameBase, stateData=settings)

			if "postScript" in state:
				pcore.appPlugin.executeScript(pcore, state["postScript"], execute=True)
				
			if state["execute"]:
				if stateItem.ui.listType == "Import":
					getattr(stateItem.ui, "importObject", lambda: None)()
				elif stateItem.ui.listType == "Export":
					stateManager.publish(executeState=True, states=[stateItem])
				print "executed state %%s: %%s" %% (idx, stateNameBase)
				
		pcore.saveScene(versionUp=False)
		
	print "Scene was processed successfully"

	""" % (houPaths, sceneStates)
	return cmd