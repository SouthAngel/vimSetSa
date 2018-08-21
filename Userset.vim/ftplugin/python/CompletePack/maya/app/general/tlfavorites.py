"""
Manage treeLister favorites.
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)

import pprint
import os.path
from functools import partial
import maya.cmds as cmds

_header = \
"""# This file contains favorites for a treeLister.
# To work with renderCreateBarUI it must python eval() to a list of
# 2-tuples of strings [(u"path","nodeType")]
"""

# Keep a map of item paths to storable keys, which will be stored
# along with the path
_pathToStoredKey= {}
def addPath(path, key):
    """
    Add a path to key pair.
    """
    if isinstance(path,str):
        # make sure path is unicode
        enc = cmds.about(codeset=True)
        path = path.decode(enc)
    _pathToStoredKey[path] = key

# keep track of TLFavoriteStore instances which are tracking the backed
# with the same file.  When one store updates the file, the other stores
# should be notified so that their client treeLister instances can be
# updated.
_storesByFilename = {}

def attachStore(lister, fpath):
    """
    Connects the TLFavoriteStore instance for the specified file path
    to the specified tree lister.  Populates the treeLister with the
    stored favorites.
    
    lister   - the treeLister 
    fpath    - full path to the favorites file
    """
    if _storesByFilename.has_key(fpath):
        fs = _storesByFilename[fpath]
    else:
        fs = _storesByFilename[fpath] = TLFavoriteStore(fpath)
    
    favPaths = [tpl[0] for tpl in fs.get()]
    fs._dontUpdate = True
    cmds.treeLister(lister, e=True, addFavorite = favPaths)
    fs.attachClient(lister)
    fs._dontUpdate = False
    return fs

def detachStore(lister):
    """
    Disconnects the given tree lister from the favorites store.  The
    lister will no longer be updated when the store changes.
    """
    for _,fs in _storesByFilename.iteritems():
        fs.removeClient(lister)

def readFavorites(fname):
    """
    returns the favorites from the specified file 
    as a MEL-friendly flattened list 
    ["path","key","path2","key2",...]
    """
    favorites = []
    if os.path.exists(fname): 
        try:
            favorites = eval(open(fname, 'r').read())   
        except Exception, ex:
            cmds.warning(str(ex))

    flattened = []
    for tpl in favorites:
        flattened.extend(tpl)
    return flattened

class TLFavoriteStore(object):
    """
    Manages syncing treeLister favorites to a file
    """
    def __init__(self, fname):
        self._fname = fname
        self._favorites = None
        self._clients = []
        self._dontUpdate = False

    def attachClient(self, lister):
        """
        Add a treeLister instance as a client of this favorites store.
        Any changes from the lister will propagate to other clients.
        """
        if lister not in self._clients:
            self._clients.append(lister)
            try:
                cmds.treeLister(lister, e=True, favoritesCallback=partial(self.update, lister))
            except RuntimeError,ex:
                cmds.warning(str(ex))

    def removeClient(self, lister):
        try:
            self._clients.remove(lister)
        except ValueError:
            pass

    def get(self):
        """
        returns the list of favorites
        """
        if self._favorites is None:
            if os.path.exists(self._fname): 
                try:                    
                    self._favorites = eval(open(self._fname, 'r').read())     
                except Exception, ex:
                    msg = maya.stringTable['y_tlfavorites.kProblemReadingFavoritesFile' ]
                    cmds.warning(msg.format(self._fname,str(ex)))
        if self._favorites is None:
            self._favorites = []
        return self._favorites

    def update(self,lister,path,isAdded):
        """ 
        updates the persistant favorite store 

        lister  - name of the treeLister which has added/removed the favorite
        path    - item path to be updated
        isAdded - True means add to store, False means remove
        """
        if self._dontUpdate:
            return
        item = (path, _pathToStoredKey[path])
        favs = self.get()
        if isAdded:
            if item not in favs:
                favs.append(item)
        elif item in favs:
            favs.remove(item)

        self._syncToDisk()

        # make sure we aren't re-entered
        self._dontUpdate = True

        # notify others
        for client in self._clients:
            if lister != client:
                try:
                    if isAdded:
                        cmds.treeLister(client, e=True, addFavorite=path)
                    else:
                        cmds.treeLister(client, e=True, removeFavorite=path)
                except RuntimeError,ex:
                    cmds.warning(str(ex))
                    pass
        self._dontUpdate = False

    def _syncToDisk(self):        
        try:
            with open(self._fname, 'w') as fp:
                fp.write(_header)
                fp.write('\n')
                pprint.pprint(self.get(), fp, 4, 64)
        except Exception, ex:
            cmds.warning(str(ex))
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
