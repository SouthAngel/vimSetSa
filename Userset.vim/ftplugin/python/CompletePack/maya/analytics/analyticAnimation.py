"""
Analytic class for examining animation data
"""
import maya.cmds as cmds
from .BaseAnalytic import BaseAnalytic, OPTION_DETAILS, OPTION_SUMMARY
from .decorators import addMethodDocs,addHelp,makeAnalytic

@addMethodDocs
@addHelp
@makeAnalytic
class analyticAnimation(BaseAnalytic):
    """
    Analyze the volume and distribution of animation data.
    """
    # Define the JSON dictionary key values to be used
    KEY_STATIC = 'static'
    KEY_NON_STATIC = 'nonStatic'
    KEY_MAYBE_STATIC = 'maybeStatic'
    KEY_DRIVEN = 'driven'
    KEY_MULTI_DRIVEN = 'multiDriven'
    KEY_NO_DRIVEN = 'noDriven'
    KEY_KEYFRAMES = 'keyframes'

    def run(self):
        """
        Examine the animation in the system and gather some basic statistics
        about it. There are two types of animation to find:

            1) Anim curves, which animate in the usual manner
               Care is taken to make sure either time is either an explicit or
               implicit input since anim curves could be used for reasons
               other than animation (e.g. setDrivenKey)
            2) Any other node which has the time node as input
               Since these are pretty generic we can only take note of how
               many of these there are, and how many output connections they
               have.

        The summary data consists of a count of the static and non-static
        param curves. Any curve with an input to the time parameter is
        considered non-static since the time may warp and it's more difficult
        than it's worth to figure out if this is the case.

        Example of a normal dump for a simple scene:

        "output" : {
            "static"      : { "animCurveTL" : 4, "animCurveTA" : 1 },
            "nonStatic"   : { "animCurveTL" : 126, "animCurveTA" : 7 },
            "maybeStatic" : { "expression" : 1 },
            "keys"        : { "animCurveTL" : 7200, "animCurveTA" : 43 }
            "driven"      : { "animCurveTL" : { 1 : 7200 },
                              "animCurveTA" : { 1 : 42, 2 : 1 }
                              "expression"  : { 1 : 1 } }
        }

            "static"      : Count of animation nodes with the same value at all times
            "nonStatic"   : Count of animation nodes with differing values at some times
            "maybeStatic" : Count of animation nodes whose values could not be ascertained
            "keys"        : Count of keyframes, where appropriate.
            "driven"      : Count of number of nodes driving various numbers of outputs
                            e.g. { 1 : 7, 2 : 1 } means 7 nodes driving a single output and
                                 1 node driving 2 outputs

        and the same scene with the 'summary' option enabled:

        "output" : {
            "summary" :
            {
                "static"       : 5,
                "nonStatic"    : 133,
                "maybeStatic"  : 1,
                "keys"         : 7243,
                "animCurveTL"  : 130,
                "animCurveTA"  : 8,
                "multiDriven"  : 1,
                "noDriven"     : 0,
                "expression"   : 1
            },
            "static"      : { "animCurveTL" : 4, "animCurveTA" : 1 },
            "nonStatic"   : { "animCurveTL" : 126, "animCurveTA" : 7 }
            "maybeStatic" : { "expression" : 1 }
            "keyframes"   : { "animCurveTL" : 7200, "animCurveTA" : 43 }
            "driven"      : { "animCurveTL" : { 1 : 7200 },
                              "animCurveTA" : { 1 : 42, 2 : 1 }
                              "expression"  : { 1 : 1 } }
        }

        For the summary the "multiDriven" value means "the number of
        animation nodes driving more than one outputs", and "noDriven" means
        "the number of animation nodes not driving any outputs".

        The additional NODE_TYPE counts indicate the number of nodes of each
        animation node type in the scene. The other summary values are a count
        of the data of that type. All of the summary information is available
        within the normal data, this is just a convenient method of accessing.

        When the 'details' option is on then the fully detailed information about
        all animation curves is added. Here is a sample for one curve:

            "static" :
            {
                "animCurveTL" :
                {
                    "nurbsCone1_translateX" :
                    {
                        "keyframes" : [ [1.0,1.0], [10.0,10.0] ],
                        "driven"    : {"group1.tx" : "transform"}
                    }
                }
            },
            "nonStatic" :
            {
                ...
            },
            "maybeStatic" :
            {
                ...
            }

            The data is nested as "type of animation" over "type of animation
            node" over "animation node name". Inside each node are these
            fields:

            "driven"    : Keyed on plugs on the destination end of the animation,
                          values are the type of said node
            "keyframes" : [Key,Value] pairs for the animation keyframes.
                          an animCurve. For expressions et. al. the member
                          will be omitted.

        Return True if the analysis succeeded, else False
        """
        # This will be the total animation data for the scene,
        # to be returned when complete.
        scene_data = {}

        # Summary data. Some is collected as we go, some is added in at the end.
        summary_data = {}

        # Normal data to be collected. Collected when either the summary
        # option is on, since the normal data will provide the summary counts,
        # or the detail option is off when the data is structured differently.
        static_node_types = {}
        non_static_node_types = {}
        maybe_static_node_types = {}
        keys_on_node_types = {}
        driven_by_node_types = {}
        nodes_of_type = {}

        # First pass, get all interesting animation curves
        anim_curves = cmds.ls( type='animCurve' )
        if not anim_curves:
            # Warn but continue since there might be other animation node types
            self.warning( 'No anim curves in this scene' )

        for anim_curve in anim_curves:
            # If time isn't in this curve's immediate history then it's
            # not animation so skip it. (Time warps will be reported as
            # animating the anim_curve(s) they drive.)
            time_input = cmds.listConnections( anim_curve + '.input', destination=False, source=True )
            if time_input and ('time' != cmds.nodeType(time_input[0])):
                continue

            try:
                anim_curve_node_type = cmds.nodeType( anim_curve )
                summary_data[anim_curve_node_type] = summary_data.get(anim_curve_node_type,0) + 1
                keyframe_count = cmds.keyframe(anim_curve,query=True,keyframeCount=True)
                really_animated = self.__is_really_animated(anim_curve)

            except Exception, ex:
                raise ex

            # Get the driven node information
            driven_node_list = cmds.listConnections( anim_curve, skipConversionNodes=True,
                                                     destination=True, source=False )

            # Update the main data if it's needed for summary or no detail was
            # requested.
            if self.option(OPTION_SUMMARY) or not self.option(OPTION_DETAILS):
                nodes_of_type[anim_curve_node_type] = nodes_of_type.get(anim_curve_node_type,0) + 1

                keys_on_node_types[anim_curve_node_type] = keys_on_node_types.get(anim_curve_node_type,0) + keyframe_count

                if really_animated:
                    non_static_node_types[anim_curve_node_type] = non_static_node_types.get(anim_curve_node_type,0) + 1
                else:
                    static_node_types[anim_curve_node_type] = static_node_types.get(anim_curve_node_type,0) + 1

                # Driven node totals are a little more complicated since they
                # are stored as a dictionary with the key being the driven node count.
                if driven_node_list:
                    driven_by_node_types[anim_curve_node_type] = driven_by_node_types.get(anim_curve_node_type,{})
                    this_driven_data = driven_by_node_types[anim_curve_node_type]
                    driven_count = len(driven_node_list)
                    this_driven_data[driven_count] = this_driven_data.get(driven_count,0) + 1

            # If the details are requested then build up the per-node data in
            # the JSON structure as described above.
            if self.option(OPTION_DETAILS):
                keyframes = cmds.keyframe(anim_curve,valueChange=True,timeChange=True,query=True)
                anim_curve_data = { self.KEY_KEYFRAMES : zip(keyframes[::2],keyframes[1::2]) }

                # If driven nodes exist add their data, otherwise leave that
                # section empty.
                if driven_node_list:
                    anim_curve_data[self.KEY_DRIVEN] = {}
                    for driven_node in driven_node_list:
                        driven_node_type = cmds.nodeType( driven_node )
                        anim_curve_data[self.KEY_DRIVEN][self._node_name(driven_node)] = driven_node_type

                # Now decide the section to receive this node data based on animation type
                if really_animated:
                    scene_data[self.KEY_NON_STATIC] = scene_data.get(self.KEY_NON_STATIC,{})
                    type_data = scene_data[self.KEY_NON_STATIC]
                else:
                    scene_data[self.KEY_STATIC] = scene_data.get(self.KEY_STATIC,{})
                    type_data = scene_data[self.KEY_STATIC]
                type_data[anim_curve_node_type] = type_data.get(anim_curve_node_type, {})
                type_data[anim_curve_node_type][self._node_name(anim_curve)] = anim_curve_data

        # Now grab everything connected to the time node output that's not
        # already handled above. Only the direct connections (modulo unit
        # conversion nodes) are considered since the rest is animated but
        # not animation, a subtle but important difference.
        timeNode = cmds.ls( type='time' )[0]
        timed_nodes = cmds.listConnections( '%s.outTime' % timeNode
                                          , skipConversionNodes=True
                                          , destination=True
                                          , source=False )
        if timed_nodes:
            for node in timed_nodes:
                # It's possible for anim curves to be directly driven by the
                # time node but those have already been handled above.
                if node in anim_curves:
                    continue

                node_type = cmds.nodeType( node )

                # Get the driven node information
                driven_node_list = cmds.listConnections( node, skipConversionNodes=True,
                                                         destination=True, source=False )

                # Update the main data if it's needed for summary or no detail was
                # requested.
                if self.option(OPTION_SUMMARY) or not self.option(OPTION_DETAILS):
                    keys_on_node_types[node_type] = 0
                    nodes_of_type[node_type] = nodes_of_type.get(node_type,0) + 1
                    maybe_static_node_types[anim_curve_node_type] = maybe_static_node_types.get(anim_curve_node_type,0) + 1

                    # Driven node totals are a little more complicated since they
                    # are stored as a dictionary with the key being the driven node count.
                    if driven_node_list:
                        driven_by_node_types[node_type] = driven_by_node_types.get(node_type,{})
                        this_driven_data = driven_by_node_types[node_type]
                        driven_count = len(driven_node_list)
                        this_driven_data[driven_count] = this_driven_data.get(driven_count,0) + 1

                # If the details are requested then build up the per-node data for
                # this animation node
                if self.option(OPTION_DETAILS):
                    node_data = {}

                    # No keyframe information for these other node types since
                    # there isn't a specific meaning for it.

                    # If driven nodes exist add their data, otherwise leave that
                    # section empty.
                    if driven_node_list:
                        node_data[self.KEY_DRIVEN] = {}
                        for driven_node in driven_node_list:
                            driven_node_type = cmds.nodeType( driven_node )
                            node_data[self.KEY_DRIVEN][self._node_name(driven_node)] = driven_node_type

                    # Static is not ascertainable since the input varies with the
                    # time but it's possible that the node will not change its output.
                    scene_data[self.KEY_MAYBE_STATIC] = scene_data.get(self.KEY_MAYBE_STATIC,{})
                    type_data = scene_data[self.KEY_MAYBE_STATIC]
                    type_data[node_type] = type_data.get(node_type, {})
                    type_data[node_type][self._node_name(node)] = node_data

        if self.option(OPTION_SUMMARY):
            # Gather node summary information if requested
            summary_data[self.KEY_STATIC] = sum(static_node_types.values())
            summary_data[self.KEY_NON_STATIC] = sum(non_static_node_types.values())
            summary_data[self.KEY_MAYBE_STATIC] = sum(maybe_static_node_types.values())
            summary_data[self.KEY_KEYFRAMES] = sum(keys_on_node_types.values())

            total_no_driven = 0
            total_multi_driven = 0
            for driven_data in driven_by_node_types.values():
                for (driven_count,driven_per_count) in driven_data.iteritems():
                    if driven_count == 0:
                        total_no_driven += driven_per_count
                    elif driven_count > 1:
                        total_multi_driven += driven_per_count
            summary_data[self.KEY_MULTI_DRIVEN] = total_multi_driven
            summary_data[self.KEY_NO_DRIVEN] = total_no_driven

            scene_data['summary'] = summary_data

        # This data is embedded at a deeper level when the detail option is set
        if not self.option(OPTION_DETAILS):
            scene_data[self.KEY_KEYFRAMES] = keys_on_node_types
            scene_data[self.KEY_DRIVEN] = driven_by_node_types

        return scene_data

    #======================================================================
    @classmethod
    def __is_zero(cls,potentialZero):
        """
        Simple near-zero check for floats
        """
        return abs(potentialZero) <= 0.001

    #======================================================================
    @classmethod
    def __is_really_animated(cls,the_curve):
        """
        Check to see if the animation curve takes on more than one value over time.
        the_curve : Anim curve to check
        Returns True if the curve does vary
        """
        try:
            if len(cmds.ls( the_curve, type='animCurve' )) == 0:
                # It's too difficult to figure out if non-anim_curves are really
                # animated so we'll err on the side of caution.
                return False
        except TypeError:
            # Return could be None
            return False

        # Tangents with angles below this value will be considered flat
        angleTol = 0.001

        # Go through the keyframes on the current animation-curve and get in_angle and out_angle
        in_angle = cmds.keyTangent( the_curve, query=True, inAngle=True )
        in_angle = in_angle if in_angle else []
        out_angle = cmds.keyTangent( the_curve, query=True, outAngle=True )
        out_angle = out_angle if out_angle else []
        out_tan_type = cmds.keyTangent( the_curve, query=True, outTangentType=True )
        out_tan_type = out_tan_type if out_tan_type else []

        # Make in_angle and out_angle absolute values, for less work on the comparison
        in_angle = [abs(x) for x in in_angle]
        out_angle = [abs(x) for x in out_angle]

        # Get each keyed frame, and get the value of each keyed frame
        keyed_frames = cmds.keyframe( the_curve, query=True, timeChange=True )
        keyed_frames = keyed_frames if keyed_frames else []
        keyed_values = cmds.keyframe( the_curve, query=True, valueChange=True )
        keyed_values = keyed_values if keyed_values else []

        # For each keyframe on the animation curve check for non-flat keys
        for key_num in range(0, len(keyed_frames)):
            # Get the outTangentType of the previuos frame, the current frame,
            # and the next frame. Keyframes past the endpoints are considered
            # stepped if the endpoints themselves are.
            #
            stepped = (out_tan_type[key_num] == "step")
            stepped = stepped and ((key_num==0) or (out_tan_type[key_num-1] == "step"))
            stepped = stepped and ((key_num+1 >= len(keyed_frames)) or (out_tan_type[key_num+1] == "step"))

            # If stepped or the angles are flat check the values
            if (stepped
                or (    ((key_num == 0) or cls.__is_zero(out_angle[key_num-1]))
                    and  (in_angle[key_num] < angleTol)
                    and  (out_angle[key_num] < angleTol)
                    and  ((key_num+1 >= len(keyed_frames)) or cls.__is_zero(in_angle[key_num+1])) ) ):
                # Get the difference of the value of the current attribute between
                # the previous frame and the current frame
                if key_num > 0:
                    prev_val_diff = abs(keyed_values[key_num-1] - keyed_values[key_num])
                else:
                    prev_val_diff = 0
                # Get the difference of the value of the current attribute between
                # the current frame and the next frame
                if key_num+1 < len(keyed_values):
                    next_val_diff = abs(keyed_values[key_num+1] - keyed_values[key_num])
                else:
                    next_val_diff = 0

                # If there is a flat step tangent or the values before and after
                # the keyframe are the same as at the keyframe then this is a
                # flat area of the curve.
                if (  not cls.__is_zero(prev_val_diff)
                   or (not stepped and not cls.__is_zero(next_val_diff)) ):
                    return True

        return False

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
