"""
Analytic class for examining static node type distribution.

The information regarding the node type hierarchy and their flags is returned
in JSON format.

    "nodeTypes" :
    {
        "type"       : "node",
        "children"   :
        [
            {
                "type" : "childNodeType",
                "children" :
                [
                    { "type" : "grandchildNodeType" }
                ]
            }
        ]
    }

Options Available
    details = Include all of the attribute information for each node type.
              Attribute information is not inherited; the node type will only
              show those attributes it has added, none of the parent node
              type's attributes.

                "attributes" :
                {
                    "staticAttributes" :
                    [
                        { "weightedPair" : [ "weight", { "pair" : [ "pairA", "pairB" ] } ] }
                    ]
                    ,
                    "extensionAttributes" :
                    [
                        ...etc...
                    ]
                }
"""
import json
import maya.cmds as cmds
from .BaseAnalytic import BaseAnalytic, OPTION_DETAILS
from .dg_utilities import node_type_hierarchy_list
from .decorators import addMethodDocs,addHelp,make_static_analytic

@addMethodDocs
@addHelp
@make_static_analytic
class AnalyticStaticNodeTypes(BaseAnalytic):
    """
    This class provides scene stats collection on node types.
    """
    def __init__(self):
        """
        Initialize the persistent class members
        """
        super(self.__class__, self).__init__()
        self.node_type_children = None
        self.attribute_json = None

    #----------------------------------------------------------------------
    def __get_json(self, root_node_type):
        """
        Recursively get the JSON structure describing the node type hierarchy.
        """
        if root_node_type in self.node_type_children:
            child_list = self.node_type_children[root_node_type]
        else:
            child_list = []

        # The root node is stored as an empty name; replace it with
        # something that makes more sense for the JSON format.
        if root_node_type == '':
            root_node_type = 'node'

        node_type_json = { 'type' : root_node_type }
        if child_list:
            child_json = {}
            for child_node in child_list:
                child_json[child_node] = self.__get_json( child_node )
            node_type_json['children'] = child_json
        if self.attribute_json and (root_node_type in self.attribute_json):
            node_type_json['attributes'] = self.attribute_json[root_node_type]
        return node_type_json

    #----------------------------------------------------------------------
    def run(self):
        """
        Generates a JSON structure containing the node type hierarchy

        If the 'details' option is set include the list of attributes attached to each node type.
        """
        self.attribute_json = None
        if self.option(OPTION_DETAILS):
            try:
                self.attribute_json = json.loads( cmds.dbpeek(op='attributes', a='nodeType', all=True) )['nodeTypes']
            except Exception, ex:
                self.error( 'Could not find node type attributes : "{0:s}"'.format( ex ) )

        # Hierarchy data is {'NODE_NAME' = '|GRANDPARENT|PARENT...'}
        # Root node (TdependNode) does not appear in the hierarchy but
        # since all node types derive from it the leading '|' can be
        # used to automatically add it.
        node_type_hierarchy = node_type_hierarchy_list()

        # Store the children types of each node type here so that the
        # structure can be recreated in a tree form
        self.node_type_children = {}

        for (name,hierarchy) in node_type_hierarchy.iteritems():
            hierarchy_list = hierarchy.split('|')
            # The root node will not have any parent types to parse. Every
            # other type will have itself and at least one ancestor here.
            if len(hierarchy_list) > 1:
                # Element [-1] is the node_type itself, the next one back
                # is its immediate parent, the one of interest in building
                # the child list
                parent_type = hierarchy_list[-2]
                self.node_type_children[parent_type] = self.node_type_children.get(parent_type,[]) + [name]

        # All nodes derive from the root and the root has the null name, even
        # though it's derived from 'node'. Recursively generate the JSON code
        # for each node down the hierarchy.
        json_results = self.__get_json( '' )

        return json_results

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
