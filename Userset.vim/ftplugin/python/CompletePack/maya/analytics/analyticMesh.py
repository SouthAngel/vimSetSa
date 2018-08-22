"""
Analytic class for examining mesh objects
"""
import re
import maya.cmds as cmds
from .BaseAnalytic import BaseAnalytic
from .decorators import addMethodDocs,addHelp,makeAnalytic

RE_MULTI_GEOMETRY_OUTPUT = re.compile( r'\[([0-9]+)\]' )

@addMethodDocs
@addHelp
@makeAnalytic
class analyticMesh(BaseAnalytic):
    """
    Analyze the volume and distribution of mesh data.
    """
    def __traceMeshOrigin(self, mesh_node, came_from_output):
        """
        The listHistory command doesn't differentiate between geometry history
        and other history, such as matrix data. This method recursively looks
        backwards through a mesh history using knowledge of the types of nodes
        that can generate or influence meshes (mesh operators, deformers, mesh
        creation, etc.)

        Recursion stops when either no further relevant inputs are found to
        the current node being checked or if the node type is not one of the
        recognized ones.
        """
        node_types = cmds.nodeType(mesh_node, inherited=True)
        input_attribute = None
        if 'mesh' in node_types:
            # This is a mesh shape, inputs come through .inMesh
            input_attribute = 'inMesh'
        elif 'geometryFilter' in node_types:
            # This is a deformer inputs come from .input[x].inputGeometry
            # Use the output attribute to find the matching index "x"
            match = RE_MULTI_GEOMETRY_OUTPUT.search( came_from_output )
            if match:
                input_attribute = 'input[%s].inputGeometry' % match.group(1)
            else:
                # Unrecognized output, we have to bail
                return mesh_node
        elif 'polyModifier' in node_types:
            # This is a polyOperation, inputs come from .inputPolymesh
            input_attribute = 'inputPolymesh'
        elif 'groupParts' in node_types:
            # This is a groupParts node, inputs come from .inputGeometry
            input_attribute = 'inputGeometry'
        elif 'inputGeometry' in cmds.listAttributes(mesh_node):
            # Some other type of geometry history that's not part of the
            # polyModifier hierarchy, e.g. deleteComponents
            input_attribute = 'inputGeometry'
        else:
            # Don't recognize this type
            self.warning( 'Stopping at unrecognized node type %s' % mesh_node )
            return mesh_node

        try:
            stepBack = cmds.listConnections( '%s.%s' % (mesh_node, input_attribute), plugs=True, source=True )[0].split('.')
            origin = self.__traceMeshOrigin( stepBack[0], stepBack[1] )
            return origin
        except Exception:
            # No connection means no source, we're at the end
            return mesh_node

    #======================================================================
    def run(self):
        """
        Scan all of the Mesh shapes in the scene and provide a column for
        each node with the following statistics in it:
            - Number of vertices in the mesh
            - Number of faces in the mesh
            - Number of edges in the mesh
            - Number of triangles in the mesh
            - Number of UV coordinates in the mesh
            - Number of vertices "tweaked"
            - Is it using user normals?
            - What is the source node for the mesh? For meshes with no
              construction history it will be the mesh itself. For others
              it could be a polySphere or other creation operation, or some
              other mesh at the beginning of a deformation chain.
        """
        self._output_csv( ['Node',
                           'Vertices',
                           'Edges',
                           'Faces',
                           'Triangles',
                           'UV Coordinates',
                           'Tweaks',
                           'User Normals',
                           'Source'] )

        mesh_list = cmds.ls( type='mesh' )
        if len(mesh_list) == 0:
            self.warning( 'No meshes, no mesh data to collect' )
            return

        for mesh in mesh_list:
            mesh_name = self._node_name( mesh )

            vertex_count = cmds.polyEvaluate( mesh, vertex=True )
            edge_count = cmds.polyEvaluate( mesh, edge=True )
            face_count = cmds.polyEvaluate( mesh, face=True )
            triangle_count = cmds.polyEvaluate( mesh, triangle=True )
            uv_count = cmds.polyEvaluate( mesh, uvcoord=True )
            tweak_count = cmds.getAttr( '%s.pnts' % mesh, size=True )
            mesh_source = self._node_name( self.__traceMeshOrigin( mesh, None ) )

            user_normals = (cmds.getAttr( '%s.normals' % mesh, size=True ) > 0)

            self._output_csv( [ mesh_name
                              , vertex_count
                              , edge_count
                              , face_count
                              , triangle_count
                              , uv_count
                              , tweak_count
                              , user_normals
                              , mesh_source
                              ] )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
