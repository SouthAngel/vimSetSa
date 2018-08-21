#typetool set up script
import maya

from os.path import expanduser
import platform
import maya.cmds as cmds
import maya.mel as mel
import maya.app.type.AEtypeTemplate as typeTemplate

try:
  from PySide2.QtGui import *
  from PySide2.QtWidgets import *
except ImportError:
  from PySide.QtGui import *

def createTypeTool(font=None, style=None, text=None, legacy = False):

    typeTool = cmds.createNode( 'type', n='type#' )
    typeExtruder = None
    if legacy:
        typeExtruder = cmds.createNode( 'vectorExtrude', n='typeExtrude#' )
        cmds.setAttr( typeTool+'.legacyDecomposition', 1)
    else:
        typeExtruder = cmds.createNode( 'typeExtrude', n='typeExtrude#' )
    typeTransform = cmds.createNode( 'transform', n='typeMesh#' )
    typeMesh = cmds.createNode( 'mesh', n='typeMeshShape#', p=typeTransform )

    #group ID nodes for the materials
    groupIdCaps = cmds.createNode( 'groupId', n= 'groupid#' )
    groupIdBevels = cmds.createNode( 'groupId', n= 'groupid#' )
    groupIdExtrusion = cmds.createNode( 'groupId', n= 'groupid#' )

    cmds.connectAttr( typeTool+'.vertsPerChar', typeExtruder+'.vertsPerChar' )
    cmds.connectAttr( groupIdCaps+'.groupId', typeExtruder+'.capGroupId' )
    cmds.connectAttr( groupIdBevels+'.groupId', typeExtruder+'.bevelGroupId' )
    cmds.connectAttr( groupIdExtrusion+'.groupId', typeExtruder+'.extrudeGroupId' )

    #the last thing we do is plug the nodes into each other, which triggers a calculation.
    cmds.connectAttr( typeTool+'.outputMesh', typeExtruder+'.inputMesh' )
    cmds.connectAttr( typeExtruder+'.outputMesh', typeMesh+'.inMesh' )

    #set the home folder, Mac OS stores fonts here.
    home = expanduser("~")
    cmds.setAttr( typeTool+'.homeFolder', home, type="string" )

    #defaults
    cmds.setAttr( typeTool+'.manipulatorMode', 0)
    cmds.setAttr( typeTool+'.animationScale', 1,1,1, type="double3" )

    if platform.system() == 'Darwin':
        defaultFont = "Lucida Grande"
        defaultStyle = "Regular"
    elif platform.system() == 'Linux':
        defaultFont = None
        possibleFont = None
        # find a usable font
        for family in ['Arial', 'Liberation Sans', 'Lucida Grande']:
            defaultQFont = QFont(family)
            fontInfo = QFontInfo(defaultQFont)
            if fontInfo.family() == family:
                defaultFont = family
                break
            if (possibleFont is None) and (len(fontInfo.family()) is not 0):
                possibleFont = fontInfo.family()
        if defaultFont is None:
            defaultFont = possibleFont
        if defaultFont is None:
            # in desperation choose the first available font
            database = QFontDatabase()
            for family in database.families():
                if database.isScalable(family):
                    defaultFont = family
                    break
        if defaultFont is None:
            # the font system is unusable
            defaultFont = 'Arial'
        defaultStyle = "Regular"
    elif platform.system() == 'Windows':
        defaultFont = "Lucida Sans Unicode"
        defaultStyle = "Regular"

    if font:
        defaultQFont = QFont(font)
        print defaultQFont.styleName()
        fontInfo = QFontInfo(defaultQFont)
        if fontInfo.family() != font:
            cmds.warning(maya.stringTable['y_AEtypeTemplate.kFontNotFound' ])
            font = None

    if font and style:
        fontDB = QFontDatabase()
        allStyles = fontDB.styles(font)
        if style not in allStyles:
            cmds.warning(maya.stringTable['y_AEtypeTemplate.kStyleNotFound' ])
            style = None

    if font:
        cmds.setAttr( typeTool+'.currentFont', font, type="string" )
    else:
        cmds.setAttr( typeTool+'.currentFont', defaultFont, type="string" )

    if style:
        cmds.setAttr( typeTool+'.currentStyle', style, type="string" )
    else:
        cmds.setAttr( typeTool+'.currentStyle', defaultStyle, type="string" )


    #create a default material
    blinnShader = cmds.shadingNode('blinn', asShader=True, n="typeBlinn")
    defaultColour = [(1, 1, 1)]
    cmds.setAttr( blinnShader+'.color', defaultColour[0][0], defaultColour[0][1], defaultColour[0][2], type="double3" )
    shadingGroup = cmds.sets(n=blinnShader+'SG', renderable=True,noSurfaceShader=True,empty=True)
    cmds.connectAttr('%s.outColor' %blinnShader ,'%s.surfaceShader' %shadingGroup)

    # Message connections: Direction is important! For nodes downstream of the type network,
    # the source has to be the type node (i.e. the extruder, shell node, and remesh node)
    # This ensures there are no cycles in the graph, which cause "delete history" to skip
    # over the type node. Since the default message attribute on nodes is read-only
    # we create a new message attribute that we can connect as a destination.
    cmds.addAttr( typeExtruder, hidden=True, longName='typeMessage', attributeType='message' )
    cmds.connectAttr( typeTool+'.extrudeMessage', typeExtruder+'.typeMessage' )
    # For nodes outside of the type network (i.e. the transform) the
    # destination needs to be the type node.
    cmds.connectAttr( typeTransform+'.message', typeTool+'.transformMessage' )

    #assign the shader
    cmds.select(typeTransform)
    cmds.hyperShade( assign=blinnShader )

    #connect the adjust deformer
    connectTypeAdjustDeformer(typeMesh,typeTransform, typeExtruder, typeTool)

    #set normals
    cmds.polySoftEdge(typeMesh, angle=30, ch=1)

    #add polyRemesh
    cmds.evalDeferred('import maya.app.type.typeToolSetup; maya.app.type.typeToolSetup.addPolyRemeshNodeType("'+typeTransform+'","'+typeExtruder+'","'+typeTool+'","'+typeMesh+'")', lp=True)

    #orig node un needed and exposes a problem with the extrude API.
    cmds.delete(typeMesh+"Orig")

    if text:
        byteString = typeTemplate.ByteToHex( text )
        cmds.setAttr(typeTool+".textInput", byteString, type="string")

    return typeTool

def addPolyRemeshNodeType(typeTransform, typeExtruder, typeTool, typeMesh):
    cmds.select(typeTransform)
    polyRemeshNode = cmds.polyRemesh(nodeState=1, interpolationType=0, tessellateBorders=0, refineThreshold=1.0)[0]

    cmds.addAttr( polyRemeshNode, hidden=True, longName='typeMessage', attributeType='message' )

    cmds.connectAttr( typeTool+'.remeshMessage', polyRemeshNode+'.typeMessage' )
    cmds.connectAttr( typeExtruder+'.capComponents', polyRemeshNode+'.inputComponents' )

    #add the UV proj node
    addUVNodeToType(typeMesh, typeExtruder)

    #connect the deformer
    connectShellDeformer(typeMesh, typeTransform, typeExtruder, typeTool)

    showTheTypeTool(typeTool, typeTransform)

def showTheTypeTool(typeTool, typeTransform):
    # THIS COMMAND CAUSES DELETION OF THE TYPE TOOL TO REQUIRE UNDOING TWICE
    cmds.select(typeTransform)
    command = 'evalDeferred \"showEditorExact(\\"'+ typeTool + '\\")\"'
    mel.eval(command)

def addUVNodeToType(typeMesh, typeExtruder):
    cmds.select(typeMesh)
    autoProj = cmds.polyAutoProjection( lm =0 ,pb =0 ,ibd = 0 ,cm =0 ,l =2 ,sc =1 ,o =1 ,p =6 ,ps =0.2 ,ws =0, n="typePolyAutoProj#")

def connectTypeAdjustDeformer(typeMesh,typeTransform, typeExtruder, typeTool):
    cmds.select(typeMesh)
    newAdjustDeformer = cmds.deformer(type="vectorAdjust")[0]

    cmds.connectAttr( typeTool+'.grouping', newAdjustDeformer+'.grouping' )
    cmds.connectAttr( typeTool+'.manipulatorTransforms', newAdjustDeformer+'.manipulatorTransforms' )
    cmds.connectAttr( typeTool+'.alignmentMode', newAdjustDeformer+'.alignmentMode' )

    # This causes a cycle in the DG which breaks delete non deformer history. (MAYA-57226)
    # This attribute is never set by the vectorAdjust node, so this connection doesnt affect anything.
    #cmds.connectAttr( newAdjustDeformer+'.extrudeDistanceScalePP', typeExtruder+'.extrudeDistanceScalePP' )
    cmds.connectAttr( typeTool+'.vertsPerChar', newAdjustDeformer+'.vertsPerChar' )
    cmds.connectAttr( typeExtruder+'.vertexGroupIds', newAdjustDeformer+'.vertexGroupIds' )

    return newAdjustDeformer


def connectShellDeformer(typeMesh, typeTransform, typeExtruder, typeTool):
    #apply the type deformer to the mesh
    cmds.select(typeMesh)
    newTypeDeformer = cmds.deformer(type="shellDeformer")[0]
    cmds.connectAttr( typeTool+'.animationPosition', newTypeDeformer+'.animationPosition' )
    cmds.connectAttr( typeTool+'.animationPositionX', newTypeDeformer+'.animationPositionX' )
    cmds.connectAttr( typeTool+'.animationPositionY', newTypeDeformer+'.animationPositionY' )
    cmds.connectAttr( typeTool+'.animationPositionZ', newTypeDeformer+'.animationPositionZ' )
    cmds.connectAttr( typeTool+'.animationRotation', newTypeDeformer+'.animationRotation' )
    cmds.connectAttr( typeTool+'.animationRotationX', newTypeDeformer+'.animationRotationX' )
    cmds.connectAttr( typeTool+'.animationRotationY', newTypeDeformer+'.animationRotationY' )
    cmds.connectAttr( typeTool+'.animationRotationZ', newTypeDeformer+'.animationRotationZ' )
    cmds.connectAttr( typeTool+'.animationScale', newTypeDeformer+'.animationScale' )
    cmds.connectAttr( typeTool+'.animationScaleX', newTypeDeformer+'.animationScaleX' )
    cmds.connectAttr( typeTool+'.animationScaleY', newTypeDeformer+'.animationScaleY' )
    cmds.connectAttr( typeTool+'.animationScaleZ', newTypeDeformer+'.animationScaleZ' )

    cmds.connectAttr( typeTool+'.vertsPerChar', newTypeDeformer+'.vertsPerChar' )
    #time to deformer
    cmds.connectAttr( 'time1.outTime', newTypeDeformer+'.time' )
    #these makes the deformer aware of manipulations (as they affect the pivot point of each character/ word)
    cmds.connectAttr( typeTool+'.grouping', newTypeDeformer+'.grouping' )

    #message connections:
    cmds.addAttr( newTypeDeformer, hidden=True, longName='typeMessage', attributeType='message' )
    cmds.connectAttr( typeTool+'.animationMessage', newTypeDeformer+'.typeMessage'  )

    #the points node is used to display the pivot points
    pointsNode = cmds.createNode ('displayPoints', n='displayPoints#')
    pointsTransform = cmds.listRelatives( pointsNode, allParents=True )[0]
    cmds.setAttr( pointsNode+'.hiddenInOutliner', 1 )
    cmds.setAttr( pointsTransform+'.hiddenInOutliner', 1 )
    cmds.connectAttr( newTypeDeformer+'.rotationPivotPointsPP', pointsNode+'.inPointPositionsPP[0]' )
    cmds.connectAttr( newTypeDeformer+'.scalePivotPointsPP', pointsNode+'.inPointPositionsPP[1]' )
    cmds.connectAttr( typeExtruder+'.vertexGroupIds', newTypeDeformer+'.vertexGroupIds' )
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
