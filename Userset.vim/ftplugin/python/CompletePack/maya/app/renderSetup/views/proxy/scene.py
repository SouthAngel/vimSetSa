import maya
maya.utils.loadStringResourcesForModule(__name__)

from PySide2.QtCore import Qt, QSize
from PySide2.QtGui import QColor, QGuiApplication, QStandardItem, QStandardItemModel
from PySide2.QtWidgets import QApplication

import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya

import maya.app.renderSetup.common.utils as commonUtils

import maya.app.renderSetup.model.renderSetup as renderSetupModel
import maya.app.renderSetup.model.plug as plug
import maya.app.renderSetup.model.rendererCallbacks as rendererCallbacks

import maya.app.renderSetup.views.pySide.standardItem as standardItem
import maya.app.renderSetup.views.utils as utils
import maya.app.renderSetup.views.lightEditor.editor as lightEditor

SCENE_TYPE_IDX                          = 0
SCENE_CATEGORY_TYPE_IDX                 = 1
SCENE_CATEGORY_RENDER_SETTINGS_TYPE_IDX = 2
SCENE_CATEGORY_CAMERAS_TYPE_IDX         = 3
SCENE_CATEGORY_LIGHTS_TYPE_IDX          = 4
SCENE_CATEGORY_AOVS_TYPE_IDX            = 5
SCENE_CATEGORY_SELECTION_SETS_TYPE_IDX  = 6
# The following should always be the last one
MAX_TYPE_IDX = 8

SCENE_TYPE                          = QStandardItem.UserType + SCENE_TYPE_IDX
SCENE_CATEGORY_TYPE                 = QStandardItem.UserType + SCENE_CATEGORY_TYPE_IDX
SCENE_CATEGORY_RENDER_SETTINGS_TYPE = QStandardItem.UserType + SCENE_CATEGORY_RENDER_SETTINGS_TYPE_IDX
SCENE_CATEGORY_CAMERAS_TYPE         = QStandardItem.UserType + SCENE_CATEGORY_CAMERAS_TYPE_IDX
SCENE_CATEGORY_LIGHTS_TYPE          = QStandardItem.UserType + SCENE_CATEGORY_LIGHTS_TYPE_IDX
SCENE_CATEGORY_AOVS_TYPE            = QStandardItem.UserType + SCENE_CATEGORY_AOVS_TYPE_IDX
SCENE_CATEGORY_SELECTION_SETS_TYPE  = QStandardItem.UserType + SCENE_CATEGORY_SELECTION_SETS_TYPE_IDX

# All needed roles
# Enum value 0 removed.
NODE_ACCEPTS_DRAG      = Qt.UserRole + 1
NODE_VISIBLE           = Qt.UserRole + 2
NODE_START_FRAME       = Qt.UserRole + 3
NODE_END_FRAME         = Qt.UserRole + 4
NODE_FRAME_ANIMATION   = Qt.UserRole + 5
NODE_RENDERABLE        = Qt.UserRole + 6
NODE_ACTIVE_FRAME      = Qt.UserRole + 7

SCENE_STR           = maya.stringTable['y_scene.kScene' ]
RENDER_SETTINGS_STR = maya.stringTable['y_scene.kRenderSettings' ]
CAMERAS_STR         = maya.stringTable['y_scene.kCameras' ]
LIGHTS_STR          = maya.stringTable['y_scene.kLights' ]
AOVS_STR            = maya.stringTable['y_scene.kAOVs' ]
SELECTION_SETS_STR  = maya.stringTable['y_scene.kSelectionSets' ]

ROW_HEIGHT = 30

EXPAND_COLLAPSE_ACTION     = maya.stringTable['y_scene.kExpandCollapseAction' ]
SET_VISIBILITY_ACTION      = maya.stringTable['y_scene.kSetVisibilityAction' ]
SET_RENDERABLE_ACTION      = maya.stringTable['y_scene.kSetRenderableAction' ]
PRESET_MENU                = maya.stringTable['y_scene.kPresetMenu' ]
AOVS_MENU                  = maya.stringTable['y_scene.kAOVsMenu' ]
EXPORT_CURRENT_ACTION      = maya.stringTable['y_scene.kExportCurrentAction' ]
DEFAULT_PRESET_ACTION      = maya.stringTable['y_scene.kDefaultPresetAction' ]
GLOBAL_PRESETS_ACTION      = maya.stringTable['y_scene.kGlobalPresetAction' ]
USER_PRESETS_ACTION        = maya.stringTable['y_scene.kUserPresetAction' ]

RS_DEFAULT_RENDER_GLOBALS = "defaultRenderGlobals"
RS_START_FRAME = "startFrame"
RS_END_FRAME = "endFrame"
RS_ANIMATION = "animation"
RS_INVALID_NODE_NAME = maya.stringTable['y_scene.kInvalidNodeName' ]

class ModelProxyItem(standardItem.StandardItem):

    def __init__(self, name):
        super(ModelProxyItem, self).__init__(name)
        self.name = name
        self._isActiveLayerObserver = False

    def data(self, role):
        if role == Qt.DisplayRole:
            return self.name
        elif role == Qt.EditRole:
            return self.name
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter
        elif role == Qt.TextColorRole:
            return QGuiApplication.palette().text().color()
        elif role == Qt.FontRole:
            return QApplication.font()
        elif role == Qt.SizeHintRole:
            return QSize(0, utils.dpiScale(ROW_HEIGHT))
        elif role == NODE_ACCEPTS_DRAG:
            return False
        elif role == NODE_ACTIVE_FRAME:
            return QColor(150, 150, 150)
        else:
            return super(ModelProxyItem, self).data(role)
        
    def setData(self, value, role):
        if role == Qt.EditRole:
            self.name = value
        else:
            super(ModelProxyItem, self).setData(value, role)

    def onClick(self, sceneView):
        pass

    def onDoubleClick(self, sceneView):
        pass

    def isActive(self):
        return False

    def getActionButton(self, column):
        return None

    def getActionButtonCount(self):
        return 0

    def addActiveLayerObserver(self):
        if not self._isActiveLayerObserver and renderSetupModel.hasInstance():
            renderSetupModel.instance().addActiveLayerObserver(self._onRenderLayerChangeCB)
            self._isActiveLayerObserver = True

    def removeActiveLayerObserver(self):
        if self._isActiveLayerObserver and renderSetupModel.hasInstance():
            renderSetupModel.instance().removeActiveLayerObserver(self._onRenderLayerChangeCB)
        self._isActiveLayerObserver = False

    def _onRenderLayerChangeCB(self):
        self.emitDataChanged()

class SceneProxyItem(ModelProxyItem):
    def __init__(self, name):
        super(SceneProxyItem, self).__init__(name)

    @property
    def _model(self):
        return renderSetupModel.instance().getDefaultRenderLayer() if renderSetupModel.hasInstance() else None

    def type(self):
        return SCENE_CATEGORY_TYPE
        
    def typeIdx(self):
        return SCENE_CATEGORY_TYPE_IDX
        
    def data(self, role):
        if role == Qt.BackgroundRole:
            return QColor(93, 93, 93)
        elif role == NODE_VISIBLE:
            return self._model is None or self._model.isVisible()
        elif role == NODE_RENDERABLE:
            return self._model is None or self._model.isRenderable()
        else:
            return super(SceneProxyItem, self).data(role)

    def setData(self, value, role):
        if self._model is None:
            super(SceneProxyItem, self).setData(value, role)
            return

        if role == NODE_VISIBLE and value:
            renderSetupModel.instance().switchToLayer(self._model)
        if role == NODE_RENDERABLE:
            self._model.setRenderable(value)
        else:
            super(SceneProxyItem, self).setData(value, role)

    def getActionButton(self, column):
        if column == 0:
            return SET_RENDERABLE_ACTION
        elif column == 1:
            return SET_VISIBILITY_ACTION
        return None

    def getActionButtonCount(self):
        return 2

class SceneItemProxyItem(ModelProxyItem):
    def __init__(self, name):
        super(SceneItemProxyItem, self).__init__(name)

    def data(self, role):
        if role == Qt.BackgroundRole:
            return QColor(82, 82, 82)
        else:
            return super(SceneItemProxyItem, self).data(role)

class SceneRenderSettingsProxyItem(SceneItemProxyItem):
    def __init__(self, name):
        super(SceneRenderSettingsProxyItem, self).__init__(name)
        self.endFrame = None
        self.animation = None
        self.startFrame = None
        self.callback = 0
        self.refresh(imposeRefresh=False)

    def dispose(self):
        self.reset()

    def defaultRenderGlobalsChanged(self, msg, mplug, otherMplug, clientData):
        nodeName, attrName = plug.Plug.getNames(mplug.name())
        if msg & OpenMaya.MNodeMessage.kAttributeSet:
            if nodeName.lstrip(':') != RS_DEFAULT_RENDER_GLOBALS:
                raise RuntimeError(RS_INVALID_NODE_NAME % mplug.name())
            if attrName == RS_START_FRAME:
                self.startFrame = mplug.asMTime().value
                self.emitDataChanged()
            elif attrName == RS_END_FRAME:
                self.endFrame = mplug.asMTime().value
                self.emitDataChanged()
            elif attrName == RS_ANIMATION:
                self.animation = mplug.asBool()
                self.emitDataChanged()

    def type(self):
        return SCENE_CATEGORY_RENDER_SETTINGS_TYPE
        
    def typeIdx(self):
        return SCENE_CATEGORY_RENDER_SETTINGS_TYPE_IDX
        
    def data(self, role):
        if role == NODE_ACCEPTS_DRAG:
            return True
        elif role == NODE_START_FRAME:
            return self.startFrame
        elif role == NODE_END_FRAME:
            return self.endFrame
        elif role == NODE_FRAME_ANIMATION:
            return self.animation
        else:
            return super(SceneRenderSettingsProxyItem, self).data(role)

    def getActionButton(self, column):
        if column == 0:
            return PRESET_MENU
        return None

    def getActionButtonCount(self):
        return 1

    def onDoubleClick(self, sceneView):
        import maya.mel as mel
        mel.eval('unifiedRenderGlobalsWindow')

    def isActive(self):
        return renderSetupModel.hasInstance() and \
               renderSetupModel.instance().getDefaultRenderLayer().isVisible() and \
               cmds.window('unifiedRenderGlobalsWindow', exists=True) and \
               cmds.window('unifiedRenderGlobalsWindow', query=True, visible=True)

    def refresh(self, imposeRefresh):
        node            = commonUtils.nameToNode(RS_DEFAULT_RENDER_GLOBALS)
        self.startFrame = commonUtils.findPlug(node, RS_START_FRAME).asMTime().value
        self.endFrame   = commonUtils.findPlug(node, RS_END_FRAME).asMTime().value
        self.animation  = commonUtils.findPlug(node, RS_ANIMATION).asBool()

        if self.callback is 0:
            self.callback = OpenMaya.MNodeMessage.addAttributeChangedCallback(node, self.defaultRenderGlobalsChanged, None)
        if imposeRefresh:
            self.emitDataChanged()

    def reset(self):
        if self.callback is not 0:
            OpenMaya.MNodeMessage.removeCallback(self.callback)
            self.callback = 0
            
class SceneCamerasProxyItem(SceneItemProxyItem):
    def __init__(self, name):
        super(SceneCamerasProxyItem, self).__init__(name)

    def type(self):
        return SCENE_CATEGORY_CAMERAS_TYPE
        
    def typeIdx(self):
        return SCENE_CATEGORY_CAMERAS_TYPE_IDX
        
    def data(self, role):
        if role == NODE_ACCEPTS_DRAG:
            return True
        else:
            return super(SceneCamerasProxyItem, self).data(role)

class SceneLightProxyItem(SceneItemProxyItem):
    def __init__(self, name):
        super(SceneLightProxyItem, self).__init__(name)
        lightEditor.theLightEditorUI.visibilityChanged.connect(self._redraw)

    def type(self):
        return SCENE_CATEGORY_LIGHTS_TYPE
        
    def typeIdx(self):
        return SCENE_CATEGORY_LIGHTS_TYPE_IDX
        
    def data(self, role):
        if role == NODE_ACCEPTS_DRAG:
            return True
        else:
            return super(SceneLightProxyItem, self).data(role)

    def _redraw(self):
        self.emitDataChanged()

    def isActive(self):
        return lightEditor.theLightEditorUI.isVisible() and lightEditor.theLightEditorUI.currentRenderLayer() == None

    def onDoubleClick(self, sceneView):
        lightEditor.theLightEditorUI.openEditor()

class SceneAovsProxyItem(SceneItemProxyItem):
    def __init__(self, name):
        super(SceneAovsProxyItem, self).__init__(name)

    def type(self):
        return SCENE_CATEGORY_AOVS_TYPE
        
    def typeIdx(self):
        return SCENE_CATEGORY_AOVS_TYPE_IDX

    def data(self, role):
        if role == NODE_ACCEPTS_DRAG:
            return True
        else:
            return super(SceneAovsProxyItem, self).data(role)
            
    def getActionButton(self, column):
        if column == 0:
            return AOVS_MENU
        return None

    def getActionButtonCount(self):
        return 1

    def onDoubleClick(self, sceneView):
        aovCallbacks = rendererCallbacks.getCallbacks(rendererCallbacks.CALLBACKS_TYPE_AOVS)
        if aovCallbacks:
            aovCallbacks.displayMenu()

class SceneSelectionSetsProxyItem(SceneItemProxyItem):
    def __init__(self, name):
        super(SceneSelectionSetsProxyItem, self).__init__(name)

    def type(self):
        return SCENE_CATEGORY_SELECTION_SETS_TYPE
        
    def typeIdx(self):
        return SCENE_CATEGORY_SELECTION_SETS_TYPE_IDX
        
    def data(self, role):
        return super(SceneSelectionSetsProxyItem, self).data(role)

class SceneProxy(QStandardItemModel):
    
    def __init__(self, parent=None):
        super(SceneProxy, self).__init__(parent=parent)
        self._buildHeader()
        self._buildTree()
        self.refreshModel()
        self.renderLayerManagerChangeCallback = 0

        self._cbIds = []
        cbArgs = [(OpenMaya.MSceneMessage.kBeforeNew,  self._beforeCb, 'before new'),
                  (OpenMaya.MSceneMessage.kBeforeOpen, self._beforeCb, 'before open'),
                  (OpenMaya.MSceneMessage.kAfterOpen,  self._afterCb,  'after open'),
                  (OpenMaya.MSceneMessage.kAfterNew,   self._afterCb,  'after new')]

        # MAYA-66710: Monitor Legacy Render Layers And Redraw
        # We need to monitor the legacy render layer changes as long as other parts of
        # the Maya UI can switch the active legacy render layer
        if self.renderLayerManagerChangeCallback is 0:
            self.renderLayerManagerChangeCallback = OpenMaya.MEventMessage.addEventCallback("renderLayerManagerChange", self._redraw)

        for (msg, cb, data) in cbArgs:
            self._cbIds.append(
                OpenMaya.MSceneMessage.addCallback(msg, cb, data))

    def _redraw(self, *args, **kwargs):
        self.layoutChanged.emit()

    def _beforeCb(self, data):
        self.renderSettingsProxyItem.reset()

    def _afterCb(self, data):
        self.renderSettingsProxyItem.refresh(imposeRefresh=True)

    def dispose(self):
        # MAYA-66710: Monitor Legacy Render Layers And Redraw
        # We need to monitor the legacy render layer changes as long as other parts of
        # the Maya UI can switch the active legacy render layer
        if self.renderLayerManagerChangeCallback:
            OpenMaya.MEventMessage.removeCallback(self.renderLayerManagerChangeCallback)
            self.renderLayerManagerChangeCallback = 0

        OpenMaya.MSceneMessage.removeCallbacks(self._cbIds)
        self._cbIds = []
        self.renderSettingsProxyItem.dispose()

        self.resetModel()

    def _buildHeader(self):
        header = QStandardItem(parent=self)
        header.setText("Scene Root")
        self.setHorizontalHeaderItem(0, header)

    def _buildTree(self):
        self.sceneProxyItem = SceneProxyItem(SCENE_STR)
        self.appendRow(self.sceneProxyItem)
        self.renderSettingsProxyItem = SceneRenderSettingsProxyItem(RENDER_SETTINGS_STR)
        self.sceneProxyItem.appendRow(self.renderSettingsProxyItem)
        self.sceneProxyItem.appendRow(SceneAovsProxyItem(AOVS_STR))
        self.lightsProxyItem = SceneLightProxyItem(LIGHTS_STR)
        self.sceneProxyItem.appendRow(self.lightsProxyItem)
        # Cameras , selection sets, and AOVs are not implemented for R2016.5 so hiding for now
        #self.sceneProxyItem.appendRow(SceneCamerasProxyItem(CAMERAS_STR))
        #self.sceneProxyItem.appendRow(SceneSelectionSetsProxyItem(SELECTION_SETS_STR))

    def type(self):
        return SCENE_TYPE

    def typeIdx(self):
        return SCENE_TYPE_IDX

    def flags(self, index):
        return Qt.ItemIsEnabled

    def refreshModel(self):
        self.sceneProxyItem.addActiveLayerObserver()
        self.renderSettingsProxyItem.addActiveLayerObserver()
        self.lightsProxyItem.addActiveLayerObserver()

    def resetModel(self):
        self.sceneProxyItem.removeActiveLayerObserver()
        self.renderSettingsProxyItem.removeActiveLayerObserver()
        self.lightsProxyItem.removeActiveLayerObserver()
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
