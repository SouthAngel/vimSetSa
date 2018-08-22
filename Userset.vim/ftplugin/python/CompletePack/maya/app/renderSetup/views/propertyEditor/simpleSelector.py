import maya
maya.utils.loadStringResourcesForModule(__name__)

from PySide2.QtCore import Qt
from PySide2.QtGui import QFont, QIcon
from PySide2.QtWidgets import QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLineEdit, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from maya.app.renderSetup.views.propertyEditor.expressionLabels import IncludeExpressionLabel
from maya.app.renderSetup.views.propertyEditor.layout import Layout
from maya.app.renderSetup.views.propertyEditor.collectionStaticSelectionWidget import CollectionStaticSelectionWidget
from maya.app.renderSetup.views.propertyEditor.collectionFilterLineEdit import CollectionFilterLineEdit
from maya.app.renderSetup.views.renderSetupDelegate import RenderSetupDelegate

import maya.app.renderSetup.views.utils as utils

import maya.app.renderSetup.model.selector as selector

import maya.cmds as cmds
import maya.app.renderSetup.common.guard as guard
from maya.app.renderSetup.common.devtools import abstractmethod

def ifNotBlockChangeMessages(f):
    """Avoid calling the decorated function if change messages are blocked."""

    # See undo module for decorator comments.
    def wrapper(*args, **kwargs):
        # args[0] is the object, self in the method member definition. 
        if not args[0]._blockChangeMessages:
            f(*args, **kwargs)
    return wrapper

class SimpleSelector(object):
    
    # Constants
    LIST_BOX_HEIGHT = utils.dpiScale(100)
    EXPRESSION_BUTTON_WIDTH = utils.dpiScale(50)
    INVERSE_STRING = maya.stringTable['y_simpleSelector.kInverse' ]
    SELECT_STRING = maya.stringTable['y_simpleSelector.kSelect' ]
    CREATE_EXPRESSION_STRING = maya.stringTable['y_simpleSelector.kCreateExpression' ]
    DRAG_DROP_FILTER_STRING = maya.stringTable['y_simpleSelector.kDragDropFilter' ]
    
    # Corresponding data model type.
    kModelType = selector.SimpleSelector.kTypeName

    def __init__(self, selector):
        self.expression = ""
        self._blockChangeMessages = False
        self._selector = selector
        self.filterType = None
        self.addToCollectionGroupBoxLayout = None
        self.includeExpressionWidgets = None
        self.includeExpression = None
        self.customFilterEdit = None
        self.filtersGroupBoxLayout = None
        self.staticSelector = None

    def build(self, layout, populate=True):
        self._setupFilterGroupBox(layout)
        self._setupAddToCollectionGroupBox(layout)
        if populate:
            self.populateFields()

    def displayType(self):
        """Return the user-visible display type string.

        By default this is the same for all objects of a selector class."""
        return self.kDisplayType

    def _setupExpression(self, expressionLabel, expressionChangedCB, expressionFinishedCB):
        expressionWidget = QWidget()
        expressionLayout = QHBoxLayout()
        expressionLayout.setContentsMargins(0, 0, 0, 0)
        expressionLayout.setSpacing(utils.dpiScale(2))
        expressionWidget.setLayout(expressionLayout)
        expression = QLineEdit()
        tip =  maya.stringTable['y_simpleSelector.kExpressionTooltipStr'  ]
        tip += maya.stringTable['y_simpleSelector.kExpressionTooltipStr1' ]
        tip += maya.stringTable['y_simpleSelector.kExpressionTooltipStr2' ]
        tip += maya.stringTable['y_simpleSelector.kExpressionTooltipStr3' ]
        tip += maya.stringTable['y_simpleSelector.kExpressionTooltipStr4' ]
        tip += maya.stringTable['y_simpleSelector.kExpressionTooltipStr5' ]
        tip += maya.stringTable['y_simpleSelector.kExpressionTooltipStr6' ]
        tip += maya.stringTable['y_simpleSelector.kExpressionTooltipStr7' ]
        tip += maya.stringTable['y_simpleSelector.kExpressionTooltipStr8' ]
        tip += maya.stringTable['y_simpleSelector.kExpressionTooltipStr9' ]
        tip += maya.stringTable['y_simpleSelector.kExpressionTooltipStr10' ]
        tip += maya.stringTable['y_simpleSelector.kExpressionTooltipStr11' ]
        tip += maya.stringTable['y_simpleSelector.kExpressionTooltipStr12' ]
        tip += maya.stringTable['y_simpleSelector.kExpressionTooltipStr13' ]
        tip += maya.stringTable['y_simpleSelector.kExpressionTooltipStr14' ]
        expression.setToolTip(tip)

        expression.textChanged.connect(expressionChangedCB)

        # editingFinished is triggered for both enter key pressed and focused lost.
        expression.editingFinished.connect(expressionFinishedCB)
        expression.returnPressed.connect(lambda: expression.clearFocus())

        expression.setPlaceholderText(self.CREATE_EXPRESSION_STRING)
        expressionLayout.addWidget(expression)

        selectButton = QPushButton(self.SELECT_STRING)
        selectButton.setToolTip(maya.stringTable['y_simpleSelector.kExpressionSelectTooltipStr' ])
        selectButton.setMinimumWidth(self.EXPRESSION_BUTTON_WIDTH)
        selectButton.clicked.connect(self.selectIncludeExpression)
        expressionLayout.addWidget(selectButton)

        self.addToCollectionGroupBoxLayout.addRow(expressionLabel, expressionWidget)
        return expressionWidget, expression
        
    def _setupIncludeExpression(self):
        includeExpressionLabel = IncludeExpressionLabel(maya.stringTable['y_simpleSelector.kInclude' ])
        includeExpressionWidget, self.includeExpression = \
            self._setupExpression(includeExpressionLabel, self.includeExpressionChanged, self.includeExpressionEntered)
        self.includeExpressionWidgets = [includeExpressionWidget]
        self.expression = self._selector.getPattern()

    @abstractmethod
    def _getFilterEnum(self):
        pass

    def _setupFilterUI(self, layout):
        filterUIWidget = QWidget()
        filterUILayout = QHBoxLayout()
        filterUILayout.setContentsMargins(0, 0, 0, 0)
        filterUILayout.setSpacing(utils.dpiScale(2))
        filterUIWidget.setLayout(filterUILayout)

        #setup and add the filter combo box.
        self.filterType = QComboBox()
        self.filterType.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(10)  # stronger than the spacer added below
        self.filterType.setSizePolicy(sizePolicy)
        self.filterType.setMinimumContentsLength(0)
        self.filterType.setMaximumWidth(200)
        self.filterType.setToolTip(maya.stringTable['y_simpleSelector.kFiltersToolTip' ])
        
        for ftype in self._selector.getAvailableFilters():
            self.filterType.addItem(QIcon(RenderSetupDelegate.getFilterIcon(ftype)), 
                                    selector.Filters.filterUIName(ftype), ftype)

        # get the current filter value and set the index of the combo box appropriately.
        filter = self._selector.getFilterType()
        self.filterType.currentIndexChanged[str].connect(self._filterTypeChanged)
        filterUILayout.addWidget(self.filterType)

        filterUILayout.addStretch()
        filterUILayout.addSpacing(4)

        self.customFilterEdit = CollectionFilterLineEdit()
        self.customFilterEdit.returnPressed.connect(lambda: self.customFilterEdit.clearFocus())
        self.customFilterEdit.setPlaceholderText(self.DRAG_DROP_FILTER_STRING)
        self.customFilterEdit.editingFinished.connect(self.customFilterEntered)
        showCustomFilter = (filter == selector.Filters.kCustom)

        layout.addRow("", filterUIWidget)
        layout.addRow(maya.stringTable['y_simpleSelector.kByTypeFilter' ], self.customFilterEdit)       
            
    @ifNotBlockChangeMessages
    def _filterTypeChanged(self, value):
        filterNameMap = { selector.Filters.filterUIName(ftype):ftype for ftype in self._selector.getAvailableFilters() }
        self._selector.setFilterType(filterNameMap[value])


    def _setupStaticSelector(self):
        staticSelectionWidget = QWidget()
        staticSelectionLayout = QHBoxLayout()
        staticSelectionLayout.setContentsMargins(0, 0, 0, 0)
        staticSelectionLayout.setSpacing(utils.dpiScale(2))
        self.staticSelector = CollectionStaticSelectionWidget(self._selector)
        self.staticSelector.setFixedHeight(self.LIST_BOX_HEIGHT)
        staticSelectionLayout.addWidget(self.staticSelector)
        
        # Add the drag/drop buttons
        dragDropButtonLayout = QVBoxLayout()
        dragDropButtonLayout.setSpacing(utils.dpiScale(2))
        dragDropButtonLayout.setContentsMargins(0, 0, 0, 0)
        addButton = QPushButton(maya.stringTable['y_simpleSelector.kAdd' ])
        addButton.setToolTip(maya.stringTable['y_simpleSelector.kStaticAddTooltipStr' ])
        addButton.setMinimumWidth(self.EXPRESSION_BUTTON_WIDTH)
        addButton.clicked.connect(self.staticSelector.addEntry)
        dragDropButtonLayout.addWidget(addButton)
        removeButton = QPushButton(maya.stringTable['y_simpleSelector.kRemove' ])
        removeButton.setToolTip(maya.stringTable['y_simpleSelector.kStaticRemoveTooltipStr' ])
        removeButton.setMinimumWidth(self.EXPRESSION_BUTTON_WIDTH)
        removeButton.clicked.connect(self.staticSelector.removeEntry)
        dragDropButtonLayout.addWidget(removeButton)
        dragDropButtonLayout.addStretch(1)
        selectButton = QPushButton(self.SELECT_STRING)
        selectButton.setToolTip(maya.stringTable['y_simpleSelector.kStaticSelectTooltipStr' ])
        selectButton.setMinimumWidth(self.EXPRESSION_BUTTON_WIDTH)
        selectButton.clicked.connect(self.selectStaticEntries)
        dragDropButtonLayout.addWidget(selectButton)
        dragDropButtonWidget = QWidget()
        staticSelectionLayout.addWidget(dragDropButtonWidget)
        dragDropButtonWidget.setLayout(dragDropButtonLayout)
        staticSelectionWidget.setLayout(staticSelectionLayout)
        self.addToCollectionGroupBoxLayout.addRow("", staticSelectionWidget)

    def _setupSelectAllButton(self):
        selectAllButtonWidget = QWidget()
        selectAllButtonLayout = QHBoxLayout()
        selectAllButtonLayout.setContentsMargins(0, 0, 0, 0)
        selectAllButtonLayout.setSpacing(utils.dpiScale(2))
        selectAllButton = QPushButton(maya.stringTable['y_simpleSelector.kSelectAll' ])
        selectAllButtonLayout.addStretch(1)
        selectAllButtonLayout.addWidget(selectAllButton)
        selectAllButtonLayout.addStretch(1)
        selectAllButtonLayout.addSpacing(self.EXPRESSION_BUTTON_WIDTH)
        selectAllButtonWidget.setLayout(selectAllButtonLayout)
        self.addToCollectionGroupBoxLayout.addRow("", selectAllButtonWidget)

    def _setupFilterGroupBox(self, layout):
        filterGroupBox = QGroupBox(maya.stringTable['y_simpleSelector.kCollectionFilters' ])
        font = QFont()
        font.setBold(True)
        filterGroupBox.setFont(font)
        filterGroupBox.setContentsMargins(0, utils.dpiScale(12), 0, 0)
        self.filtersGroupBoxLayout = Layout()
        self.filtersGroupBoxLayout.setVerticalSpacing(utils.dpiScale(2))

        self._setupFilterUI(self.filtersGroupBoxLayout)

        filterGroupBox.setLayout(self.filtersGroupBoxLayout)
        layout.addWidget(filterGroupBox)

    def _setupAddToCollectionGroupBox(self, layout):
        addToCollectionGroupBox = QGroupBox(maya.stringTable['y_simpleSelector.kAddToCollection' ])
        font = QFont()
        font.setBold(True)
        addToCollectionGroupBox.setFont(font)
        addToCollectionGroupBox.setContentsMargins(0, utils.dpiScale(12), 0, 0)
        self.addToCollectionGroupBoxLayout = Layout()
        self.addToCollectionGroupBoxLayout.setVerticalSpacing(utils.dpiScale(2))

        self._setupIncludeExpression()
        self._setupStaticSelector()

        addToCollectionGroupBox.setLayout(self.addToCollectionGroupBoxLayout)
        layout.addWidget(addToCollectionGroupBox)
    
    def includeExpressionChanged(self, text):
        self.expression = text
    
    @ifNotBlockChangeMessages
    def includeExpressionEntered(self):
        self._selector.setPattern(self.expression)

    @ifNotBlockChangeMessages
    def customFilterEntered(self):
        customFilterText = self.customFilterEdit.text()
        self._selector.setCustomFilterValue(customFilterText)

    @guard.member('_blockChangeMessages', True)
    def populateFields(self):
        filter = self._selector.getFilterType()
        filterIndex = self.filterType.findData(filter)
        self.filterType.setCurrentIndex(filterIndex)

        showCustomFilter = (filter == selector.Filters.kCustom)
        customFilterText = self._selector.getCustomFilterValue()
        self.customFilterEdit.setText(customFilterText)
        self.customFilterEdit.setVisible(showCustomFilter)
        self.filtersGroupBoxLayout.labelForField(self.customFilterEdit).setVisible(showCustomFilter)

        expressionText = self._selector.getPattern()
        self.includeExpression.setText(expressionText)

        self.staticSelector.populate()

    def selectIncludeExpression(self):
        cmds.select(list(self._selector.getDynamicNames()), add=False, noExpand=True)
      
    def selectStaticEntries(self):
        self.staticSelector.selectMembers()
        cmds.select(list(self._selector.getStaticNames()), add=False, noExpand=True)
        
    def highlight(self, names):
        dynamicNames = self._selector.getDynamicNames()
        if next((name for name in names if name in dynamicNames), None) is not None:
            self.includeExpression.setSelection(0,len(self.includeExpression.text()))
        staticNames = self._selector.getStaticNames()
        self.staticSelector.highlight(set(name for name in names if name in staticNames))

class BasicSelector(SimpleSelector):

    # User-visible usage message.  Can be used as tool tip.
    kUsage = maya.stringTable['y_simpleSelector.kBasicSelectorUsage' ]

    # User-visible display type.
    kDisplayType = maya.stringTable['y_simpleSelector.kBasicSelectorDisplayType' ]

    # Corresponding data model type.
    kModelType = selector.BasicSelector.kTypeName

    def __init__(self, selector):
        super(BasicSelector, self).__init__(selector)
        self.includeHierarchy = None
        
    def build(self, layout):
        super(BasicSelector, self).build(layout, populate=False)
        self._setupIncludeHierarchy(self.addToCollectionGroupBoxLayout)
        self.populateFields()
        
    def _setupIncludeHierarchy(self, layout):
        self.includeHierarchy = QCheckBox(maya.stringTable['y_simpleSelector.kIncludeHierarchy' ])
        self.includeHierarchy.setToolTip(maya.stringTable['y_simpleSelector.kIncludeHierarchyTooltipStr' ])
        self.includeHierarchy.stateChanged.connect(lambda x: self.setIncludeHierarchy(x == Qt.Checked))
        layout.addWidget(self.includeHierarchy)
        
    @ifNotBlockChangeMessages
    def setIncludeHierarchy(self, value):
        self._selector.setIncludeHierarchy(value)
    
    @guard.member('_blockChangeMessages', True)    
    def populateFields(self):
        super(BasicSelector, self).populateFields()
        self.includeHierarchy.setCheckState(Qt.Checked if self._selector.getIncludeHierarchy() else Qt.Unchecked)
    
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
