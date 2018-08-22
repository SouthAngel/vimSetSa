"""
Utility to verify that the background evaluation and caching system are
yielding the same results as the Maya parallel evaluation.

It is a simple wrapper around run_correctness_test().  See its documentation
for more details.

Sample usage to run the tests on a single file:

    from maya.debug.cacheCorrectnessTest import cacheCorrectnessTest
    cacheErrors = cacheCorrectnessTest(fileName='MyDir/MyFile.ma', resultsPath='MyDir/cacheCorrectness', modes=[['transform', 'mesh', 'curves']])

Sample usage to run the tests on the current scene and ignore output:

    from maya.debug.cacheCorrectnessTest import cacheCorrectnessTest
    cacheErrors = cacheCorrectnessTest(modes=[['transform', 'mesh', 'curves']])
"""

import maya.cmds as cmds
import maya.mel as mel
from maya.debug.TODO import TODO as TODO
from maya.debug.correctnessUtils import run_correctness_test as run_correctness_test
from maya.debug.correctnessUtils import CORRECTNESS_MAX_FRAMECOUNT as CORRECTNESS_MAX_FRAMECOUNT
from maya.debug.correctnessUtils import CORRECTNESS_NO_SETUP as CORRECTNESS_NO_SETUP

__all__ = [ 'cacheCorrectnessTest'
          , 'CACHE_TIMEOUT'
          , 'getModeString'
          ]

# Maximum amount of time to wait for cache to fill.
CACHE_TIMEOUT = 1800

#======================================================================

class CacheEvaluatorContext(object):
    """
    This class configures the cache evaluator according to a set of options.

    It enables the evaluator for a given set of nodes.  The supported values are:
    - 'transform' : to enable the evaluator on transforms and derived types.
    """
    def __init__(self, mode, cacheTimeout):
        self.mode = mode
        self.cacheTimeout = cacheTimeout

        self.activeNodeTypes = cmds.evaluator(query=True, name='cache', nodeType=True, enable=True)

        evaluationCache = CacheEvaluatorContext.getEvaluationCache(['mesh'])
        if len(evaluationCache) != 1 or evaluationCache[0] not in [0, 1]:
            raise RuntimeError('Unexpected value for mesh evaluation cache.')
        self.evaluationCacheMesh = evaluationCache[0]

    def __enter__(self):
        cmds.evaluator(name='cache', enable='transform' in self.mode, nodeType='transform', nodeTypeChildren=True)
        cmds.evaluator(name='cache', enable='mesh' in self.mode, nodeType='mesh', nodeTypeChildren=True)
        cmds.evaluator(name='cache', enable='curves' in self.mode, nodeType='nurbsCurve', nodeTypeChildren=True)

        cmds.evaluator(name='cache', enable=False, nodeType='constraint', nodeTypeChildren=True)

        vp2Mode = 'On' if 'meshOnlyVP2' in self.mode else 'Off'
        cmds.evaluator(name='cache', configuration='evaluationCache%s=mesh' % vp2Mode)

        # Trigger background computation.
        cmds.currentTime(cmds.currentTime(query=True))
        # Wait for it to be done.
        cacheIsReady = cmds.evaluator(name='cache', configuration='waitForCache=%d' % self.cacheTimeout)[0]
        if not cacheIsReady:
            print 'WARNING: Cache was not completely filled'

        return self

    def __exit__(self,type,value,traceback):
        # Reset the evaluation cache value for meshes.
        vp2Mode = 'On' if self.evaluationCacheMesh else 'Off'
        cmds.evaluator(name='cache', configuration='evaluationCache%s=mesh' % vp2Mode)

        # Disable the evaluator on all the nodes
        cmds.evaluator(name='cache', nodeType='node', nodeTypeChildren=True, enable=False)
        # Enable the evaluator on nodes that were enabled.
        for node in self.activeNodeTypes:
            cmds.evaluator(name='cache', nodeType='node', nodeTypeChildren=False, enable=True)

    @staticmethod
    def getEvaluationCache(types):
        typeString = ','.join(types)
        TODO('BUG', 'A bug prevents us from using the Python command.', None)
        result = mel.eval('evaluator -name "cache" -valueName "evaluationCache=%s" -q;' % typeString)
        return [int(value) for value in result.split()]

#======================================================================

class CacheCorrectnessMode(object):
    """
    This class represents a mode to be tested in cache correctness tests.

    It knows about the cache mode (i.e. what caching point to be enabled).

    It always requires the same evaluation mode:
    - Parallel evaluation
    - Cache evaluator enabled
    """
    def __init__(self, cacheMode, cacheTimeout):
        self.cacheMode = cacheMode
        self.cacheTimeout = cacheTimeout

    def getTitle(self):
        """
        Returns the identifying string for this cache mode.
        """
        return getModeString(self.cacheMode)

    def getEmMode(self):
        """
        Returns the evaluation mode in which the cache correctness test must
        be run, which is the same for all tests:
        - Parallel evaluation
        - Cache evaluator enabled
        """
        return 'emp+cache'

    def getContext(self):
        """
        Returns the context object that will set up and tear down the required
        caching configuration to be tested.
        """
        return CacheEvaluatorContext(self.cacheMode, self.cacheTimeout)

def getModeString(mode):
    """
    Returns the identifying string for this cache mode, which is just the
    list of activated options separated by a '+' sign.
    """
    return '+'.join(mode)

def cacheCorrectnessTest( fileName=None
                        , resultsPath=None
                        , verbose=False
                        , modes=[['transform', 'mesh', 'curves']]
                        , maxFrames=CORRECTNESS_MAX_FRAMECOUNT
                        , dataTypes=['matrix','vertex','screen']
                        , emSetup=CORRECTNESS_NO_SETUP
                        , cacheTimeout=CACHE_TIMEOUT ):
    """
    Evaluate the file in multiple caching modes and compare the results.

    fileName:     See fileName parameter in run_correctness_test.
    resultsPath:  See resultsPath parameter in run_correctness_test.
    verbose:      See verbose parameter in run_correctness_test.
    modes:        List of modes to run the tests in.  A mode is a list of options to activate
                  in the cache system.  The only valid ones are:
                  transform: caches transforms
                  mesh: caches meshes
                  curves: caches NURBS curves
                  meshOnlyVP2: activates VP2 mesh caching
    maxFrames:    See maxFrames parameter in run_correctness_test.
    dataTypes:    See dataTypes parameter in run_correctness_test.
    emSetup:      See emSetup parameter in run_correctness_test.
    cacheTimeout: The maximum amount of time to wait for cache to fill.

    Returns the output of run_correctness_test().
    """

    referenceMode = 'emp'
    testModes = [CacheCorrectnessMode(mode, cacheTimeout) for mode in modes]

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
