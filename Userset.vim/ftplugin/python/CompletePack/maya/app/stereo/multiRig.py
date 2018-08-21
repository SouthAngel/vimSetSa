"""
Multi-rigs are the collection of stereo camera rigs contained by a camera set.
This class provides a generic way of defining a multi-rig and creating them.
A multi-rig has 2 parts:

    - Naming information
    - Layer information

Each layer has information on how to populate that layer. It includes

    - Prefix the name of the layer
	- The type of stereo camera
    - Whether an object set should be created for that layer. 
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.cmds as cmds
import copy

import maya.app.stereo.stereoCameraErrors as stereoCameraErrors
import maya.app.stereo.stereoCameraRig as stereoCameraRig
import maya.app.stereo.stereoCameraSets as stereoCameraSets
import maya.app.stereo.stereoCameraUtil as stereoCameraUtil
import maya.app.stereo.stereoCameraDefaultRig as defaultRigType

# Makes sure the plug-in is loaded.
#
def getDefaultRig(): 
	stereoCameraUtil.runCallbackChecks()
	return cmds.stereoRigManager( query=True, defaultRig=True  )

SwapRigsOptionVar = 'StereoCameraAlwaysSwapForDefault'
def swapDefault( oldDefault, newDefault ):
	global SwapRigsOptionVar 
	msg = maya.stringTable[ 'y_multiRig.kSwapDefaultMsg'  ]
	msg = msg % (oldDefault, newDefault)
	
	_btns = [ maya.stringTable[ 'y_multiRig.kSwapYes'  ],
			  maya.stringTable[ 'y_multiRig.kSwapNo'   ],
			  maya.stringTable[ 'y_multiRig.kSwapAlwaysYes'  ],
			  maya.stringTable[ 'y_multiRig.kSwapAlwaysNo'   ] ]

	ex = cmds.optionVar( exists=SwapRigsOptionVar )
	if ex:
		value = cmds.optionVar( query=SwapRigsOptionVar )
		if value == _btns[2]:
			return True
		if value == _btns[3]:
			return False
	if cmds.about(batch=True):
		return False
	
	result = cmds.confirmDialog( title=maya.stringTable['y_multiRig.kReplace' ],
								 message=msg,
								 button = _btns,
								 defaultButton='Yes',
								 cancelButton='No' )

	if ex: 
		cmds.optionVar( rm=SwapRigsOptionVar )
	cmds.optionVar( sv=[SwapRigsOptionVar,result] )
	if result == _btns[2] or result == _btns[0]:
		return True
	return False

def clearDefaultSwapOV( ):
	global SwapRigsOptionVar
	if cmds.optionVar( exists=SwapRigsOptionVar ):
		cmds.optionVar( rm=SwapRigsOptionVar )

class NamingTemplate:
	"""
	This class encapsulates the naming convension when creating new camera set
	multi rigs.   
	"""
	_DefaultLayerPreset = { 0: ["Near",  getDefaultRig, 1],
							1: ["Mid",   getDefaultRig, 1],
							2: ["Far",   getDefaultRig, 1],
					'default': ["Layer", getDefaultRig, 1]
							}
	
	def __init__( self, mgr, template = None ):
		"""
		Class initializer.  
		"""
		self._manager = mgr
		self._templateName = ''
		self._camSetPrefix = ''
		self._camSetPrefixLayer = []
		self._cameraSetType = 'cameraSet'
		
		if template: 
			self._templateName = template[0]
			self._camSetPrefix = template[1]
			self._setLayers( template[2] )
			if len(template) > 3:
				self._cameraSetType = template[3]


	def _resolveLayerAndAdd( self, layer ):
		layer_as_string = [layer[0], layer[1], layer[2]]
		if type(layer[1]) != str:
			layer_as_string[1] = layer[1]()
			
		self._camSetPrefixLayer.append(layer_as_string)
		
	def _setLayers( self, layers ):
		self._camSetPrefixLayer = [] 
		for l in layers:
			self._resolveLayerAndAdd( l )
		
	def gatherFromString( self, sval ):
		"""
		Takes a string previously packed using 'stringify' and restores
		the state to variables on this class. 
		"""
		theList = eval( sval )
		self._templateName = theList[0]
		self._camSetPrefix = theList[1]
		self._camSetPrefixLayer = theList[2]
		if len(theList) > 3:
			self._cameraSetType = theList[3]
		else:
			self._cameraSetType = 'cameraSet'

	def checkMultibyte( self ):
		import maya.mel as mel
		check_list = [self._templateName, self._camSetPrefix] + [x[0] for x in self._camSetPrefixLayer]
		for c in check_list:
			if mel.eval( 'containsMultibyte( "%s" )' % c ):
				stereoCameraErrors.displayError( 'kNoMultibyte', c )
				return 1
		return 0 
	
	def create( self, *args ):
		"""
		Create the Maya nodes per the specification of this template. 
		"""
		if self.checkMultibyte():
			return 

		rigs = cmds.stereoRigManager( listRigs=True )
		defaultCam = cmds.stereoRigManager( query=True, defaultRig=True )
		standardDefault = defaultRigType.rigTypeName
		
		swapWithDefault = False
		askedUserAlready = False
		for i in range(self.layers()):
			rtype = self.rigTypeForLayer( i )
			if rtype not in rigs:
				if rtype == standardDefault and defaultCam != standardDefault:
					# Check to make sure we haven't already asked the user
					# for this create call.  There are multiple layers
					# of a multi-rig and we don't want to ask the user
					# the same question multiple times.
					# 
					if not askedUserAlready: 
						swapWithDefault = swapDefault( standardDefault,
													   defaultCam )
						askedUserAlready = True
					if not swapWithDefault:
						stereoCameraErrors.displayError( 'kRigNotFound', rtype )
						return 
				else: 
					stereoCameraErrors.displayError( 'kRigNotFound', rtype )
					return

		camSet = None
		camSetType = self.cameraSetNodeType()
		val = cmds.objectType( tagFromType=camSetType )
		if val>0: 
			camSet = cmds.createNode( camSetType,
									  name=self._templateName )
		else:
			stereoCameraErrors.displayError('kCameraSetNotFound', camSetType)
			return 
		
		masterPrefix = self._camSetPrefix.replace( ' ', '_' )
		
		uniqueRigs = [] 
		for i in range(self.layers()):
			rtype = self.rigTypeForLayer( i )
			if rtype == standardDefault and swapWithDefault:
				rtype = defaultCam
				stereoCameraErrors.displayWarning( 'kDefaultRigSwap', rtype )
				
			if rtype not in uniqueRigs:
				uniqueRigs.append( rtype )
			layerPrefix = self.layerPrefixForLayer( i ).replace( ' ', '_' )
			prefix = masterPrefix + layerPrefix 
			autoCreateSet = self.autoCreateSet( i )
			rig = stereoCameraRig.createStereoCameraRig( rtype )
			objSet = None
			if autoCreateSet:
				objSet = cmds.createNode( 'objectSet', name=prefix + 'Set' )
			stereoCameraSets.addNewRigToSet( rig[0], camSet, objSet )
			baseName = rig[0]
			for r in rig:
				cmds.rename( r, r.replace( baseName, prefix ) )

		# Notify once to all unique rigs that we have finished
		# building the multi rig.
		# 
		for u in uniqueRigs:
			stereoCameraSets.notifyCameraSetCreateFinished( camSet, u )
						  
	def stringify( self ):
		"""
		Converts the data members of this class into a string format.
		This is so we can pack the data into a Maya optionVar 
		"""
		theList = [self._templateName, self._camSetPrefix,
				   self._camSetPrefixLayer, self._cameraSetType]
		return str(theList)

	def store( self ):
		"""
		Forces the storage of the changes the option var back into the
		optionVar. 
		"""
		self._manager.store()

	def rigName( self ):
		"""
		Returns the name of this multi rig. 
		"""
		return self._templateName
	
	def setRigName( self, name ):
		"""
		Sets the name for this multi-rig. 
		""" 
		self._templateName = name
		self.store()

	def camSetPrefix( self ):
		"""
		Returns the naming prefix to append to new cameras & sets.
		"""
		return self._camSetPrefix

	def setCamSetPrefix( self, camSetPre ):
		"""
		Sets the prefix name. 
		"""
		self._camSetPrefix = camSetPre
		self.store()

	def layers( self ):
		"""
		Returns the number of layers this template currently holds. 
		"""
		return len(self._camSetPrefixLayer)
	
	def layerPrefixForLayer( self, layer ):
		"""
		Query the value for the layer prefix using layer id.
		"""
		return self._camSetPrefixLayer[layer][0]

	def rigTypeForLayer( self, layer ):
		"""
		Query the name for the rigType for the specified layer.
		""" 
		return self._camSetPrefixLayer[layer][1]

	def autoCreateSet( self, layer ):
		"""
		Query the value for the auto create object set option by layer id.
		"""
		return self._camSetPrefixLayer[layer][2]

	def setLayerPrefix( self, prefix, layer ):
		"""
		Change the prefix value for the layer. 
		"""
		self._camSetPrefixLayer[layer][0] = prefix
		self.store()

	def setLayerCamera( self, camera, layer=0 ):
		"""
		Change the camera value for the specified layer. 
		"""
		self._camSetPrefixLayer[layer][1] = camera
		self.store()

	def setAutoCreateSet( self, create=1, layer=0 ):
		"""
		Set the auto create flag. 
		"""
		self._camSetPrefixLayer[layer][2] = create
		self.store()

	def setCameraSetNodeType( self, nodeType ):
		
		self._cameraSetType = nodeType
		self.store()
	
	def deleteLayer( self, layer=0 ):
		"""
		Remove the specified layer from this template. 
		"""
		del self._camSetPrefixLayer[layer]
		self.store()

	def cameraSetNodeType( self ):
		"""
		Return the node type for the camera set.  This information is used
		to create a new camera set. 
		"""
		return self._cameraSetType
	
	def addLayer( self ):
		"""
		Add a new layer to this object. 
		""" 
		next_val = len( self._camSetPrefixLayer )
		defaults = NamingTemplate._DefaultLayerPreset
		template = defaults['default']
		if defaults.has_key( next_val ):
			template = defaults[next_val]

		self._resolveLayerAndAdd(copy.deepcopy(template))
		self.store()

g3RigSetup = ( "Multi Stereo Rig",
			   "shot",
			   [["Near", getDefaultRig, 1],
				["Mid",  getDefaultRig, 1],
				["Far",  getDefaultRig, 1]] )
gDefaultTemplates = [g3RigSetup]

class NamingTemplateManager:
	"""
	This manages the list of naming templates used by the editor.  Users
	can create customized templates.  Any operation that changes a template:
	   - New
	   - Delete
	   - Modify

	Will force the storage of that changed value back into the optionVar
	Thus the optionVar is always in-sync with the manager.  It is possible
	to create more than one template manager; however, multiple instances
	may stomp over each other and provide un-predictable results.  
	"""
	_NamingOV = "CameraSetToolNamingTemplate"
	def __init__( self ):
		"""
		Class constructor.  Retreive the optionVar for the manager and read 
		the contents.  If the option var does not exist, we create it and
		populate the default values. 
		"""
		ex = cmds.optionVar( exists=NamingTemplateManager._NamingOV )
		self._namingTemplates = [] 
		if not ex:
			# This is the first time that the option var has been populated
			# we need to initialize with the default data.
			#
			self.resetToDefault() 
		else:
			self.retreive()

	def defaultTemplate( self ):
		"""
		Return the default template. 
		"""
		global gDefaultTemplates
		# Python tracks data using references.  To prevent from ever
		# overriding our default settings. We always make a copy of
		# the data.
		#
		tmpl = copy.deepcopy( gDefaultTemplates[0] )
		nt = NamingTemplate( self, tmpl )
		return nt

	def resetToDefault( self ):
		"""
		Reset to the default settings.
		"""
		self._namingTemplates = []
		global gDefaultTemplates
		for x in gDefaultTemplates:
			# Python references all data. To prevent from ever
			# overriding our default settings. We always make a copy
			# of the data.
			# 
			tmpl = copy.deepcopy(x)
			nt = NamingTemplate( self, tmpl )
			self._namingTemplates.append( nt )
		self.store()
		
	def retreive(self):
		"""
		Retreives the template information from the option var that
		contains this data. 
		"""
		self._namingTemplates = []
		thelist = cmds.optionVar( query=NamingTemplateManager._NamingOV )
		for t in thelist:
			nt = NamingTemplate( self )
			nt.gatherFromString( t )
			self._namingTemplates.append( nt )

	def deleteTemplate( self, template ):
		"""
		Remove the name template from the template manager.
		"""
		self._namingTemplates.remove( template )
		self.store()
		
	def addNew( self ):
		"""
		Create a new template from the default form. 
		"""
		df = self.defaultTemplate()
		self._namingTemplates.append( df )
		self.store()
		return df

	def store(self):
		"""
		Store the template information back onto the option var.
		"""
		cmds.optionVar( rm=NamingTemplateManager._NamingOV )
		for s in self._namingTemplates:
			cmds.optionVar( sva=[NamingTemplateManager._NamingOV, s.stringify()] )

	def templates( self ):
		"""
		Return the list of templates.
		"""
		return self._namingTemplates
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
