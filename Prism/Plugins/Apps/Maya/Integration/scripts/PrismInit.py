import os
import sys
from maya import OpenMaya as omya

pcore = None
_init_scheduled = False


def prismInit(prismArgs=None, quiet=False, skipBatch=False):
    global _init_scheduled

    if prismArgs is None:
        prismArgs = []

    if omya.MGlobal.mayaState() == omya.MGlobal.kBatch and skipBatch:
        return

    if pcore:
        if not quiet:
            try:
                from PySide6 import QtWidgets
            except:
                from PySide2 import QtWidgets

            msg = "Prism is loaded multiple times. This can cause unexpected errors. Please clean all Prism related content from the userSetup.py in your Maya user preferences.\n\nYou can add a new Prism integration through the Prism Settings dialog."
            QtWidgets.QMessageBox.warning(None, "Prism Warning", msg)

        return pcore
    elif _init_scheduled:
        return
    elif sys.version_info.major == 2:
        if not quiet:
            import PySide2
            msg = "Prism supports only Python 3 versions of Maya.\nPython 3 is the default in Maya 2022 and later."
            PySide2.QtWidgets.QMessageBox.warning(None, "Prism Warning", msg)

        return

    prismRoot = os.getenv("PRISM_ROOT")
    if not prismRoot:
        msg = "PRISM_ROOT env var is not defined. Please reinstall the Prism integration"
        raise Exception(msg)

    import maya.cmds as cmds
    if cmds.about(batch=True):
        try:
            from PySide6 import QtWidgets
        except:
            from PySide2 import QtWidgets

        qapp = QtWidgets.QApplication.instance()
        if not isinstance(qapp, QtWidgets.QApplication):
            print("Cannot create Prism instance because no QApplication exists. To load Prism you can create a QApplication before initilizing mayapy like this: import sys;from PySide2 import QtWidgets;QtWidgets.QApplication(sys.argv)")
            return

        if not qapp:
            QtWidgets.QApplication(sys.argv)

        prismArgs.append("noUI")

    scriptDir = os.path.join(prismRoot, "Scripts")

    if scriptDir not in sys.path:
        sys.path.append(scriptDir)

    _init_scheduled = True
    deferredArgs = list(prismArgs)
    if cmds.about(batch=True):
        _deferredPrismInit(deferredArgs)
    else:
        import maya.utils
        maya.utils.executeDeferred(lambda: _deferredPrismInit(deferredArgs))

    return pcore


def _deferredPrismInit(prismArgs):
    global _init_scheduled
    try:
        import PrismCore
        global pcore
        if pcore:
            return

        pcore = PrismCore.PrismCore(app="Maya", prismArgs=prismArgs)
        mainModule = sys.modules.get("__main__")
        if mainModule is not None:
            mainModule.pcore = pcore

    except Exception:
        import traceback
        print("Error occured while loading Prism:\n\n%s" % traceback.format_exc())
    finally:
        _init_scheduled = False
