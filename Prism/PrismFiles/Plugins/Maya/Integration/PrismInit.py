import os, sys, platform
def prismInit():
	if platform.system() == "Windows":
		Dir = os.path.join(os.getenv('LocalAppdata'), "Prism", "Scripts")
	elif platform.system() == "Linux":
		Dir = "/usr/local/Prism/Scripts"
	elif platform.system() == "Darwin":
		Dir = "/Applications/Prism/Prism/Scripts"

	if Dir not in sys.path:
		sys.path.append(Dir)
		
	import PrismCore
	pcore = PrismCore.PrismCore(app="Maya")
	return pcore