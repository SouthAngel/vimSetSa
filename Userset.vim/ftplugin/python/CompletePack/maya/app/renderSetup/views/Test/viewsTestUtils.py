"""Utilities to test the render setup UI."""

import maya.app.renderSetup.model.renderSetup as renderSetup
import maya.app.renderSetup.model.traverse as traverse

import maya.cmds as cmds
import os


class proxyChildren(object):
    """Iterator on UI model (Qt) proxy objects."""

    def __init__(self, item):
        self.i    = 0
        self.item = item
        self.n    = item.rowCount()

    def __iter__(self):
        return self

    def next(self):
        if self.i < self.n:
            i = self.i
            self.i += 1
            return self.item.child(i)
        else:
            raise StopIteration()

def getProxy(node):
    # Don't import at module level, otherwise import will fail in batch mode.
    import maya.app.renderSetup.views.proxy.renderSetup as renderSetupProxy
    import maya.app.renderSetup.views.renderSetup as renderSetupUI

    return renderSetupUI.renderSetupWindow.centralWidget.renderSetupView.model() \
        if node == renderSetup.instance() else renderSetupProxy.getProxy(node)

def assertConsistency(unitTest, dataModel, proxy):
    """Check that the Qt model and the data model are consistent.

    This function checks that the UI (Qt) model and the data model are
    consistent by checking that their trees are identical in topology and
    refer to the same elements."""

    # Create generators that do a depth-first traversal of the UI (Qt)
    # model and data model trees, and compare them: they have to match.

    for (node, item) in zip(
            traverse.depthFirst(dataModel, traverse.nodeListChildren),
            traverse.depthFirst(proxy, proxyChildren)):

        # Number of children in the data model and UI model must be the same.
        unitTest.assertEqual(len(list(traverse.nodeListChildren(node))),
                             item.rowCount())

        # Qt model object as obtained from data model must be identical to
        # Qt model from traversal.
        unitTest.assertEqual(getProxy(node), item)



import maya.app.renderSetup.common.test.renderSetupTest as Test

class ViewRenderSetupTest(Test.RenderSetupTest):
    """ This class is the base class for all view regression test classes """
    
    def __init__(self, testName):
        super(ViewRenderSetupTest, self).__init__(testName)
        
    @classmethod
    def setUpClass(cls):
        super(ViewRenderSetupTest, cls).setUpClass()
        # Avoid any user interaction
        import maya.app.renderSetup.model.renderSetupPreferences as userPrefs
        cls.editMode = userPrefs.getEditMode()
        userPrefs.setEditMode(False)
        # The file dialog has (very) poor performance when opened on a
        # directory with a large number of files, which the user temporary
        # directory can have.  To avoid the test running for minutes
        # blocked on file dialog refresh, we create an empty sub-directory
        # just for our test.
        import maya.app.renderSetup.common.test.sceneUtils as sceneUtils
        cls.tmpDir = sceneUtils.tmpSubDirName(cmds.internalVar(utd=1), 'rsImportExport')
        os.mkdir(cls.tmpDir)

    @classmethod
    def tearDownClass(cls):
        super(ViewRenderSetupTest, cls).tearDownClass()
        # Revert the user interaction preference
        import maya.app.renderSetup.model.renderSetupPreferences as userPrefs
        userPrefs.setEditMode(cls.editMode)
        cls.editMode = None
        # Delete the temporary directory
        os.rmdir(cls.tmpDir)

    def setUp(self):
        super(ViewRenderSetupTest, self).setUp()
        # Start the Render Setup Window
        import maya.app.renderSetup.views.renderSetup as renderSetupUI
        self.mainWindow, self.propertyEditor = renderSetupUI.createUI()
        self.centralWidget = self.mainWindow.centralWidget
        cmds.flushIdleQueue()

    def tearDown(self):
        super(ViewRenderSetupTest, self).tearDown()
        # Close the Render Setup Window
        self.centralWidget = None
        self.propertyEditor.close()
        self.mainWindow.close()
        self.propertyEditor = None
        self.mainWindow = None

    def renderSetupWindow(self):
        return self.centralWidget
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
