"""
Ragdoll - Python module for working with ragdolls and MayaBullet.

"""
# Python standard library
import maya
maya.utils.loadStringResourcesForModule(__name__)

import types
import math
import logging
from collections import deque
# Maya
import maya.api.OpenMaya as OpenMaya
import maya.cmds
# MayaBullet
import maya.app.mayabullet.RigidBody as RigidBody
import maya.app.mayabullet.RigidBodyConstraint as RigidBodyConstraint
import maya.app.mayabullet.CommandWithOptionVars as CommandWithOptionVars

from maya.app.mayabullet.RigidBodyConstraint import eConstraintType, eConstraintLimitType
from maya.app.mayabullet.RigidBody import eBodyType, eShapeType, eAxisType

from maya.app.mayabullet import logger as logger
from maya.app.mayabullet.Trace import Trace

################################### GLOBALS ####################################

RB_XFORM_PREFIX = "jointToRigidBody"

ROTATE_MIN = -360
ROTATE_MAX =  360

# Angular constraint defaults
DEFAULT_ANGULAR_DAMPING		= 0.5
DEFAULT_ANGULAR_SOFTNESS	= 0.0
DEFAULT_ANGULAR_RESTITUTION = 0.0
# Capsule defaults
DEFAULT_CAPSULE_LENGTH		= 0.8  # as a proportion of bone length
DEFAULT_CAPSULE_RADIUS		= 0.1  # as a proportion of bone length
DEFAULT_CAPSULE_MASS		= 1.0
DEFAULT_NAME_SEPARATOR		= '_'

############################### PYMEL SUBSTITUTES ###############################
@Trace()
def _longName( obj ):
	if type(obj) not in [types.StringType,types.UnicodeType]:
		return obj.longName()
	if unicode(obj[0]) != unicode('|'):
		objs = maya.cmds.ls(obj,long=True)
		if len(objs)>1:
			logger.warn( maya.stringTable[ 'y_Ragdoll.kLongNameAmbiguity' ] % obj )
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
def _numChildren(obj, type=None):
	return len(_getChildren(obj, type))
@Trace()
def _firstParent(obj):
	l= maya.cmds.listRelatives( obj, fullPath=True, parent=True )
	return l[0] if l else None
@Trace()
def _setParent(child,parent):
	child = maya.cmds.parent(child,parent) 
	return '|{0}|{1}'.format(parent,child[0])
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
def _getTranslation(obj, space='local' ):
	return OpenMaya.MVector( maya.cmds.xform(obj,q=True,translation=True, worldSpace=(space=='world')) )
@Trace()
def _setTranslation(obj, pos, space='local' ):
	return maya.cmds.xform(_longName(obj),translation=list(pos), worldSpace=(space=='world'))
@Trace()
def _getRotation(obj, space='local' ):
	return OpenMaya.MEulerRotation( maya.cmds.xform(_longName(obj),q=True,rotation=True, worldSpace=(space=='world')) )
@Trace()
def _setRotation(obj, rot, space='local' ):
	return maya.cmds.rotate( math.degrees(rot[0]), math.degrees(rot[1]), math.degrees(rot[2]), _longName(obj), worldSpace=(space=='world') )
@Trace()
def _getRotLimits(obj):
	minX,maxX = maya.cmds.transformLimits( obj, q=True, rotationX=True )
	minY,maxY = maya.cmds.transformLimits( obj, q=True, rotationY=True )
	minZ,maxZ = maya.cmds.transformLimits( obj, q=True, rotationZ=True )
	return ((minX,minY,minZ),(maxX,maxY,maxZ))
def _getRotLimitsEnabled(obj):
	minX,maxX = maya.cmds.transformLimits( obj, q=True, enableTranslationX=True )
	minY,maxY = maya.cmds.transformLimits( obj, q=True, enableTranslationY=True )
	minZ,maxZ = maya.cmds.transformLimits( obj, q=True, enableTranslationZ=True )
	return ((minX,minY,minZ),(maxX,maxY,maxZ))
@Trace()
def _isJoint( obj ):
	return maya.cmds.objectType(obj).lower() in ['joint']
@Trace()
def _vector(xx,yy,zz):
	return OpenMaya.MVector(xx,yy,zz)
@Trace()
def _vectorLength(xx,yy,zz):
	return OpenMaya.MVector(xx,yy,zz).length()
@Trace()
def _quaternion(v1,v2):
	return OpenMaya.MQuaternion(v1,v2)

@Trace()
def _createRigidBody( *args, **kw ):
	kw['autoFit']=0
	rtn = RigidBody.CreateRigidBody.command(*args, **kw)
	return [ a if type(a) in [types.UnicodeType,types.StringType] else a.longName() for a in rtn]
def _createRigidBodyConstraint( *args, **kw ):
	rtn = RigidBodyConstraint.CreateRigidBodyConstraint.command(*args, **kw)
	return [ a if type(a) in [types.UnicodeType,types.StringType] else a.longName() for a in rtn]

############################### HELPER FUNCTIONS ###############################
@Trace()
def _calcCapsuleRadius( jointStart, jointEnd, 
						radiusRatio=DEFAULT_CAPSULE_RADIUS ):
	"""
	Given a bone (specified by the joints on either end), return the
	radius of the capsule for this bone.
	"""
	# This is a simple placeholder implementation. Ideas for more
	# sophisticated solutions:
	#
	# TODO: implement based on bounds around static mesh shapes
	# TODO: implement based on clusters for skinned meshes

	return _vectorLength(*_getTranslation(jointEnd)) * radiusRatio
# end


@Trace()
def _getNodesToVisit( rootJointName ):
	"""
	Returns a list of nodes for traversal. If the rootJointName is
	None, uses the current selection.
	"""
	# figure out where the traversal will start
	if ( rootJointName is None ):
		nodesToVisit = maya.cmds.ls( sl=True, long=True, type='joint' )
	else:
		try:
			assert( _isJoint(rootJointName) )
		except:
			logger.error( maya.stringTable['y_Ragdoll.kUnableStartJoint'] % rootJointName ) 
			raise
		# end-try
	# end-if	

	return nodesToVisit
# end


@Trace()
def _getCapsule( startJoint, endJoint ):
	"""
	Given a parent (start) joint and child (end) joint, retrieve the
	(user editable) rigid body transform and the rigid body shape that
	is associated with this bone.

	Returns (rbXform, rbShape) on success, or (None, None) on failure.
	"""
	if ( startJoint is None or endJoint is None ):
		return (None, None)

	childXforms = _getChildren( startJoint, type="transform" )
	for childXform in childXforms:
		childTranslation =  _getTranslation(childXform)
		endJointTranslation =  _getTranslation(endJoint)

		if ( childTranslation == endJointTranslation * 0.5 ):
			# NOTE: assumes only the bullet transform is the only
			#	   child of the capsule rb transform.
			# NOTE: assumes there is only one rigid body under the
			#	   bullet transform
			rbs = _getChildren( childXform, type="bulletRigidBodyShape" )
			return ( rbs[0] if rbs else None )
		# end-if
	# end-for
	
	return (None, None)
# end


@Trace()
def _createCapsule( currentJoint, childJoint, bAttachToJoint=True,
					bodyType=eBodyType.kKinematicRigidBody, mass=0.0,
					boneLengthRatio   = DEFAULT_CAPSULE_LENGTH,
					lengthRadiusRatio = DEFAULT_CAPSULE_RADIUS,
					transformName=None ):
	"""
	Create a capsule collider around the bone from currentJoint to
	childJoint. If bAttachToJoint is True, the capsule will be
	parented to the current joint, otherwise it will be created at the
	top level of the scene. BodyType and mass can be specified, and
	transform name can be used to specify the name of the new
	top-level rigid body transform.

	This implementation is based on the current rigid body hierarchy,
	which looks like:

	rbXform
	  --> bulletXform
			--> rbShape (capsule)

	Returns (rbXform, rbShape)
	"""
	if ( transformName is None ):
		transformName = '%s#' % RB_XFORM_PREFIX

	if ( bAttachToJoint ): 
		parent=currentJoint
	else: 
		parent=None

	rbXform = maya.cmds.createNode( 'transform', name=transformName,
						  parent=parent, skipSelect=True )

	# these values will work when adding capsules to a joint hierarchy
	boneVector   = _getTranslation(childJoint)
	center  =  _vector( _vectorLength(*boneVector) * .5, 0 ,0 )
	worldOffset  = _vector( 0, 0, 0 )

	if ( not bAttachToJoint ):
		# if this capsule won't be inheriting the transform from the 
		# parent joint, these values need to be adjusted for world-space
		worldOffset = _getTranslation( currentJoint, space="world" )
		boneVector  = _getTranslation( childJoint, space="world") \
						  - _getTranslation(currentJoint, space="world")
		center =  _vector( _vectorLength(*boneVector) * .5, 0 ,0 )  # rotation is from the x axis.
	# end-if

	rotateQuat = _quaternion( _vector(1,0,0), boneVector )
	rotateAngles = rotateQuat.asEulerRotation()

	_setRotation( rbXform, rotateAngles )
	_setTranslation(rbXform, worldOffset)

	logger.info( maya.stringTable[ 'y_Ragdoll.kAddingRB'  ] % rbXform )
	(rbParentName, rbName) = _createRigidBody( \
						transformName=_longName(rbXform),
						colliderShapeType=eShapeType.kColliderCapsule,
						axis=eAxisType.kXAxis,
						ignoreShape=True,
						bAttachSelected=False )
	rbNode = rbName
	_setAttr(rbNode,'bodyType', bodyType )
	_setAttr(rbNode,'mass',  mass )
	_setAttr(rbNode,'centerOfMass',  center )  
	capsuleRadius = _calcCapsuleRadius( currentJoint, childJoint, 
										lengthRadiusRatio )
	_setAttr(rbNode, 'length', \
		max(0.0, 
			math.fabs( _vectorLength(*boneVector) * boneLengthRatio) 
			- capsuleRadius) )
	_setAttr(rbNode,'radius', capsuleRadius)

	return ( rbXform, rbNode )
# end


@Trace()
def _getRagdollCapsule( ragdollRootNode, parentJoint, currentJoint, 
						jointNameSeparator=DEFAULT_NAME_SEPARATOR ):
	"""
	Retrieves the rigid body from the ragdoll that corresponds to the
	give pair of joints. This method relies on the naming convention
	used for creating the transforms for the rigid bodies.

	Returns (rbXform, rb), or (None, None) on failure.
	"""
	if ( parentJoint is None or currentJoint is None ):
		return (None, None)

	capsuleXform \
		= "%s|%s%s%s" % (ragdollRootNode, _name(parentJoint), jointNameSeparator, _name(currentJoint))
	return ( capsuleXform, 
			 # NOTE: assumes there is only one transform under the capsule
			 _getChildren( capsuleXform, type="bulletRigidBodyShape" )[0] )
# end


@Trace()
def _applyJointLimits( joint, constraint ):
	"""
	joint - joint to get the limits from
	constraint - constraint shape for a 6-DOF constraint
				 to apply the limits to 
	"""
	minRotLimitEnable, maxRotLimitEnable = _getRotLimitsEnabled(joint)
	minRotLimit, maxRotLimit = _getRotLimits(joint)

	if ( minRotLimitEnable[0] or maxRotLimitEnable[0] ):
		if ( minRotLimit[0] == maxRotLimit[0] ):
			_setAttr(constraint, 'angularConstraintX', \
				eConstraintLimitType.kRBConstraintLimitLocked )
		else:
			_setAttr(constraint, 'angularConstraintX', \
				eConstraintLimitType.kRBConstraintLimitLimited )
			# Since Bullet doesn't make the distinction between
			# enabling the min or max of a limit, if the joint has one
			# end of the range is disabled, set the min/max angle to
			# be effectively disabled in Bullet.
			if ( not minRotLimitEnable[0] ):
				minRotLimit[0] = ROTATE_MIN
			if ( not maxRotLimitEnable[0] ):
				maxRotLimit[0] = ROTATE_MAX
		# end-if

	if ( minRotLimitEnable[1] or maxRotLimitEnable[1] ):
		if ( minRotLimit[1] == maxRotLimit[1] ):
			_setAttr(constraint,'angularConstraintY', \
				eConstraintLimitType.kRBConstraintLimitLocked )
		else:
			_setAttr(constraint,'angularConstraintY', \
				eConstraintLimitType.kRBConstraintLimitLimited )
			if ( not minRotLimitEnable[1] ):
				minRotLimit[1] = ROTATE_MIN
			if ( not maxRotLimitEnable[1] ):
				maxRotLimit[1] = ROTATE_MAX
		# end-if

	if ( minRotLimitEnable[2] or maxRotLimitEnable[2] ):
		if ( minRotLimit[2] == maxRotLimit[2] ):
			_setAttr(constraint,'angularConstraintZ', \
				eConstraintLimitType.kRBConstraintLimitLocked )
		else:
			_setAttr(constraint,'angularConstraintZ', \
				eConstraintLimitType.kRBConstraintLimitLimited )
			if ( not minRotLimitEnable[2] ):
				minRotLimit[2] = ROTATE_MIN
			if ( not maxRotLimitEnable[2] ):
				maxRotLimit[2] = ROTATE_MAX
		# end-if

	# push the limits through to the constraint regardless of what's
	# enabled, since they should be harmless for any disabled axes.
	_setAttr(constraint,'angularConstraintMin',minRotLimit ) 
	_setAttr(constraint,'angularConstraintMax',maxRotLimit )
# end


@Trace()
def _addWidget( widgetFcn, optionVarName, widgetDict, **kwargs ):
	"""
	Helper for adding UI widgets in addOptionDialogWidget() callbacks.
	"""
	widget = widgetFcn( **kwargs )
	widgetDict[optionVarName] = ( widgetFcn, widget )
# end


@Trace()
def _addCapsuleWidgets( widgetDict, bIncludeMass=True ):
	"""
	Adds the widgets for editing capsule attributes.
	"""
	if ( bIncludeMass ):
		_addWidget( maya.cmds.floatSliderGrp, 'capsuleMass', widgetDict,
					label=maya.stringTable[ 'y_Ragdoll.kCapsuleMass'  ],
					minValue=0, maxValue=100, fieldMaxValue=9999999 )
	# end-if
	_addWidget( maya.cmds.floatSliderGrp, 'capsuleBoneRatio', widgetDict,
				label=maya.stringTable[ 'y_Ragdoll.kCapsuleBoneLengthRatio'  ],
				minValue=0, maxValue=1, fieldMaxValue=9999999 )
	_addWidget( maya.cmds.floatSliderGrp, 'capsuleRadiusRatio', widgetDict,
				label=maya.stringTable[ 'y_Ragdoll.kCapsuleRadiusLengthRatio'  ],
				minValue=0, maxValue=1, fieldMaxValue=9999999 )
# end


############################### PUBLIC API #####################################

@Trace()
def addCapsulesToSkeleton( rootJointName	  = None, 
						   capsuleBoneRatio   = DEFAULT_CAPSULE_LENGTH,
						   capsuleRadiusRatio = DEFAULT_CAPSULE_RADIUS ):
	"""
	This method traverses a joint hierarchy, adding kinematic rigid
	body capsules to the bones. If the name of the root joint is
	provided, the traversal will begin at that joint. Otherwise, the
	currently selected joint(s) will be used.
	"""
	initialSelection = maya.cmds.ls( long=True, selection=True )
	nodesToVisit = deque( _getNodesToVisit( rootJointName ) )

	if not nodesToVisit or len(nodesToVisit)<1:
		maya.OpenMaya.MGlobal.displayError(maya.stringTable[ 'y_Ragdoll.kAddCollidersSelectJoint' ])
		return

	while ( len(nodesToVisit) > 0 ):
		currentJoint = nodesToVisit.popleft()
		logger.debug( maya.stringTable[ 'y_Ragdoll.kVisiting'  ] % currentJoint )

		# within the current iteration, we will consider only other
		# joints attached to the current joint
		children = [ child for child in _getChildren(currentJoint) \
						 if _isJoint(child) ]
		# future iterations need only consider joints with children
		nodesToVisit.extend( [child for child in children \
								  if _numChildren(child) > 0] )
		prevCapsules = [child for child in _getChildren(currentJoint) \
							if RB_XFORM_PREFIX in _name(child)]

		# examine the bones between this joint and its child joints...
		for childJoint in children:
			logger.debug( maya.stringTable[ 'y_Ragdoll.kBoneFromTo'  ] % (currentJoint, childJoint) )
			boneVector = _getTranslation(childJoint)

			bCapsuleExists = False
			for prevCapsuleXform in prevCapsules:
				if _getTranslation(prevCapsuleXform) == boneVector * 0.5:
					bCapsuleExists = True
					break
				# end-if
			# end-for
			if ( bCapsuleExists ): 
				logger.warn( maya.stringTable[ 'y_Ragdoll.kSkippingBone'  ] )
				continue
			# end-if

			_createCapsule( currentJoint, childJoint, bAttachToJoint=True,
							# colliders for animation should be kinematic, 
							# with zero mass
							bodyType=eBodyType.kKinematicRigidBody, mass=0.0,
							boneLengthRatio=capsuleBoneRatio,
							lengthRadiusRatio=capsuleRadiusRatio )
		# end-for
	# end-while

	# restore the initial selection
	maya.cmds.select( initialSelection, replace=True )

# end addCapsulesToSkeleton()


class AddColliders( CommandWithOptionVars.CommandWithOptionVars ):
	"""
	OptionBox wrapper for addCapsulesToSkeleton()
	"""

	@Trace()
	def __init__( self ):
		super( AddColliders, self ).__init__()

		self.commandName	   = 'AddColliders'
		self.commandHelpTag	   = 'BulletAddColliders'
		self.l10nCommandName   = maya.stringTable['y_Ragdoll.kAddColliders' ]
		self.optionVarPrefix   = 'bullet_Ragdoll_'
		self.optionVarDefaults = {
			'capsuleBoneRatio'	: DEFAULT_CAPSULE_LENGTH,
			'capsuleRadiusRatio'  : DEFAULT_CAPSULE_RADIUS,
		}
	# end


	@staticmethod
	@Trace()
	def command( **kwargs ):
		"""
		Callback to execute the AddColliders command.
		"""
		# If command echoing is off, echo this short line.
		if (not maya.cmds.commandEcho(query=True, state=True)):
			print("Ragdoll.AddColliders().executeCommandCB()")

		addCapsulesToSkeleton( **kwargs )

	# end


	@Trace()
	def addOptionDialogWidgets( self ):
		"""
		"""
		# dict format: {optionVarDictKey, (widgetClass, widget)}
		widgetDict = {} 

		maya.cmds.separator( style="none", height=5 )
		_addCapsuleWidgets( widgetDict, bIncludeMass=False )

		return widgetDict
	# end

# end class		


def createRagdoll( rootJoint=None,
				   angularDamping	 = DEFAULT_ANGULAR_DAMPING,
				   angularSoftness	= DEFAULT_ANGULAR_SOFTNESS,
				   angularRestitution = DEFAULT_ANGULAR_RESTITUTION,
				   capsuleBoneRatio   = DEFAULT_CAPSULE_LENGTH,
				   capsuleRadiusRatio = DEFAULT_CAPSULE_RADIUS,
				   capsuleMass		= DEFAULT_CAPSULE_MASS,
				   jointNameSeparator = DEFAULT_NAME_SEPARATOR ):
	"""
	Creates a ragdoll of capsules joined by constraints, that matches
	the skeleton starting from the joint named by rootJoint. If no
	root is specified, the current selection is used.
	"""
	nodesToVisit = deque( _getNodesToVisit(rootJoint) )

	if not nodesToVisit or len(nodesToVisit)<1:
		maya.OpenMaya.MGlobal.displayError(maya.stringTable[ 'y_Ragdoll.kCreateRagdollSelectJoint' ])
		return

	ragdollRootNode = maya.cmds.createNode( 'transform', name="Ragdoll#",
								   skipSelect=True )
						  
	currentJoint = None
	while ( len(nodesToVisit) > 0 ):
		logger.debug( maya.stringTable[ 'y_Ragdoll.kStartingIterCurrJoint'  ] \
						   % (currentJoint, nodesToVisit) )
		currentJoint = nodesToVisit.popleft()
		# NOTE: assumes joints are directly connected to each other
		try:
			parentJoint = _firstParent(currentJoint)
			if ( not _isJoint(parentJoint) ):
				parentJoint = None
		except:
			parentJoint = None
		# end-try

		logger.debug( maya.stringTable[ 'y_Ragdoll.kVisiting2'  ] % currentJoint )
		(rbAXform, rbA) = _getRagdollCapsule( ragdollRootNode, parentJoint, currentJoint,
											  jointNameSeparator )
		childJoints = _getChildren(currentJoint, type="joint")
		nodesToVisit.extend( childJoints )

		prevChildJoint = None
		for childJoint in childJoints:
			# Here's what we're working with within this loop:
			#
			# parent		   current		   child
			#  joint --[rbA]--> joint --[rbB]--> joint
			(rbBXform, rbB) \
				= _createCapsule( currentJoint, childJoint, False,
								  eBodyType.kDynamicRigidBody, capsuleMass,
								  capsuleBoneRatio, capsuleRadiusRatio,
								  "%s%s%s" % (_name(currentJoint),
											  jointNameSeparator,
											  _name(childJoint)) )
			rbBXform = _setParent( rbBXform, ragdollRootNode )
			rbBName = None
			if ( rbB is not None ): rbBName = _getChildren(rbBXform,type='bulletRigidBodyShape')[0]
			rbBXformName = None
			if ( rbBXform is not None ): rbBXformName = _longName(rbBXform)

			# figure out what to anchor this rigid body to
			if ( rbA is None and prevChildJoint is not None ): 
				# prevChildJoint implies that a sibling capsule was
				# created in a previous iteration, which this capsule
				# can be constrained to. 
				(sibXform, sib) \
					= _getRagdollCapsule( ragdollRootNode, currentJoint, prevChildJoint,
										  jointNameSeparator )
				rbAnchorName = _longName(sib)
			elif ( rbA is not None ):
				rbAnchorName = _longName(rbA)
			else:
				# NOTE: don't create constraints without an anchor, or
				# else the ragdoll will end up constrained to the world.
				rbAnchorName = None
			# end-if

			if ( rbAnchorName is not None ):
				logger.info( maya.stringTable[ 'y_Ragdoll.kCreatingConstr'  ] \
								  % (rbAnchorName, rbB) )
				# "constraint" abbreviated "constr"
				constrName = _createRigidBodyConstraint( \
									constraintType=eConstraintType.kRBConstraintSixDOF,
									rigidBodyA=rbAnchorName, 
									rigidBodyB=rbBName, 
									parent=None )[0]
				constrNode = constrName
				constrXformNode = _firstParent(constrNode)

				# configure the transform
				constrXformNode = maya.cmds.rename( constrXformNode, 
						"constraint_%s" % _name(currentJoint) )
				constrXformNode = _setParent( constrXformNode, ragdollRootNode )
				constrNode = _getChildren( constrXformNode, type='bulletRigidBodyConstraintShape' )[0]
				_setTranslation( constrXformNode,
					_getTranslation(currentJoint, space="world") )
				_setRotation(constrXformNode,
					_getRotation(currentJoint, space="world") )

				# configure the constraint
				_setAttr(constrNode,'angularDamping', angularDamping )
				_setAttr(constrNode,'angularSoftness', angularSoftness )
				_setAttr(constrNode,'angularRestitution', angularRestitution )

				# lock the linear motion, to behave like a point constraint
				_setAttr(constrNode,'linearConstraintX', \
					eConstraintLimitType.kRBConstraintLimitLocked )
				_setAttr(constrNode,'linearConstraintY', \
					eConstraintLimitType.kRBConstraintLimitLocked )
				_setAttr(constrNode,'linearConstraintZ', \
					eConstraintLimitType.kRBConstraintLimitLocked )

				# set the rotational limits to match the joint
				_applyJointLimits( currentJoint, constrNode )
			# end-if

			prevChildJoint = childJoint
		# end-for
	# end-while

	maya.cmds.select( ragdollRootNode, replace=True )
# end createRagdoll()


class CreateRagdoll( CommandWithOptionVars.CommandWithOptionVars ):
	"""
	OptionBox wrapper for createRagdoll().
	"""

	@Trace()
	def __init__( self ):
		super( CreateRagdoll, self ).__init__()

		self.commandName	   = 'CreateRagdoll'
		self.commandHelpTag	   = 'BulletCreateRagdoll'
		self.l10nCommandName   = maya.stringTable['y_Ragdoll.kCreateRagdoll' ]
		self.optionVarPrefix   = 'bullet_Ragdoll_'
		self.optionVarDefaults = {
			'angularDamping'	  : DEFAULT_ANGULAR_DAMPING,
			'angularSoftness'	 : DEFAULT_ANGULAR_SOFTNESS,
			'angularRestitution'  : DEFAULT_ANGULAR_RESTITUTION,
			'capsuleMass'		 : DEFAULT_CAPSULE_MASS,
			'capsuleBoneRatio'	: DEFAULT_CAPSULE_LENGTH,
			'capsuleRadiusRatio'  : DEFAULT_CAPSULE_RADIUS,
			'jointNameSeparator'  : DEFAULT_NAME_SEPARATOR,
		}
	# end


	@staticmethod
	@Trace()
	def command( **kwargs ):
		"""
		Callback to execute the CreateRagdoll command.
		"""
		
		# If command echoing is off, echo this short line.
		if (not maya.cmds.commandEcho(query=True, state=True)):
			print("Ragdoll.CreateRagdoll().executeCommandCB()")
		createRagdoll( **kwargs )
	# end


	@Trace()
	def addOptionDialogWidgets( self ):
		"""
		Callback to set up the OptionBox UI.
		"""
		# dict format: {optionVarDictKey, (widgetClass, widget)}
		widgetDict = {} 

		maya.cmds.separator( style="none", height=5 )
		_addCapsuleWidgets( widgetDict )

		maya.cmds.separator( style="none", height=5 )
		_addWidget( maya.cmds.floatSliderGrp, 'angularDamping', widgetDict,
					label=maya.stringTable[ 'y_Ragdoll.kJointAngDampLabel'  ], 
					minValue=0, maxValue=1, fieldMaxValue=9999999 )
		_addWidget( maya.cmds.floatSliderGrp, 'angularSoftness', widgetDict,
					label=maya.stringTable[ 'y_Ragdoll.kJointAngSoftLabel'  ], 
					minValue=0, maxValue=1, fieldMaxValue=9999999 )
		_addWidget( maya.cmds.floatSliderGrp, 'angularRestitution', widgetDict,
					label=maya.stringTable[ 'y_Ragdoll.kJointAngRestitutionLabel'  ], 
					minValue=0, maxValue=1, fieldMaxValue=9999999 )

		_addWidget( maya.cmds.textFieldGrp, 'jointNameSeparator', widgetDict,
					label=maya.stringTable[ 'y_Ragdoll.kJointNameSepLabel'  ] )

		return widgetDict
	# end

# end class
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
