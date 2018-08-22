"""
SoftBodyUI - Module containing functions for managing the soft body
	related UI elements.

"""
# Maya
import maya
maya.utils.loadStringResourcesForModule(__name__)

import maya.cmds as cmds

# MayaBullet
from maya.app.mayabullet import logger


def updateSoftBodyUI( nodeName ):
	"""
	Called when the attribute editor UI for the soft body
	needs to be updated to reflect the latest attribute
	values. Enables and disables controls.
	"""
	logger.debug( maya.stringTable[ 'y_SoftBodyUI.kUpdatingSoftBody'  ] % nodeName )

	generateBendConstraints = cmds.getAttr('{0}.generateBendConstraints'.format(nodeName))
	enableVolumeMatching = cmds.getAttr('{0}.enableVolumeMatching'.format(nodeName))
	enableShapeMatching = cmds.getAttr('{0}.enableShapeMatching'.format(nodeName))

	cmds.editorTemplate( 
		dimControl=(nodeName, "bendResistance",
					not generateBendConstraints) )

	cmds.editorTemplate(
		dimControl=(nodeName, "volumeCoefficient",
					not enableVolumeMatching) )

	cmds.editorTemplate(
		dimControl=(nodeName, "maxVolumeRatio",
					not enableVolumeMatching) )	

	cmds.editorTemplate(
		dimControl=(nodeName, "shapeCoefficient",
					not enableShapeMatching) )
# end

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
