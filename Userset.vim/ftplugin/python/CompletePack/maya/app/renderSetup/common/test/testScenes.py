import maya.cmds as cmds
import maya.mel as mel
from collections import namedtuple

# named tuple to hold all information about the instances needed for the tests
Material = namedtuple('Material', 'shadingEngine surfaceShader displacementShader volumeShader')
Material.__new__.__defaults__ = (None,) * len(Material._fields)

Instance = namedtuple('Instance', 'transform shape generator materials')
Instance.__new__.__defaults__ = (None,) * (len(Instance._fields)-1) + ((),)

DefaultMaterial = Material(shadingEngine='initialShadingGroup', surfaceShader='lambert1')

def createSurfaceShader(color):
    '''
    Creates a Surface Shader with the specified color.
    Returns a tuple (shaderName, shadingEngineName)
    '''
    shaderName = cmds.shadingNode('surfaceShader', asShader=True)
    sgName = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=(shaderName + "SG"))
    cmds.connectAttr(shaderName + ".outColor", sgName + ".surfaceShader")
    cmds.setAttr(shaderName+".outColor", color[0], color[1], color[2], type="float3")
    return Material(shadingEngine=sgName, surfaceShader=shaderName)

def assignShadingEngine(shape, shadingEngine, components=None):
    '''
    Assign shading engine to shape.
    "components" is an optional list of mesh face indices or nurbs surface patch indices
    that can be used to specify per-face shading engine assignment.
    A mesh index is given by an integer >= 0.
    A surface patch is given by a tuple (span, section) where span and section are integers >= 0.
    '''
    selection = [shape]
    if components:
        funct = None
        if cmds.objectType(shape, isAType='mesh'): 
            funct = lambda face: 'f[%d]' % face
        elif cmds.objectType(shape, isAType='nurbsSurface'): 
            funct = lambda (span,section) : 'sf[%d][%d]' % (span,section)
        else: 
            raise RuntimeError('Unsupported shape type for shader assignment')
        selection = [shape+"."+funct(component) for component in components]
    cmds.select(selection, replace=True)
    cmds.sets(edit=True, forceElement=shadingEngine)
    cmds.select(clear=True)

def createSceneWithMaterials():
    '''
    Create a test scene composed of
    - 2 polySphere (instances of the same shape)
    - 2 nurbsSphere (instances of the same shape)
    First instance has whole shape material assignment.
    Second instance has per-face shape material assignment.
    - 1 polyCube without any per-face
    - 1 directionalLight
    
    Returns a set of Instance (named tuples) containing these 6 objects.
    
    To see it in maya, just run python script:
    import maya.app.renderSetup.common.test.testScenes as scenes; scenes.createSceneWithMaterials()
    '''
    
    # create 3 different surface shaders
    material1 = createSurfaceShader([1,0,0])
    material2 = createSurfaceShader([0,1,0])
    material3 = createSurfaceShader([0,0,1])
    
    # create two instances of a poly sphere
    transform1, generator = cmds.polySphere()
    shape1 = cmds.listRelatives(transform1, fullPath=True)[0]
    transform2 = cmds.instance(transform1)[0]
    shape2 = cmds.listRelatives(transform2, fullPath=True)[0]
    
    # assign shader1 to |pSphere1|pSphereShape1
    # assign shader2 to |pSphere2|pSphereShape1 and shader3 per-face for faces [0,100[
    assignShadingEngine(shape1, material1.shadingEngine)
    assignShadingEngine(shape2, material2.shadingEngine)
    assignShadingEngine(shape2, material3.shadingEngine, range(0,100))
    
    poly1 = Instance(transform="|"+transform1, shape=shape1, generator=generator, materials=(material1,))
    poly2 = Instance(transform="|"+transform2, shape=shape2, generator=generator, materials=(material2,material3))
    
    # create two instances of a nurbs sphere
    transform1, generator = cmds.sphere()
    shape1 = cmds.listRelatives(transform1, fullPath=True)[0]
    transform2 = cmds.instance(transform1)[0]
    shape2 = cmds.listRelatives(transform2, fullPath=True)[0]
    
    # assign shader1 to |nurbsSphere1|nurbsSphereShape1
    # assign shader2 to |nurbsSphere2|nurbsSphereShape1 and shader3 per-face for patches span=[0,2[, sections=[0,8[
    assignShadingEngine(shape1, material1.shadingEngine)
    assignShadingEngine(shape2, material2.shadingEngine)
    assignShadingEngine(shape2, material3.shadingEngine, ((i,j) for i in range(0,2) for j in range(0,8)))
    
    nurbs1 = Instance(transform="|"+transform1, shape=shape1, generator=generator, materials=(material1,))
    nurbs2 = Instance(transform="|"+transform2, shape=shape2, generator=generator, materials=(material2,material3))
    
    # create an instance without any per-face
    transform1, generator = cmds.polyCube()
    shape1 = cmds.listRelatives(transform1, fullPath=True)[0]
    cube = Instance(transform="|"+transform1, shape=shape1, generator=generator, materials=(DefaultMaterial,))
    
    # create an instance that doesn't have generators nor assigned shading engines
    mel.eval("defaultDirectionalLight(1, 1,1,1, \"0\", 0,0,0, 0)")
    light = Instance(transform='|directionalLight1', shape='|directionalLight1|directionalLightShape1')
    
    cmds.select(clear=True)
    
    # translate (for no reasons really, just to see it better in maya ^_^)
    instances = [poly1, poly2, nurbs1, nurbs2, cube, light]
    for i, instance in enumerate(instances):
        cmds.setAttr(instance.transform+".translateX", 2.5*i)
    
    return set(instances)

def createAllShaders():
    '''
    place2dTexture# ----> noise# ----> bump# ----> blinn# ----\ 
                                      displacementShader# ----- shadingGroup#
                                               volumeFog# ----/
    '''
    shadingGroup = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="shadingGroup1")
    
    surface = cmds.shadingNode('blinn', asShader=True)
    cmds.connectAttr(surface+".outColor", shadingGroup+".surfaceShader")
    bump = cmds.shadingNode('bump2d', asUtility=True)
    cmds.connectAttr(bump+'.outNormal', surface+'.normalCamera')
    noise = cmds.shadingNode('noise', asTexture=True)
    cmds.setAttr(noise+".alphaIsLuminance", True)
    cmds.connectAttr(noise+'.outAlpha', bump+'.bumpValue')
    placeTexture = cmds.shadingNode('place2dTexture', asUtility=True)
    cmds.connectAttr(placeTexture+".outUV", noise+".uv")
    cmds.connectAttr(placeTexture+".outUvFilterSize", noise+".uvFilterSize")
    
    volumeFog = cmds.shadingNode('volumeFog', asShader=True)
    cmds.connectAttr(volumeFog+".outColor", shadingGroup+".volumeShader")
    
    displacement = cmds.shadingNode('displacementShader', asShader=True)
    cmds.connectAttr(displacement+'.displacement', shadingGroup+'.displacementShader')
    return shadingGroup
    
def createSphereWithAllShaders():
    '''
    Creates a poly sphere (pSphere1) with the following material.
     
    place2dTexture1 ----> noise1 ----> bump1 ----> lambert1 ----\ 
                                        displacementShader1 ----- initialShadingGroup
                                                 volumeFog1 ----/
    You can see it with: 
    import maya.app.renderSetup.common.test.testScenes as scenes; scenes.createSphereWithAllShaders()
    '''
    
    mel.eval('\
    shadingNode -asUtility bump2d; \
    shadingNode -asTexture noise; \
    shadingNode -asUtility place2dTexture; \
    connectAttr place2dTexture1.outUV noise1.uv; \
    connectAttr place2dTexture1.outUvFilterSize noise1.uvFilterSize; \
    setAttr noise1.alphaIsLuminance true; \
    connectAttr -f noise1.outAlpha bump2d1.bumpValue; \
    connectAttr -f bump2d1.outNormal lambert1.normalCamera;\
    shadingNode -asShader volumeFog; \
    connectAttr -f volumeFog1.outColor initialShadingGroup.volumeShader;\
    shadingNode -asShader displacementShader; \
    connectAttr -f displacementShader1.displacement initialShadingGroup.displacementShader; \
    polySphere(); \
    ')
    
    cmds.select(clear=True)
    
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
