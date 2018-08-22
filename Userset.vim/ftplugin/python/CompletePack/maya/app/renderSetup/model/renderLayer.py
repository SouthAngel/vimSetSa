""" Render layer node class and utility functions.

    This module provides the render layer class, as well as utility
    functions to operate on render layers.
   

    Note:
        In order to better control the update of the render layer, two flags were added 
        to each render layer instance to control the update of 1) the list of nodes owned
        by the legacy layer and 2) the rendering. The controls were introduced to avoid
        performance penalty on any user requests.
        
        The flag RenderLayer.needsMembershipUpdate is set to True when the list of nodes 
        part of the render layer changed meaning that the legacy layer must be updated. 
        The update is managed by an evalDeferred() so it will only be executed during 
        the next idle time. If an update is already planned, 
        the flag RenderLayer.isUpdatingMembership will be True. These flags only apply
        to the visible render layer. No updates are performed on the not visible ones.
        
        The flag RenderLayer.needsApplyUpdate is set to True when the rendering must be updated. 
        The default dirty mechanism of the scene is not enough as the render setup behavior implies
        to sometime apply or unapply some overrides. The first 'not optimized' implementation 
        of the rendering refresh is to impose a switchToLayer() 
        (i.e. unapply and apply all overrides). This flag only applies to the visible render layer. 
        No updates are performed on the not visible ones.
   
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya

import maya.app.renderSetup.model.nodeList as nodeList
import maya.app.renderSetup.model.utils as utils
import maya.app.renderSetup.common.utils as commonUtils
import maya.app.renderSetup.model.typeIDs as typeIDs
import maya.app.renderSetup.model.collection as collection
import maya.app.renderSetup.model.selector as selector
import maya.app.renderSetup.model.undo as undo
import maya.app.renderSetup.model.legacyRenderLayer as legacyLayer
import maya.app.renderSetup.model.childNode as childNode
import maya.app.renderSetup.model.overrideManager as overrideManager
import maya.app.renderSetup.model.rendererCallbacks as rendererCallbacks
import maya.app.renderSetup.model.traverse as traverse
import maya.app.renderSetup.model.enabled as enabled
import maya.app.renderSetup.model.memberSet as memberSet
from maya.app.renderSetup.model.renderLayerSwitchObservable import RenderLayerSwitchObservable

import maya.app.renderSetup.common.profiler as profiler
import maya.app.renderSetup.common.guard as guard
import maya.app.renderSetup.model.namespace as namespace
import maya.app.renderSetup.model.context as context

import maya.app.renderSetup.model.jsonTranslatorUtils as jsonTranslatorUtils
import maya.app.renderSetup.model.jsonTranslatorGlobals as jsonTranslatorGlobals
from maya.app.renderSetup.model.observable import Observable
from functools import partial
import itertools

from maya.app.renderSetup.model.renderSetupPrivate import PostApplyCmd


# List all error messages
kInvalidCollectionName = maya.stringTable['y_renderLayer.kInvalidCollectionName' ]
kUnknownCollection     = maya.stringTable['y_renderLayer.kUnknownCollection'     ]
kCollectionUnicity     = maya.stringTable['y_renderLayer.kCollectionUnicity'     ]

# List of undo messages
kAttachCollection              = maya.stringTable['y_renderLayer.kAttachCollection'               ]
kCreateLightsCollection        = maya.stringTable['y_renderLayer.kCreateLightsCollection'         ]
kCreateRenderSettingsCollection= maya.stringTable['y_renderLayer.kCreateRenderSettingsCollection' ]
kCreateAOVCollection           = maya.stringTable['y_renderLayer.kCreateAOVCollection'            ]
kCreateAOVChildCollection      = maya.stringTable['y_renderLayer.kCreateAOVChildCollection'       ]
kSetRenderability              = maya.stringTable['y_renderLayer.kSetRenderability'               ]
kCollectionDetached            = maya.stringTable['y_renderLayer.kCollectionDetached'             ]
kCollectionAttached            = maya.stringTable['y_renderLayer.kCollectionAttached'             ]

def memberTraversal(node):
    """Traverse render setup node children to determine layer membership.

    During the collection traversal to determine membership, we consider
    the isolate select state of the layer and of collections, and prune
    those collections that are not included by isolate select.

    If the node has no children, an empty list is returned."""

    # If the node has no children, return an empty list.
    if not isinstance(node, nodeList.ListBase):
        return []

    # If the node is not a collection, return its children.
    if not isinstance(node, collection.Collection):
        return nodeList.forwardListGenerator(node)

    # The node is a collection.  If it's disabled, return an empty list, else
    # return its children.
    return node.getCollections() if node.isEnabled() else []

def _syncLegacyRenderLayers(layerName):
    # Suspend and resume undo logging around this callback
    # It will be called for any changes to the data model as well as the undo of any changes so
    # it does not need to handle undo itself.
    with undo.SuspendUndo():
        # Update visibility as required
        import maya.app.renderSetup.model.renderSetup as renderSetupModel

        # Make sure the render setup system is still in use
        # This function is called deferred and the system might have been
        # shut down before we reach this point
        if not renderSetupModel.hasInstance():
            return

        renderLayers = renderSetupModel.instance().getRenderLayers()
        for renderLayer in renderLayers:
            # When called during a file reference load / unload, node names
            # are surprisingly returned as absolute names, qualified with a
            # leading colon.  Make sure name matching handles this.
            if renderLayer.name().lstrip(':') == layerName.lstrip(':') \
               and renderLayer.isVisible():
                renderLayer._updateLegacyRenderLayerVisibility()
                break

class RenderLayerBase(object):
    """Abstract base class for RenderLayer and DefaultRenderLayer classes
       Defines functions for toggling visibility and renderability.
       Children must implement:
         - _getLegacyNodeName()
         - _updateLegacyRenderLayerVisibility()
         - apply()
         - unapply()
    """

    def __init__(self):
        super(RenderLayerBase, self).__init__()
        self.needsApplyUpdate = False

    def isRenderable(self):
        return legacyLayer.isRenderable(self._getLegacyNodeName())

    def setRenderable(self, value):
        if value != self.isRenderable():
            with undo.NotifyCtxMgr(kSetRenderability % (self.name(), value), self.itemChanged):
                legacyLayer.setRenderable(self._getLegacyNodeName(), value)
  
    def isVisible(self):
        return legacyLayer.isVisible(self._getLegacyNodeName())

    def makeVisible(self):
        # do not call this function directly
        # use renderSetup.switchToLayer(layer) instead
        if not self.isVisible():
            return legacyLayer.makeVisible(self._getLegacyNodeName())


class DefaultRenderLayer(RenderLayerBase, Observable):
    """Singleton class to access and modify default render layer properties
       This singleton instance is also observable: it will notify observers
       on visibility and renderability changes.

       Singleton instance belongs to renderSetup instance
       Access it using renderSetup.instance().getDefaultRenderLayer()
    """

    def __init__(self):
        super(DefaultRenderLayer, self).__init__()

    def name(self):
        return 'defaultRenderLayer'

    def _getLegacyNodeName(self):
        return 'defaultRenderLayer'

    def hasLightsCollectionInstance(self):
        return False

    def needsRefresh(self):
        return False

    def clearMemberNodesCache(self):
        pass

    def setMemberNodesCache(self, cache):
        pass

    def getMemberNodesCache(self):
        return []

    # default render layer always contains everything in the scene
    # nothing to do in the next three functions
    # but they need to exist as they may be called when switching visible layer
    def _updateLegacyRenderLayerVisibility(self):
        pass
    def apply(self):
        pass
    def unapply(self):
        pass

class RenderLayer(RenderLayerBase, nodeList.ListBase, childNode.ChildNode):
    """
    Render layer node.
    
    A render layer has an ordered list of collections.  It can
    optionally have an ordered list of overrides."""

    kTypeId = typeIDs.renderLayer
    # Can't use 'renderLayer', as it is the type name of the Maya 2016 and
    # earlier render layers.
    kTypeName = 'renderSetupLayer'

    # Attributes for render layer as list of collections.
    # 
    # Connections to lowest-priority and highest-priority collections
    # on collection linked list.  The lowest-priority collection
    # is considered to be the front of the list, and the highest-priority
    # collection the back of the list.
    collectionLowest  = OpenMaya.MObject()
    collectionHighest = OpenMaya.MObject()
    
    # Connection to all collections in the list.
    collections = OpenMaya.MObject()

    # Attribute for the connection to the legacy render layer
    legacyRenderLayer = OpenMaya.MObject()

    # The number of children collections that are isolate selected in the
    # layer, including nested collections.
    numIsolatedChildren = OpenMaya.MObject()
    
    @staticmethod
    def creator():
        return RenderLayer()

    @staticmethod
    def initializer():
        
        # A render layer is a render setup list element.
        # inheritAttributesFrom() must be called before adding any other
        # attributes.
        RenderLayer.inheritAttributesFrom(nodeList.ListItem.kTypeName)

        # A render layer is a list of collections.
        RenderLayer.collections = RenderLayer.initListItems()

        RenderLayer.collectionLowest = utils.createDstMsgAttr(
            'collectionLowest', 'cl')
        RenderLayer.addAttribute(RenderLayer.collectionLowest)

        RenderLayer.collectionHighest = utils.createDstMsgAttr(
            'collectionHighest', 'ch')
        RenderLayer.addAttribute(RenderLayer.collectionHighest)

        RenderLayer.legacyRenderLayer = utils.createDstMsgAttr(
            'legacyRenderLayer', 'lrl')
        RenderLayer.addAttribute(RenderLayer.legacyRenderLayer)

        # Add isolateSelected attribute
        RenderLayer.numIsolatedChildren = enabled.createNumIsolatedChildrenAttribute()
        RenderLayer.addAttribute(RenderLayer.numIsolatedChildren)

    def __init__(self):
        super(RenderLayer, self).__init__()
        self._currentlyVisibleNodeNames = set()
        self.isUpdatingMembership = False
        self.needsMembershipUpdate = False
    
    def postConstructor(self):
        overrideManager.postConstructor(self)

    def needsRefresh(self):
        ''' Following some changes the instance must be updated. '''
        # membership is always up to date since startMembershipUpdate 
        # is called when collection change their content.
        return self.needsApplyUpdate

    def typeId(self):
        return RenderLayer.kTypeId

    def typeName(self):
        return RenderLayer.kTypeName

    def _getLegacyNodeName(self):
        return utils.getSrcNodeName(utils.findPlug(self, RenderLayer.legacyRenderLayer))

    def _getNumIsolatedChildrenPlug(self):
        return OpenMaya.MPlug(self.thisMObject(), RenderLayer.numIsolatedChildren)

    def getNumIsolatedChildren(self):
        return self._getNumIsolatedChildrenPlug().asInt()

    def clearMemberNodesCache(self):
        # Under a file reference unload / reload, the list of render layer
        # member nodes does not change, and will still match the render
        # layer node cache, but the unload / reload will have cleared out
        # the actual legacy render layer membership connections.  In such a
        # case, clear out the cache, which causes
        # _updateLegacyRenderLayerVisibility() to update the legacy render
        # layer membership.
        self._currentlyVisibleNodeNames = []

    def setMemberNodesCache(self, cache):
        self._currentlyVisibleNodeNames = cache

    def getMemberNodesCache(self):
        return self._currentlyVisibleNodeNames

    @guard.state(OpenMaya.MFnReference.ignoreReferenceEdits, OpenMaya.MFnReference.setIgnoreReferenceEdits, True)
    @undo.chunk('Update legacy render layer members')
    def _updateLegacyRenderLayerVisibility(self):
        """ Update layer visibility. Note that we always edit layer member
            to maintain consistency and let the update logic optimize as needed for performance.
            For instance, VP2 will not update its scene representation for invisible layers.
        """
        # Note: deltas are not being computed yet so we are
        #  doing a reset on the associated old render layer for now.
        #
        # Note: Still no delta computation but at least there is no processing
        #  if the list of selected nodes did not changed.        
        try:
            with profiler.ProfilerMgr('RenderLayer::_updateLegacyRenderLayerVisibility'):
                currentlySelectedNodeNames = self.getMembers()
                if currentlySelectedNodeNames!=self._currentlyVisibleNodeNames:
                    legacyRenderLayerName = self._getLegacyNodeName()
                    # Clear out old membership
                    legacyLayer.removeNodes(legacyRenderLayerName)
                    # Add in nodes from enabled collections only
                    legacyLayer.appendNodes(legacyRenderLayerName, currentlySelectedNodeNames)
                    # Preserve the new list of nodes
                    self.setMemberNodesCache(currentlySelectedNodeNames)
            self.needsMembershipUpdate = False
            self.itemChanged()
        
        finally:
            self.isUpdatingMembership = False
    
    @guard.state(OpenMaya.MFnReference.ignoreReferenceEdits, OpenMaya.MFnReference.setIgnoreReferenceEdits, True)
    def addDefaultMembers(self, objs):
        # layer members can only be dag nodes
        paths = [OpenMaya.MFnDagNode(obj).getPath() for obj in objs]
        if self.isVisible():
            # add nodes to legacy layer now to make them visible right away
            legacyLayer.appendNodes(self._getLegacyNodeName(), [path.fullPathName() for path in paths])
            self._currentlyVisibleNodeNames.update(path.fullPathName() for path in paths)
        self.getDefaultCollection().getSelector().staticSelection.add(paths)
    
    def _startMembershipUpdate(self):
        if not self.isUpdatingMembership:
            self.isUpdatingMembership = True
            pythonCmd = "import maya.app.renderSetup.model.renderLayer as layer; layer._syncLegacyRenderLayers('{0}')".format(self.name())
            cmds.evalDeferred(pythonCmd)
    
    def _visible(f):
        '''Decorator that will call decorated function only if the layer (self, first argument) is visible.'''
        def wrapper(*args, **kwargs):
            if args[0].isVisible(): # args[0] = self
                return f(*args, **kwargs)
        return wrapper
    
    @_visible
    def descendantAdded(self, child):
        '''If the layer is currently visible and a descendant is added (collection or override), apply it right away.'''
        PostApplyCmd.execute(child)
    
    @_visible
    def _enabledChanged(self, collection):
        self.needsMembershipUpdate = self.needsMembershipUpdate or collection.getSelector().hasDagNodes()
        if self.needsMembershipUpdate:
            self._startMembershipUpdate()
        collection.pullEnabled()
    
    @_visible
    def _isolateSelectedChanged(self, collection):
        self.needsMembershipUpdate = True
        self._startMembershipUpdate()
        collection.pullEnabled()
    
    @_visible
    def _selectedNodesChanged(self, collection):
        """ Some attributes of this render layer or one of its children changed """
        self.needsMembershipUpdate = self.needsMembershipUpdate or collection.getSelector().hasDagNodes()
        if self.needsMembershipUpdate:
            self._startMembershipUpdate()
        # set needsApplyUpdate conservatively
        # - if the collection has children (overrides or collection) and the selection changed, then there might be objects in it that
        #   are not overridden by the overrides in that collection/subcollections, or objects that are still overridden but should no longer be.
        # - if the collection is traversing connections to populate itself, then reevaluating its content may give wrong results 
        #   as subsequent connection override may be applied and the scene is thus not in the state it would have been when sequentially
        #   applying collections/overrides on layer switch
        self.needsApplyUpdate = self.needsApplyUpdate or collection.hasChildren() or collection.getSelector().isTraversingConnections()

    @undo.chunk('Rename render layer')
    def setName(self, newName):
        oldName = self._getLegacyNodeName()

        super(RenderLayer, self).setName(newName)

        # Renaming the legacy render layer is not required, as we have a
        # connection to it, but it's very useful for maintainability to
        # preserve the association between the legacy render layer name and
        # the render layer name.
        #
        # Note: self.name() is used as newName could have needed to be 
        # renamed as it was a duplicate name.
        with namespace.RootNamespaceGuard():
            legacyLayer.rename(oldName, self.name())

    @undo.chunk('Create and append a collection')
    def createCollection(self, collectionName):
        """ Create and append a new Collection

            @type collectionName: string
            @param collectionName: Name of collection to create
        """
        with profiler.ProfilerMgr('createCollection'):
            c = collection.create(collectionName)
            self.appendCollection(c)
            # Note: No need to update visibility here since it's an empty collection
            # which will not modify membership. 
            return c

    def _collectionAttached(self, child):
        with undo.NotifyCtxMgr(kCollectionDetached % (self.name(), child.name()), 
                                partial(self._selectedNodesChanged, collection=child)):
            child._attach(self)
            self.descendantAdded(child)
        
    @undo.chunk('Append to layer')
    def appendCollection(self, child):
        """ Add a collection as the highest-priority render collection """
        nodeList.append(self, child)
        self._collectionAttached(child)

    def attachCollection(self, pos, child):
        """ Attach a collection at a specific position """
        
        # This method appends the child collection to the requested position 
        # with the exception of 'special' collections which have dedicated 
        # positions. The collection order should always be: 
        # 1) the RenderSettings collection, 
        # 2) the AOV collection, 
        # 3) the Lights collection, 
        # and finally any 'normal' collections.

        colNames = [collection.RenderSettingsCollection.kTypeName,
                    collection.AOVCollection.kTypeName,
                    collection.LightsCollection.kTypeName]

                    
        hasCol = [t for t in colNames if self._getNamedCollection(t) is not None]
        
        # Error if a special collection child is already created.
        if child.typeName() in hasCol:
            raise Exception(kCollectionUnicity % child.typeName())

        if child.typeName() not in colNames:
            # If child is not a special collection, insert it after all special
            # collections.
            pos = max(len(hasCol), pos)
        else:
            # If child is a special collection, insert it as soon as possible.
            pos = 0
            for colName in colNames:
                if child.typeName() == colName:
                    break
                else:
                    if colName in hasCol:
                        pos += 1

        with undo.CtxMgr(kAttachCollection % (child.name(), self.name(), pos)):
            nodeList.insert(self, pos, child)
            self._collectionAttached(child)

    @undo.chunk('Detach from layer')
    def detachCollection(self, child):
        """ Detach a collection whatever is its position
        """
        collection.unapply(child) # NoOp if not applied; otherwise commands are used
        with undo.NotifyCtxMgr(
                kCollectionDetached % (self.name(), child.name()), 
                partial(self._selectedNodesChanged, collection=child)):
            # Must perform detach operations before removing from list,
            # otherwise parenting information is gone.
            child._detach(self)
            nodeList.remove(self, child)

    def getCollections(self):
        """ Get list of all existing Collections """
        return list(nodeList.forwardListGenerator(self))

    def hasDefaultCollection(self):
        """ Get the default collection where newly created nodes are placed """
        defaultCollectionName = "_untitled_"
        for col in nodeList.forwardListGenerator(self):
            if col.name().startswith(defaultCollectionName):
                return True
        return False

    def getDefaultCollection(self):
        """ Get the default collection where newly created nodes are placed """
        defaultCollectionName = "_untitled_"
        for col in nodeList.forwardListGenerator(self):
            if col.name().startswith(defaultCollectionName):
                return col
        col = collection.create(defaultCollectionName)
        self.attachCollection(self.getFirstCollectionIndex(), col)
        return col
        
    def getCollectionByName(self, collectionName, nested=False):
        """ Look for an existing collection by name """
        if not collectionName:
            raise Exception(kInvalidCollectionName)

        for child in nodeList.forwardListGenerator(self):
            if child.name() == collectionName:
                return child
            elif nested and child.typeId() == typeIDs.collection:
                child2 = child.getCollectionByName(collectionName, True)
                if child2:
                    return child2

        raise Exception(kUnknownCollection % (collectionName, self.name()))
        
    # Unify interface with Collection
    appendChild = appendCollection
    attachChild = attachCollection
    detachChild = detachCollection
    getChildren = getCollections
        

    def hasCollection(self, collectionName):
        for collection in nodeList.forwardListGenerator(self):
            if collection.name() == collectionName:
                return True
        return False

    def _getTypedCollection(self, typeId):
        '''Get the first collection with the argument type ID.'''

        for col in nodeList.forwardListGenerator(self):
            if col.typeId() == typeId:
                return col
        return None

    def _getNamedCollection(self, typeName):
        '''Get the first collection with the argument type name.'''

        for col in nodeList.forwardListGenerator(self):
            if col.typeName() == typeName:
                return col
        return None

    def renderSettingsCollectionInstance(self):
        """ Get the render settings collection instance for this render layer,
            creating it if it doesn't exists. """

        # Check if we already have a render settings on the list
        # We can only have zero or one lights collections so pick the first
        # one we find. It is always among the first ones on the list so this 
        # search is quick.
        settings = self._getTypedCollection(collection.RenderSettingsCollection.kTypeId)
        if not settings:
            with undo.CtxMgr(kCreateRenderSettingsCollection % self.name()):
                # Create a new render settings collection and put it first in the list
                settings = collection.create("RenderSettingsCollection", collection.RenderSettingsCollection.kTypeId)
                self.attachCollection(0, settings)

        return settings

    def aovCollectionInstance(self):
        """ Get the AOV collection instance for this render layer,
            creating it if it doesn't exists as long as renderer 
            callbacks are registered for the current renderer. """

        # Check if we already have an AOV collection in the list
        # We can only have zero or one AOV collections so pick the first
        # one we find. It is always among the first ones on the list so this 
        # search is quick.
        aovCollection = self._getTypedCollection(collection.AOVCollection.kTypeId)
        if not aovCollection and not rendererCallbacks.getCallbacks(rendererCallbacks.CALLBACKS_TYPE_AOVS) is None:
            with undo.CtxMgr(kCreateAOVCollection % self.name()):
                # Create a new AOV collection and put it first in the list
                aovCollection = collection.create("AOVCollection", collection.AOVCollection.kTypeId)
                settings = self._getTypedCollection(collection.RenderSettingsCollection.kTypeId)
                self.attachCollection(0 if settings is None else 1, aovCollection)

        return aovCollection
    
        
    def lightsCollectionInstance(self):
        """ Get the lights collection instance for this render layer,
            creating it if it doesn't exists. """

        # Check if we already have a lights collection on the list
        # We can only have zero or one lights collections so pick the first
        # one we find. It is always among the first ones on the list so this 
        # search is quick.
        lights = self._getTypedCollection(collection.LightsCollection.kTypeId)
        if not lights:
            # Create a new light collection and put it first in the list
            with undo.CtxMgr(kCreateLightsCollection % self.name()):
                lights = collection.create("lightsCollection", collection.LightsCollection.kTypeId)
                settings = self._getTypedCollection(collection.RenderSettingsCollection.kTypeId)
                aovCollection = self._getTypedCollection(collection.AOVCollection.kTypeId)
                self.attachCollection(0 if settings is None and aovCollection is None else \
                                      2 if not settings is None and not aovCollection is None else 1, lights)

        return lights

    def hasLightsCollectionInstance(self):
        """ Returns True if this layer has the lights collection instance created. """
        return self._getTypedCollection(collection.LightsCollection.kTypeId) is not None

    def hasRenderSettingsCollectionInstance(self):
        """ Returns True if this layer has the render settings collection instance created. """
        return self._getTypedCollection(collection.RenderSettingsCollection.kTypeId) is not None

    def hasAOVCollectionInstance(self):
        """ Returns True if this layer has the AOV collection instance created. """
        return self._getTypedCollection(collection.AOVCollection.kTypeId) is not None

    def getFirstCollectionIndex(self):
        index = 1 if self.hasLightsCollectionInstance() else 0
        if self.hasRenderSettingsCollectionInstance():
            index += 1
        if self.hasAOVCollectionInstance():
            index += 1
        return index

    def getMembers(self):
        """ Get the names of the layer's DAG node members.

            The layer's members are DAG nodes selected by the layer's
            collections, based on whether a collection is enabled or solo'ed. 
            
            @rtype: list
            @return: list of node names. Empty if none found.
        """

        with profiler.ProfilerMgr('RenderLayer::getMembers'):

            # Collection membership has the following properties:
            #
            # o The union of top-level collection members defines the
            #   render layer membership.
            # o Sub-collections filter their parent's objects, so they are
            #   always subsets of their parents.
            # o Collections exclude objects when disabled, and include
            #   objects when enabled.
            # o Explicitly including / excluding a DAG parent
            #   includes / excludes its children.
            # o Collections are processed in depth-first order, lowest
            #   priority to highest priority.  Later, higher-priority
            #   collection exclusions or inclusions replace earlier,
            #   lower-priority ones.
            #
            # Collection membership is also determined by a collection's
            # isolate select boolean flag.  Conceptually, isolate select is
            # a mode where only isolate selected collections are considered
            # when determining render layer membership.  Isolate select
            # mode is on when one or more collections are isolate
            # selected.  Isolate select has the following additional
            # properties:
            # 
            # o All ancestor collections of an isolate selected collections
            #   are enabled.  They do not contribute to render layer
            #   membership, but their overrides will be applied.  This is
            #   to support use cases where ancestor collections modify a
            #   child collection's transform: keeping the ancestors of that
            #   child enabled keeps the parent transform of the child
            #   collection's objects unchanged.
            # o All descendant collections of an isolate selected
            #   collection are enabled, and contribute to render layer
            #   membership.  Conceptually, isolate selecting a collection
            #   includes that collection's subtree into the render layer.
            #
            # The algorithm for determining membership proceeds
            # sequentially on the depth-first ordering of collections,
            # adding in members from enabled collections, and excluding
            # members from disabled collections.
            #
            # There is one important complexity that stems from the fact
            # that setting a DAG parent as member implicitly makes its
            # children members as well.  If only a subset of its children
            # must be excluded, we cannot make the parent member of the
            # layer.

            members = memberSet.MemberSet()
            
            if not self.hasLightsCollectionInstance():
                lights = itertools.ifilter(None, (commonUtils.nameToDagPath(name) for name in cmds.ls(type=cmds.listNodeTypes('light'))))
                reduce(lambda memberset,path: members.include(path), lights, members)
            
            isolateSelectMode = not cmds.about(batch=True) and (self.getNumIsolatedChildren() > 0)
            
            for c in traverse.depthFirst(self, memberTraversal):
                if not isinstance(c, collection.Collection):
                    continue

                # In isolate select mode, if a collection isn't isolate selected and
                # has no isolate selected ancestors, it's ignored.
                hasNoIsolatedAncestors = (c.getNumIsolatedAncestors() == 0)
                if isolateSelectMode and not c.isIsolateSelected() and hasNoIsolatedAncestors and \
                    not isinstance(c, collection.LightsCollection) and not isinstance(c, collection.LightsChildCollection):
                    # Lights cannot be isolate selected.  The following ensures they're visible when other collections are isolate selected.  
                    # MAYA-70684: a more maintainable solution should be found.
                    continue

                # The collection selector has a cache, which will always be hit once on
                # layer switching (to apply overrides).  Therefore, there is no need to
                # cache or be lazy in accessing the collection's members.
                nodes = [n for n in c.getSelector().getAbsoluteNames() if n.startswith('|')]
                paths = itertools.ifilter(None, (commonUtils.nameToDagPath(path) for path in nodes)) 
                
                mtd = memberSet.MemberSet.include if c.isEnabled() else memberSet.MemberSet.exclude
                reduce(lambda memberset,path: mtd(members, path), paths, members)
            
            included = set(p.fullPathName() for p in members.paths())

            return included

    # Required for backward compatibility.
    getEnabledSelectedNodeNames = getMembers

    def findCollection(self, predicate, creator=None):
        '''Find the collection of this layer satisfying the predicate function or creates it
        with the creator function if not found and a creator function is specified.
        Function signatures are:
          predicate(collection): returns boolean.
          creator(void) : returns the created node.'''
        for col in self.getCollections():
            if predicate(col):
                return col
        if not creator:
            return None
        col = creator()
        self.appendCollection(col)
        return col
    
    def getCorrespondingCollection(self, nodeName, selectedCollectionName):
        """ 
            The behavior is to look for Render Settings attribute to add the override
            in the Render Settings collection if it exists, then to use the selected
            collection; otherwise, to create a new collection containing the override.
        """
        
        # Search if the node is part of the render settings node list
        if collection.RenderSettingsCollection.containsNodeName(nodeName):
            return self.renderSettingsCollectionInstance()

        # Search if the node is part of the AOV selector list
        if collection.AOVCollection.containsNodeName(nodeName):
            aovCol = self.aovCollectionInstance()
            # Look for a child collection whose selection contains the node            
            for childColl in aovCol.getCollections():
                if childColl and childColl.containsNodeName(nodeName):
                    return childColl
                    
            # If it doesn't exist, create a new child node
            with undo.CtxMgr(kCreateAOVChildCollection % self.name()):
                # Create a new AOV child collection and put it last in the list
                callbacks = rendererCallbacks.getCallbacks(rendererCallbacks.CALLBACKS_TYPE_AOVS)
                aovName = callbacks.getAOVName(nodeName)
                coll = collection.create(aovName, collection.AOVChildCollection.kTypeId, aovName=aovName)
                aovCol.appendChild(coll)
                return coll

        coll = self.getCollectionByName(selectedCollectionName, True) if selectedCollectionName else None
        if coll:
            return coll
        
        selectorType = selector.SimpleSelector.kTypeName
        filterType, customFilter = selector.Filters.getFiltersFor(cmds.objectType(nodeName))
        def predicate(col):
            sel = col.getSelector()
            return sel.kTypeName == selectorType and \
                sel.getPattern() == "" and \
                len(sel.staticSelection) == 1 and nodeName in sel.staticSelection and \
                sel.getFilterType() == filterType and \
                (filterType != selector.Filters.kCustom or sel.getCustomFilterValue() == customFilter)
        def creator():
            col = collection.create(nodeName+"_col")
            col.setSelectorType(selectorType)
            sel = col.getSelector()
            sel.staticSelection.set([nodeName])
            sel.setFilterType(filterType)
            sel.setCustomFilterValue(customFilter)
            return col
        return self.findCollection(predicate, creator)
    
    @undo.chunk('Create an absolute override')
    def createAbsoluteOverride(self, nodeName, attrName, collectionName=None):
        """ Add an absolute override to a collection """
        return self.getCorrespondingCollection(nodeName, collectionName).createAbsoluteOverride(nodeName, attrName)

    @undo.chunk('Create a relative override')
    def createRelativeOverride(self, nodeName, attrName, collectionName=None):
        """ Add a relative override to a collection """
        return self.getCorrespondingCollection(nodeName, collectionName).createRelativeOverride(nodeName, attrName)

    def getOverrides(self):
        return []

    def attachOverride(self, overrideName):
        pass

    def isAbstractClass(self):
        # Override method inherited from base class: not an abstract class.
        return False

    # Render setup hack for 2016_R2.  See MAYA-65530.
    @guard.environ('MAYA_RENDER_SETUP_OVERRIDE_CONNECTABLE', '1')
    @context.applyLayer
    def apply(self):
        """Apply overrides for all collections in this render layer."""
        with profiler.ProfilerMgr('RenderLayer::applyOverrides'):
            for col in nodeList.forwardListGenerator(self):
                col.apply()
                RenderLayerSwitchObservable.getInstance().notifyRenderLayerSwitchObserver()

        self.needsApplyUpdate = False

    # Render setup hack for 2016_R2.  See MAYA-65530.
    @guard.environ('MAYA_RENDER_SETUP_OVERRIDE_CONNECTABLE', '1')
    @context.unapplyLayer
    def unapply(self):
        """Unapply overrides for all collections in this render layer."""
        with profiler.ProfilerMgr('RenderLayer::unapplyOverrides'):
            for col in nodeList.reverseListGenerator(self):
                col.unapply()
                RenderLayerSwitchObservable.getInstance().notifyRenderLayerSwitchObserver()

        self.needsApplyUpdate = False

    # Render layer interface as list of collections.
    # These methods implement the list requirements for the nodeList module.
    #
    # The list front and back are destination plugs connected to the render
    # collection node's message plug (which is a source).
    def _getFrontAttr(self):
        return RenderLayer.collectionLowest

    def _getBackAttr(self):
        return RenderLayer.collectionHighest

    def _getListItemsAttr(self):
        return RenderLayer.collections

    def _preChildDelete(self, child):
        # Private interface for collection to inform its parent that it
        # is about to be deleted.  Here, we simply remove the collection
        # from our list.
        self.detachCollection(child)

    # The passed in value is an integer offset on the number of isolate
    # selected children in this layer.
    def _updateIsolateSelected(self, val):
        # Use a command to support the undo mechanism
        if val != 0:
            newVal = self._getNumIsolatedChildrenPlug().asInt() + val
            cmds.setAttr(self._getNumIsolatedChildrenPlug().name(), newVal)

    def _importCollection(self, collectionName, nodeType):
        """ Create a collection of given type. 

            Note: It should never be used outside the import/export context
        """
        if nodeType == collection.LightsCollection.kTypeName:
            return self.lightsCollectionInstance()
        elif nodeType == collection.RenderSettingsCollection.kTypeName:
            return self.renderSettingsCollectionInstance()
        elif nodeType == collection.AOVCollection.kTypeName:
            return self.aovCollectionInstance()
        else:
            return self.createCollection(collectionName)

    def _encodeProperties(self, dict):
        super(RenderLayer, self)._encodeProperties(dict)
        dict[jsonTranslatorGlobals.VISIBILITY_ATTRIBUTE_NAME] = self.isVisible()
        dict[jsonTranslatorGlobals.COLLECTIONS_ATTRIBUTE_NAME] = jsonTranslatorUtils.encodeObjectArray(self.getCollections())

    def _decodeChildren(self, children, mergeType, prependToName):
        jsonTranslatorUtils.decodeObjectArray(children, 
                                              jsonTranslatorUtils.MergePolicy(self.getCollectionByName, 
                                                                              self._importCollection, 
                                                                              mergeType, 
                                                                              prependToName))

    def _decodeProperties(self, dict, mergeType, prependToName):
        super(RenderLayer, self)._decodeProperties(dict, mergeType, prependToName)
        # Decode all attributes
        if jsonTranslatorGlobals.COLLECTIONS_ATTRIBUTE_NAME in dict:
            self._decodeChildren(dict[jsonTranslatorGlobals.COLLECTIONS_ATTRIBUTE_NAME],
                                 mergeType, 
                                 prependToName)
        # Note: Always be the last operation in order 
        #         to have completely decoded the layer before switching 
        #         in visible mode and so avoid too many notifications.
        if jsonTranslatorGlobals.VISIBILITY_ATTRIBUTE_NAME in dict \
                and dict[jsonTranslatorGlobals.VISIBILITY_ATTRIBUTE_NAME]==True:
            self.parent().switchToLayer(self)

    def acceptImport(self):
        super(RenderLayer, self).acceptImport()
        for collection in nodeList.forwardListGenerator(self):
            collection.acceptImport()

    def isAcceptableChild(self, modelOrData):
        """ Check if the model could be a child of the render layer model """
        typeName = modelOrData.typeName()
        return ((typeName == collection.LightsCollection.kTypeName and not self.hasLightsCollectionInstance()) or
                (typeName == collection.RenderSettingsCollection.kTypeName and not self.hasRenderSettingsCollectionInstance()) or
                (typeName == collection.AOVCollection.kTypeName and not self.hasAOVCollectionInstance())) or \
               typeName == collection.Collection.kTypeName
    
    def findIn(self, nodeNames, includeSelf=True):
        '''Generator that returns all the collections in that layer that contain at least on of the 
        object in nodeNames. Optionally also returns self (with includeSelf=True) if the object is in the layer.'''
        found = False
        for collection in utils.getCollectionsRecursive(self):
            if next((n for n in nodeNames if n in collection.getSelector().names()), False):
                found = True
                yield collection
        
        if includeSelf:
            if found:
                yield self
            elif not self.hasLightsCollectionInstance():
                lightTypes = cmds.listNodeTypes('light')
                def isLight(name):
                    return next((t for t in lightTypes if cmds.objectType(name, isAType=t)), False)
                if next((n for n in nodeNames if isLight(n)), False):
                    yield self

@undo.chunk('Create render layer')
@namespace.root
def create(name):
    """ Create a render layer.

    Returns the MPxNode object corresponding to the created render
    collection node.

    This function is undoable."""

    # Using existing command for undo / redo purposes, even if it requires
    # a name-based lookup to return the user node, since render layer
    # creation is not performance-critical.  If the name flag is specified,
    # it cannot be an empty string.
    renderLayerName = cmds.createNode(RenderLayer.kTypeName, name=name, skipSelect=True) if name \
                 else cmds.createNode(RenderLayer.kTypeName, skipSelect=True)

    renderLayer = utils.nameToUserNode(renderLayerName)

    # Second create the associated legacy render layer
    legacyRenderLayerName = legacyLayer.create(renderLayerName)

    # Third connect the render layer node to the legacy render layer node
    cmds.connectAttr(legacyRenderLayerName + '.msg', renderLayerName + '.lrl')

    return renderLayer

@undo.chunk('Delete render layer')
def delete(renderLayer):
    """Remove the argument render layer from the scene.

    All overrides and collections in the render layer are
    removed."""

    # At time of writing (18-Jun-2015), no render layer overrides.
    # Collections detach themselves on delete.
    for child in renderLayer.getCollections():
        collection.delete(child)
    
    # Inform our parent (if any) of upcoming delete.
    parent = renderLayer.parent()
    if parent:
        parent._preRenderLayerDelete(renderLayer)

    # Keep an access to the legacy render layer node instance
    legacyRenderLayerName = renderLayer._getLegacyNodeName()
    
    # First disconnect from the render layer
    cmds.disconnectAttr(legacyRenderLayerName + '.msg', renderLayer.name() + '.lrl')

    # Second delete the legacy render layer
    legacyLayer.delete(legacyRenderLayerName)

    # Third delete the render layer
    utils.deleteNode(renderLayer)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
