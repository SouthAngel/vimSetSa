"""Selector node classes and utility functions.

   In the render setup system, a selector is a node that identifies which
   nodes (or more properly instances) to apply overrides to.  One selector
   node is associated with each collection: the collection is
   considered to own its associated selector.  The output of a selector
   node is a multi-line string, with one node name (or instance name) per
   line."""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.api.OpenMaya as OpenMaya
import maya.cmds as cmds
import re as re
import itertools
import weakref

import maya.app.renderSetup.model.typeIDs as typeIDs
import maya.app.renderSetup.model.utils as utils
import maya.app.renderSetup.model.undo as undo
import maya.app.renderSetup.model.sceneObservable as sceneObservable

import maya.app.renderSetup.model.algorithm as algorithm
from maya.app.renderSetup.model.selection import Selection
from maya.app.renderSetup.common.devtools import abstractmethod
from functools import partial

from maya.app.renderSetup.model.dagPath import DagPath

# List of undo titles
kSet = maya.stringTable['y_selector.kSet' ]

# Internal error messages
kNodeNotInStaticSelection  = "Node '%s' is not in static selection"
kNodeToAbsoluteNameFailure = "Failed to get the absolute name for '%s'"

# Status
kParentMissing = maya.stringTable['y_selector.kParentMissing' ]
kInvalidParent = maya.stringTable['y_selector.kInvalidParent' ]
kHasMissingObjects = maya.stringTable['y_selector.kHasMissingObjects' ]

def createTypeFilter(types):
    includes = [t for t in types if not t.startswith('-')]
    excludes = [t[1:] for t in types if t.startswith('-')]
    def filterFunction(name):
        for type in excludes:
            if cmds.objectType(name, isAType=type):
                return False
        for type in includes:
            if cmds.objectType(name, isAType=type):
                return True
        return len(includes) == 0
    return filterFunction

def createCustomFilter(customs):
    '''"customs" is a string of types and classifications. ex: 'shader/surface -blinn'
       returns a filter function over a node name that returns True if the name passes the custom filtering, False otherwise.'''
    filters = filter(None, re.split(r';|,|\s', customs))
    includes = [t for t in filters if not t.startswith('-')]
    excludes = [t[1:] for t in filters if t.startswith('-')]
    includeTypes = filter(utils.isExistingType, includes)
    excludeTypes = filter(utils.isExistingType, excludes)
    includeClassifications = filter(utils.isExistingClassification, includes)
    excludeClassifications = filter(utils.isExistingClassification, excludes)
    final = len(includes) == 0
    def filterFunction(name):
        for type in excludeTypes:
            if cmds.objectType(name, isAType=type):
                return False
        for classif in excludeClassifications:
            if cmds.getClassification(cmds.objectType(name), satisfies=classif):
                return False
        for type in includeTypes:
            if cmds.objectType(name, isAType=type):
                return True
        for classif in includeClassifications:
            if cmds.getClassification(cmds.objectType(name), satisfies=classif):
                return True
        return final
    return filterFunction
    
def createClassificationFilter(classification):
    def filterFunction(name):
        return cmds.getClassification(cmds.objectType(name), satisfies=classification)
    return filterFunction

class Filters(object):
    kAll                     = 0
    kTransforms              = 1
    kShapes                  = 2
    kShaders                 = 3
    kLights                  = 4
    kSets                    = 5
    kTransformsAndShapes     = 6
    kCameras                 = 7
    kCustom                  = 8
    kTransformsShapesShaders = 9
    kGenerators              = 10
    kShadingEngines          = 11
    
    _filterNames = {
        kCustom                  : "Custom",
        kAll                     : "All",
        kTransforms              : "Transforms",
        kShapes                  : "Shapes",
        kShaders                 : "Shaders",
        kLights                  : "Lights",
        kSets                    : "Sets",
        kTransformsAndShapes     : "Transforms and Shapes",
        kCameras                 : "Cameras",
        kGenerators              : "Geometry and NURBS",
        kTransformsShapesShaders : "Transforms, Shapes and Shaders",
        kShadingEngines          : "Shading engines"
    }
    # MFnEnumAttribute.addField uses non-localized strings, the UI makes use of
    # these localized ones.
    _filterUINames = {
        kCustom                  : maya.stringTable['y_selector.kCustomFilter' ],
        kAll                     : maya.stringTable['y_selector.kAllFilter' ],
        kTransforms              : maya.stringTable['y_selector.kTransformsFilter' ],
        kShapes                  : maya.stringTable['y_selector.kShapesFilter' ],
        kShaders                 : maya.stringTable['y_selector.kShadersFilter' ],
        kLights                  : maya.stringTable['y_selector.kLightsFilter' ],
        kSets                    : maya.stringTable['y_selector.kSetsFilter' ],
        kTransformsAndShapes     : maya.stringTable['y_selector.kTransformsAndShapesFilter' ],
        kCameras                 : maya.stringTable['y_selector.kCamerasFilter' ],
        kGenerators              : maya.stringTable['y_selector.kGeneratorsFilter' ],
        kTransformsShapesShaders : maya.stringTable['y_selector.kTransformsShapesShadersFilter' ],
        kShadingEngines          : maya.stringTable['y_selector.kShadingEnginesFilter' ]
    }
    names = { # names used to create subcollection's names suffixes
        kTransforms              : "transforms",
        kShapes                  : "shapes",
        kShaders                 : "shaders",
        kLights                  : "lights",
        kSets                    : "sets",
        kCameras                 : "cameras",
        kGenerators              : "generators",
        kShadingEngines          : "shadingEngines"
    }
    
    @staticmethod
    def filterName(ftype):
        return Filters._filterNames[ftype]

    @staticmethod
    def filterUIName(ftype):
        return Filters._filterUINames[ftype]
    
    _filterTypes = {
        kAll                 : ["-override", "-applyOverride"],
        kTransforms          : ["transform"],
        kShapes              : ["shape"],
        kSets                : ["objectSet"],
        kTransformsAndShapes : ["transform", "shape"],
        kCameras             : ["camera"],
        kGenerators          : ["polyCreator", "primitive"],
        kShadingEngines      : ["shadingEngine"]
    }
    _filterClassifications = {
        kShaders : 'shader/surface',
        kLights  : 'light'
    }
    @staticmethod
    def filterTypes(ftype):
        if ftype in Filters._filterTypes:
            return Filters._filterTypes[ftype]
        if ftype in Filters._filterClassifications:
            return cmds.listNodeTypes(Filters._filterClassifications[ftype])
        if ftype == Filters.kTransformsShapesShaders:
            return Filters._filterTypes[Filters.kTransformsAndShapes] + \
                   cmds.listNodeTypes(Filters._filterClassifications[Filters.kShaders])
    
    @staticmethod
    def filterFunction(ftype):
        if ftype in Filters._filterTypes:
            return createTypeFilter(Filters._filterTypes[ftype])
        if ftype in Filters._filterClassifications:
            return createClassificationFilter(Filters._filterClassifications[ftype])
        raise RuntimeError('Unknown type')
    
    @staticmethod
    def getFiltersFor(typeName):
        inherited = cmds.nodeType(typeName, inherited=True, isTypeName=True)
        def inherit(types):
            return reduce(lambda out,x : out or x in inherited, types, False)
        tests = itertools.chain(
            ((Filters.kShaders, lambda: utils.isSurfaceShaderType(typeName)),
            (Filters.kLights, lambda: 'light' in OpenMaya.MFnDependencyNode.classification(typeName))),
            ((filterType, lambda: inherit(Filters._filterTypes[filterType])) for filterType in ( Filters.kShadingEngines, Filters.kSets, Filters.kGenerators, Filters.kTransforms, Filters.kShapes )))
        for filterType,predicate in tests:
            if predicate():
                return (filterType, '')
        return (Filters.kCustom, typeName)
            
    _dagTypes = ( kAll, kTransforms, kShapes, kLights, kTransformsAndShapes, kCustom )
    _nonDagTypes = ( kAll, kShaders, kGenerators, kShadingEngines, kSets, kCustom )
    _allTypes = ( kAll, kTransforms, kShapes, kShaders, kLights, kShadingEngines, kSets, kGenerators, kCustom )
    
    
def _mSelectionListToAbsoluteNames(selection):
    '''Generator that converts nodes in a MSelectionList to long names.
       i.e. absolute path for dag nodes or instances and names for dependency (non-dag) nodes.'''
    for i in range(0,selection.length()):
        try:
            yield selection.getDagPath(i).fullPathName()
        except TypeError:
            yield OpenMaya.MFnDependencyNode(selection.getDependNode(i)).name()

def _nodesToLongNames(selection, permissive=False):
    '''Generator that converts name/MObject/MDagPath/MDagNode/MFnDependencyNode to long names.
       i.e. absolute paths for dag nodes or instances and names for dependency (non-dag) nodes.'''
    sl = OpenMaya.MSelectionList()
    for name in selection:
        sl.clear()
        try:
            sl.add(name)
        except RuntimeError as e:
            # name not found
            if permissive and isinstance(name,basestring):
                yield name
                continue
            else:
                # this should never happen
                raise RuntimeError(kNodeToAbsoluteNameFailure % str(name))
        try:
            yield sl.getDagPath(0).fullPathName()
        except TypeError:
            yield OpenMaya.MFnDependencyNode(sl.getDependNode(0)).name()
        
def selectionToAbsoluteNames(selection, permissive=False):
    '''Generator that converts selected nodes to long names.
       i.e. absolute paths for dag nodes or instances and names for dependency (non-dag) nodes.
       "selection" can either be a MSelectionList or an iterable of nodes.
       if permissive, invalid nodes names (strings) are kept.'''
    if isinstance(selection, OpenMaya.MSelectionList):
        return _mSelectionListToAbsoluteNames(selection)
    return _nodesToLongNames(selection, permissive)


def ls(patterns, types=None):
    '''
    Returns a set containing all the nodes matching patterns and types.
    '''
    #Default argument correction
    if types is None:
        types = []
    includeTypes = [t for t in types if not t.startswith('-')]
    
    def addPattern(selection, pattern):
        update = set.update
        if pattern.startswith(r'-'):
            pattern = pattern[1:]
            update = set.difference_update
        update(selection, cmds.ls(pattern, type=includeTypes, long=True) if pattern != '*' \
            else cmds.ls(type=includeTypes, long=True))
        return selection
    selection = reduce(addPattern, patterns, set())
    
    # Apparently, ls -excludeType cannot be used in conjunction with a pattern...
    # it does the same as -type when we do so... 
    # i.e. ls -excludeType transform "*" returns all the transforms...
    # => must exclude types ourselves
    excludeTypes = [t for t in types if t.startswith('-')]
    if len(excludeTypes) > 0:
        selection = itertools.ifilter(createTypeFilter(excludeTypes), selection)
    
    return set(selection)

class Selector(OpenMaya.MPxNode):
    '''Selector node base class (abstract).
    
    A selector is a node that is responsible for finding nodes and/or dag paths
    given some search criterions.'''

    kTypeId = typeIDs.selector
    kTypeName = "selector"
    
    # aIn, aOut are integer attributes, they are only used to specify 
    # relationships between selectors and allow dirty propagation
    aIn   = OpenMaya.MObject()
    aOut  = OpenMaya.MObject()

    # Attribute for message connection to collection node which owns
    # this selector.  We use a source message attribute, which doesn't
    # correspond to the intended data model, as a selector is owned by a
    # single collection, but the collection's selector
    # attribute is also a destination, and destination to destination
    # message connections produce errors on connection lookup.
    collection = OpenMaya.MObject()
    
    # Optional callbacks
    # These are functions of the form onSomeEvent(self, **kwargs)
    # kwargs are defined such as in sceneObservable.py
    # Subclasses can override them to handle the corresponding event
    onNodeAdded = None
    onNodeRemoved = None
    onNodeRenamed = None
    onNodeReparented = None
    onConnectionChanged = None
    onReferenceLoaded = None
    onReferenceUnloaded = None
    
    kDagOnly = 1
    kNonDagOnly = 2
    kDagOrNonDag = 3 # (kDagOnly | kNonDagOnly)
    
    @abstractmethod
    def contentType(self):
        pass
    
    def hasDagNodes(self):
        return self.contentType() != Selector.kNonDagOnly
    
    @staticmethod
    def synced(f):
        '''Decorator for Selector's functions to guarantee selection is up to date (_update() is called if needed).
        Must decorate an instance function (starting with self).'''
        def wrapper(*args, **kwargs):
            self = args[0]
            OpenMaya.MPlug(self.thisMObject(), Selector.aOut).asInt() # trigger update if plug is dirty
            return f(*args, **kwargs)
        return wrapper
    
    @classmethod
    def create(cls, name):
        fn = OpenMaya.MFnDependencyNode()
        obj = fn.create(cls.kTypeId, name)
        return fn.userNode()

    @classmethod
    def creator(cls):
        return cls()
    
    @staticmethod
    def createInput(attr, args):
        obj = attr.create(*args)
        attr.storable = True
        attr.writable = True
        return obj
        
    @classmethod
    def affectsOutput(cls, attr):
        cls.attributeAffects(attr, Selector.aOut)
    
    @staticmethod
    def initializer():
        attrFn = OpenMaya.MFnNumericAttribute()
        def createDirtyAttr(longName, shortName):
            obj = attrFn.create(longName, shortName, OpenMaya.MFnNumericData.kInt, 0)
            attrFn.hidden = True
            Selector.addAttribute(obj)
            return obj
        
        Selector.aIn  = createDirtyAttr( 'input',  'in')
        Selector.aOut = createDirtyAttr('output', 'out')
        Selector.affectsOutput(Selector.aIn)
        
        Selector.collection = utils.createSrcMsgAttr('collection', 'c')
        Selector.addAttribute(Selector.collection)
    
    def __init__(self):
        super(Selector, self).__init__()
        self._selection = None
        self._callbacks = None
        self._cbId = None
    
    def postConstructor(self):
        self.activate()
        
    def isAbstractClass(self):
        # Used only as base class, cannot be created.
        return True
    
    def _onNodeRemoved(self, obj, clientData):
        if obj == self.thisMObject():
            self.deactivate()
    
    def activate(self):
        '''Called when the selector is used in an active collection.
        Override this method to do any scene specific initialization.'''
        if self._callbacks:
            return # already activated
        
        self._cbId = None
        self._callbacks = {
            sceneObservable.SceneObservable.NODE_ADDED : self.onNodeAdded,
            sceneObservable.SceneObservable.NODE_REMOVED : self.onNodeRemoved,
            sceneObservable.SceneObservable.NODE_RENAMED : self.onNodeRenamed, 
            sceneObservable.SceneObservable.NODE_REPARENTED : self.onNodeReparented, 
            sceneObservable.SceneObservable.CONNECTION_CHANGED : self.onConnectionChanged,
            sceneObservable.SceneObservable.REFERENCE_LOADED : self.onReferenceLoaded,
            sceneObservable.SceneObservable.REFERENCE_UNLOADED : self.onReferenceUnloaded }
        
        # create the callbacks if they are defined
        observable = sceneObservable.instance()
        for cbtype, callback in self._callbacks.iteritems():
            if callback:
                observable.register(cbtype, callback)
                if not self._cbId:
                    self._cbId = OpenMaya.MDGMessage.addNodeRemovedCallback(self._onNodeRemoved, Selector.kTypeName)

    def deactivate(self):
        '''Called when the selector is used in an active collection.
        Override this method to do any scene specific teardown. '''
        if not self._callbacks:
            return # already deactivated
            
        if self._cbId:
            OpenMaya.MMessage.removeCallback(self._cbId)
        
        # remove the callbacks if they are defined
        observable = sceneObservable.instance()
        for cbtype, callback in self._callbacks.iteritems():
            if callback:
                observable.unregister(cbtype, callback)
        
        self._callbacks = self._cbId = None
    
    def parent(self):
        '''Returns the parent of this selector if any, None otherwise.'''
        return utils.getSrcUserNode(OpenMaya.MPlug(self.thisMObject(), self.aIn))
        
    def setParent(self, parent):
        with undo.NotifyCtxMgr('Set selector\'s parent', self.selectionChanged):
            prevParent = self.parent()
            if prevParent:
                cmds.disconnectAttr(prevParent.name()+".out", self.name()+".in")
            if parent:
                cmds.connectAttr(parent.name()+".out", self.name()+".in")
    
    def isTraversingConnections(self):
        return False
    
    # functions for subclasses to override
    @abstractmethod
    def _update(self, dataBlock):
        '''Update the selection cache of this selector using dataBlock. Must be overridden by subclasses.
        This is called in Selector.compute() function, when output is dirty.'''
        pass
    
    def nodes(self):
        '''Return selection content as MObjects iterable.'''
        return ()
    
    def paths(self):
        '''Return selection content as DagPath iterable.'''
        return ()
    
    def names(self):
        '''Return selection content as name string iterable.'''
        return ()
    
    def status(self):
        '''Returns the status of this selector (a string warning/error or None).'''
        return None
    
    def minimalClone(self, other):
        '''Does a minimal copy of other (Selector) to search for the same kind of objects.
           "other" must be the same type as "self".
           To be overriden by subclasses if needed.'''
        return
    
    def _setDirty(self):
        cmds.dgdirty(self.name()+".out", propagation=True)
        
    def isDirty(self):
        return cmds.isDirty(self.name()+".out", d=True)
    
    def selectionChanged(self):
        self._setDirty()
        owner = self.owner()
        if owner:
            owner._selectedNodesChanged()
    
    def compute(self, plug, dataBlock):
        # to ensure that self._selection cache is rebuilt on self.selection() call
        self._selection = None
        if plug == Selector.aOut:
            self._update(dataBlock)
            # need to set the input clean to allow correct dirty propagation
            # since we're using it only for this but not actually pulling its value.
            # (setting the output clean implies nothing on the cleanliness of the inputs and
            # dirty propagation recursion stops on already dirtied plugs)
            dataBlock.setClean(self.aIn)
            dataBlock.setClean(plug)
    
    def owner(self):
        """ Find the collection owner of this selector."""
        # Since we're forced to use a source attribute, the return type is
        # an array, but its length must be one.
        dst = utils.getDstUserNodes(OpenMaya.MPlug(self.thisMObject(), self.collection))
        return dst[0] if dst else None

    # for backward compatibility
    def getAbsoluteNames(self):return self.names()

class StaticSelection(object):
    '''
    Class that represents a static selection of nodes, without duplicates (a set).
    It has specialized functions to add/remove/set nodes and optimized query functions.
    '''
    
    def __init__(self, selector):
        '''Constructor of the StaticSelection.
        "selector" is the BasicSelector this static selection belongs to.'''
        super(StaticSelection, self).__init__()
        self._selector = weakref.ref(selector)
        # caches
        self._cList = None # selection as a list with deterministic order
        self._cSet = None # selection as a set for quick queries
        self._cFilteredOut = None # dictionary <name(string)> : <is name filtered out(bool)>
        self._cHasMissing = None # bool
        self._cHasFilteredOut = None # bool
    
    # mutators
    def set(self, selection):
        '''Sets the given nodes as the new static selection.
           "selection" can either be a MSelectionList or an iterable of node names or dag paths or dag nodes or dependency nodes.'''
        self._setStr('\n'.join(selectionToAbsoluteNames(selection)))

    def setWithoutExistenceCheck(self, selection):
        '''Sets the given nodes as the new static selection.
           "selection" can either be a MSelectionList or an iterable of node names or dag paths or dag nodes or dependency nodes.
           NOTE: Do not use. Reserved for Render Settings nodes.'''
        self._setList(selectionToAbsoluteNames(selection, True))

    def add(self, selection):
        '''Adds the given nodes to the static selection.
           "selection" can either be a MSelectionList or an iterable of node names or dag paths or dag nodes or dependency nodes.'''
        toAddStr = '\n'.join(s for s in selectionToAbsoluteNames(selection) if s not in self.asSet())
        if len(toAddStr) != 0:
            prev = self._getStr()
            self._setStr((prev+'\n' if len(prev) != 0 else prev) + toAddStr)
        
    def remove(self, selection):
        '''Removes the given nodes from the static selection.
           "selection" can either be a MSelectionList or an iterable of node names or dag paths or dag nodes or dependency nodes.'''
        toRemove = set( s for s in selectionToAbsoluteNames(selection, True) if s in self.asSet() )
        if len(toRemove) != 0:
            self._setList(item for item in self.asList() if item not in toRemove)
    
    # queries
    def __iter__(self):
        '''Generator over the all the selection in deterministic order.'''
        return ( key for key in self.asList() )
    
    def __contains__(self, node):
        '''Return True if node is in the static selection. False otherwise.'''
        return self._key(node) in self.asSet()
        
    def __len__(self):
        '''Return the length of the static selection (including missing/filtered out items).'''
        return len(self.asList())
        
    def asList(self):
        '''Returns the static selection items as a list.'''
        if self._cList is None:
            self._cList = self._getStr().split()
        return self._cList

    def setCache(self, names):
        '''Caches the static selection items as a list.'''
        self.dirtySelectionCB()
        self._cList = names.split()
    
    def asSet(self):
        '''Returns the static selection items as a set.'''
        if self._cSet is None:
            self._cSet = set(self.asList())
        return self._cSet
    
    def isMissing(self, node):
        '''Returns True if the given node is in the static selection but missing in the scene.
           Raises RuntimeError if given node is not in the static selection.'''
        return self._isMissing(self._existingKey(node))
    
    def isFilteredOut(self, node):
        '''Returns True if given node is in the static selection but filtered out.
           Raises RuntimeError if given node is not in the static selection.'''
        return self._isFilteredOut(self._existingKey(node))
    
    def hasMissingObjects(self):
        '''Returns True if static selection contains an object that doesn't exist in the scene. False otherwise.'''
        hasMissing = self._cHasMissing
        if hasMissing is None:
            self._cHasMissing = hasMissing = False
            for key in self.asList():
                if self._isMissing(key):
                    return True
        return hasMissing
    
    def hasFilteredOutObjects(self):
        '''Returns True if static selection contains filtered out nodes. False otherwise.'''
        hasFilteredOut = self._cHasFilteredOut
        if hasFilteredOut is None:
            self._cHasFilteredOut = hasFilteredOut = False
            for key in self.asList():
                if self._isFilteredOut(key):
                    return True
        return hasFilteredOut
    
    # encoding / decoding
    def encode(self):
        '''Encodes the static selection into a string.'''
        return self._getStr()
    
    def decode(self, string):
        '''Decodes the static selection from a string.'''
        self._setStr(string)
        
    # private methods
    def _setList(self, lst):
        self.dirtySelectionCB()
        self._cList = list(lst)
        self._setStr('\n'.join(self._cList))
    
    def _setStr(self, string):
        self._selector()._setStaticSelectionString(string)
    
    def _getStr(self):
        return self._selector()._getStaticSelectionString()
   
    def _key(self, node):
        '''Returns the key string unambiguously representing the given node.'''
        if isinstance(node, basestring) and node in self.asSet():
            return node
        return list(selectionToAbsoluteNames([node], True))[0]
    
    def _existingKey(self, node):
        '''Returns the key string unambiguously reprensenting the given node
        if it is in the static selection. Raises RuntimeError otherwise.'''
        key = self._key(node)
        if key not in self.asSet():
            raise RuntimeError(kNodeNotInStaticSelection % key)
        return  key
    
    def _isMissing(self, key):
        isMissing = not cmds.objExists(key)
        if isMissing:
            self._cHasMissing = True
        return isMissing
    
    def _isFilteredOut(self, key):
        if self._isMissing(key):
            return False
        filteredOut = self._cFilteredOut
        if filteredOut is None:
            self._cFilteredOut = filteredOut = dict()
        if key not in filteredOut:
            filteredOut[key] = not self._selector().acceptsType(cmds.nodeType(key))
            if filteredOut[key]:
                self._cHasFilteredOut = True
        return filteredOut[key]
    
    # callbacks
    def dirtySelectionCB(self):
        '''Clears all cache.'''
        self._cList, self._cSet = (None, None)
        self.dirtyFilterCB()
        self.dirtyMissingCB()
    
    def dirtyFilterCB(self):
        '''Clears filter-related cache.'''
        self._cFilteredOut, self._cHasFilteredOut = (None, None)
    
    def dirtyMissingCB(self):
        '''Clears missing objects related cache.'''
        self._cHasMissing = None  
    
    def _onSceneChanged(self, item):
        if item in self:
            self.dirtyMissingCB()
            return True
        return False
    
    def onNodeAdded(self, obj):
        return self._onSceneChanged(OpenMaya.MFnDagNode(obj).getPath() if obj.hasFn(OpenMaya.MFn.kDagNode) else obj)
    
    def onNodeRemoved(self, obj):
        item = OpenMaya.MFnDagNode(obj).getPath() if obj.hasFn(OpenMaya.MFn.kDagNode) else obj
        if item in self:
            self._cHasMissing = True
            return True
        return False
    
    def onNodeRenamed(self, obj, oldName):
        newList = list(self.asList())
        
        if obj.hasFn(OpenMaya.MFn.kDagNode):
            paths = (path.fullPathName() for path in OpenMaya.MFnDagNode(obj).getAllPaths())
            replacements = { path[:path.rfind('|')+1]+oldName:path for path in paths }
        else:
            replacements = { oldName:OpenMaya.MFnDependencyNode(obj).name() }
        
        hasChanged = False
        for i, name in enumerate(newList):
            for before, after in replacements.iteritems():
                if name.startswith(before) and (len(name) == len(before) or name[len(before)]=='|'):
                    newList[i] = after+name[len(before):]
                    hasChanged = True
                elif name.startswith(after) and cmds.objExists(name):
                    # object is no longer missing
                    hasChanged = True
        if hasChanged:
            self._setList(newList)
        return hasChanged
    
    def onNodeReparented(self, msgType, child, parent):
        return self._onSceneChanged(child)


class Strategy(object):
    '''Abstract parent class for strategies for finding nodes given an input Selection.
       items(self, selection) returns an iterable of items found by the strategy.
       An item can be a MObject, a MDagPath or a string (existing node name or existing dag path).'''
    
    @abstractmethod
    def create(cls, filterType, customs):
        '''Returns a Strategy specialized for the given filters or None if the strategy doesn't apply to the given filter.
           Must be redefined by subclasses.'''
        pass
    
    @abstractmethod
    def items(self, selection):
        '''Returns the items found using the strategy.
           Must be redefined by subclasses.'''
        pass
    
    @abstractmethod
    def onConnectionChanged(self, selector, srcPlug, dstPlug, made):
        pass
        
    @abstractmethod
    def isTraversingConnections(self):
        pass
    

class DagStrategy(Strategy):
    '''Strategy for searching in the dag hierarchy.'''
    
    def __init__(self, filterType):
        self.shapesOnly = filterType in { Filters.kShapes, Filters.kLights }
        self.filterFunct = {
            Filters.kAll        : None,
            Filters.kTransforms : (lambda path: path.node().hasFn(OpenMaya.MFn.kTransform)),
            Filters.kShapes     : (lambda path: path.node().hasFn(OpenMaya.MFn.kShape)),
            Filters.kLights     : (lambda path: cmds.getClassification(OpenMaya.MFnDependencyNode(path.node()).typeName, satisfies='light')),
            Filters.kCustom     : None
        }[filterType]
    
    @staticmethod
    def create(filterType, customs):
        if filterType in { Filters.kAll, Filters.kTransforms, Filters.kShapes, Filters.kLights }:
            return DagStrategy(filterType)
        if filterType==Filters.kCustom and reduce(lambda out,x: out or utils.isInheritedType('dagNode',x), customs, False):
            return DagStrategy(filterType)
        return None
    
    def items(self, selection):
        return itertools.ifilter(self.filterFunct, selection.shapes() if self.shapesOnly else selection.hierarchy())
        
    def onConnectionChanged(self, selector, srcPlug, dstPlug, made):
        pass # not traversing any connection, only dag hierarchy
    
    def isTraversingConnections(self):
        return False

class TraversingConnectionStrategy(Strategy):
    def isTraversingConnections(self):
        return True

class ShadingEngineStrategy(TraversingConnectionStrategy):
    '''Strategy for finding assigned materials (shading engines).'''
    
    @staticmethod
    def create(filterType, customs):
        if filterType in { Filters.kAll, Filters.kShadingEngines }:
            return ShadingEngineStrategy()
        if filterType==Filters.kCustom and reduce(lambda out,x: out or utils.isInheritedType('shadingEngine',x), customs, False):
            return ShadingEngineStrategy()
        return None
        
    @staticmethod
    def _findShadingEngines(dagPaths):
        treated = set()
        for dagPath in dagPaths:
            for engine in dagPath.findShadingEngines():
                name = OpenMaya.MFnDependencyNode(engine).name()
                if name not in treated:
                    treated.add(name)
                    yield engine
    
    def items(self, selection):
        return itertools.chain(ShadingEngineStrategy._findShadingEngines(DagPath(p) for p in selection.shapes()),
            (o for o in selection.nonDagNodes() if o.hasFn(OpenMaya.MFn.kShadingEngine)))
    
    def onConnectionChanged(self, selector, srcPlug, dstPlug, made):
        # shape => shadingEngine
        if srcPlug.node().hasFn(OpenMaya.MFn.kShape) and dstPlug.node().hasFn(OpenMaya.MFn.kShadingEngine):
            selector.selectionChanged()

class ShadingStrategy(TraversingConnectionStrategy):
    '''Strategy for finding shading nodes in shading networks of assigned materials.'''
    
    def __init__(self, surface, displace, volume, network):
        # booleans telling if the strategy needs to search for surface shaders, 
        # volume shaders, displacement shaders and input nodes (networks) of those
        self.surface  = surface
        self.displace = displace
        self.volume   = volume
        self.network  = network
    
    @staticmethod
    def create(filterType, customs):
        def createCustom():
            shading  = set(filter(utils.isShadingType, customs))
            if len(shading)==0:
                return None # nothing related to shading nodes
            surface  = set(filter(lambda t: 'shader/surface' in OpenMaya.MFnDependencyNode.classification(t), customs))
            displace = set(filter(lambda t: 'shader/displacement' in OpenMaya.MFnDependencyNode.classification(t), customs))
            volume   = set(filter(lambda t: 'shader/volume' in OpenMaya.MFnDependencyNode.classification(t), customs))
            network  = ( surface | displace | volume ) != shading
            if network:
                surface = displace = volume = True
            else:
                surface, displace, volume = (len(s)>0 for s in (surface, displace, volume))
            return ShadingStrategy(surface, displace, volume, network)
        
        return {
            Filters.kShaders : partial(ShadingStrategy, surface=True, displace=False, volume=False, network=False),
            Filters.kAll     : partial(ShadingStrategy, surface=True, displace=True,  volume=True,  network=True),
            Filters.kCustom  : createCustom,
        }.get(filterType, lambda:None)()
    
    @staticmethod
    def _findSurfaceShaders(engines):
        return itertools.ifilter(None, (utils.findSurfaceShader(engine, True) for engine in engines))
        
    @staticmethod
    def _findDisplacementShaders(engines):
        return itertools.ifilter(None, (utils.findDisplacementShader(engine, False) for engine in engines))
        
    @staticmethod
    def _findVolumeShaders(engines):
        return itertools.ifilter(None, (utils.findVolumeShader(engine, False) for engine in engines))
        
    def items(self, selection):
        engines = list(ShadingEngineStrategy._findShadingEngines(DagPath(p) for p in selection.shapes()))
        objs = itertools.chain(
            ShadingStrategy._findSurfaceShaders(engines) if self.surface else (),
            ShadingStrategy._findDisplacementShaders(engines) if self.displace else (),
            ShadingStrategy._findVolumeShaders(engines) if self.volume else ())
        if self.network:
            objs = algorithm.traverse(objs, predicate=utils.isShadingNode)
        return itertools.chain(objs, 
            (o for o in selection.nonDagNodes() if utils.isShadingNode(o)))
    
    def onConnectionChanged(self, selector, srcPlug, dstPlug, made):
        # shape => shadingEngine <= shader [<= shading nodes]*
        # skip shaders we don't need to find and shading nodes if we don't need to traverse network
        srcNode, dstNode = srcPlug.node(), dstPlug.node()
        if dstNode.hasFn(OpenMaya.MFn.kShadingEngine):
            if srcNode.hasFn(OpenMaya.MFn.kShape):
                selector.selectionChanged()
            else:
                classification = OpenMaya.MFnDependencyNode.classification(OpenMaya.MFnDependencyNode(srcNode).typeName)                
                if (self.surface and 'shader/surface' in classification) or \
                    (self.volume and 'shader/volume' in classification) or \
                    (self.displace and 'shader/displacement' in classification):
                    selector.selectionChanged()
        elif self.network and utils.isShadingNode(srcNode) and utils.isShadingNode(dstNode):
            selector.selectionChanged()

class GeneratorStrategy(TraversingConnectionStrategy):
    '''Strategy for finding geometry generators.'''
    
    @staticmethod
    def create(filterType, customs):
        if filterType in { Filters.kAll, Filters.kGenerators }:
            return GeneratorStrategy()
        if filterType==Filters.kCustom and \
            reduce(lambda out,x: out or utils.isInheritedType('primitive',x) or utils.isInheritedType('polyCreator',x), customs, False):
            return GeneratorStrategy()
        return None
    
    @staticmethod
    def _findGeometryGenerators(dagPaths):
        return itertools.ifilter(None, (dagPath.findGeometryGenerator() for dagPath in dagPaths))
    
    def items(self, selection):
        return itertools.chain(GeneratorStrategy._findGeometryGenerators(DagPath(p) for p in selection.shapes()),
            (o for o in selection.nonDagNodes() if o.hasFn(OpenMaya.MFn.kPolyCreator) or o.hasFn(OpenMaya.MFn.kPrimitive)))
    
    def onConnectionChanged(self, selector, srcPlug, dstPlug, made):
        # shape [<= groupParts]* <= generator (geom/nurbs)
        srcTypes = (OpenMaya.MFn.kPolyCreator, OpenMaya.MFn.kPrimitive, OpenMaya.MFn.kGroupParts)
        dstTypes = (OpenMaya.MFn.kShape, OpenMaya.MFn.kGroupParts)        
        if reduce(lambda out,x: out or srcPlug.node().hasFn(x), srcTypes, False) and \
            reduce(lambda out,x: out or dstPlug.node().hasFn(x), dstTypes, False):
            selector.selectionChanged()
            
class SetStrategy(TraversingConnectionStrategy):
    '''Strategy for finding sets containing the dag paths in the selection.'''
    
    @staticmethod
    def create(filterType, customs):
        if filterType in { Filters.kAll, Filters.kSets }:
            return SetStrategy()
        if filterType==Filters.kCustom and reduce(lambda out,x: out or not utils.isInheritedType('shadingEngine',x) and utils.isInheritedType('objectSet',x), customs, False):
            return SetStrategy()
        return None
        
    @staticmethod
    def _findSets(dagPaths, findMtd=DagPath.findSets):
        treated = set()
        for dagPath in dagPaths:
            for objectSet in findMtd(dagPath):
                name = OpenMaya.MFnDependencyNode(objectSet).name()
                if name not in treated:
                    treated.add(name)
                    yield objectSet
    
    def items(self, selection):
        return itertools.chain(SetStrategy._findSets(DagPath(p) for p in selection.paths()),
            (o for o in selection.nonDagNodes() if o.hasFn(OpenMaya.MFn.kSet)))
    
    def onConnectionChanged(self, selector, srcPlug, dstPlug, made):
        # dag => set
        if srcPlug.node().hasFn(OpenMaya.MFn.kDagNode) and dstPlug.node().hasFn(OpenMaya.MFn.kSet):
            selector.selectionChanged()

class CompositeStrategy(Strategy):
    def __init__(self, strategies):
        self._strategies = strategies
        
    def __str__(self):
        return str(self._strategies)
    
    def items(self, selection):
        return itertools.chain.from_iterable(strategy.items(selection) for strategy in self._strategies)
    
    def onConnectionChanged(self, selector, srcPlug, dstPlug, made):
        for strategy in self._strategies:
            if selector.isDirty():
                return
            strategy.onConnectionChanged(selector, srcPlug, dstPlug, made)
    
    def isTraversingConnections(self):
        return reduce(lambda isTraversing, strategy: isTraversing or strategy.isTraversingConnections(), self._strategies, False)

class SimpleSelector(Selector):
    '''Selector node with both dynamic wildcard-based selection and static
       list of names selection.
       
       Output is the union of both selections (dynamic and static).'''
    
    kTypeId = typeIDs.simpleSelector
    kTypeName = 'simpleSelector'

    # Attributes
    aPattern           = OpenMaya.MObject()  # Pattern for dynamic selection.
    aStaticSelection   = OpenMaya.MObject()  # Static list of node names.
    aTypeFilter        = OpenMaya.MObject()  # typeFilter as attribute
    aCustomFilterValue = OpenMaya.MObject()  # custom filter value as attribute

    @classmethod
    def getDefaultFilter(cls):
        return Filters.kTransforms
    
    @classmethod
    def getAvailableFilters(cls):
        return Filters._allTypes
        
    def contentType(self):
        filterType = self.getFilterType()
        if filterType == Filters.kAll:
            return Selector.kDagOrNonDag
        if filterType in Filters._dagTypes:
            return Selector.kDagOnly 
        if filterType != Filters.kCustom:
            return Selector.kNonDagOnly
        customs = filter(lambda t: not t.startswith('-'), self.getTypeFilters())
        if len(customs) == 0:
            return Selector.kDagOrNonDag
        dags = filter(lambda t: 'dagNode' in cmds.nodeType(t, isTypeName=True, inherited=True), customs)
        return { 0            : Selector.kNonDagOnly, 
                 len(customs) : Selector.kDagOnly     }.get(len(dags),Selector.kDagOrNonDag)
    
    def isAbstractClass(self):
        return False
    
    def isTraversingConnections(self):
        '''Returns True if this selector traverses connections to populate its content, False otherwise.'''
        return False if self.parent() is None else self.strategy().isTraversingConnections()
    
    @classmethod
    def initializer(cls):
        cls.inheritAttributesFrom(Selector.kTypeName)

        default = OpenMaya.MFnStringData().create('')
        attr = OpenMaya.MFnTypedAttribute()
        cls.aPattern = cls.createInput(attr,["pattern", "pat", OpenMaya.MFnData.kString, default])
        cls.aStaticSelection = cls.createInput(attr, ["staticSelection", "ssl", OpenMaya.MFnData.kString, default])
        cls.aCustomFilterValue = cls.createInput(attr, ["customFilterValue", "cfv", OpenMaya.MFnData.kString, default])
        
        attr = OpenMaya.MFnEnumAttribute()
        cls.aTypeFilter = cls.createInput(attr, ["typeFilter", "tf", cls.getDefaultFilter()])
        for ftype in cls.getAvailableFilters():
            attr.addField(Filters.filterName(ftype), ftype)
        
        for attr in [cls.aPattern, cls.aStaticSelection, cls.aTypeFilter, cls.aCustomFilterValue]:
            cls.addAttribute(attr)
            cls.affectsOutput(attr)

    def __init__(self):
        super(SimpleSelector, self).__init__()
        self._staticSelection = StaticSelection(self)
        self._activated = False
        self._strategy = None
        self._staticCache = set()
        self._dynamicCache = set()
        self._cache = set()
    
    # CALLBACKS
    # TODO optimize pattern check
    def onNodeAdded(self, obj):
        if self.staticSelection.onNodeAdded(obj) or \
            not self.isDirty() and len(self.patterns()) > 0 and self.acceptsType(OpenMaya.MFnDependencyNode(obj).typeName):
            self.selectionChanged()
        
    def onNodeRenamed(self, obj, oldName):
        if self.staticSelection.onNodeRenamed(obj, oldName) or \
            not self.isDirty() and len(self.patterns()) > 0 and self.acceptsType(OpenMaya.MFnDependencyNode(obj).typeName):
            self.selectionChanged()
        
    def onNodeRemoved(self, obj):
        if self.staticSelection.onNodeRemoved(obj) or \
            not self.isDirty() and len(self.patterns()) > 0 and self.acceptsType(OpenMaya.MFnDependencyNode(obj).typeName):
            self.selectionChanged()
        
    def onNodeReparented(self, msgType, child, parent):
        if self.staticSelection.onNodeReparented(msgType, child, parent) or \
            not self.isDirty() and (len(self.patterns()) > 0 or self.parent()) and self.hasDagNodes():
            self.selectionChanged()
    
    def onReferenceLoaded(self, referenceNode, resolvedRefPath):
        self.staticSelection.dirtyMissingCB()
        if not self.isDirty():
            self.selectionChanged()
    
    def onReferenceUnloaded(self, referenceNode, resolvedRefPath):
        self.staticSelection.dirtyMissingCB()
        if not self.isDirty():
            self.selectionChanged()
        
    def onConnectionChanged(self, srcPlug, dstPlug, made):
        if not self.isDirty() and self.parent():
            self.strategy().onConnectionChanged(self, srcPlug, dstPlug, made)
    
    def _filtersChanged(self):
        self.staticSelection.dirtyFilterCB()
        self._strategy = None
        self.selectionChanged()
    
    def _patternChanged(self):
        self.selectionChanged()
    
    def _staticSelectionChanged(self):
        self.staticSelection.dirtySelectionCB()
        self.selectionChanged()

    # ACCESSORS / MUTATORS / QUERIES
    def _getInputAttr(self, attr, dataBlock=None):
        return dataBlock.inputValue(attr) if dataBlock else OpenMaya.MPlug(self.thisMObject(), attr)
    
    def isEmpty(self):
        return len(self.getPattern()) == 0 and len(self.staticSelection) == 0
    
    def getPattern(self, dataBlock=None):
        return self._getInputAttr(self.aPattern, dataBlock).asString()
    
    def setPattern(self, val):
        if val != self.getPattern():
            with undo.NotifyCtxMgr(kSet % (self.name(), 'pattern', val), self._patternChanged):
                cmds.setAttr(self.name() + '.pattern', val, type='string')

    def getFilterType(self, dataBlock=None):
        return self._getInputAttr(self.aTypeFilter, dataBlock).asShort()

    def setFilterType(self, val):
        if val not in self.getAvailableFilters():
            cmds.warning(maya.stringTable['y_selector.kInvalidTypeFilter' ] % (self.name(), Filters.filterUIName(val)))
            return
        if val != self.getFilterType():
            with undo.NotifyCtxMgr(kSet % (self.name(), 'typeFilter', val), self._filtersChanged):
                cmds.setAttr(self.name() + '.typeFilter', val)

    def getCustomFilterValue(self, dataBlock=None):
        return self._getInputAttr(self.aCustomFilterValue, dataBlock).asString()

    def setCustomFilterValue(self, val):
        if val != self.getCustomFilterValue():
            with undo.NotifyCtxMgr(kSet % (self.name(), 'customFilterValue', val), self._filtersChanged):
                cmds.setAttr(self.name() + '.customFilterValue', val, type='string')
    
    def patterns(self, dataBlock=None):
        return filter(None, re.split(r';|,|\s', self.getPattern(dataBlock)))
    
    def getTypeFilters(self, dataBlock=None):
        type = self.getFilterType(dataBlock)
        if type != Filters.kCustom:
            return Filters.filterTypes(type)
        filters = itertools.ifilter(None, re.split(r';|,|\s', self.getCustomFilterValue(dataBlock)))
        def expand(f):
            '''If f is a classification string, expands it to an iterable of node types satifying that classification.
               If f is already a valid node type, simply returns it in a tuple.
               Otherwise, returns an empty tuple.'''
            negate = f.startswith('-')
            if negate: f = f[1:]
            types = cmds.listNodeTypes(f) or ((f,) if utils.isExistingType(f) else ())
            if negate: types = itertools.imap(lambda t: "-"+t, types)
            return types
        return list(itertools.chain.from_iterable(expand(f) for f in filters))
    
    @property
    def staticSelection(self):
        return self._staticSelection

    def _setStaticSelectionString(self, string):
        with undo.NotifyCtxMgr(kSet % (self.name(), 'staticSelection', string), self._staticSelectionChanged):
            cmds.setAttr(self.name() + '.staticSelection', string, type='string')
    
    def _getStaticSelectionString(self):
        return OpenMaya.MPlug(self.thisMObject(), self.aStaticSelection).asString()
    
    def minimalClone(self, other):
        filterType = other.getFilterType()
        self.setFilterType(filterType)
        if filterType == Filters.kCustom:
            self.setCustomFilterValue(other.getCustomFilterValue)

    def strategy(self, dataBlock=None):
        if dataBlock or not self._strategy:
            filterType = self.getFilterType(dataBlock)
            customs = self.getTypeFilters() if filterType==Filters.kCustom else []
            strategies = filter(None, (cls.create(filterType, customs) for cls in [DagStrategy, ShadingStrategy, ShadingEngineStrategy, GeneratorStrategy, SetStrategy]))
            self._strategy = strategies[0] if len(strategies)==1 else CompositeStrategy(strategies)
        return self._strategy

    def acceptsType(self, typeName, dataBlock=None):
        if self.getFilterType(dataBlock) == Filters.kShaders:
            return utils.isSurfaceShaderType(typeName)
        includes = filter(lambda t: not t.startswith('-'), self.getTypeFilters(dataBlock))
        if len(includes) == 0:
            return True
        try: parents = set(cmds.nodeType(typeName, inherited=True, isTypeName=True) or ())
        except: return False # typeName doesn't exist
        for typeName in includes:
            if typeName in parents:
                return True
        return False

    def _update(self, dataBlock):
        return self._updateFromWorld(dataBlock) if not self.parent() else \
            self._updateFromSelection(dataBlock, Selection(self.strategy(dataBlock).items(self.parent().selection())))

    def _updateStaticSelection(self, dataBlock):
        # compute static selection
        self.staticSelection.setCache(dataBlock.inputValue(self.aStaticSelection).asString())
        filterType = self.getFilterType(dataBlock)
        filterFunc = Filters.filterFunction(filterType) if filterType != Filters.kCustom else \
                    createCustomFilter(self.getCustomFilterValue(dataBlock))
        return itertools.ifilter(filterFunc, (name for name in self.staticSelection if cmds.objExists(name)))

    def _updateDynamicSelection(self, dataBlock):
        # compute dynamic selection
        return ls(self.patterns(dataBlock), types=self.getTypeFilters(dataBlock))
        
    def _updateFromWorld(self, dataBlock):
        self._staticCache  = set(self._updateStaticSelection(dataBlock))
        self._dynamicCache = set(self._updateDynamicSelection(dataBlock))
        self._cache = self._staticCache | self._dynamicCache
    
    def _updateFromSelection(self, dataBlock, selection):
        # compute static selection
        self._staticCache = set(itertools.ifilter(lambda n: n in selection, self._updateStaticSelection(dataBlock)))
        
        # compute dynamic selection
        names = selection.ls(self.patterns(dataBlock))
        if self.getFilterType(dataBlock) == Filters.kCustom:
            typeFilter = createCustomFilter(self.getCustomFilterValue(dataBlock))
            names = itertools.ifilter(typeFilter, names)
        elif self.getFilterType(dataBlock) == Filters.kAll:
            names = itertools.ifilter(Filters.filterFunction(Filters.kAll), names)
        self._dynamicCache = set(names)
        
        self._cache = self._dynamicCache | self._staticCache
    
    def selection(self):
        names = self.names()
        if not self._selection:
            self._selection = Selection(names)
        return self._selection
    
    @Selector.synced
    def paths(self):
        return (DagPath(p) for p in self.selection().paths())
        
    @Selector.synced
    def shapes(self):
        return (DagPath(p) for p in self.selection().shapes())
    
    @Selector.synced
    def nodes(self):
        return self.selection().nodes()
    
    @Selector.synced
    def names(self):
        return self._cache
    
    @Selector.synced
    def getStaticNames(self):
        return self._staticCache
    
    @Selector.synced
    def getDynamicNames(self):
        return self._dynamicCache
    
    def getInvalidFilters(self, dataBlock=None):
        return [] if self.getFilterType(dataBlock) != Filters.kCustom else \
            filter(lambda t: not utils.isExistingType(t) and not utils.isExistingClassification(t), # test validity
                itertools.imap(lambda t: t[1:] if t.startswith('-') else t, # remove heading '-'
                    itertools.ifilter(None, re.split(r';|,|\s', self.getCustomFilterValue(dataBlock))))) # get custom filters
    
    def status(self, dataBlock=None):
        invalidFilters = self.getInvalidFilters(dataBlock)
        if len(invalidFilters) > 0:
            return maya.stringTable['y_selector.kInvalidTypes' ] % ' '.join(invalidFilters)
        if self.staticSelection.hasMissingObjects():
            return kHasMissingObjects
        return None
            
    def setStaticSelection(self, ss):
        """Deprecated method.

        Use methods on SimpleSelector.staticSelection instead."""

        return self.staticSelection._setStr(ss)
    
    def getStaticSelection(self):
        """Deprecated method.

        Use methods on SimpleSelector.staticSelection instead."""

        return self.staticSelection._getStr()
        
    def hasMissingObjects(self):
        return self.staticSelection.hasMissingObjects()
    
    def hasFilteredOutObjects(self):
        return self.staticSelection.hasFilteredOutObjects()
        
    def _encodeProperties(self, dict):
        encoders = (
            (self.aPattern,           self.getPattern),
            (self.aStaticSelection,   self.staticSelection.encode),
            (self.aTypeFilter,        self.getFilterType),
            (self.aCustomFilterValue, self.getCustomFilterValue))
        for attr, encode in encoders:
            dict[OpenMaya.MPlug(self.thisMObject(), attr).partialName(useLongNames=True)] = encode()
        
    def _decodeProperties(self, dict):
        decoders = (
            (self.aPattern,           self.setPattern),
            (self.aStaticSelection,   self.staticSelection.decode),
            (self.aTypeFilter,        self.setFilterType),
            (self.aCustomFilterValue, self.setCustomFilterValue))
        for attr, decode in decoders:
            name = OpenMaya.MPlug(self.thisMObject(), attr).partialName(useLongNames=True)
            if name in dict:
                decode(dict[name])

class BasicSelector(SimpleSelector):
    
    kTypeId = typeIDs.basicSelector
    kTypeName = 'basicSelector'
    
    aIncludeHierarchy = OpenMaya.MObject()
    
    # 2016 May 24, this is used only for backward compatibility in the tests
    # basic selector are no longer supported in Maya 2017 => they should gather no nodes
    # they need to be converted in Maya 2017 (see conversion.py)
    # use force compute = true in the tests until we translate them all to use the new selectors
    kForceCompute = False
    
    @classmethod
    def getDefaultFilter(cls):
        return Filters.kAll
    
    @classmethod
    def getAvailableFilters(cls):
        return list(Filters._allTypes) + [Filters.kTransformsAndShapes, Filters.kTransformsShapesShaders]

    @classmethod
    def initializer(cls):
        super(BasicSelector, cls).initializer()
        attr = OpenMaya.MFnNumericAttribute()
        cls.aIncludeHierarchy = cls.createInput(attr, ("includeHierarchy", "ih", OpenMaya.MFnNumericData.kBoolean, True))
        cls.addAttribute(cls.aIncludeHierarchy)
        cls.affectsOutput(cls.aIncludeHierarchy)
        
    def isAbstractClass(self):
        return False
    
    def status(self):
        from maya.app.renderSetup.model.conversion import kIssueShortDescription
        return super(BasicSelector, self).status() if self.kForceCompute else kIssueShortDescription
    
    @Selector.synced
    def shapes(self):
        paths = filter(None, (DagPath.create(name) for name in self._cache))
        return (p for p in paths if p.node().hasFn(OpenMaya.MFn.kShape))

    @staticmethod
    def _findHierarchy(names):
        # get dag paths + dag hierarchy
        def addRelatives(selection, parent):
            selection.update(cmds.listRelatives(parent, allDescendents=True, fullPath=True) or ())
            return selection
        parents   = set(name for name in names if name.startswith('|'))
        children = reduce(addRelatives, parents, set())
        dagPaths = [DagPath.create(name) for name in set(parents)|set(children)]
        # find shading nodes from dag paths
        engines = list(ShadingEngineStrategy._findShadingEngines(dagPaths))
        shadingNodes = algorithm.traverse(
            itertools.chain(
                ShadingStrategy._findSurfaceShaders(engines),
                ShadingStrategy._findDisplacementShaders(engines),
                ShadingStrategy._findVolumeShaders(engines)),
            predicate=utils.isShadingNode)
        # find generators from dag paths
        generators = GeneratorStrategy._findGeometryGenerators(dagPaths)
        objs = itertools.chain(engines, shadingNodes, generators)
        return itertools.chain(children, (OpenMaya.MFnDependencyNode(o).name() for o in objs))
    
    def _update(self, dataBlock):
        if not self.kForceCompute:
            self._cache = self._staticCache = self._dynamicCache = set()
            return
        self.staticSelection.setCache(dataBlock.inputValue(self.aStaticSelection).asString())
        self._staticCache = set(itertools.ifilter(cmds.objExists, self.staticSelection.asList()))
        self._dynamicCache = ls(self.patterns())
        
        if dataBlock.inputValue(self.aIncludeHierarchy).asBool():
            self._staticCache.update(BasicSelector._findHierarchy(self._staticCache))
            self._dynamicCache.update(BasicSelector._findHierarchy(self._dynamicCache))
        
        # must do post filtering because of include hierarchy
        # with basic selector, static selection is also filtered...
        types = self.getTypeFilters(dataBlock)
        if len(types) > 0:
            filterFunction = createTypeFilter(types)
            self._staticCache = set(itertools.ifilter(filterFunction, self._staticCache))
            self._dynamicCache = set(itertools.ifilter(filterFunction, self._dynamicCache))
        
        parent = self.parent()
        if parent:
            self._staticCache.intersection_update(parent.names())
            self._dynamicCache.intersection_update(parent.names())
        
        self._cache = self._staticCache | self._dynamicCache
        
    def getIncludeHierarchy(self):
        return OpenMaya.MPlug(self.thisMObject(), self.aIncludeHierarchy).asBool()
        
    def setIncludeHierarchy(self,val):
        cmds.setAttr(self.name()+".includeHierarchy", val)
        
    def _encodeProperties(self, dict):
        super(BasicSelector, self)._encodeProperties(dict)
        encoders = [(self.aIncludeHierarchy,  self.getIncludeHierarchy)]
        for attr, encode in encoders:
            dict[OpenMaya.MPlug(self.thisMObject(), attr).partialName(useLongNames=True)] = encode()
        
    def _decodeProperties(self, dict):
        super(BasicSelector, self)._decodeProperties(dict)
        decoders = [(self.aIncludeHierarchy,  self.setIncludeHierarchy)]
        for attr, decode in decoders:
            name = OpenMaya.MPlug(self.thisMObject(), attr).partialName(useLongNames=True)
            if name in dict:
                decode(dict[name])
    
    def onNodeAdded(self, **kwargs):
        super(BasicSelector, self).onNodeAdded(**kwargs)
        if not self.isDirty() and self.getIncludeHierarchy():
            self.selectionChanged()
    
    def onNodeRemoved(self, **kwargs):
        super(BasicSelector, self).onNodeRemoved(**kwargs)
        if not self.isDirty() and self.getIncludeHierarchy():
            self.selectionChanged()
    
    def onNodeRenamed(self, **kwargs):
        super(BasicSelector, self).onNodeRenamed(**kwargs)
        if not self.isDirty() and self.getIncludeHierarchy():
            self.selectionChanged()
    
    def onNodeReparented(self, **kwargs):
        super(BasicSelector, self).onNodeReparented(**kwargs)
        if not self.isDirty() and self.getIncludeHierarchy():
            self.selectionChanged()
    
    def onConnectionChanged(self, **kwargs):
        if self.getIncludeHierarchy():
            self.selectionChanged()


def create(name, typeid):
    fn = OpenMaya.MFnDependencyNode()
    obj = fn.create(typeid, name)
    return fn.userNode()
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
