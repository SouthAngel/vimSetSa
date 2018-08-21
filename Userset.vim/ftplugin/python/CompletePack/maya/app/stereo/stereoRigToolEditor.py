import maya
maya.utils.loadStringResourcesForModule(__name__)

import maya.cmds as cmds
import maya.mel as mel
from maya.app.stereo import stereoCameraErrors

def __buildCB(layout, func, control, param):
	return ('from maya.app.stereo import stereoRigToolEditor\n'+
			('stereoRigToolEditor.%(f)s("%(lay)s", "%(c)s", "%(p)s")' %
			 {'lay': str(layout),
			  'f': str(func),
			  'c': str(control),
			  'p': str(param)}))

def __buildCB2(layout, func, name, lang, create, cameraSet):
	return ('from maya.app.stereo import stereoRigToolEditor\n'+
			('stereoRigToolEditor.%(f)s("%(lay)s", "%(n)s", "%(l)s", "%(c)s", "%(cs)s")' %
			 {'lay': str(layout),
			  'f': str(func),
			  'n': str(name),
			  'c': str(create),
			  'cs': str(cameraSet),
			  'l': str(lang)}))

def __add(layout, nameBox, langMenu, createBox, createCamSet):
	name = cmds.textField(nameBox, query=True, text=True)
	lang = cmds.optionMenu(langMenu, query=True, value=True)
	create = cmds.textField(createBox, query=True, text=True)
	camSet = cmds.textField(createCamSet, query=True, text=True)
	
	# Multibyte string is not allowed for node name
	if mel.eval( u'containsMultibyte \"%s\"' % name ) == 1:
		stereoCameraErrors.displayError('kRigToolMultiByteName', arg1=name)
		return 
	if name == '':
		stereoCameraErrors.displayError('kRigToolNoName')
	elif create == '':
		stereoCameraErrors.displayError('kRigToolNoCreate')
	elif name in cmds.stereoRigManager(listRigs=True):
		stereoCameraErrors.displayError('kRigToolAlreadyExists', arg1=name)
	else:
		cmds.stereoRigManager(add=[name, lang, create])
		cmds.stereoRigManager(cameraSetFunc=[name,camSet])
		rebuildUI(layout)
	
def __delete(layout, control, rig):
	cmds.stereoRigManager(delete=rig)
	rebuildUI(layout)

def __changeLang(layout, control, rig):
	lang = cmds.optionMenu(control, query=True, value=True)
	cmds.stereoRigManager(language=[rig,lang])

def __changeCameraSetProcedure( layout, control, rig ):
	cb = cmds.textField(control, query=True, text=True)
	cmds.stereoRigManager(cameraSetFunc=[rig,cb])
						  
def __changeProcedure(layout, control, rig):
	create = cmds.textField(control, query=True, text=True)
	cmds.stereoRigManager(creationProcedure=[rig,create])

def __oneItem(layout, rig, definition, mode):
	"Build the UI for one rig"
	
	cmds.rowColumnLayout(numberOfColumns=2,
						 columnSpacing=[2,10],
						 columnWidth=[[1,150],[2,300]])
	# Tool name label and text
	#----------------------------------------------------------------------
	if mode == 'maya':
		name = cmds.text(label=maya.stringTable['y_stereoRigToolEditor.kReadOnly' ], align='right')
	else:
		cmds.text(label=maya.stringTable['y_stereoRigToolEditor.kRigToolName' ], align='right')
	if rig == None:
		name = cmds.textField()
	else:
		name = cmds.text(label=rig, font='boldLabelFont')
		
	# Language label, delete icon and text
	#----------------------------------------------------------------------
	cmds.text(label=maya.stringTable['y_stereoRigToolEditor.kRigLanguage' ], align='right')
	if mode == 'custom':
		cmds.rowLayout(numberOfColumns=2, columnWidth2=[270,30])
	menu = cmds.optionMenu()
	# Those are keywords and should not be translated
	cmds.menuItem( label="Python" )
	cmds.menuItem( label="MEL" )

	if mode == 'custom':
		icon = cmds.iconTextButton(style="iconOnly",
				image="removeRenderable.png",
				annotation=maya.stringTable['y_stereoRigToolEditor.kDelete' ],
				width=20, height=20)
		cmds.iconTextButton(icon, edit=True,
							command=__buildCB(layout, '__delete', icon, rig))
		cmds.setParent('..')

	# Create procedure label and text
	#----------------------------------------------------------------------	
	cmds.text(label=maya.stringTable['y_stereoRigToolEditor.kRigCreate' ], align='right')
	text = cmds.textField(text=definition[1])
	cmds.text(label=maya.stringTable['y_stereoRigToolEditor.kCameraSetCb' ], align='right')
	text2 = cmds.textField(text=definition[2])
	cmds.setParent('..')
	
	return [name, menu, text, text2]

def buildMainToolUI():
	"Build the UI for this window"
	
	layout = cmds.columnLayout()

	cmds.frameLayout(label=maya.stringTable['y_stereoRigToolEditor.kEdit' ])
	cmds.columnLayout()
	cmds.separator(height=5, style='none')
	
	mode = 'maya'
   	rigTools = cmds.stereoRigManager(listRigs=True)
	for rig in rigTools:
		definition = cmds.stereoRigManager(rigDefinition=rig)
		print definition
		[name, menu, text, text2] = __oneItem(layout, rig, definition, mode)
		
		if mode == 'maya':
			cmds.textField(text, edit=True, enable=False)
			cmds.textField(text2, edit=True, enable=False)
			cmds.optionMenu(menu, edit=True, enable=False, value=definition[0])
		else:
			cmds.textField(text, edit=True,
						   changeCommand=__buildCB(layout, '__changeProcedure', text, rig))
			cmds.textField(text2, edit=True,
						   changeCommand=__buildCB(layout, '__changeCameraSetProcedure', text2, rig))
		
			cmds.optionMenu(menu, edit=True, value=definition[0],
							changeCommand=__buildCB(layout, '__changeLang', menu, rig))

		cmds.separator(height=5, style='none')
		cmds.separator(width=460)
		cmds.separator(height=5, style='none')
		mode = 'custom'

	cmds.setParent( '..' )
	cmds.setParent( '..' )

	# Add a last entry to register a new rig
 
	cmds.separator(height=8, style='none')
		
	cmds.frameLayout(label=maya.stringTable['y_stereoRigToolEditor.kRegister' ])
	cmds.columnLayout()
	cmds.separator(height=5, style='none')

	[name, menu, text, text2] = __oneItem(layout, None, ['','', ''], 'new')
	
	cmds.separator(height=5, style='none')
	
	cmds.rowColumnLayout(numberOfColumns=2,
						 columnSpacing=[2,10],
						 columnWidth=[[1,150],[2,300]])
	cmds.text(label='')
	btn = cmds.button( label=maya.stringTable['y_stereoRigToolEditor.kNewRig' ])
	btn = cmds.button(btn, edit=True,
					  command=__buildCB2(layout, '__add', name, menu, text, text2) )
	cmds.setParent( '..' )
	
	cmds.setParent( '..' )
	cmds.setParent( '..' )
	
	cmds.setParent( '..' )

# Keep track of the main window handle
__mainWin = None

def __rebuildUI(layout):
	"Rebuild the complete UI after a tool was added or removed"
	
	cmds.setParent(layout)
	cmds.scrollLayout(layout, edit=True, visible=0)
	for child in cmds.scrollLayout(layout, query=True, childArray=True):
		cmds.deleteUI(child)
	cmds.setParent(layout)
	buildMainToolUI()
	cmds.scrollLayout(layout, edit=True, visible=1)

def rebuildUI(layout):
	"""
	Rebuild the complete UI after a tool was added or removed. Using
	evalDeferred so that it can be attached to the UI controls.
	"""
	parent = cmds.columnLayout(layout, query=True, parent=True)
	cmds.evalDeferred('from maya.app.stereo import stereoRigToolEditor\n'+
					  'stereoRigToolEditor.__rebuildUI("'+parent+'")')

def customRigEditor():
	"Create the custom stereo rig editor window"
	
	global __mainWin

	if (__mainWin <> None) and cmds.window( __mainWin, exists=True ):
		cmds.deleteUI(__mainWin)

	__mainWin = cmds.window( title = maya.stringTable['y_stereoRigToolEditor.kRigWndTitle' ],
							width=500, height=600)
	
	form = cmds.formLayout( )
	scroll = cmds.scrollLayout(horizontalScrollBarThickness=0)
	buildMainToolUI( )
	cmds.formLayout(  form, edit=True, attachForm=[ (scroll, 'top',   0), 
													(scroll, 'left',  0),
													(scroll, 'bottom', 0),
													(scroll, 'right',0) ] )
	cmds.setParent( '..' )
	
	cmds.showWindow( __mainWin )
	return __mainWin
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
