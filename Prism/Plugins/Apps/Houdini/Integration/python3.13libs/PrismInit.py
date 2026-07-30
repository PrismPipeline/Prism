import os
import sys
import platform


def prismInit(prismArgs=[]):
    if "hython" in os.path.basename(sys.executable).lower():
        if "noUI" not in prismArgs:
            prismArgs.append("noUI")

        if platform.system() == "Linux":
            os.environ["QT_QPA_PLATFORM"] = "offscreen"

        import hou
        psBase = os.path.join(hou.text.expandString("$HFS"), "python313/lib/site-packages-forced")
        if os.path.exists(psBase + "/PySide6"):
            from PySide6.QtWidgets import QApplication
        elif os.path.exists(psBase + "/PySide2"):
            from PySide2.QtWidgets import QApplication
        else:
            try:
                from PySide6.QtWidgets import QApplication
            except:
                from PySide2.QtWidgets import QApplication

        if platform.system() == "Windows":
            qtPath = os.path.join(hou.text.expandString("$HFS"), "bin", "Qt_plugins")
        else:
            qtPath = os.path.join(hou.text.expandString("$HFS"), "dsolib", "Qt_plugins")

        QApplication.addLibraryPath(qtPath)
        if not QApplication.instance():
            QApplication(sys.argv)

    root = os.getenv("PRISM_ROOT", "")
    if not root:
        if not os.getenv("PRISM_STANDALONE_KARMA", ""):
            try:
                from PySide6 import QtWidgets
            except:
                from PySide2 import QtWidgets

            QtWidgets.QMessageBox.warning(None, "Prism", "The environment variable \"PRISM_ROOT\" is not defined. Try to setup the Prism Houdini integration again from the DCC apps tab in the Prism User Settings.")

        return

    if os.pathsep in root:
        root = root.split(os.pathsep)[0]

    scriptPath = os.path.join(root, "Scripts")
    if scriptPath not in sys.path:
        sys.path.append(scriptPath)

    import PrismCore
    pcore = PrismCore.PrismCore(app="Houdini", prismArgs=prismArgs)
    return pcore


def createPrismCore():
    if os.getenv("PRISM_ENABLED") == "0":
        return

    if "usdview" in sys.argv:
        return
    
    try:
        import PySide6
    except:
        try:
            import PySide2
        except:
            return

    global pcore
    pcore = prismInit()
