"""
Currently the RenderSetupView is repopulated on new file creation, but the 
SceneView is only populated once.
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)

   
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

import maya.OpenMaya as OpenMaya
import maya.mel

from functools import partial
import json
import os

import maya.cmds as cmds

from PySide2.QtCore import QEvent, QMimeData, QModelIndex, QObject, QPersistentModelIndex, QSize, Qt, QPoint, QItemSelectionModel, QThread, Signal, Slot
from PySide2.QtGui import QCursor, QDrag, QIcon, QPen, QColor, QPainter, QKeySequence
from PySide2.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QVBoxLayout, QBoxLayout, QMenu, QMenuBar, QSizePolicy, QToolTip
from PySide2.QtWidgets import QWidget, QLayoutItem, QAbstractItemView, QTreeView 

from maya.app.renderSetup.views.renderSetupButton import RenderSetupButton
from maya.app.renderSetup.views.renderSetupDelegate import RenderSetupDelegate
from maya.app.renderSetup.views.renderSetupStyle import RenderSetupStyle
from maya.app.renderSetup.views.sceneDelegate import SceneDelegate
import maya.app.renderSetup.views.utils as utils
import maya.app.renderSetup.views.importExportUI as importExportUI

import maya.app.renderSetup.views.pySide.action as action
import maya.app.renderSetup.views.pySide.menu as menu
import maya.app.renderSetup.views.pySide.cursors as cursors

import maya.app.renderSetup.views.proxy.renderSetup as renderSetup
import maya.app.renderSetup.views.proxy.renderSetupRoles as renderSetupRoles
import maya.app.renderSetup.views.proxy.scene as scene
import maya.app.renderSetup.views.renderSetupPreferences as prefs

import maya.app.renderSetup.model.override as overrideModel
import maya.app.renderSetup.model.connectionOverride as connectionOverrideModel
import maya.app.renderSetup.model.undo as undo
import maya.app.renderSetup.model.renderSetup as renderSetupModel
import maya.app.renderSetup.model.jsonTranslatorUtils as jsonTranslatorUtils
import maya.app.renderSetup.model.renderSetupPreferences as userPrefs
import maya.app.renderSetup.model.collection as collectionModel
import maya.app.renderSetup.model.rendererCallbacks as rendererCallbacks
import maya.app.renderSetup.model.renderSettings as renderSettings
import maya.app.renderSetup.model.aovs as aovs
import maya.app.renderSetup.model.utils as modelUtils

import maya.app.renderSetup.common.errorAndWarningDeferrer as errorAndWarningDeferrer

# Localized texts
kFile                 = maya.stringTable['y_renderSetupWindow.kFile'                 ]
kRenderSetup          = maya.stringTable['y_renderSetupWindow.kRenderSetup'          ]
kExportAll            = maya.stringTable['y_renderSetupWindow.kExportAll'            ]
kExportSelected       = maya.stringTable['y_renderSetupWindow.kExportSelected'       ]
kImportAll            = maya.stringTable['y_renderSetupWindow.kImportAll'            ]
kExportRenderSettings = maya.stringTable['y_renderSetupWindow.kExportRenderSettings' ]
kImportRenderSettings = maya.stringTable['y_renderSetupWindow.kImportRenderSettings' ]
kExportAOVs           = maya.stringTable['y_renderSetupWindow.kExportAOVs'           ]
kImportAOVs           = maya.stringTable['y_renderSetupWindow.kImportAOVs'           ]
kHelp                 = maya.stringTable['y_renderSetupWindow.kHelp'                 ]
kMayaHelp             = maya.stringTable['y_renderSetupWindow.kMayaHelp'             ]
# The following string is added in case "Render Setup" should be shipped to Maya LT
kMayaLTHelp		      = maya.stringTable['y_renderSetupWindow.kMayaLTHelp'	         ]
kRenderSetupHelp      = maya.stringTable['y_renderSetupWindow.kRenderSetupHelp'      ]
kOptions              = maya.stringTable['y_renderSetupWindow.kOptions'              ]
kAutoUpdate           = maya.stringTable['y_renderSetupWindow.kAutoUpdate'           ]
kEdit                 = maya.stringTable['y_renderSetupWindow.kEdit'                 ]
kCut                  = maya.stringTable['y_renderSetupWindow.kCut'                  ]
kCopy                 = maya.stringTable['y_renderSetupWindow.kCopy'                 ]
kPaste                = maya.stringTable['y_renderSetupWindow.kPaste'                ]
kCutShortcut          = maya.stringTable['y_renderSetupWindow.kCutShortcut'          ]
kCopyShortcut         = maya.stringTable['y_renderSetupWindow.kCopyShortcut'         ]
kPasteShortcut        = maya.stringTable['y_renderSetupWindow.kPasteShortcut'        ]

kExportAllTitle         = maya.stringTable['y_renderSetupWindow.kExportAllTitle'        ]
kExportSelectedTitle    = maya.stringTable['y_renderSetupWindow.kExportSelectedTitle'   ]
kImportAllTitle         = maya.stringTable['y_renderSetupWindow.kImportAllTitle'        ]
kImportWrongFile        = maya.stringTable['y_renderSetupWindow.kImportWrongFile'       ]
kImportWrongFileWasTemplate = maya.stringTable['y_renderSetupWindow.kImportWrongFileWasTemplate' ]
kExportSelectionError   = maya.stringTable['y_renderSetupWindow.kExportSelectionError'  ]
kImportWrongContent     = maya.stringTable['y_renderSetupWindow.kImportWrongContent'    ]
kExportAVOsNoHandler    = maya.stringTable['y_renderSetupWindow.kExportAVOsNoHandler'   ]
kImportAVOsNoHandler    = maya.stringTable['y_renderSetupWindow.kImportAVOsNoHandler'   ]

kAvailableGlobalTemplates = maya.stringTable['y_renderSetupWindow.kAvailableGlobalTemplates'  ]
kAvailableUserTemplates   = maya.stringTable['y_renderSetupWindow.kAvailableUserTemplates'    ]

kCreateLayerButton  = maya.stringTable['y_renderSetupWindow.kCreateLayerButton'  ]
kImportLayerButton  = maya.stringTable['y_renderSetupWindow.kImportLayerButton'  ]
kAcceptImportButton = maya.stringTable['y_renderSetupWindow.kAcceptImportButton' ]
kRefreshLayerButton = maya.stringTable['y_renderSetupWindow.kRefreshLayerButton' ]

kCreateOverrideToolTip = maya.stringTable['y_renderSetupWindow.kCreateOverrideToolTip' ]
kSetLocalRenderToolTip = maya.stringTable['y_renderSetupWindow.kSetLocalRenderToolTip' ]

def _exportAOVs():
    selectedFilepath = cmds.fileDialog2(caption=kExportAOVs, 
                                        fileFilter="*.json", dialogStyle=2)

    if selectedFilepath is not None and len(selectedFilepath[0]) > 0:
        aovData = aovs.encode()
        with open(selectedFilepath[0], "w") as file:
            json.dump(aovData, file, sort_keys=True)

class TemplateThreadWorker(QObject):
    """This class implements the worker for templates
    It is intended to be executed in a thread"""

    #Two signals are defined, one for the beginning and one for the end
    #Done signal emit a templateList and an int (the index of the thread)
    done = Signal(object, int)
    start = Signal()

    def __init__(self, templateDir, model, index):
        super(TemplateThreadWorker, self).__init__()
        self.model = model
        self.templateDir = templateDir
        self.index = index
        self.templateList = None
        self.end = False

    @Slot()
    def run(self):
        self.templateList = []
        if self.templateDir is not None:
            for item in self.model.templateActions(self.templateDir):
                self.templateList.append(item)
                if self.end:
                    # If the main thread changed this bool, return
                    # from the function. The main thread does not need
                    # the results anymore.
                    return
            if not self.end:
                # Emit only if the main thread still needs the results
                self.done.emit(self.templateList, self.index)


class SceneView(QTreeView):
    """
    This class implements the scene view.
    """
    
    # Constants
    VIEW_PADDING = utils.dpiScale(4)
    EXPAND_WIDTH = utils.dpiScale(60)

    def __init__(self, parent):
        super(SceneView, self).__init__(parent=parent)
        # hold a local reference to this model so it does not get deleted before
        # we get a chance to dispose it.
        self.localModelRef = scene.SceneProxy(self)
        self.setModel(self.localModelRef)
        self.setIndentation(0)
        self.setMouseTracking(True)

        self.expandAll()

        self.setHeaderHidden(True)
        self.setItemDelegate(SceneDelegate(self))
        self.setStyle(RenderSetupStyle(self.style()))
        
        self.setSizePolicy(QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed))
        
        self.collapsed.connect(self.onCollapse)
        self.expanded.connect(self.onExpand)
        self.clicked.connect(self.onClick)

        self.dragStartPosition = None
        
        # The tree needs to be resized when the Scene is collapsed and expanded
        # When collapsed the tree height is set to self.COLLAPSED_HEIGHT and when
        # expanded to self.EXPANDED_HEIGHT.
        self.COLLAPSED_HEIGHT = utils.dpiScale(scene.ROW_HEIGHT) + self.VIEW_PADDING
        item = self.model().invisibleRootItem().child(0, 0)
        self.EXPANDED_HEIGHT = (item.rowCount() + 1 ) * utils.dpiScale(scene.ROW_HEIGHT) + self.VIEW_PADDING
        self.setFixedHeight(self.EXPANDED_HEIGHT)
        
        self.buttonPressed = None

        self.contextMenu = menu.Menu(self)

        self.setVisibilityAction = action.Action(scene.SET_VISIBILITY_ACTION, self.contextMenu)
        self.setVisibilityAction.triggered.connect(self._setVisibility)
        self.setRenderableAction = action.Action(scene.SET_RENDERABLE_ACTION, self.contextMenu)
        self.setRenderableAction.triggered.connect(self._setRenderable)
        self.staticActions = [ self.setVisibilityAction, self.setRenderableAction ]

        self.presetMenu = menu.Menu(scene.PRESET_MENU, self.contextMenu)
        self.presetMenuAction = action.Action(scene.PRESET_MENU, self.contextMenu, triggered=self._popupPresetMenu)

        self.aovsMenu = menu.Menu(scene.AOVS_MENU, self.contextMenu)
        self.aovsMenuAction = action.Action(scene.AOVS_MENU, self.contextMenu, triggered=self._popupAOVsMenu)
        self.aovsExportCurrentAction = action.Action(scene.EXPORT_CURRENT_ACTION, self.contextMenu)
        self.aovsMenu.addAction(self.aovsExportCurrentAction)
        self.aovsExportCurrentAction.triggered.connect(_exportAOVs)

        self.expandCollapseAction = action.Action(scene.EXPAND_COLLAPSE_ACTION, self.contextMenu, triggered=self._toggleExpandCollapse)

    def dispose(self):
        self.localModelRef.dispose()

    def _popupPresetMenu(self):
        self.presetMenu.clear()
        
        # Export current menu item
        exportCurrentPresetAction = action.Action(scene.EXPORT_CURRENT_ACTION, self.contextMenu)
        exportCurrentPresetAction.triggered.connect(self._exportCurrentPreset)
        self.presetMenu.addAction(exportCurrentPresetAction)
        self.presetMenu.addSeparator()

        # Default preset menu item
        defaultPresetAction = action.Action(scene.DEFAULT_PRESET_ACTION, self.contextMenu)
        defaultPresetAction.triggered.connect(self._setDefaultPreset)
        self.presetMenu.addAction(defaultPresetAction)

        # Global presets menu items
        globalPresetsAction = action.Action(scene.GLOBAL_PRESETS_ACTION, self.contextMenu)
        globalPresetsAction.setSeparator(True)
        self.presetMenu.addAction(globalPresetsAction)
        currentRenderer = cmds.getAttr('defaultRenderGlobals.currentRenderer')
        globalPresets = prefs.getGlobalPresets(currentRenderer)
        for globalPreset in globalPresets:
            globalPresetAction = action.Action(globalPreset, self.contextMenu)
            globalPresetAction.triggered.connect(self._setGlobalPreset)
            self.presetMenu.addAction(globalPresetAction)

        # User presets menu items
        userPresetsAction = action.Action(scene.USER_PRESETS_ACTION, self.contextMenu)
        userPresetsAction.setSeparator(True)
        self.presetMenu.addAction(userPresetsAction)        
        userPresets = prefs.getUserPresets(currentRenderer)
        for userPreset in userPresets:
            userPresetAction = action.Action(userPreset, self.contextMenu)
            userPresetAction.triggered.connect(self._setUserPreset)
            self.presetMenu.addAction(userPresetAction)

        self.presetMenu.popup(QCursor.pos())

    def _popupAOVsMenu(self):
        self.aovsMenu.popup(QCursor.pos())
        
    def _exportCurrentPreset(self):
        prefs.savePreset()
        
    def _setDefaultPreset(self):
        maya.mel.eval("unifiedRenderGlobalsRevertToDefault")
        
    def _setGlobalPreset(self):
        prefs.loadGlobalPreset(self.sender().text())

    def _setUserPreset(self):
        prefs.loadUserPreset(self.sender().text())

    def _getCorrespondingItem(self, index):
        if index.isValid():
            return self.model().itemFromIndex(index)
        return None

    @cursors.waitCursor()
    def _setVisibility(self):
        item = self._getCorrespondingItem(self.currentIndex())
        
        # UI Feedback
        progressBar = utils.ProgressBar()
        progressBar.createProgressBar('Switching Back to Master Layer', \
            modelUtils.getTotalNumberOperations(item._model))
        
        # Trigger the progressBar visibility
        progressBar.stepProgressBar()

        item.setData(not item.data(scene.NODE_VISIBLE), scene.NODE_VISIBLE)

        # UI Feedback ended
        progressBar.endProgressBar()

    def _setRenderable(self):
        item = self._getCorrespondingItem(self.currentIndex())
        item.setData(not item.data(scene.NODE_RENDERABLE), scene.NODE_RENDERABLE)
    
    def _toggleExpandCollapse(self):
        index = self.currentIndex()
        self.setExpanded(index, not self.isExpanded(index))

    def _getCurrentAction(self, point, index):
        item = self.model().itemFromIndex(index)
        if item:
            # If the row has children, check to see if the user clicked before the row entry name. If so, then expand/collapse the row
            if item.rowCount() > 0 and point.x() < self.EXPAND_WIDTH:
                return self.expandCollapseAction

            actionName = self.itemDelegate().lastHitAction
            if actionName != None:
                if (actionName == scene.PRESET_MENU):
                    return self.presetMenuAction
                elif (actionName == scene.AOVS_MENU):
                    return self.aovsMenuAction
                for a in self.staticActions:
                    if a.text() == actionName:
                        return a
            return None
        return None

    def mousePressEvent(self, event):
        event = utils.updateMouseEvent(event)
        self.buttonPressed = event.button()
        if event.button() == Qt.MiddleButton:
            self.dragStartPosition = event.pos()
        elif event.button() == Qt.LeftButton:
            index = self.indexAt(event.pos())
            # get the action button under the mouse if there is one
            action = self._getCurrentAction(event.pos(), index)
            if action != None:
                # set the currently clicked on element active without selecting it
                self.selectionModel().setCurrentIndex(index, QItemSelectionModel.NoUpdate)
                # trigger the action to be executed
                action.trigger()
                event.accept()
        else:
            super(SceneView, self).mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        event = utils.updateMouseEvent(event)
        index = self.indexAt(event.pos())
        item = self.model().itemFromIndex(index)
        if item:
            item.onDoubleClick(self)

    def leaveEvent(self, *args, **kwargs):
        self.itemDelegate().lastHitAction = None

    def mouseMoveEvent(self, event):
        event = utils.updateMouseEvent(event)
        if self.dragStartPosition:
            index = self.indexAt(self.dragStartPosition)
            item = self.model().itemFromIndex(index)
            if item is not None and item.data(scene.NODE_ACCEPTS_DRAG) and \
                            int(event.buttons()) & int(Qt.MiddleButton) and \
                            (event.pos() - self.dragStartPosition).manhattanLength() >= QApplication.startDragDistance():
                drag = QDrag(self)
                mimeData = QMimeData()
                mimeData.setText(item.name)
                drag.setMimeData(mimeData)
                dropAction = drag.exec_()

        QTreeView.mouseMoveEvent(self, event)

        if not self.itemDelegate().lastHitAction:
            QToolTip.hideText()

        # dirty the treeview so it will repaint when mouse is over it
        # this is needed to change the icons when ohvered over them
        self.itemDelegate().lastHitAction = None
        region = self.childrenRegion()
        self.setDirtyRegion(region)

    def onClick(self, index):
        if self.buttonPressed == Qt.LeftButton:
            item = self.model().itemFromIndex(index)
            item.onClick(self)

    def onDoubleClick(self, index):
        if self.buttonPressed == Qt.LeftButton:
            item = self.model().itemFromIndex(index)
            item.onDoubleClick(self)

    def onCollapse(self):
        self.setFixedHeight(self.COLLAPSED_HEIGHT)

    def onExpand(self):
        self.setFixedHeight(self.EXPANDED_HEIGHT)

class RenderSetupView(QTreeView):
    """
    This class implements the render setup view. 
    """

    NO_LAYERS_IMAGE = utils.createPixmap(":/RS_no_layer.png")
    PLACEHOLDER_TEXT_PEN = QPen(QColor(128, 128, 128))
    HALF_FONT_HEIGHT = utils.dpiScale(7)
    NO_LAYERS_IMAGE_SIZE = utils.dpiScale(62)

    def __init__(self, parent):
        super(RenderSetupView, self).__init__(parent=parent)
        self.actionButtonPressed = False
        self.renderLayerTemplates = None
        self.setIndentation(10)

        self.setMouseTracking(True)

        # Set up the Qt Model
        self.localModelRef = renderSetup.RenderSetupProxy(self)
        self.setModel(self.localModelRef)

        self.setHeaderHidden(True)
        self.setItemDelegate(RenderSetupDelegate(self))
        self.setStyle(RenderSetupStyle(self.style()))
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Right click context
        self.contextMenu = menu.Menu(self)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

        # Right click potential actions
        self.createCollectionAction = action.Action(renderSetup.CREATE_COLLECTION_ACTION, self.contextMenu)
        self.createCollectionAction.triggered.connect(partial(self._createCollection, collectionModel.Collection.kTypeId))
        self.setVisibilityAction = action.Action(renderSetup.SET_VISIBILITY_ACTION, self.contextMenu)
        self.setVisibilityAction.triggered.connect(self._setVisibility)
        self.setRenderableAction = action.Action(renderSetup.SET_RENDERABLE_ACTION, self.contextMenu)
        self.setRenderableAction.triggered.connect(self._setRenderable)
        self.createAbsoluteOverrideAction = action.Action(renderSetup.CREATE_ABSOLUTE_OVERRIDE_ACTION, self.contextMenu)
        self.createAbsoluteOverrideAction.triggered.connect(partial(self._createOverride, overrideTypeId=overrideModel.AbsOverride.kTypeId))
        self.createRelativeOverrideAction = action.Action(renderSetup.CREATE_RELATIVE_OVERRIDE_ACTION, self.contextMenu)
        self.createRelativeOverrideAction.triggered.connect(partial(self._createOverride, overrideTypeId=overrideModel.RelOverride.kTypeId))
        self.createConnectionOverrideAction = action.Action(renderSetup.CREATE_CONNECTION_OVERRIDE_ACTION, self.contextMenu)
        self.createConnectionOverrideAction.triggered.connect(partial(self._createOverride, overrideTypeId=connectionOverrideModel.ConnectionOverride.kTypeId))
        self.createShaderOverrideAction = action.Action(renderSetup.CREATE_SHADER_OVERRIDE_ACTION, self.contextMenu)
        self.createShaderOverrideAction.triggered.connect(partial(self._createOverride, overrideTypeId=connectionOverrideModel.ShaderOverride.kTypeId))
        self.createMaterialOverrideAction = action.Action(renderSetup.CREATE_MATERIAL_OVERRIDE_ACTION, self.contextMenu)
        self.createMaterialOverrideAction.triggered.connect(partial(self._createOverride, overrideTypeId=connectionOverrideModel.MaterialOverride.kTypeId))

        self.expandCollapseAction = action.Action(renderSetup.EXPAND_COLLAPSE_ACTION, self.contextMenu, triggered=self._toggleExpandCollapse)
        self.setEnabledAction = action.Action(renderSetup.SET_ENABLED_ACTION, self.contextMenu, triggered=self._setEnabled)
        self.isolateSelectAction = action.Action(renderSetup.SET_ISOLATE_SELECTED_ACTION, self.contextMenu, triggered=self._setIsolateSelected)
        self.renameAction = action.Action(renderSetup.RENAME_ACTION, self.contextMenu, triggered=self._rename)
        self.deleteAction = action.Action(renderSetup.DELETE_ACTION, self.contextMenu, triggered=self._delete)
        self.setLocalRenderAction = action.Action(renderSetup.SET_LOCAL_RENDER_ACTION, self.contextMenu, triggered=self._setLocalRender)
        self.setLocalRenderAction.setToolTip(kSetLocalRenderToolTip)

        # staticActions are a list of potential actions proposed in the
        # context menu.  Illegal actions are filtered out in
        # showContextMenu() by querying the proxy items.
        self.staticActions = [ self.createCollectionAction,
                               self.setVisibilityAction,
                               self.setRenderableAction,
                               self.setEnabledAction,
                               self.isolateSelectAction,
                               self.renameAction,
                               self.deleteAction,
                               self.createConnectionOverrideAction,
                               self.createShaderOverrideAction,
                               self.createMaterialOverrideAction,
                               self.createAbsoluteOverrideAction,
                               self.createRelativeOverrideAction,
                               self.setLocalRenderAction]
        
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)
        
        self.installEventFilter(self)
        
        self.menuTemplates = []
        self.threads = []
        self.exportSelectedAction = None

        # Restore all expanded nodes, beginning from the Model Ref
        self._restoreExpandedState(self.localModelRef)
        
    def rowsInserted(self, parent, start, end):
        super(RenderSetupView, self).rowsInserted(parent, start, end)
        index = QModelIndex(parent)
        while(index.isValid()):
            self.setExpanded(index, True)
            index = index.parent()

    def setExpanded(self, index, state):
        """ Override from the Qt class
        Expands the group and saves its state """
        super(RenderSetupView, self).setExpanded(index, state)
        utils.setExpandedState(self._getCorrespondingItem(index)._model.thisMObject(), state)

    def _clearTemplates(self):
        # Note: As the actions are created by themselves (i.e. not using QMenu.createAction(name)),
        #       the life scope is under the caller responsibility. Prior to their deletion,
        #       the parent has to be reset.
        for item in self.menuTemplates[:]:
            if item:
                item.setParent(None)
        self.menuTemplates[:] = []
        # Ping the worker to not emit results and return
        for thr in self.threads:
            thr[0].end = True

    def dispose(self):
        self.localModelRef.dispose()
        self._clearTemplates()

    def mousePressEvent(self, event):
        wasRightButton = event.button() == Qt.RightButton
        event = utils.updateMouseEvent(event)
        if event.button() == Qt.LeftButton:
            if not event.modifiers() & Qt.ShiftModifier:
                index = self.indexAt(event.pos())
                # get the action button under the mouse if there is one
                action = self._getCurrentAction(event.pos(), index)
                if action != None:
                    # set the currently clicked on element active without selecting it
                    self.selectionModel().setCurrentIndex(index, QItemSelectionModel.NoUpdate)
                    # trigger the action to be executed
                    action.trigger()
                    self.actionButtonPressed = True
                    event.accept()
                else:
                    # Select the currently clicked on element
                    super(RenderSetupView, self).mousePressEvent(event)
            else:
                super(RenderSetupView, self).mousePressEvent(event)

        elif event.button() == Qt.RightButton:
            if not wasRightButton:
                self.customContextMenuRequested.emit(event.pos())
            
            # if the clicked item is already selected, then right clicking should not change the selection
            index = self.indexAt(event.pos())
            if not self.selectionModel().isSelected(index):
                item = self.model().itemFromIndex(index)
                if item:
                    # Select the currently clicked on element
                    self.setCurrentIndex(index)
            else:
                # Because of the behavior for 'click on action' where the current index is changed
                # but the selection model is not updated accordingly, 
                # ensure that the selected item is also the current index
                self.selectionModel().setCurrentIndex(index, QItemSelectionModel.NoUpdate)

        elif event.button() == Qt.MiddleButton:
            super(RenderSetupView, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        event = utils.updateMouseEvent(event)
        if not self.actionButtonPressed:
            super(RenderSetupView, self).mouseReleaseEvent(event)
        else:
            self.actionButtonPressed = False

    def leaveEvent(self, *args, **kwargs):
        self.itemDelegate().lastHitAction = None

    def mouseMoveEvent(self, event):
        event = utils.updateMouseEvent(event)
        if not self.actionButtonPressed:
            super(RenderSetupView, self).mouseMoveEvent(event)

        if not self.itemDelegate().lastHitAction:
            QToolTip.hideText()

        # dirty the treeview so it will repaint when mouse is over it
        # this is needed to change the icons when ohvered over them
        self.itemDelegate().lastHitAction = None
        region = self.childrenRegion()
        self.setDirtyRegion(region)

    def mouseDoubleClickEvent(self, event):
        event = utils.updateMouseEvent(event)
        index = self.indexAt(event.pos())
        item = self.model().itemFromIndex(index)
        action = self._getCurrentAction(event.pos(), index)
        if action != None:
            # trigger the action to be executed
            action.trigger()
        elif item and item.data(renderSetupRoles.NODE_EDITABLE):
            # Put item in edit mode if it is editable
            self.edit(index)

        # Propagate event to item
        if item:
            item.onDoubleClick(self)

    def eventFilter(self, object, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Delete:
                self._delete()
            return True
        else:
            return super(RenderSetupView, self).eventFilter(object, event)

    def dragEnterEvent(self, event):
        # Check if this is a supported scene item.
        # Add more items here if needed later
        if event.mimeData().text() == scene.LIGHTS_STR \
                or event.mimeData().text() == scene.RENDER_SETTINGS_STR \
                or event.mimeData().text() == scene.AOVS_STR:
            event.acceptProposedAction()
        else:
            super(RenderSetupView, self).dragEnterEvent(event)

    def dragMoveEvent(self, event):
        # Check if this is a supported scene item.
        # Add more items here if needed later
        if event.mimeData().text() == scene.LIGHTS_STR \
                or event.mimeData().text() == scene.RENDER_SETTINGS_STR \
                or event.mimeData().text() == scene.AOVS_STR:
            index = self.indexAt(event.pos())
            if not index.isValid():
                event.ignore()
                return
            item = self.model().itemFromIndex(index)
            item.handleDragMoveEvent(event)
        else:
            super(RenderSetupView, self).dragMoveEvent(event)

    def dropEvent(self, event):
        # Check if this is a supported scene item.
        # Add more items here if needed later
        if event.mimeData().text() == scene.LIGHTS_STR \
                or event.mimeData().text() == scene.RENDER_SETTINGS_STR \
                or event.mimeData().text() == scene.AOVS_STR:
            index = self.indexAt(event.pos())
            if not index.isValid():
                return
            item = self.model().itemFromIndex(index)
            item.handleDropEvent(event, self)
        else:
            super(RenderSetupView, self).dropEvent(event)
            # MAYA-66671: Workaround for a Qt Bug: https://bugreports.qt.io/browse/QTBUG-26229
            #             The description of the workaround can be found here: http://www.qtcentre.org/archive/index.php/t-49819.html
            #             Basically this makes dropMimeEvents cancel-able. Although it's not ideal as the drop indicator
            #             still makes it seem as though a cancelled drop was a valid operation initially.
            if self.model().dropMimeDataFailure:
                event.setDropAction(Qt.IgnoreAction)

    def paintEvent(self, e):
        """ Overrides the paint event to make it so that place holder text is displayed when the list is empty. """
        super(RenderSetupView, self).paintEvent(e)
        if self.model().rowCount() == 0:
            painter = QPainter(self.viewport())
            sz = self.NO_LAYERS_IMAGE_SIZE
            sz = sz / 2
            pos = self.contentsRect().center() - QPoint(sz, sz+self.HALF_FONT_HEIGHT)
            painter.drawPixmap(pos, self.NO_LAYERS_IMAGE)

            oldPen = painter.pen()
            painter.setPen(self.PLACEHOLDER_TEXT_PEN)
            textRect = self.contentsRect()
            textRect.translate(0, sz)
            painter.drawText(textRect, Qt.AlignCenter, maya.stringTable['y_renderSetupWindow.kNoLayers' ])
            painter.setPen(oldPen)

    def _getCorrespondingItem(self, index):
        if index.isValid():
            return self.model().itemFromIndex(index)
        return None
        
    def _createActionSubMenus(self, topMenu, name):
        ''' Add all the submenus computed from the action name '''
        # Find all sub menus (i.e. all parts of the path)
        head, tail = os.path.split(name)
        parts = [tail]
        while head!='':
            head, tail = os.path.split(head)
            parts.insert(0, tail)
        # If there is a path in the action name then create or reuse the sub menus
        currentMenu = topMenu
        for idx in range(len(parts)-1):
            existingSubMenus = currentMenu.findChildren(QMenu)
            for o in existingSubMenus:
                if o.title()==parts[idx]:
                    currentMenu = o
                    break
            else:
                currentMenu = currentMenu.addMenu(parts[idx])
        return (currentMenu, parts[-1])

    def _filterSelectedIndices(self, selectedIndices):
        ''' Filter all indices by type '''
        proxies = []
        # Check that the selected items are from the same type
        for index in selectedIndices:
            proxy = self.model().itemFromIndex(index)
            if len(proxies)>=1 and proxies[0].type()!=proxy.type():
                proxies = []
                break
            proxies.append(proxy)
        # Check that only one render settings or lights collection
        #  could be exported in the same export file.
        if( len(proxies)>1 and 
            ( proxies[0].type()==renderSetup.RENDER_SETTINGS_TYPE 
                or proxies[0].type()==renderSetup.LIGHTS_TYPE ) ):
            proxies = []
        return proxies

    def _addExportSelectedMenu(self, selectedIndices):
        ''' Add the export selected action in the context menu '''
        # Selected proxies should have the same type
        proxies = self._filterSelectedIndices(selectedIndices)
        if len(proxies)>=1:
            # Delete previous action 
            if self.exportSelectedAction is not None:
                self.exportSelectedAction.setParent(None)
            # Build using action.Action to propagate an exception if any
            self.exportSelectedAction = action.Action(kExportSelected, self.contextMenu)
            self.exportSelectedAction.triggered.connect(partial(self._exportSelected, proxies))
            self.contextMenu.addAction(self.exportSelectedAction)

    def showContextMenu(self, point):
        ''' Rebuild from scratch the context menu '''
        selectedIndexes = self.selectedIndexes()
        numIndexes = len(selectedIndexes)
        # Only show the context menu if we have selected items
        if numIndexes > 0:
            # Make a list of all actions and remove all actions that don't apply to each element        
            applicableStaticActions = list(self.staticActions)
            for selectedIndex in selectedIndexes:
                actionsToRemove = []
                for action in applicableStaticActions:
                    item = self._getCorrespondingItem(selectedIndex)
                    if not item.supportsAction(action.text(), numIndexes):
                        actionsToRemove.append(action)
                for actionToRemove in actionsToRemove:
                    applicableStaticActions.remove(actionToRemove)

            # Note: Directly clear() the QMenu causes 'already deleted exception'
            #       so I manually remove the actions
            for a in reversed(self.contextMenu.actions()):
                self.contextMenu.removeAction(a)
                
            # Add the dynamic menus to the context menu
            if numIndexes==1:
                self._clearTemplates()

                self._createTemplateMenu(self.contextMenu, self._getCorrespondingItem(selectedIndexes[0]))

            # Add the export selected action
            self._addExportSelectedMenu(selectedIndexes)

            # Add the static menus to the context menu
            self.contextMenu.addActions(applicableStaticActions)

            self.contextMenu.exec_(self.mapToGlobal(point))

    def _rename(self):
        """ Begins editing of the current tree view index. """
        self.edit(self.currentIndex())

    def _expandAndEditOverride(self, overrideIndex):
        if overrideIndex != self.currentIndex():
            self.expand(self.currentIndex())
            self.setCurrentIndex(overrideIndex)
            if userPrefs.getEditMode():
                self.edit(overrideIndex)

    @undo.chunk('Create override')
    def _createOverride(self, overrideTypeId):
        item = self._getCorrespondingItem(self.currentIndex())
        if item:
            overrideIndex = item.createOverride(overrideTypeId)
            self._expandAndEditOverride(overrideIndex)

    def _getCurrentAction(self, point, index):
        item = self.model().itemFromIndex(index)
        if item:
            # If the row has children, check to see if the user clicked before the row entry name. If so, then expand/collapse the row
            if item.rowCount() > 0:
                leftOffset = 0
                indent = item.depth() * self.indentation()
                leftOffset = indent + item.data(renderSetupRoles.NODE_HEADING_WIDTH) + RenderSetupDelegate.LEFT_NON_TEXT_OFFSET
                if point.x() < leftOffset:
                    return self.expandCollapseAction

            actionName = self.itemDelegate().lastHitAction
            if actionName != None:
                for a in self.staticActions:
                    if a.text() == actionName:
                        return a
            return None
        return None

    @cursors.waitCursor()
    def _setVisibility(self):
        item = self._getCorrespondingItem(self.currentIndex())
        
        # UI Feedback
        progressBar = utils.ProgressBar()
        progressBar.createProgressBar('Switching Render Layer Visibility', \
            modelUtils.getTotalNumberOperations(item.model))

        # Trigger the progressBar visibility
        progressBar.stepProgressBar()

        item.setData(not item.data(renderSetupRoles.NODE_VISIBLE), renderSetupRoles.NODE_VISIBLE)

        # UI Feedback ended
        progressBar.endProgressBar()

    def _setRenderable(self):        
        item = self._getCorrespondingItem(self.currentIndex())
        item.setData(not item.data(renderSetupRoles.NODE_RENDERABLE), renderSetupRoles.NODE_RENDERABLE)

    def _setState(self, flag, state, item = None):
        if item == None:
            item = self._getCorrespondingItem(self.currentIndex())
        if item:
            if not self.selectionModel().isSelected(self.currentIndex()):
                # only toggle the current item if it's not selected
                item.setData(state, flag)
            else:
                # else set all selected items to the same state
                selectedIndexes = self.selectedIndexes()
                for selectedIndex in selectedIndexes:
                    selItem = self._getCorrespondingItem(selectedIndex)
                    if selItem:
                        selItem.setData(state, flag)
        
        # invalidate the view for full redraw.
        # MAYA-66676: It is unclear why this is needed, we should look into removing this
        region = self.childrenRegion()
        self.setDirtyRegion(region)

    def _setFilterType(self, value, item = None):
        if item == None:
            item = self._getCorrespondingItem(self.currentIndex())
        if item:
            if not self.selectionModel().isSelected(self.currentIndex()):
                # only set the current item if it's not selected
                item.model.getSelector().setFilterType(value)
            else:
                # else set all selected items to the same state
                selectedIndexes = self.selectedIndexes()
                for selectedIndex in selectedIndexes:
                    selItem = self._getCorrespondingItem(selectedIndex)
                    if selItem:
                        selItem.model.getSelector().setFilterType(value)
        
        # invalidate the view for full redraw.
        # MAYA-66676: It is unclear why this is needed, we should look into removing this
        region = self.childrenRegion()
        self.setDirtyRegion(region)

    def _toggleState(self, flag):
        item = self._getCorrespondingItem(self.currentIndex())
        if item:
            state = not item.data(flag)
            self._setState(flag, state, item)

    def _toggleExpandCollapse(self):
        index = self.currentIndex()
        self.setExpanded(index, not self.isExpanded(index))

    @cursors.waitCursor()
    def _setEnabled(self):
        self._toggleState(renderSetupRoles.NODE_SELF_ENABLED)

    @cursors.waitCursor()
    def _setIsolateSelected(self):
        self._toggleState(renderSetupRoles.NODE_ISOLATE_SELECTED)

    def _createCollection(self, nodeType):
        item = self._getCorrespondingItem(self.currentIndex())
        if item:
            collectionIndex = item.createCollection("", nodeType)
            if collectionIndex!=self.currentIndex():
                self.expand(self.currentIndex())
                self.setCurrentIndex(collectionIndex)
                if userPrefs.getEditMode():
                    self.edit(collectionIndex)

    def _createRenderLayer(self):
        renderLayerIndex = self.model().createRenderLayer("")
        if renderLayerIndex!=self.currentIndex():
            self.setCurrentIndex(renderLayerIndex)
            if userPrefs.getEditMode():
                self.edit(renderLayerIndex)

    #Slot to connect to the done signal of the TemplateThreadWorker
    @Slot(object, int)
    def _templatesOver(self, templateList, index):
        self.menuTemplates[index].clear()
        self._addTemplateMenusFromList(templateList, self.menuTemplates[index])

    def _addTemplateMenusFromList(self, templateList, templateMenu):
        ''' Add all the template actions in the templateMenu from a list 
        and return the actions as a list'''
        actions = []
        if templateList:
            for (name, tooltip, callable) in templateList:
                (parentMenu, actionName) = self._createActionSubMenus(templateMenu, name)
                # Create and attach the action
                a = action.Action(actionName, parentMenu)
                a.setToolTip(tooltip)
                a.triggered.connect(callable)
                parentMenu.addAction(a)
                actions.append(a)
        else:
            #If there is no template remaining after the filter but the base folder exists
            loading = action.Action('Empty', templateMenu)
            loading.setEnabled(False)
            font = loading.font()
            font.setItalic(True)
            loading.setFont(font)
            templateMenu.addAction(loading)
        return actions

    def _initTemplatesThread(self, index, menuName, templateDir, topMenu, model):
        """ Create the menu and connect threads signals """
        self.menuTemplates.append(topMenu.addMenu(menuName))
        loading = action.Action('Loading...', self.menuTemplates[index])
        loading.setEnabled(False)
        self.menuTemplates[index].addAction(loading)

        # Create the thread and the worker ,start it, move the worker to the thread and connect signals
        # Threads are not deleted in order to resolve segFault on Linux
        if len(self.threads) == index:
            self.threads.append([None, QThread()])
            self.threads[index][-1].start()
        self.threads[index][0] = TemplateThreadWorker(templateDir, model, index)
        self.threads[index][0].moveToThread(self.threads[index][-1])
        self.threads[index][0].start.connect(self.threads[index][0].run)
        self.threads[index][0].done.connect(self._templatesOver)

    def _createTemplateMenu(self, topMenu, model):
        """Factorization with contextMenu in order to create the template menu"""
        index = 0
        #Create the menu only if the dir exist
        if userPrefs.getGlobalTemplateDirectoryWithoutCheck():
            self._initTemplatesThread(index, kAvailableGlobalTemplates, \
                userPrefs.getGlobalTemplateDirectoryWithoutCheck(), topMenu, model)
            index += 1

        if userPrefs.getUserTemplateDirectory():
            self._initTemplatesThread(index, kAvailableUserTemplates, \
                userPrefs.getUserTemplateDirectory(), topMenu, model)

        #Start the threads
        for thr in self.threads:
            thr[0].start.emit()

    def _importLayerButton(self):
        self._clearTemplates()
        #Save the position of the cursor in case of little freezing
        cursorPosSave = QCursor.pos()

        # Delete the former menu and create the new one
        self.renderLayerTemplates = menu.Menu('')

        self._createTemplateMenu(self.renderLayerTemplates, self.model())

        # Show the menu
        self.renderLayerTemplates.popup(cursorPosSave)

    def _acceptImportButton(self):
        self.model().acceptImport()

    def _refreshLayerButton(self):
        pass

    @undo.chunk('Delete items')
    def _deleteItems(self, indexes):
        for index in indexes:
            item = self._getCorrespondingItem(index)
            if item:
                item.delete()
    
    @undo.chunk('Set Local Render')
    def _setLocalRender(self):
        value = not self._getCorrespondingItem(self.currentIndex()).isLocalRender()
        for index in self.selectedIndexes():
            item = self._getCorrespondingItem(index)
            if item:
                item.setLocalRender(value)

    @cursors.waitCursor()
    def _delete(self):
        selectedIndexes = self.selectedIndexes()        
        if len(selectedIndexes) < 1:
            return
        persistentSelectedIndexes = []
        for selectedIndex in selectedIndexes:
            persistentSelectedIndexes.append(QPersistentModelIndex(selectedIndex))
        self._deleteItems(persistentSelectedIndexes)

    def _exportFileBrowser(self, proxies, caption=kExportAllTitle):
        # Create the directory if needed
        basePath = userPrefs.getUserTemplateDirectory()
        if not os.path.exists(basePath):
            os.makedirs(basePath)

        # Display the file dialog
        selectedFilepath = cmds.fileDialog2(caption=caption, 
                                            fileFilter='*.'+userPrefs.getFileExtension(), dialogStyle=2, 
                                            optionsUICreate="exportAllOptionsUIBuilder",
                                            startingDirectory=basePath)

        # Export the render setup to a file
        if selectedFilepath is not None and len(selectedFilepath[0]) > 0:
            self.model().exportSelectedToFile(selectedFilepath[0], importExportUI.ExportAllUI.notesText, proxies)
    
    def _exportSelected(self, proxies):
         # Arbitrary pick the notes of the first selected proxy
        importExportUI.ExportAllUI.notesText = proxies[0].data(renderSetupRoles.NODE_NOTES)
        self._exportFileBrowser(proxies, kExportSelectedTitle)

    def _restoreExpandedState(self, proxy):
        """ Recursively get all proxies of the treeview
        and expand them if they were already expanded before closing the 
        window, and do the same on their children.
        It stops because overrides do not have children
        (and if they have children, it will still work) """

        proxies = []
        for i in range(proxy.rowCount()):
            proxies.append(proxy.child(i,0))

        for child in proxies:
            if utils.getExpandedState(child._model.thisMObject()):
                self.setExpanded(child.index(), True)
                self._restoreExpandedState(child)

class RenderSetupCentralWidget(QWidget):
    """
    This class implements the controls inside the render setup window
    """

    PREFERRED_SIZE = QSize(370, 420)
    MINIMUM_SIZE = QSize(220, 220)

    def __init__(self, parent):
        # The class MayaQWidgetDockableMixin retrieves the right parent (i.e. Maya Main Window)
        super(RenderSetupCentralWidget, self).__init__(parent=parent)

        # Set up the file menu
        self.menuBar = QMenuBar(self)
        self.fileMenu = self.menuBar.addMenu(kFile)
        self.fileMenu.aboutToShow.connect(self._fileMenuAboutToBeShown)

        self.importAllAction = action.Action(kImportAll, self.fileMenu)
        self.importRenderSettingsAction = action.Action(kImportRenderSettings, self.fileMenu)
        self.importAOVsAction = action.Action(kImportAOVs, self.fileMenu)
        self.exportAllAction = action.Action(kExportAll, self.fileMenu)
        self.exportSelectedAction = action.Action(kExportSelected, self.fileMenu)
        self.exportRenderSettingsAction = action.Action(kExportRenderSettings, self.fileMenu)
        self.exportAOVsAction = action.Action(kExportAOVs, self.fileMenu)

        self.fileMenu.addAction(self.importAllAction)
        self.fileMenu.addAction(self.importRenderSettingsAction)
        self.fileMenu.addAction(self.importAOVsAction)
        self.fileMenu.addAction(self.exportAllAction)
        self.fileMenu.addAction(self.exportSelectedAction)
        self.fileMenu.addAction(self.exportRenderSettingsAction)
        self.fileMenu.addAction(self.exportAOVsAction)
        self.importAllAction.triggered.connect(self._importAll)
        self.importRenderSettingsAction.triggered.connect(self._importRenderSettings)
        self.importAOVsAction.triggered.connect(self._importAOVs)
        self.exportAllAction.triggered.connect(self._exportAll)
        self.exportSelectedAction.triggered.connect(self._exportSelected)
        self.exportRenderSettingsAction.triggered.connect(self._exportRenderSettings)
        self.exportAOVsAction.triggered.connect(self._exportAOVs)

        self.editMenu = self.menuBar.addMenu(kEdit)

        self.cutAction = action.Action(kCut, self.editMenu)
        self.cutAction.setShortcut(QKeySequence(kCutShortcut))
        self.copyAction = action.Action(kCopy, self.editMenu)
        self.copyAction.setShortcut(QKeySequence(kCopyShortcut))
        self.pasteAction = action.Action(kPaste, self.editMenu)
        self.pasteAction.setShortcut(QKeySequence(kPasteShortcut))
        self.cutAction.triggered.connect(self._cut)
        self.copyAction.triggered.connect(self._copy)
        self.pasteAction.triggered.connect(self._paste)

        self.editMenu.addAction(self.cutAction)
        self.editMenu.addAction(self.copyAction)
        self.editMenu.addAction(self.pasteAction)
        
        self.clipBoard = None
        
        self.optionsMenu = self.menuBar.addMenu(kOptions)
        # Add a menu item to control how render setup responds when there are changes
        # made to the scene while there is an active render layer.
        # If using dynamic update the render layer membership will be processed automatically
        # and immediately.  If not a visual indication will be given to the user informing them
        # they need to take action.
        self.autoUpdate = action.Action(kAutoUpdate, self.optionsMenu)
        self.autoUpdate.setCheckable(True)
        self.autoUpdate.setChecked(userPrefs.useDynamicUpdate())
        def _toggleDynamicUpdate():
            autoUpdate = not userPrefs.useDynamicUpdate()
            userPrefs.setUseDynamicUpdate(autoUpdate)
            self.autoUpdate.setChecked(autoUpdate)
        self.autoUpdate.triggered.connect(_toggleDynamicUpdate)
        self.optionsMenu.addAction(self.autoUpdate)

        self.helpMenu = self.menuBar.addMenu(kHelp)
        self.mayaHelp = action.Action(kMayaHelp, self.helpMenu)
        self.renderSetupHelp = action.Action(kRenderSetupHelp, self.helpMenu)
        self.mayaHelp.triggered.connect(lambda: maya.mel.eval("showHelp -d index.html"))
        self.renderSetupHelp.triggered.connect(lambda: maya.mel.eval("showHelp RenderSetup"))
        self.helpMenu.addAction(self.mayaHelp)
        self.helpMenu.addAction(self.renderSetupHelp)

        self.sceneView = SceneView(self)        
        self.renderSetupView = RenderSetupView(self)
        renderSetupModel.addObserver(self)
        
        # Adds the tree view to the window's layouts
        # the renderSetupView is set to be stretchy, while the other widgets are not
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(5)
        layout.addWidget(self.menuBar, 0)
        layout.addWidget(self.sceneView, 0)
        layout.addSpacing(10)
        layout.addWidget(self._createToolBar(), 0)
        layout.addWidget(self.renderSetupView, 1)
        self.setLayout(layout)

        self.setAcceptDrops(True)

    def aboutToDelete(self):
        """Cleanup method to be called immediately before the object is deleted."""
        self.sceneView.dispose()
        self.renderSetupView.dispose()
        # Qt object can take a long time before actually being destroyed
        # => observation of renderSetupModel may remain active (since self is not dead)
        # => explicitly remove observer to avoid receiving unwanted notifications
        renderSetupModel.removeObserver(self)

    # Obsolete interface.
    dispose = aboutToDelete

    def sizeHint(self):
        return self.PREFERRED_SIZE

    def minimumSizeHint(self):
        return self.MINIMUM_SIZE

    def renderSetupAdded(self):
        self.renderSetupView.model().refreshModel()
        self.sceneView.model().refreshModel()

    def renderSetupPreDelete(self):
        self.renderSetupView.model().resetModel()
        self.sceneView.model().resetModel()

    def _fileMenuAboutToBeShown(self):
        AOVCallbacksAvailable = not rendererCallbacks.getCallbacks(rendererCallbacks.CALLBACKS_TYPE_AOVS) is None
        self.importAOVsAction.setEnabled(AOVCallbacksAvailable)
        self.exportAOVsAction.setEnabled(AOVCallbacksAvailable)
    
    def _createToolBar(self):
        icon = QIcon(utils.createPixmap(":/RS_create_layer.png"))
        self.createLayerButton = RenderSetupButton(self, icon, utils.dpiScale(20))
        self.createLayerButton.setToolTip(kCreateLayerButton)
        icon = QIcon(utils.createPixmap(":/RS_import_layer.png"))
        self.importLayerButton = RenderSetupButton(self, icon, utils.dpiScale(20))
        self.importLayerButton.setToolTip(kImportLayerButton)
        
        icon = QIcon(utils.createPixmap(":/RS_warning.png"))
        self.issueButton = RenderSetupButton(self, icon, utils.dpiScale(20))
        self.issueButton.setToolTip(maya.stringTable['y_renderSetupWindow.kRenderSetupIssue' ])
        icon = QIcon(utils.createPixmap(":/RS_accept_update.png"))
        self.acceptImportButton = RenderSetupButton(self, icon, utils.dpiScale(20))
        self.acceptImportButton.setToolTip(kAcceptImportButton)
        #icon = QIcon(utils.createPixmap(_NOL10N(":/RS_refresh_layer.png")))
        #self.refreshLayerButton = RenderSetupButton(self, icon, utils.dpiScale(20))
        #self.refreshLayerButton.setToolTip(kRefreshLayerButton)
 
        # icon = QIcon(utils.createPixmap(_NOL10N(":/RS_create_layer_from_selection.png")))
        # createLayerFromSelectionButton = RenderSetupButton(self, icon)

        leftToolbarWidget = QWidget()
        leftToolbarLayout = QHBoxLayout()
        QLayoutItem.setAlignment(leftToolbarLayout, Qt.AlignBottom)
        leftToolbarLayout.setContentsMargins(0, 0, 0, 0)
        leftToolbarLayout.addStretch(1)       
        leftToolbarLayout.setDirection(QBoxLayout.RightToLeft)
        leftToolbarLayout.addWidget(self.importLayerButton)
        leftToolbarLayout.addWidget(self.createLayerButton)
        leftToolbarWidget.setLayout(leftToolbarLayout)

        rightToolbarWidget = QWidget()
        rightToolbarLayout = QHBoxLayout()
        QLayoutItem.setAlignment(rightToolbarLayout, Qt.AlignBottom)
        rightToolbarLayout.setContentsMargins(0, 0, 0, 0)
        rightToolbarLayout.addStretch(1)       
        rightToolbarLayout.setDirection(QBoxLayout.LeftToRight)
        rightToolbarLayout.addWidget(self.issueButton)
        rightToolbarLayout.addWidget(self.acceptImportButton)
        rightToolbarWidget.setLayout(rightToolbarLayout)       
        
        toolbarWidget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(utils.dpiScale(5), 0, utils.dpiScale(5), 0)
        layout.addWidget(leftToolbarWidget)
        layout.addWidget(rightToolbarWidget)
        toolbarWidget.setLayout(layout)

        self.createLayerButton.clicked.connect(self.renderSetupView._createRenderLayer)
        self.acceptImportButton.clicked.connect(self.renderSetupView._acceptImportButton)
        self.importLayerButton.clicked.connect(self.renderSetupView._importLayerButton)
        self.issueButton.clicked.connect(self._resolveIssue)
        
        self.issueButton.setVisible(renderSetupModel.RenderSetupIssuesObservable.instance().hasIssues())
        renderSetupModel.RenderSetupIssuesObservable.instance().addItemObserver(self._issuesChanged)
        
        return toolbarWidget
    
    def _issuesChanged(self):
        issue = renderSetupModel.RenderSetupIssuesObservable.instance().getIssue()
        self.issueButton.setVisible(issue is not None)
        if issue:
            self.issueButton.setIcon(QIcon(utils.createPixmap(":/RS_"+issue.type+".png")))
            self.issueButton.setToolTip(issue.description+maya.stringTable['y_renderSetupWindow.kDetails' ])
    
    def _resolveIssue(self):
        renderSetupModel.RenderSetupIssuesObservable.instance().resolveIssue()

    def _cut(self):
        if self._copy():
            self.renderSetupView._delete()
    
    def _copy(self):
        proxies = self.renderSetupView._filterSelectedIndices(self.renderSetupView.selectedIndexes())
        if len(proxies) == 0:
            return False
        # If the proxies don't have the same parent, then they should not be copyable
        parents = set()
        for proxy in proxies:
            parents.add(proxy.parent())
            if len(parents) > 1:
                return False
        self.clipBoard = self.renderSetupView.model().exportSelectedToJson(proxies)
        return True

    def _paste(self):
        selectedIndexes = self.renderSetupView.selectedIndexes()
        if len(selectedIndexes) < 1:
            self.renderSetupView.localModelRef.paste(self.clipBoard)
        else:
            item = self.renderSetupView.model().itemFromIndex(selectedIndexes[0])
            item.paste(self.clipBoard)
        
    def _exportAll(self):
        """ 
            Export the complete render setup to a file. 
        """
        notes = renderSetupModel.instance().getNotes()
        importExportUI.ExportAllUI.notesText = '' if notes is None else notes

        self.renderSetupView._exportFileBrowser(None)

    def _exportSelected(self):
        """ 
            Export the selected render setup objects to a file. 
        """
        proxies = self.renderSetupView._filterSelectedIndices(self.renderSetupView.selectedIndexes())
        if len(proxies)>=1:
            # Arbitrary pick the notes of the first selected proxy
            importExportUI.ExportAllUI.notesText = proxies[0].data(renderSetupRoles.NODE_NOTES)
            self.renderSetupView._exportFileBrowser(proxies, kExportSelectedTitle)
        else:
            # Indication of what went wrong
            OpenMaya.MGlobal.displayError(kExportSelectionError)

    def _importAll(self):
        """ 
            Import the complete render setup contained in the selected file using the options
            defined by the type of merge and the text to prepend for unexpected nodes.
        """
        selectedFilepath = cmds.fileDialog2(caption=kImportAllTitle, 
                                            fileFilter='*.'+userPrefs.getFileExtension(), fileMode=1, dialogStyle=2, 
                                            optionsUICreate="importAllOptionsUIBuilder",
                                            selectionChanged="importAllOptionsUIContentBuilder",
                                            startingDirectory=userPrefs.getUserTemplateDirectory())

        if selectedFilepath is not None and len(selectedFilepath[0]) > 0:
            try:
                self.renderSetupView.model().importAllFromFile(selectedFilepath[0], 
                    importExportUI.ImportAllUI.importType, 
                    importExportUI.ImportAllUI.importText)
            except TypeError as ex:
                # Try to understand if the user tried to import a template render setup.
                # In that case, reformat the error to have something more meaningful for the user.
                with open(selectedFilepath[0], "r") as file:
                    if jsonTranslatorUtils.isRenderSetupTemplate(json.load(file)):
                        OpenMaya.MGlobal.displayError(kImportWrongFileWasTemplate)
                    else:
                        OpenMaya.MGlobal.displayError(kImportWrongFile % str(ex))
            except Exception as ex:
                # Trap anything else
                OpenMaya.MGlobal.displayError(kImportWrongContent % str(ex))

    def _exportRenderSettings(self):
        selectedFilepath = cmds.fileDialog2(caption=kExportRenderSettings, 
                                            fileFilter="*.json", dialogStyle=2)
        if selectedFilepath is not None and len(selectedFilepath[0]) > 0:
            renderSettingsData = renderSettings.encode()
            with open(selectedFilepath[0], "w") as file:
                json.dump(renderSettingsData, file, sort_keys=True)

                                            
    def _importRenderSettings(self):
        selectedFilePath = cmds.fileDialog2(caption=kImportRenderSettings,
                                            fileFilter="*.json", fileMode=1, dialogStyle=2)
        if selectedFilePath is not None and len(selectedFilePath[0]) > 0:
            with open(selectedFilePath[0], "r") as file:
                renderSettingsData = json.load(file)
                renderSettings.decode(renderSettingsData)
                
    def _exportAOVs(self):
        _exportAOVs()

    def _importAOVs(self):
        selectedFilePath = cmds.fileDialog2(caption=kImportAOVs,
                                            optionsUICreate="importAOVsOptionsUIBuilder",
                                            fileFilter="*.json", fileMode=1, dialogStyle=2)
        if selectedFilePath is not None and len(selectedFilePath[0]) > 0:
            with open(selectedFilePath[0], "r") as file:
                aovData = json.load(file)
                aovs.decode(aovData, importExportUI.ImportAOVsUI.importType)


class RenderSetupWindow(MayaQWidgetDockableMixin, QWidget):
    """
    This class implements the dockable render setup window. 
    """

    # Constants
    # MAYA-66674: Make default size a user preference
    width = (cmds.optionVar(query='workspacesWidePanelInitialWidth')) * 0.75
    STARTING_SIZE = QSize(width, 600)
    PREFERRED_SIZE = QSize(width, 420)
    MINIMUM_SIZE = QSize((width * 0.95), 220)

    def __init__(self):
        # The class MayaQWidgetDockableMixin retrieves the right parent (i.e. Maya Main Window)
        super(RenderSetupWindow, self).__init__(parent=None)
        self.preferredSize = self.PREFERRED_SIZE

        self.setWindowTitle(kRenderSetup)
        self.resize(utils.dpiScale(self.STARTING_SIZE))

        # create a frame that other windows can dock into.
        self.dockingFrame = QMainWindow(self)
        self.dockingFrame.layout().setContentsMargins(0,0,0,0)
        self.dockingFrame.setWindowFlags(Qt.Widget)
        self.dockingFrame.setDockOptions(QMainWindow.AnimatedDocks)

        self.centralWidget = RenderSetupCentralWidget(self)
        self.centralWidget.layout().setContentsMargins(0,0,0,0)
        self.dockingFrame.setCentralWidget(self.centralWidget)

        # Adds the tree view to the window's layouts
        # the renderSetupView is set to be stretchy, while the other widgets are not
        layout = QVBoxLayout(self)
        layout.addWidget(self.dockingFrame, 0)
        self.setLayout(layout)
        
        errorAndWarningDeferrer.instance().displayErrorsAndWarnings()

    def setSizeHint(self, size):
        self.preferredSize = size

    def sizeHint(self):
        return self.preferredSize

    def minimumSizeHint(self):
        return self.MINIMUM_SIZE

    def dispose(self):
        self.centralWidget.dispose()

    def show(self, *args, **kwargs):
        # Override MayaQWidgetDockableMixin.show() method
        # to resolve menu parenting issues for templates
        # MAYA-73418
        self.centralWidget.renderSetupView._clearTemplates()
        super(RenderSetupWindow, self).show(*args, **kwargs)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
