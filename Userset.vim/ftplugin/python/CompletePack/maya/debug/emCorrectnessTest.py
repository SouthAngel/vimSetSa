"""
Utility to verify that the evaluation manager is yielding the same results
as the Maya DG evaluation.

It is a simple wrapper around run_correctness_test().  See its documentation
for more details.

Legal values for modes are 'ems' and 'emp' with an optional '+XXX' to
indicate that evaluator XXX should be turned on during the test or an
optional '-XXX' to indicate that it should be turned off. Evaluator
states will be returned to their original value after the test is run.
If an evaluator is not explicitly listed the current state of it will
be used for the test.

e.g. modes=['ems','emp+deformer']  means run the comparison twice, first
against EM Serial mode, the second time against EM Parallel mode with
the 'deformer' evaluator turned on. You can use multiple evaluators if
you wish: modes=['ems+deformer-dynamics'].

Sample usage to run the tests on a single file:

    from maya.debug.emCorrectnessTest import emCorrectnessTest
    serialErrors = emCorrectnessTest(fileName='MyDir/MyFile.ma', resultsPath='MyDir/emCorrectness', modes=['ems'])[1]

Sample usage to run the tests on the current scene in parallel mode with the deformer evaluator and ignore output:

    from maya.debug.emCorrectnessTest import emCorrectnessTest
    parallelErrors = emCorrectnessTest(modes=['emp+deformer'])
"""

from maya.debug.correctnessUtils import run_correctness_test as run_correctness_test
from maya.debug.correctnessUtils import CORRECTNESS_MAX_FRAMECOUNT as CORRECTNESS_MAX_FRAMECOUNT
from maya.debug.correctnessUtils import CORRECTNESS_NO_SETUP as CORRECTNESS_NO_SETUP

__all__ = [ 'emCorrectnessTest' ]

#======================================================================

class EMCorrectnessMode(object):
    """
    This class represents a mode to be tested in EM correctness tests.
    """
    def __init__(self, mode):
        self.mode = mode

    def getTitle(self):
        return self.mode

    def getEmMode(self):
        return self.mode

    def getContext(self):
        return None

#======================================================================

def emCorrectnessTest( fileName=None
                     , resultsPath=None
                     , verbose=False
                     , modes=['ems']
                     , maxFrames=CORRECTNESS_MAX_FRAMECOUNT
                     , dataTypes=['matrix','vertex','screen']
                     , emSetup=CORRECTNESS_NO_SETUP ):
    """
    Evaluate the file in multiple evaluation manager modes and compare the results.

    fileName:    See fileName parameter in run_correctness_test.
    resultsPath: See resultsPath parameter in run_correctness_test.
    verbose:     See verbose parameter in run_correctness_test.
    modes:       List of modes to run the tests in. 'ems' and 'emp' are the
                 only valid ones. A mode can optionally enable or disable an
                 evaluator as follows:
                     'ems+deformer': Run in EM Serial mode with the deformer evalutor turned on
                     'emp-dynamics': Run in EM Parallel mode with the dynamics evalutor turned off
                     'ems+deformer-dynamics': Run in EM Serial mode with the dynamics evalutor
                                              turned off and the deformer evaluator turned on
    maxFrames:   See maxFrames parameter in run_correctness_test.
    dataTypes:   See dataTypes parameter in run_correctness_test.
    emSetup:     See emSetup parameter in run_correctness_test.

    Returns the output of run_correctness_test().
    """

    referenceMode = 'dg'
    testModes = [EMCorrectnessMode(mode) for mode in modes]

    return run_correctness_test(
        referenceMode,
        testModes,
        fileName,
        resultsPath,
        verbose,
        maxFrames,
        dataTypes,
        emSetup
        )
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
