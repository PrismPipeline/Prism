# Houdini: Create SOP and geo ROP
geo = hou.node("/obj").createNode("geo", "Placeholder")
pig = geo.createNode("testgeometry_pighead")
pig.createOutputNode("rop_geometry", "ROP_geo")