import maya.api.OpenMaya as OpenMaya
import maya.OpenMaya
import maya.cmds as cmds

import maya.app.renderSetup.model.renderSetup as renderSetup
from maya.app.renderSetup.model.renderLayer import RenderLayer
from maya.app.renderSetup.model.selector import Selector, BasicSelector, SimpleSelector
import maya.app.renderSetup.model.nodeList as nodeList
import maya.app.renderSetup.model.nodeListPrivate as nodeListPrivate
from maya.app.renderSetup.model.collection import getAllCollectionClasses
import maya.app.renderSetup.model.override as override
from maya.app.renderSetup.model.overrideUtils import getAllOverrideClasses
from maya.app.renderSetup.model.applyOverride import getAllApplyOverrideClasses
import maya.app.renderSetup.model.dragAndDropBehavior as dragAndDropBehavior
import maya.app.renderSetup.model.childNode as childNode
import maya.app.renderSetup.model.renderSetupPrivate as renderSetupPrivate
import maya.app.renderSetup.model.modelCmds as modelCmds
import maya.app.renderSetup.model.fileLoadMonitor as fileLoadMonitor
import maya.app.renderSetup.model.undo as undo
import maya.app.renderSetup.model.plug as plug
import maya.app.renderSetup.model.shadingNodes as shadingNodes
import maya.app.renderSetup.model.overriddenAttributeManager as overriddenAttributeManager

# The list of all nodes needed by the model layer
#
# Note: The order of initialization is critical, as base classes must be
# initialized first, before derived classes call inheritAttributesFrom() their
# base class.
#
nodeTypes  = [nodeList.ListItem, childNode.ChildNode, Selector, BasicSelector, SimpleSelector, RenderLayer, renderSetup.RenderSetup ]
nodeTypes += getAllCollectionClasses()
nodeTypes += getAllOverrideClasses()
nodeTypes += getAllApplyOverrideClasses()

commands = [nodeListPrivate.RemoveCmd, nodeListPrivate.InsertCmd,
            nodeListPrivate.InsertBeforeCmd, nodeListPrivate.AppendCmd, 
            nodeListPrivate.PrependCmd, nodeListPrivate.PopCmd,
            override.UnapplyCmd, childNode.EditImportedStatusCmd,
            modelCmds.RenderLayerMembersCmd, modelCmds.RenderSetupFindCmd,
            renderSetupPrivate.SwitchVisibleRenderLayerCmd,
            undo.NotifyPostRedoCmd, undo.NotifyPostUndoCmd,
            plug.AddDynamicAttribute,
            renderSetupPrivate.PostApplyCmd
]
syntaxCommands = [modelCmds.RenderSetupCmd, modelCmds.RenderSetupLegacyLayerCmd]

nodeDragAndDropBehaviors = [dragAndDropBehavior.ConnectionOverrideDragAndDrop]

# cmd.error() both displays the error to the user and raises a RuntimeError.

def initialize(mplugin):

    if maya.OpenMaya.MGlobal.mayaState() == maya.OpenMaya.MGlobal.kInteractive:
        # Source MEL scripts needed by this plugin
        maya.mel.eval('source \"connectionOverrideUI.mel\"')

    for type in nodeTypes:
        try:
            # The nodes need to be classified in order for the map button to appear 
            # when creating UI controls for the node attributes.
            mplugin.registerNode(
                type.kTypeName, type.kTypeId, type.creator, type.initializer, OpenMaya.MPxNode.kDependNode, renderSetup.getClassification(type))
        except:
            OpenMaya.MGlobal.displayError('Register failed for %s' % type.kTypeName)
    
    for type in getAllApplyOverrideClasses():
        cmds.setNodeTypeFlag(type.kTypeName, display=False)

    for cmd in commands:
        try:
            mplugin.registerCommand(cmd.kCmdName, cmd.creator) 
        except:
            OpenMaya.MGlobal.displayError('Register failed for %s' % cmd.kCmdName)

    for cmd in syntaxCommands:
        try:
            mplugin.registerCommand(cmd.kCmdName, cmd.creator, createSyntaxFunc=cmd.createSyntax) 
        except:
            cmds.error('Register failed for %s' % cmd.kCmdName)

    for dnd in nodeDragAndDropBehaviors:
        try:
            mplugin.registerDragAndDropBehavior(dnd.kTypeName, dnd.creator) 
        except:
            OpenMaya.MGlobal.displayError('Register failed for %s' % dnd.kTypeName)

    shadingNodes.initialize()
    renderSetup.initialize()
    fileLoadMonitor.initialize()
    overriddenAttributeManager.initialize()
    
    renderSetup.setPluginObject(mplugin)

def uninitialize(mplugin):

    overriddenAttributeManager.finalize()
    fileLoadMonitor.finalize()
    renderSetup.finalize()

    # When a node has a drawdb classification, there is a OGS callback called on deregisterNode. 
    # In this callback, it is looping over the node type and ITS ANCESTORS... 
    # If the ancestors are already deleted, then it leads to invalid memory reference => crash
    # => must deregister nodes in reversed order
    for type in reversed(nodeTypes):
        try:
            mplugin.deregisterNode(type.kTypeId)
        except:
            OpenMaya.MGlobal.displayError('Unregister failed for %s' % type.kTypeName)

    for cmd in commands:
        try:
            mplugin.deregisterCommand(cmd.kCmdName) 
        except:
            OpenMaya.MGlobal.displayError('Unregister failed for %s' % cmd.kCmdName)

    for cmd in syntaxCommands:
        try:
            mplugin.deregisterCommand(cmd.kCmdName) 
        except:
            cmds.error('Unregister failed for %s' % cmd.kCmdName)

    for dnd in nodeDragAndDropBehaviors:
        try:
            mplugin.deregisterDragAndDropBehavior(dnd.kTypeName) 
        except:
            OpenMaya.MGlobal.displayError('Unregister failed for %s' % dnd.kTypeName)

    shadingNodes.uninitialize()

    renderSetup.setPluginObject(None)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
