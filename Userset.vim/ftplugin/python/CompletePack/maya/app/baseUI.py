import maya
maya.utils.loadStringResourcesForModule(__name__)


import os
import maya.cmds as cmds

class StandardInput:
	"""
	Implements a basic user interface for Python sys.stdin
	
	When a Python call tries to read from sys.stdin in Maya's interactive GUI
	mode, then this object will receive the read call and present the user
	with a basic modal UI that will let them respond to the request for input
	"""
	def readline( self ):
		"""
		Read a line of input.  This will prompt the user for a single line of
		input
		"""
		if 'MAYA_IGNORE_DIALOGS' in os.environ:
			return '\n'
		else:
			return self.__promptUser( False )
		
	def read( self ):
		"""
		Read a line of input.  This will prompt the user for multiple 
		lines of input
		"""
		return self.__promptUser( True )
	
	def __promptUser( self, multiLine ):
		okStr = maya.stringTable['y_baseUI.kOK']
		result = cmds.promptDialog( title=maya.stringTable['y_baseUI.kStdinTitle'], 
								  	message=maya.stringTable['y_baseUI.kStdinMessage'],
								  	text='', scrollableField=True,
								  	button=okStr, defaultButton=okStr,
								  	dismissString=maya.stringTable['y_baseUI.kCancel'] )
		if okStr == result:
			return cmds.promptDialog( query=True, text=True )
		else:
			return '\n'


# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
