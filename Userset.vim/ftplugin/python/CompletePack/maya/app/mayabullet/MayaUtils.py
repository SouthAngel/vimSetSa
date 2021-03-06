"""
MayaUtils - Python module containing Maya-related utility functions for
			MayaBullet.

"""
# Maya
import maya
maya.utils.loadStringResourcesForModule(__name__)

import maya.mel as mel
import maya.cmds as cmds
import maya.OpenMaya as om
# MayaBullet
from maya.app.mayabullet import logger as logger
import maya.app.mayabullet as mayabullet
from maya.app.mayabullet.Trace import Trace
# Python
import os.path

bulletDagPaths = []
bulletCutCopyPasteCBId = 0

############################ PUBLIC FUNCTIONS ######################

@Trace()
def handlePreCut():
	"""
	Callback dispatched just before the export on a Cut operation,
	from the customized implementation of cutCopyPaste.mel. This only
	happens if the current selection includes any Bullet shapes.
	"""
	_disconnectSelection()
# end


@Trace()
def handlePreCopy():
	"""
	Callback dispatched just before the export on a Copy operation,
	from the customized implementation of cutCopyPaste.mel. This only
	happens if the current selection includes any Bullet shapes.
	"""
	_disconnectSelection()
# end


@Trace()
def handlePostCopy():
	"""
	Callback dispatched just after the export on a Copy operation,
	from the customized implementation of cutCopyPaste.mel. This only
	happens if the current selection includes any Bullet shapes.

	In the preCopy, we disconnected the solver from the Bullet
	shapes. Here, we need to reconnect them.
	"""
	_reconnectSelection()
# end

@Trace()
def handlePrePaste():
	"""
	Callback dispatched just before the import on a Paste operation,
	from the customized implementation of cutCopyPaste.mel. This
	happens on every paste operation, even if there are no Bullet
	shapes involved.

	Since we disconnected the solver on cut/copy, after pasting, the
	newly created Bullet shapes will not be connected to a solver. This 
	is fixed by adding addNodeAddedCallback at prePaste and deleting 
	the callback at postPaste. The callback will collect all the 
	bulletShapes to be connected to the solver.
	"""
	global bulletCutCopyPasteCBId
	bulletCutCopyPasteCBId = om.MDGMessage.addNodeAddedCallback(bulletCutCopyPasteCB)
# end

@Trace()
def handlePostPaste():
	"""
	Callback dispatched just after the import on a Paste operation,
	from the customized implementation of cutCopyPaste.mel. This
	happens on every paste operation, even if there are no Bullet
	shapes involved.

	Since we disconnected the solver on cut/copy, after pasting, the
	newly created Bullet shapes will not be connected to a solver. This 
	is fixed by adding addNodeAddedCallback at prePaste and deleting 
	the callback at postPaste. The callback will collect all the 
	bulletShapes to be connected to the solver.
	"""
	global bulletCutCopyPasteCBId
	om.MMessage.removeCallback(bulletCutCopyPasteCBId)
	_reconnectBulletShapes()
# end

@Trace()
def getScriptDir():
	"""
	Returns the full path to the Bullet plug-in's scripts directory.
	"""
	pluginPath = pluginInfo( "bullet", query=True, path=True )
	pluginDir = os.path.dirname( pluginPath ) + "/../scripts"
	pluginDir = os.path.normpath( pluginDir ).replace('\\', '\\\\')
	return pluginDir
# end


@Trace()
def rawScriptResultToPath( rawResult ):
	"""
	The whatIs command returns a string like:

	Script found in: /usr/autodesk/maya/scripts/startup/cutCopyPaste.mel

	which we'd like to parse into just the useful bit at the end.
	"""
	return rawResult.rsplit( "Script found in: ", 1  )[1]
# end


############################ INTERNAL HELPERS ###############################

@Trace()
def _disconnectSelection():
	"""
	Cut and Copy do an export of the current selection. If the
	selected bullet shapes are connected to the solver, then the
	export will drag in everything connected to the solver, i.e. all
	of the bullet shapes in the scene. To avoid this, we disconnect
	the shapes from the solver before export.
	"""
	selectedBulletShapes = mayabullet.BulletUtils.findSelectedBulletShapes()
	for bulletShape in selectedBulletShapes:
		mayabullet.BulletUtils.disconnectFromSolver( bulletShape )
	# end-for
# end


@Trace()
def _reconnectSelection():
	"""
	When a scene is pasted, the pasted Bullet shapes will not be
	connected to the solver, so we connect them in this method.
	"""
	try:
		existingSolverShape \
			= mayabullet.BulletUtils \
						  .getSolver(bCreateIfMissing=False, \
									 bCheckForDuplicates=False)
	except:
		# if we don't actually need to use the solver, then this error
		# is harmless and should be ignored.
		existingSolverShape = None

	selectedBulletShapes = mayabullet.BulletUtils.findSelectedBulletShapes()
	for bulletShape in selectedBulletShapes:
		if existingSolverShape is None:
			# if we get to the point of actually trying to use the
			# solver, and it's not present, then an error has
			# occurred.
			logger.error( maya.stringTable['y_MayaUtils.kMissingSolver' ])
			return
		mayabullet.BulletUtils.connectToSolver( bulletShape, 
												existingSolverShape )
	# end-for
# end


@Trace()
def _reconnectBulletShapes():
	"""
	When a scene is pasted, the pasted Bullet shapes will not be
	connected to the solver, so we connect them in this method.
	"""
	global bulletDagPaths
	try:
		existingSolverShape \
			= mayabullet.BulletUtils \
						.getSolver(bCreateIfMissing=False, \
									 bCheckForDuplicates=False)
	except:
		# if we don't actually need to use the solver, then this error
		# is harmless and should be ignored.
		existingSolverShape = None

	for bulletDagPath in bulletDagPaths:
		bulletShape = bulletDagPath.fullPathName()
		if existingSolverShape is None:
			# if we get to the point of actually trying to use the
			# solver, and it's not present, then an error has
			# occurred.
			logger.error( maya.stringTable['y_MayaUtils.kMissingSolver2' ])
			return
		mayabullet.BulletUtils.connectToSolver( bulletShape, 
												existingSolverShape )
	bulletDagPaths = []
	# end-for
# end


@Trace()
def bulletCutCopyPasteCB(object, clientData):
	global bulletDagPaths
	isDagObject = True
	try:
		nodeFn = om.MFnDagNode(object)

	except:
		isDagObject = False

	if not isDagObject:
		return

	nodeName = nodeFn.name()
	nodeType = maya.cmds.nodeType(nodeName)
	if nodeType in ["bulletRigidBodyShape",
					"bulletRigidBodyConstraintShape",
					"bulletSoftBodyShape",
					"bulletSoftConstraintShape"]:
		dagPath = om.MDagPath()
		nodeFn.getPath(dagPath)
		bulletDagPaths.append(dagPath)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
