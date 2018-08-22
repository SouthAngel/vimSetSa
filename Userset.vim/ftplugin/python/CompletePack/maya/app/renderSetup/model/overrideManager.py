"""
    This module provides backward compatibility for the override manager class.
"""

import maya.app.renderSetup.model.utils as utils
import maya.api.OpenMaya as OpenMaya
import maya.OpenMaya as OpenMaya1_0

from maya.app.renderSetup.model.connectionOverride import ApplyConnectionOverride

def deleteApplyOverrideChain(last):
    '''Delete a chain of apply override nodes.

    The argument is the last apply override node in the chain.'''

    aoObjs = [ao.thisMObject() for ao in ApplyConnectionOverride.reverseGenerator(last)]
    dgMod = OpenMaya.MDGModifier()
    for obj in aoObjs:
        dgMod.deleteNode(obj)
    dgMod.doIt()

def postConstructor(layer):
    # backward compatibility for when layers derived from overrideManager class
    # They were defined as:
    # "
    # The overrideManager class has an array of override elements that represents the overrides currently applied to
    # the scene where each such element holds a connection from the target attribute (the attribute being overridden)
    # and a connection from the apply node operating on that attribute. If there are more than one apply node 
    # operating on the same target attribute they form a chain where the first one in the chain is connected to the element. 
    # "
    # i.e. They were the end point of the apply connection override nodes
    #
    layer._backwardCompID = None
    if OpenMaya1_0.MFileIO.isReadingFile():
        # if file was saved in a visible layer with override manager attributes used (i.e. connection override using layer as override manager),
        # then opening file will fail if these attributes are missing.
        # 1) Create dynamic attribute array on file open 
        # 2) Transfer them to the apply nodes after file open (all apply overrides hold original and most prioritary override hold target)
        # 3) Remove dynamic attributes array
        fnCompoundAttr = OpenMaya.MFnCompoundAttribute()
        aOverrides = fnCompoundAttr.create("overrides", "ovrs")
        aTarget = utils.createGenericAttr("target", "tg")
        aApplyNode = utils.createDstMsgAttr("applyNode", "an")
        fnCompoundAttr.addChild(aTarget)
        fnCompoundAttr.addChild(aApplyNode)
        fnCompoundAttr.array = True
        OpenMaya.MFnDependencyNode(layer.thisMObject()).addAttribute(aOverrides)
        
        if not OpenMaya1_0.MFileIO.isReferencingFile():
            handle = OpenMaya.MObjectHandle(layer.thisMObject())
            def transferAttributes(clientData=None):
                if layer._backwardCompID is None:
                    return
                OpenMaya.MSceneMessage.removeCallback(layer._backwardCompID)
                layer._backwardCompID = None
                if not handle.isValid():
                    # layer was destroyed before the end of file open
                    return
                arrayPlug = OpenMaya.MPlug(layer.thisMObject(), aOverrides)
                for i in xrange(arrayPlug.evaluateNumElements()):
                    plug = arrayPlug.elementByLogicalIndex(i)
                    target = plug.child(aTarget)
                    applyOv = plug.child(aApplyNode)
                    # target and applyOv plugs are always as a pair.
                    # 
                    # Since apply override nodes are always in the scene
                    # (never referenced, and thus never unloaded), the
                    # connection to them must exist.
                    #
                    # The target plug is different: if the target pointed
                    # to a referenced node, that node might not be loaded,
                    # and thus target would not be connected.  For versions
                    # of Maya where this code applies, there is no way to
                    # recover the target by name, so the whole apply
                    # override node chain is stale, and should be removed.
                    # Otherwise, connection apply override unapply code
                    # pre-conditions and invariants cannot be guaranteed.
                    #
                    # Correctness is still obtained through brute force 
                    # post-read re-application of the render layer (see
                    # model.renderSetup.RenderSetup._afterOpenCB).

                    ao = OpenMaya.MFnDependencyNode(
                        applyOv.source().node()).userNode()

                    if target.isConnected:
                        ao.connectTarget(target.source())
                        utils.disconnect(target.source(), target)
                        utils.disconnect(applyOv.source(), applyOv)
                    else:
                        # Apply override node chain is stale.  Get rid of it.
                        # This will disconnect applyOv from its source.
                        deleteApplyOverrideChain(ao)

                OpenMaya.MFnDependencyNode(layer.thisMObject()).removeAttribute(aOverrides)
            
            # transferAttributes is a closure around declared variables in this function (postConstructor)
            # That's why it can still reference them when called on after open callback
            # It's a call-once function (called after file open). 
            # (Attributes only need to be transfered once, applying layers later on will no longer use the layer as override manager)
            layer._transferAttributes = transferAttributes
            layer._backwardCompID = OpenMaya.MSceneMessage.addCallback(OpenMaya.MSceneMessage.kAfterOpen, layer._transferAttributes, None)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
