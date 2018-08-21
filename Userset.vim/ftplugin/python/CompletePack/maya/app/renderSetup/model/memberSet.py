

import maya.api.OpenMaya as OpenMaya

EXCLUDE = -1
NEUTRAL = 0
INCLUDE = 1

class AlreadyHasStatus(Exception):
    pass

class Node(object):
    '''Node in the MemberSet structure. This should only be used by the MemberSet.
    MemberSet should be the only instance to ever create a node.'''
    
    def __init__(self, path=OpenMaya.MDagPath(), status=NEUTRAL):
        self.status = status
        self.path = path
        self.children = dict()
        self.parent = None
    
    def __hash__(self):
        return hash(self.path.fullPathName())

    def __eq__(self, other):
        return self.path.fullPathName() == other.path.fullPathName()
    
    # children accessors, mutators, queries
    def get(self, child):
        return self.children[child]
    
    def add(self, child):
        if child in self:
            # we need to clear the key object in the dictionary, 
            # otherwise it will be kept, and only its value will be changed.
            del self.children[child]
        self.children[child] = child
        child.parent = self

    def remove(self, child):
        if child in self.children:
            child.parent = None
            del self.children[child]

    def __contains__(self, child):
        return child in self.children

    # inclusion/exclusion insertion rules
    def _insert2(self, node, newstatus):
        '''Finds node in the hierarchy. 
        Creates a path to it if it doesn't exist.
        Raises AlreadyHasStatus if the node already implicitly has the status to be set.'''
        if node.path.length() == 0:
            return (self, EXCLUDE)
        parent, status = self._insert2(Node(OpenMaya.MDagPath(node.path).pop()), newstatus)
        
        if node in parent:
            # there already exist inclusion rules for the subpath => keep searching where to insert it
            parent = parent.get(node)
            if parent.status != NEUTRAL and parent.status != status:
                status = parent.status
            return parent, status
        
        if status == newstatus:
            # node is not in parent but the current status is identical to the one we want to set
            # => path implicitly has the given status (newstatus) already
            raise AlreadyHasStatus()
        
        parent.add(node)
        return parent.get(node), status

    def _insert(self, node):
        if node.path.length() == 0:
            raise RuntimeError('should not include world')
        try: parent, status = self._insert2(Node(OpenMaya.MDagPath(node.path).pop()), node.status)
        except AlreadyHasStatus: return
        parent.add(node)
        if status == node.status:
            # remove meaningless tail of neutral elements (they implicitly have the same status as their parent)
            node.status = NEUTRAL
            while parent and node.status == NEUTRAL:
                parent.remove(node)
                parent, node = parent.parent, parent
    
    # query the explicit members
    def _paths(self,status):
        if self.status != NEUTRAL and status != self.status:
            # update status if it changes
            status = self.status
        
        if status == INCLUDE:
            if len(self.children) == 0:
                # an included leaf is always included
                yield self.path
            else:
                # include mode but not a leaf => has excluded descendant in all subpaths
                # => include all children that are not in subpaths
                children = (self.path.child(i) for i in xrange(self.path.childCount()))
                for child in children:
                    self.path.push(child)
                    if Node(self.path) not in self.children:
                        yield self.path
                    self.path.pop()
        
        for child in self.children:
            # yield from children included paths
            for path in child._paths(status):
                yield path  

class MemberSet(object):
    '''Class for creating a set of layer members that will handle explicit 
    inclusion and exclusion of dag paths.'''
    
    def __init__(self):
        self.root = Node(status=EXCLUDE)

    def include(self, path):
        self.root._insert(Node(path,INCLUDE))
        return self

    def exclude(self, path):
        self.root._insert(Node(path,EXCLUDE))
        return self

    def paths(self):
        return self.root._paths(EXCLUDE)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
