"""Utilities to test render setup drag and drop."""

import maya.app.renderSetup.views.proxy.renderSetup as renderSetupProxy
import maya.app.renderSetup.views.renderSetup as renderSetupUI
import maya.app.renderSetup.model.utils as utils
import maya.app.renderSetup.model.renderSetup as renderSetupModel

import PySide2.QtCore as QtCore

def mimeData(nodeNames):
    mimeData = QtCore.QMimeData()
    encodedData = QtCore.QByteArray()
    stream = QtCore.QDataStream(encodedData, QtCore.QIODevice.WriteOnly)
    for name in nodeNames:
        stream.writeString(name)
    mimeData.setData(renderSetupProxy.RENDER_SETUP_MIME_TYPE, encodedData)

    return mimeData

def dropOnto(nodeName, mimeData, row):
    # Note: If nodeName is None, then we are dropping onto the RenderSetup model.
    if nodeName != renderSetupModel.instance().name():
        n = utils.nameToUserNode(nodeName)
        nProxy = n.getOpaqueData(renderSetupProxy.PROXY_OPAQUE_DATA)()
    rsProxy = renderSetupUI.renderSetupWindow.centralWidget.renderSetupView.model()

    rsProxy.dropMimeDataFailure = False # Indicates if the drop was accepted
    rsProxy.dropMimeData(
        mimeData, QtCore.Qt.DropAction.MoveAction, row, 0, QtCore.QModelIndex() if nodeName==renderSetupModel.instance().name() else nProxy.index())
    
    return not rsProxy.dropMimeDataFailure
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
