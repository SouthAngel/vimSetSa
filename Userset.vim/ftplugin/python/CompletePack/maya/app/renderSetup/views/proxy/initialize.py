import maya.app.renderSetup.model.override as ovModel
import maya.app.renderSetup.model.connectionOverride as conOvModel
import maya.app.renderSetup.model.collection as colModel

import maya.app.renderSetup.views.proxy.proxyFactory as proxyFactory
import maya.app.renderSetup.views.proxy.renderSetup as rs

_entries = {
    colModel.LightsChildCollection.kTypeName:    rs.LightsChildCollectionProxy,
    ovModel.AbsOverride.kTypeName:               rs.AbsOverrideProxy,
    ovModel.RelOverride.kTypeName:               rs.RelOverrideProxy,
    ovModel.AbsUniqueOverride.kTypeName:         rs.AbsUniqueOverrideProxy,
    ovModel.RelUniqueOverride.kTypeName:         rs.RelUniqueOverrideProxy,
    conOvModel.ConnectionOverride.kTypeName:     rs.ConnectionOverrideProxy,
    conOvModel.ShaderOverride.kTypeName:         rs.ShaderOverrideProxy,
    conOvModel.MaterialOverride.kTypeName:       rs.MaterialOverrideProxy,
    colModel.Collection.kTypeName:               rs.CollectionProxy,
    colModel.RenderSettingsCollection.kTypeName: rs.RenderSettingsCollectionProxy,
    colModel.LightsCollection.kTypeName:         rs.LightsProxy,
    colModel.AOVCollection.kTypeName:            rs.AOVCollectionProxy,
    colModel.AOVChildCollection.kTypeName:       rs.AOVChildCollectionProxy
}

def initialize():
    for entry in _entries.iteritems():
        proxyFactory.register(*entry)

def uninitialize():
    for entry in _entries:
        proxyFactory.unregister(entry)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
