import os
import sys


def prismInit(prismArgs=[]):
    root = os.getenv("PRISM_ROOT", "")
    if not root:
        if not os.getenv("PRISM_STANDALONE_KARMA", ""):
            from PySide2 import QtWidgets
            QtWidgets.QMessageBox.warning(None, "Prism", "The environment variable \"PRISM_ROOT\" is not defined. Try to setup the Prism Houdini integration again from the DCC apps tab in the Prism User Settings.")
        
        return

    scriptPath = os.path.join(root, "Scripts")
    if scriptPath not in sys.path:
        sys.path.append(scriptPath)

    if "hython" in os.path.basename(sys.executable).lower() and "noUI" not in prismArgs:
        prismArgs.append("noUI")

    import PrismCore

    pcore = PrismCore.PrismCore(app="Houdini", prismArgs=prismArgs)
    return pcore


def createPrismCore():
    if os.getenv("PRISM_ENABLED") == "0":
        return
    
    try:
        import PySide2
    except:
        return

    global pcore
    pcore = prismInit()
