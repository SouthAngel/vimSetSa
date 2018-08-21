""" Connection override node classes and utility functions.

    This module provides the connection override classes.

    An override for an attribute is created by adding an override for it to an OverrideManager.
    The RenderLayer class derives from the OverrideManager class, so the currently active layer 
    is the manager to add the overrides to.

    The manager is responsible for creating override apply nodes that represents an override on an 
    attribute for a particular object. See overrideManager module for more information.

    From the user perspective there is always just a single override created per override node, 
    for instance replacing a single surface shader or replacing material assignments 
    with a single new material. However, internally this can result in multiple overrides.
    For example when overriding a material (shading engine) there can be multiple connections 
    that need to be overridden per member of the collection. A single mesh can have multiple 
    per-instance and per-face assignments that all need to be overridden for the material to have 
    effect on the whole mesh.

    All the apply overrides are added to the manager when the override node is applied, and they
    exists until the override node is unapplied. During this time the override can be disabled/enabled which 
    will switch all the values or connections according to the "new" and "original" plugs specified by the 
    override. The override manager handles all changes that needs to be done then something is disabled/enabled.
    The apply overrides are removed from the manager and deleted when the override node is unapplied.
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya

import maya.app.renderSetup.model.override as override
import maya.app.renderSetup.model.applyOverride as applyOverride
import maya.app.renderSetup.model.typeIDs as typeIDs
import maya.app.renderSetup.model.utils as utils
import maya.app.renderSetup.model.enabled as enabled
import maya.app.renderSetup.common.utils as commonUtils
import maya.app.renderSetup.common.guard as guard
import maya.app.renderSetup.model.plug as plug
import maya.app.renderSetup.model.undo as undo
import maya.app.renderSetup.model.context as context
import itertools

# List all error messages
kApplyNodeNoRenderLayerConnection = maya.stringTable['y_connectionOverride.kApplyNodeNoRenderLayerConnection' ]
kAttrValueAlreadyCreated = maya.stringTable['y_connectionOverride.kAttrValueAlreadyCreated' ]
kMaterialOverrideFailure = maya.stringTable['y_connectionOverride.kMaterialOverrideFailure' ]

# Connection overrides must create reference edits when restoring an
# overridden connection on an attribute of a referenced node.  In this
# state, connections must be made with reference edits on.
_restoringOriginal = False

def isRestoringOriginal():
    return _restoringOriginal

def setRestoringOriginal(restoringOriginal):
    global _restoringOriginal
    _restoringOriginal = restoringOriginal

def handleRestoringOriginalCtx():
    '''Create and return a context to properly set reference edits.

    The context turns reference edits on when restoring the original of a
    connection override.'''

    # Negative logic: when restoring the original, don't ignore reference edits.
    return guard.StateGuardCtx(
        OpenMaya.MFnReference.ignoreReferenceEdits, 
        OpenMaya.MFnReference.setIgnoreReferenceEdits, 
        not isRestoringOriginal())

# Copy-pasted from utils._transferConnectedPlug, so that LEGB lookup will
# find the transferPlug function in this module, which correctly handles
# reference edits.
def _transferConnectedPlug(src, dst):
    if src.isDestination:
        fromSrc = utils.plugSrc(src)
        # Turn reference edits on if restoring the original.
        with handleRestoringOriginalCtx():
            utils.connect(fromSrc, dst)
    elif src.isCompound and dst.isCompound:
        for idx in range(0, src.numChildren()):
            transferPlug(src.child(idx), dst.child(idx))

def transferPlug(src, dst):
    """ Transfer the connection or value set on plug 'src' on to the plug 'dst'."""

    # Adapted from utils.transferPlug.  We turn reference edits on when
    # restoring the original only for connected attributes, not setAttr:
    # render setup should not create spurious setAttr edits when restoring
    # unconnected attributes of referenced nodes.  These should simply
    # revert back to the value in the reference file, or to any
    # previously-existing reference edit.
    if utils._isDestination(src):
        # src is connected so transfer the connection.
        _transferConnectedPlug(src, dst)
    else:
        # src is not connected.  Break any connection on dst and then
        # transfer value instead.
        if dst.isDestination:
            utils.disconnectDst(dst)
        plug.Plug(dst).copyValue(src)

def plugsToSEConnection(plgs):
    for src in plgs:
        for dest in src.destinations():
            if dest.node().hasFn(OpenMaya.MFn.kShadingEngine):
                yield (src,dest)

def dagPathToSEConnections(dagPath):
    '''Returns an iterable over all the connections from an instance to a shading engine.
       There can be more than one when mesh has per-face shading.
       
       Connections are returned as tuples (srcPlug, destPlug)
       "srcPlug" belongs to the shape. "destPlug" belongs to the assigned shading engine.
       srcPlug ---> destPlug '''
    # get the parent instObjgroup plug
    instanceNr = dagPath.instanceNumber()
    node = OpenMaya.MFnDependencyNode(dagPath.node())
    instObjGroups = node.findPlug("instObjGroups", False)
    if instanceNr >= instObjGroups.evaluateNumElements():
        return ()
    
    # get whole instance and per face plugs 
    instObjGroup = instObjGroups.elementByLogicalIndex(instanceNr)
    objGroups = instObjGroup.child(0)
    plugs = itertools.chain([instObjGroup], # whole instance
        (objGroups.elementByLogicalIndex(i) for i in xrange(objGroups.evaluateNumElements()))) # per-face
    return plugsToSEConnection(plugs)


class ConnectionOverride(override.AbsOverride):
    """ Attribute connection override node.

    This override node type implements an attribute override by setting a
    new value or connection on an attribute.

    A value attribute is used to let the user set a value or make a connection to
    the node to be used as override. This attribute is dynamic and created 
    with a type matching the target attribute. The override node is not valid 
    until such a dynamic attribute is created. An override that is not valid 
    will not be applied when its layer is made active. However an override that 
    later becomes valid (the user drag and drops a target attribute), will then 
    automatically be applied if the layer is active.
    
    Source connections to the value attribute is encoded/decoded for export/import
    using OverridePlugHandle (in override.py). This class handles missing dependencies
    on decode and remakes the connection when the dependency node is added.
    """

    kTypeId = typeIDs.connectionOverride
    kTypeName = "connectionOverride"
    
    @staticmethod
    def initializer():
        ConnectionOverride.inheritAttributesFrom(override.AbsOverride.kTypeName)
        
        # legacy, do not use
        stringData = OpenMaya.MFnStringData().create("")
        fnStringAttr = OpenMaya.MFnTypedAttribute()
        legacyAttr = fnStringAttr.create("connectionStr", "cs", OpenMaya.MFnData.kString, stringData)
        fnStringAttr.writable = True
        fnStringAttr.storable = True
        ConnectionOverride.addAttribute(legacyAttr)
        
    def __init__(self):
        super(ConnectionOverride, self).__init__()
        self.attrChangedCallbackId = None

    def postConstructor(self):
        """ Method running after the node is constructed. 
        All initialization that will access the MObject or other 
        methods of the MPxNode must be done here. Since the node 
        is not fully created until after the call to __init__ """

        # Call parent class postConstructor
        super(ConnectionOverride, self).postConstructor()
        self.activate()

    def activate(self):
        # Add the callback
        if not self.attrChangedCallbackId:
            self.attrChangedCallbackId = OpenMaya.MNodeMessage.addAttributeChangedCallback(self.thisMObject(), self.attrChangedCB)

        # Call parent class activate
        super(ConnectionOverride, self).activate()

    def deactivate(self):
        # Remove the callback
        if self.attrChangedCallbackId:
            OpenMaya.MMessage.removeCallback(self.attrChangedCallbackId)
            self.attrChangedCallbackId = None

        # Call parent class deactivate
        super(ConnectionOverride, self).deactivate()

    def __del__(self):
        self.deactivate()
    
    def attrChangedCB(self, msg, plg, otherPlug, clientData):
        '''Update the connection override when attrValue changes.'''
        # callbacks should not add commands on the undo stack because 
        # 1. the command will be added to the stack BEFORE the command triggering the notification is added to it 
        #    (=> order is reversed on the undo stack)
        # 2. they are called on undo/redo
        if (msg & (OpenMaya.MNodeMessage.kConnectionMade | OpenMaya.MNodeMessage.kConnectionBroken | OpenMaya.MNodeMessage.kAttributeSet)) and \
            self.isFinalized() and self._getAttrValuePlug() == plg:
            self.update()
    
    def enabledChanged(self):
        # Don't update ourselves if a collection is pulling on our enabled
        # output.  The collection will update us in a second step (to avoid
        # DG evaluation cycles).
        if not enabled.isPulling():
            self.update()
        super(ConnectionOverride, self).enabledChanged()

    @override.valid
    @context.applyOverride
    def apply(self, selectedNodeNames=None):
        """ Apply the override to selected node names. """
        for target in self._targets(selectedNodeNames):
            self._createApplyOverride(target)
        self.update()
    
    @override.valid
    @context.applyOverride
    def postApply(self):
        '''Applies the override at the right position in the apply override node chain.'''
        for target in self._targets():
            destinations = (OpenMaya.MFnDependencyNode(d.node()).userNode() for d in target.destinations())
            firstAO = next((d for d in destinations if d and isinstance(d, ApplyConnectionOverride)), None)
            nextOvr = None
            overrides = (ao.override() for ao in ApplyConnectionOverride.reverseGenerator(firstAO))
            for ov in overrides:
                if ov < self:
                    break
                nextOvr = ov
            self._createApplyOverride(target, nextOvr)
        self.update()
    
    @context.applyOverride
    def reapply(self, overridden):
        for node, attrName, nextOvr in overridden:
            self._createApplyOverride(commonUtils.findPlug(node, attrName), nextOvr)
        self.update()

    # Since removing a connection override is equivalent to disabling it 
    # (in term of how it can affect subcollections to be populated), 
    # also add updateConnectionOverride decorator. See context.py for details.
    @context.unapplyOverride
    @context.updateConnectionOverride
    def unapply(self):
        """ Restore the override. """
        dgMod = OpenMaya.MDGModifier()
        for applyNode in self.getApplyOverrides():
            applyNode.extract()
            dgMod.deleteNode(applyNode.thisMObject())
        dgMod.doIt()
        
    def _createApplyOverride(self, target, nextOvr=None):
        name = self.name()+"_"+target.partialName(includeNodeName=True, includeNonMandatoryIndices=True, includeInstancedIndices=True)
        # Namespace qualifies from the original node name cannot be used
        # to rename the new apply node.  Replace the namespace qualifiers with '_'.
        name = name.replace(':', '_').replace('.','_')
        if utils.nameToUserNode(name):
            return
        
        ao = ApplyConnectionOverride.create(name)
        utils.connect(self._getEnabledPlug(), ao.getEnabledPlug())
        ao.finalize(self._getAttrValuePlug())
        ao.insert(target, nextOvr)
        return ao

    @context.updateConnectionOverride
    def update(self):
        """ Update the override """
        for applyNode in self.getApplyOverrides():
            applyNode.update()

    def updateOnEnabledChanged(self):
        """Connection overrides need to update their apply override nodes
        on enabled changed, so this method returns true."""
        return True

    def doAction(self, target, source):
        """ This method performs the override action for a given target and source. """
        # NOTE: doAction should never add commands in the undo stack
        with plug.UnlockedGuard(target):
            transferPlug(source, target)

    def doSaveOriginal(self, target, storage):
        """ This method performs saving of original state for a given target
        and a storage plug for storing the state. """
        utils.transferPlug(target, storage)

    def getOverridden(self):
        """Return the list of nodes being overridden.

        The items in the return list are triplets of (MObject, attrName, ovrNext).
        MObject is the object being overridden, attrName is the name of the attribute 
        being overridden and ovrNext is the override node in the position of the next 
        override in the apply override list.

        Returns an empty list if no attribute is being overridden."""
        def aoToOverridden(ao):
            target = ao.getTarget()
            attrName = target.partialName(includeNodeName=False, includeNonMandatoryIndices=True, includeInstancedIndices=True)
            nextAo = ao.next()
            return (target.node(), attrName, nextAo.override() if nextAo else None)
        return [aoToOverridden(ao) for ao in self.getApplyOverrides()]

    def setSource(self, attr):
        """ Method used by import to set the new source attribute. """
        self._valuePlugHandle.setSource(attr)

    def _isPolymorphic(self):
        """ Returns True if this class can support multiple attribute types.
        Derived classes should override this. """
        return True
    
    def _encodeProperties(self, dict):
        super(ConnectionOverride, self)._encodeProperties(dict)
        if not self._isPolymorphic():
            # if attrValue is not polymorfic, no need to encode it's properties
            # as they are unrelevant on decode. Only source is relevant.
            if 'attrValue' in dict:
                del dict['attrValue']
            source = self._valuePlugHandle.getSource()
            if source is not None:
                dict["connectionStr"] = source.name()
    
    def _decodeProperties(self, dict, mergeType, prependToName):
        super(ConnectionOverride, self)._decodeProperties(dict, mergeType, prependToName)
        # backward comp
        if "connectionStr" in dict:
            self.setSource(dict["connectionStr"])

class ShaderOverride(ConnectionOverride):
    """ Shader override node.

    Specialization of connection override for surface shader replacement.

    This override node type implements a shader override
    (replace surface shader) for shadingEngines assigned to DAG nodes.

    The surfaceShader attribute on shadingEngine nodes holds the shader to 
    use as surface shader for that material. See MaterialOverride docstring
    for how the assignment to shadingEngine is handled.

    This class will override the connection to the surfaceShader attribute
    with another shader node specified by the user. Since it is just replacing
    surfaceShader connections and keeps all shadingEngine assignments it will
    preserve displacement and volume shader assignments. """

    kTypeId = typeIDs.shaderOverride
    kTypeName = "shaderOverride"

    @staticmethod
    def creator():
        return ShaderOverride()

    @staticmethod
    def initializer():
        ShaderOverride.inheritAttributesFrom(ConnectionOverride.kTypeName)

    def __init__(self):
        super(ShaderOverride, self).__init__()

    def postConstructor(self):
        """ Method running after the node is constructed. 
        All initialization that will access the MObject or other 
        methods of the MPxNode must be done here. Since the node 
        is not fully created until after the call to __init__ """

        # Call parent class postConstructor
        super(ShaderOverride, self).postConstructor()

        # Create the value attribute as a color attribute
        attrObj = OpenMaya.MFnNumericAttribute().createColor(ConnectionOverride.kAttrValueLong, ConnectionOverride.kAttrValueShort)
        fn = OpenMaya.MFnDependencyNode(self.thisMObject())
        fn.addAttribute(attrObj)

    def _isPolymorphic(self):
        return False # Attribute is fixed and created in postCostructor above

    def isValid(self):
        # Material and Shader Overrides don't need to have a connection set (the override connection) 
        # in order to know on what plugs they will apply => they can be considered valid and create their apply 
        # override nodes even if they don't have a connection override set.
        return super(ShaderOverride, self).isValid()

    def _targets(self, selectedNodeNames=None):
        '''Returns a generator of plug targets on which to create apply connection override nodes.'''
        # If we weren't given node names to find target for, get them from our
        # parent collection's selector.
        nodes = (commonUtils.nameToNode(name) for name in selectedNodeNames) \
                if selectedNodeNames is not None else \
                self.parent().getSelector().nodes()
        
        return (OpenMaya.MFnDependencyNode(o).findPlug('message', False) for o in nodes if o.hasFn(OpenMaya.MFn.kShadingEngine))

    def doAction(self, target, source):
        """ This method performs the override action for a given target and source. """
        # NOTE: doAction should never add commands in the undo stack
        shaderPlug = utils.plugSrc(source)
        if shaderPlug:
            surfaceShader = shaderPlug.node()
            shadingEngine = target.node()

            # Break any connections to old surface shader
            fnShadingEngine = OpenMaya.MFnDependencyNode(shadingEngine)
            connections = fnShadingEngine.getConnections()
            for c in connections:
                if c.isDestination:
                    fn = OpenMaya.MFnDependencyNode(c.source().node())
                    nodeClass = OpenMaya.MNodeClass(fn.typeName)
                    if 'shader/surface' in nodeClass.classification:
                        utils.disconnect(c.source(), c)

            # Make connections to new surface shader
            connections = ShaderOverride._getNewConnections(surfaceShader, shadingEngine)
            # Turn reference edits on if restoring the original.
            with handleRestoringOriginalCtx():
                for c in connections:
                    utils.connect(c[0], c[1])

    def doSaveOriginal(self, target, storage):
        """ This method performs saving of original state for a given target
        and a storage plug for storing the state. """
        # Find old surface shader
        fnShadingEngine = OpenMaya.MFnDependencyNode(target.node())
        connections = fnShadingEngine.getConnections()
        for c in connections:
            if c.isDestination:
                fn = OpenMaya.MFnDependencyNode(c.source().node())
                nodeClass = OpenMaya.MNodeClass(fn.typeName)
                if 'shader/surface' in nodeClass.classification:
                    # Source surface shader found.
                    # Use the message plug to save a reference to it.
                    target = fn.findPlug('message', False)
                    utils.connect(target, storage)
                    break

    @staticmethod
    def _getNewConnections(surfaceShader, shadingEngine):
        """ Get a list for connections that should be made when connecting a 
        surface shader to a shading engine. This can be customizable by plug-ins
        using the callback hook 'provideNodeToNodeConnection'. """
        connections = []
        fnSurfaceShader = OpenMaya.MFnDependencyNode(surfaceShader)
        fnShadingEngine = OpenMaya.MFnDependencyNode(shadingEngine)
        # Check if a plug-in has provided custom attributes to use for the connection
        # Using EAFP style code and catch any exception raised if no custom attributes
        # are given, or they are given in incorrect format.
        try:
            result = cmds.callbacks(fnSurfaceShader.typeName, fnShadingEngine.typeName, executeCallbacks=True, hook='provideNodeToNodeConnection')
            attributes = result[0].split(':')
            # Make a connection for each pair of "src:dst" attributes
            count = len(attributes)
            for i in xrange(0, count, 2):
                shaderPlug = fnSurfaceShader.findPlug(attributes[i], False)
                enginePlug = fnShadingEngine.findPlug(attributes[i+1], False)
                connections.append((shaderPlug,enginePlug))
        except:
            # Fall back to default behavior making a default connection
            # between surface shader and shading engine
            shaderPlug = fnSurfaceShader.findPlug('outColor', False)
            enginePlug = fnShadingEngine.findPlug('surfaceShader', False)
            if shaderPlug and enginePlug:
                connections.append((shaderPlug,enginePlug))
        return connections


class MaterialOverride(ConnectionOverride):
    """Material override node.

    Specialization of connection override for material (shading engine) assignments.

    This override node type implements a material override
    (replace shading engine assignments) for DAG nodes.

    Shading group assignments in Maya are represented by connections to the 
    instObjGroups attribute on the shape node. It's an array attribute that represents 
    per-instance assignments and per-face group assignments in the following way:

    myShape.instObjGroups[N] - connection to this represents material assignment to
    instance number N.

    myShape.instObjGroups[N].objectGroups[M] - connection to this represents assignment 
    to face group M of instance number N.

    The connections are made from myShape.instObjGroups[N] -> mySG.dagSetMembers[X],
    where mySG is a shadingEngine node, which represents that this shading engine is
    assigned to that instance of the shape. The dagSetMembers attribute is special and is
    using disconnectBehavior = kDelete which means its array elements are deleted as soon
    as they are disconnected. So we cannot save these element plugs explicitly. Instead we 
    use the message attribute to have a reference to the node. Then we override the
    doAction() and doSaveOriginal() methods to handle the shading engine set assignments.

    Since this override type is replacing the whole shadingEngine with a new one,
    it will not preserve any displacement or volume material set on the shadingEngine.

    Care must be taken when applying an override to shapes whose original
    material is from a referenced file.  In addition to preserving the
    state of the original material through a connection, we also save the
    name of the material in the apply override node as a string, if the
    material was referenced."""

    kTypeId = typeIDs.materialOverride
    kTypeName = "materialOverride"

    # String-based dynamic attribute storage for referenced materials.
    # This attribute is added to the apply override node.
    kShadingEngineNameLong  = 'shadingEngineName'
    kShadingEngineNameShort = 'sen'

    @staticmethod
    def creator():
        return MaterialOverride()

    @staticmethod
    def initializer():
        MaterialOverride.inheritAttributesFrom(ConnectionOverride.kTypeName)

    def __init__(self):
        super(MaterialOverride, self).__init__()

    def postConstructor(self):
        """ Method running after the node is constructed. 
        All initialization that will access the MObject or other 
        methods of the MPxNode must be done here. Since the node 
        is not fully created until after the call to __init__ """

        # Call parent class postConstructor
        super(MaterialOverride, self).postConstructor()

        # Create the value attribute as a message attribute
        attrObj = utils.createDstMsgAttr(ConnectionOverride.kAttrValueLong, ConnectionOverride.kAttrValueShort)
        fn = OpenMaya.MFnDependencyNode(self.thisMObject())
        fn.addAttribute(attrObj)
        
    def isValid(self):
        # Material and Shader Overrides don't need to have a connection set (the override connection) 
        # in order to know on what plugs they will apply => they can be considered valid and create their apply 
        # override nodes even if they don't have a connection override set.
        return super(MaterialOverride, self).isValid()

    def _isPolymorphic(self):
        return False # Attribute is fixed and created in postCostructor above
    
    def setMaterial(self, name):
        self.setSource(name+".message")

    def _targets(self, selectedNodeNames=None):
        # If we were given node names to find targets for, create a generator that
        # will convert them to DAG paths.  Otherwise, get DAG paths from
        # our parent collection's selector.
        dagPaths = (p.dagPath for p in self.parent().getSelector().shapes()) \
                   if selectedNodeNames is None else \
                   (commonUtils.nameToDagPath(n) for n in selectedNodeNames)

        for dagPath in dagPaths:
            for (src,_) in dagPathToSEConnections(dagPath):
                yield src

    def doAction(self, target, source):
        """ This method performs the override action for a given target and source. """
        # NOTE: doAction should never add commands in the undo stack

        # Make connection to new shading engine
        enginePlug = source.source()
        if not enginePlug.isNull:

            # First break the connection to old shading engine.
            # NOTE: Returning the plug and then disconnecting it didn't work. 
            # The plug object was destroyed when we got outside the scope of 
            # where it was created (reference count didn't work properly). 
            # I think it has to do with the special nature of the shadingEngine 
            # attribute (dagSetMembers) which has its array elements destroyed 
            # as soon as they are disconnected. 
            # A workaround for this was to add support to disconnect the 
            # shading engine directly inside the method instead.
            MaterialOverride._hasShadingEngineConnection(target, disconnect=True)

            fnShadingEngine = OpenMaya.MFnDependencyNode(enginePlug.node())
            dagSetMembersPlug = fnShadingEngine.findPlug("dagSetMembers", False)

            # Get full path name to target which is needed in case of object instancing
            targetPath = OpenMaya.MFnDagNode(target.node()).fullPathName()
            targetAttr = target.partialName(
                includeNodeName=False, 
                includeNonMandatoryIndices=True, 
                includeInstancedIndices=True, 
                useAlias=False, 
                useFullAttributePath=True, 
                useLongNames=True
            )
            targetFullAttrName = targetPath + "." + targetAttr

            # Need to use a command here to use 'nextAvailable' needed by set assignment
            with undo.SuspendUndo():
                # Turn reference edits on if restoring the original.
                with handleRestoringOriginalCtx():
                    # Guard agains the case where the connection can't be made,
                    # to make sure we don't break the system if that happens.
                    # This happens if per-face assignments are made when the
                    # override is already applied, which is not supported.
                    try:
                        # doAction should never add commands in the undo stack
                        cmds.connectAttr(targetFullAttrName, dagSetMembersPlug.name(), nextAvailable = True)
                    except:
                        OpenMaya.MGlobal.displayWarning(kMaterialOverrideFailure % self.name())

    @staticmethod
    def saveShadingEngine(shadingEngineObj, storagePlug):
        '''Save a connection to the shading engine node in the storage plug.

        This function unconditionally connects the shading engine to the
        storage plug.  It also stores the name of the shading engine as a full
        name with the namespace path in the storage plug's node, if the shading
        engine is not in the main scene.'''
    
        # Store the shading engine message attribute
        fnEngine = OpenMaya.MFnDependencyNode(shadingEngineObj)
        enginePlug = fnEngine.findPlug('message', False)
        utils.connect(enginePlug, storagePlug)

        # Deal with fact that material might be in a referenced file.
        storageNode = storagePlug.node()
        storageStrPlug = plug.findPlug(
            storageNode, MaterialOverride.kShadingEngineNameLong)

        if fnEngine.isFromReferencedFile:
            if storageStrPlug is None:
                properties = {'type' : 'String', 'connectable' : False}
                storageStrPlug = plug.Plug.createAttribute(
                    storageNode, MaterialOverride.kShadingEngineNameLong, 
                    MaterialOverride.kShadingEngineNameShort, 
                    properties, plug.kNotUndoable)

            storageStrPlug.value = fnEngine.name()
        elif storageStrPlug is not None:
            # Remove dynamic attribute.
            fn = OpenMaya.MFnDependencyNode(storageNode)
            fn.removeAttribute(storageStrPlug.plug.attribute())

    def doSaveOriginal(self, target, storage):
        """ This method performs saving of original state for a given target
        and a storage plug for storing the state. """
        # Find existing shading engine connection
        if target.isSource:
            connections = target.destinations()
            for c in connections:
                n = c.node()
                if n.hasFn(OpenMaya.MFn.kShadingEngine):
                    MaterialOverride.saveShadingEngine(n, storage)
                    break

    @staticmethod
    def _hasShadingEngineConnection(plg, disconnect=False):
        """ Return True if a shading engine is connected to a given plug. """
        if plg.isSource:
            connections = plg.destinations()
            for c in connections:
                if c.node().hasFn(OpenMaya.MFn.kShadingEngine):
                    if disconnect:
                        utils.disconnect(plg, c)
                    return True
        return False


class DstConnectionHandle(object):
    '''Plug class that handles and persists a destination connection.

    The source of a destination connection can be in a referenced file.  If
    so, the connection is recorded by this class as a string, and stored in
    a dynamic attribute.

    On connect, if the source is referenced, store the string
    representation of the source.  On disconnect, if we have a string
    representation, remove it.  On access, if disconnected, check if we
    have a string representation.  If so, use it and connect.'''

    def __init__(self, node, aDst, srcStrAttrNameLong, srcStrAttrNameShort):
        '''Create the handle on the argument MObject node, for the destination
        attribute aDst.

        If the source is referenced, store its string representation in the
        attribute named srcStrAttrNameLong, srcStrAttrNameShort.'''
        self._node                = node
        self._aDst                = aDst
        self._srcStrAttrNameLong  = srcStrAttrNameLong
        self._srcStrAttrNameShort = srcStrAttrNameShort

    def connect(self, src):
        '''Connect this destination to the argument source MPlug.  If the
        source node is referenced, store a string representation of the
        source.'''

        # For non-referenced sources, simply connect.  This will trivially
        # and obviously persist the connection information.
        utils.connect(src, self.dst())

        # If src is referenced, record it as a string, as connections to
        # referenced objects are normally recorded as referenced edits,
        # which we intentionally turn off in render setup.
        srcNode = src.node()
        srcFn = OpenMaya.MFnDependencyNode(srcNode)

        if srcFn.isFromReferencedFile:
            srcStrPlug = self._srcStrPlug()
            if srcStrPlug is None:
                properties = {'type' : 'String', 'connectable' : False}
                srcStrPlug = plug.Plug.createAttribute(
                    self._node, self._srcStrAttrNameLong, 
                    self._srcStrAttrNameShort, properties, plug.kNotUndoable)

            # Connection overrides represent a connection to a node, and
            # therefore don't need a DAG path to disambiguate between
            # different instances.  However, because DAG nodes don't have
            # unique names, we do need a DAG path to disambiguate different
            # DAG nodes with the same name.
            if srcNode.hasFn(OpenMaya.MFn.kDagNode):
                srcPath = OpenMaya.MFnDagNode(srcNode).fullPathName()
                srcAttr = src.partialName(
                    includeNodeName=False, 
                    includeNonMandatoryIndices=True, 
                    includeInstancedIndices=True, 
                    useAlias=False, 
                    useFullAttributePath=True, 
                    useLongNames=True
                )
                srcFullAttrName = srcPath + "." + srcAttr
            else:
                srcFullAttrName = src.name()

            srcStrPlug.value = srcFullAttrName

    def disconnect(self):
        '''Disconnect this destination from its source (if any).  If we
        have a string representation of the source, it is removed.'''

        utils.disconnectDst(self.dst())
        srcStrPlug = self._srcStrPlug()
        if srcStrPlug is not None:
            self._removeSrcStr(srcStrPlug)

    def src(self):
        '''Convenience to return the source MPlug of this destination plug
        handle.'''

        return self.dst().source()

    def _srcStrPlug(self):
        '''Return a plug.Plug handle to the string representation of the
        source, if it exists, else None.'''

        return plug.findPlug(self._node, self._srcStrAttrNameLong)

    def _removeSrcStr(self, srcStrPlug):
        '''Remove the dynamic attribute storing the string representation
        of the source.

        The argument is the plug.Plug handle to the dynamic attribute.'''

        fn = OpenMaya.MFnDependencyNode(self._node)
        fn.removeAttribute(srcStrPlug.plug.attribute())
            
    def _restoreConnection(self, dst):
        # If the source was in a referenced file, the connection to it may
        # have been broken.  To deal with this case, we also stored a
        # string representation of the source.
        srcStrPlug = self._srcStrPlug()
        if srcStrPlug is not None:
            src = commonUtils.nameToPlug(srcStrPlug.value)
            if src is not None and not src.isNull:
                utils.connect(src, dst)
        
    def dst(self):
        '''Return the destination MPlug of this handle.

        If disconnected, we check if we have a string representation.  If
        so, we use it and try to re-connect to the source.'''

        dst = OpenMaya.MPlug(self._node, self._aDst)
        if not dst.isConnected:
            self._restoreConnection(dst)
        return dst
        

class ApplyConnectionOverride(applyOverride.LeafClass, applyOverride.ApplyOverride):
    """ Connection override apply class. 

    Class for applying all connection overrides. It is similar to apply nodes for value overrides, 
    but with some notable differences. Firstly, since it is generating connections it cannot be connected to 
    the target attribute like value apply nodes. Secondly, there is no numeric values flowing between these 
    nodes. Instead message attributes are used to chain the nodes together and the chain represents the order 
    of priority for the nodes.

    When an override needs updating, e.g. if the enabled state is changed, the chain of apply nodes is 
    traversed to find the highest priority enabled apply node. The override action from that node 
    is then executed on the target attribute to perform the override change. """

    kTypeId = typeIDs.applyConnectionOverride
    kTypeName = "applyConnectionOverride"

    # The two next attributes are only valid for the first apply connection override
    # contains the original connection
    kOriginalLong  = "original"
    kOriginalShort = "org"
    # point to the target for the connection override to be made
    # the target is held by the apply override with the highest priority
    # (this target plug is meaningless for all the apply override nodes in the chain
    # except the last one (with highest priority))
    kTargetLong  = "target"
    kTargetShort = "tg"

    # String-based dynamic attribute storage for referenced targets.
    kTargetNameLong  = 'targetName'
    kTargetNameShort = 'tgn'

    aTarget   = OpenMaya.MObject()
    aPrevious = OpenMaya.MObject() # Previous apply node if chained
    aNext     = OpenMaya.MObject() # Next apply node if chained

    @classmethod
    def create(cls, name):
        applyNode = OpenMaya.MFnDependencyNode()
        applyNode.create(cls.kTypeId, name)
        return applyNode.userNode()

    @staticmethod
    def initializer():
        ApplyConnectionOverride.inheritAttributesFrom(applyOverride.ApplyOverride.kTypeName)
        ApplyConnectionOverride.aTarget = utils.createGenericAttr("target", "tg")

        # Input attribute for chaining nodes
        ApplyConnectionOverride.aPrevious = utils.createDstMsgAttr("previous", "p")
        # Output attribute for chaining nodes
        ApplyConnectionOverride.aNext = utils.createSrcMsgAttr("next", "n")

        ApplyConnectionOverride.addAttribute(ApplyConnectionOverride.aTarget)
        ApplyConnectionOverride.addAttribute(ApplyConnectionOverride.aPrevious)
        ApplyConnectionOverride.addAttribute(ApplyConnectionOverride.aNext)

    def __init__(self):
        super(ApplyConnectionOverride, self).__init__()
        # Silence pylint warning.
        self._targetHandle = None

    def postConstructor(self):
        super(ApplyConnectionOverride, self).postConstructor()
        self._targetHandle = DstConnectionHandle(
            self.thisMObject(), self.aTarget, self.kTargetNameLong, 
            self.kTargetNameShort)

    def finalize(self, ovrValuePlug):
        # Create the "original" plug by cloning the attribute of the given plug
        plg = plug.Plug(ovrValuePlug)
        # We don't want the clone attribute to be undoable (because it will break
        # the undo/redo for switch render layer)
        plg.cloneAttribute(self.thisMObject(), ApplyConnectionOverride.kOriginalLong, ApplyConnectionOverride.kOriginalShort, plug.kNotUndoable)
        return self.getOriginalPlug() is not None

    def typeId(self):
        return ApplyConnectionOverride.kTypeId

    def typeName(self):
        return ApplyConnectionOverride.kTypeName

    def _restoreOriginalPlug(self, original):
        # If the original shading engine was in a referenced file, the
        # connection to it may have been broken.  To deal with this
        # case, we also stored the shading engine name as a string.
        originalStr = commonUtils.findPlug(
            self.thisMObject(), MaterialOverride.kShadingEngineNameLong)
        if originalStr is not None:
            originalNode = commonUtils.nameToNode(originalStr.asString())
            if not originalNode.isNull():
                fnEngine = OpenMaya.MFnDependencyNode(originalNode)
                enginePlug = fnEngine.findPlug('message', False)
                utils.connect(enginePlug, original)

    def getOriginalPlug(self):
        original = commonUtils.findPlug(self.thisMObject(), ApplyConnectionOverride.kOriginalLong)
        if not original.isConnected:
            self._restoreOriginalPlug(original)
        return original

    def getTarget(self):
        '''Return the target's plug. This is held by the apply override with the highest priority.'''
        return self._getLast()._targetHandle.src()
    
    def connectTarget(self, target):
        '''Connect the argument MPlug source to this node's target plug
        destination, to store it.'''
        self._targetHandle.connect(target)

    def isEnabled(self):
        return self.getEnabledPlug().asBool()

    def getPrevPlug(self):
        return OpenMaya.MPlug(self.thisMObject(), ApplyConnectionOverride.aPrevious)

    def getNextPlug(self):
        return OpenMaya.MPlug(self.thisMObject(), ApplyConnectionOverride.aNext)
    
    def _getLast(self):
        '''Returns the last applied override in the chain (higher priority).'''
        applyNode = self
        for applyNode in ApplyConnectionOverride.forwardGenerator(applyNode):
            pass
        return applyNode

    def update(self):
        last = self._getLast()
        toApply = (ao for ao in ApplyConnectionOverride.reverseGenerator(last) if ao.isEnabled() or not ao.prev()).next()
        target = last._targetHandle.src()
        enabled = toApply.isEnabled()
        source = toApply.override()._getAttrValuePlug() if enabled else toApply.getOriginalPlug()
        # If disabled, we're restoring the original.
        with guard.StateGuardCtx(isRestoringOriginal, setRestoringOriginal, not enabled):
            self.override().doAction(target=target, source=source)
        
    def prev(self):
        '''Returns the previous connection override in the chain (lower priority) if any, None otherwise.'''
        userNode = utils.getSrcUserNode(self.getPrevPlug())
        return userNode if isinstance(userNode, ApplyConnectionOverride) else None
    
    def next(self):
        '''Returns the next connection override in the chain (higher priority) if any, None otherwise.'''
        userNodes = utils.getDstUserNodes(self.getNextPlug())
        return userNodes[0] if userNodes and isinstance(userNodes[0], ApplyConnectionOverride) else None
    
    def moveTargetTo(self, to):
        '''Move the target of this ApplyConnectionOverride to the argument
         ApplyConnectionOverride.'''
        target = self._targetHandle.src()
        self._targetHandle.disconnect()
        to.connectTarget(target)

    def insert(self, target, nextOvr=None):
        '''Insert self in the override chain for given target, or start the chain if none exists.'''
        destinations = (OpenMaya.MFnDependencyNode(d.node()).userNode() for d in target.destinations())
        firstApplyNode = next((d for d in destinations if d and isinstance(d, ApplyConnectionOverride)), None)
        
        if not firstApplyNode:
            # no apply override chain on that target => self becomes the only apply override node for that target
            self.connectTarget(target)
            self.override().doSaveOriginal(target, self.getOriginalPlug())
            return
        utils.transferPlug(firstApplyNode.getOriginalPlug(), self.getOriginalPlug())
        
        # search where to insert
        if not nextOvr:
            prevAO, nextAO = firstApplyNode, None
        else:
            nextAO = (ao for ao in ApplyConnectionOverride.reverseGenerator(firstApplyNode) if ao.override() == nextOvr).next()
            prevAO = nextAO.prev()
        
        # insert between prevAO and nextAO
        if prevAO:
            utils.connect(prevAO.getNextPlug(), self.getPrevPlug())
        
        if nextAO:
            utils.connect(self.getNextPlug(), nextAO.getPrevPlug())
        else:
            # no nextAO => self becomes highest priority => must hold target
            prevAO.moveTargetTo(self)
    
    def extract(self):
        '''Removes self from the apply override chain. This will trigger an update of the chain.'''
        prevAO, nextAO = self.prev(), self.next()
        
        if prevAO:
            utils.disconnect(prevAO.getNextPlug(), self.getPrevPlug())
        
        if nextAO:
            utils.disconnect(self.getNextPlug(), nextAO.getPrevPlug())
        elif prevAO:
            # no nextAO => prevAO becomes highest priority => must hold target
            self.moveTargetTo(prevAO)
        
        if prevAO and nextAO:
            utils.connect(prevAO.getNextPlug(), nextAO.getPrevPlug())
        
        if not prevAO and not nextAO:
            # no other apply overrides => must restablish original connection
            with guard.StateGuardCtx(isRestoringOriginal, setRestoringOriginal, True):
                self.override().doAction(self._targetHandle.src(), self.getOriginalPlug())
        else:
            # any apply override in the chain can trigger the update
            (prevAO or nextAO).update()

    @staticmethod
    def reverseGenerator(applyNode):
        """ Generator to iterate on apply override nodes in the direction of
        lower-priority apply override nodes.

        When more than one override applies to a single overridden attribute, a
        chain of apply override nodes is formed, with the highest priority
        apply override nodes directly connected to the overridden attribute,
        and previous overrides having lower priority.

        In such a case, the 'next' plug of a lower-priority apply override node
        is connected to the 'previous' plug of a higher-priority apply override
        node. Moving up a chain of apply override nodes from higher priority
        to lower priority therefore means traversing the connection from the
        'previous' plug (destination) of the higher-priority node to the 'next'
        plug (source) of the lower-priority node. """

        while applyNode:
            yield applyNode
            # Move to previous (lower-priority) apply override.
            applyNode = applyNode.prev()

    @staticmethod
    def forwardGenerator(applyNode):
        """Generator to iterate on apply override nodes in the direction of
        higher-priority apply override nodes.

        See reverseGenerator() documentation. Moving down a chain of apply
        override nodes from lower priority to higher priority means traversing
        the connection from the 'next' plug (source) of the lower-priority
        node to the 'previous' plug (destination) of the higher-priority node."""

        while applyNode:
            yield applyNode
            # Move to next (higher-priority) apply override.
            applyNode = applyNode.next()
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
