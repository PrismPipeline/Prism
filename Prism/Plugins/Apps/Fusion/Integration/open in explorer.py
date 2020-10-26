import os
import sys

prismRoot = os.getenv("PRISM_ROOT")
if not prismRoot:
    prismRoot = PRISMROOT
	
sys.path.append(os.path.join(prismRoot, "Scripts"))
sys.path.append(os.path.join(prismRoot, "PythonLibs", "Python37", "PySide"))

try:
	from PySide2.QtCore import *
	from PySide2.QtGui import *
	from PySide2.QtWidgets import *
except:
	from PySide.QtCore import *
	from PySide.QtGui import *

qapp = QApplication.instance()
if qapp == None:
  qapp = QApplication(sys.argv)

import PrismCore
pcore = PrismCore.PrismCore(app='Fusion', prismArgs=["parentWindows"])
pcore.appPlugin.fusion = fusion

curPrj = pcore.getConfig('globals', 'current project')
if curPrj is not None and curPrj != "":
	pcore.changeProject(curPrj)
	tool = comp.ActiveTool
	try:
		versionPath = os.path.dirname(tool.GetAttrs()["TOOLST_Clip_Name"][1])
		if not os.path.exists(versionPath):
			versionPath = os.path.dirname(versionPath)
	except:
		versionPath = ""

	if os.path.exists(versionPath):
		pcore.openFolder(versionPath)
	else:
		msg = QMessageBox(QMessageBox.Warning, "Prism Warning", "The outputfolder doesn't exist yet.")
		pcore.parentWindow(msg)
		msg.exec_()
else:
	QMessageBox.warning(pcore.messageParent, "Prism warning", "No project is active.\nPlease set a project in the Prism Settings or by opening the Project Browser.")
