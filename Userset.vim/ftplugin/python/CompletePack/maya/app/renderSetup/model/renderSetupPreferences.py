"""
    The file must contain all user preferences related to the Render Setup
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.cmds as cmds
import os

import maya.app.renderSetup.common.errorAndWarningDeferrer as errorAndWarningDeferrer

# When true puts the UI in edit mode after a render setup object creation 
kOptionVarEditMode = 'renderSetup_editMode'

# The default path to find the user render setup template files 
kOptionVarUserTemplateDirectory = 'renderSetup_userTemplateDirectory'

# The default path to find the global render setup template files 
kOptionVarGlobalTemplateDirectory = 'renderSetup_globalTemplateDirectory'

# The default path to find the user render setup presets files 
kOptionVarUserPresetsDirectory = 'renderSetup_userPresetsDirectory'

# The default path to find the global render setup presets files 
kOptionVarGlobalPresetsDirectory = 'renderSetup_globalPresetsDirectory'

# Error message to display when the global template path does not exist
kGlobalTemplatePathInvalid = maya.stringTable['y_renderSetupPreferences.kGlobalTemplatePathInvalid' ]

# Error message to display when the global presets path does not exist
kGlobalPresetsPathInvalid = maya.stringTable['y_renderSetupPreferences.kGlobalPresetsPathInvalid' ]

# When true Scene changes with automatically be applied to the current render layer.
kOptionVarUseDynamicUpdate = 'renderSetup_useDynamicUpdate'

def getEditMode():
    if not cmds.optionVar(exists=kOptionVarEditMode):
        cmds.optionVar(intValue=(kOptionVarEditMode, 1))

    return cmds.optionVar(query=kOptionVarEditMode)==1

def setEditMode(value):
    return cmds.optionVar(intValue=(kOptionVarEditMode, 1 if value else 0))

def _getUserDirectory(userDirectoryOptionVar, defaultUserDirectoryName):
    if not cmds.optionVar(exists=userDirectoryOptionVar):
        dstPath = os.path.join(os.getenv('MAYA_APP_DIR'), defaultUserDirectoryName)
        if not os.path.exists(dstPath):
            os.mkdir(dstPath)
        cmds.optionVar(stringValue=(userDirectoryOptionVar, dstPath))
    return cmds.optionVar(query=userDirectoryOptionVar)

def _getGlobalDirectory(globalDirectoryOptionVar):
    if cmds.optionVar(exists=globalDirectoryOptionVar):
        path = cmds.optionVar(query=globalDirectoryOptionVar)
        if os.path.exists(path):
            return path
    return None
    
def getUserTemplateDirectory():
    return _getUserDirectory(kOptionVarUserTemplateDirectory, 'RSTemplates')

def getGlobalTemplateDirectory():
    return _getGlobalDirectory(kOptionVarGlobalTemplateDirectory)

def getGlobalTemplateDirectoryWithoutCheck():
    """ For asynchronous purpose, we want to check if the path
    really exists AFTER getting the path string """
    if cmds.optionVar(exists=kOptionVarGlobalTemplateDirectory):
        return cmds.optionVar(query=kOptionVarGlobalTemplateDirectory)
    return None

def getUserPresetsDirectory():
    return _getUserDirectory(kOptionVarUserPresetsDirectory, 'Presets')

def getGlobalPresetsDirectory():
    return _getGlobalDirectory(kOptionVarGlobalPresetsDirectory)
    
def getFileExtension():
    return 'json'

def useDynamicUpdate():
    if not cmds.optionVar(exists=kOptionVarUseDynamicUpdate):
        cmds.optionVar(intValue=(kOptionVarUseDynamicUpdate, 0))

    return cmds.optionVar(query=kOptionVarUseDynamicUpdate)==1

def setUseDynamicUpdate(value):
    return cmds.optionVar(intValue=(kOptionVarUseDynamicUpdate, 1 if value else 0))

def initialize():
    # If the env. variable exists, override the optionVar value containing the global template path
    #
    defaultGlobalTemplatePath = os.getenv('MAYA_RENDER_SETUP_GLOBAL_TEMPLATE_PATH')
    if defaultGlobalTemplatePath is not None:
        if os.path.exists(defaultGlobalTemplatePath):
            cmds.optionVar(stringValue=(kOptionVarGlobalTemplateDirectory, defaultGlobalTemplatePath))
        else:
            errorAndWarningDeferrer.instance().registerWarning(kGlobalTemplatePathInvalid % defaultGlobalTemplatePath)
    
    # If the env. variable exists, override the optionVar value containing the global preset path
    #
    defaultGlobalPresetsPath = os.getenv('MAYA_RENDER_SETUP_GLOBAL_PRESETS_PATH')
    if defaultGlobalPresetsPath is not None:
        if os.path.exists(defaultGlobalPresetsPath):
            cmds.optionVar(stringValue=(kOptionVarGlobalPresetsDirectory, defaultGlobalPresetsPath))
        else:
            errorAndWarningDeferrer.instance().registerWarning(kGlobalPresetPathInvalid % defaultGlobalPresetsPath)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
