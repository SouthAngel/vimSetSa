import maya
maya.utils.loadStringResourcesForModule(__name__)

import maya.api.OpenMaya as OpenMaya

import maya.cmds as cmds

kListCmdPrivate = maya.stringTable['y_nodeListPrivate.kListCmdPrivate' ]


"""List management utilities without undo / redo support.

   This module provides the implementation for list operations that write
   to lists, without undo / redo support.  It is used by the implementation
   of the undo-capable write to list operations in the nodeList module."""

# Not a write operation, but needed by the implementation of insert().
def forwardListGenerator(list):
    node = list.getFront()
    while node:
        yield node
        node = node.getNext()

def remove(list, x):
    """ Remove node x from the list.

        This function will detach the node x from the list if x is an element
        of the list, otherwise nothing will be done.

        It has O(1) time complexity."""

    if x.parent() == list:
        prev = x.getPrevious()
        next = x.getNext()
        if not prev:
            if not next:
                # x is the only node in the list
                list.setBack(None)
                list.setFront(None)
            else:
                # x is the first node in the list
                next.setPrevious(None)
                x.setNext(None)
                list.setFront(next)
        else:
            if not next:
                # x is the last node in the list
                prev.setNext(None)
                x.setPrevious(None)
                list.setBack(prev)
            else:
                prev.setNext(next)
                next.setPrevious(prev)
                x.setPrevious(None)
                x.setNext(None)

        x.setParent(None)
        list.itemRemoved(x)

def insertBefore(list, nextItem, x):
    """Insert node x before item nextItem in list.

    If nextItem is None, element x will be appended to the list.  This function
    has O(1) time complexity."""

    if nextItem is None:
        append(list, x)
    else:
        if list.getFront() == nextItem:
            list.setFront(x)
        x.setPrevious(nextItem.getPrevious())
        x.setNext(nextItem)
        nextItem.setPrevious(x)
        x.setParent(list)
        list.itemAdded(x)

def append(list, x):
    """Append node x to the list.

    This function has O(1) time complexity."""

    back = list.getBack()
    x.setPrevious(back)
    x.setNext(None)
    if back:
        back.setNext(x)
    else:
        list.setFront(x)
    list.setBack(x)
    x.setParent(list)
    list.itemAdded(x)

def prepend(list, x):
    """Add x to the head of the list.

    This function is a convenience for insert(list, 0, x).  It has O(1) time
    complexity."""

    front = list.getFront()
    x.setPrevious(None)
    x.setNext(front)
    if front:
        front.setPrevious(x)
    else:
        list.setBack(x)
    list.setFront(x)
    x.setParent(list)
    list.itemAdded(x)

def insert(list, ndx, x):
    """Insert node x before position ndx in list.

    Positions run from 0 to n-1, for a list of length n.  Inserting at
    position 0 calls prepend(), and thus has O(1) time complexity.
    Inserting mid-list has O(n) time complexity.  Inserting at position n
    or beyond appends to the list, with O(n) time complexity.  To append to
    the list use append() directly, as it has O(1) time complexity."""

    # Inserting at front is a trivial special case
    if ndx == 0:
        prepend(list, x)
    else:
        i = 0
        for node in forwardListGenerator(list):
            if ndx == i:
                previous = node.getPrevious()
                node.setPrevious(x)
                previous.setNext(x)
                x.setPrevious(previous)
                x.setNext(node)
                x.setParent(list)
                list.itemAdded(x)
                break
            i += 1
        else:
            # Ran through the list without finding the index, consider the
            # insert to be an append.
            append(list, x)

def pop(list):
    """Pop the last node from the list.
       
       The method disconnects the last node from list and returns it.  It has
       O(1) time complexity."""

    x = list.getBack()
    if x:
        prev = x.getPrevious()
        if not prev:
            # x is the only node in the list
            list.setBack(None)
            list.setFront(None)
        else:
            prev.setNext(None)
            x.setPrevious(None)
            list.setBack(prev)

        x.setParent(None)
        list.itemRemoved(x)

    return x


#==============================================================================
# CLASS ListCmdBase
#==============================================================================

class ListCmdBase(OpenMaya.MPxCommand):
    """Base class for list commands that write to node lists.

    This command is intended as a base class for concrete list commands."""

    # Command data.  Must be set before creating an instance of the command
    # and executing it.  Ownership of this data is taken over by the
    # instance of the command.
    nodeList = None

    def isUndoable(self):
        return True

    def doIt(self, args):
        # Completely ignore the MArgList argument, as it's unnecessary:
        # arguments to the commands are passed in Python object form
        # directly to the command's constructor.

        if self.nodeList is None:
            self.displayWarning(kListCmdPrivate % self.kCmdName)
        else:
            self.redoIt()

#==============================================================================
# CLASS RemoveCmd
#==============================================================================

class RemoveCmd(ListCmdBase):
    """Remove an item from a list.

    This command is a private implementation detail of this module and should
    not be called otherwise."""
    
    kCmdName = 'removeListItem'

    # Command data.  Must be set before creating an instance of the command
    # and executing it.  Ownership of this data is taken over by the
    # instance of the command.
    listItem = None

    @staticmethod
    def execute(nodeList, listItem):
        """Remove the list item from the node list, and add an entry to the
           undo queue."""

        # Would be nice to have a guard context to restore the class data
        # to its previous value (which is None).  Not obvious how to write
        # a Python context manager for this, as Python simply binds names
        # to objects in a scope.
        RemoveCmd.nodeList = nodeList
        RemoveCmd.listItem = listItem
        cmds.removeListItem()
        RemoveCmd.nodeList = None
        RemoveCmd.listItem = None

    @staticmethod
    def creator():
        # Give ownership of the override to the command instance.
        return RemoveCmd(RemoveCmd.nodeList, RemoveCmd.listItem)

    def __init__(self, nodeList, listItem):
        super(RemoveCmd, self).__init__()
        self.nodeList = nodeList
        self.listItem = listItem
        self.nextItem = None

    def redoIt(self):
        if self.listItem:
            # Save data needed for undo, then remove.
            self.nextItem = self.listItem.getNext()
            remove(self.nodeList, self.listItem)

    def undoIt(self):
        if self.listItem:
            insertBefore(self.nodeList, self.nextItem, self.listItem)

#==============================================================================
# CLASS InsertCmd
#==============================================================================

class InsertCmd(ListCmdBase):
    """Insert a list item before a given position in a list.

    This command is a private implementation detail of this module and should
    not be called otherwise."""
    
    kCmdName = 'insertListItem'

    # Command data.  Must be set before creating an instance of the command
    # and executing it.  Ownership of this data is taken over by the
    # instance of the command.
    ndx      = None
    listItem = None

    @staticmethod
    def execute(nodeList, ndx, listItem):
        """Insert the list item into the node list before position ndx, and
        add an entry to the undo queue."""

        # Would be nice to have a guard context to restore the class data
        # to its previous value (which is None).  Not obvious how to write
        # a Python context manager for this, as Python simply binds names
        # to objects in a scope.
        InsertCmd.nodeList = nodeList
        InsertCmd.ndx      = ndx
        InsertCmd.listItem = listItem
        cmds.insertListItem()
        InsertCmd.nodeList = None
        InsertCmd.ndx      = None
        InsertCmd.listItem = None

    @staticmethod
    def creator():
        # Give ownership of the override to the command instance.
        return InsertCmd(InsertCmd.nodeList, InsertCmd.ndx, InsertCmd.listItem)

    def __init__(self, nodeList, ndx, listItem):
        super(InsertCmd, self).__init__()
        self.nodeList = nodeList
        self.ndx      = ndx
        self.listItem = listItem

    def redoIt(self):
        insert(self.nodeList, self.ndx, self.listItem)

    def undoIt(self):
        remove(self.nodeList, self.listItem)

#==============================================================================
# CLASS InsertBeforeCmd
#==============================================================================

class InsertBeforeCmd(ListCmdBase):
    """Insert a list item before another.

    This command is a private implementation detail of this module and should
    not be called otherwise."""
    
    kCmdName = 'insertListItemBefore'

    # Command data.  Must be set before creating an instance of the command
    # and executing it.  Ownership of this data is taken over by the
    # instance of the command.
    nextItem = None
    listItem = None

    @staticmethod
    def execute(nodeList, nextItem, listItem):
        """Insert the list item into the node list before nextItem, and add an
        entry to the undo queue."""

        # Would be nice to have a guard context to restore the class data
        # to its previous value (which is None).  Not obvious how to write
        # a Python context manager for this, as Python simply binds names
        # to objects in a scope.
        InsertBeforeCmd.nodeList = nodeList
        InsertBeforeCmd.nextItem = nextItem
        InsertBeforeCmd.listItem = listItem
        cmds.insertListItemBefore()
        InsertBeforeCmd.nodeList = None
        InsertBeforeCmd.nextItem = None
        InsertBeforeCmd.listItem = None

    @staticmethod
    def creator():
        # Give ownership of the override to the command instance.
        return InsertBeforeCmd(InsertBeforeCmd.nodeList,
                               InsertBeforeCmd.nextItem,
                               InsertBeforeCmd.listItem)

    def __init__(self, nodeList, nextItem, listItem):
        super(InsertBeforeCmd, self).__init__()
        self.nodeList = nodeList
        self.nextItem = nextItem
        self.listItem = listItem

    def redoIt(self):
        insertBefore(self.nodeList, self.nextItem, self.listItem)

    def undoIt(self):
        remove(self.nodeList, self.listItem)

#==============================================================================
# CLASS AppendCmd
#==============================================================================

class AppendCmd(ListCmdBase):
    """Append an item to a list.

    This command is a private implementation detail of this module and should
    not be called otherwise."""
    
    kCmdName = 'appendListItem'

    # Command data.  Must be set before creating an instance of the command
    # and executing it.  Ownership of this data is taken over by the
    # instance of the command.
    listItem = None

    @staticmethod
    def execute(nodeList, listItem):
        """Append the item to the list, and add an entry to the undo queue."""

        AppendCmd.nodeList = nodeList
        AppendCmd.listItem = listItem
        cmds.appendListItem()
        AppendCmd.nodeList = None
        AppendCmd.listItem = None

    @staticmethod
    def creator():
        # Give ownership of the override to the command instance.
        return AppendCmd(AppendCmd.nodeList, AppendCmd.listItem)

    def __init__(self, nodeList, listItem):
        super(AppendCmd, self).__init__()
        self.nodeList = nodeList
        self.listItem = listItem

    def redoIt(self):
        append(self.nodeList, self.listItem)

    def undoIt(self):
        remove(self.nodeList, self.listItem)

#==============================================================================
# CLASS PrependCmd
#==============================================================================

class PrependCmd(ListCmdBase):
    """Add an item to the head of the list.

    This command is a private implementation detail of this module and should
    not be called otherwise."""
    
    kCmdName = 'prependListItem'

    # Command data.  Must be set before creating an instance of the command
    # and executing it.  Ownership of this data is taken over by the
    # instance of the command.
    listItem = None

    @staticmethod
    def execute(nodeList, listItem):
        """Prepend the item to the list, and add an entry to the undo queue."""

        PrependCmd.nodeList = nodeList
        PrependCmd.listItem = listItem
        cmds.prependListItem()
        PrependCmd.nodeList = None
        PrependCmd.listItem = None

    @staticmethod
    def creator():
        # Give ownership of the override to the command instance.
        return PrependCmd(PrependCmd.nodeList, PrependCmd.listItem)

    def __init__(self, nodeList, listItem):
        super(PrependCmd, self).__init__()
        self.nodeList = nodeList
        self.listItem = listItem

    def redoIt(self):
        prepend(self.nodeList, self.listItem)

    def undoIt(self):
        remove(self.nodeList, self.listItem)

#==============================================================================
# CLASS PopCmd
#==============================================================================

class PopCmd(ListCmdBase):
    """Remove and return the last item from a list.

    This command is a private implementation detail of this module and should
    not be called otherwise."""
    
    kCmdName = 'popListItem'

    # Command return data.  Set by doIt().
    listItem = None

    @staticmethod
    def execute(nodeList):
        """Remove and return the last list item from the node list, and add an
        entry to the undo queue."""

        # Would be nice to have a guard context to restore the class data
        # to its previous value (which is None).  Not obvious how to write
        # a Python context manager for this, as Python simply binds names
        # to objects in a scope.
        PopCmd.nodeList = nodeList
        cmds.popListItem()
        listItem = PopCmd.listItem
        PopCmd.nodeList = None
        PopCmd.listItem = None
        return listItem

    @staticmethod
    def creator():
        # Give ownership of the override to the command instance.
        return PopCmd(PopCmd.nodeList)

    def __init__(self, nodeList):
        super(PopCmd, self).__init__()
        self.nodeList = nodeList

    def doIt(self, args):
        super(PopCmd, self).doIt(args)
        PopCmd.listItem = self.listItem

    def redoIt(self):
        self.listItem = pop(self.nodeList)

    def undoIt(self):
        # If we pop from an empty list, listItem will be None.  This is in
        # fact normal when performing pop in a loop to empty it, since loop
        # termination is on a None return value from pop.
        if self.listItem is not None:
            append(self.nodeList, self.listItem)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
