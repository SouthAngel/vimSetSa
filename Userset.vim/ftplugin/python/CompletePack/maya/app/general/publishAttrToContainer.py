import maya
maya.utils.loadStringResourcesForModule(__name__)

import maya.cmds
import warnings

def pyError(errorString):
	""" print an error message """
	import maya.mel as mel
	try:
		mel.eval('error "%s"' % errorString)
	except: pass

# Take a list of attrs and convert any contained triple children into
# their parent. For example if the input is:
#   diffuse, colorR, colorG, colorB
# the return would be:
#   diffuse, color
#
def collectTripleAttrs(obj,attrs):
	returnAttrs = []
	for ii in range(len(attrs)):
		addedTriple = 0
		if (attrs[ii] == ''):
			continue
		if ((ii+2) < len(attrs)):
			parent = maya.cmds.attributeQuery(attrs[ii],listParent=1,node=obj)
			if (parent):
				attrType = maya.cmds.getAttr(obj+'.'+parent[0],type=1)
				if (attrType == 'float3' or attrType == 'double3'):
					parent2 = maya.cmds.attributeQuery(attrs[ii+1],listParent=1,node=obj)
					parent3 = maya.cmds.attributeQuery(attrs[ii+2],listParent=1,node=obj)
					if (parent2 and parent3 and (parent3[0] == parent[0]) and (parent2[0] == parent[0])):
						returnAttrs.append(parent[0])
						attrs[ii+1] = ''
						attrs[ii+2] = ''
						addedTriple = 1
		if (addedTriple == 0):
			longAttrName = maya.cmds.listAttr(obj+'.'+attrs[ii])
			returnAttrs.append(longAttrName[0])
	return returnAttrs				

def addAndConnectObjAttrsToContainer(obj,inAttrs):
	#get container node
	containerNode = maya.cmds.container(query=1, findContainer=obj)
	if containerNode:
		attrs = collectTripleAttrs(obj,inAttrs)
		for attr in attrs:
			maya.cmds.container(containerNode,edit=1,publishAndBind=[obj+'.'+attr,attr])
			msg = maya.stringTable['y_publishAttrToContainer.kPublishingAttrMsg'] % (obj,attr,containerNode)
			print(msg)
	else:
		warnings.warn(maya.stringTable['y_publishAttrToContainer.kNotInContainer'])

def removePublishedAttrsFromContainer(obj,inAttrs):
	#get container node
	if( maya.cmds.container(obj,query=1,isContainer=1) ):
		containerNode = obj ;
	else:
		containerNode = maya.cmds.container(query=1, findContainer=obj)
	if containerNode:
		for attr in inAttrs:
			maya.cmds.container(containerNode,edit=1,unbindAndUnpublish=(obj+'.'+attr))
			msg = 'container -e -unbindAndUnpublish %s.%s %s;' % (obj,attr,containerNode)
			print(msg)
	else:
		warnings.warn(maya.stringTable['y_publishAttrToContainer.kNotInContainer2'])

	
def publishAttrToContainer():
	# main channel box selection
	#
	selectedObjects = maya.cmds.channelBox(r'mainChannelBox',query=1, mainObjectList=1)
	selectedAttrs = maya.cmds.channelBox(r'mainChannelBox',query=1, selectedMainAttributes=1)

	if selectedObjects and selectedAttrs:
		addAndConnectObjAttrsToContainer(selectedObjects[0],selectedAttrs)

	# shape channel box selection
	#
	selectedObjects = maya.cmds.channelBox(r'mainChannelBox',query=1, shapeObjectList=1)
	selectedAttrs = maya.cmds.channelBox(r'mainChannelBox',query=1, selectedShapeAttributes=1)

	if selectedObjects and selectedAttrs:
		addAndConnectObjAttrsToContainer(selectedObjects[0],selectedAttrs)

	# history channel box selection
	#
	selectedObjects = maya.cmds.channelBox(r'mainChannelBox',query=1, historyObjectList=1)
	selectedAttrs = maya.cmds.channelBox(r'mainChannelBox',query=1, selectedHistoryAttributes=1)

	if selectedObjects and selectedAttrs:
		addAndConnectObjAttrsToContainer(selectedObjects[0],selectedAttrs)

	# output channel box selection
	#
	selectedObjects = maya.cmds.channelBox(r'mainChannelBox',query=1, outputObjectList=1)
	selectedAttrs = maya.cmds.channelBox(r'mainChannelBox',query=1, selectedOutputAttributes=1)

	if selectedObjects and selectedAttrs:
		addAndConnectObjAttrsToContainer(selectedObjects[0],selectedAttrs)

def unpublishAttrFromContainer():

	foundObjects = 0

	# main channel box selection
	#
	selectedObjects = maya.cmds.channelBox(r'mainChannelBox',query=1, mainObjectList=1)
	selectedAttrs = maya.cmds.channelBox(r'mainChannelBox',query=1, selectedMainAttributes=1)

	if selectedObjects and selectedAttrs:
		removePublishedAttrsFromContainer(selectedObjects[0],selectedAttrs)
		foundObjects = 1

	# shape channel box selection
	#
	selectedObjects = maya.cmds.channelBox(r'mainChannelBox',query=1, shapeObjectList=1)
	selectedAttrs = maya.cmds.channelBox(r'mainChannelBox',query=1, selectedShapeAttributes=1)

	if selectedObjects and selectedAttrs:
		removePublishedAttrsFromContainer(selectedObjects[0],selectedAttrs)
		foundObjects = 1

	# history channel box selection
	#
	selectedObjects = maya.cmds.channelBox(r'mainChannelBox',query=1, historyObjectList=1)
	selectedAttrs = maya.cmds.channelBox(r'mainChannelBox',query=1, selectedHistoryAttributes=1)

	if selectedObjects and selectedAttrs:
		removePublishedAttrsFromContainer(selectedObjects[0],selectedAttrs)
		foundObjects = 1

	# output channel box selection
	#
	selectedObjects = maya.cmds.channelBox(r'mainChannelBox',query=1, outputObjectList=1)
	selectedAttrs = maya.cmds.channelBox(r'mainChannelBox',query=1, selectedOutputAttributes=1)

	if selectedObjects and selectedAttrs:
		removePublishedAttrsFromContainer(selectedObjects[0],selectedAttrs)
		foundObjects = 1

	if not foundObjects:
		pyError( maya.stringTable['y_publishAttrToContainer.kNoChannelBoxSelection'])

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
