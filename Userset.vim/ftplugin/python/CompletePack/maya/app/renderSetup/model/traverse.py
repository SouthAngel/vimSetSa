"""Render setup traversal."""

import maya.app.renderSetup.model.nodeList as nodeList

def nodeListChildren(node):
    """Utility function to iterate on children of a data model node.

    If the node has no children, an empty list is returned."""

    return nodeList.forwardListGenerator(node) if isinstance(
        node, nodeList.ListBase) else []

def depthFirst(node, children):
    """Generator for depth-first traversal of a tree.

    The node argument is the starting point of the traversal.

    The children argument is a callable that must produce an iterable on
    the node's children.  This is used by the traversal to iterate on the
    node's children and thus recurse."""

    yield node
    for child in children(node):
        # Intuition would suggest simply writing the following:
        # 
        # depthFirst(child, children)
        #
        # However, this ends the generator without recursing.  The proper
        # generator construction is to iterate on the recursive call.  See:
        #
        # http://stackoverflow.com/questions/248830/python-using-a-recursive-algorithm-as-a-generator
        # http://stackoverflow.com/questions/8407760/python-how-to-make-a-recursive-generator-function

        for d in depthFirst(child, children):
            yield d
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
