fname = "hou_ImageRender"
# fname = "hou_ImportFile"
# fname = "hou_Export"
# fname = "hou_InstallHDA"
# fname = "hou_SaveHDA"
# fname = "hou_Playblast"
# fname = "hou_Dependency"

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
