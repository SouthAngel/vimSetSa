"""
Analytic class for examining GPU deformer information
"""
import json
import maya.cmds as cmds
from .BaseAnalytic import BaseAnalytic, OPTION_DETAILS
from .decorators import addMethodDocs,addHelp,makeAnalytic
from  maya.debug.emModeManager import emModeManager

@addMethodDocs
@addHelp
@makeAnalytic
class analyticGPUDeformers(BaseAnalytic):
    """
    Analyze the usage mode of deformer nodes.
    """
    @staticmethod
    def is_supported_geometry( geometry ):
        """
        Checks if the geometry is supported by deformer evaluator.

        For it to be supported, it must:
            1) Be a mesh
            2) Not have a connected output
            3) Have at least k vertices, where k=2000 on NVidia hardware (hard-coded value)
        """
        # Check if the deformed geometry is a mesh.
        geometry_type = cmds.nodeType( geometry )
        if geometry_type != 'mesh':
            return False

        # Check if output is connected.
        world_mesh_dsts = cmds.listConnections( geometry + '.worldMesh'
                                              , source=False
                                              , destination=True
                                              , plugs=True )
        if world_mesh_dsts != None and len( world_mesh_dsts ) > 0:
            return False

        # Check the number of vertices.
        vertex_count = cmds.polyEvaluate( geometry , vertex=True )
        if vertex_count < 2000:
            return False

        return True

    #======================================================================
    @staticmethod
    def __deformer_types( ):
        """
        Return the list of deformer types.
        """
        deformer_types = [
            "baseLattice" ,
            "blendShape" ,
            "boneLattice" ,
            "cluster" ,
            "deformBend" ,
            "deformFlare" ,
            "deformSine" ,
            "deformSquash" ,
            "deformTwist" ,
            "deformWave" ,
            "ffd" ,
            "flexorShape" ,
            "historySwitch" ,
            "jiggle" ,
            "jointCluster" ,
            "jointFfd" ,
            "jointLattice" ,
            "lattice" ,
            "nonLinear" ,
            "revealGeometry" ,
            "sculpt" ,
            "shrinkWrap" ,
            "skinCluster" ,
            "softMod" ,
            "surfaceFit" ,
            "textureDeformer" ,
            "transferAttributes" ,
            "tweak" ,
            "wire" ,
            "wrap" ,
        ]

        return deformer_types

    #======================================================================
    def run(self):
        """
        Examine animated deformers nodes and check how they are used.

        If the 'details' option is set the CSV columns are:
            DeformerNode      : Name of the animated deformer node
            Type              : Type for this node
            SupportedGeometry : True if the geometry processed by animated
                                deformer node is supported by deformer evaluator

        otherwise the CSV columns are:
            DeformerMode       : Description of the usage for the animated deformer node
            Type               : Deformer type
            SupportedGeometry  : True if the geometry processed by animated
                                 deformer nodes is supported by deformer evaluator
            Count              : Number of animated deformer nodes in this mode

            See is_supported_geometry() for what criteria a geometry must meet to be supported.

        One row is output for every animated deformer node.

        Return True if the analysis succeeded, else False
        """
        with emModeManager() as em_manager:
            em_manager.setMode( 'ems' )
            em_manager.rebuild()

            # Get all animated nodes.
            try:
                json_nodes = json.loads(cmds.dbpeek( op='graph', eg=True, all=True, a='nodes' ))
                animated_nodes = set( json_nodes['nodes'] )
            except Exception, ex:
                self.error( 'Graph examination failure ({0:s})'.format( str(ex) ) )
                return

        if not animated_nodes:
            self.warning( 'No GPU animation to examine' )
            return

        # deformer node types.
        deformer_node_types = self.__deformer_types()

        # Loop and process only deformer nodes of the right type.
        deformer_nodes = []
        for node in animated_nodes:
            # Get the type.
            node_type = cmds.nodeType( node )

            if node_type in deformer_node_types:
                # Now loop over each output geometry as separate usage of this node.
                geometries      = cmds.deformer( node , query=True , geometry=True )
                geometry_indices = cmds.deformer( node , query=True , geometryIndices=True )
                if geometries == None or geometry_indices == None:
                    continue

                deformer_geometry = dict( zip( geometry_indices , geometries ) )
                for index , geometry in deformer_geometry.items():
                    # Check if the deformed geometry is supported.
                    supportedGeometry = self.is_supported_geometry( geometry )

                    # Append the info.
                    nodeName = '%s[%d]' % ( self._node_name(node) , index )
                    deformer_nodes.append( ( nodeName , node_type , supportedGeometry ) )

        # Output to CSV.
        if self.option(OPTION_DETAILS):
            self._output_csv( [ 'DeformerNode'
                              , 'Type'
                              , 'SupportedGeometry'
                              ] )
            output_rows = deformer_nodes
        else:
            self._output_csv( [ 'DeformerMode'
                              , 'Type'
                              , 'SupportedGeometry'
                              , 'Count'
                              ] )

            # Build the summary using different categories.
            categories = []
            for node_type in deformer_node_types:
                categories.append( ( "%s_NotSupported" % node_type , ( node_type , False ) ) )
                categories.append( ( "%s_Supported"    % node_type , ( node_type , True  ) ) )

            # Loop over each "category" and count the number of collected nodes (in deformer_nodes)
            # meeting the criteria for each category.
            #
            # Here, the criteria to know whether or not a node belongs to a category is:
            # - The node type
            # - Whether or not the deformer node drives a supported mesh (vs another type of geometry)
            summary = []
            for category in categories:
                name = category[ 0 ]
                criteria = category[ 1 ]
                tester = lambda x,criteria_to_check=criteria : x[1:] == criteria_to_check
                count = len( [node for node in deformer_nodes if tester( node ) ] )

                summary.append( ( name , criteria[0] , criteria[1] , count ) )

            output_rows = summary

        for row in output_rows:
            self._output_csv( list( row ) )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
