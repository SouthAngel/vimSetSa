"""
This is a dedicated editor for specifying camera set rigs.  It allows
the artist to preset a multi-rig type.  They can then use the
create menus for quickly creating complicated rigs.  
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.cmds as cmds
import maya.app.stereo.multiRig as multiRig 
import copy

class BaseUI:
	"""
	Each region of the editor UI is abstracted into a UI class that
	contains all of the widgets for that objects and relavant callbacks.
	This base class should not be instanced as this is only a container
	for common code.  
	"""
	def __init__( self, parent ):
		"""
		Class initialization. We simply hold onto the parent layout.
		"""
		self._parent = parent
		self._control = None

	def setControl( self, control ):
		"""
		Set the pointer to the control handle for this UI.  This is
		the main control that parents or children can reference 
		for UI updates.  
		"""
		self._control = control 

	def parent( self ):
		"""
		Return the parent instace of this UI. This can be None. 
		"""
		return self._parent
	
	def control( self ):
		"""
		Return the master control for this UI.  
		"""
		return self._control

class NamingTemplateUI( BaseUI ):
	"""
	This class encapsulates all of the UI around multi rig naming templates. 
	"""
	def __init__( self, parent, mgr, template ):
		"""
		Class initializer.  
		"""
		BaseUI.__init__(self, parent)
		self._manager = mgr
		self._template = template
		self._layerFrameUI = [] 

	def resetUI( self ):
		"""
		"""
		self._layerFrameUI = []
		
	def multiRigNameChanged( self, ui ):
		"""
		Called when the user changes the name of this multi-rig
		using the supplied text box. 
		"""
		templateName = cmds.textFieldGrp( self._templateCamSetField, 
										  query=True, text=True )
		self._template.setRigName( templateName )
		cmds.frameLayout(self._frameName,edit=True,label=templateName)

	def cameraSetNameChanged( self, arg ):
		nodeType = cmds.optionMenuGrp( self._cameraSetName, query=True, value=True )
		self._template.setCameraSetNodeType( nodeType )
		
	def namingPrefixChanged( self, arg ):
		"""
		Called when the users changes the prefix name used for the
		multi-rig. 
		"""
		camSetPrefix = cmds.textFieldGrp( self._camSetPrefix,
										  query=True, text=True )
		self._template.setCamSetPrefix( camSetPrefix )

	def layerPrefixChanged( self, args, layer=0 ):
		"""
		Called when the prefix changes for a layer. 
		"""
		self._template.setLayerPrefix( args[0], layer )

	def layerCameraChanged( self, args, layer=0 ):
		"""
		Called when the option menu group changes. 
		"""
		self._template.setLayerCamera( args[0], layer )

	def autoCreateCkboxChange( self, args, layer=0 ):
		"""
		Called when the check box is changed. 
		"""
		self._template.setAutoCreateSet( args[0], layer )
		
	def deleteLayer( self, args, layer=0 ):
		"""
		Called when the delete layer button is clicked.
		"""
		cmds.deleteUI( self._layerFrameUI[layer]['frame'] )
		del self._layerFrameUI[layer]
		self._template.deleteLayer( layer )
		layerL10N = maya.stringTable['y_cameraSetTool.kLayerId'  ] 
		for i in range(len(self._layerFrameUI)):
			numStr = ' %d' % i 
			cmds.frameLayout( self._layerFrameUI[i]['frame'], edit=True,
							  label=layerL10N + numStr )
			# The layer order has changed because we deleted a layer
			# We need to reset all callbacks.
			#
			self._setCallbacks( i )

	def _setCallbacks( self, layer ):
		"""
		Every layer object has a callback. If we delete a layer, we
		need to reset those callbacks because the layer order has
		changed. 
		"""
		ui = self._layerFrameUI[layer]
		callback = NamingTemplateUI._wrapCb(self.layerPrefixChanged, layer)
		cmds.textFieldGrp( ui['layerPrefix'],
						   edit=True, changeCommand=callback )
		callback = NamingTemplateUI._wrapCb(self.layerCameraChanged, layer )
		cmds.optionMenuGrp( ui['menuGrp'], edit=True, 
							changeCommand=callback )
		callback = NamingTemplateUI._wrapCb(self.autoCreateCkboxChange, layer)
		cmds.checkBox( ui['ckbox'], edit=True,
					   changeCommand=callback)
		callback = NamingTemplateUI._wrapCb(self.deleteLayer, layer)
		cmds.iconTextButton(ui['icon'], edit=True, 
							command=callback)
	
	@staticmethod
	def _wrapCb( function,layer ):
		"""
		Utility method to define a new function which calls the
		the layer. 
		"""
		def cbFunction( *args ):
			return function( args, layer=layer )
		return cbFunction

	def addLayer( self, *args ):
		"""
		Add a new layer to this object. 
		""" 
		curParent =cmds.setParent(query=True)
		cmds.setParent(self._layerParent)
		self._template.addLayer()
		next_val = self._template.layers()-1
		self.layoutForLayer( next_val )
		cmds.setParent(curParent)

	def createIt( self, *args ):
		"""
		Function called when the user clicks the 'Create' button.
		This will force the creation of a new rig.
		"""
		self._template.create()

	def removeDef( self, *args ):
		"""
		Remove this object from the list. 
		"""
		self._manager.deleteTemplate( self._template )
		self.parent().rebuild()
		
	def layoutForLayer( self, layer ):
		"""
		Build the UI for the specified layer. We need to access the
		UI data later in callbacks. So we store the data inside
		a dictionary for reference layer. 
		"""
		ui = {}
		#frlt = cmds.frameLayout( collapsable=True, borderStyle="out", label="Layer %d" % layer )
		locLayer = maya.stringTable['y_cameraSetTool.kLayerNumberString' ]
		frlt = cmds.frameLayout( collapsable=True, label= locLayer + " %d" % layer )
		ui['frame'] = frlt
		self._layerFrameUI.append(ui)

		cmds.columnLayout( adjustableColumn=True )
		ui['layerPrefix'] = cmds.textFieldGrp( label=maya.stringTable['y_cameraSetTool.kLabelPrefix'],
											   text=self._template.layerPrefixForLayer(layer))
		ui['menuGrp'] = cmds.optionMenuGrp( label=maya.stringTable['y_cameraSetTool.kRigType'] )
		opValue = rigTypeLayer = self._template.rigTypeForLayer( layer )
		rigs = cmds.stereoRigManager( listRigs=True )
		for r in rigs:
			cmds.menuItem( label=r )
		if not opValue in rigs:
			cmds.menuItem( label=opValue )
			
		cmds.optionMenuGrp( ui['menuGrp'], edit=True, value=opValue )

		# For some reason, the only way I can get the check box to line
		# up is if I embed it in a form layout.
		#
		form = cmds.formLayout()
		ui['ckbox'] = cmds.checkBox( label=maya.stringTable['y_cameraSetTool.kAutoCreate' ] )
		ui['icon'] = cmds.iconTextButton(style="iconOnly",
										 image="removeRenderable.png",
										 annotation=maya.stringTable['y_cameraSetTool.kDelete' ],
										 width=20, height=20)
		cmds.checkBox( ui['ckbox'], edit=True,
					   value=self._template.autoCreateSet( layer ) )
		cmds.formLayout( form, edit=True,
						 attachForm=[(ui['ckbox'], "left", 125),
									 (ui['ckbox'], "top", 0),
									 (ui['ckbox'], "bottom", 0),
									 (ui['icon'],  "top", 0),
									 (ui['icon'],  "bottom",0),
									 (ui['icon'],  "right",5)],
						 attachNone=[(ui['ckbox'],"right"),
									 (ui['icon'], "left")] )
		self._setCallbacks( layer )
		cmds.setParent('..')
		cmds.setParent('..')
		cmds.setParent('..')

	def buildLayout( self ):
		"""
		Build a new multi-rig template UI. 
		"""
		curParent = cmds.setParent( query=True )

		self._frameName = cmds.frameLayout( collapsable=True,
											label=self._template.rigName() )

		self.setControl( self._frameName )
		cmds.columnLayout( adjustableColumn=True )

		labelL10N = maya.stringTable[ 'y_cameraSetTool.kMultiRigName'  ]
		self._templateCamSetField = cmds.textFieldGrp( label=labelL10N,
													   text=self._template.rigName(),
													   changeCommand=self.multiRigNameChanged )
		labelL10N = maya.stringTable[ 'y_cameraSetTool.kMultiRigPrefix'  ]
		self._camSetPrefix = cmds.textFieldGrp( label=labelL10N,
												text=self._template.camSetPrefix(),
												changeCommand=self.namingPrefixChanged )

		camSetTemplate = self._template.cameraSetNodeType()
		availCameraSets = ['cameraSet']
		camSet = cmds.pluginInfo( query=True,
								  dependNodeByType='kCameraSetNode' )
		if camSet and len(camSet):
			availCameraSets = availCameraSets + camSet
		if camSetTemplate not in availCameraSets:
			availCameraSets = availCameraSets + [camSetTemplate]
			
		if len(availCameraSets) > 1: 
			labelL10N = maya.stringTable[ 'y_cameraSetTool.kCameraSetNodeType'  ]
			self._cameraSetName = cmds.optionMenuGrp( label=labelL10N )
			for c in availCameraSets:
				cmds.menuItem( label=c )

			callback = self.cameraSetNameChanged
			cmds.optionMenuGrp( self._cameraSetName, edit=True, 
								changeCommand=callback )
			cmds.optionMenuGrp( self._cameraSetName, edit=True,
								value=camSetTemplate )

		cmds.scrollLayout( childResizable=True,
						   minChildWidth=200 )
		self._layerParent = cmds.columnLayout( adjustableColumn=True )
		# Build the layout for each of the layers.
		# 
		for i in range( self._template.layers() ):
			self.layoutForLayer( i )
		cmds.setParent('..')
		cmds.setParent('..')
		form = cmds.formLayout()
		b1 = cmds.button( label=maya.stringTable['y_cameraSetTool.kCreateIt' ],
						  command=self.createIt )
		b2 = cmds.button( label=maya.stringTable['y_cameraSetTool.kRemoveIt' ],
						  command=self.removeDef )
		b3 = cmds.button( label=maya.stringTable['y_cameraSetTool.kAddIt' ],
						  command=self.addLayer)
		attachForm = [(b1, "top", 0),
					  (b1, "bottom", 0),
					  (b1, "left", 0),
					  (b2, "top", 0),
					  (b2, "bottom", 0),
					  (b3, "right", 0),
					  (b3, "top", 0),
					  (b3, "bottom", 0)]
		attachControl = [(b2, "right", 5, b3)]
		attachNone= [(b1,"right"),
					 (b3,"left")]
		cmds.formLayout( form, edit=True, attachForm=attachForm,
						 attachNone=attachNone, attachControl=attachControl)

		cmds.setParent(curParent)

class NewCameraSetUI( BaseUI ):
	"""
	UI for adding 'new' camera set.  
	"""
	def __init__( self, parent ):
		"""
		Class constructor
		"""
		BaseUI.__init__( self, parent)
		self._templateMgr = multiRig.NamingTemplateManager()
		self._columnLayout = ''
		self._uiTemplates = [] 
		
	def name( self ):
		"""
		Name of this UI component. 
		"""
		return 'New'

	def resetUI( self ):
		"""
		Tells all ui templates to reset their ui handles.  This
		is done because this UI templates hold onto some
		local data that must be cleared out before rebuilding 
		"""
		for x in self._uiTemplates:
			x.resetUI()
	
	def rebuild( self ):
		"""
		Rebuild the UI.  We find the parent class and tell it
		to kickstart the rebuild. 
		"""
		self.resetUI()
		self.parent().rebuild()
	
	def newTemplate( self, *args ):
		"""
		Create a new template and adding the template to the
		UI layout for user manipulation. 
		"""
		tmpl = self._templateMgr.addNew()
		self.rebuild()

	def saveSettings( self, *args ):
		"""
		Call the template manager to store its current settings
		"""
		self._templateMgr.store()

	def resetSettings( self, *args ):
		"""
		Reset to the default settings and rebuild the UI. 
		"""
		self._templateMgr.resetToDefault()
		multiRig.clearDefaultSwapOV() 
		self.rebuild()
		
	def buildLayout( self ):
		"""
		Construct the UI for this class.
		"""
		self.setControl( cmds.scrollLayout( childResizable=True,
											minChildWidth=200 ) )
		cmds.columnLayout( adjustableColumn=True )
		self._uiTemplates = [] 
		for t in self._templateMgr.templates():
			ui = NamingTemplateUI( self, self._templateMgr, t )
			ui.buildLayout()
			self._uiTemplates.append( ui )
		cmds.setParent('..')
		cmds.setParent('..')
		return self._control

# We use a global variable to track the current open instance of the
# camera set editor. If it is already opened then the existing window
# is shown instead of creating a new instance.
#
gEditorWindowInstance = None

class CameraSetEditor( BaseUI ):
	"""
	Main class for the camera set editor. 
	"""
	_EditorName = maya.stringTable['y_cameraSetTool.kEditorName' ]
	def __init__(self, parent=None ):
		"""
		Class constructor. 
		"""
		BaseUI.__init__( self, None )
		self._win = None
		self._newUI = None
		self._job = 0 

	def name( self ):
		"""
		Return the name for this editor.
		"""
		return CameraSetEditor._EditorName

	def buildLayout( self ):
		"""
		Build the main layout for the class. This will kickstart all
		UI creation for the class. You should have a window instance
		created for the layouts to parent under.  
		"""
		form = cmds.formLayout()
		layout = self._newUI.buildLayout()
		button = cmds.button( label= maya.stringTable['y_cameraSetTool.kEditorNew' ], command=self._newUI.newTemplate )
		attForm = [
				   (layout, 'top', 0),
				   (layout, 'right', 0),
				   (layout, 'left', 0),
				   (button, 'bottom', 0),
				   (button, 'left', 0),
				   (button, 'right', 0)
				   ]
		attNone = [(button, 'top')]
		attControl = [(layout,'bottom',5,button)]
		cmds.formLayout( form, edit=True,
						 attachForm=attForm, attachNone=attNone,
						 attachControl=attControl
						 )
		# We use a base class to store the main control. This
		# is so other classes can access the parent layouts
		# 
		self.setControl( form )
		return form

	def rebuild( self ):
		"""
		Force the rebuild of the UI. This happens when
		users create new templates.  
		"""
		cmds.deleteUI( self.control() )
		curParent = cmds.setParent( query=True )
		cmds.setParent( self._win )
		self.buildLayout()
		cmds.setParent( curParent )

	def _deleteCallback( self, *args ):
		"""
		Called when the UI is about to be deleted.
		"""
		self._newUI = None
		self._win = None
		self._job = 0
		global gEditorWindowInstance
		gEditorWindowInstance = None
	
	def create( self ):
		"""
		Create a new instance of the window. If there is already a instance
		then show it instead of creating a new instance. 
		"""
		global gEditorWindowInstance
		if gEditorWindowInstance :
			cmds.showWindow( gEditorWindowInstance._win )
			self._win = gEditorWindowInstance._win
			self._newUI = gEditorWindowInstance._newUI
			return
	
		self._newUI = NewCameraSetUI(self)
		self._win = cmds.window( menuBar=True,
								 title=CameraSetEditor._EditorName )
		gEditorWindowInstance = self
		cmds.menu( label=maya.stringTable['y_cameraSetTool.kEditMenu' ] )
		cmds.menuItem( label=maya.stringTable['y_cameraSetTool.kSaveSettings' ],
					   command=self._newUI.saveSettings )
		cmds.menuItem( label=maya.stringTable['y_cameraSetTool.kResetSettings' ],
					   command=self._newUI.resetSettings )
		cmds.menu( label=maya.stringTable['y_cameraSetTool.kHelpMenu' ] )
		cmds.menuItem( label=maya.stringTable['y_cameraSetTool.kHelpOnMultiRig' ], 
						command='import maya.cmds as cmds\ncmds.showHelp("MultiRigCreateHelp")')
		self.buildLayout()
		self._job = cmds.scriptJob( runOnce=True,
									uiDeleted=[self._win, self._deleteCallback] )
		cmds.showWindow()
			
def createIt():
	"""
	Create a new window instance of the Camera Set Editor. 
	"""
	editor = CameraSetEditor()
	editor.create()
	return editor
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
