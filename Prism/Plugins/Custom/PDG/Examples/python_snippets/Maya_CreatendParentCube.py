# Maya: Create and parent cube
import maya.cmds as cmds
geo_group = cmds.createNode('transform', name='GEO')
cube = cmds.polyCube()[0]
cmds.parent(cube, geo_group)