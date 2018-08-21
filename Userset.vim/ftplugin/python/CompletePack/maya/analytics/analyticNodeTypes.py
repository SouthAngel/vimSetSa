"""
Analytic class for examining node type distribution. This analytic collects
the number of each node type in the scene.

All of the persistent and default nodes are skipped unless they have a new
connection. The way these two things are measured is different by necessity
for the cases of analyzing a file that is read and analyzing the current scene.

If the file is being read:
    - persistent and default nodes are defined as any node present before the
      file is loaded
    - exceptions are made if a new connection is formed to a persistent or
      default node after the file is loaded

If the current scene is used:
    - persistent and default nodes are taken to be those marked as such by the
      Maya 'ls' command. This won't include any special persistent nodes
      created after-the-fact, such as those a newly loaded plug-in might create.
    - exceptions are made if there is any connection at all to these default
      or persistent nodes to a scene node.

If the 'summary' option is used then the output includes a dictionary
consisting of NODE_TYPE keys with value equal to the number of nodes of that
type in the scene, not including default node types. Only node types with at
least 1 node of that type are included.

    "summary" : {
        "transform" : 3,
        "mesh" : 1
    }

For normal output the output is a dictionary whose keys are the node types and
the values are a list of nodes of that type. The information is put into an
object named "node_types". This avoids the potential for a name conflict
between the object "summary" and a node type also named "summary".

    "nodeTypes" : {
        "transform" : ["transform1", "transform2", "group1"],
        "mesh" : ["cubeShape1"]
    }

If the 'details' option is used then the output is arranged hierarchically by
node type layers instead of a flat dictionary.

    "nodeTypeTree" : {
        "ROOT_NODE" : {
            "nodes" : [],
            "children" : {
                "CHILD_NODE" : {
                    "nodes" : [],
                    "children" : {
                        "GRANDCHILD_NODE_TYPE1" : {
                            "nodes" : ["GC1_NODE_NAME],
                            "children" : []
                        },
                        "GRANDCHILD_NODE_TYPE2" : {
                            "nodes" : ["GC2_NODE_NAME],
                            "children" : []
                        }
                    }
                }
            }
        }
    }

If the analytic-specific option 'use_defaults' is used then the default nodes
will be included in the output.
"""
import maya.cmds as cmds
from .BaseAnalytic import BaseAnalytic, OPTION_DETAILS, OPTION_SUMMARY
from .dg_utilities import node_type_hierarchy_list, default_nodes_and_connections, node_level_connections
from .decorators import addMethodDocs,addHelp,makeAnalytic

OPTION_USE_DEFAULTS = 'use_defaults'

@addMethodDocs
@addHelp
@makeAnalytic
class analyticNodeTypes(BaseAnalytic):
    """
    This class provides scene stats collection on node types.
    """
    # Dictionary key for node children in the detailed output
    KEY_CHILDREN = 'children'
    # Dictionary key for node lists in the detailed output
    KEY_NODES = 'nodes'
    # Dictionary key for the main body of the node information in all modes
    KEY_NODE_TYPES = 'nodeTypes'

    def __init__(self):
        """
        Initialize the persistent class members

        default_nodes:            Set of all default nodes
        default_node_connections: Set of (src,dst) pairs for all connections
                                  between default nodes.
        """
        super(self.__class__, self).__init__()
        self.default_nodes = set()
        self.default_node_connections = set()

    #----------------------------------------------------------------------
    def __is_node_counted(self, node_name):
        """
        Check to see if this node is to be counted as part of the analytic.
        If it's not a default/persistent node it will always be counted.
        Otherwise it will depend on whether it has any new connections.
        """
        if node_name not in self.default_nodes:
            return True

        # So the node is persistent or default. If it has connections to a
        # scene node it should still be counted so check for that next.
        (sources, destinations) = node_level_connections(node_name)
        for connection in sources:
            if (connection,node_name) not in self.default_node_connections:
                return True
        for connection in destinations:
            if (node_name,connection) not in self.default_node_connections:
                return True

        return False

    #----------------------------------------------------------------------
    def establish_baseline(self):
        """
        This is run on an empty scene, to find all of the nodes/node types
        present by default. They will all be ignored for the purposes of
        the analytic since they are not relevant to scene contents.
        """
        # Allow defaults by simply leaving the list of defaults empty
        if self.option( OPTION_USE_DEFAULTS ):
            self.default_nodes = set()
            self.default_node_connections = set()
            return

        # Start with the list of nodes Maya thinks are default or persistent
        (self.default_nodes, self.default_node_connections) = default_nodes_and_connections()

        # Generates alternating name,type pairs in a flat list. The zip trick
        # is a neat way to convert that list into a single list of pairs.
        # This is to catch any other nodes that may be already present in an
        # empty scene but may not be flagged as default or persistent (e.g.
        # a node created when the slice is loaded). The list should be small
        # so the overhead of potential duplication is negligible.
        ls_list = cmds.ls( showType=True )

        # Walk the list of all nodes and add them to the default list.
        for (node_name,_) in zip(ls_list[::2], ls_list[1::2]):
            # Skip duplicates
            if node_name in self.default_nodes:
                continue
            self.default_nodes.add( node_name )

            # Get source and destination connections to the default nodes
            # separately so that the pairs are in the right order. Unlike
            # __find_default_nodes this check can be done as we go since there
            # are no scene nodes loaded at this point so all connections are
            # relevant.
            (sources, destinations) = node_level_connections(node_name)
            for connection in sources:
                self.default_node_connections.add( (connection,node_name) )
            for connection in destinations:
                self.default_node_connections.add( (node_name,connection) )

    #----------------------------------------------------------------------
    def __find_leaf( self, hierarchy_below, parent_dict ):
        """
        Walk down the tree to find the leaf pointed at by the node path
        in hierarchy_below.

        hierarchy_below : List of parent types of the desired node type,
                          from root to leaf inclusive, in that order.
        parent_dict     : Reference to the value on the parent node's key,

        return: The leaf node is a key in a dictionary, return a reference to
                its value.
        """
        if len(hierarchy_below) == 0:
            return parent_dict

        # Use an exception here to catch the case of the leaf not existing,
        # though at least in initial usage it will always exist.
        try:
            next_level = hierarchy_below[0]
            return self.__find_leaf( hierarchy_below[1:], parent_dict[self.KEY_CHILDREN][next_level] )
        except KeyError:
            return None

    #----------------------------------------------------------------------
    def __create_subtree( self, hierarchy_below, parent_dict ):
        """
        Recursively create the subtree using parent_dict as the root, and
        hierarchy_below as the list of nodes to create on the way down.

        For a hierarchy_below of "|A|B" constructing the tree with a
        parent_dict whose key is "ROOT" this tree will be constructed:

        "ROOT" : {
            "children" : {
                "A" : {
                    "children" : {
                        "B" : {
                        }
                    }
                }
            }
        }

        hierarchy_below : List of parent types of the desired node type,
                          from root to leaf inclusive, in that order.
        parent_dict     : Reference to the value on the parent node's key,

        In the above example the descent looks like this:

            step      hierarchy_below   parent_dict
            ---------------------------------------------------
            initial   [A,B]             ROOT
            1         [B]               ROOT['children'][A]
            2         []                ROOT['children'][A]['children'][B]

        return: Subtree that can be added as the parent key's value. In
                the example above "ROOT" is the parent key and everything
                else is the value.
        """
        # If this is the leaf level then return the parent's child list
        if len(hierarchy_below) == 0:
            return parent_dict

        # If there are still levels below this then merge them into this
        # node's children
        next_node = hierarchy_below[0]
        parent_dict[self.KEY_CHILDREN] = parent_dict.get(self.KEY_CHILDREN,{})
        next_level = parent_dict[self.KEY_CHILDREN].get(next_node,{})
        parent_dict[self.KEY_CHILDREN][next_node] = self.__create_subtree( hierarchy_below[1:], next_level)

        return parent_dict

    #----------------------------------------------------------------------
    def run(self):
        """
        Generates the number of nodes of each type in a scene in the
        CSV form "node_type","Count", ordered from most frequent to least
        frequent.

        If the 'details' option is set then insert two extra columns:
            "Depth" containing the number of parents the given node type has,
            "Hierarchy" containing a "|"-separated string with all of the
                node types above that one in the hierarchy, starting with it
                and working upwards.
        It will also include lines for all of the node types that have no
        corresponding nodes in the scene, signified by a "Count" of 0.
        """
        json_data = {}

        # If the analytic is called as part of a file load and run then it
        # will have had an empty scene from which to establish a baseline.
        # If it is run directly on an already loaded scene then it has to
        # make a best guess by looking at the nodes Maya believes are not
        # part of the scene. It's less accurate (e.g. won't catch when a
        # plug-in adds a persistent node) but it's better than no filter.
        if (len(self.default_nodes) == 0) and not self.option(OPTION_USE_DEFAULTS):
            (self.default_nodes, self.default_node_connections) = default_nodes_and_connections()

        node_type_counts = {}
        node_type_list = {}
        # Generates alternating name,type pairs in a flat list. The zip trick
        # is a neat way to convert that list into a single list of pairs.
        ls_list = cmds.ls( showType=True )

        # Walk the list of all nodes and add them to the collected list.
        for (node_name,node_type) in zip(ls_list[::2], ls_list[1::2]):
            if self.__is_node_counted(node_name):
                node_type_counts[node_type] = node_type_counts.get(node_type,0) + 1
                node_type_list[node_type] = node_type_list.get(node_type,[]) + [self._node_name(node_name)]

        # If the summary was requested put it in first
        if self.option(OPTION_SUMMARY):
            json_data['summary'] = node_type_counts

        # More construction is needed for the detailed output
        if self.option(OPTION_DETAILS):
            # Get the information required to build up a node type tree
            node_type_hierarchy = node_type_hierarchy_list()
            node_type_tree = { 'node' : {} }
            # For each node type that has existing nodes ...
            for (node_type,nodes_of_type) in node_type_list.iteritems():
                # ... create the subtree for that node type and add the nodes.
                # Skip the first element since it's always empty. (The root
                # node type 'node' will have an element there but it's
                # abstract and you can never create a node of that type.)
                hierarchy_list = node_type_hierarchy[node_type].split('|')[1:]
                node_type_tree['node'] = self.__create_subtree( hierarchy_list, node_type_tree['node'] )
                # Separating the create and find operations into different
                # methods greatly simplifies the code.
                node_type_position = self.__find_leaf( hierarchy_list, node_type_tree['node'] )
                node_type_position[self.KEY_NODES] = nodes_of_type
            json_data[self.KEY_NODE_TYPES] = node_type_tree
        else:
            json_data[self.KEY_NODE_TYPES] = node_type_list

        return json_data

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
