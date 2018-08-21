#
#	Description:
#		Assembly-related utility routines.
#

import maya.OpenMaya as OpenMaya

def isReferenceInAssembly(refNodeName):
	'''	
		Determines if the specified reference node is contained within an assembly.
	'''

	selectionList = OpenMaya.MSelectionList()
	selectionList.add( refNodeName )
	refNode = OpenMaya.MObject()
	selectionList.getDependNode( 0, refNode )
	refNodeFn = OpenMaya.MFnReference(refNode)
	assemblyNode = refNodeFn.parentAssembly()
	
	#if the return value is not null object, the reference has a parent of assembly.
	return OpenMaya.MObject() != assemblyNode# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
