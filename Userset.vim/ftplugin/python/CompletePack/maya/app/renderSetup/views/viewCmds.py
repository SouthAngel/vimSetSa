import maya
maya.utils.loadStringResourcesForModule(__name__)

import maya.api.OpenMaya as OpenMaya
import maya.app.renderSetup.model.utils as utils
import maya.app.renderSetup.model.modelCmds as modelCmds
import itertools

import maya.cmds as cmds

kParsingError             = maya.stringTable['y_viewCmds.kParsingError'             ]
kAddAndDeselectEditOnly   = maya.stringTable['y_viewCmds.kAddAndDeselectEditOnly'   ]
kNotEditableFlags         = maya.stringTable['y_viewCmds.kNotEditableFlags'         ]
kAddAndDeselectNoTogether = maya.stringTable['y_viewCmds.kAddAndDeselectNoTogether' ]
kSelectionEditFailed      = maya.stringTable['y_viewCmds.kSelectionEditFailed'      ]


def getRenderSetupWindow():
    import maya.app.renderSetup.views.renderSetup as renderSetupUI
    return renderSetupUI.renderSetupWindow
    
def getPropertyEditor():
    import maya.app.renderSetup.views.renderSetup as renderSetupUI
    return renderSetupUI.propertyEditor

def getRenderSetupView():
    rsw = getRenderSetupWindow()
    return None if rsw is None else rsw.centralWidget.renderSetupView

def getSelectionModel():
    rsv = getRenderSetupView()
    return None if rsv is None else rsv.selectionModel()


def _itemMatches(item, renderLayers, overrides, collections):
    import maya.app.renderSetup.views.proxy.renderSetup as renderSetupProxy
    return ((renderLayers and item.type() == renderSetupProxy.RENDER_LAYER_TYPE) or
            (collections and item.type() == renderSetupProxy.COLLECTION_TYPE) or
            (overrides and item.type() == renderSetupProxy.RENDER_OVERRIDE_TYPE))
            
def getSelection(renderLayers=False, collections=False, overrides=False):
    results = []
    
    selectionModel = getSelectionModel()
    if selectionModel is None:
        return results

    selectedIndexes = selectionModel.selectedIndexes()

    from PySide2.QtCore import Qt
    if not renderLayers and not collections and not overrides:
        # If we're not filtering by renderLayers, collections or overrides,
        # set the result to be the list of selected index item names
        results = [selectedIndex.data(Qt.EditRole) for selectedIndex in selectedIndexes]
    else:
        # Otherwise, set the result to be the list of selected index item 
        # names, where only the selected index items of the specified types
        # (renderLayers, collections, overrides) are used.
        results = [selectedIndex.data(Qt.EditRole) for selectedIndex in selectedIndexes \
                   if _itemMatches(selectedIndex.model().itemFromIndex(selectedIndex), renderLayers, overrides, collections)]

    return results

def getSelectedCollections():
    # add the collections from the selected layers to the set
    selection = getSelection(True, False, False)
    renderLayers = (utils.nameToUserNode(renderLayerName) for renderLayerName in selection)
    collectionSet = set(modelCmds.getCollections(renderLayers))

    # add the selected collections to the set
    selection = getSelection(False, True, False)
    collections = (utils.nameToUserNode(collectionName) for collectionName in selection)
    collectionSet.update(collections)
    return collectionSet

def notInSelectedRenderLayers(*args, **kwargs):
    ''' Tests for nodes not in any currently selected layer.
        args: an array of nodes to test
        kwargs:
            attributes: an array of attributes to test
    '''
    collectionSet = getSelectedCollections()
    return [objectName for objectName in args if not modelCmds.isCollectionMember(objectName, collectionSet)]

def inSelectedRenderLayers(*args, **kwargs):
    ''' Tests for nodes in any currently selected layer.
        args: an array of nodes to test
        kwargs:
            attributes: an array of attributes to test
    '''
    collectionSet = getSelectedCollections()
    return [objectName for objectName in args if modelCmds.isCollectionMember(objectName, collectionSet)]
    
def highlight(names):
    propertyEditor = getPropertyEditor()
    if propertyEditor:
        propertyEditor.highlight(names)

class RenderSetupSelectCmd(OpenMaya.MPxCommand):
    """
    Command that can be used to select render setup elements as well as to
    query the elements in the render setup selection.
    
    Five optional flags can be used with this command:
    
    -additive (-a) adds elements to the selection (without clearing it)
    
    -deselect (-d) removes elements from the current selection
    
    -renderLayers is a query only flag that specifies that renderLayers 
    should be returned as part of the query
    
    -collections is a query only flag that specifies that collections should 
    be returned as part of the query

    -overrides is a query only flag that specifies that overrides should be 
    returned as part of the query

    By default the selection is cleared before selecting elements. Also the
    additive and deselect flags cannot be used in conjunction.
    
    Sample Usage:
    // Select "renderSetupLayer1" and "renderSetupLayer2" 
    renderSetupSelect "renderSetupLayer1" "renderSetupLayer2"
    
    // Add "renderSetupLayer1" and "renderSetupLayer2" to the selection
    renderSetupSelect -additive "renderSetupLayer1" "renderSetupLayer2"

    // Deselect "renderSetupLayer1" and "renderSetupCollection2" from the selection
    renderSetupSelect -deselect "renderSetupLayer1" "renderSetupCollection2"

    // Query the selected render setup items
    renderSetupSelect -query
    
    // Query the selected render setup items that are renderLayers and 
    // overrides
    renderSetupSelect -query -renderLayers -overrides
    """
    kCmdName = "renderSetupSelect"
    kAddFlag = "-a"
    kAddFlagLong = "-additive"
    kDeselectFlag = "-d"
    kDeselectFlagLong = "-deselect"
    kRenderLayersFlag = "-rl"
    kRenderLayersFlagLong = "-renderLayers"
    kCollectionsFlag = "-c"
    kCollectionsFlagLong = "-collections"
    kOverridesFlag = "-o"
    kOverridesFlagLong = "-overrides"
    
    @staticmethod
    def creator():
        return RenderSetupSelectCmd()

    @staticmethod
    def createSyntax():
        syntax = OpenMaya.MSyntax()
        syntax.enableQuery = True
        syntax.addFlag(RenderSetupSelectCmd.kAddFlag, RenderSetupSelectCmd.kAddFlagLong, OpenMaya.MSyntax.kNoArg)
        syntax.addFlag(RenderSetupSelectCmd.kDeselectFlag, RenderSetupSelectCmd.kDeselectFlagLong, OpenMaya.MSyntax.kNoArg)
        syntax.addFlag(RenderSetupSelectCmd.kRenderLayersFlag, RenderSetupSelectCmd.kRenderLayersFlagLong, OpenMaya.MSyntax.kNoArg)
        syntax.addFlag(RenderSetupSelectCmd.kCollectionsFlag, RenderSetupSelectCmd.kCollectionsFlagLong, OpenMaya.MSyntax.kNoArg)
        syntax.addFlag(RenderSetupSelectCmd.kOverridesFlag, RenderSetupSelectCmd.kOverridesFlagLong, OpenMaya.MSyntax.kNoArg)
        syntax.setObjectType(OpenMaya.MSyntax.kStringObjects, 0)
        syntax.useSelectionAsDefault(False)
        return syntax

    def isUndoable(self):
        return False
    
    def doIt(self, args):
        # Use an MArgDatabase to parse the command invocation.
        #
        try:
            argDb = OpenMaya.MArgDatabase(self.syntax(), args)
        except RuntimeError as ex:
            raise RunTimeError(kParsingError % str(ex))

        # add and deselect are non-query mode flags
        add = argDb.isFlagSet(RenderSetupSelectCmd.kAddFlag)
        deselect = argDb.isFlagSet(RenderSetupSelectCmd.kDeselectFlag)
        if argDb.isQuery and (add or deselect):
            raise RuntimeError(kAddAndDeselectEditOnly)

        # renderLayers, collections, and overrides are query mode flags
        renderLayers = argDb.isFlagSet(RenderSetupSelectCmd.kRenderLayersFlag)
        collections = argDb.isFlagSet(RenderSetupSelectCmd.kCollectionsFlag)
        overrides = argDb.isFlagSet(RenderSetupSelectCmd.kOverridesFlag)
        if not argDb.isQuery and (renderLayers or collections or overrides):
            raise RuntimeError(kNotEditableFlags)

        if argDb.isQuery:
            results = getSelection(renderLayers, collections, overrides)
            self.setResult(results)
        else:
            selectionModel = getSelectionModel()
            if selectionModel is None:
                if argDb.numberOfFlagsUsed:
                    raise RuntimeError(kSelectionEditFailed)

            # Can't have both add and deselect at the same time
            if add and deselect:
                raise RuntimeError(kAddAndDeselectNoTogether)
        
            # Find the items that we are selecting and add them to our item selection
            from PySide2.QtCore import QItemSelection, QItemSelectionModel
            import maya.app.renderSetup.views.proxy.renderSetup as renderSetupProxy

            itemsToSelect = argDb.getObjectStrings()
            selection = QItemSelection()
            
            models = itertools.ifilter(None, (utils.nameToUserNode(item) for item in itemsToSelect))
            proxies = [renderSetupProxy.getProxy(model) for model in models]
            for proxy in proxies:
                selection.select(proxy.index(), proxy.index())
            
            if not deselect:
                treeview = getRenderSetupView()
                for proxy in proxies:
                    parent = proxy.parent()
                    while parent:
                        treeview.setExpanded(parent.index(), True)
                        parent = parent.parent()

            # Use the appropriate selection method
            selectMode = QItemSelectionModel.Select if add else QItemSelectionModel.Deselect if deselect else QItemSelectionModel.ClearAndSelect
            selectionModel.select(selection, selectMode)
    

class RenderSetupHighlightCmd(OpenMaya.MPxCommand):
    """
    Command that can be used to highlights given object names/paths
    in the collections.
    
    This helps visualize how objects ended up being part of the 
    selected collections. For ex: by pattern or by static selection.
    """
    
    kCmdName = "renderSetupHighlight"
    
    @staticmethod
    def creator():
        return RenderSetupHighlightCmd()
        
    @staticmethod
    def createSyntax():
        syntax = OpenMaya.MSyntax()
        syntax.enableQuery = False
        syntax.useSelectionAsDefault(True)
        return syntax

    def isUndoable(self):
        return False
    
    def doIt(self, args):
        names = set((args.asString(i) for i in xrange(len(args))) \
            if len(args) > 0 else cmds.ls(long=True, selection=True))
        highlight(names)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
