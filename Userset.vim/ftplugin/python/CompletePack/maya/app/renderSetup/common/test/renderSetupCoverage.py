'''Render setup coverage support and configuration.

This module contains the configuration to run coverage.py on the render
setup code base.'''

import maya.cmds as cmds

import PythonTests.harness as harness

import coverage
import os
import os.path
import sys
import shutil

# Coverage singleton object in use during a test run.  If None, no coverage
# was computed.
cov = None

# Coverage directory.
covDir = None

# Modules to omit from coverage.
_omit = [
    # Omit resource files
    r'*_res.py']

_include = [
    # Only test render setup common and model for now (30-July-2016).
    r'*/maya/app/renderSetup/model/*',

    r'*/maya/app/renderSetup/common/*']

_renderSetupEditors = ['MayaLightEditorWindowWorkspaceControl', 
                       'MayaRenderSetupWindowWorkspaceControl']

# At least one member of _renderSetupEditors was deleted by this module.
editorDeleted = False


def initialize():
    global cov
    global covDir

    # We must be starting from a clean slate, so make sure the cov object
    # is None.
    if cov is not None:
        raise RuntimeError('Coverage data collection already started.')

    # Initialize the coverage directory.
    covDir = initializeCoverageDir()

    # If any render setup UI editor is shown, delete it.
    deleteEditors()

    # Unload all render setup modules, to reload them and properly compute
    # their coverage.
    unloadRenderSetup()

    # Create the coverage object
    cov = coverage.Coverage(
        omit=[os.path.normpath(path) for path in _omit],
        include=[os.path.normpath(path) for path in _include],
        config_file=False)
    cov.start()

    # Load the plugin
    cmds.loadPlugin('renderSetup.py')

def finalize():
    '''End coverage collecting, and return coverage percentage.'''

    global cov
    global covDir
    global editorDeleted

    if not cov:
        raise RuntimeError('No coverage data being collected.')

    cov.stop()
    # Pre-flight builds on Windows and Linux raise at this step with
    # 'No source for code OpenMaya.py', which is uninteresting, so ignore
    # errors.  PPT, 29-Jul-2016.
    covPercent = cov.html_report(directory=covDir+'/covhtml', 
                                 ignore_errors=True)
    cov = None
    covDir = None
    editorDeleted = False
    return covPercent

def unloadRenderSetup():
    '''Unload the render setup plugin and remove references to its modules.'''
    cmds.unloadPlugin('renderSetup.py')

    # Don't unload modules with sub-modules (a.k.a. packages).
    dontUnload = set(['maya.app.renderSetup.model', 
                      'maya.app.renderSetup.views', 
                      'maya.app.renderSetup.common',
                      'maya.app.renderSetup.common.test'])

    modules = dict(sys.modules)
    for mod in modules: 
        # Unload all modules except ourselves.
        if 'maya.app.renderSetup.' in mod and \
           'renderSetupCoverage' not in mod and \
           mod not in dontUnload:
            del sys.modules[mod]

def initializeCoverageDir():
    '''Create or clear out the coverage output directory.'''

    path = cmds.internalVar(userTmpDir=True) + '/coverage'

    # Use EAFP style (Easier to Ask for Forgiveness than Permission) and
    # create the directory, rather than LBYL style (Look Before You Leap),
    # which can lead to multi-process race conditions.  If the directory
    # exists, remove its contents.
    try: 
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise 
        else:
            shutil.rmtree(path)
            # At this point, directory creation must succeed, else let the
            # raised exception go through.
            os.makedirs(path)

    return path

def deleteEditors():
    '''Delete render setup editors before computing coverage.

    Unloading render setup modules causes the render setup window and
    light editor to fail.  Delete them if present.'''

    global editorDeleted

    batchMode = cmds.about(batch=True)
    if not batchMode:
        for e in _renderSetupEditors:
            if cmds.workspaceControl(e, exists=True):
                cmds.deleteUI(e)
                editorDeleted = True

def skipProblemTest(test):
    '''Decorator to skip render setup tests that fail when run with coverage.

    For reasons still unclear, certain tests fail because the
    PySide2.QtCore.QEvent module is no longer imported inside the
    views.renderSetupButton and views.renderSetupWindow modules.  This only
    occurs if a render setup editor window is deleted in deleteEditors.
    Skip these tests in such a case.

    This decorator can be used on classes or on individual test cases.'''

    return harness.skipIf(editorDeleted, 'Test fails under coverage')(test)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
