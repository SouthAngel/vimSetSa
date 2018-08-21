
"""
This module provides camera set support to the stereo camera
plug-in. Camera sets allow the users to break a single camera shot
into layers. Instead of drawing all objects with a single camera, you
can isolate the camera to only focus on certain objects and layer another
camera into the viewport that draws the other objects.  

For instance, a set of stereo parameters may make the background
objects divergent beyond the tolerable range of the human perceptual
system. However, you like the settings because the main focus is in
the foreground and the depth is important to the visual look of the
scene.  You can use camera sets to break apart the shot into a
foreground stereo camera and background stereo camera. The foreground
stereo camera will retain the original parameters; however, it will
only focus on the foreground elements.  The background stereo camera
will have a different set of stereo parameters and will only draw the
background element.
"""

from maya import cmds
from maya.app.stereo import stereoCameraUtil
from maya.app.stereo import stereoCameraRig
from maya.app.stereo import stereoCameraErrors 

def parentToLayer0Rig( rigRoot, cameraSet=None ):
	"""
	When adding a new layer to a camera set, the most common desired
	placement of that new rig is under the primary camera, which is
	at layer 0. This function performs the task of looking up the
	transform at layer 0 and parenting the new rig under its
	transform. 
	"""
	
	if cameraSet and len(rigRoot)>0:
		layers = cmds.cameraSet( cameraSet, query=True, numLayers=True )
		if layers == 0:
			return
		camSetRig = cmds.cameraSet( cameraSet,
									query=True, layer=0, camera=True )
		camSetRigParent = cmds.ls( camSetRig, long=True, dag=True )[0]
		rigRootToParent = cmds.ls( rigRoot, long=True, dag=True )[0]
			
		if camSetRigParent != rigRootToParent and cmds.objectType( rigRootToParent, isa="transform" ):
			cmds.parent( rigRootToParent, camSetRigParent, relative=True )

def _getDefinition( rigType ):
	"""
	Get the definition for this object.  
	"""
	definitions = [] 
	if rigType: 
		try:
			definitions = cmds.stereoRigManager(rigDefinition=rigType)
		except:
			stereoCameraErrors.displayError('kNoStereoRigCommand', rigType)
	return definitions 

def _callFromDefinition( definitions, rigType, keywords, args ):
	"""
	Call the custom callback for this object.  
	"""
	if len(definitions) >= 3 and definitions[2] != '':
		stereoCameraUtil.__call( definitions[0], definitions[2],
								 rigType, keywords, args )
		
def __attachToCameraSet( rigRoot, cameraSet, objectSet=None ):
	"""
	Attach the rigRoot to the cameraSet and assign it to the camera
	set.  If an objectSet is provided then also attach it to the same layer
	"""
	if not objectSet: 
		cmds.cameraSet( cameraSet, edit=True, appendTo=True, camera=rigRoot )
	else:
		cmds.cameraSet( cameraSet, edit=True, appendTo=True, camera=rigRoot, objectSet=objectSet )
	layerId = cmds.cameraSet( cameraSet, query=True, numLayers=True )-1		
	rigType = stereoCameraRig.rigType( rigRoot )
	definitions = _getDefinition( rigType )
	keywords = {'cameraSet' : cameraSet,
				'layer' : layerId}
	args = [rigRoot]
	_callFromDefinition( definitions, rigType, keywords, args ) 


def notifyCameraSetCreateFinished( cameraSet, rigType='StereoCamera' ):
	"""
	Developers who need to customize camera sets have requested the ability to
	receive nofications when we have finished created a camera set. This
	is the function that kick-starts that notification. 
	"""
	definitions = _getDefinition( rigType )
	keywords = {'cameraSet' : cameraSet,
				'allDone'   : 1 }
	args = []
	_callFromDefinition( definitions, rigType, keywords, args )
	
def isCameraSet( cameraSet ):
	"""
	Returns true if the object is a camera set.  This is simply
	a wrapper objectType -isa

	"""
	return cmds.objectType( cameraSet, isa="cameraSet" )
	
def addNewRigToSet( newRigRoot, currentRigRootOrCameraSet, objectSet=None ): 
	"""
	This is the main function for adding cameras/rigs to a camera
	set. Given a valid stereo rig, add that rig to the specified
	camera set. The second argument to this function can either be the
	existing rig root that we are layering or the current camera set.
	
	If it is the camera set then simply append the newRigRoot to the
	camera set. If it is a rig then create a new camera set attach
	the current rig to the set and then append the newRigRoot to
	that set.

	We return the camera set on exit. 
	"""
	cameraSet = None
	if currentRigRootOrCameraSet:
		if cmds.objectType( currentRigRootOrCameraSet, isa="cameraSet" ):
			cameraSet = currentRigRootOrCameraSet
		else:
			cameraSet = cmds.createNode( 'cameraSet' )
			__attachToCameraSet( currentRigRootOrCameraSet, cameraSet, objectSet )
	__attachToCameraSet( newRigRoot, cameraSet, objectSet )
	return cameraSet 

def _gatherSelObjects( ):
	"""
	Private method that gets the active selection list, finds all selected
	transforms and returns two lists:
	1) a list of cameras attached to camera sets stuff into a python set in the
   	   form  (cameraSet, cameraSet layerId, cameraName, objectSet)
	2) a list of objects to attach to the items found in 1)
	""" 
	objects = cmds.ls( type="transform", sl=True )
	cameras = []
	setObj = [] 
	for x in objects:
		if ( stereoCameraRig.isRigRoot( x ) ): 
			cameras.append( x )
		else:
			setObj.append( x )
	camWithSets = [] 
	for c in cameras:
		connections = cmds.listConnections( c + ".message", t='cameraSet' )
		if not connections:
			continue
		# Scan over all unique connections. list(set(connections))
		# uniquifies the list. A camera can belong to the same set
		# twice.
		#
		for con in list(set(connections)):
			layers = cmds.cameraSet( con, query=True, numLayers=True )
			for l in range(layers):
				camera = cmds.cameraSet( con, query=True, layer=l, camera=True )
				if ( cmds.ls(camera, l=True) == cmds.ls(c,l=True) ):
					objSet = cmds.cameraSet( con, query=True,
											 layer=l, objectSet=True)
					camWithSets.append( (con, l, camera, objSet) )
	
	if len(camWithSets) == 0:
		stereoCameraErrors.displayError( 'kNoValidCameraSelected' )
	if len(setObj) == 0:
		stereoCameraErrors.displayError( 'kNoObjectsSelected' )
	return (camWithSets, setObj)

def _makeOrSet( cameraSet, layerId, objectSet, setObj, add=True ):
	objSet = objectSet
	if not objSet:
		objSet = cmds.createNode( 'objectSet' )
		cmds.cameraSet( cameraSet, edit=True, layer=layerId, objectSet=objSet )
	if add: 
		cmds.sets( setObj, addElement=objSet )
	else:
		cmds.sets( setObj, remove=objSet )

def makeLinks( ):
	camWithSets, setObj = _gatherSelObjects()
	if len(camWithSets) == 0 or len(setObj) == 0:
		return

	for c in camWithSets:
		_makeOrSet( c[0], c[1], c[3], setObj )
	
def breakLinks( ):
	camWithSets, setObj = _gatherSelObjects()
	if len(camWithSets) == 0 or len(setObj) == 0:
		return
	
	for c in camWithSets:
		_makeOrSet( c[0], c[1], c[3], setObj, add=False )	
		

	



# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
