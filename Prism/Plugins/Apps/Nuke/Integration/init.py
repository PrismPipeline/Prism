# >>>PrismStart
import nuke

if not nuke.env["studio"] and not nuke.env.get("gui"):
    if "pcore" in locals():
        nuke.message("Prism is loaded multiple times. This can cause unexpected errors. Please clean this file from all Prism related content:\n\n%s\n\nYou can add a new Prism integration through the Prism Settings dialog" % __file__)
    else:
        import os
        import sys

        try:
            from PySide2.QtCore import *
            from PySide2.QtGui import *
            from PySide2.QtWidgets import *
        except:
            from PySide.QtCore import *
            from PySide.QtGui import *

        prismRoot = os.getenv("PRISM_ROOT")
        if not prismRoot:
            prismRoot = PRISMROOT

        scriptDir = os.path.join(prismRoot, "Scripts")
        if scriptDir not in sys.path:
            sys.path.append(scriptDir)

        qapp = QApplication.instance()
        if not qapp:
            qapp = QApplication(sys.argv)

        if isinstance(qapp, QCoreApplication):
            print("a QCoreApplication exists. failed to load Prism")
        else:
            print(qapp)
            import PrismCore

            pcore = PrismCore.PrismCore(app="Nuke", prismArgs=["noUI"])

# <<<PrismEnd