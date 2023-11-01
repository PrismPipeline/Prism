import os


def load_stylesheet():
    sFile = os.path.dirname(__file__) + "/Photoshop.qss"
    if not os.path.exists(sFile):
        return ""

    with open(sFile, "r") as f:
        stylesheet = f.read()

    stylesheet = stylesheet.replace("qss:", os.path.dirname(__file__).replace("\\", "/") + "/")
    return stylesheet
