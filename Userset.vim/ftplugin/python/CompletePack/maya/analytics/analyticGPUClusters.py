"""
Analytic class for examining GPU deformer cluster data
"""
import maya.cmds as cmds
import json
from .BaseAnalytic import BaseAnalytic, OPTION_DETAILS
from .decorators import addMethodDocs,addHelp,makeAnalytic
from .analyticGPUDeformers import analyticGPUDeformers
from  maya.debug.emModeManager import emModeManager

@addMethodDocs
@addHelp
@makeAnalytic
class analyticGPUClusters(BaseAnalytic):
    """
    Analyze the usage mode of cluster node.
    """
    def run(self):
        """
        Examine animated cluster nodes and check how they are used.  It checks
        whether they are used for fixed rigid transform, weighted rigid transform
        or per-vertex-weighted transform.

        When the 'details' option is set the CSV columns are:
            ClusterNode         : Name of the animated cluster node
            envelope_is_static : True if the envelope is not animated and its value is 1
            uses_weights         : True if weights are used in the node
            uses_same_weight      : True if weight is the same for all vertices
            Mode                : Mode for this node
            supported_geometry   : True if the geometry processed by animated cluster node
                                  is supported by deformer evaluator

        otherwise the CSV columns are:
            ClusterMode        : Description of the usage for the animated cluster node
            Mode               : Mode for animated cluster nodes meeting this criteria
            supported_geometry  : True if the geometry processed by animated cluster nodes
                                 meeting this criteria is supported by deformer evaluator
            Count              : Number of animated cluster nodes in this mode

            See is_supported_geometry() for what criteria a geometry must meet to be supported.

        One row is output for every animated cluster node.

        The "Mode" is an integer value with the following meaning:
        - 1 => Rigid transform          : cluster node only performs a rigid transform
        - 2 => Weighted rigid transform : cluster node performs a rigid transform, but it
                                          is weighted down by a factor
        - 3 => Per-vertex transform     : cluster node computes a different transform for
                                          each individually-weighted vertex

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

        # Loop and process only cluster nodes.
        cluster_nodes = []
        for node in animated_nodes:
            if cmds.nodeType( node ) == 'cluster':
                # Check the envelope attribute.
                envelope_source = cmds.listConnections( node + '.envelope' , source=True , destination=False )
                if envelope_source and len( envelope_source ) > 0:
                    envelope_is_static = False
                else:
                    envelope = cmds.getAttr( node + '.envelope' )
                    if envelope == 1:
                        envelope_is_static = True
                    else:
                        envelope_is_static = False

                # Now loop over each output geometry as separate usage of this node.
                geometries      = cmds.cluster( node , query=True , geometry=True )
                geometry_indices = cmds.cluster( node , query=True , geometryIndices=True )
                if geometries == None or geometry_indices == None:
                    continue

                cluster_geometry = dict( zip( geometry_indices , geometries ) )
                for index , geometry in cluster_geometry.items():
                    # Check if the deformed geometry is supported.
                    supported_geometry = analyticGPUDeformers.is_supported_geometry( geometry )

                    # Check if weights are used.
                    uses_weights = False
                    weight_plug = '%s.weightList[%d]' % ( node , index )
                    weights_source = cmds.listConnections( weight_plug , source=True , destination=False )
                    if weights_source and len( weights_source ) > 0:
                        # If they are animated, we consider they don't have default value.
                        uses_weights = True

                    uses_same_weight = False
                    common_value = None
                    if not uses_weights:
                        uses_same_weight = True

                        # Check if the weights have non default value.
                        weights = cmds.percent( node , geometry , query=True , value=True )
                        for weight in weights:
                            if common_value == None:
                                common_value = weight
                            else:
                                if common_value != weight:
                                    uses_same_weight = False
                                    break

                    if ( not uses_same_weight ) or ( common_value != 1 ):
                        uses_weights = True

                    # Determine the mode.
                    if uses_weights:
                        mode = 3
                    else:
                        if envelope_is_static:
                            mode = 1
                        else:
                            mode = 2

                    # Append the info.
                    nodeName = '%s[%d]' % ( self._node_name(node) , index )
                    cluster_nodes.append( ( nodeName , envelope_is_static , uses_weights , uses_same_weight , mode , supported_geometry ) )

        if not cluster_nodes:
            self.warning( 'No GPU clusters to examine' )
            return

        # Output to CSV.
        if self.option(OPTION_DETAILS):
            self._output_csv( [ 'ClusterNode'
                              , 'EnvelopeIsStatic'
                              , 'UsesWeights'
                              , 'UsesSameWeight'
                              , 'Mode'
                              , 'SupportedGeometry'
                              ] )
            output_rows = cluster_nodes
        else:
            self._output_csv( [ 'ClusterType'
                              , 'Mode'
                              , 'SupportedGeometry'
                              , 'Count'
                              ] )

            # Build the summary using different categories.
            categories = [
                ( 'Rigid_Supported'        , ( 1 , True  ) ) ,
                ( 'Weighted_Supported'     , ( 2 , True  ) ) ,
                ( 'PerVertex_Supported'    , ( 3 , True  ) ) ,
                ( 'Rigid_NotSupported'     , ( 1 , False ) ) ,
                ( 'Weighted_NotSupported'  , ( 2 , False ) ) ,
                ( 'PerVertex_NotSupported' , ( 3 , False ) ) ,
                ]

            # Loop over each "category" and count the number of collected nodes (in cluster_nodes)
            # meeting the criteria for each category.
            #
            # Here, the criteria to know whether or not a node belongs to a category is:
            # - The "mode" (see help above for description of the modes)
            # - Whether or not the cluster node drives a supported mesh (vs another type of geometry)
            summary = []
            for category in categories:
                name = category[ 0 ]
                criteria = category[ 1 ]
                tester = lambda x,criteria_to_check=criteria : x[4:] == criteria_to_check
                count = len( [node for node in cluster_nodes if tester( node ) ] )

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
