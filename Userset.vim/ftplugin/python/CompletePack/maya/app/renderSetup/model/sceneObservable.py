'''
    This module handles scene observation.
    
    The scene observable is a central point of observation.
    It is the one actually Maya scene changes events and it forwards 
    them to the registered callbacks when global observation is enabled (sceneObserversEnabled).
'''

import maya.app.renderSetup.model.observable as observable
import maya.app.renderSetup.model.utils as utils
import maya.app.renderSetup.common.guard as guard

import maya.api.OpenMaya as OpenMaya
import maya.OpenMaya as OpenMaya1_0




_renderSetup_sceneObserversEnabled = True

def enableSceneObservers(value):
    global _renderSetup_sceneObserversEnabled
    _renderSetup_sceneObserversEnabled = value

def sceneObserversEnabled():
    global _renderSetup_sceneObserversEnabled
    return _renderSetup_sceneObserversEnabled

def isInSceneChangeCallback():
    return instance().isInSceneChangeCallback()

class SceneObservable(object):

    # Callbacks forward the arguments received from the Maya callback.  In the
    # case of file referencing callbacks, the arguments are forwarded in string
    # form.  clientData is not forwarded, since it's always None.
    NODE_ADDED         = 'NodeAdded'  # args = obj
    NODE_REMOVED       = 'NodeRemoved'  # args = obj
    NODE_RENAMED       = 'NodeRenamed'  # args = obj, oldName
    NODE_REPARENTED    = 'NodeReparented'  # args = msgType, child, parent
    CONNECTION_CHANGED = 'ConnectionChanged'  # args = srcPlug, dstPlug, made
    REFERENCE_LOADED   = 'ReferenceLoaded'  # args = reference node name, resolvedRefPath string
    REFERENCE_UNLOADED = 'ReferenceUnloaded'  # args = reference node name, resolvedRefPath string
    REFERENCE_REMOVED  = 'ReferenceRemoved'  # No args.
    REFERENCE_CREATED  = 'ReferenceCreated'  # args = reference node name, resolvedRefPath string.
    BEFORE_REFERENCE_LOAD = 'BeforeReferenceLoad'  # args = reference node name, resolvedRefPath string
    BEFORE_REFERENCE_UNLOAD = 'BeforeReferenceUnload'  # args = reference node name, resolvedRefPath string
    BEFORE_REFERENCE_REMOVE = 'BeforeReferenceRemove'  # args = reference node name, resolvedRefPath string
    BEFORE_REFERENCE_CREATE = 'BeforeReferenceCreate'  # No args.

    # The selector needs to register to all the scene changes.
    ALL_EVENTS         = 'AllSceneEvents' # args = eventType and args associated with this eventType


    def __init__(self):
        self._observers = None
        self._isInSceneChangeCallback = False
        self._cbIds = []
        # workaround to avoid unwanted notifications on nodes that are not yet done being created
        self._aboutToCreate = None
        # Maya does not send load / unload notifications on reference add /
        # remove.  Do so ourselves, and keep track of the reference information.
        self._refInfo = None
        self.activate()
    
    def _enabled(f):
        '''Decorator that calls the decorated function only if scene observation is enabled.'''
        def wrapper(*args, **kwargs):
            if sceneObserversEnabled():
                return f(*args, **kwargs)
        return wrapper

    def isInSceneChangeCallback(self):
        return self._isInSceneChangeCallback
    
    def __del__(self):
        self.deactivate()

    def activated(self):
        return self._observers is not None

    def activate(self):
        '''Create callbacks to listen to scene changes.'''
        if self.activated():
            return
        self._aboutToCreate = set()
        
        self._observers = { key:observable.Observable() for key in [SceneObservable.ALL_EVENTS,
                                                                    SceneObservable.NODE_ADDED,
                                                                    SceneObservable.NODE_REMOVED,
                                                                    SceneObservable.NODE_RENAMED,
                                                                    SceneObservable.NODE_REPARENTED,
                                                                    SceneObservable.CONNECTION_CHANGED,
                                                                    SceneObservable.BEFORE_REFERENCE_LOAD,
                                                                    SceneObservable.REFERENCE_LOADED,
                                                                    SceneObservable.BEFORE_REFERENCE_UNLOAD,
                                                                    SceneObservable.REFERENCE_UNLOADED,
                                                                    SceneObservable.BEFORE_REFERENCE_REMOVE,
                                                                    SceneObservable.REFERENCE_REMOVED,
                                                                    SceneObservable.BEFORE_REFERENCE_CREATE,
                                                                    SceneObservable.REFERENCE_CREATED] }

        self._cbIds = [ OpenMaya.MDGMessage.addNodeAddedCallback(self._nodeAddedCB, "dependNode"),
                        OpenMaya.MDGMessage.addNodeRemovedCallback(self._nodeRemovedCB, "dependNode"),
                        OpenMaya.MNodeMessage.addNameChangedCallback(OpenMaya.MObject.kNullObj, self._nodeRenamedCB),
                        OpenMaya.MDGMessage.addConnectionCallback(self._connectionChangedCB) ]
        
        dagCallbacks = { 
            OpenMaya.MDagMessage.kChildAdded, 
            OpenMaya.MDagMessage.kChildRemoved, 
            OpenMaya.MDagMessage.kInstanceAdded, 
            OpenMaya.MDagMessage.kInstanceRemoved }
        
        for type in dagCallbacks:
            self._cbIds.append(OpenMaya.MDagMessage.addDagCallback(type, self._nodeReparentedCB))
                        
        # All the following Maya core callbacks are exposed in this class'
        # interface with identical semantics, except for
        # kAfterCreateReferenceAndRecordEdits.  This last callback is used
        # to provide the reference node and reference path arguments for our
        # reference created notification; this data is not provided by the
        # Maya core callback.  It is also used as an implementation detail
        # of our support for generating before and after load reference
        # messages on create reference, which the Maya core does not provide.
        referenceCallbacks = {
            OpenMaya.MSceneMessage.kBeforeLoadReference   : self._beforeLoadReferenceCB,
            OpenMaya.MSceneMessage.kAfterLoadReference    : self._afterLoadReferenceCB,
            OpenMaya.MSceneMessage.kBeforeUnloadReference : self._beforeUnloadReferenceCB,
            OpenMaya.MSceneMessage.kAfterUnloadReference  : self._afterUnloadReferenceCB,
            OpenMaya.MSceneMessage.kBeforeRemoveReference : self._beforeRemoveReferenceCB,
            OpenMaya.MSceneMessage.kAfterCreateReferenceAndRecordEdits : self._afterCreateReferenceAndRecordEditsCB } 
        
        for type, callback in referenceCallbacks.iteritems():
            self._cbIds.append(OpenMaya.MSceneMessage.addReferenceCallback(type, callback))
            
        for msg in (OpenMaya.MSceneMessage.kBeforeNew, OpenMaya.MSceneMessage.kBeforeOpen):
            self._cbIds.append(OpenMaya.MSceneMessage.addCallback(msg, self._beforeNewCb, None))
    
        # After remove reference can't receive the reference node as an
        # argument to the callback, since it's been removed.  Similar
        # argument for before create reference.
        basicCallbacks = {
            OpenMaya.MSceneMessage.kAfterRemoveReference : self._afterRemoveReferenceCB,
            OpenMaya.MSceneMessage.kBeforeCreateReference: self._beforeCreateReferenceCB }

        for type, callback in basicCallbacks.iteritems():
            self._cbIds.append(OpenMaya.MSceneMessage.addCallback(
                type, callback))

    def deactivate(self):
        '''Removes callbacks to listen to scene changes'''
        self._observers = None
        for id in self._cbIds:
            OpenMaya.MMessage.removeCallback(id)
        self._cbIds = []
    
    def register(self, eventType, observer):
        '''Add a callback for the given event(s).'''
        if not self.activated():
            self.activate()
        self._observers[eventType].addItemObserver(observer)

    def unregister(self, eventType, observer):
        '''Removes a callback for the given event(s).'''
        if not self.activated():
            return
        self._observers[eventType].removeItemObserver(observer)

    def _beforeNewCb(self, data):
        self.deactivate()
    
    @_enabled
    @guard.member('_isInSceneChangeCallback', True)
    def _notifyObservers(self, **kwArgs):
        if self.activated() and not OpenMaya1_0.MFileIO.isReadingFile() and not OpenMaya1_0.MFileIO.isReferencingFile():
            self._observers[SceneObservable.ALL_EVENTS].itemChanged(**kwArgs)
            eventType = kwArgs['eventType']
            del kwArgs['eventType']
            self._observers[eventType].itemChanged(**kwArgs)

    def _isValid(self, obj):
        '''Check if obj is a valid object to send notifications for.'''
        return OpenMaya.MObjectHandle(obj).hashCode() not in self._aboutToCreate and utils.canOverrideNode(obj)

    @_enabled
    def _nodeAddedCB(self, obj, clientData):
        self._aboutToCreate.difference_update((OpenMaya.MObjectHandle(obj).hashCode(),))
        if not utils.canOverrideNode(obj):
            return
        self._notifyObservers(eventType=SceneObservable.NODE_ADDED, obj=obj)
    
    @_enabled
    def _nodeRemovedCB(self, obj, clientData):
        if not utils.canOverrideNode(obj):
            return
        self._notifyObservers(eventType=SceneObservable.NODE_REMOVED, obj=obj)

    @_enabled
    def _nodeRenamedCB(self, obj, oldName, clientData):
        # Note: The oldName is a node name and not an absolute path
        if len(oldName) == 0:
            # node name is never empty after the node is done being created
            # => if this happens, then we know this node is in process of being created
            # => ignore events to this node until it is created
            self._aboutToCreate.add(OpenMaya.MObjectHandle(obj).hashCode())
            return
        
        if not self._isValid(obj) or oldName==OpenMaya.MFnDependencyNode(obj).name():
            return
        self._notifyObservers(eventType=SceneObservable.NODE_RENAMED, obj=obj, oldName=oldName)
    
    @_enabled
    def _nodeReparentedCB(self, msgType, child, parent, clientData):
        if not self._isValid(child.node()):
            return
        self._notifyObservers(eventType=SceneObservable.NODE_REPARENTED, msgType=msgType, child=child, parent=parent)

    @_enabled
    def _connectionChangedCB(self, srcPlug, dstPlug, made, clientData):
        if not utils.canOverrideNode(srcPlug.node()) or not utils.canOverrideNode(dstPlug.node()):
            return
        self._notifyObservers(eventType=SceneObservable.CONNECTION_CHANGED, srcPlug=srcPlug, dstPlug=dstPlug, made=made)
    
    @_enabled
    def _beforeLoadReferenceCB(self, referenceNode, resolvedRefPath, clientData):
        self._notifyObservers(
            eventType=SceneObservable.BEFORE_REFERENCE_LOAD, 
            referenceNode=OpenMaya.MFnReference(referenceNode).name(), 
            resolvedRefPath=resolvedRefPath.expandedFullName())

    @_enabled
    def _afterLoadReferenceCB(self, referenceNode, resolvedRefPath, clientData):
        self._notifyObservers(
            eventType=SceneObservable.REFERENCE_LOADED,
            referenceNode=OpenMaya.MFnReference(referenceNode).name(),
            resolvedRefPath=resolvedRefPath.expandedFullName())

    @_enabled
    def _beforeUnloadReferenceCB(self, referenceNode, resolvedRefPath, clientData):
        self._notifyObservers(
            eventType=SceneObservable.BEFORE_REFERENCE_UNLOAD,
            referenceNode=OpenMaya.MFnReference(referenceNode).name(),
            resolvedRefPath=resolvedRefPath.expandedFullName())

    @_enabled
    def _afterUnloadReferenceCB(self, referenceNode, resolvedRefPath, clientData):
        self._notifyObservers(
            eventType=SceneObservable.REFERENCE_UNLOADED, 
            referenceNode=OpenMaya.MFnReference(referenceNode).name(), 
            resolvedRefPath=resolvedRefPath.expandedFullName())
        
    @_enabled
    def _beforeRemoveReferenceCB(self, referenceNode, resolvedRefPath, clientData):
        refPath = resolvedRefPath.expandedFullName()
        refFn = OpenMaya.MFnReference(referenceNode)
        refName = refFn.name()
        self._notifyObservers(
            eventType=SceneObservable.BEFORE_REFERENCE_REMOVE, 
            referenceNode=refName, resolvedRefPath=refPath)

        # If reference was loaded, send an unload notification as well.
        # Maya does not do this.
        if refFn.isLoaded():
            self._notifyObservers(
                eventType=SceneObservable.BEFORE_REFERENCE_UNLOAD, 
                referenceNode=refName, resolvedRefPath=refPath)

            # Capture name, path of reference to pass it to the after
            # remove reference callback.
            self._refInfo = (refName, refPath)

    @_enabled
    def _afterRemoveReferenceCB(self, clientData):

        # If we sent a before unload notification on remove reference, send an
        # after unload notification as well.
        if self._refInfo is not None:
            (refName, refPath) = self._refInfo
            self._notifyObservers(eventType=SceneObservable.REFERENCE_UNLOADED,
                                  referenceNode=refName,
                                  resolvedRefPath=refPath)
            self._refInfo = None

        self._notifyObservers(eventType=SceneObservable.REFERENCE_REMOVED)
        
    @_enabled
    def _beforeCreateReferenceCB(self, clientData):
        self._notifyObservers(eventType=SceneObservable.BEFORE_REFERENCE_CREATE)
        
    @_enabled
    def _afterCreateReferenceAndRecordEditsCB(
            self, referenceNode, resolvedRefPath, clientData):
        # Contrary to API documentation, creation of a non-deferred
        # reference does NOT send reference loaded notifications.  Fake it
        # here: the plain after create reference notification bizarrely
        # doesn't have the reference node and resolved path arguments, so
        # use the "record edits" version.
        refPath = resolvedRefPath.expandedFullName()
        refFn = OpenMaya.MFnReference(referenceNode)
        refName = refFn.name()
        if refFn.isLoaded():
            # Awkwardly, we generate the before reference loaded message
            # AFTER the reference is actually loaded.  This is because we
            # are compensating for the fact that the Maya core does not
            # generate these messages, and must use the after create
            # reference support to do so.  The before create reference
            # message does not provide the reference node or reference
            # path, since they haven't been created yet.
            self._notifyObservers(
                eventType=SceneObservable.BEFORE_REFERENCE_LOAD,
                referenceNode=refName, resolvedRefPath=refPath)
            self._notifyObservers(
                eventType=SceneObservable.REFERENCE_LOADED,
                referenceNode=refName, resolvedRefPath=refPath)
        
        self._notifyObservers(
            eventType=SceneObservable.REFERENCE_CREATED,
            referenceNode=refName, resolvedRefPath=refPath)

_sceneObservable = None

def instance():

    global _sceneObservable
    
    if _sceneObservable is None:
        _sceneObservable = SceneObservable()

    return _sceneObservable
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
