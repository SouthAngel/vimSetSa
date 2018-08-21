import maya
maya.utils.loadStringResourcesForModule(__name__)

from PySide2.QtGui import QFont
from PySide2.QtWidgets import QGroupBox, QHBoxLayout, QListWidget, QVBoxLayout, QWidget

import maya.app.renderSetup.views.propertyEditor.layout as propEdLayout
import maya.app.renderSetup.views.propertyEditor.basicCollection as basicCollection

import maya.app.renderSetup.views.utils as utils


class StaticCollection(basicCollection.BasicCollection):
    """
        This class represents the property editor view of a static collection.
        A static selection is read-only and only contains a list of selected nodes.
    """
    
    # Constants
    LIST_BOX_HEIGHT = utils.dpiScale(100)

    def __init__(self, item, parent):
        super(StaticCollection, self).__init__(item, parent)
        self.addToCollectionGroupBoxLayout = None
        self.staticSelector = None

    def setupSelector(self, layout):
        self._setupAddToCollectionGroupBox(layout)

    def _setupStaticSelector(self):
        staticSelectionWidget = QWidget()
        staticSelectionLayout = QHBoxLayout()
        staticSelectionLayout.setContentsMargins(0, 0, 0, 0)
        staticSelectionLayout.setSpacing(utils.dpiScale(2))
        self.staticSelector = QListWidget()
        self.staticSelector.setFixedHeight(self.LIST_BOX_HEIGHT)
        staticSelectionLayout.addWidget(self.staticSelector)
        
        # Re-populate the static selection list view with the previously stored value
        staticSelections = self.item().model.getSelector().getStaticSelection()
        staticSelectionList = staticSelections.split() if staticSelections is not None else list()
        self.staticSelector.addItems(staticSelectionList)
        
        # Add the drag/drop buttons
        dragDropButtonLayout = QVBoxLayout()
        dragDropButtonLayout.setSpacing(utils.dpiScale(2))
        dragDropButtonLayout.setContentsMargins(0, 0, 0, 0)
        dragDropButtonWidget = QWidget()
        staticSelectionLayout.addWidget(dragDropButtonWidget)
        dragDropButtonWidget.setLayout(dragDropButtonLayout)
        staticSelectionWidget.setLayout(staticSelectionLayout)
        self.addToCollectionGroupBoxLayout.addRow("", staticSelectionWidget)

    def _setupAddToCollectionGroupBox(self, layout):
        addToCollectionGroupBox = QGroupBox(maya.stringTable['y_staticCollection.kAddToCollection' ])
        font = QFont()
        font.setBold(True)
        addToCollectionGroupBox.setFont(font)
        addToCollectionGroupBox.setContentsMargins(0, utils.dpiScale(12), 0, 0)
        self.addToCollectionGroupBoxLayout = propEdLayout.Layout()
        self.addToCollectionGroupBoxLayout.setVerticalSpacing(utils.dpiScale(2))

        self._setupStaticSelector()

        addToCollectionGroupBox.setLayout(self.addToCollectionGroupBoxLayout)
        layout.addWidget(addToCollectionGroupBox)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
