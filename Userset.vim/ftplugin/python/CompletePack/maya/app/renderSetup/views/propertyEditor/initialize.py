import maya.app.renderSetup.views.propertyEditor.collection as collection
from maya.app.renderSetup.views.propertyEditor.staticCollection import StaticCollection
from maya.app.renderSetup.views.propertyEditor.basicCollection import BasicCollection
import maya.app.renderSetup.views.propertyEditor.simpleSelector as simpleSelector

import maya.app.renderSetup.views.propertyEditor.collectionFactory as collectionFactory
import maya.app.renderSetup.views.propertyEditor.selectorFactory as selectorFactory

import maya.app.renderSetup.model.collection as modelCollection
import maya.app.renderSetup.model.selector as modelSelector

_collectionEntries = {
    modelCollection.LightsCollection.kTypeName:         BasicCollection,
    modelCollection.LightsChildCollection.kTypeName:    StaticCollection,
    modelCollection.RenderSettingsCollection.kTypeName: StaticCollection,
    modelCollection.Collection.kTypeName:               collection.Collection,
    modelCollection.AOVCollection.kTypeName:            BasicCollection,
    modelCollection.AOVChildCollection.kTypeName:       BasicCollection
}

_selectorEntries = {
    modelSelector.SimpleSelector.kTypeName:    simpleSelector.SimpleSelector,
    modelSelector.BasicSelector.kTypeName:     simpleSelector.BasicSelector
}

def initialize():
    for entry in _collectionEntries.iteritems():
        collectionFactory.register(*entry)
        
    for entry in _selectorEntries.iteritems():
        selectorFactory.register(*entry)

def uninitialize():
    for entry in _collectionEntries:
        collectionFactory.unregister(entry)
        
    for entry in _selectorEntries:
        selectorFactory.unregister(entry)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
