import os


def load_stylesheet():
    sFile = os.path.dirname(__file__) + "/Blender2.8.qss"
    if not os.path.exists(sFile):
        return ""

    with open(sFile, "r") as f:
        stylesheet = f.read()

    stylesheet = stylesheet.replace("qss:", os.path.dirname(__file__).replace("\\", "/") + "/")
    return stylesheet
