import maya.cmds as cmds
import maya.mel as mel

from maya.app.stereo import stereoCameraUILabel
from maya.app.stereo import stereoCameraSettings
from maya.app.stereo import stereoCameraRig

"""
This module contains the code for creation of all UI code around the
specialized stereo viewer.
"""

def populateEditorSettings( editor ):
	"""
	This routine populates some initial values onto the specified editor.
	It does this by searching the Maya scene for any selected stereo
	camera rigs.  If there are no stereo rigs selected, then it searches
	the scene for the first available stereo rig.  If there are no stereo
	rigs in the scene, then it defaults to using the perspective camera for
	center, left, and right views.
	"""
	
	# Do we have any selected stereo cameras.
	# 
	selList = cmds.ls( sl=True )
	viewCam = None
	stereoFound = True

	if selList:
		for s in selList: 
			if stereoCameraRig.isStereoRig( s ):
				viewCam = s

	# Do we have any stereo rigs in this scene.
	# 
	if not viewCam:
		rigs = stereoCameraRig.listRigs()
		if rigs:
			viewCam = rigs[0] 

	# Fallback to using the persp camera, which is always in the scene.
	#
	if not viewCam:
		cams = cmds.listCameras( perspective=True )
		viewCam = cams[0] 
		stereoFound = False 

	# Set the default value on the plugin.
	# 
	cmds.stereoCameraView( editor, edit=True, camera=viewCam )
	if stereoFound: 
		cmds.stereoCameraView(editor, edit=True, rightCamera=stereoCameraRig.rightCam(viewCam))
		cmds.stereoCameraView(editor, edit=True, leftCamera=stereoCameraRig.leftCam(viewCam))
	cmds.stereoCameraView( editor, edit=True, centerCamera=viewCam )
	cmds.stereoCameraView( editor, edit=True, displayMode='centerEye' )

def stereoCameraCreateToolBar( editor ):
	"""
	Creates the main tool bar on the customized model editor.
	"""
	iconButtons = stereoCameraSettings.gViewLayoutButtons
	exsts = cmds.optionVar( exists='stereoCameraStereoToolBarDisplay' )
	if not exsts:
		cmds.optionVar( intValue=('stereoCameraStereoToolBarDisplay', False) )
	vis = not cmds.optionVar( query='stereoCameraStereoToolBarDisplay' )

	framel = cmds.frameLayout( 'stereoCameraToolBar', label="test", 
							   visible=True, borderVisible=False,
							   collapsable=True, labelVisible=False,
							   collapse=vis ) 

	melCreateCmd = 'createModelPanelBar ' + framel + ' ' + editor
	mel.eval(melCreateCmd)

	cmds.modelEditor(editor, edit=True, editorChanged="updateModelPanelBar")

	return framel 

def toolBarPack( editor, form ):
	cmds.setParent( form )
	layout = stereoCameraCreateToolBar( editor )

	cmds.formLayout( form, edit=True,
					 attachForm=[ (layout, 'top',   0),
								  (layout, 'left',  0),
								  (layout, 'right', 0),
								  (editor, 'left',  0),
								  (editor, 'bottom',0),
								  (editor, 'right', 0) ],
					 attachNone=[ (layout, 'bottom') ],
					 attachControl=[ (editor, 'top', 0, layout) ] )

def createViewUI( panelName, editor ):
	"""
	Creates the UI around a StereoCamera 3d View tool. This includes tool bar and
	corresponding buttons.  You can pass in a panel name and an editor name
	to this procedure.  If panelName == '' then a window is created for the
	UI.  If editor == '' then a new editor is created. Otherwise, a named
	editor tells this method that one has been created and it should
	simple parent the editor to the created UI.
	"""

	isNewEditor = False 
	if not editor:
		isNewEditor = True

	# Create a new window if we have no panel.
	#
	window = ''
	if not panelName:
		window = cmds.window()

	form   = cmds.formLayout()
	if isNewEditor: 
		# No previous editor was created. We need to create a new
		# editor for this window.
		#
		if not panelName: 
			editor = cmds.stereoCameraView()
		else:
			editor = cmds.stereoCameraView( panelName + 'Editor' )
	else:
		# We already have an editor. Parent this edtor to the
		# newly created form.
		#
		cmds.stereoCameraView( editor, edit=True, unParent=True )
		cmds.stereoCameraView( editor, edit=True, parent=form )

	toolBarPack( editor, form ) 

	if isNewEditor:
		populateEditorSettings( editor )

	if window:
		cmds.showWindow( window )
		
	return editor

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
