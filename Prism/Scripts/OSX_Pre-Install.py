import os
import sys
import logging

logger = logging.getLogger(__name__)
logging.basicConfig()
logging.root.setLevel("INFO")

modulePath = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, "PythonLibs", "CrossPlatform"))
sys.path.insert(0, modulePath)

pipPath = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, "PythonLibs", "CrossPlatform", "PrismModules"))
sys.path.insert(0, pipPath)

targetPath = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, "PythonLibs", "Python27", "PySide"))
sys.path.append(targetPath)


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
            installPackage("PySide2 <5.15.0", targetPath)

    targetPath = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, "PythonLibs", "CrossPlatform"))
    sys.path.append(targetPath)
