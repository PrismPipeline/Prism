
# >>>PrismStart
import sys
from maya import OpenMaya as omya

if omya.MGlobal.mayaState() != omya.MGlobal.kBatch:
    if "pcore" in locals() and pcore:
        import PySide2
        PySide2.QtWidgets.QMessageBox.warning(None, "Prism Warning", "Prism is loaded multiple times. This can cause unexpected errors. Please clean all Prism related content from the userSetup.py in your Maya user preferences.\n\nYou can add a new Prism integration through the Prism Settings dialog.")
    elif sys.version[0] == "2":
        import PySide2
        PySide2.QtWidgets.QMessageBox.warning(None, "Prism Warning", "Prism supports only Python 3 versions of Maya.\nPython 3 is the default in Maya 2022 and later.")

    else:
        try:
            import PrismInit
            pcore = PrismInit.prismInit()
        except:
            import traceback
            print("Error occured while loading Prism:\n\n%s" % traceback.format_exc())
# <<<PrismEnd
