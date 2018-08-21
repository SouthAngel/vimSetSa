import maya.cmds as cmds

"""
This module defines a Stereo Camera rig.

    createRig() creates the rig itself
    registerThisRig() registers it into the system
"""

def __createSlaveCamera(masterShape, name, parent):
  """
  Private method to this module.
  Create a slave camera
  Make the default connections between the master camera and the slave one.
  """

  # First create a camera under the right parent with the desired name
  #
  slave = cmds.camera()[0]
  slave = cmds.parent(slave, parent)[0]
  slave = cmds.rename(slave, name)
  slaveShape = cmds.listRelatives(slave, path=True, shapes=True)[0]
  
  # Change some default attributes
  #
  cmds.setAttr( slave + '.renderable', 0 )
  
  # Connect the camera attributes from the master, hide them
  #
  for attr in [ 'horizontalFilmAperture',
                'verticalFilmAperture',
                'focalLength',
                'lensSqueezeRatio',
                'fStop',
                'focusDistance',
                'shutterAngle',
                'cameraPrecompTemplate',
                'filmFit',
                'displayFilmGate',
                'displayResolution',
                'nearClipPlane',
                'farClipPlane' ] :
    slaveAttr = slaveShape + '.' + attr
    cmds.connectAttr(masterShape + '.' + attr, slaveAttr)
    cmds.setAttr(slaveAttr, keyable=False )
    
  # Hide some more attributes on the transform
  #
  for attr in [ 'scaleX', 'scaleY', 'scaleZ',
                'visibility',
                'centerOfInterest' ] :
    cmds.setAttr( slave + '.' + attr, keyable=False )

  return slave

def __createFrustumNode( mainCam, parent, baseName ):
  """
  Private method to this module.
  Create a display frustum node under the given parent.
  Make the default connections between the master camera and the frustum  
  Remove some of the channel box attributes that we do not want to show
  up in the channel box. 
  """

  frustum = cmds.createNode( 'stereoRigFrustum', name=baseName, parent=parent )
  for attr in [ 'localPositionX', 'localPositionY', 'localPositionZ',
                'localScaleX', 'localScaleY', 'localScaleZ' ] :
    cmds.setAttr( frustum + '.' + attr, channelBox=False )

  for attr in ['displayNearClip', 'displayFarClip', 'displayFrustum',
               'zeroParallaxPlane',
               'zeroParallaxTransparency',
               'zeroParallaxColor',
               'safeViewingVolume',
               'safeVolumeTransparency',
               'safeVolumeColor',
               'safeStereo',
               'zeroParallax' ] :
    cmds.connectAttr( mainCam+'.'+attr, frustum+'.'+attr )
    
  return frustum

def createRig(basename='stereoCameraMulti'):
  """
  Creates a new stereo rig. Uses a series of Maya commands to build
  a stereo rig.
  The optionnal argument basename defines the base name for each DAG
  object that will be created.
  """

  # Create the root of the rig
  # 
  root = cmds.createNode( 'stereoRigTransform', name=basename )
    
  # The actual basename use is the name of the top transform. If a
  # second rig is created, the default base name may be incremented
  # (e.g. stereoRig1). We want to use the same name for the whole
  # hierarchy.
  # If such a name already exists, root will be a partial path. Keep
  # only the last part for the name.
  #
  rootName = root.split('|')[-1]

  # Create the center (main) camera
  # Connect the center camera attributes to the root
  # Change any default parameters.
  #
  centerCam = cmds.createNode('stereoRigCamera',
                              name=rootName + 'CenterCamShape',
                              parent=root )
  for attr in ['stereo', 'interaxialSeparation',
               'zeroParallax', 'toeInAdjust',
               'filmOffsetRightCam', 'filmOffsetLeftCam'] :
    cmds.connectAttr( centerCam+'.'+attr, root+'.'+attr )
  cmds.connectAttr( centerCam + '.focalLength', root + '.focalLengthInput' )
  cmds.setAttr( centerCam + '.stereo', 2 )
  cmds.setAttr( centerCam + '.renderable', 0 )

  # Create the Frustum node, connect it to the root.
  #
  frustum = __createFrustumNode(centerCam, root, rootName + 'Frustum')

  # Create 3 groups for each stereo pairs
  # We need to use ls, not the retunr value, in case another group
  # with the same name exists somewhere in the hierarchy.
  #
  cmds.group(empty=True, name=rootName+'Front', parent=root)
  layer1 = cmds.ls(selection=True)[0]
  cmds.group(empty=True, name=rootName+'Mid', parent=root)
  layer2 = cmds.ls(selection=True)[0]
  cmds.group(empty=True, name=rootName+'Back', parent=root)
  layer3 = cmds.ls(selection=True)[0]
  
  # Create the 3 left & right eye cameras pairs
  # 
  leftCam1  = __createSlaveCamera(centerCam, rootName+'Left1',  layer1)
  rightCam1 = __createSlaveCamera(centerCam, rootName+'Right1', layer1)
  leftCam2  = __createSlaveCamera(centerCam, rootName+'Left2',  layer2)
  rightCam2 = __createSlaveCamera(centerCam, rootName+'Right2', layer2)
  leftCam3  = __createSlaveCamera(centerCam, rootName+'Left3',  layer3)
  rightCam3 = __createSlaveCamera(centerCam, rootName+'Right3', layer3)

  # Move them to make them more visible
  #
  cmds.setAttr( layer1 + '.translateZ',  5)
  cmds.setAttr( layer3 + '.translateZ', -5)
  
  # Set up message attribute connections to define the role of each camera
  #
  cmds.connectAttr( leftCam2   + '.message', frustum + '.leftCamera' )
  cmds.connectAttr( rightCam2  + '.message', frustum + '.rightCamera' )
  cmds.connectAttr( centerCam  + '.message', frustum + '.centerCamera')

  # Connect the specific left and right output attributes of the root
  # transform to the corresponding left and right camera attributes.
  # Lock the attributes that should not be manipulated by the artist.
  #
  for left in [ leftCam1, leftCam2, leftCam3] :
    cmds.connectAttr( root + '.stereoLeftOffset',   left  + '.translateX')
    cmds.connectAttr( root + '.stereoLeftAngle',    left  + '.rotateY' )
    cmds.connectAttr( root + '.filmBackOutputLeft', left  + '.hfo' )
    cmds.setAttr( left + '.translate', lock=True )
    cmds.setAttr( left + '.rotate'   , lock=True )
  for right in [ rightCam1, rightCam2, rightCam3] :
    cmds.connectAttr( root + '.stereoRightOffset',   right  + '.translateX')
    cmds.connectAttr( root + '.stereoRightAngle',    right  + '.rotateY' )
    cmds.connectAttr( root + '.filmBackOutputRight', right  + '.hfo' )
    cmds.setAttr( right + '.translate', lock=True )
    cmds.setAttr( right + '.rotate'   , lock=True )

  cmds.select(root)
  
  return [root, leftCam2, rightCam2]

def registerThisRig():
  """
  Registers the rig in Maya's database
  """
  cmds.stereoRigManager(add=['StereoCameraMulti', 'Python',
                             'maya.app.stereo.stereoCameraComplexRig.createRig'])
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
