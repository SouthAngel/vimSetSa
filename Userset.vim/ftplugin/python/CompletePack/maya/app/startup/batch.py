"""
This module is imported during the startup of Maya in batch mode.
"""

import maya.app.startup.basic

# Run the user's userSetup.py if it exists
maya.app.startup.basic.executeUserSetup()

pass
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
