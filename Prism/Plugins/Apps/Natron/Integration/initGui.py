# >>>PrismStart
if not NatronEngine.natron.isBackground():
    import os
    import sys

    prismRoot = os.getenv("PRISM_ROOT")
    if not prismRoot:
        prismRoot = PRISMROOT

    scriptDir = os.path.join(prismRoot, "Scripts")
    if scriptDir not in sys.path:
        sys.path.append(scriptDir)

    import PrismCore

    pcore = PrismCore.PrismCore(app="Natron")


def writePrismParamChanged(thisParam, thisNode, thisGroup, app, userEdited):
    pcore.appPlugin.wpParamChanged(thisParam, thisNode, thisGroup, app, userEdited)


# <<<PrismEnd
