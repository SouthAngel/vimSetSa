import maya.cmds as cmds
import maya.mel as mel

from maya import OpenMayaUI as omui 

from PySide2.QtCore import Qt
from PySide2.QtGui import QMouseEvent, QPixmap
from shiboken2 import wrapInstance 

import maya.app.renderSetup.common.utils as commonUtils
import maya.app.renderSetup.model.plug as plug

kExpandedStateString = "expandedState"

_DPI_SCALE = 1.0 if not hasattr(cmds, "mayaDpiSetting") else cmds.mayaDpiSetting(query=True, realScaleValue=True)

def dpiScale(value):
    return value * _DPI_SCALE

def updateMouseEvent(event):
    # Handles one and two button mice CMD-click and Control-click events in
    # order to make it possible to right click and middle click with those mice.
    if cmds.about(mac=True):
        numMouseButtons = cmds.mouse(mouseButtonTrackingStatus=True)
        if numMouseButtons == 1:
            if event.modifiers() & Qt.MetaModifier:
                return QMouseEvent(event.type(),
                                   event.localPos(),
                                   event.windowPos(),
                                   event.screenPos(),
                                   Qt.RightButton,
                                   event.buttons(),
                                   event.modifiers() & ~Qt.MetaModifier,
                                   event.source())
            elif int(event.buttons()) & int(Qt.LeftButton) and event.modifiers() & Qt.ControlModifier:
                return QMouseEvent(event.type(),
                                   event.localPos(),
                                   event.windowPos(),
                                   event.screenPos(),
                                   event.button(),
                                   Qt.MouseButtons(int(event.buttons())|Qt.MiddleButton&~Qt.LeftButton),
                                   event.modifiers() & ~Qt.ControlModifier,
                                   event.source())
            elif event.modifiers() & Qt.ControlModifier:
                return QMouseEvent(event.type(),
                                   event.localPos(),
                                   event.windowPos(),
                                   event.screenPos(),
                                   Qt.MiddleButton,
                                   event.buttons(),
                                   event.modifiers() & ~Qt.ControlModifier,
                                   event.source())

        elif numMouseButtons == 2:
            if event.button() == Qt.LeftButton and event.modifiers() & Qt.ControlModifier:
                return QMouseEvent(event.type(),
                                   event.localPos(),
                                   event.windowPos(),
                                   event.screenPos(),
                                   Qt.MiddleButton,
                                   event.buttons(),
                                   event.modifiers() & ~Qt.ControlModifier,
                                   event.source())
            elif int(event.buttons()) & int(Qt.LeftButton) and event.modifiers() & Qt.ControlModifier:
                return QMouseEvent(event.type(),
                                   event.localPos(),
                                   event.windowPos(),
                                   event.screenPos(),
                                   event.button(),
                                   Qt.MouseButtons(int(event.buttons())|Qt.MiddleButton&~Qt.LeftButton),
                                   event.modifiers() & ~Qt.ControlModifier,
                                   event.source())
    return event

def createPixmap(imageName, width=0, height=0):
    rawPixmap = omui.MQtUtil.createPixmap(imageName)
    if rawPixmap is None:
        raise RuntimeError("Error: image not found: " + imageName)
    pixmap = wrapInstance(long(rawPixmap), QPixmap)
    if (width != 0 and height != 0):
        return pixmap.scaled(width, height)
    return pixmap


class ProgressBar(object):
  
    def __init__(self):
        super(ProgressBar, self).__init__()
        self.gMainProgressBar = mel.eval('$tmp = $gMainProgressBar')

    def stepProgressBar(self):
        if self.gMainProgressBar:
            cmds.progressBar(self.gMainProgressBar, edit=True, step=1)

    def createProgressBar(self, text, steps):
        from maya.app.renderSetup.model.renderLayerSwitchObservable import RenderLayerSwitchObservable

        if self.gMainProgressBar:
            cmds.progressBar(self.gMainProgressBar,
                                edit=True,
                                beginProgress=True,
                                isInterruptable=False,
                                status=text,
                                maxValue=steps)
            RenderLayerSwitchObservable.getInstance().addRenderLayerSwitchObserver(self.stepProgressBar)

    def endProgressBar(self):
        if self.gMainProgressBar:
            from maya.app.renderSetup.model.renderLayerSwitchObservable import RenderLayerSwitchObservable
            RenderLayerSwitchObservable.getInstance().removeRenderLayerSwitchObserver(self.stepProgressBar)
            cmds.progressBar(self.gMainProgressBar, edit=True, endProgress=True)

    def updateTextProgressBar(self, text):
        if self.gMainProgressBar:
            cmds.progressBar(self.gMainProgressBar, edit=True, status=text)

def setExpandedState(node, value):
    """ Sets an attribute on the node storing the expanded state of
    this node in the view. Creates it if it doesn't exist """

    # Get the plug associated with the expanded state attribute
    plugRef = commonUtils.findPlug(node, kExpandedStateString)
    if plugRef is None:
        # If it doesn't exist, we create it. It's a Plug object, Python side
        plugRef = plug.Plug.createAttribute(node, kExpandedStateString, 
            kExpandedStateString, {'type': 'Bool', 'connectable': False},
            plug.kNotUndoable)
        plugRef.value = value
    else:
        # If it already exists, we set its value. It's a MPlug object, OpenMaya side
        plugRef.setBool(value)

def getExpandedState(node):
    """ Retrieves the expanded state attribute of the node """

    plugRef = commonUtils.findPlug(node, kExpandedStateString)

    # If the attribte doesn't exist, just return False
    return plugRef.asBool() if plugRef is not None else False
  
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
