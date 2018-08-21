#svgTool set up script

import platform
import maya.cmds as cmds
import maya.mel as mel

def createSVGTool(fromPaste = False, fromImport = False):

    svgTool = setUpSVGNetwork(fromPaste, fromImport)

    #Has no effect
    #cmds.evalDeferred('import maya.app.type.svgSetup as svg; svg.svgScriptJobSetup("'+svgTool+'")', lp=True)

def svgScriptJobSetup(svgTool):
    melCmdPaste = 'AEsvgRepopulateOffsetMenu("'+svgTool+'",2)'
    cmdPaste = 'mel.eval(\''+melCmdPaste+'\')'
    melCmdFile = 'AEsvgRepopulateOffsetMenu("'+svgTool+'",2)'
    cmdFile = 'mel.eval(\''+melCmdPaste+'\')'
    cmds.scriptJob( attributeChange=[svgTool+'.pathNamesFromPaste', cmdPaste] )
    cmds.scriptJob( attributeChange=[svgTool+'.pathNames', cmdFile] )

def setUpSVGNetwork(fromPaste = False, fromImport = False, legacy = False):

    svgTool = cmds.createNode( 'svgToPoly', n='svg#' )

    if legacy:
        svgExtruder = cmds.createNode( 'vectorExtrude', n='vectorExtrude#' )
    else:
        svgExtruder = cmds.createNode( 'typeExtrude', n='svgExtrude#' )

    svgTransform = cmds.createNode( 'transform', n='svgMesh#' )
    svgMesh = cmds.createNode( 'mesh', n='svgMeshShape#', p=svgTransform )

    #group ID nodes for the materials
    groupIdCaps = cmds.createNode( 'groupId', n= 'groupid#' )
    groupIdBevels = cmds.createNode( 'groupId', n= 'groupid#' )
    groupIdExtrusion = cmds.createNode( 'groupId', n= 'groupid#' )

    cmds.connectAttr( groupIdCaps+'.groupId', svgExtruder+'.capGroupId' )
    cmds.connectAttr( groupIdBevels+'.groupId', svgExtruder+'.bevelGroupId' )
    cmds.connectAttr( groupIdExtrusion+'.groupId', svgExtruder+'.extrudeGroupId' )

    cmds.connectAttr( svgTool+'.vertsPerChar', svgExtruder+'.vertsPerChar' )
    cmds.connectAttr( svgTool+'.outputMesh', svgExtruder+'.inputMesh' )
    cmds.connectAttr( svgExtruder+'.outputMesh', svgMesh+'.inMesh' )

    #defaults
    cmds.setAttr( svgExtruder+'.extrudeDivisions', 1 )
    cmds.setAttr( svgMesh+'.displayColors', 1 )
    cmds.polyOptions (svgMesh, colorMaterialChannel='diffuse')
    cmds.setAttr( svgTool+'.animationScale', 1,1,1, type="double3" )

    #create a default material
    blinnShader = cmds.shadingNode('blinn', asShader=True, n="svgBlinn#")
    defaultColour = [(1, 1, 1)]
    cmds.setAttr( blinnShader+'.color', defaultColour[0][0], defaultColour[0][1], defaultColour[0][2], type="double3" )
    shadingGroup = cmds.sets(n=blinnShader+'SG', renderable=True,noSurfaceShader=True,empty=True)
    cmds.connectAttr('%s.outColor' %blinnShader ,'%s.surfaceShader' %shadingGroup)

    # Message connections: Direction is important! For nodes downstream of the type node,
    # the source has to be the type node (i.e. the extruder, shell node, and remesh node)
    # This ensures there are no cycles in the graph, which cause "delete history" to skip
    # over the type node. Since the default message attribute on nodes is read-only
    # we create a new message attribute that we can connect as a destination.
    cmds.addAttr( svgExtruder, hidden=True, longName='typeMessage', attributeType='message' )
    cmds.connectAttr( svgTool+'.extrudeMessage', svgExtruder+'.typeMessage' )

    # For nodes outside of the type network (i.e. the transform) the
    # destination needs to be the type node.
    cmds.connectAttr( svgTransform+'.message', svgTool+'.transformMessage' )

    #assign the shader
    cmds.select(svgTransform)
    cmds.hyperShade( assign=blinnShader )

    #adjust deformer
    svgAdjuster = connectSVGAdjustDeformer(svgMesh, svgTransform, svgExtruder, svgTool)

    cmds.evalDeferred('import maya.app.type.svgSetup; maya.app.type.svgSetup.addPolyRemeshNodeType("'+svgTransform+'","'+svgExtruder+'","'+svgTool+'","'+svgMesh+'","'+svgAdjuster+'")', lp=True)

    if (fromImport == True):
        cmds.evalDeferred('import maya.mel as mel; mel.eval(\'AESCGFileBrowser( "", "'+ svgTool +'.svgFilepath ")\')')
    else:
        cmds.setAttr( svgTool+'.svgMode', 2 )

    cmds.setAttr( svgTool+'.useArtboard', 1 )
    #orig node un needed and exposes a problem with the extrude API.
    cmds.delete(svgMesh+"Orig")

    return svgTool

def addPolyRemeshNodeType(svgTransform, svgExtruder, svgTool, svgMesh, svgAdjuster):
    cmds.select(svgTransform)
    polyRemeshNode = cmds.polyRemesh(nodeState=1, interpolationType=0, tessellateBorders=0, refineThreshold=1.0)[0]

    cmds.addAttr( polyRemeshNode, hidden=True, longName='typeMessage', attributeType='message' )
    cmds.connectAttr( svgTool+'.remeshMessage', polyRemeshNode+'.typeMessage' )

    cmds.connectAttr( svgExtruder+'.capComponents', polyRemeshNode+'.inputComponents' )

    #set normals
    cmds.polySoftEdge(svgMesh, angle=30, ch=1)

    #add the UV proj node
    addUVNodeToSVG(svgTransform, svgExtruder)

    #connect the deformer
    connectSVGShellDeformer(svgMesh, svgTransform, svgExtruder, svgTool, svgAdjuster)

    showThesvgTool(svgTool, svgTransform)

def showThesvgTool(svgTool, svgTransform):
    # THIS COMMAND CAUSES UNDOING THE CREATION OF THE SVG NODE TO REQUIRE TO UNDOS
    cmds.select(svgTransform)
    command = 'evalDeferred \"showEditorExact(\\"'+ svgTool + '\\")\"'
    mel.eval(command)

def addUVNodeToSVG(svgTransform, svgExtruder):
    cmds.select(svgTransform)
    autoProj = cmds.polyAutoProjection( lm =0 ,pb =0 ,ibd = 0 ,cm =0 ,l =2 ,sc =1 ,o =1 ,p =6 ,ps =0.2 ,ws =0, n="svgPolyAutoProj#")

def connectSVGAdjustDeformer(svgMesh,svgTransform, svgExtruder, svgTool):
    cmds.select(svgMesh)
    newAdjustDeformer = cmds.deformer(type="vectorAdjust")[0]

    cmds.connectAttr( svgTool+'.vertsPerChar', newAdjustDeformer+'.vertsPerChar' )
    cmds.connectAttr( svgTool+'.solidsPerCharacter', newAdjustDeformer+'.solidsPerCharacter' )
    cmds.connectAttr( newAdjustDeformer+'.message', svgTool+'.adjustMessage' )
    cmds.connectAttr( svgExtruder+'.vertexGroupIds', newAdjustDeformer+'.vertexGroupIds' )

    return newAdjustDeformer


def connectSVGShellDeformer(svgMesh, svgTransform, svgExtruder, svgTool, svgAdjuster):
    #apply the type deformer to the mesh
    cmds.select(svgMesh)
    newTypeDeformer = cmds.deformer(type="shellDeformer")[0]
    cmds.connectAttr( svgTool+'.animationPosition', newTypeDeformer+'.animationPosition' )
    cmds.connectAttr( svgTool+'.animationRotation', newTypeDeformer+'.animationRotation' )
    cmds.connectAttr( svgTool+'.animationScale', newTypeDeformer+'.animationScale' )

    cmds.connectAttr( svgTool+'.vertsPerChar', newTypeDeformer+'.vertsPerChar' )

    #time to deformer
    cmds.connectAttr( 'time1.outTime', newTypeDeformer+'.time' )

    #these makes the deformer aware of manipulations (as they affect the pivot point of each character/ word)
    cmds.connectAttr( svgTool+'.solidsPerCharacter', newTypeDeformer+'.solidsPerCharacter' )

    #the points node is used to display the pivot points
    pointsNode = cmds.createNode ('displayPoints', n='displayPoints#')
    pointsTransform = cmds.listRelatives( pointsNode, allParents=True )[0]
    cmds.setAttr( pointsNode+'.hiddenInOutliner', 1 )
    cmds.setAttr( pointsTransform+'.hiddenInOutliner', 1 )
    cmds.connectAttr( newTypeDeformer+'.rotationPivotPointsPP', pointsNode+'.inPointPositionsPP[0]' )
    cmds.connectAttr( newTypeDeformer+'.scalePivotPointsPP', pointsNode+'.inPointPositionsPP[1]' )

    cmds.connectAttr( svgExtruder+'.vertexGroupIds', newTypeDeformer+'.vertexGroupIds' )

    #message connections
    cmds.addAttr( newTypeDeformer, hidden=True, longName='typeMessage', attributeType='message' )
    cmds.connectAttr( svgTool+'.animationMessage', newTypeDeformer+'.typeMessage'  )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
