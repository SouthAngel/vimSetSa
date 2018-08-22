"""List management classes and utilities.

This module provides a base class for using nodes in linked lists as the
items in the list, as well as functions to modify a list of nodes.

The list management functions in this module that write to lists support
undo / redo.

Commands in this module should be considered private implementation
details, and should not be called by code outside this module.  Unfortunately,
there is no way to enforce this programmatically.  The following commands
are implemented in this module, and should not be called externally:

o removeListItem: remove a node item from a node list
o insertListItem: insert a node item before a given index position in a
                  node list.
o insertListItemBefore: insert a node item before another node item in a
                  node list.
o appendListItem: append a node item to a node list
o prependListItem: prepend a node item to a node list
o popListItem: remove and return the last node item from a node list

Maya commands do two things:

1) Support undo / redo
2) Support interactive execution through string argument parsing.

In this Python module, we are only interested in (1), as we have Python
objects that we can directly work with; converting them to string data to
pass to a command, which would need to convert them back to Python objects,
is wasteful and unnecessary.  This is because these commands are not meant
for interactive invocation, only for undo / redo purposes, and therefore
do not need interactive argument parsing.

Because of this, contrary to standard Maya commands, commands in this
module receive and take ownership of their data directly as Python objects,
on first execution."""

import maya.api.OpenMaya as OpenMaya

import maya.app.renderSetup.model.nodeListPrivate as nodeListPrivate
import maya.app.renderSetup.model.utils as utils
import maya.app.renderSetup.model.typeIDs as typeIDs

import weakref
from collections import deque

#==============================================================================
# CLASS ListItem
#==============================================================================

class ListItem(OpenMaya.MPxNode):
    """List of nodes item base class.

    Nodes that are part of a list must have next item and previous item
    capability, implemented through message connections.
    """

    kTypeId = typeIDs.listItem
    kTypeName = "listItem"

    # List parent message connection attribute.
    parentList = OpenMaya.MObject()

    # Next node, previous node message connection attributes.
    next     = OpenMaya.MObject()
    previous = OpenMaya.MObject()

    def __init__(self):
        super(ListItem, self).__init__()

    def isAbstractClass(self):
        # Used only as base class, cannot be created.
        return True

    # Awkwardly, abstract base classes seem to need a creator method.
    @staticmethod
    def creator():
        return ListItem()

    @staticmethod
    def initializer():
        ListItem.parentList = utils.createDstMsgAttr('parentList', 'pls')
        ListItem.addAttribute(ListItem.parentList)

        ListItem.next = utils.createSrcMsgAttr('next', 'nxt')
        ListItem.addAttribute(ListItem.next)

        ListItem.previous = utils.createDstMsgAttr('previous', 'prv')
        ListItem.addAttribute(ListItem.previous)

    def getNext(self):
        """Return the list item following this one.

        If there is no next item, returns None."""

        nextPlug = utils.findPlug(self, ListItem.next)

        dstPlugs = utils.plugDst(nextPlug)
        if not dstPlugs:
            return None
        nextFn = OpenMaya.MFnDependencyNode(dstPlugs[0].node())
        return nextFn.userNode()
        
    def getPrevious(self):
        """Return the list item before this one.

        If there is no previous item, returns None."""

        previousPlug = utils.findPlug(self, ListItem.previous)

        srcPlug = utils.plugSrc(previousPlug)
        if not srcPlug:
            return None
        previousFn = OpenMaya.MFnDependencyNode(srcPlug.node())
        return previousFn.userNode()

    def setNext(self, item):
        nextPlug     = utils.findPlug(self, ListItem.next)
        previousPlug = utils.findPlug(item, ListItem.previous)

        utils.connect(nextPlug, previousPlug)

    def setPrevious(self, item):
        previousPlug = utils.findPlug(self, ListItem.previous)
        nextPlug     = utils.findPlug(item, ListItem.next)

        utils.connect(nextPlug, previousPlug)

    def parent(self):
        """Returns the list to which this item belongs.

        If the item belongs to no list, None is returned.  This method
        has O(1) time complexity."""

        return utils.getSrcUserNode(utils.findPlug(self, ListItem.parentList))

    def ancestors(self, root=None):
        """Returns the inclusive list of parents of this node.

        The head (start) of the list is the root, and the tail (end) of the
        list is this node.  If a root argument is given, iteration will
        stop at and include this root node, if found."""

        n = self
        a = deque()

        while n:
            a.appendleft(n)
            n = None if n is root else n.parent()

        return a

    def setParent(self, parentListUserNode):
        """Set the list to which this item belongs.

        To remove this item from its list, the parent node argument must be
        None."""

        # Get the parent list to which we belong, which is a destination plug,
        # and disconnect ourselves from the previous parent.
        parentListPlug = utils.findPlug(self, ListItem.parentList)
        utils.disconnectDst(parentListPlug)

        # If we're removing this item from its parent list, nothing more to do.
        if not parentListUserNode:
            return

        # We're setting a non-None parent.  Get the listItems source plug
        # from the parent, and connect ourselves up to it, which makes us
        # an item in our parent's list.
        utils.connect(utils.findPlug(parentListUserNode,
                                     parentListUserNode._getListItemsAttr()),
                      parentListPlug)

    def activate(self):
        '''
        Called when this list item is inserted into the list.
        Override this method to do any scene specific initialization.
        '''
        pass

    def deactivate(self):
        '''
        Called when this list item is removed from the list.
        Override this method to do any scene specific teardown.
        '''
        pass

#==============================================================================
# CLASS ListBase
#==============================================================================

class ListBase(object):
    """List mix-in class.

    This class implements list operations for its derived classes.
    Lists are observable (subjects in the Observer Pattern:

    https://en.wikipedia.org/wiki/Observer_pattern

    ).  Observers are held through weak references.  It is not necessary
    for observers to remove themselves from ListBase subjects when they are
    about to be destroyed (in their __del__ method).  A ListBase subject
    will clean up these zombie observers on next invocation of its
    itemAdded() or itemRemoved().

    Observers are notified with the list item that was added or removed.
    They must have listItemAdded() and listItemRemoved() methods."""

    @classmethod
    def initListItems(cls):
        """Create and return a source message attribute that connects to all list items."""

        listItemsAttr = utils.createSrcMsgAttr('listItems', 'lit')
        cls.addAttribute(listItemsAttr)

        return listItemsAttr

    def __init__(self):
        super(ListBase, self).__init__()
        self._listObservers = []

    # List front and back operations.
    #
    # The list front and back are destination message plugs, so that there
    # can only be one connection to them, as there is only one front and
    # one back list item.  They are connected to the front and back list
    # items through the list item's message plug.
    def getFront(self):
        return utils.getSrcUserNode(utils.findPlug(self, self._getFrontAttr()))
        
    def getBack(self):
        return utils.getSrcUserNode(utils.findPlug(self, self._getBackAttr()))

    def setFront(self, item):
        utils.connectMsgToDst(item, utils.findPlug(self, self._getFrontAttr()))

    def setBack(self, item):
        utils.connectMsgToDst(item, utils.findPlug(self, self._getBackAttr()))

    # List item added / removed methods called by list operations that write
    # to the list (mutating list operations).
    def itemAdded(self, listItem):
        """Call the listItemAdded() methods on list item observers

        The order in which observers are called is not specified."""

        # activate the item to make it go live.  This might cause nodes to begin listening to scene events, etc.
        listItem.activate()

        self._cleanObservers()

        for o in self._listObservers:
            o().listItemAdded(listItem)
        
    def itemRemoved(self, listItem):
        """Call the listItemRemoved() methods on list item observers

        The order in which observers are called is not specified."""

        # deactivate the item so it stops listening to scene events, etc.
        listItem.deactivate()

        self._cleanObservers()

        for o in self._listObservers:
            o().listItemRemoved(listItem)

    def _cleanObservers(self):
        # Clean up zombie observers.
        self._listObservers = [o for o in self._listObservers
                               if o() is not None]

    def addListObserver(self, obs):
        """Add an observer to this list.

        Observers are kept as weak references.  The order in which
        observers are called is unspecified."""

        self._listObservers.append(weakref.ref(obs))

    def removeListObserver(self, obs):
        """Remove an observer from this list.

        Observers are kept as weak references.  ValueError is raised by the 
        remove listItem method if the argument observer is not found."""

        self._listObservers.remove(weakref.ref(obs))

    def clearListObservers(self):
        self._listObservers[:] = []

def reverseListGenerator(list):
    node = list.getBack()
    while node:
        yield node
        node = node.getPrevious()

# Implementation in nodeListPrivate module, as it is needed for implementation
# of insert().
forwardListGenerator = nodeListPrivate.forwardListGenerator

def reverseListNodeClassGenerator(list, cls):
    node = list.getBack()
    while node:
        if isinstance(node, cls):
            yield node
        node = node.getPrevious()

def forwardListNodeClassGenerator(list, cls):
    node = list.getFront()
    while node:
        if isinstance(node, cls):
            yield node
        node = node.getNext()

def isAfter(list, a, b):
    """Return True if a is after b in list.

    No check is made to ensure either argument is a member of the list.
    This function has O(n) time complexity."""

    for item in forwardListGenerator(list):
        foundA = (item == a)
        foundB = (item == b)

        # If we find a first (or at the same time as b), it's not after.
        if foundA:
            return False

        # At this point foundA is False, so if we find b first, a is after.
        if foundB:
            return True

    return False

def remove(list, x):
    """Remove node x from the list, with support for undo.

    This function has the same characteristics as nodeListPrivate.remove(),
    along with support for undo / redo."""

    nodeListPrivate.RemoveCmd.execute(list, x)

def insert(list, ndx, x):
    """Insert node x before position ndx in list.

    This function has the same characteristics as nodeListPrivate.insert(),
    along with support for undo / redo."""

    nodeListPrivate.InsertCmd.execute(list, ndx, x)

def insertBefore(list, nextItem, x):
    """Insert node x before item nextItem in list.

    This function has the same characteristics as nodeListPrivate.insertBefore(),
    along with support for undo / redo."""

    nodeListPrivate.InsertBeforeCmd.execute(list, nextItem, x)

def append(list, x):
    """Append node x to the list.

    This function has the same characteristics as nodeListPrivate.insertBefore(),
    along with support for undo / redo."""

    nodeListPrivate.AppendCmd.execute(list, x)

def prepend(list, x):
    """Add x to the head of the list.

    This function has the same characteristics as nodeListPrivate.prepend(),
    along with support for undo / redo."""

    nodeListPrivate.PrependCmd.execute(list, x)

def pop(list):
    """Pop the last node from the list.
       
    This function has the same characteristics as nodeListPrivate.pop(),
    along with support for undo / redo."""

    return nodeListPrivate.PopCmd.execute(list)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
