import maya.cmds as cmds
# Following import does not work with Maya LT.  PPT, 17-Nov-2014.

from maya.debug.TODO import *

def reapply():

    # Get the list of color managed nodes.
    cmNodes = cmds.colorManagementPrefs(query=True, colorManagedNodes=True)

    # Avoid warning if mental ray plugin isn't loaded.
    if cmds.pluginInfo('Mayatomr', query=True, loaded=True):
        cmNodes = cmNodes + cmds.ls(type='mentalrayIblShape')

    # Avoid warning if mtoa plugin isn't loaded.
    if cmds.pluginInfo('mtoa', query=True, loaded=True):
        cmNodes = cmNodes + cmds.ls(type='aiImage')

    # Loop over nodes: get each node's file path, evaluate rules, set
    # the color space.
    for nodeName in cmNodes:

        # If ignore file rules is set for that node, don't reapply on it.
        ignoreColorSpaceFileRules = cmds.getAttr(
            nodeName + '.ignoreColorSpaceFileRules')
        if ignoreColorSpaceFileRules:
            continue

        TODO('HACK', 'Should not depend on per node type knowledge', None)

        # We should not need to know the list of file name attribute names
        # for all types of color managed nodes, as more color managed node
        # types can be added in the future.
        #
        # As of 5-Nov-2014, we know that the colorManagedNodes query
        # will return two types of nodes: image plane nodes, which have an
        # image file attribute, and file texture nodes, which have a file
        # name attribute.
        #
        # Additionally, we are relying on identical attribute naming for
        # the color space across all node types, which is very weak.
        attrList = cmds.listAttr(nodeName)
        fileAttrName = 'imageName' 
        if 'imageName' in attrList:
            fileAttrName = 'imageName'
        elif 'fileTextureName' in attrList:
            fileAttrName = 'fileTextureName'
        elif 'filename' in attrList:  # aiImage
            fileAttrName = 'filename'
        else:
            fileAttrName = 'texture'

        fileName = cmds.getAttr(nodeName + '.' + fileAttrName)

        colorSpace = cmds.colorManagementFileRules(evaluate=fileName)

        cmds.setAttr(nodeName + '.colorSpace', colorSpace, type='string')
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
