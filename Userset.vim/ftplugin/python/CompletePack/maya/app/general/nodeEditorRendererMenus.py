"""
Support for mental ray shader menus in the Node Editor panel.
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


from maya import cmds, mel

def _isClassified(node, classification):
    type = cmds.nodeType(node)
    classified = cmds.getClassification(type, satisfies=classification)
    return classified

def _addMrLightShaderMenuItems(ned, node):
    """
    Check for mental ray light shader node and create necessary menu items
    """
    isLight = _isClassified(node, 'rendernode/mentalray/light')
    isLightmap = _isClassified(node, 'rendernode/mentalray/lightmap')
    if isLight and not isLightmap:
        _createMrLightShaderMenuItems(node)
        return True
    else:
        return False

def _addMrTextureShaderMenuItems(ned, node):
    """
    Check for mental ray texture shader node and create necessary menu items
    """
    isTexture = _isClassified(node, 'rendernode/mentalray/texture')
    if isTexture:
        _createMrTextureShaderMenuItems(node)
        return True
    else:
        return False

customMrNodeItemMenuCallbacks = [_addMrLightShaderMenuItems, _addMrTextureShaderMenuItems]

def _createMrLightShaderMenuItems(node):
    """
    Create node item marking menu items specific to mental ray light shader nodes
    """
    lightArray = cmds.listConnections(node, source=False, destination=True, type='light')
    if lightArray:
        selectObjString = maya.stringTable[ 'y_nodeEditorRendererMenus.kSelectObjectsIlluminated'  ]
        frameObjString = maya.stringTable[ 'y_nodeEditorRendererMenus.kFrameObjectsIlluminated'  ]

        for member in lightArray:
            def selectCB(light=member, *args):
                mel.eval('selectObjectsIlluminatedBy "%s"' % light)

            def frameCB(light=member, *args):
                mel.eval('selectObjectsIlluminatedBy "%s"; fitAllPanels -selected' % light)

            selectObjStrFmt = cmds.format(selectObjString, stringArg=member)
            cmds.menuItem(label=selectObjStrFmt, radialPosition='E', c = selectCB)

            frameObjStrFmt = cmds.format(frameObjString, stringArg=member)
            cmds.menuItem(label=frameObjStrFmt, c = frameCB)

        cmds.menuItem( divider=True )

def _createMrTextureShaderMenuItems(node):
    """
    Create node item marking menu items specific to mental ray texture shader nodes
    """
    attrName = '%s.outValue' % node
    existingAttr = cmds.ls(attrName)
    if len(existingAttr) > 0:
        def assignCB(*args):
            mel.eval('hypergraphAssignTextureToSelection "%s"' % (node))

        cmds.menuItem(label= maya.stringTable['y_nodeEditorRendererMenus.kMentalRayTextureShadersAssign' ],
        radialPosition = 'N',
        c = assignCB)

def addMrShaderMenuItems(ned, node):
    """
    Check for mental ray shader node and create necessary menu items
    """
    added = False
    for callback in customMrNodeItemMenuCallbacks:
        added = callback(ned, node)
        if added:
            break
    if not added:
        # If node is some kind of mental ray node, consider it
        # processed to prevent it from falling into other node
        # type menu categories.
        isMentalRay = _isClassified(node, 'rendernode/mentalray')
        if isMentalRay:
            added = True
    return added
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
