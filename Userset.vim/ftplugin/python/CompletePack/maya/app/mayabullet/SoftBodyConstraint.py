#!/usr/bin/env python
import maya
maya.utils.loadStringResourcesForModule(__name__)

"""
SoftBodyConstraint - Module containing functions for working with soft body constraints
           and MayaBullet. 
"""
import logging
import string

import maya.cmds
import maya.OpenMaya
import maya.mel
# MayaBullet
import maya.app.mayabullet.BulletUtils as BulletUtils
import CommandWithOptionVars
import RigidBody

def centroid( verts ):
    result = [0,0,0]

    for vert in verts:
        pt = maya.cmds.xform(vert, q=True, ws=True, t=True )
        result[0] += pt[0]
        result[1] += pt[1]
        result[2] += pt[2]

    nVerts = len(verts)
    result[0] *= 1.0 / nVerts
    result[1] *= 1.0 / nVerts
    result[2] *= 1.0 / nVerts

    return result

def createSoftBodyAnchorConstraint(selectedVerts=None):
    '''Create a bulletSoftConstraint to anchor selected SoftBody vertices to a
    RigidBody. If no RigidBody is specified, then one will be created and
    centered on the first selected vertex.
    '''

    # Get list of selected verts
    if selectedVerts == None:
        selectedVerts = maya.cmds.ls(sl=True, flatten=True, type='float3') # flattened list
    if len(selectedVerts) == 0:
        maya.OpenMaya.MGlobal.displayError(maya.stringTable[ 'y_SoftBodyConstraint.kPleaseSelectASetOfMeshVertsForTheAnchorConstraint'  ]);
        return

    # extract out the vertex number
    anchoredVertexIds = BulletUtils.extractVertexIds(selectedVerts)

    # Get center of selected vertices
    origTranslate = centroid( selectedVerts )

    # Get meshshape
    objs = maya.cmds.listRelatives(selectedVerts[0], parent=True, type='mesh')
    if objs == None or len(objs) == 0:
        maya.OpenMaya.MGlobal.displayError(maya.stringTable[ 'y_SoftBodyConstraint.kPleaseSelectMeshVertsForTheAnchorConstraint'  ])
        return

    mesh = objs[0]
    # Get $softbody attached to mesh
    # First check if output mesh vert selected, so look for incoming connection
    softbody = ""
    cons = maya.cmds.listConnections(".inMesh", s=1, sh=1, type='bulletSoftBodyShape')
    if cons != None and len(cons) == 1:
        softbody = cons[0]
    else:
        # Otherwise, check input mesh to be connected to a softbody
        cons = maya.cmds.listConnections(".worldMesh[0]",  d=1, sh=1, type='bulletSoftBodyShape')
        if cons != None and len(cons) == 1:
            softbody = cons[0]
    if softbody == "":
        maya.OpenMaya.MGlobal.displayError(maya.stringTable[ 'y_SoftBodyConstraint.kCouldNotDetermineSBShape'  ])
        return

    # Get anchor object
    anchorCandidates = maya.cmds.ls(sl=True, dag=True, shapes=True) # list all selected shape nodes
    numCandidates = len(anchorCandidates)
    if numCandidates==0:
        maya.OpenMaya.MGlobal.displayError(maya.stringTable[ 'y_SoftBodyConstraint.kPleaseSelectOneBulletRigidBodyForAnchorConstraint'  ])
        return

    # use first object found or first rigid body found
    anchorConstrError1 = maya.stringTable[ 'y_SoftBodyConstraint.kPleaseSelectOnlyOneObjectForAnchorConstraint1'  ]
    anchorConstrError2 = maya.stringTable[ 'y_SoftBodyConstraint.kPleaseSelectOnlyOneObjectForAnchorConstraint2'  ]
    anchor = None
    shape = None
    rigidbody = None
    for candidate in anchorCandidates:
        if maya.cmds.objectType( candidate, isType='bulletRigidBodyShape' ):
            if rigidbody is not None:
                maya.OpenMaya.MGlobal.displayError(anchorConstrError1)
                return
            anchor = candidate
            rigidbody = candidate
        else:
            if shape is not None:
                maya.OpenMaya.MGlobal.displayError(anchorConstrError2)
                return
            anchor = candidate
            shape = candidate

    # allow a geometry shape and rigid body shape to be selected as long as the rigid body 
    # shape is connected to the geometry shape and therefore the same 'object'.
    if shape and rigidbody:
        rigidbodies = maya.cmds.listConnections(shape, sh=True, type='bulletRigidBodyShape')
        if rigidbodies is None or rigidbodies[0]!=rigidbody:
            maya.OpenMaya.MGlobal.displayError(anchorConstrError2)
            return

    # Create SoftConstraint
    shape = maya.cmds.createNode("bulletSoftConstraintShape")
    shapeT = maya.cmds.listRelatives(shape, parent=True)[0]
    # Create Solver
    sol = BulletUtils.getSolver()

    maya.cmds.setAttr((shapeT+".translate"), *origTranslate)

    # The logical place for the anchors to be stored is on the constraint node,
    # but in order to remap the indices when the topology changes we have to
    # put it on the soft body node and connect it to the constraint node.  This
    # is an array (multi) attribute, one per constraint; each constraint is
    # itself an int32 array.

    # Find the new index for the anchor.
    anchorListAttr = softbody+".anchors"
    anchorIndices = maya.cmds.getAttr(anchorListAttr, multiIndices=True)
    if anchorIndices:
        anchorNewIndex = anchorIndices[-1] + 1
    else:
        anchorNewIndex = 0
    anchorName = "%s[%d]" % (anchorListAttr, anchorNewIndex)

    # getAttr allocates the new index, then setAttr stores the data,
    # then connectAttr moves the data to where it's used.
    maya.cmds.getAttr(anchorName)
    maya.cmds.setAttr(anchorName, anchoredVertexIds, type='Int32Array')
    maya.cmds.connectAttr(anchorName, shape+".indexList")

    # Connect the simple attributes.
    maya.cmds.connectAttr((sol      +".startTime"),         (shape +".startTime"))
    maya.cmds.connectAttr((sol      +".currentTime"),       (shape +".currentTime"))
    maya.cmds.connectAttr((softbody +".outSoftBodyData"),   (shape +".softBody"))

    if (rigidbody):
        maya.cmds.connectAttr((rigidbody+".outRigidBodyData"),  (shape +".rigidBody"))
    else:
       maya.cmds.connectAttr((anchor   +".worldMatrix"),    (shape +".inWorldMatrix"))

    maya.cmds.connectAttr((shape    +".outConstraintData"), (sol   +".softConstraints"), na=True)
    # Return
    maya.cmds.select(shape)
    ret = [shape]
    
    # If command echoing is off, echo this short line.
    if (not maya.cmds.commandEcho(query=True, state=True)):
        print("SoftBodyConstraint.createSoftBodyAnchorConstraint()")
        print "// Result: %s //" % shape

    return ret
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
