import maya
maya.utils.loadStringResourcesForModule(__name__)

from maya.app.general.mayaMixin import MayaQWidgetBaseMixin

from PySide2.QtWidgets import QGroupBox, QLabel, QVBoxLayout
from shiboken2 import getCppPointer

import maya.app.renderSetup.views.propertyEditor.layout as propEdLayout

import maya.app.renderSetup.views.proxy.renderSetupRoles as renderSetupRoles
import maya.app.renderSetup.views.utils as utils

# For Maya UI name extraction
import maya.OpenMayaUI as mui


class BasicCollection(MayaQWidgetBaseMixin, QGroupBox):
    """
    Empty collection property editor UI.

    This class provides a very simple property editor UI for a collection.
    It displays the "path" to the collection within the render setup data
    model tree.  It can be used as a base class for more complex collection
    property editor UIs.
    """
    
    def __init__(self, item, parent):
        super(BasicCollection, self).__init__(parent=parent)
        # item is a weakref.
        self.item = item
        self.path = None

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(utils.dpiScale(2))
        layout.setObjectName('collection_vertical_box_layout')
        
        self._setupMainCollectionGroupBox(layout)
        self.setLayout(layout)
        # Unwrap the layout into a pointer to be able to get the UI name.
        # We use fullName() to ensure a unique name is used
        self._layoutName = mui.MQtUtil.fullName(
            long(getCppPointer(self.layout())[0]))

        self.preSelector()
        self.setupSelector(layout)

    def preSelector(self):
        # Nothing to show before the selector UI.
        pass

    def setupSelector(self, layout):
        # Basic collection has no selector layout.
        pass

    def _setupCollectionPathName(self, mainGroupBoxLayout):
        self.path = QLabel(self.item().data(renderSetupRoles.NODE_PATH_NAME))
        mainGroupBoxLayout.addRow(maya.stringTable['y_basicCollection.kLayer' ], self.path)
        
    def _setupMainCollectionGroupBox(self, layout):
        mainGroupBox = QGroupBox()
        mainGroupBox.setContentsMargins(0, 0, 0, 0)
        mainGroupBoxLayout = propEdLayout.Layout()
        mainGroupBoxLayout.setVerticalSpacing(utils.dpiScale(2))

        self._setupCollectionPathName(mainGroupBoxLayout)

        mainGroupBox.setLayout(mainGroupBoxLayout)
        layout.addWidget(mainGroupBox)

    def paintEvent(self, event):
        if self.item():
            path = self.item().data(renderSetupRoles.NODE_PATH_NAME)
            if self.path.text() != path:
                self.path.setText(path)

        super(BasicCollection, self).paintEvent(event)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
