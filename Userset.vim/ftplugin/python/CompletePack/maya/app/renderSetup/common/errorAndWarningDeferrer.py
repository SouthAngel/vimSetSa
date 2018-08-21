import maya.api.OpenMaya as OpenMaya

# Note: this class was introduced as a work around. The problem is that the 
# render setup plugin is being loaded in loadPreferredRenderGlobalsPreset,
# and at that point, no warnings/errors can be displayed, so we decided to
# queue up the warnings/errors for display when the render setup window was
# opened.
class ErrorAndWarningDeferrer:
    def __init__(self):
        self.warnings = []
        self.errors = []
    
    def registerWarning(self, warning):
        self.warnings.append(warning)

    def registerError(self, error):
        self.errors.append(error)

    def displayErrorsAndWarnings(self, clearLog=True):
        for warning in self.warnings:
            OpenMaya.MGlobal.displayWarning(warning)
        for error in self.errors:
            OpenMaya.MGlobal.displayError(error)
        if clearLog:
            self.warnings = []
            self.errors = []

_instance = None
def instance():
    global _instance
    if not _instance:
	    _instance = ErrorAndWarningDeferrer()
    return _instance
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
