""" 
    The import/export mechanism for Render Setup relies on the json library from Python 
    for the encode/decode of any kind of data types.
    
    Render settings information is comprised of multiple pieces:
    - Generic default nodes
    - Renderer specific default nodes
    - Data exported by a registered 3rdParty renderer
    
    3rdParty renderers can register to export render settings information by either 
    deriving from the RenderSettingsCallbacks class defined in the rendererCallbacks
    module, or by implementing an identical interface. This class is then registered by 
    calling:
    
    rendererCallbacks.registerCallbacks(rendererName, 
                                        rendererCallbacks.CALLBACKS_TYPE_RENDER_SETTINGS
                                        callbacksClassImplementation)
                                        
    A sample implementation of the RenderSettingsCallbacks is as follows:

    # This works because the BasicNodeExporter has the same interface as the RenderSettingsCallbacks
    class RendererRenderSettingsCallbacks(rendererCallbacks.BasicNodeExporter):
        def __init__(self):
            self.setNodes(['defaultRendererNode'])
            self.setPlugsToIgnore(['defaultRendererNode.attrToIgnore'])
            
    The above example exports the attribute values of the defaultRendererNode with the exception of the
    attribute defaultRendererNode.attrToIgnore which is being passed to the setPlugsToIgnore function call.
    Users can use a BasicNodeExporter in a similar way to specify an array of nodes to export attribute
    information from with setNodes, as well as a list of attributes to avoid exporting with the 
    setPlugsToIgnore call.

    Note: In order to ease the understanding of the json file resulting from an 'Export All' and to improve
          the long-term maintainability, the encode/decode mechanism creates a Python structure with a specific
          decomposition for the Render Settings attributes. The goal is to highlight the three pieces of data 
          that is exported so that issues can be tracked down more easily.

          The structure is:

            {
                "sceneSettings": {
                    "mayaSoftware": {
                        "userData": {},              # User defined information is here (renderer specific data)
                        "defaultNodes": {},          # Generic default nodes information is here
                        "defaultRendererNodes": {}   # Renderer specific default nodes information is here
                    }
                },
                "renderSetup": {
                }
            }
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.cmds as cmds

import maya.api.OpenMaya as OpenMaya

import maya.app.renderSetup.model.rendererCallbacks as rendererCallbacks


# Errors
kRendererMismatch   = maya.stringTable['y_renderSettings.kRendererMismatch' ]
kCreateDefaultNodesFailed = maya.stringTable['y_renderSettings.kCreateDefaultNodesFailed' ]


class VoidUserDataExporter(rendererCallbacks.RenderSettingsCallbacks):
    ''' Placeholder exporter class '''

    # Json file key for the dictionary containing all the attribute values
    _key   = 'userData'
        
class DefaultNodeExporter(rendererCallbacks.BasicNodeExporter):
    ''' Exporter to only manage the default nodes independant of the selected renderer '''

    # Json file key for the dictionary containing all the attribute values
    _key   = 'defaultNodes'
    
    def __init__(self):
        # Known default nodes applicable to any kind of renderer 
        self.setNodes(['defaultRenderQuality', 'defaultRenderGlobals', 'defaultResolution'])
        # We want to avoid exporting certain attributes
        self.setPlugsToIgnore(['defaultRenderGlobals.startFrame',
                               'defaultRenderGlobals.endFrame',
                               'defaultRenderGlobals.byFrame',
                               'defaultRenderGlobals.modifyExtension',
                               'defaultRenderGlobals.startExtension',
                               'defaultRenderGlobals.byExtension'])

class DefaultRendererNodeExporter(rendererCallbacks.BasicNodeExporter):
    ''' Exporter to only manage renderer specific default nodes '''

    # Json file key for the dictionary containing all the attribute values
    _key = 'defaultRendererNodes'

    def __init__(self, renderer, defaultNodeExporter):
        super(DefaultRendererNodeExporter, self).__init__()
        nodes = set(cmds.renderer(renderer, query=True, globalsNodes=True))
        # Compute the list of nodes specific to a renderer
        nodes.difference_update(defaultNodeExporter.getNodes())
        # Preserve the computed list
        self.setNodes(list(nodes))


# Store all exporters for all known renderers
renderSettingsExporters = dict()
voidUserDataExporter = VoidUserDataExporter()

def _registerDefaultMechanisms(renderer):
    global renderSettingsExporters

    if renderer not in renderSettingsExporters:
        renderSettingsExporters[renderer] = dict()
        defaultNodeExporter = renderSettingsExporters[renderer][DefaultNodeExporter._key] = DefaultNodeExporter()
        renderSettingsExporters[renderer][DefaultRendererNodeExporter._key] = DefaultRendererNodeExporter(renderer, defaultNodeExporter)


def _registerSelectedRender(currentRenderer):
    _registerDefaultMechanisms(currentRenderer)
    return currentRenderer

def getDefaultNodes():
    ''' Return the list of default nodes '''    
    currentRenderer = cmds.getAttr('defaultRenderGlobals.currentRenderer')
    _registerSelectedRender(currentRenderer)

    nodes  = set(renderSettingsExporters[currentRenderer][DefaultNodeExporter._key].getNodes())
    nodes |= set(renderSettingsExporters[currentRenderer][DefaultRendererNodeExporter._key].getNodes())
    try:
        global voidUserDataExporter
        renderSettingsCallbacks = rendererCallbacks.getCallbacks(currentRenderer, rendererCallbacks.CALLBACKS_TYPE_RENDER_SETTINGS)
        nodes |= set(voidUserDataExporter.getNodes() if renderSettingsCallbacks is None else renderSettingsCallbacks.getNodes())
    except Exception as ex:
        # Control any user mistake to avoid a complete failure
        OpenMaya.MGlobal.displayError('%s.getNodes() - %s' % (str(voidUserDataExporter if renderSettingsCallbacks is None else renderSettingsCallbacks), str(ex)))

    return list(nodes)


def encode():
    ''' Encode all the attribute values related to the Render Settings of a specific renderer '''
    currentRenderer = cmds.getAttr('defaultRenderGlobals.currentRenderer')
    _registerSelectedRender(currentRenderer)

    # Encode all the information
    encodedData = {}
    encodedData[DefaultNodeExporter._key]         = renderSettingsExporters[currentRenderer][DefaultNodeExporter._key].encode()
    encodedData[DefaultRendererNodeExporter._key] = renderSettingsExporters[currentRenderer][DefaultRendererNodeExporter._key].encode()
    try:
        global voidUserDataExporter
        renderSettingsCallbacks = rendererCallbacks.getCallbacks(currentRenderer, rendererCallbacks.CALLBACKS_TYPE_RENDER_SETTINGS)
        encodedData[VoidUserDataExporter._key]    = voidUserDataExporter.encode() if renderSettingsCallbacks is None else renderSettingsCallbacks.encode()
    except Exception as ex:
        # Control any user mistake to avoid a complete failure of the encode
        OpenMaya.MGlobal.displayError('%s.encode() - %s' % (str(voidUserDataExporter if renderSettingsCallbacks is None else renderSettingsCallbacks), str(ex)))

    # Encapsulate with the renderer name
    dict = {}
    dict[currentRenderer] = encodedData
    return dict


def decode(dict):
    ''' Decode and apply all the attribute values related to the Render Settings of a specific renderer '''
    currentRenderer = dict.keys()[0]
    _registerSelectedRender(currentRenderer)
    data = dict[currentRenderer]

    # Decode all the information
    #
    # Note: The order of decoding is extremely important as it allows to override any attributes.
    #       For example the user defined exporter could override any attribute already decoded 
    #       by the DefaultNodeExporter or the DefaultRendererNodeExporter implementations.
    #
    renderSettingsCallbacks = rendererCallbacks.getCallbacks(currentRenderer, rendererCallbacks.CALLBACKS_TYPE_RENDER_SETTINGS)
    if renderSettingsCallbacks is not None:
        try:
            # guard against plugin failures
            renderSettingsCallbacks.createDefaultNodes()
        except:
            OpenMaya.MGlobal.displayError(kCreateDefaultNodesFailed % currentRenderer)
    renderSettingsExporters[currentRenderer][DefaultNodeExporter._key].decode(data[DefaultNodeExporter._key])
    renderSettingsExporters[currentRenderer][DefaultRendererNodeExporter._key].decode(data[DefaultRendererNodeExporter._key])
    try:
        global voidUserDataExporter
        if renderSettingsCallbacks is None:
            voidUserDataExporter.decode(data[VoidUserDataExporter._key])
        else:        
            renderSettingsCallbacks.decode(data[VoidUserDataExporter._key])
    except Exception as ex:
        # Control any user mistake to avoid a complete failure of the decode
        OpenMaya.MGlobal.displayError('%s.decode() - %s' % (str(voidUserDataExporter if renderSettingsCallbacks is None else renderSettingsCallbacks), str(ex)))
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
