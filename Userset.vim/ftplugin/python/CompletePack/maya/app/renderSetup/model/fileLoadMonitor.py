""" File Loading Monitoring module.

    This module monitors file loads (including imports and reference load) and 
	displays warning messages if it discovers that new loaded files are not 
	compatible with the current renderSetup mode
	
	Implementation details:
	In order to determine if the loaded file is compatible with the current Maya state
	we first determine the type the loaded file based on its content. Then depending 
	on the current Maya RenderSetup mode error messages are displayed if incompatibilities
	are identified
	
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMaya as OpenMaya
import maya.app.renderSetup.model.renderSetup as renderSetup
import maya.app.renderSetup.model.legacyRenderLayer as legacyRenderLayer

# Module variables
beforeCallback = None	# Handle for the callback invoked at the beginning of a file load
afterCallback = None	# Handle for the callback invoken at the end of a file load operation

# List all error messages														  
kErrorSwitchToRenderLayer = maya.stringTable['y_fileLoadMonitor.kErrorSwitchToRenderLayer' ]
kErrorSwitchToRenderSetup = maya.stringTable['y_fileLoadMonitor.kErrorSwitchToRenderSetup' ]
kWarningInactiveRenderSetup = maya.stringTable['y_fileLoadMonitor.kWarningInactiveRenderSetup' ]
kErrorCombiningLegacyToNew = maya.stringTable['y_fileLoadMonitor.kErrorCombiningLegacyToNew' ]
kErrorCombiningNewToLegacy = maya.stringTable['y_fileLoadMonitor.kErrorCombiningNewToLegacy' ]


def _getErrorSwitchToRenderLayerIfNeeded():
	# If we have a render layer manager with render layers (not connected to render setup layers)
	# in the scene, then return an error warning the user that the combination of render setup and 
	# legacy render layers is not supported.
	renderLayerManagers = cmds.ls(type="renderLayerManager")
	for renderLayerManager in renderLayerManagers:
		size = cmds.getAttr(renderLayerManager + ".renderLayerId", size=True)
		allRenderLayers = (cmds.listConnections(renderLayerManager + ".renderLayerId[" + str(i) + "]")[0] for i in range(0, size))
		numRenderLayers = len([rsl for rsl in (legacyRenderLayer.renderSetupLayer(rl) for rl in allRenderLayers) if rsl is None])

		# It's ok to import or reference a file that has a render layer manager and one
		# legacy render layer (the default one). If the number of legacy render layers that
		# aren't used for render setup is greater than one, we have an intentional use of
		# legacy render layers and we should flag it.
		if numRenderLayers > 1:
			return kErrorSwitchToRenderLayer
	return None

def initialize():
	# This method must be called when the plugin is loaded
	# It registers listening callback for file load activities

	# Written to global variables
	global beforeCallback
	global afterCallback

	# Register file load callbacks
	beforeCallback = OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kBeforeFileRead, onReadStart )
	afterCallback = OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kAfterFileRead, onReadEnd )

	# Handle the case where the plugin gets loaded during a file load operation
	# This happens if the plugin is not loaded and the loaded file contains renderSetup nodes
	if OpenMaya.MFileIO.isReadingFile():
		# Required plugins are loaded at the beginning of the file load before any node
		# gets created. It is safe to do a pre-load inventory at this stage
		preLoadInventory()

def finalize():
	# This method must be called when the plugin is unloaded

	# Unregistering callbacks
	OpenMaya.MSceneMessage.removeCallback(beforeCallback)
	OpenMaya.MSceneMessage.removeCallback(afterCallback)

def getLayerInventory():
	# Utility method that returns the actual count of renderSetupLayer, 
	# renderLayer, and applyOverride nodes.
	renderLayerCount   = len( cmds.ls( type="renderLayer" ) )
	renderSetupCount   = len( cmds.ls( type="renderSetupLayer" ) )
	applyOverrideCount = len( cmds.ls( type="applyOverride" ) )
	
	return renderSetupCount, renderLayerCount, applyOverrideCount

def preLoadInventory():
	# Invoked at the beginning of a file load, it identifies the renderSetupLayers 
	# and RenderLayers that may be already present into the scene
	global initialRenderLayerCount
	global initialRenderSetupCount
	global initialApplyOverrideCount

	initialRenderSetupCount, initialRenderLayerCount, initialApplyOverrideCount = getLayerInventory()


def onReadStart( data ):
	# File load callback
	# Invoked when a file load is initiated but also on Import and Reference Load
	preLoadInventory()


def onReadEnd( data ):
	# File loaded callback
	# Invoked at the end of a load, import or reference load
	# This callback validates if the content of the  loaded file is compatible with
	# current Maya RenderSetup mode.

	# Determine if the newly loaded file is a renderSetup or Render Layer type file
	# based on the content of the newly loaded file
	
	# The presence of certain types of nodes is determined by making the difference 
	# between the actual count of a specific type of nodes and the count we had at the 
	# beginning of the file load operation
	
	renderSetupCount, renderLayerCount, applyOverrideCount = getLayerInventory()

	isRSfile = False  # true if the loaded file is a renderSetup file
	isRLfile = False  # true if the loaded file is a legacy render layer file
	hasAppliedOverrides = False # true if the loaded file is a renderSetup file with applied overrides.

	if renderSetupCount - initialRenderSetupCount > 0:
		# If the file contains renderSetupLayers it is a renderSetup file
		isRSfile = True
		hasAppliedOverrides = ((applyOverrideCount - initialApplyOverrideCount) > 0)
	elif renderLayerCount - initialRenderLayerCount > 1: 
		# If the file contains renderLayers but no renderSetupLayers it is a renderLayer file
		# A difference of 1 layer does not qualify a file as being a renderLayerFile. That 
		# difference represent the defaultRenderLayer. There are 2 reasons why the difference count
		# would be 1: 
		#   - on file load the defaultRenderLayer has not been created yet when we did the preLoad inventory
		#	  so initialRenderLayerCount will be 0 but the defaultRenderLayer of the newly loaded file
		#     got loaded and created at the time the final LayerInventory was done
		#	- on file import, the initialRenderLayerCount is 1 but the import involves the load of a 
		#	  second defaultRenderLayer. That last layer gets removed at the end of the load but not 
		#     before the current callback gets invoked
		# This behavior seems subject to change so it should be one of the first thing to check if 
		# the associated regression test starts failing
		isRLfile = True

	# Determine if current operation is a clean file load in an empty scene
	# or an addition to a main scene (import or reference load)
	isNewScene = not OpenMaya.MFileIO.isImportingFile() and not OpenMaya.MFileIO.isReferencingFile()

	# Allows batch rendering of legacy render layer and render setup files 
	# regardless of whether we are in render setup or legacy render layer
	# mode.  Only valid on file open, not on file import or load of 
	# deferred file reference: loading deferred references should not
	# affect the main file mode.  If we were in render setup mode, we
	# should stay in render setup mode, and vice versa for legacy render
	# layer mode.
	if cmds.about(batch=True) and isNewScene:
		maya.mel.eval('global int $renderSetupEnableCurrentSession; $renderSetupEnableCurrentSession=' + ('0' if isRLfile else '1'))
        		
	# Early exit if the new file contains no RenderLayer or RenderSetups
	if not isRSfile and not isRLfile:
		return

	# Identify the message to output, if any
	errorMsg = None
	warningMsg = None

	if mel.eval( "mayaHasRenderSetup()" ) > 0:
		
		# Render Setup Mode
		if isRLfile:
			if initialRenderSetupCount > 0:
				# Appending to a scene already containing renderSetupLayers, disabling Maya RenderSetup mode is not a solution
				errorMsg = kErrorCombiningLegacyToNew
			else:
				errorMsg = _getErrorSwitchToRenderLayerIfNeeded()

		elif isRSfile and not isNewScene and hasAppliedOverrides:
			# Error: import or reference of render setup file 
			# detected apply override nodes.  Tell the user to 
			# switch to master layer in the file before importing
			# or referencing.
			errorMsg = kWarningInactiveRenderSetup 

	else:
		# RenderLayer mode
		if isRSfile:
			if initialRenderLayerCount > 1:
				# Appending to a scene already containing RenderLayers, enabling Maya RenderSetup mode is not a solution 
				# Again we allow a count of 1 because of the defaultRenderLayer
				errorMsg = kErrorCombiningNewToLegacy
			else:			
				errorMsg = kErrorSwitchToRenderSetup


	# Print out identified Error or Warning message
	if errorMsg:
		OpenMaya.MGlobal.displayError( errorMsg )

		# Force the display of the Maya File Load pop-up at the end of the read operation
		OpenMaya.MFileIO.setError()

	elif warningMsg:
		OpenMaya.MGlobal.displayWarning( warningMsg )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
