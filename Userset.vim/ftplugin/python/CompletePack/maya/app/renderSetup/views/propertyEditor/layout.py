from PySide2.QtCore import Qt
from PySide2.QtWidgets import QFormLayout, QLabel

import maya.app.renderSetup.views.utils as utils

class Layout(QFormLayout):
    """
    This class implements a special form layout for the property editor in which the label column is of a specific size.
    """

    # Constants
    LABEL_COLUMN_WIDTH = utils.dpiScale(48)

    def __init__(self):
        super(Layout, self).__init__()
        self.setContentsMargins(0, 4, 0, 0)
        
    def _createLabel(self, v1):
        """ Returns a label with a specific size and right alignment. """
        label = v1
        # If v1 is not a label, it should be a string
        if not isinstance(v1, QLabel):
            label = QLabel(v1)
        label.setMinimumSize(self.LABEL_COLUMN_WIDTH, 0)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return label

    def insertRow(self, row, v1, v2=None):
        """ Inserts a row into the layout. If v2 is None, then there is no label specified. """
        if v2 == None:
            super(Layout, self).insertRow(row, v1)
        else:
            label = self._createLabel(v1)
            super(Layout, self).insertRow(row, label, v2)
        
    def addRow(self, v1, v2=None):
        """ Adds a row to the layout. If v2 is None, then there is no label specified. """
        if v2 == None:
            super(Layout, self).addRow(v1)
        else:
            label = self._createLabel(v1)
            super(Layout, self).addRow(label, v2)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
