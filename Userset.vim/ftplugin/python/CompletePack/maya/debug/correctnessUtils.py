"""
This file holds utilities used to write correctness tests.

It is meant to be used by tests validating the correctness of evaluation, for
instance validating the correctness of evaluation under evaluation manager or
background evaluation.

Its main utility function is run_correctness_test().

If resultsPath is set then the graph output and differences are dumped to
files using that path as the base name.  For example:

    resultsPath             = MyDirectory/emCorrecteness_animCone
    reference results dump  = MyDirectory/emCorrecteness_animCone.ref.txt
    reference results image = MyDirectory/emCorrecteness_animCone.ref.png
    ${mode} results dump    = MyDirectory/emCorrecteness_animCone.${mode}.txt
    ${mode} results image   = MyDirectory/emCorrecteness_animCone.${mode}.png

If resultsPath is not set then no output is stored, everything is live.

The return value is a list of value pairs indicating number of differences
between the reference evaluation and the tested mode. e.g. if you requested 'ems'
mode then you would get back {'ems' : (0, 0, 0)} from a successful comparison.

If fileName is not set then the current scene is analyzed.
"""

import json
import os
import os.path
import tempfile
import maya.cmds as cmds
from maya.debug.TODO import TODO as TODO
from maya.debug.DGState import DGState as DGState
from maya.debug.emModeManager import emModeManager as emModeManager
from maya.debug.playbackModeManager import playbackModeManager as playbackModeManager


__all__ = [ 'run_correctness_test'
        ,   'CORRECTNESS_MAX_FRAMECOUNT'
        ,   'CORRECTNESS_NO_SETUP'
        ,   'CORRECTNESS_DOUBLE_PLAYBACK'
        ,   'CORRECTNESS_INVALIDATE'
        ,   'CORRECTNESS_LOAD'
        ]

# Maximum number of frames to play (to avoid eternal tests)
CORRECTNESS_MAX_FRAMECOUNT = 20

# Setup modes when analyzing scenes in EM modes
CORRECTNESS_NO_SETUP        = 0 # Do nothing, just run playback
CORRECTNESS_DOUBLE_PLAYBACK = 1 # Run playback twice to ensure graph is valid
CORRECTNESS_INVALIDATE      = 2 # Invalidate the graph to force rebuild
CORRECTNESS_LOAD            = 4 # Load the file between every mode (if the file was loaded at all)


#======================================================================

def model_panel_visible():
    '''
    Return true if any model panel is currently visible. This includes
    checking for GUI model and looking at the currently visible panels
    to see if any of them are model panels.
    '''
    if cmds.about(batch=True):
        return False

    panel_list = cmds.getPanel( visiblePanels=True ) or []
    for visible_panel in panel_list:
        try:
            cmds.modelPanel( visible_panel, query=True, modelEditor=True )
            return True
        except RuntimeError:
            pass
    return False

#======================================================================

class EmptyContext(object):
    """
    Empty context class that performs no action on entry or exit.
    """
    def __enter__(self):
        return self

    def __exit__(self,type,value,traceback):
        pass

#======================================================================

def __is_maya_file(path):
    """
    Check to see if the given path is a Maya file. Only looks for native Maya
    files ".ma" and ".mb", not other importable formats such as ".obj" or ".dxf"
    """
    return os.path.isfile(path) and ((path[-3:] == '.ma') or (path[-3:] == '.mb'))


#======================================================================

def __find_em_plugs(ignored_nodes):
    """
    Find all of the root level plugs that the EM will be marking
    dirty. The passed-in dictionary will be populated by a list of
    dictionaries.

    em_plugs[NODE] = {DIRTY_PLUG_IN_NODE:True}
    ignored_nodes  = [NODES_TO_SKIP]
    """
    em_plugs = {}
    try:
        json_plugs = json.loads(cmds.dbpeek(op='graph', eg=True, all=True, a='plugs'))
    except ValueError:
        print 'WARNING: No output from plug list'
        return em_plugs

    if not json_plugs or 'plugs' not in json_plugs:
        print 'WARNING: No output from plug list'
        return em_plugs

    for node, per_node_list in json_plugs['plugs'].iteritems():
        if node in ignored_nodes:
            continue
        input_plugs = per_node_list['input']
        output_plugs = per_node_list['output']
        world_plugs = per_node_list['affectsWorld']
        attribute_plugs = per_node_list['attributes']
        for attribute in input_plugs + output_plugs + world_plugs + attribute_plugs:
            if node in em_plugs:
                em_plugs[node][attribute] = True
            else:
                em_plugs[node] = {attribute:True}

    return em_plugs


#======================================================================

def run_correctness_test( referenceMode
                        , modes
                        , fileName=None
                        , resultsPath=None
                        , verbose=False
                        , maxFrames=CORRECTNESS_MAX_FRAMECOUNT
                        , dataTypes=['matrix','vertex','screen']
                        , emSetup=CORRECTNESS_NO_SETUP ):
    """
    Evaluate the file in multiple modes and compare the results.

    referenceMode: Mode to which other modes will be compared for correctness.
                   It's a string that can be passed to emModeManager.setMode()
                   function.
    modes:         List of modes to run the tests in.  They must be have the following methods:
                   getTitle   : returns a string describing the mode
                   getEmMode  : returns a string to be passed to emModeManager.setMode()
                                before running the test.
                   getContext : returns a context object that can set extra state on enter
                                and reset it on exit (or None if not needed).
    fileName:      Name of file to load for comparison. None means use the current scene
    resultsPath:   Where to store the results. None means don't store anything
    verbose:       If True then dump the differing values when they are encountered
    maxFrames:     Maximum number of frames in the playback, to avoid long tests.
    dataTypes:     List of data types to include in the analysis. These are the possibilities:
                   matrix: Any attribute that returns a matrix
                   vector: Any attribute with type 3Double
                   vertex: Attributes on the mesh shape that hold vertex positions
                   number: Any attribute that returns a number
                   screen: Screenshot after the animation runs
    emSetup:       What to do before running an EM mode test, in bitfield combinations
                   CORRECTNESS_NO_SETUP        Do nothing, just run playback
                   CORRECTNESS_DOUBLE_PLAYBACK Run playback twice to ensure graph is valid
                   CORRECTNESS_INVALIDATE      Invalidate the graph to force rebuild
                   CORRECTNESS_LOAD            Load the file between every mode's run
                                               (Default is to just load once at the beginning.)

    Returns a list of value tuples indicating the run mode and the number of
    changes encountered in that mode. e.g. ['ems', 0]

    If verbose is true then instead of counts return a list of actual changes.
    e.g. ['ems', ["plug1,oldValue,newValue"]]

    Changed values are a CSV 3-tuple with "plug name", "value in reference mode", "value in the named test mode"
    in most cases.

    In the special case of an image difference the plug name will be one
    of the special ones below and the values will be those generated by the
    comparison method used:
        DGState.SCREENSHOT_PLUG_MD5 : md5 values when the image compare could not be done
        DGState.SCREENSHOT_PLUG_MAG : md5 and image difference values from ImageMagick
        DGState.SCREENSHOT_PLUG_IMF : md5 and image difference values from imf_diff
    """
    # Fail if the fileName is not a valid Maya file.
    if fileName != None and not __is_maya_file(fileName):
        print 'ERROR: %s is not a Maya file' % fileName
        return {}

    # Load the fileName if it was specified, otherwise the current scene will bbbbbbbbb
    if fileName != None:
        cmds.file(fileName, force=True, open=True)

    ref_results = None
    ref_results_image = None

    # Using lists allows me to do a comparison of two identical modes.
    # If resultsPath is given then the second and successive uses of the
    # same type will go into files with an incrementing suffix (X.ref.txt,
    # X.ref1.txt, X.ref2.txt...)
    mode_results_files = []
    mode_compare_files = []
    mode_results_image_files = []
    results = []
    em_plug_file_name = None

    # Create a list of unique mode suffixes, appending a count number whenever
    # the same mode appears more than once on the modes list.
    mode_counts = {}
    unique_modes = []
    mode_counts['ref'] = 1
    for modeObject in modes:
        mode = modeObject.getTitle()
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        suffix = ''
        if mode_counts[mode] > 1:
            suffix = str(mode_counts[mode])
        unique_modes.append('%s%s' % (mode, suffix))

    if resultsPath != None:
        # Make sure the path exists
        if not os.path.isdir(resultsPath):
            os.makedirs(resultsPath)

        em_plug_file_name = os.path.join(resultsPath, 'EMPlugs.txt')

        # Build the rest of the paths to the results files.
        # If no file was given default the results file prefix to "SCENE".
        if fileName != None:
            # Absolute paths cannot be appended to the results path. Assume
            # that in those cases just using the base name is sufficient.
            if os.path.isabs(fileName):
                resultsPath = os.path.join(resultsPath, os.path.basename(fileName))
            else:
                resultsPath = os.path.join(resultsPath, fileName)
        else:
            resultsPath = os.path.join(resultsPath, 'SCENE')

        ref_results = '%s.ref.txt' % resultsPath
        mode_counts['ref'] = 1

        for mode in unique_modes:
            # mode strings can have '/' which are illegal in filenames, replace with '='.
            mode = mode.replace('/', '=')
            mode_results_files.append('%s.%s.txt' % (resultsPath, mode))
            mode_compare_files.append('%s.DIFF.%s.txt' % (resultsPath, mode))
    else:
        # Still need the file args to pass in to DGState. None = don't output.
        for _ in modes:
            mode_results_files.append( None )
            mode_compare_files.append( None )

    # If the image comparison was requested figure out where to store the
    # file. Done separately because even if the files won't be saved the image
    # comparison needs to dump a file out for comparison.
    if 'screen' in dataTypes:
        if resultsPath == None:
            image_dir = tempfile.gettempdir()
            if fileName != None:
                # Absolute paths cannot be appended to the results path. Assume
                # that in those cases just using the base name is sufficient.
                if os.path.isabs(fileName):
                    image_dir = os.path.join(image_dir, os.path.basename(fileName))
                else:
                    image_dir = os.path.join(image_dir, fileName)
            else:
                image_dir = os.path.join(image_dir, 'SCENE')
        else:
            image_dir = resultsPath

        ref_results_image = '%s.ref.png' % image_dir
        for mode in unique_modes:
            # mode strings can have '/' which are illegal in filenames, replace with '='.
            mode = mode.replace('/', '=')
            mode_results_image_files.append('%s.%s.png' % (image_dir, mode))
    else:
        ref_results_image = None
        for _ in unique_modes:
            mode_results_image_files.append( None )

    # The IK multi-chain solver is known to create inconsistent results so remove
    # any joints that are being controlled by it from the list being compared.
    TODO('REFACTOR', 'Is this still needed now that we have an evaluator that handles it and disable EM if they are found?', None)
    ignored_nodes = []
    for node in cmds.ls(type='ikHandle'):
        try:
            solver_type = None
            solver_type = cmds.nodeType(cmds.ikHandle(node, query=True, solver=True))
        except Exception:
            pass

        # Any other kind of IK solver is fine
        if solver_type != 'ikMCsolver':
            continue

        multi_chain_joints = cmds.ikHandle(node, query=True, jointList=True)
        if multi_chain_joints is not None:
            ignored_nodes += multi_chain_joints
        multi_chain_effector = cmds.ikHandle(node, query=True, endEffector=True)
        if multi_chain_effector is not None:
            ignored_nodes += [multi_chain_effector]

    em_plugs = None
    comparisons = {}

    TODO('FEATURE', 'Could modify the verbose input to allow dumping of JSON instead of CSV', None)
    comparison_mode = DGState.OUTPUT_CSV

    # Record the reference evaluation version of the results
    with emModeManager() as em_mode:
        em_mode.setMode(referenceMode)

        with playbackModeManager() as play_mode:
            # Set to free running but hit every frame
            play_mode.setOptions( framesPerSecond=0.0, maxPlaybackSpeed=0.0, loop='once' )
            play_mode.setLimitedRange( maxFrames=maxFrames, fromStart=True )

            # If no model panel is visible the refresh command won't trigger any evaluation
            if model_panel_visible():
                cmds.refresh()
            else:
                cmds.dgdirty(allPlugs=True)

            if (emSetup & CORRECTNESS_DOUBLE_PLAYBACK) != 0:
                play_mode.playAll()
            play_mode.playAll()

            mDG = DGState()
            mDG.scan_scene(do_eval=(referenceMode == 'dg'), data_types=dataTypes)
            mDG.store_state(ref_results, ref_results_image)

            # Walk all of the modes requested and run the tests for them
            for mode_num in range(len(modes)):
                test_mode = modes[mode_num]
                with emModeManager() as test_em_mode:
                    test_em_mode.setMode(test_mode.getEmMode())
                    extra_context = test_mode.getContext()
                    if not extra_context:
                        extra_context = EmptyContext()
                    with extra_context:
                        if (emSetup & CORRECTNESS_LOAD != 0) and fileName != None:
                            cmds.file(fileName, force=True, open=True)
                        if (emSetup & CORRECTNESS_DOUBLE_PLAYBACK) != 0:
                            play_mode.playAll()
                        if (emSetup & CORRECTNESS_INVALIDATE) != 0:
                            cmds.evaluationManager(invalidate=True)
                        play_mode.playAll()
                        if em_plugs == None:
                            em_plugs = __find_em_plugs(ignored_nodes)
                            mDG.filter_state(em_plugs)
                            if em_plug_file_name:
                                try:
                                    em_handle = open(em_plug_file_name, 'w')
                                    for (node,plug_list) in em_plugs.iteritems():
                                        em_handle.write('%s\n' % node)
                                        for plug in plug_list.keys():
                                            em_handle.write('\t%s\n' % plug)
                                    em_handle.close()
                                except Exception, ex:
                                    print 'ERROR: Could not write to EM plug file %s: "%s"' % (em_plug_file_name, str(ex))
                        mode_state = DGState()
                        # Catch the case when the EM has been disabled due to unsupported areas in the graph.
                        # When that happens the evaluation has to be forced or the values will be wrong.
                        em_still_enabled = cmds.evaluationManager(query=True, mode=True) != 'dg' and cmds.evaluationManager(query=True, enabled=True)

                        mode_state.scan_scene(do_eval=not em_still_enabled, data_types=dataTypes)
                        mode_state.store_state(mode_results_files[mode_num], mode_results_image_files[mode_num])

                        results.append(mode_state)
                        results[mode_num].filter_state(em_plugs)
                        mode_title = test_mode.getTitle()
                        (comparison,error_count,_) = mDG.compare(results[mode_num], output_mode=comparison_mode)
                        if verbose:
                            comparisons[mode_title] = comparison
                        else:
                            comparisons[mode_title] = error_count
                        if mode_compare_files[mode_num] is not None:
                            with open(mode_compare_files[mode_num], 'w') as compare_file:
                                compare_file.write( str(comparison) )

    # Force restoration of EM state by leaving scope

    return comparisons
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
