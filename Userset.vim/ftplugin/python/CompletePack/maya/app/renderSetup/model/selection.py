import maya.api.OpenMaya as OpenMaya

import maya.app.renderSetup.model.algorithm as algorithm
import itertools

import re

def createProgram(e):
    negate = e.startswith('-')
    if negate: e = e[1:]
    if e == '*': return (negate, re.compile('.*'))
    e = re.escape(e).replace('\\*','[a-zA-Z0-9_]*')
    # recursive namespace syntax ::
    e = e.replace('\:\:', '\:([a-zA-Z0-9_]+\:)*')
    if e.startswith('\:'): e = e[2:]
    return (negate, re.compile("^((.*\|)|)"+e+"$"))

def createNameFilter(expressions):
    # creates a filter function that search for regex name match
    # * used as multi wildcard, - to negate
    # ex: noise* keeps all nodes starting with "noise"
    #    -noise* removes all nodes starting with "noise"
    expressions = [createProgram(e) for e in expressions]
    def filterFunction(name):
        value = False
        for negate, exp in expressions:
            if exp.match(name):
                value = not negate
        return value
    return filterFunction

class Node(object):
    
    def __init__(self, obj):
        self.obj = OpenMaya.MObjectHandle(obj)
    
    def object(self):
        return self.obj.object()
    
    def __hash__(self):
        return self.obj.hashCode()
    
    def __eq__(self, o):
        return self.obj == o.obj

class Selection(object):
    '''Selection of nodes (MObject) and paths (MDagPath). Behaves like a set.'''
    
    def __init__(self, items=None):
        self._paths = dict()  # keys=Node, value=MSelectionList of DagPaths
        self._nondags = set()
        if items:
            self.update(items)

    def dagNodes(self):
        return (node.object() for node in self._paths.iterkeys())
        
    def nonDagNodes(self):
        return (node.object() for node in self._nondags)
        
    def nodes(self):
        return itertools.chain(self.dagNodes(), self.nonDagNodes())
        
    def paths(self):
        lists = (l for l in self._paths.itervalues() if l)
        for l in lists:
            for i in xrange(l.length()):
                yield l.getDagPath(i)
                
    def hierarchy(self):
        return algorithm.hierarchy(self.paths())
        
    def shapes(self):
        return (p for p in self.hierarchy() if p.node().hasFn(OpenMaya.MFn.kShape))
    
    def names(self, allPaths=True):
        nonDagNames = (OpenMaya.MFnDependencyNode(o).name() for o in self.nonDagNodes())
        paths = self.paths() if allPaths else \
            (l.getDagPath(0) for l in self._paths.itervalues() if l)
        pathNames = (p.fullPathName() for p in paths)
        return itertools.chain(pathNames, nonDagNames)

    def ls(self, patterns):
        names = set()
        for pattern in patterns:
            negate, prog = createProgram(pattern)
            update = set.difference_update if negate else set.update
            if '|' in pattern:
                update(names, itertools.ifilter(lambda n: prog.match(n), (p.fullPathName() for p in self.paths())))
            else:
                dags = (key for key in self._paths.iterkeys() if prog.match(OpenMaya.MFnDependencyNode(key.object()).name()))
                update(names, (self._paths[key].getDagPath(0).fullPathName() for key in dags))
                update(names, itertools.ifilter(lambda n: prog.match(n), (OpenMaya.MFnDependencyNode(o.object()).name() for o in self._nondags)))
        return names
    
    def _addMSelection(self, selection):
        for i in range(0,selection.length()):
            try: self._addPath(selection.getDagPath(i))
            except TypeError: self._addNode(selection.getDependNode(i))
    
    def _addPath(self, path):
        node = Node(path.node())
        if node not in self._paths:
            self._paths[node] = OpenMaya.MSelectionList()
        self._paths[node].add(path)
        
    def _addNode(self, obj):
        if obj.hasFn(OpenMaya.MFn.kDagNode):
            self._addPath(OpenMaya.MFnDagNode(obj).getPath())
        else:
            self._nondags.add(Node(obj))
    
    def clear(self):
        self._paths.clear()
        self._nondags.clear()
    
    def add(self, item):
        lst = OpenMaya.MSelectionList()
        lst.add(item)
        self._addMSelection(lst)
    
    def update(self, items):
        lst = items
        if not isinstance(items, OpenMaya.MSelectionList):
            lst = OpenMaya.MSelectionList()
            for item in items:
                lst.add(item)
        self._addMSelection(lst)
    
    def __contains__(self,item):
        lst = OpenMaya.MSelectionList()
        try: lst.add(item)
        except: return False # does not exist
        node = Node(lst.getDependNode(0))
        if node not in self._paths and node not in self._nondags:
            return False
        return True if not node.object().hasFn(OpenMaya.MFn.kDagNode) else self._paths[node].hasItem(lst.getDagPath(0))
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
