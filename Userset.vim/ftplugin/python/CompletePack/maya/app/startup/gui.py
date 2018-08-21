# module: maya.app.gui
#
# This module is imported during the startup of Maya in GUI mode.
#
import sys
import maya.app.startup.basic

# Run the user's userSetup.py if it exists
maya.app.startup.basic.executeUserSetup()

import maya.app.baseUI
import maya.utils

# Replace sys.stdin with a GUI version that will request input from the user
sys.stdin = maya.app.baseUI.StandardInput()

# Replace sys.stdout and sys.stderr with versions that can output to Maya's
# GUI
sys.stdout = maya.utils.Output()
sys.stderr = maya.utils.Output( error=1 )

maya.utils.guiLogHandler()

# ADSK_CLR_MGT_BEGIN
import maya.app.colorMgt.customTransformUI
import maya.app.colorMgt.inputSpaceRulesUI
# ADSK_CLR_MGT_END

import maya.app.quickRig.quickRigUI
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
