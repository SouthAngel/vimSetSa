'''
Test the comparitive performance between regular Maya transforms and the
leanTransformTest node to see what overhead the API brings.
'''

import random
import maya.cmds as cmds
from maya.debug.playbackModeManager import playbackModeManager
from maya.debug.emModeManager import emModeManager

PLUGIN = 'leanTransformTest'    # Name of plug-in with the MPxTransform node
NODE_NAME = 'leanTransformTest' # Name of the plug-in node
NODE_COUNT = 500               # Number of nodes to test with
KEY_COUNT = 500                # Number of keyframes to set on each node
NATIVE_PROFILE = 'Ttransform_profile.txt'   # File containing profile information for Ttransform
PLUGIN_PROFILE = 'MPxTransform_profile.txt' # File containing profile information for MPxTransform

#======================================================================
def create_nodes(node_count, node_type):
    '''
    Create a given number of nodes of the given type and return the
    list of nodes created.
    '''
    print '    creating nodes'
    return [cmds.createNode(node_type) for i in range(0,node_count)]

#======================================================================
def animate(node_list, keyframe_count):
    '''
    Animate the TRS attributes of every node in the list with random
    values for each frame from 1 to "keyframe_count"
    '''
    print '    creating animation'
    step = int(keyframe_count / 10)
    for frame in range(1,keyframe_count+1):
        tx = random.randrange( 0.0, 100.0 )
        ty = random.randrange( 0.0, 100.0 )
        tz = random.randrange( 0.0, 100.0 )
        rx = random.randrange( -180.0, 180.0 )
        ry = random.randrange( -180.0, 180.0 )
        rz = random.randrange( -180.0, 180.0 )
        sx = random.randrange( 1.0, 5.0 )
        sy = random.randrange( 1.0, 5.0 )
        sz = random.randrange( 1.0, 5.0 )
        cmds.currentTime( frame )
        for node in node_list:
            cmds.select( node )
            cmds.move( tx, ty, tz )
            cmds.rotate( rx, ry, rz )
            cmds.scale( sx, sy, sz )
            cmds.setKeyframe( '{}.t'.format(node) )
            cmds.setKeyframe( '{}.r'.format(node) )
            cmds.setKeyframe( '{}.s'.format(node) )
        if frame % step == 0:
            print '    ...{} of {} done'.format(frame, keyframe_count)

def measureMPxTransformPerformance():
    '''
    Run two performance tests with 1000 transforms keyed randomly over 1000 frames
    for both the native Ttransform and the API leanTransformTest. Report the timing
    for playback of the two, and dump profile files for both for manual inspection.
    '''
    cmds.file( force=True, new=True )

    # Make sure the test plug-in is loaded and remember whether it was already
    # loaded or not so that the state can be restored after the test is finished.
    plugin_loaded = (cmds.loadPlugin(PLUGIN) is not None)

    # Do all profiling in parallel mode
    with emModeManager() as em_mgr:
        em_mgr.setMode( 'emp' )

        #----------------------------------------------------------------------
        # Test 1: Simple node derived from MPxTransform
        print 'Testing plug-in transform...'
        animate( create_nodes(NODE_COUNT, NODE_NAME), KEY_COUNT )
        print '   playing back'
        with playbackModeManager() as play_mgr:
            play_mgr.setOptions( loop='once', minTime=1.0, maxTime=KEY_COUNT, framesPerSecond=0.0 )
            plugin_playback = play_mgr.playAll()
            # Sample enough of the playback range to get good results
            cmds.profiler( sampling=True )
            play_mgr.playLimitedRange( 10 )
            cmds.profiler( sampling=False )
            cmds.profiler( output=PLUGIN_PROFILE )
        cmds.file( force=True, new=True )

        #----------------------------------------------------------------------
        # Test 2: The native Ttransform
        print 'Testing internal transforms'
        animate( create_nodes(NODE_COUNT, 'transform'), KEY_COUNT )
        print '   playing back'
        with playbackModeManager() as play_mgr:
            play_mgr.setOptions( loop='once', minTime=1.0, maxTime=KEY_COUNT, framesPerSecond=0.0 )
            native_playback = play_mgr.playAll()
            # Sample enough of the playback range to get good results
            cmds.profiler( sampling=True )
            play_mgr.playLimitedRange( 10 )
            cmds.profiler( sampling=False )
            cmds.profiler( output=NATIVE_PROFILE )
        cmds.file( force=True, new=True )

    # If the test loaded the plug-in then unload it so that state is unchanged.
    if plugin_loaded:
        cmds.unloadPlugin(PLUGIN)

    # Report the results
    #
    print 'Native transform playback time = {}'.format( native_playback )
    print 'Plugin transform playback time = {}'.format( plugin_playback )
    print 'Profile outputs are in {} and {}'.format( NATIVE_PROFILE, PLUGIN_PROFILE )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
