"""
Node Editor Bookmarking UI

Bookmarks are saved using the special node nodeGraphEditorBookmarkInfo.

Each Node Editor Bookmark is represented by a nodeGraphEditorBookmarkInfo which stores the bookmark info, i.e. the view state and the graph state, including the state of each individual node in the scene.

"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.cmds as cmds
from functools import partial
import re

# The singleton bookmark editor window
#
windowName = 'nodeEditorBookmarksWindow'
_instance = None

# keeps track of the last bookmark loaded for each panel
# panelName -> nodeGraphEditorBookmarkInfo
#
_panelInfos = {}

class NodeEditorBookmarksWindow(object):
    """ Tracks the state of the Bookmarks window UI """
    def __init__(self, ned):
        self._ed = ned
        self._bookmarks = []  # list of [bookmark name , nodeGraphEditorBookmarkInfo]
        self._createUI()
    
    def _findInfo(self, name):
        # find the nodeGraphEditorBookmarkInfo with the given name
        for n,i in self._bookmarks:
            if n == name:
                return i

    def _onDelete(self, *args):
        items = cmds.textScrollList(self._tsl, q=True, si=True)
        if items and len(items):
            _deleteBookmarks([self._findInfo(n) for n in items])

    def _onSelect(self, *args):
        ixs = cmds.textScrollList(self._tsl, q=True, sii=True)
        # only restore the bookmark if one is selected
        if ixs and len(ixs) == 1:
            loadBookmark(self._ed, self._bookmarks[ixs[0]-1][1])

    def _onCreate(self, *args):
        createBookmark(self._ed)
        self.reset()

    def _onRename(self, *args):
        # rename the selected bookmark
        txt = cmds.textScrollList(self._tsl,q=True, si=True)
        if txt and len(txt):
            txt = txt[0]
            name = _getBookmarkName(txt)
            if name:
                _renameBookmark(self._findInfo(txt), name)
                self.reset()

    def _onReplace(self, *args):
        # replace the selected bookmark 
        txt = cmds.textScrollList(self._tsl,q=True, si=True)
        if txt and len(txt):
            txt = txt[0]
            info = self._findInfo(txt)
            cmds.nodeEditor(self._ed, e=True, createInfo=info)
            self.reset()

    def reset(self):
        # reset the UI to match the current bookmark state
        del self._bookmarks[:]

        bookmarksNodes = cmds.ls(exactType='nodeGraphEditorBookmarks')
        # there should be one bookmarks node
        if len(bookmarksNodes):
            bookmarksNode = bookmarksNodes[0]
            bookmarkInfos = cmds.listConnections(bookmarksNode + '.bookmarks')
            for bookmarkInfo in bookmarkInfos:
                name = cmds.getAttr(bookmarkInfo + '.name')
                if not len(name):
                    # ignore bookmarks with null descriptions, these are likely
                    # implicitly saved panel states
                    continue
                self._bookmarks.append((name,bookmarkInfo))

        # re-populate the scroll list
        self._bookmarks.sort(key=lambda e: _naturalKey(e[0]))
        cmds.textScrollList(self._tsl, e=True, ra=True)
        cmds.textScrollList(self._tsl, e=True, append = [n for n,i in self._bookmarks])
        self.selectLastLoadedInfo()

    def selectLastLoadedInfo(self):
        # select the last loaded bookmark
        lastInfo = _panelInfos[self._ed]
        if lastInfo:
            for i,(n,inf) in enumerate(self._bookmarks):
                if inf == lastInfo:
                    cmds.textScrollList(self._tsl, e=True, deselectAll=True, sii=i+1)

    def _createEditMenu(self, parent):
        cmds.setParent(parent, menu=True)
        cmds.menu(parent, e=True, deleteAllItems=True)

        cmds.menuItem(label=maya.stringTable['y_nodeEditorBookmarks.kDeleteBookmark' ],
                      c = self._onDelete)

        def deleteAllBookmarks(*args):
            items = cmds.textScrollList(self._tsl, q=True, ai=True)
            if items and len(items):
                _deleteBookmarks([i for n,i in self._bookmarks])
                
        cmds.menuItem(label=maya.stringTable['y_nodeEditorBookmarks.kDeleteAllBookmarks' ],
                      c = deleteAllBookmarks)
        
        cmds.menuItem(label=maya.stringTable['y_nodeEditorBookmarks.kRenameBookmark' ],
                      c = self._onRename)

        cmds.menuItem(label=maya.stringTable['y_nodeEditorBookmarks.kReplaceBookmark' ],
                      c = self._onReplace)
    
    def _createUI(self):
        # build the window UI

        cmds.window(windowName, title=maya.stringTable['y_nodeEditorBookmarks.kBookmarks' ],
                    width=150, height=400, menuBar=True, 
                    minimizeButton=True, maximizeButton=False)

        # create the menubar
        mnu = cmds.menu(label=maya.stringTable['y_nodeEditorBookmarks.kEdit' ], to=False)
        self._createEditMenu(mnu)

        # create the rest
        cmds.setParent(windowName)

        topfl = cmds.formLayout()
        listfl = cmds.formLayout()

        self._tsl = cmds.textScrollList(
            height=100,allowMultiSelection=True, 
            sc = self._onSelect, dkc=self._onDelete, dcc=self._onRename)

        # create the popupMenu on the scroll list
        mnu = cmds.popupMenu()
        self._createEditMenu(mnu)

        cmds.formLayout(listfl, e=True,
                        attachForm = [ (self._tsl, 'top', 0),
                                       (self._tsl, 'left', 0),
                                       (self._tsl, 'bottom', 0),
                                       (self._tsl, 'right', 0)])

        cmds.setParent('..')  # topfl

        buttonfl = cmds.formLayout(height=30)
        btn = cmds.button(label=maya.stringTable['y_nodeEditorBookmarks.kCreate' ], c = self._onCreate)
        cmds.formLayout(buttonfl, e=True,
                        attachForm = [ (btn, 'top', 0),
                                       (btn, 'left', 0),
                                       (btn, 'bottom', 0),
                                       (btn, 'right', 0)])

        cmds.formLayout(topfl, e=True,
                        attachForm = [ (listfl, 'right', 0),
                                       (listfl, 'left', 0),
                                       (listfl, 'top', 0),
                                       (buttonfl, 'right', 0),
                                       (buttonfl, 'left', 0),
                                       (buttonfl, 'bottom', 0)],
                        attachControl = [ (listfl, 'bottom', 0, buttonfl) ])

def addCallback(ned):
    """ called when a panel is added """
    _panelInfos[ned] = None

def removeCallback(ned = None):
    """ called when the owning panel is removed, and on file-new """
    global _instance
    if _instance:
        if _instance._ed == ned or ned == None:
            _instance = None
            try:
                cmds.deleteUI(windowName)
            except RuntimeError:
                pass
    try:
        del _panelInfos[ned]
    except KeyError:
        pass

def buildMenu(ned):
    """ builds the Bookmarks menu for the panel menuBar """
    menuName = ned + "Bookmarks"
    def bookmarksPMC(*args):
        cmds.setParent(menuName, menu=True)
        cmds.menu(menuName, e=True, dai=True)
        cmds.menuItem(label=maya.stringTable['y_nodeEditorBookmarks.kCreateBookmark'],
                      ann=maya.stringTable[ 'y_nodeEditorBookmarks.kCreateBookmarkAnnot'  ],
                      image= "addBookmark.png",
                      c=partial(createBookmark, ned))
        cmds.menuItem(label=maya.stringTable['y_nodeEditorBookmarks.kBookmarkEditor'],
                      ann=maya.stringTable[ 'y_nodeEditorBookmarks.kBookmarkEditorAnnot'  ],
                      image= "editBookmark.png",
                      c=partial(showWindow, ned))
        cmds.menuItem(divider=True)

        for name,info in _getBookmarkInfos():
            cmds.menuItem(label=name, ann=maya.stringTable['y_nodeEditorBookmarks.kLoadBookmarkAnnot' ],
                          c=partial(loadBookmark, ned, info) )
            cmds.menuItem(ob=True, ann=maya.stringTable['y_nodeEditorBookmarks.kRenameBookmarkAnnot' ],
                          c=partial(renameBookmark, ned, name, info) )
    cmds.menu(menuName, label=maya.stringTable['y_nodeEditorBookmarks.kBookmarks2'], pmc=bookmarksPMC)

def buildToolbar(ned):
    """ builds the bookmarking toolbar elmenets for the given editor """
    isz = 26
    addBookmarkItem = '%sAddBM' % (ned)
    editBookmarkItem = '%sEditBM' % (ned)
    fileDialogBackItem = '%sFDBack' % (ned)
    fileDialogForwardItem = '%sFDForward' % (ned)

    cmds.iconTextButton(
	addBookmarkItem,
        i1 = "addBookmark.png",
        w = isz,h = isz,
        ann = maya.stringTable[ 'y_nodeEditorBookmarks.kCreateBookmarkAnnot2'  ],
        c = partial(createBookmark, ned))
    cmds.iconTextButton(
	editBookmarkItem,
        i1 = "editBookmark.png",
        w = isz,h = isz,
        ann = maya.stringTable[ 'y_nodeEditorBookmarks.kBookmarkEditorAnnot2'  ],
        c = partial(showWindow, ned))
    cmds.iconTextButton(
	fileDialogBackItem,
        i1 = "SP_FileDialogBack.png",
        w = isz,h = isz,
        ann = maya.stringTable[ 'y_nodeEditorBookmarks.kPreviousBookmarkAnnot'  ],
        c = partial(loadPreviousBookmark, ned))
    cmds.iconTextButton(
	fileDialogForwardItem,
        i1 = "SP_FileDialogForward.png",
        w = isz,h = isz,
        ann = maya.stringTable[ 'y_nodeEditorBookmarks.kNextBookmarkAnnot'  ],
        c = partial(loadNextBookmark, ned))

def renameBookmark(ned, oldname, info, *args):
    """ Rename the supplied bookmark, given the old name """
    newname = _getBookmarkName(oldname)
    if newname:
        _renameBookmark(info, newname)

def loadBookmark(ned, info, *args):
    """ apply the supplied bookmark """
    name = _getDescriptionForInfo(info)
    # restore the info, clear the existing hud message and set the bookmark name
    # as the hud message for 3 seconds.
    cmds.nodeEditor(ned, e=True, hudMessage = ("",0,0), restoreInfo=info)
    cmds.nodeEditor(ned, e=True, hudMessage = (name, 0, 3.0))
    _panelInfos[ned] = info
    inst = _getInstance()
    if inst:
        inst.selectLastLoadedInfo()

def createBookmark(ned, *args):
    """ create a new bookmark """
    n0 = set(cmds.ls(type='nodeGraphEditorBookmarkInfo'))
    cmds.nodeEditor(ned, e=True, createInfo='nodeView#')
    n1 = set(cmds.ls(type='nodeGraphEditorBookmarkInfo'))
    # find the new nodeGraphEditorBookmarkInfo and set its name attr
    newInfos = n1 - n0
    if len(newInfos):
        newInfo = newInfos.pop()
        name = _getBookmarkName(newInfo)
        if name:
            cmds.setAttr(newInfo + '.name', name,
                         type = 'string')

            _refreshWindow()
        else:
            # user cancelled, delete the new info
            _deleteBookmarks([newInfo])

def loadNextBookmark(ned):
    """ load the next bookmark, based on alphabetical ordering of bookmarks """
    info = _getNextBookmark(ned, 1)
    if info:
        loadBookmark(ned, info)

def loadPreviousBookmark(ned):
    """ load the previous bookmark, based on alphabetical ordering of bookmarks """
    info = _getNextBookmark(ned, -1)
    if info:
        loadBookmark(ned, info)

def showWindow(ned, *args):
    """ Show the Bookmarks window.  If it already exists, re-build it """
    global _instance
    if cmds.window(windowName, ex=True):
        cmds.deleteUI(windowName)
    _instance = NodeEditorBookmarksWindow(ned)

    cmds.scriptJob(parent=windowName, 
                   conditionTrue=("deleteAllCondition", removeCallback))

    _instance.reset()
    cmds.showWindow(windowName)

#
# Internal functions
#

def _getInstance():
    # get the window object or None
    if _instance and cmds.window(windowName, ex=True):
        return _instance
    return None

def _getNextBookmark(ned, incr):
    # get the next bookmark for the given editor
    # incr - movement increment in alphabetical bookmark list
    #
    lastInfo = _panelInfos[ned]
    i = 0
    infos = _getBookmarkInfos()
    if len(infos):
        if lastInfo:
            for ix, (name,info) in enumerate(infos):
                if info == lastInfo:
                    i = (ix + incr) % len(infos)
        return infos[i][1]
    return None


def _getBookmarkName(name):
    # show a prompt to get a new name from the supplied name
    ok = maya.stringTable['y_nodeEditorBookmarks.kOk']
    cancel = maya.stringTable['y_nodeEditorBookmarks.kCancel']
    result = cmds.promptDialog(
        title=maya.stringTable['y_nodeEditorBookmarks.kNameBookmarkTitle'],
        message=maya.stringTable['y_nodeEditorBookmarks.kNameMessage'],
        text=name, defaultButton=ok, button=[ok,cancel])
    if result == ok:
        return cmds.promptDialog(q=True, tx=True)
    return None

def _renameBookmark(info, name):
    # replace the name of the supplied bookmark
    cmds.setAttr(info + '.name', name,
                     type = 'string')
    _refreshWindow()

def _getDescriptionForInfo(bookmarkInfo):
    # gets the in name (.name) for the given nodeGraphEditorBookmarkInfo
    return cmds.getAttr(bookmarkInfo + '.name')

def _getBookmarkInfos():
    # gets the list of (name, nodeGraphEditorBookmarkInfo), sorted by name
    bookmarks = []
    bookmarksNodes = cmds.ls(exactType='nodeGraphEditorBookmarks')
    if len(bookmarksNodes):
        bookmarksNode = bookmarksNodes[0]
        bookmarkInfos = cmds.listConnections(bookmarksNode + '.bookmarks')
        for bookmarkInfo in bookmarkInfos:
            name = _getDescriptionForInfo(bookmarkInfo)
            if not len(name):
                # ignore bookmarks with null descriptions, these are likely
                # implicitly saved panel states
                continue
            bookmarks.append((name, bookmarkInfo))
    bookmarks.sort(key=lambda e: _naturalKey(e[0]))
    return bookmarks
    
def _deleteBookmarks(infos):
    # disconnect saved nodes from the bookmark info nodes we're deleting so they don't get deleted as well
    for bookmarkInfo in infos:
        if bookmarkInfo:
            bookmarkInfoIndices = cmds.getAttr(bookmarkInfo + '.nodeInfo', multiIndices=True)
            nodeInfoDepNodeAttrFormat = bookmarkInfo + '.nodeInfo[{}].dependNode'
            for index in bookmarkInfoIndices:
                nodeInfoDepNodeAttr = nodeInfoDepNodeAttrFormat.format(str(index))
                depNodeMessageAttr = cmds.connectionInfo(nodeInfoDepNodeAttr, sourceFromDestination=True)
                if depNodeMessageAttr:
                    cmds.disconnectAttr(depNodeMessageAttr, nodeInfoDepNodeAttr)

    # delete the supplied bookmarks
    todelete = []
    todelete.extend(infos)
    if len(todelete):
        cmds.delete(*todelete)
    _refreshWindow()

def _refreshWindow():
    # Refresh the bookmarks UI
    inst = _getInstance()
    if inst:
        inst.reset()

def _naturalKey(str_):
    # for natural sort
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', str_)]
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
