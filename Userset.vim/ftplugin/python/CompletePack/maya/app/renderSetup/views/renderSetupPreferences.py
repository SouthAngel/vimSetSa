from maya.app.renderSetup.views.renderSetupPreferencesViewsStrings import *

import maya.app.renderSetup.model.renderSetupPreferences as prefs
import maya.app.renderSetup.model.renderSettings as renderSettings

import maya.cmds as cmds

import json
import os

def _syncOptionVarWithTextField(userTextField, option):
    path = cmds.textField(userTextField, query=True, text=True)
    cmds.optionVar(stringValue=(option, path))

def _selectPath(userTextField, option, title):
    initialPath = cmds.optionVar(query=option)
    userChoices = cmds.fileDialog2(startingDirectory=initialPath, fileMode=2, caption=title)
    if userChoices is not None and userChoices[0] != "":
        cmds.textField(userTextField, edit=True, text=userChoices[0])
        _syncOptionVarWithTextField(userTextField, option)

def addRenderSetupPreferences():
    cmds.frameLayout(label=kRenderSetupTemplatesTitle)
    cmds.columnLayout(adjustableColumn=True)

    # Build the User Templates Location
    cmds.rowLayout(numberOfColumns=4, columnWidth=[(1,50), (2,130), (4,20)], adjustableColumn=3,\
        columnAttach4=('left', 'both', 'both', 'right'), \
        columnAlign4=('left', 'left', 'left', 'left'))
    cmds.text(label="")
    cmds.text(label=kUserTemplatesLocation)
    userTextField = cmds.textField(text=prefs.getUserTemplateDirectory())
    cmd1 = 'maya.app.renderSetup.views.renderSetupPreferences._syncOptionVarWithTextField(\'%s\', \'%s\')' % (userTextField, prefs.kOptionVarUserTemplateDirectory)
    cmds.textField(userTextField, edit=True, changeCommand=cmd1)
    cmd2 = 'maya.app.renderSetup.views.renderSetupPreferences._selectPath(\'%s\', \'%s\', \'%s\')' % (userTextField, prefs.kOptionVarUserTemplateDirectory, kSelectUserTemplatesLocation)
    cmds.symbolButton(image='navButtonBrowse.png', command=cmd2)
    cmds.setParent('..')

    # Build the Global Template Location
    cmds.rowLayout(numberOfColumns=4, columnWidth=[(1,40), (2,140), (4,20)], adjustableColumn=3,\
        columnAttach4=('left', 'both', 'both', 'right'), \
        columnAlign4=('left', 'left', 'left', 'left'))
    cmds.text(label="")
    cmds.text(label=kGlobalTemplatesLocation)
    userTextField = cmds.textField(text=prefs.getGlobalTemplateDirectory())
    cmd1 = 'maya.app.renderSetup.views.renderSetupPreferences._syncOptionVarWithTextField(\'%s\', \'%s\')' % (userTextField, prefs.kOptionVarGlobalTemplateDirectory)
    cmds.textField(userTextField, edit=True, changeCommand=cmd1)
    cmd2 = 'maya.app.renderSetup.views.renderSetupPreferences._selectPath(\'%s\', \'%s\', \'%s\')' % (userTextField, prefs.kOptionVarGlobalTemplateDirectory, kSelectUserTemplatesLocation)
    cmds.symbolButton(image='navButtonBrowse.png', command=cmd2)
    cmds.setParent('..')

    cmds.setParent('..')
    cmds.frameLayout(label=kRenderSettingsPresetsTitle)
    cmds.columnLayout(adjustableColumn=True)
    
    # Build the User Presets Location
    cmds.rowLayout(numberOfColumns=4, columnWidth=[(1,65), (2,115), (4,20)], adjustableColumn=3,\
        columnAttach4=('left', 'both', 'both', 'right'), \
        columnAlign4=('left', 'left', 'left', 'left'))
    cmds.text(label="")
    cmds.text(label=kUserPresetsLocation)
    userTextField = cmds.textField(text=prefs.getUserPresetsDirectory())
    cmd1 = 'maya.app.renderSetup.views.renderSetupPreferences._syncOptionVarWithTextField(\'%s\', \'%s\')' % (userTextField, prefs.kOptionVarUserPresetsDirectory)
    cmds.textField(userTextField, edit=True, changeCommand=cmd1)
    cmd2 = 'maya.app.renderSetup.views.renderSetupPreferences._selectPath(\'%s\', \'%s\', \'%s\')' % (userTextField, prefs.kOptionVarUserPresetsDirectory, kSelectUserPresetsLocation)
    cmds.symbolButton(image='navButtonBrowse.png', command=cmd2)
    cmds.setParent('..')

    # Build the Global Presets Location
    cmds.rowLayout(numberOfColumns=4, columnWidth=[(1,54), (2,126), (4,20)], adjustableColumn=3,\
        columnAttach4=('left', 'both', 'both', 'right'), \
        columnAlign4=('left', 'left', 'left', 'left'))
    cmds.text(label="")
    cmds.text(label=kGlobalPresetsLocation)
    userTextField = cmds.textField(text=prefs.getGlobalPresetsDirectory())
    cmd1 = 'maya.app.renderSetup.views.renderSetupPreferences._syncOptionVarWithTextField(\'%s\', \'%s\')' % (userTextField, prefs.kOptionVarGlobalPresetsDirectory)
    cmds.textField(userTextField, edit=True, changeCommand=cmd1)
    cmd2 = 'maya.app.renderSetup.views.renderSetupPreferences._selectPath(\'%s\', \'%s\', \'%s\')' % (userTextField, prefs.kOptionVarGlobalPresetsDirectory, kSelectUserPresetsLocation)
    cmds.symbolButton(image='navButtonBrowse.png', command=cmd2)
    cmds.setParent('..')

    cmds.setParent('..')

# Saves a preset to a user specified location. Note: for testing purposes, a
# filename can be passed in, this should only be used for testing!
def savePreset(filePath=None):
    basePath = prefs.getUserPresetsDirectory()
    if not os.path.exists(basePath):
        os.makedirs(basePath)
    
    
    # Display the file dialog if we're not testing
    selectedFilePath = [filePath] if filePath is not None else (
                       cmds.fileDialog2(caption=kSavePreset,
                                        fileFilter='*.'+prefs.getFileExtension(), dialogStyle=2,
                                        startingDirectory=basePath))
    if selectedFilePath is not None and len(selectedFilePath[0]) > 0:
        rs = renderSettings.encode()
        with open(selectedFilePath[0], "w+") as file:
            json.dump(rs, fp=file, indent=2, sort_keys=True)

# Loads the specified preset from the specified directory
def _loadPreset(preset, basePath):
    presetFile = preset + '.'+prefs.getFileExtension()
    with open(os.path.join(basePath, presetFile)) as file:
        try:
            renderSettings.decode(json.load(file))
        except:
            cmds.error(kInvalidPresetFound % os.path.join(basePath, presetFile))

# Loads the specified user preset.
def loadUserPreset(preset):
    _loadPreset(preset, prefs.getUserPresetsDirectory())

# Loads the specified global preset.
def loadGlobalPreset(preset):
    _loadPreset(preset, prefs.getGlobalPresetsDirectory())
            
# Deletes a user preset. Note: for testing purposes, noWarn can be set to True
# to prevent a warning popup box on delete, this should only be used for 
# testing!
def deleteUserPreset(preset, warn=True):
    basePath = prefs.getUserPresetsDirectory()
    presetFile = preset + '.'+prefs.getFileExtension()
    
    message =  kDeletePresetMsg % preset
    delete =  kDelete
    cancel =  kCancel
    if warn:
        confirmResponse = cmds.confirmDialog(title=kDeletePreset, button=[delete, cancel], cancelButton=cancel, defaultButton=delete, message=message)
    if (not warn or delete == confirmResponse):
        os.remove(os.path.join(basePath, presetFile))

# Returns the list of presets in the specified base path.
def _getPresets(renderer, basePath):
    presets = []
    if basePath is not None and os.path.exists(basePath):
        presetFiles = [f for f in os.listdir(basePath) if os.path.isfile(os.path.join(basePath, f)) and os.path.splitext(f)[1] == '.'+prefs.getFileExtension()]
        for presetFile in presetFiles:
            with open(os.path.join(basePath, presetFile)) as file:
                try:
                    rs = json.load(file)
                    if renderer in rs:
                        presets.append(os.path.splitext(presetFile)[0])
                except:
                    cmds.warning(kInvalidPresetFound % os.path.join(basePath, presetFile))
    return presets

# Returns the list of presets in the user presets directory.
def getUserPresets(renderer):
    return _getPresets(renderer, prefs.getUserPresetsDirectory())

# Returns the list of presets in the global presets directory.
def getGlobalPresets(renderer):
    return _getPresets(renderer, prefs.getGlobalPresetsDirectory())
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
