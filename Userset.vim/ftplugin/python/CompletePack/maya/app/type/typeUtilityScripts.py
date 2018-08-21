#various utilities used by the type tool

#getShadingGroupsFromObject
#findNodeInTypeToolChain
#getAnimationNode
#typeDeletingHistory
#resetAllManipulations
#splitTypeMaterials

###Falloff curve utilties:

#getFalloffCurveAttr
#setCurveAttr
#getMObjectFromName
#resetTypeCurve
#setCurvePreset

from sets import Set
import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMaya as om
import pymel.core as pm

def getCurrentCtxName():
    ctx = cmds.currentCtx()
    className = ""
    if True == cmds.contextInfo(ctx, exists=True):
        className = cmds.contextInfo(ctx, c=True)
    return className

#this function is used to toggle the colour of the manipulator button (dark background when the manip is selected)
def toggleTypeManipButton(typeNode):
    className = getCurrentCtxName()
    if (className == "typeTRSTool"):
        cmds.evalDeferred("cmds.iconTextButton( 'typeManipToggleAEReplacement', e=True,  ebg=False)")
        cmds.SelectTool()
    else:
        #manipulator is off
        #get the transform node and select it (it's required for the manipulator)
        transforms = cmds.listConnections(typeNode+'.transformMessage')
        cmds.select(transforms[0], replace=True)

        cmds.iconTextButton( 'typeManipToggleAEReplacement', e=True, ebg=True, bgc=[0.32, 0.52, 0.65])
        mel.eval("typeMoveTool");

#check if the manipulator is loaded and make sure the manip button background is correct (run from AE replacement)
def checkTypeManipButton():
    className = getCurrentCtxName()
    if (className == "typeTRSTool"):
        cmds.iconTextButton( 'typeManipToggleAEReplacement', e=True, ebg=True, bgc=[0.32, 0.52, 0.65])
    else:
        cmds.iconTextButton( 'typeManipToggleAEReplacement', e=True,  ebg=True, bgc=[0.364, 0.364, 0.364])

def flipTypeManipulator():
    className = getCurrentCtxName()
    if (className == "typeTRSTool"):
        cmds.MoveTool()
        mel.eval("typeMoveTool");

#get the shader attribute attached to an object
#this and the next function are VERY similar, but they go about their task in different ways - which only work in different situations.
def getShaderFromObject (mesh):
    #use a set, because we'll get each material returned a couple of times
    materials = Set()
    shapes = cmds.listRelatives (str(mesh), fullPath=True, shapes=True)
    future = cmds.listConnections(shapes[0], type="shadingEngine")
    if future is None:
        return None

    # Search for the connecting shading group
    for n in future:
        if cmds.attributeQuery("surfaceShader",node=n, exists=True):
            materials.add ("%s.surfaceShader" % (str(n)))

    #we're expecting a list back, so lets not confuse things.
    returnList = list(materials)
    return returnList

#get the shaders attached to an object
def getShadingGroupsFromObject (mesh):
    materials = []
    future = cmds.listHistory(str(mesh), f=1, pdo=1)

    if future is None:
        return None

    # Search for the connecting shading group
    for n in future:
        if cmds.attributeQuery("surfaceShader",node=n, exists=True):
            materials.append(n)

    return materials

#given the group nodes, get the associated materials
def getVectorShadingGroups (mesh, extrudeNode):
    capGroupId = cmds.listConnections(extrudeNode+'.capGroupId')
    bevelGroupId = cmds.listConnections(extrudeNode+'.bevelGroupId')
    extrudeGroupId = cmds.listConnections(extrudeNode+'.extrudeGroupId')

    capGrpMessageConections = cmds.listConnections(capGroupId[0]+'.message')
    bevelGrpMessageConections = cmds.listConnections(bevelGroupId[0]+'.message')
    extrudeGrpMessageConections = cmds.listConnections(extrudeGroupId[0]+'.message')

    if (capGrpMessageConections is not None and bevelGrpMessageConections is not None and extrudeGrpMessageConections is not None):
        capMaterialAtr = getShaderFromArray(capGrpMessageConections)
        bevelMaterialAtr = getShaderFromArray(bevelGrpMessageConections)
        extrudeMaterialAtr = getShaderFromArray(extrudeGrpMessageConections)
        return [capMaterialAtr, bevelMaterialAtr, extrudeMaterialAtr]
    else:
        return []

#given a list of nodes, find the shading engine, and it's material
def getShaderFromArray(GrpMessageConections):
    for node in GrpMessageConections:
        if cmds.nodeType(node) == "shadingEngine":
            return node+'.surfaceShader'

#resets all manipulations.
def resetAllManipulations (nodeName):
    import pymel.core as pm #doing this here because Maya trips up because this is called from MEL and this skips the imports at the top of this file

    charManipulations = pm.getAttr(nodeName+'.manipulatorPositionsPP' )
    wordManipulations = pm.getAttr(nodeName+'.manipulatorWordPositionsPP')
    lineManipulations = pm.getAttr(nodeName+'.manipulatorLinePositionsPP' )

    currentChar = pm.getAttr(nodeName+'.manipulateId')
    currentWord = pm.getAttr(nodeName+'.manipulateWord')
    currentLine = pm.getAttr(nodeName+'.manipulateLine')

    #for all in arrays
    for i in range (0, len(charManipulations), 1):
        charManipulations[i] = [0.0, 0.0, 0.0]

    for i in range (0, len(wordManipulations), 1):
        wordManipulations[i] = [0.0, 0.0, 0.0]

    for i in range (0, len(lineManipulations), 1):
        lineManipulations[i] = [0.0, 0.0, 0.0]

    pm.setAttr(nodeName+'.manipulatorPositionsPP', charManipulations, type="vectorArray" )
    pm.setAttr(nodeName+'.manipulatorWordPositionsPP', wordManipulations, type="vectorArray" )
    pm.setAttr(nodeName+'.manipulatorLinePositionsPP', lineManipulations, type="vectorArray" )

    pm.setAttr(nodeName+'.manipulatorRotationsPP', charManipulations, type="vectorArray" )
    pm.setAttr(nodeName+'.manipulatorWordRotationsPP', wordManipulations, type="vectorArray" )
    pm.setAttr(nodeName+'.manipulatorLineRotationsPP', lineManipulations, type="vectorArray" )

    pm.setAttr(nodeName+'.manipulatorScalesPP', charManipulations, type="vectorArray" )
    pm.setAttr(nodeName+'.manipulatorWordScalesPP', wordManipulations, type="vectorArray" )
    pm.setAttr(nodeName+'.manipulatorLineScalesPP', lineManipulations, type="vectorArray" )

    cmds.setAttr( nodeName+'.positionAdjust', 0,0,0, type="double3" )
    cmds.setAttr( nodeName+'.rotationAdjust', 0,0,0, type="double3" )
    cmds.setAttr( nodeName+'.scaleAdjust', 0,0,0, type="double3" )

    #trick to get the type tool to update
    cmds.MoveTool()
    mel.eval("typeMoveTool");


def joinTypeMaterials(meshShape, typeNode):
    transformList = cmds.listRelatives(meshShape, parent=True, fullPath=True)

    cmds.setAttr( meshShape+'.displayColors', 0 )
    shaderType = cmds.optionMenuGrp('typeToolShaderType', q=True, v=True )

    shader = cmds.shadingNode(shaderType, asShader=True, n="typeShader#")
    defaultColour = [(1, 1, 1)]
    try:
        cmds.setAttr( shader+'.color', defaultColour[0][0], defaultColour[0][1], defaultColour[0][2], type="double3" )
    except:
        pass

    shadingGroup = cmds.sets(n=shader+'SG', renderable=True,noSurfaceShader=True,empty=True)
    cmds.connectAttr('%s.outColor' %shader ,'%s.surfaceShader' %shadingGroup)

    #assign the shader
    cmds.select(transformList[0])
    cmds.hyperShade( assign=shader )

    cmds.evalDeferred("maya.mel.eval('updateAE "+typeNode+"')")
    cmds.select (transformList[0])

#assign materials to the type tool
def splitTypeMaterials (extrudeNode, meshShape, typeNode):
    shadingGroups = getShadingGroupsFromObject(meshShape)
    cmds.setAttr( meshShape+'.displayColors', 0 )
    for shaders in shadingGroups:
        cmds.sets( rm=shaders )

    capGroupId = cmds.listConnections(extrudeNode+'.capGroupId')
    bevelGroupId = cmds.listConnections(extrudeNode+'.bevelGroupId')
    extrudeGroupId = cmds.listConnections(extrudeNode+'.extrudeGroupId')

    if (capGroupId is None) or (len(capGroupId) == 0):
        groupIdCaps = cmds.createNode( 'groupId' )
        cmds.connectAttr( groupIdCaps+'.groupId', extrudeNode+'.capGroupId' )
        capGroupId = cmds.listConnections(extrudeNode+'.capGroupId')

    if (bevelGroupId is None) or (len(bevelGroupId) == 0):
        groupIdBevels = cmds.createNode( 'groupId' )
        cmds.connectAttr( groupIdBevels+'.groupId', extrudeNode+'.bevelGroupId' )
        bevelGroupId = cmds.listConnections(extrudeNode+'.bevelGroupId')

    if (extrudeGroupId is None) or (len(extrudeGroupId) == 0):
        groupIdExtrusion = cmds.createNode( 'groupId' )
        cmds.connectAttr( groupIdExtrusion+'.groupId', extrudeNode+'.extrudeGroupId' )
        extrudeGroupId = cmds.listConnections(extrudeNode+'.extrudeGroupId')

    groupIds = [capGroupId[0], bevelGroupId[0], extrudeGroupId[0]]

    shaderNames = ["typeCapsShader", "typeBevelShader", "typeExtrusionShader"]
    shaderColours = [(0.627451, 0.627451, 0.627451), (1.0, 0.4019, 0.1274), (0.129412, 0.65098, 1)]

    s = 0
    shaderType = cmds.optionMenuGrp('typeToolShaderType', q=True, v=True )
    for ids in groupIds:

        shader = cmds.shadingNode(shaderType, asShader=True, n=shaderNames[s]+'#')
        try:
            cmds.setAttr( shader+'.color', shaderColours[s][0], shaderColours[s][1], shaderColours[s][2], type="double3" )
        except:
            try:
                #rampShader
                cmds.setAttr( shader+'.color[0].color_Color', shaderColours[s][0], shaderColours[s][1], shaderColours[s][2], type="double3" )
            except:
                pass

        shadingGroup = cmds.sets(n=shaderNames[s]+'SG#', renderable=True,noSurfaceShader=True,empty=True)
        cmds.connectAttr('%s.outColor' %shader ,'%s.surfaceShader' %shadingGroup)
        try:
            cmds.assignShaderToType(gr=ids, sg=shadingGroup, me=meshShape)
        except:
            cmds.warning ("Material assignment failure.")
        s +=1

    transformList = cmds.listRelatives(meshShape, parent=True, fullPath=True)
    cmds.evalDeferred("maya.mel.eval('updateAE "+typeNode+"')")
    transform = cmds.listRelatives(meshShape,type='transform',p=True)[0]
    cmds.select (transform)

# curve utilities
def getFalloffCurveAttr(thisNode, attr):
    #get the ramp attribute
    fnThisNode = om.MFnDependencyNode(thisNode)
    rampAttribute = fnThisNode.attribute(attr)
    rampPlug = om.MPlug( thisNode, rampAttribute )
    rampPlug.setAttribute(rampAttribute)
    RampPlug01 = om.MPlug(rampPlug.node(), rampPlug.attribute())

    #Get the atrribute as an MRampAttribute
    myRamp = om.MCurveAttribute(RampPlug01.node(), RampPlug01.attribute())
    return myRamp

def setCurveAttr(myRamp, pos, val):
    myRamp.setCurve(val, pos)

def getMObjectFromName(nodeName):
    sel = om.MSelectionList()
    sel.add(nodeName)
    thisNode = om.MObject()
    sel.getDependNode( 0, thisNode )
    return thisNode

def resetTypeCurve(attributeName, curveName):
    nodeName = attributeName.split(".", 1)
    thisNode = getMObjectFromName(nodeName[0])

    val = om.MFloatArray()
    pos = om.MFloatArray()

    if curveName == "extrudeCurveCurve":
        pos.append(0.0)
        pos.append(0.333)
        pos.append(0.667)
        pos.append(1.0)

        val.append(0.50)
        val.append(0.50)
        val.append(0.50)
        val.append(0.50)

        #attribute name
        curveWidget = getFalloffCurveAttr(thisNode, "extrudeCurve")
        setCurveAttr(curveWidget, pos, val)
    else:
        pos.append(0.0)
        pos.append(0.5)
        pos.append(1.0)
        pos.append(1.0)

        val.append(1.0)
        val.append(1.0)
        val.append(0.50)
        val.append(0.00)

        if curveName == "frontBevelCurveCurve":
            curveWidget = getFalloffCurveAttr(thisNode, "frontBevelCurve")
            setCurveAttr(curveWidget, pos, val)
        elif curveName == "backBevelCurveCurve":
            curveWidget = getFalloffCurveAttr(thisNode, "backBevelCurve")
            setCurveAttr(curveWidget, pos, val)
        elif curveName == "offsetBevelCurveCurve":
            curveWidget = getFalloffCurveAttr(thisNode, "offsetBevelCurve")
            setCurveAttr(curveWidget, pos, val)
        elif curveName == "outerBevelCurveCurve":
            curveWidget = getFalloffCurveAttr(thisNode, "outerBevelCurve")
            setCurveAttr(curveWidget, pos, val)

def setCurvePreset(attributeName, valueString):
    nodeName = attributeName.split(".", 1)
    thisNode = getMObjectFromName(nodeName[0])

    arrayValues = valueString.split(",", -1)

    val = om.MFloatArray()
    pos = om.MFloatArray()

    for i in range (0, len(arrayValues), 2):
        position = float(arrayValues[i])
        pos.append(position)
        curVal = float(arrayValues[i+1])
        val.append(curVal)

    curveWidget = getFalloffCurveAttr(thisNode, nodeName[1])
    setCurveAttr(curveWidget, pos, val)


def particlesToTypePivotPoints():
    selectedObjects = maya.cmds.ls(sl=True)
    if len(selectedObjects) == 0:
        cmds.error("Please select a Type Object")

    for sel in selectedObjects:
        createdSystem = cmds.nParticle()

        selNodeType = cmds.nodeType(sel)
        if selNodeType == "type":
            bboxMinArray = cmds.getAttr(sel+".characterBoundingBoxesMin")
            bboxMaxArray = cmds.getAttr(sel+".characterBoundingBoxesMax")

        for i in range (0, len(bboxMinArray), 1):
            thisMin = bboxMinArray[i]
            thisMax = bboxMaxArray[i]

            particleX = thisMin[0]+((thisMax[0]-thisMin[0])*0.5)
            particleY = thisMin[1]+((thisMax[1]-thisMin[1])*0.5)
            particleZ = thisMin[2]+((thisMax[2]-thisMin[2])*0.5)

            #cmds.spaceLocator(p=(particleX, particleY, particleZ))

            cmds.emit( object=createdSystem[0], position=((particleX, particleY, particleZ)))

        setDynStartState;
        animationNode = cmds.listConnections( sel+'.animationMessage', d=True, s=True)[0]
        cmds.connectAttr(createdSystem[1]+'.positions', animationNode+'.positionInPP')

#sets keys for TRS on the animaiton attributes
def setShellAnimateKeys(typeNode):
    cmds.setKeyframe(typeNode, at='animationPosition' )
    cmds.setKeyframe(typeNode, at='animationRotation' )
    cmds.setKeyframe(typeNode, at='animationScale' )
    # set the animation attributes as dirty to force evaluation
    cmds.dgdirty('%s.animationPosition' % typeNode)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
