"""Overridden attribute manager.

The overridden attribute manager is a singleton that observes the scene to
react to attribute changes.  If the attribute change is on an attribute
that is overridden by render setup, the attribute manager will attempt to
take the value change and reproduce it on the override itself.

This allows for convenient workflows like using direct manipulation on an
object with a value override, where the value is actually written back to
the override.

Apply value override nodes conditionally implement the passive output plug
behavior, through a chain of responsibility.  A passive output allows
setting its destination input.  If this destination input is connected to
an apply override node, the overridden attribute manager asks the
highest-priority apply override node to write the value to its
corresponding override, if it's enabled, else pass the request to the next
lower-priority apply override node.  The chain ends by writing into the
original.  If the highest-priority apply override node returns true from
isPassiveOutput(), this means that the overridden attribute write must
succeed, as one of the apply override nodes in the chain will accept the
write.

Autokey functionality is supported in this framework: in autokey mode, we
query the auto keyer to ask if an overridden attribute would be auto-keyed.
If so, we add the override attribute to the list of attributes the auto
keyer will add keys to.  See the autoKey render setup module and the
autoKeyframe command for more information.

Note that it is understood that changing the override value will cause all
overridden attributes to change."""

import maya.app.renderSetup.model.renderSetup as renderSetup
import maya.app.renderSetup.model.applyOverride as applyOverride
import maya.app.renderSetup.model.utils as utils
import maya.app.renderSetup.model.autoKey as autoKey
import maya.app.renderSetup.model.typeIDs as typeIDs
import maya.app.renderSetup.model.plug as plug

import maya.api.OpenMaya as OpenMaya

# The singleton itself.
_instance = None

def isDefaultRenderLayerVisible():
    return not renderSetup.hasInstance() or \
        renderSetup.instance().getDefaultRenderLayer().isVisible()

def instance():
    return _instance

def initialize():
    global _instance
    assert _instance is None, 'Overridden attribute manager already initialized.'
    _instance = OverriddenAttributeManager()

def finalize():
    global _instance
    assert _instance is not None, 'Overridden attribute manager not initialized.'
    _instance.aboutToDelete()
    _instance = None

class OverriddenAttributeManager(object):
    """Observe and react to overridden attribute changes.

    The overridden attribute manager attempts to convert changes to
    overridden attributes to changes to overrides.  See the module
    documentation for more details.

    The overridden attribute manager is only active when a render layer
    other than the default (or master) layer is visible."""

    def __init__(self):
        super(OverriddenAttributeManager, self).__init__()

        self._cbId = None

        # Register to observe creation / destruction of render setup.
        renderSetup.addObserver(self)

        # Register to observe visible render layer changes.
        if renderSetup.hasInstance():
            self.renderSetupAdded()

        # If we're already in a layer other than master, observe attribute
        # changes.
        if not isDefaultRenderLayerVisible():
            self.addAttributeChangeObservation()

    def aboutToDelete(self):
        """Final clean up before the manager is destroyed."""

        # Unregister from observation of render setup creation / destruction.
        renderSetup.removeObserver(self)

        self.renderSetupPreDelete()

    def renderSetupPreDelete(self):
        """Called just before the render setup node is deleted.

        Unregisters from visible render layer and attribute change
        observation."""

        # Called from aboutToDelete, so not guaranteed we have an instance.
        if renderSetup.hasInstance():
            rs = renderSetup.instance()
            if rs.hasActiveLayerObserver(self.onRenderLayerChanged):
                rs.removeActiveLayerObserver(self.onRenderLayerChanged)

        self.removeAttributeChangeObservation()

    def renderSetupAdded(self):
        """Called just after the render setup node has been added."""
        renderSetup.instance().addActiveLayerObserver(self.onRenderLayerChanged)

        # We might be called as a result of file open.  Make sure we
        # observe attribute changes.
        self.onRenderLayerChanged()

    def onRenderLayerChanged(self):
        """Called after the visible render layer has been changed."""

        if not isDefaultRenderLayerVisible():
            self.addAttributeChangeObservation()
        else:
            self.removeAttributeChangeObservation()

    def addAttributeChangeObservation(self):
        """Start observing DG attribute changes."""
        if self._cbId is None:
            self._cbId = OpenMaya.MNodeMessage.addAttributeChangedCallback(
                OpenMaya.MObject.kNullObj, self.onAttributeChanged)

    def removeAttributeChangeObservation(self):
        """End observation of DG attribute changes."""
        if self._cbId is not None:
            OpenMaya.MMessage.removeCallback(self._cbId)
            self._cbId = None

    def onAttributeChanged(self, msg, plg, otherPlug, clientData):
        if msg & OpenMaya.MNodeMessage.kAttributeSet:
            # Plug itself might be overridden, or its parent might be
            # overridden.
            plugs = [plg]
            if plg.isChild:
                plugs.append(plg.parent())

            for p in plugs:
                # Get rid of uninteresting plugs as quickly as possible.
                # 
                # 1) Overridden plug is connected, by definition.
                if not p.isConnected:
                    continue

                # 2) If plug's node is a render setup node, not interesting.
                nodeFn = OpenMaya.MFnDependencyNode(p.node())
                if typeIDs.isRenderSetupType(nodeFn.typeId):
                    continue

                # Check if the plug is connected to an apply override node.
                src = utils.plugSrc(p)
                if src is None:
                    continue

                node = OpenMaya.MFnDependencyNode(src.node()).userNode()
                
                if not isinstance(node, applyOverride.ApplyOverride):
                    continue

                # Query the autoKeyer only if a plug is interesting.
                # Autokeyer should not be listening during undo / redo,
                # only when the attribute is initially set.
                if 'autoKeyedAttr' not in locals():
                    inUndoRedo = OpenMaya.MGlobal.isUndoing() or \
                                 OpenMaya.MGlobal.isRedoing()
                    autoKeyedAttr = set() if inUndoRedo else autoKey.autoKeyed()

                autoKeyed = p.name() in autoKeyedAttr

                # At this point we know the node can handle the override.
                # No need to call ApplyValueOverride.canHandleSetOverride
                # to validate, because that method has been called by
                # isPassiveOutput, which returned true to allow the
                # attribute to be changed and therefore end up in this
                # notification.
                node.handleSetOverride(p, autoKeyed)
                # all plugs between override and target plug should never be dirty
                plug.Plug(p).value

                break
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
