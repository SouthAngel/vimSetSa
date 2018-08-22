import maya
maya.utils.loadStringResourcesForModule(__name__)

import maya.mel as mel

import maya.api.OpenMaya as OpenMaya

import maya.app.renderSetup.common.utils as commonUtils

import maya.app.renderSetup.model.plug as plug
import maya.app.renderSetup.model.jsonTranslatorGlobals as jsonTranslatorGlobals

# List of callbacks types
CALLBACKS_TYPE_RENDER_SETTINGS = 0
CALLBACKS_TYPE_AOVS = 1

# Errors
kDefaultNodeMissing = maya.stringTable['y_rendererCallbacks.kDefaultNodeMissing' ]
kDefaultNodeAttrMissing = maya.stringTable['y_rendererCallbacks.kDefaultNodeAttrMissing' ]

# Renderers should either extend this class or create a class with the same signature to provide additional render settings callbacks
class RenderSettingsCallbacks(object):
    
     # Encodes any renderer specific render settings data
    def encode(self):
        return {}
        
     # Decodes any renderer specific render settings data
    def decode(self, rendererData):
        pass
    
    # Returns the default render settings nodes for the specific renderer
    def getNodes(self):
        return []
        
    # Create the default nodes for the specific renderer
    def createDefaultNodes(self):
        pass

# Renderers should either extend this class or create a class with the same signature to provide additional AOV callbacks
class AOVCallbacks(object):
    DECODE_TYPE_OVERWRITE = jsonTranslatorGlobals.DECODE_AND_ADD
    DECODE_TYPE_MERGE     = jsonTranslatorGlobals.DECODE_AND_MERGE

     # Encodes the AOV information into some format
    def encode(self):
        return {}
     
     # Decodes the AOV information from some format
     # aovsData   - The AOV data to decode
     # decodeType - Overwrite, Merge
    def decode(self, aovsData, decodeType):
        pass
    
    # This function is called to display the AOV information for the current renderer
    def displayMenu(self):
        pass

    # From a given AOV node, returns the AOV name
    def getAOVName(self, aovNode):
        return ""
        
    # This function is called to create the selector for the AOV collection
    def getCollectionSelector(self, selectorName):
        return None

    # This function is called to create the selector for the AOV child collection
    def getChildCollectionSelector(self, selectorName, aovName):
        return None
    
    # This function returns the child selector AOV node name from the provided dictionary
    def getChildCollectionSelectorAOVNodeFromDict(self, d):
        return None

# Helper exporter to encode/decode any nodes
class NodeExporter(object):
    _plugsToIgnore = []

    def encode(self):
        attrs = {}
        for name in self.getNodes():
            node = commonUtils.nameToNode(name)
            nodeFn = None
            try:
                nodeFn = OpenMaya.MFnDependencyNode(node)
            except:
                # No guarantee that the default node exist
                OpenMaya.MGlobal.displayWarning(kDefaultNodeMissing % name)
            else:
                for attrIdx in xrange(nodeFn.attributeCount()):
                    plg = plug.Plug(node, nodeFn.attribute(attrIdx))
                    if plg.type is not plug.Plug.kInvalid and plg.name not in self._plugsToIgnore:
                        attrs[plg.name] = plg.value
        return attrs

    def decode(self, encodedData):
        nodes = {} # Avoid creating several time the same node
        for (key, value) in encodedData.items():
            (nodeName, attrName) = plug.Plug.getNames(key)
            node = None
            if nodeName in nodes:
                node = nodes[nodeName]
            else:
                try:
                    node = commonUtils.nameToNode(nodeName)
                    OpenMaya.MFnDependencyNode(node)
                except:
                    node = None
                nodes[nodeName] = node

            if node is None:
                # No guarantee that the default node exist
                OpenMaya.MGlobal.displayWarning(kDefaultNodeMissing % nodeName)
            else:
                plg = plug.findPlug(nodeName, attrName)
                if plg is None:
                    OpenMaya.MGlobal.displayWarning(kDefaultNodeAttrMissing % (nodeName, attrName))
                else:
                    plg.value = value

    def setPlugsToIgnore(self, plugsToIgnore):
        self._plugsToIgnore = plugsToIgnore
                
# Exporter that is used to export the nodes that have been set
class BasicNodeExporter(NodeExporter):
    _nodes = []

    def setNodes(self, nodes):
        self._nodes = nodes

    def getNodes(self):
        return self._nodes


global rendererCallbacks
rendererCallbacks = {}
def registerCallbacks(renderer, callbacksType, callbacks):
    if not renderer in rendererCallbacks:
        rendererCallbacks[renderer] = dict()
    rendererCallbacks[renderer][callbacksType] = callbacks

def unregisterCallbacks(renderer, callbacksType=None):
    if callbacksType == None:
        del rendererCallbacks[renderer]
    else:
        del rendererCallbacks[renderer][callbacksType]
    
def getCallbacks(*args):
    if len(args) == 1:
        renderer =  mel.eval("currentRenderer()")
        callbacksType = args[0]
    else:
        renderer = args[0]
        callbacksType = args[1]
        
    return None if not renderer in rendererCallbacks or \
        not callbacksType in rendererCallbacks[renderer] \
        else rendererCallbacks[renderer][callbacksType]
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
