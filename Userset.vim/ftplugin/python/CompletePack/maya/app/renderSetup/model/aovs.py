""" 
    AOV information is encoded and decoded by 3rdParty renderers. These renderers
    register AOV callbacks by deriving from or implementing an interface identical
    to the AOVCallbacks interface located in the rendererCallbacks module. This
    class is then registered by calling:
    
    rendererCallbacks.registerCallbacks(rendererName, 
                                        rendererCallbacks.CALLBACKS_TYPE_AOVS
                                        callbacksClassImplementation)
    
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.cmds as cmds

import maya.api.OpenMaya as OpenMaya
import maya.app.renderSetup.model.rendererCallbacks as rendererCallbacks


# Errors
kRendererMismatch   = maya.stringTable['y_aovs.kRendererMismatch' ]

def _getCurrentRenderer():
    return cmds.getAttr('defaultRenderGlobals.currentRenderer')

def encode():
    ''' Encode all the attribute values related to the AOVs of a specific renderer '''

    try:
        aovsCallbacks = rendererCallbacks.getCallbacks(rendererCallbacks.CALLBACKS_TYPE_AOVS)
        if not aovsCallbacks is None:
            encodedData = aovsCallbacks.encode()
            # Encapsulate with the renderer name
            aovsData = {}
            currentRenderer = _getCurrentRenderer()
            aovsData[currentRenderer] = encodedData
            return aovsData
    except Exception as ex:
        # Control any user mistake to avoid a complete failure of the encode
        OpenMaya.MGlobal.displayError('aovs.encode() - %s' % (str(ex)))
    return dict()

def decode(aovsData, decodeType):
    ''' Decode and apply all the attribute values related to the AOVss of a specific renderer '''

    currentRenderer = _getCurrentRenderer()

    # Check if the renderer is the currently selected one 
    data = {}
    try:
        data = aovsData[currentRenderer]
    except:
        raise RuntimeError(kRendererMismatch % (currentRenderer, aovsData.keys()[0]))

    try:
        aovsCallbacks = rendererCallbacks.getCallbacks(rendererCallbacks.CALLBACKS_TYPE_AOVS)
        if not aovsCallbacks is None:
            aovsCallbacks.decode(data, decodeType)
    except Exception as ex:
        # Control any user mistake to avoid a complete failure of the decode
        OpenMaya.MGlobal.displayError('aovs.decode() - %s' % (str(ex)))
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
