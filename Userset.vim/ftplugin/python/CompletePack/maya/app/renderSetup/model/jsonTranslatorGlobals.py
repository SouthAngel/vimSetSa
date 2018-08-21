"""
    This module contains all global variables used for Json syntax
    
    This module exists to avoid cyclic dependencies between modules.
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)



# List of all error messages
kUnknownKeys            = maya.stringTable['y_jsonTranslatorGlobals.kUnknownKeys'            ]
kMissingTypeName        = maya.stringTable['y_jsonTranslatorGlobals.kMissingTypeName'        ]
kFaultyTypeName         = maya.stringTable['y_jsonTranslatorGlobals.kFaultyTypeName'         ]
kWrongMergeType         = maya.stringTable['y_jsonTranslatorGlobals.kWrongMergeType'         ]
kUnknownTypeNode        = maya.stringTable['y_jsonTranslatorGlobals.kUnknownTypeNode'        ]
kObjectAlreadyExists    = maya.stringTable['y_jsonTranslatorGlobals.kObjectAlreadyExists'    ]
kMissingProperty        = maya.stringTable['y_jsonTranslatorGlobals.kMissingProperty'        ]
kUnknownData            = maya.stringTable['y_jsonTranslatorGlobals.kUnknownData'            ]
kTypeNodeCreationFailed = maya.stringTable['y_jsonTranslatorGlobals.kTypeNodeCreationFailed' ]


# Decoding options
DECODE_AND_ADD      = 0   # Add the imported render setup (without any namespace)
DECODE_AND_MERGE    = 1   # Merge with the existing render setup
DECODE_AND_RENAME   = 2   # Rename all imported render setup objects to not conflict with the existing render setup



# Keywords for encoding and decoding
NAME_ATTRIBUTE_NAME              = 'name'
IMPORTED_ATTRIBUTE_NAME          = 'imported'
NOTES_ATTRIBUTE_NAME             = 'notes'
LAYERS_ATTRIBUTE_NAME            = 'renderLayers'
COLLECTIONS_ATTRIBUTE_NAME       = 'collections'
VISIBILITY_ATTRIBUTE_NAME        = 'isVisible'
CHILDREN_ATTRIBUTE_NAME          = 'children'
SCENE_SETTINGS_ATTRIBUTE_NAME    = 'sceneSettings'
SELECTOR_ATTRIBUTE_NAME          = 'selector'
SCENE_AOVS_ATTRIBUTE_NAME        = 'sceneAOVs'




def computeValidObjectName(dict, mergeType, prependToName, objectTypeName):
    # Ensure that the name could not be None or empty
    newName = dict[NAME_ATTRIBUTE_NAME] if NAME_ATTRIBUTE_NAME in dict else objectTypeName
    newName = newName if newName is not None and newName is not '' else objectTypeName
    # Prepend the string selected by the user 
    newName = (prependToName if mergeType==DECODE_AND_RENAME and prependToName is not None else '') + newName
    return newName


# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
