import os
import sys
import logging

logger = logging.getLogger(__name__)
logging.basicConfig()
logging.root.setLevel("INFO")

libPath = os.getenv("PRISM_LIBS")
if not libPath:
    libPath = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir))

modulePath = os.path.join(libPath, "PythonLibs", "CrossPlatform")
sys.path.insert(0, modulePath)

pipPath = os.path.join(libPath, "PythonLibs", "CrossPlatform", "PrismModules")
sys.path.insert(0, pipPath)

lib27Path = os.path.join(libPath, "PythonLibs", "Python27")
sys.path.append(lib27Path)

pysidePath = os.path.join(libPath, "PythonLibs", "Python27", "PySide")
sys.path.append(pysidePath)


def installPackage(package, targetPath):
    logger.info("Install package: %s - %s" % (package, targetPath))
    from PrismModules.pip import _internal
    _internal.main(["install", package, "-t", targetPath])


if __name__ == '__main__':
    try:
        import PySide2
    except:
        try:
            import PySide
        except:
            installPackage("PySide2 <5.15.0", pysidePath)

    try:
        import psutil
    except:
        installPackage("psutil", lib27Path)
