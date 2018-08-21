"""
    This module contains all the utility methods used for Json syntax
    
    Please have a look to http://json.org/ for the detailed Json syntax
    and the official documentation is http://www.ecma-international.org/publications/files/ECMA-ST/ECMA-404.pdf

"""

import maya.app.renderSetup.model.jsonTranslatorGlobals as jsonTranslatorGlobals
import maya.app.renderSetup.model.rendererCallbacks as rendererCallbacks


def _isRenderSetup(encodedData):
    return isinstance(encodedData, dict) and jsonTranslatorGlobals.SCENE_SETTINGS_ATTRIBUTE_NAME in encodedData


def isRenderSetupTemplate(encodedData):
    return isinstance(encodedData, list) and isinstance(encodedData[0], dict)

    
def encodeObjectArray(objects):
    """
        Encode an array of Render Setups Object as a list for the Json default encoder
    """
    result = list()
    for obj in objects:
        result.append(obj.encode())
    return result


def isRenderSetup(encodedData):
    """
        Is the encodedData defining a Render Setup ?
        Note: The test is not foolproof but should segregate obvious unrelated data
    """
    return _isRenderSetup(encodedData) or isRenderSetupTemplate(encodedData)


def getTypeNameFromDictionary(encodedData):
    """
        Get the root typename stored in the dictionary
        Note: Any node encoding always first encapsulates its data in a dictionary
              where the key is the node type.
    """
    return encodedData.keys()[0] if isinstance(encodedData, dict) else None


def getObjectNotes(encodedData):
    """
        Get the Notes from any Render Setup Object knowing that all nodes
        could or not contain the 'notes' dynamic attribute.
    """
    if _isRenderSetup(encodedData):
        keys = set(encodedData.keys())
        keys.remove(jsonTranslatorGlobals.SCENE_SETTINGS_ATTRIBUTE_NAME)
        data = encodedData[list(keys)[0]]
        if jsonTranslatorGlobals.NOTES_ATTRIBUTE_NAME in data.keys():
            return data[jsonTranslatorGlobals.NOTES_ATTRIBUTE_NAME]

    if isRenderSetupTemplate(encodedData):
        data = encodedData[0]        # Arbitrary choice
        data = data[data.keys()[0]]  # Jump over the node type
        if jsonTranslatorGlobals.NOTES_ATTRIBUTE_NAME in data.keys():
            return data[jsonTranslatorGlobals.NOTES_ATTRIBUTE_NAME]

    return ''


class MergePolicy(object):
    """
        The class is the policy to manage a new object instance when decoding a list 
        of render setup object depending of the merge type.
    """
    def __init__(self, getFn, createFn, mergeType, prependToName):
        self._getFn    = getFn               # The function to get the object instance by name
        self._createFn = createFn            # The function to create & attach the object instance 
        self._mergeType = mergeType          # The merge type
        self._prependToName = prependToName  # string to prepend to any 'unexpected' render setup objects
                                             #    Note: It could be a string (i.e. 'Imported_') or a namespace (i.e. 'Imported:')
                                             
    def _getAOVArgs(self, dict, typeName):
        callbacks = rendererCallbacks.getCallbacks(rendererCallbacks.CALLBACKS_TYPE_AOVS)
        aovNode = callbacks.getChildCollectionSelectorAOVNodeFromDict(dict)
        aovName = callbacks.getAOVName(aovNode)
        return {'aovName' : aovName}
                                             
    def create(self, dict, typeName):
        newName = jsonTranslatorGlobals.computeValidObjectName(dict, self._mergeType, self._prependToName, typeName)

        if self._mergeType==jsonTranslatorGlobals.DECODE_AND_MERGE:
            """ 
                The merge mode requests to merge the imported object to the current object 
                if object already exists. In any other case, it creates a new object instance.
            """
            try:
                # The object already exists so use it
                return self._getFn(newName)
            except:
                pass
            # The object does not exist so create a new one with the computed name
            if typeName == "aovChildCollection":
                return self._createFn(newName, typeName, self._getAOVArgs(dict, typeName))
            else:
                return self._createFn(newName, typeName)
        elif self._mergeType==jsonTranslatorGlobals.DECODE_AND_RENAME or self._mergeType==jsonTranslatorGlobals.DECODE_AND_ADD:
            """ 
                These two merge types need to create a new object
            """
            if typeName == "aovChildCollection":
                return self._createFn(newName, typeName, self._getAOVArgs(dict, typeName))
            else:
                return self._createFn(newName, typeName)
        else:
            raise Exception(jsonTranslatorGlobals.kWrongMergeType % self._mergeType)
                

def decodeObjectArray(list, policy):
    """
        Decode an array of Render Setups Objects

        list is a list of dictionaries (json representation for a array of objects)
        policy encapsulates the behavior to create the render setup object instance based on the merge type
    """
    for d in list:
        keys = d.keys()
        nbKeys = len(keys)
        if nbKeys==0:
            raise SyntaxError(jsonTranslatorGlobals.kMissingTypeName)
        # If we have more than one key, then we better have two keys, one of 
        # which is 'parentTypeName' which indicates that we are doing a 
        # copy&paste
        elif nbKeys>2 or (nbKeys==2 and 'parentTypeName' not in d):
            raise SyntaxError(jsonTranslatorGlobals.kUnknownKeys % str(keys))
        nodeTypeName = keys[0]

        objInst = policy.create(d[nodeTypeName], nodeTypeName)
        if not objInst:
            raise SyntaxError(jsonTranslatorGlobals.kTypeNodeCreationFailed % nodeTypeName)
        elif objInst.typeName()!= nodeTypeName:
            raise SyntaxError(jsonTranslatorGlobals.kUnknownTypeNode % (objInst.typeName(), nodeTypeName))

        objInst.decode(d[nodeTypeName], policy._mergeType, policy._prependToName)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
