import math
import maya.cmds as cmds
import maya.mel as mel

from maya.app.stereo import stereoCameraErrors
from maya.app.stereo import stereoCameraUtil
from maya.app.stereo import stereoCameraRig
from maya.app.stereo import stereoCameraSets




def switchToSinglePerspLayout():
	"""
	Switch the current view into to single perspective stereo mode.
	"""
	if not stereoCameraUtil.runCallbackChecks():
		return
	mel.eval( "setNamedPanelLayout `localizedPanelLabel( " + "\"Stereo Persp\"" + " )`" )
	cmds.refresh()

def switchToOutlinerPerspLayout():
	"""
	Switch the current view into a outliner / persp viewer mode.
	"""
	if not stereoCameraUtil.runCallbackChecks():
		return
	
	mel.eval( "setNamedPanelLayout `localizedPanelLabel( " + "\"Stereo Persp/Outliner\"" + " )`" )
	cmds.refresh()

def currentViewCameraFromEditor( editor ):
	"""
	Given an editor retrieve the current camera from that editor.
	"""
	theCam = cmds.stereoCameraView( editor, query=True, camera=True )
	if theCam:
		relatives = cmds.listRelatives( theCam, parent=True )
		if relatives:
			return relatives[0]
	return theCam

def currentViewRigFromEditor( editor ):
	theRig = cmds.stereoCameraView( editor, query=True, rigRoot=True )
	return theRig 

def currentViewCamera( *args ):
	"""
	Get the camera that is assigned to the current view.
	"""
	if not stereoCameraUtil.runCallbackChecks():
		return
	
	editor = ''
	if len(args):
		editor = args[0]
	else:
		panel = cmds.getPanel( withFocus=True )
		editor = panel + 'Editor'
	
	return currentViewCameraFromEditor( editor )


def selectCamera( *args ):
	"""
	Select the camera that is in the current view.
	"""
	parent = currentViewCamera( args )
	if parent:
		cmds.select( parent, replace=True )

def setConvergenceDistanceToSelected( *args ):
	"""
	Sets the convergence distance on the current viewing camera to the
	the specified selection. If more than one object is selected. It
	takes the average distance between each selection. Note, this only
	works with the standard StereoCamera rig and does not support generic rig
	data types.
	"""
	selList = cmds.ls( sl=True )
	if not selList:
		# Report an error if nothing was selected.
		#
		stereoCameraErrors.displayError( 'kNothingSelected' )

	# Find the centroid of all selected objects. This will become the
	# convergence distance.
	#
	avg = [0,0,0]
	for s in selList:
		pos = cmds.xform( s, query=True, worldSpace=True, translation=True )
		avg = [avg[0] + pos[0], avg[1] + pos[1], avg[2] + pos[2]]
	c = len(selList)
	avg = [avg[0]/c, avg[1]/c, avg[2]/c]
	parent = currentViewCamera( args )
	pos = cmds.xform( parent, query=True, worldSpace=True, translation=True )
	sub_pos = [avg[0] - pos[0], avg[1] - pos[1], avg[2] - pos[2]]
	dist = sub_pos[0] * sub_pos[0] + sub_pos[1] * sub_pos[1] + sub_pos[2]*sub_pos[2]
	dist = math.sqrt( dist )
	# The smallest convergence distance we allow is 1 cm.
	#
	if dist < 1:
		dist = 1
	stereoCameraRig.setZeroParallaxPlane( parent, dist )
	return dist
	
def switchToSelected( *args ):
	"""
	Switch the viewing camera to the current selection.
	"""
	if not stereoCameraUtil.runCallbackChecks():
		return
	nodes = stereoCameraRig.selectedCameras()
	if nodes:
		switchToCamera( nodes[0], args[0] )
	else:
		stereoCameraErrors.displayError( 'kNotAValidStereoCamera' )

def getValidEditor( panel ):
	if panel:
		ttype = cmds.getPanel( typeOf=panel )
		if ttype == 'scriptedPanel':
			stype = cmds.scriptedPanel( panel, query=True, type=True )
			if stype == 'Stereo':
				return panel + 'Editor'

	# We don't recognize this panel type. Try to find one we like.
	#
	spanel = cmds.getPanel( scriptType='Stereo' )
	if spanel and spanel[0]:
		return spanel[0] + "Editor"
	else:
		stereoCameraErrors.displayError( 'kNoValidPanelsFound' )
	return None
		
def getValidPanel( editor ):
	"""
	This function checks the given editor to make sure it is an editor
	that we recognize. If it is not an known editor then we try to
	find an editor that will work.
	"""
	panel = cmds.modelEditor( editor, query=True, panel=True )
	ttype = cmds.getPanel( typeOf=panel )
	if ttype == 'scriptedPanel':
		stype = cmds.scriptedPanel( panel, query=True, type=True )
		if stype == 'Stereo':
			return editor

	# We don't recognize this panel type. Try to find one we like.
	#
	spanel = cmds.getPanel( scriptType='Stereo' )
	if spanel and spanel[0]:
		cmds.scriptedPanel( spanel[0], edit=True, replacePanel=editor )
		return spanel[0] + "Editor"
	else:
		stereoCameraErrors.displayError( 'kNoValidPanelsFound' )

def switchToCamera( *args ):
	"""
	Switch the viewport editor the specified camera name.
	"""
	if not stereoCameraUtil.runCallbackChecks():
		return
	editor = args[1]
	cameraName = args[0]
	root = cameraName

	# Display an error to the user if the camera set contains no data. 
	#
	if cmds.objectType(cameraName, isa="cameraSet"):
		nl = cmds.cameraSet( cameraName, query=True, numLayers=True )
		if nl == 0:
			stereoCameraErrors.displayError( 'kNoDataInCameraSet', cameraName )
	
	editor = getValidPanel( editor )

	# Users can switch to a stereo camera using camera sets or via
	# rigs.  If it is a camera set then we don't need to find the
	# root.  We can simply view that camera set.
	#
	if not cmds.objectType(cameraName, isa="cameraSet"):
		root = stereoCameraRig.rigRoot( cameraName )
		
	cmds.stereoCameraView( editor, edit=True, rigRoot=root )

	if len(args) > 2 and args[2]:
		# The 3rd argument indicates if we should select the camera
		# after assignment. It is tiggered by an option box on the
		# camera switcher.
		#
		cmds.select( cameraName, replace=True )

def switchToCameraLeft( cameraName, editor ):
	"""
	Additional wrapper layer around switchToCamera. This function switches
	to the current camera and also toggles the view mode to be 'left'
	"""
	if not stereoCameraUtil.runCallbackChecks():
		return
	switchToCamera( cameraName, editor )
	cmds.stereoCameraView( editor, edit=True, displayMode="leftEye" )

def switchToCameraRight( cameraName, editor ):
	"""
	Additional wrapper layer around switchToCamera. This function switches
	to the current camera and also toggles the view mode to be 'right'
	"""
	if not stereoCameraUtil.runCallbackChecks():
		return
	switchToCamera( cameraName, editor )
	cmds.stereoCameraView( editor, edit=True, displayMode="rightEye" )

def switchToCameraCenter( cameraName, editor ):
	"""
	Additional wrapper layer around switchToCamera. This function switches
	to the current camera and also toggles the view mode to be 'center'
	"""
	if not stereoCameraUtil.runCallbackChecks():
		return
	switchToCamera( cameraName, editor )
	cmds.stereoCameraView( editor, edit=True, displayMode="centerEye" )

def swapCameras( *args ):
	"""
	Toggle the swap bit on the view.
	"""
	if not stereoCameraUtil.runCallbackChecks():
		return
	if len(args):
		editor = args[0]
		cmds.stereoCameraView( editor, edit=True, swapEyes=True )
	else:
		panels = cmds.lsUI( panels=True )
		for panel in panels:
			ttype = cmds.getPanel( typeOf=panel )
			if ttype == 'scriptedPanel':
				stype = cmds.scriptedPanel( panel, query=True, type=True )
				if stype == 'Stereo':
					editor = panel + 'Editor'
					cmds.stereoCameraView( editor, edit=True, swapEyes=True )
	
def swapCamerasState( *args ):
	"""
	Query the swap bit on the view.
	"""
	if not stereoCameraUtil.runCallbackChecks():
		return
	if len(args):
		editor = args[0]
		return cmds.stereoCameraView( editor, query=True, swapEyes=True )
	else:
		panels = cmds.lsUI( panels=True )
		for panel in panels:
			ttype = cmds.getPanel( typeOf=panel )
			if ttype == 'scriptedPanel':
				stype = cmds.scriptedPanel( panel, query=True, type=True )
				if stype == 'Stereo':
					editor = panel + 'Editor'
					return cmds.stereoCameraView( editor, query=True, swapEyes=True )

def switchToCameraSet( *args ):
	"""
	Switch the viewport editor the specified cameraSet name.
	"""
	if not stereoCameraUtil.runCallbackChecks():
		return
	editor = args[1]
	cameraSetName = args[0]
	editor = getValidPanel( editor )
	if cmds.objectType( cameraSetName, isa="cameraSet" ):
		nl = cmds.cameraSet( cameraSetName, query=True, numLayers=True );
		if nl == 0:
			stereoCameraErrors.displayError( 'kNoDataInCameraSet', cameraSetName )
		else: 
			cmds.stereoCameraView( editor, edit=True, rigRoot=cameraSetName )

def toggleUseCustomBackground( *args ):
	"""
    Toggle whether the current viewport background should match the background
    that is defined in the user preferences.
	"""
	if not stereoCameraUtil.runCallbackChecks():
		return
	editor = ''
	if len(args):
		editor = args[0]
	else:
		panel = cmds.getPanel( withFocus=True )
		editor = panel + 'Editor'

	usePref = cmds.stereoCameraView( editor, query=True,
				useCustomBackground = True)
	cmds.stereoCameraView( editor, edit=True,
				useCustomBackground = not usePref )

def useCustomBackgroundState( *args ):
	"""
	Return the state (True/False) of whether we use the display preferences or
	a solid background.
	"""
	if not stereoCameraUtil.runCallbackChecks():
		return
	editor = ''
	if len(args):
		editor = args[0]
	else:
		panel = cmds.getPanel( withFocus=True )
		editor = panel + 'Editor'
	return cmds.stereoCameraView( editor, query=True, 
				useCustomBackground = True)

def adjustBackground( *args ):
	"""
	Get the camera that is assigned to the current view.
	"""
	if not stereoCameraUtil.runCallbackChecks():
		return
	editor = ''
	if len(args):
		editor = args[0]
	else:
		panel = cmds.getPanel( withFocus=True )
		editor = panel + 'Editor'

	result = cmds.stereoCameraView( editor, query=True, viewColor=True )
	result = cmds.colorEditor( alpha=float(result[3]),
							   rgbValue=[float(result[0]),
										 float(result[1]),
										 float(result[2])] )
	buffer = result.split()
	if '1' == buffer[3]:
		values = cmds.colorEditor(query=True, rgb=True)
		alpha = cmds.colorEditor(query=True, alpha=True)
		cmds.stereoCameraView( editor, edit=True,
					   viewColor=[values[0], values[1], values[2], alpha],
                       useCustomBackground = True )
		
def stereoCameraViewCallback( *args ):
	"""
	Main callback point for sending information to the editor command.
	The format of the callback is as follows:
	
	arg1 = the name of the editor
	arg2 = keyword dictionary represented as a string.
	
	"""
	if not stereoCameraUtil.runCallbackChecks():
		return
	keywords = eval(args[1])
	keywords['edit'] = True
	# Run the command
	#
	cmds.stereoCameraView( args[0], **keywords )

def activeModeAvailable( *args ):
	"""
	Query the custom view to determine if the specified mode is available.
	"""
	modeSupported=cmds.stereoCameraView( args[0], query=True, activeSupported=True )
	return (modeSupported==1)

def checkState( *args ):
	"""
	This is a callback that is invoked by the menu creation code. It is
	used to determine if the menu item should be checked. The first argument
	is assumed to be the displayMode name to check against and the second
	argument is assumed to be the name of the editor. Both are string types.
	"""
	displayMode=cmds.stereoCameraView( args[1], query=True, displayMode=True )
	if displayMode == args[0]:
		return True
	return False

def createStereoCameraViewCmdString( command, editor, the_args ):
	"""
	Packs the given arguments into a python string that can be evaluated
	at runtime.

	- the_args is assumed to be represented as a dictionary
	- editor is the custom editor.
	"""
	if type(the_args) == dict:
		return 'from maya.app.stereo import stereoCameraCustomPanel\nstereoCameraCustomPanel.stereoCameraViewCallback( "%s", "%s" )' % (editor[0], str(the_args))
	else:
		return the_args

def addNewCameraToCurrentSet( rigRoot, panel ):
	"""
	This is the main function for adding camera rigs to a camera
	set. Given a valid stereo rig, add that rig to the current camera
	set. If a camera set does not exist then, create one and make the
	view aware of the camera set.
	"""
	if not stereoCameraUtil.runCallbackChecks():
		return
	editor = getValidEditor( panel )
	currentRig = currentViewRigFromEditor( editor )
	cameraSet = stereoCameraSets.addNewRigToSet( rigRoot, currentRig )
	cmds.stereoCameraView(editor, edit=True, rigRoot=cameraSet )

def initialize():
	"""
	Main initialization routine for registering a new panel type. This menu
	registers the new panel with Maya. We also install callbacks to monitor
	for new scene changes.
	"""
	# Note: custom panels are currently not supported by python. So we
	# need to call MEL code to do the setup and creation of the custom
	# scripted panel type.
	#
	cps = 'stereoCameraCustomPanelSetup'
	script = 'eval \"source \\\"%s.mel\\\"; %s(\\\"\\\");\"' % (cps, cps)
	mel.eval( script )

def uninitialize():
	"""
	Main uninitialization routine for deregistering the new panel and removes
	callbacks.
	"""
	script = 'stereoCameraCustomPanelCleanup;'
	mel.eval( script )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
