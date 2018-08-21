"""
Analytic class to look for specific values on the nodes in the scene.
"""
import math
import maya.cmds as cmds
from .BaseAnalytic import BaseAnalytic, OPTION_DETAILS
from .decorators import addMethodDocs,addHelp,makeAnalytic

@addMethodDocs
@addHelp
@makeAnalytic
class analyticValues(BaseAnalytic):
    """
    Analyze use of plug values that make some simple algorithms complex.
    """
    def run(self):
        """
        Here is a complete list of what will be counted and reported:
            - transforms using each of the non-standard rotation orders
            - transforms using scale limits, min and/or max
            - transforms using rotate limits, min and/or max
            - transforms using translation limits, min and/or max
            - joints with incoming connections on their scale attribute(s)
            - joints with incoming connections on their shear attribute(s)
            - joints with incoming connections on their translate attribute(s)
            - joints with non-uniform scale values (and no incoming connection)
            - joints with non-default shear values (and no incoming connection)
            - meshes with displaySmoothMesh turned on

        If the 'details' option is set then instead of showing one line per type
        of match with the number of matches found there will be a line for every
        match showing the node name matched.
        """
        if self.option(OPTION_DETAILS):
            self._output_csv( ["Node Type", "Value Type", "Node Name"] )
        else:
            self._output_csv( ["Node Type", "Value Type", "Count"] )

        #------------------------------------------------------------------
        #{
        #  Check transforms for the following conditions:
        #
        #        Altered rotation order
        #        Limits turned on
        #
        rotateOrderNames = ['xyz', 'yzx', 'zxy', 'xzy', 'yxz', 'zyx', 'Unknown']
        transformNodes = cmds.ls( type='transform' )
        rotateOrders ={}
        limitTypes = {}
        for node in transformNodes:
            rotateOrder = cmds.getAttr( '%s.ro' % node )
            # Cap the rotation type value in case of future changes
            if rotateOrder > 6:
                rotateOrder = 6
            if rotateOrder != 0:
                rotateOrders[rotateOrder] = rotateOrders.get(rotateOrder,0) + 1
                if self.option(OPTION_DETAILS):
                    self._output_csv( ['transform'
                                     , 'Rotate Order %s' % rotateOrderNames[rotateOrder]
                                     , node] )
            for limitType in ['minTransLimitEnable', 'maxTransLimitEnable',
                         'minRotLimitEnable',   'maxRotLimitEnable',
                         'minScaleLimitEnable', 'maxScaleLimitEnable' ]:
                limitsOn= cmds.getAttr( '%s.%s' % (node, limitType) )
                if limitsOn != [(False, False, False)]:
                    limitTypes[limitType] = limitTypes.get(limitType,0) + 1
                    if self.option(OPTION_DETAILS):
                        self._output_csv( ['transform', 'Used Limit %s' % limitType, node] )
        # Only report the summary if the details were not supplied.
        # The summary information can easily be calculated after-the-fact
        # if necessary.
        if not self.option(OPTION_DETAILS):
            for order,count in rotateOrders.iteritems():
                self._output_csv( ['transform', 'Rotate Order %s' % rotateOrderNames[order], count] )
            for limitType,count in limitTypes.iteritems():
                self._output_csv( ['transform', 'Used Limit %s' % limitType, count] )
        #}
        #-----------------------------------------------------------------

        #-----------------------------------------------------------------
        #{
        #  Check joints for the following conditions:
        #
        #        Scale with incoming connection(s)
        #        Translate with incoming connection(s)
        #        Shear with incoming connection(s)
        #        Non-Uniform scale (no incoming connection)
        #        Shear values at non-default values (no incoming connection)
        #
        jointNodes = cmds.ls( type='joint' )
        incomingCounts = {}
        nonUniformScaleCount = 0
        nonDefaultShearCount = 0
        children = {}
        children['scale'] = ['', 'X','Y','Z']
        children['translate'] = ['', 'X','Y','Z']
        children['shear'] = ['', 'XY','XZ','YZ']
        for node in jointNodes:
            for attr in ['scale', 'translate', 'shear']:
                aName = '%s.%s' % (node, attr)
                hasConnection = False
                for subAttr in children[attr]:
                    conn = cmds.listConnections( '%s%s' % (aName,subAttr), destination=False, source=True )
                    if conn != None:
                        hasConnection =True
                        incomingCounts[attr] = incomingCounts.get(attr,0) + 1
                        if self.option(OPTION_DETAILS):
                            self._output_csv( ['joint', 'Incoming Connection %s' % attr, node] )
                if not hasConnection and attr == 'scale':
                    scaling = cmds.getAttr( aName )[0]
                    if not analyticValues.__eq(scaling[0], scaling[1]) or not analyticValues.__eq(scaling[1], scaling[2]):
                        nonUniformScaleCount += 1
                        if self.option(OPTION_DETAILS):
                            self._output_csv( ['joint', 'Non-Uniform Scale', node] )
                elif not hasConnection and attr == 'shear':
                    shearValue = cmds.getAttr( aName )[0]
                    if not analyticValues.__eq3(shearValue, (0.0, 0.0, 0.0)):
                        nonDefaultShearCount += 1
                        if self.option(OPTION_DETAILS):
                            self._output_csv( ['joint', 'Non-Default Shear', node] )
        # Only print the summary if the details were not supplied.
        # The summary information can easily be calculated after-the-fact
        # if necessary.
        if not self.option(OPTION_DETAILS):
            for attr,count in incomingCounts.iteritems():
                self._output_csv( ['joint', 'Incoming Connection %s' % attr, count] )
            self._output_csv( ['joint', 'Non-Uniform Scale', nonUniformScaleCount] )
            self._output_csv( ['joint', 'Non-Default Shear', nonDefaultShearCount] )
        #}
        #-----------------------------------------------------------------

        #-----------------------------------------------------------------
        #{
        #  Check point constraints for the following conditions:
        #
        #        Non-default offset
        #
        pointConstraintNodes = cmds.ls( type='pointConstraint' )
        nonDefaultOffsetCount = 0
        for node in pointConstraintNodes:
            offsetValue = cmds.getAttr( '%s.offset' % node )[0]
            if not analyticValues.__eq3(offsetValue, (0.0, 0.0, 0.0)):
                nonDefaultOffsetCount += 1
                if self.option(OPTION_DETAILS):
                    self._output_csv( ['pointConstraint', 'Non-Default Offset', node] )

        # Only print the summary if the details were not supplied. The summary
        # information can easily be calculated after-the-fact if necessary.
        if not self.option(OPTION_DETAILS):
            self._output_csv( ['pointConstraint', 'Non-Default Offset', nonDefaultOffsetCount] )
        #}
        #-----------------------------------------------------------------

        #-----------------------------------------------------------------
        #{
        #  Check meshes for the following conditions:
        #
        #        displaySmoothMesh turned on
        #
        meshNodes = cmds.ls( type='mesh' )
        smoothMeshEnabledCount = 0
        for node in meshNodes:
            if cmds.getAttr( '%s.displaySmoothMesh' % node ):
                smoothMeshEnabledCount += 1
                if self.option(OPTION_DETAILS):
                    self._output_csv( ['mesh', 'Smooth Mesh Preview Enabled', node] )

        # Only print the summary if the details were not supplied. The summary
        # information can easily be calculated after-the-fact if necessary.
        if not self.option(OPTION_DETAILS):
            self._output_csv( ['mesh', 'Smooth Mesh Preview Enabled', smoothMeshEnabledCount] )
        #}
        #-----------------------------------------------------------------

    #======================================================================
    @classmethod
    def __eq( cls, leftValue, rightValue, eps=0.0001 ):
        """Simple implementation of a floating point 'equality'"""
        # Catch the 0 cases first since they mess up the adaptive log() trick
        if abs(leftValue) <= eps and abs(rightValue) > eps:
            return False
        if abs(rightValue) <= eps and abs(leftValue) > eps:
            return False
        if abs(rightValue) <= eps and abs(leftValue) <= eps:
            return True
        return abs(math.log( leftValue ) - math.log(rightValue)) <=  eps

    #======================================================================
    @classmethod
    def __eq3( cls, aVec, bVec, eps=0.0001 ):
        """Simple implementation of a floating point vector 'equality'"""
        for leftValue,rightValue in zip(aVec,bVec):
            if not cls.__eq(leftValue, rightValue, eps):
                return False
        return True

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
