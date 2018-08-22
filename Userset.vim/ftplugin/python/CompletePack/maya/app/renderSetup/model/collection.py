"""Collection node class and utility functions.

   This module provides the collection class, as well as utility
   functions to operate on collections.

   The collection owns its associated selector node: on collection
   delete, the collection is deleted as well.

   Conceptually, a collection fulfills four roles in render setup:

   1) It is a container of overrides.  If enabled, the collection will
      apply all its enabled overrides on nodes it selects (see (2)).
   2) It selects nodes onto which overrides will be applied.  These nodes
      can be DAG or DG nodes.
   3) It is a container of child collections.  Child collections always
      select nodes based on their parent's selected nodes (see (2)).
   4) It defines render layer membership.  Members of a render layer can
      only be DAG nodes.  These are always a subset of the nodes selected
      by the collection (see (2)).  The members of the render layer are the
      union of the top-level collection members; children collections can
      exclude or re-include members.  See RenderLayer.getMembers for more
      details (including the effect of isolate select mode).

   The application of overrides only obeys enabled / disabled status.

   Render layer membership is determined from enabled / disabled, in
   conjunction with isolate select."""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import re
import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya

import maya.app.renderSetup.model.nodeList as nodeList
import maya.app.renderSetup.model.utils as utils
import maya.app.renderSetup.model.plug as plug
import maya.app.renderSetup.model.typeIDs as typeIDs
import maya.app.renderSetup.model.selector as selector
import maya.app.renderSetup.model.undo as undo
import maya.app.renderSetup.model.override as override
import maya.app.renderSetup.model.overrideUtils as overrideUtils
import maya.app.renderSetup.model.childNode as childNode
import maya.app.renderSetup.model.enabled as computeEnabled
import maya.app.renderSetup.model.namespace as namespace
import maya.app.renderSetup.model.renderSettings as renderSettings
import maya.app.renderSetup.model.rendererCallbacks as rendererCallbacks
import maya.app.renderSetup.model.traverse as traverse
from maya.app.renderSetup.model.renderLayerSwitchObservable import RenderLayerSwitchObservable
import maya.app.renderSetup.model.clipboardData as clipboardData

import maya.app.renderSetup.common.utils as commonUtils
import maya.app.renderSetup.common.profiler as profiler
import maya.app.renderSetup.common.guard as guard
import maya.app.renderSetup.model.context as context

import maya.app.renderSetup.model.jsonTranslatorUtils as jsonTranslatorUtils
import maya.app.renderSetup.model.jsonTranslatorGlobals as jsonTranslatorGlobals


# List all error messages below
kInvalidChildName          = maya.stringTable['y_collection.kInvalidChildName'          ]
kUnknownChild              = maya.stringTable['y_collection.kUnknownChild'              ]
kOverrideCreationFailed    = maya.stringTable['y_collection.kOverrideCreationFailed'    ]
kCollectionMissingSelector = maya.stringTable['y_collection.kCollectionMissingSelector' ]
kRendererMismatch          = maya.stringTable['y_collection.kRendererMismatch'          ]
kIncorrectChildType        = maya.stringTable['y_collection.kIncorrectChildType'        ]

# List of undo messages
kChildAttached = maya.stringTable['y_collection.kChildAttached' ]
kChildDetached = maya.stringTable['y_collection.kChildDetached' ]
kSet           = maya.stringTable['y_collection.kSet'           ]

def collections(c):
    return c.getCollections()

class Collection(nodeList.ListBase, childNode.TreeOrderedItem,
                 childNode.ChildNode):
    """
    Collection node.

    A collection has an ordered list of children, and a selector to
    determine nodes to which the children apply.

    MAYA-59277: 
      - When we start implementing proper hierarchical collections we 
        need to decide on the relationship between parent and child
        selectors. Do we always consider a parent collection to be the 
        union of its child collections, and propagate the selector 
        information upwards when a child collection is added or changed?
        Or do we go the opposite direction and restrict the child collection
        to use the intersection between its selector and its parent's selector?

      - Light child collections always have a single light source member.
        We should utilize this and create a specific selector for such
        use cases for better performance.

    """

    kTypeId = typeIDs.collection
    kTypeName = 'collection'

    # Attributes for collection as list of children.
    # 
    # Connections to lowest-priority and highest-priority child
    # on children linked list.  The lowest-priority child
    # is considered to be the front of the list, and the highest-priority
    # child the back of the list.
    childLowest  = OpenMaya.MObject()
    childHighest = OpenMaya.MObject()

    # Connection to all children in the list.
    children = OpenMaya.MObject()

    # Attribute for message connection to selector node associated with the
    # collection. This attribute is a destination, as only one selector
    # can be associated with each collection.
    aSelector = OpenMaya.MObject()

    # Enabled behavior.  See enabled module for documentation.
    enabled       = OpenMaya.MObject()
    selfEnabled   = OpenMaya.MObject()
    parentEnabled = OpenMaya.MObject()

    # isolateSelected flag as attribute
    isolateSelected = OpenMaya.MObject()
    
    # The number of isolate selected children in a collection's subtree.
    numIsolatedChildren = OpenMaya.MObject()
    
    # The number of isolate selected ancestors of this collection.
    numIsolatedAncestors = OpenMaya.MObject()

    # the SimpleSelector is the default.
    kDefaultSelectorTypeName = selector.SimpleSelector.kTypeName
    
    @staticmethod
    def creator():
        return Collection()

    @staticmethod
    def initializer():
        
        # A collection is a render layer list element.
        # inheritAttributesFrom() must be called before adding any other
        # attributes.
        Collection.inheritAttributesFrom(nodeList.ListItem.kTypeName)

        # A collection is a list of children.
        Collection.children = Collection.initListItems()

        Collection.childLowest = utils.createDstMsgAttr(
            'childLowest', 'cl')
        Collection.addAttribute(Collection.childLowest)

        Collection.childHighest = utils.createDstMsgAttr(
            'childHighest', 'ch')
        Collection.addAttribute(Collection.childHighest)

        Collection.aSelector = utils.createDstMsgAttr('selector', 'sel')
        Collection.addAttribute(Collection.aSelector)
        
        # Set up enabled attribute.
        computeEnabled.initializeAttributes(Collection)

        # Add isolateSelected attribute
        Collection.numIsolatedChildren = computeEnabled.createNumIsolatedChildrenAttribute()
        Collection.addAttribute(Collection.numIsolatedChildren)

        Collection.numIsolatedAncestors = computeEnabled.createHiddenIntAttribute(
            "numIsolatedAncestors", "nia")
        Collection.addAttribute(Collection.numIsolatedAncestors)

        # Add isolateSelected attribute
        numAttrFn = OpenMaya.MFnNumericAttribute() 
        Collection.isolateSelected = numAttrFn.create("isolateSelected", "is", OpenMaya.MFnNumericData.kBoolean, 0)
        numAttrFn.storable = True
        numAttrFn.keyable = False
        numAttrFn.readable = True
        numAttrFn.writable = True
        numAttrFn.hidden = True
        OpenMaya.MPxNode.addAttribute(Collection.isolateSelected)
        
        Collection.attributeAffects(Collection.numIsolatedChildren, Collection.enabled)
        Collection.attributeAffects(Collection.numIsolatedAncestors, Collection.enabled)
        Collection.attributeAffects(Collection.isolateSelected, Collection.enabled)

    def __init__(self):
        super(Collection, self).__init__()
        self._enabledDirty = False
        self._callbackIds  = []
        
    def postConstructor(self):
        # Call parent class postConstructor
        super(Collection, self).postConstructor()

        # Listen to changes in the enabled attribute.
        self._callbackIds = computeEnabled.addChangeCallbacks(self)

    def typeId(self):
        return Collection.kTypeId

    def typeName(self):
        return Collection.kTypeName

    def _createSelector(self, parent=None, selArgs=None):
        """Create a selector node, and attach it to the collection.

        parent is an optional parent collection.  This method must be
        overridden by derived classes."""

        self.setSelectorType(parent.getSelector().kTypeName if parent else \
                             self.kDefaultSelectorTypeName)
        if parent:
            self.getSelector().minimalClone(parent.getSelector())

    def _createAndConnectSelector(self, typeName, selArgs=None):
        """Engine method for _createSelector.
    
        selArgs is an optional dictionary passed to _createSelectorNode."""
    
        newSelector = self._createSelectorNode(
            typeName, self.name()+'Selector', selArgs)
        cmds.connectAttr(newSelector + '.c', self.name() + '.selector')

    def _createSelectorNode(self, typeName, selectorName, selArgs):
        """Create the selector node.

        Can be overridden by derived classes."""
        return cmds.createNode(typeName, name=selectorName, skipSelect=True)
    
    def getSelectorType(self):
        try: return self.getSelector().kTypeName
        except: return None
    
    def setSelectorType(self, typeName):
        '''Sets the selector type of this collection.'''
        if self.getSelectorType() == typeName:
            return
        with undo.NotifyCtxMgr("Set selector type", self._selectorChanged):
            children = [child for child in self.getChildren() if isinstance(child, Collection)]
            # need to disconnect all selector children 
            # otherwise they get deleted along with their parent selector
            for child in children:
                child.getSelector().setParent(None)
            try: self._deleteSelector()
            except: pass
            self._createAndConnectSelector(typeName)
            parent = self.parent()
            selector = self.getSelector()
            if isinstance(parent, Collection):
                selector.setParent(parent.getSelector())
            for child in children:
                child.getSelector().setParent(selector)

    def _deleteSelector(self):
        selector = self.getSelector()   
        cmds.disconnectAttr(selector.name() + '.c', self.name() + '.selector')
        utils.deleteNode(selector)

    def _getInputAttr(self, attr, dataBlock=None):
        return dataBlock.inputValue(attr) if dataBlock else OpenMaya.MPlug(self.thisMObject(), attr)
    
    def _getSelfEnabledPlug(self):
        return OpenMaya.MPlug(self.thisMObject(), Collection.selfEnabled)

    def _getIsolatePlug(self):
        return OpenMaya.MPlug(self.thisMObject(), Collection.isolateSelected)

    def hasIsolatedAncestors(self, dataBlock=None):
        return self._getInputAttr(self.numIsolatedAncestors, dataBlock).asInt() > 0

    def hasIsolatedChildren(self, dataBlock=None):
        return self._getInputAttr(self.numIsolatedChildren, dataBlock).asInt() > 0
    
    def compute(self, plug, dataBlock):
        if plug == self.enabled:
            # We are enabled if:
            #
            # o The normal enabled computation is true (self enabled is true AND
            #   parent enabled is true).
            #
            # AND
            #
            # o We're in batch mode OR
            # o No node is isolated OR
            # o This node is isolated OR
            # o This node has isolate selected children OR
            # o This node has isolate selected ancestors.
            #
            value = computeEnabled.computeEnabled(self, dataBlock) and \
                (cmds.about(batch=True) or \
                dataBlock.inputValue(self.layerNumIsolatedChildren).asInt()==0 or \
                self.isIsolateSelected(dataBlock) or \
                self.hasIsolatedAncestors(dataBlock) or \
                self.hasIsolatedChildren(dataBlock))
            computeEnabled.setEnabledOutput(self, dataBlock, value)

    def enabledChanged(self):
        layer = self.getRenderLayer()
        if layer: 
            layer._enabledChanged(self)
        self.itemChanged()

    def isEnabled(self, dataBlock=None):
        return self._getInputAttr(self.enabled, dataBlock).asBool()

    def isSelfEnabled(self, dataBlock=None):
        return self._getInputAttr(self.selfEnabled, dataBlock).asBool()

    def setSelfEnabled(self, value):
        if value != self.isSelfEnabled():
            # pulling isEnabled will trigger enabledChanged 
            # (no matter if enable output value has changed or not)
            with undo.NotifyCtxMgr("Set Override Enabled",self.isEnabled):
                cmds.setAttr(self.name()+".selfEnabled", 1 if value else 0)

    @guard.state(computeEnabled.isPulling, computeEnabled.setPulling, True)
    def pullEnabled(self):
        # This will force pulling the enabled plug on overrides.  It solves
        # the problem of connection overrides not being applied / unapplied
        # when not visible in the RenderSetup window; being visible in the
        # RenderSetup window causes enabled to be pulled.
        #
        # Connection overrides are not part of the network; they are a
        # procedure that must be run on enable change to modify the
        # network.  Therefore, the enabled plug is not pulled, contrary to
        # value overrides that get inserted in the network, and thus we
        # need to force the plug to be pulled.

        # Two phase procedure to avoid DG cycle check warnings.  First,
        # pull on enabled output of connection overrides.
        needsUpdate = set()
        for n in traverse.depthFirst(self, traverse.nodeListChildren):
            if isinstance(n, override.Override) and n.updateOnEnabledChanged():
                # Call isEnabled to force computation of the enabled output.
                n.isEnabled()
                needsUpdate.add(n)
        
        # Second, update the connection override.  This will iterate over
        # the connection override apply nodes, which query the connection
        # override enabled state we've finished computing above.  Had we
        # done the override enabled computation and the update in the same
        # call, we would have gotten a DG evaluation cycle (compute
        # enabled, cause update, which queries enabled).
        for o in needsUpdate:
            o.update()
        
    def getRenderLayer(self):
        # For hierarchical collections the parent
        # could be another collection, otherwise
        # the parent is always the render layer
        parent = self.parent()
        if isinstance(parent, Collection):
            return parent.getRenderLayer()
        return parent
    
    def isolateSelectedChanged(self):
        layer = self.getRenderLayer()
        if layer: 
            layer._isolateSelectedChanged(self)

    def isIsolateSelected(self, dataBlock=None):
        """ Get if isolate selected. Will always return False in batch mode """
        return False if cmds.about(batch=True) else self._getInputAttr(self.isolateSelected, dataBlock).asBool()

    def setIsolateSelected(self, val):
        if val!=self.isIsolateSelected() and not cmds.about(batch=True):
            with undo.NotifyCtxMgr(kSet % (self.name(), 'isolateSelected', val), self.isolateSelectedChanged):
                # Use a command to support the undo mechanism
                cmds.setAttr(self._getIsolatePlug().name(), val)
                self._updateIsolateSelected(1 if val else -1)
    
    def _findSubcollectionForType(self, typeName):
        '''Finds the subcollection of this collection that will handle that typeName
           or creates it and returns it if it doesn't exist.'''
        filterType, customFilter = selector.Filters.getFiltersFor(typeName)
        
        def predicate(child):
            if not isinstance(child, Collection):
                return False
            sel = child.getSelector()
            return sel.kTypeName == selector.SimpleSelector.kTypeName and \
                sel.getPattern() == "*" and \
                len(sel.staticSelection) == 0 and \
                sel.getFilterType() == filterType and \
                (filterType != selector.Filters.kCustom or sel.getCustomFilterValue() == customFilter)
        
        def creator():
            name = self.name() + "_" + selector.Filters.names.get(filterType, customFilter)
            col = create(name)
            col.setSelectorType(selector.SimpleSelector.kTypeName)
            sel = col.getSelector()
            sel.setPattern('*')
            sel.setFilterType(filterType)
            sel.setCustomFilterValue(customFilter)
            return col
        
        return self.findChild(predicate, creator)
    
    @undo.chunk('Create and append an override')
    def createOverride(self, overrideName, overrideType):
        """ Add an override to the Collection using its node type id or type name."""
        # Note: No need to propagate the change notification
        #       as an empty override does not affect the collection
        over = override.create(overrideName, overrideType)
        if not over:
            raise Exception(kOverrideCreationFailed % overrideName)
        
        # special handle for shader override as they apply to shading engines
        # => create subcollection of shading engines if we're in a dag only collection
        from maya.app.renderSetup.model.connectionOverride import ShaderOverride
        if over.typeId() != typeIDs.shaderOverride or \
            self.getSelector().acceptsType('shadingEngine'):
            self.appendChild(over)
        else:
            self._findSubcollectionForType('shadingEngine').appendChild(over)
        return over
    
    def _getOverrideType(self, plg, overrideType):
        '''Returns the override type that should be created for the given 
        plg in the given collection (self). Overrides that can't be relative will become absolute.'''
        return plg.overrideType(overrideType)
    
    @undo.chunk('Create and append an override')
    def _createOverride(self, plg, overrideType):
        over = override.create(plg.attributeName, self._getOverrideType(plg, overrideType))
        if not over:
            raise Exception(kOverrideCreationFailed % attrName)
        over.finalize(plg.name)
        
        typeName = OpenMaya.MFnDependencyNode(plg.node()).typeName
        collection = self if self.getSelector().acceptsType(typeName) else \
            self._findSubcollectionForType(typeName)
        collection.appendChild(over)
        return over
    
    @undo.chunk('Create and append an absolute override')
    def createAbsoluteOverride(self, nodeName, attrName):
        """ Add an absolute override to a collection """
        return self._createOverride(plug.Plug(nodeName,attrName), typeIDs.absOverride)
            
    @undo.chunk('Create and append a relative override')
    def createRelativeOverride(self, nodeName, attrName):
        """ Add a relative override to a collection """
        return self._createOverride(plug.Plug(nodeName,attrName), typeIDs.relOverride)

    @undo.chunk('Create and append a child collection')
    def _createCollection(self, collectionName, typeName):
        col = create(collectionName, typeName, parent=self)
        self.appendChild(col)
        return col

    def createCollection(self, collectionName):
        """ Add a child collection to the Collection. """
        return self._createCollection(collectionName, Collection.kTypeName)

    def _childAttached(self, child):
        '''Perform work to attach a child.

        The child has already been added to collection's list when this
        method is called.'''

        with undo.NotifyCtxMgr(kChildAttached % (self.name(), child.name()), self.itemChanged):
            # Once inserted, hook up the child's parentEnabled input to our
            # enabled output.  Use existing command for undo / redo purposes.
            cmds.connectAttr(self.name() + '.enabled',
                             child.name() + '.parentEnabled')
            if isinstance(child, Collection):
                child.getSelector().setParent(self.getSelector())
                child._attach(self.getRenderLayer())
                
            layer = self.getRenderLayer()
            if layer:
                layer.descendantAdded(child)
        
    def _detachChild(self, child):
        '''Perform work to detach a child.

        The child has not yet been removed from the collection's list when
        this method is called.'''

        with undo.NotifyCtxMgr(kChildDetached % (self.name(), child.name()), self.itemChanged):
            # Disconnect the child's parentEnabled input from our enabled
            # output.  Use existing command for undo / redo purposes.
            childParentEnabled = child.name() + '.parentEnabled'
            cmds.disconnectAttr(self.name() + '.enabled', childParentEnabled)

            # Child parentEnabled will retain its last value, so set it
            # to True in case the collection gets parented to the render layer.
            cmds.setAttr(childParentEnabled, 1)

            if isinstance(child, Collection):
                child.getSelector().setParent(None)
                child._detach(self.getRenderLayer())

    def _attach(self, layer):
        """Attach this collection."""
        self._connectLayerIsolatedChildren(layer)

        # Number of isolated children doesn't change when we attach.
        # Update isolated children of our ancestors.
        self._updateAncestorsIsolatedChildren(
            self.getNumIsolatedChildren(includeSelf=True))

        # Update isolated ancestors of ourselves and our children.
        self._updateChildrenIsolatedAncestors(
            self.getNumIsolatedAncestors(), includeSelf=True)
            
    def _detach(self, layer):
        """Detach this collection."""
        self._disconnectLayerIsolatedChildren(layer)
        
        # Number of isolated children doesn't change when we detach.
        # Update isolated children of our ancestors.
        self._updateAncestorsIsolatedChildren(
            -self.getNumIsolatedChildren(includeSelf=True))

        # Update isolated ancestors of ourselves and our children.
        self._updateChildrenIsolatedAncestors(
            -self.getNumIsolatedAncestors(), includeSelf=True)


    @undo.chunk('Append to collection')
    def appendChild(self, child):
        """ Add a child as the highest-priority child."""
        if child.typeId()==RenderSettingsCollection.kTypeId \
            or child.typeId()==LightsCollection.kTypeId:
            raise RuntimeError(kIncorrectChildType % child.typeName())

        nodeList.append(self, child)
        self._childAttached(child)

    @undo.chunk('Attach to collection')
    def attachChild(self, pos, child):
        """ Attach a child at a specific position. """
        if child.typeId()==RenderSettingsCollection.kTypeId \
            or child.typeId()==LightsCollection.kTypeId:
            raise RuntimeError(kIncorrectChildType % child.typeName())

        nodeList.insert(self, pos, child)
        self._childAttached(child)

    @undo.chunk('Detach from collection')
    def detachChild(self, child):
        """ Detach a child whatever its position. """
        unapply(child) # NoOp if not applied; otherwise commands are used
        # Must perform detach operations before removing from list,
        # otherwise parenting information is gone.
        self._detachChild(child)
        nodeList.remove(self, child)

    def getChildren(self, cls=childNode.ChildNode):
        """ Get the list of all children. 
        Optionally only the children matching the given class. """
        return list(nodeList.forwardListNodeClassGenerator(self, cls))
    
    def hasChildren(self):
        return self.findChild(lambda child: True) is not None
        
    def getCollections(self):
        return self.getChildren(cls=Collection)
        
    def getCollectionByName(self, collectionName, nested=False):
        for collection in nodeList.forwardListNodeClassGenerator(self, cls=Collection):
            if collection.name() == collectionName:
                return collection
            elif nested:
                collection2 = collection.getCollectionByName(collectionName, True)
                if collection2:
                    return collection2
        return None
        
    def findChild(self, predicate, creator=None):
        '''Find the child of this collection satisfying the predicate function or creates it
        with the creator function if not found and a creator function is specified.
        Function signatures are:
          predicate(childNode): returns boolean.
          creator(void) : returns the created node.'''
        for child in nodeList.forwardListNodeClassGenerator(self, childNode.ChildNode):
            if predicate(child):
                return child
        if not creator:
            return None
        child = creator()
        self.appendChild(child)
        return child

    def getChild(self, childName, cls=childNode.ChildNode):
        """ Look for an existing child by name and optionally class.

            @type childName: string
            @param childName: Name of child to look for
            @type cls: class name
            @param cls: Class name for the type of class to look for
            @rtype: Child model instance
            @return: Found instance or throw an exception
        """
        if not childName:
            raise Exception(kInvalidChildName)

        for child in nodeList.forwardListNodeClassGenerator(self, cls):
            if child.name() == childName:
                return child

        raise Exception(kUnknownChild % (childName, self.name()))

    def isAbstractClass(self):
        # Override method inherited from base class: not an abstract class.
        return False

    def getSelector(self):
        """Return the selector user node for this collection."""
        selector = utils.getSrcUserNode(
            utils.findPlug(self, Collection.aSelector))
        if (selector is None):
            raise Exception(kCollectionMissingSelector % self.name())
        return selector

    @context.applyCollection
    def apply(self):
        """ Apply all children in this collection. """
        with profiler.ProfilerMgr('Collection::apply'):
            # Apply all our children to the selection
            for child in nodeList.forwardListGenerator(self):
                child.apply()
                # UI Feedback (progressBar)
                RenderLayerSwitchObservable.getInstance().notifyRenderLayerSwitchObserver()

    @context.applyCollection
    def postApply(self):
        '''Post applies all children in this collection. This function may be called to apply a collection (with contained overrides)
        after the layer was set visible. It allows inserting new overrides in the currently visible layer
        without the need to toggle visibility.'''
        with profiler.ProfilerMgr('Collection::postApply'):
            # Post apply all our children
            for child in nodeList.forwardListGenerator(self):
                child.postApply()

    @context.unapplyCollection
    def unapply(self):
        """Unapply all children in this collection."""
        with profiler.ProfilerMgr('Collection::unapply'):
            for child in nodeList.reverseListGenerator(self):
                child.unapply()
                # UI Feedback (progressBar)
                RenderLayerSwitchObservable.getInstance().notifyRenderLayerSwitchObserver()

    def getOverrides(self): 
        return self.getChildren(cls=override.Override)

    # Collection interface as list of children.
    # These methods implement the list requirements for the nodeList module.
    #
    # The list front and back are destination plugs connected to the child
    # node's message plug (which is a source).
    def _getFrontAttr(self):
        return Collection.childLowest

    def _getBackAttr(self):
        return Collection.childHighest

    def _getListItemsAttr(self):
        return Collection.children

    def _preChildDelete(self, child):
        # Private interface for child to inform its parent that it is
        # about to be deleted.  Remove the child from our list.
        self.detachChild(child)

    def _selectedNodesChanged(self):
        """ Ownership of this collection or one of its children changed """
        layer = self.getRenderLayer()
        if layer:
            layer._selectedNodesChanged(self)
        self.itemChanged()

    def _selectorChanged(self):
        """Selector of this collection changed.

        Identical to _selectedNodesChanged(), except that the itemChanged()
        notification is given with selectorChanged=True."""
        layer = self.getRenderLayer()
        if layer:
            layer._selectedNodesChanged(self)
        self.itemChanged(selectorChanged=True)

    def _refreshRendering(self):
        ''' Some changes impose to refresh the rendering for the visible layer only. '''
        parent = self.parent()
        if parent:
            parent._refreshRendering()

    def getLayerNumIsolatedChildren(self):
        return OpenMaya.MPlug(
            self.thisMObject(), Collection.layerNumIsolatedChildren).asInt()

    def _getNumIsolatedChildrenPlug(self):
        return OpenMaya.MPlug(self.thisMObject(), Collection.numIsolatedChildren)

    def getNumIsolatedChildren(self, includeSelf=False):
        nic = self._getNumIsolatedChildrenPlug().asInt()
        if includeSelf and self.isIsolateSelected():
            nic += 1
        return nic

    def _getNumIsolatedAncestorsPlug(self):
        return OpenMaya.MPlug(self.thisMObject(), Collection.numIsolatedAncestors)

    def getNumIsolatedAncestors(self):
        return self._getNumIsolatedAncestorsPlug().asInt()

    # See comments in RenderLayer._updateIsolateSelected.
    def _updateNumIsolatedChildren(self, val):
        # Use a command to support the undo mechanism
        if val != 0:
            newVal = self.getNumIsolatedChildren() + val
            cmds.setAttr(self._getNumIsolatedChildrenPlug().name(), newVal)

    def _updateNumIsolatedAncestors(self, val):
        # Use a command to support the undo mechanism
        if val != 0:
            newVal = self.getNumIsolatedAncestors() + val
            cmds.setAttr(self._getNumIsolatedAncestorsPlug().name(), newVal)

    def _updateIsolateSelected(self, val):
        self._updateAncestorsIsolatedChildren(val)
        self._updateChildrenIsolatedAncestors(val)

    def _updateAncestorsIsolatedChildren(self, val):
        layer = self.getRenderLayer()
        if layer:
            layer._updateIsolateSelected(val)
        for c in self.ancestorCollections():
            c._updateNumIsolatedChildren(val)

    def _updateChildrenIsolatedAncestors(self, val, includeSelf=False):
        # Tell descendants there has been a change in their ancestors'
        # isolate select.
        for c in traverse.depthFirst(self, collections):
            if c is self and not includeSelf:
                continue
            c._updateNumIsolatedAncestors(val)
            
    def _connectLayerIsolatedChildren(self, layer):
        # Connect subtree to layer's isolated children attribute.
        if layer:
            for c in traverse.depthFirst(self, collections):
                c._connectSelfLayerIsolatedChildren(layer)

    def _disconnectLayerIsolatedChildren(self, layer):
        # Disconnect subtree from layer's isolated children attribute.
        if layer:
            for c in traverse.depthFirst(self, collections):
                c._disconnectSelfLayerIsolatedChildren(layer)

    def _connectSelfLayerIsolatedChildren(self, layer):
        if layer:
            # Use existing command for undo / redo purposes.
            cmds.connectAttr(layer.name() + '.numIsolatedChildren',
                             self.name() + '.parentNumIsolatedChildren')

    def _disconnectSelfLayerIsolatedChildren(self, layer):
        if layer:
            # Use existing command for undo / redo purposes.
            cmds.disconnectAttr(layer.name() + '.numIsolatedChildren',
                                self.name() + '.parentNumIsolatedChildren')

    def _importChild(self, childName, nodeType, selArgs=None):
        name = cmds.createNode(nodeType, name=childName, skipSelect=True)
        child = utils.nameToUserNode(name)
        if isinstance(child, Collection):
            child._createSelector(None, selArgs)
        self.appendChild(child)
        return child

    def activate(self):
        '''
        Called when this list item is inserted into the list.
        Override this method to do any scene specific initialization.
        '''
        if len(self._callbackIds) == 0:
            self._callbackIds = computeEnabled.addChangeCallbacks(self)
        self.getSelector().activate()

    def deactivate(self):
        '''
        Called when this list item is removed from the list.
        Override this method to do any scene specific teardown.
        '''
        # Remove all callbacks.
        OpenMaya.MMessage.removeCallbacks(self._callbackIds)
        self._callbackIds = []
        self.getSelector().deactivate()

    def _encodeProperties(self, dict):
        super(Collection, self)._encodeProperties(dict)
        dict[self._getSelfEnabledPlug().partialName(useLongNames=True)] = self.isEnabled()
        dict[self._getIsolatePlug().partialName(useLongNames=True)] = self.isIsolateSelected()
        
        if self.getSelectorType() == selector.BasicSelector.kTypeName: # backward comp with 2016 R2
            selectorDict = dict
        else:
            selectorDict = {}
            dict[jsonTranslatorGlobals.SELECTOR_ATTRIBUTE_NAME] = { self.getSelectorType() : selectorDict }
        self.getSelector()._encodeProperties(selectorDict)
        
        dict[jsonTranslatorGlobals.CHILDREN_ATTRIBUTE_NAME] = jsonTranslatorUtils.encodeObjectArray(self.getChildren())

    def _decodeChildren(self, children, mergeType, prependToName):
        jsonTranslatorUtils.decodeObjectArray(children,
                                              jsonTranslatorUtils.MergePolicy(self.getChild, 
                                                                              self._importChild, 
                                                                              mergeType, 
                                                                              prependToName))

    def _decodeProperties(self, dict, mergeType, prependToName):
        super(Collection, self)._decodeProperties(dict, mergeType, prependToName)
        if self._getSelfEnabledPlug().partialName(useLongNames=True) in dict:
            self.setSelfEnabled(dict[self._getSelfEnabledPlug().partialName(useLongNames=True)])

        if self._getIsolatePlug().partialName(useLongNames=True) in dict:
            self.setIsolateSelected(dict[self._getIsolatePlug().partialName(useLongNames=True)])
        
        if jsonTranslatorGlobals.SELECTOR_ATTRIBUTE_NAME not in dict: # backward comp with 2016 R2
            self.setSelectorType(selector.BasicSelector.kTypeName)
            selectorProperties = dict
        else:
            selectorType = dict[jsonTranslatorGlobals.SELECTOR_ATTRIBUTE_NAME].keys()[0]
            if self.getSelectorType() != selectorType:
                self.setSelectorType(selectorType)
            selectorProperties = dict[jsonTranslatorGlobals.SELECTOR_ATTRIBUTE_NAME].values()[0]
        self.getSelector()._decodeProperties(selectorProperties)

        if jsonTranslatorGlobals.CHILDREN_ATTRIBUTE_NAME in dict:
            self._decodeChildren(dict[jsonTranslatorGlobals.CHILDREN_ATTRIBUTE_NAME],
                                 mergeType, 
                                 prependToName)

    def acceptImport(self):
        super(Collection, self).acceptImport()
        for child in self.getChildren():
            child.acceptImport()
            
    def isSelfAcceptableChild(self):
        """Overridden instances that return False, prevent copy/paste of the collection type to itself."""
        return True

    def isAcceptableChild(self, modelOrData):
        """ Check if the model could be a child"""
        if isinstance(modelOrData, clipboardData.ClipboardData):
            isOverride = modelOrData.typeName() in _overrideTypes
            parentTypeName = modelOrData.parentTypeName
        else:
            isOverride = isinstance(modelOrData, override.Override)
            parentTypeName = modelOrData.parent().typeName()
        return isOverride and parentTypeName == self.typeName() or (modelOrData.typeName() == self.typeName() and self.isSelfAcceptableChild())
    def isTopLevel(self):
        """Is the collection's parent a render layer?"""
        # Don't have access to renderLayer.RenderLayer, type check on
        # Collection instead.
        return not isinstance(self.parent(), Collection)

    def ancestorCollections(self):
        """Return this collection's ancestors.

        Neither the collection itself, nor the render layer, are included
        in the ancestors.  Therefore, a top-level collection has no
        ancestors."""

        parent = self.parent()
        while isinstance(parent, Collection):
            yield parent
            parent = parent.parent()

class LightsCollection(Collection):
    """
    LightsCollection node.

    A collection node specific for grouping light sources
    and overrides on those light sources.

    This collection should have all light sources as member by default. All nodes 
    matching the light classification should be returned by the selector
    on this collection.

    """

    kTypeId = typeIDs.lightsCollection
    kTypeName = 'lightsCollection'

    @staticmethod
    def creator():
        return LightsCollection()

    @staticmethod
    def initializer():
        # Inherit all attributes from parent class
        LightsCollection.inheritAttributesFrom(Collection.kTypeName)

    def __init__(self):
        super(LightsCollection, self).__init__()

    def typeId(self):
        return LightsCollection.kTypeId

    def typeName(self):
        return LightsCollection.kTypeName

    def _createSelector(self, parent=None, selArgs=None):
        self._createAndConnectSelector(selector.SimpleSelector.kTypeName)

        # Make it select all light sources in the scene
        self.getSelector().setPattern("*")
        self.getSelector().setFilterType(selector.Filters.kLights)

    def setSelectorType(self, typeName):
        raise RuntimeError('Illegal call to derived class method.')

    def createCollection(self, collectionName):
        """ Add a lights child collection to the Collection. """
        return self._createCollection(collectionName, LightsChildCollection.kTypeName)

    def isAcceptableChild(self, modelOrData):
        """Check if the argument can be a child of this collection.
           
           We want to prevent copying LightsChildCollections in the same 
           LightsCollection at the expense of not being able to copy 
           LightsChildCollections between different LightsCollections.
        """
        return False

    def compute(self, plug, dataBlock):
        computeEnabled.compute(self, plug, dataBlock)


class LightsChildCollection(Collection):
    """
        LightsChildCollection node.

        A child collection node specific for one single light source
        and overrides on this light source.
    
    """

    kTypeId = typeIDs.lightsChildCollection
    kTypeName = 'lightsChildCollection'

    @staticmethod
    def creator():
        return LightsChildCollection()

    @staticmethod
    def initializer():
        # Inherit all attributes from parent class
        LightsChildCollection.inheritAttributesFrom(Collection.kTypeName)

    def __init__(self):
        super(LightsChildCollection, self).__init__()

    def typeId(self):
        return LightsChildCollection.kTypeId

    def typeName(self):
        return LightsChildCollection.kTypeName

    def _createSelector(self, parent=None, selArgs=None):
        self._createAndConnectSelector(selector.SimpleSelector.kTypeName)
        
        # Only accepts light sources.
        self.getSelector().setFilterType(selector.Filters.kLights)

    def setSelectorType(self, typeName):
        raise RuntimeError('Illegal call to derived class method.')

    def compute(self, plug, dataBlock):
        computeEnabled.compute(self, plug, dataBlock)

    def isAcceptableChild(self, modelOrData):
        """Check if the argument can be a child of this collection.
        
           Pasting is prevented because the Light Editor considers only the 
           first override in the LightsChildCollection. Additionally dragging 
           is prevented between overrides in LightsChildCollections to prevent 
           dragging between incompatible LightsChildCollection types 
           (ie. point light, spot light)
        """
        return False


class RenderSettingsCollection(Collection):
    """
    Render Settings Collection node.

    This collection has an ordered list of children, and a static & const selector
    to determine nodes to which the children apply. The list of nodes is based
    on the selected renderer at the time of creation.
    
    MAYA-66757:
    - A base collection will be needed to factorize commonalities and segregate differences.
    - A static selector is needed which could be the existing static selection or an object set.
    - The name is read-only.
    - The selector content is read-only
    - The render name should be part of the collection so that the settings are clearly linked 
      to the used renderer, or linked using a plug

    """

    kTypeId = typeIDs.renderSettingsCollection
    kTypeName = 'renderSettingsCollection'

    # Type of selector created by this collection
    kSelectorTypeName = selector.SimpleSelector.kTypeName
    
    @staticmethod
    def creator():
        return RenderSettingsCollection()

    @staticmethod
    def initializer():
        # A render settings collection is a render layer list element.
        # inheritAttributesFrom() must be called before adding any other attributes.
        RenderSettingsCollection.inheritAttributesFrom(Collection.kTypeName)

    def __init__(self):
        super(RenderSettingsCollection, self).__init__()

    @staticmethod
    def containsNodeName(nodeName):
        return nodeName in renderSettings.getDefaultNodes()

    def _createSelector(self, parent=None, selArgs=None):
        self._createAndConnectSelector(self.kSelectorTypeName)

        # Set the default nodes as static selection
        # Note: Some renderers could return nodes which do not exist yet.
        self.getSelector().staticSelection.setWithoutExistenceCheck(renderSettings.getDefaultNodes())
        self.getSelector().setFilterType(selector.Filters.kAll)

    def setSelectorType(self, typeName):
        raise RuntimeError('Illegal call to derived class method.')

    def typeId(self):
        return RenderSettingsCollection.kTypeId

    def typeName(self):
        return RenderSettingsCollection.kTypeName

    def appendChild(self, child):
        if isinstance(child, Collection):
            raise RuntimeError(kIncorrectChildType % child.typeName())
        else:
            super(RenderSettingsCollection, self).appendChild(child)

    def attachChild(self, pos, child):
        if isinstance(child, Collection):
            raise RuntimeError(kIncorrectChildType % child.typeName())
        else:
            super(RenderSettingsCollection, self).attachChild(pos, child)

    def _createCollection(self, collectionName, typeName):
        raise RuntimeError(kIncorrectChildType % typeName)

    def compute(self, plug, dataBlock):
        computeEnabled.compute(self, plug, dataBlock)

    def isAcceptableChild(self, modelOrData):
        """Check if the argument can be a child of this collection.

           No collection of any kind can be a child of this collection."""
        return modelOrData.typeName() not in _collectionTypes and \
            super(RenderSettingsCollection, self).isAcceptableChild(modelOrData)
    
    def _getOverrideType(self, plg, overrideType):
        overrideType = super(RenderSettingsCollection, self)._getOverrideType(plg, overrideType)
        return typeIDs.absUniqueOverride if overrideType == typeIDs.absOverride else typeIDs.relUniqueOverride

class AOVCollection(Collection):
    """
    AOV (arbitrary output variable) parent collection node.
    """

    kTypeId = typeIDs.aovCollection
    kTypeName = 'aovCollection'

    
    @staticmethod
    def creator():
        return AOVCollection()

    @staticmethod
    def initializer():
        # An AOV collection is a render layer list element.
        # inheritAttributesFrom() must be called before adding any other attributes.
        AOVCollection.inheritAttributesFrom(Collection.kTypeName)

    def __init__(self):
        super(AOVCollection, self).__init__()

    @staticmethod
    def containsNodeName(nodeName):
        callbacks = rendererCallbacks.getCallbacks(rendererCallbacks.CALLBACKS_TYPE_AOVS)
        try:
            callbacks.getAOVName(nodeName)
            return True
        except:
            return False

    def _createSelector(self, parent=None, selArgs=None):
        # Selector type name argument is ignored.
        self._createAndConnectSelector('')
        
    def _createSelectorNode(self, typeName, selectorName, selArgs):
        # Ignore the argument selector type name: get the AOV collection
        # selector from the AOV renderer callback.
        callbacks = rendererCallbacks.getCallbacks(rendererCallbacks.CALLBACKS_TYPE_AOVS)
        return callbacks.getCollectionSelector(selectorName)

    def setSelectorType(self, typeName):
        raise RuntimeError('Illegal call to derived class method.')

    def typeId(self):
        return AOVCollection.kTypeId

    def typeName(self):
        return AOVCollection.kTypeName

    def appendChild(self, child):
        if isinstance(child, Collection) and not isinstance(child, AOVChildCollection):
            raise RuntimeError(kIncorrectChildType % child.typeName())
        else:
            super(AOVCollection, self).appendChild(child)

    def attachChild(self, pos, child):
        if isinstance(child, Collection) and not isinstance(child, AOVChildCollection):
            raise RuntimeError(kIncorrectChildType % child.typeName())
        else:
            super(AOVCollection, self).attachChild(pos, child)

    # This should never be called, as AOVCollections are created in renderLayer.py in aovCollectionInstance()
    def _createCollection(self, collectionName, typeName):
        raise RuntimeError(kIncorrectChildType % typeName)

    def compute(self, plug, dataBlock):
        computeEnabled.compute(self, plug, dataBlock)

class AOVChildCollection(Collection):
    """
        AOV (arbitrary output variable) Child Collection node.
    """

    kTypeId = typeIDs.aovChildCollection
    kTypeName = 'aovChildCollection'

    @staticmethod
    def creator():
        return AOVChildCollection()

    @staticmethod
    def initializer():
        # Inherit all attributes from parent class
        AOVChildCollection.inheritAttributesFrom(Collection.kTypeName)

    def __init__(self):
        super(AOVChildCollection, self).__init__()

    def containsNodeName(self, nodeName):
        return nodeName in self.getSelector().getAbsoluteNames()

    def typeId(self):
        return AOVChildCollection.kTypeId

    def typeName(self):
        return AOVChildCollection.kTypeName

    def _createSelector(self, parent=None, selArgs=None):
        # Selector type name argument is ignored.
        self._createAndConnectSelector('', selArgs)
        
    def _createSelectorNode(self, typeName, selectorName, selArgs):
        # Ignore the argument selector type name: get the AOV child
        # collection selector from the AOV renderer callback.
        #
        # selArgs is a dictionary for selector argument 
        # construction.  It must contain a value for 'aovName'.
        callbacks = rendererCallbacks.getCallbacks(rendererCallbacks.CALLBACKS_TYPE_AOVS)
        return callbacks.getChildCollectionSelector(selectorName, selArgs['aovName'])

    def setSelectorType(self, typeName):
        raise RuntimeError('Illegal call to derived class method.')

    def compute(self, plug, dataBlock):
        computeEnabled.compute(self, plug, dataBlock)

    def isSelfAcceptableChild(self):
        """This code prevents copy/paste of AOV child collections to themselves/other AOV child collections."""
        return False
        
@undo.chunk('Create collection')
@namespace.root
def create(name, nodeType=Collection.kTypeName, parent=None, **selArgs):
    """ Create a collection.

    Returns the MPxNode object corresponding to the created
    collection node.  A RuntimeError is raised in case of error.
    The selArgs keyword arguments are passed along to the selector creation.

    This function is undoable.
    
    """
    # collection names should never contain namespace delimiter or other invalid characters
    # collections belong to current namespace (i.e. root)
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    if isinstance(nodeType, basestring):
        typeName = nodeType
    else:
        typeName = cmds.objectType(typeFromTag=nodeType.id())

    # To avoid writing a command to implement collection creation,
    # re-use existing name-based commands for undo / redo purposes, since
    # collection creation is not performance-critical.  If the name
    # flag is specified, it cannot be an empty string.

    returnCollectionName = cmds.createNode(
        typeName, name=name, skipSelect=True) if name else \
        cmds.createNode(typeName, skipSelect=True)
    collection = utils.nameToUserNode(returnCollectionName)

    collection._createSelector(parent=parent, selArgs=selArgs)

    return collection


@undo.chunk('Delete collection')
def delete(collection):
    """Remove the argument collection from the scene.

    All overrides and sub-collections in the collection are removed."""
    
    # Inform our parent (if any) of upcoming delete.
    # This will remove the collection from its parent,
    # and will trigger deactivation of the collection
    # causing it and the selector to stop listening to scene and attribute changes.
    # Need to call _preChildDelete before removing children, otherwise we lose the parenting information 
    # to the children which may be used by the parent (ex: renderLayers use that information
    # to determine if they need to be refreshed).
    parent = collection.parent()
    if parent:
        parent._preChildDelete(collection)
    
    # Delete the children.
    for child in collection.getChildren():
        if isinstance(child, Collection):
            delete(child)
        else:
            override.delete(child)

    # Deleting the selector means unhooking the selector node
    # from the collection and removing it from the scene.
    collection._deleteSelector()

    # Deleting the node will remove it from the scene.
    utils.deleteNode(collection)


@undo.chunk('Unapply a collection')
def unapply(collection):
    ''' Command to unapply a collection '''
    if isinstance(collection, Collection):
        for c in collection.getChildren():
            unapply(c)
    else:
        # End of recursion so unapply the override
        #  using a command
        override.UnapplyCmd.execute(collection)

def getAllCollectionClasses():
    """ Returns the list of Collection subclasses """
    return commonUtils.getSubClasses(Collection)
_collectionTypes = { c.kTypeName for c in getAllCollectionClasses() }
_overrideTypes = { o.kTypeName for o in overrideUtils.getAllOverrideClasses() }
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
