"""
Prototype platform to view the currently available custom evaluators and their
states.

Import via:

	from maya.plugin.evaluator.customEvaluatorUI import customEvaluatorUI, customEvaluatorDisplay
	
and then create the window with:

	evaluatorUI = customEvaluatorUI()

or visualize the custom evaluator clusters using display layers with:

	customEvaluatorDisplay('theEvaluatorName')
"""
import maya.cmds as cmds

__all__ = [ 'customEvaluatorReadyStateChange'
		  , 'customEvaluatorActiveStateChange'
		  , 'customEvaluatorUI'
		  , 'customEvaluatorDisplay'
		  ]

#======================================================================

def customEvaluatorReadyStateChange(evaluatorName, newValue):
	"""
	Callback when a checkbox is ticked to alter the ready state of a custom
	evaluator.
	"""
	print 'Changing evaluator %s ready state to %d' % (evaluatorName, newValue)
	cmds.evaluatorInternal( name=evaluatorName, ready=newValue )

#======================================================================

def customEvaluatorActiveStateChange(evaluatorName, newValue):
	"""
	Callback when a checkbox is ticked to alter the active state of a custom
	evaluator.
	"""
	print 'Changing evaluator %s active state to %d' % (evaluatorName, newValue)
	cmds.evaluator( name=evaluatorName, enable=newValue )

#======================================================================

customEvaluatorScriptJob = None
def customEvaluatorUI():
	"""
	Create a simple window showing the current status of the custom evaluators
	and providing a callback so that they can update the status when it changes.
	Layout is a row per evaluator with the following information:

		EvaluatorName   Ready []   Active []   <Evaluator-specific information>
	"""
	global customEvaluatorScriptJob
	print 'Constructing custom evaluator UI'
	windowName = 'CustomEvaluatorUI'
	if not cmds.window( windowName, exists=True ):
		windowName = cmds.window( windowName,
								  title='Custom Evaluators',
								  iconName='Custom Evaluators' )
	else:
		cmds.deleteUI( 'CustomEvaluatorUIList' )
		cmds.setParent( windowName )
	if customEvaluatorScriptJob == None:
		customEvaluatorScriptJob = cmds.scriptJob( event=['customEvaluatorChanged','maya.plugin.evaluator.customEvaluatorUI.customEvaluatorUI()'] )
	cmds.frameLayout( 'CustomEvaluatorUIList', label='Custom Evaluator Information' )
	cmds.rowColumnLayout( 'CustomEvaluatorList', numberOfColumns=4,
						  columnAlign=[(1, 'left'), (2, 'center'), (3, 'center'), (4,'left')],
						  columnSpacing=[(1,10), (2,10), (3,10), (4,10)]
						)
	evaluators = cmds.evaluator( query=True, name=True )
	for evaluatorName in evaluators:
		cmds.text(label=evaluatorName, font='boldLabelFont')
		cmds.checkBox( value=cmds.evaluatorInternal(name=evaluatorName, query=True, ready=True),
					   label='Ready',
					   onCommand='maya.plugin.evaluator.customEvaluatorUI.customEvaluatorReadyStateChange("%s",True)' % evaluatorName,
					   offCommand='maya.plugin.evaluator.customEvaluatorUI.customEvaluatorReadyStateChange("%s",False)' % evaluatorName
					 )
		cmds.checkBox( value=cmds.evaluator(name=evaluatorName, query=True, enable=True),
					   label='Active',
					   onCommand='maya.plugin.evaluator.customEvaluatorUI.customEvaluatorActiveStateChange("%s",True)' % evaluatorName,
					   offCommand='maya.plugin.evaluator.customEvaluatorUI.customEvaluatorActiveStateChange("%s",False)' % evaluatorName
					 )
		nodeTypes = cmds.evaluator(name=evaluatorName, query=True, nodeType=True)
		if nodeTypes:
			nodeTypeCount = len(nodeTypes)
		else:
			nodeTypeCount = 0
		infoString = 'Node Types = %d' % nodeTypeCount
		info = cmds.evaluator( name=evaluatorName, query=True, info=True )
		if info and len(info)>0:
			infoString = '%s, %s' % (infoString, info)
		cmds.text( label=infoString )
	cmds.setParent( '..' )
	cmds.button( label='Update', command='maya.plugin.evaluator.customEvaluatorUI.customEvaluatorUI()' )
	cmds.setParent( '..' )
	cmds.showWindow( windowName )

#======================================================================

def customEvaluatorDisplay(customEvaluatorName):
	"""
	Take the named custom evaluator and put each of its evaluation clusters
	into a different display layer with a rotating colouring. (It's rotating
	because the display layers only have a small number of colours available
	whereas there could be a large number of clusters in the scene.)

	Although it only works for DAG nodes this provides a simple visual cue
	of how the custom evaluator has created its clusters.
	"""
	print 'Assigning clusters to display layers'
	clusterInfo = cmds.evaluatorInternal( name=customEvaluatorName, query=True, clusters=True )
	if clusterInfo == None:
		print 'No clusters on evaluator %s' % customEvaluatorName
	else:
		idx = 0
		colour = 1
		try:
			while idx < len(clusterInfo):
				clusterSize = clusterInfo[idx]
				clusterContents = []
				for subIndex in range(1,clusterSize+1):
					objectName = clusterInfo[idx+subIndex]
					if 'dagNode' in cmds.nodeType( objectName, inherited=True ):
						clusterContents.append( objectName )
				# No sense creating a display layer when no DAG objects exist
				if len(clusterContents) > 0:
					cmds.select( clusterContents )
					newLayer = cmds.createDisplayLayer( noRecurse=True, name='%sLayer' % customEvaluatorName )
					cmds.setAttr( '%s.drawInfo.color' % newLayer, colour )
					colour = (colour + 1) % 256
					print '%s contains %s' % (newLayer, clusterContents)
				idx += clusterSize + 1
		except Exception, ex:
			print 'ERR: Bad cluster information at index %d (%s)' % (idx, str(ex))

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
