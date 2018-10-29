import sys, os, platform
if os.path.basename(sys.executable) != "hython.exe":
	Dir = os.path.join(PRISMROOT, "Scripts")

	if Dir not in sys.path:
		sys.path.append(Dir)

	import PrismCore
	pcore = PrismCore.PrismCore(app="Houdini")