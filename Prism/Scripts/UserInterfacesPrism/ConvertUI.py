#fname = "SetPath"
#fname = "CreateProject"
fname = "SetProject"
fname = "PrismSettings"
# fname = "ExternalPandoraSubmitter"
# fname = "ProjectCreated"
#fname = "PrismInstaller"
# fname = "SaveComment"

pyside = 0

if pyside in [0, 1]:
    from pysideuic import compileUi

    pyfile = open(fname + "_ui.py", "w")
    compileUi(fname + ".ui", pyfile, False, 4, False)

if pyside in [0, 2]:
    from pyside2uic import compileUi as compileUi2

    pyfile = open(fname + "_ui_ps2.py", "w")
    compileUi2(fname + ".ui", pyfile, False, 4, False)

pyfile.close()
