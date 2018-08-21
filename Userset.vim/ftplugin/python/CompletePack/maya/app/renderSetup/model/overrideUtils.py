from maya.app.renderSetup.model.override import *
from maya.app.renderSetup.model.connectionOverride import *
import maya.app.renderSetup.common.utils as commonUtils

def getAllOverrideClasses():
    """ Returns the list of Override subclasses """
    return commonUtils.getSubClasses(Override)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
