
import maya.app.renderSetup.views.viewCmds as viewCmds

import maya.app.renderSetup.model.collection as collection
import maya.app.renderSetup.model.renderSetup as renderSetupModel
import maya.app.renderSetup.model.utils as utils

def _getSources(nodeName):
    '''Returns objects to add override in.
    i.e. selected collections in the visible render layer if any, or the layer itself otherwise.'''
    visibleLayer = renderSetupModel.instance().getVisibleRenderLayer()
    dic = { name:utils.nameToUserNode(name) for name in viewCmds.getSelection(collections=True) }
    collections = [node for name,node in dic.iteritems() if node.getRenderLayer() == visibleLayer and node.parent().name() not in dic]
    finalCollections = set([])
    for col in collections:
        finalCollections.add(visibleLayer.getCorrespondingCollection(nodeName, col.name()))
    if len(finalCollections) > 0:
        return list(finalCollections)
    else:
        return [visibleLayer]

def createAbsoluteOverride(nodeName, attrName):
    """ Add an absolute override to selected collections part of the visible render layer 
    or to the layer itself if no collections are selected """
    for source in _getSources(nodeName):
        source.createAbsoluteOverride(nodeName, attrName)

def createRelativeOverride(nodeName, attrName):
    """ Add a relative override to the selected collections part of the visible render layer
    or to the layer itself if no collections are selected """
    for source in _getSources(nodeName):
        source.createRelativeOverride(nodeName, attrName)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
