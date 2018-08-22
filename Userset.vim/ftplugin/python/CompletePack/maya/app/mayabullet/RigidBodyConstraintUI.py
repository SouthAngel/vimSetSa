"""
RigidBodyConstraintUI - Module containing functions for managing the
	constraint related UI elements.
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


# Maya
import maya.cmds as cmds

# MayaBullet
from maya.app.mayabullet.RigidBodyConstraint import dictConstraintAttributes
from maya.app.mayabullet import logger

def _enableControl( nodeName, attrName, constraintType, supportedTypes ):
	"""
	A small helper function that reduces code duplication for toggling UI
	controls on/off based on the selected constraint type.
	"""
	cmds.editorTemplate( dimControl=(nodeName, attrName,
								constraintType not in supportedTypes) )
# end


def updateConstraintUI( nodeName ):
	"""
	Called when the attribute editor UI for the rigid body constraints
	needs to be updated to reflect the latest attribute
	values. Enables and disables controls.
	"""
	logger.debug( maya.stringTable[ 'y_RigidBodyConstraintUI.kUpdatingConstrUI'  ] % nodeName )

	# Limit Properties section
	constraintType = cmds.getAttr('{0}.constraintType'.format(nodeName))
	for attrName in dictConstraintAttributes.keys():
		_enableControl( nodeName, attrName, constraintType, dictConstraintAttributes[attrName] )

	linearMotorEnabled = cmds.getAttr('{0}.linearMotorEnabled'.format(nodeName))
	cmds.editorTemplate( dimControl=(nodeName, "linearMotorTargetSpeed", not linearMotorEnabled))
	cmds.editorTemplate( dimControl=(nodeName, "linearMotorMaxForce", not linearMotorEnabled))

	angularMotorEnabled = cmds.getAttr('{0}.angularMotorEnabled'.format(nodeName))
	cmds.editorTemplate( dimControl=(nodeName, "angularMotorTargetSpeed", not angularMotorEnabled))
	cmds.editorTemplate( dimControl=(nodeName, "angularMotorMaxForce", not angularMotorEnabled))

# end
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
