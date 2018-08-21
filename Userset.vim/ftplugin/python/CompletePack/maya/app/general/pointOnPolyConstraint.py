import maya.cmds as cmds
import maya.OpenMaya as om

def assembleCmd():
	cmd = ''

	sel = om.MSelectionList()
	om.MGlobal.getActiveSelectionList( sel )
	if sel.length() > 1:
		for i in range( 0, sel.length()-1 ):
			path = om.MDagPath()
			comp = om.MObject()
			dn = om.MObject()
			sel.getDependNode(i, dn);
			sel.getDagPath( i, path, comp )
			
			#match naming used in pointonpolyconstraint.cmd
			useParentName = ""
			if dn.apiType() == om.MFn.kMesh :
				dagNode = om.MFnDagNode(dn)
				if dagNode.parentCount == 1:
					path.pop();	
					useParentName = path.partialPathName();
			
			
			strings = []

			sel.getSelectionStrings( i, strings )
			try:
				if useParentName != "" :
					name = useParentName
				else:
					name = strings[0].split( '.' )[0]
				namespaces = name.split(':')
				name = namespaces[len(namespaces)-1]
				if '.vtx[' in strings[0]:
					meshIt = om.MItMeshVertex( path, comp )
					if meshIt.count() == 1:
						# single vertex selected - place on the vertex
						uv = om.MScriptUtil()
						uv.createFromDouble( 0.0 )
						uvPtr = uv.asFloat2Ptr()
						meshIt.getUV( uvPtr )
						uv = [ om.MScriptUtil.getFloat2ArrayItem(uvPtr,0,j) for j in [0,1] ]
						cmd += '; setAttr ($constraint[0]+".%sU%d") %f; setAttr ($constraint[0]+".%sV%d") %f' % ( name, i, uv[0], name, i, uv[1] )
				elif '.e[' in strings[0]:
					meshIt = om.MItMeshEdge( path, comp )
					if meshIt.count() == 1:
						# single edge selected - place in the centre of the edge
						vtx = [ meshIt.index( j ) for j in [ 0, 1 ] ]
						vtxIt = om.MItMeshVertex( path )
						uvs = []
						for v in vtx:
							prev = om.MScriptUtil()
							prev.createFromInt( 0 )
							prevPtr = prev.asIntPtr()
							vtxIt.setIndex( v, prevPtr )
							uv = om.MScriptUtil()
							uv.createFromDouble( 0.0 )
							uvPtr = uv.asFloat2Ptr()
							vtxIt.getUV( uvPtr )
							uvs.append( [ om.MScriptUtil.getFloat2ArrayItem(uvPtr,0,j) for j in [0,1] ] )
						uv = [ 0.5*(uvs[0][j]+uvs[1][j]) for j in [0,1] ]
						cmd += '; setAttr ($constraint[0]+".%sU%d") %f; setAttr ($constraint[0]+".%sV%d") %f' % ( name, i, uv[0], name, i, uv[1] )
				elif '.f[' in strings[0]:
					meshIt = om.MItMeshPolygon( path, comp )
					if meshIt.count() == 1 and meshIt.hasUVs():
						# single face selected - place in the centre of the face
						u, v = om.MFloatArray(), om.MFloatArray()
						meshIt.getUVs( u, v )
						uv = ( sum(u)/len(u), sum(v)/len(v) )
						cmd += '; setAttr ($constraint[0]+".%sU%d") %f; setAttr ($constraint[0]+".%sV%d") %f' % ( name, i, uv[0], name, i, uv[1] )
			except Exception as inst:
				cmd += '; print("%s")' % str(inst)

	return cmd
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
