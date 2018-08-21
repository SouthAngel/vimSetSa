"""
    This file contains all the classes which implement the Qt Model needed to benefit from the
    Model/View design from Qt.
    
    The design intent is that these classes only be used to implement Qt views.
    They should be used as proxies to the underlying render setup data model
    objects only by Qt views code, and in such cases only with as little code
    as is required to interface with Qt.

    All other uses, by any other code, should use the render setup data
    model interface directly.  It already provides an encapsulation of the
    underlying Maya objects, as well as observation and notification
    capability.  There is no need to duplicate render setup data model
    interfaces and services in Qt model interfaces and services: this
    is a maintenance burden, introduces the possibility of error, and
    requires additional testing, for no gain.  Similarly, Qt model code
    should not perform any render setup data model computation or abstraction;
    such services must be implemented in the render setup data model layer.
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


from PySide2.QtCore import *
from PySide2.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QStandardItem, QStandardItemModel
from PySide2.QtWidgets import QApplication

import json
import os
from functools import partial
import weakref

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as OpenMaya

import maya.app.renderSetup.views.utils as utils

import maya.app.renderSetup.views.pySide.standardItem as standardItem

import maya.app.renderSetup.views.proxy.renderSetupRoles as renderSetupRoles
from maya.app.renderSetup.views.proxy.renderSetupProxyStrings import *
import maya.app.renderSetup.views.proxy.proxyFactory as proxyFactory

import maya.app.renderSetup.model.renderSetup as renderSetupModel
import maya.app.renderSetup.model.override as overrideModel
import maya.app.renderSetup.model.collection as collectionModel
import maya.app.renderSetup.model.renderLayer as renderLayerModel
import maya.app.renderSetup.model.undo as undo
import maya.app.renderSetup.model.jsonTranslatorUtils as jsonTranslatorUtils
import maya.app.renderSetup.model.renderSetupPreferences as userPrefs
import maya.app.renderSetup.model.typeIDs as typeIDs
import maya.app.renderSetup.model.plug as plug
import maya.app.renderSetup.model.renderSetupPrivate as renderSetupPrivate
import maya.app.renderSetup.model.nodeList as nodeList
import maya.app.renderSetup.model.clipboardData as clipboardData
import maya.app.renderSetup.model.overrideUtils as overrideUtils
import maya.app.renderSetup.model.rendererCallbacks as rendererCallbacks

import maya.app.renderSetup.common.guard as guard
import maya.app.renderSetup.views.lightEditor.editor as lightEditor



RENDER_SETUP_TYPE_IDX            = 0
RENDER_LAYER_TYPE_IDX            = 1
COLLECTION_TYPE_IDX              = 2
RENDER_OVERRIDE_TYPE_IDX         = 3
RENDER_SETTINGS_TYPE_IDX         = 4
CAMERAS_TYPE_IDX                 = 5
LIGHTS_TYPE_IDX                  = 6
AOVS_TYPE_IDX                    = 7
LIGHTS_CHILD_COLLECTION_TYPE_IDX = 8
AOVS_CHILD_COLLECTION_TYPE_IDX   = 9
# The following should always be the last one
MAX_TYPE_IDX                     = 10


RENDER_SETUP_TYPE           = QStandardItem.UserType + RENDER_SETUP_TYPE_IDX
RENDER_LAYER_TYPE           = QStandardItem.UserType + RENDER_LAYER_TYPE_IDX
COLLECTION_TYPE             = QStandardItem.UserType + COLLECTION_TYPE_IDX
RENDER_OVERRIDE_TYPE        = QStandardItem.UserType + RENDER_OVERRIDE_TYPE_IDX
RENDER_SETTINGS_TYPE        = QStandardItem.UserType + RENDER_SETTINGS_TYPE_IDX
CAMERAS_TYPE                = QStandardItem.UserType + CAMERAS_TYPE_IDX
LIGHTS_TYPE                 = QStandardItem.UserType + LIGHTS_TYPE_IDX
AOVS_TYPE                   = QStandardItem.UserType + AOVS_TYPE_IDX
LIGHTS_CHILD_COLLECTION_TYPE= QStandardItem.UserType + LIGHTS_CHILD_COLLECTION_TYPE_IDX
AOVS_CHILD_COLLECTION_TYPE  = QStandardItem.UserType + AOVS_CHILD_COLLECTION_TYPE_IDX

RENDER_SETTINGS_STR = kRenderSettings
CAMERAS_STR         = kCameras
LIGHTS_STR          = kLights
AOVS_STR            = kAOVs

RENDER_SETUP_MIME_TYPE = "application/renderSetup"

CREATE_COLLECTION_ACTION = kCreateCollectionAction
SET_VISIBILITY_ACTION = kSetVisibilityAction
SET_RENDERABLE_ACTION = kSetRenderableAction
CREATE_ABSOLUTE_OVERRIDE_ACTION = kCreateAbsoluteOverrideAction
CREATE_RELATIVE_OVERRIDE_ACTION = kCreateRelativeOverrideAction
CREATE_CONNECTION_OVERRIDE_ACTION = kCreateConnectionOverrideAction
CREATE_SHADER_OVERRIDE_ACTION = kCreateShaderOverrideAction
CREATE_MATERIAL_OVERRIDE_ACTION = kCreateMaterialOverrideAction
SET_ENABLED_ACTION = kSetEnabledAction
EXPAND_COLLAPSE_ACTION = kExpandCollapseAction
SET_ISOLATE_SELECTED_ACTION = kSetIsolateSelectedAction
RENAME_ACTION = kRenameAction
DELETE_ACTION = kDeleteAction
FILTER_MENU = kFiltersMenu
ALLFILTER_ACTION = kFilterAll
SHAPESFILTER_ACTION = kFilterGeometry
CAMERASFILTER_ACTION = kFilterCameras
LIGHTSFILTER_ACTION = kFilterLights
SHADERSFILTER_ACTION = kFilterShaders
CUSTOMFILTER_ACTION = kFilterCustom
NEWFILTER_ACTION = kNewFilter
TRANSFORMSFILTER_ACTION = kFilterTransforms
SETSFILTER_ACTION = kFilterSets
TM_SHAPESFILTER_ACTION = kFilterTransformsAndShapes
TM_SHAPES_SHADERSFILTER_ACTION = kFilterTransformsShapesShaders
SET_LOCAL_RENDER_ACTION = kSetLocalRender

PROXY_OPAQUE_DATA = "ProxyOpaqueData"

PARENT_TYPE_NAME = "parentTypeName"


# Returns the UI proxy associated with the given data model object. Note that
# the proxy opaque data is a weakref, thus the () used to access the value.
def getProxy(dataModel):
    return None if dataModel.getOpaqueData(PROXY_OPAQUE_DATA) \
        is None else dataModel.getOpaqueData(PROXY_OPAQUE_DATA)()

class DataModelListObserver(object):
    """Mixin class for proxy items so they can observe their underlying
    data model list."""

    # As per
    # 
    # https://rhettinger.wordpress.com/2011/05/26/super-considered-super/
    #
    # the signature of __init__() callee methods needs to match the caller.
    # We therefore use the most generic parameter list to accomodate the
    # needs of any other base class in the list of base classes.
    #
    def __init__(self, *args, **kwargs):
        super(DataModelListObserver, self).__init__(*args, **kwargs)
        self._hasObserver = False

        # Prevent self-notification when adding a list item to the data model.
        self._ignoreListItemAdded = False

    def ignoreListItemAdded(self):
        return self._ignoreListItemAdded

    def addListObserver(self, model):
        model.addListObserver(self)

    def removeListObserver(self, model):
        model.removeListObserver(self)

    def listItemAdded(self, listItem):
        """React to list item addition to the data model.

        If a list item is added to the data model, we create a
        list item proxy and insert it at the proper position."""

        # If we're adding a list item to the data model in this class and
        # handling the UI model addition elsewhere, early out.
        if self.ignoreListItemAdded():
            return

        # Unfortunately, trying to re-use the proxy in the data model
        # object (if one already exists) fails at first draw with
        # 
        # AttributeError: 'PySide.QtGui.QStandardItem' object has no attribute 'depth'
        #
        # The present module never creates QStandardItem objects, rather
        # standardItem.StandardItem objects, so this error is unexpected.
        # Pending further investigation, unconditionally re-create the
        # proxy.  PPT, 23-Oct-2015.
        proxy = self.createListItemProxy(listItem)

        # Get the data model listItem's next item in the data model list.
        # We iterate over our existing items and insert before that one.
        # If the next item is None, means the added list item is last in the
        # list, so we append.
        next = listItem.getNext()
        if next is None:
            self.appendRow(proxy)
        else:
            # Use single-item list because of
            # https://bugreports.qt.io/browse/PYSIDE-237
            self.insertRow(getProxy(next).index().row(), [proxy])

    def listItemRemoved(self, listItem):
        """React to list item removal from the data model.

        If a list item is removed from the data model, we remove the row
        corresponding to its list item proxy."""

        proxy = getProxy(listItem)
        proxy.dispose() # As the life scope is undefined, dispose by default
        self.removeRow(proxy.index().row())

    def addActiveLayerObserver(self):
        if not self._hasObserver and renderSetupModel.hasInstance():
            renderSetupModel.instance().addActiveLayerObserver(self._onRenderLayerChangeCB)
            self._hasObserver = True

    def removeActiveLayerObserver(self):
        if self._hasObserver and renderSetupModel.hasInstance():
            renderSetupModel.instance().removeActiveLayerObserver(self._onRenderLayerChangeCB)
        self._hasObserver = False

    def _onRenderLayerChangeCB(self):
        self.emitDataChanged()


class Template(object):
    ''' Base class for all the proxy classes to offer the template file import '''

    def findAllTemplateFiles(self, templateDirectory):
        """ Find the list of all template files """
        for root, dirs, files in os.walk(templateDirectory):
            for file in files:
                if file.split('.')[-1] == userPrefs.getFileExtension():
                    yield os.path.join(root, file)

    def acceptableDictionaries(self, templateDirectory):
        """ Find the list of template files applicable to a specific proxy """
        for filepath in self.findAllTemplateFiles(templateDirectory):
            with open(filepath, "r") as file:
                # Catch all kind of errors but still continue to search for
                #  the appropriate template files. The directory could contain
                #  faulty json files and/or files which are not render setup template files.
                try:
                    dic = json.load(file)
                    objList = dic if isinstance(dic, list) else [dic]
                    if self.isAcceptableTemplate(objList):
                        # Only preserve a partial filepath (i.e. remove the user template directory part)
                        partialFilepath = os.path.relpath(filepath, templateDirectory)
                        yield (objList, partialFilepath)
                except GeneratorExit:
                    # If the generator is destroyed at higher level (return from a for loop for example)
                    # the method close() from the generator is called and raises GeneratorExit
                    # We need to exit if this exception is raised because the generator is destroyed
                    # (Cf TemplateThreadWorker in views.renderSetupWindow)
                    return
                except:
                    # Ignore errors because there is no need to display unexpected json files
                    pass

    def templateActions(self, templateDirectory):
        """ Build the list of all possible template actions """
        for (objList, filepath) in self.acceptableDictionaries(templateDirectory):
            # The name of the action is the filename without the extension
            #    be carefull some file names and some file paths could 
            #    contain the '.' character
            fileExtension = '.' + filepath.split('.')[-1]
            # Note: Arbitrary use the notes of the first selected object for the tooltip
            yield (filepath.split(fileExtension)[0], jsonTranslatorUtils.getObjectNotes(objList), partial(self.importTemplate, objList))


# Because of MAYA-60799, QStandardItem must appear last in the list of
# base classes.
class ModelProxyItem(Template, standardItem.StandardItem):

    def __init__(self, model):
        super(ModelProxyItem, self).__init__(model.name())
        self._model = model

        # Trying to add emitDataChanged as the bound method fails with
        # "'builtin_function_or_method' object has no attribute 'im_self'".
        # Most likely Python extension objects have this characteristic.
        # Use an intermediate Python method as a workaround.
        self._model.addItemObserver(self.modelChanged)
        self._modelDirty = False

        self._model.addOpaqueData(PROXY_OPAQUE_DATA, weakref.ref(self))

    def aboutToDelete(self):
        """Cleanup method to be called immediately before the object is deleted."""
        self._model.removeItemObserver(self.modelChanged)
        self._model.removeOpaqueData(PROXY_OPAQUE_DATA)

        for idx in range(self.rowCount()):
            self.child(idx).dispose()

    # Obsolete interface.
    dispose = aboutToDelete

    @property
    def model(self):
        """Get the data model object for this proxy item."""
        return self._model

    # The next function (isModelDirty) is a workaround.
    # It should not be necessary but it is currently because we set tooltips in the treeview
    # and that triggers emitDataChanged which triggers the rebuild or repopulate of the property editor.
    # The proper fix will be to use columns in the treeview where each column has its own static tooltip
    # and the tooltips should no longer be dynamically set by the delegate (views/renderSetupDelegate.py)
    # depending on the lastHitAction
    def isModelDirty(self):
        return self._modelDirty

    @guard.member('_modelDirty', True)
    def modelChanged(self, *posArgs, **kwArgs):
        self.emitDataChanged()

    def isActive(self):
        return False
    
    def getWarning(self):
        for i in range(0, self.rowCount()):
            child = self.child(i, 0)
            warning = child.getWarning()
            if warning:
                return maya.stringTable['y_renderSetup.kChildHasWarning' ] % child.data(Qt.EditRole)
        return None
    
    def data(self, role):
        if role == Qt.DisplayRole:
            return self._model.name()
        elif role == Qt.EditRole:
            return self._model.name()
        elif role == Qt.TextColorRole:
            return QGuiApplication.palette().text().color()
        elif role == Qt.FontRole:
            font = QApplication.font()
            if self._model.getImportedStatus():
                font.setStyle(QFont.StyleItalic)
                font.setWeight(QFont.Bold)
            return font
        elif role == Qt.SizeHintRole:
            return QSize(0, utils.dpiScale(30))
        elif role == renderSetupRoles.NODE_FLAGS:
            return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled
        elif role == renderSetupRoles.NODE_NOTES:
            return self._model.getNotes()
        elif role == renderSetupRoles.NODE_VALID:
            return True
        elif role == renderSetupRoles.NODE_REBUILD_UI_WHEN_CHANGED:
            return False
        elif role == renderSetupRoles.NODE_EDITABLE:
            return True
        elif role == renderSetupRoles.NODE_SHOULD_DISPLAY_NAME:
            return True
        elif role == renderSetupRoles.NODE_NEEDS_UPDATE:
            return False
        elif role == renderSetupRoles.NODE_WARNING:
            return self.getWarning()
        else:
            return super(ModelProxyItem, self).data(role)

    def setData(self, value, role):
        if role == Qt.EditRole:
            if self._model.name() != value:
                # No need to call emitDataChanged(), data model observation
                # will do this for us (see modelChanged()).
                self._model.setName(value)
        else:
            super(ModelProxyItem, self).setData(value, role)

    def equalsDragType(self, dragType):
        return False
        
    def handleDragMoveEvent(self, event):
        event.ignore()

    def handleDropEvent(self, event, sceneView):
        pass

    def onClick(self, view):
        pass

    def onDoubleClick(self, view):
        pass

    def findProxyItem(self, name):
        if self.data(Qt.EditRole) == name:
            return self
        else:
            count = self.rowCount()
            for i in range(0, count):
                item = self.child(i, 0)
                result = item.findProxyItem(name)
                if result:
                    return result    
            return None

    def headingWidth(self, heading):
        fm = QFontMetrics(self.data(Qt.FontRole))
        return fm.width(heading)

    def getActionButton(self, column):
        return None

    def getActionButtonCount(self):
        return 0

    def isDropAllowed(self, destinationModel):
        return destinationModel.isAcceptableChild(self._model)

    @undo.chunk('Paste')
    def paste(self, jsonStr):
        objList = json.loads(jsonStr)
        typeName = jsonTranslatorUtils.getTypeNameFromDictionary(objList[0])
        parentTypeName = objList[0][PARENT_TYPE_NAME]
        data = clipboardData.ClipboardData(typeName, parentTypeName)
        if self._model.isAcceptableChild(data):
            self._model._decodeChildren(objList, renderSetupModel.DECODE_AND_RENAME, None)

def _createControlForAttribute(attr, attrLabel, connectable=True):
    """ Create a UI control for the given attribute, 
    matching its type and considering if it's connectable."""

    plg = plug.Plug(attr)
    attrLabel = mel.eval('interToUI(\"%s\")' % attrLabel)
    hideButton = not (connectable and plg.isConnectable)
    ctrl = None

    # Vectors must be handled explicitly with attrFieldGrp. If the more general attrControlGrp is used
    # no map button is created. This is a bug with the attrControlGrp command and vector types.
    if plg.isVector:
        ctrl = cmds.attrFieldGrp(attribute=attr, label=attrLabel, forceAddMapButton=not hideButton, hideMapButton=hideButton, preventOverride=True, precision=3)

    # Bools must also be handled explicitly. The general command attrControlGrp gives error messages
    # when creating a bool control.
    elif plg.type is plug.Plug.kBool:
        ctrl = cmds.checkBoxGrp(label=attrLabel, numberOfCheckBoxes=1, preventOverride=True)
        cmds.connectControl(ctrl, attr, index=2)
        
    # Floats must be handled separately to set their precision
    elif plg.type is plug.Plug.kFloat or plg.type is plug.Plug.kDouble:
        ctrl = cmds.attrFieldSliderGrp(attribute=attr, label=attrLabel, forceAddMapButton=not hideButton, hideMapButton=hideButton, preventOverride=True, precision=3)

    # Strings must also be handled explicitly. The general command attrControlGrp gives error messages
    # when creating a string control.
    elif plg.type is plug.Plug.kString:
        ctrl = cmds.textFieldGrp(label=attrLabel, preventOverride=True)
        cmds.connectControl(ctrl, attr, index=2)

    # Handled all other types with attrControlGrp, if supported
    elif cmds.attrControlGrp(query=True, handlesAttribute=attr):
        ctrl = cmds.attrControlGrp(attribute=attr, label=attrLabel, hideMapButton=hideButton, preventOverride=True)

    # If no control was created above, fallback to a navigation control group,
    # so that connections can be made on the attribute.
    if ctrl is None:
        ctrl = cmds.attrNavigationControlGrp(label=attrLabel, attribute=attr,
                createNew="connectionOverrideNewNode " + attr, connectToExisting="connectionOverrideReplaceNode " + attr)

    return ctrl

class OverrideProxy(ModelProxyItem):
    """ The class provides the Qt model counterpart for the Override """
    """ It should forward any Override property request to the model layer,
        and handle any UI specific data """
        
    def __init__(self, model):
        super(OverrideProxy, self).__init__(model)

    def type(self):
        return QStandardItem.UserType + self.typeIdx()
        
    def typeIdx(self):
        return RENDER_OVERRIDE_TYPE_IDX
        
    def genericTypeIdx(self):
        # Constant for all derived classes
        return RENDER_OVERRIDE_TYPE_IDX
        
    def _typeName(self):
        return mel.eval('interToUI(\"%s\")' % self._model.typeName()) \
                       if not isinstance(
                               self._model, overrideModel.ValueOverride) \
                       else kAbsoluteType \
                            if isinstance(
                                    self._model, overrideModel.AbsOverride) \
                            else kRelativeType
    
    def getWarning(self):
        return self._model.status()

    def data(self, role):
        if role == Qt.DisplayRole:
            return "%s:   %s" % (self._typeName(), self._model.name())
        elif role == renderSetupRoles.NODE_TYPE_STR:
            return "%s:" % (self._typeName())
        elif role == Qt.EditRole:
            return self._model.name()
        elif role == Qt.BackgroundRole:
            return QColor(71, 71, 71) if not self._model.isLocalRender() else QColor(67,79,70)
        elif role == Qt.ForegroundRole:
            return QColor(255, 255, 255) if self._model.isSelfEnabled() \
                else QColor(165, 165, 165)
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignRight | Qt.AlignVCenter
        elif role == renderSetupRoles.NODE_COLOR_BAR:
            return QColor(124, 194, 144)
        elif role == renderSetupRoles.NODE_PATH_NAME:
            item = self
            pathName = ""
            while item:
                pathName = item.data(Qt.EditRole) + "\\" + pathName
                item = item.parent()
            return pathName
        elif role == renderSetupRoles.NODE_ENABLED:
            return self._model.isEnabled()
        elif role == renderSetupRoles.NODE_SELF_ENABLED:
            return self._model.isSelfEnabled()
        elif role == renderSetupRoles.NODE_VALID:
            return self._model.isValid()
        elif role == renderSetupRoles.NODE_FLAGS:
            return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled
        elif role == renderSetupRoles.NODE_HEADING_WIDTH:
            typeName = mel.eval('interToUI(\"%s\")' % self._model.typeName())
            return self.headingWidth("%s:   " % (typeName))
        elif role == renderSetupRoles.NODE_REBUILD_UI_WHEN_CHANGED:
            return True
        else:
            return super(OverrideProxy, self).data(role)
            
    def setData(self, value, role):
        # No need to call self.emitDataChanged(), model observation will.
        if role == renderSetupRoles.NODE_SELF_ENABLED:
            self._model.setSelfEnabled(value)
        else:
            super(OverrideProxy, self).setData(value, role)
    
    def isUniqueOverride(self):
        return False
            
    def setLocalRender(self, value):
        self.model.setLocalRender(value)
    
    def isLocalRender(self):
        return self.model.isLocalRender()

    def acceptsDrops(self, attribute):
        plg = plug.Plug(attribute)
        if not plg.isOvrSupported():
            return False
        overrideType = plg.overrideType(typeIDs.absOverride if isinstance(self._model, overrideModel.AbsOverride) else typeIDs.relOverride)
        return self._model.typeId()==overrideType

    def delete(self):
        # listItemRemoved() data model list observation will take care of
        # removing ourself from our UI parent.
        overrideModel.delete(self._model)

    def supportsAction(self, action, numIndexes):
        return action in [SET_ENABLED_ACTION, DELETE_ACTION, SET_LOCAL_RENDER_ACTION] or \
            (numIndexes == 1 and action in [ RENAME_ACTION ])

    def getActionButton(self, column):
        if column == 0:
            return SET_ENABLED_ACTION
        return None

    def getActionButtonCount(self):
        return 1

    def isAcceptableTemplate(self, objList):
        return False

    def finalizeOverrideCreation(self, plugName):
        if plugName is not None:
            self._model.finalize(plugName)
        return self._model.isValid()

class AbsOverrideProxy(OverrideProxy):
    def __init__(self, model):
        super(AbsOverrideProxy, self).__init__(model)

    def createAttributeUI(self, attribute):
        if not self.finalizeOverrideCreation(attribute):
            return None
        return _createControlForAttribute(self._model.attrValuePlugName(), self._model.attributeName(), connectable=True)

class RelOverrideProxy(OverrideProxy):
    def __init__(self, model):
        super(RelOverrideProxy, self).__init__(model)

    def createAttributeUI(self, attribute):
        if not self.finalizeOverrideCreation(attribute):
            return None
        multiplyDisplay = '%s: %s ' % (self._model.attributeName(), plug.Plug.getNames(self._model.multiplyPlugName())[1])
        offsetDisplay = '%s: %s ' % (self._model.attributeName(), plug.Plug.getNames(self._model.offsetPlugName())[1])
        return (_createControlForAttribute(self._model.multiplyPlugName(), multiplyDisplay, connectable=True),
                _createControlForAttribute(self._model.offsetPlugName(), offsetDisplay, connectable=True))

class UniqueOverrideProxy(object):
    def isUniqueOverride(self):
        return True
    
    def targetNodeName(self):
        return self._model.targetNodeName()

class AbsUniqueOverrideProxy(UniqueOverrideProxy, AbsOverrideProxy):
    def __init__(self, model):
        super(AbsUniqueOverrideProxy, self).__init__(model)

class RelUniqueOverrideProxy(UniqueOverrideProxy, RelOverrideProxy):
    def __init__(self, model):
        super(RelUniqueOverrideProxy, self).__init__(model)

class ConnectionOverrideProxy(OverrideProxy):

    def __init__(self, model):
        super(ConnectionOverrideProxy, self).__init__(model)

    def acceptsDrops(self, attribute):
        return True

    def createAttributeUI(self, attribute):
        if not self.finalizeOverrideCreation(attribute):
            # Check if finalize failed because there is no
            # value attribute created yet. If so we cannot
            # create a UI control, so return None
            if not self._model.isFinalized():
                return None

        attributeName = self._model.attributeName()
        valueAttr = self._model.attrValuePlugName()
        return _createControlForAttribute(valueAttr, attributeName) if valueAttr else None

class ShaderOverrideProxy(ConnectionOverrideProxy):

    def __init__(self, model):
        super(ShaderOverrideProxy, self).__init__(model)

    def acceptsDrops(self, attribute):
        return False

    def createAttributeUI(self, attribute):
        overrideAttr = self._model.attrValuePlugName()
        overrideCtrl = cmds.attrNavigationControlGrp(label="Override Shader", attribute=overrideAttr,
            createNew="connectionOverrideNewNode " + overrideAttr, connectToExisting="connectionOverrideReplaceNode " + overrideAttr)
        return overrideCtrl

class MaterialOverrideProxy(ConnectionOverrideProxy):

    def __init__(self, model):
        super(MaterialOverrideProxy, self).__init__(model)

    def acceptsDrops(self, attribute):
        return False

    def createAttributeUI(self, attribute):
        overrideAttr = self._model.attrValuePlugName()
        overrideCtrl = cmds.attrNavigationControlGrp(label="Override Material", attribute=overrideAttr,
            createNew="materialOverrideNewNode " + overrideAttr, connectToExisting="connectionOverrideReplaceNode " + overrideAttr)
        return overrideCtrl


# Because of MAYA-60799, PySide base classes must appear last in the list of
# base classes.
class BaseCollectionProxy(DataModelListObserver, ModelProxyItem):
    
    def __init__(self, model):
        super(BaseCollectionProxy, self).__init__(model)

        # Build first, then add ourselves as an override observer after,
        # otherwise we'll observe ourselves adding overrides to our list.
        self._build()

        self.addListObserver(self._model)

    def _build(self):
        # Load the current children
        for child in self._model.getChildren():
            self.appendRow(proxyFactory.create(child))

    def aboutToDelete(self):
        """Cleanup method to be called immediately before the object is deleted."""
        super(BaseCollectionProxy, self).aboutToDelete()
        self.removeListObserver(self._model)

    # Obsolete interface.
    dispose = aboutToDelete

    def type(self):
        return QStandardItem.UserType + self.typeIdx()

    def genericTypeIdx(self):
        # Constant for all derived classes
        return COLLECTION_TYPE_IDX

    def getWarning(self):
        warning = self.model.getSelector().status()
        if warning:
            return warning
        return super(BaseCollectionProxy, self).getWarning()

    def data(self, role):
        if role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter
        elif role == Qt.BackgroundRole:
            return QColor(82, 82, 82)
        elif role == Qt.ForegroundRole:
            return QColor(255, 255, 255) if self._model.isSelfEnabled() \
                else QColor(165, 165, 165)
        elif role == renderSetupRoles.NODE_ENABLED:
            return self._model.isEnabled()
        elif role == renderSetupRoles.NODE_SELF_ENABLED:
            return self._model.isSelfEnabled()
        elif role == renderSetupRoles.NODE_PATH_NAME:
            item = self
            pathName = ""
            while item:
                pathName = item.data(Qt.EditRole) + "\\" + pathName
                item = item.parent()
            return pathName
        elif role == renderSetupRoles.NODE_FLAGS:
            return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
        elif role == renderSetupRoles.NODE_HEADING_WIDTH:
            return self.headingWidth(self.typeName + ":   ")
        else:
            return super(BaseCollectionProxy, self).data(role)

    def setData(self, value, role):
        if role == renderSetupRoles.NODE_SELF_ENABLED:
            self._model.setSelfEnabled(value)
        elif role == renderSetupRoles.NODE_ISOLATE_SELECTED:
            self._model.setIsolateSelected(value)            
        else:
            super(BaseCollectionProxy, self).setData(value, role)
    
    def listItemAdded(self, listItem):
        super(BaseCollectionProxy, self).listItemAdded(listItem)

    def listItemRemoved(self, listItem):
        super(BaseCollectionProxy, self).listItemRemoved(listItem)

    def createOverride(self, overrideTypeId):
        ov = self._model.createOverride("", overrideTypeId)
        proxy = getProxy(ov)
        return proxy.index()

    @guard.member('_ignoreListItemAdded', True)
    def attachOverrideProxy(self, overrideProxy):
        # Override addition observation creates a proxy and inserts it
        # in the proper position.  If we've already done this work, we
        # turn off data model override addition observation while we attach.
        self._model.attachChild(overrideProxy.row(), overrideProxy._model)
        
    def delete(self):
        collectionModel.delete(self._model)

    def attachChild(self, override, pos):
        self.model.attachChild(pos, override)

    def createListItemProxy(self, override):
        return proxyFactory.create(override)

    def isAcceptableTemplate(self, objList):
        """ Only collections and overrides could be imported in a collection """
        typename = jsonTranslatorUtils.getTypeNameFromDictionary(objList[0])
        overrideTypenames = { o.kTypeName for o in overrideUtils.getAllOverrideClasses() }
        return typename in overrideTypenames

    @undo.chunk('Import a template render setup file')
    def importTemplate(self, objList):
        """ Import the collection template or override template in the current collection """
        self._model._decodeChildren(objList, renderSetupModel.DECODE_AND_MERGE, None)


class CollectionProxy(BaseCollectionProxy):

    # Value override creation menu item values.
    NO_OVERRIDE       = kNoOverride
    ABSOLUTE_OVERRIDE = kAbsolute
    RELATIVE_OVERRIDE = kRelative

    def __init__(self, model):
        super(CollectionProxy, self).__init__(model)

        self.typeName = mel.eval('interToUI(\"%s\")' % self._model.typeName())

        self._valueOverrideMode = CollectionProxy.ABSOLUTE_OVERRIDE

    def _getValueOverrideMode(self):
        """Drag and drop value override creation mode.

        Legal values are None (don't show drop zone), Absolute, and Relative."""

        # Because the collection property editor is always re-created, we
        # need to store the value override creation mode in the Qt model.
        # While a collection is selected (and thus shown in the property
        # editor), we must keep the UI value and this value in sync.
        return self._valueOverrideMode

    def _setValueOverrideMode(self, mode):
        self._valueOverrideMode = mode

    def typeIdx(self):
        return COLLECTION_TYPE_IDX

    def data(self, role):
        if role == Qt.DisplayRole:
            return "%s:   %s" % (self.typeName, self._model.name())
        if role == renderSetupRoles.NODE_TYPE_STR:
            return "%s:" % (self.typeName)
        elif role == Qt.EditRole:
            return self._model.name()
        elif role == renderSetupRoles.NODE_COLOR_BAR:
            return QColor(204,203,129)
        elif role == renderSetupRoles.NODE_ISOLATE_SELECTED:
            return self._model.isIsolateSelected()
        else:
            return super(CollectionProxy, self).data(role)

    def supportsAction(self, action, numIndexes):
        actions = set(
            [SET_ENABLED_ACTION, SET_ISOLATE_SELECTED_ACTION,
             FILTER_MENU, DELETE_ACTION])

        if numIndexes == 1:
            actions |= set(
                [CREATE_COLLECTION_ACTION,
                 CREATE_ABSOLUTE_OVERRIDE_ACTION,
                 CREATE_RELATIVE_OVERRIDE_ACTION,
                 CREATE_CONNECTION_OVERRIDE_ACTION, 
                 CREATE_SHADER_OVERRIDE_ACTION, 
                 CREATE_MATERIAL_OVERRIDE_ACTION, 
                 RENAME_ACTION])

        return action in actions

    def getActionButton(self, column):
        if column == 2:
            return FILTER_MENU
        elif column == 0:
            return SET_ENABLED_ACTION
        elif column == 1 and not isinstance(self.parent(), LightsProxy):
            return SET_ISOLATE_SELECTED_ACTION
        return None

    def getActionButtonCount(self):
        return 3

    def createCollection(self, collectionName, nodeType):
        collection = self._model.createCollection(collectionName)
        # Set the child collection's selector to be of the same type as
        # that of the parent.
        collection.setSelectorType(self._model.getSelector().kTypeName)
        proxy = getProxy(collection)
        return proxy.index()
        
    def isAcceptableTemplate(self, objList):
        """ Only collections and overrides could be imported in a collection """
        typename = jsonTranslatorUtils.getTypeNameFromDictionary(objList[0])
        overrideTypenames = { o.kTypeName for o in overrideUtils.getAllOverrideClasses() } | { collectionModel.Collection.kTypeName }
        return typename in overrideTypenames

class RenderSettingsCollectionProxy(BaseCollectionProxy):
    
    def __init__(self, model):
        super(RenderSettingsCollectionProxy, self).__init__(model)
        self.typeName = RENDER_SETTINGS_STR
        self.addActiveLayerObserver()

    def aboutToDelete(self):
        """Cleanup method to be called immediately before the object is deleted."""
        super(RenderSettingsCollectionProxy, self).aboutToDelete()
        self.removeActiveLayerObserver()

    # Obsolete interface.
    dispose = aboutToDelete

    def typeIdx(self):
        return RENDER_SETTINGS_TYPE_IDX

    def data(self, role):
        if role == Qt.DisplayRole:
            return self.typeName
        elif role == renderSetupRoles.NODE_TYPE_STR:
            return self.typeName
        elif role == renderSetupRoles.NODE_COLOR_BAR:
            return QColor(150, 150, 150)
        elif role == renderSetupRoles.NODE_EDITABLE:
            return False
        elif role == renderSetupRoles.NODE_SHOULD_DISPLAY_NAME:
            return False
        else:
            return super(RenderSettingsCollectionProxy, self).data(role)

    def supportsAction(self, action, numIndexes):
        return action in ([SET_ENABLED_ACTION, 
                           DELETE_ACTION] if numIndexes == 1 else
                          [SET_ENABLED_ACTION,
                           DELETE_ACTION])

    def onDoubleClick(self, view):
        mel.eval('unifiedRenderGlobalsWindow')

    def isActive(self):
        return renderSetupModel.hasInstance() and \
               renderSetupModel.instance().getVisibleRenderLayer() == self.parent().model and \
               cmds.window('unifiedRenderGlobalsWindow', exists=True) and \
               cmds.window('unifiedRenderGlobalsWindow', query=True, visible=True)

    def equalsDragType(self, dragType):
        return dragType == self.typeName

    def getActionButton(self, column):
        return SET_ENABLED_ACTION if column == 0 else None

    def getActionButtonCount(self):
        return 1

    def isAcceptableTemplate(self, objList):
        return False

# Can simplify this with a common base class
class AOVCollectionProxy(BaseCollectionProxy):
    
    def __init__(self, model):
        super(AOVCollectionProxy, self).__init__(model)
        self.typeName = AOVS_STR
        self.addActiveLayerObserver()

    def aboutToDelete(self):
        """Cleanup method to be called immediately before the object is deleted."""
        super(AOVCollectionProxy, self).aboutToDelete()
        self.removeActiveLayerObserver()

    # Obsolete interface.
    dispose = aboutToDelete

    def typeIdx(self):
        return AOVS_TYPE_IDX

    def data(self, role):
        if role == Qt.DisplayRole:
            return self.typeName
        elif role == renderSetupRoles.NODE_TYPE_STR:
            return self.typeName
        elif role == renderSetupRoles.NODE_COLOR_BAR:
            return QColor(150, 150, 150)
        elif role == renderSetupRoles.NODE_EDITABLE:
            return False
        elif role == renderSetupRoles.NODE_SHOULD_DISPLAY_NAME:
            return False
        else:
            return super(AOVCollectionProxy, self).data(role)

    def supportsAction(self, action, numIndexes):
        return action in ([SET_ENABLED_ACTION, 
                           DELETE_ACTION] if numIndexes == 1 else
                          [SET_ENABLED_ACTION,
                           DELETE_ACTION])

    def isActive(self):
        return renderSetupModel.hasInstance() and \
               renderSetupModel.instance().getVisibleRenderLayer() == self.parent().model and \
               cmds.window('unifiedRenderGlobalsWindow', exists=True) and \
               cmds.window('unifiedRenderGlobalsWindow', query=True, visible=True)

    def equalsDragType(self, dragType):
        return dragType == self.typeName

    def getActionButton(self, column):
        return SET_ENABLED_ACTION if column == 0 else None

    def getActionButtonCount(self):
        return 1

    def isAcceptableTemplate(self, objList):
        return False

    def onDoubleClick(self, view):
        aovCallbacks = rendererCallbacks.getCallbacks(rendererCallbacks.CALLBACKS_TYPE_AOVS)
        if aovCallbacks:
            aovCallbacks.displayMenu()

# Can simplify this with a common base class
class AOVChildCollectionProxy(BaseCollectionProxy):

    def __init__(self, model):
        super(AOVChildCollectionProxy, self).__init__(model)
        self.typeName = mel.eval('interToUI(\"%s\")' % self._model.typeName())
        self.addActiveLayerObserver()

    def aboutToDelete(self):
        """Cleanup method to be called immediately before the object is deleted."""
        super(AOVChildCollectionProxy, self).aboutToDelete()
        self.removeActiveLayerObserver()

    # Obsolete interface.
    dispose = aboutToDelete

    def typeIdx(self):
        return AOVS_CHILD_COLLECTION_TYPE_IDX

    def data(self, role):
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return self._model.name()
        elif role == renderSetupRoles.NODE_TYPE_STR:
            return "%s" % (self._model.name())
        elif role == renderSetupRoles.NODE_COLOR_BAR:
            return QColor(204,203,129)
        elif role == renderSetupRoles.NODE_SHOULD_DISPLAY_NAME:
            return False
        else:
            return super(AOVChildCollectionProxy, self).data(role)

    def supportsAction(self, action, numIndexes):
        return action in ([SET_ENABLED_ACTION, DELETE_ACTION])

    def getActionButton(self, column):
        return SET_ENABLED_ACTION if column == 0 else None

    def getActionButtonCount(self):
        return 1

    def isAcceptableTemplate(self, objList):
        return False

class LightsProxy(BaseCollectionProxy):

    def __init__(self, model):
        super(LightsProxy, self).__init__(model)
        self.typeName = LIGHTS_STR
        self.addActiveLayerObserver()

    def aboutToDelete(self):
        """Cleanup method to be called immediately before the object is deleted."""
        super(LightsProxy, self).aboutToDelete()
        self.removeActiveLayerObserver()

    # Obsolete interface.
    dispose = aboutToDelete

    def typeIdx(self):
        return LIGHTS_TYPE_IDX

    def data(self, role):
        if role == Qt.DisplayRole:
            return self.typeName
        elif role == renderSetupRoles.NODE_TYPE_STR:
            return self.typeName
        elif role == renderSetupRoles.NODE_COLOR_BAR:
            return QColor(150, 150, 150)
        elif role == renderSetupRoles.NODE_EDITABLE:
            return False
        elif role == renderSetupRoles.NODE_SHOULD_DISPLAY_NAME:
            return False
        else:
            return super(LightsProxy, self).data(role)

    def supportsAction(self, action, numIndexes):
        return action in ([SET_ENABLED_ACTION, 
                           DELETE_ACTION] if numIndexes == 1 else
                          [SET_ENABLED_ACTION,
                           DELETE_ACTION])

    def onDoubleClick(self, view):
        lightEditor.theLightEditorUI.openEditor(self._model.getRenderLayer())

    def isActive(self):
        return lightEditor.theLightEditorUI.currentRenderLayer() == self.parent().model

    def equalsDragType(self, dragType):
        return dragType == self.typeName

    def getActionButton(self, column):
        return SET_ENABLED_ACTION if column == 0 else None

    def getActionButtonCount(self):
        return 1

    def isAcceptableTemplate(self, objList):
        return False

class LightsChildCollectionProxy(BaseCollectionProxy):

    def __init__(self, model):
        super(LightsChildCollectionProxy, self).__init__(model)
        self.typeName = mel.eval('interToUI(\"%s\")' % self._model.typeName())
        self.addActiveLayerObserver()

    def aboutToDelete(self):
        """Cleanup method to be called immediately before the object is deleted."""
        super(LightsChildCollectionProxy, self).aboutToDelete()
        self.removeActiveLayerObserver()

    # Obsolete interface.
    dispose = aboutToDelete

    def typeIdx(self):
        return LIGHTS_CHILD_COLLECTION_TYPE_IDX

    def data(self, role):
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return self._model.name()
        elif role == renderSetupRoles.NODE_TYPE_STR:
            return "%s" % (self._model.name())
        elif role == renderSetupRoles.NODE_COLOR_BAR:
            return QColor(204,203,129)
        elif role == renderSetupRoles.NODE_SHOULD_DISPLAY_NAME:
            return False
        else:
            return super(LightsChildCollectionProxy, self).data(role)

    def supportsAction(self, action, numIndexes):
        return action in ([SET_ENABLED_ACTION, DELETE_ACTION])

    def getActionButton(self, column):
        return SET_ENABLED_ACTION if column == 0 else None

    def getActionButtonCount(self):
        return 1

    def isAcceptableTemplate(self, objList):
        return False

# Because of MAYA-60799, PySide base classes must appear last in the list of
# base classes.
class RenderLayerProxy(DataModelListObserver, ModelProxyItem):

    def __init__(self, model):
        super(RenderLayerProxy, self).__init__(model)

        # Build first, then add ourselves as an override observer after,
        # otherwise we'll observe ourselves adding overrides to our list.
        self._build()

        self.addListObserver(self._model)

    def _build(self):
        collections = self._model.getCollections()
        for collection in collections:
            self.appendRow(proxyFactory.create(collection))

    def aboutToDelete(self):
        """Cleanup method to be called immediately before the object is deleted."""
        super(RenderLayerProxy, self).aboutToDelete()
        self.removeListObserver(self._model)

    # Obsolete interface.
    dispose = aboutToDelete

    def type(self):
        return QStandardItem.UserType + self.typeIdx()
        
    def typeIdx(self):
        return RENDER_LAYER_TYPE_IDX
        
    def genericTypeIdx(self):
        # Constant for all derived classes
        return RENDER_LAYER_TYPE_IDX

    def data(self, role):
        if role == Qt.DisplayRole:
            return "Layer:   %s" % self._model.name()
        elif role == renderSetupRoles.NODE_TYPE_STR:
            return "Layer:"
        elif role == Qt.EditRole:
            return self._model.name()
        elif role == Qt.BackgroundRole:
            return QColor(93, 93, 93)
        elif role == renderSetupRoles.NODE_COLOR_BAR:
            return QColor(227,149,141)
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter
        elif role == renderSetupRoles.NODE_VISIBLE:
            return self._model.isVisible()
        elif role == renderSetupRoles.NODE_RENDERABLE:
            return self._model.isRenderable()
        elif role == renderSetupRoles.NODE_PATH_NAME:
            return self.data(Qt.EditRole) + "\\"
        elif role == renderSetupRoles.NODE_FLAGS:
            return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
        elif role == renderSetupRoles.NODE_HEADING_WIDTH:
            return self.headingWidth("Layer:   ")
        # The following two roles are irrelevant for render layers, but needed
        # by the draw code, which is common to all render setup node types.
        elif role == renderSetupRoles.NODE_SELF_ENABLED:
            return True
        elif role == renderSetupRoles.NODE_ENABLED:
            return True
        elif role == renderSetupRoles.NODE_NEEDS_UPDATE:
            # If this returns True it means we have received a selection change message, but have not processed it yet.
            # This is used to give visual indication to the user that they need to take action.
            return self._model.needsRefresh()
        else:
            return super(RenderLayerProxy, self).data(role)
            
    def setData(self, value, role):
        if role == renderSetupRoles.NODE_VISIBLE:
            renderSetupModel.instance().switchToLayer(self._model if (value==True or self._model.needsRefresh()) else None)
        if role == renderSetupRoles.NODE_RENDERABLE:
            self._model.setRenderable(value)
        else:
            super(RenderLayerProxy, self).setData(value, role)
    
    def handleDragMoveEvent(self, event):
        dragType = event.mimeData().text()
        for i in range(0, self.rowCount()):
            childItem = self.child(i, 0)
            # Does the dragged scene item type already exist in the layer?
            if childItem.equalsDragType(dragType):
                event.ignore()
                return
        event.accept()

    def handleDropEvent(self, event, sceneView):
        dragType = event.mimeData().text()
        if dragType == RENDER_SETTINGS_STR:
            self._createRenderSettings()
        elif dragType == CAMERAS_STR:
            self._createCameras(dragType)
        elif dragType == LIGHTS_STR:
            self._createLights()
        elif dragType == AOVS_STR:
            self._createAOVs()
        sceneView.expand(self.index())

        event.acceptProposedAction()

    def createCollection(self, collectionName, nodeType):
        collection = None
        if nodeType == collectionModel.Collection.kTypeId:
            collection = self._model.createCollection(collectionName)
        elif nodeType == collectionModel.RenderSettingsCollection.kTypeId:
            collection = self._model.renderSettingsCollectionInstance()
        elif nodeType == collectionModel.LightsCollection.kTypeId:
            collection = self._model.lightsCollectionInstance()
        elif nodeType == collectionModel.AOVCollection.kTypeId:
            collection = self._model.aovCollectionInstance()
        proxy = getProxy(collection)
        return proxy.index()

    def _getSceneItemIndex(self, previousTypesArray):
        index = 0
        for i in range(0, self.rowCount()):
            childItem = self.child(i, 0)
            childType = childItem.type()
            if childType in previousTypesArray:
                index = index + 1
            else:
                return index
        return index
    
    def _createCameras(self, camerasName):
        index = self._getSceneItemIndex([RENDER_SETTINGS_TYPE])
        camerasCollection = self._model.createCollection(camerasName)
        if camerasCollection:
            # Note: insertRows is used instead of insertRow because of a known Qt Bug: https://bugreports.qt.io/browse/PYSIDE-237
            self.insertRows(index, [CamerasProxy(camerasCollection)])

    def _createAOVs(self):
        self._model.aovCollectionInstance()

    def _createLights(self):
        self._model.lightsCollectionInstance()

    def _createRenderSettings(self):
        self._model.renderSettingsCollectionInstance()

    def delete(self):
        if self.data(renderSetupRoles.NODE_VISIBLE):
            self.setData(False, renderSetupRoles.NODE_VISIBLE)
        renderLayerModel.delete(self._model)

    def attachChild(self, collection, pos):
        self.model.attachCollection(pos, collection)

    def supportsAction(self, action, numIndexes):
        return action in ([CREATE_COLLECTION_ACTION,
                           SET_VISIBILITY_ACTION,
                           SET_RENDERABLE_ACTION,
                           RENAME_ACTION,
                           DELETE_ACTION] if numIndexes == 1 else
                          [DELETE_ACTION])
    def getActionButton(self, column):
        if column == 0:
            return SET_RENDERABLE_ACTION
        if column == 1:
            return SET_VISIBILITY_ACTION
        return None

    def getActionButtonCount(self):
        return 2

    def createListItemProxy(self, collection):
        return proxyFactory.create(collection)

    def isAcceptableTemplate(self, objList):
        """ Find if the selected filename is a template for a render layer """
        typename = jsonTranslatorUtils.getTypeNameFromDictionary(objList[0])
        return typename in [o.kTypeName for o in collectionModel.getAllCollectionClasses()] \
            and typename!=collectionModel.LightsChildCollection.kTypeName

    def _contains(self, specialCollectionType):
        # Iterate over the layer members and see if one of them is of the 
        # specialCollectionType (LightsCollection, RenderSettingsCollection, 
        # AOVCollection), if so, return True, if not return False
        for item in nodeList.forwardListGenerator(self._model):
            if item.kTypeName == specialCollectionType:
                return True
        return False

    @undo.chunk('Import a template render setup file')
    def importTemplate(self, objList):
        """ Import the collection template file in the current render layer """
        self._model._decodeChildren(objList, renderSetupModel.DECODE_AND_RENAME, None)

    def isDropAllowed(self, destinationModel):
        return destinationModel is self._model.parent()

class SceneItemProxy(DataModelListObserver, ModelProxyItem):
    def __init__(self, model):
        super(SceneItemProxy, self).__init__(model)
        
    def data(self, role):
        if role == Qt.BackgroundRole:
            return QColor(93, 93, 93)
        elif role == renderSetupRoles.NODE_COLOR_BAR:
            return QColor(150, 150, 150)
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter
        elif role == renderSetupRoles.NODE_FLAGS:
            return Qt.ItemIsEnabled
        elif role == renderSetupRoles.NODE_ENABLED:
            return True
        else:
            return super(SceneItemProxy, self).data(role)

class CamerasProxy(SceneItemProxy):
    def __init__(self, model):
        super(CamerasProxy, self).__init__(model)

    def type(self):
        return CAMERAS_TYPE
        
    def typeIdx(self):
        return CAMERAS_TYPE_IDX
        
    def data(self, role):
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return CAMERAS_STR
        else:
            return super(CamerasProxy, self).data(role)

    def equalsDragType(self, dragType):
        return dragType == CAMERAS_STR

class AOVsProxy(SceneItemProxy):
    def __init__(self, model):
        super(AOVsProxy, self).__init__(model)

    def type(self):
        return AOVS_TYPE
        
    def typeIdx(self):
        return AOVS_TYPE_IDX
        
    def data(self, role):
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return AOVS_STR
        else:
            return super(AOVsProxy, self).data(role)

    def equalsDragType(self, dragType):
        return dragType == AOVS_STR


# Because of MAYA-60799, QStandardItemModel must appear last in the list of
# base classes.
class RenderSetupProxy(DataModelListObserver, Template, QStandardItemModel):

    def __init__(self, parent=None):
        super(RenderSetupProxy, self).__init__(parent=parent)

        self._registered = False
        self._register()

        self.refreshModel()
        
        self.dropMimeDataFailure = False


        # Observer overall render setup model create and delete.  Note that
        # this observation does NOT create a render setup node.
        renderSetupModel.addObserver(self)
        
        # monitor changes to the light editor window for active border highlighting
        lightEditor.theLightEditorUI.visibilityChanged.connect(self._redraw)

    def renderSetupAdded(self):
        self._register()

    def renderSetupPreDelete(self):
        self.resetModel()

    @property
    def model(self):
        """Get the data model object for this proxy item.

        If the data model object does not exist, None is returned."""

        # We cannot keep an attribute containing a reference to the Render
        # Setup model instance because the underlying node is a scene node
        # that is re-created after any new scene or scene load.

        return renderSetupModel.instance() if renderSetupModel.hasInstance() \
            else None

    def aboutToDelete(self):
        """Cleanup method to be called immediately before the object is deleted."""
        self.resetModel()
        # Qt object can take a long time before actually being destroyed
        # => observation of renderSetupModel may remain active (since self is not dead)
        # => explicitly remove observer to avoid receiving unwanted notifications
        renderSetupModel.removeObserver(self)

    # Obsolete interface.
    dispose = aboutToDelete

    def __eq__(self, o):
        # The default QStandardItem:__eq__() method is not implemented
        # https://bugreports.qt.io/browse/PYSIDE-74
        return id(self)==id(o)
    
    def __ne__(self, o):
        # The default QStandardItem:__ne__() method is not implemented
        # https://bugreports.qt.io/browse/PYSIDE-74
        return not self.__eq__(o)

    def child(self, row, column=0):
        # RenderSetupProxy is a QStandardItemModel, not a QStandardItem,
        # but needs to be treated as a QStandardItem by the data model list
        # observation code.
        return self.item(row, column)

    def _register(self):
        # Observe data model
        #
        # Unfortunately, this class does not behave as CollectionProxy
        # or RenderLayerProxy, and does not respond correctly to list
        # observation.  Entered as MAYA-59899.
        # 
        if renderSetupModel.hasInstance() and not self._registered:
            self.addListObserver(renderSetupModel.instance())
            self._registered = True

    def _unregister(self):
        if self._registered:
            self.removeListObserver(renderSetupModel.instance())
            self._registered = False

    def _redraw(self, *args, **kwargs):
        self.layoutChanged.emit()

    def _buildHeader(self):
        header = QStandardItem(parent=self)
        header.setText("Render Setup")
        self.setHorizontalHeaderItem(0, header)

    def _buildTree(self):
        if renderSetupModel.hasInstance():
            renderLayers = renderSetupModel.instance().getRenderLayers()
            for renderLayer in renderLayers:
                proxy = RenderLayerProxy(renderLayer)
                self.appendRow(proxy)

    def attachChild(self, renderLayer, pos):
        self.model.attachRenderLayer(pos, renderLayer)

    def resetModel(self):
        self._unregister()
        for idx in range(self.rowCount()):
            self.child(idx).dispose()
        self.clear()

    def refreshModel(self):
        self._register()
        self._buildHeader()
        self._buildTree()

    def createRenderLayer(self, renderLayerName):
        # Impose the creation of the render setup node
        renderLayer = renderSetupModel.instance().createRenderLayer(
            renderLayerName)
        proxy = getProxy(renderLayer)
        return proxy.index()

    def acceptImport(self):
        # Accept the imported nodes
        if renderSetupModel.hasInstance():
            renderSetupModel.instance().acceptImport()

    def type(self):
        return QStandardItem.UserType + self.typeIdx()
        
    def typeIdx(self):
        return RENDER_SETUP_TYPE_IDX

    def supportedDropActions(self):
        return Qt.MoveAction # MAYA-61079: When we are ready for copy support, add back in: | Qt.CopyAction
        
    def mimeTypes(self):
        return [ RENDER_SETUP_MIME_TYPE ]
    
    def mimeData(self, indices):
        ''' This method builds the mimeData if the selection is correct '''

        # On drag start, prepare to pass the names of the dragged items to the drop mime data handler
        self.dropMimeDataFailure = False

        # Check that all selected entries have the same generic type
        genericModelTypeIdx  = None
        for index in indices:
            item = self.itemFromIndex(index)
            # Accept only item of the same 'generic' type
            if genericModelTypeIdx is None or genericModelTypeIdx==item.genericTypeIdx():
                genericModelTypeIdx = item.genericTypeIdx()
            else:
                self.dropMimeDataFailure = True
                break

        # However some collection entries have specific behaviors
        if not self.dropMimeDataFailure and genericModelTypeIdx==COLLECTION_TYPE_IDX:
            modelTypeIdx = None
            for index in indices:
                item = self.itemFromIndex(index)
                if modelTypeIdx is None:
                    modelTypeIdx = item.typeIdx()
                elif modelTypeIdx==RENDER_SETTINGS_TYPE_IDX or modelTypeIdx==LIGHTS_TYPE_IDX:
                    # Only one Lights or Render Settings could be moved;
                    # otherwise, the destination will have to merge them
                    # which will not produce the expected rendering.
                    self.dropMimeDataFailure = True
                    break

        # Prepare the entries to move
        mimeData = QMimeData()
        if not self.dropMimeDataFailure:
            encodedData = QByteArray()
            stream      = QDataStream(encodedData, QIODevice.WriteOnly)
            for index in indices:
                item = self.itemFromIndex(index)
                stream.writeString(item.data(Qt.EditRole))
            mimeData.setData(RENDER_SETUP_MIME_TYPE, encodedData)

        return mimeData

    def dropMimeData(self, mimeData, action, row, column, parentIndex):
    
        if self.dropMimeDataFailure:
            # The mimeData parsing faced a type mismatch
            OpenMaya.MGlobal.displayError(kSelectionTypeError)
            return False

        self.dropMimeDataFailure = False

        if action == Qt.IgnoreAction:
            return False

        if not mimeData.hasFormat(RENDER_SETUP_MIME_TYPE) or column > 0:
            self.dropMimeDataFailure = True
            return False
            
        # row is -1 when dropped on a parent item and not between rows.
        #   In that case we want to insert at row 0
        if row == -1:
            row = 0

        # Parse the mime data that was passed to us (a list of item string names)
        encodedData = mimeData.data(RENDER_SETUP_MIME_TYPE)
        stream      = QDataStream(encodedData, QIODevice.ReadOnly)

        destinationModel = renderSetupModel.instance() if not parentIndex.isValid() else self.itemFromIndex(parentIndex)._model

        # Is the drop allowed ?
        items = []
        while not stream.atEnd():
            name = stream.readString()
            item = self.findProxyItem(name)

            if (not item.isDropAllowed(destinationModel)):
                # Forbid the complete drop
                self.dropMimeDataFailure = True
                return False
            else:
                items.append(item)

        # Perform the drop
        try:
            with undo.CtxMgr(kDragAndDrop % (destinationModel.name(), row)):
                i = 0
                for item in items:
                    # If moving down within the same parent, the drop row must be
                    # decremented by one, as we're vacating one row.
                    destinationPosition = row + i
                    if item._model.parent() == destinationModel and row > item.row():
                        destinationPosition -= 1

                    renderSetupPrivate.moveModel(item._model, destinationModel, destinationPosition)

                    i += 1
        except Exception as ex:
            OpenMaya.MGlobal.displayError(kDragAndDropFailed % str(ex))
            self.dropMimeDataFailure = True

        return not self.dropMimeDataFailure

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsDropEnabled
        item = self.itemFromIndex(index)
        if not item:
            return Qt.NoItemFlags
        return item.data(renderSetupRoles.NODE_FLAGS)

    def findProxyItem(self, name):
        count = self.rowCount()
        for i in range(0, count):
            index = self.index(i, 0)
            item = self.itemFromIndex(index)
            result = item.findProxyItem(name)
            if result is not None:
                return result
        return None

    def createListItemProxy(self, renderLayer):
        return RenderLayerProxy(renderLayer)

    def exportSelectedToJson(self, proxies):
        """
            Export the selected proxies to a JSON string
        """
        data = []
        for proxy in proxies:
            proxyData = proxy._model.encode()
            parentIndex = proxy.index().parent()
            proxyData[PARENT_TYPE_NAME] = self.itemFromIndex(parentIndex)._model.kTypeName if parentIndex.isValid() else renderSetupModel.RenderSetup.kTypeName
            data.append(proxyData)
        return json.dumps(data, indent=2)

    def exportSelectedToFile(self, filePath, notes, proxies):
        """
            Export the selected proxies to the file
        """
        # Impose the creation of the render setup node
        rs = renderSetupModel.instance()
        with open(filePath, "w+") as file:
            if proxies is None:
                json.dump(rs.encode(notes), fp=file, indent=2, sort_keys=True)
            else:
                data = []
                for proxy in proxies:
                    data.append(proxy._model.encode(notes))              
                json.dump(data, fp=file, indent=2, sort_keys=True)

    def importAllFromFile(self, filePath, behavior, prependToName):
        """
            Import a complete render setup from that file
        """
        # Impose the creation of the render setup node
        rs = renderSetupModel.instance()
        with open(filePath, "r") as file:
            # Note: UTF-8 encoding by default
            rs.decode(json.load(file), behavior, prependToName)

    def isAcceptableTemplate(self, objList):
        """ Find if the selected filename is a template for the render setup """
        typename = jsonTranslatorUtils.getTypeNameFromDictionary(objList[0])
        return typename==renderLayerModel.RenderLayer.kTypeName

    @undo.chunk('Import a template render setup file')
    def importTemplate(self, objList):
        """ Import the render layer template file in the render setup """
        # Impose the creation of the render setup node
        rs = renderSetupModel.instance()
        rs._decodeChildren(objList, renderSetupModel.DECODE_AND_MERGE, None)

    @undo.chunk('Paste')
    def paste(self, jsonStr):
        objList = json.loads(jsonStr)
        typeName = jsonTranslatorUtils.getTypeNameFromDictionary(objList[0])
        parentTypeName = objList[0][PARENT_TYPE_NAME]
        data = clipboardData.ClipboardData(typeName, parentTypeName)
        if self.model.isAcceptableChild(data):
            self.model._decodeChildren(objList, renderSetupModel.DECODE_AND_RENAME, None)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
