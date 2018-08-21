"""
    This module defines private class and functions related to RenderSetup.
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya
import maya.app.renderSetup.model.undo as undo
import maya.app.renderSetup.model.namespace as namespace
from maya.app.renderSetup.model.renderLayerSwitchObservable import RenderLayerSwitchObservable

kCmdPrivate = maya.stringTable['y_renderSetupPrivate.kCmdPrivate' ]
kSwitchVisibleRenderLayer = maya.stringTable['y_renderSetupPrivate.kSwitchVisibleRenderLayer' ]

def _renderSetupInstance():
    import maya.app.renderSetup.model.renderSetup as renderSetup
    return renderSetup.instance()

class SwitchVisibleRenderLayerCmd(OpenMaya.MPxCommand):
    """Command to switch the visible layer.

    This command is a private implementation detail of this module and should
    not be called otherwise.
    """

    kCmdName = 'renderSetupSwitchVisibleRenderLayer'

    # Command data.  Must be set before creating an instance of the command
    # and executing it.  Ownership of this data is taken over by the
    # instance of the command.
    
    newLayer = None

    def isUndoable(self):
        return True

    def doIt(self, args):
        # Completely ignore the MArgList argument, as it's unnecessary:
        # arguments to the commands are passed in Python object form
        # directly to the command's constructor.

        if self.newLayer is None:
            cmds.warning(kCmdPrivate % self.kCmdName)
            return

        self.oldLayer = _renderSetupInstance().getVisibleRenderLayer()        
        self.redoIt()

    @staticmethod   
    def execute(newLayer):
        """ Switch to given RenderLayer """
        SwitchVisibleRenderLayerCmd.newLayer = newLayer
        with undo.CtxMgr(kSwitchVisibleRenderLayer % newLayer.name()):
            with namespace.RootNamespaceGuard():
                cmds.renderSetupSwitchVisibleRenderLayer()
        SwitchVisibleRenderLayerCmd.newLayer = None

    @staticmethod
    def creator():
        return SwitchVisibleRenderLayerCmd(SwitchVisibleRenderLayerCmd.newLayer)

    def __init__(self, newLayer):
        super(SwitchVisibleRenderLayerCmd, self).__init__()
        self.newLayer = newLayer
        self.oldLayer = None
        # Everytime it switches to a new layer, the layer cache is empty.
        # We initialize the saved cache to an empty list then. When restore is done for the
        # first time, it does not change the layer cache (still empty).
        self.savedLayerCache = []

    def _switchToLayer(self, oldLayer, newLayer):
        # On undo/redo, we do not want to pass through the _updateLegacyRenderLayerVisibility
        # condition, because it will trigger the commands twice (once in 
        # _updateLegacyRenderLayerVisibility and once because they are in the undo/redo chunk)
        # That's why we save the cache to reassign it in case of undo/redo
        # The first time it's done (through the doIt method), it will pass through
        # the _updateLegacyRenderLayerVisibility condition, and that's what we also want
        # Summary : We do not want to use commands during the undoIt/redoIt since it will
        # be added on the undo/redo stack but only use commands during the doIt
        self._saveAndRestoreCache(self.oldLayer, self.newLayer)

        oldLayer.unapply()
        oldLayer.itemChanged()
        # Since the layer is no more visible, clear the cache
        oldLayer.clearMemberNodesCache()
        
        # UI Feedback (progressBar)
        RenderLayerSwitchObservable.getInstance().notifyRenderLayerSwitchObserver()
        
        newLayer.apply()
        newLayer._updateLegacyRenderLayerVisibility()
        newLayer.itemChanged()
        newLayer.makeVisible()

        # UI Feedback (progressBar)
        RenderLayerSwitchObservable.getInstance().notifyRenderLayerSwitchObserver()
        _renderSetupInstance()._notifyActiveLayerObservers()

    def _saveAndRestoreCache(self, oldLayer, newLayer):
        self.newLayer.setMemberNodesCache(self.savedLayerCache)
        self.savedLayerCache = self.oldLayer.getMemberNodesCache()

    def redoIt(self):        
        self._switchToLayer(self.oldLayer, self.newLayer)

    def undoIt(self):
        self._switchToLayer(self.newLayer, self.oldLayer)

class PostApplyCmd(OpenMaya.MPxCommand):
    """Command to apply collection or override when the layer is already visible.
    This should apply the overrides in the right order, i.e. apply override nodes
    must be inserted at the right position in the apply chain.

    This command is a private implementation detail of this module and should
    not be called otherwise.
    """

    kCmdName = 'renderSetupPostApply'

    # Command data.  Must be set before creating an instance of the command
    # and executing it.  Ownership of this data is taken over by the
    # instance of the command.
    
    applicable = None

    def isUndoable(self):
        return True

    def doIt(self, args):
        # Completely ignore the MArgList argument, as it's unnecessary:
        # arguments to the commands are passed in Python object form
        # directly to the command's constructor.
        if self.applicable is None:
            cmds.warning(kCmdPrivate % self.kCmdName)
            return
        self.redoIt()

    @classmethod   
    def execute(cls, applicable):
        """ Applies an applicable (collection/override) after the layer was already set visible. """
        cls.applicable = applicable
        with undo.CtxMgr("Apply %s" % applicable.name()):
            with namespace.RootNamespaceGuard():
                cmds.renderSetupPostApply()
        cls.applicable = None

    @classmethod
    def creator(cls):
        return cls(cls.applicable)

    def __init__(self, applicable):
        super(PostApplyCmd, self).__init__()
        self.applicable = applicable

    def redoIt(self):
        self.applicable.postApply()

    def undoIt(self):
        self.applicable.unapply()


def moveModel(modelToMove, destinationModel, destinationPosition):
    ''' Helper method to move a model from a location to antoher location '''
    with undo.CtxMgr('Move %s to %s at position %d' % (modelToMove.name(), destinationModel.name(), destinationPosition)):
        sourceModel = modelToMove.parent()
        sourceModel.detachChild(modelToMove)
        destinationModel.attachChild(destinationPosition, modelToMove)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
