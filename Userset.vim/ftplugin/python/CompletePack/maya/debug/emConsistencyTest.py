"""
Utility to run a playback equivalent on the current or named file and force
the evaluation manager to rebuild its graph every frame. The graphs are then
compared to see what, if anything, changes between frames.

Ideally the graphs are consistent but there are some cases where differences
arise due to changing dirty propagation for optimization purposes. This
utility will help track those down.

If resultsPath is set then the graph output and differences are dumped to
files using that path as the base name.  For example:

	resultsPath		  = MyDirectory/emConsistency_animCone
	graph at frame N  = MyDirectory/emConsistency_animCone_N.eg
	graph comparisons = MyDirectory/emConsistency_animCone_diff.txt

If resultsPath is not set then no output is stored, everything is live.

The return value is always a simple True/False indicating whether all
of the frames in the animation yielded the same graph or not.

If fileName is not set then the current scene is analyzed.

Sample usage to run the tests on a single file:

	from maya.debug.emConsistencyTest import emConsistencyTest
	emConsistencyTest(fileName='MyDirectory/MyFile', resultsPath='MyDirectory/emConsistency_MyFile', doParallel=False)

Sample usage to run the tests on the current scene in parallel mode and ignore output:

	from maya.debug.emConsistencyTest import emConsistencyTest
	emConsistencyTest(doParallel=True)
"""

import os, sys, getopt
import maya.cmds as cmds
from maya.debug.graphStructure import *

# The other methods are just helpers for this one.
__all__ = ['emConsistencyTest']

# Maximum number of frames to play (to avoid eternal tests)
EMCONSISTENCY_MAX_FRAMECOUNT = 10

#======================================================================

def _hasEvaluationManager():
	"""
	Check to see if the evaluation manager is available
	"""
	return 'evaluationManager' in dir(cmds)

#======================================================================

def _isMayaFile(fileName):
	return fileName[-3:] == '.ma' or fileName[-3:] == '.mb'

#======================================================================

def _testPlayback(outputFile=None, maxFrames=EMCONSISTENCY_MAX_FRAMECOUNT, resultsPath=None):
	"""
	Run a simluated playback sequence. Since Maya has no script-based
	per-frame callback the playback has to be faked by changing the
	current frame and forcing a refresh, for each frame in the playback.

	This isn't a precise representation of what playback does but since
	the EM rebuilds the graph on any global time change it should give
	exactly the same results as though it were measured right within a
	playback sequence.

	maxFrames indicates the most frames that will be played back.
	Generally speaking the tests should only need a few frames to get an
	accurate picture but you may want more to catch odd conditions. Set
	it to 0 to run all frames specified by the playback options.

	If outputFile is set then dump the graph comparison results to that
	file.

	If resultsPath is set then the graph outputs will be dumped to a file
	whose base name is that with the suffix "_N.eg" for frame "N".
	"""
	startFrame = cmds.playbackOptions( query=True, minTime=True )
	actualEndFrame = cmds.playbackOptions( query=True, maxTime=True )
	endFrame = actualEndFrame

	# If you have a scene with hugely long playback you don't want to be
	# waiting forever for the runs so limit the frame length to something
	# reasonable. (Or this could be recoded to make this an option.)
	if EMCONSISTENCY_MAX_FRAMECOUNT > 0 and actualEndFrame - startFrame >= EMCONSISTENCY_MAX_FRAMECOUNT:
		endFrame = startFrame + EMCONSISTENCY_MAX_FRAMECOUNT - 1

	# List of the evaluation graph contents, one entry per frame
	graphList = []

	# The value to return
	allTheSame = True

	totalElapsed = 0.0
	theFrame = int(startFrame)
	while theFrame <= endFrame:
		# Move to the new time
		cmds.currentTime( theFrame )

		# Force a refresh to get evaluation running.
		cmds.refresh( force=True )

		# Get the EM graph
		graphList.append( graphStructure(evaluationGraph=True) )

		# Dump the graph to a file if requested
		if resultsPath != None:
			try:
				graphFileName = resultsPath + '_%d.eg' % theFrame
				graphList[-1].write( graphFileName )
				if resultsPath != None:
					print '-> Graph at frame %d dumped to "%s"' % (theFrame, graphFileName)
			except Exception, ex:
				print 'WARNING: Results for frame %d could not be dumped to file %s (%s)' % (theFrame, graphFileName, str(ex) )

		# Compare the graph against the previous one. Any other one will do
		# since the check is for all of them being equal but doing one at a
		# time gives a better way to see what has changed.
		if theFrame > startFrame:
			currentFrame = theFrame - int(startFrame)
			lastFrame = currentFrame - 1
			graphDiff = graphList[currentFrame].compare( graphList[lastFrame] )
			if len(graphDiff) > 0:
				allTheSame = False
				if outputFile:
					outputFile.write( 'Compare Frame %g and Frame %g\n{\n' % (theFrame, theFrame-1) )
					for diffLine in graphDiff:
						outputFile.write( '    ' + diffLine )
					outputFile.write( '}\n' )

		# Invalidate the EM graph for next time. Use "False" as the value so
		# that the rebuild isn't immediately queued up.
		cmds.evaluationManagerInternal( invalidate=False )

		theFrame += 1

	return allTheSame

#======================================================================

def emConsistencyTest( fileName=None, resultsPath=None, doParallel=False, maxFrames=EMCONSISTENCY_MAX_FRAMECOUNT ):
	"""
	Run a simulated playback, forcing a rebuild the evaluation manager graph
	every frame and dumping the graph structure into a Python object for
	later comparison.

	Compare successive frames, pushing the output to the named resultsPath if
	it was specified. A "_N.eg" suffix is added for the contents of the graph
	at frame "N" and a "_diff.txt" suffix is added for the comparisons between
	the different graphs (with appropriate markers within the file indicating
	which frames are being compared).

	If doParallel is set to True then use the EM parallel evaluation mode
	instead of the serial mode. It's less stable at the moment but will
	also allow dumping and comparison of the scheduling graph.

	maxFrames is used to define the maximum number of frames to run in the
	playback test. Set it to 0 to indicate that every available frame should
	be used. The playback will run from startFrame to startFrame+maxFrames-1

	Returns True if all frames generated the same graph, otherwise False.
	"""
	outputFile = sys.stdout
	if resultsPath != None:
		resultsFileName = resultsPath + '_diff.txt'
		try:
			outputFile = open( resultsFileName, 'w' )
		except Exception, err:
			print 'ERROR: Could not open output file (%s)' % str(err)
			return
	else:
		resultsFileName = ''
		outputFile = None

	# Fail if evaluation manager is not available
	if not _hasEvaluationManager():
		print 'ERROR: Evaluation manager is not available.'
		return False

	# Fail if the fileName is not a valid Maya file.
	if fileName != None and not _isMayaFile(fileName):
		print 'ERROR: %s is not a Maya file' % fileName
		return False

	# Load the fileName if it was specified, otherwise the current scene will be tested
	if fileName != None:
		cmds.file( fileName, force=True, open=True )

	# Run the actual test
	oldMode = cmds.evaluationManager( query=True, mode=True )[0]

	if doParallel:
		cmds.evaluationManager( mode='parallel' )
	else:
		cmds.evaluationManager( mode='serial' )
	
	success = _testPlayback( outputFile=outputFile, maxFrames=maxFrames, resultsPath=resultsPath )

	cmds.evaluationManager( mode=oldMode )

	if resultsPath != None:
		print 'Result differences dumped to "%s"' % resultsFileName

	return success

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
