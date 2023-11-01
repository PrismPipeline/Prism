import os
import sys

from pymxs import runtime as rt


def prismInit():
    prismRoot = os.getenv("PRISM_ROOT")
    if not prismRoot:
        prismRoot = PRISMROOT

    scriptDir = os.path.join(prismRoot, "Scripts")
    if scriptDir not in sys.path:
        sys.path.append(scriptDir)

    import PrismCore
    global pcore
    pcore = PrismCore.PrismCore(app="3dsMax")


if "pcore" not in globals() and not rt.execute("IsNetServer()"):
    prismInit()
