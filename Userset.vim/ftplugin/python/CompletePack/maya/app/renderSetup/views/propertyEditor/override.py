from maya.app.general.mayaMixin import MayaQWidgetBaseMixin

from PySide2.QtCore import Qt
from PySide2.QtWidgets import QGroupBox, QLabel, QVBoxLayout
from shiboken2 import getCppPointer

from maya.app.renderSetup.views.propertyEditor.layout import Layout
from maya.app.renderSetup.views.propertyEditor.overridePropertyEditorStrings import *

import maya.app.renderSetup.views.proxy.renderSetupRoles as renderSetupRoles
import maya.app.renderSetup.views.utils as utils

import maya.cmds as cmds

import weakref

from functools import partial

# For Maya UI name extraction
import maya.OpenMayaUI as mui

class Override(MayaQWidgetBaseMixin, QGroupBox):
    """
    This class represents the property editor view of an override.
    """
    
    def __init__(self, item, parent):
        super(Override, self).__init__(parent=parent)
        self.path = None
        self.attributeUI = None
        self.item = weakref.ref(item)

        layout = QVBoxLayout()
        layout.setObjectName('override_vertical_box_layout')
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(utils.dpiScale(2))
        self._setupMainOverrideGroupBox(layout)
        
        self.setLayout(layout)

        # Unwrap the layout into a pointer to be able to get the UI name.
        # We use fullName() to ensure a unique name is used
        layoutName = mui.MQtUtil.fullName(long(getCppPointer(layout)[0]))
        cmds.setParent(layoutName)
        
        self._uiLayout = cmds.columnLayout(adjustableColumn=True)

        self._dropBoxInit()

        if item.isUniqueOverride():
            self.target = QLabel(kAppliedToUnique % item.targetNodeName())
            self.target.setAlignment(Qt.AlignBottom | Qt.AlignCenter)
            layout.addWidget(self.target)

    def _createAttributeUI(self, attrName):
        self.attributeUI = self.item().createAttributeUI(attrName)

    def _dropCb(self, dragControl, dropControl, messages, x, y, dragType):
        # Create attribute UI.  We are expecting a node.plug string as the
        # first element of the messages list.
        if not messages or not isinstance(messages[0], basestring):
            return

        attr = messages[0]
        try:
            if not self.item().acceptsDrops(attr):
                cmds.warning(kIncompatibleAttribute % attr)
                return
        except (RuntimeError, TypeError):
            # RuntimeError occurs if 'attr' is not found.
            # TypeError occurs if 'attr' cannot be read as a plug.
            raise RuntimeError(kInvalidAttribute % attr)

        cmds.setParent(self._uiLayout)

        self._createAttributeUI(attr)

        isDropBoxVisible = self._isDropBoxVisible()

        cmds.iconTextStaticLabel(self._dropBox, edit=True,
                                 visible=isDropBoxVisible)

    def _isDropBoxVisible(self):
        return self.attributeUI is None

    def _dropBoxInit(self):
        self._createAttributeUI(None)

        self._dropBox = cmds.iconTextStaticLabel(
            style='iconAndTextVertical',
            i1='RS_drop_box.png',
            label=kDragAttributeFromAE,
            dropCallback=partial(Override._dropCb, self),
            visible=self._isDropBoxVisible())

    def _setupOverridePathName(self, mainGroupBoxLayout):
        self.path = QLabel(self.item().data(renderSetupRoles.NODE_PATH_NAME))
        mainGroupBoxLayout.addRow(kLayer, self.path)
        
    def _setupMainOverrideGroupBox(self, layout):
        mainGroupBox = QGroupBox()
        mainGroupBox.setContentsMargins(0, 0, 0, 0)
        mainGroupBoxLayout = Layout()
        mainGroupBoxLayout.setVerticalSpacing(utils.dpiScale(2))

        self._setupOverridePathName(mainGroupBoxLayout)

        mainGroupBox.setLayout(mainGroupBoxLayout)
        layout.addWidget(mainGroupBox)

    def paintEvent(self, event):
        if self.item():
            path = self.item().data(renderSetupRoles.NODE_PATH_NAME)
            if self.path.text() != path:
                self.path.setText(path)

        super(Override, self).paintEvent(event)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
