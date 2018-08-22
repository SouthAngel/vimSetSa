"""
RigidBodyUI - Module containing functions for managing the rigid body
	related UI elements.

"""
# Maya
import maya
maya.utils.loadStringResourcesForModule(__name__)

import maya.cmds

# MayaBullet
from maya.app.mayabullet.RigidBody import (eShapeType as eShapeType)
from maya.app.mayabullet import logger

def _getAttr(obj,attrName):
	return maya.cmds.getAttr('{0}.{1}'.format(obj,attrName))

def updateColliderUI( nodeName ):
	"""
	Called when the attribute editor UI for the rigid body
	needs to be updated to reflect the latest attribute
	values. Enables and disables controls.
	"""
	logger.debug( maya.stringTable[ 'y_RigidBodyUI.kUpdatingCollider'  ] % nodeName )

	cst = _getAttr(nodeName, 'colliderShapeType')
	autoFit = _getAttr(nodeName, 'autoFit')

	maya.cmds.editorTemplate(
		dimControl=(nodeName,"colliderShapeOffset",
					autoFit ) )
	maya.cmds.editorTemplate(
		dimControl=(nodeName,"axis",
					autoFit or cst
						not in (eShapeType.kColliderCylinder,
								eShapeType.kColliderCapsule)) )
	maya.cmds.editorTemplate(
		dimControl=(nodeName,"length",
					autoFit or cst
						not in (eShapeType.kColliderCylinder,
								eShapeType.kColliderCapsule)) )
	maya.cmds.editorTemplate(
		dimControl=(nodeName,"radius",
					autoFit or cst
						not in (eShapeType.kColliderCylinder,
								eShapeType.kColliderCapsule,
								eShapeType.kColliderSphere)) )
	maya.cmds.editorTemplate( 
		dimControl=(nodeName,"extents",
					autoFit or cst
						not in (eShapeType.kColliderBox,)) )

def updateNeverSleepUI( nodeName ):
	"""
	Called when the attribute editor UI for the rigid body
	needs to be updated to reflect the latest attribute
	values. Enables and disables controls.
	"""
	neverSleeps = _getAttr(nodeName,"neverSleeps")
	maya.cmds.editorTemplate( 
		dimControl=(nodeName,"initiallySleeping", neverSleeps) )
# end
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
