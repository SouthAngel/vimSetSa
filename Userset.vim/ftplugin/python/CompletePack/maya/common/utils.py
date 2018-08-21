"""
Maya-specific utility tools (classes and method)

These are utilities to interact with Maya.  They give basic building blocks to
wrap simple operations in easier-to-use tools.

These can be used inside Maya and MayaLT.
"""

import maya.cmds as cmds


__all__ = [
    'getSourceNodesFromPlug',
    'getSourceNodes',
    'getSourceNodeFromPlug',
    'getSourceNode',
    'getIndexAfterLastValidElement',
    ]


def getSourceNodesFromPlug(plug, shapes=False):
    """
    This method returns the name of the nodes connected as sources for the
    given plug.
    """

    parameters = {'destination': False, 'source': True}
    if shapes:
        parameters['shapes'] = True
    connections = cmds.listConnections(plug, **parameters)
    return connections or []


def getSourceNodes(node, attribute, shapes=False):
    """
    This method returns the name of the nodes connected as sources for the
    given attribute.
    """

    plug = '%s.%s' % (node, attribute)
    return getSourceNodesFromPlug(plug, shapes)


def getSourceNodeFromPlug(plug, shapes=False):
    """
    This method returns the name of the node connected as a source for the
    given plug.
    """

    connections = getSourceNodesFromPlug(plug, shapes)
    if connections:
        # Something is connected.
        assert(len(connections) == 1)
        return connections[0]
    else:
        return None


def getSourceNode(node, attribute, shapes=False):
    """
    This method returns the name of the node connected as a source for the
    given attribute.
    """

    plug = '%s.%s' % (node, attribute)
    return getSourceNodeFromPlug(plug, shapes)


def getIndexAfterLastValidElement(attribute):
    """
    This method returns the index right after the last valid element in a multi
    attribute.
    """

    indices = cmds.getAttr(attribute, multiIndices=True)
    return 0 if not indices else indices[-1] + 1
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
