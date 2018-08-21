"""
Analytic class for GPU deformation tweaks
"""
import json
import maya.cmds as cmds
from .BaseAnalytic import BaseAnalytic, OPTION_DETAILS
from .decorators import addMethodDocs,addHelp,makeAnalytic
from  maya.debug.emModeManager import emModeManager

@addMethodDocs
@addHelp
@makeAnalytic
class analyticGPUTweaks(BaseAnalytic):
    """
    Analyze the usage mode of tweak node.
    """
    def run(self):
        """
        Examine animated tweak nodes and check how they are used.  It checks
        whether they use the relative or absolute mode and whether individual
        tweaks themselves are actually used.

        If the 'details' option is set the CSV columns are:
            TweakNode  : Name of the animated tweak node
            Relative   : Value of the relative_tweak attribute of the animated tweak node
            uses_tweaks : True if tweaks are used in the node
            UsesMesh   : True if some of the geometry processed by animated tweak node is a mesh

        otherwise the CSV columns are:
            TweakType   : Description of the usage for the animated tweak node
            Relative    : Value of the relative_tweak attribute of the animated
                          tweak nodes meeting this criteria
            uses_tweaks  : True if tweaks are used in the nodes meeting this criteria
            UsesMesh    : True if some of the geometry processed by animated tweak
                          nodes meeting this criteria is a mesh
            Count       : Number of animated tweak nodes meeting this criteria

        One row is output for every animated tweak node.

        Return True if the analysis succeeded, else False
        """
        with emModeManager() as em_manager:
            em_manager.setMode( 'ems' )
            em_manager.rebuild()

            # Get all animated nodes.
            try:
                node_list = cmds.dbpeek( op='graph', eg=True, all=True, a='nodes' )
                json_nodes = json.loads(node_list)
                animated_nodes = set( json_nodes['nodes'] )
            except Exception, ex:
                self.error( 'Graph examination failure ({0:s})'.format( str(ex) ) )
                return

        if not animated_nodes:
            self.warning( 'No GPU animation to examine' )
            return

        # Loop and process only tweak nodes.
        tweak_nodes = []
        for node in animated_nodes:
            if cmds.nodeType( node ) == 'tweak':
                # Read the relative_tweak attribute.
                relative_tweak = cmds.getAttr( node + '.relativeTweak' )

                # Check if tweaks are used.
                uses_tweaks = False
                for attribute in [ 'vlist' , 'plist' ]:
                    source = cmds.listConnections( node + '.' + attribute , source=True , destination=False )
                    if source and len( source ) > 0:
                        uses_tweaks = True
                        break

                # Check if the deformed geometry is a mesh.
                usesMesh = False
                destination_plugs = cmds.listConnections( node + '.outputGeometry'
                                                        , source=False
                                                        , destination=True
                                                        , plugs=True )
                for plug in destination_plugs:
                    geometry_type = cmds.getAttr( plug , type=True )
                    if geometry_type == 'mesh':
                        usesMesh = True
                        break

                tweak_nodes.append( ( self._node_name(node) , relative_tweak , uses_tweaks , usesMesh ) )

        if not tweak_nodes:
            self.warning( 'No GPU tweaks to examine' )
            return

        # Output to CSV.
        if self.option(OPTION_DETAILS):
            self._output_csv( [ 'TweakNode'
                              , 'Relative'
                              , 'UsesTweaks'
                              , 'UsesMesh'
                              ] )
            outputRows = tweak_nodes
        else:
            self._output_csv( [ 'TweakType'
                              , 'Relative'
                              , 'UsesTweaks'
                              , 'UsesMesh'
                              , 'Count'
                              ] )

            # Build the summary using different categories.
            categories = [
                ( 'Relative_Tweaks_Mesh'       , ( True  , True  , True  ) ) ,
                ( 'NoRelative_Tweaks_Mesh'     , ( False , True  , True  ) ) ,
                ( 'Relative_NoTweaks_Mesh'     , ( True  , False , True  ) ) ,
                ( 'NoRelative_NoTweaks_Mesh'   , ( False , False , True  ) ) ,
                ( 'Relative_Tweaks_NoMesh'     , ( True  , True  , False ) ) ,
                ( 'NoRelative_Tweaks_NoMesh'   , ( False , True  , False ) ) ,
                ( 'Relative_NoTweaks_NoMesh'   , ( True  , False , False ) ) ,
                ( 'NoRelative_NoTweaks_NoMesh' , ( False , False , False ) ) ,
                ]
            summary = []
            for category in categories:
                name = category[ 0 ]
                criteria = category[ 1 ]
                tester = lambda x,criteria_to_check=criteria : x[1:4] == criteria_to_check
                count = len( [node for node in tweak_nodes if tester( node ) ] )

                summary.append( ( name , criteria[0] , criteria[1] , criteria[2] , count ) )

            outputRows = summary

        for row in outputRows:
            self._output_csv( list( row ) )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
