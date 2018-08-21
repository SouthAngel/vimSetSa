import maya.api.OpenMaya as om
import maya.cmds as cmds
import os

def findNodeFromMaya(nodeName):
	try:
		s = om.MSelectionList()
		s.add(nodeName)
		if s.isEmpty():
			return None
		return s.getDependNode(0)
	except:
		return None		

def findSelectedNodeFromMaya():
	s = om.MGlobal.getActiveSelectionList()
	if s.isEmpty():
		return None
	return s.getDependNode(0)

def createDynamicAttribute(nodeName, attrName, attrType, value):
	result = cmds.listAttr(nodeName, string=attrName)
	if not result:
		cmds.addAttr(nodeName, longName=attrName, attributeType=attrType, defaultValue=value)

def resolveIconFile(filename):
	"""Resolve filenames using the XBMLANGPATH icon searchpath or look
	through the embedded Qt resources (if the path starts with a ':').

	:Parameters:
		filename (string)
			filename path or resource path (uses embedded Qt resources if starts with a ':'
	
	:Return: (string)
		Fully resolved filename, or empty string if file is not resolved.
	"""
	resolvedFileName = ""
	# Load directly if it is a QRC resource (starts with :)
	if filename.startswith(":"):  # it is a QRC resource (starts with ':', load it directly
		resolvedFileName = filename
	else: # Search icon search path to find image file
		searchpaths = os.environ["XBMLANGPATH"].split(os.pathsep)
		for p in searchpaths:
			p = p.replace("%B", "")  # Remove the trailing %B found in Linux paths
			fullpath = os.path.join(p, filename)
			if os.path.isfile(fullpath):
				resolvedFileName = fullpath
	return resolvedFileName
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
