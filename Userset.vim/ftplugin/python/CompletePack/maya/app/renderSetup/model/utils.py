import maya.api.OpenMaya as OpenMaya
import maya.cmds as cmds

import maya.app.renderSetup.common.utils as commonUtils
import maya.app.renderSetup.model.plug as plug
import maya.app.renderSetup.model.typeIDs as typeIDs
from maya.app.renderSetup.model.utilsModelStrings import *

# Declaration of the data types supported by our 
# numeric and generic attributes
#
kSupportedSimpleTypes = set([
    OpenMaya.MFnNumericData.kFloat,
    OpenMaya.MFnNumericData.kDouble,
    OpenMaya.MFnNumericData.kInt,
    OpenMaya.MFnNumericData.kShort,
    OpenMaya.MFnNumericData.kBoolean,
])
kSupportedVectorTypes = set([
    OpenMaya.MFnNumericData.k2Float,
    OpenMaya.MFnNumericData.k3Float,
    OpenMaya.MFnNumericData.k2Double,
    OpenMaya.MFnNumericData.k3Double,
    OpenMaya.MFnNumericData.k2Int,
    OpenMaya.MFnNumericData.k3Int,
    OpenMaya.MFnNumericData.k2Short,
    OpenMaya.MFnNumericData.k3Short,
])

def nameToUserNode(name):
    node = commonUtils.nameToNode(name)
    return OpenMaya.MFnDependencyNode(node).userNode() if node else None

def nameToExistingUserNode(name):
    node = nameToUserNode(name)
    if node is None:
        raise RuntimeError(kNoSuchNode % name)
    return node

def canOverrideNode(node):
    if node.isNull():
        return False
    
    # We do not care about changes to certain node types.
    # This list could grow
    
    # We only care about dependency nodes and we don't care
    # about manipulators, group id and parts, components, or render layers...
    if not node.hasFn(OpenMaya.MFn.kDependencyNode) or \
        node.hasFn(OpenMaya.MFn.kManipulator3D) or \
        node.hasFn(OpenMaya.MFn.kGroupId) or \
        node.hasFn(OpenMaya.MFn.kGroupParts) or \
        node.hasFn(OpenMaya.MFn.kComponent) or \
        node.hasFn(OpenMaya.MFn.kRenderLayer) or \
        node.hasFn(OpenMaya.MFn.kRenderLayerManager) or \
        node.hasFn(OpenMaya.MFn.kObjectFilter) or \
        node.hasFn(OpenMaya.MFn.kSelectionListOperator) or \
        node.hasFn(OpenMaya.MFn.kSelectionListData ) or \
        node.hasFn(OpenMaya.MFn.kReference ) or \
        node.hasFn(OpenMaya.MFn.kSelectionListOperator) or \
        node.hasFn(OpenMaya.MFn.kFilter) or \
        node.hasFn(OpenMaya.MFn.kNodeGraphEditorInfo) or \
        node.hasFn(OpenMaya.MFn.kScript):
        return False

    if not cmds.objExists(OpenMaya.MFnDependencyNode(node).name()):
        # this is True if the node is internal
        return False

    # and we definitely don't want to include our own nodes
    depNode = OpenMaya.MFnDependencyNode(node)
    if typeIDs.isRenderSetupType(depNode.typeId):
        return False

    if node.hasFn(OpenMaya.MFn.kShape) and OpenMaya.MFnDagNode(node).getPath().length() <= 1:
        # shapes without transforms are invalid
        # yet defaultDirectionalLight (created at render time) satisfies this
        return False
    
    return True

def createSrcMsgAttr(longName, shortName):
    """Create a source (a.k.a. output, or readable) message attribute."""
    msgAttrFn = OpenMaya.MFnMessageAttribute()
    attr = msgAttrFn.create(longName, shortName)
    msgAttrFn.writable = False
    msgAttrFn.storable = False
    return attr

def createDstMsgAttr(longName, shortName):
    """Create a destination (a.k.a. input, or writable) message attribute."""
    msgAttrFn = OpenMaya.MFnMessageAttribute()
    attr = msgAttrFn.create(longName, shortName)
    msgAttrFn.writable = True
    # Since message attributes carry no data, does storable mean anything?
    msgAttrFn.storable = True
    return attr

def createGenericAttr(longName, shortName):
    attrFn = OpenMaya.MFnGenericAttribute()
    attrObj = attrFn.create(longName, shortName)
    attrFn.addDataType(OpenMaya.MFnData.kAny)

    # All simple generic numeric types are equivalent,
    # and we can only add one, so just a kDouble here
    attrFn.addNumericType(OpenMaya.MFnNumericData.kDouble)

    # Add vector types
    for t in kSupportedVectorTypes:
        attrFn.addNumericType(t)

    return attrObj

def plugSrc(dstPlug):
    """Return the source of a connected destination plug.

    If the destination is unconnected, returns None."""
    src = dstPlug.source()

    return None if src.isNull else src

def plugDst(srcPlug):
    """Return the destinations of a connected source plug.

    If the source is unconnected, returns None."""
    plugArray = srcPlug.destinations()

    return None if len(plugArray) == 0 else plugArray

def connect(src, dst):
    """Connect source plug to destination plug.

    If the dst plug is None, the src plug will be disconnected from all its
    destinations (if any).  If the src plug is None, the dst plug will be
    disconnected from its source (if any).  If both are None, this function
    does nothing.  If the destination is already connected, it will be
    disconnected."""

    dgMod = OpenMaya.MDGModifier()

    if src:
        if dst:
            if dst.isDestination:
                oldSrc = plugSrc(dst)
                if oldSrc == src:
                    # This connection is already made
                    return
                dgMod.disconnect(oldSrc, dst)
            dgMod.connect(src, dst)
        else:
            destinations = plugDst(src)
            # None is not iterable.
            if destinations:
                for dst in destinations:
                    dgMod.disconnect(src, dst)
    else:
        if dst:
            src = plugSrc(dst)
            if src:
                dgMod.disconnect(src, dst)
        else:
            # Both src and dst are None, nothing to do.
            pass

    dgMod.doIt()

def disconnect(src, dst):
    dgMod = OpenMaya.MDGModifier()
    dgMod.disconnect(src, dst)
    dgMod.doIt()

def disconnectSrc(src):
    """Disconnect a source (readable) plug from all its destinations.

    Note that a single plug can be both source and destination, so this
    interface makes the disconnection intent explicit."""
    if src.isCompound:
        for i in range(0, src.numChildren()):
            disconnectSrc(src.child(i)) 
    connect(src, None)

def disconnectDst(dst):
    """Disconnect a destination (writable) plug from its source.

    Note that a single plug can be both source and destination, so this
    interface makes the disconnection intent explicit."""
    if dst.isCompound:
        for i in range(0, dst.numChildren()):
            disconnectDst(dst.child(i)) 
    connect(None, dst)

def connectMsgToDst(userNode, dst):
    """ Connect the argument userNode's message attribute to the
        argument dst plug.

        If the userNode is None the dst plug is disconnected
        from its sources.
        
        If the dst plug is None the userNode's message plug
        is disconnected from its destinations """

    msgPlug = None
    if userNode:
        fn = OpenMaya.MFnDependencyNode(userNode.thisMObject())
        msgPlug = fn.findPlug('message', False)

    connect(msgPlug, dst)

def getSrcUserNode(dst):
    """ Get the user node connected to the argument dst plug.
        Note: Only applies to MPxNode derived nodes

    If the dst plug is unconnected, None is returned."""

    src = plugSrc(dst)
    if not src:
        return None

    srcFn = OpenMaya.MFnDependencyNode(src.node())
    return srcFn.userNode()

def getDstUserNodes(src):
    """Get the user nodes connected to the argument src plug.
        Note: Only applies to MPxNode derived nodes

    If the src plug is unconnected, None is returned."""

    dst = plugDst(src)
    if not dst:
        return None

    return [OpenMaya.MFnDependencyNode(d.node()).userNode() for d in dst]

def getSrcNode(dst):
    """ Get the node connected to the argument dst plug.
    """
    src = plugSrc(dst)
    if not src:
        return None

    return src.node()

def getSrcNodeName(dst):
    """ Get the name of the node connected to the argument dst plug.
    """
    srcNode = getSrcNode(dst)
    if not srcNode:
        return None

    srcFn = OpenMaya.MFnDependencyNode(srcNode)
    return srcFn.name()

def findPlug(userNode, attr):
    """Return plug corresponding to attr on argument userNode.

    If the argument userNode is None, or the attribute is not found, None
    is returned.
    """
    if not userNode:
        return None

    fn = OpenMaya.MFnDependencyNode(userNode.thisMObject())
    return fn.findPlug(attr, False)

def _isDestination(plug):
    """ Returns True if the given plug is a destination plug, and False otherwise.

    If the plug is a compond attribute it returns True if any of it's children is a 
    destination plug.
    """
    if plug.isDestination:
        return True
    if plug.isCompound:
        for idx in range(0, plug.numChildren()):
            if _isDestination(plug.child(idx)):
                return True
    return False

def _transferConnectedPlug(src, dst):
    if src.isDestination:
        fromSrc = plugSrc(src)
        connect(fromSrc, dst)
    elif src.isCompound and dst.isCompound:
        for idx in range(0, src.numChildren()):
            transferPlug(src.child(idx), dst.child(idx))

def transferPlug(src, dst):
    """ Transfer the connection or value set on plug 'src' on to the plug 'dst'."""
    if _isDestination(src):
        # src is connected
        # so transfer the connection
        _transferConnectedPlug(src, dst)
    else:
        # src is not connected
        # Break any connection on dst and then
        # transfer value instead
        if dst.isDestination:
            disconnectDst(dst)
        plug.Plug(dst).copyValue(src)

def deleteNode(node):
    """Remove the argument node from the graph.

    This function is undoable."""

    # For efficiency, should be code as:
    #
    # dgMod = OpenMaya.MDGModifier()
    # dgMod.deleteNode(node.thisMObject())
    # dgMod.doIt()
    #
    # This removes the need for the name-based lookup done by the delete
    # command, since we already have the object.  However, the above three
    # lines of code are not undoable, and would need to be wrapped into an
    # MPxCommand with a redoIt() and undoIt() in order to be undoable.
    # Therefore, for ease of maintenance, simply use the delete command.

    cmds.delete(node.name())


def _findShader(shadingEngine, attribute, classification=None):
    '''
    Returns the shader connected to given attribute on given shading engine.
    Optionally search for nodes from input connections to the shading engines 
    satisfying classification if plug to attribute is not a destination and
    a classification string is specified.
    '''
        
    # If expected input attribute to a shading node DOES have a node as source, take it. We're done.
    # Otherwise, we're in a non-standard connection from shader to shading engine.
    #  => search for alternate input connection by node classification.
    # Idea is: avoid heavy computation (searching) if we can. => Try expected scenario, and search on fail.
    
    node = OpenMaya.MFnDependencyNode(shadingEngine)
    # Try "standard scenario" first to avoid searching
    plg = node.findPlug(attribute, False)
    if plg.isDestination:
        return plg.source().node()
    elif classification:
        # We're not in the standard scenario (shader might be connected through plugin's added attributes)
        # (some mentalray's shaders work this way for example)
        # Then search for input connections satifying classification
        sources = (plg.source().node() for plg in node.getConnections() if plg.isDestination)
        for source in sources:
            for c in OpenMaya.MFnDependencyNode.classification(OpenMaya.MFnDependencyNode(source).typeName).split(':'):
                if c.startswith(classification):
                    return source
    return None

def getCollectionsRecursive(parent):
    for child in parent.getCollections():
        yield child
        for c in getCollectionsRecursive(child):
            yield c

def getOverridesRecursive(parent):
    import maya.app.renderSetup.model.override as override
    if isinstance(parent, override.Override):
        yield parent
        return
    for child in parent.getChildren():
        for ov in getOverridesRecursive(child):
            yield ov

def findSurfaceShader(shadingEngine, search=False):
    '''Returns the surface shader (as MObject) of the given shading engine (as MObject).'''
    return _findShader(shadingEngine, 'surfaceShader', 'shader/surface' if search else None)
    
def findDisplacementShader(shadingEngine, search=False):
    '''Returns the displacement shader (as MObject) of the given shading engine (as MObject).'''
    return _findShader(shadingEngine, 'displacementShader', 'shader/displacement' if search else None)
    
def findVolumeShader(shadingEngine, search=False):
    '''Returns the volume shader (as MObject) of the given shading engine (as MObject).'''
    return _findShader(shadingEngine, 'volumeShader', 'shader/volume' if search else None)

def isShadingType(typeName):
    classif = OpenMaya.MFnDependencyNode.classification(typeName)
    return reduce(lambda out, c: out or c in classif, ('shader', 'texture'), False)
    
def isShadingNode(obj):
    return isShadingType(OpenMaya.MFnDependencyNode(obj).typeName)

def isSurfaceShaderType(typeName):
    return 'shader/surface' in OpenMaya.MFnDependencyNode.classification(typeName)

def isSurfaceShaderNode(obj):
    return isSurfaceShaderType(OpenMaya.MFnDependencyNode(obj).typeName)
    
def isExistingType(t):
    try: return t and cmds.nodeType(t,isTypeName=True)
    except: return False

def isInheritedType(parentTypeName, childTypeName):
    try: return childTypeName and parentTypeName in cmds.nodeType(childTypeName, inherited=True, isTypeName=True)
    except: return False

def isExistingClassification(t):
    try: return t and cmds.listNodeTypes(t) is not None
    except: return False

# Fonctions to compute the number of operations when layer are switched
def _recursiveSearch(colList):
    if not colList:
        return 0
    result = 0
    for col in colList:
        result += 1
        result += len(col.getOverrides())
        result += _recursiveSearch(col.getCollections())
    return result

def getTotalNumberOperations(model):
    import maya.app.renderSetup.model.renderSetup as renderSetupModel
    newLayer = model
    oldLayer = renderSetupModel.instance().getVisibleRenderLayer()
    totalTopNumberOperations = 0
    if(oldLayer and not oldLayer == renderSetupModel.instance().getDefaultRenderLayer()):
        totalTopNumberOperations += _recursiveSearch(oldLayer.getCollections())
    if(newLayer and not newLayer == renderSetupModel.instance().getDefaultRenderLayer() and newLayer != oldLayer):
        totalTopNumberOperations += _recursiveSearch(newLayer.getCollections())
    totalTopNumberOperations += 3
    return totalTopNumberOperations

def notUndoRedoing(f):
    '''Decorator that will call the decorated method only if not currently in undoing or redoing.
    Particularly useful to prevent callbacks from generating commands since that would clear the redo stack.'''
    def wrapper(*args, **kwargs):
        if not OpenMaya.MGlobal.isUndoing() and not OpenMaya.MGlobal.isRedoing():
            return f(*args, **kwargs)
    return wrapper
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
