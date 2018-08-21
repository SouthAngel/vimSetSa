import maya
maya.utils.loadStringResourcesForModule(__name__)

import maya.api.OpenMaya as OpenMaya

kNameToNodeTypeMismatch = maya.stringTable['y_utils.kNameToNodeTypeMismatch' ]
kAmbiguousName = maya.stringTable['y_utils.kAmbiguousName' ]

def _selectPlug(name):
    sl = OpenMaya.MSelectionList()
    try:
        sl.add(name)
    except RuntimeError:
        # not found
        return None
    if sl.length() > 1:
        # found multiple results (ambiguous)
        raise RuntimeError(kAmbiguousName % name.split('.',1)[0])
    plg = None
    try:
        plg = sl.getPlug(0)
    except TypeError:
        # not a plug
        return None
    if plg.isElement and name.find('[') == -1:
        # Hack because MSelectionList returns a plug over the first element of 
        # a array of plug when no logical index is given
        return None
    return plg

def nodeToLongName(node):
    """Returns the full name of the node, 
    i.e. the absolute path for dag nodes and name for dependency (non-dag) nodes."""
    return OpenMaya.MFnDagNode(node).fullPathName() if node.hasFn(OpenMaya.MFn.kDagNode) else \
           OpenMaya.MFnDependencyNode(node).name()
           
def nodeToShortName(node):
    """Returns the minimum name string necessary to uniquely identify the node."""
    return OpenMaya.MFnDagNode(node).partialPathName() if node.hasFn(OpenMaya.MFn.kDagNode) else \
           OpenMaya.MFnDependencyNode(node).name()

def nameToNode(name):
    """Returns the MObject matching given name or None if not found.
       Raises RuntimeError if name is ambiguous."""
    plg = _selectPlug(name + ".message")
    return plg.node() if plg else None

def nameToDagPath(name):
    """Returns the MDagPath matching given name or None if not found.
       Raises RuntimeError if name is ambiguous."""
    plg = _selectPlug(name + ".message")
    if not (plg and plg.node().hasFn(OpenMaya.MFn.kDagNode)):
        return None
    selection = OpenMaya.MSelectionList()
    selection.add(name)
    return selection.getDagPath(0)

def nameToPlug(name):
    """Returns the MPlug matching given name or None if not found.
       Raises RuntimeError if name is ambiguous."""
    plg = _selectPlug(name)
    if plg is None:
        return None
    # This final check is a hack to detect false positive returned by the selection list
    # because maya "helps" us for example by returning a plug to pSphereShape1.smoothLevel (shape)
    # when we ask for pSphere1.smoothLevel (group) (which doesn't exist in the group...)
    endName1 = name.split('.',1)[0].split('|')[-1]
    endName2 = OpenMaya.MFnDependencyNode(plg.node()).name().split('|')[-1]
    return plg if endName1 == endName2 else None

def findPlug(node, attr):
    """ Return the MPlug corresponding to attr on argument node or None if not found.
    The node argument can be an MObject or a node string name.
    The attr argument can be an MObject or a attr string name.
    Raises RuntimeError if plug is ambiguous."""
    if isinstance(node, basestring):
        attrName = attr if isinstance(attr, basestring) else OpenMaya.MFnAttribute(attr).name
        return nameToPlug(node+"."+attrName)
    
    if isinstance(attr, OpenMaya.MObject):
        plg = OpenMaya.MPlug(node, attr)
    else:
        if attr.find('[') != -1:
            # fn.findPlug doesn't work for elements of arrays
            # use a selection list to find the plug
            return nameToPlug(nodeToLongName(node)+"."+attr)
        if attr.find('.') != -1:
            # fn.findPlug doesn't work for compound paths
            # use last name in compound path as it is unique
            attr = attr.split('.')[-1]

        fn = OpenMaya.MFnDependencyNode(node)
        plg = fn.findPlug(attr, True) if fn.hasAttribute(attr) else None
    
    if not plg or plg.isNull or plg.isArray:
        # an array of plug is not a plug
        return None
     
    if plg.isChild and plg.parent().isElement and plg.parent().logicalIndex() < 0:
        # MAYA-66726: Plugs satisfying this should not be valid plugs
        # Example: "miDefaultOptions.name" satisfies this and is said to be a valid plug
        # its parent is miDefaultOptions.stringOptions[-1] which is an element with invalid logical index...
        return None

    return plg

def removeDuplicates(seq):
    """ Removes all duplicated elements from a list.
    Note that order is not preserved."""
    return list(set(seq))

def getSubClasses(classType):
    cl  = [ classType ]
    for c in classType.__subclasses__():
        cl += getSubClasses(c)
    return cl

def isNodeInstance(node, nodeType):
    return isinstance(OpenMaya.MFnDependencyNode(node).userNode(), nodeType)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
