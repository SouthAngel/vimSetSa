import maya.cmds as cmds
import maya.mel as mel 
import os, sys, os.path, imp

from maya.app.stereo import stereoCameraErrors

"""
Modules provides a set of utility functions.
"""

def __call(language, method, rigName, kwords ={}, cmd_args=[]):
	"""Private method to call a MEL or Python callback. Return 'Error' in
	case of error. We avoid None, [], '' because those are more likely
	to be returned by the command we call"""
	errReturn = 'Error'
	
	if language == 'MEL':
		try:
			call_string = method
			for item in kwords.items():
				flag = ' -%s %s'
				if type(item[1]) == str:
					flag = ' -%s "%s"'
				call_string = call_string + flag % (str(item[0]), str(item[1]))
			for arg in cmd_args:
				argstr = ' "%s"'
				if type(arg) != str:
					argstr = ' %s'
				call_string = call_string + argstr % str(arg)
			return mel.eval(call_string)
		except:
			stereoCameraErrors.displayError('kRigCommandFailed', method, rigName)
			return errReturn
	elif language == 'Python':
		pair = method.rsplit('.', 1)
		if len(pair) < 2:
			# Happens if ther is no . in the method
			stereoCameraErrors.displayError('kRigCommandPython', method, rigName)
			return errReturn
		[moduleName, funcName] = pair

		path = ''
		pair = moduleName.rsplit('.', 1)
		if len(pair) > 1 :
			[path, moduleName] = pair
		if not sys.modules.has_key(moduleName):
			path = path.replace('.', '/')
			alteredPath = [sys.path[i]+'/'+path for i in range(len(sys.path))]
		   	try:
				desc = imp.find_module(moduleName, alteredPath)
				if desc:
					try:
						imp.load_module(moduleName, desc[0], desc[1], desc[2])
					finally:
						# Since we may exit via an exception, close fp
						desc[0].close()
			except:
				pass

		if sys.modules.has_key(moduleName):
			module = sys.modules[moduleName]
			funcPtr = module.__dict__[funcName]
			if kwords or cmd_args:
				return funcPtr( *cmd_args, **kwords )
			else:
				return funcPtr() 

		stereoCameraErrors.displayError('kMissingPythonCB', method, rigName)
		return errReturn

	stereoCameraErrors.displayError('kLanguageNotSupported', language, rigName)
	return errReturn

def performReloadChk( ):
	"""
	Scans the current module database and looks for any modules that we
	own.  If we find a module that we own, reload it in case any changes
	have been made. In terms of module reloading, this module cannot be
	reloaded because it would imply that the code is changing while it
	is being executed. If you change this module, you must invoke a
	reload in the python shell prior to calling this script. 
	"""

	# Our main assumption is that all of our scripts exist in the
	# same directory as stereoCameraInitStereo
	#
	stereoCameraPath = __file__
	directory = os.path.dirname( stereoCameraPath )
	contents = os.listdir( directory )
	for c in contents:
		if c.endswith( '.pyc' ) or c.endswith( '.py' ):
			module_name = c.split( '.' )[0]
			if sys.modules.has_key( module_name ) and module_name != __name__:
				# Found it ... reload the module, except in cases where
				# the name of the module is this module.
				#
				module = sys.modules[module_name]
				reload(module)

def loadPlugin():
	loaded = cmds.pluginInfo( "stereoCamera", query=True, loaded=True )
	if not loaded:
		cmds.loadPlugin( "stereoCamera" )

def unloadPlugin( *args ):
	loaded = cmds.pluginInfo( "stereoCamera", query=True, loaded=True )
	if loaded:
		cmds.unloadPlugin( "stereoCamera" )

def reloadScripts():
	runCallbackChecks()
	performReloadChk()

def runCallbackChecks( ):
	loaded = cmds.pluginInfo( "stereoCamera", query=True, loaded=True )
	if not loaded:
		stereoCameraErrors.displayError( 'kPluginNotLoaded' )
		return False

	return True 


# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
