
"""

This module wraps around Maya's internal commands and api functions
for querying polygon objects. It provides a class base abstraction to
store vertex and faces. 

The main class is polyUtilMeshQuery.  When called this class will hold
onto empty list of mesh primitives.  It must be initialized with a
Maya mesh object by calling the gatherFromMesh method.  After that
point all list objects will be populated with the current values of
the mesh at the instance in time that it was queried.

The class does not store any pointer to Maya objects in the scene. So
it acts as a container for stats on the mesh.  This can then be used
in unit tests to make comparison between mesh states or simply as a
convenient way to access the mesh data.

"""

import maya.OpenMaya as OpenMaya

class polyUtilMeshQuery:
	def __init__( self, state_init = {} ):
		'''

		Main class initialization. By default, itt takes no arguments
		and simply initializes the mesh data structures to empty. However,
		callers can optionally pass in a dictionary object which is used
		to populate the data value.

		This class is used for some unit tests and the unit tests need
		a way to save the current polygon state, revert it back to
		that state and compare it between states. So the parameter
		above is a dictionary form of this class.  See __str__ for
		more more information.

		
		'''
		
		self._vertices = []
		self._faces = []

		self.data_tab = [ ('vertices', self._vertices),
						  ('faces', self._faces) ] 


		# Pull values from the state initialization table if
		# that data exists.
		# 
		for d in self.data_tab:
			if state_init.has_key(d[0]):
				d[1] = state_init[d[0]]
				
		
	def gatherFromMesh( self, meshStrName, smooth=False ):
		'''
		Given a mesh shape name, gather up statistics of that mesh in
		python friendly data structure.  Currently it only gathers the
		following components:
		   - vertices
		   - face data

		It is possible to ask for the smooth version of the mesh by
		setting the smooth flag to True. 
		
		'''
		
		selList = OpenMaya.MSelectionList()
		selList.add( str(meshStrName) )
		meshObj = OpenMaya.MObject()
		selList.getDependNode( 0, meshObj )
		
		unsmoothedMesh = OpenMaya.MFnMesh( meshObj )
		meshFn = unsmoothedMesh 
		if smooth:
			# We have to grab the smooth mesh output and
			# get that as our mesh object.
			#
			obj = OpenMaya.MObject()
			plug = meshFn.findPlug( "outSmoothMesh", False )
			if plug:
				obj = plug.asMObject( )
				if not obj.isNull():
					meshFn = OpenMaya.MFnMesh(obj)
		
		floatPts = OpenMaya.MFloatPointArray()
		meshFn.getPoints( floatPts )
		
		# Convert floatPts into a proper python list.
		#
		for i in range(floatPts.length()):
			mpt = floatPts[i]
			self._vertices.append( (mpt.x, mpt.y,mpt.z) )

		polyCount = meshFn.numPolygons()
		for i in range(polyCount):
			intArray = OpenMaya.MIntArray()
			meshFn.getPolygonVertices( i, intArray )
			self._faces.append( list(intArray) )


	def asDictionary( self ):
		'''
		Returns this class as a dictionary object. That is suitable
		for the initialization method of this class.
		'''
		table = {} 
		for d in self.data_tab:
			table[d[0]] = d[1]
		return table 
			
	def __str__( self ):
		'''
		Output this class in a string format.
		'''
		myD  = self.asDictionary()
		return str(myD)
		
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
