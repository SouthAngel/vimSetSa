"""
Analytic class for examining DG connections
"""
import maya.cmds as cmds
from .BaseAnalytic import BaseAnalytic, OPTION_DETAILS, OPTION_SUMMARY
from .dg_utilities import plug_level_connections, node_type_hierarchy_list
from .decorators import addMethodDocs,addHelp,makeAnalytic

@addMethodDocs
@addHelp
@makeAnalytic
class analyticConnections(BaseAnalytic):
    """
    This analytic looks at all connections in the DG and reports on them.

    In full detail mode the CSV file consists of the following columns with
    one connection per row:
        Source           : Source plug of the connection
        Source Type      : Node type of the source plug's node
        Destination      : Destination plug of the connection
        Destination Type : Node type of the destination plug's node

    In regular mode the CSV file consists of the following columns with
    one node type per row:
        Node Type         : Type of node involved in connections
        Source Count      : Number of outgoing connections on nodes of that type
        Destination Count : Number of incoming connections on nodes of that type
    """
    def run(self):
        """
        Run the analytic and output the results.
        """
        if self.option(OPTION_DETAILS):
            self._output_csv( ['Source', 'Source Type', 'Destination', 'Destination Type'] )
        else:
            self._output_csv( ['Node Type', 'Source Count', 'Destination Count'] )

        # Get the type hierarchy information for looking up nodes
        node_types = node_type_hierarchy_list()

        # Ignore the undeletable nodes since they are the same in
        # every scene.
        all_nodes = cmds.ls( undeletable=False )
        all_nodes = all_nodes if all_nodes else []

        src_counts = {}
        dst_counts = {}
        type_list = {}
        connections_shown = {}
        for nodeIdx in range(0, len(all_nodes)/2):
            nodeName = all_nodes[nodeIdx]
            node_type = all_nodes[nodeIdx+1]
            (incoming_connections, outgoing_connections) = plug_level_connections( nodeName )
            for (src,dst) in incoming_connections:
                # Make sure the connection only shows up once. Every
                # connecton will show up at both the source and
                # destination node.
                if (src,dst) in connections_shown:
                    continue
                try:
                    dstType = node_types[cmds.nodeType(dst)]
                    if self.option(OPTION_DETAILS):
                        # src is a different node so it's not needed for the summary
                        srcType = node_types[cmds.nodeType(src)]
                        self._output_csv( [self._plug_name(src), srcType, self._plug_name(dst), dstType] )
                    else:
                        dst_counts[dstType] = dst_counts.get(dstType, 0) + 1
                        type_list[dstType] = True
                except Exception,ex:
                    self.error( 'Type of %s/%s not found (%s)' % (src, dst, str(ex)) )
            for (src,dst) in outgoing_connections:
                # Make sure the connection only shows up once. Every
                # connecton will show up at both the source and
                # destination node.
                try:
                    srcType = node_types[cmds.nodeType(src)]
                    if self.option(OPTION_DETAILS):
                        # All connections appear twice. In detailed mode
                        # it was already reported so skip it. Summary mode
                        # is only counting one side of the connection at a
                        # time so it won't skip.
                        if (src,dst) in connections_shown:
                            continue

                        # dst is a different node so it's not needed for the summary
                        dstType = node_types[cmds.nodeType(dst)]
                        self._output_csv( [self._plug_name(src), srcType, self._plug_name(dst), dstType] )
                    else:
                        src_counts[srcType] = src_counts.get(srcType, 0) + 1
                        type_list[srcType] = True
                except Exception,ex:
                    self.error( 'Type of %s/%s not found (%s)' % (src, dst, str(ex)) )

        # Mixed data with the summary of all connections on the node type -
        # merits converting to native JSON
        if self.option(OPTION_SUMMARY):
            for node_type in sorted(type_list.keys()):
                src_count = src_counts[node_type] if node_type in src_counts else 0
                dst_count = dst_counts[node_type] if node_type in dst_counts else 0
                self._output_csv( [node_type, src_count, dst_count] )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
