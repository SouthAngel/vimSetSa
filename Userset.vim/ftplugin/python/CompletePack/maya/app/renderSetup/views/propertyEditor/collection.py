from PySide2.QtWidgets import QGroupBox, QVBoxLayout

import maya.app.renderSetup.views.propertyEditor.basicCollection as basicCollection
import maya.app.renderSetup.views.propertyEditor.selectorFactory as selectorFactory
from maya.app.renderSetup.views.propertyEditor.collectionPropertyEditorStrings import *

import maya.app.renderSetup.views.proxy.renderSetup as renderSetup

import maya.app.renderSetup.views.utils as utils

import maya.app.renderSetup.model.override as override
import maya.app.renderSetup.model.plug as modelPlug

import maya.cmds as cmds

from functools import partial

# Layout inter-widget vertical, horizontal spacing.
vSpc = 3
hSpc = 10

class Collection(basicCollection.BasicCollection):
    """
    This class represents the property editor view of a collection.
    """
    
    def __init__(self, item, parent):
        # parent.treeView is a weakref.
        self.treeView = parent.treeView

        # Base class calls preSelector(), which for this class requires the
        # selector UI builder, so create it first.
        self._selectorUI = selectorFactory.create(item().model.getSelector())

        super(Collection, self).__init__(item, parent)

        # Observe data model selector changes.
        self.item().model.addItemObserver(self.dataModelChanged)

        self.postSelector()

    def postSelector(self):
        cmds.setParent(self._layoutName)
        
        form = cmds.formLayout(numberOfDivisions=100)

        buttonWidth = 50

        # Buttons to select and to view the selector output.
        selectAllBtn = cmds.button(
            label=kSelectAll, width=buttonWidth, annotation=kSelectAllTooltip,
            command=partial(Collection._selectAllCb, self))

        viewAllBtn = cmds.button(
            label=kViewAll, width=buttonWidth, annotation=kViewAllTooltip,
            command=partial(Collection._viewAllCb, self))

        separator = cmds.separator()

        self._menu = cmds.optionMenu(
            label=kAddOverride, width=200, annotation=kAddOverrideTooltipStr,
            changeCommand=partial(Collection._menuCb, self))
        cmds.menuItem(label=renderSetup.CollectionProxy.NO_OVERRIDE)
        cmds.menuItem(label=renderSetup.CollectionProxy.ABSOLUTE_OVERRIDE)
        cmds.menuItem(label=renderSetup.CollectionProxy.RELATIVE_OVERRIDE)
        cmds.optionMenu(self._menu, edit=True,
                        value=self.item()._getValueOverrideMode())

        self._dropBox = cmds.iconTextStaticLabel(
            style='iconAndTextVertical',
            i1='RS_drop_box.png',
            label=kDragAttributesFromAE,
            dropCallback=partial(Collection._dropCb, self),
            visible=self._isDropBoxVisible())

        cmds.formLayout(
            form, edit=True,
            attachForm=[(selectAllBtn,  'top',   0),
                        (selectAllBtn,  'right', hSpc+buttonWidth),
                        (viewAllBtn,    'top',   0),
                        (separator,     'left',  hSpc),
                        (separator,     'right', hSpc),
                        (self._menu,    'left',  hSpc),
                        (self._dropBox, 'left',  hSpc),
                        (self._dropBox, 'right', hSpc)],
            attachControl=[(viewAllBtn,    'right', hSpc, selectAllBtn),
                           (separator,     'top',   vSpc, selectAllBtn),
                           (self._menu,    'top',   vSpc, separator),
                           (self._dropBox, 'top',   vSpc, self._menu)])

        cmds.setParent('..')


    def __del__(self):
        if self.item() is not None:
            self.item().model.removeItemObserver(self.dataModelChanged)

    def dataModelChanged(self, *posArgs, **kwArgs):
        if 'selectorChanged' in kwArgs:
            # Clear existing selector UI, create a new one.
            self._clearSelectorWidgets()
            self._selectorUI = selectorFactory.create(self.getModelSelector())
            self._selectorUI.build(self._selectorLayout)

        # Unconditionally update the selector display type 
        self._syncSelectorDisplay()

    def _clearSelectorWidgets(self):
        # Code in main.PropertyEditor.clearWidgets() causes 
        # RuntimeError: 'Internal C++ object (PySide.QtGui.QVBoxLayout) already deleted.
        # The following from
        # http://stackoverflow.com/questions/4528347/clear-all-widgets-in-a-layout-in-pyqt
        for i in reversed(xrange(self._selectorLayout.count())):
            self._selectorLayout.itemAt(i).widget().setParent(None)

    def _syncSelectorDisplay(self):
        # Selector display type not being shown in UI as of 21-Apr-2016.
        pass

    def preSelector(self):
        """Create UI displayed above selector UI."""

        # Nothing to display as of 21-Apr-2016.
        pass
        
    def _selectAllCb(self, data):
        cmds.select(list(self.getModelSelector().names()))

    def _viewAllCb(self, data):
        """On view button click, show modal window with list of objects."""

        cmds.layoutDialog(ui=self.buildViewObjects, title=kViewCollectionObjects)

    def getModelSelector(self):
        return self.item().model.getSelector()

    def setupSelector(self, layout):
        self._selectorGroupBox = QGroupBox(parent=self)
        self._selectorGroupBox.setContentsMargins(0, 0, 0, 0)
        self._selectorLayout = QVBoxLayout()
        self._selectorLayout.setContentsMargins(0, 0, 0, 0)
        self._selectorLayout.setSpacing(utils.dpiScale(2))
        self._selectorLayout.setObjectName('collection_selector_layout')
        self._selectorGroupBox.setLayout(self._selectorLayout)

        self._selectorUI.build(self._selectorLayout)

        layout.addWidget(self._selectorGroupBox)

    def _isDropBoxVisible(self):
        return cmds.optionMenu(self._menu, query=True, value=True) != \
            renderSetup.CollectionProxy.NO_OVERRIDE

    def isAbsoluteMode(self):
        return self.item()._getValueOverrideMode() == \
            renderSetup.CollectionProxy.ABSOLUTE_OVERRIDE

    def _setDropBoxVisibility(self):
        cmds.iconTextStaticLabel(self._dropBox, edit=True,
                                 visible=self._isDropBoxVisible())

    def _menuCb(self, mode):
        self.item()._setValueOverrideMode(mode)
        self._setDropBoxVisibility()

    def _dropCb(self, dragControl, dropControl, messages, x, y, dragType):
        # Create override.  We are expecting a node.plug string as the
        # first element of the messages list.
        if not messages or not isinstance(messages[0], basestring):
            return

        tokens = messages[0].split('.')
        attrName = tokens[-1]
        nodeName = tokens[0]

        model = self.item().model
        relative = not self.isAbsoluteMode()

        ov = model.createRelativeOverride(nodeName, attrName) if relative \
             else model.createAbsoluteOverride(nodeName, attrName)

        if relative and isinstance(ov, override.AbsOverride):
            # We asked for relative, got absolute.  Warn the user.
            rsPlug = modelPlug.Plug(nodeName, attrName)
            msg = kRelativeWarning % (attrName, rsPlug.localizedTypeString())
            cmds.warning(msg)

    def populateFields(self):
        self._selectorUI.populateFields()

    def buildViewObjects(self):

        # Get the layoutDialog's formLayout.
        #
        form = cmds.setParent(q=True)

        # layoutDialog's are unfortunately not resizable, so hard code a size
        # here, to make sure all UI elements are visible.
        #
        cmds.formLayout(form, e=True, width=500)

        objects = list(self.getModelSelector().names())
        objects.sort()

        nbObjects = cmds.text(label=(kNbObjects % len(objects)))

        textField = cmds.scrollField(editable=False, text='\n'.join(objects))

        okBtn = cmds.button(label=kOK,
                            command=partial(self.onOKButton, msg='ok'))

        cmds.formLayout(
            form, edit=True,
            attachForm=[(nbObjects, 'top',    vSpc),
                        (nbObjects, 'left',   hSpc),
                        (textField, 'left',   hSpc),
                        (textField, 'right',  hSpc),
                        (okBtn,     'bottom', vSpc),
                        (okBtn,     'right',  hSpc)],
            attachControl=[(textField, 'top', vSpc, nbObjects),
                           (textField, 'bottom', vSpc, okBtn)])

    def onOKButton(self, data, msg):
        cmds.layoutDialog(dismiss=msg)
    
    def highlight(self, names):
        self._selectorUI.highlight(names)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
