import maya.api.OpenMaya as OpenMaya
import maya.app.renderSetup.common.utils as commonUtils
import maya.app.renderSetup.model.utils as utils
import itertools

class DagPath(object):
    ''' 
    Helper class wrapper over MDagPath with specialized queries.
    '''
    def __init__(self, dagPath):
        '''Constructor. "dagPath" is a OpenMaya.MDagPath.'''
        super(DagPath, self).__init__()
        self.dagPath = dagPath
    
    @staticmethod
    def create(pathStr):
        '''Create a DagPath object for the given string path or None if it doesn't exist. '''
        dagPath = commonUtils.nameToDagPath(pathStr)
        return DagPath(dagPath) if dagPath else None
    
    def node(self):
        '''Returns the DAG node at the end of the path (as MObject).'''
        return self.dagPath.node()
    
    def fullPathName(self):
        '''Returns the full path string of this DAG path.'''
        return self.dagPath.fullPathName()
    
    def _getShapePath(self):
        '''
        Returns:
        - A MDagPath copy of self.dagPath if self.dagPath is already a path to a shape node.
        - A MDagPath to the only shape parented directly beneath self.dagPath if self.dagPath is a path to a transform node.
        - None otherwise.
        '''
        dagPath = OpenMaya.MDagPath(self.dagPath)
        try: dagPath.extendToShape()
        except RuntimeError: return None
        return dagPath
    
    def findSetsConnections(self, fnType=OpenMaya.MFn.kSet):
        ''' 
        Generator over all the connections from this path to a shading engine.
        There can be more than one if shape has per-face shading.
       
        Connections are returned as tuples (srcPlug, destPlug)
        "srcPlug" belongs to the shape node. "destPlug" belongs to the assigned shading engine node.
        srcPlug ---> destPlug
        '''
        shapePath = self.dagPath
        
        # get the parent instObjGroup plug
        instanceNr = shapePath.instanceNumber()
        node = OpenMaya.MFnDagNode(shapePath.node())
        instObjGroups = node.findPlug("instObjGroups", False)
        if instanceNr >= instObjGroups.evaluateNumElements():
            return
    
        # get whole instance and per face plugs 
        instObjGroup = instObjGroups.elementByLogicalIndex(instanceNr)
        objGroups = instObjGroup.child(0)
        plugs = itertools.chain([instObjGroup], # whole instance
            (objGroups.elementByLogicalIndex(i) for i in xrange(objGroups.evaluateNumElements()))) # per-face
        
        # yield all connections to shading engines
        for srcPlg in plugs:
            for dstPlg in srcPlg.destinations():
                if dstPlg.node().hasFn(fnType):
                    yield (srcPlg, dstPlg)
    
    def findShadingEngineConnections(self):
        shapePath = self._getShapePath()
        if not shapePath:
            return ()
        return DagPath(shapePath).findSetsConnections(OpenMaya.MFn.kShadingEngine)
        
    def findSets(self):
        return (dstPlug.node() for (_,dstPlug) in self.findSetsConnections())

    def findShadingEngines(self):
        '''Generator over all the shading engines assigned to this DAG path.
        There can be more than one if shape has per-face shading.'''
        return (dstPlug.node() for (_,dstPlug) in self.findShadingEngineConnections())
   
    def findSurfaceShaders(self):
        '''Generator over the surface shaders assigned to this DAG path.
        There can be more than one if shape has per-face shading.'''
        return itertools.ifilter(lambda o:o, (utils.findSurfaceShader(se,True) for se in self.findShadingEngines())) 
        
    def findDisplacementShaders(self):
        '''Generator over the displacement shaders assigned to this DAG path.
        There can be more than one if shape has per-face shading.'''
        return itertools.ifilter(lambda o:o, (utils.findDisplacementShader(se,False) for se in self.findShadingEngines())) 
        
    def findVolumeShaders(self):
        '''Generator over the volume shaders assigned to this DAG path.
        There can be more than one if shape has per-face shading.'''
        return itertools.ifilter(lambda o:o, (utils.findVolumeShader(se,False) for se in self.findShadingEngines())) 
    
    def findGeometryGenerator(self):
        '''Returns the mesh or nurbs generator of this DAG path if any, None otherwise.'''
        shapePath = self._getShapePath()
        if not shapePath:
            return None

        obj = shapePath.node()
        typeToAttr = {  OpenMaya.MFn.kMesh         : 'inMesh',
                        OpenMaya.MFn.kNurbsSurface : 'create'  } 
        
        for ktype, attr in typeToAttr.iteritems():
            if obj.hasFn(ktype):
                plg = OpenMaya.MFnDagNode(obj).findPlug(attr,False)
                # When per-face shading is applied to shapes, generators are not direct inputs to 
                # the shape node. It is at the beginning of a groupParts node chain.
                while plg.isDestination:
                    source = plg.source().node()
                    if not source.hasFn(OpenMaya.MFn.kGroupParts):
                        # We're done traversing groupParts nodes.
                        return source
                    plg = OpenMaya.MFnDependencyNode(source).findPlug('inputGeometry', False)
                return None
        
        # shape is neither a mesh nor a nurbs
        return None
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
