import os
import sys


def prismInit():
    prismRoot = os.getenv("PRISM_ROOT")
    if not prismRoot:
        prismRoot = PRISMROOT

    scriptDir = os.path.join(prismRoot, "Scripts")

    if scriptDir not in sys.path:
        sys.path.append(scriptDir)

    import PrismCore

    pcore = PrismCore.PrismCore(app="PluginEmtpy")
    return pcore
