#>>>PrismStart
import nuke
if not nuke.env["studio"]:
	import sys, os, platform

	if platform.system() == "Windows":
		prismRoot = os.path.join(os.getenv('LocalAppdata'), "Prism")
	elif platform.system() == "Linux":
		prismRoot = "/usr/local/Prism"
	elif platform.system() == "Darwin":
		prismRoot = "/Applications/Prism/Prism"

	Dir = os.path.join(prismRoot, "Scripts")
	if Dir not in sys.path:
		sys.path.append(Dir)

	import PrismCore
	pcore = PrismCore.PrismCore(app="Nuke")
#<<<PrismEnd