import maya.app.renderSetup.views.lightEditor.editor as editor
import maya.app.renderSetup.views.lightEditor.itemDelegate as itemDelegate
import maya.app.renderSetup.views.lightEditor.itemModel as itemModel
import maya.app.renderSetup.views.lightEditor.itemStyle as itemStyle
import maya.app.renderSetup.views.lightEditor.node as node
import maya.app.renderSetup.views.lightEditor.group as group
import maya.app.renderSetup.views.lightEditor.lightSource as lightSource
import maya.app.renderSetup.views.lightEditor.lightTypeManager as typeMgr
import maya.app.renderSetup.views.lightEditor.enterScope as enterScope
import maya.app.renderSetup.views.lightEditor.utils as utils

"""
This file contains some simple functions for testing of the light editor.
We can create proper test cases later and place in a seperate Test directory.
"""

lightEditorWindow = None

def reloadModules():
	""" Reload all light editor modules """
	reload(typeMgr)
	reload(enterScope)
	reload(utils)
	reload(node)
	reload(group)
	reload(lightSource)
	reload(itemStyle)
	reload(itemModel)
	reload(itemDelegate)
	reload(editor)

def createLightEditorUI():
	""" Creates the light editor UI """
	global lightEditorWindow
	if lightEditorWindow:
		lightEditorWindow.close()
		lightEditorWindow = None

	reloadModules()

	lightEditorWindow = editor.Editor()
	lightEditorWindow.show(dockable=True)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
