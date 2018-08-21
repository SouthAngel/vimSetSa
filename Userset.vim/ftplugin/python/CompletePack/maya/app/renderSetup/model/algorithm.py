
import maya.api.OpenMaya as OpenMaya
import itertools
from collections import deque

kUpstream = 0
kDownStream = 1

kDepthFirst = 0
kBreadthFirst = 1

def _getSources(node):
    return (c.source().node() for c in node.getConnections() if c.isDestination)

def _getDestinations(node):
    plugs = itertools.chain.from_iterable(c.destinations() for c in node.getConnections() if c.isSource)
    return (plug.node() for plug in plugs)

def _traverseOne(obj, nexts, predicate, visited):
    node = OpenMaya.MFnDependencyNode(obj)
    name = node.name()
    if name in visited:
        return # already visited, recursion is done
    visited.add(name)
    if not predicate(obj):
        return
    yield obj
    for next in nexts(node):
        for obj in _traverseOne(next, nexts, predicate, visited):
            yield obj

def traverseDepthFirst(objs, direction=kUpstream, predicate=lambda x:True):
    if isinstance(objs, OpenMaya.MObject):
        objs = (objs,)
    nexts = _getSources if direction==kUpstream else _getDestinations
    visited = set() # to prevent infinite loop if there is a cycle
    return itertools.chain.from_iterable(_traverseOne(obj, nexts, predicate, visited) for obj in objs)

def traverseBreadthFirst(objs, direction=kUpstream, predicate=lambda x:True):
    if isinstance(objs, OpenMaya.MObject):
        objs = (objs,)
    nexts = _getSources if direction==kUpstream else _getDestinations
    queue = deque(objs)
    visited = set() # to prevent infinite loop if there is a cycle
    while len(queue) != 0:
        obj = queue.popleft()
        node = OpenMaya.MFnDependencyNode(obj)
        name = node.name()
        if name in visited:
            continue
        visited.add(name)
        if not predicate(obj):
            continue
        yield obj
        queue.extend(nexts(node))
        
def traverse(objs, strategy=kDepthFirst, direction=kUpstream, predicate=lambda x:True):
    return traverseDepthFirst(objs, direction, predicate) if strategy==kDepthFirst else \
        traverseBreadthFirst(objs, direction, predicate)

def _hierarchy(path):
    yield path
    children = (path.child(i) for i in xrange(path.childCount()))
    for obj in children:
        path.push(obj)
        for child in _hierarchy(path):
            yield child
        path.pop()

def hierarchy(paths):
    if isinstance(paths, OpenMaya.MDagPath):
        paths = (paths,)
    for path in paths:
        for child in _hierarchy(path):
            yield OpenMaya.MDagPath(child)


# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
