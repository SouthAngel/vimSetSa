"""
RigidBody - Module containing functions for working with rigid bodies
			and MayaBullet. 

"""
import maya
maya.utils.loadStringResourcesForModule(__name__)

import string
import types
# Maya
import maya.cmds
import maya.mel
import maya.api.OpenMaya as OpenMaya

# MayaBullet
import maya.app.mayabullet.BulletUtils as BulletUtils
import CommandWithOptionVars
from maya.app.mayabullet import logger
from maya.app.mayabullet.Trace import Trace


################################### ENUMS ###################################

class eShapeType:
	kColliderNone	  = 0
	kColliderBox	  = 1
	kColliderSphere	  = 2
	kColliderCapsule  = 3
	kColliderHull	  = 4
	kColliderMesh	  = 5
	kColliderPlane	  = 6
	kColliderCylinder = 7
	kColliderHACD	 = 8
	kColliderCompound = 9
# end

class eAxisType:
	kXAxis	  = 0
	kYAxis	  = 1
	kZAxis	  = 2
# end

class eBodyType:
	kStaticBody			= 0	 # non-moving
	kKinematicRigidBody = 1	 # user-animatable
	kDynamicRigidBody	= 2	 # dynamics system driven
# end

############################### PYMEL SUBSTITUTES ##############################
@Trace()
def _longName( obj ):
	if type(obj) not in [types.StringType,types.UnicodeType]:
		return obj.longName()
	if unicode(obj[0]) != unicode('|'):
		objs = maya.cmds.ls(obj,long=True)
		if len(objs)>1:
			logger.warn( maya.stringTable[ 'y_RigidBody.kLongNameAmbiguity' ] % obj )
		return objs[0]
	return obj
@Trace()
def _name( obj ):
	return obj.name() if type(obj) not in [types.StringType,types.UnicodeType] else obj.split('|')[-1]
@Trace()
def _getChildren( obj, type=None ):
	args = { 'children':True, 'fullPath':True }
	if type:
		args['type']=type
	result = maya.cmds.listRelatives( obj, **args )
	return result if result else []
@Trace()
def _numChildren(obj, type=None):
	return len(_getChildren(obj, type))
@Trace()
def _firstParent(obj):
	l= maya.cmds.listRelatives( obj, fullPath=True, parent=True )
	return l[0] if l else None
@Trace()
def _setAttr(obj,attrName,attrVal):
	if type(attrVal) in [types.ListType,types.TupleType]:
		maya.cmds.setAttr('{0}.{1}'.format(obj, attrName), *attrVal )
	elif isinstance(attrVal, OpenMaya.MVector):
		maya.cmds.setAttr('{0}.{1}'.format(obj, attrName), *list(attrVal) )
	else:
		maya.cmds.setAttr( '{0}.{1}'.format(obj, attrName), attrVal )
@Trace()
def _getAttr(obj,attrName):
	return maya.cmds.getAttr('{0}.{1}'.format(obj,attrName))
@Trace()
def _attr(obj,attrName):
	return '{0}.{1}'.format(obj,attrName)
@Trace()
def _connectAttr( outPlug, inPlug, nextAvailable=None, force=None ):
	kw = {}
	if nextAvailable:
		kw['nextAvailable']=nextAvailable
	if force:
		kw['force']=force
	return maya.cmds.connectAttr( outPlug, inPlug, **kw )

############################### HELPER FUNCTIONS ###############################
@Trace()
def _getSelectedShapes(transform=None):
	return maya.cmds.listRelatives(transform,s=True, ni=True, fullPath=True, type='mesh') if transform else maya.cmds.listRelatives(s=True, ni=True, fullPath=True, type='mesh') 
# end
@Trace()
def _getSelectedTransforms():
	return maya.cmds.ls( long=True, selection=True, type="transform" )
# end

@Trace()
def centerOfMass(nodeT):
	# Use transform rotation pivot for centerOfMass
	return list(maya.cmds.getAttr(nodeT+".rp")[0])

@Trace()
def refitCollisionShape(rigidBodyName, mesh = None, transform = None):
	'''
	Description:
		This method refits the collision shape for the simulated object.
		New values for radius, length, extents are computed from the mesh's
		bounding box.
		The center of mass is reset based on the object's
		rotation pivot.
	'''
	@Trace()
	def groupBBox(parent,bbox):
		meshes = maya.cmds.listRelatives(parent, ad=True, ni=True, type='mesh')
		meshes = meshes if meshes else []
		for mesh in meshes:
			xmin, ymin, zmin = list(maya.cmds.getAttr((mesh+".boundingBoxMin"))[0])
			xmax, ymax, zmax = list(maya.cmds.getAttr((mesh+".boundingBoxMax"))[0])
			bbox.expand(maya.OpenMaya.MPoint(xmin,ymin,zmin))
			bbox.expand(maya.OpenMaya.MPoint(xmax,ymax,zmax))

	@Trace()
	def groupExtents(parent):
		bbox = maya.OpenMaya.MBoundingBox()
		groupBBox(parent,bbox)
		center = bbox.center()
		
		return [bbox.width(), bbox.height(), bbox.depth(), center.x,center.y,center.z]

	@Trace()
	def nodeExtents(mesh):
		# return bounding min/max in local space
		xmin, ymin, zmin = list(maya.cmds.getAttr((mesh+".boundingBoxMin"))[0])
		xmax, ymax, zmax = list(maya.cmds.getAttr((mesh+".boundingBoxMax"))[0])
		return [(xmax - xmin), (ymax - ymin), (zmax - zmin), (xmax+xmin) * 0.5,(ymax+ymin) * 0.5, (zmax+zmin) * 0.5]

	@Trace()
	def computeRadiusAndLength( colliderShapeType, axis, dx, dy, dz ):
		# REVIST: this assume that the center mass is also at the 
		# center of vertices which is not always the case
		if (colliderShapeType == eShapeType.kColliderCapsule ):
			if (axis == eAxisType.kXAxis):
				radius = 0.5 * max(dy, dz)
				length = dx
			elif (axis == eAxisType.kYAxis):
				radius = 0.5 * max(dx, dz)
				length = dy
			else:
				radius = 0.5 * max(dx, dy)
				length = dz
		elif (colliderShapeType == eShapeType.kColliderCylinder ):
			if (axis == eAxisType.kXAxis):
				radius = 0.5 * max(dy, dz) 
				length = dx
			elif (axis == eAxisType.kYAxis):
				radius = 0.5 * max(dx, dz)
				length = dy
			else:
				radius = 0.5 * max(dx, dy)
				length = dz
		else:
			radius = 0.5 * max(dx, dy, dz)
			length = 2.0 * radius

		return radius, length

	@Trace()
	def computeShapeOffset( rbT, bboxPos=[0.0,0.0,0.0], comPos=[0.0,0.0,0.0] ):
		# We want the implicit collision shapes (box etc) to 
		# centered around the bounding box center so, we need to make
		# the collider shift offset relative to the center of mass
		rtn = (bboxPos[0]-comPos[0]), (bboxPos[1]-comPos[1]), (bboxPos[2]-comPos[2])

		scl = maya.cmds.xform(rbT, q=True, relative=True, scale=True)

		# if scaling applied then remove
		if scl[0]!=1.0 or scl[1]!=1.0 or scl[2]!=1.0:
			m = [
				scl[0],	0.0,	0.0,	0.0,
				0.0,	scl[1],	0.0,	0.0,
				0.0,	0.0,	scl[2],	0.0,
				0.0,	0.0,	0.0,	1.0 ]

			pt = OpenMaya.MFloatPoint(rtn)
			sclMat = OpenMaya.MFloatMatrix(m)

			# return x,y,z
			rtn = list(pt * sclMat.inverse())[:-1]

		return rtn

	radius, length = 0.0,0.0
	ex, ey, ez = 0.0,0.0,0.0			# extents
	csoX, csoY, csoZ = 0.0,0.0,0.0		# collider shift offset
	bboxX, bboxY, bboxZ = 0.0,0.0,0.0	# center of bbox

	colliderShapeType = _getAttr(rigidBodyName,'colliderShapeType')
	axis = _getAttr(rigidBodyName,'axis')
	rbT = _firstParent(rigidBodyName)
	comX, comY, comZ = centerOfMass(rbT)

	if mesh:
		ex, ey, ez, bboxX, bboxY, bboxZ  = nodeExtents(mesh)
	elif transform:
		# check we're not just a bullet object
		if not _numChildren(transform, type='transform'):
			return
		ex, ey, ez, bboxX, bboxY, bboxZ = groupExtents(transform)

	if colliderShapeType not in [eShapeType.kColliderHull,eShapeType.kColliderMesh,eShapeType.kColliderHACD,eShapeType.kColliderCompound]:
		csoX, csoY, csoZ = computeShapeOffset( rbT, [bboxX, bboxY, bboxZ], [comX, comY, comZ] )

	radius, length = computeRadiusAndLength(colliderShapeType, axis, ex, ey, ez)

	_setAttr(rigidBodyName,'radius', radius)
	_setAttr(rigidBodyName,'length', length)
	_setAttr(rigidBodyName,'extents', [ex, ey, ez] )
	# COM will include local scaling if scaling has been used
	_setAttr(rigidBodyName,'centerOfMass', [comX, comY, comZ])
	# CSO must not include local scaling.
	_setAttr(rigidBodyName,'colliderShapeOffset', [csoX, csoY, csoZ])

	return [radius, length, ex, ey, ez, comX, comY, comZ]
# end

################################# PUBLIC API ################################

class CreateRigidBody( CommandWithOptionVars.CommandWithOptionVars ):
	"""
	Add a new rigid body to the scene.
	"""
	
	scriptJobNum = -1

	settableAttrs = [
		'colliderShapeType',
		'colliderShapeMargin',
		'colliderShapeOffset',
		'axis',
		'length',
		'radius',
		'extents',
		'bodyType',
		'initiallySleeping',
		'neverSleeps',
		'linearDamping',
		'mass',
		'angularDamping',
		'friction',
		'restitution',
		'initialVelocity',
		'initialAngularVelocity',
		'impulse',
		'torqueImpulse',
		'centerOfMass',
		'autoFit',
		]

	@Trace()
	def __init__(self, isActive=True):
		super(CreateRigidBody, self).__init__()
		
		self.commandName = 'CreateRigidBody'
		self.commandHelpTag = 'BulletCreateRigidBody' if isActive else 'BulletCreatePassiveBody'
		self.l10nCommandName = maya.stringTable['y_RigidBody.kCreateRigidBody' ]
		self.optionVarPrefix = 'bullet_RigidBody_'
		self.optionVarDefaults = {
			'colliderShapeType' : eShapeType.kColliderBox,
			'colliderShapeOffset' : [0.0, 0.0, 0.0],
			'colliderShapeMargin' : 0.04,
			'axis'		 : eAxisType.kYAxis,
			'autoFit'	 : True,
			'hideShape'	 : False,
			'length'		 : 1.0,
			'radius'		 : 0.5,
			'extents'		 : [1.0, 1.0, 1.0],
			'bodyType'		 : eBodyType.kDynamicRigidBody,
			'initiallySleeping' : False,
			'neverSleeps'	 : False,
			'mass'			 : 1.0,
			'linearDamping'	 : 0.0,
			'angularDamping' : 0.0,
			'friction'		 : 1.0,
			'restitution'	 : 0.0,
			'initialVelocity': [0.0, 0.0, 0.0],
			'initialAngularVelocity': [0.0, 0.0, 0.0],
			'impulse'		 : [0.0, 0.0, 0.0],
			'torqueImpulse'	 : [0.0, 0.0, 0.0],
			'centerOfMass'	 : [0.0, 0.0, 0.0],
		}
		
		# List of collider option widgets whose availability depends on whether a mesh
		# is selected or not.
		self.colliderOptionWidgets = {}
		self.box = ""
		
		# Update the body type option var depending on whether the creation is for an active
		# or a passive rigid body.  For an active rigid body, make sure the body type
		# starts out as Dynamic.  Otherwise for a passive body, make sure the body type
		# starts out as Static.
		if not isActive:
			self.optionVarDefaults['bodyType'] = eBodyType.kStaticBody
		bodyTypeVar = self.optionVarPrefix + 'bodyType'
		currentType = maya.cmds.optionVar(q=bodyTypeVar)
		if isActive and (currentType != eBodyType.kDynamicRigidBody):
			maya.cmds.optionVar(iv=(bodyTypeVar, eBodyType.kDynamicRigidBody))
		elif (not isActive) and (currentType != eBodyType.kStaticBody):
			maya.cmds.optionVar(iv=(bodyTypeVar, eBodyType.kStaticBody))


	@staticmethod
	@Trace()
	def command(*args, **kwargs ):
		ret = []

		transformNames = []
		if (kwargs.has_key('bAttachSelected') and not kwargs['bAttachSelected']):
			if kwargs.has_key('transformName'):
				transformNames = [kwargs['transformName']]
		else:
			# Make sure the list doesn't contain any bullet objects.
			transformNames = _getSelectedTransforms()

		if (kwargs.has_key('ignoreShape') and kwargs['ignoreShape']):
			shapes = []
		else:
			shapes = _getSelectedShapes(transformNames)

		# remove transforms already processed as shapes
		if shapes and transformNames and len(transformNames):
			filteredTransformNames = []

			for transformName in transformNames:
				ts = _getSelectedShapes(transformName)
				ts = ts if ts else []
				if len(ts)==0 or len(set(ts).intersection(shapes))==0:
					filteredTransformNames.append(transformName)
			transformNames = filteredTransformNames

		# if no shapes and no transforms create bullet object without node
		if (not transformNames or len(transformNames)==0) and (not shapes or len(shapes) == 0):
			transformNames = [None] 

		if shapes and len(shapes):
			kwargs['shapes'] = shapes
			rbShapes = CreateRigidBody.command_shape(**kwargs)
			ret += rbShapes if rbShapes else []

		if len(transformNames):
			# Create rigid bodies without an associated shape

			# Verify collision shape type is valid.
			if (kwargs.has_key('colliderShapeType')):
				shapeType = kwargs['colliderShapeType']
				if (shapeType == eShapeType.kColliderHull) or (shapeType == eShapeType.kColliderMesh):
					kwargs['colliderShapeType'] = eShapeType.kColliderBox

			for transformName in transformNames:
				# Make sure the transformName doesn't contain any bullet objects.
				if transformName and BulletUtils.getRigidBodyFromTransform(transformName):
					OpenMaya.MGlobal.displayWarning(maya.stringTable['y_RigidBody.kAlreadyBulletObject2' ].format(transformName) )
					continue

				kwargs['transformName'] = transformName

				rbShapes = CreateRigidBody.doCommand(*args, **kwargs)
				ret += rbShapes
				rbShape = _longName(rbShapes[1])

				if transformName and kwargs.has_key('autoFit') and kwargs['autoFit']:
					(radius, length, ex, ey, ez, cx, cy, cz) = refitCollisionShape(rbShape, transform=transformName)
					kwargs['radius'] = radius
					kwargs['length'] = length
					kwargs['extents'] = [ex, ey, ez]
					kwargs['centerOfMass'] = [cx, cy, cz] 

		if len(ret):
			maya.cmds.select(ret, r=True)

		# If command echoing is off, echo this short line.
		if (not maya.cmds.commandEcho(query=True, state=True)):
			print("RigidBody.CreateRigidBody().executeCommandCB()")
			print "// Result: %s //" % string.join(ret, " ")

		return ret

	@staticmethod
	@Trace()
	def doCommand(name='bulletRigidBodyShape#',
				transformName = None,
				bAttachSelected = True,
				ignoreShape = False,
				hideShape = False,
				# Attrs
				colliderShapeType = None,
				axis = None,
				length = None,
				radius = None,
				extents = None,
				bodyType = None,
				initiallySleeping = None,
				neverSleeps = None,
				mass = None,
				linearDamping = None,
				angularDamping = None,
				friction = None,
				restitution = None,
				initialVelocity = None,
				initialAngularVelocity = None,
				impulse = None,
				torqueImpulse = None,
				centerOfMass = None,
				autoFit = None,
				colliderShapeOffset = None,
				colliderShapeMargin = None,
				**kwargs ):
		'''Create a bulletRigidBody 
		'''
		# Explicitly list the names of settable attributes iterated over below

		# Check for selection being a rigid body already
		if ( bAttachSelected ):
			selectedObjs = _getSelectedTransforms()
			selectedObj = selectedObjs[0] if len(selectedObjs) else None

			# don't attach a rigid body underneath another one during
			# creation, it's more likely that the user is invoking
			# this command multiple times, and the selection is
			# leftover from a previous invocation. 
			if ( BulletUtils.getRigidBodyFromTransform(selectedObj) is not None ):
				selectedObj = None
			else:
				transformName = selectedObj
		else:
			selectedObj = None

		if not transformName:
			transformName=''

		# Create from scratch
		rbShape = maya.cmds.createNode( "bulletRigidBodyShape", name=name, parent=transformName )
		rbXform = _firstParent(rbShape)

		if not rbXform:
			OpenMaya.MGlobal.displayError(maya.stringTable[ 'y_RigidBody.kErrorRigidBodyNotCreated' ])
			return [ None, None ]

		# Performance: if we're attaching to an object 
		# make rbShape an visibility so it doesn't draw by default.
		# NOTE: since the rigid body is not a MPxShape it doesn't
		# support an intermediateObject attribute.
		if transformName and hideShape:
			_setAttr(rbShape, 'visibility', 0)

		# Create Solver (proto)
		solver = BulletUtils.getSolver()

		# Set Attrs (optional, set if value != None)
		# Use the settableAttrs list above to qualify kwargs passed into the function
		for k,v in locals().iteritems():
			if k in CreateRigidBody.settableAttrs and v != None:
				_setAttr( rbShape, k, v )

		# Additional Actions

		# ******* TODO: Need to enable local transform instead of just worldSpace.  Pass in parentMatrix to rigidbody

		# Store t and r (used below)
		origTranslate = _getAttr(rbXform, 'translate')[0]
		origRotate = _getAttr(rbXform,'rotate')[0]

		# Connect
		_connectAttr( _attr(rbXform,'worldMatrix'), _attr(rbShape,'inWorldMatrix') )
		_connectAttr( _attr(rbXform,'parentInverseMatrix'), _attr(rbShape,'inParentInverseMatrix') )

		_connectAttr( _attr(solver,'outSolverInitialized'), _attr(rbShape,'solverInitialized') )
		_connectAttr( _attr(solver,'outSolverUpdated'), _attr(rbShape,'solverUpdated') )
		_connectAttr( _attr(rbShape,'outRigidBodyData'), _attr(solver,'rigidBodies'), nextAvailable=True )
		# REVISIT: Consider alternatives like a single initSystem bool
		#		  attr instead of startTime and currentTime. 
		#		  Might be able to get around needing it at all
		_connectAttr( _attr(solver,'startTime'), _attr(rbShape,'startTime') )
		_connectAttr( _attr(solver,'currentTime'), _attr(rbShape,'currentTime') )
		_setAttr(rbShape, 'initialTranslate', origTranslate)
		deg2Rad = 3.14159 / 180
		_setAttr(rbShape, 'initialRotateX', origRotate[0] * deg2Rad)
		_setAttr(rbShape, 'initialRotateY', origRotate[1] * deg2Rad)
		_setAttr(rbShape, 'initialRotateZ', origRotate[2] * deg2Rad)
		pairBlend = maya.cmds.createNode( "pairBlend", name= "translateRotate")
		_setAttr(pairBlend, 'inTranslate1', origTranslate)
		_setAttr(pairBlend, 'inRotate1', origRotate)
		_connectAttr( _attr(rbShape, 'outSolvedTranslate'), _attr(pairBlend, 'inTranslate2') )
		_connectAttr( _attr(rbShape, 'outSolvedRotate'), _attr(pairBlend, 'inRotate2') )
		_connectAttr(_attr(pairBlend, 'outTranslateX'), _attr(rbXform, 'translateX'), force=True) 
		_connectAttr(_attr(pairBlend, 'outTranslateY'), _attr(rbXform, 'translateY'), force=True) 
		_connectAttr(_attr(pairBlend, 'outTranslateZ'), _attr(rbXform, 'translateZ'), force=True) 
		_connectAttr(_attr(pairBlend, 'outRotateX'),	_attr(rbXform, 'rotateX'),	force=True) 
		_connectAttr(_attr(pairBlend, 'outRotateY'),	_attr(rbXform, 'rotateY'),	force=True) 
		_connectAttr(_attr(pairBlend, 'outRotateZ'),	_attr(rbXform, 'rotateZ'),	force=True) 
		_connectAttr(_attr(rbXform, 'isDrivenBySimulation'), _attr(pairBlend,'weight'), force=True)

		_connectAttr(_attr(rbXform, 'rotatePivot'), _attr(rbShape,'pivotTranslate') )

		# ****** TODO: Remove the unused pairBlend weight attrs

		# Select the rigidBody transform and return the resulting values
		maya.cmds.select( rbXform, replace=True )

		return [ rbXform, rbShape ]

	@staticmethod
	@Trace()
	def command_shape(**kwargs):
		returnedTransforms = []
		shapes = kwargs['shapes']

		# Make sure the list doesn't contain any bullet objects.
		shapes = BulletUtils.verifySelectionNotBullet(shapes, False)

		for s in shapes:
			shapeT = _firstParent(s)

			# Verify collision shape type is valid.
			if (maya.cmds.nodeType(s) != 'mesh'):
				if (kwargs.has_key('colliderShapeType')):
					shapeType = kwargs['colliderShapeType']
					if (shapeType == eShapeType.kColliderHull) or (shapeType == eShapeType.kColliderMesh):
						kwargs['colliderShapeType'] = eShapeType.kColliderBox

			kwargs['centerOfMass'] = centerOfMass(shapeT)

			# Create rigidbody
			kwargs['bAttachSelected']=False
			kwargs['transformName']=shapeT
			rbTs = CreateRigidBody.doCommand(**kwargs)
			rbShape = _longName(rbTs[1])

			if kwargs.has_key('autoFit') and kwargs['autoFit']:
				(radius, length, ex, ey, ez, cx, cy, cz) = refitCollisionShape(rbShape, s)
				kwargs['radius'] = radius
				kwargs['length'] = length
				kwargs['extents'] = [ex, ey, ez]
				kwargs['centerOfMass'] = [cx, cy, cz] 

			returnedTransforms.append(rbTs[0])
			returnedTransforms.append(rbTs[1])

			# Connects
			if (maya.cmds.nodeType(s) == 'mesh'):
				_connectAttr( _attr(s,"outMesh"), _attr(rbShape, "inMesh"))
	
		return returnedTransforms
		
	@staticmethod
	@Trace()
	def hasMeshes():
		meshes = maya.cmds.listRelatives(s=True, type='mesh')
		return meshes != None and len(meshes) > 0

	@Trace()
	def addOptionDialogWidgets(self):
		'''Create OptionBox Widgets
		Make sure to return a dict of {optionVarDictKey, (widgetClass, widget)}
		Also set  self.optionMenuGrp_labelToEnum[optionVarDictKey] = {<label> : <value>,} if using optionMenuGrp
		'''
		widgetDict = {} # dict format: {optionVarDictKey, (widgetClass, widget)}
		
		# Register a script job to check for selection changes, as this will affect
		# what is displayed in the option box.
		if (CreateRigidBody.scriptJobNum == -1):
			CreateRigidBody.scriptJobNum = maya.cmds.scriptJob(event=['SelectionChanged', self.selectionChangedCB])
		
		# == Collider Properties == 
		widget = maya.cmds.optionMenuGrp(label=maya.stringTable['y_RigidBody.kColliderType'])

		self.box=maya.stringTable['y_RigidBody.kBox']
		sphere=maya.stringTable['y_RigidBody.kSphere']
		capsule=maya.stringTable['y_RigidBody.kCapsule']
		hull=maya.stringTable['y_RigidBody.kHull']
		mesh=maya.stringTable['y_RigidBody.kMesh']
		plane=maya.stringTable['y_RigidBody.kPlane']
		cylinder=maya.stringTable['y_RigidBody.kCylinder']
		hacd=maya.stringTable['y_RigidBody.kHACD']
		compound=maya.stringTable['y_RigidBody.kCompound']
		none=maya.stringTable['y_RigidBody.kNone']

		boxItem = maya.cmds.menuItem(label=self.box)
		maya.cmds.menuItem(label=sphere)
		maya.cmds.menuItem(label=capsule)
		hullItem = maya.cmds.menuItem(label=hull)
		meshItem = maya.cmds.menuItem(label=mesh)
		maya.cmds.menuItem(label=plane)
		maya.cmds.menuItem(label=cylinder)
		maya.cmds.menuItem(label=hacd)
		maya.cmds.menuItem(label=compound)

		self.optionMenuGrp_labelToEnum['colliderShapeType'] = {
			none	 : eShapeType.kColliderNone,
			self.box : eShapeType.kColliderBox,
			sphere	 : eShapeType.kColliderSphere,
			capsule	 : eShapeType.kColliderCapsule,
			hull	 : eShapeType.kColliderHull,
			mesh	 : eShapeType.kColliderMesh,
			plane	 : eShapeType.kColliderPlane,
			cylinder : eShapeType.kColliderCylinder,
			hacd	 : eShapeType.kColliderHACD,
			compound : eShapeType.kColliderCompound,
		}
		self.colliderOptionWidgets = {
			'hull' : (hull, hullItem),
			'mesh' : (mesh, meshItem),
		}
		widgetDict['colliderShapeType'] = (maya.cmds.optionMenuGrp, widget)

		widget = maya.cmds.optionMenuGrp(label=maya.stringTable[ 'y_RigidBody.kAxisType'  ])
		xAxis=maya.stringTable[ 'y_RigidBody.kXAxis']
		yAxis=maya.stringTable[ 'y_RigidBody.kYAxis']
		zAxis=maya.stringTable[ 'y_RigidBody.kZAxis']
		maya.cmds.menuItem(label=xAxis)
		maya.cmds.menuItem(label=yAxis)
		maya.cmds.menuItem(label=zAxis)
		self.optionMenuGrp_labelToEnum['axis'] = {
			xAxis	: eAxisType.kXAxis,
			yAxis	: eAxisType.kYAxis,
			zAxis	: eAxisType.kZAxis,
		}
		widgetDict['axis'] = (maya.cmds.optionMenuGrp, widget)

		widget = maya.cmds.checkBoxGrp(label=maya.stringTable['y_RigidBody.kAutoFit'], changeCommand=self.autoFitCB, 
									   numberOfCheckBoxes=1)
		widgetDict['autoFit'] = (maya.cmds.checkBoxGrp, widget)

		widget = maya.cmds.checkBoxGrp(label=maya.stringTable['y_RigidBody.kAutoHide'], changeCommand=self.hideShapeCB, 
									   numberOfCheckBoxes=1)
		widgetDict['hideShape'] = (maya.cmds.checkBoxGrp, widget)

		widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_RigidBody.kLength'  ],
										  minValue=0, maxValue=10, fieldMaxValue=9999999)
		widgetDict['length'] = (maya.cmds.floatSliderGrp, widget)
		maya.cmds.control(widget, edit=True, enable=False)

		widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_RigidBody.kRadius'  ],
										  minValue=0, maxValue=10, fieldMaxValue=9999999)
		widgetDict['radius'] = (maya.cmds.floatSliderGrp, widget)
		maya.cmds.control(widget, edit=True, enable=False)
		
		widget = maya.cmds.floatFieldGrp(label=maya.stringTable[ 'y_RigidBody.kExtents'  ],
										 numberOfFields=3)
		widgetDict['extents'] = (maya.cmds.floatFieldGrp, widget)
		maya.cmds.control(widget, edit=True, enable=False)
		
		# == RigidBody Properties== 
		widget = maya.cmds.optionMenuGrp(label=maya.stringTable[ 'y_RigidBody.kBodyType'  ], changeCommand=self.bodyTypeCB)
		staticBody=maya.stringTable[ 'y_RigidBody.kStaticBody']
		kinRigidBody=maya.stringTable[ 'y_RigidBody.kKinematicRigidBody']
		dynRigidBody=maya.stringTable[ 'y_RigidBody.kDynRigidBody' ]
		maya.cmds.menuItem(label=staticBody)
		maya.cmds.menuItem(label=kinRigidBody)
		maya.cmds.menuItem(label=dynRigidBody)
		self.optionMenuGrp_labelToEnum['bodyType'] = {
			staticBody		: eBodyType.kStaticBody,
			kinRigidBody	: eBodyType.kKinematicRigidBody,
			dynRigidBody	: eBodyType.kDynamicRigidBody,
		}
		widgetDict['bodyType'] = (maya.cmds.optionMenuGrp, widget)
	
		widget = maya.cmds.checkBoxGrp(label=maya.stringTable['y_RigidBody.kNeverSleeps'],
									   numberOfCheckBoxes=1)
		widgetDict['neverSleeps'] = (maya.cmds.checkBoxGrp, widget)

		widget = maya.cmds.floatSliderGrp(label=maya.stringTable['y_RigidBody.kMass'],
										  minValue=0, maxValue=10, fieldMaxValue=9999999)
		widgetDict['mass'] = (maya.cmds.floatSliderGrp, widget)

		widget = maya.cmds.floatSliderGrp(label=maya.stringTable['y_RigidBody.kLinearDamp' ],
										  minValue=0, maxValue=1)
		widgetDict['linearDamping'] = (maya.cmds.floatSliderGrp, widget)

		widget = maya.cmds.floatFieldGrp( label=maya.stringTable['y_RigidBody.kCenterOfMass' ],
										  numberOfFields=3 )
		widgetDict['centerOfMass'] = (maya.cmds.floatFieldGrp, widget)
		
		widget = maya.cmds.floatFieldGrp( label=maya.stringTable['y_RigidBody.kColliderShapeOffset' ],
										  numberOfFields=3 )
		widgetDict['colliderShapeOffset'] = (maya.cmds.floatFieldGrp, widget)
		
		widget = maya.cmds.floatSliderGrp(label=maya.stringTable['y_RigidBody.kColliderShapeMargin'],
										  minValue=0, maxValue=10, fieldMaxValue=9999999)
		widgetDict['colliderShapeMargin'] = (maya.cmds.floatSliderGrp, widget)

		widget = maya.cmds.floatSliderGrp(label=maya.stringTable['y_RigidBody.kAngDamp'],
										  minValue=0, maxValue=1)
		widgetDict['angularDamping'] = (maya.cmds.floatSliderGrp, widget)

		widget = maya.cmds.floatSliderGrp(label=maya.stringTable['y_RigidBody.kFriction'],
										  minValue=0, maxValue=1)
		widgetDict['friction'] = (maya.cmds.floatSliderGrp, widget)

		widget = maya.cmds.floatSliderGrp(label=maya.stringTable['y_RigidBody.kRestitution'],
										  minValue=0, maxValue=1)
		widgetDict['restitution'] = (maya.cmds.floatSliderGrp, widget)
		
		# Initial Conditions
		widget = maya.cmds.checkBoxGrp(label=maya.stringTable['y_RigidBody.kInitSleep'],
									   numberOfCheckBoxes=1)
		widgetDict['initiallySleeping'] = (maya.cmds.checkBoxGrp, widget)

		widget = maya.cmds.floatFieldGrp(label=maya.stringTable['y_RigidBody.kInitVel'],
										 numberOfFields=3)
		widgetDict['initialVelocity'] = (maya.cmds.floatFieldGrp, widget)

		widget = maya.cmds.floatFieldGrp(label=maya.stringTable['y_RigidBody.kInitAngVel'],
										 numberOfFields=3)
		widgetDict['initialAngularVelocity'] = (maya.cmds.floatFieldGrp, widget)
				
		# Forces
		widget = maya.cmds.floatFieldGrp(label=maya.stringTable['y_RigidBody.kImpulse'],
										 numberOfFields=3)
		widgetDict['impulse'] = (maya.cmds.floatFieldGrp, widget)

		widget = maya.cmds.floatFieldGrp(label=maya.stringTable['y_RigidBody.kTorqueImpulse'],
										 numberOfFields=3)
		widgetDict['torqueImpulse'] = (maya.cmds.floatFieldGrp, widget)
		
		return widgetDict
		
	@Trace()
	def autoFitCB(self, enable):
		(floatFieldGrp, widget) = self.optionVarToWidgetDict['length']
		if not maya.cmds.control(widget, exists=True):
			return
		maya.cmds.control(widget, edit=True, enable=not enable)
		(floatFieldGrp, widget) = self.optionVarToWidgetDict['radius']
		maya.cmds.control(widget, edit=True, enable=not enable)
		(floatFieldGrp, widget) = self.optionVarToWidgetDict['extents']
		maya.cmds.control(widget, edit=True, enable=not enable)

	@Trace()
	def hideShapeCB(self, enable):
		pass

	@Trace()
	def bodyTypeCB(self, value):
		'''
		Detect changes to the body type in the dialog. If a body type of dynamic or kinematic
		is selected, then we do not allow the mesh collider type
		'''
		self.updateOptionBox()

	@Trace()
	def selectionChangedCB(self):
		'''
		Handle a selection change while the option box is open.  In this case,
		update the available collider shape types based on whether a mesh is selected or not.
		'''
		self.updateOptionBox()

	@Trace()
	def updateOptionBox(self):
		# If a mesh is not selected, gray out the collision shape types applicable to them.
		hasMeshes = CreateRigidBody.hasMeshes()
		(grpCmd, menuGrp) = self.optionVarToWidgetDict['colliderShapeType']
		
		if not maya.cmds.control(menuGrp, exists=True):
			return

		(checkBoxGrp, widget) = self.optionVarToWidgetDict['autoFit']
		autoFit = checkBoxGrp(widget, query=True, value1=True)
		self.autoFitCB(autoFit)

		(checkBoxGrp, widget) = self.optionVarToWidgetDict['hideShape']
		hideShape = checkBoxGrp(widget, query=True, value1=True)
		self.hideShapeCB(hideShape)

		if hasMeshes:
			for (label, item) in self.colliderOptionWidgets.values():
				maya.cmds.menuItem( item, edit=True, enable=True )
				
			# Disable the mesh collision type unless the static body type
			# is chosen
			(optionMenuGrp, widget) = self.optionVarToWidgetDict['bodyType']
			value = optionMenuGrp(widget, query=True, value=True)
			if self.optionMenuGrp_labelToEnum['bodyType'][value] != eBodyType.kStaticBody:
				maya.cmds.menuItem( self.colliderOptionWidgets['mesh'][1], edit=True, enable=False )

				# If the body type has been changed to something non-static and the 
				# collider shape type is "mesh" then we need to change it to "box"
				# as non-static mesh collider shapes are not supported
				selectedVal = maya.cmds.optionMenuGrp(menuGrp, query=True, value=True)
				if self.optionMenuGrp_labelToEnum['colliderShapeType'][selectedVal] == eShapeType.kColliderMesh:
					maya.cmds.optionMenuGrp(menuGrp, edit=True, value=self.box)
		else:
			selectedVal = maya.cmds.optionMenuGrp(menuGrp, query=True, value=True)
			for (label, item) in self.colliderOptionWidgets.values():
				maya.cmds.menuItem( item, edit=True, enable=False )
				
				# If the current value of the option is either mesh or label, reset it to box.
				if (label == selectedVal):
					maya.cmds.optionMenuGrp(menuGrp, edit=True, value=self.box)

	@Trace()
	def optionBoxClosing(self):
		'''OVERRIDE
		Remove the script job looking for selection changes
		'''
		if not (CreateRigidBody.scriptJobNum == -1):
			maya.cmds.scriptJob(kill=CreateRigidBody.scriptJobNum, force=True)
			CreateRigidBody.scriptJobNum = -1
# end class

############################### CreateRigidSet ###############################

@Trace()
def _findRigidSetsFromMembers(objects):
	assert(objects!=None)
	result = set()

	for object in objects:
		setList = maya.cmds.listSets( object=object )
		rbSetList = maya.cmds.ls(setList,type='bulletRigidSet') if setList else []

		result = result.union(set(rbSetList))

	return result

@Trace()
def _findRigidSetsFromSelection(excludeTransforms=False):
	rigidSets = set()

	rbISList = maya.cmds.ls( sl=True, type='bulletInitialState' )
	for rbIS in rbISList:
		rbSetList = maya.cmds.listConnections( '{0}.message'.format(rbIS), sh=True, t='bulletRigidSet')
		if len(rbSetList):
			rigidSets = rigidSets.union(set(rbSetList))
		else:
			# try and figure out what rigid set was called if rbSet is missing
			# and hope user hasn't renamed the InitialState node.
			suffix= rbIS[len(rbIS)-12:]
			if suffix == 'initialstate':
				rbSet = rbIS[:-len('initialstate')].lower()
				rigidSets.add(rbSet)

		# find rigid set name from bulletInitialState

	rbSetList = maya.cmds.ls( sl=True, type='bulletRigidSet' )
	for rbSet in rbSetList:
		rigidSets.add(rbSet)

	if not excludeTransforms:
		objects = maya.cmds.ls( sl=True, type='transform' )

		rigidSets = rigidSets.union(set(_findRigidSetsFromMembers(objects)))

	return list(rigidSets)

def _getInitialState(rbSet):
	sList = maya.cmds.listConnections( '{0}.usedBy'.format(rbSet), sh=True, t='bulletInitialState')
	return sList[0] if sList else None


class CreateRigidSet( CommandWithOptionVars.CommandWithOptionVars ):
	"""
	OptionBox wrapper for bulletRigidSets()
	"""
	extractableAttrs = {
		'collisionShapeType':'colliderShapeType',
		'collisionShapeMargin':'colliderShapeMargin',
		'initiallySleeping':'initiallySleeping',
		'neverSleeps':'neverSleeps',
		'linearDamping':'linearDamping',
		'defaultMass':'mass',
		'angularDamping':'angularDamping',
		'friction':'friction',
		'restitution':'restitution',
		'initialVelocity':'initialVelocity',
		'initialAngularVelocity':'initialAngularVelocity',
		}

	@Trace()
	def __init__( self, sl=True ):
		super( CreateRigidSet, self ).__init__()

		self.commandName	   = 'CreateRigidSet'
		self.commandHelpTag	   = 'BulletCreateRigidSet'
		self.l10nCommandName   = maya.stringTable['y_RigidBody.kCreateRigidSet' ]
		self.optionVarPrefix   = 'bullet_rigidSet_'
		self.optionVarDefaults = {
			'name'	: 'bulletRigidSet',
			'inputSet'	: True,
			'outputMesh'  : True,
			'sl'  : sl,
			'hideShape'  : True,
		}
	# end

	@staticmethod
	@Trace()
	def command( **kwargs ):
		"""
		main entry point for command 
		"""

		# To create an empty set pass an empty list for the objects 
		# argument
		args=[]

		sl=True
		if kwargs.has_key('sl'):
			sl = kwargs['sl']
			kwargs.pop('sl')

		hideShape = False
		if kwargs.has_key('hideShape'):
			hideShape = kwargs['hideShape']
			kwargs.pop('hideShape')

		if not sl:
			args.append([])

		objects = _getSelectedTransforms() if sl else []

		# ensure exclusive
		if len(objects):
			rbSets = _findRigidSetsFromMembers(objects)
			if len(rbSets):
				CreateRigidSet.removeFromRigidSet( rbSets, members=objects)

		result = maya.cmds.bulletRigidSets( *args, **kwargs )

		'''
		return result from command 
		'''
		if result:
			# hide source objects
			if hideShape:
				BulletUtils.setAsIntermediateObjects( objects, 1, deferred=True )

			# If command echoing is off, echo this short line.
			if (not maya.cmds.commandEcho(query=True, state=True)):
				print "// Result: %s //" % (string.join(result, " "))

		return result
	# end

	@Trace()
	def addOptionDialogWidgets( self ):
		"""
		"""
		# dict format: {optionVarDictKey, (widgetClass, widget)}
		widgetDict = {} 

		widget = maya.cmds.textFieldGrp(label=maya.stringTable[ 'y_RigidBody.kSetName'  ])
		widgetDict['name'] = (maya.cmds.textFieldGrp, widget)

		widget = maya.cmds.checkBoxGrp(label=maya.stringTable[ 'y_RigidBody.kInputSet'  ],
									annotation=maya.stringTable[ 'y_RigidBody.kInputSetAnnot'  ],
									numberOfCheckBoxes=1)
		widgetDict['inputSet'] = (maya.cmds.checkBoxGrp, widget)

		widget = maya.cmds.checkBoxGrp(label=maya.stringTable[ 'y_RigidBody.kOutputMesh'  ],
									annotation=maya.stringTable[ 'y_RigidBody.kOutputMeshAnnot'  ],
									numberOfCheckBoxes=1)
		widgetDict['outputMesh'] = (maya.cmds.checkBoxGrp, widget)

		widget = maya.cmds.checkBoxGrp(label=maya.stringTable[ 'y_RigidBody.kSelectedObjects'  ],
									annotation=maya.stringTable[ 'y_RigidBody.kSelectedObjectsAnnot'  ],
									numberOfCheckBoxes=1)
		widgetDict['sl'] = (maya.cmds.checkBoxGrp, widget)

		widget = maya.cmds.checkBoxGrp(label=maya.stringTable[ 'y_RigidBody.kHideInputGeometry'  ],
									annotation=maya.stringTable[ 'y_RigidBody.kHideInputGeometryAnnot'  ],
									numberOfCheckBoxes=1)
		widgetDict['hideShape'] = (maya.cmds.checkBoxGrp, widget)

		return widgetDict
	# end

	@Trace()
	def uniqueName(self, basename):
		name = basename

		if name:
			numInstances = 1

			while maya.cmds.objExists(name):
				name = u'{0}{1}'.format(basename,numInstances)
				numInstances += 1

		return name

	@Trace()
	def executeCommandCB(self, miscBool=None):
		'''Callback to be used by a menuItem.
		Performs command with the specified optionVar preferences.
		'''
		logger.info(maya.stringTable[ 'y_RigidBody.kGetOptVarValues'  ])
		optionVarDict = self.getOptionVars()

		# REVISIT: May want to pass in parameters to the command a different way
		logger.info(maya.stringTable[ 'y_RigidBody.kExecuteCmd'  ])
		optionVarDictWithDefaults = self.optionVarDefaults.copy()
		optionVarDictWithDefaults.update(optionVarDict)

		# called directly from menu item
		if miscBool:
			# if there's only 1 object in select then use its name + 'Set'
			# otherwise let command determine name
			name = None
			list = maya.cmds.ls(sl=True,type='transform')
			if list and len(list)==1:
				name = list[0] + 'Set'
				baseName = name
				numInstances = 1
				while maya.cmds.objExists(name):
					name = '{0}{1}'.format(baseName,numInstances)
					numInstances += 1
			else:
				# otherwise use the name stored in the options
				name = optionVarDictWithDefaults['name']

			optionVarDictWithDefaults['name'] = self.uniqueName(name)

		returnVal = self.command(**optionVarDictWithDefaults)

		return returnVal

	@staticmethod
	@Trace()
	def resetInitialState( *args, **kw ):
		rigidSets = _findRigidSetsFromSelection()

		for rbSet in rigidSets:
			maya.cmds.bulletRigidSets( e=True, reset=True, name=rbSet )

	@staticmethod
	@Trace()
	def setInitialState( *args, **kw ):
		rigidSets = _findRigidSetsFromSelection()

		for rbSet in rigidSets:
			maya.cmds.bulletRigidSets( e=True, setInitialState=True, name=rbSet )

	@staticmethod
	@Trace()
	def selectInitialState( *args, **kw ):
		rigidSets = _findRigidSetsFromSelection()

		initialStates = []
		for rbSet in rigidSets:
			initialStates.append( _getInitialState(rbSet) )

		if len(initialStates):
			maya.cmds.select( initialStates )

	@staticmethod
	@Trace()
	def addToRigidSet( *args, **kw ):
		rbSets = _findRigidSetsFromSelection(excludeTransforms=True)

		if len(rbSets)>1:
			OpenMaya.MGlobal.displayError(maya.stringTable['y_RigidBody.kAmbiguousAddToSet' ])
			return 

		if len(rbSets)==0:
			OpenMaya.MGlobal.displayError(maya.stringTable['y_RigidBody.kNoRigidSetToAddSelected' ])
			return 

		addObjects = kw['members'] if kw.has_key('members') else maya.cmds.ls(sl=True, type='transform')
		hideShape = kw['hideShape'] if kw.has_key('hideShape') else True

		# filter out objects with rigid body shapes
		filteredAddObjects = []
		bulletObjects = []

		for object in addObjects:
			if BulletUtils.getRigidBodyFromTransform(object):
				OpenMaya.MGlobal.displayInfo(maya.stringTable['y_RigidBody.kAlreadyRigidBody' ].format(object))
				bulletObjects.append(object)
			else:
				filteredAddObjects.append(object)
		
		# ensure exclusive
		if len(filteredAddObjects):
			CreateRigidSet.removeFromRigidSet(members=filteredAddObjects, excludeSets=rbSets)

		# remove bullet rigid shape from objects
		if len(bulletObjects):
			BulletUtils.removeBulletObjectsFromList(bulletObjects)
			filteredAddObjects.extend( bulletObjects )

		if len(filteredAddObjects):
			maya.cmds.sets( filteredAddObjects, e=True, addElement=rbSets[0] )
			if hideShape:
				BulletUtils.setAsIntermediateObjects( filteredAddObjects, 1, deferred=True )

	@staticmethod
	@Trace()
	def removeFromRigidSet( *args, **kw ):
		rbSets = args[0] if len(args) else _findRigidSetsFromSelection(excludeTransforms=True)
		removeObjects = kw['members'] if kw.has_key('members') else maya.cmds.ls(sl=True, type='transform')
		excludeSets = kw['excludeSets'] if kw.has_key('excludeSets') else []

		if len(rbSets)==0:
			rbSets = _findRigidSetsFromMembers(removeObjects)

		# only remove from sets not in excludeSets
		rbSets = set(rbSets).difference(set(excludeSets))

		for rbSet in rbSets:
			BulletUtils.setAsIntermediateObjects( removeObjects, 0 )
			maya.cmds.sets( removeObjects, e=True, remove=rbSet )

		return removeObjects

	@staticmethod
	@Trace()
	def selectRigidSetMembers( *args, **kw ):
		rbSets = _findRigidSetsFromSelection(excludeTransforms=True)

		if len(rbSets)==0:
			OpenMaya.MGlobal.displayError(maya.stringTable[ 'y_RigidBody.kErrorNoRigidSetSelected'  ])
			return

		selectObjects=set([])

		for rbSet in rbSets:
			selectObjects=selectObjects.union(set(maya.cmds.sets( rbSet, q=True )))

		if len(selectObjects):
			maya.cmds.select( list(selectObjects), r=True )

		return

	@staticmethod
	@Trace()
	def selectRigidSetFromMembers( *args, **kw ):
		objects = _getSelectedTransforms()

		if len(objects)==0:
			OpenMaya.MGlobal.displayError(maya.stringTable[ 'y_RigidBody.kErrorNoRigidSetMemberSelected'  ])
			return

		rbSets = _findRigidSetsFromMembers(objects)

		if len(rbSets):
			maya.cmds.select( list(rbSets), r=True, ne=True )

		return

	@staticmethod
	@Trace()
	def clearRigidSets( *args, **kw ):
		rbSets = _findRigidSetsFromSelection(excludeTransforms=True)

		if len(rbSets)==0:
			OpenMaya.MGlobal.displayError(maya.stringTable[ 'y_RigidBody.kErrorClearNoRigidSetSelected'  ])
			return

		for rbSet in rbSets:
			members = maya.cmds.sets( rbSet, q=True )
			maya.cmds.sets( e=True, clear=rbSet )
			BulletUtils.setAsIntermediateObjects(members,0)

		return rbSets

	@staticmethod
	@Trace()
	def deleteRigidSets( *args, **kw ):
		from BulletUtils import removeBulletObjectsFromList
		rbSets = _findRigidSetsFromSelection(excludeTransforms=True)

		if len(rbSets)==0:
			OpenMaya.MGlobal.displayError(maya.stringTable[ 'y_RigidBody.kErrorDeleteNoRigidSetSelected'  ])
			return

		for rbSet in rbSets:
			members = maya.cmds.sets( rbSet, q=True )
			BulletUtils.setAsIntermediateObjects(members,0)

		removeBulletObjectsFromList(list(rbSets))

		return

	@staticmethod
	@Trace()
	def extractFromRigidSet( *args, **kw ):

		rbSets = _findRigidSetsFromSelection()
		memberObjects = set(kw['members'] if kw.has_key('members') else maya.cmds.ls(sl=True, type='transform'))

		for rbSet in rbSets:
			extractObjects = memberObjects.intersection(set(maya.cmds.sets( rbSet, q=True )))

			if len(extractObjects):

				CreateRigidSet.removeFromRigidSet([rbSet], members=list(extractObjects))

				# read attributes from rigidset
				rbInitialState = _getInitialState(rbSet)

				kwArgs = {'bodyType':eBodyType.kDynamicRigidBody,  'autoFit':True, 'bAttachSelected':False}

				for attr, mappedAttr in CreateRigidSet.extractableAttrs.iteritems():
					attrVal =_getAttr(rbInitialState,attr)
					# getAttr returns [()] for vector values
					if type(attrVal) in [types.ListType] and type(attrVal[0]) in [types.TupleType]:
						attrVal = attrVal[0]

					kwArgs[mappedAttr]=attrVal

				for object in extractObjects:
					kwArgs['transformName'] = object

					rtn = CreateRigidBody().command(**kwArgs)

			BulletUtils.setAsIntermediateObjects( extractObjects, 0 )

# end class
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
