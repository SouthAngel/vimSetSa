import maya.mel as mel
import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya

import maya.app.renderSetup.views.viewCmds as viewCmds

from maya.app.renderSetup.views.renderSetupPreferences import addRenderSetupPreferences

import maya.app.renderSetup.views.propertyEditor.initialize as propertyEditorInitialize
import maya.app.renderSetup.views.proxy.initialize as proxyInitialize

commands = [viewCmds.RenderSetupSelectCmd, viewCmds.RenderSetupHighlightCmd]

_initializeModules = [propertyEditorInitialize, proxyInitialize]


def initialize(mplugin):

    mel.eval('source \"renderSetupImportExportCallbacks.mel\"')

    cmds.callbacks(addCallback=addRenderSetupPreferences, hook='addMayaRenderingPreferences', owner='renderSetup')

    for cmd in commands:
        try:
            mplugin.registerCommand(cmd.kCmdName, cmd.creator, createSyntaxFunc=cmd.createSyntax)
        except:
            OpenMaya.MGlobal.displayError('Register failed for %s' % cmd.kCmdName)

    for m in _initializeModules:
        m.initialize()

def uninitialize(mplugin):

    for m in _initializeModules:
        m.uninitialize()

    cmds.callbacks(removeCallback=addRenderSetupPreferences, hook='addMayaRenderingPreferences', owner='renderSetup')
    
    for cmd in commands:
        try:
            mplugin.deregisterCommand(cmd.kCmdName)
        except:
            OpenMaya.MGlobal.displayError('Unregister failed for %s' % cmd.kCmdName)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
