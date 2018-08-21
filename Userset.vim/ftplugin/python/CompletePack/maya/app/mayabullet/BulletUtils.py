"""
BulletUtils - Python module containing general Bullet-related helpers
	and utilities, for use with MayaBullet.

"""
# Python
import maya
maya.utils.loadStringResourcesForModule(__name__)

import re
import types
# Maya
import maya.cmds
import maya.OpenMaya
import maya.api.OpenMaya as OpenMaya
# MayaBullet
from maya.app.mayabullet import logger
import maya.app.mayabullet as mayabullet
from maya.app.mayabullet.Trace import Trace

################## HELPERS #########################################
@Trace()
def _longName( obj ):
	if type(obj) not in [types.StringType,types.UnicodeType]:
		return obj.longName()
	if unicode(obj[0]) != unicode('|'):
		objs = maya.cmds.ls(obj,long=True)
		if len(objs)>1:
			logger.warn( maya.stringTable[ 'y_BulletUtils.kLongNameAmbiguity' ] % obj )
		return objs[0]
	return obj
@Trace()
def _name( obj ):
	return obj.name() if type(obj) not in [types.StringType,types.UnicodeType] else obj.split('|')[-1]
@Trace()
def _isType( obj, typeName ):
	return maya.cmds.objectType(obj).lower() in [typeName.lower()]
@Trace()
def _getChildren( obj, type=None ):
	args = { 'children':True, 'fullPath':True }
	if type:
		args['type']=type
	result = maya.cmds.listRelatives( obj, **args )
	return result if result else []
@Trace()
def _setAttr(obj,attrName,attrVal):
	if type(attrVal) in [types.ListType,types.TupleType]:
		maya.cmds.setAttr('{0}.{1}'.format(obj, attrName), *attrVal )
	elif isinstance(attrVal, OpenMaya.MVector):
		maya.cmds.setAttr('{0}.{1}'.format(obj, attrName), *list(attrVal) )
	else:
		maya.cmds.setAttr( '{0}.{1}'.format(obj, attrName), attrVal )

############################ PUBLIC FUNCTIONS ######################

@Trace()
def checkPluginLoaded(autoLoad=True):
	result = True

	if not maya.cmds.pluginInfo( 'bullet', q=True, loaded=True):
		if autoLoad:
			maya.cmds.loadPlugin('bullet', quiet=True)
			result = maya.cmds.pluginInfo( 'bullet', q=True, loaded=True)
		else:
			result = False

	return result

@Trace()
def selectSolver( bCreateIfMissing=True ):
	solver = getSolver(bCreateIfMissing)
	if solver:
		solverT=maya.cmds.listRelatives([solver], parent=True)[0]
		maya.cmds.select(solverT,r=True)

@Trace()
def getSolver( bCreateIfMissing=True, bCheckForDuplicates=True ):
	"""
	Retrieve name of existing bulletSolverShape in scene or create new one.
	
	Returns:
		str - bulletSolverShape name
	"""
	#Create Solver (proto)
	# Try to get existing solver
	solver = None
	solvers = maya.cmds.ls(type='bulletSolverShape',long=True)
	if len(solvers) > 0:
		solver = solvers[0]  # use the first one found
		if bCheckForDuplicates and len( solvers ) > 1:
			warnMsg = maya.stringTable[ 'y_BulletUtils.kMultipleSolvers'  ] % solver
			maya.cmds.warning( warnMsg )
	elif ( bCreateIfMissing ): 
		# Create New Solver Node
		solver = maya.cmds.createNode('bulletSolverShape')
		if solver:
			# Connect node
			maya.cmds.connectAttr('time1.outTime', (solver+'.currentTime'))
		else:
			errorMsg = maya.stringTable[ 'y_BulletUtils.kErrSolverNotCreated' ]
			maya.OpenMaya.MGlobal.displayError( errorMsg )
	# end-if
		
	# return solver
	return solver
# end


@Trace()
def getConnectedRigidBodies(nodes=None):
	"""
	Return connected RigidBodies
	"""
	return maya.cmds.ls(sl=True, dag=True, type='bulletRigidBodyShape')
# end


@Trace()
def extractVertexIds(vertexStrings):
	"""
	Input:
	  Vertex strings comes from a function like
	  `ls -sl -flatten -type float3` when verts are selected
	  ie. pPlane1_Solved.vtx[35]
	Output:
	  Array of ints with the vert ids
	  ie. 35
	"""
	vertIds = []
	# extract out the vertex number
	for vertexString in vertexStrings:
		vertIds.extend( [int(i) for i in re.findall(r'\.vtx\[(\d+)\]$', vertexString)] )
	return vertIds
#end


@Trace()
def findSelectedBulletShapes():
	"""
	find all bullet nodes within 3 dimensions of connection from the 
	children shapes of the selected nodes in cut and paste operations.
	The connection should not go pass bulletSolverShape because it would
	pull in all the rigid body nodes in the system.
	
	1. In copy and cut, the selected nodes are the transform
	
	   transform
		   shape --> softBody | rigidBody --> constraint
	
	2. In paste, the selected nodes are the mesh construction node if
	   shape has history, otherwise, they are the pairBlend nodes.

	   construction | pairBlend --> shape --> softBody | rigidBody --> constraint
	"""

	# find all the children shapes of the selection list
	srcNodes = []
	tmp = maya.cmds.ls( selection=True )
	if tmp != None:
		srcNodes += tmp
	tmp = maya.cmds.listRelatives(allDescendents=True, shapes=True)
	if tmp != None:
		srcNodes += tmp 

	# find 1 dimension of connection to children shapes
	connNodes = []
	for node in srcNodes:
		tmp = maya.cmds.listConnections(node, sh=True)
		if tmp != None:
			connNodes += tmp 
	# keep unique items
	srcNodes = list(set(connNodes))
	for i in range(len(srcNodes)-1, -1, -1):
		if maya.cmds.nodeType(srcNodes[i]) == "bulletSolverShape":
			del srcNodes[i]

	# find 2 dimensions of connection to children shapes
	for node in srcNodes:
		tmp = maya.cmds.listConnections(node, sh=True)
		if tmp != None:
			connNodes += tmp 
	# keep unique items
	srcNodes = list(set(connNodes))
	for i in range(len(srcNodes)-1, -1, -1):
		if maya.cmds.nodeType(srcNodes[i]) == "bulletSolverShape":
			del srcNodes[i]

	# find 3 dimensions of connection to children shapes
	for node in srcNodes:
		tmp = maya.cmds.listConnections(node, sh=True)
		if tmp != None:
			connNodes += tmp 
	# keep unique items
	srcNodes = list(set(connNodes))
	for i in range(len(srcNodes)-1, -1, -1):
		if maya.cmds.nodeType(srcNodes[i]) == "bulletSolverShape":
			del srcNodes[i]

	# find bullet shapes
	bulletShapes = []
	for node in srcNodes:
		nodeType = maya.cmds.nodeType(node)
		if nodeType in ["bulletRigidBodyShape",
						"bulletRigidBodyConstraintShape",
						"bulletSoftBodyShape",
						"bulletSoftConstraintShape"]:
			if (node not in bulletShapes):
				bulletShapes.append(node)

	return bulletShapes



@Trace()
def disconnectFromSolver( bulletShape ):
	"""
	Given a Bullet shape, disconnect its connections to any
	BulletSolverShape nodes.
	"""
	@Trace()
	def _inputs(obj):
		return zip(	maya.cmds.listConnections( bulletShape, plugs=True, \
							source=True, destination=False ),
					maya.cmds.listConnections( bulletShape, \
							source=True, destination=False, sh=True ) )
	@Trace()
	def _nodeFromPlug(plug):
		return _longName(plug.split('.')[0])
	@Trace()
	def _disconnect( outPlug, inPlug ):
		maya.cmds.disconnectAttr(outPlug, inPlug)

	bulletShape = _longName(bulletShape)

	logger.debug( maya.stringTable[ 'y_BulletUtils.kDisconnectShape' ] % bulletShape )
	# into the shape from other nodes

	for outPlug, outSrc in _inputs(bulletShape):
		if not _isType( outSrc, 'bulletSolverShape' ):
			logger.debug( maya.stringTable[ 'y_BulletUtils.kSkipNonSolverConn' ] % outPlug )
			continue
		# get input plugs connected to output plug
		for inPlug in maya.cmds.connectionInfo(outPlug, \
											  destinationFromSource=True):
			# get the node from plug
			if ( _nodeFromPlug(inPlug) != bulletShape ):
				logger.debug( maya.stringTable[ 'y_BulletUtils.kSkipUnrelatedConn' ] % inPlug )
				continue

			logger.debug( maya.stringTable[ 'y_BulletUtils.kDisconnectConn' ] % (outPlug, inPlug) )
			_disconnect( outPlug, inPlug )
		# end-for
	# end-for

	# these are connections out from the shape to other nodes
	destinations = maya.cmds.listConnections( _longName(bulletShape), plugs=True, \
									source=False, destination=True )
	for inPlug in destinations:
		if ( not _isType(inPlug, 'bulletSolverShape') ):
			logger.debug( maya.stringTable[ 'y_BulletUtils.kSkipNonSolverConn2' ] % inPlug )
			continue

		outPlug \
			= maya.cmds.connectionInfo(_name(inPlug), \
										  sourceFromDestination=True)

		if _nodeFromPlug(outPlug) != bulletShape:
			logger.debug( maya.stringTable[ 'y_BulletUtils.kSkipUnrelatedConn2' ] % outPlug )
			continue

		logger.debug( maya.stringTable[ 'y_BulletUtils.kDisconnectConn2' ] % (outPlug, inPlug) )
		_disconnect( outPlug, inPlug )
	# end-for

	return True
# end


@Trace()
def connectToSolver( bulletShape, solver ):
	"""
	Given a Bullet shape and a BulletSolverShape, connect the
	bullet shape to the solver.
	"""
	@Trace()
	def _connect( outPlug, inPlug, nextAvailable=None ):
		kw = {}
		if nextAvailable:
			kw['nextAvailable']=nextAvailable
		return maya.cmds.connectAttr( outPlug, inPlug, **kw )
	@Trace()
	def _plug( obj, attr ):
		return u'{0}.{1}'.format(obj,attr)

	if type(bulletShape) not in [types.StringType,types.UnicodeType]:
		bulletShape = _longName(bulletShape)
	if type(solver) in [types.StringType,types.UnicodeType]:
		solver = _longName(solver)

	nodes = maya.cmds.listConnections( _longName(bulletShape), source=False, destination=True, sh=True, type="bulletSolverShape" )
	if nodes != None and len(nodes) > 0:
		# return if already connected to a solver
		return False

	if _isType( bulletShape, 'bulletRigidBodyShape' ):
		# connect rigid body to solver
		_connect( _plug(bulletShape,'outRigidBodyData'), _plug(solver,'rigidBodies'), nextAvailable=True)
		_connect( _plug(solver,'outSolverInitialized'), _plug(bulletShape,'solverInitialized'))
		_connect( _plug(solver,'currentTime'), _plug(bulletShape,'currentTime'))
		_connect( _plug(solver,'startTime'), _plug(bulletShape,'startTime'))
		_connect( _plug(solver,'outSolverUpdated'), _plug(bulletShape,'solverUpdated'))

	elif _isType( bulletShape, 'bulletRigidBodyConstraintShape' ):
		# connect rigid body constraint to solver
		_connect( _plug(bulletShape,'outConstraintData'), _plug(solver,'rigidBodyConstraints'), nextAvailable=True)
		_connect( _plug(solver,'outSolverInitialized'), _plug(bulletShape,'solverInitialized'))
		_connect( _plug(solver,'currentTime'), _plug(bulletShape,'currentTime'))
		_connect( _plug(solver,'startTime'), _plug(bulletShape,'startTime'))

	elif _isType( bulletShape, 'bulletSoftBodyShape' ):
		# connect soft body to solver
		_connect( _plug(bulletShape,'outSoftBodyData'), _plug(solver,'softBodies'), nextAvailable=True)
		_connect( _plug(solver,'outSolverInitialized'), _plug(bulletShape,'solverInitialized'))
		_connect( _plug(solver,'currentTime'), _plug(bulletShape,'currentTime'))
		_connect( _plug(solver,'startTime'), _plug(bulletShape,'startTime'))
		_connect( _plug(solver,'outSolverUpdated'), _plug(bulletShape,'solverUpdated'))

	elif _isType( bulletShape, 'bulletSoftConstraintShape' ):
		# connect soft body constraint to solver
		_connect( _plug(bulletShape,'outConstraintData'), _plug(solver,'softConstraints'), nextAvailable=True)
		_connect( _plug(solver,'currentTime'), _plug(bulletShape,'currentTime'))
		_connect( _plug(solver,'startTime'), _plug(bulletShape,'startTime'))

	else:
		warnMsg = maya.stringTable[ 'y_BulletUtils.kUnexpectedShapeInputToSolver' ] \
							 % bulletShape
		maya.cmds.warning( warnMsg )
	# end-if

	return True
# end

@Trace()
def getRigidBodyFromTransform( transform ):
	"""
	Given a transform (by name), return the rigid body.

	This method encapsulates the logic behind the RB
	hierarchies. Currently that hierarchy looks like:

	init_xform
		rb_xform
			rb_shape
	"""
	logger.debug( maya.stringTable[ 'y_BulletUtils.kGettingRB'  ] % transform )
	if transform:
		xformNode = _longName(transform)
	else:
		return None

	# first check if this is a rigid body xform...
	shapeNodes = _getChildren(xformNode, type=("bulletRigidBodyShape",
											  "bulletSoftBodyShape",
											  "bulletSolverShape",
											  "bulletRigidBodyConstraintShape",
											  "bulletSoftConstraintShape") )
	if ( len(shapeNodes) > 1 ):
		logger.warn( maya.stringTable[ 'y_BulletUtils.kExceptedShapeUnder'  ] % xformNode )
	if ( len(shapeNodes) > 0 ):
		return shapeNodes[0]

	# no match? check if the xform was the init xform...
	for childXformNode in _getChildren(xformNode, type="transform" ):
		shapeNodes = _getChildren(childXformNode, type=("bulletRigidBodyShape",
											  "bulletSoftBodyShape",
											  "bulletSolverShape",
											  "bulletRigidBodyConstraintShape",
											  "bulletSoftConstraintShape") )
		if ( len(shapeNodes) > 1 ):
			logger.warn( maya.stringTable[ 'y_BulletUtils.kExceptedShapeUnder2'  ] % childXformNode )
		if ( len(shapeNodes) > 0 ):
			return shapeNodes[0]
	# end-for

	# didn't find any RB shapes in the expected places
	return None
# end

@Trace()
def getSelectedSoftBodies(selection = None):
	'''Description:
		This script returns the selected mesh shape.  The return value contains
		three strings:  the selected mesh transform, node, and the upstream bulletSoftBodyShape node.
	Return: str <softbody nodename>
	'''
	if selection == None:
		selection = maya.cmds.ls(sl=True)
	
	# Sanity check selection
	if len(selection) == 0:
		return None
		
	# Primary: Check for selected bulletSoftBodyShape
	# First check for exact selection
	softbodies = maya.cmds.ls(selection, type='bulletSoftBodyShape')
	if softbodies == None or len(softbodies) == 0:
		softbodies = maya.cmds.listRelatives(selection, noIntermediate=True, shapes=True, type='bulletSoftBodyShape')

	# Secondary: Check for connected mesh connected to bulletSoftBodyShape
	if softbodies == None or len(softbodies) == 0:		
		meshes = maya.cmds.ls(selection, type='mesh')
		if len(meshes) == 0:
			# then check for child shapes
			meshes = maya.cmds.listRelatives(selection, noIntermediate=True, shapes=True, type='mesh')
		# Get connected bulletSoftBodyShape	
		if meshes != None and len(meshes) > 0:		
			softbodies = maya.cmds.listConnections(meshes[0], sh=True, type='bulletSoftBodyShape')

	# Return resulting softbodies
	if softbodies != None and len(softbodies) > 0:
		return softbodies
	else:
		return None

@Trace()
def verifySelectionNotBullet(shapes = None, treatAsError=True):
	result = []

	# Get list of shapes from selection if not passed in
	if (shapes==None):
		return []

	# Make sure the selection doesn't already contain a bullet object.
	softbodies = getSelectedSoftBodies(shapes)
	if softbodies != None:
		maya.OpenMaya.MGlobal.displayError(maya.stringTable['y_BulletUtils.kAlreadyBulletObject1' ])
		return result

	for shape in shapes:
		shapeT = maya.cmds.listRelatives([shape], parent=True)[0]
		rb = getRigidBodyFromTransform(shapeT)
		if rb != None:
			strMsg = maya.stringTable['y_BulletUtils.kAlreadyBulletObject2' ].format(shape)
			if treatAsError:
				maya.OpenMaya.MGlobal.displayError(strMsg)
				return []
			else:
				maya.cmds.warning(strMsg)

		result.append(shape)

	return result

@Trace()
def setAsIntermediateObjects( objects, val=1, deferred=False ):
	# guard against None
	objects = objects if objects else []

	if deferred:
		# delay turning object intermediate so that bulletRigidSet as chance to grab
		# geometry.
		melStr = "import maya.app.mayabullet.BulletUtils as btUtils; btUtils.setAsIntermediateObjects({0},{1}, deferred=False)".format(objects,val)
		maya.cmds.scriptJob(runOnce=True,  idleEvent=melStr)
	else:
		# TODO: cannot use intermediateObject because the bulletRigidSet cannot determine (on reset)
		# which meshShape to use when we turn the intermediate flag on.
		#shapes = maya.cmds.ls( list(objects), long=True, dagObjects=True, geometry=True, intermediateObjects=False )
		#for shape in shapes:
		#	_setAttr( shape, 'intermediateObject', val )
		for object in objects:
			# handle groups
			meshShapes = maya.cmds.listRelatives( object, allDescendents=True, noIntermediate=True, type="mesh" )
			if meshShapes:
				meshTransforms = maya.cmds.listRelatives(meshShapes, parent=True)
				if meshTransforms:
					for meshTransform in meshTransforms:
						_setAttr( meshTransform, 'visibility', val==0 )

@Trace()
def removeBulletObjectsFromList(objects = None):
	'''
	Description:
		remove all bullet node from objects

	Limitations: soft bodies not implemented (copy code from DeleteEntireSystem)
	'''
	@Trace()
	def listSiblings(node, parent=None):
		if not parent:
			parent = maya.cmds.listRelatives(node, parent=True)
		siblings = maya.cmds.listRelatives(parent, children=True)
		siblings.remove(node)
		return siblings

	@Trace()
	def findRigidBodyDependents(rs):
		result = []
		ragdollRoots = []

		# If the rigid body is dynamic, remove the pairBlend node before the rigid
		# body gets deleted.  Otherwise the pairBlend will cause the rigid body's
		# transform to be reset.
		if maya.cmds.getAttr(rs + ".bodyType") == 2:
			result += list(set(maya.cmds.listConnections( rs, type="pairBlend")))

		# rigid body transform has no more children so it is safe 
		# to delete.
		parents = maya.cmds.listRelatives( rs, parent=True )

		if len(listSiblings(rs,parents[0])) == 0:
			result.append( parents[0] )
		else:
			result.append( rs )

		# If grand-parent is a transform and it's name starts with 'Ragdoll'
		# NOTE: if the root was renamed then we don't delete because
		# we cannot differentiate between a locator created by the user
		# and one created by the bullet system.
		grandparents = maya.cmds.listRelatives( parents, parent=True )

		if grandparents and len(grandparents) and "Ragdoll" in grandparents[0]:
			ragdollRoots.append( grandparents[0] )

		# check collected ragdoll roots, if they have no more children
		# then they are safe to delete.
		for ragdollRoot in ragdollRoots:
			childNodes = maya.cmds.listRelatives(ragdollRoot, children=True)
			if childNodes and len(childNodes):
				result.append( ragdollRoot )

		return result

	@Trace()
	def findConnectedMesh( node ):
		result = None

		objType = maya.cmds.objectType(node)

		if objType=='mesh':
			return maya.cmds.listRelatives([node], parent=True)[0]

		attr1 = '{0}.outMesh'.format(node)
		attr2 = '{0}.outputGeometry'.format(node)
		attr = attr1 if maya.cmds.objExists(attr1) else attr2 if maya.cmds.objExists(attr2) else None

		if attr:
			objs = maya.cmds.listConnections( attr, shapes=True )
			objs = objs if objs else []

			for obj in objs:
				result = findConnectedMesh( obj )
				if result:
					break

		return result

	@Trace()
	def findSetDependents(rbSet):
		result = []

		# get initial state
		rbInitialState = maya.cmds.listConnections( '{0}.usedBy'.format(rbSet), sh=True, t='bulletInitialState')
		if  rbInitialState:
			result.append(rbInitialState[0])
			# get solved state
			rbSolvedState = maya.cmds.listConnections( '{0}.solvedState'.format(rbInitialState[0]), sh=True, t='bulletRigidCollection')
			if  rbSolvedState:
				result.append(rbSolvedState[0])
				# get output mesh
				rbMesh = findConnectedMesh( rbSolvedState[0] )
				if  rbMesh:
					result.append(rbMesh)

		return result

	toDelete = []

	if not objects:
		objects = maya.cmds.ls(sl=True)

	rbObjects = maya.cmds.ls(objects, type='transform')
	rbSets = maya.cmds.ls(objects, type='bulletRigidSet')

	if len(rbObjects):
		rbShapes = maya.cmds.listRelatives( rbObjects, ad=True, type='bulletRigidBodyShape')
		rbShapes = rbShapes if rbShapes else []

		for rbShape in rbShapes:
			toDelete += findRigidBodyDependents(rbShape)

		# Remove objects from bulletRigidSets
		from collections import defaultdict
		toRemoveFromSet = defaultdict( lambda : [] )

		for object in objects:
			setList = maya.cmds.listSets( object=object )
			rbSetList = maya.cmds.ls(setList,type='bulletRigidSet') if setList else []

			for rbSet in rbSetList:
				toRemoveFromSet[rbSet].append(object)

		for rbSet, rbSetMembers in toRemoveFromSet.iteritems():
			maya.cmds.sets( rbSetMembers, remove=rbSet )

			# Remove empty bulletRigidSets along with their initial states, solved states and output mesh
			if maya.cmds.sets( rbSet, q=True, size=True ) == 0:
				toDelete.append(rbSet)
				toDelete.extend(findSetDependents(rbSet))

	if len(rbSets):
		for rbSet in rbSets:
			members = maya.cmds.sets( rbSet, q=True )
			setAsIntermediateObjects( members, 0 )
			toDelete.append(rbSet)
			toDelete.extend(findSetDependents(rbSet))

	if len(toDelete):
		maya.cmds.delete( list(set(toDelete)) )



# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
