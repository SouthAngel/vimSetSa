
"""Utilities for render setup import / export testing."""

import maya.app.renderSetup.model.renderSetup as renderSetup
import maya.app.renderSetup.model.override as override

import os


def createBasicRenderSetup():
    """ Create a basic render setup """
    rl1 = renderSetup.instance().createRenderLayer('rl1')
    c1 = rl1.createCollection('c1')
    ov1 = c1.createOverride('ov1', override.RelOverride.kTypeId)
    return (rl1, c1, ov1)

def tmpSubDirName(dir, subDir):
    """ Create a unique sub directory """
    suffix = ''
    while True:
        tmpPath = os.path.join(dir, (subDir + suffix))
        if os.path.exists(tmpPath):
            suffix = '1' if suffix == '' else str(int(suffix) + 1)
        else:
            break

    return tmpPath

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
