'''
This module encapsulates the local override enabled state.
Applied enabled (selfEnabled) local overrides should not report being enabled in batch mode or on export.
'''

import maya.api.OpenMaya as OpenMaya
import maya.cmds as cmds
import maya.app.renderSetup.model.utils as utils

def _toggle(ovrs):
    for ov in ovrs:
        ov.setSelfEnabled(False)
        ov.setSelfEnabled(True)

class ExportListener(object):
    '''
    This instance listen for export callbacks (before/after).
    Ensures that all calls to ov.isEnabled() for every applied local override
    will return false during export time.
    '''
    # This is a workaround to fake batch mode in non batch mode...
    # This listener will toggle override.selfEnabled for all applied enabled local override
    # this will force enabled plug to be pulled (since it's dirty) and will henceforth return
    # false during export time (see enabled() function bellow).
    # The selfEnabled attribute is toggled back after export to dirty enabled again and will 
    # then return true next time it is queried.
    
    _instance = None
    
    @staticmethod
    def instance():
        if ExportListener._instance is None:
            import maya.app.renderSetup.model.renderSetup as renderSetup
            assert renderSetup.hasInstance(), "Should not create an ExportListener instance without Render Setup instance."
            ExportListener._instance = ExportListener()
        return ExportListener._instance
    
    @staticmethod
    def deleteInstance():
        if ExportListener._instance is not None:
            for id in ExportListener._instance._cbIds:
                OpenMaya.MMessage.removeCallback(id)
        ExportListener._instance = None
    
    def __init__(self):
        callbacks = { OpenMaya.MSceneMessage.kBeforeExport : self._beforeExport,
                      OpenMaya.MSceneMessage.kAfterExport  : self._afterExport }
        self._cbIds = [ OpenMaya.MSceneMessage.addCallback(type, callback) \
            for type,callback in callbacks.iteritems() ]
        self._exporting = False
        self._enabledLocalOverrides = []
        
    def _beforeExport(self, clientData):
        import maya.app.renderSetup.model.renderSetup as renderSetup
        rs = renderSetup.instance()
        self._enabledLocalOverrides = [] if rs.getDefaultRenderLayer().isVisible() else \
            filter(lambda ov: ov.isLocalRender() and ov.isEnabled(), utils.getOverridesRecursive(rs.getVisibleRenderLayer()))
        self._exporting = True
        _toggle(self._enabledLocalOverrides)
    
    def _afterExport(self, clientData):
        self._exporting = False
        _toggle(self._enabledLocalOverrides)
        self._enabledLocalOverrides = []

    def isExporting(self):
        return self._exporting
    

def enabled():
    return not cmds.about(batch=True) and not ExportListener.instance().isExporting()
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
