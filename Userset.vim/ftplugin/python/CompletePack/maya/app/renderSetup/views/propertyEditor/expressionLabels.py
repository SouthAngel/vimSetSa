import maya
maya.utils.loadStringResourcesForModule(__name__)

from PySide2.QtCore import Qt, Signal
from PySide2.QtWidgets import QLabel, QMenu

class IncludeExpressionLabel(QLabel):
    """
    This class represents an include expression label which has a right click menu used to create additional include expressions.
    """

    # Signals
    includeExpressionAdded = Signal()

    def __init__(self, text):
        super(IncludeExpressionLabel, self).__init__(text)
        self.addIncludeExpressionAction = None
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.customContextMenuRequested.connect(self.createStandardContextMenu)
     
    def createStandardContextMenu(self, position):
        """ Creates the right-click menu for creating additional include expressions. """
        menu = QMenu()
        self.addIncludeExpressionAction = menu.addAction(maya.stringTable['y_expressionLabels.kAddIncludeExpression' ])
        self.addIncludeExpressionAction.triggered.connect(self.addIncludeExpression)
        menu.exec_(self.mapToGlobal(position))

    def addIncludeExpression(self):
        self.includeExpressionAdded.emit()

class ExcludeExpressionLabel(QLabel):
    """
    This class represents an exclude expression label which has a right click menu used to create additional exclude expressions.
    """

    # Signals
    excludeExpressionAdded = Signal()

    def __init__(self, text):
        super(ExcludeExpressionLabel, self).__init__(text)
        self.addExcludeExpressionAction = None
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.createStandardContextMenu)
     
    def createStandardContextMenu(self, position):
        """ Creates the right-click menu for creating additional exclude expressions. """
        menu = QMenu()
        self.addExcludeExpressionAction = menu.addAction(maya.stringTable['y_expressionLabels.kAddExcludeExpression' ])
        self.addExcludeExpressionAction.triggered.connect(self.addExcludeExpression)
        menu.exec_(self.mapToGlobal(position))

    def addExcludeExpression(self):
        self.excludeExpressionAdded.emit()

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
