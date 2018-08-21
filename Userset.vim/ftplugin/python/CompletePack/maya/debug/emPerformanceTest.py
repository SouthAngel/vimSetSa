"""
Utiity to run a set of performance tests on files in a directory and report
the results in a CSV file for graphing.

Sample usage to run the tests on a bunch of files in a directory and show
progress as the tests are run:

    from maya.debug.emPerformanceTest import emPerformanceTest
    from maya.debug.emPerformanceTest import emPerformanceOptions as emo
    options = emo()
    options.setViewports( emo.VIEWPORT_2 )
    options.setReportProgress( True )
    emPerformanceTest(['MyDirectory'], resultsFileName='MyDirectory/emPerformance.csv', options)

It tries to be intelligent about defaults for resultsFileName - if a single
directory was specified in the locations parameter then the output is sent to
that directory with the file name "emPerformance.csv". Otherwise it defaults
to the same file name in the current working directory.

Results are posted in seconds for a single evaluation (min, max, and/or
average times when mutiple frames are evaluated).
"""

import os, sys
import maya.cmds as cmds
import maya.mel as mel
from maya.debug.emModeManager import *
from maya.debug.TODO import TODO as TODO

__all__ = ['emPerformance', 'emPerformanceTest', 'emPerformanceOptions']

# Maximum number of frames in playback (to avoid eternal tests)
EMPERFORMANCE_PLAYBACK_MAX = 50

#======================================================================

def evaluationManagerExists():
    """
    Check to see if the evaluation manager is available
    """
    return 'evaluationManager' in dir(cmds)

#======================================================================

def switchMayaViewport(newMode):
    """
    Helper to switch viewport modes. Only handles VP1 or VP2.
    """
    if newMode == emPerformanceOptions.VIEWPORT_1:
        mel.eval( 'setRendererInModelPanel "base_OpenGL_Renderer" modelPanel4' )
    elif newMode == emPerformanceOptions.VIEWPORT_2:
        mel.eval( 'setRendererInModelPanel "vp2Renderer" modelPanel4' )
    else:
        raise NameError( 'Switching to unknown viewport mode: %s' % str(newMode) )

#======================================================================

class emPerformanceRun(object):
    """
    Utility class to facilitate various types of performance timing.

    # Sample to run and gather playback results for two files
    timing = emPerformanceRun( fileName=file1, refresh=False )
    timing.runTests()
    print timing.columnTitles()
    print timing.columns()

    timing = emPerformanceRun( fileName=file2, refresh=False )
    timing.runTests()
    print timingResults.columns()

        fileNam        : Name of file on which to run the tests
                      If None then use the current file
        options        : Options for running the tests
        progress    : Progress object for reporting current status
    """
    def __init__(self, fileName=None, options=None, progress=None):
        """
        Nothing to initialize for the timing tester
        """
        self.results = {}
        self.fileName = fileName

        self.fileLoadResults = emPerformanceResults()
        self.fileNewResults = emPerformanceResults()
        self.setDirtyResults = emPerformanceResults()

        self.startFrame = 0.0
        self.endFrame = 0.0

        self.options = options
        self.progress = progress
        self.evalMode = emPerformanceOptions.EVALUATION_MODE_DG
        self.hasEvaluationManager = evaluationManagerExists()

    #----------------------------------------------------------------------

    def timingColumns(self, results):
        """
        Return the list of average, min, and max timing information from the
        results object passed in.
        """
        if self.options.allColumns:
            if results != None:
                return [results.averageTime(), results.minElapsed, results.maxElapsed]
            return [-1.0, -1.0, -1.0]

        if results != None:
            return [results.averageTime()]
        return [-1.0]

    #----------------------------------------------------------------------

    def columnTitles(self):
        """
        Get the CSV titles given the types of timing test requested.
        """
        columns = ['File']
        if self.options.allColumns:
            columns += ['Load', 'New']
        columns += self.options.columnTitles()
        return ','.join(columns)

    #----------------------------------------------------------------------

    def columns(self):
        """
        Get the CSV columns with timing information from the types of timing test requested.
        """
        columns = [self.fileName]
        if self.options.allColumns:
            columns += [self.fileLoadResults.totalElapsed, self.fileNewResults.totalElapsed]
        extras = []
        if emPerformanceOptions.TEST_PLAYBACK in self.options.testTypes:
            if self.options.allColumns:
                columns += [self.startFrame, self.endFrame]
            # For playback in EM there is also collection of graph creation and
            # scheduling time. Add those to the result tyeps to collect.
            if self.options.usesEvaluationManager():
                extras = [emPerformanceOptions.TEST_GRAPH_CREATION, emPerformanceOptions.TEST_GRAPH_SCHEDULING]

        for viewport in self.options.viewports:
            for mode in self.options.evalModes:
                for testType in self.options.testTypes + extras:
                    testId = (mode, testType, viewport)
                    if testId in self.results:
                        columns += self.timingColumns(self.results[testId])

        return ','.join( [str(c) for c in columns] )

    #----------------------------------------------------------------------

    def setEvaluationMode(self, newMode):
        """
        Helper to switch evaluation modes. Handles DG evaluation and both
        serial and parallel evaluation manager modes. Degrades gracefully
        when the evaluation manager is not present.
        """
        if newMode == emPerformanceOptions.EVALUATION_MODE_DG or not self.hasEvaluationManager:
            if self.hasEvaluationManager:
                cmds.evaluationManager( mode='off' )
        elif newMode == emPerformanceOptions.EVALUATION_MODE_EM_SERIAL:
            cmds.evaluationManager( mode='serial' )
        elif newMode == emPerformanceOptions.EVALUATION_MODE_EM_PARALLEL:
            cmds.evaluationManager( mode='parallel' )
        else:
            raise NameError( 'Switching to unknown mode: %s' % str(newMode) )
        self.evalMode = newMode

    #----------------------------------------------------------------------
    def testTheType(self, theTestType):
        """
        Simple redirect function to allow iteration over test modes
        """
        if theTestType == emPerformanceOptions.TEST_PLAYBACK:
            return self.testPlayback()
        elif theTestType == emPerformanceOptions.TEST_REFRESH:
            return self.testRefresh()
        elif theTestType == emPerformanceOptions.TEST_DIRTY_REFRESH:
            return self.testDirtyRefresh()
        elif theTestType == emPerformanceOptions.TEST_DIRTY:
            # This test is done as part of TEST_DIRTY_REFRESH
            return None
        elif theTestType == emPerformanceOptions.TEST_GRAPH_CREATION:
            # This test is done as part of TEST_PLAYBACK
            return None
        elif theTestType == emPerformanceOptions.TEST_GRAPH_SCHEDULING:
            # This test is done as part of TEST_PLAYBACK
            return None
        else:
            raise NameError( 'Trying to run in unknown test mode: %s' % str(theTestType) )

    #----------------------------------------------------------------------

    def runTests(self):
        """
        Run the tests specified by the options
        """

        # Doesn't actually use the mode manager yet, it's just here so that the state
        # of the evaluation manager is properly preserved and restored
        TODO( "REFACTOR", "Use the emModeManager to manage evaluation manager state", None )
        with emModeManager() as mgr:

            # Get to a neutral consistent state for file I/O.
            # If you want to measure file I/O in different modes use a different
            # test, this one takes long enough to run already and there is little
            # chance that different evaluation modes or viewports will make a
            # difference in the file loading time (maybe the first refresh, but
            # that's not measured here)
            #
            self.setEvaluationMode( emPerformanceOptions.EVALUATION_MODE_DG )
            if self.fileName:
                cmds.file( force=True, new=True )
                self.progress.startPhase( 'Reading' )
                self.fileLoadResults.startRep( 0 )
                cmds.file( self.fileName, force=True, open=True )
                self.fileLoadResults.endRep( 0 )

            # Run all combinations of tests specified by the options
            for mode in self.options.evalModes:
                self.setEvaluationMode( mode )
                for viewport in self.options.viewports:
                    switchMayaViewport( viewport )
                    for testType in self.options.testTypes:
                        testRun = (mode, testType, viewport)
                        # Dirty refresh measures both the refresh and the dirty
                        # times so it has to collect the results separately
                        timingResults = self.testTheType( testType )
                        if not timingResults:
                            pass
                        elif testType == emPerformanceOptions.TEST_DIRTY_REFRESH:
                            if len(timingResults) == 2:
                                (dirtyResults, refreshResults) = (timingResults[0], timingResults[1])
                            else:
                                raise TypeError( 'Dirty refresh results not a pair: %s' % str(timingResults) )
                            self.results[testRun] = refreshResults
                            self.results[(mode, emPerformanceOptions.TEST_DIRTY, viewport)] = dirtyResults
                        elif testType == emPerformanceOptions.TEST_REFRESH:
                            self.results[testRun] = timingResults
                        elif testType == emPerformanceOptions.TEST_DIRTY:
                            self.results[testRun] = timingResults
                        else:
                            # Some modes only have playback results, others will
                            # separate out graph creation and scheduling results.
                            if type(timingResults) == type(()):
                                # EM playback keeps the graph creation times and actual
                                # playback times separate so record them separately
                                creationResults = timingResults[0]
                                schedulingResults = timingResults[1]
                                playbackResults = timingResults[2]
                                self.results[testRun] = playbackResults
                                self.results[(mode, emPerformanceOptions.TEST_GRAPH_CREATION, viewport)] = creationResults
                                self.results[(mode, emPerformanceOptions.TEST_GRAPH_SCHEDULING, viewport)] = schedulingResults
                            else:
                                self.results[testRun] = timingResults

            # Get back to the neutral state for file new timing
            self.setEvaluationMode( emPerformanceOptions.EVALUATION_MODE_DG )

            # If no file was loaded don't delete the current scene
            if self.fileName:
                self.progress.startPhase( 'New' )
                self.fileNewResults.startRep( 0 )
                cmds.file( force=True, new=True )
                self.fileNewResults.endRep( 0 )

    #----------------------------------------------------------------------

    def testPlayback(self):
        """
        Run a playback sequence, repeating 'iterationCount' times to get an overall average.
        Dump all of the results into the object's emPerformanceResults member.

            For EM modes returns a 3-tuple of emPerformanceResults object where timing will be stored
                1. Timing for evaluation graph creation (0 in DG mode) - 1 repetition
                2. Timing for scheduling graph creation (0 in DG mode) - 1 repetition
                3. Timing for playback - self.options.iterationCount repetitions
            For DG mode just returns the third element of the tuple.

        In the EM modes there is a bootstrapping process for evaluation that
        works as follows:
            - First frame of animation is used to build the evaluation graph
            - Second frame of animation is used to build the scheduling graph
            - Third frame of animation may be used to clean up any uninitialized caches in some scenes

        We want to separate the timing of the graph creation with the
        playback. The graph creation is a one-time cost whereas the playback
        is a repeating cost. Keeping these times separate lets us distinguish
        between per-frame evaluation speed and startup cost.
        """
        graphCreationResults = None
        graphSchedulingResults = None
        if 'off' != cmds.evaluationManager( query=True, mode=True )[0]:
            graphCreationResults = emPerformanceResults()
            graphSchedulingResults = emPerformanceResults()
        playbackResults = emPerformanceResults()
        TODO( "REFACTOR", "Use the playbackModeManager to manage playback state", None )
        self.startFrame = cmds.playbackOptions( query=True, minTime=True )
        actualEndFrame = cmds.playbackOptions( query=True, maxTime=True )
        self.endFrame = actualEndFrame

        # If you have a scene with hugely long playback you don't want to be
        # waiting forever for the runs so limit the frame length to something
        # reasonable. (Or this could be recoded to make this an option.)
        if actualEndFrame - self.startFrame >= EMPERFORMANCE_PLAYBACK_MAX:
            self.endFrame = self.startFrame + EMPERFORMANCE_PLAYBACK_MAX - 1
            cmds.playbackOptions( maxTime=self.endFrame )

        # Make sure it only plays a single loop
        oldLoopStyle = cmds.playbackOptions( query=True, loop=True )
        cmds.playbackOptions( loop="once" )

        # If using any of the evaluation manager modes collect the graph
        # building timing. A slight hack is used to collect this by nudging
        # the current time back and forth.
        if graphCreationResults:
            currentFrame = cmds.currentTime( query=True )
            graphCreationResults.startRep( 0 )
            cmds.currentTime( currentFrame + 1, edit=True )
            graphCreationResults.endRep( 0 )
            graphSchedulingResults.startRep( 0 )
            cmds.currentTime( currentFrame + 2, edit=True )
            graphSchedulingResults.endRep( 0 )
            # The currentTime call before playback will take care of any
            # uninitialized caches.

        self.progress.startPhase( '%s Play (%d times)' % (self.evalMode, self.options.iterationCount) )

        for idx in range(0, self.options.iterationCount):
            # Move to first frame to avoid slight variation in self.options.iterationCount
            # caused by the initialization of playback from different frames.
            cmds.currentTime( self.startFrame, edit=True )

            # Time a single runthrough of the entire animation sequence
            playbackResults.startRep( idx )
            cmds.play( wait=True )
            playbackResults.endRep( idx )

        # Restore the original options
        cmds.playbackOptions( loop=oldLoopStyle )
        cmds.playbackOptions( maxTime=actualEndFrame )

        # If the creation and scheduling results exist return them too
        if graphCreationResults:
            return (graphCreationResults, graphSchedulingResults, playbackResults)

        # Otherwise just the playback results go back. The caller has to
        # determine which set of results they have received.
        return playbackResults

    #----------------------------------------------------------------------

    def testRefresh(self):
        """
        Force a refresh "iterationCount" times to get an overall average.
        Dump all of the results into a emPerformanceResults class and return it.
        It dirties everything once before starting so that refresh has
        a consistent place to start, but the first refresh is not measured.

            Returns emPerformanceResults object where timing will be stored
        """
        results = emPerformanceResults()

        # Get the DG to a consistent state
        cmds.dgdirty( a=True )
        cmds.refresh( force=True )

        # Since refreshes are fast compared to playback do it 10 times
        self.progress.startPhase( '%s Refresh (%d times)' % (self.evalMode, self.options.iterationCount * 10) )
        for idx in range(0, self.options.iterationCount * 10):

            results.startRep( idx )
            cmds.refresh( force=True )
            results.endRep( idx )

        return results

    #----------------------------------------------------------------------

    def testDirtyRefresh(self):
        """
        Force a refresh "iterationCount" times to get an overall average.
        Dump all of the results into a emPerformanceResults class and return it.
        Unlike testRefresh() this method dirties the entire DG before each
        refresh to force the maximum evaluation.

            Returns emPerformanceResults object where timing will be stored
        """
        results = emPerformanceResults()
        dirtyResults = emPerformanceResults()
        # Since refreshes are fast compared to playback do it 10 times
        self.progress.startPhase( '%s Dirty Refresh (%d times)' % (self.evalMode, self.options.iterationCount * 10) )
        for idx in range(0, self.options.iterationCount * 10):

            # Make everything dirty so that the maximum evaluation happens
            dirtyResults.startRep( idx )
            cmds.dgdirty( a=True )
            dirtyResults.endRep( idx )

            results.startRep( idx )
            cmds.refresh( force=True )
            results.endRep( idx )

        return (results, dirtyResults)

#======================================================================

class emPerformanceOptions(object):
    """
    Simple holder class to manage all of the test run options in a single
    location. All of the members are orthogonal : they all specify a new
    set of combinations in which to run the others.

        iterationCount   : Number of iterations per playback/refresh (default 3).
                           Refresh uses 10x this number to get more consistent results.

        allColumns       : If True then only include file name and timing columns.
                           Excludes min/max, file load/new times, and playback range.

        reportProgress   : If True then put up a dialog window showing test run progress.
                           Will not affect the timing results. It also
                           provides a button that will let you terminate the
                           test run early if it turns out to be taking too long.

        evalModes        : List of modes to run (EVALUATION_MODE_XX)
                            EVALUATION_MODE_DG            Regular Maya DG Evaluation
                            EVALUATION_MODE_EM_SERIAL    Evaluation Manager serial mode
                            EVALUATION_MODE_EM_PARALLEL    Evaluation Manager parallel mode

        testTypes        : List of test types to run (TEST_TYPE_XX)
                            TEST_PLAYBACK        Run a playback (max 50 frames)
                            TEST_DIRTY            Dirty all before a refresh
                            TEST_REFRESH        Do refresh without dirty in between
                            TEST_DIRTY_REFRESH    Do refresh with dirty in between

        viewports        : List of viewports in which to run (VIEWPORT_X)
                            VIEWPORT_1            Run tests in original viewport
                            VIEWPORT_2            Run tests in VP2 (OGS)

    Total number of tests run will be:
        len(evalModes) * len(testTypes) * len(viewports)
    """
    # Modes in which to run tests
    EVALUATION_MODE_DG = 'DG'
    EVALUATION_MODE_EM_SERIAL = 'EMS'
    EVALUATION_MODE_EM_PARALLEL = 'EMP'

    # Types of tests to run
    TEST_PLAYBACK = 'Playback'
    TEST_DIRTY = 'Dirty'
    TEST_REFRESH = 'Refresh'
    TEST_DIRTY_REFRESH = 'Dirty Refresh'
    # Timing collected during playback of EM runs. Not specifically requested.
    TEST_GRAPH_CREATION = 'Graph Creation'
    TEST_GRAPH_SCHEDULING = 'Graph Scheduling'

    # Viewports in which tests can run
    VIEWPORT_1 = 'VP1'
    VIEWPORT_2 = 'VP2'

    #----------------------------------------------------------------------
    def __init__(self):
        if evaluationManagerExists():
            self.evalModes = [
                              emPerformanceOptions.EVALUATION_MODE_DG
                              , emPerformanceOptions.EVALUATION_MODE_EM_SERIAL
                              , emPerformanceOptions.EVALUATION_MODE_EM_PARALLEL
                             ]
        else:
            self.evalModes = [emPerformanceOptions.EVALUATION_MODE_DG]

        self.testTypes = [
                          emPerformanceOptions.TEST_PLAYBACK
                          , emPerformanceOptions.TEST_REFRESH
                          , emPerformanceOptions.TEST_DIRTY_REFRESH
                          , emPerformanceOptions.TEST_DIRTY
                         ]

        self.viewports = [emPerformanceOptions.VIEWPORT_1, emPerformanceOptions.VIEWPORT_2]

        self.allColumns = True
        self.iterationCount = 3
        self.reportProgress = False

    #----------------------------------------------------------------------
    def usesEvaluationManager(self):
        'Check to see if any of the active modes use the EM'
        if emPerformanceOptions.EVALUATION_MODE_EM_SERIAL in self.evalModes:
            return True
        if emPerformanceOptions.EVALUATION_MODE_EM_PARALLEL in self.evalModes:
            return True
        return False

    #----------------------------------------------------------------------
    def setAllColumns(self, newAllColumns):
        """
        Toggles the amount of data that will appear in the output CSV file.
        If turned off then only the bare minimum will be included:
            Name of File
            Timing Rate for each mode
        Noticeably omitted are start/end of playback ranges (if requested),
        file load and new times, and min/max timing.

        When you just want local comparisons of simple timing then turn
        this mode off. Full runs that will be backed up to databases should
        keep it on.
        """
        self.allColumns = newAllColumns

    #----------------------------------------------------------------------
    def setIterationCount(self, newIterationCount):
        """
        Set the number of iterations that the playback will do in order to get
        a reasonable average. Refresh will do 10x this number since it is so
        much faster (i.e. equivalent to 10 frames of playback)
        """
        self.iterationCount = newIterationCount

    #----------------------------------------------------------------------
    def setReportProgress(self, newReportProgress):
        """
        Turn on or off reporting of progress. When on the test run will put up
        a dialog indicating how much work is done and how much is lest. The
        dialog is updated outside of timing tests to it will not influence
        results.  It also provides a button that will let you terminate the
        test run early if it turns out to be taking too long.
        """
        self.reportProgress = newReportProgress

    #----------------------------------------------------------------------
    def setEvalModes(self, newEvalModes):
        """
        Define the evaluation modes to be used for the test runs. Valid values are:
            emPerformanceOptions.EVALUATION_MODE_DG
            emPerformanceOptions.EVALUATION_MODE_EM_SERIAL
            emPerformanceOptions.EVALUATION_MODE_EM_PARALLEL
        You can pass in a single value or a list of values.
        """
        if type(newEvalModes) == type([]):
            self.evalModes = newEvalModes
        else:
            self.evalModes = [newEvalModes]

    #----------------------------------------------------------------------
    def setTestTypes(self, newTestTypes):
        """
        Define the test types to be used for the test runs. Valid values are:
            emPerformanceOptions.TEST_PLAYBACK
            emPerformanceOptions.TEST_REFRESH
            emPerformanceOptions.TEST_DIRTY
            emPerformanceOptions.TEST_DIRTY_REFRESH
        You can pass in a single value or a list of values.
        """
        if type(newTestTypes) == type([]):
            self.testTypes = newTestTypes
        else:
            self.testTypes = [newTestTypes]

    #----------------------------------------------------------------------
    def setViewports(self, newViewports):
        """
        Define the viewports to be used for the test runs. Valid values are:
            emPerformanceOptions.VIEWPORT_1
            emPerformanceOptions.VIEWPORT_2
        You can pass in a single value or a list of values.
        """
        if type(newViewports) == type([]):
            self.viewports = newViewports
        else:
            self.viewports = [newViewports]

    #----------------------------------------------------------------------
    def columnTitles(self):
        """
        Build the list of column titles defined by the currently active options.
        """
        if self.allColumns:
            stats = ['Avg', 'Min', 'Max']
        else:
            stats = ['Time']
        columns = []
        extras = []
        if emPerformanceOptions.TEST_PLAYBACK in self.testTypes:
            if self.allColumns:
                columns += ['Start Frame', 'End Frame']
            # For playback in EM there is also collection of graph creation and
            # scheduling time. Add those to the result tyeps to collect.
            if self.usesEvaluationManager():
                extras = [emPerformanceOptions.TEST_GRAPH_CREATION, emPerformanceOptions.TEST_GRAPH_SCHEDULING]

        for viewport in self.viewports:
            for mode in self.evalModes:
                for resultType in self.testTypes + extras:
                    # DG mode doesn't have the creation and scheduling times
                    if (mode == emPerformanceOptions.EVALUATION_MODE_DG) and (resultType in extras):
                        continue
                    for stat in stats:
                        columns += ['%s %s %s %s' % (viewport, resultType, mode, stat)]
        return columns

#======================================================================

class emPerformanceResults(object):
    """
    Utility class to hold results of emPerformance runs of all types.
    Mostly used to print out results but can also be used to store
    them for later use and/or reformatting.
    """
    class RepData(object):
        """
        Helper container class to maintain sets of timing valid over
        a single repetition of a timing unit. A typical timing run will
        create at least three of these and run an average in order to
        get a more reliable value.

        startTime    : Timer value when the rep starts
        elapsedTime    : Difference between start and end timer values
        """
        def __init__(self):
            'Initialize times to zero'
            self.startTime = 0.0
            self.elapsedTime = 0.0

        def start(self):
            'Start the timer'
            self.startTime = cmds.timerX()

        def finish(self):
            'Stop the timer, record elapsed time'
            self.elapsedTime = cmds.timerX( st=self.startTime )

        def __str__(self):
            'Convert the timer to a human readable string'
            return "Elapsed time = %f" % self.elapsedTime

    #----------------------------------------------------------------------

    def __init__(self):
        'Clear out the current results'
        self.totalElapsed = 0.0
        self.repData = []
        self.minElapsed = 999999999
        self.maxElapsed = -999999999

    #----------------------------------------------------------------------

    def reset(self):
        'Clear out the current results'
        self.totalElapsed = 0.0
        self.repData = []
        self.minElapsed = 999999999
        self.maxElapsed = -999999999

    #----------------------------------------------------------------------

    def averageTime(self):
        'Calculate the average time of all the repetitions.'
        if len(self.repData) == 0:
            return 0
        return self.totalElapsed / len(self.repData)

    #----------------------------------------------------------------------

    def startRep(self, rep):
        'Start a repetition, initializing the timing data'
        self.repData.append( emPerformanceResults.RepData() )
        self.repData[rep].start()

    #----------------------------------------------------------------------

    def endRep(self, rep):
        'Finish a repetition, storing the timing data'
        try:
            self.repData[rep].finish()
            elapsed = self.repData[rep].elapsedTime
            if elapsed > self.maxElapsed:
                self.maxElapsed = elapsed
            if elapsed < self.minElapsed:
                self.minElapsed = elapsed
            self.totalElapsed = self.totalElapsed + elapsed
        except Exception, ex:
            print "*** ERR: End without start (%s)" % str(ex)

#======================================================================
def findMayaFiles(directory):
    'Search a directory and return a list of all Maya files beneath it'
    filesFound = []
    for content in os.listdir(directory):
        subpath = os.path.join(directory, content)
        if os.path.isdir(subpath):
            filesFound += findMayaFiles( subpath )
        elif os.path.isfile(subpath):
            if isMayaFile(subpath):
                filesFound.append( subpath )
    return filesFound

#======================================================================
def isMayaFile(potentialMayaFile):
    'Check to see if a given file is a valid Maya file'
    return potentialMayaFile[-3:] == '.ma' or potentialMayaFile[-3:] == '.mb'

#======================================================================
class progressState(object):
    """
    Helper class that manages the information relevant to the progress window.
        enable                : Turn on the window
        fileCount            : Total number of files to be processed
        currentFileName        : Name of file currently being processed
        progressPerFile        : Percentage of the whole (0-1) each file takes
        totalProgress        : Current total progress (0-1)
        currentFile            : Current file number
        currentPhase        : Current phase number
        currentPhaseName    : Name of the current phase
        progressPerPhase    : Percentage of the whole (0-1) each phase takes
                              Should be <= progressPerFile since a file will
                              consist of one or more phases.
    """
    def __init__(self, fileCount, phaseCount, enable):
        'Initialize all of the progress information and open the window if requested'
        self.enable = enable
        self.currentFileName = 'Startup'
        self.progressPerFile = 1.0 / fileCount
        self.totalProgress = 0
        self.currentFile = 0
        self.currentPhase = 0
        self.currentPhaseName = 'Reading'
        self.progressPerPhase = self.progressPerFile / phaseCount
        if enable:
            winTitle = 'Processing %d file(s)' % fileCount
            cmds.progressWindow( title=winTitle, progress=0, status='Initializing: 0%%', isInterruptable=True )

    def __del__(self):
        'Close the progress window if it was opened'
        if self.enable:
            cmds.progressWindow( endProgress=True )

    def aborting(self):
        """
        Call this when looping through the phases if you want to allow
        cancellation of tests at any particular time.
        """
        if not self.enable:
            return False
        return cmds.progressWindow(query=True, isCancelled=True)

    def reportProgress(self):
        """
        If the window is enabled put progress information consisting of the
        percentage done, the current file, and the current phase
        """
        if not self.enable:
            return
        progressPct = self.totalProgress * 100
        statusString = '%s:%s' % (self.currentPhaseName,self.currentFileName)
        cmds.progressWindow( edit=True, progress=progressPct, status=statusString )

    def startFile(self, newFileName):
        'Checkpoint a new file is starting'
        # At this level rough estimate of progress is by file since there
        # is no way of telling how much relative time each file will take.
        self.totalProgress = self.progressPerFile * self.currentFile
        self.currentFile += 1
        self.currentPhase = 0
        self.currentPhaseName = 'Reading'
        self.currentFileName = newFileName
        self.reportProgress()

    def startPhase(self, phaseName):
        'Checkpoint a new phase of the performance run is starting'
        self.currentPhaseName = phaseName
        previousProgress = self.totalProgress

        # Little trick to make the progress seem more reasonable driven by the
        # fact that you will never be able to reach 100%.
        #
        # For example if you have 3 phases then at the beginning of each phase
        # you would see progress (0%, 33%, 66%) representing amount of work
        # done. This gives the false impression that you're not making much
        # progress on individual phases.
        #
        # One obvious solution is to use much finer phases so that progress is
        # more continuous (0%, 1%, 2%...). Failing that this little trick can
        # be used that starts progress not at the beginning of the phase but a
        # little ways in. That's probably closer to reality anyway since by
        # the time you see the progress bar some work has been done.
        #
        # The factor 0.2 was picked arbitrarily, to represent a good balance
        # between amount of work probably done and perceived progress. In the
        # case above with 3 phases now you'll see (16.5%, 49.5%, 82.5%).
        #
        # For finer grained phases this works out well too since they will be
        # closer together anyway (0%, 1%, 2%...) becomes (0.5%, 1.5%, 2.5%...)
        # A cap is placed at 99% just in case too many phases are reported.
        #
        self.totalProgress += self.progressPerPhase*0.5
        self.totalProgress = 0.99 if self.totalProgress > 0.99 else self.totalProgress

        self.reportProgress()
        self.totalProgress = previousProgress + self.progressPerPhase

#======================================================================
def emPerformance(
    filesAndDirectories=None,
    resultsFileName=None,
    iterationCount=3,
    modes=None,
    testTypes=None,
    viewports=None,
    verbose=False
    ):
    """
    Same as emPerformanceTest but the options separated into different
    arguments. Legacy support.

        filesAndDirectories : List of locations in which to find Maya files to test
        resultsFileName     : Location of results.  Default is stdout.
                              Also correctly interprets the names 'stderr',
                              'cout', and 'cerr', plus if you use the
                              destination 'csv' it will return a Python list
                              of the CSV data.

    See the emPerformanceOptions class for a description of the other args.
    """
    options = emPerformanceOptions()
    if viewports:
        options.setViewports( viewports )
    options.setIterationCount( iterationCount )
    if testTypes:
        options.setTestTypes( testTypes )
    if modes:
        options.setEvalModes( modes )
    options.setReportProgress( verbose )
    return emPerformanceTest( filesAndDirectories, resultsFileName, options )

#======================================================================
def emPerformanceTest(
    filesAndDirectories=None,
    resultsFileName=None,
    options=None ):
    """
    Run a set of performance tests on files in a directory and report
    the results in a CSV file for graphing.

        filesAndDirectories : List of locations in which to find Maya files to test
        resultsFileName     : Location of results.  Default is stdout.
                              Also correctly interprets the names 'stderr',
                              'cout', and 'cerr', plus if you use the
                              destination 'csv' it will return a Python list
                              of the CSV data.
        options             : Set of options being used for the test run. See
                              the emPerformanceOptions class for details.

    The selected test types are run a number of times, collecting the min,
    max, and average timing. The stats dumped will depend on the options
    member 'allColumns'.

    The CSV file will contain timing information in several columns. Only the
    columns matching the requested flags are output. Every file found is put
    into its own row (so be careful about interpreting directories containing
    referenced files):

        File                    Name of the file being tested
        Load                    Load time
        New                        Time to do a "file -f -new"
        Start Frame                Start frame of the playback used by the file
        End Frame                End frame of the playback used by the file
        ...followed by multiple columns as selected in the format:
            VP MODE TYPE STAT

            VP        =    "VP1" or "VP2", for the viewport being tested
            MODE    =    "DG" for Maya evaluation
                        "EMP" for Evaluation Manager Parallel
                        "EMS" for Evaluation Manager Serial
            TYPE    =    "Playback" for timing of a playback sequence
                        "Refresh" for timing of simple refresh repeated
                        "Dirty Refresh" for timing of refresh after 'dgdirty -a'
            STAT    =    "Avg" for the average timing of all iterations
                        "Min" for the shortest timing over all iterations
                        "Max" for the longest timing over all iterations
    """
    dirList = []
    mayaFiles = []
    outputData = True
    if filesAndDirectories:
        for path in filesAndDirectories:
            if os.path.isdir( path ):
                dirFiles = findMayaFiles( path )
                dirList.append( path )
                mayaFiles += dirFiles
            elif os.path.isfile( path ):
                if isMayaFile( path ):
                    mayaFiles.append( path )
            else:
                print 'WARN: "%s" is neither file nor directory. Skipping.' % path

        if len(mayaFiles) == 0:
            print 'ERR: No files found at the given locations. Exiting.'
            return
    else:
        mayaFiles = [None]

    if resultsFileName == 'stdout' or resultsFileName == 'cout':
        outputFile = sys.stdout
    elif resultsFileName == 'stderr' or resultsFileName == 'cerr':
        outputFile = sys.stderr
    elif resultsFileName == 'csv':
        outputFile = None
        outputData = []
    elif resultsFileName == None:
        resultsFileName = 'emPerformance.csv'
        if len(dirList) == 1:
            resultsFileName = os.path.join( dirList[0], resultsFileName )
        try:
            outputFile = open( resultsFileName, 'w' )
        except Exception, err:
            print 'ERR: %s' % str(err)
            return
    else:
        try:
            outputFile = open( resultsFileName, 'w' )
        except Exception, err:
            print 'ERR: %s' % str(err)
            return

    # Warn if evaluation manager modes are requested but are not available
    if not options:
        options = emPerformanceOptions()
    if options.usesEvaluationManager():
        if not evaluationManagerExists():
            print 'WARN: Evaluation manager modes requested with no evaluation manager available. Using DG mode only'
            options.setEvalModes( emPerformanceOptions.EVALUATION_MODE_DG )

    # A single iteration of a single test run is considered a phase.
    # The orthogonal multipliers are:
    #        - evaluation type (dgEval, emsEval, empEval)
    #        - iteration count
    #        - test type (optional playback, optional refresh, + file load, new if not local)
    #
    phaseCount = len(options.evalModes) * len(options.testTypes) * len(options.viewports)
    if mayaFiles[0] != None:
        phaseCount += 2

    currentProgress = progressState(len(mayaFiles), phaseCount, options.reportProgress)

    titleObject = emPerformanceRun( fileName=None, options=options )
    if outputFile:
        outputFile.write( titleObject.columnTitles() + os.linesep )
    else:
        outputData.append( titleObject.columnTitles() )
    for fileName in mayaFiles:
        if fileName:
            currentProgress.startFile( os.path.basename(fileName) )
        else:
            currentProgress.startFile( 'Current Scene' )
        perform = emPerformanceRun( fileName=fileName, options=options, progress=currentProgress )
        perform.runTests()
        if outputFile:
            outputFile.write( perform.columns() + os.linesep )
        else:
            outputData.append( perform.columns() )

        # Allow premature cancellation
        if currentProgress.aborting():
            break

    return outputData

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
