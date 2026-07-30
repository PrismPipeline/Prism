fname = "CreateItem"
fname = "EnterText"
fname = "SetPath"
fname = "SaveComment"
fname = "ChangeUser"
fname = "CreateProject"
fname = "UserSettings"
# fname = "ProjectSettings"
# fname = "PrismInstaller"

code = """
with open("%s" + "_ui.py", "r+") as f:
    data = f.read()
    data = data.replace("PySide6", "qtpy")
    f.seek(0)
    f.truncate(0)
    f.write(data)

print("done")
""" % fname

import subprocess
proc = subprocess.Popen(["pyside6-uic", "--star-imports", "-o", fname + "_ui.py", fname + ".ui"])
result = proc.communicate()
print(result)

proc = subprocess.Popen(["python", "-c", code])
result = proc.communicate()
print(result)