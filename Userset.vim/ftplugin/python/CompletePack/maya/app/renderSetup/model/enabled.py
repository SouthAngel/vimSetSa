"""Utilities to implement hierarchical enabling of overrides and collections.

   Render setup overrides and collections can be enabled and disabled.

   Disabling an override removes its effect, but keeps the override itself.

   Disabling a collection disables all the overrides in its list, as well
   as disabling any child (nested) collection it may have.

   To implement this behavior, overrides and collections have three
   attributes:

   1) An enabled attribute.  This attribute is readable only (output), and
      is (trivially) computed from the two following attributes.
   2) A self enabled attribute.  This writable attribute determines whether
      the override or collection itself is enabled.
   3) A parent enabled attribute.  This writable attribute is connected to
      its parent's enabled output attribute, unless it is a collection
      immediately under a render layer.

   The enabled output boolean value is the logical and of the self enabled
   attribute and the parent enabled attribute."""

import maya.app.renderSetup.common.guard as guard

import maya.api.OpenMaya as OpenMaya

# On collection enabled changed, we pull on connection attribute enabled,
# to force the connection apply override update to run.
_pulling = False

def setPulling(value):
    _pulling = value
    
def isPulling():
    return _pulling

def createBoolAttribute(longName, shortName, defaultValue):
    """ Helper method to create an input (writable) boolean attribute """

    attrFn = OpenMaya.MFnNumericAttribute()
    attr = attrFn.create(
        longName, shortName, OpenMaya.MFnNumericData.kBoolean, defaultValue)
    attrFn.writable = True
    attrFn.storable = True
    attrFn.keyable  = False

    return attr

def createIntAttribute(longName, shortName, defaultValue):
    """ Helper method to create an input (writable) int attribute """

    attrFn = OpenMaya.MFnNumericAttribute()
    attr = attrFn.create(
        longName, shortName, OpenMaya.MFnNumericData.kInt, defaultValue)
    attrFn.writable = True
    attrFn.storable = True
    attrFn.keyable  = False

    return attr
    
def createBoolOutputAttribute(longName, shortName, defaultValue):
    """ Helper method to create an output (readable) boolean attribute """

    attrFn = OpenMaya.MFnNumericAttribute()
    attr = attrFn.create(
        longName, shortName, OpenMaya.MFnNumericData.kBoolean, defaultValue)
    attrFn.readable = True
    attrFn.writable = False
    attrFn.storable = False
    return attr

def createHiddenIntAttribute(longName, shortName):
    """Helper method to create a hidden, readable, non-keyable, and
    writable integer attribute."""

    numAttrFn = OpenMaya.MFnNumericAttribute() 
    attr = numAttrFn.create(longName, shortName, OpenMaya.MFnNumericData.kInt, 0)
    numAttrFn.storable = True
    numAttrFn.keyable = False
    numAttrFn.readable = True
    numAttrFn.writable = True
    numAttrFn.hidden = True
    return attr

def createNumIsolatedChildrenAttribute():
    """Helper method to create the number of isolated children attribute.

    This renderLayer and collection attribute is a count of the number
    of isolate selected children in the subtree of the render layer
    or collection."""

    return createHiddenIntAttribute("numIsolatedChildren", "nic")

def initializeAttributes(cls):

    cls.selfEnabled = createBoolAttribute('selfEnabled', 'sen', 1)
    cls.addAttribute(cls.selfEnabled)

    cls.parentEnabled = createBoolAttribute('parentEnabled', 'pen', 1)
    cls.addAttribute(cls.parentEnabled)

    # NOTE: this function is called by override classes, and therefore adds
    # a "parentNumIsolatedChildren" attribute to them.  This attribute is
    # unused by overrides, so the addition is undesirable (but harmless)
    # for overrides.  Keeping attribute for overrides to avoid backward
    # compatibility issues.  PPT, 25-Apr-2016
    #
    # Keeping attribute name identical to 2016_R2, to avoid backward
    # compatibility issues.  PPT, 22-Apr-2016.
    cls.layerNumIsolatedChildren = createIntAttribute('parentNumIsolatedChildren', 'pic', 0)
    cls.addAttribute(cls.layerNumIsolatedChildren)
    
    # Add the enabled output attribute.
    cls.enabled = createBoolOutputAttribute('enabled', 'en', 1)
    cls.addAttribute(cls.enabled)
    
    # Add dependencies
    cls.attributeAffects(cls.selfEnabled, cls.enabled)
    cls.attributeAffects(cls.parentEnabled, cls.enabled)
    cls.attributeAffects(cls.layerNumIsolatedChildren, cls.enabled)

def computeParentEnabled(node, dataBlock):
    """Compute the parent enabled input while avoiding DG cycle check warnings."""
    # Avoid DG cycle check warnings.  A collection that computes its
    # enabled output notifies its observers in attrChangedCB, which is
    # still considered to be within the scope of the computation.  The
    # collection will pull on its connection override children enabled
    # outputs, which asks for the parent enabled output, which is a cycle
    # (compute collection enabled, notify, pull and compute child enabled,
    # ask for collection enabled).  Avoid this by using our own cached
    # value for the enabled output in such a case, which requires us to set
    # the parentEnabled input clean.  This violates the DG requirement that
    # all values used to compute an output attribute should be read from
    # the data block, but should be safe in pratice.
    parent = node.parent()
    if parent is not None and parent._inEnabledChanged:
        parentEnabled = parent.cachedEnabled
        # See selector.Selector.compute comments.
        dataBlock.setClean(node.parentEnabled)
    else:
        parentEnabledHandle = dataBlock.inputValue(node.parentEnabled)
        parentEnabled = parentEnabledHandle.asBool()

    return parentEnabled

def computeEnabled(node, dataBlock):
    '''Returns the enabled state based on the basic conditions (selfEnabled and parentEnabled).'''

    return dataBlock.inputValue(node.selfEnabled).asBool() and \
        computeParentEnabled(node, dataBlock)
    
def compute(node, plug, dataBlock):
    '''
    Computes the enabled plug with the basic conditions (selfEnabled and parentEnabled).
    Do not use if 'enabled' depends on other attributes.
    '''
    if (plug == node.enabled):
        setEnabledOutput(node, dataBlock, computeEnabled(node, dataBlock))

def setEnabledOutput(node, dataBlock, value):
    outHandle = dataBlock.outputValue(node.enabled)
    outHandle.setBool(value)
    # DG cycle check warning avoidance.  See computeParentEnabled comments. 
    node.cachedEnabled = value
    dataBlock.setClean(node.enabled)

def addChangeCallbacks(node):
    """Add callbacks to indicate the argument node's enabled attribute changed.

    A list of callback IDs is returned."""

    # Need two callbacks to notify of enabled change, which work in sequence:
    #
    # 1) The dirty callback notifies that the enabled attribute must be
    #    computed.
    # 
    #    However, notifying that enabled has changed at this point is
    #    incorrect.  For example, calling setSelfEnabled() will set the
    #    selfEnabled attribute, which will dirty the enabled attribute on
    #    the node.  If we notify with enabledChanged() at this point, this
    #    will call code that triggers evaluation of enabled through
    #    compute().  However, the value of selfEnabled in the datablock has
    #    not yet been changed (setSelfEnabled() is not yet complete), and
    #    the datablock holds the previous value.  The result of compute()
    #    is therefore incorrect.
    #
    #    We must delay notification until enabled is actually computed, for
    #    which we use the following callback.  We simply record that
    #    enabled is dirty.
    #
    # 2) Next time the enabled attribute is evaluated, if it's dirty, send
    #    the enabledChanged() notification and reset dirty.
    #
    # Note that there is no use of
    # MNodeMessage.addAttributeChangedCallback() that directly does what we
    # want, as MNodeMessage.kAttributeEval is generated for each
    # evaluation, and MNodeMessage.kAttributeSet is generated only for
    # writable (input) attributes, not for output attributes.

    def dirtyCB(nodeObj, plug, data):
        # As per documentation, dirty callback is sent for input
        # attributes only.  Need to check if enabled output attribute
        # is dirty.
        fn = OpenMaya.MFnDependencyNode(nodeObj)
        affectedAttributes = fn.getAffectedAttributes(plug.attribute())

        # Using MFnDependencyNode.getAffectedAttributes() is overkill,
        # as the affects relationship between enabled and its inputs is
        # static.  However, keeping a separate static list for this
        # purpose violates the DRY (Don't Repeat Yourself) principle,
        # and there is no practical performance impact in recomputing it.
        if type(node).enabled in affectedAttributes:
            node._enabledDirty = True

    def attrChangedCB(msg, plug, otherPlug, clientData):
        if plug.attribute() == type(node).enabled and \
           msg & OpenMaya.MNodeMessage.kAttributeEval and \
           node._enabledDirty:
            node._enabledDirty = False
            # DG cycle check warning avoidance.  See computeParentEnabled
            # comments. 
            with guard.MemberGuardCtx(node, '_inEnabledChanged', True):
                node.enabledChanged()

    # Create the callbacks
    attrChangedId = OpenMaya.MNodeMessage.addAttributeChangedCallback(
        node.thisMObject(), attrChangedCB)

    dirtyId = OpenMaya.MNodeMessage.addNodeDirtyPlugCallback(
        node.thisMObject(), dirtyCB)

    return [attrChangedId, dirtyId]
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
