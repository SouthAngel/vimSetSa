"""Override node classes and utility functions.

   This module provides the override base and concrete classes, as well as
   utility functions to operate on overrides."""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya
import maya.app.renderSetup.model.localOverride as localOverride

import maya.app.renderSetup.common.utils as commonUtils
import maya.app.renderSetup.model.utils as utils
import maya.app.renderSetup.model.namespace as namespace
import maya.app.renderSetup.model.typeIDs as typeIDs
import maya.app.renderSetup.model.applyOverride as applyOverride
import maya.app.renderSetup.model.undo as undo
import maya.app.renderSetup.model.enabled as enabled
import maya.app.renderSetup.model.childNode as childNode
import maya.app.renderSetup.model.plug as plug
import maya.app.renderSetup.model.sceneObservable as sceneObservable
import maya.app.renderSetup.model.context as context
import weakref
import itertools

import maya.app.renderSetup.common.guard as guard
from collections import namedtuple
from maya.app.renderSetup.model.renderSetupPrivate import PostApplyCmd

# Errors
kUnapplyCmdPrivate = maya.stringTable['y_override.kUnapplyCmdPrivate' ]
kUnconnectableAttr = maya.stringTable['y_override.kUnconnectableAttr' ]
kUnfinalized       = maya.stringTable['y_override.kUnfinalized'       ]
kMissingDependencies = maya.stringTable['y_override.kMissingDependencies' ]

def fillVector(value, dimension):
    """Return a list of specified dimension initialized with value.

    If dimension is 0, return the argument value as a scalar."""

    return value if dimension == 0 else [value] * dimension

class Property(namedtuple('Property', 'name encode decode')):
    '''Namedtuple to hold what is needed to encode a property (name, encode function, decode function).
    'name' will be the name of the given attribute (MObject).'''
    def __new__(cls, attr, encode, decode):
        return cls.__bases__[0].__new__(cls, OpenMaya.MFnAttribute(attr).name, encode, decode)

class LeafClass(object):
    """ To be used by leaf classes only """
    def isAbstractClass(self):
        # False means that the class is a leaf class
        return False

def valid(f):
    '''Decorator that calls the decorated method if and only if self.isValid() evaluates to True.'''
    def validityCheck(*args, **kwargs):
        if args[0].isValid():
            f(*args, **kwargs)
    return validityCheck

def finalizationChanged(f):
    '''Decorator for functions that may change the finalization of an override (decode, finalize).
    This will ensure that if the layer in which this override lives is visible, then the override
    should be unapplied and reapplied with the new finalization.'''
    def wrapper(*args, **kwargs):
        # when the first opened chunk is empty, the used chunk string is the next non-empty one
        with undo.CtxMgr(''):
            self = args[0] # self = Override
            isApplied = self.isApplied()
            if isApplied and self.isValid():
                # override was already finalized and applied
                # must unapply before we refinalize
                UnapplyCmd.execute(self)
            out = f(*args, **kwargs)
            if isApplied and self.isValid():
                PostApplyCmd.execute(self)
            return out
    return wrapper

class OverridePlugHandle(object):
    '''
    Plug class that handles dynamic plug and missing dependencies.
    
    Has functions for finalization, encoding, decoding and handling missing dependencies.
    
    Finalization creates a dynamic attribute based on another plug. It has 3 available modes:
     - kModeClone clones the input plug
     - kModeMultiply will have the same arity as the input plug but has float scalar units
       (can be used to multiply input's plug type by a scalar)
     - kModeOffset clones the input plug but with more flexible min/max, softMin/softMax
       (can be used to offset input's plug type by some value in the same units)
       
    Encode/decode creates/read dictionary of attributes that defines the plug attributes.
    
    Handles missing dependency:
     If the plug is decoded and can't find the source plug it's supposed to connect to, then
     it has a missing dependency. It creates a dynamic string attribute containing the name of the
     missing dependency (this allows the "missing dependency" state to persist on file new) and it 
     starts listening to scene changes to find the missing dependency and connect to it if it's created.
    
    '''
    
    # finalization modes
    kModeClone = 0
    kModeOffset = 1
    kModeMultiply = 2
    
    def __init__(self, ovr, longName, shortName, mode=kModeClone):
        self.ovr = weakref.ref(ovr)
        self.handle = OpenMaya.MObjectHandle(ovr.thisMObject())
        self.longName = longName
        self.shortName = shortName
        self._attr = None
        self._attrDependency = None
        self._mode = mode
        
        # MObject is not yet valid in override's postConstructor (when this is created)
        # => can't search for a plug on it yet
        # => _uninitialized is used to so that we will search _attr and _attrDependency on query (later when MObject becomes valid)
        # Doing this avoids searching for the plug every time self._attr is None. 
        # None is a valid value for self._attr (when no dynamic attr was created yet).
        # _attrChanged will make sure that self._attr is correctly updated when it needs to
        # (same for attrDependency)
        self._uninitialized = True
        self.attrChangedID = None
        
    def update(self):
        self._attrChanged()
        self._attrDependencyChanged()
        self._uninitialized = False
        
    def _attrChanged(self):
        plg = plug.findPlug(self.handle.object(), self.longName)
        self._attr = plg.plug.attribute() if plg else None
    
    def _attrDependencyChanged(self):
        plg = plug.findPlug(self.handle.object(), self.longName+"Dependency")
        self._attrDependency = plg.plug.attribute() if plg else None
        if self._attrDependency is not None:
            self._startListening()
        else:
            self._stopListening()

    @property
    def attr(self):
        if self._uninitialized:
            self.update()
        return self._attr
    
    @property
    def attrDependency(self):
        if self._uninitialized:
            self.update()
        return self._attrDependency
    
    def node(self):
        return OpenMaya.MFnDependencyNode(self.handle.object())
    
    def name(self):
        return self.node().name()+"."+self.longName
    
    def getPlug(self):
        '''Return the Plug object (plug.py). (this is not a MPlug)'''
        return plug.Plug(self.handle.object(), self.attr) if self.attr else None
    
    def isFinalized(self):
        return self.attr is not None
    isValid = isFinalized
    
    def hasMissingDependency(self):
        return self.attrDependency is not None
    
    def getMissingDependency(self):
        return OpenMaya.MPlug(self.handle.object(), self.attrDependency).asString()
    
    def setMissingDependency(self, source):
        with undo.NotifyCtxMgr('Set missing dependency', self._attrDependencyChanged):
            if source is not None:
                if not self.attrDependency:
                    cmds.addAttr(self.node().name(), longName=self.longName+"Dependency", shortName=self.shortName+"Dep", dt="string")
                cmds.setAttr(self.node().name()+"."+self.longName+"Dependency", source, type="string")
            elif self.attrDependency:
                cmds.deleteAttr(OpenMaya.MPlug(self.handle.object(), self.attrDependency).name())
    
    # observation functions (only when there's a missing dependency)
    @utils.notUndoRedoing
    def _onAttrChanged(self, msg, plg, otherPlug, clientData):
        if plg == self.getPlug().plug and ((msg & OpenMaya.MNodeMessage.kConnectionMade and plg.isDestination) or msg & OpenMaya.MNodeMessage.kAttributeSet):
            self.setMissingDependency(None)
    
    @utils.notUndoRedoing      
    def _onNodeAdded(self, obj):
        if OpenMaya.MFnDependencyNode(obj).name() == self.getMissingDependency().split('.')[0]:
            # FIXME: Connection should not be deferred. MAYA-75122
            OpenMaya.MGlobal.displayInfo("Missing dependency '%s' found for plug '%s', connecting to it." % (self.getMissingDependency(), self.name()))
            cmd = ( "import maya.cmds as cmds\n"
                    "if not cmds.connectionInfo('{dst}', isDestination=True):\n"
                    "    cmds.connectAttr('{src}', '{dst}')").format(dst=self.name(), src=self.getMissingDependency())
            cmds.evalDeferred(cmd)
            
    def _onNodeRenamed(self, obj, oldName):
        self._onNodeAdded(obj)
    
    def _startListening(self):
        if not self.attrChangedID:
            sceneObservable.instance().register(sceneObservable.SceneObservable.NODE_ADDED, self._onNodeAdded)
            sceneObservable.instance().register(sceneObservable.SceneObservable.NODE_RENAMED, self._onNodeRenamed)
            self.attrChangedID = OpenMaya.MNodeMessage.addAttributeChangedCallback(self.handle.object(), self._onAttrChanged, None)
            self.ovr().itemChanged() # (ovr status changed)
    
    def _stopListening(self):
        if self.attrChangedID:
            sceneObservable.instance().unregister(sceneObservable.SceneObservable.NODE_ADDED, self._onNodeAdded)
            sceneObservable.instance().unregister(sceneObservable.SceneObservable.NODE_RENAMED, self._onNodeRenamed)
            OpenMaya.MMessage.removeCallback(self.attrChangedID)
            self.attrChangedID = None
            self.ovr().itemChanged() # (ovr status changed)
    
    def getSource(self):
        plg = self.getPlug().plug
        return plg.source() if plg.isDestination else None
    
    def setSource(self, source):
        with undo.CtxMgr("Set source '%s' for plug '%s'" % (source, self.name())):
            if source is None or cmds.objExists(source):
                self.setMissingDependency(None)
                if source and not cmds.isConnected(source, self.getPlug().name):
                    cmds.connectAttr(source, self.getPlug().name, force=True)
            else:
                self.setMissingDependency(source)
                OpenMaya.MGlobal.displayWarning("Missing source dependency '%s' for plug '%s'" % (source, self.name()))
    
    def encode(self, dict):
        if self.isValid():
            dict[self.longName] = {}
            plg = self.getPlug()
            plg._encodeProperties(dict[self.longName])
            if plg.plug.isDestination:
                dict[self.longName]['source'] = plg.plug.source().name()
            elif self.hasMissingDependency():
                dict[self.longName]['source'] = self.getMissingDependency()
    
    def decode(self, dict):
        if self.longName not in dict:
            return
        with undo.CtxMgr("Decode plug '%s'" % self.name()):
            with undo.NotifyCtxMgr("Decode plug '%s'" % self.name(), self._attrChanged):
                if self.isFinalized():
                    # remove previous finalization to avoid setting incompatible type
                    cmds.deleteAttr(self.getPlug().name)
                # create new attribute
                plg = plug.Plug.createAttribute(self.handle.object(), self.longName, self.shortName, dict[self.longName])
            # set source if any
            self.setSource(dict[self.longName].get('source',None))
    
    def finalize(self, plg):            
        with undo.NotifyCtxMgr("Finalize plug '%s'" % self.name(), self._attrChanged):
            dim = plg.plug.numChildren() if plg.plug.isCompound else 0
            if self._mode == OverridePlugHandle.kModeMultiply:
                attrDefinition = {'type': fillVector('Float', dim), 'connectable': True, 'softMin':0, 'softMax':2}
                plg = plg.createAttribute(self.handle.object(), self.longName, self.shortName, attrDefinition)
                plg.value = fillVector(1,dim)
                
            elif self._mode == OverridePlugHandle.kModeOffset:
                newAttrLimits = None
                if plg.hasLimits:
                    def _getValue(key, attrLimits):
                        return attrLimits.get(key, None)
        
                    attrLimits = plg.getAttributeLimits()
        
                    newSoftMin = _getValue('min', attrLimits)
                    if newSoftMin is None:
                        newSoftMin = _getValue('softMin', attrLimits)
                    newSoftMax = _getValue('max', attrLimits)
                    if newSoftMax is None:
                        newSoftMax = _getValue('softMax', attrLimits)
        
                    if newSoftMin is not None and newSoftMax is not None:
                        delta = newSoftMax - newSoftMin
                        # Note: Do not set min and max to avoid fixed range,
                        #       the softMin and softMax allows to dynamically change the range.
                        newAttrLimits = {'min':None, 'softMin':-delta, 'softMax':delta, 'max':None}
                    else:
                        newAttrLimits = {'min':None, 'softMin':None, 'softMax':None, 'max':None}
                plg = plg.createAttributeFrom(self.handle.object(), self.longName, self.shortName, limits=newAttrLimits)
                plg.value = fillVector(0,dim)
                
            else: # OverridePlugHandle.kModeClone
                plg.cloneAttribute(self.handle.object(), self.longName, self.shortName)
        

class Override(childNode.TreeOrderedItem, childNode.ChildNode):
    """
    Override node base class.
    
    An override represents a non-destructive change to a scene property
    that can be reverted or disabled.  Render setup uses overrides to describe
    changes that apply in a single render layer, and are unapplied when
    switching to another render layer.  When working within a render layer, an
    override can be preserved but disabled, to remove its effect.

    The override node base class cannot be directly created in Maya.  It is
    derived from the ListItem base class, so that overrides can be inserted
    in a list."""

    kTypeId = typeIDs.override
    kTypeName = "override"

    # Attributes

    # Enabled behavior.  See enabled module for documentation.
    enabled       = OpenMaya.MObject()
    selfEnabled   = OpenMaya.MObject()
    parentEnabled = OpenMaya.MObject()

    # Attribute name on which to apply the override
    attrName = OpenMaya.MObject()
    attrLocal = OpenMaya.MObject()

    # Awkwardly, abstract base classes seem to need a creator method.
    @classmethod
    def creator(cls):
        return cls()

    @staticmethod
    def initializer():

        # An override is a collection list item.
        Override.inheritAttributesFrom(childNode.ChildNode.kTypeName)

        # Set up enabled attribute.
        enabled.initializeAttributes(Override)

        # The attribute name
        stringData = OpenMaya.MFnStringData().create('')
        strAttrFn = OpenMaya.MFnTypedAttribute()

        Override.attrName = strAttrFn.create(
            "attribute", "atr", OpenMaya.MFnData.kString, stringData)
        strAttrFn.writable = True
        strAttrFn.storable = True
        Override.addAttribute(Override.attrName)
        
        attrFn = OpenMaya.MFnNumericAttribute()
        Override.attrLocal = attrFn.create("localRender", "local", OpenMaya.MFnNumericData.kBoolean, 0)
        attrFn.writable = True
        attrFn.storable = True
        attrFn.keyable  = False
        Override.addAttribute(Override.attrLocal)
        Override.attributeAffects(Override.attrLocal, Override.enabled)
    
    def __init__(self):
        super(Override, self).__init__()
        self._enabledDirty = False
        self._callbackIds = []

    def postConstructor(self):
        # Call parent class postConstructor
        super(Override, self).postConstructor()

        # Listen to changes in the enabled attribute.
        self._callbackIds = enabled.addChangeCallbacks(self)

    def isAbstractClass(self):
        # Used only as base class, cannot be created.
        return True

    def typeId(self):
        return self.kTypeId

    def typeName(self):
        return self.kTypeName

    def _getInputAttr(self, attr, dataBlock=None):
        return dataBlock.inputValue(attr) if dataBlock else OpenMaya.MPlug(self.thisMObject(), attr)

    def _getEnabledPlug(self):
        return OpenMaya.MPlug(self.thisMObject(), Override.enabled)

    def _getSelfEnabledPlug(self):
        return OpenMaya.MPlug(self.thisMObject(), Override.selfEnabled)

    def _getAttrNamePlug(self):
        return OpenMaya.MPlug(self.thisMObject(), Override.attrName)

    def attributeName(self):
        return self._getAttrNamePlug().asString()

    def setAttributeName(self, attributeName):
        """Set the name of the attribute to be overridden."""
        if attributeName != self.attributeName():
            with undo.NotifyCtxMgr('Set attribute name', self.itemChanged):
                cmds.setAttr(
                    self.name() + '.attribute', attributeName, type='string')

    def attrValuePlugName(self):
        return self._getAttrValuePlug().name()

    def enabledChanged(self):
        self.itemChanged()

    def isEnabled(self):
        return self._getEnabledPlug().asBool()
    
    def isLocalRender(self, dataBlock=None):
        return self._getInputAttr(self.attrLocal, dataBlock).asBool()
    
    def setLocalRender(self, value):
        if value != self.isLocalRender():
            with undo.NotifyCtxMgr("Set Local Render", self.itemChanged):
                cmds.setAttr(self.name()+".localRender", 1 if value else 0)
        
    def isSelfEnabled(self, dataBlock=None):
        return self._getInputAttr(self.selfEnabled, dataBlock).asBool()

    def setSelfEnabled(self, value):
        if value != self.isSelfEnabled():
            # pulling isEnabled will trigger enabledChanged 
            # (no matter if enable output value has changed or not)
            with undo.NotifyCtxMgr("Set Override Enabled", self.isEnabled):
                cmds.setAttr(self.name()+".selfEnabled", 1 if value else 0)

    def isValid(self):
        return True
    
    def isApplied(self):
        layer = self.getRenderLayer()
        return layer and layer.isVisible()

    def updateOnEnabledChanged(self):
        """Does this override need an update when its enabled output changes?

        The base class behavior is that overrides need no update."""
        return False

    def getRenderLayer(self):
        parent = self.parent()
        return parent.getRenderLayer() if parent else None

    def getApplyOverrides(self):
        """Return the list of apply override nodes that correspond to this override."""

        # Our enabled plug's destinations are the apply nodes.
        overrideEnabledPlug = self._getEnabledPlug()
        applyEnabledPlugs = utils.plugDst(overrideEnabledPlug)

        if not applyEnabledPlugs:
            return []

        applyOverrides = []
        for applyEnabledPlug in applyEnabledPlugs:
            applyObj = applyEnabledPlug.node()
            fn = OpenMaya.MFnDependencyNode(applyObj)
            applyOverrides.append(fn.userNode())

        return applyOverrides

    def activate(self):
        # Listen to changes in the enabled attribute.
        if len(self._callbackIds) == 0:
            self._callbackIds = enabled.addChangeCallbacks(self)

    def deactivate(self):
        # Remove all callbacks.
        OpenMaya.MMessage.removeCallbacks(self._callbackIds)
        self._callbackIds = []
    
    def _properties(self):
        return (Property(*args) for args in (
                (self.selfEnabled, self.isSelfEnabled, self.setSelfEnabled),
                (self.attrName   , self.attributeName, self.setAttributeName),
                (self.attrLocal  , self.isLocalRender, self.setLocalRender)))

    def _encodeProperties(self, dict):
        super(Override, self)._encodeProperties(dict)
        for prop in self._properties():
            dict[prop.name] = prop.encode()

    def _decodeProperties(self, dict, mergeType, prependToName):
        super(Override, self)._decodeProperties(dict, mergeType, prependToName)
        for prop in self._properties():
            if prop.name in dict:
                prop.decode(dict[prop.name])

    def isAcceptableChild(self, model):
        """ Check if the model could be a child """
        return False

    def compute(self, plug, dataBlock):
        if plug == self.enabled:
            value = (not self.isLocalRender(dataBlock) or localOverride.enabled()) and \
                enabled.computeEnabled(self, dataBlock)
            enabled.setEnabledOutput(self, dataBlock, value)

class ValueOverride(Override):
    """
    Override node base class for all value overrides.
    """

    kTypeId = typeIDs.valueOverride
    kTypeName = "valueOverride"

    @staticmethod
    def initializer():
        ValueOverride.inheritAttributesFrom(Override.kTypeName)

    def __init__(self):
        super(ValueOverride, self).__init__()
    
    def _isApplicableTo(self, plg):
        """Verify if override is applicable to the given plug.
           Parameter can either be a OpenMaya.MPlug or a plug.Plug"""
        if isinstance(plg, OpenMaya.MPlug):
            plg = plug.Plug(plg)
        
        # override is applicable to plug if
        # plug is connectable and type compatible with override
        return plg.isConnectable and plg.accepts(self._getCompatibilityCheckPlug())
    
    def _targets(self, selectedNodeNames=None):
        '''Returns a generator over all the target plugs on which to apply the override.'''
        # If we weren't given node names to find targets for, get them from our
        # parent collection's selector.
        nodes = (commonUtils.nameToNode(name) for name in selectedNodeNames) \
                if selectedNodeNames is not None else \
                self.parent().getSelector().nodes()
        
        # Get the attribute to be overridden.
        attrName = self.attributeName()

        return itertools.ifilter(
            lambda plg: plg and OpenMaya.MFnAttribute(plg.attribute()).writable and self._isApplicableTo(plg), 
            (commonUtils.findPlug(node, attrName) for node in nodes))
    
    @valid
    @context.applyOverride
    def apply(self, selectedNodeNames=None):
        """Apply the override to selected node names.

        This method will apply the override as the highest-priority
        override on the attribute, for each selected node."""
        for target in self._targets(selectedNodeNames):
            self._applyOne(target)
    
    @context.applyOverride
    def reapply(self, overridden):
        '''Reapply the override on the overridden. Overridden is given in the format returned by
        getOverridden(). This is called when an override is reapplied when undoing its deletion.'''
        for o in overridden:
            self.applyInsertOne(*o)
        
    @valid
    @context.applyOverride
    def postApply(self):
        '''Post applies this override. This function may be called to apply the override
        after the layer was set visible. It allows inserting new overrides in the currently visible layer
        without the need to toggle visibility. For each plug target to override, it traverses the apply override 
        chain (if any) and inserts an apply override node at the right position (right before the next override 
        that affect the same target plug).'''
        for target in self._targets():
            for ao in applyOverride.reverseGenerator(target):
                if ao.override() > self:
                    target = ao.getOriginalPlug()
            self._applyOne(target)

    def _applyOne(self, plugToOverride):
        """Apply this override to a single plug."""
        
        # Create an apply override node.  This holds the connection to the
        # original source of the attribute (if any), and is chainable to
        # other apply override nodes (in the case of multiple overrides).
        applyOverrideName = '%s_%s' % (
            self.name(), plugToOverride.partialName(includeNodeName=True).replace('.','_'))
        apply = applyOverride.create(
            applyOverrideName, self._getApplyOverrideTypeId())

        # Record if the apply override node is applied to a node that is
        # not in the main scene.
        if OpenMaya.MFnDependencyNode(plugToOverride.node()).isFromReferencedFile:
            apply.setNotOnMainScene()

        with plug.UnlockedGuard(plugToOverride):
            # Wire up the three external node attributes of the override node:
            # 1) transfer the plug to be overridden to the apply override original
            #    input.
            utils.transferPlug(plugToOverride, apply.getOriginalPlug())
            # We must disconnect plugToOverride and its children (if any) recursively 
            # because Maya allows parent and children plugs to be connected independently 
            # (and therefore simultaneously).
            # Children of overridden plugs should not be connected as they may preempt the override.
            utils.disconnectDst(plugToOverride)
    
            # 2) Connect our enabled plug to the apply override node enabled input.
            utils.connect(self._getEnabledPlug(), apply.getEnabledPlug())
    
            # 3) Connect the apply override output to the plug to be overridden.
            utils.connect(apply.getOutputPlug(), plugToOverride)
            
            # 4) Connect the value override plugs to the apply override value plugs.
            # This must be connected at the end because of the way TdrawingChangeManager.cpp 
            # processes the callbacks to check if a shading network must be updated in OGS 
            # (otherwise, there's no callback on the override node and changing 
            # it's input connections doesn't trigger fragment graph to be rebuilt)
            self._connectOverridePlugs(apply)

    def applyInsertOne(self, node, attrName, nextOvr):
        """Apply this override to a single node at the given priority.

        - node is the name of the node (or DAG instance path), or an MObject.
        - attrName is the name of the attribute the override is applied to.
        - nextOvr is the next higher-priority override.  If None,
          the override is applied as highest priority (closest to the
          attribute)."""

        # If the node doesn't have the attribute we're looking for, early out.
        plugToOverride = commonUtils.findPlug(node, attrName)
        if not plugToOverride:
            return

        # Starting at the plug, iterate backward on apply override nodes
        # until the corresponding override is nextOvr.
        if nextOvr is not None:
            for ao in applyOverride.reverseGenerator(plugToOverride):
                if ao.override() == nextOvr:
                    plugToOverride = ao.getOriginalPlug()
                    break

        self._applyOne(plugToOverride)

    @context.unapplyOverride
    def unapply(self):
        """Remove the override from all nodes it was applied to."""

        # Our enabled plug's destinations are the apply nodes.
        applyOverrides = self.getApplyOverrides()

        if not applyOverrides:
            return

        # Disconnect our override plug(s) and our enabled plug from all their
        # apply node destinations.
        self._disconnectOverridePlugs()

        utils.disconnectSrc(self._getEnabledPlug())

        # For all apply override nodes we created, restore the original
        # value (or connection), disconnect the apply override nodes, and
        # remove them.
        dgMod = OpenMaya.MDGModifier()

        for apply in applyOverrides:

            # Save the apply node output destination, then disconnect it.
            # Must be only one destination to the apply output.
            applyOut = apply.getOutputPlug()
            plugToOverride = utils.plugDst(applyOut)

            # If the apply override node was applied to a node that is not
            # in the main scene (e.g. a file referenced node), the
            # connection to the node might not be there. 
            # It could also happen that the overridden attribute no longer 
            # exists because it's a plugin attribute and the plugin is not loaded.
            # There is nothing to disconnect in such cases, nor is there any 
            # original value to restore on the node either, since the node is read-only.
            if plugToOverride:
                with plug.UnlockedGuard(plugToOverride[0]):
                    nodeToOverride = plugToOverride[0].node()
                    attrToOverride = plugToOverride[0].attribute()
        
                    utils.disconnectSrc(applyOut)
                    
                    # We must not reference a networked plug after it's modified
                    # by the DG modifier:
                    # http://help.autodesk.com/view/MAYAUL/2016/ENU/?guid=__cpp_ref_class_m_plug_html
                    # We must create a new reference to the plug
                    plugToOverride[0] = OpenMaya.MPlug(nodeToOverride, attrToOverride)
        
                    # Restore the original value or the connection, stored on the
                    # apply node original input
                    utils.transferPlug(apply.getOriginalPlug(), plugToOverride[0])

            # We know we're disconnected.  Delete apply override node.
            dgMod.deleteNode(apply.thisMObject())

        dgMod.doIt()

    def getOverridden(self):
        """Return the list of nodes being overridden.

        The items in the return list are triplets of (MObject, attrName, ovrNext).
        MObject is the object being overridden, attrName is the name of the attribute 
        being overridden and ovrNext is the override node in the position of the next 
        override in the apply override list.

        Returns an empty list if no attribute is being overridden."""

        # Get all current apply override nodes.
        applyOverrides = self.getApplyOverrides()

        attrName = self.attributeName()

        # For each apply override node (if any), iterate forward until the
        # overridden attribute is hit.
        overridden = []
        for ao in applyOverrides:
            # Iterate and move forward in the chain of apply override
            # nodes, starting at ao.
            aoIter = ao
            for i in applyOverride.forwardGenerator(aoIter.getOutputPlug()):
                aoIter = i

            # After the iteration is done, aoIter is the last apply
            # override node in the chain.  Its output plug is connected to
            # the overridden attribute.
            # But make sure this connection still exists. The apply override 
            # could have been connected to an attribute that is no longer in
            # the scene, for example if the attribute was added by a plugin
            # that is no longer loaded.
            aoDst = utils.plugDst(aoIter.getOutputPlug())
            if aoDst is None:
                continue

            # Get the override corresponding to the next apply override in
            # the list.  If we're the highest-priority override, returns None.
            nextAo = applyOverride.connectedDst(ao.getOutputPlug())

            overridden.append(
                (aoDst[0].node(), attrName, nextAo.override() if nextAo else None))

        return overridden
    

class AbsOverride(LeafClass, ValueOverride):
    """Absolute override node.

    This concrete override node type implements an absolute override
    (replace value) for an attribute."""

    kTypeId = typeIDs.absOverride
    kTypeName = "absOverride"

    # Name of the value attribute. A dynamic attribute created at runtime.
    kAttrValueLong  = "attrValue"
    kAttrValueShort = "atv"

    @staticmethod
    def initializer():
        AbsOverride.inheritAttributesFrom(ValueOverride.kTypeName)

    def __init__(self):
        super(AbsOverride, self).__init__()
        # A plug handle encapsulating the value attribute. The value attribute is dynamic
        # and created in finalize(). The plug handle will be None until the attribute is created.
        self._valuePlugHandle = None
        
    def postConstructor(self):
        super(AbsOverride, self).postConstructor()
        self._valuePlugHandle = OverridePlugHandle(self, self.kAttrValueLong, self.kAttrValueShort, OverridePlugHandle.kModeClone)

    def isValid(self):
        # The node is valid when the value attribute has been created
        return self._valuePlugHandle.isValid()

    def isFinalized(self):
        return self._valuePlugHandle.isFinalized()

    def hasMissingDependencies(self):
        return self._valuePlugHandle.hasMissingDependency()
    
    def status(self):
        '''Returns a problem string if there is a problem with override or None otherwise.'''
        if not self.isFinalized():
            return kUnfinalized
        if self._valuePlugHandle.hasMissingDependency():
            return kMissingDependencies % self._valuePlugHandle.getMissingDependency()
        return None

    def _getAttrValuePlug(self):
        return self._valuePlugHandle.getPlug().plug

    def getAttrValue(self):
        return self._valuePlugHandle.getPlug().value

    def setAttrValue(self, value):
        self._valuePlugHandle.getPlug().value = value

    def _connectOverridePlugs(self, apply):
        """ Connect the abs value plug of the override node 
            to its corresponding plug in the apply override node """
        utils.connect(self._getAttrValuePlug(), apply.getValuePlug())

    def _disconnectOverridePlugs(self):
        """ Disconnect the abs value plug of the override node 
            from its corresponding plug in the apply override node """
        utils.disconnectSrc(self._getAttrValuePlug())

    def _encodeProperties(self, dict):
        super(AbsOverride, self)._encodeProperties(dict)
        self._valuePlugHandle.encode(dict)

    @finalizationChanged
    def _decodeProperties(self, dict, mergeType, prependToName):
        with undo.NotifyCtxMgr("Decode Absolute Override '%s'" % self.name(), self.itemChanged):
            super(AbsOverride, self)._decodeProperties(dict, mergeType, prependToName)
            self._valuePlugHandle.decode(dict)

    def _getCompatibilityCheckPlug(self):
        return self._getAttrValuePlug()

    @finalizationChanged
    def finalize(self, plugName):
        """ Finalize the creation of an override by setting all needed information """
        # Create the value attribute by cloning the attribute of the given plug
        with undo.NotifyCtxMgr("Finalize override '%s'" % self.name(), self.itemChanged):
            plg = plug.Plug(plugName)
            self._valuePlugHandle.finalize(plg)
            self.setAttributeName(plg.attributeName)

    def _getApplyOverrideTypeId(self):
        """Return the type ID of the apply override node that must be
        created to apply this override."""
        return self._valuePlugHandle.getPlug().applyOverrideType(typeIDs.absOverride)

    def compute(self, plg, dataBlock):
        # Workaround to MAYA-52699: in theory should not need to pull on
        # plug that is both input (writable) and output (readable), DG
        # evaluation should do this itself.
        if self._valuePlugHandle.isFinalized() and plg == self._valuePlugHandle.getPlug().plug:
            val = dataBlock.inputValue(plg)
        Override.compute(self, plg, dataBlock)


class RelOverride(LeafClass, ValueOverride):
    """Relative override node to transform a attribute using:

       newValue = originalValue * multiply + offset

       This concrete override node type implements a relative override
       for a float scalar attribute."""

    kTypeId = typeIDs.relOverride
    kTypeName = "relOverride"

    # Names of the "multiply" (scale) and "offset" dynamic attributes.
    kMultiplyLong  = "multiply"
    kMultiplyShort = "mul"
    kOffsetLong    = "offset"
    kOffsetShort   = "ofs"

    @staticmethod
    def initializer():
        RelOverride.inheritAttributesFrom(ValueOverride.kTypeName)

    def __init__(self):
        super(RelOverride, self).__init__()

        # Use plug handles to encapsulate the multiply and offset attributes.
        # These are dynamic and created in finalize().
        self._multiplyPlugHandle = None
        self._offsetPlugHandle   = None
        
    def postConstructor(self):
        super(RelOverride, self).postConstructor()
        self._multiplyPlugHandle = OverridePlugHandle(self, self.kMultiplyLong, self.kMultiplyShort, OverridePlugHandle.kModeMultiply)
        self._offsetPlugHandle = OverridePlugHandle(self, self.kOffsetLong, self.kOffsetShort, OverridePlugHandle.kModeOffset)

    def isValid(self):
        # The node is valid when the multiply and offset attributes have
        # been created.  Both must be not None or both must be None.
        return self._multiplyPlugHandle.isValid() and self._offsetPlugHandle.isValid()
    
    def status(self):
        '''Returns a problem string if there is a problem with override or None otherwise.'''
        if not self.isFinalized():
            return kUnfinalized
        dependencies = [h.getMissingDependency() for h in (self._multiplyPlugHandle, self._offsetPlugHandle) if h.hasMissingDependency() ]
        if len(dependencies) > 0:
            return kMissingDependencies % (', '.join(dependencies))
        return None

    def _getMultiplyPlug(self):
        return self._multiplyPlugHandle.getPlug().plug

    def _getOffsetPlug(self):
        return self._offsetPlugHandle.getPlug().plug

    def getMultiply(self):
        return self._multiplyPlugHandle.getPlug().value
        
    def setMultiply(self, value):
        self._multiplyPlugHandle.getPlug().value = value

    def getOffset(self):
        return self._offsetPlugHandle.getPlug().value
        
    def setOffset(self, value):
        self._offsetPlugHandle.getPlug().value = value

    def _encodeProperties(self, dict):
        super(RelOverride, self)._encodeProperties(dict)
        self._multiplyPlugHandle.encode(dict)
        self._offsetPlugHandle.encode(dict)

    @finalizationChanged
    def _decodeProperties(self, dict, mergeType, prependToName):
        with undo.NotifyCtxMgr("Decode Absolute Override '%s'" % self.name(), self.itemChanged):
            super(RelOverride, self)._decodeProperties(dict, mergeType, prependToName)
            self._multiplyPlugHandle.decode(dict)
            self._offsetPlugHandle.decode(dict)

    def _connectOverridePlugs(self, apply):
        """ Connect the value plugs from the override node 
            to their corresponding plugs in the apply override node """
        utils.connect(self._getMultiplyPlug(), apply.getMultiplyPlug())
        utils.connect(self._getOffsetPlug(), apply.getOffsetPlug())

    def _disconnectOverridePlugs(self):
        """ Disconnect the value plugs from the override node 
            to their corresponding plugs in the apply override node """
        utils.disconnectSrc(self._getMultiplyPlug())
        utils.disconnectSrc(self._getOffsetPlug())

    def _getCompatibilityCheckPlug(self):
        return self._getOffsetPlug()

    def multiplyPlugName(self):
        return self._getMultiplyPlug().name()

    def offsetPlugName(self):
        return self._getOffsetPlug().name()

    @finalizationChanged
    def finalize(self, plugName):
        """ Finalize the creation of an override by setting all needed information """
        # Create the offset attribute by cloning the attribute of the given plug
        with undo.NotifyCtxMgr("Finalize override '%s'" % self.name(), self.itemChanged):
            plg = plug.Plug(plugName)
            self._multiplyPlugHandle.finalize(plg)
            self._offsetPlugHandle.finalize(plg)
            self.setAttributeName(plg.attributeName)
    
    def isFinalized(self):
        return self._multiplyPlugHandle.isFinalized() and self._offsetPlugHandle.isFinalized()

    def _getApplyOverrideTypeId(self):
        """Return the type ID of the apply override node that must be
        created to apply this override."""
        return self._offsetPlugHandle.getPlug().applyOverrideType(typeIDs.relOverride)
    
    def compute(self, plug, dataBlock):
        # Workaround to MAYA-52699: in theory should not need to pull on
        # plug that is both input (writable) and output (readable), DG
        # evaluation should do this itself.
        if self._multiplyPlugHandle.isValid() and plug == self._multiplyPlugHandle.getPlug().plug:
            mul = dataBlock.inputValue(plug)
        elif self._offsetPlugHandle.isValid() and plug == self._offsetPlugHandle.getPlug().plug:
            ofs = dataBlock.inputValue(plug)
        Override.compute(self, plug, dataBlock)

class UniqueOverride(object):
    '''Mixin class for override that applies to a unique node. This override 
    unconditionnaly applies to the node it was finalized on (if it exists).
    It doesn't care about the collection's content.'''
    kTargetNodeName = OpenMaya.MObject()
    
    @staticmethod
    def initializer(cls):
        cls.kTargetNodeName = OpenMaya.MFnTypedAttribute().create("targetNodeName", "tgName", 
            OpenMaya.MFnData.kString, OpenMaya.MFnStringData().create(""))
        cls.writable = True
        cls.storable = True
        cls.addAttribute(cls.kTargetNodeName)

    def _targets(self, selectedNodeNames=None):
        # completely ignores selectedNodeNames or collection's selector content
        node = commonUtils.nameToNode(self.targetNodeName())
        if node is None:
            return # no op
        plg = commonUtils.findPlug(node, self.attributeName())
        return (plg,) if plg and OpenMaya.MFnAttribute(plg.attribute()).writable and self._isApplicableTo(plg) else ()
    
    def _properties(self):
        return itertools.chain(super(UniqueOverride, self)._properties(), 
            (Property(self.kTargetNodeName, self.targetNodeName, self.setTargetNodeName),))
    
    @finalizationChanged
    def finalize(self, plugName):
        """ Finalize the creation of an override by setting all needed information """
        super(UniqueOverride, self).finalize(plugName)
        self.setTargetNodeName(plugName.split('.')[0])
    
    def targetNodeName(self, dataBlock=None):
        return self._getInputAttr(self.kTargetNodeName, dataBlock).asString()

    @undo.chunk('Set unique override node name')
    def setTargetNodeName(self, nodeName):
        if nodeName != self.targetNodeName():
            cmds.setAttr(self.name()+".targetNodeName", nodeName, type='string')


class AbsUniqueOverride(UniqueOverride, AbsOverride):
    kTypeId = typeIDs.absUniqueOverride
    kTypeName = "absUniqueOverride"
    
    @classmethod
    def initializer(cls):
        cls.inheritAttributesFrom(AbsOverride.kTypeName)
        UniqueOverride.initializer(cls)


class RelUniqueOverride(UniqueOverride, RelOverride):
    kTypeId = typeIDs.relUniqueOverride
    kTypeName = "relUniqueOverride"
    
    @classmethod
    def initializer(cls):
        cls.inheritAttributesFrom(RelOverride.kTypeName)
        UniqueOverride.initializer(cls)
        

@undo.chunk("Create override")
@namespace.root
def create(name, nodeType):
    """Create an override with type given by the argument type ID.

    Returns the MPxNode object corresponding to the created override node.
    A RuntimeError is raised in case of error.

    This function is undoable."""

    if isinstance(nodeType, basestring):
        typeName = nodeType
    else:
        typeName = cmds.objectType(typeFromTag=nodeType.id())

    # Using existing command for undo / redo purposes, even if it requires
    # a name-based lookup to return the user node, since override
    # creation is not performance-critical.  If the name flag is specified,
    # it cannot be an empty string.
    returnName = cmds.createNode(typeName, name=name, skipSelect=True) if name \
                 else cmds.createNode(typeName, skipSelect=True)

    return utils.nameToUserNode(returnName)


@undo.chunk('Delete override')
def delete(override):
    """Remove the argument override from the scene.

    If the override was applied, it is unapplied first."""

    # Perform unapply before detach, so we can record our position in our
    # parent's override list.
    UnapplyCmd.execute(override)

    # Inform our parent (if any) of upcoming delete.
    parent = override.parent()
    if parent:
        parent._preChildDelete(override)

    # Do any required finalization and delete the node
    utils.deleteNode(override)

#==============================================================================
# CLASS UnapplyCmd
#==============================================================================

class UnapplyCmd(OpenMaya.MPxCommand):
    """Command to unapply and reapply an override.

    This command is a private implementation detail of this module and should
    not be called otherwise."""

    kCmdName = 'unapplyOverride'

    # Command data.  Must be set before creating an instance of the command
    # and executing it.  Ownership of this data is taken over by the
    # instance of the command.
    override = None

    def isUndoable(self):
        return True

    def doIt(self, args):
        # Completely ignore the MArgList argument, as it's unnecessary:
        # arguments to the commands are passed in Python object form
        # directly to the command's constructor.

        if self.override is None:
            self.displayWarning(kUnapplyCmdPrivate % self.kCmdName)
        else:
            self.redoIt()

    @staticmethod
    def execute(override):
        """Unapply the override, and add an entry to the undo queue."""

        UnapplyCmd.override = override
        cmds.unapplyOverride()
        UnapplyCmd.override = None

    @staticmethod
    def creator():
        # Give ownership of the override to the command instance.
        return UnapplyCmd(UnapplyCmd.override)

    def __init__(self, override):
        super(UnapplyCmd, self).__init__()
        self.override = override
        self.overridden = None

    # Render setup hack for 2016_R2.  See MAYA-65530.
    @guard.environ('MAYA_RENDER_SETUP_OVERRIDE_CONNECTABLE', '1')
    def redoIt(self):
        # Save the information needed for undo.  This information is the
        # overridden list, a list of pairs of MObject's.
        #
        # The first element in the pair is simply one node to which the
        # override is applied.
        #
        # The second element in the pair is the next override in the
        # chain of applied overrides, which provides the position in the
        # chain.  If the override to be applied was the highest-priority
        # override (i.e. closest to the attribute), this element is None.
        #
        # This list of pairs may be a subset of the nodes given to the
        # override on apply, because some of the selected nodes might
        # not have the named attribute, in which case the override was
        # never applied.

        self.overridden = self.override.getOverridden()
        self.override.unapply()

    # Render setup hack for 2016_R2.  See MAYA-65530.
    @guard.environ('MAYA_RENDER_SETUP_OVERRIDE_CONNECTABLE', '1')
    def undoIt(self):
        # Re-apply the override.  For each node to which the override was
        # previously applied (nodeObj), apply the override, with the
        # appropriate position in the list of applied overrides given from
        # our saved data (nextOvrObj).
        self.override.reapply(self.overridden)

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
