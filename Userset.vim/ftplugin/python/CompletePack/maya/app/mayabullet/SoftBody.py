#!/usr/bin/env python
import maya
maya.utils.loadStringResourcesForModule(__name__)

"""
SoftBody - Module containing functions for working with soft bodies
		   and MayaBullet. 

"""

import logging
import string

import maya.cmds
import maya.mel
import maya.OpenMaya

# MayaBullet
import maya.app.mayabullet.BulletUtils as BulletUtils
import CommandWithOptionVars


class CreateSoftBody(CommandWithOptionVars.CommandWithOptionVars):
	def __init__(self):
		super(CreateSoftBody, self).__init__()
		
		self.commandName = 'CreateSoftBody'
		self.commandHelpTag	   = 'BulletCreateSoftBody'
		self.l10nCommandName = maya.stringTable['y_SoftBody.kCreateSoftBody' ]
		self.optionVarPrefix = 'bullet_SoftBody_'
		self.optionVarDefaults = {
			'generateBendConstraints':False,
			'selfCollision':False,
			'bendResistance':0.0,
			'linearStiffness':1.0,
			'friction':0.01,
			'damping':0.05,
			'pressure':0.0,
			'collisionMargin':0.01,
			'positionIterations':10,
			#'poseMatching':0.0,
			#'enablePoseMatching':False,
			'preserveSourceMesh':False,
			'singleTransform':True
		}
		

	@staticmethod
	def command(meshes=None,
					   name='bulletSoftBodyShape#',
					   # Attrs
					   generateBendConstraints=None,
					   selfCollision=None,
					   bendResistance=None,
					   linearStiffness=None,
					   friction=None,
					   damping=None,
					   pressure=None,
					   collisionMargin=None,
					   positionIterations=None,
					   #poseMatching=None,
					   #enablePoseMatching=None,
					   preserveSourceMesh=None,
					   singleTransform=None,
					   **kwargs):
		'''Create a bulletSoftBody from specified mesh.  
		'''

		# Explicitly list the names of settable attributes iterated over below
		settableAttrs = [
			'generateBendConstraints',
			'selfCollision',
			'bendResistance',
			'linearStiffness',
			'friction',
			'damping',
			'pressure',
			'collisionMargin',
			'positionIterations',
			#'poseMatching',
			#'enablePoseMatching',
			]

		# Make a boolean value that is easier to read in code
		singleTransform = singleTransform != False
		
		# Get list of meshes from selection if not passed in
		if (meshes==None):
			maya.cmds.select(maya.cmds.listRelatives(shapes=True, fullPath=True), add=True)
			meshes =  maya.cmds.ls(sl=True, type='mesh', long=True)

		# Make sure the selection doesn't contain any bullet objects.
		BulletUtils.verifySelectionNotBullet(meshes)

		returnedNodes = []
		# Sanity Checking
		if len(meshes) == 0:
			maya.OpenMaya.MGlobal.displayError(maya.stringTable['y_SoftBody.kSelectMesh' ])
			return returnedNodes

		# Loop over meshes and create soft bodies
		for mesh in meshes:
			meshT = maya.cmds.listRelatives([mesh], parent=True, fullPath=True)[0]
	
			# Duplicate mesh and connect in history
			# Alternate: use a stub func like polyReduce -replaceOriginal 0 -percentage 100 -nodeState 1 -name "stubPolyMod";
			meshCopyT = maya.cmds.polyDuplicateAndConnect(mesh)[0]
			meshCopyShape = maya.cmds.listRelatives(meshCopyT, s=True, fullPath=True)[0]

			if not singleTransform:
				maya.cmds.setAttr((meshCopyT+".t"), 0, 0, 0);  # zero out the transform since get values from WorldSpace
				maya.cmds.setAttr((meshCopyT+".r"), 0, 0, 0);  # zero out the transform since get values from WorldSpace
				maya.cmds.setAttr((meshCopyT+".s"), 1, 1, 1);  # zero out the transform since get values from WorldSpace
				maya.cmds.setAttr((meshCopyT+".inheritsTransform"), 0);
			
			# Create softbody shape
			# NOTE: If plugin not loaded, then sbShape will return unknown nodetype
			#	   and listRelatives will not work as expected
			sbShape = maya.cmds.createNode('bulletSoftBodyShape', name=name);
			sbT = maya.cmds.listRelatives([sbShape], parent=True, fullPath=True)[0];
	
			# Reparent body shape under it
			maya.cmds.parent(sbShape, meshT, r=True, s=True);
			maya.cmds.delete(sbT);
			sbT = meshT;
	
			# Create Solver (proto)
			sol = BulletUtils.getSolver()
	
			# Connect
			maya.cmds.connectAttr((mesh	+".worldMesh"),			(sbShape	   +".inWorldMesh"))
			maya.cmds.connectAttr((sol	 +".outSolverInitialized"), (sbShape	   +".solverInitialized"))
			maya.cmds.connectAttr((sbShape +".outSoftBodyData"),	  (sol		   +".softBodies"), na=True)
			maya.cmds.connectAttr((sol	 +".outSolverUpdated"),	 (sbShape	   +".solverUpdated"))
			maya.cmds.connectAttr((sbShape +".outSolvedMesh"),		(meshCopyShape +".inMesh"), f=True)
	
			# REVISIT: Consider alternatives like a single initSystem bool attr instead of startTime and currentTime.
			#		  Might be able to get around needing it at all
			maya.cmds.connectAttr((sol	 +".startTime"),   (sbShape +".startTime"))
			maya.cmds.connectAttr((sol	 +".currentTime"), (sbShape +".currentTime"))
	
			# Set Attrs (optional, set if value != None)
			# Use the settableAttrs list above to qualify kwargs passed into the function
			for k,v in locals().iteritems():
				if k in settableAttrs and v != None:
					if isinstance(v, list):
						maya.cmds.setAttr('%s.%s'%(sbShape,k), *v) # covers float3 cases
					else:
						maya.cmds.setAttr('%s.%s'%(sbShape,k), v)
					
			# Additional Actions
			if (preserveSourceMesh == False):
				maya.cmds.setAttr((mesh+'.intermediateObject'), True)

			# Alternate: Explicit method		
			#if generateBendConstraints != None:
			#	maya.cmds.setAttr((sbShape+'.generateBendConstraints'), generateBendConstraints)
			#if selfCollision != None:
			#	maya.cmds.setAttr((sbShape+'.selfCollision'), selfCollision)
			#...
	

			if singleTransform:
				# Move the solved mesh under the same transform as the original mesh
				maya.cmds.parent(meshCopyShape, meshT, relative=True, shape=True)
				maya.cmds.reorder(sbShape, back=True)
				maya.cmds.delete(meshCopyT)
				maya.cmds.setAttr(sbShape + '.localSpaceOutput', True)
			else:	
				# We will keep the solved mesh under the new transform
				# Rename new transform
				maya.cmds.rename(meshCopyT, meshT + "_Solved")

			# Update list of returned nodes
			returnedNodes.append(sbT)
			returnedNodes.append(sbShape)
			

		# If command echoing is off, echo this short line.
		if (not maya.cmds.commandEcho(query=True, state=True)):
			print("SoftBody.CreateSoftBody.executeCommandCB()")
			print "// Result: %s //" % string.join(returnedNodes, " ")

		# Select and return
		maya.cmds.select(returnedNodes, add=True)
		return returnedNodes


	def addOptionDialogWidgets(self):
		widgetDict = {} # {optionVarDictKey, (widgetClass, widget)}

		widget = maya.cmds.checkBoxGrp(label=maya.stringTable[ 'y_SoftBody.kGenBendConstraints'  ],
									   numberOfCheckBoxes=1)
		widgetDict['generateBendConstraints'] = (maya.cmds.checkBoxGrp, widget)

		widget = maya.cmds.checkBoxGrp(label=maya.stringTable[ 'y_SoftBody.kSelfCollision'  ],
									   numberOfCheckBoxes=1)
		widgetDict['selfCollision'] = (maya.cmds.checkBoxGrp, widget)

		widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_SoftBody.kBendResistance'  ],
										  minValue=0, maxValue=1)
		widgetDict['bendResistance'] = (maya.cmds.floatSliderGrp, widget)

		widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_SoftBody.kLinearStiffness'  ],
										  minValue=.01, maxValue=1)
		widgetDict['linearStiffness'] = (maya.cmds.floatSliderGrp, widget)

		widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_SoftBody.kFriction'  ],
										  minValue=.01, maxValue=1)
		widgetDict['friction'] = (maya.cmds.floatSliderGrp, widget)

		widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_SoftBody.kDamping'  ],
										  minValue=.01, maxValue=1)
		widgetDict['damping'] = (maya.cmds.floatSliderGrp, widget)

		widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_SoftBody.kPressure'  ],
										  minValue=0, maxValue=10)
		widgetDict['pressure'] = (maya.cmds.floatSliderGrp, widget)

		widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_SoftBody.kCollisionMargin'  ],
										  minValue=0.01, maxValue=1)
		widgetDict['collisionMargin'] = (maya.cmds.floatSliderGrp, widget)

		widget = maya.cmds.intSliderGrp(label=maya.stringTable[ 'y_SoftBody.kPositionIterations'  ],
										  minValue=1, maxValue=20)
		widgetDict['positionIterations'] = (maya.cmds.intSliderGrp, widget)

		#widget = maya.cmds.floatSliderGrp(label='Pose Matching',
		#								  minValue=0, maxValue=1)
		#widgetDict['poseMatching'] = (maya.cmds.floatSliderGrp, widget)

		#widget = maya.cmds.checkBoxGrp(label='Enable Pose Match',
		#							   numberOfCheckBoxes=1)
		#widgetDict['enablePoseMatching'] = (maya.cmds.checkBoxGrp, widget)

		widget = maya.cmds.checkBoxGrp(label=maya.stringTable[ 'y_SoftBody.kPreserveSourceMesh'  ],
									   numberOfCheckBoxes=1)
		widgetDict['preserveSourceMesh'] = (maya.cmds.checkBoxGrp, widget)

		widget = maya.cmds.checkBoxGrp(label=maya.stringTable[ 'y_SoftBody.kSingleTransform'  ],
									   numberOfCheckBoxes=1)
		widgetDict['singleTransform'] = (maya.cmds.checkBoxGrp, widget)
		
		return widgetDict
	
	
# =======================================================================

# This method is meant to be used when a particular string Id is needed more than
# once in this file.  The Maya Python pre-parser will report a warning when a
# duplicate string Id is detected.
def _loadUIString(strId):
	try:
		return {
			'kSelectVertsAttached': maya.stringTable[ 'y_SoftBody.kSelectVertsAttached'  ],
			'kOk': maya.stringTable[ 'y_SoftBody.kOk'  ],
			'kCancel': maya.stringTable[ 'y_SoftBody.kCancel'  ],
			'kBulletSoftbodyPerParticleSet': maya.stringTable[ 'y_SoftBody.kBulletSoftbodyPerParticleSet'  ],
		}[strId]
	except KeyError:
		return " "

def setSoftBodyPerParticleMass(newValue=None):
	# Store off original selection
	origSel = maya.cmds.ls(sl=True)

	#Get softBody for verts
	softBodies = maya.cmds.ls(sl=True, dag=True, type='bulletSoftBodyShape')
	if len(softBodies) != 1:
		maya.cmds.select(origSel, r=True)
		maya.OpenMaya.MGlobal.displayError(_loadUIString('kSelectVertsAttached'))
		return

	destShapes = maya.cmds.listConnections('.worldMesh', d=1, sh=1, type='bulletSoftBodyShape')
	if destShapes and len(destShapes)>0:
		maya.cmds.select( destShapes,  add=True)
	srcShapes = maya.cmds.listConnections(".inMesh", s=1, sh=1, type='bulletSoftBodyShape')
	if srcShapes and len(srcShapes)>0:
		maya.cmds.select( srcShapes, add=True)

	# If $newValue is -1, then bring up the prompt
	if (newValue == None): 
		okBut = _loadUIString('kOk')
		cancelBut = _loadUIString('kCancel')
		result = maya.cmds.promptDialog(
			title=_loadUIString('kBulletSoftbodyPerParticleSet'),
			message=maya.stringTable[ 'y_SoftBody.kEnterPerParticleMass'  ],
			button=[ okBut,	cancelBut ],
			defaultButton=okBut,
			cancelButton=cancelBut,
			dismissString=cancelBut)
		if result != okBut:
			maya.cmds.select(origSel, r=True)
			return;
		newValue = float(maya.cmds.promptDialog(query=True, text=True))

	if newValue < 0.0:
		maya.cmds.select(origSel, r=True)
		maya.OpenMaya.MGlobal.displayError(maya.stringTable[ 'y_SoftBody.kCannotHaveANegativeValueForMass'  ])
		return

	softBody = softBodies[0]

	# Get ids
	ids = BulletUtils.extractVertexIds( maya.cmds.ls(sl=True, flatten=True, type='float3') )

	# Set particleMass
	if len(ids) > 0:
		# get the current array of values
		attr = softBody+".particleMass"
		vals = maya.cmds.getAttr(attr)
		# create the array if it doesn't exist
		if (vals == None):
			mesh = maya.cmds.listConnections(softBody+'.inWorldMesh', d=1, sh=1)
			maya.cmds.select(mesh, r=True)
			selList = maya.OpenMaya.MSelectionList()
			maya.OpenMaya.MGlobal.getActiveSelectionList( selList )
			path = maya.OpenMaya.MDagPath()
			comp = maya.OpenMaya.MObject()
			selList.getDagPath(0, path, comp)
			path.extendToShape()
			meshFn = maya.OpenMaya.MFnMesh(path)
			count = meshFn.numVertices()
			vals = [1] * count
		 # override value for selected ids
		for id in ids:
			vals[id] = newValue
		# set the array of values
		maya.cmds.setAttr(attr, vals, type='doubleArray')
	else:
		maya.OpenMaya.MGlobal.displayError(_loadUIString('kSelectVertsAttached'))

	# Set back original selection
	maya.cmds.select(origSel, r=True)


# =======================================================================

def setSoftBodyPerParticleLinearStiffness(newValue=None):
	# Store off original selection
	origSel = maya.cmds.ls(sl=True)

	# If $newValue is -1, then bring up the prompt
	if (newValue == None): 
		okBut = _loadUIString('kOk')
		cancelBut = _loadUIString('kCancel')
		result = maya.cmds.promptDialog(
			title=_loadUIString('kBulletSoftbodyPerParticleSet'),
			message=maya.stringTable[ 'y_SoftBody.kEnterPerParticleLinearStiffness'  ],
			button=[ okBut,	cancelBut ],
			defaultButton=okBut,
			cancelButton=cancelBut,
			dismissString=cancelBut)
		if result != okBut:
			maya.cmds.select(origSel, r=True)
			return;
		newValue = float(maya.cmds.promptDialog(query=True, text=True))

	if newValue < 0.0:
		maya.cmds.select(origSel, r=True)
		maya.OpenMaya.MGlobal.displayError(maya.stringTable[ 'y_SoftBody.kCannotHaveANegativeValueForLinearStiffness'  ])
		return

	#Get softBody for verts
	maya.cmds.select( maya.cmds.listConnections('.worldMesh', d=1, sh=1, type='bulletSoftBodyShape'),  add=True)
	maya.cmds.select( maya.cmds.listConnections(".inMesh", s=1, sh=1, type='bulletSoftBodyShape'), add=True)
	softBodies = maya.cmds.ls(sl=True, dag=True, type='bulletSoftBodyShape')
	if len(softBodies) != 1:
		maya.cmds.select(origSel, r=True)
		maya.OpenMaya.MGlobal.displayError(_loadUIString('kSelectVertsAttached'))
	softBody = softBodies[0]

	# Get ids
	ids = BulletUtils.extractVertexIds( maya.cmds.ls(sl=True, flatten=True, type='float3') )

	# Set particleLinearStiffness
	if len(ids) > 0:
		# get the current array of values
		attr = softBody+".particleLinearStiffness"
		vals = maya.cmds.getAttr(attr)
		# create the array if it doesn't exist
		if (vals == None):
			mesh = maya.cmds.listConnections(softBody+'.inWorldMesh', d=1, sh=1)
			maya.cmds.select(mesh, r=True)
			selList = maya.OpenMaya.MSelectionList()
			maya.OpenMaya.MGlobal.getActiveSelectionList( selList )
			path = maya.OpenMaya.MDagPath()
			comp = maya.OpenMaya.MObject()
			selList.getDagPath(0, path, comp)
			path.extendToShape()
			meshFn = maya.OpenMaya.MFnMesh(path)
			count = meshFn.numVertices()
			vals = [1] * count
		# override value for selected ids
		for id in ids:
			vals[id] = newValue
		# set the array of values
		maya.cmds.setAttr(attr, vals, type='doubleArray')
	else:
		maya.OpenMaya.MGlobal.displayError(_loadUIString('kSelectVertsAttached'))

	# Set back original selection
	maya.cmds.select(origSel, r=True)


# =======================================================================

def setSoftBodyPerParticleBendResistance(newValue=None):
	# Store off original selection
	origSel = maya.cmds.ls(sl=True)

	#Get softBody for verts
	maya.cmds.select( maya.cmds.listConnections('.worldMesh', d=1, sh=1, type='bulletSoftBodyShape'),  add=True)
	maya.cmds.select( maya.cmds.listConnections(".inMesh", s=1, sh=1, type='bulletSoftBodyShape'), add=True)
	softBodies = maya.cmds.ls(sl=True, dag=True, type='bulletSoftBodyShape')
	if len(softBodies) != 1:
		maya.cmds.select(origSel, r=True)
		maya.OpenMaya.MGlobal.displayError(_loadUIString('kSelectVertsAttached'))
		return

	# If $newValue is -1, then bring up the prompt
	if (newValue == None): 
		okBut = _loadUIString('kOk')
		cancelBut = _loadUIString('kCancel')
		result = maya.cmds.promptDialog(
			title=_loadUIString('kBulletSoftbodyPerParticleSet'),
			message=maya.stringTable[ 'y_SoftBody.kEnterPerParticleBendResistance'  ],
			button=[ okBut,	cancelBut ],
			defaultButton=okBut,
			cancelButton=cancelBut,
			dismissString=cancelBut)
		if result != okBut:
			maya.cmds.select(origSel, r=True)
			return;
		newValue = float(maya.cmds.promptDialog(query=True, text=True))

	if newValue < 0.0:
		maya.cmds.select(origSel, r=True)
		maya.OpenMaya.MGlobal.displayError(maya.stringTable[ 'y_SoftBody.kCannotHaveANegativeValueForBendResistance'  ])
		return

	softBody = softBodies[0]

	# Get ids
	ids = BulletUtils.extractVertexIds( maya.cmds.ls(sl=True, flatten=True, type='float3') )

	# Set particleBendResistance
	if len(ids) > 0:
		# get the current array of values
		attr = softBody+".particleBendResistance"
		vals = maya.cmds.getAttr(attr)
		# create the array if it doesn't exist
		if (vals == None):
			mesh = maya.cmds.listConnections(softBody+'.inWorldMesh', d=1, sh=1)
			maya.cmds.select(mesh, r=True)
			selList = maya.OpenMaya.MSelectionList()
			maya.OpenMaya.MGlobal.getActiveSelectionList( selList )
			path = maya.OpenMaya.MDagPath()
			comp = maya.OpenMaya.MObject()
			selList.getDagPath(0, path, comp)
			path.extendToShape()
			meshFn = maya.OpenMaya.MFnMesh(path)
			count = meshFn.numVertices()
			vals = [1] * count
		# override value for selected ids
		for id in ids:
			vals[id] = newValue
		# set the array of values
		maya.cmds.setAttr(attr, vals, type='doubleArray')
	else:
		maya.OpenMaya.MGlobal.displayError(_loadUIString('kSelectVertsAttached'))

	# Set back original selection
	maya.cmds.select(origSel, r=True)


# =======================================================================

def paintSoftBodyVertexProperty(vertexProperty, softbody=None):
	'''Perform paint action on SoftBody node
	'''
	# if mesh not specified, then get from current selection
	if softbody == None:
		softbodies = BulletUtils.getSelectedSoftBodies()
		if (softbodies != None) and (len(softbodies) > 0):
			softbody = softbodies[0]
			if len(softbodies) > 1:
				maya.cmds.warning(maya.stringTable[ 'y_SoftBody.kMultipleBulletUsingFirst'  ])
		
	if softbody != None:
		maya.mel.eval('source "artAttrCreateMenuItems"; artSetToolAndSelectAttr("artAttrCtx", "mesh.%s.%s")'%(softbody,vertexProperty))
		
		# If the soft body does not have any vertices being mapped, initialize the map to 1.0.
		vals = maya.cmds.getAttr(softbody + "." + vertexProperty)
		if (vals == None):
			ctx = maya.cmds.currentCtx()
			maya.cmds.artAttrCtx(ctx, edit=True, value=1.0)
			maya.cmds.artAttrCtx(ctx, edit=True, clear=True)
	else:
		maya.OpenMaya.MGlobal.displayError(maya.stringTable[ 'y_SoftBody.kNoBulletSoftbodyshape'  ])

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
