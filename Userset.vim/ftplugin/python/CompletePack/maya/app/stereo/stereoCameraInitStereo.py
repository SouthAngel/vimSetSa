# 
# Description:
#  This is the main entry point for initialization of stereo code.  This script
#  called on plug-in load and can be called from a userSetup.mel script.
#

import maya.cmds as cmds 

from maya.app.stereo import stereoCameraErrors
from maya.app.stereo import stereoCameraUtil
from maya.app.stereo import stereoCameraCustomPanel
from maya.app.stereo import stereoCameraRig
		
def init( ):
	"""
	Basic setup of the stereo tool. This will register a new icons in the
	shelf toolbar and add menu items to the main menu bar.  It will also
	verify that the plug-in is loaded.
	"""

	# Check for reload ... Since python modules always remain in memory
	# we need to make sure that none of our modules should be reloaded
	#
	#stereoCameraUtil.performReloadChk( )
	
	stereoCameraCustomPanel.initialize()

def remove( ):
	"""
	Removes the tool from the running maya session.
	"""
	stereoCameraCustomPanel.uninitialize()	
	
	return 1 
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
