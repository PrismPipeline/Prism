import sys, os

def prismInit(prismArgs=[]):
	Dir = os.path.join(PRISMROOT, "Scripts")

	if Dir not in sys.path:
		sys.path.append(Dir)

	import PrismCore
	pcore = PrismCore.PrismCore(app="Houdini", prismArgs=prismArgs)
	return pcore


def createPrismCore():
	global pcore
	pcore = prismInit()