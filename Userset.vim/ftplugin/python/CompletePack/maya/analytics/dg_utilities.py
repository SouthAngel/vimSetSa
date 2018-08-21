"""
A collection of utilities to help manage the basic information in the DG in a
common way. This includes extracting node types from nodes and plugs, parsing
connection information, etc.
"""
__all__ = ['plug_level_connections',
           'node_type_hierarchy_list',
           'default_nodes_and_connections',
           'node_level_connections']

import maya.cmds as cmds

NODE_TYPE_ROOT = 'node' # Name of the root node type from which all types derive

#======================================================================
def plug_level_connections(node):
    """
    Given the name of a node find all of the connections to and from it.
    The return value is a pair of arrays, connections coming in and
    connections going out of this node, each consisting of pairs with
    the names of the source and destination plug names.

    This is an easier to understand format than the flat list with
    inconsistent ordering of source and destination.

    e.g. for connections A.o -> X.iA, B.o -> X.iB, and X.o -> C.i
    the return value will be:

        (
            [("A.o","X.iA"), ("B.o", "X.iB")],
            [("X.o","C.i"])
        )
    """
    # This command returns plugs as a flat list of dst1, src1, dst2, src2, ...
    all_incoming = cmds.listConnections( node
                                       , plugs=True
                                       , connections=True
                                       , source=True
                                       , destination=False )
    all_incoming = all_incoming if all_incoming else []
    # This command returns plugs as a flat list of src1, dst1, src2, dst2, ...
    all_outgoing = cmds.listConnections( node
                                       , plugs=True
                                       , connections=True
                                       , source=False
                                       , destination=True )
    all_outgoing = all_outgoing if all_outgoing else []

    incoming_list = []
    for connection in range(0, len(all_incoming)/2):
        incoming_list.append( (all_incoming[connection+1], all_incoming[connection]) )
    outgoing_list = []
    for connection in range(0, len(all_outgoing)/2):
        outgoing_list.append( (all_outgoing[connection], all_outgoing[connection+1]) )

    return (incoming_list, outgoing_list)

#======================================================================
def __inheritance_list(leaf):
    """
    Returns the list of all node types inherited from "leaf", not
    including the root "node". Uses the member variable inheritance{}
    to allow recursive construction of the list while avoiding O(N^2)
    duplication of work.

    Returned list will be in order from base to most derived class.
    """
    if leaf == NODE_TYPE_ROOT:
        return []

    # Unfortunately the inherited=True flag only provides the
    # immediate parent so we have to do some work to get the
    # entire hierarchy.
    parent_list = cmds.nodeType( leaf, inherited=True, isTypeName=True )
    if parent_list == None:
        return []
    return parent_list

#======================================================================
def node_type_hierarchy_list():
    """
    Extract the list of all node types in the hierarchy below the root
    node. The list is returned with full hierarchy information,
    separated by a vertical bar '|'. For example the time-to-linear
    animcurve node type will look like '|animCurve|animCurveTL'.

    The root 'node' is omitted from all hierarchies since it would be
    redundant to include it everywhere. The leading vertical bar is
    used as a placeholder. The root type will be the one and only entry
    in the list without the leading vertical bar.

    e.g. return for the one-type hierarchy above would be:
        [ 'node' : 'node'
        , 'animCurve'   : '|animCurve'
        , 'animCurveTL' : '|animCurve|animCurveTL'
        ]
    """
    node_type_hierarchy = {}
    try:
        #----------------------------------------------------------------------
        #
        # First step is to construct the hiearchy information based on the
        # limited amount of data available from the 'nodeType' command
        #
        # The derived=True flag dumps every node in the inheritance tree
        # so this is a good starting point to get all types.
        all_node_types = cmds.nodeType( NODE_TYPE_ROOT, derived=True, isTypeName=True )
        for node_type in all_node_types:
            inheritance_list = __inheritance_list( node_type )

            # Since everything is rooted at 'node', and it doesn't
            # show up in the inheritance output, add it manually. It's a
            # bit redundant but harmless.
            node_type_hierarchy[node_type] = '|'+'|'.join( inheritance_list )
        node_type_hierarchy[NODE_TYPE_ROOT] = NODE_TYPE_ROOT
    except Exception,ex:
        print 'ERR: Node type hierarchy calculation failed: %s' % str(ex)

    return node_type_hierarchy

#======================================================================
def node_level_connections(node_name):
    """
    Get the source and destination connection list on a node. Handles
    all of the error and return cases so that calles can just use the
    result directly without having to duplicate the exception handling.

    node_name: Name of node on which to find connections
    returns:  A pair of lists of connected nodes, (sources,destinations)
              A list is empty if no connections in that direction exist.
    """
    sources = []
    destinations = []
    try:
        sources = cmds.listConnections(node_name, source=True, destination=False)
        sources = sources if sources else []
        destinations = cmds.listConnections(node_name, source=False, destination=True)
        destinations = destinations if destinations else []
    except Exception:
        # If the node has gone away the listConnections command may fail
        # but that's okay, it just means it can be safely ignored
        pass

    return (sources,destinations)

#======================================================================
def default_nodes_and_connections():
    """
    Find what Maya believes to be all of the default and persistent nodes.
    This may not be the same as all of the nodes present in an empty scene
    but in cases where the empty scene couldn't be measured directly this
    is the next best thing.

    Returns a 2-tuple where the first element is a set of all default nodes
    and the second is a list of pairs of (src,dst) for connections going
    between default nodes.
    """
    # Generates alternating name,type pairs in a flat list. The zip trick
    # is a neat way to convert that list into a single list of pairs.
    # Have to call the command twice because when both flags are used it
    # "and"s them together and we want "or".
    ls_list = cmds.ls( showType=True, persistentNodes=True )
    ls_list = ls_list if ls_list else []
    ls_list += cmds.ls( showType=True, defaultNodes=True )
    ls_list = ls_list if ls_list else []

    # Add some hardcoded items that at least for now are not showing up as
    # default/persistent nodes even though they are
    ls_list += [ 'persp',                   'transform'
               , 'side',                    'transform'
               , 'top',                     'transform'
               , 'front',                   'transform'
               , 'perspShape',              'camera'
               , 'sideShape',               'camera'
               , 'topShape',                'camera'
               , 'frontShape',              'camera'
               , 'defaultRenderLayer',      'renderLayer'
               , 'defaultLayer',            'displayLayer'
               , 'layerManager',            'displayLayerManager'
               , 'lightLinker1',            'lightLinker'
               , 'timeEditor',              'timeEditor'
			   , 'composition1',            'timeEditorTracks'
               , 'renderLayerManager',      'renderLayerManager'
               ]

    default_nodes = set()
    default_node_connections = set()
    # Walk the list of all nodes and add them to the default list.
    for (node_name,_) in zip(ls_list[::2], ls_list[1::2]):
        # Skip duplicates
        if node_name in default_nodes:
            continue
        default_nodes.add( node_name )

    # The connections have to be checked after the entire default node
    # name list is built since it is looking for connections between
    # default nodes only.
    for node_name in default_nodes:
        # Get source and destination connections to the default nodes
        # separately so that the pairs are in the right order.
        (sources, destinations) = node_level_connections(node_name)
        for connection in sources:
            if connection in default_nodes:
                default_node_connections.add( (connection,node_name) )
        for connection in destinations:
            if connection in default_nodes:
                default_node_connections.add( (node_name,connection) )

    return ( default_nodes, default_node_connections )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
