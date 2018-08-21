"""
Analytic class for examining IK patterns
"""
import maya.cmds as cmds
from .BaseAnalytic import BaseAnalytic, OPTION_DETAILS
from .decorators import addMethodDocs,addHelp,makeAnalytic

@addMethodDocs
@addHelp
@makeAnalytic
class analyticIK(BaseAnalytic):
    """
    Analyze structure and usage of standard IK system.
    """
    def __init__(self):
        """
        Initialize the class members
        """
        super(self.__class__, self).__init__()
        self.joints_reported = {}
        self.joint_count = 0
        self.handle_name = ''
        self.start_joints = []
        self.end_joints = []

    def _follow_chain_up( self, joint ):
        """
        Follow the IK chain recursively up the parent hierarchy. The recursion
        ends when either the root is hit or a node belonging to 'start_joints'
        is hit.

        Presumes that self.start_joints, self.handle_name, and self.joint_count
        are set before being called. These were made into transient class
        members to avoid the messiness of passing a lot of parameters in.

        joint    : Joint being visited
        returns number of joints found in the chain above 'joint', including it
        """
        chain_count = 0
        if joint not in self.start_joints:
            chain_count += 1
            try:
                # This gives a count of nodes in the chain which includes all
                # potential instance branches. That's okay, though it doesn't
                # give the "longest chain" if that is important.
                for link in cmds.listRelatives( joint, allParents=True ):
                    self.joints_reported[link] = True
                    if self.option(OPTION_DETAILS) and link not in self.start_joints:
                        self._output_csv( [ self.handle_name
                                          , 'Chain Link'
                                          , self._node_name( link ) ] )
                    chain_count += self._follow_chain_up( link )
            except TypeError:
                # No relatives existed, end of the line
                pass
        return chain_count

    def run(self):
        """
        Scan all of the standard IK connections to pull out usage statistics.
        "standard" means "not HIK". See analyticHIK() for specific details on
        that IK subsystem.

        The CSV output provides columns for the name of the statistic
        collected and the count of occurences of that statistic with the
        headings 'Handle', 'Parameter', 'Value'. If the 'details' option is not
        set then any node names in the output are replaced by their generic form
        'NODETYPEXXX' where 'NODETYPE' is the type of node and 'XXX' is a
        unique ID per node type. The following are collected:
            - IK Handle Name, 'Solver', Name of the solver the handle uses
            - IK Handle Name, 'Chain Start', Starting node of chain
            - IK Handle Name, 'Chain End', Ending node of chain
            - IK Handle Name, 'Chain Length', Number of nodes in the chain
            - IK Handle Name, 'End Effector', Name of chain's end effector
            - "", 'Solver', Name/Type of solver with no associated handles
            - "", 'Chain Link', Number of Joint nodes with no associated Handle
                (Not reported if the 'details' option is set.)

        If the 'details' option is set these columns are added to the output:
            - IK Handle Name, 'Chain Link', Node in the middle of a chain
            - "", 'Chain Link', Joint node with no associated Handle
        """
        # First find all of the IK types present
        all_solvers = cmds.ls( type='ikSolver' )
        solver_count = len(all_solvers) if all_solvers else 0
        all_handles = cmds.ls( type='ikHandle' )
        handle_count = len(all_handles) if all_handles else 0
        all_effectors = cmds.ls( type='ikEffector' )
        effector_count = len(all_effectors) if all_effectors else 0
        all_joints = cmds.ls( type='joint' )
        self.joint_count = len( all_joints ) if all_joints else 0
        self.joints_reported = {}

        self._output_csv( [ 'Handle'
                          , 'Parameter'
                          , 'Value'
                          ] )

        if solver_count + handle_count + effector_count + self.joint_count == 0:
            self.warning( 'No IK to report' )
            return

        # Set the leading zero's on node names consistently
        max_count = self.joint_count
        if solver_count > max_count:
            max_count = solver_count
        if handle_count > max_count:
            max_count = handle_count
        if effector_count > max_count:
            max_count = effector_count
        self._set_node_name_count( max_count )

        # Loop through the handles, dumping all relevant information
        solvers_used = {}
        for handle in all_handles:
            self.handle_name = self._node_name( handle )

            #----------------------------------------
            # IK Solver
            solvers = cmds.listConnections( '%s.ikSolver' % handle )
            for solver in solvers:
                self._output_csv( [ self.handle_name
                                  , 'Solver'
                                  , self._node_name( solver ) ] )
                solvers_used[solver] = True

            #----------------------------------------
            # Start joints
            self.start_joints = cmds.listConnections( '%s.startJoint' % handle )
            for start_joint in self.start_joints:
                self.joints_reported[start_joint] = True
                self._output_csv( [ self.handle_name
                                  , 'Chain Start'
                                  , self._node_name( start_joint ) ] )

            #----------------------------------------
            # End Effector
            end_effectors = cmds.listConnections( '%s.endEffector' % handle )
            for end_effector in end_effectors:
                self._output_csv( [ self.handle_name
                                  , 'End Effector'
                                  , self._node_name( end_effector ) ] )

            #----------------------------------------
            # Ending joints
            #
            # End effectors have a bunch of different connections. Make
            # sure only unique joints are collected by using the list(set())
            # trick to uniquify the returned values and the list comprehension
            # to restrict it to joints.
            try:
                self.end_joints = list(set([j for j in cmds.listConnections( end_effectors[0] ) if cmds.nodeType(j) == 'joint']))
                for end_joint in self.end_joints:
                    if cmds.nodeType( end_joint ) != 'joint':
                        continue
                    self.joints_reported[end_joint] = True
                    self._output_csv( [ self.handle_name
                                      , 'Chain End'
                                      , self._node_name( end_joint ) ] )
            except Exception:
                self.end_joints = []

            #----------------------------------------
            # Chain lengths
            for end_joint in self.end_joints:
                chain_count = self._follow_chain_up( end_joint )
                # Leaving in the degenerate chains (chain_count = 0) since
                # they may be of interest.
                self._output_csv( [ self.handle_name, 'Chain Length', str(chain_count) ] )

        #----------------------------------------
        # Unused solvers
        for solver in all_solvers:
            if solver in solvers_used:
                continue
            self._output_csv( [ '', 'Solver', self._node_name( solver ) ] )

        #----------------------------------------
        # Joints without handle controls
        try:
            unreported_joints = [j for j in all_joints if not j in self.joints_reported]
        except Exception:
            unreported_joints = []
        if self.option(OPTION_DETAILS):
            for joint in unreported_joints:
                self._output_csv( [ ''
                                  , 'Chain Link'
                                  , self._node_name( joint ) ] )
        else:
            self._output_csv( [ '', 'Chain Link', len(unreported_joints) ] )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
