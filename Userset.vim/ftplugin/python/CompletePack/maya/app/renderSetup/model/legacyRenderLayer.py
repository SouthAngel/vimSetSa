""" Legacy Render layer utility functions.
"""

import maya.cmds as cmds

import maya.app.renderSetup.common.profiler as profiler
# Python 1.0 API for render setup.  Remember that Python 1.0 API MObject's
# are not compatible with Python 2.0 API MObject's.
import maya.OpenMayaRender as OpenMayaRender

def create(parentName):
    with profiler.ProfilerMgr('create'):
        newName = 'rs_%s' % parentName
        return cmds.createRenderLayer(name=newName, empty=True)


def rename(oldLegacyRenderLayerName, newParentName):
    with profiler.ProfilerMgr('rename'):
        cmds.rename(oldLegacyRenderLayerName,  'rs_%s' % newParentName)


def delete(legacyRenderLayerName):
    with profiler.ProfilerMgr('legacyRenderLayer::delete'):
        cmds.delete(legacyRenderLayerName)


def removeNodes(legacyRenderLayerName):
    with profiler.ProfilerMgr('legacyRenderLayer::removeNodes'):
        nodeList = cmds.editRenderLayerMembers(legacyRenderLayerName, query=True, fullNames=True)
        if nodeList:
            nodes = [node for node in nodeList if cmds.objExists(node)]
            cmds.editRenderLayerMembers(legacyRenderLayerName, nodes, remove=True)


def appendNodes(legacyRenderLayerName, nodeNames):
    with profiler.ProfilerMgr('legacyRenderLayer::appendNodes'):
        cmds.editRenderLayerMembers(legacyRenderLayerName, list(nodeNames), noRecurse=True)


def makeVisible(legacyRenderLayerName):
    with profiler.ProfilerMgr('legacyRenderLayer::makeVisible'):
        OpenMayaRender.MRenderSetupPrivate._switchToLegacyRenderLayer(legacyRenderLayerName)



def isVisible(legacyRenderLayerName):
    with profiler.ProfilerMgr('legacyRenderLayer::isVisible'):
        currentName = cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True)
        return legacyRenderLayerName==currentName

def isRenderable(legacyRenderLayerName):
    with profiler.ProfilerMgr('legacyRenderLayer::isRenderable'):
        return cmds.getAttr(legacyRenderLayerName + '.renderable')

def setRenderable(legacyRenderLayerName, value):
    with profiler.ProfilerMgr('legacyRenderLayer::setRenderable'):
        cmds.setAttr(legacyRenderLayerName + '.renderable', value)


def renderSetupLayer(legacyRenderLayerName):
    rsLayer = cmds.listConnections(legacyRenderLayerName + '.msg', type='renderSetupLayer')
    return None if rsLayer is None else rsLayer[0]
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
