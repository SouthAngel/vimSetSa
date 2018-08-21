import maya
maya.utils.loadStringResourcesForModule(__name__)

import re, string
import maya.cmds as cmds
import maya.mel as mel

from maya.app.stereo import stereoCameraUILabel
from maya.app.stereo import stereoCameraSettings
from maya.app.stereo import stereoCameraUI
from maya.app.stereo import stereoCameraRig
from maya.app.stereo import stereoCameraSets
from maya.app.stereo import multiRig 

"""
This module is responsible for populating various menu sets in the Maya UI.
It assigns menu items to both the 'Maya > Create' menu and the 'Maya > Display'
menu.
"""

def populateItems( subMenu, items ):
	"""
	Populates the given submenu with the specified items. subMenu
	is a string identifier of the sub menu and items is a list of
	stereoCameraUILabel entries.
	"""
	cmds.setParent( subMenu, menu=True )

	for i in items:
		if i and i.type() == stereoCameraUILabel.UILabelGroup:
			parent = subMenu
			if not i.radioGroup():
				parent = cmds.menuItem( label=i.label(), subMenu=True )
			else:
				cmds.radioMenuItemCollection()
			if i.postMenuCommand():
				i.setArgs( [parent] )
				cmds.menuItem( parent, edit=True, postMenuCommand=i.command() )
				cmds.setParent( '..', menu=True )
			else: 
				populateItems( parent, i.items() )
		else:
			if not i or not i.label():
				if not i.divider_label():
					cmds.menuItem( divider=True )
				else:
					cmds.menuItem( divider=True, dividerLabel=i.divider_label() )
			else:
				radiogrp = i.radioGrpItem()
				item = None
				if radiogrp:
					radioval = i.radioItemOn()
					cmds.menuItem( label=i.label(),
								   annotation=i.annotation(),
								   image=i.image(), command=i.command(),
								   radioButton=radioval,
								   enable=(i.enabled()) )
				elif i.check_box() != "":
					callbackMethod = i.check_box()
					cmds.menuItem( label=i.label(),
								   annotation=i.annotation(),
								   command=i.command(),
								   checkBox=callbackMethod() )
				else:
					cmds.menuItem( label=i.label(),
								   annotation=i.annotation(),
								   image=i.image(), command=i.command(),
								   enable=(i.enabled()) )

				if i.option_box():
					cmds.menuItem( label=i.label()+'Option',
								   annotation=i.annotation() + ' Options',
								   command=i.command_option(),
								   optionBox=True )


	cmds.setParent( '..', menu=True )
	
def addCustomViewMenus( parent, editor ):
	"""
	This procedure adds new menu items to the current panel view.
	"""
	
	cmds.setParent( parent, menu=True )

	cmds.menu( parent, edit=True, deleteAllItems=True )
	
	mitems = []
	for i in stereoCameraSettings.gStereoMenuItems:
		if i != stereoCameraUILabel.EmptyLabel:
			i.setArgs( [editor] )
		mitems.append( i )

	populateItems( parent, mitems )

	cmds.setParent( '..', menu=True )

def __makeShape( dagNode ):
	if not cmds.objectType(dagNode, isAType='camera'):
		shapes = cmds.listRelatives(dagNode, path=True, shapes=True,
									noIntermediate=True,
									type='camera')
		if shapes <> None:
			return shapes[0]
	return dagNode

def __addRigMenuItem( rigCmd, camCmd, rig ):
	cmds.menuItem(label=rig, command=(rigCmd % {'arg1': rig}))

	# Show the cameras under the rig, in a sub menu.
	# Show Left, Center, Right first, then a divider, then
	# other cameras if any.
	labelVal = maya.stringTable['y_stereoCameraMenus.kRigContent' ] % {'arg1': rig}
	cmds.menuItem(label=labelVal, subMenu=True)

	# Get the default cameras
	left =   stereoCameraRig.leftCam(rig)
	right =  stereoCameraRig.rightCam(rig)
	center = stereoCameraRig.centerCam(rig)

	# Add the default cameras, make sure to remove the duplicates. In
	# particular, some rigs may use the same camera for center an
	# left or right.
	done = set()

	for camDesc in [[left, ''],
					[center, '%(arg1)s (center)'],
					[right, '']]:
		cam = camDesc[0]
		camLabel = cam
		if camDesc[1] <> '':
			camLabel = camDesc[1] % {'arg1': cam}
		camShape = __makeShape(cam)
		if camShape not in done:
			cmds.menuItem(label=camLabel,
						  command=(camCmd % {'arg1': camShape}))
			done.add(camShape)

	# Now add the other cameras if any.
	first = True
	cameras = cmds.listRelatives(rig, type="camera",
								 allDescendents=True, path=True)
	for cam in cameras:
		# Get the transform from the camera
		camXform = cmds.listRelatives(cam, path=True, parent=True)[0]
		if cam not in done:
			if first:
				cmds.menuItem(divider=True)
				first = False
			cmds.menuItem(label=camXform, command=(camCmd % {'arg1': cam}))
			done.add(cam)

	cmds.setParent('..', menu=True)

def __addCameraSetsMenuItem( rigCmd, camCmd, rig ):
	"""
	"""
	layers = cmds.cameraSet( rig, query=True, numLayers=True )
	if layers == 0: 
		return 
	cmds.menuItem(label=rig, command=(rigCmd % {'arg1': rig}))

	# Show the cameras under the rig, in a sub menu.
	# Show Left, Center, Right first, then a divider, then
	# other cameras if any.
	labelVal = maya.stringTable['y_stereoCameraMenus.kCameraSet' ] % {'arg1': rig}
	cmds.menuItem(label=labelVal, subMenu=True)
	rigList = [] 
	for i in range(layers):
		rigList.append( cmds.cameraSet( rig, query=True, layer=i, camera=True ) )
	for r in rigList:
		__addRigMenuItem( rigCmd, camCmd, r )

	cmds.setParent('..', menu=True)
			
def createStereoCameraSubmenus(rigCmd, camCmd, rigOnly=False):
	"""
	Add menus and sub menus for all the stereo rigs.
	For the rig root, rigCmd is attached to the menu callback. %(arg1)s is
	replaced with the root transform
	For all cameras, camCmd is used and %(arg1)s is replaced with the
	camera shape
	"""
	camRigs = stereoCameraRig.listRigs(rigOnly)
	rigCmd = "import maya.mel as mel\nmel.eval('"+rigCmd+"')"
	camCmd = "import maya.mel as mel\nmel.eval('"+camCmd+"')"
	cameraSets = [x for x in camRigs if stereoCameraSets.isCameraSet(x)]
	cameras = [x for x in camRigs if not stereoCameraSets.isCameraSet(x)] 
	
	[__addRigMenuItem(rigCmd, camCmd, x) for x in cameras]
	cmds.menuItem(divider=True) 
	[__addCameraSetsMenuItem(rigCmd, camCmd, x) for x in cameraSets]



def gatherCreateMenuUILabels():
	rigs = cmds.stereoRigManager( listRigs=True )
	menuTitle = maya.stringTable['y_stereoCameraMenus.kNewStereoCamera' ]
	menuAnnot = maya.stringTable['y_stereoCameraMenus.kNewStereoCameraAnnot' ]
	rigCount = len(rigs)
	uiLabels = [] 
	for rig in rigs:
		label = menuTitle;
		if (rigCount > 1):
			label = "%s (%s)" % (label, rig)
		annot = menuAnnot + rig
		theMenu = stereoCameraUILabel.UILabel( label=label,
											   annotation=annot,
											   command=stereoCameraRig.createStereoCameraRig,
											   command_keywords={'rigName':rig})
		uiLabels.append(theMenu)
	multiRigMgr = multiRig.NamingTemplateManager()
	
	for m in multiRigMgr.templates():
		label = m.rigName()
		annot = menuAnnot + label
		theMenu = stereoCameraUILabel.UILabel( label=label,
											   annotation=annot,
											   command=m.create,
											   command_pack=None )
		uiLabels.append(theMenu)
	return uiLabels
	
def buildCreateMenu( parent=None ):
	if parent:
		cmds.setParent( parent, menu=True )
		cmds.menu( parent, edit=True, deleteAllItems=True )
	uiLabels = gatherCreateMenuUILabels()
	for u in uiLabels:
		if u == stereoCameraUILabel.EmptyLabel:
			cmds.menuItem( divider=True )
		else: 
			cmds.menuItem( label=u.label(),
						   annotation=u.annotation(),
						   command=u.command() )

def populateStereoRenderMenu(parent):
	curParent = cmds.setParent( menu=True, query=True )
	rc = stereoCameraSettings.gStereoMenuRenderCreate

	rc.setCommand( buildCreateMenu )

	populateItems( parent, stereoCameraSettings.gStereoMenuRenderItems )

def createStereoCameraSetSubmenus(dirCmd):
    """
    Add menu items for all the stereo camera set.  A stereo camera set
	is one in which all camera passes point to stereo camera rigs.
	The passed dirCmd contains a mel command which sets a given
	director in the view.
    """
    cameraRigs = stereoCameraRig.listRigs()
    directors = cmds.ls( type='cameraSet' )
    dirCmd = "import maya.mel as mel\nmel.eval('"+dirCmd+"')"

    # Check each director to see if all camera passes point to rigs.
    # If so, add a menu item for it.
	#
    for director in directors:
        isStereo = True
        passCameras = cmds.listConnections( director, type="transform", destination=False )
        if passCameras != None:
            for pc in passCameras:
                if cameraRigs.count(pc) == 0:
                    isStereo = False
                    break
            if isStereo:
                cmds.menuItem(label=director, command=(dirCmd % {'arg1': director}))
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
