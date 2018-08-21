import maya
maya.utils.loadStringResourcesForModule(__name__)

import maya.cmds as cmds

def positionAlongCurve():
	'''Space selected objects along selected curve by its parameterization.
	Rebuilding the curve to even parameterization will space the objects evenly.'''
	
	objects = cmds.ls( selection=1 )
	
	# should have at least 3 objects, 1 being a curve
	if (objects.__len__()>2):
		
		# check for the curve in the selection
		curve = r'temporaryCurveNamePlaceholder'
		for object in objects:
			child = cmds.listRelatives( object, shapes=1, fullPath=1)
			# print (child )
			if (cmds.nodeType( child ) == r'nurbsCurve'):
				print (maya.stringTable['y_positionAlongCurve.kTest' ])
				curve = object

		if (curve == r'temporaryCurveNamePlaceholder'):
			errorString = maya.stringTable['y_positionAlongCurve.kNoCurve' ]
			#raise RuntimeError( 'error _L10N( kNoCurve, "Position Along Curve: No curve selected to position along" )' )
			raise RuntimeError( errorString )
				
		# remove the curve from the list of selected objects
		objects.remove( curve )
		
		numObjects = objects.__len__()
		
		if (numObjects>1):
			for i in range( 0, numObjects ):
				position = list()
				normal = list()
				# first object goes to start of curve
				if i == 0:
					position = cmds.pointOnCurve( curve, position=1, parameter=0, turnOnPercentage=1 )
					normal = cmds.pointOnCurve( curve, normal=1, parameter=0, turnOnPercentage=1 )
				# middle objects get evenly spaced along curve
				elif i < numObjects-1:
					position = cmds.pointOnCurve( curve, position=1, parameter=((1.0/(numObjects-1))*i), turnOnPercentage=1)
					normal = cmds.pointOnCurve( curve, normal=1, parameter=((1.0/(numObjects-1))*i), turnOnPercentage=1)
				# last object goes to end of curve
				else:
					position = cmds.pointOnCurve( curve, position=1, parameter=1, turnOnPercentage=1 )
					normal = cmds.pointOnCurve( curve, normal=1, parameter=1, turnOnPercentage=1 )
					
				# move object to appropriate point on the curve
				#cmds.move( position[0], position[1], position[2], objects[i], absolute=1 )
				
				# get the pivot for offsetting the object based on pivot
				pivot = cmds.xform( objects[i], query=1, rotatePivot=1 )
				position[0] = position[0] - pivot[0]
				position[1] = position[1] - pivot[1]
				position[2] = position[2] - pivot[2]
				cmds.xform( objects[i], translation= (position[0], position[1], position[2])  )

	else:
		errorString = maya.stringTable['y_positionAlongCurve.kNoSelection' ]
		#raise RuntimeError( 'error _L10N( kNoSelection, "Position Along Curve: Nothing selected. Select a curve and two or more nodes." )' )
		raise RuntimeError( errorString )


# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
