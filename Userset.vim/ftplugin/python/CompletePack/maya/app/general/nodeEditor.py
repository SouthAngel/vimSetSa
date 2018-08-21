"""
Support for Node Editor panel.

Plugin Support:

Plugins providing nodes with a custom creation script should add
callbacks to the lists:

pluginNodeClassificationCallbacks
pluginNodeCreationCallbacks

Following the Mentalray example at the bottom of this file.

"""

from maya import cmds, mel
import maya.app.general.nodeEditorMenus as nodeEditorMenus

pluginNodeClassificationCallbacks = []
pluginNodeCreationCallbacks = []


nEd = cmds.nodeEditor

# tracks all normal node editor panels
editors = {}

class NodeEditor(object):
    """
    Encapsulates one Node Editor panel instance.
    """
    def __init__(self, ned):
        self._ed = ned
        self._popupMenu = ned + 'PopupMenu'
    
    def buildMenus(self):
        """
        Create any required UI for this editor
        """
        self._createPopupMenu()

    def _createPopupMenu(self):
        """
        Create the popupMenu for this editor
        """
        # popupMenu will be parented to the editor control
        parent = nEd(self._ed, q=True, control=True)
        if not cmds.popupMenu(self._popupMenu, exists=True):
            cmds.popupMenu(self._popupMenu, p=parent, mm=True, pmc=self._onPopupMenuPost)
    
    def _onPopupMenuPost(self, pm, ned):
        """
        postMenuCommand for the editor popupMenu
        """
        assert(cmds.popupMenu(self._popupMenu, exists=True))
        cmds.popupMenu(pm, e=True, deleteAllItems=True)
        fbType = nEd(self._ed, q=True, feedbackType=True)
        if fbType == 'node':
            cmds.setParent(self._popupMenu, m=True)
            fbNode = nEd(self._ed, q=True, feedbackNode=True)
            nodeEditorMenus.createNodeItemMarkingMenu(self._ed, fbNode)
        elif fbType == 'connection':
            cmds.setParent(self._popupMenu, m=True)
            nEd(ned, e=True, selectFeedbackConnection=True)
            nodeEditorMenus.createConnectionMarkingMenu(self._ed)
        elif fbType == 'plug':
            cmds.setParent(self._popupMenu, m=True)
            fbPlug = nEd(self._ed, q=True, feedbackPlug=True)
            fbNode = nEd(self._ed, q=True, feedbackNode=True)
            nodeEditorMenus.createPlugMarkingMenu(self._ed, fbNode, fbPlug)
        elif fbType == 'tab':
            cmds.setParent(self._popupMenu, m=True)
            fbTab = nEd(self._ed, q=True, feedbackTabIndex=True)
            nodeEditorMenus.createTabContextMenu(self._ed, fbTab)
        elif fbType == None:
            cmds.setParent(self._popupMenu, m=True)
            nodeEditorMenus.createNodeEditorMarkingMenu(self._ed)

#
# hooks for MEL scripted panel
#

def createCallback(ned):
    """
    Do non-UI initialization
    """
    pass

def addCallback(ned):
    """ 
    Create any required UI
    """
    # this is called while the editor is still unparented
    editors[ned] = NodeEditor(ned)

def removeCallback(ned):
    """
    Clean up any UI
    """
    # remove the NodeEditor from the list of editors, it should be garbage collected shortly
    del editors[ned]

def buildPanelMenus(ned):
    """
    Do the python menu creation.
    This is called by nodeEdBuildPanelMenus
    """
    ne = editors[ned]
    ne.buildMenus()

def createNode(nodeType):
    """
    Called by the editor to create a new node based on the supplied type.
    """

    # Some node types have special procedures associated with them
    # which will create them as well as do other required set-up.
    # This is true of most rendering-related nodes.
    #
    
    melcmd = _findCustomCreateCommand(nodeType)
    if not melcmd:
        # didn't find a custom command, search the internal data
        melcmd = _findStandardCreateCommand(nodeType)

    if melcmd:
        mel.eval(melcmd)
    else:
        # fall back on just straight-up creating it
        cmds.createNode(nodeType)

#
# Internal methods
#

# local copy of global table from renderCreateNodeUI.mel
_createNodeTable = []
def mayaNodeCategories():
    # Create the table if it doesn't exist
    if len(_createNodeTable) == 0:
        n = mel.eval('mayaNumNodeCategories')
        for i in range(n):
            _createNodeTable.append( mel.eval('mayaGetNodeCategory(%d)' % i) )
    return _createNodeTable

def _findCustomCreateCommand(nodeType):
    """
    Locate a custom command to create this nodeType, based on registered 
    custom classification categories. Return None if no match.
    """
    use2012 = not hasattr(cmds, 'callbacks')
    if use2012:
        # use the pre-2013 method of finding custom node create scripts
        return _findCustomCreateCommand2012(nodeType)

    # get the list of classifications which have custom handlers
    customClassifications = cmds.callbacks(hook='renderNodeClassification', 
                                           executeCallbacks=True)
    if not customClassifications:
        return None
    for topclassif in customClassifications:
        if cmds.getClassification(nodeType, sat=topclassif):
            # this is a type with a custom handler
            postCmd = ''
            customCallbacks = cmds.callbacks(postCmd, 
                                             nodeType, 
                                             hook='createRenderNodeCommand', 
                                             executeCallbacks=True)
            if customCallbacks and len(customCallbacks):
                # there should be only one callback, which must be a MEL fragment
                return customCallbacks[0]

def _findStandardCreateCommand(nodeType):
    """
    Locate a standard create command based on classification cateogries
    """
    for name, classif, asFlag, catFlag in mayaNodeCategories():
        if cmds.getClassification(nodeType, sat=classif):
            # this type matches the current category, create as a standard maya render node
            return 'createRenderNodeCB %s "%s" "%s" ""' % (asFlag, catFlag, nodeType)

#
# 2012 support for plugin node types
#

def _findCustomCreateCommand2012(nodeType):
    """
    Implementation of _findCustomCreateCommand for 2012
    """
    for i,classifCB in enumerate(pluginNodeClassificationCallbacks):
        topclassif = classifCB()
        if cmds.getClassification(nodeType, sat=topclassif):
            # this is a type with a custom handler, call the corresponding callback
            # to get the MEL script which will actually create the node
            createCB = pluginNodeCreationCallbacks[i]
            postCmd = ''
            customCallback = createCB(postCmd, nodeType)
            # the result must be a MEL fragment
            return customCallback

#
# Mentalray support for 2012
#

# local copy of global table from mentalRayCustomNodeUI.mel
_mrCreateNodeTable = []
def mrNodeCategories():
    # Create the table if it doesn't exist
    if len(_mrCreateNodeTable) == 0:
        n = mel.eval('mrNumNodeCategories')
        for i in range(n):
            _mrCreateNodeTable.append( mel.eval('mrGetNodeCategory(%d)' % i) )
    return _mrCreateNodeTable

def mrClassificationCB():
    """
    \return classification root of all nodes handled by the corresponding create callback.
    """
    return 'rendernode/mentalray'

def mrCreateNodeCB(postCmd, nodeType):
    """
    If the given node is Mentalray, return a MEL command which will create
    an instance of the supplied node type.  Return None if the given node
    is not handled by Mayatomr.

    \param[in] postCmd - MEL code to be executed after creation
    \param[in] nodeType - The type of the node to be created
    \return MEL command which creates the given node, or None

    """
    if cmds.pluginInfo('Mayatomr', q=True, loaded=True) and\
    cmds.getClassification(nodeType, sat='rendernode/mentalray'):
        
        for title, uibasename, staticclassif, runtimeclassif in mrNodeCategories():
            if cmds.getClassification(nodeType, sat=staticclassif):
                # this type matches the current category
                return 'mrCreateCustomNode "%s" "%s" "%s"' % (runtimeclassif, postCmd, nodeType)

# add the Mentalray callbacks
pluginNodeClassificationCallbacks.append(mrClassificationCB)
pluginNodeCreationCallbacks.append(mrCreateNodeCB)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
