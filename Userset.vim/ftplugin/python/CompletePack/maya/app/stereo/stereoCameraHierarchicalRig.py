import maya.cmds as cmds
from maya.app.stereo import stereoCameraDefaultRig

"""
This module defines a Stereo Camera rig.

    createRig() creates the rig itself
    registerThisRig() registers it into the system
"""

def createRig(basename='stereoCameraHier'):
  """
  Creates a new stereo rig. Uses a series of Maya commands to build
  a stereo rig.
  The optionnal argument basename defines the base name for each DAG
  object that will be created.
  """

  # Create the root of the rig
  # 
  root = cmds.camera( name=basename )[0]

  # use this name as basename for the other rigs. This may not be the
  # exact original basenaemif this object already exists in the scene. 
  basename = root.split('|')[-1]
  
  # create sub-rigs, using default setup
  #
  front = stereoCameraDefaultRig.createRig(basename=basename+'Front')
  mid   = stereoCameraDefaultRig.createRig(basename=basename+'Mid')
  back  = stereoCameraDefaultRig.createRig(basename=basename+'Back')

  # Reparent them under the main camera
  #
  cmds.parent(front[0], root)
  cmds.parent(mid[0], root)
  cmds.parent(back[0], root)
  
  # Move them to make them more visible
  #
  cmds.setAttr( front[0] + '.translateZ',  8)
  cmds.setAttr( mid[0]   + '.translateZ',  4)
  cmds.setAttr( back[0]  + '.translateZ', -4)
  
  # define Mid as the default Left, Right pair, return it.
  #
  return [root, mid[1], mid[2]]

def registerThisRig():
  """
  Registers the rig in Maya's database
  """
  cmds.stereoRigManager(add=['StereoCameraHier', 'Python',
                             'maya.app.stereo.stereoCameraHierarchicalRig.createRig'])
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
