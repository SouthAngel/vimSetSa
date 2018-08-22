import maya
maya.utils.loadStringResourcesForModule(__name__)

from functools import partial
import weakref

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

import PySide2.QtCore as QtCore
from PySide2.QtCore import QPersistentModelIndex, QSize, Slot, QItemSelection, QTimer
from PySide2.QtGui import QStandardItem
from PySide2.QtWidgets import QScrollArea, QVBoxLayout, QWidget, QWidgetItem

import maya.cmds as cmds

from maya.app.renderSetup.views.frameLayout import FrameLayout
from maya.app.renderSetup.views.propertyEditor.override import Override
from maya.app.renderSetup.views.propertyEditor.renderLayer import RenderLayer
import maya.app.renderSetup.views.propertyEditor.collectionFactory as collectionFactory

import maya.app.renderSetup.views.proxy.renderSetup as renderSetup
import maya.app.renderSetup.views.proxy.renderSetupRoles as renderSetupRoles
import maya.app.renderSetup.views.utils as utils

import maya.app.renderSetup.model.renderSetup as renderSetupModel

class PropertyEditorScrollArea(QScrollArea):
    STARTING_SIZE = QSize(450, 600)

    def sizeHint(self):
        return utils.dpiScale(self.STARTING_SIZE)

class PropertyEditor(MayaQWidgetDockableMixin, QWidget):
    """
    This class represents the property editor which displays the selected render setup item's property information.


    Note: The Qt should never called any 'deferred' actions because all the design is based on synchronous notifications
          and any asynchronous events will change the order of execution of these events.
    
          For example when the selection in the Render Setup Window is changed (so the Property Editor must be updated). 
          The delete must be synchronous on the 'unselected' layouts otherwise they will be updated along with selected ones. 
          The two main side effects are that lot of unnecessary processings are triggered (those one the deleted layouts) 
          and the infamous 'C++ already deleted' issue appears because the Data Model & Qt Model objects were deleted 
          but not their corresponding Layout (instance used by the Property Editor to display a render setup object).    
    """

    width = cmds.optionVar(query='workspacesWidePanelInitialWidth')
    PREFERRED_SIZE = QSize(width, 600)
    MINIMUM_SIZE = QSize((width * 0.75), 0)

    def __init__(self, treeView, parent):
        super(PropertyEditor, self).__init__(parent=parent)
        self.needsRebuild = None
        self.itemsToRepopulate = None
        self.rebuildInProgress = None
        self.preferredSize = self.PREFERRED_SIZE
                
        self.treeView = weakref.ref(treeView)
        self.model = weakref.ref(treeView.model())

        self.setWindowTitle(maya.stringTable['y_main.kPropertyEditor' ])
        
        self.scrollArea = PropertyEditorScrollArea(self)
        self.scrollAreaLayout = QVBoxLayout(self)
        self.scrollArea.setLayout(self.scrollAreaLayout)
        self.scrollWidget = QWidget(self)
        self.scrollArea.setWidget(self.scrollWidget)         
        self.scrollArea.setWidgetResizable(True)
        self.scrollWidgetLayout = QVBoxLayout(self)
        self.scrollWidget.setLayout(self.scrollWidgetLayout)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.scrollArea, 0)
        self.setLayout(layout)

        self.frameLayouts = []
        
        self.setAcceptDrops(True)
        
        self._registered = False
        self._register()

        renderSetupModel.addObserver(self)

    def __del__(self):
        self._unregister()
        
    def _register(self):
        if not self._registered:
            self.model().itemChanged.connect(self.itemChanged)
            self.rebuildInProgress = False
            self.itemsToRepopulate = [] # List of items waiting to be repopulated
            self.needsRebuild = False

            selectionModel = self.treeView().selectionModel()
            selectionModel.selectionChanged.connect(self.selectionChanged)
            
            self._registered = True
        
    def _unregister(self):
        if self._registered:
            self.model().itemChanged.disconnect()
            self.rebuildInProgress = False
            self.itemsToRepopulate = [] # List of items waiting to be repopulated
            self.needsRebuild = False

            selectionModel = self.treeView().selectionModel()

            # The following more obvious implementation:
            #
            # selectionModel.selectionChanged.disconnect(self.selectionChanged)
            #
            # raises
            #
            # // Error: line 0: RuntimeError: file renderSetup\views\propertyEditor\main.py line 103: Failed to disconnect signal selectionChanged(QItemSelection,QItemSelection). //
            #
            # which comes from PySide2's CPython implementation, in file
            # pysidesignal.cpp, function signalInstanceDisconnect().  The
            # argument slot is not recognized, and the function fails.
            # Use old-style disconnection as a workaround.

            selectionModel.disconnect(
                QtCore.SIGNAL(
                    'selectionChanged(QItemSelection,QItemSelection)'),
                self, QtCore.SLOT(
                    'selectionChanged(QItemSelection,QItemSelection)'))
            
            self._registered = False

    def setSizeHint(self, size):
        self.preferredSize = size

    def sizeHint(self):
        return self.preferredSize

    def minimumSizeHint(self):
        return self.MINIMUM_SIZE

    def aboutToDelete(self):
        """Cleanup method to be called immediately before the object is deleted."""
        self._unregister()
        self._clearWidgets()
        # Qt object can take a long time before actually being destroyed
        # => observation of renderSetupModel may remain active (since self is not dead)
        # => explicitly remove observer to avoid receiving unwanted calls
        renderSetupModel.removeObserver(self)

    # Obsolete interface.
    dispose = aboutToDelete

    def renderSetupAdded(self):
        """ RenderSetup node was created """
        self._register()

    def renderSetupPreDelete(self):
        """ RenderSetup node is about to be deleted """
        # Flush the current content to avoid intermediate refreshes
        self._unregister()
        self._clearWidgets()

    def _clearWidgets(self):
        """ Clears the property editor widgets """
        while self.scrollWidgetLayout.count() > 0:
            layoutItem = self.scrollWidgetLayout.takeAt(0)
            # Note: Not obvious but to enforce the layoutItem delete, the parent should be None. 
            #  I would have expected that the takeAt() call did it by default 
            #  as the layoutItem is not anymore in the layout.
            if isinstance(layoutItem, QWidgetItem):
                layoutItem.widget().setParent(None)
            del layoutItem

        self.frameLayouts = []

    def _addItemEditor(self, propertyEditorItem):
        """
        Adds a property editor item type to the end of the layout, also
        keeps track of the control and frameLayout in case there is a data
        change.
        """
        frameLayout = FrameLayout(propertyEditorItem.item(), self)
        self.scrollWidgetLayout.addWidget(frameLayout)
        frameLayout.addWidget(propertyEditorItem)
        self.frameLayouts.append(frameLayout)
        return propertyEditorItem
        
    def _addLayer(self, currentItem):
        """ Adds a property editor layer to the end of the layout. """
        self._addItemEditor(RenderLayer(currentItem, self))

    def _addCollection(self, currentItem):
        """ Adds a property editor collection to the end of the layout. """
        collection = self._addItemEditor(
            collectionFactory.create(currentItem, self))

    def _addOverride(self, currentItem):
        """ Adds a property editor override to the end of the layout. """
        override = self._addItemEditor(Override(currentItem, self))

    @Slot(QStandardItem)
    def itemChanged(self, item):
        """
        When an item in the model changes, update the control and 
        frameLayout that make use of that item (if one exists).
        """
        if not item.isModelDirty():
            # itemChanged was not triggered due to a change to the model.
            # Nothing to do.
            # This is a workaround (see views/proxy/renderSetup.py (modelChanged() callback))
            return
        if item.data(renderSetupRoles.NODE_REBUILD_UI_WHEN_CHANGED):
            self.triggerRebuild()
        else:
            self.triggerRepopulate(item)

    def _getSortedSelectedIndexes(self):
        """ Unfortunately the selected items that are given to us from Qt are not sorted, we need to do this ourselves. """
        selectionModel = self.treeView().selectionModel()
        selectedIndexes = selectionModel.selectedIndexes()
        rootIndex = self.treeView().rootIndex()
        indexStack = []
        indexStack.append(rootIndex)

        # Pre-order traversal of our tree in order to get the preOrderIndex for each item in the tree.
        # Then a sort is applied by preOrderIndex on the selected items to get the sorted selected indexes.
        count = 0
        while(len(indexStack) > 0):
            index = indexStack.pop()
            if index != self.treeView().rootIndex():
                item = self.model().itemFromIndex(index)
                item.preOrderIndex = count
                count = count + 1
            if index is not None and (index.isValid() or index == self.treeView().rootIndex()):
                numRows = self.model().rowCount(index)
                for i in range(numRows):
                    indexStack.append(self.model().index(numRows - i - 1, 0, index))

        sortedSelectedIndices = []
        for i in range(len(selectedIndexes)):
            item = self.model().itemFromIndex(selectedIndexes[i])
            sortedSelectedIndices.append((selectedIndexes[i], item.preOrderIndex))
        sortedSelectedIndices = sorted(sortedSelectedIndices, key=lambda element: element[1]) # Sort by preOrderIndex
        return sortedSelectedIndices

    @Slot(QItemSelection, QItemSelection)
    def selectionChanged(self, selected, deselected):
        """
        On selection changed we lazily regenerate our collection/override/layer 
        controls.
        """
        self.triggerRebuild()

    def triggerRebuild(self):
        self.needsRebuild = True
        if len(self.itemsToRepopulate) == 0 and not self.rebuildInProgress:
            self.rebuildInProgress = True
            QTimer.singleShot(0, lambda: self.rebuild())

    def rebuild(self):
        """ regenerate our collection/override/layer controls. """
        if not self.needsRebuild:
            # early out if we no longer need to rebuild
            # this can happen because rebuild is asynchronous
            return
        self.scrollArea.setVisible(False)
        self._clearWidgets()
        indexes = self._getSortedSelectedIndexes()
        
        creators = {    renderSetup.RENDER_LAYER_TYPE            : self._addLayer,
                        renderSetup.COLLECTION_TYPE              : self._addCollection,
                        renderSetup.RENDER_SETTINGS_TYPE         : self._addCollection,
                        renderSetup.LIGHTS_TYPE                  : self._addCollection,
                        renderSetup.AOVS_TYPE                    : self._addCollection,
                        renderSetup.AOVS_CHILD_COLLECTION_TYPE   : self._addCollection,
                        renderSetup.LIGHTS_CHILD_COLLECTION_TYPE : self._addCollection,
                        renderSetup.RENDER_OVERRIDE_TYPE         : self._addOverride }
        
        for i in range(0, len(indexes)):
            currentIndex = QPersistentModelIndex(indexes[i][0])
            currentItem = self.model().itemFromIndex(currentIndex)
            creators[currentItem.type()](currentItem)

        self.scrollWidgetLayout.addStretch(1)
        self.rebuildInProgress = False
        self.needsRebuild = False
        self.itemsToRepopulate = []
        self.scrollArea.setVisible(True)

    def triggerRepopulate(self, item):
        if not self.rebuildInProgress and not item in self.itemsToRepopulate:
            self.itemsToRepopulate.append(item)
            QTimer.singleShot(0, partial(self.populateFields, item=item))

    def populateFields(self, item):
        # If we need a rebuild while a populateFields request is made, the rebuild is the priority, so rebuild and return.
        if self.needsRebuild:
            return self.rebuild()
        # If another populateFields caused a rebuild then the item will no longer be in the list so return there is no work to do.
        elif not item in self.itemsToRepopulate:
            return

        PropertyEditor.updaters = \
            { renderSetup.RENDER_LAYER_TYPE            : self._updateItem,
              renderSetup.COLLECTION_TYPE              : self._updateCollection,
              renderSetup.RENDER_SETTINGS_TYPE         : self._updateItem,
              renderSetup.LIGHTS_TYPE                  : self._updateItem,
              renderSetup.AOVS_TYPE                    : self._updateItem,
              renderSetup.AOVS_CHILD_COLLECTION_TYPE   : self._updateItem,
              renderSetup.LIGHTS_CHILD_COLLECTION_TYPE : self._updateItem,
              renderSetup.RENDER_OVERRIDE_TYPE         : self._updateItem }
        
        PropertyEditor.updaters[item.type()](item)
        self.itemsToRepopulate.remove(item)

    def _updateItem(self, item):
        for frameLayout in self.frameLayouts:
            if frameLayout.item() is item:
                frameLayout.update()

    def _updateCollection(self, item):
        for frameLayout in self.frameLayouts:
            if frameLayout.item() is item:
                frameLayout.getWidget(0).populateFields()
        self._updateItem(item)
        
    def highlight(self, names):
        if not isinstance(names, set):
            names = set(names)
        def doHighlight():
            collections = (frameLayout.getWidget(0) for frameLayout in self.frameLayouts \
                if frameLayout.item().type() == renderSetup.COLLECTION_TYPE)
            for col in collections:
                col.highlight(names)
        # triggerRepopulate is delayed => highlight must also be delayed to apply only
        # when repopulate is complete
        QTimer.singleShot(0, doHighlight)
        
            
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
