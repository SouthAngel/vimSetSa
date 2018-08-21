"""
    This module defines a base class to manage the notes which is a dynamic attribute for any DG Nodes.
"""

import maya.cmds as cmds

import maya.api.OpenMaya as OpenMaya

import maya.app.renderSetup.model.jsonTranslatorGlobals as jsonTranslatorGlobals


_NOTES_ATTRIBUTE_SHORT_NAME = 'nts'


class NodeNotes(object):
    """ 
        The class adds the support to the notes dynamic attribute.
    """

    def __init__(self):
        super(NodeNotes, self).__init__()

    def _hasNotesPlug(self):
        return OpenMaya.MFnDependencyNode(self.thisMObject()).hasAttribute(jsonTranslatorGlobals.NOTES_ATTRIBUTE_NAME)

    def _getNotesPlug(self):
        if not self._hasNotesPlug():
            # Use the command in order to allow undo/redo
            cmds.addAttr(self.name(), shortName=_NOTES_ATTRIBUTE_SHORT_NAME, longName=jsonTranslatorGlobals.NOTES_ATTRIBUTE_NAME, dataType='string')
        return OpenMaya.MFnDependencyNode(self.thisMObject()).findPlug(jsonTranslatorGlobals.NOTES_ATTRIBUTE_NAME, True)

    def getNotes(self):
        # None means that no notes attribute is present on this specific node
        return self._getNotesPlug().asString() if self._hasNotesPlug() else None

    def setNotes(self, string):
        if string is None:
            cmds.deleteAttr(self.name(), at=NOTES_ATTRIBUTE_NAME)
        else:
            self._getNotesPlug().setString(string)

    def _encodeProperties(self, dict):
        if self._hasNotesPlug() and self.getNotes()!='':
            dict[self._getNotesPlug().partialName(useLongNames=True)] = self.getNotes()

    def _decodeProperties(self, dict, mergeType, prependToName):
        if self._getNotesPlug().partialName(useLongNames=True) in dict:
            self.setNotes(dict[self._getNotesPlug().partialName(useLongNames=True)])
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
