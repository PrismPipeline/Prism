import os


def load_stylesheet():
    sFile = os.path.dirname(__file__) + "/ComfyUI.qss"
    if not os.path.exists(sFile):
        return ""

    with open(sFile, "r") as f:
        stylesheet = f.read()

    ssheetDir = os.path.dirname(sFile)
    ssheetDir = ssheetDir.replace("\\", "/") + "/"

    repl = {
        "qss:": ssheetDir,
        "@mainBackground1": "rgb(24, 24, 27)",
        "@borders": "rgb(90, 90, 90)",
        "@tableHeader": "rgb(19, 19, 20)",
        "@selectionBackgroundColor": "rgb(96, 165, 250)",
        "@selectionBackgroundHoverColor": "rgb(168, 168, 168)",
        "@selectionHoverColor": "rgb(39, 39, 42)",
        "@selectionColor": "rgb(5, 5, 5)",
        "@menuBackground": "rgb(9, 9, 11)",
        "@menuhoverbackground": "rgb(39, 39, 42)",
        "@menuSelectionbackground": "rgb(23, 35, 49)",
        "@buttonBackgroundDefault": "rgb(49, 50, 53)",
        "@buttonBackgroundDisabled": "rgb(55, 55, 55)",
        "@buttonBackgroundHover": "rgb(77, 77, 77)",
        "@buttonBackgroundBright1": "rgb(67, 67, 67)",
        "@buttonBackgroundBright2": "rgb(26, 26, 26)",
        "@white": "rgb(250, 250, 250)",
        "@tableBackground": "rgb(32, 32, 32)",
        "@inputHover": "rgb(31, 31, 31)",
        "@inputBackground": "rgb(28, 28, 28)",
        "@inputFocus": "rgb(28, 28, 28)",
        "@test": "rgb(200, 49, 49)",
        "@lightgrey": "rgb(190, 190, 190)",
        "@disabledText": "rgb(105, 105, 105)",
        "@tableBorders": "rgb(90, 90, 90)",
        "@scrollHandleColor": "rgb(49, 49, 49)",
        "@scrollHandleHoverColor": "rgb(69, 69, 69)",
    }

    for key in repl:
        stylesheet = stylesheet.replace(key, repl[key])

    return stylesheet
