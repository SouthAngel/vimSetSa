"""
Analytic class for skin cluster networks
"""
import maya.cmds as cmds
from .BaseAnalytic import BaseAnalytic
from .decorators import addMethodDocs,addHelp,makeAnalytic

@addMethodDocs
@addHelp
@makeAnalytic
class analyticSkinClusters(BaseAnalytic):
    """
    Analyze type and usage of skin cluster deformers to discover usage
    patterns contrary to the assumptions of the code.
    """
    def run(self):
        """
        Examine the skin cluster nodes in the scene for connection on the
        driver points attribute. Checks for any connection first, and then for
        the size of the driver versus the size of the driven mesh second. The
        assumption was that the driver would always be much smaller than the
        driven mesh since that's kind of the point of a skin cluster.

        The analytics output contains the following columns
            Deformer    : Name of the skin cluster found
            Connection    : Name of the node connected at the driver points
                          input or '' if none
            DriverSize    : Number of points in the driver points input
            DrivenSize    : Number of points in the driven object
        """
        self._output_csv( [ 'Deformer'
                          , 'Connection'
                          , 'DriverSize'
                          , 'DrivenSize'
                          ] )

        clusterList = cmds.ls( type='skinCluster' )
        try:
            if len(clusterList) == 0:
                self.warning( 'No skin clusters to check' )
                return
        except Exception, ex:
            # If the 'ls' command returns None this is the easiest
            # way to trap that case.
            self.warning( 'Skin cluster check failed ({0:s})'.format(str(ex)) )
            return

        for skinCluster in clusterList:
            driverSize = 0
            drivenSize = 0
            drivers = cmds.listConnections( '%s.driverPoints' % skinCluster, destination=False, source=True )
            if drivers:
                for driver in drivers:
                    self._output_csv( [ self._node_name(skinCluster)
                                      , self._node_name(driver)
                                      , str(driverSize)
                                      , str(drivenSize)
                                      ] )
            else:
                self._output_csv( [ self._node_name(skinCluster)
                                  , ''
                                  , '0'
                                  , str(drivenSize)
                                  ] )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
