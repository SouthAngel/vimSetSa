"""
SolverUI - Module containing functions for managing the solver node
	related UI elements.

"""
# Maya
import maya
maya.utils.loadStringResourcesForModule(__name__)

import maya.cmds as cmds
from maya.app.mayabullet.Trace import Trace

solverDisplayOptionsMap = {
	maya.stringTable[ 'y_SolverUI.kDrawCenterOfMass'  ]		: (1<<00),
	maya.stringTable[ 'y_SolverUI.kDrawBB'  ]		: (1<<01),
	maya.stringTable[ 'y_SolverUI.kDrawContactPoints'  ]		: (1<<03),
	maya.stringTable[ 'y_SolverUI.kDrawConstraints'  ]			: (1<<11),
	maya.stringTable[ 'y_SolverUI.kDrawCollisionShape'  ]		: (1<<4),
		}

def attrName(attr):
	return attr.split('.')[-1]

@Trace()
def optionsColumnCtrl(attr):
	return '{0}_column'.format(attrName(attr))
@Trace()
def optionsFormCtrl(attr):
	return '{0}_form'.format(attrName(attr))

@Trace()
def optionsExist(attr):
	return cmds.control(optionsColumnCtrl(attr),exists=True) 

class AEOptionsChanged:
	@Trace()
	def __init__( self, attrName, control, optionValue ):
		self._attrName = attrName
		self._control = control
		self._optionValue = optionValue

	@Trace()
	def __call__(self,*args,**kw):
		# query the value from the attr
		value = cmds.getAttr(self._attrName)

		# query the value from the checkBox
		checked = args[0]
	
		# if checkBox different from attribute value then change
		if ((value&self._optionValue)!=checked):
			if (checked):
				value += self._optionValue
			else:
				value -= self._optionValue

			cmds.setAttr( self._attrName, value )
			if (not maya.cmds.commandEcho(query=True, state=True)):
				setAttrCmd = 'setAttr {0} {1};'.format( self._attrName, value )
				print( setAttrCmd )

class AEDeleteControl:
	@Trace()
	def __init__(self, ctrl):
		self._ctrl = ctrl

	@Trace()
	def __call__(self):
		if self._ctrl:
			cmds.deleteUI(self._ctrl)
			self._ctrl = None

@Trace()
def AEOptions( attr, optionsMap, deleteCB=None, replace=False ):
	replace = optionsExist(attr)

	# Register a script job to delete all of the control UI in the case of a file -new
	if not replace:
		cmds.scriptJob( runOnce=True, e=["deleteAll", AEDeleteControl(optionsFormCtrl(attr))] )

	cmds.setUITemplate( "attributeEditorTemplate", pushTemplate=True )

	try:
		if not replace:
			formName = optionsFormCtrl(attr)
			columnName = optionsColumnCtrl(attr)

			cmds.formLayout(formName,numberOfDivisions=100)

			cmds.columnLayout(columnName)

			cmds.formLayout(formName, e=True,
				attachForm=[[columnName,"left",148]])

	except Exception as e:
		print 'error creating layout {0}'.format(e)

	# Iterate over each option and create a checkbox
	attrValue = cmds.getAttr(attr)

	# sort by optionName
	for optionName in sorted(optionsMap.iterkeys()):
		optionValue = optionsMap[optionName]
		# If the UI doesn't exist create it.  Otherwise, reuse the existing UI.
		checkBoxName = '{0}_{1}_CheckBox'.format(attrName(attr), optionValue)

		if (replace) :
			cmds.checkBox(checkBoxName,
				e=True,
				label=optionName,
				value=(attrValue&optionValue),
				changeCommand=AEOptionsChanged(attr, checkBoxName, optionValue))
		else:
			cmds.checkBox(checkBoxName,
				label=optionName,
				value=(attrValue&optionValue),
				changeCommand=AEOptionsChanged(attr, checkBoxName, optionValue))
	
	cmds.setUITemplate( popTemplate=True )


# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
