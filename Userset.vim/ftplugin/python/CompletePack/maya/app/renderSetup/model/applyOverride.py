"""Override application node classes and utility functions.

   This module provides classes that perform the application of overrides.
   It includes base and concrete classes, as well as utility functions to
   operate on override application nodes.

   Override application nodes are created when an override is applied.
   They allow the override value to be evaluated by the Maya DG, or
   optionally disabled.  Since they are Maya DG nodes, they persist and will
   be saved to file if the Maya scene is saved when a given render layer is
   current.

   Overrides and their application nodes have the following characteristics:

   - One override, multiple nodes: within a single render layer, an
     override can apply to multiple nodes. To support override removal on
     layer change and simple override muting, the override must remember the
     previous value or previous connection for each attribute.

   - One attribute, multiple overrides: within a single render layer, a
     single attribute on a node can have multiple overrides, for three
     reasons:

     -- Collections are non-exclusive: a node can be in more than one 
        collection. This is both by design, for flexibility (a node can have 
        properties that make it a part of more than one group of nodes), and 
        also in part because since a node can be made part of multiple 
        collections dynamically (e.g. through name wildcards or explicitly
        through a static selection), it is difficult to prevent nodes from being 
        exclusively in a single collection. 
     -- Value overrides can be relative: relative overrides modify an
        existing input value, which itself can be an override 
        or an absolute override: the output value is the 'imposed' value.
     -- Render layers can have overrides: render layers can apply
        overrides, outside of, and in addition to, collections.

     Because of this, there is potentially a chain of override application
     nodes connected to an overridden attribute, with the closest override
     application node having the highest priority.

   - Overrides are connections: relative overrides and material assignment
     overrides must be connections, by their very nature. Absolute
     overrides should be connections, to support animation. In theory, a
     non-animated override could be implemented without a connection, but
     updating or muting the value would require editing all nodes for which
     the override applies. Using a connection to a single value makes this
     trivial."""

import maya.api.OpenMaya as OpenMaya

import maya.app.renderSetup.model.typeIDs as typeIDs
import maya.app.renderSetup.model.utils as utils
import maya.app.renderSetup.model.plug as plug
import maya.app.renderSetup.model.autoKey as autoKey
import maya.app.renderSetup.common.utils as commonUtils

# Python 1.0 API for MFileIO.  Remember that Python 1.0 API MObject's
# are not compatible with Python 2.0 API MObject's.
import maya.OpenMaya as OpenMaya1_0

def _createInputAttribute(attrClass, longAttrName, shortAttrName, attrTypeId, defaultValue):
    """ Helper method to create a typed attribute """
    attrFn = attrClass()
    attr = attrFn.create(longAttrName, shortAttrName, attrTypeId, defaultValue)
    attrFn.writable = True
    attrFn.readable = False
    attrFn.storable = True
    attrFn.keyable  = False
    return attr
    
def _createOutputAttribute(attrClass, longAttrName, shortAttrName, attrTypeId, defaultValue):
    """ Helper method to create a typed attribute """
    attrFn = attrClass()
    attr = attrFn.create(longAttrName, shortAttrName, attrTypeId, defaultValue)
    attrFn.readable = True
    attrFn.writable = False
    attrFn.storable = False
    attrFn.keyable  = False
    return attr


class LeafClass(object):
    """ To be used by leaf classes only """
    def isAbstractClass(self):
        # False means that the class is a leaf class
        return False

class ApplyValueOverride(object):
    """Mixin class to support applying value overrides.

       The chain of apply override nodes for an attribute acts as a
       handler in a chain of responsibility design pattern when the
       overridden attribute is set (written to).  This class implements
       support for this chain of responsibility."""

    def isPassiveOutput(self, plug):
        # During Maya file read, writes to the apply override node can
        # occur before it is connected to the override node, simply by
        # virtue of connectAttr statements being at end of file.  Assume
        # the file was in a valid state when it was saved (which will be
        # true unless the file is edited by hand), and be permissive.
        return plug.attribute() == self.out and \
            (OpenMaya1_0.MFileIO.isReadingFile() or \
             self.canHandleSetOverride())

    def isInvertible(self):
        """Can input values be found that produce a given output value?"""
        # By default, all apply value overrides are invertible.
        return True

    def canHandleSetOverride(self):
        """Can this apply override node handle a set override value request?

        This predicate indicates whether the apply override can handle such
        a request.  If true, Maya will accept writes to the overridden
        attribute.  If false, the overridden attribute cannot be written to."""

        # If the apply override node is enabled:
        # 
        # o The override can be set if the apply override node is
        #   invertible, that is, given an output value, we can find inputs
        #   that produce this output.
        # o Additionally, the override's value must be settable.
        #
        # If the apply override node is disabled:
        #
        # o If the original plug is connected to a (lower-priority) apply
        #   override node, we forward the call to it, the next handler in
        #   the chain of responsibility.
        # o If the original plug is not connected to an apply override
        #   node, we check if the plug is settable.
        if self.isEnabled():
            return self.isInvertible() and self.isOverrideValueSettable()
        else:
            original = self.getOriginalPlug()
            previous = connectedSrc(original)
            return previous.canHandleSetOverride() if previous else \
                plug.isSettable(original)
        
    def handleSetOverride(self, overriddenPlug, autoKeyed):
        """Handle a set override request.

        This is the chain of responsibility handler that sets (writes) the
        override value.  It assumes that canHandleSetOverride has returned
        true for this node.

        If autoKeyed is True, autoKeyframe will be given the override
        attribute that ultimately receives the value, so that a keyframe
        will be set on the override (or the original) if the autoKeyframe
        conditions to set a keyframe are met."""

        if self.isEnabled():
            self.setOverrideValue(overriddenPlug, autoKeyed)
        else:
            # Override is disabled, therefore apply override is disabled as
            # well: forward to next handler in the chain, if it exists,
            # else write to original, which will succeed because
            # canHandleSetOverride returned true.
            original = self.getOriginalPlug()
            previous = connectedSrc(original)
            if previous:
                # Forward to next handler in the chain.
                previous.handleSetOverride(overriddenPlug, autoKeyed)
            else:
                # Write to original.
                # Apply override nodes obtain all values in ui units because of the unit conversion nodes (if any)
                # => the original plug (that belongs to the apply override node) must be in ui units
                autoKey.setValue(original, plug.Plug(overriddenPlug).uiUnitValue, autoKeyed)


class ApplyOverride(OpenMaya.MPxNode):
    """Apply an override to an input attribute.

    This is a base class that cannot be directly created in Maya.

    To conform with the apply override interface, base classes must supply
    two attributes:

    - The "original" attribute: this input (destination) attribute
      is either a copy of the overridden attribute's value (if the original
      attribute on the node was unconnected), or the new destination of
      what was originally connected to the overridden attribute.

    - The "out" attribute: this output (source) attribute is the result of
      the computation of the apply override node.

    Both attributes are typed by apply override leaf classes.

    Correspondingly, derived classes must provide the following two
    accessors in their interface: getOriginalPlug() and getOutputPlug().

    These attributes are important when defining a chain of apply override
    nodes, when more than one override applies to a single overridden
    attribute.  The output plug of a lower-priority apply override node is
    then connected to the original plug of a higher-priority apply override
    node.  Moving up a chain of apply override nodes from higher priority
    to lower priority therefore means traversing the connection from the
    original plug (destination) of the higher-priority node to the output
    plug (source) of the lower-priority node."""

    kTypeId = typeIDs.applyOverride
    kTypeName = "applyOverride"

    # Attribute name for dynamic attribute storing whether apply override
    # was applied to a main scene node.  Presence of the attribute means
    # the apply override node was applied to a node not in the main scene,
    # e.g. a file referenced node.
    kNotOnMainSceneShort = 'nms'
    kNotOnMainSceneLong  = 'notOnMainScene'

    @classmethod
    def creator(cls):
        return cls()

    @staticmethod
    def initializer():
        ApplyOverride.enabled = _createInputAttribute(
            OpenMaya.MFnNumericAttribute, "enabled", "en", OpenMaya.MFnNumericData.kBoolean, 1)
        ApplyOverride.addAttribute(ApplyOverride.enabled)
        
    @classmethod
    def _baseInitialize(cls, attrClass, attrTypeId, defaultValue):        
        # Add the output value attribute
        cls.out = \
            _createOutputAttribute(attrClass, "out", "o", attrTypeId, defaultValue)
        cls.addAttribute(cls.out)
    
        # Add the original value attribute
        cls.original = \
            _createInputAttribute(attrClass, "original", "ori", attrTypeId, defaultValue)
        cls.addAttribute(cls.original)
        cls.attributeAffects(cls.original, cls.out)
    
        cls.attributeAffects(cls.enabled, cls.out)
        
    def __init__(self):
        super(ApplyOverride, self).__init__()

    def isAbstractClass(self):
        # Used only as base class, cannot be created.
        return True

    def isEnabled(self):
        return self.getEnabledPlug().asBool()
    
    def getEnabledPlug(self):
        return OpenMaya.MPlug(self.thisMObject(), self.enabled)
        
    def getOriginalPlug(self):
        return OpenMaya.MPlug(self.thisMObject(), self.original)

    def getOutputPlug(self):
        return OpenMaya.MPlug(self.thisMObject(), self.out)

    def override(self):
        """Return the override that corresponds to this apply override node."""

        # Use the enabled plug connection to find the override node.
        return utils.getSrcUserNode(self.getEnabledPlug())

    def onMainScene(self):
        """Applied to a node not in the main scene?

        Nodes that are not in the main scene include file referenced nodes and 
        nodes in scene assemblies.  These nodes might not be loaded."""

        return not OpenMaya.MFnDependencyNode(self.thisMObject()).hasAttribute(
            self.kNotOnMainSceneShort)

    def setNotOnMainScene(self):
        """Mark as applied to a node that is not in the main scene.

        Nodes that are not in the main scene include file referenced nodes and 
        nodes in scene assemblies.  These nodes might not be loaded."""
        properties = {'type' : 'Bool', 'connectable' : False}
        plug.Plug.createAttribute(self.thisMObject(), self.kNotOnMainSceneLong, 
                                  self.kNotOnMainSceneShort, properties)

class ApplyAbsOverride(ApplyValueOverride, ApplyOverride):
    """Apply an absolute override.

       If the enabled boolean input is false, return the original input, else 
       return the value input."""

    kTypeId   = typeIDs.applyAbsOverride
    kTypeName = 'applyAbsOverride'

    @staticmethod
    def initializer():
        ApplyAbsOverride.inheritAttributesFrom(ApplyOverride.kTypeName)
    
    @classmethod
    def _initialize(cls, attrClass, attrTypeId, defaultValue):
        """Private initializer for ApplyAbsOverride children classes.
           Children must call this function in the initializer method."""
        cls.inheritAttributesFrom(ApplyAbsOverride.kTypeName)
        cls._baseInitialize(attrClass, attrTypeId, defaultValue)

        # Add the abs value attribute
        cls.attrValue = \
            _createInputAttribute(attrClass, "value", "val", attrTypeId, defaultValue)
        cls.addAttribute(cls.attrValue)
        cls.attributeAffects(cls.attrValue, cls.out)
        
    def __init__(self):
        super(ApplyAbsOverride, self).__init__()
        
    def _compute(self, plug, dataBlock, getMtd, setMtd):
        if (plug == self.out):
            enabled = dataBlock.inputValue(self.enabled).asBool()

            valueHandle = dataBlock.inputValue(self.attrValue if enabled else self.original)

            outHandle = dataBlock.outputValue(self.out)
            value = getMtd(valueHandle)
            setMtd(outHandle, value)
            dataBlock.setClean(plug)
        
    def getValuePlug(self):
        return OpenMaya.MPlug(self.thisMObject(), self.attrValue)

    def setOverrideValue(self, overriddenPlug, autoKeyed):
        autoKey.setValue(
            self.override()._getAttrValuePlug(), 
            plug.value(overriddenPlug), autoKeyed)

    def isOverrideValueSettable(self):
        override = self.override()
        return False if override is None else \
            plug.isSettable(override._getAttrValuePlug())


class ApplyRelOverride(ApplyValueOverride, ApplyOverride):
    """Apply a relative override.

       newValue = orginalValue * multiply + offset

       This override apply node will multiply the original value by a 'multiply value' and add an offset.
       If the enabled boolean input is false, the 'multiply value' is 1.0 and the offset is 0.0."""

    kTypeId = typeIDs.applyRelOverride
    kTypeName = 'applyRelOverride'

    @staticmethod
    def initializer():
        ApplyRelOverride.inheritAttributesFrom(ApplyOverride.kTypeName)
        
    @classmethod
    def _initialize(cls, attrTypeId, modifiersAttrTypeId):
        """Private initializer for ApplyRelOverride children classes.
           Children must call this function in the initializer method."""
        cls.inheritAttributesFrom(ApplyRelOverride.kTypeName)
        attrClass = OpenMaya.MFnNumericAttribute
        cls._baseInitialize(attrClass, attrTypeId, 0)
        
        # Add the multiply attribute
        cls.multiply = \
            _createInputAttribute(attrClass, "multiply", "mul", modifiersAttrTypeId, 1.0)
        cls.addAttribute(cls.multiply)
        cls.attributeAffects(cls.multiply, cls.out)

        # Add the offset attribute
        cls.offset = \
            _createInputAttribute(attrClass, "offset", "ofs", modifiersAttrTypeId, 0)
        cls.addAttribute(cls.offset)
        cls.attributeAffects(cls.offset, cls.out)

    def __init__(self):
        super(ApplyRelOverride, self).__init__()
        
    def _compute(self, plug, dataBlock, getMtd, setMtd, getModifierMtd):
        if (plug == self.out):
            enabled = dataBlock.inputValue(self.enabled).asBool()
            value = getMtd(dataBlock.inputValue(self.original))
            
            if enabled:
                multiply = getModifierMtd(dataBlock.inputValue(self.multiply))
                offset = getModifierMtd(dataBlock.inputValue(self.offset))
                value = map(lambda orig,mult,ofs: orig*mult+ofs, value, multiply, offset) \
                        if isinstance(value,list) else value * multiply + offset
            
            outHandle = dataBlock.outputValue(self.out)
            setMtd(outHandle, value)
            dataBlock.setClean(plug)
        
    def getMultiplyPlug(self):
        return OpenMaya.MPlug(self.thisMObject(), self.multiply)

    def getOffsetPlug(self):
        return OpenMaya.MPlug(self.thisMObject(), self.offset)

    def setOverrideValue(self, overriddenPlug, autoKeyed):
        def computeOutput(orig, mult, offset):
            return orig * mult + offset

        # Get our current offset value.
        offset0 = plug.Plug(self.getOffsetPlug()).value

        # Get our current output value, and the desired output value.
        # This is the line we wanted to write, but the output doesn't seem
        # to change when the parent (compound) attribute is written to.
        # outValue0 = plug.Plug(self.getOutputPlug()).value

        # Instead, repeat the output computation from compute().
        orig = plug.Plug(self.getOriginalPlug()).value
        mult = plug.Plug(self.getMultiplyPlug()).value

        outValue0 = map(computeOutput, orig, mult, offset0) if \
                  isinstance(orig, list) else \
                  computeOutput(orig, mult, offset0)

        # Apply override nodes obtain all values in ui units because of the unit conversion nodes (if any)
        # => all values must be read and computation must be performed in ui units
        ovrPlg = plug.Plug(overriddenPlug)
        outValue1 = ovrPlg.uiUnitValue

        # Compute the new offset, and set it onto the override.
        def computeOffset(out1, out0, offset0):
            return out1 - out0 + offset0

        offset1 = map(computeOffset, outValue1, outValue0, offset0) if \
                  isinstance(outValue0, list) else \
                  computeOffset(outValue1, outValue0, offset0)

        # convert to internal units since autoKey.setValue expects internal units
        offset1 = plug.toInternalUnits(ovrPlg.type, offset1)
        autoKey.setValue(self.override()._getOffsetPlug(), offset1, autoKeyed)

    def isOverrideValueSettable(self):
        # When we invert the apply relative override processing to set the
        # underlying override's inputs, we affect the offset.
        override = self.override()
        return False if override is None else \
            plug.isSettable(self.override()._getOffsetPlug())


class ApplyAbsFloatOverride(LeafClass, ApplyAbsOverride):
    """Apply a float absolute override."""

    kTypeId = typeIDs.applyAbsFloatOverride
    kTypeName = 'applyAbsFloatOverride'

    def __init__(self):
        super(ApplyAbsFloatOverride, self).__init__()

    @staticmethod
    def initializer():
        ApplyAbsFloatOverride._initialize(
            OpenMaya.MFnNumericAttribute,
            OpenMaya.MFnNumericData.kFloat, 0.0)
        
    def compute(self, plug, dataBlock):
        ApplyAbsOverride._compute(self, plug, dataBlock,
            OpenMaya.MDataHandle.asFloat, 
            OpenMaya.MDataHandle.setFloat)


class ApplyRelFloatOverride(LeafClass, ApplyRelOverride):
    """Apply a float relative override."""

    kTypeId = typeIDs.applyRelFloatOverride
    kTypeName = 'applyRelFloatOverride'

    def __init__(self):
        super(ApplyRelFloatOverride, self).__init__()

    @staticmethod
    def initializer():
        ApplyRelFloatOverride._initialize(
            OpenMaya.MFnNumericData.kFloat,
            OpenMaya.MFnNumericData.kFloat)

    def compute(self, plug, dataBlock):
        ApplyRelOverride._compute(self, plug, dataBlock,
            OpenMaya.MDataHandle.asFloat, 
            OpenMaya.MDataHandle.setFloat, 
            OpenMaya.MDataHandle.asFloat)


class ApplyAbsIntOverride(LeafClass, ApplyAbsOverride):
    """Apply an int absolute override."""

    kTypeId = typeIDs.applyAbsIntOverride
    kTypeName = 'applyAbsIntOverride'

    def __init__(self):
        super(ApplyAbsIntOverride, self).__init__()

    @staticmethod
    def initializer():
        ApplyAbsIntOverride._initialize(
            OpenMaya.MFnNumericAttribute,
            OpenMaya.MFnNumericData.kInt, 0)

    def compute(self, plug, dataBlock):
        ApplyAbsOverride._compute(self, plug, dataBlock,
            OpenMaya.MDataHandle.asInt, 
            OpenMaya.MDataHandle.setInt)


class ApplyRelIntOverride(LeafClass, ApplyRelOverride):
    """Apply an int relative override."""

    kTypeId = typeIDs.applyRelIntOverride
    kTypeName = 'applyRelIntOverride'

    def __init__(self):
        super(ApplyRelIntOverride, self).__init__()

    @staticmethod
    def initializer():
        ApplyRelIntOverride._initialize(
            OpenMaya.MFnNumericData.kInt,
            OpenMaya.MFnNumericData.kFloat)

    def compute(self, plug, dataBlock):
        ApplyRelOverride._compute(self, plug, dataBlock,
            OpenMaya.MDataHandle.asInt, 
            lambda handle,x: handle.setInt(int(x)), 
            OpenMaya.MDataHandle.asFloat)


class ApplyAbs3FloatsOverride(LeafClass, ApplyAbsOverride):
    """Apply a 3 floats absolute override."""

    kTypeId = typeIDs.applyAbs3FloatsOverride
    kTypeName = 'applyAbs3FloatsOverride'

    def __init__(self):
        super(ApplyAbs3FloatsOverride, self).__init__()

    @staticmethod
    def initializer():
        ApplyAbs3FloatsOverride._initialize(
            OpenMaya.MFnNumericAttribute,
            OpenMaya.MFnNumericData.k3Float, 0.0)
        
    def compute(self, plug, dataBlock):
        ApplyAbsOverride._compute(self, plug, dataBlock,
            OpenMaya.MDataHandle.asFloat3, 
            lambda handle,x: handle.set3Float(*x))


class ApplyRel3FloatsOverride(LeafClass, ApplyRelOverride):
    """Apply a 3 floats relative override."""

    kTypeId = typeIDs.applyRel3FloatsOverride
    kTypeName = 'applyRel3FloatsOverride'

    def __init__(self):
        super(ApplyRel3FloatsOverride, self).__init__()

    @staticmethod
    def initializer():
        ApplyRel3FloatsOverride._initialize(
            OpenMaya.MFnNumericData.k3Float,
            OpenMaya.MFnNumericData.k3Float)

    def compute(self, plug, dataBlock):
        ApplyRelOverride._compute(self, plug, dataBlock,
            OpenMaya.MDataHandle.asFloat3, 
            lambda handle,x: handle.set3Float(*x),
            OpenMaya.MDataHandle.asFloat3)
    

class ApplyAbsBoolOverride(LeafClass, ApplyAbsOverride):
    """Apply a boolean absolute override."""

    kTypeId = typeIDs.applyAbsBoolOverride
    kTypeName = 'applyAbsBoolOverride'

    def __init__(self):
        super(ApplyAbsBoolOverride, self).__init__()

    @staticmethod
    def initializer():
        ApplyAbsBoolOverride._initialize(
            OpenMaya.MFnNumericAttribute,
            OpenMaya.MFnNumericData.kBoolean, 0.0)

    def compute(self, plug, dataBlock):
        ApplyAbsOverride._compute(self, plug, dataBlock,
            OpenMaya.MDataHandle.asBool, 
            OpenMaya.MDataHandle.setBool)


class ApplyAbsEnumOverride(LeafClass, ApplyAbsOverride):
    """Apply an enum absolute override."""

    kTypeId = typeIDs.applyAbsEnumOverride
    kTypeName = 'applyAbsEnumOverride'

    def __init__(self):
        super(ApplyAbsEnumOverride, self).__init__()

    @staticmethod
    def initializer():
        ApplyAbsEnumOverride._initialize(
            OpenMaya.MFnNumericAttribute,
            OpenMaya.MFnNumericData.kInt, 0)

    def compute(self, plug, dataBlock):
        ApplyAbsOverride._compute(self, plug, dataBlock,
            OpenMaya.MDataHandle.asInt, 
            OpenMaya.MDataHandle.setInt)


class ApplyAbsStringOverride(LeafClass, ApplyAbsOverride):
    """Apply a string absolute override."""

    kTypeId = typeIDs.applyAbsStringOverride
    kTypeName = 'applyAbsStringOverride'

    def __init__(self):
        super(ApplyAbsStringOverride, self).__init__()

    @staticmethod
    def initializer():
        defaultString = OpenMaya.MFnStringData().create("")        
        ApplyAbsStringOverride._initialize(
            OpenMaya.MFnTypedAttribute,
            OpenMaya.MFnData.kString, defaultString)

    def compute(self, plug, dataBlock):
        ApplyAbsOverride._compute(self, plug, dataBlock,
            OpenMaya.MDataHandle.asString, 
            OpenMaya.MDataHandle.setString)


class ApplyAbs2FloatsOverride(LeafClass, ApplyAbsOverride):
    """Apply a 2 floats absolute override."""

    kTypeId = typeIDs.applyAbs2FloatsOverride
    kTypeName = 'applyAbs2FloatsOverride'

    def __init__(self):
        super(ApplyAbs2FloatsOverride, self).__init__()

    @staticmethod
    def initializer():
        ApplyAbs2FloatsOverride._initialize(
            OpenMaya.MFnNumericAttribute,
            OpenMaya.MFnNumericData.k2Float, 0.0)
        
    def compute(self, plug, dataBlock):
        ApplyAbsOverride._compute(self, plug, dataBlock,
            OpenMaya.MDataHandle.asFloat2, 
            lambda handle,x: handle.set2Float(*x))


class ApplyRel2FloatsOverride(LeafClass, ApplyRelOverride):
    """Apply a 2 floats relative override."""

    kTypeId = typeIDs.applyRel2FloatsOverride
    kTypeName = 'applyRel2FloatsOverride'

    def __init__(self):
        super(ApplyRel2FloatsOverride, self).__init__()

    @staticmethod
    def initializer():
        ApplyRel2FloatsOverride._initialize(
            OpenMaya.MFnNumericData.k2Float,
            OpenMaya.MFnNumericData.k2Float)

    def compute(self, plug, dataBlock):
        ApplyRelOverride._compute(self, plug, dataBlock,
            OpenMaya.MDataHandle.asFloat2, 
            lambda handle,x: handle.set2Float(*x),
            OpenMaya.MDataHandle.asFloat2)
    

def create(name, typeId):
    """ Create an apply override with type given by the argument type ID.

    Returns the MPxNode object corresponding to the created override node.
    A RuntimeError is raised in case of error."""

    fn = OpenMaya.MFnDependencyNode()
    fn.create(typeId, name)
    return fn.userNode()

def connectedSrc(dstPlug):
    """Return the apply override node connected to the destination plug,
    if one exists, else None."""

    userNode = utils.getSrcUserNode(dstPlug)
    return userNode if isinstance(userNode, ApplyOverride) else None

def reverseGenerator(dstPlug):
    """Generator to iterate on apply override nodes in the direction of
    lower-priority apply override nodes.

    When more than one override applies to a single overridden attribute, a
    chain of apply override nodes is formed, with the highest priority
    apply override nodes directly connected to the overridden attribute,
    and previous overrides having lower priority.

    In such a case, the output plug of a lower-priority apply override node
    is connected to the original plug of a higher-priority apply override
    node.  Moving up a chain of apply override nodes from higher priority
    to lower priority therefore means traversing the connection from the
    original plug (destination) of the higher-priority node to the output
    plug (source) of the lower-priority node."""    
 
    while dstPlug:
        applyOverride = connectedSrc(dstPlug)
        if applyOverride:
            yield applyOverride
            # Move to previous (lower-priority) apply override.
            dstPlug = applyOverride.getOriginalPlug()
        else:
            dstPlug = None

def connectedDst(srcPlug):
    """Return the apply override node connected to the source plug,
    if one exists, else None."""

    userNodes = utils.getDstUserNodes(srcPlug)
    if userNodes is None:
        return None

    return userNodes[0] if isinstance(userNodes[0], ApplyOverride) else None

def forwardGenerator(srcPlug):
    """Generator to iterate on apply override nodes in the direction of
    higher-priority apply override nodes.

    See reverseGenerator() documentation.  Moving down a chain of apply
    override nodes from lower priority to higher priority means traversing
    the connection from the output plug (source) of the lower-priority
    node to the original plug (destination) of the higher-priority node."""
 
    while srcPlug:
        applyOverride = connectedDst(srcPlug)
        if applyOverride:
            yield applyOverride
            # Move to next (higher-priority) apply override.
            srcPlug = applyOverride.getOutputPlug()
        else:
            srcPlug = None

def getAllApplyOverrideClasses():
    """ Returns the list of Apply Override subclasses """
    return commonUtils.getSubClasses(ApplyOverride)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
