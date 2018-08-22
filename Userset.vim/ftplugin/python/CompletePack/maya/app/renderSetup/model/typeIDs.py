"""Node type IDs for render setup model nodes.

   This module centralizes type IDs for all render setup nodes.  The
   range of reserved node type IDs for render setup is 0x58000370 to
   0x580003FF, inclusive.  See file Maya/src/Plugins/NodeIdList.txt.
"""

import maya.api.OpenMaya as OpenMaya

override                = OpenMaya.MTypeId(0x58000370)
renderSetup             = OpenMaya.MTypeId(0x58000371)
renderLayer             = OpenMaya.MTypeId(0x58000372)
collection              = OpenMaya.MTypeId(0x58000373)
selector                = OpenMaya.MTypeId(0x58000374)
basicSelector           = OpenMaya.MTypeId(0x58000375)
listItem                = OpenMaya.MTypeId(0x58000376)
applyOverride           = OpenMaya.MTypeId(0x58000377)
absOverride             = OpenMaya.MTypeId(0x58000378)
applyAbsOverride        = OpenMaya.MTypeId(0x58000379)
relOverride             = OpenMaya.MTypeId(0x5800037A)
applyRelOverride        = OpenMaya.MTypeId(0x5800037B)
applyAbsFloatOverride   = OpenMaya.MTypeId(0x5800037D)
applyRelFloatOverride   = OpenMaya.MTypeId(0x5800037F)
applyAbs3FloatsOverride = OpenMaya.MTypeId(0x58000381)
applyRel3FloatsOverride = OpenMaya.MTypeId(0x58000383)
applyConnectionOverride = OpenMaya.MTypeId(0x58000384)
connectionOverride      = OpenMaya.MTypeId(0x58000385)
shaderOverride          = OpenMaya.MTypeId(0x58000386)
materialOverride        = OpenMaya.MTypeId(0x58000387)
valueOverride           = OpenMaya.MTypeId(0x58000388)
applyAbsBoolOverride    = OpenMaya.MTypeId(0x5800038A)
applyAbsEnumOverride    = OpenMaya.MTypeId(0x5800038C)
childNode               = OpenMaya.MTypeId(0x5800038D)
applyAbsIntOverride     = OpenMaya.MTypeId(0x58000391)
applyRelIntOverride     = OpenMaya.MTypeId(0x58000392)
applyAbsStringOverride  = OpenMaya.MTypeId(0x58000393)
lightsCollection        = OpenMaya.MTypeId(0x58000394)
renderSettingsCollection= OpenMaya.MTypeId(0x58000395)
applyAbs2FloatsOverride = OpenMaya.MTypeId(0x58000397)
applyRel2FloatsOverride = OpenMaya.MTypeId(0x58000399)
lightsChildCollection   = OpenMaya.MTypeId(0x5800039A)
aovCollection           = OpenMaya.MTypeId(0x5800039B)
aovChildCollection      = OpenMaya.MTypeId(0x5800039C)
simpleSelector          = OpenMaya.MTypeId(0x5800039E)

# Third party renderers will be required to provide their own selector type 
# IDs. As Arnold is an Autodesk product, we simply provide it here ourselves.
arnoldAOVChildSelector  = OpenMaya.MTypeId(0x5800039F)

absUniqueOverride       = OpenMaya.MTypeId(0x580003A0)
relUniqueOverride       = OpenMaya.MTypeId(0x580003A1)

def isRenderSetupType(typeID):
    '''
    Args:
        typeID: the MTypeId to test

    Returns: True if it is in the range of reserved RenderSetup class types otherwise False
    '''
    return typeID.id() >= 0x58000370 and typeID.id() <= 0x580003FF

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
