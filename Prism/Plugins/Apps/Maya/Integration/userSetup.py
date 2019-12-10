
#>>>PrismStart
from maya import OpenMaya as omya

if omya.MGlobal.mayaState() != omya.MGlobal.kBatch:
	try:
		import PrismInit
		pcore = PrismInit.prismInit()
	except:
		print("Error occured while loading pcore")
#<<<PrismEnd
