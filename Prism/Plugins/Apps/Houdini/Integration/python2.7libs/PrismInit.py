import os
import sys


def prismInit(prismArgs=[]):
    Dir = os.path.join(
        os.path.abspath(
            os.path.join(
                __file__,
                os.pardir,
                os.pardir,
                os.pardir,
                os.pardir,
                os.pardir,
                os.pardir,
                "Scripts",
            )
        )
    )

    if Dir not in sys.path:
        sys.path.append(Dir)

    if "hython" in os.path.basename(sys.executable).lower() and "noUI" not in prismArgs:
        prismArgs.append("noUI")

    import PrismCore

    pcore = PrismCore.PrismCore(app="Houdini", prismArgs=prismArgs)
    return pcore


def createPrismCore():
    try:
        import PySide2
    except:
        return

    global pcore
    pcore = prismInit()
