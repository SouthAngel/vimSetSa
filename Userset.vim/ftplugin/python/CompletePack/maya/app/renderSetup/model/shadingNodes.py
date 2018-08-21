'''
This module defines the hardware shaders for the apply override nodes from render setup.

The apply override nodes that may be inserted in a shading network are divided into two families:
 - absolute override
 - relative override
and they can output the following types:
 - float, float2, float3
 - int, int2, int3
 - enum (absolute only)
 - bool (absolute only)
 - string (absolute only)
and they can be enabled or not.

Absolute overrides have the following inputs:
 - an original value (original)
 - an override value (attrValue)
 - an enabled bool (enabled)
In pseudo code, their output would be evaluated as:
  out = enabled? attrValue : original;
  
Relative overrides have the following inputs:
 - an original value (original)
 - a multiply value (multiply)
 - an offset value (offset)
 - an enabled bool (enabled)
 In pseudo code, their output would be evaluated as:
  out = enabled? original * multiply + offset : original;

Plugin renderers need to translate these nodes in order for their shading network to be evaluated accurately.

IMPORTANT:

Apply override nodes are connected to override nodes.
Override nodes define the override parameters (attrValue (absolute), offset, multiply (relative)).
Apply overrides are a specific application of the override on a specific target node, since an override can apply to one or more targets. They read the 
parameters from the override nodes and these parameters are readable AND writable attributes (in and out).
They are NOT computed by the override node but simply "forwarded" to the apply override nodes.
They may have SOURCE CONNECTIONS or be KEYED though. This means that the override nodes don't need to be translated
since they do not compute the outputs. But the override node's sources must be translated and connected to the translated apply override 
in order to be well evaluated.

Example:
                                                                                 
                                                                                 
  -----------      ---------------      --------------         --------------    
 | SOME NODE |    |  ABSOLUTE OV  |    | APPLY ABS OV |       | A SHADING NODE | 
 |           |    |               |    |              |       |                | 
 o someIn    |    |               |    o original     |   /---o anAttribute    | 
 |   someOut o----o attrValue     o----o attrValue    |   |   o <other attrs>  | 
 |           |    o enabled       o----o enabled      |   |   |                | 
 |           |    |               |    |       output o---/   |      <outputs> o 
  -----------      ---------------      --------------         ----------------  
                                                                                 
                                                                                 
'''


import maya.api.OpenMaya as OpenMaya
import maya.api.OpenMayaRender as OpenMayaRender
import maya.cmds as cmds
import maya.app.renderSetup.model.plug as plug
import maya.app.renderSetup.model.typeIDs as typeIDs
import itertools

class ApplyOverrideShadingNodeOverride(OpenMayaRender.MPxShadingNodeOverride):
    '''Base class for shading node overrides for the apply override nodes.
    Subclasses only provide the fragment body template to be filled in with template args.'''
    
    _plugTypeToTemplateArgs = { key:value for (key, value) in itertools.chain(
        ((ptype, ('float', '0', 'float', 'float', 'float')) for ptype in (
            plug.Plug.kFloat, plug.Plug.kDouble, plug.Plug.kTime, plug.Plug.kAngle, plug.Plug.kDistance)),
        ((ptype, ('int', '0', 'int', 'int', 'int')) for ptype in (
            plug.Plug.kInt, plug.Plug.kByte, plug.Plug.kEnum)),
        ((ptype, ('bool', '0', 'bool', 'bool', 'bool')) for ptype in (
            plug.Plug.kBool,)),
        ((ptype, ('float3', '0,0,0', 'float3', 'float3', 'vec3')) for ptype in (
            plug.Plug.kColor,)))
    }
    
    @classmethod
    def _getTemplateArgs(cls, obj):
        '''Returns a dictionary mapping the template arg name to its replacement for the input MObject 
        to create a shading node override for.
        Keys are : ('propertyType', 'propertyValue', 'cgType', 'hlslType', 'glslType')
        => {propertyType} in the fragment template will be replaced by its mapped value, and so on.'''
        
        plg = plug.Plug(OpenMaya.MFnDependencyNode(obj).userNode().getOriginalPlug())
        
        keys = ('propertyType', 'propertyValue', 'cgType', 'hlslType', 'glslType')
        values = ApplyOverrideShadingNodeOverride._plugTypeToTemplateArgs[plg.type] \
            if not plg.isVector else \
            { 2 : ('float2', '0,0', 'float2', 'float2', 'vec2'),
              3 : ('float3', '0,0,0', 'float3', 'float3', 'vec3')}[len(plg.type)]
        
        args = { key:value for key,value in itertools.izip(keys, values) }
        args['fragmentName'] = cls.__name__ + str(args['propertyType']) + "Fragment"
        return args
    
    @classmethod
    def creator(cls, obj):
        return cls(obj)
        
    def __init__(self, obj):
        super(ApplyOverrideShadingNodeOverride, self).__init__(obj)
        
        args = self._getTemplateArgs(obj)
        self._fragmentName = args['fragmentName']
        
        fragmentMgr = OpenMayaRender.MRenderer.getFragmentManager()
        if fragmentMgr is not None and not fragmentMgr.hasFragment(self._fragmentName):
            fragmentBody = self._getFragmentTemplate().format(**args)
            fragmentMgr.addShadeFragmentFromBuffer(fragmentBody, False)
        
    def supportedDrawAPIs(self):
        return OpenMayaRender.MRenderer.kOpenGL | OpenMayaRender.MRenderer.kOpenGLCoreProfile | OpenMayaRender.MRenderer.kDirectX11

    def fragmentName(self):
        return self._fragmentName


class ApplyAbsOverrideShadingNodeOverride(ApplyOverrideShadingNodeOverride):
    @staticmethod
    def _getFragmentTemplate():
        return '''
<fragment uiName="{fragmentName}" name="{fragmentName}" type="plumbing" class="ShadeFragment" version="1.0">
    <properties>
        <{propertyType} name="original" />
        <{propertyType} name="value" />
        <bool name="enabled" />
    </properties>"
    <values>"
        <{propertyType} name="original" value="{propertyValue}" />
        <{propertyType} name="value" value="{propertyValue}" />
    </values>
    <outputs>
        <{propertyType} name="out" />
    </outputs>
    <implementation>
    <implementation render="OGSRenderer" language="Cg" lang_version="2.1">
        <function_name val="{fragmentName}" />
        <source><![CDATA[
{cgType} {fragmentName}({cgType} original, {cgType} value, bool enabled) 
{{ 
    return enabled? value : original;
}} ]]>
        </source>
    </implementation>
    <implementation render="OGSRenderer" language="HLSL" lang_version="11.0">
        <function_name val="{fragmentName}" />
        <source><![CDATA[
{hlslType} {fragmentName}({hlslType} original, {hlslType} value, bool enabled)
{{
   return enabled? value : original;
}} ]]>
        </source>
    </implementation>
    <implementation render="OGSRenderer" language="GLSL" lang_version="3.0">
        <function_name val="{fragmentName}" />
        <source><![CDATA[
{glslType} {fragmentName}({glslType} original, {glslType} value, bool enabled)
{{ 
    return enabled? value : original;
}} ]]>
        </source>
    </implementation>
    </implementation>
</fragment>'''


class ApplyRelOverrideShadingNodeOverride(ApplyOverrideShadingNodeOverride):
    @staticmethod
    def _getFragmentTemplate():
        return '''
<fragment uiName="{fragmentName}" name="{fragmentName}" type="plumbing" class="ShadeFragment" version="1.0">
    <properties>
        <{propertyType} name="original" />
        <{propertyType} name="multiply" />
        <{propertyType} name="offset" />
        <bool name="enabled" />
    </properties>"
    <values>"
        <{propertyType} name="original" value="{propertyValue}" />
        <{propertyType} name="multiply" value="{propertyValue}" />
        <{propertyType} name="offset" value="{propertyValue}" />
    </values>
    <outputs>
        <{propertyType} name="out" />
    </outputs>
    <implementation>
    <implementation render="OGSRenderer" language="Cg" lang_version="2.1">
        <function_name val="{fragmentName}" />
        <source><![CDATA[
{cgType} {fragmentName}({cgType} original, {cgType} multiply, {cgType} offset, bool enabled) 
{{ 
    return enabled? (original * multiply + offset) : original;
}} ]]>
        </source>
    </implementation>
    <implementation render="OGSRenderer" language="HLSL" lang_version="11.0">
        <function_name val="{fragmentName}" />
        <source><![CDATA[
{hlslType} {fragmentName}({hlslType} original, {hlslType} multiply, {hlslType} offset, bool enabled)
{{
   return enabled? (original * multiply + offset) : original;
}} ]]>
        </source>
    </implementation>
    <implementation render="OGSRenderer" language="GLSL" lang_version="3.0">
        <function_name val="{fragmentName}" />
        <source><![CDATA[
{glslType} {fragmentName}({glslType} original, {glslType} multiply, {glslType} offset, bool enabled)
{{ 
    return enabled? (original * multiply + offset) : original;
}} ]]>
        </source>
    </implementation>
    </implementation>
</fragment>'''


_classifToTypeIds = {
    "drawdb/shader/applyAbsOverride" : { 
        typeIDs.applyAbsFloatOverride.id(),
        typeIDs.applyAbs2FloatsOverride.id(),
        typeIDs.applyAbs3FloatsOverride.id(),
        typeIDs.applyAbsBoolOverride.id(),
        typeIDs.applyAbsEnumOverride.id(),
        typeIDs.applyAbsIntOverride.id() },
    "drawdb/shader/applyRelOverride" : {
        typeIDs.applyRelFloatOverride.id(),
        typeIDs.applyRel2FloatsOverride.id(),
        typeIDs.applyRel3FloatsOverride.id(),
        typeIDs.applyRelIntOverride.id() },
    "drawdb/shader/override" : {
        typeIDs.absOverride.id(),
        typeIDs.relOverride.id()
    }    
}

def getDrawdbClassification(typeid):
    for classif, typeids in _classifToTypeIds.iteritems():
        if typeid in typeids:
            return classif
    return None


_classifToCreator = {
    "drawdb/shader/applyAbsOverride" : ApplyAbsOverrideShadingNodeOverride.creator,
    "drawdb/shader/applyRelOverride" : ApplyRelOverrideShadingNodeOverride.creator
}

def initialize():
    for classif, creator in _classifToCreator.iteritems():
        try:
            OpenMayaRender.MDrawRegistry.registerShadingNodeOverrideCreator(classif, "renderSetupPlugin", creator)
        except:
            cmds.error("Failed to register shading node override for %s." % classif)

def uninitialize():
    for classif in _classifToCreator.iterkeys():
        try:
            OpenMayaRender.MDrawRegistry.deregisterShadingNodeOverrideCreator(classif, "renderSetupPlugin")
        except:
            cmds.error("Failed to deregister shading node override for %s." % classif)
            

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
