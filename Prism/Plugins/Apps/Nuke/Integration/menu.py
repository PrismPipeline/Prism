# >>>PrismStart
import nuke

if not nuke.env["studio"] and nuke.env.get("gui"):
    if "pcore" in locals():
        nuke.message("Prism is loaded multiple times. This can cause unexpected errors. Please clean this file from all Prism related content:\n\n%s\n\nYou can add a new Prism integration through the Prism Settings dialog" % __file__)
    else:
        import os
        import sys

        prismRoot = os.getenv("PRISM_ROOT")
        if not prismRoot:
            prismRoot = PRISMROOT

        scriptDir = os.path.join(prismRoot, "Scripts")
        if scriptDir not in sys.path:
            sys.path.append(scriptDir)

        import PrismCore

        pcore = PrismCore.PrismCore(app="Nuke")
# <<<PrismEnd
