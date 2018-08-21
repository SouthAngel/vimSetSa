"""
Utility to read and analyze dependency graph or evaluation graph structure
information. Allows you to produce a visualization of a single graph, a
text comparision of two graphs, or a merged comparison of two graphs.

    from maya.debug.graphStructure import graphStructure

    # Store the current scene's graph structure in a file
    g = graphStructure()
    g.write( 'FileForGraph.dg' )

    # Get a new scene and get its structure directly
    cmds.file( 'MyTestFile.ma', force=True, open=True )
    graph1 = graphStructure()

    # Retrieve the stored graph structure
    graph2 = graphStructure( structure_file_name='FileForGraph.dg' )

    # Compare them to see if they are the same
    if not graph1.compare(graph2):
        print 'Oh noooes, the graph structure has changed!'
        # Now visualize the differences
        graph1.compare_as_dot(graph2, structure_file_name='GraphCompare.dot', show_only_differences=True)
"""

__all__ = ['graphStructure']

import sys
import json

# JSON keywords used in parsing the dbpeek output
KEY_CONNECTIONS  = 'connections'   # Plug list for dbpeek(op='graph', a='connections')
KEY_NODES        = 'nodes'         # Plug list for dbpeek(op='graph', a='nodes')
KEY_PLUGS        = 'plugs'         # Plug list for dbpeek(op='graph', a='plugs')
KEY_PLUGS_INPUT  = 'input'         # Sub list of KEY_PLUGS for input plugs
KEY_PLUGS_OUTPUT = 'output'        # Sub list of KEY_PLUGS for output plugs
KEY_PLUGS_WORLD  = 'affectsWorld'  # Sub list of KEY_PLUGS for plugs affecting worldspace
KEY_ADDED        = 'added'         # List of entries added in a comparison
KEY_REMOVED      = 'removed'       # List of entries removed in a comparison

#======================================================================
#
# Structure analysis of offline files will work without Maya running so
# use the maya import to dynamically detect what can and can't be done here.
#
try:
    import maya.cmds as cmds
    MAYA_IS_AVAILABLE = True
except ImportError:
    MAYA_IS_AVAILABLE = False
def checkMaya():
    '''Check to see if Maya Python libraries are available'''
    if MAYA_IS_AVAILABLE:
        return True
    print 'ERROR: Cannot perform this operation unless Maya is available'
    return False

#======================================================================
#
def split_connection(connection):
    """
    Extract the name of a node and its attribute specification from
    one side of a connection.
    """
    parts = connection.split('.', 1)
    if len(parts) == 2:
        return (parts[0], parts[1])
    return (parts[0], '')

#######################################################################

class DotFormatting(object):
    """
    Encapsulation of all of the .dot formatting decisions made for this
    type of graph output.
    """
    # Dotted and Red for elements only in graph 1
    style_a_not_b = 'penwidth="1.0", style="dotted", color="#CC0000", fontcolor="#CC0000"'

    # Bold and Green for elements only in graph 2
    style_b_not_a = 'penwidth="4.0", style="solid", color="#127F12", fontcolor="#127F12"'

    # Thin and black for elements in both graphs
    style_a_and_b = 'penwidth="1.0", style="solid", color="#000000", fontcolor="#000000"'

    # Thin and grey for elements unchanged but required for context
    style_context = 'penwidth="1.0", style="solid", color="#CCCCCC", fontcolor="#CCCCCC"'

    # Legend is only needed for comparison, and one line is only required for
    # context when only the differences are being shown
    legend_fmt = """    {
        rank = sink ;
        node [shape=box] ;
        __bothGraphs [label="In both graphs", %s] ;
        __aButNotb [label="In graph 1 but not graph 2", %s] ;
        __bButNota [label="In graph 2 but not graph 1", %s] ;
        %%s
    }""" % (style_a_and_b, style_a_not_b, style_b_not_a)
    legend_compare = legend_fmt % ''
    label = '__context [label="In both graphs, shown for context", %s] ;' % style_context
    legend_compare_only_differences = legend_fmt % label

    #======================================================================
    #
    def __init__(self, long_names=False):
        """
        If long_names is True then don't attempt to shorten the node names by
        removing namespaces and DAG path elements.
        """
        self.use_long_names = long_names

    #======================================================================
    #
    def nodeLabel(self, node):
        """
        Provide a label for a node. Uses the basename if use_long_names is not
        turned on, otherwise the full name.

        e.g.  Original:   grandparent|parent:ns1|:child
              Label:      child
        """
        if self.use_long_names:
            return node
        name_list = node.split(':')
        return name_list[-1]

    #======================================================================
    @staticmethod
    def header():
        """
        Print this only once, at the beginning of the .dot file
        """
        return 'digraph G\n{\n\tnslimit = 1.0 ;\n\tsize = "7.5,10" ;\n'

    #======================================================================
    @staticmethod
    def legend(dot_file):
        """
        Print out a legend node. In the case of a graph dump this is only
        the title, containing the name of the file analyzed.
        """
        return '\n\tlabelloc="b" ;\n\tlabel="%s" ;\n' % dot_file

    #======================================================================
    @staticmethod
    def legend_for_compare(file1, file2, show_only_differences):
        """
        Print out a legend node showing the formatting information for a
        comparison of two graphs.
        """
        sub_title = ''
        if show_only_differences:
            sub_title = '\\n(showing changes only)'

        legend = DotFormatting.legend_compare
        if show_only_differences:
            legend = DotFormatting.legend_compare_only_differences
        return '\n%s\n\tlabelloc="b" ;\n\tlabel="Graph 1 = %s\\nGraph 2 = %s%s" ;\n' % (legend, file1, file2, sub_title)

    #======================================================================
    @staticmethod
    def footer():
        """
        Print this only once, at the end of the .dot file
        """
        return '}\n'

    #======================================================================
    @staticmethod
    def simple_node_format():
        """
        Print out the formatting instruction to make nodes the default format.
        """
        return '\n\tnode [shape="ellipse", %s] ;\n' % DotFormatting.style_a_and_b

    #======================================================================
    @staticmethod
    def context_node_format():
        """
        Print out the formatting instruction to make nodes visible in the
        comparison graph but faded to indicate that they are actually the
        same and only present for context.
        """
        return '\n\tnode [shape="ellipse", %s] ;\n' % DotFormatting.style_context

    #======================================================================
    def node(self, node):
        """
        Print out a graph node with a simplified label.
        """
        node = node.replace( '"', '\\"' )
        return '\t"%s" [label="%s"] ;\n' % (node, self.nodeLabel(node) )

    #======================================================================
    @staticmethod
    def altered_node_format(inOriginal):
        """
        Print out formatting instruction for nodes that were in one graph
        but not the other. If inOriginal is True the nodes were in the
        original graph but not the secondary one, otherwise vice versa.
        """
        if inOriginal:
            nodeFormat = DotFormatting.style_a_not_b
        else:
            nodeFormat = DotFormatting.style_b_not_a
        return '\n\tnode [%s] ;\n' % nodeFormat

    #======================================================================
    @staticmethod
    def simple_connection(src, dst):
        """
        Print out a simple connection
        """
        src = src.replace( '"', '\\"' )
        dst = dst.replace( '"', '\\"' )

        # Only use the node names for the connection for now since
        # creating graph nodes for every attribute doesn't give a
        # realistic view of connectivity (internal attribute dependencies
        # are not accounted for)
        try:
            (src_node,src_plug) = split_connection( src )
            (dst_node,dst_plug) = split_connection( dst )
        except Exception, ex:
            print 'WARN: Could not connect %s to %s : "%s"' % (src, dst, str(ex))
            return ''

        connection_format = ''
        if len(src_plug) > 0 or len(dst_plug) > 0:
            connection_format = '[ label="%s" ]' % ("%s -> %s" % (src_plug, dst_plug))
        return '\t"%s" -> "%s" %s;\n' % (src_node, dst_node, connection_format)

    #======================================================================
    @staticmethod
    def altered_connection(src, dst, inOriginal):
        """
        Print out code for a connection that was in one graph but not the other.
        If inOriginal is True the connection was in the original graph but not
        the secondary one, otherwise vice versa.
        """
        src = src.replace( '"', '\\"' )
        dst = dst.replace( '"', '\\"' )
        if inOriginal:
            connection_format = DotFormatting.style_a_not_b
        else:
            connection_format = DotFormatting.style_b_not_a

        # Only use the node names for the connection for now since
        # creating graph nodes for every attribute doesn't give a
        # realistic view of connectivity (internal attribute dependencies
        # are not accounted for)
        try:
            (src_node,src_plug) = split_connection( src )
            (dst_node,dst_plug) = split_connection( dst )
        except Exception, ex:
            print 'WARN: Could not connect %s to %s : "%s"' % (src, dst, str(ex))
            return ''

        if len(src_plug) > 0 or len(dst_plug) > 0:
            connection_format = 'label="%s", %s' % ("%s -> %s" % (src_plug, dst_plug), connection_format)
        return '\t"%s" -> "%s" [ %s ];\n' % (src_node, dst_node, connection_format)

#######################################################################

class graphStructure(object):
    """
    Provides access and manipulation on graph structure data that has been
    produced by the 'dbpeek -op graph' or 'dbpeek -op evaluation_graph' commands.
    """
    #======================================================================
    def __init__(self, structure_file_name=None, long_names=False,
                       evaluation_graph=False, inclusions=['connections']):
        """
        Create a graph structure object from a file or the current scene.

        The graph data is read in and stored internally in a format that makes
        formatting and comparison easy.

        structure_file_name: if 'None' then the current scene will be used,
        otherwise the named file will be read.

        long_names: if True then don't attempt to shorten the node names by
        removing namespaces and DAG path elements.

        evaluation_graph: if True then get the structure of the evaluation
        manager graph, not the DG. This requires that the graph has already
        been created of course, e.g. by playing back a frame or two in EM
        serial or EM parallel mode.

        inclusions: A list representing which parts of the graph to include
        in the structure information. Valid members are the argument types
        to the dbpeek(op='graph') command:
            'nodes'       : List of nodes in the graph
            'plugs'       : DG mode - List of networked plugs
                            (not so useful as these are at the whim of the DG)
                            EM mode - List of plugs to dirty
            'connections' : List of connections in the graph
            'scheduling'  : DG mode - Scheduling types for the nodes
                            EM mode - Scheduling types plus the list of
                            clusters and the nodes they control during
                            evaluation.

        The more inclusions there are the slower any comparison will be so
        keep the amount of data collected to a minimum if you are concerned
        about performance. For simple graph structure verification a good
        minimal set is just the connection values.
        """
        self.use_long_names = long_names
        self.evaluation_graph = evaluation_graph
        self.inclusions = inclusions
        self.name = ''
        self.nodes = []
        self.plugs_in = []
        self.plugs_out = []
        self.plugs_other = []
        self.plugs_world = []
        self.connections = []
        self.raw_json = {}
        self.operation = None   # The operation that created the graph to be compared

        if structure_file_name == None:
            self.__init_from_scene()
        else:
            self.__init_from_file(structure_file_name)

    #======================================================================
    def current_graph(self):
        """
        Returns a new graphStructure object with all of the same options as
        this one, except that it will always use the current scene even if
        the original came from a file.
        """
        return graphStructure( structure_file_name=None, long_names=self.use_long_names,
                       evaluation_graph=self.evaluation_graph, inclusions=self.inclusions )

    #======================================================================
    def __init_from_json(self, json_string):
        """
        Initialize the graph structure information from the raw JSON obtained
        from the dbpeek command (or file contents with the equivalent).
        """
        self.nodes = []
        self.plugs_in = []
        self.plugs_out = []
        self.plugs_world = []
        self.connections = []

        try:
            self.raw_json = json.loads( json_string )
        except Exception, ex:
            print 'ERROR: Could not parse raw JSON ({0:s})'.format( ex )

        try:
            self.nodes = self.raw_json[KEY_NODES]
        except Exception, ex:
            # If the nodes weren't included then of course they are not present
            if KEY_NODES in self.inclusions:
                print 'ERROR: Could not parse graph node list ({0:s})'.format( ex )

        if self.evaluation_graph:
            try:
                plug_json = self.raw_json[KEY_PLUGS]
                for (node, plug_dictionary) in plug_json.iteritems():
                    self.plugs_in += ['{0:s}.{1:s}'.format(node,p) for p in plug_dictionary[KEY_PLUGS_INPUT]]
                    self.plugs_out += ['{0:s}.{1:s}'.format(node,p) for p in plug_dictionary[KEY_PLUGS_OUTPUT]]
                    self.plugs_world += ['{0:s}.{1:s}'.format(node,p) for p in plug_dictionary[KEY_PLUGS_WORLD]]
            except Exception, ex:
                # If the plugs weren't included then of course they are not present
                if KEY_PLUGS in self.inclusions:
                    print 'ERROR: Could not parse graph plug list ({0:s})'.format( ex )

        try:
            # The same connections will appear as both an upstream connection
            # and a downstream connection (usually on different nodes). Only
            # one is needed for comparison so arbitrarily choose downstream.
            for (_,node_connections) in self.raw_json[KEY_CONNECTIONS].iteritems():
                # downstream connections will be a list of {src:dst} pairs.
                for connections in node_connections['downstream']:
                    # There should only be one item in each dictionary but
                    # iterate anyway to be safe. The main reason these are
                    # dictionaries is because JSON doesn't support tuples.
                    self.connections += ['{} {}'.format(src,dst) for (src,dst) in connections.iteritems()]
        except Exception, ex:
            # If the plugs weren't included then of course they are not present
            if KEY_CONNECTIONS in self.inclusions:
                print 'ERROR: Could not parse graph connection list ({0:s})'.format( ex )

    #======================================================================
    def __init_from_scene(self):
        """
        Create a graph structure object from the current Maya scene.
        """
        if not checkMaya():
            return
        self.name = '__SCENE__'
        args = self.inclusions

        if self.evaluation_graph:
            args.append( 'evaluationGraph' )

        self.__init_from_json(cmds.dbpeek(operation='graph', all=True, argument=args))

    #======================================================================
    def __init_from_file(self, structure_file_name):
        """
        Create a graph structure object from contents of the given file.
        Data in the file will be JSON format, derived directly from the
        output of the dbpeek command using the 'graph' operation.
        """
        self.name = structure_file_name
        try:
            structure_file = open(structure_file_name, 'r')
            self.__init_from_json( structure_file.read() )
            structure_file.close()
        except Exception, ex:
            print 'ERROR: Could not parse structure file {0:s} ({1:s})'.format( structure_file_name, ex )

    #======================================================================
    def write(self, fileName=None):
        """
        Dump the graph in the .dg format it uses for reading. Useful for
        creating a dump file from the current scene, or just viewing the
        graph generated from the current scene. If the fileName is specified
        then the output is sent to that file, otherwise it goes to stdout.
        """
        out = sys.stdout
        if fileName:
            out = open(fileName, 'w')

        # Add some indentation so that the file is somewhat human readable
        out.write( json.dumps( self.raw_json, indent=4 ) )
        out.close()

    #======================================================================
    def write_as_dot(self, fileName=None):
        """
        Dump the graph in .dot format for visualization in an application
        such as graphViz. If the fileName is specified then the output is
        sent to that file, otherwise it is printed to stdout.

        Plugs have no dot format as yet.
        """
        out = sys.stdout
        if fileName:
            out = open(fileName, 'w')
        dot = DotFormatting(self.use_long_names)

        out.write( dot.header() )
        out.write( dot.legend(self.name) )

        out.write( dot.simple_node_format() )
        for node in self.nodes:
            out.write( dot.node(node) )

        # Plugs have no output method as yet

        for connection in self.connections:
            (src,dst) = connection.split(' ')
            out.write( dot.simple_connection(src, dst) )

        out.write( dot.footer() )

    #======================================================================
    def compare_as_dot(self, other, fileName=None, show_only_differences=False):
        """
        Compare this graph structure against another one and print out a
        .dot format for visualization in an application such as graphViz.

        The two graphs are overlayed so that the union of the graphs is
        present. Colors for nodes and connetions are:

            Black      : They are present in both graphs
            Red/Dotted : They are present in this graph but not the alternate graph
            Green/Bold : They are present in the alternate graph but not this graph

        If the fileName is specified then the output is sent
        to that file, otherwise it is printed to stdout.

        If show_only_differences is set to True then the output will omit all of
        the nodes and connections the two graphs have in common. Some common
        nodes may be output anyway if there is a new connection between them.

        Plugs have no dot format as yet.
        """
        out = sys.stdout
        if fileName:
            out = open(fileName, 'w')

        dot = DotFormatting(self.use_long_names)

        out.write( dot.header() )
        out.write( dot.legend_for_compare(self.name, other.name, show_only_differences) )

        # Node are written out in multiple passes so that a single formatting
        # line can provide drawing instructions for the entire group of nodes.
        # This makes the file a lot smaller.

        # When showing only differences some connected nodes may not be
        # explicitly output. Although .dot can handle the formatting correctly
        # it cannot handle the name shortening for the label so remember which
        # ones were shown so that we can do it explicitly.
        nodes_shown = {}

        # Pass 1: Write out nodes in both graphs
        if not show_only_differences:
            out.write( dot.simple_node_format() )
            for node in self.nodes:
                if node in other.nodes:
                    nodes_shown[node] = True
                    out.write( dot.node(node) )

        # Pass 2: Write out nodes in graph 1 but not graph 2
        out.write( dot.altered_node_format(True) )
        for node in self.nodes:
            if node not in other.nodes:
                nodes_shown[node] = True
                out.write( dot.node(node) )

        # Pass 3: Write out nodes in graph 2 but not graph 1
        out.write( dot.altered_node_format(False) )
        for node in other.nodes:
            if node not in self.nodes:
                nodes_shown[node] = True
                out.write( dot.node(node) )

        # Set up node formatting for context since it's possible that new
        # connections will have been made on nodes in both graphs. In that
        # case the nodes have to be output as well to visualize the connection
        # so we can let .dot handle the correct formatting for those.
        out.write( dot.context_node_format() )

        # Pass 4: Write out connections in both graphs
        if not show_only_differences:
            for connection in self.connections:
                if connection in other.connections:
                    (src,dst) = connection.split(' ')
                    out.write( dot.simple_connection(src,dst) )

        # Pass 5: Write out connections in graph 1 but not graph 2
        for connection in self.connections:
            if connection not in other.connections:
                (src,dst) = connection.split(' ')
                (src_node,_) = split_connection( src )
                if src_node not in nodes_shown:
                    out.write( dot.node(src_node) )
                (dst_node,_) = split_connection( dst )
                if dst_node not in nodes_shown:
                    out.write( dot.node(dst_node) )
                out.write( dot.altered_connection(src,dst,True) )

        # Pass 6: Write out connections in graph 2 but not graph 1
        for connection in other.connections:
            if connection not in self.connections:
                (src,dst) = connection.split(' ')
                (src_node,_) = split_connection( src )
                if src_node not in nodes_shown:
                    out.write( dot.node(src_node) )
                (dst_node,_) = split_connection( dst )
                if dst_node not in nodes_shown:
                    out.write( dot.node(dst_node) )
                out.write( dot.altered_connection(src,dst,False) )

        out.write( dot.footer() )

    #======================================================================
    @staticmethod
    def __compare_lists(list1, list2):
        """
        Compare two lists and output generate a 2-tuple of lists with
        differences between them. The first element is the list of objects
        in the first list but not the second, the second elements contains
        objects in the second list but not the first.

        The naive implementation (walking each list and checking membership
        in the other) was too slow so a faster algorithm was put into place.
        A dictionary is populated, adding 1 if the entry is in the first list
        and 2 if the entry is in the second list. Any entries with both will
        have a value of 3 and can be ignored. Adds will have value 2 and
        removals will have value 1.

        list1: Baseline list for comparison
        list2: List against which it is compared
        """
        list_totals = {}
        for entry in list1:
            list_totals[entry] = 1

        for entry in list2:
            list_totals[entry] = list_totals.get(entry,0) + 2

        additions = []
        removals = []
        for (entry,entry_count) in list_totals.iteritems():
            if entry_count == 1:
                removals.append(entry)
            elif entry_count == 2:
                additions.append(entry)
        return (additions, removals)

    #======================================================================
    def compare(self, other):
        """
        Compare this graph structure against another one and generate a
        summary of how the two graphs differ. Differences will be returned
        as a JSON structure consisting of difference types. If no differences
        are found in any category then None is returned so that a quick
        test for "identical" can be made.

        Otherwise the changes found are layered:
        {
            'original' : 'SELF_NAME',
            'compared_with' : 'OTHER_NAME',
            'nodes' :
                {
                    'added' : [ NODES_IN_SELF_BUT_NOT_OTHER ],
                    'removed' : [ NODES_IN_OTHER_BUT_NOT_SELF ]
                },
            'plugs_in' :
                {
                    'added' : [ INPUT_PLUGS_IN_SELF_BUT_NOT_OTHER ],
                    'removed' : [ INPUT_PLUGS_IN_OTHER_BUT_NOT_SELF ]
                },
            'plugs_out' :
                {
                    'added' : [ INPUT_PLUGS_IN_SELF_BUT_NOT_OTHER ],
                    'removed' : [ INPUT_PLUGS_IN_OTHER_BUT_NOT_SELF ]
                },
            'plugs_world' :
                {
                    'added' : [ WORLDSPACE_PLUGS_IN_SELF_BUT_NOT_OTHER ],
                    'removed' : [ WORLDSPACE_PLUGS_IN_OTHER_BUT_NOT_SELF ]
                },
            'connections' :
                {
                    'added' : [ OUTGOING_CONNECTIONS_IN_SELF_BUT_NOT_OTHER ],
                    'removed' : [ OUTGOING_CONNECTIONS_IN_OTHER_BUT_NOT_SELF ]
                }
        }

        All of the 'plugs' lists are for evaluation graph mode only.
        """
        # Build up the structure using all found differences.
        json_compare = { 'original' : self.name, 'compared_with' : other.name }
        if self.operation is not None:
            json_compare['operation'] = self.operation

        total_differences = 0
        if KEY_NODES in self.inclusions:
            print 'Comparing node lists of sizes {} and {}'.format( len(self.nodes), len(other.nodes) )
            (nodes_added,nodes_removed) = self.__compare_lists( self.nodes, other.nodes )
            total_differences += len(nodes_added) + len(nodes_removed)
            json_compare[KEY_NODES]        = { KEY_ADDED : nodes_added,       KEY_REMOVED : nodes_removed }

        if KEY_PLUGS in self.inclusions:
            print 'Comparing in plug lists of sizes {} and {}'.format( len(self.plugs_in), len(other.plugs_in) )
            (plugs_in_added,plugs_in_removed) = self.__compare_lists( self.plugs_in, other.plugs_in )
            total_differences += len(plugs_in_added) + len(plugs_in_removed)

            print 'Comparing out plug lists of sizes {} and {}'.format( len(self.plugs_out), len(other.plugs_out) )
            (plugs_out_added,plugs_out_removed) = self.__compare_lists( self.plugs_out, other.plugs_out )
            total_differences += len(plugs_out_added) + len(plugs_out_removed)

            print 'Comparing world plug lists of sizes {} and {}'.format( len(self.plugs_world), len(other.plugs_world) )
            (plugs_world_added,plugs_world_removed) = self.__compare_lists( self.plugs_world, other.plugs_world )
            total_differences += len(plugs_world_added) + len(plugs_world_removed)

            json_compare[KEY_PLUGS_INPUT]  = { KEY_ADDED : plugs_in_added,    KEY_REMOVED : plugs_in_removed }
            json_compare[KEY_PLUGS_OUTPUT] = { KEY_ADDED : plugs_out_added,   KEY_REMOVED : plugs_out_removed }
            json_compare[KEY_PLUGS_WORLD]  = { KEY_ADDED : plugs_world_added, KEY_REMOVED : plugs_world_removed }

        if KEY_CONNECTIONS in self.inclusions:
            print 'Comparing connection lists of sizes {} and {}'.format( len(self.connections), len(other.connections) )
            (connections_added,connections_removed) = self.__compare_lists( self.connections, other.connections )
            total_differences += len(connections_added) + len(connections_removed)
            json_compare[KEY_CONNECTIONS]  = { KEY_ADDED : connections_added, KEY_REMOVED : connections_removed }


        # Do the check for no differences
        if total_differences == 0:
            print '--- No differences'
            return None

        return json_compare

    #======================================================================
    def compare_after_operation(self, operation, operation_arguments=None):
        """
        Compare a graph before and after an operation (Python function).
        This method takes a snapshot of the graph, performs the operation, takes another snapshot of
        the graph, and then compares the two versions of the graph.

        operation:           Function to call between graph captures.
        operation_arguments: Arguments to pass to the operation() function. This is passed as-is so
                             if you need multiple arguments use a dictionary and the **args syntax.
                             If "None" then the operation is called with no arguments.

        Usage:
            def my_operation( **args ):
                pass
            g = graphStructure()
            g.compare_after_operation( my_operation, operation_arguments={ 'arg1' : 6, 'arg2' : 4 } )
        """
        self.operation = str(operation)
        if operation_arguments is None:
            operation()
        else:
            operation( operation_arguments )

        graph_after = self.current_graph()

        return self.compare( graph_after )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
