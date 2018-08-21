""" Drag and drop behavior classes for the render setup nodes.

This module provides the drag and drop base and concrete classes.

They are derived from the API class MPxDragAndDropBehavior and are
used to handle the connections to make when the user drops a node 
or an attribute on to another node or attribute.

The interface to implement for each derived class is the following:

    - shouldBeUsedFor(sourceNode, destinationNode, sourcePlug, destinationPlug) -> bool
        # Returns True if the class should be used for this connection

    - connectAttrToAttr(sourcePlug, destinationPlug, force) -> None
        # Create all connections needed when sourcePlug is dropped on destinationPlug

    - connectAttrToNode(sourcePlug, destinationNode, force) -> None
        # Create all connections needed when sourcePlug is dropped on destinationNode

    - connectNodeToAttr(sourceNode, destinationPlug, force) -> None
        # Create all connections needed when sourceNode is dropped on destinationPlug

    - connectNodeToNode(sourceNode, destinationNode, force) -> None
        # Create all connections needed when sourceNode is dropped on destinationNode
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya
import maya.api.OpenMayaUI as OpenMayaUI

import maya.app.renderSetup.model.plug as plug
from maya.app.renderSetup.model.connectionOverride import *


class DragAndDropBehavior(OpenMayaUI.MPxDragAndDropBehavior):
    """ Base class for drag and drop behavior for render setup nodes. """

    # Name of attributes to try to connect with if no explicit attribute is given
    # The list order defines the priority for the attributes
    #
    # MAYA-66650: Can this be improved? How can we find out if the user wants a
    #             float connection and we should try 'outFloat' first?
    #
    kAttributeCandidates = [
        "outColor",  # Maya standard color output
        "outAlpha",  # Maya standard float output
        "outNormal", # Maya standard normal vector output
        "outValue",  # Mental Ray standard output
        "result",    # Used by some Mental Ray nodes
    ]

    # Error messages
    kErrorMsg_NoAttributeFound     = maya.stringTable['y_dragAndDropBehavior.kNoAttributeFound'     ]
    kErrorMsg_NoSurfaceShader      = maya.stringTable['y_dragAndDropBehavior.kNoSurfaceShader'      ]
    kErrorMsg_NoShadingGroup       = maya.stringTable['y_dragAndDropBehavior.kNoShadingEngine'      ]
    kErrorMsg_NoSurfaceShaderFound = maya.stringTable['y_dragAndDropBehavior.kNoSurfaceShaderFound' ]
    kErrorMsg_NoShadingGroupFound  = maya.stringTable['y_dragAndDropBehavior.kNoShadingGroupFound'  ]
    kErrorMsg_IncompatibleTypes    = maya.stringTable['y_dragAndDropBehavior.kIncompatibleTypes'    ]

    @staticmethod
    def raiseWarning(msg):
        """ Give an warning message to the user to avoid raising an exception here. """
        OpenMaya.MGlobal.displayWarning(msg)

    @staticmethod
    def connect(sourcePlug, destinationPlug):
        """ Try to connect two plugs and catch any plug type mismatches. """
        try:
            # We need this to be undoable
            cmds.connectAttr(sourcePlug.name(), destinationPlug.name(), force=True)
        except RuntimeError:
            DragAndDropBehavior.raiseWarning(DragAndDropBehavior.kErrorMsg_IncompatibleTypes + " (%s -> %s)" % (sourcePlug.name(),destinationPlug.name()))

    @staticmethod
    def isMatchingClass(node, classificationString):
        """ Returns True if the given node has a matching classification string. """
        fn = OpenMaya.MFnDependencyNode(node)
        return cmds.getClassification(fn.typeName, satisfies=classificationString)

    @staticmethod
    def findNode(node, typeId=OpenMaya.MFn.kDependencyNode, acceptor=None):
        """ Find a node of given type in a network, starting with the given node
        and searching downstream if needed. If an acceptor, user defined callable,
        is given we use that to accept or reject nodes during the search.

        The acceptor signature should be: func(MObject) -> bool """

        # Check if the given node can be accepted directly
        # MItDependencyGraph doesn't include the root node in the
        # search results below so we need a special case for this
        if (node.hasFn(typeId)):
            if acceptor:
                # Acceptor given so only return the node if it is accepted
                if acceptor(node):
                    return node
            else:
                # No acceptor given so this is a valid node
                return node

        # Start the search at given node searching downstream
        it = OpenMaya.MItDependencyGraph(node,
            filter = typeId, 
            direction = OpenMaya.MItDependencyGraph.kDownstream,
            traversal = OpenMaya.MItDependencyGraph.kDepthFirst,
            level = OpenMaya.MItDependencyGraph.kNodeLevel
        )

        # If no node was found we can early out here
        if it.isDone():
            return None

        node = it.currentNode()
        if acceptor:
            while True:
                # Check if we can accept current node
                if acceptor(node):
                    return node
                # Continue to next
                it.next()
                if it.isDone():
                    return None
                node = it.currentNode()

        # If we get here we don't have an acceptor and a node of the 
        # right type has already been found, so just return the current node
        return node

    @staticmethod
    def findCandidatePlug(sourceNode, destinationPlug):
        """ Return a plug to the first matching attribute in the candidate list.
        If no attribute is found, None is returned."""
        for attr in DragAndDropBehavior.kAttributeCandidates:
            plg = plug.Plug(sourceNode, attr)
            if plg.plug:
                destPlg = plug.Plug(destinationPlug)
                if plg.accepts(destPlg):
                    return plg.plug
        return None


class ConnectionOverrideDragAndDrop(DragAndDropBehavior):
    """ Class handling drag and drop for connection override nodes. """

    kTypeName = "connectionOverrideDragAndDrop"

    # Specific nodes to ignore during search in a network
    kNodeSearchIgnoreList = [
        "initialParticleSE" # Default node lambert1 has both initialParticleSE and initialShadingGroup connected, and we only want initialShadingGroup
    ]

    @staticmethod
    def creator():
        return ConnectionOverrideDragAndDrop()

    def __init__(self):
        super(ConnectionOverrideDragAndDrop, self).__init__()

    def shouldBeUsedFor(self, sourceNode, destinationNode, sourcePlug, destinationPlug):
        """ Return True if the given nodes/plugs are handled by this class. """

        # If the destination is one of our override nodes, we know how to handle it
        fnDstNode = OpenMaya.MFnDependencyNode(destinationNode)
        return fnDstNode.typeId == ConnectionOverride.kTypeId or \
           fnDstNode.typeId == ShaderOverride.kTypeId or \
           fnDstNode.typeId == MaterialOverride.kTypeId

    def connectAttrToAttr(self, sourcePlug, destinationPlug, force):
        """ Handle connection requests from source attribute to destination attribute. """

        if destinationPlug.isDestination and not force:
            # The destination is already connected and we're not allowed to break it
            # There is nothing we can do so early out here
            return

        sourceNode = sourcePlug.node()
        fnSourceNode = OpenMaya.MFnDependencyNode(sourceNode)
        fnDestinationNode = OpenMaya.MFnDependencyNode(destinationPlug.node())

        # If an explicit source attribute is given we think the user 
        # wants to connect to that specific node.attribute. 
        # If the node types doesn't match don't try to guess the right connection,
        # instead give an error message.
        # One exception is for material override where we can try to find the
        # shading engine for the source node.

        # Handle connection overrides node
        if fnDestinationNode.typeId == ConnectionOverride.kTypeId:
            # The value attribute is the only user connectable attribute
            if destinationPlug.partialName(useLongNames=True) == ConnectionOverride.kAttrValueLong:
                DragAndDropBehavior.connect(sourcePlug, destinationPlug)

        # Handle shader overrides node
        elif fnDestinationNode.typeId == ShaderOverride.kTypeId:
            # The override attribute is the only user connectable attribute
            if destinationPlug.partialName(useLongNames=True) == ConnectionOverride.kAttrValueLong:
                # Source must be a surface shader
                if DragAndDropBehavior.isMatchingClass(sourceNode, "shader/surface"):
                    DragAndDropBehavior.connect(sourcePlug, destinationPlug)
                else:
                    DragAndDropBehavior.raiseWarning(DragAndDropBehavior.kErrorMsg_NoSurfaceShader + " (%s)" % fnSourceNode.name())

        # Handle material overrides node
        elif fnDestinationNode.typeId == MaterialOverride.kTypeId:
            # The value attribute is the only user connectable attribute
            if destinationPlug.partialName(useLongNames=True) == ConnectionOverride.kAttrValueLong:
                # For material override we ignore which plug was given on the source node,
                # we just want the shading group for the source node.
                # Find the shading group for this node (searching downstream if needed)
                sgNode = DragAndDropBehavior.findNode(sourceNode, typeId=OpenMaya.MFn.kShadingEngine, acceptor = lambda obj: OpenMaya.MFnDependencyNode(obj).name() not in self.kNodeSearchIgnoreList)
                if sgNode:
                    sourcePlug = plug.Plug(sgNode, 'message').plug
                    DragAndDropBehavior.connect(sourcePlug, destinationPlug)
                else:
                    DragAndDropBehavior.raiseWarning(DragAndDropBehavior.kErrorMsg_NoShadingGroupFound + " (%s)" % fnSourceNode.name())

    def connectAttrToNode(self, sourcePlug, destinationNode, force):
        """ Handle connection requests from source attribute to destination node. """

        # In this case we can just set the destination plug 
        # and then call the connectAttrToAttr method
        node = OpenMaya.MFnDependencyNode(destinationNode).userNode()
        destinationPlug = node._getAttrValuePlug()
        if destinationPlug:
            self.connectAttrToAttr(sourcePlug, destinationPlug, force)

    def connectNodeToAttr(self, sourceNode, destinationPlug, force):
        """ Handle connection requests from source node to destination attribute. """

        if destinationPlug.isDestination and not force:
            # The destination is already connected and we're not allowed to break it
            # There is nothing we can do so early out here
            return

        fnSourceNode = OpenMaya.MFnDependencyNode(sourceNode)
        fnDestinationNode = OpenMaya.MFnDependencyNode(destinationPlug.node())

        # No explicit source attribute is given so we need to guess what
        # attribute to use. Also if the source node type doesn't match in this
        # case we try to find a matching node downstream.
        # If no valid node or attribute is found we fail with an error message.

        # Handle connection overrides node
        if fnDestinationNode.typeId == ConnectionOverride.kTypeId:
            # The value attribute is the only user connectable attribute
            if destinationPlug.partialName(useLongNames=True) == ConnectionOverride.kAttrValueLong:
                # Search for a valid source plug.
                sourcePlug = DragAndDropBehavior.findCandidatePlug(sourceNode, destinationPlug)
                if sourcePlug:
                    DragAndDropBehavior.connect(sourcePlug, destinationPlug)
                else:
                    DragAndDropBehavior.raiseWarning(DragAndDropBehavior.kErrorMsg_NoAttributeFound + " (%s)" % fnSourceNode.name())

        # Handle shader overrides node
        elif fnDestinationNode.typeId == ShaderOverride.kTypeId:
            # The value attribute is the only user connectable attribute
            if destinationPlug.partialName(useLongNames=True) == ConnectionOverride.kAttrValueLong:
                # Find the surface shader for this node (searching downstream if needed)
                surfaceShaderNode = DragAndDropBehavior.findNode(sourceNode, acceptor = lambda obj: DragAndDropBehavior.isMatchingClass(obj, classificationString="shader/surface"))
                if surfaceShaderNode:
                    # Search for a valid source plug
                    sourcePlug = DragAndDropBehavior.findCandidatePlug(surfaceShaderNode, destinationPlug)
                    if sourcePlug:
                        DragAndDropBehavior.connect(sourcePlug, destinationPlug)
                    else:
                        DragAndDropBehavior.raiseWarning(DragAndDropBehavior.kErrorMsg_NoAttributeFound + " (%s)" % OpenMaya.MFnDependencyNode(surfaceShaderNode).name())
                else:
                    DragAndDropBehavior.raiseWarning(DragAndDropBehavior.kErrorMsg_NoSurfaceShaderFound + " (%s)" % fnSourceNode.name())

        # Handle material overrides node
        elif fnDestinationNode.typeId == MaterialOverride.kTypeId:
            # The value attribute is the only user connectable attribute
            if destinationPlug.partialName(useLongNames=True) == ConnectionOverride.kAttrValueLong:
                # Find the shading group for this node (searching downstream if needed)
                sgNode = DragAndDropBehavior.findNode(sourceNode, typeId=OpenMaya.MFn.kShadingEngine, acceptor = lambda obj: OpenMaya.MFnDependencyNode(obj).name() not in self.kNodeSearchIgnoreList)
                if sgNode:
                    sourcePlug = plug.Plug(sgNode, 'message').plug
                    DragAndDropBehavior.connect(sourcePlug, destinationPlug)
                else:
                    DragAndDropBehavior.raiseWarning(DragAndDropBehavior.kErrorMsg_NoShadingGroupFound + " (%s)" % fnSourceNode.name())

    def connectNodeToNode(self, sourceNode, destinationNode, force):
        """ Handle connection requests from source node to destination node. """

        # In this case we can just set the destination plug 
        # and then call the connectNodeToAttr method
        node = OpenMaya.MFnDependencyNode(destinationNode).userNode()
        destinationPlug = node._getAttrValuePlug()
        if destinationPlug:
            self.connectNodeToAttr(sourceNode, destinationPlug, force)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
