import maya.cmds as cmds
from maya.app.stereo import stereoCameraRig

"""
This module defines a new stereo camera rig. It illustrates how to create
a proxy camera rig.

  createRig() creates the rig itself.
  registerThisRig() registers it into the system. 
"""

def __createSlave( name, parent ):
  """
  Creates a left / right slave camera.  This is private method and
  not intended to be called from outside this module. 
  """
  # First create a camera under the right parent with the desired name
  #
  slave = cmds.camera()[0]
  if parent: 
    slave = cmds.parent(slave, parent, relative=True)[0]
  slave = cmds.rename(slave, name)
  return slave

def __createAControlCamera():
  """
  Creates a main control camera. This is a private function and not
  intended to be called outside of this module.
  """
  return __createSlave( "Master", parent=None )

def createRig(basename='stereoCameraProxy', centerCam=None, camRoot=None, partOfMulti=False):
  """
  Creates a new custom stereoCameraProxy rig. 
  """
  # Create the root of the rig
  #
  rigRoot = None
  if not camRoot: 
    selected = cmds.ls(sl=True)
    if len(selected) > 0 and cmds.objectType( selected[0], isa="transform" ):
      rigRoot = selected[0]
  else:
    rigRoot = camRoot

  if rigRoot:
    relatives = cmds.listRelatives( rigRoot )
    if relatives: 
      for rel in relatives: 
        if cmds.objectType( rel, isa="camera" ):
          centerCam = rigRoot
          break

  if not centerCam:
    centerCam = __createAControlCamera()
    rigRoot = centerCam
  stereoMarker = centerCam
  
  stereoRigRoot = cmds.createNode( "transform", name=basename, parent=rigRoot )
  rootName = stereoRigRoot.split( '|' )[-1]
    
  left  = __createSlave( rootName + "Left", stereoRigRoot )
  leftShape = cmds.listRelatives( left, path=True, shapes=True )[0]
  right = __createSlave( rootName + "Right", stereoRigRoot )
  rightShape = cmds.listRelatives( right, path=True, shapes=True )[0]

  if partOfMulti:
    stereoMarker = left

  if not cmds.attributeQuery( 'proxyRig', n=stereoMarker, exists=True ):
    cmds.addAttr( stereoMarker, longName='proxyRig', attributeType='message')
  if not cmds.attributeQuery( 'proxyRig', n=stereoRigRoot, exists=True ): 
    cmds.addAttr( stereoRigRoot, longName='rigReceiver', attributeType='message' )
  
  cmds.connectAttr( stereoMarker + '.proxyRig', stereoRigRoot + '.rigReceiver' ) 
  
  if not cmds.attributeQuery('stereoRigType', n=stereoRigRoot, exists=True):
    cmds.addAttr(stereoRigRoot, longName='stereoRigType', dataType='string' )

  cmds.setAttr( stereoRigRoot + '.stereoRigType', 'StereoCameraProxy',
                type="string" )

  stereoCameraRig.__addAttrAndConnect( 'centerCam', stereoRigRoot, centerCam )
  stereoCameraRig.__addAttrAndConnect( 'leftCam', stereoRigRoot, left )
  stereoCameraRig.__addAttrAndConnect( 'rightCam', stereoRigRoot, right )

  cmds.setAttr( left + '.tx', -1.0 );
  cmds.setAttr( right +'.tx',  1.0 );
  cmds.select( stereoRigRoot, replace=True ) 
 
  # define Mid as the default Left, Right pair, return it.
  #
  return [stereoMarker, leftShape, rightShape, stereoRigRoot]

def registerThisRig():
  """
  Registers the rig in Maya's database
  """
  cmds.stereoRigManager(add=['StereoCameraProxy', 'Python',
                             'maya.app.stereo.stereoCameraProxyRig.createRig'])
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
