'''
This module centralizes the treatment of applying/unapplying layers/collections/overrides.

RenderLayers, Collections and Overrides are DG nodes they should technically be well-behaved, 
i.e. they should depend only on their local input attributes to compute consistently the same outputs.
In practice, they don't because some collections are traversing connections to populate their content and yet these connections 
may change because of previously applied overrides that will insert nodes in the unique global graph and/or edit connections in it.
This module is tracking apply/unapply/connection override update in a global way (context) to insure that collection's content are correctly
evaluated when they are applied.

Example: if we have something like this:

renderLayer1
  - collection1 with pSphere1
    - collection1_shaders1 gathering shaders assigned to pSphere1 (lambert1)
      - abs override color to yellow
    - materialOverride1 assigning blinn1 to pSphere1
    - collection1_shaders2 gathering shaders assigned to pSphere1 (blinn1 if materialOverrides is enabled, lambert1 otherwise)
      - abs override color to green

On apply, collection1_shaders2 must reevaluate its content depending on wheter or not materialOverride1 is enabled.
On the other hand, collection1_shaders1 remains unchanged because it is evaluated before materialOverride1.

This context module ensures that collection1_shaders1 doesn't listen to materialOverride1 
(on apply, on enable/disable, on connection change) but collection1_shaders2 does. 

On apply: 
 > apply renderLayer1 
   > evaluate collection1 content
   > deactivate collection1's selector
   > apply collection1
     > evaluate collection1_shader1 content
     > deactivate collection1_shaders1's selector
     > apply collection1_shaders1
       > override lambert1's color to yellow
     > assign blinn1 to pSphere1
     > evaluate collection1_shader2 content
     > deactivate collection1_shaders2's selector
     > apply collection1_shaders2
       > override blinn1's color to green
   > reactivate all selectors from the first applied element (i.e. renderLayer1)
   
On materialOverride1 update (enable/disable/connection changed, when renderLayer1 is visible):
 > create a PivotGuard on materialOverride1. This will deactivate all the selectors BEFORE materialOverride1
   but let the ones after activated.
 > update materialOverride1
 > look if there's a collection AFTER that materialOverride1 to see if any is dirty 
   (i.e. they may need to reevaluate their content due to the connection change). collection1_shaders2 will be.
   It will then create a PivotGuard around collection1_shaders2 and reapply the layer.
   The PivotGuard guaranties that collection1 and collection1_shaders1 selectors and protect these collections 
   from being unapplied/reapplied, since they would remain unchanged anyway.
 
'''

import maya.app.renderSetup.model.utils as utils
import maya.app.renderSetup.model.traverse as traverse
import maya.app.renderSetup.model.sceneObservable as sceneObservable
import maya.app.renderSetup.common.guard as guard
import maya.api.OpenMaya as OpenMaya

def _getRoot(element):
    from maya.app.renderSetup.model.renderLayer import RenderLayer
    while element:
        parent = element.parent()
        if not parent or isinstance(element, RenderLayer):
            return element
        element = parent

def _getCollectionsBefore(pivot):
    from maya.app.renderSetup.model.collection import Collection
    parent = pivot.parent()
    root = _getRoot(parent)
    for child in traverse.depthFirst(root, traverse.nodeListChildren):
        if child == pivot:
            return
        if isinstance(child, Collection):
            yield child

class PivotGuard:
    '''Protects every override that is before the pivot in application order from
    being unapplied or applied. Also deactivate all the selectors before pivot.
    The pivot can be either a collection or an override.
    This is useful for partially reapplying a layer from a certain point.'''
    
    lockedNames = set()
    
    def __init__(self, pivot):
        self.pivot = pivot
        # Silence pylint warning.
        self.collections = None
    
    def __enter__(self):
        self.collections = [c for c in _getCollectionsBefore(self.pivot) if c.name() not in PivotGuard.lockedNames]
        PivotGuard.lockedNames.update((c.name() for c in self.collections))
        for collection in self.collections:
            collection.getSelector().deactivate()

    def __exit__(self, type, value, traceback):
        PivotGuard.lockedNames.difference_update((c.name() for c in self.collections))
        for collection in self.collections:
            collection.getSelector().activate()
    
    @staticmethod
    def accepts(override):
        parent = override.parent()
        return parent is None or parent.name() not in PivotGuard.lockedNames

class StackContext(object):
    stack = []
    
    @staticmethod
    def empty():
        return len(StackContext.stack) == 0
    
    def __init__(self, element):
        self.element = element
    
    def __enter__(self):
        StackContext.stack.append(self.element)

    def __exit__(self, type, value, traceback):
        StackContext.stack.pop()

class ApplyContext(StackContext):
    def __exit__(self, type, value, traceback):
        super(ApplyContext, self).__exit__(type, value, traceback)
        if StackContext.empty():
            self.conclude()
    
    def conclude(self):
        pass

class ApplyLayerContext(ApplyContext):
    def conclude(self):
        for c in utils.getCollectionsRecursive(self.element):
            c.getSelector().activate()

class ApplyCollectionContext(ApplyContext):
    def conclude(self):
        self.element.getSelector().activate()
        for c in utils.getCollectionsRecursive(self.element):
            c.getSelector().activate()

def stateGuards(ignoreReferenceEdit=True, enableSceneObservers=False):
    def decorator(f):
        @guard.state(OpenMaya.MFnReference.ignoreReferenceEdits, OpenMaya.MFnReference.setIgnoreReferenceEdits, ignoreReferenceEdit)
        @guard.state(sceneObservable.sceneObserversEnabled, sceneObservable.enableSceneObservers, enableSceneObservers)
        def stateGuardsWrapper(*args, **kwargs):
            return f(*args, **kwargs)
        return stateGuardsWrapper
    return decorator

# decorators for keeping track of application, unapplication and update context
def applyLayer(f):
    @stateGuards()
    def applyLayerWrapper(*args, **kwargs):
        with ApplyLayerContext(args[0]): # args[0] = self (RenderLayer)
            f(*args, **kwargs)
    return applyLayerWrapper

def applyCollection(f):
    @stateGuards()
    def applyCollectionWrapper(*args, **kwargs):
        collection = args[0]
        with ApplyCollectionContext(collection):
            selector = collection.getSelector()
            selector.names() # pull names to update cache if needed
            selector.deactivate()
            f(*args, **kwargs)
    return applyCollectionWrapper

def applyOverride(f):
    @stateGuards()
    def applyOverrideWrapper(*args, **kwargs):
        if PivotGuard.accepts(args[0]): # args[0] = self (Override)
            f(*args, **kwargs)
    return applyOverrideWrapper

def unapplyLayer(f):
    @stateGuards()
    def unapplyLayerWrapper(*args, **kwargs):
        with StackContext(args[0]):
            f(*args, **kwargs)
    return unapplyLayerWrapper

def unapplyCollection(f):
    @stateGuards()
    def unapplyCollectionWrapper(*args, **kwargs):
        with StackContext(args[0]):
            f(*args, **kwargs)
    return unapplyCollectionWrapper

def unapplyOverride(f):
    # since there are cases where selectors caches can be wrong due to being evaluated
    # when the scene is not in the "state" it should be when treating the collection they belong to,
    # enabling scene observation on unapply override will dirty caches again so they will be correctly
    # recomputed when reapplied
    @stateGuards(enableSceneObservers=True)
    def unapplyOverrideWrapper(*args, **kwargs):
        if PivotGuard.accepts(args[0]): # args[0] = self (Override)
            f(*args, **kwargs)
    return unapplyOverrideWrapper

def updateConnectionOverride(f):
    # enable scene observers on connection changes since subsequent collections selectors
    # may change their content due to that connection change
    # but previously applied collections must not listen because their content did not depend on that
    # connection override
    # so the idea is to enable scene observers but process the connection override update with following the steps:
    #   1) disable observation before connection override (deactivate previous selectors)
    #   2) update connection override
    #   3) reapply layer from the first dirty collection AFTER the connection override to reflect that connection change
    @stateGuards(enableSceneObservers=True)
    def updateConnectionOverrideWrapper(*args, **kwargs):
        override = args[0] # args[0] = self (Override)
        layer = override.getRenderLayer()
        if not StackContext.empty() or not layer or not layer.isVisible():
            # Only do the expensive update (with PivotGuards/unapply/apply) if updating the connection override in isolation,
            # effectively assuming that if (not StackContext.empty()), something (collection or layer) in that apply/unapply stack 
            # is already doing the necessary work to make sure that selectors listen/invalidate caches correctly or layer should 
            # tell it may need to be refreshed (layer.needsRefresh() = True)
            
            # if we're currently applying layer => previous selectors are already deactivated => nothing special to do
            # if we're currently unapplying layer => all selectors will listen and invalidate caches
            # if we're currently applying collection (postApply) => layer will tell it may need to be refreshed
            # if we're currently unapplying collection (detach) => layer will tell it may need to be refreshed
            f(*args, **kwargs)
            return
        
        needsApplyUpdate = layer.needsApplyUpdate
        pivot = None
        # use a PivotGuard on the override to make sure that every collection 
        # before the override is not listening the scene changes (1)
        with PivotGuard(override):
            # update call (2)
            f(*args, **kwargs) 
            # find the next pivot from where we'd need to unapply/reapply layer to make it truthful to that connection change
            # (subsequent collection may be populated differently because of that connection change
            #  => they should then apply to a different set of nodes)
            pivot = next((c for c in utils.getCollectionsRecursive(layer) \
                if c.getSelector().isDirty() and c.name() not in PivotGuard.lockedNames), None)
        
        if pivot: 
            # something was dirtied after the connection override update
            # => reapply layer from that point
            with PivotGuard(pivot):
                layer.unapply()
                layer.apply()
            # what triggered needsApplyUpdate to be True could have been before
            # the updated connection override (and there's currently no way to determine that)
            # => it could be false to say the layer doesn't need apply update anymore
            # layer.apply() sets needsApplyUpdate to False => reset it to its previous value
            layer.needsApplyUpdate = needsApplyUpdate
    return updateConnectionOverrideWrapper
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
