import os
import sys


def prismInit(prismArgs=[]):
    if "PRISM_ROOT" in os.environ:
        prismRoot = os.environ["PRISM_ROOT"]
        if not prismRoot:
            return
    else:
        prismRoot = PRISMROOT

    import maya.cmds as cmds
    if cmds.about(batch=True):
        from PySide2 import QtWidgets
        qapp = QtWidgets.QApplication.instance()
        if not isinstance(qapp, QtWidgets.QApplication):
            print("Cannot create Prism instance because no QApplication exists. To load Prism you can create a QApplication before initilizing mayapy like this: import sys;from PySide2 import QtWidgets;QtWidgets.QApplication(sys.argv)")
            return

        if not qapp:
            QtWidgets.QApplication(sys.argv)

    scriptDir = os.path.join(prismRoot, "Scripts")

    if scriptDir not in sys.path:
        sys.path.append(scriptDir)

    import PrismCore

    global pcore
    pcore = PrismCore.PrismCore(app="Maya", prismArgs=prismArgs)
    return pcore
