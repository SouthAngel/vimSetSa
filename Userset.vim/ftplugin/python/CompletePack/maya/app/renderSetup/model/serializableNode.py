"""
    This module defines a base class to all serializable render setup nodes.
"""

import maya.app.renderSetup.model.jsonTranslatorGlobals as jsonTranslatorGlobals


class SerializableNode(object):

    def __init__(self):
        super(SerializableNode, self).__init__()

    def encode(self, notes=None):
        result = dict()
        result[self.typeName()] = dict()
        
        result[self.typeName()][jsonTranslatorGlobals.NAME_ATTRIBUTE_NAME] = self.name()   
        
        self._encodeProperties(result[self.typeName()])
        
        # If the user provides some notes, those are the ones to be saved
        if notes is not None and len(notes)>=1:
            result[self.typeName()][jsonTranslatorGlobals.NOTES_ATTRIBUTE_NAME] = notes

        return result

    def decode(self, dict, mergeType, prependToName):
        self._decodeProperties(dict, mergeType, prependToName)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
