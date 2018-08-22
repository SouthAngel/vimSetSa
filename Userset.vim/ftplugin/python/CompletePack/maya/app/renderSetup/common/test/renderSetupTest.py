import maya.app.renderSetup.model.conversion as conversion

import PythonTests.harness as harness

import maya.cmds as cmds
import maya.mel as mel


class RenderSetupTest(harness.TestCase):
    """ This class is the base class for all regression test classes """

    def __init__(self, testName):
        super(RenderSetupTest, self).__init__(testName)

    def setUp(self):
        super(RenderSetupTest, self).setUp()
        self.loadPlugin("renderSetup.py")

    @classmethod
    def setUpClass(cls):
        super(RenderSetupTest, cls).setUpClass()

        cls.previousAutoConvertFlag = None if not conversion.hasAutoConvertFlag() else conversion.getAutoConvertFlag()
        conversion.setAutoConvertFlag(False) # otherwise a dialog prompts during non-batch test

        # Unpredictability of idle queue job execution timing means that
        # some idle queue jobs (e.g. mental ray plugin load) execute in
        # legacy render layer mode (which is what our automated tests are
        # set up to do), but render setup tests expect render setup mode.
        # With flushIdleQueue() at start of render setup tests, all test
        # executions start with the same clean slate for idle queue jobs.
        cmds.flushIdleQueue()

        # This MEL global variable controls which render layer system is used 
        # to run regression tests. By default, even when using render setup,
        # regression tests are run in legacy render layer mode, so that 
        # legacy render layer tests run unchanged and therefore flag any 
        # legacy render layer regressions.

        # Here, we change the mode to render setup during the render setup tests."
        mel.eval("global int $renderSetupEnableDuringTests; $renderSetupEnableDuringTests = 1")

        # Some code now needs to have the mayaSoftware renderer to succeed
        # when it manipulates a render setup and/or a render layer because 
        # of the Render Settings collection. 
        # A Render Settings collection requests all the default nodes from
        # the default renderer. When executing some regression tests 
        # through Mutt the default renderer (i.e. mayaSoftware) is not loaded.

        # Impose mayaSoftware as the default renderer
        if not cmds.renderer("mayaSoftware", exists=True):
            mel.eval('registerMayaSoftwareRenderer')
        cls._prevRenderer = cmds.preferredRenderer(query=True)
        cmds.preferredRenderer("mayaSoftware", makeCurrent=True)

    @classmethod
    def tearDownClass(cls):
        super(RenderSetupTest, cls).tearDownClass()

        conversion.removeAutoConvertFlag()
        if cls.previousAutoConvertFlag is not None:
            conversion.setAutoConvertFlag(cls.previousAutoConvertFlag)

        # Clear render setup during test.
        mel.eval("global int $renderSetupEnableDuringTests; $renderSetupEnableDuringTests = 0")

        cmds.preferredRenderer(cls._prevRenderer, makeCurrent=True)
        del cls._prevRenderer
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
