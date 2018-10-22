import sys, os, platform
if os.path.basename(sys.executable) != "hython.exe":
	if platform.system() == "Windows":
		Dir = os.path.join(os.getenv('LocalAppdata'), "Prism", "Scripts")
	elif platform.system() == "Linux":
		Dir = os.path.join("/usr", "local", "Prism", "Scripts")
	elif platform.system() == "Darwin":
		Dir = "/Applications/Prism/Prism/Scripts"

	if Dir not in sys.path:
		sys.path.append(Dir)
	
	import PrismCore
	pcore = PrismCore.PrismCore(app="Houdini")