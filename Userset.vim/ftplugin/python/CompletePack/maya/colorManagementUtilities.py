import maya.cmds as cmds

def __runCommand(cmdName, parameterContent):
    return eval(cmdName + parameterContent)

#
# Purpose: Updates the gamma of the Editor
#
def updateGamma(editor, floatFieldPath, cmdName) :
    value = cmds.floatField(floatFieldPath, q=True, value=True)
    parameterContent = '("{theEditor}", e=True, gamma={gamma})'.format(theEditor=editor, gamma=value)
    __runCommand(cmdName, parameterContent)

#
# Purpose: Updates the exposure of the Editor
#
def updateExposure(editor, floatFieldPath, cmdName) :
    value = cmds.floatField(floatFieldPath, q=True, value=True)
    parameterContent = '("{theEditor}", e=True, exposure={exposure})'.format(theEditor=editor, exposure=value)
    __runCommand(cmdName, parameterContent)

#
# Purpose: Synchronizes the gamma of the editor with a floatField
#
def syncGammaField(editor, floatFieldPath, cmdName) :
    parameterContent = '("{theEditor}", e=True, toggleGamma=True)'.format(theEditor=editor)
    __runCommand(cmdName, parameterContent)
    parameterContent = '("{theEditor}", q=True, gamma=True)'.format(theEditor=editor)
    value = __runCommand(cmdName, parameterContent)
    cmds.floatField(floatFieldPath, e=True, value=value)

#
# Purpose: Synchronizes the exposure of the editor with a floatField
#
def syncExposureField(editor, floatFieldPath, cmdName) :
    parameterContent = '("{theEditor}", e=True, toggleExposure=True)'.format(theEditor=editor)
    __runCommand(cmdName, parameterContent)
    parameterContent = '("{theEditor}", q=True, exposure=True)'.format(theEditor=editor)
    value = __runCommand(cmdName, parameterContent)
    cmds.floatField(floatFieldPath, e=True, value=value)

#
# Purpose: Toggles the color management in the editor
#
def toggleCM(editor, buttonPath, cmdName) :
    enabled = cmds.symbolCheckBox(buttonPath, q=True, value=True )
    globalCmEnabled = cmds.colorManagementPrefs(q=True, cmEnabled=True)
    parameterContent = '("{theEditor}", e=True, cmEnabled={cmEnabled})'.format(theEditor=editor, cmEnabled= enabled)
    __runCommand(cmdName, parameterContent)
    cmds.symbolCheckBox(buttonPath, e=True, enable=globalCmEnabled)

#
# Purpose: Sets the viewTransformName used by the Editor
#
def setViewTransform(editor, optionMenuPath, cmdName) :
    newVtName = cmds.optionMenu(optionMenuPath, q=True, value=True )
    parameterContent = '("{theEditor}", q=True, viewTransformName=True)'.format(theEditor=editor)
    curVtName = __runCommand(cmdName, parameterContent)
    try:
        parameterContent = '("{theEditor}", e=True, viewTransformName="{vtName}")'.format(theEditor=editor, vtName=newVtName)
        __runCommand(cmdName, parameterContent)
    except RuntimeError:
        cmds.optionMenu(optionMenuPath, e=True, value=curVtName )
        raise



# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
