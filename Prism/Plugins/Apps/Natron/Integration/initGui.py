#>>>PrismStart
if not NatronEngine.natron.isBackground():
	import sys, os

	Dir = os.path.join(PRISMROOT, "Scripts")
	if Dir not in sys.path:
		sys.path.append(Dir)

	import PrismCore
	pcore = PrismCore.PrismCore(app="Natron")

def writePrismParamChanged(thisParam, thisNode, thisGroup, app, userEdited):
	pcore.appPlugin.wpParamChanged(thisParam, thisNode, thisGroup, app, userEdited)
#<<<PrismEnd

