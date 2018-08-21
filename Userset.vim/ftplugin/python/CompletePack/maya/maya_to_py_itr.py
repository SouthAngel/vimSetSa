import maya.OpenMaya as om

"""
TODO : extend for the following classes

MItGeometry Iterator class for geometry data  
MItInstancer Particle iterator  
MItKeyframe Keyframe Iterator  
MItMeshEdge Polygon edge iterator  
MItMeshFaceVertex Face vertex iterator  
MItMeshPolygon Polygon iterator  
MItMeshVertex Polygon vertex iterator  
MItSelectionList Iterate over the items in the selection list  
MItSubdEdge Subdiv edge iterator  
MItSubdFace Subdiv face iterator  
MItSubdVertex Subdiv vertex iterator  
MItSurfaceCV NURBS surface CV iterator

to implement any of these just override the _item method

"""

class MayaToPyItr(object):
    """
    This class turns a non pythonic maya iterator into a standard
    python iterator that can be used with all the standard libs and idioms
    (for loops, list comprehensions, filters and maps).
    it dispatches unknown method calls to the wrapped maya iterator class
    """
    def _item(self):
        """
        This method should be overriden to return the current item of the maya iterator
        """
        raise NotImplemented('must override method _item')

    def _reset(self):
        """
        This method should be overriden in case of PyDgItr especially in the case
        MItDependencyNodes which doesn't provide a zero arg reset method
        """
        self._maya_iterator.reset()
    

    def __init__(self, maya_iterator):
        self._maya_iterator = maya_iterator

    def __iter__(self):
        # make iterator reusable
        self._reset()

        while not self._maya_iterator.isDone():
            yield self._item()
            self._maya_iterator.next()

    def __len__(self):
        items = 0
        for _ in self:
            items = items + 1
        return items

    # delegate all unknown methods and attr accesses to the maya iterator
    def __getattr__(self, attrname):
        return getattr(self._maya_iterator, attrname)

class PyEditItr(MayaToPyItr):
    """
    A class that wraps the MItEdits to make it work as a python iterator
    Usage Examples:

    edits = PyEditItr( om.MItEdits( assembly_mobject ) )
    for edit in edits:
       print(edit.getString())
       if edit.getType() == om.MEdit.kParentEdit:
           pe = edits.parentingEdit()

    # get how many edits the standard python way
    print(len(edits))

    # list comprehension with filter
    parent_edits = [edits.parentingEdit() for edit in edits if edits.currentEditType() == om.MEdit.kParentEdit]

    # map example
    edit_strings = [ e.getString() for e in edits ]
   
    """
    edit_factories = {
        om.MEdit.kSetAttrEdit : (lambda itr : itr.setAttrEdit()),
        om.MEdit.kConnectDisconnectEdit : (lambda itr : itr.connectDisconnectEdit()),
        om.MEdit.kAddRemoveAttrEdit : (lambda itr : itr.addRemoveAttrEdit()),
        om.MEdit.kParentEdit : (lambda itr : itr.parentingEdit()),
        om.MEdit.kFcurveEdit : (lambda itr : itr.fcurveEdit())
        }

    edit_factories.setdefault( lambda itr : itr.edit() ) 

    def __init__(self, mit_edits=None, ar_mobj=None):
        """
        mit_edits om.MItEdits the 
        ar_mobj assembly reference MObject
        """
        if ar_mobj:
            self._maya_iterator = om.MItEdits( ar_mobj )
        elif mit_edits:
            self._maya_iterator = mit_edits
        else:
            raise TypeError('PyEditItr require exactly one non NoneType')

    def _item(self):
        """
        look up the appropriate edit factory based on the type of edit and return
        the actual edit type instead of the more general MEdit
        """
        edit_factory = PyEditItr.edit_factories[self._maya_iterator.currentEditType()]
        return edit_factory( self._maya_iterator )

class PyDagItr(MayaToPyItr):
    """
    Wraps MItDag iterator making it function as a standard python
    iterator. A default MItDag iterator will be constructed if none is 
    specified.

    Usage Examples:
    # print tabbed dag hierarchy
    dag_objects = PyDagItr()
    for dag_object in dag_objects:
        print('%s%s' % ( '\t' * dag_objects.depth(), dag_object.fullPathName()) )

    """
    def _item(self):
        return om.MFnDagNode( self._maya_iterator.currentItem() )

    def __init__(self, mit_dag=om.MItDag()):
        self._maya_iterator = mit_dag

class PyDepGraphItr(MayaToPyItr):
    """
    This wraps MItDependencyGraph iterator and turns it into a python iterator
    """
    def _item(self):
        # use thisNode method because both 
        # MItDependencyGraph and MItDependencyNodes support it
        return om.MFnDependencyNode( self._maya_iterator.thisNode() )


class PyDepNodesItr(PyDepGraphItr):
    """
    This wraps MItDependencyNodes iterator turning it into a python iterator.
    A default MItDependencyNodes iterator will be constructed if none is 
    specified.
    """
    def __init__(self, mit_dependency_nodes=om.MItDependencyNodes(), 
                 filter=om.MFn.kInvalid, miterator_type=None):
        """
        filter and miterator_type are used to determine how to properly reset the
        mit_dependency_nodes iterator they should be the same values used to 
        construct mit_dependency_nodes iterator
        """
        # maybe call super constructor instead
        self._maya_iterator = mit_dependency_nodes

        self._filter = filter
        self._miterator_type = miterator_type

    def _reset(self):
        """
        override this method to compensate for the fact that MItDependencyNodes has no zero arg reset method
        """
        if self._miterator_type:
            self._maya_iterator.reset(self._miterator_type)
        else:
            self._maya_iterator.reset(self._filter)


class PyAssemblyItr(PyDagItr):
    """
    This iterates over all the scene assembly nodes in the scene
    usage example:
    assemblies = PyAssemblyItr()
    [assembly.name() for assembly in assemblies]
    """
    def __init__(self):
        self._maya_iterator = om.MItDag( om.MItDag.kDepthFirst, om.MFn.kAssembly )

    def _item(self):        
        return om.MFnAssembly( self._maya_iterator.currentItem() )
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
