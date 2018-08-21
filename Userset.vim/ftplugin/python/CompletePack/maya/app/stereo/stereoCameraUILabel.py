import os
import os.path
import string
import maya.cmds as cmds 

"""
This module provides a UILabel class that can contain a description
of a UI entity as used by the stereo viewer code.  This UI entity
can be shared by multiple UI components. For example, you can define
a list of buttons that are also used as menu items.
"""

def pack_cmd( command, command_args, command_keywords ):
	"""
	Packs the python command into a string command that can be
	executed by Maya.  Keywords argument is currently not implemented
	and is a placeholder for future code.
	"""
	modName = command.__module__
	funcName = command.__name__
	cmdStr = 'import %s\n%s.%s(' % (modName, modName, funcName)
	if command_args:
		arg_list = []
		for ca in command_args:
			arg_list.append( '"%s"' % ca )
		cmdStr = cmdStr + string.join( arg_list, ',' )
	cmdStr = cmdStr + ')'
	return cmdStr 

def pack_load( command, command_args, command_keywords ):
	"""
	Identical to pack_cmd but it insures the plug-in is loaded before
	calling the command.
	"""
	
	gLoadPlugin = """\
import maya.cmds as cmds
import maya.mel as mel
def stereoCameraLoadPlugin( pname ):
	if not cmds.pluginInfo( pname, query=True, loaded=True ):
		try:
			cmds.loadPlugin( pname )
			return True
		except:
			try:
				mel.eval( 'error "Unable to load stereoCamera. Please ensure it is in your plugin path";' % (pname) )
			except:
				pass
	else:
		return True
	return False

"""
	pname = 'stereoCamera' 
	try: 
		pname = cmds.pluginInfo( pname, query=True, path=True )
	except RuntimeError:
		pname = 'stereoCamera' 

	exec_cmd = None
	if command: 
		cmd = pack_cmd( command, command_args, command_keywords )
		substr = cmd.split( '\n' )
		exec_cmd = "if stereoCameraLoadPlugin('%s'):" % pname
		exec_cmd = gLoadPlugin + exec_cmd + "\n\t" + string.join( substr, '\n\t' )
	else:
		exec_cmd = "stereoCameraLoadPlugin('%s')\n" % pname
		exec_cmd = gLoadPlugin + exec_cmd 
		
	return exec_cmd 

class UILabel:
	"""
	Wrapper class around UI labels and buttons. It allows us to define
	a piece of UI once and use it across multiple UI elements. 
	"""
	def __init__( self, label=None, annotation=None, image=None, command=None, command_pack=pack_cmd, command_args=[], command_keywords={}, option_box=False, check_box="", disabled=False, radio_cb=[], enable_cb=[], divider_label=None ):
				  
		self._image = image
		self._label = label
		self._annotation = annotation
		self._command = command
		self._command_args = command_args
		self._command_keywords = command_keywords
		self._command_pack = command_pack
		self._option_box = option_box
		self._check_box = check_box
		self._disabled = disabled
		self._radio = radio_cb
		self._enable_cb = enable_cb 
		self._divider_label = divider_label

	def enabled( self ):
		"""
		Returns true if the UI should be created enabled. If a enable_cb
		is defined then execute the callback to determine if we should
		enable or disable the UI. 
		"""
		if self._disabled:
			return False 
		
		if self._enable_cb != []:
			func = self._enable_cb[0]
			args = self._enable_cb[1:] + self._command_args
			return func( *args )
		return True 

	def radioGrpItem( self ):
		"""
		Returns true if this ui label support check box menu item.
		""" 
		return (self._radio != [])

	def radioItemOn( self ):
		"""
		If a check box callback has been added to this UI entry. Call that
		callback to determine if the item should be checked.
		"""
		if self._radio:
			func = self._radio[0]
			args = self._radio[1:] + self._command_args
			return func( *args )
		return False
	
	def option_box( self ):
		return self._option_box
		
	def check_box( self ):
		return self._check_box
	
	def label(self):
		return self._label

	def setCommand(self, command ):
		self._command = command
		
	def setArgs(self, args):
		self._command_args = args
		
	def annotation(self):
		return self._annotation

	def type(self):
		return UILabel
	
	def command(self):
		if self._command_pack:
			cmd_str = self._command_pack( self._command,
										  self._command_args,
										  self._command_keywords )
			return cmd_str
		else:
			return self._command

	def command_option( self ):
		if self._command_pack: 
			cmd_str = self._command_pack( self._command,
										  self._command_args + [True],
										  self._command_keywords )
			return cmd_str
		else:
			return self._command
	
	def image(self):
		return self._image

	def divider_label( self ):
		return self._divider_label

class UILabelGroup( UILabel ):
	def __init__( self, label, items, radioGroup=False ):
		UILabel.__init__( self, label=label )
		self._items = items
		self._postMenuCmd = None

		self._radioGrp = radioGroup

	def radioGroup( self ):
		return self._radioGrp
	
	def type(self):
		return UILabelGroup

	def postMenuCommand( self ):
		if self._command: 
			return True
		else:
			return False
		
	def setArgs( self, args ):
		UILabel.setArgs( self, args )
		for i in self._items:
			i.setArgs( args )
	
	def items(self):
		return self._items

EmptyLabel = UILabel()
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
