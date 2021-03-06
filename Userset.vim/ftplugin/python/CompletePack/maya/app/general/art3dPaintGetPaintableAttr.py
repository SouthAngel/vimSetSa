import maya
maya.utils.loadStringResourcesForModule(__name__)

from maya import cmds
import sys

# ==============
# File Globals
# ==============
# Dict to convert attribute names to friendly (and localized) label names
_dict_attributeToPaint_melToUI = {
    'color' : maya.stringTable[ 'y_art3dPaintGetPaintableAttr.kColor'            ],
    'transparency' : maya.stringTable[ 'y_art3dPaintGetPaintableAttr.kTransparency'     ],
    'incandescence' : maya.stringTable[ 'y_art3dPaintGetPaintableAttr.kIncandescence'    ],
    'normalCamera' : maya.stringTable[ 'y_art3dPaintGetPaintableAttr.kBumpMap'          ],
    'specularColor' : maya.stringTable[ 'y_art3dPaintGetPaintableAttr.kSpecularColor'    ],
    'reflectivity' : maya.stringTable[ 'y_art3dPaintGetPaintableAttr.kReflectivity'     ],
    'ambientColor' : maya.stringTable[ 'y_art3dPaintGetPaintableAttr.kAmbient'          ],
    'diffuse' : maya.stringTable[ 'y_art3dPaintGetPaintableAttr.kDiffuse'          ],
    'translucence' : maya.stringTable[ 'y_art3dPaintGetPaintableAttr.kTranslucence'     ],
    'reflectedColor' : maya.stringTable[ 'y_art3dPaintGetPaintableAttr.kReflectedColor'   ],
    'displacement' : maya.stringTable[ 'y_art3dPaintGetPaintableAttr.kDisplacement'     ],
}
# Reverse lookup for dict_attrNameToLabelName
_dict_attributeToPaint_uiToMel = dict([(v,k) for k,v in _dict_attributeToPaint_melToUI.items()])


def attributeToPaint_uiToMel(value):
    # The resource strings in art3dPaintGetPaintableAttr_res.py are unicode, to match with them
    # we need to convert the non-unicode string "value" to a unicoded one.
    sysEncoding = sys.getfilesystemencoding()
    return _dict_attributeToPaint_uiToMel.get(unicode(value, sysEncoding))

def attributeToPaint_melToUI(value):
    return _dict_attributeToPaint_melToUI.get(value, value)


def art3dPaintGetPaintableAttr(allowCustomAttrs=True):
    '''Return list of all the names of 
    all color attrs common (to all selected shader) paintable attributes.
    This includes custom attributes.
    '''

    shaderPaintableAttrs = []
    # Start with list of standard paintable attrs supplied by art3dPaintCtx (if not allowing custom attrs)
    explicitPaintableAttrs = set([str(attr) for attr in cmds.art3dPaintCtx(cmds.currentCtx(), q=True, attrnames=True).split()])
    if not allowCustomAttrs:
        shaderPaintableAttrs.append(explicitPaintableAttrs)
   
    # Retrieve paintable attrs from each shader    
    shaders = cmds.art3dPaintCtx(cmds.currentCtx(), q=True, shadernames=True).split()
    shaderTypesWithDisplacement = set([
        'lambert',
        'blinn',
        'phong',
        'phongE',
        'anisotropic',
        ])
    attrTypes = set([
        'float',
        'double',
        'float3',
        'double3',
        ])
    nonPaintableAttrs = set([
        'hardwareShader',
        ])
    for shader in shaders:
        # attrs explicitly specified or user-defined float,float3,double,double3 attrs
        paintableAttrs = cmds.attributeInfo(shader, logicalAnd=True, writable=True, leaf=False, bool=False, enumerated=False, hidden=False)
        paintableAttrs = set([str(attr) for attr in paintableAttrs if ((attr in explicitPaintableAttrs) or (cmds.listAttr(shader, userDefined=True, st=attr) and (cmds.getAttr('%s.%s'%(shader,attr), type=True) in attrTypes)))])
        paintableAttrs -= nonPaintableAttrs  # omit attrs explicitly listed to omit
        if cmds.nodeType(shader) in shaderTypesWithDisplacement:
            paintableAttrs.add('displacement')
        shaderPaintableAttrs.append(paintableAttrs)
    
    # Determine attrs common to all selected shaders
    if len(shaderPaintableAttrs) > 0:
        commonPaintableAttrs = set.intersection(*shaderPaintableAttrs)
    else:
        commonPaintableAttrs = ''
        
    return commonPaintableAttrs
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
