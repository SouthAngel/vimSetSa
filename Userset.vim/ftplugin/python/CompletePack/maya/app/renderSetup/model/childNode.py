"""
    This module defines a base class to manage any child nodes in the render setup tree.
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.cmds as cmds

import maya.api.OpenMaya as OpenMaya

import maya.app.renderSetup.model.nodeList as nodeList
from maya.app.renderSetup.model.nodeNotes import NodeNotes
from maya.app.renderSetup.model.serializableNode import SerializableNode
from maya.app.renderSetup.model.observable import Observable
import maya.app.renderSetup.model.typeIDs as typeIDs
import maya.app.renderSetup.model.jsonTranslatorGlobals as jsonTranslatorGlobals
import maya.app.renderSetup.model.undo as undo

from itertools import izip

kCmdPrivate = maya.stringTable['y_childNode.kCmdPrivate' ]

kOrderingFailure = "Nodes '%s' and '%s' cannot be ordered."
kRename = maya.stringTable['y_childNode.kRename' ]

_IMPORTED_ATTRIBUTE_SHORT_NAME = 'imp'


# Because of MAYA-59270, nodeList.ListItem (which is derived from MPxNode)
# must appear last in the list of base classes.
class ChildNode(Observable, NodeNotes, SerializableNode, nodeList.ListItem):
    """ 
        The class provides the basic functionality for any child nodes
    """

    kTypeId = typeIDs.childNode
    kTypeName = "childNode"

    # Awkwardly, abstract base classes seem to need a creator method.
    @staticmethod
    def creator():
        return ChildNode()

    @staticmethod
    def initializer():
        ChildNode.inheritAttributesFrom(nodeList.ListItem.kTypeName)

    def __init__(self):
        super(ChildNode, self).__init__()
        self._opaqueData = dict()
        # Collections and overrides have an enabled output that is computed
        # by the DG.  As parents of collections, render layers are asked if
        # their enabled output is being computed, but since they have none,
        # they always answer False.
        self._inEnabledChanged = False
        
    def setName(self, newName):
        """Rename render setup node."""
        if newName != self.name():
            # Keep the node in the same namespace, regardless of the
            # current namespace.
            fn = OpenMaya.MFnDependencyNode(self.thisMObject())
            absName = fn.absoluteName()
            (path, sep, name) = absName.rpartition(':')
            with undo.NotifyCtxMgr(kRename % (name, newName), self.itemChanged):
                cmds.rename(absName, path + sep + newName)

    def addOpaqueData(self, key, data):
        self._opaqueData[key] = data

    def removeOpaqueData(self, key):
        # Use built-in behavior of raising KeyError if key not found.
        del self._opaqueData[key]

    def getOpaqueData(self, key):
        return self._opaqueData[key]

    def hasOpaqueData(self, key):
        return key in self._opaqueData

    def _hasImportedPlug(self):
        return OpenMaya.MFnDependencyNode(self.thisMObject()).hasAttribute(jsonTranslatorGlobals.IMPORTED_ATTRIBUTE_NAME)

    def _getImportedPlug(self):
        if not self._hasImportedPlug():
            # Use the command in order to allow undo/redo
            cmds.addAttr(self.name(), shortName=_IMPORTED_ATTRIBUTE_SHORT_NAME, longName=jsonTranslatorGlobals.IMPORTED_ATTRIBUTE_NAME, attributeType='bool')
        return OpenMaya.MFnDependencyNode(self.thisMObject()).findPlug(jsonTranslatorGlobals.IMPORTED_ATTRIBUTE_NAME, False)

    def getImportedStatus(self):
        # None means that no imported attribute is present on this specific node
        return self._getImportedPlug().asBool() if self._hasImportedPlug() else None

    def setImportedStatus(self, value):
        EditImportedStatusCmd.execute(self, value)

    def acceptImport(self):
        self.setImportedStatus(False)

    def _encodeProperties(self, dict):
        super(ChildNode, self)._encodeProperties(dict)
        # Do not export the 'import status'

    def _decodeProperties(self, dict, mergeType, prependToName):
        super(ChildNode, self)._decodeProperties(dict, mergeType, prependToName)
        self.setImportedStatus(True)

#==============================================================================
# CLASS TreeOrderedItem
#==============================================================================

class TreeOrderedItem(object):
    """Override tree mixin class.

    A render layer can be considered as the root of a tree of overrides,
    with collections (and nested collections) as internal tree nodes, and
    overrides as leaf nodes.  This base class implements ordering on
    collections and overrides.  An override that is higher-priority will
    supercede the effect of a lower-priority override, and transitively any
    override in a higher-priority partition will supercede the effects of
    any override in a lower-priority partition.

    In a given list, an item is higher-priority if it occurs after another
    item (closer to the back) in the same list.  If the items are from
    different lists, we move up the tree hierarchy until we can compare two
    items from the same list.

    Note that in the render setup hierarchy, only collections and overrides
    are ordered; render layers are not."""

    # Here are a few examples of override and collection orderings.
    # In the override trees below, tree nodes under a common parent are
    # siblings, and priority goes lower to higher from left to right
    # (rightmost tree nodes are highest priority)
    #
    #       +--+
    #       |rl|
    #       +--+
    #     /-   \-
    # +--+      +--+           collection cb > collection ca
    # |ca|      |cb|
    # +--+      +--+--
    #           /  \  \---
    #        +--+  +--+  +--+  Override oc > override ob > override oa
    #        |oa|  |ob|  |oc|
    #        +--+  +--+  +--+
    #
    #    +--+
    #    |rl|
    #    +--+
    #    /  \-
    #    |    \
    # +--+   +--+
    # |ca|   |cb|
    # +--+   +--+
    #  |      |
    # +--+   +--+  Override ob > override oa
    # |oa|   |ob|
    # +--+   +--+
    #
    #       +--+        In this example, cc is a child collection
    #       |rl|        of collection cb.
    #       +--+        
    #    --/    \
    # +--+      +--+
    # |ca|      |cb|
    # +--+      +--+
    #   |         |
    # +--+      +--+    Override oc > override ob > override oa
    # |oa|      |cc|
    # +--+      +--+
    #           /  \
    #        +--+  +--+
    #        |ob|  |oc|
    #        +--+  +--+
    #

    def __gt__(self, b):
        """Return whether this item is higher-priority than the argument.

        For well-balanced override trees, the average time complexity of
        this method is O(log(n)), for n overrides and collections.
        Pathological cases (n collections strung out in a linear hierarchy,
        or n overrides in a collection strung out in a linear list) will
        cause O(n) time complexity."""

        # The algorithm used is to find in the ancestor list the deepest
        # common parent of the two nodes, then compare the sibling
        # ancestors to determine priority.

        # Early out: compare with ourselves.
        if b is self:
            return False

        rl = self.getRenderLayer()

        # Error if we don't belong to the same render layer.
        if rl is not b.getRenderLayer():
            raise RuntimeError(
                kOrderingFailure % (str(self.name()), str(b.name())))

        aas = self.ancestors(root=rl)
        bas = b.ancestors(root=rl)

        # Find the deepest common parent in both ancestor lists, then return
        # the order of the next two children.
        for (aa, ba) in izip(aas, bas):
            if aa is not ba:
                return nodeList.isAfter(aa.parent(), aa, ba)

        # If we ran out of nodes without finding a differing ancestor,
        # then a is a subset of b, or vice versa.  The longest ancestor
        # chain has highest priority.
        return len(aas) > len(bas)


#==============================================================================
# CLASS EditImportedStatusCmd
#==============================================================================

class EditImportedStatusCmd(OpenMaya.MPxCommand):
    """Command to unapply and reapply a change of the imported status.

    This command is a private implementation detail of this module and should
    not be called otherwise."""

    kCmdName = 'editImportedStatus'

    # Command data.  Must be set before creating an instance of the command
    # and executing it.  Ownership of this data is taken over by the
    # instance of the command.
    node = None
    imported = None

    def isUndoable(self):
        return True

    def doIt(self, args):
        # Completely ignore the MArgList argument, as it's unnecessary:
        # arguments to the commands are passed in Python object form
        # directly to the command's constructor.

        if self.node is None or self.imported is None:
            self.displayWarning(kCmdPrivate % self.kCmdName)
        else:
            self.redoIt()

    @staticmethod
    def execute(node, imported):
        """Unapply the change of the imported status flag."""

        EditImportedStatusCmd.node = node
        EditImportedStatusCmd.imported = imported
        cmds.editImportedStatus()
        EditImportedStatusCmd.node = None
        EditImportedStatusCmd.imported = None

    @staticmethod
    def creator():
        # Give ownership of the node to the command instance.
        return EditImportedStatusCmd(EditImportedStatusCmd.node, EditImportedStatusCmd.imported)

    def __init__(self, node, imported):
        super(EditImportedStatusCmd, self).__init__()
        self._dgMod = None
        self._node = node
        self._imported = imported

    def _buildCmd(self):
        dgMod = None
        if self._imported!=self._node.getImportedStatus():
            if self._imported is None or not self._imported:
                if self._node._hasImportedPlug():
                    dgMod = OpenMaya.MDGModifier()
                    dgMod.removeAttribute(self._node.thisMObject(), self._node._getImportedPlug().attribute())
            else:
                attr = OpenMaya.MFnNumericAttribute().create(jsonTranslatorGlobals.IMPORTED_ATTRIBUTE_NAME, \
                            _IMPORTED_ATTRIBUTE_SHORT_NAME, OpenMaya.MFnNumericData.kBoolean, self._imported)
                dgMod = OpenMaya.MDGModifier()
                dgMod.addAttribute(self._node.thisMObject(), attr)
        return dgMod

    def redoIt(self):
        self._dgMod = self._buildCmd()
        if self._dgMod is not None:
            self._dgMod.doIt()
            self._node.itemChanged()

    def undoIt(self):
        if self._dgMod is not None:
            self._dgMod.undoIt()
            self._node.itemChanged()
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
