fname = "CreateItem"
# fname = "EnterText"
# fname = "SetPath"
# fname = "SaveComment"
# fname = "ChangeUser"
# fname = "CreateProject"
fname = "UserSettings"
fname = "ProjectSettings"
# fname = "CreateProject"
# fname = "PrismInstaller"

code = """
import sys, pprint
sys.path.append("C:/Users/richa/Downloads/qtpy-tools-main/qtpy-tools-main")

fname = "%s"
from qtpyuic import compileUi
pyfile = open(fname + "_ui.py", "w")
compileUi(fname + ".ui", pyfile, False, 4, False)


pyfile.close()
print("done")
""" % fname

import subprocess
proc = subprocess.Popen(["python2", "-c", code])
result = proc.communicate()
print(result)