#!/usr/bin/env python
import maya
maya.utils.loadStringResourcesForModule(__name__)

"""
creaseSetEditor

Description:
The CreaseSetEditor creates a hierarchal tree view that has editable and
sortable columns. It adjusts based on the Maya scene changes and selection
changes. It can adjust the Maya scene and selections. It additionally has
middle-mouse drag to set the crease values just like the channel box.

Compatibility:
This will work with standard Maya 2012 (as it contains stubs to simulate the creaseSet backend)
and also the Pixar cut of Maya with the CreaseSet backend.

Author:
Scot Brew

Usage:
import creaseSetEditor
reload(creaseSetEditor)
a = creaseSetEditor.showCreaseSetEditor()
"""

import sys
import os
import types
import logging
import collections
import math
import uuid

# Import available PySide or PyQt package, as it will work with both
try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    from shiboken2 import wrapInstance
    _qtImported = 'PySide2'
except ImportError, e1:
    try:
        from PyQt4.QtCore import *
        from PyQt4.QtGui import *
        from sip import wrapinstance as wrapInstance
        _qtImported = 'PyQt4'
    except ImportError, e2:
        raise ImportError, "%s, %s"%(e1,e2)
    
# Workarounds for Qt interface nuances
if not hasattr(Qt, 'MiddleButton'):
    Qt.MiddleButton = Qt.MidButton # some Qt code uses MidButton and other places it uses MiddleButton

import maya.cmds
import maya.utils
from maya import OpenMaya as om
from maya import OpenMayaUI as omui


# ==============
# LOGGING
#   Use the python standard logging module to control logging info, warning, and
#   debug statements for the editor.  By default, only warnings and errors are displayed
#   After is module is loaded, the logging level can be specified.
#   This is useful for debugging, 
# Usage:
#     creaseSetEditor.logger.setLevel(logging.DEBUG)
# ==============

logger = logging.getLogger('CreaseSetEditor')
#logger.setLevel(logging.INFO)
#logger.setLevel(logging.DEBUG)
if len(logger.handlers) == 0:
    formatter = logging.Formatter('[%(name)s] %(levelname)s: %(message)s')
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.propagate=0   # do not propagate to the standard Maya logger or it will double-represent it in the logs


# ==============
# GLOBALS
# ==============

# color attribute not currently support for edge sets
_edgeSetColorSupported = False

# This method is meant to be used when a particular string Id is needed more than
# once in this file.  The Maya Python pre-parser will report a warning when a
# duplicate string Id is detected.
def _loadUIString(strId):
	try:
		return {
			'kNonMeshOrTransform': maya.stringTable['y_creaseSetEditor.kNonMeshOrTransform' ],
			'kPleaseSelectMeshesOrCreaseSets': maya.stringTable['y_creaseSetEditor.kPleaseSelectMeshesOrCreaseSets' ],
			'kComponentsMovedWarning': maya.stringTable['y_creaseSetEditor.kComponentsMovedWarning' ],
			'kOkButton': maya.stringTable['y_creaseSetEditor.kOkButton' ],
			'kCancelButton' :maya.stringTable['y_creaseSetEditor.kCancelButton' ],
			'kInvalidCreaseEditorClass': maya.stringTable['y_creaseSetEditor.kInvalidCreaseEditorClass' ],
		}[strId]
	except KeyError:
		return " "



# ==============
# MAYA CLASS CONVERSION UTILITIES
#   Functions that aid in converting between MEL-style function arguements
#   and C++ API style function arguments
# ==============

def getDependNode(nodeName):
    """Get an MObject (depend node) for the associated node name

    :Parameters:
        nodeName
            String representing the node
    
    :Return: depend node (MObject)

    """
    selList = om.MSelectionList()
    selList.add(nodeName)
    dependNode = om.MObject()
    selList.getDependNode(0, dependNode)
    return dependNode


# ==============
# UNDO BLOCKS
#   Classes to be used with the 'with' command to denote specific blocks
#   that should handle undo in a certain way
# ==============
class MayaUndoChunk:
    '''Safe way to manage group undo chunks using the 'with' command.
    It will close the chunk automatically on exit from the block
    
    :Example:
        maya.cmds.polyCube()
        with MayaUndoChunk():
            maya.cmds.polyCube()
            maya.cmds.polyCube()
        maya.cmds.undo()
    '''
    def __init__(self, name='unnamedChunk'):
        self.name = name 
    def __enter__(self):
        maya.cmds.undoInfo(openChunk=True, chunkName=self.name)
        return None
    def __exit__(self, type, value, traceback):
        maya.cmds.undoInfo(closeChunk=True)


class MayaSkipUndoChunk:
    '''Safe way to using the 'with' command to create a block of commands that are not added to the undo queue.
    It will close the chunk automatically on exit from the block and
    restore the existing undo state.
    
    :Example:
        cmds.polyCube()
        with MayaSkipUndoChunk():
            cmds.polyCube()
            cmds.polyCube()
        cmds.polyCube()
    '''
    def __enter__(self):
        self.undoState = maya.cmds.undoInfo(q=True, state=True)
        if self.undoState == True:
            maya.cmds.undoInfo(stateWithoutFlush=False)
        return None
    def __exit__(self, type, value, traceback):
        if self.undoState == True:
            maya.cmds.undoInfo(stateWithoutFlush=True)


# ==============
# NON-UI GENERAL FUNCTIONS
#   Separating the UI from the functions decouples them and allows for these
#   functions to be called independently of the UI in other scripts or for testing.
# ==============
def getSelectedMeshComponents(items=None, verts=False, edges=False, meshShapes=False, expand=False):
    '''Return a list of the selected mesh components

    :Parameters:
        items ([string])
            items to filter.  If unspecified, then the function will act on the selected items.
        verts (bool)
            include mesh vertices in the list (default=False)
        edges (bool)
            include mesh edges in the list (default=False)
        meshShapes (bool)
            include mesh shapes (default=False)
        expand (bool)
            list each individual component as a separate item.  If false, compress the component list. (default=False)
    
    :Limitation:
        The returned component list will have dupliate components if both the meshShape and components are specified (or selected)
        in the list of items and meshShapes=True and at the verts/edges components equal True.
    
    :Return: list of component items ([string])
    '''
    # Convert arguments to the selectionMask list
    selectionMask = []
    if verts:
        selectionMask.append(31)
    if edges:
        selectionMask.append(32)

    # Perform filterExpand command for the components
    selItems = []
    if len(selectionMask) > 0:
        if items == None:
            selItems = maya.cmds.filterExpand(selectionMask=selectionMask, expand=expand)  # get a list of selected edges and verts
        else:
            selItems = maya.cmds.filterExpand(items, selectionMask=selectionMask, expand=expand)  # get a list of selected edges and verts
        # Workaround: The 'filterExpand' command can return None.  Convert that to an empty list [] for continuity of return value
        if selItems == None:
            selItems = []

    # Optionally add the components of mesh shapes.  This can be useful if wanting to do a listSets() and find all sets
    # that the mesh has its components in
    if meshShapes == True:
        if items == None:
            dagItems = maya.cmds.ls(dag=True, sl=True, noIntermediate=True, type='mesh') # all selected mesh shapes
        else:
            dagItems = maya.cmds.ls(items, dag=True, noIntermediate=True, type='mesh')   # all specified mesh shapes from the "items" arg
        # add the components (expand or leave the components in compact form, depending on the expand arg)
        if len(dagItems) > 0:
            selItems.extend( maya.cmds.ls( maya.cmds.polyListComponentConversion(dagItems, tv=True, te=True), flatten=expand ))
            
    # Return the list of components
    logger.debug('getSelectedMeshComponents selItems: %s'%selItems)
    return selItems


def filterComponentsBySelectedItems(components):
    '''Filters list of components against exact match of selected components or all the components for selected meshes.

    :Parameters:
        components ([string])
            component items to filter against the current selection
            
    :Return: list of items ([string])

    :Example:
        cmds.select('pCube1', 'pCube2.e[2:5]')
        filterComponentsBySelectedItems(['pCube1.e[2]', 'pCube1.e[4]', 'pCube2.e[1]', 'pCube2.e[2]', 'pCube3.e[1]'])
        # Result: ['pCube1.e[2]', 'pCube1.e[4]', 'pCube2.e[2]']
    '''
    filteredComponents = []
    flattenedComponents = maya.cmds.ls(components, flatten=True) # use this so can do a direct name comparison below
    selectedObjs  = set(maya.cmds.ls(sl=True, dag=True, noIntermediate=True))
    selectedComps = set(getSelectedMeshComponents(verts=True, edges=True, expand=True))  # get a flattened list of selected edges and verts
    logger.debug('filterComponentsBySelectedItems: Original (%i): %s'%(len(flattenedComponents), flattenedComponents))
    logger.debug('filterComponentsBySelectedItems: selectedObjs: %s'%selectedObjs)
    logger.debug('filterComponentsBySelectedItems: selectedComps: %s'%selectedComps)
    if len(selectedObjs)>0 or len(selectedComps)>0:
        filteredComponents = [i for i in flattenedComponents if ((i in selectedComps) or (i.split('.',1)[0] in selectedObjs ))]
        logger.debug('filterComponentsBySelectedItems: Filtered (%i): %s'%(len(filteredComponents), filteredComponents))
    return filteredComponents


def getCreaseSetPartition():
    """Returns a singleton 'creasePartition' shared node.  It creates one if it does not already exist.
    
    :Return: nodeName string to the creasePartition (string)
    """
    nodes = maya.cmds.ls('creasePartition', type='partition')
    if len(nodes) > 0:
        creasePartition = nodes[0]
    else:
        creasePartition = maya.cmds.createNode('partition', name='creasePartition', shared=True)  # NOTE: This is a shared node
    return creasePartition


def newCreaseSet(name='creaseSet#', elements=None, creaseLevel=2):
    '''Create a crease set
    
    :Parameters:
        name (string)
            Name of the creaseSet node
        elements ([string])
            List of edges and vertices to add to the creaseSet
        creaseLevel (float)
            Initial creasing for the creaseSet creaseLevel attribute
            
    :Return: None
    '''
    # NOTE: The polyCreaseCtx requires edges to be selected and also does not return the created CreaseSet name
    #       Not very useful
    #cs = maya.cmds.polyCreaseCtx('polyCreaseContext', edit=True, createSet="CreaseSet")

    # Store off original selection
    selObjs = maya.cmds.ls(sl=True) 

    # Determine items to add to set (if not explicitly specified)
    if elements == None:
        elements = getSelectedMeshComponents(verts=True, edges=True, expand=False)

    with MayaUndoChunk('newCreaseSet'): # group the following actions in this block into a single undo chunk
        # Create creaseSet
        cs = maya.cmds.createNode('creaseSet', name=name)
        
        # Add to creasePartition
        cp = getCreaseSetPartition()
        maya.cmds.partition(cs, add=cp)
    
        # Add members
        if len(elements) > 0:
            shared = getCreaseSetsContainingItems(items=elements,asDict=False)
            shared.discard(cs) # discard target creaseSet so not to perform comparisons against it below
            if len(shared) > 0:
                maya.cmds.warning(_loadUIString('kComponentsMovedWarning'))

            # add items to selected set
            maya.cmds.sets(*elements, forceElement=cs)  # can also use include to not force items

            # remove any shared items because forceElement doesn't always work
            for s in shared:
                intersection = maya.cmds.sets(cs, intersection=s)
                if len(intersection) > 0:
                    maya.cmds.sets(*intersection, remove=s)

        # Set Attrs
        if creaseLevel != 0:
            maya.cmds.setAttr('%s.creaseLevel'%cs, creaseLevel)
        
        # Restore original selection
        if len(selObjs) > 0:
            maya.cmds.select(selObjs)
        else:
            maya.cmds.select(clear=True)
    
    # Return created set
    return cs


def getCreaseSetsContainingItems(items=None, asDict=False):
    '''Return list of sets that have edge/vertex members with the specified items

    :Parameters:
        items ([string])
            The edge and vertex items to look for in the creaseSet nodes.
            If mesh shapes are included, it will return all creaseSet nodes
            used by the mesh shapes as well.  If "None", then operate on the
            selected items.
        asDict (bool)
            if true, return a dict
            if false, return a set
            (default=False)
            
    :Limitation:
        If both a mesh and some of its components are selected/specified, then this function
        will return an artificially elevated count of selected members for the asDict=True option.
        It will add the total number of member components for the mesh and then additionally add
        the number of member components for the selected/specified components.
            
    :Return: Set of creaseSet names or dict in the format {creaseSet: numItems}
    '''
    logger.debug('In getCreaseSetsContainingItems(items=%s, asDict=%i)'%(items, asDict))
    
    # Results to return
    dictContainingItems = collections.defaultdict(int)  # dict: {creaseSet: numItems)
    setsContainingItems = set()

    #
    # NOTE: Using the API operations to provide faster performance than the less direct MEL-style commands
    # In some large models with 50,000+ crease items it was taking 17 seconds to select items.  With the API calls, it is negligible.
    #

    # Create MSelectionList
    selList = om.MSelectionList()
    if items != None:
        for item in items:
            selList.add(item)
    else:
        # Get the current selection
        om.MGlobal.getActiveSelectionList(selList)


    # Loop over items and perform operations if is a meshShape
    dagPath   = om.MDagPath()
    component = om.MObject()
    processedTransObjHandles = set()  # track processed items
    itSelList = om.MItSelectionList(selList)
    while (not itSelList.isDone() ):
        # Process only dag objects and components
        if (itSelList.itemType() == om.MItSelectionList.kDagSelectionItem):
            
            # Process only dagPaths that are mesh shapes (or transforms of mesh shapes)
            itSelList.getDagPath(dagPath, component)       
            if dagPath.hasFn(om.MFn.kMesh):
                
                # Filter to not re-iterate over both the transform and the shape if both are in the selection list
                dagPathTransObjHandle =  HashableMObjectHandle(dagPath.transform())
                if (not component.isNull()) or (dagPathTransObjHandle not in processedTransObjHandles):
                    processedTransObjHandles.add( HashableMObjectHandle(dagPath.transform()) ) # update processed item set
        
                    # Process mesh and mesh components
                    meshFn = om.MFnMesh(dagPath)
                    
                    connectedSets = om.MObjectArray()
                    connectedSetMembers = om.MObjectArray()
                    meshFn.getConnectedSetsAndMembers(dagPath.instanceNumber(), connectedSets, connectedSetMembers, False)
                              
                    # Add all members for each creaseSet
                    for iConnectedSets in range(connectedSets.length()):
                        if connectedSets[iConnectedSets].hasFn(om.MFn.kCreaseSet):  # if is a creaseSet
                            # Gather the creaseSet name and members for this mesh
                            creaseSetName = om.MFnSet(connectedSets[iConnectedSets]).name()
                            creaseSetMemberSelList = om.MSelectionList()
                            if not connectedSetMembers[iConnectedSets].isNull():
                                creaseSetMemberSelList.add(dagPath, connectedSetMembers[iConnectedSets])
                                    
                            # Filter to the selected components (if a component is specified, otherwise add all the items)
                            # NOTE: Suggestion made to add MSelectionList.intersection() in MAYA-14750
                            if not component.isNull():
                                # perform intersection of the lists
                                selListToRemoveItems = om.MSelectionList(creaseSetMemberSelList)
                                selListToRemoveItems.merge(dagPath, component, om.MSelectionList.kRemoveFromList)                   
                                if not selListToRemoveItems.isEmpty():
                                    creaseSetMemberSelList.merge(selListToRemoveItems, om.MSelectionList.kRemoveFromList)
            
                            # Update results to return
                            if asDict:
                                for iCreaseSetMemberSelList in range(creaseSetMemberSelList.length()):
                                    creaseSetMemberSelList_dagPath = om.MDagPath()
                                    creaseSetMemberSelList_component = om.MObject()
                                    creaseSetMemberSelList.getDagPath(iCreaseSetMemberSelList, creaseSetMemberSelList_dagPath, creaseSetMemberSelList_component)
                                    if not creaseSetMemberSelList_component.isNull():
                                        dictContainingItems[creaseSetName] += om.MFnComponent(creaseSetMemberSelList_component).elementCount()
                            else:
                                if not creaseSetMemberSelList.isEmpty():
                                    setsContainingItems.add(creaseSetName)
                            
        # Iterate to next itSelList item
        itSelList.next()

    # return results
    if asDict:
        logger.debug("dictContainingItems: %s"%dictContainingItems)
        return dictContainingItems
    else:
        logger.debug("setsContainingItems: %s"%setsContainingItems)
        return setsContainingItems


def bakeOutCreaseSetValues(meshes):
    '''Bake out the CreaseSet values from the specified meshes directly onto
    the meshes and remove the components from the CreaseSet.

    :Parameters:
        meshes ([string])
            The mesh shape nodes or mesh transforms to act upon
            
    :Return: None
    '''
    with MayaUndoChunk('bakeCreaseSet'): # group the following actions in this block into a single undo chunk
        emptySetsToDelete = []
        for mesh in meshes:
            # get the mesh transform
            if maya.cmds.objectType(mesh, isAType='transform'):
                meshT = mesh
            else:
                # See if it is a mesh shape
                if maya.cmds.objectType(mesh, isAType='mesh'):
                    meshT = maya.cmds.listRelatives(mesh, parent=True, path=True)[0]
                else:
                    maya.cmds.warning(_loadUIString('kNonMeshOrTransform')%mesh)
                    continue
            
            # Get crease values (to set later directly onto the mesh)
            creaseValuesE = maya.cmds.polyCrease('%s.e[:]'%meshT, query=True, value=True)
            creaseValuesV = maya.cmds.polyCrease('%s.vtx[:]'%meshT, query=True, vertexValue=True)
            
            # Remove from existing CreaseSets (and thus clear the creasing)
            setsForMeshE = getCreaseSetsContainingItems(['%s.e[:]'%meshT])
            for s in setsForMeshE:
                maya.cmds.sets( '%s.e[:]'%meshT, remove=s)
                setMembers = maya.cmds.sets(s, q=True)
                if setMembers == None:
                    setMembers = []
                if len(setMembers) == 0:
                    emptySetsToDelete.append(s)

            setsForMeshV = getCreaseSetsContainingItems(['%s.vtx[:]'%meshT])
            for s in setsForMeshV:
                maya.cmds.sets( '%s.vtx[:]'%meshT, remove=s)
                setMembers = maya.cmds.sets(s, q=True)
                if setMembers == None:
                    setMembers = []
                if len(setMembers) == 0:
                    emptySetsToDelete.append(s)
    
            # Explicitly assign new crease values directly to the mesh
            maya.cmds.polyCrease('%s.e[:]'%meshT, value=creaseValuesE, ch=True)
            maya.cmds.polyCrease('%s.vtx[:]'%meshT, vertexValue=creaseValuesV, ch=True)

        if len(emptySetsToDelete) > 0:
            maya.cmds.delete(emptySetsToDelete)
            

def unbakeValuesIntoCreaseSets(meshes, name='creaseSet#'):
    '''Un-bake edges/verts with similar crease values into new CreaseSets

    :Parameters:
        meshes ([string])
            The mesh shape nodes (of type mesh) to act upon
        name (string)
            The name template to use for the new creaseSets.
            The "#" if used at the end of the string will be replaced with
            a number to make the name unique.
            
    :Return: None
    '''
    with MayaUndoChunk('creaseSetFromMesh'): # group the following actions in this block into a single undo chunk
        # Group components together that have similar crease values
        # Note: alternatively to using a defaultdict, one could use regular dict with setdefault(), but it is slower
        valueCompDictE = collections.defaultdict(list)
        valueCompDictV = collections.defaultdict(list)
        for mesh in meshes:
            # get the mesh transform
            if maya.cmds.objectType(mesh, isAType='transform'):
                meshT = mesh
            else:
                # See if it is a mesh shape
                if maya.cmds.objectType(mesh, isAType='mesh'):
                    meshT = maya.cmds.listRelatives(mesh, parent=True, path=True)[0]
                else:
                    maya.cmds.warning(_loadUIString('kNonMeshOrTransform')%mesh)
                    continue

            # Get crease values and group them by value
            creaseValuesE = maya.cmds.polyCrease('%s.e[:]'%meshT, query=True, value=True)
            for i in range(len(creaseValuesE)):
                if creaseValuesE[i] > 0.0:  # if has a crease value
                    valueCompDictE[creaseValuesE[i]].append('%s.e[%i]'%(meshT, i))  # append to list of similar valued items
                
            creaseValuesV = maya.cmds.polyCrease('%s.vtx[:]'%meshT, query=True, vertexValue=True)
            for i in range(len(creaseValuesV)):
                if creaseValuesV[i] > 0.0:  # if has a crease value
                    valueCompDictV[creaseValuesV[i]].append('%s.vtx[%i]'%(meshT, i))  # append to list of similar valued items
            
            # Clear existing Crease values
            maya.cmds.polyCrease(meshT, op=2)  # remove all crease values from the mesh
    
        # Create new CreaseSets and assign similar components
        newCreaseSets = []
        for val, elements in valueCompDictE.iteritems():
            newCreaseSets.append( newCreaseSet(name=name, elements=elements, creaseLevel=val) )
        for val, elements in valueCompDictV.iteritems():
            newCreaseSets.append( newCreaseSet(name=name, elements=elements, creaseLevel=val) )


def subdivideBaseMesh(meshes, level=1, adjustSmoothLevelDisplay=False):
    '''Subdivide selected meshes by the specified level and decrement the creasing values in order to add resolution into the base mesh.
    The creaseSets used by the mesh must be exclusive to the meshes subdivided as the subdivide and creaseLevel adjustment must be done
    in tandem.

    :Parameters:
        meshes ([string])
            The mesh shape (of type 'mesh') or transform nodes (parent transform of mesh shapes)  to act upon
        level (int)
            level of subdivision to add to the base mesh
        adjustSmoothLevelDisplay (bool)
            specify if the mesh 'preview division levels' smoothLevel should be decremented to preserve
            the topology of the displayed mesh.  Setting this to True will preserve the same displayed vertex positions for
            the before/after smoothed meshes.
            
    :Return: list of meshes modified ([string])
    '''
    # get list of creaseSets and meshes in those creaseSets
    creaseSets = list(getCreaseSetsContainingItems(meshes))
    if (len(creaseSets) == 0):
        maya.cmds.warning(_loadUIString('kPleaseSelectMeshesOrCreaseSets'))
        return []

    memberComps  = maya.cmds.sets(creaseSets, q=True)
    memberMeshTs = set([i.split('.')[0] for i in memberComps])

    # Convert list to list of mesh transforms if a mesh shape
    meshTs = set()
    for mesh in meshes:
        if maya.cmds.objectType(mesh, isAType='transform'):
            meshTs.add(mesh)
        else:
            # See if it is a mesh shape
            if maya.cmds.objectType(mesh, isAType='mesh'):
                meshTs.add( maya.cmds.listRelatives(mesh, parent=True, path=True)[0] )
            else:
                maya.cmds.warning(_loadUIString('kNonMeshOrTransform')%mesh)
                continue
    
    # make sure there are some meshes specified
    if (len(meshTs) == 0):
        maya.cmds.warning(_loadUIString('kPleaseSelectMeshesOrCreaseSets'))
        return []
    
    # if there are mesh components in the creaseSets that are not selected list of meshes, then fail
    memberMeshTsNotSelected = memberMeshTs-set(meshTs)
    if (len(memberMeshTsNotSelected) != 0):
        maya.cmds.warning(maya.stringTable['y_creaseSetEditor.kCreaseSetsHaveComponents' ]%memberMeshTsNotSelected)
        return []

    with MayaUndoChunk('subdivideCreaseSet'): # group the following actions in this block into a single undo chunk
        # smooth and respect creasing (boundaryRule=2)
        maya.cmds.polySmooth(list(memberMeshTs), boundaryRule=2, continuity=1.0, divisions=level, propagateEdgeHardness=True)
        
        # Decrement creaseLevel, with a floor of 0.0
        for creaseSet in creaseSets:
            oldCreaseLevel = maya.cmds.getAttr('%s.creaseLevel'%creaseSet)
            newCreaseLevel = max(0.0, oldCreaseLevel-level)
            maya.cmds.setAttr('%s.creaseLevel'%creaseSet, newCreaseLevel)
            logger.debug('Old/new %s.creaseLevel: %f %f'%(creaseSet, oldCreaseLevel, newCreaseLevel))
            
        # Decrement preview division level (min value = 2) [optional]
        memberMeshes = maya.cmds.listRelatives(list(memberMeshTs), shapes=True, path=True, type='mesh')
        if adjustSmoothLevelDisplay:
            minLevel=2
            for mesh in memberMeshes:
                oldSmoothLevel = maya.cmds.getAttr('%s.smoothLevel'%mesh)
                newSmoothLevel = max(minLevel, oldSmoothLevel-level)
                logger.debug('Old/new %s.smoothLevel: %f %f'%(mesh, oldSmoothLevel, newSmoothLevel))
                if newSmoothLevel != oldSmoothLevel:
                    maya.cmds.setAttr('%s.smoothLevel'%mesh, newSmoothLevel)
                    
    # Return list of member meshes that were modified
    return memberMeshes


# ====================
# CreaseValue ColorMap
# ====================

def lookupColorValue(v, minvalue=0.0, maxvalue=1.0, colors=None):
    '''Linearly convert the value within the min/max range to a color with the specified colormap
    
    :Parameters:
        v (float)
            The value to convert
        minvalue (float)
            The minimum clamp value for the color scale
        maxvalue (float)
            The maximum clamp vaule for the color scale
        colors ([(r,g,b),...])
            A list of rgb colors to represent the colors to map 
            
    :Return: rgb tuple representing a color (r,g,b)
    '''
    if colors==None:
        colors = [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0)]  # black to white by default
    if minvalue >= maxvalue:
        logger.warning(maya.stringTable['y_creaseSetEditor.kBadMinMaxValue' ])
        return colors[0]
    v = max(min(v, maxvalue), minvalue) # clamp to range
    valNormalized = (v-minvalue) / (maxvalue-minvalue)  # linearly map value between min max represented by 0-1 range
    valNormalized = min(1.0, max(0.0, valNormalized))  # clamp to range 0-1
    (x, c0) = math.modf(valNormalized*(len(colors)-1))
    c0 = int(c0)
    if (c0+1) >= len(colors):
        return colors[-1]
    elif (x < 0.00001):
        return colors[c0]
    else:
        color0 = colors[c0]
        color1 = colors[c0+1]
        y = 1-x
        c = ((color0[0]*y + color1[0]*x),
             (color0[1]*y + color1[1]*x),
             (color0[2]*y + color1[2]*x))        
        return c


def convertCreasesToVertValues(meshT):
    '''Convert edge and vertex crease values to a per-vertex dict of the max crease value
    connected to each vertex.

    :Parameters:
        meshT (string)
            The transform mesh node name to act upon
    
    Return: dict(vertexId, float)
    '''
    vertexColorDict = {}

    # Get a MFnMesh for the specified mesh name
    selList = om.MSelectionList()
    selList.add(meshT)
    meshDag = om.MDagPath()
    selList.getDagPath(0, meshDag)
    meshFn = om.MFnMesh(meshDag)

    # Process the edge creases
    edgeIds  = om.MUintArray()
    creaseData = om.MDoubleArray()
    try:
        meshFn.getCreaseEdges(edgeIds, creaseData)
    except RuntimeError:
        pass # no valid crease values

    if edgeIds.length() > 0:
        # Create a dict of the creases
        creaseValsE = dict(zip(edgeIds, creaseData))
    
        # Create an edge component list
        meshEdgeComp = om.MFnSingleIndexedComponent()
        meshEdgeCompObj = meshEdgeComp.create(om.MFn.kMeshEdgeComponent)
        meshEdgeCompItems = om.MIntArray(edgeIds.length())
        for i in range(edgeIds.length()):
            meshEdgeCompItems.set(edgeIds[i], i)
        meshEdgeComp.addElements(meshEdgeCompItems)
    
        # Iterate over edges and update vertex color values
        meshItE = om.MItMeshEdge(meshDag, meshEdgeCompObj)
        while not meshItE.isDone():
            if vertexColorDict.has_key(meshItE.index(0)):
                vertexColorDict[meshItE.index(0)] = max(creaseValsE[meshItE.index()], vertexColorDict[meshItE.index(0)])
            else:
                vertexColorDict[meshItE.index(0)] = creaseValsE[meshItE.index()]
            if vertexColorDict.has_key(meshItE.index(1)):
                vertexColorDict[meshItE.index(1)] = max(creaseValsE[meshItE.index()], vertexColorDict[meshItE.index(1)])
            else:
                vertexColorDict[meshItE.index(1)] = creaseValsE[meshItE.index()]
            meshItE.next()

    # Process the vert creases
    vertIds  = om.MUintArray()
    creaseData = om.MDoubleArray()
    try:
        meshFn.getCreaseVertices(vertIds, creaseData)
    except RuntimeError:
        pass # no valid crease values

    if vertIds.length() > 0:
        creaseValsV = dict(zip(vertIds, creaseData))
    
        # Create an vert component list
        meshVertComp = om.MFnSingleIndexedComponent()
        meshVertCompObj = meshVertComp.create(om.MFn.kMeshVertComponent )
        meshVertCompItems = om.MIntArray(vertIds.length())
        for i in range(vertIds.length()):
            meshVertCompItems.set(vertIds[i], i)
        meshVertComp.addElements(meshVertCompItems)
    
        # Iterate over verts and update vertex color values
        meshItV = om.MItMeshVertex(meshDag, meshVertCompObj)
        while not meshItV.isDone():
            if vertexColorDict.has_key(meshItV.index()):
                vertexColorDict[meshItV.index()] = max(creaseValsV[meshItV.index()], vertexColorDict[meshItV.index()])
            else:
                vertexColorDict[meshItV.index()] = creaseValsV[meshItV.index()]
            meshItV.next()

    # Return dict of vertex colors
    return vertexColorDict


def calcCreaseValueColorSet(meshTs=None, minvalue=0.0, maxvalue=4.0, colorSetName='creaseValues'):
    '''Create a per-vertex "creaseValue" colorSet map from mesh crease values.
    Combines the crease values (max edge and vertex crease value per vertex) for each vertex and represent
    them by a color.

    :Parameters:
        meshTs ([string])
            List of transform mesh node names to act upon
        minvalue (float)
            The minimum clamp value for the color scale
        maxvalue (float)
            The maximum clamp vaule for the color scale
        colorSetName (string)
            The name of the colorSet to use, and create if it does not exist
    
    Return: None
    '''
    # Determine the color key to represent the values
    colorkey = [(0.0, 0.0, 1.0), (1.0, 0.0, 0.0)] # blue -> red
    lookupColorValueCache = {}  # cache of color values
    
    if meshTs == None:
        meshTs = maya.cmds.ls(sl=True, dag=True, noIntermediate=True, type='mesh')
    
    for meshT in meshTs:
        # process the verts
        vertexColorDict = convertCreasesToVertValues(meshT)

        # Set the 'creaseValues' to be the current colorset.  Create if needed.        
        allColorSets = maya.cmds.polyColorSet(meshT, q=True, allColorSets=True)
        if (allColorSets != None) and (colorSetName in allColorSets):
            maya.cmds.polyColorSet(meshT, currentColorSet=True, colorSet=colorSetName)
        else:
            maya.cmds.polyColorSet(meshT, create=True, colorSet=colorSetName, representation='RGB')
    
        # Get a MFnMesh for the specified mesh name
        selList = om.MSelectionList()
        selList.add(meshT)
        meshDag = om.MDagPath()
        selList.getDagPath(0, meshDag)
        meshFn = om.MFnMesh(meshDag)
        
        # Set the default color
        maya.cmds.polyColorPerVertex(meshT, colorRGB=colorkey[0], cdo=True) # display vertex colors and set the default color to the lowest value
        
        # Construct the arrays and populate with setVertexColors (faster than individual polyColorPerVertex commands)
        colorArray  = om.MColorArray(len(vertexColorDict))
        vertexArray = om.MIntArray(len(vertexColorDict))
        for (i,(k,v)) in enumerate(vertexColorDict.iteritems()):
            # retrieve color value from lookup cache or calculate from lookupColorValue() function
            c = lookupColorValueCache.setdefault(v, lookupColorValue(v, minvalue=minvalue, maxvalue=maxvalue, colors=colorkey))
            colorArray.set(i, c[0], c[1], c[2])
            vertexArray.set(k, i)
        meshFn.setVertexColors(colorArray, vertexArray)


# ====================
# Internal Utilities
# ====================

# See Feature Request MAYA-13005 for incorporating this utility into MQtUtil
def _findPixmapResource(filename):
    '''Resolve filenames using the XBMLANGPATH icon searchpath or look
    through the embedded Qt resources (if the path starts with a ':').

    :Parameters:
        filename (string)
            filename path or resource path (uses embedded Qt resources if starts with a ':'
    
    :Return: (QPixmap)
        QPixmap created from image found for absolute path string.
        Use .isNull() to check if the returned QPixmap is valid.
    '''
    pixmap = QPixmap()
    # Load directly if it is a QRC resource (starts with :)
    if filename.startswith(':'):  # it is a QRC resource (starts with ':', load it directly
        pixmap = QPixmap(filename)
    else: # Search icon search path to find image file
        searchpaths = os.environ['XBMLANGPATH'].split(os.pathsep)
        for p in searchpaths:
            p = p.replace('%B','')  # Remove the trailing %B found in Linux paths
            fullpath = os.path.join(p, filename)
            if os.path.isfile(fullpath):
                pixmap = QPixmap(fullpath)
    return pixmap


# ====================
# Internal Classes
# ====================

class HashableMObjectHandle(om.MObjectHandle):
    '''Hashable MObjectHandle referring to an MObject that can be used as a key in a dict.

    :See: MObjectHandle documentation for more information.
    '''
    def __hash__(self):
        '''Use the proper unique hash value unique to the MObject that the MObjectHandle points to so this class can be used as a key in a dict.
    
        :Return:
            MObjectHandle.hasCode() unique memory address for the MObject that is hashable
        
        :See: MObjectHandle.hashCode() documentation for more information.
        '''
        return self.hashCode()


class MCallbackIdWrapper(object):
    '''Wrapper class to handle cleaning up of MCallbackIds from registered MMessage
    '''
    def __init__(self, callbackId):
        super(MCallbackIdWrapper, self).__init__()
        self.callbackId = callbackId
        logger.debug("Adding callback %s"%self.callbackId)

    def __del__(self):
        om.MMessage.removeCallback(self.callbackId)
        logger.debug("Removing callback %s"%self.callbackId)

    def __repr__(self):
        return 'MCallbackIdWrapper(%r)'%self.callbackId


# ====================
# CreaseSetTreeWidget
# ====================

class CreaseSetTreeWidget(QTreeWidget):
    '''Derives off of standard QTreeWidget. The QTreeWidget embeds the data for
    the tree inside the class. If wanting a "view" widget that accesses data
    external to the widget, then use QTreeView.
    '''
    # ==============
    # CLASS ITEMS
    # ==============
    # Enumerate column semantics for easier readability
    COLUMN_SETCOLOR   = 0
    COLUMN_SETNAME    = 1
    COLUMN_CREASEVALUE= 2
    COLUMN_NUMMEMBERS = 3
    COLUMN_SELMEMBERS = 4
    COLUMN_COUNT      = 5
   
    # ==============
    # OVERRIDDEN FUNCTIONS
    # ==============
    def __init__(self, parent=None, name=None):
        '''Init for the CreaseSetTreeWidget
        
        :Parameters:
            parent (QWidget)
                parent Qt widget for this object.  Passed into the QtTreeWidget init function
            name (string)
                the objectName and windowTitle for this widget instance
        '''
        super(CreaseSetTreeWidget, self).__init__(parent=parent)
        #self.show()
        if name != None:
            self.setObjectName(name)
            self.setWindowTitle(name)
        self.resize(250,300) 

        # Disable edge color if not supported
        if not _edgeSetColorSupported:
            self.COLUMN_SETCOLOR    = -1 # not used
            self.COLUMN_SETNAME     -= 1
            self.COLUMN_CREASEVALUE -= 1
            self.COLUMN_NUMMEMBERS  -= 1
            self.COLUMN_SELMEMBERS  -= 1
            self.COLUMN_COUNT       -= 1
    
        # -- Members Variables 
        self._newSetColorIndex = 0
        self._highlightedNames = set()
        self._disableUpdateUIStack = [] # if len() > 0, then disable updating the UI
        self._requested_objectSetMembersChanged = set()
        self._requested_updateHighlightedItems = False

        # -- Preferences
        self.creaseLevelInc = 0.1
        self.defaultCreaseSetName = 'creaseSet#'
        
        # Update Preferences with OptionVar values
        if maya.cmds.optionVar( exists='creaseSetEditor_creaseLevelInc'):
            self.creaseLevelInc = maya.cmds.optionVar( q='creaseSetEditor_creaseLevelInc')
        if maya.cmds.optionVar( exists='creaseSetEditor_defaultCreaseSetName'):
            self.defaultCreaseSetName = maya.cmds.optionVar( q='creaseSetEditor_defaultCreaseSetName')

        # Track MCallbacks added by this class so they can be cleaned up when the widget closes
        self._registeredMayaCallbacks = []        # used to register/deregister Maya callbacks
        self._registeredMayaCallbacksPerNode = {}  # key=<MObjectHandle<node>> value=[callbacks] -- used to register/deregister Maya callbacks per creaseSet node
        
        # For middle-mouse drag value
        self._middleMouseDragPos0 = None
        self._middleMouseDragOrigValue = {}
        
        # Create Color Brushes (to be used below)
        #   Use Maya's outlinerChildHighlightColor as this widget's item highlight color for continuity with Maya
        mayaHighlightColor = [i*255.0 for i in maya.cmds.displayRGBColor('outlinerChildHilightColor', q=True)]
        self.memberForegroundBrush    = QBrush(QColor(150,180,255))
        self.highlightBackgroundBrush = QBrush(QColor(*mayaHighlightColor)) # QBrush(QColor(200,200,255,50))
        self.normalBackgroundBrush    = QBrush(QColor(0,0,0,0))
    
        # -- Set the headers
        tmpHeaders = ['']*self.COLUMN_COUNT
        tmpHeaders[self.COLUMN_SETNAME]     = maya.stringTable['y_creaseSetEditor.kSet' ]
        tmpHeaders[self.COLUMN_CREASEVALUE] = maya.stringTable['y_creaseSetEditor.kCrease' ]
        tmpHeaders[self.COLUMN_NUMMEMBERS]  = maya.stringTable['y_creaseSetEditor.kMembers' ]
        tmpHeaders[self.COLUMN_SELMEMBERS]  = maya.stringTable['y_creaseSetEditor.kSelected' ]
        self.setColumnCount(len(tmpHeaders))
        self.setHeaderLabels(tmpHeaders)
        
        self.setColumnWidth(self.COLUMN_SETNAME, 120)
        if _edgeSetColorSupported:
            self.setColumnWidth(self.COLUMN_SETCOLOR, 20)
        self.setColumnWidth(self.COLUMN_CREASEVALUE, 60)
        self.setColumnWidth(self.COLUMN_NUMMEMBERS , 60)
        self.setColumnWidth(self.COLUMN_SELMEMBERS , 60)
        self.setColumnWidth(0, self.columnWidth(0)+20) # Add some extra onto column 0 since it has the tree expander ctrl
 
        # -- Set other parameters   
        self.setSortingEnabled(True) # Allow for column sorting
        self.sortByColumn(self.COLUMN_SETNAME, Qt.AscendingOrder)
        self.setEditTriggers(QTreeWidget.NoEditTriggers) # explicitly set in itemDoubleClickedCB
        self.setExpandsOnDoubleClick(False) # Don't want this behavior
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        # -- Set CreaseSet color icons
        #    Generate a set of color swatches representing the allowable
        #    memberWireframeColor attr values (color index mode).
        wireframeColorIndexes = {}
        wireframeColorIndexes[0]  = [1,1,1,0]
        wireframeColorIndexes[-1] = [1,1,1,0]
        for i in range(1,32):
            wireframeColorIndexes[i] = maya.cmds.colorIndex(i, q=True)+[1.0]  #[r,g,b,a]

        self.rgbColorIcons = {}            
        for k,v in wireframeColorIndexes.items():
            logger.debug("Generate ColorIndex QIcon %i: %s"%(k, v))
            # Create color swatch QIcon
            genPixmap = QPixmap(20,20)
            genPixmap.fill(QColor(v[0]*255, v[1]*255, v[2]*255, v[3]*255))
            self.rgbColorIcons[k] = QIcon(genPixmap)


    def showEvent(self, *args):
        '''Show the widget, add the callbacks, and repopulate the data.
        '''
        logger.debug("In showEvent")

        # Signal/Slots
        #self.itemChanged.connect(self.itemChangedCB)  # Superceded by use of commitData() as better way.  See below.
        self.itemDoubleClicked.connect(self.itemDoubleClickedCB)
        
        # Maya Callbacks
        cb = om.MDGMessage.addNodeAddedCallback(self.objectSetNodeAddedCB, 'creaseSet', None) 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))
        cb = om.MDGMessage.addNodeRemovedCallback(self.objectSetNodeRemovedCB, 'creaseSet', None) 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))
        cb = om.MModelMessage.addCallback(om.MModelMessage.kActiveListModified, self.mayaSelectionChangedCB, None) 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))

        cb = om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeNew, self.beforeSceneUpdatedCB, 'kBeforeNew') 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))
        cb = om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeImport, self.beforeSceneUpdatedCB, 'kBeforeImport') 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))
        cb = om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeOpen, self.beforeSceneUpdatedCB, 'kBeforeOpen') 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))
        cb = om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeReference, self.beforeSceneUpdatedCB, 'kBeforeReference') 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))
        cb = om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeRemoveReference, self.beforeSceneUpdatedCB, 'kBeforeRemoveReference') 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))
        cb = om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeImportReference, self.beforeSceneUpdatedCB, 'kBeforeImportReference') 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))
        cb = om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeLoadReference, self.beforeSceneUpdatedCB, 'kBeforeLoadReference') 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))
        cb = om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeUnloadReference, self.beforeSceneUpdatedCB, 'kBeforeUnloadReference') 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))
        cb = om.MSceneMessage.addCallback(om.MSceneMessage.kMayaExiting, self.beforeSceneUpdatedCB, 'kMayaExiting') 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))

        cb = om.MSceneMessage.addCallback(om.MSceneMessage.kAfterNew, self.sceneUpdatedCB, 'kBeforeNew') 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))
        cb = om.MSceneMessage.addCallback(om.MSceneMessage.kAfterImport, self.sceneUpdatedCB, 'kBeforeImport') 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))
        cb = om.MSceneMessage.addCallback(om.MSceneMessage.kAfterOpen, self.sceneUpdatedCB, 'kBeforeOpen') 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))
        cb = om.MSceneMessage.addCallback(om.MSceneMessage.kAfterReference, self.sceneUpdatedCB, 'kBeforeReference') 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))
        cb = om.MSceneMessage.addCallback(om.MSceneMessage.kAfterRemoveReference, self.sceneUpdatedCB, 'kBeforeRemoveReference') 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))
        cb = om.MSceneMessage.addCallback(om.MSceneMessage.kAfterImportReference, self.sceneUpdatedCB, 'kBeforeImportReference') 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))
        cb = om.MSceneMessage.addCallback(om.MSceneMessage.kAfterLoadReference, self.sceneUpdatedCB, 'kBeforeLoadReference') 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))
        cb = om.MSceneMessage.addCallback(om.MSceneMessage.kAfterUnloadReference, self.sceneUpdatedCB, 'kBeforeUnloadReference') 
        self._registeredMayaCallbacks.append(MCallbackIdWrapper(cb))
        
        # Populate tree
        self.repopulate()

        return super(CreaseSetTreeWidget, self).showEvent(*args)
                

    def hideEvent(self, *args):
        '''When widget is hidden, remove the Maya callbacks and clean up.
        '''
        logger.debug("In hideEvent")
        self.cleanup()
        
        # NOTE: Not using super() as hideEvent could be called after it seems that self is deleted with __del__ and super does not work then
        return QTreeWidget.hideEvent(self, *args)


    def cleanup(self):
        '''Cleanup environment by removing the Maya callbacks, etc.
        '''
        logger.debug('CreaseSetEditor::cleanup()')
        # MCallbackWrapper items automatically clean themselves up on deletion
        self._registeredMayaCallbacks = []
        self._registeredMayaCallbacksPerNode= {}


    def removePerNodeMayaCallbacks(self, nodeObjs):
        '''Remove per-node Maya callbacks.

        :Parameters:
            nodeObjs ([MObject])
                List of MObject dependency nodes on which to remove the Maya per-node callbacks
        '''
        logger.debug('CreaseSetEditor::removePerNodeMayaCallbacks(%s)'%nodeObjs)
        # Remove existing per-set callbacks
        nodeObjHandles = [HashableMObjectHandle(nodeObj) for nodeObj in nodeObjs] # Determine MObjectHandles for the nodeObjs as that is used for the keys
        for nodeObjHandle in nodeObjHandles:
            if nodeObjHandle in self._registeredMayaCallbacksPerNode:
                callbacks = self._registeredMayaCallbacksPerNode[nodeObjHandle]
                logger.debug('Removing %i per-node callbacks for \"%s\"'%(len(callbacks), om.MFnDependencyNode(nodeObjHandle.object()).name()))
                del self._registeredMayaCallbacksPerNode[nodeObjHandle]
            else:
                logger.debug('No registered per-node callbacks to remove for %s.'%nodeObjHandle)
                
                
    def sizeHint(self):
        '''The window sizeHint used by Qt
        '''
        columnWidths = sum([self.columnWidth(i) for i in range(self.columnCount())])
        return QSize(columnWidths, 200)


    def minimumSizeHint(self):
        '''The minimum size for the Qt window
        '''
        return QSize(150, 100)

    # ===================
    # MOUSE MOVEMENT
    #   The feature to allow one to middle-mouse drag the attribute value
    #   if on the attribute value column is implemented, just like it is done
    #   with the Maya ChannelBox.
    #   See mousePressEvent(), mouseReleaseEvent(), and mouseMoveEvent()
    # ===================
    def mousePressEvent(self, event):
        '''Store off initial value of mouse for the middle-mouse button move event.
        '''
        logger.debug("In mousePressEvent")
        if (event.button()&Qt.MiddleButton):
            logger.debug("  middlebtn")
            maya.cmds.undoInfo(openChunk=True,chunkName='setCreaseValue')  # NOTE: MUST call the closeChunk (in mouseReleaseEvent) or it can destabilize the undo queue
            selectedSets =  self.getCurrentSetNames()
            if len(selectedSets) > 0:
                self._middleMouseDragPos0 = (event.x(), event.y())
                self._middleMouseDragAttrDelta0 = 0
        return super(CreaseSetTreeWidget, self).mousePressEvent(event)
    

    def mouseReleaseEvent(self, event):
        '''Store off initial value of mouse for the mouse move event
        '''
        logger.debug("In mouseReleaseEvent")
        if (event.button()&Qt.MiddleButton):
            logger.debug("  middlebtn")
            maya.cmds.undoInfo(closeChunk=True)  # NOTE: MUST follow the openChunk (in mousePressEvent) or it can destabilize the undo queue
            self._middleMouseDragPos0 = None
            self._middleMouseDragOrigValue = {}
            self._middleMouseDragAttrDelta0 = 0

        return super(CreaseSetTreeWidget, self).mouseReleaseEvent(event)


    def mouseMoveEvent(self, event):
        '''Interactively adjust creaseLevel attr values when middle mouse button
        pressed and mouse moved.
        '''
        logger.debug("In mouseMoveEvent")
        if self._middleMouseDragPos0 != None:
            logger.debug("  middlebtn")
            attrValuePerPixel = 0.01
            attrStep          = self.creaseLevelInc
            attrSoftMax       = 6  # max cap interative value
            
            selectedSets =  self.getCurrentSetNames()
            logger.debug("  moving middle button (%f, %f)"%(event.x(), event.y()))
            # NOTE: Maya just uses the X axis for float attrs, so do the same
            posDelta = event.x()-self._middleMouseDragPos0[0]  # + (event.y()-self._middleMouseDragPos0[1]) # sum of orthogonal deltas
            attrDelta = int((posDelta*attrValuePerPixel)/attrStep)*attrStep
            logger.debug("  attr delta = %f"%attrDelta)

            if abs(attrDelta-self._middleMouseDragAttrDelta0) > 0:
                # Change creaseLevel for selected items
                for setName in selectedSets:
                    origVal = self._middleMouseDragOrigValue.setdefault(setName, maya.cmds.getAttr('%s.creaseLevel'%setName)) # get original value at time of middle-mouse down
                    newVal = origVal + attrDelta
                    if newVal < 0:
                        newVal = 0
                    if newVal > attrSoftMax:
                        newVal = attrSoftMax
                    logger.debug("setAttr '%s.creaseLevel %f'"%(setName, newVal))
                    maya.cmds.setAttr('%s.creaseLevel'%setName, newVal)

            # Update interactive cached values
            self._middleMouseDragPos = (event.x(), event.y())
            self._middleMouseDragAttrDelta0 = attrDelta

        return super(CreaseSetTreeWidget, self).mouseMoveEvent(event)


    # ==============
    # FUNCTIONS
    # ==============
    def setItemValues(self, item=None, name=None, colorIndex=None, creaseLevel=None, members=None, numSelectedMembers=None, showSetMembers=False):
        '''This helper function sets the column values for an item.
        It will set all values that are specified so can do partial or full setting of the item values.

        :Parameters:
            item (QTreeWidgetItem)
                QTreeWidgetItem to act upon.  If 'None', then create a new QTreeWidgetItem.
            name (string)
                new text for the 'Name Column'
            colorIndex (int)
                new colorIndex for the 'Color Column' swatch (range=0-7)
            creaseLevel (float)
                new creaseLevel for the 'CreaseLevel Column'
            members ([string])
                new list of members to add as sub-items to this tree item
            numSelectedMembers (int)
                number of members that are currently selected
            showSetMembers (bool)
                Add tree items under the CreaseSet item for each member in the CreasSet
                Disabled by default for performance reasons.
                (default=False) 
        
        :Return: QTreeWidgetItem created or acted upon (QTreeWidgetItem)
        '''
        if isinstance(item, types.NoneType):  # NOTE: Using isinstance() instead of item==None since PySide does not allow for that __eq__ operator
            item = CreaseSetTreeWidgetItem(self)      # Create a new item for the QTreeWidget if item==None
            item.setFlags(item.flags() | Qt.ItemIsEditable  )
            item.setText(self.COLUMN_SELMEMBERS, str(0)) # init number of selected members to 0
        logger.debug('In setItemValues(item=%s, name=%s, colorIndex=%s, creaseLevel=%s, members=%s, numSelectedMembers=%s, showSetMembers=%s'%(item, name, colorIndex, creaseLevel, members, numSelectedMembers, showSetMembers))
        if name != None:    
            item.setText(self.COLUMN_SETNAME, name)
        if _edgeSetColorSupported and colorIndex != None:
            if colorIndex == -1:
                item.setIcon(self.COLUMN_SETCOLOR, self.rgbColorIcons[-1])
            else:
                item.setIcon(self.COLUMN_SETCOLOR, self.rgbColorIcons.get(colorIndex+24, self.rgbColorIcons[0]))
        if creaseLevel != None:
            item.setText(self.COLUMN_CREASEVALUE, '%.2f'%creaseLevel)
        if members != None:
            item.takeChildren()  # remove all child items
            if len(members) > 0:
                numMembers = len(maya.cmds.ls(*members, flatten=True))
            else:
                numMembers = 0
            item.setText(self.COLUMN_NUMMEMBERS, str(numMembers))
            # Add child items for each member (Note: Can have a performance impact seen with 50K+ components)
            if showSetMembers:
                for setMember in members:
                        item_setMember = CreaseSetTreeWidgetItem(item)
                        item_setMember.setText(self.COLUMN_SETNAME, setMember)
                        item_setMember.setForeground(self.COLUMN_SETNAME, self.memberForegroundBrush)
                        item_setMember.setFlags(Qt.NoItemFlags  )  # not selectable or editable
        if numSelectedMembers != None:
            item.setText(self.COLUMN_SELMEMBERS, str(numSelectedMembers))
        return item    
    
    
    def addPerNodeMayaCallbacks(self, nodeObj):
        '''Add the Maya per-node callbacks for the specified item
        and register them with the widget (so they can be cleaned up).

        :Parameters:
            nodeObj (MObject)
                MObject depend node to add per-node callbacks to
        
        :Return: None
        '''
        # Get an MObjectHandle for the MObject
        nodeObjHandle = HashableMObjectHandle(nodeObj)
        
        # Trivial rejection
        if self._registeredMayaCallbacksPerNode.has_key(nodeObjHandle):
            logger.debug('Maya per-node callback already has a key in the dict. Expected it to be empty. Overwriting.')
            
        # Get a reference to the list for that node in the dict
        perNodeCallbacks = self._registeredMayaCallbacksPerNode.setdefault(nodeObjHandle, [])  # init it to a list if it is a new reference
        
        # = Membership changed
        cb = om.MObjectSetMessage.addSetMembersModifiedCallback(nodeObj, self.objectSetMembersChangedCB, None)
        perNodeCallbacks.append( MCallbackIdWrapper(cb) )

        # = Attr Changed (Connect Controls)
        # Do a 'connectControl' style operation
        cb = om.MNodeMessage.addAttributeChangedCallback(nodeObj, self.objectSetAttrChangedCB, None)
        perNodeCallbacks.append( MCallbackIdWrapper(cb) )

        # = Name changed callback
        cb = om.MNodeMessage.addNameChangedCallback(nodeObj, self.objectSetNodeNameChangedCB, None)
        perNodeCallbacks.append( MCallbackIdWrapper(cb) )
        
        logger.debug('Adding %i per-node callbacks for \"%s\": %s'%(len(perNodeCallbacks), om.MFnDependencyNode(nodeObj).name(), perNodeCallbacks) )

    
    def repopulate(self):
        '''Clear and populate the table with data retrieved from the Maya scene.
        Add Maya callbacks for creaseSet changes to trigger UI updates.
        '''
        #logger.debug("In repopulate")
        curSelection = self.getCurrentSetNames()  # restored below

        # Remove existing per-set callbacks
        self._registeredMayaCallbacksPerNode= {}  # MCallbackWrapper objects auto-remove themselves.  See also self.removePerNodeMayaCallbacks()

        # Clear items in QTreeWidget
        self.clear()

        # Get the list of CreaseSets
        creaseSets = maya.cmds.ls(type='creaseSet')

        # Generate the QTreeWidgetItem for each set
        for s in creaseSets:
            # Get values from the objectSet
            colorIndex = maya.cmds.getAttr('%s.memberWireframeColor'%s)
            creaseLevel = maya.cmds.getAttr('%s.creaseLevel'%s)
            setMembers = maya.cmds.sets(s, q=True)
            if setMembers == None:
                setMembers = []
    
            # Set the item parameters
            item = self.setItemValues(item=None, name=s, colorIndex=colorIndex, creaseLevel=creaseLevel, members=setMembers)

            # == Callbacks
            sObj = getDependNode(s)  # Get an MObject for the set node (sObj) to be used in the callbacks below
            self.addPerNodeMayaCallbacks(sObj)
            
        # Update selection
        self.setCurrentItemsFromSetNames(curSelection)
        
        # Update highlights
        self.requestUpdateHighlightedItems()
        

    # ==============
    # UI FUNCTIONS
    # ==============   
    def getCurrentSetNames(self):
        '''Get the Maya nodenames for the widget's selected items
        '''
        curItems = self.selectedItems()  # of type QTreeWidgetItem
        curItemNames = [str(i.text(self.COLUMN_SETNAME)) for i in curItems]
        logger.debug("CurrentSetNames %s"%curItemNames)
        return curItemNames
        

    def getSelectedMeshes(self):
        '''Get selected meshes. If there are no selected meshes then
        get the meshes associated with selected crease sets.
        '''
        meshes = maya.cmds.ls(sl=True, dag=True, noIntermediate=True, type='mesh')
        if len(meshes) > 0:
            return meshes
        creaseSets = self.getCurrentSetNames()
        if len(creaseSets) > 0:
            meshes = maya.cmds.ls(maya.cmds.sets(creaseSets, q=True), dag=True, objectsOnly=True)
        return meshes


    def setCurrentItemsFromSetNames(self, setNames):
        '''Adjust the selection highlighting of the QtTreeWidgetItems based on the creaseSet
        node names passed in.
        
        :Parameters:
            setNames ([string])
                node names of the creaseSet nodes to highlight in the tree
        
        :Note: This "selection" is not the same as Maya's currentSelected items, but
        instead the selected items for the widget.
        '''
        self.clearSelection()
        for setName in setNames:
            curSelectItems = self.findItems(setName, Qt.MatchFixedString|Qt.MatchCaseSensitive, self.COLUMN_SETNAME)
            if len(curSelectItems) > 0:
                curSelectItems[0].setSelected(True)
                if (len(curSelectItems) > 1):
                    logger.debug('Expected only single match of setName %s'%setName)
    

    # ==============
    # SLOT FUNCTION CALLBACKS
    # ==============   
    def itemDoubleClickedCB (self, item, column):
        """Double-click behavior on a per-column basis.
        Used to edit values if double-clicked on the item's name or crease value.

        :Parameters:
            item (QtTreeWidgetItem)
                the QtTreeWidgetItem acted upon
            column (int)
                the column index where the double-click action occurred
        """
        logger.debug("In itemDoubleClicked %s %i"%(item, column))
        if column in (self.COLUMN_SETNAME, self.COLUMN_CREASEVALUE):
            logger.debug("Double-clicked column %i"%column)
            self.editItem(item, column)


    def commitData(self, *args):
        '''Override the virtual function commitData() to retrieve the old and
        new values, revert the item value to its original value, then pass them
        along to commitDataCB().
        
        The commitDataCB() will update the Maya scene,
        that will then in turn update the widget. Therefore updating the item
        data directly is not desired, but retrieving the values are necessary. 

        :Dataflow:
            Maya Scene -> QCreaseSetTree (data)
            QCreaseSetTree (uncomitted edited values) -> Maya Scene

        :Note:
            Using commitData() is better than connecting a function to
            itemChanged signal as it will be triggered whenever an
            item value changes, not just when an editor changes the value
            by the user.  We can also get the old and new values
        '''
        logger.debug("In commitData column %i", self.currentColumn())
        item = self.currentItem()
        col = self.currentColumn()
        oldValue = str(item.text(col))
        super(CreaseSetTreeWidget, self).commitData(*args)
        newValue = str(item.text(col))
        item.setText(col, oldValue)  # reset value back to old value so Maya scene is updated, that will then update the UI
        self.commitDataCB(item, col, oldValue, newValue)

     
    def commitDataCB (self, item, column, oldValue, newValue):
        '''Update Maya scene with the new values.  It is called by the commitData()
        function above when column data is edited from the UI.

        :Parameters:
            item (QtTreeWidgetItem)
                the QtTreeWidgetItem acted upon
            column (int)
                the column index where the double-click action occurred
            oldValue
                original value of the attribute or name.
            newValue
                new value of the attribute or name
        '''
        logger.debug("In commitDataCB column=%i oldValue=%s newValue=%s"%(column, oldValue, newValue))
        
        if column == self.COLUMN_SETNAME:
            logger.debug("New Name %s"%repr(newValue))
            newName = maya.cmds.rename(oldValue, newValue)
        elif column == self.COLUMN_CREASEVALUE:
            try:
                newValue = float(newValue)
            except ValueError, e:
                logger.warning(maya.stringTable['y_creaseSetEditor.kUnableToConvertFloat' ]%newValue)
                # Note: The widget value has already been reverted to the oldValue in commitData() above
                # so no modification of the value is necessary here.  The changing of the widget value
                # to the new value is handled by Maya callbacks when the attr value changes.  This was done so
                # that Maya's scenegraph would drive the widget values whenever they are modified (whether it is
                # done manually or by the CreaseSetEditor UI)
                return
            logger.debug("New creaseLevel %f"%newValue)
            # Update Maya and Tree (for single or multiple creaseSets)
            curItems = self.selectedItems()  # of type QTreeWidgetItem
            with MayaUndoChunk('setCreaseValue'):
                for curItem in curItems:
                    setName = str(curItem.text(self.COLUMN_SETNAME))
                    maya.cmds.setAttr('%s.creaseLevel'%setName, newValue)


    # ==============
    # MENU ITEM CALLBACKS
    #   All the actions for the popup menu callbacks.
    #   Note that these Popup Menu action callbacks just modify the Maya scene
    #   and not the Qt widget.  Other functions are hooked up to MCallbacks to
    #   update the Qt widget when the maya scene changes.  These action callbacks
    #   explicitly just modify the Maya scene.
    # ==============
    def contextMenuEvent(self, event):
        '''Dynamically driven contextMenu for popup menu. Easily edited dict of labels and actions.
        '''
        # Add context menu
        # Reference: See http://diotavelli.net/PyQtWiki/Handling%20context%20menus
        
        # In-place recursive function to create menus
        def createMenu(menu, curActions):
            '''Nested function that is used to generate the menus from the actions dict above
            '''
            for (cbTxt,cb,enable) in curActions:
                if isinstance(cbTxt, str) and cbTxt.startswith('---'):
                    menu.addSeparator()
                elif callable(cb):
                    if isinstance(cbTxt, QIcon):          # Handle pure icon option
                        action = QAction('', self)        # Add blank menu item
                        action.setIcon(cbTxt)             # Set icon
                        action.setIconVisibleInMenu(True)
                    else:                                   
                        action = QAction(cbTxt, self)     # Add menu item with text
                    action.setEnabled(enable)
                    action.triggered.connect(cb)
                    menu.addAction(action)
                elif isinstance(cb, list):                # Handle Submenus (indicated by a list)
                    submenuItems = cb
                    if len(submenuItems) > 0:
                        submenu = menu.addMenu(cbTxt)     # Add submenu
                        createMenu(submenu, submenuItems) # Add recursive submenu items
                else:
                    logger.debug('Unsupported menu type for \"%s\"'%cbTxt)
                            

        # ContextMenu Actions
        creasesets = self.getCurrentSetNames()
        meshes = getSelectedMeshComponents(meshShapes=True) 
        components = getSelectedMeshComponents(verts=True,edges=True)
        componentsSelected = len(components) > 0

        if len(creasesets) == 0:
            self.contextMenuActions = [
                (maya.stringTable['y_creaseSetEditor.kContextCreateSet' ], self.newCreaseSetCB, True)
                ]
        elif len(creasesets) == 1:
            self.contextMenuActions = [
                (maya.stringTable['y_creaseSetEditor.kContextAdd' ], self.addMembersCB, componentsSelected),
                (maya.stringTable['y_creaseSetEditor.kContextRemove' ], self.removeMembersCB, componentsSelected),
                ('---', None, True),
                (maya.stringTable['y_creaseSetEditor.kContextRemoveOne' ], self.deleteCreaseSetCB, True),
                (maya.stringTable['y_creaseSetEditor.kContextSplitOne' ], self.splitCreaseSetCB, componentsSelected),
                ('---', None, True),
                (maya.stringTable['y_creaseSetEditor.kContextMemberSel' ], self.selectMembersCB, True),
                (maya.stringTable['y_creaseSetEditor.kContextNodeSelOne' ], self.selectSelectedSetNodesCB, True),
                ]
        else: # len(creasesets) > 1
            self.contextMenuActions = [
                (maya.stringTable['y_creaseSetEditor.kContextRemove2' ], self.removeMembersCB, componentsSelected),
                ('---', None, True),
                (maya.stringTable['y_creaseSetEditor.kContextRemoveMultiple' ], self.deleteCreaseSetCB, True),
                (maya.stringTable['y_creaseSetEditor.kContextSplitMultiple' ], self.splitCreaseSetCB, componentsSelected),
                (maya.stringTable['y_creaseSetEditor.kContextMerge' ], self.mergeCreaseSetsCB, True),
                ('---', None, True),
                (maya.stringTable['y_creaseSetEditor.kContextMemberSel2' ], self.selectMembersCB, True),
                (maya.stringTable['y_creaseSetEditor.kContextNodeSelMultiple' ], self.selectSelectedSetNodesCB, True),
                ]

        if _edgeSetColorSupported and len(creasesets) > 0:
            colorMenuItems = [
                # Set Color Override submenu
                (maya.stringTable['y_creaseSetEditor.kCreaseSetColorMenu' ], [
                    # Note: The lambda is used to generate a function on the fly that takes no arguments
                    #       but calls the resulting self.setComponentColor() with the specified parameter.
                    #       It is the cleanest way to tie in with the Qt event callback system for this.
                    #       Otherwise, separate functions would have to be written as wrappers that can be called
                    #       by the Qt event system.
                    (maya.stringTable['y_creaseSetEditor.kContextNoColor' ], lambda:self.setComponentColor(-1), True)
                    (self.rgbColorIcons[24], lambda:self.setComponentColor(0), True),
                    (self.rgbColorIcons[25], lambda:self.setComponentColor(1), True),
                    (self.rgbColorIcons[26], lambda:self.setComponentColor(2), True),
                    (self.rgbColorIcons[27], lambda:self.setComponentColor(3), True),
                    (self.rgbColorIcons[28], lambda:self.setComponentColor(4), True),
                    (self.rgbColorIcons[29], lambda:self.setComponentColor(5), True),
                    (self.rgbColorIcons[30], lambda:self.setComponentColor(6), True),
                    (self.rgbColorIcons[31], lambda:self.setComponentColor(7), True),
                    ], True),
                ]
            self.contextMenuActions.extend(colorMenuItems)

        popupmenu = QMenu(self)
        createMenu(popupmenu, self.contextMenuActions)
        popupmenu.popup(event.globalPos())
    
    
    def selectMembersCB(self):
        '''Select the Maya creaseSet members for the highlighed tree item(s)
        If there are existing meshes or components selected, then select the intersection
        of the members in the creaseSet with the current selected items.
        '''
        logger.debug("selectMembersCB")
        highlightedSets = self.getCurrentSetNames()
        if len(highlightedSets) > 0:
            members = maya.cmds.ls( maya.cmds.sets(highlightedSets, q=True), flatten=True) # list of individual comps
            logger.debug('selectMembersCB: All members (%i): %s'%(len(members), members))
            
            # Filter resulting members by objects or comps already selected (if items selected)
            allmembers = members
            if len(maya.cmds.ls(sl=True)) > 0:
                members = filterComponentsBySelectedItems(members)
            
            if len(members) > 0:
                maya.cmds.select( *members, replace=True)
            elif len(allmembers) > 0:
                maya.cmds.select( *allmembers, replace=True)
            else:
                maya.cmds.select(clear=True)
        else:
            maya.cmds.warning(maya.stringTable['y_creaseSetEditor.kPleaseSelectOneOrMore' ])
        

    def addMembersCB(self):
        '''Add selected Maya edge and vertex components to the highlighed tree item
        '''
        logger.debug("addMembersCB")
        selObjs = getSelectedMeshComponents(verts=True, edges=True, expand=False)
        if len(selObjs) > 0:
            # NOTE: Expects a single CreaseSet
            curSets = self.getCurrentSetNames()
            if len(curSets) != 1:
                maya.cmds.warning(maya.stringTable['y_creaseSetEditor.kSelectASingleCreaseSet' ])
                return
            setName = curSets[0]
            with MayaUndoChunk('addToCreaseSet'): # WORKAROUND: group the following (internal) actions in this block into a single undo chunk
                shared = getCreaseSetsContainingItems(items=selObjs,asDict=False)
                shared.discard(setName) # discard target creaseSet so not to perform comparisons against it below
                if len(shared) > 0:
                    maya.cmds.warning(_loadUIString('kComponentsMovedWarning'))

                # add items to selected set
                maya.cmds.sets(*selObjs, forceElement=setName)

                # remove any shared items because forceElement doesn't always work
                for s in shared:
                    intersection = maya.cmds.sets(setName, intersection=s)
                    if len(intersection) > 0:
                        maya.cmds.sets(*intersection, remove=s)


    def removeMembersCB(self):
        '''Remove selected Maya edge and vertex components from the highlighed tree item
        '''
        logger.debug("removeMembersCB")
        selObjs = getSelectedMeshComponents(verts=True, edges=True, expand=False)
        if len(selObjs) > 0:
            curSets = self.getCurrentSetNames()
            with MayaUndoChunk('removeFromCreaseSet'): # Group the following actions in this block into a single undo chunk
                for setName in curSets:
                    maya.cmds.sets( *selObjs, remove=setName)


    def newCreaseSetCB(self):
        '''Create a new creaseSet and populate it with the selected Maya edge and vertex components.
        '''
        logger.debug("newCreaseSetCB")
        newSet = newCreaseSet(name=self.defaultCreaseSetName)
        self.setCurrentItemsFromSetNames([newSet])


    def deleteCreaseSetCB(self):
        '''Delete the creaseSet(s) corresponding to the highlighted tree item(s)
        '''
        logger.debug("deleteCreaseSetCB")
        curSets = self.getCurrentSetNames()
        if len(curSets) > 0:
            with MayaUndoChunk('deleteCreaseSet'): # WORKAROUND: group the following (internal) actions in this block into a single undo chunk
                maya.cmds.delete(curSets)


    def mergeCreaseSetsCB(self):
        '''Merge and combine two or more highlighted creaseSets into the last highlighted item.
        
        :Note: Order of highlighting the creaseSet items matters.  The last one selected is the target
        creaseSet.  This follows the same paradigm used in Maya parenting.
        '''
        logger.debug("mergeCreaseSetsCB")
        selSetNames = self.getCurrentSetNames()
        if len(selSetNames) < 2:
            maya.cmds.warning(maya.stringTable['y_creaseSetEditor.kSelectAtLeastTwo' ])
            return False

        # The last item selected is the target that the others are merged into
        mergeIntoTarget = selSetNames[-1]
        mergeFromSets   = selSetNames[:-1]
        
        # Move members into target creaseSet and delete the other creaseSets after the move
        with MayaUndoChunk('mergeCreaseSet'): # group the following actions in this block into a single undo chunk
            origCreaseLevel = maya.cmds.getAttr('%s.creaseLevel'%mergeIntoTarget)

            for s in mergeFromSets:
                selObjs = maya.cmds.sets(s, q=True)
                if len(selObjs) > 0:
                    maya.cmds.sets(*selObjs, remove=s)
                    maya.cmds.sets(*selObjs, forceElement=mergeIntoTarget)

            maya.cmds.delete(mergeFromSets)

            # reset crease level because delete of old crease set can reset it
            maya.cmds.setAttr('%s.creaseLevel'%mergeIntoTarget, origCreaseLevel)


    def splitCreaseSetCB(self):
        '''Split the edges/vertices in selected meshes or components in CreaseSets into separate CreaseSets.
        '''
        logger.debug("splitCreaseSetCB")
        newCreaseSets = []
        selMeshes = maya.cmds.ls(sl=True, dag=True, noIntermediate=True, type='mesh')
        selComps  = getSelectedMeshComponents(verts=True, edges=True, expand=False)
        
        # Trivial rejection if no relevant items selected
        if (len(selMeshes) == 0) and (len(selComps) == 0):
            maya.cmds.warning(maya.stringTable['y_creaseSetEditor.kSelectOneOrMoreMeshesToSplit' ])
            return []
        
        # Trivial rejection if no sets selected
        # REVISIT: Use all sets if none specified
        selSetNames = self.getCurrentSetNames()
        if len(selSetNames) == 0:
            maya.cmds.warning(maya.stringTable['y_creaseSetEditor.kSelectACreaseSetToSplit' ])
            return []
        
        with MayaUndoChunk('splitCreaseSet'): # group the following actions in this block into a single undo chunk
            for srcSetName in selSetNames:  # loop over each set and create a new set if members match selected items
                setItems = maya.cmds.sets(srcSetName, q=True)
                
                # Trivial rejection if creaseSet has no members
                if len(setItems) == 0:
                    maya.cmds.warning(maya.stringTable['y_creaseSetEditor.kCreaseSetHasNoMembers' ]%srcSetName)
                    continue
                
                newSetMembers = filterComponentsBySelectedItems(setItems)
                if len(newSetMembers) > 0:
                    # Create New Set and move members into it
                    origCreaseLevel = maya.cmds.getAttr('%s.creaseLevel'%srcSetName)
                    newCreaseSets.append( newCreaseSet(name='%s_#'%srcSetName, elements=newSetMembers, creaseLevel=origCreaseLevel) )

        if len(newCreaseSets) == 0:
            maya.cmds.warning(maya.stringTable['y_creaseSetEditor.kSelectedMeshedNotInCreaseSet' ]%srcSetName)
        
        return newCreaseSets


    def selectSelectedSetNodesCB(self):
        '''Select the CreaseSets in Maya that are highlighted in the CreaseSetEditor
        '''
        logger.debug("selectSelectedSetNodesCB")
        curSetNames = self.getCurrentSetNames()
        if len(curSetNames) > 0:
            maya.cmds.select(curSetNames, ne=True)


    def selectSetsWithSelectedMembersCB(self):
        '''Select the CreaseSet tree items in the CreaseSetEditor that have members
        that are currently selected in Maya.
        '''
        logger.debug("selectSetsWithSelectedMembersCB")
        setsToHighlight = getCreaseSetsContainingItems(asDict=False)
        self.setCurrentItemsFromSetNames(setsToHighlight)


    # ------------
    # Mesh Actions
    # ------------
    def hardenCreaseEdgesCB(self):
        '''Set the cage hard/soft edge value for the selected meshes based on whether
        the edges are creased.  Creasing is assumed if creaseLevel > 0.
        '''
        meshes = self.getSelectedMeshes()
        with MayaUndoChunk('setEdgeHardness'): # group the following actions in this block into a single undo chunk
            origSel = maya.cmds.ls(sl=True)
            for mesh in meshes:
                meshT = maya.cmds.listRelatives(mesh, parent=True, path=True)[0]
                creaseValues = maya.cmds.polyCrease('%s.e[:]'%meshT, query=True, value=True)
                creaseEdges = ['%s.e[%i]'%(meshT, i) for i,val in enumerate(creaseValues) if val > 0.0] # construct list of edges to be hardened
                logger.debug("Hard edges: %s"%creaseEdges)
                # Note: polySoftEdge only works on a single mesh at a time, so call it once per mesh
                maya.cmds.polySoftEdge(mesh, angle=180)       # Soften all edges
                if len(creaseEdges) > 0:
                    maya.cmds.polySoftEdge(creaseEdges, angle=0)  # Harden those specific edges
            if len(origSel) > 0:
                maya.cmds.select(origSel)
            else:
                maya.cmds.select(clear=True)


    def optimizeSubdLevelCB(self):
        '''Set the subd smoothLevel attr to be +1 above the truncated max crease value.
        This is useful to see the most efficient representation of the creasing effects
        on the mesh.
        '''
        minLevel=2
        maxLevel=6
        meshes = self.getSelectedMeshes()
        with MayaUndoChunk('optimalSubdivDisplay'): # group the following actions in this block into a single undo chunk
            for mesh in meshes:
                meshT = maya.cmds.listRelatives(mesh, parent=True, path=True)[0]
                maxCreaseValue = int(max(maya.cmds.polyCrease('%s.e[:]'%meshT, query=True, value=True)))
                subdLevel = min(max(minLevel,maxCreaseValue+1), maxLevel)
                logger.debug('setAttr "%s.smoothLevel" %f'%(mesh,subdLevel))
                maya.cmds.setAttr('%s.smoothLevel'%mesh, subdLevel)


    def unoptimizeSubdLevelCB(self):
        '''Restore the displayed subd smoothLevel attr to the default value of 2.
        '''
        meshes = self.getSelectedMeshes()
        with MayaUndoChunk('defaultSubdivDisplay'): # group the following actions in this block into a single undo chunk
            for mesh in meshes:
                maya.cmds.setAttr('%s.smoothLevel'%mesh, 2)


    def bakeOutCreaseSetValuesCB(self):
        '''Bake out the CreaseSet values from the selected meshes directly onto
        the meshes and remove the components from the CreaseSet.
        '''
        meshes = self.getSelectedMeshes()
        bakeOutCreaseSetValues(meshes)


    def unbakeValuesIntoCreaseSetsCB(self):
        '''Un-bake edges/verts with similar crease values into new CreaseSets
        '''
        meshes = self.getSelectedMeshes()
        unbakeValuesIntoCreaseSets(meshes, name=self.defaultCreaseSetName)


    def subdivideBaseMeshCB(self):
        '''Subdivide selected meshes by 1 level and decrement the creasing values to add resolution into the base mesh.
        '''
        meshes = self.getSelectedMeshes()
        subdivideBaseMesh(meshes, level=1, adjustSmoothLevelDisplay=True)


    # ------------
    # ColorSet Representation
    # ------------
    def calcCreaseValueColorSetCB(self):
        '''Calculate a color-per-vertex colorSet representation for crease values
        on the selected meshes.
        '''
        meshes = self.getSelectedMeshes()
        calcCreaseValueColorSet(meshes)


    def hideCreaseValueColorSetCB(self):
        meshes = self.getSelectedMeshes()
        maya.cmds.polyOptions(meshes, colorShadedDisplay=False)

        
    def showCreaseValueColorSetCB(self):
        meshes = self.getSelectedMeshes()
        maya.cmds.polyOptions(meshes, colorShadedDisplay=True)

  
    def toggleCreaseValueColorSetCB(self):
        meshes = self.getSelectedMeshes()
        maya.cmds.polyOptions(meshes, colorShadedDisplay=True, r=True)
        


    # ------------
    # Preferences
    # ------------
    def setCreaseLevelIncrementCB(self):
        okBut = _loadUIString('kOkButton')
        cancelBut = _loadUIString('kCancelButton')
        result = maya.cmds.promptDialog(
            title=maya.stringTable['y_creaseSetEditor.kCreaseSetIncrementTitle' ],
            message=maya.stringTable['y_creaseSetEditor.kEnterCreaseLevelIncrement' ],
            style='float',
            text=str(self.creaseLevelInc),
            button=[ okBut, cancelBut ],
            defaultButton=okBut,
            cancelButton=cancelBut,
            dismissString=cancelBut)
        if result == okBut:
            val = float(maya.cmds.promptDialog(query=True, text=True))
            self.creaseLevelInc = val
            logger.debug("CreaseLevel Increment: %f", val)
            # Store off as optionVar
            maya.cmds.optionVar( fv=('creaseSetEditor_creaseLevelInc', val) )


    def setDefaultCreaseSetNameCB(self):
        okBut = _loadUIString('kOkButton')
        cancelBut = _loadUIString('kCancelButton')
        setDefaultCreaseSetNameDone = False
        while not setDefaultCreaseSetNameDone:
            result = maya.cmds.promptDialog(
                title=maya.stringTable['y_creaseSetEditor.kCreaseSetNameTitle' ],
                message=maya.stringTable['y_creaseSetEditor.kEnterDefaultName' ],
                text=str(self.defaultCreaseSetName),
                button=[ okBut, cancelBut ],
                defaultButton=okBut,
                cancelButton=cancelBut,
                dismissString=cancelBut)
            if result == okBut:
                val = maya.cmds.promptDialog(query=True, text=True)
                if maya.mel.eval( u'containsMultibyte \"%s\"' % val ):
                    # The Maya "error" command will trigger a Python runtime error, so
                    # wrap the statement in a try/except block that will catch and pass
                    # it so that the Maya command can properly execute
                    try:
                        errorMsg = (maya.stringTable['y_creaseSetEditor.kMultibyteDefaultCreaseSetNameError' ] % val)
                        maya.mel.eval( 'error "%s"' % errorMsg )
                    except RuntimeError:
                        pass
                else:
                    if len(val) == 0:
                        val = 'creaseSet#'
                    self.defaultCreaseSetName = val
                    logger.debug("Default CreaseSet Name: %s", val)
                    # Store off as optionVar
                    maya.cmds.optionVar( sv=('creaseSetEditor_defaultCreaseSetName', val) )
                    setDefaultCreaseSetNameDone = True
            else:
                setDefaultCreaseSetNameDone = True


    # ------------
    # Component Color Actions
    # ------------

    def setComponentColor(self, colorIndex):
        '''Set the creaseSet component memberWireframeColor color colorIndex.
        
        :Parameters:
            colorIndex
                index value for the color (0-7).
                If set to -1, then color the override is disabled
        '''
        selSetNames = self.getCurrentSetNames()
        with MayaUndoChunk('creaseSetColor'): # group the following actions in this block into a single undo chunk
            for s in selSetNames:
                maya.cmds.setAttr('%s.memberWireframeColor'%s, colorIndex)


    # ==============
    # MAYA MMessage SCENE CALLBACKS
    #   These are the Maya callbacks that update the Qt widget from the Maya scene changes.
    #   Maya Scene changed -> Qt widget updated
    #   These are distinctly separate from and should not be confused with the
    #   Popup menu action callbacks above.
    # ==============
    
    def objectSetNodeAddedCB(self, nodeObj, clientData):
        '''Selectively update the widget tree for the specified item when a
        creaseSet is added to the Maya scene

        :Parameters:
            nodeObj (MObject)
                MObject depend node for the node added
            clientData
                container of the Maya client data for the event
        
        :Return: None
        '''
        logger.debug('In objectSetNodeAddedCB')
        if len(self._disableUpdateUIStack) > 0:
            return
        nodeFn   = om.MFnDependencyNode(nodeObj)
        nodeName = nodeFn.name()
        logger.debug('Node added: %s'%nodeName)

        # Get values from the objectSet
        colorIndex = maya.cmds.getAttr('%s.memberWireframeColor'%nodeName)
        creaseLevel = maya.cmds.getAttr('%s.creaseLevel'%nodeName)
        setMembers = maya.cmds.sets(nodeName, q=True)
        if setMembers == None:
            setMembers = []
            
        # Surgically add the item (and callbacks) to the UI (instead of repopulating entire widget)
        item = self.setItemValues(item=None, name=nodeName, colorIndex=colorIndex, creaseLevel=creaseLevel, members=setMembers)
        self.addPerNodeMayaCallbacks(nodeObj)


    def objectSetNodeRemovedCB(self, nodeObj, clientData):
        '''Selectively update the widget tree for the specified item when
        a creaseSet is removed from the Maya scene

        :Parameters:
            nodeObj (MObject)
                MObject depend node for the node added
            clientData
                container of the Maya client data for the event
        
        :Return: None
        '''
        logger.debug('In objectSetNodeRemovedCB')        
        if len(self._disableUpdateUIStack) > 0:
            return
        nodeName = om.MFnDependencyNode(nodeObj).name()
        logger.debug('Node to remove: %s'%nodeName)

        # Surgically remove the item from the UI (instead of repopulating entire widget)
        items = self.findItems(nodeName, Qt.MatchFixedString|Qt.MatchCaseSensitive, self.COLUMN_SETNAME)
        if len(items) > 0:
            if len(items) > 1:
                logger.debug('Unexpected multiple matches for %s.  Updating only first one in UI.'%nodeName)
            logger.debug('Updating UI for new value')
            item = items[0]
            logger.debug('Removing node from UI: %s'%nodeName)
            itemIndex = self.indexFromItem(item)
            self.takeTopLevelItem(itemIndex.row())  # remove the item
        else:
            logger.debug('Could not find a match for %s.  Skipping update in UI.'%nodeName)
        
        # Remove node callbacks
        self.removePerNodeMayaCallbacks([nodeObj])


    def objectSetNodeNameChangedCB(self, nodeObj, prevName, clientData):
        '''Selectively update the widget items when a Maya CreaseSet node name changes

        :Parameters:
            nodeObj (MObject)
                MObject depend node for the node added
            prevName (string)
                previous name of the node
            clientData
                container of the Maya client data for the event
        
        :Return: None
        '''
        logger.debug('In objectSetNodeNameChangedCB')
        if len(self._disableUpdateUIStack) > 0:
            return
        nodeFn   = om.MFnDependencyNode(nodeObj)
        nodeName = nodeFn.name()
        logger.debug('Node name changed: %s -> %s'%(prevName, nodeName))

        # tactically update the UI
        items = self.findItems(prevName, Qt.MatchFixedString|Qt.MatchCaseSensitive, self.COLUMN_SETNAME)
        if len(items) > 0:
            item = items[0]
            self.setItemValues(item, name=nodeName)
        else:
            logger.debug('Could not find a match for %s.  Skipping update in UI.'%prevName)


    def beforeSceneUpdatedCB(self, clientData):
        '''Freeze the callbacks before the entire scene is being reloaded or cleared.
        Unfreezing the callbacks is handled in the sceneUpdatedCB below.

        :Parameters:
            clientData
                container of the Maya client data for the event
        
        :Return: None
        '''
        logger.debug('beforeSceneUpdatedCB(%s)'%clientData)
        self._disableUpdateUIStack.append(clientData)


    def sceneUpdatedCB(self, clientData):
        '''The entire scene is being reloaded or cleared. Repopulate the entire widget.

        :Parameters:
            clientData
                container of the Maya client data for the event
        
        :Return: None
        '''
        logger.debug('sceneUpdatedCB(%s)'%clientData)
        # Expect that beforeSceneUpdatedCB() was called before to push an item onto the stack
        if len(self._disableUpdateUIStack) > 0:        
            disableUpdateItem = self._disableUpdateUIStack.pop()
            if disableUpdateItem != clientData:
                logger.debug('Unexpected item on \"%s\" _disableUpdateUIStack. Expected \"%s\"'%(disableUpdateItem, clientData))
        else:
            logger.debug('No items to pop on _disableUpdateUIStack. Expected beforeSceneUpdatedCB() to add one.')
        if len(self._disableUpdateUIStack) > 0:
            return
        self.repopulate()
    
    
    def objectSetAttrChangedCB(self, msg, plg, otherPlg, clientData):
        """Selectively update the widget tree for the specified item when
        the attributes of a creaseSet are modified
        
        :Parameters:
            msg (maya.OpenMaya.MNodeMessage)
                om.MNodeMessage enum for the action upon the attr.  Use '&' to check the value.
                Example use: msg&om.MNodeMessage.kAttributeSet
            plug (MPlug)
                MPlug for the attribute
            otherPlg (MPlug)
                MPlug for other connected attribute that may be contributing to this action
            clientData
                container of the Maya client data for the event
        
        :Return: None
        """
        logger.debug("objectSetAttrChangedCB: msg='%s' plg='%s' otherPlg='%s' clientData='%s'"%(msg, plg.name(), otherPlg.name(), clientData))
        if len(self._disableUpdateUIStack) > 0:
            logger.debug('Skipping. DisableUpdateUIStack has a items.')
            return
        if not (msg&om.MNodeMessage.kAttributeEval or msg&om.MNodeMessage.kAttributeSet):
            logger.debug('Skipping. Attr message does is not kAttributeEval or kAttributeSet')
            return
        (nodename, attrName) = plg.name().split('.',1)

        if attrName in ('creaseLevel', 'memberWireframeColor'):
            # tactically update the UI
            try:
                items = self.findItems(nodename, Qt.MatchFixedString|Qt.MatchCaseSensitive, self.COLUMN_SETNAME)
            except RuntimeError, e:
                logger.debug('objectSetAttrChangedCB skipped from RuntimeError, likely from deferred evaluation on deleted object. %s'%e)
                return # RETURN
            if len(items) > 0:
                if len(items) > 1:
                    logger.debug('Unexpected multiple matches for %s. Updating only first one in UI.'%nodename)
                logger.debug('Updating UI for new value')
                item = items[0]
                with PushValueOntoStack(self._disableUpdateUIStack, 'objectSetAttrChangedCB'):
                    if attrName == 'creaseLevel':
                        self.setItemValues(item, creaseLevel=plg.asFloat())
                    elif attrName == 'memberWireframeColor':  # mwc=memberWireframeColor
                        colorIndex = plg.asShort()
                        self.setItemValues(item, colorIndex=colorIndex)
                    else:
                        logger.debug('Unhandled attr %s in objectSetAttrChangedCB'%attrName)
            else:
                logger.debug('Could not find a nodeName match for %s in UI. Skipping update in UI.'%nodename)
            
    
    def objectSetMembersChangedCB(self, nodeObj, clientData):
        '''Selectively update the widget tree for the specified item when
        members are added/removed.  This updated column values for counts as well
        as updating the sub-items for the creaseSet.
        
        :Parameters:
            nodeObj (MObject)
                MObject depend node for the node added
            clientData
                container of the Maya client data for the event
        
        :Return: None
        '''
        logger.debug('In objectSetMembersChangedCB()')
        if len(self._disableUpdateUIStack) > 0:
            return
        changedSetFn = om.MFnSet(nodeObj)
        objectSetName = changedSetFn.name()
        logger.debug('objectSetMembersChangedCB: creaseSet=%s clientData=%s'%(objectSetName, clientData))

        # Performance: MAYA-27977
        #   Deferring action is done for performance reasons, otherwise you will get an update for each edge 
        #   added/removed.  If you have 100 objects each with 100 creases, then you have 10000 updates for a
        #   duplicate action.
        #
        # Issue: MAYA-18582
        #   The querying of the objectSets needs to execute deferred since it can mess up the DG state.
        #

        # If updateHighlightedItems is not already in the queue to be updated, add it to the idle event queue
        updateAlreadyRequested = (len(self._requested_objectSetMembersChanged) != 0)

        # Add to the internal list of item values to update
        self._requested_objectSetMembersChanged.add(objectSetName)

        # Kick off deferred processing if not already queued
        if not updateAlreadyRequested:
            maya.cmds.evalDeferred(self.updateUI_objectSetMembersChanged, low=True)
        else:
            logger.debug("Skipping on idle execute of setItemValues_execute(). Already queued.")


    def updateUI_objectSetMembersChanged(self):
        '''Selectively update the widget tree for the specified creaseSet.
        This function is called by the objectSetMembersChangedCB callback when
        membership changes.  This updated column values for counts as well
        as updating the sub-items for the creaseSet.

        It processes self._requested_objectSetMembersChanged.
        
        :Return: None

        :Note: It should be called 'deferred' from a MCallback so as not to mess with the DG state by performing queries.
        '''
        logger.debug('In updateUI_objectSetMembersChanged()')

        while (True):  # exit via exception below
            # Retrieve an item to process.  Remove it from the dict so the processing does not have
            # a race condition with the function adding values to _requested_setItemValues
            try:
                objectSetName = self._requested_objectSetMembersChanged.pop()
            except KeyError, e:
                break  # exit the loop
            logger.debug("In updateUI_objectSetMembersChanged(): processing %s"%objectSetName)

            try:
                items = self.findItems(objectSetName, Qt.MatchFixedString|Qt.MatchCaseSensitive, self.COLUMN_SETNAME)
            except RuntimeError, e:
                logger.debug('updateUI_objectSetMembersChanged skipped from RuntimeError, likely from deferred evaluation on deleted object. %s'%e)
                return # RETURN
            if len(items) > 0:
                # Update UI
                if len(items) > 1:
                    logger.debug('Unexpected multiple matches for %s. Updating only first one in UI.'%nodename)
                item = items[0]
                logger.debug('ObjectSet Name: %s'%objectSetName)
                try:
                   members = maya.cmds.sets(objectSetName, q=True)
                except ValueError, e:
                   logger.debug('updateUI_objectSetMembersChanged skipped as creaseSet %s does not exist'%objectSetName)
                   return
                if members == None:
                    members = []
                logger.debug('Updating UI for changes in membership creaseSet=%s members=%s'%(objectSetName, members))
                self.setItemValues(item, members=members)
                self.requestUpdateHighlightedItems() # Update selection count


    def mayaSelectionChangedCB(self, clientData):
        '''The selection has changed.  Update the background coloring of the items
        using the secondary highlight color (used by the Maya Outliner) to reflect member-set relationships.

        :Parameters:
            clientData
                container of the Maya client data for the event
        
        :Return: None
        '''
        logger.debug("In mayaSelectionChangedCB()")
        if len(self._disableUpdateUIStack) > 0:
            return
        self.requestUpdateHighlightedItems()
        

    def requestUpdateHighlightedItems(self):
        '''Request deferred update of the highlighted items to when Maya is idle.
        This improves performance when doing large operations like duplicating
        hundreds of objectSets.
        '''
        logger.debug("In requestUpdateHighlightedItems()")
        if len(self._disableUpdateUIStack) > 0:
            return

        # If updateHighlightedItems is not already in the 
        # queue to be updated, add it to the idle event queue
        if not self._requested_updateHighlightedItems:
            self._requested_updateHighlightedItems = True
            maya.cmds.evalDeferred(self.updateHighlightedItems_execute, low=True)
        else:
            logger.debug("Skipping on idle execute of updateHighlightedItems_execute(). Already queued.")


    def updateHighlightedItems_execute(self):
        '''Update the highlighted items (visualized by changing the background
        color of the item) to indicate the items that the Maya selected items
        are members of.
        '''
        logger.debug("In updateHighlightedItems_execute()")

        # Set the dirty flag to clean as updateHighlightedItems_execute
        # is being executed
        self._requested_updateHighlightedItems = False
        
        # Get list of creaseSets that have members that are selected
        dictContainingItems = getCreaseSetsContainingItems(asDict=True)
        creaseSetsWithSelectedMeshes = set(dictContainingItems.keys())

        # Update if needed
        if (creaseSetsWithSelectedMeshes != self._highlightedNames):
            # Handle highlighting changes
            itemsToHighlight     = self._highlightedNames       - creaseSetsWithSelectedMeshes
            itemsToDehighlight   = creaseSetsWithSelectedMeshes - self._highlightedNames
            for itemName in itemsToDehighlight:
                widgetItems = self.findItems (itemName, Qt.MatchFixedString|Qt.MatchCaseSensitive, self.COLUMN_SETNAME )
                if (len(widgetItems) > 0):
                    widgetItems[0].setBackground(self.COLUMN_SETNAME, self.highlightBackgroundBrush)
                    if len(widgetItems) > 1:
                        logger.debug('Should only have one item returned for %s'%itemName)
            for itemName in itemsToHighlight:
                widgetItems = self.findItems (itemName, Qt.MatchFixedString|Qt.MatchCaseSensitive, self.COLUMN_SETNAME )
                if (len(widgetItems) > 0):
                    widgetItems[0].setBackground(self.COLUMN_SETNAME, self.normalBackgroundBrush)
                    self.setItemValues(item=widgetItems[0], numSelectedMembers=0)
                    if len(widgetItems) > 1:
                        logger.debug('Should only have one item returned for %s'%itemName)
            
            # Update highlighted items
            self._highlightedNames = creaseSetsWithSelectedMeshes

        # Handle number of selected items
        for k,v in dictContainingItems.iteritems():
            widgetItems = self.findItems (k, Qt.MatchFixedString|Qt.MatchCaseSensitive, self.COLUMN_SETNAME )
            if (len(widgetItems) > 0):
                self.setItemValues(item=widgetItems[0], numSelectedMembers=v)
                if len(widgetItems) > 1:
                    logger.debug('Should only have one item returned for %s'%k)

        logger.debug("Exiting updateHighlightedItems_execute()")


# ==============
# CreaseSetTreeWidget Helpers
#   Classes used by CreaseSetTreeWidget
# ==============
class PushValueOntoStack:
    '''Safe way to push/pop of items onto a list (stack) using the "with" command
    It will push the value onto the list on entering the block and
    remove it on exit from the block.
    
    :Example:
        disableActionStack = []
        print disableActionStack
        with PushValueOntoStack(disableActionStack, 'outerLoop'):
            print disableActionStack
            with PushValueOntoStack(disableActionStack, 'innerLoop'):
                print disableActionStack
            print disableActionStack
        print disableActionStack
    '''
    def __init__(self, stackItem, value):
        self.stackItem = stackItem
        self.value = value
        
    def __enter__(self):
        self.stackItem.append(self.value)
        return None
    
    def __exit__(self, type, value, traceback):
        self.stackItem.pop()


class CreaseSetTreeWidgetItem(QTreeWidgetItem):
    '''QTreeWidgetItem tailored for the CreaseSetTreeWidget
    '''
    NUMERIC_COLUMNS = set([CreaseSetTreeWidget.COLUMN_CREASEVALUE, CreaseSetTreeWidget.COLUMN_NUMMEMBERS, CreaseSetTreeWidget.COLUMN_SELMEMBERS])
    
    def __init__(self, *args, **kwargs):
        super(CreaseSetTreeWidgetItem, self).__init__(*args, **kwargs)
        
        
    def __lt__(self, other):
        '''Properly handle numeric sorting for the columns that have numeric values
        '''
        col = self.treeWidget().sortColumn()
        if col in self.NUMERIC_COLUMNS:
            try:
                return float(self.text(col)) < float(other.text(col))
            except:
                pass
        # Fallback to use standard __lt__
        # WORKAROUND: PySide 1.1.1 produces a recursive issue if super(...).__lt__() used
        #             return super(CreaseSetTreeWidgetItem, self).__lt__(other)
        return self.text(col) < other.text(col)


# ==============
# CreaseSetEditor
# ==============

class CreaseSetEditor(QWidget):
    '''CreaseSetEditor widget
    
    :Contains:
        * row of buttons at the top for actions
        * the main column/tree view widget with popup menu for managing/selecting the creaseSets
    '''
    def __init__(self, parent=None, name=None, title=None):
        '''Init for the CreaseSetEditor
        Initializes its child widgets and sets up the button actions.
        
        :Parameters:
            parent (QWidget)
                parent Qt widget for this object.  Passed into the QWidget init function
            name (string)
                the objectName for this widget instance
            title (string)
                the windowTitle for this widget instance.  Defaults to 'CreaseSetEditor'.
        '''
        super(CreaseSetEditor, self).__init__(parent=parent)

        if name == None:
            name = 'CreaseSetEditor_%s'%uuid.uuid4()  # make it a unique name for Maya
        if title == None:
            title = maya.stringTable['y_creaseSetEditor.kCreaseSetEditorTitle' ]

        self.setObjectName(name)
        self.setWindowTitle(title)
        self.resize(250,300) 

        layout = QVBoxLayout()

        # Create Tree
        self.tree = CreaseSetTreeWidget(parent=self)
        
        # Create Button Bar
        #   Dict of labels, icons, and actions for the buttons
        #   NOTE: Paths starting with ':/' indicate using the embedded qrc resource path
        buttonLayout = QHBoxLayout()
        actions = [
            (maya.stringTable['y_creaseSetEditor.kNewCreaseSet'    ],  self.tree.newCreaseSetCB, ':/newLayerSelected.png'), # polyCreateCreaseSet.png #'subdivCrease.png'), #'subdivBaseMesh.png')
            (maya.stringTable['y_creaseSetEditor.kAddMembers'      ],    self.tree.addMembersCB, ':/trackAdd.png'),
            (maya.stringTable['y_creaseSetEditor.kRemoveMembers'   ], self.tree.removeMembersCB, ':/trackRemove.png'),
            (maya.stringTable['y_creaseSetEditor.kSelectMembers'   ], self.tree.selectMembersCB, (':/subdivMirror.png', 'subdivMirror.png')[(maya.cmds.about(api=True)<201300)]), # icon stored as resource in 2013
            (maya.stringTable['y_creaseSetEditor.kDeleteCreaseSet' ] , self.tree.deleteCreaseSetCB,(':/smallTrash.png'  , 'smallTrash.png'  )[(maya.cmds.about(api=True)<201300)]), # icon stored as resource in 2013
            ]
        for (cbTxt,cb,cbIconName) in actions:
            btn = QPushButton()
            btn.setText(cbTxt.split()[0])
            btn.setToolTip(cbTxt)
            cbPixmap = _findPixmapResource(cbIconName)  # returns a QPixmap for embedded image resource or on found in icon path
            if not cbPixmap.isNull():
                btn.setIcon(QIcon(cbPixmap))
            else:
                logger.debug('Unable to load icon %s'%cbIconName)
            btn.pressed.connect(cb)
            buttonLayout.addWidget(btn)

        # Create Menubar
        self.menubar = QMenuBar(self)
        def addMenuItem(menu, cbTxt, cb):
            action = QAction(cbTxt, self)
            action.triggered.connect(cb)
            menu.addAction(action)
            return action

        # Edit menu
        menu = self.menubar.addMenu(maya.stringTable['y_creaseSetEditor.kEditMenu' ])
        selectAction = addMenuItem(menu, maya.stringTable['y_creaseSetEditor.kEditSelectFromSel' ], self.tree.selectSetsWithSelectedMembersCB)
        menu.addSeparator()
        bakeAction   = addMenuItem(menu, maya.stringTable['y_creaseSetEditor.kEditBake' ], self.tree.bakeOutCreaseSetValuesCB)
        unbakeAction = addMenuItem(menu, maya.stringTable['y_creaseSetEditor.kEditUnBake' ], self.tree.unbakeValuesIntoCreaseSetsCB)
        menu.addSeparator()
        subdAction   = addMenuItem(menu, maya.stringTable['y_creaseSetEditor.kEditSubdivide' ], self.tree.subdivideBaseMeshCB)
        hardAction   = addMenuItem(menu, maya.stringTable['y_creaseSetEditor.kEditEdgeHardness' ], self.tree.hardenCreaseEdgesCB)
        def editMenuAboutToShow():
            creasesets = self.tree.getCurrentSetNames()
            meshes = getSelectedMeshComponents(meshShapes=True) 
            components = getSelectedMeshComponents(verts=True,edges=True)
            meshSelected = (len(creasesets) > 0 or len(meshes) > 0)
            selectAction.setEnabled(len(meshes) > 0 or len(components) > 0)
            bakeAction.setEnabled(meshSelected)
            unbakeAction.setEnabled(len(meshes) > 0)
            subdAction.setEnabled(meshSelected)
            hardAction.setEnabled(meshSelected)
        menu.aboutToShow.connect(editMenuAboutToShow)

        # Display menu
        menu = self.menubar.addMenu(maya.stringTable['y_creaseSetEditor.kDisplayMenu' ])
        optimizeDisplayAction = addMenuItem(menu, maya.stringTable['y_creaseSetEditor.kDisplayOptimal' ], self.tree.optimizeSubdLevelCB)
        defaultDisplayAction  = addMenuItem(menu, maya.stringTable['y_creaseSetEditor.kDisplayDefault' ], self.tree.unoptimizeSubdLevelCB)
        menu.addSeparator()
        updateColorAction     = addMenuItem(menu, maya.stringTable['y_creaseSetEditor.kDisplayUpdateColor' ], self.tree.calcCreaseValueColorSetCB)
        toggleColorAction     = addMenuItem(menu, maya.stringTable['y_creaseSetEditor.kdisplayToggleColor' ], self.tree.toggleCreaseValueColorSetCB)
        def displayMenuAboutToShow():
            creasesets = self.tree.getCurrentSetNames()
            meshes = getSelectedMeshComponents(meshShapes=True) 
            meshSelected = (len(creasesets) > 0 or len(meshes) > 0)
            optimizeDisplayAction.setEnabled(meshSelected)
            defaultDisplayAction.setEnabled(meshSelected)
            updateColorAction.setEnabled(meshSelected)
            toggleColorAction.setEnabled(meshSelected)
        menu.aboutToShow.connect(displayMenuAboutToShow)

        # Settings menu
        menu = self.menubar.addMenu(maya.stringTable['y_creaseSetEditor.kSettingsMenu' ])
        addMenuItem(menu, maya.stringTable['y_creaseSetEditor.kSettingsIncr' ], self.tree.setCreaseLevelIncrementCB)
        addMenuItem(menu, maya.stringTable['y_creaseSetEditor.kSettingsName' ], self.tree.setDefaultCreaseSetNameCB)

        # Layout main items
        layout.addWidget(self.menubar)
        layout.addLayout(buttonLayout)
        layout.addWidget(self.tree)
        self.setLayout(layout)


    def closeEvent(self, evt):
        evt.accept()


# ==============
# SHOW EDITOR
# ==============

# GLOBAL: Specify the default CreaseSetEditor class to use by showCreaseSetEditor()
#   This allows studios the ability to override the standard CreaseSetEditor
#   and replace it with their own and still use the existing menu items
#   for calling it
#   See setDefaultCreaseSetEditor(), getDefaultCreaseSetEditor()
_DefaultCreaseSetEditor = CreaseSetEditor


def getDefaultCreaseSetEditor():
    '''Get the current CreaseSetEditor class used by default.
    
    :Return: class CreaseSetEditor or derived class
    '''
    # If the _DefaultCreaseSetEditor variable has been defined and overridden, then use it.
    #   Otherwise use the standard CreaseSetEditor
    return _DefaultCreaseSetEditor


def setDefaultCreaseSetEditor(cls=CreaseSetEditor):
    '''Set the CreaseSetEditor class to use by default.
    This allows studios the ability to override the standard CreaseSetEditor
    and replace it with their own and still use the existing menu items
    for calling it
    
    :Parameters:
        cls (class)
            CreaseSetEditor or derived class. (default=CreaseSetEditor)
            
    :Example:
        import creaseSetEditor
        import myCreaseSetEditor
        creaseSetEditor.setDefaultCreaseSetEditor(myCreaseSetEditor.MyCreaseSetEditor)
        creaseSetEditor.showCreaseSetEditor()
    '''
    # Make sure the class passed in is the CreaseSetEditor or derived from it
    if not issubclass(cls, CreaseSetEditor):
        raise TypeError, _loadUIString('kInvalidCreaseEditorClass')%cls
    
    # GLOBAL VARIABLE: Set the new default CreaseSetEditor to use
    global _DefaultCreaseSetEditor
    _DefaultCreaseSetEditor = cls


def showCreaseSetEditor(dockControl=False, creaseSetEditorCls=None):
    '''Create the CreaseSetEditor (optionally in a dockControl) and make it visible.
    This is the main way to launch the CreaseSetEditor.

    :Parameters:
        dockControl (bool)
            display the widget by a dock control. Otherwise use a standard standalone window
            (default=True)
        creaseSetEditorCls (class)
            explicitly specify the CreaseSetEditor class (or derived class) to show.  If unspecified, then
            it defaults to the value from getDefaultCreaseSetEditor()
            (default=None, which means the standard CreaseSetEditor)
    
    :Note:
        Handle internals to remove any existing CreaseSetEditor so it does not conflict
        with this new one.
        
    :Return: Tuple of CreaseSetEditor and dock control string identifier if specified (QWidget, string)
    '''
    logger.debug("showCreaseSetEditor: CreaseSetEditor class: %s"%creaseSetEditorCls)
    
    # Determine the CreaseSetEditor class to use, if unspecified (or None) use the _DefaultCreaseSetEditor
    if creaseSetEditorCls == None:
        creaseSetEditorCls = getDefaultCreaseSetEditor()
        
    # Make sure the class used is the CreaseSetEditor or derived from it
    if not issubclass(creaseSetEditorCls, CreaseSetEditor):
        raise TypeError, _loadUIString('kInvalidCreaseEditorClass')%creaseSetEditorCls
    
    # API WORKAROUND MAYA-13960: Hardcode the name of the widget using objectName() to a known value.
    #   There needs to be a way to automatically generate a unique name for a widget so it can be uniquely
    #   identified by MQtUtil::findWidget(), dockControl, and other MEL/API commands.
    #   Since we want to guarantee uniqueness for this widget name, first delete any existing ones with
    #   the same name before creating a new one
    #   NOTE: One can use the python function uuid.uuid4() to create a unique name
    if maya.cmds.dockControl('CreaseSetEditorDock', ex=True):
        maya.cmds.deleteUI('CreaseSetEditorDock', control=True)  # deletes docked window completely
    elif maya.cmds.control('CreaseSetEditor', ex=True):
        winFullName = maya.cmds.control('CreaseSetEditor', q=True, fpn=True)
        maya.cmds.deleteUI(winFullName, control=True)  # only deletes control inside dockControl, not the dockControl window itself

    # Get a pointer to the main maya window to use as a parent 
    mainWindowPtr = omui.MQtUtil.mainWindow()
    mainWindow = wrapInstance(long(mainWindowPtr), QWidget) 

    # Create Window
    #   Parent the widget under the Maya mainWindow so it does not auto-destroy itself when the variable that references
    #   it goes out of scope
    win = creaseSetEditorCls(name='CreaseSetEditor', parent=mainWindow)
    
    # Dock or show the standalone window
    if dockControl:
        # Make the window dockable
        # Note: Should explicitly specify the parent as gMainWindow since otherwise it can on occasion error on creation
        #       with "RuntimeError: Controls must have a layout.  No layout found in window" 
        gMainPane = maya.mel.eval('$gMainPane=$gMainPane')  # API WORKAROUND: Extract variable from MEL into python as there is no maya.mel.variable() function
        dc = maya.cmds.dockControl('CreaseSetEditorDock', content=str(win.objectName()), parent=gMainPane, label=str(win.windowTitle()), allowedArea='all',area='right', floating=True)
        # Return the parent dock control
        return (win, dc)
    else:
        win.setWindowFlags(Qt.Window) # Make this widget a standalone window even though it is parented
        win.setProperty("saveWindowPref", True ) # identify a Maya-managed floating window, which handles the z order properly and saves its positions
        # Show window
        win.show()
        # Return the created CreaseSetEditor widget and an empty string since the dock control is not being used
        return (win, "")

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
