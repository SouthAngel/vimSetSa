import maya.cmds
import maya.OpenMaya as om
def meshHeight(name, x, z):
    # mesh object  
    selectionList = om.MSelectionList()
    selectionList.add( name )
    nodeDagPath = om.MDagPath()
    selectionList.getDagPath(0, nodeDagPath )
    
    meshObj =  om.MFnMesh(nodeDagPath)

    # position FP
    posFP = om.MFloatPoint(x,1000,z)

    # dir FP
    dirFP = om.MFloatVector(0,-1,0)

    # empty objects
    hitFPoint = om.MFloatPoint()	# intersection
    hitFace = om.MScriptUtil()
    hitTri = om.MScriptUtil()
    hitFace.createFromInt(0)
    hitTri.createFromInt(0)

    hFacePtr = hitFace.asIntPtr()
    hTriPtr = hitTri.asIntPtr()

    farclip = 10000.0

    hit = meshObj.closestIntersection( posFP,
    dirFP,
    None,
    None,
    True,
    om.MSpace.kWorld,
    farclip,
    True,
    None,
    hitFPoint,
    None,
    hFacePtr,
    hTriPtr,
    None,
    None)

    return hitFPoint[1]# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
