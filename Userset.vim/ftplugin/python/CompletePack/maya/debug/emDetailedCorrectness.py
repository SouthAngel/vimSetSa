"""
Utility to dump the correctness data for some failing files in more detail
with summaries including the type of nodes and attributes that are failing.

If these environment variables are defined they will be used to locate the
files for analyzing, otherwise a file browser will open to locate them.

    EM_CORRECTNESS_RESULTS  : Directory in which to store the results
    EM_CORRECTNESS_FILES    : Directory at which to find the files to analyze
"""
import shutil
import os
import re
import maya.cmds as cmds
from maya.debug.emCorrectnessTest import emCorrectnessTest
from maya.debug.emCorrectnessTest import SCREENSHOT_NODE

__all__ = [ 'onFile'
		  , 'onDirectory'
		  ]

# File dialog filter for file selection (directory selection needs no filter)
MAYA_FILE_FILTER = "Maya Files (*.ma *.mb);;Maya ASCII (*.ma);;Maya Binary (*.mb)"

# Location and environment variable where results will be stored
RESULTS_ROOT = None
RESULTS_ENV = 'EM_CORRECTNESS_RESULTS'
# Location and environment variable where data is found
DATA_LOCATION_ROOT = None
DATA_LOCATION_ENV = 'EM_CORRECTNESS_FILES'

#======================================================================
def __summarizeCorrectnessInScene(resultsDir, dataRoot):
    """
    Summarize the current scene's emCorrectnessTest results, placing the
    detailed results into "resultsDir" in a subdirectory corresponding to the
    scene's name, relative to the dataRoot.
        e.g. if dataRoot = "~/Files/Weta/Avatar/AvatarScene.ma"
        and resultsDir = "~/Results" then the results will be stored
        in "~/Results/Weta/Avatar/AvatarScene.ma/"

    resultsDir : Root directory where the results files will be stored
    dataRoot   : Root directory where all of the data files are stored
    """
    reMulti = re.compile( r'([^\[]+)\[.*' )

    results = emCorrectnessTest(verbose=True, modes=['ems','emp'], maxFrames=300, resultsPath=resultsDir)
    modeNames = {'ems':'EM Serial', 'emp':'EM Parallel'}
    attrChanges = {}
    nodeChanges = {}
    nodeTypes = {}
    (path,fileName) = os.path.split( cmds.file( query=True, loc=True ) )
    path = path.replace( dataRoot, '' )
    if len(path) > 0 and (path[0] == '/' or path[0] == os.sep):
        path = path[1:]

    # Copy the results files in place
    resultsPath = os.path.join( resultsDir, path, fileName )
    print 'Copying results to %s' % resultsPath

    if not os.path.isdir( resultsPath ):
        os.makedirs( resultsPath )
    for mode in modeNames.keys() + ['dg']:
        for suffix in ['txt','png']:
            resultsBaseName = 'SCENE.%s.%s' % (mode,suffix)
            resultsFile = os.path.join( resultsDir, resultsBaseName )
            destinationFile = os.path.join( resultsPath, resultsBaseName )
            shutil.move( resultsFile, destinationFile )

    # Move the file containing the EM graph over, if it exists
    emPlugFileName = 'EMplugs.txt'
    resultsEmPlugFile = os.path.join( resultsDir, emPlugFileName )
    if os.path.exists( resultsEmPlugFile ):
        shutil.move( resultsEmPlugFile, os.path.join( resultsPath, emPlugFileName ) )

    rawDifferences = 0
    rawValues = {}
    rawValues['dg'] = {}
    for (comparisonType,result) in results.iteritems():
        # Just look at the changes; ignore the additions and removals
        if len(result[1]) == 0:
            continue

        if comparisonType not in rawValues:
            rawValues[comparisonType] = {}

        for resultLine in result[1]:
            rawDifferences += 1
            (plug, value1, value2, _) = resultLine.split(',')
            rawValues['dg'][plug] = value1
            rawValues[comparisonType][plug] = value2
            (nodeName,attr) = plug.split('.')
            if nodeName == SCREENSHOT_NODE:
                nodeType = SCREENSHOT_NODE
            else:
                nodeType = cmds.nodeType( nodeName )
            multiMatch = reMulti.match( attr )
            if multiMatch:
                attr = multiMatch.group(1)

            nodeTypes[nodeType] = nodeTypes.get(nodeType,0) + 1
            nodeChanges[nodeName] = nodeChanges.get(nodeName,0) + 1
            attrChanges[attr] = attrChanges.get(attr,0) + 1

    summaryFile = os.path.join(resultsPath, 'SUMMARY.txt')
    print '    Creating summary file %s' % summaryFile

    # Create a special summary file with node type information
    summaryFd = open( summaryFile, 'w' )

    # First lines are the list of node types and counts; the most useful
    print     '--- %d node type results' % len(nodeTypes.keys())
    for nodeType in sorted(nodeTypes.keys()):
        summaryFd.write( 'TYPE\t%d\t%s\n' % (nodeTypes[nodeType], nodeType) )

    summaryFd.write( '\n' )

    # Next lines are the total number of attribute differences
    print     '--- %d attribute change results' % len(attrChanges.keys())
    for attr in sorted(attrChanges.keys()):
        summaryFd.write( 'ATTR\t%d\t%s\n' % (attrChanges[attr],attr) )

    summaryFd.write( '\n' )

    # Dump out a selection command to easily access failing nodes
    print     '--- %d node change results' % len(nodeChanges.keys())
    summaryFd.write( 'cmds.select( [\n\t' )
    summaryFd.write( '\n\t,'.join( '"%s"' % node for node in sorted(nodeChanges) if node != SCREENSHOT_NODE) )
    summaryFd.write( '\n\t] )\n' )

    summaryFd.write( '\n' )

    # Lastly dump out the raw difference data for later comparison.
    # Only the values that differ will appear in this.
    print     '--- %d raw difference results' % rawDifferences
    for plug in rawValues['dg'].keys():
        summaryFd.write( '%s\n' % plug )
        for comparisonType in rawValues.keys():
            if plug in rawValues[comparisonType]:
                summaryFd.write( '    %s\t' % comparisonType )
                for value in rawValues[comparisonType][plug].split(' '):
                    try:
                        summaryFd.write( ' %8g' % float(value) )
                    except ValueError:
                        # If not a float then the type is unknown so just
                        # print as a string.
                        summaryFd.write( ' %s' % str(value) )
            summaryFd.write( '\n' )

    summaryFd.close()

#======================================================================
def __summarizeCorrectness(resultsDir='.', dataRoot='.', files=None):
    """
    Summarize the correctness results.
    Returns a list of the directories in which results can be found.
    """
    resultsPaths = []
    if files == None:
        __summarizeCorrectnessInScene( resultsDir, dataRoot )
        resultsPaths += [dataRoot]
    else:
        for loadFile in files:
            if not os.path.exists( os.path.join(dataRoot,loadFile) ):
                print 'ERROR: No file %s, aborting' % os.path.join( dataRoot, loadFile )
                return
        for loadFile in files:
            cmds.file( os.path.join(dataRoot,loadFile), force=True, open=True )
            __summarizeCorrectnessInScene( resultsDir, dataRoot )
            resultsPaths += [os.path.join(dataRoot,loadFile)]
    return resultsPaths

#======================================================================
def __getFileLocations():
    """
    Find the file locations using the environment variables if they exist and
    calls to the file dialog if they do not.

    Returns a 2-tuple if (RESULTS_ROOT, DATA_LOCATION_ROOT)
    """
    global RESULTS_ROOT
    global DATA_LOCATION_ROOT

    if not RESULTS_ROOT:
        if RESULTS_ENV in os.environ:
            RESULTS_ROOT = os.getenv( RESULTS_ENV )
        else:
            RESULTS_ROOT = cmds.fileDialog2( dialogStyle=2
                                           , fileMode=4
                                           , okCaption='Set Results')

    if not DATA_LOCATION_ROOT:
        if DATA_LOCATION_ENV in os.environ:
            DATA_LOCATION_ROOT = os.getenv( DATA_LOCATION_ENV )
        else:
            DATA_LOCATION_ROOT = cmds.fileDialog2( dialogStyle=2
                                                 , fileMode=4
                                                 , okCaption='Set Data')

    return (RESULTS_ROOT, DATA_LOCATION_ROOT)

#======================================================================
def onFile():
    """
    Run the detailed correctness tests with summary on the selected scene.
    Returns a list of the directories in which results can be found.
    """
    (resultsRoot, dataFileRoot) = __getFileLocations()
    fileToAnalyze = cmds.fileDialog2( startingDirectory=dataFileRoot
                                    , fileFilter=MAYA_FILE_FILTER
                                    , dialogStyle=2
                                    , fileMode=1
                                    , okCaption='Analyze')
    if not fileToAnalyze or (len(fileToAnalyze) == 0):
        print 'No file selected for analysis'
    else:
        # Remove the root path since the summarize method doesn't need it.
        # use [1:] to skip the path separator without needing to know what it is
        filesToAnalyze = [fileToAnalyze[0].replace( dataFileRoot, '' )[1:]]
        return __summarizeCorrectness( resultsDir = resultsRoot
                              , dataRoot = dataFileRoot
                              , files = filesToAnalyze )
    return []

#======================================================================
def onDirectory():
    """
    Run the detailed correctness tests with summary on all of the scenes
    below the selected directory.
    Returns a list of the directories in which results can be found.
    """
    (resultsRoot, dataFileRoot) = __getFileLocations()
    directoryToAnalyze = cmds.fileDialog2( startingDirectory=dataFileRoot
                                         , dialogStyle=2
                                         , fileMode=3
                                         , okCaption='Analyze')
    if not directoryToAnalyze or (len(directoryToAnalyze) == 0):
        print 'No directory selected for analysis'
    else:
        filesToAnalyze = []
        for root, dirs, files in os.walk(directoryToAnalyze[0]):
            # Skip reference directories
            if 'references' in dirs:
                dirs.remove( 'references' )
            for name in files:
                if name[-3:] == '.ma' or name[-3:] == '.mb':
                    filesToAnalyze.append( os.path.join(root, name) )
        if len(filesToAnalyze) == 0:
            print 'No Maya files in directory selected for analysis'
        else:
            print 'Analyzing files %s' % str(filesToAnalyze)
            return __summarizeCorrectness( resultsDir = resultsRoot
                                         , dataRoot = dataFileRoot
                                         , files = filesToAnalyze )
    return []


# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
