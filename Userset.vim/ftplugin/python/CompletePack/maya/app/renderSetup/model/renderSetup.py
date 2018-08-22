"""Render setup singleton node.

   The render setup node is the main entry point for the render setup
   system.  Render setup is a singleton that manages a list of render
   layers, each one of which can have different overrides to
   non-destructively change the scene.

   The data model for render setup is the following:

   - A render setup singleton node, which has a list of render layers.
   - Each render layer has a list of collections, and an optional list of 
     overrides.
   - Each collection has a selector, a list of overrides, and an optional 
     list of child collections.

   A render setup can also be imported and exported, to be shared between
   different scenes."""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya

import maya.app.renderSetup.model.observable as observable
import maya.app.renderSetup.model.renderLayer as renderLayer
import maya.app.renderSetup.model.nodeList as nodeList
import maya.app.renderSetup.model.utils as utils
import maya.app.renderSetup.model.typeIDs as typeIDs
import maya.app.renderSetup.model.nodeNotes as nodeNotes
import maya.app.renderSetup.model.serializableNode as serializableNode
import maya.app.renderSetup.model.undo as undo
import maya.app.renderSetup.model.renderSetupPreferences as userPrefs
import maya.app.renderSetup.model.override as override
import maya.app.renderSetup.model.applyOverride as applyOverride
import maya.app.renderSetup.model.renderSetupPrivate as renderSetupPrivate
import maya.app.renderSetup.model.renderSettings as renderSettings
import maya.app.renderSetup.model.aovs as aovs
import maya.app.renderSetup.model.sceneObservable as sceneObservable
import maya.app.renderSetup.model.shadingNodes as shadingNodes

import maya.app.renderSetup.common.utils as commonUtils
import maya.app.renderSetup.common.profiler as profiler

import maya.app.renderSetup.model.jsonTranslatorUtils as jsonTranslatorUtils
import maya.app.renderSetup.model.jsonTranslatorGlobals as jsonTranslatorGlobals

import maya.app.renderSetup.common.guard as guard
import maya.app.renderSetup.model.namespace as namespace
import maya.app.renderSetup.model.plug as plug
import maya.app.renderSetup.model.conversion as conversion
import maya.app.renderSetup.model.localOverride as localOverride

# Python 1.0 API for MFileIO.  Remember that Python 1.0 API MObject's
# are not compatible with Python 2.0 API MObject's.
import maya.OpenMaya as OpenMaya1_0

import weakref
import os
from collections import deque

# Workaround to MAYA-65920: at startup, MSceneMessage.kAfterNew file callback
# is incorrectly called by Maya before the MSceneMessage.kBeforeNew file
# callback, which should be illegal.  Detect this and ignore illegal calls to
# after new file callbacks.  PPT, 19-Jan-16.
_beforeNewCbCalled = False

# Name of the singleton node, and of its type.  The render setup singleton
# must be in the root namespace.
_RENDER_SETUP_TYPE = 'renderSetup'
_RENDER_SETUP_NAME = ':' + _RENDER_SETUP_TYPE

# Decode options
DECODE_AND_OVERWRITE = jsonTranslatorGlobals.DECODE_AND_ADD     # Flush existing render setup and add without any namesapce
DECODE_AND_MERGE     = jsonTranslatorGlobals.DECODE_AND_MERGE   # Merge with the existing render setup objects and rename the unexpected objects
DECODE_AND_RENAME    = jsonTranslatorGlobals.DECODE_AND_RENAME  # Renaming all decoded render setup objects to not conflict with the existing render setup


# List all error messages
kInvalidRenderLayerName      = maya.stringTable['y_renderSetup.kInvalidRenderLayerName'      ]
kUnknownRenderLayer          = maya.stringTable['y_renderSetup.kUnknownRenderLayer'          ]
kUnknownLegacyRenderLayer    = maya.stringTable['y_renderSetup.kUnknownLegacyRenderLayer'    ]
kRenderSetupNodeTypeMismatch = maya.stringTable['y_renderSetup.kRenderSetupNodeTypeMismatch' ]
kRenderSetupNodeNameMismatch = maya.stringTable['y_renderSetup.kRenderSetupNodeNameMismatch' ]
kSyncingActiveLayerMessage   = maya.stringTable['y_renderSetup.kSyncingActiveLayerMessage'   ]
kFileRefCbFailed             = maya.stringTable['y_renderSetup.kFileRefCbFailed'  ]
kBefore                      = maya.stringTable['y_renderSetup.kBefore' ]
kAfter                       = maya.stringTable['y_renderSetup.kAfter' ]
kLoading                     = maya.stringTable['y_renderSetup.kLoading' ]
kUnloading                   = maya.stringTable['y_renderSetup.kUnloading' ]
kRegisterFailed              = maya.stringTable['y_renderSetup.kRegisterFailed' ]
kUnregisterFailed            = maya.stringTable['y_renderSetup.kUnregisterFailed' ]

def _preventDeletionFromSceneCleanupCB(nodeToBeDeleted, connectedNode, connection):
    # Prevent node deletion if the connected node is 
    # any of the connection override nodes
    nodeObj = commonUtils.nameToNode(connectedNode)
    if nodeObj:
        fn = OpenMaya.MFnDependencyNode(nodeObj)
        return fn.typeId in [
            typeIDs.applyConnectionOverride,
            typeIDs.connectionOverride,
            typeIDs.shaderOverride,
            typeIDs.materialOverride]
    return False

def _fileRefErrMsg(when, what, resolvedRefPath):
    return kFileRefCbFailed % (when, what, resolvedRefPath)

def canOverride(nodeName, attrName):
    ''' The method checks if an override could be 'applied' to the specified node/attribute '''
    # This function is called in TrenderSetup.cpp.  Note that we are
    # not verifying the connectable status of the plug, assuming render
    # setup can connect even to unconnectable plugs.
    plg = plug.findPlug(nodeName, attrName)
    return plg is not None \
           and plg.isOvrSupported() \
           and not plg.isLocked \
           and not commonUtils.isNodeInstance(plg.node(), override.Override)

def hasOverrideApplied(nodeName, attrName):
    ''' The method checks if the specified node/attribute has an override applied'''
    # This function is called in TrenderSetup.cpp.
    plg = plug.findPlug(nodeName, attrName)
    if plg:
        # Check if this is an override nodes. They can't be overridden but they will have connections
        # to apply override nodes by design, and will return false positives below
        if commonUtils.isNodeInstance(plg.node(), override.Override):
            return False

        def _hasOverrideApplied(mplug):
            # Check if a value override is applied
            src = utils.plugSrc(mplug)
            if src and commonUtils.isNodeInstance(src.node(), applyOverride.ApplyOverride):
                return True
            # Check if a connection override is applied
            dst = utils.plugDst(mplug)
            for d in (dst if dst else []):
                if commonUtils.isNodeInstance(d.node(), applyOverride.ApplyOverride):
                    return True

        # Check the attribute
        if _hasOverrideApplied(plg.plug):
            return True
        # Check any child attributes
        if plg.plug.isCompound:
            for idx in range(0, plg.plug.numChildren()):
                if _hasOverrideApplied(plg.plug.child(idx)):
                    return True
        # Check any parent attribute
        elif plg.plug.isChild:
            if _hasOverrideApplied(plg.plug.parent()):
                return True
    return False


# Because of MAYA-59270, MPxNode must appear last in the list of base classes.
class RenderSetup(nodeList.ListBase, nodeNotes.NodeNotes, serializableNode.SerializableNode, OpenMaya.MPxNode):
    """Singleton node that manages a list of render layers.

    The render setup node is a singleton: at most one can exist in a scene.
    It is not implemented as a default node, and therefore is not created
    on file new, but rather created on demand."""

    kTypeId = typeIDs.renderSetup
    kTypeName = _RENDER_SETUP_TYPE

    # Attributes

    # Connections to first and last render layers on render layer linked list.
    firstRenderLayer = OpenMaya.MObject()
    lastRenderLayer  = OpenMaya.MObject()

    # Connection to all render layers in the list.
    renderLayers = OpenMaya.MObject()

    @staticmethod
    def creator():
        return RenderSetup()

    @staticmethod
    def initializer():

        # A render setup is a list of render layers.
        RenderSetup.renderLayers = RenderSetup.initListItems()

        RenderSetup.firstRenderLayer = utils.createDstMsgAttr(
            'firstRenderLayer', 'frl')
        RenderSetup.addAttribute(RenderSetup.firstRenderLayer)

        RenderSetup.lastRenderLayer = utils.createDstMsgAttr(
            'lastRenderLayer', 'lrl')
        RenderSetup.addAttribute(RenderSetup.lastRenderLayer)

    def __init__(self):
        super(RenderSetup, self).__init__()
        self.activeLayerChangeObservable = observable.Observable()
        self._cbIds = []
        self.visibleLayerBeforeUnloadReference = None
        self.visibleLayerBeforeLoadReference = None
        self._addToModelCbId = None
        
        self._callbacks = {
            sceneObservable.SceneObservable.NODE_ADDED : self._onMayaNodeAddedCB,
            sceneObservable.SceneObservable.BEFORE_REFERENCE_LOAD : self._beforeLoadReferenceCB,
            sceneObservable.SceneObservable.REFERENCE_LOADED : self._afterLoadReferenceCB, 
            sceneObservable.SceneObservable.BEFORE_REFERENCE_UNLOAD : self._beforeUnloadReferenceCB, 
            sceneObservable.SceneObservable.REFERENCE_UNLOADED : self._afterUnloadReferenceCB}
        
        for type, callback in self._callbacks.iteritems():
            sceneObservable.instance().register(type, callback)
        
        self._cbIds.append(OpenMaya.MDGMessage.addNodeRemovedCallback(self._onNodeRemoved, self.kTypeName))
        
        self._cbIds.append(OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kBeforeSave,
            self._beforeSaveSceneCB))

        self._cbIds.append(OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kAfterOpen, self._afterOpenCB))

        # List to keep objects created by duplication.
        # This allows objects to be added only once to the default collection of the visible layer
        # when duplication is completed.
        self._duplicated = None
        self._cbIds.append(OpenMaya.MModelMessage.addBeforeDuplicateCallback(self._beforeDuplicate))
        self._cbIds.append(OpenMaya.MModelMessage.addAfterDuplicateCallback(self._afterDuplicate))

        self._defaultRenderLayer = renderLayer.DefaultRenderLayer()

        # Add a callback to prevent nodes to be deleted when Scene Cleanup is executed
        if not cmds.about(batch=True):
            cmds.callbacks(addCallback=_preventDeletionFromSceneCleanupCB,
                           hook="preventMaterialDeletionFromCleanUpSceneCommand",
                           owner="renderSetup")

     
    def _onNodeRemoved(self, obj, clientData):
        if obj == self.thisMObject():
            self.dispose()

    def dispose(self):
        self.clearAll()
        # remove all callbacks that have been registered
        for id in self._cbIds:
            OpenMaya.MMessage.removeCallback(id)
        for type, callback in self._callbacks.iteritems():
            sceneObservable.instance().unregister(type, callback)
        self._cbIds = []
        if not cmds.about(batch=True):
            cmds.callbacks(removeCallback=_preventDeletionFromSceneCleanupCB,
                           hook="preventMaterialDeletionFromCleanUpSceneCommand",
                           owner="renderSetup")

    def typeName(self):
        return RenderSetup.kTypeName

    def parent(self):
        """Returns None, as the render setup node is the root of the hierarchy."""

        return None

    def ancestors(self):
        """Returns a single-element deque with the render setup node itself."""
        return deque([self])

    @undo.chunk('Create and append a render layer')
    def createRenderLayer(self, renderLayerName):
        """ Create and append a new Render Layer """
        with profiler.ProfilerMgr('RenderSetup::createRenderLayer'):
            layer = renderLayer.create(renderLayerName)
            self.appendRenderLayer(layer)
            return layer

    def getRenderLayer(self, renderLayerName):
        """ Look for an existing render layer by name.

            @type renderLayerName: string
            @param renderLayerName: Name of render layer to look for
            @rtype: RenderLayer model instance
            @return: Found instance or throw an exception
        """
        if not renderLayerName:
            raise Exception(kInvalidRenderLayerName)

        modelRenderLayers = self.getRenderLayers()
        for modelRenderLayer in modelRenderLayers:
            if modelRenderLayer.name() == renderLayerName:
                return modelRenderLayer

        raise Exception(kUnknownRenderLayer % renderLayerName)

    def getRenderLayers(self):
        return list(nodeList.forwardListGenerator(self))

    def appendRenderLayer(self, renderLayer):
        nodeList.append(self, renderLayer)

    def attachRenderLayer(self, pos, renderLayer):
        """ Attach a render layer at a specific position """
        nodeList.insert(self, pos, renderLayer)

    def detachRenderLayer(self, renderLayer):
        """ Detach a render layer whatever is its position """
        nodeList.remove(self, renderLayer)

    appendChild = appendRenderLayer
    attachChild = attachRenderLayer
    detachChild = detachRenderLayer
    getChildren = getRenderLayers

    # Ignore reference edits during this entire operation
    @guard.state(OpenMaya.MFnReference.ignoreReferenceEdits, OpenMaya.MFnReference.setIgnoreReferenceEdits, True)
    def switchToLayer(self, rLayer):
        """ Set the argument render layer as the visible render layer """
        if rLayer == None:
            rLayer = self.getDefaultRenderLayer()
        if not rLayer.isVisible() or rLayer.needsApplyUpdate:
            renderSetupPrivate.SwitchVisibleRenderLayerCmd.execute(rLayer)
        else:
            # if it is already visible then just update it to keep the legacy layers in sync.
            rLayer._updateLegacyRenderLayerVisibility()

    def switchToLayerUsingLegacyName(self, renderLayerName):
        """ Set the argument render layer as the visible render layer """

        with profiler.ProfilerMgr('RenderSetup::switchToLayerUsingLegacyName'):
            renderLayer = None
            if renderLayerName != "defaultRenderLayer":
                renderLayers = self.getRenderLayers()
                for layer in renderLayers:
                    if layer._getLegacyNodeName() == renderLayerName:
                        renderLayer = layer
                        break
                if renderLayer is None:
                    cmds.warning(kUnknownLegacyRenderLayer % renderLayerName)

            self.switchToLayer(renderLayer)
        
    def addActiveLayerObserver(self, obsMethod):
        self.activeLayerChangeObservable.addItemObserver(obsMethod)
        
    def removeActiveLayerObserver(self, obsMethod):
        self.activeLayerChangeObservable.removeItemObserver(obsMethod)

    def hasActiveLayerObserver(self, obsMethod):
        return self.activeLayerChangeObservable.hasItemObserver(obsMethod)

    def _notifyActiveLayerObservers(self):
        self.activeLayerChangeObservable.itemChanged()

    def getDefaultRenderLayer(self):
        return self._defaultRenderLayer

    def getVisibleRenderLayer(self):
        renderLayers = self.getRenderLayers()
        for rLayer in renderLayers:
            if rLayer.isVisible():
                return rLayer
        return self.getDefaultRenderLayer()

    def clearAll(self):
        """ Clear the render setup by deleting all its render layers """
        layers = self.getRenderLayers()
        for layer in layers:
            if layer.isVisible():
                self.switchToLayer(self.getDefaultRenderLayer())
            self.detachRenderLayer(layer)
            renderLayer.delete(layer)

    def _onMayaNodeAddedCB(self, obj):
        mayaObj = obj
        # When an interesting node is added to the scene we do two things.
        # We first send out a message to scene change observers.
        # And second, if if it is a DAG node we add it to an "_untitled_" collection
        # in the active layer.

        # During file import and file referencing, don't add to the default
        # collection.
        if OpenMaya1_0.MFileIO.isReadingFile():
            return

        # If it is not a transform node or we are in the middle of an undo or redo we exit early.
        if not mayaObj.hasFn(OpenMaya.MFn.kTransform) or \
                OpenMaya.MGlobal.isUndoing() or OpenMaya.MGlobal.isRedoing():
            return

        # Get the active layer if there is one
        visibleLayer = self.getVisibleRenderLayer()
        if visibleLayer != self.getDefaultRenderLayer():
            node = OpenMaya.MFnDagNode(mayaObj)
            
            if node.parentCount() == 0:
                # Node doesn't belong to the scene -> fullPathName is empty
                # This is true for the default directional light (created at render time)
                return

            # Local function checking if a DAG node is a light shape,
            # or a transform with only light shapes
            def _isLightNode(nodeObj):
                fn = OpenMaya.MFnDagNode(nodeObj)
                if fn.object().hasFn(OpenMaya.MFn.kTransform):
                    childCount = fn.childCount()
                    for i in range(childCount):
                        if not _isLightNode(fn.child(i)):
                            # At least one child is not a light shape
                            return False
                    # If we got here then all children were light shapes
                    return childCount>0
                else:
                    return cmds.getClassification(fn.typeName, satisfies='light')

            # Local function checking if a DAG node is a camera
            # attached to a light source (looking through camera)
            def _isLightCamera(nodeObj):
                fn = OpenMaya.MFnDagNode(nodeObj)
                if fn.object().hasFn(OpenMaya.MFn.kCamera) and fn.parentCount() == 1:
                    # Check if the parent transform has another child that is a light source
                    fn = OpenMaya.MFnDagNode(fn.parent(0))
                    if fn.object().hasFn(OpenMaya.MFn.kTransform) and fn.childCount() == 2:
                        fnChild0 = OpenMaya.MFnDependencyNode(fn.child(0))
                        fnChild1 = OpenMaya.MFnDependencyNode(fn.child(1))
                        return cmds.getClassification(fnChild0.typeName, satisfies='light') or \
                            cmds.getClassification(fnChild1.typeName, satisfies='light')
                return False

            # Ignore light cameras
            if _isLightCamera(mayaObj):
                return

            # Don't add lights to the default collection, but update 
            # layer membership to make the light visible
            if _isLightNode(mayaObj):
                visibleLayer._startMembershipUpdate()
                return
            
            if self._duplicated is not None:
                # append to duplicate array and add when duplicating is done
                self._duplicated.append(obj)
            else:
                visibleLayer.addDefaultMembers([obj])
                currentToolName = cmds.currentCtx()
                if currentToolName and "Create" in currentToolName and "Ctx" in currentToolName:
                    # Check if the current tool is an Interactive Creation Tool. If yes, 
                    # wait until object creation is completed and refresh (since object doesn't really exist until then)
                    def refresh():
                        visibleLayer.getDefaultCollection().getSelector().staticSelection.dirtyMissingCB()
                        visibleLayer.getDefaultCollection().itemChanged()
                    cmds.scriptJob(conditionTrue=["SomethingSelected", refresh], runOnce=True)
            
    def _beforeDuplicate(self, clientData):
        self._duplicated = []
    
    def _afterDuplicate(self, clientData):
        if len(self._duplicated) > 0:
            self.getVisibleRenderLayer().addDefaultMembers(self._duplicated)
        self._duplicated = None

    def _switchToLayerFileIO(self, layer, errMsg):
        try:
            self.switchToLayer(layer)
        except RuntimeError:
            OpenMaya.MGlobal.displayError(errMsg)
            OpenMaya1_0.MFileIO.setError()
            raise

    def _beforeLoadReferenceCB(self, referenceNode, resolvedRefPath):
        self.visibleLayerBeforeLoadReference = self.getVisibleRenderLayer()
        self._switchToLayerFileIO(
            None, _fileRefErrMsg(kBefore, kLoading, resolvedRefPath))
 
    def _afterLoadReferenceCB(self, referenceNode, resolvedRefPath):
        # When opening a file, child references will be loaded within the
        # scope of the file open, and this callback will be called.
        # However, this callback is intended to deal with a reload of a
        # child reference (after an unload), once file open is done.  It is
        # not intended to be called within the scope of a file open, at
        # which point there is no need to switch layers to update the
        # scene, which is not yet finished loading.
        if OpenMaya1_0.MFileIO.isOpeningFile():
            return

        # It could also affect the overrides from a visible render layer
        if self.visibleLayerBeforeLoadReference is not None:
            self.visibleLayerBeforeLoadReference._updateLegacyRenderLayerVisibility()
            self._switchToLayerFileIO(
                self.visibleLayerBeforeLoadReference,
                _fileRefErrMsg(kAfter, kLoading, resolvedRefPath))

            self.visibleLayerBeforeLoadReference = None

    def _beforeUnloadReferenceCB(self, referenceNode, resolvedRefPath):
        """ Before unloading a reference, preserve the visible render layer """
        self.visibleLayerBeforeUnloadReference = self.getVisibleRenderLayer()
        self._switchToLayerFileIO(None, _fileRefErrMsg(
            kBefore, kUnloading, resolvedRefPath))

    def _afterUnloadReferenceCB(self, referenceNode, resolvedRefPath):
        """ After unloading a reference, revert to the visible render layer
            and ensure the ownership consistency """

        # The reference unload potentially affects membership in all
        # layers, so clear out all render layer node membership caches.
        # This is an undesirable breach of encapsulation, as the node
        # membership cache is an implementation detail of the render layer.
        for rLayer in self.getRenderLayers():
            rLayer.clearMemberNodesCache()

        # It could also affect the overrides from a visible render layer
        if self.visibleLayerBeforeUnloadReference is not None:
            self.visibleLayerBeforeUnloadReference._updateLegacyRenderLayerVisibility()
            self._switchToLayerFileIO(
                self.visibleLayerBeforeUnloadReference,
                _fileRefErrMsg(kAfter, kUnloading, resolvedRefPath))
            
            self.visibleLayerBeforeUnloadReference = None

    def _beforeSaveSceneCB(self, clientData):
        """ Before saving the scene, force an update of the visible render layer
            to save it in a valid state """
        layer = self.getVisibleRenderLayer()
        if layer.needsRefresh():
            layer._updateLegacyRenderLayerVisibility()
            self.switchToLayer(layer)

    def _afterOpenCB(self, clientData):
        """If file references were loaded during file open in a visible render
        layer, refresh that layer."""

        # Render layer membership is stored as a connection from the member
        # node to the legacy render layer node.  Similarly, applied
        # overrides are connected to the attribute they override.  For
        # scenes without file references, these connections persist in the
        # saved file.
        # 
        # For scenes with file references, these connections are NOT saved
        # with the file: as per the file referencing architecture, they are
        # supposed to be connection reference edits stored with the file.
        # 
        # However, render setup blocks all reference edits during render
        # setup operations, as the information they contain is largely 
        # redundant with the render setup procedures themselves (e.g. render
        # layer membership, applied overrides).  Therefore, re-apply the
        # layer if loaded file references are present in the scene.

        layer = self.getVisibleRenderLayer()
        # Are we in a layer that isn't the default?
        if layer != self._defaultRenderLayer:
            # Are there any file reference nodes in our scene?
            refNodeNames = cmds.ls(type='reference')
            if refNodeNames:
                # Are there any loaded file reference nodes in our scene?
                refNodes = (commonUtils.nameToNode(r) for r in refNodeNames)
                loadedRef = next((r for r in refNodes if OpenMaya.MFnReference(r).isLoaded()), None)
                if loadedRef:
                    # backward comp after refactoring overrideManager, see overrideManager.py for details
                    if layer._backwardCompID is not None:
                        layer._transferAttributes()
                    # Unapply / reapply overrides.
                    layer.needsApplyUpdate = True
                    self.switchToLayer(layer)
        
    # Render setup interface as list of render layers.
    # These methods implement the list requirements for the nodeList module.
    #
    def _getFrontAttr(self):
        return RenderSetup.firstRenderLayer

    def _getBackAttr(self):
        return RenderSetup.lastRenderLayer

    def _getListItemsAttr(self):
        return RenderSetup.renderLayers

    def _preRenderLayerDelete(self, renderLayer):
        # Private interface for render layer to inform its parent that it
        # is about to be deleted.  Remove the render layer from our list.
        # If it was visible, set the default render layer as visible.

        if renderLayer.isVisible():
            self.switchToLayer(self.getDefaultRenderLayer())
        nodeList.remove(self, renderLayer)

    def _encodeProperties(self, dict):
        super(RenderSetup, self)._encodeProperties(dict)
        dict[jsonTranslatorGlobals.LAYERS_ATTRIBUTE_NAME] = jsonTranslatorUtils.encodeObjectArray(self.getRenderLayers())

    def _decodeChildren(self, children, mergeType, prependToName):
        jsonTranslatorUtils.decodeObjectArray(children, 
                                              jsonTranslatorUtils.MergePolicy(self.getRenderLayer, 
                                                                              lambda x,y: self.createRenderLayer(x), 
                                                                              mergeType, prependToName))
        
    def _decodeProperties(self, dict, mergeType, prependToName):
        super(RenderSetup, self)._decodeProperties(dict, mergeType, prependToName)
        if jsonTranslatorGlobals.LAYERS_ATTRIBUTE_NAME in dict:
            self._decodeChildren(dict[jsonTranslatorGlobals.LAYERS_ATTRIBUTE_NAME],
                                 mergeType, 
                                 prependToName)

    @undo.chunk('Import a complete render setup')
    def decode(self, encodedData, behavior=DECODE_AND_MERGE, prependToName=None):
    
        # Check that its a dictionary
        if type(encodedData) != dict:
            raise TypeError(jsonTranslatorGlobals.kUnknownData % str(encodedData))

        # Check that the dictionary is one related to the render setup
        if not self.kTypeName in encodedData:
            raise TypeError(jsonTranslatorGlobals.kUnknownKeys % encodedData.keys()[0])

        # Decode the content of the scene settings part
        if jsonTranslatorGlobals.SCENE_SETTINGS_ATTRIBUTE_NAME in encodedData:
            renderSettings.decode(encodedData[jsonTranslatorGlobals.SCENE_SETTINGS_ATTRIBUTE_NAME])

        if (jsonTranslatorGlobals.SCENE_AOVS_ATTRIBUTE_NAME in encodedData and 
            encodedData[jsonTranslatorGlobals.SCENE_AOVS_ATTRIBUTE_NAME] != dict()):
            aovs.decode(encodedData[jsonTranslatorGlobals.SCENE_AOVS_ATTRIBUTE_NAME], behavior)
            
        if behavior==DECODE_AND_OVERWRITE:
            self.clearAll()

        # Decode the content of the render setup part
        super(RenderSetup, self).decode(encodedData[self.kTypeName], behavior, 
                                        prependToName if behavior==DECODE_AND_RENAME else None)

    def encode(self, notes=None, includeSceneSettings=True):
        # Note: The includeSceneSettings option should always be true as the scene settings 
        #       should always be exported as part of the renderSetup export. Currently passing 
        #       a value of false for the includeSceneSettings option is reserved for test cases 
        #       that attempt to test pieces of the render setup export in isolation.
        encodedData = super(RenderSetup, self).encode(notes)

        if includeSceneSettings:
            encodedData[jsonTranslatorGlobals.SCENE_SETTINGS_ATTRIBUTE_NAME] = renderSettings.encode()
            encodedData[jsonTranslatorGlobals.SCENE_AOVS_ATTRIBUTE_NAME] = aovs.encode()

        return encodedData

    @undo.chunk('Accept the last import')
    def acceptImport(self):
        for renderLayer in self.getRenderLayers():
            renderLayer.acceptImport()

    def isAcceptableChild(self, modelOrData):
        """ Check if the model can be a child of the render setup root. """
        return modelOrData.typeName() == renderLayer.RenderLayer.kTypeName

class RenderSetupIssuesObservable(observable.Observable):
    '''Class to add render setup "general" issues (see issue.py).
    When there are issues, render setup shows an issue button. The callback is called on click and should provide
    an explanation of the issue and propose a way for the user to resolve it.'''
    
    _instance = None
    
    def __init__(self):
        if RenderSetupIssuesObservable._instance:
            raise RuntimeError("RenderSetupIssuesObservable is a singleton")
        super(RenderSetupIssuesObservable, self).__init__()
        self._issues = []
    
    @staticmethod
    def instance():
        if not RenderSetupIssuesObservable._instance:
            RenderSetupIssuesObservable._instance = RenderSetupIssuesObservable()
        return RenderSetupIssuesObservable._instance
    
    def hasIssues(self):
        return len(self._issues) > 0
    
    def addIssue(self, issue):
        if issue not in self._issues:
            self._issues.append(issue)
        self.itemChanged()
    
    def getIssue(self):
        return self._issues[0] if self.hasIssues() else None
    
    def removeIssue(self, issue):
        if issue in self._issues:
            self._issues.remove(issue)
        self.itemChanged()
    
    def resolveIssue(self):
        issue = self.getIssue()
        if issue and issue.resolve():
            self.removeIssue(issue)
        self.itemChanged()
    
    def clear(self):
        self._issues = []
        self.itemChanged()

def hasInstance():
    """ Return true if the render setup node exists """

    # If name-based lookup is a bottleneck, could have a render setup
    # cache, at the expense of render setup node lifescope management
    # complexity, since the cache should not prevent a render setup node
    # from being removed from the graph, nor should it be stale in such a
    # case.  PPT, 5-May-2015.
    return commonUtils.nameToNode(_RENDER_SETUP_NAME) is not None

@namespace.root
def _createInstance():
    fn = OpenMaya.MFnDependencyNode()
    renderSetupObj = fn.create(RenderSetup.kTypeId, _RENDER_SETUP_NAME)

    if ':' + fn.name() != _RENDER_SETUP_NAME:
        exceptionInfo = (RenderSetup.kTypeName, _RENDER_SETUP_NAME)
        raise ValueError(kRenderSetupNodeNameMismatch % exceptionInfo)

    _subject.renderSetupAdded()
    return renderSetupObj

def instance():
    """Return the render setup singleton node, creating it if required."""

    # If name-based lookup is a bottleneck, could have a render setup
    # cache, at the expense of render setup node lifescope management
    # complexity, since the cache should not prevent a render setup node
    # from being removed from the graph, nor should it be stale in such a
    # case.  PPT, 5-May-2015.
    renderSetupObj = commonUtils.nameToNode(_RENDER_SETUP_NAME)
    if not renderSetupObj:
        # No renderSetup node, create one
        # Creation of render setup node singleton must not affect
        # undo stack, disable it for the creation only
        swf = cmds.undoInfo(query=True, stateWithoutFlush=True)
        try:
            cmds.undoInfo(stateWithoutFlush=False)
            renderSetupObj = _createInstance()
        finally:
            cmds.undoInfo(stateWithoutFlush=swf)

    fn = OpenMaya.MFnDependencyNode(renderSetupObj)
    # If renderSetup node isn't the proper type, blow up.
    if fn.typeId != RenderSetup.kTypeId:
        exceptionInfo = (_RENDER_SETUP_NAME, RenderSetup.kTypeName)
        raise TypeError(kRenderSetupNodeTypeMismatch % exceptionInfo)

    return fn.userNode()

# Variables managed by the load & unload of the render setup plugin 
_autoAdjustements = False
_subject = None


class _Subject(object):
    """Subject class to observe overall render setup behavior.

    The renderSetup._Subject class is observed for render setup creation,
    deletion, and other overall events.  See

    https://en.wikipedia.org/wiki/Observer_pattern

    for more information on the Observer pattern."""

    def __init__(self):
        super(_Subject, self).__init__()
        self._observers = []

        self._cbIds = []
        cbArgs = [(OpenMaya.MSceneMessage.kBeforeNew, self._beforeNewCb,
                   'before new'),
                  (OpenMaya.MSceneMessage.kBeforeOpen, self._beforeOpenCb, 
                   'before open'),
                  (OpenMaya.MSceneMessage.kAfterOpen, self._afterOpenCb, 
                   'after open'),
                  (OpenMaya.MSceneMessage.kAfterNew, self._afterNewCb, 
                   'after open')]

        for (msg, cb, data) in cbArgs:
            self._cbIds.append(
                OpenMaya.MSceneMessage.addCallback(msg, cb, data))

    def finalize(self):
        OpenMaya.MMessage.removeCallbacks(self._cbIds)
        self._cbIds = []

    def _beforeNewCb(self, data):
        global _beforeNewCbCalled
        _beforeNewCbCalled = True

        if hasInstance():
            self.renderSetupPreDelete()
        # Render setup hack for 2016_R2.  See MAYA-65530.
        # Required for file new, because we can be deleting a scene where
        # unconnectable attributes are connected.
        os.environ['MAYA_RENDER_SETUP_OVERRIDE_CONNECTABLE'] = '1'

    def _beforeOpenCb(self, data):
        if hasInstance():
            self.renderSetupPreDelete()
        # Render setup hack for 2016_R2.  See MAYA-65530.
        os.environ['MAYA_RENDER_SETUP_OVERRIDE_CONNECTABLE'] = '1'

    def _afterOpenCb(self, data):
        # If we have a render setup node after file open, it's a new render
        # setup node by definition, so tell observers about it.
        if hasInstance():
            self.renderSetupAdded()
        # Render setup hack for 2016_R2.  See MAYA-65530.
        if 'MAYA_RENDER_SETUP_OVERRIDE_CONNECTABLE' in os.environ:
            del os.environ['MAYA_RENDER_SETUP_OVERRIDE_CONNECTABLE']

    def _afterNewCb(self, data):
        global _beforeNewCbCalled

        # Workaround to MAYA-65920: detect and avoid illegal callback sequence.
        if not _beforeNewCbCalled:
            return

        _beforeNewCbCalled = False

        # Render setup hack for 2016_R2.  See MAYA-65530.
        if 'MAYA_RENDER_SETUP_OVERRIDE_CONNECTABLE' in os.environ:
            del os.environ['MAYA_RENDER_SETUP_OVERRIDE_CONNECTABLE']
        
    def renderSetupAdded(self):
        """Call the renderSetupAdded() methods on render setup observers.

        The order in which observers are called is not specified."""
        conversion.Observer2016R2.instance().activate()
        
        self._cleanObservers()

        for o in self._observers:
            o().renderSetupAdded()
        
    def renderSetupPreDelete(self):
        """Call the renderSetupPreDelete() methods on render setup observers.

        The order in which observers are called is not specified."""
        conversion.Observer2016R2.instance().deactivate()
        
        if hasInstance():
            # Reset the master scene visibility upon deletion
            instance().switchToLayer(None)
            # Clean the model and remove model's callbacks
            instance().dispose()

        # Stop listening to any scene changes
        sceneObservable.instance().deactivate()
        localOverride.ExportListener.deleteInstance()
        
        self._cleanObservers()

        for o in self._observers:
            o().renderSetupPreDelete()

    def _cleanObservers(self):
        # Clean up zombie observers.
        self._observers = [o for o in self._observers if o() is not None]

    def addObserver(self, obs):
        """Add a render setup observer.

        Observers are kept as weak references.  The order in which
        observers are called is unspecified."""

        self._observers.append(weakref.ref(obs))

    def removeObserver(self, obs):
        """Remove an observer from this list.

        Observers are kept as weak references.  ValueError is raised by the 
        remove listItem method if the argument observer is not found."""

        self._observers.remove(weakref.ref(obs))

    def clearObservers(self):
        self._observers[:] = []


def initialize():
    # Only intended to be called by the plugin initialization, to
    # initialize the render setup model.
    global _subject

    _subject = _Subject()
    
    
    # Disable the auto adjustment of the legacy render layers to avoid edits on some overriden attributes
    # as it conflicts with the new render layer mechanism.
    # Refer to the Maya 2016 documentation related to 'Auto Overrides'
    # http://help.autodesk.com/view/MAYAUL/2016/ENU/?guid=GUID-61E6243A-9EE1-402C-9946-08E11AEFA571
    # Refer to MAYA-60084
    # 
    global _autoAdjustements
    _autoAdjustements = cmds.editRenderLayerGlobals(query=True, enableAutoAdjustments=True)
    cmds.editRenderLayerGlobals(enableAutoAdjustments=False)

    userPrefs.initialize()

def finalize():
    # Only intended to be called by the plugin finalization, to
    # finalize the render setup model.
    global _subject

    _subject.finalize()
    del _subject
    
    # Revert the auto adjustment to its original status
    global _autoAdjustements
    cmds.editRenderLayerGlobals(enableAutoAdjustments=_autoAdjustements)


def addObserver(obs):
    """Add a render setup observer.

    Observers are kept as weak references.  The order in which
    observers are called is unspecified."""

    _subject.addObserver(obs)

def removeObserver(obs):
    """Remove an observer from this list.

    Observers are kept as weak references.  ValueError is raised by the 
    remove listItem method if the argument observer is not found."""

    _subject.removeObserver(obs)


_mplugin = None

def getClassification(type):
    # We use the 'hidden' classification string for render setup nodes
    # unless specified otherwise in the classifications dictionary
    classifs = ['hidden']
    
    if type.kTypeId.id() in (typeIDs.connectionOverride.id(), typeIDs.materialOverride.id(), typeIDs.shaderOverride.id()):
        # The connection override needs to be classified as a render node in order 
        # to have the map button visible for its value attribute in the UI, 
        # so that connections can be made to it.
        classifs.append('rendernode')
    
    drawClassification = shadingNodes.getDrawdbClassification(type.kTypeId.id())
    if drawClassification is not None:
        classifs.append(drawClassification)
    
    return ':'.join(classifs)

def setPluginObject(mplugin):
    global _mplugin
    _mplugin = mplugin

def registerNode(type):
    try:
        global _mplugin
        _mplugin.registerNode(type.kTypeName, type.kTypeId, type.creator, type.initializer, OpenMaya.MPxNode.kDependNode, getClassification(type))
    except:
        OpenMaya.MGlobal.displayError(kRegisterFailed % type.kTypeName)

def unregisterNode(type):
    try:
        global _mplugin
        _mplugin.deregisterNode(type.kTypeId)
    except:
        OpenMaya.MGlobal.displayError(kUnregisterFailed % type.kTypeName)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
