import sys, os

Dir = os.path.join(os.getenv('LocalAppdata'), "Prism", "Scripts")
if Dir not in sys.path:
	sys.path.append(Dir)

import PrismCore
pcore = PrismCore.PrismCore(app="3dsMax")