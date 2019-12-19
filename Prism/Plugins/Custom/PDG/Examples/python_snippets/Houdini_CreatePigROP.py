# Houdini: Create SOP and geo ROP
# This examples creates a pighead and a ROP node in a Houdini scene.
# These nodes can be used as placeholders by the state created through this node.
# Use "/obj/Placeholder/ROP_geo" as value for the "connectednode" setting of an export state.

geo = hou.node("/obj").createNode("geo", "Placeholder")
pig = geo.createNode("testgeometry_pighead")
pig.createOutputNode("rop_geometry", "ROP_geo")