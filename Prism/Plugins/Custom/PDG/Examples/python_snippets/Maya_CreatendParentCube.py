# Maya: Create and parent cube
# This example creates a group and a cube in a Maya scene.
# These objects can be used as placeholder objects by the state created through this node.

import maya.cmds as cmds

geo_group = cmds.createNode('transform', name='GEO')
cube = cmds.polyCube()[0]
cmds.parent(cube, geo_group)