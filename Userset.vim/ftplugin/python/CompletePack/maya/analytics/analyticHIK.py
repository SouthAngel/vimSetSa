"""
Analytics looking for HIK in a file.
"""
import maya.cmds as cmds
from .BaseAnalytic import BaseAnalytic
from .decorators import addMethodDocs,addHelp,makeAnalytic

@addMethodDocs
@addHelp
@makeAnalytic
class analyticHIK(BaseAnalytic):
    """
    Analyze structure and usage of HIK characters.

    FBIK pattern:
        A joint connects to an hikEffector through a message attribute.
        Interesting because it causes the EM to fail.
    """
    def run(self):
        """
        Scan all of the HIK connections to see if any recognized patterns
        are found.
        """
        # Find all joints present
        all_joints = cmds.ls( type='joint' )
        try:
            joint_count = len(all_joints)
        except TypeError:
            joint_count = 0

        # Find all hikEffectors present
        all_hik_effectors = cmds.ls( type='hikEffector' )
        try:
            hik_effector_count = len(all_hik_effectors)
        except TypeError:
            hik_effector_count = 0

        self._output_csv( [ 'Pattern'
                          , 'Joints'
                          , 'Handles'
                          ] )

        if joint_count == 0 or hik_effector_count == 0:
            self.warning( 'No patterns to report' )
            return
        
        # Set the leading zero's on joint and effector names consistently
        if joint_count > hik_effector_count:
            self.set_node_count( joint_count )
        else:
            self.set_node_count( hik_effector_count )

        # Loop through all joints, looking for the connection from the
        # message attribute to the hik_effector node
        for joint in all_joints:
            effectors = cmds.listConnections( '%s.message' % joint )
            for effector in effectors:
                if cmds.nodeType( effector ) == 'hikEffector':
                    self._output_csv( ['FBIK'
                                      , self._node_name( joint )
                                      , self._node_name( effector ) ] )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
