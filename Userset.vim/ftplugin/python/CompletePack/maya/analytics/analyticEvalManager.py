"""
Analytic class for examining evaluation manager information.

The information regarding the evaluation graph and scheduling information
for the current scene is output. The evaluation graph is updated before
dumping the information so it is guaranteed to be current. If no options
are selected the format shows the names of the nodes grouped by scheduling
types as well as a list of the node clusters created for scheduling.

    "BuildTime"      : GRAPH_BUILD_TIME_IN_MICROSECONDS
    "Parallel"       : [ LIST_OF_NODES_SCHEDULED_AS_PARALLEL ],
    "Serial"         : [ LIST_OF_NODES_SCHEDULED_AS_SERIAL ],
    "GloballySerial" : [ LIST_OF_NODES_SCHEDULED_AS_GLOBALLY_SERIAL ],
    "Untrusted"      : [ LIST_OF_NODES_SCHEDULED_AS_UNTRUSTED ]
    "Clusters"       : [ { CLUSTER_NAME : [ LIST_OF_NODES_IN_CLUSTER ] },
                         { CLUSTER_NAME : [ LIST_OF_NODES_IN_CLUSTER ] }
                         ...
                       ]
    The last is presented as an array of objects because the cluster
    names are not necessarily unique.

Options Available
    summary = Show a count of the various scheduling and cluster types
              in the graph. Appends this section to the above.

              "summary" : {
                  "Parallel" : COUNT_OF_PARALLEL_NODES,
                  "Serial" : COUNT_OF_SERIAL_NODES,
                  "GloballySerial" : COUNT_OF_GLOBALLY_SERIAL_NODES,
                  "Untrusted" : COUNT_OF_UNTRUSTED_NODES,
                  "Clusters" : [ COUNT_OF_NODES_PER_CLUSTER ]
              }

    details = Include all of the plug and connection information for each
              evaluation node. Instead of a list of node names each node
              will be an object containing plug and connection information:

              "NODE_NAME" : {
                 "inputPlugs"            : [ LIST_OF_INPUT_PLUGS_TO_DIRTY ],
                 "outputPlugs"           : [ LIST_OF_OUTPUT_PLUGS_TO_DIRTY ],
                 "affectsWorldPlugs"     : [ LIST_OF_WORLD_AFFECTING_PLUGS_TO_DIRTY ],
                 "upstreamConnections"   : [ LIST_OF_NODES_CONNECTED_UPSTREAM ],
                 "downstreamConnections" : [ LIST_OF_NODES_CONNECTED_DOWNSTREAM ]
              }

Example of a graph with two nodes in one cluster dumped with the 'summary' option:

    "output" : {
        "summary" : {
            "Parallel" : 1,
            "Serial" : 1,
            "GloballySerial" : 0,
            "Untrusted" : 0,
            "Clusters" : [1,1]
        },
        "BuildTime" : 12318,
        "Parallel" : [ "node1" ],
        "Serial" : [ "node2" ],
        "GloballySerial" : [],
        "Untrusted" : [],
        "Clusters" : [
            { "pruneRootsEvaluator" : [ "node1" ] },
            { "cacheEvaluator" : [ "node2" ] }
        ]
    }

The same graph with no options:

    output" : {
        "BuildTime" : 12318,
        "Parallel" : [ "node1" ],
        "Serial" : [ "node2" ],
        "GloballySerial" : [],
        "Untrusted" : [],
        "Clusters" : [
            { "pruneRootsEvaluator" : [ "node1" ] },
            { "cacheEvaluator" : [ "node2" ] }
        ]
    }

The same graph with both 'summary' and 'details' options:

    "output" : {
        "summary" : {
            "Parallel" : 1,
            "Serial" : 1,
            "GloballySerial" : 0,
            "Untrusted" : 0,
            "Clusters" : [1,1]
        },
        "BuildTime" : 12318,
        "Parallel" : {
            "node1" : {
                "inputPlugs" : [ "node1.i" ],
                "outputPlugs" : [ "node1.wm", "node1.pm" ],
                "affectsWorldPlugs" : [],
                "upstreamConnections" : [ "node2" ],
                "downstreamConnections" : []
                }
            },
        },
        "Serial" : {
            "node2" : {
                "inputPlugs" : [],
                "outputPlugs" : [ "node2.o" ],
                "affectsWorldPlugs" : [],
                "upstreamConnections" : [],
                "downstreamConnections" : [ "node1" ]
            }
        },
        "GloballySerial" : {},
        "Untrusted" : {},
        "Clusters" : [
            { "pruneRootsEvaluator" : ["node1"] },
            { "cacheEvaluator" : ["node2"] }
        ]
    }
"""
import maya.cmds as cmds
import os
import re
import json
from  maya.debug.emModeManager import emModeManager
from .BaseAnalytic import BaseAnalytic, OPTION_DETAILS, OPTION_SUMMARY
from .decorators import addMethodDocs,addHelp,makeAnalytic

#======================================================================

@addMethodDocs
@addHelp
@makeAnalytic
class analyticEvalManager(BaseAnalytic):
    """
    Create information specific to the evaluation manager:
        - list of nodes, plugs, and connections in the evaluation graph
        - scheduling type information for all nodes
    """
    PLUG_TYPES = ['input','output','affectsWorld']
    CONNECTION_TYPES = ['downstream','upstream']
    #======================================================================
    def __gather_summary_data(self, raw_json):
        """
        Extracts the summary data from the raw JSON output.

        raw_json: Dictionary containing all of the eval manager data for a node
        return:   Dictionary containing a dictionary of counts for all
                  scheduling and cluster types
                    {
                        'Parallel' : 0,
                        'Serial' : 0,
                        'GloballySerial' : 0,
                        'Untrusted' : 0,
                        'Clusters' : [0,0],
                    }
        """
        scheduling_summary = {}
        try:
            try:
                scheduling_list = raw_json['scheduling']
            except KeyError:
                scheduling_list = {}

            for (scheduling_type,scheduled_nodes) in scheduling_list.iteritems():
                # Empty lists are assumed to be scheduling types
                if len(scheduled_nodes) == 0:
                    scheduling_summary[scheduling_type] = 0
                    continue

                # Check the first element of the list to determine if further
                # recursion is necessary
                if type(scheduled_nodes[0]) is dict:
                    # This is a cluster list; output one count per cluster
                    scheduling_summary[scheduling_type] = scheduling_summary.get(scheduling_type,[])
                    for cluster in scheduled_nodes:
                        # Clusters should always be one key/value per object
                        # but looping over them is more robust.
                        for (_,cluster_nodes) in cluster.iteritems():
                            scheduling_summary[scheduling_type].append( len(cluster_nodes) )
                elif type(scheduled_nodes[0]) is str:
                    # This is a node list, output the length of the list
                    scheduling_summary[scheduling_type] = len(scheduled_nodes)
                elif type(scheduled_nodes[0]) is unicode:
                    # This is a node list, output the length of the list
                    scheduling_summary[scheduling_type] = len(scheduled_nodes)
                else:
                    self.error( 'Unrecognized scheduling data type on {}'.format(scheduled_nodes[0]) )

        except Exception,ex:
            self.error( 'Failed getting EM scheduling summary information ({})'.format(str(ex)) )

        return scheduling_summary

    #======================================================================
    def __gather_detail_data(self, raw_json):
        """
        Extracts the detailed` data from the raw JSON output.

        raw_json: Dictionary containing all of the eval manager data for a node
        return:   Dictionary containing a dictionary of {node:detailed_data}
        """
        node_details = {}
        try:
            try:
                plug_list = raw_json['plugs']
            except KeyError:
                plug_list = {}
            for (node,plug_types) in plug_list.iteritems():
                node_details[node] = {}
                for (plug_type,plug_type_list) in plug_types.iteritems():
                    node_details[node][plug_type+'Plugs'] = plug_type_list[:]

            try:
                connection_list = raw_json['connections']
            except KeyError:
                connection_list = {}
            for (node,connection_types) in connection_list.iteritems():
                node_details[node] = node_details.get(node,{})
                for (connection_type,connection_type_pairs) in connection_types.iteritems():
                    connection_key = connection_type+'Connections'
                    node_details[node][connection_key] = []
                    if connection_type == 'upstream':
                        for connection in connection_type_pairs:
                            node_details[node][connection_key] += [key for (key,value) in connection.iteritems()]
                    elif connection_type == 'downstream':
                        for connection in connection_type_pairs:
                            node_details[node][connection_key] += [value for (key,value) in connection.iteritems()]
                    else:
                        self.error( 'Unrecognized connection type: {}'.format( connection_type ) )
        except Exception,ex:
            self.error( 'Failed getting EM detailed connection information ({})'.format(str(ex)) )

        return node_details

    #======================================================================
    def __get_event_timing(self, event):
        """
        Use the profiler data to extract the timing taken by a named event.
        If more than one event of the given name exists only the first one
        will be used.

        Returns the amount of time, in microseconds, taken by the event
        """
        self.debug( 'Getting event timing for {}'.format(event) )
        event_time = 0
        try:
            re_event = re.compile( r'^(@[0-9]+)\s+=\s+{}$'.format(event) )
            tmp_dir = cmds.internalVar(userTmpDir=True)
            tmp_file = os.path.join( tmp_dir, '__PROFILER__.txt' )
            cmds.profiler( output=tmp_file )
            profiler_data = open( tmp_file, 'r' ).readlines()
            os.remove( tmp_file )

            found_event = None
            for line in profiler_data:
                if found_event is not None:
                    fields = line.split('\t')
                    if len(fields) > 4 and fields[1] == found_event:
                        self.debug( 'Found the timing' )
                        event_time = int(fields[4])
                        break
                else:
                    match = re_event.match(line)
                    if match:
                        self.debug( 'Found the event' )
                        found_event = match.group(1)
        except Exception, ex:
            self.error( 'Failed to get timing of event {}: {}'.format(event, ex) )

        return event_time

    #======================================================================
    def run(self):
        """
        Generates a JSON structure containing the evaluation graph information

        If the 'details' option is set then include the extra information as described
        in the analytic help information.
        """
        node_data = { 'BuildTime'      : 0,
                      'Parallel'       : {},
                      'Serial'         : {},
                      'GloballySerial' : {},
                      'Untrusted'      : {}
                      }
        node_counts = { scheduling_type:0 for scheduling_type in node_data.keys() }

        try:
            with emModeManager() as em_manager:

                # Rebuild the graph in parallel mode, then extract the schedulingGraph event
                # timing from it, which is the root level timing event for graph rebuilding.
                # (The rebuild also counts invalidation and redraw time so that can't be used as-is.)
                em_manager.setMode( 'emp' )

                self.debug( 'Getting profiler information' )
                cmds.profiler( sampling=True )
                em_manager.rebuild()
                cmds.profiler( sampling=False )
                node_data['BuildTime'] = self.__get_event_timing( 'GraphConstruction' )
                self.debug( 'Got the sample time of {}'.format( node_data['BuildTime'] ) )

                em_json = None
                try:
                    graph_data = cmds.dbpeek( operation='graph', all=True, evaluationGraph=True,
                                              argument=['plugs','connections','scheduling'] )
                    em_json = json.loads( graph_data )
                except Exception, ex:
                    self.warning( 'First evaluation failed, forcing time change for second attempt ({})'.format(ex) )
                    # If the first attempt to get the graph fails maybe the
                    # rebuild didn't work so force it the old ugly way for
                    # now.
                    now = cmds.currentTime(query=True)
                    cmds.currentTime( now + 1 )
                    cmds.currentTime( now )

                if em_json is None:
                    # Second chance to get the graph data. This one is not
                    # protected by an inner try() because if this fails we
                    # want the outer exception handler to kick in.
                    graph_data = cmds.dbpeek( operation='graph', all=True, evaluationGraph=True,
                                              argument=['plugs','connections','scheduling'] )
                    em_json = json.loads( graph_data )

            if self.option(OPTION_SUMMARY):
                # Gather node summary information if requested
                summary_info = self.__gather_summary_data(em_json)
                node_data['summary'] = summary_info

            # Gather node detail information if requested
            detailed_info = self.__gather_detail_data(em_json) if self.option(OPTION_DETAILS) else {}

            # Relies on the fact that the scheduling output keys match the
            # ones being put into the node_data dictionary, which they do by
            # design.
            for (scheduling_type, scheduling_list) in em_json['scheduling'].iteritems():
                try:
                    node_counts[scheduling_type] = len(scheduling_list)
                    # Any extra scheduling information is for detailed output only
                    if scheduling_type not in node_data.keys():
                        if self.option(OPTION_DETAILS):
                            node_data[scheduling_type] = scheduling_list
                        if self.option(OPTION_SUMMARY):
                            node_counts[scheduling_type] = node_counts.get(scheduling_type,0) + len(scheduling_list)
                        continue

                    # The simplest output will just have the nodes of each
                    # type in a list.
                    if not self.option(OPTION_SUMMARY) and not self.option(OPTION_DETAILS):
                        node_data[scheduling_type] = scheduling_list
                        continue

                    node_data[scheduling_type] = {}
                    for node in scheduling_list:
                        node_info = {}

                        # Add in the detailed information if requested
                        if node in detailed_info:
                            node_info.update( detailed_info[node] )

                        # Attach the node data to its name
                        node_data[scheduling_type][self._node_name(node)] = node_info

                except Exception, ex:
                    # There may be a formatting problem if scheduling types
                    # are not found since they will be dumped even if empty.
                    self.warning( 'Node information not available for type {} ({})'.format(scheduling_type, ex) )

        except Exception, ex:
            # If there is no animation there will be no evaluation graph
            self.warning( 'No Evaluation Manager information available ({})'.format(ex) )

        return node_data

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
